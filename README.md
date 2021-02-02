# edges_calib_cli

**Automated calibration of edges receiver**

## Installation

You need to separately install u3 and u6. They can be installed following the instructions
at https://labjack.com/support/software/examples/ud/labjackpython

Then just `pip install .`.

## Project Structure
Main_calib.py

 This file calls the individual function for each load calibration. It also takes care of the naming convention and directory structure.

Cli_automation.py

 This file contains individual functions for each load, other than that it contains functions for VNA calibration, Receiver reading VNA calibration, reading S11 from VNA, exit control when ctrl+C detection.

Global_var.py

 This file contains all the global variable declarations like calibration data path, digitizer data location, PXspec, and PXspec .ini location and temperature measurement python code location. It also initializes labjack U3 as a global variable(used for power supply automation).

Temp_sensor_with_time_U6_t.py
  This file reads the resistance value of different thermistors located at load and inside the receiver.
