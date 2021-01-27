import shutil
import os
import sys
import u6,time,csv,datetime,math

#sys.stdout.write("\033[1;34m")
calib_dir='/home/edges-0/Desktop/Titu/Automation/Calib/'      # Directory in which calibration data is saved
spect_dir='/home/edges-0/Desktop/DATA//asulab/lab/2020/'      # Directory in which Spectra is saved by digitizer code
Resistance_dir='/home/edges-0/Desktop/Titu/Automation/'       # Directory in which Temperature data is saved from labjack
def temp_sensor():
    	#stop_time=float(sys.argv[1])
	#temp=str(sys.argv[2])
        stop_time=1 
        temp=str(25)
	#-----------------------------------------------------------------------------------
	#-----------------------------------------------------------------------------------
#    	y=0
    	d = u6.U6()
#	L=1

	Start_second = time.time()
	filename = 'Temperature.csv'

	with open(filename, 'w') as csvfile:
		fieldnames = ['Date','Time','LNA Voltage','LNA Thermistor (Ohm)','LNA (C)','SP4T Voltage', 'SP4T Thermistor (Ohm)','SP4T (C)','Load Voltage','Load-thermistor (Ohm)','Load (C)','Room_Temp(C)']
	        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        	writer.writeheader()

        	while True:
                	now = datetime.datetime.now()
                	year=now.year
                	month=now.month
                	day=now.day
                	hour=now.hour
                	minute=now.minute
                	second=now.second
                	date= str(month) + "/" + str(day) + "/" + str(year)
                	times= str(hour) + ":" + str(minute) + ":" + str(second)
                	internalT = d.getTemperature()-273 # internal temp of labjack   

#-----------------------------------------------------------------------------------
#    			Reading Labjack Voltage			

#-----------------------------------------------------------------------------------


                	LNAV = d.getAIN(3)
                	SP4TV = d.getAIN(0)
               	 	LoadV = d.getAIN(1)
#-----------------------------------------------------------------------------------
#                      Calculating the resistence from voltage
#-----------------------------------------------------------------------------------


                	LNAresistance = ((LNAV*9918)/(5.05-LNAV))
                	SP4Tresistance = ((SP4TV*9960)/(4.9262-SP4TV))
                	Loadresistance = ((LoadV*9923)/(4.9262-LoadV))

#-----------------------------------------------------------------------------------
#                      Calculating the temperature with curve fitting 
#-----------------------------------------------------------------------------------


                	F1 = .129675e-2
                	F2 = .197374e-3
                	F3 = .304e-6
                	F4 = 1.03514e-3
                	F5 = 2.33825e-4
                	F6 = 7.92467e-8
                	try: #Hello leroy Fixes the value error causing a crash
                        	LNAdegc = 1/(F1+F2*math.log(LNAresistance)+F3*math.pow(math.log(LNAresistance),3))-273.15
                        	SP4Tdegc = 1/(F1+F2*math.log(SP4Tresistance)+F3*math.pow(math.log(SP4Tresistance),3))-273.15
				Loaddegc = 1/(F4+F5*math.log(Loadresistance)+F6*math.pow(math.log(Loadresistance),3))-273.15
                	except ValueError:
                        	print("Warning, Failed to calculate values! LoadResistance was {} and load voltage was {}. Skipping Measurement".format(Loadresistance, LoadV))
                        	continue
                	time.sleep(30)
                	writer.writerow({'Date': date,'Time': times,'LNA Voltage':LNAV,'LNA Thermistor (Ohm)': LNAresistance,'LNA (C)':LNAdegc,'SP4T Voltage': SP4TV, 'SP4T Thermistor (Ohm)': SP4Tresistance,'SP4T (C)':SP4Tdegc,'Load Voltage': LoadV,'Load-thermistor (Ohm)': Loadresistance,'Load (C)':Loaddegc,'Room_Temp(C)':internalT})
                	#root.after(1000)
                	print("Date","     Time","   LNA_Voltage","LNA_Resistance","LNA_DegC","SP4T_Voltage","SP4T_Resistance","SP4T_DegC","LOAD_Voltage","LOAD_Resistance","LOAD_DegC","LabJack_temp")
                	print(date, times, round(LNAV,3), "    ",round(LNAresistance,0),"     ", round(LNAdegc,1), "   ",round(SP4TV,3),"     ", round(SP4Tresistance,0),"      ", round(SP4Tdegc,1), "       ",round(LoadV,3),"      ", round(Loadresistance,0),"     ", round(Loaddegc,1),"     ",round(internalT,1))
		
			
		
#-----------------------------------------------------------------------------------
#      Saving the temperature file  
#-----------------------------------------------------------------------------------


               
        #shutil.move(filename,temp+'_'+str(year)+'_'+str(day)+'_'+str(month)+'_'+str(hour)+'_'+str(minute)+'_'+str(second)+'_'+filename)


#-----------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------

                
if __name__=='__main__':
    temp_sensor()

