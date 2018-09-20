#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging

import gobject
import dbus.mainloop.glib

from advertisement import TestAdvertisement
from constants import DBUS_OM_IFACE, DBUS_PROP_IFACE
from constants import BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE



_LOGGER = logging.getLogger(__name__)



class ServiceManager():
    '''
    classdocs
    '''

    def __init__(self):
        '''
        ServiceManager
        '''
        self.mainloop = None
        self.bus = None
        self.bluez_manager = None
        self._init()

    def register_service(self, service):
        service.register(self.bluez_manager)
    
    def run(self):
        _LOGGER.debug("Starting main loop")
        self.mainloop.run()

    def stop(self):
        _LOGGER.debug( "Stopping main loop" )
        self.mainloop = None

    def _init(self):
        _LOGGER.debug("Initializing service manager")
        
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
    
#         self._initAdvertisement()
        
        self._initGattService()
        
        self.mainloop = gobject.MainLoop()

    def _initAdvertisement(self):
        advertise_adapter = find_advertise_adapter(self.bus)
        if not advertise_adapter:
            _LOGGER.error('LEAdvertisingManager1 interface not found')
            return
        
        advertiseObj = self.bus.get_object(BLUEZ_SERVICE_NAME, advertise_adapter)
        adapter_props = dbus.Interface(advertiseObj, DBUS_PROP_IFACE);
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
         
        ad_manager = dbus.Interface(advertiseObj, LE_ADVERTISING_MANAGER_IFACE)
     
        test_advertisement = TestAdvertisement(self.bus, 0)
     
        ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                         reply_handler=self._register_ad_cb,
                                         error_handler=self._register_ad_error_cb)
        
    def _register_ad_cb(self):
        _LOGGER.info( 'Advertisement registered' )

    def _register_ad_error_cb(self, error):
        _LOGGER.error( 'Failed to register advertisement: %s', str(error) )
        self.mainloop.quit()
        
    def _initGattService(self):
        gatt_adapter = find_gatt_adapter(self.bus)
        if not gatt_adapter:
            _LOGGER.error('GattManager1 interface not found')
            return
            
        gattObj = self.bus.get_object(BLUEZ_SERVICE_NAME, gatt_adapter)
        self.bluez_manager = dbus.Interface( gattObj, GATT_MANAGER_IFACE )


## ====================================================================
    

def find_advertise_adapter(bus):
    serviceObj = bus.get_object(BLUEZ_SERVICE_NAME, '/')
    remote_om = dbus.Interface(serviceObj, DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.iteritems():
        if LE_ADVERTISING_MANAGER_IFACE in props:
            return o

    return None

def find_gatt_adapter(bus):
    serviceObj = bus.get_object(BLUEZ_SERVICE_NAME, '/')
    remote_om = dbus.Interface(serviceObj, DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.iteritems():
        if props.has_key(GATT_MANAGER_IFACE):
            return o

    return None
