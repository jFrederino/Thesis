# JAMES USHER 2026
import time, threading, dearpygui.dearpygui as dpg, dearpygui_ext.logger as dpg_logger, numpy as np
import sys, os, stat, serial
import serial.tools.list_ports
import screeninfo
from dearpygui_ext.themes import create_theme_imgui_light
import dearpygui_extend as dpge
import random
import matplotlib.pyplot as plt
import matplotlib
from types import FunctionType
import Spectrometer as dbr
import generate_table as table
import pyvisa

from labjack import ljm
import socket
import struct
from pathlib import Path
from datetime import datetime
import csv
import shutil

class GUI_Controller:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger_on: bool = True #if false, most class methods will not print update statements in logger in the GUI. some will still print: (Serial and Voltmeter connection info, etc.)

        # scan control tracking
        self.packet_delay: float = 0.0
        self.settle_delay: float = 0.0
        self.scan_tracker = 1627.5 #x value of scan tracker line on DAC plot, and table index.
        self.scan_running = False
        self.scan_paused = False
        self.log_voltage = True

        #  scan parameters for DBR object init
        self.start_wl = 1627.5
        self.end_wl = 1672.4955
        self.interpolation_type = "true_linear"
        self.interpolation_value = 0
        self.sending_packets = True

        # GUI Display parameters
        monitors = []
        for monitor in screeninfo.get_monitors(): monitors.append(monitor)

        monitor = monitors[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height - 50

        #self.SCREEN_HEIGHT = 480    
        #self.SCREEN_WIDTH = 854
        self.window_buffer_size = 8
        self.DAC_plot_unlocked = False
        self.voltage_plots_unlocked = False

        # file management and plotting parameters
        self.saving_LUT = True
        self.new_plot_path = 'default path'
        self._num_voltage_1_series = 0
        self._num_voltage_2_series = 0
        self.voltage_1_data: list[tuple] = []
        self.voltage_2_data: list[tuple] = []
        self.DAC_list = [[],[],[],[],[],[]]

        #updated after scan completes or data is pushed via save voltage button
        self.voltage_1_data_all: list[list[tuple]] = [] 
        self.voltage_2_data_all: list[list[tuple]] = []
        
        # FP4029 Serial Communication parameters
        self.default_port_name = "COM4"
        self.port_name = "COM4"

        # Voltmeter pyvisa communication parameters
        self.default_voltmeter_1_connection = "USB0::0x2A8D::0x1601::MY60077980::INSTR"
        self.default_voltmeter_2_connection = "USB0::0x2A8D::0x1601::MY60077980::INSTR"
        self.voltage_hardware_averaging = False
        self.software_averaging = False
        self.v1_channel = 'AIN0'
        self.v2_channel = 'AIN0'

        
        self.TIME = datetime.now()
        self.CWD = os.path.dirname(os.path.realpath(__file__))
        self.TEMP_DIR = self.CWD + '/temp'
        try:
            shutil.rmtree(self.TEMP_DIR)
        except:
            print('Temp does not exist')
        Path(self.TEMP_DIR).mkdir(parents=True, exist_ok=True)

        dpg.create_context()
        matplotlib.use('Agg')

    def setup_laser(self):
        try: 
            print(self.port)
        except:
            print(f"No Laser Serial Port Setup yet")
            self.Laser = dbr.DBR_Spectrometer(
                port_name = self.default_port_name,
                start_wl = self.start_wl, 
                end_wl = self.end_wl,
                interpolation_type = self.interpolation_type, 
                interpolation_value = self.interpolation_value, 
                saving_LUT = self.saving_LUT)
            if self.logger_on: self.logger.log("Laser Setup Updated")
            self.DAC_list, logger_message = self.Laser.get_table()
            if self.logger_on: self.logger.log(logger_message)
            return

        self.Laser = dbr.DBR_Spectrometer(
                port_name = self.default_port_name,
                start_wl = self.start_wl, 
                end_wl = self.end_wl,
                interpolation_type = self.interpolation_type, 
                interpolation_value = self.interpolation_value, 
                saving_LUT = self.saving_LUT, #if False, Laser.get_table() will delete LUT in /DAC_Tables/* after updating self.DAC_list
                port = self.port)
        
        if self.logger_on: self.logger.log("Laser Setup Updated")
        self.DAC_list, logger_message = self.Laser.get_table()
        if self.logger_on: self.logger.log(logger_message)

    def log_available_ports(self):
        ports = serial.tools.list_ports.comports()
        ports_message = "Available Ports: "
        for port, desc, hwid in sorted(ports):
            ports_message += "\n" + ("{} : {} [{}]".format(port, desc, hwid))
        self.logger.log(ports_message)
        return ports_message

    def connect_to_laser(self):
        def _new_connection():
            self.logger.log(f"Connecting to Laser via Port '{self.port_name}'")
            try:
                self.port = serial.Serial(
                    port = self.port_name, 
                    baudrate = 9600, 
                    bytesize = serial.EIGHTBITS,
                    parity = serial.PARITY_NONE, 
                    timeout = 1) 
                
                self.logger.log(f"Serial port {self.port.name} opened successfully.")

                #TEST CONNECTION TO COMX to see if it is the FP4209 Instatune
                self.setup_laser()

                response, res = self.Laser.check_if_on()
                name, status, status_message, gain_value = response
                if status != 1: #ERROR HAS OCCURRED (Packet not understood etc.) WRONG RESPONSE
                    self.logger.log_error(f"{response}")
                    self.logger.log_error(f"Error in communication with Instatune at '{self.port_name}', \n Is this port connected to a FP4209 Instatune? Check NI MAX")
                    self.logger.log_error(f"Closing Serial Port '{self.port_name}'")
                    #self.port.close()  #Laser.read_response() already does this actually.

            except: #NO RESPONSE (error in indexing response in Laser.read_response is most common error here, when connected to wrong device.)
                self.logger.log_error(f"Device at '{self.port_name}' not responding, or could not be connected to. \n Is this port connected to a FP4209 Instatune? Check NI MAX")
                self.log_available_ports()
        try: 
            #self.port
            if self.port_name == self.port.name:
                self.logger.log(f"Already Connected to '{self.port.name}'")
            else: 
                _new_connection()
        except: _new_connection()

    def enable_laser(self):
        self.Laser.enable()
        
        if self.logger_on: 
            self.logger.log("Laser Enabled")
            self.logger.log(f"Voltage: {self.read_voltage_1_()}")
    
    def disable_laser(self):
        self.Laser.disable()
        if self.logger_on: 
            self.logger.log("Laser Disabled")
            self.logger.log(f"Voltage: {self.read_voltage_1_()}")

    def toggle_voltage_averaging(self, sender, data):

        if sender == "hardware":
            self.voltage_hardware_averaging = bool(data)
        if sender == 'software':
            self.software_averaging = bool(data)

        if self.voltage_hardware_averaging == 0: 
            try: 
                ljm.eWriteName(self.handle, f"{self.v1_channel}_EF_INDEX", 0)
                ljm.eWriteName(self.handle, f"{self.v2_channel}_EF_INDEX", 0)
                self.logger.log("Hardware Voltage Averaging Disabled")

            except ljm.LJMError as e:
                self.logger.log_error(f"LJM Error occurred: {e}")

        if self.voltage_hardware_averaging == 1:
            '''
            config_names_1 = [
                f"{self.v1_channel}_EF_INDEX",       # Set Extended Feature index
                f"{self.v1_channel}_EF_CONFIG_A",    # Number of samples to collect
                f"{self.v1_channel}_EF_CONFIG_D"     # Scan rate / frequency (Hz)
            ]
            config_values = [
                3,       # Index 3 = Average, Min, & Max mode
                100,     # Collect 100 samples per read cycle
                50000.0   # Sample at 50kHz (100kHz/2 channels)
            ]
            '''

            try:
                # 3. Write configuration to the T7
                ljm.eWriteNames(self.handle, 3, [f"{self.v1_channel}_EF_INDEX",f"{self.v1_channel}_EF_CONFIG_A", f"{self.v1_channel}_EF_CONFIG_D"], [3, 10, 100.0])
                self.logger.log(f"{ljm.eReadNames(self.handle, 3, [f"{self.v1_channel}_EF_INDEX",f"{self.v1_channel}_EF_CONFIG_A", f"{self.v1_channel}_EF_CONFIG_D"])}")

                ljm.eWriteNames(self.handle, 3, [f"{self.v2_channel}_EF_INDEX",f"{self.v2_channel}_EF_CONFIG_A", f"{self.v2_channel}_EF_CONFIG_D"], [3, 10, 100.0])
                self.logger.log(f"{ljm.eReadNames(self.handle, 3, [f"{self.v2_channel}_EF_INDEX",f"{self.v2_channel}_EF_CONFIG_A", f"{self.v2_channel}_EF_CONFIG_D"])}")

                self.logger.log(f"{self.v1_channel} & {self.v2_channel} EF configured successfully.")
                
            except ljm.LJMError as e:
                self.logger.log_error(f"LJM Error occurred: {e}")

        
    def read_voltage_1_(self) -> float:
        '''
        try: self._voltmeter_inst_1
        except: 
            self.connect_to_voltmeter(sender="volt_com_1", data=self.default_voltmeter_1_connection)
        '''
        if self.voltmeter_type == "KEYSIGHT":
            return float(self._voltmeter_inst_1.query("MEAS:VOLT:DC? 10,0.001")) #SLOW
        if self.voltmeter_type == "LJM":
            #self.logger.log_debug("T7")
            if self.voltage_hardware_averaging:
                averaged_voltage = float()
                try: 
                    # 4. Perform a single read of the averaged samples
                    # Reading _READ_A explicitly triggers the T7 to capture the burst and average it
                    averaged_voltage = ljm.eReadName(self.handle, f"{self.v1_channel}_EF_READ_A")
                    _max = ljm.eReadName(self.handle, f"{self.v1_channel}_EF_READ_B")
                    _min = ljm.eReadName(self.handle, f"{self.v1_channel}_EF_READ_C")
                    self.logger.log(f"Averaged Reading: {averaged_voltage:.5f} V")
                    self.logger.log(f"{_max}, {_min}, {averaged_voltage}")

                except ljm.LJMError as e:
                    self.logger.log_error(f"LJM Error occurred: {e}")

                return averaged_voltage
            else: 
                #self.logger.log_debug("T7")
                #self.logger.log(f"Channel = {int(self.v1_channel[-1])}")
                address = int(self.v1_channel[-1])*2
                self.logger.log(f"{address}")
                return ljm.eReadAddress(self.handle, address=address, dataType=ljm.constants.FLOAT32)
    
    def read_voltage_2_(self) -> float:
        '''
        try: self._voltmeter_inst_2
        except: 
            self.connect_to_voltmeter(sender="volt_com_2", data=self.default_voltmeter_2_connection)
        '''
        if self.voltmeter_type == "KEYSIGHT":
            return float(self._voltmeter_inst_2.query("MEAS:VOLT:DC? 10,0.001")) #SLOW
        if self.voltmeter_type == "LJM":
            #self.logger.log_debug("T7")
            if self.voltage_hardware_averaging:
                #print("averaging?")
                averaged_voltage = float()
                try: 
                    # 4. Perform a single read of the averaged samples
                    # Reading _READ_A explicitly triggers the T7 to capture the burst and average it
                    averaged_voltage = ljm.eReadName(self.handle, f"{self.v2_channel}_EF_READ_A")
                    self.logger.log(f"Averaged Reading: {averaged_voltage:.5f} V")

                except ljm.LJMError as e:
                    self.logger.log_error(f"LJM Error occurred: {e}")

                return averaged_voltage
            
            elif self.software_averaging:
                address = int(self.v2_channel[-1])*2
                self.logger.log(f"{address}")
                sample = []
                for i in range(10): 
                    x = ljm.eReadAddress(self.handle, address=address, dataType=ljm.constants.FLOAT32)
                    sample.append(x)
                return np.mean(sample)

            else: 
                #print("not averaging")
                #self.logger.log_debug("T7")
                address = int(self.v2_channel[-1])*2
                self.logger.log(f"{address}")
                return ljm.eReadAddress(self.handle, address=address, dataType=ljm.constants.FLOAT32)

    def connect_to_voltmeter(self, sender, data):

        self.logger.log(data)

        if 'INSTR' in data:
            self.voltmeter_type = 'KEYSIGHT'
        if 'LJM' in data:
            self.voltmeter_type = 'LJM'
            self.v1_channel = 'AIN0'
            self.v2_channel = 'AIN0'
        #self.logger.log(voltmeter_type)
        
        channel = 1
        match sender:
            case "volt_com_1": channel = 1
            case "volt_com_2": channel = 2
  
        if self.logger_on: self.logger.log(f"Connecting to Voltmeter channel {channel} : {data}")

        if self.voltmeter_type == "LJM":
            try:
                if channel == 1: self._voltmeter_inst_1 = data
                if channel == 2: self._voltmeter_inst_2 = data
                    
                Labjack_Serial_Number = data.split('::')[1]
                # Open LabJack
                self.handle = ljm.openS(deviceType="T7", connectionType="ANY", identifier=Labjack_Serial_Number)
                # Call eReadName to read the serial number from the LabJack.
                self.logger.log(f"Voltmeter SN = {ljm.eReadName(self.handle, "SERIAL_NUMBER")}")
                self.logger.log(f"Voltmeter Name = {ljm.eReadNameString(self.handle, "DEVICE_NAME_DEFAULT")}")
                #AIN0 is at REG ADDR 0
                self.logger.log(f"V_{channel} = {ljm.eReadAddress(self.handle, address=0, dataType=ljm.constants.FLOAT32)}")

            except:
                self.logger.log_error(f"LJM cannot connect to Device: {data}")
                return

        if self.voltmeter_type == 'KEYSIGHT':
            try:
                if channel == 1:
                    self._voltmeter_inst_1 = self.pyvisa_voltmeter_resources.open_resource(data)
                    self.logger.log(f"Voltmeter IDN: {self._voltmeter_inst_1.query("*IDN?")}")
                    self.logger.log(f"V_1 = {self._voltmeter_inst_1.query("MEAS:VOLT:DC? 10,0.001")}")
                if channel == 2: 
                    self._voltmeter_inst_2 = self.pyvisa_voltmeter_resources.open_resource(data)
                    self.logger.log(f"Voltmeter IDN: {self._voltmeter_inst_2.query("*IDN?")}")
                    self.logger.log(f"V_2 = {self._voltmeter_inst_2.query("MEAS:VOLT:DC? 10,0.001")}")
            except:
                self.logger.log_error(f"Pyvisa cannot connect to Device: {data}")
                return
        
        
    def disconnect_from_voltmeter(self):
        try: 
            self._voltmeter_inst.close()
        except: 
            self.logger.log_error(f'Voltmeter instance not found')

    def get_duplicates(self, data:list):
        from collections import Counter
        # Convert sublists to tuples to make them hashable
        counts = Counter(tuple(x) for x in data)
        # List only the items that appear more than once
        duplicates = [list(item) for item, count in counts.items() if count > 1]
        return duplicates
    
    def _scan(self):
        #self.logger.log("Starting Scan")

        try:
            self.Laser._laser_serial
        except:
            self.logger.log_error(f"No Serial Connection to Laser set up.")
            self.reset_scan()

        start = time.perf_counter()
        packets = self.Laser.make_packets_list(self.DAC_list)
        end = time.perf_counter()

        self.logger.log_debug(f"packet generation time: {end - start:.6f} seconds")
        
        num_packets = len(packets)
        if self.logger_on: self.logger.log_info(f"Packets : {num_packets}")

        wl_target_list = []
        #create New Voltage series for plot
        self.add_voltage_1_series()
        self.add_voltage_2_series()

        if self._num_voltage_1_series == self._num_voltage_2_series: 
            self.save_yaml_config(self.TEMP_DIR, series_index=self._num_voltage_1_series) #these will be grabbed and used when exporting voltage data
        else:
            self.logger.log_error("Cannot Save YAML config with current voltage data series index mismatch. MYBAD")

        self.voltage_1_data: list[tuple] = []
        self.voltage_2_data: list[tuple] = []

        new_voltage_1_list = []
        new_voltage_2_list = []
        sent_list = []
        
        #code timing debug lists for averageing
        packet_time_list = []
        voltage_time_list = []

        start = time.perf_counter()
        for i in range(num_packets):

            while self.scan_paused: time.sleep(0.1)
            if not self.scan_running: return

            self.scan_tracker = i
            
            if self.sending_packets: 
                fm, bm, ph, soa, target_wl = packets[i][0], packets[i][1], packets[i][2], packets[i][3], packets[i][4]

                self.scan_tracker = target_wl
                wl_target_list.append(target_wl)
                
                self.update_tracker()
                logger_message = 'Response Packets: \n'

                if self.debug:
                    sent_list.append([fm, bm, ph, soa])
                    if self.logger_on: self.logger.log_info(f'Target: {target_wl}')
                    for i in range(4):
                        name, status, status_message, gain_value = "debug_name", '0x01', "Command Executed, Response Data Valid: ", i
                        logger_message += f'{name} : status = {status} : {status_message}{gain_value} \n'

                    if self.logger_on: self.logger.log_debug(logger_message)
                # -------------------------------------------------------------------------------------------

                #PACKET COMMUNICATION
                else: 
                    start_packet_time = time.perf_counter()
                    responses:list[tuple] = self.Laser.set_laser_target_via_packets(fm, bm, ph, soa)
                    end_packet_time = time.perf_counter()
                    packet_time_list.append(end_packet_time - start_packet_time)

                    
                    if self.logger_on: self.logger.log_info(f'Target: {target_wl}')
                    for response in responses:
                        name, status, status_message, gain_value = response
                        logger_message += f'{name} : status = {status} : {status_message}{gain_value} \n'

                    if self.logger_on: self.logger.log_info(logger_message)
                # -------------------------------------------------------------------------------------------

                start_voltage_time = time.perf_counter()
                if self.log_voltage: 
                    if self.debug: 
                        new_voltage_1 = random.randrange(-5000,5000) / 1000
                        new_voltage_2 = random.randrange(-5000,5000) / 1000

                    #VOLTMETER COMMUNICATION
                    else: 
                    
                        time.sleep(self.settle_delay)
                        new_voltage_1 = self.read_voltage_1_()
                        new_voltage_2 = self.read_voltage_2_()
                        
                        
                    new_voltage_1_list.append(new_voltage_1)
                    new_voltage_2_list.append(new_voltage_2)

                    self.voltage_1_data.append((target_wl, new_voltage_1))
                    self.voltage_2_data.append((target_wl, new_voltage_2))

                    dpg.configure_item(f'v_1_data_{self._num_voltage_1_series}', x=wl_target_list, y=new_voltage_1_list)
                    dpg.configure_item(f'v_2_data_{self._num_voltage_2_series}', x=wl_target_list, y=new_voltage_2_list)
                    
                    self.logger.log_info(f"V_1 = ({target_wl}, {new_voltage_1})" + "\n"+ f"V_2 = ({target_wl}, {new_voltage_2})" + "\n" + "-"*60)
                end_voltage_time = time.perf_counter()
                voltage_time_list.append(end_voltage_time - start_voltage_time)
                # ---------------------------------------------------------------------------------

            time.sleep(self.packet_delay)
        
        if self.debug: self.logger.log_debug(f'Duplicate Packets:\n' + f'{self.get_duplicates(sent_list)}')
        if self.logger_on: self.logger.log(f"Scan Complete!")

        self.store_voltage_data(self.voltage_1_data, self.voltage_2_data)
        

        if self.logger_on: self.logger.log(f"Saved Voltage Data")
        end = time.perf_counter()

        self.logger.log_debug(f"full scan time: {end - start:.6f} seconds")
        self.logger.log_debug(f"avg 4 packet send & receive time: {np.mean(packet_time_list):.6f} seconds")
        self.logger.log_debug(f"std: {np.std(packet_time_list):.6f} seconds" + '\n')
        self.logger.log_debug(f"avg voltage recording time: {np.mean(voltage_time_list):.6f} seconds")
        self.logger.log_debug(f"std: {np.std(voltage_time_list):.6f} seconds")

    def store_voltage_data(self, v1_data: list[tuple], v2_data: list[tuple]):
        self.voltage_1_data_all.append(v1_data)
        self.voltage_2_data_all.append(v2_data)

    def import_LUT(self):
        def update_DAC_table(path):
            t = table.DAC_Table()
            self.DAC_list = t.get_DAC_arrays(path)
            
        self.open_file_browser(choose_dir=False, callback_function=update_DAC_table)
        self.update_DAC_plot()

    def update_plot_path(self, path):
        self.new_plot_path = path

    def generate_tracker(self, x):
        data_x, data_y = [x, x], [-10000, 70000]
        return data_x, data_y

    def update_tracker(self):
        data_x, data_y = self.generate_tracker(self.scan_tracker)
        #print(data_x[0])
        dpg.configure_item('tracker', x=data_x, y=data_y)

    def update_delay(self, sender, data):
        self.packet_delay = data
        #if sender != "delay_slider":
        if self.logger_on: self.logger.log(f"Packet Delay: {self.packet_delay}")

    def update_settle_delay(self, sender, data):
        self.settle_delay = data
        #if sender != "delay_slider":
        if self.logger_on: self.logger.log(f"Settle Delay: {self.settle_delay}")

    def update_start_wavelength(self, sender, data:float):
        self.start_wl = data
        if self.logger_on: self.logger.log(f"Start Index = {self.start_wl}")

    def update_end_wavelength(self, sender, data:float):
        self.end_wl = data
        if self.logger_on: self.logger.log(f"End Index = {self.end_wl}")

    def toggle_debug(self, sender, data:str):
        self.debug = bool(data)
        if self.logger_on: self.logger.log(f"Debug = {self.debug}")

    def toggle_logger_on(self, sender, data:str):
        self.logger_on = bool(data)
        self.logger.log(f"Log Outputs = {self.logger_on}")

    def toggle_log_voltage(self, sender, data:str):
        self.log_voltage = bool(data)
        if self.logger_on: self.logger.log(f"Read Voltage = {self.log_voltage}")

    def update_interpolation_type(self, sender, data:str):
        data = data.lower()
        match data:
            case "true linear": self.interpolation_type = "true_linear"
            case "linear extrapolation": self.interpolation_type = "linear_extrapolation"
            case "line fit": self.interpolation_type = "line_fit"
            

        if self.logger_on: self.logger.log(f"Interp Type = {self.interpolation_type}")

    def update_interpolation_value(self, sender, data):
        self.interpolation_value = data
        if self.logger_on: self.logger.log(f"Interp Value = {self.interpolation_value}")

    def update_DAC_plot(self): 
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT - (15*self.window_buffer_size)
        
        try: dpg.delete_item(self.DAC_plot)
        except: pass

        with dpg.plot(label="DAC Values",  parent= self.DAC_plot_window, height=plot_height-40, width=plot_width-24, tag="DAC_plot") as self.DAC_plot:
            dpg.add_plot_legend(show=True, location=9)

            dpg.add_plot_axis(dpg.mvXAxis, parent="DAC_plot", label="Wavelength", tag="DAC_xaxis")
            dpg.add_plot_axis(dpg.mvYAxis, parent="DAC_plot", label="Controller Value", tag="DAC_yaxis")

            dpg.set_axis_limits(axis='DAC_xaxis', ymin=1627, ymax=1673)
            dpg.set_axis_limits(axis='DAC_yaxis', ymin=-10000, ymax=70000)

        idx, wl, fm, bm, ph, soa = self.DAC_list[0], self.DAC_list[5], self.DAC_list[1], self.DAC_list[2], self.DAC_list[3], self.DAC_list[4]
        if idx:
            dpg.add_line_series(wl, fm, label="FM", parent="DAC_yaxis", tag="data")
            dpg.add_line_series(wl, bm, label="BM", parent="DAC_yaxis", tag="data2")
            dpg.add_line_series(wl, ph, label="PH", parent="DAC_yaxis", tag="data3")
            dpg.add_line_series(wl, soa, label="SOA", parent="DAC_yaxis", tag="data4")

            data_x, data_y = self.generate_tracker(self.scan_tracker)
            dpg.add_line_series(data_x, data_y, parent="DAC_yaxis", tag="tracker")

            dpg.bind_item_theme("data", "plot_theme")
            dpg.bind_item_theme("data2", "plot_theme")
            dpg.bind_item_theme("data3", "plot_theme")
            dpg.bind_item_theme("data4", "plot_theme")
            dpg.bind_item_theme("tracker", "tracker_theme")

    def add_voltage_1_series(self):
        self._num_voltage_1_series += 1
        def delete_series(sender, data): 
            dpg.delete_item(dpg.get_item_parent(sender))
        dpg.add_line_series(label=f"Scan {self._num_voltage_1_series}", x=[], y=[], parent="V_1_yaxis", tag=f'v_1_data_{self._num_voltage_1_series}')
        dpg.add_button(label="Delete", parent=dpg.last_item(), callback=delete_series)
        dpg.bind_item_theme(f"v_1_data_{self._num_voltage_1_series}", "plot_theme")

    def add_voltage_2_series(self):
        self._num_voltage_2_series += 1
        def delete_series(sender, data): 
            dpg.delete_item(dpg.get_item_parent(sender))
        dpg.add_line_series(label=f"Scan {self._num_voltage_2_series}", x=[], y=[], parent="V_2_yaxis", tag=f'v_2_data_{self._num_voltage_2_series}')
        dpg.add_button(label="Delete", parent=dpg.last_item(), callback=delete_series)
        dpg.bind_item_theme(f"v_2_data_{self._num_voltage_2_series}", "plot_theme")

    def _init_voltage_1_plot(self):
        self._num_voltage_1_series = 0
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT/2 - (6*self.window_buffer_size)
        with dpg.plot(parent= self.voltage_1_window, height=plot_height-40, width=plot_width-24, tag="voltage_1_plot") as self.voltage_1_plot:
            dpg.add_plot_legend(show=True, location=9)
            
            dpg.add_plot_axis(dpg.mvXAxis, auto_fit=True, parent="voltage_1_plot", label="Wavelength", tag="V_1_xaxis")
            dpg.add_plot_axis(dpg.mvYAxis, parent="voltage_1_plot", label="Voltage", tag="V_1_yaxis")
            dpg.set_axis_limits(axis='V_1_xaxis', ymin=1627, ymax=1673)
            #self.add_voltage_series()

    def _init_voltage_2_plot(self):
        self._num_voltage_2_series = 0
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT/2 - (6*self.window_buffer_size)
        with dpg.plot(parent= self.voltage_2_window, height=plot_height-40, width=plot_width-24, tag="voltage_2_plot") as self.voltage_2_plot:
            dpg.add_plot_legend(show=True, location=9)
            
            dpg.add_plot_axis(dpg.mvXAxis, auto_fit=True, parent="voltage_2_plot", label="Wavelength", tag="V_2_xaxis")
            dpg.add_plot_axis(dpg.mvYAxis, parent="voltage_2_plot", label="Voltage", tag="V_2_yaxis")
            dpg.set_axis_limits(axis='V_2_xaxis', ymin=1627, ymax=1673)
            #self.add_voltage_series()
            
    def check_if_laser_on(self):
        response, res_bool = self.Laser.check_if_on()
        name, status, status_message, gain_value = response
        if self.logger_on: self.logger.log_info(f'{name} : {status} : {status_message}{gain_value} \n')

    def update_com_port(self, sender, data):
        self.port_name = data
        #self.connect_to_laser()
        self.Laser.set_default_serial_port(self.port_name)
        self.logger.log(f"Will Connect to Port: {self.port_name}")

    def load_project_file(path): #NOTE: NOT IMPLEMENTED
        pass

    def open_project_file(self): 
        self.open_file_browser(choose_dir=False, callback_function=self.load_project_file)

    def save_project_file(self, sender, data): #NOTE: NOT IMPLEMENTED
        if self.logger_on: self.logger.log(f"Saving Current Project")

    def open_DAC_table(self):
        with dpg.window(label="DAC LUT", pos=(932,32), height= self.SCREEN_HEIGHT-(self.window_buffer_size*10), width= 500) as DAC_table_window:
            
            table_tag = dpg.generate_uuid()
            with dpg.table(header_row=True, tag=table_tag, row_background=True,
                        borders_innerH=True, borders_outerH=True, borders_innerV=True,
                        borders_outerV=True):
                        
               
                dpg.add_table_column(label="IDX")
                dpg.add_table_column(label="FM DAC")
                dpg.add_table_column(label="BM DAC")
                dpg.add_table_column(label="PH DAC")
                dpg.add_table_column(label="SOA DAC")
                dpg.add_table_column(label="WL Target")

                for i in range(len(self.DAC_list[0])):
                    with dpg.table_row():
                        for j in range(0, 6):
                            text_tag = dpg.add_text(f"{self.DAC_list[j][i]}")

    def open_logger(self):
        def create_logger_window():
            dpg.add_window(label="Logger", pos=(932,32), height= self.SCREEN_HEIGHT-(self.window_buffer_size*18), width=650, tag="logger_window")
            self.logger = dpg_logger.mvLogger(parent="logger_window")

        if not dpg.does_item_exist("logger_window"):
            create_logger_window()

        if not dpg.is_item_shown("logger_window"):
            dpg.show_item("logger_window")

        dpg.focus_item("logger_window")

    def toggle_unlock_DAC_plot(self):
        if not self.DAC_plot_unlocked:
            self.DAC_plot_unlocked = True
            if self.logger_on: self.logger.log("DAC Plot View Unlocked")
            dpg.set_axis_limits_auto(axis='DAC_xaxis')
            dpg.set_axis_limits_auto(axis='DAC_yaxis')
            dpg.set_item_label("laser_config_unlock_plot_button", "Lock Plots")
        else:
            self.DAC_plot_unlocked = False
            dpg.set_axis_limits(axis='DAC_xaxis', ymin=1627, ymax=1673)
            dpg.set_axis_limits(axis='DAC_yaxis', ymin=-10000, ymax=70000)

            if self.logger_on: self.logger.log("DAC Plot View Locked")
            dpg.set_item_label("laser_config_unlock_plot_button", "Unlock Plots")

    def toggle_unlock_voltage_plots(self):
        if not self.voltage_plots_unlocked:
            self.voltage_plots_unlocked = True
            if self.logger_on: self.logger.log("Voltage Plot View Unlocked")
            dpg.set_axis_limits_auto(axis='V_1_xaxis')
            dpg.set_axis_limits_auto(axis='V_2_xaxis')
            dpg.set_item_label("voltage_config_unlock_plot_button", "Lock Plots")
        else:
            self.voltage_plots_unlocked = False
            dpg.set_axis_limits(axis='V_1_xaxis', ymin=1627, ymax=1673)
            dpg.set_axis_limits(axis='V_2_xaxis', ymin=1627, ymax=1673)

            if self.logger_on: self.logger.log("Voltage Plot View Locked")
            dpg.set_item_label("voltage_config_unlock_plot_button", "Unlock Plots")

    def toggle_save_LUT(self, sender, data):
        self.saving_LUT = bool(data)
        if self.logger_on: self.logger.log(f"Saving Generated Tables = {self.saving_LUT}")

    def create_DAC_plot_file(self, path:str):
        self.logger.log("test DAC")
        fig, ax = plt.subplots()
        plt.gcf().set_size_inches(8,6)
        self.logger.log("Creating DAC Plot")
        idx, wl, fm, bm, ph, soa = self.DAC_list[0], self.DAC_list[5], self.DAC_list[1], self.DAC_list[2], self.DAC_list[3], self.DAC_list[4]

        ax.plot(wl, fm, 'o--', ms=0.85, linewidth=0.5, label=f"FM")
        ax.plot(wl, bm, 'o--', ms=0.85, linewidth=0.5, label=f"BM")
        ax.plot(wl, ph, 'o--', ms=0.85, linewidth=0.5, label=f"PH")
        ax.plot(wl, soa, 'o--', ms=0.85, linewidth=0.5, label=f"SOA")
        
        plt.xlabel('Wavelength')
        plt.ylabel("DAC Values")
        plt.legend()

        if not self.interpolation_value: plt.title(f'Default DAC Parameters ({self.start_index}, {self.end_index})')
        if self.interpolation_value > 0 and self.interpolation_type == "true_linear": 
            plt.title(f'DAC Parameters ({self.start_index}, {self.end_index}) Interpolated with {self.interpolation_value} Intermediate Integer Values')
        if self.interpolation_value > 0 and self.interpolation_type == "linear_extrapolation": 
            plt.title(f'DAC Parameters ({self.start_index}, {self.end_index}) Extrapolated with {self.interpolation_value} Intermediate Integer Values')
        if self.interpolation_value > 0 and self.interpolation_type == "line_fit": 
            plt.title(f'DAC Parameters ({self.start_index}, {self.end_index}) Extrapolated with {self.interpolation_value} Intermediate Integer Values')
        file_path = ''
        if self.interpolation_type == "true_linear": file_path = path+f'/DAC_True_Linear_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'
        if self.interpolation_type == "linear_extrapolation": file_path = path+f'/DAC_Linear_Extrapolation_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'
        if self.interpolation_type == "line_fit": file_path = path+f'/DAC_Line_Fit_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'

        plt.savefig(file_path, format='pdf')
        self.logger.log(f"DAC Plot Saved in: {file_path}")
        plt.close()

    def create_voltage_plot_file(self, path, wl_list, voltage_list):
        
        fig, ax = plt.subplots()
        plt.gcf().set_size_inches(8,6)
        self.logger.log("Creating Voltage Channel 1 Plot")

        ax.plot(wl_list, voltage_list, 'o--', ms=0.85, linewidth=0.5, label=f"Voltage Channel 1")

        plt.xlabel('Wavelength')
        plt.ylabel("Voltage")
        plt.legend()

        if not self.interpolation_value: plt.title(f'Voltage with Default LUT ({self.start_index}, {self.end_index})')
        if self.interpolation_value > 0 and self.interpolation_type == "true_linear": 
            plt.title(f'Voltage Data ({self.start_index}, {self.end_index}) LUT Interpolated with {self.interpolation_value} Intermediate Integer Values')
        if self.interpolation_value > 0 and self.interpolation_type == "linear_extrapolation": 
            plt.title(f'Voltage Data ({self.start_index}, {self.end_index}) LUT Extrapolated with {self.interpolation_value} Intermediate Integer Values')
        if self.interpolation_value > 0 and self.interpolation_type == "line_fit": 
            plt.title(f'Voltage Data ({self.start_index}, {self.end_index}) LUT Extrapolated with {self.interpolation_value} Intermediate Integer Values')
        file_path = ''
        if self.interpolation_type == "true_linear": file_path = path+f'/V_True_Linear_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'
        if self.interpolation_type == "linear_extrapolation": file_path = path+f'/V_Linear_Extrapolation_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'
        if self.interpolation_type == "line_fit": file_path = path+f'/V_Line_Fit_({self.interpolation_value}, {self.start_index}, {self.end_index}).pdf'

        plt.savefig(file_path, format='pdf')
        if self.logger_on: self.logger.log(f"Voltage Plot Saved in: {file_path}")
        plt.close()

    def clear_voltage_plot(self):
        dpg.delete_item("V_1_yaxis", children_only=True)
        dpg.delete_item("V_2_yaxis", children_only=True)

    def open_file_browser(self, choose_dir: bool, callback_function: FunctionType):

        def close_browser(sender, data, cancel_pressed):
            def new_func():
                if not cancel_pressed:
                    path = data[0]
                    if self.logger_on: self.logger.log(f"Using Directory: {path}")
                    dpg.delete_item(item='browser_window')
                    print(F"NEW PATH: {path}")
                    callback_function(path)
            new_func()

        if dpg.does_alias_exist("browser_window"): dpg.delete_item("browser_window")
        with dpg.window(label="Open Project File", tag="browser_window"):
            dpge.add_file_browser(
                parent="browser_window",
                show_as_window=False,
                default_path=self.CWD,
                collapse_sequences=True,
                allow_multi_selection=False,
                show_ok_cancel = True, 
                dirs_only = choose_dir,
                callback= close_browser
            )

    def export_voltage_plot(self):
        def create_voltage_plots(path):
            wl_list = []
            voltage_list = []
            for pair in self.voltage_1_data:
                target_wl, voltage = pair
                wl_list.append(target_wl)
                voltage_list.append(voltage)
            self.create_voltage_plot_file(path, wl_list, voltage_list)
            
        self.open_file_browser(choose_dir=True, callback_function=create_voltage_plots)

    def export_DAC_plot(self):
        def create_DAC_plot(path):
            self.create_DAC_plot_file(path)

        self.open_file_browser(choose_dir=True, callback_function=create_DAC_plot)
    
    def export_voltage_data(self):
        self.open_file_browser(choose_dir=True, callback_function=self.write_voltage_data)

    def save_yaml_config(self, given_path, series_index = -1):
        '''
        Saves current scan configuration (Laser config settings, etc. as yaml file)
        '''
        import yaml
        # Data to be written to the YAML file
        data = {
            'scan_date': self.TIME.strftime("%Y-%m-%d %H:%M:%S"), #is calculated at startup of GUI, so within the same session it will not change
            'debug': self.debug,
            'packet_delay': self.packet_delay,
            'settle_delay': self.settle_delay,
            'start_wavelength': self.start_wl,
            'end_wavelength': self.end_wl,
            'interpolation_type': self.interpolation_type,
            'self.interpolation_value': self.interpolation_value
        }

        # Writing the data to a YAML file
        with open(f'{given_path}/scan_config_{series_index}.yaml', 'w') as file:
            yaml.dump(data, file)

    def write_voltage_data(self, given_path, series_list: list|str = 'ALL'):
        '''
        Saves chosen voltage series to given path location, along with current config settings as yaml file.
        '''

        # Create directories
        '''
        Chosen_Directory/
        └── 2026-05-27_10'45''20/ 
            ├── Scan_1
            │   ├── voltage_data.csv 
            │   └── scan_config.yaml
            └── Scan_2
                ├── voltage_data.csv 
                └── scan_config.yaml
            .
            .
            .
        '''
        session_path = f"{given_path}/{self.TIME.strftime("%Y-%m-%d_%H'%M''%S")}"
        Path(session_path).mkdir(parents=True, exist_ok=True)
        #Save Scan Config yaml file
        
        all_data = list(zip(self.voltage_1_data_all, self.voltage_2_data_all))
        
        #only export data for which there is a yaml file.
        if series_list == 'ALL':
            files = [f.name for f in Path(self.TEMP_DIR).iterdir() if f.is_file()]
            file_numbers = []
            for file in files:
                file_numbers.append(int(file.split('_')[2][0])) #[1, 2, 3 ...] skipped
            series_list = file_numbers
            print(series_list)
        else: 
            if not isinstance(series_list, list): 
                self.logger.log_error("Chosen saved voltage series list is malformed")

        for i in series_list:
            series_path = session_path + f'/scan_{i}' 
            print(series_path)
            Path(series_path).mkdir(parents=True, exist_ok=True)
            try: 
                shutil.move(self.TEMP_DIR + f'/scan_config_{i}.yaml', series_path + f'/scan_config.yaml')
            except: 
                self.logger.log_error(f"Error moving yaml config from temp to export directory; does it exist?")
            try:
                v1_data, v2_data = all_data[i-1]
            except:
                self.logger.log(f"No data for scan yaml: scan_config_{i}; did scan complete?")
                continue

            if len(v1_data) != len(v2_data):
                self.logger.log_error(f"V1 data and V2 data are different sizes: {len(v1_data)} != {len(v2_data)}")
                return
            
            with open(series_path + '/voltage_data.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='|')
                writer.writerow(['IDX','Voltage 1','Voltage 2','Target Wl'])
                
                for j in range(len(v1_data)): 
                    target_wl, voltage_1 = v1_data[j]
                    target_wl, voltage_2 = v2_data[j]
                    writer.writerow([j, voltage_1, voltage_2, target_wl])

            csvfile.close()

        if self.logger_on: self.logger.log(f"Voltage Data Saved in: {given_path}")
        
    def toggle_scan(self):
        if not self.scan_running:
            self.scan_running = True
            self.scan_paused = False
            scan_thread = threading.Thread(target=self._scan, args=(), daemon=True)
            scan_thread.start()
            if self.logger_on: self.logger.log("Scan Started")
            dpg.set_item_label("laser_config_scan_button", "Pause")
            dpg.set_item_label("voltage_config_scan_button", "Pause")
        else:
            if not self.scan_paused:
                self.scan_paused = True
                if self.logger_on: self.logger.log("Scan Paused")
                dpg.set_item_label("laser_config_scan_button", "Resume")
                dpg.set_item_label("voltage_config_scan_button", "Resume")
                dpg.show_item("laser_config_reset_scan_button")
                dpg.show_item("voltage_config_reset_scan_button")
                return
            self.scan_paused = False
            if self.logger_on: self.logger.log("Scan Resumed")
            dpg.set_item_label("laser_config_scan_button", "Pause")
            dpg.set_item_label("voltage_config_scan_button", "Pause")

    def reset_scan(self):
        self.scan_running = False
        self.scan_paused = False
        self.scan_tracker = 1627.5
        dpg.set_item_label("laser_config_scan_button", "Start Scan")
        dpg.set_item_label("voltage_config_scan_button", "Start Scan")
        dpg.enable_item("scan_button")
        if self.logger_on: self.logger.log("Scan Reset")

    def update_resolution_index(self, sender, data):
        if data > 0: self.logger.log(f"Averaging Enabled, with index resolution: {data}")
        if data == 0: self.logger.log(f"Averaging Disabled")
        resolution_index = data
        ljm.eWriteName(self.handle, f"{self.v1_channel}_RESOLUTION_INDEX", resolution_index)
        ljm.eWriteName(self.handle, f"{self.v2_channel}_RESOLUTION_INDEX", resolution_index)
        self.logger.log(f"{self.v1_channel} & {self.v2_channel} Resolution Index = {resolution_index}")

    def update_T7_voltage_range(self, sender, data):

        match data:
            case '±10 volts': voltage_range_index = 1
            case '±1 volts': voltage_range_index = 10
            case '±0.1 volts': voltage_range_index = 100 
            case '±0.01 volts': voltage_range_index = 1000

        
        if sender == 'v1_range_input': 
            ljm.eWriteName(self.handle, f"{self.v1_channel}_RANGE", voltage_range_index)
            self.logger.log(f"{self.v1_channel} Voltage Range: {data}")

        if sender == 'v2_range_input': 
            ljm.eWriteName(self.handle, f"{self.v2_channel}_RANGE", voltage_range_index)
            self.logger.log(f"{self.v2_channel} Voltage Range: {data}")


    def update_T7_channel(self, sender, data):
        
        if sender == 'v1_channel_combo': 
            self.v1_channel = data
            self.logger.log(f"V1 Channel = {data}")
        if sender == 'v2_channel_combo': 
            self.v2_channel = data
            self.logger.log(f"V2 Channel = {data}")

    def voltage_config(self):
        config_width = 200
        if dpg.does_item_exist("voltage_config_window"): 
            dpg.show_item("voltage_config_window")
        else:
            with dpg.window(
                label="Voltage Config", 
                pos=(8,48), 
                height=self.SCREEN_HEIGHT-self.window_buffer_size*10, 
                width=config_width, 
                no_close=True, 
                no_move=True,
                tag="voltage_config_window") as voltage_config_window:
                
                debug_button = dpg.add_checkbox(label="Debug Mode", default_value=self.debug, callback=self.toggle_debug, tag="voltage_config_toggle_debug_button")
                logger_button = dpg.add_checkbox(label="Log Output", default_value=True, callback=self.toggle_logger_on, tag="voltage_config_toggle_logger_button")
                voltage_button = dpg.add_checkbox(label="Read Voltage", default_value=self.log_voltage, callback=self.toggle_log_voltage, tag="voltage_config_toggle_log_voltage_button")
                
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                def int_to_ip(ip_int):
                    # Pack the integer as a 32-bit unsigned network integer and convert to dotted string
                    packed_ip = struct.pack('!I', ip_int & 0xFFFFFFFF)
                    return socket.inet_ntoa(packed_ip)

                self.pyvisa_voltmeter_resources = pyvisa.ResourceManager()
                ljm_resources_untagged = ljm.listAll(ljm.constants.dtANY, ljm.constants.dtANY)
                #(numFound, aDeviceTypes, aConnectionTypes, aSerialNumbers, aIPAddresses)
                ljm_resources = []
                #print(ljm_resources_untagged)
                num_devices, labjack_types, connection_types, serial_numbers, IP_addresses = ljm_resources_untagged
                for connection_type in connection_types: 
                    if connection_type == 1: #USB
                        this_index = connection_types.index(1)
                        this_serial_number = serial_numbers[this_index]
                        this_labjack_type = labjack_types[this_index]
                        ljm_resources.append(f'USB0::{this_serial_number}::T{this_labjack_type}::LJM')
                    if connection_type == 3: # ETHERNET
                        this_index = connection_types.index(3)
                        this_labjack_type = labjack_types[this_index]
                        this_serial_number = serial_numbers[this_index]
                        this_IP = IP_addresses[this_index]
                        ljm_resources.append(f'ETHERNET::{this_serial_number}::'+int_to_ip(this_IP)+f'::T{this_labjack_type}::LJM')
                
                
                self.voltmeter_resource_list = list(self.pyvisa_voltmeter_resources.list_resources()) + ljm_resources
                voltmeter_resource_list = self.voltmeter_resource_list

                dpg.add_checkbox(label="Hardware Averaging", tag="hardware", callback=self.toggle_voltage_averaging)
                dpg.add_checkbox(label="Software Averaging", tag="software", callback=self.toggle_voltage_averaging)
                

                dpg.add_text("Voltage Channel 1 Resource ")
                voltmeter_connection_display_1 = dpg.add_combo(voltmeter_resource_list, width=config_width-16, default_value=self.default_voltmeter_1_connection, callback=self.connect_to_voltmeter,tag="volt_com_1")

                v1_channel_combo = dpg.add_combo(
                    default_value='AIN0',
                    items=('AIN0', 'AIN1', 'AIN2', 'AIN3'),
                    width=config_width-16,
                    tag="v1_channel_combo",
                    callback=self.update_T7_channel)
            
                resolution_index_input_1 = dpg.add_combo(
                    items=('±10 volts','±1 volts','±0.1 volts','±0.01 volts'),
                    default_value='±1 volts',
                    width=config_width-16, 
                    tag='v1_range_input',
                    callback=self.update_T7_voltage_range)
                
                dpg.add_text("Voltage Channel 2 Resource ")
                voltmeter_connection_display_2 = dpg.add_combo(voltmeter_resource_list, width=config_width-16, default_value=self.default_voltmeter_2_connection, callback=self.connect_to_voltmeter, tag="volt_com_2")
                
                v2_channel_combo = dpg.add_combo(
                    default_value='AIN0',
                    items=('AIN0', 'AIN1', 'AIN2', 'AIN3'),
                    width=config_width-16, 
                    tag="v2_channel_combo",
                    callback=self.update_T7_channel)
                
                resolution_index_input_2 = dpg.add_combo(
                    items=('±10 volts','±1 volts','±0.1 volts','±0.01 volts'),
                    default_value='±1 volts',
                    width=config_width-16, 
                    tag='v2_range_input',
                    callback=self.update_T7_voltage_range)
                
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                dpg.add_text("T7 Resolution Index")
                resolution_index_input = dpg.add_input_int(
                    default_value=0,
                    min_value= 0, 
                    max_value= 8,
                    min_clamped=True, 
                    max_clamped=True,
                    width=config_width-16, 
                    callback=self.update_resolution_index)
                
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                enable_laser_button = dpg.add_button(label="Enable Laser", width=config_width-16, callback=self.enable_laser)
                disable_laser_button = dpg.add_button(label="Disable Laser", width=config_width-16, callback=self.disable_laser)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                
                check_if_on_button = dpg.add_button(label="Check Laser Status", width=config_width-16, callback=self.check_if_laser_on)
                setup_button = dpg.add_button(label="Update Laser", width=config_width-16, callback=self.setup_laser)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                scan_button = dpg.add_button(label="Start Scan", width=config_width-16, callback=self.toggle_scan, tag="voltage_config_scan_button")
                reset_button = dpg.add_button(label="Reset Scan", width=config_width-16, callback=self.reset_scan, tag="voltage_config_reset_scan_button")
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                
                clear_voltage_plot_button = dpg.add_button(label="Clear Voltage Plot", width=config_width-16, callback=self.clear_voltage_plot)
                self.toggle_unlock_plots_button = dpg.add_button(label="Unlock Voltage Plots", width= config_width-16, callback=self.toggle_unlock_voltage_plots)
                dpg.add_spacer(height=self.window_buffer_size)

    def laser_config(self):
    
        config_width = 200
        if dpg.does_item_exist("laser_config_window"): 
            dpg.show_item("laser_config_window")
        else:
            with dpg.window(
                label="Laser Config", 
                pos=(8,48), 
                height=self.SCREEN_HEIGHT-self.window_buffer_size*10, 
                width=config_width, 
                no_close=True, 
                no_move=True,
                tag="laser_config_window") as laser_config_window:
                
                debug_button = dpg.add_checkbox(label="Debug Mode", default_value=self.debug, callback=self.toggle_debug)
                logger_button = dpg.add_checkbox(label="Log Output", default_value=True, callback=self.toggle_logger_on)
                voltage_button = dpg.add_checkbox(label="Read Voltage", default_value=self.log_voltage, callback=self.toggle_log_voltage)
                save_tables_button = dpg.add_checkbox(label="Save LUT", default_value=self.saving_LUT, callback=self.toggle_save_LUT)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                COMS_LIST = self.Laser.get_ports_list()

                dpg.add_text("Serial COM Port")
                serial_com_input = dpg.add_combo(items=COMS_LIST, width=config_width-16, default_value=self.port_name, callback=self.update_com_port)
                connect_to_laser_button = dpg.add_button(label="Connect to Laser", width=config_width-16, callback=self.connect_to_laser)

                enable_laser_button = dpg.add_button(label="Enable Laser", width=config_width-16, callback=self.enable_laser)
                disable_laser_button = dpg.add_button(label="Disable Laser", width=config_width-16, callback=self.disable_laser)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                
                check_if_on_button = dpg.add_button(label="Check Laser Status", width=config_width-16, callback=self.check_if_laser_on)
                setup_button = dpg.add_button(label="Update Laser", width=config_width-16, callback=self.setup_laser)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                scan_button = dpg.add_button(label="Start Scan", width=config_width-16, callback=self.toggle_scan, tag="laser_config_scan_button")
                reset_button = dpg.add_button(label="Reset Scan", width=config_width-16, callback=self.reset_scan, tag="laser_reset_scan_button")
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                #plot_button = dpg.add_button(label="Show Plot", width=config_width-16, callback=show_plot)
                update_plot_button = dpg.add_button(label="Update Plot", width = config_width-16, callback=self.update_DAC_plot)
                self.toggle_unlock_plots_button = dpg.add_button(label="Unlock Plot", width=config_width-16, callback=self.toggle_unlock_DAC_plot, tag="laser_config_unlock_plot_button")
            

                dpg.add_text("Packet Delay")
                packet_delay_input = dpg.add_input_float(
                    default_value=self.packet_delay,
                    min_value= 0, 
                    min_clamped=True, 
                    max_clamped=False,
                    width=config_width-16, 
                    callback=self.update_delay)
                
                dpg.add_text("Settle Delay")
                packet_delay_input = dpg.add_input_float(
                    default_value=self.settle_delay,
                    min_value= 0, 
                    min_clamped=True, 
                    max_clamped=False,
                    width=config_width-16, 
                    callback=self.update_settle_delay)

                dpg.add_text("Interpolation Type")
                match self.interpolation_type: #from init of GUI object
                    case "true_linear": interpolation_default = "True Linear"
                    case "line_fit": interpolation_default = "Line Fit"
                    case "linear_extrapolation": interpolation_default = "Linear Extrapolation"

                interpolation_type_input = dpg.add_combo(
                    default_value=interpolation_default, 
                    items=("True Linear", "Line Fit", "Linear Extrapolation"),
                    width=config_width-16, 
                    callback=self.update_interpolation_type)

                dpg.add_text("Interpolation Value")
                interpolation_value_input = dpg.add_input_int(default_value=0, width=config_width-16, callback=self.update_interpolation_value)
                
                dpg.add_text("Wavelength Range")
                start_wavelength_input = dpg.add_input_float(
                    label="Start", 
                    default_value= 1627.5, 
                    min_value=1627.5, 
                    max_value=1672.4955, 
                    min_clamped=True, 
                    max_clamped=True, 
                    width=config_width/1.5, 
                    callback=self.update_start_wavelength)
                
                end_wavelength_input = dpg.add_input_float(
                    label="End", 
                    default_value= 1672.4955, 
                    min_value=1627.5, 
                    max_value=1672.4955,
                    min_clamped=True, 
                    max_clamped=True, 
                    width=config_width/1.5, 
                    callback=self.update_end_wavelength)
                
                dpg.add_separator()

    def load_DAC_tab(self):
        self.laser_config()
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT - 15*self.window_buffer_size
        if not dpg.does_item_exist("DAC_window"):
            if not dpg.get_item_children("DAC View", 1):
                with dpg.window(
                    label="DAC Plot", 
                    pos=(216,48), 
                    height=plot_height,
                    width=plot_width, 
                    no_close=True, 
                    no_move=True,
                    tag="DAC_window") as self.DAC_plot_window:
                    
                    self.update_DAC_plot()
        else: dpg.show_item("DAC_window")
        
    def load_Voltage_tab(self):
        self.voltage_config()
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT/2 - 6*self.window_buffer_size
        if not dpg.does_item_exist("voltage_1_window"):
            if not dpg.get_item_children("Voltage Data", 1):
                with dpg.window(
                    label="Voltage Channel 1", 
                    pos=(216, 48), 
                    height=plot_height, 
                    width=plot_width, 
                    no_close=True, 
                    no_move=True,
                    tag="voltage_1_window") as self.voltage_1_window:

                    self._init_voltage_1_plot()

                with dpg.window(
                    label="Voltage Channel 2", 
                    pos=(216, plot_height+48+self.window_buffer_size), 
                    height=plot_height, 
                    width=plot_width, 
                    no_close=True, 
                    no_move=True,
                    tag="voltage_2_window") as self.voltage_2_window:

                    self._init_voltage_2_plot()
        else: 
            dpg.show_item("voltage_1_window")
            dpg.show_item("voltage_2_window")
      
    def tab_callback(self, sender, data):
        def clear_primary_window():

            if dpg.does_item_exist("laser_config_window"): dpg.hide_item("laser_config_window")
            if dpg.does_item_exist("voltage_config_window"): dpg.hide_item("voltage_config_window")

            if dpg.does_item_exist("voltage_1_window"):
                dpg.hide_item("voltage_1_window")
                dpg.hide_item("voltage_2_window")

            if dpg.does_item_exist("DAC_window"): dpg.hide_item("DAC_window")

        if dpg.get_item_configuration(data)['label'] == "Voltage Data":
            clear_primary_window()
            self.load_Voltage_tab()
            
        if dpg.get_item_configuration(data)['label'] == "DAC View":
            clear_primary_window()
            self.load_DAC_tab()

    def create_tab_bar(self):
        with dpg.tab_bar(tag="tab_bar", callback= self.tab_callback) as tb:
            dpg.add_tab(label="DAC View", tag="DAC View", parent="tab_bar")
            dpg.add_tab(label="Voltage Data", tag="Voltage Data", parent="tab_bar")

    def start_window(self):
        dpg.create_viewport(x_pos=0, y_pos=0, width=self.SCREEN_WIDTH, height=self.SCREEN_HEIGHT, title="Laser Control")
        
        def set_theme_light():
            light_theme = create_theme_imgui_light()
            dpg.bind_theme(light_theme)

        with dpg.window(tag="primary_window") as self.primary_window:
            dpg.set_primary_window(self.primary_window, True)

            self.open_logger()
            self.setup_laser()
            
            with dpg.menu_bar():
                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Logger", callback=self.open_logger)
                    dpg.add_menu_item(label="DAC Table", callback=self.open_DAC_table)
                with dpg.menu(label="Themes"):
                    dpg.add_menu_item(label="Dark", callback=lambda: dpg.bind_theme(0))
                    dpg.add_menu_item(label="Light", callback=set_theme_light)
                    dpg.add_menu_item(label="Theme Editor", callback=lambda: dpg.show_style_editor())
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Open Project", callback=self.open_project_file)
                    dpg.add_menu_item(label="Open LUT", callback=self.import_LUT)
                    with dpg.menu(label="Save"):
                        dpg.add_menu_item(label="Save Project As", callback=self.save_project_file) #NOTE: NOT IMPLEMENTED
                    with dpg.menu(label="Export"):
                        dpg.add_menu_item(label="Export Voltage Plot", callback=self.export_voltage_plot)
                        dpg.add_menu_item(label="Export DAC Plot", callback=self.export_DAC_plot)
                        dpg.add_menu_item(label="Export Voltage Data", callback=self.export_voltage_data)

            with dpg.theme(tag="plot_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

            with dpg.theme(tag="tracker_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)

            

            self.create_tab_bar()
            self.load_Voltage_tab()
            if dpg.does_item_exist("voltage_1_window"):
                dpg.hide_item("voltage_1_window")
                dpg.hide_item("voltage_2_window")
            self.load_DAC_tab()
            self.open_logger()
                    
                        

            
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        #dpg.destroy_context()