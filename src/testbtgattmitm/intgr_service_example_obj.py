#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
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
from typing import Any, Dict, List

import logging
import argparse

from btgattmitm.main import configure_logger, find_interface
from btgattmitm.mitmmanager import MitmManager
from btgattmitm.connector import AbstractConnector
from btgattmitm.dbusobject.service import Service
from btgattmitm.gattmock import ServiceMock, CharacteristicMock
from btgattmitm.constants import GATT_CHRC_IFACE


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


_LOGGER = logging.getLogger(__name__)


class LocalCharacteristic(CharacteristicMock):

    def __init__(self, chUuid: str, cHandler: int, flags: List[str], bus, index: int, service: Service):  # noqa
        CharacteristicMock.__init__(self, chUuid, cHandler, flags, bus, index, service, None)
        self.currValue = None

    def readValueHandler(self):
        return self.currValue

    def writeValueHandler(self, value):
        self.currValue = value
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])


def start_mitm(args: Dict[str, Any]) -> bool:
    iface: int = args["iface"]  ## interface index of local device

    mitm_service = None
    try:
        mitm_service = MitmManager(iface_index=iface, sudo_mode=True, change_mac=None)

        connector: AbstractConnector = None

        service = ServiceMock("00000333-0000-1000-8000-000000000333", mitm_service.bus, 0)
        charProps = ["read", "write", "notify"]
        char = LocalCharacteristic("00000444-0000-1000-8000-000000000444", 8, charProps, mitm_service.bus, 0, service)
        service.add_characteristic(char)
        mitm_service.gatt_application.add_service(service)

        mitm_service.configure_notifications(connector)

        advname = "TestService"
        if advname:
            if mitm_service.advertisement:
                mitm_service.advertisement.set_local_name(advname)

        mitm_service.start()

    finally:
        _LOGGER.info("disconnecting application")
        if mitm_service:
            mitm_service.stop()

    return True


def main():
    parser = argparse.ArgumentParser(description="Bluetooth GATT MITM Test")
    parser.add_argument(
        "--iface",
        action="store",
        required=False,
        default="hci0",
        help="Local adapter to use: integer (eg. 0), device name (eg. hci0) or MAC address (eg. 00:11:22:33:44:55)",
    )
    parser.add_argument(
        "--sudo", action="store_const", const=True, default=False, help="Run terminal commands with sudo if required"
    )

    args = parser.parse_args()

    configure_logger()

    _LOGGER.debug("Starting the application")

    exitCode = 0

    try:
        args.iface = find_interface(args.iface)
        _LOGGER.info("Found adapter index: %s", args.iface)

        args_dict = vars(args)
        valid = start_mitm(args_dict)
        if valid is False:
            exitCode = 1

    except:  # noqa    # pylint: disable=W0702
        _LOGGER.error("Exception occured")
        raise

    sys.exit(exitCode)


# =============================================================


if __name__ == "__main__":
    main()
    sys.exit(0)
