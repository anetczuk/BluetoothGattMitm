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
from typing import Dict, Any, List

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

# from btgattmitm.bleakconnector import BleakConnector
from btgattmitm.bluepyconnector import BluepyConnector

from btgattmitm.mitmmanager import MitmManager

from btgattmitm.hcitool.advertisement import is_mac_address, find_hci_iface_by_mac, get_hci_ifaces


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


def start_mitm(args: Dict[str, Any]):
    iface: int = args["iface"]  ## interface index of local device
    connectto: str = args["connectto"]  ## mac of device to connect to
    noconnect: bool = args["noconnect"]
    addrtype: str = args["addrtype"]  ## 'public' or 'random'
    advname: str = args["advname"]
    advserviceuuids: List[str] = args["advserviceuuids"]
    sudo_mode: bool = args["sudo"]
    change_mac: str = args["changemac"]
    devicestorepath: str = args["devicestorepath"]
    deviceloadpath: str = args["deviceloadpath"]

    connection: AbstractConnector = None
    mitm_service: MitmManager = None
    try:
        device_config: Dict[str, Any] = {}
        if deviceloadpath:
            device_config = dataio.load_from(deviceloadpath)

        if connectto is None:
            connectto = device_config.get("connectto")

        if change_mac == "False":
            change_mac = None
        elif change_mac == "True":
            change_mac = connectto

        mitm_service = MitmManager(iface_index=iface, sudo_mode=sudo_mode, change_mac=change_mac)

        if noconnect is False and connectto is not None:
            if addrtype is None:
                addrtype = device_config.get("addrtype")
            # connection = BleakConnector(btServiceAddress)
            connection = BluepyConnector(connectto, iface=iface, address_type=addrtype)
        else:
            _LOGGER.info("Device connection skipped")

        valid_clone = mitm_service.configure(connection, device_config)
        if valid_clone is False:
            _LOGGER.error("unable to configure device")
            return False

        if advname is None:
            advname = device_config.get("advname", None)

        if advname:
            if mitm_service.advertisement:
                mitm_service.advertisement.set_local_name(advname)
        if advserviceuuids:
            if mitm_service.advertisement:
                mitm_service.advertisement.set_service_uuid_list(advserviceuuids)

        if devicestorepath:
            _LOGGER.debug("Storing device configuration to %s", devicestorepath)
            device_dump_config: Dict[str, Any] = {}
            if advname:
                device_dump_config["advname"] = advname
            if connectto:
                device_dump_config["connectto"] = connectto
            device_dump_config["addrtype"] = connection.get_address_type()
            device_dump_config["advertisement"] = mitm_service.get_adv_config()
            device_dump_config["scanresponse"] = mitm_service.get_scanresp_config()
            services_list = connection.get_services()
            device_dump_config["services"] = ServiceData.dump_config(services_list)

            try:
                dataio.dump_to(device_dump_config, devicestorepath)
            except Exception as exc:  # pylint: disable=W0703
                _LOGGER.error(f"unable to store config: {exc}")
                _LOGGER.info("data:\n%s", pprint.pformat(device_dump_config))

        ## start advertisement and notification listening
        mitm_service.start()

    finally:
        _LOGGER.info("disconnecting application")
        if mitm_service is not None:
            mitm_service.stop()
        if connection is not None:
            connection.disconnect()
        _LOGGER.info("application end")

    return True


## ========================================================================


## iface_data - index, device name or MAC address
def find_iface_index(iface_data: str) -> int:
    try:
        return int(iface_data)
    except ValueError:
        ## unable to convert - assuming 'iface_data' contains MAC or device name
        pass

    device_name = None
    if is_mac_address(iface_data):
        device_name = find_hci_iface_by_mac(iface_data)
    else:
        device_name = iface_data

    if device_name is None:
        return None
    device_index_str = device_name[3:]
    return int(device_index_str)


def main():
    parser = argparse.ArgumentParser(description="Bluetooth GATT MITM")
    parser.add_argument(
        "--iface",
        action="store",
        required=False,
        default="hci0",
        help="Local adapter to use: integer (eg. 0), device name (eg. hci0) or MAC address (eg. 00:11:22:33:44:55)",
    )
    parser.add_argument("--connectto", action="store", required=False, help="BT address to connect to")
    parser.add_argument(
        "--noconnect", action="store_const", const=True, default=False, help="Do not connect even if 'connectto' passed"
    )
    parser.add_argument(
        "--addrtype", action="store", required=False, help="Address type to connect ('public' or 'random'"
    )
    parser.add_argument("--advname", action="store", required=False, help="Device name to advertise (override device)")
    parser.add_argument(
        "--advserviceuuids",
        nargs="*",
        action="store",
        required=False,
        help="List of service UUIDs to advertise (override device)",
    )
    parser.add_argument(
        "--sudo", action="store_const", const=True, default=False, help="Run terminal commands with sudo if required"
    )
    parser.add_argument(
        "--changemac",
        nargs="?",
        default=None,
        const=True,
        help="Change MAC address: boolean(True or False) or target MAC address",
    )
    parser.add_argument("--devicestorepath", action="store", required=False, help="Store device configuration to file")
    parser.add_argument(
        "--deviceloadpath",
        action="store",
        required=False,
        help="Load device configuration from file",
    )

    args = parser.parse_args()

    logDir = os.getcwd()
    log_file = os.path.join(logDir, "log.txt")

    configure_logger(log_file)

    _LOGGER.debug("Starting the application")
    _LOGGER.debug("Logger log file: %s", log_file)

    exitCode = 0

    try:
        name_mac_list: List[List[str]] = get_hci_ifaces()
        if len(name_mac_list) == 1:
            args.iface = name_mac_list[0][0]
            args.iface = args.iface[3:]
        else:
            args.iface = find_iface_index(args.iface)
            if args.iface is None:
                _LOGGER.error("unable to found adapter index by %s", args.iface)
                sys.exit(exitCode)

        _LOGGER.info("Found adapter index: %s", args.iface)

        args_dict = vars(args)
        valid = start_mitm(args_dict)
        if valid is False:
            exitCode = 1

    # except BluetoothError as e:
    #     print("Error: ", e, " check if BT is powered on")

    except:  # noqa    # pylint: disable=W0702
        _LOGGER.error("Exception occured")
        raise

    sys.exit(exitCode)


if __name__ == "__main__":
    main()
