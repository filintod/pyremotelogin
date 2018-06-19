import unittest

from fdutils.structures import *


__author__ = 'filinto'


class TestStructure(unittest.TestCase):

    def test_range(self):

        r1 = Range(1, 10)

        self.assertTrue(r1.length == 10)

        r2 = Range(5, 15)

        self.assertTrue(r2.length == 11)

        r3 = Range(-5, 4)

        self.assertTrue(r2 > r1)

        self.assertTrue(r1 > r3)

        self.assertTrue(r3 < r1)

        self.assertTrue(r2.overlaps(r1))

        self.assertTrue(r1.overlaps(r2))

        self.assertTrue(r1.overlaps(r3))

        self.assertFalse(r2.overlaps(r3))

        r4 = r2.union(r1)
        self.assertTrue(r4.length == 15)

        r5 = r2.union(Range(-5,0), True)
        self.assertTrue(r5 == (r2, Range(-5,0)))

        self.assertTrue([v for v in r1.values()] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        r5 = r2.intersection(r1)

        self.assertTrue([v for v in r5.values()] == [5,6,7,8,9,10])

        r2.union_update(Range(14, 20))

        self.assertTrue(r2.end == 20 and r2.start == 5)

        r2.intersection_update(Range(5, 12))

        self.assertTrue(r2.end == 12 and r2.start == 5)

        self.assertTrue(r2.is_subrange(Range(5, 12)))

        self.assertTrue(Range(5, 5).is_subrange(r2))

        self.assertFalse(r2.is_subrange(Range(5, 11)))

        r6 = Range(10, 20)
        rr = Range(18, 25)
        rl = Range(5, 12)
        rout = Range(22, 25)
        # remove out
        self.assertTrue(r6.difference(rout) == r6)
        # remove right
        self.assertTrue(r6.difference(rr) == Range(10, 17))
        # remove left
        self.assertTrue(r6.difference(rl) == Range(13, 20))
        # removes all
        self.assertTrue(r6.difference(Range(1, 22)) is None)

        rx = Range(1, 10)
        self.assertTrue(rx.difference(Range(10, 10)) == Range(1, 9))
        self.assertTrue(rx.difference(Range(2, 4), split_if_needed=True) == (Range(1, 1), Range(5, 10)))

        rx = Range(1, 10)
        self.assertTrue(rx.difference_update(Range(10, 10)) == Range(1, 9))
        with self.assertRaises(ValueError):
            rx.difference_update(Range(2, 4))


        r7 = Range(7, 10)
        r8 = Range(11, 15)
        r9 = Range(3, 6)
        self.assertTrue(r7.is_contiguous_to(r8) and r7.is_contiguous_to(r9))
        self.assertTrue(r7.union(r9) == Range(3, 10))

        self.assertTrue(Range(1, 9).overlaps(Range(9, 10)))