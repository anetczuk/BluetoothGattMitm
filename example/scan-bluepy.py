#!/usr/bin/env python3

import sys
import logging

from bluepy.btle import Scanner, DefaultDelegate


streamHandler = logging.StreamHandler(stream=sys.stdout)
logging.basicConfig(level=logging.NOTSET, handlers=[streamHandler])

_LOGGER = logging.getLogger(__name__)


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, scanEntry, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", scanEntry.addr)
        elif isNewData:
            print("Received new data from", scanEntry.addr)


if __name__ == "__main__":
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)

    for dev in devices:
        print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            print("  %s = %s" % (desc, value))
