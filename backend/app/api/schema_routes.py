# -*- coding: utf-8 -*-
"""t314 (28/10/2026) (C2 Scan : illustration ou schéma → base d'animation motion, spec boîte à outils §7.3) — /api/schema.

Boucle locale SEULEMENT (`routes._require_localhost`) ; la route qui peut dépenser (détourage fal) a aussi
`routes._require_local_depense`.
- `GET  /devis`        les modèles de détourage proposés et leur prix : {defaut, modeles: [{id, label, voie, usd,
                       disponible, raison}]} ; gratuit.
- `POST /analyser`     multipart `image` + `detourage` (défaut local-chroma) + `langue` (fr | en | auto) + `max_usd`
                       (requis pour un modèle fal) -> {largeur, hauteur, detourage, usd, elements (png en data URL),
                       liens, avertissements, duree_ms} (schema_calques.analyser).
- `POST /animation`    JSON {doc_id, nom, largeur, hauteur, fond?, script?, calques: [{image, nom, nature, boite, queue?,
                       pointe?}]} -> {graph, graph_id, page_id, aspect, duree_s} : le graphe Studio (schema_animation),
                       enregistré au magasin du Studio, la page motion code enregistrée (motion_code.enregistrer).

Détourage (Global Constraints du plan t314) : `local-chroma` = le masque de schema_calques (alpha s'il y en a, sinon fond
estimé par le pourtour, sans la garde de couverture de pixel_ops.chroma_key qui refuse un schéma au trait) ;
`local-rembg` si le paquet est installé ; les modèles fal du registre unique (sans ceux qui exigent un sujet nommé) sont
PAYANTS : refus gratuits (_detourage_controles : 400 / 503 clé) puis accord (`max_usd` ≥ devis, sinon 409 sans appel)
puis garde des plafonds (catégorie « vectorlab », 402) — dans cet ordre, avant l'envoi du fichier.
L'OCR (scan_ocr, t312) lit l'image D'ORIGINE (meilleur contraste) ; indisponible : aucune étiquette, avertissement.
Journaux : nombres, tailles, durées — jamais le texte lu.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import math
import re
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from app.services import detourage as DT
from app.services import schema_calques as SC

router = APIRouter()

LANGUES = ("fr", "en", "auto")
DEFAUT = "local-chroma"
MAX_CALQUES = 60
MAX_CORPS = 512 * 1024
_ID_DOC = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FICHIER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
CATEGORIE = "vectorlab"


class RefusAccord(ValueError):
    """Le devis du détourage payant n'a pas été accepté (409 structuré {message, usd}) ; nommée au L10."""


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _traduire(texte: str, request: Request) -> str:
    from app.i18n import erreurs as _ERR
    return _ERR.texte(texte, _ERR.langue(request)) if texte else texte


def _usd(mid: str) -> float:
    return SC.usd_detourage(mid)


def modeles() -> list[str]:
    return SC.detourages()


@router.get("/devis", dependencies=[Depends(_local)])
async def devis(request: Request):
    lst = []
    for m in modeles():
        cle = DT.cle_manquante(m)
        lst.append({"id": m, "label": DT.REGISTRE[m]["label"], "voie": DT.REGISTRE[m]["voie"], "usd": _usd(m),
                    "disponible": cle is None, "raison": cle or ""})
    return {"defaut": DEFAUT, "modeles": lst}


def _lignes_ramenees(lignes: list, fx: float, fy: float) -> list:
    if fx == 1 and fy == 1:
        return lignes
    out = []
    for li in lignes:
        mots = [dict(m, x=m["x"] * fx, y=m["y"] * fy, l=m["l"] * fx, h=m["h"] * fy) for m in li.get("mots") or []]
        out.append(dict(li, mots=mots))
    return out


@router.post("/analyser", dependencies=[Depends(_local), Depends(_depense_locale)])
async def analyser(request: Request, image: UploadFile = File(...), detourage: str = Form(DEFAUT),
                   langue: str = Form("fr"), max_usd: str = Form("")):
    from app.api import routes as R
    from app.services import scan_ocr as O
    from app.services import scan_pages as SP
    from PIL import Image
    t0 = time.perf_counter()
    if langue not in LANGUES:
        raise HTTPException(400, "Langue de lecture inconnue : fr, en ou auto.")
    mid = str(detourage or DEFAUT)
    R._detourage_controles(mid, DT.IMAGE, "-", request)          # 400 inconnu / autre nature, 503 clé absente
    if mid not in modeles():
        raise HTTPException(400, "Ce détourage n'est pas proposé pour un schéma : choisis-en un autre.")
    octets = await image.read(SP.MAX_OCTETS + 1)
    try:
        plan = await asyncio.to_thread(SP.charger, [(image.filename or "", octets)])
    except SP.RefusPages as e:
        raise HTTPException(e.statut, str(e)) from None
    page = next((p for p in plan if p["genre"] == "image"), None)
    if page is None:
        raise HTTPException(422, "Aucune image dans ce fichier : dépose une photo ou un dessin.")
    source = page["octets"]
    usd = _usd(mid)
    if DT.REGISTRE[mid]["voie"] == "fal":
        try:
            accepte = float(max_usd)
        except ValueError:
            accepte = float("nan")
        if not math.isfinite(accepte) or accepte < 0 or usd > accepte + 1e-9:
            try:
                raise RefusAccord("Le coût du détourage a changé ou n'a pas été accepté : confirme le nouveau devis.")
            except RefusAccord as e:
                raise HTTPException(409, {"message": _traduire(str(e), request), "usd": usd}) from None
        await R._plafond(DT.op_cout(mid, images=1), CATEGORIE)
    travail = source
    if mid != DEFAUT:
        with tempfile.TemporaryDirectory(prefix="dzschema_") as d:
            src = Path(d) / "source.png"
            await asyncio.to_thread(lambda: Image.open(io.BytesIO(source)).save(src, format="PNG"))
            try:
                nom = await DT.detourer_image(mid, src, None, dossier=d)
            except RuntimeError as e:
                logger.warning(f"schema_routes : détourage {mid} sans image ({type(e).__name__})")
                raise HTTPException(502, "Le détourage n'a rien rendu : réessaie ou choisis un autre modèle.") from None
            travail = (Path(d) / nom).read_bytes()
    lg = "en" if langue == "en" else "fr"
    avert = []
    try:
        ocr = await asyncio.to_thread(O.lire_page, source, lg)
        lignes = ocr.get("lignes") or []
    except (O.ScanIndisponible, O.ScanErreur, ValueError):
        lignes = []
        avert.append("ocr_indisponible")

    def _analyse():
        im = Image.open(io.BytesIO(travail))
        im.load()
        with Image.open(io.BytesIO(source)) as so:
            fx, fy = im.width / so.width, im.height / so.height
        return SC.analyser(im, _lignes_ramenees(lignes, fx, fy), langue=lg)
    try:
        r = await asyncio.to_thread(_analyse)
    except SC.RefusSchema as e:
        if e.code == "fond_non_uni":
            raise HTTPException(422, "Le fond de l'image n'est pas uni : choisis un détourage par IA, ou dépose une "
                                     "image déjà détourée (PNG transparent).") from None
        raise HTTPException(422, "L'image est vide : rien à séparer.") from None
    for e in r["elements"]:
        if "png" in e:
            e["png"] = "data:image/png;base64," + base64.b64encode(e.pop("png")).decode("ascii")
    r["avertissements"] = avert + r["avertissements"]
    ms = int((time.perf_counter() - t0) * 1000)
    compte = {}
    for e in r["elements"]:
        compte[e["nature"]] = compte.get(e["nature"], 0) + 1
    logger.info(f"schema_routes : {r['largeur']}x{r['hauteur']} px, détourage {mid}, {compte}, "
                f"{len(r['liens'])} lien(s), {usd:.4f} USD, {ms} ms")
    return {**r, "detourage": mid, "usd": usd, "duree_ms": ms}


# ------------------------------------------------------------------------------------------------- animation
async def _corps(request: Request) -> dict:
    morceaux, total = [], 0
    async for m in request.stream():
        total += len(m)
        if total > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(m)
    try:
        c = json.loads(b"".join(morceaux) or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    if not isinstance(c, dict):
        raise HTTPException(400, "Corps JSON attendu.")
    return c


def _nb(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _point(v):
    return {"x": float(v["x"]), "y": float(v["y"])} if isinstance(v, dict) and _nb(v.get("x")) and _nb(v.get("y")) \
        else None


@router.post("/animation", dependencies=[Depends(_local)])
async def animation(request: Request):
    from app.api import routes as R
    from app.config import settings
    from app.i18n import langue_requete
    from app.services import motion_code as MC
    from app.services import schema_animation as SA
    from PIL import Image
    c = await _corps(request)
    did = str(c.get("doc_id") or "")
    if not _ID_DOC.match(did):
        raise HTTPException(400, "Identifiant de document invalide.")
    lw, lh = c.get("largeur"), c.get("hauteur")
    if not (_nb(lw) and _nb(lh) and 1 <= lw <= 20000 and 1 <= lh <= 20000):
        raise HTTPException(400, "Taille du document invalide.")
    brut = c.get("calques")
    if not isinstance(brut, list) or not 1 <= len(brut) <= MAX_CALQUES:
        raise HTTPException(400, "Il faut de 1 à 60 calques à animer.")
    racine = settings.images_path
    calques = []
    for n, k in enumerate(brut, 1):
        k = k if isinstance(k, dict) else {}
        im = str(k.get("image") or "")
        b = k.get("boite") if isinstance(k.get("boite"), dict) else {}
        if not _FICHIER.match(im) or not (racine / im).is_file():
            raise HTTPException(400, f"Calque {n} : image « {im[:80]} » absente de la Bibliothèque.")
        if not all(_nb(b.get(x)) for x in ("x", "y", "w", "h")) or b["w"] <= 0 or b["h"] <= 0:
            raise HTTPException(400, f"Calque {n} : boîte invalide.")
        octets = (racine / im).read_bytes()
        try:
            with Image.open(io.BytesIO(octets)) as p:
                pw, ph = p.size
        except Exception:  # noqa: BLE001
            raise HTTPException(400, f"Calque {n} : image « {im[:80]} » illisible.") from None
        nat = k.get("nature") if k.get("nature") in ("forme", "fleche", "etiquette", "details") else "forme"
        calques.append({"image": im, "nom": str(k.get("nom") or "")[:120], "nature": nat,
                        "boite": {x: float(b[x]) for x in ("x", "y", "w", "h")}, "largeur_png": pw,
                        "hauteur_png": ph, "queue": _point(k.get("queue")), "pointe": _point(k.get("pointe")),
                        "octets": octets})
    nom = str(c.get("nom") or "").strip()[:100] or "Schéma"
    fond = SA.couleur(c.get("fond"))
    aspect = SA.aspect_pour(lw, lh)
    duree = SA.duree_pour(len(calques))
    script = str(c.get("script") or "").strip()[:6000] or "\n".join(k["nom"] for k in calques if k["nom"])
    nom_fond = f"vector_{did}_fond.png"
    (racine / nom_fond).write_bytes(SA.png_fond(aspect, fond))
    els = [SA.element_fond(nom_fond, duree)] + SA.elements(calques, lw, lh, aspect, duree)
    page = SA.page(calques, lw, lh, aspect, duree, fond=fond)
    if MC.controler(page):
        raise HTTPException(413, "La page motion code du schéma dépasse 10 Mo : anime moins de calques à la fois.")
    pid = MC.enregistrer(page)
    graphe = SA.graphe(nom, els, pid, script, aspect, duree)
    gid = "g_schema_" + hashlib.sha256(did.encode("utf-8")).hexdigest()[:8]
    graphe["id"] = gid
    titre = nom + (" — animated diagram" if langue_requete(request) == "en" else " — schéma animé")
    from datetime import datetime
    rec = {"id": gid, "name": titre[:120], "graph": graphe, "updated_at": datetime.utcnow().isoformat()}
    (R._studio_graphs_dir() / f"{gid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    logger.info(f"schema_routes : animation de {len(calques)} calque(s), {aspect}, {duree} s, page {len(page)} car.")
    return {"graph": graphe, "graph_id": gid, "page_id": pid, "aspect": aspect, "duree_s": duree}
