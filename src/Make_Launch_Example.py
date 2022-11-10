'''
Created on Oct 7, 2020

@author: denk
'''
from scipy.io import savemat
import numpy as np
    
def make_launch_mat(filename, f, df, R, phi, z, theta_pol, phi_tor, dist_focus, width, pol_coeff_X):
    # All of the input quantities should be a function of the channel number
    mdict = {}
    # Frequency in GHz
    mdict["launch_f"] = np.array([f])
    # IF bandwidth
    mdict["launch_df"] = np.array([df])
    # R position of the launch point. Has to be outside of separatrix
    mdict["launch_R"] = np.array([R])
    # Phi position of the launch point. Has to be outside of separatrix
    # Not important for the moment since I do not have anything for the Bt ripple of DIII-D
    mdict["launch_phi"] = np.array([phi])
    # z position of the launch point. Has to be outside of separatrix
    mdict["launch_z"] = np.array([z])
    # Angle between a perfectly horizontal line and the diagnostic LOS
    # Negative for upwards, posiitive for downwards
    mdict["launch_pol_ang"] = np.array([theta_pol])
    # Angle between a line pointing to the center of the torus and the diagnostic LOS
    # Negative for clockwards, positive for counterclockwards
    # Sign not matter for thermal plasmas in the absence of magnetic field ripple 
    mdict["launch_tor_ang"] = np.array([phi_tor])
    # The quantities below are optional for the moment
    # Distance btween the origin of the ray (R,phi,z) and the focus point
    mdict["launch_dist_focus"] = np.array([dist_focus])
    # Width of the volume of sight at R, phi,z
    mdict["launch_width"] = np.array([width])
    # X mode fraction measured by the diagnostic
    # Set -1 for a horizontally aligned polarization filter.
    mdict["launch_pol_coeff_X"] = np.array([pol_coeff_X])
    savemat(filename, mdict, appendmat=False)
    