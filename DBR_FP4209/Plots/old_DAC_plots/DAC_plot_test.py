#   JAMES USHER 
#   1 FEB 2026


#TODO 

# Plot over narrow range (maybe 50 wavelengths) X
# interpolate via scipy X 
#   generate new tables / organize tables for DAC X 
#   -> serial transformation
#   
#   
# 


import matplotlib.pyplot as plt
import csv
import scipy 
import numpy as np

IDX = []
FM = []
BM = []
PH = []
SOA = []
WL = []

with open('DAC_plots/UU341_LUT_0v0.csv', newline='') as f:
    reader = csv.reader(f, delimiter=',', quotechar='|')
    next(reader)
    for row in reader:
        IDX.append(row[0])
        FM.append(row[1])
        BM.append(row[2])
        PH.append(row[3])
        SOA.append(row[4])
        WL.append(row[5])

#very important! otherwise plt will just plot them in order of appearance as strings, this converts them to numbers that actually mean something
WL = np.array(WL,dtype=np.float32)
FM = np.array(FM,dtype=np.float32)
BM = np.array(BM,dtype=np.float32)
PH = np.array(PH,dtype=np.float32)
SOA = np.array(SOA,dtype=np.float32)


def plot_full_DAC(): # naive plot of full range of DAC values

    #with WL as the x axis, all other parameters as dependent variables, obviously.

    fig, ax = plt.subplots()

    ax.plot(WL, FM, 'o--', linewidth=0.5, label=r"FM")
    ax.plot(WL, BM, 'o--', linewidth=0.5, label=r"BM")
    ax.plot(WL, PH, 'o--', linewidth=0.5, label=r"PH")
    ax.plot(WL, SOA, 'o--', linewidth=0.5, label=r"SOA")

    #ax.set(xlim=(1627.5, 1672.4955), xlabel="WL")
    ax.legend(fontsize=14)
    '''
    # https://stackoverflow.com/a/44864135 wide plot (warning! _very_ wide)

    N = len(WL)
    plt.gca().margins(x=0)
    plt.gcf().canvas.draw()
    tl = plt.gca().get_xticklabels()
    maxsize = max([t.get_window_extent().width for t in tl])
    m = 0.2 # inch margin
    s = maxsize/plt.gcf().dpi*N+2*m
    margin = m/plt.gcf().get_size_inches()[0]

    plt.gcf().subplots_adjust(left=margin, right=1.-margin)
    plt.gcf().set_size_inches(s, plt.gcf().get_size_inches()[1])

    '''
    plt.gcf().set_size_inches(60,40) #this thing is like 8MB in size lol


    plt.savefig(__file__+'_'+"DAC_plot_FIXED.png", dpi=300)
    #plt.show()

'''
wl_dif = 1672.4955-1627.5 # range of wl in DAC table
delta = wl_dif / 10000
new = 1627.5 + delta # checking second value on DAC table (it matches)
# delta = 0.004499549999999999
print(new)
'''
# confirms even spacing of wavelength values in ref DAC table
# also helps determine what new size of delta we need for higher resolution (proportionally)
#   -> new resolution is 10 times finer: new delta is ten times smaller? 
#       -> assumes ten integer values between refs for at least one of the DAC controllers? (naive)

#question: is there always an available gap to fill between reference wavelengths? i.e. is it possible that all four parameters have a gap of zero between two wavelengths?
#question: what is the smallest total gap (sum of all gaps) between two wavelengths? what is the biggest? what is the average?


def plot_DAC_range(start_wl:int = 0, end_wl:int = 9999, interp:bool = False):
    '''
    start_wl: int                   wavelength (index) to start at on ref DAC table (starts at zero normally)
    end_wl: int                     (index) ends at 9999 in full data set the number of reference DAC wavelengths (the range of the plot), that will be interpolated between        
    '''
    #over indexing end_wl in the list slicing doesnt matter. but it does matter for loops

    wl = WL[start_wl:end_wl]
    fm = FM[start_wl:end_wl]
    bm = BM[start_wl:end_wl]
    ph = PH[start_wl:end_wl]
    soa = SOA[start_wl:end_wl]
    
    fig, ax = plt.subplots()
    if interp == False:
        ax.plot(wl, fm,'o--', linewidth=0.5, label=r"FM" )
        ax.plot(wl, bm, 'o--', linewidth=0.5, label=r"BM")
        ax.plot(wl, ph, 'o--', linewidth=0.5, label=r"PH")
        ax.plot(wl, soa, 'o--', linewidth=0.5, label=r"SOA")

    plt.gcf().set_size_inches(30,15)

    gaps_fm, gaps_bm, gaps_ph, gaps_soa = [],[],[],[]
    gaps_wl = []
    total_gaps = []

    
    for i in range(0, len(wl)-1):
        fm_gap = abs(int(fm[i] - fm[i+1]))
        bm_gap = abs(int(bm[i] - bm[i+1]))
        ph_gap = abs(int(ph[i] - ph[i+1]))
        soa_gap = abs(int(soa[i] - soa[i+1]))
        wl_gap_center = wl[i]+0.004499549999999999 #add delta value

        gaps_fm.append(fm_gap)
        gaps_bm.append(bm_gap)
        gaps_ph.append(ph_gap)
        gaps_soa.append(soa_gap)
        gaps_wl.append(wl_gap_center)
        total_gaps.append(fm_gap+bm_gap+ph_gap+soa_gap)

    def stats_list(xs:list):
        avg = sum(xs) / len(xs)
        minimum = min(xs)
        maximum = max(xs)
        mode = max(set(xs), key=xs.count)
        return avg, minimum, maximum, mode
  
    #print(f'{fm}:{stats_list(gaps_fm)}') 
    #print(f'{bm}:{stats_list(gaps_bm)}')
    #print(f'{ph}:{stats_list(gaps_ph)}')
    #print(f'{soa}:{stats_list(gaps_soa)}')

    #print(stats_list(total_gaps))

    #ax.plot(gaps_wl, total_gaps, 'o--', linewidth=0.5, label=r"gap size")

    #ax.legend(fontsize=14)
    #plt.savefig(__file__+'_'+"DAC_plot_range=("+str(start_wl)+', '+str(end_wl)+").png", dpi=300)
    #plt.show()
    #   for all 10,000 reference wavelengths:
    #    AVERAGE GAP SIZE   |   MIN SIZE   |   MAX SIZE

    #FM  47.213621362136216 |   0          |    48612
    #BM  57.79357935793579  |   0          |    40042
    #PH  199.61456145614562 |   46         |    9730
    #SOA 67.1935193519352   |   0          |    24104

    #THE MOST IMPORTANT PROPERTY OF THIS DATA SET:

    #sum 371.8152815281528  |   48         |    115568
    

# interpolation via integer succession? 
    #the valuex of the list 'x' in np.interp() is found by dividing up the space by the desired resolution. we can assume that we can fit maybe 40 to 80 distinct wavelengths in the average gap.
    #so we divide old_wl_delta = 0.004499549999999999 / (number of points desired in 'x')  to get the new delta
    #then we add the delta to the wl[i] to get the next x value, until we have all 80, then we have x for that gap. 
    #np.interp defaults to the closest boundary value.
    
    if interp == True:
        
        res = 80
        delta = 0.004499549999999999 / res
        new_fm = []
        new_bm = []
        new_ph = []
        new_soa = []

        new_wl = []
        new_fm = []
        
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
            for k in range(res):
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
        
        ax.plot(new_wl, new_fm, 'o--', linewidth=0.5, label=r"interp fm")
        ax.plot(new_wl, new_bm, 'o--', linewidth=0.5, label=r"interp fm")
        ax.plot(new_wl, new_ph, 'o--', linewidth=0.5, label=r"interp fm")
        ax.plot(new_wl, new_soa, 'o--', linewidth=0.5, label=r"interp fm")

        ax.legend(fontsize=14)
        plt.savefig(__file__+'_'+"INTERP_("+str(start_wl)+', '+str(end_wl)+").png", dpi=300)



















'''
basically, the naive and almost certainly incorrect assumption is that each DAC parameter has an equal effect on the produced wavelength;
that is: an increase of 1 of any of the controllers will have the same effect on the produced wavelength. based on the parameter spread above i have to assume the truth is that
some of the controllers (like the PH and SOA controllers have a weaker effect) and thus need to be increased more, proportionately, between changes in reference wavelengths;
I havent even looked into corralated changes in variables yet (its possible that increasing more than one at a time is nessesary or vice versa)  
    i simply do not know what any non-reference value given to the DAC will actually do. 


so the most simple way to produce more DAC values is to incrememnt whatever parameter is available by 1 (the smallest integer value possible), 
and assume this will produce some shift in wavelength. then, prioritizing unused parameters (keeping track of how many times each is incremented i guess?), 
repeat until the next reference wavelength is reached, then start over at the next gap. 
this will unfortunately produce so many data points that it might be difficult to visualize. but the resolution will be great, probably. ;u;
    I would like to have control over the interpolation density (maybe even per variable)

'''
 





















def main():
    #plot_full_DAC()
    plot_DAC_range(4225, 4275, interp=True)
    pass


if __name__ == "__main__": main()
