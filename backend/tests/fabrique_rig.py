# -*- coding: utf-8 -*-
"""Un VRAI GLB riggé pour les bancs et les preuves du panneau Rig (tâche T093) — PAS UN TEST (nom sans test_).

Aucune donnée de l'utilisateur ne porte de squelette (relevé du 06/10 : 0 GLB riggé sous outputs/) ; on en fabrique
un, conforme glTF 2.0, que le vrai GLTFLoader de three.js charge comme un export Blender ou Mixamo :

  - une COLONNE carrée (0,5 × 3 × 0,5) en quatre anneaux, y = 0, 1, 2, 3 ;
  - une ARMATURE (nœud « Armature ») qui n'est PAS un os — le cas courant que rig_inventory signale : le parent du
    premier os est absent de la liste des os ;
  - trois os en chaîne : « racine » (y = 0), « coude » (y = 1), « main » (y = 2) ;
  - des poids qui se PARTAGENT aux anneaux du milieu (0,5 / 0,5) : la heatmap a quelque chose à montrer ;
  - deux clips : « plier » (le coude tourne de 60° autour de z, aller-retour en 2 s) et « tourner » (la racine fait
    un demi-tour autour de y en 1 s).

Run : python tests/fabrique_rig.py <chemin.glb>    (écrit le fichier, pour une preuve 8799)
"""
from __future__ import annotations

import math
import struct
import sys


def _quat_z(deg):
    a = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(a), math.cos(a))


def _quat_y(deg):
    a = math.radians(deg) / 2
    return (0.0, math.sin(a), 0.0, math.cos(a))


def glb_rigge() -> bytes:
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from app.services.mesh_edit import ecrire_glb

    h = 0.25
    pos, joints, poids = [], [], []
    for k in range(4):                                     # anneaux y = 0, 1, 2, 3
        for (x, z) in ((-h, -h), (h, -h), (h, h), (-h, h)):
            pos.append((x, float(k), z))
            if k == 0:
                joints.append((0, 0, 0, 0)); poids.append((1.0, 0.0, 0.0, 0.0))
            elif k == 1:
                joints.append((0, 1, 0, 0)); poids.append((0.5, 0.5, 0.0, 0.0))
            elif k == 2:
                joints.append((1, 2, 0, 0)); poids.append((0.5, 0.5, 0.0, 0.0))
            else:
                joints.append((2, 0, 0, 0)); poids.append((1.0, 0.0, 0.0, 0.0))
    idx = []
    for k in range(3):                                     # flancs, normales sortantes
        b, t = 4 * k, 4 * (k + 1)
        for i in range(4):
            j = (i + 1) % 4
            idx += [b + i, t + j, b + j, b + i, t + i, t + j]
    idx += [0, 1, 2, 0, 2, 3]                              # dessous
    idx += [12, 14, 13, 12, 15, 14]                        # dessus

    binc = bytearray()
    vues, acces = [], []

    def ajouter(octets, cible=None):
        while len(binc) % 4:
            binc.append(0)
        v = {"buffer": 0, "byteOffset": len(binc), "byteLength": len(octets)}
        if cible:
            v["target"] = cible
        vues.append(v)
        binc.extend(octets)
        return len(vues) - 1

    def accesseur(vue, ct, n, typ, **extra):
        acces.append({"bufferView": vue, "componentType": ct, "count": n, "type": typ, **extra})
        return len(acces) - 1

    a_pos = accesseur(ajouter(struct.pack("<%df" % (3 * len(pos)), *[c for p in pos for c in p]), 34962),
                      5126, len(pos), "VEC3", min=[-h, 0.0, -h], max=[h, 3.0, h])
    a_j = accesseur(ajouter(struct.pack("<%dH" % (4 * len(joints)), *[c for j in joints for c in j]), 34962),
                    5123, len(joints), "VEC4")
    a_w = accesseur(ajouter(struct.pack("<%df" % (4 * len(poids)), *[c for w in poids for c in w]), 34962),
                    5126, len(poids), "VEC4")
    a_i = accesseur(ajouter(struct.pack("<%dH" % len(idx), *idx), 34963), 5123, len(idx), "SCALAR")
    ibm = []
    for y in (0.0, 1.0, 2.0):                              # inverse du lien : translation (0, −y, 0), colonnes
        ibm += [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, -y, 0, 1]
    a_ibm = accesseur(ajouter(struct.pack("<48f", *ibm)), 5126, 3, "MAT4")

    t_plier = [0.0, 1.0, 2.0]
    q_plier = [_quat_z(0), _quat_z(60), _quat_z(0)]
    t_tourner = [0.0, 0.5, 1.0]
    q_tourner = [_quat_y(0), _quat_y(90), _quat_y(180)]
    a_tp = accesseur(ajouter(struct.pack("<3f", *t_plier)), 5126, 3, "SCALAR", min=[0.0], max=[2.0])
    a_qp = accesseur(ajouter(struct.pack("<12f", *[c for q in q_plier for c in q])), 5126, 3, "VEC4")
    a_tt = accesseur(ajouter(struct.pack("<3f", *t_tourner)), 5126, 3, "SCALAR", min=[0.0], max=[1.0])
    a_qt = accesseur(ajouter(struct.pack("<12f", *[c for q in q_tourner for c in q])), 5126, 3, "VEC4")
    while len(binc) % 4:
        binc.append(0)

    doc = {
        "asset": {"version": "2.0", "generator": "Deepotus fabrique_rig (banc)"},
        "scene": 0, "scenes": [{"nodes": [0, 1]}],
        "nodes": [
            {"name": "colonne", "mesh": 0, "skin": 0},
            {"name": "Armature", "children": [2]},
            {"name": "racine", "children": [3]},
            {"name": "coude", "translation": [0.0, 1.0, 0.0], "children": [4]},
            {"name": "main", "translation": [0.0, 1.0, 0.0]},
        ],
        "meshes": [{"name": "colonne", "primitives": [{
            "attributes": {"POSITION": a_pos, "JOINTS_0": a_j, "WEIGHTS_0": a_w}, "indices": a_i, "mode": 4}]}],
        "skins": [{"name": "squelette", "joints": [2, 3, 4], "skeleton": 1, "inverseBindMatrices": a_ibm}],
        "animations": [
            {"name": "plier", "samplers": [{"input": a_tp, "output": a_qp, "interpolation": "LINEAR"}],
             "channels": [{"sampler": 0, "target": {"node": 3, "path": "rotation"}}]},
            {"name": "tourner", "samplers": [{"input": a_tt, "output": a_qt, "interpolation": "LINEAR"}],
             "channels": [{"sampler": 0, "target": {"node": 2, "path": "rotation"}}]},
        ],
        "buffers": [{"byteLength": len(binc)}], "bufferViews": vues, "accessors": acces,
    }
    return ecrire_glb(doc, bytes(binc))


if __name__ == "__main__":
    sortie = sys.argv[1] if len(sys.argv) > 1 else "rig.glb"
    with open(sortie, "wb") as f:
        f.write(glb_rigge())
    print(sortie)
