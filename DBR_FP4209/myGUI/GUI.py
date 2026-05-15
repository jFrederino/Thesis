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

class GUI_Controller:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger_on: bool = True #if false, most class methods will not print update statements in logger in the GUI. some will still print: (Serial and Voltmeter connection info, etc.)

        # scan control tracking
        self.packet_delay: float = 0.1
        self.settle_delay: float = 0.1
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
        
        # FP4029 Serial Communication parameters
        self.default_port_name = "COM4"
        self.port_name = "COM4"

        # Voltmeter pyvisa communication parameters
        self.default_voltmeter_1_connection = "USB0::0x2A8D::0x1601::MY60077980::INSTR"
        self.default_voltmeter_2_connection = "USB0::0x2A8D::0x1601::MY60077980::INSTR"

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
                self.setup_laser()
            except:
                self.logger.log_error(f"Port '{self.port_name}' could not be found.")
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


    def read_voltage_1_(self) -> float:
        try: self._voltmeter_inst_1
        except: 
            self.connect_to_voltmeter(sender="volt_com_1", data=self.default_voltmeter_1_connection)

        return float(self._voltmeter_inst_1.query("MEAS:VOLT:DC? 10,0.001"))
    
    def read_voltage_2_(self) -> float:
        try: self._voltmeter_inst_2
        except: 
            self.connect_to_voltmeter(sender="volt_com_2", data=self.default_voltmeter_2_connection)

        return float(self._voltmeter_inst_2.query("MEAS:VOLT:DC? 10,0.001"))

    def connect_to_voltmeter(self, sender, data):
        channel = 1
        match sender:
            case "volt_com_1": channel = 1
            case "volt_com_2": channel = 2
        try:
            if channel == 1: print(self._voltmeter_inst_1)
            if channel == 2: print(self._voltmeter_inst_2)
        except:
            if self.logger_on: self.logger.log(f"Connecting to Voltmeter channel {channel} : {data}")
            try:
                if channel == 1:
                    self._voltmeter_inst_1 = self.voltmeter_resource_manager.open_resource(data)
                    self.logger.log(f"Voltmeter IDN: {self._voltmeter_inst_1.query("*IDN?")}")
                    self.logger.log(f"V_1 = {self._voltmeter_inst_1.query("MEAS:VOLT:DC? 10,0.001")}")
                if channel == 2: 
                    self._voltmeter_inst_2 = self.voltmeter_resource_manager.open_resource(data)
                    self.logger.log(f"Voltmeter IDN: {self._voltmeter_inst_2.query("*IDN?")}")
                    self.logger.log(f"V_2 = {self._voltmeter_inst_2.query("MEAS:VOLT:DC? 10,0.001")}")
            except:
                self.logger.log_error(f"Pyvisa cannot connect to Device: {data}")
                return
        

    def disconnect_from_voltmeter(self):
        try: 
            self._voltmeter_inst.close()
        except: 
            self.connect_to_voltmeter()
            self.disconnect_from_voltmeter()


    def add_manual_to_voltage_plot(self):

        data1 = [[1650.9495,1.635],
                [1650.954,1.325],
                [1650.9585,1.959],
                [1650.963,4.395],
                [1650.9675,3.116],
                [1650.972,1.588],
                [1650.9765,1.324],
                [1650.981,2.004],
                [1650.9855,4.081],
                [1650.99,3.23],
                [1650.9945,1.537],
                [1650.999,1.359],
                [1651.0035,2.111]]
        data2 = [[5204,7138,7776,9282,19374,1650.918,3.8],
                [5205,7138,7776,9136,19313,1650.9225,1.9],
                [5206,7138,7776,8992,19259,1650.927,1.3],
                [5207,7138,7776,8850,19221,1650.9315,1.5],
                [5208,7138,7776,8706,19163,1650.936,2.3],
                [5209,7138,7776,8552,19132,1650.9405,4.1],
                [5210,7138,7776,8408,19094,1650.945,3.5],
                [5211,7138,7776,8274,19055,1650.9495,2.0],
                [5212,7138,7776,8130,19004,1650.954,1.4],
                [5213,7138,7776,7984,18964,1650.9585,1.4],
                [5214,6964,7568,8482,19159,1650.963,2.6],
                [5215,6964,7568,8370,19134,1650.9675,4.1],
                [5216,6964,7568,8242,19117,1650.972,3.6],
                [5217,6964,7568,8112,19086,1650.9765,1.9],
                [5218,6964,7568,7968,19047,1650.981,1.3],
                [5219,6964,7568,7842,19020,1650.9855,1.4],
                [5220,6964,7568,7714,18987,1650.99,2.4],
                [5221,6964,7568,7560,18943,1650.9945,4.4],
                [5222,6964,7568,7432,18926,1650.999,2.7],
                [5223,6964,7568,7314,18908,1651.0035,1.5]]
        
        wl_list_1 = []
        new_voltage_1_list_1 = []
        self.add_voltage_1_series()
        
        for row in data1:
            wl_list_1.append(row[0])
            new_voltage_1_list_1.append(row[-1])
        dpg.configure_item(f'v_1_data_{self._num_voltage_1_series}', x=wl_list_1, y=new_voltage_1_list_1)

        wl_list = []
        new_voltage_1_list = []
        self.add_voltage_1_series()

        for row in data2:
            wl_list.append(row[5])
            new_voltage_1_list.append(row[-1])
        dpg.configure_item(f'v_1_data_{self._num_voltage_1_series}', x=wl_list, y=new_voltage_1_list)

    def get_duplicates(self, data:list):
        from collections import Counter
        # Convert sublists to tuples to make them hashable
        counts = Counter(tuple(x) for x in data)

        # List only the items that appear more than once
        duplicates = [list(item) for item, count in counts.items() if count > 1]
        return duplicates
    
    def _scan(self):
        self.logger.log("Starting Scan")
        packets = self.Laser.make_packets_list(self.DAC_list)
        num_packets = len(packets)
        if self.logger_on: self.logger.log_info(f"Packets : {num_packets}")

        wl_target_list = []
        self.add_voltage_1_series()
        self.add_voltage_2_series()
        self.voltage_1_data: list[tuple] = []
        self.voltage_2_data: list[tuple] = []
        new_voltage_1_list = []
        new_voltage_2_list = []
        sent_list = []
        #create New Voltage series for plot
    
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
                else: 
                    sent_list.append([fm, bm, ph, soa])
                    responses:list[tuple] = self.Laser.set_laser_target_via_packets(fm, bm, ph, soa)

                    if self.logger_on: self.logger.log_info(f'Target: {target_wl}')
                    for response in responses:
                        name, status, status_message, gain_value = response
                        logger_message += f'{name} : status = {status} : {status_message}{gain_value} \n'

                    if self.logger_on: self.logger.log_info(logger_message)
                    
                if self.log_voltage: 
                    if self.debug: 
                        new_voltage_1 = random.randrange(-5000,5000) / 1000
                        new_voltage_2 = random.randrange(-5000,5000) / 1000
                    else: 
                        try:
                            time.sleep(self.settle_delay)
                            new_voltage_1 = self.read_voltage_1_()
                            new_voltage_2 = self.read_voltage_2_()
                        except: self.logger.log_error("Voltmeter Read Error")
                    new_voltage_1_list.append(new_voltage_1)
                    new_voltage_2_list.append(new_voltage_2)

                    self.voltage_1_data.append((target_wl, new_voltage_1))
                    self.voltage_2_data.append((target_wl, new_voltage_2))

                    dpg.configure_item(f'v_1_data_{self._num_voltage_1_series}', x=wl_target_list, y=new_voltage_1_list)
                    dpg.configure_item(f'v_2_data_{self._num_voltage_2_series}', x=wl_target_list, y=new_voltage_2_list)
                    
                    self.logger.log_info(f"V_1 = ({target_wl}, {new_voltage_1})" + "\n"+ "V_2 = ({target_wl}, {new_voltage_2})" + "\n" + "-"*60)
                    
            time.sleep(self.packet_delay)
        
        print(self.get_duplicates(sent_list))

        if self.logger_on:
            self.logger.log(f"Scan Complete!")

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

        CWD = os.path.dirname(os.path.realpath(__file__))

        if dpg.does_alias_exist("browser_window"): dpg.delete_item("browser_window")
        with dpg.window(label="Open Project File", tag="browser_window"):
            dpge.add_file_browser(
                parent="browser_window",
                show_as_window=False,
                default_path=CWD,
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

    def write_voltage_data(self, path):
        import csv
        CWD = os.path.dirname(os.path.realpath(__file__))
        if self.interpolation_type == "true_linear":
            new_table_path = path + f'/True_Linear_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        if self.interpolation_type == "linear_extrapolation":
            new_table_path = path + f'/Linear_Extrapolation_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        if self.interpolation_type == "line_fit":
            new_table_path = path + f'/Line_Fit_({self.interpolation_value}, {self.start_index}, {self.end_index}).csv'

        with open(new_table_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|')
            writer.writerow(['IDX','Voltage','Target Wl'])
            idx = 0
            for pair in self.voltage_1_data:  
                target_wl, voltage = pair
                writer.writerow([idx, voltage, target_wl])
                idx += 1

        csvfile.close()
        if self.logger_on: self.log(f"Voltage Data Saved in: {path}")

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
                add_manual = dpg.add_button(label="Add Manual Voltages",width=config_width-16,callback=self.add_manual_to_voltage_plot)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

                self.voltmeter_resource_manager = pyvisa.ResourceManager()
                voltmeter_resource_list = self.voltmeter_resource_manager.list_resources()
                dpg.add_text("Voltage Channel 1 Resource ")
                voltmeter_connection_display_1 = dpg.add_combo(voltmeter_resource_list, width=config_width-16, default_value=self.default_voltmeter_1_connection, callback=self.connect_to_voltmeter,tag="volt_com_1")

                dpg.add_text("Voltage Channel 2 Resource ")
                voltmeter_connection_display_2 = dpg.add_combo(voltmeter_resource_list, width=config_width-16, default_value=self.default_voltmeter_2_connection, callback=self.connect_to_voltmeter, tag="volt_com_2")

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

                connect_to_laser_button = dpg.add_button(label="Connect to Laser", width=config_width-16, callback=self.connect_to_laser)
                dpg.add_text("Serial COM Port")
                serial_com_input = dpg.add_combo(items=COMS_LIST, width=config_width-16, default_value=self.port_name, callback=self.update_com_port)
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
                update_plot_buttom = dpg.add_button(label="Update DAC Plot", width = config_width-16, callback=self.update_DAC_plot)
                self.toggle_unlock_plots_button = dpg.add_button(label="Unlock DAC Plot", width= config_width-16, callback=self.toggle_unlock_DAC_plot, tag="laser_config_unlock_plot_button")
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)

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

            if dpg.does_item_exist("laser_config_window"):
                dpg.hide_item("laser_config_window")
            if dpg.does_item_exist("voltage_config_window"):
                dpg.hide_item("voltage_config_window")

            if dpg.does_item_exist("voltage_1_window"):
                dpg.hide_item("voltage_1_window")
                dpg.hide_item("voltage_2_window")
            if dpg.does_item_exist("DAC_window"):
                dpg.hide_item("DAC_window")

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