# Personal Input Profile Hub

Lokale desktop-hub rond de bestaande `tools/mouse_lab` tooling.

## Functies in v0.2.0

- Dashboard met lokale recordings, labels en profielstatus
- Bestaande Mouse Lab starten en stoppen
- Sessies includen of uitsluiten van het masterprofiel
- Echte replay uit `points.csv`
- Masterprofiel en compact runtimeprofiel opbouwen
- Profielhistorie en atomaire exports
- Profile Stress Lab met 10 tot 5000 versnelde batchruns
- Repetition-, continuïteit-, timing-, outlier- en profielconsistentieanalyse
- JSON-rapport en JSONL-runbestand per stresstest
- Geen besturing van externe applicaties vanuit replay of Stress Lab

## Hub starten

Dubbelklik in de repository-root op:

```text
Start Input Profile Hub.bat
```

Of:

```bash
python -m tools.mouse_profile_hub.main
```

## Profile Stress Lab starten

Bouw eerst minimaal één masterprofiel vanuit geldige, ingeschakelde recordings. Start daarna:

```text
Start Profile Stress Lab.bat
```

Of:

```bash
python -m tools.mouse_profile_hub.stress_lab
```

Kies standaard 100 runs. De seed maakt een test reproduceerbaar. Resultaten worden opgeslagen in:

```text
data/mouse_profile_hub/stress_lab/<timestamp>/report.json
data/mouse_profile_hub/stress_lab/<timestamp>/runs.jsonl
```

Het rapport geeft scores voor:

- Profile similarity
- Natural variation
- Movement continuity
- Timing diversity
- Repetition control
- Physical plausibility
- Outlier control

Deze scores beoordelen de kwaliteit van de lokale demo en het profiel. Ze zijn geen garantie over externe detectie- of beveiligingssystemen.

## Datastroom

```text
Mouse Lab recording
  -> tools/mouse_lab/recordings/<session>/profile_preview.json
  -> tools/mouse_lab/recordings/<session>/points.csv
  -> master profile + runtime export
  -> Profile Stress Lab batch simulation
  -> data/mouse_profile_hub/stress_lab/<timestamp>/
```

## Belangrijk

Ruwe recordings worden niet gewijzigd of verwijderd. De hub en Stress Lab lezen lokale data en schrijven uitsluitend aparte profiel-, status-, historie- en rapportbestanden.
