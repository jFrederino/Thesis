import serial, sys, os, glob, time, csv
import serial.tools.list_ports
import generate_table as table
import pyvisa
import os 

print(serial.__file__)

def val_to_split_hex(val): 
    msb, lsb = divmod(val, 0x100)
    return (hex(msb), hex(lsb))

def read_response():
    response = laser_serial.read(4)
    reg = response[0]
    value_msb = response[1]
    value_lsb = response[2]
    status = response[3]
    name = "Unknown"
    match reg:
        case 0x00: name = "Firmware Revision"
        case 0x01: name = "Protocol Version"
        case 0x02: name = "Product Identifier"
        case 0x0A: name = "Reserved"
        case 0x0B: name = "TEC Current" #32767 indicates 0 mA
        case 0x0C: name = "Laser Temperature Set Point" #given in centi-Celsius
        case 0x0D: name = "Laser Temperature Operating Point" #also given in centi-Celsius

        #This seems to be a current that doesnt change as the laser sweeps through the LUT, so it should not affect wavelength, probably.
        case 0x10: name = "GAIN Current DAC"
        #These are the controller registers we actually write to.
        case 0x13: name = "FM"
        case 0x12: name = "BM"
        case 0x11: name = "PH"
        case 0x14: name = "SOA"

        #These relate to the Laser's built in LUT Sweep functionality, which is currently not being used in this project.
        case 0x1E: name = "LUT Prepare Write"
        case 0x1F: name = "LUT Write Point" #automatically incremented after write
        case 0x20: name = "LUT Start Index"
        case 0x21: name = "LUT Length"
        case 0x27: name = "Sweep Configuration"
        case 0x28: name = "Step Sync Delay"
        case 0x29: name = "Step Period"

    status_message = "Unknown"
    match status:
        case 0x01:
            gain_value = (value_msb << 8) | value_lsb
            status_message = "Command Executed, Response Data Valid: "
            
        case 0x02: status_message = "Register not recognized. "
        case 0x03: status_message = "Register is Read Only. "
        case 0x04: status_message = "Command could not be executed. "
        case 0x05: status_message = "Value out of range. "
            
    if status != 0x01: 
        print(f"Error: status code 0x{status:X}")
        print(status_message)
        laser_serial.close()
        #sys.exit()

    return name, status, status_message, gain_value

def get_DAC_arrays(csv_table_path):
    IDX,FM,BM,PH,SOA,WL = [],[],[],[],[],[] 
    with open(csv_table_path, newline='') as f:
        reader = csv.reader(f, delimiter=',', quotechar='|')
        next(reader) #skip headers
        for row in reader:
            IDX.append(int(row[0]))
            FM.append(int(row[1]))
            BM.append(int(row[2]))
            PH.append(int(row[3]))
            SOA.append(int(row[4]))
            WL.append(float(row[5]))

    controllers = [IDX,FM,BM,PH,SOA,WL]
    return controllers

def set_laser_target_via_packets(fm_packet, bm_packet, ph_packet, soa_packet):
        packets = [ph_packet, bm_packet, fm_packet, soa_packet]
        responses = []
        for packet in packets:
            print(list(packet))
            laser_serial.write(packet)
            
            time.sleep(0.1)
            responses.append(read_response())
        return responses

def format_message(reg_num, data, write):
    return bytes([(reg_num | 0x80) & 0xFF, 
                  (data >> 8) & 0xFF, 
                  data & 0xFF, 
                  0x00])

def make_packet(DAC_type:str, value:int) -> bytes:
        '''
        Creates DAC packet (bytes object) that can be sent to the Laser immediately. Also sanatizes given values
        '''
        maximum = minimum = 0
        match DAC_type:
            case "FM": 
                register = (0x13 & 0x3F)|(1 << 7)
                maximum = 57954
                minimum = 668
            case "BM": 
                register = (0x12 & 0x3F)|(1 << 7)
                maximum =  43418
                minimum = 982
            case "PH":
                register = (0x11 & 0x3F)|(1 << 7)
                maximum =  17448
                minimum = 2496
            case "SOA": 
                register = (0x14 & 0x3F)|(1 << 7)
                maximum =  45527
                minimum = 14319

        if value > maximum: raise Exception(f"{DAC_type} value outside of acceptable range: {value} > {maximum}" )
        if value < minimum: raise Exception(f"{DAC_type} DAC value outside of acceptable range: {value} < {minimum}" )

        #msb, lsb = val_to_split_hex(value)
        m_encoding = format_message(register, value, write=True)
        #j_encoding = bytes([register, int(msb, 16), int(lsb, 16), 0x00])
        #print(list(m_encoding))
        #print(list(j_encoding))
        return m_encoding

def make_packets_list(DAC_list:list[list]) -> list[list]:
        '''
        Given DAC LUT will produce list containing all cooresponding packets, bundled with Target Wavelengths.
        '''
        packets = []
        for i in range(len(DAC_list[0])):
            fm_packet = make_packet("FM", DAC_list[1][i])
            bm_packet = make_packet("BM", DAC_list[2][i])
            ph_packet = make_packet("PH", DAC_list[3][i])
            soa_packet = make_packet("SOA", DAC_list[4][i])
            target_wl = DAC_list[5][i]

            packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])

        return packets

#voltage_data.append((target_wl, new_voltage_1))
#time.sleep(packet_delay)

'''
rm = pyvisa.ResourceManager()
#print(rm.list_resources())
choice = "USB0::0x2A8D::0x1601::MY60077980::INSTR"
voltmeter = rm.open_resource(choice)
print(voltmeter.query("*IDN?"))
#print(voltmeter.query("MEAS:VOLT:DC? 10,0.001"))
'''
DAC_list = get_DAC_arrays('DBR_FP4209/myGUI/UU341_LUT_0v0.csv')
laser_serial = serial.Serial(
        port = "COM4", 
        baudrate = 9600, 
        bytesize = serial.EIGHTBITS,
        parity = serial.PARITY_NONE, 
        timeout = 1) 

packets = make_packets_list(DAC_list)
num_packets = len(packets)

while(True):
    for i in range(7486, 7486+20):
        a = input()
    #controller = input("controller: ")
    #i = int(input("Input LUT table index (starts at 0): "))

        fm, bm, ph, soa, target_wl = packets[i][0], packets[i][1], packets[i][2], packets[i][3], packets[i][4]
        print(f'{list(fm)}, {list(bm)}, {list(ph)}, {list(soa)}, {target_wl}')
        print(packets[i])
        #new_voltage = read_voltage()
        #print(new_voltage)
        responses:list[tuple] = set_laser_target_via_packets(fm, bm, ph, soa)

        def write_fm(): 
            print("fm")
            laser_serial.write(packets[i][0])
        def write_bm(): 
            laser_serial.write(packets[i][1])
        def write_ph(): 
            laser_serial.write(packets[i][2])
        def write_soa(): 
            laser_serial.write(packets[i][3])
        
        '''
        match controller.lower():
            case 'fm': write_fm()
            case 'bm': write_bm()
            case 'ph': write_ph()
            case 'soa': write_soa()
        '''
        #print(read_response())
        for response in responses: print(response)
        time.sleep(0.1)
    
