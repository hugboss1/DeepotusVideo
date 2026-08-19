# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Backend, phase 1 : export par couches.

Monté par `cards/__init__.py` sous `/api/cards/{did}/forge3d`. Chemins RELATIFS.
CE FICHIER APPARTIENT À P9 (règle 8) : aucun autre module ne l'importe, il
n'importe le routeur d'aucun autre.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import struct
import time
import zipfile
import zlib
from functools import reduce
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from .contract import deck_dir

router = APIRouter()

MANIFEST_SCHEMA = "card-3d/layers-manifest@1"

# ── LA TABLE DES COUCHES — BLOC MIROIR ──────────────────────────────────────
# ═══ CF-FORGE3D-LAYERS-BEGIN ═══
# Le miroir JS est dans frontend/cardforge/js/mod-forge3d.js, entre les mêmes
# marqueurs ; test_cards_forge3d compare les deux champ à champ et dans l'ordre.
# Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82).
LAYER_ROLES = [
    {"role": "fond-matiere", "z": [10], "module": "texture"},
    {"role": "illustration", "z": [20], "module": "face"},
    {"role": "voile-matiere", "z": [30], "module": "texture"},
    {"role": "cadre", "z": [40], "module": "frame"},
    {"role": "typographie", "z": [60], "module": "type"},
    {"role": "ornements", "z": [70], "module": "frame"},
]
# ═══ CF-FORGE3D-LAYERS-END ═══

# ── bornes d'entrée — vérifiées AVANT tout décodage (spec 2.5) ──────────────
MAX_LAYER_BYTES = 64 * 1024 * 1024   # un PNG de carte, pas un film — même
                                      # chiffre que le précédent du domaine,
                                      # gltf.py:MAX_ATLAS_BYTES (copie, règle 8)
MAX_LAYER_FILES = 12                 # 6 rôles connus ; marge x2 avant qu'un
                                      # gros lot ne soit décodé pour rien
LAYER_MODES = {"isolee", "empreinte"}  # vocabulaire FERMÉ du CORE (core.js) ;
                                        # un autre mot est un bug à révéler,
                                        # pas une valeur à archiver


@router.get("/info")
async def get_info(did: str):
    """Ce que l'écran doit savoir sans rien recalculer."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    return {"schema": MANIFEST_SCHEMA, "layer_roles": LAYER_ROLES}


def _out_dir(did: str, create: bool = False) -> Path:
    d = deck_dir(did) / "forge3d"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _dpi_to_ppm(dpi: float) -> int:
    """DPI -> pixels par mètre, arrondi demi-haut. 300 -> 11811, 600 -> 23622.

    COPIE LOCALE de la formule de `face.py:dpi_to_ppm` — le domaine impose
    ZÉRO import pièce->pièce (règle 8) : c'est déjà le patron établi par
    `frame.py:dpi_to_ppm` et `print.py:phys_ppm`, chacune sa propre copie,
    chacune sa parité testée contre P1. Le pHYs de cette pièce DOIT porter la
    même densité que celui de P1 pour la même carte : recalculer `ppm` depuis
    `canvas_px / (trim_mm + 2*bleed_mm)` (comme le proposait le plan) dérive
    de l'arrondi ENTIER de `canvas_px` — mesuré jusqu'à 9 px/m d'écart sur
    poker_eu/tarot_eu/mini/square_eu, et une densité X != Y sur plusieurs
    formats. La seule source qui ne dérive jamais est le DPI nominal lui-même."""
    d = float(dpi)
    return int(math.floor(d / 0.0254 + 0.5))


def _num(raw, default: float, lo: float, hi: float) -> float:
    """Garde numérique — COPIE LOCALE de `gltf.py:_num` (même règle 8 que
    `_dpi_to_ppm` ci-dessus : zéro import pièce->pièce). Toute entrée qui
    n'est pas un nombre fini retombe sur `default`, jamais une exception :
    c'est ce qui manquait à `int(proof_c.get("diff_px") or 0)`, où une liste
    ou un dict levait un `TypeError` non attrapé — 500 reproduit en revue."""
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(lo if v < lo else hi if v > hi else v)


def _phys_chunk(ppm_x: int, ppm_y: int) -> bytes:
    data = struct.pack(">IIB", ppm_x, ppm_y, 1)
    return (struct.pack(">I", len(data)) + b"pHYs" + data
            + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xFFFFFFFF))


def _stamp_phys(png: bytes, ppm: tuple[float, float]) -> bytes:
    """Insère un pHYs après l'IHDR — même densité que l'écran (patron P1/P8),
    relue dans les octets par les tests. Un PNG déjà estampillé est réécrit.

    La boucle est BORNÉE et s'arrête à IEND : un PNG à queue parasite (des
    octets après IEND — navigateurs et outils en écrivent bel et bien) passe
    le décodage PIL sans broncher, mais faisait planter `struct.unpack` sur
    un fragment de moins de 4 octets — 500 non attrapé, reproduit en revue."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu")
    ihdr_end = 8 + 8 + struct.unpack(">I", png[8:12])[0] + 4
    out, off = [png[:ihdr_end]], ihdr_end
    out.append(_phys_chunk(int(round(ppm[0])), int(round(ppm[1]))))
    while off + 8 <= len(png):
        ln = struct.unpack(">I", png[off:off + 4])[0]
        typ = png[off + 4:off + 8]
        end = off + 8 + ln + 4
        if end > len(png):
            break
        if typ != b"pHYs":
            out.append(png[off:end])
        off = end
        if typ == b"IEND":
            break
    return b"".join(out)


@router.post("/layers")
async def post_layers(did: str,
                      layers: list[UploadFile] = File(...),
                      composite: UploadFile = File(...),
                      side: str = Form("front"),
                      modes: str = Form("{}"),
                      client_proof: str = Form("{}")):
    """N couches PNG alpha + composite -> contre-preuve PIL, estampille,
    ZIP + manifeste. Le navigateur a DÉJÀ prouvé l'empilement chez lui
    (même moteur, pixel strict) ; ici on ré-empile en second avis et on
    écrit LES DEUX mesures dans le manifeste.

    `await up.read()` reste async (c'est de l'E/S) ; tout le reste — décodage,
    empilement, mesures, estampilles, zip, écritures — est du calcul pur et
    tourne dans `work()`, déporté par `asyncio.to_thread` (patron des sœurs :
    gltf.py:post_build, gltf.py:post_atlas, print.py:post_card). Mesuré :
    l'inline gelait la boucle d'évènements de 0,45 s (poker 300 DPI) à plus
    de 2,6 s (tarot 600 DPI)."""
    from .core import read_deck, geom_of
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    g = geom_of(doc)
    w, h = g.canvas_px
    face = "back" if str(side).strip().lower() == "back" else "front"

    # ── bornes AVANT décodage : compte, puis rôle — aucune des deux ne lit
    #    un octet du corps du fichier ─────────────────────────────────────
    if len(layers) > MAX_LAYER_FILES:
        raise HTTPException(
            400, f"trop de couches ({len(layers)}, maximum {MAX_LAYER_FILES})")
    valid_roles = {r["role"] for r in LAYER_ROLES}
    noms: list[str] = []
    seen: set[str] = set()
    for up in layers:
        nom = (up.filename or "").rsplit(".", 1)[0]
        if nom not in valid_roles:
            raise HTTPException(400, f"{nom!r} : rôle de couche inconnu")
        if nom in seen:
            raise HTTPException(400, f"{nom!r} : couche envoyée deux fois")
        seen.add(nom)
        noms.append(nom)

    # ── modes / preuve client : JSON valide mais pas un objet -> réparé,
    #    jamais 500 (spec 2.5) ; le mode est validé contre le vocabulaire
    #    fermé du CORE ────────────────────────────────────────────────────
    try:
        modes_d = json.loads(modes or "{}")
    except ValueError:
        modes_d = {}
    if not isinstance(modes_d, dict):
        modes_d = {}
    for role, mode in modes_d.items():
        if str(mode) not in LAYER_MODES:
            raise HTTPException(
                400, f"mode inconnu pour {role!r} : {mode!r} "
                     f"(attendu {sorted(LAYER_MODES)})")
    try:
        proof_c = json.loads(client_proof or "{}")
    except ValueError:
        proof_c = {}
    if not isinstance(proof_c, dict):
        proof_c = {}

    # ── lecture des octets (E/S -> reste async), bornée AVANT tout décodage
    raw_par_role: dict[str, bytes] = {}
    for up, nom in zip(layers, noms):
        raw = await up.read()
        if len(raw) > MAX_LAYER_BYTES:
            raise HTTPException(
                413, f"{nom} : fichier trop lourd ({len(raw)} o, "
                     f"maximum {MAX_LAYER_BYTES} o)")
        raw_par_role[nom] = raw
    raw_comp = await composite.read()
    if len(raw_comp) > MAX_LAYER_BYTES:
        raise HTTPException(
            413, f"composite : fichier trop lourd ({len(raw_comp)} o, "
                 f"maximum {MAX_LAYER_BYTES} o)")

    def work() -> dict:
        from PIL import Image, ImageChops

        def _ouvre(raw: bytes, nom: str):
            """Un corps mal formé fait 400, JAMAIS 500 (spec 2.5). `format`
            est lu AVANT `convert()` : la conversion RGBA renvoie une image
            neuve dont `.format` vaut None — le vérifier après serait un
            contrôle qui ne contrôle rien."""
            try:
                im = Image.open(io.BytesIO(raw))
                im.load()
            except Exception as e:
                raise HTTPException(400, f"{nom} : PNG illisible ({e})")
            fmt = (im.format or "").upper()
            if fmt != "PNG":
                raise HTTPException(
                    400, f"{nom} : PNG attendu, {fmt or 'format inconnu'} reçu")
            return im.convert("RGBA")

        images: dict[str, "Image.Image"] = {}
        for nom, raw in raw_par_role.items():
            im = _ouvre(raw, nom)
            if im.size != (w, h):
                raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
            images[nom] = im
        comp = _ouvre(raw_comp, "composite")
        if comp.size != (w, h):
            raise HTTPException(409, f"composite : trame {comp.size} != {(w, h)}")

        ordre = [r["role"] for r in LAYER_ROLES if r["role"] in images]
        if not ordre:
            raise HTTPException(409, "aucune couche reconnue")

        # ── contre-preuve : empilement PIL, ecart MESURE au composite ──────
        pile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for nom in ordre:
            pile = Image.alpha_composite(pile, images[nom])
        diff = ImageChops.difference(pile, comp)
        # getdata() est déprécié (retrait Pillow 14) — équivalence mesurée
        # (scratchpad/bench_forge3d.py) : fast-path getbbox() si aucun écart,
        # sinon histogramme du canal fusionné (0 == pixels IDENTIQUES sur les
        # 4 bandes, donc w*h - ce compte = pixels qui diffèrent).
        if diff.getbbox() is None:
            diff_px = 0
        else:
            fusion = reduce(ImageChops.lighter, diff.split())
            diff_px = w * h - fusion.histogram()[0]

        ppm = float(_dpi_to_ppm(g.dpi))
        zip_entries: dict[str, bytes] = {}
        rows = []
        for nom in ordre:
            data = _stamp_phys(raw_par_role[nom], (ppm, ppm))
            fn = f"{nom}_{face}.png"
            zip_entries[fn] = data
            alpha = images[nom].getchannel("A")
            bbox = alpha.getbbox()
            # coverage : w*h - (pixels d'alpha nul), même mesure histogramme
            cover = ((w * h - alpha.histogram()[0]) / float(w * h) * 100.0)
            meta = next(r for r in LAYER_ROLES if r["role"] == nom)
            rows.append({
                "role": nom, "z": meta["z"], "module": meta["module"],
                "file": fn,
                "mode": str(modes_d.get(nom, "isolee")),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "bbox_px": list(bbox) if bbox else None,
                "coverage_pct": round(cover, 2),
            })
        comp_fn = f"composite_{face}.png"
        comp_data = _stamp_phys(raw_comp, (ppm, ppm))
        zip_entries[comp_fn] = comp_data

        manifest = {
            "schema": MANIFEST_SCHEMA,
            "deck": {"id": did, "name": doc.get("name")},
            "side": face,
            "canvas_px": [w, h],
            "size_mm": [g.trim_mm[0], g.trim_mm[1]],
            "bleed_mm": g.bleed_mm,
            "layers": rows,
            "composite": {"file": comp_fn,
                          "sha256": hashlib.sha256(comp_data).hexdigest(),
                          "bytes": len(comp_data)},
            "proof": {
                "client": {"stack_ok": bool(proof_c.get("stack_ok")),
                           "diff_px": int(_num(proof_c.get("diff_px"), 0,
                                               0, w * h)),
                           "note": "empilement navigateur, meme moteur, strict"},
                "backend": {"diff_px": int(diff_px),
                            "note": "re-empilement PIL alpha-over, second avis"},
            },
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # ── ZIP : octets EN MÉMOIRE, jamais de relecture disque ────────────
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            for fn, data in zip_entries.items():
                z.writestr(fn, data)
            z.writestr("layers.json", json.dumps(manifest, ensure_ascii=False,
                                                 indent=2))
        zname = f"couches_{face}.zip"
        zip_bytes = zbuf.getvalue()
        manifest["zip"] = {"name": zname, "bytes": len(zip_bytes)}

        out = _out_dir(did, create=True)
        for fn, data in zip_entries.items():
            (out / fn).write_bytes(data)
        (out / zname).write_bytes(zip_bytes)
        (out / f"layers_{face}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return manifest

    try:
        manifest = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except ModuleNotFoundError as e:           # pragma: no cover - env casse
        raise HTTPException(503, f"Module requis absent : {e}")
    except Exception as e:
        logger.exception("cards/forge3d: export de couches impossible")
        raise HTTPException(500, f"Export de couches impossible : {e}")
    return {"layers": manifest}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit (patron P8)."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    import re as _re
    if not _re.match(r"^[A-Za-z0-9._-]{1,90}$", name or ""):
        raise HTTPException(400, "Nom invalide")
    p = _out_dir(did) / name
    if not p.is_file():
        raise HTTPException(404, "Fichier inconnu")
    kind = "application/zip" if name.endswith(".zip") else \
        "image/png" if name.endswith(".png") else "application/json"
    return Response(p.read_bytes(), media_type=kind, headers={
        "Content-Disposition": f'attachment; filename="{p.name}"',
        "Cache-Control": "no-store"})
