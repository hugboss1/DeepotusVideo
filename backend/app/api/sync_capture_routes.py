# -*- coding: utf-8 -*-
"""t323 (Compagnon M6, 26/11/2026) — la capture de l'app faite SUR LE TÉLÉPHONE, déposée au PC (écriture n° 5 de la spec
mère §10), et le skin de l'espace lu par le téléphone (lecture n° 6). Jeton d'appareil exigé ; l'appareil est celui du
JETON, jamais un champ du corps. Les trois écritures sont ouvertes au Wi-Fi par `main._ECRITURES_OUVERTES`.

- `POST /api/sync/capture` {empreinte (64 hex), taille, sha256, mime video/mp4, duree_ms, cadre, options} -> {id, recus} :
  une session `captures/<id>/` en mode `telephone`, IDEMPOTENTE par (appareil, empreinte) : la même empreinte rend la
  même session et le nombre de morceaux déjà reçus (reprise après une coupure) ; une session déjà reçue rend
  `terminee: true` (rien à renvoyer) ; une session abandonnée rend 409.
- `POST /api/sync/capture/{id}/morceau/{n}` corps brut video/mp4 (16 Mo au plus) : `capture.ajouter_morceau`, piste
  `scene`, dans l'ordre. Un morceau déjà reçu (n < attendu) rend {recu, deja: true} sans rien écrire.
- `POST /api/sync/capture/{id}/terminer` {clics (dzclics v1), montage, recette, titre} : la taille et le sha256 du
  fichier ENTIER sont revérifiés contre la déclaration (409 sinon, la session reste ouverte), puis la même clôture que le
  PC (`capture_routes.terminer` : réservation, copie dans la Bibliothèque, job `capture`, index `capture` avec la recette
  `origine: telephone` et l'appareil du jeton). Le plan de montage simple est gardé à côté (`montage_telephone.json`).
- `GET /api/sync/skin?espace=<id>` -> {skin (skins.actif : normalisé v1) | null (sans habillage), contexte}.
Aucun réseau, aucune dépense."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import threading
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from app.services import capture as C

router = APIRouter()

_EMP = re.compile(r"^[0-9a-f]{64}$")
MAX_VIDEO = C.MAX_PISTE
MAX_CORPS = 8 * 1024 * 1024
FICHIER_SESSIONS = "telephone.json"
_VERROU = threading.Lock()


async def _appareil(request: Request) -> dict:
    from app.api.routes import _appareil_requis
    return await _appareil_requis(request)


async def _json(request: Request, maximum: int = MAX_CORPS) -> dict:
    corps = await request.body()
    if len(corps) > maximum:
        raise HTTPException(413, "Corps de requête trop lourd.")
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


def _registre() -> dict:
    try:
        d = json.loads((C.racine() / FICHIER_SESSIONS).read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ecrire_registre(d: dict) -> None:
    f = C.racine() / FICHIER_SESSIONS
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    tmp.replace(f)


def _session_du_telephone(appareil: dict, cid: str) -> dict:
    """La déclaration de la session `cid`, si elle appartient à l'appareil du jeton (404 sinon : rien à deviner)."""
    if not C.ID.match(cid or ""):
        raise HTTPException(404, "Capture inconnue.")
    for v in _registre().values():
        if isinstance(v, dict) and v.get("id") == cid and v.get("appareil") == str(appareil["id"]):
            return v
    raise HTTPException(404, "Capture inconnue.")


def _entier(v, lo: int, hi: int):
    return v if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi else None


def _ouvrir(appareil: dict, d: dict) -> dict:
    emp = str(d.get("empreinte") or "").lower()
    sha = str(d.get("sha256") or "").lower()
    taille = _entier(d.get("taille"), 1, MAX_VIDEO)
    if not _EMP.match(emp) or not _EMP.match(sha) or taille is None:
        raise HTTPException(400, "Déclaration invalide : empreinte, sha256 (64 hex) et taille exigés.")
    if str(d.get("mime") or "").split(";")[0].strip().lower() != "video/mp4":
        raise HTTPException(415, "Seule une vidéo MP4 est acceptée du téléphone.")
    cle = f"{appareil['id']}:{emp}"
    with _VERROU:
        reg = _registre()
        v = reg.get(cle)
        if isinstance(v, dict):
            s = C._lire_session(v["id"])
            if s["etat"] == "terminee":                          # déjà reçue : le téléphone n'a rien à renvoyer
                return {"id": v["id"], "recus": int((s["pistes"].get("scene") or {}).get("morceaux") or 0), "terminee": True}
            if s["etat"] != "en_cours":
                raise HTTPException(409, "Cette capture est close au PC sans avoir été reçue (abandonnée).")
            return {"id": v["id"], "recus": int((s["pistes"].get("scene") or {}).get("morceaux") or 0)}
        o = d.get("options") if isinstance(d.get("options"), dict) else {}
        s = C.creer({"mode": "telephone", "voix": o.get("voix") is True, "camera": o.get("camera") is True, "clics": True})
        reg[cle] = {"id": s["id"], "appareil": str(appareil["id"]), "empreinte": emp, "sha256": sha, "taille": taille,
                    "duree_ms": _entier(d.get("duree_ms"), 0, 24 * 3600 * 1000) or 0,
                    "cadre": {k: _entier((d.get("cadre") or {}).get(k) if isinstance(d.get("cadre"), dict) else None, 0, 16384) or 0
                              for k in ("largeur", "hauteur")},
                    "cree": datetime.now().isoformat(timespec="seconds")}
        _ecrire_registre(reg)
    logger.info(f"capture {s['id']} : ouverte par le téléphone {str(appareil['id'])[:8]} ({taille} o annoncés)")
    return {"id": s["id"], "recus": 0}


@router.post("/sync/capture")
async def ouvrir(request: Request):
    appareil = await _appareil(request)
    d = await _json(request, 64 * 1024)
    try:
        return await asyncio.to_thread(_ouvrir, appareil, d)
    except C.RefusCapture as e:
        raise HTTPException(e.statut, str(e)) from None


@router.post("/sync/capture/{cid}/morceau/{n}")
async def morceau(cid: str, n: int, request: Request):
    appareil = await _appareil(request)
    v = await asyncio.to_thread(_session_du_telephone, appareil, cid)
    if n < 0:
        raise HTTPException(400, "Numéro de morceau invalide.")
    s = await asyncio.to_thread(C._lire_session, cid)
    attendu = int((s["pistes"].get("scene") or {}).get("morceaux") or 0)
    if n < attendu:
        return {"recu": n, "deja": True}                         # reprise : ce morceau est déjà là
    octets = bytearray()
    async for bout in request.stream():
        octets += bout
        if len(octets) > C.MAX_MORCEAU:
            raise HTTPException(413, "Morceau trop lourd : 16 Mo au plus.")
    deja = int((s["pistes"].get("scene") or {}).get("octets") or 0)
    if deja + len(octets) > v["taille"]:
        raise HTTPException(409, "Plus d'octets que la taille annoncée.")
    try:
        r = await asyncio.to_thread(C.ajouter_morceau, cid, "scene", n, bytes(octets), "video/mp4")
    except C.RefusCapture as e:
        raise HTTPException(e.statut, str(e)) from None
    return {"recu": r["recu"], "octets": r["octets"]}


def _verifier_fichier(cid: str, v: dict) -> None:
    f = C.chemin_piste(cid, "scene")
    if f is None or f.stat().st_size != v["taille"]:
        raise HTTPException(409, "Fichier incomplet : la taille reçue n'est pas celle annoncée.")
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for bout in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bout)
    if h.hexdigest() != v["sha256"]:
        raise HTTPException(409, "Empreinte du fichier différente de celle annoncée : renvoyez la capture.")


@router.post("/sync/capture/{cid}/terminer")
async def terminer(cid: str, request: Request):
    appareil = await _appareil(request)
    v = await asyncio.to_thread(_session_du_telephone, appareil, cid)
    d = await _json(request)
    await asyncio.to_thread(_verifier_fichier, cid, v)
    from app.api import routes as R
    from app.config import settings
    from app.services import library_index as LI
    try:
        await asyncio.to_thread(C.reserver, cid)
    except C.RefusCapture as e:
        raise HTTPException(e.statut, str(e)) from None
    try:
        dest = await asyncio.to_thread(C.copier_scene, cid, settings.outputs_path / "captures")
    except BaseException as e:
        await asyncio.to_thread(C.liberer, cid)
        if isinstance(e, C.RefusCapture):
            raise HTTPException(e.statut, str(e)) from None
        raise
    try:
        r = await asyncio.to_thread(C.clore, cid, d.get("clics"), v["duree_ms"], v["cadre"], ())
    except C.RefusCapture as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(e.statut, str(e)) from None
    montage = d.get("montage") if isinstance(d.get("montage"), dict) else None
    if montage is not None:
        brut = json.dumps(montage, ensure_ascii=False)
        if len(brut) <= 256 * 1024:
            (C._dossier(cid) / "montage_telephone.json").write_text(brut, "utf-8")
    titre = C._texte(d.get("titre"), 120) or f"Capture du téléphone {datetime.now().strftime('%d/%m %H:%M')}"
    job_id = await R._sfx_video_job(dest, titre, provider="capture", etape="Capture")
    evts = r["clics"]["evenements"]
    clics = [e for e in evts if e["type"] == "clic"]
    await LI.noter([dest.name], "capture", kind="video", job_id=job_id,
                   recette={"capture_id": cid, "mode": "telephone", "origine": "telephone",
                            "appareil": str(appareil["id"])[:8], "empreinte": v["empreinte"], "sha256": v["sha256"],
                            "pistes": sorted(r["session"]["pistes"]), "clics": len(clics),
                            "montage": bool(montage)})
    logger.info(f"capture {cid} : close (téléphone), {len(evts)} événements, {v['taille']} o")
    return {"id": cid, "job_id": job_id, "fichier": dest.name,
            "clics": {"evenements": len(evts), "clics": len(clics), "reconnus": sum(1 for e in clics if e.get("fiche"))}}


@router.get("/sync/skin")
async def skin(request: Request, espace: str = ""):
    await _appareil(request)
    from app.services import espaces, skins
    eid = espace or espaces.espace_courant()
    if eid not in espaces.lire()["espaces"]:
        raise HTTPException(404, "Espace inconnu.")
    try:
        s = await asyncio.to_thread(skins.actif, eid)
    except Exception as e:  # noqa: BLE001 — un skin illisible : le téléphone prend le livré par défaut
        logger.warning(f"sync/skin : skin illisible ({type(e).__name__})")
        raise HTTPException(409, "Skin de l'espace illisible.") from None
    return {"skin": s, "contexte": await asyncio.to_thread(skins.contexte, eid)}
