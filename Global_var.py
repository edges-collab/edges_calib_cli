import u3 , os ,time


calib_dir='/home/edges-0/Desktop/Titu/Automation_cleanup/Calib/'      # Directory in which calibration data is saved
spect_dir='/home/edges-0/Desktop/DATA//asulab/lab/2021/' 

PXspec='/home/edges-0/Desktop/code/Edges2/fastspec-1.1.0/fastspec_single'
Temp_res='/home/edges-0/Desktop/Titu/Automation/Temp_sensor_with_time_U6_t.py'
PXspec_ini='/home/edges-0/Desktop/code/Edges2/fastspec-1.1.0/edges.ini'
def initialize():
    global d, e, p
    d=u3.U3()
    d.configIO(FIOAnalog = 15)
    d.getFeedback(u3.BitDirWrite(4, 1))
    d.getFeedback(u3.BitDirWrite(5, 1))
    d.getFeedback(u3.BitDirWrite(6, 1))
    d.getFeedback(u3.BitDirWrite(7, 1))

