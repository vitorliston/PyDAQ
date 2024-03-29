import traceback
from time import sleep

import PyQt5
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
from Connect import connect
import serial

class Arduino(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)
        self.command_arduino = []

        self.thread = True
       
        self.variables = {'Valve': 0, 'fan_ff': 0, 'fan_fz': 0,'Check_valve':0,'Pumpout':0}
        self.names = {'V': 'Valve', 'FF': 'fan_ff', 'FZ': 'fan_fz','CK':'Check_valve','PP':'Pumpout'}
        self.serialConnection = None
        self.ready=True
    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.serialConnection = serial.Serial('com10',9600,timeout=1)
        except:
            self.serialConnection = None

        if self.serialConnection != None:
            self.signalStatus.emit('Arduino connected')

            while self.thread:

                try:

                    if self.command_arduino != [] and self.ready:
                        self.send_arduino()
                        self.ready=False
                        print("Sent {}".format(self.command_arduino[0]))
                        del self.command_arduino[0]

                    if self.serialConnection.inWaiting()>0:
                        a=self.read_arduino()

                        if bool(a):

                            self.variables.update(a)
                            self.ready=True
                            self.signalStatus.emit('UPDATE')


                    sleep(0.1)

                except:
                    print(traceback.print_exc())
        else:

            self.signalStatus.emit('Arduino not connected')

    def send_arduino(self):
        command = self.command_arduino[0]
        self.signalStatus.emit('Command in progress ' + command)
        self.serialConnection.write(command.encode())

        # response = self.serialConnection.readline().decode('utf-8').strip('\r\n').split(',')
        # print(response)
        self.signalStatus.emit('Command done ' + command)

       # res = {}

        # for i in response:
        #     r = i.split(':')
        #     if len(r) == 2:
        #         res[self.names[r[0]]] = float(r[1])

       # return res

    def read_arduino(self):

        response = self.serialConnection.readline().decode('utf-8').strip('\r\n').split(',')
        print("Received {}".format(response))
        res = {}

        for i in response:
            r = i.split(':')
            if len(r) == 2:
                res[self.names[r[0]]] = float(r[1])

        return res
