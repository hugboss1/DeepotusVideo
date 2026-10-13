"""Traduction L10 (t150, 12/10/2026) : les messages d'erreur du backend, traduits À LA SORTIE.

Décision de l'utilisateur : les sources gardent leurs messages tels qu'ils sont écrits (français pour l'essentiel,
anglais pour le socle d'origine). Le gestionnaire d'HTTPException de app.main traduit le `detail` au moment de
répondre, dans la langue de l'en-tête Accept-Language que le runtime /shared/dz-i18n.js ajoute aux appels /api/.
SANS en-tête, rien ne change : les bancs qui lisent un `detail` tournent sans en-tête.

Le dictionnaire erreurs.json (écrit par scripts/i18n_l10_erreurs.py, qui relit les sources par AST) donne pour
chaque message un gabarit fr et un gabarit en, et `src`, la langue du code. Un `detail` est confronté aux gabarits
SOURCE (ceux qu'écrit le code), les plus longs d'abord ; reconnu en entier, il est rendu par le gabarit de la langue
demandée, ses variables d'abord traduites elles-mêmes (« Échec : {e} » où e est un message connu). Un texte inconnu
(erreur d'un fournisseur, d'une bibliothèque) passe tel quel.
"""
import json
import pathlib
import re

from app.i18n import borne

_FICHIER = pathlib.Path(__file__).with_name("erreurs.json")
_VAR = re.compile(r"\{(\w+)\}")
_PROFONDEUR = 3
_DICO: dict | None = None
_GABARITS: list | None = None


def dico() -> dict:
    global _DICO
    if _DICO is None:
        _DICO = json.loads(_FICHIER.read_text("utf-8")) if _FICHIER.is_file() else {}
    return _DICO


def _regex(g: str):
    morceaux = re.split(r"(\{\w+\})", g)
    if not any(_VAR.fullmatch(m) for m in morceaux):
        return None, g                 # sans variable : une simple égalité, bien plus rapide qu'une regex
    vus, motif = set(), ""
    for m in morceaux:
        v = _VAR.fullmatch(m)
        if v and v.group(1) not in vus:
            vus.add(v.group(1))
            motif += f"(?P<{v.group(1)}>.*?)"
        elif v:
            motif += f"(?P={v.group(1)})"
        else:
            motif += re.escape(m)
    return re.compile(motif + r"\Z", re.S), None


def _gabarits() -> tuple[dict, list]:
    """({texte exact: entrée} pour les gabarits sans variable, [(regex, entrée)] des autres, les plus longs d'abord)."""
    global _GABARITS
    if _GABARITS is None:
        exacts, rx = {}, []
        for e in dico().values():
            g = e.get(e.get("src") or "fr") or ""
            if not g:
                continue
            r, exact = _regex(g)
            if exact is not None:
                exacts.setdefault(exact, e)
            else:
                rx.append((len(_VAR.sub("", g)), r, e))
        rx.sort(key=lambda x: -x[0])
        _GABARITS = (exacts, [(r, e) for _, r, e in rx])
    return _GABARITS


def texte(t, lang, _prof: int = 0):
    """Un message dans la langue `lang` s'il est connu, sinon lui-même (et toujours lui-même sans langue connue)."""
    lang = borne(lang)
    if not lang or not isinstance(t, str) or not t.strip() or _prof > _PROFONDEUR:
        return t
    exacts, rx = _gabarits()
    e = exacts.get(t)
    if e is not None:
        return e.get(lang) or t
    for r, e in rx:
        m = r.match(t)
        if m:
            vars = {k: texte(v, lang, _prof + 1) for k, v in m.groupdict().items()}
            cible = e.get(lang) or e.get(e.get("src") or "fr")
            return _VAR.sub(lambda x: vars.get(x.group(1), x.group(0)), cible)
    return t


_CHAMPS = ("message", "detail", "erreur", "error", "raison")


def detail(d, lang):
    """Le `detail` d'une HTTPException traduit : une chaîne, ou les champs texte connus d'un dict (copie)."""
    if isinstance(d, str):
        return texte(d, lang)
    if isinstance(d, dict):
        out = None
        for k in _CHAMPS:
            v = d.get(k)
            if isinstance(v, str):
                t = texte(v, lang)
                if t != v:
                    out = out if out is not None else dict(d)
                    out[k] = t
        return d if out is None else out
    return d


def langue(request):
    """La langue de l'en-tête Accept-Language d'une requête, sinon None (sans en-tête : rien ne se traduit)."""
    from app.i18n import langue_entete
    try:
        return langue_entete(request.headers.get("accept-language")) if request is not None else None
    except Exception:  # noqa: BLE001 — une fonction de route appelée directement par un banc (request=None ou faux)
        return None


def job(d: dict, lang) -> dict:
    """Un job sérialisé (GET /jobs) avec son étape (`current_step`) et son `error` traduits — décision de l'utilisateur
    en G10 (t192) : l'étape suit L10. Le dict est modifié sur place et rendu ; sans langue, il ne change pas."""
    if borne(lang):
        for k in ("current_step", "error"):
            if isinstance(d.get(k), str):
                d[k] = texte(d[k], lang)
    return d
