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

from btgattmitm.servicebase import ServiceBase, CharacteristicBase



_LOGGER = logging.getLogger(__name__)



class ServiceMock(ServiceBase):
    '''
    classdocs
    '''

    def __init__(self, btService, bus, index):
        '''
        Service
        '''
        btUuid = btService.uuid
        serviceUuid = str(btUuid)
        
        _LOGGER.debug("Creating service: %s[%s]", serviceUuid, btUuid.getCommonName())
        
        ServiceBase.__init__(self, bus, index, serviceUuid, True)
        
        self._mock_characteristics(btService, bus)
    
    def __del__(self):
        pass

    def _mock_characteristics(self, btService, bus):
        charsList = btService.getCharacteristics()
        charIndex = 0
        for btCh in charsList:
            ##_LOGGER.debug("Char: %s h:%i p:%s", btCh, btCh.getHandle(), btCh.propertiesToString())
            char = CharacteristicMock(btCh, bus, charIndex, self)
            self.add_characteristic( char )
            charIndex += 1
    
    
    
class CharacteristicMock(CharacteristicBase):
    '''
    classdocs
    '''

    def __init__(self, btCharacteristic, bus, index, service):
        '''
        Characteristic
        '''
        btUuid = btCharacteristic.uuid
        characteristicUuid = str(btUuid)
        
        _LOGGER.debug("Creating characteristic: %s[%s]", characteristicUuid, btUuid.getCommonName())
        
        CharacteristicBase.__init__(self, bus, index, characteristicUuid, ['read'], service)
    
    def __del__(self):
        pass

