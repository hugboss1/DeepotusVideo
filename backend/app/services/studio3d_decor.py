# -*- coding: utf-8 -*-
"""t402 (31/10/2026) — Décor › Accessoire : un élément généré dans l'onglet 3D (rocher, caisse, plante…) préparé pour
le décor d'un jeu. Gratuit et local.

`poser` : le pivot AU SOL (le bas de la boîte englobante à y = 0, centré en x et z) et, si demandée, la HAUTEUR RÉELLE
en mètres (mise à l'échelle uniforme). Même mécanique que `mesh_edit.reparer` — un nœud racine NEUF porte la
correction, les transformations existantes ne sont jamais réécrites —, écrite comme une version de plus par la route.
Le haut est Y (convention glTF ; un modèle couché se redresse d'abord dans l'Établi, « Réparer › axe haut »).

`budget` : le préréglage de triangles conseillé par RÔLE de décor (accessoire de premier plan, de fond, végétation
dense…), ramené aux préréglages de l'écran Préparer.

`variantes` (t402, suite) : N copies (2 à 8) du modèle, chacune tirée de la GRAINE — échelle uniforme ± %, rotation
autour de Y, multiplicateur de teinte (jitter HSV) posé sur le `baseColorFactor` de chaque matériau. Seul le document
JSON change : le tampon binaire ressort identique octet pour octet. Chaque variante devient un JOB NEUF
`<job>_var<k>` et non une version : une version REMPLACE la précédente dans la chaîne d'un modèle (Préparer, Exporter
et la galerie montrent la dernière), alors que des variantes COEXISTENT — on les pose ensemble dans une scène, chacune
avec sa ligne dans la galerie et sa source propre au Plateau. Le manifeste dit la source (job, version), la graine,
l'indice et le tirage. Même graine + mêmes réglages = mêmes variantes, et le même job resservi (aucun doublon).

`masque_vent` : un attribut de sommet `_WIND` (flottant ; le préfixe « _ » est celui des attributs d'application en
glTF 2.0) = la hauteur normalisée (0 au pied, 1 au sommet, courbe et seuil facultatifs), ajouté EN FIN de tampon (les
octets déjà là ne bougent pas) et écrit comme une version de plus. Pas COLOR_0 : three.js et Blender multiplient la
couleur de base par COLOR_0, le pied du modèle sortirait noir. Le runtime de vent (`decor_runtime.js`) lit `_wind`.

`cartes` : l'IMPOSTEUR d'un modèle — 2 ou 3 plans croisés (deux faces chacun, dos à dos), texturés par un atlas de huit
vues orthographiques (azimuts 0°, 45°… 315°, 4 × 2 cases, rendu dans le navigateur). Matériau éclairé d'avance
(KHR_materials_unlit), alpha MASK. Un fichier à part (`decor/cartes.v<N>.glb`), pas une version : il ne remplace pas
le modèle, il le relaie au loin.

`instance_plateau` : l'instance de scène du Plateau 3D (forme de `scene3d_routes._instances`) qui pose la version
courante à l'origine, à l'échelle 1 (le GLB est en mètres une fois posé).
"""
from __future__ import annotations

import base64
import colorsys
import json
import math
import random
import re
import struct

HAUTEUR_MIN, HAUTEUR_MAX = 0.01, 500.0

# rôle → préréglage de Préparer (mesh_optimize.PRESETS) ; l'écran envoie vers Préparer avec ce préréglage allumé
ROLES = {
    "premier_plan": "detailed",     # 5 000 : un accessoire que la caméra approche
    "decor": "prop",                # 2 500 : un élément de décor courant
    "fond": "small",                # 1 000 : vu de loin
    "foule": "micro",               # 500 : répété des dizaines de fois (cailloux, touffes)
    "heros": "game",                # 10 000 : l'objet central d'une scène
}


def poser(data: bytes, hauteur_m: float | None = None) -> tuple[bytes, dict]:
    """(GLB posé au sol et à la hauteur demandée, mesures avant/après). ValueError pour une hauteur hors bornes ou un
    GLB illisible (compressé : `print3d.lire_glb_triangles` le dit)."""
    from app.services import mesh_edit, print3d
    if hauteur_m is not None:
        if isinstance(hauteur_m, bool) or not isinstance(hauteur_m, (int, float)):
            raise ValueError("hauteur_m attend un nombre de mètres")
        if not HAUTEUR_MIN <= float(hauteur_m) <= HAUTEUR_MAX:
            raise ValueError(f"hauteur_m hors de [{HAUTEUR_MIN}, {HAUTEUR_MAX}] m")
    tris = print3d.lire_glb_triangles(data)
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    h = y1 - y0
    if h <= 0:
        raise ValueError("modèle plat : aucune hauteur à mesurer")
    s = 1.0 if hauteur_m is None else float(hauteur_m) / h
    # p' = s·p + t : le bas à 0, le centre en x et z à 0
    t = [-s * (x0 + x1) / 2.0, -s * y0, -s * (z0 + z1) / 2.0]
    doc, binc = mesh_edit.lire_glb(data)
    ident = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    mesh_edit._envelopper(doc, mesh_edit._matrice(ident, s, t))
    sortie = mesh_edit.ecrire_glb(doc, binc)
    mesures = {"avant": {"hauteur": round(h, 6), "largeur": round(x1 - x0, 6), "profondeur": round(z1 - z0, 6),
                         "bas": round(y0, 6)},
               "apres": {"hauteur": round(h * s, 6), "largeur": round((x1 - x0) * s, 6),
                         "profondeur": round((z1 - z0) * s, 6), "bas": 0.0},
               "echelle": round(s, 9)}
    return sortie, mesures


def budget(role: str) -> dict:
    from app.services import mesh_optimize
    if role not in ROLES:
        raise ValueError(f"rôle inconnu : {role!r} (attendu : {', '.join(ROLES)})")
    p = ROLES[role]
    return {"role": role, "preset": p, "triangles": mesh_optimize.PRESETS[p]}


# ── variantes ────────────────────────────────────────────────────────────────
VARIANTES_MIN, VARIANTES_MAX = 2, 8
ECHELLE_MAX_PCT = 50.0          # ± 50 % au plus
TEINTE_MAX = 1.0                # saturation du multiplicateur (0 = aucune teinte)
LUMINOSITE_MAX = 0.6            # assombrissement au plus
_JOB_MAX = 64                   # la forme de job du Plateau : ^[A-Za-z0-9_-]{1,64}$


def _borne(v, nom: str, lo: float, hi: float) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise ValueError(f"{nom} attend un nombre")
    if not lo <= float(v) <= hi:
        raise ValueError(f"{nom} hors de [{lo:g}, {hi:g}]")
    return float(v)


def reglages_variantes(r: dict | None) -> dict:
    """Les réglages des variantes, vérifiés et complétés. ValueError sinon."""
    r = dict(r or {})
    n = r.get("nombre", 4)
    if isinstance(n, bool) or not isinstance(n, int) or not VARIANTES_MIN <= n <= VARIANTES_MAX:
        raise ValueError(f"nombre de variantes : un entier de {VARIANTES_MIN} à {VARIANTES_MAX}")
    g = r.get("graine", 1)
    if isinstance(g, bool) or not isinstance(g, int) or not 0 <= g <= 2 ** 31 - 1:
        raise ValueError("graine : un entier positif")
    rot = r.get("rotation", True)
    if not isinstance(rot, bool):
        raise ValueError("rotation : vrai ou faux")
    return {"nombre": n, "graine": g, "rotation": rot,
            "echelle_pct": _borne(r.get("echelle_pct", 15), "echelle_pct", 0, ECHELLE_MAX_PCT),
            "teinte": _borne(r.get("teinte", 0.25), "teinte", 0, TEINTE_MAX),
            "luminosite": _borne(r.get("luminosite", 0.15), "luminosite", 0, LUMINOSITE_MAX)}


def tirage(graine: int, k: int, reglages: dict) -> dict:
    """Le tirage de la variante k (1..N) : déterministe (graine textuelle → sha512, stable d'un lancement à l'autre).
    Les cinq nombres sont TOUJOURS tirés, dans le même ordre : couper la rotation ne change pas l'échelle."""
    from app.services.gltf_builder import _srgb_to_linear
    rnd = random.Random(f"deepotus-decor:{int(graine)}:{int(k)}")
    u_ech, u_rot, u_h, u_s, u_v = (rnd.random() for _ in range(5))
    s = 1.0 + (2 * u_ech - 1) * reglages["echelle_pct"] / 100.0
    ry = u_rot * 360.0 if reglages["rotation"] else 0.0
    srgb = colorsys.hsv_to_rgb(u_h, u_s * reglages["teinte"], 1.0 - u_v * reglages["luminosite"])
    return {"index": int(k), "echelle": round(s, 6), "rotation_y": round(ry, 4),
            "teinte": "#" + "".join(f"{round(c * 255):02x}" for c in srgb),
            "multiplicateur": [round(_srgb_to_linear(c), 6) for c in srgb]}


def appliquer_variante(data: bytes, t: dict) -> bytes:
    """Le GLB d'une variante : un nœud racine NEUF porte l'échelle et la rotation Y (autour de l'origine, donc du
    pivot au sol une fois l'accessoire posé), chaque `baseColorFactor` est multiplié par la teinte (un matériau sans
    facteur part du blanc, une texture garde ses détails et prend la teinte). Une primitive sans matériau en reçoit
    un, teinté. Le tampon binaire n'est pas touché."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(data)
    m = t["multiplicateur"]
    mats = doc.get("materials") or []
    for mat in mats:
        pbr = mat.setdefault("pbrMetallicRoughness", {})
        bc = list(pbr.get("baseColorFactor") or [1.0, 1.0, 1.0, 1.0])
        pbr["baseColorFactor"] = [round(bc[i] * m[i], 6) for i in range(3)] + [bc[3] if len(bc) > 3 else 1.0]
    sans = [p for me in doc.get("meshes") or [] for p in me.get("primitives") or [] if "material" not in p]
    if sans:
        mats.append({"name": "variante_teinte", "pbrMetallicRoughness": {"baseColorFactor": list(m) + [1.0],
                                                                          "metallicFactor": 0.0, "roughnessFactor": 1.0}})
        for p in sans:
            p["material"] = len(mats) - 1
    if mats:
        doc["materials"] = mats
    a = math.radians(t["rotation_y"])
    c, s_ = math.cos(a), math.sin(a)
    rot = [[c, 0.0, s_], [0.0, 1.0, 0.0], [-s_, 0.0, c]]
    mesh_edit._envelopper(doc, mesh_edit._matrice(rot, t["echelle"], [0.0, 0.0, 0.0]))
    return mesh_edit.ecrire_glb(doc, binc)


def _base_variante(job: str) -> str:
    return re.sub(r"_var\d+$", "", job)[:_JOB_MAX - len("_var99")]


def variantes(job: str, version: int, data: bytes, nom: str, reglages: dict) -> list[dict]:
    """Écrit les N variantes comme jobs neufs (ou resservit ceux déjà écrits pour la même source et le même tirage).
    Rend [{job, index, nouveau, tirage}]. Jamais d'écrasement : un nom pris passe au numéro libre suivant."""
    from app.services import asset3d_service as A3, mesh_report
    r = reglages_variantes(reglages)
    racine = mesh_report.job_dir("x").parent
    base = _base_variante(job)
    regl = {k: r[k] for k in ("rotation", "echelle_pct", "teinte", "luminosite")}
    existants, pris = {}, set()
    for d in racine.glob(f"{base}_var*"):
        if not re.fullmatch(re.escape(base) + r"_var\d+", d.name):
            continue
        pris.add(d.name)
        try:
            v = json.loads((d / "asset.json").read_text(encoding="utf-8")).get("variante") or {}
        except (OSError, ValueError, AttributeError):
            continue
        existants[(v.get("source_job"), v.get("source_version"), v.get("graine"), v.get("index"),
                   json.dumps(v.get("reglages"), sort_keys=True))] = d.name
    out, libre = [], 1
    for k in range(1, r["nombre"] + 1):
        t = tirage(r["graine"], k, r)
        cle = (job, int(version), r["graine"], k, json.dumps(regl, sort_keys=True))
        if cle in existants:
            out.append({"job": existants[cle], "index": k, "nouveau": False, "tirage": t})
            continue
        while f"{base}_var{libre}" in pris:
            libre += 1
        nj = f"{base}_var{libre}"
        pris.add(nj)
        d = mesh_report.job_dir(nj)
        d.mkdir(parents=True, exist_ok=False)
        (d / "model.glb").write_bytes(appliquer_variante(data, t))
        A3.write_manifest(d, {"name": f"{nom} · variante {k}", "engine": "decor", "stage": "variante", "version": 1,
                              "variante": {"source_job": job, "source_version": int(version), "graine": r["graine"],
                                           "index": k, "reglages": regl, "tirage": t}})
        mesh_report.write_report(nj, "model.glb", version=1, avec_silhouettes=False,
                                 extra={"outil": "decor", "operation": "decor_variante",
                                        "depuis": {"job": job, "version": int(version)}, "graine": r["graine"],
                                        "index": k})
        out.append({"job": nj, "index": k, "nouveau": True, "tirage": t})
    return out


# ── masque de vent ───────────────────────────────────────────────────────────
ATTRIBUT_VENT = "_WIND"
_COMPRESSIONS = ("KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_meshopt_compression")


def valeur_masque(t: float, courbe: float = 1.0, seuil: float = 0.0) -> float:
    """Hauteur normalisée t (0..1) → masque (0..1) : nul jusqu'au seuil, puis ((t − seuil) / (1 − seuil))^courbe.
    Croissante (au sens large) pour toute courbe > 0 : plus haut ne bouge jamais moins."""
    t = min(max(float(t), 0.0), 1.0)
    if t <= seuil:
        return 0.0
    return ((t - seuil) / (1.0 - seuil)) ** courbe


def masque_vent(data: bytes, *, courbe: float = 1.5, seuil: float = 0.0) -> tuple[bytes, dict]:
    """(GLB avec `_WIND` sur chaque primitive, rapport). La hauteur est celle du MONDE (transformations des nœuds
    comprises), normalisée sur tout le modèle. ValueError : GLB compressé, sans maillage ou plat."""
    from app.services import mesh_edit
    courbe = _borne(courbe, "courbe", 0.2, 5.0)
    seuil = _borne(seuil, "seuil", 0.0, 0.9)
    doc, binc = mesh_edit.lire_glb(data)
    if set(doc.get("extensionsUsed") or []) & set(_COMPRESSIONS):
        raise ValueError("GLB compressé (Draco / meshopt) : le masque s'écrit sur un GLB non compressé")
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    monde = {}                                  # maillage → matrice monde du premier nœud qui le porte
    for i, n in enumerate(nodes):
        if "mesh" in n and n["mesh"] not in monde:
            monde[n["mesh"]] = mesh_edit._mat_mul(mesh_edit._monde_des_ancetres(doc, i), mesh_edit._mat_locale(n))
    hauteurs = {}                               # accesseur POSITION → hauteurs monde
    cibles = []
    for mi, me in enumerate(meshes):
        if mi not in monde:
            continue
        m = monde[mi]
        for p in me.get("primitives") or []:
            acc = (p.get("attributes") or {}).get("POSITION")
            if acc is None:
                continue
            if acc not in hauteurs:
                pos = mesh_edit.lire_accesseur(doc, binc, acc, quoi="le masque de vent")
                hauteurs[acc] = [m[1] * x + m[5] * y + m[9] * z + m[13] for x, y, z in pos]
            cibles.append((p, acc))
    if not cibles or not any(hauteurs.values()):
        raise ValueError("aucun maillage posé dans la scène")
    y0 = min(min(h) for h in hauteurs.values() if h)
    y1 = max(max(h) for h in hauteurs.values() if h)
    if y1 - y0 <= 0:
        raise ValueError("modèle plat : aucune hauteur à mesurer")
    buf = bytearray(binc)
    acc_de = {}
    remplaces = 0
    for p, acc in cibles:
        if acc not in acc_de:
            vals = [valeur_masque((h - y0) / (y1 - y0), courbe, seuil) for h in hauteurs[acc]]
            buf += b"\x00" * (-len(buf) % 4)
            debut = len(buf)
            buf += struct.pack(f"<{len(vals)}f", *vals)
            doc.setdefault("bufferViews", []).append({"buffer": 0, "byteOffset": debut, "byteLength": 4 * len(vals)})
            doc.setdefault("accessors", []).append({"bufferView": len(doc["bufferViews"]) - 1, "componentType": 5126,
                                                    "count": len(vals), "type": "SCALAR",
                                                    "min": [min(vals)], "max": [max(vals)]})
            acc_de[acc] = len(doc["accessors"]) - 1
        if ATTRIBUT_VENT in p["attributes"]:
            remplaces += 1
        p["attributes"][ATTRIBUT_VENT] = acc_de[acc]
    bufs = doc.get("buffers") or [{}]
    bufs[0]["byteLength"] = len(buf)
    doc["buffers"] = bufs
    rapport = {"attribut": ATTRIBUT_VENT, "courbe": courbe, "seuil": seuil, "primitives": len(cibles),
               "sommets": sum(len(hauteurs[a]) for a in acc_de), "pied": round(y0, 6), "sommet": round(y1, 6),
               "remplaces": remplaces}
    return mesh_edit.ecrire_glb(doc, bytes(buf)), rapport


# ── cartes (imposteur) ───────────────────────────────────────────────────────
AZIMUTS = 8                     # 0°, 45°… 315° ; case k = azimut 45·k
ATLAS_COLONNES, ATLAS_LIGNES = 4, 2
ATLAS_MAX_OCTETS = 16 * 1024 * 1024
ATLAS_MAX_PX = 4096
PLANS = (2, 3)


def cadre_cartes(bornes) -> dict:
    """Le cadre CARRÉ commun aux vues et aux plans : centre de la boîte, côté = max(diagonale horizontale, hauteur).
    Le navigateur cadre ses huit caméras orthographiques avec la même formule (decor_calc.cadreCartes)."""
    (x0, x1), (y0, y1), (z0, z1) = bornes
    rayon = math.hypot((x1 - x0) / 2.0, (z1 - z0) / 2.0)
    cote = max(2.0 * rayon, y1 - y0)
    return {"centre": [(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0], "cote": cote}


def faces_cartes(plans: int) -> list[dict]:
    """Les faces des plans croisés : chaque plan d'angle a (k·180°/plans) a deux faces, a et a + 180°, chacune
    texturée par la vue d'azimut la plus proche (case round(angle / 45) mod 8)."""
    if isinstance(plans, bool) or plans not in PLANS:
        raise ValueError("plans : 2 ou 3")
    out = []
    for k in range(plans):
        a = 180.0 * k / plans
        for ang in (a, a + 180.0):
            out.append({"angle": ang, "case": int(round(ang / 45.0)) % AZIMUTS})
    return out


def _png_taille(png: bytes) -> tuple[int, int]:
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise ValueError("atlas : une image PNG est attendue")
    return struct.unpack(">II", png[16:24])


def lire_atlas(atlas) -> bytes:
    """Le PNG de l'atlas (data URL ou base64), vérifié : 4 × 2 cases carrées, de 64 à 4096 px de large, ≤ 16 Mo."""
    if not isinstance(atlas, str) or not atlas:
        raise ValueError("atlas : une image PNG en base64 est attendue")
    b64 = atlas.split(",", 1)[1] if atlas.startswith("data:") else atlas
    if len(b64) > ATLAS_MAX_OCTETS * 4 // 3 + 8:
        raise ValueError("atlas trop lourd (16 Mo au plus)")
    try:
        png = base64.b64decode(b64, validate=True)
    except ValueError:
        raise ValueError("atlas : base64 illisible")
    w, h = _png_taille(png)
    if w != 2 * h or w % ATLAS_COLONNES or not 64 <= w <= ATLAS_MAX_PX:
        raise ValueError(f"atlas : {ATLAS_COLONNES} × {ATLAS_LIGNES} cases carrées attendues (reçu {w} × {h})")
    return png


def cartes(bornes, png: bytes, plans: int = 2) -> bytes:
    """Le GLB imposteur : un maillage, un matériau non éclairé à alpha MASK, l'atlas embarqué."""
    from app.services import mesh_edit
    c = cadre_cartes(bornes)
    cx, cy, cz = c["centre"]
    d = c["cote"] / 2.0
    pos, nor, uv, idx = [], [], [], []
    for f in faces_cartes(plans):
        a = math.radians(f["angle"])
        n = (math.sin(a), 0.0, math.cos(a))             # vers la caméra de cet azimut
        r = (math.cos(a), 0.0, -math.sin(a))            # sa droite à l'écran
        col, lig = f["case"] % ATLAS_COLONNES, f["case"] // ATLAS_COLONNES
        u0, u1 = col / ATLAS_COLONNES, (col + 1) / ATLAS_COLONNES
        v0, v1 = lig / ATLAS_LIGNES, (lig + 1) / ATLAS_LIGNES
        b = len(pos)
        for sx, sy, u, v in ((-1, -1, u0, v1), (1, -1, u1, v1), (1, 1, u1, v0), (-1, 1, u0, v0)):
            pos.append((cx + sx * d * r[0], cy + sy * d, cz + sx * d * r[2]))
            nor.append(n)
            uv.append((u, v))
        idx += [b, b + 1, b + 2, b, b + 2, b + 3]       # anti-horaire vu de sa caméra
    # les bornes de POSITION sont celles des float32 écrits (le validateur glTF compare aux données, pas aux doubles)
    pos = [struct.unpack("<3f", struct.pack("<3f", *p)) for p in pos]
    vues: list[dict] = []
    binc = bytearray()

    def vue(octets: bytes, cible=None) -> int:
        binc.extend(b"\x00" * (-len(binc) % 4))
        v = {"buffer": 0, "byteOffset": len(binc), "byteLength": len(octets)}
        if cible:
            v["target"] = cible
        binc.extend(octets)
        vues.append(v)
        return len(vues) - 1

    bp = vue(b"".join(struct.pack("<3f", *p) for p in pos), 34962)
    bn = vue(b"".join(struct.pack("<3f", *p) for p in nor), 34962)
    bu = vue(b"".join(struct.pack("<2f", *p) for p in uv), 34962)
    bi = vue(struct.pack(f"<{len(idx)}H", *idx), 34963)
    bimg = vue(png)
    doc = {
        "asset": {"version": "2.0", "generator": "DeepotusVideo Décor · cartes (t402)"},
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "dz_cartes", "mesh": 0}],
        "meshes": [{"name": "dz_cartes", "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                                          "indices": 3, "material": 0}]}],
        "materials": [{"name": "dz_cartes", "alphaMode": "MASK", "alphaCutoff": 0.5, "doubleSided": False,
                       "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0,
                                                "roughnessFactor": 1.0},
                       "extensions": {"KHR_materials_unlit": {}}}],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "images": [{"bufferView": bimg, "mimeType": "image/png", "name": "dz_cartes_atlas"}],
        "accessors": [
            {"bufferView": bp, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": [min(p[i] for p in pos) for i in range(3)], "max": [max(p[i] for p in pos) for i in range(3)]},
            {"bufferView": bn, "componentType": 5126, "count": len(nor), "type": "VEC3"},
            {"bufferView": bu, "componentType": 5126, "count": len(uv), "type": "VEC2"},
            {"bufferView": bi, "componentType": 5123, "count": len(idx), "type": "SCALAR"},
        ],
        "bufferViews": vues,
        "buffers": [{"byteLength": len(binc) + (-len(binc) % 4)}],
    }
    return mesh_edit.ecrire_glb(doc, bytes(binc))


# ── Plateau 3D ───────────────────────────────────────────────────────────────
def id_libre(base: str, pris) -> str:
    """Un identifiant d'instance libre (≤ 40 caractères, comme scene3d_routes) : base, base_2, base_3…"""
    b = re.sub(r"[^A-Za-z0-9_-]+", "_", str(base or "accessoire"))[:34] or "accessoire"
    if b not in pris:
        return b
    n = 2
    while f"{b}_{n}" in pris:
        n += 1
    return f"{b}_{n}"


def instance_plateau(job: str, fichier: str, nom: str, dims, pris) -> dict:
    """L'instance du Plateau : maillage `assets3d` allégé à l'affichage, posé à l'origine, échelle 1 (mètres)."""
    return {"id": id_libre(job, pris), "nom": str(nom or job)[:80],
            "source": {"kind": "assets3d", "job": job, "file": fichier},
            "niveau": "allege", "dims": [round(float(x), 6) for x in dims],
            "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}, "couleur": "#8a8f98", "role": "decor"}
