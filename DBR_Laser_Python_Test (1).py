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

ports = serial.tools.list_ports.comports()
for port in ports:
    print(port.device)  

#%%


# Open serial port (Find info Device Manger - COMx - Properties)
ser = serial.Serial(port = 'COM4', 
                    baudrate = 9600, 
                    bytesize = serial.EIGHTBITS,
                    parity = serial.PARITY_NONE, 
                    timeout = 1) 
print(f"Serial port {ser.name} opened successfully.")

# -------- Construct command packet to WRITE to register 0x__ --------
# Format:
# Byte 0: [bit7 = 1 (write), bits6-1 = register address] => 0x__
# Byte 1: MSB of data 
# Byte 2: LSB of data 
# Byte 3: Checksum (not used, send 0x00)

reg_addr = 0x13 #FM command

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
    0x1D,             # Data MSB (ignored)
    0x3E,             # Data LSB (ignored)
    0x00              # Checksum (not implemented)
])

# Send command
ser.write(cmd_packet)
value_msb = cmd_packet[1]
value_lsb = cmd_packet[2]
gain_value = (value_msb << 8) | value_lsb
print(f"Sent {name} = {gain_value}")

reg_addr = 0x12 #BM command

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
    0x20,             # Data MSB (ignored)
    0x00,             # Data LSB (ignored)
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
    0x29,             # Data MSB (ignored)
    0x98,             # Data LSB (ignored)
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
    0x4C,             # Data MSB (ignored)
    0xCE,             # Data LSB (ignored)
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
