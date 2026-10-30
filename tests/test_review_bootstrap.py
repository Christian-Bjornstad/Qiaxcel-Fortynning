from pathlib import Path
import runpy
import sys
import unittest

from test_core import Peak, Sample, analyze
from qiaxcel.core import review_result

ROOT = Path(__file__).resolve().parents[1]


class ReviewTests(unittest.TestCase):
    def test_manual_review_keeps_original_and_requires_comment(self):
        result = analyze(Sample('report.pdf', 'A01', 'IDH', 1,
                                 [Peak(210, 3.0, 2)]), factor=1000)
        with self.assertRaises(ValueError):
            review_result(result, assay='IDH1', bp=210, raw_height=3,
                          reviewer='GM', comment='', chosen_dilution='1:5')
        revised = review_result(result, assay='IDH1', bp=210, raw_height=3.1,
                                reviewer='GM', comment='Kontrollert mot graf', chosen_dilution='1:5')
        self.assertEqual(revised.status, 'KONTROLLERT')
        self.assertEqual(revised.rfu, 3100)
        self.assertEqual(revised.sample.peaks[0].height, 3.0)
        self.assertIn('Manuell', revised.peak.method)
        self.assertEqual(result.status, 'KONTROLL')
        with self.assertRaises(ValueError):
            review_result(result, assay='IDH1', bp=457, raw_height=3,
                          reviewer='GM', comment='x', chosen_dilution='1:5')

    def test_unconfirmed_scale_cannot_be_approved(self):
        result = analyze(Sample('a.pdf', 'A01', 'TERT', 1))
        with self.assertRaises(ValueError):
            review_result(result, assay='TERT', bp=190, raw_height=3,
                          reviewer='GM', comment='x', chosen_dilution='1:5')


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.old_path = list(sys.path)
        self.addCleanup(setattr, sys, 'path', self.old_path)

    def test_start_does_not_inherit_felles_arguments_or_start_subprocess(self):
        ns = runpy.run_path(str(ROOT / 'start_python_felles.py'), run_name='test_felles')
        captured = []
        old = sys.argv
        sys.argv = ['ivanti', '--host-flag']
        try:
            result = ns['start'](app_main=lambda args: captured.append(args))
        finally:
            sys.argv = old
        self.assertEqual(result, 0)
        self.assertEqual(captured, [[]])
        ns['start'](app_main=lambda args: captured.append(args), argv=['--help'])
        self.assertEqual(captured[-1], ['--help'])
        self.assertEqual(ns['start'](app_main=lambda args: 2, argv=['--input', 'bad.pdf']), 2)

    def test_install_uses_inprocess_pip_user_and_source_folder(self):
        ns = runpy.run_path(str(ROOT / 'install_python_felles.py'), run_name='test_install')
        called, imported = [], []
        ns['install'](pip_main=lambda args: called.append(args), importer=imported.append)
        self.assertIn('--user', called[0])
        self.assertIn('-e', called[0])
        self.assertIn('qiaxcel.gui', imported)
        self.assertIn('pdfplumber', imported)


if __name__ == '__main__':
    unittest.main()
