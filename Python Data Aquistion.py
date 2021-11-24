import os
import sys
import traceback
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from threads.daq_thread import daq_thread
from threads.save_thread import save_thread
from control_tab import Control
from Aquisition import DAQ
from plot import PlotWindow, PlotCurveItem
from pid_tab import pid_tab
import matplotlib.cm as cm
import sys
QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
import random
import csv
import time
from datetime import datetime

class system_out:
    def __init__(self,stdout):
        self.stdout=stdout
        self.file = open('log.txt',"w")
    def write(self,message):


        self.stdout.write(message)
        if message!='\n':
            self.file.write(datetime.now().strftime("%d/%m %H:%M:%S "))
            self.file.write(message+'\n')
    def flush(self):
        self.file.flush()
        self.stdout.flush()

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        sys.stdout=system_out(sys.stdout)

        uic.loadUi(os.path.dirname(__file__) + '/ui.ui', self)
        uic.loadUi(os.path.dirname(__file__) + '/control.ui', self.control)
        self.pid_section=pid_tab(self)
        self.control_tab=Control(self.control,self)
        self.bstartdaq.clicked.connect(self.start_daq)
        self.bstopdaq.clicked.connect(self.stop_daq)
        self.bcloseall.clicked.connect(self.close_plots)

        self.bloadcolors.clicked.connect(self.load_plots)
        self.bsavecolors.clicked.connect(self.save_plots)
        self.exportvar.clicked.connect(self.export_var)
        self.autorange.clicked.connect(self.autorange_yokos)
        self.resetintegral.clicked.connect(self.reset_yokos)
        self.startintegral.clicked.connect(self.start_yokos)
        self.stopintegral.clicked.connect(self.stop_yokos)

        self.bopencustom.clicked.connect(self.open_curves)
        self.bsavecustom.clicked.connect(self.save_custom)

        self.bclearplots.clicked.connect(self.clear_plots)
        self.bopensettings.clicked.connect(self.open_settings)
        self.bopencurves.clicked.connect(self.open_curves)
        self.bscan_instrument.clicked.connect(self.scan_instrumens)
        self.checksavefile.clicked.connect(self.record_test)
        self.bsavechangesset.clicked.connect(self.save_settings)
        self.bsavechangescurve.clicked.connect(self.save_curves)
      #  self.linkaxis.clicked.connect(self.link_plots)
        self.plots_colors={}

        self.daq=DAQ()
        self.daq_thread=None
        self.focusedsub = None
        self.variables = {}
        self.delta_time=0
       
        self.line_colors = [(255, 0, 0), (0, 200, 0), (0, 0, 230), (150, 150, 0), (0, 150, 150), (153, 51, 255), (255, 0, 255), (0, 0, 0)]

        self.variable_widgets=[]
        self.mdi.subWindowActivated.connect(self.setfocusedsub)
        self.colormap=cm.jet
        self.addplot.clicked.connect(self.add_plot)
        self.reorganize.clicked.connect(self.reorgsubs)
        self.treevar.setHeaderHidden(False)
        self.treevar.itemClicked.connect(self.onItemClicked)

        self.storedstring = ''

        self.settings_file='config.txt'
        self.curves_file='curves.txt'
        self.custom_file = 'custom_vars.txt'
        self.load_config_files()
    def export_var(self):
        with open("Saved_files/exported_vars.csv", "w") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(self.variables.keys())
            writer.writerows(zip(*self.variables.values()))

    def load_config_files(self):
        self.save_thread = None
        self.settings_model = QStandardItemModel(self)

        self.write_order = []
        self.tableView.setModel(self.settings_model)

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

        self.genericthread = None
        self.save_file = 'test.csv'
        self.record = False
        try:
            self.table_loadCsv(self.settings_file, self.settings_model, ['Channel', 'Name', 'Curve'])
        except:
            pass



    def autorange_yokos(self):
        if self.daq_thread is not None:
            self.daq_thread.autorange=True

    def stop_yokos(self):
        if self.daq_thread is not None:
            self.daq_thread.stop_integral=True
    def start_yokos(self):
        if self.daq_thread is not None:
            self.daq_thread.start_integral=True
    def reset_yokos(self):
        if self.daq_thread is not None:
            self.daq_thread.reset_integral=True

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
        if len(self.variables['Time'])>0:
            self.delta_time += self.variables['Time'][-1]
            self.variables={}
            self.first_output = True

    def record_test(self):
        save = self.checksavefile.isChecked()
        if save:
            if self.daq_thread is not None:

                self.checksavefile.setText('Recording')
                self.savefilepath.setDisabled(True)
                path = self.savefilepath.text()

                if path.split('.')[-1]!='csv':
                    path+='.csv'

                self.save_thread = save_thread(path,self.write_order)
                self.daq_thread.daq.start_yokogawa()
                self.save_thread.start()

        else:
            self.checksavefile.setText('Record')
            self.savefilepath.setDisabled(False)
            self.save_thread.save=False
            self.save_thread=None








    def table_loadCsv(self, fileName,model,header):
        with open(fileName, "r") as fileInput:
            for row in csv.reader(fileInput,delimiter=';'):
                items = [
                    QStandardItem(field)
                    for field in row
                ]
                model.appendRow(items)

        for i,val in enumerate(header):
            model.setHeaderData(i, Qt.Horizontal, val)



    def table_writeCsv(self, fileName,model):
        with open(fileName, "w") as fileOutput:
            writer = csv.writer(fileOutput,delimiter=';')
            for rowNumber in range(self.model.rowCount()):
                fields = [
                    model.data(
                        model.index(rowNumber, columnNumber),
                        QtCore.Qt.DisplayRole
                    )
                    for columnNumber in range(self.model.columnCount())
                ]
                writer.writerow(fields)


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
        # file=open(file,'r')
        # self.settingstext.setPlainText(file.read())
        self.table_loadCsv(self.settings_file,self.settings_model,['Channel','Name','Curve'])


    def open_curves(self):
        file = QFileDialog.getOpenFileName(self, " Open curves", '', filter="(*.txt) ")[0]
        self.curves_file = file
        file=open(file,'r')
        self.curvestext.setPlainText(file.read())

    def save_settings(self):
        self.table_writeCsv(self.settings_file,self.settings_model)
        self.statusBar().showMessage('Settings saved, restart aquisition to apply changes',3000)

    def save_curves(self):
        with open(self.curves_file, 'w') as yourFile:
            yourFile.write(str(self.curvestext.toPlainText()))
        self.statusBar().showMessage('Curves saved, restart aquisition to apply changes', 3000)



    def scan_instrumens(self,response=False):
        self.instrument_scanner_text.clear()
        if isinstance(response,bool):

            self.genericthread=generic_thread(self.daq.get_devices_identification)
            self.genericthread.start()
            self.genericthread.signalStatus.connect(self.scan_instrumens)
            self.instrument_scanner_text.appendPlainText('Scanning...')
        else:


            self.instrument_scanner_text.appendPlainText(response)


    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def onItemClicked(self, it, col):

        if self.focusedsub is not None:
            item_name = it.text(col)
            try:
                if not isinstance(self.variables[item_name][-1], str):
                    if it.checkState(0) == 2:
                        if item_name not in self.focusedsub.focused['Ploted'].keys():

                            if not bool(self.focusedsub.line_styles):
                                self.focusedsub.line_styles=self.line_colors.copy()

                            color=random.choice(self.focusedsub.line_styles)


                            a = PlotCurveItem(pen=pg.mkPen(color=color, width=1), name=item_name)



                            self.focusedsub.focused['Plot'].addItem(a)

                            self.focusedsub.focused['Ploted'][item_name] = a
                            self.focusedsub.line_styles.remove(color)
                            a.setData(self.variables['Time'], self.variables[item_name])
                            a.get_avg()


                    else:
                        if item_name in self.focusedsub.focused['Ploted'].keys():

                            item = self.focusedsub.focused['Ploted'][item_name]

                            self.focusedsub.line_styles.append(item.opts['pen'].color().getRgb())

                            self.focusedsub.focused['Plot'].removeItem(item)
                            del self.focusedsub.focused['Ploted'][item_name]

            except Exception as e:
                print(traceback.format_exc())
                print('Could not plot variable',e)

        #self.update_plots()

    # def link_plots(self):
    #     if self.linkaxis.isChecked():
    #         if len(self.mdi.subWindowList()) > 1:
    #             first=True
    #
    #             for subwin in self.mdi.subWindowList():
    #                 if first:
    #                     plot=subwin.plotlist[0]['Plot']
    #                     plot.vb.enableAutoRange()
    #                     first=False
    #                 else:
    #                     subwin.plotlist[0]['Plot'].setXLink(plot)
    #     else:
    #         if len(self.mdi.subWindowList()) > 1:
    #
    #
    #             for subwin in self.mdi.subWindowList():
    #
    #                     subwin.plotlist[0]['Plot'].setXLink(subwin.plotlist[0]['Plot'].vb)



    def update_plots(self):
        for subwin in self.mdi.subWindowList():
            for subplot in subwin.plotlist:
                # a=''
                for curve in subplot['Plot'].curves:
                    if isinstance(curve, PlotCurveItem):
                        item_name = curve.name()
                        if len(self.variables[item_name]) > 0:
                            curve.setData(self.variables['Time'], self.variables[item_name])
                            curve.get_avg()
                            # a+=item_name+''+str(self.variables[item_name][-1])


                for row in subplot['Plot'].legend.items:
                    name=row[1].text.split(' ')[0]
                    if len(self.variables[name])>0:

                        text="{} {}".format(name,self.variables[name][-1])
                        row[1].setText(text,size='10')






    def add_variables(self, variables):
        self.variable_widgets = []
        self.treevar.clear()

        watt = QTreeWidgetItem(self.treevar)

        watt.setText(0, 'Wattmeter')



        for var in variables:
            self.variables[var] = []
            if var[:2]=='WT':

                item = QTreeWidgetItem(watt)
                self.variable_widgets.append(item)
                item.setText(0, var)
                item.setText(1, '0')
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
            else:

                item = QTreeWidgetItem(self.treevar)
                self.variable_widgets.append(item)
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
       # self.link_plots()
        sub.show()

        self.reorgsubs()

    def close_plots(self):
        self.mdi.closeAllSubWindows()
        self.reorgsubs()

    def gradient_color(self,x):


        col=self.colormap(0.0067*x + 0.3333)


        return QColor(int(col[0]*255),int(col[1]*255),int(col[2]*255),int(col[3]*150))



    def update_all(self):
        self.daq_thread.variables.update(self.control_tab.get_variables(self.daq_thread.variables))

        if self.save_thread is not None:
            self.save_thread.variables = self.daq_thread.variables.copy()
            self.save_thread.save_point=True
            self.record_time.setText(time.strftime('%H:%M:%S', time.gmtime(self.save_thread.record_time)))

        variables = self.daq_thread.variables.copy()
        variables['Time'] -= self.delta_time
        variables['Time']=round(variables['Time'],4)





        if self.first_output:
            output = []
            for key, val in variables.items():
                output.append(key)
                self.variables[key] = [val]
            self.add_variables(output)
            self.first_output = False
            self.write_order = output

            a=self.daq_thread.daq.get_connected_devices()

            for i in a:
                self.log_text.appendPlainText(i)

                self.variables[key].append(val)
            for qitem in self.variable_widgets:


                var = variables[qitem.text(0)]
                qitem.setText(1, str(var))




        else:

            for key, val in variables.items():
                self.variables[key].append(val)
            for qitem in self.variable_widgets:

                var=variables[qitem.text(0)]
                qitem.setText(1, str(var))
             
                if qitem.text(0) in self.daq.temperature_vars:

                    qitem.setBackground(1,self.gradient_color(var))

        self.update_plots()

    def start_daq(self):
        try:
            self.load_config_files()
            self.daq.initialize(self.settings_file, self.curves_file,self.custom_file)
            self.daqstatus.setText('Running')
            self.first_output = True


            self.daq_thread = daq_thread(self.daq,self.checksavefile,int(self.daqinterval.text()))
            self.daq_thread.control_tab=self.control_tab
            self.daqinterval.setDisabled(True)
            self.daq_thread.start()
            self.daq_thread.signalStatus.connect(self.update_all)
            self.daq_thread.save_file=self.savefilepath.text()
            self.close_plots()


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
    a.add_variables(['Time','a'])
    a.variables['Time']=list(range(int(1000)))
    a.variables['a'] = list([random.randint(0,1000) for i in range(1000)])
    # a.variables['b'] =  list([random.randint(0,1000) for i in range(1000)])
    # a.variables['c'] = list([random.randint(0,1000) for i in range(1000)])

    a.update_plots()
    # a.variables['Time'] =[1,2,3,4,5,6,7,8,9]
    # a.variables['a'] =[1,2,3,4,5,6,7,8,9]

    a.show()

    sys.exit(app.exec_())


if __name__ == '__main__':  # T
    run_DataViewer()

"""
2020
Developed by Vitor Junges Liston
Courtesy of Polo Labs

"""
