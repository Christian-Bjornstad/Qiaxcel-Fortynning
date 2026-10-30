"""Generated PDFs test the actual PDF library without distributing sample data."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from openpyxl import load_workbook
from test_core import analyze
from qiaxcel.core import read_pdf

ROOT = Path(__file__).resolve().parents[1]


def make_pdf(path, page_texts):
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for lines in page_texts:
        page_id = len(objects) + 1
        content_id = page_id + 1
        kids.append(f'{page_id} 0 R')
        objects.append((f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                        f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>').encode())
        operations = ['BT /F1 11 Tf 40 790 Td 16 TL']
        for line in lines.splitlines():
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            operations.append(f'({escaped}) Tj T*')
        data = ('\n'.join(operations) + '\nET').encode('ascii')
        objects.append(f'<< /Length {len(data)} >>\nstream\n'.encode() + data + b'\nendstream')
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
    start = len(output)
    output.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    Path(path).write_bytes(output)


class IntegrationTests(unittest.TestCase):
    def test_real_pdf_reader_cli_and_excel_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf, out = Path(tmp) / 'demo.pdf', Path(tmp) / 'result.xlsx'
            make_pdf(pdf, ['Position: A1 Run Date: test\nSample Info: TERT\n',
                          'Result Table\nSize Height Size Height\n[bp] [RFU] [bp] [RFU]\n'
                          '1 15 1.44 2 192 3.10\n3 1000 1.59'])
            samples = read_pdf(pdf)
            self.assertEqual(samples[0].peaks[1].page, 2)
            self.assertEqual(analyze(samples[0], factor=1000).rfu, 3100)
            result = subprocess.run([sys.executable, str(ROOT / 'start_python_felles.py'),
                                     '--input', str(pdf), '--output', str(out), '--factor', '1000'],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout)
            wb = load_workbook(out)
            self.assertEqual(wb['Resultater']['G2'].value, 3100)
            wb.close()

    def test_help_works_with_windows_console_encoding(self):
        import os
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        result = subprocess.run([sys.executable, str(ROOT / 'start_python_felles.py'), '--help'],
                                env=env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
