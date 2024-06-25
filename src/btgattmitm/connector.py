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

import logging

from time import sleep
from threading import Thread


_LOGGER = logging.getLogger(__name__)


# =====================================================


class CharacteristicData:
    def __init__(self, char_uuid, char_name, char_handle, char_props):
        self._uuid = char_uuid
        self._common_name = char_name
        self._handle = char_handle
        self._props_list = char_props

    @property
    def uuid(self):
        return self._uuid

    def getCommonName(self):
        if self._common_name is None:
            return self.uuid
        return self._common_name

    @property
    def properties(self):
        return self._props_list

    def getHandle(self):
        return self._handle


class ServiceData:
    def __init__(self, service_uuid, service_name=None):
        self._uuid = service_uuid
        self._common_name = service_name
        self._chars_list = []

    @property
    def uuid(self):
        return self._uuid

    def getCommonName(self):
        if self._common_name is None:
            return self.uuid
        return self._common_name

    def getCharacteristics(self):
        return self._chars_list

    def add_characteristic(self, char_uuid, char_name, char_handle, char_props):
        char_data = CharacteristicData(char_uuid, char_name, char_handle, char_props)
        self._chars_list.append(char_data)

    def print_data(self):
        _LOGGER.debug("Service: %s [%s]", self.uuid, self.getCommonName())
        chars_list = self.getCharacteristics()
        for char_item in chars_list:
            _LOGGER.debug(
                "  Char: %s [%s] h:%i p:%s",
                char_item.uuid,
                char_item.getCommonName(),
                char_item.getHandle(),
                char_item.properties,
            )


# =====================================================


class AbstractConnector:
    def is_connected(self) -> bool:
        raise NotImplementedError()

    def get_address(self) -> str:
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    def get_device_properties(self):
        raise NotImplementedError()

    def get_services(self):
        raise NotImplementedError()

    def read_characteristic(self, handle):
        raise NotImplementedError()

    def write_characteristic(self, handle, val):
        raise NotImplementedError()

    def subscribe_for_notification(self, handle, callback):
        raise NotImplementedError()

    def unsubscribe_from_notification(self, handle, callback):
        raise NotImplementedError()

    def process_notifications(self):
        raise NotImplementedError()

    def print_services(self, serv_list):
        if not serv_list:
            _LOGGER.debug("no services")
            return
        _LOGGER.debug("Found services:")
        for serv in serv_list:
            serv.print_data()


# =====================================================


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


class NotificationHandler(Thread):
    def __init__(self, connector: AbstractConnector):
        Thread.__init__(self)
        self.connector: AbstractConnector = connector
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
