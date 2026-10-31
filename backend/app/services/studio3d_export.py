# -*- coding: utf-8 -*-
"""t400 (31/10/2026) — l'écran EXPORTER du 3D Studio : ce qui sort de la version ouverte, en local et sans dépense.

Relevé de Sorceress (inventaire §7, panneau « Export » d'Animate) : FILE NAME, une collection de clips, puis GAME
ENGINE (Unreal · Unity · Blender) avec trois GLB — « Skeletal Mesh Only », « Pose », « Animation » — et WEB / THREE.JS
avec un paquet .zip (personnage, clip, manifeste, runtime, AGENT_INSTRUCTIONS.md) et le clip seul en .clip.json.

Chez nous, ce module écrit :

* trois VARIANTES du GLB de la version ouverte, en réécrivant le seul chunk JSON (`mesh_edit.lire_glb/ecrire_glb`) :
    - `maillage`  : le maillage et sa PEAU, sans aucune animation. Les nœuds de la scène sont recopiés avec leurs
                    dépendances par `mesh_edit._extraire_doc` (recopie d'OCTETS des bufferViews retenus, jamais un
                    ré-encodage) : les accesseurs des clips disparaissent avec eux. Un GLB meshopt, que l'extraction
                    refuse, perd seulement la liste `animations` (ses octets restent, inertes) ;
    - `pose`      : la première image d'UN clip figée dans les TRS des nœuds, puis comme `maillage` ; sans clip, la
                    pose de repos (bind pose) — c'est alors le même fichier que `maillage`, et la réponse le dit ;
    - `animation` : le GLB tel quel, ou réduit aux clips cochés (la liste `animations` seule change) ;
* le PAQUET three.js (`zipfile`) : `characters/<nom>/character.glb`, `manifest.json`, `clips/<clip>.clip.json`
  (au format d'`AnimationClip.toJSON`, extrait ICI des accesseurs du GLB), `runtime/deepotus-personnage.js` (chargeur
  + AnimationMixer, écrit pour ce dépôt) et `AGENT_INSTRUCTIONS.md` (comment un agent de code l'intègre) ;
* le FBX par Blender en arrière-plan (`blender -b`), trouvé par `passes_blender.etat_blender` (même règle que les
  passes : BLENDER_PATH, puis Program Files, puis PATH ; 4.2 au moins). Le script est FIXE ; les deux chemins, calculés
  ici, passent en JSON après `--`. Délai borné, dossier temporaire sous `exports/`, nettoyé.

Tout s'écrit sous `<job>/exports/` et se sert par GET (`chemin_fichier`). Les réglages physiques (« Physics Config ») de
Sorceress n'ont pas d'équivalent : le dépôt n'a pas de physique de personnage — le manifeste ne promet rien.

Le reste de l'écran RÉUTILISE les routes existantes (Établi `/etabli/export` pour Unreal / Unity / Blender / Godot,
`/etabli/mouvement/godot` pour la scène .tscn et ses hitboxes, LOD, textures, conversions locales, impression 3D).
"""
from __future__ import annotations

import io
import json
import math
import re
import shutil
import subprocess
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.services import mesh_edit as ME

VARIANTES = ("maillage", "pose", "animation")
DELAI_BLENDER_S = 300.0
_NOM_SUR = re.compile(r"[^A-Za-z0-9_-]+")
_FICHIER = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
_EXT_SERVIES = (".glb", ".zip", ".fbx", ".json", ".md")

# three.js : les constantes de KeyframeTrack (InterpolateDiscrete / Linear) et de AnimationClip (NormalAnimationBlendMode)
_THREE_DISCRET, _THREE_LINEAIRE, _THREE_MELANGE_NORMAL = 2300, 2301, 2500
_PISTE = {"translation": ("position", "vector"), "rotation": ("quaternion", "quaternion"),
          "scale": ("scale", "vector"), "weights": ("morphTargetInfluences", "number")}
# un accesseur NORMALISÉ (rotations en octets ou en mots) : glTF 2.0 §3.11, la division qui rend la valeur réelle
_NORMES = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


class RefusExport(ValueError):
    """Une demande impossible sur ce modèle (400 côté route)."""


class BlenderIndisponible(RuntimeError):
    """Aucun Blender utilisable : la route répond 503 avec ce qu'il faut installer."""


# ─────────────────────────────── la source ───────────────────────────────

def job_nu(job) -> str:
    """Le nom de dossier du job, tel quel : un chemin, « . » ou « .. » sont refusés (jamais aplatis en silence)."""
    j = str(job or "")
    if not j or Path(j).name != j or j in (".", "..") or not _FICHIER.match(j):
        raise RefusExport("job : le nom du dossier du job 3D est attendu")
    return j


def dossier_exports(job: str) -> Path:
    from app.services import mesh_report
    return mesh_report.job_dir(job_nu(job)) / "exports"


def source(job: str, version: int | None = None) -> tuple[dict, Path]:
    """La fiche du modèle ouvert (`studio3d_ouvert.fiche`) et le chemin du GLB de cette version.
    FileNotFoundError : job ou version absents."""
    from app.services import studio3d_ouvert as SO
    f = SO.fiche(job_nu(job), version)
    etape = next(e for e in f["versions"] if e["version"] == f["version"])
    return f, SO._job_dir(f["job"]) / etape["file"]


def nom_sur(nom, defaut: str) -> str:
    """Un nom de fichier sûr (lettres ASCII sans accent, chiffres, _ et -), 48 caractères au plus ; vide → `defaut`."""
    def sur(x) -> str:
        a = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode("ascii")
        return _NOM_SUR.sub("_", a).strip("_-")[:48]
    return sur(nom) or sur(defaut) or "modele"


def _copie(doc: dict) -> dict:
    return json.loads(json.dumps(doc))


# ─────────────────────────────── lecture des clips ───────────────────────────────

def _valeurs(doc: dict, binc: bytes, i: int) -> list[tuple]:
    """Un accesseur lu par LE lecteur du dépôt, puis dénormalisé s'il est `normalized` (rotations compactes)."""
    vals = ME.lire_accesseur(doc, binc, i, quoi="l'export")
    a = doc["accessors"][i]
    if a.get("normalized") and a.get("componentType") in _NORMES:
        n = _NORMES[a["componentType"]]
        vals = [tuple(max(-1.0, c / n) for c in v) for v in vals]
    return vals


def _duree(doc: dict, binc: bytes, anim: dict) -> float:
    fin = 0.0
    for s in anim.get("samplers") or []:
        a = doc["accessors"][s["input"]]
        if a.get("max"):
            fin = max(fin, float(a["max"][0]))
        else:
            t = _valeurs(doc, binc, s["input"])
            if t:
                fin = max(fin, float(t[-1][0]))
    return round(fin, 6)


def clips(data: bytes) -> list[dict]:
    """Les clips du GLB : index, nom (celui du fichier, sinon clip_<i>), durée en secondes, nombre de pistes."""
    doc, binc = ME.lire_glb(data)
    out = []
    for i, a in enumerate(doc.get("animations") or []):
        out.append({"index": i, "nom": a.get("name") or f"clip_{i}", "pistes": len(a.get("channels") or []),
                    "duree": _duree(doc, binc, a)})
    return out


def _index_clip(doc: dict, clip) -> int:
    anims = doc.get("animations") or []
    if isinstance(clip, bool):
        raise RefusExport("clip : un index ou un nom est attendu")
    if isinstance(clip, int):
        if 0 <= clip < len(anims):
            return clip
    elif isinstance(clip, str):
        for i, a in enumerate(anims):
            if (a.get("name") or f"clip_{i}") == clip:
                return i
    raise RefusExport(f"clip « {str(clip)[:40]} » absent de ce modèle ({len(anims)} clip(s))")


# ─────────────────────────────── les trois variantes ───────────────────────────────

def _sans_animations(doc: dict, binc: bytes) -> tuple[dict, bytes]:
    """Le document sans animations, compacté : seuls les nœuds de la scène et ce qu'ils tirent derrière eux restent.

    La peau DOIT survivre (c'est le « Skeletal Mesh Only ») : si l'extraction en perd une (un squelette rangé hors de
    la scène), ou refuse (meshopt), on retombe sur le retrait de la seule liste `animations`."""
    scenes = doc.get("scenes") or []
    racines = (scenes[doc.get("scene", 0) or 0].get("nodes") if scenes else None) or []
    try:
        if not racines:
            raise ValueError("scène vide")
        out, neuf, _ = ME._extraire_doc(doc, binc, racines)
        if len(out.get("skins") or []) == len(doc.get("skins") or []) \
                and len(out.get("meshes") or []) == len(doc.get("meshes") or []):
            for cle in ("extras",):
                if cle in doc:
                    out[cle] = _copie(doc[cle])
            return out, neuf
    except (ValueError, KeyError, IndexError):
        pass
    out = _copie(doc)
    out.pop("animations", None)
    return out, binc


def glb_maillage(data: bytes) -> bytes:
    doc, binc = ME.lire_glb(data)
    return ME.ecrire_glb(*_sans_animations(doc, binc))


def figer_pose(doc: dict, binc: bytes, index: int) -> dict:
    """Un document dont les nœuds portent la PREMIÈRE image du clip `index` (les animations restent, on les retire
    après). Une valeur CUBICSPLINE se lit au milieu de son triplet (tangente d'entrée, valeur, tangente de sortie)."""
    out = _copie(doc)
    anim = out["animations"][index]
    nodes = out.get("nodes") or []
    for ch in anim.get("channels") or []:
        cible = ch.get("target") or {}
        n, chemin = cible.get("node"), cible.get("path")
        if n is None or not (0 <= n < len(nodes)) or chemin not in _PISTE:
            continue
        s = anim["samplers"][ch["sampler"]]
        cubique = s.get("interpolation") == "CUBICSPLINE"
        cles = int(out["accessors"][s["input"]]["count"])
        vals = _valeurs(out, binc, s["output"])
        if not cles or not vals:
            continue
        if chemin == "weights":
            k = len(vals) // (cles * (3 if cubique else 1))
            debut = k if cubique else 0
            nodes[n]["weights"] = [float(v[0]) for v in vals[debut:debut + k]]
            continue
        v = vals[1] if cubique else vals[0]
        if chemin == "rotation":
            lg = math.sqrt(sum(c * c for c in v)) or 1.0
            v = tuple(c / lg for c in v)
        nodes[n].pop("matrix", None)           # glTF : un nœud animé ne porte pas de matrice
        nodes[n][chemin] = [float(c) for c in v]
    return out


def glb_pose(data: bytes, clip=None) -> tuple[bytes, dict]:
    doc, binc = ME.lire_glb(data)
    anims = doc.get("animations") or []
    if not anims:
        return ME.ecrire_glb(*_sans_animations(doc, binc)), {"pose": "repos", "clip": None}
    i = _index_clip(doc, 0 if clip is None else clip)
    pose = figer_pose(doc, binc, i)
    return ME.ecrire_glb(*_sans_animations(pose, binc)), {"pose": "premiere_image",
                                                          "clip": anims[i].get("name") or f"clip_{i}"}


def _garder_clips(doc: dict, voulus) -> dict:
    out = _copie(doc)
    anims = out.get("animations") or []
    if not anims:
        raise RefusExport("ce modèle n'a aucune animation : exporte le maillage seul, ou anime-le d'abord")
    if voulus:
        if not isinstance(voulus, list):
            raise RefusExport("clips : une liste d'index ou de noms est attendue")
        garder = sorted({_index_clip(doc, c) for c in voulus})
        out["animations"] = [anims[i] for i in garder]
    return out


def glb_animation(data: bytes, voulus=None) -> bytes:
    doc, binc = ME.lire_glb(data)
    if not voulus:
        if not doc.get("animations"):
            raise RefusExport("ce modèle n'a aucune animation : exporte le maillage seul, ou anime-le d'abord")
        return data                              # tel quel : pas un octet réécrit
    return ME.ecrire_glb(_garder_clips(doc, voulus), binc)


# ─────────────────────────────── clips three.js ───────────────────────────────

def nom_three(nom: str) -> str:
    """`PropertyBinding.sanitizeNodeName` de three.js : blancs → « _ », puis « [ ] . : / » retirés."""
    return re.sub(r"[\[\]\.:/]", "", re.sub(r"\s", "_", str(nom)))


def noms_three(doc: dict) -> list[str]:
    """Le nom que GLTFLoader donnera à chaque nœud : assaini, puis rendu unique (« _1 », « _2 »… comme
    `GLTFParser.createUniqueName`). Un nœud sans nom n'a qu'un uuid au chargement : sa piste ne se lie pas (vide)."""
    vus: dict[str, int] = {}
    out = []
    for n in doc.get("nodes") or []:
        if not n.get("name"):
            out.append("")
            continue
        s = nom_three(n["name"])
        if s in vus:
            vus[s] += 1
            s = f"{s}_{vus[s] - 1}"
        else:
            vus[s] = 1
        out.append(s)
    return out


def clip_three(doc: dict, binc: bytes, index: int) -> dict:
    """Le clip `index` au format d'`AnimationClip.toJSON` (relu par `AnimationClip.parse`). CUBICSPLINE est ramené à
    ses valeurs (tangentes ignorées) en interpolation linéaire ; STEP devient discret."""
    anim = doc["animations"][index]
    noms = noms_three(doc)
    pistes = []
    for ch in anim.get("channels") or []:
        cible = ch.get("target") or {}
        n, chemin = cible.get("node"), cible.get("path")
        if n is None or chemin not in _PISTE or not (0 <= n < len(noms)) or not noms[n]:
            continue
        s = anim["samplers"][ch["sampler"]]
        temps = [float(t[0]) for t in _valeurs(doc, binc, s["input"])]
        vals = _valeurs(doc, binc, s["output"])
        interp = s.get("interpolation") or "LINEAR"
        if interp == "CUBICSPLINE":
            k = len(vals) // (3 * len(temps)) if temps else 0
            plat = []
            for c in range(len(temps)):
                for v in vals[(3 * c + 1) * k:(3 * c + 2) * k]:
                    plat.extend(v)
        else:
            plat = [float(c) for v in vals for c in v]
        prop, type_ = _PISTE[chemin]
        pistes.append({"name": f"{noms[n]}.{prop}", "type": type_, "times": temps,
                       "values": [float(c) for c in plat],
                       "interpolation": _THREE_DISCRET if interp == "STEP" else _THREE_LINEAIRE})
    nom = anim.get("name") or f"clip_{index}"
    return {"name": nom, "duration": _duree(doc, binc, anim), "tracks": pistes,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"deepotus-clip:{nom}:{index}")),
            "blendMode": _THREE_MELANGE_NORMAL}


# ─────────────────────────────── le paquet three.js ───────────────────────────────

RUNTIME_JS = r"""/* deepotus-personnage.js — runtime minimal d'un personnage exporté par le 3D Studio de DeepotusVideo.
 * © DeepotusVideo. Licence MIT : utilisation, copie, modification, fusion, publication, distribution, sous-licence
 * et vente permises, à condition de garder cette mention. LE LOGICIEL EST FOURNI « TEL QUEL », SANS GARANTIE.
 *
 * Needs three.js (r150+) with an import map: "three" and "three/addons/".
 *   import { DeepotusCharacter } from "./runtime/deepotus-personnage.js";
 *   const hero = await DeepotusCharacter.load("./characters/<name>/");
 *   scene.add(hero.object); hero.play("Walk");  // in your loop: hero.update(clock.getDelta());
 */
import { AnimationClip, AnimationMixer, LoopOnce, LoopRepeat } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export class DeepotusCharacter {
  /** Loads manifest.json, the character GLB and every clips/*.clip.json listed in the manifest. */
  static async load(folder, { loader = new GLTFLoader() } = {}) {
    const base = folder.endsWith("/") ? folder : folder + "/";
    const manifest = await (await fetch(base + "manifest.json")).json();
    const gltf = await loader.loadAsync(base + manifest.glb);
    const clips = [...gltf.animations];
    for (const c of manifest.clips || []) {
      if (!c.fichier || clips.some((k) => k.name === c.nom)) continue;
      clips.push(AnimationClip.parse(await (await fetch(base + c.fichier)).json()));
    }
    return new DeepotusCharacter(gltf.scene, clips, manifest);
  }

  constructor(object, clips, manifest = {}) {
    this.object = object;
    this.clips = clips;
    this.manifest = manifest;
    this.mixer = new AnimationMixer(object);
    this.current = null;
  }

  /** Clip names, in file order. */
  get names() { return this.clips.map((c) => c.name); }

  /** Plays a clip by name, cross-fading from the current one. Returns the AnimationAction (or null). */
  play(name, { fade = 0.25, loop = true, speed = 1 } = {}) {
    const clip = this.clips.find((c) => c.name === name);
    if (!clip) return null;
    const action = this.mixer.clipAction(clip);
    action.reset();
    action.setLoop(loop ? LoopRepeat : LoopOnce, Infinity);
    action.clampWhenFinished = !loop;
    action.timeScale = speed;
    action.play();
    if (this.current && this.current !== action) this.current.crossFadeTo(action, fade, false);
    this.current = action;
    return action;
  }

  /** Stops every clip (back to the bind pose). */
  stop() { this.mixer.stopAllAction(); this.current = null; }

  /** Advance the animation; call once per frame with the elapsed seconds. */
  update(dt) { this.mixer.update(dt); }
}
"""


def _instructions(nom: str, manifeste: dict) -> str:
    clips_l = "\n".join(f"- `{c['nom']}` — {c['duree']:g} s" + (f" (`{c['fichier']}`)" if c.get("fichier") else "")
                        for c in manifeste["clips"]) or "- (no clip: a static character)"
    return f"""# AGENT_INSTRUCTIONS — integrating `{nom}` (exported by DeepotusVideo 3D Studio)

You are a coding agent adding this character to a three.js project. Follow these steps exactly.

## What is in this package

- `characters/{nom}/character.glb` — the skinned character ({manifeste['triangles']} triangles, {len(manifeste['os'])} bones), clips embedded.
- `characters/{nom}/manifest.json` — bones, clips (name, duration, file), source job and version. Read it; do not guess.
- `characters/{nom}/clips/*.clip.json` — each clip in `THREE.AnimationClip.toJSON` format (`AnimationClip.parse`).
- `runtime/deepotus-personnage.js` — a ~60-line ES module: `DeepotusCharacter.load(folder)`, `play(name)`, `stop()`, `update(dt)`.

Clips:
{clips_l}

## Steps

1. Copy `characters/` and `runtime/` into the project's static/public folder, keeping the structure.
2. Make sure `three` (r150 or newer) resolves, and that `three/addons/` resolves to `three/examples/jsm/`
   (bundlers do this already; plain HTML needs an import map).
3. Load and play:

```js
import * as THREE from "three";
import {{ DeepotusCharacter }} from "./runtime/deepotus-personnage.js";

const hero = await DeepotusCharacter.load("./characters/{nom}/");
scene.add(hero.object);
hero.play(hero.names[0]);              // or a name from manifest.json
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {{ hero.update(clock.getDelta()); renderer.render(scene, camera); }});
```

## Rules

- Units are metres, +Y is up, the character faces +Z (glTF convention). Scale the `object`, never the bones.
- Do not edit `character.glb`; re-export from DeepotusVideo instead.
- Clip `.clip.json` tracks target bones by their three.js node name (`PropertyBinding.sanitizeNodeName`).
  If you rename nodes, the clips stop binding.
- No physics settings are shipped: add colliders in your engine if you need them.
"""


def paquet_threejs(data: bytes, *, nom: str, job: str, version: int, voulus=None) -> tuple[bytes, dict]:
    """Le ZIP et son manifeste. `voulus` réduit les clips du GLB ET des .clip.json aux clips cochés."""
    doc, binc = ME.lire_glb(data)
    if voulus:
        doc = _garder_clips(doc, voulus)
        glb = ME.ecrire_glb(doc, binc)
    else:
        glb = data
    inv = ME.rig_inventory(glb)
    tris = _triangles(doc)
    racine = f"characters/{nom}/"
    fichiers_clips, entrees_clips = {}, []
    for i, a in enumerate(doc.get("animations") or []):
        cj = clip_three(doc, binc, i)
        fichier = f"clips/{nom_sur(cj['name'], f'clip_{i}')}.clip.json"
        k = 2
        while fichier in fichiers_clips:
            fichier = f"clips/{nom_sur(cj['name'], f'clip_{i}')}_{k}.clip.json"
            k += 1
        fichiers_clips[fichier] = cj
        entrees_clips.append({"nom": cj["name"], "duree": cj["duration"], "pistes": len(cj["tracks"]),
                              "fichier": fichier})
    manifeste = {
        "format": "deepotus-personnage", "version_format": 1, "nom": nom, "glb": "character.glb",
        "source": {"job": job, "version": int(version), "outil": "DeepotusVideo 3D Studio"},
        "cree_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "triangles": tris, "os": [o["nom"] for o in inv["os"]], "rigge": inv["a_squelette"],
        "clips": entrees_clips, "unites": "metres", "haut": "+Y",
        "physique": None,
    }
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(racine + "character.glb", glb)
        z.writestr(racine + "manifest.json", json.dumps(manifeste, ensure_ascii=False, indent=1))
        for f, cj in fichiers_clips.items():
            z.writestr(racine + f, json.dumps(cj, ensure_ascii=False, separators=(",", ":")))
        z.writestr("runtime/deepotus-personnage.js", RUNTIME_JS)
        z.writestr("AGENT_INSTRUCTIONS.md", _instructions(nom, manifeste))
    return tampon.getvalue(), manifeste


def _triangles(doc: dict) -> int:
    n = 0
    for m in doc.get("meshes") or []:
        for p in m.get("primitives") or []:
            if p.get("mode", 4) != 4:
                continue
            if p.get("indices") is not None:
                n += int(doc["accessors"][p["indices"]]["count"]) // 3
            elif (p.get("attributes") or {}).get("POSITION") is not None:
                n += int(doc["accessors"][p["attributes"]["POSITION"]]["count"]) // 3
    return n


# ─────────────────────────────── écrire sous exports/ ───────────────────────────────

def _ecrire(job: str, fichier: str, octets: bytes) -> dict:
    d = dossier_exports(job)
    d.mkdir(parents=True, exist_ok=True)
    p = d / fichier
    p.write_bytes(octets)
    return {"fichier": fichier, "octets": len(octets), "url": url_fichier(job, fichier)}


def url_fichier(job: str, fichier: str) -> str:
    return f"/api/studio3d/exporter/{job_nu(job)}/fichier/{fichier}"


def exporter_glb(job: str, version: int | None, variante: str, *, clip=None, voulus=None, nom=None) -> dict:
    if variante not in VARIANTES:
        raise RefusExport(f"variante « {str(variante)[:20]} » — {', '.join(VARIANTES)}")
    f, p = source(job, version)
    data = p.read_bytes()
    info: dict = {}
    if variante == "maillage":
        octets = glb_maillage(data)
    elif variante == "pose":
        octets, info = glb_pose(data, clip)
    else:
        octets = glb_animation(data, voulus)
    base = nom_sur(nom, f["nom"] or f["job"])
    r = _ecrire(f["job"], f"{base}_v{f['version']}_{variante}.glb", octets)
    doc, _ = ME.lire_glb(octets)
    return {**r, **info, "variante": variante, "job": f["job"], "version": f["version"],
            "clips": [a.get("name") or f"clip_{i}" for i, a in enumerate(doc.get("animations") or [])],
            "peaux": len(doc.get("skins") or [])}


def exporter_paquet(job: str, version: int | None, *, nom=None, voulus=None) -> dict:
    f, p = source(job, version)
    base = nom_sur(nom, f["nom"] or f["job"])
    octets, manifeste = paquet_threejs(p.read_bytes(), nom=base, job=f["job"], version=f["version"], voulus=voulus)
    r = _ecrire(f["job"], f"{base}_v{f['version']}_threejs.zip", octets)
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        entrees = z.namelist()
    return {**r, "job": f["job"], "version": f["version"], "manifeste": manifeste, "entrees": entrees}


# ─────────────────────────────── FBX par Blender ───────────────────────────────

SCRIPT_FBX = r'''# DeepotusVideo t400 — GLB -> FBX (script FIXE ; seuls deux chemins calculés par le serveur arrivent, en JSON)
import json, sys
import bpy
a = json.loads(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a["source"])
bpy.ops.export_scene.fbx(filepath=a["sortie"], use_selection=False, add_leaf_bones=False,
                         bake_anim=bool(a["animation"]), path_mode="COPY", embed_textures=True)
print("DZFBX fin")
'''


def _blender() -> dict:                      # couture : remplacée au banc
    from app.services import passes_blender
    return passes_blender.etat_blender()


def _executer(argv: list[str], delai: float) -> tuple[int, str]:     # couture : remplacée au banc
    drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run(argv, capture_output=True, timeout=delai, creationflags=drapeaux)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def etat_blender() -> dict:
    try:
        e = _blender()
    except Exception as ex:                   # noqa: BLE001 — l'état ne doit jamais casser l'écran
        return {"dispo": False, "exe": None, "version": None, "raison": f"{type(ex).__name__}"}
    return {k: e.get(k) for k in ("dispo", "exe", "version", "raison")}


def exporter_fbx(job: str, version: int | None, *, variante: str = "animation", nom=None) -> dict:
    """Le FBX de la variante demandée (maillage ou animation), écrit par Blender en arrière-plan. Refus AVANT tout
    lancement : variante, modèle, puis Blender absent (BlenderIndisponible)."""
    if variante not in ("maillage", "animation"):
        raise RefusExport("fbx : variante « maillage » ou « animation »")
    f, p = source(job, version)
    data = p.read_bytes()
    doc, _ = ME.lire_glb(data)
    if variante == "animation" and not doc.get("animations"):
        variante = "maillage"                 # rien à cuire : un FBX du maillage, et la réponse le dit
    gl = data if variante == "animation" else glb_maillage(data)
    e = _blender()
    if not e.get("dispo"):
        raise BlenderIndisponible("Blender 4.2 ou plus récent est introuvable (BLENDER_PATH, Program Files ou PATH) — "
                                  "installe-le depuis blender.org, c'est gratuit.")
    base = nom_sur(nom, f["nom"] or f["job"])
    sortie_nom = f"{base}_v{f['version']}_{variante}.fbx"
    d = dossier_exports(f["job"])
    tmp = d / f"_blender_{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True)
    try:
        (tmp / "source.glb").write_bytes(gl)
        (tmp / "fbx.py").write_text(SCRIPT_FBX, encoding="utf-8")
        params = json.dumps({"source": str(tmp / "source.glb"), "sortie": str(tmp / "sortie.fbx"),
                             "animation": variante == "animation"}, ensure_ascii=True)
        argv = [str(e["exe"]), "-b", "--factory-startup", "--python", str(tmp / "fbx.py"), "--", params]
        try:
            code, texte = _executer(argv, DELAI_BLENDER_S)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Blender a dépassé {int(DELAI_BLENDER_S)} s")
        produit = tmp / "sortie.fbx"
        if code != 0 or not produit.is_file() or produit.stat().st_size == 0:
            fin = " ".join(texte.strip().splitlines()[-3:])[:300]
            raise RuntimeError(f"Blender n'a pas écrit le FBX (code {code}) : {fin}")
        octets = produit.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    r = _ecrire(f["job"], sortie_nom, octets)
    return {**r, "variante": variante, "job": f["job"], "version": f["version"], "blender": e.get("version")}


# ─────────────────────────────── état et fichiers ───────────────────────────────

def etat(job: str, version: int | None = None) -> dict:
    """Ce que l'écran doit savoir AVANT d'exporter : clips, os (et leur rôle, pour les hitboxes Godot), Blender,
    et les exports déjà écrits pour ce job."""
    from app.services import mouvement_rig as MR
    f, p = source(job, version)
    data = p.read_bytes()
    inv = ME.rig_inventory(data)
    d = dossier_exports(f["job"])
    deja = sorted((x.name for x in d.iterdir() if x.is_file() and x.suffix.lower() in _EXT_SERVIES), key=str.lower) \
        if d.is_dir() else []
    return {"job": f["job"], "version": f["version"], "nom": f["nom"], "nom_fichier": nom_sur(None, f["nom"] or f["job"]),
            "clips": clips(data), "a_squelette": inv["a_squelette"],
            "os": [{"nom": o["nom"], "role": MR.role(o["nom"])} for o in inv["os"]],
            "variantes": list(VARIANTES), "blender": etat_blender(),
            "exports": [{"fichier": n, "url": url_fichier(f["job"], n)} for n in deja]}


def chemin_fichier(job: str, fichier: str) -> Path:
    """Un fichier de `<job>/exports/`, par son NOM seul. RefusExport : nom invalide ; FileNotFoundError : absent."""
    nom = str(fichier or "")
    if Path(nom).name != nom or not _FICHIER.match(nom) or nom.startswith(".") \
            or Path(nom).suffix.lower() not in _EXT_SERVIES:
        raise RefusExport("fichier : nom invalide")
    p = dossier_exports(job) / nom
    if not p.is_file():
        raise FileNotFoundError("export introuvable")
    return p
