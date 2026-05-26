'''
This example reads various test registers from a T7 using the pymodbus library.

'''

from pymodbus.client.sync import ModbusTcpClient



'''
# Import files
from DBR_FP4209.myGUI.T7_testing.convert_data import *



# Open TCP port
client = ModbusTcpClient("192.168.1.15")

# Test writing registers
rq = client.write_register(55110, uint16_to_data(1234))
rq = client.write_registers(55120, uint32_to_data(1234567))
rq = client.write_registers(55122, int32_to_data(-1234))
rq = client.write_registers(55124, float32_to_data(1.234))

# Test reading registers
rr = client.read_input_registers(55100, 2)
print("LJ Test Register (UINT32) %s" % data_to_uint32(rr.registers))
rr = client.read_input_registers(55110, 1)
print("Test UINT16 %s" % data_to_uint16(rr.registers))
rr = client.read_input_registers(55120, 2)
print("Test UINT32 %s" % data_to_uint32(rr.registers))
rr = client.read_input_registers(55122, 2)
print("Test INT32 %s" % data_to_int32(rr.registers))
rr = client.read_input_registers(55124, 2)
print("Test FLOAT32 %s" % data_to_float32(rr.registers))

# Close TCP port
client.close()
'''