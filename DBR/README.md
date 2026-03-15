

# PROGRAM FLOWCHART

## main.py
    init DBR_Spectrometer obj
        attributes: 
            mode (manual allows for setting parameters via command line)
            start_index
            end_index
            interpolation_type (linear interpolation or linear curve fitting)
            interpolation_value
            plot_choice
            plot_both 
            delay (delay between sets of four packets)
            sending_packets 
            log_voltage = False

    laser.scan() -> class method in DBR.py

## DBR.py

### laser.scan()
    scans one pass through table defined by DBR_Spectrometer object attributes. 
        
    
