## Bluetooth GATT Man In The Middle

This is console application allowing listening and intercepting Bluetooth GATT/LE 
protocol of certain service. Typical use case is listening messages between some 
Bluetooth device and client application when communication protocol is unknown.

When started, application registers the same Bluetooth services as target device 
and waits for client to connect. Then the application mediates in communication 
allowing to reveal the protocol.


### Running

Typical setup consists of BLE *server* (some third party device), BLE *client* (e.g. smartphone app) and 
this *interceptor* application. To connect all parts perform following steps:
1. put *server* device into pairing mode (if applicable)
2. connect *interceptor* to the *server*
3. run third party test app on smartphone (e.g. GATTBrowser by Renesas) to check *interceptor* and pair/bond to the PC
4. run *client* application on the same smartphone to make requests to the *server*
5. observe messages (logs on services) printed on *iterceptor* while using *client* application

Execute example:

`./btgattmitm/main.py --connect=AA:BB:CC:DD:EE:FF`

where *AA:BB:CC:DD:EE:FF* is address of GATT service, then connect within client application to created MITM service.

Some devices require pairing to be performed during first connection.

Program options:

<!-- insertstart include="doc/help.txt" pre="\n\n```\n" post="```\n\n" -->

```

usage: main.py [-h] [--connect CONNECT] [--bt-name BT_NAME]
               [--bt-service-uuids [BT_SERVICE_UUIDS [BT_SERVICE_UUIDS ...]]]
               [--listen] [--dumpdevice DUMPDEVICE]
               [--devicefromcfg DEVICEFROMCFG]

Bluetooth GATT MITM

optional arguments:
  -h, --help            show this help message and exit
  --connect CONNECT     BT address to connect to
  --bt-name BT_NAME     Device name to advertise (override device)
  --bt-service-uuids [BT_SERVICE_UUIDS [BT_SERVICE_UUIDS ...]]
                        List of service UUIDs to advertise (override device)
  --listen              Automatically subscribe for all notifications from
                        service
  --dumpdevice DUMPDEVICE
                        Store device configuration to file
  --devicefromcfg DEVICEFROMCFG
                        Load device configuration from file ('connect' not
                        needed)
```

<!-- insertend -->


### Android test apps

There are several Android applications allowing writing custom messages and 
reading data from Bluetooth services. Two among them:
- GATTBrowser by Renesas
- nRF Connect (Nordic Semiconductor)


### ToDo:
- fix registration of Generic Access and Generic Attribute Profile
- implement 'indicate' mode


### References:
- https://github.com/Vudentz/BlueZ
- https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
- https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
- [D-Bus specification with Type System](https://dbus.freedesktop.org/doc/dbus-specification.html)
- [dbus-python binding module](https://dbus.freedesktop.org/doc/dbus-python/index.html)
- https://ianharvey.github.io/bluepy-doc/index.html
- https://punchthrough.com/creating-a-ble-peripheral-with-bluez/
- [Bluetooth LE commands](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-0f07d2b9-81e3-6508-ee08-8c808e468fed)
