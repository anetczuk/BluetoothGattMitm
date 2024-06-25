#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging

from gi.repository import GObject

# from gobject import gobject as GObject
# import gobject as GObject
# import dbus
import dbus.mainloop.glib

from btgattmitm.dbusobject.advertisement import AdvertisementManager
from btgattmitm.connector import NotificationHandler, AbstractConnector
from btgattmitm.gattmock import ApplicationMock
from btgattmitm.dbusobject.agent import AgentManager


_LOGGER = logging.getLogger(__name__)


class MitmManager:
    """
    classdocs
    """

    def __init__(self):
        """
        MITM manager
        """

        ## required for Python threading to work
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        _LOGGER.debug("Initializing MITM manager")

        self.mainloop = None

        self.bus = dbus.SystemBus()

        self._notificationHandler = None

        self.gatt_application = ApplicationMock(self.bus)

        self.advertisement = AdvertisementManager(self.bus, 0)
        # self.advertisement.set_local_name("DESK 2256")

        self.agent = AgentManager(self.bus)

    def configure(self, connector: AbstractConnector, listenMode):
        _LOGGER.debug("Configuring MITM")
        if self.gatt_application is not None:
            valid = self.gatt_application.prepare(connector, listenMode)
            if valid is False:
                if connector.get_address() is not None:
                    _LOGGER.warning("unable to connect to device")
                    return False

        ## register advertisement
        if self.advertisement is not None:
            dev_props = connector.get_device_properties()

            if dev_props:
                dev_uuids = dev_props.get("UUIDs", [])
                if len(dev_uuids) < 4:
                    # long UUIDs causes starting advertisement server to fail
                    self.advertisement.add_service_uuid_list(dev_uuids)
                # self.advertisement.add_service_uuid("99fa0001-338a-1024-8a49-009c0215f78a")
                # self.advertisement.add_service_uuid("FD50")

                # # there is problem with long manufacturer data
                # dev_manufacturer = dev_props.get("ManufacturerData", {})
                # self.advertisement.add_manufacturer_data_dict(dev_manufacturer)

                dev_serv_data = dev_props.get("ServiceData", {})
                self.advertisement.add_service_data_dict(dev_serv_data)

            self.advertisement.initialize()
            self.advertisement.register()

        if self.agent is not None:
            self.agent.initialize()

        if self.gatt_application is not None:
            self.gatt_application.register()
        return True

    def start(self, connector: AbstractConnector):
        _LOGGER.debug("Starting notification handler")
        if self._notificationHandler is not None:
            self._notificationHandler.stop()
        self._notificationHandler = NotificationHandler(connector)
        self._notificationHandler.start()

        _LOGGER.debug("Starting main loop")
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()

    def stop(self):
        _LOGGER.debug("Stopping MITM")
        if self._notificationHandler is not None:
            self._notificationHandler.stop()

        if self.advertisement is not None:
            self.advertisement.unregister()

        if self.gatt_application is not None:
            self.gatt_application.unregister()

        self.mainloop = None
