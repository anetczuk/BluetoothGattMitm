#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
import pprint

import dbus.service

from btgattmitm.constants import DBUS_PROP_IFACE, LE_ADVERTISEMENT_IFACE
from btgattmitm.constants import BLUEZ_SERVICE_NAME
from btgattmitm.constants import LE_ADVERTISING_MANAGER_IFACE
from btgattmitm.find_adapter import find_advertise_adapter
from btgattmitm.dbusobject.exception import InvalidArgsException


_LOGGER = logging.getLogger(__name__)


class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.discoverable = True
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        _LOGGER.debug("Getting advertisement properties")

        properties = {}
        properties["Type"] = dbus.String(self.ad_type)
        properties["Discoverable"] = dbus.Boolean(self.discoverable)

        if self.local_name is not None:
            properties["LocalName"] = dbus.String(self.local_name)

        if self.include_tx_power:
            properties["Includes"] = dbus.Array(["tx-power"], signature="s")

        if self.service_uuids is not None:
            properties["ServiceUUIDs"] = dbus.Array(self.service_uuids, signature="s")

        if self.solicit_uuids is not None:
            properties["SolicitUUIDs"] = dbus.Array(self.solicit_uuids, signature="s")

        if self.manufacturer_data is not None:
            man_data = {}
            for man_key, man_val in self.manufacturer_data.items():
                man_data[man_key] = dbus.Array(man_val, signature="y")
            properties["ManufacturerData"] = dbus.Dictionary(man_data, signature="qv")

        if self.service_data is not None:
            serv_data = {}
            for serv_key, serv_val in self.service_data.items():
                serv_data[serv_key] = dbus.Array(serv_val, signature="y")
            properties["ServiceData"] = dbus.Dictionary(serv_data, signature="sv")

        if self.data is not None:
            properties["Data"] = self.data

        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def set_service_uuid_list(self, uuid_list):
        self.service_uuids = []
        for item in uuid_list:
            self.add_service_uuid(item)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        _LOGGER.debug("Adding service uuid: %s", uuid)
        self.service_uuids.append(uuid)

    def add_service_uuid_list(self, uuid_list):
        for item in uuid_list:
            self.add_service_uuid(item)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        _LOGGER.debug("Adding solicit uuid: %s", uuid)
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = {}
        _LOGGER.debug("Adding manufacturer data: %s %s", manuf_code, data)
        # self.manufacturer_data[manuf_code] = data
        self.manufacturer_data[manuf_code] = data

    def add_manufacturer_data_dict(self, data_dict):
        for key, data in data_dict.items():
            self.add_manufacturer_data(key, data)

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = {}
        _LOGGER.debug("Adding service data: %s %s", uuid, data)
        self.service_data[str(uuid)] = data

    def add_service_data_dict(self, data_dict):
        for key, data in data_dict.items():
            self.add_service_data(key, data)

    def set_local_name(self, name):
        if name is None:
            return
        if not self.local_name:
            self.local_name = ""
        _LOGGER.debug("Setting local name: %s", name)
        self.local_name = name

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature="yv")
        _LOGGER.debug("Adding data: %s %s", ad_type, data)
        self.data[ad_type] = dbus.Array(data, signature="y")

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        _LOGGER.debug("Getting advertisement all")
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        #         print( 'returning props' )
        allProps = self.get_properties()
        _LOGGER.debug("Getting properties from dict:\n%s", pprint.pformat(allProps))
        leProp = allProps[LE_ADVERTISEMENT_IFACE]
        # _LOGGER.debug("LE Properties:\n%s\n", pprint.pformat(leProp))
        return leProp

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        _LOGGER.debug("Advertisement released")


class AdvertisementManager(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")

        self.include_tx_power = True
        self.register_completed = False
        self.manager_iface = None

    def initialize(self):
        advertise_adapter = find_advertise_adapter(self.bus)
        if not advertise_adapter:
            _LOGGER.error("LEAdvertisingManager1 interface not found")
            return

        advertiseObj = self.bus.get_object(BLUEZ_SERVICE_NAME, advertise_adapter)
        adapter_props = dbus.Interface(advertiseObj, DBUS_PROP_IFACE)
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
        self.manager_iface = dbus.Interface(advertiseObj, LE_ADVERTISING_MANAGER_IFACE)

    def register(self):
        if self.manager_iface is None:
            return
        adPath = self.get_path()
        _LOGGER.info("Registering advertisement: %s", adPath)
        self.manager_iface.RegisterAdvertisement(
            adPath, {}, reply_handler=self._register_ad_cb, error_handler=self._register_ad_error_cb
        )

    def unregister(self):
        if self.register_completed is False:
            return
        _LOGGER.error("Unregistering advertisement")
        adPath = self.get_path()
        self.manager_iface.UnregisterAdvertisement(adPath)

    def _register_ad_cb(self):
        _LOGGER.info("Advertisement registered")
        self.register_completed = True

    def _register_ad_error_cb(self, error):
        _LOGGER.error("Failed to register advertisement: %s", str(error))
        self.register_completed = False
