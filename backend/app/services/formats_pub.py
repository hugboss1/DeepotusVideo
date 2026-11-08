# -*- coding: utf-8 -*-
"""t439 (lot M6 « Méthodes », 08/11/2026) — le contrôle LOCAL d'une vidéo publicitaire contre le format attendu d'un
réseau (méthodes game-ua-ads, tap-to-install, playable-ads : « livrer chaque pub sur plusieurs réseaux »).

Les bornes ci-dessous sont des RECOMMANDATIONS COURANTES relevées le 08/11/2026 (formats verticaux et carrés des
plateformes), volontairement prudentes ; chaque réseau peut les changer : le rapport le dit. Le contrôle est gratuit
(ffprobe) et ne modifie rien.
"""
from __future__ import annotations

from app.services import briques as BR

RELEVE = "2026-11-08"
RESEAUX: dict[str, dict] = {
    "tiktok": {"libelle": "TikTok", "ratios": ["9:16"], "duree": (5, 60), "cote_min": 720, "octets": 500e6},
    "reels": {"libelle": "Instagram Reels", "ratios": ["9:16"], "duree": (3, 90), "cote_min": 720, "octets": 4e9},
    "shorts": {"libelle": "YouTube Shorts", "ratios": ["9:16", "1:1"], "duree": (1, 60), "cote_min": 720, "octets": 4e9},
    "youtube": {"libelle": "YouTube (in-stream)", "ratios": ["16:9"], "duree": (6, 180), "cote_min": 720, "octets": 4e9},
    "meta_feed": {"libelle": "Meta (fil)", "ratios": ["1:1", "4:5"], "duree": (1, 240), "cote_min": 600, "octets": 4e9},
    "stories": {"libelle": "Stories (Instagram, Facebook)", "ratios": ["9:16"], "duree": (1, 60), "cote_min": 720,
                "octets": 4e9},
}
TOLERANCE_RATIO = 0.02
FPS_MAX = 60


def _ratio(r: str) -> float:
    a, b = r.split(":")
    return float(a) / float(b)


def verifier(chemin: str, reseaux: list[str] | None = None) -> dict:
    """{chemin, infos, reseaux: {id: {libelle, ok, ecarts: [...], conseils: [...]}}, releve}. Un écart bloque
    (ratio, durée, côté, taille) ; un conseil prévient (pas de son, cadence > 60)."""
    from app.services import finition as FI
    from app.services import previs_plan as PV
    p = BR.confiner(chemin)
    if BR.nature(p) != "video":
        raise ValueError("Le format d'une pub se vérifie sur une vidéo.")
    ids = list(reseaux or RESEAUX)
    inconnus = [r for r in ids if r not in RESEAUX]
    if inconnus:
        raise ValueError(f"Réseau inconnu : {', '.join(inconnus)}")
    i = PV.infos_clip(p)
    w, h, s = i.get("largeur"), i.get("hauteur"), i.get("secondes")
    if not w or not h or not s:
        raise ValueError("Vidéo illisible.")
    son = FI.a_une_piste_audio(p)
    ratio = w / h
    out = {}
    for rid in ids:
        r = RESEAUX[rid]
        ecarts, conseils = [], []
        if not any(abs(ratio - _ratio(x)) / _ratio(x) <= TOLERANCE_RATIO for x in r["ratios"]):
            ecarts.append(f"ratio {w}x{h} ≠ {' ou '.join(r['ratios'])}")
        lo, hi = r["duree"]
        if s < lo - 0.05 or s > hi + 0.05:
            ecarts.append(f"durée {round(s, 2)} s hors de {lo}-{hi} s")
        if min(w, h) < r["cote_min"]:
            ecarts.append(f"petit côté {min(w, h)} px < {r['cote_min']} px")
        if (i.get("octets") or 0) > r["octets"]:
            ecarts.append(f"fichier {round(i['octets'] / 1e6, 1)} Mo > {round(r['octets'] / 1e6)} Mo")
        if not son:
            conseils.append("aucune piste son : la plupart des pubs se regardent son coupé, mais une musique aide")
        if (i.get("fps") or 0) > FPS_MAX:
            conseils.append(f"cadence {i['fps']} i/s > {FPS_MAX}")
        out[rid] = {"libelle": r["libelle"], "ok": not ecarts, "ecarts": ecarts, "conseils": conseils}
    return {"chemin": str(p.relative_to(BR.racine())).replace("\\", "/"),
            "infos": {"largeur": w, "hauteur": h, "secondes": round(s, 3), "fps": i.get("fps"), "son": son,
                      "octets": i.get("octets")},
            "reseaux": out, "releve": RELEVE,
            "avertissement": "Recommandations courantes relevées le " + RELEVE + " ; vérifie les règles du réseau avant "
                             "de diffuser."}
