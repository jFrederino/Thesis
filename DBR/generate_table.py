# JAMES USHER 2026
import csv
import numpy as np
import matplotlib.pyplot as plt
import scienceplots
import glob 
import os 
from scipy.optimize import curve_fit

plt.style.use(["science", "grid"])

'''
max_fm = 57954
min_fm = 668

max_bm = 43418
min_bm = 982

max_ph = 17448
min_ph = 2496

max_soa = 45527
min_soa = 14319
'''

def linear_function(x, m, b): return m*x + b

CWD = os.path.dirname(os.path.realpath(__file__))
DAC_TABLE_PATH_LIST = glob.glob(CWD+'/UU341_LUT_0v0.csv', recursive=True)
if not DAC_TABLE_PATH_LIST: raise Exception("UU341_LUT_0v0.csv not found in CWD") 
else: DAC_TABLE_PATH = DAC_TABLE_PATH_LIST[0]

def get_DAC_arrays_from_table(csv_table_path:str, bounds:bool=False, start_index:int = 0, end_index:int = 9999):
 
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
    if bounds: 
        idx = IDX[start_index:end_index]
        fm = FM[start_index:end_index]
        bm = BM[start_index:end_index]
        ph = PH[start_index:end_index]
        soa = SOA[start_index:end_index]
        wl = WL[start_index:end_index]
        return [idx,fm,bm,ph,soa,wl]
    else:
        return [IDX,FM,BM,PH,SOA,WL]

def generate_DAC_table(interpolate_type: str = "linear", interpolate_val:int = 0, start_index:int = 0, end_index:int = 9999, plot:bool = True):
    DAC_arrays = get_DAC_arrays_from_table(DAC_TABLE_PATH, True, start_index, end_index) #this is what narrows down what we are interpolating between

    #if not interpolate_val: return DAC_TABLE_PATH
    idx,fm,bm,ph,soa,wl = DAC_arrays[0],DAC_arrays[1],DAC_arrays[2],DAC_arrays[3],DAC_arrays[4],DAC_arrays[5]
    
    if interpolate_val and interpolate_type == "linear": 

        fig, ax = plt.subplots()
        plt.gcf().set_size_inches(8,6)

        print(f"interpolating with {interpolate_val} intermediate values generated")
        res = interpolate_val+1
        delta = 0.004499549999999999 / res
        new_idx,new_fm,new_bm,new_ph,new_soa,new_wl  = [],[],[],[],[],[]
    
        for i in range(0, len(wl)-1):
            #i is index of current left bound DAC value
            next_wl = wl[i+1]

            #if we need to skip large discontinuities: 
            '''
            fm_gap = abs(int(fm[i] - fm[i+1]))
            bm_gap = abs(int(bm[i] - bm[i+1]))
            ph_gap = abs(int(ph[i] - ph[i+1]))
            soa_gap = abs(int(soa[i] - soa[i+1]))
            '''
            interp_wavelengths = [] #for each gap we interpolate
            interp_wavelengths.append(wl[i])
            for k in range(1, res):
                interp_wavelengths.append(wl[i] + (delta * k)) #starts at k = 0 so it keeps the original points

            #for each DAC type:
            #if fm_gap < 1000:
            interp_fm = np.interp(interp_wavelengths, [wl[i], next_wl], [fm[i], fm[i+1]])
            interp_bm = np.interp(interp_wavelengths, [wl[i], next_wl], [bm[i], bm[i+1]])
            interp_ph = np.interp(interp_wavelengths, [wl[i], next_wl], [ph[i], ph[i+1]])
            interp_soa = np.interp(interp_wavelengths, [wl[i], next_wl], [soa[i], soa[i+1]])

            new_wl.extend(interp_wavelengths)
            new_fm.extend(interp_fm)
            new_bm.extend(interp_bm)
            new_ph.extend(interp_ph)
            new_soa.extend(interp_soa)

        # Rounding DAC values to nearest integer
        r_fm,r_bm,r_ph,r_soa = [],[],[],[]
        for val in new_fm: r_fm.append(round(val))
        for val in new_bm: r_bm.append(round(val))
        for val in new_ph: r_ph.append(round(val))
        for val in new_soa: r_soa.append(round(val))

        new_table_path = CWD+f'/DAC_Tables/INTERP_({interpolate_val}, {start_index}, {end_index}).csv'
        with open(new_table_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|')
            writer.writerow(['IDX','FM DAC','BM DAC','PH DAC','SOA DAC','WL Target'])
            for row in range(0, len(new_wl)):
                writer.writerow([row, r_fm[row], r_bm[row], r_ph[row], r_soa[row], new_wl[row]])
    
    if interpolate_type == "curve_fit":
        #https://stackoverflow.com/a/49087165
        #https://stackoverflow.com/a/64929683
        #https://stackoverflow.com/a/48507056
        #https://www.eg.bucknell.edu/~phys310/jupyter/linear_fit_example_2.html

        '''
        -- from the manual -- 
        DAC GUI

        The DAC GUI can be accessed from the FP42xx GUI Utility
        menu. This GUI allows the user to control the individual
        laser section drive strength as well as adjust the laser
        operating temperature.
        Temperature Control

        The Temperature control portion of the GUI allows the
        user to set and read laser temperature as well as read TEC
        Voltage in 16-bit DAC counts with a midscale 32767. The
        Set Temp button allows the user to set a temperature in
        centi-Celsius or deg C*100. (i.e. 4000 deg cC = 40 deg C).
        Read Temp button reads the current operating
        temperature back from the module in centi-Celsius.
    
        "The Laser Drive Portion of the GUI allows the user to
        drive each laser section manually. Full scale on each
        current source is 65535." 

        I take this to mean that the DAC current/voltage control values are allowed to be anywhere in that range:
        0 to 65535. That would mean that extending the edges like this is perfectly fine. 
        this is the maxmimum unsigned 16 bit int, which makes sense

        '''
        res = interpolate_val+1
        delta = 0.004499549999999999 / res
        new_idx,new_fm,new_bm,new_ph,new_soa,new_wl  = [],[],[],[],[],[]
        controllers = [fm,bm,ph,soa]
        controller_names = ["fm", "bm", "ph", "soa"]

        controller_thresholds = [30,30,200,200]

        fig, ax = plt.subplots()
        plt.gcf().set_size_inches(8,6)
        
        print(f"wl {len(wl)}")
        print(f"ph {len(ph)}")

        if interpolate_val > 0:
            for j in range(len(controllers)): 
                controller = controllers[j]
                controller_name = controller_names[j]
                print(controller_name)
                controller_threshold = controller_thresholds[j]

                discontinuities_controller_indices = np.where(abs(np.diff(np.array(controller))) > controller_threshold)[0]

                if discontinuities_controller_indices.size == 0:
                    print("NO DISCONTINUTIES")

                print(f"{controller_name}: {discontinuities_controller_indices.size}")
                #print(discontinuities_controller_indices)

                r_values = []
                w_values = []

                for i in range(discontinuities_controller_indices.size): 

                    if i != 0: 
                        x = wl[discontinuities_controller_indices[i-1]+1:discontinuities_controller_indices[i]+1]
                        y = controller[discontinuities_controller_indices[i-1]+1:discontinuities_controller_indices[i]+1]

                    if i == discontinuities_controller_indices.size - 1:
                        x = wl[discontinuities_controller_indices[i-1]+1:]
                        y = controller[discontinuities_controller_indices[i-1]+1:]

                    if i == 0:
                        x = wl[:discontinuities_controller_indices[0]+1]
                        y = controller[:discontinuities_controller_indices[0]+1]
         
                               
                    xfine = np.linspace(min(x), max(x)+(delta*res), len(x)*res + 1)
                    xfine = np.delete(xfine, -1) #get rid of overlaps
                    for wavelength in xfine: 
                        w_values.append(wavelength)

                    if len(y) != 1:
                        popt, pcov = curve_fit(linear_function, x, y)
                        extrapolated_values = linear_function(xfine, *popt)
                        for value in extrapolated_values: 
                            r_values.append(round(value))

                    else: #you cant fit a curve to a single point lol (this bug caused such a headache)
                        extrapolated_values = [y[0]]
                        next_value = y[0]
                        for i in range(res-1):
                            extrapolated_values.append(round(next_value))

                        for value in extrapolated_values: 
                            r_values.append(round(value))
                    
                if interpolate_val:
                    new_wl = w_values

                if plot:
                    plt.plot(w_values, r_values, 'o--', ms=0.85, label=f"extrapolated {controller_name}")

                match controller_name:
                    case "fm": r_fm = r_values
                    case "bm": r_bm = r_values
                    case "ph": r_ph = r_values
                    case "soa": r_soa = r_values

            new_table_path = CWD+f'/DAC_Tables/EXTRAP_({interpolate_val}, {start_index}, {end_index}).csv'
            with open(new_table_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='|')
                writer.writerow(['IDX','FM DAC','BM DAC','PH DAC','SOA DAC','WL Target'])
                for row in range(0, len(new_wl)):
                    writer.writerow([row, r_fm[row], r_bm[row], r_ph[row], r_soa[row], new_wl[row]])
            

    if plot:
        
        if not interpolate_val:
            plt.title(f'Default DAC Parameters ({start_index}, {end_index})')
            ax.plot(wl, fm, 'o--', ms=0.85, linewidth=0.5, label=r"FM")
            ax.plot(wl, bm, 'o--', ms=0.85, linewidth=0.5, label=r"BM")
            ax.plot(wl, ph, 'o--', ms=0.85, linewidth=0.5, label=r"PH")
            ax.plot(wl, soa, 'o--', ms=0.85, linewidth=0.5, label=r"SOA")

        if interpolate_val > 0 and interpolate_type == "linear": #for clarity's sake
            plt.title(f'DAC Parameters ({start_index}, {end_index}) Interpolated with {interpolate_val} Intermediate Integer Values')

            ax.plot(new_wl, r_fm, 'o--', ms=0.85, linewidth=0.5, label=r"FM")
            ax.plot(new_wl, r_bm, 'o--', ms=0.85, linewidth=0.5, label=r"BM")
            ax.plot(new_wl, r_ph, 'o--', ms=0.85, linewidth=0.5, label=r"PH")
            ax.plot(new_wl, r_soa, 'o--', ms=0.85, linewidth=0.5, label=r"SOA")

        if interpolate_val > 0 and interpolate_type == "curve_fit":
            plt.title(f'DAC Parameters ({start_index}, {end_index}) Extrapolated with {interpolate_val} Intermediate Integer Values')

        plt.xlabel(r'$\text{Wavelength} ( \lambda )$')
        plt.ylabel(r"DAC Value")
        
        #ax.legend(fontsize=14)
        #plt.savefig(f'DBR/Plots/INTERP_({interpolate_val},{start_index},{end_index}).png', dpi=300)
        if interpolate_type == "linear":
            plt.savefig(CWD+f'/Plots/INTERP_({interpolate_val}, {start_index}, {end_index}).pdf', format='pdf')

        if interpolate_type == "curve_fit":
            plt.savefig(CWD+f'/Plots/EXTRAP_({interpolate_val}, {start_index}, {end_index}).pdf', format='pdf')

        plt.show()
    if not interpolate_val: return DAC_TABLE_PATH

    print('Generated Table:' + new_table_path)
    return new_table_path
    
#generate_DAC_table(interpolate_val=3, start_index=400, end_index=450)

#generate_DAC_table(interpolate_type = "linear", interpolate_val = 0, start_index=5000, end_index=6000, plot=True)

