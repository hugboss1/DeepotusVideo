# scripts/patch_bundle_numbering.py
"""Assert-guarded patcher: number same-type source nodes (#1/#2/#3) so multiple
identical sources (e.g. three "Existing render") are distinguishable.

Why: the Effects node's "Appliquer sur" dropdown already targets a source by
node id, but labelled every node by its TYPE title — so three Existing-render
sources were three identical "Existing render" entries, impossible to target
individually. The Concatenate/Composer sources panel had the same ambiguity.

Fix (frontend only): label sources "{type} #{entry}" where the number is the
CONCATENATE ENTRY ORDER (input port a=1, b=2, c=3 ...), identical in the
Concatenate sources panel and the Effects "Appliquer sur" dropdown, so
"Existing render #2" maps 1:1 across both lists. Sources not wired to a
Concatenate fall back to a per-type counter in the Effects dropdown.

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

    # NUM-1: Effects "Appliquer sur" dropdown. A source wired to a Concatenate
    # input gets that ENTRY number (port a->1, b->2, c->3 ...) — the same number
    # the Concatenate panel shows — so "Existing render #2" maps 1:1 across both
    # lists. Sources not feeding a Concatenate fall back to a per-type counter.
    anchor_1 = '(g.nodes||[]).forEach(function(nd){if(srcT[nd.type]){var lbl=(Me[nd.type]&&Me[nd.type].title)||nd.type;opts.push({value:nd.id,label:lbl})}});'
    add_1 = ('var _byId={};(g.nodes||[]).forEach(function(z){_byId[z.id]=z});'
             'var _cnt={};(g.nodes||[]).forEach(function(nd){if(srcT[nd.type]){'
             '_cnt[nd.type]=(_cnt[nd.type]||0)+1;var num=_cnt[nd.type];'
             'var ed=(g.edges||[]).find(function(E2){var tn=_byId[E2.to];'
             'return E2.from===nd.id&&tn&&tn.type==="Concatenate"&&"abcdef".indexOf(E2.toPort)>=0});'
             'if(ed)num="abcdef".indexOf(ed.toPort)+1;'
             'var lbl=((Me[nd.type]&&Me[nd.type].title)||nd.type)+" #"+num;'
             'opts.push({value:nd.id,label:lbl})}});')
    s = apply(s, anchor_1, add_1, "NUM-1-effects-targets")

    # NUM-2: Concatenate sources panel — label each filled entry
    # "{type title} #{entry}" where entry = the input port order (a=1, b=2, c=3),
    # matching NUM-1's numbering exactly. `pt` is the port letter in scope.
    anchor_2 = 'children:src?((Me[src.type]&&Me[src.type].title)||src.type):"— libre —"})'
    add_2 = 'children:src?(((Me[src.type]&&Me[src.type].title)||src.type)+" #"+("abcdef".indexOf(pt)+1)):"— libre —"})'
    s = apply(s, anchor_2, add_2, "NUM-2-concat-sources")

    BUNDLE.write_text(s, encoding="utf-8")
    print("patched OK")


if __name__ == "__main__":
    main()
