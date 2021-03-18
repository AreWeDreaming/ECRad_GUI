#!/bin/bash
if [ $SYS == "amd64_sles15" ]
  then
  module purge
  module load intel
  module load mkl
  module load texlive
  module load anaconda/3/2018.12
  module load git
fi
rm id
git rev-parse HEAD > id
if [ -d "../augd_ecrad_pylib" ]
  then 
  cd ../augd_ecrad_pylib; rm id; git rev-parse HEAD > id; cd -
else
  cd ../ECRad_PyLib; rm id; git rev-parse HEAD > id; cd -
fi
python ECRad_GUI_Application.py
