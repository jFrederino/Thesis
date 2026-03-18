import time, threading, dearpygui.dearpygui as dpg, dearpygui_ext.logger as dpg_logger, numpy as np
from DBR import DBR_Spectrometer
import generate_table as table
import subprocess
import sys
dpg.create_context()

Laser = DBR_Spectrometer(mode = "auto",
    start_index = 0, 
    end_index = 9999,
    interpolation_type = "curve_fit", 
    interpolation_value = 3, 
    plot_choice = False, 
    plot_both = False,
    delay = 1, 
    sending_packets = False,
    log_voltage = False,
    gui = True)

DAC_list = Laser.get_table()


with dpg.window() as primary_window:
    logger = dpg_logger.mvLogger()
    logger.log("Welcome to the logger !")

    with dpg.theme(tag="plot_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 2, category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag="tracker_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)

    DAC_tracker_value = 1626
   
    with dpg.plot(label="DAC", height=400, width=700):

        DAC_type = 'FM'
        maximum = minimum = 0
        match DAC_type:
            case "FM": 
                maximum = 57954
                minimum = 668
            case "BM": 
                maximum =  43418
                minimum = 982
            case "PH":
                maximum =  17448
                minimum = 2496
            case "SOA": 
                maximum =  45527
                minimum = 14319

        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="xaxis")
        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="yaxis")
        wl= DAC_list[5]
        fm = DAC_list[1]
        bm = DAC_list[2]
        ph = DAC_list[3]
        soa = DAC_list[4]
        dpg.add_line_series(wl, fm, label="FM", parent="yaxis", tag="data")
        dpg.add_line_series(wl, bm, label="BM", parent="yaxis", tag="data2")
        dpg.add_line_series(wl, ph, label="PH", parent="yaxis", tag="data3")
        dpg.add_line_series(wl, soa, label="SOA", parent="yaxis", tag="data4")

        #data_x, data_y = generate_data(DAC_tracker_value)
        #dpg.add_line_series(data_x, data_y, parent="yaxis", tag="tracker")

        dpg.bind_item_theme("data", "plot_theme")
        dpg.bind_item_theme("data2", "plot_theme")
        dpg.bind_item_theme("data3", "plot_theme")
        dpg.bind_item_theme("data4", "plot_theme")
       # dpg.bind_item_theme("tracker", "tracker_theme")

    #dpg.add_slider_float(label="m", tag="slider", default_value=1600, min_value=1625, max_value=1675, callback=update_plot)
    
dpg.set_primary_window(primary_window, True)
dpg.create_viewport(width=900, height=600, title="DAC Plot WIP")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()