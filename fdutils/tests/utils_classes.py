__author__ = 'Filinto Duran (duranto@gmail.com)'
import unittest

from fdutils.capabilities import *


class TestUtils(unittest.TestCase):

    def test_with_capabilities_bin(self):
        NOTHING = 0
        CAP1 = 1
        CAP2 = 1 << 1
        CAP3 = 1 << 2
        CAP4 = 1 << 3
        CAP5 = 1 << 4

        c = WithCapabilities()
        c.add_capability(CAP1)
        c.add_capability(CAP2)
        self.assertTrue(c.can(CAP1))
        self.assertTrue(c.can(CAP2))
        self.assertTrue(c.can(CAP3 | CAP2))
        self.assertFalse(c.can(CAP3))
        c.remove_capability(CAP2)
        self.assertFalse(c.can(CAP2))
        # checking double removing is idempotent
        c.remove_capability(CAP2)
        self.assertFalse(c.can(CAP2))
        c.add_capability(CAP4 | CAP5)
        self.assertTrue(c.can(CAP5))
        self.assertTrue(c.can(CAP4))
        self.assertTrue(c.cannot(CAP2))
        c.disable_capability(CAP1 | CAP2)
        self.assertFalse(c.can(CAP1))
        # it can do nothing
        self.assertTrue(c.can(NOTHING))



