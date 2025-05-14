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

import logging
from typing import List, Any, Dict

import subprocess  # nosec
import re

from btgattmitm.connector import AdvertisementData
from btgattmitm.advertisementmanager import AdvertisementManager


_LOGGER = logging.getLogger(__name__)


def is_mac_address(data):
    pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    return bool(pattern.match(data))


## get device name (eg. hci0) using MAC address
def find_hci_iface_by_mac(mac_address) -> str:
    mac_address = mac_address.replace("-", ":")

    cmd_list = ["hcitool", "dev"]
    result = subprocess.run(  # nosec
        cmd_list,
        capture_output=True,  # Capture stdout and stderr
        text=True,  # Decode the output as a string
        check=True,
    )

    stdout = result.stdout

    out_list = stdout.split("\n")
    dev_lines = out_list[1:]
    if len(dev_lines) < 1:
        _LOGGER.warning("no devices found, raw output:\n%s", stdout)
        return None

    dev_lines = [item.strip() for item in dev_lines]
    name_mac_list: List[List[str]] = [item.split() for item in dev_lines]

    for item in name_mac_list:
        if not item:
            continue
        if item[1] == mac_address:
            return item[0]

    _LOGGER.warning("unable to find device by MAC, raw output:\n%s", stdout)
    return None


## =============================================================


## unfortunately hcitool does not work well with bluepy
class Advertiser:

    def __init__(self, hci_iface_index: int):
        self.iface = f"hci{hci_iface_index}"
        self.adv_data = AdvertisementData()
        self.scanresp_data = AdvertisementData()
        self.sudo_mode = False

    def advertise(self) -> bool:
        try:
            _LOGGER.info("Starting advertisement")

            ### causes disconnection from device
            # cmd_list = []
            # if self.sudo_mode:
            #     cmd_list.append("sudo")
            # cmd_list.extend(["hciconfig", self.iface, "down"])
            # subprocess.run(cmd_list,    # nosec
            #     capture_output=True,  # Capture stdout and stderr
            #     text=True,  # Decode the output as a string
            #     check=True,
            # )
            #
            # cmd_list = []
            # if self.sudo_mode:
            #     cmd_list.append("sudo")
            # cmd_list.extend(["hciconfig", self.iface, "up"])
            # subprocess.run(cmd_list,    # nosec
            #     capture_output=True,  # Capture stdout and stderr
            #     text=True,  # Decode the output as a string
            #     check=True,
            # )

            #### causes connected adapter to hang
            # ## reset device state
            # self._run_hcitool_cmd(["0x03", "0x0003"])

            ## disable advertisement
            self._run_hcitool_cmd(["0x08", "0x000A"], ["00"])

            ## set advertisement parameters
            data = ["20", "00", "20", "00", "00", "00", "00", "00", "00", "00", "00", "00", "00", "07", "00"]
            self._run_hcitool_cmd(["0x08", "0x0006"], data)

            ## set advertisement data
            adv_data = AdvertisementDataBuilder()
            adv_data.add_adv(self.adv_data)

            data = adv_data.get_data()
            self._run_hcitool_cmd(["0x08", "0x0008"], data)

            ## set scan response
            adv_data = AdvertisementDataBuilder()
            adv_data.add_adv(self.scanresp_data)

            data = adv_data.get_data()
            self._run_hcitool_cmd(["0x08", "0x0009"], data)

            ## enable advertisement
            self._run_hcitool_cmd(["0x08", "0x000A"], ["01"])

            _LOGGER.info("Advertisement started")
            return True

        except subprocess.CalledProcessError:
            _LOGGER.error("exception occur while starting advertisement")
            return False

        except Exception:  # pylint: disable=W0718
            _LOGGER.exception("exception occur while starting advertisement")
            return False

    def stop(self):
        try:
            # Stop advertising
            cmd_list = []
            if self.sudo_mode:
                cmd_list.append("sudo")
            cmd_list.extend(["hciconfig", self.iface, "noscan"])
            subprocess.run(cmd_list,    # nosec
                capture_output=True,  # Capture stdout and stderr
                text=True,  # Decode the output as a string
                check=True,
            )
            _LOGGER.info("Advertisement stopped")
            return True

        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip()
            _LOGGER.error("exception occur during advertisement stop, reason: %s", message)
            _LOGGER.warning("in case of lack of privileges try running program with --sudo option")
            return False

        except Exception:  # pylint: disable=W0718
            _LOGGER.exception("exception occur during advertisement stop")
            return False

    def _run_hcitool_cmd(self, cmd_bytes, data_list: List[str] = None) -> bool:
        if data_list is None:
            data_list = []

        status_byte = None

        try:
            cmd_list = []
            if self.sudo_mode:
                cmd_list.append("sudo")
            cmd_list.extend(["hcitool", "-i", self.iface, "cmd"])
            cmd_list.extend(cmd_bytes)
            cmd_list.extend(data_list)
            _LOGGER.info("executing: %s", " ".join(cmd_list))

            result = subprocess.run(  # nosec
                cmd_list,
                capture_output=True,  # Capture stdout and stderr
                text=True,  # Decode the output as a string
                check=True,
            )

            stdout = result.stdout

            out_list = stdout.split("\n")

            found_line = -1
            for index, element in enumerate(out_list):
                if element.startswith("> HCI Event:"):
                    found_line = index + 1
                    break

            if found_line < 0 or found_line >= len(out_list):
                _LOGGER.warning("unable to get status, raw output:\n%s", stdout)
                return False

            status_line = out_list[found_line]
            status_line = status_line.strip()

            status_bytes = status_line.split()
            if len(status_bytes) < 4:
                _LOGGER.warning("unable to get status, raw output:\n%s", stdout)
                return False

            status_byte = status_bytes[3]

        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip()
            _LOGGER.error("error while running command: %s, reason: %s", cmd_list, message)
            _LOGGER.warning("in case of lack of privileges try running program with --sudo option")
            raise

        status = int(status_byte, 16)

        meaning = ""
        if status == 0x00:
            meaning = "Success"
        elif status == 0x0C:
            meaning = "Command Disallowed"

        if status == 0x00:
            if meaning:
                _LOGGER.info("got status: %s 0x%s", meaning, status_byte)
            else:
                _LOGGER.info("got status: 0x%s", status_byte)
        else:
            if meaning:
                _LOGGER.error("got status: %s 0x%s", meaning, status_byte)
            else:
                _LOGGER.error("got status: 0x%s", status_byte)

            raise RuntimeError(f"command failed with status: 0x{status_byte}")

        return True


class AdvertisementDataBuilder:

    def __init__(self):
        self.data = []

    def get_data(self):
        ret_data = []
        data_len = len(self.data)
        ret_data.append(hex(data_len))
        ret_data.extend(self.data)
        return ret_data

    def add_field_raw(self, data_string: str):
        data_array = data_string.split()
        type_byte = data_array[0]
        data_array = data_array[1:]
        self.add_field(type_byte, data_array)

    def add_field(self, type_byte: str, data_array: List[str]):
        data_len = len(data_array) + 1
        self.data.append(hex(data_len))
        self.data.append(type_byte)
        self.data.extend(data_array)

    def add_text(self, type_byte: str, data_string: str):
        hex_list = [hex(ord(c)) for c in data_string]
        self.add_field(type_byte, hex_list)

    def add_adv(self, adv_data: AdvertisementData):
        props_dict: Dict[int, Any] = adv_data.get_props()
        for prop_key, prop_val in props_dict.items():
            _LOGGER.info("adding advertisement: %s %s", prop_key, prop_val)

            if prop_key == 0x02:
                ## 0x02 - Incomplete List of 16-bit Services UUIDS
                # skipped - will be added when handling service data
                continue

            if prop_key == 0x09:
                ## 0x09 - device name
                prop_id = hex(prop_key)
                self.add_text(prop_id, prop_val)
                continue

            if prop_key == 0x16:
                ## 0x16 - Service data
                prop_id = hex(prop_key)
                for service_id, service_data in prop_val.items():
                    service_num = int(service_id, 16)
                    service_id_list = int_to_hex_list(service_num)

                    self.add_field("0x02", service_id)
                    data_str = [hex(item) for item in service_data]
                    data_list = service_id_list
                    data_list.extend(data_str)
                    self.add_field(prop_id, data_list)
                continue

            if prop_key == 0xFF:
                ## 0xFF - manufacturer name
                prop_id = hex(prop_key)
                for manu_id, manu_data in prop_val.items():
                    manu_id_list = int_to_hex_list(manu_id)
                    data_str = [hex(item) for item in manu_data]
                    data_list = manu_id_list
                    data_list.extend(data_str)
                    self.add_field(prop_id, data_list)
                continue

            _LOGGER.warning("unhandled property %s with '%s'", hex(prop_key), prop_val)


def int_to_hex_list(number: int, byte_order="little"):
    # determine how many bytes are needed to represent the integer
    length = (number.bit_length() + 7) // 8 or 1
    # convert to bytes
    bytes_list = number.to_bytes(length, byteorder=byte_order)
    # convert each byte to hex and join with spaces
    return [f"{byte:02X}" for byte in bytes_list]


## =======================================================


class HciToolAdvertisementManager(AdvertisementManager):

    def __init__(self, hci_iface_index: int, sudo_mode: bool = False):
        self.adv = Advertiser(hci_iface_index)
        self.adv.sudo_mode = sudo_mode

    ## configuration of service
    def initialize(self):
        ## do nothing
        pass

    ## startup of service
    def register(self):
        self.adv.advertise()

    ## stop of service
    def unregister(self):
        self.adv.stop()

    ## ======================================================

    def set_local_name(self, name: str):
        self.adv.adv_data.set_name(name)

    def set_service_uuid_list(self, service_list: List[str]):
        self.adv.adv_data.set_service_uuid_list(service_list)

    def get_adv_data(self) -> AdvertisementData:
        return self.adv.adv_data

    def get_scanresp_data(self) -> AdvertisementData:
        return self.adv.scanresp_data

    def add_adv_data(self, adv_data: AdvertisementData):
        self.adv.adv_data.merge(adv_data)

    def add_scanresp_data(self, scanresp_data: AdvertisementData):
        self.adv.scanresp_data.merge(scanresp_data)
