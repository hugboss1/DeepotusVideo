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
(2) Bilan hebdomadaire et alerte « gagnant détecté » au propriétaire de l'espace (décision de l'utilisateur du 26/11 :
    validé, modèle UTILITAIRE, prix au devis, envoi seulement après son accord). `devis_alertes` donne le prix d'un
    message (grille WhatsApp saisie, `pricing` kind « whatsapp », catégorie utility) ; `accorder` enregistre l'accord
    (destinataire, modèle approuvé de catégorie utility à un paramètre au plus, prix accepté, bilan et/ou alerte) dans
    `alertes_croissance.json` de l'espace ; `revoquer` le retire. `tic` (boucle du lifespan, 2 min puis 30 min) ne fait
    RIEN sans accord ; sinon il envoie l'alerte d'un gagnant (≥ 3× l'habituel sur 7 jours, une seule fois par post) et le
    bilan du lundi, par `whatsapp_echanges.envoyer` (règles, STOP, fenêtre et plafond « whatsapp » inchangés). Un prix
    monté au-dessus du prix accepté suspend l'envoi (`etat` « prix_change ») jusqu'à un nouvel accord.
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


# ---- (2) envoi du bilan et de l'alerte (après l'accord de l'utilisateur) ---------------------------------------------

FICHIER_ALERTES = "alertes_croissance.json"
CATEGORIE_MODELE = "utility"
TIC_S = 1800
EPS = 0.00005


def _fichier_alertes(eid: str):
    f = espaces.chemin(eid, FICHIER_ALERTES)
    if f is None or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    return f


def lire_alertes(eid: str) -> dict:
    try:
        d = json.loads(_fichier_alertes(eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _ecrire_alertes(eid: str, d: dict) -> None:
    f = _fichier_alertes(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


def _identite(numero: str) -> str:
    chiffres = re.sub(r"\D", "", str(numero or ""))
    if not 6 <= len(chiffres) <= 15:
        raise ValueError("Numéro WhatsApp de l'espace invalide : indicatif du pays compris, chiffres seulement.")
    return "tel:" + chiffres


def prix_message(eid: str, identite: str) -> float:
    """Le prix d'UN message utilitaire vers `identite` (grille saisie) ; ValueError si la grille ne le connaît pas."""
    from app.services import pricing, whatsapp as WA, whatsapp_echanges as WE
    marche = WE._marche(identite, WA.reglages(eid)["marche_defaut"])
    op = {"kind": "whatsapp", "categorie": CATEGORIE_MODELE, "marche": marche, "service_deja_mois": 0}
    return round(float(pricing.estimate(op).get("total_usd") or 0.0), 5)


def devis_alertes(eid: str, numero: str) -> dict:
    ident = _identite(numero)
    try:
        usd = prix_message(eid, ident)
    except ValueError:
        return {"disponible": False, "usd_par_message": None, "raison": "prix"}
    return {"disponible": True, "usd_par_message": usd, "par_mois_max": round(usd * 6, 4)}


async def accorder(eid: str, *, numero: str, modele: dict, usd_accepte, bilan: bool = True, alerte: bool = True) -> dict:
    """L'ACCORD de l'utilisateur : rien ne part avant. Le modèle doit être approuvé, utilitaire, à un paramètre au plus."""
    from app.services import whatsapp_echanges as WE, whatsapp_validation as WV
    ident = _identite(numero)
    relie = WV._compte_relie(eid)
    if relie is None:
        raise ValueError("aucun numéro WhatsApp relié pour cet espace")
    nom, langue = str((modele or {}).get("nom") or ""), str((modele or {}).get("langue") or "")
    m = next((x for x in await WE.modeles(relie[0]) if x.get("nom") == nom and x.get("langue") == langue), None)
    if m is None:
        raise ValueError("modèle inconnu ou non approuvé pour cette langue")
    if str(m.get("categorie") or "").lower() != CATEGORIE_MODELE:
        raise ValueError("le modèle du bilan et de l'alerte doit être de catégorie « utilitaire »")
    if (m.get("n_parametres") or 0) > 1:
        raise ValueError("le modèle du bilan et de l'alerte doit avoir au plus un paramètre (le texte)")
    if isinstance(usd_accepte, bool) or not isinstance(usd_accepte, (int, float)):
        raise ValueError("Montant accepté (max_usd) manquant ou invalide.")
    prix = prix_message(eid, ident)
    if prix > float(usd_accepte) + EPS:
        raise ValueError("Le coût a changé : il dépasse le montant accepté.")
    d = {"accord": {"le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "usd_par_message": prix},
         "destinataire": ident, "modele": {"nom": nom, "langue": langue, "n_parametres": m.get("n_parametres") or 0,
                                           "parametres": m.get("parametres"), "noms_parametres": m.get("noms_parametres")},
         "bilan": bool(bilan), "alerte": bool(alerte), "deja_alertes": lire_alertes(eid).get("deja_alertes") or [],
         "dernier_bilan": lire_alertes(eid).get("dernier_bilan"), "etat": "actif"}
    _ecrire_alertes(eid, d)
    return d


def revoquer(eid: str) -> dict:
    d = lire_alertes(eid)
    d.pop("accord", None)
    d["etat"] = "revoque"
    _ecrire_alertes(eid, d)
    return d


def _envoi(d: dict, texte: str) -> dict:
    m = d["modele"]
    t = " ".join(str(texte).split())[:1024]
    if not m.get("n_parametres"):
        params = []
    elif m.get("parametres") == "nommes" and m.get("noms_parametres"):
        params = {str(m["noms_parametres"][0]): t}
    else:
        params = [t]
    return {"type": "modele", "nom": m["nom"], "langue": m["langue"], "parametres": params}


async def _envoyer(eid: str, d: dict, texte: str) -> dict:
    from app.services import whatsapp_echanges as WE, whatsapp_validation as WV
    relie = WV._compte_relie(eid)
    if relie is None:
        raise ValueError("aucun numéro WhatsApp relié pour cet espace")
    return await WE.envoyer(relie[0], d["destinataire"], _envoi(d, texte))


def _due_bilan(d: dict, maintenant: datetime) -> bool:
    if not d.get("bilan") or maintenant.weekday() != 0:
        return False
    try:
        dernier = datetime.fromisoformat(d.get("dernier_bilan") or "")
    except ValueError:
        return True
    if dernier.tzinfo is None:
        dernier = dernier.replace(tzinfo=timezone.utc)
    return (maintenant - dernier).days >= 6


async def tic_espace(eid: str, maintenant: datetime | None = None) -> dict:
    """Une passe pour un espace : rien sans accord ; alerte des gagnants neufs, bilan du lundi."""
    from app.services import metrics_service as MS
    t = maintenant or datetime.now(timezone.utc)
    d = lire_alertes(eid)
    if not d.get("accord") or d.get("etat") not in ("actif", "prix_change"):
        return {"envoyes": 0, "raison": "sans_accord"}
    if prix_message(eid, d["destinataire"]) > float(d["accord"]["usd_par_message"]) + EPS:
        d["etat"] = "prix_change"
        _ecrire_alertes(eid, d)
        return {"envoyes": 0, "raison": "prix_change"}
    d["etat"] = "actif"
    tab = await MS.tableau(7, eid)
    envoyes = 0
    langue = "en" if (d.get("modele") or {}).get("langue", "").startswith("en") else "fr"
    if d.get("alerte"):
        for g in tab.get("gagnants") or []:
            pid = str(g.get("id") or "")
            if not pid or pid in d["deja_alertes"]:
                continue
            await _envoyer(eid, d, texte_alerte(g.get("title") or "", (g.get("croissance") or {}).get("multiplicateur") or 0, langue))
            d["deja_alertes"] = (d["deja_alertes"] + [pid])[-500:]
            envoyes += 1
            _ecrire_alertes(eid, d)
    if _due_bilan(d, t):
        await _envoyer(eid, d, texte_bilan(tab, langue))
        d["dernier_bilan"] = t.isoformat(timespec="seconds")
        envoyes += 1
    _ecrire_alertes(eid, d)
    return {"envoyes": envoyes, "raison": ""}


async def tic(maintenant: datetime | None = None) -> int:
    """Tous les espaces ayant un accord ; une erreur d'un espace n'arrête pas les autres."""
    from loguru import logger
    n = 0
    for eid in list(espaces.lire()["espaces"]):
        f = espaces.chemin(eid, FICHIER_ALERTES)
        if f is None or not f.is_file():
            continue
        try:
            n += (await tic_espace(eid, maintenant))["envoyes"]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"alertes de croissance : espace {eid[:8]} en échec ({type(e).__name__})")
    return n


async def boucle() -> None:
    import asyncio
    await asyncio.sleep(120)
    while True:
        await tic()
        await asyncio.sleep(TIC_S)
