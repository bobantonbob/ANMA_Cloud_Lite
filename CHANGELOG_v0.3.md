# ANMA Cloud Lite v0.3 — UI only

- Power-flow diagram above KPI tiles on desktop and above graphs on mobile.
- Live flow directions via animated SVG particles, computed from demo grid and battery signed power.
- Interactive 24h charts with hover/touch pointer values.
- Today/tomorrow forecast cards — DEMO ONLY, not weather-based.
- Ukrainian/English, light/dark retained.
- Home Assistant integration and remote pairing not implemented.

## Windows upgrade
Stop Django. Back up your current folder. Copy templates/dashboard.html, static/css/app.css, static/js/dashboard.js, static/js/app.js from this archive into existing project. Keep your .env and db.sqlite3. Restart server and hard-refresh browser with Ctrl+F5.
