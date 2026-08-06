# -*- coding: utf-8 -*-
"""Tombstone guard for retired bundle patchers.

Context (audit 2026-08-06). The UI is a minified bundle patched in place,
step by step, each patcher backing up the bundle before its own edit. Three
of the earliest patchers (concat, numbering, presets) share ONE untagged
backup, `index-BEOJX8L5.js.bak`, and treat it as "the pristine bundle":

    if not bak.exists(): copy(BUNDLE -> bak)   # "pristine"
    else:                copy(bak -> BUNDLE)   # "restore clean base"

Both branches are now traps. Their anchors were consumed years of patches
ago, so they can never usefully re-apply — but before failing they either
(a) write a fresh `.js.bak` from the CURRENT fully-patched bundle, planting a
file that a later run will happily restore as if it were pristine, or (b) if
such a stale backup ever resurfaces (an old export, a migration kit, a manual
copy), restore it over the live bundle and silently roll the UI back to
v1.15.1 — every feature since then gone, with no error.

Retired patchers are kept for provenance, not for running. This guard makes
that explicit: they refuse to run unless someone deliberately passes
--i-know-this-is-retired.
"""
import sys

FLAG = "--i-know-this-is-retired"


def assert_not_retired(name: str, reason: str) -> None:
    """Abort unless the operator explicitly opted in on the command line."""
    if FLAG in sys.argv:
        print(f"[{name}] RETIRED patcher forced with {FLAG} — you are on your own.")
        return
    sys.exit(
        f"[{name}] RETIRED — refusing to run.\n"
        f"  {reason}\n"
        f"  The UI's source of record is the committed frontend/dist bundle;\n"
        f"  recover it with `git checkout -- frontend/dist` instead.\n"
        f"  Override (not recommended): {FLAG}"
    )
