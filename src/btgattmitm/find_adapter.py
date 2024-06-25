##
##
##

import logging

import dbus

from btgattmitm.constants import DBUS_OM_IFACE
from btgattmitm.constants import BLUEZ_SERVICE_NAME, GATT_MANAGER_IFACE, LE_ADVERTISING_MANAGER_IFACE


_LOGGER = logging.getLogger(__name__)


def find_advertise_adapter(bus):
    serviceObj = bus.get_object(BLUEZ_SERVICE_NAME, "/")
    remote_om = dbus.Interface(serviceObj, DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    return find_object_with_key_old(objects, LE_ADVERTISING_MANAGER_IFACE)


def find_gatt_adapter(bus):
    serviceObj = bus.get_object(BLUEZ_SERVICE_NAME, "/")
    remote_om = dbus.Interface(serviceObj, DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    return find_object_with_key_old(objects, GATT_MANAGER_IFACE)


def find_object_with_key(objects, key):
    for obj, props in objects.items():
        pr = props.get(key)
        if pr is not None:
            _LOGGER.debug("item: %s %s", obj, pr)
            return obj
    return None


def find_object_with_key_old(objects, key):
    for obj, props in objects.items():
        if key in props:
            return obj
    return None
