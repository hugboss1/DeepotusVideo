# -*- coding: utf-8 -*-
"""Material Forge — stockage disque, validation et export des matières PBR.

Contrat : SPEC Material Forge, sections 1 à 3. Une matière = un dossier
``settings.outputs_path / "materials" / mat_xxxxxxxx/`` contenant son
``meta.json`` (l'objet Material) et ses maps PNG.

Trois règles tiennent tout le module :

1. **`mid` est le seul identifiant accepté** et il doit matcher
   ``^mat_[0-9a-f]{8}$``. Aucun nom venant du client n'est concaténé à un
   chemin sans passer par :func:`material_dir`, qui refuse tout le reste
   (même garde-fou que ``_lut_path`` dans ``effects_engine.py``).
2. **Aucune entrée invalide ne casse quoi que ce soit** : chaque valeur de
   ``props`` / ``derive`` est ramenée à son défaut si elle est absente,
   du mauvais type ou hors bornes. Les routes n'ont donc jamais à renvoyer 500
   sur un corps mal formé.
3. **PIL pur, zéro numpy** (contrainte du runtime embarqué). Le PNG 16 bits
   est écrit à la main (zlib + struct) parce que Pillow ne sait encoder du
   16 bits qu'en niveaux de gris, pas en RVB.

La dérivation des maps (``pbr_service``) et la construction GLB
(``gltf_builder``) vivent dans leurs propres modules ; ici on ne fait que
stocker, valider et empaqueter.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
import shutil
import struct
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageChops
from loguru import logger

__all__ = [
    "MID_RE", "MAP_KINDS", "SECONDARY_MAPS", "MESHES", "NAMINGS",
    "EXPORT_FORMATS", "RESOLUTIONS", "PREVIEW_RESOLUTIONS", "SEAM_METHODS",
    "ENVS", "PRESETS", "clean_preview_res", "preview_cache_key",
    "preview_cache_get", "preview_cache_put",
    "is_valid_mid", "new_mid", "materials_root", "material_dir", "map_path",
    "default_props", "default_derive", "merge_props", "merge_derive",
    "normalize_material", "create_material", "read_material", "env_list",
    "write_material", "list_materials", "duplicate_material",
    "delete_material", "save_maps", "load_maps", "write_source",
    "write_thumb", "thumb_is_current",
    "resize_maps", "png_bytes", "export_zip", "export_manifest",
    "GLB_SLOTS", "glb_to_gltf", "MASKMAP", "EXPORT_EXTRA_KINDS",
    "DEFAULT_EXPORT_MAPS", "default_export_maps", "build_maskmap", "map_role",
    "bake_levels", "map_stats", "seam_report", "refresh_report",
    "natural_levels", "NAMING_ALIASES", "NAMING_LABELS", "NAMING_NOTES",
    "UNITY_NAMINGS", "clean_naming", "naming_catalog", "engine_slot",
    "render_block", "RENDER_NOTE", "public_material",
    "export_filename", "naming_map", "env_jpeg",
]

# ── constantes de contrat ────────────────────────────────────────────────────

MID_RE = re.compile(r"^mat_[0-9a-f]{8}$")

# ordre canonique (celui du SPEC) : sert aussi d'ordre d'affichage
MAP_KINDS = ("basecolor", "normal", "roughness", "metallic", "ao", "height",
             "emissive", "orm")
# tout sauf la basecolor : ce que `derive` reconstruit gratuitement
SECONDARY_MAPS = tuple(k for k in MAP_KINDS if k != "basecolor")

MAP_MODES = {"basecolor": "RGB", "normal": "RGB", "emissive": "RGB",
             "orm": "RGB", "roughness": "L", "metallic": "L", "ao": "L",
             "height": "L"}

MESHES = ("sphere", "cube", "torus", "cylinder", "plane", "tiled")

# ── conventions d'export : URP et HDRP ne sont PAS le même moteur ────────────
#
# LE DEFAUT QUE CECI CORRIGE. Une seule cible « unity » annonçait
# « Slots URP / HDRP : BaseMap, MaskMap, Occlusion ». Vérification faite dans
# la documentation Unity (URP Lit « Lit shader material Inspector window
# reference », HDRP « Mask and detail maps ») :
#
#   URP Lit  — emplacements : Base Map · Metallic Map · Normal Map ·
#              Height Map · Occlusion Map · Emission Map.
#              AUCUNE propriété « Mask Map » (le mot Mask n'apparaît que dans
#              Detail Inputs). Le smoothness vient de l'alpha de la Metallic
#              Map (« Source : Metallic Alpha », défaut). URP accepte une
#              texture packée R=métal V=occlusion A=smoothness, à condition de
#              l'assigner AUX DEUX emplacements Metallic et Occlusion.
#   HDRP Lit — emplacement Mask Map : R=métal, V=occlusion, B=masque de détail,
#              A=smoothness. L'occlusion vit donc DANS le Mask Map : un
#              emplacement Occlusion séparé n'existe pas.
#
# Une cible unique ne pouvait donc pas être vraie pour les deux : le texte
# citait un slot inexistant sous URP et un slot redondant sous HDRP, puis
# l'archive décochait justement Occlusion, Roughness et Metallic — elle ne
# remplissait plus aucun emplacement d'URP. Deux cibles séparées, chacune
# livrant exactement ce que SON moteur branche.
NAMINGS = ("standard", "unity_urp", "unity_hdrp", "unreal", "godot")
# `unity` reste accepté (liens et réglages enregistrés) et pointe sur URP, le
# pipeline par défaut d'Unity depuis 2021.
NAMING_ALIASES = {"unity": "unity_urp", "urp": "unity_urp",
                  "hdrp": "unity_hdrp"}
UNITY_NAMINGS = ("unity_urp", "unity_hdrp")

NAMING_LABELS = {
    "standard": "Standard (Blender, Substance, Marmoset)",
    "unity_urp": "Unity URP — Lit",
    "unity_hdrp": "Unity HDRP — Lit",
    "unreal": "Unreal Engine",
    "godot": "Godot — StandardMaterial3D",
}

NAMING_NOTES = {
    "standard": "Suffixes explicites (_basecolor, _normal, _orm…). Le choix "
                "neutre : Blender, Substance, Marmoset, archive d'équipe.",
    "unity_urp": "URP Lit n'a pas de Mask Map : il a un Metallic Map "
                 "(R=métal, A=smoothness) et un Occlusion Map (V) séparés. "
                 "L'archive livre UNE texture packée à déposer dans les deux "
                 "emplacements, sRGB décoché.",
    "unity_hdrp": "HDRP Lit lit un Mask Map (R=métal, V=occlusion, "
                  "B=masque de détail, A=smoothness). L'occlusion y est déjà : "
                  "aucun emplacement Occlusion séparé n'existe.",
    "unreal": "Convention Epic : préfixe T_ et suffixes courts (_BC, _N, "
              "_ORM). L'ORM se branche par canal sur un Texture Sample.",
    "godot": "Vocabulaire StandardMaterial3D : albedo, roughness, emission. "
             "L'ORM se branche en choisissant le canal dans chaque section.",
}


def clean_naming(raw) -> str:
    """Convention canonique. Les alias (`unity`) sont résolus ; l'inconnu
    retombe sur `standard` — jamais d'erreur."""
    s = str(raw or "").strip().lower()
    s = NAMING_ALIASES.get(s, s)
    return s if s in NAMINGS else "standard"



EXPORT_FORMATS = ("zip", "glb", "gltf")
RESOLUTIONS = (512, 1024, 2048, 4096)
# resolutions servies uniquement (apercus de galerie) : 128/256 en plus
PREVIEW_RESOLUTIONS = (128, 256, 512, 1024, 2048, 4096)
SEAM_METHODS = ("offset", "mirror")
SOURCE_KINDS = ("prompt", "library", "upload")

# Générateurs autorisés pour la génération depuis un prompt. La route mappe
# ces ids sur le routage FLUX / OpenAI déjà en place (image_providers.py).
MODELS = ("flux", "gpt-image-2", "gpt-image-1", "gpt-image-1-mini",
          "nano-banana")
MODEL_ALIASES = {"gptimage": "gpt-image-1", "gpt-image": "gpt-image-1",
                 "openai": "gpt-image-1", "fal": "flux", "banana": "nano-banana"}

# Gabarit de prompt (aligné sur la barre) — `enhance` est un enrichissement
# LOCAL et gratuit, pas un crédit facturé.
PROMPT_TEMPLATE = ("PBR texture, flat surface, {desc}, top-down view, "
                   "full frame, no objects, no 3D render, no diagram")
PROMPT_ENHANCE = (", seamless tileable, even diffuse lighting, no baked "
                  "shadows, no specular highlights, high micro-detail, "
                  "physically plausible albedo")

ENVS = [
    {"name": "unlit",    "label": "Sans éclairage"},
    {"name": "daylight", "label": "Plein jour"},
    {"name": "studio",   "label": "Studio"},
    {"name": "sunset",   "label": "Coucher de soleil"},
    {"name": "overcast", "label": "Ciel couvert"},
    {"name": "night",    "label": "Nuit"},
    {"name": "dramatic", "label": "Dramatique"},
]
ENV_NAMES = tuple(e["name"] for e in ENVS)

# ── valeurs par défaut (SPEC section 2) ──────────────────────────────────────
# spec = (type, défaut, min, max) ; type "hex" ignore min/max.
_PROPS_SPEC: dict[str, tuple] = {
    "color":              ("hex", "#ffffff"),
    "metallic":           ("f", 0.0, 0.0, 1.0),
    "roughness":          ("f", 1.0, 0.0, 1.0),
    "opacity":            ("f", 1.0, 0.0, 1.0),
    "emissive":           ("hex", "#000000"),
    "emissive_strength":  ("f", 0.0, 0.0, 10.0),
    "clearcoat":          ("f", 0.0, 0.0, 1.0),
    "clearcoat_roughness": ("f", 0.0, 0.0, 1.0),
    "sheen":              ("f", 0.0, 0.0, 1.0),
    "sheen_color":        ("hex", "#ffffff"),
    "transmission":       ("f", 0.0, 0.0, 1.0),
    "ior":                ("f", 1.5, 1.0, 3.0),
    "thickness":          ("f", 0.0, 0.0, 10.0),
    "normal_scale":       ("f", 1.0, 0.0, 4.0),
    "ao_strength":        ("f", 1.0, 0.0, 2.0),
    "displacement":       ("f", 0.0, 0.0, 1.0),
    "tiling":             ("f", 1.0, 0.01, 64.0),
    "rotation":           ("f", 0.0, -360.0, 360.0),
}

_DERIVE_SPEC: dict[str, tuple] = {
    "normal_strength":    ("f", 0.8, 0.0, 4.0),
    "normal_invert_y":    ("b", False),
    # d'où vient le motif de rugosité : "micro" (micro-contraste + cavité,
    # défaut) ou "albedo" (ancienne formule 1 - luminance). Voir pbr_service.
    "roughness_source":   ("e", "micro", ("micro", "albedo")),
    "roughness_bias":     ("f", 0.5, 0.0, 1.0),
    "roughness_contrast": ("f", 0.5, 0.0, 1.0),
    "roughness_invert":   ("b", False),
    "ao_strength":        ("f", 1.0, 0.0, 2.0),
    "ao_radius":          ("f", 4.0, 1.0, 32.0),
    "metallic_mode":      ("e", "auto", ("auto", "none", "luminance")),
    "metallic_threshold": ("f", 0.5, 0.0, 1.0),
    "emissive_threshold": ("f", 0.85, 0.0, 1.0),
    "height_detail":      ("f", 0.5, 0.0, 1.0),
}

# Préréglages de matière (bouton « Appliquer un préréglage »). Ne touchent que
# `props` — la dérivation reste celle de la matière.
PRESETS = [
    {"id": "brushed_metal", "label": "Métal brossé",
     "props": {"color": "#c8ccd2", "metallic": 1.0, "roughness": 0.35,
               "clearcoat": 0.1, "normal_scale": 1.2}},
    {"id": "polished_gold", "label": "Or poli",
     "props": {"color": "#ffd257", "metallic": 1.0, "roughness": 0.12,
               "clearcoat": 0.3}},
    {"id": "plastic", "label": "Plastique",
     "props": {"color": "#e8e8ec", "metallic": 0.0, "roughness": 0.45,
               "clearcoat": 0.6, "clearcoat_roughness": 0.15}},
    {"id": "varnished_wood", "label": "Bois verni",
     "props": {"color": "#8a6a43", "metallic": 0.0, "roughness": 0.4,
               "clearcoat": 0.5, "clearcoat_roughness": 0.2,
               "normal_scale": 1.1}},
    {"id": "glass", "label": "Verre",
     "props": {"color": "#ffffff", "metallic": 0.0, "roughness": 0.05,
               "opacity": 0.25, "transmission": 0.95, "ior": 1.5,
               "thickness": 0.5}},
    {"id": "fabric", "label": "Tissu",
     "props": {"color": "#8d94a8", "metallic": 0.0, "roughness": 0.95,
               "sheen": 0.7, "sheen_color": "#dfe4f0", "normal_scale": 1.4}},
    {"id": "stone", "label": "Pierre",
     "props": {"color": "#9a9a95", "metallic": 0.0, "roughness": 0.9,
               "normal_scale": 1.5, "ao_strength": 1.2, "displacement": 0.3}},
    {"id": "emissive_panel", "label": "Panneau lumineux",
     "props": {"color": "#101014", "metallic": 0.0, "roughness": 0.5,
               "emissive": "#ff8a1f", "emissive_strength": 2.5}},
    {"id": "rubber", "label": "Caoutchouc",
     "props": {"color": "#232326", "metallic": 0.0, "roughness": 1.0,
               "normal_scale": 0.8}},
]

# ── Unity : le MaskMap n'est PAS l'ORM ───────────────────────────────────────
#
# LE DEFAUT QUE CECI CORRIGE. La convention Unity nommait le fichier
# `<n>_MaskMap.png` mais y mettait l'ORM (R=AO, V=rugosité, B=métal). Le Mask
# Map de Unity (HDRP/Lit, et la même image sert le Metallic Map d'URP/Lit) est
# tout autre :
#     R = métallique · V = occlusion ambiante · B = masque de détail ·
#     A = smoothness (= 1 − rugosité)
# Déposée telle quelle dans URP/HDRP, l'ORM intervertit métal et occlusion et
# n'a pas d'alpha : le métal devient de l'AO, la matière sort fausse. On
# produit donc une VRAIE MaskMap RGBA pour Unity (`build_maskmap`) et on garde
# l'ORM pour glTF / Unreal / Godot.
#
# Le canal B (masque de détail) vaut 0 : aucune carte de détail n'est livrée,
# et 0 est la valeur qui la désactive.
MASKMAP = "maskmap"
# maps livrables au-delà des huit du dossier (fabriquées à l'export)
EXPORT_EXTRA_KINDS = (MASKMAP,)

# Conventions de nommage d'export. `{n}` = nom de la matière assaini.
_NAMING_PATTERNS: dict[str, dict[str, str]] = {
    "standard": {"basecolor": "{n}_basecolor.png", "normal": "{n}_normal.png",
                 "roughness": "{n}_roughness.png", "metallic": "{n}_metallic.png",
                 "ao": "{n}_ao.png", "height": "{n}_height.png",
                 "emissive": "{n}_emissive.png", "orm": "{n}_orm.png"},
    # URP : les noms sont ceux des emplacements réels du Lit URP. Le fichier
    # packé s'appelle _MetallicOcclusion parce que c'est LÀ qu'il va — dans les
    # deux emplacements — et surtout pas « MaskMap », qui n'existe pas ici.
    "unity_urp": {"basecolor": "{n}_BaseMap.png", "normal": "{n}_Normal.png",
                  "roughness": "{n}_Roughness.png",
                  "metallic": "{n}_Metallic.png",
                  "ao": "{n}_Occlusion.png", "height": "{n}_Height.png",
                  "emissive": "{n}_Emission.png", "orm": "{n}_orm.png",
                  MASKMAP: "{n}_MetallicOcclusion.png"},
    # HDRP : là, le Mask Map existe vraiment, et il porte l'occlusion.
    "unity_hdrp": {"basecolor": "{n}_BaseMap.png", "normal": "{n}_Normal.png",
                   "roughness": "{n}_Roughness.png",
                   "metallic": "{n}_Metallic.png",
                   "ao": "{n}_Occlusion.png", "height": "{n}_Height.png",
                   "emissive": "{n}_Emissive.png", "orm": "{n}_orm.png",
                   MASKMAP: "{n}_MaskMap.png"},
    # Unreal : préfixe T_ + suffixes courts de la convention Epic.
    "unreal": {"basecolor": "T_{n}_BC.png", "normal": "T_{n}_N.png",
               "roughness": "T_{n}_R.png", "metallic": "T_{n}_M.png",
               "ao": "T_{n}_AO.png", "height": "T_{n}_H.png",
               "emissive": "T_{n}_E.png", "orm": "T_{n}_ORM.png"},
    # Godot : minuscules, vocabulaire StandardMaterial3D.
    "godot": {"basecolor": "{n}_albedo.png", "normal": "{n}_normal.png",
              "roughness": "{n}_roughness.png", "metallic": "{n}_metallic.png",
              "ao": "{n}_ao.png", "height": "{n}_height.png",
              "emissive": "{n}_emission.png", "orm": "{n}_orm.png"},
}

# Ce que chaque moteur BRANCHE réellement, donc ce qui part coché.
#
# LE DEFAUT QUE CECI CORRIGE. Sous Unity, Roughness / Metallic / Occlusion
# restaient cochées alors que le texte disait qu'Unity ne branche que
# BaseMap / MaskMap : 2.5 Mo livrés deux fois, ~15 % de l'archive, et trois
# fichiers qu'aucun slot ne lit. La sélection par défaut suit désormais le
# moteur ; tout le reste reste décochable-recochable à la main.
DEFAULT_EXPORT_MAPS: dict[str, tuple] = {
    "standard": MAP_KINDS,                       # archive complète, neutre
    # URP : la texture packée VA dans Metallic Map ET Occlusion Map. Ce seul
    # fichier remplit donc les deux emplacements — l'archive Unity précédente
    # les laissait tous les deux vides.
    "unity_urp": ("basecolor", "normal", MASKMAP, "height", "emissive"),
    "unity_hdrp": ("basecolor", "normal", MASKMAP, "height", "emissive"),
    "unreal": ("basecolor", "normal", "orm", "height", "emissive"),
    "godot": ("basecolor", "normal", "orm", "height", "emissive"),
}

# ── où chaque fichier VA, dans le moteur visé ────────────────────────────────
#
# Le nom d'un fichier ne branche rien : Unity n'assigne automatiquement que les
# textures embarquées d'un FBX. Le bordereau et le LISEZMOI nomment donc
# l'emplacement de destination, moteur par moteur. C'est vérifiable, et c'est
# ce que la barre de référence ne dit nulle part (« Download GLB », point).
_ENGINE_SLOTS: dict[str, dict[str, str]] = {
    "unity_urp": {
        "basecolor": "Base Map (sRGB coché)",
        MASKMAP: "Metallic Map ET Occlusion Map — la même image dans les deux "
                 "emplacements (R=métal, V=occlusion, A=smoothness), "
                 "sRGB DÉCOCHÉ",
        "normal": "Normal Map (Texture Type = Normal map à l'import ; "
                  "OpenGL +Y, c'est ce qu'attend Unity)",
        "height": "Height Map (parallaxe)",
        "emissive": "Emission Map (cocher Emission)",
        "metallic": "Metallic Map, si tu préfères les fichiers séparés — mais "
                    "sans alpha il n'y a pas de smoothness",
        "ao": "Occlusion Map, si tu préfères les fichiers séparés",
        "roughness": "aucun emplacement : Unity lit la SMOOTHNESS (1 − "
                     "rugosité), déjà dans l'alpha du fichier packé",
        "orm": "aucun emplacement URP : l'ORM est la convention glTF/Unreal",
    },
    "unity_hdrp": {
        "basecolor": "Base Map (sRGB coché)",
        MASKMAP: "Mask Map — R=métal, V=occlusion, B=masque de détail, "
                 "A=smoothness, sRGB DÉCOCHÉ",
        "normal": "Normal Map (Texture Type = Normal map à l'import ; "
                  "OpenGL +Y)",
        "height": "Height Map (Displacement / parallaxe)",
        "emissive": "Emissive Map (cocher Use Emission Intensity)",
        "metallic": "aucun emplacement séparé : HDRP lit le canal R du "
                    "Mask Map",
        "ao": "aucun emplacement séparé : HDRP lit le canal V du Mask Map",
        "roughness": "aucun emplacement : la smoothness (1 − rugosité) est "
                     "dans l'alpha du Mask Map",
        "orm": "aucun emplacement HDRP : l'ORM est la convention glTF/Unreal",
    },
    "unreal": {
        "basecolor": "Base Color",
        "normal": "Normal (Texture Sample, compression Normalmap)",
        "orm": "un Texture Sample, sRGB décoché : R → Ambient Occlusion, "
               "V → Roughness, B → Metallic",
        "height": "World Displacement / Parallax Occlusion",
        "emissive": "Emissive Color",
        "roughness": "Roughness, si tu branches les fichiers séparés",
        "metallic": "Metallic, si tu branches les fichiers séparés",
        "ao": "Ambient Occlusion, si tu branches les fichiers séparés",
    },
    "godot": {
        "basecolor": "Albedo > Texture",
        "normal": "Normal Map > Texture (activer Normal Map)",
        "orm": "Ambient Occlusion (canal Red), Roughness (canal Green), "
               "Metallic (canal Blue) — la même texture, canal choisi dans "
               "chaque section",
        "height": "Height > Texture (activer Height)",
        "emissive": "Emission > Texture (activer Emission)",
        "roughness": "Roughness > Texture, si tu branches les fichiers séparés",
        "metallic": "Metallic > Texture, si tu branches les fichiers séparés",
        "ao": "Ambient Occlusion > Texture, si tu branches les fichiers séparés",
    },
}


def engine_slot(kind: str, naming: str = "standard") -> str:
    """L'emplacement de destination de ce fichier dans le moteur visé
    (chaîne vide pour la convention neutre)."""
    return (_ENGINE_SLOTS.get(clean_naming(naming)) or {}).get(kind, "")

# Rôle de chaque fichier, DIT PAR LE CODE QUI L'ÉCRIT (l'écran ne le devine
# plus). Le rôle de l'ORM et du MaskMap dépend de la convention : c'est
# exactement là que la version précédente mentait.
_ROLE_COMMON = {
    "basecolor": "Couleur de base (albédo), sRGB",
    "normal": "Relief tangent-space, OpenGL (+Y vers le haut)",
    "roughness": "Rugosité, 0 = miroir, 1 = mat",
    "metallic": "Métallicité, 0 = diélectrique, 1 = métal",
    "ao": "Occlusion ambiante de cavité",
    "height": "Hauteur / displacement",
    "emissive": "Lumière émise, sRGB",
    "orm": "Packée R=AO V=rugosité B=métal (glTF / Unreal / Godot)",
    MASKMAP: "Packée Unity : R=métal V=occlusion B=détail A=smoothness",
}
_ROLE_BY_NAMING = {
    "unity_urp": {
        "normal": "Normal Map Unity (OpenGL ; cocher « Fix now » à l'import "
                  "si Unity le propose)",
        MASKMAP: "R=métal V=occlusion B=détail A=smoothness — remplit à elle "
                 "seule Metallic Map et Occlusion Map",
        "orm": "Packée R=AO V=rugosité B=métal — convention glTF/Unreal, "
               "URP ne la lit pas",
        "roughness": "Rugosité — Unity lit la smoothness (1 − rugosité), "
                     "déjà dans l'alpha du fichier packé",
        "metallic": "Métallicité — redondante : le fichier packé la porte "
                    "dans son canal R (et lui a l'alpha smoothness)",
        "ao": "Occlusion — redondante : le fichier packé la porte dans son "
              "canal V"},
    "unity_hdrp": {
        "normal": "Normal Map Unity (OpenGL ; cocher « Fix now » à l'import "
                  "si Unity le propose)",
        MASKMAP: "Mask Map HDRP : R=métal V=occlusion B=détail A=smoothness",
        "orm": "Packée R=AO V=rugosité B=métal — convention glTF/Unreal, "
               "HDRP ne la lit pas",
        "roughness": "Rugosité — HDRP lit la smoothness dans l'alpha du "
                     "Mask Map",
        "metallic": "Métallicité — redondante : Mask Map, canal R",
        "ao": "Occlusion — redondante : Mask Map, canal V (HDRP n'a pas "
              "d'emplacement Occlusion séparé)"},
    "unreal": {"roughness": "Rugosité — redondante avec l'ORM (canal V)",
               "metallic": "Métallicité — redondante avec l'ORM (canal B)",
               "ao": "Occlusion — redondante avec l'ORM (canal R)"},
    "godot": {"roughness": "Rugosité — redondante avec l'ORM (canal V)",
              "metallic": "Métallicité — redondante avec l'ORM (canal B)",
              "ao": "Occlusion — redondante avec l'ORM (canal R)"},
}


def map_role(kind: str, naming: str = "standard") -> str:
    """Ce que ce fichier est, pour CE moteur."""
    per = _ROLE_BY_NAMING.get(clean_naming(naming)) or {}
    return per.get(kind) or _ROLE_COMMON.get(kind, "")


def default_export_maps(naming: str = "standard") -> list[str]:
    return list(DEFAULT_EXPORT_MAPS.get(clean_naming(naming),
                                        DEFAULT_EXPORT_MAPS["standard"]))


def naming_catalog() -> list[dict]:
    """Les conventions d'export, avec leur libellé, leur note VÉRIFIÉE dans la
    documentation du moteur, et la liste des emplacements que l'archive
    remplit. C'est la source de vérité de l'écran : plus aucun texte de
    convention n'est écrit en dur côté client."""
    out = []
    for name in NAMINGS:
        defaults = default_export_maps(name)
        pat = _NAMING_PATTERNS.get(name, _NAMING_PATTERNS["standard"])
        slots = [{"kind": k, "file": pat.get(k, f"{k}.png"),
                  "slot": engine_slot(k, name)}
                 for k in defaults if engine_slot(k, name)]
        out.append({"id": name, "label": NAMING_LABELS.get(name, name),
                    "note": NAMING_NOTES.get(name, ""),
                    "default_maps": defaults, "slots": slots})
    return out


def build_maskmap(maps: dict) -> Image.Image | None:
    """Mask Map Unity RGBA : R=métallique, V=occlusion, B=détail (0),
    A=smoothness = 255 − rugosité.

    Prend ce qui est disponible : les maps séparées, sinon l'ORM (R=AO,
    V=rugosité, B=métal) dont on redistribue les canaux. Retourne None s'il
    n'y a de quoi remplir aucun canal utile."""
    metal = maps.get("metallic")
    ao = maps.get("ao")
    rough = maps.get("roughness")
    orm = maps.get("orm")
    if orm is not None:
        o_ao, o_r, o_m = orm.convert("RGB").split()
        metal = metal if metal is not None else o_m
        ao = ao if ao is not None else o_ao
        rough = rough if rough is not None else o_r
    if metal is None and ao is None and rough is None:
        return None
    size = next(im.size for im in (metal, ao, rough) if im is not None)
    metal = metal.convert("L") if metal is not None else Image.new("L", size, 0)
    ao = ao.convert("L") if ao is not None else Image.new("L", size, 255)
    rough = rough.convert("L") if rough is not None else Image.new("L", size, 255)
    detail = Image.new("L", size, 0)          # aucune carte de détail livrée
    smooth = ImageChops.invert(rough)         # smoothness = 1 − rugosité
    return Image.merge("RGBA", (metal, ao, detail, smooth))


# ── coercition « jamais de 500 » ─────────────────────────────────────────────

def _coerce_float(raw, default: float, lo: float, hi: float) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if v != v or v in (float("inf"), float("-inf")):   # NaN / inf
        return float(default)
    return round(min(hi, max(lo, v)), 6)


def _coerce_bool(raw, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("1", "true", "vrai", "yes", "oui", "on"):
            return True
        if s in ("0", "false", "faux", "no", "non", "off", ""):
            return False
    return bool(default)


def _coerce_hex(raw, default: str) -> str:
    """#rrggbb minuscule. Accepte « rrggbb », « #RGB », rejette le reste."""
    if not isinstance(raw, str):
        return default
    s = raw.strip().lower().lstrip("#")
    if len(s) == 3 and all(c in "0123456789abcdef" for c in s):
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or any(c not in "0123456789abcdef" for c in s):
        return default
    return "#" + s


def _coerce_enum(raw, default: str, allowed: tuple) -> str:
    s = str(raw).strip().lower() if raw is not None else ""
    return s if s in allowed else default


def _apply_spec(spec: dict, base: dict | None, patch: dict | None) -> dict:
    """Défauts <- base <- patch, chaque valeur repassée par sa validation.
    Les clés inconnues sont ignorées ; un `patch` non-dict est ignoré."""
    src: dict = {}
    for layer in (base, patch):
        if isinstance(layer, dict):
            src.update({k: v for k, v in layer.items() if k in spec})
    out: dict = {}
    for key, rule in spec.items():
        kind, default = rule[0], rule[1]
        raw = src.get(key, default)
        if kind == "f":
            out[key] = _coerce_float(raw, default, rule[2], rule[3])
        elif kind == "b":
            out[key] = _coerce_bool(raw, default)
        elif kind == "hex":
            out[key] = _coerce_hex(raw, default)
        else:                                    # "e" — liste blanche
            out[key] = _coerce_enum(raw, default, rule[2])
    return out


def default_props() -> dict:
    return _apply_spec(_PROPS_SPEC, None, None)


def default_derive() -> dict:
    return _apply_spec(_DERIVE_SPEC, None, None)


def merge_props(base: dict | None, patch: dict | None) -> dict:
    """Fusion PARTIELLE : ce que le patch ne mentionne pas garde sa valeur."""
    return _apply_spec(_PROPS_SPEC, base, patch)


def merge_derive(base: dict | None, patch: dict | None) -> dict:
    return _apply_spec(_DERIVE_SPEC, base, patch)


def clean_res(raw, default: int = 2048) -> int:
    """Résolution de la liste blanche la plus proche (jamais d'erreur)."""
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    if v in RESOLUTIONS:
        return v
    return min(RESOLUTIONS, key=lambda r: abs(r - v))


def clean_preview_res(raw, default: int = 512) -> int:
    """Comme clean_res, mais pour ce qui n'est QUE servi (aperçus de galerie,
    posters de carte) : on autorise 128 et 256, trop petits pour être une
    resolution de stockage mais decisifs pour la galerie. Un GLB de carte en
    256 pese ~4x moins qu'en 512 — a 60 cartes, c'est la difference entre une
    galerie fluide et une page qui rame."""
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    if v in PREVIEW_RESOLUTIONS:
        return v
    return min(PREVIEW_RESOLUTIONS, key=lambda r: abs(r - v))


# ── cache disque des GLB d'apercu ────────────────────────────────────────────
# Reconstruire un GLB de carte coute ~0.9 s (resize PIL + encodage PNG des 8
# maps). Une galerie de 60 cartes rechargee a chaque scroll ecroulerait le
# backend : on garde les derniers rendus sur disque, cles par (maillage,
# resolution, proprietes, mtime des maps).

def preview_cache_key(mat: dict, mesh: str, res: int) -> str:
    d = material_dir(mat["id"])
    stamps = []
    for kind in MAP_KINDS:
        f = d / f"{kind}.png"
        try:
            stamps.append(f"{kind}:{int(f.stat().st_mtime_ns)}")
        except OSError:
            continue
    payload = json.dumps({
        "mesh": mesh, "res": res,
        "props": mat.get("props") or {},
        "maps": stamps,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


def _preview_cache_dir(mid: str, create: bool = False) -> Path:
    d = material_dir(mid, create=create) / "_cache"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def preview_cache_get(mid: str, key: str) -> bytes | None:
    if not is_valid_mid(mid) or not re.fullmatch(r"[0-9a-f]{1,40}", key or ""):
        return None
    p = _preview_cache_dir(mid) / f"p_{key}.glb"
    try:
        return p.read_bytes() if p.is_file() else None
    except OSError:
        return None


def preview_cache_put(mid: str, key: str, data: bytes, keep: int = 12) -> None:
    if not is_valid_mid(mid) or not re.fullmatch(r"[0-9a-f]{1,40}", key or ""):
        return
    try:
        d = _preview_cache_dir(mid, create=True)
        tmp = d / f"p_{key}.tmp"
        tmp.write_bytes(data)
        tmp.replace(d / f"p_{key}.glb")
        files = sorted(d.glob("p_*.glb"), key=lambda f: f.stat().st_mtime,
                       reverse=True)
        for old in files[keep:]:
            old.unlink(missing_ok=True)
    except OSError as e:
        logger.debug(f"cache apercu {mid} ignore: {e}")


def clean_name(raw, fallback: str = "matière") -> str:
    n = str(raw or "").strip().replace("\n", " ").replace("\r", " ")
    return (n[:80] or fallback)


def clean_model(raw) -> str:
    m = str(raw or "").strip().lower()
    m = MODEL_ALIASES.get(m, m)
    return m if m in MODELS else "flux"


def build_full_prompt(desc: str, enhance: bool = False) -> str:
    p = PROMPT_TEMPLATE.format(desc=str(desc or "").strip())
    return p + PROMPT_ENHANCE if enhance else p


# ── identité et chemins ──────────────────────────────────────────────────────

def is_valid_mid(mid) -> bool:
    return bool(isinstance(mid, str) and MID_RE.match(mid))


def materials_root() -> Path:
    from app.config import settings
    p = settings.outputs_path / "materials"
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_mid() -> str:
    root = materials_root()
    for _ in range(64):
        mid = "mat_" + uuid4().hex[:8]
        if not (root / mid).exists():
            return mid
    raise RuntimeError("Impossible d'allouer un identifiant de matière")


def material_dir(mid: str, create: bool = False) -> Path:
    """Dossier d'une matière. Refuse tout `mid` hors ``^mat_[0-9a-f]{8}$``.

    Le motif interdit déjà séparateurs, points et chemins absolus ; la
    vérification de confinement qui suit est la ceinture par-dessus les
    bretelles (même doctrine que l'audit sécurité : basename + confinement).
    """
    if not is_valid_mid(mid):
        raise ValueError(f"Identifiant de matière invalide: {mid!r}")
    root = materials_root()
    p = (root / mid).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError(f"Identifiant de matière invalide: {mid!r}")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def map_path(mid: str, kind: str) -> Path:
    """Chemin d'une map. `kind` est une liste blanche stricte."""
    k = str(kind or "").strip().lower()
    if k not in MAP_KINDS:
        raise ValueError(f"Map inconnue: {kind!r}")
    return material_dir(mid) / f"{k}.png"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── objet Material ───────────────────────────────────────────────────────────

def normalize_material(raw: dict | None, mid: str | None = None) -> dict:
    """Objet Material complet à partir de n'importe quoi (meta.json abîmé,
    corps client partiel…). Ne lève jamais."""
    raw = raw if isinstance(raw, dict) else {}
    mid = mid or raw.get("id")
    src = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    kind = _coerce_enum(src.get("kind"), "prompt", SOURCE_KINDS)
    model = src.get("model")
    model = str(model).strip().lower() if isinstance(model, str) and model.strip() else None
    filename = src.get("filename")
    filename = Path(str(filename)).name if isinstance(filename, str) and filename.strip() else None

    seam = raw.get("seam") if isinstance(raw.get("seam"), dict) else {}
    seam_out = {}
    # `before` / `after` = le score de bord historique (pixel_ops.seam_score).
    # `ratio` / `grade` = le rapport de couture APRÈS correction, le seul des
    # quatre qui décide si la matière est utilisable (voir pbr_service).
    for k in ("before", "after", "ratio"):
        try:
            seam_out[k] = round(float(seam.get(k)), 2)
        except (TypeError, ValueError):
            seam_out[k] = None
    grade = seam.get("grade")
    seam_out["grade"] = (str(grade) if isinstance(grade, str) and grade
                         else None)

    maps = raw.get("maps")
    maps = [k for k in MAP_KINDS if isinstance(maps, list) and k in maps]

    # Statistiques par map (moyenne/min/max + « porte-t-elle une information »).
    # Écrites à la dérivation, relues telles quelles : c'est ce qui permet à
    # l'écran d'annoncer un compte honnête au lieu d'un « 8 » de principe.
    stats_in = raw.get("map_stats")
    map_stats = {}
    if isinstance(stats_in, dict):
        for k in MAP_KINDS:
            v = stats_in.get(k)
            if isinstance(v, dict):
                map_stats[k] = v

    created = raw.get("created")
    created = created if isinstance(created, str) and created else _now_iso()

    props_out = merge_props(raw.get("props"), None)
    # `render` n'est jamais relu du client : il est RECALCULÉ à chaque
    # normalisation à partir des props courantes, sinon un bloc périmé pourrait
    # annoncer un facteur qui n'est plus celui du GLB. Les valeurs effectives
    # mesurées y sont réinjectées par `refresh_report` (qui, lui, a les maps).
    eff_in = ((raw.get("render") or {}).get("effective")
              if isinstance(raw.get("render"), dict) else None)
    render = render_block(props_out)
    if isinstance(eff_in, dict):
        for k in ("metallic", "roughness"):
            try:
                render["effective"][k] = round(float(eff_in[k]), 3)
                render["measured"] = bool((raw.get("render") or {})
                                          .get("measured"))
            except (KeyError, TypeError, ValueError):
                pass

    return {
        "id": mid,
        "name": clean_name(raw.get("name"), fallback="Matière"),
        "prompt": str(raw.get("prompt") or "")[:2000],
        "full_prompt": str(raw.get("full_prompt") or "")[:4000],
        "source": {"kind": kind, "model": model, "filename": filename},
        "res": clean_res(raw.get("res")),
        "seamless": bool(raw.get("seamless", True)),
        "seam": seam_out,
        "maps": maps,
        "map_stats": map_stats,
        "maps_informative": sum(1 for v in map_stats.values()
                                if v.get("informative")),
        # maps dont l'information duplique la luminance de la base color
        "maps_dependent": sum(1 for v in map_stats.values()
                              if v.get("dependent")),
        "props": props_out,
        "render": render,
        "derive": merge_derive(raw.get("derive"), None),
        "created": created,
        "thumb": bool(raw.get("thumb")),
    }


def create_material(*, name: str, prompt: str = "", full_prompt: str = "",
                    source: dict | None = None, res: int = 2048,
                    seamless: bool = True, seam: dict | None = None,
                    props: dict | None = None, derive: dict | None = None,
                    mid: str | None = None) -> dict:
    """Crée le dossier + meta.json d'une nouvelle matière et la retourne."""
    mid = mid or new_mid()
    material_dir(mid, create=True)
    mat = normalize_material({
        "id": mid, "name": name, "prompt": prompt, "full_prompt": full_prompt,
        "source": source or {}, "res": res, "seamless": seamless,
        "seam": seam or {}, "maps": [], "props": props, "derive": derive,
        "created": _now_iso(), "thumb": False,
    }, mid)
    return write_material(mat)


def write_material(mat: dict) -> dict:
    """Écrit meta.json (atomique : tmp + replace)."""
    mid = mat.get("id")
    d = material_dir(mid, create=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(mat, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(d / "meta.json")
    return mat


def read_material(mid: str) -> dict | None:
    """Objet Material, ou None si le dossier/meta est absent. Un meta.json
    corrompu est normalisé plutôt que de faire tomber l'appelant."""
    try:
        d = material_dir(mid)
    except ValueError:
        return None
    f = d / "meta.json"
    if not f.is_file():
        return None
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning(f"materials: meta.json illisible pour {mid}: {e}")
        raw = {}
    mat = normalize_material(raw, mid)
    # le disque fait foi pour les maps et la vignette
    mat["maps"] = [k for k in MAP_KINDS if (d / f"{k}.png").is_file()]
    mat["thumb"] = thumb_is_current(d)
    return mat


def list_materials() -> list[dict]:
    """Toutes les matières, plus récente d'abord.

    `created` n'a qu'une précision d'une seconde (format du SPEC) : deux
    matières créées dans la même seconde seraient départagées au hasard, d'où
    le mtime de meta.json en clé secondaire.
    """
    rows = []
    for d in materials_root().iterdir():
        if not d.is_dir() or not is_valid_mid(d.name):
            continue
        m = read_material(d.name)
        if not m:
            continue
        try:
            mtime = (d / "meta.json").stat().st_mtime
        except OSError:
            mtime = 0.0
        rows.append((m.get("created") or "", mtime, m))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return [r[2] for r in rows]


def duplicate_material(mid: str) -> dict | None:
    """Copie intégrale (maps + vignette) sous un nouveau mid."""
    src_mat = read_material(mid)
    if src_mat is None:
        return None
    src = material_dir(mid)
    new = new_mid()
    dst = material_dir(new, create=True)
    for f in src.iterdir():
        if f.is_file() and f.name != "meta.json.tmp":
            shutil.copy2(f, dst / f.name)
    mat = dict(src_mat)
    mat["id"] = new
    mat["name"] = clean_name(f"{src_mat['name']} (copie)")
    mat["created"] = _now_iso()
    return write_material(mat)


def delete_material(mid: str) -> bool:
    try:
        d = material_dir(mid)
    except ValueError:
        return False
    if not d.is_dir():
        return False
    shutil.rmtree(d, ignore_errors=True)
    return not d.exists()


# ── maps sur disque ──────────────────────────────────────────────────────────

def _as_mode(img: Image.Image, kind: str) -> Image.Image:
    mode = MAP_MODES[kind]
    return img if img.mode == mode else img.convert(mode)


def save_maps(mid: str, maps: dict) -> list[str]:
    """Écrit les maps fournies (PIL) dans le dossier. Retourne les kinds
    réellement écrits, dans l'ordre canonique."""
    d = material_dir(mid, create=True)
    written = []
    for kind in MAP_KINDS:
        img = maps.get(kind)
        if img is None:
            continue
        _as_mode(img, kind).save(d / f"{kind}.png", format="PNG",
                                 optimize=False)
        written.append(kind)
    return written


def load_maps(mid: str, kinds=None) -> dict:
    """Maps présentes sur disque, en PIL."""
    d = material_dir(mid)
    want = [k for k in MAP_KINDS if kinds is None or k in kinds]
    out = {}
    for kind in want:
        f = d / f"{kind}.png"
        if f.is_file():
            with Image.open(f) as im:
                out[kind] = _as_mode(im.copy(), kind)
    return out


def write_source(mid: str, img: Image.Image) -> Path:
    """Image de base AVANT raccord — traçabilité (SPEC section 1)."""
    d = material_dir(mid, create=True)
    p = d / "source.png"
    img.convert("RGB").save(p, format="PNG")
    return p


def _mesh_version() -> int:
    """Version de la géométrie/UV en cours. Import différé : gltf_builder
    importe des utilitaires d'ici, un import au sommet ferait un cycle."""
    try:
        from app.services.gltf_builder import MESH_VERSION
        return int(MESH_VERSION)
    except Exception:
        return 0


def thumb_is_current(d) -> bool:
    """Une vignette est un RENDU 3D figé : elle ne vaut que pour la géométrie
    qui l'a produite. Les vignettes capturées avant la correction du placage
    (MESH_VERSION 2) montraient la matière EN MIROIR ; servies telles quelles,
    elles remettaient le défaut à l'écran sur la carte de galerie dès que la
    scène 3D n'était pas montée (case « aperçus 3D vivants » décochée, carte
    hors budget, avant chargement). On les tient donc pour absentes : la carte
    retombe alors sur la couleur de base, qui est plate et juste."""
    p = d / "thumb.png"
    if not p.is_file():
        return False
    try:
        got = int((d / "thumb.mv").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return got == _mesh_version()


def write_thumb(mid: str, data: bytes) -> tuple[bool, str]:
    """Vignette 512x512 poussée par le client (rendu du viewport).
    Retour (ok, message) — jamais d'exception sur données pourries."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            thumb = im.convert("RGB")
    except Exception as e:
        return False, f"PNG illisible: {e}"
    if thumb.size != (512, 512):
        thumb = thumb.resize((512, 512), Image.LANCZOS)
    d = material_dir(mid, create=True)
    thumb.save(d / "thumb.png", format="PNG")
    # on estampille la géométrie qui a produit ce rendu (cf. thumb_is_current)
    (d / "thumb.mv").write_text(str(_mesh_version()), encoding="utf-8")
    return True, "ok"


def resize_maps(maps: dict, res: int) -> dict:
    """Redimensionne un jeu de maps. Délègue à ``pbr_service.resize_maps``
    (qui re-normalise la normale) quand le module est présent ; sinon
    repli PIL simple pour que l'export reste possible.

    La liste blanche utilisée ici est celle des tailles SERVIES (128/256 en
    plus) : les routes d'export, elles, filtrent déjà `res` par ``clean_res``
    avant d'arriver ici. Sans cela un aperçu de carte demandé en 256 remontait
    silencieusement à 512 — soit 4x le poids, à chaque carte."""
    res = clean_preview_res(res, 1024)
    if not maps:
        return {}
    try:
        from app.services import pbr_service as PBR
        fn = getattr(PBR, "resize_maps", None)
        if callable(fn):
            out = fn(maps, res)
            if isinstance(out, dict) and out:
                return out
    except Exception as e:          # module absent ou en cours d'écriture
        logger.warning(f"materials: resize_maps via pbr_service indisponible "
                       f"({e}) — repli PIL")
    out = {}
    for kind, img in maps.items():
        if img.size == (res, res):
            out[kind] = img
            continue
        f = Image.LANCZOS if kind in ("basecolor", "emissive") else Image.BICUBIC
        out[kind] = img.resize((res, res), f)
    return out


# ── niveaux, statistiques, raccord : une seule source de vérité ──────────────
#
# `bake_levels` cuit `props["metallic"]` / `props["roughness"]` dans les maps.
# TOUT ce qui sort d'ici passe par lui — vignette de map servie par l'API, GLB
# d'aperçu, GLB/glTF exporté, PNG du ZIP — de sorte que l'écran et le moteur
# reçoivent le même pixel. Il n'y a pas de chemin qui l'oublie : c'est la
# condition pour que « ce qu'on voit soit ce qui sort ».

def bake_levels(maps: dict, props: dict | None) -> dict:
    """Applique les niveaux de matière aux maps (délègue à pbr_service).
    Repli : les maps telles quelles, jamais d'exception."""
    if not maps:
        return maps
    try:
        from app.services import pbr_service as PBR
        fn = getattr(PBR, "bake_levels", None)
        if callable(fn):
            out = fn(maps, props)
            if isinstance(out, dict) and out:
                return out
    except Exception as e:
        logger.warning(f"materials: bake_levels indisponible ({e})")
    return maps


def natural_levels(maps: dict) -> dict:
    """{"metallic": m, "roughness": r} = la moyenne que ces maps portent
    naturellement. À la création d'une matière, c'est le seul réglage honnête :
    le curseur montre ce que la texture vaut, et cuire ce niveau-là ne modifie
    aucun pixel."""
    try:
        from app.services import pbr_service as PBR
    except Exception:
        return {}
    out = {}
    for kind in ("metallic", "roughness"):
        img = maps.get(kind)
        if img is not None:
            out[kind] = PBR.natural_level(img)
    return out


def map_stats(mid: str, props: dict | None = None, maps: dict | None = None
              ) -> dict:
    """Statistiques des maps TELLES QU'ELLES SERONT LIVRÉES (donc après
    `bake_levels`). Retourne le bloc à écrire dans meta.json."""
    try:
        from app.services import pbr_service as PBR
    except Exception as e:
        logger.warning(f"materials: map_stats indisponible ({e})")
        return {}
    src = maps if maps else load_maps(mid)
    if not src:
        return {}
    # la base color sert de référence à la corrélation : une map qui la
    # recopie ne porte pas d'information indépendante, et le rapport le dit.
    base = src.get("basecolor")
    if base is None:
        p = material_dir(mid) / "basecolor.png"
        if p.is_file():
            with Image.open(p) as im:
                base = im.copy()
    out = dict(PBR.map_report(bake_levels(src, props), base).get("maps") or {})
    # Motif BRUT des maps à niveau : il ne dépend pas des props, et il permet
    # de recalculer exactement la map cuite quand le curseur bouge, sans
    # relire 16 M pixels (voir pbr_service.level_stats).
    for kind, band in (("metallic", None), ("roughness", None),
                       ("orm", 1)):
        img = src.get(kind)
        if img is None or kind not in out:
            continue
        ch = img.convert("RGB").split()[band] if band is not None else img
        if ch.mode != "L":
            ch = ch.convert("L")
        # L'HISTOGRAMME du motif, pas seulement ses quantiles : c'est lui qui
        # permet a `pbr_service.level_mean` de donner la moyenne EXACTE des
        # octets cuits quand le curseur bouge. Sans lui, le bloc `render`
        # republiait la valeur de la derniere derivation (mesure : curseur
        # deplace a 0.25, `effective` annoncait encore 0.485).
        out[kind] = dict(out[kind], pattern=PBR.stats(ch),
                         pattern_hist=[int(v) for v in ch.histogram()[:256]])
    return out


def seam_report(mid: str) -> dict:
    """Rapport de raccord de la basecolor sur disque (rapport + verdict)."""
    try:
        from app.services import pbr_service as PBR
    except Exception as e:
        logger.warning(f"materials: seam_report indisponible ({e})")
        return {}
    p = map_path(mid, "basecolor")
    if not p.is_file():
        return {}
    with Image.open(p) as im:
        return PBR.seam_report(im.copy())


def refresh_report(mat: dict, maps: dict | None = None) -> dict:
    """Recalcule `map_stats` et le volet `ratio`/`grade` du raccord, puis rend
    la matière à jour (sans l'écrire). Utilisé après chaque dérivation et par
    le rattrapage des matières antérieures."""
    mid = mat.get("id")
    mat = dict(mat)
    stats = map_stats(mid, mat.get("props"), maps)
    if stats:
        mat["map_stats"] = stats
        mat["maps_informative"] = sum(1 for v in stats.values()
                                      if v.get("informative"))
        mat["maps_dependent"] = sum(1 for v in stats.values()
                                    if v.get("dependent"))
    # valeurs effectives MESURÉES sur les maps cuites, pas recopiées des props
    src = maps if maps else load_maps(mid, ["roughness", "metallic", "orm"])
    if src:
        mat["render"] = render_block(mat.get("props"), src)
    rep = seam_report(mid)
    if rep:
        seam = dict(mat.get("seam") or {})
        seam["ratio"] = rep.get("ratio")
        seam["grade"] = rep.get("grade")
        mat["seam"] = seam
    return mat


# ── PNG 16 bits (stdlib, Pillow ne sait pas écrire du RVB 16 bits) ───────────

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _png16(img: Image.Image) -> bytes:
    """PNG profondeur 16 (gris ou RVB) depuis une image 8 bits.

    Les maps sont dérivées en 8 bits (contrainte PIL pur du SPEC) : la
    conversion ``v -> v*257`` produit un vrai conteneur 16 bits — le format
    qu'attendent Unreal/Unity pour le displacement — sans inventer de
    précision. Dupliquer chaque octet donne exactement v*257 en big-endian.
    """
    nch = 3 if img.mode == "RGB" else 1
    color_type = 2 if nch == 3 else 0
    w, h = img.size
    src = img.tobytes()
    stride = w * nch
    raw = bytearray()
    for y in range(h):
        row = src[y * stride:(y + 1) * stride]
        dup = bytearray(len(row) * 2)
        dup[0::2] = row            # octet fort
        dup[1::2] = row            # octet faible -> v*256 + v = v*257
        raw.append(0)              # filtre None
        raw += dup
    ihdr = struct.pack(">IIBBBBB", w, h, 16, color_type, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + _png_chunk(b"IEND", b""))


def png_bytes(img: Image.Image, kind: str, bits: int = 8) -> bytes:
    """PNG d'une map. `bits=16` n'est honoré que pour height et normal
    (les seules maps où la profondeur change quelque chose au rendu)."""
    img = _as_mode(img, kind)
    if int(bits or 8) >= 16 and kind in ("height", "normal"):
        return _png16(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


# ── export ───────────────────────────────────────────────────────────────────

def slug(name: str, fallback: str = "material") -> str:
    """Nom de fichier sûr pour un moteur de jeu : ASCII, sans espace.
    Les accents sont translittérés (« rouillé » -> « rouille ») plutôt que
    supprimés, sinon les noms français partent en charpie."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return (s[:48] or fallback)


def naming_map(naming: str, name: str) -> dict:
    """kind -> nom de fichier, selon la convention demandée."""
    pat = _NAMING_PATTERNS.get(clean_naming(naming),
                               _NAMING_PATTERNS["standard"])
    n = slug(name)
    return {k: v.format(n=n) for k, v in pat.items()}


def export_filename(mat: dict, fmt: str, naming: str = "standard") -> str:
    n = slug(mat.get("name"), fallback=mat.get("id") or "material")
    ext = {"zip": "zip", "glb": "glb", "gltf": "gltf"}.get(fmt, "zip")
    naming = clean_naming(naming)
    if fmt == "zip" and naming != "standard":
        return f"{n}_{naming}.zip"
    return f"{n}.{ext}"


# ── comment le scalaire se compose avec la map, DIT NOIR SUR BLANC ───────────
#
# LE DEFAUT QUE CECI CORRIGE. glTF pose
#     rugosité effective  = roughnessFactor x metallicRoughnessTexture.G
#     métallicité effective = metallicFactor x metallicRoughnessTexture.B
# Nous cuisons le niveau dans la map et mettons les facteurs à 1.0 — mais rien
# ne le DISAIT. `material.json` publiait `props.roughness = 0.25` à côté d'un
# `roughness.png` de moyenne 0.251 : un script d'import qui lit l'un et branche
# l'autre applique 0.25 x 0.251 = 0.063 et sort une matière quasi miroir. Le
# bloc ci-dessous accompagne désormais la matière partout (meta.json, réponses
# API, material.json de l'archive) : il donne le facteur à poser, la valeur
# effective MESURÉE sur les octets livrés, et la formule.
RENDER_NOTE = ("Les niveaux sont CUITS dans les maps : metallicFactor et "
               "roughnessFactor doivent rester à 1.0. glTF calcule "
               "rugosité = roughnessFactor x texture.G et "
               "métallicité = metallicFactor x texture.B — appliquer en plus "
               "la valeur du curseur reviendrait à la compter deux fois.")


def public_material(mat: dict) -> dict:
    """La matière SANS sa comptabilité interne.

    `map_stats[k]["pattern_hist"]` est l'histogramme du motif brut : il sert au
    backend à recalculer la moyenne exacte des octets cuits quand le curseur
    bouge, il n'a rien à faire dans l'archive livrée (256 entiers x 3 maps =
    9.4 ko de bruit dans un fichier qu'un humain ouvre)."""
    out = dict(mat)
    stats = out.get("map_stats")
    if isinstance(stats, dict):
        out["map_stats"] = {
            k: ({kk: vv for kk, vv in v.items() if kk != "pattern_hist"}
                if isinstance(v, dict) else v)
            for k, v in stats.items()}
    return out


def render_block(props: dict | None = None, maps: dict | None = None,
                 baked: bool = False) -> dict:
    """Contrat de composition scalaire x texture, avec les valeurs effectives
    MESURÉES quand les maps sont fournies (sinon celles réglées).

    `baked=True` quand `maps` a déjà traversé `bake_levels` — c'est le cas des
    maps livrées : on mesure alors les octets exacts qui partent."""
    p = props if isinstance(props, dict) else {}
    eff = {}
    if maps:
        try:
            from app.services import pbr_service as PBR
            eff = PBR.effective_levels(
                maps if baked else bake_levels(maps, p)) or {}
        except Exception as e:                      # jamais bloquant
            logger.warning(f"materials: effective_levels indisponible ({e})")
    out = {
        "levels_baked": ["metallic", "roughness"],
        "metallicFactor": 1.0,
        "roughnessFactor": 1.0,
        "formula": "roughness = roughnessFactor x metallicRoughnessTexture.G ; "
                   "metalness = metallicFactor x metallicRoughnessTexture.B",
        "effective": {
            "metallic": eff.get("metallic",
                                round(float(p.get("metallic", 0.0)), 3)),
            "roughness": eff.get("roughness",
                                 round(float(p.get("roughness", 1.0)), 3)),
        },
        "measured": bool(eff),
        "note": RENDER_NOTE,
    }
    return out


def _readme(mat: dict, files: dict, bits: int, naming: str, res: int) -> str:
    seam = mat.get("seam") or {}
    before, after = seam.get("before"), seam.get("after")
    ratio, grade = seam.get("ratio"), seam.get("grade")
    props = mat.get("props") or {}
    naming = clean_naming(naming)
    render = mat.get("render") or render_block(props)
    eff = render.get("effective") or {}
    lines = [
        f"Matière : {mat.get('name')}  ({mat.get('id')})",
        f"Générée par Deepotus Material Forge le {mat.get('created')}",
        "",
        f"Résolution : {res}x{res}",
        f"Convention de nommage : {naming} — "
        f"{NAMING_LABELS.get(naming, naming)}",
        f"Profondeur : 8 bits (height et normal en {bits} bits)",
        "",
        NAMING_NOTES.get(naming, ""),
        "",
        "Raccord de tuile, APRÈS correction :",
        f"  rapport de couture : {ratio if ratio is not None else 'n/d'}"
        f"  ({grade or 'n/d'})",
        "  (1.00 = la jonction ne dépasse pas la variation interne du motif ;",
        "   mesuré visible à partir de 2.0 sur un pavage 3x3)",
        f"  bord brut avant/après : "
        f"{before if before is not None else 'n/d'} -> "
        f"{after if after is not None else 'n/d'}",
        "",
        "Niveaux : la métallicité et la rugosité sont CUITES dans les maps.",
        f"  metallicFactor  = {render.get('metallicFactor', 1.0)}"
        f"   (métallicité effective mesurée : {eff.get('metallic')})",
        f"  roughnessFactor = {render.get('roughnessFactor', 1.0)}"
        f"   (rugosité effective mesurée : {eff.get('roughness')})",
        "  " + RENDER_NOTE.replace(". ", ".\r\n  "),
        "",
        "Maps incluses :",
    ]
    for kind, fname in files.items():
        lines.append(f"  {fname:<34} {map_role(kind, naming)}")
    slots = [(files[k], engine_slot(k, naming)) for k in files
             if engine_slot(k, naming)]
    if slots:
        lines += ["", f"Où déposer chaque fichier ({NAMING_LABELS.get(naming, naming)}) :"]
        for fname, slot in slots:
            lines.append(f"  {fname:<34} -> {slot}")
    stats_blk = mat.get("map_stats") or {}
    told = [(k, s) for k, s in stats_blk.items()
            if k in files and (not s.get("informative") or s.get("dependent"))]
    if told:
        lines += ["", "Ce que ces maps NE portent PAS (mesuré, pas supposé) :"]
        for kind, s in told:
            lines.append(f"  {files[kind]:<34} {s.get('note') or 'constante'}")
    lines += [
        "",
        "normal.png : tangent-space OpenGL (+Y vers le haut).",
        "",
        "Prompt : " + (mat.get("prompt") or "-"),
    ]
    return "\r\n".join(lines) + "\r\n"


# Emplacements de texture que le GLB/glTF embarque réellement. height n'a pas
# d'équivalent en glTF cœur ; roughness/metallic séparées ne sont référençables
# par aucun emplacement du format (seule la paire packée l'est), et l'AO ne
# l'est que faute d'ORM — gltf_builder ne les embarque donc plus.
GLB_SLOTS = ("basecolor", "normal", "orm", "emissive", "ao")

# Coût géométrie du GLB, par maillage : positions+normales+UV (32 o/sommet)
# + indices. Mesuré sur les maillages générés par gltf_builder.
_MESH_BYTES = {"sphere": 148_000, "cube": 5_000, "torus": 96_000,
               "cylinder": 40_000, "plane": 400, "tiled": 400}


# Facteur de poids d'un ré-échantillonnage, MESURÉ et non supposé.
#
# La loi « pixels^0.72 » utilisée jusqu'ici se trompait de +29 % en 512 depuis
# une matière 2048 (2,05 Mo annoncés contre 1,59 Mo produits). Vérification :
# deux matières réelles (mat_20387482 « braise », mat_eecc3455 « acier rouge »,
# natives en 2048) exportées en 512 / 1024 / 2048 / 4096, poids des huit PNG
# relevé DANS l'archive :
#
#   côté demandé / natif   0.25      0.5       1.0     2.0
#   braise                 0.1055    0.3502    1.0     2.7403
#   acier rouge            0.1126    0.3788    1.0     2.8147
#   moyenne retenue        0.1091    0.3645    1.0     2.7775
#
# L'exposant équivalent varie de 0.73 à 0.81 selon l'écart : aucune puissance
# unique ne convient. On interpole donc en log/log ENTRE LES POINTS MESURÉS, et
# on prolonge au-delà avec la pente du segment de bord.
_SIZE_ANCHORS = ((-2.0, -3.1963), (-1.0, -1.4562), (0.0, 0.0), (1.0, 1.4740))


def _size_scale(target: int, native: int) -> float:
    """Rapport de poids attendu d'un jeu de PNG passé de `native` à `target`."""
    if not native or target == native:
        return 1.0
    x = math.log2(target / native)
    pts = _SIZE_ANCHORS
    if x <= pts[0][0]:
        slope = (pts[1][1] - pts[0][1]) / (pts[1][0] - pts[0][0])
        y = pts[0][1] + slope * (x - pts[0][0])
    elif x >= pts[-1][0]:
        slope = (pts[-1][1] - pts[-2][1]) / (pts[-1][0] - pts[-2][0])
        y = pts[-1][1] + slope * (x - pts[-1][0])
    else:
        y = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
                break
    return 2.0 ** y


def _flat_png_size(side: int, mode: str = "L", value: int = 0) -> int:
    """Taille REELLE d'un PNG uni de `side` px de cote. Encodage effectif :
    quelques millisecondes (une image uniforme se compresse par lignes
    identiques), et le chiffre n'est plus une extrapolation."""
    try:
        im = Image.new(mode, (int(side), int(side)),
                       int(value) if mode == "L" else (value, value, value))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.tell()
    except Exception:
        return 0


# ── LA RÈGLE DU « ≈ », ÉNONCÉE UNE FOIS ET APPLIQUÉE SANS EXCEPTION ────────
#
# Le marqueur « ≈ » était posé sans règle lisible : trois fichiers 8 bits le
# portaient (Roughness L 8, orm RGB 8, MaskMap RGBA 8) pendant qu'Occlusion —
# L 8 elle aussi — était donnée comme exacte, et la seule justification
# affichée parlait de profondeur 16 bits. Rien ne séparait les lignes.
#
# La règle est celle-ci, et elle ne dépend NI du nombre de canaux NI de la
# profondeur :
#
#   = mesuré : le fichier qui part existe déjà, encodé, sur le disque — on lit
#     sa taille, point.
#   ≈ estimé : l'export doit FABRIQUER un fichier qui n'existe pas encore. Le
#     chiffre vient alors d'un modèle calibré sur de vraies archives.
#
# Quatre fabrications, une seule suffit à faire basculer une ligne :
#   1. le niveau réglé est cuit dans la map (metallic, roughness, orm — voir
#      pbr_service.bake_levels : ce sont les SEULES qu'il transforme) ;
#   2. le fichier n'a jamais existé (MaskMap Unity, empilé à l'export) ;
#   3. la définition demandée diffère de la native (rééchantillonnage) ;
#   4. la profondeur demandée est 16 bits, ou l'enveloppe est du base64 glTF.
#
# Occlusion, height, normale, couleur de base et émissive ne subissent AUCUNE
# de ces quatre transformations en 8 bits à définition native : leur PNG part
# tel quel, leur poids est lu sur le disque. C'est pour cela — et seulement
# pour cela — qu'elles sont exactes quand roughness ne l'est pas.
#
# Chaque ligne du bordereau porte sa raison (`weigh`), l'écran l'affiche.
BAKED_KINDS = ("metallic", "roughness", "orm")

WEIGH_MEASURED = ("le PNG du disque part tel quel : sa taille est lue, "
                  "pas estimée")

WEIGH_RULE = (
    "Un poids est mesuré quand le fichier qui part existe déjà, encodé, sur le "
    "disque. Il est estimé — « ≈ » — dès que l'export doit en fabriquer un : "
    "niveau cuit dans la map (rugosité, métal, ORM), fichier empilé à la volée "
    "(MaskMap), rééchantillonnage, 16 bits ou base64. Ni le nombre de canaux "
    "ni la profondeur ne décident : seule la fabrication décide. Chaque ligne "
    "dit laquelle la concerne.")


def export_manifest(mat: dict, fmt: str = "zip", naming: str = "standard",
                    res: int = 0, bits: int = 8,
                    kinds: list | None = None, mesh: str = "sphere") -> dict:
    """Ce que contiendra l'export, AVANT de le produire : nom d'archive, liste
    exacte des fichiers avec leur nom moteur, leurs canaux, leur profondeur et
    leur poids.

    Le poids est EXACT (taille sur disque du PNG déjà encodé) quand la
    résolution demandée est la résolution native et que la profondeur reste en
    8 bits — c'est le cas par défaut. Sinon il est estimé, avec deux facteurs
    calibrés sur des exports réels (voir plus bas). Chaque entrée porte son
    propre drapeau ``exact`` : on n'annonce jamais un chiffre mesuré là où il
    est deviné."""
    fmt = fmt if fmt in EXPORT_FORMATS else "zip"
    naming = clean_naming(naming)
    try:
        bits = int(bits or 8)
    except (TypeError, ValueError):
        bits = 8
    bits = 16 if bits >= 16 else 8
    mid = str(mat.get("id") or "")
    d = material_dir(mid)
    native = int(mat.get("res") or 0) or 2048
    target = clean_res(res, native) if res else native
    names = naming_map(naming, mat.get("name") or mid or "material")

    on_disk = [k for k in MAP_KINDS if (d / f"{k}.png").is_file()]
    # Le MaskMap Unity n'est pas sur disque : il est fabriqué à l'export à
    # partir de metallic / ao / roughness (ou de l'ORM).
    extra = [MASKMAP] if (fmt == "zip" and naming in UNITY_NAMINGS
                          and {"metallic", "ao", "roughness", "orm"}
                          & set(on_disk)) else []
    avail = on_disk + extra
    # Sans sélection explicite, c'est le moteur choisi qui décide : Unity ne
    # branche que BaseMap / MaskMap / Normal (+ Height, Emission), Unreal et
    # Godot lisent l'ORM. Livrer en plus les maps séparées, c'était le même
    # contenu deux fois.
    sel = (set(kinds) if kinds
           else {k for k in default_export_maps(naming) if k in avail}
           or set(avail))
    # Le bordereau liste TOUTES les maps disponibles, y compris celles qu'on
    # laisse de côté (barrées à l'écran) : on voit ce qu'on emporte et ce qu'on
    # abandonne. Seules les sélectionnées comptent dans le total.
    if fmt == "zip":
        listed = avail
    else:
        # `GLB_SLOTS` est l'union des emplacements POSSIBLES ; ce que le GLB
        # embarque vraiment en dépend : avec une ORM sur disque, l'occlusion
        # est lue dans son canal R et `ao.png` n'est PAS embarquée (voir
        # gltf_builder, ao_slot). Le bordereau la comptait quand même — il
        # annonçait 4,71 Mo pour un fichier de 4,19 Mo, et listait une image
        # absente du livrable.
        listed = [k for k in on_disk if k in GLB_SLOTS]
        if "orm" in listed:
            listed = [k for k in listed if k != "ao"]

    # Un PNG ne grossit PAS comme le nombre de pixels : rééchantillonner lisse
    # l'image et le deflate en profite. Le facteur vient de _size_scale, qui
    # interpole entre des rapports MESURÉS sur de vraies archives.
    scale = _size_scale(target, native)
    same_res = (target == native)

    entries: list[dict] = []
    for kind in listed:
        depth = 8
        # raisons d'estimer : (etiquette courte pour le regroupement a
        # l'ecran, phrase complete pour la ligne). Une seule suffit a faire
        # basculer la ligne en « ~ ».
        why: list[tuple] = []
        st = (mat.get("map_stats") or {}).get(kind) or {}
        if kind == MASKMAP:
            # RGBA fabriquée à la volée : trois canaux de données + un alpha,
            # jamais un fichier sur disque. Estimée à partir des maps qui la
            # composent (mesuré : ~1.15x la somme metallic + ao + roughness,
            # le deflate profitant du canal de détail constant).
            src_sz = sum((d / f"{k}.png").stat().st_size
                         for k in ("metallic", "ao", "roughness")
                         if (d / f"{k}.png").is_file())
            est = src_sz * scale * 1.15
            why.append(("fabriqué à l'export",
                        "aucun MaskMap n'existe sur disque : il est empilé à "
                        "l'export depuis métal, occlusion et rugosité"))
        else:
            est = (d / f"{kind}.png").stat().st_size * scale
            if kind in BAKED_KINDS:
                # LE POIDS ANNONCE PORTAIT SUR LE MAUVAIS FICHIER. `metallic.png`
                # sur disque est le MOTIF derive (319 556 o) ; ce qui part dans
                # l'archive est le motif APRES bake_levels, uni des que le niveau
                # est a 0.00 ou 1.00 — 1 097 o.
                why.append(("niveau cuit à l'export",
                            "le niveau réglé est cuit dans la map à l'export "
                            "(bake_levels) : le PNG posé sur le disque n'est "
                            "pas celui qui part"))
            if not same_res:
                why.append(("rééchantillonné",
                            f"rééchantillonnage {native}² → {target}² : le "
                            "PNG est réencodé à la livraison"))
            if fmt == "zip" and bits == 16 and kind in ("height", "normal"):
                depth = 16
                # Le conteneur 16 bits double les octets bruts, mais chaque
                # paire est identique (v -> v*257) : le deflate en ravale une
                # partie. Le facteur unique de 1.42 sous-estimait l'archive de
                # 9 %. Re-mesuré sur quatre matieres reelles (or martele,
                # pierre moussue, obsidienne, braise), fichier par fichier :
                #   normal x1.36 1.39 1.59 1.59  -> 1.48
                #   height x1.51 1.78 1.83 1.85  -> 1.74
                # La height compresse mieux en 8 bits (grands aplats), donc
                # elle gonfle davantage : un facteur par map, pas un moyen.
                est *= 1.74 if kind == "height" else 1.48
                why.append(("16 bits",
                            "conversion 8 → 16 bits : chaque octet est "
                            "doublé, le deflate en ravale une part"))
            # Quand la map LIVRÉE est uniforme (métal à 0.00, émissive
            # éteinte), le motif du disque n'a plus rien à voir avec elle : on
            # encode pour de vrai le PNG uni à la taille visée (quelques
            # millisecondes) plutôt que d'extrapoler depuis un fichier qui ne
            # part pas. Cela reste une estimation — la map n'est uniforme qu'à
            # FLAT_SPAN niveaux près — mais une estimation bien meilleure.
            if why and st.get("informative") is False \
                    and MAP_MODES.get(kind) == "L":
                est = _flat_png_size(target, "L", int(round(st.get("mean", 0))))
                if depth == 16:
                    est *= 1.74 if kind == "height" else 1.48
        if fmt == "gltf":
            # le PNG part encodé en base64 dans une data: URI du JSON
            est *= 4 / 3
            why.append(("base64",
                        "l'image part encodée en base64 dans le JSON glTF "
                        "(+33 %)"))
        entries.append({
            "kind": kind,
            "name": names.get(kind, f"{kind}.png") if fmt == "zip"
                    else f"{kind}.png",
            "channels": "RGBA" if kind == MASKMAP else MAP_MODES.get(kind, "L"),
            "role": map_role(kind, naming if fmt == "zip" else "standard"),
            # l'emplacement de DESTINATION dans le moteur visé : un nom de
            # fichier ne branche rien tout seul.
            "slot": engine_slot(kind, naming) if fmt == "zip" else "",
            "bits": depth, "bytes": int(round(est)), "exact": not why,
            # POURQUOI ce poids est estimé — la règle appliquée à CETTE ligne.
            "weigh": WEIGH_MEASURED if not why
                     else " ; ".join(w[1] for w in why),
            # etiquette courte : l'ecran regroupe les lignes qui partagent la
            # meme raison, pour ecrire la regle sans la repeter dix fois.
            "weigh_tag": "" if not why else " + ".join(w[0] for w in why),
            "selected": kind in sel,
            # ce que la map porte vraiment, repris de la mesure déjà faite
            "informative": st.get("informative", True),
            "corr_lum": st.get("corr_lum", 0.0),
            "note": st.get("note", ""),
        })

    extras: list[dict] = []
    if fmt == "zip":
        files = {e["kind"]: e["name"] for e in entries if e["selected"]}
        readme = _readme(mat, files, bits, naming, target)
        extras.append({"name": "LISEZMOI.txt",
                       "bytes": len(readme.encode("utf-8")), "exact": True,
                       "weigh": "texte écrit ici même : ses octets sont comptés",
                       "weigh_tag": ""})
        extras.append({"name": "material.json",
                       # le MEME objet que l'archive écrit, sinon le bordereau
                       # annonce un poids que le ZIP ne fait pas
                       "bytes": len(json.dumps(public_material(mat),
                                               ensure_ascii=False,
                                               indent=2).encode("utf-8")),
                       "exact": True,
                       "weigh": "le MÊME objet que l'archive écrit : "
                                "ses octets sont comptés",
                       "weigh_tag": ""})
        thumb_p = d / "thumb.png"
        # une vignette périmée (géométrie d'avant) ne part pas dans l'archive
        if thumb_is_current(d):
            extras.append({"name": "thumb.png",
                           "bytes": thumb_p.stat().st_size, "exact": True,
                           "weigh": WEIGH_MEASURED, "weigh_tag": ""})
    else:
        geo = _MESH_BYTES.get(mesh, 118_000) * (4 / 3 if fmt == "gltf" else 1)
        extras.append({"name": f"géométrie {mesh}",
                       "bytes": int(geo), "exact": False,
                       "weigh": "sommets et indices sérialisés à l'export : "
                                "taille relevée sur les maillages générés"
                                + (", puis base64" if fmt == "gltf" else ""),
                       "weigh_tag": "fabriqué à l'export"
                                    + (" + base64" if fmt == "gltf" else "")})
    total = sum(e["bytes"] for e in entries if e["selected"])
    total += sum(e["bytes"] for e in extras)
    if fmt == "gltf":
        total += 3_000                        # l'enveloppe JSON elle-même

    return {
        "id": mid, "format": fmt, "naming": naming,
        "naming_label": NAMING_LABELS.get(naming, naming),
        "naming_note": NAMING_NOTES.get(naming, ""),
        # comment le scalaire se compose avec la map — plus jamais implicite
        "render": mat.get("render") or render_block(mat.get("props")),
        "res": target,
        "bits": bits, "native_res": native,
        # ce que la route d'export FAIT réellement des pixels, dit par le code
        # qui le fait : l'écran n'a plus à le deviner.
        "resample": ("none" if target == native
                     else ("up" if target > native else "down")),
        "archive": export_filename(mat, fmt, naming),
        # ce que CE moteur branche vraiment : l'écran coche là-dessus
        "default_maps": [k for k in default_export_maps(naming) if k in listed],
        "entries": entries, "extras": extras,
        "total_bytes": int(total),
        # le total ne somme que les lignes COCHÉES : son drapeau ne regarde
        # donc que celles-là. Décocher les trois maps cuites rend l'archive
        # entièrement mesurée, et le bordereau doit le dire.
        "exact": bool(all(e["exact"] for e in entries if e["selected"])
                      and all(e.get("exact") for e in extras)),
        # LA RÈGLE, publiée avec le bordereau qui l'applique.
        "weigh_rule": WEIGH_RULE,
    }


def export_zip(mat: dict, maps: dict, naming: str = "standard",
               bits: int = 8, thumb: bytes | None = None,
               material_json: bool = True) -> bytes:
    """ZIP complet : maps nommées selon la convention, material.json,
    vignette et LISEZMOI (scores de raccord inclus).

    `maps` peut contenir la clé `maskmap` (déjà construite) ; sinon, sous
    convention Unity, elle est fabriquée ici depuis metallic/ao/roughness.

    `material.json` emporte le bloc `render` : un script d'import y lit que les
    facteurs valent 1.0 et que le niveau est déjà dans la map. Sans lui,
    `props.roughness` seul se relisait comme un facteur à appliquer — et la
    rugosité était comptée deux fois."""
    naming = clean_naming(naming)
    names = naming_map(naming, mat.get("name") or mat.get("id") or "material")
    mat = dict(mat)
    mat["render"] = render_block(mat.get("props"), maps, baked=True)
    res = 0
    buf = io.BytesIO()
    files = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for kind in tuple(MAP_KINDS) + EXPORT_EXTRA_KINDS:
            img = maps.get(kind)
            if img is None or kind not in names:
                continue
            res = max(res, img.size[0])
            fname = names[kind]
            files[kind] = fname
            if kind == MASKMAP:
                mbuf = io.BytesIO()
                img.convert("RGBA").save(mbuf, format="PNG", optimize=False)
                z.writestr(fname, mbuf.getvalue())
                continue
            z.writestr(fname, png_bytes(img, kind, bits))
        if thumb:
            z.writestr("thumb.png", thumb)
        if material_json:
            z.writestr("material.json",
                       json.dumps(public_material(mat), ensure_ascii=False,
                                  indent=2))
        z.writestr("LISEZMOI.txt", _readme(mat, files, bits, naming, res))
    return buf.getvalue()


def glb_to_gltf(glb: bytes) -> bytes:
    """GLB -> .gltf autonome (buffer en data: URI base64).

    Évite de dupliquer la génération de géométrie : le GLB produit par
    ``gltf_builder`` est décomposé en ses deux chunks, et le chunk binaire
    devient l'URI du buffer 0. Pur stdlib.
    """
    if len(glb) < 20 or glb[:4] != b"glTF":
        raise ValueError("GLB invalide (en-tête manquant)")
    total = struct.unpack("<I", glb[8:12])[0]
    off, js, bin_ = 12, None, b""
    while off + 8 <= min(total, len(glb)):
        clen, ctype = struct.unpack("<II", glb[off:off + 8])
        data = glb[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:            # 'JSON'
            js = data
        elif ctype == 0x004E4942:          # 'BIN\0'
            bin_ = data
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    if js is None:
        raise ValueError("GLB invalide (chunk JSON absent)")
    doc = json.loads(js.decode("utf-8").rstrip("\x00 "))
    buffers = doc.get("buffers") or []
    if bin_ and buffers:
        declared = int(buffers[0].get("byteLength") or len(bin_))
        payload = bin_[:declared] if 0 < declared <= len(bin_) else bin_
        buffers[0]["byteLength"] = len(payload)
        buffers[0]["uri"] = ("data:application/octet-stream;base64,"
                             + base64.b64encode(payload).decode("ascii"))
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


# ── environnements (repli local si aucun module dédié n'est présent) ─────────

def _fallback_env(name: str) -> bytes:
    """Équirectangulaire 1024x512 en PIL pur : dégradé de ciel + soleil + sol.

    Repli utilisé tant que le module d'environnements dédié (SPEC section 6)
    n'expose pas de générateur — l'inspecteur a toujours ses 7 ambiances.
    """
    presets = {
        "unlit":    ((190, 190, 195), (150, 150, 155), (120, 120, 122), 0.0, 0.30),
        "daylight": ((70, 130, 220), (200, 225, 250), (95, 92, 84), 1.0, 0.28),
        "studio":   ((235, 235, 240), (255, 255, 255), (60, 60, 64), 0.6, 0.34),
        "sunset":   ((40, 45, 95), (255, 150, 70), (60, 45, 40), 1.0, 0.06),
        "overcast": ((160, 168, 178), (205, 210, 215), (85, 85, 88), 0.25, 0.22),
        "night":    ((6, 9, 22), (25, 32, 60), (10, 12, 18), 0.35, 0.10),
        "dramatic": ((12, 14, 20), (210, 120, 40), (22, 20, 24), 1.0, 0.12),
    }
    top, hor, ground, sun_i, sun_h = presets.get(name, presets["studio"])
    w, h = 1024, 512
    img = Image.new("RGB", (w, h))
    px = img.load()
    horizon = h // 2
    for y in range(h):
        if y < horizon:
            t = y / max(1, horizon - 1)
            col = tuple(round(top[i] + (hor[i] - top[i]) * (t ** 0.7))
                        for i in range(3))
        else:
            t = (y - horizon) / max(1, h - horizon - 1)
            col = tuple(round(hor[i] + (ground[i] - hor[i]) * min(1.0, t * 3))
                        for i in range(3))
        for x in range(w):
            px[x, y] = col
    if sun_i > 0:                       # tache solaire (dégradé radial doux)
        sx, sy = int(w * 0.68), int(h * (1.0 - sun_h) * 0.98)
        radius = 70
        for y in range(max(0, sy - radius * 2), min(h, sy + radius * 2)):
            for x in range(max(0, sx - radius * 2), min(w, sx + radius * 2)):
                d = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
                if d > radius * 2:
                    continue
                k = sun_i * max(0.0, 1.0 - d / (radius * 2)) ** 2
                r, g, b = px[x, y]
                px[x, y] = (min(255, round(r + (255 - r) * k)),
                            min(255, round(g + (250 - g) * k)),
                            min(255, round(b + (225 - b) * k)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def env_list() -> list[dict]:
    """[{name,label}] des 7 ambiances — celle d'``env_service`` si le module
    est présent (labels tenus à jour côté générateur), sinon la liste locale."""
    try:
        from app.services import env_service as ES
        rows = ES.env_list()
        if isinstance(rows, list) and rows:
            return [{"name": r["name"], "label": r["label"]} for r in rows]
    except Exception as e:
        logger.warning(f"materials: env_service.env_list indisponible ({e})")
    return list(ENVS)


def env_jpeg(name: str) -> bytes:
    """JPEG équirectangulaire d'une ambiance.

    Délègue au module d'environnements du SPEC (section 6), qui gère son
    propre cache disque ; sinon repli local (mis en cache ici).
    Le nom passe d'abord par la liste blanche : ``env_service`` retomberait
    silencieusement sur « studio » pour un nom inconnu, on préfère un 404.
    """
    n = _coerce_enum(name, "", ENV_NAMES)
    if not n:
        raise ValueError(f"Environnement inconnu: {name!r}")
    data = None
    import importlib
    for modname, fname in (("app.services.env_service", "env_bytes"),
                           ("app.services.env_service", "env_jpeg"),
                           ("app.services.env_service", "build_env"),
                           ("app.services.gltf_builder", "env_jpeg"),
                           ("app.services.gltf_builder", "build_env")):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        fn = getattr(mod, fname, None)
        if not callable(fn):
            continue
        try:
            out = fn(n)
        except Exception as e:
            logger.warning(f"materials: {modname}.{fname} a échoué ({e})")
            continue
        if isinstance(out, (bytes, bytearray)):
            data = bytes(out)
        elif isinstance(out, Image.Image):
            buf = io.BytesIO()
            out.convert("RGB").save(buf, format="JPEG", quality=88)
            data = buf.getvalue()
        if data:
            return data
    cache = materials_root() / "_envs"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{n}.jpg"
    if f.is_file():
        return f.read_bytes()
    data = _fallback_env(n)
    f.write_bytes(data)
    return data
