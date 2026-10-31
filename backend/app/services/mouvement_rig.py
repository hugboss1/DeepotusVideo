# -*- coding: utf-8 -*-
"""t343 (29/10/2026, lot Scenario B8) — un MOUVEMENT appliqué au rig d'un modèle de l'Établi.

Chez Scenario, Uthana et Cartwheel captent un mouvement depuis une vidéo puis le posent sur le rig. Ici, la partie
SOLIDE est locale et gratuite, en Python pur (numpy n'est pas dans le python embarqué) :
  - LIRE un mouvement : un fichier BVH (mocap, Rokoko, Cascadeur, Uthana…) ou un GLB animé (Uthana, Mixamo converti,
    les clips Meshy du job, ou un clip de la version elle-même pour le retimer) ;
  - le RECIBLER (retargeting) sur le squelette de la version : correspondance des os par leur rôle (bassin, colonne,
    bras, jambes…, préfixes mixamorig:, côtés Left/L/_l/.L), puis rotations transférées EN MONDE — la variation de
    l'os source depuis sa pose de repos est appliquée à l'os cible, après avoir aligné la direction de repos de l'os
    cible sur celle de la source (une source en T et un rig en A donnent un bras levé juste) ; le déplacement du
    bassin est mis à l'échelle des hauteurs de bassin ;
  - le RETIMER : rognage (début, fin), vitesse, boucle (les dernières images fondues vers la première), sur place ;
  - l'ÉCRIRE comme clip NOMMÉ d'une version de plus (un clip du même nom est remplacé) ;
  - l'export GODOT avec des hitboxes attachées aux os : BoneAttachment3D + Area3D + CollisionShape3D (capsule le long
    de l'os, ou boîte) par os choisi, un petit script relie les attaches au Skeleton3D importé du GLB.
FBX n'est PAS lu (aucun lecteur FBX dans le python embarqué) : le refus le dit, passer par Blender en GLB ou BVH.
La voie vidéo → mouvement payante (Uthana) vit dans `uthana.py` ; elle rend un GLB que ce module lit comme les autres.
"""
from __future__ import annotations

import io
import json
import math
import re
import zipfile
from pathlib import Path

from app.services import mesh_edit as ME

EXTENSIONS = (".bvh", ".glb")
MAX_OCTETS = 40 * 1024 * 1024          # un mouvement importé : 40 Mo au plus
MAX_IMAGES = 20_000                    # images d'un mouvement (≈ 11 min à 30 i/s)
VITESSE_MIN, VITESSE_MAX = 0.1, 4.0
FPS_MIN, FPS_MAX = 10, 60
FONDU_MAX = 2.0
NOM_CLIP_MAX = 48
FORMES = ("capsule", "boite")
ROLES_HITBOX = ("hurt", "hit")
COUCHES = {"hurt": 1, "hit": 2}         # collision_layer Godot : 1 = reçoit les coups, 2 = les porte
MAX_HITBOXES = 64

# ───────────────────────────── quaternions (x, y, z, w), comme glTF ─────────────────────────────

Q_ID = (0.0, 0.0, 0.0, 1.0)


def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def q_norm(q):
    n = math.sqrt(sum(c * c for c in q))
    if n < 1e-12:
        return Q_ID
    return tuple(c / n for c in q)


def q_inv(q):
    x, y, z, w = q_norm(q)
    return (-x, -y, -z, w)


def q_rot(q, v):
    """La rotation de q appliquée au vecteur v."""
    x, y, z, w = q
    vx, vy, vz = v
    # t = 2 * (q.xyz × v) ; v' = v + w t + q.xyz × t
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def q_axe(axe: str, degres: float):
    a = math.radians(degres) / 2
    s, c = math.sin(a), math.cos(a)
    return {"X": (s, 0.0, 0.0, c), "Y": (0.0, s, 0.0, c), "Z": (0.0, 0.0, s, c)}[axe]


def q_slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-c for c in b), -d
    if d > 0.9995:
        return q_norm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(max(-1.0, min(1.0, d)))
    s = math.sin(th)
    wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
    return tuple(wa * x + wb * y for x, y in zip(a, b))


def q_entre(u, v):
    """La plus petite rotation qui amène la direction u sur v (unitaires ou non)."""
    nu, nv = _norme(u), _norme(v)
    if nu < 1e-9 or nv < 1e-9:
        return Q_ID
    u = tuple(c / nu for c in u)
    v = tuple(c / nv for c in v)
    d = sum(a * b for a, b in zip(u, v))
    if d > 1 - 1e-9:
        return Q_ID
    if d < -1 + 1e-9:                     # demi-tour : un axe perpendiculaire quelconque
        ax = (0.0, -u[2], u[1]) if abs(u[0]) < 0.9 else (-u[2], 0.0, u[0])
        n = _norme(ax)
        return (ax[0] / n, ax[1] / n, ax[2] / n, 0.0)
    cx = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return q_norm((cx[0], cx[1], cx[2], 1 + d))


def q_de_matrice(m):
    """Quaternion d'une matrice 3×3 de rotation (lignes)."""
    (m00, m01, m02), (m10, m11, m12), (m20, m21, m22) = m
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return q_norm(((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s))
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        return q_norm((0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s))
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        return q_norm(((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s))
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2
    return q_norm(((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s))


def _norme(v):
    return math.sqrt(sum(c * c for c in v))


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# ───────────────────────────── le modèle commun d'un mouvement ─────────────────────────────
# {"os": [{"nom", "parent": int | None, "t": vec, "r": quat, "base": (quat, échelle, vec) | None, "noeud": int}],
#  "fps": float, "n": int, "rot": [liste de quats | None par os], "trans": [liste de vecs | None par os]}
# Les os sont rangés parents d'abord. `base` est le repère CONSTANT au-dessus d'une racine (l'armature d'un export
# Blender ou Mixamo, souvent tournée de -90° en X et mise à l'échelle 0,01) : il compte pour le passage en monde.


def _ranger(os_: list[dict]) -> list[int]:
    """Ordre parents d'abord (un cycle n'empêche pas de finir)."""
    vus, ordre = set(), []

    def visiter(i, pile=()):
        if i in vus or i in pile:
            return
        p = os_[i]["parent"]
        if p is not None:
            visiter(p, pile + (i,))
        vus.add(i)
        ordre.append(i)
    for i in range(len(os_)):
        visiter(i)
    return ordre


def monde(squ: list[dict], rots, trans):
    """Rotations et positions MONDE de chaque os pour une pose (listes locales par os, None = repos)."""
    n = len(squ)
    R = [Q_ID] * n
    P = [(0.0, 0.0, 0.0)] * n
    S = [1.0] * n
    for i in _ranger(squ):
        o = squ[i]
        r = rots[i] if rots is not None and rots[i] is not None else o["r"]
        t = trans[i] if trans is not None and trans[i] is not None else o["t"]
        p = o["parent"]
        if p is None:
            br, bs, bt = o.get("base") or (Q_ID, 1.0, (0.0, 0.0, 0.0))
            R[i] = q_norm(q_mul(br, r))
            P[i] = _add(bt, _mul(q_rot(br, t), bs))
            S[i] = bs
        else:
            R[i] = q_norm(q_mul(R[p], r))
            P[i] = _add(P[p], _mul(q_rot(R[p], t), S[p]))
            S[i] = S[p]
    return R, P, S


# ───────────────────────────── lecture : BVH ─────────────────────────────

_CANAUX = {"Xposition", "Yposition", "Zposition", "Xrotation", "Yrotation", "Zrotation"}


def lire_bvh(texte: str) -> dict:
    """Un fichier BVH → le modèle commun. Rotations d'Euler en degrés, composées dans l'ordre des canaux
    (R = R1 · R2 · R3) ; repos = identité, décalages = OFFSET ; la racine porte la position."""
    jetons = texte.split()
    if not jetons or jetons[0].upper() != "HIERARCHY":
        raise ValueError("BVH : l'en-tête HIERARCHY manque — ce fichier n'est pas un BVH")
    os_: list[dict] = []
    canaux: list[tuple[int, list[str]]] = []
    pile: list[int | None] = []
    k = 1
    courant: int | None = None
    try:
        while k < len(jetons):
            j = jetons[k]
            ju = j.upper()
            if ju in ("ROOT", "JOINT"):
                nom = jetons[k + 1]
                parent = pile[-1] if pile else None
                os_.append({"nom": nom, "parent": parent, "t": (0.0, 0.0, 0.0), "r": Q_ID, "base": None,
                            "noeud": len(os_)})
                courant = len(os_) - 1
                k += 2
            elif ju == "END":                   # End Site { OFFSET … } : un bout d'os sans canal, ignoré
                k += 2
                if jetons[k] != "{":
                    raise ValueError("BVH : « End Site » sans accolade")
                prof = 0
                while True:
                    if jetons[k] == "{":
                        prof += 1
                    elif jetons[k] == "}":
                        prof -= 1
                        if prof == 0:
                            k += 1
                            break
                    k += 1
            elif j == "{":
                pile.append(courant)
                k += 1
            elif j == "}":
                pile.pop()
                k += 1
            elif ju == "OFFSET":
                os_[courant]["t"] = (float(jetons[k + 1]), float(jetons[k + 2]), float(jetons[k + 3]))
                k += 4
            elif ju == "CHANNELS":
                nb = int(jetons[k + 1])
                noms = jetons[k + 2:k + 2 + nb]
                if any(c not in _CANAUX for c in noms):
                    raise ValueError(f"BVH : canal inconnu dans {noms}")
                canaux.append((courant, noms))
                k += 2 + nb
            elif ju == "MOTION":
                k += 1
                break
            else:
                raise ValueError(f"BVH : mot inattendu « {j[:20]} »")
        if not os_:
            raise ValueError("BVH : aucun os")
        if jetons[k].upper() != "FRAMES:":
            raise ValueError("BVH : « Frames: » attendu après MOTION")
        n = int(jetons[k + 1])
        if jetons[k + 2].upper() != "FRAME" or jetons[k + 3].upper() != "TIME:":
            raise ValueError("BVH : « Frame Time: » attendu")
        dt = float(jetons[k + 4])
        valeurs = [float(v) for v in jetons[k + 5:]]
    except (IndexError, TypeError) as e:
        raise ValueError(f"BVH tronqué ou mal formé ({type(e).__name__})") from None
    if not 0 < n <= MAX_IMAGES:
        raise ValueError(f"BVH : {n} images (1 à {MAX_IMAGES} attendues)")
    if not 0 < dt < 1:
        raise ValueError("BVH : durée d'image hors bornes (0 à 1 s)")
    largeur = sum(len(c) for _, c in canaux)
    if len(valeurs) < n * largeur:
        raise ValueError(f"BVH : {len(valeurs)} valeurs pour {n} images de {largeur} canaux")
    rot = [None] * len(os_)
    trans = [None] * len(os_)
    for i, noms in canaux:
        if any(c.endswith("rotation") for c in noms):
            rot[i] = []
        if any(c.endswith("position") for c in noms) and os_[i]["parent"] is None:
            trans[i] = []
    for f in range(n):
        base = f * largeur
        for i, noms in canaux:
            r = Q_ID
            pos = list(os_[i]["t"])
            for c in noms:
                v = valeurs[base]
                base += 1
                if c.endswith("rotation"):
                    r = q_mul(r, q_axe(c[0], v))
                else:
                    pos["XYZ".index(c[0])] = v
            if rot[i] is not None:
                rot[i].append(q_norm(r))
            if trans[i] is not None:
                trans[i].append(tuple(pos))
    fps = round(1.0 / dt, 3)
    if abs(fps - round(fps)) < 0.01:              # « Frame Time: 0.033333 » : 30 i/s, pas 30,0003
        fps = float(round(fps))
    return {"os": os_, "fps": fps, "n": n, "rot": rot, "trans": trans, "format": "bvh"}


# ───────────────────────────── lecture : GLB ─────────────────────────────

def _trs(node: dict):
    """(t, r, s uniforme) d'un nœud glTF ; une matrice est décomposée."""
    m = node.get("matrix")
    if m and len(m) == 16:
        cols = [(m[0], m[1], m[2]), (m[4], m[5], m[6]), (m[8], m[9], m[10])]
        ech = [_norme(c) or 1.0 for c in cols]
        n = [tuple(x / e for x in c) for c, e in zip(cols, ech)]
        lignes = ((n[0][0], n[1][0], n[2][0]), (n[0][1], n[1][1], n[2][1]), (n[0][2], n[1][2], n[2][2]))
        return (m[12], m[13], m[14]), q_de_matrice(lignes), sum(ech) / 3
    t = tuple(float(c) for c in (node.get("translation") or (0, 0, 0)))
    r = q_norm(tuple(float(c) for c in (node.get("rotation") or Q_ID)))
    s = node.get("scale") or (1, 1, 1)
    return t, r, (float(s[0]) + float(s[1]) + float(s[2])) / 3


def squelette_glb(doc: dict) -> list[dict]:
    """Les os d'un document glTF (joints des skins, sinon les nœuds animés), parents d'abord, avec leur repos et le
    repère constant au-dessus des racines."""
    nodes = doc.get("nodes") or []
    joints: list[int] = []
    for s in doc.get("skins") or []:
        for j in s.get("joints") or []:
            if j not in joints:
                joints.append(j)
    if not joints:
        for a in doc.get("animations") or []:
            for c in a.get("channels") or []:
                n = (c.get("target") or {}).get("node")
                if isinstance(n, int) and n not in joints:
                    joints.append(n)
    parents = ME._parents(nodes)
    jset = set(joints)

    def ancetre_joint(i):
        p = parents.get(i)
        while p is not None and p not in jset:
            p = parents.get(p)
        return p

    def base_de(i):
        """Le repère monde (r, s, t) des nœuds NON-os au-dessus d'une racine."""
        chaine = []
        p = parents.get(i)
        while p is not None:
            chaine.append(p)
            p = parents.get(p)
        r, s, t = Q_ID, 1.0, (0.0, 0.0, 0.0)
        for k in reversed(chaine):
            nt, nr, ns = _trs(nodes[k])
            t = _add(t, _mul(q_rot(r, nt), s))
            r = q_norm(q_mul(r, nr))
            s = s * ns
        return r, s, t

    index = {n: k for k, n in enumerate(joints)}
    os_ = []
    for n in joints:
        t, r, _s = _trs(nodes[n] if 0 <= n < len(nodes) else {})
        pa = ancetre_joint(n)
        os_.append({"nom": (nodes[n].get("name") if 0 <= n < len(nodes) else None) or f"os_{n}",
                    "parent": index[pa] if pa is not None else None, "t": t, "r": r,
                    "base": None if pa is not None else base_de(n), "noeud": n})
    ordre = _ranger(os_)
    if ordre != list(range(len(os_))):            # ranger parents d'abord, en renumérotant
        nouveau = {old: k for k, old in enumerate(ordre)}
        os_ = [dict(os_[old], parent=(nouveau[os_[old]["parent"]] if os_[old]["parent"] is not None else None))
               for old in ordre]
    return os_


def _echantillon(temps, valeurs, t, interp, quat):
    if t <= temps[0]:
        return valeurs[0]
    if t >= temps[-1]:
        return valeurs[-1]
    lo, hi = 0, len(temps) - 1
    while hi - lo > 1:
        mi = (lo + hi) // 2
        if temps[mi] <= t:
            lo = mi
        else:
            hi = mi
    if interp == "STEP":
        return valeurs[lo]
    a = (t - temps[lo]) / ((temps[hi] - temps[lo]) or 1)
    return q_slerp(valeurs[lo], valeurs[hi], a) if quat else _lerp(valeurs[lo], valeurs[hi], a)


def clips_glb(data: bytes) -> list[str]:
    doc, _ = ME.lire_glb(data)
    return [a.get("name") or f"clip_{i}" for i, a in enumerate(doc.get("animations") or [])]


def lire_glb_mouvement(data: bytes, clip: str | None = None, fps: float | None = None) -> dict:
    """Un clip d'un GLB animé → le modèle commun, échantillonné à cadence fixe (celle des clés, bornée 10–60 i/s)."""
    doc, binc = ME.lire_glb(data)
    anims = doc.get("animations") or []
    if not anims:
        raise ValueError("GLB : aucun clip d'animation dans ce fichier")
    noms = [a.get("name") or f"clip_{i}" for i, a in enumerate(anims)]
    if clip is None or clip == "":
        ai = 0
    elif clip in noms:
        ai = noms.index(clip)
    else:
        raise ValueError(f"GLB : clip « {str(clip)[:40]} » introuvable")
    anim = anims[ai]
    os_ = squelette_glb(doc)
    if not os_:
        raise ValueError("GLB : aucun os (ni skin ni nœud animé)")
    par_noeud = {o["noeud"]: k for k, o in enumerate(os_)}
    pistes = {}
    t_max, pas = 0.0, []
    for c in anim.get("channels") or []:
        tg = c.get("target") or {}
        k = par_noeud.get(tg.get("node"))
        chemin = tg.get("path")
        if k is None or chemin not in ("rotation", "translation"):
            continue
        smp = (anim.get("samplers") or [])[c["sampler"]]
        temps = [v[0] for v in ME.lire_accesseur(doc, binc, smp["input"], quoi="un clip")]
        vals = ME.lire_accesseur(doc, binc, smp["output"], quoi="un clip")
        interp = smp.get("interpolation", "LINEAR")
        if interp == "CUBICSPLINE":                  # (entrée, valeur, sortie) par clé : la valeur seule
            vals = vals[1::3]
        if not temps or len(vals) < len(temps):
            continue
        if chemin == "rotation":
            vals = [q_norm(tuple(float(x) for x in v)) for v in vals]
        else:
            vals = [tuple(float(x) for x in v) for v in vals]
        pistes[(k, chemin)] = (temps, vals[:len(temps)], interp)
        t_max = max(t_max, temps[-1])
        pas.extend(b - a for a, b in zip(temps, temps[1:]) if b > a)
    if not pistes:
        raise ValueError("GLB : le clip n'anime aucun os")
    if fps is None:
        pas.sort()
        med = pas[len(pas) // 2] if pas else 1 / 30
        fps = round(1 / med) if med > 0 else 30
    fps = float(min(FPS_MAX, max(FPS_MIN, fps)))
    n = int(math.floor(t_max * fps + 1e-6)) + 1
    if n > MAX_IMAGES:
        raise ValueError(f"GLB : clip trop long ({n} images, {MAX_IMAGES} au plus)")
    rot = [None] * len(os_)
    trans = [None] * len(os_)
    for (k, chemin), (temps, vals, interp) in pistes.items():
        serie = [_echantillon(temps, vals, f / fps, interp, chemin == "rotation") for f in range(n)]
        if chemin == "rotation":
            rot[k] = serie
        else:
            trans[k] = serie
    return {"os": os_, "fps": fps, "n": n, "rot": rot, "trans": trans, "format": "glb", "clip": noms[ai]}


def lire_fichier(nom: str, data: bytes, clip: str | None = None) -> dict:
    ext = Path(nom).suffix.lower()
    if ext == ".fbx":
        raise ValueError("FBX non lu ici (aucun lecteur FBX embarqué) : exporte-le en GLB ou en BVH depuis Blender")
    if ext == ".bvh":
        try:
            texte = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            texte = data.decode("latin-1")
        return lire_bvh(texte)
    if ext == ".glb":
        return lire_glb_mouvement(data, clip)
    raise ValueError("format de mouvement non pris en charge : .bvh ou .glb")


def resume(m: dict) -> dict:
    return {"os": len(m["os"]), "images": m["n"], "fps": m["fps"], "secondes": round((m["n"] - 1) / m["fps"], 3),
            "format": m.get("format"), "clip": m.get("clip")}


# ───────────────────────────── la correspondance des os ─────────────────────────────

_PARASITES = {"mixamorig", "bip01", "bip001", "bip", "def", "org", "mch", "jnt", "joint", "bone", "b", "j", "c",
              "armature", "ctrl", "bn"}
_ALIAS = {
    "bassin": {"hips", "hip", "pelvis"},
    "cou": {"neck", "neck0", "neck1", "neck01", "neck2", "neck02"},
    "tete": {"head"},
    "epaule": {"shoulder", "clavicle", "collar", "collarbone"},
    "bras": {"arm", "upperarm", "uparm", "humerus"},
    "avantbras": {"forearm", "lowerarm", "lowarm", "elbow"},
    "main": {"hand", "wrist"},
    "cuisse": {"upleg", "thigh", "upperleg", "femur", "hip"},
    "jambe": {"leg", "shin", "calf", "lowerleg", "lowleg", "knee"},
    "pied": {"foot", "ankle"},
    "orteil": {"toe", "toebase", "toes", "ball", "toe0", "toe01"},
}
_COLONNE = ("spine", "chest", "upperchest", "lowerback", "back", "torso", "abdomen")


def decouper(nom: str) -> tuple[str | None, str]:
    """(côté « g » / « d » / None, base normalisée) d'un nom d'os."""
    s = re.sub(r"^.*[:|]", "", str(nom))
    s = re.sub(r"^([LR])([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    cote, reste = None, []
    for t in (x for x in re.split(r"[^A-Za-z0-9]+", s.lower()) if x):
        if t in ("left", "l", "lft"):
            cote = "g"
        elif t in ("right", "r", "rgt"):
            cote = "d"
        elif t not in _PARASITES:
            reste.append(t)
    base = "".join(reste)
    for pre, c in (("left", "g"), ("right", "d")):
        if base.startswith(pre) and len(base) > len(pre):
            cote, base = c, base[len(pre):]
    return cote, base


def role(nom: str) -> str | None:
    """Le rôle canonique d'un os (« bras_g », « bassin », « colonne »…) ou None."""
    cote, base = decouper(nom)
    if cote is None and base in ("hip",):
        return "bassin"
    for r, alias in _ALIAS.items():
        if base in alias:
            if r in ("bassin", "cou", "tete"):
                return r if cote is None else None
            return f"{r}_{cote}" if cote else None
    if cote is None and any(base.startswith(c) for c in _COLONNE):
        return "colonne"
    return None


def _profondeur(squ, i):
    d = 0
    while squ[i]["parent"] is not None and d < 512:
        i = squ[i]["parent"]
        d += 1
    return d


def correspondance(src: list[dict], cible: list[dict]) -> dict[int, int]:
    """{os cible → os source}. Par rôle ; la colonne (et le cou) par chaîne PROPORTIONNELLE (3 vertèbres d'un côté,
    2 de l'autre) ; puis les noms identiques une fois normalisés (doigts d'une même convention)."""
    def par_role(squ):
        out: dict[str, list[int]] = {}
        for i, o in enumerate(squ):
            r = role(o["nom"])
            if r:
                out.setdefault(r, []).append(i)
        for r in out:
            out[r].sort(key=lambda i: _profondeur(squ, i))
        # « Leg » est ambigu : le BVH de Meshy Text to Motion nomme la cuisse « LeftLeg » et le tibia « LeftShin »
        # (relevé réel du 31/10). Deux « jambes » sans « cuisse » d'un côté : la plus haute est la cuisse.
        for c in ("g", "d"):
            jambes = out.get(f"jambe_{c}") or []
            if f"cuisse_{c}" not in out and len(jambes) >= 2:
                out[f"cuisse_{c}"], out[f"jambe_{c}"] = jambes[:1], jambes[1:]
        return out
    rs, rc = par_role(src), par_role(cible)
    m: dict[int, int] = {}
    for r, lc in rc.items():
        ls = rs.get(r)
        if not ls:
            continue
        if r in ("colonne", "cou"):
            for k, i in enumerate(lc):
                j = ls[round(k * (len(ls) - 1) / (len(lc) - 1))] if len(lc) > 1 else ls[0]
                m[i] = j
        else:
            m[lc[0]] = ls[0]
    norm_src = {}
    for j, o in enumerate(src):
        norm_src.setdefault("".join(x or "" for x in decouper(o["nom"])), j)
    for i, o in enumerate(cible):
        if i not in m:
            j = norm_src.get("".join(x or "" for x in decouper(o["nom"])))
            if j is not None:
                m[i] = j
    return m


# ───────────────────────────── le retimage ─────────────────────────────

def valider_retimage(rt: dict | None, duree: float) -> dict:
    rt = dict(rt or {})

    def nombre(cle, defaut):
        v = rt.get(cle, defaut)
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"retimage : « {cle} » attend un nombre")
        return float(v)
    debut = nombre("debut", 0.0) or 0.0
    fin = nombre("fin", None)
    fin = duree if fin is None else fin
    vitesse = nombre("vitesse", 1.0)
    fondu = nombre("fondu", 0.25)
    if not 0 <= debut < duree or not debut < fin <= duree + 1e-6:
        raise ValueError(f"retimage : rognage hors du mouvement (0 à {round(duree, 3)} s, début avant la fin)")
    if not VITESSE_MIN <= vitesse <= VITESSE_MAX:
        raise ValueError(f"retimage : vitesse entre {VITESSE_MIN} et {VITESSE_MAX}")
    if not 0 <= fondu <= FONDU_MAX:
        raise ValueError(f"retimage : fondu de boucle entre 0 et {FONDU_MAX} s")
    fps = rt.get("fps")
    if fps is not None and (isinstance(fps, bool) or not isinstance(fps, (int, float)) or not FPS_MIN <= fps <= FPS_MAX):
        raise ValueError(f"retimage : cadence entre {FPS_MIN} et {FPS_MAX} i/s")
    return {"debut": debut, "fin": min(fin, duree), "vitesse": vitesse, "boucle": rt.get("boucle") is True,
            "fondu": fondu, "en_place": rt.get("en_place") is True, "fps": float(fps) if fps else None}


def _pose(m: dict, t: float):
    """Les rotations et translations locales d'un mouvement au temps t (interpolées entre deux images)."""
    x = t * m["fps"]
    a = max(0, min(m["n"] - 1, int(math.floor(x))))
    b = min(m["n"] - 1, a + 1)
    u = max(0.0, min(1.0, x - a))
    rots = [None if s is None else q_slerp(s[a], s[b], u) for s in m["rot"]]
    trans = [None if s is None else _lerp(s[a], s[b], u) for s in m["trans"]]
    return rots, trans


def _hauteur_bassin(P, i):
    """Hauteur du bassin au-dessus de l'os le plus bas de la pose."""
    bas = min(p[1] for p in P)
    return P[i][1] - bas


# ───────────────────────────── le reciblage ─────────────────────────────

def recibler(source: dict, cible: list[dict], *, retimage: dict | None = None, aligner: bool = True) -> dict:
    """Le mouvement `source` posé sur le squelette `cible` (os rangés parents d'abord, repos = nœuds du GLB).
    Rend {"fps", "temps", "rot": {os cible: [quats]}, "trans": {os cible: [vecs]}, "rapport"}."""
    duree = (source["n"] - 1) / source["fps"]
    if duree <= 0:
        raise ValueError("mouvement trop court : il faut au moins deux images")
    rt = valider_retimage(retimage, duree)
    m = correspondance(source["os"], cible)
    if not m:
        raise ValueError("aucun os en commun : les noms des deux squelettes ne se reconnaissent pas "
                         "(bassin, colonne, bras, jambes…)")
    fps = rt["fps"] or min(FPS_MAX, max(FPS_MIN, source["fps"]))
    duree_sortie = (rt["fin"] - rt["debut"]) / rt["vitesse"]
    n = max(2, int(math.floor(duree_sortie * fps + 1e-6)) + 1)
    if n > MAX_IMAGES:
        raise ValueError(f"clip trop long après retimage ({n} images, {MAX_IMAGES} au plus)")
    temps = [k / fps for k in range(n)]

    # Repos : monde des deux squelettes.
    Rs0, Ps0, _ = monde(source["os"], None, None)
    Rt0, Pt0, _ = monde(cible, None, None)
    inv_Rs0 = [q_inv(q) for q in Rs0]

    enfants_c: dict[int, list[int]] = {}
    for i, o in enumerate(cible):
        if o["parent"] is not None:
            enfants_c.setdefault(o["parent"], []).append(i)
    enfants_s: dict[int, list[int]] = {}
    for j, o in enumerate(source["os"]):
        if o["parent"] is not None:
            enfants_s.setdefault(o["parent"], []).append(j)

    # Alignement des directions de repos (os cible → os source), sur l'enfant correspondant si possible.
    C = {}
    for i, j in m.items():
        if not aligner:
            C[i] = Q_ID
            continue
        ec = enfants_c.get(i) or []
        cm = next((c for c in ec if c in m and m[c] != j), None)
        if cm is not None:
            dt, ds = _sub(Pt0[cm], Pt0[i]), _sub(Ps0[m[cm]], Ps0[j])
        elif ec and enfants_s.get(j):
            dt, ds = _sub(Pt0[ec[0]], Pt0[i]), _sub(Ps0[enfants_s[j][0]], Ps0[j])
        else:
            dt = ds = None
        C[i] = q_entre(dt, ds) if dt and ds and _norme(dt) > 1e-9 and _norme(ds) > 1e-9 else Q_ID

    # L'os qui porte le déplacement : le bassin de la cible s'il est relié, sinon la racine reliée la moins profonde.
    candidats = sorted(m, key=lambda i: (role(cible[i]["nom"]) != "bassin", _profondeur(cible, i)))
    porteur = candidats[0]
    src_porteur = m[porteur]

    rots_out = {i: [] for i in m}
    trans_out: list = []
    pose0 = None
    for k in range(n):
        ts = rt["debut"] + temps[k] * rt["vitesse"]
        rs, tr = _pose(source, ts)
        Rs, Ps, _ = monde(source["os"], rs, tr)
        if pose0 is None:
            pose0 = Ps[src_porteur]
            h_s = _hauteur_bassin(Ps, src_porteur)
            h_c = _hauteur_bassin(Pt0, porteur)
            ratio = h_c / h_s if h_s > 1e-6 and h_c > 1e-6 else 1.0
        Rw = [None] * len(cible)
        Pw = [None] * len(cible)
        Sw = [1.0] * len(cible)
        loc_t = {}
        for i in _ranger(cible):
            o = cible[i]
            if o["parent"] is None:
                pr, ps, pp = o.get("base") or (Q_ID, 1.0, (0.0, 0.0, 0.0))
            else:
                pr, ps, pp = Rw[o["parent"]], Sw[o["parent"]], Pw[o["parent"]]
            if i in m:
                j = m[i]
                delta = q_mul(Rs[j], inv_Rs0[j])
                rw = q_norm(q_mul(q_mul(delta, C[i]), Rt0[i]))
                rl = q_norm(q_mul(q_inv(pr), rw))
                rots_out[i].append(rl)
            else:
                rl = o["r"]
                rw = q_norm(q_mul(pr, rl))
            t_local = o["t"]
            if i == porteur:
                d = _mul(_sub(Ps[src_porteur], pose0), ratio)
                if rt["en_place"]:
                    d = (0.0, d[1], 0.0)
                cible_monde = _add(Pt0[i], d)
                t_local = _mul(q_rot(q_inv(pr), _sub(cible_monde, pp)), 1.0 / (ps or 1.0))
                loc_t[i] = t_local
            Rw[i] = rw
            Pw[i] = _add(pp, _mul(q_rot(pr, t_local), ps))
            Sw[i] = ps
        trans_out.append(loc_t[porteur])

    if rt["boucle"] and n > 2:
        nf = min(n - 1, max(1, int(round(rt["fondu"] * fps))))
        for k in range(n - nf, n):
            w = (k - (n - nf - 1)) / nf                 # 0 → 1 : la dernière image EST la première
            for i in rots_out:
                rots_out[i][k] = q_slerp(rots_out[i][k], rots_out[i][0], w)
            a, b = trans_out[k], trans_out[0]
            trans_out[k] = (a[0], a[1] + (b[1] - a[1]) * w, a[2]) if not rt["en_place"] else _lerp(a, b, w)

    nommes_c = {cible[i]["nom"]: source["os"][j]["nom"] for i, j in m.items()}
    importants = [o["nom"] for i, o in enumerate(cible) if role(o["nom"]) and i not in m]
    return {"fps": fps, "temps": temps, "rot": rots_out, "trans": {porteur: trans_out},
            "rapport": {"relies": len(m), "os_cible": len(cible), "os_source": len(source["os"]),
                        "correspondance": nommes_c, "non_relies": importants, "porteur": cible[porteur]["nom"],
                        "images": n, "fps": fps, "secondes": round(temps[-1], 3), "retimage": rt,
                        "aligner": bool(aligner)}}


# ───────────────────────────── écriture du clip dans le GLB ─────────────────────────────

def nom_clip(nom) -> str:
    s = re.sub(r"[^\w .-]+", "", str(nom or ""), flags=re.UNICODE).strip()[:NOM_CLIP_MAX]
    if not s:
        raise ValueError("nom du clip : des lettres ou des chiffres sont attendus")
    return s


def ecrire_clip(data: bytes, nom: str, cible: list[dict], res: dict) -> bytes:
    """Ajoute (ou remplace, même nom) le clip `nom` au GLB : un échantillonneur LINEAR par os relié. Le tampon
    binaire d'origine est gardé tel quel, le clip est ajouté à sa suite."""
    import struct
    doc, binc = ME.lire_glb(data)
    nom = nom_clip(nom)
    buf = bytearray(binc)
    buf += b"\x00" * (-len(buf) % 4)
    doc.setdefault("buffers", [])
    if not doc["buffers"]:
        doc["buffers"].append({"byteLength": 0})
    if "uri" in doc["buffers"][0]:
        raise ValueError("GLB à tampon externe (uri) : hors périmètre")
    vues, acc = doc.setdefault("bufferViews", []), doc.setdefault("accessors", [])

    def ajouter(valeurs, type_, minmax=False):
        nonlocal buf
        buf += b"\x00" * (-len(buf) % 4)
        debut = len(buf)
        plat = [float(x) for v in valeurs for x in (v if isinstance(v, (tuple, list)) else (v,))]
        buf += struct.pack(f"<{len(plat)}f", *plat)
        vues.append({"buffer": 0, "byteOffset": debut, "byteLength": len(buf) - debut})
        a = {"bufferView": len(vues) - 1, "componentType": 5126, "count": len(valeurs), "type": type_}
        if minmax:
            a["min"], a["max"] = [min(valeurs)], [max(valeurs)]
        acc.append(a)
        return len(acc) - 1

    entree = ajouter(res["temps"], "SCALAR", minmax=True)
    samplers, canaux = [], []
    for i, serie in sorted(res["rot"].items()):
        samplers.append({"input": entree, "output": ajouter(serie, "VEC4"), "interpolation": "LINEAR"})
        canaux.append({"sampler": len(samplers) - 1, "target": {"node": cible[i]["noeud"], "path": "rotation"}})
    for i, serie in sorted(res["trans"].items()):
        samplers.append({"input": entree, "output": ajouter(serie, "VEC3"), "interpolation": "LINEAR"})
        canaux.append({"sampler": len(samplers) - 1, "target": {"node": cible[i]["noeud"], "path": "translation"}})
    anims = [a for a in (doc.get("animations") or []) if a.get("name") != nom]
    anims.append({"name": nom, "samplers": samplers, "channels": canaux})
    doc["animations"] = anims
    buf += b"\x00" * (-len(buf) % 4)
    doc["buffers"][0]["byteLength"] = len(buf)
    return ME.ecrire_glb(doc, bytes(buf))


def appliquer(cible_glb: bytes, source: dict, *, nom: str, retimage: dict | None = None,
              aligner: bool = True) -> tuple[bytes, dict]:
    """Le mouvement source, reciblé et retimé, devient le clip `nom` d'une copie du GLB cible."""
    nom = nom_clip(nom)
    doc, _ = ME.lire_glb(cible_glb)
    if not doc.get("skins"):
        raise ValueError("ce modèle n'a pas de squelette : rigge-le d'abord (3D Studio › Rig Meshy)")
    cible = squelette_glb(doc)
    res = recibler(source, cible, retimage=retimage, aligner=aligner)
    sortie = ecrire_clip(cible_glb, nom, cible, res)
    return sortie, {"clip": nom, **res["rapport"]}


# ───────────────────────────── export Godot : hitboxes sur les os ─────────────────────────────

def nom_os_godot(nom: str) -> str:
    """L'importeur glTF de Godot 4 remplace « : » et « / » dans les noms d'os (mixamorig:Hips → mixamorig_Hips)."""
    return str(nom).replace(":", "_").replace("/", "_")


def _nom_noeud(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)[:60] or "Os"


def _base_vers(d):
    """Une base orthonormée (colonnes X, Y, Z) dont Y suit la direction d."""
    n = _norme(d)
    y = (0.0, 1.0, 0.0) if n < 1e-9 else tuple(c / n for c in d)
    ref = (1.0, 0.0, 0.0) if abs(y[0]) < 0.9 else (0.0, 0.0, 1.0)
    z = (ref[1] * y[2] - ref[2] * y[1], ref[2] * y[0] - ref[0] * y[2], ref[0] * y[1] - ref[1] * y[0])
    nz = _norme(z)
    z = tuple(c / nz for c in z)
    x = (y[1] * z[2] - y[2] * z[1], y[2] * z[0] - y[0] * z[2], y[0] * z[1] - y[1] * z[0])
    return x, y, z


def _f(v) -> str:
    s = f"{float(v):.6g}"
    return "0" if s in ("-0", "0") else s


def valider_hitboxes(choix, noms_os: list[str]) -> list[dict]:
    if not isinstance(choix, list) or not choix:
        raise ValueError("hitboxes : une liste non vide d'os est attendue")
    if len(choix) > MAX_HITBOXES:
        raise ValueError(f"hitboxes : {MAX_HITBOXES} au plus")
    out, vus = [], set()
    for h in choix:
        if not isinstance(h, dict):
            raise ValueError("hitboxes : chaque entrée est un objet {os, forme, rayon, role}")
        os_ = h.get("os")
        if os_ not in noms_os:
            raise ValueError(f"hitboxes : os « {str(os_)[:40]} » absent du squelette")
        if os_ in vus:
            continue
        vus.add(os_)
        forme = h.get("forme", "capsule")
        if forme not in FORMES:
            raise ValueError("hitboxes : forme « capsule » ou « boite »")
        r = h.get("rayon", 0.25)
        if isinstance(r, bool) or not isinstance(r, (int, float)) or not 0.05 <= r <= 1.0:
            raise ValueError("hitboxes : rayon (part de la longueur de l'os) entre 0,05 et 1")
        role_ = h.get("role", "hurt")
        if role_ not in ROLES_HITBOX:
            raise ValueError("hitboxes : rôle « hurt » (reçoit) ou « hit » (frappe)")
        out.append({"os": os_, "forme": forme, "rayon": float(r), "role": role_})
    return out


def scene_godot(glb: bytes, choix: list, *, res_glb: str, res_script: str, nom: str = "Personnage") -> tuple[str, dict]:
    """Le .tscn Godot 4 : le GLB instancié + une BoneAttachment3D → Area3D → CollisionShape3D par os choisi. La forme
    suit l'os jusqu'à son premier enfant (capsule de rayon r × longueur, ou boîte) dans le repère de l'os."""
    doc, _ = ME.lire_glb(glb)
    if not doc.get("skins"):
        raise ValueError("ce modèle n'a pas de squelette : pas de hitbox sur des os")
    squ = squelette_glb(doc)
    noms = [o["nom"] for o in squ]
    hb = valider_hitboxes(choix, noms)
    enfants: dict[int, list[int]] = {}
    for i, o in enumerate(squ):
        if o["parent"] is not None:
            enfants.setdefault(o["parent"], []).append(i)
    subs, noeuds, rapport = [], [], []
    for k, h in enumerate(hb, start=1):
        i = noms.index(h["os"])
        ec = enfants.get(i) or []
        if ec:
            d = max((squ[c]["t"] for c in ec), key=_norme)
        else:                                      # un bout de chaîne : la moitié de la longueur du parent
            p = squ[i]["parent"]
            lp = _norme(squ[i]["t"]) if p is not None else 0.1
            d = (0.0, max(lp * 0.5, 1e-3), 0.0)
        L = max(_norme(d), 1e-3)
        r = h["rayon"] * L
        x, y, z = _base_vers(d)
        o = _mul(d, 0.5)
        transfo = (f"Transform3D({_f(x[0])}, {_f(y[0])}, {_f(z[0])}, {_f(x[1])}, {_f(y[1])}, {_f(z[1])}, "
                   f"{_f(x[2])}, {_f(y[2])}, {_f(z[2])}, {_f(o[0])}, {_f(o[1])}, {_f(o[2])})")
        sid = f"Forme_{k}"
        if h["forme"] == "capsule":
            subs.append(f'[sub_resource type="CapsuleShape3D" id="{sid}"]\nradius = {_f(r)}\nheight = {_f(L + 2 * r)}\n')
        else:
            subs.append(f'[sub_resource type="BoxShape3D" id="{sid}"]\nsize = Vector3({_f(2 * r)}, {_f(L)}, {_f(2 * r)})\n')
        os_g = nom_os_godot(h["os"])
        att = f"Hitbox_{_nom_noeud(os_g)}"
        noeuds.append(
            f'[node name="{att}" type="BoneAttachment3D" parent="."]\nbone_name = "{os_g}"\n'
            f'use_external_skeleton = true\n\n'
            f'[node name="Zone" type="Area3D" parent="{att}"]\ncollision_layer = {COUCHES[h["role"]]}\n'
            f'collision_mask = 0\nmonitoring = false\nmetadata/role = "{h["role"]}"\nmetadata/os = "{os_g}"\n\n'
            f'[node name="Forme" type="CollisionShape3D" parent="{att}/Zone"]\ntransform = {transfo}\n'
            f'shape = SubResource("{sid}")\n')
        rapport.append({**h, "os_godot": os_g, "longueur": round(L, 5), "rayon_m": round(r, 5)})
    tete = (f"[gd_scene load_steps={2 + len(subs) + 1} format=3]\n\n"
            f'[ext_resource type="PackedScene" path="{res_glb}" id="1_modele"]\n'
            f'[ext_resource type="Script" path="{res_script}" id="2_hitboxes"]\n\n')
    racine = (f'[node name="{_nom_noeud(nom)}" type="Node3D"]\nscript = ExtResource("2_hitboxes")\n\n'
              f'[node name="Modele" parent="." instance=ExtResource("1_modele")]\n\n')
    return tete + "\n".join(subs) + "\n" + racine + "\n".join(noeuds), {"hitboxes": rapport}


SCRIPT_GODOT = '''extends Node3D
## DeepotusVideo t343 : relie chaque BoneAttachment3D (hitbox) au Skeleton3D importé du GLB.
## Le chemin du squelette dépend de l'importeur : il est cherché au démarrage, sous « Modele ».
## Couches : 1 = hurtbox (reçoit les coups), 2 = hitbox (les porte) ; metadata « role » et « os » sur chaque Area3D.

@export var modele: NodePath = ^"Modele"

func _ready() -> void:
	var racine := get_node_or_null(modele)
	if racine == null:
		push_warning("hitboxes : nœud %s introuvable" % modele)
		return
	var trouves := racine.find_children("*", "Skeleton3D", true, false)
	if trouves.is_empty():
		push_warning("hitboxes : aucun Skeleton3D sous %s" % racine.name)
		return
	var squelette: Skeleton3D = trouves[0]
	for enfant in get_children():
		if enfant is BoneAttachment3D:
			var attache := enfant as BoneAttachment3D
			attache.set_external_skeleton(attache.get_path_to(squelette))
			attache.bone_name = attache.bone_name
			if squelette.find_bone(attache.bone_name) < 0:
				push_warning("hitboxes : os « %s » absent du squelette importé" % attache.bone_name)
'''


def archive_godot(glb: bytes, choix: list, *, dossier: str, nom: str = "Personnage") -> tuple[bytes, dict]:
    """ZIP à déposer dans un projet Godot : `<dossier>/modele.glb`, `<dossier>/<nom>.tscn`, `hitboxes_os.gd`."""
    dossier = re.sub(r"[^A-Za-z0-9_-]", "_", dossier)[:60] or "deepotus"
    base = f"res://deepotus/{dossier}"
    tscn, rapport = scene_godot(glb, choix, res_glb=f"{base}/modele.glb", res_script=f"{base}/hitboxes_os.gd",
                                nom=nom)
    clips = clips_glb(glb)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"deepotus/{dossier}/modele.glb", glb)
        z.writestr(f"deepotus/{dossier}/{_nom_noeud(nom)}.tscn", tscn)
        z.writestr(f"deepotus/{dossier}/hitboxes_os.gd", SCRIPT_GODOT)
        z.writestr(f"deepotus/{dossier}/LISEZMOI.json", json.dumps(
            {"tache": "t343", "scene": f"{_nom_noeud(nom)}.tscn", "clips": clips, **rapport,
             "couches": {"1": "hurt", "2": "hit"},
             "note": "Copier le dossier « deepotus » à la racine du projet Godot 4 ; les clips sont dans "
                     "l'AnimationPlayer importé du GLB."}, ensure_ascii=False, indent=1))
    return tampon.getvalue(), {"clips": clips, **rapport, "dossier": f"deepotus/{dossier}"}


# ───────────────────────────── les mouvements rangés dans le job ─────────────────────────────
# `<job>/mouvements/<nom>.bvh|.glb` + `<nom>.json` (origine, date, résumé, devis). Les clips Meshy du job
# (`anim_*.glb`, rig T104) et les clips de la version affichée sont aussi des sources, sans copie.

def dossier(job: str) -> Path:
    from app.services import mesh_report
    return mesh_report.job_dir(Path(str(job)).name) / "mouvements"


def nom_fichier(nom: str, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(str(nom)).stem).strip("_")[:48] or "mouvement"
    return base + ext


def ranger(job: str, nom: str, data: bytes, meta: dict) -> dict:
    """Range un mouvement LU sans erreur dans le job (un nom déjà pris reçoit un suffixe)."""
    import time
    ext = Path(nom).suffix.lower()
    m = lire_fichier(nom, data)
    d = dossier(job)
    d.mkdir(parents=True, exist_ok=True)
    f = nom_fichier(nom, ext)
    k = 2
    while (d / f).exists():
        f = nom_fichier(f"{Path(nom).stem}_{k}", ext)
        k += 1
    (d / f).write_bytes(data)
    fiche = {"fichier": f, "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S"), **resume(m), **(meta or {})}
    (d / (f + ".json")).write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    return fiche


def sources(job: str) -> list[dict]:
    """Les mouvements du job : importés / vidéo (dossier mouvements) puis les clips Meshy rapatriés."""
    out = []
    d = dossier(job)
    if d.is_dir():
        for f in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix.lower() in EXTENSIONS and f.is_file():
                try:
                    fiche = json.loads((d / (f.name + ".json")).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    fiche = {}
                out.append({"type": "fichier", "nom": f.name, "origine": fiche.get("origine", "import"),
                            "secondes": fiche.get("secondes"), "fps": fiche.get("fps"), "os": fiche.get("os"),
                            "format": f.suffix.lower()[1:], "cree_le": fiche.get("cree_le")})
    try:
        from app.services import asset3d_rig
        for a in asset3d_rig.animations_du_job(Path(str(job)).name):
            out.append({"type": "meshy", "nom": a["nom"], "origine": "meshy", "format": "glb"})
    except Exception:                                   # noqa: BLE001 — un job sans manifeste n'a pas de clip Meshy
        pass
    return out


def charger_source(job: str, src: dict, version_glb: bytes) -> dict:
    """Le mouvement désigné par {type, nom, clip?} : fichier rangé, clip Meshy du job, ou clip de la version."""
    if not isinstance(src, dict):
        raise ValueError("source : {type, nom} attendu")
    typ, nom = src.get("type"), str(src.get("nom") or "")
    clip = src.get("clip")
    if clip is not None and not isinstance(clip, str):
        raise ValueError("source : « clip » attend un nom")
    if typ == "clip":
        return lire_glb_mouvement(version_glb, nom)
    if not nom or Path(nom).name != nom:
        raise ValueError("source : un nom de fichier nu est attendu")
    if typ == "fichier":
        p = dossier(job) / nom
        if p.suffix.lower() not in EXTENSIONS or not p.is_file():
            raise FileNotFoundError(f"mouvement introuvable : {nom}")
        return lire_fichier(nom, p.read_bytes(), clip)
    if typ == "meshy":
        from app.services import asset3d_rig
        from app.services import asset3d_service as A3
        for a in asset3d_rig.animations_du_job(Path(str(job)).name):
            if a["nom"] == nom:
                return lire_glb_mouvement((A3._job_dir(Path(str(job)).name) / Path(a["file"]).name).read_bytes(), clip)
        raise FileNotFoundError(f"clip Meshy introuvable : {nom}")
    raise ValueError("source : type « fichier », « meshy » ou « clip »")
