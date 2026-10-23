# -*- coding: utf-8 -*-
"""Registre des conversations de l'agent interne (t285a, 23/10/2026).

L'index vit en base (table `agent_conversations`), le détail dans `conversation.json` : dans le dossier de campagne
quand `dossier` est réglé, sinon sous `campagnes/_conversations/<id>/`. Un message n'est jamais modifié : un changement
d'état de carte s'écrit comme un NOUVEAU message. L'import (conversation menée sur le téléphone) est idempotent par
empreinte ; un même id avec une autre empreinte est un conflit et ne remplace rien.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app import config
from app.services import agent_format as fmt
from app.services.storage import AgentConversation, async_session_factory

ROLES = ("orienteur", "campagnes", "demonstrateur", "bilan")
ETATS_PORTE = ("aucune", "porte1_proposee", "porte1_validee", "brouillons_crees")

_VERROU = asyncio.Lock()          # lecture-modification-écriture de conversation.json, un seul à la fois
_SUR = re.compile(r"[^a-z0-9]+")
_ESPACE_OK = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _racine() -> Path:
    return config.DATA_ROOT / "campagnes"


def _ligne(r: AgentConversation) -> dict:
    return {"id": r.id, "espace_id": r.espace_id, "role": r.role, "titre": r.titre, "etat_porte": r.etat_porte,
            "cout_usd": float(r.cout_usd or 0.0), "dossier": r.dossier, "origine": r.origine,
            "cree": r.cree.isoformat() if r.cree else None, "maj": r.maj.isoformat() if r.maj else None}


def _fichier(ligne: dict) -> Path:
    """conversation.json de la conversation : dans son dossier de campagne, sinon sous _conversations/<id>."""
    if ligne.get("dossier"):
        return Path(ligne["dossier"]) / "conversation.json"
    return _racine() / "_conversations" / ligne["id"] / "conversation.json"


class ConversationIllisible(ValueError):
    """conversation.json existe mais n'est pas lisible (JSON invalide ou pas une liste) : on n'écrit rien dessus."""


def _lire_messages_strict(f: Path) -> list[dict]:
    """Fichier absent = liste vide. Fichier présent mais illisible : copie `.corrompu-<horodatage>` puis
    ConversationIllisible ; l'original n'est ni supprimé ni écrasé."""
    if not f.is_file():
        return []
    try:
        v = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(v, list):
            return v
    except (OSError, ValueError):
        pass
    try:
        shutil.copy2(f, f.with_name(f.name + ".corrompu-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")))
    except OSError:
        pass
    raise ConversationIllisible(f"conversation illisible : {f}")


def _lire_messages(f: Path) -> list[dict]:
    """Tolérant, pour l'affichage seulement : [] si illisible (voir `lire`, champ `illisible`)."""
    try:
        return _lire_messages_strict(f)
    except ConversationIllisible:
        return []


def _ecrire_messages(f: Path, messages: list[dict]) -> None:
    """Écriture atomique : fichier temporaire puis os.replace."""
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(messages, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, f)


async def _ligne_de(cid: str) -> AgentConversation | None:
    async with async_session_factory() as s:
        return (await s.execute(select(AgentConversation).where(AgentConversation.id == cid))).scalar_one_or_none()


async def _lire_sain(cid: str, absent_ok: bool = False) -> dict | None:
    """Comme `lire`, mais refuse (ConversationIllisible) si le fichier est corrompu : pour les chemins qui écrivent."""
    r = await _ligne_de(cid)
    if r is None:
        if absent_ok:
            return None
        raise KeyError(cid)
    ligne = _ligne(r)
    ligne["messages"] = _lire_messages_strict(_fichier(ligne))
    return ligne


async def creer(role: str, espace_id: str | None, titre: str, *, origine: str = "pc", id: str | None = None) -> dict:
    if role not in ROLES:
        raise ValueError(f"rôle inconnu : {role!r}")
    if origine not in fmt.ORIGINES:
        raise ValueError(f"origine inconnue : {origine!r}")
    now = datetime.utcnow()
    r = AgentConversation(id=id or str(uuid.uuid4()), espace_id=espace_id, role=role, titre=(titre or "")[:200],
                          etat_porte="aucune", cout_usd=0.0, dossier=None, origine=origine, cree=now, maj=now)
    async with async_session_factory() as s:
        s.add(r)
        await s.commit()
    return _ligne(r)


async def lire(cid: str) -> dict | None:
    r = await _ligne_de(cid)
    if r is None:
        return None
    ligne = _ligne(r)
    try:
        ligne["messages"] = _lire_messages_strict(_fichier(ligne))
    except ConversationIllisible:
        ligne["messages"] = []
        ligne["illisible"] = True
    return ligne


async def _modifier(cid: str, *, cout: float = 0.0, **champs) -> None:
    async with async_session_factory() as s:
        r = (await s.execute(select(AgentConversation).where(AgentConversation.id == cid))).scalar_one_or_none()
        if r is None:
            raise KeyError(cid)
        r.cout_usd = float(r.cout_usd or 0.0) + float(cout)
        for k, v in champs.items():
            setattr(r, k, v)
        r.maj = datetime.utcnow()
        await s.commit()


async def ajouter(cid: str, messages: list[dict], cout_usd: float = 0.0) -> None:
    """Ajoute des messages en fin de conversation et cumule le coût. Un message invalide lève ValueError, rien
    n'est écrit."""
    for m in messages:
        e = fmt.valider(m)
        if e:
            raise ValueError("; ".join(e))
    if cout_usd < 0:
        raise ValueError("cout_usd négatif")
    async with _VERROU:
        l = await _lire_sain(cid)
        _ecrire_messages(_fichier(l), l["messages"] + list(messages))
        await _modifier(cid, cout=cout_usd)


async def importer(conv: dict) -> dict:
    """Importe une conversation menée ailleurs. Idempotent : même id et même empreinte = ignoré ; même id et autre
    empreinte = conflit (rien d'écrasé) ; id inconnu = ajouté s'il est valide. Le `cout_paye` des seuls messages
    ajoutés rejoint le cumul. La clé `invalides` n'apparaît que s'il y en a."""
    res = {"ajoutes": 0, "ignores": 0, "conflits": []}
    if not isinstance(conv, dict) or not isinstance(conv.get("id"), str) or not conv["id"]:
        raise ValueError("conversation : id requis")
    async with _VERROU:
        l = await _lire_sain(conv["id"], absent_ok=True)
        if l is None:
            await creer(conv.get("role") or "campagnes", conv.get("espace_id"), conv.get("titre") or "",
                        origine=conv.get("origine") or "telephone", id=conv["id"])
            l = await _lire_sain(conv["id"])
        connus = {m.get("id"): fmt.empreinte(m) for m in l["messages"]}
        neufs: list[dict] = []
        cout = 0.0
        for m in conv.get("messages") or []:
            e = fmt.valider(m)
            if e:
                res.setdefault("invalides", []).append({"id": m.get("id") if isinstance(m, dict) else None, "erreurs": e})
                continue
            emp = fmt.empreinte(m)
            if m["id"] in connus:
                if connus[m["id"]] == emp:
                    res["ignores"] += 1
                else:
                    res["conflits"].append(m["id"])
                continue
            connus[m["id"]] = emp
            neufs.append(m)
            cout += float(m.get("cout_paye") or 0.0)
        if neufs:
            _ecrire_messages(_fichier(l), l["messages"] + neufs)
            await _modifier(conv["id"], cout=cout)
        res["ajoutes"] = len(neufs)
    return res


def _confiner(texte: str, defaut: str) -> str:
    """Un nom de dossier sûr : minuscules, chiffres et tirets, jamais de séparateur ni de point."""
    s = _SUR.sub("-", str(texte or "").lower()).strip("-")
    return (s or defaut)[:60]


def dossier_campagne(espace_id: str, slug: str) -> Path:
    """campagnes/<espace>/<AAAA-MM-JJ>-<slug>, créé à la demande. Le slug est confiné ; un espace_id hostile lève
    ValueError."""
    if not isinstance(espace_id, str) or not _ESPACE_OK.match(espace_id):
        raise ValueError(f"espace_id invalide : {espace_id!r}")
    base = (_racine() / espace_id).resolve()
    p = (base / f"{datetime.now():%Y-%m-%d}-{_confiner(slug, 'campagne')}").resolve()
    if not p.is_relative_to(base):
        raise ValueError("dossier hors de l'espace")
    p.mkdir(parents=True, exist_ok=True)
    return p


async def regler_dossier(cid: str, chemin: str | Path) -> None:
    """Fixe le dossier de campagne et y déplace conversation.json s'il existait ailleurs."""
    cible = Path(chemin).resolve()
    if not cible.is_relative_to(_racine().resolve()):
        raise ValueError("dossier hors du dossier des campagnes")
    async with _VERROU:
        l = await _lire_sain(cid)
        nouveau = cible / "conversation.json"
        ancien = _fichier(l)
        _ecrire_messages(nouveau, l["messages"])
        await _modifier(cid, dossier=str(cible))
        try:
            if ancien.is_file() and ancien.resolve() != nouveau.resolve():
                ancien.unlink()
        except OSError:
            pass


async def regler_espace(cid: str, espace_id: str) -> bool:
    """t285a (T7) : l'espace d'une conversation qui n'en a pas encore (carte « espace » acceptée). Rend False, sans
    rien changer, si un AUTRE espace est déjà réglé : l'espace d'une campagne ne change jamais. Le même espace
    réappliqué rend True (une reprise après panne). L'appelant le valide."""
    async with async_session_factory() as s:
        r = (await s.execute(select(AgentConversation).where(AgentConversation.id == cid))).scalar_one_or_none()
        if r is None:
            raise KeyError(cid)
        if r.espace_id:
            return r.espace_id == str(espace_id)[:40]
        r.espace_id = str(espace_id)[:40]
        r.maj = datetime.utcnow()
        await s.commit()
    return True


async def regler_porte(cid: str, etat: str) -> None:
    if etat not in ETATS_PORTE:
        raise ValueError(f"état de porte inconnu : {etat!r}")
    await _modifier(cid, etat_porte=etat)
