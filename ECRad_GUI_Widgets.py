'''
Created on Mar 21, 2019

@author: sdenk
'''
import wx
from ECFM_GUI_regex import test_float, test_integer, integer_pattern
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
    def __init__(self, parent, label, state):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.SetAutoLayout(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.label = wx.StaticText(self, wx.ID_ANY, label)
        self.label.Wrap(160)
        self.cb = wx.CheckBox(self, wx.ID_ANY, "")
        self.cb.SetValue(state)
        self.sizer.Add(self.label, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.cb, 0, \
            wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetClientSize(self.GetEffectiveMinSize())

    def GetValue(self):
        return self.cb.GetValue()

    def SetValue(self, state):
        return self.cb.SetValue(state)

class simple_label_tc(wx.Panel):
    def __init__(self, parent, label, value, value_type, border=0, tooltip=None):
        if(border):
            wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        else:
            wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.SetAutoLayout(True)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
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
                    style=wx.ALIGN_CENTER)
        self.label.Wrap(160)
        self.tc = wx.TextCtrl(self, wx.ID_ANY, str(value))
        if(tooltip is not None):
            self.tc.SetToolTip(wx.ToolTip(tooltip))
        self.lastValue = str(value)
        self.SetValue(value)
        self.tc.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.tc.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.sizer.Add(self.label, 0, \
            wx.ALIGN_CENTER_VERTICAL | wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.tc, 0, \
            wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        if(len(label_text) < 25):
            self.grsize = (1, 2)
        elif(len(label_text) < 45):
            self.grsize = (1, 3)
        else:
            self.grsize = (2, 3)
        self.grpos = (-1, -1)
        self.SetClientSize(self.GetEffectiveMinSize())

    def GetValue(self):
        if(self.value_type == 'string'):
            self.value = self.tc.GetValue()
            return self.value

        elif(self.value_type == 'real'):
            temp_str = self.tc.GetValue().replace('d', 'e').replace(',', '')
            self.value = float(temp_str)
            return self.value

        elif(self.value_type == 'integer'):
            self.value = int(float(self.tc.GetValue().replace(',', '')))
            return self.value

    def SetValue(self, Value):
        if(self.test_str(str(self.GetValue()))):
            self.lastValue = str(self.GetValue())
        if(self.value_type == 'string' or type(Value) == str):
            self.tc.SetValue(Value)
        elif(type(Value) == np.unicode_):
            self.tc.SetValue(str(Value))
        elif(self.value_type == 'real'):
            self.tc.SetValue("{0:f}".format(Value).replace(',', ''))
        elif(self.value_type == 'integer'):
            self.tc.SetValue("{0:d}".format(int(Value)).replace(',', ''))

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

    def test_str(self, test_str):
        if(self.value_type == 'string'):
            return True
        if(self.value_type == 'real' and test_float(test_str)):
            return True
        elif(self.value_type == 'integer' and re.search(\
                                                integer_pattern, test_str)):
            return True
        else:
            return False


class Variable_CheckBox(wx.Panel):
    def __init__(self, parent, Var, border=0):
        if(border):
            wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        else:
            wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.Var = Var
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        label_text = Var.desc.replace('_', label_seperator)
        if(use_newlines and len(label_text) > 8):
            for i in range(7, int(len(label_text))):
                if(label_text[i] == ' '):
                    label_text = label_text[0:i] + EOLCHART + \
                                        label_text[i + 1:len(label_text)]
                    break
        self.cb = wx.CheckBox(self, wx.ID_ANY, label_text)
        self.cb.SetValue(Var.value)
        self.sizer.Add(self.cb, 0, \
            wx.ALIGN_CENTER_VERTICAL | wx.ALL | wx.EXPAND, 5)
        self.grsize = (1, 1)
        self.grpos = (-1, -1)
        self.SetClientSize(self.GetEffectiveMinSize())

    def ReturnVar(self):
        self.Var.value = self.cb.GetValue()
        return self.Var



class Add_Tuple_Dialog(wx.Dialog):
    def __init__(self, parent, TupleList, Var):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.GridSizer(6, Var.n, 5, 5)
        self.TextCtrlList = []
        self.Var = Var
        self.TupleList = TupleList
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        self.label = wx.StaticText(self, wx.ID_ANY, 'Adding tuples to: {0}'\
            .format(Var.desc) + '.' + EOLCHART + \
            'Click Accept when you are done', style=wx.ALIGN_CENTER)
        for i in range(6 * Var.n):
            self.TextCtrlList.append(wx.TextCtrl(self, wx.ID_ANY))
            self.grid.Add(self.TextCtrlList[i], 0, wx.ALL, 5)
        self.SetSizer(self.sizer)
        self.sizer.Add(self.label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.sizer.Add(self.ButtonSizer, 0, wx.ALL | \
                                    wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetClientSize(self.GetEffectiveMinSize())


    def EvtClose(self, Event):
        self.EndModal(False)

    def EvtAccept(self, Event):
        for i in range(6):
            cur_str = ''
            for j in range(self.Var.n):
                if(test_float(self.TextCtrlList[i + j].\
                                        GetValue())):
                    if(len(cur_str) > 0):
                        cur_str += ',' + \
                            self.TextCtrlList[i * self.Var.n + j]\
                                                                .GetValue()
                    else:
                        cur_str = self.TextCtrlList[i * self.Var.n + j]\
                                                                .GetValue()
                else:
                    cur_str = ''
                    break
            if('real' in self.Var.var_type and test_float(cur_str, 1)):
                    if(test_integer(cur_str, 1)):
                        temp_arr = cur_str.split(',')
                        cur_str = temp_arr[0] + '.0'
                        for j in range(1, len(temp_arr)):
                            cur_str += ',' + temp_arr[j] + '.0'
                    self.TupleList.append(cur_str)
            elif('integer' in self.Var.var_type and \
                            test_integer(cur_str, 1)):
                    self.TupleList.append(cur_str)
        self.EndModal(True)
