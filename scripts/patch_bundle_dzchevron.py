# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzchevron.py
"""Assert-guarded patcher : le chevron UNIQUE du design 26/08 dans le bundle.

BASELINE : bundle POST-patch dzdesign (dernier patch en date).
Backup dédié : .js.bak_dzchevron (état juste avant CE patch).

Réf : DESIGN.md §15-4.1 — « une seule icône dans toute la codebase ; toutes
les orientations par rotation ». Le bundle portait deux triangles pleins
(`caret` bas, `caretR` droite) ; ils deviennent le chevron du design :

  caret   -> le glyphe de base (pointe GAUCHE) — le bouton « Collapse » du
             rail de navigation pointe désormais dans la direction du
             mouvement de fermeture (edge: left), comme partout ailleurs.
  caretR  -> le même tracé tourné de 180° (pointe droite) — il sert à la
             fois d'affordance de repli (les en-têtes qui le tournent de
             90° à l'ouverture) et de flèche « suivant » des boutons.

Aucun autre octet ne bouge : les tailles, les emplois et les rotations des
appelants restent les leurs.

Run : python scripts/patch_bundle_dzchevron.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzchevron")

CHEV = "M14.8 5.6 9 12l5.8 6.4z"

OLD_CARET = 'caret:r.jsx("path",{fill:"currentColor",d:"M7 10l5 5 5-5H7z"})'
NEW_CARET = 'caret:r.jsx("path",{fill:"currentColor",d:"' + CHEV + '"})'
OLD_CARETR = 'caretR:r.jsx("path",{fill:"currentColor",d:"M10 7l5 5-5 5V7z"})'
NEW_CARETR = ('caretR:r.jsx("path",{fill:"currentColor",d:"' + CHEV
              + '",transform:"rotate(180 12 12)"})')


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    s = BUNDLE.read_text(encoding="utf-8")
    if CHEV in s:
        raise SystemExit("Bundle déjà patché (tracé du chevron présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)
    s = apply(s, OLD_CARET, NEW_CARET, "S1-caret")
    s = apply(s, OLD_CARETR, NEW_CARETR, "S2-caretR")
    BUNDLE.write_text(s, encoding="utf-8", newline="")
    print("bundle écrit :", len(s), "o — caret/caretR unifiés au chevron")


if __name__ == "__main__":
    main()
