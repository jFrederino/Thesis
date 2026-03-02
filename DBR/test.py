
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
