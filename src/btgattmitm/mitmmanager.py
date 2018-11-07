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
        
        self.leAdvertisement = AdvertisementManager(self.bus, 0)
        self.gattServer      = GattServer(self.bus)
    
    def prepate(self, connector, listenMode):
        if self.gattServer != None:
            self.gattServer.prepare(connector, listenMode)
        
        self.mainloop = GObject.MainLoop()
        
        ## register advertisement
        if self.leAdvertisement != None:
            self.leAdvertisement.register()
        
        if self.gattServer != None:
            self.gattServer.register()

    def run(self):
        _LOGGER.debug("Starting main loop")
        self.mainloop.run()

    def stop(self):
        _LOGGER.debug( "Stopping main loop" )
        if self.leAdvertisement != None:
            self.leAdvertisement.unregister()
            
        if self.gattServer != None:
            self.gattServer.unregister()
            
        self.mainloop = None
