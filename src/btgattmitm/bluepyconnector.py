#
# MIT License
#
# Copyright (c) 2017 Arkadiusz Netczuk <dev.arnet@gmail.com>
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

import struct
import logging
from typing import List, Dict

from bluepy import btle

from btgattmitm.synchronized import synchronized
from btgattmitm.dbusobject.exception import InvalidStateError
from btgattmitm.connector import AbstractConnector, CallbackContainer, ServiceData, AdvertisementData


_LOGGER = logging.getLogger(__name__)


# =================================================


## allowed flags
#         broadcast
#         read
#         write-without-response
#         write
#         notify
#         indicate
#         authenticated-signed-writes
#         extended-properties
FLAGS_DICT = {  # 0b00000001 : "BROADCAST",
    0b00000010: "read",
    0b00000100: "write-without-response",
    0b00001000: "write",
    0b00010000: "notify",
    0b00100000: "indicate",
    # 0b01000000 : "WRITE SIGNED",
    # 0b10000000 : "EXTENDED PROPERTIES",
}


def extract_flag(prop):
    if prop not in FLAGS_DICT:
        return None
    return FLAGS_DICT[prop]


def extract_bits(number):
    ret = []
    bit = 1
    while number >= bit:
        if number & bit:
            ret.append(bit)
        bit <<= 1
    return ret


def props_mask_to_list(char_item):
    props_mask = char_item.properties
    propsString = char_item.propertiesToString()

    #         _LOGGER.debug("Reading flags from: %s", propsString)
    #         _LOGGER.debug("Properties bitmask: %s", format(propsMask,'016b') )

    flagsList = []
    propsList = extract_bits(props_mask)
    for prop in propsList:
        flag = extract_flag(prop)
        if flag is None:
            _LOGGER.warning("Could not find flag for property: %i in string: %s", prop, propsString)
            continue
        flagsList.append(flag)

    _LOGGER.debug("Reading properties %s to flags %s", propsString, flagsList)

    return flagsList


def get_services_data(peripheral: btle.Peripheral) -> List[ServiceData]:
    _LOGGER.debug("getting services")
    services_list = peripheral.getServices()
    ret_list = []
    for serv in services_list:
        serv_uuid = str(serv.uuid)
        serv_name = serv.uuid.getCommonName()
        _LOGGER.debug("Service: %s[%s]", serv_uuid, serv_name)
        serv_data = ServiceData(serv_uuid, serv_name)
        ret_list.append(serv_data)

        charsList = serv.getCharacteristics()
        for ch in charsList:
            _LOGGER.debug("Char: %s h:%#x p:%s", ch, ch.getHandle(), ch.propertiesToString())
            char_uuid = str(ch.uuid)
            char_name = ch.uuid.getCommonName()
            char_handle = ch.getHandle()
            char_props = props_mask_to_list(ch)
            serv_data.add_characteristic(char_uuid, char_name, char_handle, char_props)
    return ret_list


# =================================================


###
class BluepyConnector(AbstractConnector):
    """Deprecated connector based on bluepy."""

    ## iface: int - hci index
    def __init__(self, mac: str, iface: int = None, address_type: str = None):
        super().__init__()

        self.address: str = mac
        self.addressType: str = address_type
        self.iface: int = iface
        self.callbacks = CallbackContainer()
        self.connectDelegate = ConnectDelegate(self.callbacks)
        self._peripheral: btle.Peripheral = None

    def is_connected(self) -> bool:
        return self._peripheral is not None

    def get_address(self) -> str:
        return self.address

    def get_address_type(self):
        return self.addressType

    def get_advertisement_data(self) -> Dict[str, AdvertisementData]:
        return self._scan()

    @synchronized
    def _scan(self) -> Dict[str, AdvertisementData]:
        _LOGGER.info("scanning device %s advertisement data using controller: %s", self.address, self.iface)
        delegate = ScanDelegate(self.address)
        scanner = btle.Scanner(iface=self.iface)
        scanner.withDelegate(delegate)
        try:
            scanner.scan(10.0)
        except btle.BTLEDisconnectError:
            _LOGGER.warning("device disconnected prematurely")
        except:  # noqa
            _LOGGER.error("exception occured while scanning devices")
            raise
        adv_data = delegate.get_adv_data()
        scan_data = delegate.get_scan_data()
        return {"adv": adv_data, "scan": scan_data}

    def get_services(self) -> List[ServiceData]:
        peripheral: btle.Peripheral = self.connect()
        if peripheral is None:
            return None
        services_list = get_services_data(peripheral)
        ServiceData.print_services(services_list)
        return services_list

    @synchronized
    def connect(self, reconnect=False) -> btle.Peripheral:
        if self._peripheral is not None and reconnect is False:
            return self._peripheral

        if self.addressType == "public":
            addr_type_set = (btle.ADDR_TYPE_PUBLIC, btle.ADDR_TYPE_RANDOM)
        else:
            addr_type_set = (btle.ADDR_TYPE_RANDOM, btle.ADDR_TYPE_PUBLIC)

        for addr_type in addr_type_set:
            _LOGGER.debug(f"connecting to device {self.address} type: {addr_type}")
            try:
                self._peripheral = btle.Peripheral()
                self._peripheral.withDelegate(self.connectDelegate)
                self._peripheral.connect(self.address, addrType=addr_type, iface=self.iface)
                self.addressType = str(addr_type)
                return self._peripheral
            except btle.BTLEException as ex:
                self._peripheral = None
                _LOGGER.debug("Unable to connect to the device %s, retrying: %s", self.address, ex)

        return None

    @synchronized
    def disconnect(self):
        _LOGGER.debug("Disconnecting")
        if self._peripheral is not None:
            self._peripheral.disconnect()
        self._peripheral = None

    ## ================================================================================

    @synchronized
    def read_characteristic(self, handle):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        return self._peripheral.readCharacteristic(handle)

    @synchronized
    def write_characteristic(self, handle: int, val):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        try:
            self._peripheral.writeCharacteristic(handle, val)
        except:  # noqa
            _LOGGER.error("error writing to characteristic: %#x %s", handle, val)
            raise

    @synchronized
    def subscribe_for_notification(self, handle: int, callback):
        data = struct.pack("BB", 1, 0)
        self.write_characteristic(handle, data)
        self.callbacks.register(handle, callback)

    @synchronized
    def unsubscribe_from_notification(self, handle: int, callback):
        data = struct.pack("BB", 0, 0)
        ret = self.write_characteristic(handle, data)
        self.callbacks.unregister(handle, callback)
        return ret

    @synchronized
    def subscribe_for_indication(self, handle: int, callback):
        data = struct.pack("BB", 2, 0)
        self.write_characteristic(handle, data)
        self.callbacks.register(handle, callback)

    @synchronized
    def unsubscribe_from_indication(self, handle: int, callback):
        data = struct.pack("BB", 0, 0)
        ret = self.write_characteristic(handle, data)
        self.callbacks.unregister(handle, callback)
        return ret

    def get_service_by_uuid(self, uuid: str):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        try:
            return self._peripheral.getServiceByUUID(uuid)
        except btle.BTLEGattError:
            _LOGGER.warning("service %s not found", uuid)
            return None

    ## ================================================================================

    @synchronized
    def process_notifications(self):
        if self._peripheral is None:
            return
        if self._peripheral.waitForNotifications(1.0):
            return
        # _LOGGER.debug("waiting for notifications...")


###
class ConnectDelegate(btle.DefaultDelegate):

    def __init__(self, callbacks=None):
        super().__init__()
        self.callbacks = callbacks

    def handleNotification(self, cHandle: int, data):
        try:
            _LOGGER.debug("Received new notification: %#x >%s<", cHandle, data)
            callbacks = self.callbacks.get(cHandle)
            if callbacks is None:
                # _LOGGER.debug("No callback found for notification handle: %#x", cHandle)
                return
            for function in callbacks:
                if function is not None:
                    function(data)
        except:  # noqa    # pylint: disable=W0702
            _LOGGER.exception("notification exception")

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        _LOGGER.debug("new discovery: %s %s %s", scanEntry, isNewDev, isNewData)


###
class ScanDelegate(btle.DefaultDelegate):

    def __init__(self, mac_filter=None):
        super().__init__()
        if mac_filter:
            mac_filter = mac_filter.lower()
        self.mac_filter = mac_filter

        self.addr_type: str = None  # public or random
        self.adv_dict = AdvertisementData()
        self.scan_dict = AdvertisementData()

    def get_adv_data(self) -> AdvertisementData:
        return self.adv_dict

    def get_scan_data(self) -> AdvertisementData:
        return self.scan_dict

    def handleNotification(self, cHandle: int, data):
        _LOGGER.debug("new notification: %#x >%s<", cHandle, data)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        if self.mac_filter:
            if self.mac_filter != scanEntry.addr:
                _LOGGER.debug(
                    "new discovery: %s RSSI=%s AddrType=%s (skipping)",
                    scanEntry.addr,
                    scanEntry.rssi,
                    scanEntry.addrType,
                )
                return

        _LOGGER.debug(
            "new discovery: %s RSSI=%s AddrType=%s %s %s",
            scanEntry.addr,
            scanEntry.rssi,
            scanEntry.addrType,
            isNewDev,
            isNewData,
        )
        if isNewDev:
            ## advertisement data
            self.addr_type = scanEntry.addrType
            for adtype, desc, value in scanEntry.getScanData():
                _LOGGER.debug(f"  {desc} ({adtype}) = {value}")
                ScanDelegate.append_to_dict(self.adv_dict, adtype, value)
        else:
            ## scan response data
            for adtype, desc, value in scanEntry.getScanData():
                if self.adv_dict.contains(adtype):
                    continue
                _LOGGER.debug(f"  {desc} ({adtype}) = {value}")
                ScanDelegate.append_to_dict(self.scan_dict, adtype, value)

    @staticmethod
    def append_to_dict(data_dict: AdvertisementData, adtype, value):
        ## Flags
        if adtype == 0x01:
            ## store in dict
            value = int(value, 16)
            data_dict.set_prop(adtype, value)

        ## Incomplete 16b Services
        elif adtype == 0x02:
            ## store in list
            data_container = data_dict.get_prop(adtype, [])
            data_container.append(value)
            data_dict.set_prop(adtype, data_container)

        ## Incomplete 128b Services
        elif adtype == 0x06:
            ## store in list
            data_container = data_dict.get_prop(adtype, [])
            data_container.append(value)
            data_dict.set_prop(adtype, data_container)

        ## Complete Local Name
        elif adtype == 0x09:
            ## store in dict
            data_dict.set_prop(adtype, value)

        ## Tx Power Level
        elif adtype == 0x0A:
            ## store in dict
            data_dict.set_prop(adtype, value)

        ## 16b Service Data
        elif adtype == 0x16:
            ## store in dict
            data_id = value[:4]
            data_id = data_id[2:4] + data_id[0:2]
            data_str = value[4:]
            data_container = data_dict.get_prop(adtype, {})
            data_container[data_id] = data_str
            data_dict.set_prop(adtype, data_container)

        ## Manufacturer
        elif adtype == 0xFF:
            ## store in dict
            data_id = value[:4]
            data_id = data_id[2:4] + data_id[0:2]
            data_id = int(data_id, 16)
            data_str = value[4:]
            data_container = data_dict.get_prop(adtype, {})
            data_container[data_id] = data_str
            data_dict.set_prop(adtype, data_container)

        else:
            # data_dict[ adtype ] = value
            _LOGGER.warning("unhandled adtype: %s", hex(adtype))
