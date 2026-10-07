"""Routes du Photolab (t136, P1, 07/10/2026) : /api/photolab — le pont HTTP vers le moteur photocraft.

L'écran (P2) ne parle qu'à ces routes. Les fichiers n'entrent et ne sortent que par elles : une image de la
Bibliothèque est COPIÉE dans <données>/photolab/entrees/ avant d'être ouverte (le moteur ne lit que son dossier),
les rendus et exports sont servis depuis rendus/ et exports/. Rien de payant : le moteur est local.

Chaque réponse qui a parlé au moteur porte l'en-tête X-Photolab-Generation : la génération du processus qui a
répondu. Si elle change entre deux demandes, le moteur a été relancé et les documents ouverts ont disparu.
"""
import asyncio
import concurrent.futures
import hashlib
import itertools
import os
import re
import shutil
import time
import unicodedata
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.services import photolab_moteur as PM

router = APIRouter()
# Un nom ne finit ni par « . » ni par une espace : Windows les retire en silence (« a.png. » devient « a.png »), le
# fichier copié n'aurait alors plus le nom qu'on ouvre.
_NOM_IMAGE = re.compile(r"[A-Za-z0-9_]([A-Za-z0-9._ -]{0,179}[A-Za-z0-9_-])?")
_NOM_SERVI = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,180}")
FORMATS = ("pcraft", "psd", "psb", "png", "jpg", "webp", "tif", "tga")
_COMPTEUR_RENDUS = itertools.count(1)
_PERIPHERIQUE = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9])", re.IGNORECASE)
_APERCU = re.compile(r"apercu-\d+-\d+\.png")
GARDES_APERCUS = 3
_VERROU_EXPORT = asyncio.Lock()          # choisir un nom libre ET enregistrer d'un seul tenant : deux sauvegardes ne se marchent pas dessus
ENTETE_GENERATION = "X-Photolab-Generation"

# Une opération du moteur peut durer jusqu'à son délai (60 s) en tenant un thread : sur le pool par défaut de la
# boucle (partagé avec tout le backend : to_thread, sqlite…) quelques rendus lents suffiraient à affamer les
# autres routes. Un petit pool à part borne ce que le Photolab peut occuper.
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="photolab")


async def _appeler(methode, params=None, delai_s=None):
    """(résultat, génération) — les erreurs du moteur deviennent des statuts HTTP qui disent la cause."""
    try:
        s = PM.session()
        return await asyncio.get_running_loop().run_in_executor(_POOL, s.appeler_g, methode, params or {}, delai_s)
    except PM.MoteurAbsent as e:
        raise HTTPException(503, str(e))
    except PM.MoteurOccupe as e:
        raise HTTPException(409, str(e))
    except PM.MoteurDelai as e:
        raise HTTPException(504, str(e))
    except PM.MoteurErreur as e:
        raise HTTPException(422, f"photocraft : {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))


def _json(resultat, gen):
    return JSONResponse(resultat, headers={ENTETE_GENERATION: str(gen)})


def _sur(souche: str) -> str:
    """Windows traite « CON », « NUL », « COM1 »… comme des périphériques, même avec une extension : on suffixe « _ »
    plutôt que de refuser un nom que l'utilisateur a légitimement choisi."""
    return souche + "_" if _PERIPHERIQUE.fullmatch(souche) else souche


def _relatif(chemin: str) -> str:
    """PM.relatif en erreur HTTP : une règle de chemin violée est une demande refusée (400), jamais un 500."""
    try:
        return PM.relatif(chemin)
    except ValueError as e:
        raise HTTPException(400, str(e))


def _entier(v, bas, haut, nom):
    if not isinstance(v, int) or isinstance(v, bool) or not bas <= v <= haut:
        raise HTTPException(400, f"{nom} : entier de {bas} à {haut} attendu")
    return v


@router.get("/etat")
async def etat():
    try:
        chemin = str(PM.chemin_cli()) if PM.FABRIQUE is None else "(banc)"
        present = True
    except PM.MoteurAbsent:
        chemin, present = None, False
    return {"version": PM.VERSION, "present": present, "chemin": chemin, **PM.etat_session()}


@router.get("/commandes")
async def commandes():
    return _json(*await _appeler("engine.commands"))


@router.post("/nouveau")
async def nouveau(body: dict):
    p = {"width": _entier(body.get("width"), 1, 30000, "width"), "height": _entier(body.get("height"), 1, 30000, "height")}
    for k in ("background", "resolution", "mode", "depth", "name"):
        if k in body:
            p[k] = body[k]
    return _json(*await _appeler("doc.new", p))


@router.post("/ouvrir")
async def ouvrir(body: dict):
    from app.config import settings
    nom = (body or {}).get("filename")
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        raise HTTPException(400, f"nom d'image refusé : {nom!r}")
    racine = settings.images_path.resolve()
    src = (settings.images_path / nom).resolve()
    # Un lien symbolique dans la Bibliothèque ne doit pas faire copier un fichier d'ailleurs dans le dossier du moteur.
    if racine not in src.parents:
        raise HTTPException(400, f"image hors de la Bibliothèque : {nom}")
    if not src.is_file():
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {nom}")
    souche, ext = os.path.splitext(nom)
    # Préfixe = empreinte du NOM d'origine : stable (rouvrir réutilise la copie), jamais deux noms qui se confondent
    # après nettoyage (« a b.png » et « a-b.png »).
    h = hashlib.sha1(nom.encode("utf-8")).hexdigest()[:8]
    sur = f"{h}-{_sur(re.sub(r'[^A-Za-z0-9._-]', '-', souche))}{re.sub(r'[^A-Za-z0-9.]', '-', ext)}"
    chemin = _relatif(f"entrees/{sur}")                    # refus (400) AVANT de copier quoi que ce soit
    await asyncio.to_thread(shutil.copyfile, src, PM.dossier_travail() / chemin)
    return _json(*await _appeler("doc.open", {"path": chemin}))


@router.post("/executer")
async def executer(body: dict):
    cid, params = (body or {}).get("command"), (body or {}).get("params") or {}
    try:
        PM.commande_autorisee(cid, params)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _json(*await _appeler("engine.execute", {"command": cid, "params": params}))


@router.get("/inspecter")
async def inspecter():
    return _json(*await _appeler("doc.inspect"))


def _ranger_apercu(tmp: Path, final: Path):
    """Renomme l'aperçu sous son nom définitif puis ne garde que les derniers : un fichier par rendu, sinon le
    navigateur et l'écran se disputent un même `apercu.png` en cours de réécriture."""
    os.replace(tmp, final)
    anciens = sorted((f for f in final.parent.iterdir() if _APERCU.fullmatch(f.name)),
                     key=lambda f: (f.stat().st_mtime_ns, f.name))
    for f in anciens[:-GARDES_APERCUS]:
        try:
            f.unlink()
        except OSError:
            pass                                          # ouvert par un lecteur : le prochain rendu le reprendra


@router.post("/rendu")
async def rendu(body: dict | None = None):
    m = _entier((body or {}).get("maxSide", 1024), 64, 8192, "maxSide")
    t0 = time.perf_counter()
    n = next(_COMPTEUR_RENDUS)
    # La génération n'est connue qu'APRÈS l'appel (le moteur a pu être relancé pendant celui-ci) : on écrit sous un
    # nom provisoire, puis on renomme avec la génération qui a réellement répondu.
    _, gen = await _appeler("doc.render", {"path": _relatif(f"rendus/tmp-{n}.png"), "maxSide": m})
    d = PM.dossier_travail() / "rendus"
    nom = f"apercu-{gen}-{n}.png"
    try:
        await asyncio.to_thread(_ranger_apercu, d / f"tmp-{n}.png", d / nom)
    except OSError as e:
        raise HTTPException(500, f"aperçu introuvable après le rendu : {e}")
    return _json({"url": f"/api/photolab/rendus/{nom}", "ms": round((time.perf_counter() - t0) * 1000)}, gen)


@router.post("/enregistrer")
async def enregistrer(body: dict):
    fmt = (body or {}).get("format")
    if fmt not in FORMATS:
        raise HTTPException(400, f"format hors liste : {fmt!r} ({', '.join(FORMATS)})")
    # ASCII d'abord (« Photo d'été » -> « Photo-d-ete ») : Windows et le moteur ne se fient pas aux accents.
    brut = unicodedata.normalize("NFKD", str((body or {}).get("nom") or "")).encode("ascii", "ignore").decode()
    base = _sur(re.sub(r"[^A-Za-z0-9_-]+", "-", brut).strip("-")[:80] or "photolab")
    q = None
    if "quality" in (body or {}):
        q = _entier(body["quality"], 1, 100, "quality")
    dossier = PM.dossier_travail() / "exports"
    async with _VERROU_EXPORT:
        fichier, k = f"{base}.{fmt}", 1
        while (dossier / fichier).exists():               # jamais d'écrasement : un export est le travail de quelqu'un
            k += 1
            fichier = f"{base}-{k}.{fmt}"
        p = {"path": _relatif(f"exports/{fichier}"), "format": fmt}
        if q is not None:
            p["quality"] = q
        _, gen = await _appeler("doc.save", p)
    return _json({"fichier": fichier, "url": f"/api/photolab/exports/{fichier}"}, gen)


def _servir(sous, nom):
    if not _NOM_SERVI.fullmatch(nom or ""):
        raise HTTPException(400, "nom refusé")
    f = PM.dossier_travail() / sous / nom
    if not f.is_file():
        raise HTTPException(404, "introuvable")
    if sous == "rendus":
        # no-store : un aperçu est éphémère (rangé après 3 rendus), jamais à resservir depuis le cache du navigateur.
        return FileResponse(f, media_type="image/png", headers={"Cache-Control": "no-store"})
    return FileResponse(f, filename=nom)                  # export : Content-Disposition = nom de téléchargement


@router.get("/rendus/{nom}")
async def servir_rendu(nom: str):
    return _servir("rendus", nom)


@router.get("/exports/{nom}")
async def servir_export(nom: str):
    return _servir("exports", nom)
