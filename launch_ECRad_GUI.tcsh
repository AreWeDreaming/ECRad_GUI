#!/usr/bin/tcsh

source ../ECRad_core/set_environment.tcsh
rm id
git rev-parse HEAD > id
cd ../ECRad_PyLib; rm id; git rev-parse HEAD > id; cd -
python ECRad_GUI_Application.py
