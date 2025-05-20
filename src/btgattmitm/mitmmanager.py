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

from btgattmitm.connector import NotificationHandler, AbstractConnector, AdvertisementData, ServiceData
from btgattmitm.gattmock import ApplicationMock
from btgattmitm.advertisementmanager import AdvertisementManager

# from btgattmitm.dbusobject.advertisement import DBusAdvertisementManager
# from btgattmitm.hcitool.advertisement import HciToolAdvertisementManager
from btgattmitm.btmgmt.advertisement import BtmgmtAdvertisementManager

# from btgattmitm.dbusobject.agent import AgentManager


_LOGGER = logging.getLogger(__name__)


class MitmManager:
    def __init__(self, iface_index=0, sudo_mode=False):
        ## required for Python threading to work
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        _LOGGER.info("Initializing MITM manager")

        self.mainloop = None

        self.bus = dbus.SystemBus()

        self._notificationHandler: NotificationHandler = None

        self.gatt_application = ApplicationMock(self.bus)

        self.advertisement: AdvertisementManager = None
        self.advertisement = BtmgmtAdvertisementManager(iface_index, sudo_mode=sudo_mode)
        # self.advertisement = HciToolAdvertisementManager(iface_index, sudo_mode=sudo_mode)
        # self.advertisement = DBusAdvertisementManager(self.bus, iface_index)

        self.agent = None
        # self.agent = AgentManager(self.bus)

    def configure(self, connector: AbstractConnector, device_config: Dict[str, Any]):
        """Configure MITM service."""
        _LOGGER.info("Configuring MITM")

        ## register advertisement
        if self.advertisement is not None:
            adv_data: AdvertisementData = None
            scanresp_data: AdvertisementData = None
            if device_config:
                _LOGGER.info("Reading advertisement data from config")
                adv_dict = device_config.get("advertisement", {})
                adv_data = AdvertisementData(adv_dict)
                self._configure_advertisement(adv_data)
                scanresp_dict = device_config.get("scanresponse", {})
                scanresp_data = AdvertisementData(scanresp_dict)
                self._configure_scanresponse(scanresp_data)
            elif connector:
                _LOGGER.info("Reading advertisement data from device")
                adv_props_list: List[AdvertisementData] = connector.get_advertisement_data()
                if adv_props_list is not None:
                    adv_data = adv_props_list[0]
                    _LOGGER.debug("Found advertisement data: %s", adv_data.get_props())
                    self._configure_advertisement(adv_data)

                    scanresp_data = adv_props_list[1]
                    _LOGGER.debug("Found scan response data: %s", scanresp_data.get_props())
                    self._configure_scanresponse(scanresp_data)
                else:
                    _LOGGER.warning("Unable to configure advertisement - missing device properties")
            else:
                _LOGGER.warning("Unable to configure advertisement")
        else:
            _LOGGER.warning("Skipping advertisement")

        ## register services
        if self.gatt_application is not None:
            service_list: List[ServiceData] = None
            if device_config:
                _LOGGER.info("Reading GATT services data from config")
                services_dict = device_config.get("services", {})
                services_data = services_dict.values()
                services_data = list(services_data)
                service_list = ServiceData.prepare_from_config(services_data)
                if connector:
                    connector.connect()
                valid = self.gatt_application.configure_services(service_list, connector)
                if valid is False:
                    _LOGGER.warning("unable to configure services")
                    return False
            elif connector:
                _LOGGER.info("Reading GATT services data from device")
                service_list = connector.get_services()
                valid = self.gatt_application.configure_services(service_list, connector)
                if valid is False:
                    _LOGGER.warning("unable to connect to device")
                    return False
            else:
                _LOGGER.warning("Unable to configure GATT services")
        else:
            _LOGGER.warning("Skipping GATT services")

        ## configuring notification handler
        if self._notificationHandler is not None:
            self._notificationHandler.stop()
        if connector:
            _LOGGER.info("Setting notification handler")
            self._notificationHandler = NotificationHandler(connector)
        else:
            _LOGGER.warning("Skipping notification handler")

        return True

    def _configure_advertisement(self, adv_data: AdvertisementData):
        ## register advertisement
        if self.advertisement is None:
            return
        self.advertisement.add_adv_data(adv_data)

    def _configure_scanresponse(self, scanresp_data: AdvertisementData):
        ## register advertisement
        if self.advertisement is None:
            return
        self.advertisement.add_scanresp_data(scanresp_data)

    ## configure services and start main loop
    def start(self):
        ## register advertisement
        if self.advertisement is not None:
            self.advertisement.initialize()
            self.advertisement.register()

        if self.agent is not None:
            self.agent.initialize()

        if self.gatt_application is not None:
            self.gatt_application.register()

        if self._notificationHandler is not None:
            _LOGGER.debug("Starting notification handler")
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
