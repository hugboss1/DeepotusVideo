# -*- coding: utf-8 -*-
"""t502 (G12, 26/11/2026) — WhatsApp dans la boucle de croissance : validation NOTÉE, lien SUIVI par post, bilan et alerte.

Spec docs/superpowers/specs/2026-11-09-getripping-design.md (ligne WhatsApp, décision D6). Kapso, règles 24 h et STOP
inchangées (tout envoi passe par `whatsapp_echanges.envoyer`, qui applique `whatsapp.controler`).

(1) `bloc_note(brief, langue)` : la note avant publication (G7, `brief.note_rendu`) et ses trois premières remarques,
    ajoutées au message de validation envoyé au client (`whatsapp_validation.envoyer_validation`).
(3) Lien SUIVI : `lien(numero, post_id, texte)` = https://wa.me/<numéro>?text=<texte + « réf. #PXXXXXXXX »>. Le code
    (`code_post`, 8 caractères tirés de l'id du post) est rangé dans `DATA_ROOT/espaces/<id>/liens_suivis.json`. Quand
    un message entrant porte ce code, `whatsapp.noter_entrant` note l'ORIGINE du contact (`etat.origines[identite]` :
    code et date, jamais le texte du message) ; `prospects_sources.whatsapp_entrants` rend alors `origine_post` :
    l'entrant devient un prospect rattaché au post qui l'a amené.
(2) Bilan hebdomadaire et alerte « gagnant détecté » au propriétaire de l'espace : `texte_bilan`, `texte_alerte` (purs)
    seulement. L'ENVOI attend la décision de l'utilisateur (modèle utilitaire payant par message, tarifs à relire chez
    Meta et Kapso) : rien n'est branché à une boucle ni envoyé ici.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

from app.services import espaces

FICHIER = "liens_suivis.json"
CODE = re.compile(r"#P([0-9A-F]{8})\b")
MAX_LIENS = 2000
REMARQUES = {
    "fr": {"plan_long": "image figée {secondes} s à {t}", "accroche_tardive": "la voix part à {secondes} s",
           "accroche_maigre": "peu de mots dans les 3 premières secondes", "debit_lent": "débit lent ({mpm} mots/min)",
           "debit_rapide": "débit rapide ({mpm} mots/min)", "sans_soustitres": "sans sous-titres",
           "pas_vertical": "pas au format vertical", "long": "long ({secondes} s)", "hors_zone_sure": "texte hors zone sûre",
           "sans_voix": "sans voix"},
    "en": {"plan_long": "still image for {secondes} s at {t}", "accroche_tardive": "voice starts at {secondes} s",
           "accroche_maigre": "few words in the first 3 seconds", "debit_lent": "slow pace ({mpm} wpm)",
           "debit_rapide": "fast pace ({mpm} wpm)", "sans_soustitres": "no subtitles", "pas_vertical": "not vertical",
           "long": "long ({secondes} s)", "hors_zone_sure": "text outside the safe zone", "sans_voix": "no voice"},
}
ENTETE_NOTE = {"fr": "Note avant publication (estimation) : {note}/100", "en": "Pre-publish score (estimate): {note}/100"}


def _mmss(t) -> str:
    t = int(float(t or 0))
    return f"{t // 60}:{t % 60:02d}"


def bloc_note(brief, langue: str = "fr") -> str | None:
    """Le bloc « note » d'un message de validation (None sans note)."""
    try:
        b = json.loads(brief) if isinstance(brief, str) else (brief or {})
    except ValueError:
        return None
    n = (b or {}).get("note_rendu") if isinstance(b, dict) else None
    if not isinstance(n, dict) or not isinstance(n.get("note"), (int, float)):
        return None
    lg = langue if langue in REMARQUES else "fr"
    lignes = [ENTETE_NOTE[lg].format(note=int(n["note"]))]
    for r in (n.get("remarques") or [])[:3]:
        gab = REMARQUES[lg].get(str((r or {}).get("code")))
        if gab:
            v = {k: r.get(k, "") for k in ("secondes", "mpm")}
            lignes.append("- " + gab.format(t=_mmss(r.get("t")), **v))
    return "\n".join(lignes)


def code_post(post_id: str) -> str:
    return hashlib.sha1(str(post_id).encode("utf-8")).hexdigest()[:8].upper()


def extraire_code(texte) -> str | None:
    m = CODE.search(str(texte or "").upper())
    return m.group(1) if m else None


def _fichier(eid: str):
    f = espaces.chemin(eid, FICHIER)
    if f is None or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    return f


def _lire(eid: str) -> dict:
    try:
        d = json.loads(_fichier(eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def lien(eid: str, numero: str, post_id: str, texte: str = "", langue: str = "fr") -> dict:
    """Le lien wa.me suivi d'un post ; le code est rangé pour reconnaître l'entrant."""
    chiffres = re.sub(r"\D", "", str(numero or ""))
    if not 6 <= len(chiffres) <= 15:
        raise ValueError("Numéro WhatsApp de l'espace invalide : indicatif du pays compris, chiffres seulement.")
    code = code_post(post_id)
    ref = ("réf." if langue != "en" else "ref.") + f" #P{code}"
    message = (" ".join(str(texte or "").split())[:200] + " " + ref).strip()
    doc = _lire(eid)
    doc[code] = {"post_id": str(post_id)[:64], "cree": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if len(doc) > MAX_LIENS:
        for k in sorted(doc, key=lambda k: doc[k].get("cree") or "")[:len(doc) - MAX_LIENS]:
            del doc[k]
    f = _fichier(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)
    return {"lien": f"https://wa.me/{chiffres}?text={quote(message)}", "code": code, "message": message}


def post_du_code(eid: str, code: str) -> str | None:
    return ((_lire(eid).get(str(code or "").upper()) or {}).get("post_id")) if code else None


# ---- (2) textes du bilan et de l'alerte (purs ; l'envoi attend la décision de l'utilisateur) ------------------------

def texte_bilan(tableau: dict, langue: str = "fr") -> str:
    """Le bilan hebdomadaire depuis `metrics_service.tableau` (totaux, gagnants)."""
    t = (tableau or {}).get("totaux") or {}
    g = (tableau or {}).get("gagnants") or []
    if langue == "en":
        return (f"Weekly report: {t.get('posts', 0)} post(s), {t.get('views', 0)} views, {t.get('engagement', 0)} "
                f"interactions; {len(g)} winner(s).")
    return (f"Bilan de la semaine : {t.get('posts', 0)} post(s), {t.get('views', 0)} vues, {t.get('engagement', 0)} "
            f"interactions ; {len(g)} gagnant(s).")


def texte_alerte(post_titre: str, multiplicateur: float, langue: str = "fr") -> str:
    m = f"{float(multiplicateur):.1f}".rstrip("0").rstrip(".")
    titre = " ".join(str(post_titre or "").split())[:120]
    if langue == "en":
        return f"Winner spotted: “{titre}” is at {m}× your usual. Worth recycling?"
    return f"Gagnant détecté : « {titre} » fait {m}× votre habituel. On le recycle ?"
