
import pyvisa



"Generic class for Yokogawa Power Meter, reference manual https://www.axiomtest.com/documents/models/Yokogawa%20WT110%20data%20sheet.pdf"

class Yokogawa:
    def __init__(self,address,yoko_identifier=''):
        rm = pyvisa.ResourceManager()
        self.address = address
        self.identifier=yoko_identifier
        self.device = rm.open_resource(address)
        self.id = self.device.query("*IDN?")




        self.normal_output=['V1','V2','V3','V_SUM','A1','A2','A3','A_SUM','W1','W2','W3','W_SUM']
        self.integral_output = ['W1','W2','W3','W_SUM','WH1','WH2','WH3','WH_SUM','AH1','AH2','AH3','AH_SUM','H','M','S']

        self.auto_range_v(True)
        self.auto_range_a(True)
    def read_normal(self):

        self.device.write(":MEASURE:NORMAL:ITEM:PRESET NORMAL")
        resp=self.device.query(":MEASURE:NORMAL:VALUE?").strip('/n').split(',')

        resp={self.identifier+self.normal_output[index]:float(val) for index,val in enumerate(resp)}

        for key,val in resp.items():

            if val>1e20:
                self.auto_range_v(True)
                self.auto_range_a(True)
                resp[key]=0

        return resp

    def read_integral(self):

        self.device.write(":MEASURE:NORMAL:ITEM:PRESET INTEGRATE")
        resp=self.device.query(":MEASURE:NORMAL:VALUE?").strip('/n').split(',')
        resp={self.identifier+self.integral_output[index]:float(val) for index,val in enumerate(resp)}
        for key,val in resp.items():

            if val>1e20:
                resp[key]=0


        return resp

    def auto_range_v(self,on):
        print('Autorange voltage {}'.format(self.identifier))
        if on:
            self.device.write(":VOLTAGE:AUTO ON")
        else:
            self.device.write(":VOLTAGE:AUTO OFF")

    def auto_range_a(self,on):
        print('Autorange current {}'.format(self.identifier))
        if on:
            self.device.write(":CURRENT:AUTO ON")
        else:
            self.device.write(":CURRENT:AUTO OFF")

    def a_range(self,range):
        self.device.write(":CURRENT:RANGE {}A".format(range))

    def reset_integral(self):
        print('Reset integral {}'.format(self.identifier))
        self.stop_integral()
        self.device.write(":INTEGRATE:RESET")


    def start_integral(self):
        print('Start integral {}'.format(self.identifier))
        self.device.write(":INTEGRATE:START")
    def stop_integral(self):
        self.device.write(":INTEGRATE:STOP")
    def query(self,command):
        res=self.device.query(command)
        return res
    def write(self,command):
        res=self.device.write(command)
        return res
