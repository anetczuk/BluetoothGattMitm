## Bluetooth GATT Man In The Middle

This is console application allowing listening and intercepting Bluetooth GATT/LE 
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
- GATTBrowser by Renesas
- BLE Tool


## Required libraries
- Python 3
- Linux *python-dbus* package (1.2.6-1)
- *bluepy* (1.3.0)


### Issues:
- when application is started then it is impossible to discover the MITM device --
workaround is to directly insert address of MITM service
- messages like *Unable to set arguments (dbus.ObjectPath('/org/bluez/example/service0'), {}) according to signature None: <type 'exceptions.ValueError'>: Unable to guess signature from an empty dict
* mean your bluepy library is *old* compared to DBus client


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
- https://github.com/Vudentz/BlueZ/blob/master/test/example-gatt-server
- https://github.com/Vudentz/BlueZ/blob/master/test/example-advertisement
