'''
Created on 11.04.2019

@author: Severin Denk
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
        elif(self.stat_unc is not None and self.sys_unc is None):
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             self.stat_unc[timeindex], None, self.is_prof)
        else:
            return TimeSlice(self.Diag.name, self.rhop[timeindex], self.val[timeindex], \
                             self.stat_unc[timeindex], self.sys_unc[timeindex], self.is_prof)
        
class TimeSlice:
    def __init__(self, name, rhop, val, stat_unc, sys_unc, is_prof):
        self.name = name
        self.rhop = np.copy(rhop)
        self.val = np.copy(val)
        self.is_prof = is_prof
        if(stat_unc is not None):
            self.unc = np.copy(stat_unc)
        if(sys_unc is not None):
            self.unc += np.copy(sys_unc)
        if(stat_unc is None and sys_unc is None):
            self.unc = None
        else:
            self.unc = np.copy(self.unc)
            self.rhop = np.copy(self.rhop)
            self.val = np.copy(self.val)
        