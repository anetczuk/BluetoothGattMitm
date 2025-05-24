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

from btgattmitm.connector import AdvertisementData
from btgattmitm.advertisementmanager import AdvertisementManager
from btgattmitm.hcitool.advertisement import find_mac_by_hci_iface, parse_hcitool_output_status


_LOGGER = logging.getLogger(__name__)


class Advertiser:

    def __init__(self, hci_iface_index: int):
        self.iface = hci_iface_index
        self.adv_data = AdvertisementData()
        self.scanresp_data = AdvertisementData()
        self.sudo_mode = False

    def advertise(self) -> bool:
        try:
            _LOGGER.info("Starting advertisement")

            # _LOGGER.info("setting MAC address")
            # device_mac = "DC:23:4F:DD:48:3E"
            # # device_mac = "74:E5:F9:5E:C1:2F"
            # self._run_btmgmt_cmd(["power", "off"])
            # self._run_btmgmt_cmd(["public-addr", device_mac])
            # self._run_btmgmt_cmd(["power", "on"])

            # ## enable BLE
            # _LOGGER.info("enabling BLE")
            # if self._run_btmgmt_cmd(["le", "on"]) is False:
            #     _LOGGER.error("unable to start BLE advertisement")
            #     return False

            # ## disable "classic" device type
            # if self._run_btmgmt_cmd(["bredr", "off"]) is False:
            #     _LOGGER.warning("unable to disable classic mode")

            ## disable default advertisement - "add-adv" will activate advertisement automatically with custom data
            _LOGGER.info("disabling btmgmt advertising")
            if self._run_btmgmt_cmd(["advertising", "off"]) is False:
                _LOGGER.error("unable to configure advertisement")
                return False

            # _LOGGER.info("clearing old advertisings")
            # self._run_btmgmt_cmd(["clr-adv"])

            bt_name = self.adv_data.get_name()
            if bt_name is not None:
                _LOGGER.info("setting device name: %s", bt_name)
                if self._run_btmgmt_cmd(["name", bt_name]) is False:
                    _LOGGER.warning("unable to set advertising name")

            ## set advertisement data
            _LOGGER.info("setting advertisement data")
            adv_command_data = ["add-adv"]

            # service_uuids = self.adv_data.get_prop(0x06)
            # if service_uuids is not None:
            #     adv_command_data.append("-u")
            #     adv_command_data.extend(service_uuids)

            adv_data = self._prepare_adv_data()

            ## set advertisement
            data = adv_data[0]
            if data:
                adv_command_data.append("-d")  ## set advertising data
                adv_command_data.append(data)

            ## set scan response
            data = adv_data[1]
            if data:
                adv_command_data.append("-s")  ## set scan response data
                adv_command_data.append(data)

            adv_command_data.append("-c")  ## set connectable

            adv_instance = "2"  ## have to be greater than 1

            adv_command_data.append(adv_instance)  ## set advertising instance

            if self._run_btmgmt_cmd(adv_command_data) is False:
                _LOGGER.error("unable to configure advertisement")
                return False

            if self._set_public_mac(adv_instance) is False:
                return False

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
            # stop advertising
            self._run_btmgmt_cmd("clr-adv")
            _LOGGER.info("Advertisement stopped")
            return True

        except subprocess.CalledProcessError as exc:
            message = exc.output.strip()
            _LOGGER.error("exception occur during advertisement stop, reason: %s", message)
            _LOGGER.warning("in case of lack of privileges try running program with --sudo option")
            return False

        except Exception:  # pylint: disable=W0718
            _LOGGER.exception("exception occur during advertisement stop")
            return False

    def _prepare_adv_data(self):
        ret_adv_list = []
        ret_scan_list = []

        ## set advertisement data
        adv_data_count = 0

        adv_data_builder = AdvertisementDataBuilder()
        adv_data_builder.add_adv(self.adv_data)
        data = adv_data_builder.get_fields()
        if data:
            for item in data:
                item = convert_to_btmgmt(item)
                str_data = "".join(item)
                curr_size = int(len(str_data) / 2)
                ## put data to scan response if size exceeds limit
                ## or when previous data was already added to scan response
                if adv_data_count + curr_size < 31 and not ret_scan_list:
                    adv_data_count += curr_size
                    ret_adv_list.extend(item)
                else:
                    _LOGGER.warning("advertisement data size overflow - setting data as scan response")
                    ret_scan_list.extend(item)

        ## set scan response
        scanresp_data_builder = AdvertisementDataBuilder()
        scanresp_data_builder.add_adv(self.scanresp_data)
        data = scanresp_data_builder.get_data()
        if data:
            data = convert_to_btmgmt(data)
            ret_scan_list.extend(data)

        ret_adv = "".join(ret_adv_list)
        ret_scan = "".join(ret_scan_list)
        return [ret_adv, ret_scan]

    def _set_public_mac(self, adv_instance) -> bool:
        ## workaround for disabling privacy (random MAC)
        ## because 'btmgmt' way seems not working:
        ##   sudo btmgmt --index ${IFACE} power off
        ##   sudo btmgmt --index ${IFACE} privacy off
        ##   sudo btmgmt --index ${IFACE} power on
        ## workaround is to call 'hcitool' directly
        ### at least works, but better to disable privacy instead of setting MAC directly
        _LOGGER.info("setting MAC address (prevent privacy)")
        device_mac = find_mac_by_hci_iface(self.iface)
        # device_mac = "DC:23:4F:DD:48:3E"
        mac_pairs = device_mac.split(":")
        mac_pairs.reverse()
        cmd_list = ["hcitool", "-i", "hci0", "cmd", "0x08", "0x0035", f"0{adv_instance}"]
        cmd_list.extend(mac_pairs)
        result = self._run_cmd(cmd_list)
        if result is None or result.returncode != 0:
            _LOGGER.warning("unable to set MAC address")
            return False

        status_byte = parse_hcitool_output_status(result.stdout)
        if status_byte is None:
            _LOGGER.warning("unable to set MAC address")
            return False
        status = int(status_byte, 16)
        if status == 0x00:
            _LOGGER.info("static MAC address configured")
        else:
            _LOGGER.warning("unable to set MAC address, response status: %s", status)

        return True

    def _run_btmgmt_cmd(self, cmd_params: str | List[str] = None) -> bool:
        if cmd_params is None:
            cmd_params = []
        if isinstance(cmd_params, str):
            cmd_params = [cmd_params]
        cmd_list = []
        cmd_list.extend(["btmgmt", "--index", str(self.iface)])
        cmd_list.extend(cmd_params)
        result = self._run_cmd(cmd_list)
        if result is None:
            return False
        if result.returncode != 0:
            return False
        return True

    def _run_cmd(self, cmd_params: str | List[str] = None):
        if cmd_params is None:
            cmd_params = []
        if isinstance(cmd_params, str):
            cmd_params = [cmd_params]

        try:
            cmd_list = []
            if self.sudo_mode:
                cmd_list.append("sudo")
            cmd_list.extend(cmd_params)
            _LOGGER.info("executing: %s", " ".join(cmd_list))

            result = subprocess.run(  # nosec
                cmd_list,
                capture_output=True,  # capture stdout and stderr
                text=True,  # decode the output as a string
                check=True,
            )

            _LOGGER.info("command response: %s", result.stdout.strip())
            return result

        except subprocess.CalledProcessError as exc:
            message = exc.output.strip()
            _LOGGER.error("error while running command: %s, reason: %s", " ".join(cmd_list), message)
            _LOGGER.warning("in case of lack of privileges try running program with --sudo option")

        return None


class AdvertisementDataBuilder:

    def __init__(self):
        self.fields_bytes = []

    def get_fields(self):
        return self.fields_bytes.copy()

    ## returns list of hex numbers
    def get_data(self) -> List[str]:
        ret_data = []
        for item in self.fields_bytes:
            ret_data.extend(item)
        return ret_data

    def add_field_raw(self, data_string: str):
        data_array = data_string.split()
        type_byte = data_array[0]
        data_array = data_array[1:]
        self.add_field(type_byte, data_array)

    ## 'data_array' contains pairs of characters
    def add_field(self, type_byte: str, data_array: List[str]):
        data_len = len(data_array) + 1
        data = []
        data.append(hex(data_len))
        data.append(type_byte)
        data.extend(data_array)
        self.fields_bytes.append(data)

    def add_text(self, type_byte: str, data_string: str):
        hex_list = [hex(ord(c)) for c in data_string]
        self.add_field(type_byte, hex_list)

    def add_adv(self, adv_data: AdvertisementData):
        props_dict: Dict[int, Any] = adv_data.get_props()
        for prop_key, prop_val in props_dict.items():
            _LOGGER.info("adding advertisement: %s %s %s", prop_key, prop_val, type(prop_val))

            ## 0x01 - Flags
            if prop_key == 0x01:
                prop_id = hex(prop_key)
                if isinstance(prop_val, int):
                    prop_val = hex(prop_val)
                self.add_field(prop_id, [prop_val])
                continue

            ## 0x02 - Incomplete List of 16-bit Services UUIDS
            if prop_key == 0x02:
                # skipped - will be added when handling service data
                continue

            ## 0x06 - Incomplete List of 128-bit Services UUIDS
            if prop_key == 0x06:
                prop_id = hex(prop_key)
                for service_uuid in prop_val:
                    service_uuid = service_uuid.replace("-", "")
                    pairs = [service_uuid[i : i + 2] for i in range(0, len(service_uuid), 2)]
                    pairs.reverse()
                    self.add_field(prop_id, pairs)
                continue

            ## 0x08 - short device name
            if prop_key == 0x08:
                prop_id = hex(prop_key)
                self.add_text(prop_id, prop_val)
                continue

            ## 0x09 - device name
            if prop_key == 0x09:
                prop_id = hex(prop_key)
                self.add_text(prop_id, prop_val)
                continue

            ## 0x0A - Tx Power Level
            if prop_key == 0x0A:
                prop_id = hex(prop_key)
                self.add_field(prop_id, [prop_val])
                continue

            ## 0x16 - Service data
            if prop_key == 0x16:
                prop_id = hex(prop_key)
                for service_id, service_data in prop_val.items():
                    service_num = int(service_id, 16)
                    service_id_list = int_to_hex_list(service_num)

                    self.add_field("0x02", service_id_list)
                    data_str = [hex(item) for item in service_data]
                    data_list = service_id_list
                    data_list.extend(data_str)
                    self.add_field(prop_id, data_list)
                continue

            ## 0xFF - manufacturer name
            if prop_key == 0xFF:
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


def convert_to_btmgmt(data_list: List[str]):
    data = remove_hex_prefix(data_list)
    ret_data = []
    for item in data:
        if len(item) < 2:
            ret_data.append(f"0{item}")
        else:
            ret_data.append(item)
    return ret_data


## remove 0x prefix
def remove_hex_prefix(data_list: List[str]):
    ret_data = []
    for item in data_list:
        if item.startswith("0x"):
            ret_data.append(item[2:])
        else:
            ret_data.append(item)
    return ret_data


## =======================================================


class BtmgmtAdvertisementManager(AdvertisementManager):

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
