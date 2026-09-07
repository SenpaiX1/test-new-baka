"""
Wire the 'sussybakabois' library into the cleaned Nocturne HTML.
Adds:
  - A third segment button in the header ('sussybakabois')
  - A third option in the settings sheet
  - A loadSussy() function that fetches the local sussybakabois/catalog.json
  - A dedicated open path that uses iframe.src (not srcdoc) so wrapper pages
    can iframe ../gamesf/ correctly.

Idempotent: safe to run multiple times.
"""
import re
from pathlib import Path

TARGETS = [
    Path("/app/output/index.html"),
    Path("/app/frontend/public/nocturne-cleaned.html"),
]

MARKER = "/* SUSSYBAKABOIS_LIB_INJECTED */"

SEG_OLD = (
    '<div class="seg" id="libSeg">\n'
    '        <button data-lib="gnmath">gnmath</button>\n'
    '        <button data-lib="lumin" class="on">Lumin</button>\n'
    '    </div>'
)
SEG_NEW = (
    '<div class="seg" id="libSeg">\n'
    '        <button data-lib="gnmath">gnmath</button>\n'
    '        <button data-lib="lumin" class="on">Lumin</button>\n'
    '        <button data-lib="sussy">sussybakabois</button>\n'
    '    </div>'
)

SET_OPTS_OLD = (
    '<div class="opts" id="setLib">\n'
    '                <div class="opt on" data-lib="gnmath">gnmath<br><span style="font-size:11px;color:var(--fg-3)">more known library</span></div>\n'
    '                <div class="opt" data-lib="lumin">Lumin<br><span style="font-size:11px;color:var(--fg-3)">bigger game libary</span></div>\n'
    '            </div>'
)
SET_OPTS_NEW = (
    '<div class="opts" id="setLib">\n'
    '                <div class="opt on" data-lib="gnmath">gnmath<br><span style="font-size:11px;color:var(--fg-3)">more known library</span></div>\n'
    '                <div class="opt" data-lib="lumin">Lumin<br><span style="font-size:11px;color:var(--fg-3)">bigger game libary</span></div>\n'
    '                <div class="opt" data-lib="sussy">sussybakabois<br><span style="font-size:11px;color:var(--fg-3)">local library, works offline</span></div>\n'
    '            </div>'
)

# JS patch: add loadSussy() near loadLumin(), route it in loadLibrary(),
# and short-circuit openGame() for sussy games (use iframe.src, no sandbox).
JS_PATCH_ANCHOR = 'async function loadLibrary(lib,persist){'
JS_PATCH_BLOCK = (
    'async function loadSussy(){\n'
    '    var r=await fetch("sussybakabois/catalog.json?t="+Date.now());\n'
    '    if(!r.ok) throw new Error("sussybakabois catalog not found");\n'
    '    var games=await r.json();\n'
    '    return games.map(function(g){ return {\n'
    '        id:g.id, name:g.name, cover:g.cover, url:g.url,\n'
    '        special:["sussybakabois"], _sussy:true\n'
    '    }; });\n'
    '}\n\n' + JS_PATCH_ANCHOR
)

# In loadLibrary(): dispatch to loadSussy when lib==="sussy".
LOADLIB_OLD = 'S.games = lib==="lumin" ? await loadLumin() : await loadGnmath();'
LOADLIB_NEW = 'S.games = lib==="lumin" ? await loadLumin() : (lib==="sussy" ? await loadSussy() : await loadGnmath());'

# Spinner label so users see "sussybakabois"
SPIN_OLD = "grid.innerHTML='<div class=\"status\"><div class=\"spinner\"></div>Loading the '+(lib===\"lumin\"?\"Lumin\":\"gnmath\")+' library…</div>';"
SPIN_NEW = "grid.innerHTML='<div class=\"status\"><div class=\"spinner\"></div>Loading the '+(lib===\"lumin\"?\"Lumin\":(lib===\"sussy\"?\"sussybakabois\":\"gnmath\"))+' library…</div>';"

# coverOf(): sussy covers are plain relative paths, not templates.
COVER_OLD = 'function coverOf(g){ return g._lumin ? "" : resolve(g.cover); }'
COVER_NEW = 'function coverOf(g){ return g._lumin ? "" : (g._sussy ? (g.cover||"") : resolve(g.cover)); }'

# renderFeatured() hides itself for lumin — extend that to sussy so we don't show
# a broken cover row (sussy has 43 items, we'd rather they all show in the grid).
FEAT_OLD = 'if(feats.length<4 || S.library==="lumin"){ $("featWrap").style.display="none"; return; }'
FEAT_NEW = 'if(feats.length<4 || S.library==="lumin" || S.library==="sussy"){ $("featWrap").style.display="none"; return; }'

# Chip strip: same idea — hide featured row when a category is picked in sussy.
CHIP_OLD = '$("featWrap").style.display = (S.cat==="all"&&S.library!=="lumin") ? "block":"none";'
CHIP_NEW = '$("featWrap").style.display = (S.cat==="all"&&S.library!=="lumin"&&S.library!=="sussy") ? "block":"none";'

# openGame(): add a sussy branch BEFORE the gnmath fetch branch.
OPEN_OLD = (
    "    if(g._lumin){\n"
    "        try{\n"
    "            var res=await Lumin.getGameUrl(g.id); var url=res&&res.url;\n"
    "            if(!url) throw new Error(\"no url\");\n"
    "            vFrame.removeAttribute(\"sandbox\");\n"
    "            vFrame.src=url; S.current={type:\"lumin\",url:url};\n"
    "        }catch(e){ alert(\"Load failed: \"+(e.message||e)); closeViewer(); }\n"
    "        return;\n"
    "    }\n"
)
OPEN_NEW = OPEN_OLD + (
    "    if(g._sussy){\n"
    "        try{\n"
    "            vFrame.removeAttribute(\"sandbox\");\n"
    "            vFrame.src=g.url;\n"
    "            S.current={type:\"sussy\",url:g.url};\n"
    "        }catch(e){ alert(\"Load failed: \"+(e.message||e)); closeViewer(); }\n"
    "        if(prefs().cloak){ viewerNewTab(); }\n"
    "        return;\n"
    "    }\n"
)

# viewerNewTab(): make cloak mode work for sussy too (iframe url in blank tab).
NEWTAB_OLD = 'if(S.current&&S.current.type==="lumin"){ body+=\'<iframe src="\'+S.current.url+\'" allow="autoplay;fullscreen;pointer-lock;gamepad"></iframe>\'; w.document.write(body); }'
NEWTAB_NEW = 'if(S.current&&(S.current.type==="lumin"||S.current.type==="sussy")){ body+=\'<iframe src="\'+S.current.url+\'" allow="autoplay;fullscreen;pointer-lock;gamepad"></iframe>\'; w.document.write(body); }'


def patch(text: str) -> str:
    if MARKER in text:
        return text  # already patched
    assert SEG_OLD in text, "header segment block not found"
    text = text.replace(SEG_OLD, SEG_NEW, 1)

    assert SET_OPTS_OLD in text, "settings-sheet opts block not found"
    text = text.replace(SET_OPTS_OLD, SET_OPTS_NEW, 1)

    assert JS_PATCH_ANCHOR in text, "loadLibrary anchor not found"
    text = text.replace(JS_PATCH_ANCHOR, JS_PATCH_BLOCK, 1)

    assert LOADLIB_OLD in text
    text = text.replace(LOADLIB_OLD, LOADLIB_NEW, 1)

    assert SPIN_OLD in text
    text = text.replace(SPIN_OLD, SPIN_NEW, 1)

    assert COVER_OLD in text
    text = text.replace(COVER_OLD, COVER_NEW, 1)

    assert FEAT_OLD in text
    text = text.replace(FEAT_OLD, FEAT_NEW, 1)

    assert CHIP_OLD in text
    text = text.replace(CHIP_OLD, CHIP_NEW, 1)

    assert OPEN_OLD in text, "openGame Lumin branch anchor not found"
    text = text.replace(OPEN_OLD, OPEN_NEW, 1)

    assert NEWTAB_OLD in text
    text = text.replace(NEWTAB_OLD, NEWTAB_NEW, 1)

    # Marker so re-runs are no-ops.
    text = text.replace("<script>\n(function(){", "<script>\n" + MARKER + "\n(function(){", 1)
    return text


for target in TARGETS:
    src = target.read_text(encoding="utf-8")
    out = patch(src)
    target.write_text(out, encoding="utf-8")
    print(f"Patched {target}  ({len(src)} -> {len(out)} bytes)")
