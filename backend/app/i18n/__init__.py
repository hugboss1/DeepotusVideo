"""La langue des MESSAGES du serveur (t134, traduction lot 0, 07/10/2026).

Le français est la langue de référence : chaque clé de `messages.json` a son texte `fr`, l'anglais en est la
traduction. La langue d'une requête vient de l'en-tête Accept-Language que le runtime /shared/dz-i18n.js ajoute aux
appels /api/, sinon du réglage UI_LANG. Les messages pas encore migrés restent écrits en dur (lot L10) ; les bancs
qui lisent un `detail` français tournent sans en-tête, donc en français.
"""
import json
import pathlib
import re
from typing import Optional

LANGUES = ("fr", "en")
_DICO = json.loads((pathlib.Path(__file__).with_name("messages.json")).read_text("utf-8"))


def borne(lang) -> Optional[str]:
    lang = str(lang or "").strip().lower()
    return lang if lang in LANGUES else None


def langue_ui() -> str:
    """La langue choisie pour l'interface (UI_LANG), fr si illisible."""
    from app.config import settings
    return borne(getattr(settings, "UI_LANG", "")) or "fr"


def langue_entete(valeur: str | None) -> Optional[str]:
    """La première langue connue d'un en-tête Accept-Language (« en-US,en;q=0.9 » -> en), sinon None."""
    for morceau in str(valeur or "").split(","):
        code = morceau.split(";")[0].strip().lower().split("-")[0]
        if code in LANGUES:
            return code
    return None


def langue_requete(request) -> str:
    try:
        return langue_entete(request.headers.get("accept-language")) or langue_ui()
    except Exception:
        return langue_ui()


def msg(cle: str, lang: str | None = None, **vars) -> str:
    """Le message `cle` dans la langue demandée (fr par défaut), {variables} remplacées ; clé absente -> la clé."""
    e = _DICO.get(cle)
    if not e:
        return cle
    s = e.get(borne(lang) or "fr") or e.get("fr") or cle
    vars = {k: (nom_modele(v.mid, str(v), lang) if isinstance(v, Nom) else v.dans(lang) if isinstance(v, Message)
                else v) for k, v in vars.items()}
    return re.sub(r"\{(\w+)\}", lambda m: str(vars[m.group(1)]) if m.group(1) in vars else m.group(0), s)


# ── t192 (G10) : les refus des lots « Génération IA » G0-G9 dans la langue de la requête ─────────────────────────
# Un service (vfx_ia, sfx_service, detourage, storyboard3d) ne connaît pas la langue de la requête : il rend un
# `Message` (une chaîne dont le texte est le FRANÇAIS — les bancs, les f-strings et les journaux n'y voient rien de
# neuf) ou lève un `Refus` (ValueError du même texte), qui gardent leur clé et leurs variables ; la route les rend
# dans la langue de la requête par `texte(x, lang)`. Un nom de modèle passe par `Nom(id, libellé)` : le libellé du
# registre (français) en français, la clé `ia.nom.<id>` de messages.json dans une autre langue (sinon le libellé,
# nom propre).

class Nom(str):
    """Le nom d'un modèle dans un message : sa chaîne est le libellé du registre ; `mid` son id."""

    def __new__(cls, mid, libelle=None):
        s = str.__new__(cls, str(libelle if libelle is not None else mid))
        s.mid = str(mid or "")
        return s


def nom_modele(mid, libelle, lang=None) -> str:
    """Le nom d'un modèle dans la langue `lang` : français = le libellé ; sinon ia.nom.<id>, à défaut le libellé."""
    lang = borne(lang) or "fr"
    if lang == "fr":
        return str(libelle)
    e = _DICO.get(f"ia.nom.{mid}")
    return (e.get(lang) if e and e.get("fr") == str(libelle) else None) or str(libelle)


class Message(str):
    """Un message serveur traduisible, transporté comme une chaîne : str(m) = le français."""

    def __new__(cls, cle, **vars):
        s = str.__new__(cls, msg(cle, "fr", **vars))
        s.cle, s.vars = cle, vars
        return s

    def dans(self, lang) -> str:
        return msg(self.cle, lang, **self.vars)


class Refus(ValueError):
    """Un refus nommé d'un service (ValueError dont le texte est le français), rendu dans une langue par `texte`."""

    def __init__(self, cle, **vars):
        self.message = Message(cle, **vars)
        super().__init__(str(self.message))


def texte(x, lang=None) -> str:
    """Le texte d'un refus (Refus, Message, ou n'importe quelle exception / chaîne) dans la langue `lang`."""
    if isinstance(x, Refus):
        return x.message.dans(lang)
    if isinstance(x, Message):
        return x.dans(lang)
    return str(x)
