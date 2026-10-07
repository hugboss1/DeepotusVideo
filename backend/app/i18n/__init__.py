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
    return re.sub(r"\{(\w+)\}", lambda m: str(vars[m.group(1)]) if m.group(1) in vars else m.group(0), s)
