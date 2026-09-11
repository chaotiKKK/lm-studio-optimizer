# LM Studio Optimizer – PWA (Android, ohne Play Store)

Installierbare Web-App: gleiche Profile wie die Desktop-App
(`tasks.json`, per `android/export_tasks.py` aus `TASKS` erzeugt).

## Dateien

- `index.html` – die App (eine Datei, kein Build, kein CDN → voll offline)
- `manifest.webmanifest` – Installierbarkeit, Icons, Farben
- `sw.js` – Service Worker (Cache `lmo-pwa-v1`; bei Release bumpen!)
- `tasks.json` – Profildaten (generiert, nicht von Hand editieren)
- `icon-192.png` / `icon-512.png` – Home-Screen-Icons (maskable-tauglich)

## Installieren (Android)

1. Ordner per HTTPS hosten – z. B. GitHub Pages, Netlify oder lokal:
   `python -m http.server 8080` im `pwa/`-Ordner, dann per Tunnel/HTTPS öffnen.
   `file://` geht **nicht** (Service Worker + Install-Dialog brauchen
   Secure Context).
2. In Chrome öffnen → ⋮ → **App installieren** / **Zum Startbildschirm**.
3. Offline-Test: Flugmodus → App startet trotzdem (Shell aus Cache).
   Online-Suche (Hugging Face) braucht Netz.

## Selbsttest

`index.html?selftest` zeigt `SELFTEST n/n` (Aufgaben, Profile, Schaetzung,
Rendering). Nach `tasks.json`-Update Seite neu laden.

## Echte APK (optional, Follow-up)

PWA per **Bubblewrap (Trusted Web Activity)** oder **Capacitor** als APK/AAB
verpacken – braucht Android SDK + Java + öffentliche HTTPS-URL.
