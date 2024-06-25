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

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject
import dbus

from btgattmitm.dbusobject.service import Service
from btgattmitm.dbusobject.characteristic import Characteristic
from btgattmitm.constants import GATT_CHRC_IFACE, BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE
from btgattmitm.connector import ServiceData, AbstractConnector
from btgattmitm.dbusobject.application import Application
from btgattmitm.find_adapter import find_gatt_adapter


_LOGGER = logging.getLogger(__name__)


def to_hex_string(data):
    return " ".join("0x{:02X}".format(x) for x in data)


class CharacteristicMock(Characteristic):
    """
    classdocs
    """

    def __init__(self, btCharacteristic, bus, index, service, connector: AbstractConnector, listenMode):
        """
        Characteristic
        """
        self.connector: AbstractConnector = connector
        self.cHandler = btCharacteristic.getHandle()

        btUuid = btCharacteristic.uuid
        self.chUuid = str(btUuid)

        _LOGGER.debug(
            "Creating characteristic: %s[%s] %s",
            self.chUuid,
            btCharacteristic.getCommonName(),
            "0x{:02X}".format(self.cHandler),
        )

        flags = btCharacteristic.properties
        # flags = self._get_flags(btCharacteristic)
        Characteristic.__init__(self, bus, index, self.chUuid, flags, service)

        ## subscribe for notifications
        if listenMode:
            ncount = flags.count("notify") + flags.count("indicate")
            if ncount > 0:
                _LOGGER.debug("Subscribing for %s", self.chUuid)
                connector.subscribe_for_notification(self.cHandler, self._handle_notification)

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
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": vallist}, [])

    def _convert_data(self, data):
        if isinstance(data, str):
            ### convert string to byte array, required for Python2
            data = bytearray(data)
        return data


class ServiceMock(Service):
    """
    classdocs
    """

    def __init__(self, btService: ServiceData, bus, index, connector: AbstractConnector, listenMode):
        """
        Service
        """
        btUuid = btService.uuid
        serviceUuid = str(btUuid)

        _LOGGER.debug("Creating service: %s[%s]", serviceUuid, btService.getCommonName())

        Service.__init__(self, bus, index, serviceUuid, True)

        self._mock_characteristics(btService, bus, connector, listenMode)

    def __del__(self):
        pass

    def _mock_characteristics(self, btService: ServiceData, bus, connector: AbstractConnector, listenMode):
        charsList = btService.getCharacteristics()
        charIndex = 0
        for btCh in charsList:
            char = CharacteristicMock(btCh, bus, charIndex, self, connector, listenMode)
            self.add_characteristic(char)
            charIndex += 1

    # def register(self, gattManager):
    #     gattManager.RegisterService(
    #         self.get_path(), {}, reply_handler=self._register_service_cb, error_handler=self._register_service_error_cb
    #     )
    #
    # def _register_service_cb(self):
    #     _LOGGER.info("GATT service registered: uuid:%s", self.uuid)
    #
    # #         _LOGGER.info('GATT service registered: %s uuid:%s', self.__class__.__name__, self.uuid)
    #
    # def _register_service_error_cb(self, error):
    #     _LOGGER.error("Failed to register service: %s uuid:%s", str(error), self.uuid)


# ==================================================================


class BatteryService(Service):
    """
    Fake Battery service that emulates a draining battery.

    """

    BATTERY_UUID = "180f"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """
    Fake Battery Level characteristic. The battery level is drained by 2 points
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


class ApplicationMock(Application):
    """
    classdocs
    """

    def __init__(self, bus):
        """
        Application
        """
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

    def prepare(self, connector: AbstractConnector, listenMode):
        _LOGGER.debug("Getting services")
        serviceList = connector.get_services()
        if serviceList is None:
            _LOGGER.debug("Could not get list of services - adding sample service")

            # add sample service - otherwise application registering will fail
            service = BatteryService(self.bus, 0)
            self.add_service(service)
            return False

        _LOGGER.debug("Registering services")
        serviceIndex = -1
        for serv in serviceList:
            if serv.uuid == "00001800-0000-1000-8000-00805f9b34fb":
                ## causes Failed to register application: org.bluez.Error.Failed: Failed to create entry in database
                _LOGGER.debug("Skipping service: %s", serv.uuid)
                continue
            if serv.uuid == "00001801-0000-1000-8000-00805f9b34fb":
                ## causes Failed to register application: org.bluez.Error.Failed: Failed to create entry in database
                _LOGGER.debug("Skipping service: %s", serv.uuid)
                continue
            serviceIndex += 1
            service = ServiceMock(serv, self.bus, serviceIndex, connector, listenMode)
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
        _LOGGER.error("Failed to register application: " + str(error))
        ##mainloop.quit()
