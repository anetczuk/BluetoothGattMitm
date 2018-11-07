#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging

import dbus

from .constants import DBUS_OM_IFACE
from .constants import BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE
from .find_adapter import find_gatt_adapter
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



class GattServer(ApplicationBase):
    '''
    classdocs
    '''

    def __init__(self, bus):
        '''
        Application
        '''
        self.bus         = bus
        self.gattManager = None

        ApplicationBase.__init__(self, self.bus)
        
        self._initManager()
        
    def _initManager(self):
        gatt_adapter = find_gatt_adapter( self.bus )
        if not gatt_adapter:
            _LOGGER.error('GattManager1 interface not found')
            return
            
        gattObj = self.bus.get_object(BLUEZ_SERVICE_NAME, gatt_adapter)
        self.gattManager = dbus.Interface( gattObj, GATT_MANAGER_IFACE )
            
    def prepare(self, connector, listenMode):
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
            
    def register(self):
        if self.gattManager == None:
            return
        ## register services
        self._register_services_old()
            
    def unregister(self):
        ## do nothing
        pass
            
    def _register_services_old(self):
        for service in self.services:
            service.register( self.gattManager )
        
    def _register_services_new(self):
        self.gattManager.RegisterApplication( self.get_path(), {},
                                              reply_handler=self.register_app_cb,
                                              error_handler=self.register_app_error_cb)
    
    def register_app_cb(self):
        _LOGGER.info('GATT application registered')
    
    def register_app_error_cb(self, error):
        _LOGGER.error('Failed to register application: ' + str(error))
        ##mainloop.quit()
    