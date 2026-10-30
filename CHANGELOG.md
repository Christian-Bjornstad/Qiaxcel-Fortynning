# Endringer

## 0.2.0 – 2026-10-30

- PyQt6-grensesnitt med venstremeny, statusfilter, søk, PDF-visning og kandidatdetaljer.
- Feil automatisk valg av høyeste topp er fjernet: flere kandidater krever valg av eksakt bp.
- Standardfaktor1000 for arbeidsflyten; råhøyde, faktor og RFU vises hver for seg.
- Kalibrert manuell grafavlesning for eldre rapporter uten Height, med signert kontroll.
- Manglende Height bevarer bp, men gir aldri RFU=0.
- Sporbar eksport med mål-bp, kandidater, kildehash, tabellside og avlest side.
- Full eksport eller bare avklarte resultater; filfeil bevares i begge.
- Nye tester for tvetydige topper, kalibrering, presisjon, kildeendringer og GUI-tilstander.
- Opprinnelig SVG/ICO-programikon og offentlig kildekode med kun syntetiske testdata.

## 0.1.0 – 2026-10-26

- Første lokalutgave med ScreenGel-tabellinnlesing og Excel-eksport.
- Python FELLES-installasjon og oppstart etter eksisterende in-process-mønster.
- Kopiering til en eksisterende Excel-mal via eksplisitt JSON-profil.

Versjonen er til lokal utprøving. Automatisk OCR er ikke implementert; arbeidsmiljø,
RFU-skala, laboratoriets faktiske Excel-mal og klinisk samsvar må verifiseres lokalt.
