#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
import pprint

import dbus.service

from btgattmitm.constants import DBUS_OM_IFACE, DBUS_PROP_IFACE
from btgattmitm.constants import GATT_SERVICE_IFACE
from btgattmitm.dbusobject.exception import InvalidArgsException


_LOGGER = logging.getLogger(__name__)


class Service(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/service"

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        props = {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(self.get_characteristic_paths(), signature="o"),
            }
        }
        #         print( "returning props:", props )
        return props

    def get_path(self):
        path = dbus.ObjectPath(self.path)
        #         print( "returning path:", path )
        return path

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        #         print( "returning char paths:", result )
        return result

    def get_characteristics(self):
        #         print( "returning chars:", self.characteristics )
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        props = self.get_properties[GATT_SERVICE_IFACE]
        _LOGGER.info("returning service props:\n%s", pprint.pformat(props))
        return props

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        #         print('GetManagedObjects')

        response[self.get_path()] = self.get_properties()
        chrcs = self.get_characteristics()
        for chrc in chrcs:
            response[chrc.get_path()] = chrc.get_properties()
            descs = chrc.get_descriptors()
            for desc in descs:
                response[desc.get_path()] = desc.get_properties()
        #         print( "returning objects:", response )
        _LOGGER.info("returning characteristics:\n%s", pprint.pformat(response))
        return response
