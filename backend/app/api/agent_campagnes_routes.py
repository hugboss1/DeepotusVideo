# -*- coding: utf-8 -*-
"""Les routes LOCALES de l'agent Campagnes (t285a, T7, 23/10/2026, spec §5, §6, §7) — /api/agent/campagnes.

Boucle locale SEULEMENT ici (garde partagée `routes._require_localhost`) ; t286 les ouvrira aux appareils appairés.
- `POST /` {role, espace_id?, titre?} : crée la conversation (espace nommé : existant et non archivé, sinon 400) ;
- `GET /{cid}` : la conversation ; ajoute d'abord un message `fait` par carte `devis` acceptée dont le job est fini
  (DONE ou FAILED) — un seul par job, quel que soit le nombre de GET ;
- `POST /{cid}/devis` {texte} : le plafond en dollars du prochain message (rendu même sans clé) ;
- `POST /{cid}/message` {texte, plafond_usd} : la réponse en SSE (une ligne `data:` JSON par évènement). Sans clé
  Anthropic : 503 AVANT toute écriture. Le PREMIER évènement est tiré avant d'ouvrir le flux : un refus 402 de la
  garde (`dz_plafond`) au premier tour devient un vrai HTTP 402 (le dialogue des plafonds le rejoue avec
  `X-DZ-Plafond: confirme`) et « occupée » un 409 ; plus loin dans la boucle, un 402 reste un évènement `erreur`
  (les octets sont partis). `tour()` est mené sous `contextlib.aclosing` et la réponse ferme le flux même si le client
  coupe : le verrou de la conversation est toujours rendu ;
- `POST /{cid}/carte/{n}` {decision, job_id?, espace_id?} : `n` = rang (0, 1, …) de la carte parmi les cartes des
  messages `agent`. La décision s'écrit comme un message NEUF (`fait`, bloc carte, `arguments.carte = n`) : l'original
  n'est jamais modifié ; une carte déjà décidée = 409 ;
- `POST /{cid}/depot` : multipart `fichier` (texte extrait par marketing.extract_document_text) ou JSON {texte} →
  gardé pour `lire_document` ; JSON {url} → rendu comme texte pour le message de l'utilisateur, rien de téléchargé
  (la lecture reste à `lire_document`, sous ses gardes) ;
- `POST /importer` {conversation} : `agent_store.importer` (idempotent).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import math
import re

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services import agent_campagnes as AC, agent_format as fmt, agent_outils as AO, agent_store as ST, espaces

router = APIRouter()

MAX_CORPS = 8_000_000                  # JSON (une conversation importée tient très en dessous)
MAX_DEPOT_OCTETS = 15 * 1024 * 1024    # comme l'import d'un document de stratégie (/marketing/plan/import)
DECISIONS = ("acceptee", "refusee")
_JOB = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_VERROU = asyncio.Lock()               # décisions de cartes et blocs `fait` : relire puis écrire, un seul à la fois


# ---- gardes et lecture ------------------------------------------------------------------------------------------------
# Les gabarits d'erreur (scripts/i18n_l10_traductions.json) : un LITTÉRAL par HTTPException, traduit à la sortie.

def _introuvable() -> HTTPException:
    return HTTPException(404, "Conversation introuvable.")


def _illisible() -> HTTPException:
    return HTTPException(409, "Conversation illisible : son fichier est mis de côté, rien n'a été écrit.")


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    try:
        _require_localhost(request)
    except HTTPException:
        raise HTTPException(403, "L'agent Campagnes n'est accessible que depuis ce PC.") from None


async def _json(request: Request) -> dict:
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")
    morceaux, total = [], 0
    async for morceau in request.stream():
        total += len(morceau)
        if total > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(morceau)
    try:
        corps = json.loads(b"".join(morceaux) or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    if not isinstance(corps, dict):
        raise HTTPException(400, "Corps JSON attendu.")
    return corps


@contextlib.contextmanager
def _traduire():
    """Les erreurs du registre en HTTP. ConversationIllisible hérite de ValueError : attrapée AVANT lui."""
    try:
        yield
    except ST.ConversationIllisible:
        raise _illisible() from None
    except KeyError:
        raise _introuvable() from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


async def _conversation(cid: str, *, saine: bool = True) -> dict:
    l = await ST.lire(cid)
    if l is None:
        raise _introuvable()
    if saine and l.get("illisible"):
        raise _illisible()
    return l


def _espace_valide(eid) -> str:
    """Un espace NOMMÉ : existant et non archivé (vigilance 5) ; sinon 400, jamais de repli sur l'actif."""
    e = espaces.lire()["espaces"].get(eid) if isinstance(eid, str) and espaces.id_valide(eid) else None
    if not e or e.get("archive"):
        raise HTTPException(400, f"Espace inconnu ou archivé : {str(eid)[:40]}")
    return eid


def _lang(request: Request) -> str:
    from app.i18n import langue_requete
    return "en" if langue_requete(request) == "en" else "fr"


# ---- cartes -----------------------------------------------------------------------------------------------------------

def _cartes(messages: list) -> list[dict]:
    """Les cartes PROPOSÉES, dans l'ordre : celles des messages `agent` (les messages `fait` ne portent que des
    changements d'état). Leur rang est le `n` des routes."""
    return [b for m in messages if m.get("role") == "agent"
            for b in (m.get("blocs") or []) if isinstance(b, dict) and b.get("type") == "carte"]


def _etats(messages: list) -> dict[int, dict]:
    """n → le DERNIER bloc d'état écrit pour la carte n (messages `fait`)."""
    out: dict[int, dict] = {}
    for m in messages:
        if m.get("role") != "fait":
            continue
        for b in m.get("blocs") or []:
            n = ((b.get("arguments") or {}) if isinstance(b, dict) else {}).get("carte")
            if b.get("type") == "carte" and isinstance(n, int) and not isinstance(n, bool):
                out[n] = b
    return out


def _bloc_etat(carte: dict, n: int, etat: str, extra: dict, action: str | None = None) -> dict:
    """Le bloc d'un changement d'état de la carte n : genre, libellé, devis et action de l'original (ou `action`)."""
    b = {"type": "carte", "genre": carte.get("genre"), "libelle": str(carte.get("libelle") or ""), "etat": etat,
         "action": action or carte.get("action"), "arguments": {"carte": n, **extra}}
    if carte.get("devis") is not None:
        b["devis"] = carte["devis"]
    return b


async def _noter_faits(cid: str) -> None:
    """Un message `fait` par carte `devis` acceptée dont le job est fini (DONE ou FAILED), une seule fois par job.
    L'agent ne reprend JAMAIS seul : la carte devient « terminée » et porte l'action « continuer » (spec §5)."""
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    l = await ST.lire(cid)
    if l is None or l.get("illisible"):
        return
    attente = {n: b for n, b in _etats(l["messages"]).items()
               if b.get("genre") == "devis" and b.get("etat") == "acceptee" and (b.get("arguments") or {}).get("job_id")}
    if not attente:
        return
    async with _VERROU:
        l = await ST.lire(cid)                           # relu sous le verrou : deux GET n'écrivent qu'un fait
        if l is None or l.get("illisible"):
            return
        faits = {(b.get("arguments") or {}).get("job_id") for m in l["messages"] if m.get("role") == "fait"
                 for b in m.get("blocs") or [] if isinstance(b, dict) and b.get("etat") == "terminee"}
        cartes = _cartes(l["messages"])
        neufs = []
        async with async_session_factory() as s:
            for n, b in sorted(_etats(l["messages"]).items()):
                jid = (b.get("arguments") or {}).get("job_id")
                if b.get("genre") != "devis" or b.get("etat") != "acceptee" or not jid or jid in faits:
                    continue
                j = await s.get(JobRecord, jid)
                if j is None or j.status not in (JobStatus.DONE.value, JobStatus.FAILED.value):
                    continue
                carte = cartes[n] if n < len(cartes) else b
                neufs.append(fmt.nouveau_message("fait", [_bloc_etat(carte, n, "terminee", {
                    "job_id": jid, "statut": j.status}, action="continuer")]))
                faits.add(jid)
        if neufs:
            await ST.ajouter(cid, neufs)


# ---- le flux SSE ------------------------------------------------------------------------------------------------------

def _sse(e: dict) -> str:
    return "data: " + json.dumps(e, ensure_ascii=False) + "\n\n"


async def _flux(agen, premier):
    """Les évènements du tour en SSE. `aclosing` : le tour est fermé (verrou rendu) dès que ce flux l'est."""
    async with contextlib.aclosing(agen):
        try:
            if premier is not None:
                yield _sse(premier)
            async for e in agen:
                yield _sse(e)
        except (GeneratorExit, asyncio.CancelledError):
            raise
        except Exception as e:  # noqa: BLE001 — en plein flux, une panne devient un évènement terminal
            yield _sse({"type": "erreur", "code": "interne", "message": str(e)[:300]})


class _ReponseSSE(StreamingResponse):
    """Ferme le flux ET le tour quoi qu'il arrive (fin, client parti, annulation) : Starlette laisse un itérateur
    suspendu quand l'envoi échoue, et le verrou de la conversation resterait pris jusqu'au ramasse-miettes."""

    def __init__(self, flux, tour_gen):
        super().__init__(flux, media_type="text/event-stream",
                         headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        self._tour = tour_gen

    async def stream_response(self, send) -> None:
        try:
            await super().stream_response(send)
        finally:
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()
                await self._tour.aclose()


def _sans_cle(lang: str) -> HTTPException:
    """503 « clé absente », la convention du dépôt (messages.json ia.cle.absente_tir : la clé et les Réglages)."""
    from app import i18n as _i18n
    from app.services import moteurs_texte as MT
    return HTTPException(503, _i18n.msg("ia.cle.absente_tir", lang, nom_cle="ANTHROPIC_API_KEY",
                                        modele=MT.modele_agent()), headers={"X-DZ-Erreur": "sans_cle"})


def _plafond_usd(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise HTTPException(400, "plafond_usd : un nombre positif est requis.")
    v = float(v)
    if not math.isfinite(v) or v <= 0:
        raise HTTPException(400, "plafond_usd : un nombre positif est requis.")
    return v


# ---- les routes -------------------------------------------------------------------------------------------------------

@router.post("/")
async def creer(request: Request):
    _local(request)
    corps = await _json(request)
    eid = corps.get("espace_id")
    eid = _espace_valide(eid) if eid not in (None, "") else None
    titre = corps.get("titre")
    with _traduire():
        l = await ST.creer(str(corps.get("role") or ""), eid, str(titre)[:200] if isinstance(titre, str) else "")
    return await ST.lire(l["id"])


@router.post("/importer")
async def importer(request: Request):
    _local(request)
    corps = await _json(request)
    conv = corps.get("conversation")
    if not isinstance(conv, dict):
        raise HTTPException(400, "conversation : objet attendu.")
    with _traduire():
        return await ST.importer(conv)


@router.get("/{cid}")
async def lire(cid: str, request: Request):
    _local(request)
    await _conversation(cid, saine=False)
    await _noter_faits(cid)
    return await ST.lire(cid)


@router.post("/{cid}/devis")
async def devis(cid: str, request: Request):
    _local(request)
    corps = await _json(request)
    conv = await _conversation(cid)
    return await asyncio.to_thread(AC.devis_message, conv, str(corps.get("texte") or ""), _lang(request))


@router.post("/{cid}/message")
async def message(cid: str, request: Request):
    _local(request)
    corps = await _json(request)
    texte = corps.get("texte")
    if not isinstance(texte, str) or not texte.strip():
        raise HTTPException(400, "Texte requis.")
    plafond = _plafond_usd(corps.get("plafond_usd"))
    await _conversation(cid)
    lang = _lang(request)
    if not AC.cle_presente():                            # vigilance 2 : AVANT le flux et toute écriture
        raise _sans_cle(lang)
    agen = AC.tour(cid, texte, plafond, lang)
    try:
        with _traduire():
            premier = await agen.__anext__()             # le premier tour : garde, puis modèle
    except StopAsyncIteration:
        premier = None
    except RuntimeError as e:
        await agen.aclose()
        if str(e) == "sans_cle":                         # clé retirée entre le test et le tour : rien n'est écrit
            raise _sans_cle(lang) from None
        raise
    except BaseException:
        await agen.aclose()
        raise
    if premier and premier.get("type") == "erreur" and premier.get("code") in ("dz_plafond", "occupee"):
        await agen.aclose()
        if premier["code"] == "dz_plafond":
            raise HTTPException(402, premier.get("detail"))
        raise HTTPException(409, "Conversation occupée : une réponse est déjà en cours.")
    return _ReponseSSE(_flux(agen, premier), agen)


@router.post("/{cid}/carte/{n}")
async def carte(cid: str, n: int, request: Request):
    _local(request)
    corps = await _json(request)
    decision = corps.get("decision")
    if decision not in DECISIONS:
        raise HTTPException(400, "decision : acceptee ou refusee.")
    job_id = corps.get("job_id")
    if job_id is not None and (not isinstance(job_id, str) or not _JOB.match(job_id)):
        raise HTTPException(400, "job_id illisible.")
    async with _VERROU:
        l = await _conversation(cid)
        cartes = _cartes(l["messages"])
        if n < 0 or n >= len(cartes):
            raise HTTPException(404, "Carte introuvable.")
        orig = cartes[n]
        etat = (_etats(l["messages"]).get(n) or orig).get("etat")
        if etat != "proposee":
            raise HTTPException(409, "Carte déjà décidée.")
        genre, extra = orig.get("genre"), {}
        with _traduire():
            if genre == "espace" and decision == "acceptee":
                eid = _espace_valide(corps.get("espace_id"))
                if not await ST.regler_espace(cid, eid):
                    raise HTTPException(409, "La conversation a déjà son espace : il ne change pas.")
                extra["espace_id"] = eid
            elif genre == "devis" and decision == "acceptee" and job_id:
                extra["job_id"] = job_id
            if genre == "porte" and decision == "acceptee":
                await ST.regler_porte(cid, "porte1_validee")
            await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n, decision, extra)])])
    return await ST.lire(cid)


@router.post("/{cid}/depot")
async def depot(cid: str, request: Request):
    _local(request)
    if (request.headers.get("content-type") or "").lower().startswith("multipart/form-data"):
        try:
            taille = int(request.headers.get("content-length") or 0)
        except ValueError:
            taille = 0
        if taille > MAX_DEPOT_OCTETS + 64 * 1024:
            raise HTTPException(413, "Document trop lourd (15 Mo au plus).")
        await _conversation(cid)
        form = await request.form()
        f = form.get("fichier")
        if f is None or not hasattr(f, "read"):
            raise HTTPException(400, "Fichier requis (champ « fichier »).")
        data = await f.read()
        if len(data) > MAX_DEPOT_OCTETS:
            raise HTTPException(413, "Document trop lourd (15 Mo au plus).")
        from app.services import marketing
        nom = f.filename or "document"
        try:
            texte = await asyncio.to_thread(marketing.extract_document_text, nom, data)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        except Exception:  # noqa: BLE001 — un document corrompu : un refus lisible, jamais une trace
            raise HTTPException(400, "Document illisible.") from None
    else:
        corps = await _json(request)
        await _conversation(cid)
        if isinstance(corps.get("url"), str) and corps["url"].strip():
            u = AO._url_normale(corps["url"])
            if not u:
                raise HTTPException(400, "URL http(s) attendue.")
            return {"url": u, "texte": corps["url"].strip()}
        if not isinstance(corps.get("texte"), str) or not corps["texte"].strip():
            raise HTTPException(400, "Donne un fichier, un texte ou une URL.")
        nom, texte = str(corps.get("nom") or "texte"), corps["texte"]
    with _traduire():
        garde = await AO.enregistrer_depot(cid, nom, texte)
    return {"depot": garde, "caracteres": len(texte)}
