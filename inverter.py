import serial
import time


class inverter:
    def __init__(self, port, baudrate):
    

        self.ser = serial.Serial(port=port, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,timeout=1)
        


        self.compressor_responses = {'5a-83-00-ff-24': 'Stopped', '5a-83-00-00-23': 'Running', '5a-83-01-00': 'Start fail', '5a-83-02-00': 'Overload', '5a-83-04-00': 'Under speed (1550 rpm or lower)',
                                 '5a-83-10-00': 'Short circuit', '5a-83-20-00': 'Over temperature', '5a-83-80-00': 'Set speed out of range'}

        self.com_error = {'F0': 'Error in 4th Byte', 'F2': 'Checksum error', 'F4': 'Command erro', 'F8': 'Error in the 3rd Byte'}
        self.current_set_speed=0
    def disconnect(self):
        self.ser.close()
    def parse_response(self, response):

       
        if response[:5] == '5a-83':
            return (self.compressor_responses[response])
        elif response[:5] == '5a-80':

            a = response[6:11].split('-')

            h = '0x' + a[1] + a[0]

            return (int(h, 16))
        elif response[:5] == '5a-86':

            a = response[6:11].split('-')

            h = '0x' + a[1] + a[0]

            return (int(h, 16))


        else:
            try:
               b=self.com_error[response[3:5]]
            except:
                b=response
            return ()

    def read_status(self):
        A = '0xA5'
        B = '0x3C'
        C = '0x83'
        D = '0X39'
        Sum = int(A, 16) + int(B, 16) + int(C, 16) + int(D, 16)

        checksum = 0xff - int(str(hex(Sum))[0:2] + str(hex(Sum))[-2] + str(hex(Sum))[-1], 16) + 1

        array = [int(A, 16), int(B, 16), int(C, 16), int(D, 16), checksum]
        values = bytearray(array)
        self.ser.write(values)

        response = []
        for i in range(5):
            a = self.ser.read()
            print(a)
            response.append(a.hex())
        RES=self.parse_response('-'.join(response))
        return RES

    def read_set_speed(self):
        A = '0xA5'
        B = '0x3C'
        C = '0x80'
        D = '0X39'
        Sum = int(A, 16) + int(B, 16) + int(C, 16) + int(D, 16)

        checksum = 0xff - int(str(hex(Sum))[0:2] + str(hex(Sum))[-2] + str(hex(Sum))[-1], 16) + 1

        array = [int(A, 16), int(B, 16), int(C, 16), int(D, 16), checksum]
        values = bytearray(array)
        self.ser.write(values)

        response = []
        for i in range(5):
            a = self.ser.read()

            response.append(a.hex())
        RES=self.parse_response('-'.join(response))
        return RES

    def read_speed(self):
      
        A = '0xA5'
        B = '0x3C'
        C = '0x86'
        D = '0X39'
        Sum = int(A, 16) + int(B, 16) + int(C, 16) + int(D, 16)

        checksum = 0xff - int(str(hex(Sum))[0:2] + str(hex(Sum))[-2] + str(hex(Sum))[-1], 16) + 1

        array = [int(A, 16), int(B, 16), int(C, 16), int(D, 16), checksum]
          
        values = bytearray(array)
      
        self.ser.write(values)
      
        response = []
      
        for i in range(5):
            a = self.ser.read()
          
            if a==b'':
             
                break

            response.append(a.hex())
      
        RES=self.parse_response('-'.join(response))
        return RES

    def set_rotation(self, rpm):
        self.current_set_speed=rpm

        A = '0xA5'
        B = '0xC3'
        if rpm==0:
            C = str(hex(rpm))[-2:].strip('0x')
            D = str(hex(rpm))[:-2].strip('0x')
        else:
            C = str(hex(rpm))[-2:]#.strip('0x')
            D = str(hex(rpm))[:-2]#.strip('0x')
            
        if C == '':
            C = '0'

        if D == '':
            D = '0'
        print(C,D)
        Sum = int(A, 16) + int(B, 16) + int(C, 16) + int(D, 16)

        checksum = 0xff - int(str(hex(Sum))[0:2] + str(hex(Sum))[-2] + str(hex(Sum))[-1], 16) + 1

        array = [int(A, 16), int(B, 16), int(C, 16), int(D, 16), checksum]
        #print(array)
        values = bytearray(array)
      
        self.ser.write(values)

        response = []

        for i in range(5):
            a = self.ser.read()

            response.append(a.hex())

        RES=self.parse_response('-'.join(response))

        return RES

if __name__=='__main__':
    a=inverter('COM4',600)
    a.set_rotation(2000)
   # while True:
 

       
