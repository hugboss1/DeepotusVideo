"""Catalogue unique des modèles appelables, par NATURE d'appel, avec leurs
deux voies (clé individuelle / clé fal). Source des sélecteurs de l'app.

t182 (G0, plan « Génération IA enrichie », 11/10/2026). Gratuit à lire ; ne
fait aucun appel réseau. Chaque entrée dit : sa voie (fal, openai…), la clé
qui la sert, si cette clé est posée (`dispo`), son prix unitaire (`usd`,
`unite`) et son JUMEAU — le même modèle servi par l'autre voie
(gpt-image-2 <-> gpt-image-2-fal). Un modèle sans clé reste PRÉSENT
(dispo=False) : c'est au sélecteur de le griser, pas au catalogue de le
cacher. Un prix à 0 se dit « prix à mesurer », jamais « gratuit ».
"""
from app.config import settings
from app.services import pricing as P

CLES = {"fal": "FAL_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY", "meshy": "MESHY_API_KEY",
        "heygen": "HEYGEN_API_KEY", "local": None}
NATURES = ("image",)            # étendu par les lots suivants (G2, G4…G7)

_SOURCES = {}                   # nature -> fonction () -> list[dict] brutes

PRIX_A_MESURER = "prix à mesurer"


def source(nature):
    """Décorateur : inscrit la fonction qui rend les entrées brutes d'une
    nature (id, label, voie, usd, unite, jumeau…)."""
    def deco(fn):
        _SOURCES[nature] = fn
        return fn
    return deco


def _dispo(voie: str) -> bool:
    cle = CLES.get(voie)
    return True if cle is None else bool(str(getattr(settings, cle, "") or "").strip())


@source("image")
def _images() -> list[dict]:
    """Une entrée par id de pricing._IMAGE_MODELS (raster) puis de
    pricing._IMAGE_MODELS_VECTEUR (SVG) ; `sortie` le dit (« raster » /
    « svg ») pour que seuls les écrans vectoriels proposent les seconds. Le
    jumeau se lit dans image_providers._FAL_GPT (id `-fal` -> id direct)."""
    from app.services import image_providers as IP
    p = P.load()
    inverse = {v: k for k, v in IP._FAL_GPT.items()}
    out = []
    registre = [(mid, spec, "raster") for mid, spec in P._IMAGE_MODELS.items()]
    registre += [(mid, spec, "svg") for mid, spec in P._IMAGE_MODELS_VECTEUR.items()]
    for mid, (label, voie, cle_prix), sortie in registre:
        try:
            usd = float(p.get(cle_prix, P.DEFAULTS.get(cle_prix, 0.0)) or 0.0)
        except (TypeError, ValueError):
            usd = 0.0
        jumeau = IP._FAL_GPT.get(mid) or inverse.get(mid)
        fal = IP.FAL_IMAGES.get(mid) or {}
        out.append({"id": mid, "label": label, "voie": voie, "usd": usd,
                    "unite": "image", "jumeau": jumeau,
                    "note": "" if usd else PRIX_A_MESURER,
                    "edit": not (fal and not fal.get("edit")),
                    "sortie": sortie})
    return out


def lister(nature: str) -> list[dict]:
    """Toutes les entrées d'une nature, disponibles OU NON. KeyError si la
    nature est inconnue (la route en fait un 400)."""
    if nature not in _SOURCES:
        raise KeyError(nature)
    out = []
    for e in _SOURCES[nature]():
        e = dict(e)
        e["nature"] = nature
        e["cle"] = CLES.get(e["voie"])
        e["dispo"] = _dispo(e["voie"])
        out.append(e)
    return out
