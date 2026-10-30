"""Linear y-axis calibration, in the image's original coordinates.

Values must already be in RFU, including the chart's explicit multiplier.
The x-axis in ScreenGel is migration time: never interpolate bp from x.
No OCR and no automatic identification of an unlabeled peak is attempted.
"""
import math


def rfu_from_y(y0: float, value0: float, y1: float, value1: float,
               peak_y: float) -> float:
    if not all(math.isfinite(v) for v in (y0, value0, y1, value1, peak_y)):
        raise ValueError('Kalibreringspunkter må være endelige tall.')
    if min(value0, value1) < 0 or abs(y1 - y0) < 20:
        raise ValueError('Velg to adskilte y-aksepunkter (minst 20 bildepiksler) og RFU ≥0.')
    slope = (value1 - value0) / (y1 - y0)
    if slope >= 0:
        raise ValueError('RFU må øke oppover i grafen. Kontroller punktene og verdiene.')
    if not min(y0, y1) <= peak_y <= max(y0, y1):
        raise ValueError('Toppen må ligge mellom de to kalibreringsnivåene; ingen ekstrapolering.')
    return value0 + (peak_y - y0) * slope
