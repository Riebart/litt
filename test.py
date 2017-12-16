#!/usr/bin/env python3

import imp
import unittest
import collections

imp.load_source("tt", "./tt")


class LITTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass


class StopwatchTests(LITTTest):
    pass


if __name__ == "__main__":
    unittest.main()
