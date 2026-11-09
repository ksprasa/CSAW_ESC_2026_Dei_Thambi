import time
import serial

port = "/dev/ttyUSB0"
baud = 115200
ser = serial.Serial(port, baudrate=baud, timeout=1)

for i in range(1,101):
    ser.write((f"log{i}\n").encode("utf-8"))
    time.sleep(0.1)
    line = ser.read(ser.in_waiting).decode(errors="ignore")
    time.sleep(0.1)
    if "Peripheral check passed" not in line:
        print(line)

ser.close()