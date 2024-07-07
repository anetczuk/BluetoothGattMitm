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
from btgattmitm.connector import AbstractConnector, CallbackContainer, ServiceData


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
    0b00100000: "indicate"
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


class BluepyConnector(btle.DefaultDelegate, AbstractConnector):
    """
    classdocs
    """

    def __init__(self, mac):
        """
        Constructor
        """
        super().__init__()

        self.address = mac
        self.callbacks = CallbackContainer()
        self._peripheral = None

    def is_connected(self) -> bool:
        return self._peripheral is not None

    def get_address(self) -> str:
        return self.address

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

        # addrType = btle.ADDR_TYPE_PUBLIC
        addrType = btle.ADDR_TYPE_RANDOM
        _LOGGER.debug(f"connecting to device {self.address} type: {addrType}")
        for _ in range(0, 2):
            try:
                conn = btle.Peripheral()
                conn.withDelegate(self)
                conn.connect(self.address, addrType=addrType)
                # conn.connect(self.address, addrType=btle.ADDR_TYPE_RANDOM)
                # conn.connect(self.address, addrType='random')
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
