"""Les CATALOGUES que le serveur affiche dans les écrans Son & VFX et Montage, dans la langue de la requête (t144,
traduction L4, 09/10/2026).

Les tables sources restent en français, la langue de référence : effets (effects_engine : nom, aide, catégorie,
libellés des paramètres), transitions xfade (montage_service : familles et libellés), préréglages de livraison
(montage_service._DELIVER) et gabarits de titre (titles.LABELS). Elles ne changent pas ; la route traduit sa réponse
au dernier moment, par une COPIE, et seulement pour une autre langue que le français. Un texte sans clé reste tel quel.
Les clés vivent dans app/i18n/messages.json (fr = le texte de la table, vérifié par backend/tests/test_i18n_l4_serveur.py).

  effets.<type>.nom / effets.<type>.aide      effets.cat.<id>      effets.param.<slug du libellé>
  transitions.famille.<id>                    transitions.<id>     livraison.<id>      titres.gabarit.<id>
"""
import copy
import re
import unicodedata

from app.i18n import _DICO, borne


def slug(texte: str) -> str:
    """« Fondu du bord » -> fondu_du_bord ; « Couleurs ternes (%) » -> couleurs_ternes ; ASCII minuscule."""
    t = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _t(cle: str, fr: str, lang: str) -> str:
    e = _DICO.get(cle)
    if lang == "fr" or not e or e.get("fr") != fr:
        return fr                       # clé absente, ou table source changée depuis la traduction : le texte servi
    return e.get(lang) or fr


def _lang(lang) -> str:
    return borne(lang) or "fr"


def effets(catalogue: dict, lang) -> dict:
    """{type: spec} d'effects_engine.catalog() -> copie traduite (label, hint, bounds[*].label)."""
    lang = _lang(lang)
    if lang == "fr":
        return catalogue
    out = copy.deepcopy(catalogue)
    for typ, spec in out.items():
        base = "grade" if typ == "lut" else typ          # « lut » est l'alias de « grade » (même définition)
        if isinstance(spec.get("label"), str):
            spec["label"] = _t(f"effets.{base}.nom", spec["label"], lang)
        if isinstance(spec.get("hint"), str):
            spec["hint"] = _t(f"effets.{base}.aide", spec["hint"], lang)
        for b in (spec.get("bounds") or {}).values():
            if isinstance(b, dict) and isinstance(b.get("label"), str):
                b["label"] = _t("effets.param." + slug(b["label"]), b["label"], lang)
    return out


def categories(lst: list, lang) -> list:
    lang = _lang(lang)
    if lang == "fr":
        return lst
    return [dict(c, label=_t(f"effets.cat.{c.get('id')}", c.get("label"), lang)) for c in lst]


def transitions(payload: dict, lang) -> dict:
    """{familles:[{id,label,items:[{id,label,live}]}]} -> copie traduite."""
    lang = _lang(lang)
    if lang == "fr":
        return payload
    out = copy.deepcopy(payload)
    for f in out.get("familles", []):
        f["label"] = _t(f"transitions.famille.{f.get('id')}", f.get("label"), lang)
        for it in f.get("items", []):
            it["label"] = _t(f"transitions.{it.get('id')}", it.get("label"), lang)
    return out


def livraison(builtins: list, lang) -> list:
    lang = _lang(lang)
    if lang == "fr":
        return builtins
    return [dict(b, label=_t(f"livraison.{b.get('id')}", b.get("label"), lang)) for b in builtins]


def titres(gabarits: list, lang) -> list:
    lang = _lang(lang)
    if lang == "fr":
        return gabarits
    return [dict(g, label=_t(f"titres.gabarit.{g.get('id')}", g.get("label"), lang)) for g in gabarits]
