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
import argparse
import logging

from bluepy import btle


streamHandler = logging.StreamHandler(stream=sys.stdout)
logging.basicConfig(level=logging.NOTSET, handlers=[streamHandler])

_LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Connecting to device using bluepy")
    parser.add_argument("--connect", action="store", required=True, help="BT address to connect to")

    args = parser.parse_args()
    address = args.connect

    # addrType = btle.ADDR_TYPE_PUBLIC
    addrType = btle.ADDR_TYPE_RANDOM
    _LOGGER.debug(f"connecting to device {address} type: {addrType}")
    try:
        conn = btle.Peripheral()
        conn.connect(address, addrType=addrType)
        _LOGGER.info("connected")
    except btle.BTLEException as ex:
        _LOGGER.warning("Unable to connect to the device %s, retrying: %s", address, ex)


if __name__ == "__main__":
    main()
