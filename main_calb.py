import shutil
import os
from ambient import ambient_load
import sys

calib_dir='/home/edges-0/Desktop/Titu/Automation/Calib/'      # Directory in which calibration data is saved
spect_dir='/home/edges-0/Desktop/DATA//asulab/lab/2020/'      # Directory in which Spectra is saved by digitizer code


def main():
    temp=str(sys.argv[2])
    time=float(sys.argv[1])
    Spectra_path=calib_dir+temp+'/Ambient/Spectra/'
    Resistance_path=calib_dir+temp+'/Ambient/Resistance/'
    S11_path=calib_dir+temp+'/Ambient/S11/'
#---------------------------------------------------------
#       Clean up any previous ,acq or .csv files 
#---------------------------------------------------------    
    clear_acq=os.listdir(spect_dir)
    for item in clear_acq:
 	   if item.endswith(".acq"):
         	os.remove(item)
    cwd=os.getcwd()
    clear_csv=os.listdir(cwd)
    for item in clear_csv:
           if item.endswith(".csv"):
                os.remove(item)
    shutil.rmtree(Resistance_path)
    shutil.rmtree(Spectra_path)
    shutil.rmtree(S11_path)
    #clear_acq=os.listdir(Resistance_path)
    #for item in clear_acq:
    #       if item.endswith(".csv"):
    #            os.remove(item)
    #clear_acq=os.listdir(Spectra_path)
    #for item in clear_acq:
    #       if item.endswith(".acq"):
    #            os.remove(item)
    #clear_acq=os.listdir(S11_path)
    #for item in clear_acq:
    #       if item.endswith(".csv"):
    #            os.remove(item)
#-------------------------------------------------------
#       Creat directory structure
#------------------------------------------------------
    if not os.path.exists(Spectra_path):
        os.makedirs(Spectra_path)
    if not os.path.exists(Resistance_path):
        os.makedirs(Resistance_path)
    if not os.path.exists(S11_path):
        os.makedirs(S11_path)
#------------------------------------------------------
#      Starting ambient load calibration
#------------------------------------------------------
    ambient_load(temp,time)


#------------------------------------------------------
#      moving the calibration files
#------------------------------------------------------
    for file in os.listdir(spect_dir):
                        if file.endswith(".acq"):
                                source_path=os.path.join(spect_dir, file)
                                dest_path=os.path.join(Spectra_path,('Ambient_'+file))
                                shutil.move(source_path,dest_path)

    for file in os.listdir(cwd):
                        if file.endswith("Temperature.csv"):
                                #source_path=os.path.join(spect_dir, file)
                                dest_path=os.path.join(Resistance_path,('Ambient_'+file))
                                shutil.move(file,dest_path)


    for file in os.listdir(cwd):
                        if file.endswith(".csv"):
                                #source_path=os.path.join(spect_dir, file)
                                dest_path=os.path.join(S11_path,(file))
                                shutil.move(file,dest_path)
    print("**************************************************************************")
    print("--------------------------------------------------------------------------")
    print("                           Finished Calibration                 ")
    print("--------------------------------------------------------------------------")
    print("**************************************************************************")
#--------------------------------------------------------
if __name__=='__main__':
    main()




