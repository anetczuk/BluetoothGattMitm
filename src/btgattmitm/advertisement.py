#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging

import dbus.service

from .constants import DBUS_PROP_IFACE, LE_ADVERTISEMENT_IFACE
from .constants import BLUEZ_SERVICE_NAME
from .constants import LE_ADVERTISING_MANAGER_IFACE
from .exception import InvalidArgsException
from .find_adapter import find_advertise_adapter

import pprint


_LOGGER = logging.getLogger(__name__)



class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
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
        
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary( self.manufacturer_data, signature='qv' )
            ##properties['ManufacturerData'] = dbus.Dictionary( self.manufacturer_data, signature='qay' )
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
            ##properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='say')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power is not None:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        _LOGGER.debug( "Adding service uuid: %s", uuid )
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        _LOGGER.debug( "Adding solicit uuid: %s", uuid )
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        _LOGGER.debug( "Adding manufacturer data: %s %s", manuf_code, data )
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')
#         if not self.manufacturer_data:
#             self.manufacturer_data = dict()
#         _LOGGER.debug( "Adding manufacturer data: %s %s", manuf_code, data )
#         self.manufacturer_data[manuf_code] = data

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        _LOGGER.debug( "Adding service data: %s %s", uuid, data )
        self.service_data[uuid] = dbus.Array(data, signature='y')
#         if not self.service_data:
#             self.service_data = dict()
#         _LOGGER.debug( "Adding service data: %s %s", uuid, data )
#         self.service_data[uuid] = data

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        _LOGGER.debug( "Adding local name: %s", name )
        self.local_name = dbus.String(name)
        
    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        _LOGGER.debug( "Adding data: %s %s", ad_type, data )
        self.data[ad_type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        _LOGGER.debug("Getting advertisement all")
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
#         print( 'returning props' )
        allProps = self.get_properties()
        _LOGGER.debug("Getting properties from dict:\n%s\n", pprint.pformat(allProps) )
        leProp = allProps[LE_ADVERTISEMENT_IFACE]
        _LOGGER.debug( "LE Properties:\n%s\n", pprint.pformat(leProp) )
        return leProp

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        _LOGGER.debug("Advertisement released")



class AdvertisementManager(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180D')
        self.add_service_uuid('180F')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_local_name('TestAdvertisementX')
        self.include_tx_power = True
        self.add_data(0x26, [0x01, 0x01, 0x00])
        
        self.adRegistered = False
        self.adManager = None
        self._initManager(bus)
        
    def _initManager(self, bus):
        advertise_adapter = find_advertise_adapter(bus)
        if not advertise_adapter:
            _LOGGER.error('LEAdvertisingManager1 interface not found')
            return
        
        advertiseObj = self.bus.get_object(BLUEZ_SERVICE_NAME, advertise_adapter)
        adapter_props = dbus.Interface(advertiseObj, DBUS_PROP_IFACE);
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
        self.adManager = dbus.Interface(advertiseObj, LE_ADVERTISING_MANAGER_IFACE)

    def register(self):
        if self.adManager == None:
            return
        adPath = self.get_path()
        _LOGGER.error( 'Registering advertisement: %s', adPath )
        self.adManager.RegisterAdvertisement( adPath, {},
                                              reply_handler=self._register_ad_cb,
                                              error_handler=self._register_ad_error_cb)

    def unregister(self):
        if self.adRegistered == False:
            return
        _LOGGER.error('Unregistering advertisement')
        adPath = self.get_path()
        self.adManager.UnregisterAdvertisement( adPath )

    def _register_ad_cb(self):
        _LOGGER.info( 'Advertisement registered' )
        self.adRegistered = True

    def _register_ad_error_cb(self, error):
        _LOGGER.error( 'Failed to register advertisement: %s', str(error) )
        self.adRegistered = False
    