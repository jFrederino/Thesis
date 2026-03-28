# JAMES USHER 2026

from Spectrometer import DBR_Spectrometer

laser = DBR_Spectrometer()
laser.connect_to_laser("COM4")
laser.enable()
laser.disable()
laser.disconnect_from_voltmeter()
