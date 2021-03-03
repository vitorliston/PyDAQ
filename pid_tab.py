import os
import time

import serial.tools.list_ports
from PyQt5 import QtCore, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from Instruments.PID import Eurotherm2216e
from functools import partial

class PID_window(QMdiSubWindow):
    def __init__(self, id, parent=None):
        super(PID_window, self).__init__(parent)
        self.id = id
        self.ui = QWidget()
        self.ui.setContentsMargins(0, 0, 0, 0)
        self.setWidget(self.ui)
        self.setMaximumSize(250, 400)
        self.commands={}
        uic.loadUi(os.path.dirname(__file__) + '/pid.ui', self.ui)

        self.ui.setpoint.textEdited.connect(partial(self.command,self.ui.setpoint,'SETPOINT',100))
        self.ui.output.textEdited.connect(partial(self.command,self.ui.output,'OUTPUT',10))
        self.ui.high.textEdited.connect(partial(self.command,self.ui.high,'HIGH',10))
        self.ui.low.textEdited.connect(partial(self.command,self.ui.low,'LOW',10))
        self.ui.mode.textActivated.connect(partial(self.command,self.ui.mode,'MODE'))
        self.ui.setpid.clicked.connect(self.set)
        self.scanning=False
        self.items_to_update=[]

    def command(self,item,setting,mult):
        self.items_to_update.append([item,setting,mult])
        # if setting=='MODE':
        #
        #     self.commands[setting]=item.currentText()
        # else:
        #     self.commands[setting]=int(float(item.text())*mult)

    def set(self):
        commands={}
        for param in self.items_to_update:
            item,setting,mult=param
            if setting == 'MODE':

                commands[setting] = item.currentText()
            else:
                commands[setting] = int(float(item.text()) * mult)
        self.commands=commands


    def closeEvent(self, closeEvent: QCloseEvent):
        self.hide()



class pid_tab:
    def __init__(self, ui):

        self.ui = ui
        self.ui.bscanpid.clicked.connect(self.scan)
        self.pid_thread = None
        self.pid_sub = {}
        self.scanning = False
    def scan(self):
        if not self.scanning:
            self.scanning = True
            self.ui.statusbar.showMessage('Scanning PIDs')
            self.pid_thread = pid_thread()
            self.pid_thread.signalStatus.connect(self.communication)
            self.pid_thread.start()

    def communication(self, message):
        if message == 'PID FOUND':
            self.add_pid()
        elif message == 'UPDATE':

            self.update_pids()

        elif message == 'SCAN DONE':
            self.scanning = False
            self.ui.statusbar.showMessage('PID scan done')

    def update_pids(self):

        for pid in self.pid_sub.keys():



            self.pid_sub[pid]['SUB'].ui.setpoint_display2.setText(str(self.pid_thread.pid_data[pid]['SP_TARGET']))
            self.pid_sub[pid]['SUB'].ui.output_display.setText(str(self.pid_thread.pid_data[pid]['OUTPUT']))
            self.pid_sub[pid]['SUB'].ui.pv_display.setText(str(self.pid_thread.pid_data[pid]['PV']))
            self.pid_sub[pid]['SUB'].ui.pv_display.setFont(QFont('MS Shell Dlg 2', 36))

            self.pid_sub[pid]['SUB'].ui.high_display.setText(str(self.pid_thread.pid_data[pid]['HIGH_LIMIT']))
            self.pid_sub[pid]['SUB'].ui.low_display.setText(str(self.pid_thread.pid_data[pid]['LOW_LIMIT']))
            mode=str(self.pid_thread.pid_data[pid]['MODE'])
            self.pid_sub[pid]['SUB'].ui.mode_display.setText(mode)

            if mode =='MANUAL':
                self.pid_sub[pid]['SUB'].ui.output.setDisabled(False)
            else:
                self.pid_sub[pid]['SUB'].ui.output.setDisabled(True)

        for pid in self.pid_sub.keys():
            if bool(self.pid_sub[pid]['SUB'].commands):

                self.pid_thread.commands[pid]=self.pid_sub[pid]['SUB'].commands
                self.pid_sub[pid]['SUB'].commands={}
                self.pid_thread.update_commands=True


    def add_pid(self):
        sub = PID_window(self.pid_thread.pid_ids[-1])

        sub.setWindowTitle('PID')
        a = QLabel('PID ' + str(self.pid_thread.pid_ids[-1]))
        b = QPushButton('Show')
        b.clicked.connect(partial(self.show,sub))
        self.ui.formLayout_10.addRow(a, b)

        self.ui.mdipid.addSubWindow(sub)
        sub.show()
        self.pid_sub[self.pid_thread.pid_ids[-1]] = {'SUB': sub, 'button': b}
    def show(self,sub):
        sub.show()

class pid_thread(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)
        self.thread = True
        self.pid_ids = []
        self.pid_data = {}
        self.pid = None
        self.pid_port = None
        self.commands={}
        self.update_commands=False
        self.update=True

    @QtCore.pyqtSlot()
    def run(self):

        ports = list(serial.tools.list_ports.comports())
        success = False
        for port in ports:
            if not success:
                a = Eurotherm2216e(port.name)

                for i in range(5):
                    try:
                        a.get_pv_loop1(unit=i)
                        success = True
                        self.pid = a
                        self.pid_port = port.name
                        self.pid_ids.append(i)
                        self.signalStatus.emit('PID FOUND')
                        self.pid_data[i] = {}
                        print(self.pid_port, self.pid_ids)


                    except:
                        pass

        self.signalStatus.emit('SCAN DONE')
        while self.thread:

            if self.update_commands:
                self.send_command()

            for pid in self.pid_data.keys():
                self.pid_data[pid]['PV'] = self.pid.get_pv_loop1(unit=pid)
                self.pid_data[pid]['OUTPUT'] = self.pid.get_targetout__loop1(unit=pid)

            if self.update:
                for pid in self.pid_data.keys():

                    self.pid_data[pid]['MODE'] = self.pid.get_mode_loop1(unit=pid)
                    self.pid_data[pid]['SP_TARGET'] = self.pid.get_sptarget_loop1(unit=pid)

                    self.pid_data[pid]['HIGH_LIMIT'] = self.pid.get_highlim_loop1(unit=pid)
                    self.pid_data[pid]['LOW_LIMIT'] = self.pid.get_lowlim_loop1(unit=pid)
                self.update = False
            self.signalStatus.emit('UPDATE')
            time.sleep(2)
    def send_command(self):

        for pid,commands in self.commands.items():
            for setting,value in commands.items():
                print(setting,value)
                try:
                    if setting!='MODE':
                        self.pid.functions[setting](int(value),unit=pid)
                    else:
                        self.pid.functions[setting](value, unit=pid)
                except:
                    pass
                time.sleep(0.1)
        self.update=True

        self.commands={}
        self.update_commands = False