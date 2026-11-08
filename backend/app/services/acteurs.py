# -*- coding: utf-8 -*-
"""t438 (lot M5 « Méthodes », 08/11/2026) — les contrôles LOCAUX de l'agent métier DIRECTEUR D'ACTEURS (méthodes
one-more-take, dotties-voice, babel-tavern, a-cast-of-one : « la transcription vérifie chaque réplique », « des
invites calées à la seconde »). Gratuits, sans réseau :

  controler_replique(attendu, obtenu)   écart mot à mot entre le texte voulu et le texte DIT (transcription déjà faite,
                                        sous-titres, ou texte collé) : taux d'erreur (WER), mots manquants, ajoutés,
                                        remplacés — accents, casse et ponctuation ignorés ;
  segments_voix(chemin, texte="")       les passages parlés d'un son ou d'une vidéo (silencedetect), leur durée totale,
                                        les pauses ; avec le texte : le débit en mots par minute.
La transcription elle-même est PAYANTE (Sous-titres) : l'agent ne la lance jamais.
"""
from __future__ import annotations

import re
import unicodedata

from app.services import briques as BR

MAX_MOTS = 3000


def mots(texte: str) -> list[str]:
    """PUR — les mots normalisés : minuscules, sans accents, sans ponctuation (l'apostrophe sépare : « l'agent »)."""
    t = unicodedata.normalize("NFKD", str(texte or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.findall(r"[a-z0-9]+", t)[:MAX_MOTS]


def controler_replique(attendu: str, obtenu: str) -> dict:
    """PUR — l'alignement mot à mot (distance d'édition) : {wer, mots_attendus, manquants, ajoutes, remplaces, verdict}.
    verdict « exact » (0), « proche » (WER ≤ 10 %), « ecart » sinon. ValueError si le texte attendu est vide."""
    a, b = mots(attendu), mots(obtenu)
    if not a:
        raise ValueError("Donne le texte attendu de la réplique.")
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    manquants, ajoutes, remplaces = [], [], []
    i, j = n, m
    # remontée : à coût égal, d'abord l'accord exact, puis l'ajout ou l'oubli, et le remplacement en dernier (un mot
    # ajouté en fin de phrase n'est pas « remplacé » par décalage)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and d[i][j] == d[i - 1][j - 1]:
            i, j = i - 1, j - 1
        elif j > 0 and d[i][j] == d[i][j - 1] + 1:
            ajoutes.append(b[j - 1])
            j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            manquants.append(a[i - 1])
            i -= 1
        else:
            remplaces.append([a[i - 1], b[j - 1]])
            i, j = i - 1, j - 1
    wer = round(d[n][m] / n, 4)
    return {"wer": wer, "mots_attendus": n, "mots_obtenus": m, "manquants": manquants[::-1][:50],
            "ajoutes": ajoutes[::-1][:50], "remplaces": remplaces[::-1][:50],
            "verdict": "exact" if wer == 0 else "proche" if wer <= 0.10 else "ecart"}


def segments_voix(chemin: str, texte: str = "", seuil_db: float = -33.0, silence_min_s: float = 0.25) -> dict:
    """Les passages parlés (le complément des silences de silencedetect), la parole totale, les pauses ; avec `texte`,
    le débit en mots par minute de parole. Local, gratuit."""
    from app.services import previs_plan as PV
    from app.services import transcribe_service as TS
    p = BR.confiner(chemin)
    if BR.nature(p) not in ("son", "video"):
        raise ValueError("On mesure la voix d'un son ou d'une vidéo.")
    total = float(PV.infos_clip(p).get("secondes") or TS.probe_duration(p) or 0.0)
    if total <= 0:
        raise ValueError("Durée illisible.")
    silences = TS.detect_silences(p, noise_db=seuil_db, min_silence_s=silence_min_s)
    parle, t = [], 0.0
    for s0, s1 in sorted(silences):
        if s0 - t > 0.05:
            parle.append([round(t, 3), round(s0, 3)])
        t = max(t, s1)
    if total - t > 0.05:
        parle.append([round(t, 3), round(total, 3)])
    duree_parole = round(sum(b - a for a, b in parle), 3)
    pauses = [round(b - a, 3) for (_a, a), (b, _b) in zip(parle, parle[1:])]
    n = len(mots(texte)) if texte else 0
    return {"chemin": str(p.relative_to(BR.racine())).replace("\\", "/"), "duree_s": round(total, 3),
            "segments": parle[:500], "parole_s": duree_parole, "pauses_s": pauses[:500],
            "pause_max_s": max(pauses) if pauses else 0.0,
            "mots_par_minute": round(n / (duree_parole / 60.0), 1) if n and duree_parole > 0 else None}
