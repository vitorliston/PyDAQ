import PyQt5
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow


from threads.arduino_thread import Arduino
from threads.inverter_thread import Inverter
import time
from inverter import inverter


class Control:
    def __init__(self, tab, main_interface):

        self.main_interface = main_interface
        self.ui = tab
        self.arduino_thread = None
        self.inverter_thread = None

        self.connected = False

        self.millis = 0

        self.serialport = None

        self.time = []
        self.tff = []
        self.tfz = []
        self.tfffilter = []
        self.tfzfilter = []

        self.ui.connect.clicked.connect(self.connect_arduino)
        self.ui.setlogic.clicked.connect(self.set_logic)

        self.ui.connectinverter.clicked.connect(self.connect_inverter)
        self.ui.controltest.clicked.connect(self.arduino_custom_command)
        self.ui.sendrpm.clicked.connect(self.custom_rpm)


        self.control_variables = {'Valve': 0, 'fan_ff': 0, 'fan_fz': 0, 'RPM': 0, 'Only_fz': 0,'Set_rpm':0}
        self.valve_positions = {'Closed': 100, 'FF': 50, 'FF-FZ': 25, 'FZ': 0}
        self.valve_names = {}
        for key, val in self.valve_positions.items():
            self.valve_names[val] = key

        self.inverter = None

        self.only_fz = False
        self.compressor_ison = False
        self.logic_vars = {'fz_max': 0, 'fz_min': 0, 'fz_tol': 0, 'ff_max': 0, 'ff_min': 0, 'ff_tol': 0, 'rpm': 0, 'pd_rpm': 0}
        self.external_logic = None
        self.delay = 0
        self.roots = [1, 1]
        self.first = True

    def set_logic(self):
        self.logic_vars={}
        self.first = True
        l = self.ui.logicinput.toPlainText().split('\n')
        self.ui.console.appendPlainText('Set logic:')
        for i in l:

            i=i.split(',')
            self.logic_vars[i[0]] = float(i[1])
            self.ui.console.appendPlainText(i[0]+':'+str(i[1]))



        from logic import logic
        self.external_logic = logic

    def connect_inverter(self):

        try:
            if self.inverter!=None:
                try:
                    self.inverter.disconnect()
                except:
                    pass

            self.inverter = inverter(self.ui.compport.text(), int(self.ui.compbaud.text()))
            self.inverter_thread = Inverter(self.inverter)
            self.inverter_thread.start()
            self.inverter_thread.signalStatus.connect(self.update_gui_inverter)

            self.ui.inverterstatus.setText('Connected')
            self.ui.inverterstatus.setStyleSheet('color: green')
            self.main_interface.statusbar.showMessage('Inverter connected', 5000)
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + 'Inverter connected')

        except Exception as e:
            print(e)
            self.ui.inverterstatus.setText('Error')
            self.ui.inverterstatus.setStyleSheet('color: red')
            self.main_interface.statusbar.showMessage('Error inverter', 5000)
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + 'Error inverter')
            self.inverter = None

    def com(self, message):

        if message == 'Arduino not connected':
            self.arduino_thread = None
            self.ui.arduinostatus.setText('Error')
            self.ui.arduinostatus.setStyleSheet('color: red')
            self.main_interface.statusbar.showMessage(message, 5000)
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + message)

        elif message == 'Arduino connected':
            self.ui.arduinostatus.setText('Connected')
            self.ui.arduinostatus.setStyleSheet('color: green')
            self.main_interface.statusbar.showMessage(message, 5000)
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + message)

        elif message == 'UPDATE':
            self.update_gui_arduino()



    def connect_arduino(self):

        if self.arduino_thread is None:
            self.connected = True
            self.main_interface.statusbar.showMessage('Connecting Arduino', 5000)
            self.arduino_thread = Arduino()
            self.arduino_thread.start()
            self.arduino_thread.signalStatus.connect(self.com)

            self.initialtime = time.time()

    def update_gui_arduino(self):
        #

        a=self.arduino_thread.variables

        valve_delta,ff_fan,fz_fan=a['Valve'],int(a['fan_ff']),int(a['fan_fz'])

        if valve_delta != None:
            if valve_delta == 3000:
                self.ui.statusstep.setText('0')

            elif valve_delta > 1000:

                self.ui.statusstep.setText(str(float(self.ui.statusstep.text()) - valve_delta + 1000))
            else:
                self.ui.statusstep.setText(str(float(self.ui.statusstep.text()) + valve_delta))
            if float(self.ui.statusstep.text()) < 0:
                self.ui.statusstep.setText('0')
            if float(self.ui.statusstep.text()) > 105:
                self.ui.statusstep.setText('105')

        if ff_fan is not None:

            if ff_fan == 1:
                self.ui.statusfffan.setText("On")
            else:
                self.ui.statusfffan.setText("Off")
        if fz_fan is not None:
            if fz_fan == 1:
                self.ui.statusfzfan.setText("On")
            else:
                self.ui.statusfzfan.setText("Off")

    def update_gui_inverter(self):

        self.ui.statuscomp.setText(str(self.inverter_thread.variables['RPM']))

    def get_variables(self,daq_variables):
        try:
            control_variables = self.control_variables.copy()
            if self.arduino_thread is not None:
                control_variables.update(self.arduino_thread.variables)
            if self.inverter_thread is not None:
                control_variables.update(self.inverter_thread.variables)



            control_variables['Valve_setting'] = self.valve_names[int(float(self.ui.statusstep.text()))]

            fz_air=(daq_variables['FZ_air_top']+daq_variables['FZ_air_bot'])*0.5
            ff_air = (daq_variables['FF_air_top'] + daq_variables['FF_air_bot']++ daq_variables['FF_air_mid1']++ daq_variables['FF_air_mid2']) * 0.25

            res=self.process_data(ff_air,fz_air)

            control_variables['FF_air_filter']=round(res[0],4)
            control_variables['FZ_air_filter'] = round(res[1],4)
        except Exception as e:
            print(e)
            return {}

        return control_variables

    def process_data(self, Tff, Tfz):
        self.tff.append(Tff)
        self.tfz.append(Tfz)

        if len(self.tff) > 6:
            Tff = sum(self.tff[-5:]) / 5
            Tfz = sum(self.tfz[-5:]) / 5

        self.tfffilter.append(Tff)
        self.tfzfilter.append(Tfz)

        self.control(self.tfffilter[-1], self.tfzfilter[-1])
        self.ui.statusfftemp.setText(str(round(self.tfffilter[-1], 2)))
        self.ui.statusfztemp.setText(str(round(self.tfzfilter[-1], 2)))
        return self.tfffilter[-1],self.tfzfilter[-1]

    def arduino_custom_command(self):
        text = self.ui.controltest_text.text()

        if text == '':
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + 'Sent 0,0,0')
            self.arduino_thread.command_arduino.append('0,0,0\r')
        else:
            self.arduino_thread.command_arduino.append(text+'\r')
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + text)

    def control(self, T_ff, T_fz, test=False):
        logic=2
        if self.external_logic is not None and time.time() - self.delay > 120 or test:
            roots = [0, 0]
            if logic ==1:
                if not self.compressor_ison:
                    if T_fz - self.logic_vars['fz_max'] > 0:
                        roots[0] = 1
                    else:
                        roots[0] = -1

                else:
                    if T_fz - self.logic_vars['fz_min'] > 0:
                        roots[0] = 1
                    else:
                        roots[0] = -1

                if not self.compressor_ison or self.only_fz:
                    if T_ff - self.logic_vars['ff_max'] > 0:
                        roots[1] = 1
                    else:
                        roots[1] = -1

                else:
                    if T_ff - self.logic_vars['ff_min'] > 0:
                        roots[1] = 1
                    else:
                        roots[1] = -1
            elif logic==2:


                if not self.compressor_ison or self.only_fz:
                    if T_ff - self.logic_vars['ff_max']>0:

                        roots[0] = 1
                    else:
                        roots[0] = -1

                else:
                    if T_ff - self.logic_vars['ff_min']>0:
                        roots[0] = 1
                    else:
                        roots[0] = -1



                if self.compressor_ison:
                    if T_fz - self.logic_vars['fz_min']>0:
                        roots[1] = 1
                    else:
                        roots[1] = -1
                else:
                    roots[1] = 1

            if roots != self.roots or self.first:

                self.roots = roots
                print('Roots crossed ', roots)
                only_fz, compressor_ison, pulldown = self.external_logic(T_ff, T_fz, self.logic_vars, self.only_fz, self.compressor_ison)

                print('Logic only_fz,comp', only_fz, compressor_ison)

                if not compressor_ison:
                    valve_pos = self.valve_positions['Closed']
                    fan_ff = '2'
                    fan_fz = '2'
                    comp_rpm = '0'
                else:
                    if only_fz:
                        valve_pos = self.valve_positions['FZ']
                        fan_ff = '2'
                        fan_fz = '1'
                        comp_rpm = self.logic_vars['rpm']
                    else:
                        valve_pos = self.valve_positions['FF']
                        fan_ff = '1'
                        fan_fz = '2'
                        comp_rpm = self.logic_vars['rpm']

                    if pulldown:
                        comp_rpm = self.logic_vars['pd_rpm']

                if self.ui.enablelogic.isChecked() or test:
                    self.first = False
                    self.delay = time.time()
                    self.only_fz = only_fz
                    self.compressor_ison = compressor_ison
                    if self.ui.enablelogic.isChecked():
                        self.logic_command(valve_pos, fan_ff, fan_fz, comp_rpm)

    def logic_command(self, valve_pos, fan_ff, fan_fz, comp_rpm):

        rel_pos = valve_pos - float(self.ui.statusstep.text())
        if rel_pos < 0:
            rel_pos = -rel_pos + 1000

        self.arduino_thread.command_arduino.append(str(int(rel_pos)) + ',' + fan_ff + ',' + fan_fz + ',')

        self.inverter_thread.command_inverter = int(comp_rpm)

        self.ui.console.appendPlainText(str(rel_pos) + ',' + fan_ff + ',' + fan_fz + ',' + str(comp_rpm))

    def custom_command(self):
        if self.arduino_thread.command_status == 'Done':
            try:
                i1rel = float(self.ui.customvalve.text()) - float(self.ui.statusstep.text())
            except:
                i1rel = 0
            if i1rel < 0:

                i1 = str(-i1rel + 1000)
            else:
                i1 = str(i1rel)

            i2 = self.ui.customfffan.text()
            i3 = self.ui.customfzfan.text()

            command = i1 + ',' + i2 + ',' + i3

            self.arduino_thread.command_arduino.append(command)
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' + 'Sent '+ command)

            self.main_interface.statusbar.showMessage('Command sent', 10000)
        else:

            self.ui.console.appendPlainText('Command still executing , please wait')
            self.main_interface.statusbar.showMessage('Controller still executing command, please wait', 10000)

    def custom_rpm(self):
        if self.arduino_thread is not None and self.inverter is not None:

            self.inverter_thread.command_inverter = int(self.ui.rpminput.text())
        elif self.inverter is not None:
            self.inverter.set_rotation(int(self.ui.rpminput.text()))
            self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' +'Sent rpm ' + self.ui.rpminput.text())

    def reset_valve(self):
        command = '3000' + ',0,0'
        self.ui.console.appendPlainText(time.strftime("%Y:%m:%d %H:%M:%S") + '\n' +'Sent reset valve ' + command)
        self.arduino_thread.command_arduino.append(command)






    
#serialConnection = connect('USB-SERIAL CH340')
#while True:
   # serialConnection.write('0,0,0\r'.encode())
  #  response = serialConnection.readline().decode('utf-8').strip('\r\n')
 #   print(response)
