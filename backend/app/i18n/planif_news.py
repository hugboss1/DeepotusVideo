"""Les textes que le serveur affiche dans le Planificateur et dans News, dans la langue de la requête (correctifs
de traduction du 10/10/2026, relevés en capturant le guide v3 t175).

Comme app/i18n/catalogues.py (t144) : les textes SOURCES restent en français, la langue de référence (quotas de
quota.LIMITS, formes de news_forms, motifs de news_filter / news_rank / news_trends / news_voice, messages des routes
News, aperçu des posts) ; la route traduit sa réponse au dernier moment, par une COPIE, et seulement pour une autre
langue que le français. Un texte sans clé reste tel quel (raison rendue par un modèle, erreur d'un fournisseur).

Les motifs sont souvent COMPOSÉS (« brief : a, b ; 2 média(s) sur le même sujet ; -6 source sur-représentée ») : un
motif se coupe sur « ; », chaque bout est confronté aux gabarits `fr` des clés (« {n} média(s) sur le même sujet »)
et rendu par le gabarit `en`, ses variables d'abord traduites elles-mêmes si elles sont un texte connu (la source
d'un quota cité dans un motif de tendance). Les clés vivent dans app/i18n/messages.json (préfixes `quota.`,
`apercu.`, `news.serveur.`), écrites par scripts/i18n_planif_news_serveur.py qui lit le français dans les sources.
"""
import copy
import re

from app.i18n import _DICO, borne, msg

PREFIXES = ("quota.", "apercu.", "news.serveur.")
_GABARITS: list | None = None


def _lang(lang) -> str:
    return borne(lang) or "fr"


def _gabarits() -> list:
    """[(regex du gabarit fr, clé)] des clés du lot, les plus longs d'abord (un gabarit court ne mange pas un long)."""
    global _GABARITS
    if _GABARITS is None:
        g = []
        for cle, e in _DICO.items():
            if not cle.startswith(PREFIXES) or not e.get("fr"):
                continue
            morceaux = re.split(r"(\{\w+\})", e["fr"])
            motif = "".join(f"(?P<{m[1:-1]}>.+?)" if re.fullmatch(r"\{\w+\}", m) else re.escape(m) for m in morceaux)
            g.append((len(e["fr"]), re.compile(motif + r"\Z", re.S), cle))
        g.sort(key=lambda x: -x[0])
        _GABARITS = [(rx, cle) for _, rx, cle in g]
    return _GABARITS


def texte(t, lang):
    """Un texte simple (sans « ; ») : sa traduction si un gabarit fr le reconnaît en entier, sinon lui-même."""
    lang = _lang(lang)
    if lang == "fr" or not isinstance(t, str) or not t:
        return t
    for rx, cle in _gabarits():
        m = rx.match(t)
        if m:
            vars = {k: texte(v, lang) for k, v in m.groupdict().items()}
            return msg(cle, lang, **vars)
    return t


def motif(t, lang):
    """Un motif composé « a ; b ; c » : chaque bout traduit à part, l'ordre et le séparateur gardés."""
    if _lang(lang) == "fr" or not isinstance(t, str) or not t:
        return t
    return " ; ".join(texte(b, lang) for b in t.split(" ; "))


def quotas(resume: dict, lang) -> dict:
    """quota.summary() -> copie dont chaque `source` est dans la langue demandée."""
    if _lang(lang) == "fr":
        return resume
    out = copy.deepcopy(resume)
    for ch, q in out.items():
        if isinstance(q, dict) and isinstance(q.get("source"), str):
            q["source"] = texte(q["source"], lang)
    return out


def formes(liste: list, lang) -> list:
    """Les formes de reel de news_forms : `label` et `description` traduits par l'id de la forme."""
    lang = _lang(lang)
    if lang == "fr":
        return liste
    out = copy.deepcopy(liste)
    for f in out:
        for champ, role in (("label", "nom"), ("description", "description")):
            cle = f"news.serveur.forme.{f.get('id')}.{role}"
            e = _DICO.get(cle)
            if e and e.get("fr") == f.get(champ):        # source changée depuis la traduction : servie telle quelle
                f[champ] = e.get(lang) or f[champ]
    return out
