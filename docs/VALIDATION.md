# Verifikasjon og begrensninger

Denne versjonen har syntetiske enhets-, integrasjons- og GUI-tester. Testene bruker genererte PDF-er og Excel-filer, ikke laboratoriedata. Kjør `python -m unittest discover -s tests -v` etter installasjon. CI kjører samme tester på Windows med Python 3.11 og 3.12.

Regresjonstester sikrer spesielt at:

- flere kandidater ikke automatisk gir høyden til den høyeste toppen;
- en valgt bp kobles til akkurat dens tabellhøyde;
- manglende høyde aldri blir null, og NaN/inf/negative verdier ikke blir avklarte RFU-er;
- manuell grafverdi beholder kilde, metode, faktisk grafside og opprinnelig tabellside;
- markørhøyder ikke blir relevante PCR-resultater;
- grafkalibrering ikke dobbeltskaleres, ekstrapoleres eller bruker feil akseretning;
- PDF-tekst ikke blir Excel-formler;
- malinnfylling ikke overskriver originaler, formler eller sammenslåtte celler;
- kandidatantall, faktor og kildehash beholdes i eksporten;
- avklart eksport utelater ventende prøver og beholder filfeil;
- kildens identitet kontrolleres før PDF-kontroll og malinnfylling;
- valg og signerte kontroller ikke mistes stille ved ny innlesing eller innstillingsendringer.

Det er også gjennomført lokal gjennomgang av reelle rapporter og visuell sammenligning av utvalgte bp/Height-par. Disse filene, pasient-/prøveopplysninger og kontrollbildene er ikke del av offentlig kildekode. Fravær av filfeil bekrefter bare innlesbar rapportstruktur, ikke at riktig klinisk topp er valgt i hver prøve.

Før rutinebruk må laboratoriet bekrefte RFU-skala, forventede størrelser, terskler, kontrollhåndtering og samsvar mot manuell avlesning. Det må også prøve Ivanti/Python FELLES, nettverksdisk, installasjonsrettigheter og den faktiske Excel-malen på arbeidsmaskinen. Ingen programtest her erstatter dette.

Verktøyet lover ikke at alle topper alltid identifiseres riktig. Det stopper automatisk resultat ved tvetydighet og bevarer rådata for menneskelig vurdering. Automatisk OCR/grafavlesning er ikke implementert; grafverktøyet bruker eksplisitt manuell kalibrering.
