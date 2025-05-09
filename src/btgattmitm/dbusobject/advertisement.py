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
from btgattmitm.connector import AdvertisementData


_LOGGER = logging.getLogger(__name__)


ADV_PROP_ID_TO_NAME_DICT = {
    2: "ServiceUUIDs",
    # ?: "SolicitUUIDs",
    # ?: "Data"
    9: "LocalName",
    22: "ServiceData",
    255: "ManufacturerData",
}

SCANRESP_PROP_ID_TO_NAME_DICT = {
    2: "ScanResponseServiceUUIDs",
    # ?: "ScanResponseSolicitUUIDs",
    # ?: "ScanResponseData"
    22: "ScanResponseServiceData",
    255: "ScanResponseManufacturerData",
}


class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus

        self.ad_type = advertising_type
        self.discoverable = True
        self.include_tx_power = None

        self.adv_data = {}
        self.scanresp_data = {}
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        _LOGGER.debug("Getting advertisement properties")

        try:
            properties = {}

            for key, data in self.adv_data.items():
                prop_name = ADV_PROP_ID_TO_NAME_DICT.get(key)
                if prop_name is not None:
                    value = self._convert_prop_to_dbus(prop_name, data)
                    if value is not None:
                        properties[prop_name] = value
                    continue
                _LOGGER.warning("unhandled adv property: %s", key)

            for key, data in self.scanresp_data.items():
                prop_name = SCANRESP_PROP_ID_TO_NAME_DICT.get(key)
                if prop_name is not None:
                    value = self._convert_prop_to_dbus(prop_name, data)
                    if value is not None:
                        properties[prop_name] = value
                    continue
                prop_name = ADV_PROP_ID_TO_NAME_DICT.get(key)
                if prop_name is not None:
                    value = self._convert_prop_to_dbus(prop_name, data)
                    if value is not None:
                        properties[prop_name] = value
                    continue
                _LOGGER.warning("unhandled scanresp property: %s", key)

            properties["Type"] = dbus.String(self.ad_type)
            properties["Discoverable"] = dbus.Boolean(self.discoverable)

            if self.include_tx_power:
                properties["Includes"] = dbus.Array(["tx-power"], signature="s")

            return {LE_ADVERTISEMENT_IFACE: properties}

        except:  # noqa
            _LOGGER.exception("unable to get dbus properties")
            raise

    def _convert_prop_to_dbus(self, key, data):
        if key == "Type":
            return dbus.String(data)
        if key == "Discoverable":
            return dbus.Boolean(data)
        if key == "LocalName":
            return dbus.String(data)
        if key == "ServiceUUIDs":
            return dbus.Array(data, signature="s")
        if key == "SolicitUUIDs":
            return dbus.Array(data, signature="s")
        if key in ("ManufacturerData", "ScanResponseManufacturerData"):
            man_data = {}
            for man_key, man_val in data.items():
                man_data[man_key] = dbus.Array(man_val, signature="y")
            return dbus.Dictionary(man_data, signature="qv")
        if key == "ServiceData":
            serv_data = {}
            for serv_key, serv_val in data.items():
                serv_data[serv_key] = dbus.Array(serv_val, signature="y")
            return dbus.Dictionary(serv_data, signature="sv")
        # if key == "Data":
        #     return self.data

        _LOGGER.warning("unhandled property: %s", key)
        return None

    def get_adv_data(self) -> AdvertisementData:
        return AdvertisementData(self.adv_data)

    def add_adv_data(self, adv_data: AdvertisementData):
        ## merge two dicts
        adv_dict = adv_data.get_props()
        self.adv_data = self.adv_data | adv_dict

    def get_scanresp_data(self) -> AdvertisementData:
        return AdvertisementData(self.scanresp_data)

    def add_scanresp_data(self, scanresp_data: AdvertisementData):
        ## merge two dicts
        scanresp_dict = scanresp_data.get_props()
        self.scanresp_data = self.scanresp_data | scanresp_dict

    def set_service_uuid_list(self, uuid_list):
        self.adv_data[0x02] = []
        for item in uuid_list:
            self.add_service_uuid(item)

    def add_service_uuid(self, uuid):
        _LOGGER.debug("Adding service uuid: %s", uuid)
        data_container = self.adv_data.get(0x02, [])
        data_container.append(uuid)
        self.adv_data[0x02] = data_container

    def add_service_uuid_list(self, uuid_list):
        for item in uuid_list:
            self.add_service_uuid(item)

    # def add_solicit_uuid(self, uuid):
    #     _LOGGER.debug("Adding solicit uuid: %s", uuid)
    #     data_container = self.adv_data.get("SolicitUUIDs", [])
    #     data_container.append(uuid)
    #     self.adv_data["SolicitUUIDs"] = data_container

    def add_manufacturer_data(self, manuf_code, data):
        _LOGGER.debug("Adding manufacturer data: %s %s", manuf_code, data)
        data_container = self.adv_data.get(0xFF, {})
        data_container[manuf_code] = data
        self.adv_data[0xFF] = data_container

    def add_manufacturer_data_dict(self, data_dict):
        for key, data in data_dict.items():
            self.add_manufacturer_data(key, data)

    def add_service_data(self, uuid, data):
        _LOGGER.debug("Adding service data: %s %s", uuid, data)
        data_container = self.adv_data.get(0x16, {})
        data_container[str(uuid)] = data
        self.adv_data[0x16] = data_container

    def add_service_data_dict(self, data_dict):
        for key, data in data_dict.items():
            self.add_service_data(key, data)

    def set_local_name(self, name):
        if name is None:
            return
        _LOGGER.debug("Setting local name: %s", name)
        self.adv_data[0x09] = name

    # def add_data(self, ad_type, data):
    #     data_container = self.adv_data.get("Data", None)
    #     if data_container is None:
    #         data_container = dbus.Dictionary({}, signature="yv")
    #     _LOGGER.debug("Adding data: %s %s", ad_type, data)
    #     data_container[ad_type] = dbus.Array(data, signature="y")
    #     self.adv_data["Data"] = data_container

    ## ========================================================

    def get_path(self):
        return dbus.ObjectPath(self.path)

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
