# -*- coding: utf-8 -*-
"""Rattrapage des matieres anterieures : statistiques de maps + rapport de
raccord APRES correction, ecrits dans meta.json.

Les matieres creees avant cette passe n'ont ni `map_stats` (ce que chaque map
contient vraiment) ni `seam.ratio` / `seam.grade` (le seul score qui decide si
la tuile est utilisable). Sans eux, l'ecran retomberait sur un « 8 maps » de
principe et sur le score AVANT correction. Ce script les calcule une fois.

    python scripts/materials_backfill.py             # toutes les matieres
    python scripts/materials_backfill.py mat_xxxx    # une seule
    python scripts/materials_backfill.py --rederive  # + refabrique les maps

Lecture seule cote pixels : aucune map n'est reecrite, seul meta.json change.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services import material_store as MS      # noqa: E402


def main(argv: list[str]) -> int:
    rederive = "--rederive" in argv
    wanted = [a for a in argv if a.startswith("mat_")]
    root = MS.materials_root()
    mids = wanted or sorted(d.name for d in root.iterdir()
                            if d.is_dir() and MS.is_valid_mid(d.name))
    if not mids:
        print("aucune matiere dans", root)
        return 0
    print(f"{len(mids)} matiere(s) dans {root}\n")
    t0 = time.time()
    for mid in mids:
        mat = MS.read_material(mid)
        if mat is None:
            print(f"  {mid}  introuvable")
            continue
        t = time.time()
        # Niveau que la rugosite portait AVANT re-derivation. Sert a savoir si
        # le reglage courant avait ete adopte automatiquement (auquel cas il
        # doit suivre le nouveau motif) ou choisi a la main (auquel cas on n'y
        # touche pas). Sans cette lecture, une matiere restait figee a 0.95
        # alors que le nouveau motif a une moyenne de 0.44 : l'ecart ecrasait
        # toute la variation a la cuisson.
        old_nat = MS.natural_levels(MS.load_maps(mid, ["roughness"])) \
            .get("roughness")
        if rederive:
            # L'AO d'avant cette passe etait plate (moy 251/255 mesuree, soit
            # 1.4 % d'occlusion) : une seule octave et un gain de 1. Les maps
            # doivent etre refabriquees pour porter la nouvelle occlusion de
            # cavite. Local, gratuit, hors ligne.
            base_p = MS.map_path(mid, "basecolor")
            if base_p.is_file():
                from PIL import Image
                from app.services import pbr_service as PBR
                with Image.open(base_p) as im:
                    base = im.copy().convert("RGB")
                fresh = PBR.derive_maps(base, mat["derive"],
                                        list(MS.SECONDARY_MAPS))
                fresh["basecolor"] = base
                MS.save_maps(mid, fresh)
        # Niveau de rugosite jamais touche (1.00, le defaut de principe) : la
        # map est desormais cuite a ce niveau, donc uniformement blanche. On
        # lui rend la valeur que sa propre texture porte. Un niveau REGLE par
        # l'utilisateur (or martele : 0.28) n'est jamais ecrase.
        loaded = MS.load_maps(mid, ["metallic", "roughness"])
        nat = MS.natural_levels(loaded)
        props = dict(mat["props"])
        cur = props.get("roughness", 1.0)
        auto = (abs(cur - 1.0) < 1e-9
                or (old_nat is not None and abs(cur - old_nat) <= 0.02))
        if auto and "roughness" in nat:
            props["roughness"] = nat["roughness"]
        mat["props"] = MS.merge_props(mat["props"], props)
        updated = MS.refresh_report(mat)
        MS.write_material(updated)
        seam = updated.get("seam") or {}
        stats = updated.get("map_stats") or {}
        n_inf = updated.get("maps_informative", 0)
        flat = [k for k, v in stats.items() if not v.get("informative")]
        print(f"  {mid}  {str(mat.get('name'))[:22]:22s} "
              f"raccord {seam.get('ratio')} ({seam.get('grade')})  "
              f"maps utiles {n_inf}/{len(stats)}"
              + (f"  uniformes: {', '.join(flat)}" if flat else "")
              + f"   {time.time() - t:.1f}s")
    print(f"\ntermine en {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
