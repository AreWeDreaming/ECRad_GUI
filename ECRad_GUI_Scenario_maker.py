'''
Created on Jul 3, 2019

@author: sdenk
'''
#Module independent of the main GUI which allows the user to easily create ECRad Scenarios from external data
import os
import sys
from glob import glob
library_list = glob("../*pylib") + glob("../*Pylib")
found_lib = False
ECRadPylibFolder = None
for folder in library_list:
    if("ECRad" in folder or "ecrad"in folder ):
        sys.path.append(folder)
        found_lib = True
        ECRadPylibFolder = folder
        break
if(not found_lib):
    print("Could not find pylib")
    print("Important: ECRad_GUI must be launched with its home directory as the current working directory")
    print("Additionally, the ECRad_Pylib must be in the parent directory of the GUI and must contain one of ECRad, ecrad and Pylib or pylib")
    exit(-1)
from GlobalSettings import globalsettings
from equilibrium_utils import EQDataSlice, special_points, EQDataExt
from TB_communication import make_mdict_from_TB_files
import numpy as np
from scipy.io import savemat
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
    
def make_launch_mat(filename, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X):
    mdict = {}
    mdict["launch_f"] = np.array([f])
    mdict["launch_df"] = np.array([df])
    mdict["launch_R"] = np.array([R])
    mdict["launch_phi"] = np.array([phi])
    mdict["launch_z"] = np.array([z])
    mdict["launch_pol_ang"] = np.array([theta_pol])
    mdict["launch_tor_ang"] = np.array([phi_tor])
    mdict["launch_dist_focus"] = np.array([dist_focus])
    mdict["launch_width"] = np.array([width])
    mdict["launch_pol_coeff_X"] = np.array([pol_coeff_X])
    savemat(filename, mdict, appendmat=False)

def make_test_launch(filename):
    f = np.array([110.e9, 130.e9])
    df = np.array([0.2e9, 0.2e9])
    R = np.array([3.9, 3.9])
    phi = np.array([1, 1]) # degree
    z = np.array([0.1, 0.1])
    theta_pol = np.array([7, 7])
    phi_tor = np.array([2, 2])
    dist_focus = np.array([2.3, 2.3])
    width = np.array([0.2, 0.2])
    pol_coeff_X = np.array([-1, -1])
    make_launch_mat(filename, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X)
    
if (__name__ == "__main__"):
    make_test_launch("/afs/ipp/u/sdenk/public/DIII-D_TB/test_launch.mat")
#     make_ECRadScenario_from_TB_input(178512, 2.200,"/afs/ipp/u/sdenk/Documentation/Data/DIII-D_TB", "DIIID_input_test.mat")
    
    