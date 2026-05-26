#Import Files
from convert_data import *
from pymodbus.client import ModbusTcpClient

#Open TCP Port
client = ModbusTcpClient('192.168.1.15')

#Read AIN0
result = client.read_input_registers(address=0,2)
print(f'AIN0 val: {data_to_float32(result.registers)}')

#Close TCP Port
client.close()