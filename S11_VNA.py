import socket
import sys
import time
import array as arr
from codecs import decode
import struct
import csv
import numpy as np
import re

def S11():
	#-----------------------------------------------------------------------
	#             Function to read the data transfered from VNA
	#-----------------------------------------------------------------------
	def binblock_raw(data_in):

	    #Find the start position of the IEEE header, which starts with a '#'.
	    startpos = data_in.find("#")
    	    #print("Start Position reported as " + str(startpos))

	    #Check for problem with start position.
	    if startpos < 0:
	        raise IOError("No start of block found")

	    #Find the number that follows '#' symbol.  This is the number of digits in the block length.
	    Size_of_Length = int(data_in[startpos+1])
	    #print("Size of Length reported as " + str(Size_of_Length))

	    ##Now that we know how many digits are in the size value, get the size of the data file.
	    Image_Size = int(data_in[startpos+2:startpos+2+Size_of_Length])
	    #print("Number of bytes in file are: " + str(Image_Size))

	    # Get the length from the header
	    offset = startpos+Size_of_Length

	    # Extract the data out into a list.
	    return data_in[offset:offset+Image_Size]
	#-----------------------------------------------------------------------
	#             Function to read the data transfered from VNA
	#-----------------------------------------------------------------------



	# Create a TCP/IP socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_address = ('10.206.161.72', 5025)                         # ip address of NA
	print "--------------------------------------------------------------------------"
        print >>sys.stderr, 'connecting to network analyser  %s port %s' % server_address
        print "--------------------------------------------------------------------------"
	
        s.connect(server_address)
	MESSAGE = '*IDN?\n'
	s.send(MESSAGE)
	time.sleep(0.05)
	data = s.recv(200)
	print "--------------------------------------------------------------------------"
	print "   Connected to ENA: ", data
	print "--------------------------------------------------------------------------"

	MESSAGE = 'FORM:DATA ASCii;*OPC?\n'             #Define data format for Data transfer reference SCPI Programer guide E5061A 
	s.send(MESSAGE)

	MESSAGE = 'SENS:FREQ:START 100e6;*OPC?\n'
	s.send(MESSAGE)

	MESSAGE = 'SENS:FREQ:STOP 200e6;*OPC?\n'
	s.send(MESSAGE)

	MESSAGE = 'SENS:SWE:POIN 201;*OPC?\n'
	s.send(MESSAGE)
	MESSAGE = 'SENS:BWID 300;*OPC?\n'
	s.send(MESSAGE)
	MESSAGE = 'SENS:AVER:COUN 10;*OPC?\n'
	s.send(MESSAGE)
	MESSAGE = 'INIT:CONT OFF;*OPC?\n'
	s.send(MESSAGE)
	print "__________________________________________________________________________ "
	print '                        STARTING MEASUREMENTS'
	MESSAGE = 'INIT:IMM;*OPC?\n'
	print '__________________________________________________________________________'
	s.send(MESSAGE)
	time.sleep(10)
	#___________________________________________________________

	# Read Phase value and transfer to host controller
	#-----------------------------------------------------------


	MESSAGE = 'CALC1:FORM PHASE;*OPC?\n' #Define data type and chanel for Data transfer reference SCPI Programer guide E5061A 
	s.send(MESSAGE)

	MESSAGE = 'MMEM:STOR:FDAT "D:\\Auto\\EDGES_p.csv";*OPC?\n'#save data internal memory reference SCPI Programer guide E5061A 
	s.send(MESSAGE)
	MESSAGE = 'MMEM:TRAN? "D:\\Auto\\EDGES_p.csv";*OPC?\n' #transfer data to host controller reference SCPI Programer guide E5061A 
	s.send(MESSAGE)
	time.sleep(1)
	data_phase = s.recv(15000) #buffer size for receiving data currently set as 15Kbytes

	binary_data_p=binblock_raw(data_phase)
	data_p=re.split('\r\n|,',binary_data_p)
	length=len(data_p[5:])
	data_p_array=np.array(data_p[5:])
	data_p_re=data_p_array.reshape(length/3,3)

	#-----------------------------------------------------------
	#___________________________________________________________


	#___________________________________________________________

	# Read Magnitude value and transfer to host controller
	#-----------------------------------------------------------

	MESSAGE = 'CALC1:FORM MLOG;*OPC?\n'
	s.send(MESSAGE)

	MESSAGE = 'MMEM:STOR:FDAT "D:\\Auto\\EDGES_m.csv";*OPC?\n'
	s.send(MESSAGE)
	MESSAGE = 'MMEM:TRAN? "D:\\Auto\\EDGES_m.csv";*OPC?\n'
	s.send(MESSAGE)
	time.sleep(1)
	data_mag = s.recv(15000)

	binary_data_m=binblock_raw(data_mag)
	data_m=re.split('\r\n|,',binary_data_m)
	length=len(data_m[5:])
	data_m_array=np.array(data_m[5:])
	data_m_re=data_m_array.reshape(length/3,3)

	#-----------------------------------------------------------
	#___________________________________________________________

	#___________________________________________________________

	# Reshape Magnitude, phase and save as S11.csv in host controller
	#-----------------------------------------------------------

	S11=np.empty([np.size(data_m_re,0),3])
	S11[:,0]=data_m_re[:,0]
	S11[:,1]=data_m_re[:,1]
	S11[:,2]=data_p_re[:,1]
	#print("S11=",S11)
	np.savetxt('S11.csv',S11, delimiter=",")
	#print("S11 saved as S11.csv")
	#print("Number of points=",np.size(S11,0))
	#-----------------------------------------------------------
	#___________________________________________________________


	s.close()
def main():
    S11()
if __name__=='__main__':
    main()    
