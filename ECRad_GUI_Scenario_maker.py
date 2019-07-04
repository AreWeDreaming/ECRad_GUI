'''
Created on Jul 3, 2019

@author: sdenk
'''
#Module independent of the main GUI which allows the user to easily create ECRad Scenarios from external data
from GlobalSettings import globalsettings
from equilibrium_utils import EQDataSlice, special_points, EQDataExt
from TB_communication import make_mdict_from_TB_files
import numpy as np
from scipy.io import savemat
import os
from pandas.tests.io.parser import skiprows
from scipy.interpolate import InterpolatedUnivariateSpline


if(globalsettings.AUG):
    from equilibrium_utils_AUG import EQData, vessel_bd_file
    from shotfile_handling_AUG import load_IDA_data
    def make_plasma_mat_for_testing(filename, shot, times, eq_exp, eq_diag, eq_ed, \
                                    bt_vac_correction=1.005, IDA_exp="AUGD", IDA_ed=0):
        plasma_dict = load_IDA_data(shot, timepoints=times, exp=IDA_exp, ed=IDA_ed)
        EQ_obj = EQData(shot, EQ_exp=eq_exp, EQ_diag=eq_diag, EQ_ed=eq_ed, bt_vac_correction=bt_vac_correction)
        plasma_dict["eq_data"] = []
        for time in times:
            plasma_dict["eq_data"].append(EQ_obj.GetSlice(time))
        make_plasma_mat(filename, plasma_dict)

def make_ECRadScenario_from_TB_input(shot, time, path, mat_out_name):
    plasma_dict = {}
    plasma_dict["shot"] = shot
    plasma_dict["time"] = np.array([time])
    topfile_dict = make_mdict_from_TB_files(os.path.join(path, "topfile"), True)
    EQObj = EQDataExt(shot)
    EQObj.load_slices_from_mat(plasma_dict["time"], topfile_dict, eq_prefix=False)
    vessel_bd = np.loadtxt(os.path.join(path, "vessel_bd"), skiprows=1)
    plasma_dict["vessel_bd"] = []
    plasma_dict["vessel_bd"].append(vessel_bd.T[0])
    plasma_dict["vessel_bd"].append(vessel_bd.T[1])
    plasma_dict["vessel_bd"] = np.array(plasma_dict["vessel_bd"])
    plasma_dict["rhop_prof"], plasma_dict["Te"] = np.loadtxt(os.path.join(path, "Te.dat"), skiprows=1, unpack=True)
    rhop_temp, plasma_dict["ne"]= np.loadtxt(os.path.join(path, "ne.dat"), skiprows=1, unpack=True)
    interpolate = False
    if(len(rhop_temp) != len(plasma_dict["rhop_prof"])):
        interpolate=True
    elif(any(rhop_temp != plasma_dict["rhop_prof"])):
        interpolate=True
    if(interpolate):
        ne_spl = InterpolatedUnivariateSpline(rhop_temp, plasma_dict["ne"], k=1)
        plasma_dict["ne"] = ne_spl(plasma_dict["rhop_prof"])
    plasma_dict["ne"] *= 1.e19
    plasma_dict["Te"] *= 1.e3
    plasma_dict["eq_data"] = [EQObj.GetSlice(time)]
    make_plasma_mat(os.path.join(path, mat_out_name), plasma_dict)

def make_plasma_mat(filename, plasma_dict):
    mdict = {}
    for key in plasma_dict.keys():
        if(key !="eq_data"):
            mdict[key] = plasma_dict[key]
    mdict["Psi_sep"] = []
    mdict["Psi_ax"] = []
    mdict["Psi"] = []
    mdict["Br"] = []
    mdict["Bt"] = []
    mdict["Bz"] = []
    R_init = False
    for itime, time in enumerate(plasma_dict["time"]):
        EQ_t = plasma_dict["eq_data"][itime]
        if(not R_init):
            R_init = True
            mdict["R"] = EQ_t.R
            mdict["z"] = EQ_t.z
        mdict["Psi_sep"].append(EQ_t.Psi_sep)
        mdict["Psi_ax"].append(EQ_t.Psi_ax)
        mdict["Psi"].append(EQ_t.Psi)
        mdict["Br"].append(EQ_t.Br)
        mdict["Bt"].append(EQ_t.Bt)
        mdict["Bz"].append(EQ_t.Bz)
    mdict["Psi_sep"] = np.array(mdict["Psi_sep"])
    mdict["Psi_ax"] = np.array(mdict["Psi_ax"])
    mdict["Psi"] = np.array(mdict["Psi"])
    mdict["Br"] = np.array(mdict["Br"])
    mdict["Bt"] = np.array(mdict["Bt"])
    mdict["Bz"] = np.array(mdict["Bz"])
    savemat(filename, mdict, appendmat=False)
    
if (__name__ == "__main__"):
    make_ECRadScenario_from_TB_input(178512, 2.200,"/afs/ipp/u/sdenk/Documentation/Data/DIII-D_TB", "DIIID_input_test.mat")
    
    