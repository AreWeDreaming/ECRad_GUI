from ecrad_pylib.ECRad_Results import ECRadResults
import numpy as np
import os

def package_resonance_positions(ecrad_result_filename, target_folder):
    Results = ECRadResults()
    Results.from_netcdf(ecrad_result_filename)
    np.savetxt(os.path.join(target_folder,"R_res_.txt"), Results["resonance"]["R_cold"][...,0,:])
    np.savetxt(os.path.join(target_folder,"z_res.txt"), Results["resonance"]["z_cold"][...,0,:])
    np.savetxt(os.path.join(target_folder,"R_res_warm.txt"), Results["resonance"]["R_warm"][...,0,:])
    np.savetxt(os.path.join(target_folder,"z_res_warm.txt"), Results["resonance"]["z_warm"][...,0,:])
    np.savetxt(os.path.join(target_folder,"time.txt"), Results.Scenario["time"])
    np.savetxt(os.path.join(target_folder,"f.txt"), Results.Scenario["diagnostic"]["f"][0])
    np.savetxt(os.path.join(target_folder,"z_launch.txt"), Results.Scenario["diagnostic"]["z"][0])

    
if __name__ == "__main__":
    package_resonance_positions("/home/denks/ECRad/ECRad_00000_EXT_ed2.nc","/home/denks/ECRad/extracted_v2/")
