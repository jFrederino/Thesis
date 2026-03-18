
# DONE AS OF 18 MAR 2026

## Clipping extraneous points beyond LUT bounds off of curve_fit extrapolated DAC lists
Curve_fit algorithm is now safe and adheres to LUT boundaries. 

## fixed LUT discontinuities (jumping)
Split Hex function in helper.py was using string splitting incorrectly, for some values like 4011, the hex is 0xfab (not 0x0fab), which is not four characters long in pythons representation. This was splitting 4011 into 0xfa, 0xb (interpreted by laser as 64011) instead of the correct 0xf, 0xab (4011). this has been replaced with the divmod method that uses modular division to split the hex values correctly. 


# TO-DO LIST 

## Command Line argument control
The program should accept parameter controls via in-line command line arguements: one command to run the program in its entirety.

## Characterization of Laser spectrum
Using the 'glorified block of glass' (destructive interferance precision wavemeter thing).

## GUI Side Quest

#### Integrate GUI with real time processing 
Currently the GUI does not actually enagage with the laser running through the scan. It should be able to record data and visualize behavior in real time, as well as engage and pause operations. 

#### GUI DAC Table 
The GUI should use DearPyGUI table functionality to display the DAC table being loaded, as well as the current values (and the previous values) being packaged and sent to the Laser. This should help check consistency between the DBR program sanatization and the DAC table in real time.

#### GUI Scan Parameter Controls
Currently the GUI does not allow for creation of a new DBR_Spectrometer Object with different scan parameters. The GUI should be able to set all of these values and initiate a scan or repeated scan with detailed controls.

## Packaging of DBR python utility
The final product should be managed as a python package and include both Command Line functionality and GUI functionality. This may also include building the program as an exe and hosting that on the github. 

## Updated Documentation
The github should include example snippets and documentation of the process and code timing as will be documented in the Thesis writeup (this should help with writing in general)

## Thesis Writing

#### Introduction
Motivation for research and structure of paper established: See abstract for ideas.

#### Theory
This includes a background in some relevant parts of laser spectroscopy, as well as a simplified model of how a laser works. 

#### Method
This will be the bulk of the documentation for the actual laser control system. including figures like program flow charts, code timing charts, and images of the apparatus. This should also include some of the process and problems solved over the course of the Thesis work. 

#### Analysis
This will include analysis on the actual functionality of the laser; data on the feasability of interpolation methods, on the accuracy and precision of the generated laser, and its use in laser spectroscopy. This includes any measurements taken of actual methane samples in the future as well.

#### Conclusion
Restating the introduction with concluding statments driven by the analysis and discsussion of future work.




