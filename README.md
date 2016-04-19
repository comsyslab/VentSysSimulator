# Ventilation System Simulator
This repository contains the ventilation system simulator based on the affinity laws with tunable exponents. 
The different components modelled in this simulator are: ventilation system (with exhaust and supply fan), 
indoor CO2 model, household loads (using BehavSim), residential buildings and demand response controller. 
For details on the model please check:

Sergi Rotger-Griful, Rune Hylsberg Jacobsen, Dat Nguyen, Gorm Sørensen, Demand response potential of ventilation systems in residential buildings, Energy and Buildings, Volume 121, 1 June 2016, Pages 1-10, ISSN 0378-7788, http://dx.doi.org/10.1016/j.enbuild.2016.03.061.

Version 1.0 developed by Sergi Rotger Griful <srgr@eng.au.dk> in collaboration with Dat Nguyen <nguyen763@gmail.com> 
on 23-10-2015.

## Content
- aggregayed-behavsim-loads/: Folder containing a a CSV file per each household load generated from the BehavSim csv files using aggregated_behavsim.py
- household-loads-behavsim/: Folder containing all CSV files generated with BehavSim
- results/: Folder containing the simualtion results (configuration of the different buildings and output variables)
- aggregate_behavsim.py: Code that gets as input the CSV files generated in BehavSim and aggregates all appliances loads per households.
- simulator.py: Main simulator with all classes definition and execution of the environment.
- dr_controller_test.csv: File containing the control actions scheduled by the demand response controllers (from, to, relative pressure setpoint)
- IndoorCo2Gen24h.csv: File containing the indoor CO2 generation per each hour in Grundfos Dormiotry Lab required by the indoor CO2 model (parameter G in CO2 model)
- stable-req.txt: File containing all required Python packages to run the simulator

## Requirements
- Python 2.7
- Python libraries from stable-req.txt
- Access to BehavSim data: https://github.com/gridsim/behavsim

## How to run it
- Define simulation capitalized parameters in the constants definition in simulator.py (e.g., simulation time, number of buildings...)
- Write the scheduled control actions in dr_controller_test.csv
- Run simulator.py. This will generate 2 files: SimulationConfiguration.csv with all buildings definition and output.csv with the simulation data (time, total power, average CO2) 


## Behavsim
Here is the link to download the BehavSim: https://github.com/gridsim/behavsim

Python libraries required to run BehavSim:

- numpy-1.9.2-win32-superpack-python2.7 (http://sourceforge.net/projects/numpy/files/NumPy/1.9.2/)
- pygtk-all-in-one-2.24.2.win32-py2.7 (http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/)
- scipy-0.16.0-win32-superpack-python2.7 (http://sourceforge.net/projects/scipy/files/scipy/0.16.0b2/)

