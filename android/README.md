# Android-Versionen – Übersicht

| Weg | Was | Programme | Store nötig | Python bleibt | Live-System (psutil) |
|---|---|---|---|---|---|
| `pwa/` ✅ gebaut | Web-App, installierbar, offline | Nur Chrome + HTTPS-Host | Nein | Nein (JS-Umschreibung) | Nein (entfällt) |
| `flet/` ✅ gebaut | Echte APK/AAB | `pip install flet` (Flutter/SDK auto) | Nur für Play (AAB) | Ja | Nein (n/a, guarded) |
| BeeWare (Alternative) | Nativ via Toga | `pip install briefcase`, Android SDK | Für Play ja | Ja | Nein |
| Kivy/Chaquopy | Nur der Vollständigkeit halber | WSL + NDK bzw. Android Studio + Kotlin | Ja | Ja | Nein |

**Wichtig:** tkinter läuft auf Android grundsätzlich nicht – jede Route
braucht die UI neu. `tasks.json` (`export_tasks.py`) hält alle Varianten
synchron mit der Desktop-App.

**Empfehlung:** PWA für sofortiges Installieren ohne Store; Flet-APK, wenn
eine echte App-Datei (Sideload/Play) gewünscht ist.
