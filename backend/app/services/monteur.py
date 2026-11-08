# -*- coding: utf-8 -*-
"""t435 (lot M2 « Méthodes », 08/11/2026) — les gestes LOCAUX de l'agent métier MONTEUR (B5 de la conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4), tous gratuits :

  temps_forts(chemin)                       les temps forts mesurés d'une musique (musique_temps.analyser)
  caler_coupes(chemin, n_plans | durees)    des plans dont les bords tombent sur les accents
  poser_titre(video, texte, debut, fin, …)  un titre GRAVÉ PAR L'APP (gabarits des titres du Montage, fontes
                                            embarquées, libass) — jamais dessiné par un modèle ; la vidéo d'origine
                                            n'est pas touchée, une copie titrée est rangée dans <données>/briques/monteur.
Les chemins passent par briques.confiner (dossier de données seulement).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4

from app.services import briques as BR
from app.services import musique_temps as MU


def temps_forts(chemin: str) -> dict:
    p = BR.confiner(chemin)
    if BR.nature(p) not in ("son", "video"):
        raise ValueError("Les temps forts se mesurent sur un son ou une vidéo.")
    a = MU.analyser(p)
    a["chemin"] = str(p.relative_to(BR.racine())).replace("\\", "/")
    return a


def caler_coupes(chemin: str, n_plans: int = 0, durees: list | None = None) -> dict:
    a = temps_forts(chemin)
    if durees is not None and not (isinstance(durees, list) and all(isinstance(d, (int, float)) and not isinstance(d, bool)
                                                                    for d in durees)):
        raise ValueError("Les durées des plans sont des nombres de secondes.")
    n = int(n_plans) if isinstance(n_plans, int) and not isinstance(n_plans, bool) else 0
    if n > 200 or (durees and len(durees) > 200):
        raise ValueError("200 plans au plus.")
    plans = MU.caler(a, n_plans=n, durees=[float(d) for d in durees] if durees else None)
    return {"chemin": a["chemin"], "bpm": a["bpm"], "duree_s": a["duree_s"], "plans": plans,
            "sur_accent": sum(1 for p in plans if p["cale"] == "accent")}


def gabarits() -> list[str]:
    from app.services import titles as TI
    return list(TI.TEMPLATES)


def poser_titre(video: str, texte: str, debut: float, fin: float, gabarit: str = "tiers_inferieur",
                sous_titre: str = "") -> dict:
    from app.services import previs_plan as PV
    from app.services import subtitle_service as SS
    from app.services import titles as TI
    p = BR.confiner(video)
    if BR.nature(p) != "video":
        raise ValueError("Le titre se pose sur une vidéo.")
    if gabarit not in TI.TEMPLATES:
        raise ValueError("Gabarit de titre inconnu.")
    spec = TI.title_spec({"start": debut, "end": fin,
                          "title": {"text": texte, "template": gabarit, "sub": sous_titre or ""}})
    if not spec:
        raise ValueError("Titre vide ou horaires invalides (la fin doit suivre le début).")
    i = PV.infos_clip(p)
    if not i.get("largeur") or not i.get("hauteur"):
        raise ValueError("Vidéo illisible.")
    dossier = BR.racine() / "briques" / "monteur"
    dossier.mkdir(parents=True, exist_ok=True)
    stem = f"{p.stem[:50]}_titre_{uuid4().hex[:6]}"
    ass = TI.to_ass_title(spec, (int(i["largeur"]), int(i["hauteur"])), stem, dest=dossier)
    if not ass:
        raise RuntimeError("Le titre n'a pas pu être écrit.")
    dest = dossier / f"{stem}.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf", SS.subtitles_filter(str(ass)),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy",
                        str(dest)], capture_output=True, text=True, timeout=600)
    try:
        Path(ass).unlink(missing_ok=True)
    except OSError:
        pass
    if r.returncode != 0:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg (titre) : {(r.stderr or '').strip()[-300:]}")
    return {"chemin": str(dest.relative_to(BR.racine())).replace("\\", "/"), "titre": spec,
            "infos": PV.infos_clip(dest)}
