# JAMES USHER 2026

import serial, sys, os, glob, time
import serial.tools.list_ports
from timeit import default_timer as timer
from tqdm import tqdm

import generate_table as table 
import helper_functions as helper

'''
#Procedure to turn on laser:

open GUI
INIT on COM4 probably
DOWNLOAD DEFAULT LUT -> 1627 nm DEFAULT STARTING WL
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
def laser_manual_scan():

    CWD = os.path.dirname(os.path.realpath(__file__))
    SENDING_PACKETS = helper.get_user_input(message="Send Packets to Laser Y/N: ", input_type="y/n")


    if SENDING_PACKETS:
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            print("{}: {} [{}]".format(port, desc, hwid))

        target_port = input("Input Target Port: ")

        ser = serial.Serial(port = target_port, 
                            baudrate = 9600, 
                            bytesize = serial.EIGHTBITS,
                            parity = serial.PARITY_NONE, 
                            timeout = 1) 
        print(f"Serial port {ser.name} opened successfully.")


    START_INDEX = helper.get_user_input(message="Start Index (int): ", input_type="int")
    END_INDEX = helper.get_user_input(message="End Index (int): ", input_type="int")
    INTERPOLATION_TYPE = helper.get_user_input(message="Interpolation Type ('linear'/'curve_fit'): ", input_type="str")
    if INTERPOLATION_TYPE not in ["linear", "curve_fit"]:
        INTERPOLATION_TYPE = helper.get_user_input(message="Please Input Interpolation Type ('linear'/'curve_fit'): ", input_type="str")
    INTERPOLATION_VALUE = helper.get_user_input(message="Interpolation Value (int): ", input_type="int")
    SANATIZE = helper.get_user_input(message="Sanatize Packets Y/N: ", input_type="y/n")
    
    PLOT_CHOICE = helper.get_user_input(message="Plot DAC values Y/N: ", input_type="y/n")
    PLOT_BOTH = helper.get_user_input(message="Plot Original values also Y/N: ", input_type="y/n")
    #look for existing table first
    if INTERPOLATION_TYPE == "linear": table_list = glob.glob(f'**/DAC_Tables/INTERP_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.csv', recursive=True)
    if INTERPOLATION_TYPE == "curve_fit": table_list = glob.glob(f'**/DAC_Tables/EXTRAP_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.csv', recursive=True)
    if table_list:
        path = table_list[0]
        print(f"Table already exists! Fetching data from: {path}")

    if not table_list or PLOT_CHOICE:
        path = table.generate_DAC_table(interpolate_type=INTERPOLATION_TYPE, 
                                        interpolate_val=INTERPOLATION_VALUE, 
                                        start_index=START_INDEX,
                                        end_index=END_INDEX, 
                                        plot=PLOT_CHOICE,
                                        plot_both=PLOT_BOTH)
        
    DAC_list = table.get_DAC_arrays_from_table(path, False)     

    packets = []
    for i in range(len(DAC_list[0])):
        fm_val = DAC_list[1][i]
        bm_val = DAC_list[2][i]
        ph_val = DAC_list[3][i]
        soa_val = DAC_list[4][i]
        wl_val = DAC_list[5][i]

        if SANATIZE:
            #SANATIZE PACKETS HERE
           

            values = [fm_val, bm_val, ph_val, soa_val, wl_val]
            names = ["FM", "BM", "PH", "SOA", "WL"]
            maximums = [57954, 43418, 17448, 45527, 1672.4955]
            minimums = [668, 982, 2496, 14319, 1627.5]
        
            for val in values:
                j = values.index(val) 
                if val > maximums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} > {maximums[j]}" )
                if val < minimums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} < {minimums[j]}" )

        fm_hex = helper.val_to_split_hex(fm_val)
        bm_hex = helper.val_to_split_hex(bm_val)
        ph_hex = helper.val_to_split_hex(ph_val)
        soa_hex = helper.val_to_split_hex(soa_val)
        target_wl = DAC_list[5][i]
        #print(target_wl)

        fm_packet =  bytes([(0x13)|(1 << 7), fm_hex[0], fm_hex[1], 0x00 ])
        bm_packet =  bytes([(0x12)|(1 << 7), bm_hex[0], bm_hex[1], 0x00 ])
        ph_packet =  bytes([(0x11)|(1 << 7), ph_hex[0], ph_hex[1], 0x00 ])
        soa_packet =  bytes([(0x14)|(1 << 7), soa_hex[0], soa_hex[1], 0x00 ])

        packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])
    

    if not helper.get_user_input(message="Scan over full Interpolated DAC table Y/N: ", input_type="y/n"):
        num_packets = helper.get_user_input(message="Number of Wavelengths to scan over (int): ", input_type="int")

    else: num_packets = len(DAC_list[0])
    automatic = helper.get_user_input(message="Scan automatically Y/N: ", input_type="y/n")

    delay = 0
    if automatic: delay = helper.get_user_input(message="Input Delay between packets: ", input_type="float")
   
    print(f"Preparing: {num_packets} Packets")

    for i in tqdm(range(num_packets)):

        print(f'Target: {packets[i][4]}')
        print(f"FM:  {packets[i][0]}")
        print(f"BM:  {packets[i][1]}")
        print(f"PH:  {packets[i][2]}")
        print(f"SOA: {packets[i][3]}")
        
        if not automatic and not helper.get_user_input("Proceed to Send Y/N: ", input_type="y/n"):
                print("Closing Serial port...")
                ser.close()
                print("Serial port closed.")
                sys.exit()
        if automatic: 
            print(f"waiting {delay} second(s)...")
            time.sleep(delay)

        if SENDING_PACKETS:

            for j in range(4): 
                ser.write(packets[i][j])

        #   Read 4-byte response per 4 packets sent?
      
        if SENDING_PACKETS: 
            start = timer()
            response = ser.read(4)
            end = timer()
            print(f"Response Delay: {end - start}s")

        #   simulate good response
        else: response = bytes([ 0x00, 0x00, 0x00, 0x01 ])
        print(f"Full Response: {response}")

        #   these are not implemented in the documentation for the Instatune
        reg = response[0]
        value_msb = response[1]
        value_lsb = response[2]

        status = response[3] 
        if status == 0x01: 
            #   gain_value = (value_msb << 8) | value_lsb #reconstructs hex value that i had to split anyway for some reason.
            print(f"Status: {status} = all good \n")
        else:
            #   dont know what these error codes look like. right now, any number other than 1 is an error
            print(f"Error: status code 0x{status:X}")
            sys.exit()

    if SENDING_PACKETS: 
        print("Closing Serial port...")
        ser.close()
        print("Serial port closed.")


def laser_auto_scan(
        START_INDEX = 0, 
        END_INDEX = 10000, 
        INTERPOLATION_TYPE = "linear", 
        INTERPOLATION_VALUE = 3, 
        PLOT_CHOICE = False, 
        delay = 0.1, 
        SENDING_PACKETS: bool = True, 
        SANATIZE: bool = True):

    CWD = os.path.dirname(os.path.realpath(__file__))

    if SENDING_PACKETS:
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            print("{}: {} [{}]".format(port, desc, hwid)) 

        target_port = input("Input Target Port: ")

        ser = serial.Serial(port = target_port, 
                            baudrate = 9600, 
                            bytesize = serial.EIGHTBITS,
                            parity = serial.PARITY_NONE, 
                            timeout = 1) 
        print(f"Serial port {ser.name} opened successfully.")

    #look for existing table first
    if INTERPOLATION_TYPE == "linear": table_list = glob.glob(f'**/DAC_Tables/INTERP_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.csv', recursive=True)
    if INTERPOLATION_TYPE == "curve_fit": table_list = glob.glob(f'**/DAC_Tables/EXTRAP_{INTERPOLATION_VALUE, START_INDEX, END_INDEX}.csv', recursive=True)

    if table_list:
        path = table_list[0]
        print(f"Table already exists! Fetching data from: {path}")

    if not table_list or PLOT_CHOICE:
        path = table.generate_DAC_table(interpolate_type=INTERPOLATION_TYPE, interpolate_val=INTERPOLATION_VALUE, start_index=START_INDEX, end_index=END_INDEX, plot=PLOT_CHOICE, plot_both=PLOT_BOTH)

    DAC_list = table.get_DAC_arrays_from_table(path) 

    packets = []
    
    for i in range(len(DAC_list[0])):
        fm_val = DAC_list[1][i]
        bm_val = DAC_list[2][i]
        ph_val = DAC_list[3][i]
        soa_val = DAC_list[4][i]

#%%     SANATIZE PACKETS HERE
        if SANATIZE:
        

            values = [fm_val, bm_val, ph_val, soa_val]
            names = ["FM", "BM", "PH", "SOA"]
            maximums = [57954, 43418, 17448, 45527]
            minimums = [668, 982, 2496, 14319]
        
            for val in values:
                j = values.index(val) 
                if val > maximums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} > {maximums[j]}" )
                if val < minimums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} < {minimums[j]}" )

        #   END OF SANATIZE 
       
        fm_hex = helper.val_to_split_hex(fm_val)
        bm_hex = helper.val_to_split_hex(bm_val)
        ph_hex = helper.val_to_split_hex(ph_val)
        soa_hex = helper.val_to_split_hex(soa_val)
        target_wl = DAC_list[5][i]

        fm_packet =  bytes([(0x13)|(1 << 7), fm_hex[0], fm_hex[1], 0x00 ])
        bm_packet =  bytes([(0x12)|(1 << 7), bm_hex[0], bm_hex[1], 0x00 ])
        ph_packet =  bytes([(0x11)|(1 << 7), ph_hex[0], ph_hex[1], 0x00 ])
        soa_packet =  bytes([(0x14)|(1 << 7), soa_hex[0], soa_hex[1], 0x00 ])

        packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])

    num_packets = len(DAC_list[0])
    print(f"Preparing: {num_packets} Packets")

    for i in tqdm(range(num_packets)):

        print(f'Target: {packets[i][4]}')
        print(f"FM:  {packets[i][0]}")
        print(f"BM:  {packets[i][1]}")
        print(f"PH:  {packets[i][2]}")
        print(f"SOA: {packets[i][3]}")
      
        print(f"waiting {delay} second(s)...")
        time.sleep(delay)

        if SENDING_PACKETS: 
        # SEND
            for j in range(4): ser.write(packets[i][j])
    
        # RESPONSE
            start = timer()
            response = ser.read(4)
            end = timer()
            print(f"Response Delay: {end - start}s")

        #   simulate good response
        else: response = bytes([ 0x00, 0x00, 0x00, 0x01 ])
        print(f"Full Response: {response}")

        #   these are not implemented in the documentation for the Instatune
        if response != b'': 
            reg = response[0]
            value_msb = response[1]
            value_lsb = response[2]

            status = response[3] 
            if status == 0x01: 
                print(f"Status: {status} = all good \n")
            else:
                print(f"Error: status code 0x{status:X}")
                sys.exit()
        else: 
            print("Response Empty")

    if SENDING_PACKETS: 
        print("Closing Serial port...")
        ser.close()
        print("Serial port closed.")


