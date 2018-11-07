#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging

# from gi.repository import GObject
# from gobject import gobject as GObject
import gobject as GObject
# import dbus
import dbus.mainloop.glib

from .advertisement import TestAdvertisement
from .constants import DBUS_OM_IFACE, DBUS_PROP_IFACE
from .constants import BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE
from .servicemock import ServiceMock


_LOGGER = logging.getLogger(__name__)



class ApplicationBase(dbus.service.Object):
    PATH_BASE = '/org/bluez/example'
    
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        _LOGGER.debug("Initializing ApplicationBase")
        self.path = self.PATH_BASE
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        ##_LOGGER.debug("ApplicationBase::GetManagedObjects: %r", self.services)

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response



class Application(ApplicationBase):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Application
        '''
        self.mainloop = None
        self.bus = None
        self.bluez_manager = None
        
        self.adManager = None
        self.adRegistered = False
        
        self._init()
        
        ##super().__init__(self.bus)
        ApplicationBase.__init__(self, self.bus)

    
    def register_services(self, connector, listenMode):
        self.register_services_old(connector, listenMode)
#         self.register_services_new(connector, listenMode)
    
    def register_services_new(self, connector, listenMode):
        _LOGGER.debug("Getting services")
        serviceList = connector.get_services()
        if serviceList == None:
            _LOGGER.debug("Could not get list of services")
            return
                     
        _LOGGER.debug("Registering services")
        serviceIndex = -1
        for s in serviceList:
            if s.uuid == '00001800-0000-1000-8000-00805f9b34fb':
                _LOGGER.debug("Skipping service: %s", s.uuid)
                continue
            if s.uuid == '00001801-0000-1000-8000-00805f9b34fb':
                _LOGGER.debug("Skipping service: %s", s.uuid)
                continue
            serviceIndex += 1
            service = ServiceMock( s, self.bus, serviceIndex, connector, listenMode )
            self.add_service( service )
    
        self.bluez_manager.RegisterApplication(    self.get_path(), {},
                                                   reply_handler=self.register_app_cb,
                                                   error_handler=self.register_app_error_cb)
    
    def register_app_cb(self):
        _LOGGER.info('GATT application registered')
    
    def register_app_error_cb(self, error):
        _LOGGER.error('Failed to register application: ' + str(error))
        ##mainloop.quit()
    
    def register_services_old(self, connector, listenMode):
        _LOGGER.debug("Getting services")
        serviceList = connector.get_services()
        if serviceList == None:
            _LOGGER.debug("Could not get list of services")
            return
                     
        _LOGGER.debug("Registering services")
        serviceIndex = -1
        for s in serviceList:
            if s.uuid == '00001800-0000-1000-8000-00805f9b34fb':
                _LOGGER.debug("Skipping service: %s", s.uuid)
                continue
            if s.uuid == '00001801-0000-1000-8000-00805f9b34fb':
                _LOGGER.debug("Skipping service: %s", s.uuid)
                continue
            serviceIndex += 1
            service = ServiceMock( s, self.bus, serviceIndex, connector, listenMode )
            service.register( self.bluez_manager )
            self.add_service( service )
    
        ##self.mainloop = GObject.MainLoop()
    
    def run(self):
        _LOGGER.debug("Starting main loop")
        self.mainloop.run()

    def stop(self):
        _LOGGER.debug( "Stopping main loop" )
        if self.adManager != None and self.adRegistered:
            _LOGGER.error('Unregistering advertisement')
            adPath = self.testAdvertisement.get_path()
            self.adManager.UnregisterAdvertisement( adPath )
        
        self.mainloop = None

    def _init(self):
        _LOGGER.debug("Initializing service manager")
        
        ## required for Python threading to work
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            
        self.bus = dbus.SystemBus()
        
        self._initAdvertisement()
        self._initGattService()
        
        self.mainloop = GObject.MainLoop()
        

    def _initAdvertisement(self):
        advertise_adapter = find_advertise_adapter(self.bus)
        if not advertise_adapter:
            _LOGGER.error('LEAdvertisingManager1 interface not found')
            return
        
        advertiseObj = self.bus.get_object(BLUEZ_SERVICE_NAME, advertise_adapter)
        adapter_props = dbus.Interface(advertiseObj, DBUS_PROP_IFACE);
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
         
        self.adManager = dbus.Interface(advertiseObj, LE_ADVERTISING_MANAGER_IFACE)
     
        self.adRegistered = False
        self.testAdvertisement = TestAdvertisement(self.bus, 0)
        adPath = self.testAdvertisement.get_path()
        self.adManager.RegisterAdvertisement(adPath, {},
                                             reply_handler=self._register_ad_cb,
                                             error_handler=self._register_ad_error_cb)
        
    def _register_ad_cb(self):
        _LOGGER.info( 'Advertisement registered' )
        self.adRegistered = True

    def _register_ad_error_cb(self, error):
        _LOGGER.error( 'Failed to register advertisement: %s', str(error) )
        self.adRegistered = False
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
    return find_object_with_key_old(objects, GATT_MANAGER_IFACE)

def find_object_with_key(objects, key):
    for obj, props in objects.items():
        pr = props.get(key)
        if pr != None:
            _LOGGER.debug('item: %s %s', obj, pr )
            return obj
    return None
        
def find_object_with_key_old(objects, key):
    for obj, props in objects.iteritems():
        if props.has_key(key):
            return obj
    return None
