#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2025 Arkadiusz Netczuk <dev.arnet@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import subprocess
import time
import re

from typing import List

import argparse


class Advertiser:

    ## device: interface name or MAC address
    def __init__(self, device = "hci0"):
        self.device = device
        self.iface = None

    def advertise_ble(self, name=None) -> bool:
        try:
            if self.iface is None:
                self.iface = self._get_interface()

            ## disable advertisement
            self._run_hcitool_cmd( ["0x08", "0x000A"], ["00"] )
            
            ## set advertisement parameters
            data = [
                "20", "00", "20", "00", "00", "00", "00", "00", "00", "00", "00", "00", "00", "07", "00"
            ]
            self._run_hcitool_cmd(["0x08", "0x0006"], data)            

            ## set advertisement data
            adv_data = AdvertisementData()
            ## 0x01 - Flags
            adv_data.add_field("01", ["06"])    
            ## 0x02 - Incomplete List of 16-bit Services UUIDS
            adv_data.add_field("02", ["50", "FD"])    
            ## 0x16 - Service data
            adv_data.add_field("16", ["0x50", "0xFD", "0x41", "0x00", "0x00", "0x08", "0x63", "0x63", 
                                      "0x71", "0x68", "0x76", "0x66", "0x6A", "0x78"])    

            data = adv_data.get_data()
            self._run_hcitool_cmd( ["0x08", "0x0008"], data)

            ## set scan response
            adv_data = AdvertisementData()
            ## 0xFF - manufacturer name
            adv_data.add_field_raw("0xFF d0 07 00 00 01 04 96 1c 64 ff 53 ed 16 10 e1 91 1c f1 bf 03 b5 f8")
            ## 0x09 - device name
            if name:
                adv_data.add_text("0x09", name)
            
            data = adv_data.get_data()
            self._run_hcitool_cmd( ["0x08", "0x0009"], data )

            ## enable advertisement
            self._run_hcitool_cmd( ["0x08", "0x000A"], ["01"] )

            print(f"Advertising as {name}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            return False
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def stop(self):
        try:
            # Stop advertising
            subprocess.run(["sudo", "hciconfig", self.iface, "noscan"], check=True)
            print("Advertising stopped.")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            return False

        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def _run_hcitool_cmd(self, cmd_bytes, data_list) -> bool:
        # cmd_list = ["hcitool", "-i", self.iface, "cmd"]
        cmd_list = ["sudo", "hcitool", "-i", self.iface, "cmd"]
        cmd_list.extend(cmd_bytes)
        cmd_list.extend(data_list)
        print( "executing:", " ".join(cmd_list) )

        result = subprocess.run( cmd_list, 
                                 capture_output=True,   # Capture stdout and stderr
                                 text=True,             # Decode the output as a string
                                 check=True )

        stdout = result.stdout
        
        out_list = stdout.split("\n")

        found_line = -1
        for index, element in enumerate(out_list):
            if element.startswith("> HCI Event:"):
                found_line = index + 1
                break

        if found_line < 0 or found_line >= len(out_list):
            print(f"unable to get status, raw output:\n{stdout}")
            return False

        status_line = out_list[found_line]
        status_line = status_line.strip()

        status_bytes = status_line.split()
        if len(status_bytes) < 4:
            print(f"unable to get status, raw output:\n{stdout}")
            return False

        status_byte = status_bytes[3]
        status = int(status_byte, 16)

        meaning = ""
        if status == 0x00:
            meaning = "Success"
        elif status == 0x0c:
            meaning = "Command Disallowed"

        if meaning:
            print(f"got status: {meaning} 0x{status_byte}")       
        else:
            print(f"got status: 0x{status_byte}")

        return status == 0

    def _get_interface(self):
        if is_mac_address(self.device) == False:
            ## no mac - assume interface name
            return self.device

        self.device = self.device.replace("-", ":")

        cmd_list = ["hcitool", "dev"]
        result = subprocess.run( cmd_list, 
                                 capture_output=True,   # Capture stdout and stderr
                                 text=True,             # Decode the output as a string
                                 check=True )

        stdout = result.stdout
        
        out_list = stdout.split("\n")
        dev_lines = out_list[1:]
        if len(dev_lines) < 1:
            print(f"no devices found, raw output:\n{stdout}")
            return None

        dev_lines = [item.strip() for item in dev_lines]
        dev_lines = [item.split() for item in dev_lines]

        for item in dev_lines:
            if not item:
                continue
            if item[1] == self.device:
                return item[0]

        print(f"unable to find device by MAC, raw output:\n{stdout}")
        return None


class AdvertisementData:
    
    def __init__(self):
        self.data = []

    def get_data(self):
        ret_data = []
        data_len = len(self.data)
        ret_data.append( hex(data_len) )
        ret_data.extend( self.data )
        return ret_data

    def add_field_raw(self, data_string: str):
        data_array = data_string.split()
        type_byte = data_array[0]
        data_array = data_array[1:]
        self.add_field(type_byte, data_array)
    
    def add_field(self, type_byte: str, data_array: List[str]):
        data_len = len(data_array) + 1
        self.data.append( hex(data_len) )
        self.data.append( type_byte )
        self.data.extend( data_array )
    
    def add_text(self, type_byte: str, data_string: str):
        hex_list = [hex(ord(c)) for c in data_string]
        self.add_field(type_byte, hex_list)


def is_mac_address(data):
    pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(pattern.match(data))


def main():
    parser = argparse.ArgumentParser(description="Advertise legacy using hcitool")
    parser.add_argument('iface', help="Adapter (interface) to use, e.g. hci0")
    
    args = parser.parse_args()
    
    iface = args.iface

    advertiser = Advertiser(device=iface)
    if advertiser.advertise_ble(name="TH09") == False:
        return

    # Advertise for the specified duration
    duration = 30
    time.sleep(duration)
    
    advertiser.stop()    


if __name__ == "__main__":
    main()
