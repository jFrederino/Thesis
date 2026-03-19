import time, threading, dearpygui.dearpygui as dpg, dearpygui_ext.logger as dpg_logger, numpy as np
from DBR import DBR_Spectrometer
import generate_table as table
import subprocess
import sys
from math import sin, cos

class GUI:
    def __init__(self, debug: bool = False):
        self.debug = debug

        self.fm_input = 0
        self.bm_input = 0
        self.ph_input = 0
        self.soa_input = 0

        self.scan_tracker = 1627.5 #x value of scan tracker line on DAC plot, and table index.

        self.scan_running = False
        self.scan_paused = False

        #   scan parameters for DBR object init
        self.start_index = 0 
        self.end_index = 9999
        self.interpolation_type = "linear"
        self.interpolation_value = 0
        self.delay = 1
        self.sending_packets = True
        self.log_voltage = False

        self.DAC_list = [[0],[0],[0],[0],[0],[0]]
        dpg.create_context()
        
    def setup(self):
        
        self.Laser = DBR_Spectrometer(mode = "auto",
            start_index = self.start_index, 
            end_index = self.end_index,
            interpolation_type = self.interpolation_type, 
            interpolation_value = self.interpolation_value, 
            plot_choice = False, 
            plot_both = False,
            delay = self.delay, 
            sending_packets = self.sending_packets,
            log_voltage = self.log_voltage,
            gui = True)

        self.logger.log("Laser Setup Updated")
        self.DAC_list = self.Laser.get_table()
        self.logger.log("DAC Table Updated")

    def enable_laser(self):
        self.Laser.enable()
    
    def disable_laser(self):
        self.Laser.disable()

    def _scan(self):
        
        self.logger.log("Starting Scan")
        packets = self.Laser.make_packets_list(self.DAC_list)
        num_packets = len(packets)
        self.logger.log_info(f"Packet : {num_packets}")

        for i in range(num_packets):

            while self.scan_paused: 
                #self.logger.log_debug("Paused")
                time.sleep(0.1)
            if not self.scan_running: return

            self.scan_tracker = i

            if self.Laser.sending_packets: 
                fm, bm, ph, soa, target_wl = packets[i][0], packets[i][1], packets[i][2], packets[i][3], packets[i][4]

                for packet in packets[i]:
                    self.scan_tracker = target_wl
                    self.update_plot()
                    if self.debug:
                        #self.Laser.set_laser_target(fm, bm, ph, soa)
                    
                        self.logger.log_info(f'Sending : {packet}')
                        name, status, status_message, gain_value = "debug_name", 0x01, "Command Executed, Response Data Valid: ", i
                        self.logger.log_debug(f'{name} : {status} : {status_message}{gain_value} \n')
                        #self.logger.log_info("-"*60)
                        
                    else: 
                        self.Laser.set_laser_target_via_packets(fm, bm, ph, soa)
                        self.logger.log_info(f'Sending : {packet}')
                        name, status, status_message, gain_value = self.Laser.read_response()
                        self.logger.log_info(f'{name} : {status} : {status_message}{gain_value} \n')
                        #self.logger.log_info("-"*60)
                    
                time.sleep(self.Laser.delay)
                if self.Laser.log_voltage: 
                    self.Laser.voltage_data.append(self.Laser.read_voltage())

    def generate_data(self, x):
        data_x, data_y = [], []
        for y in range(0, 75000):
            data_x.append(x)
            data_y.append(y)
        return data_x, data_y

    def update_plot(self):
        data_x, data_y = self.generate_data(self.scan_tracker)
        #print(data_x[0])
        dpg.configure_item('tracker', x=data_x, y=data_y)
        
    def start_window(self):

        def open_logger():
            with dpg.window(label="Logger", pos=(932,32), height=800, width=600) as logger_window:
                self.logger = dpg_logger.mvLogger(parent=logger_window)

        dpg.create_viewport(width=1600, height=900, title="Laser Control")
        open_logger()

        def toggle_scan():
            if not self.scan_running:
                self.scan_running = True
                self.scan_paused = False
                scan_thread = threading.Thread(target=self._scan, args=(), daemon=True)
                scan_thread.start()
                dpg.set_item_label(scan_button, "Pause")
            else:
                if not self.scan_paused:
                    #print("Paused...")
                    self.scan_paused = True
                    dpg.set_item_label(scan_button, "Resume")
                    dpg.show_item(reset_button)
                    return
                #print("Resuming...")
                self.scan_paused = False
                dpg.set_item_label(scan_button, "Pause")
                #dpg.hide_item(reset_button)

        def reset_scan():
            self.scan_running = False
            self.scan_paused = False
            self.scan_tracker = 1627.5

            dpg.set_item_label(scan_button, "Start Scan")

            dpg.enable_item(scan_button)
            #dpg.hide_item(reset_button)

        def show_plot():
            
            with dpg.theme(tag="plot_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

            with dpg.theme(tag="tracker_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)

            with dpg.window(label="DAC Plot", pos=(216,32), height=440, width=716) as plot_window:
                with dpg.plot(label="DAC Values", parent=plot_window,  height=400, width=700):
                    dpg.add_plot_legend(show=True, location=9)
                    dpg.add_plot_axis(dpg.mvXAxis, label="Wavelength", tag="xaxis")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Controller Value", tag="yaxis")
                    idx, wl, fm, bm, ph, soa = self.DAC_list[0], self.DAC_list[5], self.DAC_list[1], self.DAC_list[2], self.DAC_list[3], self.DAC_list[4]
                    dpg.add_line_series(wl, fm, label="FM", parent="yaxis", tag="data")
                    dpg.add_line_series(wl, bm, label="BM", parent="yaxis", tag="data2")
                    dpg.add_line_series(wl, ph, label="PH", parent="yaxis", tag="data3")
                    dpg.add_line_series(wl, soa, label="SOA", parent="yaxis", tag="data4")

                    data_x, data_y = self.generate_data(self.scan_tracker)
                    dpg.add_line_series(data_x, data_y, parent="yaxis", tag="tracker")

                    dpg.bind_item_theme("data", "plot_theme")
                    dpg.bind_item_theme("data2", "plot_theme")
                    dpg.bind_item_theme("data3", "plot_theme")
                    dpg.bind_item_theme("data4", "plot_theme")
                    dpg.bind_item_theme("tracker", "tracker_theme")

        with dpg.window() as primary_window:
            with dpg.menu_bar():
                 with dpg.menu(label="Tools"):
                    dpg.add_menu_item(label="Logger", callback=open_logger)
            dpg.set_primary_window(primary_window, True)

            config_width = 200
            with dpg.window(label="Config", pos=(8,32), height=800, width=config_width) as laser_config_window:
                setup_button = dpg.add_button(label="Set Up Laser", width=config_width-16, callback=self.setup)
                scan_button = dpg.add_button(label="Start Scan", width=config_width-16, callback=toggle_scan)
                reset_button = dpg.add_button(label="Reset Scan", width=config_width-16, callback=reset_scan)
                plot_button = dpg.add_button(label="Show Plot", width=config_width-16, callback=show_plot)

                dpg.add_separator()

                interpolation_type_input = dpg.add_combo(("Linear", "Curve Fit"))










        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        #dpg.destroy_context()