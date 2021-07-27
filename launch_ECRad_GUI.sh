#!/bin/bash
source ../ECRad_core/set_environment.sh
rm id
git rev-parse HEAD > id
if [ -d "../augd_ecrad_pylib" ]
  then 
  cd ../augd_ecrad_pylib; rm id; git rev-parse HEAD > id; cd -
else
  cd ../ECRad_PyLib; rm id; git rev-parse HEAD > id; cd -
fi
python ECRad_GUI_Application.py
