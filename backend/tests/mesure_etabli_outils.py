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
    elif quoi == "booleen":
        # deux tores de 158 x 158 x 2 = 49 928 triangles, décalés de 1,4 sur x : ils s'intersectent sur une large
        # couronne — la géométrie la plus dure de la famille (courbure partout, aucune face plane)
        from app.services import mesh_boolean, print3d
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from test_mesh_optimize import build_torus_glb
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 158
        pa, pb = pathlib.Path(_tmp, "a.glb"), pathlib.Path(_tmp, "b.glb")
        build_torus_glb(pa, n, n)
        build_torus_glb(pb, n, n)
        ta = print3d.lire_glb_triangles(pa.read_bytes())
        tb = [tuple((p[0] + 1.4, p[1], p[2]) for p in t) for t in print3d.lire_glb_triangles(pb.read_bytes())]
        print(f"A : {len(ta)} tris, B : {len(tb)} tris")
        mesh_boolean.MAX_TRIS = max(mesh_boolean.MAX_TRIS, len(ta), len(tb))
        for op in ("difference", "union", "intersection"):
            r = chrono(f"{op} {len(ta)} x {len(tb)}", lambda o=op: mesh_boolean.operer(ta, tb, o))
            print(f"   -> {len(r)} triangles")
    elif quoi == "orienter":
        from app.services import orient
        data = tore()
        r = chrono("orienter tore 100k", lambda: orient.candidats(data, None))
        print(f"   -> meilleure pose {r['candidats'][0]['bas']}, score {r['candidats'][0]['score']}")
        if REEL.is_file():
            brut = REEL.read_bytes()
            r = chrono("orienter reel", lambda: orient.candidats(brut, None))
            print(f"   -> meilleure pose {r['candidats'][0]['bas']}, appui {r['candidats'][0]['part_contact']:.1%}")
        else:
            print("modele reel absent : saute")
    elif quoi == "tranches":
        from app.services import mesh_slice
        data = tore()
        r = chrono("trancher tore 100k en 20 couches", lambda: mesh_slice.trancher(data, None, "y", nombre=20))
        print(f"   -> {sum(len(c['segments']) for c in r['couches'])} segments, "
              f"perimetre max {max(c['perimetre'] for c in r['couches']):.3f}")
        if REEL.is_file():
            brut = REEL.read_bytes()
            chrono("trancher reel en 20 couches", lambda: mesh_slice.trancher(brut, None, "y", nombre=20))
        else:
            print("modele reel absent : saute")
    elif quoi == "creuser":
        from app.services import hollow
        data = tore()
        _g, r = chrono("creuser tore 100k paroi 0,05", lambda: hollow.creuser(data, None, 0.05))
        print("   ->", r["avertissement"], "paroi_max", r["paroi_max"])
        _g, r = chrono("creuser tore 100k paroi 0,9 > rayon du tube 0,7 (dichotomie)", lambda: hollow.creuser(data, None, 0.9))
        print("   ->", r["pieces"][0]["effondres"], "effondres, paroi_max", r["paroi_max"])
        if REEL.is_file():
            brut = REEL.read_bytes()
            try:
                chrono("creuser reel 144k paroi 0,001", lambda: hollow.creuser(brut, None, 0.001))
            except ValueError as e:
                print("reel refuse :", e)
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
