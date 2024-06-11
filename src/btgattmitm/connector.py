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

from time import sleep
from threading import Thread

from bluepy import btle

from .synchronized import synchronized
from .exception import InvalidStateError


_LOGGER = logging.getLogger(__name__)


class CallbackContainer:
    def __init__(self):
        self.container = {}

    def register(self, handle, callback):
        handlers = self.get(handle)
        if handlers is None:
            handlers = set()
            self.container[handle] = handlers
        handlers.add(callback)

    def unregister(self, handle, callback):
        handlers = self.get(handle)
        if handlers is None:
            return
        handlers.discard(callback)

    def get(self, handle):
        if handle in self.container:
            return self.container[handle]
        return None


class BluepyConnector(btle.DefaultDelegate):
    """
    classdocs
    """

    def __init__(self, mac):
        """
        Constructor
        """
        btle.DefaultDelegate.__init__(self)

        self.address = mac
        self._peripheral = None
        self.callbacks = CallbackContainer()

    #     def __del__(self):
    #         print("destroying", self.__class__.__name__)

    def get_services(self):
        peripheral = self._connect()
        if peripheral is None:
            return None
        _LOGGER.debug("getting services")
        return peripheral.getServices()

    def print_services(self):
        _LOGGER.debug("Discovering services")
        peripheral = self._connect()
        if peripheral is None:
            return
        serviceList = peripheral.getServices()
        for s in serviceList:
            _LOGGER.debug("Service: %s[%s]", s.uuid, s.uuid.getCommonName())
            charsList = s.getCharacteristics()
            for ch in charsList:
                _LOGGER.debug("Char: %s h:%i p:%s", ch, ch.getHandle(), ch.propertiesToString())

    #             descList = s.getDescriptors()
    #             for desc in descList:
    # #                 _LOGGER.debug("Desc: %s: %s", desc, desc.read())
    # #                 _LOGGER.debug("Desc: %s %s %s", desc, dir(desc), vars(desc) )
    # #                 _LOGGER.debug("Desc: %s uuid:%s h:%i v:%s", desc, desc.uuid, desc.handle, desc.read() )
    #                 _LOGGER.debug("Desc: %s uuid:%s h:%i", desc, desc.uuid, desc.handle )

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
    def write_characteristic(self, handle, val, withResponse=False):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        return self._peripheral.writeCharacteristic(handle, val, withResponse)

    @synchronized
    def read_characteristic(self, handle):
        if self._peripheral is None:
            raise InvalidStateError("not connected")
        return self._peripheral.readCharacteristic(handle)

    @synchronized
    def subscribe_for_notification(self, handle, callback):
        data = struct.pack("BB", 1, 0)
        ret = self.write_characteristic(handle, data)
        self.callbacks.register(handle, callback)
        return ret

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


class NotificationHandler(Thread):
    def __init__(self, connector):
        Thread.__init__(self)
        self.connector = connector
        self.daemon = True
        self.execute = True

    def stop(self):
        _LOGGER.info("Stopping notify handler")
        self._stop_loop()
        self.join()

    def run(self):
        try:
            _LOGGER.info("Starting notify handler")
            self.execute = True
            while self.execute:
                try:
                    self.connector.process_notifications()
                except:  # noqa    # pylint: disable=W0702
                    _LOGGER.exception("Exception occurred")
                    self._stop_loop()
                sleep(0.001)  ## prevents starving other thread
        finally:
            _LOGGER.info("Notification handler run loop stopped")

    def _stop_loop(self):
        self.execute = False
