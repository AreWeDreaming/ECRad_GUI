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
from ECFM_Interface import get_diag_launch, write_diag_launch
import os
from Diags import ECRH_diag, EXT_diag
if(AUG):
    from get_ECRH_config import get_ECRH_launcher, get_ECRH_viewing_angles
    from shotfile_handling_AUG import get_ECI_launch

class Launch_Panel(wx.Panel):
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

    def RecreateNb(self):
        self.Notebook.DeleteAllPages()
        self.Notebook.PageList = []

    def UpdateScenario(self, Scenario):
        Scenario.diags_set = False
        Scenario.avail_diags_dict = self.Notebook.UpdateDiagDict(Scenario.avail_diags_dict)
        for Diagkey in self.diag_cb_dict.keys():
            if(self.diag_cb_dict[Diagkey].GetValue()):
                Scenario.used_diags_dict.update({Diagkey : Scenario.avail_diags_dict[Diagkey]})
        if(len(Scenario.plasma_dict["time"]) == 0):
            # No time points yet, only updating diag info
            return Scenario
        for diag_key in Scenario.used_diags_dict.keys():
            gy_dict = {}
            if("CT" in diag_key or "IEC" == diag_key):
                new_gy = get_ECRH_viewing_angles(self.Scenario.shot, \
                                                self.Scenario.used_diags_dict[diag_key].beamline, \
                                                self.Scenario.used_diags_dict[diag_key].base_freq_140)
                if(new_gy.error == 0):
                    gy_dict[str(self.Scenario.used_diags_dict[diag_key].beamline)] = new_gy
                else:
                    print("Error when reading viewing angles")
                    print("Launch aborted")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('Error while preparing launch!')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
            ECI_dict = {}
            if(diag_key in ["ECN", "ECO", "ECI"]):
                ECI_dict = get_ECI_launch(self.Scenario.used_diags_dict[diag_key], self.Config.shot)
        Scenario.ray_launch = []
        # Prepare the launches for each time point
        # Some diagnostics have steerable LO, hence each time point has an individual launch
        for time in Scenario.plasma_dict["time"]:
            Scenario.ray_launch.append(get_diag_launch(Scenario.shot, time, Scenario.used_diags_dict, \
                                                        gy_dict=gy_dict, ECI_dict=ECI_dict))
        Scenario.diags_set = True
        return Scenario

    def SetScenario(self, Scenario):
        for Diagkey in self.diag_cb_dict.keys():
            self.diag_cb_dict[Diagkey].SetValue(False)
            if(Diagkey in Scenario.used_diags_dict.keys()):
                self.diag_cb_dict[Diagkey].SetValue(True)
        self.Notebook.DistributeInfo(Scenario)

class Diag_Notebook(wx.Choicebook):
    def __init__(self, parent):
        wx.Choicebook.__init__(self, parent, wx.ID_ANY, \
                            style=wx.BK_DEFAULT)
        self.PageList = []

    def Spawn_Pages(self, DiagDict) :
        self.varsize = (0, 0)
        for diag in DiagDict.keys():
            self.PageList.append(Diag_Page(self, DiagDict[diag]))
            pagename = self.PageList[-1].name
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
            self.AddPage(self.PageList[-1], pagename)

    def UpdateDiagDict(self, DiagDict):
        for i in range(len(self.PageList)):
            DiagDict[self.PageList[i].name] = self.PageList[i].RetrieveDiag()
        return DiagDict

    def DistributeInfo(self, Scenario):
        for i in range(len(self.PageList)):
            if(self.PageList[i].name in Scenario.avail_diags_dict.keys()):
                self.PageList[i].DepositDiag(Scenario.avail_diags_dict[self.PageList[i].name])


class Diag_Page(wx.Panel):
    def __init__(self, parent, Diag_obj, border=1, maxwidth=max_var_in_row, \
                    parentmode=False, style=wx.TAB_TRAVERSAL | wx.NO_BORDER):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=style)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.diagpanel = Diag_Panel(self, Diag_obj)
        self.name = Diag_obj.name
        self.sizer.Add(self.diagpanel, 0, wx.ALL | wx.TOP, 5)

    def RetrieveDiag(self):
        self.diag = self.diagpanel.GetDiag()
        return self.diag

    def DepositDiag(self, diag):
        self.diagpanel.SetDiag(diag)

class Diag_Panel(wx.Panel):
    def __init__(self, parent, Diag_obj):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.Diag = Diag_obj
        self.grid_sizer = wx.GridSizer(0, 4, 0, 0)
        self.art_data_beamline = 1
        self.art_data_base_freq_140 = True
        self.art_data_pol_coeff_X = 1.0
        self.art_data_pol_launch = 0.0
        self.art_data_tor_launch = 0.0
        if(not hasattr(self.Diag, 'N_ch')):
            self.N_freq_tc = simple_label_tc(self, "# frequencies", self.Diag.N_freq, "integer")
            self.N_freq_tc.Disable()
            self.N_ray_tc = simple_label_tc(self, "# rays", self.Diag.N_ray, "integer")
            self.N_ray_tc.Disable()
            self.waist_scale_tc = simple_label_tc(self, "waist scale", self.Diag.waist_scale, "real")
            self.waist_scale_tc.Disable()
            self.waist_shift_tc = simple_label_tc(self, "waist shift", self.Diag.waist_shift, "real")
            self.waist_shift_tc.Disable()
        self.exp_tc = simple_label_tc(self, "Exp", self.Diag.exp, "string")
        self.diag_tc = simple_label_tc(self, "DIAG", self.Diag.diag, "string")
        self.ed_tc = simple_label_tc(self, "Edition", self.Diag.ed, "integer")
        if(hasattr(self.Diag, 'beamline')):
            if(self.Diag.name == "CTC" or self.Diag.name == "IEC"):
                self.beamline_tc = simple_label_tc(self, "Beamline", self.Diag.beamline, "integer")
            else:
                self.beamline_tc = simple_label_tc(self, "Beamline", self.Diag.beamline, "integer")
            self.pol_coeff_X_tc = simple_label_tc(self, "Pol. coeff. X", self.Diag.pol_coeff_X, "real")
            self.base_freq_140_cb = simple_label_cb(self, "140 [GHz]", self.Diag.base_freq_140)
        elif(hasattr(self.Diag, 'Rz_exp')):
            self.RZ_label = wx.StaticText(self, wx.ID_ANY, "Geometry:")
            self.exp_tc_RZ = simple_label_tc(self, "Exp", self.Diag.Rz_exp, "string")
            self.diag_tc_RZ = simple_label_tc(self, "DIAG", self.Diag.Rz_diag, "string")
            self.ed_tc_RZ = simple_label_tc(self, "Edition", self.Diag.Rz_ed, "integer")
            self.grid_sizer.AddSpacer(10)
        elif(hasattr(self.Diag, 'N_ch')):
            self.selected_channel = 0
            self.N_freq_tc = simple_label_tc(self, "# frequencies", self.Diag.N_freq[self.selected_channel], "integer")
            self.N_freq_tc.Disable()
            self.N_ray_tc = simple_label_tc(self, "# rays", self.Diag.N_ray[self.selected_channel], "integer")
            self.N_ray_tc.Disable()
            self.waist_scale_tc = simple_label_tc(self, "waist scale", self.Diag.waist_scale[self.selected_channel], "real")
            self.waist_scale_tc.Disable()
            self.waist_shift_tc = simple_label_tc(self, "waist shift", self.Diag.waist_shift[self.selected_channel], "real")
            self.waist_shift_tc.Disable()
            self.ext_h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.N_ch_tc = simple_label_tc(self, "# of Channels", self.Diag.N_ch, "integer")
            self.update_N_ch_Button = wx.Button(self, label='Update Channel Number')
            self.update_N_ch_Button.Bind(wx.EVT_BUTTON, self.OnUpdateNch)
            self.chanel_select = wx.ComboBox(self, wx.ID_ANY, choices=np.array(range(1, self.Diag.N_ch + 1), dtype="|S3").tolist(), \
                                             style=wx.CB_READONLY | wx.ALIGN_CENTRE, size=(150, -1))
            self.chanel_select.Bind(wx.EVT_COMBOBOX, self.OnNewChannelSelected)
            self.ray_launch_format_cb = simple_label_cb(self, "Raylaunch file", False)
            self.load_launch_Button = wx.Button(self, label='Load launch')
            self.load_launch_Button.Bind(wx.EVT_BUTTON, self.OnLoadLaunch)
            self.save_launch_Button = wx.Button(self, label='Save launch')
            self.save_launch_Button.Bind(wx.EVT_BUTTON, self.OnSaveLaunch)
            self.ArtCTA_launch_Button = wx.Button(self, label='Artifical CTA launch')
            self.ArtCTA_launch_Button.Bind(wx.EVT_BUTTON, self.OnMakeArtificalCTA)
            self.f_tc = simple_label_tc(self, "f [GHz]", self.Diag.f[self.selected_channel] / 1.e9, "real")
            self.df_tc = simple_label_tc(self, "Bandwidth [GHz]", self.Diag.df[self.selected_channel] / 1.e9, "real")
            self.R_tc = simple_label_tc(self, "R [m]", self.Diag.R[self.selected_channel], "real")
            self.phi_tc = simple_label_tc(self, "phi [deg]", self.Diag.phi[self.selected_channel], "real")
            self.z_tc = simple_label_tc(self, "z [m]", self.Diag.z[self.selected_channel], "real")
            self.theta_pol_tc = simple_label_tc(self, "theta pol [deg]", self.Diag.theta_pol[self.selected_channel], "real")
            self.phi_tor_tc = simple_label_tc(self, "phi tor [deg]", self.Diag.phi_tor[self.selected_channel], "real")
            self.dist_focus_tc = simple_label_tc(self, "distance launch-focus [m]", self.Diag.dist_focus[self.selected_channel], "real")
            self.width_tc = simple_label_tc(self, "1/e^2 beam width[m]", self.Diag.width[self.selected_channel], "real")
            self.pol_coeff_X_tc = simple_label_tc(self, "X-mode fraction", self.Diag.pol_coeff_X[self.selected_channel], "real", \
                                                  tooltip="-1 for toroidally aligned polarizer")
            self.chanel_select.Select(0)
            # self.launch_label = wx.StaticText(self, wx.ID_ANY, "Launching Geometry")
            self.grid_sizer.AddSpacer(10)
        elif(hasattr(self.Diag, 'R_scale')):
            self.R_scale_tc = simple_label_tc(self, "R scale", self.Diag.R_scale, "real")
            self.z_scale_tc = simple_label_tc(self, "z scale", self.Diag.z_scale, "real")
        self.grid_sizer.Add(self.N_freq_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.N_ray_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.waist_scale_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.waist_shift_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.exp_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.diag_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.grid_sizer.Add(self.ed_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        if(hasattr(self.Diag, 'beamline')):
            self.grid_sizer.Add(self.beamline_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.pol_coeff_X_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.base_freq_140_cb, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        elif(hasattr(self.Diag, 'Rz_exp')):
            self.grid_sizer.Add(self.RZ_label, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.exp_tc_RZ, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.diag_tc_RZ, 0, \
                             wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.ed_tc_RZ, 0, \
                             wx.ALIGN_LEFT | wx.ALL, 5)
        elif(hasattr(self.Diag, 'N_ch')):
            self.ext_h_sizer.Add(self.N_ch_tc, 0, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.ext_h_sizer.Add(self.update_N_ch_Button, 0, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.ext_h_sizer.Add(self.chanel_select, 1, \
                                 wx.EXPAND | wx.ALL, 5)
            self.ext_h_sizer.Add(self.ray_launch_format_cb, 1, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.ext_h_sizer.Add(self.load_launch_Button, 1, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.ext_h_sizer.Add(self.save_launch_Button, 1, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.ext_h_sizer.Add(self.ArtCTA_launch_Button, 1, \
                                 wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            self.sizer.Add(self.ext_h_sizer, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.f_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.df_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.R_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.phi_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.z_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.theta_pol_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.phi_tor_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.dist_focus_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.width_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.pol_coeff_X_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        elif(hasattr(self.Diag, 'R_scale')):
            self.grid_sizer.Add(self.R_scale_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
            self.grid_sizer.Add(self.z_scale_tc, 0, \
                         wx.ALIGN_LEFT | wx.ALL, 5)
        self.sizer.Add(self.grid_sizer, 0, \
                             wx.ALIGN_LEFT | wx.ALL, 5)
        self.SetSize(self.sizer.GetSize())

    def OnUpdateNch(self, evt):
        N_ch = self.N_ch_tc.GetValue()
        if(N_ch < self.Diag.N_ch):
            temp = self.Diag.f
            self.Diag.f = np.zeros(N_ch)
            self.Diag.f[:] = temp[0:N_ch]
            temp = self.Diag.df
            self.Diag.df = np.zeros(N_ch)
            self.Diag.df[:] = temp[0:N_ch]
            temp = self.Diag.N_freq
            self.Diag.N_freq = np.zeros(N_ch, dtype=np.int)
            self.Diag.N_freq[:] = temp[0:N_ch]
            temp = self.Diag.N_ray
            self.Diag.N_ray = np.zeros(N_ch, dtype=np.int)
            self.Diag.N_ray[:] = temp[0:N_ch]
            temp = self.Diag.waist_scale
            self.Diag.waist_scale = np.zeros(N_ch)
            self.Diag.waist_scale[:] = temp[0:N_ch]
            temp = self.Diag.waist_shift
            self.Diag.waist_shift = np.zeros(N_ch)
            self.Diag.waist_shift[:] = temp[0:N_ch]
            temp = self.Diag.R
            self.Diag.R = np.zeros(N_ch)
            self.Diag.R[:] = temp[0:N_ch]
            temp = self.Diag.phi
            self.Diag.phi = np.zeros(N_ch)
            self.Diag.phi[:] = temp[0:N_ch]
            temp = self.Diag.z
            self.Diag.z = np.zeros(N_ch)
            self.Diag.z[:] = temp[0:N_ch]
            temp = self.Diag.theta_pol
            self.Diag.theta_pol = np.zeros(N_ch)
            self.Diag.theta_pol[:] = temp[0:N_ch]
            temp = self.Diag.phi_tor
            self.Diag.phi_tor = np.zeros(N_ch)
            self.Diag.phi_tor[:] = temp[0:N_ch]
            temp = self.Diag.dist_focus
            self.Diag.dist_focus = np.zeros(N_ch)
            self.Diag.dist_focus[:] = temp[0:N_ch]
            temp = self.Diag.width
            self.Diag.width = np.zeros(N_ch)
            self.Diag.width[:] = temp[0:N_ch]
            if(self.selected_channel > N_ch):
                self.selected_channel = N_ch - 1
        elif(N_ch > self.Diag.N_ch):
            temp = self.Diag.f
            self.Diag.f = np.zeros(N_ch)
            self.Diag.f[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.f[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.df
            self.Diag.df = np.zeros(N_ch)
            self.Diag.df[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.df[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.N_freq
            self.Diag.N_freq = np.zeros(N_ch, dtype=np.int)
            self.Diag.N_freq[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.N_freq[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.N_ray
            self.Diag.N_ray = np.zeros(N_ch)
            self.Diag.N_ray[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.N_ray[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.waist_scale
            self.Diag.waist_scale = np.zeros(N_ch)
            self.Diag.waist_scale[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.waist_scale[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.waist_shift
            self.Diag.waist_shift = np.zeros(N_ch)
            self.Diag.waist_shift[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.waist_shift[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.R
            self.Diag.R = np.zeros(N_ch)
            self.Diag.R[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.R[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.phi
            self.Diag.phi = np.zeros(N_ch)
            self.Diag.phi[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.phi[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.z
            self.Diag.z = np.zeros(N_ch)
            self.Diag.z[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.z[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.theta_pol
            self.Diag.theta_pol = np.zeros(N_ch)
            self.Diag.theta_pol[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.theta_pol[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.phi_tor
            self.Diag.phi_tor = np.zeros(N_ch)
            self.Diag.phi_tor[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.phi_tor[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.dist_focus
            self.Diag.dist_focus = np.zeros(N_ch)
            self.Diag.dist_focus[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.dist_focus[self.Diag.N_ch:N_ch] = temp[-1]
            temp = self.Diag.width
            self.Diag.width = np.zeros(N_ch)
            self.Diag.width[0:self.Diag.N_ch] = temp[0:self.Diag.N_ch]
            self.Diag.width[self.Diag.N_ch:N_ch] = temp[-1]
        self.Diag.N_ch = N_ch
        self.chanel_select.Clear()
        self.chanel_select.AppendItems(np.array(range(1, N_ch + 1), dtype="|S3").tolist())
        self.chanel_select.Select(0)

    def OnNewChannelSelected(self, evt):
        self.Diag.f[self.selected_channel] = self.f_tc.GetValue() * 1.e9
        self.Diag.df[self.selected_channel] = self.df_tc.GetValue() * 1.e9
        self.Diag.N_freq[self.selected_channel] = self.N_freq_tc.GetValue()
        self.Diag.N_ray[self.selected_channel] = self.N_ray_tc.GetValue()
        self.Diag.waist_scale[self.selected_channel] = self.waist_scale_tc.GetValue()
        self.Diag.waist_shift[self.selected_channel] = self.waist_shift_tc.GetValue()
        self.Diag.R[self.selected_channel] = self.R_tc.GetValue()
        self.Diag.phi[self.selected_channel] = self.phi_tc.GetValue()
        self.Diag.z[self.selected_channel] = self.z_tc.GetValue()
        self.Diag.theta_pol[self.selected_channel] = self.theta_pol_tc.GetValue()
        self.Diag.phi_tor[self.selected_channel] = self.phi_tor_tc.GetValue()
        self.selected_channel = int(self.chanel_select.GetValue()) - 1
        self.f_tc.SetValue(self.Diag.f[self.selected_channel] / 1.e9)
        self.df_tc.SetValue(self.Diag.df[self.selected_channel] / 1.e9)
        self.R_tc.SetValue(self.Diag.R[self.selected_channel])
        self.phi_tc.SetValue(self.Diag.phi[self.selected_channel])
        self.z_tc.SetValue(self.Diag.z[self.selected_channel])
        self.theta_pol_tc.SetValue(self.Diag.theta_pol[self.selected_channel])
        self.phi_tor_tc.SetValue(self.Diag.phi_tor[self.selected_channel])
        self.dist_focus_tc.SetValue(self.Diag.dist_focus[self.selected_channel])
        self.width_tc.SetValue(self.Diag.width[self.selected_channel])

    def OnLoadLaunch(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a *_launch.dat file for input", \
            defaultDir=self.ECFMConfig.working_dir, \
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
        else:
            print("Import aborted")
            return

    def OnSaveLaunch(self, evt):
        dlg = wx.DirDialog(self,
                           message="Choose the folder to store the EXT_launch.dat file")  # defaultDir=self.ECFMConfig.working_dir, \
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            used_diags_dict = {}
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
                new_gy = get_ECRH_launcher(self.ECFMConfig.shot, diags_dict["CTA"].beamline, diags_dict["CTA"].base_freq_140)
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
                diag_launch = get_diag_launch(self.ECFMConfig.working_dir, self.ECFMConfig.shot, 0.0, diags_dict, gy_dict=gy_dict)
                self.SetDiag(EXT_diag(self.Diag.name, self.Diag.exp, self.Diag.diag, self.Diag.ed, \
                             diag_launch=diag_launch, t_smooth=self.Diag.t_smooth, append_launch=self.append))
            except Exception as e:
                print("Failed to load external launch - reason:")
                print(e)
                return
        else:
            print("Setup aborted")
            return

    def GetDiag(self):
        self.Diag.exp = self.exp_tc.GetValue()
        self.Diag.diag = self.diag_tc.GetValue()
        self.Diag.ed = self.ed_tc.GetValue()
        if(hasattr(self.Diag, 'beamline')):
            self.Diag.beamline = self.beamline_tc.GetValue()
            self.Diag.pol_coeff_X = self.pol_coeff_X_tc.GetValue()
            self.Diag.base_freq_140 = self.base_freq_140_cb.GetValue()
        elif(hasattr(self.Diag, 'Rz_exp')):
            self.Diag.Rz_exp = self.exp_tc_RZ.GetValue()
            self.Diag.Rz_diag = self.diag_tc_RZ.GetValue()
            self.Diag.Rz_ed = self.ed_tc_RZ.GetValue()
        elif(hasattr(self.Diag, 'N_ch')):
            self.Diag.f[self.selected_channel] = self.f_tc.GetValue() * 1.e9
            self.Diag.df[self.selected_channel] = self.df_tc.GetValue() * 1.e9
            self.Diag.R[self.selected_channel] = self.R_tc.GetValue()
            self.Diag.phi[self.selected_channel] = self.phi_tc.GetValue()
            self.Diag.z[self.selected_channel] = self.z_tc.GetValue()
            self.Diag.theta_pol[self.selected_channel] = self.theta_pol_tc.GetValue()
            self.Diag.phi_tor[self.selected_channel] = self.phi_tor_tc.GetValue()
            self.Diag.dist_focus[self.selected_channel] = self.dist_focus_tc.GetValue()
            self.Diag.width[self.selected_channel] = self.width_tc.GetValue()
            self.Diag.pol_coeff_X[self.selected_channel] = self.pol_coeff_X_tc.GetValue()
        elif(hasattr(self.Diag, 'R_scale')):
            self.Diag.R_scale = self.R_scale_tc.GetValue()
            self.Diag.z_scale = self.z_scale_tc.GetValue()
        return self.Diag

    def SetDiag(self, Diag):
        self.Diag = Diag
        self.exp_tc.SetValue(self.Diag.exp)
        self.diag_tc.SetValue(self.Diag.diag)
        self.ed_tc.SetValue(self.Diag.ed)
        if(hasattr(self.Diag, 'beamline')):
            self.beamline_tc.SetValue(self.Diag.beamline)
            self.pol_coeff_X_tc.SetValue(self.Diag.pol_coeff_X)
            self.base_freq_140_cb.SetValue(self.Diag.base_freq_140)
        elif(hasattr(self.Diag, 'Rz_exp')):
            self.exp_tc_RZ.SetValue(self.Diag.Rz_exp)
            self.diag_tc_RZ.SetValue(self.Diag.Rz_diag)
            self.ed_tc_RZ.SetValue(self.Diag.Rz_ed)
        elif(hasattr(self.Diag, 'N_ch')):
            self.ext_h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.N_ch_tc.SetValue(self.Diag.N_ch)
            self.chanel_select.Clear()
            self.chanel_select.AppendItems(np.array(range(1, self.Diag.N_ch + 1), dtype="|S3").tolist())
            self.selected_channel = 0
            self.f_tc.SetValue(self.Diag.f[self.selected_channel] / 1.e9)
            self.R_tc.SetValue(self.Diag.R[self.selected_channel])
            self.phi_tc.SetValue(self.Diag.phi[self.selected_channel])
            self.z_tc.SetValue(self.Diag.z[self.selected_channel])
            self.theta_pol_tc.SetValue(self.Diag.theta_pol[self.selected_channel])
            self.phi_tor_tc.SetValue(self.Diag.phi_tor[self.selected_channel])
            self.dist_focus_tc.SetValue(self.Diag.dist_focus[self.selected_channel])
            self.width_tc.SetValue(self.Diag.width[self.selected_channel])
            self.pol_coeff_X_tc.SetValue(self.Diag.pol_coeff_X[self.selected_channel])
            self.chanel_select.Select(0)
        elif(hasattr(self.Diag, 'R_scale')):
            self.R_scale_tc.SetValue(self.Diag.R_scale)
            self.z_scale_tc.SetValue(self.Diag.z_scale)
        return self.Diag

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
