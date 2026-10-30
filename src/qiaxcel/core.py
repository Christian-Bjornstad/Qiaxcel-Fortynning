"""ScreenGel text reader and explicit laboratory-supplied selection rules."""
from dataclasses import dataclass, field, replace
import math
import hashlib
from pathlib import Path
import re
from typing import Iterable


ASSAYS = {
    'TERT': 185, 'BRAF': 270, 'IDH1': 200, 'IDH2': 218,
    'H3F3A': 255, 'H3C2': 304, 'H3C3': 276, 'H3C14': 311,
    'CTNNB1': 263, 'FOXL2': 279, 'KIT exon 9': 275, 'KIT exon 11': 223,
    'PDGFRA exon 12': 202, 'PDGFRA exon 18': 230,
    'POLE exon 9': 286, 'POLE exon 11': 288, 'POLE exon 14': 282,
    'POLE exon 13': 345, 'ABL-B': 401, 'ABL-C': 457, 'ABL-D': 353,
}
PATTERNS = {name: re.compile(r'(?<![A-Z0-9])' + re.escape(name) + r'(?![A-Z0-9])')
            for name in ASSAYS if 'exon' not in name and not name.startswith('ABL-')}
PATTERNS.update({
    'IDH1': re.compile(r'(?<![A-Z0-9])IDH\s*1(?![A-Z0-9])'),
    'IDH2': re.compile(r'(?<![A-Z0-9])IDH\s*2(?![A-Z0-9])'),
    'CTNNB1': re.compile(r'(?<![A-Z0-9])(?:CTNNB1|CTNB1|B[ -]?CAT)(?![A-Z0-9])'),
    'FOXL2': re.compile(r'(?<![A-Z0-9])(?:FOXL2|FOX)(?![A-Z0-9])'),
})
for _name in ASSAYS:
    if 'exon' in _name:
        _gene, _, _exon = _name.split()
        PATTERNS[_name] = re.compile(r'(?<![A-Z0-9])' + _gene + r'\s*[-_ ]?\s*EX(?:ON)?\s*' + _exon + r'(?!\d)')
    elif _name.startswith('ABL-'):
        PATTERNS[_name] = re.compile(r'(?<![A-Z0-9])ABL(?:MUT)?\s*[-_ ]?\s*' + _name[-1] + r'(?![A-Z0-9])')


@dataclass
class Peak:
    bp: float
    height: float | None
    page: int
    method: str = 'PDF-tabell'


@dataclass
class Sample:
    source: str
    position: str
    info: str
    header_page: int
    peaks: list[Peak] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    source_sha256: str = ''
    table_page: int | None = None


@dataclass
class Result:
    sample: Sample
    assay: str | None
    expected: int | None
    peak: Peak | None
    rfu: float | None
    dilution: str
    status: str
    note: str
    factor: int | None
    tolerance: int
    override: bool = False
    reviewer: str = ''
    review_note: str = ''
    target_bp: float | None = None

    @property
    def candidates(self) -> list[Peak]:
        return candidates_for(self.sample, self.expected, self.tolerance)


def candidates_for(sample: Sample, expected: float | None, tolerance: int) -> list[Peak]:
    return [p for p in sample.peaks if expected is not None and
            math.isfinite(p.bp) and abs(p.bp - expected) <= tolerance]


def file_sha256(path: str | Path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalize_position(value: str) -> str:
    match = re.fullmatch(r'([A-Ha-h])0?([1-9]|1[0-2])', value.strip())
    if not match:
        raise ValueError(f'Ugyldig prøveposisjon: {value!r}')
    return f'{match[1].upper()}{int(match[2]):02d}'


def identify_assay(info: str) -> str | None:
    if re.search(r'(?<![A-Z0-9])IDH(?!\s*[12])', info.upper()):
        return None
    matches = [name for name, pattern in PATTERNS.items() if pattern.search(info.upper())]
    return matches[0] if len(matches) == 1 else None


def dilution(rfu: float) -> str:
    if not math.isfinite(rfu) or rfu < 0:
        raise ValueError('RFU må være et endelig, ikke-negativt tall.')
    if rfu < 1500:
        return 'Ufortynnet'
    if rfu < 2000:
        return '1:2'
    if rfu < 4000:
        return '1:5'
    if rfu <= 6000:
        return '1:10'
    return '1:15 eller 1:20'


def analyze(sample: Sample, *, factor: int | None = None, tolerance: int = 20,
            assay_override: str | None = None, target_bp: float | None = None) -> Result:
    if factor not in (None, 1, 1000):
        raise ValueError('RFU-faktor må være ubekreftet, 1 eller 1000.')
    if not 1 <= tolerance <= 50:
        raise ValueError('Søkevindu må være mellom 1 og 50 bp.')
    if assay_override is not None and assay_override not in ASSAYS:
        raise ValueError('Ukjent analysevalg.')
    assay = assay_override or identify_assay(sample.info)
    expected = ASSAYS.get(assay)
    candidates = candidates_for(sample, expected, tolerance)
    notes = list(sample.issues)
    peak = None
    if target_bp is not None:
        matches = [p for p in candidates if p.bp == target_bp]
        if len(matches) == 1:
            peak = matches[0]
        else:
            notes.append('Valgt bp må finnes nøyaktig én gang i søkevinduet')
    elif len(candidates) == 1:
        peak = candidates[0]
    if assay is None:
        notes.append('Ukjent eller tvetydig analyse – velg analyse manuelt')
    elif not candidates:
        notes.append('Ingen topp innenfor søkevinduet')
    if len(candidates) > 1:
        notes.append(f'{len(candidates)} topper i søkevinduet. Velg nøyaktig bp og kontroller PDF')
    if peak is not None and peak.height is None:
        notes.append('Valgt topp mangler høyde – les grafen eller registrer råhøyde manuelt')
    control = bool(re.search(r'(?i)\b(?:NTC|NTK|NEG|gDNA|negativ|positiv|kontroll|control)\b', sample.info))
    if control:
        notes.append('Kontrollprøve (NTC/gDNA/kontroll) – vurder separat')
    if factor is None:
        notes.append('RFU-skala ikke bekreftet')
    rfu = None
    if peak is not None and peak.height is not None:
        if not math.isfinite(peak.height) or peak.height < 0:
            notes.append('Ugyldig topphøyde – verdien brukes ikke')
        elif factor is not None:
            converted = peak.height * factor
            if math.isfinite(converted):
                rfu = converted
            else:
                notes.append('RFU-omregning ga ugyldig tall – verdien brukes ikke')
    suggestion = dilution(rfu) if rfu is not None and not control else ''
    if rfu is not None:
        if any(abs(rfu - limit) <= limit * 0.10 for limit in (1500, 2000, 4000, 6000)):
            notes.append('Nær fortynningsgrense (±10 %) – kontroller kategori')
        if rfu > 6000:
            notes.append('Over 6000: laboratoriet må velge 1:15 eller 1:20')
    return Result(sample, assay, expected, peak, rfu, suggestion,
                  'KONTROLL' if notes else 'KLAR', '; '.join(notes), factor,
                  tolerance, assay_override is not None, target_bp=target_bp)


NUMBER = r'\d+(?:[.,]\d+)?'
ROW = re.compile(r'^\d+\s+' + NUMBER + r'\s+' + NUMBER + r'(?:\s+\d+\s+' + NUMBER + r'\s+' + NUMBER + r')*$')
SIZE_ROW = re.compile(r'^\d+\s+' + NUMBER + r'(?:\s+\d+\s+' + NUMBER + r')*$')


def review_result(result: Result, *, assay: str, bp: float, raw_height: float,
                  reviewer: str, comment: str, chosen_dilution: str,
                  source_page: int | None = None, method: str | None = None) -> Result:
    """An explicit human review is kept alongside the unchanged original peaks."""
    if result.sample.source_sha256 and (not Path(result.sample.source).is_file() or
                                       file_sha256(result.sample.source) != result.sample.source_sha256):
        raise ValueError('Kildefilen er flyttet eller endret. Les den på nytt før signering.')
    if result.factor is None:
        raise ValueError('Bekreft RFU-skala før manuell kontroll.')
    if assay not in ASSAYS or not reviewer.strip() or not comment.strip():
        raise ValueError('Velg analyse og oppgi kontrollør og kontrollkommentar.')
    if not math.isfinite(bp) or bp <= 0 or not math.isfinite(raw_height) or raw_height < 0:
        raise ValueError('Peak bp og råhøyde må være gyldige, ikke-negative tall (bp > 0).')
    if abs(bp - ASSAYS[assay]) > result.tolerance:
        raise ValueError('Valgt topp ligger utenfor analysens søkevindu.')
    matching = [p for p in result.sample.peaks if p.bp == bp]
    candidates = candidates_for(result.sample, ASSAYS[assay], result.tolerance)
    if len(matching) > 1 or (candidates and len(matching) != 1):
        raise ValueError('Velg en unik bp-verdi fra rapportens toppliste.')
    if not matching and (source_page is None or not method):
        raise ValueError('Topp utenfor tabellisten krever eksplisitt grafside og avlesningsmetode.')
    if not math.isfinite(raw_height * result.factor):
        raise ValueError('RFU-omregning ga ugyldig verdi.')
    if chosen_dilution not in ('Ufortynnet', '1:2', '1:5', '1:10', '1:15', '1:20', 'Kontrollprøve'):
        raise ValueError('Velg en konkret fortynning, eller Kontrollprøve.')
    original_peak = matching[0] if matching else None
    page = original_peak.page if original_peak else (result.sample.table_page or result.sample.header_page)
    if source_page is not None:
        end_page = result.sample.table_page or page
        if not isinstance(source_page, int) or not result.sample.header_page <= source_page <= end_page:
            raise ValueError('Grafside må ligge mellom prøveoverskrift og resultattabell.')
        if source_page != page and not method:
            raise ValueError('Alternativ grafside krever eksplisitt avlesningsmetode.')
        page = source_page
    same_peak = original_peak is not None and original_peak.height == raw_height
    peak = original_peak if same_peak and method is None and page == original_peak.page else Peak(
        bp, raw_height, page, method or 'Manuell grafavlesning/korreksjon')
    return replace(result, assay=assay, expected=ASSAYS[assay], peak=peak,
                   rfu=raw_height * result.factor,
                   dilution='' if chosen_dilution == 'Kontrollprøve' else chosen_dilution,
                   status='KONTROLLERT', reviewer=reviewer.strip(), review_note=comment.strip(),
                   override=result.override or result.assay != assay, target_bp=bp)


def parse_pages(pages: Iterable[tuple[int, str]], source: str) -> list[Sample]:
    """Keep the active sample across pages; never pair tables by page number."""
    samples: list[Sample] = []
    current = None
    in_table = False
    valid_header = None
    ids: set[int] = set()
    table_count = 0

    def finish():
        if current is not None:
            if not current.peaks:
                current.issues.append('Ingen lesbar Size/Height-tabell')
            samples.append(current)

    for page_number, text in pages:
        for line in text.splitlines():
            line = line.strip()
            pos = re.match(r'^Position:\s*(\S+)', line)
            if pos:
                finish()
                current = Sample(source, normalize_position(pos[1]), '', page_number)
                in_table, valid_header = False, None
                ids = set()
                table_count = 0
            elif current is not None and line.startswith('Sample Info:'):
                current.info = line.partition(':')[2].strip()
            elif line == 'Result Table':
                if current is None:
                    raise ValueError(f'Resultattabell uten prøveoverskrift på side {page_number}.')
                table_count += 1
                current.table_page = page_number
                if table_count > 1:
                    current.issues.append('Flere resultattabeller for samme prøve')
                in_table, valid_header = True, None
            elif in_table and current is not None:
                if 'Size' in line and 'Height' in line:
                    valid_header = 'height'
                elif re.fullmatch(r'(?:Size\s*)+', line):
                    valid_header = 'size'
                    current.issues.append('Rapporttabellen mangler Height – les RFU fra grafen manuelt')
                elif (SIZE_ROW if valid_header == 'size' else ROW).fullmatch(line):
                    if not valid_header:
                        current.issues.append('Ukjent tabelloverskrift – verdier ikke brukt')
                        continue
                    parts = line.split()
                    stride = 2 if valid_header == 'size' else 3
                    for offset in range(0, len(parts), stride):
                        idx = int(parts[offset])
                        bp = float(parts[offset + 1].replace(',', '.'))
                        height = float(parts[offset + 2].replace(',', '.')) if stride == 3 else None
                        if idx in ids or idx != len(ids) + 1 or bp <= 0 or (height is not None and height < 0):
                            current.issues.append('Uventet toppnummer eller ugyldig verdi')
                        ids.add(idx)
                        current.peaks.append(Peak(bp, height, page_number))
                elif line.startswith(('Sample Header', 'Generated by', 'Figure:', 'Sample Comment', 'Plate ID:')):
                    in_table = False
                elif line and line[0].isdigit():
                    current.issues.append('Uleselig tallrad i resultattabell')
    finish()
    if not samples:
        raise ValueError('Ingen prøveoverskrifter funnet. Skannet PDF eller ukjent rapportformat støttes ikke.')
    return samples


def read_pdf(path: str | Path) -> list[Sample]:
    import pdfplumber
    path = Path(path).resolve()
    if path.suffix.lower() != '.pdf':
        raise ValueError('Velg en PDF-fil.')
    checksum = file_sha256(path)
    with pdfplumber.open(path) as document:
        def pages():
            for page in document.pages:
                yield page.page_number, page.extract_text() or ''
                page.close()
        samples = parse_pages(pages(), str(path))
    if checksum != file_sha256(path):
        raise ValueError('PDF-filen ble endret under lesing. Les filen på nytt.')
    for sample in samples:
        sample.source_sha256 = checksum
    return samples
