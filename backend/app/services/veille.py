# -*- coding: utf-8 -*-
"""t352 (27/10/2026) — la veille concurrentielle d'un ESPACE de marque (spec veille & prospection §5, P1).

Où elle vit : `DATA_ROOT/espaces/<id>/veille/` —
  etat.json                    la dernière collecte (en_cours | fini | fini_partiel | erreur | interrompu, journal)
  <AAAA-MM-JJ>/perimetre.json  ce qui a été cherché
  <AAAA-MM-JJ>/brut/*.jsonl    sortie de veille_collecte (auteurs hachés)
  <AAAA-MM-JJ>/verbatims.jsonl les verbatims classés (veille_grille)
  <AAAA-MM-JJ>/rapport.json    matrice, douleurs, angles, forces, demandes, limites
  <AAAA-MM-JJ>/importe.jsonl + import.json  une veille importée d'un dossier fait hors de l'app (gardée à côté du brut)

Une collecte à la fois par espace, en tâche de fond (asyncio) ; un `en_cours` sans tâche vivante dans ce processus
(backend redémarré) se lit « interrompu » et ne bloque rien. Lecture seule sur le web, aucune dépense.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import re
import time
from pathlib import Path

from app.services import espaces, veille_collecte as VC, veille_grille as G

MAX_IMPORT = 20 * 1024 * 1024          # octets d'un verbatims.jsonl importé
MAX_JOURNAL = 50
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TACHES: dict[str, asyncio.Task] = {}
_IMPORTS: set[str] = set()             # espaces dont un import tourne (thread) : exclu d'une collecte, et inversement
_EMPREINTE = re.compile(r"^[0-9a-f]{10}$")
TEXTES = ("concurrent", "source", "url", "date", "auteur_hash", "texte", "collecte_le", "requete", "theme", "polarite",
          "chez_nous", "resume")
_COLLECTER = VC.collecter              # couture du banc


class ConflitCollecte(Exception):
    """Une collecte tourne déjà pour cet espace (la route dit 409)."""


class ImportTropGros(ValueError):
    """Le fichier importé dépasse MAX_IMPORT (la route dit 413)."""


def _verifier(eid) -> str:
    e = espaces.lire()["espaces"].get(eid) if espaces.id_valide(eid) else None
    if not e or e.get("archive"):
        raise LookupError(f"espace inconnu ou archivé : {str(eid)[:40]}")
    return eid


def _racine(eid) -> Path:
    if not espaces.id_valide(eid):
        raise ValueError(f"id d'espace invalide : {str(eid)[:40]}")
    return espaces.dossier() / eid / "veille"


def dossier(eid, date: str | None = None) -> Path:
    """Le dossier daté de la veille (aujourd'hui par défaut) ; ValueError si l'id ou la date sortent de la liste blanche."""
    date = date or dt.date.today().isoformat()
    if not isinstance(date, str) or not _DATE.match(date):
        raise ValueError(f"date invalide : {str(date)[:20]}")
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        raise ValueError(f"date invalide : {date}") from None
    return _racine(eid) / date


def _lire_json(f: Path):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ecrire_json(f: Path, doc) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    for essai in range(6):          # sous Windows, un lecteur qui tient le fichier refuse le remplacement un instant
        try:
            tmp.replace(f)
            return
        except PermissionError:
            if essai == 5:
                raise
            time.sleep(0.05 * (essai + 1))


def _lignes(f: Path) -> tuple[list[dict], int]:
    """(lignes JSON lisibles, nombre de lignes illisibles)."""
    out, ko = [], 0
    if not f.exists():
        return out, ko
    for brute in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not brute.strip():
            continue
        try:
            l = json.loads(brute, parse_constant=_sans_nan)
        except ValueError:
            ko += 1
            continue
        if isinstance(l, dict):
            out.append(l)
        else:
            ko += 1
    return out, ko


def _sans_nan(c: str):
    raise ValueError(f"constante JSON refusée : {c}")


def _propre(l: dict) -> dict | None:
    """Une ligne importée réduite au schéma, aux bons types ; None si elle n'a pas de texte. Un auteur_hash qui n'est
    pas une empreinte (un pseudo en clair) est vidé : aucun pseudo n'atteint le disque."""
    if not isinstance(l.get("texte"), str) or not l["texte"].strip():
        return None
    out = {k: l[k] for k in TEXTES if isinstance(l.get(k), str)}
    for k in ("score", "intensite"):
        v = l.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            out[k] = v
    if not _EMPREINTE.match(out.get("auteur_hash", "")):
        out["auteur_hash"] = ""
    return out


def _en_vie(eid: str) -> bool:
    t = _TACHES.get(eid)
    return t is not None and not t.done()


def etat(eid) -> dict | None:
    e = _lire_json(_racine(eid) / "etat.json")
    if not isinstance(e, dict):
        return None
    if e.get("etat") == "en_cours" and not _en_vie(eid):
        e["etat"] = "interrompu"
    e.pop("debut_ts", None)
    return e


def _dates(eid) -> list[str]:
    r = _racine(eid)
    if not r.exists():
        return []
    return sorted((p.name for p in r.iterdir() if p.is_dir() and _DATE.match(p.name)), reverse=True)


def lister(eid) -> list[dict]:
    out = []
    for d in _dates(eid):
        rap = _lire_json(dossier(eid, d) / "rapport.json")
        if isinstance(rap, dict) and rap.get("version") == 1:
            out.append({"date": d, "classement": rap.get("classement"), "gardes": (rap.get("volumes") or {}).get("gardes")})
    return out


def dernier(eid, date: str | None = None) -> dict | None:
    for d in ([date] if date else _dates(eid)):
        rap = _lire_json(dossier(eid, d) / "rapport.json")
        if isinstance(rap, dict) and rap.get("version") == 1:
            return rap
    return None


def perimetre(eid) -> dict:
    """Le dernier périmètre de l'espace, sinon le périmètre par défaut (veille n°1)."""
    for d in _dates(eid):
        p = _lire_json(dossier(eid, d) / "perimetre.json")
        if isinstance(p, dict):
            try:
                return VC.valider_perimetre(p)
            except ValueError:
                continue
    return VC.valider_perimetre(VC.PERIMETRE_DEFAUT)


def verbatims(eid, date: str | None = None, theme=None, concurrent=None, limite: int = 50) -> list[dict]:
    date = date or (_dates(eid) or [None])[0]
    if not date:
        return []
    lignes, _ = _lignes(dossier(eid, date) / "verbatims.jsonl")
    out = []
    for l in lignes:
        if l.get("polarite") not in ("force", "faiblesse", "demande"):
            continue
        if (theme and l.get("theme") != theme) or (concurrent and l.get("concurrent") != concurrent):
            continue
        out.append({k: l.get(k) for k in ("concurrent", "source", "url", "date", "texte", "theme", "polarite",
                                          "intensite", "chez_nous", "resume")})
        out[-1]["texte"] = str(out[-1]["texte"] or "")[:500]
        if len(out) >= max(1, min(int(limite), 200)):
            break
    return out


def _consolider(eid: str, date: str, limites: list[str]) -> dict:
    """Classe le brut collecté ET les verbatims importés du dossier (un même jour peut avoir les deux, aucun n'écrase
    l'autre ; doublon = lien + texte), puis écrit verbatims.jsonl + rapport.json."""
    d = dossier(eid, date)
    brut = [l for f in sorted((d / "brut").glob("*.jsonl")) for l in _lignes(f)[0]]
    importes = _lignes(d / "importe.jsonl")[0]
    vus, classes = set(), []
    for l in importes + brut:
        k = VC.cle(l)
        if k not in vus:
            vus.add(k)
            classes.append(G.classer(l))
    with (d / "verbatims.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for l in classes:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    meta = _lire_json(d / "import.json")
    if isinstance(meta, dict):
        limites = list(limites) + [f"veille importée ({meta.get('lignes')} verbatims, {meta.get('ignorees')} lignes ignorées)"]
    rap = G.rapport(classes, {"date": date, "espace_id": eid, "brut": len(brut) + len(importes), "limites": limites})
    _ecrire_json(d / "rapport.json", rap)
    return rap


async def _executer(eid: str, date: str, p: dict, e: dict) -> None:
    f = _racine(eid) / "etat.json"

    def journal(ligne: str):
        e["journal"] = (e.get("journal") or [])[-(MAX_JOURNAL - 1):] + [ligne[:200]]
        _ecrire_json(f, e)

    try:
        r = await _COLLECTER(p, dossier(eid, date) / "brut", VC._horloge() + VC.DUREE_MAX, journal)
        await asyncio.to_thread(_consolider, eid, date, r.get("limites") or [])
        e.update(etat="fini_partiel" if r.get("limites") else "fini", ajoutes=r.get("ajoutes") or {},
                 limites=r.get("limites") or [])
    except Exception as ex:  # noqa: BLE001 — l'état le dit, rien ne remonte
        e.update(etat="erreur", limites=(e.get("limites") or []) + [f"{type(ex).__name__} : {str(ex)[:200]}"])
    finally:
        e["fin"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        _ecrire_json(f, e)
        _TACHES.pop(eid, None)


async def lancer(eid, perim: dict | None = None, retenir: bool = True) -> dict:
    """Lance la collecte en tâche de fond. LookupError (espace), ValueError (périmètre), ConflitCollecte.
    `retenir=False` (un sous-ensemble demandé par l'agent) : ce périmètre n'est pas gardé comme celui de l'espace."""
    _verifier(eid)
    if _en_vie(eid) or eid in _IMPORTS:
        raise ConflitCollecte("une collecte ou un import tourne déjà pour cet espace")
    p = VC.valider_perimetre(perim) if perim else perimetre(eid)
    date = dt.date.today().isoformat()
    d = dossier(eid, date)
    _ecrire_json(d / ("perimetre.json" if retenir else "perimetre_lance.json"), p)
    e = {"etat": "en_cours", "date": date, "debut": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
         "debut_ts": time.time(), "fin": None, "journal": [], "ajoutes": {}, "limites": [],
         "concurrents": [c["id"] for c in p["concurrents"]]}
    _ecrire_json(_racine(eid) / "etat.json", e)
    _TACHES[eid] = asyncio.get_running_loop().create_task(_executer(eid, date, p, e))
    return {"date": date, "etat": "en_cours", "concurrents": e["concurrents"]}


def importer(eid, source: str) -> dict:
    """Importe le `verbatims.jsonl` d'une veille faite hors de l'app (skill veille-concurrents) : rien d'autre n'est lu.
    Champs hors schéma retirés (dont tout pseudo en clair) ; le classement manuel est gardé."""
    _verifier(eid)
    if _en_vie(eid) or eid in _IMPORTS:
        raise ConflitCollecte("une collecte ou un import tourne pour cet espace : importez quand il est fini")
    _IMPORTS.add(eid)
    try:
        return _importer(eid, source)
    finally:
        _IMPORTS.discard(eid)


def _importer(eid, source: str) -> dict:
    s = Path(str(source or "").strip().strip('"'))
    f = s / "verbatims.jsonl" if s.is_dir() else s
    if f.name != "verbatims.jsonl" or not f.is_file():
        raise ValueError("dossier sans verbatims.jsonl")
    if f.stat().st_size > MAX_IMPORT:
        raise ImportTropGros(f"fichier trop gros (plus de {MAX_IMPORT // (1024 * 1024)} Mo)")
    lignes, ko = _lignes(f)
    propres = []
    for l in lignes:
        p = _propre(l)
        if p is None:
            ko += 1
        else:
            propres.append(p)
    date = f.parent.name if _DATE.match(f.parent.name) else dt.date.today().isoformat()
    d = dossier(eid, date)
    d.mkdir(parents=True, exist_ok=True)
    avant = {n: (d / n).read_bytes() for n in ("importe.jsonl", "import.json") if (d / n).exists()}
    with (d / "importe.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for l in propres:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    meta = {"source": str(f.parent), "lignes": len(propres), "ignorees": ko,
            "le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    _ecrire_json(d / "import.json", meta)
    try:
        rap = _consolider(eid, date, [])
    except Exception as e:  # un import qui ne se consolide pas ne doit jamais empoisonner la date : retour en arrière
        for n in ("importe.jsonl", "import.json"):
            if n in avant:
                (d / n).write_bytes(avant[n])
            else:
                (d / n).unlink(missing_ok=True)
        raise ValueError(f"import illisible : {type(e).__name__} : {str(e)[:200]}") from None
    return {"date": date, "lignes": len(propres), "ignorees": ko, "rapport": rap}
