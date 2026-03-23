# JAMES USHER 2026

from DBR import DBR_Spectrometer
from GUI import GUI


GUI_Main = GUI(debug=True)

#GUI_Main = GUI()

GUI_Main.start_window()

'''
input("-------")

laser2 = DBR_Spectrometer(
    mode = "auto",
    start_index = 3000, 
    end_index = 3200,
    interpolation_type = "curve_fit", 
    interpolation_value = 3, 
    plot_choice = True, 
    plot_both = True,
    delay = 0.01, 
    sending_packets = False, 
    sanatize = False, 
    log_voltage = False)

input("to continue enter anything: ")

laser2.scan()

#dbr.laser_auto_scan(LOG_VOLTAGE = True)a
'''