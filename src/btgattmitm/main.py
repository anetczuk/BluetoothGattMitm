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

import time
import argparse
import logging.handlers
import cProfile

from btgattmitm.connector import BluepyConnector
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


def start_mitm(btServiceAddress, listenMode):
    connection = None
    device = None
    try:
        connection = BluepyConnector(btServiceAddress)
        device = MitmManager()
        device.start(connection, listenMode)
    finally:
        if device is not None:
            device.stop()
        if connection is not None:
            connection.disconnect()

    return 0


## ========================================================================


if __name__ != "__main__":
    sys.exit(0)

parser = argparse.ArgumentParser(description="Bluetooth GATT MITM")
parser.add_argument("--profile", action="store_const", const=True, default=False, help="Profile the code")
parser.add_argument("--pfile", action="store", default=None, help="Profile the code and output data to file")
# parser.add_argument('--mode', action='store', required=True, choices=["BF", "POLY", "COMMON"], help='Mode' )
# parser.add_argument('--file', action='store', required=True, help='File with data' )
parser.add_argument("--connect", action="store", required=True, help="BT address to connect to")
parser.add_argument(
    "--listen",
    action="store_const",
    const=True,
    default=False,
    help="Automatically subscribe for all notifications from service",
)


args = parser.parse_args()


logDir = os.path.join(SCRIPT_DIR, "../../tmp")
if os.path.isdir(logDir) is False:
    logDir = os.getcwd()
log_file = os.path.join(logDir, "log.txt")

configure_logger(log_file)


_LOGGER.debug("Starting the application")
_LOGGER.debug("Logger log file: %s" % log_file)


starttime = time.time()
profiler = None

exitCode = 0


try:

    profiler_outfile = args.pfile
    if args.profile is True or profiler_outfile is not None:
        print("Starting profiler")
        profiler = cProfile.Profile()
        profiler.enable()

    exitCode = start_mitm(args.connect, args.listen)


# except BluetoothError as e:
#     print("Error: ", e, " check if BT is powered on")

except:  # noqa    # pylint: disable=W0702
    _LOGGER.exception("Exception occured")
    raise

finally:
    _LOGGER.info("")  ## print new line
    if profiler is not None:
        profiler.disable()
        if profiler_outfile is None:
            _LOGGER.info("Generating profiler data")
            profiler.print_stats(1)
        else:
            _LOGGER.info("Storing profiler data to %s", profiler_outfile)
            profiler.dump_stats(profiler_outfile)
            _LOGGER.info("pyprof2calltree -k -i %s", profiler_outfile)

    timeDiff = (time.time() - starttime) * 1000.0
    _LOGGER.info("Calculation time: {:13.8f}ms\n\n".format(timeDiff))

    sys.exit(exitCode)
