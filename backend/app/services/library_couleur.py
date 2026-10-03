# -*- coding: utf-8 -*-
"""Tâche #81 (03/10/2026, plan-library T11) — la COULEUR DOMINANTE des images de la Bibliothèque.

Décision de l'utilisateur (03/10) : calculée EN TÂCHE DE FOND après le démarrage (jamais bloquant — ≈ 31 s mesurées
sur les 1009 images réelles ; le plan la mettait DANS le reconcilier du démarrage, attendu par le lifespan) et pour
chaque nouvelle image ; 12 teintes + « neutre » ; la puce « Teinte » filtre la grille, la fiche montre la pastille.
Méthode (celle du plan, mesurée) : vignette 128 px → quantize(8, MEDIANCUT) → la couleur la plus fréquente ; nommée
par sa teinte HLS en 12 secteurs de 30°, « neutre » si peu saturée ou presque noire / blanche. La transparence compte
pour rien (un sticker détouré n'est pas « noir »).
"""
from __future__ import annotations

import asyncio
import colorsys
from pathlib import Path

from loguru import logger

from app.config import settings

TEINTES = ("rouge", "orange", "jaune", "vert-jaune", "vert", "émeraude", "cyan", "azur", "bleu", "violet",
           "magenta", "rose")
NEUTRE = "neutre"
_TACHES: set = set()
#: armé par le DÉMARRAGE de l'application (lifespan) : la couleur des nouvelles images ne part en tâche de fond que
#: dans un serveur qui tourne. MESURÉ (03/10) : sans ce drapeau, un banc qui écrit la base en sqlite3 SYNCHRONE
#: pendant qu'une tâche tient le verrou d'écriture bloquait la boucle qui devait le rendre (« database is locked »).
ACTIF = False


def nommer(rgb: tuple[int, int, int]) -> str:
    r, g, b = (c / 255 for c in rgb[:3])
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    # la saturation HLS GONFLE près du blanc et du noir (#f2efe9, un crème, y vaut 0,25 : « orange », vu sur la
    # preuve) — on exige aussi une chroma absolue (max − min) d'au moins 0,10
    if s < 0.18 or l < 0.06 or l > 0.94 or (max(r, g, b) - min(r, g, b)) < 0.10:
        return NEUTRE
    return TEINTES[int(((h * 360 + 15) % 360) // 30)]


def dominante(chemin: Path) -> tuple[str, str] | None:
    """(#rrggbb, teinte) de l'image, None si illisible."""
    try:
        from PIL import Image
        with Image.open(chemin) as im:
            im.thumbnail((128, 128))
            rgba = im.convert("RGBA")
            fond = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
            visible = rgba.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
            # (une image ENTIÈREMENT transparente : aucun pixel compté, max() lève, l'except rend None)
            rgb = Image.composite(rgba, fond, visible).convert("RGB")
            q = rgb.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
            pal = q.getpalette()
            # on ne compte que les pixels VISIBLES
            comptes: dict[int, int] = {}
            for idx, a in zip(q.getdata(), visible.getdata()):
                if a:
                    comptes[idx] = comptes.get(idx, 0) + 1
            i = max(comptes, key=comptes.get)
            c = tuple(pal[i * 3:i * 3 + 3])
    except Exception:  # noqa: BLE001 — une image illisible n'a pas de couleur
        return None
    return "#%02x%02x%02x" % c, nommer(c)


async def remplir(noms: list[str] | None = None, lot: int = 50) -> int:
    """Calcule et écrit la couleur des images SANS couleur (ou de celles nommées). Le calcul part en thread, par lots,
    la boucle d'événements n'est jamais gelée. Rend le nombre d'images coloriées."""
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    async with async_session_factory() as s:
        q = select(LibraryAsset.filename).where(LibraryAsset.kind == "image")
        q = q.where(LibraryAsset.filename.in_(noms)) if noms else q.where(LibraryAsset.couleur.is_(None))
        a_faire = [r[0] for r in (await s.execute(q)).fetchall()]
    fait = 0
    for i in range(0, len(a_faire), lot):
        part = a_faire[i:i + lot]
        res = await asyncio.to_thread(lambda p=part: {n: dominante(settings.images_path / n) for n in p})
        lignes = [{"filename": n, "couleur": v[0], "teinte": v[1]} for n, v in res.items() if v is not None]
        if lignes:   # UNE mise à jour groupée par lot : le verrou d'écriture est tenu le moins longtemps possible
            from sqlalchemy import update
            async with async_session_factory() as s:
                await s.execute(update(LibraryAsset), lignes)
                await s.commit()
            fait += len(lignes)
    return fait


def en_fond(noms: list[str] | None = None) -> None:
    """Lance `remplir` sans l'attendre (démarrage, nouvelle image). Sans boucle en cours, ou hors d'un serveur démarré
    (ACTIF faux) : rien."""
    if not ACTIF:
        return
    try:
        boucle = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def _go():
        try:
            n = await remplir(noms)
            if n and not noms:
                logger.info(f"library_couleur : {n} image(s) coloriée(s) en tâche de fond")
        except Exception as e:  # noqa: BLE001 — la couleur est un à-côté
            logger.warning(f"library_couleur ignorée : {e}")

    t = boucle.create_task(_go())
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
