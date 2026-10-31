# -*- coding: utf-8 -*-
"""t398 + t399 (31/10/2026) — l'écran ANIMER du 3D Studio : bibliothèque de l'utilisateur, application d'une
animation du catalogue Meshy, texte → mouvement.

1. FAVORIS ET COLLECTIONS (t398) : une écriture de l'utilisateur, rangée dans `DATA_ROOT/studio3d/animer.json`
   (jamais dans le dépôt, jamais dans un job) : `{"favoris": [ids], "collections": [{id, nom, ids, cree_le}]}`.
   Un identifiant inconnu du catalogue est refusé ; l'ordre d'ajout est gardé.

2. APPLIQUER une animation du catalogue à un modèle RIGGÉ PAR MESHY (t398) : `POST openapi/v1/animations` avec le
   `rig_task_id` du manifeste (`asset.json › rig.meshy_task`, écrit par `asset3d_rig.rigger_asset3d`) et UN
   `action_id` — 3 crédits, sans refaire le rig (5 crédits) comme le ferait `POST /assets/3d/{job}/rig`. Le clip est
   rapatrié en `anim_action_<id>.glb` et inscrit dans `rig.animations` : il devient une source de `mouvement_rig`
   (type « meshy ») comme les clips rapatriés par le rig.

3. TEXTE → MOUVEMENT (t399, D5 révisée) : Meshy Text to Motion, `POST openapi/v1/text-to-motion`
   {prompt ≤ 400 car., mode, duration 2 à 10 s par pas de 0,5}. Le mode « swift » (3 crédits) rend un BVH que
   `mouvement_rig` lit ; « prime » (10 crédits) rend un FBX qu'aucun lecteur embarqué ne lit : il est REFUSÉ avant
   toute dépense. Le BVH est rangé dans `<job>/mouvements/` (origine « meshy-motion ») puis RECIBLÉ sur le rig de la
   version ouverte : une version de plus avec le clip nommé (jamais un écrasement, doctrine de l'Établi).
   HY-Motion (fal) n'est PAS branché : sa licence exclut l'UE (relevé t387) ; il attend l'avis de l'utilisateur.

Rien ici ne vérifie la clé, le devis ou le plafond : c'est la route (`studio3d_animer_routes`) qui refuse, dans
l'ordre, AVANT d'appeler ces fonctions.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from uuid import uuid4

from app.services import animations_catalogue as CAT

# ───────────────────────────── 1. favoris et collections ─────────────────────────────

COLLECTIONS_MAX = 50
IDS_MAX = 300
NOM_MAX = 48
_VERROU = threading.Lock()


def _fichier() -> Path:
    from app.config import DATA_ROOT
    return Path(DATA_ROOT) / "studio3d" / "animer.json"


def _lire() -> dict:
    try:
        d = json.loads(_fichier().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    fav = [int(x) for x in d.get("favoris") or [] if isinstance(x, int)]
    cols = [c for c in d.get("collections") or [] if isinstance(c, dict) and c.get("id")]
    return {"favoris": fav, "collections": cols}


def _ecrire(d: dict) -> None:
    p = _fichier()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def _id_connu(x) -> int:
    if isinstance(x, bool):
        raise ValueError("identifiant d'animation : un entier du catalogue Meshy est attendu")
    try:
        i = int(x)
    except (TypeError, ValueError):
        raise ValueError("identifiant d'animation : un entier du catalogue Meshy est attendu")
    if CAT.par_id(i) is None:
        raise ValueError(f"animation {i} absente du catalogue Meshy")
    return i


def favoris() -> list[int]:
    return _lire()["favoris"]


def marquer_favori(action_id, favori: bool = True) -> list[int]:
    i = _id_connu(action_id)
    with _VERROU:
        d = _lire()
        fav = [x for x in d["favoris"] if x != i]
        if favori:
            if len(fav) >= IDS_MAX:
                raise ValueError(f"favoris : {IDS_MAX} au plus")
            fav.append(i)
        d["favoris"] = fav
        _ecrire(d)
        return fav


def collections() -> list[dict]:
    return _lire()["collections"]


def _nom(nom) -> str:
    n = re.sub(r"\s+", " ", str(nom or "")).strip()
    if not n:
        raise ValueError("collection : un nom est attendu")
    return n[:NOM_MAX]


def creer_collection(nom, ids=()) -> dict:
    with _VERROU:
        d = _lire()
        if len(d["collections"]) >= COLLECTIONS_MAX:
            raise ValueError(f"collections : {COLLECTIONS_MAX} au plus")
        propres = []
        for x in ids or ():
            i = _id_connu(x)
            if i not in propres:
                propres.append(i)
        c = {"id": uuid4().hex[:10], "nom": _nom(nom), "ids": propres[:IDS_MAX],
             "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S")}
        d["collections"].append(c)
        _ecrire(d)
        return c


def modifier_collection(cid: str, *, nom=None, ajouter=(), retirer=()) -> dict:
    with _VERROU:
        d = _lire()
        c = next((x for x in d["collections"] if x.get("id") == cid), None)
        if c is None:
            raise FileNotFoundError(f"collection inconnue : {cid}")
        if nom is not None:
            c["nom"] = _nom(nom)
        ids = [int(x) for x in c.get("ids") or []]
        for x in ajouter or ():
            i = _id_connu(x)
            if i not in ids:
                ids.append(i)
        enlever = set()
        for x in retirer or ():
            try:
                enlever.add(int(x))
            except (TypeError, ValueError):
                raise ValueError("retirer : des identifiants entiers sont attendus")
        ids = [i for i in ids if i not in enlever]
        if len(ids) > IDS_MAX:
            raise ValueError(f"collection : {IDS_MAX} animations au plus")
        c["ids"] = ids
        _ecrire(d)
        return c


def supprimer_collection(cid: str) -> None:
    with _VERROU:
        d = _lire()
        avant = len(d["collections"])
        d["collections"] = [x for x in d["collections"] if x.get("id") != cid]
        if len(d["collections"]) == avant:
            raise FileNotFoundError(f"collection inconnue : {cid}")
        _ecrire(d)


# ───────────────────────────── 2. appliquer une animation du catalogue ─────────────────────────────

ANIM_BASE = "openapi/v1/animations"
CREDITS_ANIMATION = 3            # pricing.md de Meshy, relevé t387 : 3 crédits l'action


def rig_meshy(job: str) -> str | None:
    """Le `rig_task_id` Meshy du job (manifeste), ou None : modèle non riggé par Meshy, ou job sans manifeste."""
    from app.services import asset3d_service as A3
    try:
        rig = A3.read_manifest(Path(str(job)).name).get("rig") or {}
    except (FileNotFoundError, ValueError, OSError):
        return None
    t = rig.get("meshy_task")
    return str(t) if t else None


def devis_credits(credits: float) -> dict:
    """Le devis d'une tâche Meshy à `credits` crédits (kind « meshy » de pricing : la conversion $ reste
    directionnelle, `meshy_credit_usd`)."""
    from app.services import pricing
    return pricing.estimate({"kind": "meshy", "credits": float(credits)})


async def appliquer_animation(job: str, action_id: int, on_etat=None) -> dict:
    """Une animation du catalogue sur le rig Meshy du job → `anim_action_<id>.glb`, inscrite au manifeste."""
    from app.services import asset3d_service as A3
    from app.services import meshy_service as MS

    async def etat(**champs):
        if on_etat:
            await on_etat(champs)

    job = Path(str(job)).name
    tid = rig_meshy(job)
    if not tid:
        raise ValueError("ce modèle n'a pas de rig Meshy : passe par l'écran Rig")
    payload = {"rig_task_id": tid, "action_id": int(action_id)}
    atid = await MS.create_task(ANIM_BASE, payload)
    await etat(etat="genere", meshy_task=atid)
    t = await A3._attendre_meshy(ANIM_BASE, atid, None)
    res = t.get("result") if isinstance(t.get("result"), dict) else t
    url = res.get("animation_glb_url")
    if not url:
        raise RuntimeError(f"meshy: la tâche {atid} n'a rendu aucun GLB d'animation")
    d = A3._job_dir(job)
    f = d / f"anim_action_{int(action_id)}.glb"
    f.write_bytes(await MS._fetch_url(url))
    man = A3.read_manifest(job)
    rig = dict(man.get("rig") or {})
    anims = dict(rig.get("animations") or {})
    anims[f"action_{int(action_id)}"] = f.name
    rig["animations"] = anims
    A3.write_manifest(d, {**man, "rig": rig})
    return {"meshy_task": atid, "nom": f"action_{int(action_id)}", "fichier": f.name,
            "url": f"/api/assets/3d/{job}/animation/action_{int(action_id)}"}


# ───────────────────────────── 3. texte → mouvement (Meshy Text to Motion) ─────────────────────────────

MOTION_BASE = "openapi/v1/text-to-motion"
PROMPT_MAX = 400
DUREE_MIN, DUREE_MAX, DUREE_PAS = 2.0, 10.0, 0.5
# docs.meshy.ai/api/text-to-motion (relevé t387) : prime = FBX 10 cr (défaut de Meshy), swift = BVH 3 cr
MODES = {
    "swift": {"credits": 3, "format": "bvh", "lisible": True},
    "prime": {"credits": 10, "format": "fbx", "lisible": False},
}
# les autres modèles de la rangée « Generate » de Sorceress, dits et grisés (relevé t387, D5 révisée)
AUTRES_MODELES = [
    {"id": "hy-motion", "raison": "licence"},      # Tencent HY-MOTION 1.0 : exclut l'UE et le Royaume-Uni
    {"id": "kimodo", "raison": "sans_api"},        # NVIDIA Kimodo : aucune API officielle
    {"id": "gvhmr", "raison": "non_commercial"},   # vidéo → mouvement, licence non commerciale (Uthana le remplace)
]


def valider_texte(body: dict) -> dict:
    """{prompt, duree, mode, nom} propres, ou ValueError au message lisible. Aucune dépense ici."""
    prompt = re.sub(r"\s+", " ", str((body or {}).get("prompt") or "")).strip()
    if not prompt:
        raise ValueError("prompt : décris le mouvement (« marche prudente, regarde à gauche »)")
    if len(prompt) > PROMPT_MAX:
        raise ValueError(f"prompt : {PROMPT_MAX} caractères au plus")
    duree = (body or {}).get("duree")
    if isinstance(duree, bool) or not isinstance(duree, (int, float)):
        raise ValueError(f"durée : un nombre de secondes, de {DUREE_MIN:g} à {DUREE_MAX:g}")
    duree = float(duree)
    if not DUREE_MIN <= duree <= DUREE_MAX:
        raise ValueError(f"durée : de {DUREE_MIN:g} à {DUREE_MAX:g} s")
    if abs(duree / DUREE_PAS - round(duree / DUREE_PAS)) > 1e-9:
        raise ValueError(f"durée : par pas de {DUREE_PAS:g} s")
    mode = str((body or {}).get("mode") or "swift")
    if mode not in MODES:
        raise ValueError("mode : « swift » (BVH) ou « prime » (FBX)")
    if not MODES[mode]["lisible"]:
        raise ValueError("mode « prime » : Meshy rend un FBX, qu'aucun lecteur embarqué ne lit — "
                         "choisis « swift » (BVH), relu et reciblé ici")
    brut = str((body or {}).get("nom") or "") or "_".join(prompt.split()[:4])
    nom = re.sub(r"[^A-Za-z0-9_-]+", "_", brut).strip("_")[:40] or "mouvement"
    return {"prompt": prompt, "duree": duree, "mode": mode, "nom": nom}


def etat_texte() -> dict:
    """Ce que l'écran affiche avant tout geste : modes, bornes, devis par mode, modèles grisés."""
    return {"modes": [{"id": m, **v, "devis": devis_credits(v["credits"])} for m, v in MODES.items()],
            "duree": {"min": DUREE_MIN, "max": DUREE_MAX, "pas": DUREE_PAS}, "prompt_max": PROMPT_MAX,
            "autres": AUTRES_MODELES, "intensite": False}


async def texte_vers_mouvement(job: str, version: int, entree: dict, on_etat=None) -> dict:
    """Meshy Text to Motion → BVH rangé dans le job → reciblé sur la version `version` → une version de plus.

    `entree` sort de `valider_texte`. Rend {meshy_task, source, version, rapport}."""
    from app.services import asset3d_service as A3
    from app.services import mesh_edit as ME
    from app.services import mesh_report
    from app.services import meshy_service as MS
    from app.services import mouvement_rig as MR

    async def etat(**champs):
        if on_etat:
            await on_etat(champs)

    job = Path(str(job)).name
    payload = {"prompt": entree["prompt"], "mode": entree["mode"], "duration": entree["duree"]}
    tid = await MS.create_task(MOTION_BASE, payload)
    await etat(etat="genere", meshy_task=tid)
    t = await A3._attendre_meshy(MOTION_BASE, tid, None)
    res = t.get("result") if isinstance(t.get("result"), dict) else t
    url, fmt = res.get("motion_url"), str(res.get("motion_format") or "").lower()
    if not url:
        raise RuntimeError(f"meshy: la tâche {tid} n'a rendu aucun mouvement")
    if fmt and fmt != "bvh":
        raise ValueError(f"meshy: mouvement rendu en {fmt}, illisible ici (BVH attendu)")
    data = await MS._fetch_url(url)
    await etat(etat="recible", meshy_task=tid)
    fiche = MR.ranger(job, f"{entree['nom']}.bvh", data, {
        "origine": "meshy-motion", "prompt": entree["prompt"], "duree_demandee": entree["duree"],
        "mode": entree["mode"], "meshy_task": tid})
    nom_v = "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"
    cible = mesh_report.job_dir(job) / nom_v
    if not cible.is_file():
        raise FileNotFoundError(f"{job}/{nom_v} introuvable")
    src = MR.lire_fichier(fiche["fichier"], (MR.dossier(job) / fiche["fichier"]).read_bytes())
    sortie, rapport = MR.appliquer(cible.read_bytes(), src, nom=entree["nom"])
    ecrite = ME.ecrire_version(job, sortie, operation="mouvement", detail={
        "depuis": {"version": int(version), "fichier": nom_v},
        "source": {"type": "fichier", "nom": fiche["fichier"], "origine": "meshy-motion"}, **rapport})
    return {"meshy_task": tid, "source": {"type": "fichier", "nom": fiche["fichier"]},
            "version": ecrite.get("version"), "clip": rapport.get("clip"), "rapport": rapport}


# ───────────────────────────── l'état des tâches de fond (fichier par tâche, dans le job) ─────────────────────────────

def _etat_chemin(job: str, tache: str) -> Path:
    from app.services import mesh_report
    return mesh_report.job_dir(Path(str(job)).name) / "mouvements" / "_animer" / f"{tache}.json"


def poser_etat(job: str, tache: str, **champs) -> dict:
    p = _etat_chemin(job, tache)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        e = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        e = {"tache": tache}
    e.update(champs, maj_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
    p.write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    return e


def lire_etat(job: str, tache: str) -> dict | None:
    p = _etat_chemin(job, tache)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
