# Bakaboiz Game Launcher — PRD

## Original Problem Statement
Take an uploaded HTML static file (originally "Nocturne" game launcher), strip out all ads/trackers/monetization scripts, and output a clean single self-contained HTML file. Add a custom game library "sussybakabois" loading 250 games from a remote Cloudflare worker. Rebrand "Nocturne" → "Bakaboiz".

## Deliverable
Single self-contained static HTML launcher.
- `/app/output/index.html` — final deliverable
- `/app/frontend/public/nocturne-cleaned.html` — live preview mirror (kept byte-identical; synced via `cp output/index.html frontend/public/nocturne-cleaned.html`)
- `/app/frontend/public/sussybakabois/catalog.json` — 250-game catalog

Preview served at `${REACT_APP_BACKEND_URL}/nocturne-cleaned.html`.

## Implemented (June 2026)
- Rebranded fully to "Bakaboiz".
- 3 libraries: sussybakabois (remote worker, 250 games), gnmath, Lumin.
- sussybakabois is the first/primary choice (header seg + settings popup) with animated shimmer gradient, star, pulsing "BEST" badge, subtitle "the best choice for students & better games".
- **Request Game** (sussybakabois only): gold header button (data-testid=request-game-btn) → modal → posts embed to Discord webhook `REQ_WEBHOOK` (…1432190089710145618…). Tested: submit success + empty validation.
- **Report a Problem** (always visible): header alert-triangle icon button (data-testid=report-problem-btn) → modal → posts embed to Discord webhook `REPORT_WEBHOOK` (…1420170958664237146…). Tested: submit success + empty validation.
- **Animated dither WebGL2 background** (exact ReactBits/aidesigner "dither" shader: fBm Perlin `cnoise` flow field + 8x8 Bayer ordered dithering, plus a glow term on wave peaks). Full-screen `<canvas id="dither">` at z-index -3. Syncs waveColor to accent, toggles with "Ambient effects" switch (applies on Save). Exposed via `window.NFDither.setAccent/setEnabled`. Params: waveSpeed 0.05, waveFrequency 3.0, waveAmplitude 0.4, colorNum 4, pixelSize 2, f-gain 1.4, glow pow(f,4)*0.5.

## Critical fix log
- **Black background covering the dither**: root cause was `body{background:var(--bg)}` (opaque) painting over the negative-z-index fixed canvas. Fixed by moving the dark background to `html` only and setting `body{background:transparent}`. Verified (testing agent iteration_1): bodyBg transparent, canvas brightness 204/255 at empty gaps.

## Known limitations / Backlog
- P1: Discord webhook URLs are hardcoded in client-side JS (publicly exposed, spammable) — inherent to a single static file. Consider client-side cooldown / rate-limit.
- P2: Ambient toggle applies only on Save; could apply instantly in the #setFx click handler.
- P2: High-score submission to Discord (from source site).
- P2: Settings controls to tune the dither (pixel size / colors / speed).
