import PyQt5
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
import serial
from numpy import fft, linspace, abs


class RPM_ACC(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self, port):
        QThread.__init__(self)

        self.port = port
        self.thread = True
        self.variables = {'RPM_acc_x': -1, 'RPM_acc_y': -1, 'RPM_acc_z': -1}

        self.ser = None
        self.connected = False
        self.ax = ['x', 'y', 'z']
        self.xyz = [[], [], []]
        self.max_rpm = 5000
        self.min_rpm = 1000
        self.last_x=0
        self.last_y=0
        self.last_z=0
        self.last_t = 0

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.ser = serial.Serial(self.port, 74880, timeout=1)
            self.connected = True



        except:
            self.variables = {'RPM_acc_x': -1, 'RPM_acc_y': -1, 'RPM_acc_z': -1}
           
            self.ser = None
            self.signalStatus.emit('RPM Failed')
            print('RPM arduino failed')




        if self.ser != None:

            a = []

            while len(a)!=4:
                try:
                    a=self.ser.readline().decode('utf-8').strip('\r\n').split(';')
                    print(a)
                except:
                    a=[]

            while self.thread:


                try:
                    a = self.ser.readline().decode('utf-8').strip('\r\n').split(';')


                except Exception as e:
                    print(e)

                self.process_rpm(a)
    def process_rpm(self, a):
            try:
                if len(self.xyz[0]) < 512:

                    try:
                        self.xyz[0].append(float(a[1])-self.last_x)
                        self.xyz[1].append(float(a[2])-self.last_y)
                        self.xyz[2].append(float(a[3])-self.last_z)
                        self.last_x=float(a[1])
                        self.last_y=float(a[2])
                        self.last_z=float(a[3])

                    except:
                        self.xyz[0].append(0)
                        self.xyz[1].append(0)
                        self.xyz[2].append(0)

                if len(self.xyz[0]) == 512:
                    dt=float(a[0])-self.last_t
                    if dt>0:
                        for i in range(3):
                            # print(a)
                            axis = self.xyz[i]
                            resolution = 512

                            transformed_y = fft.fft(axis)

                            # Take the absolute value of the complex numbers for magnitude spectrum
                            freqs_magnitude = abs(transformed_y)

                            # Create frequency x-axis that will span up to sample_rate

                            delta = 0.001 * dt / resolution
                            rate = 1 / delta

                            freq_axis = linspace(0, rate, len(freqs_magnitude))


                            rpm = round(freq_axis[freqs_magnitude.argmax()] * 60)
                            key = 'RPM_acc_' + self.ax[i]
                            if 1000<rpm<4700:
                                # print(dt,delta,rate,rpm,freq_axis[freqs_magnitude.argmax()])

                                self.variables[key] = rpm
                            else:
                                self.variables[key] =0
                            self.xyz[i] = []
                            self.last_t=float(a[0])

            except Exception as e:
                print(e)
