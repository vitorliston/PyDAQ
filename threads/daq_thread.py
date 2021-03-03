from PyQt5.QtCore import QThread,pyqtSignal,pyqtSlot


class daq_thread(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self, daq, savecheckbox, interval):
        QThread.__init__(self)
        self.daq = daq
        self.delta_time = 0
        self.variables = {}
        self.read = True
        self.save = savecheckbox.isChecked()
        self.save_file = '../test.txt'
        self.perform_read = True
        self.read_interval = interval
        self.write_header = True
        self.write_order = []

    @pyqtSlot()
    def run(self):
        last_time = 0
        delta = 0
        self.daq.reset_yokogawa()

        while self.read:

            self.msleep(int((max(self.read_interval + delta, 0)) * 1000))

            res = self.daq.read_all()

            for key, val in res.items():
                try:
                    val = round(val, 4)
                except:
                    pass
                self.variables[key] = val

            self.signalStatus.emit('D')
            if self.save:
                self.save_to_file()
            delta += (self.read_interval - (res['Time'] - last_time))

            last_time = res['Time']

    def save_to_file(self):

        file_object = open(self.save_file, 'a')

        if self.write_header:
            self.delta_time = self.variables['Time']
            self.write_header = False
            self.daq.start_recording()
            file_object.write(','.join(self.write_order) + '\n')
        else:
            list = []
            variables = self.variables.copy()
            variables['Time'] -= self.delta_time
            for key in self.write_order:
                list.append(str(variables[key]))
            file_object.write(','.join(list) + '\n')

        file_object.close()
