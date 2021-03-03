import pyvisa


class HP_E1326B:
    def __init__(self, address):
        rm = pyvisa.ResourceManager()
        self.address = address
        self.device = rm.open_resource(address)
        self.device.clear()
        self.id=self.device.query("*IDN?")


    def read_volt_dc(self, channel_list):
        res=[]
     
        #Can only get 16 at a time
        if len(channel_list)>16:
            count=int(len(channel_list)/16)

            for i in range(count+2):
                if i<count:

                    self.device.write("CONF:VOLT:DC (@" + ",".join(channel_list[16*i:16*(i+1)]) + ");:")
                    res += self.read()
                else:

                    self.device.write("CONF:VOLT:DC (@" + ",".join(channel_list[16 * (i):]) + ");:")
                    res += self.read()

            return res

        else:

            if len(channel_list)>1:
                self.device.write("CONF:VOLT:DC (@" + ",".join(channel_list) + ");:")
            else:
                self.device.write("CONF:VOLT:DC (@" + ","+channel_list[0] + ");:")

            return self.read()


    def read_resistance(self, channel_list):
        self.device.write("CONF:RES (@" + ','.join(channel_list) + ");:")
        return self.read()

    def read(self):
        response = self.device.query("READ?").strip('\n').split(',')
        return response

if __name__=="__main__":
    a=HP_E1326B('GPIB1::9::3::INSTR')
    print(a.read_volt_dc(['101','607']))
