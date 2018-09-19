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

from bluepy import btle



_LOGGER = logging.getLogger(__name__)



class Connector(btle.DefaultDelegate):
    '''
    classdocs
    '''

    def __init__(self, mac):
        '''
        Constructor
        '''
        btle.DefaultDelegate.__init__(self)
        
        self.address = mac
        self._conn = None
    
    def __del__(self):
        #TODO: make disconnection on CTRL+C
        self._disconnect()
    
    def get_services(self):
        peripheral = self._connect()
        if peripheral == None:
            return
        return peripheral.getServices()
    
    def print_services(self):
        _LOGGER.debug("Discovering services")        
        peripheral = self._connect()
        if peripheral == None:
            return
        serviceList = peripheral.getServices()
        for s in serviceList:
            _LOGGER.debug("Service: %s[%s]", s.uuid, s.uuid.getCommonName())
            charsList = s.getCharacteristics()
            for ch in charsList:
                _LOGGER.debug("Char: %s h:%i p:%s", ch, ch.getHandle(), ch.propertiesToString())

#             descList = s.getDescriptors()
#             for desc in descList:
# #                 _LOGGER.debug("Desc: %s: %s", desc, desc.read())
# #                 _LOGGER.debug("Desc: %s %s %s", desc, dir(desc), vars(desc) )
# #                 _LOGGER.debug("Desc: %s uuid:%s h:%i v:%s", desc, desc.uuid, desc.handle, desc.read() )
#                 _LOGGER.debug("Desc: %s uuid:%s h:%i", desc, desc.uuid, desc.handle )
    
    def _connect(self):
        if self._conn != None:
            return self._conn
        
        for _ in range(0,2):
            try:
                conn = btle.Peripheral()
                conn.withDelegate(self)
                conn.connect(self.address, addrType='random')
                self._conn = conn
                return self._conn
            except btle.BTLEException as ex:
                self._conn = None
                _LOGGER.debug("Unable to connect to the device %s, retrying: %s", self.address, ex)
                
        return None
        
    def _disconnect(self):
        _LOGGER.debug("Disconnecting")
    
    def handleNotification(self, cHandle, data):
        _LOGGER.info("new notification")
        btle.DefaultDelegate.handleNotification(cHandle, data)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        _LOGGER.info("new discovery")
        btle.DefaultDelegate.handleDiscovery(scanEntry, isNewDev, isNewData)
    
    
    