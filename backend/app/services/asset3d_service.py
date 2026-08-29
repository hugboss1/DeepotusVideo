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
        "face_limit": False, "quad": False, "seed": False,
        "note": "multi-vues + texture HD + 5 formats — le plus complet.",
    },
    # Tripo H3.1 — ajouté le 29/08/2026, pages fal relues le jour même.
    #
    # LE NOM : « Tripo v3.1 » (spec Magnific §9.1) et « Tripo3D H3.1 » sont le
    # MÊME modèle — H3.1 (HD Model) est le nom officiel, v3.1 la façon
    # informelle de le citer. L'endpoint `tripo3d/tripo/v3.1` n'existe pas sur
    # fal (404) ; c'est `tripo3d/h3.1/…` qu'il faut appeler, avec DEUX
    # endpoints séparés (image unique / multi-vues) là où v2.5 n'en avait
    # qu'un.
    #
    # DEUX ÉCARTS avec les fiches produit qui circulent, mesurés sur fal :
    #   • le multi-vues n'est PAS moins cher ici. Certaines plateformes le
    #     facturent moitié prix ; la page fal du multiview affiche mot pour
    #     mot le même tarif que l'image unique (0,20/0,30/0,40 $). C'est fal
    #     qui facture cette app, donc c'est ce tarif-là qui compte.
    #   • Tripo accepte jusqu'à 10 vues en direct ; l'endpoint fal en déclare
    #     « 2 to 4 ». max_images reste donc 4 — le drapeau dit ce que CE
    #     chemin d'appel permet, pas ce que le modèle sait faire ailleurs.
    # Paramètres relevés sur la page API : image_url | image_urls (2-4, ordre
    # IMPOSÉ [front, left, back, right], front obligatoire), texture (bool),
    # pbr (bool), texture_quality standard|detailed, geometry_quality
    # standard|detailed, texture_alignment original_image|geometry,
    # face_limit (int), quad (bool), model_seed, texture_seed, auto_size,
    # orientation default|align_image.
    # Sortie : model_mesh + model_urls{glb, fbx, base_model, pbr_model}
    # + rendered_image.
    # Prix affiché : 0,20 $ sans texture · 0,30 $ texture standard · 0,40 $
    # texture HD, + 0,20 $ géométrie détaillée, + 0,05 $ maillage quad.
    "tripo-h3.1": {
        "endpoint": "tripo3d/h3.1/image-to-3d",
        "endpoint_multiview": "tripo3d/h3.1/multiview-to-3d",
        "formats": ["glb", "fbx"],
        "label": "Tripo H3.1",
        "multiview": True, "max_images": 4,
        "view_order": ["front", "left", "back", "right"],
        "texture_modes": ["no", "standard", "HD"],
        "draft": True, "detailed": True, "pbr": True, "tpose": False,
        "quality_passthrough": True,
        # les DEUX seules capacités de topologie de tout le registre
        "face_limit": True, "quad": True, "seed": True,
        "note": "budget de faces et maillage quad — le seul du registre à "
                "piloter la topologie ; multi-vues sur endpoint dédié.",
    },
    "hunyuan": {
        "endpoint": "fal-ai/hunyuan3d/v2",
        "formats": ["glb", "obj"],
        "label": "Hunyuan3D v2",
        "multiview": False, "max_images": 1,
        "texture_modes": ["no", "standard"],
        "draft": True, "detailed": False, "pbr": False, "tpose": False,
        "quality_passthrough": False,
        "face_limit": False, "quad": False, "seed": False,
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
        "face_limit": False, "quad": False, "seed": False,
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
        "face_limit": False, "quad": False, "seed": False,
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
        "face_limit": False, "quad": False, "seed": False,
        "note": "le moins cher — itération de concept, pas de livrable final.",
    },
}

# Besoins de plan → moteur, avec la capacité QUI justifie le choix (§13 phase D
# « comparer les moteurs selon l'asset »). La justification est rendue par
# l'API et stockée sur le job : une recommandation sans motif est un ordre.
BESOINS_3D = {
    # CHAÎNE Tripo → Meshy (décision utilisateur du 29/08) : Tripo reconstruit
    # le VOLUME depuis 4 vues, Meshy fait la TEXTURE. On ne paie donc pas la
    # texture Tripo (textures=False, 0,20 $ au lieu de 0,40 $), et les 4 vues
    # resservent telles quelles comme référence de style chez Meshy.
    "hero": {
        "label": "Hero / personnage détaillé",
        "engine": "tripo-h3.1",
        "why": "Tripo H3.1 pour le volume — 4 vues sur endpoint dédié, ordre "
               "imposé donc reconstruction moins ambiguë, et seed de géométrie "
               "pour rejouer à l'identique. La texture part chez Meshy : "
               "géométrie nue ici (0,20 $ au lieu de 0,40 $).",
        "opts": {"multiview": True, "views": 4, "textures": False},
        "apres_generation": {
            "quoi": "texturage Meshy (PBR) depuis les MÊMES 4 vues, une fois "
                    "la géométrie approuvée",
            "route": "POST /api/assets/3d/{job}/texturer",
            "body": {"resolution": "2k", "pbr": True},
        },
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
        "engine": "tripo-h3.1",
        "why": "le seul moteur du registre à piloter la topologie À LA SOURCE "
               "(face_limit, et quad pour un maillage éditable) — meilleur "
               "qu'une décimation après coup, qui ne peut que retirer.",
        "opts": {"multiview": False, "textures": True, "face_limit": 10000},
        # Ce n'est PAS exécuté automatiquement : c'est une étape suivante,
        # rendue par l'API et par la réponse de génération pour que le
        # client puisse la lancer. Un champ qui promettrait une action que
        # rien n'exécute serait un mensonge de plus.
        "apres_generation": {
            "quoi": "vérifier le budget atteint, et le forcer par gltfpack si "
                    "le moteur est resté au-dessus (local, gratuit)",
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


# Clés des vues, dans l'ordre où `view_prompts` les produit. La liste des
# shots d'un job est [source, *VUES_CLES[:n]] — c'est ce qui permet de
# RÉORDONNER pour un moteur dont l'ordre est imposé.
VUES_CLES = ["front", "back", "left", "right"]


def cles_des_vues(n_urls: int) -> list[str]:
    """Clés parallèles à `image_urls` = ['source', 'front', 'back', ...]."""
    return ["source"] + VUES_CLES[:max(0, n_urls - 1)]


def ordonner_vues(engine: str, image_urls: list[str],
                  view_keys: list[str] | None = None) -> list[str]:
    """Réordonne les vues selon l'ordre IMPOSÉ par le moteur, s'il en a un.

    Tripo H3.1 multiview documente « Order: [front, left, back, right]. Front
    view is required. » — envoyer nos vues dans l'ordre d'auteur (face, dos,
    gauche, droite) donnerait donc un dos là où le moteur attend un profil.
    Sans `view_order` au registre, ou sans clés fournies, on passe la liste
    telle quelle : le comportement des quatre autres moteurs ne bouge pas.
    """
    e = ENGINES.get(engine) or {}
    ordre = e.get("view_order")
    if not ordre or not view_keys or len(view_keys) != len(image_urls):
        return image_urls[:e.get("max_images") or len(image_urls)]
    par_cle = dict(zip(view_keys, image_urls))
    sortie = [par_cle[k] for k in ordre if k in par_cle]
    # « Front view is required » : à défaut de vue de face générée, l'image
    # SOURCE tient ce rôle — c'est elle qui a produit toutes les autres.
    if "front" not in par_cle and "source" in par_cle:
        sortie.insert(0, par_cle["source"])
    return sortie[:e.get("max_images") or len(sortie)]


def resolve_endpoint(engine: str, n_images: int = 1) -> str:
    """L'endpoint à appeler. H3.1 sépare image unique et multi-vues en DEUX
    endpoints ; v2.5 passait ses vues en paramètre du même."""
    e = engine_caps(engine)
    if n_images > 1 and e.get("endpoint_multiview"):
        return e["endpoint_multiview"]
    return e["endpoint"]


def build_engine_args(engine: str, image_urls: list[str], opts: dict) -> dict:
    """Map the common request to the chosen engine's fal arguments."""
    fmt = (opts.get("format") or "glb").lower()
    primary = image_urls[0] if image_urls else None
    if engine == "tripo-h3.1":
        # Contrat relu sur fal le 29/08/2026 : `texture` et `pbr` sont des
        # BOOLÉENS (v2.5 attendait un littéral dans `texture`), le palier vit
        # dans `texture_quality` standard|detailed. Aucun `output_format` :
        # la sortie porte toujours glb ET fbx dans `model_urls`.
        tex_on = bool(opts.get("textures", True))
        hd = str(opts.get("quality", "")).lower() in ("high", "hd")
        a = {"texture": tex_on, "pbr": tex_on}
        if tex_on:
            a["texture_quality"] = "detailed" if hd else "standard"
        if opts.get("geometry_detaillee"):
            a["geometry_quality"] = "detailed"      # +0,20 $ — jamais d'office
        if opts.get("face_limit"):
            a["face_limit"] = int(opts["face_limit"])
        if opts.get("quad"):
            a["quad"] = True                        # +0,05 $
        if opts.get("seed") is not None:
            a["model_seed"] = int(opts["seed"])
            a["texture_seed"] = int(opts["seed"])
        vues = ordonner_vues(engine, image_urls, opts.get("view_keys"))
        if len(vues) > 1:
            a["image_urls"] = vues
        else:
            a["image_url"] = vues[0] if vues else primary
        return a
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
    # Tripo H3.1 livre ses formats dans un OBJET `model_urls`
    # {glb, fbx, base_model, pbr_model} — pas dans la liste `model_meshes`.
    # Sans ceci, le .fbx annoncé par le registre n'était jamais récupéré et
    # `generate_asset3d` relançait une génération PAYANTE pour l'obtenir.
    mu = res.get("model_urls")
    if isinstance(mu, dict):
        for cle in ("glb", "fbx", "obj", "stl", "usdz"):
            u = _url(mu.get(cle))
            if u:
                meshes.setdefault(cle, u)
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


async def _run_engine(engine, args, endpoint=None):
    import fal_client
    # H3.1 a un endpoint multi-vues DISTINCT. Le nombre d'images est déjà
    # dans `args` (image_url seule, ou une liste image_urls/multiview_images
    # déjà ordonnée et plafonnée) : le déduire ICI évite de le faire remonter
    # dans chaque appelant — et garde la signature historique utilisable.
    n = max((len(v) for v in args.values() if isinstance(v, list)), default=1)
    ep = endpoint or resolve_endpoint(engine, n)
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
                 "quality": payload.get("quality", "medium"),
                 "tpose": payload.get("tpose"),
                 # options de topologie / reproductibilité — seul H3.1 les
                 # câble ; les autres adaptateurs les ignorent
                 "face_limit": payload.get("face_limit"),
                 "quad": payload.get("quad"),
                 "geometry_detaillee": payload.get("geometry_detaillee"),
                 "seed": payload.get("seed")}
    # UN SEUL mécanisme pour le plafond du registre ET l'ordre imposé : avec
    # views=4 la liste vaut source + 4 vues = 5 images alors que `max_images`
    # en déclare 4 (§8 : un drapeau qui ment est pire que pas de drapeau), et
    # H3.1 exige [front, left, back, right].
    vues = ordonner_vues(engine, image_urls, cles_des_vues(len(image_urls)))
    if len(vues) != len(image_urls):
        logger.info(f"{engine}: {len(image_urls)} vues → {len(vues)} envoyées "
                    f"(max_images {ENGINES[engine]['max_images']}"
                    + (f", ordre {ENGINES[engine]['view_order']}"
                       if ENGINES[engine].get("view_order") else "") + ")")
    result = await _run_engine(engine, build_engine_args(engine, vues, base_opts))

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
    # On renvoie TOUTES les vues conservées, puis `ordonner_vues` applique le
    # plafond et l'ordre imposé du moteur : tronquer avant réordonnancement
    # amputerait H3.1 de son profil droit.
    urls = []
    for s in shots[:1 + len(VUES_CLES)]:
        urls.append(await _upload(d / s))
    vues = ordonner_vues(engine, urls, cles_des_vues(len(urls)))

    await _step(f"{caps['label']} · texture {cible}", 55)
    opts = {"format": "glb", "textures": True, "quality": quality,
            "tpose": man.get("tpose"),
            "face_limit": man.get("face_limit"), "quad": man.get("quad"),
            "seed": man.get("seed")}
    res = await _run_engine(engine, build_engine_args(engine, vues, opts))
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


# ── texturage Meshy d'un maillage Tripo (29/08) ─────────────────────────────
#
# Décision produit (utilisateur, 29/08) : « utilise tripo pour le 4 vue et
# bascule sur meshy pour les rendu notamment le texturage des modèles
# générés. » La chaîne devient donc :
#
#   4 vues quasi-orthographiques  (Seedream, déjà là)
#     → Tripo H3.1 multi-vues, texture=false → GÉOMÉTRIE seule (0,20 $)
#     → porte humaine : la silhouette se juge sur le brouillon
#     → Meshy retexture (model_url externe + les MÊMES 4 vues en style)
#
# Les vues servent donc DEUX fois : à reconstruire le volume, puis à dire
# de quoi il a l'air. C'est aussi pourquoi elles imposent « even diffuse
# lighting, no cast shadow » — une lumière incrustée dans la référence se
# retrouverait cuite dans la texture.
#
# Meshy accepte un maillage ÉTRANGER via `model_url` (docs.meshy.ai/api/
# retexture : « publicly accessible URL … or a base64-encoded data URI »).
# Le pont est le stockage fal, qui rend déjà une URL publique pour tout
# fichier téléversé — même chemin que les images du reste de l'app.

MESHY_RETEXTURE_BASE = "openapi/v1/retexture"
MESHY_POLL_S = 4.0
MESHY_POLL_RETRIES = 5
MESHY_TIMEOUT_S = 1800.0


async def _attendre_meshy(base: str, tid: str, on_step=None,
                          depart: int = 55, fin: int = 85) -> dict:
    """Attend une tâche Meshy jusqu'à son état terminal.

    Même garantie que la boucle éprouvée du Cardforge (forge3d) : un blip
    réseau ne tue pas une tâche PAYÉE — les reprises sont bornées ET vivent
    dans le budget global, au-delà duquel l'échec porte le message littéral.
    """
    import asyncio
    import time
    from app.services import meshy_service as MS

    periode = 0.05 if MS.mock_enabled() else MESHY_POLL_S
    budget = time.monotonic() + MESHY_TIMEOUT_S
    echecs = 0
    while True:
        try:
            task = await MS.get_task(base, tid)
            echecs = 0
        except Exception:
            echecs += 1
            if echecs > MESHY_POLL_RETRIES or time.monotonic() > budget:
                raise
            await asyncio.sleep(min(periode * 2 ** echecs, 30.0))
            continue

        statut = str(task.get("status") or "")
        if on_step:
            try:
                pct = int(task.get("progress") or 0)
            except (TypeError, ValueError):
                pct = 0
            await on_step(f"Meshy {statut}",
                          max(depart, min(fin, depart + pct * (fin - depart) // 100)))
        if statut == "SUCCEEDED":
            return task
        if statut in ("FAILED", "CANCELED"):
            err = task.get("task_error")
            msg = err.get("message") if isinstance(err, dict) else None
            raise RuntimeError(f"meshy: {msg or f'tâche {statut}'}")
        if time.monotonic() > budget:
            raise RuntimeError(
                f"meshy: tâche {tid} toujours « {statut} » après "
                f"{int(MESHY_TIMEOUT_S // 60)} min")
        await asyncio.sleep(periode)


def _glb_courant(job: str) -> str:
    """Le fichier de maillage que le registre désigne comme courant, sinon
    model.glb. C'est LUI qu'on texture — pas un brouillon oublié."""
    try:
        from app.services import mesh_report
        reg = mesh_report.read_registry(job)
        nom = reg.get("current")
        if nom and (_job_dir(job) / nom).is_file():
            return nom
    except Exception:
        pass
    return "model.glb"


async def texturer_asset3d(job: str, *, resolution: str = "2k",
                           pbr: bool = True, ai_model: str = "meshy-7",
                           style_prompt: str | None = None,
                           garder_uv: bool = False, on_step=None) -> dict:
    """Texture un maillage existant chez Meshy, et l'ajoute en NOUVELLE version.

    Refuse tant que la géométrie n'est pas approuvée : c'est la même porte que
    `refine_asset3d`, parce que c'est la même dépense évitable — texturer un
    volume raté coûte autant que texturer un bon.
    """
    import asyncio
    import shutil
    from app.services import meshy_service as MS

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    d = _job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    man = read_manifest(job)              # FileNotFoundError parlante si absent
    if not approval(job).get("approved"):
        raise PermissionError(
            "Géométrie non approuvée : valide le volume (POST .../approve) "
            "avant de payer un texturage.")

    nom_glb = _glb_courant(job)
    src = d / nom_glb
    if not src.is_file():
        raise FileNotFoundError(f"{nom_glb} introuvable pour ce job")

    # style : les vues GÉNÉRÉES d'abord (fond propre, lumière plate — donc
    # aucune ombre cuite dans la texture), la source en repli.
    vues = [s for s in (man.get("shots") or [])[1:] if (d / s).is_file()][:4]
    if not vues and (d / "shot_0.png").is_file():
        vues = ["shot_0.png"]
    if not vues and not (style_prompt or "").strip():
        raise ValueError(
            "Aucune vue conservée et aucun style demandé : Meshy a besoin "
            "d'au moins une référence (image) ou d'un texte de style.")

    await _step("Envoi du maillage", 20)
    model_url = await _upload(src)
    urls_vues = []
    for v in vues:
        urls_vues.append(await _upload(d / v))

    payload: dict = {
        "model_url": model_url,
        "ai_model": ai_model,
        "enable_pbr": bool(pbr),
        "texture_resolution": resolution,
        # false = Meshy refait ses UV. Un maillage Tripo sans texture n'a pas
        # d'UV utilisable, donc c'est le défaut correct ici ; l'exposer permet
        # de le garder quand on texture un maillage DÉJÀ déplié.
        "enable_original_uv": bool(garder_uv),
        "target_formats": ["glb"],
    }
    if urls_vues:
        payload["multiview_image_urls"] = urls_vues
    elif style_prompt:
        payload["text_style_prompt"] = style_prompt[:600]

    await _step(f"Meshy retexture {resolution}", 45)
    tid = await MS.create_task(MESHY_RETEXTURE_BASE, payload)
    # sans cet enregistrement, `repatriate` refuse un id qu'il ne connaît pas
    await MS.record_created(tid, MESHY_RETEXTURE_BASE, payload)

    task = await _attendre_meshy(MESHY_RETEXTURE_BASE, tid, on_step)
    await MS.record_state(task, MESHY_RETEXTURE_BASE)

    await _step("Rapatriement", 88)
    rap = await MS.repatriate(tid)
    # `files` est {clé: NOM DE FICHIER}, le dossier est à part — les joindre
    # (un nom seul serait résolu depuis le répertoire courant du process).
    from pathlib import Path as _P
    fichiers = rap.get("files") or {}
    nom = fichiers.get("glb") or next(
        (v for v in fichiers.values() if str(v).lower().endswith(".glb")), None)
    if not nom:
        raise RuntimeError(
            f"meshy: la tâche {tid} n'a rendu aucun GLB "
            f"(reçu : {sorted(fichiers) or 'rien'})")
    local = _P(rap["dir"]) / nom
    if not local.is_file():
        raise RuntimeError(f"meshy: {local.name} annoncé mais absent du disque")

    # ── à partir d'ici les crédits sont CONSOMMÉS : le maillage entre dans le
    # registre du job immédiatement, le reste est best-effort.
    v = next_version(job)
    dest = d / f"model.v{v}.glb"
    await asyncio.to_thread(shutil.copy2, local, dest)
    write_manifest(d, {**man, "version": v, "stage": "final",
                       "texture_mode": f"meshy:{resolution}",
                       "texturier": "meshy", "meshy_task": tid,
                       "meshy_ai_model": ai_model, "pbr": bool(pbr),
                       "refined_from": man.get("version", 1),
                       "file": dest.name})
    try:
        from app.services import mesh_report
        await asyncio.to_thread(
            mesh_report.write_report, job, dest.name, version=v,
            extra={"engine": man.get("engine"), "texturier": "meshy",
                   "texture_mode": f"meshy:{resolution}", "meshy_task": tid,
                   "refined_from": man.get("version", 1)})
    except Exception as e:
        logger.warning(f"mesh_report texturage {job} ignoré : {e}")

    await _step("Complete", 100)
    return {"version": v, "file": dest.name, "meshy_task": tid,
            "texture_mode": f"meshy:{resolution}", "pbr": bool(pbr),
            "url": f"/api/assets/3d/{job}/version/{v}"}
