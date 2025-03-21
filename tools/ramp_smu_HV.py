import pyvisa as visa
import time
import numpy as np
import argparse
import sys

def conf_smu(resource_name):
    # Initialize VISA resource manager
    rm = visa.ResourceManager()

    # Print instrument identification
    inst = rm.open_resource(resource_name)
    print("Connected to:", inst.query("*IDN?"))

    # Configure SMU (setup details can stay the same)
    print("Configuring smu HV ... ")
    inst.write("smu.source.func = smu.FUNC_DC_VOLTAGE") # Source function --> voltage
    inst.write("smu.source.range = 2.000000e+02")
    inst.write("smu.source.autorange = smu.OFF")
    inst.write("smu.measure.range = 1.000000e-03")
    inst.write("smu.measure.autorange = smu.OFF")
    inst.write("smu.source.ilimit.level = 3.000000e-04")
    inst.write("smu.source.autodelay = smu.OFF")
    inst.write("smu.source.protect.level = smu.PROTECT_40V")
    inst.write("smu.source.readback = smu.ON")
    inst.write("smu.measure.func = smu.FUNC_DC_CURRENT") # Measure function --> current

    return inst

def ramp_voltage(resource_name, end_voltage, step, delay):
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
    # Configure the smu
    inst = conf_smu(resource_name)

    # Safety: if HV is higher than 40V (set OVERPROTECTION voltage) or has a negative value it stops the program
    if abs(end_voltage)>30:
        print("WARNING: the HV set is higher than the Overprotection Voltage set!")
        sys.exit(0)


    if end_voltage < 0.:
        print("HV cannot be negative!! ")
        sys.exit(0)

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
        sys.exit(0)

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

def main():
    # Parse arguments from terminal
    parser = argparse.ArgumentParser(description="Ramp voltage of the SMU.")
    parser.add_argument('--hv', type=float, required=True, help="HV")
    parser.add_argument('--step', type=float, default=0.5, help="Voltage step increment (default is 0.1V).")
    parser.add_argument('--delay', type=float, default=0.1, help="Delay between steps (default is 0.1 seconds).")

    args = parser.parse_args()

    # Define resource name (can be set in the terminal or as a constant)
    RESOURCE_NAME = "TCPIP0::169.254.91.3::inst0::INSTR"

    # Call the ramp voltage function
    ramp_voltage(RESOURCE_NAME, args.hv, args.step, args.delay)



if __name__ == '__main__':
    main()
