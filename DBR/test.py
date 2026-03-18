
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def hex_to_DAC_value(msb, lsb):

    print(msb)
    print(lsb)

    msb = int(hex(msb))
    lsb = int(hex(lsb))

    val = int((msb << 8) | lsb) #reconstructs hex value that i had to split anyway for some reason.
    return val


def val_to_split_hex(val): 
        '''
        Parameters
        ----------
        val : int 

        Returns
        -------
        [msb, lsb] : list of base-16 integers
        '''
        msb = int(hex(val)[2:4], base=16)
        lsb = int(hex(val)[4:6], base=16)
        #bytes() object doesnt take strings
        
        return [msb, lsb]






def check_packet(packet: list):

    '''
    packet_list = [fm_packet, bm_packet, ph_packet, soa_packet, target_wl]

    '''
    for p in packet:
        msb = p[1]
        lsb = p[2]
        print(msb)
        print(lsb)
        res = hex_to_DAC_value(msb, lsb)
        print(res)
    return 0


'''
#11425,4698,17448,24222,1627.5
val = 11425

msb = int(hex(val)[2:4], base=16)
lsb = int(hex(val)[4:6], base=16)

fm_packet = bytes([(0x13)|(1 << 7), msb, lsb, 0x00 ])
print(fm_packet)
#l = fm_packet.decode()
#
#hex_to_DAC_value(l[1],l[2])




x = np.array([0, 1, 2, 3, 4, 5])
y = np.array([30, 50, 80, 160, 300, 580])

def exponential_fit(x, a, b, c):
    return a*np.exp(-b*x) + c


fitting_parameters, covariance = curve_fit(exponential_fit, x, y)
a, b, c = fitting_parameters

x_min = -4  
x_max = 8                                #min/max values for x axis
x_fit = np.linspace(x_min, x_max, 100)   #range of x values used for the fit function
plt.plot(x, y, 'o', label='data')
plt.plot(x_fit, exponential_fit(x_fit, *fitting_parameters), '-', label='Fit')

plt.axis([x_min, x_max, 0, 2000])
plt.legend()
plt.show()
'''

'''
new_x = np.linspace(min(x)-1, max(x)+1, num=np.size(x))
coefs = np.polyfit(x,y,4)
new_line = np.polyval(coefs, new_x)

plt.scatter(x,y)
plt.plot(new_x, new_line, 'o--', ms=0.85, linewidth=0.5, label=r"FM")
plt.xlim(min(x)-1,max(x)+1)
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
'''
import ctypes

dx = 40959
dy = ctypes.c_uint16(dx << 8).value
print(dy)
#these are the same!
register = 39
turn_on = (40959 << 8) & 0xFFFF

#test = int(turn_on, base=16)
#print(test)
register = 39
regnum = register | 0x80



data = (3840 << 8) & 0xFFFF #this is just fucking zero brooooo
print(data)

msb = int(hex(data)[2:4], base=16)
lsb = 0 #int(hex(data)[4:6], base=16)
split = [msb, lsb]
print(split)
print(regnum)
print(turn_on)

turn_on_packet = bytes([regnum, split[0], split[1], 0])
a = bytes([144, 255, 0, 0])
b = bytes([167, 0, 0, 0])

print(turn_on_packet)
print(a)
print(b)


