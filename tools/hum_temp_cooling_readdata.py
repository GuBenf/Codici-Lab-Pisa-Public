# This script is used to interface with Arduino Uno used with the sketch hum_temp_cooling.ino
# The process is:
# 1. writing of a character on the serial line in order to start the acquisition;
# 2. reading of the data available on the serial port;

import sys
import serial
import time
import numpy
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime

directory = "/home/labb2/ardu_dew_point/data" # directory name << CHANGE WHEN NEEDED
actual_time = f"{datetime.now()}"
wrd = actual_time.split()
wrd2 = wrd[1].split(":")
wrd1 = wrd[0].split("-")
dat = "".join(wrd1)
tim = "".join(wrd2[:-1])
ff = "-".join([dat,tim])
file = "time-and-dew-point-{0}.dat".format(ff)
filename = directory+file # file name << CHANGE WHEN NEEDED

#hotorcold = input("Are you operating in Cooling (c) or Heating (h) mode? ")
if len(sys.argv) == 1:
	print("A parameter is needed! (h for Heating mode, c for Cooling mode)")
	aa = input("Heating or Cooling? ")
	sys.argv.append(aa)
hotorcold = sys.argv[1]
ok = False
while ok == False:
	if hotorcold != "c":
		if hotorcold != "h":
			print("NO! You must write c or h!")
			hotorcold = input("Heating or Cooling? ")
		else:
			ok = True
	else:
		ok = True

print('Please wait')


ard = serial.Serial("/dev/ttyUSB0",115200, timeout=0.01) # open the serial port << CHANGE WHEN NEEDED
time.sleep(2) # wait 2 seconds

print('Start Acquisition') # writes on the terminal

ard.write(b'G') # writes a character on the serial line (b stands for "bytes", ASCII character)
time.sleep(2) # wait another 2 seconds

# read data in a loop, every line on the terminal is read
N = 150 # number of readings shown (delay = 1000 is 1 s)
times = [] # times vector
dp = [] # dew points vector
starttime = time.time() # starting time

# NOTE: Nomenclature is the one used in the cooling mode
hum = [] # humidities vector
temp = [] # temperatures vector
t_chip = [] # chip temperatures vector
t_cold = [] # cold side temperatures vector
t_hot = [] # hot side temperatures vector
delta_t_hotncold = [] # hot-cold temperature deltas vector
delta_t_chipcold = [] # chip-cold temperature deltas vector
delta_t_dpcold = [] # cold-dew point temperature deltas vector
delta_t_chiphot = [] # chip-hot temperature deltas vector
delta_t_dphot = [] # hot-dew point temperature deltas vector

def animate(i,outputfile):
	global times, dp, t_chip, t_cold, t_hot, delta_t_hotncold, delta_t_chipcold, delta_t_dpcold, delta_t_chiphot, delta_t_dphot
	if ard.inWaiting() > 0: # Do not do anything if there are no characters to read
		while True:
			data = ard.readline().decode() # read data and decode
			# print(repr(data))
			if not data:
				break
			words = data.split()
			if outputfile.closed:
				outputfile = open(filename,"a")
			if words[0] == "inizio:" and len(words) == 8: # CHANGE accordingly to Arduino code!!!
				ddpp = float(words[1]) # extract the dew point
				ttchip = float(words[2])
				ttcold = float(words[3])
				tthot = float(words[4])
				delta_hc = abs(float(words[5]))
				delta_cc = float(words[6])
				delta_dc = float(words[7])
				delta_ch = ttchip-tthot
				delta_dh = tthot-ddpp
				tt = time.time()-starttime # extract the time
				times.append(tt) # append times to their vector
				dp.append(ddpp) # append dew points to their vector
				t_chip.append(ttchip)
				t_cold.append(ttcold)
				t_hot.append(tthot)
				delta_t_hotncold.append(delta_hc)
				delta_t_chipcold.append(delta_cc)
				delta_t_dpcold.append(delta_dc)
				delta_t_chiphot.append(delta_ch)
				delta_t_dphot.append(delta_dh)
				if len(times) > N:
					times = times[-N:]
					dp = dp[-N:]
					t_chip = t_chip[-N:]
					t_cold = t_cold[-N:]
					t_hot = t_hot[-N:]
					delta_t_hotncold = delta_t_hotncold[-N:]
					delta_t_chipcold = delta_t_chipcold[-N:]
					delta_t_dpcold = delta_t_dpcold[-N:]
					delta_t_chiphot = delta_t_chiphot[-N:]
					delta_t_dphot = delta_t_dphot[-N:]

				#n_points = min(N,len(dp))

				line = "{0} {1} {2} {3} {4} {5} {6} {7}\n".format(tt,ddpp,ttchip,ttcold,tthot,delta_hc,delta_cc,delta_dc)
				outputfile.write(line) # write data on file

		ax[0].clear()
		ax[1].clear()
		ax[2].clear()

		ax[0].set_title("Temperatures",fontsize = 15)
		ax[0].set_ylabel("T [*C]",fontsize=10)
		ax[0].set_xlabel("Time [s]",fontsize = 10)

		ax[1].set_title("Temperature deltas",fontsize = 15)
		ax[1].set_ylabel("Delta T [*C]",fontsize=10)
		ax[1].set_xlabel("Time [s]",fontsize = 10)
		ax[2].set_title("Temperature deltas",fontsize = 15)
		ax[2].set_ylabel("Delta T [*C]",fontsize=10)
		ax[2].set_xlabel("Time [s]",fontsize = 10)

		ax[0].grid()
		ax[1].grid()
		ax[2].grid()

		# Cooling mode part
		if hotorcold == "c":
			ax[0].errorbar(times,t_chip,xerr=None,yerr=None,c="blue",label="T_NTC chip") # can add errors if wanted
			ax[0].errorbar(times,t_cold,xerr=None,yerr=None,c="cyan",label="T_cold side Peltier") # can add errors if wanted
			ax[0].errorbar(times,t_hot,xerr=None,yerr=None,c="green",label="T_hot  side Peltier") # can add errors if wanted
			ax[0].errorbar(times,dp,xerr=None,yerr=None,c="red",label="Dew point") # can add errors if wanted
			#ax[1].errorbar(times,delta_t_hotncold,xerr=None,yerr=None,c="green",label="T_hot-T_cold") # can add errors if wanted
			#ax[1].errorbar(times,delta_t_chipcold,xerr=None,yerr=None,c="blue",label="T_NTC-T_cold") # can add errors if wanted
			ax[1].errorbar(times,delta_t_dpcold,xerr=None,yerr=None,c="red",label="T_cold-Dew point") # can add errors if wanted
			ax[1].hlines(5,min(times)-.5,max(times)+.5,colors="red",label="Min for Peltier (T_cold-dew point)",linestyles="dashed")
			ax[2].errorbar(times,delta_t_hotncold,xerr=None,yerr=None,c="green",label="|T_hot-T_cold|") # can add errors if wanted
			ax[2].errorbar(times,delta_t_chipcold,xerr=None,yerr=None,c="blue",label="T_NTC-T_cold") # can add errors if wanted
			#ax[1].hlines(60,min(times)-.5,max(times)+.5,colors="orange",label="Max for Peltier (T_hot-T_cold)")
			ax[0].legend(loc = "upper left", fontsize = 7)
			ax[1].legend(loc = "upper left", fontsize = 7)
			ax[2].legend(loc = "upper left", fontsize = 7)
			f.tight_layout()


		# Heating mode part
		elif hotorcold == "h":
			ax[0].errorbar(times,t_chip,xerr=None,yerr=None,c="blue",label="T_NTC chip") # can add errors if wanted
			ax[0].errorbar(times,t_cold,xerr=None,yerr=None,c="green",label="T_hot side Peltier") # can add errors if wanted
			ax[0].errorbar(times,t_hot,xerr=None,yerr=None,c="cyan",label="T_cold  side Peltier") # can add errors if wanted
			ax[0].errorbar(times,dp,xerr=None,yerr=None,c="red",label="Dew point") # can add errors if wanted
			#ax[1].errorbar(times,delta_t_hotncold,xerr=None,yerr=None,c="green",label="T_hot-T_cold") # can add errors if wanted
			#ax[1].errorbar(times,delta_t_chipcold,xerr=None,yerr=None,c="blue",label="T_NTC-T_cold") # can add errors if wanted
			ax[1].errorbar(times,delta_t_dphot,xerr=None,yerr=None,c="red",label="T_cold-Dew point") # can add errors if wanted
			ax[1].hlines(5,min(times)-.5,max(times)+.5,colors="red",label="Min for Peltier (T_cold-dew point)",linestyles="dashed")
			ax[2].errorbar(times,delta_t_hotncold,xerr=None,yerr=None,c="green",label="|T_hot-T_cold|") # can add errors if wanted
			ax[2].errorbar(times,delta_t_chiphot,xerr=None,yerr=None,c="blue",label="T_NTC-T_cold") # can add errors if wanted
			#ax[1].hlines(60,min(times)-.5,max(times)+.5,colors="orange",label="Max for Peltier (T_hot-T_cold)")
			ax[0].legend(loc = "upper left", fontsize = 7)
			ax[1].legend(loc = "upper left", fontsize = 7)
			ax[2].legend(loc = "upper left", fontsize = 7)
			f.tight_layout()




f,ax = plt.subplots(3,1,sharex =False)
ax[0].set_title("Temperatures",fontsize = 15)
ax[0].set_ylabel("T [*C]",fontsize=10)
ax[0].set_xlabel("Time [s]",fontsize = 10)

ax[1].set_title("Temperature deltas",fontsize = 15)
ax[1].set_ylabel("Delta T [*C]",fontsize=10)
ax[1].set_xlabel("Time [s]",fontsize = 10)

ax[2].set_title("Temperature deltas",fontsize = 15)
ax[2].set_ylabel("Delta T [*C]",fontsize=10)
ax[2].set_xlabel("Time [s]",fontsize = 10)

f.tight_layout()

outputfile = open(filename, "w" ) # open data file to write on it
ani = animation.FuncAnimation(f, animate, frames=N+1, interval=100,repeat=True,fargs=(outputfile,))

outputfile.close() # close the data file

plt.show()

ard.close() # close the serial comunication with Arduino



plt.show()
