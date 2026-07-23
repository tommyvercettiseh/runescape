# Personal Input Profile Hub

Lokale desktop-hub rond de bestaande `tools/mouse_lab` tooling.

## Functies in v0.1.0

- Dashboard met lokale recordings en labels
- Bestaande Mouse Lab starten
- Sessies uit `tools/mouse_lab/recordings` tonen
- `master_profile.json` uitlezen
- Masterprofiel opnieuw bouwen vanuit beschikbare recordings
- Veilige visuele replayvergelijking binnen de hub
- Geen besturing van externe applicaties vanuit de replayweergave

## Starten

Dubbelklik in de repository-root op:

```text
Start Input Profile Hub.bat
```

Of start vanuit Python:

```bash
python -m tools.mouse_profile_hub.main
```

## Datastroom

```text
Mouse Lab recording
  -> tools/mouse_lab/recordings/<session>/profile_preview.json
  -> tools/mouse_lab/build_master_profile.py
  -> tools/mouse_lab/recordings/master_profile.json
  -> Personal Input Profile Hub
```

## Belangrijk

Ruwe recordings worden niet gewijzigd of verwijderd door de hub. De hub leest de huidige mappenstructuur en gebruikt de bestaande master-profile builder.
