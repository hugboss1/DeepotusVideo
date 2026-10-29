# -*- coding: utf-8 -*-
"""t334 (A4 du lot Scenario, 29/10/2026) — les PASSES HEADLESS d'un plan : Blender en arrière-plan (`blender -b`) rend,
avec la caméra du plan reproduite depuis sa scène du Plateau 3D, cinq versions du même cadre :

  * clay        Workbench, éclairage studio, une seule couleur d'argile : la lecture des volumes ;
  * look        EEVEE, matières de la palette de la previs, un soleil : le cadre « éclairé » ;
  * profondeur  distance à la caméra NORMALISÉE (blanc = proche, noir = loin ou fond), PNG 16 bits en niveaux de gris,
                la plage [proche, loin] est rendue au manifeste ;
  * normales    normales en ESPACE CAMÉRA (R = droite, V = haut, B = vers la caméra ; convention OpenGL) ;
  * masques     une couleur PLATE par objet (Workbench « flat », sans anticrénelage) : la palette par entité de la
                previs colorée (t333, `previs_palette`) quand elle est là, sinon une couleur stable par nom.

Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A4 (« 4 versions par cut »).

LE SCRIPT EST GÉNÉRÉ ICI, JAMAIS REÇU. Le gabarit `GABARIT` est FIXE ; un seul trou, `__PARAMS__`, reçoit le repr()
d'un JSON (ASCII) bâti par `parametres` à partir de nombres VÉRIFIÉS (scene3d), d'énumérations fermées et de chemins
calculés par le serveur. Aucune chaîne venue de la page n'entre dans du code : les noms d'instances ne vivent que dans
ce JSON, relu par json.loads côté Blender (banc test_passes_blender : l'arbre syntaxique du script est celui du
gabarit, quelle que soit l'instance).

Blender est trouvé par `BLENDER_PATH` (le .env, comme mesh_export.ouvrir), sinon dans
« C:\\Program Files\\Blender Foundation\\Blender X.Y\\ » (la plus récente), sinon dans le PATH ; 4.2 au moins (EEVEE
Next, transformée « Raw »). Absent : `etat_blender()` le dit et la route répond 503 avec quoi installer.

Repère : le Plateau est en Y-haut (glTF), Blender en Z-haut ; l'importeur glTF convertit (x, y, z) → (x, −z, y) et
`vers_blender` fait la même chose pour la caméra, calculée ici (position, cible, champ VERTICAL) — Blender ne fait que
la poser. Une caméra animée (au moins deux keyframes) donne, sur demande, une SÉQUENCE courte BORNÉE (12 i/s,
48 images au plus, sur 640 px) ; sinon une image fixe au premier keyframe (le « début » du plan, comme la capture du
Plateau) sur 960 px.

Le suivi : le script écrit « DZPASSE image k n passe i » à chaque image ; `lire_ligne` le lit. L'annulation tue le
processus. Le résultat vit dans outputs/passes/<plan>/<run>/ avec son manifeste `passes.json`.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import zlib
from datetime import datetime
from pathlib import Path

from app.services import scene3d as S

PASSES = ("clay", "look", "profondeur", "normales", "masques")
VERSION_MIN = (4, 2)
COTE_FIXE = 960
COTE_SEQUENCE = 640
SEQ_FPS = 12
SEQ_MAX_IMAGES = 48
DELAI_S = 900.0
RUNS_GARDES = 5
DOSSIER_PF = Path(r"C:\Program Files\Blender Foundation")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_RUN = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{4}$")
_NOM_FICHIER = re.compile(r"^(clay|look|profondeur|normales|masques)(_\d{3}\.png|\.mp4)$")
_VERSION = re.compile(r"Blender\s+(\d+)\.(\d+)(?:\.(\d+))?")
# Couleurs stables quand la palette t333 n'est pas là : douze teintes franches, aucune noire (le noir = le fond)
_STABLES = ("#2fb344", "#c92a2a", "#1c7ed6", "#fcc419", "#f76707", "#9c36b5", "#22d3ee", "#f783ac", "#6f4518",
            "#f1f3f5", "#5c940d", "#364fc7")
GRIS_ARGILE = (0.72, 0.72, 0.70)


class BlenderAbsent(RuntimeError):
    """Aucun Blender utilisable (introuvable ou trop ancien) : la route en fait un 503 qui dit quoi installer."""


class PasseRefusee(ValueError):
    """Une demande ou une scène inutilisable (400/409 côté route)."""


# ─────────────────────────────── trouver Blender ───────────────────────────────

def _racines() -> list[Path]:          # couture : remplacée au banc
    """Les exécutables candidats, dans l'ordre : BLENDER_PATH, puis Program Files (plus récent d'abord), puis PATH."""
    out = []
    env = os.environ.get("BLENDER_PATH", "").strip().strip('"')
    if env:
        out.append(Path(env))
    if DOSSIER_PF.is_dir():
        def cle(d: Path):
            m = re.search(r"(\d+)\.(\d+)", d.name)
            return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        for d in sorted((x for x in DOSSIER_PF.iterdir() if x.is_dir()), key=cle, reverse=True):
            out.append(d / "blender.exe")
    w = shutil.which("blender")
    if w:
        out.append(Path(w))
    return out


def _sortie_version(exe: Path) -> str:  # couture : remplacée au banc
    r = subprocess.run([str(exe), "-b", "--factory-startup", "--version"], capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "replace")


def lire_version(texte: str) -> tuple | None:
    """PUR — « Blender 5.2.2 LTS » → (5, 2, 2) ; None si illisible."""
    m = _VERSION.search(str(texte or ""))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)) if m else None


_CACHE: dict = {}


def etat_blender(rafraichir: bool = False) -> dict:
    """{dispo, exe, version, source, raison}. Le premier candidat qui existe ET dit une version ≥ 4.2 l'emporte ;
    le résultat est gardé tant que l'exécutable ne change pas (sa date)."""
    trop_vieux = None
    for exe in _racines():
        try:
            if not exe.is_file():
                continue
            cle = (str(exe), exe.stat().st_mtime)
        except OSError:
            continue
        if not rafraichir and cle in _CACHE:
            v = _CACHE[cle]
        else:
            try:
                v = lire_version(_sortie_version(exe))
            except (OSError, subprocess.SubprocessError):
                v = None
            _CACHE[cle] = v
        if v is None:
            continue
        if tuple(v[:2]) < VERSION_MIN:
            trop_vieux = trop_vieux or (exe, v)
            continue
        return {"dispo": True, "exe": str(exe), "version": ".".join(str(x) for x in v), "raison": None}
    if trop_vieux:
        return {"dispo": False, "exe": str(trop_vieux[0]), "version": ".".join(str(x) for x in trop_vieux[1]),
                "raison": "trop_ancien"}
    return {"dispo": False, "exe": None, "version": None, "raison": "absent"}


# ─────────────────────────────── géométrie (PUR) ───────────────────────────────

def resolution(aspect: str, cote: int) -> tuple[int, int]:
    """Le grand côté vaut `cote`, l'autre suit le format ; deux nombres pairs (l'encodage vidéo les exige)."""
    r = S.ASPECTS.get(aspect)
    if r is None:
        raise PasseRefusee(f"format inconnu ({aspect})")
    w, h = (cote, cote / r) if r >= 1 else (cote * r, cote)
    return int(round(w / 2)) * 2, int(round(h / 2)) * 2


def vers_blender(p) -> list:
    """glTF (Y en haut) → Blender (Z en haut) : (x, y, z) → (x, −z, y), comme l'importeur glTF de Blender."""
    x, y, z = (float(v) for v in p)
    return [x, -z, y]


def etats_camera(scene: dict, sequence: bool) -> list[dict]:
    """Les états de caméra à rendre : {t, orbit, target, fov}. Image fixe = le premier keyframe (sinon la caméra de la
    scène) ; séquence (seulement si au moins deux keyframes) = 12 i/s du premier au dernier, 48 images au plus."""
    kfs = scene.get("keyframes") or []
    if kfs:
        kfs = S.valider_keyframes(kfs)
    if sequence and len(kfs) >= 2:
        t0, t1 = kfs[0]["t"], kfs[-1]["t"]
        n = min(SEQ_MAX_IMAGES, int(math.floor((t1 - t0) * SEQ_FPS)) + 1)
        n = max(2, n)
        pas = (t1 - t0) / (n - 1)
        return [{"t": round(t0 + i * pas, 4), **S.interpoler(kfs, t0 + i * pas)} for i in range(n)]
    if kfs:
        k = kfs[0]
        return [{"t": k["t"], "orbit": list(k["orbit"]), "target": list(k["target"]), "fov": k["fov"]}]
    cam = scene.get("camera")
    if not isinstance(cam, dict):
        raise PasseRefusee("la scène n'a ni caméra ni keyframe")
    return [{"t": 0.0, "orbit": S._vec(cam.get("orbit"), "orbit"), "target": S._vec(cam.get("target"), "target"),
             "fov": S._num(cam.get("fov"), "fov", 0, strict=True)}]


def cadrage_blender(etat: dict) -> dict:
    """{pos, cible, fov_v} en coordonnées Blender, la position calculée par scene3d (même orbite que le Plateau)."""
    pos = S.position_camera(etat["orbit"], etat["target"])
    fov = S._num(etat["fov"], "fov", 0, strict=True)
    if fov >= 179:
        raise PasseRefusee("champ de caméra hors bornes")
    return {"pos": [round(v, 6) for v in vers_blender(pos)],
            "cible": [round(v, 6) for v in vers_blender(etat["target"])], "fov_v": round(fov, 6)}


def plage_profondeur(instances: list, etats: list, aspect: str) -> tuple[float, float]:
    """[proche, loin] en mètres le long de l'axe de visée : les coins des boîtes d'instances devant la caméra, sur
    TOUS les états (une séquence garde une seule échelle). Le sol au-delà de `loin` sort noir, comme le fond."""
    asp = S.ASPECTS.get(aspect, 16 / 9)
    zs = []
    for inst in instances:
        if not inst.get("dims"):
            continue
        cs = S.coins(inst)
        for e in etats:
            zs += [p[2] for p in S.projeter(cs, e, asp) if p[2] > 1e-6]
    if not zs:
        return 0.1, 100.0
    proche, loin = max(0.01, min(zs) * 0.9), max(zs) * 1.5
    if loin - proche < 0.05:
        loin = proche + 0.05
    return round(proche, 5), round(loin, 5)


def sol(instances: list) -> dict:
    """Un sol carré sous la scène (centre et côté en mètres, coordonnées Blender) : quatre fois l'emprise, 10 m au
    moins — il donne une ombre au clay et au look et un plancher à la profondeur ; les masques le laissent noir."""
    xs, zs = [], []
    for inst in instances:
        if inst.get("dims"):
            for p in S.coins(inst):
                xs.append(p[0])
                zs.append(p[2])
    if not xs:
        return {"centre": [0.0, 0.0], "cote": 10.0}
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    cote = max(10.0, 4 * max(max(xs) - min(xs), max(zs) - min(zs)))
    return {"centre": [round(cx, 5), round(-cz, 5)], "cote": round(cote, 4)}


def _hex_stable(nom: str) -> str:
    return _STABLES[zlib.crc32(str(nom).encode("utf-8")) % len(_STABLES)]


def couleurs(instances: list) -> tuple[dict, str, list]:
    """({id: hex}, origine, exclus). La palette de la previs colorée (t333 : par entité de la bible, sinon par
    matière) quand le module est là ; sinon une couleur stable par nom (crc32, jamais hash() salé). `exclus` = les
    faisceaux de lumière (jamais un solide)."""
    try:
        from app.services import previs_palette as PP          # t333 : peut ne pas être encore fusionné
    except ImportError:
        PP = None
    if PP is not None:
        try:
            pal = PP.palette(instances)
            exclus = list((pal.get("blender") or {}).get("exclus") or [])
            out = {}
            for i in instances:
                iid = i.get("id")
                if iid in exclus:
                    continue
                c = (pal.get("couleurs") or {}).get(iid) or getattr(PP, "GRIS_REPERE", "#8a8f98")
                out[iid] = c if _HEX.match(str(c)) else _hex_stable(iid)
            return out, "palette", exclus
        except Exception:                                      # palette illisible : on retombe sur le stable
            pass
    exclus = [i.get("id") for i in instances if i.get("role") == "faisceau"]
    return ({i.get("id"): _hex_stable(i.get("nom") or i.get("id")) for i in instances if i.get("id") not in exclus},
            "stable", exclus)


def hex_rgb(h: str) -> list:
    """« #rrggbb » → [r, g, b] en 0-1, SANS conversion : en transformée « Raw », c'est la valeur écrite au PNG."""
    if not _HEX.match(str(h)):
        raise PasseRefusee(f"couleur illisible ({h})")
    return [round(int(h[i:i + 2], 16) / 255, 6) for i in (1, 3, 5)]


def lineaire(h: str) -> list:
    """« #rrggbb » sRVB → linéaire (la base color d'une matière Blender est linéaire)."""
    return [round(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4, 6) for c in hex_rgb(h)]


# ─────────────────────────────── le script (gabarit fixe) ───────────────────────────────

def parametres(scene: dict, *, glb: str, sortie: str, sequence: bool = False, passes=None) -> dict:
    """PUR — le JSON du script, bâti à partir de la scène VÉRIFIÉE (instances, keyframes) et de chemins du serveur.
    `passes` : sous-ensemble ordonné de PASSES (toutes par défaut)."""
    if passes is not None and (not isinstance(passes, (list, tuple)) or not all(isinstance(x, str) for x in passes)
                               or set(passes) - set(PASSES) or not passes):
        raise PasseRefusee(f"passes : {', '.join(PASSES)}")
    voulues = list(PASSES) if passes is None else [p for p in PASSES if p in set(passes)]
    aspect = scene.get("aspect", "16:9")
    instances = [i for i in (scene.get("instances") or []) if isinstance(i, dict)]
    cols, origine, exclus = couleurs(instances)
    solides = [i for i in instances if i.get("id") not in exclus]
    if not solides:
        raise PasseRefusee("scène vide : aucune forme à rendre")
    etats = etats_camera(scene, bool(sequence))
    w, h = resolution(aspect, COTE_SEQUENCE if len(etats) > 1 else COTE_FIXE)
    proche, loin = plage_profondeur(solides, etats, aspect)
    return {"version": 1, "glb": str(Path(glb)), "sortie": str(Path(sortie)), "passes": voulues,
            "largeur": w, "hauteur": h, "cameras": [cadrage_blender(e) for e in etats],
            "temps": [e["t"] for e in etats], "fps": SEQ_FPS if len(etats) > 1 else None,
            "proche": proche, "loin": loin, "clip_fin": round(max(loin * 4, 50.0), 3), "sol": sol(solides),
            "masques": {str(k): hex_rgb(v) for k, v in cols.items()},
            "look": {str(k): lineaire(v) for k, v in cols.items()},
            "couleurs": dict(cols), "palette": origine, "exclus": [str(x) for x in exclus],
            "argile": list(GRIS_ARGILE)}


def _verifier(p: dict) -> None:
    """Ce qui entre dans le script est re-vérifié ici : nombres finis, passes fermées, chemins absolus."""
    if not isinstance(p, dict) or p.get("version") != 1:
        raise PasseRefusee("paramètres illisibles")
    if not p.get("passes") or set(p["passes"]) - set(PASSES):
        raise PasseRefusee("passes inconnues")
    for k in ("glb", "sortie"):
        if not isinstance(p.get(k), str) or not Path(p[k]).is_absolute():
            raise PasseRefusee(f"{k} : un chemin absolu du serveur")

    def nombres(v):
        if isinstance(v, bool):
            raise PasseRefusee("booléen inattendu")
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise PasseRefusee("nombre non fini")
        elif isinstance(v, list):
            for x in v:
                nombres(x)
        elif isinstance(v, dict):
            for x in v.values():
                nombres(x)
        elif v is not None:
            raise PasseRefusee("valeur inattendue")
    for k in ("largeur", "hauteur", "cameras", "temps", "proche", "loin", "clip_fin", "sol", "masques", "look",
              "argile"):
        nombres(p.get(k))
    if not (16 <= p["largeur"] <= 4096 and 16 <= p["hauteur"] <= 4096):
        raise PasseRefusee("résolution hors bornes")
    if not 1 <= len(p["cameras"]) <= SEQ_MAX_IMAGES:
        raise PasseRefusee("trop d'images")


def generer_script(params: dict) -> str:
    """Le script Blender : le GABARIT fixe, son unique trou rempli par le repr() d'un JSON ASCII vérifié."""
    _verifier(params)
    brut = json.dumps(params, ensure_ascii=True, sort_keys=True)
    return GABARIT.replace("__PARAMS__", repr(brut), 1)


def argv(exe: str, script: Path) -> list[str]:
    """La ligne de commande : arrière-plan, réglages d'usine (aucun add-on ni préférence de l'utilisateur), sans son,
    et un code de sortie non nul si le script lève."""
    return [str(exe), "-b", "--factory-startup", "-noaudio", "--python-exit-code", "3", "--python", str(script)]


def lire_ligne(ligne: str) -> dict | None:
    """PUR — une ligne de la sortie de Blender : {type: image, k, n, passe, i} | {type: fin} | {type: erreur, msg}
    | None (tout le reste : le bavardage de Blender)."""
    s = str(ligne or "").strip()
    if not s.startswith("DZPASSE "):
        return None
    morceaux = s.split(" ", 2)
    if len(morceaux) < 2:
        return None
    if morceaux[1] == "fin":
        return {"type": "fin"}
    if morceaux[1] == "erreur":
        return {"type": "erreur", "msg": (morceaux[2] if len(morceaux) > 2 else "")[:300]}
    if morceaux[1] == "image" and len(morceaux) == 3:
        t = morceaux[2].split()
        if len(t) == 4 and t[2] in PASSES:
            try:
                k, n, i = int(t[0]), int(t[1]), int(t[3])
            except ValueError:
                return None
            if 0 < k <= n and i >= 0:
                return {"type": "image", "k": k, "n": n, "passe": t[2], "i": i}
    return None


GABARIT = r'''# Script GÉNÉRÉ par DeepotusVideo (t334, passes headless) — ne pas modifier : les paramètres sont des données.
import json
import math
import os
import sys

import bpy
from mathutils import Vector

P = json.loads(__PARAMS__)


def dire(*morceaux):
    print("DZPASSE", *morceaux, flush=True)


def essayer(fonction):
    try:
        fonction()
    except Exception:
        pass


def poser(objet, attribut, valeurs):
    """Pose la première valeur que cette version de Blender accepte (les énumérations changent d'une version à l'autre)."""
    for v in valeurs:
        try:
            setattr(objet, attribut, v)
            return v
        except (TypeError, ValueError, AttributeError):
            continue
    return None


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=P["glb"])
objets = [o for o in sc.objects if o.type == "MESH"]


def cle_objet(o):
    nom = o.name
    if nom not in P["masques"] and "." in nom and nom.rsplit(".", 1)[1].isdigit():
        nom = nom.rsplit(".", 1)[0]
    return nom


bpy.ops.mesh.primitive_plane_add(size=P["sol"]["cote"], location=(P["sol"]["centre"][0], P["sol"]["centre"][1], 0.0))
sol = bpy.context.active_object
sol.name = "dz_sol"

donnees_camera = bpy.data.cameras.new("dz_camera")
camera = bpy.data.objects.new("dz_camera", donnees_camera)
sc.collection.objects.link(camera)
sc.camera = camera
donnees_camera.sensor_fit = "VERTICAL"
donnees_camera.clip_start = 0.01
donnees_camera.clip_end = P["clip_fin"]
camera.rotation_mode = "QUATERNION"

monde = bpy.data.worlds.new("dz_monde")
sc.world = monde
monde.use_nodes = True
fond = monde.node_tree.nodes.get("Background")

rendu = sc.render
rendu.resolution_x = P["largeur"]
rendu.resolution_y = P["hauteur"]
rendu.resolution_percentage = 100
rendu.film_transparent = False
essayer(lambda: setattr(rendu, "dither_intensity", 0.0))
rendu.image_settings.file_format = "PNG"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.0
sc.view_settings.gamma = 1.0


def poser_camera(e):
    camera.location = Vector(e["pos"])
    camera.rotation_quaternion = (Vector(e["cible"]) - camera.location).to_track_quat("-Z", "Y")
    donnees_camera.angle_y = math.radians(e["fov_v"])


def eevee(echantillons):
    poser(rendu, "engine", ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"))
    essayer(lambda: setattr(sc.eevee, "taa_render_samples", echantillons))
    essayer(lambda: setattr(rendu, "filter_size", 0.0 if echantillons == 1 else 1.5))


def materiau(nom, construire):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    arbre = m.node_tree
    for n in list(arbre.nodes):
        arbre.nodes.remove(n)
    sortie = arbre.nodes.new("ShaderNodeOutputMaterial")
    arbre.links.new(construire(arbre), sortie.inputs["Surface"])
    return m


def emission(arbre, prise):
    e = arbre.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = 1.0
    arbre.links.new(prise, e.inputs["Color"])
    return e.outputs["Emission"]


def habiller(choix):
    for o in objets + [sol]:
        m = choix(o)
        o.data.materials.clear()
        if m is not None:
            o.data.materials.append(m)


def fond_couleur(rvb, force=1.0):
    monde.color = rvb
    if fond is not None:
        fond.inputs["Color"].default_value = (rvb[0], rvb[1], rvb[2], 1.0)
        fond.inputs["Strength"].default_value = force


def preparer_clay():
    rendu.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = P["argile"]
    essayer(lambda: setattr(sh, "show_shadows", True))
    essayer(lambda: setattr(sh, "show_cavity", True))
    poser(sc.display, "render_aa", ("8", "5", "FXAA"))
    fond_couleur((0.06, 0.06, 0.07))
    sc.view_settings.view_transform = "Standard"
    rendu.image_settings.color_mode = "RGB"
    rendu.image_settings.color_depth = "8"


def preparer_look():
    eevee(16)
    soleil = bpy.data.objects.get("dz_soleil")
    if soleil is None:
        lumiere = bpy.data.lights.new("dz_soleil", "SUN")
        lumiere.energy = 3.0
        soleil = bpy.data.objects.new("dz_soleil", lumiere)
        sc.collection.objects.link(soleil)
        soleil.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    mats = {}

    def choix(o):
        c = P["look"].get(cle_objet(o)) if o is not sol else [0.18, 0.18, 0.18]
        c = c or [0.5, 0.5, 0.5]
        cle = tuple(c)
        if cle not in mats:
            def construire(arbre, c=c):
                b = arbre.nodes.new("ShaderNodeBsdfPrincipled")
                b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
                b.inputs["Roughness"].default_value = 0.6
                return b.outputs["BSDF"]
            mats[cle] = materiau("dz_look", construire)
        return mats[cle]
    habiller(choix)
    fond_couleur((0.35, 0.38, 0.42), 0.8)
    sc.view_settings.view_transform = "Standard"
    rendu.image_settings.color_mode = "RGB"
    rendu.image_settings.color_depth = "8"


def preparer_profondeur():
    eevee(1)

    def construire(arbre):
        cam = arbre.nodes.new("ShaderNodeCameraData")
        carte = arbre.nodes.new("ShaderNodeMapRange")
        carte.clamp = True
        carte.inputs["From Min"].default_value = P["proche"]
        carte.inputs["From Max"].default_value = P["loin"]
        carte.inputs["To Min"].default_value = 1.0
        carte.inputs["To Max"].default_value = 0.0
        arbre.links.new(cam.outputs["View Z Depth"], carte.inputs["Value"])
        return emission(arbre, carte.outputs["Result"])
    m = materiau("dz_profondeur", construire)
    habiller(lambda o: m)
    fond_couleur((0.0, 0.0, 0.0), 0.0)
    sc.view_settings.view_transform = "Raw"
    rendu.image_settings.color_mode = "BW"
    rendu.image_settings.color_depth = "16"


def preparer_normales():
    eevee(1)

    def construire(arbre):
        geo = arbre.nodes.new("ShaderNodeNewGeometry")
        vt = arbre.nodes.new("ShaderNodeVectorTransform")
        vt.vector_type = "NORMAL"
        vt.convert_from = "WORLD"
        vt.convert_to = "CAMERA"
        ma = arbre.nodes.new("ShaderNodeVectorMath")
        ma.operation = "MULTIPLY_ADD"
        ma.inputs[1].default_value = (0.5, 0.5, -0.5)     # l'espace caméra des shaders regarde vers +Z : on retourne Z
        ma.inputs[2].default_value = (0.5, 0.5, 0.5)
        arbre.links.new(geo.outputs["Normal"], vt.inputs["Vector"])
        arbre.links.new(vt.outputs["Vector"], ma.inputs[0])
        return emission(arbre, ma.outputs["Vector"])
    m = materiau("dz_normales", construire)
    habiller(lambda o: m)
    fond_couleur((0.0, 0.0, 0.0), 0.0)
    sc.view_settings.view_transform = "Raw"
    rendu.image_settings.color_mode = "RGB"
    rendu.image_settings.color_depth = "16"


def preparer_masques():
    rendu.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "OBJECT"
    essayer(lambda: setattr(sh, "show_shadows", False))
    essayer(lambda: setattr(sh, "show_cavity", False))
    essayer(lambda: setattr(sh, "show_object_outline", False))
    essayer(lambda: setattr(sh, "show_specular_highlight", False))
    poser(sc.display, "render_aa", ("OFF",))
    for o in objets:
        c = P["masques"].get(cle_objet(o))
        o.color = (c[0], c[1], c[2], 1.0) if c else (0.0, 0.0, 0.0, 1.0)
    sol.color = (0.0, 0.0, 0.0, 1.0)
    fond_couleur((0.0, 0.0, 0.0), 0.0)
    sc.view_settings.view_transform = "Raw"
    rendu.image_settings.color_mode = "RGB"
    rendu.image_settings.color_depth = "8"


PREPARER = {"clay": preparer_clay, "look": preparer_look, "profondeur": preparer_profondeur,
            "normales": preparer_normales, "masques": preparer_masques}

try:
    total = len(P["passes"]) * len(P["cameras"])
    k = 0
    for passe in P["passes"]:
        PREPARER[passe]()
        for i, e in enumerate(P["cameras"]):
            poser_camera(e)
            rendu.filepath = os.path.join(P["sortie"], "%s_%03d.png" % (passe, i))
            bpy.ops.render.render(write_still=True)
            k += 1
            dire("image", k, total, passe, i)
    dire("fin")
except Exception as exc:
    dire("erreur", str(exc).replace("\n", " ")[:300])
    raise
'''


# ─────────────────────────────── l'exécution (job) ───────────────────────────────

_JOBS: dict[str, dict] = {}
_VERROU = threading.Lock()


def job_public(j: dict) -> dict:
    return {k: j.get(k) for k in ("id", "shot_id", "run", "statut", "progression", "etape", "images", "total",
                                  "erreur", "debut", "fin", "sequence")}


def job(jid: str) -> dict | None:
    return _JOBS.get(jid)


def job_actif(shot_id: str | None = None) -> dict | None:
    for j in _JOBS.values():
        if j["statut"] in ("attente", "rendu") and (shot_id is None or j["shot_id"] == shot_id):
            return j
    return None


def nouveau_job(shot_id: str, run: str, sequence: bool, total: int) -> dict:
    with _VERROU:
        if job_actif() is not None:
            raise PasseRefusee("une passe Blender tourne déjà")
        jid = f"pb_{run}"
        j = {"id": jid, "shot_id": shot_id, "run": run, "statut": "attente", "progression": 0, "etape": None,
             "images": 0, "total": total, "erreur": None, "debut": time.time(), "fin": None, "sequence": sequence,
             "annule": False, "proc": None}
        _JOBS[jid] = j
        # on ne garde que les 20 derniers jobs finis en mémoire
        finis = [k for k, v in _JOBS.items() if v["statut"] not in ("attente", "rendu")]
        for k in finis[:-20]:
            _JOBS.pop(k, None)
        return j


def annuler(jid: str) -> bool:
    j = _JOBS.get(jid)
    if j is None or j["statut"] not in ("attente", "rendu"):
        return False
    j["annule"] = True
    p = j.get("proc")
    if p is not None:
        try:
            p.kill()
        except OSError:
            pass
    return True


def _popen(args: list[str], cwd: Path):            # couture : remplacée au banc (faux Blender)
    drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=drapeaux)


def executer(j: dict, exe: str, script: Path, dossier: Path) -> bool:
    """Lance Blender, lit sa sortie ligne à ligne (progression), le tue au délai ou à l'annulation. Bloquant : à
    appeler hors de la boucle (asyncio.to_thread). True : Blender a tout rendu — le job reste « rendu », étape
    « rangement », et c'est l'appelant qui le dit « fini » une fois les images rangées (aucun « fini » prématuré
    qu'un suivi lirait avant la Bibliothèque). False : le job finit « annule » ou « erreur » (message court)."""
    if j["annule"]:
        j.update(statut="annule", fin=time.time())
        return False
    j["statut"] = "rendu"
    queue = []
    try:
        p = _popen(argv(exe, script), dossier)
    except OSError as e:
        j.update(statut="erreur", erreur=f"lancement de Blender impossible : {e}"[:300], fin=time.time())
        return False
    j["proc"] = p
    minuterie = threading.Timer(DELAI_S, lambda: (j.update(delai=True), p.kill()))
    minuterie.daemon = True
    minuterie.start()
    vu_fin, err = False, None
    try:
        for brut in iter(p.stdout.readline, b""):
            ligne = brut.decode("utf-8", "replace")
            queue = (queue + [ligne.rstrip()])[-12:]
            ev = lire_ligne(ligne)
            if ev is None:
                continue
            if ev["type"] == "image":
                j.update(images=ev["k"], total=ev["n"], etape=ev["passe"],
                         progression=int(round(100 * ev["k"] / ev["n"])))
            elif ev["type"] == "fin":
                vu_fin = True
            elif ev["type"] == "erreur":
                err = ev["msg"]
        p.wait(timeout=30)
    finally:
        minuterie.cancel()
        j["proc"] = None
    if j["annule"]:
        j.update(statut="annule", fin=time.time())
    elif j.get("delai"):
        j.update(statut="erreur", erreur=f"Blender a dépassé {int(DELAI_S)} s", fin=time.time())
    elif p.returncode != 0 or not vu_fin:
        dernier = err or next((x for x in reversed(queue) if x.strip()), "")
        j.update(statut="erreur", erreur=f"Blender a échoué (code {p.returncode}) : {dernier}"[:300], fin=time.time())
    else:
        j.update(etape="rangement", progression=99)
        return True
    return False


# ─────────────────────────────── résultats sur disque ───────────────────────────────

def dossier_plan(racine: Path, shot_id: str) -> Path:
    return Path(racine) / "passes" / Path(str(shot_id)).name


_DERNIER_RUN = [""]


def nouveau_run() -> str:
    """« AAAAMMJJ-HHMMSS-mmmm » (mmmm = millisecondes en hexadécimal) : l'ordre des noms est celui des lancements,
    strictement croissant même deux fois dans la même milliseconde."""
    with _VERROU:
        n = datetime.now()
        base, ms = n.strftime("%Y%m%d-%H%M%S"), n.microsecond // 1000
        run = f"{base}-{ms:04x}"
        while run <= _DERNIER_RUN[0]:
            ms += 1
            run = f"{base}-{ms:04x}" if ms < 0x10000 else _DERNIER_RUN[0][:-4] + f"{int(_DERNIER_RUN[0][-4:], 16) + 1:04x}"
        _DERNIER_RUN[0] = run
        return run


def run_valide(run: str) -> bool:
    return bool(_RUN.match(str(run or "")))


def fichier_valide(nom: str) -> bool:
    return bool(_NOM_FICHIER.match(str(nom or "")))


def inventaire(dossier: Path, passes: list, n: int) -> dict:
    """{passe: [fichiers]} des images réellement écrites ; une passe incomplète est une erreur nommée."""
    out = {}
    for p in passes:
        fichiers = [f"{p}_{i:03d}.png" for i in range(n)]
        manquants = [f for f in fichiers if not (dossier / f).is_file()]
        if manquants:
            raise PasseRefusee(f"{p} : {len(manquants)} image(s) manquante(s)")
        out[p] = fichiers
    return out


def video_sequence(dossier: Path, passe: str, fps: int) -> str | None:
    """Une séquence → un MP4 d'aperçu (H.264, 8 bits : la profondeur 16 bits reste dans ses PNG). None si ffmpeg
    échoue — les PNG suffisent."""
    sortie = dossier / f"{passe}.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(int(fps)), "-i", str(dossier / f"{passe}_%03d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(sortie)],
                       capture_output=True, timeout=300)
    return sortie.name if r.returncode == 0 and sortie.is_file() else None


def ecrire_manifeste(dossier: Path, manifeste: dict) -> None:
    (dossier / "passes.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_runs(dossier_du_plan: Path, n: int = RUNS_GARDES) -> list[dict]:
    """Les manifestes des runs FINIS du plan, du plus récent au plus ancien."""
    if not dossier_du_plan.is_dir():
        return []
    out = []
    for d in sorted((x for x in dossier_du_plan.iterdir() if x.is_dir() and run_valide(x.name)), reverse=True):
        f = d / "passes.json"
        if f.is_file():
            try:
                out.append(json.loads(f.read_text("utf-8")))
            except ValueError:
                continue
        if len(out) >= n:
            break
    return out


def purger(dossier_du_plan: Path, garder: int = RUNS_GARDES) -> None:
    """Garde les `garder` derniers runs du plan (les images rangées dans la Bibliothèque restent)."""
    if not dossier_du_plan.is_dir():
        return
    runs = sorted((x for x in dossier_du_plan.iterdir() if x.is_dir() and run_valide(x.name)), reverse=True)
    for d in runs[garder:]:
        shutil.rmtree(d, ignore_errors=True)


def profondeur_du_plan(racine: Path, shot_id: str) -> dict | None:
    """t337 : la passe de PROFONDEUR la plus récente du plan ({chemin, run, proche_m, loin_m, t}) — la revue du plan
    la compare au rendu (`revue_plan.mesurer(profondeur=…)`). None : aucune passe de profondeur."""
    d = dossier_plan(racine, shot_id)
    for m in lire_runs(d, 50):
        f = ((m.get("passes") or {}).get("profondeur") or {}).get("fichiers") or []
        if f and (d / m["run"] / f[0]).is_file():
            prof = m.get("profondeur") or {}
            return {"chemin": str(d / m["run"] / f[0]), "run": m["run"], "proche_m": prof.get("proche_m"),
                    "loin_m": prof.get("loin_m"), "t": (m.get("temps") or [None])[0]}
    return None
