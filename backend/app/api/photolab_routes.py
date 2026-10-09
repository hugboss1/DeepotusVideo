"""Routes du Photolab (t136, P1, 07/10/2026) : /api/photolab — le pont HTTP vers le moteur photocraft.

L'écran (P2) ne parle qu'à ces routes. Les fichiers n'entrent et ne sortent que par elles : une image de la
Bibliothèque est COPIÉE dans <données>/photolab/entrees/ avant d'être ouverte (le moteur ne lit que son dossier),
les rendus et exports sont servis depuis rendus/ et exports/. Rien de payant : le moteur est local.

Chaque réponse qui a parlé au moteur porte l'en-tête X-Photolab-Generation : la génération du processus qui a
répondu. Si elle change entre deux demandes, le moteur a été relancé et les documents ouverts ont disparu.
"""
import asyncio
import collections
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
from fastapi.responses import FileResponse, JSONResponse, Response

from app.services import photolab_moteur as PM
from app.services import photolab_espaces as ESP
from app.services import photolab_preferences as PREF
from app.services import photolab_nuancier as NUA

router = APIRouter()
# Un nom ne finit ni par « . » ni par une espace : Windows les retire en silence (« a.png. » devient « a.png »), le
# fichier copié n'aurait alors plus le nom qu'on ouvre.
_NOM_IMAGE = re.compile(r"[A-Za-z0-9_]([A-Za-z0-9._ -]{0,179}[A-Za-z0-9_-])?")
_NOM_SERVI = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,180}")
FORMATS = ("pcraft", "psd", "psb", "png", "jpg", "webp", "tif", "tga")
_COMPTEUR_RENDUS = itertools.count(1)
_PERIPHERIQUE = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9])", re.IGNORECASE)
_APERCU = re.compile(r"apercu-\d+-\d+\.png")
# t139 : le fichier de travail d'une image enregistrée par /bibliotheque — son nom, extension aplatie
# (photolab_20261008-154030_herbe.png -> photolab_20261008-154030_herbe-png.pcraft) : unique comme l'image elle-même.
_TRAVAIL = re.compile(r"photolab_\d{8}-\d{6}_[A-Za-z0-9_-]{1,120}-(png|jpg)\.pcraft")
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


# t139 : l'image de la Bibliothèque d'où vient chaque document, par CHEMIN moteur (session.list) — le nom ne suffit pas :
# un .pcraft rouvert reprend le nom du document d'origine. Le moteur rattache un document au fichier de chaque doc.save
# (exports/…, biblio/…) : la table suit ces rattachements. Bornée ; perdue au redémarrage (les documents aussi).
_ORIGINES: "collections.OrderedDict[str, str]" = collections.OrderedDict()
_ORIGINES_MAX = 256


def _retenir(chemin, nom):
    if not chemin or not nom:
        return
    _ORIGINES[chemin] = nom
    _ORIGINES.move_to_end(chemin)
    while len(_ORIGINES) > _ORIGINES_MAX:
        _ORIGINES.popitem(last=False)


async def _chemin_actif():
    """Le chemin du document actif selon le moteur, ou None (aucun document, document neuf, moteur absent)."""
    try:
        s, _ = await _appeler("session.list")
    except HTTPException:
        return None
    if not isinstance(s, dict):
        return None
    for d in s.get("documents") or []:
        if isinstance(d, dict) and d.get("index") == s.get("active"):
            return d.get("path") if isinstance(d.get("path"), str) else None
    return None


def _image_biblio(nom):
    """Chemin d'une image de la Bibliothèque, ou None (nom refusé, hors du dossier — lien symbolique —, absente)."""
    from app.config import settings
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        return None
    src = (settings.images_path / nom).resolve()
    return src if settings.images_path.resolve() in src.parents and src.is_file() else None


async def _travail_de(nom):
    """t139 : le fichier de travail (.pcraft, calques) d'une image enregistrée par le Photolab, ou None. Le lien est le
    doc_id de l'index ; il n'est suivi que pour une image de source « photolab », vers un nom de la forme écrite par
    /bibliotheque, DANS biblio/ — jamais un chemin venu d'ailleurs. Résilient : l'index ne casse jamais l'ouverture."""
    try:
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as session:
            row = await session.get(LibraryAsset, nom)
            source, doc = (row.source, row.doc_id) if row is not None else (None, None)
    except Exception:  # noqa: BLE001
        return None
    if source != "photolab" or not isinstance(doc, str) or not _TRAVAIL.fullmatch(doc):
        return None
    dossier = (PM.dossier_travail() / "biblio").resolve()
    p = (dossier / doc).resolve()
    return p if p.parent == dossier and p.is_file() else None


@router.post("/ouvrir")
async def ouvrir(body: dict):
    """{"filename", "calques"?: bool (défaut true)} : copie l'image (ou, si elle a été enregistrée par le Photolab avec
    ses calques, son fichier de travail .pcraft) dans entrees/ et l'ouvre. Réponse du moteur + "travail": bool.
    L'original n'est jamais ouvert en place : un enregistrement écrit toujours un NOUVEAU fichier."""
    corps = body or {}
    nom = corps.get("filename")
    calques = corps.get("calques", True)
    if not isinstance(calques, bool):
        raise HTTPException(400, "calques : booléen attendu")
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        raise HTTPException(400, f"nom d'image refusé : {nom!r}")
    src = _image_biblio(nom)
    if src is None:
        from app.config import settings
        brut = (settings.images_path / nom).resolve()
        # Un lien symbolique dans la Bibliothèque ne doit pas faire copier un fichier d'ailleurs dans le dossier du moteur.
        if settings.images_path.resolve() not in brut.parents:
            raise HTTPException(400, f"image hors de la Bibliothèque : {nom}")
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {nom}")
    travail = await _travail_de(nom) if calques else None
    if travail is not None:
        src, souche, ext = travail, travail.stem, travail.suffix
    else:
        souche, ext = os.path.splitext(nom)
    # Préfixe = empreinte du NOM d'origine : stable (rouvrir réutilise la copie), jamais deux noms qui se confondent
    # après nettoyage (« a b.png » et « a-b.png »).
    h = hashlib.sha1(nom.encode("utf-8")).hexdigest()[:8]
    sur = f"{h}-{_sur(re.sub(r'[^A-Za-z0-9._-]', '-', souche))}{re.sub(r'[^A-Za-z0-9.]', '-', ext)}"
    chemin = _relatif(f"entrees/{sur}")                    # refus (400) AVANT de copier quoi que ce soit
    await asyncio.to_thread(shutil.copyfile, src, PM.dossier_travail() / chemin)
    resultat, gen = await _appeler("doc.open", {"path": chemin})
    _retenir(chemin, nom)
    if isinstance(resultat, dict):
        resultat = {**resultat, "travail": travail is not None}
    return _json(resultat, gen)


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
    if cid == "layer.smartFilter.setParams" and isinstance(params, dict):
        # t157 : les clés admises sont celles du filtre VISÉ (doc.inspect : smartFilters[index].command) ; la cible est
        # figée comme pour setAdjustment.
        insp, _ = await _appeler("doc.inspect")
        try:
            PM.verifier_filtre_dynamique(reg, params, insp or {})
        except ValueError as e:
            raise HTTPException(400, str(e))
        params = {**params, "layer": params.get("layer", (insp or {}).get("activeLayer"))}
    try:
        PM.commande_autorisee(cid, params, reg, kind, etat)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if cid == "filter.render.flame" and isinstance(params, dict) and "path" in params:
        # t158 : un nom de tracé inconnu serait ignoré en silence par le moteur
        liste, _ = await _appeler("engine.execute", {"command": "path.list", "params": {}})
        try:
            PM.verifier_trace(params, liste)
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
    avant = await _chemin_actif()
    async with _VERROU_EXPORT:
        fichier, k = f"{base}.{fmt}", 1
        while (dossier / fichier).exists():               # jamais d'écrasement : un export est le travail de quelqu'un
            k += 1
            fichier = f"{base}-{k}.{fmt}"
        p = {"path": _relatif(f"exports/{fichier}"), "format": fmt}
        if q is not None:
            p["quality"] = q
        _, gen = await _appeler("doc.save", p)
    _retenir(p["path"], _ORIGINES.get(avant))             # le moteur a rattaché le document à ce fichier
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


@router.get("/reperes")
async def reperes():
    """t152 : les repères du document actif {"horizontal": [...], "vertical": [...], "revision"} — lus dans une COPIE
    enregistrée en .pcraft (doc.inspect ne les rend pas) ; listes vides et révision nulle sans document."""
    lus, gen = await _pool(lambda s: functools.partial(PM.reperes, s))
    if lus is None:
        return _json({"horizontal": [], "vertical": [], "revision": None}, gen)
    rev = (PM._CACHE_REPERES.get("base") or (None, None, None))[2]
    return _json({**lus, "revision": rev}, gen)


# ── t153 : panneaux Motifs (vignettes) et Couches (contenu des alpha) ───────────────────────────────────────────────
@router.get("/motifs/{ident}.png")
async def vignette_motif(ident: str):
    """La vignette 64×64 d'un motif de la bibliothèque (document temporaire refermé ; l'original n'est pas touché)."""
    octets, gen = await _pool(lambda s: functools.partial(PM.vignette_motif, s), ident)
    return Response(octets, media_type="image/png",
                    headers={ENTETE_GENERATION: str(gen), "Cache-Control": "private, max-age=3600"})


@router.get("/presets/{genre}/vignette.png")
async def vignette_preset(genre: str, cle: str, groupe: str | None = None):
    """t156 : la vignette 64×64 d'une forme personnalisée (genre « forme ») ou d'un style de calque (« style ») — nom et
    groupe du moteur ; « motif » (id) comme /motifs/{id}.png. Document temporaire refermé ; l'original n'est pas touché."""
    octets, gen = await _pool(lambda s: functools.partial(PM.vignette_preset, s), genre, cle, groupe)
    return Response(octets, media_type="image/png",
                    headers={ENTETE_GENERATION: str(gen), "Cache-Control": "private, max-age=3600"})


@router.get("/couches")
async def couches(maxSide: int = 96, index: int | None = None):
    """{"couches": [{"index", "png"}]} : le contenu des couches alpha du document actif en niveaux de gris (blanc =
    sélectionné), rendu sur une copie ; `index` = une seule couche ; maxSide 32..1024."""
    m = _entier(maxSide, 32, 1024, "maxSide")
    out, gen = await _pool(lambda s: functools.partial(PM.couches_alpha, s), m, index)
    return _json({"couches": out}, gen)


# ── t157 : masques de fusion, Sélectionner et masquer, Galerie de filtres ────────────────────────────────────────────
@router.get("/masques")
async def masques(maxSide: int = 48, layer: int | None = None):
    """{"masques": [{"layer", "png"}]} : le masque de fusion de chaque calque masqué (blanc = révélé), rendu sur une
    copie ; `layer` = un seul calque (le masque montré seul sur la toile) ; maxSide 16..2048."""
    m = _entier(maxSide, 16, 2048, "maxSide")
    out, gen = await _pool(lambda s: functools.partial(PM.masques, s), m, layer)
    return _json({"masques": out}, gen)


@router.post("/masquer/apercu")
async def masquer_apercu(body: dict):
    """{"reglages": {radius, smooth…}, "vue": une de VUES_MASQUER, "transparence": 0..100 = 50, "inverser": false,
    "maxSide": 64..2048 = 1024} -> {"url", "ms", "bounds"?} : une vue de « Sélectionner et masquer » calculée par le
    moteur sur une copie. La sortie n'est jamais choisie ici (400) ; sans sélection : 400."""
    corps = body if isinstance(body, dict) else {}
    m = _entier(corps.get("maxSide", 1024), 64, 2048, "maxSide")
    t0 = time.perf_counter()
    sortie, gen = await _pool(lambda s: functools.partial(PM.apercu_masque, s), corps.get("reglages") or {},
                              corps.get("vue"), corps.get("transparence", 50), corps.get("inverser", False), m)
    rep = {"url": f"/api/photolab/rendus/{sortie['fichier']}", "ms": round((time.perf_counter() - t0) * 1000)}
    if "bounds" in sortie:
        rep["bounds"] = sortie["bounds"]
    return _json(rep, gen)


@router.get("/galerie")
async def galerie():
    """Le catalogue de la Galerie de filtres : {"categories", "filters": [{category, command, key, name, params}]}."""
    return _json(*await _pool(lambda s: functools.partial(PM.catalogue_galerie, s)))


_CLE_GALERIE = re.compile(r"[a-zA-Z][A-Za-z0-9]{0,40}")


@router.get("/galerie/vignettes")
async def galerie_vignettes(cles: str):
    """{"vignettes": {clé: data-URL 80×56}} : chaque filtre (« cles » séparées par des virgules, 16 au plus) appliqué par
    le moteur au centre du document actif, sur une copie."""
    liste = [c for c in (cles or "").split(",") if c]
    if not liste or not all(_CLE_GALERIE.fullmatch(c) for c in liste):
        raise HTTPException(400, f"clés illisibles : {cles!r}")
    out, gen = await _pool(lambda s: functools.partial(PM.vignettes_galerie, s), liste)
    return _json({"vignettes": out}, gen)


_VERROU_BIBLIO = asyncio.Lock()          # choisir un nom libre ET copier d'un seul tenant (deux enregistrements la même seconde)


# ── t158 : Fichier sûr — copie, Revenir, Placer, export de calque (compositions du pont, jamais un chemin reçu) ──────
FORMATS_CALQUE = ("png", "jpg", "webp")
DESTINATIONS = ("telecharger", "bibliotheque")


def _qualite(corps):
    return _entier(corps["quality"], 1, 100, "quality") if "quality" in corps else None


def _destination(corps, fmt):
    d = corps.get("destination", "telecharger")
    if d not in DESTINATIONS:
        raise HTTPException(400, f"destination hors liste : {d!r} ({', '.join(DESTINATIONS)})")
    if d == "bibliotheque" and fmt not in ("png", "jpg"):
        raise HTTPException(400, f"la Bibliothèque reçoit du png ou du jpg, pas {fmt!r}")
    return d


async def _livrer(fichier, fmt, base, destination, gen):
    """Un fichier de exports/ : rendu à télécharger, ou DÉPLACÉ dans la Bibliothèque sous photolab_<horodatage>_<base>
    (lignée vers l'image d'où vient le document actif, si elle existe)."""
    if destination == "telecharger":
        return _json({"fichier": fichier, "url": f"/api/photolab/exports/{fichier}"}, gen)
    from app.config import settings
    from app.services import library_index as LI
    src = PM.dossier_travail() / "exports" / fichier
    dossier = settings.images_path
    dossier.mkdir(parents=True, exist_ok=True)
    horo = time.strftime("%Y%m%d-%H%M%S")
    async with _VERROU_BIBLIO:
        nom = PM.nom_libre(dossier, f"photolab_{horo}_{base}", fmt)
        try:
            await asyncio.to_thread(shutil.copyfile, src, dossier / nom)
        except OSError as e:
            raise HTTPException(500, f"copie dans la Bibliothèque impossible : {e}")
    try:
        src.unlink()
    except OSError:
        pass
    origine = _ORIGINES.get(await _chemin_actif())
    parent = origine if _image_biblio(origine) is not None else None
    await LI.noter([nom], "photolab", parent=parent, relation="retouche" if parent else None)
    return _json({"filename": nom}, gen)


@router.post("/copie")
async def copie(body: dict):
    """Enregistrer une copie : {"format": FORMATS, "quality"?, "nom"?, "destination"?: telecharger|bibliotheque} — le
    document actif est dupliqué, la COPIE enregistrée puis refermée (l'original reste tel quel, fichier compris)."""
    corps = body if isinstance(body, dict) else {}
    fmt = corps.get("format")
    if fmt not in FORMATS:
        raise HTTPException(400, f"format hors liste : {fmt!r} ({', '.join(FORMATS)})")
    q, dest = _qualite(corps), _destination(corps, fmt)
    base = _base_sure(corps.get("nom"), "copie")
    async with _VERROU_EXPORT:                            # même dossier exports/ que /enregistrer
        fichier, gen = await _pool(lambda s: functools.partial(PM.copie_document, s), fmt, base, q)
    return await _livrer(fichier, fmt, base, dest, gen)


@router.post("/calque/exporter")
async def calque_exporter(body: dict):
    """Calque › Exporter sous / Exportation rapide : {"layer"?, "format": png|jpg|webp, "echelle"?: 1..1000 (%),
    "quality"?, "nom"?, "destination"?} — le calque seul, rogné, sur une copie du document."""
    corps = body if isinstance(body, dict) else {}
    fmt = corps.get("format")
    if fmt not in FORMATS_CALQUE:
        raise HTTPException(400, f"format hors liste : {fmt!r} ({', '.join(FORMATS_CALQUE)})")
    layer = corps.get("layer")
    if layer is not None and (not isinstance(layer, int) or isinstance(layer, bool) or layer < 0):
        raise HTTPException(400, "layer : identifiant de calque attendu")
    echelle = _entier(corps.get("echelle", 100), 1, 1000, "echelle")
    q, dest = _qualite(corps), _destination(corps, fmt)
    base = _base_sure(corps.get("nom"), "calque")
    async with _VERROU_EXPORT:
        fichier, gen = await _pool(lambda s: functools.partial(PM.exporter_calque, s), layer, fmt, base, echelle, q)
    return await _livrer(fichier, fmt, base, dest, gen)


@router.post("/revenir")
async def revenir_route():
    """Revenir à la version enregistrée : le fichier du moteur du document actif est rouvert, l'ancien fermé
    (historique perdu). Sans fichier enregistré : 400. -> session.list après."""
    avant = await _chemin_actif()
    resultat, gen = await _pool(lambda s: functools.partial(PM.revenir, s))
    if avant:
        _retenir(avant, _ORIGINES.get(avant))             # même chemin : la lignée suit
    return _json(resultat, gen)


@router.post("/placer")
async def placer_route(body: dict):
    """Placer incorporé : {"filename", "objetDynamique"?, "reduire"?} d'une image de la Bibliothèque -> copiée sous
    entrees/, collée au centre du document actif en objet dynamique (réduite si elle dépasse). t159 : les deux
    booléens viennent des préférences (Paramètres), vrais par défaut. -> {"layer", "bounds"}."""
    nom = (body or {}).get("filename")
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        raise HTTPException(400, f"nom d'image refusé : {nom!r}")
    inconnues = set(body) - {"filename", "objetDynamique", "reduire"}
    if inconnues:
        raise HTTPException(400, f"paramètre inconnu : {sorted(inconnues)[0]}")
    options = {k: body.get(k, True) for k in ("objetDynamique", "reduire")}
    if not all(isinstance(v, bool) for v in options.values()):
        raise HTTPException(400, "objetDynamique et reduire : booléens attendus")
    src = _image_biblio(nom)
    if src is None:
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {nom}")
    souche, ext = os.path.splitext(nom)
    h = hashlib.sha1(nom.encode("utf-8")).hexdigest()[:8]
    chemin = _relatif(f"entrees/{h}-{_sur(re.sub(r'[^A-Za-z0-9._-]', '-', souche))}{re.sub(r'[^A-Za-z0-9.]', '-', ext)}")
    await asyncio.to_thread(shutil.copyfile, src, PM.dossier_travail() / chemin)
    calque = unicodedata.normalize("NFC", souche)[:120] or "image"
    return _json(*await _pool(lambda s: functools.partial(PM.placer, s), chemin, calque,
                              options["objetDynamique"], options["reduire"]))


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
    # t139 : le fichier de travail (calques), sous biblio/ du dossier du moteur — la Bibliothèque ne montre que l'image.
    # Un échec ici n'annule pas l'image déjà déposée : la réponse dit simplement « travail »: null.
    travail = nom.rsplit(".", 1)[0] + "-" + fmt + ".pcraft"
    origine = _ORIGINES.get(await _chemin_actif())       # rattaché à exports/… par _exporter : la table a suivi
    try:
        (PM.dossier_travail() / "biblio").mkdir(parents=True, exist_ok=True)
        _, gen = await _appeler("doc.save", {"path": _relatif(f"biblio/{travail}"), "format": "pcraft"})
        _retenir(f"biblio/{travail}", origine)
    except HTTPException:
        travail = None
    # Lignée : l'image de la Bibliothèque d'où vient le document — donnée par l'appelant, sinon retrouvée par le pont —,
    # si elle existe vraiment.
    parent = (body or {}).get("parent")
    if _image_biblio(parent) is None:
        parent = origine if _image_biblio(origine) is not None else None
    await LI.noter([nom], "photolab", doc_id=travail, parent=parent, relation="retouche" if parent else None)
    return _json({"filename": nom, "travail": travail}, gen)


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


# ── t140 (P5, D10) : le repli « app native » ──────────────────────────────────────────────────────────────────

def _base_doc(d: dict) -> str:
    """Nom de base d'un document de session.list, tiré de son CHEMIN moteur (le nom d'un document ouvert n'est pas
    fiable) : sans dossier, empreinte, extension, préfixe d'enregistrement, ni horodatage d'un envoi précédent."""
    s = os.path.basename(str(d.get("path") or "")) or str(d.get("name") or "")
    s = re.sub(r"^[0-9a-f]{8}-", "", s)
    s = re.sub(r"(\.[A-Za-z0-9]{2,6})+$", "", s)
    s = re.sub(r"^photolab_\d{8}-\d{6}_", "", s)
    s = re.sub(r"(-retour)?-\d{8}-\d{6}(-\d+)?$", "", s)
    s = re.sub(r"-(png|jpg)$", "", s)
    return _base_sure(s, "document")


def _natif_libre(prefixe: str) -> str:
    dossier = PM.dossier_travail() / "natif"
    dossier.mkdir(parents=True, exist_ok=True)
    horo = time.strftime("%Y%m%d-%H%M%S")
    nom, k = f"{prefixe}-{horo}.pcraft", 1
    while (dossier / nom).exists():
        k += 1
        nom = f"{prefixe}-{horo}-{k}.pcraft"
    return _relatif(f"natif/{nom}")


async def _natif(fn, *args):
    from app.services import photolab_natif as PN
    try:
        return await asyncio.to_thread(fn, *args)
    except PN.NatifAbsent as e:
        raise HTTPException(503, str(e))
    except PN.NatifFerme as e:
        raise HTTPException(409, str(e))
    except PN.NatifInjoignable as e:
        raise HTTPException(504, str(e))
    except PN.NatifErreur as e:
        raise HTTPException(422, f"app native : {e}")


@router.get("/natif/etat")
async def natif_etat():
    from app.services import photolab_natif as PN
    return PN.etat()


@router.post("/natif/ouvrir")
async def natif_ouvrir(body: dict | None = None):
    """Enregistre le document actif en natif/<base>-<horodatage>.pcraft (calques compris) et l'ouvre dans l'app native
    (lancée si besoin). La lignée suit : le fichier envoyé garde l'origine du document."""
    from app.services import photolab_natif as PN
    if not PN.etat()["present"]:
        await _natif(PN.chemin_app)                         # 503 qui dit où le binaire manque
    s, _ = await _appeler("session.list")
    doc = next((d for d in (s.get("documents") or []) if isinstance(d, dict) and d.get("index") == s.get("active")), None) \
        if isinstance(s, dict) else None
    if doc is None:
        raise HTTPException(409, "aucun document ouvert à envoyer vers l'app native")
    origine = _ORIGINES.get(doc.get("path"))
    base = _base_doc(doc)
    fichier = _natif_libre(base)
    _, gen = await _appeler("doc.save", {"path": fichier, "format": "pcraft"})
    _retenir(fichier, origine)
    await _natif(PN.ouvrir, fichier)
    PN.dernier = {"fichier": fichier, "base": base, "origine": origine}
    return _json({"fichier": fichier}, gen)


@router.post("/natif/reprendre")
async def natif_reprendre(body: dict | None = None):
    """Fait enregistrer l'app native sous natif/<base>-retour-<horodatage>.pcraft puis l'ouvre dans le Photolab."""
    from app.services import photolab_natif as PN
    if not PN.etat()["actif"]:
        raise HTTPException(409, "aucune app native ouverte : rien à reprendre")
    fichier = _natif_libre((PN.dernier.get("base") or "document") + "-retour")
    await _natif(PN.enregistrer, fichier)
    resultat, gen = await _appeler("doc.open", {"path": fichier})
    _retenir(fichier, PN.dernier.get("origine"))
    if isinstance(resultat, dict):
        resultat = {**resultat, "fichier": fichier}
    return _json(resultat, gen)


# ── t140 (P5) : « À propos » — les licences livrées avec le moteur ───────────────────────────────────────────────

def _licences() -> dict:
    """nom affiché -> fichier, pour les seuls textes de licence livrés : notre NOTICE, les mentions et licences amont
    (vendor/licences-photocraft/), et les licences de l'archive du moteur (LICENSE-*, OFL-*). Rien d'autre n'est servi."""
    v = PM.RACINE_APP / "vendor"
    out = {"NOTICE-photocraft.txt": v / "NOTICE-photocraft.txt"}
    lic = v / "licences-photocraft"
    if lic.is_dir():
        for f in sorted(lic.iterdir()):
            out[f"licences-photocraft/{f.name}"] = f
    base = v / f"photocraft-{PM.VERSION}"
    if base.is_dir():
        for f in sorted(base.rglob("*")):
            if f.name.startswith(("LICENSE-", "OFL-")):
                out[f.name] = f
    return {k: p for k, p in out.items() if p.is_file()}


# ── t151 : espaces de travail (disposition de l'écran, aucun appel au moteur) ──────────────────────────────────────
@router.get("/espaces")
async def espaces():
    """L'état des espaces de travail : enregistré, ou le défaut (fichier absent, illisible ou refusé)."""
    return await asyncio.to_thread(ESP.lire)


@router.put("/espaces")
async def espaces_ecrire(body: dict):
    """Remplace l'état (liste blanche stricte : photolab_espaces.valider) ; 400 qui dit pourquoi sinon."""
    try:
        return await asyncio.to_thread(ESP.ecrire, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── t159 : préférences de l'écran, raccourcis, menus (aucun appel au moteur : prefs.* reste refusé) ─────────────────
@router.get("/preferences")
async def preferences():
    """{"etat", "enregistre"} : l'état enregistré, ou le défaut (`enregistre: false` : l'écran peut reprendre ce que le
    navigateur gardait)."""
    return await asyncio.to_thread(PREF.lire)


@router.put("/preferences")
async def preferences_ecrire(body: dict):
    """Remplace l'état (liste blanche stricte : photolab_preferences.valider) ; 400 qui dit pourquoi sinon."""
    try:
        return await asyncio.to_thread(PREF.ecrire, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/preferences/reinitialiser")
async def preferences_reinitialiser():
    """Retour aux défauts (préférences, raccourcis, menus), enregistré."""
    return await asyncio.to_thread(PREF.reinitialiser)


# ── t153 : nuancier (données Deepotus ; le moteur n'a aucune commande de nuancier) ─────────────────────────────────
@router.get("/nuancier")
async def nuancier():
    """Les groupes de nuances : enregistrés, ou le défaut (fichier absent, illisible ou refusé)."""
    return await asyncio.to_thread(NUA.lire)


@router.put("/nuancier")
async def nuancier_ecrire(body: dict):
    """Remplace le nuancier (liste blanche stricte : photolab_nuancier.valider) ; 400 qui dit pourquoi sinon."""
    try:
        return await asyncio.to_thread(NUA.ecrire, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/licences")
async def licences():
    import json
    try:
        m = json.loads((PM.RACINE_APP / "vendor" / "photocraft.json").read_text("utf-8"))
    except (OSError, ValueError):
        m = {}
    return {"version": m.get("version", PM.VERSION), "depot": m.get("depot"), "licence": m.get("licence"),
            "fichiers": list(_licences())}


@router.get("/licences/{nom:path}")
async def licence(nom: str):
    f = _licences().get(nom)
    if f is None:
        raise HTTPException(404, "licence inconnue")
    return FileResponse(f, media_type="text/plain; charset=utf-8")
