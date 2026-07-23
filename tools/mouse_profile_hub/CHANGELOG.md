# Changelog

## 0.2.0

### Added

• Profile Stress Lab voor 10 tot 5000 versnelde batchruns
• Reproduceerbare simulaties met instelbare seed
• Scores voor profielovereenkomst, variatie, continuïteit, timing, herhaling, fysieke plausibiliteit en outliers
• Detectie van herhaalde pad-fingerprints en abrupte bewegingen
• JSON-hoofdrapport plus JSONL-bestand met iedere afzonderlijke run
• Eigen Windows-launcher: `Start Profile Stress Lab.bat`
• Automatische opslag onder `data/mouse_profile_hub/stress_lab/`
• CI-tests voor reproduceerbaarheid, unieke runs, scoregrenzen en rapportbestanden

### Changed

• Projectversie verhoogd naar 0.2.0 vanwege de nieuwe Stress Lab-module
• Kwaliteitsoordeel gebruikt nu meerdere gewogen categorieën in plaats van één cosmetische score

### Safety

• De simulator analyseert uitsluitend lokale demo- en profielkwaliteit
• Het rapport claimt niet dat externe detectiesystemen kunnen worden omzeild
• Er worden geen externe applicaties bestuurd tijdens batchruns

## 0.1.0

### Added

• Lokale dashboardhub voor Mouse Lab recordings
• Persistente include en exclude status per sessie
• Echte replay uit points.csv
• Profielgestuurde replayvariant en data gebaseerde similarity score
• Achtergrondopbouw van het masterprofiel
• Atomaire master en runtime exports
• Profielhistorie
• Mouse Lab procesbeheer, labeling en logging
• Windows launcher met startup checks en logbestand
• Windows CI voor Python 3.11 en 3.12

### Changed

• Het gekozen label wordt via MOUSE_LAB_LABEL aan Mouse Lab doorgegeven
• KPI's gebruiken echte recordingduur en profielversie
• Rebuild gebruikt uitsluitend ingeschakelde sessies

### Safety

• Ruwe recordings worden nooit overschreven
• Runtimeprofiel wordt pas vervangen nadat een complete nieuwe export klaarstaat
• Mouse Lab wordt bij afsluiten gecontroleerd gestopt
