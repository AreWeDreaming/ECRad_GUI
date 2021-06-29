The ECRad GUI is a wxPython based GUI for the ECRad code.

## Installation

Installation is as simple as cloning this repository.

```bash
git clone https://github.com/AreWeDreaming/ECRad_GUI.git
```

## Dependencies
[ECRad](https://github.com/AreWeDreaming/ECRad):

```bash
git clone https://github.com/AreWeDreaming/ECRad.git
```
[ECRad Pylib](https://github.com/AreWeDreaming/ECRad_Pylib):

```bash
git clone https://github.com/AreWeDreaming/ECRad_Pylib.git
```


Python 3.0 or higher
The following Python packages (has to be Python 3):
* wxPython
* numpy
* scipy
* matplotlib
* Netcdf4

Other:
* A latex distribution for plot labels
* Batch submissions only through SLURM

## Usage
If you are using bash:
```bash
cd ECRad_GUI
./launch_ECRad_GUI.sh
```
If you are using tsch
```bash
cd ECRad_GUI
./launch_ECRad_GUI.tcsh
```


## Contributing
At the moment all contributions should be discussed. Pull requests will be welcome once version 1.0 is stable.

## License
[MIT](https://choosealicense.com/licenses/mit/)

This GUI uses the wxPython library for its frontend. The license for wxPython can be found in the licenses folder.
