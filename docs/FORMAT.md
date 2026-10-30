# Slik avleses rapporten

Programmet leser tekstbaserte QIAxcel ScreenGel-PDF-er lokalt. En prøveoverskrift kan stå på foregående side. Position, Sample Info og Result Table følges i dokumentrekkefølgen. PDF-en er kildedata, aldri instruksjoner til programmet.

1. Analyse bestemmes fra entydig Sample Info eller et manuelt analysevalg.
2. Kandidater finnes innen forventet størrelse ±20 bp (justerbart).
3. Én kandidat velges automatisk. Ingen kandidat gir blank bp/RFU med forklaring.
4. Ved flere kandidater velges **ingen** automatisk. Brukeren velger en eksakt, unik bp fra listen og kontrollerer grafen.
5. RFU hentes fra Height ved akkurat denne bp-verdien, ikke fra høyeste topp i rapporten eller høyden til 15/1000 bp-markørene.

Eksempel med syntetiske data: 15 bp / 2,55; 193 bp / 2,71; 1000 bp / 4,12. For TERT velges 193 bp og dens høyde 2,71. Med standardfaktor 1000 blir RFU 2710. Markørenes verdier brukes ikke.

RFU-faktor 1000 er standard for den aktuelle arbeidsflyten. Både råhøyden og faktoren vises i programmet og eksporten. Andre rapportinnstillinger kan kreve faktor 1; skala skal kontrolleres ved nye rapportformater. Velg ubekreftet skala/råeksport for å stoppe fortynningsberegning.

## Når rapporten mangler Height

Eldre rapporter kan ha bare Size-tabell. Da bevares størrelsene, men RFU blir blank. PDF-visningen har kalibrert grafavlesning: velg to tydelige y-nivåer med kjente RFU-verdier og deretter toppen til den eksplisitt valgte bp-etiketten. Angi RFU-verdiene inkludert eventuell skalering; ikke gang resultatet med 1000 en gang til. X-aksen er migrasjonstid og brukes **ikke** til lineær beregning av bp.

Kalibreringen avviser feil akseretning, for tettliggende referanser og ekstrapolering. Resultatet er et estimat som krever manuell signering og kommentar. Automatisk OCR/grafgjetting er ikke implementert. Skannede PDF-er uten lesbar prøvestruktur gir filfeil.

## Kontroll og fortynning

- `KLAR`: én entydig kandidat med gyldig høyde og kjent skala, uten øvrige kontrollpunkter. Dette er en programstatus, ikke laboratoriegodkjenning.
- `KONTROLL`: ukjent analyse, flere kandidater, manglende høyde, kontrollprøve, grensenær RFU eller andre avvik.
- `KONTROLLERT`: eksplisitt manuell kontroll med kontrollør, begrunnelse, bp og konkret fortynning. Kildeverdiene beholdes.

| RFU | Forslag |
|---|---|
| <1500 | Ufortynnet |
| 1500–<2000 | 1:2 |
| 2000–<4000 | 1:5 |
| 4000–6000 | 1:10 |
| >6000 | Velg 1:15 eller 1:20 manuelt |

Innen ±10 % av en grense kreves kontroll. Kontroller som NTC/gDNA får ikke automatisk fortynning. De opprinnelig overlappende tersklene er gjort entydige ved 2000 og 4000; nøyaktig 6000 ligger i 1:10. Reglene og forventede fragmentstørrelser må vurderes av laboratoriet før rutinebruk.

## Sporbar eksport

Eksporten har valgt bp, forventet bp, kandidatantall og kandidatliste, råhøyde, RFU-faktor, kildefil, PDF-side, SHA256 av kilden, metode og eventuell manuell kontroll. Alle topper beholdes på eget ark. Full eksport inkluderer også uavklarte prøver og filfeil; avklart eksport utelater uavklarte prøver og registrerer antallet som ble utelatt.

Eksport til en eksisterende `.xlsx`-mal krever eksplisitt JSON-tilordning. Eksempelprofilen er kun syntetisk. Malen overskrives aldri. Opptatte/sammenslåtte celler, duplikater, endret kilde og uavklarte resultater stopper maleksport. Avanserte Excel-objekter som openpyxl ikke støtter må kontrolleres i kopien. Makromaler støttes ikke.
