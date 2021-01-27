import u3 , os ,time





d=u3.U3()
d.configIO(FIOAnalog = 15)
d.getFeedback(u3.BitDirWrite(4, 1))
d.getFeedback(u3.BitDirWrite(5, 1))
d.getFeedback(u3.BitDirWrite(6, 1))
d.getFeedback(u3.BitDirWrite(7, 1))

print("Select a Voltage output \n")
V_option=raw_input("1)37V, 2)34V, 3)31.3V, 4)28V, 5)0V \n")
print("Voltage selected=",V_option)

if V_option=="1":
   print("voltage set to 37 V  \n")
#    raw_input("Press Enter to continue...")
   d.getFeedback(u3.BitStateWrite(4, 1))
   d.getFeedback(u3.BitStateWrite(5, 1))
   d.getFeedback(u3.BitStateWrite(6, 1))
   time.sleep(0.1)
   d.getFeedback(u3.BitStateWrite(7, 0))
elif V_option=="2":
   print("voltage set to 34 V  \n")
   # raw_input("Press Enter to continue...")
   d.getFeedback(u3.BitStateWrite(4, 1))
   d.getFeedback(u3.BitStateWrite(5, 1))
   d.getFeedback(u3.BitStateWrite(6, 0))
   time.sleep(0.1)
   d.getFeedback(u3.BitStateWrite(7, 0))
elif V_option=="3":
   print("voltage set to 31.3 V  \n")
    #raw_input("Press Enter to continue...")
   d.getFeedback(u3.BitStateWrite(4, 1))
   d.getFeedback(u3.BitStateWrite(5, 0))
   d.getFeedback(u3.BitStateWrite(6, 1))
   time.sleep(0.1)
   d.getFeedback(u3.BitStateWrite(7, 0))
elif V_option=="4":
   print("voltage set to 28 V \n")
    #raw_input("Press Enter to continue...")
   d.getFeedback(u3.BitStateWrite(4, 0))
   d.getFeedback(u3.BitStateWrite(5, 1))
   d.getFeedback(u3.BitStateWrite(6, 1))
   time.sleep(0.1)
   d.getFeedback(u3.BitStateWrite(7, 0))

elif V_option=="5":
   print("voltage set to 0 V \n")
    #raw_input("Press Enter to continue...")
   d.getFeedback(u3.BitStateWrite(4, 1))
   d.getFeedback(u3.BitStateWrite(5, 1))
   d.getFeedback(u3.BitStateWrite(6, 1))
   time.sleep(0.1)
   d.getFeedback(u3.BitStateWrite(7, 1))
else :
   print("wrong choice\n")
