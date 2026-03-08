import time
import threading
import dearpygui.dearpygui as dpg
import dearpygui_ext.logger as dpg_logger
from DBR import DBR_Spectrometer
import generate_table as table
import numpy as np
dpg.create_context()




running = False
paused = False
progress = 0

# Dont use globals as storage -- at least wrap in a class
class DataValues():
	clicks = 0

def clickMe_callback(sender, value, user_data):
    logger.log_info("I was clicked !")
    # increment clickCount
    DataValues.clicks += 1

    # update text
    dpg.set_value(user_data, f"clicks: {DataValues.clicks}")

data = DataValues()


def run_task():
    global running
    global paused
    global progress
    print("Running...")
    
    points = np.linspace(1627.5, 1672.4955, 10000)
    for i in points:

        while paused:
            time.sleep(0.1)
            
        if not running:
            return
        progress = i

        #print(i)
        dpg.set_value(progress_bar, 1/10000 * (i))
        dpg.configure_item(progress_bar, overlay=f"{i}")

        data_x, data_y = generate_data(i)
        dpg.configure_item('tracker', x=data_x, y=data_y)
        
        time.sleep(0.1)

    print("Finished")
    running = False
    dpg.set_item_label(start_pause_resume_button, "Finished")
    dpg.disable_item(start_pause_resume_button)
    dpg.show_item(reset_button)

def start_stop_callback():
    global running
    global paused
    if not running:
        print("Started")
        running = True
        paused = False
        thread = threading.Thread(target=run_task, args=(), daemon=True)
        thread.start()
        dpg.set_item_label(start_pause_resume_button, "Pause")
    else:
        if not paused:
            print("Paused...")
            paused = True
            dpg.set_item_label(start_pause_resume_button, "Resume")
            dpg.show_item(reset_button)
            return
        print("Resuming...")
        paused = False
        dpg.set_item_label(start_pause_resume_button, "Pause")
        dpg.hide_item(reset_button)

def reset_callback():
    global running
    global paused
    global progress
    running = False
    paused = False
    progress = 0
    dpg.set_value(progress_bar, 0)
    dpg.configure_item(progress_bar, overlay="0%")
    dpg.set_item_label(start_pause_resume_button, "Start")
    dpg.enable_item(start_pause_resume_button)
    dpg.hide_item(reset_button)

def generate_data(x):
    data_x, data_y = [], []
    for y in range(0, 100000):
        data_x.append(x)
        data_y.append(y)
    return data_x, data_y

def update_plot():
    data_x, data_y = generate_data(dpg.get_value("slider"))
    dpg.configure_item('tracker', x=data_x, y=data_y)
    #dpg.fit_axis_data("xaxis")
    #pg.fit_axis_data("yaxis")


DAC_Table = table.DAC_Table(interpolate_type='linear', interpolate_value=0, start_index=0, end_index=9999)

path = DAC_Table.generate_DAC_table(plot_choice=False) #also plots if enabled

DAC_list = DAC_Table.get_DAC_arrays(path)  #read values from new table

def print_me(sender):
    print(f"Menu Item: {sender}")
    
with dpg.window() as primary_window:
    with dpg.menu_bar():
        with dpg.window(label="Window 01", width=300, height=200, pos=[300, 300]):
            textControl = dpg.add_text("Clicks: 0")
            dpg.add_text(tag="line1", default_value="line 1")
            dpg.add_text(tag="line2", default_value="line 2")
            dpg.add_text(tag="line3", default_value="line 3")
            dpg.add_button(label="Click me !", callback=clickMe_callback, user_data=textControl)

        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Save", callback=print_me)
            dpg.add_menu_item(label="Save As", callback=print_me)

            with dpg.menu(label="Settings"):
                dpg.add_menu_item(label="Setting 1", callback=print_me, check=True)
                dpg.add_menu_item(label="Setting 2", callback=print_me)

        dpg.add_menu_item(label="Help", callback=print_me)

        with dpg.menu(label="Widget Items"):
            dpg.add_checkbox(label="Pick Me", callback=print_me)
            dpg.add_button(label="Press Me", callback=print_me)
            dpg.add_color_picker(label="Color Me", callback=print_me)

    with dpg.group(horizontal=True):
        start_pause_resume_button = dpg.add_button(label="Start", width=70, callback=start_stop_callback)
        reset_button = dpg.add_button(label="Reset", width=70, callback=reset_callback)
        dpg.hide_item(reset_button)

    progress_bar = dpg.add_progress_bar(default_value=0, width=-1, overlay="0%")

    with dpg.theme(tag="plot_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            #dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 255, 0), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag="tracker_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)

    DAC_tracker_value = 1626
   
    with dpg.plot(label="DAC", height=400, width=700):

        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="xaxis")
        #dpg.set_axis_limits(dpg.last_item(), 1625, 1675)

        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="yaxis")
        #dpg.set_axis_limits(dpg.last_item(), 0, 60000)

        wl= DAC_list[5]
        fm = DAC_list[1]
        bm = DAC_list[2]
        ph = DAC_list[3]
        soa = DAC_list[4]
        dpg.add_line_series(wl, fm, label="FM", parent="yaxis", tag="data")
        dpg.add_line_series(wl, bm, label="BM", parent="yaxis", tag="data2")
        dpg.add_line_series(wl, ph, label="PH", parent="yaxis", tag="data3")
        dpg.add_line_series(wl, soa, label="SOA", parent="yaxis", tag="data4")

        data_x, data_y = generate_data(DAC_tracker_value)
        dpg.add_line_series(data_x, data_y, parent="yaxis", tag="tracker")

        dpg.bind_item_theme("data", "plot_theme")
        dpg.bind_item_theme("data2", "plot_theme")
        dpg.bind_item_theme("data3", "plot_theme")
        dpg.bind_item_theme("data4", "plot_theme")
        dpg.bind_item_theme("tracker", "tracker_theme")

    dpg.add_slider_float(label="m", tag="slider", default_value=1600, min_value=1625, max_value=1675, callback=update_plot)

    logger = dpg_logger.mvLogger()

    logger.log("Welcome to the logger !")




dpg.set_primary_window(primary_window, True)
dpg.create_viewport(width=900, height=600, title="DAC Plot WIP")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()