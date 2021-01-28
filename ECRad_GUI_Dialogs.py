'''
Created on Jul 15, 2019

@author: sdenk
'''
import wx
import numpy as np
from ECRad_GUI_Widgets import simple_label_cb, simple_label_tc
import os
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
        
        
        
        
        
        