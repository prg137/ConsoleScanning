"""Command-line program for running jiobit console commands"""
from __future__ import print_function
from termcolor import colored

import sys
import signal
import time
import select
import tty
import termios

import ci_bluetooth

def isData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def catch_ctrl_C(sig, frame):
    print("Did you just enter Ctrl + C ??? ")
    print("This is going to disconnect the Jiobit.")
    sys.exit()

def main():
    """Main execution of ble console"""
    print("Scanning for Jiobits. Please wait...")
    connection = ci_bluetooth.BTConnectedDevice()
    potential_connections = connection.scan_for_bt_devices(ci_bluetooth.BTDeviceTypes.ANY)
    selected_index = raw_input("select a device index from the list above > ")
    selected_index = int(selected_index.strip())
    selected_device = potential_connections[selected_index-1]
    if(selected_device is not None):
        connection.connect(selected_device.addr)
        print("Connection complete")
        command = ""
        while 1:
            signal.signal(signal.SIGINT, catch_ctrl_C)
            if isData():
                while isData():
                    if (command.find('loop') != -1):
                        a,b,c = command.split(' ')
                        for n in int(b):
                            c  += sys.stdin.readline()
                    else:
                        command  += sys.stdin.readline()
                if '\n' in command:
                    command = command.strip()
                    connection.send_console_cmd(command)
                    command = ""
            connection.peripheral.waitForNotifications(1)
            data_str = connection.delegate.print_bare_clear_console()





main()
