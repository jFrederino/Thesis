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

import Spectrometer as dbr
import generate_table as table

class GUI_Controller:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger_on: bool = True

        self.scan_tracker = 1627.5 #x value of scan tracker line on DAC plot, and table index.
        self.scan_running = False
        self.scan_paused = False

        #   scan parameters for DBR object init
        self.start_index = 0 
        self.end_index = 9999
        self.interpolation_type = "true_linear"
        self.interpolation_value = 0
        self.delay = 1
        self.sending_packets = True
        self.log_voltage = True
        self.DAC_list = [[],[],[],[],[],[]]

        self.SCREEN_HEIGHT = 480    
        self.SCREEN_WIDTH = 854
        self.window_buffer_size = 8
        self.plot_unlocked = False
        self.saving_LUT = True
        self.new_plot_path = 'default path'
        self.default_port_name = "COM4"
        self.port_name = "COM4"

        self.voltage_data: list[tuple] = []
        dpg.create_context()
        matplotlib.use('Agg')

    def setup(self):
        try: 
            print(self.port)
        except:
            print(f"No Port Setup yet")
            self.Laser = dbr.DBR_Spectrometer(
                port_name = self.default_port_name,
                start_index = self.start_index, 
                end_index = self.end_index,
                interpolation_type = self.interpolation_type, 
                interpolation_value = self.interpolation_value, 
                delay = self.delay, 
                sending_packets = self.sending_packets,
                log_voltage = self.log_voltage,
                saving_LUT = self.saving_LUT)
            return
        
        self.Laser = dbr.DBR_Spectrometer(
                port_name = self.default_port_name,
                start_index = self.start_index, 
                end_index = self.end_index,
                interpolation_type = self.interpolation_type, 
                interpolation_value = self.interpolation_value, 
                delay = self.delay, 
                sending_packets = self.sending_packets,
                log_voltage = self.log_voltage,
                saving_LUT = self.saving_LUT,
                port = self.port)
        
        if self.logger_on: self.logger.log("Laser Setup Updated")
        self.DAC_list, logger_message = self.Laser.get_table()
        if self.logger_on: self.logger.log(logger_message)

    def connect_to_laser(self):
        try: 
            #self.port
            self.logger.log(f"Already Connected to {self.port}")
        except:
            self.logger.log(f"Connecting to Laser...")
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                print("{} : {} [{}]".format(port, desc, hwid))

            self.port = serial.Serial(
                port = self.port_name, 
                baudrate = 9600, 
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE, 
                timeout = 1) 
            
            self.logger.log(f"Serial port {self.port.name} opened successfully.")

    def enable_laser(self):
        self.Laser.enable()
        
        if self.logger_on: 
            self.logger.log("Laser Enabled")
            self.logger.log(f"{self.Laser.read_voltage()}")
    
    def disable_laser(self):
        self.Laser.disable()
        if self.logger_on: 
            self.logger.log("Laser Disabled")
            self.logger.log(f"{self.Laser.read_voltage()}")

    def _scan(self):
        self.logger.log("Starting Scan")
        packets = self.Laser.make_packets_list(self.DAC_list)
        num_packets = len(packets)
        if self.logger_on: self.logger.log_info(f"Packets : {num_packets}")

        wl_target_list = []
        self.add_voltage_series()
        new_voltage_list = []

        #create New Voltage series for plot
    
        for i in range(num_packets):

            while self.scan_paused: time.sleep(0.1)
            if not self.scan_running: return

            self.scan_tracker = i
            
            if self.Laser.sending_packets: 
                fm, bm, ph, soa, target_wl = packets[i][0], packets[i][1], packets[i][2], packets[i][3], packets[i][4]

                self.scan_tracker = target_wl
                wl_target_list.append(target_wl)
                
                self.update_tracker()
                logger_message = 'Response Packets: \n'

                if self.debug:
                    if self.logger_on: self.logger.log_info(f'Target: {target_wl}')
                    for i in range(4):
                        name, status, status_message, gain_value = "debug_name", '0x01', "Command Executed, Response Data Valid: ", i
                        logger_message += f'{name} : status = {status} : {status_message}{gain_value} \n'

                    if self.logger_on: self.logger.log_debug(logger_message)
                else: 
                    responses:list[tuple] = self.Laser.set_laser_target_via_packets(fm, bm, ph, soa)
                    if self.logger_on: self.logger.log_info(f'Target: {target_wl}')
                    for response in responses:
                        name, status, status_message, gain_value = response
                        logger_message += f'{name} : status = {status} : {status_message}{gain_value} \n'

                    if self.logger_on: self.logger.log_info(logger_message)
                    
                if self.log_voltage: 
                    if self.debug: new_voltage = random.randrange(-100,100) / 10000
                    else: 
                        try:
                            new_voltage = self.Laser.read_voltage()
                        except: self.logger.log_error("Voltmeter Read Error")
                    new_voltage_list.append(new_voltage)

                    self.voltage_data.append((target_wl, new_voltage))

                    dpg.configure_item(f'v_data_{self._num_voltage_series}', x=wl_target_list, y=new_voltage_list)
                    self.logger.log_info(f"V = ({target_wl}, {new_voltage})" + "\n" + "-"*60)
                    
            time.sleep(self.Laser.delay)
        
        if self.logger_on:
            self.logger.log(f"Scan Complete!")

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
        self.delay = data
        #if sender != "delay_slider":
        if self.logger_on: self.logger.log(f"Delay: {self.delay}")

    def update_start_index(self, sender, data:str):
        self.start_index = data
        if self.logger_on: self.logger.log(f"Start Index = {data}")
    
    def update_end_index(self, sender, data:str):
        self.end_index = data
        if self.logger_on: self.logger.log(f"End Index = {data}")

    def update_start_wavelength(self, sender, data:float):
        wl_list = self.DAC_list[-1]
        closest_wavelength = min(wl_list, key=lambda x:abs(x-data))
        wl_index = wl_list.index(closest_wavelength)
        if self.logger_on: self.logger.log(f"Start WL = {closest_wavelength}")
        self.start_index = wl_index
        if self.logger_on: self.logger.log(f"Start Index = {self.start_index}")

    def update_end_wavelength(self, sender, data:float):
        wl_list = self.DAC_list[-1]
        closest_wavelength = min(wl_list, key=lambda x:abs(x-data))
        wl_index = wl_list.index(closest_wavelength)
        if self.logger_on: self.logger.log(f"End WL = {closest_wavelength}")
        self.end_index = wl_index
        if self.logger_on: self.logger.log(f"End Index = {self.end_index}")

    def toggle_debug(self, sender, data:str):
        self.debug = bool(data)
        if self.logger_on: self.logger.log(f"Debug = {self.debug}")

    def toggle_log_on(self, sender, data:str):
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
        plot_height = self.SCREEN_HEIGHT/2 - (6*self.window_buffer_size)
        
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

    def add_voltage_series(self):
        self._num_voltage_series += 1
        def delete_series(sender, data): dpg.delete_item(dpg.get_item_parent(sender))
        dpg.add_line_series(label=f"Scan {self._num_voltage_series}", x=[], y=[], parent="V_yaxis", tag=f'v_data_{self._num_voltage_series}')
        dpg.add_button(label="Delete", parent=dpg.last_item(), callback=delete_series)
        dpg.bind_item_theme(f"v_data_{self._num_voltage_series}", "plot_theme")

    def _init_voltage_plot(self):
        self._num_voltage_series = 0
        plot_width = self.SCREEN_WIDTH-240
        plot_height = self.SCREEN_HEIGHT/2 - (6*self.window_buffer_size)
        with dpg.plot(label="Voltage Data",  parent= self.voltage_plot_window, height=plot_height-40, width=plot_width-24, tag="voltage_plot") as self.voltage_plot:
            dpg.add_plot_legend(show=True, location=9)
            
            dpg.add_plot_axis(dpg.mvXAxis, auto_fit=True, parent="voltage_plot", label="Wavelength", tag="V_xaxis")
            dpg.add_plot_axis(dpg.mvYAxis, parent="voltage_plot", label="Voltage", tag="V_yaxis")
            dpg.set_axis_limits(axis='V_xaxis', ymin=1627, ymax=1673)
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

    def open_project_file(self):
        CWD = os.path.dirname(os.path.realpath(__file__))
        with dpg.window(label="Open Project File", tag="browser_window"):

            def show_selected_file(sender, files, cancel_pressed):
                if self.logger_on: self.logger.log(f"{sender}: {files[0]}")
                if not cancel_pressed:
                    dpg.set_value('selected_file', files[0])
                    project_path = files[0]
                    if self.logger_on: self.logger.log(f"Loaded File: {project_path}")
                    dpg.delete_item(item='browser_window')

            dpge.add_file_browser(
                parent="browser_window",
                show_as_window=False,
                default_path=CWD,
                collapse_sequences=True,
                allow_multi_selection=False,
                show_ok_cancel = True, 
                callback=show_selected_file
            )
            dpg.add_text(tag="selected_file")

    def save_project_file(self, sender, data):
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
            with dpg.window(
                    label="Logger", pos=(932,32), 
                    height= self.SCREEN_HEIGHT-(self.window_buffer_size*18), width= 650,
                    ) as self.logger_window:
                    self.logger = dpg_logger.mvLogger(parent=self.logger_window)
        try: 
            if not dpg.is_item_visible(self.logger_window):
                create_logger_window()
            dpg.focus_item(self.logger_window)
        except:
            create_logger_window()

    def toggle_unlock_plots(self):
        if not self.plot_unlocked:
            self.plot_unlocked = True
            if self.logger_on: self.logger.log("Plot View Unlocked")
            dpg.set_axis_limits_auto(axis='DAC_xaxis')
            dpg.set_axis_limits_auto(axis='DAC_yaxis')
            dpg.set_axis_limits_auto(axis='V_xaxis')
            dpg.set_item_label(self.toggle_unlock_plots_button, "Lock Plots")
        else:
            self.plot_unlocked = False
            dpg.set_axis_limits(axis='DAC_xaxis', ymin=1627, ymax=1673)
            dpg.set_axis_limits(axis='DAC_yaxis', ymin=-10000, ymax=70000)
            dpg.set_axis_limits(axis='V_xaxis', ymin=1627, ymax=1673)
            if self.logger_on: self.logger.log("Plot View Locked")
            dpg.set_item_label(self.toggle_unlock_plots_button, "Unlock Plots")

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
        self.logger.log("Creating Voltage Plot")

        ax.plot(wl_list, voltage_list, 'o--', ms=0.85, linewidth=0.5, label=f"Voltage")

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
        dpg.delete_item("V_yaxis", children_only=True)

    def _write_plots(self):
        wl_list = []
        voltage_list = []
    
        for pair in self.voltage_data:
            target_wl, voltage = pair
            wl_list.append(target_wl)
            voltage_list.append(voltage)

        def create_plots(sender, data, cancel_pressed):
            #if self.logger_on: self.logger.log(f"{sender}: {dir}")
            if not cancel_pressed:
                #dpg.set_value('selected_file', value=dir)
                path = data[0]
                if self.logger_on: self.logger.log(f"Using Directory: {path}")
                dpg.delete_item(item='browser_window')
                print(F"NEW PATH: {path}")

                self.create_DAC_plot_file(path)
                self.create_voltage_plot_file(path, wl_list, voltage_list)
            
        CWD = os.path.dirname(os.path.realpath(__file__))
        with dpg.window(label="Open Project File", tag="browser_window"):
            dpge.add_file_browser(
                parent="browser_window",
                show_as_window=False,
                default_path=CWD,
                collapse_sequences=True,
                allow_multi_selection=False,
                show_ok_cancel = True, 
                dirs_only = True,
                callback=create_plots
            )

        
        #dpg.add_text(tag="selected_file")

    def export_data(self):
        self._write_plots()

    def config(self):
        def toggle_scan():
            if not self.scan_running:
                self.scan_running = True
                self.scan_paused = False
                scan_thread = threading.Thread(target=self._scan, args=(), daemon=True)
                scan_thread.start()
                if self.logger_on: self.logger.log("Scan Started")
                dpg.set_item_label(scan_button, "Pause")
            else:
                if not self.scan_paused:
                    self.scan_paused = True
                    if self.logger_on: self.logger.log("Scan Paused")
                    dpg.set_item_label(scan_button, "Resume")
                    dpg.show_item(reset_button)
                    return
                self.scan_paused = False
                if self.logger_on: self.logger.log("Scan Resumed")
                dpg.set_item_label(scan_button, "Pause")

        def reset_scan():
            self.scan_running = False
            self.scan_paused = False
            self.scan_tracker = 1627.5
            dpg.set_item_label(self.config.scan_button, "Start Scan")
            dpg.enable_item(scan_button)
            if self.logger_on: self.logger.log("Scan Reset")

        config_width = 200

        with dpg.window(
            label="Config", 
            pos=(8,48), 
            height=self.SCREEN_HEIGHT-self.window_buffer_size*10, 
            width=config_width, 
            no_close=True, 
            no_move=True) as laser_config_window:
            
            debug_button = dpg.add_checkbox(label="Debug Mode", default_value=self.debug, callback=self.toggle_debug)
            logger_button = dpg.add_checkbox(label="Log Output", default_value=True, callback=self.toggle_log_on)
            voltage_button = dpg.add_checkbox(label="Read Voltage", default_value=self.log_voltage, callback=self.toggle_log_voltage)
            save_tables_button = dpg.add_checkbox(label="Save Data", default_value=self.saving_LUT, callback=self.toggle_save_LUT)
            dpg.add_separator()
            dpg.add_spacer(height=self.window_buffer_size)

            COMS_LIST = self.Laser.get_ports_list()

            dpg.add_text("Serial COM Port")
            connect_to_laser_button = dpg.add_button(label="Connect to Laser", width=config_width-16, callback=self.connect_to_laser())
            serial_com_input = dpg.add_combo(items=COMS_LIST, width=config_width-16, default_value=self.port_name, callback=self.update_com_port)
            enable_laser_button = dpg.add_button(label="Enable Laser", width=config_width-16, callback=self.enable_laser)
            disable_laser_button = dpg.add_button(label="Disable Laser", width=config_width-16, callback=self.disable_laser)
            dpg.add_separator()
            dpg.add_spacer(height=self.window_buffer_size)
            check_if_on_button = dpg.add_button(label="Check Laser Status", width=config_width-16, callback=self.check_if_laser_on)
            setup_button = dpg.add_button(label="Update Laser", width=config_width-16, callback=self.setup)
            dpg.add_separator()
            dpg.add_spacer(height=self.window_buffer_size)
            scan_button = dpg.add_button(label="Start Scan", width=config_width-16, callback=toggle_scan)
            reset_button = dpg.add_button(label="Reset Scan", width=config_width-16, callback=reset_scan)
            dpg.add_separator()
            dpg.add_spacer(height=self.window_buffer_size)
            #plot_button = dpg.add_button(label="Show Plot", width=config_width-16, callback=show_plot)
            update_plot_buttom = dpg.add_button(label="Update DAC Plot", width = config_width-16, callback=self.update_DAC_plot)
            clear_voltage_plot_button = dpg.add_button(label="Clear Voltage Plot", width=config_width-16, callback=self.clear_voltage_plot)
            self.toggle_unlock_plots_button = dpg.add_button(label="Unlock Plots", width= config_width-16, callback=self.toggle_unlock_plots)
            dpg.add_separator()
            dpg.add_spacer(height=self.window_buffer_size)

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
            dpg.add_text("Packet Delay")
            #packet_delay_slider = dpg.add_slider_float(min_value=0, default_value=self.delay, max_value=1, width=config_width-16, callback=self.update_delay, tag="delay_slider")
            packet_delay_input = dpg.add_input_float(
                default_value=1.0,
                min_value= 0, 
                min_clamped=True, 
                max_clamped=False,
                width=config_width-16, 
                callback=self.update_delay)
            
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
            '''
            dpg.add_spacer(height=self.window_buffer_size)
            dpg.add_text("Table Index Range")
            start_index_input = dpg.add_input_int(label="Start", default_value=0, min_clamped=True, width=config_width/1.5, callback=self.update_start_index)
            end_index_input = dpg.add_input_int(label="End", default_value=9999, min_clamped=True, width=config_width/1.5, callback=self.update_end_index)
            '''

    def start_window(self):
        monitors = []
        for monitor in screeninfo.get_monitors(): monitors.append(monitor)

        monitor = monitors[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height - 50

        dpg.create_viewport(x_pos=0, y_pos=0, width=self.SCREEN_WIDTH, height=self.SCREEN_HEIGHT, title="Laser Control")
        
        

        def set_theme_light():
            light_theme = create_theme_imgui_light()
            dpg.bind_theme(light_theme)

        with dpg.window(tag="primary_window") as primary_window:
            dpg.set_primary_window(primary_window, True)
            self.open_logger()
            self.setup()

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
                    dpg.add_menu_item(label="Open LUT")
                    with dpg.menu(label="Save"):
                        dpg.add_menu_item(label="Save Project As", callback=self.save_project_file)
                        dpg.add_menu_item(label="Export Data", callback=self.export_data)
                        
            with dpg.theme(tag="plot_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

            with dpg.theme(tag="tracker_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)

            plot_width = self.SCREEN_WIDTH-240
            plot_height = self.SCREEN_HEIGHT/2 - 6*self.window_buffer_size

            self.config()
            def clear_primary_window():
                dpg.delete_item("voltage_window")
                dpg.delete_item("DAC_window")

            def load_DAC_tab():
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
                        dpg.focus_item(self.logger_window)

            def load_Voltage_tab():
                if not dpg.get_item_children("Voltage Data", 1):
                    with dpg.window(
                        label="Voltage Plot", 
                        pos=(216, plot_height+48+self.window_buffer_size), 
                        height=plot_height, 
                        width=plot_width, 
                        no_close=True, 
                        no_move=True,
                        tag="voltage_window") as self.voltage_plot_window:

                        self._init_voltage_plot()
                        
                        dpg.focus_item(self.logger_window)

            def tab_callback(sender, data):
                #dpg.delete_item("primary_window", children_only=True)
                #create_tab_bar()
                if dpg.get_item_configuration(data)['label'] == "Voltage Data":
                    clear_primary_window()
                    load_Voltage_tab()
                    
                if dpg.get_item_configuration(data)['label'] == "DAC View":
                    clear_primary_window()
                    load_DAC_tab()

            def create_tab_bar():
                with dpg.tab_bar(tag="tab_bar", callback= tab_callback) as tb:
                    dpg.add_tab(label="DAC View", tag="DAC View", parent="tab_bar")
                    dpg.add_tab(label="Voltage Data", tag="Voltage Data", parent="tab_bar")

            create_tab_bar()
            load_DAC_tab()

               
                    
                        

                    

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        #dpg.destroy_context()