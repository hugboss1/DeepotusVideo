# -*- coding: utf-8 -*-
"""t311 tâche 5 (27/10/2026) — le relevé de fond WhatsApp et le mode `auto` de l'agent.

`releve_loop()` (lancée par le lifespan de `app.main`) attend DELAI_DEMARRAGE, puis appelle `releve_tick(marqueur)` toutes
les INTERVALLE secondes (motif `marketing.schedule_loop` : une panne n'arrête pas la boucle, une annulation avalée est
respectée). Aucun `espaces.lire()` avant le premier tour (piège t210) ; sans clé Kapso, un tour ne fait RIEN.

Un tour, pour chaque compte whatsapp RELIÉ (`WHATSAPP_PHONE_ID` posé, lu brut dans `comptes.json`) d'un espace non archivé
(`espaces_brut.archive`) dont l'agent est actif (`whatsapp.reglages(eid)["agent"]`, lu sans `espaces.lire()`) — ou,
agent inactif, dont l'espace attend une réponse de validation client (`whatsapp_validation.en_attente` : le crochet de
validation seul passe alors, rien d'autre) :
  · lit les messages chez Kapso depuis le marqueur du compte (`whatsapp_echanges.lire`, qui journalise chaque entrant une
    fois : STOP et accords à jour) ; au premier tour d'un compte, seuls les entrants des 10 dernières minutes sont neufs
    (jamais de réponse à l'historique au démarrage) ; `marqueur[cid]` = ISO du plus récent entrant vu (EN MÉMOIRE) ;
  · chaque entrant neuf passe d'abord par le crochet de validation (`whatsapp_validation.traiter_reponse`, tâche 6) :
    True = message consommé ;
  · les autres sont regroupés par contact (clé canonique `agent_whatsapp.canonique`) ; contact en STOP ou brouillon à
    l'état `humain` : rien ; sinon accusé de lecture « en train d'écrire » sur son dernier entrant, puis
      hors horaires : `message_hors_horaires` (non vide) — `auto` : rangé en brouillon puis envoyé, au plus une fois par
        contact et par jour local ; `brouillon` : rangé en brouillon ;
      dans les horaires : `agent_whatsapp.rediger` ; en `auto`, une carte `reponse_whatsapp` part si `auto_jour` du jour
        local < `plafond_jour_contact` et si le texte ne cite aucun mot d'argent ni montant absent de la fiche (persona
        brut) ; sinon le brouillon reste.
  Un envoi automatique passe TOUJOURS par `agent_whatsapp.envoyer_brouillon` (réservation `envoi_en_cours`, puis
  `whatsapp_echanges.envoyer` : règles, devis, plafonds) ; `auto_jour` n'augmente qu'après un envoi réussi.
Jamais deux réponses au même entrant : avant tout geste, `agent_whatsapp.noter_traite` pose `traite_jusqu_a` (= `quand` du
dernier entrant du contact) dans l'entrée du contact de `whatsapp_brouillons.json` ; un entrant dont `quand` <=
`traite_jusqu_a` n'est plus traité, même marqueur perdu (redémarrage). Une entrée peut donc exister SANS `etat` ni carte
(trace seule) : elle signifie « aucun brouillon ». Repli pour une entrée sans `traite_jusqu_a` : `cree_le`/`decide_le`.
Relecture finale (27/10) : un entrant CONSOMMÉ par le crochet de validation est noté traité (`noter_traite`) après le tour
de l'agent ; un contact `pris` (« Prendre le fil ») est noté traité puis laissé à la personne (ni accusé ni rédaction) ;
`agent.plafond_redactions_jour` borne les `rediger` du relevé par contact et par jour local (`redactions_jour`) ; en
`auto`, tout nombre absent de la fiche et les mots de `MOTS_ARGENT_SORTANT` gardent le brouillon ; un brouillon
`incertain` n'est jamais envoyé automatiquement (refus `incertain` de `envoyer_brouillon`).
Compte supprimé (ou espace disparu) pendant ou entre deux tours : sauté sans rien écrire. Toute autre exception d'un compte
est journalisée par `type(e).__name__` seulement, et le tour continue. Aucun texte de message, aucune clé au journal.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loguru import logger

from app.services import agent_whatsapp as AW, comptes, espaces_brut

INTERVALLE = 120                      # secondes entre deux tours (Kapso Free : 100 requêtes/min)
DELAI_DEMARRAGE = 30                  # secondes avant le premier tour (jamais `espaces.lire()` au démarrage)
PREMIER_TOUR = timedelta(minutes=10)  # au premier tour d'un compte, seuls les entrants plus récents sont neufs
JOURS_GARDES = 7                      # `auto_jour` ne garde que les derniers jours
_VUS = "_vus"                         # marqueur[_VUS][cid] : ids des entrants vus à la seconde du marqueur
_MONTANT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:[€$£]|eur\b|euros?\b|dollars?\b)|[€$£]\s*(\d+(?:[.,]\d+)?)")
_NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
_MOT = re.compile(r"\S+")
VOISINAGE = 3                         # un nombre à 3 mots au plus d'un mot d'argent est un montant
LIBELLE_CARTE = "Réponse WhatsApp à envoyer"


def _horloge() -> datetime:
    """HOOK DE BANC : l'heure (UTC)."""
    return datetime.now(timezone.utc)


async def _dormir(secondes: float) -> None:
    """HOOK DE BANC : l'attente de la boucle."""
    await asyncio.sleep(secondes)


# ---- aides pures ------------------------------------------------------------------------------------------------------

def _date(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _jour_local(agent: dict, maintenant: datetime) -> str:
    """Le jour (AAAA-MM-JJ) de `maintenant` dans le fuseau des horaires de l'agent (UTC si le fuseau est illisible)."""
    try:
        tz = ZoneInfo(((agent or {}).get("horaires") or {}).get("fuseau") or "UTC")
    except Exception:  # noqa: BLE001
        tz = timezone.utc
    d = maintenant if maintenant.tzinfo else maintenant.replace(tzinfo=timezone.utc)
    return d.astimezone(tz).date().isoformat()


def _montants(texte_plat: str) -> set:
    """Les montants d'un texte (minuscules, sans accents) : nombres accolés à une devise, et nombres à VOISINAGE mots au
    plus d'un mot de `agent_whatsapp.MOTS_ARGENT_SORTANT` (« le prix est de 30 »). Virgule décimale ramenée au point."""
    out = {(m.group(1) or m.group(2)).replace(",", ".") for m in _MONTANT.finditer(texte_plat)}
    mots = list(_MOT.finditer(texte_plat))
    for m in AW.MOTS_ARGENT_SORTANT.finditer(texte_plat):
        i = next((k for k, w in enumerate(mots) if w.start() <= m.start() < w.end()), None)
        if i is None:
            continue
        for w in mots[max(0, i - VOISINAGE):i + VOISINAGE + 1]:
            out.update(n.replace(",", ".") for n in _NOMBRE.findall(w.group(0)))
    return out


def montant_hors_fiche(texte: str, eid: str) -> bool:
    """Le texte cite-t-il un mot d'argent (`agent_whatsapp.MOTS_ARGENT_SORTANT` : devises, %, prix, tarif, coût, gratuit,
    remise, devis…) absent de la fiche, un montant (`_montants` : nombre + devise, ou nombre voisin d'un mot d'argent)
    que la fiche ne porte pas, ou N'IMPORTE QUEL nombre (entier, décimal, pourcentage) qui n'est pas tel quel dans la
    fiche ? Fiche = persona brut de l'espace sérialisé ; comparaison en minuscules, sans accents."""
    fiche = AW._plat(json.dumps(espaces_brut.persona(eid), ensure_ascii=False))
    t = AW._plat(texte)
    if any(m.group(0) not in fiche for m in AW.MOTS_ARGENT_SORTANT.finditer(t)):
        return True
    if set(_NOMBRE.findall(t)) - set(_NOMBRE.findall(fiche)):
        return True                              # relecture finale : tout nombre absent de la fiche garde le brouillon
    return bool(_montants(t) - _montants(fiche))


def _compteur(b, jour: str) -> int:
    aj = (b or {}).get("auto_jour")
    n = aj.get(jour) if isinstance(aj, dict) else 0
    return n if isinstance(n, int) and not isinstance(n, bool) and n > 0 else 0


def _sous_plafond(b, agent: dict, jour: str) -> bool:
    p = (agent or {}).get("plafond_jour_contact")
    return isinstance(p, int) and _compteur(b, jour) < p


def _deja_traite(b, quand) -> bool:
    """Le brouillon du contact dit-il que l'entrant daté `quand` est déjà traité ? `traite_jusqu_a` >= `quand` (posé par
    le relevé avant tout geste) ; `cree_le`/`decide_le` ne servent de repli que pour une entrée SANS `traite_jusqu_a`
    (sinon une décision humaine prise après un entrant neuf ferait ignorer cet entrant pour toujours)."""
    q = _date(quand)
    if q is None or not isinstance(b, dict):
        return False
    t = _date(b.get("traite_jusqu_a"))
    if t is not None:
        return t >= q
    return any(d is not None and d >= q for d in (_date(b.get(k)) for k in ("cree_le", "decide_le")))


def _carte(texte: str) -> dict:
    return {"type": "carte", "genre": "reponse_whatsapp", "libelle": LIBELLE_CARTE, "etat": "proposee",
            "action": "envoyer_whatsapp", "arguments": {"texte": texte}}


def _comptes_relies() -> list:
    """[(cid, eid, phone_id)] des comptes whatsapp reliés, lus BRUTS dans comptes.json (sans secret ni vérification)."""
    out = []
    for cid, e in (comptes._lire().get("comptes") or {}).items():
        if not isinstance(e, dict) or e.get("plateforme") != "whatsapp":
            continue
        pid = str((e.get("publics") or {}).get("WHATSAPP_PHONE_ID") or "").strip()
        eid = e.get("espace_id")
        if pid and isinstance(eid, str) and eid:
            out.append((cid, eid, pid))
    return out


# ---- un tour ---------------------------------------------------------------------------------------------------------

async def releve_tick(marqueur: dict, maintenant: datetime | None = None) -> dict:
    """Un tour du relevé (voir l'en-tête du module), appelable par un banc. `marqueur` : état gardé d'un tour à l'autre
    (`marqueur[cid]` = ISO du dernier entrant vu). Rend {"comptes", "neufs", "envoyes", "erreurs"}."""
    rapport = {"comptes": 0, "neufs": 0, "envoyes": 0, "erreurs": 0}
    if not comptes.cle_kapso():
        return rapport
    from app.services import whatsapp as WA, whatsapp_validation as _WV   # tâche 6 : le crochet de validation
    now = maintenant or _horloge()
    now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    suivis = set()
    for cid, eid, pid in _comptes_relies():
        try:
            if espaces_brut.archive(eid):
                continue
            agent = WA.reglages(eid)["agent"]
            actif = bool(agent.get("actif"))
            if not actif and not await _WV.en_attente(eid, now):
                continue                         # agent inactif et aucune validation client en attente : rien à lire
            suivis.add(cid)
            rapport["comptes"] += 1
            await _releve_compte(cid, eid, pid, agent, marqueur, now, rapport, _WV, seulement_validation=not actif)
        except asyncio.CancelledError:
            raise
        except KeyError:
            suivis.discard(cid)                  # compte supprimé ou espace disparu pendant le tour : sauté, rien écrit
        except Exception as e:  # noqa: BLE001 — jamais une trace ni un texte : le nom du type seulement
            rapport["erreurs"] += 1
            logger.warning(f"relevé WhatsApp : compte {cid} ignoré ce tour ({type(e).__name__})")
    vus = marqueur.get(_VUS) if isinstance(marqueur.get(_VUS), dict) else {}
    for k in [k for k in marqueur if k != _VUS and k not in suivis]:
        marqueur.pop(k, None)                    # supprimé, archivé, inactif : un retour repart de 10 minutes
    for k in [k for k in vus if k not in suivis]:
        vus.pop(k, None)
    return rapport


async def _lire_neufs(cid: str, marqueur: dict, now: datetime) -> list:
    """Les entrants neufs du compte (du plus ancien au plus récent) ; met à jour le marqueur."""
    from app.services import whatsapp_echanges as WE
    vus_tous = marqueur.setdefault(_VUS, {})
    depuis = _date(marqueur.get(cid)) if marqueur.get(cid) else None
    if depuis is None:
        depuis, vus = now - PREMIER_TOUR, set()
    else:
        vus = set(vus_tous.get(cid) or [])
    msgs, cur = [], None
    for _ in range(WE.PAGES_MAX):
        page = await WE.lire(cid, depuis=depuis.isoformat(timespec="seconds"), apres=cur)
        msgs += [m for m in page.get("messages") or [] if isinstance(m, dict)]
        cur = page.get("suivant")
        if not cur:
            break
    entrants = [(d, m) for m in msgs if m.get("sens") == "entrant" and m.get("id") and m.get("identite")
                for d in [_date(m.get("quand"))] if d is not None and d >= depuis]
    neufs = sorted(((d, m) for d, m in entrants if m["id"] not in vus), key=lambda x: x[0])
    haut = max([depuis] + [d for d, _m in entrants])
    marqueur[cid] = haut.isoformat(timespec="seconds")
    vus_tous[cid] = sorted({m["id"] for d, m in entrants if d == haut} | (vus if haut == depuis else set()))
    return [m for _d, m in neufs]


async def _releve_compte(cid, eid, pid, agent, marqueur, now, rapport, wv, seulement_validation=False) -> None:
    """Un compte : ses entrants neufs passent par le crochet de validation, puis (agent actif) par l'agent.
    `seulement_validation` (agent inactif, validation client en attente) : le crochet seul, rien d'autre."""
    neufs = await _lire_neufs(cid, marqueur, now)
    rapport["neufs"] += len(neufs)
    restants, consommes = [], []
    for m in neufs:                              # le crochet de validation passe AVANT tout le reste
        try:                                     # contrat asynchrone (un résultat attendable est attendu)
            res = wv.traiter_reponse(cid, eid, m) if wv is not None else False
            if inspect.isawaitable(res):
                res = await res
            if res is True:
                consommes.append(m)
                continue
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — même KeyError : le crochet ne fait jamais sauter le compte
            logger.warning(f"relevé WhatsApp : réponse de validation non traitée sur le compte {cid} "
                           f"({type(e).__name__})")
        restants.append(m)
    if not seulement_validation:
        await _agent_compte(cid, eid, pid, agent, restants, now, rapport)
    _noter_consommes(cid, eid, pid, consommes)   # pas après un KeyError (compte supprimé) : rien n'est écrit


def _noter_consommes(cid, eid, pid, consommes) -> None:
    """Relecture finale I1 : un message consommé par le crochet de validation est noté traité (`traite_jusqu_a`) pour
    son contact, APRÈS le tour de l'agent (un texte du même contact, plus ancien que le bouton, reste traité ce tour) :
    un redémarrage ne le rejoue pas. Une panne ici est journalisée par son type, sans faire sauter le compte."""
    for m in consommes:
        try:
            cle, groupe = AW.canonique(cid, m["identite"])
            AW.noter_traite(eid, pid, cle, m["quand"], groupe)
        except KeyError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning(f"relevé WhatsApp : réponse de validation non notée sur le compte {cid} ({type(e).__name__})")


async def _agent_compte(cid, eid, pid, agent, restants, now, rapport) -> None:
    groupes: dict = {}
    for m in restants:
        cle, groupe = AW.canonique(cid, m["identite"])
        groupes.setdefault(cle, (groupe, []))[1].append(m)
    for cle, (groupe, ms) in groupes.items():
        try:
            if await _traiter_contact(cid, eid, pid, agent, cle, groupe, ms, now):
                rapport["envoyes"] += 1
        except (asyncio.CancelledError, KeyError):
            raise
        except Exception as e:  # noqa: BLE001
            rapport["erreurs"] += 1
            logger.warning(f"relevé WhatsApp : contact ignoré ce tour sur le compte {cid} ({type(e).__name__})")


async def _traiter_contact(cid, eid, pid, agent, cle, groupe, ms, now) -> bool:
    """Un contact qui a écrit depuis le dernier tour. Rend True si un message est parti."""
    from app.services import whatsapp as WA, whatsapp_echanges as WE
    stops = WA.etat(cid)["stops"]
    if any(i in stops for i in set(groupe) | {m["identite"] for m in ms}):
        return False
    b = AW.brouillons(eid, pid).get(cle)
    if (b or {}).get("etat") == "humain":
        return False
    dernier = ms[-1]
    identite = dernier["identite"]
    if _deja_traite(b, dernier.get("quand")):
        return False                             # marqueur perdu (redémarrage) ou relu : jamais deux réponses
    AW.noter_traite(eid, pid, cle, dernier["quand"], groupe)   # avant tout geste : une panne n'entraîne pas de redite
    if (b or {}).get("pris") is True:
        return False                             # « Prendre le fil » : une personne répond, l'agent se tait (I2)
    try:
        await WE.marquer_lu(cid, str(dernier["id"]), ecrit=True)
    except KeyError:
        raise
    except Exception as e:  # noqa: BLE001 — un accusé manqué n'empêche pas la réponse
        logger.warning(f"relevé WhatsApp : accusé de lecture non posé sur le compte {cid} ({type(e).__name__})")
    jour = _jour_local(agent, now)
    auto = agent.get("mode") == "auto"
    if not WA.dans_horaires(agent, now):
        texte = str(agent.get("message_hors_horaires") or "").strip()
        if not texte or (auto and (b or {}).get("hors_jour") == jour):
            return False
        if (b or {}).get("etat") in ("attente", "envoi_en_cours"):
            return False                         # un brouillon attend le geste de l'utilisateur : jamais écrasé
        AW.ranger(eid, pid, cle, "attente", _carte(texte), "hors_horaires", groupe)
        if not auto or not _sous_plafond(b, agent, jour):
            return False
        return await _envoyer_auto(cid, eid, pid, identite, cle, groupe, jour, hors=True)
    if not _compter_redaction(eid, pid, cle, groupe, agent, jour):
        return False                             # borne de rédactions du contact atteinte : rien (déjà noté traité)
    r = await AW.rediger(cid, eid, identite)
    carte = r.get("carte") if isinstance(r.get("carte"), dict) else {}
    if not auto or r.get("etat") != "attente" or carte.get("genre") != "reponse_whatsapp":
        return False
    texte = str((carte.get("arguments") or {}).get("texte") or "")
    if not _sous_plafond(AW.brouillons(eid, pid).get(cle), agent, jour) or montant_hors_fiche(texte, eid):
        return False
    return await _envoyer_auto(cid, eid, pid, identite, cle, groupe, jour, hors=False)


def _compter_redaction(eid, pid, cle, groupe, agent, jour) -> bool:
    """Borne du coût du modèle par contact (`plafond_redactions_jour`) : sous le verrou du fichier, si
    `redactions_jour[jour]` < la borne, l'incrémente (AVANT l'appel : un appel en panne a pu coûter) et rend True ;
    sinon rend False sans rien écrire. Seuls les `rediger` du relevé comptent (pas les gestes de l'utilisateur)."""
    p = (agent or {}).get("plafond_redactions_jour")
    p = p if isinstance(p, int) and not isinstance(p, bool) else 0
    pris = []

    def geste(b):
        b = b if b is not None else {"carte": None, "auto_jour": {}}
        rj = {k: v for k, v in (b.get("redactions_jour") or {}).items()
              if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)} \
            if isinstance(b.get("redactions_jour"), dict) else {}
        n = rj.get(jour, 0) if rj.get(jour, 0) > 0 else 0
        if n >= p:
            return None
        rj[jour] = n + 1
        b["redactions_jour"] = dict(sorted(rj.items())[-JOURS_GARDES:])
        pris.append(1)
        return b
    AW._modifier(eid, pid, cle, geste, groupe)
    return bool(pris)


async def _envoyer_auto(cid, eid, pid, identite, cle, groupe, jour, *, hors: bool) -> bool:
    """Envoie le brouillon du contact par `envoyer_brouillon` ; succès -> `auto_jour[jour]` + 1 (et `hors_jour` pour le
    message d'absence). Un refus ou une panne laisse le brouillon (rendu à `attente` par `envoyer_brouillon`)."""
    try:
        await AW.envoyer_brouillon(cid, eid, identite)
    except AW.BrouillonAbsent:
        logger.warning(f"relevé WhatsApp : envoi automatique sans brouillon sur le compte {cid}")
        return False
    except KeyError:
        raise
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", "")
        code = code if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,40}", code) else ""
        logger.warning(f"relevé WhatsApp : envoi automatique non fait sur le compte {cid} "
                       f"({type(e).__name__}{' ' + code if code else ''})")
        return False

    def geste(b):
        if not b:
            return None
        aj = {k: v for k, v in (b.get("auto_jour") or {}).items()
              if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)} \
            if isinstance(b.get("auto_jour"), dict) else {}
        aj[jour] = _compteur(b, jour) + 1
        b["auto_jour"] = dict(sorted(aj.items())[-JOURS_GARDES:])
        if hors:
            b["hors_jour"] = jour
        return b
    AW._modifier(eid, pid, cle, geste, groupe)
    return True


# ---- la boucle -------------------------------------------------------------------------------------------------------

async def releve_loop() -> None:
    """Le relevé de fond : DELAI_DEMARRAGE d'abord, puis un tour toutes les INTERVALLE secondes. Une panne d'un tour est
    journalisée (nom du type) et la boucle continue ; une annulation avalée pendant un tour est respectée."""
    await _dormir(DELAI_DEMARRAGE)
    logger.info(f"relevé WhatsApp démarré ({INTERVALLE} s)")
    marqueur: dict = {}
    while True:
        try:
            await releve_tick(marqueur)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.error(f"relevé WhatsApp : tour en échec ({type(e).__name__})")
        tache = asyncio.current_task()
        if tache is not None and tache.cancelling():
            raise asyncio.CancelledError
        await _dormir(INTERVALLE)
