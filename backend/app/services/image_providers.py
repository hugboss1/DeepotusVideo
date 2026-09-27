"""v1.23 (Atelier DA) — générateurs d'images interchangeables.

Le projet choisit SON générateur (atelier_settings.image_provider) pour les
planches de la bible; chaque provider expose les deux opérations dont le
pipeline a besoin:
- t2i   : texte → image (panneau maître sans référence)
- edit  : image + texte → image (chaînage d'identité / référence de style)

Honnêteté déterminisme: seul FLUX expose un seed (recette rejouable au pixel).
Pour GPT Image et Nano Banana, l'homogénéité chapitre après chapitre repose
sur (1) le chaînage par image-édition, (2) les prompts de recette conservés,
(3) le style global injecté partout — c'est indiqué dans l'UI.
"""
import base64
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

PROVIDERS = {
    "flux": {"label": "FLUX (fal) — seeds, recettes exactes",
             "needs": "FAL_KEY", "seeds": True},
    "gpt-image-2": {"label": "GPT Image 2 (OpenAI)",
                    "needs": "OPENAI_API_KEY", "seeds": False},
    "gpt-image-1": {"label": "GPT Image 1 (OpenAI)",
                    "needs": "OPENAI_API_KEY", "seeds": False},
    "nano-banana": {"label": "Nano Banana (Gemini, via fal)",
                    "needs": "FAL_KEY", "seeds": False},
    "nano-banana-pro": {"label": "Nano Banana Pro (Gemini 3, via fal)",
                        "needs": "FAL_KEY", "seeds": False},
    # le MÊME modèle que gpt-image-2, servi et facturé PAR fal (endpoint
    # openai/gpt-image-2) : pas de clé OpenAI sur ce chemin, et le filtre
    # de sécurité côté OpenAI direct n'est pas la porte.
    "gpt-image-2-fal": {"label": "GPT Image 2 (OpenAI, via fal)",
                        "needs": "FAL_KEY", "seeds": False},
    # GPT Image 2.5 (doc OpenAI et fal lue le 27/09/2026) : deux variantes,
    # chacune servie en direct (clé OpenAI) ET par fal (clé fal) — quatre
    # entrées, quatre factures. Flare seul accepte le fond transparent.
    "gpt-image-2.5-flare": {"label": "GPT Image 2.5 Flare (OpenAI)",
                            "needs": "OPENAI_API_KEY", "seeds": False},
    "gpt-image-2.5-sunburst": {"label": "GPT Image 2.5 Sunburst (OpenAI)",
                               "needs": "OPENAI_API_KEY", "seeds": False},
    "gpt-image-2.5-flare-fal": {"label": "GPT Image 2.5 Flare (via fal)",
                                "needs": "FAL_KEY", "seeds": False},
    "gpt-image-2.5-sunburst-fal": {"label": "GPT Image 2.5 Sunburst (via fal)",
                                   "needs": "FAL_KEY", "seeds": False},
}

# id `-fal` → modèle OpenAI qu'il sert (endpoint fal dérivé du modèle)
_FAL_GPT = {"gpt-image-2-fal": "gpt-image-2",
            "gpt-image-2.5-flare-fal": "gpt-image-2.5-flare",
            "gpt-image-2.5-sunburst-fal": "gpt-image-2.5-sunburst"}
# seuls ces modèles acceptent `background: "transparent"`
_TRANSPARENT_OK = ("gpt-image-2.5-flare",)


def via_facade(model: str) -> bool:
    """Vrai si l'id doit passer par `generate` (et non par un chemin maison
    d'une route) : tout id du registre servi par fal (hors FLUX, que les
    routes servent elles-mêmes) et les GPT Image 2.5 directs, dont la qualité
    et le fond sont posés ici. Testé AVANT tout préfixe `gpt-image`."""
    meta = PROVIDERS.get(model)
    if not meta or model == "flux":
        return False
    return meta["needs"] == "FAL_KEY" or model.startswith("gpt-image-2.5")


def missing_key(model: str) -> str | None:
    """Nom de la clé manquante pour un id du registre, sinon None."""
    meta = PROVIDERS.get(model)
    if not meta:
        return None
    return None if str(getattr(settings, meta["needs"], "") or "").strip() \
        else meta["needs"]

_OPENAI_SIZE = {"portrait_16_9": "1024x1536", "portrait_4_3": "1024x1536",
                "landscape_16_9": "1536x1024", "landscape_4_3": "1536x1024",
                "square": "1024x1024", "square_hd": "1024x1024"}
_BANANA_ASPECT = {"portrait_16_9": "9:16", "portrait_4_3": "3:4",
                  "landscape_16_9": "16:9", "landscape_4_3": "4:3",
                  "square": "1:1", "square_hd": "1:1"}


def available() -> list[dict]:
    out = []
    for pid, meta in PROVIDERS.items():
        if getattr(settings, meta["needs"], "").strip():
            out.append({"id": pid, "label": meta["label"],
                        "seeds": meta["seeds"]})
    return out


def _save_bytes(data: bytes) -> str:
    fname = f"gen_{uuid4().hex[:8]}.png"
    (settings.images_path / fname).write_bytes(data)
    return fname


async def _download(urls: list[str]) -> list[str]:
    saved = []
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=90.0) as c:
        for u in urls:
            r = await c.get(u)
            r.raise_for_status()
            saved.append(_save_bytes(r.content))
    return saved


# ─────────────────────────── OpenAI GPT Image ───────────────────────────

def build_openai_request(model: str, prompt: str, size: str, n: int,
                         has_image: bool,
                         background: str | None = None) -> tuple[str, dict]:
    """(url, payload_gen) — payload des /generations; les /edits partent en
    multipart construit à l'appel. Exposé pur pour les tests.
    GPT Image 2.5 : la qualité `high` est ÉCRITE (c'est elle que la table de
    tarifs chiffre) ; `background="transparent"` n'est transmis qu'à Flare,
    avec `output_format` png. Les modèles d'avant gardent leur payload."""
    osize = _OPENAI_SIZE.get(size, "1024x1024")
    payload = {"model": model, "prompt": prompt, "n": n, "size": osize}
    if model.startswith("gpt-image-2.5"):
        payload["quality"] = "high"
        if background == "transparent" and model in _TRANSPARENT_OK:
            payload["background"] = "transparent"
            payload["output_format"] = "png"
    if has_image:
        return ("https://api.openai.com/v1/images/edits", payload)
    return ("https://api.openai.com/v1/images/generations", payload)


async def _openai_generate(model: str, prompt: str, size: str, n: int,
                           image_path: Path | None,
                           background: str | None = None) -> list[str]:
    url, payload = build_openai_request(model, prompt, size, n,
                                        image_path is not None,
                                        background=background)
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=240.0) as c:
        if image_path is not None:
            files = {"image": (image_path.name, image_path.read_bytes(),
                               "image/png")}
            r = await c.post(url, headers=headers, data=payload, files=files)
        else:
            r = await c.post(url, headers=headers, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI image {r.status_code}: {r.text[:200]}")
    saved, urls = [], []
    for it in (r.json() or {}).get("data", []):
        if it.get("b64_json"):
            saved.append(_save_bytes(base64.b64decode(it["b64_json"])))
        elif it.get("url"):
            urls.append(it["url"])
    saved += await _download(urls)
    return saved


# ───────────────────── Nano Banana (Gemini via fal) ─────────────────────

def build_banana_request(prompt: str, size: str, n: int,
                         image_url: str | None,
                         ratio: str | None = None,
                         pro: bool = False) -> tuple[str, dict]:
    """(model_id, arguments) fal pour Nano Banana. Exposé pur pour les tests.
    `ratio` (ex. "9:16") force le cadre de sortie d'un EDIT — par défaut
    l'edit suit le cadre de l'image d'entrée (leçon tests canons: un corps
    en pied chaîné sur un headshot 3:4 sort tassé ou coupé). `pro` vise
    fal-ai/nano-banana-pro (Gemini 3, mêmes arguments — doc fal du
    27/08/2026), au tarif de SA clé de prix."""
    endpoint = "fal-ai/nano-banana-pro" if pro else "fal-ai/nano-banana"
    if image_url:
        args = {"prompt": prompt, "image_urls": [image_url],
                "num_images": n, "output_format": "png"}
        if ratio:
            args["aspect_ratio"] = ratio
        return (endpoint + "/edit", args)
    return (endpoint,
            {"prompt": prompt, "num_images": n, "output_format": "png",
             "aspect_ratio": _BANANA_ASPECT.get(size, "1:1")})


async def _banana_generate(prompt: str, size: str, n: int,
                           image_path: Path | None,
                           ratio: str | None = None,
                           pro: bool = False) -> list[str]:
    import fal_client
    image_url = None
    if image_path is not None:
        from app.services.fal_service import FalSeedanceClient
        image_url = await FalSeedanceClient.upload_image(image_path)
    model, arguments = build_banana_request(prompt, size, n, image_url, ratio,
                                            pro)
    result = await fal_client.subscribe_async(model, arguments=arguments)
    urls = [im.get("url") for im in (result or {}).get("images", [])
            if im.get("url")]
    if not urls:
        raise RuntimeError(f"Nano Banana returned no images: {result}")
    return await _download(urls)


# ───────────────────── GPT Image 2 (OpenAI, via fal) ─────────────────────

def build_fal_gpt_request(prompt: str, size: str, n: int,
                          image_url: str | None,
                          model: str = "gpt-image-2",
                          background: str | None = None) -> tuple[str, dict]:
    """(model_id, arguments) fal pour GPT Image servi par fal. Exposé pur
    pour les tests. Les identifiants de taille du projet SONT les presets
    fal (`portrait_4_3`…) : ils passent tels quels. La qualité `high` est
    ÉCRITE plutôt qu'héritée du défaut : c'est elle que la table de tarifs
    chiffre, et un défaut fal qui changerait ne doit pas changer la facture
    en silence.
    `model` : `gpt-image-2` (endpoint `openai/gpt-image-2`, inchangé) ou
    `gpt-image-2.5-{flare|sunburst}` (endpoints
    `openai/gpt-image-2.5/{variante}/{text-to-image|edit}`, doc fal du
    27/09/2026). `background="transparent"` ne part que pour Flare."""
    args = {"prompt": prompt, "image_size": size, "quality": "high",
            "num_images": n, "output_format": "png"}
    if model.startswith("gpt-image-2.5-"):
        variante = model[len("gpt-image-2.5-"):]
        base = f"openai/gpt-image-2.5/{variante}"
        t2i = base + "/text-to-image"
        if background == "transparent" and model in _TRANSPARENT_OK:
            args["background"] = "transparent"
    else:
        base = "openai/gpt-image-2"
        t2i = base
    if image_url:
        args["image_urls"] = [image_url]
        return (base + "/edit", args)
    return (t2i, args)


async def _fal_gpt_generate(prompt: str, size: str, n: int,
                            image_path: Path | None,
                            model: str = "gpt-image-2",
                            background: str | None = None) -> list[str]:
    import fal_client
    image_url = None
    if image_path is not None:
        from app.services.fal_service import FalSeedanceClient
        image_url = await FalSeedanceClient.upload_image(image_path)
    endpoint, arguments = build_fal_gpt_request(prompt, size, n, image_url,
                                                model=model,
                                                background=background)
    result = await fal_client.subscribe_async(endpoint, arguments=arguments)
    urls = [im.get("url") for im in (result or {}).get("images", [])
            if im.get("url")]
    if not urls:
        raise RuntimeError(f"{model} (fal) returned no images: {result}")
    return await _download(urls)


# ─────────────────────────── façade unifiée ───────────────────────────

async def generate(provider: str, prompt: str, size: str, n: int = 1,
                   seed: int | None = None,
                   image_path: Path | None = None,
                   ratio: str | None = None,
                   background: str | None = None) -> dict:
    """Génère via le provider choisi. Retour: {"images":[filenames],
    "seed": int|None} (seed None = provider non déterministe). `ratio`
    (ex. "9:16") force le cadre des EDITS (image_path fourni) — sinon le
    modèle edit suit le cadre de l'image d'entrée. `background`
    ("transparent") n'est honoré que par GPT Image 2.5 Flare."""
    # LES CHEMINS FAL D'ABORD : les « gpt-image-…-fal » commencent par
    # « gpt-image » — testés après le préfixe OpenAI, ils partiraient chez
    # OpenAI avec la mauvaise clé ET la mauvaise facture.
    if provider in _FAL_GPT:
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY manquante (Réglages).")
        imgs = await _fal_gpt_generate(prompt, size, n, image_path,
                                       model=_FAL_GPT[provider],
                                       background=background)
        return {"images": imgs, "seed": None}
    if provider in ("nano-banana", "nano-banana-pro"):
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY manquante (Réglages).")
        imgs = await _banana_generate(prompt, size, n, image_path, ratio,
                                      pro=(provider == "nano-banana-pro"))
        return {"images": imgs, "seed": None}
    if provider.startswith("gpt-image") or provider.startswith("dall-e"):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY manquante (Réglages).")
        imgs = await _openai_generate(provider, prompt, size, n, image_path,
                                      background=background)
        return {"images": imgs, "seed": None}
    raise RuntimeError(f"Générateur inconnu: {provider}")
