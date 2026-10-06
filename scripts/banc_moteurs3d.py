# -*- coding: utf-8 -*-
"""Campagne du banc de référence 3D — T107 (plan-moteurs-3d T8, R10e D2).

Ce script NE DÉPENSE RIEN. Sans argument il imprime le plan de tir (sujet x moteur, coût estimé, ce qui est déjà
mesuré) ; avec `--enregistrer <job> <sujet>` il range un job déjà produit (le moteur est lu dans son manifeste).

  python scripts/banc_moteurs3d.py
  python scripts/banc_moteurs3d.py --enregistrer 7f3a1b2c personnage

Le tir lui-même se fait par l'interface (/studio3d), en voyant le coût : l'argent se dépense sur un geste. Les données
lues sont celles de DEEPOTUS_DATA_DIR (par défaut %LOCALAPPDATA%\\DeepotusVideoGenData)."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.services import asset3d_banc as B          # noqa: E402
from app.services import asset3d_service as A3      # noqa: E402
from app.services import pricing                    # noqa: E402


def cout_du_tir(moteur: str) -> float:
    """Le tir type d'un point du banc : texturé, avec les vues que le moteur sait prendre (4 au plus)."""
    caps = A3.engine_caps(moteur)
    vues = 4 if caps.get("multiview") else 0
    return float(pricing.estimate({"kind": "asset3d", "engine": moteur, "textures": True,
                                   "multiview": bool(vues), "views": vues})["total_usd"])


def plan() -> None:
    fait = {(l["sujet"], l["moteur"]) for l in B.lire()["lignes"]}
    total, a_tirer = 0.0, 0
    print(f"{'sujet':<12} {'moteur':<12} {'coût estimé':>12}  état")
    for s in B.SUJETS:
        for m in sorted(A3.ENGINES):
            usd = cout_du_tir(m)
            etat = "mesuré" if (s, m) in fait else "à tirer"
            if etat == "à tirer":
                total += usd
                a_tirer += 1
            print(f"{s:<12} {m:<12} {usd:>10.2f} $  {etat}")
    print(f"\nReste à dépenser pour compléter le banc : {total:.2f} $ ({a_tirer} tirs).")
    r = B.resume_par_moteur()
    if r:
        print("\nCe que le banc dit déjà :")
        for m, x in sorted(r.items()):
            print(f"  {m:<12} {x['sujets']} sujet(s) · {x['tris_median']} tris médians · "
                  f"{x['usd_median']:.2f} $ médians · étanche sur {x['ferme_sur']}/{x['mesures']}")


def main() -> None:
    a = sys.argv[1:]
    if a and a[0] == "--enregistrer":
        if len(a) != 3:
            raise SystemExit("Usage : --enregistrer <job> <sujet>")
        ligne = B.mesurer(a[1], a[2])
        print(f"OK — {ligne['sujet']} / {ligne['moteur']} : {ligne['tris']} tris, {ligne['bytes']} o, "
              f"{ligne['usd_estime']:.2f} $ estimés, étanche={ligne['ferme']}")
        return
    plan()


if __name__ == "__main__":
    main()
