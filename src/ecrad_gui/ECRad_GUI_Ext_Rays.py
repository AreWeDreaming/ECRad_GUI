'''
Created on May 29, 2020

@author: denk
'''
from ecrad_pylib.ECRad_Results import ECRadResults

def manipiulate_rays(result_file_in, result_file_out):
    res = ECRadResults()
    res.from_mat_file(result_file_in)
    for index in range(len(res.time)):
        for ich in range(len(res.Scenario.ray_launch[index]["f"])):
            for mode in res.modes:
                if(res.Config["Physics"]["N_ray"] > 1):
                    for iray in range(len(res.ray["s" + mode][index][ich])):
                        res.ray["Te" + mode][index][ich][iray][:] /= 2.0
                else:
                    res.ray["Te" + mode][index][ich][:] /= 2.0
    res.to_mat_file(result_file_out)
    
if(__name__ == "__main__"):
    manipiulate_rays("/mnt/c/Users/Severin/ECRad/ECRad_37472_EXT_ed2.mat", "/mnt/c/Users/Severin/ECRad/ECRad_37472_EXT_ed2_half_Te.mat")