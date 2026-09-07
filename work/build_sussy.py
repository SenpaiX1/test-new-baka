"""
Extract sussybakabois catalog from games/index.html and copy game HTMLs + icons
into /app/frontend/public/sussybakabois/. Emit a JSON catalog for the launcher.
"""
import json
import re
import shutil
from pathlib import Path

SRC = Path("/app/work/sussy/HTML-CSS-JS-Static-1/games")
OUT_DIR = Path("/app/frontend/public/sussybakabois")
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "gameSite").mkdir(exist_ok=True)
(OUT_DIR / "icons").mkdir(exist_ok=True)

index_html = (SRC / "index.html").read_text(encoding="utf-8", errors="ignore")

# Match cards: <h1>[optional inline tag span]NAME</h1> ... <img ... src="icons/FILE" ... > ... <button ... onclick="window.location.href='gameSite/GAME.html'">
# We do this in two passes: (1) map gameSite href -> best-guess name & icon by walking backwards.

# First, gather all card triples by regex over the raw source.
card_re = re.compile(
    r"<h1[^>]*>(?P<name>.*?)</h1>"          # name (may contain span tag)
    r"(?P<mid>.*?)"                          # anything between
    r"src=\"icons/(?P<icon>[^\"]+)\""      # icon filename
    r"(?P<mid2>.*?)"
    r"onclick=\"window\.location\.href='gameSite/(?P<game>[^']+)'\"",
    re.DOTALL | re.IGNORECASE,
)

def clean_name(raw):
    # Remove inline tag spans like <span class="update-tag">NEW</span> / <span class="online-tag">ONLINE</span>
    raw = re.sub(r"<span[^>]*(?:update-tag|online-tag|new-tag)[^>]*>.*?</span>", "", raw, flags=re.I | re.S)
    # Strip any remaining tags
    raw = re.sub(r"<[^>]+>", "", raw)
    # Collapse whitespace, decode a couple of common entities
    raw = raw.replace("&amp;", "&").replace("&#39;", "'").replace("&nbsp;", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    # Title-case if the source screamed
    if raw.isupper():
        raw = raw.title().replace("'S", "'s")
    return raw

def title_from_filename(fn):
    stem = Path(fn).stem
    # Strip common noise prefixes and split camelCase / snake
    stem = re.sub(r"^(cl|gs)", "", stem)
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", stem) or [stem]
    return " ".join(w.capitalize() for w in parts)

# Available files on disk (source of truth)
have_games = {p.name for p in (SRC / "gameSite").iterdir() if p.is_file()}
have_icons = {p.name for p in (SRC / "icons").iterdir() if p.is_file()}

# Build a dict game_filename -> (name, icon), keeping the first occurrence (usually the "New Games" section)
catalog = {}
for m in card_re.finditer(index_html):
    game_file = m.group("game")
    if game_file not in have_games:
        continue
    if game_file in catalog:
        continue
    name = clean_name(m.group("name"))
    icon = m.group("icon")
    if not name:
        name = title_from_filename(game_file)
    if icon not in have_icons:
        icon = None
    catalog[game_file] = {"name": name, "icon": icon}

# Also add any game files that had no card in the index (fall back to title-cased filename)
for gf in have_games:
    if gf not in catalog:
        catalog[gf] = {"name": title_from_filename(gf), "icon": None}

# Copy all game HTMLs + icons across.
for gf in have_games:
    shutil.copy2(SRC / "gameSite" / gf, OUT_DIR / "gameSite" / gf)
for icon in have_icons:
    shutil.copy2(SRC / "icons" / icon, OUT_DIR / "icons" / icon)

# Build a stable JSON list, sorted by name.
games_list = []
for game_file, meta in sorted(catalog.items(), key=lambda kv: kv[1]["name"].lower()):
    games_list.append({
        "id": Path(game_file).stem,
        "name": meta["name"],
        "cover": f"sussybakabois/icons/{meta['icon']}" if meta["icon"] else "",
        "url": f"sussybakabois/gameSite/{game_file}",
    })

(OUT_DIR / "catalog.json").write_text(json.dumps(games_list, indent=2), encoding="utf-8")
print(f"Wrote {len(games_list)} games to catalog.json")
print(f"Copied {len(have_games)} game HTMLs + {len(have_icons)} icons")
print("\nSample entries:")
for g in games_list[:6]:
    print(f"  - {g['name']}  ->  {g['url']}  (cover: {g['cover'] or '(none)'})")
