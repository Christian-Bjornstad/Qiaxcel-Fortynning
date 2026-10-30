"""GUI by default; an explicit CLI for repeatable local batch processing."""
import argparse
import json
from pathlib import Path

from .core import ASSAYS, analyze, read_pdf
from .excel import export_workbook, fill_template


def main(argv=None):
    parser = argparse.ArgumentParser(description='QIAxcel PDF til Excel (lokal behandling)')
    parser.add_argument('--input', nargs='+', type=Path, help='PDF-filer eller mapper')
    parser.add_argument('--recursive', action='store_true', help='Ta med undermapper')
    parser.add_argument('--output', type=Path, help='Ny .xlsx-fil; overskriving er sperret')
    scale = parser.add_mutually_exclusive_group()
    scale.add_argument('--factor', type=int, choices=(1, 1000), default=1000,
                       help='RFU-faktor (standard 1000: 2,71 blir 2710 RFU)')
    scale.add_argument('--raw-only', action='store_true', help='Kun råverdier, ingen RFU/fortynning')
    parser.add_argument('--tolerance', type=int, default=20)
    parser.add_argument('--assay', choices=list(ASSAYS), help='Eksplisitt analyse for alle prøver i kjøringen')
    parser.add_argument('--template', type=Path)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--approved-only', action='store_true', help='Eksporter bare avklarte resultater')
    args = parser.parse_args(argv)
    if not 1 <= args.tolerance <= 50:
        parser.error('--tolerance må være mellom 1 og 50 bp')
    if not args.input:
        if args.output or args.template or args.profile:
            parser.error('--input kreves ved CLI-eksport')
        from .gui import launch
        return launch()
    if not args.output:
        parser.error('--output kreves med --input')
    if bool(args.template) != bool(args.profile):
        parser.error('--template og --profile må brukes sammen')
    try:
        paths = []
        for path in args.input:
            paths.extend(sorted(path.rglob('*.pdf') if args.recursive else path.glob('*.pdf')) if path.is_dir() else [path])
        paths = list(dict.fromkeys(p.resolve() for p in paths))
        if not paths:
            raise ValueError('Ingen PDF-filer funnet.')
        rows, errors = [], []
        for index, path in enumerate(paths, 1):
            print(f'Leser rapport {index}/{len(paths)} ...', flush=True)
            try:
                rows.extend(analyze(sample, factor=None if args.raw_only else args.factor, tolerance=args.tolerance,
                                    assay_override=args.assay) for sample in read_pdf(path))
            except Exception as exc:
                errors.append((str(path), str(exc)))
        if args.template:
            if errors:
                raise ValueError('Filfeil må løses før innfylling i mal.')
            fill_template(rows, args.template, json.loads(args.profile.read_text(encoding='utf-8-sig')), args.output)
        else:
            export_workbook(rows, args.output, errors=errors, approved_only=args.approved_only)
        print(f'Eksportert {len(rows)} prøver; {sum(r.status == "KONTROLL" for r in rows)} krever kontroll; {len(errors)} filfeil.')
        print(f'Lagret: {args.output.resolve()}')
        return 2 if errors else 0
    except Exception as exc:
        print(f'Kunne ikke fullføre: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
