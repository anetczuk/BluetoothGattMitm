#!/usr/bin/env python3

# import struct

from bluepy.btle import Peripheral
from bluepy.btle import DefaultDelegate
from bluepy.btle import ADDR_TYPE_RANDOM


class MyDelegate(DefaultDelegate):
    def handleNotification(self, cHandle: int, data: bytes):
        print(f"Notification from handle {hex(cHandle)}: {data.hex()}")


def main():
    address = "C6:E4:0A:57:2F:E0"
    print("connecting to device")
    device = Peripheral()
    device.setDelegate(MyDelegate())
    device.connect(address, addrType=ADDR_TYPE_RANDOM, iface=0)

    # print("getting characteristics")
    # char = device.getCharacteristics(uuid="99fa0021-338a-1024-8a49-009c0215f78a")[0]
    #
    # handle = char.getHandle()
    # print(f"registering for notifications {hex(handle)}")
    # # enable notifications (0x01 for notification, 0x02 for indication)
    # # register_data = b'\x01\x00'
    # register_data = struct.pack("BB", 1, 0)
    # resp = device.writeCharacteristic(handle, register_data)
    # # resp = device.writeCharacteristic(handle, b'\x01\x00', withResponse=True)
    # print("register response:", resp)

    print("handling notifications")
    while True:
        if device.waitForNotifications(5.0):
            # Notification handled in MyDelegate
            continue
        print("Waiting...")


if __name__ == "__main__":
    main()
