
from functools import partial

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import numpy
from pyqtgraph.Point import Point
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('background', 'w')

pg.setConfigOption('antialias', True)  # Set to False if there is too much lag when dragging scene

class ColorAction(QtGui.QWidgetAction):
    colorSelected = QtCore.pyqtSignal(QtGui.QColor)

    def __init__(self, parent):

        QtGui.QWidgetAction.__init__(self, parent)
        self.color_id = {}
        widget = QtGui.QWidget(parent)
        layout = QtGui.QGridLayout(widget)

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        palette = self.palette()
        count = len(palette)
        rows = count // round(count ** .5)
        for row in range(rows):
            for column in range(count // rows):
                color = palette.pop()

                button = QtGui.QToolButton(widget)
                button.setAutoRaise(True)
                button.clicked.connect(partial(self.handleButton,color))

                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(color)
                button.setIcon(QtGui.QIcon(pixmap))
                layout.addWidget(button, row, column)
        self.setDefaultWidget(widget)

    def handleButton(self, color):
        self.parent().hide()
        self.colorSelected.emit(color)

    def palette(self):
        palette = []
        for g in range(4):
            for r in range(4):
                for b in range(3):
                    palette.append(QtGui.QColor(
                        r * 255 // 3, g * 255 // 3, b * 255 // 2))
        return palette

class PlotCurveItem(pg.PlotCurveItem):
    def __init__(self, *args, **kargs):
        self.ma = 0
        super(PlotCurveItem, self).__init__(*args, **kargs)
        self.avg = None
        self.menu = QtGui.QMenu()
        self.do_ma = False


        self.colorAction = ColorAction(self.menu)
        self.colorAction.colorSelected.connect(self.handleColorSelected)
        self.menu.addAction(self.colorAction)
        self.menu.addSeparator()

        fontColor = QtGui.QAction('Custom color', self)
        self.menu.addAction(fontColor)
        fontColor.triggered.connect(self.custom_color)



        self.sub_menu = QMenu("Moving average")

        a = QWidgetAction(self)


        self.spin=QSpinBox()
        self.spin.editingFinished.connect(self.moving_average)
        a.setDefaultWidget(self.spin)
        self.sub_menu.addAction(a)

        self.menu.addMenu(self.sub_menu)

        self.yData_ma=[]
        self.yData_unaltered=[]
    def moving_average(self):

        value=self.spin.value()


        if len(self.xData)>value:
            self.yData_ma = []
            self.ma = value
            if value>1:
                self.do_ma=True
                self.yData_ma=self.yData_unaltered[:value-1]+list(self._moving_average(self.yData_unaltered,value))
                self.setData_ma(self.xData, self.yData_ma)
            else:
                self.do_ma = False
                self.setData_ma(self.xData,self.yData_unaltered)

    def _moving_average(self,x, w):

        return np.convolve(x, np.ones(w), 'valid') / w

    def setData(self, *args, **kargs):
        if len(args) == 2:
            self.yData_unaltered = args[1]
            if self.do_ma:
                n=self.spin.value()
                if len(self.yData_unaltered)>n:

                    val=self.yData_ma[-1]+(self.yData_unaltered[-1]-self.yData_unaltered[-n])/n
                    self.yData_ma.append(val)
                else:
                    self.do_ma=False
                    self.spin.setValue(0)
                    self.ma=0

        self.setData_ma( *args, **kargs)


    def setData_ma(self, *args, **kargs):


        if self.ma > 1:



            super().setData(args[0], self.yData_ma)


        else:

            super().setData(*args, **kargs)

    def custom_color(self):
        color = QtGui.QColorDialog.getColor()
        color.getRgb()
        pen = pg.mkPen(color=color.getRgb(), width=1)
        self.setPen(pen)

    def handleColorSelected(self, color):

        pen = pg.mkPen(color=color.getRgb(), width=1)
        self.setPen(pen)




    def get_avg(self):
        try:
            self.avg = sum(self.yData) / len(self.yData)
            return self.avg
        except:
            return 0

    def mouseClickEvent(self, ev):
        pos=ev.pos()
        if ev.button() == QtCore.Qt.RightButton:


            if self.mouseShape().contains(pos):

                if self.raiseContextMenu(ev):
                    ev.accept()

    def raiseContextMenu(self, ev):
        menu = self.getContextMenus()

        # Let the scene add on to the end of our context menu
        # (this is optional)
        # menu = self.scene().addParentContextMenus(self, menu, ev)

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    # This method will be called when this item's _children_ want to raise
    # a context menu that includes their parents' menus.
    def getContextMenus(self, event=None):

        return self.menu


class PlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kargs):
        super(PlotWidget, self).__init__(*args, **kargs)
        self.plotItem.ctrlMenu = None  # get rid of 'Plot Options'
        self.getPlotItem().layout.setContentsMargins(1,5,5,1)
        self.scene().contextMenu = None  # get rid of 'Export'


    # On right-click, raise the context menu
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if self.raiseContextMenu(ev):
                ev.accept()

    def raiseContextMenu(self, ev):
        menu = self.getContextMenus()

        # Let the scene add on to the end of our context menu
        # (this is optional)
        # menu = self.scene().addParentContextMenus(self, menu, ev)

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    # This method will be called when this item's _children_ want to raise
    # a context menu that includes their parents' menus.
    def getContextMenus(self, event=None):

        return self.menu





class Qframe2(QFrame):
    signalStatus = pyqtSignal(QFrame)

    def __init__(self, parent=None):
        super(QFrame, self).__init__(parent)

    @pyqtSlot()
    def mousePressEvent(self, *args, **kwargs):
        self.signalStatus.emit(self)


class PlotWindow(QMdiSubWindow):
    def __init__(self, count, treevar, varlist, line_styles, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.lay = QWidget()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.fg = QGridLayout()
        self.fg.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Vertical)
        self.fg.addWidget(self.splitter)
        self.lay.setLayout(self.fg)
        self.setWidget(self.lay)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.focused = None
        self.count = count
        self.treevar = treevar
        self.varlist = varlist
        self.setWindowTitle('Plot ' + str(count))
        self.identifiers = [1, 2, 3, 4, 5, 6]
        self.plotlist = []
        self.line_styles =line_styles
        self.frame=None
        # , border=(0, 0, 0), fill=(255, 255, 255)

        self.plottooltip = pg.TextItem('None', color=(0, 0, 0),anchor=(0,1))

        # self.viewAll = QAction("sadsadsad", self.menu)

        self.menu = QtGui.QMenu()
        self.menu.setTitle('Options')

        tooltip = QtGui.QAction("Show information", self.menu)
        tooltip.setCheckable(True)
        tooltip.setChecked(True)
        tooltip.triggered.connect(self.toogle_tooltip)
        self.menu.addAction(tooltip)
        self.menu.tooltip = tooltip

        scale = QtGui.QAction("Autoscale", self.menu)
        scale.triggered.connect(self.toogle_scale)
        self.menu.addAction(scale)
        self.menu.scale = scale

        scalex = QtGui.QAction("Autoscale x", self.menu)
        scalex.triggered.connect(self.toogle_scalex)
        self.menu.addAction(scalex)
        self.menu.scalex = scalex

        scaley = QtGui.QAction("Autoscale y", self.menu)
        scaley.triggered.connect(self.toogle_scaley)
        self.menu.addAction(scaley)
        self.menu.scaley = scaley

        grid = QtGui.QAction("Grid", self.menu)
        grid.setCheckable(True)
        grid.setChecked(False)
        grid.triggered.connect(self.toogle_grid)
        self.menu.addAction(grid)
        self.menu.grid = grid

        self.show_tooltip = True
        self.show_hline = False





        self.add_subplot()


    def toogle_grid(self):
        if self.menu.grid.isChecked():
            for i in self.plotlist:
                i['Plot'].showGrid(True, True, 0.3)
        else:
            for i in self.plotlist:
                i['Plot'].showGrid(False, False, 0.3)

    def toogle_scalex(self):

        self.focused['Plot'].vb.enableAutoRange('x')
    def toogle_scale(self):

        self.focused['Plot'].vb.enableAutoRange()

    def toogle_scaley(self):

        self.focused['Plot'].vb.enableAutoRange('y')

    def add_subplot(self):
        frame = Qframe2()
        self.frame=frame
        frame.signalStatus.connect(self.setfocused)
        frame.setStyleSheet("""
                        QFrame {

                            background-color: rgb(255, 255, 255);
                            }
                        """)
        plot = PlotWidget()

        plot.setMouseTracking(True)
        plot.scene().sigMouseMoved.connect(partial(self.tool_tip, plot.getPlotItem()))

        plot.addLegend(offset=(1, 1))


        lay = QVBoxLayout()
        lay.addWidget(plot)

        frame.setLayout(lay)
        self.plotlist.append({'Widget':plot,'Plot': plot.getPlotItem(), 'Frame': frame, 'Ploted': {}})

        self.splitter.addWidget(frame)

        # self.fg.setRowStretch(self.fg.rowCount() - 1, 2)
        plot.plotItem.vb.menu = self.menu

        self.setfocused()
        self.focused = self.plotlist[0]
    def setfocused(self):

        item=self.plotlist[0]


        if bool(item['Ploted']):
            for toplevel in range(self.treevar.topLevelItemCount()):

                qitem = self.treevar.topLevelItem(toplevel)
                item_name = qitem.text(0)

                if item_name in item['Ploted'].keys():
                    qitem.setCheckState(0, Qt.Checked)
                else:
                    qitem.setCheckState(0, Qt.Unchecked)


        else:
            for toplevel in range(self.treevar.topLevelItemCount()):
                qitem = self.treevar.topLevelItem(toplevel)
                qitem.setCheckState(0, Qt.Unchecked)

    def tool_tip(self, plot, evt):
        if self.show_tooltip:
            mousePoint1 = plot.mapToView(evt)
            show = False
            for item in plot.curves:
                corrected = QtCore.QPointF(mousePoint1.x(), mousePoint1.y())

                if item.mouseShape().contains(corrected):
                    ind = (np.abs(item.xData - mousePoint1.x()).argmin())-1
                    y = item.yData[ind] + (mousePoint1.x() - item.xData[ind]) * (item.yData[ind + 1] - item.yData[ind]) / (item.xData[ind + 1] - item.xData[ind])

                    show = True
                    self.plottooltip.setText( ' '+item.name()+' '+ str(round(y, 2)) + '\n Avg ' + str(round(item.get_avg(), 2)) + '\n X ' + str(round(item.xData[ind - 1], 2)))


                    self.plottooltip.setPos(mousePoint1.x(), mousePoint1.y())


                    if self.plottooltip not in plot.items:
                        plot.addItem(self.plottooltip, ignoreBounds=True)

            if show == False:
                plot.removeItem(self.plottooltip)
        else:
            plot.removeItem(self.plottooltip)

    def toogle_tooltip(self):
        if self.menu.tooltip.isChecked():
            self.show_tooltip = True
        else:
            self.show_tooltip = False
