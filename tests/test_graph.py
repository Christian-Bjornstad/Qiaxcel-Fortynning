import unittest
from test_core import Peak
from qiaxcel.graph import rfu_from_y


class CalibrationTests(unittest.TestCase):
    def test_calibrate_in_real_rfu_not_report_raw_units(self):
        self.assertAlmostEqual(rfu_from_y(600, 0, 200, 5000, 352), 3100)
        self.assertAlmostEqual(rfu_from_y(600, 0, 200, 5, 352), 3.1)

    def test_points_can_be_entered_in_either_order(self):
        self.assertEqual(rfu_from_y(200, 5000, 600, 0, 352), 3100)

    def test_nonzero_baseline(self):
        self.assertEqual(rfu_from_y(600, 1000, 200, 5000, 300), 4000)

    def test_reject_wrong_axes_extrapolation_and_invalid_numbers(self):
        for args in [(600, 0, 600, 5000, 352), (200, 0, 600, 5000, 352),
                     (600, 0, 200, 5000, 100), (600, -1, 200, 5000, 352),
                     (600, 0, 200, float('nan'), 352), (600, 0, 595, 5000, 597)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                rfu_from_y(*args)
