#!/usr/bin/env python3
"""Patch the compiled frontend bundle with the Son & VFX (06) + Montage (07) screens.

Design handoff « son_vfx_montage » (refonte UI v2.1, direction Cinema).
Idempotent — safe to re-run after editing frontend/patches/son-vfx-montage.js:
the injected component block is delimited by markers and replaced in place;
the three micro-edits (nav rail, view whitelist, page dispatch) are applied
only if absent.

The dispatch anchor accepts both bundle generations: DzChapitres (app tree,
v2.0.0 French line) and DzEpisodes (repo v1.15.8 line).

Usage:
    python scripts/patch_bundle_sonvfx.py                 # patch repo dist
    python scripts/patch_bundle_sonvfx.py --root <dir>    # patch another tree
                                                          #   (e.g. %LOCALAPPDATA%/DeepotusVideoGen)
    python scripts/patch_bundle_sonvfx.py [--root d] --strip   # remove the patch

Chain compatibility (scripts/repatch_all.py): a one-time backup
<bundle>.bak_sonvfx is written before the first modification of a tree, so
this step appears in the .bak_* chain; --force-unchained is accepted and
ignored (marker-based refresh makes restore-then-reapply unnecessary).
"""
from __future__ import annotations

import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH_SRC = os.path.join(REPO, "frontend", "patches", "son-vfx-montage.js")
BEGIN = "/*__DZ_SONVFX_BEGIN__*/"
END = "/*__DZ_SONVFX_END__*/"

NAV_ANCHOR = ',{id:"scheduler",label:"Scheduler",icon:"calendar"'
NAV_INSERT = (
    ',{id:"sonvfx",label:"Son & VFX",icon:"wave",desc:"Musique, voix, SFX & VFX",new:!0}'
    ',{id:"montage",label:"Montage",icon:"layers",desc:"Timeline multipiste",new:!0}'
)
# historical variant (first EN iteration) — recognized by --strip
NAV_INSERT_OLD = (
    ',{id:"sonvfx",label:"Sound & VFX",icon:"wave",desc:"Music, voice, SFX & VFX",new:!0}'
    ',{id:"montage",label:"Edit",icon:"layers",desc:"Multitrack timeline",new:!0}'
)
WL_ANCHOR = '["quick","studio","assets3d","episodes","scheduler"'
WL_REPLACE = '["quick","studio","assets3d","episodes","sonvfx","montage","scheduler"'
DISPATCH_ANCHORS = [
    's==="episodes"&&r.jsx(DzChapitres,{variant:e}),',
    's==="episodes"&&r.jsx(DzEpisodes,{variant:e}),',
]
DISPATCH_INSERT = (
    's==="sonvfx"&&r.jsx(DzSonVfx,{variant:e,go:a}),'
    's==="montage"&&r.jsx(DzMontage,{variant:e,go:a}),'
)
COMPONENT_ANCHOR = "const oa=(()=>{try{return new URLSearchParams(window.location.search)"


def find_bundle(root: str) -> str:
    hits = glob.glob(os.path.join(root, "frontend", "dist", "assets", "index-*.js"))
    hits = [h for h in hits if ".bak" not in h and ".orig" not in h]
    if len(hits) != 1:
        sys.exit(f"expected exactly one dist bundle under {root}, found: {hits}")
    return hits[0]


def expect_once(hay: str, needle: str, what: str) -> None:
    n = hay.count(needle)
    if n != 1:
        sys.exit(f"anchor for {what} found {n}x (expected 1) — bundle layout changed, aborting")


def main() -> None:
    args = sys.argv[1:]
    root = REPO
    if "--root" in args:
        root = os.path.abspath(args[args.index("--root") + 1])
    strip = "--strip" in args

    bundle_path = find_bundle(root)
    with open(bundle_path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig" if bom else "utf-8")

    changed = []

    if strip:
        if BEGIN in text:
            head, rest = text.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            text = head.rstrip("\n") + tail.lstrip("\n")
            changed.append("components removed")
        for nav_ins in (NAV_INSERT, NAV_INSERT_OLD):
            if nav_ins in text:
                text = text.replace(nav_ins, "")
                changed.append("nav entries removed")
        if WL_REPLACE in text:
            text = text.replace(WL_REPLACE, WL_ANCHOR)
            changed.append("view whitelist restored")
        if DISPATCH_INSERT in text:
            text = text.replace(DISPATCH_INSERT, "")
            changed.append("page dispatch removed")
    else:
        with open(PATCH_SRC, "rb") as f:
            component_src = f.read().decode("utf-8-sig")

        # 1) injected components — replace existing block, else insert before the shell
        block = f"\n{BEGIN}\n{component_src}\n{END}\n"
        if BEGIN in text:
            head, rest = text.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            text = head + BEGIN + "\n" + component_src + "\n" + END + tail
            changed.append("components (refreshed)")
        else:
            expect_once(text, COMPONENT_ANCHOR, "component insertion")
            text = text.replace(COMPONENT_ANCHOR, block + COMPONENT_ANCHOR)
            changed.append("components (inserted)")

        # 2) nav rail entries
        if '{id:"sonvfx"' not in text:
            expect_once(text, NAV_ANCHOR, "nav rail")
            text = text.replace(NAV_ANCHOR, NAV_INSERT + NAV_ANCHOR)
            changed.append("nav entries")

        # 3) ?view= whitelist
        if '"sonvfx","montage","scheduler"' not in text:
            expect_once(text, WL_ANCHOR, "view whitelist")
            text = text.replace(WL_ANCHOR, WL_REPLACE)
            changed.append("view whitelist")

        # 4) page dispatch
        if 's==="sonvfx"' not in text:
            anchor = next((a for a in DISPATCH_ANCHORS if a in text), None)
            if not anchor:
                sys.exit("no dispatch anchor (DzChapitres/DzEpisodes) found — aborting")
            expect_once(text, anchor, "page dispatch")
            text = text.replace(anchor, anchor + DISPATCH_INSERT)
            changed.append("page dispatch")

    if not changed:
        print(f"{os.path.basename(bundle_path)}: nothing to do")
        return

    bak = bundle_path + ".bak_sonvfx"
    if not os.path.exists(bak):
        with open(bak, "wb") as f:
            f.write(raw)
        changed.append(f"backup -> {os.path.basename(bak)}")

    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    with open(bundle_path, "wb") as f:
        f.write(out)
    print(f"patched {bundle_path}: {', '.join(changed)}")


if __name__ == "__main__":
    main()
