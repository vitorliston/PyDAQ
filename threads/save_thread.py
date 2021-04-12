from PyQt5.QtCore import QThread,pyqtSignal,pyqtSlot
import os
from time import time,sleep


class save_thread(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self, filename,write_order):
        QThread.__init__(self)
        self.daq = filename

        self.save_file=filename
        self.file=None
        self.path=None
        self.save_point=False
        self.record_time=0
        self.variables=None
        self.delta_time=0
        self.save=True
        self.write_header = True
        self.write_order=write_order
    @pyqtSlot()
    def run(self):

        while self.save:
            sleep(0.1)
            if self.save_point:
                self.save_to_file()
                self.save_point=False

    def save_to_file(self):

        if self.write_header:
            self.path = os.path.join('Saved_files', self.save_file)

            self.file = open(self.path, 'a')

            self.delta_time = int(self.variables['Time'])

            self.write_header = False

            self.file.write(';'.join(self.write_order) + '\n')

        self.file = open(self.path, 'a')

        listt = []
        variables = self.variables.copy()

        variables['Time'] = round(variables['Time'] - self.delta_time, 2)

        self.record_time = variables['Time']

        for key in self.write_order:
            listt.append(str(variables[key]))

        self.file.write(';'.join(listt) + '\n')
        self.file.close()
