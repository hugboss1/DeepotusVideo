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

4. HY-MOTION (t405) : le second modèle texte → mouvement, ÉTEINT par défaut — fal-ai/hunyuan-motion (1B, 0,08 $) et
   /fast (0,46B, 0,06 $), `output_format: "dict"`. Sa licence (« Tencent HY-MOTION 1.0 Community License ») EXCLUT
   l'Union européenne, le Royaume-Uni et la Corée du Sud : l'utilisateur la lit et l'accepte pour SON usage (case
   rangée dans `animer.json › licences`), et le serveur refuse (400) tout tir sans `licence_acceptee: true`. Le dict
   rendu (rot6d (L,22,6) + transl (L,3), squelette SMPL 22 os à 30 i/s, relevé du code amont — NON confirmé chez fal)
   est converti en BVH par `hymotion_vers_bvh` (pur, accepte aussi axe-angle (L,22,3) et quaternion (L,22,4)), puis
   rangé et reciblé par `mouvement_rig` exactement comme le BVH de Meshy.

Rien ici ne vérifie la clé, le devis ou le plafond : c'est la route (`studio3d_animer_routes`) qui refuse, dans
l'ordre, AVANT d'appeler ces fonctions.
"""
from __future__ import annotations

import json
import math
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
    lic = d.get("licences") if isinstance(d.get("licences"), dict) else {}
    lic = {k: v for k, v in lic.items() if isinstance(v, dict)}
    return {"favoris": fav, "collections": cols, "licences": lic}


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
# les autres modèles de la rangée « Generate » de Sorceress, dits et grisés (relevé t387, D5 révisée) ; HY-Motion
# est branché en t405 (voir HY_MODELES), derrière sa licence
AUTRES_MODELES = [
    {"id": "kimodo", "raison": "sans_api", "detail": "kimodo"},        # NVIDIA Kimodo : aucune API officielle
    {"id": "gvhmr", "raison": "non_commercial", "detail": "gvhmr"},    # vidéo → mouvement, licence non commerciale
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
    """Ce que l'écran affiche avant tout geste : modes, bornes, devis par mode, HY-Motion et sa licence, modèles
    grisés."""
    return {"modes": [{"id": m, **v, "devis": devis_credits(v["credits"])} for m, v in MODES.items()],
            "duree": {"min": DUREE_MIN, "max": DUREE_MAX, "pas": DUREE_PAS}, "prompt_max": PROMPT_MAX,
            "hy": etat_hy(), "autres": AUTRES_MODELES, "intensite": False}


async def texte_vers_mouvement(job: str, version: int, entree: dict, on_etat=None) -> dict:
    """Meshy Text to Motion → BVH rangé dans le job → reciblé sur la version `version` → une version de plus.

    `entree` sort de `valider_texte`. Rend {meshy_task, source, version, rapport}."""
    from app.services import asset3d_service as A3
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
    r = _recibler_dans_version(job, version, fiche, entree["nom"], "meshy-motion")
    return {"meshy_task": tid, **r}


# ───────────────────────────── 4. HY-Motion (fal) : licence, saisie, conversion, tir ─────────────────────────────

HY_MODELES = {
    # relevé t387 (fal.ai/models/fal-ai/hunyuan-motion/llms.txt) : 0,08 $ le 1B, 0,06 $ le 0.46B (/fast)
    "hy-motion": {"endpoint": "fal-ai/hunyuan-motion", "usd": 0.08, "taille": "1B"},
    "hy-motion-fast": {"endpoint": "fal-ai/hunyuan-motion/fast", "usd": 0.06, "taille": "0.46B"},
}
MODELES_TEXTE = ("meshy", *HY_MODELES)
HY_DUREE_MIN, HY_DUREE_MAX, HY_DUREE_PAS = 0.5, 12.0, 0.5
HY_GUIDANCE_MIN, HY_GUIDANCE_MAX, HY_GUIDANCE_DEFAUT = 1.0, 10.0, 5.0
HY_FPS = 30.0
LICENCE_HY = {
    "id": "hy-motion",
    "nom": "Tencent HY-MOTION 1.0 Community License",
    "url": "https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/master/License.txt",
    "territoires_exclus": ["UE", "Royaume-Uni", "Corée du Sud"],
    "seuil_mau": 1_000_000,
}


def licence_hy() -> dict:
    """{acceptee, le} : la case de l'utilisateur pour HY-Motion (rangée dans DATA_ROOT/studio3d/animer.json)."""
    e = _lire()["licences"].get(LICENCE_HY["id"]) or {}
    return {"acceptee": e.get("acceptee") is True, "le": e.get("le")}


def accepter_licence_hy(acceptee: bool) -> dict:
    with _VERROU:
        d = _lire()
        lic = dict(d["licences"])
        if acceptee:
            lic[LICENCE_HY["id"]] = {"acceptee": True, "le": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                     "licence": LICENCE_HY["nom"]}
        else:
            lic.pop(LICENCE_HY["id"], None)
        d["licences"] = lic
        _ecrire(d)
    return licence_hy()


def devis_hy(modele: str) -> dict:
    from app.services import pricing
    return pricing.estimate({"kind": "hy_motion", "modele": modele})


def etat_hy() -> dict:
    return {"modeles": [{"id": m, "taille": v["taille"], "usd": v["usd"], "devis": devis_hy(m)}
                        for m, v in HY_MODELES.items()],
            "duree": {"min": HY_DUREE_MIN, "max": HY_DUREE_MAX, "pas": HY_DUREE_PAS},
            "guidance": {"min": HY_GUIDANCE_MIN, "max": HY_GUIDANCE_MAX, "defaut": HY_GUIDANCE_DEFAUT},
            "licence": {**LICENCE_HY, **licence_hy()}}


def modele_texte(body: dict) -> str:
    m = str((body or {}).get("modele") or "meshy")
    if m not in MODELES_TEXTE:
        raise ValueError("modèle : « meshy », « hy-motion » ou « hy-motion-fast »")
    return m


def valider_hy(body: dict) -> dict:
    """{modele, prompt, duree, guidance, seed, nom} propres, ou ValueError. Aucune dépense ici."""
    body = body or {}
    modele = modele_texte(body)
    if modele not in HY_MODELES:
        raise ValueError("modèle : « hy-motion » ou « hy-motion-fast » attendu")
    prompt = re.sub(r"\s+", " ", str(body.get("prompt") or "")).strip()
    if not prompt:
        raise ValueError("prompt : décris le mouvement (« marche prudente, regarde à gauche »)")
    if len(prompt) > PROMPT_MAX:
        raise ValueError(f"prompt : {PROMPT_MAX} caractères au plus")
    duree = body.get("duree")
    if isinstance(duree, bool) or not isinstance(duree, (int, float)) or not math.isfinite(duree):
        raise ValueError(f"durée : un nombre de secondes, de {HY_DUREE_MIN:g} à {HY_DUREE_MAX:g}")
    duree = float(duree)
    if not HY_DUREE_MIN <= duree <= HY_DUREE_MAX:
        raise ValueError(f"durée HY-Motion : de {HY_DUREE_MIN:g} à {HY_DUREE_MAX:g} s")
    g = body.get("guidance", HY_GUIDANCE_DEFAUT)
    if isinstance(g, bool) or not isinstance(g, (int, float)) or not HY_GUIDANCE_MIN <= g <= HY_GUIDANCE_MAX:
        raise ValueError(f"guidance : de {HY_GUIDANCE_MIN:g} à {HY_GUIDANCE_MAX:g}")
    seed = body.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2 ** 31):
        raise ValueError("graine : un entier de 0 à 2147483647")
    brut = str(body.get("nom") or "") or "_".join(prompt.split()[:4])
    nom = re.sub(r"[^A-Za-z0-9_-]+", "_", brut).strip("_")[:40] or "mouvement"
    return {"modele": modele, "prompt": prompt, "duree": duree, "guidance": float(g), "seed": seed, "nom": nom}


# ── le convertisseur : dict HY-Motion → BVH (pur, sans réseau) ──

# Les 22 os du corps SMPL dans l'ordre du code amont (joint_names.json), leur parent, leur décalage de repos en mètres
# (Y en haut, +Z devant, +X = gauche du personnage : la pose en T du modèle SMPL neutre), et le nom « Mixamo » donné
# dans le BVH pour que `mouvement_rig.role` les reconnaisse (sous leur nom SMPL, L_Hip serait refusé comme bassin
# latéral et L_Shoulder pris pour la clavicule).
SMPL_OS = [
    ("Pelvis", None, (0.0, 0.0, 0.0), "Hips"),
    ("L_Hip", 0, (0.0695, -0.0914, -0.0042), "LeftUpLeg"),
    ("R_Hip", 0, (-0.0677, -0.0905, -0.0043), "RightUpLeg"),
    ("Spine1", 0, (-0.0025, 0.1089, -0.0267), "Spine"),
    ("L_Knee", 1, (0.0343, -0.3752, -0.0045), "LeftLeg"),
    ("R_Knee", 2, (-0.0383, -0.3826, -0.0089), "RightLeg"),
    ("Spine2", 3, (0.0055, 0.1352, 0.0011), "Spine1"),
    ("L_Ankle", 4, (-0.0136, -0.3980, -0.0437), "LeftFoot"),
    ("R_Ankle", 5, (0.0158, -0.3984, -0.0423), "RightFoot"),
    ("Spine3", 6, (0.0015, 0.0529, 0.0254), "Spine2"),
    ("L_Foot", 7, (0.0264, -0.0558, 0.1193), "LeftToeBase"),
    ("R_Foot", 8, (-0.0254, -0.0481, 0.1233), "RightToeBase"),
    ("Neck", 9, (-0.0028, 0.2139, -0.0429), "Neck"),
    ("L_Collar", 9, (0.0788, 0.1218, -0.0341), "LeftShoulder"),
    ("R_Collar", 9, (-0.0818, 0.1188, -0.0386), "RightShoulder"),
    ("Head", 12, (0.0052, 0.0650, 0.0513), "Head"),
    ("L_Shoulder", 13, (0.0910, 0.0305, -0.0089), "LeftArm"),
    ("R_Shoulder", 14, (-0.0960, 0.0326, -0.0091), "RightArm"),
    ("L_Elbow", 16, (0.2596, -0.0128, -0.0275), "LeftForeArm"),
    ("R_Elbow", 17, (-0.2537, -0.0133, -0.0214), "RightForeArm"),
    ("L_Wrist", 18, (0.2493, 0.0090, -0.0012), "LeftHand"),
    ("R_Wrist", 19, (-0.2554, 0.0078, -0.0056), "RightHand"),
]
# le bout des os terminaux (End Site), en mètres
_BOUTS = {"Head": (0.0, 0.10, 0.0), "L_Foot": (0.0, 0.0, 0.04), "R_Foot": (0.0, 0.0, 0.04),
          "L_Wrist": (0.08, 0.0, 0.0), "R_Wrist": (-0.08, 0.0, 0.0)}
_CLES_ROT = (("rot6d", 6), ("rotations_6d", 6), ("poses", 3), ("axis_angle", 3), ("rotvec", 3),
             ("quat", 4), ("quaternions", 4), ("quat_wxyz", 4))
_CLES_TRANSL = ("transl", "trans", "root_translation", "translation")


def _profondeur_liste(v) -> int:
    d = 0
    while isinstance(v, list):
        d += 1
        if not v:
            break
        v = v[0]
    return d


def _sans_lot(x, profondeur: int):
    """Retire les dimensions de lot de taille 1 en tête ((1, L, …) → (L, …)) au-delà de `profondeur` niveaux."""
    while isinstance(x, list) and len(x) == 1 and _profondeur_liste(x) > profondeur:
        x = x[0]
    return x


def _forme(x) -> str:
    dims = []
    while isinstance(x, list):
        dims.append(len(x))
        if not x:
            break
        x = x[0]
    return "(" + ", ".join(str(d) for d in dims) + ")"


def _mat_6d(d):
    """rot6d → matrice 3×3 (lignes). Convention du code AMONT (hymotion/utils/geometry.py, relevé t405) : le vecteur
    est la matrice 3×2 des deux premières COLONNES aplatie ligne par ligne — a1 = (d0, d2, d4), a2 = (d1, d3, d5) —,
    orthonormalisée par Gram-Schmidt ; b1, b2, b3 sont les colonnes."""
    a1, a2 = (d[0], d[2], d[4]), (d[1], d[3], d[5])
    n1 = math.sqrt(sum(c * c for c in a1))
    if n1 < 1e-9:
        raise ValueError("rot6d dégénéré (première colonne nulle)")
    b1 = tuple(c / n1 for c in a1)
    p = sum(x * y for x, y in zip(b1, a2))
    u = tuple(y - p * x for x, y in zip(b1, a2))
    n2 = math.sqrt(sum(c * c for c in u))
    if n2 < 1e-9:
        raise ValueError("rot6d dégénéré (colonnes parallèles)")
    b2 = tuple(c / n2 for c in u)
    b3 = (b1[1] * b2[2] - b1[2] * b2[1], b1[2] * b2[0] - b1[0] * b2[2], b1[0] * b2[1] - b1[1] * b2[0])
    return ((b1[0], b2[0], b3[0]), (b1[1], b2[1], b3[1]), (b1[2], b2[2], b3[2]))


def _mat_axe_angle(v):
    x, y, z = v
    th = math.sqrt(x * x + y * y + z * z)
    if th < 1e-12:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    kx, ky, kz = x / th, y / th, z / th
    c, s, t = math.cos(th), math.sin(th), 1 - math.cos(th)
    return ((c + kx * kx * t, kx * ky * t - kz * s, kx * kz * t + ky * s),
            (ky * kx * t + kz * s, c + ky * ky * t, ky * kz * t - kx * s),
            (kz * kx * t - ky * s, kz * ky * t + kx * s, c + kz * kz * t))


def _mat_quat_wxyz(q):
    """Quaternion (w, x, y, z) — partie réelle EN TÊTE, comme `quaternion_to_matrix` du code amont."""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n < 1e-12:
        raise ValueError("quaternion nul")
    w, x, y, z = w / n, x / n, y / n, z / n
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))


def euler_zxy(m) -> tuple[float, float, float]:
    """(z, x, y) en degrés tels que M = Rz(z) · Rx(x) · Ry(y) — l'ordre des canaux « Zrotation Xrotation Yrotation »
    que `mouvement_rig.lire_bvh` compose de gauche à droite."""
    sx = max(-1.0, min(1.0, m[2][1]))
    x = math.asin(sx)
    if abs(sx) < 1 - 1e-9:
        z = math.atan2(-m[0][1], m[1][1])
        y = math.atan2(-m[2][0], m[2][2])
    else:                                   # blocage de cardan : y = 0, z porte tout
        y = 0.0
        z = math.atan2(m[1][0], m[0][0])
    return math.degrees(z), math.degrees(x), math.degrees(y)


def _rotations(motion: dict):
    """(série L × 22 matrices, nom de la représentation) ou ValueError au message lisible."""
    for cle, k in _CLES_ROT:
        if cle not in motion:
            continue
        brut = _sans_lot(motion[cle], 3)
        if not isinstance(brut, list) or not brut:
            raise ValueError(f"HY-Motion : « {cle} » vide ou illisible")
        conv = _mat_6d if k == 6 else _mat_axe_angle if k == 3 else _mat_quat_wxyz
        images = []
        for f, img in enumerate(brut):
            if isinstance(img, list) and len(img) == 22 * k and all(isinstance(v, (int, float)) for v in img):
                img = [img[j * k:(j + 1) * k] for j in range(22)]          # (L, 22·k) aplati
            if not (isinstance(img, list) and len(img) == 22
                    and all(isinstance(o, list) and len(o) == k for o in img)):
                raise ValueError(f"HY-Motion : « {cle} » de forme {_forme(brut)} — attendu (L, 22, {k})")
            try:
                vals = [[float(v) for v in o] for o in img]
            except (TypeError, ValueError):
                raise ValueError(f"HY-Motion : « {cle} » image {f} : nombres attendus") from None
            if not all(math.isfinite(v) for o in vals for v in o):
                raise ValueError(f"HY-Motion : « {cle} » image {f} : valeur non finie")
            try:
                images.append([conv(o) for o in vals])
            except ValueError as e:
                raise ValueError(f"HY-Motion : « {cle} » image {f} : {e}") from None
        return images, {6: "rot6d", 3: "axe-angle", 4: "quaternion"}[k]
    cles = ", ".join(sorted(str(c) for c in motion)[:8]) or "aucune"
    raise ValueError(f"HY-Motion : aucune rotation reconnue (clés lues : {cles}) — attendu « rot6d » (L, 22, 6), "
                     "« poses » axe-angle (L, 22, 3) ou « quat » (L, 22, 4)")


def hymotion_vers_bvh(motion, fps: float | None = None) -> str:
    """Le dict de HY-Motion → un BVH (centimètres, Y en haut, canaux de rotation Z X Y) que `mouvement_rig` lit et
    recible. Les rotations sont LOCALES à la pose en T de SMPL (os 0 = orientation globale) ; `transl` (mètres) est la
    position de la racine. Formes acceptées : rot6d (L,22,6), axe-angle (L,22,3), quaternion wxyz (L,22,4), avec ou
    sans dimension de lot 1 en tête, ou aplaties (L, 22·k) ; toute autre forme est refusée."""
    if isinstance(motion, (bytes, str)):
        try:
            motion = json.loads(motion)
        except ValueError:
            raise ValueError("HY-Motion : le mouvement rendu n'est pas du JSON") from None
    if not isinstance(motion, dict):
        raise ValueError("HY-Motion : un objet JSON est attendu (rot6d, transl…)")
    images, _rep = _rotations(motion)
    n = len(images)
    from app.services import mouvement_rig as MR
    if n > MR.MAX_IMAGES:
        raise ValueError(f"HY-Motion : {n} images ({MR.MAX_IMAGES} au plus)")
    transl = None
    for cle in _CLES_TRANSL:
        if cle in motion:
            t = _sans_lot(motion[cle], 2)
            if not (isinstance(t, list) and len(t) == n and all(isinstance(v, list) and len(v) == 3 for v in t)):
                raise ValueError(f"HY-Motion : « {cle} » de forme {_forme(t)} — attendu ({n}, 3)")
            try:
                transl = [tuple(float(c) for c in v) for v in t]
            except (TypeError, ValueError):
                raise ValueError(f"HY-Motion : « {cle} » : nombres attendus") from None
            if not all(math.isfinite(c) for v in transl for c in v):
                raise ValueError(f"HY-Motion : « {cle} » : valeur non finie")
            break
    if transl is None:
        transl = [(0.0, 0.0, 0.0)] * n
    fps = motion.get("fps") if fps is None else fps
    fps = HY_FPS if fps is None else fps
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 1 <= fps <= 240:
        raise ValueError("HY-Motion : cadence hors bornes (1 à 240 i/s)")
    enfants: dict[int, list[int]] = {}
    for i, (_n, p, _o, _m) in enumerate(SMPL_OS):
        if p is not None:
            enfants.setdefault(p, []).append(i)
    lignes, ordre = ["HIERARCHY"], []

    def cm(v):
        return " ".join(f"{100 * c:.4f}" for c in v)

    def ecrire(i, prof):
        nom_smpl, _p, off, nom = SMPL_OS[i]
        ind = "  " * prof
        lignes.append(f"{ind}{'ROOT' if prof == 0 else 'JOINT'} {nom}")
        lignes.append(f"{ind}{{")
        lignes.append(f"{ind}  OFFSET {cm(off if prof else (0, 0, 0))}")
        lignes.append(f"{ind}  CHANNELS " + ("6 Xposition Yposition Zposition Zrotation Xrotation Yrotation"
                                              if prof == 0 else "3 Zrotation Xrotation Yrotation"))
        ordre.append(i)
        for e in enfants.get(i, []):
            ecrire(e, prof + 1)
        if not enfants.get(i):
            lignes.extend([f"{ind}  End Site", f"{ind}  {{",
                           f"{ind}    OFFSET {cm(_BOUTS.get(nom_smpl, (0, 0.05, 0)))}", f"{ind}  }}"])
        lignes.append(f"{ind}}}")
    ecrire(0, 0)
    lignes.extend(["MOTION", f"Frames: {n}", f"Frame Time: {1 / float(fps):.6f}"])
    for f in range(n):
        vals = []
        for i in ordre:
            z, x, y = euler_zxy(images[f][i])
            if i == 0:
                vals.extend(100 * c for c in transl[f])
            vals.extend((z, x, y))
        lignes.append(" ".join(f"{v:.5f}" for v in vals))
    return "\n".join(lignes) + "\n"


async def _telecharger(url: str) -> bytes:
    import httpx
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


async def _mouvement_fal(res: dict):
    """Le mouvement rendu par fal : `motion_json` (un File {url}) — ou, à défaut, le dict déjà en ligne."""
    res = res if isinstance(res, dict) else {}
    mj = res.get("motion_json")
    if isinstance(mj, dict) and mj.get("url"):
        return await _telecharger(str(mj["url"]))
    if isinstance(mj, str) and mj.startswith(("http://", "https://")):
        return await _telecharger(mj)
    for cle in ("motion_json", "motion", "output"):
        if isinstance(res.get(cle), dict):
            return res[cle]
    raise RuntimeError("fal : HY-Motion n'a rendu aucun mouvement (motion_json absent)")


async def hy_motion_vers_mouvement(job: str, version: int, entree: dict, on_etat=None) -> dict:
    """fal HY-Motion (dict) → BVH rangé dans le job (origine « hy-motion ») → reciblé sur la version → une version de
    plus. `entree` sort de `valider_hy`. Rend {modele, source, version, clip, rapport}."""
    import fal_client
    from app.services import mouvement_rig as MR

    async def etat(**champs):
        if on_etat:
            await on_etat(champs)

    job = Path(str(job)).name
    m = HY_MODELES[entree["modele"]]
    args = {"prompt": entree["prompt"], "duration": entree["duree"], "guidance_scale": entree["guidance"],
            "output_format": "dict"}
    if entree.get("seed") is not None:
        args["seed"] = entree["seed"]
    await etat(etat="genere", modele=entree["modele"])
    try:
        res = await fal_client.subscribe_async(m["endpoint"], arguments=args, with_logs=False)
    except Exception as e:                          # noqa: BLE001 — le message de fal, sans la pile
        raise RuntimeError(f"fal.ai: {e}") from e
    brut = await _mouvement_fal(res)
    motion = json.loads(brut) if isinstance(brut, (bytes, str)) else brut
    bvh = hymotion_vers_bvh(motion).encode("utf-8")
    await etat(etat="recible", modele=entree["modele"])
    fiche = MR.ranger(job, f"{entree['nom']}.bvh", bvh, {
        "origine": "hy-motion", "modele": entree["modele"], "prompt": entree["prompt"],
        "duree_demandee": entree["duree"], "guidance": entree["guidance"],
        "seed": res.get("seed") if isinstance(res, dict) else None, "licence": LICENCE_HY["nom"]})
    r = _recibler_dans_version(job, version, fiche, entree["nom"], "hy-motion")
    return {"modele": entree["modele"], **r}


def _recibler_dans_version(job: str, version: int, fiche: dict, nom: str, origine: str) -> dict:
    """Le mouvement rangé `fiche` reciblé sur la version `version` → une version de plus (jamais un écrasement)."""
    from app.services import mesh_edit as ME
    from app.services import mesh_report
    from app.services import mouvement_rig as MR
    nom_v = "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"
    cible = mesh_report.job_dir(job) / nom_v
    if not cible.is_file():
        raise FileNotFoundError(f"{job}/{nom_v} introuvable")
    src = MR.lire_fichier(fiche["fichier"], (MR.dossier(job) / fiche["fichier"]).read_bytes())
    sortie, rapport = MR.appliquer(cible.read_bytes(), src, nom=nom)
    ecrite = ME.ecrire_version(job, sortie, operation="mouvement", detail={
        "depuis": {"version": int(version), "fichier": nom_v},
        "source": {"type": "fichier", "nom": fiche["fichier"], "origine": origine}, **rapport})
    return {"source": {"type": "fichier", "nom": fiche["fichier"]}, "version": ecrite.get("version"),
            "clip": rapport.get("clip"), "rapport": rapport}


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
