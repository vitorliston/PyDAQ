import datetime
import time
from math import log

import pyvisa
from CoolProp.CoolProp import PropsSI
from Instruments.HP_E1326 import HP_E1326B
from Instruments.yokogawa import Yokogawa
from Instruments.Agilent_34980A import Agilent_34980A


class DAQ:
    def __init__(self):
        pass

    def initialize(self, config_file, curve_file, custom_vars='custom_vars.txt'):
        self.available_daq = {'E1326B': HP_E1326B,'34980A':Agilent_34980A}
        self.curves = {}
        self.config = {}
        self.custom_vars = None
        self.references = []
        self.yoko1_address = None
        self.yoko2_address = None
        self.init_time = time.time()

        if custom_vars != None:
            self.custom_vars = {}
            custom_vars = open(custom_vars, "r")
            for line in custom_vars:
                splitted = line.strip('\n').split(';')
                splitted[1] = splitted[1].replace("[", "daq['")
                splitted[1] = splitted[1].replace(']', "']")
                if splitted[0][0]!='#':
                    self.custom_vars[splitted[0]] = splitted[1]

        config_file = open(config_file, "r")

        for line in config_file:
            splitted = line.strip('\n').split(';')
            if splitted[0] == 'DAQ1':
                daq1_address = splitted[1]
            elif splitted[0] == 'REF':
                self.references = splitted[1:]
            elif splitted[0] == 'YOKO1':
                self.yoko1_address = splitted[1]
            elif splitted[0] == 'YOKO2':
                self.yoko2_address = splitted[1]
            else:
                self.config[splitted[0]] = splitted[1:]

        curve_file = open(curve_file, "r")

        for line in curve_file:
            splitted = line.split(';')
            self.curves[splitted[0]] = [float(i) for i in splitted[1:]]

        self.daq1 = None
        self.yoko1 = None
        self.yoko2 = None

        rm = pyvisa.ResourceManager()
        dev = rm.open_resource(daq1_address)
        daq = dev.query("*IDN?").split(',')[1]

        self.daq1 = self.available_daq[daq](daq1_address)

        if self.yoko1_address is not None:
            self.yoko1 = Yokogawa(self.yoko1_address, 'WT1_')

        if self.yoko2_address is not None:
            self.yoko2 = Yokogawa(self.yoko2_address, 'WT2_')

        self.temperature_vars = [v[0] for i, v in self.config.items() if v[1] == 'Temperature']

    def get_connected_devices(self):
        res = []
        if self.daq1 is not None:
            res.append('Connected to {} at {}'.format(self.daq1.id, self.daq1.address))
        if self.yoko1 is not None:
            res.append('Connected to {} at {}'.format(self.yoko1.id, self.yoko1.address))
        if self.yoko2 is not None:
            res.append('Connected to {} at {}'.format(self.yoko2.id, self.yoko2.address))
        return res

    def get_devices_identification(self):
        try:
            rm = pyvisa.ResourceManager()
            devices = rm.list_resources()
            id = []
            for i in devices:
                try:
                    dev = rm.open_resource(i)
                    id.append(i + ' ' + dev.query("*IDN?"))
                except:
                    pass
            return id
        except:
            return ['No devices found']

    def apply_termistor(self, ohm):
        ohm = log(ohm)
        reftemp = (1 / (0.001031 + (0.0002388 * ohm) + (0.000000158 * (ohm ** 3)))) - 273.15

        return reftemp

    def apply_termocouple(self, ref, reading):
        x = (-2.441936200E-03 + (3.847794980E-02 * (ref)) + (4.654600000E-05 * (ref ** 2)) + (-4.600000000E-08 * (ref ** 3)) + (1.000000000E-10 * (ref ** 4))) + reading * 1000

        return round((6.002517420E-02 + (2.599494743E+01 * (x)) + (-8.130258322E-01 * (x ** 2)) + (6.344980000E-02 * (x ** 3)) + (-4.107082300E-03 * (x ** 4)) + (1.276391000E-04 * (x ** 5))), 2)

    def apply_curve(self, val, ref, channel):

        try:
            if self.config[channel][1] == 'Temperature':
                return self.apply_termocouple(ref, val)

            else:

                value = 0
                i = 0
                for coef in self.curves[self.config[channel][1]]:
                    value += coef * val ** i
                    i += 1
                return round(value, 4)

        except:
            return round(val, 6)

    def read_daq(self):

        ch_list = list(self.config.keys())

        readings = {}
        ref = sum([self.apply_termistor(float(i)) for i in self.daq1.read_resistance(self.references)]) / 3

        read = [float(i) for i in self.daq1.read_volt_dc(ch_list)]
        readings['Date'] = str(datetime.datetime.now())

        for count, i in enumerate(ch_list):
            readings[self.config[i][0]] = self.apply_curve(read[count], ref, i)

        readings['T_Ref'] = round(ref, 2)
        return readings

    def read_yoko1(self):

        a = self.yoko1.read_normal()
        b = self.yoko1.read_integral()
        a.update(b)

        return a

    def read_yoko2(self):

        a = self.yoko2.read_normal()
        b = self.yoko2.read_integral()
        a.update(b)

        return a

    def start_yokogawa(self):
        if self.yoko1 is not None:
            self.yoko1.start_integral()
        if self.yoko2 is not None:
            self.yoko2.start_integral()

    def stop_yokogawa(self):
        if self.yoko1 is not None:
            self.yoko1.stop_integral()
        if self.yoko2 is not None:
            self.yoko2.stop_integral()

    def autorange_yokogawa(self):
        if self.yoko1 is not None:
            self.yoko1.auto_range_a(True)
            self.yoko1.auto_range_v(True)
        if self.yoko2 is not None:
            self.yoko2.auto_range_a(True)
            self.yoko2.auto_range_v(True)

    def reset_yokogawa(self):

        if self.yoko1 is not None:
            self.yoko1.reset_integral()
        if self.yoko2 is not None:
            self.yoko2.reset_integral()



    def read_all(self):
        daq = {}
        daq['Time'] = 0
        if self.yoko1 is not None:
            yoko1 = self.read_yoko1()
            daq.update(yoko1)
        if self.yoko2 is not None:
            yoko2 = self.read_yoko2()
            daq.update(yoko2)

        daq['Time'] = round(time.time() - self.init_time, 2)

        daq.update(self.read_daq())

        if self.custom_vars != None:

            for key, item in self.custom_vars.items():
                try:
                    a=eval(item)
                    if isinstance(a,str):
                        daq[key]=a
                    else:
                        daq[key] = round(a, 4)
                except Exception as e:
                    daq[key] = 0
                    print('Could not create custom variable {}'.format(key), e)

        return daq

#
#
# 0.0000E+00,0.0000E+00,-0.0000E+00,-0.000E+00,9.91E+37,9.91E+37,9.91E+37,9.91E+37,9.91E+37,9.91E+37,9.91E+37,9.91E+37,0,0,0
#
#
#
#
# a=DAQ('config.txt','curves.txt')
# a.yoko2.reset_integral()
# a.yoko2.start_integral()
# while True:
#
#     a.read_yoko()
#     time.sleep(1)
