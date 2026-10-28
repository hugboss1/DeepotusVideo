# -*- coding: utf-8 -*-
"""Les routes de l'agent Campagnes (t285a, T7, 23/10/2026, spec §5, §6, §7) — /api/agent/campagnes.

Boucle locale OU appareil appairé (t286, 24/10 : `_local_ou_appareil`, jeton d'appareil sinon 401) ; les écritures
sont ouvertes au réseau local une par une (`main._ECRITURES_OUVERTES`, en gabarits). Depuis un appareil, une
conversation créée a l'origine « telephone », et le message `utilisateur` (comme le `fait` d'une décision de carte)
porte l'origine « telephone » et l'id de l'appareil du JETON (jamais un champ du corps). Le tour s'exécute sur le PC,
avec ses clés et son plafond.
- `POST /api/agent/campagnes/` (AVEC la barre finale) {role, espace_id?, titre?} : crée la conversation (espace
  nommé : existant et non archivé, sinon 400). Sans la barre, un appareil reçoit 403 de la garde des écritures avant
  la redirection de FastAPI (seul le gabarit exact est ouvert) ;
- `GET /paquet?espace_id=&avec=telephone&langue=fr|en` (L4.1) : en plus, le catalogue allégé, les poids, le système par
  rôle, les cinq outils du téléphone, le modèle et les constantes ; `ETag` = `version` (tout le contenu), `If-None-Match`
  égal → 304 sans corps. Avec `avec=telephone` et sans `espace_id`, c'est l'espace ACTIF du PC (non archivé) qui est servi (le téléphone
  ne le connaît pas, spec §6.1). Sans `avec`, la réponse reste celle ci-dessous ;
- `GET /paquet?espace_id=` : le paquet agent du compagnon, {version, fichiers} — docs/agent/campagnes/* (texte) et,
  avec un espace nommé (sinon 400), `persona.json` sans `templates` ni `voice_ids` ; `boites.json` (les boîtes à outils marquées mobile, t305, 25/10/2026) ; sans `avec`, jamais l'espace actif d'office.
  `version` = 16 hex du sha256 des fichiers (noms triés, fichiers cachés exclus) : elle change dès qu'un fichier
  change ;
- `GET /{cid}` : la conversation ; ajoute d'abord un message `fait` par carte `devis` acceptée dont le job est fini
  (DONE ou FAILED) — un seul par job, quel que soit le nombre de GET ;
- `POST /{cid}/devis` {texte} : le plafond en dollars du prochain message (rendu même sans clé) ;
- `POST /{cid}/message` {texte, plafond_usd} : la réponse en SSE (une ligne `data:` JSON par évènement). Sans clé
  Anthropic : 503 AVANT toute écriture. Le PREMIER évènement est tiré avant d'ouvrir le flux : un refus 402 de la
  garde (`dz_plafond`) au premier tour devient un vrai HTTP 402 (le dialogue des plafonds le rejoue avec
  `X-DZ-Plafond: confirme`) et « occupée » un 409 ; plus loin dans la boucle, un 402 reste un évènement `erreur`
  (les octets sont partis). `tour()` est mené sous `contextlib.aclosing` et la réponse ferme le flux même si le client
  coupe : le verrou de la conversation est toujours rendu ;
- `POST /{cid}/carte/{n}` {decision, job_id?, espace_id?, fichier?} : `n` = rang (0, 1, …) de la carte parmi les
  cartes des messages `agent`. La décision s'écrit D'ABORD comme un message NEUF (`fait`, bloc carte,
  `arguments.carte = n`), l'état (espace, porte) ensuite ; l'original n'est jamais modifié ; une carte déjà décidée =
  409 (sauf reprise d'un état non appliqué). Porte : seulement la DERNIÈRE porte, état `porte1_proposee`. Devis image
  ou voix (rendu immédiat) : `fichier` requis (nom simple, présent au magasin), le fait `terminee` s'écrit aussitôt ;
  devis vidéo : `job_id`, le fait vient au GET ;
- `POST /{cid}/depot` : multipart `fichier` (texte extrait par marketing.extract_document_text), JSON {texte} ou JSON
  {url} → gardé pour `lire_document` (l'URL est gardée comme TEXTE, rien n'est téléchargé ici : la lecture reste à
  `lire_document`, sous ses gardes) ;
- `POST /importer` {conversation} : `agent_store.importer` (idempotent ; l'id est un UUID canonique en minuscules,
  sinon 400 — il devient un dossier). Depuis un appareil : la conversation est
  « telephone » (ou sans origine) et chaque message porte l'origine « telephone » et l'appareil du JETON, sinon 400.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import math
import re

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.services import agent_campagnes as AC, agent_format as fmt, agent_outils as AO, agent_store as ST, espaces

router = APIRouter()

MAX_CORPS = 8_000_000                  # JSON (une conversation importée tient très en dessous)
MAX_DEPOT_OCTETS = 15 * 1024 * 1024    # comme l'import d'un document de stratégie (/marketing/plan/import)
DECISIONS = ("acceptee", "refusee")
_JOB = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FICHIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
_VERROU = asyncio.Lock()               # décisions de cartes et blocs `fait` : relire puis écrire, un seul à la fois


# ---- gardes et lecture ------------------------------------------------------------------------------------------------
# Les gabarits d'erreur (scripts/i18n_l10_traductions.json) : un LITTÉRAL par HTTPException, traduit à la sortie.

def _introuvable() -> HTTPException:
    return HTTPException(404, "Conversation introuvable.")


def _illisible() -> HTTPException:
    return HTTPException(409, "Conversation illisible : son fichier est mis de côté, rien n'a été écrit.")


async def _local_ou_appareil(request: Request) -> dict | None:
    """t286 : la boucle locale → None ; sinon l'appareil du jeton (`routes._appareil_requis`, 401 sans jeton valide)."""
    from app.api import routes
    try:
        routes._require_localhost(request)
        return None
    except HTTPException:
        return await routes._appareil_requis(request)


def _trace(appareil: dict | None) -> dict:
    """Origine et appareil d'un message écrit à la demande de la requête : ceux du JETON, rien depuis le PC."""
    return {"origine": "telephone", "appareil": appareil["id"]} if appareil else {}


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
    """Un espace NOMMÉ : existant et non archivé (vigilance 5) ; sinon 400, jamais de repli sur l'actif. Le même
    validateur que les routes de génération (`routes._espace_du_corps`) ; ici, l'espace est obligatoire."""
    from app.api.routes import _espace_du_corps
    v = _espace_du_corps(eid)
    if v is None:
        raise HTTPException(400, "Espace requis.")
    return v


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
            if not isinstance(b, dict):
                continue
            n = (b.get("arguments") or {}).get("carte") if isinstance(b.get("arguments"), dict) else None
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
    appareil = await _local_ou_appareil(request)
    corps = await _json(request)
    from app.api.routes import _espace_du_corps
    eid = _espace_du_corps(corps.get("espace_id"))
    titre = corps.get("titre")
    with _traduire():
        l = await ST.creer(str(corps.get("role") or ""), eid, str(titre)[:200] if isinstance(titre, str) else "",
                           origine="telephone" if appareil else "pc")
    return await ST.lire(l["id"])


def _import_de_l_appareil(conv: dict, appareil: dict) -> None:
    """t286 (relecture) : un import venu d'un appareil ne choisit ni l'origine ni l'appareil. La conversation est
    « telephone » (ou sans origine) et CHAQUE message porte `origine == "telephone"` et l'id de l'appareil du JETON ;
    sinon 400, rien d'écrit. On refuse, on ne réécrit jamais : les empreintes restent celles du téléphone."""
    if conv.get("origine") not in (None, "telephone"):
        raise HTTPException(400, "Import depuis un appareil : la conversation doit avoir l'origine « telephone ».")
    messages = conv.get("messages") or []
    if not isinstance(messages, list) or any(
            not isinstance(m, dict) or m.get("origine") != "telephone" or m.get("appareil") != appareil["id"]
            for m in messages):
        raise HTTPException(400, "Import depuis un appareil : chaque message doit porter l'origine « telephone » et "
                                 "l'appareil de ce jeton.")


@router.post("/importer")
async def importer(request: Request):
    appareil = await _local_ou_appareil(request)
    corps = await _json(request)
    conv = corps.get("conversation")
    if not isinstance(conv, dict):
        raise HTTPException(400, "conversation : objet attendu.")
    if appareil:
        _import_de_l_appareil(conv, appareil)
    # t285a (revue finale) : l'espace importé passe par le validateur des routes (inconnu ou archivé → 400, rien
    # d'écrit) ; absent → None, l'agent le demandera par une carte espace
    from app.api.routes import _espace_du_corps
    conv = dict(conv, espace_id=_espace_du_corps(conv.get("espace_id")))
    with _traduire():
        return await ST.importer(conv)


def _paquet(espace_id: str | None) -> dict:
    """Les fichiers de AC.DOCS (le dossier que lit déjà le système de l'agent), fins de ligne normalisées, plus la
    persona filtrée de l'espace NOMMÉ ; la version suit leur sérialisation déterministe. Les fichiers cachés (« . » :
    brouillons d'éditeur, .DS_Store) ne sont ni servis ni comptés."""
    fichiers = {f.name: f.read_text(encoding="utf-8").replace("\r\n", "\n")
                for f in sorted(AC.DOCS.iterdir(), key=lambda f: f.name)
                if f.is_file() and not f.name.startswith(".")}
    if espace_id:
        fichiers["persona.json"] = json.dumps(AC.persona_modele(_espace_valide(espace_id)), ensure_ascii=False,
                                              indent=2, sort_keys=True)
    # t305 (25/10/2026) : les boîtes à outils (par fonctionnalité) voyagent avec le paquet, pour que le compagnon sache quels
    # outils lui sont ouverts ; ajoutées avant le tri pour que la version reste déterministe
    from app.services import agent_boites
    fichiers["boites.json"] = json.dumps(agent_boites.paquet_mobile(), ensure_ascii=False, indent=2, sort_keys=True)
    fichiers = dict(sorted(fichiers.items()))
    brut = json.dumps(fichiers, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"version": hashlib.sha256(brut).hexdigest()[:16], "fichiers": fichiers}


# L4.1 T1 (25/10/2026) : les cinq outils que le téléphone sait exécuter (ses schémas viennent de la table d'agent_outils)
OUTILS_TELEPHONE = ("chercher_app", "lire_espace", "lire_document", "proposer_porte", "deviser_generation")
ROLES_TELEPHONE = ("orienteur", "campagnes", "demonstrateur")
_CHAMPS_FICHE = ("ecran", "type", "libelle", "infobulle", "role", "synonymes", "guide")


def _fiche_telephone(x: dict) -> dict:
    """Une fiche du catalogue sans ce qui ne sert qu'au PC (localisateur, sources, cadre, icône, empreinte, état)."""
    return {"id": x["id"], **{k: x.get(k) for k in _CHAMPS_FICHE}}


def _paquet_telephone(espace_id: str | None, langue: str) -> dict:
    """Le paquet de base plus tout ce qu'il faut au téléphone pour mener la même boucle hors ligne. `version` couvre
    TOUT le contenu rendu (sauf `genere_a`, qui change à chaque appel) : elle sert d'ETag."""
    from datetime import datetime, timezone
    from app.services import agent_aide, moteurs_texte
    p = _paquet(espace_id)
    ref = {d["name"]: d for d in AO.definitions()}
    p.update(
        catalogue=[_fiche_telephone(x) for x in agent_aide.catalogue().values()],
        mots_vides=sorted(agent_aide.MOTS_VIDES),
        poids={k: w for k, w in agent_aide.POIDS},
        systeme={r: AC.systeme_pour(r, espace_id, langue) for r in ROLES_TELEPHONE},
        outils=[ref[n] for n in OUTILS_TELEPHONE],
        modele=moteurs_texte.modele_agent(),
        constantes={"MAX_TOURS": AC.MAX_TOURS, "SORTIE_MAX": AC.SORTIE_MAX, "CARS_PAR_JETON": AC.CARS_PAR_JETON,
                    "SURCOUT_OUTILS": AC.SURCOUT_OUTILS})
    p["espace_id"] = espace_id or None
    p.pop("version")
    brut = json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"version": hashlib.sha256(brut).hexdigest()[:16], **p,
            "genere_a": datetime.now(timezone.utc).isoformat()}


def _etags(entete: str | None) -> set:
    """Les versions d'un If-None-Match : entre guillemets ou non, faible (`W/`) ou non, liste séparée par des virgules."""
    return {re.sub(r'^W/', "", x.strip()).strip('"') for x in (entete or "").split(",") if x.strip()}


def _paquet_telephone_pc(espace_id: str | None, lg: str) -> dict:
    """Le paquet du téléphone, lu HORS de la boucle d'évènements : sans `espace_id`, l'espace actif du PC (non archivé),
    dont la lecture est un fichier (spec §6.1)."""
    if not espace_id:
        a = espaces.actif()
        espace_id = None if a.get("archive") else a.get("id")
    return _paquet_telephone(espace_id, lg)


def _temoins_espaces() -> list:
    """Les espaces démonstration non archivés : (id, nom, prospect d'origine)."""
    out = []
    for eid, e in (_es_lire()["espaces"] or {}).items():
        if isinstance(e, dict) and e.get("type") == "demonstration" and not e.get("archive"):
            out.append((eid, e.get("nom") or eid, str((e.get("origine") or {}).get("prospect") or "") or None))
    return sorted(out, key=lambda x: x[1])


def _es_lire():
    from app.services import espaces as _es
    return _es.lire()


async def _conversation_temoin(eid: str) -> str | None:
    from sqlalchemy import select
    from app.services.storage import AgentConversation, async_session_factory
    async with async_session_factory() as s:
        r = (await s.execute(select(AgentConversation).where(AgentConversation.espace_id == eid,
                                                             AgentConversation.role == "campagnes")
                             .order_by(AgentConversation.cree.asc()))).scalars().first()
    return r.id if r else None


_VERROU_TEMOIN = asyncio.Lock()


@router.get("/temoins")
async def temoins(request: Request):
    """t359 : les espaces démonstration (rendez-vous d'un prospect) et leur conversation « campagne témoin »."""
    await _local_ou_appareil(request)
    return {"temoins": [{"espace_id": eid, "nom": nom, "prospect": pr, "conversation_id": await _conversation_temoin(eid)}
                        for eid, nom, pr in await asyncio.to_thread(_temoins_espaces)]}


@router.post("/temoin")
async def temoin(request: Request):
    """t359 : ouvre (ou rouvre) la conversation « campagnes » d'un espace démonstration : la campagne témoin, qui ne
    publie jamais. 409 pour un espace qui n'est pas une démonstration."""
    appareil = await _local_ou_appareil(request)
    corps = await _json(request)
    eid = _espace_valide(corps.get("espace_id"))
    from app.services import espaces as _es
    if not _es.est_demonstration(eid):
        raise HTTPException(409, "Une campagne témoin se prépare dans un espace démonstration.")
    async with _VERROU_TEMOIN:              # relecture t359 (1) : deux ouvertures simultanées → UNE conversation
        cid = await _conversation_temoin(eid)
        if cid is None:
            nom = _es.lire()["espaces"][eid].get("nom") or eid
            with _traduire():
                l = await ST.creer("campagnes", eid, f"Campagne témoin · {nom}"[:200], origine="telephone" if appareil else "pc")
            cid = l["id"]
    return await _conversation(cid)


@router.get("/paquet")
async def paquet(request: Request, espace_id: str | None = None, avec: str | None = None, langue: str | None = None):
    await _local_ou_appareil(request)
    if avec != "telephone":
        return await asyncio.to_thread(_paquet, espace_id)
    lg = langue if langue in ("fr", "en") else _lang(request)
    p = await asyncio.to_thread(_paquet_telephone_pc, espace_id, lg)
    if p["version"] in _etags(request.headers.get("if-none-match")):
        return Response(status_code=304, headers={"ETag": p["version"]})
    return JSONResponse(p, headers={"ETag": p["version"]})


@router.get("/{cid}")
async def lire(cid: str, request: Request):
    await _local_ou_appareil(request)
    await _conversation(cid, saine=False)
    await _noter_faits(cid)
    return await ST.lire(cid)


@router.post("/{cid}/devis")
async def devis(cid: str, request: Request):
    await _local_ou_appareil(request)
    corps = await _json(request)
    conv = await _conversation(cid)
    return await asyncio.to_thread(AC.devis_message, conv, str(corps.get("texte") or ""), _lang(request))


@router.post("/{cid}/message")
async def message(cid: str, request: Request):
    appareil = await _local_ou_appareil(request)
    corps = await _json(request)
    texte = corps.get("texte")
    if not isinstance(texte, str) or not texte.strip():
        raise HTTPException(400, "Texte requis.")
    plafond = _plafond_usd(corps.get("plafond_usd"))
    await _conversation(cid)
    lang = _lang(request)
    if not AC.cle_presente():                            # vigilance 2 : AVANT le flux et toute écriture
        raise _sans_cle(lang)
    agen = AC.tour(cid, texte, plafond, lang, **_trace(appareil))
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


def _fichier_rendu(genre: str, fichier) -> str:
    """Le rendu IMMÉDIAT d'un devis image ou voix accepté : un nom simple (aucun séparateur, aucun « .. »), présent
    dans le magasin de ce genre (images ou audio) ; sinon 400."""
    from app.config import settings
    if not isinstance(fichier, str) or not _FICHIER.match(fichier) or ".." in fichier:
        raise HTTPException(400, "fichier : un nom de rendu simple est requis.")
    dossier = settings.images_path if genre == "image" else settings.images_path.parent / "audio"
    if not (dossier / fichier).is_file():
        raise HTTPException(400, "fichier : rendu introuvable.")
    return fichier


def _derniere_porte(cartes: list) -> int:
    return max((i for i, b in enumerate(cartes) if b.get("genre") == "porte"), default=-1)


@router.post("/{cid}/carte/{n}")
async def carte(cid: str, n: int, request: Request):
    """La décision s'écrit D'ABORD (message `fait` neuf), puis l'état (espace, porte) est appliqué. Si ce second pas
    échoue, la même décision rejouée ne rend pas 409 : elle réapplique l'état seulement (reprise), sans second
    message. Une fois l'état appliqué, toute nouvelle réponse à la carte rend 409."""
    appareil = await _local_ou_appareil(request)
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
        orig, derniere = cartes[n], _etats(l["messages"]).get(n)
        genre, acceptee = orig.get("genre"), decision == "acceptee"
        etat = (derniere or orig).get("etat")
        if etat != "proposee":
            # reprise : la décision est écrite mais l'état n'a pas suivi (panne entre les deux pas)
            d_args = (derniere or {}).get("arguments") or {}
            reprise = acceptee and etat == "acceptee" and (
                (genre == "espace" and l.get("espace_id") is None and corps.get("espace_id") in (None, d_args.get("espace_id")))
                or (genre == "porte" and l.get("etat_porte") == "porte1_proposee"))
            if not reprise:
                raise HTTPException(409, "Carte déjà décidée.")
            with _traduire():
                if genre == "espace":
                    await ST.regler_espace(cid, _espace_valide(d_args.get("espace_id")))
                else:
                    await ST.regler_porte(cid, "porte1_validee")
            return await ST.lire(cid)
        extra, faits, recherche, collecte = {}, [], None, None
        if acceptee and genre == "espace":
            eid = _espace_valide(corps.get("espace_id"))
            if l.get("espace_id") is not None:
                raise HTTPException(409, "La conversation a déjà son espace : il ne change pas.")
            extra["espace_id"] = eid
        elif acceptee and genre == "porte":
            if l.get("etat_porte") != "porte1_proposee" or n != _derniere_porte(cartes):
                raise HTTPException(409, "Cette porte n'est plus la porte en cours : rien n'est validé.")
        elif acceptee and genre == "devis":
            g = (orig.get("arguments") or {}).get("genre")
            if g in ("image", "voix"):                   # rendu immédiat : le fait s'écrit tout de suite
                extra["fichier"] = _fichier_rendu(g, corps.get("fichier"))
                faits.append(fmt.nouveau_message("fait", [_bloc_etat(orig, n, "terminee", {
                    "fichier": extra["fichier"], "statut": "done"}, action="continuer")], **_trace(appareil)))
            elif job_id:                                  # vidéo : le fait viendra au GET, job fini
                extra["job_id"] = job_id
        elif acceptee and genre == "recherche":
            # t354 tâche 5d : plafond AVANT tout appel (402 : rien), sans clé 503 ; relecture I5 : la décision s'écrit
            # sous le verrou, la recherche part APRÈS (jamais le verrou global pendant un appel payant, jamais rejouée)
            recherche = await _reserver_recherche(cid, l, orig)
            extra["statut"] = "en_cours"
        elif acceptee and genre == "collecte":
            # t364 : même schéma que la recherche — clé (503), devis recalculé et plafonds (402) sous le verrou, rien
            # d'écrit en cas de refus ; le run part APRÈS, hors du verrou, et n'est jamais rejoué
            collecte = await _reserver_collecte(cid, l, orig)
            extra["statut"] = "en_cours"
        elif genre == "sequence":
            # t355 : la porte 2 d'une séquence — EXCEPTION à « la décision d'abord » : le geste d'abord (refus = 409, rien d'écrit) ; acceptée = validée par
            # l'utilisateur, refusée = annulée ; un geste déjà fait (reprise après panne) passe
            _decider_sequence(l.get("espace_id"), (orig.get("arguments") or {}).get("sid"), acceptee)
        with _traduire():
            await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n, decision, extra)],
                                                       **_trace(appareil))] + faits)
            if acceptee and genre == "espace":
                if not await ST.regler_espace(cid, extra["espace_id"]):
                    raise HTTPException(409, "La conversation a déjà son espace : il ne change pas.")
            elif acceptee and genre == "porte":
                await ST.regler_porte(cid, "porte1_validee")
    if acceptee and genre == "recherche":
        await _executer_recherche(cid, n, orig, recherche, appareil)
    if acceptee and genre == "collecte":
        await _executer_collecte(cid, n, orig, collecte, appareil)
    return await ST.lire(cid)


def _decider_sequence(eid, sid, acceptee: bool) -> None:
    from app.services import prospects_sequences as S
    try:
        s = [x for x in S.lister(eid) if x["id"] == sid] if eid else []
        if not s:
            raise HTTPException(404, "Séquence introuvable.")
        if acceptee and s[0]["statut"] == "proposee":
            S.valider(eid, sid, "utilisateur")
        elif not acceptee and s[0]["statut"] in S.EN_COURS:
            S.annuler(eid, sid, "utilisateur")
        elif acceptee and s[0]["statut"] not in ("validee", "planifiee"):
            raise HTTPException(409, f"Séquence {s[0]['statut']} : rien à valider.")
    except S.RefusSequence as e:
        raise HTTPException(e.statut, e.message) from None


async def _reserver_recherche(cid: str, l: dict, orig: dict) -> dict:
    """Sous le verrou : la clé (503), puis le plafond (402) — un refus n'écrit rien. Rend ce que la recherche emporte."""
    from app.services import plafonds, recherche_web as RW
    a = orig.get("arguments") or {}
    f = a.get("fournisseur") if a.get("fournisseur") in RW.FOURNISSEURS else RW.fournisseur_actif()
    q, n = str(a.get("requete") or "")[:300], a.get("max") if isinstance(a.get("max"), int) else 5
    if not RW.configure(f):
        raise HTTPException(503, f"aucune clé pour la recherche {f} : posez-la dans l'onglet Prospects")
    garde = await plafonds.verifier(RW.op(f, n), "campagnes", ref=cid, espace_id=l.get("espace_id"))
    return {"f": f, "q": q, "n": n, "lignes": (garde or {}).get("lignes") or []}


async def _executer_recherche(cid: str, n_carte: int, orig: dict, r0: dict, appareil) -> None:
    """Hors du verrou, la décision déjà écrite : UNE recherche, le coût réel noté (même en échec), les sites publics
    déposés, un fait « terminee » (résultats, ou l'échec) ; un échec rend 502 — la carte n'est plus rejouable."""
    from app.services import plafonds, recherche_web as RW
    try:
        r = await RW.rechercher(r0["q"], r0["n"], r0["f"])
    except Exception as e:  # noqa: BLE001 — toute panne : coût réconcilié, échec dit, jamais une trace
        await plafonds.noter_reel_lignes(r0["lignes"], float(getattr(e, "cout_usd", 0.0) or 0.0))
        msg = str(e) if isinstance(e, (RW.SansCle, RW.RechercheEchouee, ValueError)) else f"recherche en échec ({type(e).__name__})"
        with _traduire():
            await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n_carte, "terminee", {
                "fournisseur": r0["f"], "statut": "failed", "erreur": msg[:300]})], **_trace(appareil))])
        raise HTTPException(502, msg) from None
    await plafonds.noter_reel_lignes(r0["lignes"], float(r["cout_usd"]))
    extra = await _deposer_resultats(cid, r)
    with _traduire():
        await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n_carte, "terminee", dict(
            extra, fournisseur=r0["f"], cout_usd=r["cout_usd"], statut="done"))], **_trace(appareil))])


async def _reserver_collecte(cid: str, l: dict, orig: dict) -> dict:
    """t364, sous le verrou : l'acteur (422), la clé (503), le devis RECALCULÉ (un prix a pu changer) sous le plafond de
    l'usage puis sous les plafonds de l'application (402). Un refus n'écrit rien. Rend ce que le run emporte."""
    from app.services import apify as AP, plafonds
    a = orig.get("arguments") or {}
    cle = a.get("acteur")
    n = a.get("max") if isinstance(a.get("max"), int) and not isinstance(a.get("max"), bool) else 0
    entree = a.get("entree") if isinstance(a.get("entree"), dict) else {}
    try:
        if cle not in AP.ACTEURS or n < 1:
            raise AP.ApifyRefus("collecte illisible : acteur hors liste blanche ou nombre absent", 422)
        AP.filtrer(cle, entree, n)
        if not AP.configure():
            raise HTTPException(503, "aucune clé Apify : posez-la dans Réglages › Clés d'API")
        d = await AP.devis(cle, n, entree)
        plafond = AP.PLAFONDS[AP.ACTEURS[cle]["usage"]]
        if d > plafond:
            raise AP.ApifyRefus(f"devis {d:.2f} $ au-delà du plafond {plafond:.2f} $ : réduire le nombre de résultats", 402)
    except AP.ApifyRefus as e:
        raise HTTPException(e.code, str(e)) from None
    garde = await plafonds.verifier({"kind": "apify", "acteur": AP.ACTEURS[cle]["acteur"], "usd": d}, "campagnes",
                                    ref=cid, espace_id=l.get("espace_id"))
    return {"cle": cle, "entree": entree, "n": n, "lignes": (garde or {}).get("lignes") or [],
            "espace_id": l.get("espace_id")}


async def _executer_collecte(cid: str, n_carte: int, orig: dict, c0: dict, appareil) -> None:
    """t364, hors du verrou, la décision déjà écrite : UN run, le coût réel noté (même en échec), les résultats déposés
    en JSON (lus par `lire_document`, encadrés), un fait « terminee » ; un échec rend 502 — la carte n'est plus rejouable."""
    from app.services import agent_outils as AO, apify as AP, plafonds
    try:
        r = await AP.lancer(c0["cle"], c0["entree"], c0["n"])
    except Exception as e:  # noqa: BLE001 — toute panne : coût réconcilié, échec dit, jamais une trace
        await plafonds.noter_reel_lignes(c0["lignes"], float(getattr(e, "cout_usd", 0.0) or 0.0))
        msg = str(e) if isinstance(e, (AP.SansCle, AP.ApifyRefus, AP.ApifyEchec, ValueError)) else f"collecte en échec ({type(e).__name__})"
        with _traduire():
            await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n_carte, "terminee", {
                "statut": "failed", "erreur": msg[:300]})], **_trace(appareil))])
        raise HTTPException(502, msg) from None
    await plafonds.noter_reel_lignes(c0["lignes"], float(r["cout_usd"]))
    from app.services import apify_suite as SU
    a = orig.get("arguments") or {}
    args = dict(a, espace_id=c0.get("espace_id"))
    try:                                                # t365-t368 : ce que devient la collecte, selon son but
        suite = await SU.traiter(a.get("but"), cid, args, r["items"])
    except Exception as e:  # noqa: BLE001 — la collecte est payée : le fait l'écrit quand même, la suite dit son échec
        suite = {"suite_erreur": f"{type(e).__name__} : {str(e)[:200]}"}
    try:                                                # relecture C1 : jamais un pseudo en clair dans le dépôt
        a_deposer = SU.depot(a.get("but"), args, r["items"], suite)
    except Exception:  # noqa: BLE001
        a_deposer = []
    depot = await AO.enregistrer_depot(cid, f"apify-{c0['cle']}", json.dumps(a_deposer, ensure_ascii=False))
    with _traduire():
        await ST.ajouter(cid, [fmt.nouveau_message("fait", [_bloc_etat(orig, n_carte, "terminee", dict(suite, **{
            "resultats": len(r["items"]), "cout_usd": r["cout_usd"], "partiel": bool(r["partiel"]), "statut": "done",
            "depot": depot[:-4] if depot.endswith(".txt") else depot}))], **_trace(appareil))])


async def _deposer_resultats(cid: str, r: dict) -> dict:
    from app.services import agent_outils as AO
    gardes = []
    for x in r["resultats"]:
        u = AO._url_normale(x.get("url") or "")
        if not u:
            continue
        try:
            AO._url_sure(u)
        except Exception:  # noqa: BLE001 — hôte local ou interdit : jamais déposé
            continue
        await AO.enregistrer_depot(cid, "url", u)
        gardes.append({"titre": x.get("titre") or "", "url": u})
    return {"resultats": gardes}


async def _formulaire_borne(request: Request):
    """Le multipart lu en FLUX et borné comme `_json` : 413 dès que le corps dépasse MAX_DEPOT_OCTETS + 64 Kio, même
    sans Content-Length (chunked) — rien n'est mis de côté au-delà. Un multipart illisible : 400, jamais 500."""
    from starlette.formparsers import MultiPartException, MultiPartParser

    async def borne():
        total = 0
        async for morceau in request.stream():
            total += len(morceau)
            if total > MAX_DEPOT_OCTETS + 64 * 1024:
                raise HTTPException(413, "Document trop lourd (15 Mo au plus).")
            yield morceau
    try:
        return await MultiPartParser(request.headers, borne()).parse()
    except (MultiPartException, ValueError):        # ValueError : MultipartParseError de python-multipart
        raise HTTPException(400, "Document illisible.") from None


@router.post("/{cid}/depot")
async def depot(cid: str, request: Request):
    await _local_ou_appareil(request)
    if (request.headers.get("content-type") or "").lower().startswith("multipart/form-data"):
        try:
            taille = int(request.headers.get("content-length") or 0)
        except ValueError:
            taille = 0
        if taille > MAX_DEPOT_OCTETS + 64 * 1024:
            raise HTTPException(413, "Document trop lourd (15 Mo au plus).")
        await _conversation(cid)
        form = await _formulaire_borne(request)
        try:
            f = form.get("fichier")
            if f is None or not hasattr(f, "read"):
                raise HTTPException(400, "Fichier requis (champ « fichier »).")
            data = await f.read()
        finally:
            await form.close()
        if len(data) > MAX_DEPOT_OCTETS:
            raise HTTPException(413, "Document trop lourd (15 Mo au plus).")
        from app.services import marketing
        nom = f.filename or "document"
        try:
            if nom.lower().endswith(".csv"):         # t354 (relecture I1) : un export de liste d'attente ou de formulaire
                try:
                    texte = data.decode("utf-8-sig")
                except UnicodeDecodeError:          # l'export Excel français : cp1252
                    texte = data.decode("cp1252", errors="replace")
            else:
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
            with _traduire():                            # gardée comme TEXTE : rien n'est téléchargé ici
                garde = await AO.enregistrer_depot(cid, "url", u)
            return {"depot": garde, "url": u, "texte": corps["url"].strip(), "caracteres": len(u)}
        if not isinstance(corps.get("texte"), str) or not corps["texte"].strip():
            raise HTTPException(400, "Donne un fichier, un texte ou une URL.")
        nom, texte = str(corps.get("nom") or "texte"), corps["texte"]
    with _traduire():
        garde = await AO.enregistrer_depot(cid, nom, texte)
    return {"depot": garde, "caracteres": len(texte)}
