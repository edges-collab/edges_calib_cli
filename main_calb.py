import shutil
import os
from ambient import ambient_load
from ambient import hotload
import sys

calib_dir='/home/titu85/Calib/'            # Directory in which calibration data is saved
spect_dir='/home/titu85/sample_Data/'      # Directory in which Spectra is saved by digitizer code
Resistance_dir='/home/titu85/sample_Data/' # Directory in which Temperature data is saved from labjack
def main():
    temp=str(sys.argv[1])
    Spectra_path=calib_dir+temp+'/Spectra/'
    Resistance_path=calib_dir+temp+'/Resistance/'
    S11=calib_dir+temp+'/S11/'

    if not os.path.exists(Spectra_path):
        os.makedirs(Spectra_path)
    if not os.path.exists(Resistance_path):
        os.makedirs(Resistance_path)
    print("****************************************")
    print("****************************************")
    print("Starting Ambient load calibration")
    print("****************************************")
    print("****************************************")
    ambient_load()
    for root, dirs, files in os.walk(spect_dir):
        for file in files:
            if file.endswith(".acq"):
                source_path=os.path.join(root, file)
                dest_path=os.path.join(Spectra_path,('Ambient_'+file))
                shutil.copy(source_path,dest_path)
                #shutil.move(source_path,dest_path)

    for root, dirs, files in os.walk(Resistance_dir):
        for file in files:
            if file.endswith(".csv"):
                source_path=os.path.join(root, file)
                dest_path=os.path.join(Resistance_path,('Ambient_'+temp+'_'+file))
                shutil.copy(source_path,dest_path)
                #shutil.move(source_path,dest_path)
    #shutil.copy('/home/titu85/sample_Data/AmbientLoad_25C_11_25_2019_16_2_35.csv', '/home/titu85/Calib/25C/Resistance/AmbientLoad_25C_11_25_2019_16_2_35.csv')
    print("****************************************")
    print("****************************************")
    print("Starting Hot load calibration")
    print("****************************************")
    print("****************************************")
    hotload()
    for root, dirs, files in os.walk(spect_dir):
        for file in files:
            if file.endswith(".acq"):
                source_path=os.path.join(root, file)
                dest_path=os.path.join(Spectra_path,('Hotload_'+temp+'_'+file))
                shutil.copy(source_path,dest_path)
                #shutil.move(source_path,dest_path)

    for root, dirs, files in os.walk(Resistance_dir):
        for file in files:
            if file.endswith(".csv"):
                source_path=os.path.join(root, file)
                dest_path=os.path.join(Resistance_path,('Hotload_'+temp+file))
                shutil.copy(source_path,dest_path)

if __name__=='__main__':
    main()
#import hotload

#shutil.copy('/home/titu85/sample_Data/Ambient_2019_329_23_01_16_lab.acq', '/home/titu85/Calib/25C/Spectra/Hotload_2019_329_23_01_16_lab.acq')
#shutil.copy('/home/titu85/sample_Data/AmbientLoad_25C_11_25_2019_16_2_35.csv', '/home/titu85/Calib/25C/Resistance/Hotload_25C_11_25_2019_16_2_35.csv')
