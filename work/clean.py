"""
Static HTML ad cleanup for the 'Nocturne' launcher HTML pulled from the mathlearning zip.
Deterministic string-level edits (no BS-parser reflow) so the layout stays byte-identical
outside the removed regions.
"""
import re
from pathlib import Path

SRC = Path("/app/work/a.html")
OUT = Path("/app/work/index.html")

html = SRC.read_text(encoding="utf-8")

changelog = []

def cut(pattern, label, flags=re.DOTALL):
    global html
    new, n = re.subn(pattern, "", html, flags=flags)
    if n:
        changelog.append(f"- Removed {label} ({n} occurrence{'s' if n != 1 else ''})")
        html = new
    else:
        changelog.append(f"- (not found, skipped) {label}")

# 1. gtag / Google Analytics inline block (the HTML comment + script)
cut(
    r"<!-- gtag - for anayltics-->\s*<script>.*?</script>\s*",
    "Google Analytics (gtag) inline script"
)

# 2. Effective CPM network ad script (direct include)
cut(
    r'<script src="https://pl29479422\.effectivecpmnetwork\.com/[^"]+"></script>\s*',
    "effectivecpmnetwork.com ad <script>"
)

# 4. Self-reinjecting setInterval that re-adds the CPM ad every 15 min
cut(
    r"<script>\s*\(function \(\) \{\s*var SRC = \"https://pl29479422\.effectivecpmnetwork\.com/.*?\}, 15 \* 60 \* 1000\);\s*\}\)\(\);\s*</script>\s*",
    "CPM ad self-reinjection setInterval script"
)

# 5. Google Fonts external stylesheet + preconnects (offline requirement).
# The CSS already declares a full system-ui / -apple-system / Segoe UI / Roboto / sans-serif fallback.
cut(
    r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*',
    "Google Fonts preconnect (fonts.googleapis.com)"
)
cut(
    r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*',
    "Google Fonts preconnect (fonts.gstatic.com)"
)
cut(
    r'<link href="https://fonts\.googleapis\.com/css2\?family=Inter[^"]+" rel="stylesheet">\s*',
    "Google Fonts Inter stylesheet <link>"
)

# 6. Lumin library option kept — it's the game catalog provider, not an ad.
# (Earlier revision stripped it; restored per user feedback.)

# 9. Prepend the changelog comment block at the top of the file.
header = (
    "<!--\n"
    "  Cleaned by static HTML ad cleanup on 2026-02.\n"
    "  Source: Nocturne launcher HTML (from mathlearning zip -> \n"
    "  cdn.jsdelivr.net/gh/devmidnightst/nocturnesinglefile@main/index.html).\n"
    "\n"
    "  Removed:\n"
    + "\n".join("  " + line for line in changelog) +
    "\n"
    "\n"
    "  Notes / caveats:\n"
    "  - No local assets from the zip were referenced by this HTML, so nothing\n"
    "    needed to be inlined. All icons are inline SVG; the favicon is already\n"
    "    a data URI.\n"
    "  - The launcher still needs internet to work: it fetches its game catalog\n"
    "    from cdn.jsdelivr.net (gh/freebuisness/assets or gh/gn-math/assets) and\n"
    "    each individual game's HTML from the same CDN. That is the app's design,\n"
    "    not part of the ad/tracker layer.\n"
    "  - The 'Inter' web font was dropped along with the Google Fonts external\n"
    "    request; the CSS already declares a full ui-sans-serif/system-ui/-apple-\n"
    "    system/Segoe UI/Roboto/sans-serif fallback, so type still renders cleanly.\n"
    "  - The Lumin game library is kept intact — functionally it's the game\n"
    "    library provider (getGames, getGameUrl, getImageUrl), not an ad.\n"
    "    It routes through a.luminsdk.com to fetch its own game catalog.\n"
    "-->\n"
)

# Insert the comment right after the <!DOCTYPE html> line.
html = re.sub(r"(<!DOCTYPE html>\s*)", r"\1" + header, html, count=1)

OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT}  ({OUT.stat().st_size} bytes)")
print("\nChangelog:")
for line in changelog:
    print("  " + line)
