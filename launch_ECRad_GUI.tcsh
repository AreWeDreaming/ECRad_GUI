#!/usr/bin/tcsh

if ($HOSTNAME =~ *"mpg"* ) then
  source ../ECRad_core/set_environment.tcsh
endif
rm id
git rev-parse HEAD > id
cd ../ECRad_PyLib; rm id; git rev-parse HEAD > id; cd -
python ECRad_GUI_Application.py
