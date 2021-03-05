
from pymodbus.client.sync import ModbusSerialClient


class Eurotherm2216e( ModbusSerialClient ):


    def __init__(self, portname):
        ModbusSerialClient.__init__(self,  method='rtu',
        port=portname,
        baudrate=9600,
        timeout=3,
        parity='N',
        stopbits=1,
        bytesize=8)
        self.functions={'SETPOINT':self.set_sp_loop1,'HIGH':self.set_highlim_loop1,'LOW':self.set_lowlim_loop1,'OUTPUT':self.set_output_loop1,'MODE':self.set_mode_loop1}


    def get_pv_loop1(self,unit=1):
        """Return the process value (PV) for loop1."""
        res= self.read_holding_registers(1,unit=unit)
        res=self._parse_negative(res.registers[0])
        return round(res/100,2)

    def set_mode_loop1(self, value,unit=1):
        if value=='MANUAL':
            self.write_register(273, 1,unit=unit)
        else:
            self.write_register(273, 0, unit=unit)

    def get_mode_loop1(self,unit=1):
        """Return True if loop1 is in manual mode."""
        res= self.read_holding_registers(273,unit=unit)
        res = res.registers[0]  > 0

        if res:
            return 'MANUAL'
        elif not res:
            return 'AUTO'


    def get_sptarget_loop1(self,unit=1):
        """Return the setpoint (SP) target for loop1."""
        res= self.read_holding_registers(2,unit=unit)

        res = self._parse_negative(res.registers[0])

        return round(res / 100, 2)

    def get_targetout__loop1(self,unit=1):
        """Return the setpoint (SP) target for loop1."""
        res= self.read_holding_registers(3,unit=unit)

        return round(res.registers[0]/10,1)

    def get_sp_loop1(self,unit=1):
        """Return the (working) setpoint (SP) for loop1."""
        res= self.read_holding_registers(5,unit=unit)

        res = self._parse_negative(res.registers[0])

        return round(res / 100, 2)

    def set_sp_loop1(self, value,unit=1):
        """Set the SP1 for loop1.

        Note that this is not necessarily the working setpoint.

        Args:
            value (float): Setpoint (most often in degrees)
        """

        value = self._set_negative(value)

        self.write_register(2, value,unit=unit)


    def get_highlim_loop1(self,unit=1):
        """Return the (working) setpoint (SP) for loop1."""
        res= self.read_holding_registers(30,unit=unit)

        return round(res.registers[0]/10,1)

    def get_lowlim_loop1(self,unit=1):
        """Return the (working) setpoint (SP) for loop1."""
        res= self.read_holding_registers(31,unit=unit)

        return round(res.registers[0]/10,1)

    def set_highlim_loop1(self, value,unit=1):

        self.write_register(30, value,unit=unit)

    def set_lowlim_loop1(self, value,unit=1):

        self.write_register(31, value,unit=unit)

    def set_output_loop1(self, value, unit=1):
        if self.get_mode_loop1(unit=unit)=='MANUAL':
            self.write_register(3, value, unit=unit)



    def _parse_negative(self,value):

        if value>10000:
            return value-65536
        else:
            return value

    def _set_negative(self,value):

        if value<0:
            value = value+65536
            if value>65335:
                if str(int(value))[-1]=='6':
                    value-=1

            return value
        else:
            return value




