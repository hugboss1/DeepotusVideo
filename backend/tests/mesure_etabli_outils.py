# -*- coding: utf-8 -*-
"""Mesures des budgets des outils de l'Établi — PAS UN TEST (nom sans test_ : pytest ne le collecte pas).
Run (depuis backend/) : & $PY tests/mesure_etabli_outils.py reparer
Le maillage de mesure : le tore de test_mesh_optimize (224 x 224 = 100 352 triangles) et, s'il existe, le modèle réel
de l'utilisateur (assets3d/6e0a8a5f/model.v5.glb, 144 274 triangles, douze pièces) — LU, jamais écrit."""
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("FAL_KEY", "test-key")
_tmp = tempfile.mkdtemp()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
REEL = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGenData" / "assets" / "outputs" / "assets3d" \
    / "6e0a8a5f" / "model.v5.glb"


def tore():
    from test_mesh_optimize import build_torus_glb
    p = pathlib.Path(_tmp, "tore.glb")
    n = build_torus_glb(p, 224, 224)
    print(f"tore : {n['tris']} triangles")
    return p.read_bytes()


def chrono(nom, f):
    t0 = time.perf_counter()
    r = f()
    print(f"{nom} : {time.perf_counter() - t0:.2f} s")
    return r


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    quoi = sys.argv[1] if len(sys.argv) > 1 else "reparer"
    if quoi == "reparer":
        from app.services import mesh_repair
        data = tore()
        chrono("reparer tore 100k (defaut)", lambda: mesh_repair.reparer(data, None, None))
        chrono("reparer tore 100k (tout)", lambda: mesh_repair.reparer(data, None, list(mesh_repair.ACTIONS)))
        if REEL.is_file():
            brut = REEL.read_bytes()
            _g, r = chrono("reparer reel 144k (tout)", lambda: mesh_repair.reparer(brut, None, list(mesh_repair.ACTIONS)))
            print({k: sum((p[k] or 0) if not isinstance(p[k], dict) else p[k]["bouches"] for p in r["pieces"])
                   for k in ("soudes", "doublons", "degeneres", "retournes", "trous")}, "ferme :", r["ferme_avant"], "->",
                  r["ferme_apres"])
        else:
            print("modele reel absent : saute")
    elif quoi == "nesting":
        import random
        from app.services import nesting
        random.seed(7)
        for n in (12, 120, 500):
            pieces = [{"cle": i, "l": random.uniform(5, 60), "p": random.uniform(5, 60)} for i in range(n)]
            r = chrono(f"ranger {n} pieces", lambda: nesting.ranger(pieces, (256.0, 256.0), 2.0))
            print(f"   -> {len(r['plateaux'])} plateau(x), taux {['%.2f' % t for t in r['taux']]}, "
                  f"{len(r['debordent'])} debordent")
