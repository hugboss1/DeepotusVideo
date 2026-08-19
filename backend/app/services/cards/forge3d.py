# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Backend, phase 1 : export par couches.

Monté par `cards/__init__.py` sous `/api/cards/{did}/forge3d`. Chemins RELATIFS.
CE FICHIER APPARTIENT À P9 (règle 8) : aucun autre module ne l'importe, il
n'importe le routeur d'aucun autre.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import struct
import time
import zipfile
import zlib
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

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


def _phys_chunk(ppm_x: int, ppm_y: int) -> bytes:
    data = struct.pack(">IIB", ppm_x, ppm_y, 1)
    return (struct.pack(">I", len(data)) + b"pHYs" + data
            + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xFFFFFFFF))


def _stamp_phys(png: bytes, ppm: tuple[float, float]) -> bytes:
    """Insère un pHYs après l'IHDR — même densité que l'écran (patron P1/P8),
    relue dans les octets par les tests. Un PNG déjà estampillé est réécrit."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu")
    ihdr_end = 8 + 8 + struct.unpack(">I", png[8:12])[0] + 4
    out, off = [png[:ihdr_end]], ihdr_end
    out.append(_phys_chunk(int(round(ppm[0])), int(round(ppm[1]))))
    while off < len(png):
        ln = struct.unpack(">I", png[off:off + 4])[0]
        typ = png[off + 4:off + 8]
        if typ != b"pHYs":
            out.append(png[off:off + 8 + ln + 4])
        off += 8 + ln + 4
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
    écrit LES DEUX mesures dans le manifeste."""
    try:
        from PIL import Image
    except Exception as e:                     # pragma: no cover - env casse
        raise HTTPException(503, f"PIL indisponible : {e}")

    def _ouvre(raw: bytes, nom: str):
        """Un corps mal formé fait 400, JAMAIS 500 (spec 2.5). `Image.open`
        lève sur tout ce qui n'EST pas un format qu'il reconnaît — capturé
        ici, sinon c'est le 500 non attrapé qu'une trame de bruit produisait
        avant ce correctif (mesuré : le layer ET le composite y sont exposés
        de la même façon, donc les deux passent par ce même garde)."""
        try:
            return Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception as e:
            raise HTTPException(400, f"{nom} : PNG illisible ({e})")

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
    try:
        modes_d = json.loads(modes or "{}")
        proof_c = json.loads(client_proof or "{}")
    except ValueError:
        modes_d, proof_c = {}, {}

    par_role: dict[str, bytes] = {}
    images: dict[str, "Image.Image"] = {}
    for up in layers:
        nom = (up.filename or "").rsplit(".", 1)[0]
        raw = await up.read()
        im = _ouvre(raw, nom)
        if im.size != (w, h):
            raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
        par_role[nom], images[nom] = raw, im
    raw_comp = await composite.read()
    comp = _ouvre(raw_comp, "composite")
    if comp.size != (w, h):
        raise HTTPException(409, f"composite : trame {comp.size} != {(w, h)}")

    ordre = [r["role"] for r in LAYER_ROLES if r["role"] in par_role]
    if not ordre:
        raise HTTPException(409, "aucune couche reconnue")

    # ── contre-preuve : empilement PIL, ecart MESURE au composite ───────────
    pile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for nom in ordre:
        pile = Image.alpha_composite(pile, images[nom])
    from PIL import ImageChops
    diff = ImageChops.difference(pile, comp)
    diff_px = sum(1 for p in diff.getdata() if p != (0, 0, 0, 0))

    # Densité pHYs : voir _dpi_to_ppm — copie locale, même densité que P1.
    ppm = float(_dpi_to_ppm(g.dpi))
    out = _out_dir(did, create=True)
    rows = []
    for nom in ordre:
        data = _stamp_phys(par_role[nom], (ppm, ppm))
        fn = f"{nom}_{face}.png"
        (out / fn).write_bytes(data)
        alpha = images[nom].getchannel("A")
        bbox = alpha.getbbox()
        cover = (sum(1 for a in alpha.getdata() if a) / float(w * h) * 100.0)
        meta = next(r for r in LAYER_ROLES if r["role"] == nom)
        rows.append({
            "role": nom, "z": meta["z"], "module": meta["module"], "file": fn,
            "mode": str(modes_d.get(nom, "isolee")),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "bbox_px": list(bbox) if bbox else None,
            "coverage_pct": round(cover, 2),
        })
    comp_fn = f"composite_{face}.png"
    comp_data = _stamp_phys(raw_comp, (ppm, ppm))
    (out / comp_fn).write_bytes(comp_data)

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
                       "diff_px": int(proof_c.get("diff_px") or 0),
                       "note": "empilement navigateur, meme moteur, strict"},
            "backend": {"diff_px": int(diff_px),
                        "note": "re-empilement PIL alpha-over, second avis"},
        },
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            z.writestr(r["file"], (out / r["file"]).read_bytes())
        z.writestr(comp_fn, comp_data)
        z.writestr("layers.json", json.dumps(manifest, ensure_ascii=False,
                                             indent=2))
    zname = f"couches_{face}.zip"
    (out / zname).write_bytes(zbuf.getvalue())
    manifest["zip"] = {"name": zname, "bytes": len(zbuf.getvalue())}
    (out / f"layers_{face}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"layers": manifest}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit (patron P8)."""
    import re as _re
    if not _re.match(r"^[A-Za-z0-9._-]{1,90}$", name or ""):
        raise HTTPException(400, "Nom invalide")
    p = _out_dir(did) / name
    if not p.is_file():
        raise HTTPException(404, "Fichier inconnu")
    kind = "application/zip" if name.endswith(".zip") else \
        "image/png" if name.endswith(".png") else "application/json"
    return Response(p.read_bytes(), media_type=kind)
