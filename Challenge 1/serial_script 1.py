import time
import serial

port = "/dev/ttyUSB0"
baud = 115200
ser = serial.Serial(port, baudrate=baud, timeout=1)
char_list = list("abcdefghijklmnopqrstuvwxyz @!-_")
working_cmds = [""]

def explore(word):
    has_successor = False
    for char in char_list:
        try_w = word + char
        if try_w.startswith(" "):
            continue
        ser.write((try_w + "\n").encode("utf-8"))
        time.sleep(0.1)
        line = ser.read(ser.in_waiting).decode(errors="ignore")
        if "no command starts with" not in line:
            has_successor = True
            working_cmds.append(try_w)
            print(line)
            explore(try_w)  # recurse immediately (depth first search)
        ser.read(ser.in_waiting)
        time.sleep(2)
    if has_successor and word in working_cmds:
        working_cmds.remove(word)

explore("")
print(working_cmds)

ser.close()