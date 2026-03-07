
import pyvisa
import time
#control timing on measuring voltage delay and sending packet delay
#package all of these scripts into functions
#gui?
#


rm = pyvisa.ResourceManager()
print(rm.list_resources())
inst = rm.open_resource("USB0::0x2A8D::0x1601::MY60077980::INSTR")

#this thing can read as fast as python can talk to it.
print(inst.query("*IDN?"))
for i in range(10):
    print(inst.query("MEAS:VOLT:DC? 0.100,0.001"))