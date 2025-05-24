#!/usr/bin/env python3

import pprint

import array
from random import randint

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject


mainloop = None

BLUEZ_SERVICE_NAME = "org.bluez"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESC_IFACE = "org.bluez.GattDescriptor1"

LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.InvalidValueLength"


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.Failed"


class Application(dbus.service.Object):
    """org.bluez.GattApplication1 interface implementation."""

    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(HeartRateService(bus, 0))
        self.add_service(BatteryService(bus, 1))
        self.add_service(TestService(bus, 2))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        print("GetManagedObjects")

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """org.bluez.GattService1 interface implementation."""

    PATH_BASE = "/org/bluez/example/service"

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(self.get_characteristic_paths(), signature="o"),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """org.bluez.GattCharacteristic1 interface implementation."""

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.get_descriptor_paths(), signature="o"),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, _, _2):
        # def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print("Default StartNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print("Default StopNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, _, _2, _3):
        # def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """org.bluez.GattDescriptor1 interface implementation."""

    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/desc" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {GATT_DESC_IFACE: {"Characteristic": self.chrc.get_path(), "UUID": self.uuid, "Flags": self.flags}}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, _, _2):
        # def WriteValue(self, value, options):
        print("Default WriteValue called, returning error")
        raise NotSupportedException()


class HeartRateService(Service):
    """Fake Heart Rate Service that simulates a fake heart beat and control point behavior."""

    HR_UUID = "0000180d-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HR_UUID, True)
        self.add_characteristic(HeartRateMeasurementChrc(bus, 0, self))
        self.add_characteristic(BodySensorLocationChrc(bus, 1, self))
        self.add_characteristic(HeartRateControlPointChrc(bus, 2, self))
        self.energy_expended = 0


class HeartRateMeasurementChrc(Characteristic):
    HR_MSRMT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.HR_MSRMT_UUID, ["read", "indicate"], service)
        self.notifying = False
        self.hr_ee_count = 0

    def hr_msrmt_cb(self):
        value = []
        value.append(dbus.Byte(0x06))

        value.append(dbus.Byte(randint(90, 130)))  # nosec

        if self.hr_ee_count % 10 == 0:
            value[0] = dbus.Byte(value[0] | 0x08)
            value.append(dbus.Byte(self.service.energy_expended & 0xFF))
            value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xFF))

        self.service.energy_expended = min(0xFFFF, self.service.energy_expended + 1)
        self.hr_ee_count += 1

        print("Updating value: " + repr(value))

        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

        return self.notifying

    def _update_hr_msrmt_simulation(self):
        print("Update HR Measurement Simulation")

        if not self.notifying:
            return

        GObject.timeout_add(1000, self.hr_msrmt_cb)

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
            return

        self.notifying = True
        self._update_hr_msrmt_simulation()

    def StopNotify(self):
        if not self.notifying:
            print("Not notifying, nothing to do")
            return

        self.notifying = False
        self._update_hr_msrmt_simulation()


class BodySensorLocationChrc(Characteristic):
    BODY_SNSR_LOC_UUID = "00002a38-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.BODY_SNSR_LOC_UUID, ["read"], service)

    def ReadValue(self, _):
        # def ReadValue(self, options):
        # Return 'Chest' as the sensor location.
        return [0x01]


class HeartRateControlPointChrc(Characteristic):
    HR_CTRL_PT_UUID = "00002a39-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.HR_CTRL_PT_UUID, ["write"], service)

    def WriteValue(self, value, _):
        # def WriteValue(self, value, options):
        print("Heart Rate Control Point WriteValue called")

        if len(value) != 1:
            raise InvalidValueLengthException()

        byte = value[0]
        print("Control Point value: " + repr(byte))

        if byte != 1:
            raise FailedException("0x80")

        print("Energy Expended field reset!")
        self.service.energy_expended = 0


class BatteryService(Service):
    """Fake Battery service that emulates a draining battery."""

    BATTERY_UUID = "180f"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """Fake Battery Level characteristic.

    The battery level is drained by 2 points
    every 5 seconds.
    """

    BATTERY_LVL_UUID = "2a19"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.BATTERY_LVL_UUID, ["read", "notify"], service)
        self.notifying = False
        self.battery_lvl = 100
        GObject.timeout_add(5000, self.drain_battery)

    def notify_battery_level(self):
        if not self.notifying:
            return
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": [dbus.Byte(self.battery_lvl)]}, [])

    def drain_battery(self):
        if not self.notifying:
            return True
        if self.battery_lvl > 0:
            self.battery_lvl -= 2
            self.battery_lvl = max(self.battery_lvl, 0)
        print("Battery Level drained: " + repr(self.battery_lvl))
        self.notify_battery_level()
        return True

    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("Battery Level read: " + repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def StartNotify(self):
        if self.notifying:
            print("Already notifying, nothing to do")
            return

        self.notifying = True
        self.notify_battery_level()

    def StopNotify(self):
        if not self.notifying:
            print("Not notifying, nothing to do")
            return

        self.notifying = False


class TestService(Service):
    """Dummy test service that provides characteristics and descriptors that exercise various API functionality."""

    TEST_SVC_UUID = "12345678-1234-5678-1234-56789abcdef0"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        self.add_characteristic(TestEncryptCharacteristic(bus, 1, self))
        self.add_characteristic(TestSecureCharacteristic(bus, 2, self))


class TestCharacteristic(Characteristic):
    """Dummy test characteristic.

    Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.
    """

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef1"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.TEST_CHRC_UUID, ["read", "write", "writable-auxiliaries"], service
        )
        self.value = []
        self.add_descriptor(TestDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("TestCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, _):
        # def WriteValue(self, value, options):
        print("TestCharacteristic Write: " + repr(value))
        self.value = value


class TestDescriptor(Descriptor):
    """Dummy test descriptor. Returns a static value."""

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef2"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index, self.TEST_DESC_UUID, ["read", "write"], characteristic)

    def ReadValue(self, _):
        # def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """Writable CUD descriptor."""

    CUD_UUID = "2901"

    def __init__(self, bus, index, characteristic):
        self.writable = "writable-auxiliaries" in characteristic.flags
        self.value = array.array("B", b"This is a characteristic for testing")
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index, self.CUD_UUID, ["read", "write"], characteristic)

    def ReadValue(self, _):
        # def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, _):
        # def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class TestEncryptCharacteristic(Characteristic):
    """Dummy test characteristic requiring encryption."""

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef3"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.TEST_CHRC_UUID, ["encrypt-read", "encrypt-write"], service)
        self.value = []
        self.add_descriptor(TestEncryptDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("TestEncryptCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, _):
        # def WriteValue(self, value, options):
        print("TestEncryptCharacteristic Write: " + repr(value))
        self.value = value


class TestEncryptDescriptor(Descriptor):
    """Dummy test descriptor requiring encryption. Returns a static value."""

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef4"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index, self.TEST_DESC_UUID, ["encrypt-read", "encrypt-write"], characteristic)

    def ReadValue(self, _):
        # def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


class TestSecureCharacteristic(Characteristic):
    """Dummy test characteristic requiring secure connection."""

    TEST_CHRC_UUID = "12345678-1234-5678-1234-56789abcdef5"

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.TEST_CHRC_UUID, ["secure-read", "secure-write"], service)
        self.value = []
        self.add_descriptor(TestSecureDescriptor(bus, 2, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, _):
        # def ReadValue(self, options):
        print("TestSecureCharacteristic Read: " + repr(self.value))
        return self.value

    def WriteValue(self, value, _):
        # def WriteValue(self, value, options):
        print("TestSecureCharacteristic Write: " + repr(value))
        self.value = value


class TestSecureDescriptor(Descriptor):
    """Dummy test descriptor requiring secure connection. Returns a static value."""

    TEST_DESC_UUID = "12345678-1234-5678-1234-56789abcdef6"

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index, self.TEST_DESC_UUID, ["secure-read", "secure-write"], characteristic)

    def ReadValue(self, _):
        # def ReadValue(self, options):
        return [dbus.Byte("T"), dbus.Byte("e"), dbus.Byte("s"), dbus.Byte("t")]


def register_app_cb():
    print("GATT application registered")


def register_app_error_cb(error):
    print("Failed to register application: " + str(error))
    mainloop.quit()


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None


# ============================================================


class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = {}
        properties["Type"] = self.ad_type
        if self.service_uuids is not None:
            properties["ServiceUUIDs"] = dbus.Array(self.service_uuids, signature="s")
        if self.solicit_uuids is not None:
            properties["SolicitUUIDs"] = dbus.Array(self.solicit_uuids, signature="s")
        if self.manufacturer_data is not None:
            properties["ManufacturerData"] = dbus.Dictionary(self.manufacturer_data, signature="qv")
        if self.service_data is not None:
            properties["ServiceData"] = dbus.Dictionary(self.service_data, signature="sv")
        if self.local_name is not None:
            properties["LocalName"] = dbus.String(self.local_name)
        if self.include_tx_power:
            properties["Includes"] = dbus.Array(["tx-power"], signature="s")

        if self.data is not None:
            properties["Data"] = dbus.Dictionary(self.data, signature="yv")
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature="qv")
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature="y")

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature="sv")
        self.service_data[uuid] = dbus.Array(data, signature="y")

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature="yv")
        self.data[ad_type] = dbus.Array(data, signature="y")

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        try:
            print("GetAll")
            if interface != LE_ADVERTISEMENT_IFACE:
                raise InvalidArgsException()
            props_dict = self.get_properties()
            print("returning props")
            pprint.pprint(props_dict)
            return props_dict[LE_ADVERTISEMENT_IFACE]
        except BaseException as exc:
            print("exception:", exc)
            raise

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("%s: Released!" % self.path)


class TestAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        # self.add_local_name("TestAdvertisement2")
        self.add_local_name("TestServer")
        # self.add_service_uuid("180D")
        # self.add_service_uuid("180F")
        # self.add_manufacturer_data(0xFFFF, [0x00, 0x01, 0x02, 0x03])
        # self.add_service_data("9999", [0x00, 0x01, 0x02, 0x03, 0x04])
        # self.include_tx_power = True
        # self.add_data(0x26, [0x01, 0x01, 0x00])


def register_ad_cb():
    print("Advertisement registered")


def register_ad_error_cb(error):
    print("Failed to register advertisement: " + str(error))
    mainloop.quit()


# ============================================================


def main():
    global mainloop  # pylint: disable=W0603

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print("GattManager1 interface not found")
        return

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), DBUS_PROP_IFACE)
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE)
    test_advertisement = TestAdvertisement(bus, 0)

    service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE)

    app = Application(bus)

    mainloop = GObject.MainLoop()

    print("Registering GATT application...")

    ad_manager.RegisterAdvertisement(
        test_advertisement.get_path(), {}, reply_handler=register_ad_cb, error_handler=register_ad_error_cb
    )

    service_manager.RegisterApplication(
        app.get_path(), {}, reply_handler=register_app_cb, error_handler=register_app_error_cb
    )

    mainloop.run()

    ad_manager.UnregisterAdvertisement(test_advertisement)
    print("Advertisement unregistered")
    dbus.service.Object.remove_from_connection(test_advertisement)


if __name__ == "__main__":
    main()
