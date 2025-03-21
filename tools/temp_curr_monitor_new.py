# TO DO:
# - Check if ramp up/down and ramp voltage DC functions are compatible with main
# - Integrate them in main
# - Repeat for HV
# - Complete all the functions related to widgets

# - Test the UI in lab !!!!!!



import sys
import serial
import time
import random
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from datetime import datetime
from queue import Queue,Empty


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread,pyqtSignal,QTimer
from PyQt5.QtWidgets import QVBoxLayout,QWidget,QTabWidget,QLabel,QHBoxLayout,QComboBox, QPushButton, QSpinBox, QDoubleSpinBox, QGridLayout

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pyvisa as visa
import pymeasure.instruments.keithley as kit


class GetData(QtCore.QObject):
    """
    Subclass of QtCore.QObject, used for defining the main thread of program.
    """
    # How we expect our signal (13 floats)
    dataChanged = pyqtSignal(float, float, float, float, float, float, float, float,float,float,float,float,float)

    def __init__(self, queue, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.queue = queue

        # Data file path
        directory = "/home/labb2/ardu_dew_point/data/" # directory name << CHANGE WHEN NEEDED
        actual_time = f"{datetime.now()}"
        wrd = actual_time.split()
        wrd2 = wrd[1].split(":")
        wrd1 = wrd[0].split("-")
        dat = "".join(wrd1)
        tim = "".join(wrd2[:-1])
        ff = "-".join([dat,tim])
        file = "time-and-dew-point-{0}.dat".format(ff)
        self.filename = directory+file # file name << CHANGE WHEN NEEDED
        self.output_data_file = open(self.filename,"w")

        # Initialization of the serial port for communication with Arduino
        self.Arduino = serial.Serial("/dev/ttyUSB0",115200, timeout=0.01) # open the serial port << CHANGE WHEN NEEDED

        # INSERT THE CORRECT LINKS FOR THE KEITHLEYS
        # Initialization of the Keithleys for current measuring
        # self.keithley1 = kit.Keithley2450("TCPIP0::169.254.91.1::inst0::INSTR")
        # self.keithley2 = kit.Keithley2450("TCPIP0::169.254.91.2::inst0::INSTR")
        # self.keithley3 = kit.Keithley2450("TCPIP0::169.254.91.3::inst0::INSTR")
        self.rm,self.keithley1,self.keithley2,self.keithley3 = self.configure_keithleys()

        # self.keithley1 = self.rm.open_resource("TCPIP0::169.254.91.1::inst0::INSTR")
        # self.keithley2 = self.rm.open_resource("TCPIP0::169.254.91.2::inst0::INSTR")
        # self.keithley3 = self.rm.open_resource("TCPIP0::169.254.91.3::inst0::INSTR")


        # IF THE CURRENTS' PART DOESN'T WORK: TRY WITH THE COMMANDS OF THE RAMP UP

        time.sleep(2) # wait 2 seconds


    def __del__(self):  # part of the standard format of a QThread
        self.wait()

    def run(self):  # also a required QThread function, the working part
        starttime = time.time() # starting time
        self.active = True # flag for exit procedure management
        self.currents = True # flag for currents measuring management
        last_ihv = 0
        last_ipwell = 0
        last_ipsub = 0
        while self.active:
            try:

                if self.Arduino.inWaiting() > 0: # Do not do anything if there are no characters to read
                    while True:
                        data = self.Arduino.readline().decode() # read data and decode
                        # print(repr(data))
                        if not data:
                            break
                        words = data.split()

                        if words[0] == "inizio:" and len(words) == 8: # CHANGE accordingly to Arduino code!!!
                            # Extract the data
                            ddpp = float(words[1]) # dew point
                            ttchip = float(words[2]) # T_NTC
                            ttcold = float(words[3]) # T_cold side
                            tthot = float(words[4]) # T_hot side
                            delta_hc = abs(float(words[5])) # T_hot - T_cold
                            delta_cc = float(words[6]) # T_NTC - T_cold
                            delta_dc = float(words[7]) # T_cold - dew point
                            delta_ch = ttchip-tthot # T_NTC - T_hot
                            delta_dh = tthot-ddpp #T_hot - dew point

                            tt = time.time()-starttime # extract the time

                            # self.data structure: time,dew point,T_NTC,T_Cold,T_hot,Delta_ColdNTC,Delta_DpNTC,Delta_NTCHot,Delta_DpHot,I_HV,I_pwell,I_psub

                            # self.data_set[0].append(tt)
                            # self.data_set[1].append(ddpp)
                            # self.data_set[2].append(ttchip)
                            # self.data_set[3].append(ttcold)
                            # self.data_set[4].append(tthot)
                            # self.data_set[5].append(delta_hc)
                            # self.data_set[6].append(delta_cc)
                            # self.data_set[7].append(delta_dc)
                            # self.data_set[8].append(delta_ch)
                            # self.data_set[9].append(delta_dh)

                            # Currents' part managed by the currents flag
                            if self.currents:
                                i_hv = self.measure_current(self.keithley3)*1000000 # I_HV converted in uA
                                i_pwell = self.measure_current(self.keithley2)*1000 # I_pwell converted in mA
                                i_psub = self.measure_current(self.keithley1)*1000 # I_psub converted in mA

                                last_ipwell = i_pwell
                                last_ipsub = i_psub
                                last_ihv = i_hv
                                # self.data_set[10].append(i_hv)
                                # self.data_set[11].append(i_pwell)
                                # self.data_set[12].append(i_psub)
                            else:
                                i_hv = last_ihv
                                i_pwell = last_ipwell
                                i_psub = last_ipsub
                            # Signal with the new data
                            self.dataChanged.emit(tt,ddpp,ttchip,ttcold,tthot,delta_hc,delta_cc,delta_dc,delta_ch,delta_dh,i_hv,i_pwell,i_psub)
            except Empty:
                print("Empty")
                continue

    def measure_current(self,inst):
        inst.write("smu.measure.read()") # saving without append, it overwrites old values
        inst.write("print(smu.measure.read())")
        response = inst.read()
        response = float(response)
        return response

    def configure_keithleys(self):
        rm = visa.ResourceManager()
        keithley1 = rm.open_resource("TCPIP0::169.254.91.1::inst0::INSTR")
        keithley2 = rm.open_resource("TCPIP0::169.254.91.2::inst0::INSTR")
        keithley3 = rm.open_resource("TCPIP0::169.254.91.3::inst0::INSTR")

        keithley2.write("smu.source.func = smu.FUNC_DC_VOLTAGE") # Source function --> voltage
        keithley2.write("smu.source.range = 2.000000e+01")
        keithley2.write("smu.source.autorange = smu.OFF")
        keithley2.write("smu.measure.range = 1.000000e-02")
        keithley2.write("smu.measure.autorange = smu.OFF")
        keithley2.write("smu.source.ilimit.level = 3.000000e-03")
        keithley2.write("smu.source.autodelay = smu.OFF")
        keithley2.write("smu.source.protect.level = smu.PROTECT_20V")
        keithley2.write("smu.source.readback = smu.ON")
        keithley2.write("smu.measure.func = smu.FUNC_DC_CURRENT") # Measure function --> current

        keithley1.write("smu.source.func = smu.FUNC_DC_VOLTAGE") # Source function --> voltage
        keithley1.write("smu.source.range = 2.000000e+01")
        keithley1.write("smu.source.autorange = smu.OFF")
        keithley1.write("smu.measure.range = 1.000000e-02")
        keithley1.write("smu.measure.autorange = smu.OFF")
        keithley1.write("smu.source.ilimit.level = 3.000000e-03")
        keithley1.write("smu.source.autodelay = smu.OFF")
        keithley1.write("smu.source.protect.level = smu.PROTECT_20V")
        keithley1.write("smu.source.readback = smu.ON")
        keithley1.write("smu.measure.func = smu.FUNC_DC_CURRENT") # Measure function --> current

        keithley3.write("smu.source.func = smu.FUNC_DC_VOLTAGE") # Source function --> voltage
        keithley3.write("smu.source.range = 2.000000e+02")
        keithley3.write("smu.source.autorange = smu.OFF")
        keithley3.write("smu.measure.range = 1.000000e-03")
        keithley3.write("smu.measure.autorange = smu.OFF")
        keithley3.write("smu.source.ilimit.level = 3.000000e-04")
        keithley3.write("smu.source.autodelay = smu.OFF")
        keithley3.write("smu.source.protect.level = smu.PROTECT_40V")
        keithley3.write("smu.source.readback = smu.ON")
        keithley3.write("smu.measure.func = smu.FUNC_DC_CURRENT") # Measure function --> current

        return rm,keithley1,keithley2,keithley3


    def stop(self):
        """Method to safely stop the thread"""
        # Set the thread managing flag to False
        self.active = False
        # Close the output data file
        self.output_data_file.close()

class MplCanvas(FigureCanvas):
    """
    A subclass of FigureCanvas, required for creating widgets with plots.
    It has been optimized to work with more than 1 subplot but the class itself
    should work fine with just one of them.

    Parameters:
    - subs (int): default = 1, it is the number of subplots in the vertical diretion;
    - tit (str or list of str): default = None, it is the title or the list of
    the titles of the subplot(s);
    - xlab (str or list of str): default = None, it is the label or the list of
    the labels of the x axis of the subplot(s);
    - ylab (str or list of str): default = None, it is the label or the list of
    the labels of the y axis of the subplot(s);
    """

    def __init__(self, parent=None,subs = 1,tit=None,xlab=None,ylab=None):
        self.fig,self.axes = plt.subplots(subs,1,sharex=False)
        self.titles = tit
        self.xlabs = xlab
        self.ylabs = ylab
        # Styling of the subplot(s)
        if subs >1:
            for t,tt in enumerate(tit):
                self.axes[t].set_title(tt)
                self.axes[t].set_xlabel(xlab[t])
                self.axes[t].set_ylabel(ylab[t])
        elif subs == 1:
            self.axes.set_title(tit)
            self.axes.set_xlabel(xlab)
            self.axes.set_ylabel(ylab)
        # Preparing the lists with the infos about the plotted data and graphical charachteristics
        self.data_indx = [[] for i in range(subs)]
        self.line_colors = [[] for i in range(subs)]
        self.line_labels = [[] for i in range(subs)]
        super().__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):
    """
    A subclass of QtWidgets.QMainWindow, it is where the GUI is implemented.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Window and Tabs configuration
        self.setWindowTitle("C & T monitor")

        tabs = QTabWidget()

        temps = QWidget()
        currs = QWidget()
        ramps = QWidget()

        tabs.addTab(temps, "Temperatures")
        tabs.addTab(currs, "Currents")
        tabs.addTab(ramps, "Ramp up/down")

        # Number of points shown
        self.N_show = 150

        # Step of the ramp
        self.step = 0.5

        # Delay of the ramp
        self.delay = 0.1

        # Voltages selected
        self.HV = 0
        self.pwell = 0
        self.psub = 0

        # Index of the chip under test ["W8R4","W2R17","W8R6"]
        self.dut = 0

        # Layout of first tab (Temperatures)
        layout_temps = QVBoxLayout()

        # Last T_NTC widget
        self.last_T_NTC = QLabel(" T_NTC = --.-- *C ")
        font_NTC = self.last_T_NTC.font()
        font_NTC.setPointSize(20)
        self.last_T_NTC.setFont(font_NTC)

        # Operating mode widget(s)
        self.descr = QLabel("Select the monitoring mode: ")
        font_descr = self.descr.font()
        font_descr.setPointSize(20)
        self.descr.setFont(font_descr)

        self.heat_or_cool = QComboBox()
        self.heat_or_cool.addItems(["Cooling Mode","Heating Mode"])
        font_hc = self.heat_or_cool.font()
        font_hc.setPointSize(20)
        self.heat_or_cool.setFont(font_hc)
        self.heat_or_cool.currentIndexChanged.connect(self.index_changed)

        # Configuration of the plots
        labs_temp = [["Temperatures","Temperature Deltas","Temperature Deltas"],["T [*C]","Delta T [*C]","Delta T [*C]"],["Time [s]","Time [s]","Time [s]"]]
        self.temp_plot = MplCanvas(self,tit=labs_temp[0],ylab=labs_temp[1],xlab=labs_temp[2],subs=3)
        self.toolbar_temp = NavigationToolbar(self.temp_plot, self)
        self.temp_plot.data_indx[0].append(1)
        self.temp_plot.data_indx[0].append(2)
        self.temp_plot.data_indx[0].append(3)
        self.temp_plot.data_indx[0].append(4)
        self.temp_plot.line_colors[0].append("r")
        self.temp_plot.line_colors[0].append("b")
        self.temp_plot.line_colors[0].append("cyan")
        self.temp_plot.line_colors[0].append("green")
        self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_cold side Peltier","T_hot  side Peltier"]

        self.temp_plot.data_indx[1].append(7)
        self.temp_plot.line_colors[1].append("r")
        self.temp_plot.line_labels[1] = ["T_cold-Dew point"]

        self.temp_plot.data_indx[2].append(5)
        self.temp_plot.data_indx[2].append(6)
        self.temp_plot.line_colors[2].append("r")
        self.temp_plot.line_colors[2].append("b")
        self.temp_plot.line_labels[2] = ["|T_hot-T_cold|","T_NTC-T_cold"]
        self.temp_plot.fig.tight_layout()

        # Number of points shown selector
        self.num_label = QLabel(" Select number of points shown (4s per point): ")
        font_nlabel = self.num_label.font()
        font_nlabel.setPointSize(15)
        self.num_label.setFont(font_nlabel)

        self.num_to_show = QSpinBox()
        self.num_to_show.setMinimum(0)
        self.num_to_show.setMaximum(1000)
        self.num_to_show.setSingleStep(10)
        self.num_to_show.setValue(self.N_show)
        self.num_to_show.valueChanged.connect(self.num_changed)
        font_nshow = self.num_to_show.font()
        font_nshow.setPointSize(15)
        self.num_to_show.setFont(font_nshow)

        # Layout construction
        layout_mode = QHBoxLayout()
        layout_mode.addWidget(self.last_T_NTC)
        layout_mode.addWidget(self.descr)
        layout_mode.addWidget(self.heat_or_cool)
        layout_temps.addLayout(layout_mode)

        layout_plots = QHBoxLayout()
        layout_plots.addWidget(self.toolbar_temp)
        layout_plots.addWidget(self.num_label)
        layout_plots.addWidget(self.num_to_show)
        layout_temps.addLayout(layout_plots)

        self.temp_plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout_temps.addWidget(self.temp_plot)

        tabs.setTabText(0, "Temperatures")
        temps.setLayout(layout_temps)

        # Layout of second tab (Currents)
        layout_currs = QVBoxLayout()
        layout_meass = QHBoxLayout()

        # Configuration of the plots
        labs_currs = [["I_HV","I_DC"],["I [uA]","I [mA]"],["Time [s]","Time [s]"]]
        self.curr_plot = MplCanvas(self,tit=labs_currs[0],ylab=labs_currs[1],xlab=labs_currs[2],subs=2)
        self.curr_plot.data_indx[0].append(10)
        self.curr_plot.line_colors[0].append("r")
        self.curr_plot.line_labels[0] = ["I_HV"]

        self.curr_plot.data_indx[1].append(11)
        self.curr_plot.data_indx[1].append(12)
        self.curr_plot.line_colors[1].append("green")
        self.curr_plot.line_colors[1].append("b")
        self.curr_plot.line_labels[1] = ["I_pwell","I_psub"]
        self.curr_plot.fig.tight_layout()

        # Stop Acquisition Button configuration
        self.stop_cur = QPushButton("Stop Acquisition")
        self.stop_cur.setCheckable(False)
        self.stop_cur.clicked.connect(self.stop_acq)
        self.stop_cur.setMaximumSize(300,70)
        font_cur = self.stop_cur.font()
        font_cur.setPointSize(20)
        self.stop_cur.setFont(font_cur)

        # Stopped acquisition warning configuration
        self.warning_currs = QLabel(" If the values are red they are not updated. ")
        font_war = self.warning_currs.font()
        font_war.setPointSize(20)
        self.warning_currs.setFont(font_war)
        self.warning_currs.setAlignment(QtCore.Qt.AlignRight)

        # Last currents widgets configuration
        self.last_IHV = QLabel(" I_HV = 0.000 uA  ")
        font_HV = self.last_IHV.font()
        font_HV.setPointSize(30)
        self.last_IHV.setFont(font_HV)
        self.last_Ipwell = QLabel("I_pwell = 0.000 mA  ")
        font_pwell = self.last_Ipwell.font()
        font_pwell.setPointSize(30)
        self.last_Ipwell.setFont(font_pwell)
        self.last_Ipsub = QLabel("I_psub = 0.000 mA ")
        font_psub = self.last_Ipsub.font()
        font_psub.setPointSize(30)
        self.last_Ipsub.setFont(font_psub)

        # Layout(s) construction
        layout_meass.addWidget(self.last_IHV)
        layout_meass.addWidget(self.last_Ipwell)
        layout_meass.addWidget(self.last_Ipsub)

        layout_stop_curs = QHBoxLayout()
        layout_stop_curs.addWidget(self.stop_cur)
        layout_stop_curs.addWidget(self.warning_currs)
        layout_currs.addLayout(layout_stop_curs)
        layout_currs.addLayout(layout_meass)

        self.toolbar_currs = NavigationToolbar(self.curr_plot, self)
        self.curr_plot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout_currs.addWidget(self.toolbar_currs)
        layout_currs.addWidget(self.curr_plot)

        tabs.setTabText(1, "Currents")

        currs.setLayout(layout_currs)

        # Layout of third tab (Ramps)
        layout_ramps = QVBoxLayout()
        layout_tensions = QHBoxLayout()

        self.start_ramp = QPushButton("Start Ramp")
        self.start_ramp.setCheckable(False)
        self.start_ramp.clicked.connect(self.start_ramps)
        self.start_ramp.setMaximumSize(300,70)
        font_ramp = self.start_ramp.font()
        font_ramp.setPointSize(20)
        self.start_ramp.setFont(font_ramp)

        self.lab_HV = QLabel(" HV =  ")
        font_lHV = self.lab_HV.font()
        font_lHV.setPointSize(30)
        self.lab_HV.setFont(font_lHV)

        self.ramp_HV = QSpinBox()
        self.ramp_HV.setMinimum(0)
        self.ramp_HV.setMaximum(30)
        self.ramp_HV.setSingleStep(1)
        self.ramp_HV.setValue(self.HV)
        self.ramp_HV.setMaximumSize(200,70)
        self.ramp_HV.valueChanged.connect(self.volt_changed)
        font_rHV = self.ramp_HV.font()
        font_rHV.setPointSize(30)
        self.ramp_HV.setFont(font_rHV)

        self.lab_pwell = QLabel(" Pwell =  ")
        font_lpwell = self.lab_pwell.font()
        font_lpwell.setPointSize(30)
        self.lab_pwell.setFont(font_lpwell)

        self.ramp_pwell = QSpinBox()
        self.ramp_pwell.setMinimum(0)
        self.ramp_pwell.setMaximum(6)
        self.ramp_pwell.setSingleStep(1)
        self.ramp_pwell.setValue(self.pwell)
        self.ramp_pwell.setMaximumSize(200,70)
        self.ramp_pwell.valueChanged.connect(self.pwell_changed)
        font_rpwell = self.ramp_pwell.font()
        font_rpwell.setPointSize(30)
        self.ramp_pwell.setFont(font_rpwell)

        self.lab_psub = QLabel(" Abs(Psub-Pwell) =  ")
        font_lpsub = self.lab_psub.font()
        font_lpsub.setPointSize(30)
        self.lab_psub.setFont(font_lpsub)

        self.ramp_psub = QSpinBox()
        self.ramp_psub.setMinimum(0)
        self.ramp_psub.setMaximum(14)
        self.ramp_psub.setSingleStep(1)
        self.ramp_psub.setValue(self.psub)
        self.ramp_psub.setMaximumSize(200,70)
        self.ramp_psub.valueChanged.connect(self.psub_changed)
        font_rpsub = self.ramp_psub.font()
        font_rpsub.setPointSize(30)
        self.ramp_psub.setFont(font_rpsub)

        self.chip_sel = QLabel(" Select the chip under test:  ")
        font_ch_sel = self.chip_sel.font()
        font_ch_sel.setPointSize(30)
        self.chip_sel.setFont(font_ch_sel)

        self.chips = QComboBox()
        self.chips.addItems(["W8R4","W2R17","W8R6"])
        self.chips.setMaximumSize(200,70)
        font_ch = self.chips.font()
        font_ch.setPointSize(30)
        self.chips.setFont(font_ch)
        self.chips.currentIndexChanged.connect(self.chip_changed)

        self.lab_step = QLabel(" Step =  ")
        font_step = self.lab_step.font()
        font_step.setPointSize(30)
        self.lab_step.setFont(font_step)

        self.step_sel = QDoubleSpinBox()
        self.step_sel.setMinimum(0)
        self.step_sel.setMaximum(1)
        self.step_sel.setSingleStep(0.1)
        self.step_sel.setValue(self.step)
        self.step_sel.setMaximumSize(200,70)
        self.step_sel.valueChanged.connect(self.step_changed)
        font_step_sel = self.step_sel.font()
        font_step_sel.setPointSize(30)
        self.step_sel.setFont(font_step_sel)

        self.lab_delay = QLabel(" Delay =  ")
        font_delay = self.lab_delay.font()
        font_delay.setPointSize(30)
        self.lab_delay.setFont(font_delay)

        self.delay_sel = QDoubleSpinBox()
        self.delay_sel.setMinimum(0)
        self.delay_sel.setMaximum(1)
        self.delay_sel.setSingleStep(0.1)
        self.delay_sel.setValue(self.delay)
        self.delay_sel.setMaximumSize(200,70)
        self.delay_sel.valueChanged.connect(self.delay_changed)
        font_delay_sel = self.delay_sel.font()
        font_delay_sel.setPointSize(30)
        self.delay_sel.setFont(font_delay_sel)

        self.lab_status = QLabel("  ")
        font_status = self.lab_status.font()
        font_status.setPointSize(30)
        self.lab_status.setFont(font_status)

        self.ramp_HV.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.ramp_pwell.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.ramp_psub.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.delay_sel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.step_sel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.chip_sel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.chips.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.lab_status.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.start_ramp.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)


        # Layout(s) construction
        layout_ramps = QVBoxLayout()

        # Creazione del GridLayout
        grid_layout = QGridLayout()

        # Aggiunta dei controlli per HV, Pwell, Psub nella griglia
        grid_layout.addWidget(self.lab_HV, 0, 0)  # Prima riga, prima colonna
        grid_layout.addWidget(self.ramp_HV, 0, 1)  # Prima riga, seconda colonna

        grid_layout.addWidget(self.lab_pwell, 1, 0)  # Seconda riga, prima colonna
        grid_layout.addWidget(self.ramp_pwell, 1, 1)  # Seconda riga, seconda colonna

        grid_layout.addWidget(self.lab_psub, 2, 0)  # Terza riga, prima colonna
        grid_layout.addWidget(self.ramp_psub, 2, 1)  # Terza riga, seconda colonna

        # Aggiungi spaziatura tra le righe
        grid_layout.setRowStretch(3, 1)  # Spazio extra dopo l'ultima riga
        grid_layout.setVerticalSpacing(50)  # Distanza verticale tra le righe

        # Aggiungi i controlli della modalità di selezione e pulsante start ramp
        layout_chips = QHBoxLayout()
        layout_chips.addWidget(self.start_ramp)
        layout_chips.addWidget(self.chip_sel)
        layout_chips.addWidget(self.chips)
        grid_layout.addLayout(layout_chips, 3, 0, 1, 2)  # Aggiungi l'HBox alla quarta riga, coprendo 2 colonne

        # Layout per step e delay
        layout_del_step = QHBoxLayout()
        layout_del_step.addWidget(self.lab_step)
        layout_del_step.addWidget(self.step_sel)
        layout_del_step.addWidget(self.lab_delay)
        layout_del_step.addWidget(self.delay_sel)
        grid_layout.addLayout(layout_del_step, 4, 0, 1, 2)  # Aggiungi l'HBox alla quinta riga

        # Aggiungi lo status
        grid_layout.addWidget(self.lab_status, 5, 0, 1, 2)  # Status in fondo

        # Configurazioni finali del layout
        layout_ramps.addLayout(grid_layout)

        tabs.setTabText(2, "Ramp up/down")

        ramps.setLayout(layout_ramps)


        # Utility lists
        self.plots = [self.temp_plot,self.curr_plot]
        self.labels = [["Temperatures","Time [s]","T [*C]"],["Temperature Deltas","Time [s]","Delta T [*C]"],["Temperature Deltas","Time [s]","Delta T [*C]"],["I_HV","Time [s]","I [uA]"],["I_DC","Time [s]","I [mA]"]]

        # Data list initialization
        self.data = []
        self.data_full = []
        for i in range(13):
            self.data.append([])
            self.data_full.append([])

        # Thread initialization
        self.queue = Queue()
        self.thread = QtCore.QThread(self)
        self.receiver = GetData(self.queue)
        self.receiver.moveToThread(self.thread)
        self.thread.started.connect(self.receiver.run)
        self.receiver.dataChanged.connect(self.onDataChanged)

        self.thread.start()

        self.setCentralWidget(tabs)

        self.show()

    def closeEvent(self, event):
        """
        Method called at the closing of the window.
        We stop the thread by setting the flag to False, quitting the
        thread and waiting for it to actually finish.
        """
        print('Closing the application...')
        self.receiver.stop()  # Sets the active flag to False
        self.thread.quit()
        self.thread.wait()

    def num_changed(self,i):
        self.N_show = i

    def volt_changed(self,i):
        self.HV = i

    def pwell_changed(self,i):
        self.pwell = i

    def psub_changed(self,i):
        self.psub = i

    def step_changed(self,i):
        self.step = i

    def delay_changed(self,i):
        self.delay = i

    def chip_changed(self,i):
        self.dut = i

    def index_changed(self,i):
        """
        Method called when the operating mode is changed.
        We change the temperature plots.
        """
        # Cooling
        if i == 0:
            self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_cold side Peltier","T_hot  side Peltier"]
            self.temp_plot.data_indx[1][0] = 7
            self.temp_plot.data_indx[2][1] = 6

        # Heating
        elif i == 1:
            self.temp_plot.line_labels[0] = ["Dew point","T_NTC chip","T_hot  side Peltier","T_cold side Peltier"]
            self.temp_plot.data_indx[1][0] = 9
            self.temp_plot.data_indx[2][1] = 8

    def ramp_up(self,resource_name,set_voltage,voltage,step,delay,name):
        """"
            Ramps the voltage of the pwell source meter either up or down.

        Parameters:
            resource_name_pwell (str): VISA resource name.
            resource_name_psub (str): VISA resource name.
            voltage_pwell (float): Ending pwell voltage.
            voltage_psub (float): Ending psub voltage.
            step (float): Step increment for voltage change.
            delay (float): Delay between each step.
            name (string): Name of the voltage.
        """
        print(f"Ramping {name} up to ", voltage,"V")
        for volt in np.arange(set_voltage, voltage + step, step):
            if volt > voltage:
                break
            resource_name.write("smu.source.level = "+str(volt))
            time.sleep(delay)
            resource_name.write("smu.measure.read()") # saving without append, it overwrites old values
            resource_name.write("print(smu.measure.read())")
            response = resource_name.read()
            response = float(response)*1000 # Convert in mA
            print(f"Voltage: {volt:.1f} V, current: {response:.2e} mA", end="\r")
            print()
            time.sleep(0.1)

    def ramp_down(self,resource_name,set_voltage,voltage,step,delay,name):
        """"
            Ramps the voltage of the pwell source meter either up or down.

        Parameters:
            resource_name_pwell (str): VISA resource name.
            resource_name_psub (str): VISA resource name.
            voltage_pwell (float): Ending pwell voltage.
            voltage_psub (float): Ending psub voltage.
            step (float): Step increment for voltage change.
            delay (float): Delay between each step.
            name (string): Name of the voltage.
        """
        print(f"Ramping {name} down to ", voltage,"V")
        for volt in np.arange(set_voltage, voltage-step, -step):
            if voltage!=0:
                if volt < voltage:
                    break
            resource_name.write("smu.source.level = "+str(volt))
            time.sleep(delay)
            resource_name.write("smu.measure.read()") # saving without append, it overwrites old values
            resource_name.write("print(smu.measure.read())")
            response = resource_name.read()
            response = float(response)*1000 # Convert in mA
            print(f"Voltage: {volt:.1f} V, current: {response:.2e} mA", end="\r")
            print()
            time.sleep(0.1)




    def ramp_voltage_DC(self,inst_pwell,inst_psub, voltage_pwell, voltage_psub, step, delay,tmp_meas):
        """
        Ramps the voltage of a source meter either up or down.

        Parameters:
            resource_name_pwell (str): VISA resource name.
            resource_name_psub (str): VISA resource name.
            voltage_pwell (float): Ending pwell voltage.
            voltage_psub (float): Ending psub voltage.
            step (float): Step increment for voltage change.
            delay (float): Delay between each step.
        """
        # # Configure the smu for pwell
        # inst_pwell = conf_smu(resource_name_pwell)
        #
        # # Configure the smu for psub
        # inst_psub = conf_smu(resource_name_psub)


        # Safety: if pwell is lower than -6 V (set OVERPROTECTION voltage) or has a positive value it stops the program
        if voltage_psub < 0.:
            print("WARNING: provide the absolute value of psub!! ")
            self.lab_status.setText(" WARNING: provide the absolute value of psub!! ")
            self.ramp_psub.setValue(int(tmp_meas[2]))
            self.ramp_pwell.setValue(int(tmp_meas[1]))

            return


        if voltage_pwell < 0.:
            print("WARNING: provide the absolute value of pwell!! ")
            self.lab_status.setText(" WARNING: provide the absolute value of pwell!! ")
            self.ramp_pwell.setValue(int(tmp_meas[1]))
            self.ramp_psub.setValue(int(tmp_meas[2]))

            return


        if voltage_pwell<6:
            if voltage_psub !=0:
                print("WARNING: if pwell is <6 abs(psub-pwell) NEEDS TO be 0! ")
                self.lab_status.setText(" WARNING: if pwell is <6 abs(psub-pwell) NEEDS TO be 0! ")
                self.ramp_psub.setValue(int(tmp_meas[2]))
                self.ramp_pwell.setValue(int(tmp_meas[1]))

                return

        elif voltage_pwell == 6:
            #["W8R4","W2R17","W8R6"]
            if self.dut == 0:
                if voltage_psub > 4:
                    print("WARNING: abs(psub-pwell) CANNOT be >4 (W8R04)! ")
                    self.lab_status.setText(" WARNING: abs(psub-pwell) CANNOT be >4 (W8R04)! ")
                    self.ramp_psub.setValue(int(tmp_meas[2]))
                    self.ramp_pwell.setValue(int(tmp_meas[1]))

                    return

            elif self.dut == 1:
                if voltage_psub > 9:
                    print("WARNING: abs(psub-pwell) CANNOT be >9 (W2R17)! ")
                    self.lab_status.setText(" WARNING: abs(psub-pwell) CANNOT be >9 (W2R17)! ")
                    self.ramp_psub.setValue(int(tmp_meas[2]))
                    self.ramp_pwell.setValue(int(tmp_meas[1]))

                    return

            elif self.dut == 2:
                if voltage_psub > 14:
                    print("WARNING: abs(psub-pwell) CANNOT be >14 (W8R6)! ")
                    self.lab_status.setText(" WARNING: abs(psub-pwell) CANNOT be >14 (W8R6)! ")
                    self.ramp_psub.setValue(int(tmp_meas[2]))
                    self.ramp_pwell.setValue(int(tmp_meas[1]))

                    return

        elif voltage_pwell > 6:
            print("WARNING: pwell CANNOT be >6!! ")
            self.lab_status.setText(" WARNING: pwell CANNOT be >6!! ")
            self.ramp_pwell.setValue(int(tmp_meas[1]))
            self.ramp_psub.setValue(int(tmp_meas[2]))
            return



        # Change sign to the voltage values
        voltage_pwell = - voltage_pwell
        voltage_psub = - voltage_psub

        pwell_name = "pwell"
        psub_name = "psub"
        # Create buffer for saving data in smu
        # inst.write("testDatabuffer = buffer.make(20000)")

        # Check set voltage before ramping up/down
        inst_pwell.write("voltage_set = smu.source.level")
        inst_pwell.write("print(voltage_set)")
        responsev_pwell = inst_pwell.read()

        print("Current pwell voltage set:", responsev_pwell,"V")
        set_voltage_pwell = float(responsev_pwell)

        inst_psub.write("voltage_set = smu.source.level")
        inst_psub.write("print(voltage_set)")
        responsev_psub = inst_psub.read()

        print("Current psub voltage set:", responsev_psub,"V")
        set_voltage_psub = float(responsev_psub)


        # # Do nothing if the voltage is already set at given value
        # if set_voltage_pwell == voltage_pwell:
        #     print("pwell Voltage is already set to ",voltage_pwell, " V")
        #     sys.exit(0)

        # Check if the HV is higher or lower than the set value and the ramp up or down. For each step of ramp up/down it prints set voltage and measured current
        if set_voltage_pwell > voltage_pwell:
            self.ramp_down(inst_pwell,set_voltage_pwell,voltage_pwell,step,delay,pwell_name)
            time.sleep(0.2)
            print(" ")
            self.ramp_down(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)

        elif set_voltage_pwell < voltage_pwell:
            self.ramp_up(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)
            time.sleep(0.2)
            print(" ")

            self.ramp_up(inst_pwell,set_voltage_pwell,voltage_pwell,step,delay,pwell_name)

        else:
            if set_voltage_psub > voltage_psub:
                self.ramp_down(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)

            else:
                self.ramp_up(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)



        print(" ")

        print("Voltage ramp completed.")
        self.lab_status.setText(" Voltage ramp completed. ")
        inst_pwell.write("voltage_set = smu.source.level")
        inst_pwell.write("print(voltage_set)")
        responsev_pwell_last = inst_pwell.read()
        responsev_pwell_last = float(responsev_pwell_last)

        inst_pwell.write("smu.measure.read()")
        inst_pwell.write("print(smu.measure.read())")
        response_well_last = inst_pwell.read()
        response_well_last= float(response_well_last)*1000 # Convert in mA

        inst_psub.write("voltage_set = smu.source.level")
        inst_psub.write("print(voltage_set)")
        responsev_psub_last = inst_psub.read()
        responsev_psub_last = float(responsev_psub_last)

        inst_psub.write("smu.measure.read()")
        inst_psub.write("print(smu.measure.read())")
        response_sub_last = inst_psub.read()
        response_sub_last= float(response_sub_last)*1000 # Convert in mA


        # inst_psub.write("voltage_set = smu.source.level")
        # inst_psub.write("print(voltage_set)")
        # responsev_psub_end = inst_psub.read()
        print("Current values:")
        print(f"Pwell: Voltage: {responsev_pwell_last:.1f} V, current: {response_well_last:.2e} mA")
        print(f"abs(Psub-Pwell): Voltage: {responsev_psub_last:.1f} V, current: {response_sub_last:.2e} mA")

    def ramp_voltage_HV(self,inst, end_voltage, step, delay,tmp_meas):
        """
        Ramps the voltage of a source meter either up or down.

        Parameters:
            resource_name (str): VISA resource name.
            start_voltage (float): Starting voltage.
            end_voltage (float): Ending voltage.
            step (float): Step increment for voltage change.
            delay (float): Delay between each step.
            ramp_direction (str): 'up' for ramp up, 'down' for ramp down.
        """
        # # Configure the smu
        # inst = conf_smu(resource_name)

        # Safety: if HV is higher than 40V (set OVERPROTECTION voltage) or has a negative value it stops the program
        if abs(end_voltage)>30:
            print("WARNING: the HV set is higher than the Overprotection Voltage set!")
            self.lab_status.setText(" WARNING: the HV set is higher than the Overprotection Voltage set! ")
            self.ramp_HV.setValue(int(tmp_meas[0]))
            return


        if end_voltage < 0.:
            print("HV cannot be negative!! ")
            self.lab_status.setText(" HV cannot be negative!! ")
            self.ramp_HV.setValue(int(tmp_meas[0]))
            return

        # Create buffer for saving data in smu
        # inst.write("testDatabuffer = buffer.make(20000)")

        # Check set voltage before ramping up/down
        inst.write("voltage_set = smu.source.level")
        inst.write("print(voltage_set)")
        responsev = inst.read()
        print("Current voltage set:", responsev,"V")

        set_voltage = float(responsev)

        # Do nothing if the voltage is already set at given value
        if set_voltage == end_voltage:
            print("Voltage is already set to ",end_voltage)

        # Check if the HV is higher or lower than the set value and the ramp up or down. For each step of ramp up/down it prints set voltage and measured current
        if set_voltage > end_voltage:
            print("Ramping down to ", end_voltage,"V")
            for volt in np.arange(set_voltage, end_voltage-step, -step):
                if end_voltage!=0:
                    if volt < end_voltage:
                        break
                inst.write("smu.source.level = "+str(volt))
                time.sleep(delay)
                inst.write("smu.measure.read()") # saving without append, it overwrites old values
                inst.write("print(smu.measure.read())")
                response = inst.read()
                response = float(response)
                print(f"Voltage: {volt:.1f} V, current: {response:.2e} A", end="\r")
                print()
                time.sleep(0.1)
        else:
            print("Ramping up to ", end_voltage,"V")
            for volt in np.arange(set_voltage, end_voltage + step, step):
                if volt > end_voltage:
                    break
                inst.write("smu.source.level = "+str(volt))
                time.sleep(delay)
                inst.write("smu.measure.read()") # saving without append, it overwrites old values
                inst.write("print(smu.measure.read())")
                response = inst.read()
                response = float(response)
                print(f"Voltage: {volt:.1f} V, current: {response:.2e} A", end="\r")
                print()
                time.sleep(0.1)

        print("Voltage ramp completed.")
        self.lab_status.setText(" Voltage ramp completed.")



    def start_ramps(self):
            self.receiver.currents = False

            time.sleep(2)

            self.receiver.keithley2.write("voltage_set = smu.source.level")
            self.receiver.keithley2.write("print(voltage_set)")
            tmp_pwell = self.receiver.keithley2.read()
            self.receiver.keithley1.write("voltage_set = smu.source.level")
            self.receiver.keithley1.write("print(voltage_set)")
            tmp_psub = self.receiver.keithley1.read()
            self.receiver.keithley3.write("voltage_set = smu.source.level")
            self.receiver.keithley3.write("print(voltage_set)")
            tmp_HV = self.receiver.keithley3.read()
            tmp_meas = [int(tmp_HV),-int(tmp_pwell),-int(tmp_psub)]

            self.lab_status.setText(" Ramping... ")

            # Call the ramp voltage function
            if self.pwell == 0:
                if self.psub == 0:
                    self.lab_status.setText(" Starting ramp ")

                    self.ramp_voltage_DC(self.receiver.keithley2,self.receiver.keithley1, 0, 0, self.step, self.delay,tmp_meas)
                    time.sleep(0.5)

                    self.ramp_voltage_HV(self.receiver.keithley3, self.HV, self.step, self.delay,tmp_meas)
            else:
                if self.HV == 0:
                    self.lab_status.setText(" Starting ramp ")

                    self.ramp_voltage_HV(self.receiver.keithley3, 0, self.step, self.delay,tmp_meas)
                    time.sleep(0.5)
                    self.ramp_voltage_DC(self.receiver.keithley2,self.receiver.keithley1, self.pwell, self.psub, self.step, self.delay,tmp_meas)
                else:
                    print("Cannot power both the DCC and HVC parts!!")
                    self.lab_status.setText(" Cannot power both the DCC and HVC parts!! ")
                    self.ramp_HV.setValue(tmp_meas[0])
                    self.ramp_pwell.setValue(tmp_meas[1])
                    self.ramp_psub.setValue(tmp_meas[2])

            self.receiver.currents = True





    def stop_acq(self):
        """
        Method called when the Stop Acquisition Button is clicked.
        When the acquisition is stopped the button's label is changed to
        Restart Acquisition.
        """
        # Stopping
        if self.receiver.currents:
            self.receiver.currents = False
            self.stop_cur.setText("Restart Acquisition")
            self.receiver.rm.close()
            self.last_IHV.setStyleSheet('color: red')
            self.last_Ipsub.setStyleSheet('color: red')
            self.last_Ipwell.setStyleSheet('color: red')
            self.stop_cur.setEnabled(False)
            QTimer.singleShot(2000, lambda: self.stop_cur.setDisabled(False))


        # Restarting
        else:
            self.receiver.currents = True
            self.stop_cur.setText("Stop Acquisition")
            self.receiver.rm,self.receiver.keithley1,self.receiver.keithley2,self.receiver.keithley3 =self.receiver.configure_keithleys()
            self.last_IHV.setStyleSheet('color: black')
            self.last_Ipsub.setStyleSheet('color: black')
            self.last_Ipwell.setStyleSheet('color: black')
            self.stop_cur.setEnabled(False)
            QTimer.singleShot(2000, lambda: self.stop_cur.setDisabled(False))


    def onDataChanged(self,a,b,c,d,e,f,g,h,i,j,k,l,m):
        """
        Method called with the Data Changed signal of the Thread.
        It takes 13 floats as inputs and distributes them to the
        corresponding data sublist.
        It also writes on the output data file if the active flag
        is set to True.
        It then updates the plots and the labels widgets.
        """
        # Number of points shown
        N = min(self.N_show,len(self.data_full[0]))

        # Data distribution
        t = self.data_full[0][-N:]
        t.append(a)
        self.data_full[0].append(a)

        dp = self.data_full[1][-N:]
        dp.append(b)
        self.data_full[1].append(b)

        tchip= self.data_full[2][-N:]
        tchip.append(c)
        self.data_full[2].append(c)

        tcold = self.data_full[3][-N:]
        tcold.append(d)
        self.data_full[3].append(d)

        thot= self.data_full[4][-N:]
        thot.append(e)
        self.data_full[4].append(e)

        del_hc= self.data_full[5][-N:]
        del_hc.append(f)
        self.data_full[5].append(f)

        del_cc= self.data_full[6][-N:]
        del_cc.append(g)
        self.data_full[6].append(g)

        del_dc= self.data_full[7][-N:]
        del_dc.append(h)
        self.data_full[7].append(h)

        del_ch= self.data_full[8][-N:]
        del_ch.append(i)
        self.data_full[8].append(i)

        del_dh= self.data_full[9][-N:]
        del_dh.append(j)
        self.data_full[9].append(j)

        i_hv= self.data_full[10][-N:]
        i_hv.append(k)
        self.data_full[10].append(k)

        i_pwell= self.data_full[11][-N:]
        i_pwell.append(l)
        self.data_full[11].append(l)

        i_psub= self.data_full[12][-N:]
        i_psub.append(m)
        self.data_full[12].append(m)

        self.data[0] = t
        self.data[1] = dp
        self.data[2] = tchip
        self.data[3] = tcold
        self.data[4] = thot
        self.data[5] = del_hc
        self.data[6] = del_cc
        self.data[7] = del_dc
        self.data[8] = del_ch
        self.data[9] = del_dh
        self.data[10] = i_hv
        self.data[11] = i_pwell
        self.data[12] = i_psub

        # Writing on the output data file
        line = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11} {12}\n".format(a,b,c,d,e,f,g,h,i,j,k,l,m)
        if self.receiver.output_data_file.closed:
            print("Not saving data anymore: file closed")
        else:
            self.receiver.output_data_file.write(line)

        # Updating of the plots
        for i,pl in enumerate(self.plots):
            for j,ax in enumerate(pl.axes):
                ax.cla()  # Clear the canvas.
                ax.grid()
                for k, ind in enumerate(pl.data_indx[j]):
                    y_indx = ind
                    ax.plot(self.data[0], self.data[y_indx],color= pl.line_colors[j][k],label=pl.line_labels[j][k])
                ax.set_title(pl.titles[j])
                ax.set_xlabel(pl.xlabs[j])
                ax.set_ylabel(pl.ylabs[j])
                if i == 0:
                    if j == 1:
                        ax.hlines(5,min(t)-.5,max(t)+.5,colors="red",label="Min for Peltier (T_cold-dew point)",linestyles="dashed")
                ax.legend(loc = "upper left")
            pl.fig.tight_layout()
            pl.draw()

        # Updating of the temperature and currents labels
        t_ntc = " T_NTC = %.2f *C " % (self.data[2][-1])
        ihv = " I_HV = %.2f uA  " % (self.data[10][-1])
        ipwell = "I_pwell = %.4f mA  " % (self.data[11][-1])
        ipsub = "I_psub = %.4f mA " % (self.data[12][-1])
        self.last_T_NTC.setText(t_ntc)
        self.last_IHV.setText(ihv)
        self.last_Ipwell.setText(ipwell)
        self.last_Ipsub.setText(ipsub)

app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec_()
