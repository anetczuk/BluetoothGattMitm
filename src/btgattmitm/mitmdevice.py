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
from time import sleep
from threading import Thread

from .servicemanager import ServiceManager
from .servicemock import ServiceMock



_LOGGER = logging.getLogger(__name__)



class NotificationHandler(Thread):
    def __init__(self, connector):
        Thread.__init__(self)
        self.connector = connector
        self.daemon = True
        self.execute = True
        
    def stop(self):
        _LOGGER.info("Stopping notify handler")
        self._stopLoop()
        self.join()
        
    def run(self):
        try:
            _LOGGER.info("Starting notify handler")
            self.execute = True
            while self.execute:
                try:
                    self.connector.processNotifications()
                except:
                    _LOGGER.exception("Exception occured")
                    self._stopLoop()
                sleep(0.001)                      ## prevents starving other thread
        finally:
            _LOGGER.info("Notification handler run loop stopped")

    def _stopLoop(self):
        self.execute = False



class MITMDevice():
    '''
    classdocs
    '''

    def __init__(self):
        '''
        MITMDevice
        '''
        self.manager = ServiceManager()
        self._notificationHandler = None
        self.servceList = []
    
#     def __del__(self):
#         print "destroying", self.__class__.__name__

    def start(self, connector):
        _LOGGER.debug("Configuring MITM")
        
        serviceIndex = 0
        bus = self.manager.bus
         
        serviceList = connector.get_services()
        if serviceList == None:
            _LOGGER.debug("Could not get list of services")
            return
                    
        for s in serviceList:
            service = ServiceMock( s, bus, serviceIndex, connector )
            self.manager.register_service(service)
            self.servceList.append( service )
            serviceIndex += 1
        
        if self._notificationHandler != None:
            self._notificationHandler.stop()
        self._notificationHandler = NotificationHandler(connector)
        self._notificationHandler.start()
        
        self.manager.run()
    
    def stop(self):
        _LOGGER.debug("Stopping MITM")
        self.servceList = []
        if self._notificationHandler != None:
            self._notificationHandler.stop()
        self.manager.stop()
    