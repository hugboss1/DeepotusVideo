# -*- coding: utf-8 -*-
"""t331 (A1 du lot Scenario, 29/10/2026) — les GABARITS du pont « Scène Blender » : le SEUL code que le backend envoie
à `execute_blender_code` (mcp-for-blender, Blender ouvert de l'utilisateur, BLENDER_MCP_SAFE_MODE=1). PUR : aucune E/S.

Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A1 (« execute_blender_code UNIQUEMENT
avec gabarits générés par le backend : caméra + focale, 3 points, empty de blocking, clés ») et les risques de la même
spec (« execute_blender_code = code arbitraire : jamais de texte libre du LLM »).

LE SCRIPT EST GÉNÉRÉ ICI, JAMAIS REÇU — même discipline que les passes headless (t334, passes_blender.GABARIT) :
  * `GABARIT` est un texte FIXE ; un seul trou, `__PARAMS__`, reçoit le repr() d'un JSON ASCII ;
  * le JSON est bâti par `depuis_scene` à partir de la scène du Plateau VÉRIFIÉE (scene3d : nombres finis, keyframes
    croissantes) et d'énumérations fermées (`ELEMENTS`), puis re-vérifié par `verifier` (types, bornes, noms
    nettoyés) : aucune chaîne venue de la page n'est du code — un nom d'instance ne vit que dans le JSON, relu par
    json.loads côté Blender (banc test_blender_pont : l'arbre syntaxique du script est celui du gabarit quelle que soit
    la scène, et le validateur du mode sûr de mcp-for-blender l'accepte quand il est installé) ;
  * le script ne touche QUE ses objets : tout ce qu'il crée porte le préfixe « DZ_ » et vit dans la collection
    « DZ_Deepotus » ; un nouvel envoi remplace les objets DZ_ du même élément, jamais ceux de l'utilisateur.
    « nettoyer » retire la collection et ses objets.

Éléments (au choix de l'utilisateur, cases de la boîte) :
  * camera    la caméra du plan (DZ_Camera) : position, visée, FOCALE en mm (capteur 24 mm en hauteur, comme le champ
              vertical du Plateau), format du rendu (résolution), devient la caméra de la scène ;
  * eclairage trois points autour du sujet (clé 45° côté caméra, débouchage en face, plus faible, contre derrière),
              lampes surfaciques DZ_Cle, DZ_Debouchage, DZ_Contre tournées vers le sujet ;
  * blocking  un EMPTY « cube » par forme du Plateau (faisceaux exclus), à la taille et à l'orientation de sa boîte,
              couleur d'objet = la palette de la previs colorée (t333, `previs_palette` → table `blender`), propriétés
              dz_cle / dz_libelle / dz_palette ;
  * cles      les clés d'animation de la caméra (position, rotation, focale) aux temps des keyframes du Plateau, à la
              cadence de la scène Blender (24 i/s), interpolation Bézier.

Repère : le Plateau est en Y-haut (glTF), Blender en Z-haut : (x, y, z) → (x, −z, y), comme l'importeur glTF et
passes_blender.vers_blender. Les matrices sont calculées ICI ; Blender ne fait que les poser.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata

from app.services import scene3d as S

ELEMENTS = ("camera", "eclairage", "blocking", "cles")
COLLECTION = "DZ_Deepotus"
FPS = 24
CAPTEUR_H_MM = 24.0
MAX_BLOCKING = 200
MAX_CLES = 64
MAX_NOM = 48
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_NOM_SUR = re.compile(r"[^0-9A-Za-z _\-().']+")


class GabaritRefuse(ValueError):
    """Une scène ou des paramètres inutilisables (400/409 côté route)."""


# ── repère et matrices ────────────────────────────────────────────────────────────────────────────────────────────

def vers_blender(p) -> list:
    """glTF (Y en haut) → Blender (Z en haut) : (x, y, z) → (x, −z, y)."""
    x, y, z = (float(v) for v in p)
    return [x, -z, y]


def _matrice_blender(m3: list) -> list:
    """Une matrice 3×3 du repère glTF exprimée dans le repère Blender : C·M·Cᵀ, C = la permutation ci-dessus."""
    c = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    ct = [[c[j][i] for j in range(3)] for i in range(3)]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(mul(c, m3), ct)


def focale_mm(fov_v: float) -> float:
    """La focale (mm) qui donne le champ VERTICAL `fov_v` (degrés) sur un capteur de 24 mm de haut."""
    f = float(fov_v)
    if not 0 < f < 179:
        raise GabaritRefuse("champ de caméra hors bornes")
    return round((CAPTEUR_H_MM / 2) / math.tan(math.radians(f) / 2), 4)


def nom_sur(texte, defaut: str = "forme") -> str:
    """Un nom d'objet lisible et inoffensif : lettres sans accent, chiffres, espace, tiret, souligné, parenthèses."""
    t = unicodedata.normalize("NFKD", str(texte or ""))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = " ".join(_NOM_SUR.sub(" ", t).split())[:MAX_NOM].strip()
    return t or defaut


def _r(v, n=6):
    return round(float(v), n)


# ── la scène du Plateau → paramètres ─────────────────────────────────────────────────────────────────────────────

def _camera(etat: dict) -> dict:
    pos = S.position_camera(etat["orbit"], etat["target"])
    fov = S._num(etat["fov"], "fov", 0, strict=True)
    return {"pos": [_r(v) for v in vers_blender(pos)], "cible": [_r(v) for v in vers_blender(etat["target"])],
            "focale_mm": focale_mm(fov)}


def _etat_initial(scene: dict) -> dict:
    kfs = scene.get("keyframes") or []
    if kfs:
        k = S.valider_keyframes(kfs)[0]
        return {"orbit": list(k["orbit"]), "target": list(k["target"]), "fov": k["fov"]}
    cam = scene.get("camera")
    if not isinstance(cam, dict):
        raise GabaritRefuse("la scène n'a ni caméra ni keyframe")
    return {"orbit": S._vec(cam.get("orbit"), "orbit"), "target": S._vec(cam.get("target"), "target"),
            "fov": S._num(cam.get("fov"), "fov", 0, strict=True)}


def _bloc(inst: dict, couleur: str, cle: str, libelle: str) -> dict:
    """Un empty de blocking : la matrice monde (Blender) du cube unité [-1, 1]³ qui épouse la boîte de l'instance."""
    w, h, d = S._vec(inst.get("dims"), "dims")
    if min(w, h, d) <= 0:
        raise GabaritRefuse("dims : trois longueurs positives attendues")
    tr = inst.get("transform") or {}
    pos = S._vec(tr.get("pos", [0, 0, 0]), "pos")
    rot = S._vec(tr.get("rot", [0, 0, 0]), "rot")
    s = S._num(tr.get("scale", 1), "scale", 0, strict=True)
    m = S._rotation(rot)
    centre = [pos[i] + sum(m[i][k] * v for k, v in enumerate((0.0, h * s / 2, 0.0))) for i in range(3)]
    demi = (w * s / 2, h * s / 2, d * s / 2)
    rs = [[m[i][j] * demi[j] for j in range(3)] for i in range(3)]          # rotation × demi-tailles (glTF)
    mb = _matrice_blender(rs)
    cb = vers_blender(centre)
    monde = [[_r(mb[i][0]), _r(mb[i][1]), _r(mb[i][2]), _r(cb[i])] for i in range(3)] + [[0.0, 0.0, 0.0, 1.0]]
    rvb = [int(couleur[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return {"nom": "DZ_Blocking_" + nom_sur(libelle), "monde": monde, "couleur": [_r(c, 4) for c in rvb] + [1.0],
            "palette": couleur, "cle": nom_sur(cle, "cle")[:MAX_NOM], "libelle": nom_sur(libelle)}


def _centre_sujet(scene: dict, blocs: list) -> list:
    for inst in scene.get("instances") or []:
        if isinstance(inst, dict) and inst.get("role") == "sujet" and inst.get("dims"):
            cs = S.coins(inst)
            return [_r(v) for v in vers_blender([sum(p[i] for p in cs) / 8 for i in range(3)])]
    if blocs:
        return [_r(sum(b["monde"][i][3] for b in blocs) / len(blocs)) for i in range(3)]
    return [0.0, 0.0, 1.0]


def _eclairage(cam: dict, centre: list) -> list:
    """Trois points : la clé à 45° du côté droit de la caméra, en hauteur ; le débouchage à 45° à gauche, plus bas et
    trois fois plus faible ; le contre derrière le sujet, en hauteur. Distances proportionnelles à la caméra."""
    dx, dy = cam["pos"][0] - centre[0], cam["pos"][1] - centre[1]
    az = math.atan2(dy, dx)
    dist = max(2.0, min(30.0, math.hypot(dx, dy)))
    h = max(0.5, dist * 0.45)

    def point(angle, d, z):
        return [_r(centre[0] + d * math.cos(angle)), _r(centre[1] + d * math.sin(angle)), _r(centre[2] + z)]
    base = 60.0 * dist * dist / 9.0                       # W : ~60 W à 3 m, à l'inverse du carré de la distance
    return [{"nom": "DZ_Cle", "pos": point(az - math.radians(45), dist, h), "puissance": _r(base, 2),
             "taille": _r(max(0.5, dist / 4), 3)},
            {"nom": "DZ_Debouchage", "pos": point(az + math.radians(45), dist, h * 0.5),
             "puissance": _r(base / 3, 2), "taille": _r(max(1.0, dist / 2.5), 3)},
            {"nom": "DZ_Contre", "pos": point(az + math.pi, dist * 0.8, h * 1.2), "puissance": _r(base * 0.8, 2),
             "taille": _r(max(0.4, dist / 5), 3)}]


def depuis_scene(scene: dict, elements) -> dict:
    """PUR — les paramètres du gabarit pour la scène du Plateau VÉRIFIÉE et les éléments choisis."""
    if not isinstance(elements, (list, tuple)) or not elements or not all(isinstance(e, str) for e in elements) \
            or set(elements) - set(ELEMENTS):
        raise GabaritRefuse(f"éléments : {', '.join(ELEMENTS)}")
    voulus = [e for e in ELEMENTS if e in set(elements)]
    aspect = scene.get("aspect", "16:9")
    if aspect not in S.ASPECTS:
        raise GabaritRefuse(f"format inconnu ({aspect})")
    r = S.ASPECTS[aspect]
    largeur, hauteur = (1920, int(round(1920 / r / 2)) * 2) if r >= 1 else (int(round(1920 * r / 2)) * 2, 1920)
    cam = _camera(_etat_initial(scene))
    from app.services import previs_palette as PP
    instances = [i for i in (scene.get("instances") or []) if isinstance(i, dict)]
    pal = PP.palette(instances)
    exclus = set((pal.get("blender") or {}).get("exclus") or [])
    par_id = {}
    for e in pal.get("table") or []:
        for iid in e["ids"]:
            par_id[iid] = e
    blocs = []
    for inst in instances:
        if inst.get("id") in exclus or not inst.get("dims"):
            continue
        e = par_id.get(inst.get("id"))
        couleur = e["couleur"] if e else PP.GRIS_REPERE
        blocs.append(_bloc(inst, couleur if _HEX.match(couleur) else PP.GRIS_REPERE,
                           e["cle"] if e else "repere", PP.libelle(inst)))
    blocs = blocs[:MAX_BLOCKING]
    centre = _centre_sujet(scene, blocs)
    cles = []
    kfs = scene.get("keyframes") or []
    if len(kfs) >= 2:
        for k in S.valider_keyframes(kfs)[:MAX_CLES]:
            c = _camera(k)
            cles.append({"image": int(round(k["t"] * FPS)) + 1, **c})
    if "cles" in voulus and len(cles) < 2:
        raise GabaritRefuse("clés : le plan n'a pas de mouvement de caméra (deux keyframes au moins au Plateau)")
    if "blocking" in voulus and not blocs:
        raise GabaritRefuse("blocking : aucune forme à poser (le Plateau du plan est vide)")
    return {"version": 1, "collection": COLLECTION, "elements": voulus, "fps": FPS,
            "camera": {**cam, "nom": "DZ_Camera", "capteur_mm": CAPTEUR_H_MM, "largeur": largeur,
                       "hauteur": hauteur},
            "eclairage": _eclairage(cam, centre), "centre": centre, "blocking": blocs, "cles": cles}


def nettoyage() -> dict:
    """Les paramètres de « Retirer de Blender » : la collection DZ_Deepotus et ses objets, rien d'autre."""
    return {"version": 1, "collection": COLLECTION, "elements": ["nettoyer"], "fps": FPS, "camera": None,
            "eclairage": [], "centre": [0.0, 0.0, 0.0], "blocking": [], "cles": []}


# ── vérification puis génération ─────────────────────────────────────────────────────────────────────────────────

def _nombres(v) -> None:
    if isinstance(v, bool):
        raise GabaritRefuse("booléen inattendu")
    if isinstance(v, (int, float)):
        if not math.isfinite(v) or abs(v) > 1e6:
            raise GabaritRefuse("nombre hors bornes")
    elif isinstance(v, list):
        for x in v:
            _nombres(x)
    else:
        raise GabaritRefuse("valeur inattendue")


def _texte(v, prefixe: str = "") -> None:
    if not isinstance(v, str) or not v.startswith(prefixe) or len(v) > MAX_NOM + len("DZ_Blocking_") \
            or nom_sur(v[len(prefixe):] if prefixe else v, "") != (v[len(prefixe):] if prefixe else v):
        raise GabaritRefuse("nom inattendu")


def verifier(p: dict) -> None:
    """Ce qui entre dans le script est re-vérifié ici : version, éléments fermés, nombres finis bornés, noms sûrs."""
    if not isinstance(p, dict) or p.get("version") != 1 or p.get("collection") != COLLECTION:
        raise GabaritRefuse("paramètres illisibles")
    el = p.get("elements")
    if el != ["nettoyer"] and (not isinstance(el, list) or not el or set(el) - set(ELEMENTS)):
        raise GabaritRefuse("éléments inconnus")
    if p.get("fps") != FPS:
        raise GabaritRefuse("cadence inattendue")
    _nombres(p.get("centre"))
    cam = p.get("camera")
    if cam is not None:
        if not isinstance(cam, dict) or cam.get("nom") != "DZ_Camera":
            raise GabaritRefuse("caméra illisible")
        for k in ("pos", "cible", "focale_mm", "capteur_mm", "largeur", "hauteur"):
            _nombres(cam.get(k))
        if not (1 <= cam["focale_mm"] <= 5000 and 16 <= cam["largeur"] <= 8192 and 16 <= cam["hauteur"] <= 8192):
            raise GabaritRefuse("caméra hors bornes")
    elif el != ["nettoyer"]:
        raise GabaritRefuse("caméra absente")
    for l in p.get("eclairage") or []:
        if l.get("nom") not in ("DZ_Cle", "DZ_Debouchage", "DZ_Contre"):
            raise GabaritRefuse("lampe inconnue")
        for k in ("pos", "puissance", "taille"):
            _nombres(l.get(k))
    blocs = p.get("blocking")
    if not isinstance(blocs, list) or len(blocs) > MAX_BLOCKING:
        raise GabaritRefuse("blocking illisible")
    for b in blocs:
        _texte(b.get("nom"), "DZ_Blocking_")
        _texte(b.get("libelle"))
        _texte(b.get("cle"))
        if not _HEX.match(str(b.get("palette") or "")):
            raise GabaritRefuse("couleur illisible")
        _nombres(b.get("monde"))
        _nombres(b.get("couleur"))
        if len(b["monde"]) != 4 or any(len(r) != 4 for r in b["monde"]) or len(b["couleur"]) != 4:
            raise GabaritRefuse("matrice illisible")
    cles = p.get("cles")
    if not isinstance(cles, list) or len(cles) > MAX_CLES:
        raise GabaritRefuse("clés illisibles")
    for c in cles:
        for k in ("image", "pos", "cible", "focale_mm"):
            _nombres(c.get(k))


def generer_script(params: dict) -> str:
    """Le script : le GABARIT fixe, son unique trou rempli par le repr() d'un JSON ASCII vérifié."""
    verifier(params)
    brut = json.dumps(params, ensure_ascii=True, sort_keys=True)
    return GABARIT.replace("__PARAMS__", repr(brut), 1)


def lire_resume(texte: str) -> dict | None:
    """PUR — la ligne « DZBLENDER {json} » imprimée par le script, dans la réponse de execute_blender_code."""
    for ligne in str(texte or "").splitlines():
        i = ligne.find("DZBLENDER ")
        if i >= 0:
            try:
                v = json.loads(ligne[i + len("DZBLENDER "):].strip())
            except ValueError:
                return None
            return v if isinstance(v, dict) else None
    return None


# Le texte n'appelle que bpy et mathutils, sans import dynamique ni nom d'attribut calculé : il passe le validateur
# du mode sûr de mcp-for-blender (BLENDER_MCP_SAFE_MODE=1 ; banc test_blender_pont, section gabarits).
GABARIT = r'''# Script GENERE par DeepotusVideo (t331, pont Scene Blender) : les parametres sont des donnees.
import json
import bpy
import mathutils

P = json.loads(__PARAMS__)
scene = bpy.context.scene
cree = []


def collection():
    col = bpy.data.collections.get(P["collection"])
    if col is None:
        col = bpy.data.collections.new(P["collection"])
        scene.collection.children.link(col)
    return col


def retirer(prefixe):
    col = bpy.data.collections.get(P["collection"])
    if col is None:
        return 0
    n = 0
    for o in list(col.objects):
        if o.name.startswith(prefixe):
            genre = o.type
            donnee = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if donnee is not None and donnee.users == 0:
                if genre == "CAMERA":
                    bpy.data.cameras.remove(donnee)
                elif genre == "LIGHT":
                    bpy.data.lights.remove(donnee)
            n += 1
    return n


def viser(objet, pos, cible):
    a = mathutils.Vector(pos)
    b = mathutils.Vector(cible)
    objet.location = a
    objet.rotation_euler = (b - a).to_track_quat("-Z", "Y").to_euler()


def poser_camera():
    c = P["camera"]
    cam = bpy.data.objects.get(c["nom"])
    if cam is None or cam.type != "CAMERA":
        donnee = bpy.data.cameras.new(c["nom"])
        cam = bpy.data.objects.new(c["nom"], donnee)
        collection().objects.link(cam)
        cree.append(cam.name)
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = c["capteur_mm"]
    cam.data.lens = c["focale_mm"]
    viser(cam, c["pos"], c["cible"])
    scene.camera = cam
    scene.render.resolution_x = int(c["largeur"])
    scene.render.resolution_y = int(c["hauteur"])
    return cam


def poser_eclairage():
    retirer("DZ_Cle")
    retirer("DZ_Debouchage")
    retirer("DZ_Contre")
    for l in P["eclairage"]:
        donnee = bpy.data.lights.new(l["nom"], type="AREA")
        donnee.energy = l["puissance"]
        donnee.size = l["taille"]
        lampe = bpy.data.objects.new(l["nom"], donnee)
        collection().objects.link(lampe)
        viser(lampe, l["pos"], P["centre"])
        cree.append(lampe.name)


def poser_blocking():
    retirer("DZ_Blocking_")
    for b in P["blocking"]:
        vide = bpy.data.objects.new(b["nom"], None)
        vide.empty_display_type = "CUBE"
        vide.empty_display_size = 1.0
        vide.matrix_world = mathutils.Matrix(b["monde"])
        vide.color = b["couleur"]
        vide["dz_cle"] = b["cle"]
        vide["dz_libelle"] = b["libelle"]
        vide["dz_palette"] = b["palette"]
        collection().objects.link(vide)
        cree.append(vide.name)


def poser_cles(cam):
    if cam.animation_data is not None:
        cam.animation_data_clear()
    if cam.data.animation_data is not None:
        cam.data.animation_data_clear()
    scene.render.fps = P["fps"]
    for c in P["cles"]:
        viser(cam, c["pos"], c["cible"])
        cam.data.lens = c["focale_mm"]
        cam.keyframe_insert(data_path="location", frame=c["image"])
        cam.keyframe_insert(data_path="rotation_euler", frame=c["image"])
        cam.data.keyframe_insert(data_path="lens", frame=c["image"])
    scene.frame_start = P["cles"][0]["image"]
    scene.frame_end = P["cles"][-1]["image"]
    scene.frame_set(scene.frame_start)


if P["elements"] == ["nettoyer"]:
    n = retirer("DZ_")
    col = bpy.data.collections.get(P["collection"])
    if col is not None and len(col.objects) == 0:
        bpy.data.collections.remove(col)
    print("DZBLENDER " + json.dumps({"retires": n}))
else:
    cam = None
    if "camera" in P["elements"] or "cles" in P["elements"]:
        cam = poser_camera()
    if "eclairage" in P["elements"]:
        poser_eclairage()
    if "blocking" in P["elements"]:
        poser_blocking()
    if "cles" in P["elements"]:
        poser_cles(cam)
    print("DZBLENDER " + json.dumps({"elements": P["elements"], "crees": cree, "blocking": len(P["blocking"])}))
'''
