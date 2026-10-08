"""Routes du Photolab (t136, P1, 07/10/2026) : /api/photolab — le pont HTTP vers le moteur photocraft.

L'écran (P2) ne parle qu'à ces routes. Les fichiers n'entrent et ne sortent que par elles : une image de la
Bibliothèque est COPIÉE dans <données>/photolab/entrees/ avant d'être ouverte (le moteur ne lit que son dossier),
les rendus et exports sont servis depuis rendus/ et exports/. Rien de payant : le moteur est local.

Chaque réponse qui a parlé au moteur porte l'en-tête X-Photolab-Generation : la génération du processus qui a
répondu. Si elle change entre deux demandes, le moteur a été relancé et les documents ouverts ont disparu.
"""
import asyncio
import concurrent.futures
import functools
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
    return await _pool(lambda s: s.appeler_g, methode, params or {}, delai_s)


async def _pool(choisir, *args):
    """`choisir(session)` rend la fonction à lancer sur le pool dédié avec `args`. Les erreurs du moteur deviennent
    des statuts HTTP (503 absent, 409 occupé, 504 délai, 422 refus du moteur, 400 valeur refusée)."""
    try:
        s = PM.session()
        return await asyncio.get_running_loop().run_in_executor(_POOL, choisir(s), *args)
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
    """Le registre du moteur ; chaque entrée gagne ses `champs` (parsés une fois par génération) pour les dialogues."""
    return _json(*await _pool(lambda s: functools.partial(PM.commandes, s)))


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
    # Syntaxe d'abord : une commande illisible ne démarre pas le moteur pour lire son registre.
    if not isinstance(cid, str) or not PM._ID_COMMANDE.fullmatch(cid):
        raise HTTPException(400, f"commande illisible : {cid!r}")
    reg = await _pool(lambda s: functools.partial(PM.registre, s))
    kind = etat = None
    if cid == "layer.setAdjustment" and isinstance(params, dict):
        # Les clés admises dépendent du kind du calque VISÉ : lu dans le document, jamais déclaré par l'écran (sinon
        # le moteur ignorerait en silence les clés d'un autre kind).
        insp, _ = await _appeler("doc.inspect")
        cible = params.get("layer", (insp or {}).get("activeLayer"))
        calque = next((c for c in PM._a_plat((insp or {}).get("layers")) if c.get("id") == cible), None)
        if calque is None:
            raise HTTPException(400, f"layer.setAdjustment : calque introuvable : {cible!r}")
        kind = PM.PR.kind_de(calque)
        if kind is None:
            raise HTTPException(400, f"layer.setAdjustment : le calque {cible} n'est pas un calque de réglage")
        etat = calque.get("adjustment")                    # colorisation actuelle : bornes de hue/saturation
        # La cible est FIGÉE : sans `layer`, le moteur prendrait le calque actif AU MOMENT de l'exécution ; s'il a
        # changé depuis la lecture, des clés vérifiées pour ce kind iraient à un réglage d'un autre kind.
        params = {**params, "layer": cible}
    try:
        PM.commande_autorisee(cid, params, reg, kind, etat)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _json(*await _appeler("engine.execute", {"command": cid, "params": params}))


@router.get("/inspecter")
async def inspecter():
    insp, gen = await _appeler("doc.inspect")
    return _json(PM.elaguer_inspect(insp), gen)


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


@router.post("/apercu")
async def apercu(body: dict):
    """t138 : {"etapes": [{command, params}] (1..12), "maxSide": 64..2048 = 1024} -> {"url", "ms", "resultats"}.
    Les étapes sont jouées par le moteur sur une COPIE du document (l'original, son historique et sa pile de
    rétablissement restent intacts) ; filtres, réglages, styles, setAdjustment, setProps seulement. Refus de la liste
    blanche -> 400 sans appel ; refus du moteur sur une étape -> 422, la copie étant refermée quand même."""
    corps = body if isinstance(body, dict) else {}
    m = _entier(corps.get("maxSide", 1024), 64, 2048, "maxSide")
    t0 = time.perf_counter()
    sortie, gen = await _pool(lambda s: functools.partial(PM.apercu, s), corps.get("etapes"), m)
    return _json({"url": f"/api/photolab/rendus/{sortie['fichier']}", "ms": round((time.perf_counter() - t0) * 1000),
                  "resultats": sortie["resultats"]}, gen)


@router.get("/histogramme")
async def histogramme(maxSide: int = 256, sans: int | None = None):
    """t138 : {"r","g","b","l"} (256 comptes chacun) du document actif rendu à maxSide (64..1024) ; `sans` = id d'un
    calque de l'ORIGINAL à masquer (le réglage en cours d'édition : Courbes et Niveaux montrent l'histogramme
    d'AVANT eux). Calculé sur une copie, l'original n'est pas touché."""
    m = _entier(maxSide, 64, 1024, "maxSide")
    return _json(*await _pool(lambda s: functools.partial(PM.histogramme, s), sans, m))


def _base_sure(nom, defaut="photolab") -> str:
    # ASCII d'abord (« Photo d'été » -> « Photo-d-ete ») : Windows et le moteur ne se fient pas aux accents.
    brut = unicodedata.normalize("NFKD", str(nom or "")).encode("ascii", "ignore").decode()
    return _sur(re.sub(r"[^A-Za-z0-9_-]+", "-", brut).strip("-")[:80] or defaut)


async def _exporter(fmt, base, q):
    """doc.save sous exports/<base>.<fmt> (suffixe -2, -3… plutôt qu'un écrasement) -> (fichier, génération)."""
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
    return fichier, gen


@router.post("/enregistrer")
async def enregistrer(body: dict):
    fmt = (body or {}).get("format")
    if fmt not in FORMATS:
        raise HTTPException(400, f"format hors liste : {fmt!r} ({', '.join(FORMATS)})")
    q = None
    if "quality" in (body or {}):
        q = _entier(body["quality"], 1, 100, "quality")
    fichier, gen = await _exporter(fmt, _base_sure((body or {}).get("nom")), q)
    return _json({"fichier": fichier, "url": f"/api/photolab/exports/{fichier}"}, gen)


# ── t137 (P2) : ce que l'écran ajoute au pont ────────────────────────────────────────────────────────────────────

@router.get("/session")
async def session_liste():
    """Documents ouverts, document actif, couleurs de premier plan et d'arrière-plan (méthode `session.list`)."""
    return _json(*await _appeler("session.list"))


@router.post("/historique")
async def historique(body: dict):
    """{"annuler": n} ou {"retablir": n} (1..100, entier, un seul des deux) -> {"inspect": doc.inspect après,
    "completed": n faits, "failed": n refusés} (demander plus que l'historique n'est pas une erreur). UNE requête batch :
    le moteur n'a aucun saut direct dans l'historique, l'écran convertit « clic sur l'état k » en n annulations."""
    corps = body if isinstance(body, dict) else {}
    cles = [k for k in ("annuler", "retablir") if k in corps]
    if len(cles) != 1:
        raise HTTPException(400, "historique : exactement un de « annuler » ou « retablir » est attendu")
    n = _entier(corps[cles[0]], 1, 100, cles[0])
    return _json(*await _pool(lambda s: functools.partial(PM.historique, s), cles[0], n))


@router.get("/vignettes")
async def vignettes(maxSide: int = 48):
    """Une vignette PAR calque du document actif : {"vignettes": {"<id du calque>": "/api/photolab/rendus/vig-….png"}}.
    Les fichiers sont servis par /rendus/. Cache par (génération, révision) côté service."""
    m = _entier(maxSide, 16, 256, "maxSide")
    noms, gen = await _pool(lambda s: functools.partial(PM.vignettes, s), m)
    return _json({"vignettes": {k: f"/api/photolab/rendus/{n}" for k, n in noms.items()}}, gen)


_VERROU_BIBLIO = asyncio.Lock()          # choisir un nom libre ET copier d'un seul tenant (deux enregistrements la même seconde)


@router.post("/bibliotheque")
async def bibliotheque(body: dict):
    """{"format": "png"|"jpg", "quality"?} : enregistre le document actif dans exports/ puis COPIE le fichier dans la
    Bibliothèque sous photolab_<AAAAMMJJ-HHMMSS>_<base>.<ext> ; le préfixe + la note d'index donnent la source
    « Photolab » (même mécanisme que vector_). Rend {"filename": nom}."""
    from app.config import settings
    from app.services import library_index as LI
    fmt = (body or {}).get("format")
    if fmt not in ("png", "jpg"):
        raise HTTPException(400, f"format hors liste : {fmt!r} (png, jpg)")
    q = None
    if "quality" in (body or {}):
        q = _entier(body["quality"], 1, 100, "quality")
    nom_doc = (body or {}).get("nom")
    if not nom_doc:
        nom_doc = (await _appeler("doc.inspect"))[0].get("name")      # sans document, le moteur refuse : 422 dit
    base = _base_sure(nom_doc, "image")
    fichier, gen = await _exporter(fmt, base, q)
    src = PM.dossier_travail() / "exports" / fichier
    dossier = settings.images_path
    dossier.mkdir(parents=True, exist_ok=True)
    horo = time.strftime("%Y%m%d-%H%M%S")
    async with _VERROU_BIBLIO:
        nom, k = f"photolab_{horo}_{base}.{fmt}", 1
        while (dossier / nom).exists():
            k += 1
            nom = f"photolab_{horo}_{base}-{k}.{fmt}"
        try:
            await asyncio.to_thread(shutil.copyfile, src, dossier / nom)
        except OSError as e:
            raise HTTPException(500, f"copie dans la Bibliothèque impossible : {e}")
    try:
        src.unlink()                                      # exports/ est réservé à /enregistrer : pas de doublon caché
    except OSError:
        pass
    await LI.noter([nom], "photolab")
    return _json({"filename": nom}, gen)


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
