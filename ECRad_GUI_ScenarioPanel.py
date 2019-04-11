'''
Created on Mar 21, 2019

@author: sdenk
'''
from GlobalSettings import AUG, TCV, Phoenix
import wx
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb
from wxEvents import *
from plotting_core import plotting_core
import getpass
import numpy as np
from ECRad_Interface import load_plasma_from_mat
from plotting_configuration import *
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
if(Phoenix):
    from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
else:
    from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx
if(TCV):
    from equilibrium_utils_TCV import EQData
    from shotfile_handling_TCV import load_IDA_data, get_diag_data_no_calib, get_freqs, get_divertor_currents, filter_CTA
elif(AUG):
    from equilibrium_utils_AUG import EQData, vessel_bd_file
    from shotfile_handling_AUG import load_IDA_data, get_diag_data_no_calib, get_freqs, get_divertor_currents, filter_CTA
    from get_ECRH_config import get_ECRH_viewing_angles, identify_ECRH_on_phase, get_ECRH_launcher
    import ElmSync
else:
    print('Neither AUG nor TCV selected')
    raise(ValueError('No system selected!'))

class ScenarioSelectPanel(wx.Panel):
    def __init__(self, parent, Scenario, Config):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(8.5, 8.0), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(4.5, 4.5), tight_layout=False)
        self.fig.clf()
        self.Scenario = Scenario
        self.Config = Config
        self.delta_t = 5.e-4
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.canvas.mpl_connect('button_press_event', self.OnPlotClick)
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
        self.control_sizer = wx.BoxSizer(wx.VERTICAL)
        self.load_data_line = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.load_data_line, 0, \
                               wx.EXPAND | wx.ALL, 5)
        if(AUG):
            self.load_AUG_data_sizer = wx.BoxSizer(wx.VERTICAL)
            self.AUG_data_grid_sizer = wx.GridSizer(0, 4, 0, 0)
            self.shot_tc = simple_label_tc(self, "Shot #", Scenario.shot, "integer")
            self.AUG_data_grid_sizer.Add(self.shot_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.IDA_exp_tc = simple_label_tc(self, "IDA exp", Scenario.IDA_exp, "string")
            self.AUG_data_grid_sizer.Add(self.IDA_exp_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.IDA_ed_tc = simple_label_tc(self, "IDA ed", Scenario.IDA_ed, "integer")
            self.AUG_data_grid_sizer.Add(self.IDA_ed_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.EQ_exp_tc = simple_label_tc(self, "EQ exp", Scenario.EQ_exp, "string")
            self.AUG_data_grid_sizer.Add(self.EQ_exp_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.EQ_diag_tc = simple_label_tc(self, "EQ diag", Scenario.EQ_diag, "string")
            self.AUG_data_grid_sizer.Add(self.EQ_diag_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.EQ_ed_tc = simple_label_tc(self, "EQ ed", Scenario.EQ_ed, "integer")
            self.AUG_data_grid_sizer.Add(self.EQ_ed_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.diag_tc = simple_label_tc(self, "Comapare diag", Scenario.default_diag, "string")
            self.AUG_data_grid_sizer.Add(self.diag_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.load_AUG_data_sizer.Add(self.AUG_data_grid_sizer, 0, \
                             wx.EXPAND | wx.ALL, 5)
            self.load_aug_data_button = wx.Button(self, wx.ID_ANY, "Load AUG data")
            self.load_aug_data_button.Bind(wx.EVT_BUTTON, self.OnLoadAUG)
            self.load_AUG_data_sizer.Add(self.load_aug_data_button, 0, \
                                         wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND | wx.ALL, 5)
            self.control_sizer.Add(self.load_AUG_data_sizer, 0, \
                             wx.EXPAND | wx.ALL, 5)
            self.line_AUG_data = wx.StaticLine(self, wx.ID_ANY)
            self.control_sizer.Add(self.line_AUG_data, 0, \
                             wx.EXPAND | wx.ALL, 5)
        self.load_data_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.load_from_mat_button = wx.Button(self, wx.ID_ANY, "Load from .mat")
        self.load_from_mat_button.Bind(wx.EVT_BUTTON, self.OnLoadfromMat)
        self.load_data_sizer.Add(self.load_from_mat_button, 0, \
                         wx.ALIGN_BOTTOM | wx.ALL, 5)
#        self.load_GENE_button = wx.Button(self, wx.ID_ANY, "Load GENE dist.")
#        self.load_GENE_button.Bind(wx.EVT_BUTTON, self.OnLoadGene)
#        self.load_data_sizer.Add(self.load_GENE_button, 0, \
#                         wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.control_sizer.Add(self.load_data_sizer, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
#        if(getpass.getuser() == "sdenk"):
#            self.line_extra_1 = wx.StaticLine(self, wx.ID_ANY)
#            self.control_sizer.Add(self.line_extra_1, 0, \
#                         wx.EXPAND | wx.ALL, 5)
#            self.special_label = wx.StaticText(self, wx.ID_ANY, "Export")
#            self.special_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
#            self.special_label_sizer.AddStretchSpacer(1)
#            self.special_label_sizer.Add(self.special_label, 0, \
#                                         wx.ALIGN_CENTER | wx.ALL, 5)
#            self.special_label_sizer.AddStretchSpacer(1)
#            self.control_sizer.Add(self.special_label_sizer, 0, \
#                         wx.ALIGN_CENTER | wx.ALL, 5)
#            self.line_extra_1 = wx.StaticLine(self, wx.ID_ANY)
#            self.control_sizer.Add(self.line_extra_1, 0, \
#                         wx.EXPAND | wx.ALL, 5)
#            self.export_data_sizer = wx.BoxSizer(wx.HORIZONTAL)
#            self.make_LUKE_data_button = wx.Button(self, wx.ID_ANY, "LUKE data")
#            self.make_LUKE_data_button.Bind(wx.EVT_BUTTON, self.OnMakeLUKEdata)
#            self.make_LUKE_mat_button = wx.Button(self, wx.ID_ANY, "LUKE mat")
#            self.make_LUKE_mat_button.Bind(wx.EVT_BUTTON, self.OnMakeLUKEMat)
#            self.export_data_sizer.Add(self.make_LUKE_data_button, 0, \
#                         wx.ALIGN_BOTTOM | wx.ALL, 5)
#            self.export_data_sizer.Add(self.make_LUKE_mat_button, 0, \
#                         wx.ALIGN_BOTTOM | wx.ALL, 5)
#            self.control_sizer.Add(self.export_data_sizer, 0, \
#                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.line1 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line1, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.regular_label = wx.StaticText(self, wx.ID_ANY, "For regular time intervals")
        self.label_regular_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label_regular_sizer.AddStretchSpacer(1)
        self.label_regular_sizer.Add(self.regular_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.label_regular_sizer.AddStretchSpacer(1)
        self.control_sizer.Add(self.label_regular_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line2 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line2, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.t_start_tc = simple_label_tc(self, "start time", 0.0, "real")
        self.t_end_tc = simple_label_tc(self, "end time", 10.0, "real")
        self.steps_tc = simple_label_tc(self, "steps", 1000, "integer")
        self.RegularTimesButton = wx.Button(self, wx.ID_ANY, "Fill")
        self.RegularTimesButton.Bind(wx.EVT_BUTTON, self.OnFill)
        self.AddRegularTimesButton = wx.Button(self, wx.ID_ANY, "Add")
        self.AddRegularTimesButton.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.time_step_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.time_step_sizer.Add(self.t_start_tc, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.time_step_sizer.Add(self.t_end_tc, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.time_step_sizer.Add(self.steps_tc, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.time_step_sizer.Add(self.RegularTimesButton, 0, \
                         wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.time_step_sizer.Add(self.AddRegularTimesButton, 0, \
                         wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.control_sizer.Add(self.time_step_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line3 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line3, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.elm_filter_label = wx.StaticText(self, wx.ID_ANY, "Remove all time points during an ELM/ECRH", style=wx.ALIGN_CENTER_HORIZONTAL)
        self.elm_filter_label.Wrap(400)
        self.elm_filter_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.elm_filter_label_sizer.AddStretchSpacer(1)
        self.elm_filter_cb = wx.CheckBox(self, wx.ID_ANY, "Filter ELMS")
        # self.elm_filter_cb.SetValue(True)
        self.elm_filter_cb.Disable()
        self.elm_filter_cb.Bind(wx.EVT_CHECKBOX, self.OnFilterElms)
        self.ECRH_filter_cb = wx.CheckBox(self, wx.ID_ANY, "Filter ECRH")
        self.ECRH_filter_cb.Disable()
        self.ECRH_filter_cb.Bind(wx.EVT_CHECKBOX, self.OnFilterECRH)
        self.elm_filter_label_sizer.Add(self.elm_filter_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.elm_filter_label_sizer.Add(self.elm_filter_cb, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.elm_filter_label_sizer.Add(self.ECRH_filter_cb, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.control_sizer.Add(self.elm_filter_label_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line4 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line4, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.timepoint_label = wx.StaticText(self, wx.ID_ANY, \
                                             "Current selection - double click in plot on right to add/remove time points", \
                                             style=wx.ALIGN_CENTER_HORIZONTAL)
        self.timepoint_label.Wrap(400)
        self.timepoint_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.timepoint_label_sizer.Add(self.timepoint_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.control_sizer.Add(self.timepoint_label_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line4 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line4, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.used = []
        self.unused = []
        self.elm_times = []
        self.cta_times = []
        self.ECRH_times = []
        self.shot = 0
        self.edition = 0
        self.exp = "AUGD"
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used time points")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.shotlist = []
        self.ECRad_result_list = []
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.UnlockButton = wx.Button(self, wx.ID_ANY, 'Unlock')
        self.UnlockButton.Bind(wx.EVT_BUTTON, self.OnUnlockSelection)
        self.UnlockButton.Disable()
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.select_button_sizer.Add(self.UnlockButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused time points")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.control_sizer.Add(self.select_sizer, 1, \
                         wx.EXPAND | wx.ALL, 5)
        self.canvas_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.sizer.Add(self.control_sizer, 1, \
                wx.EXPAND, 0)
        self.sizer.Add(self.canvas_sizer, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.last_used_bt_vac_correction = Config.bt_vac_correction
        if(len(self.Scenario.plasma_dict["time"]) > 0):
            self.plasma_dict = dict(self.Scenario.plasma_dict)
            self.plasma_dict["eq_exp"] = Scenario.EQ_exp
            self.plasma_dict["eq_diag"] = Scenario.EQ_diag
            self.plasma_dict["eq_ed"] = Scenario.EQ_ed
            for t in self.plasma_dict["time"]:
                self.used.append("{0:2.4f}".format(t))
            self.used = list(set(self.used))
            self.used.sort()
            if(len(self.used) > 0):
                self.used_list.AppendItems(self.used)
            self.data_source = "self"
            self.loaded = True
        else:
            self.plasma_dict = None
            self.loaded = False
            self.data_source = None
        self.new_data_available = False

    def OnUpdate(self, evt):
        self.Results = evt.Results
        diag_id_list = []
        for key in self.Scenario.used_diags_dict.keys():
            diag_id_list.append(self.Scenario.used_diags_dict[key].name)
        if(self.diag_tc.GetValue() not in diag_id_list):
            i = 0
            while(diag_id_list[i] == "RMD" or diag_id_list[i] == "CEC"):
                i += 1
                if(i >= len(diag_id_list)):
                    break
            if(i < len(diag_id_list)):
                self.diag_tc.SetValue(diag_id_list[i])
            else:
                self.diag_tc.SetValue("")
        self.post_run = True
        self.used_list.Disable()
        self.unused_list.Disable()
        self.AddButton.Disable()
        self.RemoveButton.Disable()
        self.UnlockButton.Enable()
        self.new_data_available = False

    def OnLoadAUG(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading AUG data - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.Scenario.reset()
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        try:
            self.Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.Scenario.shot = self.shot_tc.GetValue()
        self.Scenario.IDA_exp = self.IDA_exp_tc.GetValue()
        self.Scenario.IDA_ed = self.IDA_ed_tc.GetValue()
        self.Scenario.default_diag = self.diag_tc.GetValue()
        self.pc_obj.reset(True)
        try:
            self.plasma_dict = load_IDA_data(self.Scenario.shot, \
                                None, self.Scenario.IDA_exp, self.Scenario.IDA_ed)
            vessel_bd = np.loadtxt(vessel_bd_file, skiprows=1)
            self.plasma_dict["vessel_bd"] = []
            self.plasma_dict["vessel_bd"].append(vessel_bd.T[0])
            self.plasma_dict["vessel_bd"].append(vessel_bd.T[1])
            self.plasma_dict["vessel_bd"] = np.array(self.plasma_dict["vessel_bd"])
            self.Scenario.EQ_exp = self.plasma_dict["eq_exp"]
            self.Scenario.EQ_diag = self.plasma_dict["eq_diag"]
            self.Scenario.EQ_ed = self.plasma_dict["eq_ed"]
            print("Updated equilibrium settings with values from IDA shotfile")
            self.EQ_exp_tc.SetValue(self.Scenario.EQ_exp)
            self.EQ_diag_tc.SetValue(self.Scenario.EQ_diag)
            self.EQ_ed_tc.SetValue(self.Scenario.EQ_ed)
            if(self.Config.bt_vac_correction != self.plasma_dict["Btf_corr"]):
                print("WARNING! Currently selected vacuum bt correction differs from IDA")
                print("ECRad GUI:", self.Config.bt_vac_correction)
                print("IDA:", self.plasma_dict["Btf_corr"])
            if(self.Config.ne_rhop_scale != self.plasma_dict["ne_rhop_scale_mean"]):
                print("WARNING! Currently selected ne_rhop_scale differs from IDA")
                print("ECRad GUI:", self.Config.ne_rhop_scale)
                print("IDA:", self.plasma_dict["ne_rhop_scale_mean"])
            if(self.Config.reflec_X != self.plasma_dict["RwallX"]):
                print("WARNING! Currently selected X-mode wall reflection coefficient differs from IDA")
                print("ECRad GUI:", self.Config.reflec_X)
                print("IDA:", self.plasma_dict["RwallX"])
            if(self.Config.reflec_O != self.plasma_dict["RwallO"]):
                print("WARNING! Currently selected O-mode wall reflection coefficient differs from IDA")
                print("ECRad GUI:", self.Config.reflec_O)
                print("IDA:", self.plasma_dict["RwallO"])
            if(self.Config.raytracing != self.plasma_dict["raytrace"]):
                print("WARNING! Refraction was not considered in IDA, but is considered in current ECRad configuation")
            if(self.Scenario.IDA_ed != self.plasma_dict["ed"]):
                print("IDA edition: ", self.plasma_dict["ed"])
                print("ECRad GUI IDA edition updated")
                self.Scenario.IDA_ed = self.plasma_dict["ed"]
        except Exception as e:
            print("Could not load shotfile dd Error follows")
            print(e)
            return
        if(len(self.plasma_dict["time"]) == 0):
            return
        if(len(self.plasma_dict["time"]) > 1):
            self.delta_t = 0.5 * np.mean(self.plasma_dict["time"][1:len(self.plasma_dict["time"])] - self.plasma_dict["time"][0:len(self.plasma_dict["time"]) - 1])
        else:
            self.delta_t = 1.e-3
        for t in self.plasma_dict["time"]:
            self.unused.append("{0:2.4f}".format(t))
        self.unused = list(set(self.unused))
        self.unused.sort()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)
        self.pc_obj.reset(True)
        Te_indices = np.zeros((len(self.plasma_dict["Te"]), len(self.plasma_dict["Te"][0])), dtype=np.bool)
        IDA_labels = []
        rhop_range = [0.2, 0.95]
        for index in range(len(self.plasma_dict["time"])):
            for rhop in rhop_range:
                Te_indices[index][np.argmin(np.abs(self.plasma_dict["rhop_prof"][index] - rhop))] = True
                if(index == 0):
                    IDA_labels.append("$T_\mathrm{e}$" + "({0:1.2f})".format(self.plasma_dict["rhop_prof"][index][np.argmin(np.abs(self.plasma_dict["rhop_prof"][index] - rhop))]))
        if(len(self.plasma_dict["ECE_rhop"]) > 0):
            ECE_indices = np.zeros((len(self.plasma_dict["ECE_rhop"]), len(self.plasma_dict["ECE_rhop"][0])), dtype=np.bool)
            ECE_labels = []
            ECRad_labels = []
            for index in range(len(self.plasma_dict["time"])):
                for rhop in rhop_range:
                    ECE_indices[index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))] = True
                    if(index == 0):
                        ECE_labels.append("ECE $T_\mathrm{rad}$" + "({0:1.2f})".format(self.plasma_dict["ECE_rhop"][index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))]))
                        ECRad_labels.append("ECRad $T_\mathrm{rad}$" + "({0:1.2f})".format(self.plasma_dict["ECE_rhop"][index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))]))
                if(np.count_nonzero(ECE_indices[index]) != len(rhop_range)):
                    print("Could not find ECE measurements for t = {0:1.4f}".format(self.plasma_dict["time"][index]))
                    print("Choosing first and last channel")
                    ECE_indices[index][:] = False
                    ECE_indices[index][0] = True
                    ECE_indices[index][-1] = True
        if(self.diag_tc.GetValue() in self.Scenario.avail_diags_dict.keys() and self.diag_tc.GetValue() != 'EXT'):
            diag_obj = self.Scenario.avail_diags_dict[self.diag_tc.GetValue()]
            if(diag_obj.name != "ECE"):
                if(AUG):
                    try:
                        diag_time, diag_data = get_diag_data_no_calib(diag_obj, self.Config.shot, preview=True)
                        if(len(diag_time) != len(diag_data[0])):
                            print("WARNING: The time base does not have the same length as the signal")
                            print(diag_time.shape , diag_data.shape)
                            print("All time points beyond the last index of the signal are omitted")
                        diag_time = diag_time[:len(diag_data[0])]
                        shown_ch = np.zeros(len(diag_data), dtype=np.bool)
                        shown_ch_nr = np.array(range(len(shown_ch)), np.int)
                        diag_labels = []
                        n = int(np.ceil(float(len(shown_ch)) / 2.0))
                        if(diag_obj.name == "CTA"):
                            shown_ch[4] = True
                            shown_ch[41] = True
                            diag_labels.append(diag_obj.name + ": Ch {0:d}".format(3))
                            diag_labels.append(diag_obj.name + ": Ch {0:d}".format(40))
                        else:
                            for i in shown_ch_nr[::n]:
                                if(diag_obj.name == "ECN" or diag_obj.name == "ECO"):
                                    diag_labels.append(diag_obj.name + " - LOS 9 : Ch {0:d}".format(i + 1))
                                else:
                                    diag_labels.append(diag_obj.name + ": Ch {0:d}".format(i + 1))
                                shown_ch[i] = True
                        diag_data = diag_data[shown_ch]
                    except Exception as e:
                        print("Could not load diagnostic data")
                        print(e)
                        diag_time = None
                        diag_data = None
                        diag_labels = None
                elif(TCV):
                    print("Loading diagnostic data not yet implemented for TCV")
                    diag_time = None
                    diag_data = None
                    diag_labels = None
                else:
                    print("No mashine specified")
                    diag_time = None
                    diag_data = None
                    diag_labels = None
            else:
                diag_time = None
                diag_data = None
                diag_labels = None
        else:
            diag_time = None
            diag_data = None
            diag_labels = None
        try:
            t, divertor_cur = get_divertor_currents(self.Scenario.shot)
            div_cur = [t, divertor_cur]
        except Exception as e:
            print(e)
            print("Could not get divertor currents")
            div_cur = None
        if(diag_time is not None):
            diag_indices = np.zeros(len(diag_time), dtype=np.bool)
            diag_indices[:] = False
            if(diag_obj.name == "CTA"):
                self.FilterCTA(diag_obj)
            elif(diag_obj.name == "IEC"):
                self.FilterIEC(diag_obj)
            for t in self.unused:
                diag_indices[np.argmin(np.abs(diag_time - (float(t) - 500.e-6))):np.argmin(np.abs(diag_time - (float(t) + 500.e-6)))] = True
            diag_time = diag_time[diag_indices]
            diag_data = diag_data.T[diag_indices].T
        if(len(self.plasma_dict["ECE_rhop"]) > 0):
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.Scenario.shot, self.plasma_dict["time"], diag_time, np.reshape(self.plasma_dict["Te"][Te_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, \
                                                    IDA_labels, np.reshape(np.average(self.plasma_dict["ECE_dat"], axis=1)[ECE_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, ECE_labels, \
                                                    np.reshape(self.plasma_dict["ECE_mod"][ECE_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, ECRad_labels, \
                                                    diag_data, diag_labels, div_cur)
        else:
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.Scenario.shot, self.plasma_dict["time"], diag_time, np.reshape(self.plasma_dict["Te"][Te_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, \
                                                    IDA_labels, [], [], [], [], diag_data, diag_labels, div_cur)
        self.canvas.draw()
        self.elm_filter_cb.Enable()
        self.ECRH_filter_cb.Enable()
        self.loaded = True
        self.new_data_available = True
        self.data_source = "aug_database"
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('IDA data loaded successfully!')
        self.GetEventHandler().ProcessEvent(evt)

    def OnLoadfromMat(self, evt):
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.Scenario.reset()
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        try:
            self.Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        dlg = wx.FileDialog(\
            self, message="Choose a .mat file for input", \
            defaultDir=self.Config.working_dir, \
            wildcard=('Matlab files (*.mat)|*.mat|All fiels (*.*)|*.*'),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() != wx.ID_OK):
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self.plasma_dict = load_plasma_from_mat(path)
        if(self.plasma_dict is None):
            return
        self.Scenario.shot = self.plasma_dict["shot"]
        self.shot_tc.SetValue(self.plasma_dict["shot"])
        self.Scenario.EQ_exp = self.plasma_dict["eq_exp"]
        self.Scenario.EQ_diag = self.plasma_dict["eq_diag"]
        self.Scenario.EQ_ed = self.plasma_dict["eq_ed"]
        print("Updated equilibrium settings with values from IDA shotfile")
        self.EQ_exp_tc.SetValue(self.Scenario.EQ_exp)
        self.EQ_diag_tc.SetValue(self.Scenario.EQ_diag)
        self.EQ_ed_tc.SetValue(self.Scenario.EQ_ed)
        self.delta_t = 0.5 * np.mean(self.plasma_dict["time"][1:len(self.plasma_dict["time"])] - self.plasma_dict["time"][0:len(self.plasma_dict["time"]) - 1])
        for t in self.plasma_dict["time"]:
            self.unused.append("{0:2.5f}".format(t))
        self.unused = list(set(self.unused))
        self.unused.sort()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)
        self.pc_obj.reset(True)
        Te_indices = np.zeros((len(self.Scenario.plasma_dict["Te"]), len(self.Scenario.plasma_dict["Te"][0])), dtype=np.bool)
        IDA_labels = []
        rhop_range = [0.2, 0.95]
        for index in range(len(self.plasma_dict["time"])):
            for rhop in rhop_range:
                Te_indices[index][np.argmin(np.abs(self.Scenario.plasma_dict["rhop_prof"][index] - rhop))] = True
                if(index == 0):
                    IDA_labels.append("$T_\mathrm{e}$" + "({0:1.2f})".format(self.Scenario.plasma_dict["rhop_prof"][index][np.argmin(np.abs(self.Scenario.plasma_dict["rhop_prof"][index] - rhop))]))
        diag_time = None
        diag_data = None
        diag_labels = None
        self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.Scenario.shot, self.plasma_dict["time"], diag_time, np.reshape(self.Scenario.plasma_dict["Te"][Te_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, \
                                                    IDA_labels, [], [], \
                                                    [], [], \
                                                    diag_data, diag_labels, None)
        self.canvas.draw()
        self.loaded = True
        self.new_data_available = True
        self.data_source = "file:" + path
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Data loaded successfully!')
        self.GetEventHandler().ProcessEvent(evt)

    def UpdateNeeded(self):
        return self.new_data_available

    def LoadScenario(self, Scenario, Config, callee):
        if(self.loaded == False):
            print("No plasma data loaded yet!")
            return Scenario
        elif(len(self.used) == 0):
            print("No time points selected!")
            return Scenario
        # Get rid of the old stuff it will be updated now
        old_time_list = Scenario.plasma_dict["time"]
        old_eq_list = Scenario.plasma_dict["eq_data"]
        Scenario.reset()
        Scenario.shot = self.shot_tc.GetValue()
        Scenario.IDA_exp = self.IDA_exp_tc.GetValue()
        Scenario.IDA_ed = self.IDA_ed_tc.GetValue()
        Scenario.default_diag = self.diag_tc.GetValue()
        Scenario.EQ_exp = self.plasma_dict["eq_exp"]
        Scenario.EQ_diag = self.plasma_dict["eq_diag"]
        Scenario.EQ_ed = self.plasma_dict["eq_ed"]
        Scenario.plasma_dict["vessel_bd"] = self.plasma_dict["vessel_bd"]
        EQObj = None
        if(not self.data_source == "aug_database" and  Config.bt_vac_correction != 1.0):
            print("Warning ", Config.bt_vac_correction, " differs from 1")
            print("Since vacuum component of Bt cannot be determined for external data the entire Bt will be scaled")
        profile_dimension = len(self.plasma_dict["Te"][0].shape)
        if(profile_dimension == 1):
            Scenario.plasma_dict["rhop_prof"] = []
        for time in self.used:
            Scenario.plasma_dict["time"].append(float(time))
            itime = np.argmin(np.abs(self.plasma_dict["time"] - Scenario.plasma_dict["time"][-1]))
            if(profile_dimension == 1):
                Scenario.plasma_dict["rhop_prof"].append(self.plasma_dict["rhop_prof"][itime])
            Scenario.plasma_dict["Te"].append(self.plasma_dict["Te"][itime] * Config.Te_scale)
            Scenario.plasma_dict["ne"].append(self.plasma_dict["ne"][itime] * Config.ne_scale)
            if(float(time) in old_time_list and self.last_used_bt_vac_correction == Config.bt_vac_correction):
                Scenario.plasma_dict["eq_data"].append(old_eq_list[np.argmin(np.abs(old_time_list - float(time)))])
            elif(self.data_source == "aug_database"):
                if(EQObj is None):
                    EQObj = EQData(Scenario.shot, EQ_exp=Scenario.EQ_exp, EQ_diag=Scenario.EQ_diag, EQ_ed=Scenario.EQ_ed, bt_vac_correction=Config.bt_vac_correction)
                Scenario.plasma_dict["eq_data"].append(EQObj.GetSlice(Scenario.plasma_dict["time"][-1]))
            else:
                Scenario.plasma_dict["eq_data"].append(self.plasma_dict["eq_data"][itime])
                Scenario.plasma_dict["eq_data"][-1].Bt *= Config.bt_vac_correction
        Scenario.data_source = self.data_source
        Scenario.plasma_set = True
        self.new_data_available = False
        self.Scenario = Scenario
        self.last_used_bt_vac_correction = Config.bt_vac_correction
        return Scenario

    def OnFilterElms(self, evt):
        if(self.data_source != "aug_database"):
            print("Elm sync not available for non-AUG data")
        filter_elms = self.elm_filter_cb.GetValue()
        if(filter_elms):
            try:
                idxNoElm = ElmSync.ElmExtract(np.array(self.used, dtype=np.double), self.Scenario.shot, plot=False, preFac=0.15,
                                            postFac=0.6, Experiment='AUGD')
                good_time = []
                bad_time = len(self.used) - len(idxNoElm)
                for i in range(len(self.used)):
                    if(i in idxNoElm):
                        good_time.append(self.used[i])
                i_time = 0
                while(i_time < len(self.used)):
                    if(self.used[i_time] not in good_time):
                        self.elm_times.append(self.used.pop(i_time))
                    else:
                        i_time += 1
                idxNoElm = ElmSync.ElmExtract(np.array(self.unused, dtype=np.double), self.Scenario.shot, plot=False, preFac=0.15,
                                            postFac=0.6, Experiment='AUGD')
                good_time = []
                bad_time += len(self.unused) - len(idxNoElm)
                for i in range(len(self.unused)):
                    if(i in idxNoElm):
                        good_time.append(self.unused[i])
                i_time = 0
                while(i_time < len(self.unused)):
                    if(self.unused[i_time] not in good_time):
                        self.elm_times.append(self.unused.pop(i_time))
                    else:
                        i_time += 1
                self.elm_times.sort()
                self.used_list.Clear()
                if(len(self.used) > 0):
                    self.used_list.AppendItems(self.used)
                self.unused_list.Clear()
                if(len(self.unused) > 0):
                    self.unused_list.AppendItems(self.unused)
                print("Removed a total of ", bad_time, " elm influenced time points")
            except Exception as e:
                print("This discharge does not have an ELM shotfile")
                print("Maybe this is an L-mode discharge ?")
                self.elm_filter_cb.SetValue(False)
                bad_time = 0
        else:
            bad_time = len(self.elm_times)
            while(len(self.elm_times) > 0):
                self.unused.append(self.elm_times.pop(0))
            self.unused.sort()
            self.unused_list.Clear()
            if(len(self.unused) > 0):
                self.unused_list.AppendItems(self.unused)
            print("Added a total of ", bad_time, " elm influenced time points")
        if(bad_time > 0):
            evt = NewStatusEvt(Unbound_EVT_REPLOT, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)

    def OnFilterECRH(self, evt):
        filter_ECRH = self.ECRH_filter_cb.GetValue()
        if(filter_ECRH):
            try:
                idxECRHOff = identify_ECRH_on_phase(self.Scenario.shot, np.array(self.used, dtype=np.double))
                good_time = []
                bad_time = len(self.used) - len(idxECRHOff)
                for i in range(len(self.used)):
                    if(i in idxECRHOff):
                        good_time.append(self.used[i])
                i_time = 0
                while(i_time < len(self.used)):
                    if(self.used[i_time] not in good_time):
                        self.ECRH_times.append(self.used.pop(i_time))
                    else:
                        i_time += 1
                idxECRHOff = identify_ECRH_on_phase(self.Scenario.shot, np.array(self.unused, dtype=np.double))
                good_time = []
                bad_time += len(self.unused) - len(idxECRHOff)
                for i in range(len(self.unused)):
                    if(i in idxECRHOff):
                        good_time.append(self.unused[i])
                i_time = 0
                while(i_time < len(self.unused)):
                    if(self.unused[i_time] not in good_time):
                        self.ECRH_times.append(self.unused.pop(i_time))
                    else:
                        i_time += 1
                self.ECRH_times.sort()
                self.used_list.Clear()
                if(len(self.used) > 0):
                    self.used_list.AppendItems(self.used)
                self.unused_list.Clear()
                if(len(self.unused) > 0):
                    self.unused_list.AppendItems(self.unused)
                print("Removed a total of ", bad_time, " elm influenced time points")
            except Exception as e:
                print(e)
                print("This discharge does not have an ECRH shotfile")
                print("Maybe there is ECRH in this discharge ?")
                self.elm_filter_cb.SetValue(False)
                bad_time = 0
        else:
            bad_time = len(self.elm_times)
            while(len(self.ECRH_times) > 0):
                self.unused.append(self.ECRH_times.pop(0))
            self.unused.sort()
            self.unused_list.Clear()
            if(len(self.unused) > 0):
                self.unused_list.AppendItems(self.unused)
            print("Added a total of ", bad_time, " ECRH on time points")
        if(bad_time > 0):
            evt = NewStatusEvt(Unbound_EVT_REPLOT, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)

    def FilterCTA(self, diag):
        print("Removing all time points with closed pin-switch")
        good_time = []
        idxCTA = filter_CTA(self.Scenario.shot, np.array(self.unused, dtype=np.double), diag.diag, diag.exp, diag.ed)
        for i in range(len(self.unused)):
            if(i in idxCTA):
                good_time.append(self.unused[i])
        i_time = 0
        while(i_time < len(self.unused)):
            if(self.unused[i_time] not in good_time):
                self.cta_times.append(self.unused.pop(i_time))
            else:
                i_time += 1
        self.cta_times.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def FilterIEC(self, diag):
        print("Removing all time points with closed pin-switch")
        good_time = []
        try:
            idxIEC = filter_CTA(self.Scenario.shot, np.array(self.unused, dtype=np.double), "CTA", "AUGD", 0)
        except:
            try:
                idxIEC = filter_CTA(self.Scenario.shot, np.array(self.unused, dtype=np.double), "CTA", "SDENK", 0)
            except:
                print("No CTA shot file - PIN switch filtering not possible")
                return
        for i in range(len(self.unused)):
            if(i in idxIEC):
                good_time.append(self.unused[i])
        i_time = 0
        while(i_time < len(self.unused)):
            if(self.unused[i_time] not in good_time):
                self.cta_times.append(self.unused.pop(i_time))
            else:
                i_time += 1
        self.cta_times.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def GetUsedIDAIndices(self):
        used_timepoints = np.array(self.used, dtype=np.double)
        IDA_timepoint_used = np.zeros(len(self.plasma_dict["time"]), dtype=np.bool)
        for t in used_timepoints:
            if(np.min(np.abs(t - self.plasma_dict["time"])) > self.delta_t):
                print("Error: Somehow a time point got into the used pile, without having a corresponding IDA time point")
            else:
                IDA_timepoint_used[np.argmin(np.abs(t - self.plasma_dict["time"]))] = True
        return IDA_timepoint_used

    def OnFill(self, evt):
        time = np.linspace(self.t_start_tc.GetValue(), self.t_end_tc.GetValue(), self.steps_tc.GetValue())
        if(len(self.unused) == 0):
            print("No IDA time points available - load data first")
            return
        warned = False
        IDA_timepoints = np.array(self.unused, dtype=np.double)
        fill_delta_t = np.mean(time[1:len(time)] - time[0:len(time) - 1])
        while(len(self.used) > 0):
            self.unused.append(self.used.pop(0))
            # Necessary to avoid np.min([])
        time_points_added = 0
        for t in time:
            if(t > np.max(IDA_timepoints) or t < np.min(IDA_timepoints) and not warned):
                print("Warning!: Some of the selected time points lie outside the range of IDA time points")
                warned = True
            elif(np.min(np.abs(IDA_timepoints - t)) > fill_delta_t):
                print("Warning!: One time point could not be mapped to an IDA time point - Probably Lithium beam chopped or ELM if filtering is activated")
            else:
                self.used.append(self.unused.pop(np.argmin(np.abs(IDA_timepoints - t))))
                IDA_timepoints = np.array(self.unused, dtype=np.double)  # Update - otherwise index wrong
                time_points_added += 1
        print("Added a total of {0:n}/{1:n} time points".format(time_points_added, len(time)))
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
        self.new_data_available = True

    def OnAdd(self, evt):
        time = np.linspace(self.t_start_tc.GetValue(), self.t_end_tc.GetValue(), self.steps_tc.GetValue())
        if(len(self.unused) == 0):
            print("No IDA time points available - load data first")
            return
        warned = False
        Add_delta_t = np.mean(time[1:len(time)] - time[0:len(time) - 1])
        IDA_timepoints = np.array(self.unused, dtype=np.double)
        for t in time:
            if(t > np.max(IDA_timepoints) or t < np.min(IDA_timepoints) and not warned):
                print("Warning!: Some of the selected time points lie outside the range of IDA time points")
                warned = True
            elif(np.min(np.abs(IDA_timepoints - t)) > Add_delta_t):
                print("Warning!: One time point could not be mapped to an IDA time point - Probably Lithium beam chopped")
            else:
                self.used.append(self.unused.pop(np.argmin(np.abs(IDA_timepoints - t))))
                IDA_timepoints = np.array(self.unused, dtype=np.double)  # Update - otherwise index wrong
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
        self.new_data_available = True

    def OnPlotClick(self, evt):
        if(evt.dblclick):
            t = evt.xdata
            unused_timepoints = np.array(self.unused, np.double)
            used_timepoints = np.array(self.used, np.double)
            if(len(used_timepoints) == 0):
                used_timepoints = np.array([-1.0])
                # to avoid np.min([])
            if(np.min(np.abs(unused_timepoints - t)) <= self.delta_t):
                self.used.append(self.unused.pop(np.argmin(np.abs(unused_timepoints - t))))
            elif(np.min(np.abs(used_timepoints - t)) <= self.delta_t):
                self.unused.append(self.used.pop(np.argmin(np.abs(used_timepoints - t))))
            else:
                print("No IDA data for t = {0:1.4f} ".format(t))
                return
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
            self.new_data_available = True

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
        self.new_data_available = True

    def OnUnlockSelection(self, evt):
        self.used_list.Enable()
        self.unused_list.Enable()
        self.AddButton.Enable()
        self.RemoveButton.Enable()
        evt = LockExportEvt(Unbound_EVT_LOCK_EXPORT, self.GetId())
        self.Parent.Parent.GetEventHandler().ProcessEvent(evt)

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
        self.new_data_available = True

#    def OnMakeLUKEdata(self, evt):
#        if(len(self.used) == 0):
#            print("No time point used!")
#            return
#        time = float(self.used[0])
#        i_time = np.argmin(np.abs(self.time - time))
#        try:
#            self.Config, DiagDict, time_list_box = self.Parent.Parent.NotebookPanel.Notebook.GatherInfo()
#        except ValueError as e:
#            print("Failed to parse Configuration")
#            print("Reason: " + e)
#            return
#        make_LUKE_data(self.Config.working_dir, self.Scenario.shot, self.time, i_time, self.Scenario.plasma_dict, \
#                        self.Config.EQ_exp, self.Config.EQ_diag, self.Config.EQ_ed, self.Config.bt_vac_correction)
#    def OnMakeLUKEMat(self, evt):
#        if(len(self.used) == 0):
#            print("No time point used!")
#            return
#        times = np.array(self.used, dtype=np.double)
#        try:
#            self.Config, DiagDict, time_list_box = self.Parent.Parent.NotebookPanel.Notebook.GatherInfo()
#        except ValueError as e:
#            print("Failed to parse Configuration")
#            print("Reason: " + e)
#            return
#        make_LUKE_input_mat(self.Config.working_dir, self.Config.shot, times, IDA_exp=self.Config.IDA_exp, \
#                            IDA_ed=self.Config.IDA_ed, EQ_exp=self.Config.EQ_exp, EQ_diag=self.Config.EQ_diag, \
#                            EQ_ed=self.Config.EQ_ed, bt_vac_correction=self.Config.bt_vac_correction)

    def ChangeCursor(self, event):
        if(Phoenix):
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

