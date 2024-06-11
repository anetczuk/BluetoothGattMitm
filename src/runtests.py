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

import sys
import os

import unittest
import argparse
import cProfile
import subprocess

try:
    import coverage
except ImportError:
    print("Missing coverage module. Try running 'pip install coverage'")
    print("Python info:", sys.version)
    raise

import tempfile


script_dir = os.path.dirname(os.path.abspath(__file__))


## ============================= main section ===================================


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test runner")
    parser.add_argument(
        "-rt", "--runtest", action="store", required=False, default="", help="Module with tests, e.g. test.test_class"
    )
    parser.add_argument(
        "-r", "--repeat", action="store", type=int, default=0, help="Repeat tests given number of times"
    )
    parser.add_argument("-ut", "--untilfailure", action="store_true", help="Run tests in loop until failure")
    parser.add_argument("-cov", "--coverage", action="store_true", help="Measure code coverage")
    parser.add_argument("--profile", action="store_true", help="Profile the code")
    parser.add_argument("--pfile", action="store", default=None, help="Profile the code and output data to file")

    args = parser.parse_args()

    coverageData = None
    ## start code coverage
    if args.coverage is True:
        print("Executing code coverage")
        currScript = os.path.realpath(__file__)
        coverageData = coverage.Coverage(branch=True, omit=currScript)
        ##coverageData.load()
        coverageData.start()

    if len(args.runtest) > 0:
        suite = unittest.TestLoader().loadTestsFromName(args.runtest)
    else:
        suite = unittest.TestLoader().discover(script_dir)

    testsRepeats = int(args.repeat)

    profiler = None

    try:
        ## start code profiler
        profiler_outfile = args.pfile
        if args.profile is True or profiler_outfile is not None:
            print("Starting profiler")
            profiler = cProfile.Profile()
            profiler.enable()

        ## run proper tests
        if args.untilfailure is True:
            counter = 1
            while True:
                print("Tests iteration:", counter)
                counter += 1
                testResult = unittest.TextTestRunner().run(suite)
                if testResult.wasSuccessful() is False:
                    break
                print("\n")
        elif testsRepeats > 0:
            for counter in range(1, testsRepeats + 1):
                print("Tests iteration:", counter)
                testResult = unittest.TextTestRunner().run(suite)
                if testResult.wasSuccessful() is False:
                    break
                print("\n")
        else:
            unittest.TextTestRunner().run(suite)

    finally:
        ## stop profiler
        if profiler is not None:
            profiler.disable()
            if profiler_outfile is None:
                print("Generating profiler data")
                profiler.print_stats(1)
            else:
                print("Storing profiler data to", profiler_outfile)
                profiler.dump_stats(profiler_outfile)

            if profiler_outfile is not None:
                ##pyprof2calltree -i $PROF_FILE -k
                print("Launching: pyprof2calltree -i {} -k".format(profiler_outfile))
                subprocess.call(["pyprof2calltree", "-i", profiler_outfile, "-k"])

        ## prepare coverage results
        if coverageData is not None:
            ## convert results to html
            tmprootdir = tempfile.gettempdir()
            revCrcTmpDir = tmprootdir + "/revcrc"
            if not os.path.exists(revCrcTmpDir):
                os.makedirs(revCrcTmpDir)
            htmlcovdir = revCrcTmpDir + "/htmlcov"

            coverageData.stop()
            coverageData.save()
            coverageData.html_report(directory=htmlcovdir)
            print("\nCoverage HTML output:", (htmlcovdir + "/index.html"))
