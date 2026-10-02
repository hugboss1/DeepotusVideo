"""Tâche #66 PR B (plan chapitres T18-T19, 02/10/2026) — un chapitre, des SORTIES vers le Montage. PUR : on lit le
manifeste de l'animatique et on rend les clips d'un projet de Montage ; la route copie et enregistre.

DÉCISIONS DE L'UTILISATEUR (02/10) : film et reel (gratuits) ; un NOUVEAU projet nommé — jamais la timeline en cours ;
un INSTANTANÉ d'animatique.mp4 (un nouveau rendu ne change pas un projet sous vos pieds), enregistré comme un rendu ;
la voix témoin en piste A1.
« Livre » est abandonné (les exports de #65 le font), « épisode » viendra sans rendu (PR C).

Ce que le plan du 03/09 faisait faux : il recalculait les durées sans les voix (des clips de 4 s pour des voix de 2,7 s),
écrivait la timeline COURANTE hors du verrou d'écriture, pointait les clips vivants du dossier de l'animatique (purgés
au rendu suivant) et perdait la voix (les clips par plan sont muets).
"""
from __future__ import annotations

NATURES = {"film": "Film — tous les plans, dans l'ordre", "reel": "Reel — les plans les plus forts, 30 s au plus"}
REEL_MAX_S = 30.0
ENERGIE_DEFAUT = 3


def a_jour(manifeste: dict | None, shots: list[dict]) -> bool:
    """Le manifeste décrit-il le storyboard ACTUEL (mêmes plans, même ordre) ?"""
    if not manifeste:
        return False
    actuels = [s.get("id") for s in sorted(shots, key=lambda x: x.get("idx", 0))]
    return [p.get("shot_id") for p in manifeste.get("plans") or []] == actuels


def choisir(manifeste: dict, nature: str, reel_max: float = REEL_MAX_S) -> list[dict]:
    """Les plans retenus, dans l'ORDRE du chapitre, chacun avec `debut` = sa place dans animatique.mp4. Film : tous.
    Reel : les plus énergiques d'abord (à énergie égale, le plus tôt), tant que la durée cumulée tient dans `reel_max`
    — au moins un plan."""
    plans, t = [], 0.0
    for p in manifeste.get("plans") or []:
        plans.append(dict(p, debut=round(t, 3)))
        t += float(p.get("dur") or 0)
    if nature == "film":
        return plans
    if nature != "reel":
        raise ValueError(f"nature inconnue : {nature}")
    rang = sorted(range(len(plans)), key=lambda i: (-(plans[i].get("energie") or ENERGIE_DEFAUT), i))
    pris, total = [], 0.0                     # dans l'ordre de l'ÉNERGIE ; remis dans l'ordre du chapitre au retour
    for i in rang:
        d = float(plans[i].get("dur") or 0)
        if pris and total + d > reel_max:
            continue
        pris.append(i)
        total += d
    return [plans[i] for i in sorted(pris)]


def clips_montage(plans: list[dict], job_id: str) -> tuple[list[dict], float]:
    """(clips, durée) d'un projet de Montage. UNE source — l'instantané d'animatique.mp4, enregistré comme un rendu
    (`job_id` : la seule sorte de source vidéo que l'éditeur sait prévisualiser) — découpée plan par plan : V1 la vidéo
    depuis `debut`, A1 la voix témoin du MÊME instant (la piste son de l'animatique), quand le plan en a une."""
    clips, t = [], 0.0
    src = {"job_id": job_id}
    for k, p in enumerate(plans):
        d = round(float(p.get("dur") or 0), 3)
        lib = f"Plan {int(p.get('idx', k)) + 1}" + (f" · {p['texte'][:36]}" if p.get("texte") else "")
        clips.append({"tr": "v1", "id": f"v1_ch{k:03d}", "label": lib[:48], "src": dict(src), "srcIn": p["debut"],
                      "start": round(t, 3), "end": round(t + d, 3), "transition": "cut", "transition_s": 0.0})
        if p.get("voix"):
            clips.append({"tr": "a1", "id": f"a1_ch{k:03d}", "label": f"{lib[:40]} · voix témoin", "src": dict(src),
                          "srcIn": p["debut"], "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return clips, round(t, 3)
