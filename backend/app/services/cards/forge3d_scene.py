# -*- coding: utf-8 -*-
# NB (revue) : le test de pureté scanne TOUT ce fichier, commentaires compris
# — le nom du framework HTTP du projet ne doit apparaître nulle part ici,
# même en prose (voir test_cards_forge3d.py, l'assertion sur ce mot en
# minuscules : un rappel de SON nom ici la ferait échouer).
"""P9 Forge 3D — géométrie et écriture de scène, PURES (zéro dépendance HTTP).

Couture intra-pièce actée par la revue finale de la 2a (legs 6) : forge3d.py
garde le contrat HTTP (routes, bornes, blocs miroir) et RÉEXPORTE ces noms —
les tests et l'API ne changent pas. Règle 8 inchangée : aucune importation
d'une autre pièce du lab.
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import math
import struct
from functools import lru_cache


# ── LA GÉOMÉTRIE LOCALE — PLAN, RELIEF, MESURES ─────────────────────────────
# `quad_mesh`/`relief_mesh` produisent le maillage minimal qu'un traitement
# `plane`/`relief` du graphe fabrique ; `mesh_measures` en tire la preuve de
# fermeture/volume — COPIE LOCALE réduite du principe de `mesh_report` de P8
# (règle 8 : zéro import pièce->pièce, même patron que `_dpi_to_ppm`/`_num`
# de forge3d.py). Type commun aux trois : {positions, normals, uvs, indices},
# consommé plus loin par `write_scene_glb` (Task 3).
def quad_mesh(w_mm: float, h_mm: float,
             uv_window: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
             ) -> dict:
    """Un quad aux dimensions de la carte, normale +z. `uv_window`
    (u0, v0, u1, v1) — défaut plein 0..1, rétrocompatible — INSET les UV
    émises dans cette fenêtre au lieu de la texture entière : voir le
    commentaire-contrainte au point d'appel (`post_build3d`) sur la
    différence toile/coupe que cette fenêtre réconcilie."""
    u0, v0, u1, v1 = uv_window
    return {
        "positions": [0.0, 0.0, 0.0, w_mm, 0.0, 0.0, w_mm, h_mm, 0.0,
                      0.0, h_mm, 0.0],
        "normals": [0.0, 0.0, 1.0] * 4,
        "uvs": [u0, v1, u1, v1, u1, v0, u0, v0],   # v inversé (image)
        "indices": [0, 1, 2, 0, 2, 3],
        "closed": False,             # un plan n'est pas un solide
        # DÉCLARATION, pas une mesure : ce quad a ses UV alignées sur les axes
        # (u suit +x, v suit -y), donc la tangente CONSTANTE que le writer
        # émet pour l'anisotropie est juste. Un maillage venu d'un moteur
        # (mesh3d) n'a AUCUNE raison de l'être : le writer refuse alors
        # l'anisotropie au lieu de peigner de travers (garde Task 6).
        "uv_axis_aligned": True,
    }


def relief_mesh(alpha_img, w_mm: float, h_mm: float, depth_mm: float,
                base_mm: float, grid: int,
                uv_window: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
                ) -> dict:
    """LA DALLE EN RELIEF : une grille (grid x grid') dont la face du dessus
    est déplacée par l'alpha de la couche (0 -> base, 255 -> base+depth), face
    du dessous plate à z=0, murs périphériques — un solide FERMÉ PAR
    CONSTRUCTION : chaque arête appartient à exactement deux triangles parce
    que dessus, dessous et murs partagent leurs anneaux de bord. C'est
    l'« extrusion » gratuite v1 : un vrai suivi de contour (marching squares +
    triangulation à trous) viendra si le besoin le prouve.

    `alpha_img` doit déjà être la région de COUPE (pas la toile — c'est
    l'appelant, `post_build3d`, qui croppe avant d'appeler ici : cette
    fonction n'a pas la géométrie du deck pour le faire elle-même).
    `uv_window` (u0, v0, u1, v1) — défaut plein 0..1, rétrocompatible — INSET
    les UV dans cette fenêtre pour que la texture (le PNG de toile complet,
    octets intacts) se plaque correctement sur une géométrie qui, elle, ne
    couvre que la coupe.

    Préconditions : bornes garanties par `clean_graph` (base_mm/depth_mm/grid)
    — hors de ce chemin, base_mm=0 dégénère les murs et w_mm=0 divise par
    zéro."""
    u0, v0, u1, v1 = uv_window
    gx = max(2, int(grid))
    gy = max(2, int(round(grid * (h_mm / w_mm))))
    a = alpha_img.convert("L").resize((gx + 1, gy + 1))
    px = list(a.getdata())          # (gx+1)*(gy+1) échantillons

    def z_at(i, j):
        return base_mm + (px[j * (gx + 1) + i] / 255.0) * depth_mm

    pos, uv = [], []
    # dessus : (gx+1)*(gy+1) sommets déplacés
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, z_at(i, j)]
            uv += [u0 + (i / gx) * (u1 - u0), v0 + (j / gy) * (v1 - v0)]
    top = lambda i, j: j * (gx + 1) + i                      # noqa: E731
    n_top = (gx + 1) * (gy + 1)
    # dessous : mêmes (x, y), z=0 (UV répliquées, sans importance au dos)
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, 0.0]
            uv += [u0 + (i / gx) * (u1 - u0), v0 + (j / gy) * (v1 - v0)]
    bot = lambda i, j: n_top + j * (gx + 1) + i              # noqa: E731

    # WINDING : avec y=(1-j/gy)*h, j=0 est le HAUT de carte ; l'ordre ci-dessous
    # donne une aire signée POSITIVE vue de +z (normales dehors), prouvé par le
    # test (closed ET volume>0 sur silhouette à trou). Garde-fou : une inversion
    # UNIFORME du maillage garde closed=True et ne flippe QUE le signe du volume
    # — c'est l'assertion volume>0 qui protège contre une régression, pas closed.
    idx = []
    for j in range(gy):
        for i in range(gx):
            aa, bb = top(i, j), top(i + 1, j)
            cc, dd = top(i + 1, j + 1), top(i, j + 1)
            idx += [aa, cc, bb, aa, dd, cc]                  # dessus, +z
            a2, b2 = bot(i, j), bot(i + 1, j)
            c2, d2 = bot(i + 1, j + 1), bot(i, j + 1)
            idx += [a2, b2, c2, a2, c2, d2]                  # dessous, -z
    # murs : les 4 bords, quads entre anneau du dessus et anneau du dessous
    def wall(t1, t2, b1, b2):
        idx.extend([t1, b2, b1, t1, t2, b2])
    for i in range(gx):                                       # j=0 et j=gy
        wall(top(i, 0), top(i + 1, 0), bot(i, 0), bot(i + 1, 0))
        wall(top(i + 1, gy), top(i, gy), bot(i + 1, gy), bot(i, gy))
    for j in range(gy):                                       # i=0 et i=gx
        wall(top(0, j + 1), top(0, j), bot(0, j + 1), bot(0, j))
        wall(top(gx, j), top(gx, j + 1), bot(gx, j), bot(gx, j + 1))

    # normales : accumulation de normales de faces pondérées par l'aire sur
    # les sommets partagés ; connu : l'anneau de bord mélange mur et face,
    # l'arête du pourtour s'ombre adoucie — géométrie exacte, STL non affecté
    # (normales de facette recalculées).
    nrm = [0.0] * len(pos)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
        ux, uy, uz = (pos[i1] - pos[i0], pos[i1 + 1] - pos[i0 + 1], pos[i1 + 2] - pos[i0 + 2])
        vx, vy, vz = (pos[i2] - pos[i0], pos[i2 + 1] - pos[i0 + 1], pos[i2 + 2] - pos[i0 + 2])
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for k in (i0, i1, i2):
            nrm[k] += cx; nrm[k + 1] += cy; nrm[k + 2] += cz
    for k in range(0, len(nrm), 3):
        ln = math.sqrt(nrm[k] ** 2 + nrm[k + 1] ** 2 + nrm[k + 2] ** 2) or 1.0
        nrm[k] /= ln; nrm[k + 1] /= ln; nrm[k + 2] /= ln
    # "closed": fermeture TOPOLOGIQUE, indépendante du contenu alpha —
    # prouvée une fois pour toutes par le test unitaire ; la route build3d
    # gate le STL sur ce drapeau au lieu de re-mesurer : 7 s + ~340 Mo de pic
    # par élément au grid max, mesuré en revue.
    # `uv_axis_aligned` : la grille du dessus (et celle du dessous) plaque u
    # sur +x et v sur -y comme le quad — la tangente constante du writer y est
    # juste. Les MURS, eux, héritent d'un repère dégénéré (voir le commentaire
    # du bloc TANGENT dans `write_scene_glb`) : c'est assumé, la jupe fait
    # 0,3 mm et ne reçoit pas de peigne visible.
    return {"positions": pos, "normals": nrm, "uvs": uv, "indices": idx,
            "closed": True, "uv_axis_aligned": True}


def mesh_measures(mesh: dict) -> dict:
    """Fermeture et volume signé, MESURES locales — copie du principe de
    `mesh_report` de P8 (règle 8 : pas d'import pièce->pièce), réduite aux
    deux chiffres dont l'artefact a besoin (closed, volume)."""
    pos, idx = mesh["positions"], mesh["indices"]
    edges: dict = {}
    vol = 0.0
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            ka = (round(pos[a * 3], 6), round(pos[a * 3 + 1], 6), round(pos[a * 3 + 2], 6))
            kb = (round(pos[b * 3], 6), round(pos[b * 3 + 1], 6), round(pos[b * 3 + 2], 6))
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
        a3, b3, c3 = tri[0] * 3, tri[1] * 3, tri[2] * 3
        vol += (pos[a3] * (pos[b3 + 1] * pos[c3 + 2] - pos[b3 + 2] * pos[c3 + 1])
                - pos[a3 + 1] * (pos[b3] * pos[c3 + 2] - pos[b3 + 2] * pos[c3])
                + pos[a3 + 2] * (pos[b3] * pos[c3 + 1] - pos[b3 + 1] * pos[c3])) / 6.0
    closed = bool(edges) and all(n == 2 for n in edges.values())
    return {"closed": closed, "volume_mm3": vol,
            "triangles": len(idx) // 3, "vertices": len(pos) // 3}


# ── LES MATIÈRES ET LES FINITIONS — DES OCTETS PRÊTS POUR LE WRITER (2b) ────
# `material_pngs` et `holo_finish` ne connaissent NI la boutique de matières NI
# les routes : elles reçoivent des images PIL (ou rien du tout) et rendent des
# OCTETS PNG que `write_scene_glb` embarque tels quels. C'est ce qui garde ce
# module PUR (règle 8 : zéro import d'une autre pièce du lab).
#
# COROLLAIRE, ACTÉ EN REVUE DE LA TASK 5 : le tuilage au pas physique, lui, a
# besoin de la boutique (`material_store`) pour aller chercher les maps d'une
# matière et cuire ses niveaux. Il vit donc dans forge3d.py, à côté du contrat
# HTTP (`tile_maps`), et pas ici — le plan 2b le plaçait dans ce fichier, la
# pureté du module a primé. Le partage des rôles reste net : forge3d.py va
# chercher les images, ce module les transforme en octets.


def _f(raw, default: float = 0.0) -> float:
    """Un flottant, ou le défaut — JAMAIS une exception sur une entrée
    douteuse (même discipline que `_num` côté contrat HTTP). NaN et infinis
    retombent aussi sur le défaut : écrits dans un GLB ils y seraient du JSON
    invalide (`NaN` n'existe pas dans la grammaire JSON)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):
        return default
    return v


def _png_bytes(img) -> bytes:
    """Une image PIL en octets PNG — le seul format que le writer embarque."""
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def material_pngs(maps: dict) -> dict:
    """Les maps d'une matière, CUITES en PNG pour le writer.

    Sortie : `{"normal", "mr", "ao", "emissive"}` en octets PNG — SEULEMENT
    ce qui existe en entrée (une matière sans normale ne fabrique pas une
    normale plate pour faire nombre). Le pack `mr` suit la convention glTF,
    celle que le lab Matières applique déjà à son ORM (R=AO, G=Roughness,
    B=Metallic) : ici R est neutre (255), G porte la rugosité, B la
    métallicité. L'occlusion voyage à part parce que le writer la câble sur
    SON entrée dédiée (`occlusionTexture`), pas dans le pack.

    Rugosité ou métallicité SEULE : le canal manquant prend le neutre du
    MOTEUR — rugosité 255 (entièrement mate) et métallicité 0 (diélectrique).
    Un zéro par défaut dans les deux cas rendrait un MIROIR PARFAIT à qui ne
    fournit qu'une rugosité.

    Les niveaux sont DANS les octets : c'est le writer qui remet
    metallicFactor/roughnessFactor à 1.0 (doctrine `RENDER_NOTE` du lab
    Matières — appliquer le curseur EN PLUS le compterait deux fois)."""
    # PIL importé LOCALEMENT : ce module ne dépend de PIL que là où il
    # FABRIQUE une image ; la géométrie, elle, en reçoit et n'a rien à
    # importer (patron déjà en place dans `relief_mesh`).
    from PIL import Image
    out: dict = {}
    nrm = maps.get("normal")
    if nrm is not None:
        out["normal"] = _png_bytes(nrm.convert("RGB"))
    ao = maps.get("ao")
    if ao is not None:
        out["ao"] = _png_bytes(ao.convert("L").convert("RGB"))
    emi = maps.get("emissive")
    if emi is not None:
        out["emissive"] = _png_bytes(emi.convert("RGB"))
    rough, metal = maps.get("roughness"), maps.get("metallic")
    if rough is not None or metal is not None:
        # taille de RÉFÉRENCE : la PLUS GRANDE des deux, pas la première venue.
        # Un pack RGB exige trois canaux de même dimension (`Image.merge`
        # lèverait sinon) ; aligner sur la plus petite JETTERAIT le détail de
        # l'autre, définitivement, pour n'avoir rien gagné.
        cotes = [im.size for im in (rough, metal) if im is not None]
        taille = max(cotes, key=lambda s: s[0] * s[1])
        g = (rough.convert("L") if rough is not None
             else Image.new("L", taille, 255))
        b = (metal.convert("L") if metal is not None
             else Image.new("L", taille, 0))
        # filtre de rééchantillonnage EXPLICITE (convention de
        # `material_store.resize_maps` : LANCZOS pour les maps de couleur,
        # BICUBIC pour les maps de données). Le défaut de PIL a déjà changé
        # d'une version à l'autre — le laisser implicite ferait dépendre nos
        # octets de la version de Pillow installée, et le déterminisme est
        # une PROMESSE ici, pas un effet de bord.
        if g.size != taille:
            g = g.resize(taille, Image.BICUBIC)
        if b.size != taille:
            b = b.resize(taille, Image.BICUBIC)
        out["mr"] = _png_bytes(
            Image.merge("RGB", (Image.new("L", taille, 255), g, b)))
    return out


# §6.2bis-c — les DEUX recettes de finition, chiffres de la spec, relus au bit
# près par le test.
_HOLO_RECIPES = {
    "argent": {"base": [0.95, 0.95, 0.97, 1.0], "rough": 0.12, "ior": 1.8,
               "thickness": [200.0, 900.0]},
    "dorure": {"base": [1.0, 0.84, 0.55, 1.0], "rough": 0.12, "ior": 1.6,
               "thickness": [200.0, 600.0]},
}
_HOLO_SECTORS = 48   # secteurs radiaux : mip-stables, zéro moiré (§6.2bis-c)
_HOLO_CYCLE = 8          # niveaux d'épaisseur, un cycle complet tous les 8
_HOLO_ANISO_STRENGTH = 0.85
_HOLO_CLEARCOAT_ROUGH = 0.06
# §6.2bis : les finitions se cuisent entre 1024 et 2048. Le plafond est ICI,
# et le MÊME que celui de `tile_maps` (bornes symétriques, revue Task 5) :
# 4096² coûtait ~17 s et ~200 Mo pour un gain invisible sur une carte de
# 63 mm — un chiffre venu d'un graphe ne doit pas pouvoir l'atteindre.
HOLO_PX = (8, 2048)

# La liste blanche PUBLIÉE : l'appelant borne son entrée avec elle au lieu de
# recopier deux noms qui dériveront (même patron que les blocs miroir).
HOLO_KINDS = tuple(_HOLO_RECIPES)

# ── LES MOTIFS INCRUSTÉS (3c) — spec §6.2bis-d :435-440 ─────────────────────
# « un ou PLUSIEURS calques de motif/symbole [...] encodés dans le canal G de
# l'iridescenceThicknessTexture (addition bornée des épaisseurs, ordre des
# calques = ordre d'addition) [...] Déterministe (mêmes calques -> mêmes
# octets) ». Ce module ne connaît que des OCTETS : c'est l'appelant (le
# contrat HTTP) qui sait où vivent les fichiers et qui AVOUE ce qu'il n'a pas
# trouvé. Ici, les octets d'un calque et sa part, rien d'autre.
MOTIF_MAX = 4                  # calques ; au-delà, les QUATRE PREMIERS (§6.2bis
                               # dit « un ou plusieurs », pas « autant qu'on
                               # veut » : chaque calque est un rééchantillonnage
                               # plein format, et quatre franges superposées ne
                               # se lisent déjà plus à l'œil)
MOTIF_GAIN = (0.1, 1.0)        # la PART du calque dans l'addition bornée
MOTIF_MAX_PIXELS = 32 * 1024 * 1024   # bombe de pixels : LE décodage est ici,
                                      # donc la garde aussi (copie locale du
                                      # chiffre du domaine, règle 8)


# ── LE CACHE DES OCTETS D'ÉPAISSEUR ─────────────────────────────────────────
# La 2b cachait sur UN entier (`out_px`) par `lru_cache`. Avec les motifs, la
# clé doit porter LA PILE — sans quoi deux cartes aux motifs différents
# partageraient une entrée et la seconde recevrait l'hologramme de la
# première, SANS UN MOT. La clé est donc `(out_px, ((sha256, gain), ...))`.
#
# POURQUOI PLUS `lru_cache` : sa clé RETIENT tous les arguments. Les octets
# sources d'un calque (une image de jeu peut peser des dizaines de Mo) y
# resteraient vivants pour la durée de l'entrée — huit entrées x quatre
# calques, et le cache d'une texture de 2 Mo tiendrait des centaines de Mo
# d'images en otage. Ce cache-ci ne garde QUE des empreintes (64 caractères
# par calque) et la sortie ; les images sources sont libérées à la sortie de
# l'appel. `cache_info()`/`cache_clear()` gardent l'orthographe de functools :
# le lecteur suivant n'a pas à apprendre un second vocabulaire.
THICK_CACHE_MAX = 8            # même budget qu'avant : deux tailles servies
                               # (1024, 2048) x les piles d'une session ; les
                               # tailles des tests tiennent dans le reste
_THICK_CACHE: "collections.OrderedDict[tuple, bytes]" = collections.OrderedDict()
_THICK_STATS = {"hits": 0, "misses": 0}


def _thick_cache_info() -> dict:
    return dict(_THICK_STATS, size=len(_THICK_CACHE))


def _thick_cache_clear() -> None:
    _THICK_CACHE.clear()
    _THICK_STATS.update(hits=0, misses=0)


def motif_pile(motifs) -> tuple:
    """La PILE CANONIQUE : `((sha256, gain, octets), ...)`, dans l'ORDRE reçu,
    bornée à `MOTIF_MAX` calques et à `MOTIF_GAIN` de part.

    Ce qui n'a pas d'octets est SAUTÉ ici sans un mot — et c'est voulu : la
    seule chose que ce module puisse dire d'une entrée vide, c'est « vide ».
    Qui elle était, d'où elle venait et pourquoi elle manque appartiennent à
    l'appelant, qui l'a résolue et qui l'AVOUE au bordereau (doctrine
    `ignored`)."""
    pile = []
    for m in (motifs or ()):
        try:
            raw, gain = m
        except (TypeError, ValueError):
            continue
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            continue
        g = _f(gain, 1.0)
        g = MOTIF_GAIN[0] if g < MOTIF_GAIN[0] else \
            MOTIF_GAIN[1] if g > MOTIF_GAIN[1] else g
        pile.append((hashlib.sha256(bytes(raw)).hexdigest(), g, bytes(raw)))
        if len(pile) >= MOTIF_MAX:
            break
    return tuple(pile)


def _motif_luma(raw: bytes, out_px: int):
    """UN calque, réduit à ce que le canal G sait porter : une LUMINANCE au
    format de la texture. ValueError NOMMÉE si l'image est illisible ou trop
    grande — l'appelant en fait un aveu, jamais un 500 (doctrine 2.5).

    L'ALPHA EST COMPOSÉ SUR DU NOIR, et ce n'est pas cosmétique : `convert("L")`
    IGNORE le canal alpha, si bien qu'un sigle transparent dont les pixels
    invisibles portent du blanc (le cas ordinaire d'un PNG détouré) déposerait
    son épaisseur SUR TOUTE LA CARTE. Transparent = rien à déposer.

    Filtre EXPLICITE (BICUBIC, convention « maps de données » du fichier) : le
    défaut de la bibliothèque a déjà changé d'une version à l'autre, et le
    déterminisme est une PROMESSE ici, pas un effet de bord."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        if w * h > MOTIF_MAX_PIXELS:
            raise ValueError(
                f"motif de {w}x{h} px : au-dela de {MOTIF_MAX_PIXELS // 1048576} "
                f"megapixels, non decode")
        im.load()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"motif illisible ({e or type(e).__name__})")
    if "A" in im.getbands():
        fond = Image.new("RGBA", im.size, (0, 0, 0, 255))
        im = Image.alpha_composite(fond, im.convert("RGBA"))
    lum = im.convert("L")
    if lum.size != (out_px, out_px):
        lum = lum.resize((out_px, out_px), Image.BICUBIC)
    return lum


def _holo_thickness_png(out_px: int, pile: tuple = ()) -> bytes:
    """L'épaisseur du film — l'arc-en-ciel radial de la 2b, PLUS les motifs
    incrustés de la 3c. Cache borné, clé `(out_px, ((sha, gain), ...))`.

    Il n'y a DÉLIBÉRÉMENT pas de cache sur `holo_finish` lui-même : il rend un
    dictionnaire de LISTES mutables, qu'un appelant pourrait modifier — la
    carte suivante hériterait de la mutation. Seuls les OCTETS, immuables, se
    partagent."""
    cle = (int(out_px), tuple((sha, gain) for sha, gain, _ in pile))
    fait = _THICK_CACHE.get(cle)
    if fait is not None:
        _THICK_CACHE.move_to_end(cle)
        _THICK_STATS["hits"] += 1
        return fait
    _THICK_STATS["misses"] += 1
    png = _holo_thickness_bytes(out_px, pile)
    _THICK_CACHE[cle] = png
    while len(_THICK_CACHE) > THICK_CACHE_MAX:
        _THICK_CACHE.popitem(last=False)
    return png


_holo_thickness_png.cache_info = _thick_cache_info
_holo_thickness_png.cache_clear = _thick_cache_clear


@lru_cache(maxsize=4)
def _holo_base_g(out_px: int) -> bytes:
    """LE PLAN G NU — un octet par pixel, l'arc-en-ciel radial SANS motif.

    Pourquoi des secteurs et pas un dégradé continu : une MARCHE survit au
    mip-mapping, un dégradé fin moire dès le second niveau (§6.2bis-c). 48
    secteurs sur un cycle de 8 niveaux = 6 tours d'arc-en-ciel autour de la
    carte.

    ZÉRO ALÉA : la valeur d'un pixel ne dépend que de son ANGLE au centre —
    deux appels rendent les mêmes octets, ce que le test prouve. Écriture par
    RANGÉES (bytearray + `frombytes`) plutôt que pixel par pixel : même
    sortie AU BIT PRÈS (vérifiée avant de choisir), 2,20 s -> 0,33 s à 1024²
    sur le runtime embarqué — et un aperçu de carte en demande deux.

    CACHÉ À PART DU COMPOSÉ (3c), et pour une raison mesurable : le cache des
    octets LIVRÉS est clé sur (taille, pile), donc changer d'un cran la part
    d'un motif le rate — et cette boucle-ci, la seule chose vraiment chère,
    serait repayée à chaque cran de curseur. Elle ne dépend QUE de la taille :
    deux entrées suffisent aux deux tailles réellement servies, quatre laissent
    la marge des tests (1 Mo l'entrée à 1024, 4 Mo à 2048).

    SINGULARITÉ DU CENTRE, assumée : sous r ≈ out_px/64, un pixel couvre plus
    d'un secteur et la roue crénèle en moulin à vent. Ces finitions habillent
    un SCEAU de bordure, pas le centre de la carte — la zone concernée fait
    16 px de rayon sur 1024. Adoucir le G vers une constante dans ce disque
    coûterait la lisibilité de la recette pour un défaut que personne ne
    regarde ; on le NOMME plutôt que de le corriger à l'aveugle."""
    c = out_px / 2.0
    pi = math.pi
    atan2 = math.atan2
    lut = [round(255 * ((s % _HOLO_CYCLE) / (_HOLO_CYCLE - 1)))
           for s in range(_HOLO_SECTORS)]
    data = bytearray(out_px * out_px)
    off = 0
    for y in range(out_px):
        dy = y - c
        for x in range(out_px):
            ang = atan2(dy, x - c)
            # le `% _HOLO_SECTORS` n'est pas décoratif : à ang == +pi
            # exactement (la rangée du centre, à gauche) le produit vaut 48.
            data[off] = lut[int(((ang + pi) / (2.0 * pi)) * _HOLO_SECTORS)
                            % _HOLO_SECTORS]
            off += 1
    return bytes(data)


def _holo_thickness_bytes(out_px: int, pile: tuple = ()) -> bytes:
    """L'épaisseur du film dans le canal G — le seul que lise
    KHR_materials_iridescence. R et B restent à 0 : l'octet neutre du « canal
    inutilisé », pour qu'aucun outil n'aille y lire un empaquetage qui
    n'existe pas.

    L'ADDITION EST BORNÉE, ET L'ORDRE EST LOAD-BEARING (§6.2bis-d) : chaque
    calque ne peut déposer que ce que l'épaisseur RESTANTE lui laisse
    (`min(luminance, 255 - g)`), et sa PART (`gain`) se calcule sur ce qu'il a
    pu prendre. Arriver en second coûte — c'est le geste d'une presse à foil,
    où le second poinçon ne trouve plus que le film que le premier a laissé.

    Ce n'est PAS une somme finalement écrêtée, et l'écart est le fond de
    l'affaire : `min(255, g + a + b)` est COMMUTATIF (l'écrêtage d'un total ne
    sait pas qui est arrivé le premier), si bien que « ordre des calques =
    ordre d'addition » n'y voudrait rien dire. Mesuré : `A(lum 100, part 1,0)`
    puis `B(lum 200, part 0,5)` sur un fond nul donne 178, l'ordre inverse 200.

    TOUT SE FAIT EN OPÉRATIONS D'IMAGE (invert/darker/point/add), pas en
    boucle Python : à 1024² une boucle par pixel coûtait ~1 s par calque, ces
    quatre passes en coûtent ~8 ms — et elles sont exactement aussi
    déterministes (une LUT de 256 entrées, aucun aléa)."""
    from PIL import Image, ImageChops
    g = Image.frombytes("L", (out_px, out_px), _holo_base_g(out_px))
    for _sha, gain, raw in pile:
        lum = _motif_luma(raw, out_px)
        reste = ImageChops.invert(g)                      # 255 - g
        pris = ImageChops.darker(lum, reste)              # min(lum, reste)
        depot = pris.point([round(v * gain) for v in range(256)])
        # `add` écrête à 255 — REDONDANT PAR CONSTRUCTION, et c'est dit parce
        # que c'est mesuré : `depot <= pris <= reste = 255 - g`, donc la somme
        # ne peut pas dépasser. (Mutation testée : passer en `add_modulo` seul
        # ne change AUCUN octet — le mutant survit, et il a raison. C'est le
        # `darker` au-dessus qui PORTE la borne ; retirer LUI casse à la fois
        # la borne et l'ordre, et deux tests le tuent.) La ceinture reste :
        # elle coûte zéro et elle protège un futur `gain > 1`.
        g = ImageChops.add(g, depot)
    zero = Image.new("L", (out_px, out_px), 0)
    return _png_bytes(Image.merge("RGB", (zero, g, zero)))


@lru_cache(maxsize=8)
def _holo_aniso_png(out_px: int) -> bytes:
    """La direction du peigne anisotrope : TANGENTE au périmètre — le reflet
    tourne AUTOUR du sceau, comme un métal brossé en cercle. R et G portent la
    direction remappée en 0..1 dans le plan tangent/bitangent.

    B = 255, ET PAS 0 : KHR_materials_anisotropy MULTIPLIE `anisotropyStrength`
    par le canal BLEU de cette texture. À 0, la force effective vaut zéro
    partout — la finition ne se verrait NULLE PART et le 0.85 du document ne
    serait qu'une décoration. (Amendement Task 5 au plan 2b, qui écrivait
    B=0 : mesuré contre le texte de l'extension, pas recopié.)

    La direction est PERPENDICULAIRE au rayon en tout point — c'est ce que le
    test relit dans les octets (produit scalaire (R-127,5 ; G-127,5)·(dx ; dy)
    nul aux arrondis près), et c'est ce qui distingue un peigne CIRCULAIRE
    d'un peigne radial en nœud papillon.

    Même écriture par rangées, mêmes raisons (2,30 s -> 0,75 s à 1024²)."""
    from PIL import Image
    # (même cache et même singularité de centre que la texture d'épaisseur)
    c = out_px / 2.0
    atan2, cos, sin = math.atan2, math.cos, math.sin
    quart = math.pi / 2.0
    data = bytearray(out_px * out_px * 3)
    off = 0
    for y in range(out_px):
        dy = y - c
        for x in range(out_px):
            ang = atan2(dy, x - c) + quart
            data[off] = round((cos(ang) * 0.5 + 0.5) * 255)
            data[off + 1] = round((sin(ang) * 0.5 + 0.5) * 255)
            data[off + 2] = 255
            off += 3
    return _png_bytes(Image.frombytes("RGB", (out_px, out_px), bytes(data)))


def holo_finish(kind: str, aniso: bool, out_px: int = 1024,
                motifs=()) -> dict:
    """UNE finition holographique de la spec (§6.2bis-c), prête pour le
    writer : facteurs PBR, bloc iridescence (+ sa texture d'épaisseur),
    clearcoat, et l'anisotropie SEULEMENT si on la demande.

    `kind` hors `HOLO_KINDS` lève une ValueError NOMMÉE : une finition
    inconnue silencieusement remplacée par l'argent livrerait une carte FAUSSE
    sans que personne ne le sache. C'est à l'appelant de borner son entrée
    AVANT (doctrine 2.5) — `HOLO_KINDS` lui donne la liste sans la recopier.

    `out_px` est borné à `HOLO_PX` (8..2048, §6.2bis) : la texture est
    fabriquée pixel par pixel en Python ; un chiffre non borné venu d'un
    graphe serait une bombe mémoire.

    `motifs` (3c) : une suite de `(octets, part)` — les CALQUES incrustés dans
    le canal G, dans l'ORDRE d'addition (§6.2bis-d). Les octets, jamais des
    chemins : ce module ne sait pas où vivent les fichiers, et c'est
    l'appelant qui AVOUE ce qu'il n'a pas su résoudre. Un calque ILLISIBLE
    (fichier corrompu) lève une ValueError NOMMÉE, comme une recette inconnue
    — l'appelant en fait un aveu."""
    r = _HOLO_RECIPES.get(str(kind))
    if r is None:
        raise ValueError(f"finition holographique inconnue : {kind!r} "
                         f"(connues : {', '.join(HOLO_KINDS)})")
    px = max(HOLO_PX[0], min(HOLO_PX[1], int(_f(out_px, 1024.0))))
    return {
        "pbr": {"baseColorFactor": list(r["base"]),
                "metallicFactor": 1.0, "roughnessFactor": r["rough"]},
        "iridescence": {"factor": 1.0, "ior": r["ior"],
                        "thickness": list(r["thickness"]),
                        "png": _holo_thickness_png(px, motif_pile(motifs))},
        "clearcoat": {"factor": 1.0, "rough": _HOLO_CLEARCOAT_ROUGH},
        "anisotropy": ({"strength": _HOLO_ANISO_STRENGTH,
                        "png": _holo_aniso_png(px)} if aniso else None),
    }


def _quat_z(deg) -> list:
    """Le quaternion d'une rotation autour de +z — le SEUL axe qui ait un sens
    sur une pile de couches planes. Rend l'identité pour 0°."""
    demi = math.radians(_f(deg)) / 2.0
    return [0.0, 0.0, math.sin(demi), math.cos(demi)]


# ── LA RÈGLE DE CÔTÉ (2d) : LE VERSO EST LA CARTE RETOURNÉE ────────────────
# P8 fait foi : recto plat +z sens direct, verso plat −z sens INVERSE
# (solid.py:532-545), et `uv_back` en MIROIR DE U parce que « vu de -Z la
# droite de l'écran est -x » (solid.py:513-522). P9 obtient la MÊME physique
# sans un maillage de plus : l'élément est construit en ESPACE RECTO (mêmes
# `quad_mesh`/`relief_mesh`, mêmes UV, même TANGENT local), puis LA CARTE EST
# RETOURNÉE. Un seul geste, trois effets — la normale s'oppose, l'image se
# retourne gauche-droite, la pile descend sous le plan médian.

def _quat_face(deg, retourne: bool) -> list:
    """Le quaternion d'un élément POSÉ SUR SA FACE.

    Recto (`retourne` faux) : `_quat_z(deg)` — la rotation de la 2a, au bit
    près, autour du seul axe qui ait un sens sur une pile de couches planes.

    Verso : **R_y(pi) o R_z(deg)** — la rotation de l'utilisateur D'ABORD (dans
    l'espace recto où l'élément est construit), LE DEMI-TOUR DE LA CARTE
    ENSUITE. C'est CET ordre-là, et pas l'autre, qui rend l'édition WYSIWYG :
    vu de −z on est passé DERRIÈRE, la droite de l'écran y est −x, et composer
    dans cet ordre laisse « +deg tourne dans le sens direct » vrai POUR CELUI
    QUI REGARDE LE VERSO (l'ordre inverse, R_z(deg) o R_y(pi), lui montrerait
    −deg — le banc mesure l'angle des deux côtés plutôt que de le croire).

    Le produit se SIMPLIFIE : composer un demi-tour avec une rotation d'axe
    perpendiculaire redonne un demi-tour, ici autour d'un axe du plan XY —
    (sin(d/2), cos(d/2), 0, 0). Rotation PROPRE (déterminant +1) : l'enroulement
    des triangles est préservé et le repère tangent local tourne en bloc, donc
    la règle w = −1 du bloc TANGENT plus bas (qui est LOCALE, dérivée de
    l'inversion de v de nos UV) reste juste telle quelle."""
    if not retourne:
        return _quat_z(deg)
    demi = math.radians(_f(deg)) / 2.0
    return [math.sin(demi), math.cos(demi), 0.0, 0.0]


def trs_de_face(trs: dict, w_mm: float, side) -> dict:
    """LE TRS D'UN ÉLÉMENT, POSÉ SUR SA FACE — la règle de côté, UNE fois pour
    les trois sorties (le nœud d'un local, le parent de fusion d'un moteur, et
    les sommets cuits du STL, qui n'a pas de nœud pour porter un transform).

    `side` autre que `"back"` : le TRS rendu TEL QUEL — le recto est le repère
    de référence, il n'a rien à corriger, et un GLB de la 2a ne bouge pas d'un
    bit.

    `side == "back"` : la carte est RETOURNÉE, c'est-à-dire la rotation PROPRE
    de 180 degrés autour de la verticale qui passe par le MILIEU de la carte

        (x, y, z) -> (w_mm - x, y, -z)

    — déterminant +1 (miroir GAUCHE-DROITE physique, pas une symétrie qui
    retournerait l'enroulement), normale +z -> −z, et EMPREINTE CONSERVÉE
    ([0, w_mm] -> [0, w_mm]) : les deux faces se superposent comme sur une
    vraie carte au lieu de se poser côte à côte, ce que ferait un demi-tour
    autour du COIN. C'est l'équivalent géométrique exact de `uv_back` (P8),
    porté par la PLACE au lieu des UV — l'atlas P8 ne retourne pas ses pixels
    non plus, c'est sa géométrie qui porte le miroir.

    Appliqué à un TRS glTF (p' = T + R(S.p), la translation en DERNIER et dans
    le repère du parent), le retournement se répartit exactement ainsi :
      · `translate` -> `[w_mm - tx, ty, -tz]` — d'où un `x_mm` qui pousse vers
        la DROITE DU VERSO (−x monde, la droite de celui qui le regarde) et un
        `z_mm` qui empile SOUS le plan médian. Les BORNES ne changent pas : les
        valeurs postées restent >= 0, le SIGNE appartient à la règle de côté ;
      · `rotate_deg` INCHANGÉ — la composition vit dans `_quat_face`, et le
        drapeau `retourne` la déclenche partout où ce TRS est consommé.

    Le `y` n'est JAMAIS retourné : « en bas = −y des deux côtés » (P8,
    solid.py:614-615) — une carte se retourne gauche-droite, pas tête-bêche."""
    if side != "back":
        return trs
    t = trs.get("translate")
    tx, ty, tz = ([_f(v) for v in t]
                  if isinstance(t, (list, tuple)) and len(t) == 3
                  else [0.0, 0.0, 0.0])
    return {**trs, "translate": [_f(w_mm) - tx, ty, -tz], "retourne": True}


def _node_trs(el: dict) -> dict:
    """Les champs TRS du nœud d'un élément.

    SANS `trs`, le comportement de la 2a est gardé À L'IDENTIQUE : une
    translation z (en mm) et rien d'autre, et seulement quand `z_mm` est non
    nul — un GLB de la 2a doit rester, octet pour octet, un GLB de la 2a.

    AVEC `trs` : `translate` REMPLACE cette translation (qui pose un transform
    complet porte lui-même son z), `rotate_deg` tourne autour de +z — le seul
    axe qui ait un sens sur une pile de couches planes — et `scale` est
    UNIFORME, un facteur par axe déformerait la carte. Ni la rotation ni
    l'échelle ne sont écrites quand elles ne font rien : 0° et x1 sont
    l'identité, que glTF sous-entend déjà.

    `retourne` (2d, posé par `trs_de_face`) : l'élément est au VERSO. Sa
    rotation devient R_y(pi) o R_z(rotate_deg) (`_quat_face`) et elle est
    TOUJOURS écrite — le demi-tour de la carte n'est pas une identité que glTF
    sous-entendrait, l'omettre à 0° laisserait le verso face au même côté que
    le recto. Le SIGNE du z, lui, est déjà dans `translate` : il appartient à
    la règle de côté, pas au writer."""
    trs = el.get("trs")
    if not isinstance(trs, dict):
        return ({"translation": [0.0, 0.0, float(el["z_mm"])]}
                if el.get("z_mm") else {})
    out: dict = {}
    t = trs.get("translate")
    if isinstance(t, (list, tuple)) and len(t) == 3:
        out["translation"] = [_f(v) for v in t]
    elif el.get("z_mm"):
        out["translation"] = [0.0, 0.0, float(el["z_mm"])]
    retourne = bool(trs.get("retourne"))
    demi = math.radians(_f(trs.get("rotate_deg"))) / 2.0
    if demi or retourne:
        out["rotation"] = _quat_face(trs.get("rotate_deg"), retourne)
    s = _f(trs.get("scale"), 1.0)
    if s != 1.0:
        out["scale"] = [s, s, s]
    return out


# ── L'ASSEMBLAGE — UN document glTF binaire, écrit JUSTE (Task 3) ──────────
# `write_scene_glb` consomme le type commun de `quad_mesh`/`relief_mesh`
# (positions/normals/uvs/indices — `closed` et tout champ surnuméraire sont
# IGNORÉS) et produit un GLB PROPRE dès l'écriture : bornes d'accesseurs
# EXACTES (calculées sur les float32 réellement empaquetés, pas sur les
# float64 Python d'avant arrondi), AUCUN champ d'identité (generator,
# copyright, author, producer — ce writer n'en émet simplement jamais),
# samplers CLAMP_TO_EDGE, racine à l'échelle physique mm -> m (0.001), un
# enfant nommé par élément, translation z (mm) portée par le nœud de
# l'élément. À la différence du constructeur générique du dépôt
# (gltf_builder, qui exige des rustines post-hoc — finalize_glb de P8), rien
# ici n'est corrigé après coup.

# Clés d'`extras` qui nomment un producteur — COPIE LOCALE de gltf.py:198
# (règle 8, zéro import pièce->pièce) : filtrées ICI, dans le writer, pour
# que « zéro identité » reste vrai pour TOUT appelant, pas seulement celui
# qui pense à nettoyer son propre extras avant l'appel.
_IDENTITY_KEYS = ("generator", "producer", "author", "software", "application",
                  "copyright", "artist", "company", "vendor")


# ── LA FUSION D'UN GLB EXTERNE (Task 6, 2b) ─────────────────────────────────
# Un moteur image->3D (mesh3d, Task 4) rend UN GLB entier : son propre buffer,
# ses vues, ses accesseurs, ses images, ses matériaux, son arbre de nœuds. Le
# fusionner dans NOTRE document, c'est le RÉINDEXER de bout en bout — pas le
# recoller à côté. Toute référence d'indice qu'on oublierait de décaler pointe
# alors une donnée du VOISIN : un GLB parfaitement valide, qui montre la
# mauvaise chose. D'où les cartes de décalage explicites ci-dessous, et un
# refus NOMMÉ (jamais un IndexError nu) dès qu'un indice sort des clous.
# LES EXTENSIONS EXIGIBLES QUE CETTE FUSION SAIT TRANSPORTER. Liste BLANCHE,
# et courte exprès : y ajouter un nom, c'est promettre que `_merge_external`
# recopie ET réindexe tout ce dont cette extension a besoin. Draco (sa vue
# compressée est décalée), Basisu (sa `source` d'image est réindexée dans les
# extensions de texture), unlit (aucun indice du tout). EXT_meshopt_compression
# n'y est PAS : son bloc vit dans les `extensions` d'une bufferView, que cette
# fusion ne recopie pas. KHR_mesh_quantization n'y est PAS NON PLUS, et pour une
# raison de LECTEUR, pas de recopie : `_accessor_floats` ne décode que du
# float32 (5126) et refuse nommément tout le reste — accepter l'extension ici
# promettrait une mesure que le lecteur ne sait pas faire.
# Ce que chaque entrée engage : draco et basisu sont LUS par le code de fusion
# ci-dessous (vue compressée décalée, `source` d'image réindexée) ; unlit, lui,
# ne porte aucun indice — il n'est tenu QUE par le test de source (il passe
# parce qu'il n'y a rien à réindexer, pas parce qu'on le traite).
_EXIG_CONNUES = {"KHR_draco_mesh_compression", "KHR_texture_basisu",
                 "KHR_materials_unlit"}

_PROF_MAX = 12          # borne ANTI-GEL des balayages récursifs : un document
                         # hostile à un million de niveaux ne doit pas faire
                         # sauter la pile (une RecursionError deviendrait un
                         # 500 chez l'appelant, ce que ce module s'interdit).


def _decale(carte: dict, i, quoi: str) -> int:
    """L'indice `i` vu par le décalage `carte`, ou ValueError NOMMÉE. Un GLB
    de moteur qui référence une donnée absente est une entrée douteuse, pas un
    bug d'ici : elle se refuse, elle ne lève pas un IndexError nu."""
    if isinstance(i, bool) or not isinstance(i, int) or i not in carte:
        raise ValueError(f"GLB externe : {quoi} hors bornes ({i!r})")
    return carte[i]


def _reindex_cles(obj, cles: dict, prof: int = 0) -> None:
    """Réécrit RÉCURSIVEMENT, SUR PLACE, les clés d'indice nommées dans
    `cles` ({nom de clé: carte de décalage}).

    Deux usages, deux clés : `index` dans un dict de MATÉRIAU (là, `index` ne
    désigne QUE des textures — `textureInfo`, `normalTextureInfo`,
    `occlusionTextureInfo` — y compris au fond des `extensions` : clearcoat,
    iridescence, anisotropie, specular... les balayer une par une serait une
    liste à tenir à jour contre le registre Khronos) et `source` dans les
    `extensions` d'une TEXTURE (KHR_texture_basisu porte SA propre image)."""
    if prof > _PROF_MAX:
        raise ValueError("GLB externe : document trop imbriqué")
    if isinstance(obj, dict):
        for cle, carte in cles.items():
            if cle in obj:
                obj[cle] = _decale(carte, obj[cle], cle)
        for v in obj.values():
            _reindex_cles(v, cles, prof + 1)
    elif isinstance(obj, list):
        for v in obj:
            _reindex_cles(v, cles, prof + 1)


def _scrub_extras(obj, prof: int = 0) -> None:
    """`extras` JETÉS partout, récursivement : c'est là que vivent les champs
    d'identité d'un exportateur tiers (auteur, outil, licence). Le writer
    promet « zéro identité » pour TOUT le document — la promesse ne peut pas
    s'arrêter à la frontière du GLB importé."""
    if prof > _PROF_MAX:
        raise ValueError("GLB externe : document trop imbriqué")
    if isinstance(obj, dict):
        obj.pop("extras", None)
        for v in obj.values():
            _scrub_extras(v, prof + 1)
    elif isinstance(obj, list):
        for v in obj:
            _scrub_extras(v, prof + 1)


def _merge_external(doc, buf, views, accessors, images, textures, materials,
                    meshes, nodes, samplers, ext) -> tuple:
    """Réindexation complète d'UN GLB externe dans le document EN COURS.

    `doc` porte les champs de NIVEAU DOCUMENT (`extensionsUsed` et
    `extensionsRequired`, deux ensembles) ; les autres paramètres sont les
    tableaux en construction du writer, complétés SUR PLACE. Rend
    `(indice du nœud parent, ignorés)`.

      · bufferViews recopiées VUE PAR VUE (pad4 avant chacune, `byteOffset`
        au point de recopie) — jamais le buffer entier : les paddings d'ORIGINE
        ne sont pas les nôtres, et une vue peut parfaitement en chevaucher une
        autre chez le voisin ;
      · images par bufferView OBLIGATOIRES — une image `uri` lève une
        ValueError NOMMÉE : RIEN ne se télécharge à l'assemblage (idem pour un
        buffer externe, qui emporterait la géométrie avec lui) ;
      · samplers du doc externe PRÉSERVÉS — leurs textures tuilent parfois en
        REPEAT, c'est LEUR matériau ; notre CLAMP ne vaut que pour NOS couches
        (dont le tuilage est cuit dans les pixels). Une texture externe sans
        sampler reçoit un `{}` AJOUTÉ (le défaut glTF = REPEAT), jamais notre
        CLAMP recyclé ;
      · hiérarchie de nœuds interne GARDÉE (enfants décalés), re-basée sous UN
        parent au TRS du fit ; animations / squelettes / caméras JETÉS et
        AVOUÉS (rien ici ne sait les rejouer) ;
      · asset, generator, copyright et tous les `extras` du doc externe JETÉS
        (nous gardons NOTRE asset) ; `extensionsUsed` en union ; ses
        `extensionsRequired` CONSERVÉES telles quelles — honnêteté : le
        document fusionné les exige VRAIMENT. Les NÔTRES (iridescence,
        clearcoat, anisotropie) n'y entrent jamais, elles restent des
        enjolivures.

    LIMITE CONNUE, nommée plutôt que masquée : les `attributes` d'une
    primitive compressée Draco sont des identifiants DRACO, pas des
    accesseurs — seule sa `bufferView` est décalée. Un GLB Draco garde donc
    son `extensionsRequired`, et c'est au lecteur de savoir le décompresser."""
    src, binv = read_glb(ext.get("glb") if isinstance(ext, dict) else None)
    _scrub_extras(src)
    ignores: list = []

    def tab(cle) -> list:
        v = src.get(cle)
        return v if isinstance(v, list) else []

    nom_ext = str((ext or {}).get("name") or "externe")[:60]
    for i, im in enumerate(tab("images")):
        if isinstance(im, dict) and im.get("uri"):
            raise ValueError(
                f"GLB à ressources externes (uri) non supporté : l'image {i} "
                f"de {nom_ext!r} vit au bout d'une URL — rien ne se télécharge "
                f"à l'assemblage")
    for i, bf in enumerate(tab("buffers")):
        if isinstance(bf, dict) and bf.get("uri"):
            raise ValueError(
                f"GLB à ressources externes (uri) non supporté : le buffer {i} "
                f"de {nom_ext!r} vit au bout d'une URL")
    # ── LES EXIGENCES, SUR LISTE BLANCHE ───────────────────────────────────
    # `extensionsRequired` est CONSERVÉE plus bas (honnêteté : le document
    # fusionné les exige vraiment). Mais conserver une exigence qu'on ne sait
    # pas SATISFAIRE est pire que de la jeter : la fusion ne recopie que les
    # champs qu'elle connaît — les `extensions` d'une bufferView, par exemple,
    # tombent, et c'est précisément là qu'EXT_meshopt_compression décrit son
    # bloc compressé. Le fichier annoncerait alors une exigence dont la
    # description a disparu : un artefact FAUX, livré sans un mot. On refuse
    # NOMMÉMENT au lieu de deviner.
    inconnues = sorted({x for x in tab("extensionsRequired")
                        if isinstance(x, str)} - _EXIG_CONNUES)
    if inconnues:
        raise ValueError(
            f"GLB externe : extension EXIGÉE non fusionnable "
            f"({', '.join(inconnues)}) sur {nom_ext!r} — la fusion ne sait pas "
            f"en transporter la description, et un fichier qui exige ce qu'il "
            f"ne porte plus est pire qu'un refus")

    def pad4():
        while len(buf) % 4:
            buf.append(0)

    # ── les vues : recopiées une par une DANS notre buffer ──────────────────
    dv: dict = {}
    for i, bv in enumerate(tab("bufferViews")):
        if not isinstance(bv, dict):
            raise ValueError(f"GLB externe : bufferView {i} illisible")
        off = int(_f(bv.get("byteOffset"), 0.0))
        ln = int(_f(bv.get("byteLength"), 0.0))
        if off < 0 or ln < 0 or off + ln > len(binv):
            raise ValueError(
                f"GLB externe tronqué : bufferView {i} déborde du chunk BIN "
                f"({off}+{ln} > {len(binv)})")
        pad4()
        neuve = {"buffer": 0, "byteOffset": len(buf), "byteLength": ln}
        for cle in ("byteStride", "target"):
            if cle in bv:
                neuve[cle] = bv[cle]
        buf.extend(binv[off:off + ln])
        views.append(neuve)
        dv[i] = len(views) - 1

    # ── les accesseurs : bornes et octets INTACTS, seule la vue se décale ───
    da: dict = {}
    for i, acc in enumerate(tab("accessors")):
        if not isinstance(acc, dict):
            raise ValueError(f"GLB externe : accesseur {i} illisible")
        if "bufferView" in acc:
            acc["bufferView"] = _decale(dv, acc["bufferView"],
                                        f"bufferView de l'accesseur {i}")
        sp = acc.get("sparse")
        if isinstance(sp, dict):
            for cle in ("indices", "values"):
                part = sp.get(cle)
                if isinstance(part, dict) and "bufferView" in part:
                    part["bufferView"] = _decale(
                        dv, part["bufferView"],
                        f"bufferView sparse.{cle} de l'accesseur {i}")
        accessors.append(acc)
        da[i] = len(accessors) - 1

    # ── les images : par bufferView, sans un mot de leur provenance ─────────
    di: dict = {}
    for i, im in enumerate(tab("images")):
        if not isinstance(im, dict) or "bufferView" not in im:
            raise ValueError(
                f"GLB externe : image {i} sans bufferView (seules les images "
                f"EMBARQUÉES sont fusionnables)")
        neuve = {"bufferView": _decale(dv, im["bufferView"],
                                       f"bufferView de l'image {i}"),
                 "mimeType": str(im.get("mimeType") or "image/png")}
        if im.get("name"):
            neuve["name"] = str(im["name"])[:60]
        images.append(neuve)
        di[i] = len(images) - 1

    # ── les samplers : les SIENS, ou un défaut glTF (REPEAT) ajouté ─────────
    ds: dict = {}
    for i, sm in enumerate(tab("samplers")):
        samplers.append(dict(sm) if isinstance(sm, dict) else {})
        ds[i] = len(samplers) - 1
    defaut: list = [None]

    def sampler_defaut() -> int:
        if defaut[0] is None:
            samplers.append({})        # wrap par défaut glTF = REPEAT
            defaut[0] = len(samplers) - 1
        return defaut[0]

    dt: dict = {}
    for i, tx in enumerate(tab("textures")):
        tx = tx if isinstance(tx, dict) else {}
        if "source" in tx:
            tx["source"] = _decale(di, tx["source"],
                                   f"source de la texture {i}")
        # `in ds` HACHE la valeur avant de comparer : `True` y vaut la clé 1
        # (bool est un int en Python) et volerait le sampler du voisin. Même
        # garde que `_decale`, pour la même raison.
        smp = tx.get("sampler")
        tx["sampler"] = (ds[smp]
                         if not isinstance(smp, bool) and smp in ds
                         else sampler_defaut())
        _reindex_cles(tx.get("extensions"), {"source": di})
        textures.append(tx)
        dt[i] = len(textures) - 1

    dm: dict = {}
    for i, mt in enumerate(tab("materials")):
        mt = mt if isinstance(mt, dict) else {}
        _reindex_cles(mt, {"index": dt})
        materials.append(mt)
        dm[i] = len(materials) - 1

    dh: dict = {}
    for i, mh in enumerate(tab("meshes")):
        mh = mh if isinstance(mh, dict) else {}
        prims = mh.get("primitives")
        if not isinstance(prims, list) or not prims:
            raise ValueError(f"GLB externe : mesh {i} sans primitive")
        for prim in prims:
            if not isinstance(prim, dict):
                raise ValueError(f"GLB externe : primitive illisible (mesh {i})")
            attrs = prim.get("attributes")
            if not isinstance(attrs, dict):
                raise ValueError(
                    f"GLB externe : primitive sans attributs (mesh {i})")
            prim["attributes"] = {
                k: _decale(da, v, f"attribut {k} du mesh {i}")
                for k, v in attrs.items()}
            if prim.get("indices") is not None:
                prim["indices"] = _decale(da, prim["indices"],
                                          f"indices du mesh {i}")
            if prim.get("material") is not None:
                prim["material"] = _decale(dm, prim["material"],
                                           f"matériau du mesh {i}")
            cibles = prim.get("targets")
            if isinstance(cibles, list):
                prim["targets"] = [
                    {k: _decale(da, v, f"cible de morph du mesh {i}")
                     for k, v in t.items()}
                    for t in cibles if isinstance(t, dict)]
            exts_prim = prim.get("extensions")
            draco = (exts_prim or {}).get("KHR_draco_mesh_compression")
            if isinstance(draco, dict) and "bufferView" in draco:
                draco["bufferView"] = _decale(dv, draco["bufferView"],
                                              f"vue Draco du mesh {i}")
            # KHR_materials_variants : ses `mappings[].material` indexent le
            # tableau des MATÉRIAUX de l'externe — non décalés, ils
            # désigneraient ceux du voisin dès qu'un élément local le
            # précède. Balayage par la clé `material`, comme les matériaux le
            # sont par `index`.
            _reindex_cles(exts_prim, {"material": dm})
        meshes.append(mh)
        dh[i] = len(meshes) - 1

    # ── les nœuds : hiérarchie gardée, tout le reste sur liste blanche ──────
    # (une liste BLANCHE et pas noire : `camera`, `skin`, `extensions` — une
    # lumière KHR_lights_punctual pointerait un tableau que nous ne copions
    # pas — tombent d'eux-mêmes, sans qu'il faille les avoir prévus.)
    gardes = ("name", "translation", "rotation", "scale", "matrix", "weights")
    dn: dict = {}
    s_nodes = tab("nodes")
    for i, nd in enumerate(s_nodes):
        nd = nd if isinstance(nd, dict) else {}
        neuf = {k: v for k, v in nd.items() if k in gardes}
        if "name" in neuf:
            neuf["name"] = str(neuf["name"])[:60]
        nodes.append(neuf)
        dn[i] = len(nodes) - 1
    perdus = 0
    for i, nd in enumerate(s_nodes):
        nd = nd if isinstance(nd, dict) else {}
        neuf = nodes[dn[i]]
        if nd.get("mesh") is not None:
            neuf["mesh"] = _decale(dh, nd["mesh"], f"mesh du noeud {i}")
        enf = nd.get("children")
        if isinstance(enf, list) and enf:
            neuf["children"] = [_decale(dn, c, f"enfant du noeud {i}")
                                for c in enf]
        perdus += 1 if (nd.get("camera") is not None
                        or nd.get("skin") is not None) else 0

    # ── les racines : celles des scènes ; à défaut, les nœuds sans parent ───
    racines: list = []
    vus: set = set()
    for sc in tab("scenes"):
        for k in ((sc.get("nodes") if isinstance(sc, dict) else None) or []):
            if k in dn and k not in vus:
                vus.add(k)
                racines.append(dn[k])
    if not racines:
        enfants_de: set = set()
        for nd in s_nodes:
            if isinstance(nd, dict):
                for c in (nd.get("children") or []):
                    enfants_de.add(c)
        racines = [dn[i] for i in sorted(dn) if i not in enfants_de]
    if not racines:
        raise ValueError(f"GLB externe sans aucun noeud de scène ({nom_ext!r})")

    for cle, quoi in (("animations", "animations"), ("skins", "squelettes"),
                      ("cameras", "cameras")):
        n = len(tab(cle))
        if n:
            ignores.append(f"{quoi} x{n}")
    if perdus:
        ignores.append(f"attaches camera/squelette de {perdus} noeud(s)")
    # Les `extensions` de NIVEAU DOCUMENT ne sont PAS fusionnées : elles
    # déclarent des tableaux à elles (la liste de variantes de
    # KHR_materials_variants, les lumières de KHR_lights_punctual) dont les
    # indices se télescoperaient d'un externe à l'autre. Les matériaux, eux,
    # restent correctement réindexés — c'est la DÉCLARATION qui manque, pas la
    # cible. Avoué plutôt que tu.
    doc_exts = src.get("extensions")
    if isinstance(doc_exts, dict) and doc_exts:
        ignores.append("declarations d'extensions au niveau du document ("
                       + ", ".join(sorted(str(k) for k in doc_exts)) + ")")

    doc["extensionsUsed"].update(x for x in tab("extensionsUsed")
                                 if isinstance(x, str))
    exig = {x for x in tab("extensionsRequired") if isinstance(x, str)}
    doc["extensionsRequired"].update(exig)
    doc["extensionsUsed"].update(exig)   # une exigée est forcément utilisée

    # LE PARENT : translation ET échelle TOUJOURS écrites, même à l'identité —
    # ce ne sont pas des valeurs par défaut sous-entendues mais un FIT CALCULÉ,
    # et un fit qu'on ne peut pas relire dans le fichier n'est pas auditable.
    fit = (ext or {}).get("fit")
    fit = fit if isinstance(fit, dict) else {}
    s = _f(fit.get("scale"), 1.0)
    t = fit.get("translate")
    t = ([_f(v) for v in t] if isinstance(t, (list, tuple)) and len(t) == 3
         else [0.0, 0.0, 0.0])
    parent = {"name": nom_ext, "children": racines, "translation": t,
              "scale": [s, s, s]}
    # `retourne` (2d) : le maillage du moteur suit SA couche — au verso il
    # passe derrière comme le reste de la face, et sa rotation est alors
    # TOUJOURS écrite (le demi-tour n'est pas une identité sous-entendue).
    retourne = bool(fit.get("retourne"))
    if math.radians(_f(fit.get("rotate_deg"))) / 2.0 or retourne:
        parent["rotation"] = _quat_face(fit.get("rotate_deg"), retourne)
                                                               # 0° au recto =
                                                               # identité,
                                                               # sous-entendue
    nodes.append(parent)
    return len(nodes) - 1, ignores


def apply_fit_inplace(mesh: dict, fit: dict) -> dict:
    """Le TRS d'un fit appliqué AUX POSITIONS, SUR PLACE — ordre glTF d'un
    nœud : p' = T + R(S.p). Le format STL n'a pas de nœud pour porter un
    transform : un externe doit y entrer DÉJÀ placé.

    SUR PLACE, ET C'EST LE POINT (choix mesuré, Task 6) : le plan prescrivait
    d'étendre `_write_stl_binary` d'un paramètre `externals` transformant
    sommet par sommet à l'emballage. Or `glb_scene_mesh` a DÉJÀ matérialisé
    la liste des positions — la transformer ici n'alloue RIEN de plus, tandis
    que le paramètre en plus ajoutait une passe et un chemin à tester au
    writer STL pour zéro octet gagné. Le writer garde donc son contrat
    d'octets intact, et l'externe entre comme un élément ordinaire.

    `retourne` (2d) : LE MÊME demi-tour de carte que `_quat_face` écrit dans un
    nœud, cuit ici dans les sommets — R_y(pi) o R_z(rotate_deg), donc x et z
    opposés APRÈS la rotation de l'utilisateur et AVANT la translation (qui
    porte déjà, elle, le `w_mm - tx` et le `-tz` de `trs_de_face`). Sans cette
    ligne, le STL et le GLB montreraient deux vérités différentes de la même
    carte — exactement le défaut que le transform local a déjà coûté une fois."""
    fit = fit if isinstance(fit, dict) else {}
    s = _f(fit.get("scale"), 1.0)
    t = fit.get("translate")
    tx, ty, tz = ([_f(v) for v in t]
                  if isinstance(t, (list, tuple)) and len(t) == 3
                  else [0.0, 0.0, 0.0])
    ang = math.radians(_f(fit.get("rotate_deg")))
    ca, sa = math.cos(ang), math.sin(ang)
    retourne = bool(fit.get("retourne"))
    pos = mesh["positions"]
    for k in range(0, len(pos) - 2, 3):
        x, y, z = pos[k] * s, pos[k + 1] * s, pos[k + 2] * s
        rx = x * ca - y * sa
        if retourne:
            rx, z = -rx, -z
        pos[k] = rx + tx
        pos[k + 1] = x * sa + y * ca + ty
        pos[k + 2] = z + tz
    return mesh


def write_scene_glb(elements: list, name: str, extras: dict,
                    externals: list | None = None,
                    out_ignored: list | None = None) -> bytes:
    """UN document glTF multi-éléments, écrit JUSTE du premier coup :
    bornes exactes (calculées ici même sur les floats empaquetés), aucun champ
    d'identité (ce writer n'en émet simplement jamais), samplers CLAMP, racine
    à l'échelle physique mm->m, un enfant nommé par élément, translation z en
    mm portée par le nœud de l'élément. Textures : les PNG estampillés de la
    phase 1, embarqués tels quels (mêmes octets, mêmes SHA que le manifeste).

    TROIS CLÉS FACULTATIVES par élément (2b), toutes ABSENTES = comportement
    de la 2a mot pour mot :
      · `mat_maps` — le paquet de `material_pngs` : normale, pack MR, AO,
        émissive. Le pack MR ramène metallicFactor/roughnessFactor à 1.0 (les
        niveaux sont dans les octets, pas dans les facteurs).
      · `finish`  — le paquet de `holo_finish` : une feuille holographique
        REMPLACE la micro-surface de la matière (le pack MR est alors SAUTÉ,
        glTF multipliant facteur x texture) et laisse parler son relief et son
        occlusion. Ses trois extensions n'apparaissent QUE dans
        `extensionsUsed`, jamais dans `extensionsRequired`. Une anisotropie
        exige un maillage `uv_axis_aligned` — sinon ValueError NOMMÉE.
      · `trs`     — translation/rotation/échelle du nœud ; sans elle, seul le
        `z_mm` de la 2a est écrit (voir `_node_trs`).

    `externals` (2b, Task 6) — les GLB des MOTEURS, fusionnés APRÈS les
    éléments locaux, chaque entrée `{"name", "glb": bytes, "fit": {...}}` (voir
    `_merge_external`). Absent = comportement 2a mot pour mot.

    `out_ignored` — liste FACULTATIVE à laquelle sont AJOUTÉES les pertes de
    la fusion, en dicts `{"name": <l'externe>, "why": "animations x2 : ..."}`.
    Le plan montrait des chaînes nues ; un aveu doit être ATTRIBUABLE — la
    route doit dire QUEL nœud a perdu quoi, et retrouver le nom en découpant
    une chaîne serait un couplage par la ponctuation. Choix DÉLIBÉRÉ, aussi,
    contre un tuple de retour :
    rendre `(bytes, ignored)` dès qu'il y a des externes ferait deux types de
    retour pour une même fonction — un appelant 2a qui écrirait le résultat
    tel quel produirait un GLB corrompu le jour où un externe apparaît. Un
    paramètre de sortie, lui, ne casse personne et ne se lit que si on le
    demande.

    Précondition : AU MOINS UN élément (local ou externe) — un GLB vide est
    invalide au schéma glTF ; la route build3d fait 409 avant d'appeler ce
    writer (tâche 4)."""
    # zéro identité VRAIE pour tout appelant, pas seulement le nôtre
    extras = {k: v for k, v in (extras or {}).items() if k not in _IDENTITY_KEYS}
    buf = bytearray()
    views, accessors, images, textures, materials, meshes, nodes = [], [], [], [], [], [], []
    samplers: list = [{"wrapS": 33071, "wrapT": 33071}]   # NOTRE sampler CLAMP
    exts_required: set = set()

    def pad4():
        while len(buf) % 4:
            buf.append(0)

    def add_view(data: bytes, target=None) -> int:
        pad4()
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data),
                      **({"target": target} if target else {})})
        buf.extend(data)
        return len(views) - 1

    def add_accessor(vals, n, ctype, atype, target) -> int:
        data = struct.pack("<" + "f" * len(vals), *vals) if ctype == 5126 \
            else struct.pack("<" + "I" * len(vals), *vals)
        v = add_view(data, target)
        acc = {"bufferView": v, "componentType": ctype,
               "count": len(vals) // n, "type": atype}
        if ctype == 5126:
            # les bornes sont posées sur les float32 EXACTS : repasser par
            # struct garantit la valeur que le lecteur relira (un float
            # Python 64 bits arrondi en float32 changerait de valeur)
            packed = struct.unpack("<" + "f" * len(vals), data)
            acc["min"] = [min(packed[i::n]) for i in range(n)]
            acc["max"] = [max(packed[i::n]) for i in range(n)]
        accessors.append(acc)
        return len(accessors) - 1

    sampler = 0   # NOS couches : le sampler CLAMP, toujours l'indice 0 (les
                   # samplers d'un GLB externe s'ajoutent APRÈS, jamais à sa
                   # place — voir `_merge_external`)
    exts_used: set = set()

    # MEMO DE TEXTURES, PAR APPEL (revue Task 5) : deux éléments finis avec la
    # même recette portent les MÊMES octets d'iridescence — les embarquer deux
    # fois double le poids du GLB pour rien. Le partage est RÉSERVÉ aux
    # textures de matière et de finition : le PNG de couche, lui, garde son
    # image et son nom propres, même si deux couches sont octet pour octet
    # identiques (l'identité des couches est un contrat de la 2a — la
    # mutualiser changerait les octets d'une scène 2a).
    partages: dict = {}

    def add_texture(png: bytes, nom: str, partage: bool = False) -> int:
        """Un PNG embarqué + SA texture, sur LE sampler CLAMP unique. Le
        tuilage des matières est CUIT dans les octets (`tile_maps`, côté
        contrat HTTP) : rien ici n'a jamais besoin de REPEAT."""
        if partage and png in partages:
            return partages[png]
        v = add_view(png)
        images.append({"bufferView": v, "mimeType": "image/png", "name": nom})
        textures.append({"sampler": sampler, "source": len(images) - 1})
        if partage:
            partages[png] = len(textures) - 1
        return len(textures) - 1

    for el in elements:
        m = el["mesh"]
        nom = el["name"]
        fin = el.get("finish")
        fin = fin if isinstance(fin, dict) else None
        # sous-blocs TYPÉS : `{"anisotropy": True}` ne doit pas faire tomber le
        # writer sur un `.get` d'un booléen — un paquet mal formé dégrade en
        # « pas de finition », jamais en 500.
        iri = (fin or {}).get("iridescence")
        iri = iri if isinstance(iri, dict) else None
        cc = (fin or {}).get("clearcoat")
        cc = cc if isinstance(cc, dict) else None
        ani = (fin or {}).get("anisotropy")
        ani = ani if isinstance(ani, dict) else None
        # LA FINITION EST-ELLE ACTIVE ? (résidu de re-revue Task 5) — c'est la
        # présence d'une RECETTE (le bloc `pbr`) qui compte, pas la simple
        # vérité du dictionnaire. Le saut de la map MR plus bas repose sur
        # « la finition écrit les facteurs de micro-surface » : un paquet MAL
        # FORMÉ n'en écrit AUCUN, et jeter pour lui une map MR parfaitement
        # valide reviendrait à dégrader DEUX fois pour une seule donnée
        # douteuse (la finition perdue ET la matière perdue).
        fin_actif = isinstance(fin, dict) and isinstance(fin.get("pbr"), dict)
        if ani and m.get("uv_axis_aligned") is not True:
            # GARDE (Task 6) : la tangente constante ci-dessous n'est vraie que
            # sur nos plans et nos reliefs. Sur un maillage de moteur (mesh3d,
            # UV dépaquetées par un atlas) elle peignerait n'importe comment —
            # refuser NOMMÉMENT vaut mieux que livrer un reflet faux.
            raise ValueError(
                f"anisotropie exigée sur un maillage aux UV non alignées "
                f"({nom!r}) — réservée aux plans/reliefs du lab")
        ip = add_accessor(m["positions"], 3, 5126, "VEC3", 34962)
        inm = add_accessor(m["normals"], 3, 5126, "VEC3", 34962)
        iuv = add_accessor(m["uvs"], 2, 5126, "VEC2", 34962)
        iix = add_accessor(m["indices"], 1, 5125, "SCALAR", 34963)
        attrs = {"POSITION": ip, "NORMAL": inm, "TEXCOORD_0": iuv}
        if ani:
            # TANGENT EXIGÉ par KHR_materials_anisotropy : sans lui le moteur
            # improvise une tangente d'écran et le peigne du sceau tourne avec
            # la caméra. Nos quads et nos dalles ont u sur +x : T = +x.
            #
            # w = -1, ET PAS +1. Nos UV sont INVERSÉES EN V (« v inversé
            # (image) », `quad_mesh`) : dP/dv = -y tandis que cross(N, T) =
            # cross(+z, +x) = +y. La règle glTF (w = signe de
            # dot(cross(N, T), B)) donne donc -1 — c'est EXACTEMENT ce que
            # calcule `gltf_builder.py:485` du dépôt, dont l'en-tête
            # (:139-141) documente ce changement de signe après un retournement
            # de v. Avec +1, le champ anisotrope devient RADIAL sur les
            # diagonales (un nœud papillon au lieu du métal brossé en cercle)
            # et le vert d'une normal map s'inverse sur tout élément qui porte
            # à la fois `mat_maps.normal` et une finition anisotrope.
            #
            # DOCTRINE TANGENT, DÉCISION CONSIGNÉE (résidu de re-revue Task 5)
            # — ce writer n'émet TANGENT que SOUS ANISOTROPIE, jamais pour une
            # simple normal map. Le constructeur générique du dépôt
            # (gltf_builder.py) tient la tangente pour « pas optionnelle » ;
            # nous divergeons EN CONNAISSANCE DE CAUSE : sans TANGENT, un
            # client conforme DÉRIVE la base tangente des UV du triangle
            # (glTF 2.0, « When tangents are not specified, client
            # implementations SHOULD calculate tangents using default MikkTSpace
            # algorithms »), et sur des UV comme les nôtres — alignées sur les
            # axes, v inversé — la tangente dérivée tombe sur EXACTEMENT la
            # même main que celle écrite ici (w = -1). Mieux, même : la
            # dérivation par triangle donne une tangente JUSTE sur les jupes de
            # relief, là où notre constante est dégénérée (voir juste en
            # dessous). L'anisotropie, elle, n'a pas ce luxe — son extension
            # EXIGE l'attribut, faute de quoi le peigne suit la caméra. À
            # rouvrir si un visualiseur réel prouve le contraire, et alors avec
            # de VRAIES tangentes PAR SOMMET, pas avec cette constante.
            #
            # DÉGÉNÉRESCENCE ASSUMÉE : sur les murs i=0 et i=gx d'un relief, la
            # normale est ±x — donc PARALLÈLE à cette tangente, et le repère
            # TBN y est plat. La jupe fait 0,3 mm et ne reçoit aucun peigne
            # regardable ; la nommer vaut mieux que la faire semblant de
            # corriger avec une tangente par sommet que rien ne mesure.
            attrs["TANGENT"] = add_accessor(
                [1.0, 0.0, 0.0, -1.0] * (len(m["positions"]) // 3),
                4, 5126, "VEC4", 34962)
        pbr = {"baseColorTexture": {"index": add_texture(el["png"], nom)},
               "metallicFactor": 0.0, "roughnessFactor": 0.9}
        mat = {"name": nom, "pbrMetallicRoughness": pbr,
               **({"alphaMode": "BLEND", "doubleSided": True}
                  if el.get("alpha") else {})}
        # LA MATIÈRE (`mat_maps`) : des PNG déjà cuits par `material_pngs`.
        mm = el.get("mat_maps")
        mm = mm if isinstance(mm, dict) else {}
        if mm.get("normal"):
            mat["normalTexture"] = {
                "index": add_texture(mm["normal"], f"{nom}-normal", True)}
        # LE PACK MR EST SAUTÉ QUAND UNE FINITION EST POSÉE. glTF MULTIPLIE le
        # facteur par la texture : garder les deux donnerait rugosité =
        # 0,12 x G/255 et métallicité = 1,0 x B/255 — une dorure posée sur une
        # matière mate virerait au miroir noir, exactement l'inverse de ce que
        # les deux réglages disent séparément. SÉMANTIQUE ACTÉE : une feuille
        # holographique REMPLACE la micro-surface (MR) de la matière, mais
        # laisse parler son RELIEF (normale) et son OCCLUSION — c'est ce que
        # fait une vraie dorure à chaud sur un carton texturé.
        if mm.get("mr") and not fin_actif:
            pbr["metallicRoughnessTexture"] = {
                "index": add_texture(mm["mr"], f"{nom}-mr", True)}
            # glTF calcule rugosité = roughnessFactor x texture.G et
            # métallicité = metallicFactor x texture.B : garder le 0.9/0.0 par
            # défaut MULTIPLIERAIT la map par le niveau une seconde fois
            # (doctrine `RENDER_NOTE` du lab Matières). Les niveaux sont dans
            # les octets — les facteurs redeviennent neutres.
            pbr["metallicFactor"] = 1.0
            pbr["roughnessFactor"] = 1.0
        if mm.get("ao"):
            mat["occlusionTexture"] = {
                "index": add_texture(mm["ao"], f"{nom}-ao", True)}
        if mm.get("emissive"):
            mat["emissiveTexture"] = {
                "index": add_texture(mm["emissive"], f"{nom}-emissive", True)}
            mat["emissiveFactor"] = [1.0, 1.0, 1.0]
        # LA FINITION (`finish`) EN DERNIER : ses facteurs de recette sont les
        # SEULS en piste côté micro-surface (le pack MR vient d'être sauté
        # au-dessus), et ils écrasent le 0.9/0.0 par défaut de la 2a.
        if fin:
            rec = fin.get("pbr")
            rec = rec if isinstance(rec, dict) else {}
            base = rec.get("baseColorFactor")
            if isinstance(base, (list, tuple)) and len(base) == 4:
                # RECOPIÉ, jamais partagé : le document ne doit pas garder une
                # référence vers la liste de l'appelant.
                pbr["baseColorFactor"] = [_f(v) for v in base]
            for cle in ("metallicFactor", "roughnessFactor"):
                if cle in rec:
                    pbr[cle] = _f(rec[cle], pbr[cle])
            ext: dict = {}
            if iri:
                ep = iri.get("thickness")
                ep = (ep if isinstance(ep, (list, tuple)) and len(ep) == 2
                      else [100.0, 400.0])
                bloc = {"iridescenceFactor": _f(iri.get("factor"), 1.0),
                        "iridescenceIor": _f(iri.get("ior"), 1.3),
                        "iridescenceThicknessMinimum": _f(ep[0]),
                        "iridescenceThicknessMaximum": _f(ep[1])}
                if iri.get("png"):
                    bloc["iridescenceThicknessTexture"] = {
                        "index": add_texture(iri["png"],
                                             f"{nom}-iridescence", True)}
                ext["KHR_materials_iridescence"] = bloc
            if cc:
                ext["KHR_materials_clearcoat"] = {
                    "clearcoatFactor": _f(cc.get("factor"), 1.0),
                    "clearcoatRoughnessFactor": _f(cc.get("rough"), 0.03)}
            if ani:
                bloc = {"anisotropyStrength": _f(ani.get("strength"), 0.5)}
                if ani.get("png"):
                    bloc["anisotropyTexture"] = {
                        "index": add_texture(ani["png"],
                                             f"{nom}-anisotropie", True)}
                ext["KHR_materials_anisotropy"] = bloc
            if ext:
                mat["extensions"] = ext
                exts_used.update(ext)
        materials.append(mat)
        meshes.append({"name": nom, "primitives": [{
            "attributes": attrs, "indices": iix,
            "material": len(materials) - 1}]})
        nodes.append({"name": nom, "mesh": len(meshes) - 1, **_node_trs(el)})
    # LES ENFANTS DE LA RACINE, ÉNUMÉRÉS : un élément local = un nœud, mais un
    # externe en apporte tout un ARBRE — prendre `range(len(nodes))` comme en
    # 2a hisserait chacun de ses nœuds internes au rang de racine (la carte
    # exploserait en pièces détachées, chacune à l'origine).
    enfants = list(range(len(nodes)))
    doc_ext = {"extensionsUsed": exts_used, "extensionsRequired": exts_required}
    for i_ext, ext in enumerate(externals or []):
        parent, perdus = _merge_external(
            doc_ext, buf, views, accessors, images, textures, materials,
            meshes, nodes, samplers, ext)
        enfants.append(parent)
        if isinstance(out_ignored, list):
            nom_ext = str((ext or {}).get("name") or "externe")[:60]
            # `index` : le RANG dans `externals`, seule clé qui ne peut pas
            # collisionner (deux couches homonymes des deux côtés d'une carte
            # portent le MÊME nom d'élément — attribuer l'aveu par le nom
            # l'accrocherait alors au mauvais nœud).
            out_ignored.extend(
                {"index": i_ext, "name": nom_ext,
                 "why": f"{p} : non repris de l'element externe"}
                for p in perdus)
    # PIÈGE DU SQUELETTE (auto-revue) : le buffer doit être aligné à 4 AVANT
    # que `buffers[0].byteLength` ne soit figé dans le JSON — la dernière
    # écriture de la boucle (un PNG, taille arbitraire) laisse `buf`
    # potentiellement désaligné. Padder ICI, avant de construire `doc`, pas
    # après l'avoir sérialisé : sinon le JSON porte un byteLength trop petit
    # (mesuré avant coup) pendant que le chunk BIN réellement écrit, lui,
    # est plus long (padding déjà ajouté) — total et byteLength dérivent l'un
    # de l'autre. Ici, `len(buf)` à la construction de `doc` EST déjà la
    # longueur finale du chunk BIN : plus rien ne l'allonge après.
    pad4()
    # extras posé aux DEUX etages (asset ET racine), assumé : les DCC gardent
    # node.extras en propriétés custom et JETTENT asset.extras (Blender) ;
    # three.js expose node.extras en userData — un seul emplacement ne
    # survivrait pas partout.
    racine = {"name": str(name)[:60], "scale": [0.001, 0.001, 0.001],
              "children": enfants, "extras": extras}
    nodes.append(racine)
    # `extensionsUsed` : l'union TRIÉE de ce qui a RÉELLEMENT servi, et la clé
    # DISPARAÎT quand rien n'a servi — un GLB de la 2a reste un GLB de la 2a,
    # sans un tableau vide qui laisserait croire à des extensions.
    # Et JAMAIS `extensionsRequired` DES NÔTRES : iridescence, clearcoat et
    # anisotropie sont des ENJOLIVURES. Les EXIGER ferait REFUSER le fichier
    # par tout lecteur qui ne les connaît pas, alors qu'il l'afficherait très
    # bien sans elles (dégradation propre — la carte perd son reflet, pas son
    # existence). Celles d'un GLB EXTERNE, en revanche, sont CONSERVÉES telles
    # quelles : si son maillage est compressé Draco, le document fusionné
    # l'exige VRAIMENT — le taire livrerait un fichier qui s'ouvre sur du vide.
    #
    # Les tableaux VIDES sont OMIS (glTF impose minItems 1 partout) : une scène
    # 100 % moteur sans un seul matériau produirait sinon un `"materials": []`
    # qui fait échouer la validation. Sur une scène 2a, aucun de ces tableaux
    # n'est vide — les octets d'un GLB 2a ne bougent pas d'un bit.
    doc = {"asset": {"version": "2.0", "extras": extras},
           **({"extensionsUsed": sorted(exts_used)} if exts_used else {}),
           **({"extensionsRequired": sorted(exts_required)}
              if exts_required else {}),
           "scene": 0, "scenes": [{"name": str(name)[:60], "nodes": [len(nodes) - 1]}],
           "nodes": nodes,
           **({"meshes": meshes} if meshes else {}),
           **({"materials": materials} if materials else {}),
           **({"textures": textures} if textures else {}),
           **({"images": images} if images else {}),
           "samplers": samplers,
           "accessors": accessors, "bufferViews": views,
           "buffers": [{"byteLength": len(buf)}]}
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(buf)
    out = struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
    return out


# ── LA RELECTURE — UN GLB DE MOTEUR, RAMENÉ AU TYPE COMMUN (Task 4, 2b) ─────
# Le writer ci-dessus fabrique nos propres GLB ; ces lecteurs-là relisent ceux
# des MOTEURS (Meshy, fal), dont nous ne contrôlons pas un octet. C'est ce qui
# permet de mesurer `closed` UNE fois à l'import (et de le cacher dans le job)
# au lieu de le redemander à chaque écran — et de refuser un STL MOTIVÉ sur un
# maillage ouvert, exactement comme la 2a le fait sur nos maillages locaux.
#
# DISCIPLINE : ces fonctions lèvent `ValueError` NOMMÉE sur toute entrée
# douteuse — jamais `struct.error`, `KeyError` ni `IndexError` nus. L'appelant
# (une route) en fait un refus motivé ; une exception anonyme, elle, devient un
# 500 (doctrine 2.5 du domaine : jamais 500 sur une donnée d'entrée).

def read_glb(data: bytes) -> tuple[dict, bytes]:
    """Document JSON + chunk BIN d'un GLB. ValueError NOMMÉE sinon (la route
    la transforme en refus motivé, jamais un 500).

    Le chunk BIN est FACULTATIF (un GLB peut n'avoir que du JSON) : absent,
    on rend b"" plutôt que de lever — c'est `glb_scene_mesh` qui décidera si
    l'absence de géométrie est une faute, avec SON message."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("pas un GLB (octets attendus)")
    data = bytes(data)
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("pas un GLB (magie glTF absente)")
    doc_len = struct.unpack("<I", data[12:16])[0]
    if 20 + doc_len > len(data):
        raise ValueError("GLB tronqué (chunk JSON)")
    try:
        doc = json.loads(data[20:20 + doc_len].decode("utf-8").rstrip("\x00 "))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"GLB au document JSON illisible ({e})") from e
    if not isinstance(doc, dict):
        raise ValueError("GLB au document JSON qui n'est pas un objet")
    off = 20 + doc_len
    binv = b""
    if off + 8 <= len(data):
        blen = struct.unpack("<I", data[off:off + 4])[0]
        binv = data[off + 8:off + 8 + blen]
    return doc, binv


def _accessor_view(doc: dict, idx: int) -> tuple[dict, int]:
    """(accesseur, offset absolu dans le chunk BIN) — bornes vérifiées."""
    try:
        acc = doc["accessors"][idx]
        bv = doc["bufferViews"][acc["bufferView"]]
        return acc, int(bv.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ValueError(f"accesseur {idx!r} illisible ({e})") from e


def _accessor_floats(doc: dict, binv: bytes, idx: int) -> list[float]:
    acc, off = _accessor_view(doc, idx)
    # LE COUPLAGE, RENDU EXPLICITE (résidu de la re-revue Task 6) : ce lecteur
    # ne décode QUE du float32 (5126). Un accesseur quantifié
    # (KHR_mesh_quantization : 5120/5121/5122/5123) relu ici en flottants
    # rendrait des positions ABSURDES sans lever — un GLB parfaitement valide
    # qui mesure et imprime la mauvaise chose. C'est LA raison pour laquelle
    # `_EXIG_CONNUES` n'accueille pas cette extension : la garde et l'allowlist
    # disent maintenant la même chose, chacune à son étage.
    ct = acc.get("componentType") if isinstance(acc, dict) else None
    if ct != 5126:
        raise ValueError(f"accesseur {idx!r} non float32 (componentType "
                         f"{ct!r}) — quantization non fusionnable")
    try:
        n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
        return list(struct.unpack_from("<" + "f" * (int(acc["count"]) * n),
                                       binv, off))
    except (KeyError, TypeError, ValueError, struct.error) as e:
        raise ValueError(f"accesseur flottant {idx!r} illisible ({e})") from e


def _accessor_indices(doc: dict, binv: bytes, idx: int) -> list[int]:
    acc, off = _accessor_view(doc, idx)
    try:
        fmt = {5121: "B", 5123: "H", 5125: "I"}[acc["componentType"]]
        return list(struct.unpack_from("<" + fmt * int(acc["count"]), binv, off))
    except (KeyError, TypeError, ValueError, struct.error) as e:
        raise ValueError(f"accesseur d'indices {idx!r} illisible ({e})") from e


def _mesh_prims(mesh):
    """Les primitives TRIANGLES d'UN mesh (mode 4, le défaut glTF)."""
    if not isinstance(mesh, dict):
        return
    for prim in mesh.get("primitives") or []:
        if isinstance(prim, dict) and prim.get("mode", 4) == 4:
            yield prim


def _triangle_prims(doc: dict):
    """Les primitives TRIANGLES du document, TOUS meshes confondus — sans
    regarder qui les instancie. C'est ce qu'il faut pour une mesure de
    TOPOLOGIE (`closed`), qu'aucun transform de nœud ne change."""
    for mesh in doc.get("meshes") or []:
        yield from _mesh_prims(mesh)


# ── LES TRANSFORMS DE NŒUDS, COMPOSÉS (Task 6) ──────────────────────────────
# La topologie se moque des transforms ; le PLACEMENT, lui, en vit. Mesurer un
# GLB de moteur sur ses positions BRUTES revient à parier que sa scène est à
# l'identité — pari perdu dès qu'un exportateur pose une conversion d'axes
# (Y-up -> Z-up) ou une échelle d'unité sur son nœud racine : le fit calculé
# sur du brut placerait alors la pièce couchée, ou mille fois trop petite.
# Composer les matrices rend le fit JUSTE quelle que soit l'unité du moteur —
# un GLB en mètres, en centimètres ou en pouces tient dans la même boîte de
# couche, puisque c'est sa taille RENDUE qu'on mesure.
_IDENT4 = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
           0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

# LA PROFONDEUR DE SCÈNE A SA PROPRE BORNE, et elle est PLUS HAUTE que celle
# des balayages JSON (`_PROF_MAX`, 12) : ces deux profondeurs ne mesurent pas
# la même chose. `_PROF_MAX` borne l'imbrication d'un DICTIONNAIRE (un
# matériau glTF réel tient en 4 niveaux ; 12 est déjà large). Une hiérarchie
# de NŒUDS, elle, est un objet de modelage — un rig exporté, une pièce
# assemblée en sous-ensembles descendent couramment à 15 ou 20 niveaux, et
# les tronquer à 12 supprimerait de la géométrie livrée.
_SCENE_PROF_MAX = 32


def _mat4_mul(a: list, b: list) -> list:
    """`a x b` en convention glTF (COLONNE par colonne) : le résultat applique
    `b` PUIS `a` — l'ordre parent x enfant d'une descente de scène."""
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = (a[r] * b[c * 4]
                              + a[4 + r] * b[c * 4 + 1]
                              + a[8 + r] * b[c * 4 + 2]
                              + a[12 + r] * b[c * 4 + 3])
    return out


def _node_matrix(nd: dict) -> list:
    """La matrice d'UN nœud : sa `matrix` si elle existe, sinon T x R x S
    (l'ordre imposé par glTF 2.0). Toute valeur douteuse retombe sur
    l'identité — jamais une exception (ce module lit des octets tiers)."""
    m = nd.get("matrix")
    if isinstance(m, (list, tuple)) and len(m) == 16:
        return [_f(v) for v in m]
    t = nd.get("translation")
    t = ([_f(v) for v in t] if isinstance(t, (list, tuple)) and len(t) == 3
         else [0.0, 0.0, 0.0])
    s = nd.get("scale")
    s = ([_f(v, 1.0) for v in s] if isinstance(s, (list, tuple)) and len(s) == 3
         else [1.0, 1.0, 1.0])
    q = nd.get("rotation")
    x, y, z, w = ([_f(v) for v in q]
                  if isinstance(q, (list, tuple)) and len(q) == 4
                  else [0.0, 0.0, 0.0, 1.0])
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]
    return [r[0] * s[0], r[1] * s[0], r[2] * s[0], 0.0,
            r[3] * s[1], r[4] * s[1], r[5] * s[1], 0.0,
            r[6] * s[2], r[7] * s[2], r[8] * s[2], 0.0,
            t[0], t[1], t[2], 1.0]


def _meshes_du_monde(doc: dict) -> list:
    """`(indice de mesh, matrice MONDE)` pour chaque mesh atteint depuis les
    scènes. Descente BORNÉE en profondeur ET par un ensemble de nœuds déjà
    vus : glTF interdit qu'un nœud ait deux parents, un document malformé (ou
    hostile) ne s'en prive pas — un `children` qui reboucle ferait tourner la
    descente sans fin."""
    nodes = doc.get("nodes")
    nodes = nodes if isinstance(nodes, list) else []
    depart: list = []
    for sc in (doc.get("scenes") or []):
        for k in ((sc.get("nodes") if isinstance(sc, dict) else None) or []):
            if isinstance(k, int) and 0 <= k < len(nodes):
                depart.append(k)
    if not depart:                    # aucune scène : tous les nœuds sans parent
        enfants: set = set()
        for nd in nodes:
            if isinstance(nd, dict):
                for c in (nd.get("children") or []):
                    enfants.add(c)
        depart = [i for i in range(len(nodes)) if i not in enfants]
    out: list = []
    vus: set = set()
    pile = [(k, _IDENT4, 0) for k in depart]
    while pile:
        i, parent, prof = pile.pop()
        if i in vus or not (0 <= i < len(nodes)):
            continue
        if prof > _SCENE_PROF_MAX:
            # UN REFUS, PAS UNE TRONCATURE : sauter les nœuds trop profonds
            # rendrait une scène AMPUTÉE sans le dire — le fit se calculerait
            # sur une boîte trop petite et le STL sortirait `closed` avec des
            # morceaux en moins. Le silence coûte ici plus cher que le refus.
            raise ValueError(
                f"GLB externe : hierarchie de scene trop profonde "
                f"(au-dela de {_SCENE_PROF_MAX} niveaux)")
        vus.add(i)
        nd = nodes[i] if isinstance(nodes[i], dict) else {}
        monde = _mat4_mul(parent, _node_matrix(nd))
        if isinstance(nd.get("mesh"), int) and not isinstance(nd.get("mesh"), bool):
            out.append((nd["mesh"], monde))
        for c in (nd.get("children") or []):
            if isinstance(c, int):
                pile.append((c, monde, prof + 1))
    return out


def _applique_mat4(pts: list, m: list) -> list:
    """Les positions passées à la moulinette d'une matrice 4x4 (colonnes
    glTF). L'identité rend la MÊME liste : le cas de très loin le plus
    fréquent ne paie pas une recopie."""
    if m == _IDENT4:
        return pts
    out = [0.0] * len(pts)
    for k in range(0, len(pts) - 2, 3):
        x, y, z = pts[k], pts[k + 1], pts[k + 2]
        out[k] = m[0] * x + m[4] * y + m[8] * z + m[12]
        out[k + 1] = m[1] * x + m[5] * y + m[9] * z + m[13]
        out[k + 2] = m[2] * x + m[6] * y + m[10] * z + m[14]
    return out


def glb_triangle_estimate(doc: dict) -> int:
    """Le nombre de triangles ANNONCÉ par les accesseurs — sans décoder un
    seul octet de géométrie. Les bornes AVANT décodage sont la doctrine du
    domaine : `mesh_measures` alloue ~3 entrées de dictionnaire par triangle,
    décider APRÈS avoir tout déplié serait décider trop tard."""
    total = 0
    for prim in _triangle_prims(doc):
        ai = prim.get("indices")
        if ai is None:
            ai = (prim.get("attributes") or {}).get("POSITION")
        try:
            total += int(doc["accessors"][ai]["count"]) // 3
        except (KeyError, IndexError, TypeError, ValueError):
            continue                 # un accesseur illisible sera NOMMÉ plus bas
    return total


def glb_scene_mesh(data: bytes, world: bool = False) -> dict:
    """Concatène POSITION+indices des primitives triangles d'un GLB en un mesh
    {positions, indices} pour `mesh_measures`/STL. ValueError nommée si rien
    n'est mesurable.

    `world=False` (défaut, contrat de la tâche 4) : TOUTES les primitives du
    document, positions BRUTES, transforms de nœuds IGNORÉS. C'est ce qu'il
    faut pour une mesure de TOPOLOGIE — `closed` ne dépend d'aucun transform,
    et un mesh que rien n'instancie compte quand même comme géométrie livrée.

    `world=True` (tâche 6) : la scène TELLE QU'ELLE SERA VUE — descente du
    graphe de nœuds, matrices COMPOSÉES, positions dans le repère de la scène.
    C'est ce qu'il faut pour PLACER (fit) et pour IMPRIMER (STL), les deux
    devant montrer la même chose que le GLB. Repli automatique sur le
    balayage brut si AUCUN nœud n'instancie de mesh (le GLB du simulateur
    Meshy, entre autres) : une géométrie orpheline vaut mieux que rien.

    Une primitive SANS `indices` n'est PAS une faute : glTF 2.0 la définit
    comme un tirage NON INDEXÉ, ses sommets se suivant dans l'ordre. Le GLB du
    simulateur Meshy est exactement cela (un triangle nu) — la refuser ferait
    échouer une mesure parfaitement calculable."""
    doc, binv = read_glb(data)
    couples: list = []
    if world:
        meshes = doc.get("meshes")
        meshes = meshes if isinstance(meshes, list) else []
        for mi, monde in _meshes_du_monde(doc):
            if 0 <= mi < len(meshes):
                couples.extend((prim, monde) for prim in _mesh_prims(meshes[mi]))
    if not couples:
        couples = [(prim, None) for prim in _triangle_prims(doc)]
    positions: list[float] = []
    indices: list[int] = []
    for prim, monde in couples:
        attrs = prim.get("attributes")
        if not isinstance(attrs, dict) or "POSITION" not in attrs:
            raise ValueError("primitive triangle sans POSITION")
        base = len(positions) // 3
        pts = _accessor_floats(doc, binv, attrs["POSITION"])
        positions += pts if monde is None else _applique_mat4(pts, monde)
        if prim.get("indices") is None:
            indices += list(range(base, base + len(pts) // 3))
        else:
            indices += [base + i
                        for i in _accessor_indices(doc, binv, prim["indices"])]
    if not indices:
        raise ValueError("aucune primitive triangle dans le GLB")
    # dernier garde-fou AVANT que `mesh_measures` n'indexe : un indice hors
    # bornes (GLB de moteur malformé) y lèverait un IndexError nu — donc un
    # 500 chez l'appelant, exactement ce que ce module s'interdit.
    if (max(indices) + 1) * 3 > len(positions):
        raise ValueError("GLB aux indices hors bornes (maillage incohérent)")
    return {"positions": positions, "indices": indices}


# ── L'IMPRESSION 3D — STL LOCAL (Task 4) ────────────────────────────────────
# `_write_stl_binary` : copie RÉDUITE du principe de `gltf.py:build_stl`
# (règle 8, zéro import pièce->pièce, même patron que le reste de ce
# fichier) — positions déjà en MILLIMÈTRES (nos meshes locaux, contrairement
# à ceux de P8, ne portent pas d'échelle mesh->mm à part), en-tête 80 octets
# SANS nom d'outil (le nom de l'artefact, comme gltf.py:build_stl), une
# normale par facette recalculée depuis la géométrie (le format n'a ni UV ni
# matière). Le SEUL appelant (build3d) ne le convoque qu'après avoir vérifié
# que TOUS les éléments portent `closed: True` — gate sur le drapeau DÉCLARÉ
# par les constructeurs de maillage, jamais une re-mesure ici.
#
# DEUX PASSES (legs 6, revue finale 2a) : l'ancienne version accumulait
# chaque triangle dans une liste Python de tuples AVANT d'écrire — mesuré à
# ~160 Mo d'intermédiaires par relief au grid max. Ici, une première passe
# compte les triangles (pour dimensionner le buffer de sortie UNE fois),
# la seconde passe packe chaque facette DIRECTEMENT dedans (`struct.pack_into`,
# aucune structure intermédiaire) — même sortie, au bit près : le test de
# couture le prouve par égalité d'octets, pas par relecture du format.
def _write_stl_binary(elements: list, name: str) -> bytes:
    """STL binaire local, en millimètres, DEUX PASSES : compter d'abord le
    total de triangles (pour dimensionner le buffer de sortie UNE fois), puis
    packer chaque facette directement dedans — l'ancienne version
    matérialisait toute la géométrie en tuples Python avant d'écrire (~160 Mo
    d'intermédiaires par relief au grid max, mesuré en 2a). Même sortie, au
    bit près (couture legs 6, revue finale 2a). `z_mm` de chaque élément
    (l'écart de pile porté par SON nœud, comme dans le GLB) est appliqué aux
    positions puisque le format STL n'a pas de nœud pour le porter.

    `elements` est parcouru DEUX FOIS (le comptage, puis l'emballage) : une
    LISTE (ou toute séquence re-parcourable), jamais un générateur à usage
    unique — la seconde passe le trouverait épuisé et écrirait un buffer de
    la bonne taille mais rempli de zéros après le premier élément."""
    total = sum(len(el["mesh"]["indices"]) // 3 for el in elements)
    out = bytearray(84 + 50 * total)
    # [:80] n'est pas cosmétique : le compte de triangles est empaqueté à
    # l'offset FIXE 80 juste en dessous (struct.pack_into("<I", out, 80, ...))
    # -- une entête qui déborderait au-delà de 80 octets décalerait ce champ
    # (et toute la suite du buffer), le corrompant silencieusement.
    entete = f"{name} - millimetres - {total} triangles".encode(
        "ascii", "ignore")[:80]
    out[0:len(entete)] = entete
    struct.pack_into("<I", out, 80, total)
    off = 84
    for el in elements:
        pos, idx = el["mesh"]["positions"], el["mesh"]["indices"]
        z = float(el.get("z_mm") or 0.0)
        for t in range(0, len(idx) - 2, 3):
            a, b, c = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
            ax, ay, az = pos[a], pos[a + 1], pos[a + 2] + z
            bx, by, bz = pos[b], pos[b + 1], pos[b + 2] + z
            cx, cy, cz = pos[c], pos[c + 1], pos[c + 2] + z
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            struct.pack_into("<12fH", out, off,
                             nx / ln, ny / ln, nz / ln,
                             ax, ay, az, bx, by, bz, cx, cy, cz, 0)
            off += 50
    return bytes(out)
