'''
Created on Jul 3, 2019

@author: Severin Denk
'''
#Module independent of the main GUI which allows the user to easily create ECRad Scenarios from external data
import os
import sys
print(sys.path)
import numpy as np
from scipy.io import savemat
import scipy.constants as cnst
from ecrad_pylib.Distribution_Classes import Distribution
from ecrad_pylib.Global_Settings import globalsettings
from ecrad_pylib.ECRad_Scenario import ECRadScenario
from ecrad_pylib.Equilibrium_Utils import EQDataExt, EQDataSlice
from plasma_math_tools.geometry_utils import get_theta_pol_phi_tor_from_two_points
from ecrad_pylib.TB_Communication import make_mdict_from_TB_files

from scipy.interpolate import griddata, RectBivariateSpline, InterpolatedUnivariateSpline
from ecrad_pylib.Diag_Types import EXT_diag
from ecrad_pylib.ECRad_Interface import load_plasma_from_mat
from netCDF4 import Dataset

if(globalsettings.AUG):
    from ecrad_pylib.Equilibrium_Utils_AUG import EQData
    from ecrad_pylib.Shotfile_Handling_AUG import load_IDA_data
    
def make_netcdf_plasma(filename, plasma):
    rootgrp = Dataset(filename, "w", format="NETCDF4")
    rootgrp.createGroup("Plasma")
    rootgrp["Plasma"].createDimension('str_dim', 1)
    N_time = len(plasma["time"])
    rootgrp["Plasma"].createDimension("N_time", N_time)
    if(plasma["eq_dim"] == 2):
        example_slice = plasma["eq_data_2D"].GetSlice(0)
        rootgrp["Plasma"].createDimension("N_eq_2D_R", len(example_slice.R))
        rootgrp["Plasma"].createDimension("N_eq_2D_z", len(example_slice.z))
        rootgrp["Plasma"].createDimension("N_vessel_bd", len(plasma['vessel_bd'][...,0]))
        rootgrp["Plasma"].createDimension("N_vessel_dim", 2)
    if(not plasma["2D_prof"]):
        rootgrp["Plasma"].createDimension("N_profiles", len(plasma["Te"][0]))
    var = rootgrp["Plasma"].createVariable("2D_prof", "b")
    var[...] = int(plasma["2D_prof"])
    var = rootgrp["Plasma"].createVariable("time", "f8", ("N_time",))
    var[...] = plasma["time"]
    var = rootgrp["Plasma"].createVariable("shot", "i8")
    var[...] = plasma["shot"]
    for sub_key in ["Te", "ne"]:
        if(not plasma["2D_prof"]):
            var = rootgrp["Plasma"].createVariable(sub_key, \
                                                        "f8", ("N_time", "N_profiles"))
        else:
            var = rootgrp["Plasma"].createVariable(sub_key, "f8", \
                                                        ("N_time", "N_eq_2D_R", "N_eq_2D_z"))
        var[:] = plasma[sub_key]
    if(not plasma["2D_prof"]):
        var = rootgrp["Plasma"].createVariable("prof_reference", str, ('str_dim',))
        var[0] = plasma["prof_reference"]
        sub_key = plasma["prof_reference"]
        var = rootgrp["Plasma"].createVariable(sub_key, "f8", \
                                                    ("N_time", "N_profiles"))
        var[:] = plasma[sub_key]
    var = rootgrp["Plasma"].createVariable("eq_dim", "i8")
    var[...] = plasma["eq_dim"]
    if(plasma["eq_dim"] == 3):
        for sub_key in ["B_ref", "s_plus", "s_max", \
                        "interpolation_acc", "fourier_coeff_trunc", \
                        "h_mesh", "delta_phi_mesh"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_3D" + "_" +  sub_key, "f8")
            var[...] = plasma["eq_data_3D"][sub_key]
        for sub_key in ["use_mesh", "use_symmetry"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_3D" + "_" +  sub_key, "b")
            var[...] = plasma["eq_data_3D"][sub_key]
        for sub_key in ["equilibrium_type", "vessel_filename"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_3D" + "_" +  sub_key, str, ('str_dim',))
            var[0] = plasma["eq_data_3D"][sub_key]
        var = rootgrp["Plasma"].createVariable(\
                                                    "eq_data_3D" + "_" + \
                                                    "equilibrium_files", str, ('N_time',))
        var[:] = plasma["eq_data_3D"]["equilibrium_files"]
    else:
        for sub_key in ["R", "z"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_2D" + "_" +  sub_key, "f8", \
                                                        ("N_time", "N_eq_2D_" + sub_key))
            var[:] = plasma['eq_data_2D'].get_single_attribute_from_all_slices(sub_key)
        for sub_key in ["Psi", "rhop", "Br", "Bt", "Bz"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_2D" + "_" +  sub_key, "f8", \
                                                        ("N_time", "N_eq_2D_R", "N_eq_2D_z"))
            var[:] = plasma['eq_data_2D'].get_single_attribute_from_all_slices(sub_key)
        for sub_key in ["R_ax", "z_ax", "Psi_ax", "Psi_sep"]:
            var = rootgrp["Plasma"].createVariable(\
                                                        "eq_data_2D" + "_" +  sub_key, "f8", \
                                                        ("N_time",))
            var[:] = plasma['eq_data_2D'].get_single_attribute_from_all_slices(sub_key)
        var = rootgrp["Plasma"].createVariable("vessel_bd", "f8", \
                                               ("N_vessel_bd", "N_vessel_dim"))
        var[...,0] = plasma['vessel_bd'][...,0]
        var[...,1] = plasma['vessel_bd'][...,1]
    rootgrp.close()

def make_netcdf_launch(filename, launch):
    rootgrp = Dataset(filename, "w", format="NETCDF4")
    rootgrp.createGroup("Diagnostic")
    N_time = len(launch["f"])
    rootgrp["Diagnostic"].createDimension("N_time", N_time)
    N_ch = len(launch["f"][0])
    rootgrp["Diagnostic"].createDimension("N_ch", N_ch)
    for sub_key in launch.keys():
        if(sub_key == "diag_name"):
            var = rootgrp["Diagnostic"].createVariable("diagnostic_" +  sub_key, str, \
                                                       ("N_time","N_ch"))
            var[:] = launch[sub_key]
        else:
            var = rootgrp["Diagnostic"].createVariable("diagnostic_" +  sub_key, "f8", \
                                                       ("N_time","N_ch"))
            var[:] = launch[sub_key]
    rootgrp.close()

def make_plasma_from_variables(filename, shot, times, rhop_profiles, Te, 
            ne, R, z, Br, Bt, Bz, rhop, vessel_data=None, vessel_bd_file=None):
    # Vessel data has to be a ndarray of points (shape = (n,2)) with R,z points of the machine wall
    # Alternatively a standard ECRad vessel file can be used like ASDEX_Upgrade_vessel.txt
    # rhop_profiles can be none for 2D profiles
    plasma_dict = {}
    plasma_dict["shot"] = shot
    plasma_dict["time"] = np.array(times)
    plasma_dict["prof_reference"] = "rhop_prof"
    plasma_dict["eq_dim"] = 2
    plasma_dict["2D_prof"] = len(Te[0].shape) == 2
    if(not plasma_dict["2D_prof"]):
        plasma_dict["prof_reference"] = "rhop_prof"
        plasma_dict["rhop_prof"] = np.array([rhop_profiles])
    else:
        plasma_dict["prof_reference"] = "2D"
        plasma_dict["rhop_prof"] = None
    plasma_dict["ne"] = ne
    plasma_dict["Te"] = Te
    EQObj = EQDataExt(Ext_data=True)
    slices = []
    for index, time in enumerate(times):
        slices.append(EQDataSlice(time, R[index], z[index], rhop[index]**2, Br[index], Bt[index], Bz[index], \
                                  Psi_ax=0.0, Psi_sep=1.0, rhop=rhop[index]))
    EQObj.insert_slices_from_ext(times, slices, False)
    plasma_dict["eq_data_2D"] = EQObj
    if(vessel_data is not None):
        plasma_dict["vessel_bd"] = np.array(vessel_data)
    elif(vessel_bd_file is not None):
        vessel_bd = np.loadtxt(vessel_bd_file, skiprows=1)
        plasma_dict["vessel_bd"] = []
        plasma_dict["vessel_bd"].append(vessel_bd.T[0])
        plasma_dict["vessel_bd"].append(vessel_bd.T[1])
        plasma_dict["vessel_bd"] = np.array(plasma_dict["vessel_bd"]).T
    else:
        raise ValueError("vessel_data and vessel_bd_file cannot both be None")
    make_netcdf_plasma(filename, plasma_dict)
    
def make_plasma_mat_for_testing(filename, shot, times, eq_exp, eq_diag, eq_ed, \
                                IDA_exp="AUGD", IDA_ed=0):
    plasma_dict = load_IDA_data(shot, timepoints=times, exp=IDA_exp, ed=IDA_ed)
    EQ_obj = EQData(shot, EQ_exp=eq_exp, EQ_diag=eq_diag, EQ_ed=eq_ed)
    plasma_dict["eq_data_2D"] = EQDataExt(Ext_data=True)
    for time in times:
        plasma_dict["eq_data_2D"].insert_slices_from_ext([time] , [EQ_obj.GetSlice(time)])
    make_plasma_mat(filename, plasma_dict)
        
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
    EQObj = EQDataExt(Ext_data=True)
    EQObj.insert_slices_from_ext(np.array([time]), \
                                 [EQDataSlice(time, R, z, rhop**2, Br, Bt, Bz, \
                                              Psi_ax=0.0, Psi_sep=01.0, rhop=rhop)], False)
    plasma_dict["eq_data_2D"] = EQObj
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
    EQObj = EQDataExt()
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
    plasma_dict["eq_data_2D"] = EQObj
    plasma_dict["prof_reference"] = "rhop_prof"
    make_plasma_mat(os.path.join(path, mat_out_name), plasma_dict)
    
def make_Plasma_for_DIII_D(filename, shot, time, eqdsk_file, derived_file=None, ped_prof=None):
    sys.path.append("../Pylicon")
    from omfit.omfit_classes.omfit_eqdsk import OMFITgeqdsk
    from Profile_Utils import make_profile
    profile = make_profile(derived = derived_file, ped_prof = ped_prof, \
                           touch_up={"rhop_cut": 1.04, "rhop_ant": 1.1, \
                           "n_ant": 1e+16, "T_ant": 0.001}, time = time* 1.e3, check_profiles=True)
    omfit_eq = OMFITgeqdsk(eqdsk_file)
    plasma_dict = {}
    plasma_dict["shot"] = shot
    rhop = profile.axes["T_e"]
    ne = profile.profs["n_e"]
    Te = profile.profs["T_e"]
    make_plasma_from_variables(filename, shot, [time], [rhop], [Te], [ne], \
                               [omfit_eq['AuxQuantities']["R"]], \
                               [omfit_eq['AuxQuantities']["Z"]], \
                               [omfit_eq['AuxQuantities']["Br"].T], \
                               [omfit_eq['AuxQuantities']["Bt"].T],\
                               [omfit_eq['AuxQuantities']["Bz"].T],\
                               [omfit_eq['AuxQuantities']["RHOpRZ"].T],\
                               vessel_data=np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T)

def make_DIII_D_launch_omas(launch_file, shot, time,  device='d3d'):
    import omas
    ods = omas.ODS()
    ods.open(device, shot)
    Scenario = ECRadScenario(noLoad=True)
    Scenario.set_up_launch_from_omas(ods, [time])
    make_netcdf_launch(launch_file, Scenario["diagnostic"])

def make_Plasma_for_SPARC(times, filename, Te_files, ne_files, eqdsk_files):
    from omfit.omfit_classes.omfit_eqdsk import OMFITgeqdsk
    # from Plotting_Configuration import plt
    keys = ["rhop", "Te", "ne", "R", "z", "Br", "Bt", "Bz", "RHOpRZ"]
    quants = {}
    for key in keys:
        quants[key] = []
    N_prof_pnts = None
    for Te_file, ne_file, eqdsk_file in zip(Te_files, ne_files, eqdsk_files):
        omfit_eq = OMFITgeqdsk(eqdsk_file)
        omfit_eq.addAuxQuantities()
        psi_Te, Te_scen = np.loadtxt(Te_file, skiprows=1, unpack=True)
        psi_ne, ne_scen = np.loadtxt(ne_file, skiprows=1, unpack=True)
        if(N_prof_pnts is None):
            N_prof_pnts = len(psi_Te)
        quants["rhop"].append(np.linspace(0.0, np.max(psi_Te), N_prof_pnts))
        Te_spl = InterpolatedUnivariateSpline(psi_Te, np.log(Te_scen))
        ne_spl = InterpolatedUnivariateSpline(psi_ne, np.log(ne_scen))
        quants["Te"].append(np.exp(Te_spl(quants["rhop"][-1]))*1.e3)
        quants["ne"].append(np.exp(ne_spl(quants["rhop"][-1]))*1.e20)
        for key in ["R", "z", "Br", "Bt", "Bz", "RHOpRZ"]:
            # Works also for R and z cause .T does not do anything
            quants[key].append(omfit_eq['AuxQuantities'][key].T)
    for key in keys:
        quants[key] = np.array(quants[key])
    make_plasma_from_variables(filename, 0, times, quants["rhop"], quants["Te"], quants["ne"],
                quants["R"], quants["z"], quants["Br"], quants["Bt"],
                quants["Bz"], quants["RHOpRZ"],
                vessel_data=np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]))

def create_launch_data_manually():
    f = np.array([90.5,89.9,89.3,88.7,88.1,87.5,86.9,86.3])*1.e9
    z = np.array([-0.158, -0.14136842, -0.12473684, -0.10810526, -0.09147368, -0.07484211,
                 -0.05821053, -0.04157895, -0.02494737, -0.00831579,  0.00831579,  0.02494737,
                 0.04157895,  0.05821053,  0.07484211,  0.09147368,  0.10810526,  0.12473684,
                 0.14136842,  0.158])
    f_mesh, z_mesh = np.meshgrid(f,z, indexing="ij")
    launch_data = np.zeros((f_mesh.size,7))
    launch_data.T[0] = f_mesh.flatten() # f [Hz]
    launch_data.T[1][:] = 2.5 # R first_point [m]
    launch_data.T[2][:] = 270 # Phi first_point [deg,]
    launch_data.T[3] = z_mesh.flatten() # z [m]
    launch_data.T[4][:] = 0.9 # R second_point
    launch_data.T[5][:] = 270 # phi second_point
    launch_data.T[6] = z_mesh.flatten() # z second point
    return launch_data

def make_Launch_from_freq_and_points(filename, launch_data=None, input_file=None):
    if input_file is not None:
        launch_data = np.loadtxt(input_file)
    launch = {}
    x1 = np.array(launch_data.T[1:4])
    x2 = np.array(launch_data.T[4:])
    x1_vec = np.array([
            x1[0] * np.cos(np.deg2rad(x1[1])),
            x1[0] * np.sin(np.deg2rad(x1[1])), 
            x1[2]])
    x2_vec = np.array([
            x2[0] * np.cos(np.deg2rad(x2[1])),
            x2[0] * np.sin(np.deg2rad(x2[1])), 
            x2[2]])
    launch["f"] = [launch_data.T[0]]
    launch["df"] = [launch_data.T[0] * 0.1]
    launch["R"] = [launch_data.T[1]]
    launch["phi"] = [launch_data.T[2]]
    launch["z"] = [launch_data.T[3]]
    theta_pol, phi_tor = get_theta_pol_phi_tor_from_two_points(x1_vec, x2_vec)
    launch["theta_pol"] = [theta_pol]
    launch["phi_tor"] = [phi_tor]
    launch["dist_focus"] = np.ones((1,len(launch["f"]))) * 99.0
    launch["width"] = np.ones((1,len(launch["f"]))) * 0.1
    launch["pol_coeff_X"] = np.ones((1,len(launch["f"]))) * -1
    launch["diag_name"] = np.zeros((1,len(launch["f"])), dtype="|S3")
    launch["diag_name"][0,:]= "EXT"
    
    # Phi is defined as the angle between the k_1 = -r_1 and k_2 = r_2 - r_1
    make_netcdf_launch(filename, launch)

def set_launch_in_Scenario(scenario_file_in, scenario_file_out, launch_dict):
    Scenario = ECRadScenario(noLoad=True)
    Scenario.load(scenario_file_in)
    for key in Scenario["diagnostic"]:
        Scenario["diagnostic"][key] = []
        for time in Scenario["time"]:
            Scenario["diagnostic"][key].append(launch_dict[key])
        Scenario["diagnostic"][key] = np.array(Scenario["diagnostic"][key])
    Scenario['diagnostic']["diag_name"] = np.array(Scenario["diagnostic"]["f"].shape, dtype="|S3")
    Scenario['diagnostic']["diag_name"][:] = "EXT"
    Scenario.to_netcdf(filename=scenario_file_out)

def make_DIIID_HFS_LHCD_Scenario(folder, Scenario_filename, Distribution_filename, plot=False):
    from omfit.omfit_classes.omfit_eqdsk import OMFITgeqdsk
    f = np.load(os.path.join(folder,"f.npy"))
    rho_f = np.load(os.path.join(folder,"rhosOfFluxSurfaces.npy"))
    pitch = np.load(os.path.join(folder,"pitchAngleMesh.npy"))[0]
    v = np.load(os.path.join(folder,"velocities.npy"))
    beta = v / cnst.c 
    gamma = 1.0 / np.sqrt(1.0 - beta**2)
    u = beta * gamma
    gamma_grid, pitch_grid = np.meshgrid(gamma, pitch, indexing="ij")
    for i_rho in range(f.shape[0]):
        f[i_rho] *= gamma_grid**5
    Te, ne, rho_prof = np.load(os.path.join(folder,"profiles.npy"))
    Te *= 1.e3
    ne *= 1.e19
    ne_spl = InterpolatedUnivariateSpline(rho_prof, np.log(ne/1.e19))
    ne_f = 1.e19*np.exp(ne_spl(rho_f))
    # f = (f.T / ne_f).T
    shot = 147634
    time = 4.525
    omfit_eq = OMFITgeqdsk(os.path.join(folder,"g147634.04525"))
    psi = np.linspace(omfit_eq["SIMAG"], omfit_eq["SIBRY"], len(omfit_eq["QPSI"]))
    rhop = np.sqrt((psi - omfit_eq["SIMAG"])/
                   (omfit_eq["SIBRY"] - omfit_eq["SIMAG"]))
    rhop_spl = InterpolatedUnivariateSpline(omfit_eq["RHOVN"], rhop)
    rhop_prof = rhop_spl(rho_prof)
    rhop_f = rhop_spl(rho_f)
    make_plasma_from_variables(Scenario_filename, shot, [time], [rhop_prof], [Te], [ne], \
                               [omfit_eq['AuxQuantities']["R"]], \
                               [omfit_eq['AuxQuantities']["Z"]], \
                               [omfit_eq['AuxQuantities']["Br"].T], \
                               [omfit_eq['AuxQuantities']["Bt"].T],\
                               [omfit_eq['AuxQuantities']["Bz"].T],\
                               [omfit_eq['AuxQuantities']["RHOpRZ"].T],\
                               vessel_data=np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T)
    dist_obj = Distribution()
    dist_obj.set(rho_f, rhop_f, u, pitch, f, rho_prof, rhop_prof, Te, ne)
    dist_obj.post_process()
    ne_inter = dist_obj.ne_init[dist_obj.rhop_1D_profs < 1.0]
    ne_inter[ne_inter < 1.e15] = 1.e15
    ne_spl = InterpolatedUnivariateSpline(dist_obj.rhop_1D_profs[dist_obj.rhop_1D_profs < 1.0], np.log(ne_inter))
    f = (f.T / (dist_obj.ne/np.exp(ne_spl(dist_obj.rhop)))).T
    dist_obj.set(rho_f, rhop_f, u, pitch, f, rho_prof, rhop_prof, Te, ne)
    dist_obj.post_process()
    dist_obj.to_netcdf(filename=Distribution_filename)
    if(plot):
        from Plotting_Configuration import plt
        dist_obj.plot_Te_ne()
        for rho in np.arange(0.1, 0.95, 0.15):
            plt.figure()
            dist_obj.plot(rhop=rho)
            plt.gca().set_xlim(0.0, 0.8)
            plt.gca().set_ylim(-0.8, 0.8)
        plt.show()
    
def put_JOREK_data_into_Scenario(filename, Scenario_filename, vessel_file):
    jorek_data = np.loadtxt(filename,unpack=True)
    R_0 = jorek_data[0]
    z_0 = jorek_data[1]
    scenario_grid_shape = ((400, 600))
    mesh_points = np.array([R_0, z_0]).T
    R_rect_grid = np.linspace(1.0, 2.4, scenario_grid_shape[0])
    z_rect_grid = np.linspace(-1.5, 1.5, scenario_grid_shape[1])
    R_mesh, z_mesh = np.meshgrid(R_rect_grid, z_rect_grid, indexing='ij')
    rect_grid = np.array([R_mesh.flatten(), z_mesh.flatten()]).T
    ne_grid = griddata(mesh_points, jorek_data[2], rect_grid, 
                       method="linear", fill_value=1.e16).reshape(scenario_grid_shape)
    Te_grid = griddata(mesh_points, jorek_data[3], rect_grid, \
                       method="linear", fill_value=2.e-2).reshape(scenario_grid_shape)
    Br_grid = griddata(mesh_points, jorek_data[4], rect_grid, \
                       method="linear", fill_value=0.0).reshape(scenario_grid_shape)
    Bz_grid = griddata(mesh_points, jorek_data[5], rect_grid, \
                      method="linear", fill_value=0.0).reshape(scenario_grid_shape)
    Bt_grid = griddata(mesh_points, jorek_data[6], rect_grid, \
                       method="linear", fill_value=0.0).reshape(scenario_grid_shape)
    psi_grid = griddata(mesh_points, jorek_data[7], rect_grid, \
                        method="linear", fill_value=0.0).reshape(scenario_grid_shape)
    rho_grid = griddata(mesh_points, jorek_data[8], rect_grid, \
                        method="linear", fill_value=1.5).reshape(scenario_grid_shape)
    # The rho grid has zeros as a fill value which will mess things up inside ECRad
    # Luckile PSI is increasing with increasing small radius and non-zero at the center so we can use Psi to mask rho
    rho_grid[psi_grid==0] = 1.5
    # i_z = np.argmin(np.abs(z_rect_grid))
    # for quant, range in zip([ne_grid/1.e19, Te_grid/1.e3, Br_grid, Bz_grid, Bt_grid, rho_grid], 
    #                         [[0,10],[0,5],[-0.5, 0.5],[-0.5,0.5],[-3,3],[0.0, 1.6]]):
    #     plt.figure()
    #     # plt.contourf(R_rect_grid, z_rect_grid, quant.T, levels = np.linspace(range[0], range[1], 15))
    #     plt.plot(R_rect_grid, quant[:,i_z])
    # plt.show()
    make_plasma_from_variables(Scenario_filename, 37632, [2.000], None, [Te_grid], [ne_grid], [R_rect_grid], [z_rect_grid],
                               [Br_grid], [Bt_grid], [Bz_grid], [rho_grid], vessel_bd_file=vessel_file)


def put_TRANSP_U_profiles_in_Scenario(Scenario, filename, time, scenario_name):
    from ufilelib import UFILELIB
    from ecrad_pyplib.Plotting_Configuration import plt
    u_file = UFILELIB()
    u_file.readfile(filename)
    it = np.argmin(np.abs(Scenario.plasma_dict["time"]-time))
    eq_slice = Scenario.plasma_dict["eq_data"][it]
    Scenario.plasma_dict["time"] = np.array([time])
    Scenario.plasma_dict["eq_data"] = [eq_slice]
    it_u_file = np.argmin(np.abs(u_file.ufdict["TE"]["Time"]))
    Scenario.plasma_dict["Te"] = [u_file.ufdict["TE"]["data"][it_u_file]]
    plt.plot(u_file.ufdict["TE"]["rho_tor"], u_file.ufdict["TE"]["data"][it_u_file]/1.e3)
    it_u_file = np.argmin(np.abs(u_file.ufdict["NE"]["Time"]))
    Scenario.plasma_dict["ne"] = [u_file.ufdict["NE"]["data"][it_u_file] * 1.e6]
    Scenario.plasma_dict["prof_reference"] = "rhot_prof"
    Scenario.plasma_dict["rhot_prof"] = u_file.ufdict["NE"]["rho_tor"]
    Scenario.to_mat_file(filename=scenario_name)
    plt.plot(u_file.ufdict["NE"]["rho_tor"], u_file.ufdict["NE"]["data"][it_u_file]/1.e13)
    plt.show()
    
    
def fix_ne_Te_in_plasma_mat(filename_in, filename_out):
    plasma_dict = load_plasma_from_mat(filename_in)
    # Cast to make sure we have floats not np objects
    plasma_dict["Te"] = np.array(plasma_dict["Te"], dtype=np.float64)
    plasma_dict["Te"][plasma_dict["Te"] < 2.e-2] = 2.e-2
    plasma_dict["ne"][plasma_dict["ne"] < 1.e14] = 1.e14
    make_plasma_mat(filename_out, plasma_dict)

def make_plasma_mat(filename, plasma_dict):
    mdict = {}
    for key in plasma_dict:
        if(key !="eq_data_2D"):
            mdict[key] = plasma_dict[key]
    mdict["Psi_sep"] = []
    mdict["Psi_ax"] = []
    mdict["Psi"] = []
    mdict["Br"] = []
    mdict["Bt"] = []
    mdict["Bz"] = []
    R_init = False
    for time in plasma_dict["time"]:
        EQ_t = plasma_dict["eq_data_2D"].GetSlice(time)
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
    

def scale_launch_parameter(Scenario_file_in, scenario_file_out, para_name, scale):
    Scenario = ECRadScenario(True)
    Scenario.load(filename=Scenario_file_in)
    Scenario["diagnostic"][para_name] *= scale
    Scenario.to_netcdf(filename=scenario_file_out)

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
    launch_data = create_launch_data_manually()
    make_Launch_from_freq_and_points("/home/denks/ECRad/ECEI_geo.nc", launch_data=launch_data)
    pass