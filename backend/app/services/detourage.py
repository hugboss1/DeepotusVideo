# -*- coding: utf-8 -*-
"""t186 (G4, plan « Génération IA enrichie », 12/10/2026) — LE registre unique du détourage, image ET vidéo.

Une entrée par modèle : sa nature (`detourage_image` / `detourage_video`), sa voie (« local » ou « fal »), son
endpoint fal, ses arguments FIXES, si elle exige un SUJET nommé (`prompt`), sa clé de prix (pricing.DEFAULTS) et
son unité de facturation. Le catalogue (catalogue_ia, natures detourage_*), le devis (pricing.estimate, kind
« detourage ») et tous les sites qui détourent (/images/process, /matte, sprites, Card Forge, Studio3D, décor
Avatar) lisent CE registre — aucun ne recopie un endpoint ni un paramètre.

SCHÉMAS FAL RELUS LE 12/10/2026 (openapi « queue » de chaque endpoint) ; aucun autre nom de paramètre n'est
inventé ici. Les entrées image envoient `image_url`, les vidéo `video_url`.
  · Bria RMBG 2.0 : `image_url` SEUL — avec un `prompt`, la même route facture 0,03 $ au lieu de 0,018 $.
  · VEED rapide accepte aussi `subject_is_person` et `refine_foreground_edges` : laissés au défaut (refine ON),
    d'où le tarif prudent « refine ON » de 0,012 $ par tranche de 30 images.
  · SAM 3 / SAM 3.1 / Bria extract-object : le SUJET (prompt) est requis côté nous — « dites quel sujet garder ».

PRIX (12/10/2026, pages des modèles) : Bria RMBG 0,018 $/image ; Ideogram 0,01 $/image ; SAM 3 image
0,005 $/image ; rembg (fal) 0,003 $/image ; Bria vidéo v3 0,05 $/s ; VEED rapide 0,012 $/30 images ; Pixelcut
vidéo 0,022 $/30 images ; SAM 3.1 vidéo 0,01 $/16 images. À MESURER (0 $ tant qu'un premier tir n'a pas été lu sur
le tableau de bord fal) : BiRefNet v2 image et vidéo (la page n'affiche que « $0 per compute second »), Pixelcut
image (la page n'affiche que le prix de la version vidéo), FeyNobg, Bria extract-object.

Les appels réseau passent par les TROIS seams de matte_service (`_upload`, `_fal_subscribe`, `_download`),
appelés par le MODULE au moment de l'appel : un banc qui les remplace dans matte_service couvre aussi ce
module — un seul jeu de coutures remplaçables pour tout le détourage."""
from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.i18n import Refus   # t192 : refus traduisibles (texte = le français)

IMAGE, VIDEO = "detourage_image", "detourage_video"


def _e(nature, label, voie, endpoint=None, fixes=None, prompt=False, prix=None, unite="image", ext=".png",
       apercu=None):
    return {"nature": nature, "label": label, "voie": voie, "endpoint": endpoint, "fixes": dict(fixes or {}),
            "prompt": bool(prompt), "prix": prix, "unite": unite, "ext": ext, "apercu": apercu}


# les ARGS_FIXED du matte BiRefNet vidéo (matte_service, schéma relu le 06/10) : LUS, jamais recopiés
from app.services.matte_service import ARGS_FIXED as _BIREFNET_VIDEO  # noqa: E402

# ORDRE = ordre des sélecteurs : les locales (gratuites) d'abord.
REGISTRE: dict[str, dict] = {
    "local-rembg": _e(IMAGE, "rembg (local, gratuit)", "local"),
    "local-chroma": _e(IMAGE, "Fond uni / chroma (local)", "local"),
    "birefnet-v2": _e(IMAGE, "BiRefNet v2", "fal", "fal-ai/birefnet/v2",
                      {"model": "General Use (Heavy)", "operating_resolution": "2048x2048",
                       "refine_foreground": True, "output_format": "png"}, prix="birefnet_image_usd"),
    "bria-rmbg": _e(IMAGE, "Bria RMBG 2.0", "fal", "fal-ai/bria/background/remove", prix="bria_rmbg_usd"),
    "pixelcut": _e(IMAGE, "Pixelcut", "fal", "pixelcut/background-removal", {"output_format": "rgba"},
                   prix="pixelcut_rmbg_usd"),
    "ideogram-rmbg": _e(IMAGE, "Ideogram", "fal", "fal-ai/ideogram/remove-background", prix="ideogram_rmbg_usd"),
    "feynobg": _e(IMAGE, "FeyNobg", "fal", "fal-ai/feynobg", prix="feynobg_usd"),
    "sam3-sujet": _e(IMAGE, "SAM 3 — garder un sujet nommé", "fal", "fal-ai/sam-3/image",
                     {"apply_mask": True, "output_format": "png"}, prompt=True, prix="sam3_image_usd"),
    "bria-objet": _e(IMAGE, "Bria — extraire un objet nommé", "fal", "bria/extract-object",
                     {"remove_background": True, "autocrop": False}, prompt=True, prix="bria_objet_usd"),
    "rembg-fal": _e(IMAGE, "rembg (fal, ancien)", "fal", "fal-ai/imageutils/rembg", prix="rembg_api_usd"),
    "birefnet-v2-video": _e(VIDEO, "BiRefNet v2 vidéo", "fal", "fal-ai/birefnet/v2/video",
                            dict(_BIREFNET_VIDEO, model="General Use (Light)"),
                            prix="birefnet_video_usd_per_s", unite="s", ext=".mov", apercu="birefnet-v2"),
    "bria-video-v3": _e(VIDEO, "Bria VRMBG 3.0", "fal", "bria/video/background-removal/v3",
                        {"background_color": "Transparent", "output_container_and_codec": "mov_proresks",
                         "preserve_audio": True}, prix="bria_video_usd_per_s", unite="s", ext=".mov",
                        apercu="bria-rmbg"),
    "veed-video-rapide": _e(VIDEO, "VEED rapide", "fal", "veed/video-background-removal/fast",
                            {"output_codec": "vp9"}, prix="veed_rmbg_usd_per_30f", unite="30 images", ext=".webm",
                            apercu="birefnet-v2"),
    "pixelcut-video": _e(VIDEO, "Pixelcut vidéo", "fal", "pixelcut/video-background-removal",
                         {"background": "transparent", "output_format": "webm_vp9"},
                         prix="pixelcut_video_usd_per_30f", unite="30 images", ext=".webm", apercu="pixelcut"),
    "sam31-video": _e(VIDEO, "SAM 3.1 — suivre un sujet nommé", "fal", "fal-ai/sam-3-1/video",
                      {"apply_mask": True, "video_output_type": "VP9 (.webm)"}, prompt=True,
                      prix="sam31_video_usd_per_16f", unite="16 images", ext=".webm", apercu="sam3-sujet"),
}
DEFAUT_VIDEO = "birefnet-v2-video"
# taille des tranches de facturation par unité (pricing.estimate)
TRANCHES = {"30 images": 30, "16 images": 16}


def ids(nature: str) -> list[str]:
    """Les ids d'une nature, dans l'ordre du registre."""
    return [k for k, e in REGISTRE.items() if e["nature"] == nature]


def entree(mid: str, nature: str | None = None) -> dict:
    """L'entrée d'un id — ValueError nommée si l'id est inconnu ou d'une autre nature."""
    e = REGISTRE.get(str(mid or ""))
    if e is None:
        raise ValueError(f"modèle de détourage inconnu : {str(mid)[:40]!r} "
                         f"(connus : {', '.join(ids(nature) if nature else REGISTRE)})")
    if nature and e["nature"] != nature:
        quoi = "une image" if nature == IMAGE else "une vidéo"
        raise ValueError(f"{e['label']} ne détoure pas {quoi} (connus : {', '.join(ids(nature))})")
    return e


def cle_manquante(mid: str) -> str | None:
    """Le NOM de la clé qu'exige ce modèle quand elle n'est pas posée (« FAL_KEY »), None sinon (voie locale,
    ou clé présente). Les routes en font un 503 AVANT toute garde de dépense."""
    e = REGISTRE.get(str(mid or ""))
    if e is None or e["voie"] != "fal":
        return None
    return None if str(settings.FAL_KEY or "").strip() else "FAL_KEY"


def sujet_de(mid: str, sujet) -> str | None:
    """Le sujet nettoyé ; ValueError (Refus, t192) si le modèle l'exige et qu'il manque."""
    s = str(sujet or "").strip()[:200] or None
    if REGISTRE.get(str(mid or ""), {}).get("prompt") and not s:
        from app.i18n import Nom
        raise Refus("ia.detour.sujet_manquant", modele=Nom(mid, REGISTRE[mid]['label']))
    return s


def build_request(mid: str, url: str, prompt=None) -> tuple[str, dict]:
    """(endpoint, arguments) de l'appel fal. ValueError : id inconnu, modèle LOCAL (aucune requête fal), ou
    modèle à sujet sans sujet. Les arguments fixes d'abord, puis l'URL d'entrée, puis le sujet — et le sujet
    SEULEMENT pour un modèle qui l'exige (Bria RMBG facturerait plus cher avec un prompt)."""
    e = entree(mid)
    if e["voie"] == "local":
        raise ValueError(f"{e['label']} est un détourage LOCAL : aucune requête fal")
    s = sujet_de(mid, prompt)
    args = dict(e["fixes"])
    args["video_url" if e["nature"] == VIDEO else "image_url"] = url
    if e["prompt"]:
        args["prompt"] = s
    return e["endpoint"], args


def url_image(res) -> str | None:
    """L'URL de l'image détourée : `image.url`, sinon le premier `images[].url` (deux formes circulent)."""
    if not isinstance(res, dict):
        return None
    im = res.get("image")
    if isinstance(im, dict) and im.get("url"):
        return str(im["url"])
    if isinstance(im, str) and im.startswith("http"):
        return im
    for x in res.get("images") or []:
        if isinstance(x, dict) and x.get("url"):
            return str(x["url"])
    return None


def url_video(res) -> str | None:
    """L'URL de la vidéo détourée : `video.url`, sinon `video_url`, sinon le premier `videos[].url`."""
    if not isinstance(res, dict):
        return None
    v = res.get("video")
    if isinstance(v, dict) and v.get("url"):
        return str(v["url"])
    if isinstance(res.get("video_url"), str):
        return res["video_url"]
    for x in res.get("videos") or []:
        if isinstance(x, dict) and x.get("url"):
            return str(x["url"])
    return None


def op_cout(mid: str, images: int = 1, secondes: float | None = None, fps: float | None = None) -> dict:
    """L'op de devis (pricing.estimate, kind « detourage ») d'une demande : `images` pour une image (ou des
    frames de sprite), `secondes` (+ `fps`) pour une vidéo."""
    op = {"kind": "detourage", "modele": str(mid)}
    if secondes is not None:
        op["secondes"] = float(secondes)
        if fps:
            op["fps"] = float(fps)
    else:
        op["images"] = max(1, int(images or 1))
    return op


# ── voies locales ───────────────────────────────────────────────────────────
def _local_rembg(src: Path) -> bytes:
    """Le rembg python, comme /images/process method « local » et sprite_service._rembg_local_bytes."""
    try:
        from rembg import remove as _remove
    except ImportError:
        raise Refus("ia.detour.rembg_absent")
    return _remove(src.read_bytes())


def _local_chroma(src: Path, dest: Path) -> None:
    """Le détourage par couleur de fond (pixel_ops.chroma_key, celui des sprites, tolérance 28)."""
    from PIL import Image
    from app.services.pixel_ops import chroma_key
    with Image.open(src) as im:
        out, ok = chroma_key(im, 28)
    if not ok:
        raise Refus("ia.detour.chroma_pas_uni")
    out.save(dest, format="PNG")


def _en_png(dest: Path) -> None:
    """Un fournisseur peut rendre un webp ou un jpeg malgré la demande : le fichier rangé est un PNG RGBA."""
    from PIL import Image
    with Image.open(dest) as im:
        im.load()
        if im.format == "PNG" and im.mode == "RGBA":
            return
        im2 = im.convert("RGBA")
    im2.save(dest, format="PNG")


async def detourer_image(mid: str, chemin, prompt=None, dossier=None) -> str:
    """Détoure UNE image par le modèle `mid` (nature detourage_image) et range un PNG `gen_xxxxxxxx.png` dans
    `dossier` (défaut : le dossier des images de la Bibliothèque) ; rend son NOM. PAYANT pour une voie fal :
    la route a passé la clé (503) et la garde des plafonds AVANT. ValueError : id, nature, sujet, voie locale
    indisponible ; RuntimeError : réponse fal sans image."""
    from app.services import matte_service as MT
    e = entree(mid, IMAGE)
    src = Path(chemin)
    if not src.is_file():
        raise ValueError("image source introuvable")
    d = Path(dossier) if dossier else Path(settings.images_path)
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"gen_{uuid4().hex[:8]}.png"
    if mid == "local-rembg":
        data = await asyncio.to_thread(_local_rembg, src)
        dest.write_bytes(data)
        return dest.name
    if mid == "local-chroma":
        await asyncio.to_thread(_local_chroma, src, dest)
        return dest.name
    build_request(mid, "", prompt)          # appel à blanc : le refus du sujet (ValueError) AVANT l'envoi du fichier
    url = await MT._upload(src)
    endpoint, args = build_request(mid, url, prompt)
    res = await MT._fal_subscribe(endpoint, args)
    out = url_image(res)
    if not out:
        cles = ", ".join(map(str, res)) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"fal.ai ({e['label']}) : aucune image dans la réponse (clés : {cles})")
    await MT._download(out, dest)
    await asyncio.to_thread(_en_png, dest)
    return dest.name
