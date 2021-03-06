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

import struct
import logging

from .servicebase import ServiceBase, CharacteristicBase
from .constants import GATT_CHRC_IFACE



_LOGGER = logging.getLogger(__name__)



def to_hex_string(data):
    return " ".join("0x{:02X}".format(x) for x in data)


class ServiceMock(ServiceBase):
    '''
    classdocs
    '''

    def __init__(self, btService, bus, index, connector, listenMode):
        '''
        Service
        '''
        btUuid = btService.uuid
        serviceUuid = str(btUuid)
        
        _LOGGER.debug("Creating service: %s[%s]", serviceUuid, btUuid.getCommonName())
        
        ServiceBase.__init__(self, bus, index, serviceUuid, True)
        
        self._mock_characteristics(btService, bus, connector, listenMode)
    
    def __del__(self):
        pass

    def _mock_characteristics(self, btService, bus, connector, listenMode):
        charsList = btService.getCharacteristics()
        charIndex = 0
        for btCh in charsList:
            ##_LOGGER.debug("Char: %s h:%i p:%s", btCh, btCh.getHandle(), btCh.propertiesToString())
            char = CharacteristicMock(btCh, bus, charIndex, self, connector, listenMode)
            self.add_characteristic( char )
            charIndex += 1
    
    
    def register(self, gattManager):
        gattManager.RegisterService( self.get_path(), {},
                                     reply_handler=self._register_service_cb,
                                     error_handler=self._register_service_error_cb )
     
    def _register_service_cb(self):
        _LOGGER.info('GATT service registered: uuid:%s', self.uuid)
#         _LOGGER.info('GATT service registered: %s uuid:%s', self.__class__.__name__, self.uuid)
         
    def _register_service_error_cb(self, error):
        _LOGGER.error('Failed to register service: %s uuid:%s', str(error), self.uuid )
        
    
    
class CharacteristicMock(CharacteristicBase):
    '''
    classdocs
    '''
    
    ## allowed flags
    #         broadcast
    #         read
    #         write-without-response
    #         write
    #         notify
    #         indicate
    #         authenticated-signed-writes
    #         extended-properties
    FLAGS_DICT = {  #0b00000001 : "BROADCAST",
                    0b00000010 : "read",
                    0b00000100 : "write-without-response",
                    0b00001000 : "write",
                    0b00010000 : "notify",
                    0b00100000 : "indicate"
                    #0b01000000 : "WRITE SIGNED",
                    #0b10000000 : "EXTENDED PROPERTIES",
                 }


    def __init__(self, btCharacteristic, bus, index, service, connector, listenMode):
        '''
        Characteristic
        '''
        self.connector = connector
        self.cHandler = btCharacteristic.getHandle()
        
        btUuid = btCharacteristic.uuid
        self.chUuid = str(btUuid)
        
        _LOGGER.debug("Creating characteristic: %s[%s] %s", self.chUuid, btUuid.getCommonName(), "0x{:02X}".format(self.cHandler))
        
        flags = self._getFlags( btCharacteristic )
        CharacteristicBase.__init__(self, bus, index, self.chUuid, flags, service)
        
        ## subscribe for notifications
        if listenMode:
            ncount = flags.count( "notify" ) + flags.count( "indicate" )
            if ncount>0:
                _LOGGER.debug("Subscribing for %s", self.chUuid)
                connector.subscribeForNotification( self.cHandler, self._handle_notification )
    
    def __del__(self):
        pass

    def _handle_notification(self, data):
        data = bytearray(data)
        _LOGGER.debug("Received data: [%s]", to_hex_string(data) )

    def _getFlags(self, btCharacteristic):
        propsMask = btCharacteristic.properties
        propsString = btCharacteristic.propertiesToString()
        
#         _LOGGER.debug("Reading flags from: %s", propsString)
#         _LOGGER.debug("Properties bitmask: %s", format(propsMask,'016b') )
        
        flagsList = []
        propsList = self._extractBits(propsMask)
        for prop in propsList:
            flag = self._extractFlag( prop )
            if flag == None:
                _LOGGER.warn("Could not find flag for property: %i in string: %s", prop, propsString)
                continue
            flagsList.append(flag)
            
        _LOGGER.debug("Reading properties %s to flags %s", propsString, flagsList)
            
        return flagsList
    
    def _extractFlag(self, prop):
        if prop not in self.FLAGS_DICT:
            return None
        return self.FLAGS_DICT[ prop ]
    
    def _extractBits(self, number):
        ret = []
        bit = 1
        while number >= bit:
            if number & bit:
                ret.append(bit)
            bit <<= 1
        return ret
    
    def readValueHandler(self):
        data = self.connector.readCharacteristic( self.cHandler )
        data = self._convertData(data)            
        _LOGGER.debug('Client read request on %s: %s %s', self.chUuid, repr(data), to_hex_string(data) )
        return data
        
    def writeValueHandler(self, value):
        _LOGGER.debug('Client write request on %s: %s %s', self.chUuid, repr(value), to_hex_string(value) )
        ## repr(unwrapped), [hex(no) for no in unwrapped]
        data = bytes()
        for val in value:
            data += struct.pack('B', val)
        self.connector.writeCharacteristic( self.cHandler, data )
        ##ret = self.connector.writeCharacteristic( self.cHandler, data )
        ##_LOGGER.debug("response: %r", ret)
        #TODO: implement write without return
        
    def startNotifyHandler(self):
        ret = self.connector.subscribeForNotification( self.cHandler, self.notificationCallback )        
        _LOGGER.debug('Client registered for notifications on %s [%s] %s', self.chUuid, self.cHandler, ret)
        
    def stopNotifyHandler(self):
        ret = self.connector.unsubscribeFromNotification(self.cHandler, self.notificationCallback )
        _LOGGER.debug('Client unregistered from notifications on %s [%s] %s', self.chUuid, self.cHandler, ret)
    
    def notificationCallback(self, value):
        value = self._convertData(value)
        _LOGGER.debug('Notification to client on %s: %s %s', self.chUuid, repr(value), to_hex_string(value) )
        self.sendNotification( value )
    
    def sendNotification(self, value):
        wrapped = self._wrap(value)
        self.PropertiesChanged( GATT_CHRC_IFACE, { 'Value': wrapped }, [])
        
    def _convertData(self, data):
        if isinstance(data, str):
            ### convert string to byte array, required for Python2
            data = bytearray(data)
        return data
    
    