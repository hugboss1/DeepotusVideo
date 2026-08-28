"""Game Assets 3D: image -> (optional multi-view) -> 3D engine -> mesh + shots.

See docs/superpowers/specs/2026-06-28-game-assets-3d-design.md. Per-engine
argument/result shapes are verified against live fal calls (route smoke); the
adapters below isolate those quirks so the orchestrator stays engine-agnostic.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Vues QUASI-ORTHOGRAPHIQUES (spec Magnific §9.2 étape 1 : « générer des
# références orthographiques ou quasi-orthographiques cohérentes » ; §5.1 :
# « les vues cohérentes et un fond propre renforcent la fidélité de géométrie
# et de texture »).
#
# Deux corrections mesurées par rapport à la première version :
#   1. les deux vues de côté étaient en 3/4 — un quatuor orthographique
#      demande 0°/90°/180°/270°, donc des PROFILS purs ;
#   2. rien ne contraignait la perspective, la hauteur de caméra, l'ombre ni
#      le cadrage — trois sources de dérive entre vues qui font diverger la
#      reconstruction. Le suffixe commun les verrouille.
_CADRAGE = ("orthographic framing, no perspective distortion, camera at "
            "subject mid-height, full body head to feet, centered, identical "
            "scale and distance across views, plain flat neutral background, "
            "even diffuse lighting, no cast shadow, no crop, no text")

_ANGLES = [
    "front view, T-pose",
    "back view, seen directly from behind",
    "left side view, exact profile, 90 degrees",
    "right side view, exact profile, 90 degrees",
]


def view_prompts(n: int, subject: str) -> list[str]:
    """N prompts d'angle (1..4) pour la passe multi-vues.

    Ordre : face, dos, profil gauche, profil droit — le quatuor orthographique.
    Le suffixe de cadrage est identique sur toutes les vues : c'est CE qui
    rend la série cohérente, pas l'angle seul.
    """
    n = 1 if n < 1 else 4 if n > 4 else n
    subj = (subject or "the same character/object, consistent design").strip()
    return [f"{subj}, {a}, {_CADRAGE}" for a in _ANGLES[:n]]


# endpoint + the export formats the engine can emit natively.
#
# CAPABILITY FLAGS (spec Magnific §8, transposée à la 3D) — chaque drapeau
# décrit ce que `build_engine_args` ci-dessous ENVOIE RÉELLEMENT à ce moteur,
# pas ce qu'un fournisseur annonce. Un moteur dont l'adaptateur ne câble pas
# le paramètre est déclaré `False` : l'UI et l'orchestrateur cessent de
# supposer que tout est disponible partout.
#
#   multiview        : l'adaptateur transmet plusieurs vues (sinon la 1re seule)
#   max_images       : combien de vues sont transmises au maximum
#   texture_modes    : les modes de texture réellement atteignables
#   draft            : un brouillon SANS texture est atteignable (étape 2 §9.2)
#   detailed         : une texture haute qualité est atteignable (étape 5 §9.2)
#   pbr              : l'adaptateur demande un matériau PBR
#   tpose            : l'adaptateur sait demander une T-pose (rigging)
#   quality_passthrough : `opts["quality"]` atteint le fournisseur TEL QUEL.
#     Ce que ce drapeau ne dit PAS : l'app ne valide pas la valeur contre
#     l'énumération du moteur. Pour tripo, `quality` ne sert qu'à choisir le
#     palier de texture (voir `texture_mode`) ; pour rodin elle part dans
#     `quality_mesh_option`, dont les valeurs admises sont celles du
#     fournisseur — passer « hd » à rodin est une erreur d'appelant que le
#     registre n'intercepte pas.
ENGINES = {
    "tripo": {
        "endpoint": "tripo3d/tripo/v2.5/image-to-3d",
        "formats": ["glb", "fbx", "obj", "stl", "usdz"],
        "label": "Tripo v2.5",
        "multiview": True, "max_images": 4,
        "texture_modes": ["no", "standard", "HD"],
        "draft": True, "detailed": True, "pbr": True, "tpose": False,
        "quality_passthrough": True,
        "note": "multi-vues + texture HD + 5 formats — le plus complet.",
    },
    "hunyuan": {
        "endpoint": "fal-ai/hunyuan3d/v2",
        "formats": ["glb", "obj"],
        "label": "Hunyuan3D v2",
        "multiview": False, "max_images": 1,
        "texture_modes": ["no", "standard"],
        "draft": True, "detailed": False, "pbr": False, "tpose": False,
        "quality_passthrough": False,
        "note": "image unique, texture on/off — pas de palier HD ici.",
    },
    "trellis": {
        "endpoint": "fal-ai/trellis",
        "formats": ["glb"],
        "label": "Trellis",
        "multiview": False, "max_images": 1,
        "texture_modes": ["standard"],
        "draft": False, "detailed": False, "pbr": False, "tpose": False,
        "quality_passthrough": False,
        "note": "image unique texturée, GLB seul — conversion directe.",
    },
    "rodin": {
        "endpoint": "fal-ai/hyper3d/rodin",
        "formats": ["glb", "fbx", "obj", "stl", "usdz"],
        "label": "Hyper3D Rodin",
        "multiview": True, "max_images": 4,
        "texture_modes": ["standard"],
        "draft": False, "detailed": False, "pbr": True, "tpose": True,
        "quality_passthrough": True,
        "note": "le SEUL à savoir demander une T-pose (asset à rigger).",
    },
    "triposr": {
        "endpoint": "fal-ai/triposr",
        "formats": ["glb"],
        "label": "TripoSR",
        "multiview": False, "max_images": 1,
        "texture_modes": ["standard"],
        "draft": False, "detailed": False, "pbr": False, "tpose": False,
        "quality_passthrough": False,
        "note": "le moins cher — itération de concept, pas de livrable final.",
    },
}

# Besoins de plan → moteur, avec la capacité QUI justifie le choix (§13 phase D
# « comparer les moteurs selon l'asset »). La justification est rendue par
# l'API et stockée sur le job : une recommandation sans motif est un ordre.
BESOINS_3D = {
    "hero": {
        "label": "Hero / personnage détaillé",
        "engine": "tripo",
        "why": "seul moteur cumulant multi-vues (max_images 4) et texture HD ; "
               "5 formats d'export pour la suite de production.",
        "opts": {"multiview": True, "views": 3, "textures": True, "quality": "hd"},
    },
    "prop": {
        "label": "Accessoire / objet simple",
        "engine": "trellis",
        "why": "une image suffit pour un objet compact ; GLB texturé direct, "
               "sans le surcoût des vues complémentaires.",
        "opts": {"multiview": False, "textures": True},
    },
    "decor": {
        "label": "Élément de décor",
        "engine": "tripo",
        "why": "texture standard + export multi-formats ; multi-vues laissé au "
               "choix car un décor cadré n'a souvent qu'une face utile.",
        "opts": {"multiview": False, "textures": True, "quality": "medium"},
    },
    "rig": {
        "label": "Personnage à rigger / animer",
        "engine": "rodin",
        "why": "seul moteur dont l'adaptateur câble la T-pose (tpose=True), "
               "indispensable avant tout squelette.",
        "opts": {"multiview": True, "views": 3, "tpose": True},
    },
    "realtime": {
        "label": "Temps réel / faible polygone",
        "engine": "triposr",
        "why": "aucun moteur du registre n'expose la topologie : le budget de "
               "triangles s'obtient APRÈS coup par gltfpack (preset « game »), "
               "donc on prend le moteur le moins cher.",
        "opts": {"multiview": False},
        # Ce n'est PAS exécuté automatiquement : c'est une étape suivante,
        # rendue par l'API et par la réponse de génération pour que le
        # client puisse la lancer. Un champ qui promettrait une action que
        # rien n'exécute serait un mensonge de plus.
        "apres_generation": {
            "quoi": "budget de triangles par gltfpack (local, gratuit)",
            "route": "POST /api/assets/3d/{job}/optimize",
            "body": {"preset": "game"},
        },
    },
    "brouillon": {
        "label": "Brouillon à valider avant dépense",
        "engine": "tripo",
        "why": "texture « no » atteignable (draft=True) : géométrie seule, "
               "coût réduit ; la texture HD ne part qu'après approbation.",
        "opts": {"multiview": False, "textures": False},
    },
}


def engine_caps(engine: str) -> dict:
    """Entrée du registre pour `engine`, son id inclus. ValueError parlante
    sur un id inconnu (même contrat que fal_service.resolve_video_model)."""
    e = ENGINES.get((engine or "").strip().lower())
    if e is None:
        raise ValueError(f"Moteur 3D inconnu : {engine!r}. Disponibles : "
                         + ", ".join(sorted(ENGINES)))
    return {**e, "id": (engine or "").strip().lower()}


def recommend_engine(besoin: str) -> dict:
    """Recommandation motivée pour un besoin d'asset. ValueError si inconnu."""
    b = BESOINS_3D.get((besoin or "").strip().lower())
    if b is None:
        raise ValueError(f"Besoin inconnu : {besoin!r}. Disponibles : "
                         + ", ".join(sorted(BESOINS_3D)))
    return {**b, "besoin": (besoin or "").strip().lower()}


def texture_mode(engine: str, textures: bool, quality: str | None) -> str:
    """Le mode de texture RÉELLEMENT obtenu pour ce moteur — ce que
    `build_engine_args` produira. Sert au devis et à la gate brouillon→final :
    demander « HD » à un moteur qui n'en a pas doit se voir avant de payer."""
    caps = engine_caps(engine)
    modes = caps["texture_modes"]
    if not textures:
        return "no" if "no" in modes else modes[0]
    if str(quality or "").lower() in ("high", "hd") and "HD" in modes:
        return "HD"
    return "standard" if "standard" in modes else modes[0]


def build_engine_args(engine: str, image_urls: list[str], opts: dict) -> dict:
    """Map the common request to the chosen engine's fal arguments."""
    fmt = (opts.get("format") or "glb").lower()
    primary = image_urls[0] if image_urls else None
    if engine == "rodin":
        return {"input_image_urls": image_urls, "geometry_file_format": fmt,
                "material": "PBR", "quality_mesh_option": opts.get("quality", "medium"),
                "TAPose": bool(opts.get("tpose")), "use_original_alpha": True, "preview_render": True}
    if engine == "tripo":
        # Tripo's `texture` is a literal: 'no' | 'standard' | 'HD' (not a bool).
        if not opts.get("textures", True):
            tex = "no"
        elif str(opts.get("quality", "")).lower() in ("high", "hd"):
            tex = "HD"
        else:
            tex = "standard"
        a = {"image_url": primary, "texture": tex, "output_format": fmt, "pbr": True}
        if len(image_urls) > 1:
            a["multiview_images"] = image_urls
        return a
    if engine == "hunyuan":
        return {"input_image_url": primary, "textured_mesh": bool(opts.get("textures", True)),
                "output_format": fmt}
    # trellis / triposr / fallback
    return {"image_url": primary, "output_format": fmt}


def parse_engine_result(engine: str, res: dict) -> dict:
    """Pull mesh URL (+ any extra-format URLs) + texture URLs + a preview image
    out of whatever shape the engine returned. Tolerant of common fal fields."""
    def _url(v):
        if isinstance(v, dict):
            return v.get("url") or v.get("file_url")
        if isinstance(v, str):
            return v
        return None

    mesh = None
    # tripo v2.5 (pbr:true) livre le mesh texturé dans pbr_model — model_mesh
    # peut être null (constaté le 20/07/2026, schéma OpenAPI fal à l'appui)
    for key in ("model_mesh", "pbr_model", "base_model",
                "mesh", "model", "glb", "model_glb", "output"):
        if key in res and _url(res[key]):
            mesh = _url(res[key])
            break
    if mesh is None:
        from loguru import logger
        logger.warning(f"parse_engine_result[{engine}]: no mesh url in "
                       f"keys={sorted(res.keys())}")
    meshes = {}
    for m in (res.get("model_meshes") or []):
        u = _url(m)
        if u:
            ext = u.rsplit(".", 1)[-1].split("?")[0].lower()
            meshes[ext] = u
    textures = [t for t in (_url(x) for x in (res.get("textures") or [])) if t]
    preview = None
    for key in ("preview_render", "rendered_image", "preview", "thumbnail"):
        if key in res and _url(res[key]):
            preview = _url(res[key])
            break
    return {"mesh_url": mesh, "format_urls": meshes, "texture_urls": textures, "preview_url": preview}


# ── orchestration seams (patched in tests; real impls call fal/HTTP) ──────────
async def _upload(path):
    from app.services.fal_service import FalSeedanceClient
    return await FalSeedanceClient.upload_image(path)


async def _run_engine(engine, args):
    import fal_client
    ep = ENGINES[engine]["endpoint"]
    try:
        res = await fal_client.subscribe_async(ep, arguments=args, with_logs=False)
    except Exception as e:
        raise RuntimeError(f"fal.ai: {e}") from e
    return parse_engine_result(engine, res)


async def _seedream_edit(image_url, prompt):
    import fal_client
    res = await fal_client.subscribe_async(
        "fal-ai/bytedance/seedream/v4/edit",
        arguments={"image_urls": [image_url], "prompt": prompt, "num_images": 1})
    imgs = res.get("images") or []
    return imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else None


def _download(url, dest, timeout=120):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:
        dest.write_bytes(r.read())
    return True


async def generate_asset3d(payload: dict, job_id: str, on_step=None):
    """Upload image -> optional multi-view -> 3D engine -> download mesh formats,
    shots and poster under outputs/assets3d/{job_id}/. Returns a summary dict.
    `on_step(label, pct)` (optional async) is awaited at each phase for live UI."""
    import asyncio
    import shutil
    from pathlib import Path
    from app.config import settings

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    formats = [f.lower() for f in (payload.get("formats") or ["glb"])]
    if "glb" not in formats:
        formats = ["glb"] + formats  # GLB always (preview + interchange)

    out_dir = settings.outputs_path / "assets3d" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    await _step("Uploading", 10)
    # basename + containment check: the raw payload value must never escape the
    # Library folder (it gets uploaded to fal, so a traversal would exfiltrate it)
    fn = Path(str(payload.get("image_filename") or "")).name
    src = settings.images_path / fn
    if not fn or not src.is_file() \
            or not str(src.resolve()).startswith(str(settings.images_path.resolve())):
        raise ValueError(f"Image not found in Library: {payload.get('image_filename')!r}")
    src_url = await _upload(src)

    # shots: shot_0 = source, shot_1..N = multi-view boost
    shutil.copy2(src, out_dir / "shot_0.png")
    shots = ["shot_0.png"]
    image_urls = [src_url]
    if payload.get("multiview"):
        try:
            _nv = max(1, min(4, int(payload.get("views", 3))))
        except (TypeError, ValueError):
            _nv = 3
        for i, pr in enumerate(view_prompts(_nv, payload.get("subject", "")), 1):
            await _step(f"View {i}/{_nv}", 10 + int(40 * i / max(1, _nv)))
            try:
                u = await _seedream_edit(src_url, pr)
            except Exception as e:
                # the multi-view boost is best-effort: keep the views we already
                # have instead of failing the whole (already partly paid) job
                logger.warning(f"multi-view {i}/{_nv} failed (continuing): {e}")
                u = None
            if u:
                await asyncio.to_thread(_download, u, out_dir / f"shot_{i}.png")
                shots.append(f"shot_{i}.png")
                image_urls.append(u)

    await _step(f"Running {engine}", 60)
    base_opts = {"format": "glb", "textures": payload.get("textures", True),
                 "quality": payload.get("quality", "medium"), "tpose": payload.get("tpose")}
    # Plafond du registre (§8 : un drapeau qui ment est pire que pas de
    # drapeau). Avec views=4 la liste vaut source + 4 vues = 5 images, alors
    # que `max_images` en déclare 4 : on tronque ici, à l'entrée du moteur.
    _max = ENGINES[engine]["max_images"]
    if len(image_urls) > _max:
        logger.info(f"{engine}: {len(image_urls)} vues réduites à {_max} "
                    f"(max_images du registre)")
        image_urls = image_urls[:_max]
    result = await _run_engine(engine, build_engine_args(engine, image_urls, base_opts))

    files = {}
    if result.get("mesh_url"):
        await asyncio.to_thread(_download, result["mesh_url"], out_dir / "model.glb")
        files["glb"] = str(out_dir / "model.glb")
    else:
        # sans mesh principal le job n'a aucune valeur : échouer visiblement
        # plutôt que de terminer "done" avec un dossier sans model.glb
        # (cas e9e150d2 du 20/07/2026 — pbr_model non parsé)
        raise RuntimeError(
            f"{engine}: aucun mesh dans la réponse fal (shots conservés)")
    for ext, url in (result.get("format_urls") or {}).items():
        if ext in formats:
            await asyncio.to_thread(_download, url, out_dir / f"model.{ext}")
            files[ext] = str(out_dir / f"model.{ext}")
    # extra formats not returned by the first call -> targeted re-export
    for f in formats:
        if f != "glb" and f not in files and f in ENGINES[engine]["formats"]:
            r2 = await _run_engine(engine, build_engine_args(engine, image_urls,
                {"format": f, "textures": payload.get("textures", True)}))
            if r2.get("mesh_url"):
                await asyncio.to_thread(_download, r2["mesh_url"], out_dir / f"model.{f}")
                files[f] = str(out_dir / f"model.{f}")
    if result.get("preview_url"):
        await asyncio.to_thread(_download, result["preview_url"], out_dir / "preview.png")

    # ── provenance intégrale (spec §16) + fiche du maillage (§9.2 étape 6) ──
    tex = texture_mode(engine, payload.get("textures", True),
                       payload.get("quality"))
    write_manifest(out_dir, {
        "engine": engine, "stage": "draft" if tex == "no" else "final",
        "texture_mode": tex, "version": 1,
        "image_filename": fn, "shots": shots,
        "multiview": bool(payload.get("multiview")),
        "views": len(shots) - 1,
        "formats": formats, "quality": payload.get("quality"),
        "tpose": bool(payload.get("tpose")),
        "engine_args_echo": {k: v for k, v in
                             build_engine_args(engine, ["<image>"], base_opts).items()
                             if k not in ("image_url", "image_urls",
                                          "input_image_url", "input_image_urls",
                                          "multiview_images")},
    })
    await _step("Fiche du maillage", 95)
    try:
        from app.services import mesh_report
        await asyncio.to_thread(
            mesh_report.write_report, job_id, "model.glb", version=1,
            extra={"engine": engine, "texture_mode": tex, "shots": shots})
    except Exception as e:                # jamais bloquant : le mesh est payé
        logger.warning(f"mesh_report {job_id} ignoré : {e}")

    await _step("Complete", 100)
    preview_p = out_dir / "preview.png"
    return {"glb": files.get("glb"), "files": files, "shots": shots,
            "preview": str(preview_p) if preview_p.is_file() else None,
            "skipped_formats": [f for f in formats if f not in files],
            "texture_mode": tex, "stage": "draft" if tex == "no" else "final",
            "engine": engine}


# ── manifeste, approbation et raffinement (spec §9.2 étapes 2, 5, 6) ─────────
#
# Doctrine §2.3 : « Pour la 3D, Magnific recommande d'itérer avec une texture
# Standard puis d'utiliser Detailed une fois la géométrie approuvée. » Ici :
# un brouillon (texture « no ») coûte moins, se juge sur la silhouette, et la
# version texturée ne part QU'APRÈS approbation explicite. Le raffinement
# écrit model.v{n}.glb — jamais un écrasement (§2.1).

def _job_dir(job: str):
    from pathlib import Path as _P
    from app.config import settings
    return settings.outputs_path / "assets3d" / _P(str(job)).name


def write_manifest(out_dir, data: dict) -> dict:
    """asset.json — ce qui a produit ce maillage : moteur, palier de texture,
    vues, options. Rejouer un raffinement sans lui serait deviner."""
    import json as _json
    from datetime import datetime, timezone
    d = dict(data)
    d.setdefault("created_at",
                 datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (out_dir / "asset.json").write_text(
        _json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def read_manifest(job: str) -> dict:
    """Manifeste du job. FileNotFoundError si le job est antérieur au
    manifeste (l'appelant peut alors retomber sur cost_meta)."""
    import json as _json
    p = _job_dir(job) / "asset.json"
    if not p.is_file():
        raise FileNotFoundError("asset.json absent (job antérieur au manifeste)")
    return _json.loads(p.read_text(encoding="utf-8"))


def approve(job: str, ok: bool = True, note: str = "") -> dict:
    """Porte humaine de l'étape 5 : la géométrie du brouillon est approuvée
    (ou refusée, avec le motif). Rien de coûteux ne franchit cette porte
    sans un appel explicite."""
    import json as _json
    from datetime import datetime, timezone
    d = _job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    info = {"approved": bool(ok), "note": str(note or ""),
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (d / "approval.json").write_text(
        _json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    return info


def approval(job: str) -> dict:
    """État d'approbation (jamais approuvé par défaut)."""
    import json as _json
    p = _job_dir(job) / "approval.json"
    if not p.is_file():
        return {"approved": False, "note": "", "at": None}
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"approved": False, "note": "approval.json illisible", "at": None}


def next_version(job: str) -> int:
    """Prochain numéro de version libre d'après les model*.glb présents."""
    import re as _re
    d = _job_dir(job)
    n = 1
    if (d / "model.glb").is_file():
        n = 1
    for f in d.glob("model.v*.glb"):
        m = _re.match(r"model\.v(\d+)\.glb$", f.name)
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


async def refine_asset3d(job: str, quality: str = "hd", on_step=None) -> dict:
    """Rejoue le MÊME moteur sur les MÊMES vues, en texture haute qualité.

    Refuse tant que le brouillon n'est pas approuvé (étape 5) et tant que le
    moteur ne sait pas monter d'un palier (`detailed` du registre) — refuser
    avant de payer vaut mieux qu'un doublon facturé au même niveau.
    """
    import asyncio
    from app.config import settings

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    d = _job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    man = read_manifest(job)
    engine = str(man.get("engine") or "").lower()
    caps = engine_caps(engine)

    if not approval(job).get("approved"):
        raise PermissionError(
            "Brouillon non approuvé : la géométrie doit être validée avant "
            "la passe texturée (spec §9.2 étape 5).")
    if not caps["detailed"]:
        raise ValueError(
            f"{caps['label']} n'a pas de palier haute qualité dans cet "
            f"adaptateur (texture_modes {caps['texture_modes']}) — "
            "régénère avec un moteur qui l'a, plutôt que de repayer pareil.")
    cible = texture_mode(engine, True, quality)
    if cible == man.get("texture_mode"):
        raise ValueError(f"Le maillage est déjà en texture « {cible} ».")

    shots = [s for s in (man.get("shots") or []) if (d / s).is_file()]
    if not shots:
        raise FileNotFoundError(
            "aucune vue conservée sur le disque : impossible de rejouer le "
            "moteur à l'identique.")

    await _step("Renvoi des vues", 15)
    # Plafond du registre : envoyer plus d'images que `max_images` ferait
    # mentir le drapeau — et certains moteurs ignorent silencieusement le
    # surplus, qu'on aurait payé pour rien.
    urls = []
    for s in shots[:caps["max_images"]]:
        urls.append(await _upload(d / s))

    await _step(f"{caps['label']} · texture {cible}", 55)
    opts = {"format": "glb", "textures": True, "quality": quality,
            "tpose": man.get("tpose")}
    res = await _run_engine(engine, build_engine_args(engine, urls, opts))
    if not res.get("mesh_url"):
        raise RuntimeError(f"{engine} : aucun mesh dans la réponse fal")

    # ── à partir d'ici la passe HD est FACTURÉE : plus rien n'a le droit de
    # faire perdre le résultat. Le maillage descend, le manifeste est écrit
    # IMMÉDIATEMENT (sinon un second refine repasserait la porte et
    # repaierait), et tout le reste est best-effort.
    v = next_version(job)
    dest = d / f"model.v{v}.glb"
    await asyncio.to_thread(_download, res["mesh_url"], dest)
    write_manifest(d, {**man, "version": v, "stage": "final",
                       "texture_mode": cible, "quality": quality,
                       "refined_from": man.get("version", 1),
                       "file": dest.name})

    if res.get("preview_url"):
        try:
            await asyncio.to_thread(_download, res["preview_url"],
                                    d / f"preview.v{v}.png")
        except Exception as e:      # URL signée expirée, CDN en panne…
            logger.warning(f"refine {job} : aperçu non téléchargé ({e}) — "
                           f"le maillage {dest.name} est intact")

    await _step("Fiche du maillage", 90)
    try:
        from app.services import mesh_report
        await asyncio.to_thread(
            mesh_report.write_report, job, dest.name, version=v,
            extra={"engine": engine, "texture_mode": cible,
                   "refined_from": man.get("version", 1)})
    except Exception as e:
        logger.warning(f"mesh_report refine {job} ignoré : {e}")

    await _step("Complete", 100)
    return {"version": v, "file": dest.name, "engine": engine,
            "texture_mode": cible,
            "url": f"/api/assets/3d/{job}/version/{v}"}
