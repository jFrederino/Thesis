# JAMES USHER 2026
import csv
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import scienceplots
import glob 
import os 
from scipy.optimize import curve_fit
plt.style.use(["science", "grid"])

def linear_function(x, m, b): return m*x + b

CWD = os.path.dirname(os.path.realpath(__file__))
DAC_TABLE_PATH_LIST = glob.glob(CWD+'/UU341_LUT_0v0.csv', recursive=True)
if not DAC_TABLE_PATH_LIST: raise Exception("UU341_LUT_0v0.csv not found in CWD") 
else: DAC_TABLE_PATH = DAC_TABLE_PATH_LIST[0]

class DAC_Table:
    def __init__(self, start_index: int = 0, end_index: int = 9999, 
                 interpolate_value: int = 3, interpolate_type: str = "linear"): 

        self.start_index = start_index
        self.end_index = end_index
        self.interpolate_value = interpolate_value
        self.interpolate_type = interpolate_type

    def update_DAC_values(self, controllers: list[list]):
        self.idx = controllers[0]
        self.fm = controllers[1]
        self.bm = controllers[2]
        self.ph = controllers[3]
        self.soa = controllers[4]
        self.wl = controllers[5]

    def get_DAC_arrays(self, csv_table_path, apply_bounds: bool = False):

        IDX,FM,BM,PH,SOA,WL = [],[],[],[],[],[] 

        start_index = self.start_index
        end_index = self.end_index
    
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
        if apply_bounds:
            idx = IDX[start_index:end_index]
            fm = FM[start_index:end_index]
            bm = BM[start_index:end_index]
            ph = PH[start_index:end_index]
            soa = SOA[start_index:end_index]
            wl = WL[start_index:end_index]
            controllers = [idx,fm,bm,ph,soa,wl]
        else: 
            controllers = [IDX,FM,BM,PH,SOA,WL]
    
        return controllers

    def _write_DAC_table(self) -> str:
        '''
        Takes in DAC values and Generates csv file.

        Returns
        -------

        new_table_path (str) : The file path to the newly generated DAC table csv file. (should be in DBR/DAC_Tables).
        '''
        if self.interpolate_type == "linear":
            new_table_path = CWD+f'/DAC_Tables/INTERP_({self.interpolate_value}, {self.start_index}, {self.end_index}).csv'

        if self.interpolate_type == "curve_fit":
            new_table_path = CWD+f'/DAC_Tables/EXTRAP_({self.interpolate_value}, {self.start_index}, {self.end_index}).csv'

        with open(new_table_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|')
            writer.writerow(['IDX','FM DAC','BM DAC','PH DAC','SOA DAC','WL Target'])
            for row in range(0, len(self.new_wl)):
                writer.writerow([row, self.r_fm[row], self.r_bm[row], self.r_ph[row], self.r_soa[row], self.new_wl[row]])

        return new_table_path
    
    def plot(self, plot_both: bool = False):
        fig, ax = plt.subplots()
        plt.gcf().set_size_inches(8,6)

        ax.plot(self.new_wl, self.r_fm, 'o--', ms=0.85, linewidth=0.5, label=r"FM")
        ax.plot(self.new_wl, self.r_bm, 'o--', ms=0.85, linewidth=0.5, label=r"BM")
        ax.plot(self.new_wl, self.r_ph, 'o--', ms=0.85, linewidth=0.5, label=r"PH")
        ax.plot(self.new_wl, self.r_soa, 'o--', ms=0.85, linewidth=0.5, label=r"SOA")

        if not self.interpolate_value:
            plt.title(f'Default DAC Parameters ({self.start_index}, {self.end_index})')

        if self.interpolate_value > 0 and self.interpolate_type == "linear": #for clarity's sake
            plt.title(f'DAC Parameters ({self.start_index}, {self.end_index}) Interpolated with {self.interpolate_value} Intermediate Integer Values')

        if self.interpolate_value > 0 and self.interpolate_type == "curve_fit":
            plt.title(f'DAC Parameters ({self.start_index}, {self.end_index}) Extrapolated with {self.interpolate_value} Intermediate Integer Values')

        if plot_both or not self.interpolate_value:

            ax.plot(self.wl, self.fm, 'o--', ms=0.85, linewidth=0.5, label=r"FM")
            ax.plot(self.wl, self.bm, 'o--', ms=0.85, linewidth=0.5, label=r"BM")
            ax.plot(self.wl, self.ph, 'o--', ms=0.85, linewidth=0.5, label=r"PH")
            ax.plot(self.wl, self.soa, 'o--', ms=0.85, linewidth=0.5, label=r"SOA")

        plt.xlabel(r'$\text{Wavelength} ( \lambda )$')
        plt.ylabel(r"DAC Value")
        plt.legend()

        if self.interpolate_type == "linear":
            plt.savefig(CWD+f'/Plots/INTERP_({self.interpolate_value}, {self.start_index}, {self.end_index}).pdf', format='pdf')

        if self.interpolate_type == "curve_fit":
            plt.savefig(CWD+f'/Plots/EXTRAP_({self.interpolate_value}, {self.start_index}, {self.end_index}).pdf', format='pdf')

        plt.show()

    def _linear_interpolate(self) -> str:
        '''
        Takes controller values from DAC table and linearly interpolates new DAC values. Saves new values to self.r_[controller_name]. Also generates new DAC table with new values.
        
        Returns
        -------

        new_table_path (str) : The file path to the newly generated DAC table csv file. (should be in DBR/DAC_Tables).
        '''
        fm = self.fm
        bm = self.bm
        ph = self.ph
        soa = self.soa
        wl = self.wl

        print(f"interpolating with {self.interpolate_value} intermediate values generated")
        res = self.interpolate_value+1
        delta = 0.004499549999999999 / res
        new_fm,new_bm,new_ph,new_soa,new_wl  = [],[],[],[],[]
    
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

        return self._write_DAC_table()

    def _curve_fit(self) -> str:
        '''
        Extrapolates new DAC values by fitting curves (lines) to original DAC table. Creates new DAC table and saves new points to self.r_[controller_name].

        Returns
        -------

        new_table_path (str) : The file path to the newly generated DAC table csv file. (should be in DBR/DAC_Tables).
        '''

        #https://stackoverflow.com/a/49087165
        #https://stackoverflow.com/a/64929683
        #https://stackoverflow.com/a/48507056
        #https://www.eg.bucknell.edu/~phys310/jupyter/linear_fit_example_2.html

        '''
        -- from the manual -- 
        DAC GUI

        "The Laser Drive Portion of the GUI allows the user to
        drive each laser section manually. Full scale on each
        current source is 65535." 

        I take this to mean that the DAC current/voltage control values are allowed to be anywhere in that range:
        0 to 65535. That would mean that extending the edges like this is perfectly fine. 
        this is the maxmimum unsigned 16 bit int, which makes sense

        '''
        res = self.interpolate_value+1
        delta = 0.004499549999999999 / res
        new_fm,new_bm,new_ph,new_soa,new_wl  = [],[],[],[],[]
        controller_names = ["FM", "BM", "PH", "SOA"]

        wl = self.wl
        controllers = [self.fm, self.bm, self.ph, self.soa]
        controller_thresholds = [30,30,150,60] #tuned by trial and error, could use algorithm instead?

        for j in range(len(controllers)-1): 
            controller = controllers[j]
            controller_name = controller_names[j]
            controller_threshold = controller_thresholds[j]

            discontinuities_controller_indices = np.where(abs(np.diff(np.array(controller))) > controller_threshold)[0]

            if discontinuities_controller_indices.size == 0:
                print("NO DISCONTINUTIES")

            #print(f"{controller_name}: {discontinuities_controller_indices.size}")
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
                
            if self.interpolate_value: self.new_wl = w_values

            match controller_name:
                case "FM": self.r_fm = r_values
                case "BM": self.r_bm = r_values
                case "PH": self.r_ph = r_values
                case "SOA": self.r_soa = r_values

        return self._write_DAC_table()

    def generate_DAC_table(self, interpolate_type: str = "linear", start_index:int = 0, end_index:int = 9999, plot_choice:bool = True, plot_both:bool = False) -> str:
        '''
        Generates new DAC table and outputs the path to the new table.

        Returns
        -------

        new_table_path (str) : The file path to the newly generated DAC table csv file. (should be in DBR/DAC_Tables).
        '''
        #csv_table_path = DAC_TABLE_PATH
        DAC_arrays = self.get_DAC_arrays(DAC_TABLE_PATH, apply_bounds=True) #this is what narrows down what we are interpolating between
        self.update_DAC_values(DAC_arrays) #writes values to self variables 

        #if not interpolate_val: return DAC_TABLE_PATH

        if interpolate_type == "linear": 
            new_table_path = self._linear_interpolate()

        if interpolate_type == "curve_fit":
            new_table_path = self._curve_fit()
        
        if plot_choice: self.plot(plot_both=plot_both)

        print('Generated Table:' + new_table_path)
        return new_table_path
        
    def visualize_parameters_5D(self):
        DAC_arrays = self.get_DAC_arrays() #this is what narrows down what we are interpolating between

        #if not interpolate_val: return DAC_TABLE_PATH
        fm,bm,ph,soa,wl = DAC_arrays[1],DAC_arrays[2],DAC_arrays[3],DAC_arrays[4],DAC_arrays[5]

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        names = ["FM", "BM", "PH", "SOA"]

        exclude = "SOA"

        if exclude == "SOA":
            sizes = (np.array(soa) * np.array(soa)) / 15000000
            sc = ax.scatter(fm, bm, ph, c = wl, s = sizes, cmap='viridis', marker='o')
            ax.set_xlabel('FM')
            ax.set_ylabel('BM')
            ax.set_zlabel('PH')
        
            fig.colorbar(sc, ax = ax, pad = 0.1, label='Wavelength')
            plt.title(f'5D LUT Visualization for FM, BM, PH, with size dependent on SOA')
            plt.savefig(CWD+f'/Plots/VIS_(FM,BM,PH,SOA).pdf', format='pdf')

            plt.show()

        if exclude == "PH":
            sizes = (np.array(ph) * np.array(ph)) / 15000000
            sc = ax.scatter(fm, bm, soa, c = wl, s=sizes, cmap='viridis', marker='o')
            ax.set_xlabel('FM')
            ax.set_ylabel('BM')
            ax.set_zlabel('SOA')
            
            fig.colorbar(sc, ax = ax, pad = 0.1, label='Wavelength')
            plt.title(f'5D LUT Visualization for FM, BM, SOA, with size dependent on PH')
            plt.savefig(CWD+f'/Plots/VIS_(FM,BM,SOA,PH).pdf', format='pdf')

            plt.show()
        pass
    #generate_DAC_table(interpolate_val=3, start_index=400, end_index=450)

    #generate_DAC_table(interpolate_type = "linear", interpolate_val = 0, start_index=5000, end_index=6000, plot=True)

    #visualize_parameters()