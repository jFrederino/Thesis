# -*- coding: utf-8 -*-
"""
Created on Tue Jul 29 13:53:17 2025

@author: robot
"""
'''

CODE SUMMARY:

This code tests out the code written by ChatGPT that attempts to connect the laser
through a COM port using pyserial. 

'''

#%% IMPORTS

import serial.tools.list_ports
import serial

# Print List of Ports
'''
ports = serial.tools.list_ports.comports()
for port in ports:
    print(port.device)  

#%%


# Open serial port (Find info Device Manger - COMx - Properties)
ser = serial.Serial(port = 'COM3', 
                    baudrate = 9600, 
                    bytesize = serial.EIGHTBITS,
                    parity = serial.PARITY_NONE, 
                    timeout = 1) 
print(f"Serial port {ser.name} opened successfully.")
'''
# -------- Construct command packet to WRITE to register 0x__ --------
# Format:
# Byte 0: [bit7 = 1 (write), bits6-1 = register address] => 0x__
# Byte 1: MSB of data 
# Byte 2: LSB of data 
# Byte 3: Checksum (not used, send 0x00)

reg_addr = 0x13

if reg_addr == 0x10:
    name = "GAIN"
elif reg_addr == 0x11:
    name = "PH"
elif reg_addr == 0x12:
    name = "BM"
elif reg_addr == 0x13:
    name = "FM"
elif reg_addr == 0x14:
    name = "SOA"

cmd_packet = bytes([
    (reg_addr & 0x3F)|(1 << 7),  # READ bit = 1 + 6-bit reg address
    0x2B,             # Data MSB (ignored)
    0xBC,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])


# Send command
ser.write(cmd_packet)

#debug:
print(f'ser.write(cmd_packet) = {cmd_packet}')

value_msb = cmd_packet[1]
value_lsb = cmd_packet[2]
gain_value = (value_msb << 8) | value_lsb
print(f"Sent {name} = {gain_value}")


reg_addr = 0x12

if reg_addr == 0x10:
    name = "GAIN"
elif reg_addr == 0x11:
    name = "PH"
elif reg_addr == 0x12:
    name = "BM"
elif reg_addr == 0x13:
    name = "FM"
elif reg_addr == 0x14:
    name = "SOA"

cmd_packet = bytes([
    (reg_addr & 0x3F)|(1 << 7),  # READ bit = 1 + 6-bit reg address
    0x11,             # Data MSB (ignored)
    0xA7,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])

# Send command
ser.write(cmd_packet)
value_msb = cmd_packet[1]
value_lsb = cmd_packet[2]
gain_value = (value_msb << 8) | value_lsb

print(f"Sent {name} = {gain_value}")

reg_addr = 0x11

if reg_addr == 0x10:
    name = "GAIN"
elif reg_addr == 0x11:
    name = "PH"
elif reg_addr == 0x12:
    name = "BM"
elif reg_addr == 0x13:
    name = "FM"
elif reg_addr == 0x14:
    name = "SOA"

cmd_packet = bytes([
    (reg_addr & 0x3F)|(1 << 7),  # READ bit = 1 + 6-bit reg address
    0x3C,             # Data MSB (ignored)
    0x42,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])

# Send command
ser.write(cmd_packet)
value_msb = cmd_packet[1]
value_lsb = cmd_packet[2]
gain_value = (value_msb << 8) | value_lsb
print(f"Sent {name} = {gain_value}")

reg_addr = 0x14

if reg_addr == 0x10:
    name = "GAIN"
elif reg_addr == 0x11:
    name = "PH"
elif reg_addr == 0x12:
    name = "BM"
elif reg_addr == 0x13:
    name = "FM"
elif reg_addr == 0x14:
    name = "SOA"

cmd_packet = bytes([
    (reg_addr & 0x3F)|(1 << 7),  # READ bit = 1 + 6-bit reg address
    0x5D,             # Data MSB (ignored)
    0xF8,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])

# Send command
ser.write(cmd_packet)
value_msb = cmd_packet[1]
value_lsb = cmd_packet[2]
gain_value = (value_msb << 8) | value_lsb
print(f"Sent {name} = {gain_value}")

ser.close()
print("Serial port closed.")

#%%

# Open serial port (Find info Device Manger - COMx - Properties)
ser = serial.Serial(port = 'COM3', 
                    baudrate = 9600, 
                    bytesize = serial.EIGHTBITS,
                    parity = serial.PARITY_NONE, 
                    timeout = 1) 
print(f"Serial port {ser.name} opened successfully.")

# -------- Construct command packet to READ register 0x__ --------
# Format:
# Byte 0: [bit7 = 0 (read), bits6-1 = register address] => 0x10
# Byte 1: MSB of data (0x00 for read)
# Byte 2: LSB of data (0x00 for read)
# Byte 3: Checksum (not used, send 0x00)

reg_addr = 0x12

if reg_addr == 0x10:
    name = "GAIN"
elif reg_addr == 0x11:
    name = "PH"
elif reg_addr == 0x12:
    name = "BM"
elif reg_addr == 0x13:
    name = "FM"
elif reg_addr == 0x14:
    name = "SOA"

cmd_packet = bytes([
    reg_addr & 0x3F,  # READ bit = 0 + 6-bit reg address
    0x00,             # Data MSB (ignored)
    0x00,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])

# Send command
ser.write(cmd_packet)

# Read 4-byte response
response = ser.read(4)

# Check and decode
if len(response) == 4:
    reg = response[0]
    value_msb = response[1]
    value_lsb = response[2]
    status = response[3] & 0x0F

    if status == 0x01:
        gain_value = (value_msb << 8) | value_lsb
        print(f"{name} Current DAC = {gain_value}")
    else:
        print(f"Error: status code 0x{status:X}")


ser.close()
print("Serial port closed.")

