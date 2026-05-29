# JAMES USHER 2026
import serial, sys, os, glob, time
import serial.tools.list_ports
from timeit import default_timer as timer
import generate_table as table
import pathlib 


class DBR_Spectrometer:
    def __init__(self, 
        port_name:str = "COM4", 
        start_wl: float = 1627.5, 
        end_wl: float = 1672.4955, 
        interpolation_type: str = "true_linear", 
        interpolation_value:int = 3,
        saving_LUT: bool = True, 
        **port):
        
        self.start_wl = start_wl
        self.end_wl = end_wl
        self.interpolation_type = interpolation_type
        self.interpolation_value = interpolation_value
        self.saving_LUT = saving_LUT

        self._laser_on = False
        self._laser_connected = False
        self._default_serial_port = port_name
        
        if port: self._laser_serial = port["port"]

    def val_to_split_hex(self, val): 
        msb, lsb = divmod(val, 0x100)
        return (hex(msb), hex(lsb))

    def check_if_on(self) -> bool:
        read_packet = bytes([16, 0x00, 0x00, 0x00])
        self._laser_serial.write(read_packet)
        response = self.read_response()
        name, status, status_message, gain_value = response
        res = False
        if status == 1:
            if gain_value == 0: 
                res = False
            else: 
                res = True
        else: 
            print(status_message)
        return response, res


    def enable(self): 
        '''
        Turns the laser output on. Connects to default Serial Port {self._default_serial_port} if not connected. Defaults to 1627.5 nm output.
        '''
        self.write_register(21, 0)
        self.write_register(16, 40959)

        self._laser_on = True

    def disable(self): 
        '''
        Turns the laser output off. Does NOT disconnect from Serial Connection.
        '''
        self.write_register(39, 0)
        self.write_register(16, 0)

    def set_default_serial_port(self, port_name:str):
        self._default_serial_port = port_name
        print(f"Default Serial Port set to: {self._default_serial_port}")


    def message_exchange(self, command):
        # Send the 4-byte command
        self._laser_serial.write(command)

        response = self.read_response()
        return response

    def format_message(self, reg_num, data, write):
        array = bytearray(4) #MUTABLE!!
        
        if write:
            array[0] = (reg_num | 0x80) & 0xFF
        else:
            array[0] = reg_num & 0xFF
            
        array[1] = (data >> 8) & 0xFF  # High byte
        array[2] = data & 0xFF         # Low byte
        array[3] = 0
        
        return array

    def write_register(self, reg_num, reg_data):
        self.message_exchange(self.format_message(reg_num, reg_data, write=True))


    def make_packet(self, DAC_type:str, value:int) -> bytes:
        '''
        Creates DAC packet (bytes object) that can be sent to the Laser immediately. Also sanatizes given values
        '''
        maximum = minimum = 0
        match DAC_type:
            case "FM": 
                register = (0x13)|(1 << 7)
                maximum = 57954
                minimum = 668
            case "BM": 
                register = (0x12)|(1 << 7)
                maximum =  43418
                minimum = 982
            case "PH":
                register = (0x11)|(1 << 7)
                maximum =  17448
                minimum = 2496
            case "SOA": 
                register = (0x14)|(1 << 7)
                maximum =  45527
                minimum = 14319

        if value > maximum: raise Exception(f"{DAC_type} value outside of acceptable range: {value} > {maximum}" )
        if value < minimum: raise Exception(f"{DAC_type} DAC value outside of acceptable range: {value} < {minimum}" )

        new_packet = self.format_message(reg_num=register, data=value, write=True)
    
        return new_packet
    

    def get_duplicates(self, data:list):
        from collections import Counter
        # Convert sublists to tuples to make them hashable
        counts = Counter(tuple(x) for x in data)

        # List only the items that appear more than once
        duplicates = [list(item) for item, count in counts.items() if count > 1]
        return duplicates

    def make_packets_list(self, DAC_list:list[list]) -> list[list]:
        '''
        Given DAC LUT will produce list containing all cooresponding packets, bundled with Target Wavelengths.
        '''
        
        packets = []
        for i in range(len(DAC_list[0])):
            fm_packet = self.make_packet("FM", DAC_list[1][i])
            bm_packet = self.make_packet("BM", DAC_list[2][i])
            ph_packet = self.make_packet("PH", DAC_list[3][i])
            soa_packet = self.make_packet("SOA", DAC_list[4][i])
            target_wl = DAC_list[5][i]

            packets.append([fm_packet, bm_packet, ph_packet, soa_packet, target_wl])

        #print(self.get_duplicates(packets)) No duplicates.
        return packets

    def set_laser_target(self, fm_val:int, bm_val:int, ph_val:int, soa_val:int):
        '''
        Will create and send packets to update laser output to wavelegnth cooresponding tp given DAC values.
        '''
        fm_packet = self.make_packet("FM", fm_val)
        bm_packet = self.make_packet("BM", bm_val)
        ph_packet = self.make_packet("PH", ph_val)
        soa_packet = self.make_packet("SOA", soa_val)
        packets = [fm_packet, bm_packet, ph_packet, soa_packet]

        for packet in packets:
            self._laser_serial.write(packet)
            self.read_response()

    def set_laser_target_via_packets(self, fm_packet, bm_packet, ph_packet, soa_packet):
        packets = [ph_packet, bm_packet, fm_packet, soa_packet]
    
        responses = []
        for packet in packets:
            self._laser_serial.write(packet)
            responses.append(self.read_response())
        return responses

    def get_ports_list(self):
        ports = serial.tools.list_ports.comports()
        ports_list = []
        for port, desc, hwid in sorted(ports):
            ports_list.append(port)
        return ports_list
    
    def connect_to_laser(self, target_port:str):
        if self._laser_connected: print(f"Laser is already connected to {self._laser_serial.name}")
        try: 
            self._laser_serial
        except:
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in sorted(ports):
                print("{} : {} [{}]".format(port, desc, hwid))

            self._laser_serial = serial.Serial(
                port = self._default_serial_port, 
                baudrate = 9600, 
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE, 
                timeout = 1) 
            
            print(f"Serial port {self._laser_serial.name} opened successfully.")
            self._laser_connected = True

    def disconnect_from_laser(self):
        if not self._laser_connected: print("Laser is already disconnected. ")
        print("Closing Serial Port...")
        name = self._laser_serial.name
        self._laser_serial.close()
        self._laser_connected = False
        print(f"Serial Port {name} Closed.")

    def read_response(self):
        response = self._laser_serial.read(4)
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

            #These relate to the Laser's built in LUT Sweep functionality, but some of them, like LUT Start Index must be updated when enabling the Laser.
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
            self._laser_serial.close()

        return name, status, status_message, gain_value

    def get_table(self):
        table_list = []
        logger_message = ''

        if self.interpolation_type == "true_linear": 
            table_list = glob.glob(f'**/DAC_Tables/True_Linear_{self.interpolation_value, self.start_wl, self.end_wl}.csv', recursive=True)
            print("FETCH TRUE LINEAR")
            print(table_list)

        if self.interpolation_type == "linear_extrapolation": 
            table_list = glob.glob(f'**/DAC_Tables/Linear_Extrapolation_{self.interpolation_value, self.start_wl, self.end_wl}.csv', recursive=True)
            print("FETCH LINEAR EXTRAPOLATION")
            print(table_list)

        if self.interpolation_type == "line_fit": 
            table_list = glob.glob(f'**/DAC_Tables/Line_Fit_{self.interpolation_value, self.start_wl, self.end_wl}.csv', recursive=True)
            print("FETCH LINE FIT")
            print(table_list)
            
        try:
            self.DAC_Table
        except: 
            self.DAC_Table = table.DAC_Table(
                interpolate_type=self.interpolation_type, interpolate_value=self.interpolation_value, 
                start_wl=self.start_wl, end_wl=self.end_wl)

        if not table_list:
            path = self.DAC_Table.generate_DAC_table(interpolate_type=self.interpolation_type) #also plots if enabled
            logger_message = f"Generated New Table: {path}"

        if table_list: 
            path = table_list[0]
            logger_message = f"Found Existing Table: {path}"

        DAC_list = self.DAC_Table.get_DAC_arrays(path)  #read values from table

        if not self.saving_LUT: pathlib.Path.unlink(path) 
        #NOTE: this will delete even previously saved tables, if reusing one. 
        # It deletes what DBR is using for current scan after the scan finishes.

        return DAC_list, logger_message
   

   
   
