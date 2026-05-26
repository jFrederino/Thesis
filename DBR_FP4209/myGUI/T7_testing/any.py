from labjack import ljm

#(numFound, aDeviceTypes, aConnectionTypes, aSerialNumbers, aIPAddresses)
print(ljm.listAll(ljm.constants.dtANY, ljm.constants.dtANY))

# Open LabJack, (device name is set via Kipling App, or ljm+python if you prefer)
handle = ljm.openS(deviceType="T7", connectionType="ETHERNET", identifier="Terminator7")

# Call eReadName to read the serial number from the LabJack.
result = ljm.eReadName(handle, "SERIAL_NUMBER")

print(f"Serial Number = {result}")
print(ljm.eReadNameString(handle, "DEVICE_NAME_DEFAULT"))

#AIN0 is at REG ADDR 0
ain0 = ljm.eReadAddress(handle, address=0, dataType=ljm.constants.FLOAT32)
print(f"Voltage = {ain0}")