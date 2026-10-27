# -*- coding: utf-8 -*-
"""t311 tâche 4 (27/10/2026) — la boucle de l'agent WhatsApp d'un espace et ses brouillons.

Un appel de `rediger(cid, eid, identite)` = une réponse proposée au DERNIER message entrant du contact :
  · lecture du fil chez Kapso (`whatsapp_echanges.lire`, gratuit) : contact en STOP -> rien ; aucun entrant -> rien ;
  · déclencheur humain sur le dernier entrant (`declencheur_humain` : mot de l'espace, argent, ton négatif) -> brouillon
    à l'état `humain`, SANS appel du modèle ;
  · sinon au plus MAX_TOURS appels du modèle de l'agent (Anthropic, `moteurs_texte.converser`) avec la boîte d'outils
    « whatsapp » ; avant CHAQUE appel le tour est chiffré (`MT.op_tour`) et passe la garde des plafonds (catégorie
    « whatsapp_agent », ref « compte:identité », espace DU COMPTE) ; après chaque appel le coût réel est noté sur les
    seules lignes de cette garde ; la PREMIÈRE carte arrête et devient le brouillon (`humain` -> état `humain`).
  · sans clé Anthropic : motif `sans_cle` ; garde refusée (402) : motif `plafond` ; dans les deux cas rien n'est écrit.
Pas de flux SSE ni de conversation rangée : seul le brouillon est écrit. Le texte du contact n'entre dans les messages du
modèle QUE par `lire_conversation` (cadre PREUVE de `agent_outils._preuve`) : la consigne d'ouverture ne le cite pas.

Brouillons : `DATA_ROOT/espaces/<eid>/whatsapp_brouillons.json`
  {"<phone_id>": {"<identite>": {"etat", "carte"|None, "cree_le", "raison"?, "auto_jour": {"AAAA-MM-JJ": n}}},
   "validations": {…}}   (`validations` : tâche 6, jamais touchée ici)
écrit sous un `threading.Lock` par `espaces._ecrire_json`, lu en JSON brut (jamais `espaces.lire()`, piège t210).
Le système (`systeme`) est pur et ne lit que `espaces_brut`. Aucun texte de message, aucune clé au journal.
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import unicodedata
from datetime import datetime, timezone

from fastapi import HTTPException

from app.services import (agent_aide, agent_boites, agent_outils as ao, espaces, espaces_brut,
                          moteurs_texte as MT, plafonds, pricing)

MAX_TOURS = 4
SORTIE_MAX = 2000                     # jetons de sortie par tour (une réponse WhatsApp : 4096 caractères au plus)
CATEGORIE = "whatsapp_agent"          # plafonds.CATEGORIES ; « whatsapp » reste celle des messages Meta
AGENT = "whatsapp"                    # la boîte d'outils (agent_boites) et `Ctx.agent`
MAX_PERSONA = 6000
CARS_PAR_JETON = 3
SURCOUT_OUTILS = 1000
FICHIER = "whatsapp_brouillons.json"
ETATS = ("attente", "humain", "envoye", "rejete")
DOC = agent_aide.DOSSIER / "whatsapp" / "WHATSAPP.md"
_VERROU_FICHIER = threading.Lock()
_VERROUS: dict[tuple, asyncio.Lock] = {}   # un seul `rediger` à la fois par (compte, identité)

ROLES = {
    "faq": "`faq` : réponds aux questions courantes (horaires, adresse, produits, services) d'après la fiche seulement.",
    "rendez_vous": "`rendez_vous` : aide à trouver un créneau avec `proposer_creneaux` ; tu proposes, tu ne confirmes "
                   "jamais : une personne confirme.",
    "commande": "`commande` : renseigne sur une commande ou un produit d'après la fiche ; aucun prix, aucun délai hors "
                "fiche, aucun paiement.",
    "validation": "`validation` : le client valide des publications par WhatsApp ; une réponse « Corriger » ou une "
                  "remarque se passe à une personne.",
}
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

# Montants et argent (FR-EN), sur le texte sans accents et en minuscules.
MOTS_ARGENT = re.compile(r"[€$£]|\b(?:eur|euros?|dollars?|prix|price|prices|rembours\w*|refund\w*|paiement|payment|"
                         r"virement)\b")
# Ton négatif ou conflictuel (FR-EN, sans accents) : mots entiers.
MOTS_NEGATIFS = ("arnaque", "arnaques", "arnaqueur", "escroc", "escroquerie", "scam", "scammer", "fraude", "fraud",
                 "plainte", "complaint", "avocat", "lawyer", "tribunal", "furieux", "furieuse", "furious", "angry",
                 "colere", "inadmissible", "inacceptable", "unacceptable", "honteux", "scandale", "scandaleux",
                 "degoute", "disgusting")
_NEGATIFS = frozenset(MOTS_NEGATIFS)
CONSIGNE = {"fr": "Le contact {identite} vient d'écrire. Lis la conversation avec `lire_conversation`, puis propose UNE "
                  "carte (réponse, modèle, ou passage à une personne).",
            "en": "Contact {identite} has just written. Read the conversation with `lire_conversation`, then propose ONE "
                  "card (reply, template, or hand-over to a person)."}


# ---- déclencheurs (purs) ---------------------------------------------------------------------------------------------

def _plat(t) -> str:
    """Minuscules, sans accents (NFKD sans les marques combinantes)."""
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def declencheur_humain(texte, mots_humain) -> str | None:
    """Le message doit-il passer à une personne SANS l'agent ? "mot_cle" (un des `mots_humain` de l'espace, casse et
    accents ignorés, mot ou expression entière), "argent" (montant, devise, prix, remboursement, paiement), "negatif"
    (ton conflictuel), sinon None. Pure."""
    if not isinstance(texte, str) or not texte.strip():
        return None
    t = _plat(texte)
    for m in mots_humain or []:
        m = _plat(m).strip() if isinstance(m, str) else ""
        if m and re.search(r"(?<![a-z0-9])" + re.escape(m) + r"(?![a-z0-9])", t):
            return "mot_cle"
    if MOTS_ARGENT.search(t):
        return "argent"
    if _NEGATIFS & set(re.findall(r"[a-z0-9]+", t)):
        return "negatif"
    return None


# ---- le système (pur : espaces_brut seulement) ----------------------------------------------------------------------

def _doc() -> str:
    try:
        return DOC.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    except OSError:
        return ""


def _partie_espace(eid: str) -> str:
    try:
        if espaces_brut.archive(eid):
            return (f"## Espace de marque\nL'espace `{eid}` est archivé : passe la main à une personne "
                    "(`remettre_a_l_humain`), sans autre réponse.")
        p = {k: v for k, v in espaces_brut.persona(eid).items() if k not in ("templates", "voice_ids")}
        mots = espaces_brut.interdits(eid)
    except KeyError:
        return "## Espace de marque\nEspace inconnu : passe la main à une personne (`remettre_a_l_humain`)."
    persona = json.dumps(p, ensure_ascii=False)
    if len(persona) > MAX_PERSONA:
        persona = persona[:MAX_PERSONA] + " …(tronqué)"
    return (f"## Espace de marque (id `{eid}`)\nMots interdits : {', '.join(mots) if mots else 'aucun'}.\n"
            f"Fiche (persona) — la SEULE source des faits, prix et engagements :\n{persona}")


def _partie_horaires(agent: dict) -> str:
    h = (agent or {}).get("horaires") or {}
    jours = ", ".join(JOURS[j] for j in h.get("jours") or [] if isinstance(j, int) and 0 <= j < 7) or "aucun"
    hors = str((agent or {}).get("message_hors_horaires") or "").strip()
    return (f"## Horaires de l'espace\n{jours}, de {h.get('debut', '?')} à {h.get('fin', '?')} "
            f"(fuseau {h.get('fuseau', '?')})."
            + (f"\nMessage hors horaires de l'espace : {json.dumps(hors, ensure_ascii=False)}" if hors else ""))


def systeme(eid: str, agent: dict, langue: str) -> str:
    """WHATSAPP.md + rôles cochés + fiche de l'espace (persona sans templates ni voice_ids, ≤ MAX_PERSONA caractères) +
    mots interdits + horaires + règle de prix + langue. Pure : `espaces_brut` seulement, rien n'est écrit."""
    roles = [r for r in ((agent or {}).get("roles") or []) if r in ROLES]
    parts = [_doc(),
             "## Tes rôles pour cet espace\n" + ("\n".join("- " + ROLES[r] for r in roles) if roles else
                                                 "Aucun rôle coché : passe la main à une personne pour toute demande."),
             _partie_espace(eid), _partie_horaires(agent),
             "## Règle de prix\nJamais de prix, de montant, de délai ni d'engagement hors de la fiche ci-dessus : dans "
             "ce cas, passe la main à une personne.",
             "## Langue\n" + ("Answer in the contact's language; if unclear, in English." if langue == "en" else
                              "Réponds dans la langue du contact ; à défaut, en français.")]
    return "\n\n".join(x for x in parts if x)


# ---- les brouillons ------------------------------------------------------------------------------------------------

def _chemin(eid: str):
    f = espaces.chemin(eid, FICHIER)
    if f is None:
        raise KeyError(f"espace inconnu : {str(eid)[:40]}")
    return f


def _lire(eid: str) -> dict:
    try:
        doc = json.loads(_chemin(eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _pid_valide(pid) -> str:
    if not isinstance(pid, str) or not pid or pid == "validations":
        raise ValueError("numéro WhatsApp invalide")
    return pid


def brouillons(eid: str, pid: str) -> dict:
    """{identite: brouillon} du numéro `pid` de l'espace (copie ; {} s'il n'y en a pas)."""
    d = _lire(eid).get(_pid_valide(pid))
    return json.loads(json.dumps(d)) if isinstance(d, dict) else {}


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _modifier(eid: str, pid: str, identite: str, geste) -> dict:
    """Applique `geste(brouillon_ou_None) -> brouillon` sous le verrou du fichier et écrit ; rend le brouillon."""
    _pid_valide(pid)
    f = _chemin(eid)
    with _VERROU_FICHIER:
        doc = _lire(eid)
        num = doc.get(pid) if isinstance(doc.get(pid), dict) else {}
        avant = num.get(identite) if isinstance(num.get(identite), dict) else None
        apres = geste(json.loads(json.dumps(avant)) if avant is not None else None)
        if apres is None:
            return avant or {}
        num[identite] = apres
        doc[pid] = num
        espaces._ecrire_json(f, doc)
        return json.loads(json.dumps(apres))


def ranger(eid: str, pid: str, identite: str, etat: str, carte: dict | None, raison: str | None = None) -> dict:
    """Range un brouillon neuf pour le contact (remplace le précédent ; `auto_jour` est gardé)."""
    if etat not in ETATS:
        raise ValueError(f"état de brouillon inconnu : {str(etat)[:20]}")

    def geste(b):
        neuf = {"etat": etat, "carte": carte, "cree_le": _maintenant(),
                "auto_jour": (b or {}).get("auto_jour") if isinstance((b or {}).get("auto_jour"), dict) else {}}
        if raison:
            neuf["raison"] = str(raison)[:200]
        return neuf
    return _modifier(eid, pid, identite, geste)


def marquer(eid: str, pid: str, identite: str, etat: str) -> dict:
    """Change l'état du brouillon du contact (créé sans carte s'il n'existe pas)."""
    if etat not in ETATS:
        raise ValueError(f"état de brouillon inconnu : {str(etat)[:20]}")

    def geste(b):
        b = b or {"carte": None, "cree_le": _maintenant(), "auto_jour": {}}
        b["etat"] = etat
        b["decide_le"] = _maintenant()
        return b
    return _modifier(eid, pid, identite, geste)


def apres_envoi_humain(eid: str, pid: str, identite: str) -> dict:
    """Un envoi fait par une personne a réussi : un brouillon `humain` ou `attente` du contact passe à `envoye` (l'agent
    reprend au prochain entrant). Aucun brouillon, ou déjà décidé : rien."""
    def geste(b):
        if not b or b.get("etat") not in ("humain", "attente"):
            return None
        b["etat"] = "envoye"
        b["decide_le"] = _maintenant()
        return b
    return _modifier(eid, pid, identite, geste)


def envoi_de(brouillon: dict, texte=None) -> dict:
    """L'envoi `whatsapp_echanges.envoyer` d'un brouillon en attente : texte (éventuellement modifié) ou modèle.
    ValueError : brouillon sans carte envoyable (état `humain`, carte « humain »)."""
    carte = (brouillon or {}).get("carte") if isinstance((brouillon or {}).get("carte"), dict) else None
    genre = carte.get("genre") if carte else None
    a = carte.get("arguments") if carte and isinstance(carte.get("arguments"), dict) else {}
    if genre == "reponse_whatsapp":
        t = texte if isinstance(texte, str) and texte.strip() else a.get("texte")
        return {"type": "texte", "texte": str(t or "")}
    if genre == "modele_whatsapp":
        return {"type": "modele", "nom": a.get("nom"), "langue": a.get("langue"),
                "parametres": a.get("parametres") if a.get("parametres") is not None else {}}
    raise ValueError("ce brouillon ne s'envoie pas : il attend une personne")


# ---- la boucle -------------------------------------------------------------------------------------------------------

def _jetons(systeme_: str, messages: list, outils: list) -> int:
    n = len(systeme_) + len(json.dumps(messages, ensure_ascii=False)) + len(json.dumps(outils, ensure_ascii=False))
    return -(-n // CARS_PAR_JETON) + SURCOUT_OUTILS


def _usd(op: dict) -> float:
    return float(pricing.estimate(op)["total_usd"])


def cle_presente() -> bool:
    return MT.configure("anthropic")


def _verrou(cid: str, identite: str) -> asyncio.Lock:
    return _VERROUS.setdefault((cid, identite), asyncio.Lock())


async def _fil(cid: str, identite: str) -> tuple[str | None, bool]:
    """(texte du dernier entrant du contact ou None, contact en STOP). Kapso rend les pages des plus récentes aux plus
    anciennes : la lecture s'arrête à la première page qui porte un entrant du contact (PAGES_MAX au plus)."""
    from app.services import whatsapp as WA, whatsapp_echanges as WE
    cur, trouves = None, []
    for _ in range(WE.PAGES_MAX):
        page = await WE.lire(cid, apres=cur)
        groupe = set(WA._groupe(WA.etat(cid), identite))
        trouves += [m for m in page["messages"] if m.get("identite") in groupe and m.get("sens") == "entrant"]
        cur = page.get("suivant")
        if trouves or not cur:
            break
    e = WA.etat(cid)
    groupe = set(WA._groupe(e, identite))
    stop = any(i in e["stops"] for i in groupe)
    if not trouves:
        return None, stop
    dernier = max(trouves, key=lambda m: str(m.get("quand") or ""))
    t = dernier.get("texte")
    return (t if isinstance(t, str) else ""), stop


def _res(etat, carte, motif) -> dict:
    return {"etat": etat, "carte": carte, "motif": motif}


async def rediger(cid: str, eid: str, identite: str, *, langue: str = "fr") -> dict:
    """Une réponse proposée au dernier entrant du contact : {"etat": attente|humain|None, "carte"|None, "motif"}.
    Motifs : carte, declencheur, sans_cle, plafond, moteur, max_tours, sans_carte, stop, sans_entrant, occupee.
    KeyError : compte ou espace inconnu ; ValueError : identité invalide, compte non relié, espace qui n'est pas celui
    du compte."""
    from app.services import whatsapp as WA
    langue = "en" if langue == "en" else "fr"
    WA.destinataire(identite)                               # ValueError : identité invalide
    eid_compte, pid = WA._cle_etat(cid)
    if eid != eid_compte:
        raise ValueError("ce compte WhatsApp n'appartient pas à cet espace")
    verrou = _verrou(cid, identite)
    if verrou.locked():
        return _res(None, None, "occupee")
    async with verrou:
        try:
            return await _rediger(cid, eid, pid, identite, langue)
        finally:
            if _VERROUS.get((cid, identite)) is verrou:
                _VERROUS.pop((cid, identite), None)


async def _rediger(cid: str, eid: str, pid: str, identite: str, langue: str) -> dict:
    from app.services import whatsapp as WA
    texte, stop = await _fil(cid, identite)
    if stop:
        return _res(None, None, "stop")
    if texte is None:
        return _res(None, None, "sans_entrant")
    agent = WA.reglages(eid)["agent"]
    raison = declencheur_humain(texte, agent.get("mots_humain"))
    if raison:
        ranger(eid, pid, identite, "humain", None, raison)
        return _res("humain", None, "declencheur")
    if not cle_presente():
        return _res(None, None, "sans_cle")
    return await _boucle(cid, eid, pid, identite, langue, agent)


async def _boucle(cid: str, eid: str, pid: str, identite: str, langue: str, agent: dict) -> dict:
    modele = MT.modele_agent()
    outils = agent_boites.definitions_pour(AGENT)
    sys_ = systeme(eid, agent, langue)
    msgs: list[dict] = [{"role": "user", "content": CONSIGNE[langue].format(identite=identite)}]
    ctx = ao.Ctx(cid=f"wa:{cid}:{identite}", espace_id=eid, lang=langue, agent=AGENT, compte_id=cid, identite=identite)
    ref = f"{cid}:{identite}"
    for _n in range(MAX_TOURS):
        op = MT.op_tour(modele, _jetons(sys_, msgs, outils), SORTIE_MAX)
        try:
            garde = await plafonds.verifier(op, CATEGORIE, ref=ref, espace_id=eid)
        except HTTPException as e:
            if e.status_code != 402:
                raise
            return _res(None, None, "plafond")
        lignes = (garde or {}).get("lignes") or []
        try:
            r = await asyncio.to_thread(MT.converser, modele, sys_, msgs, outils, SORTIE_MAX)
        except Exception as e:  # noqa: BLE001 — jamais une trace : le motif seulement
            # Rien de facturé (refus, sans clé) : réel 0 ; flux coupé après le 200 : la réservation reste (précédent
            # de l'agent Campagnes).
            if not isinstance(e, MT.FluxCoupe):
                await plafonds.noter_reel_lignes(lignes, 0.0)
            return _res(None, None, "sans_cle" if str(e) == "sans_cle" else "moteur")
        await plafonds.noter_reel_lignes(lignes, _usd(MT.op_tour(modele, r.get("in_tok") or 0, r.get("out_tok") or 0)))
        tronque = r.get("arret") == "max_tokens"
        blocs = list(r.get("blocs") or [])
        appels = [b for b in blocs if b.get("type") == "tool_use"]
        if not appels:
            return _res(None, None, "sans_carte")
        msgs.append({"role": "assistant", "content": blocs})
        resultats = []
        for b in appels:
            if tronque:
                resultats.append({"type": "tool_result", "tool_use_id": b.get("id"), "is_error": True,
                                  "content": json.dumps({"ok": False, "resume": "appel tronqué, non exécuté",
                                                         "donnees": None}, ensure_ascii=False)})
                continue
            args = b.get("input") if isinstance(b.get("input"), dict) else {}
            res = await ao.executer(b.get("name"), dict(args), ctx)
            carte = res.get("carte")
            if res.get("ok") and isinstance(carte, dict) and carte.get("genre") in ("reponse_whatsapp", "modele_whatsapp",
                                                                                     "humain"):
                if carte["genre"] == "humain":
                    raison = (carte.get("arguments") or {}).get("raison")
                    ranger(eid, pid, identite, "humain", carte, raison)
                    return _res("humain", carte, "carte")
                ranger(eid, pid, identite, "attente", carte)
                return _res("attente", carte, "carte")
            tr = {"type": "tool_result", "tool_use_id": b.get("id"), "content": ao.pour_modele(res)}
            if not res.get("ok"):
                tr["is_error"] = True
            resultats.append(tr)
        msgs.append({"role": "user", "content": resultats})
    return _res(None, None, "max_tours")
