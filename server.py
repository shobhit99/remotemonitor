from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
import numpy as np
from PIL import Image
import pickle
# import qdarkgraystyle
import sys
import socket
import time
import cv2

buffersize = 1024
sockets = {}
displayed_sockets = []
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


class MyThread(QThread):
    
    changevalue = pyqtSignal(str)

    def run(self):
        global sockets
        print('Starting Server...')
        ip = '0.0.0.0'
        port = 8000
        s.bind((ip, port))
        s.listen(10)
        buffersize=1024
        time.sleep(0.5)
        while True:
            da ,addr = s.accept()
            name = da.recv(1024)
            print(bytes.decode(name), "Connected to server.")
            self.changevalue.emit(str(bytes.decode(name)))
            sockets[bytes.decode(name)] = da


class Window(QMainWindow, QDialog):

    def __init__(self):
        super().__init__()
        self.selectedobject = None
        self.WindowProperties()
        self.WindowLayout()
        self.ServerThread()
        self.AllActions()
        self.MainMenu()
        self.fps = 0
        # self.MainToolbar()
        self.show()
    
    
    def WindowProperties(self):
        self.title = "LiveTrack"
        self.top = 100
        self.left = 100
        self.width = 800
        self.height = 600
        self.setWindowIcon(QtGui.QIcon("spy.png"))
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

    def ServerThread(self):
        self.thread = MyThread(self)
        self.thread.changevalue.connect(self.createinstance)
        self.thread.start()

    def WindowLayout(self):
        self.mainlayout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.mainlayout)
        self.LeftPane()
        self.RightPane()

    def MainMenu(self):
        
        mainmenu = self.menuBar()
        filemenu = mainmenu.addMenu("File")
        actionmenu = mainmenu.addMenu("Action")
        helpmenu = mainmenu.addMenu("Help")

        filemenu.addAction(self.exitaction)
        actionmenu.addAction(self.screenshotaction)
        actionmenu.addAction(self.clipboardaction)
        helpmenu.addAction(self.helpaction)

    def AllActions(self):
        self.exitaction = QAction(QIcon("exit.png"), 'Exit', self)
        self.exitaction.triggered.connect(self.exitapp)
        self.exitaction.setShortcut("Alt+F4")
        
        self.screenshotaction = QAction(QIcon("screenshot.png"), "Take Screenshot", self)
        self.screenshotaction.triggered.connect(lambda: self.executeCommands('screenshot'))
        self.screenshotaction.setShortcut("Ctrl+H")

        self.clipboardaction = QAction(QIcon("clipboard.png"), "Clipboard contents", self)
        self.clipboardaction.triggered.connect(lambda: self.executeCommands('clipboard'))

        self.helpaction = QAction(QIcon("help.png"), "Help", self)
        
    def MainToolbar(self):
        self.toolbar = self.addToolBar("ToolBar")
        self.toolbar.addAction(self.screenshotaction)
        self.toolbar.addAction(self.clipboardaction)
        self.toolbar.addAction(self.helpaction)

    def LeftPane(self):
        widget = QWidget()
        vbox = QVBoxLayout()
        widget.setLayout(vbox)
        widget.setMaximumWidth(350)

        activeLabel = QLabel("<b>Active Connections</b>")
        self.connectedUserList = QListWidget()
        self.connectedUserList.clicked.connect(self.setselecteditem)

        vbox.addWidget(activeLabel)
        vbox.addWidget(self.connectedUserList)
        self.mainlayout.addWidget(widget)

    def RightPane(self):

        tabWidget = QTabWidget()
        tabWidget.addTab(BasicCommands(self), "Basic Commands")
        tabWidget.addTab(Shell(self), "Shell")


        self.mainlayout.addWidget(tabWidget)

    def executeCommands(self, command, shellcommand='ls'):
        if self.selectedobject == None:
                pass
        else:
            # val currently is the name of connected user which will be used as a key
            val = str(self.selectedobject.text())
            # select the socket of that user
            da = sockets[val]
            # send length of command to be sent
            self.sendlength(command, da)
            if command == 'clipboard':
                da.send(b'clipboard')
                buf = b''
                # get the length of contents to be received
                contentlength = self.recvlength(da)
                while len(buf) < contentlength:
                    buf += da.recv(contentlength - len(buf))
                self.consoleoutput.setText(bytes.decode(buf))
            elif command == 'logout':
                da.send(b'logout')
            elif command == 'shutdown':
                da.send(b'shutdown')
            elif command == 'custom':
                shellcmd = shellcommand
                da.send(b'custom') 
                self.sendlength(shellcmd, da)
                da.send(str.encode(shellcmd))
                length = self.recvlength(da)
                buf = ''
                while len(buf) < length:
                    buf += bytes.decode(da.recv(length - len(buf)))
                self.outputConsole.setText(buf)
            elif command == 'screenshot':
                da.send(b'screenshot')
                imagebuf = b''
                length = self.recvlength(da)
                while len(imagebuf) < length:
                    data = da.recv(length - len(imagebuf))
                    imagebuf += data
                nparr = np.frombuffer(imagebuf, np.uint8)
                img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                cv2.imshow('Screenshot', img_np)
            elif command == 'sharescreen':
                da.send(b'sharescreen')
                # receive length of screen resolution pickle object
                length = self.recvlength(da)
                # receive pickle object
                dim = da.recv(length)
                dim = pickle.loads(dim)
                WIDTH, HEIGHT = dim[0], dim[1]
                now = time.time()
                self.xpos, self.ypos = 0, 0
                self.leftclick = False
                while True:
                    # create empty image buffer for receiving image bytes
                    imagebuf = b''
                    da.send(b'0')
                    length = self.recvlength(da)
                    while len(imagebuf) < length:
                        data = da.recv(length - len(imagebuf))
                        imagebuf += data
                    # recreate image using received bytes
                    image = Image.frombytes('RGB', (WIDTH,HEIGHT), imagebuf, 'raw')
                    img_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    cv2.imshow('screen {}'.format(val), img_np)
                    # display image
                    self.sendMouseEvent(val, da)
                    # caluclate fps 
                    self.fps += 1
                    again = time.time()
                    if again - now >= 1:
                        now = time.time()
                        print(self.fps)
                        self.fps = 0
                    # end calculate fps
                    # if q is pressed then exit the window
                    if (cv2.waitKey(1) & 0xFF) == ord('q'):
                        cv2.destroyAllWindows()
                        da.send(b'1')
                        break

    def exitapp(self):
        self.close()

    def sendMouseEvent(self, val, da):
        cv2.setMouseCallback('screen {}'.format(val), self.handleMouseEvent)
        pos = pickle.dumps([self.xpos, self.ypos, self.leftclick])
        self.leftclick = False
        self.sendlength(pos, da)
        da.send(pos)
    
    def handleMouseEvent(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.xpos = x
            self.ypos = y

        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.leftclick = True


    # send the lengh of data to be sent through socket
    def sendlength(self, data, sockobj):
        size = len(data)
        size_len = (size.bit_length() + 7) // 8
        sockobj.send(bytes([size_len]))

        size_bytes = size.to_bytes(size_len, 'big')
        sockobj.send(size_bytes)

    # receive the length of data to be received from socket
    def recvlength(self, sockobj):
        command_len = int.from_bytes(sockobj.recv(1), byteorder='big')
        length = int.from_bytes(sockobj.recv(command_len), byteorder='big')
        return length

    # adds connected user to connected users list
    def createinstance(self, username):
        item = QListWidgetItem()
        item.setText(username)
        item.setIcon(QIcon("img/desktop.png"))
        self.connectedUserList.insertItem(0, item)

    # update currently selected user
    def setselecteditem(self):
        self.selectedobject = self.connectedUserList.currentItem()

class BasicCommands(QWidget):
    def __init__(self, Window):
        super().__init__()
        self.obj = Window
        self.vbox = QVBoxLayout()
        self.addContents()
        self.setLayout(self.vbox)

    def addContents(self):
        
        # Basic Commands 
        
        rightpanesplitter = QSplitter(Qt.Vertical)
        commandWidget = QWidget()
        commandButtons = QGridLayout()
        commandWidget.setLayout(commandButtons)

        ## All Command buttons
        Screenshotbtn = QPushButton("Screenshot", self.obj)
        Screenshotbtn.setIcon(QtGui.QIcon("img/screenshot.png"))
        Screenshotbtn.setMaximumWidth(180)
        Screenshotbtn.setIconSize(QtCore.QSize(50,50))
        Screenshotbtn.clicked.connect(lambda: self.obj.executeCommands('screenshot'))

        Clipboardbtn = QPushButton("Clipboard", self.obj)
        Clipboardbtn.setIcon(QtGui.QIcon("img/clipboard.png"))
        Clipboardbtn.setMaximumWidth(180)
        Clipboardbtn.setIconSize(QtCore.QSize(50,50))
        Clipboardbtn.clicked.connect(lambda: self.obj.executeCommands('clipboard'))

        Shutdownbtn = QPushButton("Shutdown", self.obj)
        Shutdownbtn.setIcon(QtGui.QIcon("img/shutdown.png"))
        Shutdownbtn.setMaximumWidth(180)
        Shutdownbtn.setIconSize(QtCore.QSize(50,50))
        Shutdownbtn.clicked.connect(lambda: self.obj.executeCommands('shutdown'))

        Logoffbtn = QPushButton("Restart", self.obj)
        Logoffbtn.setIcon(QtGui.QIcon("img/restart.png"))
        Logoffbtn.setMaximumWidth(180)
        Logoffbtn.setIconSize(QtCore.QSize(50,50))
        Logoffbtn.clicked.connect(lambda: self.obj.executeCommands('Restart'))

        UnlockUSBbtn = QPushButton("Unlock USB", self.obj)
        UnlockUSBbtn.setIcon(QtGui.QIcon("img/usb-unlock.png"))
        UnlockUSBbtn.setMaximumWidth(180)
        UnlockUSBbtn.setIconSize(QtCore.QSize(50,50))

        remotedesktopBtn = QPushButton("Remote Desktop", self.obj)
        remotedesktopBtn.setIcon(QtGui.QIcon("img/remote.png"))
        remotedesktopBtn.setMaximumWidth(180)
        remotedesktopBtn.setIconSize(QtCore.QSize(50,50))
        remotedesktopBtn.clicked.connect(lambda: self.obj.executeCommands('sharescreen'))

        commandButtons.addWidget(Clipboardbtn, 0, 0)
        commandButtons.addWidget(Shutdownbtn, 0, 1)
        commandButtons.addWidget(Logoffbtn, 0, 2)
        commandButtons.addWidget(Screenshotbtn, 1, 0)
        commandButtons.addWidget(remotedesktopBtn, 1, 1)
        commandButtons.addWidget(UnlockUSBbtn, 1, 2)

        ## Buttons end

        ## Console output start
        label = QLabel("Output")
        self.obj.consoleoutput = QTextEdit()

        consoleoutputwidget = QWidget()
        consoleoutputlayout = QVBoxLayout()
        consoleoutputlayout.addWidget(label)
        consoleoutputlayout.addWidget(self.obj.consoleoutput)
        consoleoutputwidget.setLayout(consoleoutputlayout)

        ## Console output end
        

        rightpanesplitter.addWidget(commandWidget)
        rightpanesplitter.addWidget(consoleoutputwidget)
        
        self.vbox.addWidget(rightpanesplitter)

        # Basic Commands end

class Shell(QWidget):
    def __init__(self, Window):
        super().__init__()
        self.obj = Window
        self.vbox = QVBoxLayout()
        self.addContents()
        self.setLayout(self.vbox)

    def addContents(self):

        
        hbox = QHBoxLayout()
        commandinput = QLineEdit()
        commandinput.returnPressed.connect(lambda : self.obj.executeCommands('custom', commandinput.text()))

        execBtn = QPushButton("Execute")
        execBtn.setIcon(QtGui.QIcon("img/shell.png"))
        execBtn.clicked.connect(lambda : self.obj.executeCommands('custom', commandinput.text()))

        clearBtn = QPushButton("")
        clearBtn.setIcon(QtGui.QIcon("img/clear.png"))
        clearBtn.clicked.connect(lambda : self.obj.outputConsole.setText(""))

        hbox.addWidget(commandinput)
        hbox.addWidget(execBtn)
        hbox.addWidget(clearBtn)

        self.obj.outputConsole = QTextEdit()
        self.obj.outputConsole.setStyleSheet('background-color: #2C2C2C; color:#00FF00')

        
        self.vbox.addLayout(hbox)
        self.vbox.addWidget(self.obj.outputConsole)


App = QApplication(sys.argv)
# App.setStyleSheet(qdarkgraystyle.load_stylesheet())
window = Window()
sys.exit(App.exec())