from multiprocessing import Process
import keyboard
import time

def loop():
    while True:
        print("a")
        time.sleep(1)

if __name__ == "__main__":
    process = Process(target=loop)
    process.start()
    while process.is_alive():
        if keyboard.is_pressed('q'):
            process.terminate()
            break

