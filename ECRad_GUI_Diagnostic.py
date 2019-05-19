'''
Created on 11.04.2019

@author: sdenk
'''
import numpy as np
# This class distinguishes itself from Diags by also containing actual diagnostic data
class Diagnostic:
    def __init__(self, Diag, is_prof=False):
        self.Diag = Diag # Instance of Diag
        self.rhop = []
        self.val = []
        self.stat_unc = []
        self.sys_unc = []
        self.is_prof = is_prof
        
    def insert_data(self, rhop, val, stat_unc, sys_unc):
        self.rhop = rhop
        self.val = val
        self.stat_unc = stat_unc
        self.sys_unc = sys_unc
        
    def getSlice(self, timeindex):
        if(self.stat_unc is None and self.sys_unc is None):
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             None, None, self.is_prof)
        elif(self.stat_unc is None and self.sys_unc is not None):
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             None, self.sys_unc[timeindex], self.is_prof)
        elif(self.stat_unc  is not None and self.sys_unc is None):
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             self.stat_unc[timeindex], None, self.is_prof)
        else:
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             self.stat_unc[timeindex], self.sys_unc[timeindex], self.is_prof)
        
class TimeSlice:
    def __init__(self, name, rhop, val, stat_unc, sys_unc, is_prof, max_unc=0.5):
        self.name = name
        self.rhop = rhop
        self.val = val
        self.is_prof = is_prof
        if(stat_unc is not None):
            self.unc = stat_unc
        if(sys_unc is not None):
            self.unc += sys_unc
        if(stat_unc is None and sys_unc is None):
            self.unc = None
        else:
            mask = self.val * max_unc > np.abs(self.unc)
            self.unc = self.unc[mask]
            self.rhop = self.rhop[mask]
            self.val = self.val[mask]
        