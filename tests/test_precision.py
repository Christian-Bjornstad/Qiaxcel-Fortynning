import math
import unittest
from test_core import Peak, Sample, analyze
from qiaxcel.core import review_result


class PrecisionTests(unittest.TestCase):
    def sample(self, peaks):
        return Sample('synthetic.pdf', 'A01', 'TERT', 1, peaks)

    def test_ambiguous_window_must_never_default_to_tallest(self):
        r = analyze(self.sample([Peak(190, 3.1, 2), Peak(201, 8.9, 2)]), factor=1000)
        self.assertIsNone(r.peak)
        self.assertIsNone(r.rfu)
        self.assertEqual(r.dilution, '')
        self.assertIn('Velg', r.note)

    def test_missing_height_candidate_is_not_ignored(self):
        r = analyze(self.sample([Peak(190, 3.1, 2), Peak(200, None, 2)]), factor=1000)
        self.assertIsNone(r.rfu)

    def test_explicit_bp_links_to_that_height_not_tallest(self):
        r = analyze(self.sample([Peak(190, 3.1, 2), Peak(201, 8.9, 2)]),
                    factor=1000, target_bp=190)
        self.assertEqual(r.peak.bp, 190)
        self.assertEqual(r.rfu, 3100)
        self.assertEqual(r.target_bp, 190)
        self.assertEqual(r.status, 'KONTROLL')

    def test_size_only_single_candidate_retains_bp_without_zero_rfu(self):
        r = analyze(self.sample([Peak(190, None, 2)]), factor=1000)
        self.assertEqual(r.peak.bp, 190)
        self.assertIsNone(r.rfu)
        self.assertIn('høyde', r.note)

    def test_target_missing_out_of_range_or_duplicate_is_blocked(self):
        sample = self.sample([Peak(190, 3.1, 2), Peak(190, 2.1, 3), Peak(500, 6.0, 3)])
        for bp in (190, 195, 500, float('nan')):
            with self.subTest(bp=bp):
                r = analyze(sample, factor=1000, target_bp=bp)
                self.assertIsNone(r.rfu)
                self.assertEqual(r.status, 'KONTROLL')

    def test_nan_negative_and_overflow_heights_cannot_be_export_ready(self):
        for value in (float('nan'), float('inf'), -1, 1e308):
            r = analyze(self.sample([Peak(190, value, 2)]), factor=1000)
            self.assertIsNone(r.rfu)
            self.assertEqual(r.status, 'KONTROLL')

    def test_review_cannot_invent_a_bp_between_two_table_candidates(self):
        r = analyze(self.sample([Peak(190, 3.1, 2), Peak(201, 8.9, 2)]), factor=1000)
        with self.assertRaises(ValueError):
            review_result(r, assay='TERT', bp=195, raw_height=3.1, reviewer='TEST',
                          comment='Synthetic', chosen_dilution='1:5')

    def test_review_retains_selected_page_not_first_candidate_page(self):
        r = analyze(self.sample([Peak(190, 3.1, 2), Peak(201, 8.9, 3)]), factor=1000)
        revised = review_result(r, assay='TERT', bp=201, raw_height=8.9, reviewer='TEST',
                                comment='Synthetic', chosen_dilution='1:20')
        self.assertEqual(revised.peak.page, 3)
        self.assertEqual(revised.target_bp, 201)
        self.assertEqual(revised.peak.method, 'PDF-tabell')

    def test_graph_target_not_in_size_table_requires_explicit_provenance(self):
        r = analyze(self.sample([Peak(15, 2, 3), Peak(1000, 4, 3)]), factor=1000)
        r.sample.table_page = 3
        with self.assertRaises(ValueError):
            review_result(r, assay='TERT', bp=190, raw_height=3.1, reviewer='TEST',
                          comment='Synthetic', chosen_dilution='1:5')
        revised = review_result(r, assay='TERT', bp=190, raw_height=3.1, reviewer='TEST',
                                comment='Graph label 190 bp, calibrated', chosen_dilution='1:5',
                                source_page=2, method='Kalibrert grafavlesning')
        self.assertEqual((revised.peak.bp, revised.peak.page, revised.rfu), (190, 2, 3100))

    def test_graph_page_can_precede_table_but_not_other_sample_range(self):
        r = analyze(self.sample([Peak(190, None, 3)]), factor=1000)
        r.sample.header_page = 2
        r.sample.table_page = 3
        revised = review_result(r, assay='TERT', bp=190, raw_height=3.1, reviewer='TEST',
                                comment='Graph on preceding page', chosen_dilution='1:5',
                                source_page=2, method='Kalibrert grafavlesning')
        self.assertEqual(revised.peak.page, 2)
        self.assertEqual(revised.sample.peaks[0].page, 3)
        for bad_page in (1, 4):
            with self.assertRaises(ValueError):
                review_result(r, assay='TERT', bp=190, raw_height=3.1, reviewer='TEST',
                              comment='Bad source', chosen_dilution='1:5',
                              source_page=bad_page, method='Kalibrert grafavlesning')

    def test_signed_review_rejects_changed_pdf(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / 'demo.pdf'
            pdf.write_bytes(b'synthetic changed content')
            sample = self.sample([Peak(190, 3.1, 2)])
            sample.source = str(pdf)
            sample.source_sha256 = 'old-hash'
            r = analyze(sample, factor=1000)
            with self.assertRaises(ValueError):
                review_result(r, assay='TERT', bp=190, raw_height=3.1, reviewer='TEST',
                              comment='Review after source changed', chosen_dilution='1:5')
