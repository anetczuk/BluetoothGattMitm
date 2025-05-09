#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
from typing import List, Any, Dict

from gi.repository import GObject

# from gobject import gobject as GObject
# import gobject as GObject
# import dbus
import dbus.mainloop.glib

from btgattmitm.dbusobject.advertisement import AdvertisementManager
from btgattmitm.connector import NotificationHandler, AbstractConnector, AdvertisementData
from btgattmitm.gattmock import ApplicationMock

# from btgattmitm.dbusobject.agent import AgentManager


_LOGGER = logging.getLogger(__name__)


class MitmManager:
    def __init__(self):
        ## required for Python threading to work
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        _LOGGER.debug("Initializing MITM manager")

        self.mainloop = None

        self.bus = dbus.SystemBus()

        self._notificationHandler = None

        self.gatt_application = ApplicationMock(self.bus)

        #TODO: should 'iface' cmd parameter should be used here?
        self.advertisement = AdvertisementManager(self.bus, 0)

        self.agent = None
        # self.agent = AgentManager(self.bus)

    def configure_clone(self, connector: AbstractConnector, listenMode):
        """Configure service by cloning BT device."""
        _LOGGER.debug("Configuring MITM")

        ## register advertisement
        if self.advertisement is not None:
            _LOGGER.debug("Reading advertisement data")
            adv_props_list: List[AdvertisementData] = connector.get_advertisement_data()
            if adv_props_list is not None:
                adv_data: AdvertisementData = adv_props_list[0]
                self._configure_advertisement(adv_data)

                scanresp_data: AdvertisementData = adv_props_list[1]
                self._configure_scanresponse(scanresp_data)
            else:
                _LOGGER.debug("Unable to configure advertisement - missing device properties")

        if self.gatt_application is not None:
            _LOGGER.debug("Reading GATT data")
            valid = self.gatt_application.clone_services(connector, listenMode)
            if valid is False:
                _LOGGER.warning("unable to connect to device")
                return False

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
            adv_dict = device_config.get("advertisement", {})
            adv_data: AdvertisementData = AdvertisementData(adv_dict)
            self._configure_advertisement(adv_data)

        ## register scan response
        if self.advertisement is not None:
            scanresp_dict = device_config.get("scanresponse", {})
            scanresp_data: AdvertisementData = AdvertisementData(scanresp_dict)
            self._configure_scanresponse(scanresp_data)

        return True

    def _configure_advertisement(self, adv_data: AdvertisementData):
        ## register advertisement
        if self.advertisement is None:
            return
        self.advertisement.add_adv_data( adv_data )

    def _configure_scanresponse(self, scanresp_data: AdvertisementData):
        ## register advertisement
        if self.advertisement is None:
            return
        self.advertisement.add_scanresp_data( scanresp_data )

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

    def get_adv_config(self) -> Dict[int, Any]:
        if self.advertisement is None:
            return {}
        adv_data: AdvertisementData = self.advertisement.get_adv_data()
        return adv_data.get_props()

    def get_scanresp_config(self):
        if self.advertisement is None:
            return {}
        scanresp_data: AdvertisementData = self.advertisement.get_scanresp_data()
        return scanresp_data.get_props()

    def get_services_config(self):
        return self.gatt_application.get_services_config()
