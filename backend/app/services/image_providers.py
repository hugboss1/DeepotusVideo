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
    # t182 (G0, 11/10/2026) : gpt-image-1-mini était servi par les routes
    # (chemin OpenAI) et tarifé, mais absent du registre — l'Atelier DA ne le
    # voyait pas.
    "gpt-image-1-mini": {"label": "GPT Image 1 mini (OpenAI)",
                         "needs": "OPENAI_API_KEY", "seeds": False},
    # t182 : modèles d'image fal « simples », servis par _fal_image_generate
    # (tableau FAL_IMAGES plus bas). Clé fal seule, facture fal.
    "nano-banana-2.1": {"label": "Nano Banana 2.1 (via fal)",
                        "needs": "FAL_KEY", "seeds": False},
    "flux-3": {"label": "FLUX 3 (via fal)", "needs": "FAL_KEY", "seeds": False},
    "seedream-5-pro": {"label": "Seedream 5 Pro (via fal)",
                       "needs": "FAL_KEY", "seeds": False},
    "ideogram-4.5": {"label": "Ideogram 4.5 (via fal)",
                     "needs": "FAL_KEY", "seeds": False},
    "qwen-image-3": {"label": "Qwen Image 3 (via fal)",
                     "needs": "FAL_KEY", "seeds": False},
    # rend un SVG (vectoriel) : texte → image seulement, pas de retouche
    "recraft-4.1-vecteur": {"label": "Recraft 4.1 vecteur SVG (via fal)",
                            "needs": "FAL_KEY", "seeds": False},
}

# id `-fal` → modèle OpenAI qu'il sert (endpoint fal dérivé du modèle)
_FAL_GPT = {"gpt-image-2-fal": "gpt-image-2",
            "gpt-image-2.5-flare-fal": "gpt-image-2.5-flare",
            "gpt-image-2.5-sunburst-fal": "gpt-image-2.5-sunburst"}
# `background: "transparent"` — par VOIE, d'après la doc de chacune (27/09) :
# fal l'accepte pour flare ET sunburst (t2i et edit, auto/transparent/opaque) ;
# la doc OpenAI ne le dit que de flare, sunburst direct reste donc fermé.
_TRANSPARENT_OK_FAL = ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst")
_TRANSPARENT_OK_OPENAI = ("gpt-image-2.5-flare",)


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
    """Générateurs des planches (raster) : un modèle vectoriel n'y est pas."""
    out = []
    for pid, meta in PROVIDERS.items():
        if (FAL_IMAGES.get(pid) or {}).get("svg"):
            continue
        if getattr(settings, meta["needs"], "").strip():
            out.append({"id": pid, "label": meta["label"],
                        "seeds": meta["seeds"]})
    return out


def _save_bytes(data: bytes, ext: str = ".png") -> str:
    fname = f"gen_{uuid4().hex[:8]}{ext}"
    (settings.images_path / fname).write_bytes(data)
    return fname


async def _download(urls: list[str], ext: str = ".png") -> list[str]:
    """`ext` : extension du fichier écrit (« .svg » pour un modèle
    vectoriel, t182) ; « .png » par défaut, comme avant."""
    saved = []
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=90.0) as c:
        for u in urls:
            r = await c.get(u)
            r.raise_for_status()
            saved.append(_save_bytes(r.content, ext))
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
        if background == "transparent" and model in _TRANSPARENT_OK_OPENAI:
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

REF_MAX = 9   # tâche #62 : fal ne documente aucun maximum pour `image_urls` (doc lue le 02/10) — 9 est notre prudence


def build_banana_request(prompt: str, size: str, n: int,
                         image_url: list[str] | str | None,
                         ratio: str | None = None,
                         pro: bool = False) -> tuple[str, dict]:
    """(model_id, arguments) fal pour Nano Banana. Exposé pur pour les tests.
    `ratio` (ex. "9:16") force le cadre de sortie d'un EDIT — par défaut
    l'edit suit le cadre de l'image d'entrée (leçon tests canons: un corps
    en pied chaîné sur un headshot 3:4 sort tassé ou coupé). `pro` vise
    fal-ai/nano-banana-pro (Gemini 3, mêmes arguments — doc fal du
    27/08/2026), au tarif de SA clé de prix."""
    endpoint = "fal-ai/nano-banana-pro" if pro else "fal-ai/nano-banana"
    # tâche #62 : une LISTE de références (une chaîne seule reste acceptée), ordre gardé, tronquée à REF_MAX
    urls = [image_url] if isinstance(image_url, str) else list(image_url or [])
    urls = [u for u in urls if u][:REF_MAX]
    if urls:
        args = {"prompt": prompt, "image_urls": urls,
                "num_images": n, "output_format": "png"}
        if ratio:
            args["aspect_ratio"] = ratio
        return (endpoint + "/edit", args)
    return (endpoint,
            {"prompt": prompt, "num_images": n, "output_format": "png",
             "aspect_ratio": _BANANA_ASPECT.get(size, "1:1")})


async def _banana_generate(prompt: str, size: str, n: int,
                           image_path: Path | list[Path] | None,
                           ratio: str | None = None,
                           pro: bool = False) -> list[str]:
    import fal_client
    chemins = list(image_path) if isinstance(image_path, (list, tuple)) else ([image_path] if image_path is not None else [])
    urls: list[str] = []
    if chemins:
        from app.services.fal_service import FalSeedanceClient
        for ch in chemins[:REF_MAX]:
            urls.append(await FalSeedanceClient.upload_image(ch))
    model, arguments = build_banana_request(prompt, size, n, urls, ratio,
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
    27/09/2026). `background="transparent"` part pour Flare et Sunburst
    (doc fal), jamais pour gpt-image-2."""
    args = {"prompt": prompt, "image_size": size, "quality": "high",
            "num_images": n, "output_format": "png"}
    if model.startswith("gpt-image-2.5-"):
        variante = model[len("gpt-image-2.5-"):]
        base = f"openai/gpt-image-2.5/{variante}"
        t2i = base + "/text-to-image"
        if background == "transparent" and model in _TRANSPARENT_OK_FAL:
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


# ───────────── modèles d'image fal « simples » (t182, G0) ─────────────

# Schémas relus le 11/10/2026 avec fal_schema.py (entrée) et l'openapi de la
# file fal (sortie : `images[]` de File pour les six).
# taille : "aspect" -> aspect_ratio (+ resolution) ; "image_size" -> le preset
# du projet tel quel (ce SONT les presets fal).
# multi : False quand le schéma n'a pas de `num_images` (flux-3, recraft) —
# n images = n appels.
# edit_champ : "image_urls" (liste) ou "image_url" (une image ; les autres
# partent en `reference_image_urls`, schéma d'ideogram/v4.5/edit).
# svg : la sortie est un SVG (content_type image/svg+xml) -> fichier « .svg ».
FAL_IMAGES = {
    "nano-banana-2.1": {"t2i": "google/nano-banana-2.1",
                        "edit": "google/nano-banana-2.1/edit",
                        "taille": "aspect", "resolution": "1K",
                        "extra": {"output_format": "png"}},
    "flux-3": {"t2i": "blackforestlabs/flux-3/text-to-image",
               "edit": "blackforestlabs/flux-3/edit-image",
               "taille": "aspect", "resolution": "1k", "multi": False,
               "extra": {"output_format": "png"}},
    "seedream-5-pro": {"t2i": "bytedance/seedream/v5/pro/text-to-image",
                       "edit": "bytedance/seedream/v5/pro/edit",
                       "taille": "image_size",
                       "extra": {"output_format": "png"}},
    "ideogram-4.5": {"t2i": "ideogram/v4.5", "edit": "ideogram/v4.5/edit",
                     "taille": "image_size", "edit_champ": "image_url",
                     # qualité ÉCRITE : c'est elle que la clé de prix chiffre
                     "extra": {"quality": "high"}},
    "qwen-image-3": {"t2i": "alibaba/qwen-image-3/text-to-image",
                     "edit": "alibaba/qwen-image-3/edit",
                     "taille": "image_size",
                     "extra": {"output_format": "png"}},
    "recraft-4.1-vecteur": {"t2i": "fal-ai/recraft/v4.1/text-to-vector",
                            "edit": None, "taille": "image_size",
                            "multi": False, "svg": True},
}


def build_fal_image_request(model: str, prompt: str, size: str,
                            image_urls: list[str],
                            n: int = 1) -> tuple[str, dict]:
    """(endpoint, arguments) pour un id de FAL_IMAGES. Pur : aucun réseau.
    ValueError si une image est donnée à un modèle sans retouche."""
    m = FAL_IMAGES[model]
    urls = [u for u in (image_urls or []) if u][:REF_MAX]
    edit = bool(urls)
    if edit and not m["edit"]:
        raise ValueError(f"{model} : pas de retouche (texte → image seulement).")
    args: dict = {"prompt": prompt}
    if m["taille"] == "aspect":
        args["aspect_ratio"] = _BANANA_ASPECT.get(size, "1:1")
        args["resolution"] = m["resolution"]
    else:
        args["image_size"] = size if size in _BANANA_ASPECT else "square_hd"
    if m.get("multi", True):
        args["num_images"] = max(1, int(n))
    args.update(m.get("extra", {}))
    if edit:
        if m.get("edit_champ") == "image_url":
            args["image_url"] = urls[0]
            if urls[1:]:
                args["reference_image_urls"] = urls[1:]
        else:
            args["image_urls"] = urls
    return (m["edit"] if edit else m["t2i"]), args


async def _fal_image_generate(model: str, prompt: str, size: str, n: int,
                              image_paths: list[Path] | None = None,
                              **kw) -> list[str]:
    """Couture des modèles FAL_IMAGES (les bancs l'espionnent) : téléverse
    les références, tire (n appels si le schéma n'a pas de `num_images`),
    télécharge. Un SVG est écrit en « .svg », jamais déguisé en PNG."""
    import fal_client
    m = FAL_IMAGES[model]
    if image_paths and not m["edit"]:      # refusé AVANT de téléverser
        raise ValueError(f"{model} : pas de retouche (texte → image seulement).")
    urls: list[str] = []
    if image_paths:
        from app.services.fal_service import FalSeedanceClient
        for ch in list(image_paths)[:REF_MAX]:
            urls.append(await FalSeedanceClient.upload_image(ch))
    endpoint, arguments = build_fal_image_request(model, prompt, size, urls, n)
    tirs = 1 if m.get("multi", True) else max(1, int(n))
    trouves: list[str] = []
    for _ in range(tirs):
        result = await fal_client.subscribe_async(endpoint,
                                                  arguments=arguments)
        res = result or {}
        imgs = res.get("images") or ([res["image"]] if res.get("image") else [])
        trouves += [im.get("url") for im in imgs if im.get("url")]
    if not trouves:
        raise RuntimeError(f"{model} (fal) returned no images: {result}")
    return await _download(trouves, ".svg" if m.get("svg") else ".png")


# ─────────────────────────── façade unifiée ───────────────────────────

async def generate(provider: str, prompt: str, size: str, n: int = 1,
                   seed: int | None = None,
                   image_path: Path | None = None,
                   ratio: str | None = None,
                   background: str | None = None,
                   image_paths: list[Path] | None = None) -> dict:
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
    # t182 : AVANT le cas nano-banana — « nano-banana-2.1 » n'est pas
    # « nano-banana » et ne doit jamais retomber sur l'ancien endpoint.
    if provider in FAL_IMAGES:
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY manquante (Réglages).")
        refs = list(image_paths) if image_paths else (
            [image_path] if image_path is not None else [])
        try:
            imgs = await _fal_image_generate(provider, prompt, size, n,
                                             image_paths=refs)
        except ValueError as e:      # recraft : pas de retouche
            raise RuntimeError(str(e))
        return {"images": imgs, "seed": None}
    if provider in ("nano-banana", "nano-banana-pro"):
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY manquante (Réglages).")
        refs = list(image_paths) if image_paths else image_path     # tâche #62 : plusieurs références
        imgs = await _banana_generate(prompt, size, n, refs, ratio,
                                      pro=(provider == "nano-banana-pro"))
        return {"images": imgs, "seed": None}
    if provider.startswith("gpt-image") or provider.startswith("dall-e"):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY manquante (Réglages).")
        imgs = await _openai_generate(provider, prompt, size, n, image_path,
                                      background=background)
        return {"images": imgs, "seed": None}
    raise RuntimeError(f"Générateur inconnu: {provider}")
