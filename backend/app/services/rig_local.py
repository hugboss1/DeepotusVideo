# -*- coding: utf-8 -*-
"""t395 (31/10/2026) — le RIG SEMI-AUTOMATIQUE local du 3D Studio (écran Rig, D3) : gratuit, hors ligne, Python pur.

Relevé de Sorceress (§5 de l'inventaire) : un gabarit SMPL de 22 os, des articulations que l'utilisateur place et
ajuste, des os de poitrine en option, puis « Recompute » des poids. Ici :

  - `proposition` : les 22 articulations d'un humanoïde en pose en A ou en T, déduites de la BOÎTE du modèle par des
    proportions (bassin à 53 % de la hauteur, épaules à 81,5 %…), l'inclinaison des bras étant lue dans la largeur
    de la boîte (bras horizontaux si l'envergure vaut la hauteur). Si la version porte déjà un squelette écrit par ce
    module (mêmes noms d'os), ce sont SES articulations qui reviennent : l'ajustement reprend où on l'avait laissé ;
  - `appliquer` : le squelette (parenté SMPL), les poids de peau, et un GLB skinné (JOINTS_0 / WEIGHTS_0, une peau,
    ses inverseBindMatrices) écrit comme VERSION de plus par `mesh_edit.ecrire_version` — jamais un écrasement.

LES POIDS — méthode « distance aux segments d'os », pas la chaleur d'os : la chaleur demande une résolution de
Laplacien sur le maillage, hors de portée de Python pur sur 100 000 sommets. Pour chaque sommet :
  1. la distance à chaque os, vu comme le SEGMENT de son articulation à celle de son enfant principal (une feuille —
     tête, main, orteil, poitrine — est prolongée dans la direction de son os parent) ;
  2. on garde les os à moins de 1,6 × la plus courte distance + 1 % de la hauteur, quatre au plus ;
  3. un os d'un côté (_l / _r) n'influence pas un sommet nettement de l'autre côté de l'axe de symétrie (au-delà de
     1 % de la hauteur) : sans cette règle, l'intérieur d'une cuisse suivrait un peu l'autre jambe ;
  4. poids = 1 / d⁶, normalisés à 1 (assez raide pour qu'un membre reste rigide hors de ses articulations).
Une articulation (coude, genou) se partage donc naturellement à 50/50 entre ses deux os ; l'écran Affiner corrigera
le reste au pinceau. Deux sommets de même position (couture d'UV) reçoivent les mêmes poids, calculés une fois.

LE DOCUMENT ÉCRIT : le graphe de scène est reconstruit — un nœud par os (translations seules, rotations nulles), puis un
nœud skinné par instance de maillage, à la racine et sans transformation. Les positions et normales sont CUITES en
repère monde (la spec glTF ignore la transformation d'un nœud skinné, et three.js ne l'ignore pas : un nœud neutre met
tout le monde d'accord). Un modèle déjà riggé est d'abord ramené à sa pose de repos (Σ wᵢ · Jᵢ · IBMᵢ · p) ; son ancien
squelette et ses clips sont retirés (ils visaient des os qui n'existent plus — la fiche le dit). Matériaux, textures et
UV restent tels quels. Refus : Draco et meshopt (les positions ne sont pas lisibles sans décodeur), buffer externe.
"""
from __future__ import annotations

import copy
import math
import struct

from app.services import mesh_edit as ME

# ── le gabarit SMPL : 22 os, noms « Unreal » (le reciblage de mouvement_rig.role() les reconnaît tous) ──────────────
# (id, parent) dans l'ordre de l'inventaire Sorceress : colonne, puis bras gauche/droit, puis jambes gauche/droite.
OS = [
    ("pelvis", None), ("spine_01", "pelvis"), ("spine_02", "spine_01"), ("spine_03", "spine_02"),
    ("neck_01", "spine_03"), ("head", "neck_01"),
    ("clavicle_l", "spine_03"), ("upperarm_l", "clavicle_l"), ("lowerarm_l", "upperarm_l"), ("hand_l", "lowerarm_l"),
    ("clavicle_r", "spine_03"), ("upperarm_r", "clavicle_r"), ("lowerarm_r", "upperarm_r"), ("hand_r", "lowerarm_r"),
    ("thigh_l", "pelvis"), ("calf_l", "thigh_l"), ("foot_l", "calf_l"), ("ball_l", "foot_l"),
    ("thigh_r", "pelvis"), ("calf_r", "thigh_r"), ("foot_r", "calf_r"), ("ball_r", "foot_r"),
]
POITRINE = [("breast_l", "spine_03"), ("breast_r", "spine_03")]
IDS = [i for i, _p in OS]
IDS_POITRINE = [i for i, _p in POITRINE]
PARENTS = {i: p for i, p in OS + POITRINE}
# l'enfant qui DONNE la direction d'un os qui en a plusieurs (bassin → colonne, haut du dos → cou)
PRINCIPAL = {"pelvis": "spine_01", "spine_03": "neck_01"}

MAX_SOMMETS = 400_000            # au-delà : passer d'abord par Préparer (un rig n'a pas besoin de 2 M de sommets)
METHODE = "distance_segments_v1"
_EXT_COMPRESSION = ("KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_meshopt_compression")
_NORMALISATION = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


def cote(id_: str) -> str | None:
    return "l" if id_.endswith("_l") else "r" if id_.endswith("_r") else None


def paire(id_: str) -> str | None:
    c = cote(id_)
    return None if c is None else id_[:-1] + ("r" if c == "l" else "l")


def ordre(avec_poitrine: bool = False) -> list[str]:
    return IDS + (IDS_POITRINE if avec_poitrine else [])


# ── lecture du document : matrices monde, positions cuites ───────────────────────────────────────────────────────────

def _flottants(doc: dict, binc: bytes, i: int) -> list[tuple]:
    """Un accesseur en flottants, `normalized` appliqué (KHR_mesh_quantization, poids en octets)."""
    a = doc["accessors"][i]
    vals = ME.lire_accesseur(doc, binc, i)
    if a.get("normalized"):
        div = _NORMALISATION.get(a["componentType"])
        if div:
            return [tuple(max(c / div, -1.0) for c in v) for v in vals]
    return [tuple(float(c) for c in v) for v in vals]


def _point(m, p):
    x, y, z = p[0], p[1], p[2]
    return (m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


def _vecteur(m, v):
    x, y, z = v[0], v[1], v[2]
    return (m[0] * x + m[4] * y + m[8] * z, m[1] * x + m[5] * y + m[9] * z, m[2] * x + m[6] * y + m[10] * z)


def _unitaire(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-20 else (0.0, 1.0, 0.0)


def _identite(m) -> bool:
    return all(abs(a - b) < 1e-9 for a, b in zip(m, ME._IDENTITE))


def _mondes(doc: dict) -> tuple[dict, list[int]]:
    """{nœud: matrice monde} pour la scène active, et la liste des nœuds porteurs d'un maillage (ordre de parcours)."""
    nodes = doc.get("nodes") or []
    scenes = doc.get("scenes") or []
    racines = (scenes[int(doc.get("scene", 0) or 0)].get("nodes") if scenes else None)
    if racines is None:   # pas de scène : toutes les racines du graphe
        parent = ME._parents(nodes)
        racines = [i for i in range(len(nodes)) if i not in parent]
    mondes, porteurs, pile, vus = {}, [], [(r, ME._IDENTITE) for r in reversed(racines)], set()
    while pile:
        i, pm = pile.pop()
        if i in vus or not 0 <= i < len(nodes):
            continue
        vus.add(i)
        m = ME._mat_mul(pm, ME._mat_locale(nodes[i]))
        mondes[i] = m
        if nodes[i].get("mesh") is not None:
            porteurs.append(i)
        for c in reversed(nodes[i].get("children") or []):
            pile.append((c, m))
    return mondes, porteurs


def _refuser_compression(doc: dict) -> None:
    usees = set(doc.get("extensionsUsed") or []) | set(doc.get("extensionsRequired") or [])
    for e in _EXT_COMPRESSION:
        if e in usees:
            raise ValueError(f"GLB compressé ({e}) : ses positions ne sont pas lisibles ici — rouvre une version non "
                             "compressée (Préparer garde la v1)")
    if len(doc.get("buffers") or []) > 1 or any("uri" in b for b in doc.get("buffers") or []):
        raise ValueError("GLB à plusieurs buffers ou à buffer externe : hors périmètre du rig local")


def _transformations(doc: dict, binc: bytes, noeud: int, prim: dict, mondes: dict):
    """Ce qui amène les sommets d'une primitive en repère monde, à la pose de repos.

    Rend (matrice unique, None) pour un maillage non skinné, ou (None, [matrice par sommet]) pour un skinné :
    Σ wᵢ · monde(jointᵢ) · IBMᵢ, la pose de repos telle que la spec glTF la définit."""
    nodes = doc["nodes"]
    nd = nodes[noeud]
    att = prim.get("attributes") or {}
    skin_i = nd.get("skin")
    if skin_i is None or "JOINTS_0" not in att or "WEIGHTS_0" not in att:
        return mondes.get(noeud, ME._IDENTITE), None
    skin = doc["skins"][skin_i]
    joints = skin.get("joints") or []
    if skin.get("inverseBindMatrices") is not None:
        ibm = [list(v) for v in _flottants(doc, binc, skin["inverseBindMatrices"])]
    else:
        ibm = [list(ME._IDENTITE)] * len(joints)
    mats = []
    for k, j in enumerate(joints):
        jm = mondes.get(j)
        if jm is None:   # os hors de la scène : sa matrice locale chaînée depuis la racine
            jm = ME._mat_mul(ME._monde_des_ancetres(doc, j), ME._mat_locale(nodes[j]))
        mats.append(ME._mat_mul(jm, ibm[k] if k < len(ibm) else ME._IDENTITE))
    js = ME.lire_accesseur(doc, binc, att["JOINTS_0"])
    ws = _flottants(doc, binc, att["WEIGHTS_0"])
    par_sommet, cache = [], {}
    for jv, wv in zip(js, ws):
        cle = (jv, wv)
        m = cache.get(cle)
        if m is None:
            s = sum(w for w in wv if w > 0)
            if s <= 1e-12:
                m = mondes.get(noeud, ME._IDENTITE)
            else:
                m = [0.0] * 16
                for j, w in zip(jv, wv):
                    if w > 0 and 0 <= int(j) < len(mats):
                        mj = mats[int(j)]
                        for c in range(16):
                            m[c] += mj[c] * (w / s)
            cache[cle] = m
        par_sommet.append(m)
    return None, par_sommet


def lire_modele(data: bytes) -> dict:
    """Le document, son tampon et, par instance de maillage, les positions et normales CUITES en repère monde.

    {doc, binc, instances: [{noeud, mesh, prims: [{prim, positions, normales|None, cuit}]}], boite, sommets}."""
    doc, binc = ME.lire_glb(data)
    _refuser_compression(doc)
    mondes, porteurs = _mondes(doc)
    instances, total = [], 0
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for n in porteurs:
        mesh = (doc.get("meshes") or [])[doc["nodes"][n]["mesh"]]
        prims, cache = [], {}
        for prim in mesh.get("primitives") or []:
            att = prim.get("attributes") or {}
            if att.get("POSITION") is None:
                continue
            m, par = _transformations(doc, binc, n, prim, mondes)
            cle = (att["POSITION"], att.get("NORMAL"), att.get("JOINTS_0") if par else None,
                   att.get("WEIGHTS_0") if par else None)
            if cle not in cache:
                pos = _flottants(doc, binc, att["POSITION"])
                nrm = _flottants(doc, binc, att["NORMAL"]) if att.get("NORMAL") is not None else None
                if par is None:
                    cuit = not _identite(m)
                    if cuit:
                        pos = [_point(m, p) for p in pos]
                        nrm = [_unitaire(_vecteur(m, v)) for v in nrm] if nrm else None
                else:
                    cuit = True
                    pos = [_point(par[k], p) for k, p in enumerate(pos)]
                    nrm = [_unitaire(_vecteur(par[k], v)) for k, v in enumerate(nrm)] if nrm else None
                cache[cle] = (pos, nrm, cuit)
                total += len(pos)
                for p in pos:
                    for c in range(3):
                        if p[c] < lo[c]:
                            lo[c] = p[c]
                        if p[c] > hi[c]:
                            hi[c] = p[c]
            pos, nrm, cuit = cache[cle]
            prims.append({"prim": prim, "positions": pos, "normales": nrm, "cuit": cuit, "cle": cle})
        if prims:
            instances.append({"noeud": n, "mesh": doc["nodes"][n]["mesh"], "prims": prims})
    if not instances or total == 0:
        raise ValueError("aucun maillage avec des positions dans ce GLB")
    if total > MAX_SOMMETS:
        raise ValueError(f"{total} sommets : au-delà de {MAX_SOMMETS}, allège d'abord le modèle (écran Préparer)")
    return {"doc": doc, "binc": binc, "instances": instances, "boite": {"min": lo, "max": hi}, "sommets": total,
            "mondes": mondes}


# ── le gabarit ───────────────────────────────────────────────────────────────────────────────────────────────────────

def gabarit(boite: dict, centre_z: float | None = None) -> dict:
    """Les articulations d'un humanoïde dans une boîte (Y en haut, face à +Z, gauche du personnage en +X — glTF).

    Rend {joints, poitrine, axe_x, hauteur, pose}. Proportions moyennes d'un adulte (SMPL) ; l'inclinaison des bras
    vient de l'envergure : demi-largeur − épaule = portée horizontale d'un bras de 44 % de la hauteur. `centre_z` : la
    profondeur du TRONC (les pieds, qui avancent, décentreraient la boîte) ; à défaut, le milieu de la boîte."""
    (x0, y0, z0), (x1, y1, z1) = boite["min"], boite["max"]
    h = max(y1 - y0, 1e-6)
    cx = (x0 + x1) / 2
    cz = (z0 + z1) / 2 if centre_z is None else centre_z

    def y(f):
        return y0 + f * h

    epaule = 0.10 * h
    bras = 0.44 * h
    portee = (x1 - x0) / 2 - epaule
    c = max(0.0, min(1.0, portee / bras))
    s = math.sqrt(max(0.0, 1 - c * c))
    pose = "T" if c > 0.85 else "A" if c > 0.35 else "bas"
    if pose == "T":   # bras horizontaux : la portée EST la longueur du bras, jusqu'au bout des doigts
        c, s, bras = 1.0, 0.0, portee
    g = {
        "pelvis": (cx, y(0.53), cz), "spine_01": (cx, y(0.585), cz), "spine_02": (cx, y(0.65), cz),
        "spine_03": (cx, y(0.72), cz), "neck_01": (cx, y(0.835), cz), "head": (cx, y(0.88), cz),
        "clavicle_l": (cx + 0.02 * h, y(0.80), cz),
        "upperarm_l": (cx + epaule, y(0.815), cz),
        "thigh_l": (cx + 0.055 * h, y(0.50), cz), "calf_l": (cx + 0.055 * h, y(0.28), cz),
        "foot_l": (cx + 0.055 * h, y(0.045), cz), "ball_l": (cx + 0.055 * h, y(0.012), cz + 0.065 * h),
    }
    ep = g["upperarm_l"]
    g["lowerarm_l"] = (ep[0] + c * 0.42 * bras, ep[1] - s * 0.42 * bras, cz)
    g["hand_l"] = (ep[0] + c * 0.78 * bras, ep[1] - s * 0.78 * bras, cz)
    poitrine = {"breast_l": (cx + 0.045 * h, y(0.72), cz + 0.06 * h)}
    for d in (g, poitrine):
        for i in [k for k in d if k.endswith("_l")]:
            x, yy, z = d[i]
            d[paire(i)] = (2 * cx - x, yy, z)
    r = lambda p: [round(v, 6) for v in p]            # noqa: E731
    return {"joints": {i: r(g[i]) for i in IDS}, "poitrine": {i: r(poitrine[i]) for i in IDS_POITRINE},
            "axe_x": round(cx, 6), "hauteur": round(h, 6), "pose": pose}


def _squelette_existant(doc: dict, mondes: dict) -> dict | None:
    """Les articulations d'un squelette écrit par CE module (tous nos noms présents dans une peau), sinon None."""
    nodes = doc.get("nodes") or []
    par_nom = {}
    for sk in doc.get("skins") or []:
        for j in sk.get("joints") or []:
            if 0 <= j < len(nodes) and nodes[j].get("name"):
                par_nom.setdefault(nodes[j]["name"], j)
    if not all(i in par_nom for i in IDS):
        return None
    out = {}
    for i in IDS + IDS_POITRINE:
        if i in par_nom:
            j = par_nom[i]
            m = mondes.get(j) or ME._mat_mul(ME._monde_des_ancetres(doc, j), ME._mat_locale(nodes[j]))
            out[i] = [round(m[12], 6), round(m[13], 6), round(m[14], 6)]
    return out


def centre_tronc(modele: dict) -> float | None:
    """La profondeur (z) du milieu du tronc : milieu des z des sommets entre 45 et 85 % de la hauteur."""
    lo, hi = modele["boite"]["min"], modele["boite"]["max"]
    h = hi[1] - lo[1]
    a, b = lo[1] + 0.45 * h, lo[1] + 0.85 * h
    zs = [p[2] for inst in modele["instances"] for pr in inst["prims"] for p in pr["positions"] if a <= p[1] <= b]
    return (min(zs) + max(zs)) / 2 if zs else None


def proposition(data: bytes) -> dict:
    """Ce que l'écran Rig montre à l'ouverture : le gabarit, et les articulations de départ (le squelette déjà posé
    par ce module s'il existe, sinon le gabarit)."""
    m = lire_modele(data)
    gab = gabarit(m["boite"], centre_tronc(m))
    exist = _squelette_existant(m["doc"], m["mondes"])
    joints = {i: exist[i] for i in IDS} if exist else gab["joints"]
    poitrine = {i: exist[i] for i in IDS_POITRINE if exist and i in exist} or gab["poitrine"]
    return {
        "source": "rig" if exist else "gabarit", "ordre": IDS, "ordre_poitrine": IDS_POITRINE,
        "parents": PARENTS, "joints": joints, "poitrine": poitrine,
        "avec_poitrine": bool(exist and all(i in exist for i in IDS_POITRINE)),
        "gabarit": gab, "boite": {k: [round(v, 6) for v in m["boite"][k]] for k in ("min", "max")},
        "hauteur": gab["hauteur"], "axe_x": gab["axe_x"], "pose": gab["pose"], "sommets": m["sommets"],
    }


# ── validation des articulations reçues ──────────────────────────────────────────────────────────────────────────────

def valider(joints, avec_poitrine: bool, boite: dict) -> dict:
    """{id: (x, y, z)} pour les 22 (ou 24) os, ou ValueError en français. Une articulation à plus d'une demi-taille
    du modèle hors de sa boîte est un clic perdu, pas une intention : refusée."""
    if not isinstance(joints, dict):
        raise ValueError("joints : un objet {os: [x, y, z]} est attendu")
    lo, hi = boite["min"], boite["max"]
    marge = 0.5 * max(hi[c] - lo[c] for c in range(3))
    out = {}
    for i in ordre(avec_poitrine):
        v = joints.get(i)
        if not isinstance(v, (list, tuple)) or len(v) != 3 or not all(
                isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in v):
            raise ValueError(f"articulation « {i} » : trois nombres finis [x, y, z] sont attendus")
        if any(v[c] < lo[c] - marge or v[c] > hi[c] + marge for c in range(3)):
            raise ValueError(f"articulation « {i} » hors du modèle")
        out[i] = (float(v[0]), float(v[1]), float(v[2]))
    inconnus = sorted(k for k in joints if k not in PARENTS)
    if inconnus:
        raise ValueError(f"os inconnu(s) : {', '.join(inconnus[:5])}")
    return out


# ── les poids ────────────────────────────────────────────────────────────────────────────────────────────────────────

def segments(joints: dict, hauteur: float) -> list[tuple]:
    """Un segment par os, dans l'ordre de `joints` : (ax, ay, az, dx, dy, dz, longueur²)."""
    enfants = {}
    for i in joints:
        p = PARENTS.get(i)
        if p in joints:
            enfants.setdefault(p, []).append(i)
    out = []
    for i, a in joints.items():
        e = PRINCIPAL.get(i) if PRINCIPAL.get(i) in joints else (enfants.get(i) or [None])[0]
        if e is not None:
            b = joints[e]
        else:   # une feuille : prolongée dans la direction de son os parent
            p = joints.get(PARENTS.get(i))
            if i == "head":
                b = (a[0], a[1] + 0.11 * hauteur, a[2])
            elif i.startswith("breast"):
                b = (a[0], a[1], a[2] + 0.04 * hauteur)
            elif p is not None:
                d = (a[0] - p[0], a[1] - p[1], a[2] - p[2])
                b = (a[0] + 0.6 * d[0], a[1] + 0.6 * d[1], a[2] + 0.6 * d[2])
            else:
                b = a
        d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        out.append((a[0], a[1], a[2], d[0], d[1], d[2], d[0] * d[0] + d[1] * d[1] + d[2] * d[2]))
    return out


def poids(positions, joints: dict, hauteur: float, axe_x: float) -> list[tuple]:
    """[(j0, j1, j2, j3), (w0, w1, w2, w3)] par sommet — indices dans l'ordre de `joints`, poids normalisés."""
    segs = segments(joints, hauteur)
    cotes = [cote(i) for i in joints]
    marge = 0.01 * hauteur
    eps = 1e-6 * hauteur
    out, cache = [], {}
    for p in positions:
        cle = (p[0], p[1], p[2])
        r = cache.get(cle)
        if r is None:
            px, py, pz = cle
            sens = "l" if px > axe_x + marge else "r" if px < axe_x - marge else None
            ds = []
            for k, (ax, ay, az, dx, dy, dz, l2) in enumerate(segs):
                c = cotes[k]
                if sens and c and c != sens:
                    continue
                vx, vy, vz = px - ax, py - ay, pz - az
                t = (vx * dx + vy * dy + vz * dz) / l2 if l2 > 1e-20 else 0.0
                t = 0.0 if t < 0 else 1.0 if t > 1 else t
                ex, ey, ez = vx - t * dx, vy - t * dy, vz - t * dz
                ds.append((math.sqrt(ex * ex + ey * ey + ez * ez), k))
            ds.sort()
            seuil = 1.6 * ds[0][0] + marge
            garde = [(d, k) for d, k in ds[:4] if d <= seuil]
            w = [1.0 / max(d, eps) ** 6 for d, _k in garde]
            s = sum(w)
            idx = [k for _d, k in garde] + [0] * (4 - len(garde))
            ws = [x / s for x in w] + [0.0] * (4 - len(garde))
            r = (tuple(idx), tuple(ws))
            cache[cle] = r
        out.append(r)
    return out


# ── l'écriture ───────────────────────────────────────────────────────────────────────────────────────────────────────

class _Tampon:
    def __init__(self, doc: dict, binc: bytes):
        self.doc, self.b = doc, bytearray(binc)

    def ajouter(self, fmt: str, valeurs, count: int, type_: str, ct: int, *, cible=None, minmax=None) -> int:
        self.b += b"\x00" * (-len(self.b) % 4)
        debut = len(self.b)
        self.b += struct.pack(f"<{len(valeurs)}{fmt}", *valeurs)
        vue = {"buffer": 0, "byteOffset": debut, "byteLength": len(self.b) - debut}
        if cible:
            vue["target"] = cible
        self.doc.setdefault("bufferViews", []).append(vue)
        acc = {"bufferView": len(self.doc["bufferViews"]) - 1, "componentType": ct, "count": count, "type": type_}
        if minmax:
            acc["min"], acc["max"] = minmax
        self.doc.setdefault("accessors", []).append(acc)
        return len(self.doc["accessors"]) - 1


def _ecrire(modele: dict, joints: dict) -> tuple[bytes, dict]:
    """Le GLB skinné : squelette, maillages cuits, poids. Rend (octets, compte rendu)."""
    doc = copy.deepcopy(modele["doc"])
    tp = _Tampon(doc, modele["binc"])
    ids = list(joints)
    pos_os = [joints[i] for i in ids]
    gab = gabarit(modele["boite"])
    hauteur = gab["hauteur"]
    paires = [(joints[i], joints[paire(i)]) for i in ids if cote(i) == "l" and paire(i) in joints]
    axe_x = sum((a[0] + b[0]) / 2 for a, b in paires) / len(paires) if paires else gab["axe_x"]

    # les os : nœuds 0..n-1, translations relatives au parent, rotations nulles
    nodes = []
    for i, p in zip(ids, pos_os):
        par = PARENTS.get(i)
        q = joints[par] if par in joints else (0.0, 0.0, 0.0)
        nodes.append({"name": i, "translation": [p[0] - q[0], p[1] - q[1], p[2] - q[2]]})
    for k, i in enumerate(ids):
        par = PARENTS.get(i)
        if par in joints:
            nodes[ids.index(par)].setdefault("children", []).append(k)
    ibm = []
    for p in pos_os:
        ibm += [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -p[0], -p[1], -p[2], 1]
    a_ibm = tp.ajouter("f", ibm, len(ids), "MAT4", 5126)

    meshes, scene_nodes = [], [0]
    retirees = {"cibles_morph": 0}
    sommets = 0
    vus = {}
    ancien_nodes = modele["doc"]["nodes"]
    for inst in modele["instances"]:
        mesh = copy.deepcopy(modele["doc"]["meshes"][inst["mesh"]])
        mesh["primitives"] = []
        for pr in inst["prims"]:
            prim = copy.deepcopy(pr["prim"])
            att = prim.setdefault("attributes", {})
            for k in [k for k in att if k.startswith(("JOINTS_", "WEIGHTS_"))]:
                del att[k]
            cle = (inst["noeud"], pr["cle"])
            if cle not in vus:
                pos, nrm = pr["positions"], pr["normales"]
                n = len(pos)
                r = {}
                if pr["cuit"]:
                    lo = [min(p[c] for p in pos) for c in range(3)]
                    hi = [max(p[c] for p in pos) for c in range(3)]
                    r["POSITION"] = tp.ajouter("f", [c for p in pos for c in p], n, "VEC3", 5126, cible=34962,
                                               minmax=(lo, hi))
                    if nrm:
                        r["NORMAL"] = tp.ajouter("f", [c for v in nrm for c in v], n, "VEC3", 5126, cible=34962)
                pw = poids(pos, joints, hauteur, axe_x)
                r["JOINTS_0"] = tp.ajouter("H", [j for jv, _w in pw for j in jv], n, "VEC4", 5123, cible=34962)
                r["WEIGHTS_0"] = tp.ajouter("f", [w for _j, wv in pw for w in wv], n, "VEC4", 5126, cible=34962)
                vus[cle] = r
                sommets += n
            att.update(vus[cle])
            if pr["cuit"]:
                att.pop("TANGENT", None)          # une tangente non cuite mentirait ; three.js s'en passe
                if prim.get("targets"):
                    retirees["cibles_morph"] += len(prim["targets"])
                    prim.pop("targets", None)
            mesh["primitives"].append(prim)
        if not any(p.get("targets") for p in mesh["primitives"]):
            mesh.pop("weights", None)
            if isinstance(mesh.get("extras"), dict):
                mesh["extras"].pop("targetNames", None)
        meshes.append(mesh)
        nd = {"name": ancien_nodes[inst["noeud"]].get("name") or mesh.get("name") or f"peau_{len(meshes)}",
              "mesh": len(meshes) - 1, "skin": 0}
        nodes.append(nd)
        scene_nodes.append(len(nodes) - 1)

    retirees["os"] = len({j for sk in modele["doc"].get("skins") or [] for j in sk.get("joints") or []})
    retirees["animations"] = len(modele["doc"].get("animations") or [])
    doc["nodes"] = nodes
    doc["meshes"] = meshes
    doc["skins"] = [{"name": "rig_local", "joints": list(range(len(ids))), "skeleton": 0,
                     "inverseBindMatrices": a_ibm}]
    doc["scenes"] = [{"name": (modele["doc"].get("scenes") or [{}])[0].get("name") or "Scene", "nodes": scene_nodes}]
    doc["scene"] = 0
    doc.pop("animations", None)
    doc["buffers"] = [{"byteLength": len(tp.b)}]
    doc.setdefault("asset", {"version": "2.0"})
    doc["asset"]["generator"] = "DeepotusVideo rig_local (t395)"
    rapport = {"os": len(ids), "sommets": sommets, "methode": METHODE, "axe_x": round(axe_x, 6),
               "poitrine": all(i in joints for i in IDS_POITRINE), "retire": retirees}
    return ME.ecrire_glb(doc, bytes(tp.b)), rapport


def rigger(data: bytes, joints, *, avec_poitrine: bool = False) -> tuple[bytes, dict]:
    """Le GLB riggé (octets) et son compte rendu, sans rien écrire sur le disque. ValueError en français."""
    m = lire_modele(data)
    j = valider(joints, avec_poitrine, m["boite"])
    return _ecrire(m, j)


def appliquer(job: str, version: int, data: bytes, joints, *, avec_poitrine: bool = False,
              fichier: str | None = None) -> dict:
    """Rigge `data` (la version `version` de `job`) et l'écrit comme version de plus. Rend la fiche du registre."""
    sortie, rapport = rigger(data, joints, avec_poitrine=avec_poitrine)
    return ME.ecrire_version(job, sortie, operation="rig_local", detail={
        "outil": "studio3d", "depuis": {"version": int(version), "fichier": fichier or (
            "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb")}, **rapport})


__all__ = ["OS", "POITRINE", "IDS", "IDS_POITRINE", "PARENTS", "MAX_SOMMETS", "METHODE", "cote", "paire", "ordre",
           "lire_modele", "gabarit", "proposition", "valider", "segments", "poids", "rigger", "appliquer"]
