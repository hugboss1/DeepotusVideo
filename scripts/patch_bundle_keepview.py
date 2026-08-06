# -*- coding: utf-8 -*-
# scripts/patch_bundle_keepview.py
"""Patcher idempotent — étape 2 : l'application rouvre sur le dernier écran.

Spec : docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md

`const[s,a]=x.useState(sg||t)` repart toujours sur `studio` (prop
`initialView`). Après un redémarrage, l'utilisateur qui travaillait au
Montage ou dans le Scheduler est renvoyé au Studio.

L'écran courant est une préférence de navigation, pas du travail en cours :
le persister sur disque est ici légitime et cohérent avec les 18 clés
`dz_*` déjà présentes (rail replié, thème, favoris, modèle choisi).

Priorité conservée : le paramètre d'URL `?view=` (variable `sg`) prime
toujours, et la valeur relue est validée contre la liste `Yu` des écrans —
une clé corrompue ou un écran supprimé dans une version future retombe sur
la valeur par défaut au lieu d'afficher une page blanche.

Run : python scripts/patch_bundle_keepview.py [--root <dir>] [--check]
"""
import argparse
import pathlib
import shutil
import sys

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
MARKER = 'dz_view'

PATCHES = [
    # Lecture : ?view= prime, puis la préférence validée, puis le défaut.
    ("lecture",
     "const[s,a]=x.useState(sg||t)",
     'const[s,a]=x.useState(sg||(function(){try{var _v=localStorage.getItem'
     '("dz_view");return Yu.indexOf(_v)>=0?_v:t}catch(_e){return t}})())'),

    # Écriture : à chaque changement d'écran, quelle qu'en soit l'origine
    # (rail, palette de commandes, événement deepotus:navigate).
    ("ecriture",
     "[c,p]=x.useState([]),[h,b]=x.useState([]);",
     "[c,p]=x.useState([]),[h,b]=x.useState([]);"
     'x.useEffect(function(){try{localStorage.setItem("dz_view",s)}'
     "catch(_e){}},[s]);"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="dépôt ou app installée")
    ap.add_argument("--check", action="store_true", help="ne rien écrire")
    args = ap.parse_args()

    bundle = pathlib.Path(args.root) / REL_BUNDLE
    if not bundle.is_file():
        return f"[keepview] bundle introuvable : {bundle}"

    s = bundle.read_text(encoding="utf-8", errors="surrogateescape")

    if MARKER in s:
        print(f"[keepview] déjà appliqué — {bundle}")
        return 0

    for tag, old, _new in PATCHES:
        n = s.count(old)
        if n != 1:
            return (f"[keepview] ancre « {tag} » trouvée {n} fois (attendu 1)"
                    f" — abandon, aucune écriture.")

    if args.check:
        print(f"[keepview] applicable sur {bundle}")
        return 0

    for _tag, old, new in PATCHES:
        s = s.replace(old, new, 1)

    bak = bundle.with_name(bundle.name + ".bak_keepview")
    if not bak.exists():
        shutil.copy2(bundle, bak)
    bundle.write_text(s, encoding="utf-8", errors="surrogateescape")
    print(f"[keepview] appliqué — {bundle} (backup : {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
