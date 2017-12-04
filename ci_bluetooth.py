"""CI bluetooth"""

import struct
import binascii
from time import sleep


import msgpack

from enum import Enum
from bluepy import btle
from bluepy.btle import Peripheral, Scanner

from ci_gen_util import color_print

CONSOLE_BIT_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
MSGPACK_APPEND_UUID = "6e40000a-b5a3-f393-e0a9-e50e24dcca9e"
MSGPACK_DONE_UUID = "6e40000b-b5a3-f393-e0a9-e50e24dcca9e"

class BTDeviceTypes(Enum):
    """Types of bluetooth address for searching"""
    MFG = 1
    APP = 2
    ANY = 3

def bt_info_print(string):
    """Formatted print for internal bluetooth info"""
    color_print(string, "cyan", "on_grey")

class BLEConsoleDelegate(btle.DefaultDelegate):
    """Handles asynchronous bluetooth RX"""
    accumulate_str = ''
    data_accumulator = list()
    console_bit_tx_handle = None
    msgpack_append_handle = None
    msgpack_done_handle = None

    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        # ... initialise here


    def handleNotification(self, cHandle, data):
        """Handle a notification from the device"""
        #bt_info_print("handle{} len{}".format(hex(cHandle), len(data)))
        if(cHandle == self.console_bit_tx_handle):
            self.accumulate_str += data
        elif(cHandle == self.msgpack_append_handle):
            #self.accumulate_str += data
            for data_to_add in data:
                self.data_accumulator.append(data_to_add)
        elif(cHandle == self.msgpack_done_handle):
            bt_info_print([hex(ord(x)) for x in self.data_accumulator])
            unpacked = msgpack.unpackb(bytearray(self.data_accumulator))
            bt_info_print(unpacked)
            for item in unpacked:
                bt_info_print("msg # " + str(item[0]))
                #if (item[0] == 29):
                #    print("request stationary")
                #    send_data(p, msgpack.packb(((28,),))) #from crazyloop
            bt_info_print("crc:" + str(hex(msgpack.unpackb(bytearray(data)) * 0xffffffff)))
            tmp_str = str(hex(binascii.crc32(bytearray(self.data_accumulator)) & 0xffffffff))
            bt_info_print("calccrc: " + tmp_str)
            self.data_accumulator = list()
        else:
            bt_info_print("Unhandled cHandle")


    def print_clear_console(self):
        """Print the current bt console accumulation and clear the accumulator"""
        star_str = "*****************************"
        bt_info_print("\n\n{0}   BT Data   {0}\n".format(star_str))
        bt_info_print(self.accumulate_str)
        bt_info_print("\n  {0} END BT Data {0}\n\n".format(star_str))
        return_str = self.accumulate_str
        self.accumulate_str = ''
        return return_str

    def print_bare_clear_console(self):
        """Print the current bt console accumulation without annotation"""
        return_str = ""
        if(len(self.accumulate_str) > 0):
            color_print(self.accumulate_str, end_char="")
            return_str = self.accumulate_str
            self.accumulate_str = ''
        return return_str



class BTConnectedDevice(object):
    """Handles connecting and commands for bluetooth devices"""
    peripheral = None
    console_write_characteristic = None
    auth_characteristic = None
    console_enable_char = None
    batt_char = None
    delegate = None

    def connect(self, addr):
        """Connect to the device with the given address"""
        self.peripheral = Peripheral(str(addr), "random")
        self.peripheral.setMTU(272) # 256 16 for control or headers etc.
        self.delegate = BLEConsoleDelegate()
        self.peripheral.withDelegate(self.delegate)
        self.print_chars_and_handles()
        self.auth_characteristic = self.get_char("6E400005-B5A3-F393-E0A9-E50E24DCCA9E")
        self.auth_characteristic.write(struct.pack("16s", "iwanttobeajiobit"), False)
        self.console_enable_char = self.get_char("6E400004-B5A3-F393-E0A9-E50E24DCCA9E")
        self.console_enable_char.write(struct.pack('16s', "iwanttobeajiobit"), False)

        self.console_write_characteristic = self.get_char("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        self.peripheral.waitForNotifications(1)

    def disconnect(self):
        """Disconnect from the bluetooth device"""
        self.peripheral.disconnect()

    def connect_strongest_mfg(self):
        """Connect to the strongest mfg signal"""
        returned_devices = self.scan_for_bt_devices(BTDeviceTypes.MFG)
        strongest_rssi_dev = returned_devices[0]
        self.connect(strongest_rssi_dev.addr)

    def connect_strongest_app(self):
        """Connect to the stronest app signal"""
        returned_devices = self.scan_for_bt_devices(BTDeviceTypes.ANY)
        strongest_rssi_dev = returned_devices[0]
        sleep(1)
        self.connect(strongest_rssi_dev.addr)

    def connect_advertised_name(self, ad_name):
        """Connect to the strongest signal with a given advertised name"""
        returned_devices = self.scan_for_bt_devices(BTDeviceTypes.ANY)
        for device in returned_devices:
            device_name = self.get_device_name(device)
            if device_name == ad_name:
                sleep(1)
                self.connect(device.addr)
                return True
        bt_info_print("could not find advertising name {} in scan".format(ad_name))
        return False



    def scan_for_bt_devices(self, device_type):
        """Scan for Bluetooth devices"""
        scanner = Scanner()

        devices = scanner.scan()

        # keep only desired kind of bt device names
        correct_type_devices = self.get_devices_typed(devices, device_type)

        #sort list by RSSI
        correct_type_devices.sort(key=lambda x: x.rssi, reverse=True)

        for count, entry in enumerate(correct_type_devices):
            bt_info_print("{index}:RSSI - {rssi}, Device Name - {devicename}, Address - {address}".format(
                index=(count+1), rssi=entry.rssi,
                devicename=self.get_device_name(entry), address=entry.addr))

        return correct_type_devices

    def get_devices_typed(self, devlist, device_type):
        """Filter a list of devices using a given device type"""
        desired_devices = list()
        for entry in devlist:
            device_name = self.get_device_name(entry)
            if (device_name != None):
                if ((device_type == BTDeviceTypes.ANY) or
                        (device_type == BTDeviceTypes.MFG and len(device_name) == 12) or
                        (device_type == BTDeviceTypes.APP and device_name == "Jiobit")):
                    desired_devices.append(entry)
        return desired_devices

    def get_device_name(self, dev):
        """Return the name of the given device"""
        devname = None
        try:
            for (sdid, _, val) in dev.getScanData():
                if (sdid == 9):
                    devname = val
        except:
            return None
        return devname

    def send_console_cmd(self, command_str):
        """Send a bluetooth console command"""
        command_str = command_str + "\r\n"
        self.console_write_characteristic.write(command_str)
        #self.peripheral.waitForNotifications(1)

    def send_cmd_wait_resp_time(self, command_str, wait_sec):
        """Send a bluetooth console command and wait for a response"""
        command_str = command_str + "\r\n"
        self.console_write_characteristic.write(command_str)
        #sleep(wait_sec)
        for _ in range(0, wait_sec):
            self.peripheral.waitForNotifications(1)
        return_str = self.delegate.print_clear_console()
        return return_str

    def get_char(self, uuid):
        """Get the characteristic object associated with the given UUID"""
        characteristic = self.peripheral.getCharacteristics(uuid=uuid)[0]
        return characteristic

    def print_chars_and_handles(self):
        """
        Print all characteristics and handles for the connected device

        Also, populate some members of the delegate
        """
        characteristics = self.peripheral.getCharacteristics()
        for characteristic in characteristics:
            uuid = str(characteristic.uuid)
            handle = characteristic.getHandle()
            hex_handle = hex(handle)
            bt_info_print("characteristic " + uuid + " handle: " + hex_handle)
            if(uuid == CONSOLE_BIT_TX_UUID):
                self.delegate.console_bit_tx_handle = int(handle)
            if(uuid == MSGPACK_APPEND_UUID):
                self.delegate.msgpack_append_handle = int(handle)
            if(uuid == MSGPACK_DONE_UUID):
                self.delegate.msgpack_append_handle = int(handle)

    def read_batt_char(self):
        """Read the connected device's battery characteristic"""
        if(self.batt_char is None):
            self.batt_char = self.get_char("00002A19-0000-1000-8000-00805F9B34FB")
        if(self.batt_char.supportsRead()):
            return str(self.batt_char.read())
        else:
            bt_info_print("does not support read")
            return None


