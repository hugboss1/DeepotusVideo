# -*- coding: utf-8 -*-
"""t343 — squelettes SYNTHÉTIQUES pour les bancs du mouvement sur le rig (aucun fichier réel n'est requis).

- `bvh_source()` : un BVH « Mixamo » (Y en haut, centimètres, pose en T) dont le bassin avance de 100 cm en X, le
  bras gauche se lève de 90° (Z), la cuisse droite se plie (X) et la colonne tourne (Y), 31 images à 30 i/s ;
- `glb_cible()` : un personnage riggé « Unreal » (pelvis, spine_01…03, clavicle_l, upperarm_l…) en pose en A, os
  dans un repère Z en haut en centimètres sous une armature tournée de -90° en X et mise à l'échelle 0,01 (comme un
  export Blender) ; peau = une boîte par os, poids 1 — chargeable par three.js et Godot.
"""
import math
import struct

from app.services import mesh_edit
from app.services.mouvement_rig import q_axe, q_mul, q_rot, Q_ID

# ── la source : un BVH « Mixamo » ──────────────────────────────────────────

_SRC = [  # nom, parent, offset (cm, Y en haut)
    ("Hips", None, (0, 100, 0)),
    ("Spine", "Hips", (0, 10, 0)), ("Spine1", "Spine", (0, 10, 0)), ("Neck", "Spine1", (0, 15, 0)),
    ("Head", "Neck", (0, 10, 0)),
    ("LeftShoulder", "Spine1", (5, 12, 0)), ("LeftArm", "LeftShoulder", (10, 0, 0)),
    ("LeftForeArm", "LeftArm", (25, 0, 0)), ("LeftHand", "LeftForeArm", (25, 0, 0)),
    ("RightShoulder", "Spine1", (-5, 12, 0)), ("RightArm", "RightShoulder", (-10, 0, 0)),
    ("RightForeArm", "RightArm", (-25, 0, 0)), ("RightHand", "RightForeArm", (-25, 0, 0)),
    ("LeftUpLeg", "Hips", (8, -5, 0)), ("LeftLeg", "LeftUpLeg", (0, -45, 0)), ("LeftFoot", "LeftLeg", (0, -45, 0)),
    ("LeftToeBase", "LeftFoot", (0, -5, 10)),
    ("RightUpLeg", "Hips", (-8, -5, 0)), ("RightLeg", "RightUpLeg", (0, -45, 0)),
    ("RightFoot", "RightLeg", (0, -45, 0)), ("RightToeBase", "RightFoot", (0, -5, 10)),
]
N_IMAGES = 31


def anim_source(f: int, n: int = N_IMAGES) -> dict:
    """Les canaux animés à l'image f (degrés)."""
    u = f / (n - 1)
    return {"Hips": {"Xposition": 100 * u, "Yposition": 100.0, "Zposition": 0.0},
            "LeftArm": {"Zrotation": 90 * u}, "RightUpLeg": {"Xrotation": -30 * u}, "Spine1": {"Yrotation": 20 * u},
            "LeftForeArm": {"Yrotation": 40 * u}}


def bvh_source(n: int = N_IMAGES) -> str:
    enfants = {}
    for nom, p, _o in _SRC:
        enfants.setdefault(p, []).append(nom)
    off = {nom: o for nom, _p, o in _SRC}
    lignes, ordre = ["HIERARCHY"], []

    def ecrire(nom, prof):
        ind = "  " * prof
        lignes.append(f"{ind}{'ROOT' if prof == 0 else 'JOINT'} {nom}")
        lignes.append(f"{ind}{{")
        o = (0, 0, 0) if prof == 0 else off[nom]
        lignes.append(f"{ind}  OFFSET {o[0]} {o[1]} {o[2]}")
        if prof == 0:
            lignes.append(f"{ind}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")
        else:
            lignes.append(f"{ind}  CHANNELS 3 Zrotation Xrotation Yrotation")
        ordre.append(nom)
        if enfants.get(nom):
            for e in enfants[nom]:
                ecrire(e, prof + 1)
        else:
            lignes.extend([f"{ind}  End Site", f"{ind}  {{", f"{ind}    OFFSET 0 5 0", f"{ind}  }}"])
        lignes.append(f"{ind}}}")
    ecrire("Hips", 0)
    lignes += ["MOTION", f"Frames: {n}", f"Frame Time: {1 / 30:.6f}"]
    for f in range(n):
        a = anim_source(f, n)
        vals = []
        for nom in ordre:
            c = a.get(nom, {})
            if nom == "Hips":
                vals += [c["Xposition"], c["Yposition"], c["Zposition"], 0, 0, 0]
            else:
                vals += [c.get("Zrotation", 0), c.get("Xrotation", 0), c.get("Yrotation", 0)]
        lignes.append(" ".join(f"{v:.4f}" for v in vals))
    return "\n".join(lignes) + "\n"


# ── la cible : un personnage « Unreal » en A, Z en haut, armature -90° X × 0,01 ─────────────────

_CIB = [  # nom, parent, translation (cm, Z en haut), rotation
    ("pelvis", None, (0, 0, 95), Q_ID),
    ("spine_01", "pelvis", (0, 0, 8), Q_ID), ("spine_02", "spine_01", (0, 0, 8), Q_ID),
    ("spine_03", "spine_02", (0, 0, 8), Q_ID), ("neck_01", "spine_03", (0, 0, 14), Q_ID),
    ("head", "neck_01", (0, 0, 9), Q_ID),
    ("clavicle_l", "spine_03", (4, 0, 11), Q_ID), ("upperarm_l", "clavicle_l", (12, 0, 0), q_axe("Y", 45)),
    ("lowerarm_l", "upperarm_l", (28, 0, 0), Q_ID), ("hand_l", "lowerarm_l", (24, 0, 0), Q_ID),
    ("clavicle_r", "spine_03", (-4, 0, 11), Q_ID), ("upperarm_r", "clavicle_r", (-12, 0, 0), q_axe("Y", -45)),
    ("lowerarm_r", "upperarm_r", (-28, 0, 0), Q_ID), ("hand_r", "lowerarm_r", (-24, 0, 0), Q_ID),
    ("thigh_l", "pelvis", (9, 0, -3), Q_ID), ("calf_l", "thigh_l", (0, 0, -44), Q_ID),
    ("foot_l", "calf_l", (0, 0, -44), Q_ID), ("ball_l", "foot_l", (0, -12, -5), Q_ID),
    ("thigh_r", "pelvis", (-9, 0, -3), Q_ID), ("calf_r", "thigh_r", (0, 0, -44), Q_ID),
    ("foot_r", "calf_r", (0, 0, -44), Q_ID), ("ball_r", "foot_r", (0, -12, -5), Q_ID),
]
ARMATURE_R = q_axe("X", -90)
ARMATURE_S = 0.01


def _mat(t, r, s):
    """Matrice 4×4 (colonnes, glTF) de T · R · S uniforme."""
    x, y, z, w = r
    m = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [m[0][0] * s, m[1][0] * s, m[2][0] * s, 0, m[0][1] * s, m[1][1] * s, m[2][1] * s, 0,
            m[0][2] * s, m[1][2] * s, m[2][2] * s, 0, t[0], t[1], t[2], 1]


def _mul4(a, b):
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
    return out


def _inv_affine(m):
    """Inverse d'une matrice T·R·s (s uniforme)."""
    s2 = m[0] ** 2 + m[1] ** 2 + m[2] ** 2
    rt = [[m[0] / s2, m[4] / s2, m[8] / s2], [m[1] / s2, m[5] / s2, m[9] / s2], [m[2] / s2, m[6] / s2, m[10] / s2]]
    t = m[12:15]
    ti = [-(rt[i][0] * t[0] + rt[i][1] * t[1] + rt[i][2] * t[2]) for i in range(3)]
    return [rt[0][0], rt[1][0], rt[2][0], 0, rt[0][1], rt[1][1], rt[2][1], 0, rt[0][2], rt[1][2], rt[2][2], 0,
            ti[0], ti[1], ti[2], 1]


def glb_cible(prefixe: str = "", os_def=None) -> bytes:
    """Le personnage riggé : nœud 0 = armature, puis un nœud par os, puis le maillage skinné."""
    os_def = os_def or _CIB
    noms = [prefixe + n for n, _p, _t, _r in os_def]
    idx = {n: k + 1 for k, (n, _p, _t, _r) in enumerate(os_def)}
    nodes = [{"name": "Armature", "rotation": list(ARMATURE_R), "scale": [ARMATURE_S] * 3, "children": []}]
    for (n, p, t, r), nm in zip(os_def, noms):
        nd = {"name": nm, "translation": list(map(float, t))}
        if r != Q_ID:
            nd["rotation"] = list(r)
        nodes.append(nd)
        (nodes[0] if p is None else nodes[idx[p]]).setdefault("children", []).append(idx[n])
    # monde de repos de chaque os
    monde = {}
    arm = _mat((0, 0, 0), ARMATURE_R, ARMATURE_S)
    for n, p, t, r in os_def:
        monde[n] = _mul4(arm if p is None else monde[p], _mat(t, r, 1.0))
    # peau : une boîte par os, de sa tête à la tête de son premier enfant (un bout : 5 cm), poids 1
    enfants = {}
    for n, p, _t, _r in os_def:
        enfants.setdefault(p, []).append(n)
    pos, jts, wts, ind = [], [], [], []
    for k, (n, _p, _t, _r) in enumerate(os_def):
        a = monde[n][12:15]
        e = enfants.get(n)
        b = monde[e[0]][12:15] if e else [a[0], a[1] + 0.05, a[2]]
        w = 0.025
        lo = [min(a[i], b[i]) - w for i in range(3)]
        hi = [max(a[i], b[i]) + w for i in range(3)]
        base = len(pos)
        for c in range(8):
            pos.append((hi[0] if c & 1 else lo[0], hi[1] if c & 2 else lo[1], hi[2] if c & 4 else lo[2]))
            jts.append((k, 0, 0, 0))
            wts.append((1.0, 0.0, 0.0, 0.0))
        for f in ((0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7),
                  (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)):
            ind += [base + v for v in f]
    ibm = [v for n, _p, _t, _r in os_def for v in _inv_affine(monde[n])]
    binc = bytearray()
    vues, accs = [], []

    def ajouter(fmt, valeurs, count, type_, ct, minmax=None, cible=None):
        nonlocal binc
        binc += b"\x00" * (-len(binc) % 4)
        d = len(binc)
        binc += struct.pack(f"<{len(valeurs)}{fmt}", *valeurs)
        v = {"buffer": 0, "byteOffset": d, "byteLength": len(binc) - d}
        if cible:
            v["target"] = cible
        vues.append(v)
        a = {"bufferView": len(vues) - 1, "componentType": ct, "count": count, "type": type_}
        if minmax:
            a["min"], a["max"] = minmax
        accs.append(a)
        return len(accs) - 1
    a_pos = ajouter("f", [c for p in pos for c in p], len(pos), "VEC3", 5126,
                    ([min(p[i] for p in pos) for i in range(3)], [max(p[i] for p in pos) for i in range(3)]), 34962)
    a_j = ajouter("H", [c for p in jts for c in p], len(jts), "VEC4", 5123, cible=34962)
    a_w = ajouter("f", [c for p in wts for c in p], len(wts), "VEC4", 5126, cible=34962)
    a_i = ajouter("I", ind, len(ind), "SCALAR", 5125, cible=34963)
    a_ibm = ajouter("f", ibm, len(os_def), "MAT4", 5126)
    nodes.append({"name": "Corps", "mesh": 0, "skin": 0})
    doc = {"asset": {"version": "2.0", "generator": "banc t343"},
           "scene": 0, "scenes": [{"nodes": [0, len(nodes) - 1]}], "nodes": nodes,
           "meshes": [{"name": "Corps", "primitives": [{"attributes": {"POSITION": a_pos, "JOINTS_0": a_j,
                                                                         "WEIGHTS_0": a_w}, "indices": a_i,
                                                          "material": 0}]}],
           "materials": [{"name": "argile", "pbrMetallicRoughness": {"baseColorFactor": [0.8, 0.55, 0.4, 1],
                                                                     "metallicFactor": 0, "roughnessFactor": 0.8},
                          "doubleSided": True}],
           "skins": [{"name": "Rig", "joints": [idx[n] for n, *_ in os_def], "skeleton": 0,
                      "inverseBindMatrices": a_ibm}],
           "accessors": accs, "bufferViews": vues, "buffers": [{"byteLength": len(binc)}]}
    return mesh_edit.ecrire_glb(doc, bytes(binc))


def angle(u, v) -> float:
    nu = math.sqrt(sum(c * c for c in u))
    nv = math.sqrt(sum(c * c for c in v))
    d = max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v)) / (nu * nv)))
    return math.degrees(math.acos(d))


__all__ = ["bvh_source", "glb_cible", "anim_source", "angle", "N_IMAGES", "q_rot", "q_mul"]
