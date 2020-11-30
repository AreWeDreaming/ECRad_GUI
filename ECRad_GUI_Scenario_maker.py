'''
Created on Jul 3, 2019

@author: sdenk
'''
#Module independent of the main GUI which allows the user to easily create ECRad Scenarios from external data
import os
import sys
import numpy as np
from scipy.io import savemat
from glob import glob
from ECRad_Scenario import ECRadScenario
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
from Global_Settings import globalsettings
from Basic_Methods.Equilibrium_Utils import EQDataExt, EQDataSlice
from TB_Communication import make_mdict_from_TB_files

from scipy.interpolate import InterpolatedUnivariateSpline
from Diag_Types import EXT_diag

if(globalsettings.AUG):
    from Equilibrium_Utils_AUG import EQData
    from Shotfile_Handling_AUG import load_IDA_data
    
    
    
    def make_plasma_mat_for_testing(filename, shot, times, eq_exp, eq_diag, eq_ed, \
                                    bt_vac_correction=1.005, IDA_exp="AUGD", IDA_ed=0):
        plasma_dict = load_IDA_data(shot, timepoints=times, exp=IDA_exp, ed=IDA_ed)
        EQ_obj = EQData(shot, EQ_exp=eq_exp, EQ_diag=eq_diag, EQ_ed=eq_ed, bt_vac_correction=bt_vac_correction)
        plasma_dict["eq_data"] = []
        for time in times:
            plasma_dict["eq_data"].append(EQ_obj.GetSlice(time))
        make_plasma_mat(filename, plasma_dict)
   
def make_plasma_mat_from_variables_2D(mat_out_name, shot, time, R, z, Te, ne, Br, Bt, Bz, rhop, vessel_data=None, vessel_bd_file=None):
    # Vessel data has to be a ndarray of points (shape = (n,2)) with R,z points of the machine wall
    # Alternatively a standard ECRad vessel file can be used like ASDEX_Upgrade_vessel.txt
    plasma_dict = {}
    plasma_dict["shot"] = shot
    plasma_dict["time"] = np.array([time])
    plasma_dict["prof_reference"] = "2D"
    plasma_dict["rhop_prof"] = None
    # N2D [m^{-3}]
    plasma_dict["ne"] = ne
    # T2D [eV]
    plasma_dict["Te"] = Te
    #R = self.omfit_eq['AuxQuantities']['R']
    #z = self.omfit_eq['AuxQuantities']['Z']
    #rhop = self.omfit_eq['AuxQuantities']["RHOpRZ"].T
    #Br = self.omfit_eq['AuxQuantities']["Br"].T
    #Bt = self.omfit_eq['AuxQuantities']["Bt"].T
    #Bz = self.omfit_eq['AuxQuantities']["Bz"].T
    #vessel_data = np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T
    plasma_dict["eq_data"] = [EQDataSlice(time, R, z, rhop**2, Br, Bt, Bz, rhop, Psi_ax=0.0, Psi_sep=1.0)]
    if(vessel_data is not None):
        plasma_dict["vessel_bd"] = np.array(vessel_data).T
    elif(vessel_bd_file is not None):
        vessel_bd = np.loadtxt(vessel_bd_file, skiprows=1)
        plasma_dict["vessel_bd"] = []
        plasma_dict["vessel_bd"].append(vessel_bd.T[0])
        plasma_dict["vessel_bd"].append(vessel_bd.T[1])
        plasma_dict["vessel_bd"] = np.array(plasma_dict["vessel_bd"])
    else:
        raise ValueError("vessel_data and vessel_bd_file cannot both be None")
    make_plasma_mat(mat_out_name, plasma_dict)
        
def make_plasma_mat_from_variables(mat_out_name, shot, time, rhop_profiles, Te, ne, R, z, Br, Bt, Bz, rhop, vessel_data=None, vessel_bd_file=None):
    # Vessel data has to be a ndarray of points (shape = (n,2)) with R,z points of the machine wall
    # Alternatively a standard ECRad vessel file can be used like ASDEX_Upgrade_vessel.txt
    plasma_dict = {}
    plasma_dict["shot"] = shot
    plasma_dict["time"] = np.array([time])
    plasma_dict["prof_reference"] = "rhop_prof"
    plasma_dict["rhop_prof"] = rhop_profiles
    plasma_dict["ne"] = ne
    plasma_dict["Te"] = Te
    plasma_dict["eq_data"] = [EQDataSlice(time, R, z, rhop**2, Br, Bt, Bz, Psi_ax=0.0, Psi_sep=0.0, rhop=rhop)]
    if(vessel_data is not None):
        plasma_dict["vessel_bd"] = np.array(vessel_data).T
    elif(vessel_bd_file is not None):
        vessel_bd = np.loadtxt(vessel_bd_file, skiprows=1)
        plasma_dict["vessel_bd"] = []
        plasma_dict["vessel_bd"].append(vessel_bd.T[0])
        plasma_dict["vessel_bd"].append(vessel_bd.T[1])
        plasma_dict["vessel_bd"] = np.array(plasma_dict["vessel_bd"])
    else:
        raise ValueError("vessel_data and vessel_bd_file cannot both be None")
    make_plasma_mat(mat_out_name, plasma_dict)

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
    plasma_dict["prof_reference"] = "rhop_prof"
    make_plasma_mat(os.path.join(path, mat_out_name), plasma_dict)
    
def make_ECRadScenario_for_DIII_D(mat_out_name, shot, time, eqdsk_file, derived_file=None, ped_prof=None):
    from omfit.classes.omfit_eqdsk import OMFITeqdsk
    from Profile_Utils import make_profile
    from netCDF4 import Dataset
    profile = make_profile(derived = derived_file, ped_prof = ped_prof, time = time)
    omfit_eq = OMFITeqdsk(eqdsk_file)
    plasma_dict = {}
    plasma_dict["shot"] = shot
    rhop = np.sqrt(profile.axes["T_e"])
    ne = profile.profs["n_e"]
    Te = profile.profs["T_e"]
    np.savetxt("vessel_bd", np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T, fmt='% 1.12E')
    make_plasma_mat_from_variables(mat_out_name, shot, time, rhop, Te, ne, \
                                   omfit_eq['AuxQuantities']["R"], \
                                   omfit_eq['AuxQuantities']["Z"], \
                                   omfit_eq['AuxQuantities']["Br"].T, \
                                   omfit_eq['AuxQuantities']["Bt"].T ,\
                                   omfit_eq['AuxQuantities']["Bz"].T ,\
                                   omfit_eq['AuxQuantities']["RHOpRZ"].T,\
                                   vessel_data=np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T)


def make_plasma_mat(filename, plasma_dict):
    mdict = {}
    for key in plasma_dict:
        if(key !="eq_data"):
            mdict[key] = plasma_dict[key]
    mdict["Psi_sep"] = []
    mdict["Psi_ax"] = []
    mdict["Psi"] = []
    mdict["Br"] = []
    mdict["Bt"] = []
    mdict["Bz"] = []
    R_init = False
    for itime in range(len((plasma_dict["time"]))):
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
    
def make_launch_mat_single_timepoint(filename, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X):
    # 1D
    # arrays, with length number of channels
    #R = R_focus + 1.0
    #z = 0.0
    #dist_focus = R_focus - R
    # theta_pol = 0
    # phi_tor = 0.2
    # pol_coeff_X = -1.0
    # df = 0.5e9
    # width = 1.e-1 # see wikipedia, but we do not need it now. Figure out if you use it
    mdict = {}
    mdict["launch_f"] = np.array([f])
    mdict["launch_df"] = np.array([df])
    mdict["launch_R"] = np.array([R])
    mdict["launch_phi"] = np.array([phi])
    mdict["launch_z"] = np.array([z])
    mdict["launch_pol_ang"] = np.array([theta_pol])
    mdict["launch_tor_ang"] = np.array([phi_tor])
    mdict["launch_dist_focus"] = np.array([dist_focus])
    mdict["launch_width"] = np.array([width]) # see wikipedia, but we do not need it now
    mdict["launch_pol_coeff_X"] = np.array([pol_coeff_X])
    savemat(filename, mdict, appendmat=False)
    
def make_launch_from_ray_launch(filename_in, filename_out):
    launch = np.loadtxt(filename_in, skiprows=1)
    f = launch.T[0]
    df = launch.T[1]
    R = launch.T[2]
    phi = launch.T[3] # degree
    z = launch.T[4]
    theta_pol = launch.T[6]
    phi_tor = launch.T[5]
    dist_focus = launch.T[8]
    width = launch.T[7]
    pol_coeff_X = launch.T[9]
    make_launch_mat_single_timepoint(filename_out, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X)

def make_W7X_Scenario(ScenarioName, shot, time, folder, \
                      ray_launch_file, wall_filename, ECE_freqs=None, B_scale=1.0):
    Scenario = ECRadScenario(noLoad=True)
    profs = np.loadtxt(os.path.join(folder, "plasma_profiles.txt"), skiprows=3)
    if(len(profs.T[0]) > 40):
        Scenario.plasma_dict["rhot_prof"] = [profs.T[0]]
        Scenario.plasma_dict["Te"] = [profs.T[2] * 1.e3]
        Scenario.plasma_dict["ne"] = [profs.T[1]]
    else:
        rho = np.linspace(profs.T[0][0], profs.T[0][-1], 200)
        profs.T[1][profs.T[1] <= 0.0] = 20.e-3 # room temperature
        profs.T[2][profs.T[2] <= 0.0] = 1.e17 # arbitray
        Te_spl = InterpolatedUnivariateSpline(profs.T[0], np.log(profs.T[1]))
        ne_spl = InterpolatedUnivariateSpline(profs.T[0], np.log(profs.T[2]))
        Scenario.plasma_dict["rhot_prof"] = [rho]
        Scenario.plasma_dict["Te"] = [np.exp(Te_spl(rho)) * 1.e3]
        Scenario.plasma_dict["ne"] = [np.exp(ne_spl(rho)) * 1.e20]
    Scenario.shot = shot
    Scenario.IDA_exp = "W7X"
    Scenario.IDA_ed = -1
    Scenario.EQ_diag = "VMEC"
    Scenario.EQ_exp = "W7X"
    Scenario.EQ_ed = -1
    Scenario.plasma_dict["time"] = [time]
    Scenario.use3Dscen.used = True
    Scenario.use3Dscen.equilibrium_file = os.path.join(folder, "VMEC.txt")
    Scenario.use3Dscen.equilibrium_type = "VMEC"
    Scenario.use3Dscen.vessel_filename = wall_filename
    Scenario.use3Dscen.B_ref = B_scale
    if(not ScenarioName.endswith(".mat")):
        ScenarioName = ScenarioName + ".mat"
    ext_diag = EXT_diag("EXT")
    ext_diag.set_from_mat(ray_launch_file)
    if(ECE_freqs is not None):
        ext_diag.f = np.loadtxt(ECE_freqs, skiprows=1).T[2] * 1.e9 #skiprows=12
        ext_diag.N_ch = len(ext_diag.f)
        for key in ["df", "R", "phi", "z", "theta_pol", "phi_tor", \
                      "dist_focus", "width", "pol_coeff_X"]:
            temp_val = np.zeros(ext_diag.N_ch)
            temp_val[:] =  getattr(ext_diag, key)[0]
            setattr(ext_diag, key, temp_val)
    ext_diag.theta_pol[:] = 6.4913006098335915 # Launch params for W7X ECE
    ext_diag.phi_tor[:] = 9.828001340036531# # Launch params for W7X ECE
    Scenario.avail_diags_dict.update({"EXT":  ext_diag})
    Scenario.used_diags_dict.update({"EXT":  ext_diag})
    Scenario.ray_launch = []
    Scenario.ray_launch.append(ext_diag.get_launch())
    Scenario.use3Dscen.used = True
    Scenario.data_source = "Ext"
    Scenario.to_mat_file(ScenarioName)
    

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
    make_launch_mat_single_timepoint(filename, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X)
    
if (__name__ == "__main__"):
    make_launch_from_ray_launch("/afs/ipp-garching.mpg.de/home/s/sdenk/Documents/CECE_ray_launch.txt", "/afs/ipp-garching.mpg.de/home/s/sdenk/Documents/CECE_launch.mat")
#     make_ECRadScenario_for_DIII_D("170325.mat", 170325, time=3850, \
#                                   eqdsk_file="/mnt/c/Users/Severin/Scenarios/170325_3_850/g170325.3_850_20", \
#                                   ped_prof=["profdb_ped", 170325, "t1042"])
#     make_W7X_Scenario("/tokp/work/sdenk/ECRad/20181009043_michelson_tor", 20181009043, 2.15, "/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/example/plasma_profiles.txt", \
#                       "/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/example/oliford-20181009.043-t_2.150s-fi_0_0.050.txt", "VMEC", "/tokp/work/sdenk/ECRad/W7_X_ECE_launch.mat", \
#                       "/tokp/work/sdenk/ECRad/W7X_wall_SI.dat", "/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/freq_michelson")
#     make_W7X_Scenario("/tokp/work/sdenk/ECRad/20181009043002_5_00_mich", 20181009043002, 5.00, "/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/Travis_ECRad_Benchmark/20181009.043.002_5_00s_Mich", \
#                       "/tokp/work/sdenk/ECRad/W7_X_ECE_launch.mat", \
#                       "/tokp/work/sdenk/ECRad/W7X_wall_SI.dat", \
#                       B_scale = 0.9391666666666667, \
#                       ECE_freqs="/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/Travis_ECRad_Benchmark/20181009.043.002_5_00s_Mich/results_0/ECE_spectrum_parsed")#, ECE_freqs="/afs/ipp-garching.mpg.de/home/s/sdenk/Documentation/Data/W7X_stuff/freq_michelson")
#     make_W7X_Scenario("/tokp/work/sdenk/ECRad/AUG_32934", 32934, 3.298, "/tokp/work/sdenk/ECRad/32934_3298_plasma_profiles.txt", \
#                       "/tokp/work/sdenk/ECRad/g32934_03298", "EFIT", "/tokp/work/sdenk/ECRad/ECRad_32934_ECE_ed5.mat", "/tokp/work/sdenk/ECRad/AUG_pseudo_3D_wall.dat")
#     make_launch_from_ray_launch("/tokp/work/sdenk/ECRad/ray_launch_W7_X.dat","/tokp/work/sdenk/ECRad/W7_X_ECE_launch.mat")
#     make_test_launch("/afs/ipp/u/sdenk/public/DIII-D_TB/test_launch.mat")
#     make_ECRadScenario_from_TB_input(178512, 2.200,"/afs/ipp/u/sdenk/Documentation/Data/DIII-D_TB", "DIIID_input_test.mat")
    
    