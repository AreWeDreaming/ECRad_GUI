'''
Created on Mar 21, 2019

@author: sdenk
'''
from GlobalSettings import AUG, TCV
from wxEvents import *
import wx
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row
from collections import OrderedDict as od
import numpy as np
from ECRad_Interface import get_diag_launch, write_diag_launch
import os
from Diags import ECRH_diag, EXT_diag

class LaunchPanel(wx.Panel):
    def __init__(self, parent, Scenario):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.Notebook = Diag_Notebook(self)
        self.diag_select_panel = wx.Panel(self, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.diag_select_panel.sizer = wx.BoxSizer(wx.VERTICAL)
        self.diag_select_panel.SetSizer(self.diag_select_panel.sizer)
        self.diag_select_label = wx.StaticText(self.diag_select_panel, wx.ID_ANY, "Select diagnostics to model")
        self.diag_select_panel.sizer.Add(self.diag_select_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.grid = wx.GridSizer(0, 10, 0, 0)
        self.diag_cb_dict = od()
        for Diagkey in Scenario.avail_diags_dict.keys():
            self.diag_cb_dict.update({Diagkey :simple_label_cb(self.diag_select_panel, Diagkey, False)})
            self.grid.Add(self.diag_cb_dict[Diagkey], 0, \
                          wx.TOP | wx.ALL, 5)
        for Diagkey in Scenario.used_diags_dict.keys():
            self.diag_cb_dict[Diagkey].SetValue(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.diag_select_panel.sizer.Add(self.grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.diag_select_panel, 0, wx.ALL | wx.LEFT, 5)
        self.Notebook.Spawn_Pages(Scenario.avail_diags_dict)
        self.sizer.Add(self.Notebook, 0, wx.ALL | wx.LEFT, 5)
        self.SetSizer(self.sizer)
        self.new_data_available = False

    def RecreateNb(self):
        self.Notebook.DeleteAllPages()
        self.Notebook.PageList = []

    def UpdateScenario(self, Scenario):
        Scenario.diags_set = False
        Scenario.avail_diags_dict = self.Notebook.UpdateDiagDict(Scenario.avail_diags_dict)
        Scenario.used_diags_dict = od()
        for Diagkey in self.diag_cb_dict.keys():
            if(self.diag_cb_dict[Diagkey].GetValue()):
                Scenario.used_diags_dict.update({Diagkey : Scenario.avail_diags_dict[Diagkey]})
        if(len(Scenario.used_diags_dict.keys()) == 0):
            print("No diagnostics Selected")
            return Scenario
        if(len(Scenario.plasma_dict["time"]) == 0):
            # No time points yet, only updating diag info
            return Scenario
        gy_dict = {}
        ECI_dict = {}
        for diag_key in Scenario.used_diags_dict.keys():
            if("CT" in diag_key or "IEC" == diag_key):
                import get_ECRH_config
                new_gy = get_ECRH_config.get_ECRH_viewing_angles(Scenario.shot, \
                                                Scenario.used_diags_dict[diag_key].beamline, \
                                                Scenario.used_diags_dict[diag_key].base_freq_140)
                if(new_gy.error == 0):
                    gy_dict[str(Scenario.used_diags_dict[diag_key].beamline)] = new_gy
                else:
                    print("Error when reading viewing angles")
                    print("Launch aborted")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('Error while preparing launch!')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
                del(get_ECRH_config) # Need to destroy this here otherwise we cause an incompatability with libece
            if(diag_key in ["ECN", "ECO", "ECI"]):
                from shotfile_handling_AUG import get_ECI_launch
                ECI_dict = get_ECI_launch(Scenario.used_diags_dict[diag_key], Scenario.shot)
        Scenario.ray_launch = []
        # Prepare the launches for each time point
        # Some diagnostics have steerable LO, hence each time point has an individual launch
        for time in Scenario.plasma_dict["time"]:
            Scenario.ray_launch.append(get_diag_launch(Scenario.shot, time, Scenario.used_diags_dict, \
                                                        gy_dict=gy_dict, ECI_dict=ECI_dict))
        Scenario.ray_launch = np.array(Scenario.ray_launch)
        Scenario.diags_set = True
        return Scenario

    def SetScenario(self, Scenario):
        for Diagkey in self.diag_cb_dict.keys():
            self.diag_cb_dict[Diagkey].SetValue(False)
            if(Diagkey in Scenario.used_diags_dict.keys()):
                self.diag_cb_dict[Diagkey].SetValue(True)
        self.Notebook.DistributeInfo(Scenario)

    def UpdateNeeded(self):
        check_list = []
        for Diagkey in self.diag_cb_dict.keys():
            if(self.diag_cb_dict[Diagkey].CheckForNewValue()):
                return True
            if(self.diag_cb_dict[Diagkey].GetValue()):
                check_list.append(Diagkey)
        if(len(check_list) == 0):
            return True
        return  self.Notebook.CheckForNewValues(check_list)

class Diag_Notebook(wx.Choicebook):
    def __init__(self, parent):
        wx.Choicebook.__init__(self, parent, wx.ID_ANY, \
                            style=wx.BK_DEFAULT)
        self.PageDict = od()

    def Spawn_Pages(self, DiagDict) :
        self.varsize = (0, 0)
        for diag in DiagDict.keys():
            self.PageDict.update({diag : Diag_Page(self, DiagDict[diag])})
            pagename = diag
            if(len(pagename) > 10 and ' ' in pagename):
                pagelist = pagename.split(' ')
                pagename = ""
                last = 0
                for j in range(len(pagelist)):
                    if(int(len(pagename) / 10) > last):
                        pagelist[j] = pagelist[j] + '\n'
                        last += 1
                    else:
                        pagelist[j] = pagelist[j] + ' '
                    pagename = pagename + pagelist[j]
                if(pagename.endswith('\n') or pagename.endswith(' ')):
                    pagename = pagename[0:len(pagename) - 1]
            self.AddPage(self.PageDict[diag], pagename)

    def UpdateDiagDict(self, DiagDict):
        for diag in self.PageDict.keys():
            DiagDict[diag] = self.PageDict[diag].RetrieveDiag()
        return DiagDict

    def DistributeInfo(self, Scenario):
        for diag in self.PageDict.keys():
            if(self.PageDict[diag].name in Scenario.avail_diags_dict.keys()):
                self.PageDict[diag].DepositDiag(Scenario.avail_diags_dict[self.PageDict[diag].name])

    def CheckForNewValues(self, check_list):
        for diag in check_list:
            if(self.PageDict[diag].CheckForNewValues()):
                return True
        return False

class Diag_Page(wx.Panel):
    def __init__(self, parent, Diag_obj, border=1, maxwidth=max_var_in_row, \
                    parentmode=False, style=wx.TAB_TRAVERSAL | wx.NO_BORDER):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=style)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        if(hasattr(Diag_obj, "N_ch")):
            self.diagpanel = ExtDiagPanel(self, Diag_obj)
        else:
            self.diagpanel = Diag_Panel(self, Diag_obj)
        self.name = Diag_obj.name
        self.sizer.Add(self.diagpanel, 0, wx.ALL | wx.TOP, 5)

    def RetrieveDiag(self):
        self.diag = self.diagpanel.GetDiag()
        return self.diag

    def DepositDiag(self, diag):
        self.diagpanel.SetDiag(diag)

    def CheckForNewValues(self):
        return self.diagpanel.CheckForNewValues()

class Diag_Panel(wx.Panel):
    def __init__(self, parent, Diag_obj):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.Diag = Diag_obj
        self.grid_sizer = wx.GridSizer(0, 4, 0, 0)
        self.art_data_beamline = 1
        self.art_data_base_freq_140 = True
        self.art_data_pol_coeff_X = 1.0
        self.art_data_pol_launch = 0.0
        self.art_data_tor_launch = 0.0
        self.widget_dict = {}
        self.selected_channel = 0
        for attribute in Diag_obj.properties:
            if(Diag_obj.data_types_dict[attribute] != "bool"):
                scale = None
                if(attribute in Diag_obj.scale_dict.keys()):
                    scale = Diag_obj.scale_dict[attribute]
                self.widget_dict[attribute] = simple_label_tc(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute), \
                                                              Diag_obj.data_types_dict[attribute], \
                                                              scale=scale)
            else:
                self.widget_dict[attribute] = simple_label_cb(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute))
            self.grid_sizer.Add(self.widget_dict[attribute], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
            self.SetSizer(self.grid_sizer)

    def GetDiag(self):
        for attribute in self.Diag.properties:
            setattr(self.Diag, attribute, self.widget_dict[attribute].GetValue())
        return self.Diag

    def SetDiag(self, Diag):
        self.Diag = Diag
        for attribute in self.Diag.properties:
            self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute))

    def CheckForNewValues(self):
        for attribute in self.Diag.properties:
            if(self.widget_dict[attribute].CheckForNewValue()):
                return True
        return False

class ExtDiagPanel(Diag_Panel):
    def __init__(self, parent, Diag_obj):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.Diag = Diag_obj
        self.grid_sizer = wx.GridSizer(0, 4, 0, 0)
        self.art_data_beamline = 1
        self.art_data_base_freq_140 = True
        self.art_data_pol_coeff_X = 1.0
        self.art_data_pol_launch = 0.0
        self.art_data_tor_launch = 0.0
        self.widget_dict = {}
        self.selected_channel = 0
        self.NewValues = False
        N_ch = getattr(Diag_obj, "N_ch")
        self.widget_dict["N_ch"] = simple_label_tc(self, Diag_obj.descriptions_dict["N_ch"], \
                                                   getattr(Diag_obj, "N_ch"), \
                                                   Diag_obj.data_types_dict["N_ch"])
        self.grid_sizer.Add(self.widget_dict["N_ch"], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.channel_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.channel_select_ch = wx.Choice(self, wx.ID_ANY)
        self.channel_select_ch.AppendItems(np.array(range(1, N_ch + 1), dtype="|S3").tolist())
        self.channel_select_ch.SetSelection(self.selected_channel)
        self.channel_select_ch.Bind(wx.EVT_CHOICE, self.OnNewChannelSelected)
        self.channel_ctrl_sizer.Add(self.channel_select_ch, 0, wx.EXPAND | wx.ALL, 5)
        self.update_N_ch_Button = wx.Button(self, label='Update Channel Number')
        self.update_N_ch_Button.Bind(wx.EVT_BUTTON, self.OnUpdateNch)
        self.channel_ctrl_sizer.Add(self.update_N_ch_Button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        self.grid_sizer.Add(self.channel_ctrl_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        for attribute in Diag_obj.properties:
            if(attribute == "N_ch"):
                continue
            if(Diag_obj.data_types_dict[attribute] != "bool"):
                scale = None
                if(attribute in Diag_obj.scale_dict.keys()):
                    scale = Diag_obj.scale_dict[attribute]
                self.widget_dict[attribute] = simple_label_tc(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute)[self.selected_channel], \
                                                              Diag_obj.data_types_dict[attribute], \
                                                              scale=scale)
            else:
                self.widget_dict[attribute] = simple_label_cb(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute))
            self.grid_sizer.Add(self.widget_dict[attribute], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.SetSizer(self.grid_sizer)

    def OnUpdateNch(self, evt):
        N_ch = self.widget_dict["N_ch"].GetValue()
        if(N_ch < self.Diag.N_ch):
            if(self.selected_channel > N_ch):
                self.selected_channel = N_ch - 1
        # Shorten current channel list
            for attribute in self.Diag.properties:
                if(attribute == "N_ch"):
                    continue
                temp = np.copy(getattr(self.Diag, attribute))
                new_vals = np.zeros(N_ch)
                new_vals[:] = temp[0:N_ch]
                setattr(self.Diag, attribute, new_vals)
        elif(N_ch > self.Diag.N_ch):
        # Extend list
            for attribute in self.Diag.properties:
                if(attribute == "N_ch"):
                    continue
                temp = np.copy(getattr(self.Diag, attribute))
                new_vals = np.zeros(N_ch)
                new_vals[:] = temp[0]  # Use first channel as default for the new ones
                new_vals[0:N_ch] = temp[:]
                setattr(self.Diag, attribute, new_vals)
        setattr(self.Diag, "N_ch", N_ch)
        self.channel_select_ch.Clear()
        self.channel_select_ch.AppendItems(np.array(range(1, N_ch + 1), dtype="|S3").tolist())
        self.channel_select_ch.Select(self.selected_channel)  # note not channel number but channel index, i.e. ch no. 1 -> 0

    def OnNewChannelSelected(self, evt):
        old_selected_channel = self.selected_channel
        self.selected_channel = self.channel_select_ch.GetSelection()
        for attribute in self.Diag.properties:
            if(self.widget_dict[attribute].CheckForNewValue()):
                self.NewValues = True
            if(attribute == "N_ch"):
                    continue
            vals = getattr(self.Diag, attribute)
            vals[old_selected_channel] = self.widget_dict[attribute].GetValue()
            setattr(self.Diag, attribute, vals)
            self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute)[self.selected_channel])


    def OnLoadLaunch(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a *_launch.dat file for input", \
            defaultDir=self.ECRadConfig.working_dir, \
            wildcard=('Launch files (*_launch.dat)|*_launch.dat|All files (*.*)|*.*'),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            try:
                self.Diag.load_launch_geo_from_file(path, ray_launch=self.ray_launch_format_cb.GetValue())
                self.SetDiag(self.Diag)
            except Exception as e:
                print("Failed to load external launch - reason:")
                print(e)
                return
            self.NewValues = True
        else:
            print("Import aborted")
            return

    def OnSaveLaunch(self, evt):
        dlg = wx.DirDialog(self,
                           message="Choose the folder to store the EXT_launch.dat file")  # defaultDir=self.ECRadConfig.working_dir, \
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            used_diags_dict = {}
            self.Diag = self.GetDiag()
            used_diags_dict["EXT"] = self.Diag
            write_diag_launch(path, used_diags_dict)
            print("Sucessfully created: " + path + os.sep + "ray_launch.dat")

    def OnMakeArtificalCTA(self, evt):
        dlg = ECRH_launch_dialogue(self, self.art_data_beamline, \
                                   self.art_data_base_freq_140, \
                                   self.art_data_pol_coeff_X, \
                                   self.art_data_pol_launch, \
                                   self.art_data_tor_launch)
        if(dlg.ShowModal() == True):
            try:
                diags_dict = {}
                diags_dict["CTA"] = ECRH_diag("EXT", "EXT", 0, dlg.beamline_tc.GetValue(), \
                                              dlg.pol_coeff_X_tc.GetValue(), dlg.freq_140_rb.GetValue())
                new_gy = get_ECRH_launcher(self.ECRadConfig.shot, diags_dict["CTA"].beamline, diags_dict["CTA"].base_freq_140)
                if(np.isscalar(new_gy.phi_tor)):
                    new_gy.phi_tor = -dlg.tor_launch_tc.GetValue()
                else:
                    new_gy.phi_tor[:] = -dlg.tor_launch_tc.GetValue()
                if(np.isscalar(new_gy.phi_tor)):
                    new_gy.theta_pol = -dlg.pol_launch_tc.GetValue()
                else:
                    new_gy.theta_pol[:] = -dlg.pol_launch_tc.GetValue()
                gy_dict = {}
                gy_dict[str(diags_dict["CTA"].beamline)] = new_gy
                self.art_data_beamline = diags_dict["CTA"].beamline
                self.art_data_base_freq_140 = diags_dict["CTA"].base_freq_140
                self.art_data_pol_coeff_X = diags_dict["CTA"].pol_coeff_X
                self.art_data_pol_launch = dlg.pol_launch_tc.GetValue()
                self.art_data_tor_launch = dlg.tor_launch_tc.GetValue()
                self.append = dlg.append_cb.GetValue()
                dlg.Destroy()
                diag_launch = get_diag_launch(self.ECRadConfig.working_dir, self.ECRadConfig.shot, 0.0, diags_dict, gy_dict=gy_dict)
                self.SetDiag(EXT_diag(self.Diag.name, \
                             diag_launch=diag_launch, t_smooth=self.Diag.t_smooth, append_launch=self.append))
                self.NewValues = True
            except Exception as e:
                print("Failed to load external launch - reason:")
                print(e)
                return
        else:
            print("Setup aborted")
            return

    def GetDiag(self):
        self.OnNewChannelSelected(None)
        self.NewValues = False
        return self.Diag

    def SetDiag(self, Diag):
        self.Diag = Diag
        self.OnNewChannelSelected(None)
        self.NewValues = False

    def CheckForNewValues(self):
        if(self.NewValues):
            return self.NewValues
        return Diag_Panel.CheckForNewValues(self)

class ECRH_launch_dialogue(wx.Dialog):
    def __init__(self, parent, art_data_beamline, \
                               art_data_base_freq_140, \
                               art_data_pol_coeff_X, \
                               art_data_pol_launch, \
                               art_data_tor_launch):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.BoxSizer = wx.GridSizer(0, 5, 5, 5)
        self.beamline_tc = simple_label_tc(self, "Beamline", art_data_beamline, "integer")
        self.BoxSizer.Add(self.beamline_tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.pol_launch_tc = simple_label_tc(self, "Poloidal launch angle", art_data_pol_launch, "real")
        self.BoxSizer.Add(self.pol_launch_tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.tor_launch_tc = simple_label_tc(self, "Toroidal launch angle", art_data_tor_launch, "real")
        self.BoxSizer.Add(self.tor_launch_tc, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.freq_140_rb = wx.RadioButton(self, id=wx.ID_ANY, label="140 GHz")
        self.BoxSizer.Add(self.freq_140_rb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.freq_140_rb.SetValue(art_data_base_freq_140)
        self.freq_105_rb = wx.RadioButton(self, id=wx.ID_ANY, label="105 GHz")
        self.BoxSizer.Add(self.freq_105_rb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.pol_coeff_X_tc = simple_label_tc(self, "X-mode fraction", art_data_pol_coeff_X, "real")
        self.BoxSizer.Add(self.freq_105_rb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.append_cb = simple_label_cb(self, "Append Launch?", False)
        self.BoxSizer.Add(self.append_cb, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.BoxSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetClientSize(self.GetEffectiveMinSize())

    def EvtClose(self, Event):
        self.EndModal(False)

    def EvtAccept(self, Event):
        self.EndModal(True)
