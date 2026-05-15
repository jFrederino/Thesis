
# DONE AS OF 

## 18 MAR 2026

#### Clipping extraneous points beyond LUT bounds off of curve_fit extrapolated DAC lists
Curve_fit algorithm is now safe and adheres to LUT boundaries. 

#### fixed LUT discontinuities (jumping)
Split Hex function in helper.py was using string splitting incorrectly, for some values like 4011, the hex is 0xfab (not 0x0fab), which is not four characters long in pythons representation. This was splitting 4011 into 0xfa, 0xb (interpreted by laser as 64011) instead of the correct 0xf, 0xab (4011). this has been replaced with the divmod method that uses modular division to split the hex values correctly. 

## 19 MAR 2026

#### Integrate GUI with real time processing 
The GUI now sends packets to the laser and is pausable, but does not include some important functionality. 

## 21 MAR 2026 

#### GUI Scan Parameter Controls
The GUI config window allows for updating of laser control parameters including interpolation type and table indices. more are being added as nessesary. 

#### GUI DAC Table Window
New DAC LUT Window shows loaded LUT, but still needs functionality, like highlighting and auto scrolling. 

#### Log and Debug Toggles Added
Logger and Debug Statements now have toggles. 

## 22 MAR 2026

#### Enable and Disable Check Laser Via Packets
The enable and disable methods in DBR.py now read the GAIN value to see if the laser is on.

## 23 MAR 2026

#### Start and End Wavelength Parameter controls for table generation.
Table generator finds closest index to chosen wavelength in default LUT (allows for selecting wavelength range instead of arbitrary index range)

#### Serial Port Connection Config Functionality
Selection of serial port modifies DBR port default and allow for reconnection to laser. 

#### Voltage Data Dynamic Plot
Now Showing collected voltage data in real time. 

## 28 MAR 2026

#### GUI now passes Serial Port object to Spectrometer class __init__. 
GUI is now in charge of connecting to the laser via pyserial

#### Multiple Series (Scan Data Sets) On Voltage Plot
Now able to add new scan data on top of older scans and compare them, or delete them, etc. in Voltage Plot

#### Refactored and Reorganized Directories for GUI and Command Line interfaces. 
Removed a lot of unnesessary code form myGUI Spectrometer.py (Previously DBR.py) and generate_table.py. Also renamed other files, and added directories. Removed some old code that is accessible in repo verison control history. 

## 29 MAR 2026 

#### Tab layout now works
seperate tabs function correctly.

#### Second Voltage Channel plot.
Channel 1 works as previously built voltmeter inst. still need to rework depending on voltmeter connected to system, as well as allow for multiple voltmeter comms.

# TO-DO LIST 
-------

## CATMULL-ROM SPLINE INTERPOLATION!!

## Repeated Scan Methods
Should be able to batch scans with same parameters for analysis. (example given was 50 scans) :O

## Docstrings and cleanup
Documentation of methods within code. Probably also condensing some and refactoring others. 

## Command Line argument control
The program should accept parameter controls via in-line command line arguements: one command to run the program in its entirety.

## Characterization of Laser spectrum
Using the 'glorified block of glass' (destructive interferance precision wavemeter thing).

## The GUI Side Quest

#### GUI DAC Table Highlight
The GUI should display the current values (and the previous values) being packaged and sent to the Laser. This should help check consistency between the DBR program sanatization and the DAC table in real time.

#### Voltage Plot drag lines for bounds to export via matplotlib.
Should be able to specify bounds and other features of exported plots from GUI. Drag lines could be neat. 

#### GUI configuration saves (plus saving DAC tables)
Project files should be loadable and saveable that hold all the configuration data for a given laser scan/protocol. that way, the data collected can be saved with a config file that allows for repeatability and debugging

## Packaging of DBR python utility
The final product should be managed as a python package and include both Command Line functionality and GUI functionality. This may also include building the program as an exe and hosting that on the github. 

## Updated Documentation & MANUAL
The github should include example snippets and documentation of the process and code timing as will be documented in the Thesis writeup (this should help with writing in general)




