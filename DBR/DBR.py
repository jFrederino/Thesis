# JAMES USHER 2026

import serial, sys, os, glob, time
import serial.tools.list_ports
from timeit import default_timer as timer
from tqdm import tqdm
import pyvisa
import csv 

#import DBR.generate_table_old as table 
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
class DBR_Spectrometer:
    '''
    DBR Spectrometer Class Object

    Attributes
    ----------

    start_index (int) = 0 : Start index of DAC table (within original 10,000 value LUT).
    end_index (int) = 0 : End index of DAC table.
    interpolation_type (str) = "linear" : either "linear" or "curve_fit" method of DAC value interpolation/extrapolation.
    interpolation_value (int) = 3 : Number of new DAC values generated between existing points in LUT
    plot_choice (bool) = False : Decides whether to plot with matplotlib or not.
    plot_both (bool) = False : Decides whether or not to plot original LUT values under newly generated values.
    delay (float) = 0.1 : Delay in seconds between packets sent via serial port. 
    sending_packets (bool) = True : Decides whether to send packets to the Instatune Module. 
    sanatize (bool) = True : Decides whether to check DAC table values for outliers outside of accepted range.
    log_voltage (bool) = False : Decides whether to setup Voltmeter and log voltages via USB.
    '''
    def __init__(self, mode: str = "manual", start_index: int = 0, end_index: int = 9999, interpolation_type: str = "linear", 
        interpolation_value:int = 3, plot_choice: bool = False, plot_both: bool = False,
        delay: float = 0.1, sending_packets: bool = True, sanatize: bool = True, log_voltage: bool = False):
            self.mode = mode
            self.start_index = start_index
            self.end_index = end_index
            self.interpolation_type = interpolation_type
            self.interpolation_value = interpolation_value
            self.plot_choice = plot_choice
            self.plot_both = plot_both
            self.delay = delay
            self.sending_packets = sending_packets
            self.sanatize = sanatize
            self.log_voltage = log_voltage
            self._voltage_data = []
            self.laser_on = False
            self.laser_connected = False

    def toggle(self): #I WIN !!!
        if not self.laser_connected: 
            self._connect_to_laser("COM4")
            self.laser_connected = True
        '''
        SOURCE CODE DECOMPILED FROM GUI

        if (((Control)btnLaserEnableDisable).Text == "Enable Laser")
            {
                ushort regData = 0;
                hostComm.WriteRegister(39, regData);
                ((Control)btnLaserEnableDisable).Text = "Disable Laser";
                hostComm.WriteRegister(16, Convert.ToUInt16(40959));
                regData = 3840;
                hostComm.WriteRegister(39, regData);
            }
            else
            {
                ((Control)btnLaserEnableDisable).Text = "Enable Laser";
                ushort regData = 0;
                hostComm.WriteRegister(39, regData);
                hostComm.WriteRegister(16, Convert.ToUInt16(0));
            }
        }
        '''
        _ON = [bytes([167, 0, 0, 0]), bytes([144, 255, 0, 0]), bytes([167, 0, 0, 0])]
        _OFF = [bytes([167, 0, 0, 0]), bytes([144, 0, 0, 0]), bytes([167, 0, 0, 0])]

        if self.laser_on: 
            for packet in _OFF: 
                self._laser_serial.write(packet)
                self._read_response()
            self.laser_on = False
        else:
            for packet in _ON: 
                self._laser_serial.write(packet)
                self._read_response()
            self.set_laser_target(fm_val=11425, bm_val=4698, ph_val=17448, soa_val=24222)
            self.laser_on = True

    def set_laser_target(self, fm_val:int, bm_val:int, ph_val:int, soa_val:int):
        try: self._laser_serial
        except NameError: self._connect_to_laser("COM4")

        fm_hex = helper.val_to_split_hex(fm_val)
        bm_hex = helper.val_to_split_hex(bm_val)
        ph_hex = helper.val_to_split_hex(ph_val)
        soa_hex = helper.val_to_split_hex(soa_val)

        fm_packet =  bytes([(0x13)|(1 << 7), fm_hex[0], fm_hex[1], 0x00 ])
        bm_packet =  bytes([(0x12)|(1 << 7), bm_hex[0], bm_hex[1], 0x00 ])
        ph_packet =  bytes([(0x11)|(1 << 7), ph_hex[0], ph_hex[1], 0x00 ])
        soa_packet =  bytes([(0x14)|(1 << 7), soa_hex[0], soa_hex[1], 0x00 ])

        packets = [fm_packet, bm_packet, ph_packet, soa_packet]
        for packet in packets:
            self._laser_serial.write(packet)
            self._read_response()
           
    def _get_interpolation_type(self, start_message):
            self.interpolation_type = helper.get_user_input(message = start_message, input_type="str")
            if self.interpolation_type not in ["linear", "curve_fit"]:
                self._get_interpolation_type(start_message="Please Input Interpolation Type ('linear'/'curve_fit'): ")
            else: return self.interpolation_type

    def _connect_to_laser(self, target_port: str):
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            print("{} : {} [{}]".format(port, desc, hwid))

        self._laser_serial = serial.Serial(
            port = target_port, 
            baudrate = 9600, 
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_NONE, 
            timeout = 1) 
        
        print(f"Serial port {self._laser_serial.name} opened successfully.")

    def _write_voltage(self):
        CWD = os.path.dirname(os.path.realpath(__file__))
        if self.interpolate_type == "linear":
            new_table_path = CWD+f'/Voltage_Data/INTERP_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        if self.interpolate_type == "curve_fit":
            new_table_path = CWD+f'/Voltage_Data/EXTRAP_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        with open(new_table_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|')
            writer.writerow(['IDX','Voltage'])
            for row in range(0, len(self._voltage_data)):
                writer.writerow([row, self._voltage_data[row]])

    def _read_response(self):
                response = self._laser_serial.read(4)
                tqdm.write(f"Full Response: {response}")

                reg = response[0]
                value_msb = response[1]
                value_lsb = response[2]
                status = response[3]

                name = "unknown"
                match reg:
                    case 0x13: name = "FM"
                    case 0x12: name = "BM"
                    case 0x11: name = "PH"
                    case 0x14: name = "SOA"
                
                if status == 0x01:
                    gain_value = (value_msb << 8) | value_lsb
                    print(f"{name} Current DAC = {gain_value}")
                    if self.log_voltage: 
                        self._voltage_data.append(self._read_voltage())
                else:
                    print(f"Error: status code 0x{status:X}")

                if response != b'': 
                    reg = response[0]
                    value_msb = response[1]
                    value_lsb = response[2]

                    status = response[3] 
                    if status == 0x01: 
                        tqdm.write(f"Status: {status} = all good \n")
                        
                    else:
                        print(f"Error: status code 0x{status:X}")
                        self._laser_serial.close()
                        sys.exit()
                else: 
                    print("Response Empty")


    def _send_packets(self, DAC_list: list[list], manual: bool = True):
        '''
        Sends Packets to Instatune Laser Module.
        '''
        packets = []
        for i in range(len(DAC_list[0])):
            fm_val = DAC_list[1][i]
            bm_val = DAC_list[2][i]
            ph_val = DAC_list[3][i]
            soa_val = DAC_list[4][i]
            target_wl = DAC_list[5][i]

            #   SANATIZE PACKETS HERE
            if self.sanatize:
                #as far as i am aware, the DAC values can be anywhere between 0 and 65535 according to the manual (the unsigned 16-bit integer limit) 
                values = [fm_val, bm_val, ph_val, soa_val]
                names = ["FM", "BM", "PH", "SOA"]
                maximums = [57954, 43418, 17448, 45527] #max from LUT 0v0
                minimums = [668, 982, 2496, 14319] #min from LUT 0v0
            
                for val in values:
                    j = values.index(val) 
                    if val > maximums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} > {maximums[j]}" )
                    if val < minimums[j]: raise Exception(f"{names[j]} DAC value outside of acceptable range: {val} < {minimums[j]}" )
        
            fm_hex = helper.val_to_split_hex(fm_val)
            bm_hex = helper.val_to_split_hex(bm_val)
            ph_hex = helper.val_to_split_hex(ph_val)
            soa_hex = helper.val_to_split_hex(soa_val)
 
            #also should check hex values here
            fm_packet =  bytes([(0x13)|(1 << 7), fm_hex[0], fm_hex[1], 0x00 ])
            bm_packet =  bytes([(0x12)|(1 << 7), bm_hex[0], bm_hex[1], 0x00 ])
            ph_packet =  bytes([(0x11)|(1 << 7), ph_hex[0], ph_hex[1], 0x00 ])
            soa_packet =  bytes([(0x14)|(1 << 7), soa_hex[0], soa_hex[1], 0x00 ])

            packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])

        num_packets = len(DAC_list[0])

        if manual:
            if not helper.get_user_input(message="Scan over full Interpolated DAC table Y/N: ", input_type="y/n"):
                num_packets = helper.get_user_input(message="Number of Wavelengths to scan over (int): ", input_type="int")

        else: num_packets = len(DAC_list[0])

        if manual:
            automatic = helper.get_user_input(message="Scan automatically Y/N: ", input_type="y/n")

        if automatic: self.delay = helper.get_user_input(message="Input Delay between packets: ", input_type="float")

        print(f"Preparing: {num_packets} Packets")

        for i in tqdm(range(num_packets)):
            tqdm.write(f'Target: {packets[i][4]}')
            tqdm.write(f"FM:  {packets[i][0]}")
            tqdm.write(f"BM:  {packets[i][1]}")
            tqdm.write(f"PH:  {packets[i][2]}")
            tqdm.write(f"SOA: {packets[i][3]}")
        
            if manual:
                if not automatic and not helper.get_user_input("Proceed to Send Y/N: ", input_type="y/n"):
                    tqdm.write("Closing Serial port...")
                    self._laser_serial.close()
                    tqdm.write("Serial port closed.")
                    sys.exit()
            
            tqdm.write(f"waiting {self.delay} second(s)...")
            time.sleep(self.delay)
            simulate_response = self.sending_packets
            if self.sending_packets: 
                for j in range(4): 
                    self._laser_serial.write(packets[i][0])
                    self._read_response()
                    self._laser_serial.write(packets[i][1])
                    self._read_response()
                    self._laser_serial.write(packets[i][2])
                    self._read_response()
                    self._laser_serial.write(packets[i][3])
                    self._read_response()

            
    def _manual_setup(self):
        '''
        Allows for configuration of DBR Spectrometer Settings via command line.
        '''
        self.sending_packets = helper.get_user_input(message="Send Packets to Laser Y/N: ", input_type="y/n")
        if self.sending_packets: self._connect_to_laser(target_port = helper.get_user_input(message="Input Target Port: ", input_type="str"))

        self.log_voltage = helper.get_user_input("Log Voltage Y/N: ", input_type="y/n")
        if self.log_voltage: 
            rm = pyvisa.ResourceManager()
            print(rm.list_resources())
            #USB_address = "USB0::0x2A8D::0x1601::MY60077980::INSR"
            USB_address = helper.get_user_input(message="Voltmeter USB Address: ", input_type="str")
            self._voltmeter_inst = rm.open_resource(USB_address)

        self.start_index = helper.get_user_input(message="Start Index (int): ", input_type="int")
        self.end_index = helper.get_user_input(message="End Index (int): ", input_type="int")
        self.interpolation_type = self._get_interpolation_type(start_message="Interpolation Type ('linear'/'curve_fit'): ")
        self.interpolation_value = helper.get_user_input(message="Interpolation Value (int): ", input_type="int")
        self.sanatize = helper.get_user_input(message="Sanatize Packets Y/N: ", input_type="y/n")
        self.plot_choice = helper.get_user_input(message="Plot DAC values Y/N: ", input_type="y/n")
        self.plot_both = helper.get_user_input(message="Plot Original values also Y/N: ", input_type="y/n")

    def _read_voltage(self) -> list:
        '''
        Measures voltage via connected Voltmeter
        '''
        try: self._voltmeter_inst
        except NameError: print("No Voltmeter Instance Found")
        
        print(self._voltmeter_inst.query("*IDN?"))
        print(self._voltmeter_inst.query("MEAS:VOLT:DC? 0.100,0.001"))

        return [self._voltmeter_inst.query("*IDN?"), self._voltmeter_inst.query("MEAS:VOLT:DC? 0.100,0.001")]
    
    def scan(self, mode="manual"):
        '''
        DBR Spectrometer scans through wavelengths generated via DAC values. Tables can be generated with interpolated or extrapolated values. Manual Setup via command line allows for sending individual packets one at a time. 
        '''
        self.mode = mode

        if self.mode == "manual":
            _manual = True
            self._manual_setup()
        elif self.mode == "auto":
            _manual = False
            if self.sending_packets:
                try: self._laser_serial
                except NameError: self._connect_to_laser(target_port = helper.get_user_input(message="Input Target Port: ", input_type="str"))
        else:
            raise Exception("Mode is neither 'manual' nor 'auto'. ")
    
        CWD = os.path.dirname(os.path.realpath(__file__))

        if self.interpolation_type == "linear": 
            table_list = glob.glob(f'**/DAC_Tables/INTERP_{self.interpolation_type, self.start_index, self.end_index}.csv', recursive=True)

        if self.interpolation_type == "curve_fit": 
            table_list = glob.glob(f'**/DAC_Tables/EXTRAP_{self.interpolation_type, self.start_index, self.end_index}.csv', recursive=True)
    
        if table_list:
            path = table_list[0]
            print(f"Table already exists! Fetching data from: {path}")

        if not table_list or self.plot_choice:

            DAC_Table = table.DAC_Table(
                interpolate_type=self.interpolation_type, interpolate_value=self.interpolation_value, 
                start_index=self.start_index, end_index=self.end_index)
        
            path = DAC_Table.generate_DAC_table(plot_choice=self.plot_choice, plot_both=self.plot_both) #also plots if enabled

        DAC_list = DAC_Table.get_DAC_arrays(path)  #read values from new table
        self._send_packets(DAC_list, manual=_manual)

        if self.sending_packets: 
            print("Closing Serial port...")
            self._laser_serial.close()
            print("Serial port closed.")

   

