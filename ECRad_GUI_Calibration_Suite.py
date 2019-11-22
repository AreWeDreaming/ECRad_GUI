'''
Created on Apr 3, 2019

@author: sdenk
'''
from GlobalSettings import globalsettings
import wx
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row
from wxEvents import *
from plotting_configuration import *
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from plotting_core import plotting_core
from ECRad_DIAG_AUG import DefaultDiagDict
from copy import deepcopy
if(globalsettings.Phoenix):
    from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
else:
    from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx
from Calibration_utils import calibrate
from Fitting import make_fit
import numpy as np
import os
from ECRad_Results import ECRadResults
if(globalsettings.AUG):
    from shotfile_handling_AUG import get_data_calib, moving_average
    from get_ECRH_config import get_ECRH_viewing_angles
else:
    print("AUG shotfile system inaccessible -> Cross-calibration not supported at the moment.")
from Diags import Diag


class CalibPanel(wx.Panel):
    def __init__(self, parent, Scenario):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(8.5, 6.5), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(4.5, 4.5), tight_layout=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.Results = None
        self.calib_diag_dict = None
        self.last_used_diag_name = None
        self.Bind(wx.EVT_ENTER_WINDOW, self.ChangeCursor)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.canvas.draw()
        self.pc_obj = plotting_core(self.fig, self.dummy_fig, False)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        tw, th = self.plot_toolbar.GetSize().Get()
        fw, fh = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.plotted_time_points = []  # To avoid duplicates
        self.button_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.calibrate_button = wx.Button(self, 0, "Calibrate")
        self.calibrate_button.Bind(wx.EVT_BUTTON, self.OnCalibrate)
        self.plot_avg_button = wx.Button(self, 0, "Plot avg.")
        self.plot_avg_button.Bind(wx.EVT_BUTTON, self.OnPlotAvg)
        if(globalsettings.Phoenix):
            self.plot_avg_button.SetToolTip("Plot avg. calib factors once they are loaded")
        else:
            self.plot_avg_button.SetToolTipString("Plot avg. calib factors once they are loaded")
        self.reset_plot_button = wx.Button(self, 0, "Reset Plot")
        self.reset_plot_button.Bind(wx.EVT_BUTTON, self.OnResetPlot)
        self.button_sizer.Add(self.calibrate_button, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL, 5)
        self.button_sizer.Add(self.plot_avg_button, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL, 5)
        self.button_sizer.Add(self.reset_plot_button, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL, 5)
        self.diag_select_choice_label = wx.StaticText(self, 0, "Select diagnostic:")
        self.button_sizer.Add(self.diag_select_choice_label, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL, 5)
        self.diag_select_choice = wx.Choice(self, 0)
        self.diag_select_choice.Bind(wx.EVT_CHOICE, self.OnNewDiagSelected)
        self.button_sizer.Add(self.diag_select_choice, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL, 5)
        self.button_ctrl_sizer.Add(self.button_sizer, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.control_sizer = wx.GridSizer(0, 5, 0, 0)
        self.diag_tc = simple_label_tc(self, "diag", "None", "string")
        self.control_sizer.Add(self.diag_tc, 0, wx.ALL, 5)
        self.exp_tc = simple_label_tc(self, "exp", "None", "string")
        self.control_sizer.Add(self.exp_tc, 0, wx.ALL, 5)
        self.ed_tc = simple_label_tc(self, "ed", 0, "integer")
        self.control_sizer.Add(self.ed_tc, 0, wx.ALL, 5)
        self.smoothing_tc = simple_label_tc(self, "binning [ms]", 1.0, "real")
        self.control_sizer.Add(self.smoothing_tc, 0, wx.ALL, 5)
        self.overwrite_diag_cb = simple_label_cb(self, "overwrite diag", False)
        self.control_sizer.Add(self.overwrite_diag_cb, 0, wx.ALL, 5)
        self.button_ctrl_sizer.Add(self.control_sizer, 0, \
                wx.ALIGN_LEFT, 0)
        self.line1 = wx.StaticLine(self, wx.ID_ANY)
        self.button_ctrl_sizer.Add(self.line1, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.mode_filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mode_filter_cb = simple_label_cb(self, "Filter for MHD modes", False)
        self.mode_filter_sizer.Add(self.mode_filter_cb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.mode_width_tc = simple_label_tc(self, "Witdh of mode [Hz]", 100.0, "real")
        self.mode_filter_sizer.Add(self.mode_width_tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.freq_cut_off_tc = simple_label_tc(self, "Lower frequeny cut off for mode filter [Hz]", 100.0, "real")
        self.mode_filter_sizer.Add(self.freq_cut_off_tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.button_ctrl_sizer.Add(self.mode_filter_sizer, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.line2 = wx.StaticLine(self, wx.ID_ANY)
        self.button_ctrl_sizer.Add(self.line2, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.timepoint_label = wx.StaticText(self, wx.ID_ANY, \
                                             "Run calibrate once with all time points. " + \
                                             "Afterwards refine calibration by double clicking " + \
                                             "time points and reviewing the calibration", style=wx.ALIGN_CENTER_HORIZONTAL)
        self.timepoint_label.Wrap(400)
        self.timepoint_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.timepoint_label_sizer.Add(self.timepoint_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.button_ctrl_sizer.Add(self.timepoint_label_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line3 = wx.StaticLine(self, wx.ID_ANY)
        self.button_ctrl_sizer.Add(self.line3, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.used = []
        self.unused = []
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used time points")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.used_list.AppendItems(self.used)
        self.used_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnPlotUsedTimePoint)
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused time points")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnPlotUnUsedTimePoint)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.button_ctrl_sizer.Add(self.select_sizer, 1, \
                         wx.EXPAND | wx.ALL, 5)
        self.canvas_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.sizer.Add(self.button_ctrl_sizer, 1, wx.ALL | \
                wx.EXPAND, 5)
        self.sizer.Add(self.canvas_sizer, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)

    def OnUpdate(self, evt):
        self.Results = evt.Results
        self.shot = self.Results.Scenario.shot
        self.time = self.Results.time
        if(len(list(self.Results.Scenario.used_diags_dict)) > 0 and len(self.time) > 0):
            self.calib_diag_dict = {}
            if(self.last_used_diag_name in self.Results.Scenario.used_diags_dict):
                self.last_used_diag_name = None
            self.diag_select_choice.Clear()
            for key in self.Results.Scenario.used_diags_dict:
                self.diag_select_choice.Append(self.Results.Scenario.used_diags_dict[key].name)
                self.calib_diag_dict[key] = deepcopy(self.Results.Scenario.used_diags_dict[key])
            self.used = list(self.time.astype("|U7"))
            self.unused = []
            self.used_list.Clear()
            if(len(self.used) > 0):
                self.used_list.AppendItems(self.used)
            self.unused_list.Clear()
            if(len(self.unused) > 0):
                self.unused_list.AppendItems(self.unused)
            self.diag_select_choice.Select(0)
            self.OnNewDiagSelected(None)

    def UpdateCalib_diag_dict(self):
        if(self.last_used_diag_name in self.calib_diag_dict):
            self.calib_diag_dict[self.last_used_diag_name].diag = self.diag_tc.GetValue()
            self.calib_diag_dict[self.last_used_diag_name].exp = self.exp_tc.GetValue()
            self.calib_diag_dict[self.last_used_diag_name].ed = self.ed_tc.GetValue()
            self.calib_diag_dict[self.last_used_diag_name].t_smooth = self.smoothing_tc.GetValue() * 1.e-3
            self.calib_diag_dict[self.last_used_diag_name].mode_filter = self.mode_filter_cb.GetValue()
            self.calib_diag_dict[self.last_used_diag_name].mode_width = self.mode_width_tc.GetValue()
            self.calib_diag_dict[self.last_used_diag_name].freq_cut_off = self.freq_cut_off_tc.GetValue()

    def OnNewDiagSelected(self, evt):
        if(self.Results is None):
            return
        if(len(list(self.Results.Scenario.used_diags_dict))==0):
            return
        if(self.last_used_diag_name == self.diag_select_choice.GetStringSelection()):
            return
        if(self.last_used_diag_name is not None):
            self.UpdateCalib_diag_dict()
        self.last_used_diag_name = self.diag_select_choice.GetStringSelection()
        if(hasattr(self.calib_diag_dict[self.last_used_diag_name], "diag")):
            self.diag_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].diag )
            self.exp_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].exp)
            self.ed_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].ed)
            self.smoothing_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].t_smooth * 1.e3)
            self.mode_filter_cb.SetValue(self.calib_diag_dict[self.last_used_diag_name].mode_filter)
            self.mode_width_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].mode_width)
            self.freq_cut_off_tc.SetValue(self.calib_diag_dict[self.last_used_diag_name].freq_cut_off)
        if(self.last_used_diag_name in list(self.Results.masked_time_points)):
            self.used = list(self.time[self.Results.masked_time_points[self.last_used_diag_name]].astype("|U7"))
            self.unused = list(self.time[self.Results.masked_time_points[self.last_used_diag_name] == False].astype("|U7"))
            self.used_list.Clear()
            if(len(self.used) > 0):
                self.used_list.AppendItems(self.used)
            self.unused_list.Clear()
            if(len(self.unused) > 0):
                self.unused_list.AppendItems(self.unused)
        self.OnResetPlot(None)      
        

    def OnAddSelection(self, evt):
        sel = self.unused_list.GetSelections()
        for i_sel in sel:
            string = self.unused_list.GetString(i_sel)
            self.used.append(self.unused.pop(self.unused.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnRemoveSelection(self, evt):
        sel = self.used_list.GetSelections()
        for i_sel in sel:
            string = self.used_list.GetString(i_sel)
            self.unused.append(self.used.pop(self.used.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def ChangeCursor(self, event):
        if(globalsettings.Phoenix):
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

    def OnCalibrate(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Calibrating - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        self.UpdateCalib_diag_dict()
        if(len(self.used) == 0):
            print("No time points designated for calibration --  aborting")
            return
        self.cur_diag=None #  Diag in self.Results.Scenario.used_diags_dict that corresponds to the currently select diagnostic
        self.last_used_diag_name = self.diag_select_choice.GetStringSelection()
        try:
            for key in list(self.Results.Scenario.used_diags_dict):
                if(key == self.last_used_diag_name):
                    self.cur_diag = self.Results.Scenario.used_diags_dict[key]
                elif(self.overwrite_diag_cb.GetValue() and key == "EXT"):
                    self.Results.Scenario.used_diags_dict[self.cur_diag.name] = deepcopy(self.calib_diag_dict[self.last_used_diag_name])
                    for itime in range(len(self.Results.time)):
                        self.Results.Scenario.ray_launch["diag_name"][itime][self.Results.Scenario.ray_launch["diag_name"][itime] == "EXT"] = self.calib_diag_dict[self.last_used_diag_name].name
                    del(self.Results.Scenario.used_diags_dict[key])
        except AttributeError as e:
            print("ERROR! Nothing to calibrate!")
            print(e)
            return
        if(self.cur_diag is None):
            print("Could not find any data for {0:s} in current ECRad data set".format(self.calib_diag_dict[self.last_used_diag_name].name))
            print("Available diagnostics are", list(self.Results.Scenario.used_diags_dict))
            return
        if(self.calib_diag_dict[self.last_used_diag_name].exp != self.cur_diag.exp):
            print("Warning experiment of diagnostic not consistent with ECRad configuration")
            print("Proceeding anyways")
        if(self.calib_diag_dict[self.last_used_diag_name].ed != self.cur_diag.ed):
            print("Warning edition of diagnostic not consistent with ECRad configuration")
            print("Proceeding anyways")
        if(self.cur_diag.name in list(self.Results.calib)):
            print("Calibration already done")
            print("Deleting old calibration and proceeding")
            del(self.Results.calib[self.cur_diag.name])
            del(self.Results.calib_mat[self.cur_diag.name])
            del(self.Results.std_dev_mat[self.cur_diag.name])
            del(self.Results.rel_dev[self.cur_diag.name])
            del(self.Results.sys_dev[self.cur_diag.name])
            del(self.Results.masked_time_points[self.cur_diag.name])
        masked_timepoints = np.zeros(len(self.Results.time), np.bool)
        masked_timepoints[:] = True
        self.delta_t = 0.5 * np.mean(self.Results.time[1:len(self.Results.time)] - \
                                     self.Results.time[0:len(self.Results.time) - 1])
        no_double_booking = []
        for i in range(len(self.unused)):
            j = np.argmin(np.abs(self.Results.time - float(self.unused[i])))  # To avoid round off errors
            if(j not in no_double_booking):
                # this should identify the masked time points reliably
                masked_timepoints[j] = False
                no_double_booking.append(j)
            else:
                print("Attempted double booking", float(self.unused[i]), self.Results.time[j])
                return
        if(len(self.Results.time[masked_timepoints]) != len(self.used)):
            print("Error: Not as many masked time points as used time points")
            print("Recheck selection criterion")
            return
        self.pc_obj.reset(False)
        print("Using standard Trad for calibration")
        time = []
        Trad = []
        for i in range(len(self.Results.time[masked_timepoints])):
            time.append(self.Results.time[masked_timepoints][i])
            Trad.append(self.Results.Trad[masked_timepoints][i][self.Results.Scenario.ray_launch[masked_timepoints][i]["diag_name"] == self.cur_diag.name])
        time = np.array(time)
        Trad = np.array(Trad)
        calib_mat, std_dev_mat, calib, rel_dev, sys_dev = calibrate(self.shot, time, Trad, self.calib_diag_dict[self.last_used_diag_name], \
                                                                    self.cur_diag) # aux diag for RMC calibration to find available channels via RMD
        if(len(calib) == 0):
            print("Calibration failed")
            return
#        except ValueError as e:
#            print(e)
#            return
        self.Results.UpdateCalib(self.cur_diag, calib, calib_mat, std_dev_mat, rel_dev, sys_dev, masked_timepoints)
        evt = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
        evt.SetResults(self.Results)
        self.Parent.Parent.GetEventHandler().ProcessEvent(evt)
        # Plot makes only sense for a single frequency -> frequency at first time point
        freq = self.Results.Scenario.ray_launch[masked_timepoints][0]["f"][self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.last_used_diag_name] * 1.e-9
        self.fig, self.fig_extra = self.pc_obj.diag_calib_avg(self.cur_diag, freq, \
                                                              calib, rel_dev, "Avg. calibration factors for diagn. " + \
                                                              self.cur_diag.name)
        self.canvas.draw()
# Unnecessary ASCII output        
#         ed = 1
#         filename_out = os.path.join(self.Results.Config.working_dir, "calib_" + str(self.Results.Scenario.shot) + "_" + self.cur_diag.name + "_ed_" + str(ed))
#         while(os.path.exists(filename_out + ".cal")):
#             ed += 1
#             filename_out = os.path.join(self.Results.Config.working_dir, "calib_" + str(self.Results.Scenario.shot) + "_" + self.cur_diag.name + "_ed_" + str(ed))
#         Calib_Log_File = open(filename_out + ".log", "w")
#         Calib_Log_File.write("# " + str(self.Results.Scenario.shot) + os.linesep)
#         if(self.Results.Config.extra_output):
#             for time_index in range(len(self.Results.time[masked_timepoints])):
#                 Calib_Log_File.write("time =  " + "{0:1.2f}\t".format(self.Results.time[masked_timepoints][time_index]) + " s" + os.linesep)
#                 Calib_Log_File.write("f [Ghz]    rho_cold  c [keV / Vs] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
#                 ch_cnt = len(freq)
#                 for ch in range(ch_cnt):
#                     Calib_Log_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
#                     for i in range(3):
#                         Calib_Log_File.write(" ")
#                     Calib_Log_File.write("{0: 1.3e}".format(self.Results.resonance["rhop_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch]))
#                     for i in range(4):
#                         Calib_Log_File.write(" ")
#                     Calib_Log_File.write("{0: 1.3e} ".format(calib_mat[time_index][ch ]))
#                     Calib_Log_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
#                                         self.Results.resonance["R_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"]== self.cur_diag.name][ch], \
#                                         self.Results.resonance["z_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch], \
#                                         self.Results.resonance["R_warm"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch], \
#                                         self.Results.resonance["z_warm"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch], \
#                                         self.Results.tau[masked_timepoints][time_index][self.Results.Scenario.ray_launch["diag_name"][masked_timepoints][time_index] == self.cur_diag.name][ch]) + os.linesep)
#             Calib_Log_File.flush()
#             Calib_Log_File.close()
#             Calib_File = open(filename_out + ".cal", "w")
#             Calib_File.write("# " + str(self.Results.Scenario.shot) + os.linesep)
#             Calib_File.write("f [Ghz]  c [keV / Vs] rel. std. dev [%] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
#             for ch in range(ch_cnt):
#                 Calib_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
#                 Calib_File.write("     {0: 1.3e}         {1: 2.2e} {2: 2.2e} ".format(calib[ch], rel_dev[ch], sys_dev[ch]))
#                 Calib_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
#                                   np.average(self.Results.resonance["R_cold"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   np.average(self.Results.resonance["z_cold"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   np.average(self.Results.resonance["R_warm"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   np.average(self.Results.resonance["z_warm"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   np.average(self.Results.tau[masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch]) + os.linesep)
#             Calib_File.flush()
#             Calib_File.close()
#         else:
#             for time_index in range(len(self.Results.time[masked_timepoints])):
#                 Calib_Log_File.write("time =  " + "{0:1.2f}\t".format(self.Results.time[masked_timepoints][time_index]) + " s" + os.linesep)
#                 Calib_Log_File.write("f [Ghz]    rho_cold  c [keV / Vs] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
#                 ch_cnt = len(freq)
#                 for ch in range(ch_cnt):
#                     Calib_Log_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
#                     for i in range(3):
#                         Calib_Log_File.write(" ")
#                     Calib_Log_File.write("{0: 1.3e}".format(self.Results.resonance["rhop_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch]))
#                     for i in range(4):
#                         Calib_Log_File.write(" ")
#                     Calib_Log_File.write("{0: 1.3e} ".format(calib_mat[time_index][ch]))
#                     Calib_Log_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
#                                         self.Results.resonance["R_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch], \
#                                         self.Results.resonance["z_cold"][masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch], \
#                                         - 1.e0, \
#                                         - 1.e0, \
#                                         self.Results.tau[masked_timepoints][time_index][self.Results.Scenario.ray_launch[masked_timepoints][time_index]["diag_name"] == self.cur_diag.name][ch]) + os.linesep)
#             Calib_Log_File.flush()
#             Calib_Log_File.close()
#             Calib_File = open(filename_out + ".cal", "w")
#             Calib_File.write("# " + str(self.Results.Scenario.shot) + os.linesep)
#             Calib_File.write("f [Ghz]  c [keV / Vs] rel. std. dev [%] sys. dev [%] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
#             for ch in range(ch_cnt):
#                 Calib_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
#                 Calib_File.write("     {0: 1.3e}         {1: 2.2e} {2: 2.2e} ".format(calib[ch], rel_dev[ch], sys_dev[ch]))
#                 Calib_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
#                                   np.average(self.Results.resonance["R_cold"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   np.average(self.Results.resonance["z_cold"][masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch], \
#                                   - 1.e0, \
#                                   - 1.e0, \
#                                   np.average(self.Results.tau[masked_timepoints], axis=0)[self.Results.Scenario.ray_launch[masked_timepoints][0]["diag_name"] == self.cur_diag.name][ch]) + os.linesep)
#             Calib_File.flush()
#             Calib_File.close()

    def OnPlotAvg(self, evt):
        if("avg" not in self.plotted_time_points):
            if(self.cur_diag.name not in list(self.Results.calib)):
                print("Error: No calibration data available - calibrate first")
                return
            freq = self.Results.Scenario.ray_launch[0]["f"][self.Results.Scenario.ray_launch[0]["diag_name"] == self.last_used_diag_name] * 1.e-9
            self.fig, self.fig_extra = self.pc_obj.diag_calib_avg(self.cur_diag, freq, \
                                       self.Results.calib[self.cur_diag.name], self.Results.rel_dev[self.cur_diag.name], \
                                       "avg")
            self.plotted_time_points.append("avg")
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)

    def OnResetPlot(self, evt):
        self.pc_obj.reset(True)
        self.plotted_time_points = []
        self.fig.clf()
        self.canvas.draw()


    def OnPlotUsedTimePoint(self, evt):
        sel = self.used_list.GetSelections()
        if(len(sel) == 0):
            return
        for i_sel in sel:
            time = float(self.used_list.GetString(i_sel))
            if(time not in self.plotted_time_points):
                if(self.cur_diag.name not in list(self.Results.calib_mat)):
                    print("Error: No calibration data available - calibrate first")
                    return
                self.plotted_time_points.append(time)
                index = np.argmin(np.abs(self.Results.time - time))
                freq = self.Results.Scenario.ray_launch[index]["f"][self.Results.Scenario.ray_launch[index]["diag_name"] == self.last_used_diag_name] * 1.e-9
                self.fig, self.fig_extra = self.pc_obj.diag_calib_slice(self.cur_diag, freq, \
                                           self.Results.calib_mat[self.cur_diag.name][index], self.Results.std_dev_mat[self.cur_diag.name][index], \
                                           "t = {0:2.4f} s".format(self.Results.time[index]))
                self.canvas.draw()
                evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
                self.GetEventHandler().ProcessEvent(evt)

    def OnPlotUnUsedTimePoint(self, evt):
        sel = self.unused_list.GetSelections()
        if(len(sel) == 0):
            return
        for i_sel in sel:
            time = float(self.unused_list.GetString(i_sel))
            if(time not in self.plotted_time_points):
                if(self.cur_diag.diag not in list(self.Results.calib_mat)):
                    print("Error: No calibration data available - calibrate first")
                    return
                self.plotted_time_points.append(time)
                index = np.argmin(np.abs(self.Results.time - time))
                freq = self.Results.Scenario.ray_launch[index]["f"][self.Results.Sceario.ray_launch[index]["diag_name"] == self.last_used_diag_name] * 1.e-9
                self.fig, self.fig_extra = self.pc_obj.diag_calib_slice(self.cur_diag, freq, \
                                           self.Results.calib_mat[self.cur_diag.name][index], self.Results.std_dev_mat[self.cur_diag.name][index], \
                                           "t = {0:2.4f} s".format(self.Results.time[index]))
                self.canvas.draw()
                evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
                self.GetEventHandler().ProcessEvent(evt)

class CalibEvolutionPanel(wx.Panel):
    def __init__(self, parent, working_dir):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.working_dir = working_dir
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(7.5, 8.5), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(9, 6.5), tight_layout=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.results = None
        self.diagnostic = None
        self.ch_cnt = 0
        self.Bind(wx.EVT_ENTER_WINDOW, self.ChangeCursor)
        self.canvas.draw()
        self.pc_obj = plotting_core(self.fig, self.dummy_fig, False)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        tw, th = self.plot_toolbar.GetSize().Get()
        fw, fh = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.button_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.load_shots_button = wx.Button(self, 0, "Load ECRad data sets")
        self.load_shots_button.Bind(wx.EVT_BUTTON, self.OnOpenOldFiles)
        self.button_sizer.Add(self.load_shots_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.plot_button = wx.Button(self, 0, "Plot selected sets")
        self.plot_button.Bind(wx.EVT_BUTTON, self.OnPlot)
        self.button_sizer.Add(self.plot_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        # self.button_sizer.AddStretchSpacer(prop = 10)
        self.clear_results_button = wx.Button(self, 0, "Clear all sets")
        self.clear_results_button.Bind(wx.EVT_BUTTON, self.OnClearAllResults)
        self.button_sizer.Add(self.clear_results_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.button_ctrl_sizer.Add(self.button_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.used = []
        self.unused = []
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used shots")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.shotlist = []
        self.ECRad_result_list = []
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused shots")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_shot_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.select_shot_sizer.Add(self.select_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.button_ctrl_sizer, 0, wx.ALL | \
                wx.EXPAND, 5)
        self.button_ctrl_sizer.Add(self.select_shot_sizer, 1, \
                wx.EXPAND, 0)
        self.channel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.diagnostic_tc = simple_label_tc(self, "diagnostic", "CTA", "string")
        self.channel_sizer.Add(self.diagnostic_tc, 0, wx.ALL | wx.ALIGN_CENTER)
        self.channel_label_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ch_label = wx.StaticText(self, wx.ID_ANY, "Channel to be plotted")
        self.ch_ch = wx.Choice(self, wx.ID_ANY)
        self.channel_label_sizer.Add(self.ch_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.channel_label_sizer.Add(self.ch_ch, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.channel_sizer.Add(self.channel_label_sizer, 0, wx.ALL | wx.ALIGN_CENTER)
        self.button_ctrl_sizer.Add(self.channel_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.adv_plot_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.plot_button_Trad = wx.Button(self, 0, "Plot againt Trad")
        self.plot_button_Trad.Bind(wx.EVT_BUTTON, self.OnPlotTradvsSignal)
        self.plot_button_launch = wx.Button(self, 0, "Plot againt launch")
        self.plot_button_launch.Bind(wx.EVT_BUTTON, self.OnPlotCalibvsLaunch)
        self.plot_button_comp = wx.Button(self, 0, "Meas. vs. expected")
        self.plot_button_comp.Bind(wx.EVT_BUTTON, self.OnPlotDiagVsTrad)
        self.adv_plot_sizer.Add(self.plot_button_Trad, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.adv_plot_sizer.Add(self.plot_button_launch, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Trad_comp_sizer.Add(self.plot_button_comp, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.ECE_diag_exp_tc = simple_label_tc(self, "exp", "AUGD", "string")
        self.ECE_diag_diag_tc = simple_label_tc(self, "diag", "RMD", "string")
        self.ECE_diag_ed_tc = simple_label_tc(self, "ed", 0, "integer")
        self.Trad_comp_sizer.Add(self.ECE_diag_exp_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer.Add(self.ECE_diag_diag_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer.Add(self.ECE_diag_ed_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.button_ctrl_sizer.Add(self.adv_plot_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.button_ctrl_sizer.Add(self.Trad_comp_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.sizer.Add(self.canvas_sizer, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.SetClientSize(self.GetEffectiveMinSize())

    def OnAddSelection(self, evt):
        sel = self.unused_list.GetSelections()
        for i_sel in sel:
            string = self.unused_list.GetString(i_sel)
            self.used.append(self.unused.pop(self.unused.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnRemoveSelection(self, evt):
        sel = self.used_list.GetSelections()
        for i_sel in sel:
            string = self.used_list.GetString(i_sel)
            self.unused.append(self.used.pop(self.used.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnOpenOldFiles(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading data - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation(s)", \
            defaultDir=self.working_dir, \
            wildcard=('Matlab files (*.mat)|*.mat'),
            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if(dlg.ShowModal() == wx.ID_OK):
            self.diagnostic = self.diagnostic_tc.GetValue()
            paths = dlg.GetPaths()
            dlg.Destroy()
            new_results = []
            for path in paths:
                new_results.append(ECRadResults())
                if(new_results[-1].from_mat_file(path) == False):
                    print("Failed to load file at " + path)
                    continue
                if(self.diagnostic not in list(new_results[-1].calib)):
                    print("No calibration for " + self.diagnostic + " in " + path)
                    print("Available Calibrations: ", list(new_results[-1].calib))
                    del(new_results[-1])
                    continue
                if(len(new_results[-1].time[new_results[-1].masked_time_points[self.diagnostic]]) < 2):
                    print(path + " contains only a single time point with a calibration")
                    print("At least two calibration time points are required for these plots")
                    del(new_results[-1])
                    continue
#                elif("ed{0:d}".format(new_results[-1].edition) not in path):
#                    print("Edition in .mat file does not match filename - distributing new edition according to filename")
#                    new_results[-1].edition = 0
#                    while("ed{0:d}".format(new_results[-1].edition) not in path):
#                        new_results[-1].edition += 1
                # it would be nice to have also Te in this plot, but the mapping is a pain
#                new_results[-1].time, new_results[-1].Scenario.plasma_dict = load_IDA_data(self.Results.Scenario.shot, \
#                                    new_results[-1].time, self.Results.Scenario.IDA_exp, self.Results.Scenario.IDA_ed)
            if(len(new_results) == 0):
                print("No valid calibrations found")
                return
            if(len(self.ECRad_result_list) == 0):
                self.ECRad_result_list = new_results
                self.shotlist = []
                self.editionlist = []
                ishot = 0
                try:
                    self.ch_cnt = len(self.ECRad_result_list[ishot].calib[self.diagnostic])
                except KeyError:
                    print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                      self.ECRad_result_list[ishot].Scenario.shot, self.ECRad_result_list[ishot].edition))
                    print("Available diagnostics: ", list(self.ECRad_result_list[ishot].calib))
                    return
                if(self.ch_cnt == 0):
                    while(self.ch_cnt == 0):
                        ishot += 1
                        if(ishot == len(self.ECRad_result_list)):
                            print("Error: None of the selected shots holds any information for your selected diagnostic")
                            print("Please double check that the desired diagnostic has been selected")
                            self.ECRad_result_list = []
                            return
                        try:
                            self.ch_cnt = len(self.ECRad_result_list[ishot].calib[self.diagnostic])
                        except KeyError:
                            print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                              self.ECRad_result_list[ishot].Scenario.shot, self.ECRad_result_list[ishot].edition))
                cur_ch_cnt = 0
                for result in self.ECRad_result_list[ishot:len(self.ECRad_result_list)]:
                    try:
                        cur_ch_cnt = len(result.calib[self.diagnostic])
                        if(self.ch_cnt != cur_ch_cnt):
                            print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                          result.Scenario.shot, result.edition))
                            print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                        else:
                            self.shotlist.append(str(result.Scenario.shot))
                            self.editionlist.append(str(result.edition))
                    except KeyError:
                        print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                          result.Scenario.shot, self.ECRad_result_list[ishot].edition))
                for i in range(len(self.shotlist)):
                    self.used.append(self.shotlist[i] + "_ed_" + self.editionlist[i])
                self.used_list.AppendItems(self.used)
                self.ch_ch.AppendItems(list(map(str, range(1, self.ch_cnt + 1))))
            else:
                for new_result in new_results:
                    new_result_replaced_old = False
                    for index in range(len(self.ECRad_result_list)):
                        if(new_result.Scenario.shot == self.ECRad_result_list[index].Scenario.shot and new_result.edition == self.ECRad_result_list[index].edition):
                            new_result_replaced_old = True
                            try:
                                cur_ch_cnt = len(new_result.calib[self.diagnostic])
                                if(self.ch_cnt != cur_ch_cnt):
                                    print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                                  new_result.Scenario.shot, new_result.edition))
                                    print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                                else:
                                    self.ECRad_result_list[index] = new_result
                            except KeyError:
                                print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                                  new_result.Scenario.shot, new_result.edition))
                            break
                    if(not new_result_replaced_old):
                        try:
                            cur_ch_cnt = len(new_result.calib[self.diagnostic])
                            if(self.ch_cnt != cur_ch_cnt):
                                print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                              new_result.Scenario.shot, new_result.edition))
                                print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                            else:
                                self.ECRad_result_list.append(new_result)
                                self.shotlist.append(str(self.ECRad_result_list[-1].Scenario.shot))
                                self.editionlist.append(str(self.ECRad_result_list[-1].edition))
                                self.used.append(self.shotlist[-1] + "_ed_" + self.editionlist[-1])
                                self.used_list.Clear()
                                self.used = list(set(self.used))
                                self.used.sort()
                                self.used_list.AppendItems(self.used)
                        except KeyError:
                            print("Error!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                              new_result.Scenario.shot, new_result.edition))
            if(len(self.ch_ch.GetItems()) > 0):
                self.ch_ch.Select(0)


    def OnPlot(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        for result in self.ECRad_result_list:
            if(str(result.Scenario.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        if(globalsettings.AUG):
            cur_result = used_results[0]
            from shotfile_handling_AUG import get_shot_heating
            heating_array = get_shot_heating(cur_result.Scenario.shot)
            for heating in heating_array:
                heating_mask = np.logical_and(heating[0] >= np.min(result.time[result.masked_time_points[self.diagnostic]]), \
                                                  heating[0] <= np.max(result.time[result.masked_time_points[self.diagnostic]]))
                heating[0], heating[1] = moving_average(heating[0][heating_mask], heating[1][heating_mask], 5.e-2)
            ne = cur_result.Scenario.plasma_dict["ne"].T[0][cur_result.masked_time_points[self.diagnostic]] # Central ne
            time_ne, ne = moving_average(cur_result.time[cur_result.masked_time_points[self.diagnostic]], ne, 6.e-2)
            self.fig = self.pc_obj.calib_evolution(self.diagnostic, ch, used_results, heating_array, time_ne, ne)
        else:
            self.fig = self.pc_obj.calib_evolution(self.diagnostic, ch, used_results)
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotTradvsSignal(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        if(self.diagnostic == "CTC" or self.diagnostic == "IEC" or self.diagnostic == "CTA"):
            try:
                beamline = self.ECRad_result_list[0].Scenario.used_diags_dict[self.diagnostic].beamline
            except KeyError:
                print("Failed to get beamliune - if this is an overwritten EXT diag calculation this is expected")
                beamline = 0
        else:
            beamline = 0
        if(beamline > 0):
            pol_ang_list = []
        print("The poloidal angle plot is disabled at the moment")
        beamline = -1
        for result in self.ECRad_result_list:
            if(str(result.Scenario.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
            if(beamline > 0):
                import get_ECRH_config
                gy = get_ECRH_config.get_ECRH_viewing_angles(result.Scenario.shot, beamline, self.ECRad_result_list[0].Scenario.used_diags_dict[self.diagnostic].base_freq_140)
                pol_ang = []
                for t in result.time:
                    pol_ang.append(gy.theta_pol[np.argmin(np.abs(gy.time - t))])
                pol_ang_list.append(np.array(pol_ang))
                del(get_ECRH_config)
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        time_list = []
        diag_data = []
        std_dev_data = []
        dummy_std_dev_calib = np.zeros(len(result.calib[self.diagnostic]))
        dummy_calib = np.zeros(len(result.calib[self.diagnostic]))
        dummy_calib[:] = 1.e0
        calib_diag = used_results[0].Scenario.used_diags_dict[self.diagnostic]
        popt_list = []
        for result in used_results:
            time_list.append(result.time)
            Trad = []
            for itime in range(len(result.time)):
                if(result.masked_time_points[self.diagnostic][itime]):
                    Trad.append(result.Trad[itime][result.Scenario.ray_launch[itime]["diag_name"]  == self.diagnostic])
            Trad = np.array(Trad)
            if(result.Config.extra_output):
                resonances = result.resonance["rhop_warm"]
            else:
                resonances = result.resonance["rhop_cold"]
            std_dev, data = get_data_calib(diag=calib_diag, shot=result.Scenario.shot, time=result.time[result.masked_time_points[self.diagnostic]], \
                                           eq_exp=result.Scenario.EQ_exp, eq_diag=result.Scenario.EQ_diag, eq_ed=result.Scenario.EQ_ed, \
                                           calib=dummy_calib, \
                                           std_dev_calib=dummy_std_dev_calib, \
                                           ext_resonances=resonances)
            diag_data.append(data[1].T[ch])
            std_dev_data.append(np.copy(std_dev[0].T[ch]))
            popt, perr = make_fit('linear', Trad.T[ch], \
                                  data[1].T[ch], std_dev[0].T[ch], \
                                  [0.0, 1.0 / np.mean(result.calib_mat[self.diagnostic].T[ch])])
            # Largest deviation of calibration coefficient from measurement minus standard deviation of the measurement
            systematic_error = np.sqrt(np.sum((1.0 / popt[1] - (Trad.T[ch] / \
                                                                data[1].T[ch])) ** 2) / \
                                       len(Trad.T[ch]))
            print("Pseudo systematic error [%] and systematic vs. statistical error ", np.abs(systematic_error * popt[1] * 100.0), \
                  np.abs(systematic_error / (perr[1] / popt[1] ** 2)))
            print("Inital relative error:", np.sqrt(perr[1] ** 2 / popt[1] ** 4) * popt[1])
            popt_list.append(popt)
            print("Fit result: U_0 [V], c [keV/V] / error")
            print("{0:1.4f}, {1:1.4f} / {2:1.4f} , {3:1.4f}".format(popt[0], 1.e0 / popt[1], perr[0], np.sqrt(perr[1] ** 2 / popt[1] ** 4)))
            print("Result from calib and std. dev.")
            print("{0:1.4f}, {1:1.4f}".format(result.calib[self.diagnostic][ch], result.rel_dev[self.diagnostic][ch] * result.calib[self.diagnostic][ch] / 100.0))
            Trad0 = popt[0] / popt[1]
            DeltaTrad0 = np.sqrt(perr[0] ** 2 / popt[1] ** 2 + perr[1] ** 2 * popt[0] ** 2 / popt[1] ** 4)
            print("Trad with zero signal and error [keV]:")
            print("{0:1.4f}, {1:1.4f}".format(Trad0, DeltaTrad0))
        if(beamline > 0):
            min_ang = np.inf
            max_ang = -np.inf
            for i in range(len(pol_ang_list)):
                if(np.max(pol_ang_list[i]) > max_ang):
                    max_ang = np.max(pol_ang_list[i])
                if(np.min(pol_ang_list[i]) < min_ang):
                    min_ang = np.min(pol_ang_list[i])
            if(max_ang - min_ang > 3):
                self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list, pol_ang_list)  # , diag_time_list, diag_data_list
            else:
                self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list)  # , diag_time_list, diag_data_list
        else:
            self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list)  # , diag_time_list, diag_data_list
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotCalibvsLaunch(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        if(self.diagnostic == "CTC" or self.diagnostic == "IEC" or self.diagnostic == "CTA"):
            beamline = self.ECRad_result_list[0].Scenario.used_diags_dict[self.diagnostic].beamline
        else:
            print("This plot is only sensible for steerable ECE!")
            return
        pol_ang_list = []
        for result in self.ECRad_result_list:
            if(str(result.Scenario.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
            gy = get_ECRH_viewing_angles(result.Scenario.shot, beamline, self.ECRad_result_list[0].Scenario.used_diags_dict[self.diagnostic].base_freq_140)
            pol_ang = []
            for t in result.time:
                pol_ang.append(gy.theta_pol[np.argmin(np.abs(gy.time - t))])
            pol_ang_list.append(np.array(pol_ang))
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
#        diag_time_list = []
#        diag_data_list = []
#        for result in self.ECRad_result_list:
#            diag_time, diag_data = get_diag_data_no_calib(result.used_diags_dict[self.diagnostic], self.Results.Scenario.shot, preview=True)
#            diag_time_list.append(diag_time)
#            diag_data_list.append(diag_data.T[ch])
        self.fig = self.pc_obj.calib_vs_launch(self.diagnostic, ch, used_results, pol_ang_list)  # , diag_time_list, diag_data_list
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotDiagVsTrad(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        for result in self.ECRad_result_list:
            if(str(result.Scenario.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        ECE_diag_exp = self.ECE_diag_exp_tc.GetValue()
        ECE_diag_diag = self.ECE_diag_diag_tc.GetValue()
        ECE_diag_ed = self.ECE_diag_ed_tc.GetValue()
        time_list = []
        calib_diag_trace = []
        Trad_trace = []
        ECE_diag_trace = []
        ECE_diag = Diag("ECE", ECE_diag_exp, ECE_diag_diag, ECE_diag_ed)
        calib_diag = used_results[0].Scenario.used_diags_dict[self.diagnostic]
        for result in used_results:
            Trad = []
            for itime in range(len(result.time)):
                if(result.masked_time_points[self.diagnostic][itime]):
                    Trad.append(result.Trad[itime][result.Scenario.ray_launch[itime]["diag_name"]  == self.diagnostic])
            Trad = np.array(Trad)
            Trad_trace.append(Trad)
            time_list.append(result.time[result.masked_time_points[self.diagnostic]])
            calib_diag_trace.append(np.zeros((len(result.time[result.masked_time_points[self.diagnostic]]), \
                                              len(result.time[result.masked_time_points[self.diagnostic]]))))
            ECE_diag_trace.append(np.zeros((len(result.time[result.masked_time_points[self.diagnostic]]), \
                                            len(result.time[result.masked_time_points[self.diagnostic]]))))
            if(result.Config.extra_output):
                resonances = result.resonance["rhop_warm"]
            else:
                resonances = result.resonance["rhop_cold"]
            std_dev, data = get_data_calib(diag=calib_diag, shot=result.Scenario.shot, \
                                           time=result.time[result.masked_time_points[self.diagnostic]], \
                                           eq_exp=result.Scenario.EQ_exp, \
                                           eq_diag=result.Scenario.EQ_diag, \
                                           eq_ed=result.Scenario.EQ_ed, \
                                           calib=result.calib[self.diagnostic], \
                                           std_dev_calib=result.rel_dev[self.diagnostic] * result.calib[self.diagnostic] / 100.0, \
                                           ext_resonances=resonances)
            calib_diag_trace[-1][0][:] = data[1].T[ch]
            calib_diag_trace[-1][1][:] = std_dev[0].T[ch] + std_dev[1].T[ch]
            std_dev, data = get_data_calib(diag=ECE_diag, shot=result.Scenario.shot, \
                                           time=result.time[result.masked_time_points[self.diagnostic]], \
                                           eq_exp=result.Scenario.EQ_exp, \
                                           eq_diag=result.Scenario.EQ_diag, \
                                           eq_ed=result.Scenario.EQ_ed)
            # print(data[0], data[1])
            for i in range(len(result.time[result.masked_time_points[self.diagnostic]])):
                rhop_calib_diag = resonances[i][ch]
                ECE_diag_trace[-1][0][i] = data[1][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))]  # eV -> keV # ECE channel closest to warm resonance
                # print("res", rhop_calib_diag, data[0][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))])
                ECE_diag_trace[-1][1][i] = std_dev[0][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))]  # eV -> keV
#        diag_time_list = []
#        diag_data_list = []
#        for result in self.ECRad_result_list:
#            diag_time, diag_data = get_diag_data_no_calib(result.Scenario.used_diags_dict[self.diagnostic], self.Results.Scenario.shot, preview=True)
#            diag_time_list.append(diag_time)
#            diag_data_list.append(diag_data.T[ch])
        self.fig = self.pc_obj.Trad_vs_diag(self.diagnostic, ch, time_list, calib_diag_trace, Trad_trace, ECE_diag_trace)
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnClearAllResults(self, evt):
        self.ECRad_result_list = []
        self.shotlist = []
        self.used_list.Clear()
        self.unused_list.Clear()
        self.used = []
        self.unused = []
        self.ch_ch.Clear()

    def ChangeCursor(self, event):
        if(globalsettings.Phoenix):
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)
