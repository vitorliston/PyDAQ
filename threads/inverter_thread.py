
from PyQt5.QtWidgets import QMainWindow
from time import sleep

import PyQt5
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal


PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


class Inverter(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self, inverter):
        QThread.__init__(self)

        self.command_inverter = None
        self.testvariable = 0
        self.thread = True
        self.variables = {}
        self.variables['RPM'] = 0
        self.variables['Set_rpm'] = 0
        self.inverter = inverter

    @QtCore.pyqtSlot()
    def run(self):

        while self.thread:
            sleep(2)
            self.variables['Set_rpm'] = self.inverter.current_set_speed
            if self.command_inverter is not None:
                self.send_inverter()

            else:
                rpm = self.read_inverter_speed()

                if -1 <= rpm <= 5000:
                    self.variables['RPM'] = rpm

    def send_inverter(self):
        self.signalStatus.emit('Inverter command sent ' + str(self.command_inverter))
        self.inverter.set_rotation(self.command_inverter)
        self.command_inverter = None

    def read_inverter_speed(self):
        try:
            rpm = float(self.inverter.read_speed())
        except:
            rpm = -1
        return rpm
