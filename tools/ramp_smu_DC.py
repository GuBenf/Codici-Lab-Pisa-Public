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
    print("Configuring smu DC ... ")
    inst.write("smu.source.func = smu.FUNC_DC_VOLTAGE") # Source function --> voltage
    inst.write("smu.source.range = 2.000000e+01")
    inst.write("smu.source.autorange = smu.OFF")
    inst.write("smu.measure.range = 1.000000e-02")
    inst.write("smu.measure.autorange = smu.OFF")
    inst.write("smu.source.ilimit.level = 3.000000e-03")
    inst.write("smu.source.autodelay = smu.OFF")
    inst.write("smu.source.protect.level = smu.PROTECT_20V")
    inst.write("smu.source.readback = smu.ON")
    inst.write("smu.measure.func = smu.FUNC_DC_CURRENT") # Measure function --> current

    return inst

def ramp_up(resource_name,set_voltage,voltage,step,delay,name):
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

def ramp_down(resource_name,set_voltage,voltage,step,delay,name):
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




def ramp_voltage(resource_name_pwell,resource_name_psub, voltage_pwell, voltage_psub, step, delay):
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
    # Configure the smu for pwell
    inst_pwell = conf_smu(resource_name_pwell)

    # Configure the smu for psub
    inst_psub = conf_smu(resource_name_psub)


    # Safety: if pwell is lower than -6 V (set OVERPROTECTION voltage) or has a positive value it stops the program
    if voltage_psub < 0.:
        print("WARNING: provide the absolute value of psub!! ")
        sys.exit(0)

    if voltage_pwell < 0.:
        print("WARNING: provide the absolute value of pwell!! ")
        sys.exit(0)


    if voltage_pwell<6:
        if voltage_psub !=0:
            print("WARNING: if pwell is <6 psub NEEDS TO be 0! ")
            sys.exit(0)

    elif voltage_pwell == 6:
        # if voltage_psub > 14:
            # print("WARNING: psub CANNOT be >14 (W2R6)! ")

        if voltage_psub > 14:
            # print("WARNING: psub CANNOT be >4 (W8R04)! ")
            # print("WARNING: psub CANNOT be >9 (W2R17)! ")
            print("WARNING: psub CANNOT be >14 (W8R6)! ")
            sys.exit(0)

    elif voltage_pwell > 6:
        print("WARNING: pwell CANNOT be >6!! ")
        sys.exit(0)



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
        ramp_down(inst_pwell,set_voltage_pwell,voltage_pwell,step,delay,pwell_name)
        time.sleep(0.2)
        print(" ")
        ramp_down(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)

    elif set_voltage_pwell < voltage_pwell:
        ramp_up(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)
        time.sleep(0.2)
        print(" ")

        ramp_up(inst_pwell,set_voltage_pwell,voltage_pwell,step,delay,pwell_name)

    else:
        if set_voltage_psub > voltage_psub:
            ramp_down(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)

        else:
              ramp_up(inst_psub,set_voltage_psub,voltage_psub,step,delay,psub_name)



    print(" ")

    print("Voltage ramp completed.")
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



def main():
    # Parse arguments from terminal
    parser = argparse.ArgumentParser(description="Ramp voltage of the SMU.")
    parser.add_argument('--pwell', type=float, required=True, help="Pwell")
    parser.add_argument('--psub', type=float, required=True, help="Insert the absolute value of the difference between Pwell and Psub")

    parser.add_argument('--step', type=float, default=0.5, help="Voltage step increment (default is 0.5V).")
    parser.add_argument('--delay', type=float, default=0.1, help="Delay between steps (default is 0.1 seconds).")

    args = parser.parse_args()

    # Define resource name (can be set in the terminal or as a constant)
    RESOURCE_NAME_pwell = "TCPIP0::169.254.91.2::inst0::INSTR"
    RESOURCE_NAME_psub = "TCPIP0::169.254.91.1::inst0::INSTR"

    # Call the ramp voltage function
    ramp_voltage(RESOURCE_NAME_pwell,RESOURCE_NAME_psub, args.pwell, args.psub, args.step, args.delay)



if __name__ == '__main__':
    main()
