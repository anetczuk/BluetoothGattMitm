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
from typing import List

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import dbus

from btgattmitm.dbusobject.service import Service
from btgattmitm.dbusobject.characteristic import Characteristic
from btgattmitm.constants import GATT_CHRC_IFACE, BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE
from btgattmitm.connector import ServiceData, AbstractConnector, ServiceConnector, CharacteristicData
from btgattmitm.dbusobject.application import Application
from btgattmitm.find_adapter import find_gatt_adapter


_LOGGER = logging.getLogger(__name__)


def to_hex_string(data):
    return " ".join("0x{:02X}".format(x) for x in data)


class CharacteristicMock(Characteristic):
    def __init__(
        self, btCharacteristic: CharacteristicData, bus, index, service, connector: ServiceConnector, listenMode
    ):
        self.connector: ServiceConnector = connector
        self.cHandler = btCharacteristic.getHandle()

        btUuid = btCharacteristic.uuid
        self.chUuid = str(btUuid)

        handler_hex = "0x{:02X}".format(self.cHandler)
        _LOGGER.debug(f"Creating characteristic: {self.chUuid}[{btCharacteristic.getCommonName()}] {handler_hex}")

        flags = btCharacteristic.properties
        # flags = self._get_flags(btCharacteristic)
        Characteristic.__init__(self, bus, index, self.chUuid, flags, service)

        ## subscribe for notifications
        if listenMode:
            ncount = flags.count("notify") + flags.count("indicate")
            if ncount > 0:
                _LOGGER.debug("Subscribing for %s", self.chUuid)
                self.connector.subscribe_for_notification(self.cHandler, self._handle_notification)

    def __del__(self):
        pass

    def _handle_notification(self, data):
        data = bytearray(data)
        _LOGGER.debug("Received char %s notification data: [%s]", self.chUuid, to_hex_string(data))

    def readValueHandler(self):
        _LOGGER.debug("Client read request from %s", self.chUuid)
        data = self.connector.read_characteristic(self.cHandler)
        # data = self._convert_data(data)
        _LOGGER.debug("Client reads from %s: data: %s hex: %s", self.chUuid, repr(data), to_hex_string(data))
        return data

    def writeValueHandler(self, value):
        _LOGGER.debug("Client write request to %s", self.chUuid)
        ## repr(unwrapped), [hex(no) for no in unwrapped]
        # data = bytes()
        # for val in value:
        #     data += struct.pack("B", val)
        self.connector.write_characteristic(self.cHandler, value)
        # TODO: implement write without return
        _LOGGER.debug("Client writes to %s: data: %s hex: %s", self.chUuid, repr(value), to_hex_string(value))

    def startNotifyHandler(self):
        self.connector.subscribe_for_notification(self.cHandler, self.notification_callback)
        _LOGGER.debug("Client registered for notifications on %s [%s]", self.chUuid, self.cHandler)

    def stopNotifyHandler(self):
        ret = self.connector.unsubscribe_from_notification(self.cHandler, self.notification_callback)
        _LOGGER.debug("Client unregistered from notifications on %s [%s] %s", self.chUuid, self.cHandler, ret)

    def notification_callback(self, value):
        _LOGGER.debug("Notification callback to client on %s data: %s", self.chUuid, repr(value))
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
    def __init__(self, btService: ServiceData, bus, index, connector: ServiceConnector, listenMode):
        btUuid = btService.uuid
        serviceUuid = str(btUuid)

        _LOGGER.debug("Creating service: %s[%s]", serviceUuid, btService.getCommonName())

        Service.__init__(self, bus, index, serviceUuid, True)

        self._mock_characteristics(btService, bus, connector, listenMode)

    def __del__(self):
        pass

    def _mock_characteristics(self, btService: ServiceData, bus, connector: ServiceConnector, listenMode):
        charsList: List[CharacteristicData] = btService.getCharacteristics()
        charIndex = 0
        for btCh in charsList:
            char = CharacteristicMock(btCh, bus, charIndex, self, connector, listenMode)
            self.add_characteristic(char)
            charIndex += 1


# ==================================================================


class BatteryService(Service):
    """Fake Battery service that emulates a draining battery."""

    BATTERY_UUID = "180f"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """
    Fake Battery Level characteristic.

    The battery level is drained by 2 points
    every 5 seconds.
    """

    BATTERY_LVL_UUID = "2a19"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.BATTERY_LVL_UUID, ["read", "notify"], service)
        self.notifying = False
        self.battery_lvl = 100
        GObject.timeout_add(5000, self.drain_battery)

    def drain_battery(self):
        if not self.notifying:
            return True
        if self.battery_lvl > 0:
            self.battery_lvl -= 2
            if self.battery_lvl < 0:
                self.battery_lvl = 100
        _LOGGER.info("Battery Level drained: %s", repr(self.battery_lvl))
        self.notify_battery_level()
        return True

    def notify_battery_level(self):
        if not self.notifying:
            return
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": [dbus.Byte(self.battery_lvl)]}, [])

    def readValueHandler(self):
        _LOGGER.info("Battery Level read: %s", repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def startNotifyHandler(self):
        if self.notifying:
            _LOGGER.info("Already notifying, nothing to do")
            return

        self.notifying = True
        self.notify_battery_level()

    def stopNotifyHandler(self):
        if not self.notifying:
            _LOGGER.info("Not notifying, nothing to do")
            return

        self.notifying = False


# ==================================================================


class ConfigConnector(ServiceConnector):
    def __init__(self, config_list):
        self.config_list = config_list
        self.value_dict = {}
        # read values
        for service_item in self.config_list:
            chars_list = service_item.get("characteristics")
            for _, char_item in chars_list.items():
                char_handle = char_item.get("handle")
                self.value_dict[char_handle] = char_item.get("value")

    def read_characteristic(self, handle):
        return self.value_dict[handle]

    def write_characteristic(self, handle, val):
        self.value_dict[handle] = val

    def subscribe_for_notification(self, handle, callback):
        pass
        # raise NotImplementedError()

    def unsubscribe_from_notification(self, handle, callback):
        pass
        # raise NotImplementedError()

    def _find_config_item(self, handle):
        for service_item in self.config_list:
            chars_list = service_item.get("characteristics")
            for char_item in chars_list:
                char_handle = char_item.get("handle")
                if char_handle == handle:
                    return char_item
        return None


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

    def clone_services(self, connector: AbstractConnector, listenMode: bool):
        _LOGGER.debug("Getting services")
        serviceList: List[ServiceData] = connector.get_services()
        if serviceList is None:
            _LOGGER.debug("Could not get list of services")
            return False
        _LOGGER.debug("Mocking services from device")
        self._mock_services(connector, listenMode, serviceList)
        return True

    def prepare_services(self, services_cfg_list):
        _LOGGER.debug("Mocking services from config")
        connector = ConfigConnector(services_cfg_list)
        serviceList: List[ServiceData] = ServiceData.prepare_from_config(services_cfg_list)
        self._mock_services(connector, False, serviceList)
        return True

    def _mock_services(self, connector: ServiceConnector, listenMode: bool, serviceList):
        _LOGGER.debug("Registering services")
        serviceIndex = -1
        for serv in serviceList:
            uuid = serv.uuid
            if uuid in ("00001800-0000-1000-8000-00805f9b34fb", "00001801-0000-1000-8000-00805f9b34fb"):
                ## causes Failed to register application: org.bluez.Error.Failed: Failed to create entry in database
                _LOGGER.debug("Skipping service: %s", uuid)
                continue
            serviceIndex += 1
            service = ServiceMock(serv, self.bus, serviceIndex, connector, listenMode)
            self.add_service(service)

    def prepare_sample(self):
        _LOGGER.debug("Adding sample service")
        # add sample service - otherwise application registering will fail
        service = BatteryService(self.bus, 0)
        self.add_service(service)
        return True

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

    def get_services_config(self):
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
