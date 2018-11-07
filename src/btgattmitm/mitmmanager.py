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

from .advertisement import AdvertisementManager
from .gattserver import GattServer
from .connector import NotificationHandler



_LOGGER = logging.getLogger(__name__)



class MitmManager():
    '''
    classdocs
    '''

    def __init__(self):
        '''
        MITM manager
        '''
        
        ## required for Python threading to work
        GObject.threads_init()
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        
        _LOGGER.debug("Initializing MITM manager")
        
        self.mainloop    = None

        self.bus             = dbus.SystemBus()
        
        self._notificationHandler = None
        
        self.leAdvertisement = AdvertisementManager(self.bus, 0)
        self.gattServer      = GattServer(self.bus)

    def start(self, connector, listenMode):
        _LOGGER.debug("Configuring MITM")
         
        self._prepate(connector, listenMode)
        
        _LOGGER.debug("Starting notification handler")
        if self._notificationHandler != None:
            self._notificationHandler.stop()
        self._notificationHandler = NotificationHandler(connector)
        self._notificationHandler.start()
        
        _LOGGER.debug("Starting main loop")
        self.mainloop.run()
    
    def stop(self):
        _LOGGER.debug("Stopping MITM")
        if self._notificationHandler != None:
            self._notificationHandler.stop()

        if self.leAdvertisement != None:
            self.leAdvertisement.unregister()
            
        if self.gattServer != None:
            self.gattServer.unregister()
            
        self.mainloop = None
        
    def _prepate(self, connector, listenMode):
        if self.gattServer != None:
            self.gattServer.prepare(connector, listenMode)
        
        self.mainloop = GObject.MainLoop()
        
        ## register advertisement
        if self.leAdvertisement != None:
            self.leAdvertisement.register()
        
        if self.gattServer != None:
            self.gattServer.register()
