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
from typing import List, Dict, Any
import pprint
import asyncio

from bleak import BleakClient, BleakScanner

from btgattmitm.synchronized import synchronized
from btgattmitm.dbusobject.exception import InvalidStateError
from btgattmitm.connector import AbstractConnector, CallbackContainer, ServiceData, AdvertisementData


_LOGGER = logging.getLogger(__name__)


class SyncedBleakDevice:
    def __init__(self):
        self._client = None
        self.device_props = None
        self.running_loop = asyncio.new_event_loop()

    def is_connected(self) -> bool:
        return self._client is not None

    def connect(self, mac):
        coroutine = self._async_connect(mac)
        self.running_loop.run_until_complete(coroutine)

    def disconnect(self):
        pass

    def getServices(self) -> List[ServiceData]:
        coroutine = self._async_get_services()
        return self.running_loop.run_until_complete(coroutine)

    def writeCharacteristic(self, handle, val):
        coroutine = self._async_writeCharacteristic(handle, val)
        return self.running_loop.run_until_complete(coroutine)

    def readCharacteristic(self, handle):
        coroutine = self._async_readCharacteristic(handle)
        return self.running_loop.run_until_complete(coroutine)

    def waitForNotifications(self, timeout):
        coroutine = asyncio.sleep(timeout)
        return self.running_loop.run_until_complete(coroutine)

    def startNotify(self, handle, callback):
        coroutine = self._async_start_notify(handle, callback)
        return self.running_loop.run_until_complete(coroutine)

    # =================================================

    async def _async_connect(self, address):
        # devices = await BleakScanner.discover()
        # for dev in devices:
        #     _LOGGER.info(f"found {dev.metadata}")

        device = await BleakScanner.find_device_by_address(device_identifier=address, timeout=5.0)
        if device is None:
            _LOGGER.warning(f"unable to find device {address}")
            self._client = None
            return

        _LOGGER.info(f"found {device}")
        _LOGGER.info(f"device details:\n{pprint.pformat(device.details)}")
        _LOGGER.info(f"device metadata:\n{pprint.pformat(device.metadata)}")
        self.device_props = device.details.get("props", {})
        # self.device_props = device.metadata

        self._client = BleakClient(device)
        await self._client.connect()

    async def _async_get_services(self):
        try:
            ret_list = []
            services_list = self._client.services
            for serv in services_list:
                serv_uuid = serv.uuid
                serv_name = serv.description
                # _LOGGER.debug("Service: %s[%s]", serv_uuid, serv_name)
                serv_data = ServiceData(serv_uuid, serv_name)
                ret_list.append(serv_data)

                charsList = serv.characteristics
                for char_item in charsList:
                    char_uuid = char_item.uuid
                    char_name = char_item.description
                    char_handle = char_item.handle
                    char_props = char_item.properties
                    # _LOGGER.debug("Char: %s p:%s", char_item, char_props_str)
                    serv_data.add_characteristic(char_uuid, char_name, char_handle, char_props)
            return ret_list
        except Exception:
            _LOGGER.exception("exception occur")
            raise

    async def _async_readCharacteristic(self, handler):
        try:
            return await self._client.read_gatt_char(handler)
        except Exception:
            _LOGGER.exception("exception occur")
            raise

    async def _async_writeCharacteristic(self, handler, value):
        try:
            return await self._client.write_gatt_char(handler, value)
        except Exception:
            _LOGGER.exception("exception occur")
            raise

    async def _async_start_notify(self, handler, callback):
        try:
            return await self._client.start_notify(handler, callback)
        except Exception:  # noqa
            _LOGGER.exception("exception occur")
            raise


class BleakConnector(AbstractConnector):
    def __init__(self, mac):
        super().__init__()

        self.address = mac
        self.callbacks = CallbackContainer()
        self._peripheral: SyncedBleakDevice = None

    def is_connected(self) -> bool:
        return self._peripheral is not None

    def get_address(self) -> str:
        return self.address

    def get_advertisement_data(self) -> List[AdvertisementData]:
        if self._peripheral is None:
            return None
        bleak_props = self._peripheral.device_props
        props: Dict[int, Any] = {}

        for key, _val in bleak_props.items():
            # TODO: implement
            _LOGGER.warning("unhandled property: %s", key)

        # props["LocalName"] = bleak_props.get("Name")
        # props["ServiceUUIDs"] = bleak_props.get("UUIDs", [])
        # props["ManufacturerData"] = bleak_props.get("ManufacturerData", {})
        # props["ServiceData"] = bleak_props.get("ServiceData", {})
        return [AdvertisementData(props)]

    def get_services(self) -> List[ServiceData]:
        peripheral = self._connect()
        if peripheral is None:
            return None
        services_list: List[ServiceData] = peripheral.getServices()
        ServiceData.print_services(services_list)
        return services_list

    @synchronized
    def _connect(self):
        if self._peripheral is not None:
            return self._peripheral

        if self.address is None:
            return None

        _LOGGER.debug("Connecting to device: %s", self.address)
        peripheral = SyncedBleakDevice()
        peripheral.connect(self.address)

        if peripheral.is_connected():
            self._peripheral = peripheral
        return self._peripheral

    @synchronized
    def disconnect(self):
        _LOGGER.debug("Disconnecting")
        if self._peripheral is not None:
            self._peripheral.disconnect()
        self._peripheral = None

    def handleNotification(self, cHandle: int, data):
        try:
            ## _LOGGER.debug("new notification: %#x >%s<", cHandle, data)
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
        value = self._peripheral.readCharacteristic(handle)
        # _LOGGER.info(f"bleak received value {value} from handler {handle}")
        return value

    @synchronized
    def subscribe_for_notification(self, handle, callback):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        self._peripheral.startNotify(handle, lambda char_obj, value: callback(value))
        # self._peripheral.startNotify(handle, callback)
        # data = struct.pack("BB", 1, 0)
        # self.write_characteristic(handle, data)
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
