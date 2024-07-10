#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest
from btgattmitm import dataio


class DataIOTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass

    def tearDown(self):
        ## Called after testfunction was executed
        pass

    def test_dump_bytearray(self):
        input_data = bytearray([1, 2, 3])
        out = dataio.dump(input_data)
        # self.assertEqual("""!!python/object/apply:builtins.bytearray\n- "\\x01\\x02\\x03"\n- latin-1\n""", out)

        restored_data = dataio.load(out)
        self.assertEqual(input_data, restored_data)

    def test_dump_dict(self):
        input_data = {1: "aaa", 2: "bbb"}
        out = dataio.dump(input_data)
        # self.assertEqual("""1: aaa\n2: bbb\n""", out)

        restored_data = dataio.load(out)
        self.assertEqual(input_data, restored_data)

    def test_dump_dict_double(self):
        input_data = {"aaa": {2: "bbb"}}
        out = dataio.dump(input_data)
        # self.assertEqual("""aaa:\n  2: bbb\n""", out)

        restored_data = dataio.load(out)
        self.assertEqual(input_data, restored_data)
