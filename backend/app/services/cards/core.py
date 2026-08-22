# -*- coding: utf-8 -*-
"""Card Forge — CORE : le magasin de decks et les routes du noyau.

Ce fichier appartient à CORE. Les huit pièces ne le touchent jamais ; elles
lisent `contract.py` et écrivent leur propre `<id>.py`.

Stockage — `outputs/decks/deck_xxxxxxxx/meta.json`, voisin de materials/,
sprites/ et assets3d/. AUCUNE table SQL : ni les matières ni les sprites n'en
ont, et un deck n'est pas plus relationnel qu'une matière. `meta.json` est
écrit ATOMIQUEMENT (tmp + `.replace()`) — l'autosave de l'écran tape toutes
les 900 ms, une écriture interrompue laisserait un document tronqué que la
prochaine ouverture lirait comme un deck vide.

Le document est PARTITIONNÉ (spec 2.3) : un sous-arbre par pièce, plus les
clés de CORE. `normalize_deck` ne lève jamais — un `meta.json` abîmé se
répare au lieu de faire tomber l'appelant, exactement comme
`material_store.read_material`.

Routes (montées sous `/api/cards` par `app/main.py`) :

    GET    /formats          catalogue des 12 formats + 3 planches + DPI
    GET    /decks            liste, plus récent d'abord
    POST   /decks            création (corps `{model}` = instanciation)
    POST   /decks/{did}/duplicate   copie complète, dossier compris
    GET    /{did}            document complet
    PATCH  /{did}            autosave (fusion partielle) — spec 2.2 §10
    DELETE /{did}            suppression
    GET    /{did}/geom       géométrie du deck, calculée par `contract.geom`

L'ORDRE DE DÉCLARATION COMPTE : Starlette apparie dans l'ordre. `/formats` et
`/decks` sont déclarés AVANT `/{did}`, sinon ils tomberaient dedans et
répondraient « identifiant de deck invalide ».
"""
from __future__ import annotations

import asyncio
import json
import math
import shutil
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from loguru import logger

from .contract import (
    BLEED_IMPERIAL_MM, BLEED_METRIC_MM, BLEED_MM_MAX, CORNER_MM_MAX,
    CardGeom, DEFAULT_CORNER_MM, DEFAULT_DPI, DEFAULT_FMT, DPI_CHOICES,
    DPI_MAX, DPI_MIN, FORMATS, MODULE_IDS, RULE_TEXT, SAFE_MM_MAX, SHEETS,
    deck_dir, decks_root, format_table, geom, is_valid_did, native_bleed_mm,
    sheet_px,
)

router = APIRouter()

DOC_VERSION = 1
NAME_MAX = 120


# ── document ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_did() -> str:
    root = decks_root()
    for _ in range(64):
        did = "deck_" + uuid4().hex[:8]
        if not (root / did).exists():
            return did
    raise RuntimeError("Impossible d'allouer un identifiant de deck")


def clean_name(raw, fallback: str = "Mon jeu") -> str:
    """Nom lisible, jamais vide, jamais un roman. Ne lève pas."""
    s = str(raw or "").strip()
    if not s:
        return fallback
    return s[:NAME_MAX]


def default_format() -> dict:
    return {"fmt": DEFAULT_FMT, "dpi": DEFAULT_DPI,
            "bleed_mm": native_bleed_mm(DEFAULT_FMT),
            "safe_mm": native_bleed_mm(DEFAULT_FMT),
            "corner_mm": DEFAULT_CORNER_MM}


def normalize_format(raw, base: dict | None = None) -> dict:
    """Bloc `format` réparé, jamais une exception. Une valeur illisible
    reprend son défaut plutôt que de rendre le deck inouvrable.

    `base` est l'état ACTUEL du bloc — c'est ce qui rend le PATCH réellement
    PARTIEL. Sans lui, `PATCH {"format":{"dpi":600}}` sur un deck `tarot_us`
    repartait de `default_format()` et rendait le deck à `poker_eu` SANS UN
    MOT : la carte changeait de taille (1630x2220 au lieu de 1800x3000) sur
    un réglage de définition. Une clé absente du corps veut dire « ne touche
    pas », jamais « reprends le défaut d'usine ».

    Le changement de `fmt` reprend le fond perdu NATIF du nouveau format
    (0.125 in en impérial, 3 mm en métrique) — même règle que
    `setFormatInternal` côté écran et que l'aperçu de `/geom` — sauf si le
    corps fixe explicitement `bleed_mm` / `safe_mm`.
    """
    raw = raw if isinstance(raw, dict) else {}
    out = default_format()
    if isinstance(base, dict):
        for k in out:
            if k in base:
                out[k] = base[k]
    fmt = str(raw.get("fmt") or "").strip().lower()
    if fmt in FORMATS and fmt != out["fmt"]:
        out["fmt"] = fmt
        out["bleed_mm"] = native_bleed_mm(fmt)
        out["safe_mm"] = native_bleed_mm(fmt)
    elif fmt in FORMATS:
        out["fmt"] = fmt
    if "dpi" in raw:
        try:
            dpi = int(raw.get("dpi"))
            if DPI_MIN <= dpi <= DPI_MAX:
                out["dpi"] = dpi
        except (TypeError, ValueError, OverflowError):
            # OverflowError : json.loads("1e999") rend float('inf') et
            # int(inf) lève — c'était un 500 sur un simple corps mal formé.
            pass
    for key, hi in (("bleed_mm", BLEED_MM_MAX), ("safe_mm", SAFE_MM_MAX),
                    ("corner_mm", CORNER_MM_MAX)):
        if key not in raw:
            continue
        try:
            v = float(raw.get(key))
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(v) and 0.0 <= v <= hi:
            out[key] = v
    return out


def default_doc(did: str, name: str = "Mon jeu") -> dict:
    """Le document neuf, partitionné (spec 2.3). Chaque pièce reçoit son
    sous-arbre VIDE : c'est elle qui décide de son contenu, CORE ne préjuge
    de rien."""
    doc = {"v": DOC_VERSION, "id": did, "name": clean_name(name),
           "format": default_format(),
           "created": _now_iso(), "updated": _now_iso()}
    for mid in MODULE_IDS:
        doc[mid] = {}
    return doc


def normalize_deck(raw: dict | None, did: str | None = None) -> dict:
    """Document complet à partir de n'importe quoi (meta.json abîmé, corps
    client partiel…). NE LÈVE JAMAIS.

    Le PARTITIONNEMENT est appliqué ici, et c'est le seul endroit : une clé
    qui n'est ni une clé de CORE ni l'un des huit ids est jetée. Sans cela,
    un client (ou un module distrait) pourrait faire pousser le document
    n'importe où et deux pièces finiraient par se marcher dessus."""
    raw = raw if isinstance(raw, dict) else {}
    did = did or raw.get("id")
    doc = default_doc(did if is_valid_did(did) else "deck_00000000",
                      raw.get("name"))
    doc["format"] = normalize_format(raw.get("format"))
    created = raw.get("created")
    if isinstance(created, str) and created:
        doc["created"] = created
    updated = raw.get("updated")
    if isinstance(updated, str) and updated:
        doc["updated"] = updated
    for mid in MODULE_IDS:
        sub = raw.get(mid)
        doc[mid] = sub if isinstance(sub, dict) else {}
    return doc


def geom_of(doc: dict) -> CardGeom:
    """Géométrie du deck. Le bloc `format` est déjà normalisé par
    `normalize_deck`, donc cet appel ne peut pas lever."""
    f = normalize_format((doc or {}).get("format"))
    return geom(f["fmt"], f["dpi"], f["bleed_mm"], f["safe_mm"], f["corner_mm"])


# ── magasin sur disque ──────────────────────────────────────────────────────

def write_deck(doc: dict) -> dict:
    """Écrit meta.json ATOMIQUEMENT (tmp + replace)."""
    did = doc.get("id")
    d = deck_dir(did, create=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(d / "meta.json")
    return doc


def create_deck(name: str = "Mon jeu", fmt: dict | None = None,
                did: str | None = None) -> dict:
    did = did or new_did()
    deck_dir(did, create=True)
    doc = default_doc(did, name)
    if fmt is not None:
        doc["format"] = normalize_format(fmt)
    return write_deck(doc)


def read_deck(did: str) -> dict | None:
    """Document, ou None si le dossier/meta est absent. Un meta.json corrompu
    est normalisé plutôt que de faire tomber l'appelant."""
    try:
        d = deck_dir(did)
    except ValueError:
        return None
    f = d / "meta.json"
    if not f.is_file():
        return None
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning(f"cards: meta.json illisible pour {did}: {e}")
        raw = {}
    return normalize_deck(raw, did)


def list_decks() -> list[dict]:
    """Tous les decks, plus récent d'abord. `updated` n'a qu'une précision
    d'une seconde : le mtime de meta.json départage."""
    rows = []
    for d in decks_root().iterdir():
        if not d.is_dir() or not is_valid_did(d.name):
            continue
        doc = read_deck(d.name)
        if not doc:
            continue
        try:
            mtime = (d / "meta.json").stat().st_mtime
        except OSError:
            mtime = 0.0
        rows.append((doc.get("updated") or "", mtime, doc))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return [r[2] for r in rows]


def patch_deck(did: str, body: dict | None) -> dict | None:
    """Fusion PARTIELLE du document (autosave). None si le deck n'existe pas.

    `id`, `v` et `created` ne sont jamais repris du client.

    PARTIELLE veut dire : une clé ABSENTE du corps n'est pas touchée. Ni le
    bloc `format` (fusionné sur l'état actuel, cf. `normalize_format`), ni un
    sous-arbre de pièce. C'est ce qui rend deux onglets — ou deux des huit
    builders — inoffensifs l'un pour l'autre : l'écran n'envoie que ce qu'il a
    modifié (`saveBody`, core.js), et ce qu'il n'envoie pas survit.

    En revanche un sous-arbre PRÉSENT et bien formé est remplacé EN BLOC, pas
    fusionné : c'est `CF.patch` qui fusionne côté navigateur, et le sous-arbre
    envoyé ici est déjà son état complet. Fusionner une seconde fois ici
    rendrait la suppression d'une clé impossible.

    Un sous-arbre présent mais MAL FORMÉ (`null`, une liste, une chaîne) est
    IGNORÉ, pas appliqué : le vider effacerait le travail d'une pièce sur une
    faute de frappe d'un client. Pour vider `doc.face`, on envoie `{}`.
    """
    doc = read_deck(did)
    if doc is None:
        return None
    body = body if isinstance(body, dict) else {}
    if "name" in body:
        doc["name"] = clean_name(body.get("name"), fallback=doc["name"])
    if "format" in body:
        doc["format"] = normalize_format(body.get("format"), base=doc["format"])
    for mid in MODULE_IDS:
        if mid in body and isinstance(body.get(mid), dict):
            doc[mid] = body[mid]
    doc["updated"] = _now_iso()
    return write_deck(doc)


def duplicate_deck(did: str) -> dict | None:
    """Copie COMPLÈTE d'un deck : le document ET le dossier (spec §6.4).

    Une duplication copie TOUT, illustrations comprises — c'est
    « enregistrer comme modèle » qui les exclut. Le dossier d'un deck porte
    bien plus que `meta.json` : `texture/`, `solid/`, `gltf/`, `forge3d/`, le
    profil ICC de P7… Copier le seul document aurait rendu un deck qui
    S'OUVRE et dont la moitié des aperçus manquent, sans un message.

    `copytree` refuse une destination existante, et `new_did` ne rend qu'un
    identifiant libre : la copie ne peut pas écraser un voisin.
    """
    doc = read_deck(did)
    if doc is None:
        return None
    src = deck_dir(did)
    neuf = new_did()
    shutil.copytree(src, deck_dir(neuf))
    doc["id"] = neuf
    doc["name"] = clean_name(f"copie de {doc['name']}")
    doc["created"] = doc["updated"] = _now_iso()
    return write_deck(doc)


def delete_deck(did: str) -> bool:
    try:
        d = deck_dir(did)
    except ValueError:
        return False
    if not d.is_dir():
        return False
    shutil.rmtree(d, ignore_errors=True)
    return not d.exists()


def _deck_or_404(did: str) -> dict:
    """Deck existant, ou l'erreur qui va bien. `did` hors
    ^deck_[0-9a-f]{8}$ = 400 (aucune traversée ne peut aller plus loin)."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


# ── routes ──────────────────────────────────────────────────────────────────
# /formats et /decks D'ABORD : Starlette apparie dans l'ordre de déclaration.

@router.get("/formats")
async def list_formats():
    """Le catalogue de géométrie, calculé — jamais une table recopiée à la
    main dans l'écran.

    C'est la moitié mesurable du domaine : `poker_us` doit sortir à
    825x1125 px de toile et 750x1050 px de rogne, comme nanDECK, avec un
    trait de coupe à 37,5 px. L'écran affiche ces chiffres tels quels ; il
    n'en recalcule aucun."""
    return {
        "formats": format_table(DEFAULT_DPI),
        "sheets": [
            {"id": sid, "label": SHEETS[sid]["label"],
             "size_mm": [round(v, 3) for v in SHEETS[sid]["size_mm"]],
             "px": {str(d): list(sheet_px(sid, d)) for d in DPI_CHOICES}}
            for sid in SHEETS
        ],
        "dpis": list(DPI_CHOICES),
        "dpi_default": DEFAULT_DPI,
        "fmt_default": DEFAULT_FMT,
        # LES CONSTANTES, pas leurs valeurs recopiées : une route dont le
        # docstring dit « calculé, jamais une table à la main » ne peut pas
        # servir 3.175 en littéral. Changer la constante changeait l'API et
        # laissait ce bloc mentir, sans qu'aucun test bronche.
        "bleed": {"metric_mm": BLEED_METRIC_MM,
                  "imperial_mm": BLEED_IMPERIAL_MM,
                  "max_mm": BLEED_MM_MAX},
        "limits": {"dpi": [DPI_MIN, DPI_MAX], "bleed_mm": [0.0, BLEED_MM_MAX],
                   "safe_mm": [0.0, SAFE_MM_MAX],
                   "corner_mm": [0.0, CORNER_MM_MAX]},
        "rule": RULE_TEXT,
    }


@router.get("/decks")
async def get_decks():
    """Tous les decks, plus récent d'abord."""
    return {"decks": await asyncio.to_thread(list_decks)}


@router.post("/decks")
async def post_deck(body: dict | None = None):
    """Crée un deck. Corps {name?, format?, model?} — tout est facultatif.

    `model` INSTANCIE un modèle (spec §6.1) : le deck naît habillé, typographié
    et matiéré, puis il est ORDINAIRE — aucune référence au modèle n'est
    gardée. L'import de `models` est TARDIF, et c'est nécessaire : `models.py`
    importe CE fichier (il a besoin du magasin de decks), et `cards/__init__`
    charge `core` en premier. Un import en tête de module ferait un cycle.
    """
    body = body if isinstance(body, dict) else {}
    modele = body.get("model")
    if modele not in (None, ""):
        from .models import instancier
        try:
            doc = await asyncio.to_thread(instancier, modele, body.get("name"))
        except KeyError:
            raise HTTPException(
                404, f"Modèle inconnu : « {modele} » — la liste est servie "
                     "par GET /api/cards/models")
        except ValueError as e:
            raise HTTPException(400, f"Modèle illisible : {e}")
        except OSError as e:
            logger.exception("cards: instanciation de modèle impossible")
            raise HTTPException(500, f"Création du deck impossible: {e}")
        return {"deck": doc}
    try:
        doc = await asyncio.to_thread(create_deck, body.get("name") or "Mon jeu",
                                      body.get("format"))
    except OSError as e:
        logger.exception("cards: création de deck impossible")
        raise HTTPException(500, f"Création du deck impossible: {e}")
    return {"deck": doc}


@router.post("/decks/{did}/duplicate")
async def duplicate_deck_route(did: str):
    """Duplique un deck, dossier compris (spec §6.4). Trois segments : aucune
    chance de tomber dans le joker `/{did}`, qui n'en apparie qu'un."""
    _deck_or_404(did)
    try:
        doc = await asyncio.to_thread(duplicate_deck, did)
    except OSError as e:
        logger.exception("cards: duplication impossible")
        raise HTTPException(500, f"Duplication du deck impossible: {e}")
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return {"deck": doc}


@router.get("/{did}")
async def get_deck(did: str):
    return {"deck": _deck_or_404(did)}


@router.patch("/{did}")
async def patch_deck_route(did: str, body: dict | None = None):
    """Autosave de l'écran (spec 2.2 §10). Fusion partielle de
    {name?, format?, face?, frame?, type?, data?, solid?, texture?, print?,
    gltf?}. Toute clé étrangère est ignorée, toute valeur invalide reprend
    son défaut — jamais d'erreur 500."""
    _deck_or_404(did)
    doc = await asyncio.to_thread(patch_deck, did, body)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return {"deck": doc}


@router.delete("/{did}")
async def delete_deck_route(did: str):
    _deck_or_404(did)
    ok = await asyncio.to_thread(delete_deck, did)
    if not ok:
        raise HTTPException(409, "Le deck n'a pas pu être supprimé")
    return {"ok": True}


def _q_num(val, what: str) -> float | None:
    """Nombre venant de la CHAÎNE DE REQUÊTE. Les paramètres sont déclarés en
    `str` exprès : typés `int`/`float`, FastAPI rendait un 422 avec une charge
    pydantic EN ANGLAIS là où la spec 2.5 impose 400 + une phrase en
    français — et ce lab est francophone de bout en bout."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, f"{what} doit être un nombre (reçu {val!r})")
    if not math.isfinite(f):
        raise HTTPException(400, f"{what} doit être un nombre fini (reçu {val!r})")
    return f


@router.get("/{did}/geom")
async def get_deck_geom(did: str, fmt: str | None = None,
                        dpi: str | None = None,
                        bleed_mm: str | None = None,
                        safe_mm: str | None = None,
                        corner_mm: str | None = None):
    """Géométrie du deck — LA vérité, celle que l'écran affiche et que
    l'export applique. Les paramètres facultatifs simulent un changement de
    format sans l'enregistrer (aperçu du sélecteur)."""
    d_num = _q_num(dpi, "Le DPI")
    dpi = None if d_num is None else int(d_num)
    bleed_mm = _q_num(bleed_mm, "Le fond perdu")
    safe_mm = _q_num(safe_mm, "La zone de sécurité")
    corner_mm = _q_num(corner_mm, "Le rayon de coin")
    doc = _deck_or_404(did)
    f = dict(doc["format"])
    demande = str(fmt).strip().lower() if fmt is not None else None
    if demande and demande != f["fmt"]:
        # CHANGER DE FORMAT REPREND SON FOND PERDU NATIF : 0.125 in en
        # impérial, 3 mm en métrique. Sans cette reprise, prévisualiser
        # `poker_us` depuis un deck `poker_eu` garderait 3 mm et sortirait
        # 821x1121 au lieu de 825x1125 — la parité nanDECK tomberait sur un
        # simple aperçu. Un `bleed_mm`/`safe_mm` passé EXPLICITEMENT reste
        # prioritaire : il est appliqué juste après.
        try:
            f["bleed_mm"] = f["safe_mm"] = native_bleed_mm(demande)
        except KeyError:
            pass          # format inconnu : geom() lèvera, avec son message
    for key, val in (("fmt", demande), ("dpi", dpi), ("bleed_mm", bleed_mm),
                     ("safe_mm", safe_mm), ("corner_mm", corner_mm)):
        if val is not None:
            f[key] = val
    try:
        g = geom(f["fmt"], f["dpi"], f["bleed_mm"], f["safe_mm"], f["corner_mm"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"geom": g.to_dict()}
