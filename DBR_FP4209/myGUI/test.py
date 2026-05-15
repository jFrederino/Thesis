import codecs

def format_message(reg_num, data, write):
    array = bytearray(4) #MUTABLE!!
    
    if write:
        array[0] = (reg_num | 0x80) & 0xFF
    else:
        array[0] = reg_num & 0xFF
        
    array[1] = (data >> 8) & 0xFF  # High byte
    array[2] = data & 0xFF         # Low byte
    array[3] = 0
    
    return array

import sys
def val_to_split_hex(val): 
        msb, lsb = divmod(val, 0x100)
        return (hex(msb), hex(lsb))

fm_val = 11425
msb, lsb = val_to_split_hex(fm_val)
register = (0x13)|(1 << 7)
print(f"default encoding= {sys.getdefaultencoding()}")
data = [register, int(msb, 16), int(lsb, 16), 0x00]
print(data)

bytes_encoded = bytes(data)
print(bytes_encoded)

new_list = list(bytes_encoded)
print(new_list)
decoded_list = []
for val in new_list: 
    decoded_list.append(hex(val))

print(f"{new_list}")
print(decoded_list)

print(list(format_message(register, fm_val, write=True)))