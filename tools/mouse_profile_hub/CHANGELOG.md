# Changelog

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
