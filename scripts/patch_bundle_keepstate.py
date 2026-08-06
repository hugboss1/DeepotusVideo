# -*- coding: utf-8 -*-
# scripts/patch_bundle_keepstate.py
"""Patcher idempotent — étape 1 : Studio garde son travail à la navigation.

Spec : docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md

Le commutateur d'écrans est un tableau de 11 slots `s==="x"&&r.jsx(...)` :
un écran inactif vaut false, donc React démonte tout son arbre. Quitter
Studio pour la Bibliothèque détruit le graphe en cours.

On ne touche à AUCUN cycle de vie (garder les écrans montés ferait tourner
5 sondages en permanence et rendrait le raccourci Alt+C du Montage global,
donc destructeur depuis n'importe quel écran). À la place, l'état de travail
est miroité dans des variables de module qui survivent au démontage, et les
initialiseurs `useState` les relisent au remontage.

Studio est le cas le plus simple : le bundle recopie DÉJÀ le graphe courant
dans `__dzG` à chaque rendu. Il suffit de le relire, et d'ajouter le même
miroir pour la sélection, le zoom et le pan.

Portée : en session seulement. Rien n'est écrit sur disque, donc un
rechargement repart d'un canvas neuf — pas de brouillon fantôme référençant
un rendu supprimé entre-temps.

Précédence conservée : les points d'entrée externes (`__dzRenderGraph`,
`__dzRender`, `__dzTpl` — « rouvrir dans Studio ») sont testés AVANT et
sortent par un `return` anticipé ; ouvrir un rendu charge donc bien son
graphe au lieu de restaurer le précédent.

Run : python scripts/patch_bundle_keepstate.py [--root <dir>] [--check]
"""
import argparse
import pathlib
import shutil
import sys

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
MARKER = "__dzKeep"

PATCHES = [
    # 1. Le magasin, déclaré à côté du global existant qui porte le graphe.
    ("magasin",
     "var __dzG=null;",
     "var __dzG=null,__dzKeep={};"),

    # 2. Graphe : __dzG contient le dernier graphe rendu et survit au démontage.
    #    ts() ne fait que fusionner les props par défaut -> idempotent.
    ("graphe",
     "return ts(structuredClone(Zi[n]))",
     "return __dzG?ts(__dzG):ts(structuredClone(Zi[n]))"),

    # 3. Nœud sélectionné.
    ("selection",
     'return vn("node")||"n6"',
     'return __dzKeep.sel||vn("node")||"n6"'),

    # 4. Zoom et pan du canvas.
    ("vue",
     "[h,b]=x.useState(.75),[_,z]=x.useState({x:0,y:0})",
     "[h,b]=x.useState(__dzKeep.zoom||.75),"
     "[_,z]=x.useState(__dzKeep.pan||{x:0,y:0})"),

    # 5. Miroir, au même endroit du corps de rendu qui archive déjà le graphe.
    #    s = sélection, h = zoom, _ = pan — tous en portée ici (vérifié).
    ("miroir",
     "__dzG=o;",
     "__dzG=o;__dzKeep.sel=s;__dzKeep.zoom=h;__dzKeep.pan=_;"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="dépôt ou app installée")
    ap.add_argument("--check", action="store_true", help="ne rien écrire")
    args = ap.parse_args()

    bundle = pathlib.Path(args.root) / REL_BUNDLE
    if not bundle.is_file():
        return f"[keepstate] bundle introuvable : {bundle}"

    s = bundle.read_text(encoding="utf-8", errors="surrogateescape")

    if MARKER in s:
        print(f"[keepstate] déjà appliqué — {bundle}")
        return 0

    # Toutes les ancres doivent être uniques AVANT d'écrire quoi que ce soit.
    for tag, old, _new in PATCHES:
        n = s.count(old)
        if n != 1:
            return (f"[keepstate] ancre « {tag} » trouvée {n} fois (attendu 1)"
                    f" — abandon, aucune écriture. Le bundle a-t-il changé ?")

    if args.check:
        print(f"[keepstate] applicable sur {bundle} ({len(PATCHES)} ancres OK)")
        return 0

    for _tag, old, new in PATCHES:
        s = s.replace(old, new, 1)

    bak = bundle.with_name(bundle.name + ".bak_keepstate")
    if not bak.exists():
        shutil.copy2(bundle, bak)
    bundle.write_text(s, encoding="utf-8", errors="surrogateescape")
    print(f"[keepstate] appliqué — {bundle} (backup : {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
