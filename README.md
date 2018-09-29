## Bluetooth GATT Man In The Middle

This is console application allowing listening and intercepting Bluetooth GATT 
protocol of certain service. Typical use case is listening messages between some 
Bluetooth device and client application when communication protocol is unknown.

When started, application registers the same Bluetooth services as target device 
and waits for client to connect. Then the application mediates in communication 
allowing to reveal the protocol.


### Running

Execute:

*./btgattmitm/main.py --connect=AA:BB:CC:DD:EE:FF*

where *AA:BB:CC:DD:EE:FF* is address of GATT service, then connect within client 
application to created MITM service.


### Android test apps

There are several Android applications allowing writing custom messages and 
reading data from Bluetooth services. Two among them:
- BLE Tool
- GATTBrowser


### Troubleshootings:
- when application is started then it is impossible to discover the NITM device --
workaround is to directly insert address of MITM service


### Use example of:
- dbus with threads
- bluez library
- defining method decorators (*synchronied.py*)


### ToDo:
- fix registration of Generic Access and Generic Attribute Profile
- implement 'indicate' mode


### References:
- https://github.com/Vudentz/BlueZ
- https://dbus.freedesktop.org/doc/dbus-python/index.html
- https://ianharvey.github.io/bluepy-doc/index.html

