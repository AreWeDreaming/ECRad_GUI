#!/bin/bash
if [[ $HOSTNAME == *"mpg"* ]]
  then
  module purge
  module load intel
  module load mkl
  module load texlive
  module load anaconda/3/2020.02
  module load git
  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$MKLROOT/lib/intel64/
elif [[ $HOSTNAME == *"cm.cluster"* ]]
  then
  module use /home/software/psfc/modulefiles/
  module load psfc/config
  module load anaconda3/2020.11
  module load psfc/netcdf/intel-17/4.4.1.1
  module load intel
  module load mkl
  module load psfc/pgplot/5.2.2
  module load texlive
  module load engaging/git
  # >>> conda initialize >>>
  # !! Contents within this block are managed by 'conda init' !!
  __conda_setup="$('/home/software/anaconda3/2020.11/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
  if [ $? -eq 0 ]; then
      eval "$__conda_setup"
  else
      if [ -f "/home/software/anaconda3/2020.11/etc/profile.d/conda.sh" ]; then
          . "/home/software/anaconda3/2020.11/etc/profile.d/conda.sh"
      else
          export PATH="/home/software/anaconda3/2020.11/bin:$PATH"
      fi
  fi
  unset __conda_setup
  # <<< conda initialize <<<
  conda activate ECRad_conda
elif [[ $HOSTNAME == *"iter"* ]]; then
  module purge
  module load IMAS
  module load texlive
  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/.local/lib/python3.8/site-packages/wx/
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
