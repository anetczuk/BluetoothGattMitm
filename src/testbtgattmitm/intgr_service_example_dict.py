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
from typing import Any, Dict

import logging
import argparse

from btgattmitm.main import configure_logger, find_interface
from btgattmitm.mitmmanager import MitmManager
from btgattmitm.connector import AbstractConnector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


_LOGGER = logging.getLogger(__name__)


def start_mitm(args: Dict[str, Any]) -> bool:
    iface: int = args["iface"]  ## interface index of local device

    mitm_service = None
    try:
        mitm_service = MitmManager(iface_index=iface, sudo_mode=True, change_mac=None)

        connector: AbstractConnector = None
        device_config: Dict[str, Any] = {
            "services": {
                "00000111-0000-1000-8000-000000000111": {
                    "characteristics": {
                        "00000222-0000-1000-8000-000000000222": {
                            "descriptors": [],
                            "handle": 14,
                            "name": "00000222-0000-1000-8000-000000000222",
                            "properties": ["read", "write", "notify"],
                            "uuid": "00000222-0000-1000-8000-000000000222",
                            "value": 0,
                        },
                    },
                    "name": "111",
                    "uuid": "00000111-0000-1000-8000-000000000111",
                },
            },
        }
        valid_clone = mitm_service.configure(connector, device_config)
        if valid_clone is False:
            _LOGGER.error("unable to configure device")
            return False

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
