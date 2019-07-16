'''
Created on Jul 15, 2019

@author: sdenk
'''
import wx
import numpy as np
# Only contains the GENE time select window for now
class Select_GENE_timepoints_dlg(wx.Dialog):
    def __init__(self, parent, time_points):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.used = list(np.asarray(time_points * 1.e-3, dtype="|S7"))
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
        