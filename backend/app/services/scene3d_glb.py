# -*- coding: utf-8 -*-
"""Le Plateau 3D — le GLB de SCÈNE (t127 T2, 07/10/2026 ; spec §2, §10 P1).

Décision du 07/10 : l'écran monte la scène objet par objet dans le canevas three.js (`frontend/lib3d`) ; ce GLB-ci est
une SORTIE — l'artefact versionné et téléchargeable de la scène, relisible par tout outil 3D.

Un nœud par instance (`print3d.glb_de_pieces`, triangles MONDE : les transformations sont cuites dans les sommets, le
GLB n'a ni matériau ni normales — de la géométrie, comme celle du lecteur). Trois niveaux de source :
  * `proxy` : une primitive (boîte, sphère, cylindre de `gltf_builder` ; capsule fabriquée ici) mise aux `dims` ;
  * `allege` : le maillage d'un job `assets3d`, décimé au preset `prop` (2 500 triangles, gltfpack local) — déjà sous
    la cible, il est gardé tel quel et le rapport le dit (`decime: false`) ;
  * `plein` : le maillage tel quel.
Un maillage est RECENTRÉ PAR LE PIED (centre de sa base à l'origine), comme un proxy : ses `dims` mesurées sont rendues
dans le rapport, et ce sont elles que `scene3d.coins()` doit recevoir pour que la mesure du cadre et le GLB parlent de
la même boîte (banc test_scene3d_glb [3c]).
"""
import math

from app.services import gltf_builder, mesh_optimize, print3d
from app.services.scene3d import _num, _rotation, _vec

FORMES = ("boite", "sphere", "cylindre", "capsule")
NIVEAUX = ("proxy", "allege", "plein")
_NATIF = {"boite": ("cube", 2.0, 2.0, 2.0), "sphere": ("sphere", 2.0, 2.0, 2.0), "cylindre": ("cylinder", 1.4, 1.8, 1.4)}


def _tris_de_mesh(m):
    pos, idx = m["positions"], m["indices"]
    p = [(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]) for i in range(len(pos) // 3)]
    return [(p[idx[k]], p[idx[k + 1]], p[idx[k + 2]]) for k in range(0, len(idx), 3)]


def _capsule(seg=24, anneaux=8):
    """Une capsule unité : rayon 1 (x, z), calottes hémisphériques, hauteur totale 4 (y de -2 à 2)."""
    rangs = []
    for k in range(anneaux + 1):                       # calotte haute : y de 2 à 1
        a = (math.pi / 2) * k / anneaux
        rangs.append((1 + math.cos(a), math.sin(a)))
    for k in range(anneaux + 1):                       # calotte basse : y de -1 à -2
        a = (math.pi / 2) * k / anneaux
        rangs.append((-1 - math.sin(a), math.cos(a)))
    pts = [[(r * math.cos(2 * math.pi * j / seg), y, r * math.sin(2 * math.pi * j / seg)) for j in range(seg)]
           for y, r in rangs]
    tris = []
    for a, b in zip(pts, pts[1:]):
        for j in range(seg):
            j2 = (j + 1) % seg
            for t in ((a[j], b[j], b[j2]), (a[j], b[j2], a[j2])):
                if len({t[0], t[1], t[2]}) == 3:       # les pôles écrasent un triangle sur deux
                    tris.append(t)
    return tris


def triangles_proxy(forme, dims):
    """Les triangles d'une primitive posée par le pied : boîte englobante [-w/2, w/2] × [0, h] × [-d/2, d/2]."""
    if forme not in FORMES:
        raise ValueError(f"forme inconnue ({forme}) : {', '.join(FORMES)}.")
    w, h, d = _vec(dims, "dims")
    if min(w, h, d) <= 0:
        raise ValueError("dims : trois longueurs positives attendues.")
    if forme == "capsule":
        tris, nw, nh, nd = _capsule(), 2.0, 4.0, 2.0
    else:
        nom, nw, nh, nd = _NATIF[forme]
        tris = _tris_de_mesh(gltf_builder.build_mesh(nom))
    return [tuple((p[0] * w / nw, p[1] * h / nh + h / 2, p[2] * d / nd) for p in t) for t in tris]


def _boite(tris):
    return ([min(p[i] for t in tris for p in t) for i in range(3)],
            [max(p[i] for t in tris for p in t) for i in range(3)])


def recentrer(tris):
    """(triangles posés par le pied, dims) — le centre de la base à l'origine."""
    lo, hi = _boite(tris)
    cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
    out = [tuple((p[0] - cx, p[1] - lo[1], p[2] - cz) for p in t) for t in tris]
    return out, [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]]


def dims_de_maillage(data: bytes) -> dict:
    tris = print3d.lire_glb_triangles(data)
    if not tris:
        raise ValueError("maillage vide.")
    _t, dims = recentrer(tris)
    return {"dims": dims, "tris": len(tris)}


def placer(tris, transform):
    tr = transform or {}
    pos = _vec(tr.get("pos", [0, 0, 0]), "pos")
    rot = _vec(tr.get("rot", [0, 0, 0]), "rot")
    s = _num(tr.get("scale", 1), "scale", 0, strict=True)
    m = _rotation(rot)

    def f(p):
        v = (p[0] * s, p[1] * s, p[2] * s)
        return tuple(pos[i] + sum(m[i][k] * v[k] for k in range(3)) for i in range(3))
    return [tuple(f(p) for p in t) for t in tris]


def composer(instances, lire_maillage):
    """(octets GLB, rapport). `lire_maillage(instance)` rend les octets du GLB source d'une instance non proxy (ou
    None : refus nommé). Rapport : {instances: [{id, tris, dims, decime?}], tris_total}."""
    if not isinstance(instances, list) or not instances:
        raise ValueError("aucune instance à composer.")
    pieces, rap = [], []
    for inst in instances:
        if not isinstance(inst, dict):
            raise ValueError("instance illisible.")
        iid = str(inst.get("id") or f"inst_{len(pieces)}")
        src = inst.get("source") or {}
        niveau = inst.get("niveau", "proxy")
        if niveau not in NIVEAUX:
            raise ValueError(f"{iid} : niveau inconnu ({niveau}) — {', '.join(NIVEAUX)}.")
        ligne = {"id": iid}
        if src.get("kind", "proxy") == "proxy":
            dims = _vec(inst.get("dims"), f"{iid} : dims")
            base = triangles_proxy(src.get("forme", "boite"), dims)
        else:
            data = lire_maillage(inst)
            if not data:
                raise ValueError(f"{iid} : maillage introuvable ({src.get('job')}/{src.get('file')}).")
            if niveau == "allege":
                try:
                    data, info = mesh_optimize.decimer_octets(data, preset="prop")
                    ligne["decime"] = True
                    ligne["avant"] = info.get("before")
                except ValueError:                     # déjà sous la cible : gardé tel quel, et dit
                    ligne["decime"] = False
            base, dims = recentrer(print3d.lire_glb_triangles(data))
        ligne["tris"] = len(base)
        ligne["dims"] = dims
        rap.append({"id": ligne["id"], "tris": ligne["tris"], "dims": ligne["dims"],
                    **({"decime": ligne["decime"]} if "decime" in ligne else {})})
        pieces.append((iid, placer(base, inst.get("transform"))))
    return print3d.glb_de_pieces(pieces), {"instances": rap, "tris_total": sum(r["tris"] for r in rap)}
