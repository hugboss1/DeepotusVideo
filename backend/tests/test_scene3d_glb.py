# -*- coding: utf-8 -*-
"""t127 T2 (07/10/2026) — le composeur du GLB de scène du Plateau (`app.services.scene3d_glb`), spec §2 et §10 P1.

Le GLB composé est RELU par `print3d.lire_glb_triangles`, le lecteur éprouvé du dépôt (spec §11 : « si la composition
ment, le lecteur le voit ») : un nœud par instance, et la boîte de chaque nœud tombe EXACTEMENT sur les huit coins que
`scene3d.coins()` calcule pour la même instance — la composition et la mesure du cadre parlent de la même géométrie.

  [1] proxys : boîte, sphère, cylindre, capsule — posés par le pied, aux dimensions déclarées ;
  [2] transformations : position, rotation XYZ, échelle — relues nœud par nœud ;
  [3] maillage d'un job : recentré par le pied, ses `dims` mesurées rendues, décimé au niveau « allégé » (gltfpack,
      si présent) et tel quel au niveau « plein » ;
  [4] refus nommés et rapport (triangles par instance, total).
Run : & $PY tests/test_scene3d_glb.py   (depuis backend/)
"""
import math
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


try:
    from app.services import scene3d as S, scene3d_glb as G, print3d as P
except Exception as e:
    S = G = P = None
    print(f"  (import impossible : {e!r})")
check("x0_modules_importes", G is not None)
if G is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)


def boite(tris):
    xs = [p[i] for t in tris for p in t for i in (0,)]
    ys = [p[1] for t in tris for p in t]
    zs = [p[2] for t in tris for p in t]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]


def boite_coins(inst):
    cs = S.coins(inst)
    return [min(c[i] for c in cs) for i in range(3)], [max(c[i] for c in cs) for i in range(3)]


def egal(a, b, tol=1e-4):
    return all(abs(x - y) <= tol for x, y in zip(a[0] + a[1], b[0] + b[1]))


def inst(i, forme, dims, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0, **k):
    d = {"id": i, "nom": i, "source": {"kind": "proxy", "forme": forme}, "dims": list(dims), "niveau": "proxy",
         "transform": {"pos": list(pos), "rot": list(rot), "scale": scale}, "role": "decor"}
    d.update(k)
    return d


print("\n[1] proxys posés par le pied")
FORMES = [("boite", [1.0, 2.0, 0.5]), ("sphere", [1.2, 1.2, 1.2]), ("cylindre", [0.6, 1.8, 0.6]), ("capsule", [0.5, 1.7, 0.4])]
INST = [inst("i_" + f, f, d, pos=(k * 3.0, 0, 0)) for k, (f, d) in enumerate(FORMES)]
glb, rap = G.composer(INST, lambda _i: None)
tous = P.lire_glb_triangles(glb)
check("1a_un_glb_relu_par_le_lecteur_du_depot", len(glb) > 100 and len(tous) == rap["tris_total"] > 0, (len(tous), rap["tris_total"]))
for k, ins in enumerate(INST):
    tr = P.lire_glb_triangles(glb, noeuds={k})
    check(f"1b_{ins['source']['forme']}_sa_boite_est_celle_de_ses_coins", egal(boite(tr), boite_coins(ins)), (boite(tr), boite_coins(ins)))
check("1c_un_noeud_nomme_par_instance", rap["instances"] == [{"id": i["id"], "tris": rap["instances"][k]["tris"], "dims": i["dims"]}
                                                             for k, i in enumerate(INST)], rap["instances"])
cap = P.lire_glb_triangles(glb, noeuds={3})
haut = [p for t in cap for p in t if p[1] > 1.7 - 0.15]   # au-dessus de la bague du haut (1,5 m), dans la calotte
check("1d_capsule_arrondie_le_haut_est_plus_etroit_que_le_milieu",
      max(abs(p[0] - 9.0) for p in haut) < 0.25 - 1e-6, max(abs(p[0] - 9.0) for p in haut))

print("\n[2] transformations")
T = [inst("a", "boite", [1, 2, 0.5], pos=(2, 0.5, -1), rot=(0, 90, 0)),
     inst("b", "boite", [1, 1, 1], pos=(0, 0, 0), rot=(30, 20, 10), scale=1.5),
     inst("c", "cylindre", [0.4, 1, 0.4], pos=(-3, 0, 2), scale=2)]
glb2, _r = G.composer(T, lambda _i: None)
for k, ins in enumerate(T):
    tr = P.lire_glb_triangles(glb2, noeuds={k})
    check(f"2_{ins['id']}_relu_ou_la_transformation_le_dit", egal(boite(tr), boite_coins(ins)), (boite(tr), boite_coins(ins)))
check("2d_temoin_rotation_y90_echange_largeur_et_profondeur",
      abs((boite(P.lire_glb_triangles(glb2, noeuds={0}))[1][0] - boite(P.lire_glb_triangles(glb2, noeuds={0}))[0][0]) - 0.5) < 1e-4)

print("\n[3] maillage d'un job")
# un « maillage » : une boîte de 4 × 2 × 1 décalée loin de l'origine (son pied à y = 5)
src = P.glb_de_triangles([t for t in P.lire_glb_triangles(G.composer([inst("x", "boite", [4, 2, 1], pos=(10, 5, 10))], lambda _i: None)[0])], "piece")
M = {"id": "m", "nom": "m", "source": {"kind": "assets3d", "job": "j1", "file": "model.glb"}, "niveau": "plein",
     "dims": None, "transform": {"pos": [1, 0, 0], "rot": [0, 0, 0], "scale": 1}, "role": "sujet"}
glb3, r3 = G.composer([M], lambda i: src)
mm = r3["instances"][0]
check("3a_dims_mesurees_rendues", [round(x, 6) for x in mm["dims"]] == [4.0, 2.0, 1.0], mm)
tr = P.lire_glb_triangles(glb3, noeuds={0})
check("3b_recentre_par_le_pied_puis_place", egal(boite(tr), ([-1, 0, -0.5], [3, 2, 0.5])), boite(tr))
check("3c_coins_de_la_mesure_avec_les_dims_rendues", egal(boite(tr), boite_coins(dict(M, dims=mm["dims"]))))
dims_seul = G.dims_de_maillage(src)
check("3d_dims_de_maillage_sans_composer", [round(x, 6) for x in dims_seul["dims"]] == [4.0, 2.0, 1.0] and dims_seul["tris"] == 12, dims_seul)
if True:                                     # gltfpack absent : le refus nommé est contrôlé à sa place
    gros = P.glb_de_triangles(G.triangles_proxy("sphere", [1, 1, 1]) * 3, "s")   # une sphère dense
    try:
        glb4, r4 = G.composer([dict(M, niveau="allege")], lambda i: gros)
        check("3e_allege_decime_vers_le_preset_prop", r4["instances"][0]["tris"] <= 2500 + 50
              and r4["instances"][0].get("decime") is True, r4["instances"][0])
    except RuntimeError as e:
        check("3e_allege_gltfpack_absent_dit", "gltfpack" in str(e), e)
petit = P.glb_de_triangles(G.triangles_proxy("boite", [1, 1, 1]), "b")
_g5, r5 = G.composer([dict(M, niveau="allege")], lambda i: petit)
check("3f_allege_deja_sous_la_cible_garde_le_maillage_et_le_dit",
      r5["instances"][0]["tris"] == 12 and r5["instances"][0].get("decime") is False, r5["instances"][0])

print("\n[4] refus et rapport")
for nom, liste, src_ in (("aucune_instance", [], None), ("forme_inconnue", [inst("z", "cone", [1, 1, 1])], None),
                         ("dims_negatives", [inst("z", "boite", [1, -1, 1])], None),
                         ("maillage_introuvable", [dict(M)], "None"),
                         ("niveau_inconnu", [dict(M, niveau="ultra")], src)):
    try:
        G.composer(liste, (lambda i: None) if src_ in (None, "None") else (lambda i: src_))
        check(f"4_{nom}_refuse", False)
    except ValueError as e:
        check(f"4_{nom}_refuse", bool(str(e)), e)
check("4f_total_egal_a_la_somme", rap["tris_total"] == sum(i["tris"] for i in rap["instances"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
