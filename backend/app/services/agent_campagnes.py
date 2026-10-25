# -*- coding: utf-8 -*-
"""La boucle de l'agent Campagnes (t285a, 23/10/2026, spec §4.1, §4.2, §4.4, §5).

Un message de l'utilisateur = une boucle : envoyer au modèle → exécuter les outils GRATUITS demandés → renvoyer leurs
résultats (`tool_result`) → … jusqu'à une réponse finale, une CARTE (elle attend l'utilisateur), le plafond du message
ou MAX_TOURS. Tout est écrit par `agent_store.ajouter` : le message de l'utilisateur, puis un message « agent » par tour.

Dépense, « devis par message » (décidé le 23/10) :
- `devis_message` rend le plafond en dollars de TOUTE la réponse : MAX_TOURS × (contexte + SORTIE_MAX) jetons au tarif
  du modèle de l'agent (`moteurs_texte.modele_agent()`, lu à chaud). L'écran l'affiche ; l'envoi vaut accord ;
- avant CHAQUE appel du modèle : le tour est chiffré ; si le cumul du message plus ce chiffre dépasse le plafond,
  arrêt net SANS appel, avec une carte « continuer » qui porte un nouveau devis ; sinon `plafonds.verifier` (catégorie
  « campagnes », ref = conversation, espace = celui DE LA CAMPAGNE) — un refus 402 sort en évènement `erreur` ;
- après chaque appel : le coût RÉEL (jetons rendus par l'API) rejoint le cumul du message et celui de la conversation ;
- le message de l'utilisateur n'est écrit qu'après la PREMIÈRE garde passée : un refus ne laisse aucun orphelin ;
- sans clé Anthropic : RuntimeError("sans_cle") avant toute écriture (T7 le rend en 503).

Évènements (générateur asynchrone) : {"type": "texte"|"outil"|"carte"|"fin"|"erreur", ...}. `fin` et `erreur` sont
terminaux.
"""
from __future__ import annotations

import asyncio
import json
import math
from typing import AsyncIterator

from fastapi import HTTPException

from app.services import (agent_aide, agent_boites, agent_format as fmt, agent_outils as ao, agent_store, espaces,
                          moteurs_texte as MT, plafonds, pricing)

MAX_TOURS = 8
SORTIE_MAX = 2000                     # jetons de sortie par tour
CATEGORIE = "campagnes"
DOCS = agent_aide.DOSSIER / "campagnes"
IDS_JETON = ("deepotus", "deepotus-jeton")      # l'espace du jeton $DEEPOTUS (migration t200 : « deepotus »)
_MARQUES_JETON = ("$deepotus", "memecoin")      # persona dont le nom ou les mots d'ambiance disent le jeton
MAX_PERSONA = 6000                    # caractères de persona dans le système
CARS_PAR_JETON = 3                    # prudent : le français est plus près de 3 que de 4 caractères par jeton
SURCOUT_OUTILS = 1000                 # jetons que l'API ajoute d'elle-même (préambule d'outils, gabarit du système)
APPEL_TRONQUE = ("appel tronqué : la réponse a été coupée à la limite de sortie avant la fin de cet appel, il n'a "
                 "pas été exécuté ; recommence avec un appel plus court")
_VERROUS: dict[str, asyncio.Lock] = {}  # un seul `tour` à la fois par conversation (double envoi)
TEXTE_CONTINUER = {"fr": "Continue là où tu t'es arrêté.", "en": "Continue where you left off."}

ROLES = {
    "orienteur": "Rôle : **Orienteur**. L'utilisateur demande « que faire de ceci ? ». Propose deux ou trois suites "
                 "concrètes. N'ouvre aucun dossier (pas d'`ecrire_dossier`).",
    "campagnes": "Rôle : **Campagnes**. Mène la campagne complète, en suivant le circuit dans l'ordre, porte 1 "
                 "comprise.",
    "demonstrateur": "Rôle : **Démonstrateur**. Prépare une démonstration de l'application. N'ouvre aucun dossier "
                     "(pas d'`ecrire_dossier`).",
    "bilan": "Rôle : **Bilan** (lancé sur demande, après la campagne). Lis d'abord les posts de CETTE campagne et "
             "leurs chiffres avec `lire_planificateur` (campagne : true). Dis ce qui a marché et ce qui a raté, puis "
             "écris `bilan.md` et `apprentissages.md` (3 à 5 lignes) avec `ecrire_dossier`. Aucune autre action.",
}


# ---- le système ------------------------------------------------------------------------------------------------------

def _doc(nom: str) -> str:
    try:
        return (DOCS / nom).read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    except OSError:
        return ""


def espace_jeton(eid) -> bool:
    """L'espace est-il celui du jeton $DEEPOTUS ? Son id (`deepotus`, migration t200 ; `deepotus-jeton`), ou une
    persona marquée : `crypto`/`jeton` vrai, ou « $DEEPOTUS » / « memecoin » dans son nom ou ses mots d'ambiance."""
    if not isinstance(eid, str) or not eid:
        return False
    if eid in IDS_JETON:
        return True
    if eid not in espaces.lire()["espaces"]:
        return False
    p = espaces.persona(eid)
    if p.get("crypto") is True or p.get("jeton") is True:
        return True
    mots = [str(p.get("display_name") or "")] + [str(m) for m in (p.get("vibe_keywords") or [])]
    return any(m in x.lower() for x in mots for m in _MARQUES_JETON)


def persona_modele(eid) -> dict:
    """La persona de l'espace telle que le modèle la voit : sans `templates` ni `voice_ids` (t286 : le paquet du
    compagnon applique le MÊME filtre)."""
    return {k: v for k, v in espaces.persona(eid).items() if k not in ("templates", "voice_ids")}


def _partie_espace(eid) -> str:
    if not eid:
        return ("## Espace de marque\nAucun espace désigné pour cette conversation. Ne prends JAMAIS l'espace actif "
                "d'office : un outil qui en a besoin rend une carte pour que l'utilisateur le choisisse.")
    e = espaces.lire()["espaces"].get(eid) if isinstance(eid, str) else None
    if not e or e.get("archive"):
        return (f"## Espace de marque\nL'espace `{str(eid)[:40]}` est inconnu ou archivé : refuse le travail qui en "
                "dépend et dis pourquoi, sans repli sur un autre espace.")
    from app.services import contenus_espace
    persona = json.dumps(persona_modele(eid), ensure_ascii=False)
    if len(persona) > MAX_PERSONA:
        persona = persona[:MAX_PERSONA] + " …(tronqué ; `lire_espace` la rend en entier)"
    mots = contenus_espace._interdits(eid)
    return (f"## Espace de marque de la campagne\n{e.get('nom') or eid} (id `{eid}`). C'est SON espace : tout s'y "
            f"compte et s'y range, jamais dans l'espace actif.\nMots interdits : "
            f"{', '.join(mots) if mots else 'aucun'}.\nPersona :\n{persona}")


def systeme_pour(role, espace_id, langue: str) -> str:
    """CAMPAGNES.md + le rôle + l'espace (persona, mots interdits) + conformite-crypto.md pour l'espace du jeton
    SEULEMENT + la langue de réponse. Pure : la boucle (`systeme`) et le paquet du téléphone (L4.1) l'appellent, le
    texte est donc le même des deux côtés."""
    role = role if role in ROLES else "campagnes"
    parts = [_doc("CAMPAGNES.md"), "## Ton rôle pour cette conversation\n" + ROLES[role]]
    if role == "campagnes":
        modele = _doc("dossier-modele.md")
        if modele:
            parts.append("## dossier-modele.md\n" + modele)
    parts.append(_partie_espace(espace_id))
    if espace_jeton(espace_id):
        parts.append(_doc("conformite-crypto.md"))
    parts.append("## Langue\n" + ("Answer in English." if langue == "en" else "Réponds en français."))
    return "\n\n".join(x for x in parts if x)


def systeme(conv: dict, lang: str) -> str:
    """Le système de la boucle : celui du rôle et de l'espace DE LA CONVERSATION (`systeme_pour`)."""
    return systeme_pour(conv.get("role"), conv.get("espace_id"), lang)


# ---- l'historique au format de l'API ---------------------------------------------------------------------------------

def _texte_bloc(b: dict) -> str:
    t = b.get("type")
    if t == "texte":
        return str(b.get("texte") or "")
    if t == "resultat_outil":
        return f"[outil {b.get('outil')} : {b.get('resume')}]"
    if t == "carte":
        return f"[carte {b.get('genre')} « {b.get('libelle')} » : {b.get('etat')}]"
    if t == "porte":
        return f"[porte {b.get('numero')} : {b.get('etat')}]"
    return ""


def _historique(messages: list, texte: str | None = None) -> list[dict]:
    """Les messages écrits → messages de l'API, en texte, rôles alternés, premier et dernier `user`. Un tour d'outils
    passé est relu par ses résumés (les `tool_use` d'hier ne se rejouent pas)."""
    out: list[dict] = []

    def pousser(role: str, t: str):
        if not t.strip():
            return
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + t
        else:
            out.append({"role": role, "content": t})

    for m in messages or []:
        t = "\n".join(x for x in (_texte_bloc(b) for b in m.get("blocs") or [] if isinstance(b, dict)) if x)
        if m.get("role") == "agent":
            pousser("assistant", t)
        elif m.get("role") == "utilisateur":
            pousser("user", t)
        else:                                            # « fait », « outil » : un évènement de l'application
            pousser("user", "[évènement de l'application] " + t if t else "")
    if texte is not None:
        pousser("user", texte)
    if out and out[0]["role"] != "user":
        out.insert(0, {"role": "user", "content": "(suite de la conversation)"})
    return out


def _jetons(systeme_: str, messages: list, outils: list) -> int:
    """Jetons d'entrée d'un appel, estimés PAR EXCÈS (le plafond ne doit jamais être dépassé) : CARS_PAR_JETON
    caractères par jeton sur le système, les messages et le JSON des définitions d'outils, plus SURCOUT_OUTILS."""
    n = len(systeme_) + len(json.dumps(messages, ensure_ascii=False)) + len(json.dumps(outils, ensure_ascii=False))
    return -(-n // CARS_PAR_JETON) + SURCOUT_OUTILS


def _usd(op: dict) -> float:
    return float(pricing.estimate(op)["total_usd"])


# ---- devis et clé ----------------------------------------------------------------------------------------------------

def cle_presente() -> bool:
    return MT.configure("anthropic")


def devis_message(conv: dict, texte: str, lang: str = "fr") -> dict:
    """Le plafond en dollars de TOUTE la réponse : MAX_TOURS × (contexte + SORTIE_MAX) au tarif du modèle de l'agent.
    Rendu même sans clé (l'écran l'affiche ; c'est l'envoi qui est refusé)."""
    modele = MT.modele_agent()
    ctx = _jetons(systeme(conv, lang), _historique(conv.get("messages") or [], str(texte or "")), agent_boites.definitions_pour("campagnes"))
    in_tok, out_tok = MAX_TOURS * ctx, MAX_TOURS * SORTIE_MAX
    return {"plafond_usd": _usd(MT.op_tour(modele, in_tok, out_tok)), "in_tok": in_tok, "out_tok": out_tok,
            "modele": modele}


def _carte_continuer(devis: dict, motif: str, depense: float, lang: str, texte: str | None = None) -> dict:
    usd = float(devis["plafond_usd"])
    lib = (f"Continue: up to ${usd:.2f}" if lang == "en" else f"Continuer : ≤ {usd:.2f} $")
    args = {"motif": motif, "devis": devis, "depense_usd": round(depense, 6),
            "texte": texte if texte is not None else TEXTE_CONTINUER["en" if lang == "en" else "fr"]}
    return {"type": "carte", "genre": "continuer", "libelle": lib, "etat": "proposee", "devis": usd,
            "action": "continuer", "arguments": args}


# ---- la boucle -------------------------------------------------------------------------------------------------------

async def _conv(cid: str) -> dict:
    l = await agent_store.lire(cid)
    if l is None:
        raise KeyError(cid)
    if l.get("illisible"):
        raise agent_store.ConversationIllisible(f"conversation illisible : {cid}")
    return l


async def tour(cid: str, texte: str, plafond_usd: float, lang: str = "fr", *, origine: str = "pc",
               appareil: str | None = None) -> AsyncIterator[dict]:
    """Un message de l'utilisateur et la réponse de l'agent, au plus `plafond_usd` dollars (le devis accepté).
    `origine`/`appareil` (t286) : ceux du message de l'utilisateur — l'appareil du JETON quand il vient du téléphone."""
    lang = "en" if lang == "en" else "fr"
    if not cle_presente():                                # avant toute écriture : T7 rend 503
        raise RuntimeError("sans_cle")
    verrou = _VERROUS.setdefault(cid, asyncio.Lock())
    if verrou.locked():                                   # pris sans aucun await avant : aucun second tour en parallèle
        yield {"type": "erreur", "code": "occupee", "message": "conversation occupée"}
        return
    async with verrou:
        try:
            async for e in _tour(cid, texte, plafond_usd, lang, origine, appareil):
                yield e
        finally:
            if _VERROUS.get(cid) is verrou:
                _VERROUS.pop(cid, None)


async def _tour(cid: str, texte: str, plafond_usd: float, lang: str, origine: str = "pc",
                appareil: str | None = None) -> AsyncIterator[dict]:
    conv = await _conv(cid)
    texte = str(texte or "")
    try:
        plafond = float(plafond_usd or 0.0)
    except (TypeError, ValueError):
        plafond = 0.0
    if not math.isfinite(plafond) or plafond < 0:         # NaN ou infini désarmeraient la comparaison
        plafond = 0.0
    modele = MT.modele_agent()
    outils = agent_boites.definitions_pour("campagnes")
    sys_ = systeme(conv, lang)
    msgs = _historique(conv["messages"], texte)
    message_ecrit = False
    depense = 0.0

    for _n in range(MAX_TOURS):
        op = MT.op_tour(modele, _jetons(sys_, msgs, outils), SORTIE_MAX)
        if depense + _usd(op) > plafond + 1e-12:          # arrêt net : aucun appel au-delà du devis
            if message_ecrit:
                d = devis_message(await _conv(cid), TEXTE_CONTINUER[lang], lang)
                carte = _carte_continuer(d, "plafond", depense, lang)
                await agent_store.ajouter(cid, [fmt.nouveau_message("agent", [carte])])
            else:                                          # rien n'est parti : le même texte, avec un devis à jour
                carte = _carte_continuer(devis_message(conv, texte, lang), "plafond", 0.0, lang, texte)
            yield {"type": "carte", "carte": carte}
            yield {"type": "fin", "motif": "plafond", "cout_usd": depense}
            return
        try:
            garde = await plafonds.verifier(op, CATEGORIE, ref=cid, espace_id=conv.get("espace_id"))
        except HTTPException as e:
            if e.status_code != 402:
                raise
            yield {"type": "erreur", "code": "dz_plafond", "statut": 402, "detail": e.detail}
            return
        if not message_ecrit:
            await agent_store.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": texte}],
                                                                origine=origine, appareil=appareil)])
            message_ecrit = True
        try:
            r = await asyncio.to_thread(MT.converser, modele, sys_, msgs, outils, SORTIE_MAX)
        except Exception as e:  # noqa: BLE001 — HTTP, délai, réseau : un évènement, jamais une trace (clé ôtée par converser)
            await plafonds.noter_reel_lignes((garde or {}).get("lignes") or [], 0.0)   # rien n'a été facturé
            yield {"type": "erreur", "code": "sans_cle" if str(e) == "sans_cle" else "moteur", "message": str(e)[:300]}
            return
        cout = _usd(MT.op_tour(modele, r["in_tok"], r["out_tok"]))
        depense += cout
        await plafonds.noter_reel_lignes((garde or {}).get("lignes") or [], cout)   # les lignes de CE tour seulement
        tronque = r.get("arret") == "max_tokens"
        blocs_api = list(r.get("blocs") or [])
        msgs.append({"role": "assistant", "content": blocs_api})
        blocs: list[dict] = []
        evts: list[dict] = []
        for b in blocs_api:
            if b.get("type") == "text" and str(b.get("text") or "").strip():
                blocs.append({"type": "texte", "texte": str(b["text"])})
                evts.append({"type": "texte", "texte": str(b["text"])})
        appels = [b for b in blocs_api if b.get("type") == "tool_use"]
        resultats: list[dict] = []
        carte_vue = False
        for b in appels:
            if carte_vue:                                  # une carte attend l'utilisateur : rien d'autre ne s'exécute
                break
            nom = b.get("name")
            if tronque:                                    # entrée peut-être coupée : jamais exécutée
                blocs.append({"type": "resultat_outil", "outil": str(nom)[:60], "resume": APPEL_TRONQUE[:500], "ok": False})
                evts.append({"type": "outil", "nom": nom, "ok": False, "resume": APPEL_TRONQUE})
                resultats.append({"type": "tool_result", "tool_use_id": b.get("id"), "is_error": True,
                                  "content": json.dumps({"ok": False, "resume": APPEL_TRONQUE, "donnees": None},
                                                        ensure_ascii=False)})
                continue
            args = dict(b.get("input") or {}) if isinstance(b.get("input"), dict) else {}
            ligne = await _conv(cid)                       # l'espace DE LA CONVERSATION, la porte à jour
            if ligne.get("role") == "bilan" and nom == "lire_planificateur":
                args["campagne"] = True                    # le bilan lit les posts de CETTE campagne
            ctx = ao.Ctx(cid=cid, espace_id=ligne.get("espace_id"), lang=lang,
                         etat_porte=ligne.get("etat_porte") or "aucune", agent=CATEGORIE)
            res = await ao.executer(nom, args, ctx)
            resume = str(res.get("resume") or "")
            blocs.append({"type": "resultat_outil", "outil": str(nom)[:60], "resume": resume[:500],
                          "ok": bool(res.get("ok"))})  # t285 T9 : l'écran montre l'état, plus le résumé
            evts.append({"type": "outil", "nom": nom, "ok": bool(res.get("ok")), "resume": resume})
            tr = {"type": "tool_result", "tool_use_id": b.get("id"), "content": ao.pour_modele(res)}
            if not res.get("ok"):
                tr["is_error"] = True
            resultats.append(tr)
            if res.get("carte"):
                blocs.append(res["carte"])
                evts.append({"type": "carte", "carte": res["carte"]})
                carte_vue = True
        if not blocs:
            blocs.append({"type": "texte", "texte": ""})
        m = fmt.nouveau_message("agent", blocs)
        m["cout_paye"] = cout
        await agent_store.ajouter(cid, [m], cout_usd=cout)
        for e in evts:
            yield e
        if carte_vue:
            yield {"type": "fin", "motif": "carte", "cout_usd": depense}
            return
        if not appels:
            yield {"type": "fin", "motif": "reponse", "cout_usd": depense}
            return
        msgs.append({"role": "user", "content": resultats})

    d = devis_message(await _conv(cid), TEXTE_CONTINUER[lang], lang)
    carte = _carte_continuer(d, "max_tours", depense, lang)
    await agent_store.ajouter(cid, [fmt.nouveau_message("agent", [carte])])
    yield {"type": "carte", "carte": carte}
    yield {"type": "fin", "motif": "max_tours", "cout_usd": depense}
