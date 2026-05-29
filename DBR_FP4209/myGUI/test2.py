from datetime import datetime
import os
from pathlib import Path

# Get current date and time
TIME = datetime.now()
print(TIME.strftime("%Y-%m-%d_%H:%M:%S"))
CWD = os.path.dirname(os.path.realpath(__file__))
TEMP_DIR = CWD + '/temp'

files = [f.name for f in Path(TEMP_DIR).iterdir() if f.is_file()]
print(files)
for index in range(10):
    print(index)
    for file in files: 
        if str(index) in file: 
            print(f' {1}' )
        else:
            print(f' {0}' )
