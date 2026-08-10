# -*- coding: utf-8 -*-
"""Rend une vignette pour CHAQUE effet du catalogue et mesure son écart à la
source.

Un effet dont la vignette est indiscernable de la source est pire qu'un effet
absent : l'utilisateur paie un rendu pour rien. Ce script rend les 39 entrées
via le MÊME service que l'API (effects_preview.render_preview), puis compare
chaque vignette à la source non traitée (écart moyen absolu par pixel, 0-255).

    python scripts/qa/qa_effects_thumbs.py [dossier_de_sortie] [largeur]
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzfxthumb_"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.services import effects_engine as fx           # noqa: E402
from app.services import effects_preview as fxp         # noqa: E402
from PIL import Image, ImageChops, ImageStat            # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("shots/fx")
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 480
OUT.mkdir(parents=True, exist_ok=True)

#: En dessous de cet écart moyen, la vignette ne montre rien à l'oeil.
SEUIL = 2.0


def mad(a: Path, b: Path) -> float:
    with Image.open(a) as ia, Image.open(b) as ib:
        ia, ib = ia.convert("RGB"), ib.convert("RGB")
        if ia.size != ib.size:
            ib = ib.resize(ia.size)
        st = ImageStat.Stat(ImageChops.difference(ia, ib))
    return sum(st.mean) / len(st.mean)


def main():
    cat = fx.catalog()
    # Référence : la source passée par la même chaîne, sans effet.
    ref = fxp.render_preview("blur", {"intensity": 0}, width=WIDTH, t=0.6)
    ref_copy = OUT / "_source.jpg"
    ref_copy.write_bytes(ref.read_bytes())

    rows, faibles, casses = [], [], []
    for name in sorted(cat):
        spec = cat[name]
        params = {}
        for p in spec.get("params") or []:
            b = spec["bounds"][p]
            if b["type"] == "range":
                params[p] = 75 if p == "intensity" else b["default"]
            elif b["type"] in ("color", "choice") and b.get("default"):
                params[p] = b["default"]
        try:
            jpg = fxp.render_preview(name, params, width=WIDTH, t=0.6)
        except Exception as e:                      # noqa: BLE001
            casses.append((name, str(e)[:160]))
            print(f"  ECHEC {name:12s} {e}")
            continue
        dst = OUT / f"{name}.jpg"
        dst.write_bytes(jpg.read_bytes())
        d = mad(dst, ref_copy)
        rows.append((name, spec["cat"], d))
        if d < SEUIL:
            faibles.append((name, d))
        print(f"  {name:12s} {spec['cat']:12s} ecart={d:6.2f}  -> {dst.name}")

    print(f"\n{len(rows)}/{len(cat)} vignettes rendues dans {OUT.resolve()}")
    if casses:
        print("\nEFFETS EN ECHEC (ffmpeg n'a rien produit) :")
        for n, why in casses:
            print(f"  - {n}: {why}")
    print(f"\nEcart < {SEUIL} (vignette quasi identique a la source) :")
    if faibles:
        for n, d in sorted(faibles, key=lambda r: r[1]):
            print(f"  - {n}: {d:.2f}")
    else:
        print("  aucun")
    return 1 if casses else 0


if __name__ == "__main__":
    sys.exit(main())
