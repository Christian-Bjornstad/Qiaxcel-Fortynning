# QIAxcel Fortynning

PyQt6-verktøy for å hente RFU for en valgt PCR-topp fra QIAxcel-PDF og eksportere til Excel.

## Start

På jobb-PC med Python FELLES:

1. Pakk ut hele mappen.
2. Kjør `QIAXCEL_INSTALL.cmd`, lim inn kommandoen i FELLES og trykk Enter.
3. Lukk FELLES etter installasjon.
4. Kjør `QIAXCEL_START.cmd` og lim inn oppstartskommandoen.

På vanlig Windows med Python 3.11+:

```powershell
python install_python_felles.py
python start_python_felles.py
```

## Bruk

1. Velg rapporter og les dem inn.
2. Velg analyse når rapporten mangler et entydig analysenavn.
3. Én kandidat i søkevinduet velges automatisk. Ved flere kandidater: velg nøyaktig bp og kontroller PDF.
4. Eksporter alle eller bare avklarte resultater.

RFU hentes fra Height i samme tabellrad som valgt bp. Standard: **2,71 × 1000 = 2710 RFU**. Råverdi og faktor beholdes i eksporten. Markørene ved15/1000 bp brukes ikke som PCR-resultat.

Eldre rapporter uten Height kan avleses med to y-referanser og et toppklikk. Dette krever manuell kontroll. Automatisk OCR er ikke implementert.

## Excel-mal

Malinnfylling bruker `.xlsx` og en [JSON-celleprofil](docs/malprofil_eksempel.json). Profilen må tilpasses den faktiske malen. Originalfilen endres ikke. Eksport til makromaler støttes ikke.

## CLI og tester

```powershell
python start_python_felles.py --input "rapport.pdf" --output "resultater.xlsx"
python start_python_felles.py --input "rapporter" --recursive --output "raadata.xlsx" --raw-only
python -m unittest discover -s tests -v
```

[Avlesning og eksportformat](docs/FORMAT.md) · [Python FELLES](docs/PYTHON_FELLES.md) · [Verifikasjon](docs/VALIDATION.md) · [Endringer](CHANGELOG.md)

Laboratorieregler, RFU-skala og jobb-PC-oppsett må kontrolleres før rutinebruk. Repoet inneholder kun kode og syntetiske tester. Uavhengig prosjekt; QIAxcel-navnet tilhører sin eier.

[GPL-3.0](LICENSE)
