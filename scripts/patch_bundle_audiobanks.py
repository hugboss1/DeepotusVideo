# -*- coding: utf-8 -*-
# scripts/patch_bundle_audiobanks.py
"""Patcher idempotent : liste des banques audio libres de l'onglet Audio.

Constat de l'audit (06/08/2026) : le lien « YouTube Audio Library » pointait
sur https://studio.youtube.com/ — la racine de YouTube Studio, qui redirige
vers la page de connexion Google et n'atterrit jamais sur la bibliothèque
audio. Les trois autres (Pixabay Music, Freesound, Free Music Archive)
répondent bien en 200.

Ce patch :
  - envoie YouTube sur l'onglet musique et signale qu'un compte est requis ;
  - ajoute Mixkit et Incompetech, qui se téléchargent SANS compte — utile
    pour un acheteur qui veut de la musique tout de suite.

Idempotent : le patch se reconnaît à la présence de « Mixkit » dans la liste
et ne s'applique qu'une fois. Relançable sans risque.

Run : python scripts/patch_bundle_audiobanks.py [--root <dir>] [--check]
"""
import argparse
import pathlib
import shutil
import sys

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")

OLD = ('[["Pixabay Music","https://pixabay.com/music/"],'
       '["Freesound","https://freesound.org/"],'
       '["Free Music Archive","https://freemusicarchive.org/"],'
       '["YouTube Audio Library","https://studio.youtube.com/"]]')

NEW = ('[["Pixabay Music","https://pixabay.com/music/"],'
       '["Freesound","https://freesound.org/"],'
       '["Free Music Archive","https://freemusicarchive.org/"],'
       '["Mixkit","https://mixkit.co/free-stock-music/"],'
       '["Incompetech","https://incompetech.com/music/royalty-free/music.html"],'
       '["YouTube Audio Library (compte requis)",'
       '"https://studio.youtube.com/channel/UC/music"]]')

MARKER = '["Mixkit","https://mixkit.co/free-stock-music/"]'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".",
                    help="racine du dépôt ou de l'app installée")
    ap.add_argument("--check", action="store_true",
                    help="ne rien écrire, seulement rapporter l'état")
    args = ap.parse_args()

    bundle = pathlib.Path(args.root) / REL_BUNDLE
    if not bundle.is_file():
        return f"[audiobanks] bundle introuvable : {bundle}"

    s = bundle.read_text(encoding="utf-8", errors="surrogateescape")

    if MARKER in s:
        print(f"[audiobanks] déjà appliqué — {bundle}")
        return 0
    n = s.count(OLD)
    if n != 1:
        return (f"[audiobanks] ancre trouvée {n} fois (attendu 1) — abandon. "
                f"Le bundle a-t-il changé ?")
    if args.check:
        print(f"[audiobanks] applicable sur {bundle}")
        return 0

    bak = bundle.with_name(bundle.name + ".bak_audiobanks")
    if not bak.exists():
        shutil.copy2(bundle, bak)
    bundle.write_text(s.replace(OLD, NEW), encoding="utf-8",
                      errors="surrogateescape")
    print(f"[audiobanks] appliqué — {bundle} (backup : {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
