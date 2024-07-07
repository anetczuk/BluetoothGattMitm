#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
from typing import List

from gi.repository import GObject

# from gobject import gobject as GObject
# import gobject as GObject
# import dbus
import dbus.mainloop.glib

from btgattmitm.dbusobject.advertisement import AdvertisementManager
from btgattmitm.connector import NotificationHandler, AbstractConnector, ServiceData, AdvertisementData
from btgattmitm.gattmock import ApplicationMock
# from btgattmitm.dbusobject.agent import AgentManager


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

        self.agent = None
        # self.agent = AgentManager(self.bus)

    def configure_clone(self, connector: AbstractConnector, listenMode):
        """Configure service by cloning BT device."""

        _LOGGER.debug("Configuring MITM")
        if self.gatt_application is not None:
            valid = self.gatt_application.clone_services(connector, listenMode)
            if valid is False:
                _LOGGER.warning("unable to connect to device")
                return False

        ## register advertisement
        if self.advertisement is not None:
            adv_props: AdvertisementData = connector.get_device_properties()
            adv_dict = adv_props.get_dict()
            self._configure_advertisement(adv_dict)

        if self._notificationHandler is not None:
            self._notificationHandler.stop()
        self._notificationHandler = NotificationHandler(connector)

        return True

    def configure_config(self, device_config):
        """Configure service based on config dict."""

        _LOGGER.debug("Configuring device by config")
        if self.gatt_application is not None:
            services_dict = device_config.get("services", {})
            services_list = services_dict.values()
            services_list = list(services_list)
            valid = self.gatt_application.prepare_services(services_list)
            if valid is False:
                _LOGGER.warning("unable to configure services")
                return False

        ## register advertisement
        if self.advertisement is not None:
            configure_advertisement = device_config.get("advertisement", {})
            self._configure_advertisement(configure_advertisement)
        return True

    def _configure_advertisement(self, advertisement_config):
        ## register advertisement
        if self.advertisement is None:
            return

        dev_name = advertisement_config.get("LocalName")
        self.advertisement.set_local_name(dev_name)

        dev_uuids = advertisement_config.get("ServiceUUIDs", [])
        # if len(dev_uuids) < 4:
        #     # long UUIDs causes starting advertisement server to fail
        #     self.advertisement.add_service_uuid_list(dev_uuids)
        self.advertisement.add_service_uuid_list(dev_uuids)

        # # there is problem with long manufacturer data
        dev_manufacturer = advertisement_config.get("ManufacturerData", {})
        self.advertisement.add_manufacturer_data_dict(dev_manufacturer)

        dev_serv_data = advertisement_config.get("ServiceData", {})
        self.advertisement.add_service_data_dict(dev_serv_data)

    def configure_sample(self):
        _LOGGER.debug("Configuring sample")
        if self.gatt_application is not None:
            return self.gatt_application.prepare_sample()
        return False

    def start(self):
        ## register advertisement
        if self.advertisement is not None:
            self.advertisement.initialize()
            self.advertisement.register()

        if self.agent is not None:
            self.agent.initialize()

        if self.gatt_application is not None:
            self.gatt_application.register()

        _LOGGER.debug("Starting notification handler")
        if self._notificationHandler is not None:
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

    def get_advertisement_config(self):
        name = self.advertisement.local_name
        uuids = self.advertisement.service_uuids
        man_data = self.advertisement.manufacturer_data
        serv_data = self.advertisement.service_data
        adv_data = AdvertisementData(name, uuids, man_data, serv_data)
        return adv_data.get_dict()

    def get_services_config(self):
        return self.gatt_application.get_services_config()
