#!/bin/tcsh
module purge
if ($SYS == "amd64_sles11") then
  module load intel/16.0
  module load mkl/11.2 
  module load zeromq/4.0.5
  module load vtk/5.10.1
  module load netcdf-serial/4.2.1.1
  module load fftw/3.3.3
  module load netcdf-mpi/4.2.1.1 
  module load nag_flib/intel/legacy-r4 
  module load perflib
  module load impi/4.1.3
  module load pgplot/5.2.2
  module load jdk/1.8
  module load qt/4.8.4
  module load nag_flib/intel/mk24
  module load python27/basic
  setenv LD_LIBRARY_PATH ${LD_LIBRARY_PATH}:/afs/ipp/common/soft/netcdf/4.2.1.1/amd64_sles11/intel/12.1/impi/4.1.0/lib/:/afs/ipp/aug/ads/lib64/amd64_sles11/
  module load texlive
  module load git
else if ($SYS == "amd64_sles12") then
  module load intel/17.0 
  module load mkl/2017
  module load impi/2017.4
  module load nag_flib/intel/mk26
  module load nag_flib/intel/legacy-r4
  module load anaconda/2_5.3.0
  module load git
else if ($SYS == "amd64_sles15") then
  module load intel
  module load mkl
  module load texlive
  module load anaconda/3/2018.12
  module load git
endif
rm id
git rev-parse HEAD > id
if ( -d "../augd_ecrad_pylib" ) then
  cd ../augd_ecrad_pylib; rm id; git rev-parse HEAD > id; cd -
else
  cd ../ECRad_Pylib; rm id; git rev-parse HEAD > id; cd -
endif
python ECRad_GUI_Application.py
