# -*- coding: utf-8 -*-
"""t390 (31/10/2026) — les moteurs 3D relevés chez Sorceress et sur fal le 31/10 (relevé t387,
docs/superpowers/specs/2026-10-31-api-3d-releve.md §1), avec TOUS leurs réglages.

Pourquoi un module à part plutôt que cinq branches de plus dans `asset3d_service.build_engine_args` : chaque moteur
neuf porte un SCHÉMA de réglages dont les clés sont les noms mêmes des paramètres fal. Le schéma sert trois fois —
l'accordéon de l'écran Créer (servi par /api/assets3d/engines), la validation côté serveur (une valeur hors bornes
est un 400, jamais une surprise payante) et le devis (chaque supplément facturé est une ligne). Les sept moteurs
d'hier gardent leurs adaptateurs ; ceux-ci passent par `args()`.

Le devis suit les prix affichés par fal au 31/10/2026 (relevé t387) ; un supplément n'est compté que si le réglage
qui le déclenche est posé.
"""
from __future__ import annotations

# `badge` : un identifiant traduit par l'écran (creer3d.badge.<id>), jamais un texte affiché tel quel
# un réglage : clé fal, type (bool | enum | int), défaut, valeurs ou bornes, et le supplément facturé s'il y en a
MOTEURS = {
    "tripo-p2": {
        "label": "Tripo P2", "fournisseur": "Tripo", "badge": "nouveau",
        "endpoint": "tripo3d/p2/image-to-3d", "endpoint_texte": "tripo3d/p2/text-to-3d",
        "cle_image": "image_url", "formats": ["glb", "fbx"],
        "note": "le plus récent de Tripo : topologie quad native, texture jusqu'à « extreme ».",
        "reglages": [
            {"cle": "texture", "type": "bool", "defaut": True},
            {"cle": "pbr", "type": "bool", "defaut": True},
            {"cle": "texture_quality", "type": "enum", "defaut": "standard",
             "valeurs": ["fast", "standard", "detailed", "extreme"]},
            {"cle": "delight", "type": "bool", "defaut": True},
            {"cle": "quad", "type": "bool", "defaut": False},
            {"cle": "face_limit", "type": "int", "defaut": None, "min": 48, "max": 50000},
            {"cle": "auto_size", "type": "bool", "defaut": False},
            {"cle": "model_seed", "type": "int", "defaut": None, "min": 0, "max": 2147483647},
        ],
    },
    "tripo-p1": {
        "label": "Tripo Smart Mesh", "fournisseur": "Tripo", "badge": "low_poly",
        "endpoint": "tripo3d/p1/image-to-3d", "endpoint_texte": "tripo3d/p1/text-to-3d",
        "cle_image": "image_url", "formats": ["glb", "fbx"],
        "note": "maillage intelligent basse résolution (48 à 20 000 faces) — accessoires et décor de jeu.",
        "reglages": [
            {"cle": "texture", "type": "bool", "defaut": True},
            {"cle": "face_limit", "type": "int", "defaut": None, "min": 48, "max": 20000},
            {"cle": "model_seed", "type": "int", "defaut": None, "min": 0, "max": 2147483647},
        ],
    },
    "hunyuan-3.1": {
        "label": "Hunyuan 3D 3.1", "fournisseur": "Hunyuan", "badge": "budget",
        "endpoint": "fal-ai/hunyuan-3d/v3.1/pro/image-to-3d", "endpoint_texte": "fal-ai/hunyuan-3d/v3.1/pro/text-to-3d",
        "cle_image": "input_image_url", "formats": ["glb", "obj"],
        "note": "Hunyuan 3.1 Pro : géométrie seule ou texturée, PBR, budget de faces de 40 000 à 1 500 000.",
        "reglages": [
            {"cle": "generate_type", "type": "enum", "defaut": "Normal", "valeurs": ["Normal", "Geometry"]},
            {"cle": "enable_pbr", "type": "bool", "defaut": False, "surcout": 0.15},
            {"cle": "face_count", "type": "int", "defaut": None, "min": 40000, "max": 1500000, "surcout": 0.15},
        ],
    },
    "trellis-2": {
        "label": "TRELLIS 2", "fournisseur": "Microsoft", "badge": "",
        "endpoint": "fal-ai/trellis-2", "endpoint_texte": None,
        "cle_image": "image_url", "formats": ["glb"],
        "note": "image unique ; résolution 512 à 1536, texture jusqu'à 4096, remaillage.",
        "reglages": [
            {"cle": "resolution", "type": "enum", "defaut": 1024, "valeurs": [512, 1024, 1536]},
            {"cle": "texture_size", "type": "enum", "defaut": 2048, "valeurs": [1024, 2048, 4096]},
            {"cle": "decimation_target", "type": "int", "defaut": None, "min": 5000, "max": 2000000},
            {"cle": "remesh", "type": "bool", "defaut": True},
            {"cle": "ss_sampling_steps", "type": "int", "defaut": None, "min": 1, "max": 50},
            {"cle": "ss_guidance_strength", "type": "int", "defaut": None, "min": 0, "max": 10},
            {"cle": "seed", "type": "int", "defaut": None, "min": 0, "max": 2147483647},
        ],
    },
    "rodin-2.5": {
        "label": "Rodin 2.5", "fournisseur": "Hyper3D", "badge": "",
        "endpoint": "fal-ai/hyper3d/rodin/v2.5", "endpoint_texte": "fal-ai/hyper3d/rodin/v2.5/text-to-3d",
        "cle_image": "image_urls", "formats": ["glb", "fbx", "obj", "stl", "usdz"],
        "note": "Gen-2.5 : densité (tier), matériau, maillage quad ou brut, pose T/A, cinq formats.",
        "reglages": [
            {"cle": "tier", "type": "enum", "defaut": "Gen-2.5-High",
             "valeurs": ["Gen-2.5-Minimum", "Gen-2.5-Extreme-Low", "Gen-2.5-Low", "Gen-2.5-Medium", "Gen-2.5-High",
                         "Gen-2.5-Extreme-High"]},
            {"cle": "material", "type": "enum", "defaut": "PBR", "valeurs": ["PBR", "Shaded", "All", "None"]},
            {"cle": "quality_mesh_option", "type": "enum", "defaut": "Auto",
             "valeurs": ["Auto", "4K Quad", "8K Quad", "18K Quad", "50K Quad", "2K Triangle", "20K Triangle",
                         "150K Triangle", "500K Triangle"]},
            {"cle": "geometry_file_format", "type": "enum", "defaut": "glb", "valeurs": ["glb", "fbx", "obj", "stl", "usdz"]},
            {"cle": "hd_texture", "type": "bool", "defaut": False},
            {"cle": "seed", "type": "int", "defaut": None, "min": 0, "max": 65535},
        ],
    },
    "meshy-7.1": {
        "label": "Meshy 7.1", "fournisseur": "Meshy", "badge": "nouveau",
        "endpoint": "meshy/v7.1/image-to-3d", "endpoint_texte": "meshy/v7.1/text-to-3d",
        "cle_image": "image_url", "formats": ["glb", "fbx", "obj", "usdz"],
        "note": "Meshy 7.1 par fal : topologie, polycount, symétrie, pose, remaillage, texture et PBR.",
        "reglages": [
            {"cle": "model_type", "type": "enum", "defaut": "standard",
             "valeurs": ["standard", "lowpoly", "smart-topology", "smart-topology-t2"]},
            {"cle": "topology", "type": "enum", "defaut": "triangle", "valeurs": ["triangle", "quad"]},
            {"cle": "target_polycount", "type": "int", "defaut": 30000, "min": 100, "max": 300000},
            {"cle": "symmetry_mode", "type": "enum", "defaut": "auto", "valeurs": ["auto", "on", "off"]},
            {"cle": "should_remesh", "type": "bool", "defaut": True},
            {"cle": "should_texture", "type": "bool", "defaut": True},
            {"cle": "enable_pbr", "type": "bool", "defaut": False},
            {"cle": "geometry_resolution", "type": "enum", "defaut": "standard", "valeurs": ["standard", "2k", "4k"]},
        ],
    },
}

# la pose (t376) : la clé fal par moteur, ou None si le moteur n'en a pas (grisé à l'écran)
POSE = {"meshy-7.1": "pose_mode", "rodin-2.5": "TAPose"}

# la coupure de texture de l'appel commun (`textures: False`, le « brouillon » des sept d'hier) : le réglage du schéma
# qui la porte, par moteur ; un moteur absent d'ici n'a pas de brouillon (drapeau `draft` faux)
COUPE_TEXTURE = {"tripo-p2": ("texture", False), "tripo-p1": ("texture", False), "meshy-7.1": ("should_texture", False),
                 "hunyuan-3.1": ("generate_type", "Geometry")}


def schema(moteur: str) -> list[dict]:
    return MOTEURS[moteur]["reglages"]


def valider(moteur: str, reglages: dict | None) -> dict:
    """Les réglages d'un moteur neuf, bornés au schéma. ValueError (→ 400) pour une clé inconnue ou une valeur hors
    bornes : jamais d'envoi silencieusement corrigé à un fournisseur qui facture."""
    if moteur not in MOTEURS:
        raise ValueError(f"moteur neuf inconnu : {moteur!r}")
    sch = {r["cle"]: r for r in schema(moteur)}
    out = {}
    for k, v in (reglages or {}).items():
        if k not in sch:
            raise ValueError(f"{moteur} : réglage inconnu {k!r}")
        r = sch[k]
        if v is None or v == "":
            continue
        if r["type"] == "bool":
            if not isinstance(v, bool):
                raise ValueError(f"{moteur}.{k} : booléen attendu")
        elif r["type"] == "enum":
            if v not in r["valeurs"]:
                raise ValueError(f"{moteur}.{k} : {v!r} hors de {r['valeurs']}")
        elif r["type"] == "int":
            if isinstance(v, bool) or not isinstance(v, int):
                raise ValueError(f"{moteur}.{k} : entier attendu")
            if not r["min"] <= v <= r["max"]:
                raise ValueError(f"{moteur}.{k} : {v} hors de [{r['min']}, {r['max']}]")
        out[k] = v
    return out


def args(moteur: str, image_urls: list[str], opts: dict) -> dict:
    """Les arguments fal d'un tir : l'image (ou le prompt en mode texte), les réglages validés, la pose."""
    m = MOTEURS[moteur]
    a = dict(valider(moteur, opts.get("reglages")))
    if opts.get("textures") is False and moteur in COUPE_TEXTURE:
        k, v = COUPE_TEXTURE[moteur]
        a.setdefault(k, v)
    prompt = str(opts.get("prompt") or "").strip()
    if image_urls:
        a[m["cle_image"]] = list(image_urls[:5]) if m["cle_image"] == "image_urls" else image_urls[0]
    elif prompt:
        if not m.get("endpoint_texte"):
            raise ValueError(f"{m['label']} ne génère pas depuis un texte")
        a["prompt"] = prompt[:600]
    else:
        raise ValueError("une image ou un prompt est nécessaire")
    if image_urls and prompt and moteur == "rodin-2.5":
        a["prompt"] = prompt[:600]
    pose = opts.get("pose") or ""
    if moteur == "rodin-2.5":
        a["TAPose"] = bool(pose)                 # comme Rodin d'hier : le paramètre part toujours, vrai si une pose
    elif pose and moteur in POSE:
        a[POSE[moteur]] = pose
    if moteur == "tripo-p2" and a.get("texture") is False:
        a["pbr"] = False                         # pbr active la texture chez Tripo : on ne paie pas ce qu'on refuse
    return a


def endpoint(moteur: str, texte: bool) -> str:
    m = MOTEURS[moteur]
    if texte:
        if not m.get("endpoint_texte"):
            raise ValueError(f"{m['label']} ne génère pas depuis un texte")
        return m["endpoint_texte"]
    return m["endpoint"]


def prix(moteur: str, reglages: dict | None) -> list[tuple[str, float]]:
    """Les lignes du devis (libellé, $) pour un tir, au tarif fal relevé le 31/10/2026."""
    r = valider(moteur, reglages)
    defauts = {x["cle"]: x["defaut"] for x in schema(moteur)}
    v = lambda k: r.get(k, defauts.get(k))             # noqa: E731
    if moteur == "tripo-p2":
        if v("texture") is False:
            return [("Tripo P2 sans texture", 1.00)]
        q = v("texture_quality")
        return [(f"Tripo P2 texture {q}", {"fast": 1.10, "standard": 1.10, "detailed": 1.20, "extreme": 1.30}[q])]
    if moteur == "tripo-p1":
        return [("Tripo Smart Mesh " + ("texturé" if v("texture") is not False else "sans texture"),
                 0.50 if v("texture") is not False else 0.40)]
    if moteur == "hunyuan-3.1":
        lignes = [("Hunyuan 3D 3.1 Pro", 0.375)]
        if v("enable_pbr") and v("generate_type") != "Geometry":
            lignes.append(("PBR", 0.15))
        if r.get("face_count") is not None:
            lignes.append(("Budget de faces personnalisé", 0.15))
        return lignes
    if moteur == "trellis-2":
        return [(f"TRELLIS 2 {v('resolution')}p", {512: 0.25, 1024: 0.30, 1536: 0.35}[v("resolution")])]
    if moteur == "rodin-2.5":
        return [("Rodin 2.5", 0.40)]
    if moteur == "meshy-7.1":
        return [("Meshy 7.1 " + ("texturé" if v("should_texture") is not False else "sans texture"),
                 1.20 if v("should_texture") is not False else 0.80)]
    raise ValueError(moteur)


def registre() -> dict:
    """Les entrées à verser dans `asset3d_service.ENGINES` (mêmes drapeaux que les sept d'hier)."""
    out = {}
    for mid, m in MOTEURS.items():
        out[mid] = {
            "endpoint": m["endpoint"], "endpoint_texte": m["endpoint_texte"], "formats": m["formats"],
            "label": m["label"], "fournisseur": m["fournisseur"], "badge": m["badge"],
            "multiview": m["cle_image"] == "image_urls", "max_images": 5 if m["cle_image"] == "image_urls" else 1,
            # drapeaux de l'appel COMMUN des sept d'hier (banc « un drapeau qui ment… ») : la topologie, la graine et
            # la qualité des neufs passent par leur schéma `reglages`, pas par ces options-là
            "texture_modes": ["no", "standard"] if mid in COUPE_TEXTURE else ["standard"],
            "draft": mid in COUPE_TEXTURE, "detailed": False, "pbr": True,
            "tpose": mid == "rodin-2.5", "quality_passthrough": False, "face_limit": False, "quad": False, "seed": False,
            "texte": bool(m["endpoint_texte"]), "reglages": m["reglages"], "neuf": True, "note": m["note"],
        }
    return out
