import os
import sys

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from threads.daq_thread import daq_thread
from control_tab import Control
from Aquisition import DAQ
from plot import PlotWindow, PlotCurveItem
from pid_tab import pid_tab
QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        uic.loadUi(os.path.dirname(__file__) + '/ui.ui', self)
        uic.loadUi(os.path.dirname(__file__) + '/control.ui', self.control)
        self.pid_section=pid_tab(self)
        self.control_tab=Control(self.control,self)
        self.bstartdaq.clicked.connect(self.start_daq)
        self.bstopdaq.clicked.connect(self.stop_daq)
        self.bcloseall.clicked.connect(self.close_plots)

        self.bloadcolors.clicked.connect(self.load_plots)
        self.bsavecolors.clicked.connect(self.save_plots)

        self.bopencustom.clicked.connect(self.open_curves)
        self.bsavecustom.clicked.connect(self.save_custom)

        self.bclearplots.clicked.connect(self.clear_plots)
        self.bopensettings.clicked.connect(self.open_settings)
        self.bopencurves.clicked.connect(self.open_curves)
        self.bscan_instrument.clicked.connect(self.scan_instrumens)
        self.checksavefile.clicked.connect(self.record_test)
        self.bsavechangesset.clicked.connect(self.save_settings)
        self.bsavechangescurve.clicked.connect(self.save_curves)
        self.plots_colors={}

        self.daq=DAQ()
        self.daq_thread=None
        self.focusedsub = None
        self.variables = {}
        self.delta_time=0
       
        self.line_colors = [(255, 0, 0), (0, 200, 0), (0, 0, 230), (150, 150, 0), (0, 150, 150), (153, 51, 255), (255, 0, 255), (0, 0, 0)]


        self.mdi.subWindowActivated.connect(self.setfocusedsub)

        self.addplot.clicked.connect(self.add_plot)
        self.reorganize.clicked.connect(self.reorgsubs)
        self.treevar.setHeaderHidden(False)
        self.treevar.itemClicked.connect(self.onItemClicked)

        self.storedstring = ''

        self.settings_file='config.txt'
        self.curves_file='curves.txt'
        self.custom_file = 'custom_vars.txt'

        try:
            file = open(self.settings_file, 'r')

            self.settingstext.setPlainText(file.read())
        except:
            pass
        try:
            file = open(self.curves_file, 'r')

            self.curvestext.setPlainText(file.read())
        except:
            pass
        try:
            file = open(self.custom_file, 'r')

            self.customtext.setPlainText(file.read())
        except:
            pass

        self.genericthread=None
        self.save_file='test.txt'
        self.record=False
    def save_plots(self):
        i=0
        self.plots_colors={}

        for subwin in self.mdi.subWindowList():

            for subplot in subwin.plotlist:
                self.plots_colors['Sub'+str(i)]={}
                for curve in subplot['Plot'].curves:
                    if isinstance(curve, PlotCurveItem):
                        item_name = curve.name()
                        rgb=curve.opts['pen'].color().getRgb()
                        self.plots_colors['Sub'+str(i)][item_name]=rgb
                i+=1
        
        with open('colors.txt', 'w+') as file:
            file.write(str(self.plots_colors))


    def load_plots(self):
        self.close_plots()
        self.plots_colors = eval(open('colors.txt', 'r').read())
        for sub,plots in self.plots_colors.items():
            self.add_plot()

            for var,color in plots.items():
                if var in self.variables.keys():
                    a = PlotCurveItem(pen=pg.mkPen(color=color, width=1), name=var)
                    self.focusedsub.plotlist[0]['Plot'].addItem(a)
                    self.focusedsub.plotlist[0]['Ploted'][var] = a
                    a.setData(self.variables['Time'], self.variables[var])
                    a.get_avg()
        self.update_plots()




    def clear_plots(self):
        self.delta_time += self.variables['Time'][-1]
        self.variables={}
        self.first_output = True

    def record_test(self):
        save = self.checksavefile.isChecked()
        if save:
            self.checksavefile.setText('Recording')
            self.savefilepath.setDisabled(True)
        else:
            self.checksavefile.setText('Record')
            self.savefilepath.setDisabled(False)



        if self.daq_thread is not None:
            path = self.savefilepath.text()

            if path.split('.')[-1]!='txt':
                path+=r'\test.txt'



            self.daq_thread.save_file = path
            self.daq_thread.save = save
            self.daq_thread.write_header = True


    def open_custom(self):
        file = QFileDialog.getOpenFileName(self, " Open custom variables", '', filter="(*.txt) ")[0]
        self.custom_file = file
        file=open(file,'r')
        self.customtext.setPlainText(file.read())
    def save_custom(self):
        with open(self.custom_file, 'w') as yourFile:
            yourFile.write(str(self.customtext.toPlainText()))
        self.statusBar().showMessage('Custom variables saved, restart aquisition to apply changes',3000)


    def open_settings(self):
        file = QFileDialog.getOpenFileName(self, " Open settings", '', filter="(*.txt) ")[0]
        self.settings_file = file
        file=open(file,'r')
        self.settingstext.setPlainText(file.read())
    def open_curves(self):
        file = QFileDialog.getOpenFileName(self, " Open curves", '', filter="(*.txt) ")[0]
        self.curves_file = file
        file=open(file,'r')
        self.curvestext.setPlainText(file.read())

    def save_settings(self):
        with open(self.settings_file, 'w') as yourFile:
            yourFile.write(str(self.settingstext.toPlainText()))
        self.statusBar().showMessage('Settings saved, restart aquisition to apply changes',3000)

    def save_curves(self):
        with open(self.curves_file, 'w') as yourFile:
            yourFile.write(str(self.curvestext.toPlainText()))
        self.statusBar().showMessage('Curves saved, restart aquisition to apply changes', 3000)



    def scan_instrumens(self,response=False):

        if isinstance(response,bool):

            self.genericthread=generic_thread(self.daq.get_devices_identification)
            self.genericthread.start()
            self.genericthread.signalStatus.connect(self.scan_instrumens)
            self.instrument_scanner_text.appendPlainText('Scanning...')
        else:
            self.instrument_scanner_text.clear()

            self.instrument_scanner_text.appendPlainText(response)


    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onItemClicked(self, it, col):

        if self.focusedsub is not None:
            item_name = it.text(col)
            try:
                if not isinstance(self.variables[item_name][-1], str):
                    if it.checkState(0) == 2:

                        color = self.focusedsub.line_styles[0]


                        a = PlotCurveItem(pen=pg.mkPen(color=color, width=1), name=item_name)



                        self.focusedsub.focused['Plot'].addItem(a)

                        self.focusedsub.focused['Ploted'][item_name] = a
                        self.focusedsub.line_styles.remove(self.focusedsub.line_styles[0])
                        a.setData(self.variables['Time'], self.variables[item_name])
                        a.get_avg()


                    else:
                        if item_name in self.focusedsub.focused['Ploted'].keys():
                            item = self.focusedsub.focused['Ploted'][item_name]

                            self.focusedsub.line_styles.append(item.opts['pen'].color().getRgb())

                            self.focusedsub.focused['Plot'].removeItem(item)
                            del self.focusedsub.focused['Ploted'][item_name]
            except Exception as e:

                print('Could not plot variable',e)

    def update_plots(self):
        for subwin in self.mdi.subWindowList():
            for subplot in subwin.plotlist:
                for curve in subplot['Plot'].curves:
                    if isinstance(curve, PlotCurveItem):
                        item_name = curve.name()

                        curve.setData(self.variables['Time'], self.variables[item_name])
                        curve.get_avg()

    def add_variables(self, variables):

        self.treevar.clear()


        for var in variables:
            self.variables[var] = []
            item = QTreeWidgetItem(self.treevar)
            item.setText(0, var)
            item.setText(1, '0')
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)




      #  self.treevar.sortItems(0, QtCore.Qt.AscendingOrder)

    def reorgsubs(self):
        self.mdi.tileSubWindows()

    def setfocusedsub(self, sub):

        self.focusedsub = sub

    def add_plot(self):
        sub = PlotWindow(len(self.mdi.subWindowList()) + 1, self.treevar, self.variables,self.line_colors.copy())

        sub.layout().setContentsMargins(0, 0, 0, 0)

        self.mdi.addSubWindow(sub)

        self.focusedsub = sub
        sub.show()

        self.reorgsubs()

    def close_plots(self):
        self.mdi.closeAllSubWindows()

    def update_all(self):

        variables = self.daq_thread.variables
        variables['Time'] -= self.delta_time
        variables['Time']=round(variables['Time'],4)
        variables.update(self.control_tab.get_variables(variables))

        if self.first_output:
            output = []
            for key, val in variables.items():
                output.append(key)
                self.variables[key] = [val]
            self.add_variables(output)
            self.first_output = False
            self.daq_thread.write_order = output

            a=self.daq_thread.daq.get_connected_devices()
            for i in a:
                self.log_text.appendPlainText(i)

                self.variables[key].append(val)
            for toplevel in range(self.treevar.topLevelItemCount()):
                qitem = self.treevar.topLevelItem(toplevel)
                qitem.setText(1, str(variables[qitem.text(0)]))
        else:


            for key, val in variables.items():
                self.variables[key].append(val)
            for toplevel in range(self.treevar.topLevelItemCount()):
                qitem = self.treevar.topLevelItem(toplevel)
                qitem.setText(1, str(variables[qitem.text(0)]))

        self.update_plots()

    def start_daq(self):
        try:
            self.daq.initialize(self.settings_file, self.curves_file,self.custom_file)
            self.daqstatus.setText('Running')
            self.first_output = True


            self.daq_thread = daq_thread(self.daq,self.checksavefile,int(self.daqinterval.text()))
            self.daqinterval.setDisabled(True)
            self.daq_thread.start()
            self.daq_thread.signalStatus.connect(self.update_all)
        except Exception as e:

            self.log_text.setPlainText(str(e))
            self.daqstatus.setText('Connection error')
    def stop_daq(self):
        self.daqstatus.setText('Stopped')
        self.daqinterval.setDisabled(False)
        self.daq_thread.read=False
        self.savefilepath.setDisabled(False)

class generic_thread(QThread):
    signalStatus = pyqtSignal(str)

    def __init__(self,function):
        QThread.__init__(self)
        self.function=function
        self.response=None
    @pyqtSlot()
    def run(self):

        res=self.function()
        self.response=res

        self.signalStatus.emit("\n".join(self.response))







def run_DataViewer():
    app = QApplication(sys.argv)
    a = MainWindow()
    a.show()
    sys.exit(app.exec_())


if __name__ == '__main__':  # T
    run_DataViewer()

"""
2020
Developed by Vitor Junges Liston
Courtesy of Polo Labs

"""
