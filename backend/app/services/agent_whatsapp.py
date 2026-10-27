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
   "validations": {…}}   (`validations` : tâche 6, lue et écrite par `validations` / `modifier_validations`)
écrit sous un `threading.Lock` par `espaces._ecrire_json`, lu en JSON brut (jamais `espaces.lire()`, piège t210).
Le système (`systeme`) est pur et ne lit que `espaces_brut`. Aucun texte de message, aucune clé au journal.
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import unicodedata
from datetime import datetime, timedelta, timezone

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
ETATS = ("attente", "humain", "envoi_en_cours", "envoye", "rejete")
ENVOI_COINCE = timedelta(minutes=10)   # un `envoi_en_cours` plus vieux redevient décidable
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
    if f is None or not f.parent.is_dir():          # jamais recréer `espaces/<eid>/` d'un espace supprimé
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
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")   # `cree_le` distingue deux brouillons


def _date(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def canonique(cid: str, identite: str) -> tuple[str, list]:
    """(clé canonique, groupe) d'un contact : le premier élément trié de son groupe d'alias (`WA._groupe`), la même
    clé qu'on le voie par `tel:` ou par `bsuid:`. Clé du verrou et des brouillons."""
    from app.services import whatsapp as WA
    groupe = sorted(set(WA._groupe(WA.etat(cid), identite)))
    return groupe[0], groupe


def _modifier(eid: str, pid: str, identite: str, geste, alias=()) -> dict:
    """Applique `geste(brouillon_ou_None) -> brouillon|None` sous le verrou du fichier et écrit ; rend le brouillon.
    `alias` : les autres identités du groupe ; un brouillon rangé sous l'une d'elles (avant que l'alias soit connu) est
    repris sous `identite` et sa vieille clé retirée. Une exception de `geste` n'écrit rien."""
    _pid_valide(pid)
    f = _chemin(eid)
    with _VERROU_FICHIER:
        doc = _lire(eid)
        num = doc.get(pid) if isinstance(doc.get(pid), dict) else {}
        vieux = [a for a in alias if a != identite and isinstance(num.get(a), dict)]
        avant = num.get(identite) if isinstance(num.get(identite), dict) else (num[vieux[0]] if vieux else None)
        apres = geste(json.loads(json.dumps(avant)) if avant is not None else None)
        if apres is None:
            return json.loads(json.dumps(avant)) if avant else {}
        for a in vieux:
            num.pop(a, None)
        num[identite] = apres
        doc[pid] = num
        espaces._ecrire_json(f, doc)
        return json.loads(json.dumps(apres))


def validations(eid: str) -> dict:
    """t311 tâche 6 : {post_id: validation} de la clé `validations` du fichier (copie ; {} s'il n'y en a pas)."""
    v = _lire(eid).get("validations")
    return json.loads(json.dumps(v)) if isinstance(v, dict) else {}


def modifier_validations(eid: str, geste) -> dict:
    """t311 tâche 6 : `geste(validations) -> validations|None` sous LE verrou du fichier (le même que les brouillons) ;
    None = rien à écrire. Rend les validations après coup (copie). Une exception de `geste` n'écrit rien."""
    f = _chemin(eid)
    with _VERROU_FICHIER:
        doc = _lire(eid)
        avant = doc.get("validations") if isinstance(doc.get("validations"), dict) else {}
        apres = geste(json.loads(json.dumps(avant)))
        if apres is None:
            return json.loads(json.dumps(avant))
        doc["validations"] = apres
        espaces._ecrire_json(f, doc)
        return json.loads(json.dumps(apres))


def ranger(eid: str, pid: str, identite: str, etat: str, carte: dict | None, raison: str | None = None,
           alias=()) -> dict:
    """Range un brouillon neuf pour le contact (remplace le précédent ; `auto_jour`, `hors_jour` et `traite_jusqu_a` sont
    gardés). `identite` : la clé canonique (`canonique`)."""
    if etat not in ETATS:
        raise ValueError(f"état de brouillon inconnu : {str(etat)[:20]}")

    def geste(b):
        neuf = {"etat": etat, "carte": carte, "cree_le": _maintenant(),
                "auto_jour": (b or {}).get("auto_jour") if isinstance((b or {}).get("auto_jour"), dict) else {}}
        if raison:
            neuf["raison"] = str(raison)[:200]
        for k in ("hors_jour", "traite_jusqu_a"):           # t311 tâche 5 : traces du relevé de fond
            if isinstance((b or {}).get(k), str):
                neuf[k] = b[k]
        return neuf
    return _modifier(eid, pid, identite, geste, alias)


def noter_traite(eid: str, pid: str, identite: str, quand: str, alias=()) -> dict:
    """t311 tâche 5 : le relevé de fond a traité les entrants du contact jusqu'à `quand` (ISO) : `traite_jusqu_a`, sans
    changer l'état ni la carte. Sans brouillon, l'entrée est créée SANS `etat` (aucun brouillon à décider). Ne recule
    jamais."""
    def geste(b):
        b = b if b is not None else {"carte": None, "auto_jour": {}}
        vieux = _date(b.get("traite_jusqu_a"))
        neuf = _date(quand)
        if neuf is None or (vieux is not None and vieux >= neuf):
            return None
        b["traite_jusqu_a"] = neuf.isoformat(timespec="seconds")
        return b
    return _modifier(eid, pid, identite, geste, alias)


def marquer(eid: str, pid: str, identite: str, etat: str, alias=()) -> dict:
    """Change l'état du brouillon du contact (créé sans carte s'il n'existe pas)."""
    if etat not in ETATS:
        raise ValueError(f"état de brouillon inconnu : {str(etat)[:20]}")

    def geste(b):
        b = b or {"carte": None, "cree_le": _maintenant(), "auto_jour": {}}
        b["etat"] = etat
        b["decide_le"] = _maintenant()
        b.pop("envoi_depuis", None)
        return b
    return _modifier(eid, pid, identite, geste, alias)


def apres_envoi_humain(eid: str, pid: str, identite: str, alias=()) -> dict:
    """Un envoi fait par une personne a réussi : un brouillon `humain` ou `attente` du contact passe à `envoye` (l'agent
    reprend au prochain entrant). Aucun brouillon, ou déjà décidé : rien."""
    def geste(b):
        if not b or b.get("etat") not in ("humain", "attente"):
            return None
        b["etat"] = "envoye"
        b["decide_le"] = _maintenant()
        return b
    return _modifier(eid, pid, identite, geste, alias)


def envoi_de(brouillon: dict, texte=None) -> dict:
    """L'envoi `whatsapp_echanges.envoyer` d'un brouillon en attente : texte (éventuellement modifié) ou modèle.
    ValueError : brouillon sans carte envoyable (état `humain`, carte « humain »), texte fourni pour un modèle."""
    carte = (brouillon or {}).get("carte") if isinstance((brouillon or {}).get("carte"), dict) else None
    genre = carte.get("genre") if carte else None
    a = carte.get("arguments") if carte and isinstance(carte.get("arguments"), dict) else {}
    if genre == "reponse_whatsapp":
        t = texte if isinstance(texte, str) and texte.strip() else a.get("texte")
        return {"type": "texte", "texte": str(t or "")}
    if genre == "modele_whatsapp":
        if texte is not None:
            raise ValueError("un modèle WhatsApp ne prend pas de texte modifié")
        return {"type": "modele", "nom": a.get("nom"), "langue": a.get("langue"),
                "parametres": a.get("parametres") if a.get("parametres") is not None else {}}
    raise ValueError("ce brouillon ne s'envoie pas : il attend une personne")


class BrouillonAbsent(KeyError):
    """Aucun brouillon décidable pour ce contact (absent, déjà envoyé ou rejeté) : 404 à la route."""


def _decidable(b, maintenant: datetime) -> bool:
    """Le brouillon attend-il une décision ? `attente`/`humain`, ou `envoi_en_cours` resté coincé plus de
    ENVOI_COINCE (le processus est mort pendant l'envoi)."""
    if not b:
        return False
    if b.get("etat") in ("attente", "humain"):
        return True
    if b.get("etat") == "envoi_en_cours":
        d = _date(b.get("envoi_depuis"))
        return d is None or maintenant - d > ENVOI_COINCE
    return False


def _reserver(eid, pid, cle, groupe, texte) -> tuple[dict, str]:
    """Sous le verrou du fichier : vérifie le brouillon, calcule l'envoi, le passe à `envoi_en_cours` ; rend (envoi,
    cree_le). Refus : BrouillonAbsent, WhatsappRefus `occupee` (envoi déjà en cours), ValueError (humain, texte+modèle)."""
    from app.services import whatsapp as WA
    pris: dict = {}

    def geste(b):
        maintenant = datetime.now(timezone.utc)
        if b and b.get("etat") == "envoi_en_cours" and not _decidable(b, maintenant):
            raise WA.WhatsappRefus("ce brouillon est déjà en cours d'envoi", "occupee")
        if not _decidable(b, maintenant):
            raise BrouillonAbsent("aucun brouillon en attente pour ce contact")
        pris["envoi"] = envoi_de(b, texte)
        pris["cree_le"] = b.get("cree_le")
        b["etat"] = "envoi_en_cours"
        b["envoi_depuis"] = maintenant.isoformat(timespec="microseconds")
        return b
    _modifier(eid, pid, cle, geste, groupe)
    return pris["envoi"], pris["cree_le"]


def _conclure(eid, pid, cle, groupe, cree_le, etat) -> dict:
    """Après l'envoi : `etat` (envoye, ou attente sur un refus) seulement si le brouillon est TOUJOURS celui réservé
    (même `cree_le`, encore `envoi_en_cours`) ; un brouillon neuf rangé entre-temps reste tel quel."""
    def geste(b):
        if not b or b.get("cree_le") != cree_le or b.get("etat") != "envoi_en_cours":
            return None
        b["etat"] = etat
        b.pop("envoi_depuis", None)
        if etat == "envoye":
            b["decide_le"] = _maintenant()
        return b
    return _modifier(eid, pid, cle, geste, groupe)


def _compte_de(cid: str, eid: str) -> str:
    from app.services import whatsapp as WA
    eid_compte, pid = WA._cle_etat(cid)
    if eid != eid_compte:
        raise ValueError("ce compte WhatsApp n'appartient pas à cet espace")
    return pid


async def envoyer_brouillon(cid: str, eid: str, identite: str, texte=None) -> dict:
    """Envoie le brouillon du contact par `whatsapp_echanges.envoyer` (texte éventuellement modifié, ou modèle) :
    {"envoi", "brouillon"}. Réservé d'abord (`envoi_en_cours`, sous le verrou du fichier) : une seconde décision
    simultanée reçoit WhatsappRefus `occupee`. Succès -> `envoye` ; refus ou panne -> retour à `attente`, l'erreur
    remonte telle quelle (409 des règles, 402 du plafond, 502 de Kapso). Le message part vers `identite` telle que
    donnée ; le brouillon est rangé sous la clé canonique. Appelé par la route `decider` et par le mode auto."""
    from app.services import whatsapp as WA, whatsapp_echanges as WE
    WA.destinataire(identite)
    pid = _compte_de(cid, eid)
    cle, groupe = canonique(cid, identite)
    envoi, cree_le = _reserver(eid, pid, cle, groupe, texte)
    try:
        r = await WE.envoyer(cid, identite, envoi)
    except BaseException:
        _conclure(eid, pid, cle, groupe, cree_le, "attente")
        raise
    b = _conclure(eid, pid, cle, groupe, cree_le, "envoye")
    return {"envoi": r, "brouillon": b}


def rejeter_brouillon(cid: str, eid: str, identite: str) -> dict:
    """Rejette le brouillon décidable du contact (`rejete`). BrouillonAbsent, WhatsappRefus `occupee` pendant un envoi."""
    from app.services import whatsapp as WA
    WA.destinataire(identite)
    pid = _compte_de(cid, eid)
    cle, groupe = canonique(cid, identite)

    def geste(b):
        maintenant = datetime.now(timezone.utc)
        if b and b.get("etat") == "envoi_en_cours" and not _decidable(b, maintenant):
            raise WA.WhatsappRefus("ce brouillon est déjà en cours d'envoi", "occupee")
        if not _decidable(b, maintenant):
            raise BrouillonAbsent("aucun brouillon en attente pour ce contact")
        b["etat"] = "rejete"
        b["decide_le"] = _maintenant()
        b.pop("envoi_depuis", None)
        return b
    return _modifier(eid, pid, cle, geste, groupe)


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
    pid = _compte_de(cid, eid)
    cle, _groupe = canonique(cid, identite)                  # tel: et bsuid: d'un même contact : un seul verrou
    verrou = _verrou(cid, cle)
    if verrou.locked():
        return _res(None, None, "occupee")
    async with verrou:
        try:
            return await _rediger(cid, eid, pid, identite, langue)
        finally:
            if _VERROUS.get((cid, cle)) is verrou:
                _VERROUS.pop((cid, cle), None)


async def _rediger(cid: str, eid: str, pid: str, identite: str, langue: str) -> dict:
    from app.services import whatsapp as WA
    texte, stop = await _fil(cid, identite)
    cle, groupe = canonique(cid, identite)                  # relu : la lecture a pu lier un alias
    if stop:
        return _res(None, None, "stop")
    if texte is None:
        return _res(None, None, "sans_entrant")
    agent = WA.reglages(eid)["agent"]
    raison = declencheur_humain(texte, agent.get("mots_humain"))
    if raison:
        ranger(eid, pid, cle, "humain", None, raison, groupe)
        return _res("humain", None, "declencheur")
    if not cle_presente():
        return _res(None, None, "sans_cle")
    return await _boucle(cid, eid, pid, identite, langue, agent, cle, groupe)


async def _boucle(cid: str, eid: str, pid: str, identite: str, langue: str, agent: dict, cle: str,
                  groupe: list) -> dict:
    modele = MT.modele_agent()
    outils = agent_boites.definitions_pour(AGENT)
    sys_ = systeme(eid, agent, langue)
    msgs: list[dict] = [{"role": "user", "content": CONSIGNE[langue].format(identite=identite)}]
    ctx = ao.Ctx(cid=f"wa:{cid}:{identite}", espace_id=eid, lang=langue, agent=AGENT, compte_id=cid, identite=identite)
    ref = f"{cid}:{cle}"
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
                    ranger(eid, pid, cle, "humain", carte, raison, groupe)
                    return _res("humain", carte, "carte")
                ranger(eid, pid, cle, "attente", carte, None, groupe)
                return _res("attente", carte, "carte")
            tr = {"type": "tool_result", "tool_use_id": b.get("id"), "content": ao.pour_modele(res)}
            if not res.get("ok"):
                tr["is_error"] = True
            resultats.append(tr)
        msgs.append({"role": "user", "content": resultats})
    return _res(None, None, "max_tours")
