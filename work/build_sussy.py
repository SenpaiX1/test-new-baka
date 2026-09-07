"""
Build sussybakabois catalog. Three kinds of entries:

  1) gamesf-mapped   : local /sussybakabois/gamesf/Y.html   (self-contained; uses CDN base href)
  2) external-iframe : the external iframe src from the wrapper page
  3) wrapper         : /sussybakabois/gameSite/X.html       (wrapper's own JS resolves final URL)

Rebuilds catalog + copies files. Idempotent.
"""
import json, re, shutil
from pathlib import Path

SRC = Path("/app/work/sussy/HTML-CSS-JS-Static-1/games")
OUT = Path("/app/frontend/public/sussybakabois")
(OUT / "gamesf").mkdir(parents=True, exist_ok=True)
(OUT / "gameSite").mkdir(parents=True, exist_ok=True)
(OUT / "icons").mkdir(parents=True, exist_ok=True)

index_html = (SRC / "index.html").read_text(encoding="utf-8", errors="ignore")
have_gamesf = {p.name for p in (SRC / "gamesf").iterdir() if p.is_file()}
have_icons = {p.name for p in (SRC / "icons").iterdir() if p.is_file()}
have_gameSite = {p.name for p in (SRC / "gameSite").iterdir() if p.is_file()}

# --- Classify every gameSite wrapper. ---
IFRAME_RE = re.compile(r'<iframe[^>]*src="([^"]+)"', re.S | re.I)
# Wrappers that dynamically build the final URL in JS (nowgg cloud gaming style)
NEEDS_WRAPPER_TOKENS = ("sus.ai1490.com/embed", "ip.nowgg.fun", "window.location.search")

# name -> {"kind": "gamesf"|"external"|"wrapper", "target": path_or_url}
wrapper_kind = {}
for name in sorted(have_gameSite):
    text = (SRC / "gameSite" / name).read_text(encoding="utf-8", errors="ignore")
    m = IFRAME_RE.search(text)
    if m:
        src = m.group(1).strip()
        m2 = re.search(r"gamesf/([^/'\"]+\.html)", src)
        if m2 and m2.group(1) in have_gamesf:
            wrapper_kind[name] = {"kind": "gamesf", "target": m2.group(1)}
            continue
        if src.startswith("http://") or src.startswith("https://"):
            wrapper_kind[name] = {"kind": "external", "target": src}
            continue
    # No iframe (or unresolved iframe): if it looks like a JS-driven wrapper, keep it
    if any(tok in text for tok in NEEDS_WRAPPER_TOKENS):
        wrapper_kind[name] = {"kind": "wrapper", "target": name}

# --- Card scanner from index.html ---
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
    r"<img[^>]*?src=\"(?P<icon>[^\"]+)\""
    r"(?P<mid2>.*?)"
    r"onclick=\"window\.location\.href='gameSite/(?P<game>[^']+)'\"",
    re.DOTALL | re.IGNORECASE,
)

# entries keyed by (kind, target) so we dedupe by final destination
catalog = {}

def add(kind, target, name, icon, wrapper=None):
    key = (kind, target)
    if key in catalog:
        return
    # Icon: only keep it if the exact basename exists in our icons/ dir.
    if icon:
        icon = Path(icon).name
        if icon not in have_icons:
            icon = None
    if not name:
        name = title_from_filename(wrapper or target)
    catalog[key] = {"name": name, "icon": icon, "kind": kind, "target": target}

for m in CARD_RE.finditer(index_html):
    wrapper = m.group("game")
    info = wrapper_kind.get(wrapper)
    if not info:
        continue  # dead link
    add(info["kind"], info["target"], clean_name(m.group("name")),
        m.group("icon"), wrapper=wrapper)

# Sweep: for any wrapper we recognised but that never got a card in index.html,
# add it with a derived name so it's still surfaced.
seen_targets = {(v["kind"], v["target"]) for v in catalog.values()}
for w, info in wrapper_kind.items():
    if (info["kind"], info["target"]) not in seen_targets:
        add(info["kind"], info["target"], title_from_filename(w), None, wrapper=w)

# Also sweep gamesf/ files that were never referenced anywhere.
gamesf_covered = {v["target"] for v in catalog.values() if v["kind"] == "gamesf"}
for gf in have_gamesf:
    if gf not in gamesf_covered:
        add("gamesf", gf, title_from_filename(gf), None)

# --- Copy assets. ---
for gf in have_gamesf:
    shutil.copy2(SRC / "gamesf" / gf, OUT / "gamesf" / gf)
for icon in have_icons:
    shutil.copy2(SRC / "icons" / icon, OUT / "icons" / icon)
# Only copy the gameSite wrappers we actually reference (kind=="wrapper")
needed_wrappers = {v["target"] for v in catalog.values() if v["kind"] == "wrapper"}
# clean out any stale files first
for p in (OUT / "gameSite").iterdir():
    if p.name not in needed_wrappers:
        p.unlink()
for w in needed_wrappers:
    shutil.copy2(SRC / "gameSite" / w, OUT / "gameSite" / w)

# --- Write catalog.json ---
def entry_url(v):
    if v["kind"] == "gamesf":
        return f"sussybakabois/gamesf/{v['target']}"
    if v["kind"] == "wrapper":
        return f"sussybakabois/gameSite/{v['target']}"
    return v["target"]  # external

games_list = []
for (kind, target), meta in catalog.items():
    games_list.append({
        "id": Path(target).stem if kind != "external" else re.sub(r"[^a-z0-9]+", "-", meta["name"].lower()).strip("-"),
        "name": meta["name"],
        "cover": f"sussybakabois/icons/{meta['icon']}" if meta["icon"] else "",
        "url": entry_url(meta),
        "source": kind,   # "gamesf" | "wrapper" | "external"
    })
games_list.sort(key=lambda g: g["name"].lower())

(OUT / "catalog.json").write_text(json.dumps(games_list, indent=2), encoding="utf-8")

by_kind = {}
for g in games_list:
    by_kind[g["source"]] = by_kind.get(g["source"], 0) + 1

print(f"Wrote {len(games_list)} games:")
for k, n in by_kind.items():
    print(f"  {k:10s} : {n}")
print("\nNon-local entries (external / wrapper):")
for g in games_list:
    if g["source"] != "gamesf":
        print(f"  [{g['source']:8s}] {g['name']}  ->  {g['url'][:80]}")
