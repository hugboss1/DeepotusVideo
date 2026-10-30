# -*- coding: utf-8 -*-
"""t379 (30/10/2026, lot « Réglages : chemins & apparence », plan
docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D3) — le CÂBLAGE des
emplacements de t378 (`emplacements.py`) : ce que chaque rôle fait.

  - `sauvegarde` : une copie planifiée des données (base par instantané cohérent, bibliothèque, réglages), SANS
    secret — c'est le paquet du transfert entre machines (`transfert.exporter`, qui écarte .env, coffre et jetable).
    Une fois par jour au plus (`INTERVALLE_S`), après un échec pas avant une heure (`REESSAI_S`). Dossier :
    `<emplacement>/DeepotusVideo-Sauvegardes/DeepotusVideo-Sauvegarde-AAAA-MM-JJ-HHMMSS/` ; SFTP : la même chose en
    `.zip` (sans recompression : les médias le sont déjà), préparée dans le dossier temporaire du système. ROTATION :
    les `GARDER` plus récentes restent ; seules les sauvegardes que l'app reconnaît (préfixe, et manifeste pour un
    dossier) sont effacées, jamais un autre fichier.
  - `miroir` : chaque rendu FINI est copié dans `<emplacement>/DeepotusVideo-Rendus/<nom>-<id 8>.<ext>`. Il n'y a pas
    de point unique où un job finit (une quinzaine de pipelines) : la boucle BALAIE les jobs `done` terminés après
    le dernier passage (`miroir_depuis`) et les copie un par un, en file, hors du rendu — un rendu ne l'attend
    jamais. Au premier passage, le repère est posé à « maintenant » : l'historique n'est pas recopié.
  - `bibliotheque` : un INDEX en lecture seule des médias (images, vidéos, sons) de l'emplacement, gardé dans
    `DATA_ROOT/emplacements_index/<id>.json`, refait toutes les `INDEX_S`. Rien n'est jamais écrit là-bas ; un
    fichier se lit par la route de l'écran (confinée à l'emplacement ; SFTP : copie dans un cache jetable) et
    « Importer » le COPIE dans la Bibliothèque (source « import », origine dans la recette).

Un échec devient un job `failed` du Job Dock (provider `emplacement`, `cost_meta` = l'opération) : « Réessayer »
la rejoue (`reessayer`). Aucun emplacement avec un rôle = rien ne se passe : ni fichier d'état, ni requête, ni job.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

from loguru import logger

from app.config import DATA_ROOT, settings
from app.services import emplacements as E

INTERVALLE_S = 24 * 3600            # une sauvegarde par jour et par emplacement
REESSAI_S = 3600                    # après un échec, la boucle réessaie une heure plus tard
INDEX_S = 6 * 3600                  # l'index d'une source de bibliothèque est refait toutes les 6 h
TIC_S = 60                          # la boucle
GARDER = 7                          # rotation : les 7 sauvegardes les plus récentes
MAX_FICHIERS = 20000                # index : au plus
PROVIDER = "emplacement"            # les jobs du Job Dock nés d'un échec
DOSSIER_SAUVEGARDES = "DeepotusVideo-Sauvegardes"
DOSSIER_RENDUS = "DeepotusVideo-Rendus"
PREFIXE = "DeepotusVideo-Sauvegarde-"
_NOM_SAUVEGARDE = re.compile(r"^DeepotusVideo-Sauvegarde-\d{4}-\d{2}-\d{2}-\d{6}(-\d{1,3})?(\.zip)?$")
GENRES = {
    "image": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
    "video": {".mp4", ".mov", ".webm", ".mkv", ".m4v"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"},
}
IMPORTABLES = {"image": {".png", ".jpg", ".jpeg", ".webp"}, "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a"}}


class EchecOperation(Exception):
    """Une opération sur un emplacement a échoué : `code` (chemins.etat.*) et détail."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(E.ETATS.get(code, code) + (f" : {detail}" if detail else ""))
        self.code, self.detail = code, detail


# ── l'état (rien n'est écrit tant qu'aucun rôle n'agit) ─────────────────────────────────────────────────────────────

def _fichier_etat() -> Path:
    return DATA_ROOT / "emplacements_etat.json"


def lire_etat() -> dict:
    try:
        d = json.loads(_fichier_etat().read_text(encoding="utf-8"))
        if isinstance(d, dict):
            d.setdefault("sauvegardes", {})
            return d
    except (OSError, ValueError):
        pass
    return {"sauvegardes": {}, "miroir_depuis": None}


def _ecrire_etat(d: dict) -> None:
    f = _fichier_etat()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S")


def _date(s) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s)) if s else None
    except (TypeError, ValueError):
        return None


def _emplacement_brut(eid: str) -> dict:
    e = E._lire()["emplacements"].get(eid)
    if e is None:
        raise E.EmplacementInconnu(eid)
    return e


# ── sauvegarde ──────────────────────────────────────────────────────────────────────────────────────────────────────

def nom_sauvegarde(quand: float | None = None) -> str:
    """À la seconde : « Sauvegarder maintenant » juste après la boucle ne heurte pas un nom pris."""
    return PREFIXE + time.strftime("%Y-%m-%d-%H%M%S", time.localtime(quand if quand is not None else time.time()))


def a_sauvegarder(maintenant: datetime | None = None) -> list[str]:
    """Les emplacements « sauvegarde » dont la copie est due : jamais faite, ou faite il y a plus d'un jour ; après un
    échec, pas avant une heure."""
    n = maintenant or datetime.now()
    etat = lire_etat()["sauvegardes"]
    dus = []
    for v in E.avec_role("sauvegarde"):
        s = etat.get(v["id"]) or {}
        derniere, essai = _date(s.get("derniere")), _date(s.get("essai"))
        if derniere and (n - derniere).total_seconds() < INTERVALLE_S:
            continue
        if essai and not s.get("ok") and (n - essai).total_seconds() < REESSAI_S:
            continue
        dus.append(v["id"])
    return dus


def _tourner_dossier(dossier: Path) -> list[str]:
    """Garde les GARDER sauvegardes les plus récentes ; n'efface que les dossiers nommés et munis d'un manifeste."""
    from app.services import transfert
    siennes = sorted((p for p in dossier.iterdir() if p.is_dir() and _NOM_SAUVEGARDE.match(p.name)
                      and (p / transfert.MANIFESTE).is_file()), key=lambda p: p.name, reverse=True)
    retirees = []
    for p in siennes[GARDER:]:
        shutil.rmtree(p)
        retirees.append(p.name)
    return retirees


def _nettoyer_paquet(p: Path) -> None:
    """Un export interrompu ne laisse pas un paquet à moitié écrit (il n'a pas de manifeste : la rotation l'ignorerait)."""
    from app.services import transfert
    if p.is_dir() and not (p / transfert.MANIFESTE).is_file():
        shutil.rmtree(p, ignore_errors=True)


def _sauvegarder_dossier(e: dict, quand: float | None) -> dict:
    from app.services import transfert
    racine = Path(e["chemin"])
    if not racine.is_dir():
        raise EchecOperation("introuvable")
    dest = racine / DOSSIER_SAUVEGARDES
    dest.mkdir(exist_ok=True)
    nom, n = nom_sauvegarde(quand), 2
    while (dest / nom).exists():                        # deux sauvegardes dans la même seconde
        nom, n = f"{nom_sauvegarde(quand)}-{n}", n + 1
    try:
        man = transfert.exporter(dest, quand=quand)
    except Exception as ex:  # noqa: BLE001 — place insuffisante, base illisible, disque plein : un échec dit, au Dock
        _nettoyer_paquet(dest / transfert.nom_paquet(quand))
        raise EchecOperation("echec", str(ex)[:200])
    (dest / transfert.nom_paquet(quand)).rename(dest / nom)
    return {"nom": nom, "fichiers": man.get("fichiers"), "octets": man.get("octets"), "retirees": _tourner_dossier(dest)}


def _sauvegarder_sftp(eid: str, e: dict, quand: float | None) -> dict:
    from app.services import transfert
    d = f'{e["dossier_distant"].rstrip("/")}/{DOSSIER_SAUVEGARDES}'
    nom = nom_sauvegarde(quand) + ".zip"
    with tempfile.TemporaryDirectory(prefix="dzsauvegarde_") as td:
        try:
            man = transfert.exporter(td, quand=quand)
        except Exception as ex:  # noqa: BLE001 — le dossier temporaire part avec le « with »
            raise EchecOperation("echec", str(ex)[:200])
        paquet = Path(td) / transfert.nom_paquet(quand)
        archive = Path(td) / nom
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
            for f in sorted(paquet.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(paquet).as_posix())
        shutil.rmtree(paquet)
        ok, sortie = E.lancer_sftp(eid, e, [f'-mkdir "{d}"', f'cd "{d}"', f'put "{archive.as_posix()}" "{nom}"', "ls -1"],
                                   delai=max(E.DELAI_S, 3600))
    if not ok:
        raise EchecOperation(E._echec_sftp(sortie)["code"], E._echec_sftp(sortie)["detail"])
    siennes = sorted({PurePosixPath(l.strip()).name for l in sortie.splitlines()
                      if _NOM_SAUVEGARDE.match(PurePosixPath(l.strip()).name or "")}, reverse=True)
    vieilles = [n for n in siennes if n.endswith(".zip")][GARDER:]
    if vieilles:
        E.lancer_sftp(eid, e, [f'cd "{d}"'] + [f'-rm "{n}"' for n in vieilles])
    return {"nom": nom, "fichiers": man.get("fichiers"), "octets": man.get("octets"), "retirees": vieilles}


def sauvegarder(eid: str, *, quand: float | None = None) -> dict:
    """Une sauvegarde maintenant vers cet emplacement ; l'état est mis à jour. EchecOperation sinon."""
    e = _emplacement_brut(eid)
    etat = lire_etat()
    s = etat["sauvegardes"].setdefault(eid, {})
    s["essai"] = _iso(datetime.now())
    try:
        if e.get("type") == "sftp":
            r = _sauvegarder_sftp(eid, e, quand)
        else:
            r = _sauvegarder_dossier(e, quand)
    except EchecOperation as ex:
        etat = lire_etat()
        etat["sauvegardes"].setdefault(eid, {}).update({"essai": s["essai"], "ok": False, "code": ex.code})
        _ecrire_etat(etat)
        raise
    except FileNotFoundError:
        etat = lire_etat()
        etat["sauvegardes"].setdefault(eid, {}).update({"essai": s["essai"], "ok": False, "code": "client_absent"})
        _ecrire_etat(etat)
        raise EchecOperation("client_absent")
    etat = lire_etat()
    etat["sauvegardes"][eid] = {"essai": s["essai"], "derniere": s["essai"], "ok": True, "nom": r["nom"],
                                "octets": r.get("octets")}
    _ecrire_etat(etat)
    logger.info(f"sauvegarde {r['nom']} → {eid} ({r.get('fichiers')} fichiers, {len(r['retirees'])} retirée(s))")
    return r


# ── miroir des rendus ───────────────────────────────────────────────────────────────────────────────────────────────

def nom_miroir(fichier: Path, jid: str) -> str:
    return f"{fichier.stem}-{str(jid)[:8]}{fichier.suffix}"


def mirer(eid: str, fichier: Path, jid: str) -> dict:
    """Copie UN rendu fini vers cet emplacement (déjà là, même taille : rien à faire)."""
    e = _emplacement_brut(eid)
    fichier = Path(fichier)
    if not fichier.is_file():
        raise EchecOperation("echec", f"rendu introuvable : {fichier.name}")
    nom = nom_miroir(fichier, jid)
    if e.get("type") == "sftp":
        d = f'{e["dossier_distant"].rstrip("/")}/{DOSSIER_RENDUS}'
        try:
            ok, sortie = E.lancer_sftp(eid, e, [f'-mkdir "{d}"', f'put "{fichier.as_posix()}" "{d}/{nom}"'],
                                       delai=max(E.DELAI_S, 1800))
        except FileNotFoundError:
            raise EchecOperation("client_absent")
        if not ok:
            r = E._echec_sftp(sortie)
            raise EchecOperation(r["code"], r["detail"])
        return {"nom": nom, "copie": True}
    racine = Path(e["chemin"])
    if not racine.is_dir():
        raise EchecOperation("introuvable")
    dest = racine / DOSSIER_RENDUS
    try:
        dest.mkdir(exist_ok=True)
        cible = dest / nom
        if cible.is_file() and cible.stat().st_size == fichier.stat().st_size:
            return {"nom": nom, "copie": False}
        part = dest / (nom + ".part")
        shutil.copyfile(fichier, part)
        part.replace(cible)
    except PermissionError:
        raise EchecOperation("acces_refuse")
    except OSError as ex:
        raise EchecOperation("injoignable", ex.strerror or ex.__class__.__name__)
    return {"nom": nom, "copie": True}


def _sortie_du_job(j) -> Path | None:
    for c in (getattr(j, "final_video_path", None), getattr(j, "video_path", None)):
        if c and Path(c).is_file():
            return Path(c)
    return None


async def balayer_miroir() -> list[dict]:
    """Copie les rendus finis depuis le dernier passage vers chaque emplacement « miroir ». Rend ce qui a été fait."""
    cibles = [v["id"] for v in E.avec_role("miroir")]
    etat = lire_etat()
    if not cibles:
        if etat.get("miroir_depuis") and _fichier_etat().exists():
            etat["miroir_depuis"] = None                # le jour où un miroir revient, il part de ce jour-là
            _ecrire_etat(etat)
        return []
    depuis = _date(etat.get("miroir_depuis"))
    if depuis is None:
        etat["miroir_depuis"] = datetime.utcnow().isoformat()   # completed_at : UTC (datetime.utcnow des pipelines)
        _ecrire_etat(etat)
        return []
    from sqlalchemy import select
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    async with async_session_factory() as s:
        jobs = (await s.execute(select(JobRecord).where(
            JobRecord.status == JobStatus.DONE.value, JobRecord.completed_at > depuis,
            (JobRecord.provider.is_(None)) | (JobRecord.provider != PROVIDER)).order_by(JobRecord.completed_at))).scalars().all()
    faits = []
    for j in jobs:
        f = _sortie_du_job(j)
        if f is not None:
            for eid in cibles:
                try:
                    r = await asyncio.to_thread(mirer, eid, f, j.id)
                    faits.append({"job": j.id, "emplacement": eid, **r})
                except EchecOperation as ex:
                    await noter_echec({"operation": "miroir", "emplacement": eid, "job": j.id, "fichier": str(f)},
                                      ex, titre=f.name)
                    faits.append({"job": j.id, "emplacement": eid, "erreur": ex.code})
        etat = lire_etat()
        etat["miroir_depuis"] = j.completed_at.isoformat()  # à la microseconde : le même job ne repasse pas
        _ecrire_etat(etat)
    return faits


# ── source de bibliothèque (lecture seule) ──────────────────────────────────────────────────────────────────────────

def _genre(nom: str) -> str | None:
    ext = os.path.splitext(nom)[1].lower()
    return next((g for g, exts in GENRES.items() if ext in exts), None)


def _dossier_index() -> Path:
    return DATA_ROOT / "emplacements_index"


def _cle_index(eid: str) -> Path:
    E.nom_secret(eid)                                   # valide l'identifiant (aucun chemin)
    return _dossier_index() / f"{eid}.json"


_LS_LONG = re.compile(r"^([-dl])\S*\s+\d+\s+\S+\s+\S+\s+(\d+)\s+\w{3}\s+\d+\s+[\d:]+\s+(.+)$")


def indexer(eid: str) -> dict:
    """Relève les médias d'un emplacement « bibliothèque », SANS rien y écrire. Dossier : récursif ; SFTP : le dossier
    distant seul (sftp.exe ne liste pas récursivement)."""
    e = _emplacement_brut(eid)
    fichiers = []
    if e.get("type") == "sftp":
        try:
            ok, sortie = E.lancer_sftp(eid, e, [f'ls -ln "{e["dossier_distant"]}"'])
        except FileNotFoundError:
            raise EchecOperation("client_absent")
        if not ok:
            r = E._echec_sftp(sortie)
            raise EchecOperation(r["code"], r["detail"])
        for l in sortie.splitlines():
            m = _LS_LONG.match(l.strip())
            if m and m.group(1) == "-":
                nom = PurePosixPath(m.group(3)).name
                if nom and not nom.startswith(".") and _genre(nom):
                    fichiers.append({"chemin": nom, "octets": int(m.group(2)), "genre": _genre(nom)})
    else:
        racine = Path(e["chemin"])
        if not racine.is_dir():
            raise EchecOperation("introuvable")
        for dp, dns, fns in os.walk(racine):
            dns[:] = sorted(d for d in dns if not d.startswith(".") and d not in (DOSSIER_SAUVEGARDES,))
            for fn in sorted(fns):
                if fn.startswith(".") or not _genre(fn):
                    continue
                p = Path(dp) / fn
                try:
                    st = p.stat()
                except OSError:
                    continue
                fichiers.append({"chemin": p.relative_to(racine).as_posix(), "octets": st.st_size,
                                 "mtime": int(st.st_mtime), "genre": _genre(fn)})
                if len(fichiers) >= MAX_FICHIERS:
                    break
            if len(fichiers) >= MAX_FICHIERS:
                break
    idx = {"emplacement": eid, "quand": _iso(datetime.now()), "fichiers": fichiers[:MAX_FICHIERS],
           "tronque": len(fichiers) >= MAX_FICHIERS}
    f = _cle_index(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return idx


def _marquer_index_en_echec(eid: str, code: str) -> None:
    """L'index précédent est gardé tel quel (ses fichiers restent lisibles), daté du passage en échec."""
    idx = lire_index(eid)
    idx.update({"quand": _iso(datetime.now()), "erreur": code})
    f = _cle_index(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")


def lire_index(eid: str) -> dict:
    try:
        return json.loads(_cle_index(eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"emplacement": eid, "quand": None, "fichiers": [], "tronque": False}


def a_indexer(maintenant: datetime | None = None) -> list[str]:
    n = maintenant or datetime.now()
    dus = []
    for v in E.avec_role("bibliotheque"):
        q = _date(lire_index(v["id"]).get("quand"))
        if q is None or (n - q).total_seconds() >= INDEX_S:
            dus.append(v["id"])
    return dus


def fichier_local(eid: str, chemin: str) -> Path:
    """Le chemin LOCAL d'un fichier indexé : confiné à l'emplacement (aucun « .. », aucun chemin absolu) et présent
    dans l'index ; SFTP : rapatrié une fois dans un cache jetable (exclu des sauvegardes)."""
    e = _emplacement_brut(eid)
    if "bibliotheque" not in (e.get("roles") or []):
        raise ValueError("emplacement : pas une source de bibliothèque")
    rel = PurePosixPath(str(chemin or "").replace("\\", "/"))
    if not str(rel) or rel.is_absolute() or ".." in rel.parts or ":" in str(rel) \
            or str(rel) not in {x["chemin"] for x in lire_index(eid)["fichiers"]}:
        raise ValueError("fichier : hors de l'index de cet emplacement")
    if e.get("type") != "sftp":
        racine = Path(e["chemin"]).resolve()
        p = (racine / Path(*rel.parts)).resolve()
        if racine not in p.parents or not p.is_file():
            raise ValueError("fichier : hors de l'index de cet emplacement")
        return p
    cache = settings.outputs_path / "_cache" / "emplacements" / eid
    cache.mkdir(parents=True, exist_ok=True)
    local = cache / (hashlib.sha1(str(rel).encode("utf-8")).hexdigest()[:16] + rel.suffix.lower())
    if not local.is_file():
        try:
            ok, sortie = E.lancer_sftp(eid, e, [f'get "{e["dossier_distant"].rstrip("/")}/{rel}" "{local.as_posix()}"'])
        except FileNotFoundError:
            raise EchecOperation("client_absent")
        if not ok or not local.is_file():
            r = E._echec_sftp(sortie)
            raise EchecOperation(r["code"], r["detail"])
    return local


async def importer(eid: str, chemin: str) -> dict:
    """COPIE un fichier de la source dans la Bibliothèque (images ou sons) ; la source n'est pas touchée."""
    p = await asyncio.to_thread(fichier_local, eid, chemin)
    nom_src = PurePosixPath(str(chemin).replace("\\", "/")).name
    genre = next((g for g, exts in IMPORTABLES.items() if p.suffix.lower() in exts), None)
    if genre is None:
        raise ValueError("import : images et sons seulement")
    dossier = settings.images_path if genre == "image" else settings.images_path.parent / "audio"
    dossier.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(nom_src).stem)[:60] or "fichier"
    nom = f"empl_{base}_{uuid.uuid4().hex[:6]}{p.suffix.lower()}"
    await asyncio.to_thread(shutil.copyfile, p, dossier / nom)
    from app.services import library_index as LI
    await LI.noter([nom], "import", kind=genre, recette={"emplacement": eid, "chemin": str(chemin)})
    return {"filename": nom, "genre": genre}


# ── Job Dock : un échec = un job « failed » que « Réessayer » rejoue ────────────────────────────────────────────────

def _dit(cle: str, lang: str | None = None) -> str:
    """Un texte du Job Dock dans la langue de l'interface (UI_LANG) : la boucle n'a pas de requête dont lire la
    langue, et un job ne se retraduit pas (son `error` n'est pas un gabarit L10). Clés emplacements.* de messages.json."""
    from app.i18n import langue_ui, msg
    return msg(cle, lang or langue_ui())


def message_echec(ex: "EchecOperation", lang: str | None = None) -> str:
    return _dit(f"emplacements.etat.{ex.code}", lang) + (f" : {ex.detail}" if ex.detail else "")


def _meme_operation(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in ("operation", "emplacement", "job"))


async def noter_echec(meta: dict, ex: EchecOperation, titre: str = "") -> str:
    """Un job « failed » au Job Dock. La MÊME opération déjà en échec (un NAS éteint toute la nuit) ne fait pas un job
    de plus à chaque passage : son job est mis à jour (erreur, heure)."""
    from sqlalchemy import select
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    nom = (E._lire()["emplacements"].get(meta.get("emplacement")) or {}).get("nom") or meta.get("emplacement")
    t = f"{_dit('emplacements.operation.' + meta['operation'])} → {nom}" + (f" : {titre}" if titre else "")
    corps = json.dumps({**meta, "code": ex.code}, ensure_ascii=False)
    async with async_session_factory() as s:
        ouverts = (await s.execute(select(JobRecord).where(JobRecord.provider == PROVIDER,
                                                           JobRecord.status == JobStatus.FAILED.value))).scalars().all()
        j = next((x for x in ouverts if _meme_operation(json.loads(x.cost_meta or "{}"), meta)), None)
        if j is None:
            j = JobRecord(id=str(uuid.uuid4()), status=JobStatus.FAILED.value, progress=0, image_filename="",
                          provider=PROVIDER, current_step=meta["operation"])
            s.add(j)
        j.title, j.error, j.cost_meta, j.completed_at = t[:200], message_echec(ex), corps, datetime.utcnow()
        jid = j.id
        await s.commit()
    logger.warning(f"emplacement : {t} — {ex}")
    return jid


async def _clore(meta: dict) -> int:
    """La même opération vient de réussir d'elle-même (la boucle) : ses jobs en échec passent « done »."""
    from sqlalchemy import select
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    n = 0
    async with async_session_factory() as s:
        for j in (await s.execute(select(JobRecord).where(JobRecord.provider == PROVIDER,
                                                          JobRecord.status == JobStatus.FAILED.value))).scalars():
            if _meme_operation(json.loads(j.cost_meta or "{}"), meta):
                j.status, j.error, j.progress, j.completed_at = JobStatus.DONE.value, None, 100, datetime.utcnow()
                n += 1
        await s.commit()
    return n


async def _jouer(meta: dict) -> dict:
    op, eid = meta.get("operation"), meta.get("emplacement")
    if op == "sauvegarde":
        return await asyncio.to_thread(sauvegarder, eid)
    if op == "miroir":
        return await asyncio.to_thread(mirer, eid, Path(meta["fichier"]), meta["job"])
    if op == "index":
        return {"fichiers": len((await asyncio.to_thread(indexer, eid))["fichiers"])}
    raise ValueError("opération inconnue")


async def reessayer(jid: str) -> dict:
    """« Réessayer » du Job Dock : rejoue l'opération du job en échec ; le job passe done ou reste failed."""
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    async with async_session_factory() as s:
        j = await s.get(JobRecord, jid)
        if j is None or j.provider != PROVIDER:
            raise LookupError(jid)
        if j.status != JobStatus.FAILED.value:
            raise ValueError("job : pas en échec")
        meta = json.loads(j.cost_meta or "{}")
        j.status, j.error, j.progress = JobStatus.QUEUED.value, None, 0
        await s.commit()
    try:
        r = await _jouer(meta)
        statut, erreur = JobStatus.DONE.value, None
    except EchecOperation as ex:
        r, statut, erreur = {"erreur": ex.code}, JobStatus.FAILED.value, message_echec(ex)
    except E.EmplacementInconnu:
        r, statut, erreur = {"erreur": "inconnu"}, JobStatus.FAILED.value, _dit("emplacements.etat.retire")
    async with async_session_factory() as s:
        j = await s.get(JobRecord, jid)
        j.status, j.error, j.completed_at = statut, erreur, datetime.utcnow()
        j.progress = 100 if statut == JobStatus.DONE.value else 0
        await s.commit()
    return {"job_id": jid, "status": statut, **({"resultat": r} if statut == JobStatus.DONE.value else {"error": erreur})}


# ── la boucle (lancée par le lifespan de main.py) ───────────────────────────────────────────────────────────────────

async def tic() -> dict:
    """Un passage : sauvegardes dues, rendus finis à copier, sources à réindexer. Sans emplacement : rien."""
    fait = {"sauvegardes": [], "miroir": [], "index": []}
    if not E._fichier().exists():
        return fait
    for eid in a_sauvegarder():
        try:
            fait["sauvegardes"].append((await asyncio.to_thread(sauvegarder, eid))["nom"])
            await _clore({"operation": "sauvegarde", "emplacement": eid})
        except EchecOperation as ex:
            await noter_echec({"operation": "sauvegarde", "emplacement": eid}, ex)
    fait["miroir"] = await balayer_miroir()
    for eid in a_indexer():
        try:
            fait["index"].append({eid: len((await asyncio.to_thread(indexer, eid))["fichiers"])})
            await _clore({"operation": "index", "emplacement": eid})
        except EchecOperation as ex:
            _marquer_index_en_echec(eid, ex.code)       # pas un nouvel essai à chaque minute : au prochain délai
            await noter_echec({"operation": "index", "emplacement": eid}, ex)
    return fait


async def boucle(premier: float = 45, intervalle: float = TIC_S) -> None:
    await asyncio.sleep(premier)
    while True:
        try:
            await tic()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — une panne d'un passage n'arrête pas la boucle
            logger.warning(f"emplacements : passage ignoré : {type(e).__name__} : {e}")
        await asyncio.sleep(intervalle)
