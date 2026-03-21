import time, threading, dearpygui.dearpygui as dpg, dearpygui_ext.logger as dpg_logger, numpy as np
from DBR import DBR_Spectrometer
import generate_table as table
import sys
import screeninfo

class GUI:
    def __init__(self, debug: bool = False):
        self.debug = debug

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
        self.DAC_list = [[],[],[],[],[],[]]

        self.SCREEN_HEIGHT = 480    
        self.SCREEN_WIDTH = 854
        self.window_buffer_size = 8
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
                    self.update_tracker()
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


    

    def update_plot(self):
        
        try: 
            dpg.delete_item(self.DAC_plot)
            self._init_DAC_plot()
        except: pass
        
        idx, wl, fm, bm, ph, soa = self.DAC_list[0], self.DAC_list[5], self.DAC_list[1], self.DAC_list[2], self.DAC_list[3], self.DAC_list[4]
        if idx:
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

            dpg.set_axis_limits_auto(axis='xaxis')
            dpg.set_axis_limits_auto(axis='yaxis')

    def generate_data(self, x):
        data_x, data_y = [], []
        for y in range(0, 75000):
            data_x.append(x)
            data_y.append(y)
        return data_x, data_y

    def update_tracker(self):
        data_x, data_y = self.generate_data(self.scan_tracker)
        #print(data_x[0])
        dpg.configure_item('tracker', x=data_x, y=data_y)

    def update_delay(self, sender, data):
        self.delay = data
        self.logger.log(f"Delay: {self.delay}")

    def update_start_index(self, sender, data:str):
        if data.isdigit():
            self.start_index = int(data)
            self.logger.log(f"Start Index = {data}")
        else: self.logger.log_error(f"Start Index: {data} is non integer.")

    def update_end_index(self, sender, data:str):
        if data.isdigit():
            self.end_index = int(data)
            self.logger.log(f"End Index = {data}")
        else: self.logger.log_error(f"End Index: {data} is non integer.")

    def toggle_debug(self, sender, data:str):
        self.debug = bool(data)
        self.logger.log(f"Debug = {self.debug}")

    def _init_DAC_plot(self): 
            plot_width = self.SCREEN_WIDTH-240
            plot_height = self.SCREEN_HEIGHT/2 - 2*self.window_buffer_size

            with dpg.plot(label="DAC Values",  parent= self.DAC_plot_window, height=plot_height-40, width=plot_width-24, tag="DAC_plot") as self.DAC_plot:
                dpg.add_plot_legend(show=True, location=9)

                dpg.add_plot_axis(dpg.mvXAxis, parent="DAC_plot", label="Wavelength", tag="xaxis")
                dpg.add_plot_axis(dpg.mvYAxis, parent="DAC_plot", label="Controller Value", tag="yaxis")

                dpg.set_axis_limits(axis='xaxis', ymin=1627, ymax=1673)
                dpg.set_axis_limits(axis='yaxis', ymin=-100, ymax=75000)

            #self.update_plot()

    def open_DAC_table(self):
        with dpg.window(label="DAC LUT", pos=(932,32), height= self.SCREEN_HEIGHT-(self.window_buffer_size*10), width= 500) as DAC_table_window:
            table_tag = dpg.generate_uuid()
            with dpg.table(header_row=True, tag=table_tag, row_background=True,
                        borders_innerH=True, borders_outerH=True, borders_innerV=True,
                        borders_outerV=True):

                # use add_table_column to add columns to the table,
                # table columns use child slot 0
                dpg.add_table_column(label="IDX")
                dpg.add_table_column(label="FM DAC")
                dpg.add_table_column(label="BM DAC")
                dpg.add_table_column(label="PH DAC")
                dpg.add_table_column(label="SOA DAC")
                dpg.add_table_column(label="WL Target")
                
                # add_table_next_column will jump to the next row
                # once it reaches the end of the columns
                # table next column use slot 1
                for i in range(len(self.DAC_list[0])):
                    with dpg.table_row():
                        for j in range(0, 6):
                            text_tag = dpg.add_text(f"{self.DAC_list[j][i]}")
                          

    def start_window(self):
        monitors = []
        for monitor in screeninfo.get_monitors(): monitors.append(monitor)

        monitor = monitors[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height - 50

        #print(str(self.SCREEN_WIDTH) + 'x' + str(self.SCREEN_HEIGHT))

        def open_logger():
            with dpg.window(
                label="Logger", pos=(932,32), 
                height= self.SCREEN_HEIGHT-(self.window_buffer_size*10), width= 500
                ) as logger_window:

                self.logger = dpg_logger.mvLogger(parent=logger_window)

        dpg.create_viewport(x_pos=0, y_pos=0, width=self.SCREEN_WIDTH, height=self.SCREEN_HEIGHT, title="Laser Control")
        
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

        

        with dpg.window() as primary_window:
            with dpg.menu_bar():
                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Logger", callback=open_logger)
                    dpg.add_menu_item(label="DAC Table", callback=self.open_DAC_table)





            dpg.set_primary_window(primary_window, True)


            with dpg.theme(tag="plot_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

            with dpg.theme(tag="tracker_theme"):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)

            plot_width = self.SCREEN_WIDTH-240
            plot_height = self.SCREEN_HEIGHT/2 - 2*self.window_buffer_size

            with dpg.window(label="DAC Plot", pos=(216,32), height=plot_height, width=plot_width, no_close=True) as self.DAC_plot_window:
                self._init_DAC_plot()

            config_width = 200

            with dpg.window(label="Config", pos=(8,32), height=self.SCREEN_HEIGHT-self.window_buffer_size*10, width=config_width, no_close=True) as laser_config_window:
                dpg.add_checkbox(label="Debug Mode", callback=self.toggle_debug)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                enable_laser_button = dpg.add_button(label="Enable Laser", width=config_width-16, callback=self.enable_laser)
                disable_laser_button = dpg.add_button(label="Disable Laser", width=config_width-16, callback=self.disable_laser)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                setup_button = dpg.add_button(label="Update Laser", width=config_width-16, callback=self.setup)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                scan_button = dpg.add_button(label="Start Scan", width=config_width-16, callback=toggle_scan)
                reset_button = dpg.add_button(label="Reset Scan", width=config_width-16, callback=reset_scan)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                #plot_button = dpg.add_button(label="Show Plot", width=config_width-16, callback=show_plot)
                update_plot_buttom = dpg.add_button(label="Update Plot", width = config_width-16, callback=self.update_plot)
                dpg.add_separator()
                dpg.add_spacer(height=self.window_buffer_size)
                dpg.add_text("Interpolation Type")
                interpolation_type_input = dpg.add_combo(items=("Linear", "Curve Fit"), width=config_width-16)
                dpg.add_text("Delay")
                packet_delay_input = dpg.add_slider_float(min_value=0, max_value=1, width=config_width-16, callback=self.update_delay)
                start_index_input = dpg.add_input_text(label="Start Index", width=config_width/2, callback=self.update_start_index)
                end_index_input = dpg.add_input_text(label="End Index", width=config_width/2, callback=self.update_end_index)
                




        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        #dpg.destroy_context()