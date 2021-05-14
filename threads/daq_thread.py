from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from time import time

class daq_thread(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self, daq, savecheckbox, interval):
        QThread.__init__(self)
        self.daq = daq
        self.delta_time = 0
        self.variables = {}
        self.read = True
        self.save = savecheckbox.isChecked()
        self.save_file = '/test.txt'
        self.perform_read = True
        self.read_interval = interval
        self.write_header = True
        self.write_order = []
        self.record_time = 0
        self.autorange=False
        self.start_integral = False
        self.stop_integral = False
        self.reset_integral = False

        self.file = None
        self.path = None

    @pyqtSlot()
    def run(self):

        delta = -self.read_interval

        self.daq.reset_yokogawa()
        self.daq.autorange_yokogawa()


        last_time=0

        while self.read:
            if self.autorange:
                self.daq.autorange_yokogawa()
                self.autorange=False
            if self.start_integral:
                self.daq.start_yokogawa()
                self.start_integral=False
            if self.stop_integral:
                self.daq.stop_yokogawa()
                self.stop_integral=False
            if self.reset_integral:
                self.daq.reset_yokogawa()
                self.reset_integral=False

            self.msleep(int((max(self.read_interval + delta, 0)) * 1000))

            res = self.daq.read_all()



            self.variables.update(res)

            self.variables['dt'] = round(res['Time'] - last_time, 2)

            self.signalStatus.emit('D')
           
            delta += (self.read_interval - (res['Time'] - last_time)) * 0.5
     
            if delta > self.read_interval:
                delta = 0
            if delta < -self.read_interval:
                delta = -self.read_interval

            last_time = res['Time']


