"""Catalogue unique des modèles appelables, par NATURE d'appel, avec leurs
deux voies (clé individuelle / clé fal). Source des sélecteurs de l'app.

t182 (G0, plan « Génération IA enrichie », 11/10/2026). Gratuit à lire ; ne
fait aucun appel réseau. Chaque entrée dit : sa voie (fal, openai…), la clé
qui la sert, si cette clé est posée (`dispo`), son prix unitaire (`usd`,
`unite`) et son JUMEAU — le même modèle servi par l'autre voie
(gpt-image-2 <-> gpt-image-2-fal). Un modèle sans clé reste PRÉSENT
(dispo=False) : décision de l'utilisateur (11/10/2026), il reste CHOISISSABLE
dans les sélecteurs, avec la mention « clé X à ajouter dans Réglages » ; le
tir est refusé en 503 (avant toute dépense) tant que la clé manque.

Champs codés (jamais de texte français : l'écran traduit) :
- `note` : "" ou "a_mesurer" — prix inconnu (usd == 0). Le front affiche
  dzT("ia.prix.a_mesurer") (« prix à mesurer » / "price to be measured"),
  jamais « gratuit ».
- `sortie` : "raster" ou "svg" (image_providers.est_vectoriel) — seuls les
  écrans vectoriels proposent un modèle "svg".
- `edit` : le modèle accepte une image d'entrée (retouche).
"""
from app.config import settings
from app.services import pricing as P

CLES = {"fal": "FAL_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY", "meshy": "MESHY_API_KEY",
        "heygen": "HEYGEN_API_KEY", "local": None}
_SOURCES = {}                   # nature -> fonction () -> list[dict] brutes

NOTE_A_MESURER = "a_mesurer"     # code ; libellé : dzT("ia.prix.a_mesurer")
# t183 (G1) : le libellé d'ÉCRAN d'un modèle, quand il diffère de celui de la
# ligne de coût de pricing._IMAGE_MODELS (« FLUX image ») : c'est le libellé de
# /image-models `models` (« FLUX schnell »), que les sélecteurs affichent et que
# la pastille de dz-champ-ia relit — un modèle a UN seul nom dans les listes.
_LIBELLES_ECRAN = {"flux": "FLUX schnell"}


def source(nature):
    """Décorateur : inscrit la fonction qui rend les entrées brutes d'une
    nature (id, label, voie, usd, unite, jumeau…)."""
    def deco(fn):
        _SOURCES[nature] = fn
        return fn
    return deco


def natures() -> tuple:
    """Les natures d'appel inscrites (« image » ; les lots suivants en
    ajoutent par @source)."""
    return tuple(sorted(_SOURCES))


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
    registre = list(P._IMAGE_MODELS.items()) + list(P._IMAGE_MODELS_VECTEUR.items())
    for mid, (label, voie, cle_prix) in registre:
        try:
            usd = float(p.get(cle_prix, P.DEFAULTS.get(cle_prix, 0.0)) or 0.0)
        except (TypeError, ValueError):
            usd = 0.0
        jumeau = IP._FAL_GPT.get(mid) or inverse.get(mid)
        fal = IP.FAL_IMAGES.get(mid)
        out.append({"id": mid, "label": _LIBELLES_ECRAN.get(mid, label), "voie": voie, "usd": usd,
                    "unite": "image", "jumeau": jumeau,
                    "note": "" if usd else NOTE_A_MESURER,
                    "edit": bool(fal["edit"]) if fal else True,
                    "sortie": "svg" if IP.est_vectoriel(mid) else "raster"})
    return out


# t184 (G2) : Veo 3.1 a deux voies — fal (FAL_KEY) et l'API Google directe
# (GEMINI_API_KEY). Chaque id fal a pour jumeau l'id Google, et inversement.
JUMEAUX_VIDEO = {"veo-3.1-fast-fal": "veo-3.1-fast-google", "veo-3.1-fal": "veo-3.1-google",
                 "veo-3.1-lite-fal": "veo-3.1-lite-google"}
JUMEAUX_VIDEO.update({v: k for k, v in list(JUMEAUX_VIDEO.items())})


from app.services.fal_service import accepte_fin  # noqa: E402,F401  (source unique, réexportée)


def voie_de(m: dict) -> str:
    """La voie d'un modèle vidéo : « gemini » pour l'API Google directe, sinon « fal »."""
    return "gemini" if m.get("provider") == "google" else "fal"


def cle_de(m: dict) -> str:
    """La clé qu'exige la voie d'un modèle vidéo (CLES)."""
    return CLES[voie_de(m)]


def _videos(seulement_fin: bool) -> list[dict]:
    """Une entrée par id de fal_service.VIDEO_MODELS ; `usd` = tarif 720p
    ($/s, pricing.video_rate : colonne « * » ou la plus chère à défaut)."""
    from app.services.fal_service import VIDEO_MODELS
    p = P.load()
    out = []
    for mid, m in VIDEO_MODELS.items():
        if seulement_fin and not accepte_fin(m):
            continue
        usd = P.video_rate(mid, "720p", p) or 0.0
        jumeau = JUMEAUX_VIDEO.get(mid)
        if seulement_fin and jumeau and not accepte_fin(VIDEO_MODELS.get(jumeau) or {}):
            jumeau = None   # le jumeau doit lui-même accepter une fin (Veo Google : non)
        out.append({"id": mid, "label": m["label"],
                    "voie": voie_de(m),
                    "usd": usd, "unite": "s", "jumeau": jumeau,
                    "note": "" if usd else NOTE_A_MESURER, "fl": accepte_fin(m)})
    return out


@source("video_i2v")
def _video_i2v() -> list[dict]:
    """Image -> vidéo : tout le registre vidéo, les deux voies."""
    return _videos(False)


@source("video_fl")
def _video_fl() -> list[dict]:
    """Image de début ET de fin : seulement les modèles qui l'acceptent."""
    return _videos(True)


def _detourages(nature: str) -> list[dict]:
    """t186 (G4) : une entrée par id du registre unique du détourage (app.services.detourage.REGISTRE), dans
    son ordre (locales d'abord). `usd` = le tarif de sa clé de prix (pricing.load) dans son unité (« image »,
    « s », « 30 images », « 16 images ») ; `note` « a_mesurer » pour un modèle fal à 0 $ — une voie LOCALE est
    gratuite pour de bon et n'a pas de note ; `prompt` : le modèle exige un sujet nommé (SAM 3, Bria objet,
    SAM 3.1) ; `apercu` (vidéo) : le modèle image qui en montre un aperçu sur une image."""
    from app.services import detourage as DT
    p = P.load()
    out = []
    for mid in DT.ids(nature):
        e = DT.REGISTRE[mid]
        usd = P.taux_detourage(mid, p)
        x = {"id": mid, "label": e["label"], "voie": e["voie"], "usd": usd, "unite": e["unite"],
             "jumeau": None, "note": NOTE_A_MESURER if (e["voie"] == "fal" and not usd) else "",
             "prompt": bool(e["prompt"])}
        if e.get("apercu"):
            x["apercu"] = e["apercu"]
        out.append(x)
    return out


@source("detourage_image")
def _detourage_image() -> list[dict]:
    """Détourer une image : locales (rembg, chroma) puis les modèles fal."""
    return _detourages("detourage_image")


@source("detourage_video")
def _detourage_video() -> list[dict]:
    """Détourer une vidéo (matte avec alpha) : les modèles fal."""
    return _detourages("detourage_video")


def servis_puis_sans_cle(d: dict | None) -> list[dict]:
    """t183 (G1) : la liste d'un sélecteur raster à partir de la réponse de
    /image-models — les modèles SERVIS d'abord (`models`, dispo=True), puis
    ceux du catalogue (`tous`) dont la clé manque, avec dispo=False et le NOM
    de leur clé ; jamais un modèle vectoriel. Décision de l'utilisateur
    (11/10/2026) : un modèle sans clé reste choisissable, le tir est refusé en
    503 avant toute dépense. Partagée par les routes ai-models du Card Forge
    (face, cadre)."""
    d = d or {}
    out = [dict(m, dispo=True) for m in (d.get("models") or []) if m.get("sortie") != "svg"]
    vus = {str(m.get("id") or "") for m in out}
    for e in d.get("tous") or []:
        if e.get("sortie") == "svg" or str(e.get("id") or "") in vus:
            continue
        out.append({"id": e.get("id"), "label": e.get("label"), "provider": e.get("voie"), "note": "",
                    "dispo": e.get("dispo") is not False, "cle": e.get("cle")})
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
