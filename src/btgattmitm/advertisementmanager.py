#
# MIT License
#
# Copyright (c) 2025 Arkadiusz Netczuk <dev.arnet@gmail.com>
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

from typing import List

from btgattmitm.connector import AdvertisementData


class AdvertisementManager:

    ## configuration of service
    def initialize(self):
        raise NotImplementedError()

    ## startup of service
    def register(self):
        raise NotImplementedError()

    ## stop of service
    def unregister(self):
        raise NotImplementedError()

    ## ======================================================

    def set_local_name(self, name: str):
        raise NotImplementedError()

    def set_service_uuid_list(self, service_list: List[str]):
        raise NotImplementedError()

    def get_adv_data(self) -> AdvertisementData:
        raise NotImplementedError()

    def get_scanresp_data(self) -> AdvertisementData:
        raise NotImplementedError()

    def add_adv_data(self, adv_data: AdvertisementData):
        raise NotImplementedError()

    def add_scanresp_data(self, scanresp_data: AdvertisementData):
        raise NotImplementedError()
