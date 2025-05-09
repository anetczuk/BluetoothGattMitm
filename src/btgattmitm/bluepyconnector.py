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
from typing import List

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


def get_services_data(peripheral) -> List[ServiceData]:
    _LOGGER.debug("getting services")
    services_list = peripheral.getServices()
    ret_list = []
    for serv in services_list:
        serv_uuid = serv.uuid
        serv_name = serv.uuid.getCommonName()
        _LOGGER.debug("Service: %s[%s]", serv_uuid, serv_name)
        serv_data = ServiceData(serv_uuid, serv_name)
        ret_list.append(serv_data)

        charsList = serv.getCharacteristics()
        for ch in charsList:
            _LOGGER.debug("Char: %s h:%i p:%s", ch, ch.getHandle(), ch.propertiesToString())
            char_uuid = ch.uuid
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
    def __init__(self, mac, iface=None):
        super().__init__()

        self.address = mac
        self.iface = iface
        self.callbacks = CallbackContainer()
        self.connectDelegate = ConnectDelegate( self.callbacks )
        self._peripheral = None

    def is_connected(self) -> bool:
        return self._peripheral is not None

    def get_address(self) -> str:
        return self.address

    def get_advertisement_data(self) -> List[AdvertisementData]:    
        return self._scan()

    @synchronized
    def _scan(self):
        delegate = ScanDelegate(self.address)
        scanner = btle.Scanner(iface=self.iface)
        scanner.withDelegate(delegate)
        scanner.scan(10.0)
        adv_data = delegate.get_adv_data()
        scan_data = delegate.get_scan_data()
        return [ adv_data, scan_data ]

    def get_services(self) -> List[ServiceData]:
        peripheral = self._connect()
        if peripheral is None:
            return None
        services_list = get_services_data(peripheral)
        ServiceData.print_services(services_list)
        return services_list

    @synchronized
    def _connect(self):
        if self._peripheral is not None:
            return self._peripheral

        addrType = btle.ADDR_TYPE_PUBLIC
        # addrType = btle.ADDR_TYPE_RANDOM
        _LOGGER.debug(f"connecting to device {self.address} type: {addrType}")
        for _try in range(0, 2):
            try:
                conn = btle.Peripheral()
                conn.withDelegate( self.connectDelegate )
                conn.connect(self.address, addrType=addrType, iface=self.iface)
                _LOGGER.debug("connected")
                self._peripheral = conn
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

    @synchronized
    def write_characteristic(self, handle, val):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        self._peripheral.writeCharacteristic(handle, val)

    @synchronized
    def read_characteristic(self, handle):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        return self._peripheral.readCharacteristic(handle)

    @synchronized
    def subscribe_for_notification(self, handle, callback):
        data = struct.pack("BB", 1, 0)
        self.write_characteristic(handle, data)
        self.callbacks.register(handle, callback)

    @synchronized
    def unsubscribe_from_notification(self, handle, callback):
        data = struct.pack("BB", 0, 0)
        ret = self.write_characteristic(handle, data)
        self.callbacks.unregister(handle, callback)
        return ret

    @synchronized
    def process_notifications(self):
        if self._peripheral is not None:
            self._peripheral.waitForNotifications(0.1)


###
class ConnectDelegate(btle.DefaultDelegate):

    def __init__(self, callbacks=None):
        super().__init__()
        self.callbacks = callbacks

    def handleNotification(self, cHandle, data):
        try:
            ## _LOGGER.debug("new notification: %s >%s<", cHandle, data)
            callbacks = self.callbacks.get(cHandle)
            if callbacks is None:
                ##_LOGGER.debug("no callback found for handle: %i", cHandle)
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
        self.adv_dict = {}
        self.scan_dict = {}

    def get_adv_data(self) -> AdvertisementData:
        return AdvertisementData(self.adv_dict)

    def get_scan_data(self) -> AdvertisementData:
        return AdvertisementData(self.scan_dict)

    def handleNotification(self, cHandle, data):
        _LOGGER.debug("new notification: %s >%s<", cHandle, data)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        if self.mac_filter:
            if self.mac_filter != scanEntry.addr:
                return
        _LOGGER.debug("new discovery: %s RSSI=%s AddrType=%s %s %s",
                      scanEntry.addr, scanEntry.rssi, scanEntry.addrType, isNewDev, isNewData)
        if isNewDev:
            ## advertisement data
            for (adtype, desc, value) in scanEntry.getScanData():
                _LOGGER.debug(f"  {desc} ({adtype}) = {value}")
                ScanDelegate.append_to_dict( self.adv_dict, adtype, value )
        else:
            ## scan response data
            for (adtype, desc, value) in scanEntry.getScanData():
                if adtype in self.adv_dict:
                    continue
                _LOGGER.debug(f"  {desc} ({adtype}) = {value}")
                ScanDelegate.append_to_dict( self.scan_dict, adtype, value )

    @staticmethod
    def append_to_dict(data_dict, adtype, value):
        #data_dict[ adtype ] = value

        ## Flags
        if adtype == 1:
            ## store in dict
            data_dict[ adtype ] = int(value, 16)

        elif adtype == 2:
            ## Incomplete 16b Services
            ## store in list
            data_container = data_dict.get(adtype, [])
            data_container.append( value )
            data_dict[ adtype ] = data_container

        ## Complete Local Name
        elif adtype == 9:
            ## store in dict
            data_dict[ adtype ] = value

        ## 16b Service Data
        elif adtype == 22:
            ## store in dict
            data_id = value[:4]
            data_id = data_id[2:4] + data_id[0:2]
            data_str = value[4:]
            bytes_list = list(bytes.fromhex(data_str))
            data_container = data_dict.get(adtype, {})
            data_container[data_id] = bytes_list
            data_dict[ adtype ] = data_container

        ## Manufacturer
        elif adtype == 255:
            ## store in dict
            data_id = value[:4]
            data_id = data_id[2:4] + data_id[0:2]
            data_id = int(data_id, 16)
            data_str = value[4:]
            bytes_list = list(bytes.fromhex(data_str))
            data_container = data_dict.get(adtype, {})
            data_container[data_id] = bytes_list
            data_dict[ adtype ] = data_container            
            
        else:
            #data_dict[ adtype ] = value
            _LOGGER.warning("unhandled adtype: %s", adtype)
