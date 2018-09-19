#
# MIT License
# 
# Copyright (c) 2017 Arkadiusz Netczuk <dev.arnet@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
    
    def __del__(self):
        pass


    def register_service(self, service):
        service.register(self.bluez_manager)
    
    def run(self):
        _LOGGER.debug("Starting main loop")
        self.mainloop.run()


    def _init(self):
        _LOGGER.debug("Initializing service manager")
        
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
    
        advertise_adapter = find_advertise_adapter(self.bus)
        if not advertise_adapter:
            _LOGGER.error('LEAdvertisingManager1 interface not found')
            return
    
        gatt_adapter = find_gatt_adapter(self.bus)
        if not gatt_adapter:
            _LOGGER.error('GattManager1 interface not found')
            return
    
    
        advertiseObj = self.bus.get_object(BLUEZ_SERVICE_NAME, advertise_adapter)
        adapter_props = dbus.Interface(advertiseObj, DBUS_PROP_IFACE);
    
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
    
        ad_manager = dbus.Interface(advertiseObj, LE_ADVERTISING_MANAGER_IFACE)
    
        test_advertisement = TestAdvertisement(self.bus, 0)
    
        gattObj = self.bus.get_object(BLUEZ_SERVICE_NAME, gatt_adapter)
        self.bluez_manager = dbus.Interface( gattObj, GATT_MANAGER_IFACE )
    
        self.mainloop = gobject.MainLoop()
    
        ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                         reply_handler=self._register_ad_cb,
                                         error_handler=self._register_ad_error_cb)

    def _register_ad_cb(self):
        _LOGGER.info( 'Advertisement registered' )


    def _register_ad_error_cb(self, error):
        _LOGGER.error( 'Failed to register advertisement: %s', str(error) )
        self.mainloop.quit()


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
