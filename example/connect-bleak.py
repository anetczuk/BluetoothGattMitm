#!/usr/bin/env python3
#
# MIT License
# 
# Copyright (c) 2024 Arkadiusz Netczuk <dev.arnet@gmail.com>
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

import sys
import time
import argparse
import logging
import pprint

import asyncio
import bleak
from bleak import BleakClient, BleakScanner


streamHandler = logging.StreamHandler( stream = sys.stdout )
logging.basicConfig( level = logging.NOTSET,
                     handlers = [ streamHandler ]
                     )

bleak_logger = logging.getLogger("bleak")
bleak_logger.setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Connecting to device using bleak')
    parser.add_argument('--connect', action='store', required=True, help='BT address to connect to' )

    args = parser.parse_args()
    address = args.connect

    _LOGGER.info(f"connecting to device {address}")

    async def connect_bleak(address):
        # devices = await BleakScanner.discover()
        # for dev in devices:
        #     _LOGGER.info(f"found {dev.metadata}")

        device = await BleakScanner.find_device_by_address(device_identifier=address, timeout=5.0)
        if device is None:
            _LOGGER.warning(f"unable to find device {address}")
            return

        _LOGGER.info(f"found {device}")

        async with BleakClient(device) as client:
            _LOGGER.info("connected")
            pprint.pprint(dir(client))

            client_data = client.services

            for item in client_data.services.values():
                _LOGGER.info(f"service: {item} {type(item)}")
                # pprint.pprint(dir(item))
                for char_item in item.characteristics:
                    _LOGGER.info(f"    char: {char_item}")

            # for item in client_data.characteristics.values():
            #     _LOGGER.info(f"char: {item} props: {item.properties}")
            #     value = await client.read_gatt_char(item.handle)
            #     _LOGGER.info(f"    value: {value}")

            for item in client_data.descriptors.values():
                _LOGGER.info(f"desc: {item}")

            value = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
            _LOGGER.info(f"    value: {value}")

            for handle in range(0, 40):
                data = client.read_gatt_descriptor(handle)
                _LOGGER.info(f"handle {handle} descriptor: {data.decode()}")

            # for service_item in client.services:
            #     _LOGGER.info(f"service: {service_item}")
            #     for char_item in service_item.characteristics:
            #         _LOGGER.info(f"    char: {char_item} props: {char_item.properties}")
            #         # value = await client.read_gatt_char(char_item.handle)
            #         # _LOGGER.info(f"    value: {value}")

    # async def connect_bleak(address):
    #     for _ in range(0, 100):
    #         try:
    #             async with BleakClient(address) as client:
    #                 _LOGGER.info("connected")
    #
    #                 # servs = client.get_services()
    #                 # _LOGGER.info(f"xxxx: {servs} {type(servs)}")
    #
    #                 for service_item in client.services:
    #                     _LOGGER.info(f"service: {service_item}")
    #                     for char_item in service_item.characteristics:
    #                         _LOGGER.info(f"    char: {char_item} props: {char_item.properties}")
    #                         # value = await client.read_gatt_char(char_item.handle)
    #                         # _LOGGER.info(f"    value: {value}")
    #             return
    #         except bleak.exc.BleakDeviceNotFoundError:
    #             _LOGGER.exception(f"exception received")
    #             return
    #         except bleak.exc.BleakDBusError as exc:
    #             _LOGGER.error(f"exception received: {exc}")
    #             #_LOGGER.exception(f"exception received")
    #         time.sleep(1)

    asyncio.run(connect_bleak(address))

    _LOGGER.info("exiting")


if __name__ == '__main__':
    main()
