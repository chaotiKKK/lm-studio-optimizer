# LM Studio Optimizer – Android-APK (Flet)

Echte native App in Python (Flet/Flutter). Gleiche Profile wie Desktop
(`tasks.json` liegt daneben und wird mit verpackt).

## Voraussetzungen

- Python ≥ 3.12, `pip install flet`
- Für den Build: `flet build` lädt beim ersten Mal automatisch nach, was
  fehlt (Flutter, JDK 17, Android SDK).

## Starten / Bauen

```bash
cd android/flet
flet run .                 # Desktop-Vorschau
flet build apk             # build/apk/app-release.apk (Sideload)
flet build apk --split-per-abi   # kleinere APKs pro Architektur
flet build aab             # Play-Store-Bundle
```

Signieren für Release: `flet build apk --android-signing-key-store ...`
(siehe `flet build apk --help`).

## CI (GitHub Actions)

Der Workflow `Android APK + AAB` baut bei jedem Push unter `android/**`
automatisch APK (Sideload) und AAB (Play Store) und legt beide unter
Actions → Artifacts ab (`lm-optimizer-apk`, `lm-optimizer-aab`).
Vor dem Play-Upload das AAB mit dem eigenen Upload-Key signieren
(Play App Signing in der Play Console einrichten).

## Einschraenkungen mobil

- `psutil`/`GPUtil` gibt es auf Android nicht → Live-Systemwerte zeigen
  dort `n/a`, alle Presets funktionieren.
- HTTP läuft über `urllib` (stdlib), damit keine nativen Wheels nötig sind.
- Falls die HF-Suche auf dem Gerät scheitert: INTERNET-Permission im
  generierten Android-Manifest prüfen.
