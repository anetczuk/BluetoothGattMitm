#!/usr/bin/python2
#
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

import sys
import os

#### append local library
script_dir = os.path.dirname(__file__) 
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__), "..") ))
# sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__), "../../lib") ))
 
import time 
import argparse
import logging.handlers
import cProfile

from btgattmitm.connector import Connector
from btgattmitm.mitmdevice import MITMDevice



_LOGGER = logging.getLogger(__name__)



def configureLogger(logFile):
    loggerFormat = '%(asctime)s,%(msecs)-3d %(levelname)-8s %(threadName)s [%(filename)s:%(lineno)d] %(message)s'
    loggerDate = '%Y-%m-%d %H:%M:%S'
    
    streamHandler = logging.StreamHandler( stream = sys.stdout )
    fileHandler = logging.handlers.RotatingFileHandler( filename = logFile, maxBytes=1024*1024, backupCount=5 )
    
    if sys.version_info >= (3, 3):
        #### for Python 3.3
        logging.basicConfig( format = loggerFormat,
                             datefmt = loggerDate, 
                             level = logging.NOTSET,
                             handlers = [ streamHandler, fileHandler ]
                             )
    else:
        #### for Python 2
        rootLogger = logging.getLogger()
        rootLogger.setLevel( logging.NOTSET )
        
        logFormatter = logging.Formatter( loggerFormat, loggerDate )
        
        streamHandler.setLevel( logging.NOTSET )
        streamHandler.setFormatter( logFormatter )
        rootLogger.addHandler( streamHandler )
        
        fileHandler.setLevel( logging.NOTSET )
        fileHandler.setFormatter( logFormatter )
        rootLogger.addHandler( fileHandler )


def startMITM(btServiceAddress):
#     with Connector(btServiceAddress) as connection:

    connection = None
    device = None
    try:
        connection = Connector(btServiceAddress)
        device = MITMDevice()
        device.start( connection )
    finally:
        if device != None:
            device.stop()
        if connection != None:
            connection.disconnect()
    
    return 0



## ========================================================================



if __name__ != '__main__':
    sys.exit(0)
    
parser = argparse.ArgumentParser(description='Bluetooth GATT MITM')
parser.add_argument('--profile', action='store_const', const=True, default=False, help='Profile the code' )
parser.add_argument('--pfile', action='store', default=None, help='Profile the code and output data to file' )
# parser.add_argument('--mode', action='store', required=True, choices=["BF", "POLY", "COMMON"], help='Mode' )
# parser.add_argument('--file', action='store', required=True, help='File with data' )
parser.add_argument('--connect', action='store', required=True, help='BT address to connect to' )
 

args = parser.parse_args()


logDir = os.path.join(script_dir, "../../tmp")
if os.path.isdir( logDir ) == False:
    logDir = os.getcwd()
logFile = os.path.join(logDir, "log.txt")
    
configureLogger( logFile )


_LOGGER.debug("Starting the application")
_LOGGER.debug("Logger log file: %s" % logFile)


starttime = time.time()
profiler = None

exitCode = 0


try:
 
    profiler_outfile = args.pfile
    if args.profile == True or profiler_outfile != None:
        print( "Starting profiler" )
        profiler = cProfile.Profile()
        profiler.enable()

        
    exitCode = startMITM( args.connect )


# except BluetoothError as e:
#     print "Error: ", e, " check if BT is powered on"

except:
    _LOGGER.exception("Exception occured")
    raise

finally:
    _LOGGER.info( "" )                    ## print new line
    if profiler != None:
        profiler.disable()
        if profiler_outfile == None:
            _LOGGER.info( "Generating profiler data" )
            profiler.print_stats(1)
        else:
            _LOGGER.info( "Storing profiler data to %s", profiler_outfile )
            profiler.dump_stats( profiler_outfile )
            _LOGGER.info( "pyprof2calltree -k -i %s", profiler_outfile )
         
    timeDiff = (time.time()-starttime)*1000.0
    _LOGGER.info( "Calculation time: {:13.8f}ms\n\n".format(timeDiff) )
    
    sys.exit(exitCode)

