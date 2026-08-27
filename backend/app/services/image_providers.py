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
}

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
                         has_image: bool) -> tuple[str, dict]:
    """(url, payload_gen) — payload des /generations; les /edits partent en
    multipart construit à l'appel. Exposé pur pour les tests."""
    osize = _OPENAI_SIZE.get(size, "1024x1024")
    if has_image:
        return ("https://api.openai.com/v1/images/edits",
                {"model": model, "prompt": prompt, "n": n, "size": osize})
    return ("https://api.openai.com/v1/images/generations",
            {"model": model, "prompt": prompt, "n": n, "size": osize})


async def _openai_generate(model: str, prompt: str, size: str, n: int,
                           image_path: Path | None) -> list[str]:
    url, payload = build_openai_request(model, prompt, size, n,
                                        image_path is not None)
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
                          image_url: str | None) -> tuple[str, dict]:
    """(model_id, arguments) fal pour GPT Image 2 servi par fal. Exposé pur
    pour les tests. Les identifiants de taille du projet SONT les presets
    fal (`portrait_4_3`…) : ils passent tels quels. La qualité `high` est
    ÉCRITE plutôt qu'héritée du défaut : c'est elle que la table de tarifs
    chiffre, et un défaut fal qui changerait ne doit pas changer la facture
    en silence."""
    args = {"prompt": prompt, "image_size": size, "quality": "high",
            "num_images": n, "output_format": "png"}
    if image_url:
        args["image_urls"] = [image_url]
        return ("openai/gpt-image-2/edit", args)
    return ("openai/gpt-image-2", args)


async def _fal_gpt_generate(prompt: str, size: str, n: int,
                            image_path: Path | None) -> list[str]:
    import fal_client
    image_url = None
    if image_path is not None:
        from app.services.fal_service import FalSeedanceClient
        image_url = await FalSeedanceClient.upload_image(image_path)
    model, arguments = build_fal_gpt_request(prompt, size, n, image_url)
    result = await fal_client.subscribe_async(model, arguments=arguments)
    urls = [im.get("url") for im in (result or {}).get("images", [])
            if im.get("url")]
    if not urls:
        raise RuntimeError(f"GPT Image 2 (fal) returned no images: {result}")
    return await _download(urls)


# ─────────────────────────── façade unifiée ───────────────────────────

async def generate(provider: str, prompt: str, size: str, n: int = 1,
                   seed: int | None = None,
                   image_path: Path | None = None,
                   ratio: str | None = None) -> dict:
    """Génère via le provider choisi. Retour: {"images":[filenames],
    "seed": int|None} (seed None = provider non déterministe). `ratio`
    (ex. "9:16") force le cadre des EDITS (image_path fourni) — sinon le
    modèle edit suit le cadre de l'image d'entrée."""
    # LES CHEMINS FAL D'ABORD : « gpt-image-2-fal » commence par « gpt-image »
    # — testé après le préfixe OpenAI, il partirait chez OpenAI avec la
    # mauvaise clé ET la mauvaise facture.
    if provider == "gpt-image-2-fal":
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY manquante (Réglages).")
        imgs = await _fal_gpt_generate(prompt, size, n, image_path)
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
        imgs = await _openai_generate(provider, prompt, size, n, image_path)
        return {"images": imgs, "seed": None}
    raise RuntimeError(f"Générateur inconnu: {provider}")
