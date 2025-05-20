#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#

import logging
from typing import List, Any

import dbus.service

from btgattmitm.constants import DBUS_PROP_IFACE
from btgattmitm.constants import GATT_CHRC_IFACE
from btgattmitm.dbusobject.exception import InvalidArgsException, NotSupportedException


_LOGGER = logging.getLogger(__name__)


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index: int, uuid: str, flags, service):
        self.bus = bus
        self.service = service
        self.index: int = index
        self.path: str = service.path + "/char" + str(index)
        self.uuid: str = uuid
        self.prop_flags: List[str] = flags
        self.descriptors: List[Any] = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties_list(self) -> List[str]:
        """Return list of properties (flag) names."""
        return self.prop_flags

    def get_properties(self):
        props = {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.prop_flags,
                "Descriptors": dbus.Array(self.get_descriptor_paths(), signature="o"),
            }
        }
        #         print( "returning props:", props )
        return props

    def get_path(self):
        path = dbus.ObjectPath(self.path)
        #         print( "returning path:", path )
        return path

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        #         print( "returning paths:", result )
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        props_dict = self.get_properties()
        props = props_dict[GATT_CHRC_IFACE]
        #         print( "returning props:", props )
        return props

    ### called on read request from connected device
    # @dbus.service.method(GATT_CHRC_IFACE, out_signature="ay")
    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, _value):
        # def ReadValue(self, options):
        try:
            # pylint: disable=E1111
            value = self.readValueHandler()
            if value is None:
                return []
            # value = self._wrap(value)
            # _LOGGER.debug("Sending data to client: %s", repr(value))
            return value
        except:  # noqa    # pylint: disable=W0702
            logging.exception("Exception occured")
            raise

    ### called when connected device send something to characteristic
    # @dbus.service.method(GATT_CHRC_IFACE, in_signature="ay")
    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, _value):
        # def WriteValue(self, value, options):
        try:
            # _LOGGER.debug("Received data from client: %s", repr(value))
            # value = self._unwrap(value)
            return self.writeValueHandler(value)
        except:  # noqa    # pylint: disable=W0702
            logging.exception("Exception occured")
            raise

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        try:
            self.startNotifyHandler()
        except:  # noqa    # pylint: disable=W0702
            logging.exception("Exception occured")
            raise

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        try:
            self.stopNotifyHandler()
        except:  # noqa    # pylint: disable=W0702
            logging.exception("Exception occured")
            raise

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    # =======================================================

    def readValueHandler(self):
        _LOGGER.debug("Default ReadValue called, returning error")
        raise NotSupportedException()

    def writeValueHandler(self, _value):
        # def writeValueHandler(self, value):
        _LOGGER.debug("Default WriteValue called, returning error")
        raise NotSupportedException()

    def startNotifyHandler(self):
        _LOGGER.debug("Default StartNotify called, returning error")
        raise NotSupportedException()

    def stopNotifyHandler(self):
        _LOGGER.debug("Default StopNotify called, returning error")
        raise NotSupportedException()

    def _wrap(self, value):
        ##return dbus.Array( value, dbus.Signature('ay') )
        if isinstance(value, (list, bytearray, bytes)):
            vallist = []
            for x in value:
                vallist = vallist + self._wrap(x)
            return dbus.Array(vallist)
        if isinstance(value, bytes):
            ##return dbus.Array( [dbus.Byte( int(value) )] )
            _LOGGER.debug("bytes len: %i", len(value))
        if isinstance(value, int):
            return dbus.Array([dbus.Byte(int(value))])
        _LOGGER.error("Unsupported type: %s %s", repr(value), type(value))
        return None

    def _unwrap(self, value):
        if isinstance(value, dbus.Array):
            vallist = [self._unwrap(x) for x in value]
            return vallist
        if isinstance(value, dbus.Byte):
            return int(value)
        _LOGGER.debug("Unsupported type: %s", repr(value))
        return None


# class RCharacteristic(Characteristic):
#
#     def __init__(self, bus, index, uuid, service):
#         Characteristic.__init__(
#                 self, bus, index,
#                 uuid,
#                 ['read'],
#                 service)
#         self.value_lvl = 100
#
#     def readValueHandler(self):
#         return self.value_lvl
#
#
# class RWCharacteristic(Characteristic):
#
#     def __init__(self, bus, index, uuid, service):
#         Characteristic.__init__(
#                 self, bus, index,
#                 uuid,
#                 ['read', 'write'],
#                 service)
#         self.value_lvl = 100
#
#     def readValueHandler(self):
#         return self.value_lvl
#
#     def writeValueHandler(self, value):
#         self.value_lvl = value
#
#
# class RNCharacteristic(Characteristic):
#
#     def __init__(self, bus, index, uuid, service):
#         Characteristic.__init__(
#                 self, bus, index,
#                 uuid,
#                 ['read', 'notify'],
#                 service)
#         self.notifying = False
#         self.value_lvl = 100
#         gobject.timeout_add(5000, self.change_value)
#
#     def notify(self):
#         if not self.notifying:
#             return
#         message = { 'Value': [dbus.ByteArray(self.value_lvl)] }
#         self.PropertiesChanged(GATT_CHRC_IFACE, message, [])
#
#     def change_value(self):
#         if self.value_lvl > 0:
#             self.value_lvl -= 2
#             if self.value_lvl < 0:
#                 self.value_lvl = 0
#         self.notify()
#         return True
#
#     def readValueHandler(self):
#         return self.value_lvl
#
#     def startNotifyHandler(self):
#         if self.notifying:
#             print('Already notifying, nothing to do')
#             return
#
#         print('Starting notifying', self.__class__.__name__)
#         self.notifying = True
#         self.notify()
#
#     def stopNotifyHandler(self):
#         if not self.notifying:
#             print('Not notifying, nothing to do')
#             return
#
#         print('Stopping notifying', self.__class__.__name__)
#         self.notifying = False
#
#
# class WWCharacteristic(Characteristic):
#
#     def __init__(self, bus, index, uuid, service):
#         Characteristic.__init__(
#                 self, bus, index,
#                 uuid,
#                 ['write-without-response', 'write'],
#                 service)
#         self.value_lvl = 100
#
#     def readValueHandler(self):
#         return self.value_lvl
#
#     def writeValueHandler(self, value):
#         self.value_lvl = value
#
#
# class RWWNCharacteristic(Characteristic):
#
#     def __init__(self, bus, index, uuid, service):
#         Characteristic.__init__(
#                 self, bus, index,
#                 uuid,
#                 ['read', 'write-without-response', 'write', 'notify'],
#                 service)
#         self.notifying = False
#         self.value_lvl = 100
# #         gobject.timeout_add(5000, self.change_value)
#
#     def notifyValue(self, value):
#         self.value_lvl = value
#         self.notify()
#
#     def notify(self):
#         if not self.notifying:
#             return
#         wrapped = self._wrap(self.value_lvl)
#         message = { 'Value': wrapped }
#         print(self.__class__.__name__, 'notify:', self.value_lvl)
#         self.PropertiesChanged(GATT_CHRC_IFACE, message, [])
#
#     def readValueHandler(self):
#         return self.value_lvl
#
#     def writeValueHandler(self, value):
#         self.value_lvl = value
#
#     def startNotifyHandler(self):
#         if self.notifying:
#             print('Already notifying, nothing to do')
#             return
#
#         print('Starting notifying', self.__class__.__name__)
#         self.notifying = True
#
#     def stopNotifyHandler(self):
#         if not self.notifying:
#             print('Not notifying, nothing to do')
#             return
#
#         print('Stopping notifying', self.__class__.__name__)
#         self.notifying = False
#
#
# class Descriptor(dbus.service.Object):
#     def __init__(self, bus, index, uuid, flags, characteristic):
#         self.path = characteristic.path + '/desc' + str(index)
#         self.bus = bus
#         self.uuid = uuid
#         self.flags = flags
#         self.chrc = characteristic
#         dbus.service.Object.__init__(self, bus, self.path)
#
#     def get_properties(self):
#         return {
#                 GATT_DESC_IFACE: {
#                         'Characteristic': self.chrc.get_path(),
#                         'UUID': self.uuid,
#                         'Flags': self.flags,
#                 }
#         }
#
#     def get_path(self):
#         return dbus.ObjectPath(self.path)
#
#     @dbus.service.method(DBUS_PROP_IFACE,
#                          in_signature='s',
#                          out_signature='a{sv}')
#     def GetAll(self, interface):
#         if interface != GATT_DESC_IFACE:
#             raise InvalidArgsException()
#
#         return self.get_properties[GATT_CHRC_IFACE]
#
#     @dbus.service.method(GATT_DESC_IFACE, out_signature='ay')
#     def ReadValue(self):
#         print('Default ReadValue called, returning error')
#         raise NotSupportedException()
#
#     @dbus.service.method(GATT_DESC_IFACE, in_signature='ay')
#     def WriteValue(self, value):
#         print('Default WriteValue called, returning error')
#         raise NotSupportedException()
