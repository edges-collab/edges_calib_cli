import shutil
import subprocess
import os
import socket
from cli_automation import ambient_load
from cli_automation import hot_load
from cli_automation import LongCableOpen_load
from cli_automation import LongCableShort_load
from cli_automation import Antsim1_load
from cli_automation import Antsim2_load
from cli_automation import Antsim3_load
from cli_automation import SwitchingState01
from cli_automation import ReceiverReading01
from cli_automation import S11
from cli_automation import RS11
from cli_automation import vna_calib
from cli_automation import RR_VNA_calib
from cli_automation import handler

import sys
import time
import datetime
import u3 , os ,time
from signal import signal, SIGINT
from sys import exit
import signal
import Global_var 




calib_dir=Global_var.calib_dir      # Directory in which calibration data is saved
spect_dir=Global_var.spect_dir    # Directory in which Spectra is saved by digitizer cod


#--------------------------------------------------


def main():
    Global_var.initialize() 
    signal.signal(signal.SIGINT, handler)
    #temp=str(sys.argv[2])
    time_custom=raw_input("Please enter time(seconds) to run calibration \n")
    time=int(time_custom)
    res_name="01_"
    folder_flag=0
    now = datetime.datetime.now()
    year=now.year
    month=now.month
    #day_chk=now.strftime('%j')
    day=now.day
    if day<10:
       day="0"+str(day)
    else:
       day=str(day)
    #print("day=", day)
    if month<10:
       month="0"+str(month)
    else:
       month=str(month)
    #print("month=",month)
    hour=now.hour
    minute=now.minute
    second=now.second
    date= str(year) + "_" +month+"_"+ day + "_" +"040_to_200MHz"












    print("Select temperature for calibration \n")
    temp_option=raw_input("1)35C, 2)25C, 3)15C 4)custom temperature \n")
    print("Temperature selected=",temp_option)
    if temp_option=="1":
       temp=str(35)
    elif temp_option=="2":
       temp=str(25)
    elif temp_option=="3":
       temp=str(15)
    elif temp_option=="4":
       temp_custom=raw_input("Please enter temperature in deg C \n")
       temp=str(temp_custom)
    else :
       print("wrong receiver option \n")
       sys.exit()


    print("Select a receiver for calibration \n")
    rec_option=raw_input("1)Receiver_01, 2)Receiver_02, 3)Receiver_03 \n")
    print("Receiver selected=",rec_option)
    if rec_option=="1":
       receiver="Receiver01_"+temp+"C"+"_"+date
       rec=int(1)
    elif rec_option=="2":
       receiver="Receiver02_"+temp+"C"+"_"+date
       rec=int(2)
    elif rec_option=="3":
       receiver="Receiver03_"+temp+"C"+"_"+date
       rec=int(3)
    else :
       print("wrong receiver option \n")
       sys.exit()





#------------------------------------------------------------------
#------------------------------------------------------------------
# check any calibration folder created in last seven days if so 
# no new folder is created. Calib dat will be save in that folder
# considering that it is a part of continuos calibration process
    folders = []
    d=os.listdir(calib_dir)
    for folder in d:
        folders.append(folder)
    len_fol=len(folders)
    for folder in d:
      exist_fold=folder
      exi_rec=int(exist_fold[9])
      exi_day=int(exist_fold[-16:-14])
      exi_month=int(exist_fold[-19:-17])
      exi_temp=exist_fold[-28:-26]
      day_cal=[0,31,59,90,121,151,182,213,243,274,304,335]
      day_exi=day_cal[exi_month]+exi_day
      day_chk=day_cal[int(month)]+int(day)
      date_exi=exist_fold[-24:-1]+'z'
   
      if (temp==exi_temp) & ((day_chk-day_exi)<=15) & (rec==exi_rec):
            
         rec_c = raw_input("folder created within 15 days so considering this as a continuos calibration, Do you want to continue press y/n ")
         if rec_c=="y":
            receiver=exist_fold
         if rec_c=="n":
            print("Please remove the existing folder")
            sys.exit()

         date=date_exi
         folder_flag=1
    #sys.exit() 
#-------------------------------------------------------------
#-------------------------------------------------------------


#---------------------------------------------------------
#       Clean up any previous ,acq or .csv files 
#---------------------------------------------------------    

    
    print("Select a load for calibration \n")
    load_option=raw_input("1)Ambient, 2)HotLoad, 3)LongCableOpen, 4)LongcableShort, 5)Antsim1, 6)Antsim2, 7)Antsim3 , 8)SwitchingState, 9)ReceiverReading, 10)VNA_calibaration 11)Receiverreading_VNA_Calibartion, 12)run Fastspec continuosly\n")
    print("selected load= ",load_option)
    if load_option=="1":
       load="/Ambient"
    elif load_option=="2":
       load="/HotLoad"
    elif load_option=="3":
       load="/LongCableOpen"
    elif load_option=="4":
       load="/LongCableShorted"
    elif load_option=="5":
       load="/AntSim1"
    elif load_option=="6":
       load="/AntSim2"
    elif load_option=="7":
       load="/AntSim3"
    elif load_option=="8":
       load="/SwitchingState"
    elif load_option=="9":
       load="/ReceiverReading"
    elif load_option=="10":
       print("VNA_calibartion")
       vna_calib()
       sys.exit()
    elif load_option=="11":
       print("Receiverreading_VNA_calibartion")
       RR_VNA_calib()
       sys.exit()
    elif load_option=="12":
       print("run ./fastspec.py")
       sys.exit()
    else :
       print("wrong load option \n")
       sys.exit()
#------------------------------------------------------
    print("Enter the run number")
    run_num=raw_input("1)01, 2)02, 3)03 ")
    if run_num=="1":
       run_num_1="01"
       load=load+"01"
    elif run_num=="2":
       run_num_1="02"
       load=load+"02"
    elif run_num=="3":
       run_num_1="03"
       load=load+"03"
    else:
       print("Wrong run number entered")

    Spectra_path=calib_dir+receiver+'/Spectra/'
    Resistance_path=calib_dir+receiver+'/Resistance/'
    S11_path=calib_dir+receiver+'/S11/'+load+'/'
    today = datetime.datetime.now()
    day=today.strftime('%j')
#---------------------------------------------
#---------------------------------------------
# remove all residue *.acq and *.csv files from previous run

    clear_acq=os.listdir(spect_dir)
    for item in clear_acq:
 	   if item.endswith(".acq"):
                #print("acq=",item,"spect_dir=",spect_dir)
                acq_loc=spect_dir+item 
         	os.remove(acq_loc)
    cwd=os.getcwd()
    clear_csv=os.listdir(cwd)
    for item in clear_csv:
           if item.endswith(".csv"):
                os.remove(item)
#-------------------------------------------------------
#       Creat directory structure for no directory within seven days
#------------------------------------------------------
    if not os.path.exists(S11_path):
      os.makedirs(S11_path)
    else:
      fold = raw_input("Same run number exists, Do you want to overwrite? press y/n ")
      if fold=="n": 
          print("please change the run number")
          sys.exit()
    if folder_flag==0:
      os.makedirs(Spectra_path)
      os.makedirs(Resistance_path)

#------------------------------------------------------
#      Starting load calibration
#------------------------------------------------------
    if load_option=="1":
       ambient_load(temp,time)
    elif load_option=="2":
       hot_load(temp,time)
    elif load_option=="3":
        LongCableOpen_load(temp,time)
    elif load_option=="4":
       LongCableShort_load(temp,time)
    elif load_option=="5":
       Antsim1_load(temp,time)
    elif load_option=="6":
       Antsim2_load(temp,time)
    elif load_option=="7":
       Antsim3_load(temp,time)
    elif load_option=="8":
       SwitchingState01()
    elif load_option=="9":
       ReceiverReading01()



#------------------------------------------------------
#      moving the calibration files
#------------------------------------------------------
    for file in os.listdir(spect_dir):
                        if file.endswith(".acq"):
                                source_path=os.path.join(spect_dir, file)
                                if load_option=="1":
       					dest_path=os.path.join(Spectra_path,('Ambient_'+run_num_1+'_'+file))
    				elif load_option=="2":
       					dest_path=os.path.join(Spectra_path,('HotLoad_'+run_num_1+'_'+file))
    				elif load_option=="3":
       					dest_path=os.path.join(Spectra_path,('LongCableOpen_'+run_num_1+'_'+file))
    			        elif load_option=="4":
        				dest_path=os.path.join(Spectra_path,('LongCableShorted_'+run_num_1+'_'+file))
    				elif load_option=="5":
      					 dest_path=os.path.join(Spectra_path,('AntSim1_'+run_num_1+'_'+file))
    			        elif load_option=="6":
       					dest_path=os.path.join(Spectra_path,('AntSim2_'+run_num_1+'_'+file))
   				elif load_option=="7":
                                        dest_path=os.path.join(Spectra_path,('AntSim3_'+run_num_1+'_'+file))
                                elif load_option=="8":
                                        dest_path=source_path
                                elif load_option=="9":
                                        dest_path=source_path
#                                print("Source_path",source_path)
#                                print("Dest_path",dest_path)
                                shutil.move(source_path,dest_path)
                                res_name=source_path[-25:-4]
#                                print("res_name=",res_name)
    for file in os.listdir(cwd):
                        if file.endswith("Temperature.csv"):
                                if load_option=="1":
                                        dest_path=os.path.join(Resistance_path,('Ambient_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="2":
                                        dest_path=os.path.join(Resistance_path,('Hot_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="3":
                                        dest_path=os.path.join(Resistance_path,('LongCableOpen_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="4":
                                        dest_path=os.path.join(Resistance_path,('LongCableShorted_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="5":
                                         dest_path=os.path.join(Resistance_path,('AntSim1_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="6":
                                        dest_path=os.path.join(Resistance_path,('AntSim2_'+run_num_1+'_'+res_name+'.csv'))
                                elif load_option=="7":
                                        dest_path=os.path.join(Resistance_path,('AntSim3_'+run_num_1+'_'+res_name+'.csv'))
                   

                                shutil.move(file,dest_path)


    for file in os.listdir(cwd):
                        if file.endswith(".s1p"):
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




