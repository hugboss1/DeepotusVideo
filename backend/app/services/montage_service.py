# -*- coding: utf-8 -*-
"""Montage (écran 07) → pipeline de rendu ffmpeg réel.

Câblage « timeline → rendu » du handoff son_vfx_montage :

  GET  /api/montage/project   Timeline initiale construite depuis les VRAIS
                              assets de la Bibliothèque (rendus + uploads en
                              V1, voix off en A1, musique en A2), durées
                              ffprobe. {has_assets:false} si la Bibliothèque
                              est vide → l'écran garde sa démo.
  POST /api/montage/render    Rend la timeline postée en tâche de fond
                              (JobRecord provider="montage", poll
                              GET /api/jobs/{id}) — preview 480p (gratuit,
                              rapide) ou final 1080. Sortie dans
                              outputs/videos/, visible en Bibliothèque et
                              attachable à un post du Scheduler (job_id).
  POST /api/montage/save      Sauvegarde de la timeline ÉDITÉE (autosave de
                              l'écran 07) : le modèle CLIENT complet — textes
                              de narration, gains/fondus/automation,
                              transformations/trajectoires, vitesses, effets —
                              écrit ATOMIQUEMENT (tmp + os.replace) dans
                              montage_saved.json au répertoire de données
                              (settings.images_path.parent, à côté d'audio/).
  DELETE /api/montage/save    Efface la sauvegarde ; GET /project reconstruit
                              alors depuis la Bibliothèque.
                              GET /project sert d'abord la sauvegarde si elle
                              existe (saved:true, sources vérifiées — clip à
                              source disparue retiré avec saved_pruned).

Mécanique vidéo : segments V1 ordonnés (src_in via -ss, durée exacte
tpad/trim), enchaînés par xfade (map _XFADE de template_service, « cut » =
fondu 1 image). Audio : clips A1/A3 posés à leur position timeline (adelay),
musique A2 en boucle coupée à la durée, gains dB par canal, mixage PAR CLIP
optionnel (gain −24..+12 dB multiplié au gain de bus, fondus afade 0..3 s à
courbe lin/douce/expo/log par côté — lin n'émet pas de curve= ;
musique : fade_in au démarrage, fade_out calé sur la fin du rendu),
automation de volume par clip (volume_points [{t, db}] → volume=expr
:eval=frame, interpolation linéaire en dB multipliée aux gains — t local au
clip, temps global du rendu pour la musique bouclée), ducking
auto (sidechaincompress musique sous dialogue), « Maître de durée » = la vidéo
gèle sa dernière image plutôt que couper la voix. Les trous entre clips V1
se referment au rendu (concat séquentiel) — le projet initial est généré
sans trous, donc timeline et rendu coïncident.

Piste V2 : overlays vidéo/image posés à leur position timeline (overlay
enable='between(t,…)', cover du canvas, alpha préservé pour les PNG,
opacité optionnelle), appliqués après le maître de durée. Transformation
optionnelle par overlay (x/y : centre en fraction du canvas, scale :
largeur = scale·W hauteur auto, rotate : degrés sur fond transparent) —
sans AUCUN de ces champs la chaîne cover historique reste strictement
inchangée. Keyframes de position par overlay (motion_points [{t, x, y,
rotate?}], max 8) : x/y du filtre overlay deviennent des interpolations
linéaires par morceaux du temps global (t local converti via start), la
rotation s'anime en horloge locale du flux — l'échelle reste statique
(pas de keyframe d'échelle). Effets par clip :
moteur Effects/Mask existant (effects_engine.build_chain) sur chaque
segment V1 — catalogue exposé par GET /api/montage/effects. src_in audio :
les clips A1/A3 lisent leur source à partir de srcIn (atrim décalé).
Vitesse par clip V1 (speed 0.25..4, défaut 1) : la durée TIMELINE du clip ne
change jamais (offsets xfade, trous et adelay audio intacts) — la fenêtre
SOURCE consommée devient durée×speed et le flux est remis à la durée
timeline par setpts=PTS/speed inséré AVANT la normalisation fps ; AUCUN
atempo (l'audio des plans V1 n'entre pas dans le graphe — le clip A1 « son
du plan » garde sa vitesse, l'UI signale la désynchronisation).

Piste S1 (sous-titres) : le payload de rendu porte une clé `subtitles`
HORS du tableau `clips` — `{style, segments:[{start,end,text,words?}]}`. Le
style, exprimé dans le vocabulaire du panneau, est converti par
`subtitle_ui.ui_to_style` AVEC le canevas réel du rendu, puis
`subtitle_service.to_ass` écrit un fichier ASS (style + karaoké `\\k` par mot)
que ffmpeg grave par le filtre `subtitles=` en DERNIER maillon de la chaîne
vidéo (après les overlays V2, donc au-dessus de tout, extension du maître de
durée comprise). `fontsdir` pointe les fontes EMBARQUÉES : sans lui libass
retomberait en silence sur une fonte système et le rendu cesserait de
ressembler à l'aperçu. Clé absente : commande historique intacte.

Tout est local ffmpeg → 0 crédit, l'UI l'affiche avant déclenchement
(règle produit). Trous V1 : rendus en NOIR (segments lavfi à leur durée
timeline, compensée du chevauchement xfade des frontières pour que le clip
suivant retombe sur sa position — l'audio posé en adelay reste aligné).
"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
from datetime import datetime as _dt
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.models.schemas import JobStatus
from app.services import sfx_service
from app.services.composition_service import FFMPEG_TIMEOUT_S
from app.services.storage import JobRecord, async_session_factory

router = APIRouter()

# Transitions montage → (nom xfade, durée imposée ou None) — même table que
# build_sequential_command (template_service), recopiée pour rester autonome.
_XFADE = {
    "cut": ("fade", 0.04),
    "crossfade": ("fade", None),
    "xfade": ("fade", None),
    "fade": ("fade", None),
    "dissolve": ("dissolve", None),
    "fadeblack": ("fadeblack", None),
    "glitch": ("pixelize", None),
    "slide": ("slideleft", None),
    "flash": ("fadewhite", None),
}

# 4:5 était proposé par les menus du bundle et géré par animation_service,
# mais absent d'ici : un montage en 4:5 retombait silencieusement en 9:16.
_CANVAS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
           "4:5": (1080, 1350)}
_MUSIC_HINT = ("theme", "music", "bgm", "track", "musique", "instrumental")

# P1 : pistes dynamiques. `tracks` du payload, du HAUT vers le BAS de la
# timeline (l'ordre de SVM_TRACKS). Absent → table historique, commande
# octet pour octet identique. `layer` = rang de composition des pistes vidéo
# d'overlay, 0 = juste au-dessus de V1 : la piste listée le plus HAUT est
# composée en DERNIER, donc au-dessus de tout. V1 reste la piste de base.
_LEGACY_TRACKS = [{"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                  {"id": "a1", "kind": "audio", "bus": "dialogue"},
                  {"id": "a2", "kind": "audio", "bus": "musique", "loop": True},
                  {"id": "a3", "kind": "audio", "bus": "sfx"}]
_BUSES = ("dialogue", "musique", "sfx")


def _tracks_meta(raw) -> dict:
    """{id: {kind, bus, loop, layer}} — la LOI de classement des clips.

    `raw` est la clé `tracks` du payload : une liste de {id, kind, bus?,
    loop?} dans l'ordre d'affichage, du HAUT vers le BAS. Absente ou vide
    ⇒ `_LEGACY_TRACKS`, et tout le reste du service se comporte comme
    avant, argument pour argument.

    `kind` manquant se déduit de l'initiale (a… audio, s… sous-titres,
    sinon vidéo) ; `bus` inconnu retombe sur `sfx` (jamais de bus inventé
    dans le mixage) ; `loop` n'a de sens que sur une piste audio.
    `layer` ne concerne que les pistes VIDÉO autres que v1 : la dernière
    listée (la plus BASSE à l'écran) prend 0, la première listée le rang le
    plus haut — `_build_montage_command` composant par `layer` croissant,
    la piste du haut passe en dernier, donc au-dessus."""
    rows = raw if isinstance(raw, list) and raw else _LEGACY_TRACKS
    meta, ov = {}, []
    for t in rows:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        # L'identifiant est À LA FOIS la clé de `meta` et la valeur `tr`
        # que portent les clips. Le TRONQUER d'un côté et pas de l'autre
        # faisait disparaître les clips d'une piste au nom long en donnant
        # l'illusion qu'elle était déclarée (mesuré : id
        # "averyveryverylongtrackid" → clé "averyver", et
        # meta.get("averyveryverylongtrackid") = None). On BORNE donc au
        # lieu de tronquer : au-delà de 8 caractères la piste n'est pas
        # déclarée du tout, et ses clips sont ignorés comme ceux de
        # n'importe quelle piste inconnue.
        tid = str(t["id"])
        if len(tid) > 8:
            continue
        kind = str(t.get("kind") or {"a": "audio", "s": "subs"}.get(tid[:1], "video"))
        bus = str(t.get("bus") or {"a1": "dialogue", "a2": "musique"}.get(tid, "sfx"))
        # Pas de défaut par identifiant : `_LEGACY_TRACKS` déclare déjà
        # `"loop": True` sur a2, donc `t.get("loop", tid == "a2")`
        # n'ajoutait rien au chemin historique et faisait une surprise sur
        # un payload personnalisé — une piste a2 mise par l'utilisateur sur
        # le bus sfx et sans `loop` devenait quand même l'entrée `music` :
        # bouclée, seule à ducker la voix, et au gain MUSIQUE. C'est le
        # payload qui décide.
        loop = bool(t.get("loop")) and kind == "audio"
        meta[tid] = {"kind": kind, "bus": bus if bus in _BUSES else "sfx",
                     "loop": loop, "layer": 0}
        if kind == "video" and tid != "v1":
            ov.append(tid)
    for k, tid in enumerate(reversed(ov)):
        meta[tid]["layer"] = k
    # Une liste `tracks` PRÉSENTE mais dont aucune entrée n'est
    # exploitable (mesuré : ["v1", 3, None, True] → {}) passait le garde
    # de `rows` et laissait `meta` vide : le rendu jetait alors TOUS les
    # overlays et TOUS les clips audio, et rendait une vidéo muette en
    # status done. Une liste illisible vaut une liste absente. Pas de
    # récursion infinie : le repli rend cinq entrées.
    return meta or _tracks_meta(None)


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout.strip()
        return max(0.0, float(out))
    except (ValueError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return 0.0


def _has_audio_stream(path: Path) -> bool:
    """Vrai si le fichier porte au moins une piste audio.

    Indispensable avant de poser un clip vidéo sur une piste audio : le
    filtergraph référence [idx:a] et ffmpeg échoue sur tout le rendu si le
    flux n'existe pas.
    """
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout.strip()
        return bool(out)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _audio_dir() -> Path:
    p = settings.images_path.parent / "audio"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _db_to_gain(db: float) -> float:
    return round(10 ** (float(db) / 20.0), 4)


def _clip_mix_params(c: dict) -> tuple[float, float, float]:
    """Mixage PAR CLIP audio (champs optionnels du payload) : gain en dB
    (clamp −24..+12, défaut 0), fade_in / fade_out en s (clamp 0..3).

    Valeurs invalides (non numériques, NaN) ignorées avec warning — le clip
    garde le comportement historique. Champs absents = strictement l'ancien
    rendu (le gain 0 dB laisse le gain de bus intact, aucun afade inséré)."""
    def _num(key: str, lo: float, hi: float) -> float:
        v = c.get(key)
        if v is None:
            return 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = float("nan")
        if f != f:  # NaN — jamais propagé dans un filtergraph
            logger.warning(f"montage: {key} invalide ({v!r}), ignoré — "
                           f"{c.get('label') or c.get('tr')}")
            return 0.0
        return max(lo, min(hi, f))
    return (_num("gain", -24.0, 12.0), _num("fade_in", 0.0, 3.0),
            _num("fade_out", 0.0, 3.0))


# R2 : courbes de fondu par clip — vocabulaire payload → afade curve= ffmpeg.
# lin = tri (défaut ffmpeg, jamais émis : rétro-compat octet pour octet),
# douce = hsin (demi-sinus), expo = exp, log = log.
_FADE_CURVES = {"lin": "", "douce": "hsin", "expo": "exp", "log": "log"}


def _fade_curve(c: dict, key: str) -> str:
    """Suffixe ``:curve=…`` de l'afade d'un clip (fade_in_curve /
    fade_out_curve, optionnels — lin|douce|expo|log). Absent ou "lin" → "" :
    l'afade émis reste octet pour octet l'historique (tri est déjà le défaut
    ffmpeg, on ne l'écrit jamais). Valeur inconnue → warning + fondu
    linéaire (jamais propagée au filtergraph). Sans fondu > 0, la courbe
    est sans effet (aucun afade n'est inséré)."""
    v = c.get(key)
    if not v:
        return ""
    name = _FADE_CURVES.get(str(v).strip().lower())
    if name is None:
        logger.warning(f"montage: {key} inconnue ({v!r}), fondu linéaire — "
                       f"{c.get('label') or c.get('tr') or 'musique'}")
        return ""
    return f":curve={name}" if name else ""


# R4 : automation de volume PAR CLIP audio — les losanges de l'UI deviennent
# une expression volume=':eval=frame' (interpolation LINÉAIRE en dB entre
# points, conversion pow(10, dB/20)). Ce filtre se MULTIPLIE aux volumes déjà
# présents dans la chaîne (gain de clip × bus, plus loin) : jamais un
# remplacement — deux filtres volume en série multiplient leurs gains.
_VP_MAX_POINTS = 12


def _volume_points(c: dict) -> list | None:
    """Champ optionnel ``volume_points`` d'un clip audio : [{t, db}] → liste
    TRIÉE de tuples (t, db) prête pour :func:`_vp_expr`, ou None.

    t en secondes (clamp ≥ 0) : LOCALES au clip pour a1/a3 (0..durée, la même
    horloge que les afade) ; pour la musique A2 bouclée, temps GLOBAL du rendu
    0..total — le flux bouclé n'est jamais retrimé, son ``t`` est celui du
    montage (l'UI convertit et l'affiche). db clampé −40..+12. Entrées
    invalides (non-dict, non numériques, NaN) ignorées avec warning ; au-delà
    de 12 points triés le surplus est ignoré (warning) ; doublons de t
    (< 5 ms) fusionnés, le dernier gagne (une pente y diviserait par ~0).
    Champ absent, vide ou entièrement invalide → None : la chaîne émise reste
    STRICTEMENT l'historique (non-régression testée)."""
    raw = c.get("volume_points")
    if not raw:
        return None
    lbl = c.get("label") or c.get("tr") or "audio"
    if not isinstance(raw, list):
        logger.warning(f"montage: volume_points invalide "
                       f"({type(raw).__name__}), ignoré — {lbl}")
        return None
    pts = []
    for p in raw:
        try:
            t, db = float(p["t"]), float(p["db"])
        except (TypeError, ValueError, KeyError, IndexError):
            t = db = float("nan")
        if t != t or db != db:  # NaN — jamais propagé dans un filtergraph
            logger.warning(f"montage: point d'automation invalide ({p!r}), "
                           f"ignoré — {lbl}")
            continue
        pts.append((max(0.0, round(t, 3)),
                    max(-40.0, min(12.0, round(db, 2)))))
    pts.sort(key=lambda q: q[0])
    if len(pts) > _VP_MAX_POINTS:
        logger.warning(f"montage: {len(pts)} points d'automation (max "
                       f"{_VP_MAX_POINTS}), surplus ignoré — {lbl}")
        pts = pts[:_VP_MAX_POINTS]
    out: list = []
    for t, db in pts:
        if out and t - out[-1][0] < 0.005:
            out[-1] = (out[-1][0], db)
            continue
        out.append((t, db))
    return out or None


def _vp_expr(pts: list) -> str:
    """Expression du filtre volume (``:eval=frame``) pour des points (t, db)
    triés : interpolation LINÉAIRE en dB — la droite que l'UI trace entre deux
    losanges est exactement ce qui s'entend — constante avant le premier point
    (db0) et après le dernier (dbN), conversion finale pow(10, dB/20).

    ``t`` y est l'horloge du flux AU POINT D'INSERTION du filtre : locale au
    clip pour a1/a3 (asetpts=PTS-STARTPTS l'a remise à zéro — après atempo le
    cas échéant, la même horloge de sortie que les afade), globale au rendu
    pour la musique bouclée. Les virgules de if(…) sont sans ambiguïté :
    l'expression est posée entre quotes simples dans le filtergraph."""
    n = sfx_service.fnum
    if len(pts) == 1:
        db_expr = n(pts[0][1])
    else:
        db_expr = n(pts[-1][1])
        for k in range(len(pts) - 1, 0, -1):
            t0, d0 = pts[k - 1]
            t1, d1 = pts[k]
            seg = f"{n(d0)}+({n(d1 - d0)})*(t-{n(t0)})/{n(t1 - t0)}"
            db_expr = f"if(lt(t,{n(t1)}),{seg},{db_expr})"
        db_expr = f"if(lt(t,{n(pts[0][0])}),{n(pts[0][1])},{db_expr})"
    return f"pow(10,({db_expr})/20)"


def _ov_transform(c: dict) -> dict | None:
    """Transformation optionnelle d'un overlay V2 (champs du payload) :
    x / y = centre en fraction du canvas (défaut 0.5, clamp −0.5..1.5 — l'UI
    autorise −0.2..1.2), scale = largeur relative au canvas (0.05..3, la
    hauteur suit le ratio source), rotate = degrés (−180..180).

    AUCUN champ valide présent → None : la chaîne cover historique reste
    strictement inchangée (rétro-compat bit à bit). Valeur invalide (non
    numérique, NaN) : ignorée avec warning, le champ retombe à son défaut."""
    spec = {"x": (-0.5, 1.5, 0.5), "y": (-0.5, 1.5, 0.5),
            "scale": (0.05, 3.0, 1.0), "rotate": (-180.0, 180.0, 0.0)}
    out, seen = {}, False
    for key, (lo, hi, dv) in spec.items():
        v = c.get(key)
        if v is None:
            out[key] = dv
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = float("nan")
        if f != f:  # NaN — jamais propagé dans un filtergraph
            logger.warning(f"montage: overlay {key} invalide ({v!r}), ignoré — "
                           f"{c.get('label') or c.get('tr')}")
            out[key] = dv
            continue
        out[key] = max(lo, min(hi, f))
        seen = True
    return out if seen else None


# R4b : keyframes de position par overlay V2 — champ optionnel
# ``motion_points`` : [{t, x, y, rotate?}] (max 8). t en secondes LOCALES au
# clip (0..durée, clampé), x/y/rotate : mêmes clamps que _ov_transform. Au
# rendu, les expressions x/y du filtre overlay deviennent des interpolations
# LINÉAIRES par morceaux du temps GLOBAL du montage (le filtre overlay est
# posé sur le flux composité : son t est celui de enable='between(t,st,en)' —
# chaque point local devient start + t). La rotation s'anime sur l'horloge
# LOCALE du flux overlay (le filtre rotate précède le setpts de décalage).
# L'ÉCHELLE reste STATIQUE — aucune keyframe d'échelle : la largeur scale·W
# est figée pour toute la durée de l'overlay (l'UI l'affiche tel quel).
_MP_MAX_POINTS = 8


def _motion_points(c: dict) -> list | None:
    """Champ optionnel ``motion_points`` d'un overlay V2 : [{t, x, y,
    rotate?}] → liste TRIÉE de tuples (t, x, y, rotate|None), ou None.

    t clampé 0..durée du clip (end−start), x/y clampés −0.5..1.5, rotate
    −180..180 (mêmes bornes que _ov_transform) — rotate absent reste None :
    le point ne participe pas à l'animation d'angle. Entrées invalides
    (non-dict, non numériques, NaN) ignorées avec warning ; au-delà de
    8 points triés le surplus est ignoré (warning) ; doublons de t (< 5 ms)
    fusionnés, le dernier gagne (une pente y diviserait par ~0). Champ
    absent, vide ou entièrement invalide → None : la chaîne émise reste
    STRICTEMENT l'historique (non-régression testée)."""
    raw = c.get("motion_points")
    if not raw:
        return None
    lbl = c.get("label") or c.get("tr") or "overlay"
    if not isinstance(raw, list):
        logger.warning(f"montage: motion_points invalide "
                       f"({type(raw).__name__}), ignoré — {lbl}")
        return None
    try:
        dur = max(0.0, float(c.get("end") or 0) - float(c.get("start") or 0))
    except (TypeError, ValueError):
        dur = 0.0
    pts = []
    for p in raw:
        try:
            t, xx, yy = float(p["t"]), float(p["x"]), float(p["y"])
        except (TypeError, ValueError, KeyError, IndexError):
            t = xx = yy = float("nan")
        if t != t or xx != xx or yy != yy:  # NaN — jamais dans un filtergraph
            logger.warning(f"montage: point de position invalide ({p!r}), "
                           f"ignoré — {lbl}")
            continue
        rr = p.get("rotate") if isinstance(p, dict) else None
        if rr is not None:
            try:
                rr = float(rr)
            except (TypeError, ValueError):
                rr = float("nan")
            if rr != rr:
                logger.warning(f"montage: rotate de point invalide, ignoré — "
                               f"{lbl}")
                rr = None
            else:
                rr = max(-180.0, min(180.0, rr))
        t = max(0.0, round(t, 3))
        if dur > 0:
            t = min(t, round(dur, 3))
        pts.append((t, max(-0.5, min(1.5, xx)), max(-0.5, min(1.5, yy)), rr))
    pts.sort(key=lambda q: q[0])
    if len(pts) > _MP_MAX_POINTS:
        logger.warning(f"montage: {len(pts)} points de position (max "
                       f"{_MP_MAX_POINTS}), surplus ignoré — {lbl}")
        pts = pts[:_MP_MAX_POINTS]
    out: list = []
    for q in pts:
        if out and q[0] - out[-1][0] < 0.005:
            out[-1] = (out[-1][0], q[1], q[2], q[3])
            continue
        out.append(q)
    return out or None


def _mp_lerp_expr(pts: list) -> str:
    """Interpolation linéaire par morceaux pour des paires (t, v) TRIÉES —
    même gabarit d'expression que :func:`_vp_expr` (constante avant le
    premier point / après le dernier), sans conversion finale : sert aux
    expressions x/y (pixels, temps global) et a (radians, temps local) des
    overlays animés. Toujours posée entre quotes simples dans le filtergraph
    (les virgules de if(…) y sont sans ambiguïté)."""
    n = sfx_service.fnum
    if len(pts) == 1:
        return n(pts[0][1])
    expr = n(pts[-1][1])
    for k in range(len(pts) - 1, 0, -1):
        t0, v0 = pts[k - 1]
        t1, v1 = pts[k]
        seg = f"{n(v0)}+({n(v1 - v0)})*(t-{n(t0)})/{n(t1 - t0)}"
        expr = f"if(lt(t,{n(t1)}),{seg},{expr})"
    return f"if(lt(t,{n(pts[0][0])}),{n(pts[0][1])},{expr})"


# C4 : vitesse par clip V1 — champ optionnel ``speed`` (0.25..4, défaut 1).
# La durée TIMELINE du clip ne change JAMAIS (offsets xfade, trous, adelay
# audio et maître de durée intacts) : c'est la fenêtre SOURCE consommée qui
# devient durée×speed, et le flux est remis à la durée timeline par
# setpts=PTS/speed inséré AVANT la normalisation fps (fps=30 rematérialise
# ensuite un débit constant en dupliquant / sautant des frames — slow-motion
# par duplication, accéléré par décimation, sans interpolation). L'audio des
# plans V1 n'entre pas dans le graphe ([idx:v] seul) : AUCUN atempo — le
# clip A1 « son du plan » garde sa vitesse (l'UI le signale).


def _v1_speed(c: dict) -> float:
    """clips V1 [].speed → 0.0 (= inchangé, chaîne historique octet pour
    octet) ou 0.25..4 clampé. Invalide (non numérique, NaN, ≤ 0) : warning
    et retour au comportement historique — jamais propagé au filtergraph."""
    v = c.get("speed")
    if v is None:
        return 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = float("nan")
    if f != f or f <= 0:
        logger.warning(f"montage: speed V1 invalide ({v!r}), ignoré — "
                       f"{c.get('label') or c.get('tr')}")
        return 0.0
    f = max(0.25, min(4.0, f))
    return 0.0 if abs(f - 1.0) < 1e-6 else f


# ------------------------------------------------------------------- save ---
# A1 : sauvegarde de timeline — UN projet de montage persistant, posé dans le
# répertoire de DONNÉES de l'app (settings.images_path.parent : le parent
# commun d'images/ et audio/ — jamais dans le dépôt ni dans outputs/).
# Écriture ATOMIQUE : fichier temporaire à côté puis os.replace (un crash ne
# laisse jamais un JSON tronqué) ; lecture tolérante (absent / corrompu /
# forme inattendue → None, la Bibliothèque reprend la main). Le contenu est
# le modèle CLIENT complet (textes de narration, automation, trajectoires,
# vitesses…) : le backend le stocke tel quel et ne l'interprète qu'au GET
# /project pour vérifier que les sources existent encore.

_SAVE_MAX_CLIPS = 400
_SAVE_MAX_BYTES = 2_000_000


def _saved_path() -> Path:
    return settings.images_path.parent / "montage_saved.json"


def _write_saved(data: dict) -> None:
    """Écriture atomique (tmp voisin + replace) — laisse remonter OSError
    (l'endpoint la traduit en 500, l'UI affiche « sauvegarde impossible »)."""
    path = _saved_path()
    tmp = path.with_name(f"{path.name}.{uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        tmp.replace(path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _load_saved() -> dict | None:
    """Sauvegarde parsée, ou None (absente, illisible, corrompue, forme
    inattendue) — None signifie toujours « la Bibliothèque fait foi »."""
    path = _saved_path()
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("montage: montage_saved.json illisible — retour "
                       "Bibliothèque")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("clips"), list):
        logger.warning("montage: montage_saved.json de forme inattendue — "
                       "retour Bibliothèque")
        return None
    return data


def _delete_saved() -> bool:
    """Vrai si un fichier de sauvegarde a réellement été supprimé."""
    path = _saved_path()
    try:
        if path.is_file():
            path.unlink()
            return True
    except OSError as e:
        logger.warning(f"montage: suppression de la sauvegarde impossible : {e}")
    return False


# ---------------------------------------------------------------- project ---

@router.get("/project")
async def montage_project(limit: int = 4):
    """Timeline de l'éditeur. Une sauvegarde (POST /save) existe → elle EST
    le projet : renvoyée telle quelle (saved:true, modèle client complet),
    après vérification que chaque source référencée existe encore (clip
    retiré sinon, avec warning + saved_pruned). Sans sauvegarde exploitable :
    construction historique depuis la Bibliothèque (saved:false) — les
    `limit` derniers rendus/uploads finis en V1 (bout à bout, sans trous),
    la voix off la plus récente en A1, une musique (nom contenant
    theme/music/bgm/…) en A2."""
    saved = await asyncio.to_thread(_load_saved)
    if saved is not None:
        kept, pruned = [], 0
        for c in saved["clips"]:
            if not isinstance(c, dict):
                continue
            if c.get("src"):
                p = await _resolve_src(c.get("src"))
                if p is None:
                    logger.warning(
                        f"montage: source de la sauvegarde disparue, clip "
                        f"retiré — {c.get('label') or c.get('src')}")
                    pruned += 1
                    continue
            kept.append(c)
        if any(c.get("tr") == "v1" for c in kept):
            try:
                sdur = float(saved.get("duration") or 0)
            except (TypeError, ValueError):
                sdur = 0.0
            if sdur != sdur or sdur <= 0:
                ends = []
                for c in kept:
                    try:
                        ends.append(float(c.get("end") or 0))
                    except (TypeError, ValueError):
                        pass
                sdur = max(ends, default=1.0)
            out = {"ok": True, "has_assets": True, "saved": True,
                   "name": str(saved.get("name") or "montage"),
                   "ratio": str(saved.get("ratio") or "9:16"),
                   "duration": round(max(0.5, sdur), 3),
                   "mix": (saved.get("mix")
                           if isinstance(saved.get("mix"), dict) else
                           {"dialogue": -6, "musique": -18, "sfx": -12}),
                   "duration_master": saved.get("duration_master", True),
                   "ducking": saved.get("ducking", True),
                   "clips": kept, "saved_at": saved.get("saved_at")}
            if isinstance(saved.get("ducking_cfg"), dict):
                out["ducking_cfg"] = saved["ducking_cfg"]
            if isinstance(saved.get("subs_style"), dict):
                out["subs_style"] = saved["subs_style"]   # S1 (cf. POST /save)
            if isinstance(saved.get("tracks"), list) and saved["tracks"]:
                out["tracks"] = saved["tracks"]           # P1 (cf. POST /save)
            if pruned:
                out["saved_pruned"] = True
                out["pruned"] = pruned
            return out
        # Sauvegarde présente mais plus AUCUN clip V1 à source valide : elle
        # est inexploitable — la Bibliothèque reprend la main (le prochain
        # autosave d'une édition réelle l'écrasera).
        logger.warning("montage: sauvegarde sans clip V1 exploitable — "
                       "timeline reconstruite depuis la Bibliothèque")
    async with async_session_factory() as session:
        res = await session.execute(
            select(JobRecord).where(JobRecord.status == JobStatus.DONE.value)
            .order_by(JobRecord.completed_at.desc()).limit(60))
        jobs = res.scalars().all()

    vids = []
    for j in jobs:
        fp = j.final_video_path or j.video_path
        if not fp or not Path(fp).exists():
            continue
        if j.provider == "montage" and "_preview" in Path(fp).name:
            continue  # ne pas remonter nos propres aperçus en source
        vids.append(j)
        if len(vids) >= limit:
            break

    loop = asyncio.get_running_loop()
    clips, t = [], 0.0
    # Le mixage n'utilise QUE les pistes a1/a2/a3 : l'audio embarqué d'un clip
    # V1 est ignoré par le graphe ffmpeg ([idx:v] seulement). Sans clip A1
    # dérivé, un avatar parlant monté ici sort muet — on pose donc sa propre
    # bande son en face de lui, quand elle existe.
    v1_voices = []
    for j in vids:
        p = Path(j.final_video_path or j.video_path)
        dur = await loop.run_in_executor(None, _probe_duration, p)
        dur = round(dur or float(j.duration_s or 4.0), 3)
        if dur < 0.3:
            continue
        if await loop.run_in_executor(None, _has_audio_stream, p):
            v1_voices.append({"tr": "a1", "id": f"a1_{j.id[:8]}",
                              "label": f"{(j.title or p.stem)[:40]} · son du plan",
                              "start": round(t, 3), "end": round(t + dur, 3),
                              "src": {"job_id": j.id}, "srcIn": 0})
        clips.append({"tr": "v1", "id": f"v1_{j.id[:8]}",
                      "label": (j.title or p.stem)[:48],
                      "start": round(t, 3), "end": round(t + dur, 3),
                      "src": {"job_id": j.id}, "srcIn": 0,
                      "transition": "xfade 0.4" if clips else "cut",
                      "transition_s": 0.4 if clips else 0.0})
        t = round(t + dur, 3)

    audio = sorted(_audio_dir().glob("*"), key=lambda f: f.stat().st_mtime,
                   reverse=True)
    audio = [a for a in audio if a.is_file() and a.suffix.lower() in
             (".mp3", ".wav", ".m4a", ".ogg", ".flac")]
    voice = next((a for a in audio
                  if not any(h in a.name.lower() for h in _MUSIC_HINT)), None)
    music = next((a for a in audio
                  if any(h in a.name.lower() for h in _MUSIC_HINT)), None)

    if v1_voices:
        # Le son des plans prime : coller en plus un vieux fichier de voix off
        # sans rapport, à t=0, est pire que le silence.
        clips.extend(v1_voices)
    elif voice is not None:
        vdur = await loop.run_in_executor(None, _probe_duration, voice)
        if vdur >= 0.3:
            clips.append({"tr": "a1", "id": "a1_vo",
                          "label": voice.name, "start": 0.0,
                          "end": round(min(vdur, max(t, vdur)), 3),
                          "src": {"audio": voice.name}})
    duration = max(t, max((c["end"] for c in clips), default=0.0))
    if music is not None and duration > 0:
        clips.append({"tr": "a2", "id": "a2_bgm",
                      "label": f"{music.stem} · ducking auto",
                      "start": 0.0, "end": round(duration, 3),
                      "src": {"audio": music.name}, "loop": True})

    has = bool([c for c in clips if c["tr"] == "v1"])
    return {"ok": True, "has_assets": has, "saved": False,
            "name": "montage_bibliotheque" if has else None,
            "ratio": "9:16", "duration": round(duration, 3),
            "clips": clips if has else [],
            "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
            "sources": {"videos": len(vids), "audio": len(audio)}}


@router.get("/effects")
async def montage_effects():
    """Catalogue du moteur Effects / Mask pour le sélecteur d'effets par clip
    de l'inspecteur (labels FR + paramètres par type)."""
    from app.services import effects_engine
    return {"effects": effects_engine.catalog()}


@router.post("/save")
async def montage_save(request: Request):
    """Autosave de l'éditeur Montage. Body : {name, ratio, duration, mix,
    duration_master?, ducking? (bool), ducking_cfg? (objet), clips:[...]}
    — les clips sont le modèle CLIENT complet (texte de narration,
    gains/fondus/courbes, volume_points, x/y/scale/rotate/motion_points,
    vitesse, effets, opacité…), stockés TELS QUELS et resservis par
    GET /project (saved:true). Écriture atomique ; 400 si la forme est
    invalide ou le volume déraisonnable (> 400 clips ou > 2 Mo)."""
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict) or not isinstance(body.get("clips"), list):
        raise HTTPException(400, "Sauvegarde invalide — objet {name, ratio, "
                                 "duration, mix, clips[]} attendu.")
    clips = [c for c in body["clips"] if isinstance(c, dict)]
    if len(clips) > _SAVE_MAX_CLIPS:
        raise HTTPException(400, f"Sauvegarde refusée — {len(clips)} clips "
                                 f"(max {_SAVE_MAX_CLIPS}).")
    try:
        dur = float(body.get("duration") or 0)
    except (TypeError, ValueError):
        dur = 0.0
    if dur != dur or dur < 0:  # NaN / négatif
        dur = 0.0
    ducking = body.get("ducking", True)
    if not isinstance(ducking, (bool, dict)):
        ducking = bool(ducking)
    data = {
        "name": str(body.get("name") or "montage")[:80],
        "ratio": str(body.get("ratio") or "9:16")[:12],
        "duration": round(dur, 3),
        "mix": body.get("mix") if isinstance(body.get("mix"), dict) else {},
        "duration_master": bool(body.get("duration_master", True)),
        "ducking": ducking,
        "clips": clips,
        "saved_at": _dt.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    if isinstance(body.get("ducking_cfg"), dict):
        data["ducking_cfg"] = body["ducking_cfg"]
    # S1 : style des sous-titres. Les SEGMENTS sont déjà dans `clips` (piste
    # s1) et voyagent donc tels quels ; le style, lui, n'est pas un clip — sans
    # cette clé il ne survivait qu'en localStorage et changeait de poste à
    # poste. GET /project le resserre à l'éditeur (svmApplyProject le lit).
    if isinstance(body.get("subs_style"), dict):
        data["subs_style"] = body["subs_style"]
    # P1 : les PISTES de la timeline (ordre, bus, boucle). Stockées telles
    # quelles — sans cette clé, une piste ajoutée ou déplacée disparaissait au
    # rechargement et les clips qu'elle portait retombaient sur une piste
    # inconnue, donc hors du rendu. GET /project les resert à l'éditeur.
    if isinstance(body.get("tracks"), list):
        data["tracks"] = body["tracks"]
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > _SAVE_MAX_BYTES:
        raise HTTPException(400, "Sauvegarde refusée — plus de 2 Mo.")
    try:
        await asyncio.to_thread(_write_saved, data)
    except OSError as e:
        logger.warning(f"montage: écriture de la sauvegarde impossible : {e}")
        raise HTTPException(500, f"Écriture de la sauvegarde impossible : {e}")
    return {"ok": True, "saved_at": data["saved_at"], "clips": len(clips)}


@router.delete("/save")
async def montage_save_delete():
    """Efface la sauvegarde de timeline — GET /project reconstruira depuis la
    Bibliothèque (bouton « bibliothèque » de l'éditeur, après confirmation)."""
    deleted = await asyncio.to_thread(_delete_saved)
    return {"ok": True, "deleted": deleted}


# ----------------------------------------------------------------- render ---

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


async def _resolve_src(src: dict | None) -> Path | None:
    """{job_id} → chemin du rendu fini ; {audio: name} → fichier du dossier
    audio ; {image: name} → fichier du dossier images (overlays V2) ;
    {file_path} absolu accepté s'il existe."""
    if not isinstance(src, dict):
        return None
    jid = src.get("job_id")
    if jid:
        async with async_session_factory() as session:
            jr = await session.get(JobRecord, str(jid))
        fp = jr and (jr.final_video_path or jr.video_path)
        return Path(fp) if fp and Path(fp).exists() else None
    img = src.get("image")
    if img:
        q = settings.images_path / Path(str(img)).name
        return q if q.exists() else None
    name = src.get("audio") or src.get("filename")
    if name:
        q = _audio_dir() / Path(str(name)).name
        if q.exists():
            return q
    fp = src.get("file_path")
    if fp and Path(fp).exists():
        return Path(fp)
    return None


def _build_montage_command(v1, v2, a_clips, music, *, w, h, fps, mix_db,
                           ducking, duration_master, preview, out,
                           audio_only=False, subs_ass=None):
    """Commande ffmpeg complète (sync, testable). v1/v2/a_clips/music portent
    des chemins déjà résolus + durées sondées.

    R1 audio : a_clips/music acceptent en plus `fx_chain` (fragment ffmpeg
    déjà construit par sfx_service.fx_chain, "" = aucun) et `speed` (0.0 =
    inchangé, sinon 0.5–2 → atempo, la durée effective du clip devient
    d/speed) ; `ducking` accepte le bool historique OU un dict
    {threshold, ratio, attack, release} (sfx_service.parse_ducking).
    R2 : `fade_in_curve` / `fade_out_curve` (lin|douce|expo|log, voir
    _fade_curve) sur a_clips ET music — lin/absent n'émet pas de curve=.
    R4 : `volume_points` (liste (t, db) déjà sanitizée par _volume_points,
    None sans automation) sur a_clips ET music — volume='expr':eval=frame
    inséré après les afade, avant aresample (voir _vp_expr ; t local au clip,
    global au rendu pour la musique bouclée), multiplié au gain statique.
    R4b : `mp` sur v2 (liste (t, x, y, rotate|None) déjà sanitizée par
    _motion_points, None sans keyframes) — x/y du filtre overlay deviennent
    des interpolations linéaires par morceaux du temps GLOBAL (points posés
    à start + t), la rotation s'anime en horloge LOCALE du flux overlay si
    des points portent rotate (cadre fixe hypot(iw,ih)) ; scale reste la
    valeur statique de `tf` (aucune keyframe d'échelle) ; `mp` sans `tf` :
    défauts centre / échelle 1.
    C4 : `speed` sur v1 (0.0 = inchangé, sinon 0.25..4 déjà clampé par
    _v1_speed) — l'input lit d·speed s de source (-t, borné au disponible)
    et setpts=PTS/speed AVANT fps remet le flux à la durée timeline ; la
    durée du segment (seg_durs) et donc offsets xfade / total / adelay ne
    bougent pas ; AUCUN atempo (l'audio V1 n'entre pas dans le graphe).
    S1 : `subs_ass` = chemin d'un fichier ASS déjà écrit (piste de
    sous-titres). Il devient le DERNIER maillon de la chaîne vidéo, juste
    avant `format=yuv420p` : le texte passe donc au-dessus des overlays V2 et
    couvre l'extension du maître de durée. None (défaut) : chaîne historique
    intacte, octet pour octet.
    Sans ces champs, la commande émise est identique octet pour octet à
    l'historique (non-régression testée).

    audio_only=True (POST /measure) : MÊME graphe audio — mêmes durées de
    segments V1 (total, fondus musique, maître de durée), mêmes chaînes de
    mix — mais aucune vidéo ouverte ni décodée ; le mix sort dans ebur128
    (LUFS I / TP / LRA) et la sortie est jetée (-f null).
    EFFET DE BORD ASSUMÉ (03/09/2026) : la route de mesure partageant ce
    graphe, le correctif du ducking (apad sur la chaîne latérale, plus bas)
    CHANGE la valeur retournée pour tout projet voix + musique + ducking.
    Jusqu'ici elle mesurait un mix tronqué à la dernière syllabe de la voix —
    fidèlement, puisque le rendu l'était aussi ; les deux sont corrigés
    ensemble, et restent donc d'accord. Conséquence pratique : toute mesure
    LUFS relevée AVANT le 03/09/2026 sur un projet de ce type est périmée,
    il faut la refaire."""
    if audio_only:
        v2 = []
    inputs, parts = [], []
    idx = 0

    def _tau_for(c):
        _n, fixed = _XFADE.get(str(c.get("transition") or "cut")
                               .split()[0].lower(), _XFADE["cut"])
        return fixed if fixed is not None else float(
            c.get("transition_s") or 0.4)

    # --- V1 : les trous entre clips (et avant le premier) sont rendus en
    # NOIR — segments lavfi à leur durée timeline + compensation du
    # chevauchement xfade des deux frontières (cut entrant 0.04 + transition
    # du clip suivant), pour que le clip d'après retombe sur sa position et
    # que l'audio (adelay) reste aligné.
    segs = []
    prev_end = 0.0
    for c in v1:
        g = c["start"] - prev_end
        if g > 0.1:
            segs.append({"gap": True,
                         "dur": round(g + _tau_for(c) + 0.04, 3)})
        segs.append(c)
        prev_end = c["end"]

    seg_durs, seg_idx = [], []
    for s in segs:
        if s.get("gap"):
            if not audio_only:
                inputs.extend(["-f", "lavfi", "-t", str(s["dur"]), "-i",
                               f"color=c=black:s={w}x{h}:r={fps}"])
            seg_durs.append(s["dur"])
        else:
            want = max(0.1, s["end"] - s["start"])
            avail = max(0.1, s["src_dur"] - s["src_in"])
            # C4 : vitesse V1 — à ×spd le segment lit want·spd s de SOURCE ;
            # la durée TIMELINE d restituée est bornée par ce que la source
            # peut couvrir (d_src/spd) : un plan trop court à ×2 couvre moins
            # de timeline qu'avant (honnête), à ×0.5 il peut en couvrir plus.
            # spd 0.0/absent : arithmétique historique, octet pour octet.
            spd = float(s.get("speed") or 0.0)
            if spd:
                d_src = round(max(0.05, min(want * spd, avail)), 3)
                d = round(max(0.1, min(want, d_src / spd)), 3)
            else:
                d_src = d = round(min(want, avail), 3)
            if not audio_only:
                if s["src_in"] > 0:
                    inputs.extend(["-ss", str(s["src_in"])])
                inputs.extend(["-t", str(d_src), "-i", str(s["path"])])
            seg_durs.append(d)
        if not audio_only:
            seg_idx.append(idx)
            idx += 1
    if not audio_only:
        sf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h},setsar=1,fps={fps},format=yuv420p")
        from app.services import effects_engine as _fx
        for k, s in enumerate(segs):
            if s.get("gap"):
                parts.append(f"[{seg_idx[k]}:v]setsar=1,format=yuv420p,"
                             f"setpts=PTS-STARTPTS[n{k}]")
                continue
            # C4 : vitesse V1 — setpts=PTS/speed inséré AVANT fps : le
            # retiming comprime (×>1) ou étire (×<1) les timestamps, puis
            # fps={fps} rematérialise un débit constant (frames dupliquées ou
            # sautées) ; tpad/trim/setpts-STARTPTS en aval (INCHANGÉS)
            # garantissent la durée TIMELINE exacte seg_durs[k] — xfade et
            # offsets ne voient aucune différence. Sans speed : préfixe sf
            # historique, chaîne octet pour octet.
            spd = float(s.get("speed") or 0.0)
            if spd:
                pre = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                       f"crop={w}:{h},setsar=1,"
                       f"setpts=PTS/{sfx_service.fnum(spd)},"
                       f"fps={fps},format=yuv420p")
            else:
                pre = sf
            chain = (f"{pre},tpad=stop_mode=clone:stop_duration={seg_durs[k]},"
                     f"trim=0:{seg_durs[k]},setpts=PTS-STARTPTS")
            reff = s.get("effects")
            if reff:
                # Effets par clip — même moteur que le node Effects / Mask.
                parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}pre]")
                # dur : setpts=PTS-STARTPTS s'exécute AVANT les effets sur les
                # segments V1, donc t est local au clip — les bornes t0/t1 des
                # effets le sont aussi.
                parts += _fx.build_chain(reff, f"n{k}pre", f"n{k}",
                                         f"cfx{k}",
                                         {"w": w, "h": h, "dur": seg_durs[k], "fps": fps})
            else:
                parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}]")

    starts = [0.0] * len(segs)
    if len(segs) == 1:
        cur, total = "n0", seg_durs[0]
    else:
        cur, total = "n0", seg_durs[0]
        for k in range(1, len(segs)):
            s = segs[k]
            if s.get("gap"):
                name, tau = _XFADE["cut"]
            else:
                name, fixed = _XFADE.get(str(s.get("transition") or "cut")
                                         .split()[0].lower(), _XFADE["cut"])
                tau = fixed if fixed is not None else float(
                    s.get("transition_s") or 0.4)
            tau = max(0.04, min(tau, max(0.1, seg_durs[k] - 0.1),
                                max(0.1, total - 0.1)))
            offset = max(0.0, round(total - tau, 3))
            starts[k] = offset
            if not audio_only:
                parts.append(f"[{cur}][n{k}]xfade=transition={name}:"
                             f"duration={round(tau, 3)}:offset={offset}[x{k}]")
            cur = f"x{k}"
            total = round(total + seg_durs[k] - tau, 3)

    # --- audio : voix/sfx posées à leur position, musique bouclée + ducking ---
    voice_lbl, sfx_lbl = [], []
    for n, c in enumerate(a_clips):
        sin = max(0.0, float(c.get("src_in") or 0))
        avail = max(0.1, c["src_dur"] - sin)
        d = round(min(max(0.1, c["end"] - c["start"]), avail), 3)
        inputs.extend(["-i", str(c["path"])])
        dly = int(round(c["start"] * 1000))
        # R1 : vitesse (atempo) + rack d'effets par clip — insérés après
        # asetpts, AVANT les fondus (qui restent sur l'horloge de sortie).
        # speed 0.0/absent + fx_chain "" ⇒ proc vide, chaîne historique
        # intacte octet pour octet. d_eff = durée du clip APRÈS atempo
        # (un clip de 4 s à ×2 dure 2 s) — les fondus s'y calent.
        spd = float(c.get("speed") or 0.0)
        if spd:
            d_eff = round(d / spd, 3)
            proc = f"atempo={sfx_service.fnum(spd)},"
        else:
            d_eff = d
            proc = ""
        fxc = c.get("fx_chain") or ""
        if fxc:
            proc += fxc + ","
        # Fondus PAR CLIP (optionnels) — insérés après asetpts, sur l'horloge
        # locale 0..d du clip (fade_out : st = durée − fondu). Sans fondu la
        # chaîne reste octet pour octet celle d'avant (rétro-compat).
        # R2 : courbe optionnelle par côté (fade_in_curve / fade_out_curve →
        # :curve=hsin|exp|log ; lin/absent = rien d'émis, tri = défaut ffmpeg).
        fi = min(float(c.get("fade_in") or 0), d_eff)
        fo = min(float(c.get("fade_out") or 0), d_eff)
        fades = ""
        if fi > 0:
            fades += (f"afade=t=in:st=0:d={round(fi, 3)}"
                      f"{_fade_curve(c, 'fade_in_curve')},")
        if fo > 0:
            fades += (f"afade=t=out:st={round(max(0.0, d_eff - fo), 3)}:"
                      f"d={round(fo, 3)}{_fade_curve(c, 'fade_out_curve')},")
        # R4 : automation de volume (losanges) — volume=expr:eval=frame,
        # inséré APRÈS les afade (l'automation est un geste de MIXAGE : elle
        # se multiplie par-dessus les fondus, comme le gain statique — jamais
        # à leur place) et AVANT aresample : t y est encore l'horloge locale
        # posée par asetpts (celle des afade, après atempo le cas échéant),
        # pas celle ré-échantillonnée par async=1. Le volume statique
        # (gain clip × bus) reste où il était — deux filtres volume en série
        # multiplient leurs gains. Sans points : chaîne octet pour octet.
        vp = c.get("volume_points")
        autom = f"volume='{_vp_expr(vp)}':eval=frame," if vp else ""
        parts.append(
            f"[{idx}:a]atrim={round(sin, 3)}:{round(sin + d, 3)},"
            f"asetpts=PTS-STARTPTS,{proc}{fades}{autom}"
            f"aresample=async=1,aformat=sample_rates=44100:"
            f"channel_layouts=stereo,volume={c['gain']},"
            f"adelay={dly}|{dly}[{'va' if c['tr'] == 'a1' else 'sa'}{n}]")
        (voice_lbl if c["tr"] == "a1" else sfx_lbl).append(
            f"[{'va' if c['tr'] == 'a1' else 'sa'}{n}]")
        idx += 1

    # Maître de durée : la voix n'est jamais coupée — la vidéo gèle sa
    # dernière image jusqu'à la fin de l'audio. La vitesse d'un clip change
    # sa durée effective (d/speed) — même arithmétique qu'avant sans speed.
    def _eff_len(c):
        e = min(c["end"] - c["start"], c["src_dur"])
        s = float(c.get("speed") or 0.0)
        return e / s if s else e
    audio_end = max((c["start"] + _eff_len(c) for c in a_clips), default=0.0)
    if duration_master and audio_end > total:
        if not audio_only:
            parts.append(f"[{cur}]tpad=stop_mode=clone:"
                         f"stop_duration={round(audio_end - total, 3)}[vext]")
            cur = "vext"
        total = round(audio_end, 3)

    # --- V2 : overlays posés à leur position timeline, après le maître de
    # durée (ils couvrent aussi l'extension) et avant l'encodage final.
    # Recette : setpts décalé + enable='between(t,…)' + eof_action=pass ;
    # l'alpha des PNG est préservé (pas de format=yuv420p dans cette chaîne),
    # opacité optionnelle via colorchannelmixer.
    # P1 : `layer` d'abord (rang de composition venu de l'ordre des pistes,
    # 0 = juste au-dessus de V1), `start` ensuite. Sans le champ — payload
    # historique — tous les overlays retombent à 0 et le tri est celui
    # d'avant, argument pour argument.
    for j, o in enumerate(sorted(v2, key=lambda k2: (int(k2.get("layer") or 0),
                                                     k2["start"]))):
        want = max(0.1, o["end"] - o["start"])
        if o["is_image"]:
            d = round(min(want, max(0.1, total - o["start"])), 3)
            inputs.extend(["-loop", "1", "-t", str(d), "-i", str(o["path"])])
        else:
            avail = max(0.1, o["src_dur"] - o["src_in"])
            d = round(min(want, avail), 3)
            if o["src_in"] > 0:
                inputs.extend(["-ss", str(o["src_in"])])
            inputs.extend(["-t", str(d), "-i", str(o["path"])])
        st = round(max(0.0, o["start"]), 3)
        en = round(st + d, 3)
        op = o.get("opacity")
        try:
            op = None if op is None else float(op)
        except (TypeError, ValueError):
            op = None
        tf = o.get("tf")
        mp = o.get("mp")
        if mp and tf is None:
            # R4b : keyframes sans champ statique — défauts de _ov_transform
            # (centre, échelle 1). Jamais le cas d'un payload historique :
            # motion_points est un champ nouveau, l'identité sans lui tient.
            tf = {"x": 0.5, "y": 0.5, "scale": 1.0, "rotate": 0.0}
        if tf is None:
            # Chaîne historique (cover plein cadre) — STRICTEMENT inchangée
            # quand aucun champ de transformation n'est posé.
            och = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                   f"crop={w}:{h},setsar=1,fps={fps}")
            if op is not None and 0.0 <= op < 1.0:
                och += f",format=yuva420p,colorchannelmixer=aa={round(op, 3)}"
            och += f",setpts=PTS-STARTPTS+{st}/TB"
            pos = ""
        else:
            # Overlay transformé : largeur = scale·W (paire, hauteur suit le
            # ratio source), rotation sur fond transparent (rgba + c=none),
            # centre posé à (x·W, y·H) via les constantes w/h du filtre
            # overlay. L'opacité existante se compose (aa multiplie l'alpha),
            # l'alpha des PNG est préservé de bout en bout.
            ow2 = max(2, int(round(w * tf["scale"] / 2.0)) * 2)
            och = f"scale={ow2}:-2,setsar=1,fps={fps},format=rgba"
            if op is not None and 0.0 <= op < 1.0:
                och += f",colorchannelmixer=aa={round(op, 3)}"
            # R4b : la rotation s'anime si des points portent rotate — angle
            # interpolé (radians) sur l'horloge LOCALE du flux overlay (le
            # setpts de décalage vient après). Le cadre de sortie devient le
            # carré FIXE hypot(iw,ih) (rotw/roth dépendraient de t, que les
            # expressions ow/oh n'évaluent qu'à l'init) : le média reste
            # centré dedans, la pose x/y « centre − w/2 » ne change pas.
            rot_pts = ([(t, r) for (t, _x, _y, r) in mp if r is not None]
                       if mp else [])
            if rot_pts:
                if max(abs(r) for _t, r in rot_pts) < 0.05:
                    pass  # angles tous ≈ 0 : pas de filtre rotate
                elif len({round(r, 2) for _t, r in rot_pts}) == 1:
                    # tous les points portent le même angle : filtre statique
                    # (cadre rotw/roth exact), l'angle des points fait foi
                    rad = round(rot_pts[0][1] * math.pi / 180.0, 6)
                    och += (f",rotate={rad}:ow=rotw({rad}):oh=roth({rad})"
                            f":c=none")
                else:
                    rpts = [(t, round(r * math.pi / 180.0, 6))
                            for t, r in rot_pts]
                    och += (f",rotate='{_mp_lerp_expr(rpts)}'"
                            f":ow='hypot(iw,ih)':oh=ow:c=none")
            elif abs(tf["rotate"]) >= 0.05:
                rad = round(tf["rotate"] * math.pi / 180.0, 6)
                och += (f",rotate={rad}:ow=rotw({rad}):oh=roth({rad}):c=none")
            och += f",setpts=PTS-STARTPTS+{st}/TB"
            if mp:
                # R4b : x/y animés — interpolation en temps GLOBAL du rendu
                # (celui de enable=between) : chaque point local t devient
                # st + t ; expressions quotées (virgules de if sans
                # ambiguïté), évaluées par frame (défaut eval de overlay).
                xpts = [(round(st + t, 3), round(w * x, 2))
                        for (t, x, _y, _r) in mp]
                ypts = [(round(st + t, 3), round(h * y, 2))
                        for (t, _x, y, _r) in mp]
                pos = (f"x='({_mp_lerp_expr(xpts)})-w/2'"
                       f":y='({_mp_lerp_expr(ypts)})-h/2':")
            else:
                cx = round(w * tf["x"], 2)
                cy = round(h * tf["y"], 2)
                pos = f"x={cx}-w/2:y={cy}-h/2:"
        parts.append(f"[{idx}:v]{och}[ov{j}]")
        parts.append(f"[{cur}][ov{j}]overlay={pos}eof_action=pass:"
                     f"enable='between(t,{st},{en})'[ob{j}]")
        cur = f"ob{j}"
        idx += 1

    music_lbl = None
    if music is not None:
        inputs.extend(["-stream_loop", "-1", "-i", str(music["path"])])
        # Fondus de la musique bouclée : entrée au démarrage, sortie calée
        # sur la FIN du rendu (`total`, la boucle est coupée là par -t).
        # Sans fondu la chaîne reste octet pour octet celle d'avant.
        # R2 : mêmes courbes optionnelles que les clips (lin/absent = rien).
        mfi = min(float(music.get("fade_in") or 0), max(0.0, total))
        mfo = min(float(music.get("fade_out") or 0), max(0.0, total))
        mf = ""
        if mfi > 0:
            mf += (f"afade=t=in:st=0:d={round(mfi, 3)}"
                   f"{_fade_curve(music, 'fade_in_curve')},")
        if mfo > 0:
            mf += (f"afade=t=out:st={round(max(0.0, total - mfo), 3)}:"
                   f"d={round(mfo, 3)}{_fade_curve(music, 'fade_out_curve')},")
        # R1 : vitesse + effets aussi sur la musique (boucle coupée à `total`
        # par -t, la durée effective n'entre pas en jeu). Champs absents ⇒
        # chaîne historique intacte.
        mproc = ""
        mspd = float(music.get("speed") or 0.0)
        if mspd:
            mproc += f"atempo={sfx_service.fnum(mspd)},"
        mfx = music.get("fx_chain") or ""
        if mfx:
            mproc += mfx + ","
        # R4 : automation de volume de la musique — le flux bouclé n'est
        # jamais retrimé : t = horloge GLOBALE du rendu (0..total), les
        # points s'expriment donc en temps de MONTAGE (l'UI convertit et
        # l'affiche). Même position que les clips : après les fondus, avant
        # aresample ; se multiplie au gain statique. Sans points : chaîne
        # octet pour octet historique.
        mvp = music.get("volume_points")
        mautom = f"volume='{_vp_expr(mvp)}':eval=frame," if mvp else ""
        parts.append(
            f"[{idx}:a]{mproc}{mf}{mautom}"
            f"aresample=async=1,aformat=sample_rates=44100:"
            f"channel_layouts=stereo,volume={music['gain']}[mtrk]")
        music_lbl = "[mtrk]"
        idx += 1

    labels = []
    if voice_lbl:
        if len(voice_lbl) > 1:
            parts.append(f"{''.join(voice_lbl)}amix=inputs={len(voice_lbl)}:"
                         f"duration=longest:normalize=0[vall]")
        else:
            parts.append(f"{voice_lbl[0]}anull[vall]")
        if music_lbl and ducking:
            # P0 — LA CHAÎNE LATÉRALE DOIT DURER AUSSI LONGTEMPS QUE LA
            # MUSIQUE. MESURÉ, pas déduit : `sidechaincompress` rend un flux
            # qui s'arrête à la fin de son entrée la PLUS COURTE — 6 s de
            # musique sidechainée par 2 s de voix sortent à 2,0 s, pas à 6
            # (ffmpeg 8.1.1, celui du PATH de cette machine : c'est lui que
            # lance le « ffmpeg » nu émis plus bas ; mesure hors dépôt).
            # AUCUNE DÉCIMALE N'EST ÉCRITE ICI, ET C'EST DÉLIBÉRÉ : la même
            # commande relancée 12 fois sur le MÊME binaire rend 1,973696 /
            # 1,996916 / 2,000000 s (87040, 88064 ou 88200 échantillons — le
            # vidage des dernières trames n'est pas déterministe). Deux
            # revues successives ont lu cette dispersion comme un écart de
            # version, puis comme un écart de paramètres du filtre ; ce n'est
            # ni l'un ni l'autre, et une décimale de plus ici rouvrirait le
            # débat une quatrième fois. Le filtre n'expose AUCUNE option pour
            # décider de cette fin : `ffmpeg -h filter=sidechaincompress` ne
            # liste ni `shortest`, ni `eof_action`, ni `repeatlast` — vérifié
            # sur le 8.1.1 du PATH et sur le 9.0 embarqué de l'app. Allonger
            # le détecteur est donc le seul levier ; rien n'est affirmé ici
            # des internes d'ffmpeg, seul le comportement observé l'est. La
            # voix servant de détecteur, une voix de 2 s coupait NET la
            # musique bouclée d'un rendu de 4 s : le fichier sortait avec une
            # piste audio de 2 s dans une vidéo de 4 s — « la piste musique
            # n'est pas rendue » : elle l'était, jusqu'à la dernière syllabe
            # du commentaire, puis plus rien. Le silence n'était pas visible
            # dans la commande, seulement dans le FICHIER (ffprobe :
            # audio 2,0 s / vidéo 4,0 s) — cf.
            # tests/test_montage_pistes_rendu.py.
            parts.append("[vall]asplit=2[vsc0][vmix]")
            parts.append(f"[vsc0]apad=whole_dur={round(total, 3)}[vsc]")
            if isinstance(ducking, dict):
                # R1 : ducking paramétré {threshold, ratio, attack, release}
                # (sfx_service.parse_ducking). Le bool True historique garde
                # la ligne en dur ci-dessous, octet pour octet.
                parts.append(
                    f"{music_lbl}[vsc]sidechaincompress="
                    f"threshold={sfx_service.fnum(ducking['threshold'])}:"
                    f"ratio={sfx_service.fnum(ducking['ratio'])}:"
                    f"attack={sfx_service.fnum(ducking['attack'])}:"
                    f"release={sfx_service.fnum(ducking['release'])}[mduck]")
            else:
                parts.append(f"{music_lbl}[vsc]sidechaincompress="
                             "threshold=0.05:ratio=6:attack=50:release=400[mduck]")
            labels = ["[vmix]", "[mduck]"] + sfx_lbl
            music_lbl = None
        else:
            labels = ["[vall]"] + sfx_lbl
    else:
        labels = list(sfx_lbl)
    if music_lbl:
        labels.append(music_lbl)

    if labels:
        if len(labels) > 1:
            parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:"
                         f"duration=longest:normalize=0,"
                         f"aresample=async=1[outa]")
        else:
            parts.append(f"{labels[0]}aresample=async=1[outa]")
        amap = "[outa]"
    else:
        inputs.extend(["-f", "lavfi", "-i",
                       "anullsrc=channel_layout=stereo:sample_rate=44100"])
        amap = f"{idx}:a"

    if audio_only:
        # Mesure : le mix complet part dans ebur128 (framelog=verbose masque
        # le log par trame, seul le Summary sort au niveau info) puis est
        # jeté — aucun encodage, aucune vidéo.
        src = amap if amap.startswith("[") else f"[{amap}]"
        parts.append(f"{src}ebur128=peak=true:framelog=verbose[emeas]")
        cmd = ["ffmpeg", "-hide_banner", "-nostats", *inputs,
               "-filter_complex", ";".join(parts),
               "-map", "[emeas]", "-t", str(round(total, 3)),
               "-f", "null", "-"]
        return cmd, total

    # --- S1 : GRAVURE des sous-titres (dernier maillon de la chaîne vidéo) ---
    # `fontsdir` n'est pas une précaution : sans lui libass cherche dans les
    # fontes SYSTÈME, ne trouve pas les fontes embarquées (Anton, Bebas Neue,
    # Archivo Black… ne sont pas des fontes Windows) et retombe SILENCIEUSEMENT
    # sur une autre — le rendu cesserait de ressembler à l'aperçu sans qu'aucune
    # erreur ffmpeg ne le signale. subtitles_filter() le pose toujours.
    if subs_ass:
        from app.services.subtitle_service import subtitles_filter
        parts.append(f"[{cur}]{subtitles_filter(subs_ass)},"
                     f"format=yuv420p[outv]")
    else:
        parts.append(f"[{cur}]format=yuv420p[outv]")
    preset, crf, abr = (("veryfast", "30", "128k") if preview
                        else ("medium", "20", "192k"))
    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", ";".join(parts),
           "-map", "[outv]", "-map", amap,
           "-t", str(round(total, 3)),
           "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
           "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
           "-r", str(fps), "-c:a", "aac", "-b:a", abr,
           "-movflags", "+faststart", str(out)]
    return cmd, total


def _subs_ass(payload, canvas: tuple[int, int], stem: str) -> tuple[Path | None, dict]:
    """Piste S1 du payload de rendu → fichier ASS sur le disque.

    `payload` est la clé `subtitles` posée par l'éditeur, HORS du tableau
    `clips` (un sous-titre n'est pas un média) :
    `{style:{…vocabulaire du panneau…}, segments:[{start,end,text,words?}]}`.

    Le style est traduit par `subtitle_ui.ui_to_style` AVEC le canevas réel :
    le panneau exprime ses tailles en pixels de la LARGEUR de rendu, l'ASS en
    pixels ramenés à 1080 de HAUT. Sans cette conversion, un « 42 px » réglé
    dans l'aperçu sortirait à 75 px en 9:16 — l'aperçu mentirait.

    Les temps des segments sont ceux de la TIMELINE, c'est-à-dire exactement
    l'horloge sur laquelle l'audio est posé (`adelay`) : sous-titres et voix
    partagent donc la même référence, quoi que fassent les transitions.

    Retourne (chemin, infos) — (None, {}) si la piste est vide.
    """
    if not isinstance(payload, dict):
        return None, {}
    segs_in = [s for s in (payload.get("segments") or []) if isinstance(s, dict)]
    if not segs_in:
        return None, {}
    from app.services import subtitle_service as S
    from app.services import subtitle_ui as SU

    ui = payload.get("style") if isinstance(payload.get("style"), dict) else {}
    style = SU.ui_to_style(ui, canvas)
    karaoke = SU.ui_karaoke(ui)
    # Repli des lignes AVANT l'ASS, avec la regle du panneau : le fichier est
    # ecrit en WrapStyle 2 (libass ne replie rien tout seul), donc sans ce
    # passage une longue replique sortirait sur UNE ligne debordant du cadre
    # alors que l'apercu la montrait sur trois. Vu a l'image, pas deduit.
    segs_in = SU.ui_wrap_segments(segs_in, ui.get("maxChars"), style, canvas)
    segs = S.normalize_segments(segs_in)
    if not segs:
        return None, {}
    text = S.to_ass(segs, style, canvas=canvas, karaoke=karaoke,
                    karaoke_mode=SU.ui_karaoke_mode(ui),
                    anim=SU.ui_anim(ui))
    d = settings.outputs_path / "subtitles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{stem}.ass"
    # UTF-8 SANS BOM : libass lit le BOM comme un caractère et la première
    # ligne du script s'en trouve décalée.
    p.write_text(text, encoding="utf-8", newline="\n")
    info = {"segments": len(segs), "karaoke": karaoke,
            "font": style["font"], "font_fallback": style.get("font_fallback"),
            "unsupported": sorted(SU.ui_unsupported(ui, canvas))}
    return p, info


def _run_ffmpeg(cmd, out: Path) -> Path:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=FFMPEG_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"ffmpeg a dépassé {FFMPEG_TIMEOUT_S // 60} min — rendu interrompu.")
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        tail = (r.stderr or "")[-1200:]
        raise RuntimeError(f"ffmpeg a échoué ({r.returncode}) : {tail}")
    return out


@router.post("/render")
async def montage_render(request: Request, background_tasks: BackgroundTasks):
    """Body: {name?, ratio?, preview?, duration_master?, ducking?,
    mix?:{dialogue,musique,sfx} (dB), clips:[{tr:v1|v2|a1|a2|a3, src, start,
    end, srcIn?, transition?, transition_s?, gain? (dB −24..+12, multiplié au
    bus), fade_in?/fade_out? (s 0..3 ; musique A2 : sortie calée sur la fin
    du rendu), et pour les overlays V2 : opacity?, x?/y? (centre, fraction du
    canvas), scale? (largeur relative 0.05..3), rotate? (degrés −180..180) —
    sans x/y/scale/rotate l'overlay reste cover plein cadre comme avant}]}.

    R1 audio (rétrocompatible — payload historique ⇒ commande identique) :
    clips audio : fx? = [{type, params}] (vocabulaire sfx_service : filter/
    eq3/echo/reverb/distortion/stereo/compressor/denoise/deesser/normalize,
    types inconnus ignorés avec warning), speed? 0.5–2 (atempo — la durée
    effective du clip devient (end−start)/speed) ; ducking accepte le bool
    historique OU {enabled, ratio 2–20, attack_ms 5–500, release_ms 50–2000,
    threshold 0.01–0.3}.
    R2 : clips audio (a1/a2/a3) fade_in_curve? / fade_out_curve? ∈ lin|
    douce|expo|log (défaut lin) → afade curve= tri|hsin|exp|log ; lin ou
    absent n'émet rien (commande historique intacte), et sans fondu > 0 la
    courbe est sans effet.
    R4 : clips audio volume_points? = [{t, db}] (max 12, t s ≥ 0, db −40..
    +12 ; invalides ignorés avec warning) → automation de volume par
    interpolation LINÉAIRE en dB (volume='expr':eval=frame, après les afade,
    avant aresample), MULTIPLIÉE au gain de clip × bus. t est LOCAL au clip
    (0..durée) pour a1/a3 ; pour la musique A2 bouclée, t est le temps
    GLOBAL du rendu (0..total — le flux bouclé n'est jamais retrimé). Champ
    absent : commande historique intacte.
    R4b : overlays V2 motion_points? = [{t, x, y, rotate?}] (max 8, t s
    LOCAL au clip 0..durée, x/y −0.5..1.5, rotate −180..180 ; invalides
    ignorés avec warning) → keyframes de position : x/y interpolés
    linéairement par morceaux (constants avant le premier / après le dernier
    point), rotation animée si des points portent rotate ; scale reste
    STATIQUE (pas de keyframe d'échelle). Champ absent : commande
    historique intacte (transformée statique ou cover, comme avant).
    P1 : tracks? = [{id, kind, bus?, loop?}] — les pistes de la timeline dans
    l'ordre d'AFFICHAGE, du HAUT vers le BAS. Absent ⇒ table historique (v2
    overlay, v1 base, a1 dialogue, a2 musique bouclée, a3 sfx) et commande
    identique argument pour argument. Présent : toute piste `kind:"video"`
    autre que v1 est un overlay, composée d'autant plus HAUT qu'elle est
    listée haut ; les pistes `kind:"audio"` prennent le gain de leur `bus`
    (dialogue|musique|sfx — inconnu ⇒ sfx) ; la première piste `loop:true`
    fournit la MUSIQUE (seule entrée bouclée et seule à ducker la voix). Un
    clip dont la piste n'est pas déclarée est ignoré, comme avant.
    C4 : clips V1 speed? (0.25..4, défaut 1 ; invalide ignoré avec warning)
    → la fenêtre source consommée devient (end−start)×speed (bornée au
    disponible) et setpts=PTS/speed AVANT la normalisation fps remet la
    vidéo à sa durée timeline — transitions, trous et audio ne bougent pas ;
    AUCUN atempo (l'audio du plan V1 n'entre pas dans le graphe — le clip A1
    « son du plan » garde sa vitesse, l'UI le signale). Champ absent ou 1 :
    commande historique intacte.
    → {job_id} ; poll /api/jobs/{id}."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    clips = [c for c in (body.get("clips") or []) if isinstance(c, dict)]
    v1_in = sorted([c for c in clips if c.get("tr") == "v1"],
                   key=lambda c: float(c.get("start") or 0))
    if not v1_in:
        raise HTTPException(400, "Timeline sans clip vidéo — ajoute au moins "
                                 "un rendu ou un upload en piste V1.")

    preview = bool(body.get("preview"))
    ratio = str(body.get("ratio") or "9:16")
    w, h = _CANVAS.get(ratio, _CANVAS["9:16"])
    if preview:
        w, h = w // 4, h // 4
        w, h = w - w % 2, h - h % 2
    fps = 30
    mix = body.get("mix") or {}
    g_voice = _db_to_gain(mix.get("dialogue", -6))
    g_music = _db_to_gain(mix.get("musique", -18))
    g_sfx = _db_to_gain(mix.get("sfx", -12))
    # R1 : bool historique (True ⇒ paramètres en dur, inchangés) OU objet
    # {enabled, ratio, attack_ms, release_ms, threshold} → dict clampé.
    ducking = sfx_service.parse_ducking(body.get("ducking", True))
    duration_master = body.get("duration_master", True)
    # P1 : la LOI de classement des clips. Sans `tracks` c'est la table
    # historique — v2 overlay, a1 dialogue, a2 musique bouclée, a3 sfx.
    meta = _tracks_meta(body.get("tracks"))

    job_id = str(uuid4())
    short = job_id[:8]
    out_name = f"montage_{short}{'_preview' if preview else ''}.mp4"
    out = settings.outputs_path / "videos" / out_name
    title = (str(body.get("name") or "montage")[:60]
             + (" (aperçu 480p)" if preview else ""))

    async with async_session_factory() as session:
        session.add(JobRecord(
            id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=10,
            title=title, image_filename=out_name, aspect_ratio=ratio,
            provider="montage",
            current_step="Préparation des sources"))
        await session.commit()

    async def _fail(msg: str):
        async with async_session_factory() as session:
            jr = await session.get(JobRecord, job_id)
            if jr is not None:
                jr.status = JobStatus.FAILED.value
                jr.error = msg
                jr.current_step = "Échec"
                await session.commit()

    async def _run():
        try:
            loop = asyncio.get_running_loop()
            v1 = []
            for c in v1_in:
                p = await _resolve_src(c.get("src"))
                if p is None:
                    await _fail(f"Source vidéo introuvable : "
                                f"{c.get('label') or c.get('src')}")
                    return
                sdur = await loop.run_in_executor(None, _probe_duration, p)
                v1.append({"path": p, "src_dur": sdur or 9999.0,
                           "src_in": max(0.0, float(c.get("srcIn") or 0)),
                           "start": float(c.get("start") or 0),
                           "end": float(c.get("end") or 0),
                           "transition": c.get("transition"),
                           "transition_s": c.get("transition_s"),
                           "speed": _v1_speed(c),  # C4 — 0.0 = historique
                           "effects": (c.get("effects")
                                       if isinstance(c.get("effects"), list)
                                       else None)})
            v2 = []
            for c in clips:
                # P1 : TOUTE piste vidéo autre que v1 est un overlay — son
                # rang de composition vient de l'ordre des pistes, pas de son
                # identifiant. Piste inconnue de `meta` : clip ignoré, comme
                # l'ancien test d'égalité sur "v2" le faisait déjà.
                m = meta.get(c.get("tr"))
                if not m or m["kind"] != "video" or c.get("tr") == "v1":
                    continue
                p = await _resolve_src(c.get("src"))
                if p is None:
                    logger.warning(f"montage: overlay introuvable, ignoré — "
                                   f"{c.get('label') or c.get('src')}")
                    continue
                is_img = p.suffix.lower() in _IMAGE_EXTS
                sdur = (0.0 if is_img else
                        await loop.run_in_executor(None, _probe_duration, p))
                v2.append({"path": p, "is_image": is_img,
                           "src_dur": sdur or 9999.0,
                           "src_in": max(0.0, float(c.get("srcIn") or 0)),
                           "start": max(0.0, float(c.get("start") or 0)),
                           "end": float(c.get("end") or 0),
                           "opacity": c.get("opacity"),
                           "tf": _ov_transform(c),
                           "mp": _motion_points(c),
                           "layer": m["layer"]})
            a_clips, music = [], None
            for c in clips:
                m = meta.get(c.get("tr"))
                if not m or m["kind"] != "audio":
                    continue
                bus = m["bus"]
                p = await _resolve_src(c.get("src"))
                if p is None:
                    logger.warning(f"montage: audio introuvable, ignoré — "
                                   f"{c.get('label') or c.get('src')}")
                    continue
                # Une piste audio peut viser une vidéo (son d'un plan V1) :
                # sans flux audio, [idx:a] ferait échouer TOUT le rendu.
                if not await loop.run_in_executor(None, _has_audio_stream, p):
                    logger.warning(f"montage: source sans piste audio, ignorée — "
                                   f"{c.get('label') or p.name}")
                    continue
                sdur = await loop.run_in_executor(None, _probe_duration, p)
                # Mixage PAR CLIP : le gain (dB) se MULTIPLIE avec le gain de
                # bus (produit des linéaires) — 0 dB laisse le bus tel quel,
                # au chiffre près (rétro-compat bit à bit sans les champs).
                gdb, c_fi, c_fo = _clip_mix_params(c)
                # R1 : rack d'effets (chaîne ffmpeg pré-construite, "" sans
                # fx) + vitesse (0.0 = inchangé) — voir sfx_service.
                fx_ch = (sfx_service.fx_chain(sfx_service.sanitize_fx(
                    c.get("fx"), str(c.get("label") or c.get("tr"))))
                    if c.get("fx") else "")
                spd = sfx_service.clamp_speed(c.get("speed"))
                # R4 : volume_points sanitized ici (None sans le champ — la
                # commande émise reste alors l'historique, bit à bit).
                vp = _volume_points(c)
                # P1 : la piste `loop` du payload devient la MUSIQUE — la
                # seule entrée à porter `-stream_loop -1` et à alimenter le
                # sidechaincompress du ducking. Il n'y en a qu'une : le
                # PREMIER clip d'une piste bouclée. RESTE ASSUMÉ — un SECOND
                # clip du bus musique repart ici avec son GAIN musique
                # (corrigé), mais range son flux dans les bruitages : ni
                # bouclé, ni ducké. Ce n'est pas un point fermé.
                if m["loop"] and music is None:
                    music = {"path": p,
                             "gain": g_music if not gdb else
                             round(g_music * _db_to_gain(gdb), 4),
                             "fade_in": c_fi, "fade_out": c_fo,
                             "fade_in_curve": c.get("fade_in_curve"),
                             "fade_out_curve": c.get("fade_out_curve"),
                             "fx_chain": fx_ch, "speed": spd,
                             "volume_points": vp}
                else:
                    base = {"dialogue": g_voice, "musique": g_music,
                            "sfx": g_sfx}[bus]
                    a_clips.append({
                        "tr": "a1" if bus == "dialogue" else "a3",
                        "path": p, "src_dur": sdur or 9999.0,
                        "src_in": max(0.0, float(c.get("srcIn") or 0)),
                        "start": max(0.0, float(c.get("start") or 0)),
                        "end": float(c.get("end") or 0),
                        "gain": base if not gdb else
                        round(base * _db_to_gain(gdb), 4),
                        "fade_in": c_fi, "fade_out": c_fo,
                        "fade_in_curve": c.get("fade_in_curve"),
                        "fade_out_curve": c.get("fade_out_curve"),
                        "fx_chain": fx_ch, "speed": spd,
                        "volume_points": vp})

            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                jr.progress = 30
                jr.current_step = ("Rendu ffmpeg (aperçu 480p)" if preview
                                   else "Rendu ffmpeg")
                await session.commit()

            # S1 : l'ASS est écrit AVANT la commande (le filtre en a besoin).
            # Le canevas passé est celui du rendu RÉEL (aperçu 480p compris) :
            # les tailles suivent, un aperçu reste un aperçu fidèle.
            subs_ass, subs_info = await asyncio.to_thread(
                _subs_ass, body.get("subtitles"), (w, h), f"montage_{short}")

            cmd, total = _build_montage_command(
                v1, v2, a_clips, music, w=w, h=h, fps=fps,
                mix_db=mix, ducking=ducking,
                duration_master=duration_master, preview=preview, out=out,
                subs_ass=subs_ass)
            fx_n = sum(len(c["effects"] or []) for c in v1)
            logger.info(f"montage {short}: {len(v1)} clips V1 ({fx_n} effets), "
                        f"{len(v2)} overlays V2, {len(a_clips)} audio, "
                        f"musique={music is not None}, "
                        f"total≈{total}s → {out_name}")
            if subs_ass:
                logger.info(
                    f"montage {short}: gravure de {subs_info['segments']} "
                    f"sous-titres en {subs_info['font']} "
                    f"(karaoké={subs_info['karaoke']}) → {subs_ass.name}"
                    + (f" — non gravable : "
                       f"{', '.join(subs_info['unsupported'])}"
                       if subs_info["unsupported"] else ""))
            await asyncio.to_thread(_run_ffmpeg, cmd, out)

            dur = await loop.run_in_executor(None, _probe_duration, out)
            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                jr.status = JobStatus.DONE.value
                jr.progress = 100
                jr.final_video_path = str(out)
                jr.video_path = str(out)
                jr.duration_s = int(round(dur)) if dur else None
                jr.current_step = "Terminé"
                jr.completed_at = _dt.utcnow()
                await session.commit()
        except Exception as e:
            logger.exception(f"montage job {job_id} failed: {e}")
            await _fail(str(e))

    background_tasks.add_task(_run)
    return {"ok": True, "job_id": job_id, "preview": preview,
            "message": f"Rendu {'aperçu' if preview else 'final'} lancé — "
                       f"poll GET /api/jobs/{job_id}."}


# ---------------------------------------------------------------- measure ---

@router.post("/measure")
async def montage_measure(request: Request):
    """Loudness du MIX — même payload que /render, mais rien n'est encodé.

    Reconstruit le graphe AUDIO du rendu à l'identique (mêmes sources, gains,
    fondus, fx, vitesses, ducking, maître de durée — les durées des segments
    V1 sont recalculées depuis ffprobe pour caler `total`, fondus musique
    compris) via _build_montage_command(audio_only=True) : aucune vidéo
    décodée (seuls les flux :a sont référencés), le mix passe dans ebur128
    puis est jeté (-f null). → {ok, lufs_i, tp, lra, dur_s}.
    Synchrone (pas de job) : quelques secondes sur un montage court."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    clips = [c for c in (body.get("clips") or []) if isinstance(c, dict)]
    v1_in = sorted([c for c in clips if c.get("tr") == "v1"],
                   key=lambda c: float(c.get("start") or 0))
    if not v1_in:
        raise HTTPException(400, "Timeline sans clip vidéo — rien à mesurer.")
    mix = body.get("mix") or {}
    g_voice = _db_to_gain(mix.get("dialogue", -6))
    g_music = _db_to_gain(mix.get("musique", -18))
    g_sfx = _db_to_gain(mix.get("sfx", -12))
    ducking = sfx_service.parse_ducking(body.get("ducking", True))
    duration_master = body.get("duration_master", True)
    # P1 : MÊME loi de classement que /render — sans quoi la mesure entendrait
    # un autre mix que le rendu sur un projet à pistes personnalisées.
    meta = _tracks_meta(body.get("tracks"))

    # Résolution des sources — mêmes règles que /render (dupliquées à
    # dessein : le chemin de rendu reste intouché, non-régression oblige).
    loop = asyncio.get_running_loop()
    v1 = []
    for c in v1_in:
        p = await _resolve_src(c.get("src"))
        if p is None:
            raise HTTPException(400, f"Source vidéo introuvable : "
                                     f"{c.get('label') or c.get('src')}")
        sdur = await loop.run_in_executor(None, _probe_duration, p)
        v1.append({"path": p, "src_dur": sdur or 9999.0,
                   "src_in": max(0.0, float(c.get("srcIn") or 0)),
                   "start": float(c.get("start") or 0),
                   "end": float(c.get("end") or 0),
                   "transition": c.get("transition"),
                   "transition_s": c.get("transition_s"),
                   # C4 : la vitesse V1 peut changer la durée COUVERTE par un
                   # segment (source trop courte) — la mesure suit le rendu.
                   "speed": _v1_speed(c),
                   "effects": None})
    a_clips, music = [], None
    for c in clips:
        m = meta.get(c.get("tr"))
        if not m or m["kind"] != "audio":
            continue
        bus = m["bus"]
        p = await _resolve_src(c.get("src"))
        if p is None:
            logger.warning(f"measure: audio introuvable, ignoré — "
                           f"{c.get('label') or c.get('src')}")
            continue
        if not await loop.run_in_executor(None, _has_audio_stream, p):
            logger.warning(f"measure: source sans piste audio, ignorée — "
                           f"{c.get('label') or p.name}")
            continue
        sdur = await loop.run_in_executor(None, _probe_duration, p)
        gdb, c_fi, c_fo = _clip_mix_params(c)
        fx_ch = (sfx_service.fx_chain(sfx_service.sanitize_fx(
            c.get("fx"), str(c.get("label") or c.get("tr"))))
            if c.get("fx") else "")
        spd = sfx_service.clamp_speed(c.get("speed"))
        vp = _volume_points(c)  # R4 : la mesure entend l'automation du rendu
        if m["loop"] and music is None:   # P1 — même règle qu'au rendu
            music = {"path": p,
                     "gain": g_music if not gdb else
                     round(g_music * _db_to_gain(gdb), 4),
                     "fade_in": c_fi, "fade_out": c_fo,
                     "fade_in_curve": c.get("fade_in_curve"),
                     "fade_out_curve": c.get("fade_out_curve"),
                     "fx_chain": fx_ch, "speed": spd,
                     "volume_points": vp}
        else:
            base = {"dialogue": g_voice, "musique": g_music, "sfx": g_sfx}[bus]
            a_clips.append({
                "tr": "a1" if bus == "dialogue" else "a3",
                "path": p, "src_dur": sdur or 9999.0,
                "src_in": max(0.0, float(c.get("srcIn") or 0)),
                "start": max(0.0, float(c.get("start") or 0)),
                "end": float(c.get("end") or 0),
                "gain": base if not gdb else
                round(base * _db_to_gain(gdb), 4),
                "fade_in": c_fi, "fade_out": c_fo,
                "fade_in_curve": c.get("fade_in_curve"),
                "fade_out_curve": c.get("fade_out_curve"),
                "fx_chain": fx_ch, "speed": spd,
                "volume_points": vp})

    cmd, total = _build_montage_command(
        v1, [], a_clips, music, w=1080, h=1920, fps=30, mix_db=mix,
        ducking=ducking, duration_master=duration_master, preview=False,
        out=None, audio_only=True)

    def _measure():
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=180)
    try:
        r = await asyncio.to_thread(_measure)
    except subprocess.TimeoutExpired:
        raise HTTPException(502, "Mesure interrompue — ffmpeg a dépassé 3 min.")
    except (FileNotFoundError, OSError) as e:
        raise HTTPException(502, f"ffmpeg indisponible : {e}")
    if r.returncode != 0:
        tail = (r.stderr or "")[-400:]
        raise HTTPException(502, f"Mesure échouée ({r.returncode}) : {tail}")
    vals = sfx_service.parse_ebur128(r.stderr)
    logger.info(f"montage measure: I={vals['lufs_i']} LUFS, TP={vals['tp']} "
                f"dBFS, LRA={vals['lra']} LU sur {round(total, 3)} s")
    return {"ok": True, **vals, "dur_s": round(total, 3)}
