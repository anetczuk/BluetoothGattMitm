#
# Code based on:
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
#        https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
#


DBUS_OM_IFACE       = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE     = 'org.freedesktop.DBus.Properties'

BLUEZ_SERVICE_NAME           = 'org.bluez'
GATT_MANAGER_IFACE           = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE       = 'org.bluez.LEAdvertisement1'

GATT_SERVICE_IFACE  = 'org.bluez.GattService1'
GATT_CHRC_IFACE     = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE     = 'org.bluez.GattDescriptor1'

