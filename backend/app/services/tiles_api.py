# -*- coding: utf-8 -*-
"""Le routeur des tuiles — UNE porte pour toutes les routes de `/api/tiles`
(plan 2026-09-03-plan-tuiles, tâche t113). Monté par `main.py` sous
`/api/tiles` (bloc `__DZ_TILES_ROUTER_*`, patron des autres routeurs).

Tout est LOCAL (PIL pur, aucun fournisseur payant). Le calcul — assemblage,
atlas, et le raccord mesuré sur TOUTES les paires légales — part dans un
exécuteur : à 512 px et 5 variantes il pèse plusieurs secondes, et la boucle
d'évènements de l'application ne doit pas s'arrêter pour lui.
"""
from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services import library_index as LI
from app.services import tile_ops as TO
from app.services import tile_store as TS

router = APIRouter()


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _spec(spec) -> dict | None:
    """La source TELLE QUE REÇUE, réduite à sa seule clé utile — c'est elle que le meta garde, et que `_refaire_jeu`
    rejoue (T116 : le meta écrivait toujours `{"image": …}`, une matière du Forge y devenait `{"image": None}`)."""
    if not isinstance(spec, dict):
        return None
    if spec.get("materiau"):
        return {"materiau": str(spec["materiau"])}
    return {"image": spec.get("image")}


def _charger_matiere(spec, quoi: str) -> Image.Image:
    """Une matière = une image de la Bibliothèque, désignée par son NOM (un chemin est refusé), OU une matière du
    Material Forge, désignée par son id `mat_xxxxxxxx` (T116, plan T10) : sa couleur de base, `basecolor.png` — celle
    que le Forge affiche, `bake_levels` ne touchant que métal, rugosité et ORM. Une seule des deux clés."""
    if not isinstance(spec, dict):
        raise HTTPException(400, f"{quoi}: objet attendu")
    if spec.get("materiau") is not None:
        if spec.get("image"):
            raise HTTPException(400, f"{quoi}: une seule source — 'image' OU 'materiau'")
        from app.services import material_store as MS
        mid = str(spec.get("materiau") or "").strip()
        if not MS.is_valid_mid(mid):
            raise HTTPException(400, f"{quoi}: identifiant de matiere invalide: {mid!r}")
        try:
            if not MS.material_dir(mid).is_dir():
                raise ValueError(mid)
            p = MS.map_path(mid, "basecolor")
        except ValueError:
            raise HTTPException(400, f"{quoi}: matiere introuvable: {mid}")
        if not p.is_file():
            raise HTTPException(400, f"{quoi}: la matiere {mid} n'a pas de couleur de base (basecolor)")
        try:
            with Image.open(p) as im:
                return im.convert("RGB").copy()
        except (UnidentifiedImageError, OSError) as e:
            raise HTTPException(400, f"{quoi}: couleur de base illisible: {mid} ({e})")
    nom = str(spec.get("image") or "").strip()
    if not nom:
        raise HTTPException(400, f"{quoi}: cle 'image' attendue")
    p = settings.images_path / nom
    if p.name != nom or "\\" in nom or not p.is_file():
        raise HTTPException(400, f"{quoi}: image introuvable: {nom}")
    try:
        with Image.open(p) as im:
            return im.convert("RGB").copy()
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(400, f"{quoi}: image illisible: {nom} ({e})")


def _fabriquer(a, b, jeu_nom, cote, variantes, graine, forme="carre"):
    """Bloquant : le jeu, son atlas, et son raccord — le pire des paires légales pour un jeu carré ; pour une forme,
    celui de la matière avec elle-même (le réseau n'en ajoute aucun, voir tile_shapes). L'atlas d'une forme GARDE
    son alpha : converti en RGB (comme le plan l'écrivait), ses coins hors losange deviendraient noirs."""
    if forme != "carre":
        from app.services import tile_shapes as TF
        jeu = TO.assembler_forme(a, forme, cote)
        return jeu, jeu["tuiles"][0], 1, 1, TF.raccord_forme(a, forme, cote)
    from app.services import tile_metrics as TM
    jeu = TO.assembler_jeu(a, b, jeu_nom, cote, variantes, graine)
    img, colonnes, rangees = TO.atlas(jeu)
    return jeu, img, colonnes, rangees, TM.raccord_jeu(jeu)


@router.post("/jeu")
async def creer_jeu(body: dict):
    """Fabrique un jeu de tuiles depuis DEUX matières et le range.
    Body: {matiere_a:{image}, matiere_b:{image}, jeu, cote, variantes, graine, nom, forme}.
    `forme` : carre (défaut, le blob depuis deux matières) | iso | hex (une tuile de forme, une seule matière).
    → la méta du jeu PRODUIT, dont `raccord` = le PIRE raccord mesuré."""
    body = body if isinstance(body, dict) else {}
    jeu_nom = str(body.get("jeu") or "blob47")
    if jeu_nom not in TO.JEUX:
        raise HTTPException(400, f"jeu inconnu: {jeu_nom} (attendu {', '.join(TO.JEUX)})")
    try:
        cote = int(body.get("cote") or 64)
        variantes = int(body.get("variantes") or 1)
        graine = int(body.get("graine") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "cote, variantes et graine sont des entiers")
    if not 16 <= cote <= 512:
        raise HTTPException(400, "cote doit tenir entre 16 et 512")
    if not 1 <= variantes <= 5:
        raise HTTPException(400, "variantes doit tenir entre 1 et 5")
    forme = str(body.get("forme") or "carre")
    if forme not in ("carre", "iso", "hex"):
        raise HTTPException(400, f"forme inconnue: {forme} (attendu carre, iso, hex)")
    a = _charger_matiere(body.get("matiere_a") or {}, "matiere_a")
    # une forme n'a qu'une matière ; un jeu carré exige toujours la seconde (le fond)
    b = None if forme != "carre" else _charger_matiere(body.get("matiere_b") or {}, "matiere_b")

    jeu, img, colonnes, rangees, raccord = await asyncio.get_running_loop().run_in_executor(
        None, _fabriquer, a, b, jeu_nom, cote, variantes, graine, forme)

    tid = TS.new_tid()
    d = TS.tileset_dir(tid, create=True)
    img.save(d / "atlas.png", format="PNG")
    meta = {"tid": tid, "nom": str(body.get("nom") or "jeu de tuiles")[:80],
            # le meta décrit le jeu PRODUIT, pas le corps reçu : `_refaire_jeu` le rejoue tel quel
            "jeu": jeu["jeu"], "cles": jeu["cles"], "cote": jeu["cote"],
            "variantes": jeu["variantes"], "graine": jeu["graine"], "forme": forme,
            "largeur": jeu.get("largeur", jeu["cote"]), "hauteur": jeu.get("hauteur", jeu["cote"]),
            "tuiles": len(jeu["tuiles"]), "vide": jeu["vide"],
            "colonnes": colonnes, "rangees": rangees,
            "source_a": _spec(body.get("matiere_a")),
            "source_b": None if b is None else _spec(body.get("matiere_b")),
            "raccord": raccord, "cree_le": _maintenant()}
    TS.write_meta(tid, meta)
    # LA PROVENANCE : l'atlas est COPIÉ dans la Bibliothèque sous `tile_<id>_atlas.png` (préfixe → source
    # « tuiles »), puis indexé. Indexer le seul NOM (comme le plan le dessinait) aurait posé dans l'index une
    # ligne vers un fichier qui n'existe pas dans le dossier des images.
    copie = settings.images_path / f"{tid}_atlas.png"
    try:
        shutil.copyfile(d / "atlas.png", copie)
        await LI.noter([copie.name], "tuiles")
    except Exception as e:  # noqa: BLE001 — la provenance n'empêche jamais le jeu
        logger.warning(f"tuiles : copie / index de l'atlas ignorés ({e})")
    logger.info(f"tuiles/jeu {jeu_nom} {len(jeu['tuiles'])} tuiles cote={cote} x{variantes} "
                f"raccord={raccord} -> {tid}")
    return meta


@router.get("")
async def lister():
    return {"tilesets": TS.list_tilesets()}


@router.get("/{tid}")
async def lire(tid: str):
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    meta["tid"] = tid
    return meta


@router.post("/{tid}/export")
async def exporter(tid: str, body: dict):
    """Body: {format: 'tiled'|'ldtk'|'godot'} (t114, plan T3-T5). Écrit `tileset.tsx`, `projet.ldtk` ou
    `tileset.tres` dans le dossier du jeu, à côté de son `atlas.png`, et rend son nom — le fichier fait foi, et la
    route de fichier le sert (les trois noms sont dans la liste blanche de `tile_store`)."""
    from app.services import tile_export as TE
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    fmt = str((body or {}).get("format") or "").strip().lower()
    if fmt not in TE.FORMATS:
        raise HTTPException(400, f"format inconnu: {fmt or '(vide)'} (attendu {', '.join(sorted(TE.FORMATS))})")
    try:
        p = await asyncio.to_thread(TE.FORMATS[fmt], TS.tileset_dir(tid), meta)
    except ValueError as e:              # refus MOTIVÉ d'un format (LDtk et les formes non orthogonales)
        raise HTTPException(400, str(e))
    logger.info(f"tuiles/export {fmt}: {tid} -> {p.name} ({p.stat().st_size} o)")
    return {"tid": tid, "format": fmt, "fichier": p.name, "octets": p.stat().st_size,
            "url": f"/api/tiles/{tid}/fichier/{p.name}"}


# ── aperçu auto-tuilé (P3, tâche t115) ───────────────────────────────────────────────────────────────────────────────
#: côté maximal de l'aperçu, en PIXELS : 16 cases de 512 px feraient 8192 px de côté, soit ≈ 200 Mo en RGB pour une
#: image qu'on ne regarde qu'en vignette ; à 4096, un jeu de 512 px garde ses 8 x 8 cases
APERCU_PX_MAX = 4096


def _refaire_jeu(meta: dict) -> dict:
    """Refabrique le jeu à l'identique depuis son meta — mêmes sources, même graine, donc mêmes octets. Le jeu n'est
    pas gardé en mémoire : c'est la recette qui fait foi, pas un cache. Bloquant (PIL) : à appeler hors de la boucle
    d'évènements."""
    a = _charger_matiere(meta.get("source_a") or {}, "matiere_a")
    if meta.get("forme", "carre") != "carre":
        return TO.assembler_forme(a, meta["forme"], int(meta["cote"]))
    b = _charger_matiere(meta.get("source_b") or {}, "matiere_b")
    return TO.assembler_jeu(a, b, meta["jeu"], int(meta["cote"]),
                            int(meta["variantes"]), int(meta["graine"]))


def _bornes_apercu(body: dict, cote: int) -> tuple[int, float, int]:
    """(cases, densite, graine) validés. UNE seule porte pour l'aperçu (P3) et pour les mesures (P4), qui tirent la
    même carte. `densite: 0` est une valeur (carte vide), pas un oubli."""
    body = body if isinstance(body, dict) else {}
    try:
        cases = int(body.get("cases") or 8)
        graine = int(body.get("graine") or 1)
        densite = float(body["densite"]) if body.get("densite") is not None else 0.55
    except (TypeError, ValueError):
        raise HTTPException(400, "cases et graine entiers, densite reelle")
    if not 4 <= cases <= 16:
        raise HTTPException(400, "cases doit tenir entre 4 et 16")
    if not 0.0 <= densite <= 1.0:
        raise HTTPException(400, "densite doit tenir entre 0 et 1")
    if cases * cote > APERCU_PX_MAX:
        raise HTTPException(400, f"{cases} cases de {cote} px depassent {APERCU_PX_MAX} px de cote : "
                                 f"{APERCU_PX_MAX // cote} cases au plus pour ce jeu")
    return cases, densite, graine


def _lire_meta(tid: str) -> dict:
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    return meta


def _carre_seulement(meta: dict, quoi: str) -> None:
    """L'auto-tuilage ne vaut que pour un jeu carré : une forme n'a qu'une tuile, et `composer_carte` y chercherait
    un voisinage absent de `cles`."""
    if meta.get("forme", "carre") != "carre":
        raise HTTPException(400, f"{quoi} ne vaut que pour un jeu carre : une forme {meta['forme']} n a qu une "
                                 f"tuile, sans voisinage")


@router.post("/{tid}/apercu")
async def apercu(tid: str, body: dict):
    """Aperçu auto-tuilé : une grille de terrain tirée au hasard (rejouable), chaque case reçoit la tuile de son
    voisinage et une variante tirée. Écrit `apercu.png` dans le dossier du jeu.
    Body: {cases 4..16, densite 0..1, graine}."""
    meta = _lire_meta(tid)
    _carre_seulement(meta, "l apercu auto-tuile")
    cases, densite, graine = _bornes_apercu(body, int(meta["cote"]))

    def _faire():
        jeu = _refaire_jeu(meta)
        grille = TO.carte_aleatoire(cases, densite, graine)
        img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=True)
        img.save(TS.tileset_dir(tid, create=True) / "apercu.png", format="PNG")
        return grille, plan

    grille, plan = await asyncio.get_running_loop().run_in_executor(None, _faire)
    logger.info(f"tuiles/apercu {cases}x{cases} d={densite} g={graine}: {tid}")
    return {"tid": tid, "cases": cases, "densite": densite, "graine": graine,
            "plan": plan, "grille": grille,
            "url": f"/api/tiles/{tid}/fichier/apercu.png"}


@router.post("/{tid}/mesures")
async def mesures(tid: str, body: dict):
    """Les TROIS chiffres du jeu (raccord, répétition, éclairage), l'éclairage tuile par tuile, un verdict par
    mesure et les seuils. La répétition se lit sur la MÊME carte que l'aperçu à graine égale.
    Body: {graine, cases, densite}. Les mesures sont écrites dans le meta : elles survivent."""
    from app.services import tile_metrics as TM

    meta = _lire_meta(tid)
    _carre_seulement(meta, "la mesure de repetition")
    cases, densite, graine = _bornes_apercu(body, int(meta["cote"]))

    def _faire():
        jeu = _refaire_jeu(meta)
        img, _plan = TO.composer_carte(TO.carte_aleatoire(cases, densite, graine), jeu, graine=graine, boucle=True)
        ecl_max, ecart, par_tuile = TM.eclairage_jeu(jeu)
        return {"raccord": TM.raccord_jeu(jeu), "repetition": TM.repetition_score(img, cases),
                "eclairage_max": ecl_max, "ecart_eclairage": ecart}, par_tuile

    m, par_tuile = await asyncio.get_running_loop().run_in_executor(None, _faire)
    meta["mesures"] = m
    TS.write_meta(tid, meta)
    logger.info(f"tuiles/mesures {tid}: raccord={m['raccord']} repetition={m['repetition']} "
                f"eclairage={m['eclairage_max']}")
    return dict(m, tid=tid, par_tuile=par_tuile, verdict=TM.verdict(m), seuils=dict(TM.SEUILS),
                graine=graine, cases=cases, densite=densite)


@router.get("/{tid}/fichier/{nom}")
async def fichier(tid: str, nom: str):
    try:
        p = TS.chemin_fichier(tid, nom)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not p.is_file():
        raise HTTPException(404, f"fichier absent: {nom}")
    return FileResponse(str(p))


# ── style d'un lieu de la bible (D2, tâche t116 / plan T10-T12) ────────────────────────────────────────────────────
#: gabarit du prompt : la surface d'abord, la contrainte de tuile ensuite, le style du lieu et sa palette en dernier —
#: l'ordre où les modèles d'image pèsent le plus les premiers mots
GABARIT_LIEU = (
    "{surface}, texture de tuile pour {lieu}. {description}{style}"
    "Vue top-down, orthographique, seamless tileable, éclairage diffus uniforme, aucune ombre portée, aucun objet "
    "reconnaissable, aucun texte. {palette}.")


@router.post("/prompt-lieu")
async def prompt_lieu(body: dict | None = None):
    """D2 : un prompt de tuile contraint par la planche et la palette d'un LIEU de la bible. Cette route ne génère
    RIEN — elle formate, gratuitement ; l'image se fait ensuite dans le générateur (POST /api/images/generate, gardé
    par les plafonds). La palette est LUE sur la planche (`board_service._palette_colors`, celle de l'Atelier) : les
    couleurs distinctes trouvées, six au plus — une planche presque unie en donne moins, et c'est vrai."""
    from sqlalchemy import select
    from app.services.board_service import _palette_colors
    from app.services.storage import BibleEntity, async_session_factory
    body = body if isinstance(body, dict) else {}
    eid = str(body.get("entity_id") or "").strip()
    if not eid:
        raise HTTPException(400, "entity_id attendu")
    async with async_session_factory() as session:
        e = (await session.execute(select(BibleEntity).where(BibleEntity.id == eid))).scalar_one_or_none()
    if e is None:
        raise HTTPException(404, f"entité de bible inconnue : {eid}")
    if e.kind != "place":
        raise HTTPException(400, f"« {e.name} » est de sorte {e.kind!r} : seul un lieu contraint un jeu de tuiles")
    palette: list[str] = []
    planche = (e.ref_image or "").strip()
    p = settings.images_path / planche if planche else None
    if p is not None and p.name == planche and p.is_file():
        try:
            couleurs = await asyncio.to_thread(_palette_colors, settings.images_path, [planche], 6)
            palette = ["#%02x%02x%02x" % tuple(c[:3]) for c in couleurs]
        except Exception as err:               # noqa: BLE001 — une planche illisible n'empêche pas le prompt
            logger.warning(f"tuiles/prompt-lieu {eid} : palette illisible ({err})")
            planche = ""
    else:
        planche = ""
    surface = (str(body.get("surface") or "sol").strip() or "sol")[:80]
    prompt = GABARIT_LIEU.format(
        surface=surface, lieu=e.name,
        description=(e.description.strip().rstrip(".") + ". ") if (e.description or "").strip() else "",
        style=(e.style_notes.strip().rstrip(".") + ". ") if (e.style_notes or "").strip() else "",
        palette=("Palette imposée : " + ", ".join(palette)) if palette else "Palette libre")
    return {"entity_id": eid, "lieu": e.name, "planche": planche, "palette": palette, "surface": surface,
            "prompt": prompt}
