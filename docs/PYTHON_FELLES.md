# Python FELLES og vanlig Windows

Hele prosjektmappen må ligge samlet i en fast plassering. Python 3.11 eller nyere kreves. Avhengighetene er PyQt6, pdfplumber og openpyxl. Første installasjon trenger tilgang til en Python-pakkekilde.

1. Start `QIAXCEL_INSTALL.cmd`.
2. Når Python FELLES åpner via Ivanti: lim inn kommandoen fra utklippstavlen og trykk Enter.
3. Lukk FELLES etter installasjon.
4. Start `QIAXCEL_START.cmd`, lim inn oppstartskommandoen og trykk Enter.

CMD-filene følger eksisterende FELLES-mønster: `pwrgate.exe`, app-ID 15694, base64-kodet `runpy`-kommando og kjøring inne i vertstolken. Installereren bruker pip in-process og `--user -e` mot prosjektmappen. Programmet starter ikke en ny python.exe inne fra FELLES. Det bruker det samme Python-brukerområdet som andre FELLES-programmer, så avhengigheter deles. Administratorrettigheter trengs ikke. Start en frisk tolk etter oppdateringer.

På en vanlig Windows-PC uten Ivanti finner CMD-filene Python-launcheren eller python.exe. `QIAXCEL_PYTHON` kan angi en bestemt lokal tolk og `QIAXCEL_IVANTI` en annen Ivanti-bane. Python direkte:

```powershell
python install_python_felles.py
python start_python_felles.py
```

Kjør lokal CLI med `python start_python_felles.py --help`. Gjennom Ivanti starter CMD-filen vinduet uten CLI-argumenter. For CLI inne i FELLES brukes `runpy.run_path(<sti>, run_name='qiaxcel_cli')['main'](argv=[...])`.

Rapporter behandles lokalt. Programmet har ingen opplasting, telemetri, nettjeneste eller automatisk overvåking av rapportmapper. Kun pip-installasjon kontakter pakkekilden. Oppstartsfeil logges i `%LOCALAPPDATA%/QIAxcel Fortynning/logs/bootstrap.log`. Nettverksdisk, Ivanti og GUI-støtte må prøves på arbeidsmaskinen; lokale tester bekrefter ikke disse eksterne forholdene.
