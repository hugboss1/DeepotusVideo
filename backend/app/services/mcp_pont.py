# -*- coding: utf-8 -*-
"""t345 (29/10/2026, D1 du lot Scenario) — le PONT entre le serveur MCP local (app/mcp_stdio.py, lancé par Claude Code)
et l'application. Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne D1.

Pourquoi un pont dans le backend plutôt que les outils appelés dans le processus MCP : le backend est la SEULE source
de vérité des plafonds, du coffre, de l'espace actif et de la base ; le processus stdio n'importe rien de l'app (pas de
clé chargée, pas de second écrivain sur la base) et ne parle qu'à deux routes : « /api/mcp/outils » et « /api/mcp/appel ».

Les droits :
  - les outils = ceux de l'agent « mcp » dans agent_boites (LECTURE + le devis `deviser_generation`), plus trois outils
    du pont : `lister_espaces` (lecture), `lancer` et `suivre_lancement` ;
  - une DÉPENSE n'est jamais faite par le pont. `deviser_generation` rend un JETON (la demande est gardée ici, avec sa
    route et son corps figés) ; `lancer(jeton)` la passe « en attente » ; c'est l'UTILISATEUR qui clique « Lancer » sur
    la carte de l'app (frontend/shared/dz-mcp.js), et c'est l'ÉCRAN qui appelle alors la route de génération — la même
    que la carte de devis de l'agent Campagnes — où `plafonds.verifier` s'applique comme pour tout clic ;
  - les routes qui font avancer une demande (commencer, refuser, résultat) exigent un en-tête Origin local, que seul le
    navigateur de l'app envoie ; le processus MCP n'en envoie pas et ne les appelle jamais (liste blanche du client) ;
  - le serveur est DÉSACTIVÉ par défaut (Réglages › Serveur MCP) ; tout est local (garde des écritures + `_require_localhost`
    sur chaque route, jamais ouvert au Wi-Fi du compagnon) ;
  - chaque réponse passe par `recette_export.nettoyer` (aucune clé, aucun jeton d'API, aucun chemin local) ; le journal
    garde l'outil, les NOMS d'arguments, le résumé nettoyé et la durée — jamais les valeurs.
Données : DATA_ROOT/mcp/{reglages.json, demandes.json, journal.jsonl}.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.services import agent_outils as ao

AGENT = "mcp"
DUREE_DEVIS_S = 30 * 60          # un devis non lancé expire après 30 min
DUREE_ATTENTE_S = 24 * 3600      # une demande en attente expire après 24 h
MAX_JOURNAL = 500
MAX_DEMANDES = 200
ROUTES = {"image": "/api/images/generate", "video": "/api/generate", "voix": "/api/audio/voiceover"}
ETATS = ("devis", "en_attente", "lancement", "lancee", "refusee", "echec", "expiree")
_VERROU = threading.Lock()
_ESPACE_PROP = {"type": "string", "description": "id de l'espace de marque (facultatif ; défaut : l'espace actif, "
                                                 "voir lister_espaces)"}
TITRES = {"lister_espaces": "Espaces de marque", "lancer": "Demander le lancement d'un devis",
          "suivre_lancement": "Suivre une demande de lancement"}


class RefusPont(Exception):
    """Un refus du pont : `cle` est une clé de app/i18n/messages.json (mcp.*), rendue dans la langue de la requête."""

    def __init__(self, cle: str, statut: int = 400, **valeurs):
        super().__init__(cle)
        self.cle, self.statut, self.valeurs = cle, statut, valeurs


# ── fichiers ──────────────────────────────────────────────────────────────────────────────────────────────────────

def dossier() -> Path:
    d = config.DATA_ROOT / "mcp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lire_json(f: Path, defaut):
    try:
        v = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut
    return v if isinstance(v, type(defaut)) else defaut


def _ecrire_json(f: Path, v) -> None:
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _maintenant() -> float:
    return time.time()


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


# ── réglages ──────────────────────────────────────────────────────────────────────────────────────────────────────

def actif() -> bool:
    return bool(_lire_json(dossier() / "reglages.json", {}).get("actif") is True)


def activer(oui: bool) -> bool:
    with _VERROU:
        _ecrire_json(dossier() / "reglages.json", {"actif": bool(oui), "modifie": _iso(_maintenant())})
    return actif()


def commande() -> dict:
    """La commande à copier : le python qui fait tourner le backend (le python embarqué de l'installation) et le
    script stdio de l'app ; l'URL n'est passée que si le port n'est pas 8765."""
    python = str(Path(sys.executable))
    script = str(Path(__file__).resolve().parents[1] / "mcp_stdio.py")
    port = int(getattr(config.settings, "PORT", 8765) or 8765)
    env = "" if port == 8765 else f" -e DEEPOTUS_URL=http://127.0.0.1:{port}"
    return {"python": python, "script": script, "port": port,
            "claude": f'claude mcp add --scope user deepotus{env} -- "{python}" "{script}"',
            "json": {"mcpServers": {"deepotus": {"command": python, "args": [script],
                                                 **({"env": {"DEEPOTUS_URL": f"http://127.0.0.1:{port}"}}
                                                    if port != 8765 else {})}}}}


# ── outils ────────────────────────────────────────────────────────────────────────────────────────────────────────

def _schema_avec_espace(schema: dict) -> dict:
    s = json.loads(json.dumps(schema))
    s.setdefault("properties", {})["espace"] = dict(_ESPACE_PROP)
    return s


_META = {
    "lister_espaces": {"nature": "lecture",
                       "description": "Les espaces de marque (id, nom, type) et l'espace actif. Les outils qui lisent "
                                      "un espace prennent l'actif par défaut, ou celui passé dans « espace ».",
                       "schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}},
    "lancer": {"nature": "demande",
               "description": "Demande le LANCEMENT d'un devis obtenu par deviser_generation (son jeton). Rien n'est "
                              "dépensé ici : une carte « Claude Code demande à lancer … pour … $ » apparaît dans "
                              "DeepotusVideo et l'UTILISATEUR l'accepte ou la refuse ; les plafonds de dépense "
                              "s'appliquent à son clic. Suis la demande avec suivre_lancement.",
               "schema": {"type": "object", "properties": {
                   "jeton": {"type": "string", "description": "le jeton rendu par deviser_generation"},
                   "pourquoi": {"type": "string", "maxLength": 300,
                                "description": "une phrase pour l'utilisateur : à quoi sert ce rendu"}},
                          "required": ["jeton"], "additionalProperties": False}},
    "suivre_lancement": {"nature": "lecture",
                         "description": "L'état d'une demande de lancement : devis, en_attente (l'utilisateur n'a "
                                        "pas encore répondu), lancement, lancee (avec le job ou le fichier), refusee, "
                                        "echec ou expiree.",
                         "schema": {"type": "object", "properties": {"jeton": {"type": "string"}},
                                    "required": ["jeton"], "additionalProperties": False}},
}


def _annotations(nom: str, nature: str) -> dict:
    lecture = nature == "lecture"
    return {"title": TITRES.get(nom) or nom.replace("_", " "), "readOnlyHint": lecture, "destructiveHint": False,
            "idempotentHint": lecture, "openWorldHint": nom in ("lancer",)}


def outils() -> list[dict]:
    """La liste exposée au client MCP : [{name, description, inputSchema, annotations, nature}]."""
    from app.services import agent_boites
    out = []
    for d in agent_boites.definitions_pour(AGENT):
        nom = d["name"]
        nature = ao.OUTILS[nom]["nature"]
        desc = d["description"]
        if nom == "deviser_generation":
            desc = ("Devis GRATUIT d'une image, d'une vidéo ou d'une voix : rend un montant et un JETON. Ne lance rien ; "
                    "pour lancer, appelle « lancer » avec le jeton — l'utilisateur confirmera dans l'app.")
            nature = "devis"
        out.append({"name": nom, "description": desc, "inputSchema": _schema_avec_espace(d["input_schema"]),
                    "annotations": _annotations(nom, nature), "nature": nature})
    for nom, m in _META.items():
        out.append({"name": nom, "description": m["description"], "inputSchema": json.loads(json.dumps(m["schema"])),
                    "annotations": _annotations(nom, m["nature"]), "nature": m["nature"]})
    return out


# ── demandes (devis → lancement) ──────────────────────────────────────────────────────────────────────────────────

def _id_valide(v) -> bool:
    try:
        return isinstance(v, str) and uuid.UUID(v).hex == v
    except ValueError:
        return False


def _demandes() -> dict:
    return _lire_json(dossier() / "demandes.json", {})


def _expirer(ds: dict, t: float) -> bool:
    change = False
    for d in ds.values():
        if d.get("etat") == "devis" and t > d.get("expire", 0):
            d["etat"], change = "expiree", True
        elif d.get("etat") == "en_attente" and t > d.get("attente_expire", 0):
            d["etat"], change = "expiree", True
    return change


def _ranger(ds: dict) -> dict:
    if len(ds) <= MAX_DEMANDES:
        return ds
    garde = sorted(ds.values(), key=lambda d: d.get("cree", 0))[-MAX_DEMANDES:]
    return {d["id"]: d for d in garde}


def _resume_corps(genre: str, corps: dict) -> str:
    if genre == "image":
        return str(corps.get("prompt") or "")[:160]
    if genre == "video":
        return f"{corps.get('image_filename')} — {str(corps.get('custom_prompt') or '')[:140]}"
    return str(corps.get("script") or "")[:160]


def _nouvelle_demande(carte: dict) -> dict:
    a = carte.get("arguments") or {}
    genre = a.get("genre")
    if genre not in ROUTES or a.get("route") != ROUTES[genre]:
        raise RefusPont("mcp.devis_invalide")
    corps = dict(a.get("corps") or {})
    corps.pop("source", None)          # pas de catégorie « campagnes » : la route compte sous sa propre catégorie
    t = _maintenant()
    d = {"id": uuid.uuid4().hex, "etat": "devis", "genre": genre, "route": ROUTES[genre], "corps": corps,
         "usd": float(a.get("usd") or 0.0), "espace_id": a.get("espace_id"), "resume": _resume_corps(genre, corps),
         "cree": t, "expire": t + DUREE_DEVIS_S, "pourquoi": "", "resultat": None}
    with _VERROU:
        ds = _demandes()
        _expirer(ds, t)
        ds[d["id"]] = d
        _ecrire_json(dossier() / "demandes.json", _ranger(ds))
    return d


def _vue(d: dict, complet: bool = False) -> dict:
    v = {"id": d["id"], "etat": d["etat"], "genre": d["genre"], "usd": d["usd"], "resume": d.get("resume") or "",
         "pourquoi": d.get("pourquoi") or "", "espace_id": d.get("espace_id"), "cree": _iso(d.get("cree") or 0),
         "resultat": d.get("resultat")}
    if complet:
        v["route"], v["corps"] = d["route"], d["corps"]
    return v


def demandes(etat: str | None = None) -> list[dict]:
    with _VERROU:
        ds = _demandes()
        if _expirer(ds, _maintenant()):
            _ecrire_json(dossier() / "demandes.json", ds)
    out = [d for d in ds.values() if not etat or d.get("etat") == etat]
    out.sort(key=lambda d: d.get("cree", 0), reverse=True)
    return [_vue(d, complet=d.get("etat") == "en_attente") for d in out]


def _transition(did: str, de: tuple, vers: str, **champs) -> dict:
    if not _id_valide(did):
        raise RefusPont("mcp.demande_inconnue", 404)
    with _VERROU:
        ds = _demandes()
        _expirer(ds, _maintenant())
        d = ds.get(did)
        if d is None:
            raise RefusPont("mcp.demande_inconnue", 404)
        if d.get("etat") not in de:
            raise RefusPont("mcp.etat_refuse", 409, etat=d.get("etat"))
        d["etat"] = vers
        d.update(champs)
        _ecrire_json(dossier() / "demandes.json", ds)
    return d


def commencer(did: str) -> dict:
    """L'utilisateur a cliqué « Lancer » : la demande passe « lancement » (une seule fois) et l'écran reçoit la route et
    le corps FIGÉS au devis (le client MCP ne peut plus les changer)."""
    d = _transition(did, ("en_attente",), "lancement", decide=_maintenant())
    return _vue(d, complet=True)


def refuser(did: str) -> dict:
    return _vue(_transition(did, ("devis", "en_attente"), "refusee", decide=_maintenant()))


def noter(did: str, ok: bool, resultat: dict | None) -> dict:
    r = {}
    for k in ("job_id", "fichier", "message"):
        v = (resultat or {}).get(k)
        if isinstance(v, str) and v:
            r[k] = v[:300]
    return _vue(_transition(did, ("lancement",), "lancee" if ok else "echec", resultat=r or None))


def _lancer(jeton: str, pourquoi: str = "") -> dict:
    if not _id_valide(jeton):
        return {"ok": False, "resume": "jeton inconnu : demande un devis avec deviser_generation d'abord",
                "donnees": None}
    try:
        d = _transition(jeton, ("devis",), "en_attente", pourquoi=str(pourquoi or "")[:300],
                        attente_expire=_maintenant() + DUREE_ATTENTE_S)
    except RefusPont as e:
        if e.cle == "mcp.demande_inconnue":
            return {"ok": False, "resume": "jeton inconnu : demande un devis avec deviser_generation d'abord",
                    "donnees": None}
        return {"ok": False, "resume": f"demande déjà « {e.valeurs.get('etat')} » : demande un nouveau devis",
                "donnees": {"etat": e.valeurs.get("etat")}}
    return {"ok": True, "resume": (f"demande envoyée à l'utilisateur ({d['genre']}, {d['usd']:.4f} $) : RIEN n'est "
                                   "dépensé tant qu'il n'a pas cliqué « Lancer » dans DeepotusVideo ; suis-la avec "
                                   "suivre_lancement"),
            "donnees": {"jeton": d["id"], "etat": d["etat"], "usd": d["usd"]}}


def _suivre(jeton: str) -> dict:
    if not _id_valide(jeton):
        return {"ok": False, "resume": "jeton inconnu", "donnees": None}
    for v in demandes():
        if v["id"] == jeton:
            return {"ok": True, "resume": f"demande {v['etat']}", "donnees": {k: v[k] for k in (
                "etat", "genre", "usd", "resultat", "cree")}}
    return {"ok": False, "resume": "jeton inconnu", "donnees": None}


def _lister_espaces() -> dict:
    from app.services import espaces
    act = espaces.espace_courant()
    out = [{"id": e["id"], "nom": e.get("nom"), "type": e.get("type"), "actif": e["id"] == act}
           for e in espaces.lister(archives=False)]
    return {"ok": True, "resume": f"{len(out)} espace(s) ; actif : {act}", "donnees": {"espaces": out, "actif": act}}


# ── journal ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _journaliser(entree: dict) -> None:
    f = dossier() / "journal.jsonl"
    with _VERROU:
        try:
            lignes = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
        except OSError:
            lignes = []
        lignes.append(json.dumps(entree, ensure_ascii=False))
        f.write_text("\n".join(lignes[-MAX_JOURNAL:]) + "\n", encoding="utf-8")


def journal(n: int = 50) -> list[dict]:
    f = dossier() / "journal.jsonl"
    try:
        lignes = f.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for l in reversed(lignes[-max(1, min(MAX_JOURNAL, int(n or 50))):]):
        try:
            out.append(json.loads(l))
        except ValueError:
            continue
    return out


# ── l'appel ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _nettoyer(v):
    from app.services import recette_export
    return recette_export.nettoyer(v)


async def appeler(nom, arguments, lang: str = "fr") -> dict:
    """{ok, resume, donnees} NETTOYÉ ; ne lève que RefusPont (serveur désactivé). Toute autre erreur revient au client
    comme un échec d'outil (isError), jamais comme une panne du protocole."""
    if not actif():
        raise RefusPont("mcp.desactive", 403)
    t0 = _maintenant()
    nom = nom if isinstance(nom, str) else ""
    args = dict(arguments) if isinstance(arguments, dict) else {}
    try:
        r = await _executer(nom, args, "en" if lang == "en" else "fr")
    except Exception as e:  # noqa: BLE001 — l'erreur revient au client, jamais au serveur
        r = {"ok": False, "resume": f"{nom} : {type(e).__name__} : {str(e)[:200]}", "donnees": None}
    r = _nettoyer({"ok": bool(r.get("ok")), "resume": str(r.get("resume") or ""), "donnees": r.get("donnees")})
    _journaliser({"quand": _iso(t0), "outil": nom[:64], "arguments": sorted(str(k)[:40] for k in args)[:20],
                  "ok": r["ok"], "resume": r["resume"][:300], "duree_ms": int((_maintenant() - t0) * 1000)})
    return r


async def _executer(nom: str, args: dict, lang: str) -> dict:
    from app.services import agent_boites, espaces
    if nom == "lister_espaces":
        return _lister_espaces()
    if nom == "lancer":
        return _lancer(args.get("jeton"), args.get("pourquoi") or "")
    if nom == "suivre_lancement":
        return _suivre(args.get("jeton"))
    if nom not in agent_boites.outils_pour(AGENT):
        return {"ok": False, "resume": f"outil inconnu ou hors des droits du serveur MCP : {nom[:60]}", "donnees": None}
    eid = args.pop("espace", None)
    if eid in (None, ""):
        eid = espaces.espace_courant()
    ctx = ao.Ctx(cid="mcp", espace_id=eid if isinstance(eid, str) else None, lang=lang, agent=AGENT)
    r = await ao.executer(nom, args, ctx)
    if nom == "deviser_generation" and r.get("ok") and r.get("carte"):
        d = _nouvelle_demande(r["carte"])
        return {"ok": True,
                "resume": (f"devis {d['genre']} : {d['usd']:.4f} $ — jeton {d['id']} valable 30 min. Rien n'est lancé : "
                           "appelle « lancer » avec ce jeton, l'utilisateur confirmera dans DeepotusVideo."),
                "donnees": {"jeton": d["id"], "genre": d["genre"], "usd": d["usd"], "expire": _iso(d["expire"]),
                            "resume": d["resume"]}}
    return {"ok": r.get("ok"), "resume": r.get("resume"), "donnees": r.get("donnees")}
