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
"""
Implementation of method '@synchronized' decorator.

It reflects functionality
of 'synchronized' keyword from Java language.
It accepts one optional argument -- name of lock field declared within object.

Usage examples:

    @synchronized
    def send_dpg_write_command(self, dpgCommandType, data):
        pass

    @synchronized()
    def send_dpg_write_command(self, dpgCommandType, data):
        pass

    @synchronized("myLock")
    def send_dpg_write_command(self, dpgCommandType, data):
        pass

"""


import threading


##
## Definition of function decorator
##
def synchronized_with_arg(lock_name="_methods_lock"):
    def decorator(method):
        def synced_method(self, *args, **kws):
            lock = None
            if hasattr(self, lock_name) is False:
                lock = threading.RLock()
                setattr(self, lock_name, lock)
            else:
                lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)

        return synced_method

    return decorator


def synchronized(lock_name="_methods_lock"):
    if callable(lock_name):
        ### lock_name contains function to call
        return synchronized_with_arg("_methods_lock")(lock_name)
    return synchronized_with_arg(lock_name)
