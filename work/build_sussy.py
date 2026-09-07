"""
Build the sussybakabois catalog by walking games/index.html for every card,
resolving each gameSite/X.html wrapper -> its ../gamesf/Y.html target via the
wrapper's iframe, and emitting a catalog whose URLs point DIRECTLY at gamesf/
(skipping the wrapper page entirely).

Also picks up any gamesf/*.html files that have no card in the index.
"""
import json
import re
import shutil
from pathlib import Path

SRC = Path("/app/work/sussy/HTML-CSS-JS-Static-1/games")
OUT = Path("/app/frontend/public/sussybakabois")
(OUT / "gamesf").mkdir(parents=True, exist_ok=True)
(OUT / "icons").mkdir(parents=True, exist_ok=True)

index_html = (SRC / "index.html").read_text(encoding="utf-8", errors="ignore")
have_gamesf = {p.name for p in (SRC / "gamesf").iterdir() if p.is_file()}
have_icons = {p.name for p in (SRC / "icons").iterdir() if p.is_file()}
have_gameSite = {p.name for p in (SRC / "gameSite").iterdir() if p.is_file()}

# ---- 1. Build wrapper -> gamesf mapping by grepping each wrapper's iframe src. ----
IFRAME_RE = re.compile(r'<iframe[^>]*src="([^"]+)"', re.DOTALL | re.IGNORECASE)
wrapper_to_gamesf = {}
for name in have_gameSite:
    text = (SRC / "gameSite" / name).read_text(encoding="utf-8", errors="ignore")
    m = IFRAME_RE.search(text)
    if not m:
        continue
    src = m.group(1).strip()
    # Normalise ../gamesf/foo.html and gamesf/foo.html and /games/gamesf/foo.html
    m2 = re.search(r"gamesf/([^/'\"]+\.html)", src)
    if m2 and m2.group(1) in have_gamesf:
        wrapper_to_gamesf[name] = m2.group(1)

print(f"Resolved {len(wrapper_to_gamesf)} wrapper -> gamesf mappings")

# ---- 2. Walk index.html for every unique card and pull (name, icon, wrapper_href). ----
def clean_name(raw):
    raw = re.sub(r"<span[^>]*(?:update-tag|online-tag|new-tag)[^>]*>.*?</span>",
                 "", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = raw.replace("&amp;", "&").replace("&#39;", "'").replace("&nbsp;", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.isupper():
        raw = raw.title().replace("'S", "'s")
    return raw

def title_from_filename(fn):
    stem = Path(fn).stem
    stem = re.sub(r"^(cl|gs)", "", stem)
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", stem) or [stem]
    return " ".join(w.capitalize() for w in parts) or stem

CARD_RE = re.compile(
    r"<h1[^>]*>(?P<name>.*?)</h1>"
    r"(?P<mid>.*?)"
    r"src=\"icons/(?P<icon>[^\"]+)\""
    r"(?P<mid2>.*?)"
    r"onclick=\"window\.location\.href='gameSite/(?P<game>[^']+)'\"",
    re.DOTALL | re.IGNORECASE,
)

# Also pick up cards that link directly to gamesf/ instead of gameSite/
CARD_RE_GAMESF = re.compile(
    r"<h1[^>]*>(?P<name>.*?)</h1>"
    r"(?P<mid>.*?)"
    r"src=\"icons/(?P<icon>[^\"]+)\""
    r"(?P<mid2>.*?)"
    r"onclick=\"window\.location\.href='gamesf/(?P<game>[^']+)'\"",
    re.DOTALL | re.IGNORECASE,
)

# id -> {name, icon, gamesf_file}
catalog = {}

def add(gamesf_file, name, icon):
    if gamesf_file not in have_gamesf:
        return
    if gamesf_file in catalog:
        return
    if icon and icon not in have_icons:
        icon = None
    catalog[gamesf_file] = {"name": name or title_from_filename(gamesf_file), "icon": icon}

for m in CARD_RE.finditer(index_html):
    wrapper = m.group("game")
    gamesf_file = wrapper_to_gamesf.get(wrapper)
    if not gamesf_file:
        continue
    add(gamesf_file, clean_name(m.group("name")), m.group("icon"))

for m in CARD_RE_GAMESF.finditer(index_html):
    add(m.group("game"), clean_name(m.group("name")), m.group("icon"))

# Any gamesf file that has no matching card yet — include with a derived name.
covered = set(catalog.keys())
for gf in have_gamesf:
    if gf not in covered:
        add(gf, title_from_filename(gf), None)

print(f"Total catalog entries: {len(catalog)}  (from {len(have_gamesf)} gamesf files)")

# ---- 3. Copy assets. ----
for gf in have_gamesf:
    shutil.copy2(SRC / "gamesf" / gf, OUT / "gamesf" / gf)
for icon in have_icons:
    shutil.copy2(SRC / "icons" / icon, OUT / "icons" / icon)

# Drop the old gameSite copies — we're not using wrappers anymore.
old_gs = OUT / "gameSite"
if old_gs.exists():
    shutil.rmtree(old_gs)
    print("Removed obsolete /gameSite/ directory")

# ---- 4. Write catalog.json sorted by name. ----
games_list = []
for gamesf_file, meta in sorted(catalog.items(), key=lambda kv: kv[1]["name"].lower()):
    games_list.append({
        "id": Path(gamesf_file).stem,
        "name": meta["name"],
        "cover": f"sussybakabois/icons/{meta['icon']}" if meta["icon"] else "",
        "url": f"sussybakabois/gamesf/{gamesf_file}",
    })

(OUT / "catalog.json").write_text(json.dumps(games_list, indent=2), encoding="utf-8")
print(f"Wrote {len(games_list)} games to catalog.json")
print("Sample:")
for g in games_list[:8]:
    print(f"  - {g['name']}  ->  {g['url']}  cover={g['cover'] or '(none)'}")
