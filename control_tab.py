import time
import traceback
from PyQt5.QtCore import QTimer
from threads.arduino_thread import Arduino
from threads.inverter_thread import Inverter
from threads.rpm_acc_thread import RPM_ACC
from PyQt5 import QtCore, QtWidgets, uic
import os

class Control:
    def __init__(self, tab, status_bar):

        self.statusbar = status_bar
        self.ui = tab
        self.arduino_thread = None
        self.inverter_thread = None
        self.connected = False
        self.millis = 0
        self.custom_valve_control=False
        self.serialport = None
        self.time = []
        self.tff = []
        self.tfz = []
        self.rpm_acc_thread = None

        uic.loadUi(os.path.dirname(__file__) + '/control.ui', self.ui)

        self.ui.testbutton.clicked.connect(self.test)
        self.ui.connect.clicked.connect(self.connect_arduino)
        self.ui.setlogic.clicked.connect(self.set_logic)
        self.ui.rpmaccconnect.clicked.connect(self.connect_rpm_acc)
        self.ui.countdown_set.clicked.connect(self.set_countdown)
        self.ui.connectinverter.clicked.connect(self.connect_inverter)
        self.ui.controltest.clicked.connect(self.arduino_custom_command)
        self.ui.sendrpm.clicked.connect(self.custom_rpm)

        self.control_variables = {'Pumpout':0,'Check_valve': 0,'Valve': 0, 'fan_ff': 0, 'fan_fz': 0, 'RPM': -1, 'Only_fz': 0, 'Set_rpm': 0}#,'RPM_acc_x': -1, 'RPM_acc_y': -1, 'RPM_acc_z': -1}

        # self.valve_positions = {'Closed': 100, 'FF': 0, 'FF-FZ': 25, 'FZ': 50}
        self.valve_positions = {'Closed': 100, 'FF': 50, 'FF-FZ': 25, 'FZ': 0}

        self.valve_names = {}

        for key, val in self.valve_positions.items():
            self.valve_names[val] = key

        self.inverter = None

        self.only_fz = False
        self.compressor_ison = False
        self.logic_vars = {'fz_max': 0, 'fz_min': 0, 'fz_tol': 0, 'ff_max': 0, 'ff_min': 0, 'ff_tol': 0, 'rpm': 0, 'pd_rpm': 0,'pumpout':0,'dp':0,'logic':0}
        self.external_logic = None
        self.delay = 0
        self.roots = [1, 1]
        self.first = True
        self.stats = {'FZ': 0, 'FF': 0, 'Closed': 0, 'Time': 0, 'Off_time': 0, 'Wh': 0, 'FZ_avg': [], 'FF_avg': [],'Off':0,'Pumpout':0}
        self.cycle_finished = False
        self.timer=None
        self.ready=True
        self.pumpout=False
    def set_countdown(self):
        if self.ui.countdown_time.text()!='0':
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.set_logic)
            self.timer.start(int(float(self.ui.countdown_time.text())*3600*1000))
        else:
            self.timer.stop()
            self.timer=None
            print(self.timer)

    def set_logic(self):
        if self.timer!=None:
            self.timer.stop()
            self.timer=None


        self.logic_vars = {}
        if not self.ui.enablelogic.isChecked():
            self.first = True
        l = self.ui.logicinput.toPlainText().split('\n')

        self.ui.console.appendPlainText('Set logic:')
        for i in l:
            i = i.split(',')
            self.logic_vars[i[0]] = float(i[1])
            self.ui.console.appendPlainText(i[0] + ':' + str(i[1]))

        from logic import logic
        self.external_logic = logic

    def connect_inverter(self):

        if self.inverter_thread is not None:
            self.inverter_thread.inverter.ser.close()
            self.inverter_thread.thread=False

        self.inverter_thread = Inverter(self.ui.compport.text(), int(self.ui.compbaud.text()))
        self.inverter_thread.signalStatus.connect(self.update_gui_inverter)
        self.inverter_thread.start()

    def connect_rpm_acc(self):

        if self.rpm_acc_thread is not None and self.rpm_acc_thread.ser is not None:
            self.rpm_acc_thread.ser.close()
            self.rpm_acc_thread.thread = False

        self.rpm_acc_thread = RPM_ACC(self.ui.rpmaccport.text())
        self.rpm_acc_thread.signalStatus.connect(self.com)
        self.rpm_acc_thread.start()

        self.ui.rpmaccstatus.setText('Connected')
        self.ui.rpmaccstatus.setStyleSheet('color: green')

    def com(self, message):

        if message == 'Arduino not connected':
            self.arduino_thread = None
            self.ui.arduinostatus.setText('Error')
            self.ui.arduinostatus.setStyleSheet('color: red')
            self.statusbar.showMessage(message, 5000)
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + message)

        elif message == 'Arduino connected':
            self.ui.arduinostatus.setText('Connected')
            self.ui.arduinostatus.setStyleSheet('color: green')
            self.statusbar.showMessage(message, 5000)
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + message)

        elif message == 'UPDATE':
            self.update_gui_arduino()

        elif message == 'RPM Failed':
            self.ui.rpmaccstatus.setText('Error')
            self.ui.rpmaccstatus.setStyleSheet('color: red')

    def connect_arduino(self):

        if self.arduino_thread is not None:
            self.arduino_thread.serialConnection.close()
            self.arduino_thread.thread = False

        self.connected = True
        self.statusbar.showMessage('Connecting Arduino', 5000)
        self.arduino_thread = Arduino()
        self.arduino_thread.start()
        self.arduino_thread.signalStatus.connect(self.com)

        self.initialtime = time.time()



    def update_gui_arduino(self):
        #

        a = self.arduino_thread.variables

        valve_delta, ff_fan, fz_fan,ck_valve,pp = a['Valve'], int(a['fan_ff']), int(a['fan_fz']),int(a['Check_valve']),int(a['Pumpout'])
        if a['Pumpout']==0:
            self.pumpout=False
        else:
            self.pumpout=True

        if ck_valve != None:
            if ck_valve < 2000:
                self.ui.statusckvalve.setText(str(float(self.ui.statusckvalve.text()) + ck_valve))

            elif ck_valve > 2000:

                self.ui.statusckvalve.setText(str(float(self.ui.statusckvalve.text()) - ck_valve + 2000))

            if float(self.ui.statusckvalve.text()) < 0:

                self.ui.statusckvalve.setText('0')

            if float(self.ui.statusckvalve.text()) > 250:
                self.ui.statusckvalve.setText('250')


        if valve_delta != None:
            if valve_delta == 1000:
                self.ui.statusstep.setText('0')

            elif valve_delta > 1000:

                self.ui.statusstep.setText(str(float(self.ui.statusstep.text()) - valve_delta + 1000))
            else:
                self.ui.statusstep.setText(str(float(self.ui.statusstep.text()) + valve_delta))

            if float(self.ui.statusstep.text()) < 0:
                self.ui.statusstep.setText('0')
            if float(self.ui.statusstep.text()) > 100:
                self.ui.statusstep.setText('100')

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

    def update_gui_inverter(self, a):

        if a == 'Connected':
            self.ui.inverterstatus.setText('Connected')
            self.ui.inverterstatus.setStyleSheet('color: green')
            self.statusbar.showMessage('Inverter connected', 5000)
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + 'Inverter connected')
        if a == 'Error':
            self.ui.inverterstatus.setText('Error')
            self.ui.inverterstatus.setStyleSheet('color: red')
            self.statusbar.showMessage('Error inverter', 5000)
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + 'Error inverter')
            self.inverter_thread = None

        self.ui.statuscomp.setText(str(self.inverter_thread.variables['RPM']))

    def update_stats(self, daq_var):

        try:
            fan_ff=daq_var['fan_ff']
            fan_fz=daq_var['fan_fz']

            pos = self.valve_names[int(float(self.ui.statusstep.text()))]
            pp=daq_var['Pumpout']
            if self.compressor_ison:

                if self.cycle_finished:
                    self.cycle_finished = False
                    try:
                        fz = self.stats['FZ']
                        ff = self.stats['FF']
                        off = self.stats['Off']
                        pp=self.stats['Pumpout']
                        wh_old = self.stats['Wh']
                        dur=(fz + ff + off+pp) / 60
                        kwhmo = (1/1000)*(daq_var['Energy'] - wh_old)/(dur/60)*24*(365/12)

                        self.ui.cyclelog.appendPlainText('RTR ' + str(round(100 * (fz + ff+pp) / (fz + ff+pp + off), 2)))

                        self.ui.cyclelog.appendPlainText('FF_avg ' + str(round(sum(self.stats['FF_avg']) / len(self.stats['FF_avg']), 2)))
                        self.ui.cyclelog.appendPlainText('FZ_avg ' + str(round(sum(self.stats['FZ_avg']) / len(self.stats['FZ_avg']), 2)))

                        self.ui.cyclelog.appendPlainText('Efz ' + str(round(100 * (fz) / (fz + ff), 2)))
                        self.ui.cyclelog.appendPlainText('Eff ' + str(round(100 * (ff) / (fz + ff), 2)))
                        self.ui.cyclelog.appendPlainText('Duration [m] ' + str(round(dur, 2)))
                        self.ui.cyclelog.appendPlainText('Pumpout [m] ' + str(round(self.stats['Pumpout']/60, 2)))
                        self.ui.cyclelog.appendPlainText('Off  [m] ' + str(round(off / 60, 2)))
                        self.ui.cyclelog.appendPlainText('kwh/mo ' + str(round(kwhmo, 2)))
                        self.stats['Wh'] = daq_var['Energy']
                        self.stats['FZ'] = 0
                        self.stats['FF'] = 0
                        self.stats['Off'] = 0
                        self.stats['FF_avg'] = []
                        self.stats['FZ_avg'] = []
                        self.stats['Pumpout']=0
                        self.ui.cyclelog.appendPlainText('___________')
                    except:
                        pass

            if not self.compressor_ison:
                self.stats['Off'] += daq_var['dt']
            else:
                if pp==1:
                    self.stats['Pumpout'] += daq_var['dt']
                if fan_fz==1:
                    self.stats['FZ'] += daq_var['dt']
                if fan_ff==1:
                    self.stats['FF'] += daq_var['dt']




            self.stats['FF_avg'].append(daq_var['FF_air'])
            self.stats['FZ_avg'].append(daq_var['FZ_air'])

            if not self.compressor_ison:
                self.cycle_finished = True


        except Exception as e:
            print(traceback.print_exc())


    def update(self, daq_variables):

        try:

            if self.rpm_acc_thread is not None:
                self.control_variables.update(self.rpm_acc_thread.variables)
                # self.ui.statuscomp.setText(self.rpm_acc_thread.variables['RPM_acc_x'])

            if self.arduino_thread is not None:
                self.control_variables.update(self.arduino_thread.variables)



            if self.inverter_thread is not None:
                self.control_variables.update(self.inverter_thread.variables)



            self.control_variables['CKV_setting'] = float(self.ui.statusckvalve.text())
            self.control_variables['Valve_setting'] = self.valve_names[int(float(self.ui.statusstep.text()))]

            self.control_variables.update(self.logic_vars)
            self.control(daq_variables['FF_air'], daq_variables['FZ_air'])


            if self.custom_valve_control and self.ui.dpcontrol.isChecked() and self.ui.enablelogic.isChecked():
                self.parallel_ck_valve(daq_variables['P_fz'], daq_variables['P_suc'])


            if self.ui.enablelogic.isChecked():
                self.update_stats(daq_variables)



        except Exception as e:
            self.ui.errorconsole.appendPlainText('Control tab get_variables ERROR {}'.format(e))

            return {}

        return self.control_variables

    def parallel_ck_valve(self,P_fz,P_suc,test=False):
        if not self.pumpout and int(float(self.ui.statusckvalve.text()))==0:
            self.arduino_thread.command_arduino.append( "{},{},{},{},{}".format(0,0, 0,2015,0))
            # if P_fz-P_suc>self.logic_vars['dp']:
            #
            #     if int(float(self.ui.statusckvalve.text()))<=50:
            #
            #         self.arduino_thread.command_arduino.append( "{},{},{},{},{}".format(0,0, 0,10,0))
            #
            # if P_suc-P_fz>self.logic_vars['dp']:
            #
            #     if int(float(self.ui.statusckvalve.text())) >=5:
            #         self.arduino_thread.command_arduino.append( "{},{},{},{},{}".format(0,0, 0,2005,0))



    def arduino_custom_command(self):
        text = self.ui.controltest_text.text()

        if text == '':
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + 'Sent 0,0,0')
            self.arduino_thread.command_arduino.append('0,0,0\r')
        else:
            self.arduino_thread.command_arduino.append(text + '\r')
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + text)

    def test(self):
        a=self.ui.testfield.text().split(',')
        self.control(float(a[0]),float(a[1]),True)



    def control(self, T_ff, T_fz, test=False):
        try:
            self.ui.statuscomp.setText(str(self.inverter_thread.variables['RPM']))
        except:
            pass

        self.ui.statusfftemp.setText(str(round(T_ff, 2)))
        self.ui.statusfztemp.setText(str(round(T_fz, 2)))

        logic=int(self.logic_vars['logic'])

        if self.external_logic is not None and time.time() - self.delay > 60 or test:
            roots = [0, 0]
            if logic == 1:
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
            elif logic == 2:

                if not self.compressor_ison or self.only_fz:
                    if T_ff - self.logic_vars['ff_max'] > 0:

                        roots[0] = 1
                    else:
                        roots[0] = -1

                else:
                    if T_ff - self.logic_vars['ff_min'] > 0:
                        roots[0] = 1
                    else:
                        roots[0] = -1

                if self.compressor_ison:
                    if T_fz - self.logic_vars['fz_min'] > 0:
                        roots[1] = 1
                    else:
                        roots[1] = -1
                else:
                    roots[1] = 1

            elif logic == 3:

                if not self.compressor_ison or not self.only_fz:
                    if T_fz - self.logic_vars['fz_max'] > 0:

                        roots[0] = 1
                    else:
                        roots[0] = -1

                else:
                    if T_fz - self.logic_vars['fz_min'] > 0:
                        roots[0] = 1
                    else:
                        roots[0] = -1

                if self.compressor_ison:
                    if T_ff - self.logic_vars['ff_min'] > 0:
                        roots[1] = 1
                    else:
                        roots[1] = -1
                else:
                    roots[1] = 1


            if roots != self.roots or self.first:

                self.roots = roots


                only_fz, compressor_ison, pulldown = self.external_logic(T_ff, T_fz, self.logic_vars, self.only_fz, self.compressor_ison)


                #self.hybrid_control(only_fz, compressor_ison, pulldown,test)

                if compressor_ison and not only_fz and T_fz<T_ff-7:

                    pumpout=True

                else:
                    pumpout=False
                print()
                print('Roots crossed {} Tff: {} Tfz: {}'.format(roots,T_ff,T_fz))
                print('only_fz {} comp_ison {}, pulldown {} pumpout {}'.format(only_fz, compressor_ison, pulldown,pumpout))
                self.parallel_control(only_fz, compressor_ison, pulldown,pumpout,test)

    def parallel_control(self,only_fz, compressor_ison, pulldown,pumpout,test):


        pumpout_time=self.logic_vars['pumpout']*pumpout


        if not compressor_ison:
            valve_pos = self.valve_positions['Closed']
            fan_ff = '2'
            fan_fz = '2'
            comp_rpm = '0'
            self.custom_valve_control=False
            ck=250

        else:
            if only_fz:
                valve_pos = self.valve_positions['FZ']
                fan_ff = '2'
                fan_fz = '1'
                ck=250
                self.custom_valve_control=False
                comp_rpm = self.logic_vars['rpm']

            else:
                valve_pos = self.valve_positions['FF']
                fan_ff = '1'
                fan_fz = '2'
                comp_rpm = self.logic_vars['rpm']
                self.custom_valve_control=True
                ck = 0
            if pulldown:
                comp_rpm = self.logic_vars['pd_rpm']

            if pumpout:
                ck=250
                valve_pos=self.valve_positions['Closed']

        if self.ui.enablelogic.isChecked() or test:
            self.first = False
            self.delay = time.time()
            self.only_fz = only_fz
            self.compressor_ison = compressor_ison
            self.logic_command(test,valve_pos, fan_ff, fan_fz, comp_rpm,ck,pumpout_time)





    def logic_command(self, test,valve_pos, fan_ff, fan_fz, comp_rpm,ck=0,pumpout=0):

        rel_pos = valve_pos - float(self.ui.statusstep.text())

        rel_ck = ck - float(self.ui.statusckvalve.text())

        if rel_ck < 0:
            rel_ck = -rel_ck + 2000

        if rel_pos < 0:
            rel_pos = -rel_pos + 1000

        if test:
            self.ui.console.appendPlainText("{},{},{},{},{}".format(int(rel_pos), fan_ff, fan_fz, int(rel_ck), pumpout))
        else:
            self.inverter_thread.command_inverter = int(comp_rpm)
          #  if ck is not None:

            self.arduino_thread.command_arduino.append( "{},{},{},{},{}".format(int(rel_pos),fan_ff, fan_fz,int(rel_ck),int(pumpout)))

            self.ui.console.appendPlainText("{},{},{},{},{}".format(int(rel_pos),fan_ff, fan_fz,int(rel_ck),int(pumpout)))
            # else:
            #     self.arduino_thread.command_arduino.append( "{},{},{},{},".format(int(rel_pos),fan_ff, fan_fz,0))
            #     self.ui.console.appendPlainText("{},{},{},{},".format(int(rel_pos),fan_ff, fan_fz,0))





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
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + 'Sent ' + command)

            self.statusbar.showMessage('Command sent', 10000)
        else:

            self.ui.console.appendPlainText('Command still executing , please wait')
            self.statusbar.showMessage('Controller still executing command, please wait', 10000)

    def custom_rpm(self):
        if self.inverter_thread is not None:

            self.inverter_thread.command_inverter = int(self.ui.rpminput.text())
            self.ui.console.appendPlainText(time.strftime("%H:%M:%S ") + '' + 'Sent rpm ' + self.ui.rpminput.text())


    def hybrid_control(self,only_fz, compressor_ison, pulldown,test):
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
                fan_ff = '1'
                fan_fz = '1'

        if self.ui.enablelogic.isChecked() or test:
            self.first = False
            self.delay = time.time()
            self.only_fz = only_fz
            self.compressor_ison = compressor_ison
            if self.ui.enablelogic.isChecked():
                self.logic_command(test,valve_pos, fan_ff, fan_fz, comp_rpm)
# serialConnection = connect('USB-SERIAL CH340')
# while True:
# serialConnection.write('0,0,0\r'.encode())
#  response = serialConnection.readline().decode('utf-8').strip('\r')
#   print(response)
