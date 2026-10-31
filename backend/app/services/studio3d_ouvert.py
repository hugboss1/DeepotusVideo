# -*- coding: utf-8 -*-
"""t388 (31/10/2026) — le modèle OUVERT dans le 3D Studio à écrans.

Le 3D Studio quitte le graphe Meshy comme interface principale. Il devient une suite d'écrans : Ouvrir, Importer,
Préparer, Texture, Rig, Affiner, Animer, Exporter, Décor, Graphe. Tous partagent un même « modèle ouvert », montré dans
un bandeau : nom, badge riggé, nombre d'os et de sommets, version. Ce module le LIT sur le disque, sans rien écrire et
sans rien dépenser.

Les versions sont celles de l'Établi : `model.glb` (v1), `model.vN.glb`, écrites par `mesh_edit.ecrire_version`, plus
`model.opt.glb` (la décimée, hors numérotation). La liste vient de `mesh_sources`, qui sait déjà ignorer un fichier
hors convention. Le rig et les comptes se lisent dans le chunk JSON du GLB (`mesh_optimize`), jamais dans les données
binaires : ouvrir la galerie ne charge aucun maillage.
"""
from __future__ import annotations

from pathlib import Path

from app.services import mesh_optimize, mesh_sources

# Préréglages de l'écran Préparer, du plus léger au plus lourd. Les huit premiers sont ceux de gltfpack
# (`mesh_optimize.PRESETS`) ; « extreme » et « max » complètent l'échelle relevée chez Sorceress (150 k, 200 k).
PREPARER = ["micro", "small", "prop", "detailed", "game", "balanced", "high", "ultra", "extreme", "max"]


def _job_dir(job: str) -> Path:
    return mesh_sources._jobs_dir() / Path(str(job)).name


def lire_glb(chemin: Path) -> dict:
    """Comptes et rig d'un GLB, lus dans son seul chunk JSON.

    `os` compte les articulations DISTINCTES de toutes les peaux (un même squelette partagé par deux maillages ne
    compte qu'une fois). Un GLB sans peau n'est pas riggé, même s'il porte des animations de nœuds."""
    g = mesh_optimize._read_glb_json(chemin)
    s = mesh_optimize.glb_stats(chemin)
    joints = {int(j) for sk in g.get("skins") or [] for j in sk.get("joints") or []}
    return {
        "sommets": s["verts"], "triangles": s["tris"], "maillages": s["meshes"], "materiaux": s["materials"],
        "octets": s["bytes"], "rig": {"rigge": bool(joints), "os": len(joints),
                                      "animations": len(g.get("animations") or [])},
    }


def vignette(job: str, v: int) -> str | None:
    """L'image d'une version, dans l'ORDRE de `_etabli_vignette` (routes.py) : capture du canevas de l'Établi →
    rendu du moteur → première vue → silhouette ; `None` si le dossier n'a aucune image. Mêmes URL, même règle :
    on ne compose jamais un lien vers un fichier absent (la vignette capturée naît à l'écriture seulement)."""
    d = _job_dir(job)
    if (d / f"vignette_v{int(v)}.png").is_file():
        return f"/api/assets/3d/{d.name}/vignette?v={int(v)}"
    if (d / "preview.png").is_file():
        return f"/api/assets/3d/{d.name}/preview"
    if (d / "shot_0.png").is_file():
        return f"/api/assets/3d/{d.name}/shot/0"
    if (d / f"sil_v{int(v)}" / "silhouette_face.png").is_file():
        return f"/api/assets/3d/{d.name}/silhouette/face?v={int(v)}"
    return None


def _origines(job: str) -> dict:
    """{fichier: (operation, version source)} lus dans le registre des fiches (`report.json`).

    Une version écrite par l'Établi porte dans sa fiche `source = {outil, operation, depuis: {version, fichier}}` :
    c'est ce qui permet à l'écran Préparer de comparer une décimée à SA source, et non à la v1."""
    from app.services import mesh_report
    try:
        registre = mesh_report.read_registry(Path(str(job)).name)
    except (FileNotFoundError, ValueError):
        return {}
    out = {}
    for e in (registre.get("entries") if isinstance(registre, dict) else None) or []:
        src = e.get("source") if isinstance(e, dict) else None
        if not isinstance(src, dict):
            continue
        depuis = src.get("depuis") if isinstance(src.get("depuis"), dict) else {}
        v = depuis.get("version")
        out[str(e.get("file"))] = (src.get("operation"), int(v) if isinstance(v, int) or str(v).isdigit() else None)
    return out


def _ligne(job: str) -> dict | None:
    d = _job_dir(job)
    if not d.is_dir():
        return None
    return mesh_sources._ligne_de_job(d)


def fiche(job: str, version: int | None = None) -> dict:
    """La fiche du bandeau « Ouvert » pour un job, à sa dernière version numérotée ou à `version`.

    FileNotFoundError : job inconnu ou version absente. ValueError : GLB illisible."""
    ligne = _ligne(job)
    if not ligne:
        raise FileNotFoundError(f"modèle 3D inconnu : {Path(str(job)).name}")
    origines = _origines(ligne["id"])
    numerotees = [{**e, "operation": origines.get(e["file"], (None, None))[0],
                   "depuis": origines.get(e["file"], (None, None))[1]}
                  for e in ligne["etapes"] if e.get("version") is not None]
    if not numerotees:
        raise FileNotFoundError(f"{ligne['id']} : aucune version numérotée")
    if version is None:
        etape = numerotees[-1]
    else:
        etape = next((e for e in numerotees if e["version"] == int(version)), None)
        if etape is None:
            raise FileNotFoundError(f"{ligne['id']} : version {version} absente")
    lu = lire_glb(_job_dir(ligne["id"]) / etape["file"])
    decimee = next((e for e in ligne["etapes"] if e["file"] == "model.opt.glb"), None)
    return {
        "job": ligne["id"], "nom": ligne["nom"], "moteur": ligne["moteur"], "phase": ligne["phase"],
        "created_at": ligne["created_at"], "version": etape["version"],
        "derniere": numerotees[-1]["version"], "url": etape["url"],
        "vignette": vignette(ligne["id"], etape["version"]),
        "versions": numerotees, "decimee": decimee,
        **lu,
    }


def modeles() -> list[dict]:
    """La galerie de l'écran Ouvrir : un modèle par job, à sa dernière version, du plus récent au plus ancien.

    Un job dont le GLB est illisible reste listé, sans comptes (`illisible: True`) : il disparaîtrait sinon de l'écran
    sans un mot, comme le défaut déjà corrigé dans `mesh_sources`."""
    out = []
    for ligne in mesh_sources.lister():
        numerotees = [e for e in ligne["etapes"] if e.get("version") is not None]
        if not numerotees:
            continue
        e = numerotees[-1]
        m = {"job": ligne["id"], "nom": ligne["nom"], "moteur": ligne["moteur"], "phase": ligne["phase"],
             "created_at": ligne["created_at"], "version": e["version"], "url": e["url"],
             "vignette": vignette(ligne["id"], e["version"]), "illisible": False,
             # t389 : l'image source (shot_0), pour le volet avant/après de la galerie de l'écran Créer
             "source": (f"/api/assets/3d/{ligne['id']}/shot/0"
                        if (_job_dir(ligne["id"]) / "shot_0.png").is_file() else None)}
        try:
            m.update(lire_glb(_job_dir(ligne["id"]) / e["file"]))
        except (OSError, ValueError, KeyError):
            m["illisible"] = True
            m["rig"] = {"rigge": False, "os": 0, "animations": 0}
        out.append(m)
    out.sort(key=lambda m: (m.get("created_at") or "", m["job"]), reverse=True)
    return out


def preparer_cibles() -> list[dict]:
    """Les préréglages de l'écran Préparer avec leur budget en triangles, dans l'ordre."""
    budgets = dict(mesh_optimize.PRESETS)
    return [{"preset": p, "triangles": budgets[p]} for p in PREPARER if p in budgets]
