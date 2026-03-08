import time, threading, dearpygui.dearpygui as dpg, dearpygui_ext.logger as dpg_logger, numpy as np
from DBR import DBR_Spectrometer
import generate_table as table

dpg.create_context()


with dpg.window() as primary_window:
    pass



dpg.set_primary_window(primary_window, True)
dpg.create_viewport(width=900, height=600, title="DAC Plot WIP")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()