"""Fiche de provenance d'un maillage — spec Magnific §9.2 étape 6.

« Exporter GLB, stocker checksum, faces, taille, textures et version. »

Tout est LOCAL et GRATUIT : on relit le GLB avec les lecteurs déjà éprouvés
du dépôt (`mesh_optimize.glb_stats` pour les compteurs, `print3d` pour les
triangles en coordonnées monde) et on ajoute ce qui manquait — sha256,
inventaire des textures, dimensions de la boîte englobante, arêtes de bord
(les « zones invisibles » de l'étape 3), et les **silhouettes** projetées
face/profil/dessus qui servent de mesure objective au contrôle qualité.

Doctrine §2.1 : on ne remplace jamais silencieusement. `report.json` est un
REGISTRE : chaque version du maillage y ajoute une entrée, la précédente
reste lisible.
"""
from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

# Au-delà, les passes O(triangles) en Python coûtent plus qu'elles
# n'apprennent : on le DIT dans la fiche au lieu de faire attendre.
MAX_TRIS_TOPOLOGIE = 200_000
MAX_TRIS_SILHOUETTE = 400_000
SILHOUETTE_PX = 512

_GLB_MAGIC = b"glTF"
_CHUNK_JSON = 0x4E4F534A


def job_dir(job: str) -> Path:
    """Dossier d'un job Game Assets 3D (nom aplati — jamais de traversée)."""
    return settings.outputs_path / "assets3d" / Path(str(job)).name


# ── checksum + entête ────────────────────────────────────────────────────────

def sha256_of(path: Path) -> str:
    """sha256 du fichier, lu par blocs (un GLB texturé pèse vite 50-200 Mo)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _gltf_json(path: Path) -> dict:
    """Chunk JSON d'un .glb (stdlib pure — le binaire est ignoré)."""
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != _GLB_MAGIC:
        raise ValueError(f"{path.name} : magic GLB absent")
    version = struct.unpack_from("<I", raw, 4)[0]
    if version != 2:
        raise ValueError(f"{path.name} : GLB v{version} non géré (v2 attendu)")
    off = 12
    while off + 8 <= len(raw):
        clen, ctype = struct.unpack_from("<II", raw, off)
        off += 8
        if ctype == _CHUNK_JSON:
            return json.loads(raw[off:off + clen].decode("utf-8"))
        off += clen + (-clen % 4)
    raise ValueError(f"{path.name} : chunk JSON introuvable")


# ── inventaire glTF : textures, nodes, animations, extensions ────────────────

def gltf_inventory(path: Path) -> dict:
    """Ce que le document glTF déclare : version, générateur, comptes, et
    l'inventaire des TEXTURES (nom, mime, octets réels du bufferView ou de
    l'URI) — la ligne « textures » que la spec exige dans la fiche."""
    g = _gltf_json(path)
    asset = g.get("asset") or {}
    views = g.get("bufferViews") or []

    images = []
    for i, img in enumerate(g.get("images") or []):
        octets = None
        bv = img.get("bufferView")
        if isinstance(bv, int) and 0 <= bv < len(views):
            octets = int(views[bv].get("byteLength") or 0)
        images.append({
            "index": i,
            "name": img.get("name") or f"image_{i}",
            "mime": img.get("mimeType") or ("externe" if img.get("uri") else "?"),
            "bytes": octets,
            "externe": bool(img.get("uri")),
        })

    # quels canaux PBR sont réellement câblés (une texture déclarée mais non
    # référencée par un matériau ne sert à rien — le dire évite un faux « OK »)
    canaux = set()
    for m in g.get("materials") or []:
        pbr = m.get("pbrMetallicRoughness") or {}
        if pbr.get("baseColorTexture"):
            canaux.add("base_color")
        if pbr.get("metallicRoughnessTexture"):
            canaux.add("metallic_roughness")
        for cle, nom in (("normalTexture", "normal"),
                         ("occlusionTexture", "occlusion"),
                         ("emissiveTexture", "emissive")):
            if m.get(cle):
                canaux.add(nom)

    return {
        "gltf_version": asset.get("version"),
        "generator": asset.get("generator"),
        "copyright": asset.get("copyright"),
        "nodes": len(g.get("nodes") or []),
        "scenes": len(g.get("scenes") or []),
        "skins": len(g.get("skins") or []),
        "animations": len(g.get("animations") or []),
        "cameras": len(g.get("cameras") or []),
        "textures": len(g.get("textures") or []),
        "images": images,
        "texture_bytes": sum(i["bytes"] or 0 for i in images),
        "pbr_channels": sorted(canaux),
        "extensions_used": sorted(g.get("extensionsUsed") or []),
        "extensions_required": sorted(g.get("extensionsRequired") or []),
    }


# ── géométrie : bbox, dimensions, arêtes de bord ─────────────────────────────

def _triangles(path: Path):
    """Triangles en coordonnées MONDE via le lecteur de print3d (transforms de
    nodes appliqués). Lève ValueError parlant sur GLB compressé/externe."""
    from app.services import print3d
    return print3d.lire_glb_triangles(path.read_bytes())


def geometry(path: Path) -> dict:
    """Compteurs + boîte englobante + proportions + arêtes de bord.

    Les compteurs viennent de `mesh_optimize.glb_stats` (déjà éprouvé) ; la
    boîte et la topologie exigent les triangles, donc peuvent échouer
    proprement sur un GLB compressé — dans ce cas on rend `mesure: False`
    avec la raison, jamais une exception qui ferait tomber la fiche.
    """
    from app.services.mesh_optimize import glb_stats
    out = dict(glb_stats(path))          # tris, verts, meshes, materials, bytes
    out["mesure"] = False
    out["raison"] = None

    try:
        tris = _triangles(path)
    except Exception as e:                # GLB compressé, buffer externe, etc.
        out["raison"] = str(e)
        return out
    if not tris:
        out["raison"] = "maillage vide"
        return out

    from app.services.print3d import bbox
    bb = bbox(tris)
    dims = [round(b[1] - b[0], 6) for b in bb]
    plus_grande = max(dims) or 1.0
    out.update({
        "mesure": True,
        "bbox": {"x": list(bb[0]), "y": list(bb[1]), "z": list(bb[2])},
        # glTF est Y-up : largeur = X, hauteur = Y, profondeur = Z
        "dims": {"largeur": dims[0], "hauteur": dims[1], "profondeur": dims[2]},
        "ratio_hauteur_largeur": round(dims[1] / dims[0], 4) if dims[0] else None,
        "ratio_hauteur_profondeur": round(dims[1] / dims[2], 4) if dims[2] else None,
        # normalisé : utile pour comparer deux versions du MÊME asset
        "dims_normalisees": [round(d / plus_grande, 4) for d in dims],
        "tris_lus": len(tris),
    })

    n = len(tris)
    if n > MAX_TRIS_TOPOLOGIE:
        out["topologie"] = {"calcule": False,
                            "raison": f"{n} triangles > {MAX_TRIS_TOPOLOGIE}"}
        return out

    # Arêtes de bord = arêtes utilisées par UN seul triangle : ce sont les
    # trous. Étape 3 de la spec (« revers et zones invisibles ») : un mesh
    # image-to-3D percé au dos se voit ici, sans ouvrir un viewer.
    aretes: dict[tuple, int] = {}
    degeneres = 0
    for t in tris:
        if t[0] == t[1] or t[1] == t[2] or t[0] == t[2]:
            # Un triangle d'aire nulle N'A PAS de bord : le compter et passer.
            # Sans ce `continue` il fabriquait une self-arête (A,A) vue une
            # seule fois — donc une fausse arête de bord — ET incrémentait
            # deux fois l'arête (A,B) — donc un faux non-manifold : un cube
            # étanche ressortait « percé ». Mesuré : cube seul bord_pct 0,0 ;
            # cube + 1 dégénéré bord_pct 5,26.
            degeneres += 1
            continue
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            cle = (a, b) if a <= b else (b, a)
            aretes[cle] = aretes.get(cle, 0) + 1
    bord = sum(1 for v in aretes.values() if v == 1)
    non_manifold = sum(1 for v in aretes.values() if v > 2)
    out["topologie"] = {
        "calcule": True,
        "aretes": len(aretes),
        "aretes_de_bord": bord,
        "aretes_non_manifold": non_manifold,
        "triangles_degeneres": degeneres,
        "ferme": bord == 0 and non_manifold == 0,
        "bord_pct": round(100.0 * bord / max(1, len(aretes)), 2),
    }
    return out


# ── silhouettes projetées : la mesure objective du QC ────────────────────────

_VUES = {
    # nom  : (axe horizontal, axe vertical, inversion verticale)
    "face":   (0, 1, True),    # regard vers -Z : (x, y)
    "profil": (2, 1, True),    # regard vers -X : (z, y)
    "dessus": (0, 2, False),   # regard vers -Y : (x, z)
}


def silhouettes(path: Path, out_dir: Path, px: int = SILHOUETTE_PX) -> dict:
    """Projette le maillage en trois masques binaires (face/profil/dessus).

    Rasterisation PIL des triangles projetés : déterministe, gratuite, sans
    moteur de rendu ni GPU. Le masque sert (a) d'aperçu honnête de la
    silhouette, (b) de base au score d'IoU contre la référence maître.
    Cadrage : la boîte englobante est ajustée dans un carré avec 4 % de marge,
    échelle UNIFORME sur les deux axes — les proportions sont préservées.
    """
    from PIL import Image, ImageDraw

    tris = _triangles(path)
    if not tris:
        raise ValueError("maillage vide")
    if len(tris) > MAX_TRIS_SILHOUETTE:
        raise ValueError(f"{len(tris)} triangles > {MAX_TRIS_SILHOUETTE} — "
                         "silhouette non rendue (optimise le maillage d'abord)")

    from app.services.print3d import bbox
    bb = bbox(tris)
    out_dir.mkdir(parents=True, exist_ok=True)
    marge = 0.04
    rendu = {}

    for nom, (ah, av, inv) in _VUES.items():
        h0, h1 = bb[ah]
        v0, v1 = bb[av]
        etendue = max(h1 - h0, v1 - v0) or 1.0
        utile = px * (1 - 2 * marge)
        ech = utile / etendue
        # centrage de la boîte dans le carré
        dh = (px - (h1 - h0) * ech) / 2
        dv = (px - (v1 - v0) * ech) / 2

        img = Image.new("L", (px, px), 0)
        d = ImageDraw.Draw(img)
        for t in tris:
            poly = []
            for s in t:
                x = (s[ah] - h0) * ech + dh
                y = (s[av] - v0) * ech + dv
                poly.append((x, px - y if inv else y))
            d.polygon(poly, fill=255)

        f = out_dir / f"silhouette_{nom}.png"
        img.save(f, "PNG", optimize=True)
        pleins = sum(1 for p in img.getdata() if p > 127)
        rendu[nom] = {
            "file": f.name,
            "px": px,
            "couverture": round(pleins / float(px * px), 4),
        }
    return rendu


# ── la fiche complète + le registre versionné ────────────────────────────────

def report(glb_path: Path, *, version: int = 1, avec_silhouettes: bool = True,
           extra: dict | None = None) -> dict:
    """Fiche d'un fichier GLB. Chaque section dégrade proprement : un GLB
    compressé rend quand même checksum, taille et inventaire glTF."""
    if not glb_path.is_file():
        raise FileNotFoundError(f"{glb_path.name} introuvable")

    fiche = {
        "version": int(version),
        "file": glb_path.name,
        "bytes": glb_path.stat().st_size,
        "sha256": sha256_of(glb_path),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        fiche["gltf"] = gltf_inventory(glb_path)
    except Exception as e:
        fiche["gltf"] = {"erreur": str(e)}
    try:
        fiche["geometry"] = geometry(glb_path)
    except Exception as e:
        fiche["geometry"] = {"erreur": str(e)}

    if avec_silhouettes:
        try:
            fiche["silhouettes"] = silhouettes(
                glb_path, glb_path.parent / f"sil_v{int(version)}")
            fiche["silhouettes_dir"] = f"sil_v{int(version)}"
        except Exception as e:
            fiche["silhouettes"] = {"erreur": str(e)}

    if extra:
        fiche["source"] = extra
    return fiche


def write_report(job: str, filename: str = "model.glb", *, version: int | None = None,
                 avec_silhouettes: bool = True, extra: dict | None = None) -> dict:
    """Calcule la fiche et l'AJOUTE au registre `report.json` du job.

    Le registre garde toutes les versions (doctrine §2.1). Recalculer une
    version déjà présente REMPLACE son entrée (même version = même artefact),
    mais n'efface jamais les autres.
    """
    d = job_dir(job)
    glb = d / Path(filename).name
    registre_p = d / "report.json"

    registre = {"current": None, "entries": []}
    if registre_p.is_file():
        try:
            charge = json.loads(registre_p.read_text(encoding="utf-8"))
            if isinstance(charge, dict) and isinstance(charge.get("entries"), list):
                registre = charge
        except Exception:
            pass                          # registre illisible : on repart propre

    if version is None:
        connues = [int(e.get("version") or 0) for e in registre["entries"]]
        même = [e for e in registre["entries"] if e.get("file") == glb.name]
        version = int(même[0]["version"]) if même else (max(connues) + 1 if connues else 1)

    fiche = report(glb, version=version, avec_silhouettes=avec_silhouettes, extra=extra)
    registre["entries"] = [e for e in registre["entries"]
                           if int(e.get("version") or 0) != int(version)]
    registre["entries"].append(fiche)
    registre["entries"].sort(key=lambda e: int(e.get("version") or 0))
    # `current` ne RECULE jamais : recalculer la fiche d'une version ancienne
    # (POST .../report sans `file`, qui vise model.glb par défaut) ne doit pas
    # faire redésigner le brouillon comme maillage courant — le QC noterait
    # alors le brouillon à la place du maillage raffiné.
    haute = max(int(e.get("version") or 0) for e in registre["entries"])
    if int(version) >= haute:
        registre["current"] = glb.name
        registre["current_version"] = int(version)
    else:
        registre.setdefault("current", glb.name)
        registre.setdefault("current_version", haute)
    registre_p.write_text(json.dumps(registre, indent=1, ensure_ascii=False),
                          encoding="utf-8")
    return fiche


def read_registry(job: str) -> dict:
    """Le registre du job (404 côté route si absent)."""
    p = job_dir(job) / "report.json"
    if not p.is_file():
        raise FileNotFoundError("aucune fiche pour ce job")
    return json.loads(p.read_text(encoding="utf-8"))
