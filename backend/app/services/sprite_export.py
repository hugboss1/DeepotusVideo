"""Les exports moteur écrits PAR CODE — T109, plan sprites tâches 3 à 5 (R10a P3).

Quatre formats, un seul module, parce qu'ils lisent tous le MÊME manifeste et les MÊMES tags : les séparer ferait
diverger la convention de nommage des images (`frame_000.png`) entre quatre fichiers, et c'est elle que les moteurs
utilisent pour relier une animation à ses cases.

  - `godot_tres`        : ressource texte Godot 4 (SpriteFrames + AtlasTexture)
  - `atlas_json_hash`   : atlas façon TexturePacker, lu par Phaser et PixiJS
  - `aseprite_bytes`    : .ase binaire selon la spécification publique (relue le 06/10/2026)
  - `paper2d_json`      : feuille pour l'importateur Unreal Paper2D

Rien ici ne touche au disque sauf `write_all`, et rien n'importe FastAPI.
"""
from __future__ import annotations

import json
import struct
import zlib

from app.services.sprite_anim import duree_ms, spans

_APP = "DeepotusVideoGen — Sprite Lab"


def frame_name(i: int) -> str:
    """Le nom d'une case, PARTOUT. Godot, l'atlas, Paper2D et le pack Unity doivent s'accorder : un seul endroit le
    décide."""
    return f"frame_{i:03d}.png"


def _pivot(align: str) -> tuple[float, float]:
    """'feet' ancre le bas-centre de la case ; sinon le centre. Même règle que `build_unity_pack` — recopiée ici EXPRÈS :
    le pack Unity retourne l'axe y, pas l'atlas, et mélanger les deux conventions dans une fonction commune est
    exactement ce qui produit un sprite à l'envers."""
    return (0.5, 0.0) if align == "feet" else (0.5, 0.5)


# ── Godot 4 : SpriteFrames en .tres ─────────────────────────────────────────
def _num(v: float) -> str:
    """Godot écrit les flottants avec au moins une décimale ; `8` serait lu comme un entier et `speed` deviendrait un
    int, ce que SpriteFrames refuse au chargement."""
    s = f"{float(v):.4f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


def godot_tres(manifest: dict, sheet_name: str = "sheet.png") -> str:
    """Ressource texte Godot 4. Une AtlasTexture par case, une animation par tag (« default » sans tag). La durée
    d'une image y est RELATIVE (doc Godot 4 : `absolute = relative / (animation_fps * playing_speed)`), donc
    relative = ms / 1000 × speed, avec speed = fps de la feuille. La sérialisation `format=3` est écrite d'après les
    ressources Godot 4 connues : l'ouverture dans Godot est la vérification humaine qui reste."""
    frames = manifest["frames"]
    n = len(frames)
    fps = float(manifest.get("fps") or 8)
    lignes = [f'[gd_resource type="SpriteFrames" load_steps={n + 2} format=3]', "",
              f'[ext_resource type="Texture2D" path="res://{sheet_name}" id="1_sheet"]', ""]
    for f in frames:
        r = f["rect"]
        lignes += [f'[sub_resource type="AtlasTexture" id="Frame_{f["index"]:03d}"]',
                   'atlas = ExtResource("1_sheet")',
                   f'region = Rect2({r["x"]}, {r["y"]}, {r["w"]}, {r["h"]})', ""]
    anims = []
    for nom, a, b in spans(manifest.get("anim"), n):
        cases = []
        for i in range(a, b + 1):
            rel = round(duree_ms(frames[i], fps) / 1000.0 * fps, 4)
            cases.append('{\n"duration": %s,\n"texture": SubResource("Frame_%03d")\n}' % (_num(rel), i))
        anims.append('{\n"frames": [%s],\n"loop": true,\n"name": &"%s",\n"speed": %s\n}'
                     % (", ".join(cases), nom, _num(fps)))
    lignes += ["[resource]", "animations = [%s]" % ", ".join(anims), ""]
    return "\n".join(lignes)


# ── atlas JSON Hash (TexturePacker) ─────────────────────────────────────────
def atlas_json_hash(manifest: dict, sheet_w: int, sheet_h: int, sheet_name: str = "sheet.png") -> dict:
    """Champs vérifiés (codeandweb.com, R10a) : `frame`, `rotated`, `trimmed`, `spriteSourceSize`, `sourceSize` ;
    `meta.image`, `meta.size`, `meta.scale`. `pivot` et `meta.frameTags` sont des EXTENSIONS assumées : le format n'a
    pas de champ de tags, et `frameTags` est la forme que Pixi et Phaser lisent déjà (export JSON d'Aseprite). Sans
    tag, `frameTags` est vide — on n'invente pas « default » là où le moteur saurait lire toute la feuille."""
    px, py = _pivot(manifest.get("align") or "center")
    out = {}
    for f in manifest["frames"]:
        r = f["rect"]
        out[frame_name(f["index"])] = {
            "frame": {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]},
            "rotated": False,
            # la feuille n'est jamais rognée par case : chaque case fait exactement la taille de cellule
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": r["w"], "h": r["h"]},
            "sourceSize": {"w": r["w"], "h": r["h"]},
            "pivot": {"x": px, "y": py},
        }
    tags = [{"name": t["name"], "from": t["from"], "to": t["to"], "direction": t["direction"]}
            for t in ((manifest.get("anim") or {}).get("tags") or [])]
    return {"frames": out,
            "meta": {"app": _APP, "version": "1.0", "image": sheet_name, "format": "RGBA8888",
                     "size": {"w": sheet_w, "h": sheet_h}, "scale": "1", "frameTags": tags}}


# ── Aseprite .ase (spécification publique, relue le 06/10/2026) ─────────────
# SOUS-ENSEMBLE ÉCRIT, ET C'EST DÉLIBÉRÉ : RGBA 32 bpp ; UN calque normal « Layer 1 » visible+éditable, opacité 255 ;
# N images portant chacune UN cel de type 2 (image compressée zlib) posé en (0,0) et couvrant la toile ; un chunk de
# tags dans l'image 0 quand il y en a. PAS de palette (« for color depths more than 8bpp, palettes are optional »),
# PAS de profil colorimétrique 0x2007 — Aseprite suppose alors sRGB, seule conséquence visible —, PAS de slices, PAS
# de données utilisateur. Petit-boutiste partout (« ASE files use Intel byte order »).
_ASE_TETE = "<IHHHHHIHIIB3sHBBhhHH84s"      # 128 octets, vérifié par le banc
_ASE_IMAGE = "<IHHH2sI"                      # 16 octets
_ASE_SENS = {"forward": 0, "reverse": 1, "pingpong": 2, "pingpong_reverse": 3}


def _ase_string(s: str) -> bytes:
    b = s.encode("utf-8")
    if len(b) > 65535:
        raise ValueError("aseprite STRING: 65535 bytes at most")
    return struct.pack("<H", len(b)) + b


def _ase_chunk(type_: int, charge: bytes) -> bytes:
    """La taille COMPREND ses 4 octets et les 2 du type (spécification) — l'oublier donne un fichier qui s'ouvre à
    moitié, jamais une erreur."""
    return struct.pack("<IH", len(charge) + 6, type_) + charge


def _ase_calque(nom: str) -> bytes:
    charge = struct.pack("<HHHHHHB3s",
                         3,        # drapeaux : 1 visible | 2 éditable
                         0,        # type : normal
                         0,        # niveau d'enfant
                         0, 0,     # largeur/hauteur par défaut (ignorées)
                         0,        # fusion : normal
                         255,      # opacité
                         b"\0" * 3)
    return _ase_chunk(0x2004, charge + _ase_string(nom))


def _ase_cel(img) -> bytes:
    w, h = img.size
    charge = struct.pack("<HhhBHh5s", 0, 0, 0, 255, 2, 0, b"\0" * 5)
    return _ase_chunk(0x2005, charge + struct.pack("<HH", w, h) + zlib.compress(img.convert("RGBA").tobytes()))


def _ase_tags(tags: list[dict]) -> bytes:
    charge = struct.pack("<H8s", len(tags), b"\0" * 8)
    for t in tags:
        charge += struct.pack("<HHBH6s3sB", int(t["from"]), int(t["to"]), _ASE_SENS[t["direction"]],
                              int(t.get("repeat") or 0), b"\0" * 6, b"\0" * 3, 0) + _ase_string(t["name"])
    return _ase_chunk(0x2018, charge)


def _ase_image(chunks: list[bytes], duree: int) -> bytes:
    corps = b"".join(chunks)
    n = len(chunks)
    return struct.pack(_ASE_IMAGE, len(corps) + 16, 0xF1FA, n if n < 0xFFFF else 0xFFFF,
                       max(0, min(65535, int(duree))), b"\0" * 2, n) + corps


def aseprite_bytes(cases: list, durees: list[int], tags: list[dict] | None = None) -> bytes:
    """Les octets d'un .ase. `cases` = images PIL de MÊME taille (les cases de la feuille), `durees` = une
    milliseconde par case."""
    if not cases:
        raise ValueError("aseprite: at least one frame")
    if len(durees) != len(cases):
        raise ValueError("aseprite: one duration per frame")
    w, h = cases[0].size
    for im in cases:
        if im.size != (w, h):
            raise ValueError(f"aseprite: every frame shares the canvas size ({w}x{h}) — got {im.size}")
    corps = []
    for i, im in enumerate(cases):
        chunks = []
        if i == 0:
            chunks.append(_ase_calque("Layer 1"))
        chunks.append(_ase_cel(im))
        if i == 0 and tags:
            chunks.append(_ase_tags(tags))
        corps.append(_ase_image(chunks, durees[i]))
    corps_b = b"".join(corps)
    tete = struct.pack(_ASE_TETE, 128 + len(corps_b), 0xA5E0, len(cases), w, h,
                       32,                                   # profondeur : RGBA
                       1,                                    # drapeaux : opacité de calque valide
                       max(1, min(65535, int(durees[0]))),   # vitesse (obsolète, par égard)
                       0, 0, 0, b"\0" * 3,
                       0,                                    # nb couleurs : aucune palette
                       1, 1, 0, 0, 16, 16, b"\0" * 84)
    return tete + corps_b


# ── Unreal Paper2D ──────────────────────────────────────────────────────────
def paper2d_json(manifest: dict, sheet_w: int, sheet_h: int, sheet_name: str = "sheet.png") -> dict:
    """Feuille pour l'importateur Paper2D, en forme JSON **Array** de TexturePacker : `frames` est une LISTE, chaque
    entrée portant `filename`.

    POURQUOI Array et pas Hash (celle de `atlas_json_hash`) : l'importateur construit TOUJOURS un flipbook, donc
    l'ORDRE des images porte du sens ; une liste le garantit, un objet JSON ne le garantit pas.

    INCERTITUDE ASSUMÉE : le jeu de champs exact lu par l'importateur n'a pas pu être revérifié (documentation Epic :
    403 et 404 le 03/09/2026 ; tutoriel TexturePacker Paper2D : 404 le 06/10/2026). Ce que l'on tient : l'importateur
    lit une feuille exportée par Adobe Flash CS6 ou TexturePacker, crée texture + sprites + flipbook, et
    TexturePacker écrit un `.paper2dsprites`. Le banc ne mesure que NOTRE fichier."""
    px, py = _pivot(manifest.get("align") or "center")
    frames = []
    for f in manifest["frames"]:
        r = f["rect"]
        frames.append({"filename": frame_name(f["index"]),
                       "frame": {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]},
                       "rotated": False, "trimmed": False,
                       "spriteSourceSize": {"x": 0, "y": 0, "w": r["w"], "h": r["h"]},
                       "sourceSize": {"w": r["w"], "h": r["h"]},
                       "pivot": {"x": px, "y": py}})
    return {"frames": frames,
            "meta": {"app": _APP, "version": "1.0", "image": sheet_name, "format": "RGBA8888",
                     "size": {"w": sheet_w, "h": sheet_h}, "scale": "1"}}


# ── écriture ────────────────────────────────────────────────────────────────
EXPORTS = ("sheet.tres", "sheet.atlas.json", "sheet.ase", "sheet.paper2dsprites")


def write_all(manifest: dict, out_dir, sheet_w: int, sheet_h: int) -> list[str]:
    """Écrit les quatre exports à côté de sheet.png et rend les noms écrits. UN SEUL appelant :
    `sprite_service._assemble`, après le manifeste — c'est ce qui donne aux particules et aux séquences Kenney les
    mêmes exports sans une ligne chez elles."""
    from PIL import Image as _I
    (out_dir / "sheet.tres").write_text(godot_tres(manifest), encoding="utf-8")
    (out_dir / "sheet.atlas.json").write_text(json.dumps(atlas_json_hash(manifest, sheet_w, sheet_h), indent=2),
                                              encoding="utf-8")
    cases, durees = [], []
    for f in manifest["frames"]:
        with _I.open(out_dir / f["file"]) as im:
            cases.append(im.convert("RGBA"))       # convert APRÈS with : une image neuve, détachée du fichier
        durees.append(duree_ms(f, manifest.get("fps")))
    (out_dir / "sheet.ase").write_bytes(aseprite_bytes(cases, durees,
                                                       (manifest.get("anim") or {}).get("tags") or []))
    (out_dir / "sheet.paper2dsprites").write_text(json.dumps(paper2d_json(manifest, sheet_w, sheet_h), indent=2),
                                                  encoding="utf-8")
    return list(EXPORTS)
