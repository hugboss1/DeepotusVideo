#!/usr/bin/env python3
"""Patch the compiled frontend bundle with the SFX Studio layer (gauntlet SFX).

Injects frontend/patches/sfxstudio.js (window.DzSfx: tiroir Sons, rack
d'effets audio, metering, generation SFX) right after the sonvfx component
block, and links frontend/dist/shared/sfxstudio.css in dist/index.html.

Idempotent — the injected block is delimited by markers and replaced in
place on re-run. Depends on patch_bundle_sonvfx.py having run first (its
END marker is the insertion anchor).

Usage:
    python scripts/patch_bundle_sfxstudio.py                 # patch repo dist
    python scripts/patch_bundle_sfxstudio.py --root <dir>    # patch another tree
    python scripts/patch_bundle_sfxstudio.py [--root d] --strip

Chain compatibility (scripts/repatch_all.py): one-time backup
<bundle>.bak_sfxstudio; --force-unchained accepted and ignored.
"""
from __future__ import annotations

import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH_SRC = os.path.join(REPO, "frontend", "patches", "sfxstudio.js")
BEGIN = "/*__DZ_SFXSTUDIO_BEGIN__*/"
END = "/*__DZ_SFXSTUDIO_END__*/"
ANCHOR = "/*__DZ_SONVFX_END__*/"

CSS_ANCHOR = '<link rel="stylesheet" href="/shared/son-vfx-montage.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/sfxstudio.css">'


def find_bundle(root: str) -> str:
    hits = glob.glob(os.path.join(root, "frontend", "dist", "assets", "index-*.js"))
    hits = [h for h in hits if ".bak" not in h and ".orig" not in h]
    if len(hits) != 1:
        sys.exit(f"expected exactly one dist bundle under {root}, found: {hits}")
    return hits[0]


def expect_once(hay: str, needle: str, what: str) -> None:
    n = hay.count(needle)
    if n != 1:
        sys.exit(f"anchor for {what} found {n}x (expected 1) — aborting")


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

    html_path = os.path.join(root, "frontend", "dist", "index.html")
    with open(html_path, "rb") as f:
        hraw = f.read()
    hbom = hraw.startswith(b"\xef\xbb\xbf")
    html = hraw.decode("utf-8-sig" if hbom else "utf-8")

    changed = []
    html_changed = []

    if strip:
        if BEGIN in text:
            head, rest = text.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            text = head.rstrip("\n") + tail.lstrip("\n")
            changed.append("components removed")
        if CSS_INSERT.strip() in html:
            html = html.replace(CSS_INSERT, "").replace(CSS_INSERT.strip(), "")
            html_changed.append("css link removed")
    else:
        with open(PATCH_SRC, "rb") as f:
            component_src = f.read().decode("utf-8-sig")

        block = "\n" + BEGIN + "\n" + component_src + "\n" + END
        if BEGIN in text:
            head, rest = text.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            text = head + BEGIN + "\n" + component_src + "\n" + END + tail
            changed.append("components (refreshed)")
        else:
            expect_once(text, ANCHOR, "sfxstudio insertion (sonvfx END marker)")
            text = text.replace(ANCHOR, ANCHOR + block)
            changed.append("components (inserted)")

        if 'shared/sfxstudio.css' not in html:
            expect_once(html, CSS_ANCHOR, "css link")
            html = html.replace(CSS_ANCHOR, CSS_ANCHOR + CSS_INSERT)
            html_changed.append("css link")

    if not changed and not html_changed:
        print(f"{os.path.basename(bundle_path)}: nothing to do")
        return

    if changed:
        bak = bundle_path + ".bak_sfxstudio"
        if not os.path.exists(bak):
            with open(bak, "wb") as f:
                f.write(raw)
            changed.append(f"backup -> {os.path.basename(bak)}")
        out = text.encode("utf-8")
        if bom:
            out = b"\xef\xbb\xbf" + out
        with open(bundle_path, "wb") as f:
            f.write(out)
    if html_changed:
        hout = html.encode("utf-8")
        if hbom:
            hout = b"\xef\xbb\xbf" + hout
        with open(html_path, "wb") as f:
            f.write(hout)
    print(f"patched {bundle_path}: {', '.join(changed)} | index.html: {', '.join(html_changed) or 'unchanged'}")


if __name__ == "__main__":
    main()
