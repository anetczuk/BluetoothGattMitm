#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
from typing import List
import pprint

import dbus

from btgattmitm.constants import DBUS_OM_IFACE
from btgattmitm.dbusobject.service import Service


_LOGGER = logging.getLogger(__name__)


class Application(dbus.service.Object):
    PATH_BASE = "/org/bluez/example"

    """
    org.bluez.GattApplication1 interface implementation
    """

    def __init__(self, bus):
        _LOGGER.debug("Initializing Application")
        self.path = self.PATH_BASE
        self.services: List[Service] = []
        dbus.service.Object.__init__(self, bus, self.path)

    def add_service(self, service: Service):
        self.services.append(service)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        ##_LOGGER.debug("Application::GetManagedObjects: %r", self.services)

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()
        _LOGGER.info("returning services:\n%s", pprint.pformat(response))
        return response
