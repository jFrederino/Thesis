# JAMES USHER 2026

import serial, sys, os, glob, time
import serial.tools.list_ports
from timeit import default_timer as timer
from tqdm import tqdm
import pyvisa
import csv 
import generate_table as table
import helper_functions as helper

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
    log_voltage (bool) = False : Decides whether to setup Voltmeter and log voltages via USB.
    '''
    def __init__(self, mode: str = "manual", start_index: int = 0, end_index: int = 9999, interpolation_type: str = "linear", 
        interpolation_value:int = 3, plot_choice: bool = False, plot_both: bool = False,
        delay: float = 0.1, sending_packets: bool = True, sanatize: bool = True, log_voltage: bool = False, gui:bool = False):
            self.mode = mode
            self.start_index = start_index
            self.end_index = end_index
            self.interpolation_type = interpolation_type
            self.interpolation_value = interpolation_value
            self.plot_choice = plot_choice
            self.plot_both = plot_both
            self.delay = delay
            self.sending_packets = sending_packets
            #self.sanatize = sanatize
            self.log_voltage = log_voltage
            self.gui = gui

            self._voltage_data = []
            self._laser_on = False
            self._laser_connected = False
            self._default_serial_port = "COM4"

    def enable(self): 
        '''
        Turns the laser output on. Connects to default Serial Port {self._default_serial_port} if not connected. Defaults to 1627.5 nm output.

        '''
        self._connect_to_laser(self._default_serial_port)

        #These magic numbers are from the decompiled enable/disable code the GUI uses. Registers are undocumented in manual.
        #SWEEP = 0                      #GAIN = 255
        _ON = [bytes([167, 0, 0, 0]), bytes([144, 255, 0, 0])]


        if self._laser_on: print("laser is already on.")
        else:
            for packet in _ON: 
                self._laser_serial.write(packet)
                self._read_response()

            self.set_laser_target(fm_val=11425, bm_val=4698, ph_val=17448, soa_val=24222)
            self._laser_on = True

    def disable(self): 
        '''
        Turns the laser output off. Does NOT disconnect from Serial Connection.

        '''
        self._connect_to_laser(self._default_serial_port)

        #SWEEP = 0                      #GAIN = 0
        _OFF = [bytes([167, 0, 0, 0]), bytes([144, 0, 0, 0])]

        if self._laser_on: 
            for packet in _OFF: 
                self._laser_serial.write(packet)
                self._read_response()
            self._laser_on = False

        else: print("Laser is already off.")

    def set_default_serial_port(self, port_name:str):
        self._default_serial_port = port_name
        print(f"Default Serial Port set to: {self._default_serial_port}")

    def make_packet(self, DAC_type:str, value:int) -> bytes:
        '''
        Creates DAC packet (bytes object) that can be sent to the Laser immediately. Also sanatizes given values
        '''
        maximum = minimum = 0
        match DAC_type:
            case "FM": 
                register = (0x13)|(1 << 7)
                maximum = 57954
                minimum = 668
            case "BM": 
                register = (0x12)|(1 << 7)
                maximum =  43418
                minimum = 982
            case "PH":
                register = (0x11)|(1 << 7)
                maximum =  17448
                minimum = 2496
            case "SOA": 
                register = (0x14)|(1 << 7)
                maximum =  45527
                minimum = 14319

        if value > maximum: raise Exception(f"{DAC_type} value outside of acceptable range: {value} > {maximum}" )
        if value < minimum: raise Exception(f"{DAC_type} DAC value outside of acceptable range: {value} < {minimum}" )

        msb, lsb = helper.val_to_split_hex(value)

        return bytes([register, int(msb, 16), int(lsb, 16), 0x00])
    
    def _make_packets_list(self, DAC_list:list[list]) -> list[list]:
        '''
        Given DAC LUT will produce list containing all cooresponding packets, bundled with Target Wavelengths.
        '''
        packets = []
        for i in range(len(DAC_list[0])):
            fm_packet = self.make_packet("FM", DAC_list[1][i])
            bm_packet = self.make_packet("BM", DAC_list[2][i])
            ph_packet = self.make_packet("PH", DAC_list[3][i])
            soa_packet = self.make_packet("SOA", DAC_list[4][i])
            target_wl = DAC_list[5][i]

            packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])

        return packets

    def set_laser_target(self, fm_val:int, bm_val:int, ph_val:int, soa_val:int):
        '''
        Will create and send packets to update laser output to wavelegnth cooresponding tp given DAC values.
        '''
        if not self._laser_connected: print("Laser not connected.")
        else:
            fm_packet = self.make_packet("FM", fm_val)
            bm_packet = self.make_packet("BM", bm_val)
            ph_packet = self.make_packet("PH", ph_val)
            soa_packet = self.make_packet("SOA", soa_val)
            packets = [fm_packet, bm_packet, ph_packet, soa_packet]

            for packet in packets:
                self._laser_serial.write(packet)
                self._read_response()
            
    def _get_interpolation_type(self, start_message):
            self.interpolation_type = helper.get_user_input(message = start_message, input_type="str")
            if self.interpolation_type not in ["linear", "curve_fit"]:
                self._get_interpolation_type(start_message="Please Input Interpolation Type ('linear'/'curve_fit'): ")
            else: return self.interpolation_type

    def _connect_to_laser(self, target_port:str):
        if self._laser_connected: print(f"Laser is already connected to {self._laser_serial.name}")
        else:
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                print("{} : {} [{}]".format(port, desc, hwid))

            self._laser_serial = serial.Serial(
                port = "COM4", 
                baudrate = 9600, 
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE, 
                timeout = 1) 
            
            print(f"Serial port {self._laser_serial.name} opened successfully.")
            self._laser_connected = True

    def _disconnect_from_laser(self):
        if not self._laser_connected: print("Laser is already disconnected. ")
        print("Closing Serial Port...")
        name = self._laser_serial.name
        self._laser_serial.close()
        print(f"Serial Port {name} Closed.")

    def _write_voltage(self):
        CWD = os.path.dirname(os.path.realpath(__file__))
        if self.interpolation_type == "linear":
            new_table_path = CWD+f'/Voltage_Data/INTERP_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        if self.interpolation_type == "curve_fit":
            new_table_path = CWD+f'/Voltage_Data/EXTRAP_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        with open(new_table_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|')
            writer.writerow(['IDX','Voltage'])
            for row in range(0, len(self._voltage_data)):
                writer.writerow([row, self._voltage_data[row]])

    def _read_response(self):
        if not self._laser_connected:
            raise Exception("Laser not connected.")
        else: 
            response = self._laser_serial.read(4)
            tqdm.write(f"Full Response: {response}")

            reg = response[0]
            value_msb = response[1]
            value_lsb = response[2]
            status = response[3]

            name = "Unknown"
            match reg:
                case 0x00: name = "Firmware Revision"
                case 0x01: name = "Protocol Version"
                case 0x02: name = "Product Identifier"
                case 0x0A: name = "Reserved"
                case 0x0B: name = "TEC Current" #32767 indicates 0 mA
                case 0x0C: name = "Laser Temperature Set Point" #given in centi-Celsius
                case 0x0D: name = "Laser Temperature Operating Point" #also given in centi-Celsius

                #This seems to be a current that doesnt change as the laser sweeps through the LUT, so it should not affect wavelength, probably.
                case 0x10: name = "GAIN Current DAC"
                #These are the controller registers we actually write to.
                case 0x13: name = "FM"
                case 0x12: name = "BM"
                case 0x11: name = "PH"
                case 0x14: name = "SOA"

                #These relate to the Laser's built in LUT Sweep functionality, which is currently not being used in this project.
                case 0x1E: name = "LUT Prepare Write"
                case 0x1F: name = "LUT Write Point" #automatically incremented after write
                case 0x20: name = "LUT Start Index"
                case 0x21: name = "LUT Length"
                case 0x27: name = "Sweep Configuration"
                case 0x28: name = "Step Sync Delay"
                case 0x29: name = "Step Period"

            status_message = "Unknown"
            match status:
                case 0x01:
                    status_message = "Command Executed, Response Data Valid: "
                    tqdm.write(status_message)
                    gain_value = (value_msb << 8) | value_lsb
                    tqdm.write(f"{name} DAC reads as: {gain_value}")
                    
                case 0x02: status_message = "Register not recognized. "
                case 0x03: status_message = "Register is Read Only. "
                case 0x04: status_message = "Command could not be executed. "
                case 0x05: status_message = "Value out of range. "
            if status != 0x01: 
                print(f"Error: status code 0x{status:X}")
                print(status_message)
                self._laser_serial.close()
                sys.exit()
                
    def _send_packets(self, DAC_list: list[list], manual: bool = True):
        '''
        Sends Packets to Instatune Laser Module.
        '''
        num_packets = len(DAC_list[0])
        print(num_packets)

        if manual:
            if not helper.get_user_input(message="Scan over full Interpolated DAC table Y/N: ", input_type="y/n"):
                num_packets = helper.get_user_input(message="Number of Wavelengths to scan over (int): ", input_type="int")

        if manual:
            automatic = helper.get_user_input(message="Scan automatically Y/N: ", input_type="y/n")
            if automatic: self.delay = helper.get_user_input(message="Input Delay between packets: ", input_type="float")

        print(f"Preparing: {num_packets} Packets")

        packets = self._make_packets_list(DAC_list)

        for i in tqdm(range(len(packets))):
            tqdm.write(f'Target: {packets[i][4]}')
            tqdm.write(f"FM:  {packets[i][0]}")
            tqdm.write(f"BM:  {packets[i][1]}")
            tqdm.write(f"PH:  {packets[i][2]}")
            tqdm.write(f"SOA: {packets[i][3]}")
        
            if manual:
                if not automatic and not helper.get_user_input("Proceed to Send Y/N: ", input_type="y/n"):
                    self._disconnect_from_laser()
            
            tqdm.write(f"waiting {self.delay} second(s)...")
            time.sleep(self.delay)

            if self.sending_packets: 
                for j in range(4): 
                    self._laser_serial.write(packets[i][j])
                    self._read_response()

                if self.log_voltage: 
                    self._voltage_data.append(self._read_voltage())

            else: 
                fake_response = bytes([0,0,0,1])
                for j in range(4): 
                    tqdm.write(fake_response)
                    tqdm.write(f"Status: {1} = all good \n")

                if self.log_voltage: 
                    self._voltage_data.append(self._read_voltage())
            
    def _manual_setup(self):
        '''
        Allows for configuration of DBR Spectrometer Settings via command line.
        '''
        self.sending_packets = helper.get_user_input(message="Send Packets to Laser Y/N: ", input_type="y/n")
        if self.sending_packets: 
            if not self._laser_connected: 
                self._connect_to_laser(target_port = helper.get_user_input(message="Input Target Port: ", input_type="str"))

        self.log_voltage = helper.get_user_input("Log Voltage Y/N: ", input_type="y/n")
        if self.log_voltage: 
            rm = pyvisa.ResourceManager()
            print(rm.list_resources())
            #USB_address = "USB0::0x2A8D::0x1601::MY60077980::INSR"
            #USB_address = helper.get_user_input(message="Voltmeter USB Address: ", input_type="str")
            self._voltmeter_inst = rm.open_resource("USB0::0x2A8D::0x1601::MY60077980::INSTR")

        self.start_index = helper.get_user_input(message="Start Index (int): ", input_type="int")
        self.end_index = helper.get_user_input(message="End Index (int): ", input_type="int")
        self.interpolation_type = self._get_interpolation_type(start_message="Interpolation Type ('linear'/'curve_fit'): ")
        self.interpolation_value = helper.get_user_input(message="Interpolation Value (int): ", input_type="int")
        #self.sanatize = helper.get_user_input(message="Sanatize Packets Y/N: ", input_type="y/n")
        self.plot_choice = helper.get_user_input(message="Plot DAC values Y/N: ", input_type="y/n")
        self.plot_both = helper.get_user_input(message="Plot Original values also Y/N: ", input_type="y/n")

        if helper.get_user_input("Toggle Laser On Y/N: ", input_type="y/n"): self.enable()

    def _read_voltage(self) -> float:
        '''
        Measures voltage via connected Voltmeter
        '''
        try: self._voltmeter_inst
        except: 
            print("No Voltmeter Instance Found")
            rm = pyvisa.ResourceManager()
            print(rm.list_resources())
            self._voltmeter_inst = rm.open_resource("USB0::0x2A8D::0x1601::MY60077980::INSTR")
            print(self._voltmeter_inst.query("*IDN?"))
        
        #print(self._voltmeter_inst.query("MEAS:VOLT:DC? 0.100,0.001"))
        return float(self._voltmeter_inst.query("MEAS:VOLT:DC? 0.100,0.001"))
    
    def get_table(self):
        if self.interpolation_type == "linear": 
            table_list = glob.glob(f'**/DAC_Tables/INTERP_{self.interpolation_type, self.start_index, self.end_index}.csv', recursive=True)

        if self.interpolation_type == "curve_fit": 
            table_list = glob.glob(f'**/DAC_Tables/EXTRAP_{self.interpolation_type, self.start_index, self.end_index}.csv', recursive=True)

        if not table_list or self.plot_choice:

            DAC_Table = table.DAC_Table(
                interpolate_type=self.interpolation_type, interpolate_value=self.interpolation_value, 
                start_index=self.start_index, end_index=self.end_index)
        
            path = DAC_Table.generate_DAC_table(plot_choice=self.plot_choice, plot_both=self.plot_both) #also plots if enabled
        
        DAC_list = DAC_Table.get_DAC_arrays(path)  #read values from new table
        return DAC_list

    def scan(self, mode="manual"):
        '''
        DBR Spectrometer scans through wavelengths generated via DAC values. 
        Tables can be generated with interpolated or extrapolated values. 
        Manual Setup via command line allows for sending individual packets one at a time. 
        '''
        if self._laser_on:
            print("disabling laser")
            self.disable()

        self.mode = mode

        if self.mode == "manual": 
            self._manual_setup()
        elif self.mode == "auto":
            if self.sending_packets:
                if not self._laser_connected: 
                    self._connect_to_laser(target_port = helper.get_user_input(message="Input Target Port: ", input_type="str"))
                if not self._laser_on: self.enable()
        else:
            raise Exception("Mode is neither 'manual' nor 'auto'. ")
        
        CWD = os.path.dirname(os.path.realpath(__file__))

        DAC_list = self.get_table()  #read values from new table

        self._send_packets(DAC_list=DAC_list, manual=self.mode)
        self._write_voltage()
        self._disconnect_from_laser()
            

   

