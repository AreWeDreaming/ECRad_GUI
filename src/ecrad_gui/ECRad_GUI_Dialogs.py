'''
Created on Jul 15, 2019

@author: Severin Denk
'''
import wx
import numpy as np
from ecrad_gui.ECRad_GUI_Widgets import simple_label_cb, simple_label_tc
import os
from uncertainties import unumpy
# Only contains the GENE time select window for now
class Select_GENE_timepoints_dlg(wx.Dialog):
    def __init__(self, parent, time_points):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.used = list(np.asarray(time_points * 1.e-3, dtype="|U7"))
        self.unused = []
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used time points [ms]")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.used_list.AppendItems(self.used)
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
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused time points [ms]")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.SetSizer(self.sizer)
        self.sizer.Add(self.select_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
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

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def EvtAccept(self, Event):
        self.EndModal(wx.ID_OK)
        
class TextEntryDialog(wx.Dialog):
    def __init__(self, parent, message, default_val = ""):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)        
        self.label = wx.StaticText(self, wx.ID_ANY, message)
        self.val_tc = wx.TextCtrl(self, wx.ID_ANY, default_val)
        self.sizer.Add(self.label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.val_tc, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def EvtAccept(self, Event):
        self.val = self.val_tc.GetValue()
        self.EndModal(wx.ID_OK)

class IMASSelectDialog(wx.Dialog):
    def __init__(self, parent, description, user="public", database="ITER", shot=150601, run=1):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.description_label = wx.StaticText(self, wx.ID_ANY, description, \
                                   style=wx.ALIGN_CENTER_HORIZONTAL)
        self.sizer.Add(self.description_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.description_separator = wx.StaticLine(self, wx.ID_ANY)
        self.sizer.Add(self.description_separator, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.tc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.user_dir_tc = simple_label_tc(self, "Stored under", user, "string")
        self.tc_sizer.Add(self.user_dir_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.database_tc = simple_label_tc(self, "Database", database, "string")
        self.tc_sizer.Add(self.database_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.shot_tc = simple_label_tc(self, "shot", shot, "integer") #100003
        self.tc_sizer.Add(self.shot_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.run_tc = simple_label_tc(self, "run", run, "integer")
        self.tc_sizer.Add(self.run_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ids_meta_separator = wx.StaticLine(self, wx.ID_ANY)
        self.sizer.Add(self.tc_sizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ids_meta_separator, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.backend_label = wx.StaticText(self, wx.ID_ANY, "Backend", \
                                   style=wx.ALIGN_CENTER_HORIZONTAL)
        self.sizer.Add(self.backend_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.backend_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.MDS_rb = wx.RadioButton(self, wx.ID_ANY, label="MDSplus")
        self.MDS_rb.SetValue(True)
        self.HFD5_rb = wx.RadioButton(self, wx.ID_ANY, label="HDF5")
        self.backend_sizer.Add(self.MDS_rb, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.backend_sizer.Add(self.HFD5_rb, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.LoadButton = wx.Button(self, wx.ID_ANY, 'Load')
        self.Bind(wx.EVT_BUTTON, self.OnLoad, self.LoadButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.LoadButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.backend_sizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def OnLoad(self, Event):
        try:
            import imas
        except ImportError:
            print("IMAS not accessible!")
            return
        try:
            if self.MDS_rb.GetValue():
                backend = imas.imasdef.MDSPLUS_BACKEND
            else:
                backend = imas.imasdef.HDF5_BACKEND
            self.db = imas.DBEntry(
                    backend,
                    self.database_tc.GetValue(),
                    self.shot_tc.GetValue(),
                    self.run_tc.GetValue(),
                    self.user_dir_tc.GetValue())
            self.EndModal(wx.ID_OK)
        except Exception as e:
            print("Failed to load IMAS entry")
            print(e)
            self.EndModal(wx.ID_ABORT)

class OMASdbSelectDialog(wx.Dialog):
    def __init__(self, parent, minimal=False):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.rb_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.from_file_rb = wx.RadioButton(self, wx.ID_ANY, label="Load from file")
        self.from_file_rb.Bind(wx.EVT_RADIOBUTTON, self.On_from_rb_db)
        self.rb_sizer.Add(self.from_file_rb, 0, wx.ALL | 
                          wx.ALIGN_CENTER_VERTICAL, 5)
        self.from_db_rb = wx.RadioButton(self, wx.ID_ANY, label="From machine database")
        self.rb_sizer.Add(self.from_db_rb, 0, wx.ALL | 
                          wx.ALIGN_CENTER_VERTICAL, 5)
        self.from_db_rb.Bind(wx.EVT_RADIOBUTTON, self.On_from_rb_db)
        self.sizer.Add(self.rb_sizer)
        self.widgets = []
        self.run_id_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.widgets.append(simple_label_tc(self, "Machine", "d3d"))
        self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                              wx.ALIGN_CENTER_VERTICAL, 5)
        self.widgets.append(simple_label_tc(self, "shot", 200009))
        self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                              wx.ALIGN_CENTER_VERTICAL, 5)
        if not minimal:
            self.widgets.append(simple_label_tc(self, "EFIT Tree", "EFIT"))
            self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                                  wx.ALIGN_CENTER_VERTICAL, 5)
            self.widgets.append(simple_label_tc(self, "Run ID equilibrium", "01"))
            self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                                  wx.ALIGN_CENTER_VERTICAL, 5)
            self.widgets.append(simple_label_tc(self, "Profile Tree", "OMFIT_PROFS"))
            self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                                  wx.ALIGN_CENTER_VERTICAL, 5)
            self.widgets.append(simple_label_tc(self, "Run ID Profiles", "001"))
            self.run_id_sizer.Add(self.widgets[-1], 0, wx.ALL | 
                                  wx.ALIGN_CENTER_VERTICAL, 5)
        self.On_from_rb_db(None)
        self.sizer.Add(self.run_id_sizer)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.LoadButton = wx.Button(self, wx.ID_ANY, 'Load')
        self.Bind(wx.EVT_BUTTON, self.On_Load, self.LoadButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.LoadButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)
    
    def On_from_rb_db(self, evt):
        state = self.from_db_rb.GetValue()
        for widget in self.widgets:
            if state:
                widget.Enable()
            else:
                widget.Disable()
        # Always disable the first box because only DIII-D is supported
        self.widgets[0].Disable()

    def On_Load(self, evt):
        if self.from_file_rb.GetValue():
           self.state = [True]
        else:
            self.state= [False]
            for widget in self.widgets:
                self.state.append(widget.GetValue())
        self.EndModal(wx.ID_OK)

class OMASLoadECEDataDialog(wx.Dialog):
    def __init__(self, parent, times):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)        
        self.tc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.device_tc = simple_label_tc(self, "device", "d3d", "string")
        self.tc_sizer.Add(self.device_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.shot_tc = simple_label_tc(self, "shot", 150601, "integer") #100003
        self.tc_sizer.Add(self.shot_tc, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.LoadButton = wx.Button(self, wx.ID_ANY, 'Load')
        self.Bind(wx.EVT_BUTTON, self.OnLoad, self.LoadButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.LoadButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.tc_sizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())
        self.times = times

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def OnLoad(self, Event):
        try:
            import omas
        except ImportError:
            print("OMAS not accessible!")
            return
        try:
            ods = omas.ODS()
            ods.open(self.device_tc.GetValue(), self.shot_tc.GetValue())
            self.Trad = []
            self.f = []
            self.LOS= [[ods['ece']["line_of_sight"]["first_point"]["r"],
                        ods['ece']["line_of_sight"]["first_point"]["z"]],
                       [ods['ece']["line_of_sight"]["second_point"]["r"],
                        ods['ece']["line_of_sight"]["second_point"]["z"]]]
            for time in self.times:
                self.Trad.append([])
                self.f.append([])
                for ch in ods['ece']['channel'].values():
                    itime = np.argmin(np.abs(time - ch['time']))
                    self.Trad[-1].append(unumpy.uarray(ch['t_e.data'][itime],
                                                       ch['t_e.data_error_upper'][itime]))
                    self.f[-1].append(ch["frequency.data"][itime])
            self.Trad = np.array(self.Trad)
            self.f = np.array(self.f)
            name_first = ods['ece']['channel[0].name']
            name_last = ods['ece']['channel[{0:d}].name'.format(len(self.Trad) - 1)]
            i = 0
            while i < min(len(name_first), len(name_last)):
                if(name_first[i] == name_last[i]):
                    i += 1
                else:
                    break
            self.diag_name = name_first[:i]
            self.EndModal(wx.ID_OK)
        except Exception as e:
            print("Failed to load OMAS entry")
            print(e)
            self.EndModal(wx.ID_ABORT)

class IMASTimeBaseSelectDlg(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)        
        self.label = wx.StaticText(self, wx.ID_ANY, "Use time base from:")
        self.sizer.Add(self.label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.choice = "core_profiles"
        self.FromProfilesBtn = wx.Button(self, wx.ID_ANY, 'core_profiles')
        self.Bind(wx.EVT_BUTTON, self.OnFromProfiles, self.FromProfilesBtn)
        self.FromEquilibriumBtn = wx.Button(self, wx.ID_ANY, 'equilibrium')
        self.Bind(wx.EVT_BUTTON, self.OnFromEquilibrium, self.FromEquilibriumBtn)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.FromProfilesBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.FromEquilibriumBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def OnFromProfiles(self, Event):
        self.choice = "core_profiles"
        self.EndModal(wx.ID_OK)
    
    def OnFromEquilibrium(self, Event):
        self.choice = "equilibrium"
        self.EndModal(wx.ID_OK)
        
class Use3DConfigDialog(wx.Dialog):
    def __init__(self, parent, eq_data_3D, working_dir):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.eq_data_3D = eq_data_3D.copy()
        self.working_dir  = working_dir
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.GridSizer(0,4,0,0)
        self.widgets = {}
        for key in eq_data_3D.keys():
            if(type(eq_data_3D[key]) == bool):
                self.widgets[key] = simple_label_cb(self,key.replace("_", " "), eq_data_3D[key])
            else:
                self.widgets[key] = simple_label_tc(self,key.replace("_", " "), eq_data_3D[key], None)
            self.grid.Add(self.widgets[key], 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.sizer.Add(self.grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.select_equ_file_button = wx.Button(self, wx.ID_ANY, "Select equilibrium file")
        self.select_equ_file_button.Bind(wx.EVT_BUTTON, self.OnSelectEquFile)
        self.sizer.Add(self.select_equ_file_button, 1, wx.EXPAND | wx.ALL, 5)
        self.select_vessel_file_button = wx.Button(self, wx.ID_ANY, "Select vessel file")
        self.select_vessel_file_button.Bind(wx.EVT_BUTTON, self.OnSelectVesselFile)
        self.sizer.Add(self.select_vessel_file_button, 1, wx.EXPAND | wx.ALL, 5)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(self.sizer)
        self.SetClientSize(self.GetEffectiveMinSize())
        
    def OnSelectEquFile(self, evt):
        file_dlg = wx.FileDialog(self, message="Chose 3D equilibrium file", \
                                 defaultDir=self.working_dir,style=wx.FD_OPEN)
        if(file_dlg.ShowModal() == wx.ID_OK):
            self.widgets["equilibrium_file"].SetValue(file_dlg.GetPath())
            if(os.path.basename(self.widgets["equilibrium_file"].GetValue()).startswith("g")):
                self.widgets["equilibrium_type"].SetValue("EFIT")
            else:
                self.widgets["equilibrium_type"].SetValue("VMEC")
        file_dlg.Destroy()
        
    def OnSelectVesselFile(self, evt):
        file_dlg = wx.FileDialog(self, message="Chose 3D wall file", \
                                 defaultDir=self.working_dir,style=wx.FD_OPEN)
        if(file_dlg.ShowModal() == wx.ID_OK):
            self.widgets["vessel_filename"].SetValue(file_dlg.GetPath())
        file_dlg.Destroy()

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def EvtAccept(self, Event):
        for key in self.use3Dscen.attribute_list:
            self.eq_data_3D[key] = self.widgets[key].GetValue()        
        self.EndModal(wx.ID_OK)
        


# class ECRHFreqAndHarmonicDlg(wx.Dialog):
#     def __init__(self, parent, message, default_val = ""):
#         wx.Dialog.__init__(self, parent, wx.ID_ANY)
#         self.sizer = wx.BoxSizer(wx.VERTICAL)
#         self.entry_sizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.label = wx.StaticText(self, wx.ID_ANY, message)
#         self.val_tc = wx.TextCtrl(self, wx.ID_ANY, default_val)
#         self.sizer.Add(self.label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
#         self.sizer.Add(self.val_tc, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
#         self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
#         self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
#         self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
#         self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
#         self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
#         self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
#         self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
#                                     wx.ALIGN_CENTER_HORIZONTAL, 5)
#         self.SetSizer(self.sizer)
#         self.SetClientSize(self.GetEffectiveMinSize())
        
        
        
        
        
        