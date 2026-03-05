
import pyvisa
    
#control timing on measuring voltage delay and sending packet delay
#package all of these scripts into functions
#gui?
#




rm = pyvisa.ResourceManager()
print(rm.list_resources())
USB_address = "USB0::0x2A8D::0x1601::MY60077980::INSR"
inst = rm.open_resource(USB_address)

print(inst.query("*IDN?"))
print(inst.query("MEAS:VOLT:DC? 0.100,0.001"))