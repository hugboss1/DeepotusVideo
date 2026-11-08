# -*- coding: utf-8 -*-
"""t435 (lot M2 « Méthodes », agent Monteur, 08/11/2026) — B5 : les TEMPS FORTS d'une musique, pour caler les coupes
sur ses accents mesurés (conception docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4).

Python pur (numpy n'est pas dans le python embarqué), local et gratuit :
  1. ffmpeg décode en mono 11 025 Hz, PCM 16 bits ;
  2. énergie logarithmique par trame (fenêtre 512, pas 256 ≈ 23 ms), puis FORCE D'ATTAQUE = hausse d'énergie (redressée
     à zéro) d'une trame à l'autre ;
  3. ATTAQUES = maxima locaux (±3 trames) au-dessus d'un seuil adaptatif (moyenne glissante d'1 s + 1,5 écart-type),
     espacés d'au moins 100 ms ;
  4. TEMPO = l'autocorrélation (normée, force lissée) sur les retards de 60 à 190 BPM, pondérée par un a priori autour
     de 120 BPM (évite le saut d'octave) ; GRILLE = la phase qui fait tomber le plus de force sur les temps ;
  5. ACCENTS = les attaques nettement plus fortes (≈ 5 dB au-dessus de la médiane, sinon le quart supérieur).
Les instants sont ceux du CENTRE de la trame (k × PAS + FENETRE / 2).
`caler(analyse, …)` propose des plans dont les bords tombent sur les accents (puis sur les temps).
"""
from __future__ import annotations

import math
import subprocess
from array import array
from pathlib import Path

TAUX = 11025
FENETRE = 512
PAS = 256
BPM_MIN, BPM_MAX = 60.0, 190.0
ECART_MIN_S = 0.10
ACCENT_LOG = 0.5            # un accent dépasse la médiane des attaques de 0,5 en log10 d'énergie (≈ 5 dB)
MAX_DUREE_S = 900


def decoder(path: Path) -> array:
    """Les échantillons mono 16 bits à TAUX Hz (900 s au plus). RuntimeError si ffmpeg échoue ou ne rend rien."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", str(MAX_DUREE_S), "-vn", "-ac", "1",
                        "-ar", str(TAUX), "-f", "s16le", "-"], capture_output=True, timeout=600)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("Aucune piste son lisible dans ce fichier.")
    a = array("h")
    a.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    return a


def force_attaque(ech) -> list[float]:
    """PUR — la force d'attaque par trame (hausse d'énergie log redressée)."""
    n = (len(ech) - FENETRE) // PAS + 1 if len(ech) >= FENETRE else 0
    energie = []
    for k in range(n):
        s = 0
        base = k * PAS
        for i in range(base, base + FENETRE, 2):            # un échantillon sur deux : assez pour l'énergie
            v = ech[i]
            s += v * v
        energie.append(math.log10(1.0 + s / (FENETRE / 2)))
    return [0.0] + [max(0.0, energie[k] - energie[k - 1]) for k in range(1, n)] if n else []


def attaques(force: list[float]) -> list[tuple[int, float]]:
    """PUR — (trame, force) des attaques : maxima locaux au-dessus du seuil adaptatif, espacés de 100 ms."""
    n = len(force)
    demi = max(1, int(0.5 * TAUX / PAS))
    ecart = max(1, int(ECART_MIN_S * TAUX / PAS))
    out: list[tuple[int, float]] = []
    for k in range(n):
        v = force[k]
        if v <= 0:
            continue
        a, b = max(0, k - 3), min(n, k + 4)
        if v < max(force[a:b]):
            continue
        w = force[max(0, k - demi): min(n, k + demi + 1)]
        m = sum(w) / len(w)
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / len(w))
        if v < m + 1.5 * sd:
            continue
        if out and k - out[-1][0] < ecart:
            if v > out[-1][1]:
                out[-1] = (k, v)
            continue
        out.append((k, v))
    return out


def tempo(force: list[float]) -> tuple[float | None, int, int]:
    """PUR — (bpm, retard en trames, phase en trames) par autocorrélation ; (None, 0, 0) si trop court."""
    fps = TAUX / PAS
    rmin, rmax = int(fps * 60 / BPM_MAX), int(fps * 60 / BPM_MIN) + 1
    if len(force) < rmax * 4:
        return None, 0, 0
    # lissage triangulaire (±1 trame) : un clic qui tombe à cheval sur deux trames garde sa corrélation
    lisse = [0.25 * force[i - 1] + 0.5 * force[i] + 0.25 * force[i + 1] for i in range(1, len(force) - 1)]
    m = sum(lisse) / len(lisse)
    f = [x - m for x in lisse]
    meilleur, retard = -1e18, 0
    for r in range(rmin, rmax + 1):
        s = sum(f[i] * f[i + r] for i in range(len(f) - r)) / (len(f) - r)
        bpm = 60 * fps / r
        s *= math.exp(-0.5 * (math.log2(bpm / 120.0) / 0.9) ** 2)     # a priori : les tempos usuels autour de 120
        if s > meilleur:
            meilleur, retard = s, r
    if retard <= 0:
        return None, 0, 0
    phase = max(range(retard), key=lambda p: sum(force[p::retard]))
    return round(60 * fps / retard, 1), retard, phase


def seuil_accents(forces: list[float]) -> float:
    """PUR — la force à partir de laquelle une attaque est un ACCENT : la médiane + ACCENT_LOG (la force est une hausse
    d'énergie en log10 : +0,5 ≈ +5 dB) quand cela isole une minorité nette (au plus la moitié), sinon le quart
    supérieur (une musique égale n'a pas d'accent marqué)."""
    if not forces:
        return 0.0
    f = sorted(forces)
    med = f[len(f) // 2]
    fort = [x for x in f if x >= med + ACCENT_LOG]
    if 0 < len(fort) <= len(f) // 2:
        return fort[0]
    return f[int(len(f) * 0.75)]


def analyser(path: Path) -> dict:
    """{duree_s, bpm, temps_s, attaques: [{t, force}], accents: [{t, force}]} d'un fichier son ou vidéo."""
    ech = decoder(Path(path))
    duree = round(len(ech) / TAUX, 3)
    f = force_attaque(ech)
    at = attaques(f)
    bpm, retard, phase = tempo(f)
    fps = TAUX / PAS
    centre = FENETRE / 2 / TAUX
    temps = [round(k / fps + centre, 3) for k in range(phase, len(f), retard)] if retard else []
    forces = sorted(v for _k, v in at)
    seuil = seuil_accents(forces)
    liste = [{"t": round(k / fps + centre, 3), "force": round(v, 4)} for k, v in at]
    return {"duree_s": duree, "bpm": bpm, "temps_s": temps[:2000], "attaques": liste[:2000],
            "accents": [x for x in liste if x["force"] >= seuil][:500]}


def caler(analyse: dict, *, n_plans: int = 0, durees: list[float] | None = None, min_s: float = 0.8,
          tolerance_s: float = 0.5) -> list[dict]:
    """PUR — des plans {debut, fin, cale} dont les bords tombent sur les accents :
    - `durees` : chaque coupe visée (cumul des durées) est tirée vers l'accent le plus proche à ±tolerance, sinon vers
      le temps le plus proche, sinon laissée (cale « libre ») ;
    - `n_plans` : les n-1 accents les plus forts espacés d'au moins `min_s`, dans l'ordre du temps.
    ValueError si ni l'un ni l'autre, ou si la musique est trop courte."""
    fin = float(analyse.get("duree_s") or 0.0)
    if fin <= 0:
        raise ValueError("Musique vide : impossible de caler des coupes.")
    accents = [a["t"] for a in analyse.get("accents") or []]
    temps = list(analyse.get("temps_s") or [])
    coupes: list[tuple[float, str]] = []
    if durees:
        cible = 0.0
        for d in durees[:-1] if len(durees) > 1 else []:
            cible += max(0.1, float(d))
            if cible >= fin:
                break
            choix, cale = cible, "libre"
            proches = [a for a in accents if abs(a - cible) <= tolerance_s]
            if proches:
                choix, cale = min(proches, key=lambda a: abs(a - cible)), "accent"
            else:
                pt = [t for t in temps if abs(t - cible) <= tolerance_s]
                if pt:
                    choix, cale = min(pt, key=lambda t: abs(t - cible)), "temps"
            if not coupes or choix - coupes[-1][0] >= min_s:
                coupes.append((choix, cale))
            cible = choix
    elif n_plans and n_plans > 1:
        par_force = sorted(analyse.get("accents") or [], key=lambda a: -a["force"])
        pris: list[float] = []
        for a in par_force:
            t = a["t"]
            if t < min_s or fin - t < min_s or any(abs(t - p) < min_s for p in pris):
                continue
            pris.append(t)
            if len(pris) >= n_plans - 1:
                break
        coupes = [(t, "accent") for t in sorted(pris)]
    else:
        raise ValueError("Donne un nombre de plans ou leurs durées.")
    bords = [(0.0, "debut")] + coupes + [(fin, "fin")]
    return [{"debut": round(bords[i][0], 3), "fin": round(bords[i + 1][0], 3), "cale": bords[i + 1][1]}
            for i in range(len(bords) - 1)]
