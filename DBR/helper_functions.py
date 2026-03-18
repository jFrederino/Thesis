# JAMES USHER 2026

import fastnumbers 
import ctypes

def get_user_input(message:str, input_type:str):
    '''
    Parameters
    ----------
    message : str        
        message prompting input
    input_type : str     
        type of input required
    accepts types : "int", "float", "str", "y/n"

    Returns
    -------
    user_input : str
        if input_type = "str", returns input string
    user_input : int
        if input_type = "int", returns input int
    user_input : float
        if input_type = "float", returns input float
    user_input : Bool
        if input_type = "y/n", returns Boolean
    '''
    user_input = input(message)
    if fastnumbers.check_int(user_input): user_input_type = "int"
    elif fastnumbers.check_float(user_input): user_input_type = "float"
    else: 
        user_input_type = "str"
        if input_type == "y/n": 
            if user_input.lower() not in ['y','n']:
                print(f"ERROR please input: Y/N")
                return get_user_input(message, input_type)
            if user_input.lower() == 'y': return True
            return False
    
        if user_input_type == input_type:
            return user_input
        
    if input_type == "float" and user_input_type == "int": #allows for integer inputs as floats (less strict float inputs)
        user_input_type = "float"

    if user_input_type == input_type:

        if input_type == "int":
            print(f"returning {int(user_input)}")
            return int(user_input)
        
        if input_type == "float": 
            print(f"returning {float(user_input)}")
            return float(user_input)
    else:
        print(f"ERROR please input: {input_type}")
        return get_user_input(message, input_type)







def val_to_split_hex(val): 
    '''
    Parameters
    ----------
    val : int 

    Returns
    -------
    (msb, lsb) : tuple of hex values (str)
    '''
    #old_msb = int(hex(val)[2:4], base=16)
    #old_lsb = int(hex(val)[4:6], base=16)
    #bytes() object doesnt take strings
    #print(f'old: {hex(old_msb)}, {hex(old_lsb)}')
    
    #print(hex(val)) #4011 -> 0xfab
    msb, lsb = divmod(val, 0x100)

    return (hex(msb), hex(lsb))

'''
print(val_to_split_hex(4011))
msb, lsb = val_to_split_hex(4011)

p = bytes([(0x13)|(1 << 7), int(msb, 16), int(lsb, 16), 0x00])
print(p)
'''
