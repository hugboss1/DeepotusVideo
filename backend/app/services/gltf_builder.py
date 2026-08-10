"""Material Forge — construction de GLB procéduraux (SPEC section 5).

Stdlib PURE : ce module n'importe ni PIL, ni numpy, ni la configuration de
l'application. Il ne fait que de l'arithmétique et de l'empaquetage binaire,
ce qui le rend testable hors application et réutilisable partout.

Il produit un fichier GLB (glTF 2.0 binaire) AUTO-SUFFISANT : les textures PNG
sont recopiées telles quelles dans le tampon binaire, aucun fichier externe
n'est référencé. Le résultat s'ouvre dans <model-viewer> comme dans Blender.

Six maillages procéduraux, tous en coordonnées main droite, Y vers le haut,
enroulement CCW vu de l'extérieur (sinon l'élimination des faces arrière
rendrait l'objet invisible) :

    sphere    UV 80x40 (pôles serrés)       3321 sommets / 6240 triangles
    cube      UV par face (24 sommets)         24 sommets /   12 triangles
    torus     48x24, R=0.7 r=0.3             1225 sommets / 2304 triangles
    cylinder  48 segments + 2 capuchons       198 sommets /  192 triangles
    plane     quad vertical face à la caméra    4 sommets /    2 triangles
    tiled     grille 3x3, UV 0..3              16 sommets /   18 triangles

Chaque sommet porte POSITION, NORMAL, TEXCOORD_0 et TANGENT. La tangente n'est
pas optionnelle : sans elle, plusieurs moteurs (dont three.js/model-viewer en
l'absence de dérivées fiables, et Blender à l'import) reconstruisent une base
TBN approximative et la carte de normales part de travers. Elle est calculée
par la méthode de Lengyel (accumulation par triangle puis orthonormalisation
de Gram-Schmidt), ce qui donne aussi la main (w = +/-1) correcte pour les
capuchons de cylindre dont l'UV est en miroir.

Extensions émises : KHR_materials_clearcoat, KHR_materials_sheen,
KHR_materials_transmission, KHR_materials_ior, KHR_texture_transform.

Conventions retenues (figées ici, l'UI s'y aligne) :
  - props["rotation"] est en DEGRÉS, la rotation se fait autour du centre UV ;
  - props["tiling"] est un facteur d'échelle appliqué aux deux axes UV ;
  - les couleurs hexadécimales sont en sRGB et converties en linéaire, comme
    l'exige glTF pour baseColorFactor / emissiveFactor / sheenColorFactor ;
  - opacity est un FACTEUR multiplié par la texture (sémantique glTF standard) ;
  - metallic / roughness, eux, VIVENT DANS LA MAP (voir plus bas).

Métallicité et rugosité : le facteur ne double PAS la map
---------------------------------------------------------
glTF pose `metalness = metallicFactor x texture.B` et
`roughness = roughnessFactor x texture.G`. Tant que la map portait un motif
dérivé proche de zéro, un facteur à 1.0 promettait un métal que la texture
annulait : « or martelé » affichait Métallique 1.00 et exportait 0.005, soit
du plastique jaune — dans l'aperçu comme dans le GLB, et le ZIP livrait un
metallic.png noir sans facteur pour le rattraper.

Le niveau est donc cuit dans la map (`pbr_service.bake_levels`, moyenne de la
map = valeur réglée) et **ce module met le facteur correspondant à 1.0 dès que
la texture est présente**. Une seule vérité, la même pour l'aperçu, le GLB
exporté et les PNG du ZIP. Sans texture, le facteur reprend son rôle normal.

CE QUI VAUT POUR LE MÉTAL VAUT POUR LA RUGOSITÉ, exactement : les deux
facteurs passent à 1.0 ensemble, parce que les deux canaux vivent dans la MÊME
image (ORM : V = rugosité, B = métal). Laisser `roughnessFactor` au niveau
réglé pendant que la map le porte déjà donnerait 0.25 x 0.251 = 0.063 — une
matière presque miroir là où le curseur annonce « rugosité 0.25 ». Le matériau
émis porte en plus un bloc `extras` qui DIT cette composition : un lecteur, un
script d'import ou un critique peut la vérifier sans lire ce fichier.
"""
from __future__ import annotations

import json
import math
import struct

__all__ = [
    "MESHES", "DEFAULT_PROPS", "TEXTURE_SLOTS", "MESH_UV", "MESH_FRAME",
    "MESH_VERSION",
    "STAGE_SPAN", "build_mesh", "mesh_stats", "build_glb", "normalize_props",
]

# ── constantes glTF ─────────────────────────────────────────────────────────
_GLB_MAGIC = 0x46546C67          # 'glTF'
_GLB_VERSION = 2
_CHUNK_JSON = 0x4E4F534A         # 'JSON'
_CHUNK_BIN = 0x004E4942          # 'BIN\0'

_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963
_FLOAT = 5126
_UNSIGNED_SHORT = 5123
_UNSIGNED_INT = 5125
_LINEAR = 9729
_LINEAR_MIPMAP_LINEAR = 9987
_REPEAT = 10497
_CLAMP = 33071

MESHES = ("sphere", "cube", "torus", "cylinder", "plane", "tiled")

# ── échelle de la matière sur le maillage ───────────────────────────────────
# Un seul enroulement d'UV sur une sphère étire la tuile sur toute la
# circonférence : la matière se lit alors comme une mappemonde, pas comme une
# surface. On répète donc la tuile en respectant les proportions réelles du
# maillage (rapport circonférence/hauteur), de sorte qu'une tuile occupe à peu
# près la même surface monde quel que soit le maillage : les six aperçus
# deviennent comparables entre eux. Le raccord mesuré à 0 est ce qui rend ces
# répétitions possibles — la barre, elle, ne peut pas se le permettre.
#
# LES RÉPÉTITIONS SONT ENTIÈRES, et ce n'est pas une coquetterie.
# Avec (3.0, 1.5) la sphère portait une tuile ET DEMIE du pôle nord au pôle sud :
# la demi-tuile commençait 30° sous l'équateur, écrasée par la courbure et
# floutée par le mip-mapping. À l'écran cela donnait un motif dupliqué, flou,
# flottant en bas à droite de la sphère — l'« artefact fantôme ». Il ne venait ni
# du maillage ni de la dérivation : c'était le pavage lui-même, coupé au milieu
# d'un motif. Une répétition fractionnaire laisse toujours une tuile tronquée
# quelque part ; un nombre entier ne le peut pas.
#   (répétitions en u, en v) — entiers, et le plus proche possible d'une tuile
#   carrée en unités monde (indiqué en commentaire).
# Version des GÉNÉRATEURS de maillage. À incrémenter dès qu'une géométrie
# change : elle entre dans la clé du cache d'aperçu, donc un cache disque
# écrit avant la modification se périme tout seul au lieu de servir l'ancien
# maillage. (1 -> 2 : sphère 80x40 à rangées serrées aux pôles.
# 2 -> 3 : PLACAGE REMIS À L'ENDROIT, voir _ORIENTATION ci-dessous.)
MESH_VERSION = 3

# ── LE PLACAGE DOIT SE LIRE COMME LE FICHIER ────────────────────────────────
#
# Pendant sept rondes l'aperçu a montré autre chose que ce qu'il livre : sur la
# sphère, le cylindre et le tore, la texture était RETOURNÉE. « or martelé »
# porte du texte — « $DEEPOTUS », « PROTOCOL » — et ce texte se lisait à
# l'envers dans le viewport pendant que le PNG basecolor téléchargé, lui, était
# à l'endroit. L'écran jugé par l'artiste n'était pas le fichier livré.
#
# La cause est purement paramétrique. Sur la sphère, le cylindre et le tore, le
# tour d'axe est écrit `x = cos(theta), z = sin(theta)` avec `theta = 2*pi*u` ;
# en repère main droite (X à droite, Y en haut, Z vers l'observateur), la face
# tournée vers la caméra est celle où z > 0, et là `dx/du = -sin(theta) < 0` :
# **u croissant part vers la GAUCHE de l'écran** alors que u croissant va vers
# la DROITE de l'image. Un miroir horizontal, exactement. Le tore ajoutait le
# même défaut sur v : `y = r*sin(2*pi*v)` fait MONTER v sur la couronne
# extérieure, la seule qu'on voie, alors que v descend dans l'image.
#
# On corrige au placage et non à la géométrie : les positions, les normales et
# l'enroulement CCW restent identiques (donc les comptes de sommets, le cadrage
# et l'élimination des faces arrière ne bougent pas), seul le u — et le v du
# tore — est renversé. Les TANGENTES sont recalculées APRÈS, à partir des UV
# corrigés (`build_mesh` appelle `_tangents` en dernier) : le repère TBN suit
# le placage, `w` change de signe tout seul, et l'éclairage du relief reste
# juste. Inverser u sans toucher la tangente aurait éclairé les creux comme des
# bosses — le même mensonge, déplacé.
#
# L'invariant qui verrouille tout ça est testé dans
# `backend/tests/test_uv_orientation.py` :
#   1. pour TOUT triangle, le déterminant UV (du1*dv2 - du2*dv1) est NÉGATIF —
#      c'est la signature « pas de miroir » d'un enroulement CCW vu de dehors
#      avec v qui descend dans l'image ;
#   2. sur des points de sonde où l'orientation d'écran est non ambiguë,
#      dP/du pointe vers la droite et dP/dv vers le bas.
# Le cube, le plan et le pavage étaient déjà justes ; ils passent le test sans
# modification, ce qui prouve que le repère de référence n'a pas été déplacé
# pour arranger les autres.
_ORIENTATION = "u->droite, v->bas (aucun miroir)"

MESH_UV = {
    "sphere": (4.0, 2.0),      # 6.28/4 = 3.14/2 = 1.57 : tuiles exactement carrées
    "cube": (2.0, 2.0),        # face de 2 unités -> tuile de 1.0
    "torus": (6.0, 3.0),       # grand tour 4.40/6 = 0.73, petit tour 1.88/3 = 0.63
    "cylinder": (3.0, 1.0),    # paroi : périmètre 4.40/3 = 1.47, hauteur 1.8
    "plane": (1.0, 1.0),       # le plan montre UNE tuile, telle quelle
    "tiled": (1.0, 1.0),       # déjà 3x3 dans la géométrie
}

# Cadrage d'aperçu conseillé par maillage : (azimut, polaire, rayon, cible y).
# Publié par l'API pour que la visionneuse cadre sans tâtonner.
MESH_FRAME = {
    "sphere": (28.0, 74.0, 5.30, 0.00),
    "cube": (32.0, 72.0, 6.20, 0.00),
    "torus": (28.0, 66.0, 5.00, 0.05),
    "cylinder": (30.0, 74.0, 5.60, 0.00),
    "plane": (10.0, 82.0, 5.30, 0.00),
    "tiled": (12.0, 80.0, 5.60, 0.00),
}

# Le sol d'aperçu : quad de 16x16 unités (une case de grille = 1 unité).
STAGE_SPAN = 16.0

# Emplacements de texture reconnus dans `maps` (les autres sont ignorés :
# height n'a pas d'équivalent en glTF cœur, roughness/metallic/ao seuls
# servent uniquement de secours quand l'ORM packée est absente).
TEXTURE_SLOTS = ("basecolor", "normal", "orm", "emissive",
                 "roughness", "metallic", "ao")

DEFAULT_PROPS = {
    "color": "#ffffff", "metallic": 0.0, "roughness": 1.0, "opacity": 1.0,
    "emissive": "#000000", "emissive_strength": 0.0,
    "clearcoat": 0.0, "clearcoat_roughness": 0.0,
    "sheen": 0.0, "sheen_color": "#ffffff",
    "transmission": 0.0, "ior": 1.5, "thickness": 0.0,
    "normal_scale": 1.0, "ao_strength": 1.0, "displacement": 0.0,
    "tiling": 1.0, "rotation": 0.0,
}


# ── petites aides numériques ────────────────────────────────────────────────
def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _fnum(spec, key, default, lo=0.0, hi=1.0):
    """Lit un nombre du dictionnaire client, le borne, ne lève jamais."""
    try:
        v = float(spec.get(key, default))
    except (TypeError, ValueError):
        return float(default)
    if v != v or v in (float("inf"), float("-inf")):   # NaN / inf
        return float(default)
    return float(_clamp(v, lo, hi))


def _hex_rgb(value, default="#ffffff") -> tuple[float, float, float]:
    """'#rrggbb' -> (r, g, b) en 0..1 sRGB. Saisie invalide -> défaut."""
    s = str(value or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        s = str(default).lstrip("#")
    try:
        return (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0,
                int(s[4:6], 16) / 255.0)
    except ValueError:
        return (1.0, 1.0, 1.0)


def _srgb_to_linear(c: float) -> float:
    """glTF exige des facteurs de couleur LINÉAIRES ; l'UI donne du sRGB."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin_rgb(value, default="#ffffff") -> list[float]:
    return [round(_srgb_to_linear(c), 6) for c in _hex_rgb(value, default)]


def normalize_props(props: dict | None) -> dict:
    """Fusionne les propriétés client sur les défauts. Ne lève jamais."""
    p = dict(DEFAULT_PROPS)
    src = props if isinstance(props, dict) else {}
    p["color"] = "#%02x%02x%02x" % tuple(
        int(round(c * 255)) for c in _hex_rgb(src.get("color"), "#ffffff"))
    p["emissive"] = "#%02x%02x%02x" % tuple(
        int(round(c * 255)) for c in _hex_rgb(src.get("emissive"), "#000000"))
    p["sheen_color"] = "#%02x%02x%02x" % tuple(
        int(round(c * 255)) for c in _hex_rgb(src.get("sheen_color"), "#ffffff"))
    p["metallic"] = _fnum(src, "metallic", 0.0)
    p["roughness"] = _fnum(src, "roughness", 1.0)
    p["opacity"] = _fnum(src, "opacity", 1.0)
    p["emissive_strength"] = _fnum(src, "emissive_strength", 0.0, 0.0, 20.0)
    p["clearcoat"] = _fnum(src, "clearcoat", 0.0)
    p["clearcoat_roughness"] = _fnum(src, "clearcoat_roughness", 0.0)
    p["sheen"] = _fnum(src, "sheen", 0.0)
    p["transmission"] = _fnum(src, "transmission", 0.0)
    p["ior"] = _fnum(src, "ior", 1.5, 1.0, 3.0)
    p["thickness"] = _fnum(src, "thickness", 0.0, 0.0, 100.0)
    p["normal_scale"] = _fnum(src, "normal_scale", 1.0, 0.0, 8.0)
    p["ao_strength"] = _fnum(src, "ao_strength", 1.0, 0.0, 4.0)
    p["displacement"] = _fnum(src, "displacement", 0.0, 0.0, 4.0)
    p["tiling"] = _fnum(src, "tiling", 1.0, 0.01, 64.0)
    p["rotation"] = _fnum(src, "rotation", 0.0, -3600.0, 3600.0)
    return p


# ── maillages procéduraux ───────────────────────────────────────────────────
# Chaque générateur retourne (positions, normales, uv, indices) à plat.

def _mesh_sphere(sectors: int = 80, stacks: int = 40, radius: float = 1.0):
    """Sphère UV, avec les rangées SERRÉES AUX PÔLES.

    Aux pôles d'une sphère UV les méridiens convergent : la texture y est
    comprimée en u et, avec des rangées régulièrement espacées, la dernière
    couronne est un anneau de triangles longs qui étire visiblement le motif —
    le « pincement ». On ne peut pas le supprimer (c'est la paramétrisation
    elle-même), mais on peut le rendre petit : `phi` suit une répartition en
    cosinus, donc les rangées se resserrent près des pôles et s'espacent à
    l'équateur, à nombre de triangles quasi constant.

    Le v de texture reste `phi / pi` : la géométrie est redistribuée, PAS le
    placage. Une rangée dense porte donc une bande de texture étroite, ce qui
    est exactement l'effet cherché — le motif n'est plus étiré sur une couronne
    haute, il est découpé finement.
    """
    pos, nrm, uv = [], [], []
    for i in range(stacks + 1):
        t = i / stacks
        # cosinus : dérivée nulle en 0 et 1 -> rangées serrées aux deux pôles
        v = 0.5 * (1.0 - math.cos(math.pi * t))
        phi = v * math.pi                       # 0 au pôle nord
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(sectors + 1):
            u = j / sectors
            th = u * 2.0 * math.pi
            x, y, z = sp * math.cos(th), cp, sp * math.sin(th)
            pos += [x * radius, y * radius, z * radius]
            nrm += [x, y, z]
            # u renversé : sur la face vue (z > 0), u croissant descendait vers
            # la gauche de l'écran — la texture s'affichait en miroir. Voir
            # _ORIENTATION. v est déjà juste (0 au pôle nord = haut de l'image).
            uv += [1.0 - u, v]
    idx = []
    row = sectors + 1
    for i in range(stacks):
        for j in range(sectors):
            a = i * row + j
            b = a + row
            # les triangles dégénérés des deux calottes sont écartés
            if i != 0:
                idx += [a, a + 1, b]
            if i != stacks - 1:
                idx += [a + 1, b + 1, b]
    return pos, nrm, uv, idx


def _mesh_cube(half: float = 1.0):
    # (normale, droite, haut) avec cross(droite, haut) == normale : garantit
    # l'enroulement CCW vu de l'extérieur pour les six faces.
    faces = (
        ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
        ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
        ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
        ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
        ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
        ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    )
    pos, nrm, uv, idx = [], [], [], []
    for n, r, up in faces:
        base = len(pos) // 3
        for su, sv, tu, tv in ((-1, -1, 0.0, 1.0), (1, -1, 1.0, 1.0),
                               (1, 1, 1.0, 0.0), (-1, 1, 0.0, 0.0)):
            pos += [(n[k] + su * r[k] + sv * up[k]) * half for k in range(3)]
            nrm += list(n)
            uv += [tu, tv]
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return pos, nrm, uv, idx


def _mesh_torus(major: int = 48, minor: int = 24,
                big: float = 0.7, small: float = 0.3):
    pos, nrm, uv = [], [], []
    for i in range(major + 1):
        u = i / major
        cu, su = math.cos(u * 2 * math.pi), math.sin(u * 2 * math.pi)
        for j in range(minor + 1):
            v = j / minor
            cv, sv = math.cos(v * 2 * math.pi), math.sin(v * 2 * math.pi)
            ring = big + small * cv
            pos += [ring * cu, small * sv, ring * su]
            nrm += [cv * cu, sv, cv * su]
            # u ET v renversés : le grand tour partait vers la gauche (miroir)
            # et le petit tour faisait MONTER v sur la couronne extérieure — la
            # seule visible — donc la texture y était aussi à l'envers.
            uv += [1.0 - u, 1.0 - v]
    idx = []
    row = minor + 1
    for i in range(major):
        for j in range(minor):
            a = i * row + j
            b = a + 1
            c = a + row
            d = c + 1
            idx += [a, b, c, b, d, c]
    return pos, nrm, uv, idx


def _mesh_cylinder(seg: int = 48, radius: float = 0.7, half: float = 0.9):
    pos, nrm, uv, idx = [], [], [], []
    # paroi
    for j in range(seg + 1):
        u = j / seg
        th = u * 2 * math.pi
        cx, cz = math.cos(th), math.sin(th)
        # u renversé sur la PAROI (même miroir que la sphère). Les capuchons,
        # eux, étaient déjà justes : leur UV polaire est construit sur x et z
        # directement, avec le signe du capuchon inférieur déjà pris en compte.
        pos += [radius * cx, half, radius * cz]
        nrm += [cx, 0.0, cz]
        uv += [1.0 - u, 0.0]
        pos += [radius * cx, -half, radius * cz]
        nrm += [cx, 0.0, cz]
        uv += [1.0 - u, 1.0]
    for j in range(seg):
        a, b = 2 * j, 2 * j + 1          # haut / bas au segment j
        c, d = 2 * j + 2, 2 * j + 3      # haut / bas au segment j+1
        idx += [a, c, b, c, d, b]
    # capuchons : sommets dédiés (normale plate + UV polaire)
    for sign in (1.0, -1.0):
        center = len(pos) // 3
        pos += [0.0, half * sign, 0.0]
        nrm += [0.0, sign, 0.0]
        uv += [0.5, 0.5]
        for j in range(seg + 1):
            th = (j / seg) * 2 * math.pi
            cx, sz = math.cos(th), math.sin(th)
            pos += [radius * cx, half * sign, radius * sz]
            nrm += [0.0, sign, 0.0]
            uv += [0.5 + 0.5 * cx, 0.5 + 0.5 * sz * sign]
        for j in range(seg):
            r0, r1 = center + 1 + j, center + 2 + j
            idx += [center, r1, r0] if sign > 0 else [center, r0, r1]
    return pos, nrm, uv, idx


def _mesh_grid(cells: int, uv_span: float, half: float = 1.0):
    """Quad vertical (plan XY, normale +Z) subdivisé en `cells` x `cells`.
    `uv_span` = 1 pour le plan simple, 3 pour l'aperçu de pavage."""
    pos, nrm, uv, idx = [], [], [], []
    for j in range(cells + 1):
        ty = j / cells
        for i in range(cells + 1):
            tx = i / cells
            pos += [(-1 + 2 * tx) * half, (1 - 2 * ty) * half, 0.0]
            nrm += [0.0, 0.0, 1.0]
            uv += [tx * uv_span, ty * uv_span]
    row = cells + 1
    for j in range(cells):
        for i in range(cells):
            a = j * row + i
            b = a + 1
            c = a + row
            d = c + 1
            idx += [a, c, b, b, c, d]
    return pos, nrm, uv, idx


_BUILDERS = {
    "sphere": lambda: _mesh_sphere(),
    "cube": lambda: _mesh_cube(),
    "torus": lambda: _mesh_torus(),
    "cylinder": lambda: _mesh_cylinder(),
    "plane": lambda: _mesh_grid(1, 1.0),
    "tiled": lambda: _mesh_grid(3, 3.0),
}


def _tangents(pos, nrm, uv, idx):
    """Tangentes par sommet (Lengyel) : accumulation dP/du et dP/dv par
    triangle, puis Gram-Schmidt contre la normale. w donne la main du repère
    (bitangente = cross(N, T) * w), indispensable pour les UV en miroir."""
    n = len(pos) // 3
    tan = [0.0] * (n * 3)
    bit = [0.0] * (n * 3)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        p0, p1, p2 = i0 * 3, i1 * 3, i2 * 3
        q0, q1, q2 = i0 * 2, i1 * 2, i2 * 2
        e1 = (pos[p1] - pos[p0], pos[p1 + 1] - pos[p0 + 1], pos[p1 + 2] - pos[p0 + 2])
        e2 = (pos[p2] - pos[p0], pos[p2 + 1] - pos[p0 + 1], pos[p2 + 2] - pos[p0 + 2])
        du1, dv1 = uv[q1] - uv[q0], uv[q1 + 1] - uv[q0 + 1]
        du2, dv2 = uv[q2] - uv[q0], uv[q2 + 1] - uv[q0 + 1]
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-12:
            continue                      # triangle dégénéré en UV : ignoré
        f = 1.0 / det
        tx = (dv2 * e1[0] - dv1 * e2[0]) * f
        ty = (dv2 * e1[1] - dv1 * e2[1]) * f
        tz = (dv2 * e1[2] - dv1 * e2[2]) * f
        bx = (du1 * e2[0] - du2 * e1[0]) * f
        by = (du1 * e2[1] - du2 * e1[1]) * f
        bz = (du1 * e2[2] - du2 * e1[2]) * f
        for i in (i0, i1, i2):
            k = i * 3
            tan[k] += tx; tan[k + 1] += ty; tan[k + 2] += tz
            bit[k] += bx; bit[k + 1] += by; bit[k + 2] += bz
    out = []
    for i in range(n):
        k = i * 3
        nx, ny, nz = nrm[k], nrm[k + 1], nrm[k + 2]
        tx, ty, tz = tan[k], tan[k + 1], tan[k + 2]
        d = nx * tx + ny * ty + nz * tz
        tx -= nx * d; ty -= ny * d; tz -= nz * d
        ln = math.sqrt(tx * tx + ty * ty + tz * tz)
        if ln < 1e-8:
            # sommet sans UV exploitable (pôles) : n'importe quelle direction
            # orthogonale à la normale fait l'affaire, mieux qu'un zéro.
            ax = (0.0, 0.0, 1.0) if abs(nx) > 0.9 else (1.0, 0.0, 0.0)
            tx = ny * ax[2] - nz * ax[1]
            ty = nz * ax[0] - nx * ax[2]
            tz = nx * ax[1] - ny * ax[0]
            ln = math.sqrt(tx * tx + ty * ty + tz * tz) or 1.0
        tx, ty, tz = tx / ln, ty / ln, tz / ln
        # w : signe de dot(cross(N, T), B)
        cx = ny * tz - nz * ty
        cy = nz * tx - nx * tz
        cz = nx * ty - ny * tx
        w = -1.0 if (cx * bit[k] + cy * bit[k + 1] + cz * bit[k + 2]) < 0.0 else 1.0
        out += [tx, ty, tz, w]
    return out


def build_mesh(mesh: str, uv_repeat: tuple | None = None) -> dict:
    """Géométrie complète d'un maillage. `mesh` inconnu -> sphere.

    `uv_repeat` = (ru, rv) multiplie les coordonnées de texture : c'est
    l'échelle de la matière SUR le maillage (voir MESH_UV). Les tangentes sont
    recalculées APRÈS la mise à l'échelle — une tangente calculée sur les UV
    d'origine donnerait une normal map de travers dès que ru != rv."""
    name = str(mesh or "sphere").strip().lower()
    if name not in _BUILDERS:
        name = "sphere"
    pos, nrm, uv, idx = _BUILDERS[name]()
    if uv_repeat:
        try:
            ru = max(0.01, min(64.0, float(uv_repeat[0])))
            rv = max(0.01, min(64.0, float(uv_repeat[1])))
        except (TypeError, ValueError, IndexError):
            ru = rv = 1.0
        if abs(ru - 1.0) > 1e-9 or abs(rv - 1.0) > 1e-9:
            uv = [(v * ru if i % 2 == 0 else v * rv) for i, v in enumerate(uv)]
    return {"name": name, "positions": pos, "normals": nrm, "uvs": uv,
            "indices": idx, "tangents": _tangents(pos, nrm, uv, idx)}


def mesh_stats(mesh: str) -> dict:
    """Statistiques de topologie (reprises de Meshy dans l'UI)."""
    g = build_mesh(mesh)
    return {"mesh": g["name"], "vertices": len(g["positions"]) // 3,
            "triangles": len(g["indices"]) // 3, "indices": len(g["indices"])}


# ── empaquetage binaire ─────────────────────────────────────────────────────
class _Blob:
    """Tampon binaire du GLB : ajout avec alignement 4 octets imposé."""

    def __init__(self) -> None:
        self.buf = bytearray()

    def add(self, data: bytes) -> tuple[int, int]:
        while len(self.buf) % 4:
            self.buf.append(0)
        off = len(self.buf)
        self.buf += data
        return off, len(data)


def _mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    return "image/png"


def _tex_transform(props: dict) -> dict | None:
    """KHR_texture_transform : échelle de pavage + rotation autour du centre."""
    s = props["tiling"]
    deg = props["rotation"]
    if abs(s - 1.0) < 1e-6 and abs(deg) < 1e-6:
        return None
    r = math.radians(deg)
    cr, sr = math.cos(r), math.sin(r)
    # uv' = T * R * S * uv ; on veut la rotation centrée sur (0.5, 0.5)
    px, py = 0.5 * s, 0.5 * s
    ox = 0.5 - (cr * px + sr * py)
    oy = 0.5 - (-sr * px + cr * py)
    return {"offset": [round(ox, 6), round(oy, 6)],
            "rotation": round(r, 6), "scale": [s, s]}


def build_glb(maps: dict, props: dict | None = None, mesh: str = "sphere",
              name: str = "material", stage_png: bytes | None = None,
              uv_repeat: tuple | None = None) -> bytes:
    """Construit un GLB auto-suffisant.

    maps  : {"basecolor": png_bytes, "normal": ..., "orm": ..., "emissive": ...}
            Les octets sont recopiés tels quels (PNG ou JPEG). `orm` sert à la
            fois de metallicRoughnessTexture (G/B) et d'occlusionTexture (R),
            conformément à glTF ; en son absence on retombe sur `roughness`
            et `ao` séparés.
    props : propriétés de matière (voir DEFAULT_PROPS), fusionnées sur les
            défauts — une valeur absente ou aberrante n'est jamais une erreur.
    mesh  : un nom de MESHES ; toute autre valeur retombe sur "sphere".
    stage_png : PNG RGBA du sol d'aperçu (stage_service). Fourni, un quad de
            STAGE_SPAN unités est ajouté sous l'objet avec son propre matériau
            (grille + flaque de contact cuite, alpha en fondu radial). Absent,
            le GLB est exactement celui d'avant — l'export ne trimballe donc
            jamais de décor.
    uv_repeat : (ru, rv) échelle de la matière sur le maillage (MESH_UV).
    """
    p = normalize_props(props)
    g = build_mesh(mesh, uv_repeat)
    src = maps if isinstance(maps, dict) else {}

    blob = _Blob()
    views: list[dict] = []
    accessors: list[dict] = []

    def view(data: bytes, target: int | None = None) -> int:
        off, ln = blob.add(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": ln}
        if target is not None:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    def attr(values: list[float], comps: int, kind: str,
             minmax: bool = False) -> int:
        vi = view(struct.pack("<%df" % len(values), *values), _ARRAY_BUFFER)
        a = {"bufferView": vi, "componentType": _FLOAT,
             "count": len(values) // comps, "type": kind}
        if minmax:
            lo = [min(values[i::comps]) for i in range(comps)]
            hi = [max(values[i::comps]) for i in range(comps)]
            a["min"] = [round(x, 6) for x in lo]
            a["max"] = [round(x, 6) for x in hi]
        accessors.append(a)
        return len(accessors) - 1

    a_pos = attr(g["positions"], 3, "VEC3", minmax=True)
    a_nrm = attr(g["normals"], 3, "VEC3")
    a_uv = attr(g["uvs"], 2, "VEC2")
    a_tan = attr(g["tangents"], 4, "VEC4")

    idx = g["indices"]
    nverts = len(g["positions"]) // 3
    if nverts <= 65535:
        ctype, packed = _UNSIGNED_SHORT, struct.pack("<%dH" % len(idx), *idx)
    else:
        ctype, packed = _UNSIGNED_INT, struct.pack("<%dI" % len(idx), *idx)
    vi = view(packed, _ELEMENT_ARRAY_BUFFER)
    accessors.append({"bufferView": vi, "componentType": ctype,
                      "count": len(idx), "type": "SCALAR"})
    a_idx = len(accessors) - 1

    # Emplacements REELLEMENT utilisés. L'ORM sert à la fois de
    # metallicRoughnessTexture et d'occlusionTexture : quand elle est là,
    # roughness/metallic/ao séparées ne sont référencées par rien. Les embarquer
    # quand même gonflait le GLB pour rien — 4.78 Mo mesurés à l'export d'« or
    # martelé » en 1024, dont 1.9 Mo de textures qu'aucun matériau ne lit.
    have = {s for s in TEXTURE_SLOTS
            if isinstance(src.get(s), (bytes, bytearray)) and len(src[s]) >= 16}
    # roughness et metallic séparées ne sont référençables par aucun
    # emplacement glTF (le format ne connaît que la paire packée) ; l'AO ne
    # l'est que si l'ORM manque.
    have -= {"roughness", "metallic"}
    if "orm" in have:
        have.discard("ao")

    images: list[dict] = []
    textures: list[dict] = []
    tex_index: dict[str, int] = {}
    for slot in TEXTURE_SLOTS:
        if slot not in have:
            continue
        data = bytes(src[slot])
        bv = view(data)
        images.append({"bufferView": bv, "mimeType": _mime(data), "name": slot})
        textures.append({"sampler": 0, "source": len(images) - 1})
        tex_index[slot] = len(textures) - 1

    xform = _tex_transform(p)

    def tex_ref(slot: str, **extra):
        if slot not in tex_index:
            return None
        ref = {"index": tex_index[slot], "texCoord": 0}
        ref.update(extra)
        if xform:
            ref["extensions"] = {"KHR_texture_transform": dict(xform)}
        return ref

    # ORM packée : R=AO, G=roughness, B=metallic — exactement la convention
    # glTF : une seule image sert deux emplacements.
    #
    # Une roughness SEULE ne peut pas servir de metallicRoughnessTexture : son
    # canal B vaut le gris de la rugosité, et le moteur le lirait comme de la
    # métallicité (une matière rugueuse deviendrait métallique). Sans ORM, on
    # ne pose donc aucune texture ici — les facteurs reprennent leur rôle.
    mr_slot = "orm" if "orm" in tex_index else None
    ao_slot = "orm" if "orm" in tex_index else (
        "ao" if "ao" in tex_index else None)

    # Le niveau est cuit dans la map (bake_levels) : le facteur ne doit PAS le
    # multiplier une seconde fois, sinon 0.28 x 0.28 = 0.08. Il repasse à sa
    # valeur réglée uniquement quand aucune texture ne porte le canal.
    pbr: dict = {
        "baseColorFactor": _lin_rgb(p["color"]) + [round(p["opacity"], 6)],
        "metallicFactor": 1.0 if mr_slot else round(p["metallic"], 6),
        "roughnessFactor": 1.0 if mr_slot else round(p["roughness"], 6),
    }
    bc = tex_ref("basecolor")
    if bc:
        pbr["baseColorTexture"] = bc
    if mr_slot:
        pbr["metallicRoughnessTexture"] = tex_ref(mr_slot)

    emissive = [round(_clamp(c * p["emissive_strength"]), 6)
                for c in _lin_rgb(p["emissive"], "#000000")]

    # `extras` : la composition scalaire x texture, écrite DANS le fichier.
    # Les deux niveaux sont cuits ensemble ou pas du tout — ils partagent
    # l'image (ORM V = rugosité, B = métal), donc un seul et même booléen.
    material: dict = {
        "name": str(name or "material")[:120],
        "pbrMetallicRoughness": pbr,
        "emissiveFactor": emissive,
        "doubleSided": True,
        "extras": {
            "generator": "DeepotusVideoGen Material Forge",
            "levelsBaked": ["metallic", "roughness"] if mr_slot else [],
            "note": (
                "metallicFactor et roughnessFactor valent 1.0 : les niveaux "
                "sont cuits dans metallicRoughnessTexture (V = rugosite, "
                "B = metal). Ne pas les reappliquer."
                if mr_slot else
                "Aucune metallicRoughnessTexture : les facteurs portent seuls "
                "les niveaux regles."),
            "settings": {"metallic": round(p["metallic"], 6),
                         "roughness": round(p["roughness"], 6)},
        },
    }
    nt = tex_ref("normal", scale=round(p["normal_scale"], 6))
    if nt:
        material["normalTexture"] = nt
    ot = tex_ref(ao_slot, strength=round(p["ao_strength"], 6)) if ao_slot else None
    if ot:
        material["occlusionTexture"] = ot
    et = tex_ref("emissive")
    if et:
        material["emissiveTexture"] = et

    # KHR_materials_transmission impose alphaMode OPAQUE : c'est l'extension
    # qui gère la transparence physique, pas le canal alpha.
    if p["transmission"] <= 0.0 and p["opacity"] < 1.0:
        material["alphaMode"] = "BLEND"

    ext: dict = {}
    if p["clearcoat"] > 0.0:
        ext["KHR_materials_clearcoat"] = {
            "clearcoatFactor": round(p["clearcoat"], 6),
            "clearcoatRoughnessFactor": round(p["clearcoat_roughness"], 6)}
    if p["sheen"] > 0.0:
        ext["KHR_materials_sheen"] = {
            "sheenColorFactor": [round(c * p["sheen"], 6)
                                 for c in _lin_rgb(p["sheen_color"])],
            "sheenRoughnessFactor": round(p["roughness"], 6)}
    if p["transmission"] > 0.0:
        ext["KHR_materials_transmission"] = {
            "transmissionFactor": round(p["transmission"], 6)}
    if abs(p["ior"] - 1.5) > 1e-6:
        ext["KHR_materials_ior"] = {"ior": round(p["ior"], 6)}
    if ext:
        material["extensions"] = ext

    used = sorted(set(ext) | ({"KHR_texture_transform"} if xform else set()))

    materials = [material]
    nodes = [{"mesh": 0, "name": g["name"]}]
    meshes = [{
        "name": g["name"],
        "primitives": [{
            "attributes": {"POSITION": a_pos, "NORMAL": a_nrm,
                           "TEXCOORD_0": a_uv, "TANGENT": a_tan},
            "indices": a_idx, "material": 0, "mode": 4,
        }],
    }]

    # ── sol d'aperçu ────────────────────────────────────────────────────────
    if isinstance(stage_png, (bytes, bytearray)) and len(stage_png) > 16:
        ys = g["positions"][1::3]
        y = (min(ys) if ys else -1.0) - 0.02          # juste sous l'objet
        h = STAGE_SPAN / 2.0
        # ordre CCW vu de +Y : la normale géométrique est bien vers le haut.
        corners = ((-h, -h), (-h, h), (h, h), (h, -h))
        s_pos, s_nrm, s_uv, s_tan = [], [], [], []
        for cx, cz in corners:
            s_pos += [cx, y, cz]
            s_nrm += [0.0, 1.0, 0.0]
            s_uv += [0.5 + cx / STAGE_SPAN, 0.5 + cz / STAGE_SPAN]
            s_tan += [1.0, 0.0, 0.0, 1.0]
        sa_pos = attr(s_pos, 3, "VEC3", minmax=True)
        sa_nrm = attr(s_nrm, 3, "VEC3")
        sa_uv = attr(s_uv, 2, "VEC2")
        sa_tan = attr(s_tan, 4, "VEC4")
        svi = view(struct.pack("<6H", 0, 1, 2, 0, 2, 3), _ELEMENT_ARRAY_BUFFER)
        accessors.append({"bufferView": svi, "componentType": _UNSIGNED_SHORT,
                          "count": 6, "type": "SCALAR"})
        sa_idx = len(accessors) - 1

        sbv = view(bytes(stage_png))
        images.append({"bufferView": sbv, "mimeType": _mime(bytes(stage_png)),
                       "name": "stage"})
        # échantillonneur 1 : bords bloqués. Un REPEAT ferait réapparaître la
        # grille en damier au-delà du fondu, et donc un raccord visible.
        textures.append({"sampler": 1, "source": len(images) - 1})
        s_tex = len(textures) - 1

        materials.append({
            "name": "stage",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "baseColorTexture": {"index": s_tex, "texCoord": 0},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.82,
            },
            # émissif à pleine échelle : le plateau reste lisible même en
            # environnement « Nuit », sans jamais dépasser sa propre texture.
            "emissiveTexture": {"index": s_tex, "texCoord": 0},
            "emissiveFactor": [1.0, 1.0, 1.0],
            "alphaMode": "BLEND",
            "doubleSided": True,
        })
        meshes.append({
            "name": "stage",
            "primitives": [{
                "attributes": {"POSITION": sa_pos, "NORMAL": sa_nrm,
                               "TEXCOORD_0": sa_uv, "TANGENT": sa_tan},
                "indices": sa_idx, "material": len(materials) - 1, "mode": 4,
            }],
        })
        nodes.append({"mesh": 1, "name": "stage"})

    gltf: dict = {
        "asset": {"version": "2.0",
                  "generator": "DeepotusVideoGen Material Forge"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes))), "name": "Material Forge"}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": 0}],
    }
    if images:
        gltf["images"] = images
        gltf["textures"] = textures
        gltf["samplers"] = [{"magFilter": _LINEAR,
                             "minFilter": _LINEAR_MIPMAP_LINEAR,
                             "wrapS": _REPEAT, "wrapT": _REPEAT}]
        if len(materials) > 1:            # le sol seul a besoin du sampler 1
            gltf["samplers"].append({"magFilter": _LINEAR,
                                     "minFilter": _LINEAR_MIPMAP_LINEAR,
                                     "wrapS": _CLAMP, "wrapT": _CLAMP})
    if used:
        gltf["extensionsUsed"] = used

    while len(blob.buf) % 4:
        blob.buf.append(0)
    gltf["buffers"][0]["byteLength"] = len(blob.buf)

    js = json.dumps(gltf, separators=(",", ":"),
                    ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)          # bourrage JSON : espaces
    bins = bytes(blob.buf)                        # bourrage BIN : zéros (fait)

    total = 12 + 8 + len(js) + (8 + len(bins) if bins else 0)
    out = bytearray()
    out += struct.pack("<III", _GLB_MAGIC, _GLB_VERSION, total)
    out += struct.pack("<II", len(js), _CHUNK_JSON) + js
    if bins:
        out += struct.pack("<II", len(bins), _CHUNK_BIN) + bins
    return bytes(out)


def __getattr__(attr_name: str):
    """Passerelle paresseuse vers env_service (la SPEC section 6 autorise les
    deux emplacements). Garde ce module stdlib-pur tant qu'on ne demande pas
    un environnement : `from app.services.gltf_builder import env_list`
    fonctionne quand même."""
    if attr_name in ("ENVS", "env_list", "env_names", "env_bytes",
                     "env_path", "build_env", "ENV_W", "ENV_H"):
        from app.services import env_service
        return getattr(env_service, attr_name)
    raise AttributeError(attr_name)
