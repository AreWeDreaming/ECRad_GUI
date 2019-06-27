'''
Created on Apr 3, 2019

@author: sdenk
'''

from GlobalSettings import globalsettings
import wx
import os
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row
from wxEvents import *
from plotting_configuration import *
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from plotting_core import plotting_core
if(globalsettings.AUG):
    from shotfile_handling_AUG import shotfile_exists, get_data_calib, AUG_profile_diags,\
                                      load_IDA_data, get_Thomson_data
else:
    print("AUG shotfile system inaccessible -> Cannot plot diagnostic data!")                                
if(globalsettings.Phoenix):
    from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
else:
    from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx
import numpy as np
from TB_communication import make_all_TORBEAM_rays_thread, Ray
from ECRad_GUI_Thread import WorkerThread
from equilibrium_utils import EQDataExt as EQData
from Diags import Diag
from ECRad_GUI_Diagnostic import Diagnostic
from ECRad_Results import ECRadResults
from BDOP_3D import make_3DBDOP_cut_GUI
from Diag_efficiency import diag_weight

class PlotPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.controlplotsizer = wx.BoxSizer(wx.VERTICAL)
        self.Results = None
        self.FigureControlPanel = FigureBook(self)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_THREAD_FINISHED, self.OnThreadFinished)
        self.Bind(EVT_DIAGNOSTICS_LOADED, self.OnDiagDataLoaded)
        self.Bind(EVT_OTHER_RESULTS_LOADED, self.OnOtherResultsLoaded)
        self.controlgrid = wx.BoxSizer(wx.HORIZONTAL)
        self.controlgrid2 = wx.BoxSizer(wx.HORIZONTAL)
        self.plot_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.plot_choice_label = wx.StaticText(self, wx.ID_ANY, "Plot")
        self.plot_choice = wx.Choice(self, wx.ID_ANY)
        self.plot_choice.Append("Trad")
        self.plot_choice.Append("T")
        self.plot_choice.Append("Trad mode")
        self.plot_choice.Append("T mode")
        self.plot_choice.Append("BPD")
        self.plot_choice.Append("Ray")
        # self.plot_choice.Append("Ray_H_N")
        self.plot_choice.Append("Rz res.")
        self.plot_choice.Append("Rz res. w. rays")
        self.plot_choice.Append("3D Birthplace distribution")
        self.plot_choice.Append("Momentum space sensitivity")
        self.plot_choice.Select(0)
        self.plot_choice.Bind(wx.EVT_CHOICE, self.OnNewPlotChoice)
        self.plot_choice_sizer.Add(self.plot_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.plot_choice_sizer.Add(self.plot_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.plot_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.AddPlotButton = wx.Button(self, wx.ID_ANY, 'Add plot')
        self.AddPlotButton.Bind(wx.EVT_BUTTON, self.OnPlot)
        self.ClearButton = wx.Button(self, wx.ID_ANY, 'Clear plots')
        self.Bind(wx.EVT_BUTTON, self.OnClear, self.ClearButton)
        self.MakeTorbeamRaysButton = wx.Button(self, wx.ID_ANY, "Make TORBEAM Rays")
        self.Bind(wx.EVT_BUTTON, self.OnMakeTORBEAMRays, self.MakeTorbeamRaysButton)
        self.time_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.time_choice_label = wx.StaticText(self, wx.ID_ANY, "time")
        self.time_choice = wx.Choice(self, wx.ID_ANY)
        self.time_choice_sizer.Add(self.time_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.time_choice_sizer.Add(self.time_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.time_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.ch_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ch_choice_label = wx.StaticText(self, wx.ID_ANY, "Channel")
        self.ch_choice = wx.Choice(self, wx.ID_ANY)
        self.ch_choice.Bind(wx.EVT_CHOICE, self.OnUpdateChtooltip)
        self.ch_choice_sizer.Add(self.ch_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.ch_choice_sizer.Add(self.ch_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.ch_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.mode_cb = simple_label_cb(self, "X-mode", True)
        self.controlgrid.Add(self.mode_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.alt_model_cb = simple_label_cb(self, "show both models", True)
        self.tau_threshhold_tc = simple_label_tc(self, "lower boundary for tau", 0.0, "real")
        self.eq_aspect_ratio_cb = simple_label_cb(self, "Equal aspect ratio", True)
        self.controlgrid.Add(self.alt_model_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.AddPlotButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.ClearButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.MakeTorbeamRaysButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.tau_threshhold_tc, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.eq_aspect_ratio_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlplotsizer.Add(self.controlgrid, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.controlplotsizer.Add(self.controlgrid2, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.diag_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.controlplotsizer.Add(self.FigureControlPanel, 1, wx.ALL | wx.EXPAND, 10)
        self.diag_box_sizer = wx.BoxSizer(wx.VERTICAL)
        if(globalsettings.AUG):
            self.load_diag_data_button = wx.Button(self, wx.ID_ANY, "Load diagnostic data")
            self.load_diag_data_button.Bind(wx.EVT_BUTTON, self.OnLoadDiagData)
            self.diag_box_sizer.Add(self.load_diag_data_button, 0, wx.ALL | wx.EXPAND, 5)
            self.diag_text = wx.StaticText(self, wx.ID_ANY, "Select diagnostics to include in plot")
            self.diag_box_sizer.Add(self.diag_text, 0, wx.ALL | wx.TOP, 5)
            self.diag_box = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE, size=(100,100))
            self.diag_box_sizer.Add(self.diag_box, 0, wx.ALL | wx.EXPAND, 5)
        self.load_other_results_button = wx.Button(self, wx.ID_ANY, "Load other results")
        self.load_other_results_button.Bind(wx.EVT_BUTTON, self.OnLoadOtherResults)
        self.diag_box_sizer.Add(self.load_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.other_result_text = wx.StaticText(self, wx.ID_ANY, "Select result(s) for comparison")
        self.diag_box_sizer.Add(self.other_result_text, 0, wx.ALL | wx.TOP, 5)
        self.other_result_box = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE, size=(100,200))
        self.diag_box_sizer.Add(self.other_result_box, 0, wx.ALL | wx.EXPAND, 5)
        self.clear_other_results_button = wx.Button(self, wx.ID_ANY, "Clear other results")
        self.clear_other_results_button.Bind(wx.EVT_BUTTON, self.OnClearOtherResults)
        self.diag_box_sizer.Add(self.clear_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.diag_sizer.Add(self.diag_box_sizer, 0, wx.ALL | wx.LEFT, 10)
        self.sizer.Add(self.controlplotsizer, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.diag_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.FigureControlPanel.Show(True)
        self.cur_selected_index = 0
        self.diag_data = {}
        self.compare_data = {}

    def OnClearOtherResults(self, evt):
        self.other_result_box.Clear()
        self.compare_data = {}
        self.load_other_results_button.Enable()

    def OnNewPlotChoice(self, evt):
        plot_type = self.plot_choice.GetStringSelection()
        self.other_result_box.Clear()
        if(plot_type in  self.compare_data.keys()):        
            other_results = self.compare_data[plot_type].keys()
        elif(plot_type=="Ray" and "RayXRz" in self.compare_data.keys()):
            other_results = self.compare_data["RayXRz"].keys()
        else:
            return
        other_results.sort()
        self.other_result_box.AppendItems(other_results)
        self.other_result_box.Layout()

    def OnUpdate(self, evt):
        self.Results = evt.Results
        if(len(self.Results.time) > 0):
            self.time_choice.Clear()
            self.time_choice.AppendItems(self.Results.time.astype("|S7"))
            self.time_choice.Select(0)
            self.ch_choice.Clear()
            self.ch_choice.AppendItems(np.array(range(1, len(self.Results.Trad.T) + 1)).astype("|S4"))
            self.ch_choice.Select(0)
            if(globalsettings.AUG):
                self.diag_data = {}
                self.diag_box.Clear()
                self.load_diag_data_button.Enable()
            self.load_other_results_button.Enable()

    def OnUpdateChtooltip(self, evt):
        if(len(self.Results.time) > 0):
            time = float(self.time_choice.GetStringSelection())
            itime = np.argmin(np.abs(self.Results.time - time))
            ch = int(self.ch_choice.GetStringSelection()) - 1
            res = self.Results.resonance["rhop_cold"][itime][ch]
            if(globalsettings.Phoenix):
                self.ch_choice.SetToolTip(r"rhopol = {0:1.3f}".format(res))
            else:
                self.ch_choice.SetToolTipString(r"rhopol = {0:1.3f}".format(res))

    def OnPlot(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.time_choice.GetItems()) == 0):
            print("NO time points available!")
            return
        plot_type = self.plot_choice.GetStringSelection()
        time = float(self.time_choice.GetStringSelection())
        ch = int(self.ch_choice.GetStringSelection()) - 1  # index - not channel number
        mode = self.mode_cb.GetValue()
        alt_model = self.alt_model_cb.GetValue()
        tau_threshhold = self.tau_threshhold_tc.GetValue()
        eq_aspect_ratio = self.eq_aspect_ratio_cb.GetValue()
        if(globalsettings.AUG):
            diag_data_selected = np.array(self.diag_box.GetItems())[self.diag_box.GetSelections()]
        else:
            diag_data_selected = np.array([] )
        compare_data_selected = np.array(self.other_result_box.GetItems())[self.other_result_box.GetSelections()]
        self.FigureControlPanel.AddPlot(plot_type, self.Results.Config, self.Results, self.diag_data, diag_data_selected, self.compare_data, compare_data_selected, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio)
        self.Layout()

    def OnMakeTORBEAMRays(self, evt):
        try:
            if(len(self.Results.time) == 0):
                print("No .mat loaded")
                return
        except AttributeError:
            print("No .mat loaded")
            return
        time = float(self.time_choice.GetStringSelection())
        if(self.mode_cb.GetValue()):
            mode = -1
            self.cur_mode_str = "X"
        else:
            mode = +1
            self.cur_mode_str = "O"
        self.cur_selected_index = np.argmin(np.abs(self.Results.time - time))
        print("Calculating rays with TORBEAM hold on")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Calculating rays with TORBEAM hold on')
        self.GetEventHandler().ProcessEvent(evt)
        wt = WorkerThread(make_all_TORBEAM_rays_thread, [self.Results.Config.working_dir, \
                          self.Results.Scenario.shot, time, self.Results.Scenario.plasma_dict["eq_exp"], \
                          self.Results.Scenario.plasma_dict["eq_diag"], self.Results.Scenario.plasma_dict["eq_ed"], \
                          self.Results.ray_launch, self.cur_selected_index, mode, self.Results.Scenario.plasma_dict, \
                          self, self.Results.Config.bt_vac_correction, self.Results.Config.N_ray])

    def OnThreadFinished(self, evt):
        print("Updating ray information")
        ray_path = os.path.join(self.Results.Config.working_dir, "ecfm_data", "ray")
        if("x" + self.cur_mode_str + "tb" in self.Results.ray.keys()):
            for channel in range(len(self.Results.ray["x" + self.cur_mode_str][self.cur_selected_index])):
                TBRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_R{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                TBXRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_x{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                self.Results.ray["x" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBXRay_file.T[0] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBXRay_file.T[1] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBRay_file.T[0] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBRay_file.T[1] / 100.0)
                self.Results.ray["x" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBXRay_file.T[2] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBXRay_file.T[3] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBRay_file.T[2] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBRay_file.T[3] / 100.0)
                self.Results.ray["x" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBXRay_file.T[4] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBXRay_file.T[5] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBRay_file.T[4] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBRay_file.T[5] / 100.0)
        else:
            self.Results.ray["x" + self.cur_mode_str + "tb"] = []
            self.Results.ray["y" + self.cur_mode_str + "tb"] = []
            self.Results.ray["R" + self.cur_mode_str + "tb"] = []
            self.Results.ray["z" + self.cur_mode_str + "tb"] = []
            self.Results.ray["x" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["y" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["R" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["z" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["x" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["y" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["R" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["z" + self.cur_mode_str + "tbp2"] = []
            for i in range(len(self.Results.time)):
                self.Results.ray["x" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["x" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["x" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tbp2"].append([])
                if(i == self.cur_selected_index):
                    for channel in range(len(self.Results.ray["x" + self.cur_mode_str][i])):
                        TBRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_R{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                        TBXRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_x{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                        self.Results.ray["x" + self.cur_mode_str + "tb"][i].append(TBXRay_file.T[0] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tb"][i].append(TBXRay_file.T[1] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tb"][i].append(TBRay_file.T[0] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tb"][i].append(TBRay_file.T[1] / 100.0)
                        self.Results.ray["x" + self.cur_mode_str + "tbp1"][i].append(TBXRay_file.T[2] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tbp1"][i].append(TBXRay_file.T[3] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tbp1"][i].append(TBRay_file.T[2] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tbp1"][i].append(TBRay_file.T[3] / 100.0)
                        self.Results.ray["x" + self.cur_mode_str + "tbp2"][i].append(TBXRay_file.T[4] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tbp2"][i].append(TBXRay_file.T[5] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tbp2"][i].append(TBRay_file.T[4] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tbp2"][i].append(TBRay_file.T[5] / 100.0)

    def OnClear(self, evt):
        self.FigureControlPanel.ClearFigureBook()

    def OnLoadDiagData(self, evt):
        if(self.Results is None):
            print("No results yet!")
        if(self.Results.Scenario.data_source != "aug_database"):
            print("Sorry data load from external data is not yet implemented")
            mdict = None
            return
        else:
            diag_dict = {} # Important here we use Diag.diag as identified and not Diag.name
            # Transfer the individual entriesof used_diag:dig into diag_dict
            for key in self.Results.Scenario.used_diags_dict.keys():
                if(shotfile_exists(self.Results.Scenario.shot, self.Results.Scenario.used_diags_dict[key])):
                    diag_dict[self.Results.Scenario.used_diags_dict[key].diag] = self.Results.Scenario.used_diags_dict[key]
            for key in AUG_profile_diags:
                if(key in diag_dict.keys()):
                    continue # Already got it
                if(key == "IDA"):
                    # Use the currently used Scenario for IDA
                    diag = Diag("IDA", self.Results.Scenario.IDA_exp, "IDA", self.Results.Scenario.IDA_ed)
                else:
                    diag = Diag(key, "AUGD", key, 0)
                if(shotfile_exists(self.Results.Scenario.shot, diag)):
                    diag_dict[key] = diag
        avail_diag_list = diag_dict.keys()
        avail_diag_list.sort()
        diag_select_dialog = DiagSelectDialog(self, avail_diag_list)
        if(diag_select_dialog.ShowModal() == True):
            print()
            for key in diag_dict.keys():
                if(key not in diag_select_dialog.used_list.GetItems()):
                    del(diag_dict[key])
            diag_select_dialog.Destroy()
            if(len(diag_dict.keys()) == 0):
                return
            for key in diag_dict.keys():
                if(diag_dict[key].name in ["CTA", "CTC", "IEC", "ECN", "ECO", "ECI"] and \
                   key not in self.Results.calib.keys()):
                    # Uncalibrated diagnostic and no calibration in result file -> Ask user to load data
                    if wx.MessageBox("No calibration data for " + key + "\n Load calibration from file?", "Load calibration?",
                                     wx.ICON_QUESTION | wx.YES_NO, self) == wx.NO:
                        del(diag_dict[key])
                        continue
                    while True:
                        fileDialog=wx.FileDialog(self, "Open file with calibration for " + key, \
                                                 defaultDir = self.Results.Config.working_dir, \
                                                 wildcard="matlab files (*.mat)|*.mat",
                                                 style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                        if(fileDialog.ShowModal() == wx.ID_CANCEL):
                            del(diag_dict[key])
                            break
                        else:
                            pathname = fileDialog.GetPath()
                            fileDialog.Destroy()
                            result_with_calib = ECRadResults()
                            try:
                                result_with_calib.from_mat_file(pathname)
                            except IOError as e:
                                print("Failed to load calibration file")
                                print("Reason: ", e)
                                if wx.MessageBox("Failed to load!\n Select other file?", "Different file?",
                                     wx.ICON_QUESTION | wx.YES_NO, self) == wx.NO:
                                    del(diag_dict[key])
                                    break
                            try:
                                self.Results.calib[key] = result_with_calib.calib[key]
                                self.Results.rel_dev[key] = result_with_calib.rel_dev[key]
                                self.Results.sys_dev[key] = result_with_calib.sys_dev[key]
                                break
                            except KeyError:
                                print("No calib for selected")
                                if wx.MessageBox("No calibration for " + key + " in selected file\n Select other file?", "Different file?",
                                     wx.ICON_QUESTION | wx.YES_NO, self) == wx.NO:
                                    del(diag_dict[key])
                                    break
                                else:
                                    continue
            if(len(diag_dict.keys()) == 0):
                return
            print("Now loading diag data -- this will take a moment")
            wt = WorkerThread(self.get_diag_data, [self.Results, diag_dict])
            self.load_diag_data_button.Disable()
        else:
            diag_select_dialog.Destroy()
            return
            
    def get_diag_data(self, args):
        Results = args[0]
        diag_dict = args[1]
        temp_diag_data = {}
        try:
            for key in diag_dict.keys():
                if(diag_dict[key].name in Results.Scenario.used_diags_dict.keys()):
                    ext_resonances = []
                    for itime in range(len(Results.time)):
                        diag_mask = Results.Scenario.ray_launch[itime]["diag_name"] == diag_dict[key].name
                        ext_resonances.append(Results.resonance["rhop_cold"][itime][diag_mask])
                    ext_resonances = np.array(ext_resonances)
                else:
                    ext_resonances = None
                if(diag_dict[key].name in Results.calib.keys()):
                    #Cross calibrated diagnostic
                    calib = Results.calib[diag_dict[key].name]
                    rel_dev_calib= Results.rel_dev[diag_dict[key].name] # Percent!!
                    sys_dev_calib=Results.sys_dev[diag_dict[key].name]
                    unc, prof = get_data_calib(diag_dict[key], shot=Results.Scenario.shot, time = Results.time, ext_resonances = ext_resonances,
                                               calib=calib, std_dev_calib=rel_dev_calib * np.abs(calib) / 1.e2, \
                                               sys_dev_calib=sys_dev_calib)
                    temp_diag_data[diag_dict[key].name] = Diagnostic(diag_dict[key])
                    temp_diag_data[diag_dict[key].name].insert_data(prof[0], prof[1], unc[0], unc[1])
                elif(key in ["CEC", "RMD"]):
                    if(ext_resonances is None):
                        unc, prof = get_data_calib(diag_dict[key], shot=Results.Scenario.shot, time = Results.time, \
                                                   eq_exp=Results.Scenario.EQ_exp, \
                                                   eq_diag=Results.Scenario.EQ_diag, 
                                                   eq_ed=Results.Scenario.EQ_ed)
                        
                    else:
                        unc, prof = get_data_calib(diag_dict[key], shot=Results.Scenario.shot, time = Results.time, ext_resonances = ext_resonances)
                    temp_diag_data[diag_dict[key].name] = Diagnostic(diag_dict[key])
                    temp_diag_data[diag_dict[key].name].insert_data(prof[0], prof[1], unc[0], unc[1])
                elif(key is "IDA"):
                    IDA_dict = load_IDA_data(Results.Scenario.shot, timepoints= Results.time, \
                                             exp=self.Results.Scenario.IDA_exp, ed=self.Results.Scenario.IDA_ed)
                    temp_diag_data["ECE data in IDA"] = Diagnostic(diag_dict[key])
                    temp_diag_data["ECE data in IDA"].insert_data( IDA_dict["ECE_dat_rhop"], IDA_dict["ECE_dat"] * 1.e-3, 
                                                                                    IDA_dict["ECE_unc"] * 1.e-3, np.zeros(IDA_dict["ECE_dat_rhop"].shape))
                    temp_diag_data["ECE model in IDA"] = Diagnostic(diag_dict[key])
                    temp_diag_data["ECE model in IDA"].insert_data( IDA_dict["ECE_rhop"], IDA_dict["ECE_mod"] * 1.e-3, 
                                                                                    None, None)
                    temp_diag_data["IDA Te lower unc."] = Diagnostic(diag_dict[key],is_prof=True)
                    temp_diag_data["IDA Te lower unc."].insert_data( IDA_dict["rhop_prof"], IDA_dict["Te_up"] * 1.e-3, None, None)
                    temp_diag_data["IDA Te upper unc."] = Diagnostic(diag_dict[key],is_prof=True)
                    temp_diag_data["IDA Te upper unc."].insert_data(IDA_dict["rhop_prof"], IDA_dict["Te_low"] * 1.e-3, None, None)
                elif(key is "VTA"):
                    unc, prof = get_Thomson_data(Results.Scenario.shot, Results.time, diag_dict[key], \
                                     Te=True, edge=True, \
                                     EQ_exp=Results.Scenario.EQ_exp, \
                                     EQ_diag=Results.Scenario.EQ_diag, 
                                     EQ_ed=Results.Scenario.EQ_ed)
                    temp_diag_data["TS edge"] = Diagnostic(diag_dict[key])
                    temp_diag_data["TS edge"].insert_data(prof[0], prof[1] * 1.e-3, unc * 1.e-3, None)
                    unc, prof = get_Thomson_data(Results.Scenario.shot, Results.time, diag_dict[key], \
                                     Te=True, core=True, \
                                     EQ_exp=Results.Scenario.EQ_exp, \
                                     EQ_diag=Results.Scenario.EQ_diag, 
                                     EQ_ed=Results.Scenario.EQ_ed)
                    temp_diag_data["TS core"] = Diagnostic(diag_dict[key])
                    temp_diag_data["TS core"].insert_data(prof[0], prof[1] * 1.e-3, unc * 1.e-3, None)
                else:
                    print("Sorry " + key  + " not here yet")
        except Exception as e:
            print("Failed to load diagnostics. Reason; ")
            print(e)
        evt_out = UpdateDiagDataEvt(Unbound_EVT_DIAGNOSTICS_LOADED, self.GetId())
        evt_out.insertDiagData(temp_diag_data)
        wx.PostEvent(self, evt_out)
    
    def OnDiagDataLoaded(self, evt):
        for key in evt.DiagData.keys():
            self.diag_data[key] = evt.DiagData[key]
        self.diag_box.Clear() 
        self.diag_box.AppendItems(self.diag_data.keys())
        self.load_diag_data_button.Enable()
    
    def OnLoadOtherResults(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading data - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        plot_type = self.plot_choice.GetStringSelection()
        if(plot_type not in ["Trad", "Ray"]):
            print("Sorry only Trad and Ray supported at the moment")
            return
        if(self.Results is None):
            print("First load results before you compare")
            return
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation(s)", \
            defaultDir=self.Results.Config.working_dir, \
            wildcard=('Matlab files (*.mat)|*.mat'),
            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if(dlg.ShowModal() == wx.ID_OK):
            paths = dlg.GetPaths()
            dlg.Destroy()
            if(len(paths) > 0):
                wt = WorkerThread(self.get_other_results, [paths, plot_type])
                self.load_other_results_button.Disable()
        
    def get_other_results(self, args):
        paths = args[0]
        plot_type = args[1]
        temp_compare_data = {}
        if(plot_type == "Trad"):
            temp_compare_data[plot_type] =  {}
        elif(plot_type == "Ray"):
            for quant in ["RayXRz", "RayORz", "RayXxy", "RayXxy"]:
                temp_compare_data[quant] =  {}
        try:
            for path in paths:
                    result = ECRadResults()
                    if(result.from_mat_file(path) == False):
                        print("Failed to load file at " + path)
                        continue
                    if(hasattr(result, "comment")):
                        label = result.comment
                    else:
                        label = os.path.basename(path)
                        label = label.replace("_", " ")
                    if(plot_type == "Trad"):
                        temp_compare_data[plot_type][label] = {}
                        x, y = result.extract_field(plot_type)
                        temp_compare_data[plot_type][label]["x"] = x
                        temp_compare_data[plot_type][label]["y"] = y
                        temp_compare_data[plot_type][label]["time"] = result.time
                        diag_mask = []
                        for itime in range(len(result.Scenario.plasma_dict["time"])):
                            diag_mask.append(result.Scenario.ray_launch[itime]["diag_name"])
                        temp_compare_data[plot_type][label]["diag_mask"] = np.array(diag_mask)
                    elif(plot_type == "Ray"):
                        for quant in ["RayXRz", "RayORz", "RayXxy", "RayXxy"]:
                            x, y = result.extract_field(quant)
                            temp_compare_data[quant][label] = {}
                            temp_compare_data[quant][label]["x"] = x
                            temp_compare_data[quant][label]["y"] = y
                            temp_compare_data[quant][label]["time"] = result.time
        except Exception as e:
            print("Something went wrong when importing the other results")
            print(e)
        evt_out = GenerticEvt(Unbound_EVT_OTHER_RESULTS_LOADED, self.GetId())
        evt_out.insertData(temp_compare_data)
        wx.PostEvent(self, evt_out)

    def OnOtherResultsLoaded(self, evt):
        for key in evt.Data.keys():
            if(key not in self.compare_data.keys()):
                self.compare_data[key] = {}
            for entry in evt.Data[key].keys():
                self.compare_data[key][entry] = evt.Data[key][entry]
        plot_type = self.plot_choice.GetStringSelection()
        self.other_result_box.Clear()
        resultlist = []
        if(plot_type in  evt.Data.keys()):
            resultlist = self.compare_data[plot_type].keys()
        elif(plot_type == "Ray" and "RayXRz" in evt.Data.keys()):
            resultlist = self.compare_data["RayXRz"].keys()
        resultlist.sort()
        self.other_result_box.AppendItems(resultlist)
        self.load_other_results_button.Enable()

class FigureBook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY)
        self.FigureList = []

    def AddPlot(self, plot_type, Config, Results,  diag_data, diag_data_selected, other_results, other_results_selected, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio):
        self.FigureList.append(PlotContainer(self))
        if(self.FigureList[-1].Plot(plot_type, Config, Results, diag_data, diag_data_selected, other_results, other_results_selected, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio)):
            if(plot_type == "Trad" or plot_type == "Rz_Res"):
                self.AddPage(self.FigureList[-1], plot_type + " t = {0:2.3f} s".format(time))
            else:
                self.AddPage(self.FigureList[-1], plot_type + " t = {0:2.3f} s".format(time) + " Channel " + str(ch + 1))
        else:
            del(self.FigureList[-1])
            return
        if(not self.IsShown()):
            self.Show(True)
        return 0

    def ClearFigureBook(self):
        while self.GetPageCount() > 0:
            self.RemovePage(0)


class PlotContainer(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig_sizer = wx.BoxSizer(wx.VERTICAL)
        self.fig = plt.figure(figsize=(12.0, 8.5), tight_layout=True, frameon=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.Bind(EVT_DONE_PLOTTING, self.OnDonePlotting)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        fw, th = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.fig_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.LEFT , 5)
        self.fig_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.EXPAND , 5)
        # self.fig_H_sizer = wx.BoxSizer(wx.VERTICAL)
        # self.fig_H = plt.figure(figsize=(12.0, 8.5), tight_layout=False)
        # self.fig_H.clf()
        # self.canvas_H = FigureCanvas(self, -1, self.fig_H)
        # self.canvas_H.mpl_connect('motion_notify_event', self.UpdateCoords)
        # self.canvas_H.draw()
        # self.plot_toolbar_H = NavigationToolbar2Wx(self.canvas_H)
        # fw, th = self.plot_toolbar_H.GetSize().Get()
        # self.plot_toolbar_H.SetSize(wx.Size(fw, th))
        # self.plot_toolbar_H.Realize()
        # self.fig_H_sizer.Add(self.plot_toolbar_H, 0, wx.ALL | \
        #        wx.LEFT , 5)
        # self.fig_H_sizer.Add(self.canvas_H, 0, wx.ALL | \
        #        wx.EXPAND , 5)
        self.sizer.Add(self.fig_sizer, 0, wx.ALL | wx.EXPAND , 5)
        self.sizer.AddStretchSpacer()
        # self.sizer.Add(self.fig_H_sizer, 0, wx.ALL | wx.EXPAND , 5)
        self.pc_obj = plotting_core(self.fig, title=False)

    def Plot(self, plot_type, Config, Results, diag_data, diag_data_selected, other_results, other_results_selected, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio):
        self.pc_obj.reset(True)
        if(len(Results.time) == 0):
            print("No time points! - Did you select new IDA timepoints?")
            return
        time_index = np.argmin(np.abs(Results.time - time))
        straight = False
        if(mode):
            mode_str = 'X'
        else:
            mode_str = 'O'
        if(plot_type == "Ray"):
            if(not Config.extra_output):
                print("The rays were not output by ECRad!")
                print(r"Rerun ECRad with \"extra output\" set to True")
                return
            if(len(Results.ray["s" + mode_str]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            elif(len(Results.ray["s" + mode_str][time_index][ch]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            R_other_list = []
            z_other_list = []
            x_other_list = []
            y_other_list = []
            if(len(other_results_selected) > 0 and "RayXRz" in other_results.keys()):
                multiple_models = True
                if(hasattr(Results, "comment")):
                    label = Results.comment
                else:
                    label = "Main Result"
                label_list = [label]
            else:
                multiple_models = False
                label_list = None
            if(multiple_models):
                for entry in other_results["RayXRz"].keys():
                    if(entry not in other_results_selected):
                        continue
                    itime = np.argmin(np.abs(other_results["Ray"+mode_str + "Rz"][entry]["time"] - time))
                    
                    try:
                        dummy=other_results["Ray"+mode_str + "Rz"][entry]["x"][itime][ch][0][0]
                        print("Found multiple rays per channel in result " + entry + ". Only plotting central ray." )
                        print("Comparing with ray bundles not supported atm., sorry.")
                        R_other_list.append(other_results["Ray"+mode_str + "Rz"][entry]["x"][itime][ch][0])
                        z_other_list.append(other_results["Ray"+mode_str + "Rz"][entry]["y"][itime][ch][0])
                        x_other_list.append(other_results["Ray"+mode_str + "xy"][entry]["x"][itime][ch][0])
                        y_other_list.append(other_results["Ray"+mode_str + "xy"][entry]["y"][itime][ch][0])
                    except IndexError:
                        R_other_list.append(other_results["Ray"+mode_str + "Rz"][entry]["x"][itime][ch])
                        z_other_list.append(other_results["Ray"+mode_str + "Rz"][entry]["y"][itime][ch])
                        x_other_list.append(other_results["Ray"+mode_str + "xy"][entry]["x"][itime][ch])
                        y_other_list.append(other_results["Ray"+mode_str + "xy"][entry]["y"][itime][ch])
                    label_list.append(entry)
            try:
                try:
                    rays = []
                    if(np.iterable(Results.ray["s" + mode_str][time_index][ch][0])):
                        ir = 0
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir], \
                              x_tb=Results.ray["x" + mode_str + "tb"][time_index][ch], \
                              y_tb=Results.ray["y" + mode_str + "tb"][time_index][ch], \
                              z_tb=Results.ray["z" + mode_str + "tb"][time_index][ch], \
                              x_tbp1=Results.ray["x" + mode_str + "tbp1"][time_index][ch], \
                              y_tbp1=Results.ray["y" + mode_str + "tbp1"][time_index][ch], \
                              z_tbp1=Results.ray["z" + mode_str + "tbp1"][time_index][ch], \
                              x_tbp2=Results.ray["x" + mode_str + "tbp1"][time_index][ch], \
                              y_tbp2=Results.ray["y" + mode_str + "tbp2"][time_index][ch], \
                              z_tbp2=Results.ray["z" + mode_str + "tbp2"][time_index][ch])
                        rays.append(cur_ray)
                        for ir in range(1, len(Results.ray["s" + mode_str][time_index][ch])):
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir])
                            rays.append(cur_ray)
                    else:
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                              Results.ray["x" + mode_str][time_index][ch], \
                              Results.ray["y" + mode_str][time_index][ch], \
                              Results.ray["z" + mode_str][time_index][ch], \
                              Results.ray["H" + mode_str][time_index][ch], \
                              Results.ray["N" + mode_str][time_index][ch], \
                              Results.ray["Nc" + mode_str][time_index][ch], \
                              x_tb=Results.ray["x" + mode_str + "tb"][time_index][ch], \
                              y_tb=Results.ray["y" + mode_str + "tb"][time_index][ch], \
                              z_tb=Results.ray["z" + mode_str + "tb"][time_index][ch])
                        rays.append(cur_ray)
                except KeyError:
                    print("No TORBEAM rays found")
#                     print("Availabe keys", Results.ray.keys())
                    rays = []
                    straight = True
                    if(alt_model):
                        straight_rays = []
                    if(np.iterable(Results.ray["s" + mode_str][time_index][ch][0])):
                        ir = 0
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir])
                        rays.append(cur_ray)
                        for ir in range(1, len(Results.ray["s" + mode_str][time_index][ch])):
                            if(alt_model):
                                x0 = Results.ray["x" + mode_str][time_index][ch][ir][::-1][0]
                                x1 = Results.ray["x" + mode_str][time_index][ch][ir][::-1][40]
                                y0 = Results.ray["y" + mode_str][time_index][ch][ir][::-1][0]
                                y1 = Results.ray["y" + mode_str][time_index][ch][ir][::-1][40]
                                z0 = Results.ray["z" + mode_str][time_index][ch][ir][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ch][ir][::-1][40]
                                delta_s = Results.ray["s" + mode_str][time_index][ch][0][np.argmax(np.sqrt((Results.ray["x" + mode_str][time_index][ch][0] - \
                                                                                                            Results.ray["x" + mode_str][time_index][ch][0][-1]) ** 2 + \
                                                                                                           (Results.ray["y" + mode_str][time_index][ch][0] - \
                                                                                                            Results.ray["y" + mode_str][time_index][ch][0][-1]) ** 2))]
                                s = np.linspace(0.0, delta_s, 100)
                                x = x0 + s * (x1 - x0)
                                y = y0 + s * (y1 - y0)
                                z = z0 + s * (z1 - z0)
                                cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                                  Results.ray["x" + mode_str][time_index][ch][ir], \
                                  Results.ray["y" + mode_str][time_index][ch][ir], \
                                  Results.ray["z" + mode_str][time_index][ch][ir], \
                                  Results.ray["H" + mode_str][time_index][ch][ir], \
                                  Results.ray["N" + mode_str][time_index][ch][ir], \
                                  Results.ray["Nc" + mode_str][time_index][ch][ir], \
                                  x_tb=x, y_tb=y, z_tb=z)
                            else:
                                cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                                  Results.ray["x" + mode_str][time_index][ch][ir], \
                                  Results.ray["y" + mode_str][time_index][ch][ir], \
                                  Results.ray["z" + mode_str][time_index][ch][ir], \
                                  Results.ray["H" + mode_str][time_index][ch][ir], \
                                  Results.ray["N" + mode_str][time_index][ch][ir], \
                                  Results.ray["Nc" + mode_str][time_index][ch][ir])
                            rays.append(cur_ray)
                    else:
                        if(alt_model):
                            x0 = Results.ray["x" + mode_str][time_index][ch][::-1][0]
                            x1 = Results.ray["x" + mode_str][time_index][ch][::-1][40]
                            y0 = Results.ray["y" + mode_str][time_index][ch][::-1][0]
                            y1 = Results.ray["y" + mode_str][time_index][ch][::-1][40]
                            z0 = Results.ray["z" + mode_str][time_index][ch][::-1][0]
                            z1 = Results.ray["z" + mode_str][time_index][ch][::-1][40]
                            delta_s = np.max(Results.ray["s" + mode_str][time_index][ch])
                            s = np.linspace(0.0, delta_s, 100)
                            ds = Results.ray["s" + mode_str][time_index][ch][::-1][0] - Results.ray["s" + mode_str][time_index][ch][::-1][40]
                            x = x0 + s / ds * (x1 - x0)
                            y = y0 + s / ds * (y1 - y0)
                            z = z0 + s / ds * (z1 - z0)
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                              Results.ray["x" + mode_str][time_index][ch], \
                              Results.ray["y" + mode_str][time_index][ch], \
                              Results.ray["z" + mode_str][time_index][ch], \
                              Results.ray["H" + mode_str][time_index][ch], \
                              Results.ray["N" + mode_str][time_index][ch], \
                              Results.ray["Nc" + mode_str][time_index][ch], \
                              x_tb=x, y_tb=y, z_tb=z)
                        else:
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                            Results.ray["x" + mode_str][time_index][ch], \
                            Results.ray["y" + mode_str][time_index][ch], \
                            Results.ray["z" + mode_str][time_index][ch], \
                            Results.ray["H" + mode_str][time_index][ch], \
                            Results.ray["N" + mode_str][time_index][ch], \
                            Results.ray["Nc" + mode_str][time_index][ch])
                        rays.append(cur_ray)
            except KeyError:
                print("Error: No ray information in currently loaded data set")
                return False
            if(Results.resonance["R_cold"][time_index][ch] < 0.0):
                print("ECRad did not find a cold resonance for this channel. Cut-off?")
                s_cold = None
                R_cold = None
                z_cold = None
            else:
                s_cold = Results.resonance["R_cold"][time_index][ch]
                R_cold = Results.resonance["R_cold"][time_index][ch]
                z_cold = Results.resonance["z_cold"][time_index][ch]
            EQ_obj = EQData(Results.Scenario.shot)
            EQ_obj.insert_slices_from_ext(Results.Scenario.plasma_dict["time"], Results.Scenario.plasma_dict["eq_data"])
            # the matrices in the slices are Fortran ordered - hence transposition necessary
            args = [self.pc_obj.plot_ray, Results.Scenario.shot, time, rays]
            kwargs = {"index":time_index, "Eq_Slice":EQ_obj.GetSlice(time), "H":False, "R_cold":R_cold, \
                      "z_cold":z_cold, "s_cold":s_cold, "straight":straight, "eq_aspect_ratio":eq_aspect_ratio, \
                      "R_other_list":R_other_list, "z_other_list":z_other_list, "x_other_list":x_other_list, \
                      "y_other_list":y_other_list, "label_list":label_list, "vessel_bd":Results.Scenario.plasma_dict["vessel_bd"]}
#             self.fig = self.pc_obj.plot_ray(Results.Scenario.shot, time, rays, index=time_index, \
#                                         EQ_obj=EQ_obj.GetSlice(time), H=False, R_cold=R_cold, \
#                                         z_cold=z_cold, s_cold=s_cold, straight=straight, \
#                                         eq_aspect_ratio=eq_aspect_ratio, R_other_list=R_other_list, \
#                                         z_other_list=z_other_list, x_other_list = x_other_list, \
#                                         y_other_list=y_other_list, label_list=label_list, \
#                                         vessel_bd=Results.Scenario.plasma_dict["vessel_bd"])
#            else:
#                self.fig = self.pc_obj.plot_ray(Results.Scenario.shot, time, rays, index=time_index, \
#                                            H=False, R_cold=R_cold, \
#                                            z_cold=z_cold, s_cold=s_cold, straight=straight, eq_aspect_ratio=eq_aspect_ratio)
        if(plot_type == "Ray_H_N"):
            print("Coming soon - sorry!")
            return False
        elif(plot_type == "Trad"):
            if(len(other_results_selected) > 0 and "Trad" in other_results.keys()):
                rhop_list = []
                Trad_list = []
                diag_name_list = []
                multiple_models = True
                if(hasattr(Results, "comment")):
                    label = Results.comment
                else:
                    label = "Main Result"
                label_list = [label]
            else:
                multiple_models = False
                label_list = None
            rhop = Results.resonance["rhop_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(len(rhop) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
            Trad = Results.Trad[time_index][Results.tau[time_index] >= tau_threshhold]
            if(alt_model):
                if(Results.Config.extra_output):
                    Trad_comp = Results.Trad_comp[time_index][Results.tau[time_index] >= tau_threshhold]
                else:
                    Trad_comp = []
                    print("Secondary model was deactivated during the run.")
                    print("To enable it, activate extra outout und rerun ECRad!")
            else:
                Trad_comp = []
            diag_names = Results.Scenario.ray_launch[time_index]["diag_name"][Results.tau[time_index] >= tau_threshhold]
            if(multiple_models):
                rhop_list.append(np.copy(rhop))
                Trad_list.append(np.copy(Trad))
                diag_name_list.append(diag_names)
                for entry in other_results["Trad"].keys():
                    if(entry not in other_results_selected):
                        continue
                    itime = np.argmin(np.abs(other_results["Trad"][entry]["time"] - time))
                    rhop_list.append(other_results["Trad"][entry]["x"][itime])
                    Trad_list.append(other_results["Trad"][entry]["y"][itime])
                    diag_name_list.append(other_results["Trad"][entry]["diag_mask"][itime])
                    label_list.append(entry)
                rhop = rhop_list
                Trad = Trad_list
                diag_names = diag_name_list
            diagdict = {}
            for diag_name in diag_data_selected:
                diagdict[diag_name]=diag_data[diag_name].getSlice(time_index)
            rhop_Te= Results.Scenario.plasma_dict["rhop_prof"][time_index] * Results.Scenario.Te_rhop_scale
            Te = Results.Scenario.plasma_dict["Te"][time_index] * Results.Scenario.Te_scale / 1.e3
#            if(Config.Ext_plasma == False):
#                try:
#                    rhop_ECE = Config.plasma_dict["ECE_rhop"][time_index]
#                    if(Config.plasma_dict["ECE_dat"][time_index].ndim == 2):
#                        ECE_dat = np.mean(Config.plasma_dict["ECE_dat"][time_index] / 1.e3, axis=0)
#                        ECE_err = np.mean(Config.plasma_dict["ECE_unc"][time_index] / 1.e3, axis=0)
#                    else:
#                        print(Config.plasma_dict["ECE_dat"])
#                        ECE_dat = Config.plasma_dict["ECE_dat"][time_index] / 1.e3
#                        ECE_err = Config.plasma_dict["ECE_unc"][time_index] / 1.e3
#                    ECE_mod = Config.plasma_dict["ECE_mod"][time_index] / 1.e3
#                    self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
#                                                     rhop_IDA, Te_IDA, \
#                                                     rhop_ECE, ECE_dat, ECE_err, ECE_mod, Config.dstf, alt_model)
#                except IndexError:
#                    print("Something wrong with the IDA data - plotting only fwd. model data")
#                    self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
#                                                     rhop_IDA, Te_IDA, \
#                                                    [], [], [], [], Config.dstf, alt_model)
#            else:
            args = [self.pc_obj.plot_Trad, time, rhop, Trad, Trad_comp, \
                                         rhop_Te, Te,  diagdict, diag_names, \
                                             Config.dstf, alt_model]
            kwargs = {}
            kwargs["multiple_models"] = multiple_models
            kwargs["label_list"] = label_list
#             self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
#                                              rhop_Te, Te, diagdict, diag_names, \
#                                              Config.dstf, alt_model, multiple_models=multiple_models, \
#                                              label_list=label_list)
        elif(plot_type == "T"):
            rhop = Results.resonance["rhop_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(len(rhop) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
            tau = Results.tau[time_index][Results.tau[time_index] >= tau_threshhold]
            if(Results.Config.extra_output):
                tau_comp = Results.tau_comp[time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                tau_comp = None
            rhop_IDA = Results.Scenario.plasma_dict["rhop_prof"][time_index] * Results.Scenario.Te_rhop_scale
            Te_IDA = Results.Scenario.plasma_dict["Te"][time_index] * Results.Scenario.Te_scale / 1.e3
#             self.fig = self.pc_obj.plot_tau(time, rhop, \
#                                             tau, tau_comp, rhop_IDA, Te_IDA, \
#                                             Config.dstf, alt_model)
            args = [self.pc_obj.plot_tau, time, rhop, tau, tau_comp, \
                                         rhop_IDA, Te_IDA,  Config.dstf, alt_model]
            kwargs = {}
        elif(plot_type == "Trad mode"):
            if(Config.considered_modes != 3):
                print("This plot is only sensitble if both X and O mode are considered")
                return
            if(not Config.extra_output):
                print("Extra ouput must be set to true for this information to be available")
                print("Please rerun ECRad with 'extra output' set to True")
                return
            if(len(Results.XTrad) == 0):
                print("No information on the individual X and O mode fractions availabe")
                print("This information was not stored in the result files previously, please rerun ECRad")
                return
            diagdict = {}
            for diag_name in diag_data_selected:
                diagdict[diag_name]=diag_data[diag_name].getSlice(time_index)
            rhop_Te = Results.Scenario.plasma_dict["rhop_prof"][time_index] * Results.Scenario.Te_rhop_scale
            Te = Results.Scenario.plasma_dict["Te"][time_index] * Results.Scenario.Te_scale / 1.e3
            diag_names = Results.Scenario.ray_launch[time_index]["diag_name"][Results.tau[time_index] >= tau_threshhold]
            if(mode):
                # X-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Xtau[time_index] >= tau_threshhold]
                Trad = Results.XTrad[time_index][Results.Xtau[time_index] >= tau_threshhold]
                X_mode_frac = Results.X_mode_frac[time_index][Results.Xtau[time_index] >= tau_threshhold]
                Trad_comp = Results.XTrad_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]
                X_mode_frac_comp = Results.X_mode_frac_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]

            else:
                # O-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Otau[time_index] >= tau_threshhold]
                Trad = Results.OTrad[time_index][Results.Otau[time_index] >= tau_threshhold]
                Trad_comp = Results.OTrad_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
                X_mode_frac = Results.X_mode_frac[time_index][Results.Otau[time_index] >= tau_threshhold]
                X_mode_frac_comp = Results.X_mode_frac_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
            args = [self.pc_obj.plot_Trad, time, rhop, Trad, Trad_comp, \
                                         rhop_Te, Te,  diagdict, diag_names, \
                                         Config.dstf, alt_model]
            kwargs = {}
            kwargs["X_mode_fraction"] = X_mode_frac
            kwargs["X_mode_fraction_comp"] = X_mode_frac_comp
        elif(plot_type == "T mode"):
            if(Config.considered_modes != 3):
                print("This plot is only sensitble if both X and O mode are considered")
                return
            if(not Config.extra_output):
                print("Extra ouput must be set to true for this information to be available")
                print("Please rerun ECRad with 'extra output' set to True")
                return
            if(len(Results.XTrad) == 0):
                print("No information on the individual X and O mode fractions availabe")
                print("This information was not stored in the result files previously, please rerun ECRad")
                return
            if(mode):
                # X-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Xtau[time_index] >= tau_threshhold]
                tau = Results.Xtau[time_index][Results.Xtau[time_index] >= tau_threshhold]
                tau_comp = Results.Xtau_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]
            else:
                # O-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Otau[time_index] >= tau_threshhold]
                tau = Results.Otau[time_index][Results.Otau[time_index] >= tau_threshhold]
                tau_comp = Results.Otau_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
            rhop_IDA = Results.Scenario.plasma_dict["rhop_prof"][time_index] * Results.Scenario.Te_rhop_scale
            Te_IDA = Results.Scenario.plasma_dict["Te"][time_index] * Results.Scenario.Te_scale / 1.e3
            args = [self.pc_obj.plot_tau, time, rhop, \
                                            tau, tau_comp, rhop_IDA, Te_IDA, \
                                            Config.dstf, alt_model]
            kwargs = {}
#             self.fig = self.pc_obj.plot_tau(time, rhop, \
#                                             tau, tau_comp, rhop_IDA, Te_IDA, \
#                                             Config.dstf, alt_model)
        elif(plot_type == "BPD"):
            if(not Config.extra_output):
                print("Birthplace distribution was not computed")
                print("Rerun ECRad with 'extra output' set to True")
                return
            # R = Results.los["R" + mode_str][time_index][ch]
            rhop_IDA = Results.Scenario.plasma_dict["rhop_prof"][time_index] * Results.Scenario.Te_rhop_scale
            Te_IDA = Results.Scenario.plasma_dict["Te"][time_index] * Results.Scenario.Te_scale / 1.e3
            if(mode):
                if(len(Results.BPD["rhopX"]) == 0):
                    print("No data availabe for X-mode")
                    return False
                rhop = Results.BPD["rhopX"][time_index][ch]
                D = Results.BPD["BPDX"][time_index][ch]
                D_comp = Results.BPD["BPD_secondX"][time_index][ch]
            else:
                if(len(Results.BPD["rhopO"]) == 0):
                    print("No data availabe for O-mode")
                    return False
                rhop = Results.BPD["rhopO"][time_index][ch]
                D = Results.BPD["BPDO"][time_index][ch]
                D_comp = Results.BPD["BPD_secondO"][time_index][ch]
            rhop_cold = Results.resonance["rhop_cold"][time_index][ch]
            EQ_obj = EQData(Results.Scenario.shot)
            EQ_obj.insert_slices_from_ext(Results.Scenario.plasma_dict["time"], Results.Scenario.plasma_dict["eq_data"])
            # the matrices in the slices are Fortran ordered - hence transposition necessary
#            else:
#                EQ_obj = EQData(Results.Scenario.shot, EQ_exp=Results.Scenario.EQ_exp, EQ_diag=Results.Scenario.EQ_diag, \
#                                EQ_ed=Results.Scenario.EQ_ed)
            R_axis, z_axis = EQ_obj.get_axis(time)
            if(Results.resonance["R_cold"][time_index][ch] < R_axis):
                rhop_cold *= -1.0
            args = [self.pc_obj.plot_BPD, time, rhop, D, D_comp, rhop_IDA, Te_IDA, Config.dstf, rhop_cold]
            kwargs = {}
#             self.fig = self.pc_obj.plot_BPD(time, rhop, D, D_comp, rhop_IDA, Te_IDA, Config.dstf, rhop_cold)
        elif(plot_type == "Rz res."):
            R_cold = Results.resonance["R_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            z_cold = Results.resonance["z_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(Config.extra_output):
                R_warm = Results.resonance["R_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
                z_warm = Results.resonance["z_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                print("Warm resonances were not computed")
                print("Rerun ECRad with 'extra output' set to True")
                R_warm = []
                z_warm = []
            if(len(R_cold) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
#            if(alt_model):
#                if(mode):
#                    R_warm_comp = np.zeros(np.size(Results.birthplace_X_comp, axis=1))
#                    z_warm_comp = np.zeros(np.size(Results.birthplace_X_comp, axis=1))
#                    for ich in range(len(R_warm_comp)):
#                        R_warm_comp[ich] = Results.los["RX"][time_index][ich][np.argmax(Results.birthplace_X_comp[time_index][ich])]
#                        z_warm_comp[ich] = Results.los["zX"][time_index][ich][np.argmax(Results.birthplace_X_comp[time_index][ich])]
#                else:
#                    R_warm_comp = np.zeros(np.size(Results.birthplace_O_comp, axis=1))
#                    z_warm_comp = np.zeros(np.size(Results.birthplace_O_comp, axis=1))
#                    for ich in range(len(R_warm_comp)):
#                        R_warm_comp[ich] = Results.los["RO"][time_index][ich][np.argmax(Results.birthplace_O_comp[time_index][ich])]
#                        z_warm_comp[ich] = Results.los["zO"][time_index][ich][np.argmax(Results.birthplace_O_comp[time_index][ich])]
#                R_warm_comp = R_warm_comp[Results.tau[time_index] > tau_threshhold]
#                z_warm_comp = z_warm_comp[Results.tau[time_index] > tau_threshhold]
#                self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                   plasma=Results.Scenario.plasma_dict, R_warm_comp=R_warm_comp, z_warm_comp=z_warm_comp)
#            else:
            EQ_obj = EQData(Results.Scenario.shot)
            EQ_obj.insert_slices_from_ext(time, Results.Scenario.plasma_dict["eq_data"])
            # the matrices in the slices are Fortran ordered - hence transposition necessary
            args = [self.pc_obj.Plot_Rz_Res, Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm]
            kwargs = {"EQ_obj":EQ_obj, "eq_aspect_ratio":eq_aspect_ratio}
#             self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                EQ_obj=EQ_obj, eq_aspect_ratio=eq_aspect_ratio)
#            else:
#                self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                   EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
#                                                   EQ_ed=Config.EQ_ed, eq_aspect_ratio=eq_aspect_ratio)
        elif(plot_type == "Rz res. w. rays"):
            if(not Config.extra_output):
                print("The rays were not output by ECRad only showing cold resonances")
                print("Rerun ECRad with 'extra output' set to True")
            R_cold = Results.resonance["R_cold"][time_index][Results.tau[time_index] > tau_threshhold]
            z_cold = Results.resonance["z_cold"][time_index][Results.tau[time_index] > tau_threshhold]
            if(Config.extra_output):
                R_warm = Results.resonance["R_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
                z_warm = Results.resonance["z_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                print("Warm resonances were not computed")
                print("Rerun ECRad with 'extra output' set to True")
                R_warm = []
                z_warm = []
            rays = []
            tb_rays = []
            if(len(Results.ray["s" + mode_str]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            elif(len(Results.ray["s" + mode_str][time_index][ch]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            try:
                if(not np.isscalar(Results.ray["x" + mode_str][time_index][0][0])):
                    for ich in range(len(Results.ray["x" + mode_str][time_index])):
                        i_min = 0
                        if(mode_str == "X"):
                            points_w_emission = np.where(Results.ray["BPDX"][time_index][ich][0] > 1.e-20)  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        else:
                            points_w_emission = np.where(Results.ray["BPDO"][time_index][ich][0] > 1.e-20)  # Central ra
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        rays.append([np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][i_min:] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][i_min:] ** 2), Results.ray["z" + mode_str][time_index][ich][0][i_min:]])
                    rays = np.array(rays)[Results.tau[time_index] > tau_threshhold]
                else:
                    for ich in range(len(Results.ray["x" + mode_str][time_index])):
                        i_min = 0
                        if(mode_str == "X"):
                            points_w_emission = np.where(Results.ray["BPDX"][time_index][ich] > 1.e-20)[0]  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        else:
                            points_w_emission = np.where(Results.ray["BPDO"][time_index][ich] > 1.e-20)[0]  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        rays.append([np.sqrt(Results.ray["x" + mode_str][time_index][ich][i_min:] ** 2 + Results.ray["y" + mode_str][time_index][ich][i_min:] ** 2), Results.ray["z" + mode_str][time_index][ich][i_min:]])
                    if(len(Results.ray["x" + mode_str][time_index]) != len(Results.tau[time_index])):
                        print("Ray computation was skipped for some rays for the selected mode")
                        print("Cannot remove rays with low optical depth, showing all available rays")
                    else:
                        rays = np.array(rays)[Results.tau[time_index] > tau_threshhold]
                try:
                    for ich in range(len(Results.ray["x" + mode_str + "tb"][time_index])):
                        tb_rays.append([Results.ray["R" + mode_str + "tb"][time_index][ich], \
                                        Results.ray["z" + mode_str + "tb"][time_index][ich]])
                    tb_rays = np.array(tb_rays)[Results.tau[time_index] > tau_threshhold]
                    EQ_obj = EQData(Results.Scenario.shot)
                    EQ_obj.insert_slices_from_ext(Results.Scenario.time, Results.Scenario.plasma_dict["eq_data"])
                    args = [self.pc_obj.Plot_Rz_Res, Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm]
                    kwargs = {"EQ_obj":EQ_obj, "Rays":rays, "straight_Rays":straight_rays, \
                              "vessel_bd": Results.Scenario.plasma_dict["vessel_bd"]}
#                     self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                        EQ_obj=EQ_obj, Rays=rays, tb_Rays=tb_rays, \
#                                                        vessel_bd=Results.Scenario.plasma_dict["vessel_bd"])
#                    else:
#                        self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                           Rays=rays, tb_Rays=tb_rays)
                except KeyError:
                    print("No TORBEAM rays available")
                    if(alt_model):
                        if(len(Results.ray["x" + mode_str][time_index]) == 0):
                            print("For " + mode_str + " mode there is no data")
                            return False
                        straight_rays = []
                        for ich in range(len(Results.ray["x" + mode_str][time_index])):
                            if(not np.isscalar(Results.ray["x" + mode_str][time_index][0][0])):
                                R0 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1][0] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1][0] ** 2)
                                R1 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1][40] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1][40] ** 2)
                                z0 = Results.ray["z" + mode_str][time_index][ich][0][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ich][0][::-1][40]
                                Rmin = np.min(np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1] ** 2))
                            else:
                                R0 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1][0] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1][0] ** 2)
                                R1 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1][40] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1][40] ** 2)
                                z0 = Results.ray["z" + mode_str][time_index][ich][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ich][::-1][40]
                                Rmin = np.min(np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1] ** 2))
                            R = np.linspace(R0, Rmin, 100)
                            z = z0 + (R - R0) / (R1 - R0) * (z1 - z0)
                            straight_rays.append([R, z])
                        if(len(Results.ray["x" + mode_str][time_index]) != len(Results.tau[time_index])):
                            print("Ray computation was skipped for some rays for the selected mode")
                            print("Cannot remove rays with low optical depth, showing all available rays")
                        else:
                            straight_rays = np.array(straight_rays)[Results.tau[time_index] > tau_threshhold]
                        EQ_obj = EQData(Results.Scenario.shot)
                        EQ_obj.insert_slices_from_ext(time, Results.Scenario.plasma_dict["eq_data"])
                        # the matrices in the slices are Fortran ordered - hence transposition necessary
                        args = [self.pc_obj.Plot_Rz_Res, Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm]
                        kwargs = {"EQ_obj":EQ_obj, "Rays":rays, "straight_Rays":straight_rays, \
                                  "vessel_bd": Results.Scenario.plasma_dict["vessel_bd"]}
#                         self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                            EQ_obj=EQ_obj, Rays=rays, straight_Rays=straight_rays, \
#                                                            vessel_bd=Results.Scenario.plasma_dict["vessel_bd"])
# #                        else:
#                            self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                               Rays=rays, straight_Rays=straight_rays, \
#                                                               EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
#                                                               EQ_ed=Config.EQ_ed)
                    else:
                        EQ_obj = EQData(Results.Scenario.shot)
                        EQ_obj.insert_slices_from_ext(Results.Scenario.plasma_dict["time"], Results.Scenario.plasma_dict["eq_data"])
                        # the matrices in the slices are Fortran ordered - hence transposition necessary
                        args = [self.pc_obj.Plot_Rz_Res, Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm]
                        kwargs = {"EQ_obj":EQ_obj, "Rays":rays}
#                        else:
#                            self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                               Rays=rays, EQ_exp=Results.Scenario.EQ_exp, EQ_diag=Results.Scenario.EQ_diag, \
#                                                               EQ_ed=Results.Scenario.EQ_ed)
            except KeyError:
                print("No rays available")
                EQ_obj = EQData(Results.Scenario.shot)
                EQ_obj.insert_slices_from_ext(Results.Scenario.plasma_dict["time"], Results.Scenario.plasma_dict["eq_data"], transpose=True)
                # the matrices in the slices are Fortran ordered - hence transposition necessary
                args = [self.pc_obj.Plot_Rz_Res, Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm]
                kwargs = {"EQ_obj":EQ_obj}
#                else:
#                    self.fig = self.pc_obj.Plot_Rz_Res(Results.Scenario.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                               EQ_exp=Results.Scenario.EQ_exp, EQ_diag=Results.Scenario.EQ_diag, \
#                                                               EQ_ed=Results.Scenario.Eq_ed)
            
        elif(plot_type == "3D Birthplace distribution"):
            if(not mode):
                print("3D Birthplace distribution only available for X-mode at the moment")
                return
            args = [make_3DBDOP_cut_GUI, Results, self.fig, time, ch + 1]
            kwargs = {}
#             try:
#                 self.fig = make_3DBDOP_cut_GUI(Results, self.fig, time, ch)
#             except ValueError as e:
#                 print(e)
#                 return False
        elif(plot_type == "Momentum space sensitivity"):
            if(not mode):
                print("Momentum space sensitivity plot only available for X-mode at the moment")
                return
            args = [diag_weight, self.fig, Results, time, ch + 1, None]
            kwargs = {}
#             try:
#                 self.fig = diag_weight( self.fig, Results, time, ch, None)
#             except ValueError as e:
#                 print(e)
#                 return False
        wt = WorkerThread(self.plot_threading, args, kwargs)
        return True

    def plot_threading(self, args, kwargs):
        self.fig = args[0](*args[1:], **kwargs)
        evt = wx.PyCommandEvent(Unbound_EVT_DONE_PLOTTING, self.GetId())
        wx.PostEvent(self, evt)
        
    def OnDonePlotting(self, evt):
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        wx.PostEvent(self, evt)
        wx.PostEvent(self.Parent.Parent, evt) # There should be a way to avoid using Parent.Parent
        

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)
            
            
class DiagSelectDialog(wx.Dialog):
    def __init__(self, parent, avail_diags):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "To be loaded")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.used_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnRemoveSelection)
        self.shotlist = []
        self.ECRad_result_list = []
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.select_button_sizer.AddStretchSpacer(prop=1)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.AddStretchSpacer(prop=1)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Available")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_list.AppendItems(avail_diags)
        self.unused_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnAddSelection)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.AddStretchSpacer(prop=1)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer.AddStretchSpacer(prop=1)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer.AddStretchSpacer(prop=1)
        self.sizer.Add(self.select_sizer, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 5)
        self.SetSizer(self.sizer)
        
        
        
    def UpdateLists(self, used, unused):
        used = list(set(used))
        used.sort()
        unused = list(set(unused))
        unused.sort()
        self.used_list.Clear()
        if(len(used) > 0):
            self.used_list.AppendItems(used)
        self.unused_list.Clear()
        if(len(unused) > 0):
            self.unused_list.AppendItems(unused)
        
    def OnAddSelection(self, evt):
        used = self.used_list.GetItems()
        unused = self.unused_list.GetItems()
        if(hasattr(evt, "GetSelection")):
            sel = [evt.GetSelection()]
        else:
            sel = self.unused_list.GetSelections()
        for i_sel in sel:
            string = self.unused_list.GetString(i_sel)
            used.append(unused.pop(unused.index(string)))
        self.UpdateLists(used, unused)

    def OnRemoveSelection(self, evt):
        used = self.used_list.GetItems()
        unused = self.unused_list.GetItems()
        if(hasattr(evt, "GetSelection")):
            sel = [evt.GetSelection()]
        else:
            sel = self.used_list.GetSelections()
        for i_sel in sel:
            string = self.used_list.GetString(i_sel)
            unused.append(used.pop(used.index(string)))
        self.UpdateLists(used, unused)


    def EvtClose(self, Event):
        self.EndModal(False)

    def EvtAccept(self, Event):
        self.EndModal(True)