

import pyvisa

rm = pyvisa.ResourceManager()
print(rm.list_resources())
choice = "USB0::0x2A8D::0x1601::MY60077980::INSTR"
_voltmeter_inst = rm.open_resource(choice)

print(_voltmeter_inst.query("*IDN?"))
#print(_voltmeter_inst.query("MEAS:VOLT:DC? 10,0.001"))

def read_voltage_1_() -> float:
    global _voltmeter_inst
    return float(_voltmeter_inst.query("MEAS:VOLT:DC? 10,0.001"))
    
def disconnect_from_voltmeter():
    global _voltmeter_inst

    _voltmeter_inst.close()

while True:
    input()
    print(f"V: {read_voltage_1_()}")


disconnect_from_voltmeter()