import time
from labjack import ljm

# 1. Open the LabJack T7 connection
# Handles can be 'ANY', 'USB', or 'ETHERNET'
handle = ljm.openS("T7", "ANY", "ANY")

# Define target channel (e.g., AIN0)
channel = "AIN2"

# 2. Define the configuration parameters
# We map configuration names to their corresponding values
config_names = [
    f"{channel}_EF_INDEX",       # Set Extended Feature index
    f"{channel}_EF_CONFIG_A",    # Number of samples to collect
    f"{channel}_EF_CONFIG_D"     # Scan rate / frequency (Hz)
]

config_values = [
    3,       # Index 3 = Average, Min, & Max mode
    100,     # Collect 100 samples per read cycle
    50000.0   # Sample at 5000 Hz (Total acquisition time = 100/5000 = 20 ms)
]

try:
    # 3. Write configuration to the T7
    # Note: Total acquisition time must NOT exceed 180 ms
    ljm.eWriteNames(handle, len(config_names), config_names, config_values)
    print(f"{channel} EF configured successfully.")
    
    # Small pause to allow hardware registers to clear and settle
    time.sleep(0.1)

    # 4. Perform a single read of the averaged samples
    # Reading _READ_A explicitly triggers the T7 to capture the burst and average it
    averaged_voltage = ljm.eReadName(handle, f"{channel}_EF_READ_A")
    print(f"Averaged Reading: {averaged_voltage:.5f} V")
    
    # Optional: Retrieve the Min and Max from that same burst
    min_voltage = ljm.eReadName(handle, f"{channel}_EF_READ_B")
    max_voltage = ljm.eReadName(handle, f"{channel}_EF_READ_C")
    print(f"Burst Minimum: {min_voltage:.5f} V | Burst Maximum: {max_voltage:.5f} V")

except ljm.LJMError as e:
    print(f"LJM Error occurred: {e}")

finally:
    # 5. Close the device connection cleanly
    ljm.close(handle)