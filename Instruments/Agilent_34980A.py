import pyvisa


class Agilent_34980A:
    def __init__(self, address):
        rm = pyvisa.ResourceManager()
        self.address = address
        self.device = rm.open_resource(address)
        self.device.timeout = 20000
        self.id=self.device.query("*IDN?")
        self.first_dc=True
        self.first_res = True
        print(self.id)

    def config_dc(self,channel_list):
        self.device.write("CONF:VOLT_DC (@" + ','.join(channel_list) + ");")

    def config_res(self,channel_list):
        self.device.write("CONF:RES (@" + ','.join(channel_list) + ");")


    def read_volt_dc(self, channel_list):
        if self.first_dc:
            self.config_dc(channel_list)
            self.first_dc = False
        
       
       
        self.device.write("ROUT:SCAN (@" + ",".join(channel_list) + ");")
       
        return self.read()


    def read_resistance(self, channel_list):
        if self.first_res:
            self.config_res(channel_list)
            self.first_res = False


        self.device.write("ROUT:SCAN (@" + ','.join(channel_list) + ");")
       
        return self.read()

    def read(self):

        response = self.device.query("READ?").strip('\n').split(',')
      
        return response

if __name__=="__main__":
    import time





    a=Agilent_34980A('GPIB0::9::INSTR')
    while True:
        b=['6001','6002']
      

        print(a.read_volt_dc(b))
        time.sleep(3)
           
                
