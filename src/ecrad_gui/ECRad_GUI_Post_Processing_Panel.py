from ecrad_pylib.Global_Settings import globalsettings
import wx
from WX_Events import EVT_UPDATE_DATA

class PostProcessingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.controlplotsizer = wx.BoxSizer(wx.VERTICAL)
        self.Results = None
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.name = "ECRad settings"
        columns = 8
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.grid_list = []
        self.labels = []
        self.lines = []
        self.widgets = {}
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.labels.append(wx.StaticText(self, wx.ID_ANY, "Distributions"))
        self.sizer.Add(self.labels[-1], 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
        self.widgets["birthplace_3D_button"] = wx.Button(self, wx.ID_ANY, "Calculate 3D BDP")
        self.widgets["birthplace_3D_button"].Bind(wx.EVT_BUTTON, self.OnCalculated3DBPD)
        self.widgets["birthplace_3D_button"].SetToolTip("Load ECRad results to enable")
        self.widgets["birthplace_3D_button"].Disable()
        self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
        self.grid_list[-1].Add(self.widgets["birthplace_3D_button"], 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.sizer.Add(self.grid_list[-1], 0, wx.ALL | wx.LEFT, 5)
        

    def OnUpdate(self, evt):
            self.Results = evt.Results
            if(not self.widgets["birthplace_3D_button"].IsEnabled()):
                self.widgets["birthplace_3D_button"].Enable()

    def OnCalculated3DBPD(self, evt):
        self.Results.Calcuate3DBDP()