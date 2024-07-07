#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2017 Arkadiusz Netczuk <dev.arnet@gmail.com>
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

try:
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=W0611
    import __init__
except ImportError:
    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded
    pass

import sys
import os
import pprint

import argparse
import logging.handlers

from btgattmitm import dataio
from btgattmitm.connector import AbstractConnector, ServiceData

# from btgattmitm.bluepyconnector import BluepyConnector as Connector
from btgattmitm.bleakconnector import BleakConnector as Connector
from btgattmitm.mitmmanager import MitmManager


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


def configure_logger(logFile):
    loggerFormat = "%(asctime)s,%(msecs)-3d %(levelname)-8s %(threadName)s [%(filename)s:%(lineno)d] %(message)s"
    loggerDate = "%Y-%m-%d %H:%M:%S"

    streamHandler = logging.StreamHandler(stream=sys.stdout)
    fileHandler = logging.handlers.RotatingFileHandler(filename=logFile, maxBytes=1024 * 1024, backupCount=5)

    if sys.version_info >= (3, 3):
        #### for Python 3.3
        logging.basicConfig(
            format=loggerFormat, datefmt=loggerDate, level=logging.NOTSET, handlers=[streamHandler, fileHandler]
        )
    else:
        #### for Python 2
        rootLogger = logging.getLogger()
        rootLogger.setLevel(logging.NOTSET)

        logFormatter = logging.Formatter(loggerFormat, loggerDate)

        streamHandler.setLevel(logging.NOTSET)
        streamHandler.setFormatter(logFormatter)
        rootLogger.addHandler(streamHandler)

        fileHandler.setLevel(logging.NOTSET)
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)

    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.setLevel(logging.INFO)

    bleak_logger = logging.getLogger("bleak")
    bleak_logger.setLevel(logging.INFO)


def start_mitm(btServiceAddress, listenMode, bt_name, bt_service_uuids,
               deviceconfig_path, dumpdevice_path):
    connection = None
    device = None
    try:
        device = MitmManager()

        prepare_sample = True

        if btServiceAddress is not None:
            connection: AbstractConnector = Connector(btServiceAddress)
            # connection = BluepyConnector(btServiceAddress)

            valid_clone = device.configure_clone(connection, listenMode)
            if valid_clone is False:
                _LOGGER.warning("unable to connect to device")
                return False
            prepare_sample = False

        if deviceconfig_path:
            device_config = dataio.load_from(deviceconfig_path)
            if bt_name is None:
                bt_name = device_config.get("name", None)
            if device.configure_config(device_config):
                prepare_sample = False

        if prepare_sample:
            if device.configure_sample() is False:
                _LOGGER.warning("unable to configure sample service")
                return False

        if bt_name:
            device.advertisement.set_local_name(bt_name)
        if bt_service_uuids:
            device.advertisement.set_service_uuid_list(bt_service_uuids)

        if dumpdevice_path:
            _LOGGER.debug("Storing device configuration to %s", dumpdevice_path)
            device_dump_config = {}
            if bt_name:
                device_dump_config["name"] = bt_name
            if btServiceAddress:
                device_dump_config["address"] = btServiceAddress
            device_dump_config["advertisement"] = device.get_advertisement_config()
            device_dump_config["services"] = device.get_services_config()

            try:
                dataio.dump_to(device_dump_config, dumpdevice_path)
            except Exception as exc:
                _LOGGER.error(f"unable to store config: {exc}")
                _LOGGER.info("data:\n%s", pprint.pformat(device_dump_config))

        device.start()

    finally:
        _LOGGER.info("disconnecting application")
        if device is not None:
            device.stop()
        if connection is not None:
            connection.disconnect()

    return True


## ========================================================================


def main():
    parser = argparse.ArgumentParser(description="Bluetooth GATT MITM")
    parser.add_argument("--connect", action="store", required=False, help="BT address to connect to")
    parser.add_argument("--bt-name", action="store", required=False, help="Device name to advertise")
    parser.add_argument(
        "--bt-service-uuids", nargs="*", action="store", required=False, help="List of service UUIDs to advertise"
    )
    parser.add_argument(
        "--listen",
        action="store_const",
        const=True,
        default=False,
        help="Automatically subscribe for all notifications from service",
    )
    parser.add_argument("--devicefromcfg", action="store", required=False, help="Load device configuration from file")
    parser.add_argument("--dumpdevice", action="store", required=False, help="Store device configuration to file")

    args = parser.parse_args()

    logDir = os.path.join(SCRIPT_DIR, "../../tmp/log")
    if os.path.isdir(logDir) is False:
        logDir = os.getcwd()
    log_file = os.path.join(logDir, "log.txt")

    configure_logger(log_file)

    _LOGGER.debug("Starting the application")
    _LOGGER.debug("Logger log file: %s" % log_file)

    exitCode = 0

    try:
        valid = start_mitm(args.connect, args.listen, args.bt_name, args.bt_service_uuids,
                           args.devicefromcfg, args.dumpdevice)
        if valid is False:
            exitCode = 1

    # except BluetoothError as e:
    #     print("Error: ", e, " check if BT is powered on")

    except:  # noqa    # pylint: disable=W0702
        _LOGGER.exception("Exception occured")
        raise

    sys.exit(exitCode)


if __name__ == "__main__":
    main()
