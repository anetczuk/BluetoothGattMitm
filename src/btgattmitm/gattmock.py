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
from typing import List, Dict, Any
import struct

# try:
#     from gi.repository import GObject
# except ImportError:
#     import gobject as GObject
import dbus

from btgattmitm.dbusobject.service import Service
from btgattmitm.dbusobject.characteristic import Characteristic
from btgattmitm.constants import GATT_CHRC_IFACE, BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE
from btgattmitm.connector import ServiceData, ServiceConnector, CharacteristicData
from btgattmitm.dbusobject.application import Application
from btgattmitm.find_adapter import find_gatt_adapter


_LOGGER = logging.getLogger(__name__)


def to_hex_string(data):
    if isinstance(data, bytes):
        return data.hex()
    return " ".join("0x{:02X}".format(x) for x in data)


class CharacteristicMock(Characteristic):
    ## service - dbus service
    def __init__(
        self, btCharacteristic: CharacteristicData, bus, index: int, service: Service, connector: ServiceConnector
    ):
        btUuid = btCharacteristic.uuid
        chUuid = str(btUuid)
        cHandler = btCharacteristic.getHandle()
        flags = btCharacteristic.properties

        _LOGGER.debug(
            "Creating characteristic: %s[%s] h:%#x index:%#x flags: %s",
            chUuid,
            btCharacteristic.getCommonName(),
            cHandler,
            index,
            flags,
        )

        Characteristic.__init__(self, bus, index, chUuid, flags, service)

        ## instance of BluepyConnector
        self.connector: ServiceConnector = connector
        self.handler = cHandler

        ## subscribe for notifications
        if self.connector:
            if flags.count("notify") > 0:
                _LOGGER.debug("Subscribing for notification %s", chUuid)
                self.connector.subscribe_for_notification(self.handler, self.notification_callback)

            if flags.count("indicate") > 0:
                _LOGGER.debug("Subscribing for indication %s", chUuid)
                self.connector.subscribe_for_indication(self.handler, self.indication_callback)

    # def _handle_notification(self, data):
    #     data = bytearray(data)
    #     _LOGGER.debug("Received char %s notification data: [%s]", chUuid, to_hex_string(data))

    def readValueHandler(self):
        _LOGGER.debug("Client read request from %s", self.uuid)
        if self.connector is None:
            return None
        data = self.connector.read_characteristic(self.handler)
        # _LOGGER.debug("Got raw data: %s %s", data, type(data))
        # data = self._convert_data(data)
        if isinstance(data, int):
            data = [data]
        _LOGGER.debug("Client reads from %s: data: %s hex: %s", self.uuid, repr(data), to_hex_string(data))
        return data

    def writeValueHandler(self, value):
        ## convert 'dbus.Array' to bytes
        data = bytes()
        for val in value:
            data += struct.pack("B", val)
        _LOGGER.debug(
            "Client writes to %s [%#x]: data: %s hex: %s", self.uuid, self.handler, repr(data), to_hex_string(data)
        )
        # TODO: implement write without return

    def startNotifyHandler(self):
        ## notify has priority over indicate
        if "notify" in self.prop_flags:
            _LOGGER.debug("Client registering for notifications on %s [%#x]", self.uuid, self.handler)
            if not self.connector:
                return
            self.connector.subscribe_for_notification(self.handler, self.notification_callback)
        else:
            _LOGGER.debug("Client registering for indications on %s [%#x]", self.uuid, self.handler)
            if not self.connector:
                return
            self.connector.subscribe_for_indication(self.handler, self.notification_callback)

    def stopNotifyHandler(self):
        if self.connector:
            ret = self.connector.unsubscribe_from_notification(self.handler, self.notification_callback)
            _LOGGER.debug("Client unregistered from notifications on %s [%#x] %s", self.uuid, self.handler, ret)
        else:
            _LOGGER.debug("Client unregistered from notifications on %s [%#x]", self.uuid, self.handler)

    def notification_callback(self, value):
        _LOGGER.debug("Notification callback to client on %s data: %s", self.uuid, repr(value))
        self.send_notification(value)

    def indication_callback(self, value):
        _LOGGER.debug("Indication callback to client on %s data: %s", self.uuid, repr(value))
        self.send_notification(value)

    def send_notification(self, value):
        vallist = []
        for x in value:
            vallist.append(dbus.Byte(x))
        if not vallist:
            _LOGGER.debug("Unable to notify empty list")
            return
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": vallist}, [])

    def _convert_data(self, data):
        if isinstance(data, str):
            ### convert string to byte array, required for Python2
            data = bytearray(data)
        return data


class ServiceMock(Service):
    def __init__(self, btService: ServiceData, bus, index, connector: ServiceConnector):
        btUuid = btService.uuid
        serviceUuid = str(btUuid)

        _LOGGER.debug("Creating service: %s[%s]", serviceUuid, btService.getCommonName())

        Service.__init__(self, bus, index, serviceUuid, True)

        self._mock_characteristics(btService, bus, connector)

    def _mock_characteristics(self, btService: ServiceData, bus, connector: ServiceConnector):
        charsList: List[CharacteristicData] = btService.getCharacteristics()
        charIndex = 0
        for btCh in charsList:
            char = CharacteristicMock(btCh, bus, charIndex, self, connector)
            self.add_characteristic(char)
            charIndex += 1


# ==================================================================


# class ConfigConnector:
#     def __init__(self, config_list):
#         self.config_list = config_list
#         self.value_dict = {}
#         # read values
#         for service_item in self.config_list:
#             chars_list = service_item.get("characteristics")
#             for _item, char_item in chars_list.items():
#                 char_handle = char_item.get("handle")
#                 self.value_dict[char_handle] = char_item.get("value")
#
#     def get_services(self) -> List[ServiceData]:
#         serviceList: List[ServiceData] = ServiceData.prepare_from_config(self.config_list)
#         return serviceList
#
#     def read_characteristic(self, handle):
#         return self.value_dict[handle]
#
#     def write_characteristic(self, handle, val):
#         self.value_dict[handle] = val
#
#     def subscribe_for_notification(self, handle, callback):
#         pass
#         # raise NotImplementedError()
#
#     def unsubscribe_from_notification(self, handle, callback):
#         pass
#         # raise NotImplementedError()
#
#     def _find_config_item(self, handle):
#         for service_item in self.config_list:
#             chars_list = service_item.get("characteristics")
#             for char_item in chars_list:
#                 char_handle = char_item.get("handle")
#                 if char_handle == handle:
#                     return char_item
#         return None


class ApplicationMock(Application):
    def __init__(self, bus):
        self.bus = bus
        self.gattManager = None

        Application.__init__(self, self.bus)

        self._initManager()

    def _initManager(self):
        gatt_adapter = find_gatt_adapter(self.bus)
        if not gatt_adapter:
            _LOGGER.error("GattManager1 interface not found")
            return

        gattObj = self.bus.get_object(BLUEZ_SERVICE_NAME, gatt_adapter)
        self.gattManager = dbus.Interface(gattObj, GATT_MANAGER_IFACE)

    def configure_services(self, service_list: List[ServiceData], connector: ServiceConnector):
        _LOGGER.info("Mocking services")
        if service_list is None:
            _LOGGER.warning("Could not get list of services")
            return False

        serviceIndex = -1
        for serv in service_list:
            uuid = serv.uuid
            ## "bluetoothctl show" to display active services
            ##    00001800-0000-1000-8000-00805f9b34fb - Generic Access Profile
            ##    00001801-0000-1000-8000-00805f9b34fb - Generic Attribute Profile
            if uuid in ("00001800-0000-1000-8000-00805f9b34fb", "00001801-0000-1000-8000-00805f9b34fb"):
                ## causes Failed to register application: org.bluez.Error.Failed: Failed to create entry in database
                _LOGGER.debug("Skipping service: %s", uuid)
                continue
            serviceIndex += 1
            service = ServiceMock(serv, self.bus, serviceIndex, connector)
            self.add_service(service)

        ## subscribing for "Service Changed" indication
        if connector:
            char_handle = ServiceData.find_characteristic_handle(service_list, "00002a05-0000-1000-8000-00805f9b34fb")
            if char_handle is not None:
                _LOGGER.debug("Subscribing for indication of Service Changed")
                connector.subscribe_for_indication(char_handle, self._service_changed_callback)
        else:
            _LOGGER.warning("Unable to listen to 'Service Changed' - no connection")

        return True

    def _service_changed_callback(self):
        _LOGGER.info("Service changed!!!")

    def register(self):
        if self.gattManager is None:
            return
        _LOGGER.info("Registering application")
        ## register services
        # self._register_services_old()
        self._register_services_new()

    def unregister(self):
        ## do nothing
        pass

    ## useful when storing services to configuration file
    def get_services_config(self) -> Dict[str, Any]:
        services_data: List[ServiceData] = []
        for serv_item in self.services:
            serv_uuid = serv_item.uuid
            serv_name = "???"
            serv_data = ServiceData(serv_uuid, serv_name)
            chars_list: List[Characteristic] = serv_item.characteristics
            for char_item in chars_list:
                char_uuid = char_item.uuid
                char_name = "???"
                char_handle = char_item.handler
                char_props = char_item.get_properties_list()
                serv_data.add_characteristic(char_uuid, char_name, char_handle, char_props)
            services_data.append(serv_data)
        return ServiceData.dump_config(services_data)

    # def _register_services_old(self):
    #     for service in self.services:
    #         service.register(self.gattManager)

    def _register_services_new(self):
        self.gattManager.RegisterApplication(
            self.get_path(), {}, reply_handler=self.register_app_cb, error_handler=self.register_app_error_cb
        )

    def register_app_cb(self):
        _LOGGER.info("Application registered")

    def register_app_error_cb(self, error):
        _LOGGER.error("Failed to register application: %s", str(error))
        ##mainloop.quit()
