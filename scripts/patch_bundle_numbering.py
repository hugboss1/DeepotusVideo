# scripts/patch_bundle_numbering.py
"""Assert-guarded patcher: number same-type source nodes (#1/#2/#3) so multiple
identical sources (e.g. three "Existing render") are distinguishable.

Why: the Effects node's "Appliquer sur" dropdown already targets a source by
node id, but labelled every node by its TYPE title — so three Existing-render
sources were three identical "Existing render" entries, impossible to target
individually. The Concatenate/Composer sources panel had the same ambiguity.

Fix (frontend only): append a per-type index "#N" (node order in the graph) to
the source label in BOTH places, using the SAME numbering so an "Existing
render #2" in the Effects dropdown maps to the "#2" row in the Concatenate panel.

Run: python scripts/patch_bundle_numbering.py
"""
import pathlib, shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    bak = BUNDLE.with_suffix(".js.bak")
    if not bak.exists():
        shutil.copy2(BUNDLE, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")

    # NUM-1: Effects "Appliquer sur" dropdown — per-type "#N" so each source is
    # targetable individually (enables a precise effect on a chosen source).
    anchor_1 = '(g.nodes||[]).forEach(function(nd){if(srcT[nd.type]){var lbl=(Me[nd.type]&&Me[nd.type].title)||nd.type;opts.push({value:nd.id,label:lbl})}});'
    add_1 = 'var _cnt={};(g.nodes||[]).forEach(function(nd){if(srcT[nd.type]){_cnt[nd.type]=(_cnt[nd.type]||0)+1;var lbl=((Me[nd.type]&&Me[nd.type].title)||nd.type)+" #"+_cnt[nd.type];opts.push({value:nd.id,label:lbl})}});'
    s = apply(s, anchor_1, add_1, "NUM-1-effects-targets")

    # NUM-2: Concatenate/Composer sources panel — same "#N" next to the port
    # letter, so "a · Existing render #2" maps to the Effects dropdown entry.
    anchor_2 = 'children:src?((Me[src.type]&&Me[src.type].title)||src.type):"— libre —"})'
    add_2 = 'children:src?(((Me[src.type]&&Me[src.type].title)||src.type)+" #"+((g.nodes||[]).filter(function(z){return z.type===src.type}).findIndex(function(z){return z.id===src.id})+1)):"— libre —"})'
    s = apply(s, anchor_2, add_2, "NUM-2-concat-sources")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
