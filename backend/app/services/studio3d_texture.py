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
            "resolutions": list(RESOLUTIONS), "prompt_defaut": PROMPT_DEFAUT,
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

def decoder_image(valeur, png_seul: bool = False) -> tuple[bytes, str]:
    """Une image en data URL (ou base64 nu) → (octets, extension). ValueError si vide, illisible, trop lourde ou d'un
    type autre que PNG/JPEG (PNG seul pour une capture du canevas)."""
    s = str(valeur or "").strip()
    if not s:
        raise ValueError("image absente")
    if s.startswith("data:"):
        s = s.split(",", 1)[1] if "," in s else ""
    if len(s) > IMAGE_MAX * 4 // 3 + 8:
        raise ValueError(f"image trop lourde (> {IMAGE_MAX // (1024 * 1024)} Mo)")
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
        "style": r.get("style"), "bibliotheque": src.name})
    return entree

