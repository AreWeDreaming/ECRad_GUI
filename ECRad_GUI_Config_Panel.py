'''
Created on Apr 3, 2019

@author: sdenk
'''
import wx
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row
import os
class ConfigPanel(wx.Panel):
    def __init__(self, parent, Config, border=1, maxwidth=max_var_in_row, \
                    parentmode=False, style=wx.TAB_TRAVERSAL | wx.NO_BORDER):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=style)
        self.name = "ECRad settings"
        columns = 8
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.grid_list = []
        self.labels = []
        self.lines = []
        self.widgets = {}
        for key in Config.main_keys:
            self.lines.append(wx.StaticLine(self, wx.ID_ANY))
            self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
            self.labels.append(wx.StaticText(self, wx.ID_ANY, key + " Settings"))
            self.sizer.Add(self.labels[-1], 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
            self.lines.append(wx.StaticLine(self, wx.ID_ANY))
            self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
            self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
            for sub_key in Config.sub_keys[key]:
                if(Config.types[sub_key] == "b"):
                    self.widgets[sub_key] = simple_label_cb(self, Config.nice_labels[sub_key], Config[key][sub_key])
                else:
                    self.widgets[sub_key] = simple_label_tc(self, Config.nice_labels[sub_key], Config[key][sub_key], None)
                self.grid_list[-1].Add(self.widgets[sub_key], 0, wx.ALL | wx.LEFT | wx.TOP, 5)
            self.sizer.Add(self.grid_list[-1], 0, wx.ALL | wx.LEFT, 5)
        self.widgets["use_ext_rays"].SetToolTip("Load ECRad results in the Scenario panel to enable")
        self.widgets["use_ext_rays"].Disable()

    def UpdateConfig(self, Config):
        for key in Config.main_keys:
            for sub_key in Config.sub_keys[key]:
                Config[key][sub_key] = self.widgets[sub_key].GetValue()
        return Config

    def SetConfig(self, Config):
        for key in Config.main_keys:
            for sub_key in Config.sub_keys[key]:
                self.widgets[sub_key].SetValue(Config[key][sub_key]) 
        
    def EnableExtRays(self):
        self.use_ext_rays_cb.Enable()

    def DisableExtRays(self):
        self.use_ext_rays_cb.Disable()
