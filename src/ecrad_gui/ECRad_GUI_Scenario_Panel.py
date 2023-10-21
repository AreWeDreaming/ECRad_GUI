'''
Created on Mar 21, 2019

@author: Severin Denk
'''
from ecrad_pylib.Global_Settings import globalsettings
import os
from ecrad_gui.ECRad_GUI_Widgets import simple_label_tc
from ecrad_gui.ECRad_GUI_Dialogs import IMASTimeBaseSelectDlg,IMASSelectDialog, OMASdbSelectDialog
import wx
from ecrad_pylib.WX_Events import EVT_UPDATE_DATA, NewStatusEvt, Unbound_EVT_NEW_STATUS, \
                                  Unbound_EVT_REPLOT, LockExportEvt, Unbound_EVT_LOCK_EXPORT, \
                                  GenerticEvt, Unbound_OMAS_LOAD_FINISHED, OMAS_LOAD_FINISHED
from ecrad_pylib.Plotting_Core import PlottingCore
from ecrad_pylib.Parallel_Utils import WorkerThread
import numpy as np
from ecrad_pylib.ECRad_Interface import load_from_plasma, load_plasma_from_mat
from ecrad_pylib.Plotting_Configuration import plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from ecrad_gui.ECRad_GUI_Dialogs import Use3DConfigDialog
from ecrad_pylib.ECRad_Scenario import ECRadScenario
from ecrad_pylib.ECRad_Results import ECRadResults
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
from ecrad_pylib.Equilibrium_Utils import EQDataExt
from copy import deepcopy
if(globalsettings.AUG):
    from ecrad_pylib.Equilibrium_Utils_AUG import EQData, vessel_bd_file, check_Bt_vac_source
    from ecrad_pylib.Shotfile_Handling_AUG import load_IDA_data, get_diag_data_no_calib, get_divertor_currents, filter_CTA
    from ecrad_pylib.Get_ECRH_Config import identify_ECRH_on_phase
    from ecrad_pylib.Elm_Sync import ElmExtract

class ScenarioSelectPanel(wx.Panel):
    def __init__(self, parent, Scenario, Config):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(8.5, 8.0), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(4.5, 4.5), tight_layout=False)
        self.fig.clf()
        self.Result_for_ext_launch = None
        self.Config = Config
        self.delta_t = 5.e-4
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.canvas.mpl_connect('button_press_event', self.OnPlotClick)
        self.Bind(wx.EVT_ENTER_WINDOW, self.ChangeCursor)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(OMAS_LOAD_FINISHED, self.OnOmasLoaded)
        self.canvas.draw()
        self.pc_obj = PlottingCore(self.fig, self.dummy_fig, False)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        th = self.plot_toolbar.GetSize().Get()[1]
        fw = self.plot_toolbar.GetSize().Get()[0]
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.control_sizer = wx.BoxSizer(wx.VERTICAL)
        self.load_data_line = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.load_data_line, 0, \
                               wx.EXPAND | wx.ALL, 5)
        self.shot_data_grid_sizer = wx.GridSizer(0, 4, 0, 0)
        if(globalsettings.AUG):
            self.shot_tc = simple_label_tc(self, "Shot #", Scenario["shot"], "integer")
            self.shot_data_grid_sizer.Add(self.shot_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.IDA_exp_tc = simple_label_tc(self, "IDA exp", Scenario["AUG"]["IDA_exp"], "string")
            self.shot_data_grid_sizer.Add(self.IDA_exp_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.IDA_ed_tc = simple_label_tc(self, "IDA ed", Scenario["AUG"]["IDA_ed"], "integer")
            self.shot_data_grid_sizer.Add(self.IDA_ed_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.load_aug_data_button = wx.Button(self, wx.ID_ANY, "Load AUG data")
            self.load_aug_data_button.Bind(wx.EVT_BUTTON, self.OnLoadAUG)
            self.shot_data_grid_sizer.Add(self.load_aug_data_button, 0, \
                                         wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND | wx.ALL, 5)
            self.EQ_exp_tc = simple_label_tc(self, "EQ exp", Scenario["AUG"]["EQ_exp"], "string")
            self.shot_data_grid_sizer.Add(self.EQ_exp_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.EQ_diag_tc = simple_label_tc(self, "EQ diag", Scenario["AUG"]["EQ_diag"], "string")
            self.shot_data_grid_sizer.Add(self.EQ_diag_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.EQ_ed_tc = simple_label_tc(self, "EQ ed", Scenario["AUG"]["EQ_ed"], "integer")
            self.shot_data_grid_sizer.Add(self.EQ_ed_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
            self.diag_tc = simple_label_tc(self, "Comapare diag", Scenario.default_diag, "string")
            self.shot_data_grid_sizer.Add(self.diag_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
        else:
            self.shot_tc = simple_label_tc(self, "Shot #", Scenario["shot"], "integer", readonly=True)
            self.shot_data_grid_sizer.Add(self.shot_tc, 0, \
                             wx.ALIGN_CENTER | wx.ALL, 5)
        self.control_sizer.Add(self.shot_data_grid_sizer, 0, \
                             wx.EXPAND | wx.ALL, 5)
        self.line_shot_data = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line_shot_data, 0, \
                               wx.EXPAND | wx.ALL, 5)
        self.load_Scenario_from_mat_button = wx.Button(self, wx.ID_ANY, "Load ECRadScenario")
        self.load_Scenario_from_mat_button.Bind(wx.EVT_BUTTON, self.OnLoadScenario)
        self.load_Scenario_from_imas_button = wx.Button(self, wx.ID_ANY, "Load from IMAS database")
        self.load_Scenario_from_imas_button.Bind(wx.EVT_BUTTON, self.OnLoadIMAS)
        self.load_Scenario_from_omas_button = wx.Button(self, wx.ID_ANY, "Load from OMAS")
        self.load_Scenario_from_omas_button.Bind(wx.EVT_BUTTON, self.OnLoadOMAS)
        self.load_from_mat_button = wx.Button(self, wx.ID_ANY, "Load from *.nc/*.mat")
        self.load_from_mat_button.Bind(wx.EVT_BUTTON, self.OnLoadfromFile)
        self.load_Result_from_mat_button = wx.Button(self, wx.ID_ANY, "Load ECRadResult")
        self.load_Result_from_mat_button.Bind(wx.EVT_BUTTON, self.OnLoadResult)
        self.use_3D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_3D_cb = wx.CheckBox(self, wx.ID_ANY, "Use 3D equilibrium")
        self.use_3D_cb.Bind(wx.EVT_CHECKBOX, self.OnUse3D)
        self.use_3D_cb.SetValue(Scenario["plasma"]["eq_dim"] == 3)
        self.use_3D_config_button = wx.Button(self, wx.ID_ANY, "3D Settings")
        if(Scenario["plasma"]["eq_dim"] != 3):
            self.use_3D_config_button.Disable()
        else:
            self.load_from_mat_button.Disable()
        self.use_3D_config_button.Bind(wx.EVT_BUTTON, self.OnUse3DConfig)
        self.use_3D_sizer.Add(self.use_3D_cb, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.use_3D_sizer.Add(self.use_3D_config_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.control_sizer.Add(self.use_3D_sizer, 0, wx.EXPAND | wx.ALL, 5)
#        self.load_GENE_button = wx.Button(self, wx.ID_ANY, "Load GENE dist.")
#        self.load_GENE_button.Bind(wx.EVT_BUTTON, self.OnLoadGene)
#        self.load_data_sizer.Add(self.load_GENE_button, 0, \
#                         wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.control_sizer.Add(self.load_Scenario_from_mat_button, 0, \
                               wx.EXPAND |  wx.ALL, 5)
        self.control_sizer.Add(self.load_Scenario_from_imas_button, 0, \
                               wx.EXPAND |  wx.ALL, 5)
        self.control_sizer.Add(self.load_Scenario_from_omas_button, 0, \
                               wx.EXPAND |  wx.ALL, 5)
        self.control_sizer.Add(self.load_from_mat_button, 0, \
                               wx.EXPAND |  wx.ALL, 5)
        self.control_sizer.Add(self.load_Result_from_mat_button, 0, \
                               wx.EXPAND |  wx.ALL, 5)
        self.line1 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line1, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.modifierlabel = wx.StaticText(self, wx.ID_ANY, "Scenario modifiers")
        self.control_sizer.Add(self.modifierlabel, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ScenarioModifierGrid = wx.GridSizer(0,4,0,0)
        self.Bt_vac_scale_tc = simple_label_tc(self, "vacuum B_t scale", Scenario["scaling"]["Bt_vac_scale"], "real")
        self.ScenarioModifierGrid.Add(self.Bt_vac_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.Te_rhop_scale_tc = simple_label_tc(self, "rhop scale for Te", Scenario["scaling"]["Te_rhop_scale"], "real")
        self.ScenarioModifierGrid.Add(self.Te_rhop_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ne_rhop_scale_tc = simple_label_tc(self, "rhop scale for ne", Scenario["scaling"]["ne_rhop_scale"], "real")
        self.ScenarioModifierGrid.Add(self.ne_rhop_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.Te_scale_tc = simple_label_tc(self, "Te scale", Scenario["scaling"]["Te_scale"], "real")
        self.ScenarioModifierGrid.Add(self.Te_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ne_scale_tc = simple_label_tc(self, "ne scale", Scenario["scaling"]["ne_scale"], "real")
        self.ScenarioModifierGrid.Add(self.ne_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.control_sizer.Add(self.ScenarioModifierGrid, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.line2 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line2, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.regular_label = wx.StaticText(self, wx.ID_ANY, "For regular time intervals")
        self.label_regular_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label_regular_sizer.AddStretchSpacer(1)
        self.label_regular_sizer.Add(self.regular_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.label_regular_sizer.AddStretchSpacer(1)
        self.control_sizer.Add(self.label_regular_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line3 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line3, 0, \
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
        self.line4 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line4, 0, \
                         wx.EXPAND | wx.ALL, 5)
        if(globalsettings.AUG):
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
            self.line5 = wx.StaticLine(self, wx.ID_ANY)
            self.control_sizer.Add(self.line5, 0, \
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
        self.line6 = wx.StaticLine(self, wx.ID_ANY)
        self.control_sizer.Add(self.line6, 0, \
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
        self.avail_diags_dict = Scenario["avail_diags_dict"]
        if(len(Scenario["time"]) > 0):
            self.plasma_dict = Scenario["plasma"].copy()
            self.plasma_dict["time"] = Scenario["time"]
            self.plasma_dict["shot"] = Scenario["shot"]
            if(globalsettings.AUG):
                self.plasma_dict["IDA_exp"] = Scenario["AUG"]["IDA_exp"]
                self.plasma_dict["IDA_ed"] = Scenario["AUG"]["IDA_ed"]
                self.plasma_dict["EQ_exp"] = Scenario["AUG"]["EQ_exp"]
                self.plasma_dict["EQ_diag"] = Scenario["AUG"]["EQ_diag"]
                self.plasma_dict["EQ_ed"] = Scenario["AUG"]["EQ_ed"]
            for t in self.plasma_dict["time"]:
                self.used.append("{0:2.4f}".format(t))
            self.used = list(set(self.used))
            self.used.sort()
            if(len(self.used) > 0):
                self.used_list.AppendItems(self.used)
            self.data_source = Scenario.data_source
            self.use_3D_eq = Scenario["plasma"]["eq_dim"] == 3
            self.eq_data_3D = Scenario["plasma"]["eq_data_3D"]
            self.loaded = True
        else:
            self.plasma_dict = {}
            self.loaded = False
            self.data_source = None
            self.use_3D_eq = False
        self.new_data_available = False
        self.post_run = False

    def OnUse3D(self, evt):
        if(self.use_3D_cb.GetValue()):
            self.use_3D_config_button.Enable()
            self.load_from_mat_button.Disable()
            self.new_data_available = True
        else:
            self.use_3D_config_button.Disable()
            self.load_from_mat_button.Enable()
            self.new_data_available = True
            
    def OnUse3DConfig(self, evt):
        Config_Dlg = Use3DConfigDialog(self, self.plasma_dict["eq_data_3D"], self.Config["Execution"]["working_dir"])
        if(Config_Dlg.ShowModal() == wx.ID_OK):
            self.eq_data_3D = Config_Dlg.eq_data_3D
            self.use_3D_eq = Config_Dlg.use_3D
            self.new_data_available = True
        Config_Dlg.Destroy()

    def OnUpdate(self, evt):
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        self.Config = evt.Results.Config
        self.SetFromNewScenario(evt.Results.Scenario, evt.Results.data_origin, draw=False)
        while self.unused_list.GetCount() > 0:
            self.add_to_used([0])
        self.post_run = True
        self.used_list.Disable()
        self.unused_list.Disable()
        self.AddButton.Disable()
        self.RemoveButton.Disable()
        self.UnlockButton.Enable()
        
    def UpdateContent(self, Scenario, diag_name="ECE"):
        # Sets the content of textboxes without updating the scenario
        self.shot_tc.SetValue(Scenario["shot"])
        self.plasma_dict["shot"] = Scenario["shot"]
        if(globalsettings.AUG):
            self.IDA_exp_tc.SetValue(Scenario["AUG"]["IDA_exp"]) 
            self.IDA_ed_tc.SetValue(Scenario["AUG"]["IDA_ed"]) 
            self.plasma_dict["IDA_exp"] = Scenario["AUG"]["IDA_exp"]
            self.plasma_dict["IDA_ed"] = Scenario["AUG"]["IDA_ed"]
            self.diag_tc.SetValue(diag_name)
            self.EQ_exp_tc.SetValue(Scenario["AUG"]["EQ_exp"])
            self.EQ_diag_tc.SetValue(Scenario["AUG"]["EQ_diag"])
            self.EQ_ed_tc.SetValue(Scenario["AUG"]["EQ_ed"])
        if(Scenario["plasma"]["eq_dim"] == 3):
            self.use_3D_cb.SetValue(True)
            self.use_3D_config_button.Enable()
            self.load_from_mat_button.Disable()
        else:
            self.use_3D_cb.SetValue(False)
        self.Bt_vac_scale_tc.SetValue(Scenario["scaling"]["Bt_vac_scale"])
        self.Te_rhop_scale_tc.SetValue(Scenario["scaling"]["Te_rhop_scale"])
        self.ne_rhop_scale_tc.SetValue(Scenario["scaling"]["ne_rhop_scale"])
        self.Te_scale_tc.SetValue(Scenario["scaling"]["Te_scale"])
        self.ne_scale_tc.SetValue(Scenario["scaling"]["ne_scale"])

    def SetScaling(self, Scenario):
        Scenario["scaling"]["ne_rhop_scale"] = self.ne_rhop_scale_tc.GetValue()
        Scenario["scaling"]["Te_rhop_scale"] = self.Te_rhop_scale_tc.GetValue()
        Scenario["scaling"]["ne_scale"] = self.ne_scale_tc.GetValue()
        Scenario["scaling"]["Te_scale"] = self.Te_scale_tc.GetValue()
        if(not self.use_3D_cb.GetValue()):
            Scenario["scaling"]["Bt_vac_scale"] = self.Bt_vac_scale_tc.GetValue()
        else:
            Scenario["scaling"]["Bt_vac_scale"] = 1.0
        Scenario["scaling"]["Bt_vac_scale"] = self.Bt_vac_scale_tc.GetValue()
        return Scenario

    def OnLoadAUG(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading AUG data - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.OnUnlockSelection(None)
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        self.pc_obj.reset(True)
        try:
            self.plasma_dict = load_IDA_data(self.shot_tc.GetValue(), None, self.IDA_exp_tc.GetValue(), \
                                             self.IDA_ed_tc.GetValue())
        except AttributeError as e:
            print("ERROR:: No access to AUG shotfile system")
            return
        self.plasma_dict["shot"] = self.shot_tc.GetValue()                   
        self.plasma_dict["IDA_exp"] = self.IDA_exp_tc.GetValue()
        self.plasma_dict["IDA_ed"] = self.IDA_ed_tc.GetValue()
        self.plasma_dict["vessel_bd"] = np.loadtxt(os.path.join(globalsettings.ECRadPylibRoot, vessel_bd_file), skiprows=1)
        self.plasma_dict["prof_reference"] = "rhop_prof"
        # Set to None now, load later with user updates on shotfile info
        self.plasma_dict["eq_data_2D"] = None
        print("Updated equilibrium settings with values from IDA shotfile")
        self.EQ_exp_tc.SetValue(self.plasma_dict["EQ_exp"])
        self.EQ_diag_tc.SetValue(self.plasma_dict["EQ_diag"])
        self.EQ_ed_tc.SetValue(self.plasma_dict["EQ_ed"])
        self.EQ_exp_tc.Enable()
        self.EQ_diag_tc.Enable()
        self.EQ_ed_tc.Enable()
        Success, bt_vac = check_Bt_vac_source(self.plasma_dict["shot"])
        if(Success):
            print("Setting Bt vac according to IDA defaults")
            self.Bt_vac_scale_tc.SetValue(bt_vac)
        else:
            if(self.plasma_dict["Bt_vac_scale"] != self.Bt_vac_scale_tc.GetValue()):
                print("WARNING! Currently selected vacuum bt correction differs from IDA")
                print("ECRad GUI:", self.Bt_vac_scale_tc.GetValue())
                print("IDA:", self.plasma_dict["Bt_vac_scale"])
        if(self.ne_rhop_scale_tc.GetValue() != self.plasma_dict["ne_rhop_scale_mean"]):
            print("WARNING! Currently selected ne_rhop_scale differs from IDA")
            print("ECRad GUI:", self.plasma_dict.ne_rhop_scale)
            print("IDA:", self.plasma_dict["ne_rhop_scale_mean"])
        if(self.Config["Physics"]["reflec_X"] != self.plasma_dict["RwallX"]):
            print("WARNING! Currently selected X-mode wall reflection coefficient differs from IDA")
            print("ECRad GUI:", self.Config["Physics"]["reflec_X"])
            print("IDA:", self.plasma_dict["RwallX"])
        if(self.Config["Physics"]["reflec_O"] != self.plasma_dict["RwallO"]):
            print("WARNING! Currently selected O-mode wall reflection coefficient differs from IDA")
            print("ECRad GUI:", self.Config["Physics"]["reflec_O"])
            print("IDA:", self.plasma_dict["RwallO"])
        if(self.Config["Physics"]["raytracing"] != self.plasma_dict["raytrace"]):
            print("WARNING! Refraction was not considered in IDA, but is considered in current ECRad configuation")
        if(self.IDA_ed_tc.GetValue() != self.plasma_dict["IDA_ed"]):
            print("IDA edition: ", self.plasma_dict["IDA_ed"])
            print("ECRad GUI IDA edition updated")
            self.IDA_ed_tc.SetValue(self.plasma_dict["IDA_ed"])
        # except Exception as e:
        #     print("Could not load shotfile dd Error follows")
        #     print(e)
        #     return
        if(len(self.plasma_dict["time"]) == 0):
            return
        if(len(self.plasma_dict["time"]) > 1):
            self.delta_t = 0.5 * np.mean(self.plasma_dict["time"][1:len(self.plasma_dict["time"])] - \
                                         self.plasma_dict["time"][0:len(self.plasma_dict["time"]) - 1])
        else:
            self.delta_t = 1000.0 # Used for click adding time points -> one time point click anywhere
        for t in self.plasma_dict["time"]:
            self.unused.append("{0:2.4f}".format(t))
        self.unused = list(set(self.unused))
        self.unused.sort()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)
        self.pc_obj.reset(True)
        Te_indices = np.zeros((len(self.plasma_dict["Te"]), len(self.plasma_dict["Te"][0])), dtype=bool)
        IDA_labels = []
        rhop_range = [0.2, 0.95]
        for index in range(len(self.plasma_dict["time"])):
            for rhop in rhop_range:
                Te_indices[index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))] = True
                if(index == 0):
                    IDA_labels.append(r"$T_" + globalsettings.mathrm + r"{e}$" + r"({0:1.2f})".format(self.plasma_dict[self.plasma_dict["prof_reference"]][index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))]))
        if(len(self.plasma_dict["ECE_rhop"]) > 0):
            ECE_indices = np.zeros((len(self.plasma_dict["ECE_rhop"]), len(self.plasma_dict["ECE_rhop"][0])), dtype=bool)
            ECE_labels = []
            ECRad_labels = []
            ECE_reduced_data = np.average(self.plasma_dict["ECE_dat"].reshape((len(self.plasma_dict["time"]), \
                                                                               len(self.plasma_dict["ECE_rhop"][0]), \
                                                                               int(self.plasma_dict["ECE_dat"].shape[-1] / \
                                                                                   len(self.plasma_dict["ECE_rhop"][0])))), axis=2)
            for index in range(len(self.plasma_dict["time"])):
                for rhop in rhop_range:
                    ECE_indices[index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))] = True
                    if(index == 0):
                        ECE_labels.append(r"ECE $T_" + globalsettings.mathrm + r"{rad}$" + r"({0:1.2f})".format(self.plasma_dict["ECE_rhop"][index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))]))
                        ECRad_labels.append(r"ECRad $T_" + globalsettings.mathrm + r"{rad}$" + "({0:1.2f})".format(self.plasma_dict["ECE_rhop"][index][np.argmin(np.abs(self.plasma_dict["ECE_rhop"][index] - rhop))]))
                if(np.count_nonzero(ECE_indices[index]) != len(rhop_range)):
                    print("Could not find ECE measurements for t = {0:1.4f}".format(self.plasma_dict["time"][index]))
                    print("Choosing first and last channel")
                    ECE_indices[index][:] = False
                    ECE_indices[index][0] = True
                    ECE_indices[index][-1] = True
        if(self.diag_tc.GetValue() in self.avail_diags_dict and \
           self.diag_tc.GetValue() != 'EXT'):
            diag_obj = self.avail_diags_dict[self.diag_tc.GetValue()]
            if(diag_obj.name != "ECE"):
                if(globalsettings.AUG):
                    try:
                        diag_time, diag_data = get_diag_data_no_calib(diag_obj, self.plasma_dict["shot"], preview=True)
                        if(len(diag_time) != len(diag_data[0])):
                            print("WARNING: The time base does not have the same length as the signal")
                            print(diag_time.shape , diag_data.shape)
                            print("All time points beyond the last index of the signal are omitted")
                        diag_time = diag_time[:len(diag_data[0])]
                        shown_ch = np.zeros(len(diag_data), dtype=bool)
                        shown_ch_nr = np.array(range(len(shown_ch)), bool)
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
            t, divertor_cur = get_divertor_currents(self.plasma_dict["shot"])
            div_cur = [t, divertor_cur]
        except Exception as e:
            print(e)
            print("Could not get divertor currents")
            div_cur = None
        if(diag_time is not None):
            diag_indices = np.zeros(len(diag_time), dtype=bool)
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
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.plasma_dict["shot"], self.plasma_dict["time"], diag_time, np.reshape(self.plasma_dict["Te"][Te_indices], \
                                                                                                                                      (len(self.plasma_dict["time"]), len(rhop_range))).T / 1.e3, \
                                                        IDA_labels, ECE_reduced_data[ECE_indices].reshape((len(self.plasma_dict["time"]), len(rhop_range))).T / 1.e3, ECE_labels, \
                                                        np.reshape(self.plasma_dict["ECE_mod"][ECE_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T / 1.e3, ECRad_labels, \
                                                        diag_data, diag_labels, div_cur)
        else:
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.plasma_dict["shot"], self.plasma_dict["time"], diag_time, np.reshape(self.plasma_dict["Te"][Te_indices], (len(self.plasma_dict["time"]), len(rhop_range))).T, \
                                                    IDA_labels, [], [], [], [], diag_data, diag_labels, div_cur)
        self.canvas.draw()
        self.elm_filter_cb.Enable()
        self.ECRH_filter_cb.Enable()
        self.loaded = True
        self.new_data_available = True
        self.data_source = "aug_database"
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('IDA data loaded successfully!')
        print("Scaling factors of rhop, Te and ne are ignored in this plot!")
        self.GetEventHandler().ProcessEvent(evt)

    def SetPlotClickDelta(self, time):
        if(len(time) > 1):
            self.delta_t = 0.5 * np.mean(time[1:len(time)] - \
                                         time[0:len(time) - 1])
        else:
            self.delta_t =  10.0 # Used for click adding time points -> one time point click anywhere

    def OnLoadfromFile(self, evt):
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.OnUnlockSelection(None)
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        dlg = wx.FileDialog(self, message="Choose a .mat file for input", \
                            defaultDir=self.Config["Execution"]["working_dir"], \
                            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
                            style=wx.FD_OPEN)
        if(dlg.ShowModal() != wx.ID_OK):
            return
        path = dlg.GetPath()
        dlg.Destroy()
        ext = os.path.splitext(path)[1]
        if(ext == ".mat"):
            self.plasma_dict = load_plasma_from_mat(path)
        elif(ext == ".nc"):
            self.plasma_dict = load_from_plasma(path)
        else:
            print("Extension " + ext + " is unknown")
            raise(ValueError)
        
        if(self.plasma_dict is None):
            return
        print("Updated equilibrium settings with values from .mat")
        self.shot_tc.SetValue(self.plasma_dict["shot"])
        if(globalsettings.AUG):
            self.default_diag = self.diag_tc.GetValue()
            self.plasma_dict["IDA_exp"] = "EXT"
            self.plasma_dict["IDA_ed"] = -1
            self.plasma_dict["EQ_exp"] = "EXT"
            self.plasma_dict["EQ_diag"] = "EXT"
            self.plasma_dict["EQ_ed"] = - 1
            self.IDA_exp_tc.SetValue("EXT")
            self.IDA_ed_tc.SetValue(-1)
            self.EQ_exp_tc.SetValue("EXT")
            self.EQ_exp_tc.Disable()
            self.EQ_diag_tc.SetValue("EXT")
            self.EQ_diag_tc.Disable()
            self.EQ_ed_tc.SetValue(-1)
            self.EQ_ed_tc.Disable()
        self.SetPlotClickDelta(self.plasma_dict["time"])
        for t in self.plasma_dict["time"]:
            self.unused.append("{0:2.5f}".format(t))
        self.unused = list(set(self.unused))
        self.unused.sort()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)
        if(self.plasma_dict["Te"][0].ndim == 1):
            self.pc_obj.reset(True)
            Te_indices = np.zeros((len(self.plasma_dict["Te"]), len(self.plasma_dict["Te"][0])), dtype=bool)
            IDA_labels = []
            rhop_range = [0.2, 0.95]
            for index in range(len(self.plasma_dict["time"])):
                for rhop in rhop_range:
                    Te_indices[index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))] = True
                    if(index == 0):
                        IDA_labels.append(r"$T_" + globalsettings.mathrm + r"{e}$" + r"({0:1.2f})".format(self.plasma_dict[self.plasma_dict["prof_reference"]][index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))]))
            diag_time = None
            diag_data = None
            diag_labels = None
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.plasma_dict["shot"], self.plasma_dict["time"], diag_time, \
                                                        np.reshape(self.plasma_dict["Te"][Te_indices], \
                                                                   (len(self.plasma_dict["time"]), len(rhop_range))).T / 1.e3, \
                                                        IDA_labels, [], [], \
                                                        [], [], \
                                                        diag_data, diag_labels, None)
            self.canvas.draw()
        else:
            print("Sorry no plots for your 2D Te/ne data")
        self.loaded = True
        self.new_data_available = True
        self.data_source = "file:" + path
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Data loaded successfully!')
        print("Scaling factors of rhop, Te and ne are ignored in this plot!")
        self.GetEventHandler().ProcessEvent(evt)

    def OnLoadScenario(self, evt):
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        self.OnUnlockSelection(None)
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        dlg = wx.FileDialog(self, message="Choose a .mat or .nc file for input", \
                            defaultDir=self.Config["Execution"]["working_dir"], \
                            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
                            style=wx.FD_OPEN)
        if(dlg.ShowModal() != wx.ID_OK):
            dlg.Destroy()
            return
        else:
            NewScenario = ECRadScenario(True)
            try:
                NewScenario.load(filename=dlg.GetPath())
                path = dlg.GetPath()
                self.SetFromNewScenario(NewScenario, path)
                dlg.Destroy()
            except Exception as e:
                print(e)
                print("Failed to load Scenario -- does the selected file contain a Scenario?")
                print("If this file only contains profiles and equilibria try load from .mat instead.")
                dlg.Destroy()
                return
        
    def OnLoadOMAS(self, evt):
        try:
            from omas.omas_machine import machine_to_omas
            from omas import ODS
        except ImportError:
            print("Failed to import OMAS. OMAS is an optional dependency and needs to be installed manually.")
            return
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
#         try:
#             Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
#         except ValueError as e:
#             print("Failed to parse Configuration")
#             print("Reason: " + e)
#             return
        self.OnUnlockSelection(None)
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        omas_db_dlg = OMASdbSelectDialog(self)
        if(omas_db_dlg.ShowModal() != wx.ID_OK):
            omas_db_dlg.Destroy()
            return
        state = omas_db_dlg.state
        omas_db_dlg.Destroy()
        if state[0]:
            file_dlg = wx.FileDialog(self, message="Choose a .pkl or .nc file for input", \
                            defaultDir=self.Config["Execution"]["working_dir"], \
                            wildcard=("Matlab and Netcdf4 files (*.pkl;*.nc)|*.pkl;*.nc"),
                            style=wx.FD_OPEN)
            if(file_dlg.ShowModal() != wx.ID_OK):
                file_dlg.Destroy()
                return
            path = file_dlg.Path
            file_dlg.Destroy()
            WorkerThread(self.load_omas_from_file, [path])
        else:
            WorkerThread(self.load_omas_from_db, [state])

    def load_omas_from_file(self, args):
        from omas import ODS
        ods = ODS()
        file_path = args[0]
        ods.load(file_path, consistency_check="warn")
        evt_out = GenerticEvt(Unbound_OMAS_LOAD_FINISHED, self.GetId())
        evt_out.insertData([ods, file_path, None, None])
        wx.PostEvent(self, evt_out)

    def load_omas_from_db(self, args):
        from omas.omas_machine import machine_to_omas
        from omas import ODS
        from omas.omas_physics import derive_equilibrium_profiles_2d_quantity
        ods = ODS()
        state = args[0]
        if state[1] != "d3d":
            print("Only DIII-D machine mappings supported at the moment")
            return
        options = {'EFIT_tree':  state[3], "EFIT_run_id": state[4],  
                   "PROFILES_tree": state[5], "PROFILES_run_id": state[6]}
        machine_to_omas(ods, state[1], state[2], "equilibrium.time", 
                        options=options)
        machine_to_omas(ods, state[1], state[2], "equilibrium.time_slice.*", 
                        options=options)
        machine_to_omas(ods, state[1], state[2], "core_profiles.time", 
                        options=options)
        machine_to_omas(ods, state[1], state[2], "core_profiles.profiles_1d.*", 
                        options=options)
        machine_to_omas(ods, state[1], state[2], "wall.*", 
                        options=options)
        for time_index, time in enumerate(ods["equilibrium.time"]):
            for B_label in ["b_field_r", "b_field_tor", "b_field_z"]:
                ods = derive_equilibrium_profiles_2d_quantity(ods, time_index, 0, B_label)
        evt_out = GenerticEvt(Unbound_OMAS_LOAD_FINISHED, self.GetId())
        options["device"] = state[1] 
        options["shot"] = state[2] 
        evt_out.insertData([ods, None, state[2], str(options)])
        wx.PostEvent(self, evt_out)

    def OnOmasLoaded(self, evt):
        ods, data_path, shot, run_id = evt.Data
        self.shot_tc.SetValue(shot)
        time_base_dlg = IMASTimeBaseSelectDlg(self)
        if(time_base_dlg.ShowModal() != wx.ID_OK):
            time_base_dlg.Destroy()
            return
        time_base_source = time_base_dlg.choice
        time_base_dlg.Destroy()
        times = ods[time_base_source]['time']
        NewScenario = ECRadScenario(True)
        NewScenario["time"] = times
        NewScenario["shot"] = shot
        NewScenario.set_up_profiles_from_omas(ods,times)
        NewScenario.set_up_equilibrium_from_omas(ods,times)
        self.SetFromNewScenario(NewScenario, data_path, id=run_id)
        time_base_dlg.Destroy()

    def OnLoadIMAS(self, evt):
        import imas
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
#         try:
#             Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
#         except ValueError as e:
#             print("Failed to parse Configuration")
#             print("Reason: " + e)
#             return
        dlg = IMASSelectDialog(self)
        if(dlg.ShowModal() == wx.ID_OK):
            try:
                ids = dlg.ids
                check=ids.open()
                if check[0]!=0:
                    print('ERROR: Could not open the IMAS file with plasma')
                    return
                try:
                    eq_ids = ids.get('equilibrium')
                except Exception as e:
                    print(e)
                    print("ERROR: Cannot access equilibrium in IDS")
                    return
                try:    
                    prof_ids = ids.get('core_profiles')
                except Exception as e:
                    print(e)
                    print("ERROR: Cannot access profiles in IDS")
                    return
                try:    
                    ids_wall = imas.DBEntry(imas.imasdef.MDSPLUS_BACKEND,'ITER_MD',1180,17,'public')
                    ids_wall.open()
                    wall_ids = ids_wall.get_slice('wall', 0, 1)  
                    ids_wall.close()                
                except Exception as e:
                    print(e)
                    print("ERROR: Cannot access wall in IDS")
                    return
                time_base_dlg = IMASTimeBaseSelectDlg(self)
                if(time_base_dlg.ShowModal() != wx.ID_OK):
                    time_base_dlg.Destroy()
                    return
                time_base_source = time_base_dlg.choice
                time_base_dlg.Destroy()
                times = ids.partial_get(ids_name=time_base_source,data_path='time')
                NewScenario = ECRadScenario(True)
                NewScenario["time"]=times
                NewScenario["shot"]= dlg.shot_tc.GetValue()
                NewScenario.set_up_profiles_from_imas(prof_ids, eq_ids, times)
                NewScenario.set_up_equilibrium_from_imas(eq_ids, wall_ids, times)
                self.SetFromNewScenario(NewScenario, 'IMAS_file')
            except Exception as e:
                print(e)
                print("ERROR: Failed to load Scenario -- there are probably required ")
                print("entries missing in the IDS.")
                return
        dlg.Destroy()

    def SetFromNewScenario(self, NewScenario, path, draw=True, id=None):
        self.UpdateContent(NewScenario, diag_name=NewScenario.default_diag)
        self.plasma_dict = deepcopy(NewScenario["plasma"])
        self.plasma_dict["time"] = np.copy(NewScenario["time"])
        self.plasma_dict["shot"] = np.copy(NewScenario["shot"])
        self.plasma_dict["dist_obj"] = NewScenario["plasma"]["dist_obj"]
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.SetPlotClickDelta(self.plasma_dict["time"])
        for t in self.plasma_dict["time"]:
            self.unused.append("{0:2.5f}".format(t))
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)
        if(globalsettings.AUG):
            self.plasma_dict["IDA_exp"] = NewScenario["AUG"]["IDA_exp"] 
            self.plasma_dict["IDA_ed"] = NewScenario["AUG"]["IDA_ed"]
            self.plasma_dict["EQ_exp"] = NewScenario["AUG"]["EQ_exp"]
            self.plasma_dict["EQ_diag"] = NewScenario["AUG"]["EQ_diag"]
            self.plasma_dict["EQ_ed"] = NewScenario["AUG"]["EQ_ed"]
        if(not self.plasma_dict["2D_prof"] and draw):
            self.pc_obj.reset(True)
            Te_indices = np.zeros(self.plasma_dict["Te"].shape, dtype=bool)
            IDA_labels = []
            rhop_range = [0.2, 0.95]
            for index in range(len(self.plasma_dict["time"])):
                for rhop in rhop_range:
                    Te_indices[index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))] = True
                    if(index == 0):
                        IDA_labels.append(r"$T_" + globalsettings.mathrm + r"{e}$" + "({0:1.2f})".format(self.plasma_dict[self.plasma_dict["prof_reference"]][index][np.argmin(np.abs(self.plasma_dict[self.plasma_dict["prof_reference"]][index] - rhop))]))
            diag_time = None
            diag_data = None
            diag_labels = None
            self.fig = self.pc_obj.time_trace_for_calib(self.fig, self.plasma_dict["shot"], self.plasma_dict["time"], diag_time, \
                                                        np.reshape(self.plasma_dict["Te"][Te_indices], \
                                                                (len(self.plasma_dict["time"]), len(rhop_range))).T / 1.e3, \
                                                        IDA_labels, [], [], \
                                                        [], [], \
                                                        diag_data, diag_labels, None)
            self.canvas.draw()
        elif(draw):
            print("Sorry no plots for 2D ne/Te")
        self.loaded = True
        self.new_data_available = True
        if path is not None:
            self.data_source = "file:" + path
        elif id is not None:
            self.data_source = id
        else:
            raise ValueError("Either `path` or `id` must be not None.")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Data loaded successfully!')
        print("Scaling factors of rhop, Te and ne are ignored in this plot!")
        self.GetEventHandler().ProcessEvent(evt)
        
    def OnLoadResult(self, evt):
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(self.Config)
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
#         try:
#             self.Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
#         except ValueError as e:
#             print("Failed to parse Configuration")
#             print("Reason: " + e)
#             return
        self.OnUnlockSelection(None)
        self.unused = []
        self.used = []
        self.used_list.Clear()
        self.unused_list.Clear()
        dlg = wx.FileDialog(self, message="Choose a .nc or .mat file for input", \
                            defaultDir=self.Config["Execution"]["working_dir"], \
                            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
                            style=wx.FD_OPEN)
        if(dlg.ShowModal() != wx.ID_OK):
            dlg.Destroy()
            return
        else:
            NewResult = ECRadResults()
            try:
                self.Result_for_ext_launch = NewResult
                self.Result_for_ext_launch.load(dlg.GetPath())
                path = dlg.GetPath()
                dlg.Destroy()
            except Exception as e:
                print(e)
                print("Failed to load Scenario -- does the selected file contain a Scenario?")
                dlg.Destroy()
                return
        self.Result_for_ext_launch.Config["Physics"]["use_ext_rays"] = True
        self.Parent.Parent.launch_panel.SetScenario(self.Result_for_ext_launch.Scenario, self.Config["Execution"]["working_dir"])
        self.Parent.Parent.config_panel.SetConfig(self.Result_for_ext_launch.Config)
        self.Config = self.Result_for_ext_launch.Config
        self.Parent.Parent.config_panel.EnableExtRays()
        NewScenario = self.Result_for_ext_launch.Scenario
        self.SetFromNewScenario(NewScenario, path)

    def FullUpdateNeeded(self):
        if(self.new_data_available):
            return True
        if(globalsettings.AUG and self.data_source == "aug_database"):
            for widget in [self.EQ_exp_tc, self.EQ_diag_tc, self.EQ_ed_tc]:
                if(widget.CheckForNewValue()):
                    return True
        for widget in [self.Bt_vac_scale_tc, self.Te_rhop_scale_tc, self.ne_rhop_scale_tc, self.Te_scale_tc, self.ne_scale_tc]:
            if(widget.CheckForNewValue()):
                return True
        return False

    def UpdateScenario(self, Scenario, Config, callee):
        if(self.loaded == False):
            print("No plasma data loaded yet!")
            raise ValueError("No data loaded")
        elif(len(self.used) == 0):
            print("No time points selected!")
            raise ValueError("No time points")
        old_time_list = []
        old_eq = []
        if(globalsettings.AUG and self.data_source == "aug_database"):
            # Reset the equilibrium for AUG to make sure we get the one requested by the user
            self.plasma_dict["eq_data_2D"] = None
            # Get rid of the old stuff it will be updated now
            if(Scenario["AUG"]["EQ_exp"] == self.EQ_exp_tc.GetValue() and \
               Scenario["AUG"]["EQ_diag"] == self.EQ_diag_tc.GetValue() and \
               Scenario["AUG"]["EQ_ed"] == self.EQ_ed_tc.GetValue()):
                old_time_list = np.copy(Scenario["time"])
                old_eq = EQDataExt(Scenario["shot"], Ext_data=True)
                for time in old_time_list:
                    old_eq.insert_slices_from_ext(
                            [time], [Scenario["plasma"]["eq_data_2D"].GetSlice(time)])
                if(len(old_time_list) != len(Scenario["plasma"]["eq_data_2D"].times)):
                # Something went wrong on the last load -> reload everything
                    old_time_list = []
                    old_eq = []
        Scenario.reset()
        Scenario.data_source = self.data_source
        if(self.use_3D_cb.GetValue()):
            Scenario["plasma"]["eq_dim"] = 3
        else:
            Scenario["plasma"]["eq_dim"] = 2
        Scenario["shot"] = self.plasma_dict["shot"]
        if(globalsettings.AUG):
            Scenario["AUG"]["IDA_exp"] = self.plasma_dict["IDA_exp"]
            Scenario["AUG"]["IDA_ed"] = self.plasma_dict["IDA_ed"]
            Scenario.default_diag = self.diag_tc.GetValue()
            Scenario["AUG"]["EQ_exp"] = self.EQ_exp_tc.GetValue()
            Scenario["AUG"]["EQ_diag"] = self.EQ_diag_tc.GetValue()
            Scenario["AUG"]["EQ_ed"] = self.EQ_ed_tc.GetValue()
        self.SetScaling(Scenario)
        Scenario["plasma"]["2D_prof"] = self.plasma_dict["Te"][0].ndim > 1
        if(Scenario["plasma"]["2D_prof"]):
            Scenario["plasma"]["rhop_prof"] = []
            Scenario["plasma"]["rhot_prof"] = []
        for time_str in self.used:            
            itime = np.argmin(np.abs(self.plasma_dict["time"] - float(time_str)))
            time = self.plasma_dict["time"][itime]
            Scenario["time"].append(time)
            if(not Scenario["plasma"]["2D_prof"]):
                Scenario["plasma"][self.plasma_dict["prof_reference"]].append(
                        self.plasma_dict[self.plasma_dict["prof_reference"]][itime])
            Scenario["plasma"]["Te"].append(self.plasma_dict["Te"][itime])
            Scenario["plasma"]["ne"].append(self.plasma_dict["ne"][itime])
            if(time in old_time_list):
                if(Scenario["plasma"]["eq_dim"] == 2):
                    Scenario["plasma"]["eq_data_2D"].set_slices_from_ext([time], [old_eq.GetSlice(time)])
            elif(Scenario.data_source == "aug_database" and globalsettings.AUG == True):
                if(self.plasma_dict["eq_data_2D"] is None):
                    self.plasma_dict["eq_data_2D"] = EQData(Scenario["shot"], EQ_exp=Scenario["AUG"]["EQ_exp"], \
                                                            EQ_diag=Scenario["AUG"]["EQ_diag"], EQ_ed=Scenario["AUG"]["EQ_ed"])
                Scenario["plasma"]["eq_data_2D"].insert_slices_from_ext([time], [self.plasma_dict["eq_data_2D"].GetSlice(time)])
            else:
                if(Scenario["plasma"]["eq_dim"] == 2):
                    Scenario["plasma"]["eq_data_2D"].insert_slices_from_ext([time], [self.plasma_dict["eq_data_2D"].GetSlice(time)])
        if(Scenario["plasma"]["eq_dim"] == 2): 
            Scenario["plasma"]["vessel_bd"] = self.plasma_dict["vessel_bd"]
        Scenario["time"] = np.array(Scenario["time"])
        Scenario["plasma"]["Te"] = np.array(Scenario["plasma"]["Te"])
        Scenario["plasma"]["ne"] = np.array(Scenario["plasma"]["ne"])
        Scenario["plasma"]["prof_reference"] = self.plasma_dict["prof_reference"]
        if(not Scenario["plasma"]["2D_prof"]):
            Scenario["plasma"][Scenario["plasma"]["prof_reference"]] = np.array(
                Scenario["plasma"][Scenario["plasma"]["prof_reference"]])
        if(len(Scenario["time"]) == 1 and Config["Physics"]["dstf"] == "Re"):
            Scenario["plasma"]["dist_obj"] = self.plasma_dict["dist_obj"]
        elif(Config["Physics"]["dstf"] == "Re"):
            print("INFO: Not setting distribution data because more than one time point is selected")
        Scenario.plasma_set = True
        self.new_data_available = False
        return Scenario

    def OnFilterElms(self, evt):
        if(self.data_source != "aug_database"):
            print("Elm sync not available for non-AUG data")
        filter_elms = self.elm_filter_cb.GetValue()
        if(filter_elms):
            try:
                idxNoElm = ElmExtract(np.array(self.used, dtype=np.double), self.plasma_dict["shot"], plot=False, preFac=0.15,
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
                idxNoElm = ElmExtract(np.array(self.unused, dtype=np.double), self.plasma_dict["shot"], plot=False, preFac=0.15,
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
                print(e)
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
                idxECRHOff = identify_ECRH_on_phase(self.plasma_dict["shot"], np.array(self.used, dtype=np.double))
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
                idxECRHOff = identify_ECRH_on_phase(self.plasma_dict["shot"], np.array(self.unused, dtype=np.double))
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
        idxCTA = filter_CTA(self.plasma_dict["shot"], np.array(self.unused, dtype=np.double), diag.diag, diag.exp, diag.ed)
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
            idxIEC = filter_CTA(self.plasma_dict["shot"], np.array(self.unused, dtype=np.double), "CTA", "AUGD", 0)
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
        IDA_timepoint_used = np.zeros(len(self.plasma_dict["time"]), dtype=bool)
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
        if(self.post_run):
            return
        if(evt.dblclick and len(self.unused) > 0):
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

    def get_selected_items(self, sel, list_object):
        to_move = []
        for i_sel in sel:
            to_move.append(list_object.GetString(i_sel))
        return to_move

    def add_to_used(self, sel):
        to_move = self.get_selected_items(sel, self.unused_list)
        for item in to_move:
            self.used.append(self.unused.pop(self.unused.index(item)))
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

    def add_to_unused(self, sel):
        to_move = self.get_selected_items(sel, self.used_list)
        for item in to_move:
            self.unused.append(self.used.pop(self.used.index(item)))
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
        self.add_to_used(sel)

    def OnUnlockSelection(self, evt):
        self.post_run = False
        self.used_list.Enable()
        self.unused_list.Enable()
        self.AddButton.Enable()
        self.RemoveButton.Enable()
        if(globalsettings.AUG):
            self.IDA_exp_tc.Enable()
            self.IDA_ed_tc.Enable()
        evt = LockExportEvt(Unbound_EVT_LOCK_EXPORT, self.GetId())
        self.Parent.Parent.GetEventHandler().ProcessEvent(evt)

    def OnRemoveSelection(self, evt):
        sel = self.used_list.GetSelections()
        self.add_to_unused(sel)


    def ChangeCursor(self, event):
        self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

