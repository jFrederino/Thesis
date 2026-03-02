# JAMES USHER 2026

import serial
import serial.tools.list_ports
import generate_table as table #generate_table.py in /DBR/DAC_Tables/*
import sys
import os 
import glob
import time
from tqdm import tqdm
import random

'''
#Procedure to turn on laser:

open GUI
INIT on COM4 probably
ENABLE laser
close GUI

RUN CODE
(make sure to close serial port via pyserial before running any other code, or restarting a program)

#procedure to turn off laser:

open GUI
INIT on COM4
ENABLE laser
DISABLE laser
close GUI

profit


'''



# TODO


# Also need to build in Voltmeter Communications and Serial COM error and debug reading (reads back from the laser)
# Also need to create GUI (dearpygui)

# ! WL target signifigant figures should be limited based on frequency resolution of laser.
def get_user_int(message:str):
    num_packets = input(message)
    if not num_packets.isdigit():
        print("Please input an integer") 
        get_user_int(message)
    else: return int(num_packets)

def get_user_float(message:str):
    response = input(message)
    try: number = float(response)
    except ValueError:
        print("Please input an floating point number") 
        get_user_float(message)
    return number
 
def check_user(message:str, N_abort=True):
    user_input = input(message).lower()
    if user_input == "y": 
        print("\n")
        return True
    elif user_input == "n": 
        if N_abort: 
            ser.close()
            sys.exit("User Ended Session")
        else: print("\n")
    else: 
        print("Please Input Y or N")
        check_user(message, N_abort)

sending_packets = check_user("Send Packets to Laser Y/N: ", N_abort=False)
if sending_packets:
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(port.device)  

    target_port = input("Input Target Port: ")

    ser = serial.Serial(port = target_port, 
                        baudrate = 9600, 
                        bytesize = serial.EIGHTBITS,
                        parity = serial.PARITY_NONE, 
                        timeout = 1) 
    print(f"Serial port {ser.name} opened successfully.")


START_INDEX = get_user_int("Start Index (int): ")
END_INDEX = get_user_int("End Index (int): ")
#INTERPOLATION_VALUE = get_user_int("Number of interpolated wavelengths between reference values (int): ")
INTERPOLATION_VALUE = 3
plot_choice = check_user("Plot DAC values Y/N: ", N_abort=False)

def main():
    
    #weird GUI scripting stuff I am messing with goes here
   
    #look for existing table first!
    table_list = glob.glob(f'**/DAC_Tables/DAC_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.csv', recursive=True)
    if table_list:
        path = table_list[0] #first entry that shows up. Shouldn't be duplicates anyway.
        print(f"Table already exists! Fetching data from: {path}")

    if not table_list or plot_choice:
        path = table.generate_DAC_table(interpolate_val=INTERPOLATION_VALUE, start_index=START_INDEX, end_index=END_INDEX, plot=plot_choice)

    DAC_list = table.get_DAC_arrays_from_table(path) #works!

    def val_to_hex(DAC_val): 
        msb = int('0x'+hex(DAC_val)[2:4], base=16)
        lsb = int('0x'+hex(DAC_val)[4:6], base=16)
        return [msb, lsb]

    packets = []
    for i in range(len(DAC_list[0])):
        fm_hex = val_to_hex(DAC_list[1][i])
        bm_hex = val_to_hex(DAC_list[2][i])
        ph_hex = val_to_hex(DAC_list[3][i])
        soa_hex = val_to_hex(DAC_list[4][i])
        target_wl = DAC_list[5][i]
        #print(target_wl)

        fm_packet =  bytes([(0x13)|(1 << 7), fm_hex[0], fm_hex[1], 0x00 ])
        bm_packet =  bytes([(0x12)|(1 << 7), bm_hex[0], bm_hex[1], 0x00 ])
        ph_packet =  bytes([(0x11)|(1 << 7), ph_hex[0], ph_hex[1], 0x00 ])
        soa_packet =  bytes([(0x14)|(1 << 7), soa_hex[0], soa_hex[1], 0x00 ])

        packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])
    '''
    with open(f"DBR/SERIAL_DEBUG/SERIAL_OUTPUT_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.txt", "w") as f: #currently this just shows the full serial byte list, not what we actually send
        f.write("SENDING: \n")
        for packet in packets:
            #print(packet)
            f.write(f'FM: {packet[0]}, BM: {packet[1]}, PH: {packet[2]}, SOA: {packet[3]} \n') #these are displayed using the UTF-8 format. 
    '''
    
    num_packets = 2 #this is how many bundles of 4 packets (each bundle has one DAC val for each type) will be sent to the laser
    delay = 2
    if not check_user("Scan over full Interpolated DAC table Y/N: ", N_abort=False):
        num_packets = get_user_int("Number of Wavelengths to scan over (int): ")

    else: num_packets = len(DAC_list[0])
    automatic = check_user("Scan automatically Y/N: ", N_abort=False)

    delay = 0
    if automatic:
        delay = get_user_float("Input Delay between packets: ")
   
    print(f"Preparing: {num_packets} Packets")

    for i in tqdm(range(num_packets)):
        #packet_index = random.randint(0,len(packets))
        packet_index = i

        print(f'Target: {packets[packet_index][4]}')
        print(f"FM:  {packets[packet_index][0]}")
        print(f"BM:  {packets[packet_index][1]}")
        print(f"PH:  {packets[packet_index][2]}")
        print(f"SOA: {packets[packet_index][3]}")
        
            #print(packets[packet_index][k])
        if not automatic: check_user("Proceed to Send Y/N: ")
        if automatic: 
            print(f"waiting {delay} second(s)...")
            time.sleep(delay)
        for j in range(4):
            if sending_packets: ser.write(packets[i][j])
            pass
        # Read 4-byte response per 4 packets sent?
        #simulate good response

        if sending_packets: response = ser.read(4)
        else: response = bytes([ 0x00, 0x00, 0x00, 0x01 ])
        print(f"Full Response: {response}")

        # Check and decode
        if len(response) == 4:
            reg = response[0]
            value_msb = response[1]
            value_lsb = response[2]
            status = response[3] 
        
            if status == 0x01: 
                #gain_value = (value_msb << 8) | value_lsb #reconstructs hex value that i had to split anyway for some reason.
                print(f"Status: {status} = all good \n")
            else:
                #dont know what these error codes look like. right now, any number other than 1 is an error
                print(f"Error: status code 0x{status:X}")
                sys.exit()
    
    if sending_packets: 
        print("Closing Serial port...")
        ser.close()
        print("Serial port closed.")
    print("END PROGRAM")
if __name__ == '__main__': main()
