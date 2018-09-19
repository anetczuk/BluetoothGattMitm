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
import logging
import cProfile

from btgattmitm.connector import Connector
from btgattmitm.mitmdevice import MITMDevice



_LOGGER = logging.getLogger(__name__)



def startMITM(btServiceAddress):
    connection = Connector(btServiceAddress)
    device = MITMDevice()
    device.start( connection )
    return 0



if __name__ != '__main__':
    sys.exit(0)
    
parser = argparse.ArgumentParser(description='Bluetooth GATT MITM')
parser.add_argument('--profile', action='store_const', const=True, default=False, help='Profile the code' )
parser.add_argument('--pfile', action='store', default=None, help='Profile the code and output data to file' )
# parser.add_argument('--mode', action='store', required=True, choices=["BF", "POLY", "COMMON"], help='Mode' )
# parser.add_argument('--file', action='store', required=True, help='File with data' )
parser.add_argument('--connect', action='store', required=True, help='BT address to connect to' )
 
  

args = parser.parse_args()


loggerFormat = '%(asctime)s,%(msecs)-3d %(levelname)-8s %(threadName)s [%(filename)s:%(lineno)d] %(message)s'

logDir = os.path.join(script_dir, "../../tmp")
if os.path.isdir( logDir ) == False:
    logDir = os.getcwd()
    
logFile = os.path.join(logDir, "log.txt")    

logging.basicConfig( format = loggerFormat,
                     datefmt = '%H:%M:%S', 
                     level = logging.DEBUG,
                     handlers=[ logging.FileHandler( filename = logFile, mode = "a+" ),
                                logging.StreamHandler( stream = sys.stdout )]
                     )

_LOGGER.debug("\n\n")
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

except Exception as e:
    ## handle thrown exception properly -- it happens that sometimes some exceptions
    ## are ignored without any message
    _LOGGER.exception(e)

finally:
    print( "" )                    ## print new line
    if profiler != None:
        profiler.disable()
        if profiler_outfile == None:
            print( "Generating profiler data" )
            profiler.print_stats(1)
        else:
            print( "Storing profiler data to", profiler_outfile )
            profiler.dump_stats( profiler_outfile )
            print( "pyprof2calltree -k -i", profiler_outfile )
         
    timeDiff = (time.time()-starttime)*1000.0
    print( "Calculation time: {:13.8f}ms".format(timeDiff) )
    
    sys.exit(exitCode)

