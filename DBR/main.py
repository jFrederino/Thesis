# JAMES USHER 2026

from DBR import DBR_Spectrometer

laser = DBR_Spectrometer()
<<<<<<< HEAD
laser.enable()
=======
#laser.enable()
#laser.disable()
laser.scan(mode="manual")
>>>>>>> 08c31ef (curve_fit now adheres to LUT boundaries)

#laser.set_laser_target(10578, 4138, 9938, 22767)
#laser.set_laser_target(10578, 4138, 9778, 22711)
#laser.set_laser_target(10372, 4011, 10242, 22870)

laser.scan(mode="manual")
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