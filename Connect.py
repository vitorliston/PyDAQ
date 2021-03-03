import serial.tools.list_ports

def connect(description):


    ports = list(serial.tools.list_ports.comports())
    if ports!=[]:
        for p in ports:

            if description in p.description:

                # Connection to port
                s = serial.Serial(p.device,9600,timeout=1)

                print(s)
                return s

            else:
                s=None

        return s

