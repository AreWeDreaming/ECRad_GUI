# -*- coding: utf-8 -*-
"""
Created on Tue Sep 25 17:16:40 2012

@author: Severin
"""
import wx
class Redirect_Text:
    def __init__(self, aWxTextCtrl):
        self.out = aWxTextCtrl

    def write(self, string):
        wx.CallAfter(self.out.WriteText, string)
