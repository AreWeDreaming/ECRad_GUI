'''
Created on Mar 21, 2019

@author: Severin Denk
'''
import wx
from ecrad_gui.ECRad_GUI_Regex import test_float, integer_pattern
import wx.lib.agw.toasterbox as TB
import re
import os
import numpy as np

simple_number_pattern = re.compile(r'\d')
label_seperator = ' '
EOLCHART = os.linesep  # For direct output.
EOLCHARF = '\n'
use_newlines = True
parent_width = 4
max_var_in_row = 10

class simple_label_cb(wx.Panel):
    def __init__(self, parent, label, state, event_handler=None):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.SetAutoLayout(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.label = wx.StaticText(self, wx.ID_ANY, label)
        self.label.Wrap(160)
        self.cb = wx.CheckBox(self, wx.ID_ANY, "")
        self.cb.SetValue(state)
        if event_handler is not None:
            self.cb.Bind(wx.EVT_CHECKBOX, event_handler)
        else:
            self.cb.Bind(wx.EVT_CHECKBOX, self.OnNewValByUser)
        self.sizer.Add(self.label, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.cb, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetClientSize(self.GetEffectiveMinSize())
        self.NewvalueAvailable = False
        self.state = state

    def GetValue(self):
        self.state = self.cb.GetValue()
        self.NewvalueAvailable = False
        return self.state

    def SetValue(self, state):
        self.state = state
        self.NewvalueAvailable = False
        return self.cb.SetValue(state)

    def OnNewValByUser(self, evt):
        if(self.state != self.cb.GetValue()):
            self.NewvalueAvailable = True
        else:
            self.NewvalueAvailable = False

    def CheckForNewValue(self):
        return self.NewvalueAvailable

class simple_label_choice(wx.Panel):
    def __init__(self, parent, label, items, item):
        if(item not in items):
            raise ValueError("Item {0:s} not in items: ".format(item) + str(items))
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.selection = items.index(item)
        self.SetAutoLayout(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.label = wx.StaticText(self, wx.ID_ANY, label)
        self.label.Wrap(160)
        self.choice = wx.Choice(self, wx.ID_ANY, choices=items)
        self.choice.Select(self.selection)
        self.choice.Bind(wx.EVT_CHOICE, self.OnNewChoiceByUser)
        self.sizer.Add(self.label, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.choice, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetClientSize(self.GetEffectiveMinSize())
        self.NewvalueAvailable = False

    def GetValue(self):
        self.NewvalueAvailable = False
        self.selection = self.choice.GetSelection()
        return self.choice.GetStringSelection()

    def SetValue(self, item):
        self.NewvalueAvailable = False
        self.selection = self.choice.Items.index(item)
        return self.choice.Select(self.selection)

    def OnNewChoiceByUser(self, evt):
        if(self.selection != self.choice.GetStringSelection()):
            self.NewvalueAvailable = True
        else:
            self.NewvalueAvailable = False

    def CheckForNewValue(self):
        return self.NewvalueAvailable

    def GetSelection(self):
        self.NewvalueAvailable = False
        self.selection = self.choice.GetSelection()
        return self.selection


class simple_label_tc(wx.Panel):
    def __init__(self, parent, label, value, value_type=None, border=0, tooltip=None, scale=None, readonly=False):
        if(value_type is None):
            if(type(value) == int):
                value_type = "integer"
            elif(type(value) == float):
                value_type = "real"
            elif(type(value) == str):
                value_type = "string"
        if(border):
            wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        else:
            wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.SetAutoLayout(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        if(scale is not None and value_type in ["real"]):  # Scaling only sensible for reals at this point
            self.scale = scale
            self.value = value * self.scale
        else:
            self.scale = None
            self.value = value
        self.value_type = value_type
        label_text = label
        if(use_newlines and len(label_text) > 20):
            for i in range(7, int(len(label_text))):
                if(label_text[i] == ' '):
                    label_text = label_text[0:i] + EOLCHART + \
                                        label_text[i + 1:len(label_text)]
                    break
        self.label = wx.StaticText(self, wx.ID_ANY, label_text, \
                                   style=wx.ALIGN_CENTER_HORIZONTAL)
        self.label.Wrap(160)
        if(readonly):
            self.tc = wx.TextCtrl(self, wx.ID_ANY, str(self.value), style=wx.TE_READONLY)
        else:
            self.tc = wx.TextCtrl(self, wx.ID_ANY, str(self.value))
        if(tooltip is not None):
            self.tc.SetToolTip(wx.ToolTip(tooltip))
        self.lastValue = str(value)
        self.SetValue(value)
        self.tc.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.tc.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.tc.Bind(wx.EVT_TEXT, self.OnNewValByUser)
        self.sizer.Add(self.label, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.tc, 0, \
            wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        if(len(label_text) < 25):
            self.grsize = (1, 2)
        elif(len(label_text) < 45):
            self.grsize = (1, 3)
        else:
            self.grsize = (2, 3)
        self.grpos = (-1, -1)
        self.NewvalueAvailable = False
        self.old_val = self.tc.GetValue()

    def GetValue(self):
        self.old_val = self.tc.GetValue()
        self.NewvalueAvailable = False
        if(self.value_type == 'string'):
            self.value = self.tc.GetValue()
        elif(self.value_type == 'real'):
            temp_str = self.tc.GetValue().replace('d', 'e').replace(',', '')
            self.value = float(temp_str)
            if(self.scale is not None):
                self.value /= self.scale
        elif(self.value_type == 'integer'):
            self.value = int(float(self.tc.GetValue().replace(',', '')))
        return self.value

    def SetValue(self, Value):
        if(not self.test_str(str(Value))):
            raise ValueError("Tried to set text control of type {0:s} with this unsuitable value {1:s}".format(str(self.value_type), str(Value)))
        self.value = Value
        if(self.test_str(self.tc.GetValue())):
            self.lastValue = self.tc.GetValue()
        if(self.value_type == 'string' or type(self.value) == str):
            self.tc.SetValue(self.value)
        elif(type(Value) == np.unicode_):
            self.tc.SetValue(str(self.value))
        elif(self.value_type == 'real'):
            if(self.scale is not None):
                self.value *= self.scale
            if(self.value == 0.0):
                self.tc.SetValue("{0:1.1f}".format(self.value).replace(',', ''))
            elif(self.value < 1.e-4 or self.value > 1.e5):
                self.tc.SetValue("{0:1.5e}".format(self.value).replace(',', ''))
            else:
                self.tc.SetValue("{0:4.5f}".format(self.value).replace(',', ''))
        elif(self.value_type == 'integer'):
            self.tc.SetValue("{0:d}".format(int(self.value)).replace(',', ''))
        self.old_val = self.tc.GetValue()
        self.NewvalueAvailable = False

    def OnFocus(self, Event):
        self.lastValue = self.tc.GetValue()
        Event.Skip()

    def OnKillFocus(self, Event):
        text_str = self.tc.GetValue()
        if(not self.test_str(text_str)):
            self.tc.SetValue(self.lastValue)
            self.tc.SetFocus()
            invalid_val_tb = TB.ToasterBox(self)
            invalid_val_tb.SetPopupText('Only {0} values are allowed!'\
                                        .format(self.value_type))
            invalid_val_tb.SetPopupPosition((self.tc.GetScreenPosition()[0] \
                                        + 70, self.tc.GetScreenPosition()[1]))
            invalid_val_tb.SetPopupSize((70, 100))
            invalid_val_tb.SetPopupPauseTime(2000)
            invalid_val_tb.Play()
        else:
            if(self.value_type == 'real' and \
                        re.search(integer_pattern, text_str)):
                self.tc.SetValue(text_str + '.0')
            Event.Skip()

    def test_str(self, tobechecked):
        if(self.value_type == 'string'):
            return True
        if(self.value_type == 'real' and test_float(tobechecked)):
            return True
        elif(self.value_type == 'integer' and re.search(\
                                                integer_pattern, tobechecked)):
            return True
        else:
            return False


    def OnNewValByUser(self, evt):
        if(self.old_val != self.tc.GetValue()):
            self.NewvalueAvailable = True

    def CheckForNewValue(self):
        return self.NewvalueAvailable
