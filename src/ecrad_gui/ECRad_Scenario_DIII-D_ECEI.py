'''
Created on Oct 9, 2020

@author: denk
'''
import numpy as np
from scipy.io import savemat
class EQDataSlice:
    def __init__(self, time, R, z, Psi, Br, Bt, Bz, special=None, Psi_ax = None, Psi_sep=None, rhop=None, ripple=None):
        self.time = time
        self.R = R
        self.z = z
        self.Psi = Psi
        if(len(Psi.T[0]) != len(R) or len(Psi[0]) != len(z)):
            print("Shapes ", Psi.shape, R.shape, z.shape)
        self.rhop = rhop
        self.Br = Br
        self.Bt = Bt
        self.Bz = Bz
        if(special is not None):
            self.R_ax = special.Raxis
            self.z_ax = special.zaxis
            self.R_sep = special.Rspx
            self.z_sep = special.zspx
            self.Psi_ax = special.psiaxis
            self.Psi_sep = special.psispx
        elif(Psi_sep is not None and Psi_ax is not None):
            self.Psi_ax = Psi_ax
            self.Psi_sep = Psi_sep
        else:
            raise ValueError("Either special points or Psi_ax and Psi_sep must not be None")
        self.special = np.array([self.Psi_ax, self.Psi_sep])
        self.ripple = ripple


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
    plasma_dict["eq_data"] = [EQDataSlice(time, R, z, rhop**2, Br, Bt, Bz, rhop=rhop, Psi_ax=0.0, Psi_sep=1.0)]
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
    
    
def make_ECRadScenario_for_DIII_D(mat_out_name, shot, time, eqdsk_file, derived_file=None, ped_prof=None):
    from omfit.classes.omfit_eqdsk import OMFITeqdsk
    from netCDF4 import Dataset
    omfit_eq = OMFITeqdsk(eqdsk_file)
    plasma_dict = {}
    plasma_dict["shot"] = shot
    derived = Dataset(derived_file)
    itime = np.argmin(time - np.asarray(derived['time']))
    if(np.asarray(derived['psi_n']).ndim == 2):
        rhop = np.sqrt(np.asarray(derived.variables["psi_n"])[itime])
    else:
        rhop = np.sqrt(np.asarray(derived.variables["psi_n"]))
    Te = np.asarray(derived.variables["T_e"])[itime]
    ne = np.asarray(derived.variables["n_e"])[itime]
    make_plasma_mat_from_variables(mat_out_name, shot, time, rhop, Te, ne, \
                                   omfit_eq['AuxQuantities']["R"], \
                                   omfit_eq['AuxQuantities']["Z"], \
                                   omfit_eq['AuxQuantities']["Br"].T, \
                                   omfit_eq['AuxQuantities']["Bt"].T ,\
                                   omfit_eq['AuxQuantities']["Bz"].T ,\
                                   omfit_eq['AuxQuantities']["RHOpRZ"].T,\
                                   vessel_data=np.array([omfit_eq["RLIM"], omfit_eq["ZLIM"]]).T)
    
      
