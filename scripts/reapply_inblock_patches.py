# -*- coding: utf-8 -*-
# scripts/reapply_inblock_patches.py
"""Réapplique les correctifs AVAL qui vivent DANS le bloc sonvfx.

Le piège que ce script existe pour désamorcer
--------------------------------------------
`patch_bundle_sonvfx.py` rafraîchit son bloc EN PLACE : il remplace tout ce
qui est entre /*__DZ_SONVFX_BEGIN__*/ et /*__DZ_SONVFX_END__*/ par le contenu
courant de frontend/patches/son-vfx-montage.js. Les blocs sfxstudio, vfxrack
et subs sont ailleurs dans le bundle et survivent — mais vfxrack et subs ne se
contentent pas d'injecter un bloc : ils MODIFIENT aussi le bloc sonvfx par une
série de couples (ancre -> remplacement). Ces modifications-là sont écrasées à
chaque rafraîchissement, silencieusement : le bundle reste syntaxiquement
valide, les marqueurs sont tous là, et pourtant la piste de sous-titres et le
rack VFX ont disparu de l'éditeur.

`repatch_all.py --from sonvfx` ne répare pas ce cas : il donne à chaque patcher
aval un .bak égal au bundle courant, or ce bundle contient DÉJÀ le résultat des
couples hors-bloc (V10/V11 de vfxrack visent le nœud Studio, pas le bloc). Le
patcher ne retrouve donc plus leurs ancres et abandonne, en laissant les
couples in-bloc non réappliqués.

Ce que fait ce script
---------------------
Il rafraîchit le bloc sonvfx (il appelle patch_bundle_sonvfx.py lui-même),
puis réapplique dans CE BLOC, et dans l'ordre déclaré, les couples de vfxrack
et de subs.

Deux règles de sûreté, apprises à la dure :

1. On ne cherche l'ancre QUE dans le bloc sonvfx. Certains couples visent le
   nœud Studio, hors du bloc : ils survivent au rafraîchissement, et les
   rejouer les dupliquerait. « Ancre absente du bloc » = couple hors-bloc, on
   passe.

2. On ne tente PAS de deviner si un couple est « déjà appliqué » en cherchant
   son remplacement. C'est indécidable ici : beaucoup de remplacements
   CONTIENNENT leur propre ancre (R = A + ajout), donc l'ancre reste trouvable
   après coup et le couple se réappliquerait en boucle ; et un couple aval peut
   réécrire la zone qu'un couple amont vient d'insérer, faisant disparaître le
   remplacement du premier. La seule base fiable est un bloc PROPRE — d'où le
   rafraîchissement systématique avant de rejouer.

C'est ce qui rend l'ensemble idempotent : refresh (remet le bloc à la source)
puis rejeu (réapplique tout une fois). Aucun .bak n'est touché, la chaîne
existante reste intacte.

Emploi après une édition de frontend/patches/son-vfx-montage.js :
    python scripts/reapply_inblock_patches.py

ATTENTION aux fins de ligne : les blocs injectés du bundle sont en CRLF (git
normalise à l'extraction). Un éditeur qui réécrit son-vfx-montage.js en LF fait
échouer toutes les ancres multi-lignes des patchers aval, sans autre symptôme
qu'un compte d'ancre à 0. `--check` le signale explicitement : il compte les couples
trouvables, compare les fins de ligne des deux cotes et n'ecrit RIEN.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
MODULES = ("patch_bundle_vfxrack", "patch_bundle_subs")
BEGIN = "/*__DZ_SONVFX_BEGIN__*/"
END = "/*__DZ_SONVFX_END__*/"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # le main() est sous __main__, pas exécuté
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO),
                    help="racine du dépôt ou de l'app installée")
    ap.add_argument("--no-refresh", action="store_true",
                    help="ne pas appeler patch_bundle_sonvfx.py d'abord "
                         "(le bloc DOIT déjà être propre)")
    ap.add_argument("--check", action="store_true",
                    help="CONTROLE A SEC : n'ecrit RIEN, ne rafraichit RIEN. "
                         "Compte les couples in-bloc trouvables et compare les "
                         "fins de ligne des deux cotes.")
    args = ap.parse_args()

    bundle = pathlib.Path(args.root) / REL_BUNDLE
    if not bundle.is_file():
        print(f"[reapply] bundle introuvable : {bundle}")
        return 1

    if not args.no_refresh and not args.check:
        rc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "patch_bundle_sonvfx.py"),
             "--root", args.root]).returncode
        if rc != 0:
            print(f"[reapply] patch_bundle_sonvfx.py a échoué (rc={rc}).")
            return rc

    raw = bundle.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    s = raw.decode("utf-8-sig" if bom else "utf-8")
    crlf = "\r\n" in s
    if BEGIN not in s or END not in s:
        print("[reapply] bloc sonvfx absent du bundle — lancer d'abord "
              "patch_bundle_sonvfx.py.")
        return 1

    applied, outside, broken = [], [], []
    for name in MODULES:
        mod = _load(name)
        for tag, anchor, repl in mod.PATCHES:
            a, r = mod.nl(anchor, crlf), mod.nl(repl, crlf)
            # bornes recalculées à CHAQUE couple : une application précédente a
            # déplacé la fin du bloc
            lo = s.index(BEGIN)
            hi = s.index(END)
            n_in = s.count(a, lo, hi)
            if n_in == 1:
                if not args.check:
                    i = s.index(a, lo, hi)
                    s = s[:i] + r + s[i + len(a):]
                applied.append(f"{mod.TAG}:{tag}")
            elif n_in == 0:
                # hors du bloc (nœud Studio) : survit au rafraîchissement,
                # le rejouer le dupliquerait
                outside.append(f"{mod.TAG}:{tag}")
            else:
                broken.append(f"{mod.TAG}:{tag} (ancre×{n_in} dans le bloc)")

    print(f"[reapply] réappliqués dans le bloc : {len(applied)}")
    print(f"[reapply] hors bloc, intacts : {len(outside)}"
          + (f" — {', '.join(outside)}" if outside else ""))
    if broken:
        print(f"[reapply] ÉCHECS ({len(broken)}) :")
        for b in broken:
            print(f"    {b}")
        return 1
    if not applied:
        print("[reapply] aucun couple in-bloc trouvé — fins de ligne ?\n"
              "  Les blocs injectés du bundle sont en CRLF. Si "
              "son-vfx-montage.js a été réécrit en LF, toutes les ancres\n"
              "  multi-lignes échouent sans autre symptôme. Reconvertir la "
              "source en CRLF et relancer.")
        return 1
    if args.check:
        # LE piège, mesuré et nommé : le bloc du bundle est en CRLF ; une
        # source réécrite en LF fait échouer TOUTES les ancres multi-lignes
        # sans autre symptôme qu'un compte à 0.
        src = REPO / "frontend" / "patches" / "son-vfx-montage.js"
        if src.is_file():
            raw_src = src.read_bytes()
            n_crlf = raw_src.count(b"\r\n")
            n_lf = raw_src.count(b"\n") - n_crlf
            print(f"[reapply] bloc du bundle : {'CRLF' if crlf else 'LF'} ; "
                  f"{src.name} : CRLF={n_crlf} LF-isole={n_lf}")
            if crlf and n_lf and not n_crlf:
                print("[reapply] FINS DE LIGNE INCOMPATIBLES : la source est "
                      "en LF pur, le bloc du bundle en CRLF. Toutes les ancres "
                      "multi-lignes echoueront. Reconvertir en CRLF.")
                return 1
        print("[reapply] --check : rien n'a ete ecrit.")
        return 0
    out = s.encode("utf-8")
    bundle.write_bytes(b"\xef\xbb\xbf" + out if bom else out)
    print(f"[reapply] bundle réécrit ({bundle.stat().st_size} o)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
