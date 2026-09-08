# Bakaboiz Game Launcher — PRD

## Original Problem Statement
Take an uploaded HTML static file (originally "Nocturne" game launcher), strip out all ads/trackers/monetization scripts, and output a clean single self-contained HTML file. Add a custom game library "sussybakabois" loading 250 games from a remote Cloudflare worker. Rebrand "Nocturne" → "Bakaboiz".

## Deliverable
Single self-contained static HTML launcher.
- `/app/output/index.html` — final deliverable
- `/app/frontend/public/nocturne-cleaned.html` — live preview mirror (kept identical; synced via `cp output/index.html`)
- `/app/frontend/public/sussybakabois/catalog.json` — 250-game catalog

Preview served at `${REACT_APP_BACKEND_URL}/nocturne-cleaned.html`.

## Implemented (latest session — June 2026)
- Rebranded fully to "Bakaboiz".
- 3 libraries: sussybakabois (remote worker, 250 games), gnmath, Lumin.
- **sussybakabois made the first/primary choice** in header segmented control and settings popup, with animated shimmer gradient, star, pulsing "BEST" badge, and subtitle "the best choice for students & better games".
- **Request Game feature** (sussybakabois only): gold "Request Game" button in header (shows only when sussy active) → modal → posts embed to Discord webhook `https://discord.com/api/webhooks/1432190089710145618/...`. Verified end-to-end (returns success). Escape/backdrop close supported.
- **Animated dither WebGL2 background**: exact ReactBits/aidesigner "dither" shader (fBm Perlin `cnoise` flow field + 8x8 Bayer ordered dithering). Full-screen `<canvas id="dither">` at z-index -3. Syncs `waveColor` to the app accent color and toggles with the "Ambient effects" switch. Params: waveSpeed 0.05, waveFrequency 3.0, waveAmplitude 0.4, colorNum 4, pixelSize 2, f-gain 1.35. Exposed via `window.NFDither.setAccent/setEnabled`. Verified rendering (full purple dither range) and animating.

## Architecture Notes
- Pure static HTML/CSS/JS single file. No backend logic for the launcher.
- Edits done via search_replace on `/app/output/index.html`, then `cp` to the preview mirror (the two files are byte-identical).
- Game viewer supports gnmath (srcdoc html), lumin (iframe url), sussy (iframe url from catalog).

## Backlog / Future
- P2: "Report a problem" button + Discord webhook (bug reports), like the source site.
- P2: Cooldown/anti-spam on Request Game submissions.
- P2: High-score submission to Discord.
- P2: Optional settings controls to tune dither (pixel size / colors).
