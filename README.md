# edges_calib_cli
#   automated calibration of edges receiver
# Heading Cli- Automation testing and review 

## Heading Objectives
Review the naming convention and directory structure.
Review the missing steps in calibration if any.
Review the functionality. 

## Heading Directories 

## HeadingDestination directory
    Directory in which the calibrations files are saved      
        /home/edges-0/Desktop/Titu/Automation/Calib

  
## Heading Code directory
     Directory in which the scripts are saved
     /home/edges-0/Desktop/Titu/Automation

## Heading There are four scripts 
##Heading Main_calib.py 
Calls the measurement script (ambient.py)
Save all generated files to destination directory
##Heading ambient.py
Display all messages and comments
Calls the fastspec script
Calls the S11 measurement script
Calls the temperature measurement script 
##Heading S11_VNA.py
Connect to network analyser and measure S11
Temp_sensor_with_time_U6.py
Connect to labjack and measure the temperature.

##Heading Instruction to run

   Login to lab-PC
                      ssh edges-0@10.206.162.150
                      password :- d1p0l3ASU1420
                      cd  /home/edges-0/Desktop/Titu/Automation
                      sudo python main_calb.py 50 25C
                       where :-
                                  50 is the time in seconds to execute the calibration(can be varied)
                                  25C is the temperature of receiver
