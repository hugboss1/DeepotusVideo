# -*- coding: utf-8 -*-
"""t393 (31/10/2026) — écran TEXTURE du 3D Studio, volet 1/2 : références d'image et retexture IA.

Ce que fait l'écran (relevé de Sorceress, §4 de l'inventaire) : on CAPTURE le modèle ouvert sous une vue et un
éclairage choisis, cette capture part comme image SOURCE d'une retouche chez un modèle d'image de notre registre
(`image_providers`, les mêmes que /api/images/process op « edit ») avec un prompt facultatif et, en option, une
planche de STYLE téléversée ; l'image rendue devient une RÉFÉRENCE, rangée avec le job. La RETEXTURE IA envoie le
maillage à Meshy (`asset3d_service.texturer_asset3d`, la même passe que POST /api/assets/3d/{job}/texturer) avec la
référence choisie et/ou un texte de style ; elle écrit une NOUVELLE version, jamais un écrasement.

Les références vivent dans le dossier du job : `outputs/assets3d/<job>/texture_refs/` (images + `refs.json`). La
copie que le modèle d'image a déjà rangée dans la Bibliothèque (gen_*.png) y reste aussi.

Ce module ne dépense rien par lui-même SAUF `generer_reference` (l'appel au modèle d'image) ; les routes
(`app.api.studio3d_texture_routes`) posent devant lui, dans l'ordre : clé (503) → entrées (400) → `confirme_cout`
(409, avec le devis) → `max_usd` (409) → plafonds (402).

t394 (volet 2/2, TEXTURE AUTO) : un LOT de N captures (une par vue d'une disposition de 4 à 18 vues) part chez le même
modèle d'image — un seul devis (N × une image), une seule garde des plafonds sur le total, puis N appels — et chaque
image rendue devient une référence qui garde sa POSE ; le navigateur les projette sur l'atlas UV (projection.js).
L'atlas peint revient ici : `ecrire_texture_projetee` réécrit le GLB (Python pur) avec ce PNG pour couleur de base,
et la route en fait une NOUVELLE version (`mesh_edit.ecrire_version`, operation « texture_projection »). Gratuit.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings

# Les modèles d'image proposés, dans l'ordre de préférence (relevé §5 de l'api-3d) : Nano Banana 2 en tête s'il
# entre un jour au registre (« best alignment » chez Sorceress), puis ceux que le registre sert déjà en retouche.
PREFERES = ["nano-banana-2", "nano-banana-pro", "nano-banana-2.1", "nano-banana", "gpt-image-2-fal",
            "seedream-5-pro", "gpt-image-2"]
# ratio de l'écran → préréglage de taille du projet (ce SONT les presets fal ; image_providers les traduit)
RATIOS = {"1:1": "square_hd", "16:9": "landscape_16_9", "9:16": "portrait_16_9", "4:3": "landscape_4_3",
          "3:4": "portrait_4_3"}
RESOLUTIONS = ("1K", "2K", "4K")
# la résolution n'est un réglage QUE pour les modèles qui la prennent ; le multiplicateur de prix (doc fal de
# fal-ai/nano-banana-pro/edit relue pour le relevé du 31/10 : 1K et 2K au même prix, 4K × 2). Les autres : 1K seule.
MULT_RES = {"nano-banana-pro": {"1K": 1, "2K": 1, "4K": 2}}
RESOLUTIONS_MESHY = ("2k", "4k", "8k")
PROMPT_MAX = 1000
IMAGE_MAX = 15 * 1024 * 1024
VUES = {"face", "dos", "gauche", "droite", "dessus", "dessous", "avant_droite", "avant_gauche", "arriere_droite",
        "arriere_gauche", "libre"}
ECLAIRAGES = {"sans", "plat", "doux", "trois", "vif"}
SORTES = {"generee", "style"}

# envoyé quand le champ reste vide, et chargé par « Charger le prompt par défaut » (une seule source, en anglais :
# c'est la langue que les modèles d'image suivent le mieux)
PROMPT_DEFAUT = (
    "Turn this untextured 3D render into a fully textured reference image of the SAME object: keep exactly the same "
    "silhouette, proportions, pose, framing and camera angle. Add believable materials, colours and fine surface "
    "detail. Even, flat studio lighting with no cast shadows and no baked highlights, plain neutral background, "
    "no text.")

# « Débruiter » (retouche IA de la projection, sur devis) : l'atlas peint part comme image source du même modèle
PROMPT_DEBRUITER = (
    "This image is a UV texture atlas of a 3D model. Clean it up: remove noise, blotches, smears and seams while "
    "keeping EXACTLY the same layout, island shapes, positions, colours and details. Do not move, add or remove "
    "anything, do not add lighting or shadows, keep the background as it is.")

# t394 : les dispositions de la texture auto (relevé Sorceress §4) et les bornes de l'atlas
DISPOSITIONS = (4, 6, 8, 10, 12, 16, 18)
ATLAS_MAX = 48 * 1024 * 1024          # un atlas 4096² en PNG dépasse les 15 Mo d'une capture
ATLAS_COTE = (64, 8192)

_ID = re.compile(r"^[a-f0-9]{8,32}$")
_SIGNATURES = ((b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"))


# ── le registre des modèles ──────────────────────────────────────────────────

def _ip():
    from app.services import image_providers as IP
    return IP


def ids_modeles() -> list[str]:
    IP = _ip()
    return [m for m in PREFERES if m in IP.PROVIDERS and not IP.est_vectoriel(m)]


def resolutions(modele: str) -> list[str]:
    return list(MULT_RES.get(modele, {"1K": 1}))


def op_image(modele: str, resolution: str = "1K") -> dict:
    """L'op chiffré par la grille (pricing.estimate) et la garde : un 4K compte comme deux images (même $)."""
    return {"kind": "image", "n": int(MULT_RES.get(modele, {}).get(resolution, 1)), "model": modele}


def op_lot(modele: str, resolution: str, vues: int) -> dict:
    """Un lot de texture auto : `vues` images, chiffrées et gardées EN UNE FOIS (le total)."""
    return {"kind": "image", "n": int(vues) * int(MULT_RES.get(modele, {}).get(resolution, 1)), "model": modele}


def devis_lot(modele: str, resolution: str, vues: int) -> dict:
    from app.services import pricing
    e = pricing.estimate(op_lot(modele, resolution, vues))
    return {"action": "lot", "modele": modele, "resolution": resolution, "vues": int(vues),
            "usd": round(float(e["total_usd"]), 4), "usd_vue": devis_image(modele, resolution)["usd"],
            "lignes": e.get("breakdown") or []}


def op_retexture(resolution: str = "2k") -> dict:
    return {"kind": "asset3d_texture", "texture_resolution": resolution, "pbr": True}


def devis_image(modele: str, resolution: str = "1K") -> dict:
    from app.services import pricing
    e = pricing.estimate(op_image(modele, resolution))
    return {"action": "generer", "modele": modele, "resolution": resolution, "usd": round(float(e["total_usd"]), 4),
            "lignes": e.get("breakdown") or []}


def devis_retexture(resolution: str = "2k") -> dict:
    from app.services import meshy_service as MS, pricing
    e = pricing.estimate(op_retexture(resolution))
    return {"action": "retexturer", "resolution": resolution, "usd": round(float(e["total_usd"]), 4),
            "credits": MS.credits_retexture(resolution), "lignes": e.get("breakdown") or []}


def modeles() -> dict:
    """Ce que montre la colonne de gauche. Un modèle sans clé RESTE choisissable (`cle_ok` le dit, le 503 n'arrive
    qu'au lancement) ; le défaut est le premier de l'ordre de préférence."""
    IP = _ip()
    out = []
    for m in ids_modeles():
        out.append({"id": m, "label": IP.PROVIDERS[m]["label"], "cle": IP.PROVIDERS[m]["needs"],
                    "cle_ok": IP.missing_key(m) is None, "resolutions": resolutions(m),
                    "usd": devis_image(m, "1K")["usd"],
                    # les GPT Image servis par fal ou OpenAI ne prennent qu'UNE image : la planche de style n'y part pas
                    "multi_refs": m not in getattr(IP, "_FAL_GPT", {}) and not m.startswith("gpt-image")})
    return {"modeles": out, "defaut": out[0]["id"] if out else None, "ratios": list(RATIOS),
            "resolutions": list(RESOLUTIONS), "prompt_defaut": PROMPT_DEFAUT, "prompt_debruiter": PROMPT_DEBRUITER,
            "dispositions": list(DISPOSITIONS),
            "retexture": {"resolutions": list(RESOLUTIONS_MESHY),
                          "devis": {r: devis_retexture(r) for r in RESOLUTIONS_MESHY}}}


def cle_manquante_image(modele: str) -> str | None:
    return _ip().missing_key(modele)


def cle_manquante_meshy() -> str | None:
    """Le nom de la clé qui manque pour une retexture (Meshy texture, fal transporte le maillage), sinon None."""
    from app.services import meshy_service as MS
    if not MS.mock_enabled() and not (settings.MESHY_API_KEY or "").strip():
        return "MESHY_API_KEY"
    if not (settings.FAL_KEY or "").strip():
        return "FAL_KEY"
    return None


# ── le dossier des références ────────────────────────────────────────────────

def job_dir(job: str) -> Path:
    return settings.outputs_path / "assets3d" / Path(str(job)).name


def job_existe(job: str) -> bool:
    d = job_dir(job)
    return bool(str(job)) and Path(str(job)).name == str(job) and d.is_dir() and (d / "model.glb").is_file()


def _dossier(job: str) -> Path:
    return job_dir(job) / "texture_refs"


def _index(job: str) -> Path:
    return _dossier(job) / "refs.json"


def _lire(job: str) -> list[dict]:
    p = _index(job)
    if not p.is_file():
        return []
    try:
        l = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [r for r in l if isinstance(r, dict) and _ID.match(str(r.get("id") or ""))] if isinstance(l, list) else []


def _url(job: str, rid: str) -> str:
    return f"/api/studio3d/texture/{Path(str(job)).name}/reference/{rid}"


def references(job: str) -> list[dict]:
    """Les références du job dont le fichier existe encore, du plus récent au plus ancien, chacune avec son URL."""
    d = _dossier(job)
    out = [{**r, "url": _url(job, r["id"])} for r in _lire(job) if (d / str(r.get("fichier") or "")).is_file()]
    out.sort(key=lambda r: (str(r.get("cree_le") or ""), r["id"]), reverse=True)
    return out


def chemin_reference(job: str, rid: str) -> Path:
    """Le fichier d'une référence ; FileNotFoundError si l'id est mal formé, inconnu ou son fichier absent."""
    if not _ID.match(str(rid or "")):
        raise FileNotFoundError(f"référence inconnue : {str(rid)[:40]}")
    r = next((x for x in _lire(job) if x["id"] == rid), None)
    p = _dossier(job) / Path(str((r or {}).get("fichier") or "")).name if r else None
    if not p or not p.is_file():
        raise FileNotFoundError(f"référence inconnue : {rid}")
    return p


def _ranger(job: str, octets: bytes, ext: str, meta: dict) -> dict:
    d = _dossier(job)
    d.mkdir(parents=True, exist_ok=True)
    rid = uuid4().hex[:12]
    nom = f"ref_{rid}{ext}"
    (d / nom).write_bytes(octets)
    entree = {"id": rid, "fichier": nom, "cree_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), **meta}
    l = _lire(job)
    l.append(entree)
    tmp = _index(job).with_suffix(".tmp")
    tmp.write_text(json.dumps(l, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_index(job))
    return {**entree, "url": _url(job, rid)}


# ── les entrées ──────────────────────────────────────────────────────────────

def decoder_image(valeur, png_seul: bool = False, max_octets: int = IMAGE_MAX) -> tuple[bytes, str]:
    """Une image en data URL (ou base64 nu) → (octets, extension). ValueError si vide, illisible, trop lourde ou d'un
    type autre que PNG/JPEG (PNG seul pour une capture du canevas)."""
    s = str(valeur or "").strip()
    if not s:
        raise ValueError("image absente")
    if s.startswith("data:"):
        s = s.split(",", 1)[1] if "," in s else ""
    if len(s) > max_octets * 4 // 3 + 8:
        raise ValueError(f"image trop lourde (> {max_octets // (1024 * 1024)} Mo)")
    try:
        octets = base64.b64decode(s, validate=True)
    except (ValueError, TypeError):
        raise ValueError("image illisible (base64 attendu)") from None
    for sig, ext in _SIGNATURES:
        if octets.startswith(sig):
            if png_seul and ext != ".png":
                break
            return octets, ext
    raise ValueError("une image PNG est attendue" if png_seul else "une image PNG ou JPEG est attendue")


def valider_generation(job: str, body: dict) -> dict:
    """Les réglages d'une génération de référence, normalisés ; ValueError (400) ou FileNotFoundError (404)."""
    if not job_existe(job):
        raise FileNotFoundError(f"modèle 3D inconnu : {Path(str(job)).name}")
    modele = str(body.get("modele") or "")
    resolution = str(body.get("resolution") or "1K").upper()
    if resolution not in resolutions(modele):
        raise ValueError(f"{modele} ne prend pas la résolution {resolution} (permises : {', '.join(resolutions(modele))})")
    ratio = str(body.get("ratio") or "1:1")
    if ratio not in RATIOS:
        raise ValueError(f"ratio inconnu : {ratio[:12]} (permis : {', '.join(RATIOS)})")
    prompt = str(body.get("prompt") or "").strip()
    if len(prompt) > PROMPT_MAX:
        raise ValueError(f"prompt trop long ({len(prompt)} > {PROMPT_MAX} caractères)")
    vue = str(body.get("vue") or "libre")
    eclairage = str(body.get("eclairage") or "doux")
    if vue not in VUES or eclairage not in ECLAIRAGES:
        raise ValueError("vue ou éclairage inconnu")
    capture, _ = decoder_image(body.get("capture"), png_seul=True)
    style = body.get("style") or None
    if style is not None:
        chemin_reference(job, str(style))         # FileNotFoundError → 404
    return {"modele": modele, "resolution": resolution, "ratio": ratio, "prompt": prompt, "vue": vue,
            "eclairage": eclairage, "capture": capture, "style": style}


def _nombre(v, quoi: str, bas: float, haut: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} : un nombre est attendu") from None
    if not (bas <= x <= haut):
        raise ValueError(f"{quoi} hors bornes ({bas} à {haut})")
    return x


def valider_lot(job: str, body: dict) -> list[dict]:
    """Un lot de texture auto → une génération validée par vue (la capture et sa POSE), dans l'ordre des vues.
    Les réglages communs (modèle, résolution, prompt, éclairage) sont ceux d'une génération seule, ratio 1:1 (le
    cadre carré des caméras de projection). ValueError (400) ou FileNotFoundError (404)."""
    captures = body.get("captures")
    if not isinstance(captures, list) or len(captures) not in DISPOSITIONS:
        raise ValueError(f"captures : une liste de {', '.join(map(str, DISPOSITIONS))} vues est attendue")
    if body.get("disposition", len(captures)) != len(captures):
        raise ValueError(f"disposition {str(body.get('disposition'))[:8]} : {len(captures)} captures reçues")
    lot = uuid4().hex[:12]
    out = []
    for i, c in enumerate(captures):
        if not isinstance(c, dict) or not isinstance(c.get("pose"), dict):
            raise ValueError(f"vue {i + 1} : {{capture, pose}} attendu")
        p = c["pose"]
        pose = {"azimut": _nombre(p.get("azimut"), f"vue {i + 1} : azimut", -360, 720),
                "elevation": _nombre(p.get("elevation"), f"vue {i + 1} : élévation", -90, 90),
                "zoom": _nombre(p.get("zoom", 1), f"vue {i + 1} : zoom", 0.25, 8),
                "decalage": _nombre(p.get("decalage", 0), f"vue {i + 1} : décalage", -2, 2)}
        r = valider_generation(job, {**body, "ratio": "1:1", "vue": "libre", "capture": c.get("capture"), "style": None})
        r["meta"] = {"lot": lot, "index": i, "vues": len(captures), "pose": pose}
        out.append(r)
    return out


def valider_retexture(job: str, body: dict) -> dict:
    if not job_existe(job):
        raise FileNotFoundError(f"modèle 3D inconnu : {Path(str(job)).name}")
    resolution = str(body.get("resolution") or "2k").lower()
    if resolution not in RESOLUTIONS_MESHY:
        raise ValueError(f"resolution doit être {', '.join(RESOLUTIONS_MESHY)}")
    prompt = str(body.get("prompt") or "").strip()
    if len(prompt) > 600:
        raise ValueError(f"texte de style trop long ({len(prompt)} > 600 caractères, limite de Meshy)")
    ref = body.get("reference") or None
    chemin = chemin_reference(job, str(ref)) if ref else None
    if not chemin and not prompt:
        raise ValueError("une référence d'image ou un texte de style est nécessaire")
    return {"resolution": resolution, "prompt": prompt, "reference": ref, "chemin": chemin}


def ajouter_style(job: str, image) -> dict:
    """Range une planche de style téléversée (gratuit)."""
    if not job_existe(job):
        raise FileNotFoundError(f"modèle 3D inconnu : {Path(str(job)).name}")
    octets, ext = decoder_image(image)
    return _ranger(job, octets, ext, {"sorte": "style"})


# ── la dépense : un appel au modèle d'image ──────────────────────────────────

async def _tirer(modele: str, prompt: str, ratio: str, resolution: str, chemins: list[Path]) -> list[str]:
    """L'APPEL PAYANT (les bancs le remplacent) : la capture (et la planche de style) chez le modèle d'image → les
    noms des images rangées dans la Bibliothèque. Nano Banana Pro en 2K/4K passe par son endpoint avec `resolution`
    (la façade du registre ne la transmet pas) ; tout le reste passe par la façade, comme /images/process « edit »."""
    IP = _ip()
    size = RATIOS[ratio]
    if modele == "nano-banana-pro" and resolution != "1K":
        import fal_client
        from app.services.fal_service import FalSeedanceClient
        urls = [await FalSeedanceClient.upload_image(c) for c in chemins[:IP.REF_MAX]]
        endpoint, args = IP.build_banana_request(prompt, size, 1, urls, ratio, pro=True)
        args["resolution"] = resolution
        res = await fal_client.subscribe_async(endpoint, arguments=args)
        trouvees = [im.get("url") for im in (res or {}).get("images", []) if isinstance(im, dict) and im.get("url")]
        if not trouvees:
            raise RuntimeError(f"Nano Banana Pro n'a rendu aucune image : {str(res)[:200]}")
        return await IP._download(trouvees[:1])
    plusieurs = chemins if len(chemins) > 1 else None
    out = await IP.generate(modele, prompt, size, 1, image_path=chemins[0], image_paths=plusieurs, ratio=ratio)
    return list(out.get("images") or [])


async def generer_reference(job: str, r: dict) -> dict:
    """Capture → modèle d'image → référence rangée avec le job. `r` vient de `valider_generation`. Lève RuntimeError
    (le fournisseur a échoué : 502 pour la route)."""
    d = _dossier(job)
    d.mkdir(parents=True, exist_ok=True)
    capture = d / f"capture_{uuid4().hex[:12]}.png"
    capture.write_bytes(r["capture"])
    chemins = [capture]
    if r.get("style"):
        chemins.append(chemin_reference(job, r["style"]))
    noms = await _tirer(r["modele"], r["prompt"] or PROMPT_DEFAUT, r["ratio"], r["resolution"], chemins)
    src = settings.images_path / Path(str(noms[0] if noms else "")).name
    if not noms or not src.is_file():
        raise RuntimeError(f"{r['modele']} n'a rendu aucune image")
    entree = _ranger(job, src.read_bytes(), src.suffix.lower() or ".png", {
        "sorte": "generee", "modele": r["modele"], "resolution": r["resolution"], "ratio": r["ratio"],
        "prompt": r["prompt"], "vue": r["vue"], "eclairage": r["eclairage"], "capture": capture.name,
        "style": r.get("style"), "bibliotheque": src.name, **(r.get("meta") or {})})
    return entree


# ── t394 : l'atlas peint devient la couleur de base d'une NOUVELLE version ───

def dimensions_png(octets: bytes) -> tuple[int, int]:
    """(largeur, hauteur) lues dans l'en-tête IHDR ; ValueError si ce n'est pas un PNG lisible."""
    import struct
    if len(octets) < 24 or not octets.startswith(_SIGNATURES[0][0]) or octets[12:16] != b"IHDR":
        raise ValueError("une image PNG est attendue")
    return struct.unpack(">II", octets[16:24])


def decoder_atlas(valeur) -> tuple[bytes, int, int]:
    octets, _ = decoder_image(valeur, png_seul=True, max_octets=ATLAS_MAX)
    lg, ht = dimensions_png(octets)
    if not (ATLAS_COTE[0] <= lg <= ATLAS_COTE[1] and ATLAS_COTE[0] <= ht <= ATLAS_COTE[1]):
        raise ValueError(f"atlas {lg}×{ht} : chaque côté entre {ATLAS_COTE[0]} et {ATLAS_COTE[1]} px")
    return octets, lg, ht


_SOURCES_EXT = ("EXT_texture_webp", "KHR_texture_basisu", "MSFT_texture_dds", "EXT_texture_avif")


def _image_de_texture(tex: dict):
    if isinstance(tex.get("source"), int):
        return tex["source"]
    for e in _SOURCES_EXT:
        src = ((tex.get("extensions") or {}).get(e) or {}).get("source")
        if isinstance(src, int):
            return src
    return None


def ecrire_texture_projetee(data: bytes, png: bytes) -> tuple[bytes, dict]:
    """Le GLB `data` avec `png` pour couleur de base (Python pur, aucune géométrie touchée).

    - une seule image de couleur de base dans le fichier : elle est REMPLACÉE (nouvelle vue de tampon PNG, les
      sources webp/basis des textures qui la lisent retirées) ;
    - aucune : une image, une texture et un échantillonneur sont ajoutés, et chaque matériau d'une primitive qui a
      des UV (TEXCOORD_0) la prend — une primitive à UV sans matériau en reçoit un ;
    - plusieurs : ValueError (l'atlas peint n'en couvre qu'une).
    La couleur de base des matériaux touchés passe au blanc (alpha gardé) : la projection a déjà cuit leur teinte.
    L'atlas est peint dans les UV n° 0 : `texCoord` et `KHR_texture_transform` de l'info de texture sont retirés."""
    from app.services.mesh_edit import ecrire_glb, lire_glb
    doc, binc = lire_glb(data)
    buffers = doc.get("buffers") or []
    if buffers and "uri" in buffers[0]:
        raise ValueError("GLB à tampon externe : non géré")
    materiaux = doc.setdefault("materials", [])
    textures = doc.get("textures") or []
    infos = {}
    for i, m in enumerate(materiaux):
        info = (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
        if isinstance(info, dict) and isinstance(info.get("index"), int) and info["index"] < len(textures):
            infos[i] = info
    images = {_image_de_texture(textures[info["index"]]) for info in infos.values()} - {None}
    if len(images) > 1:
        raise ValueError(f"{len(images)} textures de couleur de base dans ce modèle : la projection n'en peint qu'une")
    prims = [p for me in doc.get("meshes") or [] for p in me.get("primitives") or []]
    a_uv = [p for p in prims if "TEXCOORD_0" in (p.get("attributes") or {})]
    if not a_uv:
        raise ValueError("ce modèle n'a pas de coordonnées UV (TEXCOORD_0) : rien où peindre l'atlas")
    # le PNG au bout du tampon, aligné sur 4 octets
    binc = bytes(binc) + b"\x00" * (-len(binc) % 4)
    vues = doc.setdefault("bufferViews", [])
    vues.append({"buffer": 0, "byteOffset": len(binc), "byteLength": len(png)})
    binc += png
    if not buffers:
        doc["buffers"] = buffers = [{}]
    buffers[0]["byteLength"] = len(binc)
    neuve = {"bufferView": len(vues) - 1, "mimeType": "image/png", "name": "texture_projection"}
    if images:
        idx = images.pop()
        doc["images"][idx] = neuve
        touches = sorted(i for i, info in infos.items() if _image_de_texture(textures[info["index"]]) == idx)
        for t in textures:
            if _image_de_texture(t) == idx:
                t["source"] = idx
                for e in _SOURCES_EXT:
                    (t.get("extensions") or {}).pop(e, None)
                if "extensions" in t and not t["extensions"]:
                    del t["extensions"]
        mode = "remplacee"
    else:
        doc.setdefault("images", []).append(neuve)
        doc.setdefault("samplers", []).append({"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497})
        doc.setdefault("textures", []).append({"source": len(doc["images"]) - 1, "sampler": len(doc["samplers"]) - 1})
        t = len(doc["textures"]) - 1
        lies = set()
        for p in a_uv:
            if not isinstance(p.get("material"), int):
                materiaux.append({"name": "texture_projection",
                                  "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.8}})
                p["material"] = len(materiaux) - 1
            lies.add(p["material"])
        for i in lies:
            materiaux[i].setdefault("pbrMetallicRoughness", {})["baseColorTexture"] = {"index": t}
        touches = sorted(lies)
        mode = "ajoutee"
    for i in touches:
        pbr = materiaux[i].setdefault("pbrMetallicRoughness", {})
        info = pbr["baseColorTexture"]
        info.pop("texCoord", None)
        (info.get("extensions") or {}).pop("KHR_texture_transform", None)
        if "extensions" in info and not info["extensions"]:
            del info["extensions"]
        f = pbr.get("baseColorFactor")
        if isinstance(f, list) and len(f) == 4:
            pbr["baseColorFactor"] = [1.0, 1.0, 1.0, f[3]]
    # une extension de source d'image que plus aucune texture n'emploie sort des listes
    for e in _SOURCES_EXT:
        if not any(e in (t.get("extensions") or {}) for t in doc.get("textures") or []):
            for cle in ("extensionsUsed", "extensionsRequired"):
                if e in (doc.get(cle) or []):
                    doc[cle].remove(e)
                    if not doc[cle]:
                        del doc[cle]
    return ecrire_glb(doc, binc), {"texture": mode, "materiaux": touches}

