# -*- coding: utf-8 -*-
"""Montage (écran 07) → pipeline de rendu ffmpeg réel.

Câblage « timeline → rendu » du handoff son_vfx_montage :

  GET  /api/montage/project   Timeline initiale construite depuis les VRAIS
                              assets de la Bibliothèque (rendus + uploads en
                              V1, voix off en A1, musique en A2), durées
                              ffprobe. {has_assets:false} si la Bibliothèque
                              est vide → l'écran garde sa démo. P8 : seule de
                              la VIDÉO entre en V1 (`_VIDEO_EXTS`) —
                              `final_video_path` porte aussi les planches PNG
                              de `sprite2d` et les maillages GLB d'`asset3d`.
                              P8-bis : cette liste blanche est DANS LA
                              REQUÊTE, pas seulement dans la boucle — sinon
                              60 planches plus récentes que la dernière vidéo
                              consommaient la fenêtre et l'écran retombait
                              sur sa démo EN SILENCE, base pleine de rendus.
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
import re
import subprocess
from datetime import datetime as _dt
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from loguru import logger
from sqlalchemy import func, or_, select

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


# P8 — extensions qu'un DÉMULTIPLEXEUR vidéo sait ouvrir. La liste est
# FERMÉE par choix : `sprite2d` range sa planche PNG et `asset3d` son maillage
# GLB dans la MÊME colonne `final_video_path` qu'un rendu `seedance`, et un
# jour un provider de plus fera pareil. Une liste blanche se lit ; une liste
# noire se contourne toute seule.
# MESURE, protocole nommé (voir l'en-tête de tests/test_montage_sources.py
# pour le détail) : ffprobe 9.0-essentials_build, commande
# `ffprobe -v error -select_streams v -show_entries stream=codec_type
#  -of csv=p=0 <fichier>`, 12 appels après 3 de chauffe, médiane, machine
# Windows 11 / AMD64 Family 23. Sur les assets RÉELS : 74 à 84 ms par planche
# PNG, 99 à 102 ms par maillage GLB — et la sonde REND « video » SUR UN PNG
# (rc=0, « video », vérifié sur trois planches ; rc=1 sur deux maillages).
# Elle n'aurait donc écarté aucune des trois planches de sprites de
# l'utilisateur, seulement le maillage — que l'extension écarte pour 0 ms.
# Pas de sonde, donc ; le trou qui reste (un `.mp4` de zéro octet, un `.webm`
# tronqué) tombe sur le message lisible de `_run_ffmpeg`, où « Invalid data
# found » est l'un des motifs remontés.
_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")
_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus",
               ".aiff", ".aif", ".wma")


def _is_video_artifact(p: Path) -> bool:
    return p.suffix.lower() in _VIDEO_EXTS


def _ffmpeg_ouvrira(p: Path) -> bool:
    """Vrai si un démultiplexeur ffmpeg sait ouvrir ce fichier.

    La frontière du PRÉ-VOL n'est pas « vidéo » mais « ce que ffmpeg sait
    ouvrir », et c'est une UNION PLATE : la MÊME pour toute piste média. Un
    `.wav` posé sur V1 passe, un `.mp4` posé sur A1 passe (MESURÉ : HTTP 200
    dans les deux sens — bancs `prevol_laisse_passer_un_son_sur_v1` et
    `prevol_laisse_passer_une_video_sur_a1`). C'est un CHOIX, pas un oubli :

      * une vidéo sur une piste audio est un geste SUPPORTÉ — le son d'un
        plan V1, cf. la garde `_has_audio_stream` de `_run` plus bas ;
        différencier symétriquement le casserait ;
      * différencier dans l'autre sens seul (« pas de fichier sans image sur
        une piste vidéo ») ne se décide PAS à l'extension : un `.mkv`, un
        `.mp4`, un `.webm` peuvent ne porter aucun flux vidéo. Il faudrait la
        sonde ffprobe que la mesure ci-dessus écarte.

    Ce que le pré-vol refuse, c'est ce qu'AUCUN démultiplexeur n'ouvre — un
    maillage, une archive, un JSON. Il ne juge pas la PERTINENCE d'un média
    sur une piste ; ce qui reste tombe sur le message lisible de
    `_run_ffmpeg`. Cette dernière phrase a été FAUSSE du 04/09/2026 jusqu'au
    correctif P8-bis, et c'est la docstring qui mentait, pas le code :
    MESURÉ (ffmpeg.exe 9.0-essentials_build de %LOCALAPPDATA%\\
    DeepotusVideoGen\\bin\\, stderr capturé en UTF-8, un `.wav` référencé par
    `[0:v]` dans un `-filter_complex` — la forme même que `_run` construit,
    cf. l.1527/1550/1558 ; scratchpad/mesure_ffmpeg_wav.py), le diagnostic
    est « Stream specifier ':v' in filtergraph description […] matches no
    streams. » et `_ffmpeg_lignes_utiles` rendait `[]` : le message
    retombait sur la tranche brute, et le diagnostic y arrivait à l'offset
    999 sur 1200 — la reproduction exacte du défaut que P8 corrigeait
    ailleurs. Le motif « matches no streams » a été ajouté à
    `_FFMPEG_MOTIFS` POUR que cette phrase devienne vraie ; la ligne de banc
    qui la tient est `motif_flux_absent`. Une image, elle, est légitime
    des deux côtés (carton fixe
    V1, incrustation V2) : `ovPicker()` du bundle propose « Images
    (Bibliothèque) » sur TOUTE piste vidéo, le filtre y est
    `trackKind(tr)==="audio"`. `_IMAGE_EXTS` est défini plus bas, avec le
    reste du rendu."""
    return p.suffix.lower() in _VIDEO_EXTS + _IMAGE_EXTS + _AUDIO_EXTS


# P8 — les lignes de stderr qui DÉCIDENT. Tout le reste (bannière de
# compilation, dumps de flux) est du bruit : sur l'échec réel du 04/09/2026,
# la ligne utile arrivait à l'offset 1069 d'une tranche de 1200 CARACTÈRES,
# coupée au milieu des drapeaux de build.
#
# P8-bis — les cinq premiers motifs ne couvraient QUE l'ouverture d'une
# ENTRÉE et le choix d'un encodeur ; toute la classe « graphe de filtres »
# rendait ZÉRO motif, donc la tranche brute. C'est la classe la plus probable
# pour un service qui construit un `filter_complex` de cette taille (xfade,
# overlay, volume='expr', adelay, subtitles).
# PROTOCOLE de la mesure (scratchpad/mesure_ffmpeg.py) : ffmpeg.exe
# 9.0-essentials_build-www.gyan.dev de %LOCALAPPDATA%\DeepotusVideoGen\bin\,
# entrées fabriquées par lavfi, stderr capturé en UTF-8 (errors="replace") et
# passé à la VRAIE `_ffmpeg_lignes_utiles` importée du service.
#   cas                                    motifs AVANT / APRÈS
#   .wav référencé par [0:v] (le pré-vol répond 200)     0 / 1
#   filtre inconnu dans filter_complex                   0 / 1
#   étiquette de sortie inexistante                      0 / 2
#   expression de filtre invalide (scale=w=oups)         0 / 1
#   dossier de sortie absent                             2 / 3
#   mp4 de zéro octet                                    3 / 3
#   encodeur inconnu                                     1 / 3
# Les OFFSETS ne sont volontairement pas cités ici : mesurés entre 916 et
# 1113 sur 1200 selon le cas, ils dépendent de la longueur du chemin
# temporaire de la machine et ne sont donc pas reproductibles au caractère —
# le chiffre qui l'est, et le seul qui décide, est « 0 motif ».
# « Error opening output » et non « Error opening output file » : ffmpeg émet
# les deux formes (« Error opening output <chemin>: … » de l'étage muxer,
# « Error opening output file <chemin>. » de l'étage CLI, « Error opening
# output files: … » en résumé), et le préfixe court les prend toutes les
# trois. « Error opening input file » ne valait QUE pour l'entrée.
_FFMPEG_MOTIFS = ("Error opening input file", "Invalid data found",
                  "No such file", "Conversion failed", "Unknown encoder",
                  "matches no streams", "Error parsing filterchain",
                  "Error initializing filters", "Error opening output")


def _ffmpeg_lignes_utiles(stderr: str, limite: int = 5) -> list:
    """Les lignes de `stderr` portant un motif de `_FFMPEG_MOTIFS`, dans
    l'ordre, sans doublon, plafonnées. Liste vide = rien de reconnu, et le
    message d'erreur reste alors celui d'avant, caractère pour caractère."""
    vues, out = set(), []
    for ligne in (stderr or "").splitlines():
        s = ligne.strip()
        if not s or s in vues:
            continue
        if any(m in s for m in _FFMPEG_MOTIFS):
            vues.add(s)
            out.append(s if len(s) <= 200 else s[:200] + "…")
            if len(out) >= limite:
                break
    return out


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


def _write_json_atomic(path: Path, data: dict) -> None:
    """Écriture atomique (tmp voisin + replace) — laisse remonter OSError
    (l'endpoint la traduit en 500, l'UI affiche « sauvegarde impossible »).
    Le tmp est retiré si le remplacement échoue : sinon le dossier finirait
    par se remplir de fragments qu'aucune route ne relit."""
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


def _write_saved(data: dict) -> None:
    """La timeline COURANTE, écrite d'un bloc. Même mécanique que les projets
    nommés (P5) — un seul endroit à relire pour savoir comment ce dossier est
    écrit."""
    _write_json_atomic(_saved_path(), data)


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


def _save_record(body) -> dict:
    """Le modèle de timeline COURANTE, normalisé depuis un corps client — et
    le SEUL endroit où cette normalisation vit. Lève HTTPException(400) sur
    une forme invalide ou un volume déraisonnable.

    Extrait de `POST /save` le 04/09/2026 pour que `POST /projects` accepte la
    timeline AFFICHÉE dans son corps sans recopier ces quinze lignes : deux
    normalisations pour un même objet auraient divergé au premier champ
    ajouté, et c'est l'objet que le disque garde."""
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
    return data


# --------------------------------------------------------------- projets ---
# P5 — un montage NOMMÉ est un fichier de montage_projects/, voisin de la
# timeline courante. Le courant reste le seul brouillon vivant : il porte
# `project_id`, et l'autosave miroite dedans. Rien ici ne remplace la
# sauvegarde courante — c'est elle que GET /project sert, projet ou pas.


async def _json_body(request: Request) -> dict:
    """Corps JSON, ou {} — un POST sans corps (« dupliquer ») n'est pas une
    erreur, et ce qui n'est pas un objet ne porte aucun champ attendu."""
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


# Le VERROU d'écriture du lot. Toutes les écritures de ce module passent par
# ici — SAUF UNE, et il faut la nommer : `DELETE /api/montage/save`
# (`montage_save_delete`) efface le courant HORS de ce verrou. Sans
# conséquence connue : c'est le bouton « bibliothèque » de l'éditeur, et le
# bundle ABANDONNE sa requête d'autosave en vol avant de le frapper (même
# geste que `svmLibReset`, gardé par test_montage_bundle.py), donc aucune
# écriture n'est en vol au moment où il passe. Le rapatrier ne réparerait rien
# de mesuré ; l'écrire ici évite qu'une lecture rapide croie la phrase plus
# large qu'elle n'est. Les écritures couvertes sont brèves (un `json.dumps` et
# un `os.replace`), donc le coût est nul. Ce qu'il ferme, MESURÉ le
# 04/09/2026 :
# `POST /save` teste l'existence du projet (`_load_project`) puis franchit DEUX
# sauts `asyncio.to_thread` — dont une écriture de fichier entière — avant
# d'écrire le miroir. Un `DELETE` d'une autre fenêtre glissé dans cette fenêtre
# faisait RESSUSCITER le projet supprimé (fichier revenu, HTTP 200 des deux
# côtés). Le banc [16] de test_montage_projets.py joue l'entrelacement,
# avec et sans ce verrou.
_ecrit = asyncio.Lock()


def _projects_dir(create: bool = False) -> Path:
    """Le dossier des projets. `create=False` par défaut, et c'est le point :
    cet accesseur est traversé par `_project_path` → `_load_project` → cinq
    routes en LECTURE SEULE. MESURÉ : un unique `GET /projects/m_jamaisvu`
    (404) suffisait à semer `montage_projects/` chez un utilisateur qui n'a
    jamais nommé un montage. Les trois routes qui ÉCRIVENT le demandent."""
    d = settings.images_path.parent / "montage_projects"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _pid(raw) -> str:
    """Un identifiant ne désigne JAMAIS qu'un fichier de CE dossier :
    `Path(...).name` mange `../`, `..\\` et tout séparateur. MESURÉ le
    04/09/2026, contre ce que ce commentaire affirmait d'abord : il ne mange
    PAS `.` ni `..` eux-mêmes — `Path("..").name` vaut `".."` (la propriété
    ne rend "" que pour une racine ou un lecteur). D'où le rejet explicite :
    sans lui, l'identifiant `..` désignait le fichier « ...json » du dossier,
    inoffensif mais que rien n'empêchait de créer. Borné à 24 caractères (les
    nôtres en font 10)."""
    s = Path(str(raw)).name
    return "" if s in (".", "..") else s[:24]


def _project_path(pid, create: bool = False) -> Path:
    return _projects_dir(create) / f"{_pid(pid)}.json"


def _load_project(pid) -> dict | None:
    """Le projet, ou None — absent, illisible, corrompu, forme inattendue.
    Un identifiant qui se réduit à rien ne peut donner qu'un None."""
    if not _pid(pid):
        return None
    p = _project_path(pid)
    try:
        if not p.is_file():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning(f"montage: projet illisible, ignoré — {p.name}")
        return None
    return d if isinstance(d, dict) else None


def _project_meta(d: dict, fallback_id: str = "") -> dict:
    """Ce que la LISTE rend. Jamais les clips eux-mêmes : une liste de vingt
    projets porterait des milliers de clips que personne ne regarde à cet
    instant — leur NOMBRE suffit à choisir."""
    return {"id": d.get("id") or fallback_id or None,
            "name": d.get("name"),
            "updated_at": d.get("saved_at"),
            "clips": len(d.get("clips") or []),
            "ratio": d.get("ratio"),
            "duration": d.get("duration")}


_NOM_TETE = " ./\\"      # tabulations et sauts de ligne : déjà mangés comme
                        # caractères de contrôle, inutile de les répéter ici


def _libelle(s: str) -> str:
    """Le nettoyage d'un LIBELLÉ, et rien de plus. Ce qui est retiré :
      * les caractères de CONTRÔLE, partout — un `\\n` ou un `\\x00` dans un
        nom traverse la liste et casse l'affichage sans rien apporter ;
      * les points et les séparateurs EN TÊTE seulement — `../x` → `x`,
        `..` → `` (donc repli), `.` → `` .
    Ce qui n'est PAS retiré : un séparateur AU MILIEU. C'est le correctif du
    04/09/2026, et il vient d'une mesure : `Path(...).name` coupait tout ce
    qui précédait le dernier `/`, donc « Bande-annonce 16/9 » était stocké
    « 9 » et « Ep.3 / v2 finale » devenait « v2 finale ». `16/9` et `4/3` sont
    des MOTS de ce domaine. Le nom n'a d'ailleurs jamais gardé le fichier :
    celui-ci s'appelle `m_<hex8>.json` et c'est `_pid` — lui seul — qui est la
    frontière du système de fichiers."""
    s = "".join(ch for ch in s if ord(ch) >= 32 and ch != "\x7f")
    return s.strip().lstrip(_NOM_TETE).strip()


def _project_name(raw, fallback) -> str:
    """Le nom est un LIBELLÉ, jamais un chemin — le fichier, lui, est nommé
    par l'identifiant. Ce qui n'est pas une chaîne, ce qui est vide et ce qui
    ne survit pas à `_libelle` retombe sur `fallback` : sans ce repli, un
    champ effacé aurait fabriqué le libellé « None »."""
    s = _libelle(raw if isinstance(raw, str) else "")
    if not s:
        s = _libelle(str(fallback or "")) or "montage"
    return s[:80]


def _now_iso() -> str:
    return _dt.utcnow().replace(microsecond=0).isoformat() + "Z"


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
    theme/music/bgm/…) en A2.

    P8 : seuls les jobs dont l'artefact porte une extension de `_VIDEO_EXTS`
    entrent en V1. La SAUVEGARDE, elle, n'est jamais élaguée de ses clips V1
    non-vidéo : ils sont seulement listés dans `v1_non_video` (et au journal)
    — voir le commentaire dans la boucle.

    CONTRAT de `v1_non_video`, arrêté ici et non plus implicite : ce sont des
    IDENTIFIANTS de clips, joignables un à un aux `clips` servis par la même
    réponse — rien d'autre. La tâche 16 lit ce champ pour marquer les clips à
    l'écran ; un repli qui aurait rendu un libellé ou un nom de fichier lui
    aurait donné une liste hétérogène que rien ne peut rejoindre. Un clip V1
    non-vidéo SANS `id` exploitable est donc EXCLU du champ (et le champ est
    absent si aucun fautif n'a d'id) ; il reste nommé au journal par son
    libellé, et le 400 du pré-vol le nommera au moment du rendu. C'est un
    choix : mieux vaut un marquage incomplet qu'un identifiant inventé."""
    saved = await asyncio.to_thread(_load_saved)
    if saved is not None:
        kept, pruned, non_video, non_video_dits = [], 0, [], []
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
                # P8 — un clip V1 qui n'est pas une vidéo est SIGNALÉ, jamais
                # élagué. Élaguer viderait la piste V1 d'une sauvegarde comme
                # celle du 04/09/2026 (montage_saved.json, 5980 o, RELU le
                # 04/09 : 17 clips — 4 V1 fautifs, 9 segments de sous-titres
                # mot à mot SANS `src`, une voix A1, une musique A2, deux
                # incrustations V2) — la garde `any(c["tr"] == "v1")` plus bas
                # ferait alors repartir la construction depuis la
                # Bibliothèque, et 13 clips de travail seraient perdus pour en
                # retirer 4. À UNE CONDITION, qui vaut d'être dite : sur ces
                # 13, seuls les 9 sous-titres survivent inconditionnellement
                # (src null). Les 4 autres — voix, musique, DEUX
                # incrustations — ne tiennent que tant que leur source
                # existe ; l'élagage déjà en place juste au-dessus les retire
                # sinon (`saved_pruned`). L'argument tient donc sur 9 clips
                # garantis et 4 conditionnels, pas sur 13 garantis. Le
                # pré-vol du rendu nomme les fautifs ; c'est l'utilisateur qui
                # décide.
                if c.get("tr") == "v1" and not _is_video_artifact(p):
                    # DEUX listes, et c'est le point : `non_video` est le
                    # champ d'API — des IDENTIFIANTS, rien d'autre, pour que
                    # la tâche 16 puisse les rejoindre aux `clips`.
                    # `non_video_dits` est le journal, qui a le droit d'être
                    # hétérogène parce qu'un humain le lit : un clip sans id
                    # y garde son libellé ou son nom de fichier au lieu de
                    # disparaître.
                    cid = c.get("id")
                    if isinstance(cid, str) and cid:
                        non_video.append(cid)
                    non_video_dits.append(cid or c.get("label") or p.name)
            kept.append(c)
        if non_video_dits:
            logger.warning(
                f"montage: {len(non_video_dits)} clip(s) V1 de la sauvegarde "
                f"ne sont pas des vidéos — "
                f"{', '.join(str(x) for x in non_video_dits)}"
                f" ; le rendu les refusera nommément s'ils ne s'ouvrent pas.")
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
            # P5 : de quel projet nommé cette timeline est le brouillon. Sans
            # cette clé, l'éditeur rouvrait toujours « sans titre » et le
            # premier autosave venu cassait le lien.
            if isinstance(saved.get("project_id"), str) and saved["project_id"]:
                out["project_id"] = saved["project_id"]
            if pruned:
                out["saved_pruned"] = True
                out["pruned"] = pruned
            if non_video:
                out["v1_non_video"] = non_video   # P8 — signalé, pas élagué
            return out
        # Sauvegarde présente mais plus AUCUN clip V1 à source valide : elle
        # est inexploitable — la Bibliothèque reprend la main (le prochain
        # autosave d'une édition réelle l'écrasera).
        logger.warning("montage: sauvegarde sans clip V1 exploitable — "
                       "timeline reconstruite depuis la Bibliothèque")
    async with async_session_factory() as session:
        # P8-bis — la liste blanche est POUSSÉE DANS LA REQUÊTE, pour que les
        # 60 lignes de la fenêtre soient 60 CANDIDATS et non 60 lignes dont la
        # boucle écarte ensuite la plupart. Sans ce `where`, le filtre Python
        # ci-dessous CONSOMMAIT le budget : 60 planches et maillages plus
        # récents que la dernière vidéo suffisaient à ne rien trouver, à poser
        # `has_assets` à faux et à faire retomber l'écran sur sa démo — les
        # rendus seedance restant en base, invisibles. MESURÉ (base sqlite
        # neuve, N jobs `sprite2d` à `final_video_path = sheet.png` tous plus
        # récents qu'un unique `seedance` .mp4 valide, un GET
        # /api/montage/project par valeur de N, scratchpad/mesure_seuil.py) :
        # N = 3/55/56/57/58/59 → has_assets vrai, le seedance en V1 ; N = 60
        # → has_assets FAUX, clips vides ; idem 61 et 80. Le seuil est
        # exactement 60, par construction.
        # Ce n'est pas un cas d'école : sur une COPIE de la base RÉELLE
        # (%LOCALAPPDATA%\DeepotusVideoGenData\deepotus.db + -wal + -shm,
        # 04/09/2026, lecture seule, scratchpad/mesure_base_reelle.py) les 60
        # lignes les plus récentes portent déjà 15 non-vidéos (8 `sprite2d`
        # .png, 7 `asset3d` .glb) et la liste COMMENCE par 10 non-vidéos
        # consécutives : 50 de marge, et les derniers commits de la branche
        # principale sont tous du pipeline 3D.
        #
        # FORME du `where`, choisie SUR MESURE (scratchpad/mesure_ilike.py,
        # base neuve, 8 jobs couvrant les cas) : le filtre Python plus bas lit
        # `fp = j.final_video_path or j.video_path`, donc un `where` sur la
        # seule colonne `final_video_path` — la forme proposée par la revue —
        # ÉCARTE des jobs légitimes. Mesuré sur les 5 jobs que le filtre
        # Python accepte : `final_video_path` seul en manque 2 (celui dont
        # `final_video_path` est NULL et celui dont il est vide, tous deux à
        # `video_path` .mp4) ; un OR sur les DEUX colonnes n'en manque aucun
        # mais en prend un de TROP (planche en `final_video_path`, .mp4 en
        # `video_path` — il consommerait le budget qu'on vient de rendre) ;
        # `coalesce(nullif(final_video_path, ''), video_path)` est le MIROIR
        # EXACT du `or` de Python — 0 manquant, 0 en trop. C'est cette
        # forme-là. (`nullif(x, '')` fait la chaîne vide, que `coalesce` seul
        # ne verrait pas, alors que le `or` de Python la traverse.)
        # `ilike` et non `like`, et il faut dire exactement ce que ça achète
        # — sinon c'est une préférence, pas une décision. MESURÉ : SQLAlchemy
        # compile `ilike` en `lower(col) LIKE lower(?)` sur SQLite, alors que
        # `like` émet un LIKE nu. Or le LIKE de SQLite est DÉJÀ insensible à
        # la casse pour l'ASCII par défaut : sous `PRAGMA
        # case_sensitive_like = 0`, les deux formes rendent les MÊMES lignes
        # (`a.mp4`, `Rush_Camera.MOV`, `b.Mp4` — les trois, dans les deux
        # cas). Elles ne se séparent que sous `PRAGMA case_sensitive_like =
        # 1`, où le LIKE nu ne garde plus que `a.mp4` quand la forme
        # `lower()/lower()` garde les trois. `ilike` met donc
        # l'insensibilité dans la REQUÊTE, où elle ne dépend ni d'un pragma
        # ni du dialecte. CONSÉQUENCE ASSUMÉE : aucune mutation du banc ne
        # distingue les deux formes sur ce backend-ci (mesuré, `ilike` →
        # `like` laisse le banc au vert plein) ; c'est la mesure ci-dessus
        # qui porte le choix, pas une ligne de banc.
        # Le cas concret que tout ceci sert : un `Rush_Camera.MOV` déposé par
        # l'upload UGC (routes.py, qui teste en minuscules mais ÉCRIT la casse
        # d'origine). Aucune extension de `_VIDEO_EXTS` ne porte de
        # métacaractère LIKE (`%`, `_`) : le motif `%<ext>` est littéral.
        _fp = func.coalesce(func.nullif(JobRecord.final_video_path, ""),
                            JobRecord.video_path)
        res = await session.execute(
            select(JobRecord).where(JobRecord.status == JobStatus.DONE.value)
            .where(or_(*[_fp.ilike(f"%{e}") for e in _VIDEO_EXTS]))
            .order_by(JobRecord.completed_at.desc()).limit(60))
        jobs = res.scalars().all()

    vids = []
    for j in jobs:
        fp = j.final_video_path or j.video_path
        if not fp or not Path(fp).exists():
            continue
        # P8 — `final_video_path` n'est PAS une promesse de vidéo : `sprite2d`
        # y range sa planche PNG, `asset3d` son maillage GLB. Sans ce test,
        # les quatre jobs les plus RÉCENTS gagnaient la piste V1 quels qu'ils
        # soient, `_probe_duration` rendait 0 sur un PNG, le repli `or 4.0`
        # donnait quatre cartons de 4 s — et les 35 rendus seedance de la
        # base, plus anciens, n'étaient jamais atteints.
        # Il RESTE alors même que le `where` ci-dessus dit déjà la même chose,
        # et ce n'est pas une redondance : la requête ne peut filtrer que ce
        # que la BASE porte, ce test-ci juge le CHEMIN effectivement retenu.
        # Il reste donc la seule autorité, et le `where` n'est qu'un
        # pré-filtre qui ne doit jamais écarter ce que ce test accepterait —
        # c'est la propriété que `coalesce(nullif(...))` a été choisi pour
        # tenir, et que la mesure ci-dessus vérifie job par job.
        if not _is_video_artifact(Path(fp)):
            logger.info(f"montage: job {j.id[:8]} ({j.provider}) ecarte de V1 — "
                        f"{Path(fp).suffix or 'sans extension'} n'est pas une video")
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


# ------------------------------------------------------ versions plus récentes ---
# P6 — « j'ai régénéré ce plan ». Le rapprochement se fait PAR LE TITRE, et
# c'est une HEURISTIQUE : rien en base ne relie deux rendus successifs du même
# plan (pas de colonne « refait à partir de »). La réponse le DIT, avec le
# vocabulaire déjà employé par la Bibliothèque (`origin: depot|heuristique`,
# library_index.py) — proposer un rapprochement deviné sans le nommer serait
# le laisser passer pour un lien établi.
#
# LE SUFFIXE NORMALISÉ EST MESURÉ, PAS SUPPOSÉ. Le plan écrivait
# « (aperçu 480p) » de mémoire ; relevé le 04/09/2026 sur une COPIE de
# %LOCALAPPDATA%\DeepotusVideoGenData\deepotus.db (+ -wal + -shm, lecture
# seule, sqlite3 stdlib) : 8 lignes le portent, TOUTES `provider='montage'`,
# et le seul point du dépôt qui l'ajoute est `montage_render` (l. 2406 —
# le commit précédent écrivait 2253, le numéro du fichier PARENT : citer un
# numéro d'avant ses propres ajouts, c'est citer un AUTRE fichier).
# Les 8 se répartissent 4 `done` / 4 `failed`, et les 4 `done` sont TOUS
# les jobs `montage` `done` de la base : le suffixe n'est pas une
# curiosité, c'est la marque de tout aperçu.
# CONSÉQUENCE À DIRE : les candidats excluant déjà `montage`, ce suffixe ne
# peut mordre que sur le job de RÉFÉRENCE — un clip dont la source est un
# rendu de montage. Le normaliser reste juste, mais son gain est celui-là.
_RE_APERCU = re.compile(r"\s*\(aperçu 480p\)\s*$")


def _norm_title(t) -> str:
    """Le titre d'un job réduit à ce qui identifie LE PLAN : sans le suffixe
    d'aperçu, sans espaces de bord, sans casse."""
    return _RE_APERCU.sub("", str(t or "")).strip().lower()


@router.get("/newer")
async def montage_newer(job_id: str = ""):
    """Les rendus plus RÉCENTS qui portent le même titre que `job_id` — au
    plus 5, du plus récent au plus ancien. C'est ce que l'inspecteur du
    Montage propose sous « Remplacer la source… ».

    `{ok, origin: "heuristique", candidates: [{job_id, title, completed_at,
    duration_s}]}`. Job inconnu, sans titre exploitable ou sans date : liste
    VIDE, jamais une erreur — l'inspecteur n'affiche alors rien du tout.

    QUATRE DÉCISIONS, chacune appuyée sur une mesure et non sur le plan.

    1. SEULEMENT DES VIDÉOS, par le MÊME chemin que `montage_project`. La
       leçon de P8 vaut ici mot pour mot : `sprite2d` range sa planche PNG et
       `asset3d` son maillage GLB dans la MÊME colonne `final_video_path`
       qu'un rendu `seedance`. Sans ce filtre, une planche de sprites serait
       proposée comme « nouvelle version » d'un plan. `_is_video_artifact`
       reste la SEULE autorité (elle juge le chemin retenu) et le `where`
       n'est qu'un pré-filtre, écrit dans la forme démontrée par P8-bis :
       `coalesce(nullif(final_video_path, ''), video_path)`, miroir exact du
       `or` de Python — ni un job légitime écarté, ni un job de trop admis.

    2. AUCUNE `.limit()` SUR LA REQUÊTE. Le plafond de 5 est pris APRÈS le
       filtre de titre, donc il borne des CANDIDATS et non des lignes brutes.
       C'est exactement le défaut que P8-bis a payé : une fenêtre SQL que le
       filtre Python consomme rend une liste vide et silencieuse. Le nombre
       de lignes chargées est borné par le `where` lui-même — les vidéos
       `done` non-montage TERMINÉES APRÈS le clip qu'on remplace — donc par
       la fraîcheur de la timeline, pas par la taille de la base (mesure :
       116 jobs `done` au total sur la base réelle du 04/09/2026).

    3. LE TITRE N'EST PAS PRÉ-FILTRÉ EN SQL, et c'est un choix mesuré. La
       forme tentante `title ILIKE '%' || norm || '%'` est un SUR-ENSEMBLE en
       Python… mais pas en SQLite : `lower()` y est ASCII SEULEMENT (pas
       d'ICU par défaut), donc `lower('Épisode')` reste `'Épisode'` et ne
       correspond plus au `'épisode'` que produit `str.lower()` de Python. Un
       job intitulé « Épisode … » — le titre PAR DÉFAUT de
       `pipeline.run_episode` — serait silencieusement écarté. C'est
       précisément la classe de bug (« une clause SQL qui écarte des jobs
       légitimes ») que P8-bis a déjà rencontrée : le titre se compare donc
       en Python, où la normalisation est celle qui décide.

    4. `coalesce(provider, '')`, PAS `provider != "montage"`. En SQL,
       `NULL != 'montage'` vaut NULL et la ligne est ÉCARTÉE. MESURÉ sur la
       copie de la base réelle : 13 jobs `done` portent `provider IS NULL`,
       et les 13 sont des `.mp4`. Aucun ne porte de titre AUJOURD'HUI — la
       correction ne change donc rien d'observable sur cette base-là : elle
       ferme un piège, elle ne répare pas un défaut constaté.

    CE QUE CETTE ROUTE N'AFFIRME PAS : que le candidat SOIT une nouvelle
    version. Deux rendus peuvent partager un titre sans rien avoir en commun
    (mesuré : « tweet_2026-05-20 » couvre 7 jobs). C'est pourquoi la réponse
    porte `origin` et pourquoi l'écran nomme le titre AVANT de remplacer."""
    empty = {"ok": True, "origin": "heuristique", "candidates": []}
    if not job_id:
        return empty
    async with async_session_factory() as session:
        ref = await session.get(JobRecord, job_id)
        if ref is None or ref.completed_at is None:
            return empty
        # LE GARDE-FOU QUI N'EST PAS AU PLAN, et que la base réelle impose :
        # 61 des 97 jobs vidéo `done` non-montage n'ont PAS de titre. Sans
        # cette sortie, chacun d'eux proposerait cinq inconnus comme « ses »
        # versions plus récentes — un rapprochement entre deux vides n'est
        # pas un rapprochement.
        # CE CHIFFRE A ÉTÉ FAUX, et la faute mérite d'être nommée : il
        # valait « 48 des 84 » parce que la mesure avait été prise avec
        # `provider != 'montage'` — LE BUG QUE LA LIGNE CI-DESSOUS
        # CORRIGE. Les 13 jobs `done` à `provider IS NULL` tombaient donc
        # de la mesure comme ils tombaient de la requête : 84+13 = 97,
        # 48+13 = 61. Mesurer une décision sous le défaut qu'elle répare,
        # c'est mesurer le monde d'avant.
        norm = _norm_title(ref.title)
        if not norm:
            return empty
        _fp = func.coalesce(func.nullif(JobRecord.final_video_path, ""),
                            JobRecord.video_path)
        res = await session.execute(
            select(JobRecord)
            .where(JobRecord.status == JobStatus.DONE.value)
            .where(func.coalesce(JobRecord.provider, "") != "montage")
            # PAS de `id != job_id` — le plan l'écrivait, la mesure le rend
            # INUTILE : la comparaison de date est STRICTE, et la référence
            # n'est pas plus récente qu'elle-même. Mutation jouée le
            # 04/09/2026 (clause retirée) : 74/0, aucune ligne rouge — c'était
            # du code mort. La propriété, elle, reste tenue et mesurée
            # (`newer_ne_se_propose_pas_lui_meme`), par la ligne ci-dessous.
            .where(JobRecord.completed_at > ref.completed_at)
            .where(or_(*[_fp.ilike(f"%{e}") for e in _VIDEO_EXTS]))
            .order_by(JobRecord.completed_at.desc()))
        jobs = res.scalars().all()

    out = []
    for j in jobs:
        fp = j.final_video_path or j.video_path
        if not fp:
            continue
        p = Path(fp)
        # `_is_video_artifact` juge le chemin RETENU, là où le `where` ne
        # peut juger que la chaîne stockée — c'est la même hiérarchie que
        # dans `montage_project`, et c'est elle qui décide.
        if not _is_video_artifact(p):
            continue
        # Un candidat dont le fichier a disparu n'est pas une sortie : le
        # rendu mourrait dessus et GET /project élaguerait le clip au
        # rechargement. On ne propose pas un piège.
        if not p.exists():
            continue
        if _norm_title(j.title) != norm:
            continue
        out.append({
            "job_id": j.id,
            "title": j.title,
            "completed_at": (j.completed_at.isoformat()
                             if j.completed_at is not None else None),
            "duration_s": j.duration_s,
        })
        if len(out) >= 5:
            break
    return {"ok": True, "origin": "heuristique", "candidates": out}


@router.get("/effects")
async def montage_effects():
    """Catalogue du moteur Effects / Mask pour le sélecteur d'effets par clip
    de l'inspecteur (labels FR + paramètres par type)."""
    from app.services import effects_engine
    return {"effects": effects_engine.catalog()}


@router.get("/media-rules")
async def montage_media_rules():
    """La RÈGLE d'extensions vidéo, telle que le rendu l'applique — servie au
    sélecteur d'assets de l'éditeur pour qu'il n'en fabrique pas une seconde
    copie.

    P9. `ovPicker()` du bundle listait ses « Rendus vidéo » sur le critère
    `status == "done" and (video_path or final_video_path)` — EXACTEMENT
    celui que P8 vient de corriger ici. Les planches `sprite2d` et les
    maillages `asset3d` y étaient donc encore proposés, et rien n'empêchait
    l'utilisateur de reposer à la main les clips que P8 écarte. Une copie de
    `_VIDEO_EXTS` écrite en JavaScript aurait divergé de celle-ci au premier
    format ajouté ; le client interroge donc CETTE liste, la même que celle
    que lit `_is_video_artifact`.

    La réponse ne porte QUE ce qui a un lecteur — un champ sans lecteur est
    un mensonge poli. Le client qui n'obtient pas cette route ne filtre PAS
    et le dit à l'écran ; il ne devine pas une liste de son côté."""
    return {"video_exts": list(_VIDEO_EXTS)}


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
    data = _save_record(body)
    clips = data["clips"]
    # P5 : de quel projet NOMMÉ cette timeline est le brouillon. Deux gardes,
    # et chacune ferme un trou mesuré :
    #  * seule une CHAÎNE est retenue — le plan écrivait `str(...)`, qui aurait
    #    fabriqué un fichier « {'a': 1}.json » que la liste aurait ensuite
    #    présenté comme un projet ;
    #  * l'identifiant doit désigner un fichier EXISTANT. L'autosave MET À JOUR
    #    un projet, il n'en CRÉE jamais : sans ce test, supprimer le projet
    #    ouvert le faisait ressusciter à la seconde suivante, par l'autosave
    #    d'une fenêtre qui n'avait rien demandé.
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > _SAVE_MAX_BYTES:
        raise HTTPException(400, "Sauvegarde refusée — plus de 2 Mo.")
    # LE TEST D'EXISTENCE ET LES DEUX ÉCRITURES SOUS LE MÊME VERROU. Entre le
    # `_load_project` et le miroir il y a DEUX sauts `asyncio.to_thread` ; un
    # `DELETE` d'une autre fenêtre glissé là faisait revenir le fichier qu'il
    # venait d'effacer (mesuré : le projet ressuscitait, HTTP 200 des deux
    # côtés). Avec `_ecrit`, le DELETE passe soit entièrement avant — `lie`
    # est alors None, rien n'est miroité — soit entièrement après, et il
    # emporte le fichier que le miroir venait de réécrire.
    async with _ecrit:
        pid = body.get("project_id")
        pid = _pid(pid) if isinstance(pid, str) else ""
        lie = await asyncio.to_thread(_load_project, pid) if pid else None
        if lie is not None:
            data["project_id"] = pid
        try:
            await asyncio.to_thread(_write_saved, data)
            # le MIROIR : le projet nommé suit les éditions sans un geste. Son
            # échec fait échouer la sauvegarde entière — l'éditeur garde
            # « NON ENREGISTRÉ » et réessaie, plutôt que d'annoncer un
            # enregistrement dont la moitié n'a pas eu lieu. CE QU'IL LAISSE
            # DERRIÈRE, mesuré par [15] : le COURANT est déjà écrit (il
            # porte la timeline neuve et son `project_id`), le PROJET reste à
            # sa version précédente, et pas un `.tmp` ne subsiste.
            if data.get("project_id"):
                # le NOM appartient au PROJET, pas au payload : sans cette
                # ligne, renommer dans le popover puis laisser passer un
                # autosave rendait au projet son ancien nom, sans un mot.
                # MESURÉ — c'est ce qui faisait sortir « abysse (copie) » là
                # où le projet s'appelait « Abysse v1 ».
                await asyncio.to_thread(
                    _write_json_atomic, _project_path(data["project_id"]),
                    dict(data, id=data["project_id"],
                         name=lie.get("name") or data["name"]))
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


# ---------------------------------------------------------- /projects (P5) ---


@router.get("/projects")
async def montage_projects():
    """Les projets nommés, MÉTADONNÉES seules, le plus récemment enregistré en
    tête. Un fichier illisible est SAUTÉ : un seul projet corrompu ne doit pas
    emporter la liste de tous les autres."""
    def _scan():
        out = []
        dossier = _projects_dir()
        if not dossier.is_dir():
            return out          # aucun montage nommé : le dossier n'existe
                                # pas encore, et LIRE ne doit pas le créer
        # `dossier`, pas `d` : la boucle réutilise `d` pour le projet lu, et
        # deux sens pour un même nom dans dix lignes finit toujours mal.
        for f in dossier.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.warning(f"montage: projet illisible, ignoré — {f.name}")
                continue
            if isinstance(d, dict):
                out.append(_project_meta(d, f.stem))
        # `str(...)` : un `saved_at` numérique venu d'un fichier bricolé
        # ferait lever la comparaison et emporterait la liste entière.
        out.sort(key=lambda p: str(p.get("updated_at") or ""), reverse=True)
        return out
    return {"ok": True, "projects": await asyncio.to_thread(_scan)}


@router.post("/projects")
async def montage_project_create(request: Request):
    """{name, timeline?} — la timeline AFFICHÉE devient un projet nommé, et le
    courant en devient le brouillon : il reçoit `project_id`, l'autosave
    miroite ensuite.

    `timeline` est le payload de `POST /save` — le modèle client complet. Il
    est là depuis le 04/09/2026, et il ferme la porte d'entrée de tout le lot.
    MESURÉ : sans lui, cette route ne lisait QUE `montage_saved.json`, et deux
    états courants n'en ont pas — une installation neuve (la Bibliothèque
    fournit la timeline, `svmApplyProject` pose `setDirty(false)`, donc aucun
    autosave ne part) et l'instant qui suit le bouton « bibliothèque » (DELETE
    de la sauvegarde puis rechargement : le même état). L'utilisateur
    regardait une timeline et le popover lui répondait en rouge qu'il n'y en
    avait pas. Second trou, même racine : la sauvegarde sur disque a jusqu'à
    1,5 s de retard sur l'écran, donc « Enregistrer sous… » nommait un
    instantané périmé — 7 clips affichés, 1 clip écrit.

    À DÉFAUT de `timeline`, le courant fait toujours foi (une fenêtre plus
    ancienne, un appel en ligne de commande). 400 dans un seul cas, et il est
    vrai : l'écran est RÉELLEMENT vide — ni corps, ni courant, ou pas un seul
    clip. Il n'y aurait rien à nommer."""
    body = await _json_body(request)
    tl = body.get("timeline")
    if isinstance(tl, dict) and isinstance(tl.get("clips"), list):
        cur = _save_record(tl)          # même normalisation que POST /save
        if len(json.dumps(cur, ensure_ascii=False).encode("utf-8")) \
                > _SAVE_MAX_BYTES:
            raise HTTPException(400, "Sauvegarde refusée — plus de 2 Mo.")
    else:
        cur = await asyncio.to_thread(_load_saved)
    if cur is None or not cur.get("clips"):
        raise HTTPException(400, "Aucune timeline à enregistrer.")
    pid = f"m_{uuid4().hex[:8]}"
    rec = dict(cur, id=pid, project_id=pid,
               name=_project_name(body.get("name"), cur.get("name")))
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_json_atomic,
                                    _project_path(pid, create=True), rec)
            await asyncio.to_thread(_write_saved, rec)
        except OSError as e:
            raise HTTPException(500, f"Écriture du projet impossible : {e}")
    return {"ok": True, **_project_meta(rec)}


@router.get("/projects/{pid}")
async def montage_project_read(pid: str):
    """Le projet ENTIER (clips compris) — c'est ce que l'éditeur applique."""
    d = await asyncio.to_thread(_load_project, pid)
    if d is None:
        raise HTTPException(404, "Projet introuvable.")
    return d


@router.patch("/projects/{pid}")
async def montage_project_rename(pid: str, request: Request):
    """{name} — renommer, rien d'autre. `saved_at` est repoussé : c'est lui
    qui ordonne la liste, et un projet qu'on vient de renommer est le dernier
    touché. Un nom VIDE garde l'ancien plutôt que de fabriquer « montage » :
    l'utilisateur a effacé le champ, il n'a pas demandé un autre nom."""
    d = await asyncio.to_thread(_load_project, pid)
    if d is None:
        raise HTTPException(404, "Projet introuvable.")
    body = await _json_body(request)
    p = _pid(pid)
    rec = dict(d, id=p, project_id=p, saved_at=_now_iso(),
               name=_project_name(body.get("name"), d.get("name")))
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_json_atomic,
                                    _project_path(p, create=True), rec)
        except OSError as e:
            raise HTTPException(500, f"Écriture du projet impossible : {e}")
    return {"ok": True, **_project_meta(rec)}


@router.post("/projects/{pid}/duplicate")
async def montage_project_duplicate(pid: str):
    """Une COPIE indépendante, sous un identifiant neuf. Le suffixe est ajouté
    APRÈS la coupe à 80 caractères de la base : collé avant, il aurait été le
    premier rogné et la copie serait revenue avec le nom exact de l'original,
    à côté de lui dans la liste."""
    d = await asyncio.to_thread(_load_project, pid)
    if d is None:
        raise HTTPException(404, "Projet introuvable.")
    nid = f"m_{uuid4().hex[:8]}"
    suff = " (copie)"
    base = _project_name(d.get("name"), "montage")[:80 - len(suff)]
    rec = dict(d, id=nid, project_id=nid, name=base + suff,
               saved_at=_now_iso())
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_json_atomic,
                                    _project_path(nid, create=True), rec)
        except OSError as e:
            raise HTTPException(500, f"Écriture du projet impossible : {e}")
    return {"ok": True, **_project_meta(rec)}


@router.post("/projects/{pid}/open")
async def montage_project_open(pid: str):
    """Le projet REMPLACE la timeline courante. GESTE DESTRUCTIF : ce que le
    courant portait n'est copié nulle part et RIEN ne le rend — l'éditeur arme
    donc le bouton avant de frapper (M14) et le dit dans sa note. La fenêtre
    qui ouvre annule d'abord son autosave en vol, sinon il retomberait sur le
    projet fraîchement ouvert avec le contenu de l'ancien.

    409 si le projet est INOUVRABLE — plus un seul plan V1 dont la source
    existe. La règle est celle de GET /project au mot près (un clip SANS src
    compte, un clip dont la source a disparu ne compte pas) : sans elle, ouvrir
    un tel projet écrasait la timeline courante pour ne rien afficher, et si
    elle n'avait pas de nom elle était perdue — ce geste est le seul du lot
    qui pouvait détruire un montage sans qu'on ait rien demandé de destructif.
    """
    d = await asyncio.to_thread(_load_project, pid)
    if d is None:
        raise HTTPException(404, "Projet introuvable.")
    ouvrable = False
    for cl in (d.get("clips") or []):
        if not isinstance(cl, dict) or cl.get("tr") != "v1":
            continue
        if not cl.get("src") or await _resolve_src(cl.get("src")) is not None:
            ouvrable = True
            break
    if not ouvrable:
        raise HTTPException(
            409, f"« {d.get('name') or pid} » n'a plus un seul plan dont la "
                 f"source existe : il ne peut pas être ouvert, et la timeline "
                 f"affichée n'a pas été touchée.")
    p = _pid(pid)
    rec = dict(d, id=p, project_id=p)
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_saved, rec)
        except OSError as e:
            raise HTTPException(500, f"Ouverture impossible : {e}")
    return {"ok": True, **_project_meta(rec)}


@router.delete("/projects/{pid}")
async def montage_project_delete(pid: str):
    """Suppression IRRÉVERSIBLE du fichier — rien ne la rejoue, ni ici ni à
    l'écran (l'historique du Montage ne mémorise que {clips, mixDb}).
    Si c'était le projet OUVERT, le courant est DÉLIÉ : sans cela le prochain
    autosave le recréerait aussitôt. C'est le second verrou de la même panne,
    le premier étant côté POST /save (qui ne miroite que dans un fichier
    existant) — la timeline courante, elle, n'est pas touchée.
    TROISIÈME verrou, ajouté le 04/09/2026 : le retrait passe sous `_ecrit`.
    Les deux premiers bornaient la course entre deux fenêtres SANS la fermer
    — mesuré, un DELETE glissé entre le test d'existence de POST /save et son
    miroir faisait revenir le fichier."""
    p = _project_path(pid)
    if not _pid(pid) or not p.is_file():
        raise HTTPException(404, "Projet introuvable.")

    def _rm():
        try:
            p.unlink()
        except OSError as e:
            return str(e)
        cur = _load_saved()
        if cur is not None and cur.get("project_id") == _pid(pid):
            try:
                _write_saved({k: v for k, v in cur.items()
                              if k != "project_id"})
            except OSError as e:
                logger.warning(f"montage: le courant reste lié au projet "
                               f"supprimé — {e}")
        return ""

    async with _ecrit:
        err = await asyncio.to_thread(_rm)
    if err:
        raise HTTPException(500, f"Suppression impossible : {err}")
    return {"ok": True, "deleted": True}


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
    # P2 — animation MOT PAR MOT. `report` dit ce qui a REELLEMENT été gravé :
    # une réplique trop longue (déjà repliée par ui_wrap_segments) ou dont la
    # largeur n'a pas pu être mesurée retombe sur le karaoké `\k`. Sans ce
    # retour, le panneau annoncerait « rebond » sur une piste qui n'en porte
    # aucun, et rien dans le journal ne le dirait.
    wa = SU.ui_word_anim(ui)
    rep: dict = {}
    text = S.to_ass(segs, style, canvas=canvas, karaoke=karaoke,
                    karaoke_mode=SU.ui_karaoke_mode(ui),
                    anim=SU.ui_anim(ui), word_anim=wa, report=rep)
    d = settings.outputs_path / "subtitles"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{stem}.ass"
    # UTF-8 SANS BOM : libass lit le BOM comme un caractère et la première
    # ligne du script s'en trouve décalée.
    p.write_text(text, encoding="utf-8", newline="\n")
    info = {"segments": len(segs), "karaoke": karaoke,
            "font": style["font"], "font_fallback": style.get("font_fallback"),
            "word_anim": wa,
            "word_segments": rep.get("word_segments", 0),
            "word_anim_skipped": list(rep.get("word_anim_skipped") or []),
            "word_anim_broken": list(rep.get("word_anim_broken") or []),
            "word_anim_unmeasured": list(rep.get("word_anim_unmeasured") or []),
            "unsupported": sorted(SU.ui_unsupported(ui, canvas))}
    # RESTE ASSUMÉ, dit ici pour n'être pas découvert ailleurs : ce dict ne
    # quitte pas le serveur. Son unique lecteur en aval est le `logger.info`
    # du rendu — il n'entre ni dans JobRecord, ni dans la réponse de la route,
    # ni dans le polling. Le panneau n'apprend donc RIEN d'un rebond qui n'a
    # pas eu lieu ; seuls les bancs le lisent, sur la valeur de retour.
    if wa != "none" and info["word_anim_unmeasured"]:
        info["unsupported"].append("wordAnim:mesure impossible (PIL/fonte)")
    if wa != "none" and info["word_anim_skipped"]:
        info["unsupported"].append(
            "wordAnim:%d réplique(s) ne tiennent pas sur une ligne — karaoké"
            % len(info["word_anim_skipped"]))
    if wa != "none" and info["word_anim_broken"]:
        info["unsupported"].append(
            "wordAnim:%d réplique(s) dont un mot commence après la fin — karaoké"
            % len(info["word_anim_broken"]))
    # L'animation d'ENTRÉE du bloc (fondu, pop) ne se pose pas sur les
    # répliques animées mot par mot — mesuré : l'ASS sort sans le moindre
    # `\fad`. On ne la grave pas (un `\fad` par mot doublerait l'entrée du
    # rebond) ; sans cette ligne le panneau montrait fondu + rebond et le
    # rendu perdait le fondu, sans un mot.
    if wa != "none" and info["word_segments"] and SU.ui_anim(ui) != "none":
        info["unsupported"].append(
            "anim:l'animation d'entrée du bloc ne se pose pas sur les "
            "répliques animées mot par mot (un événement ASS par mot)")
    # « couleur » EST le karaoké : karaoké éteint, elle ne fait plus rien du
    # tout. Mesuré : ni `\k`, ni `\pos`, et la chip restait allumée dessus
    # avec son infobulle qui parle de couleur.
    if not karaoke and str((ui or {}).get("wordAnim") or "") == "couleur":
        info["unsupported"].append(
            "wordAnim:« couleur » EST le karaoké — karaoké éteint, aucun mot "
            "ne change de couleur")
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
        # P8 — la tranche brute est GARDÉE, mais elle passe DERRIÈRE la ligne
        # qui décide. Mesuré le 04/09/2026 sur l'échec réel : « Error opening
        # input file … model.glb » arrivait à l'offset 1069 de ces 1200
        # caractères, après six lignes de drapeaux de compilation. Sans motif
        # reconnu, le message ne change pas d'un caractère.
        lignes = _ffmpeg_lignes_utiles(r.stderr or "")
        if lignes:
            raise RuntimeError(
                f"ffmpeg a échoué ({r.returncode}) : " + " | ".join(lignes)
                + "\n--- journal ffmpeg (fin) ---\n" + tail)
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
    P8 : PRÉ-VOL avant la création du JobRecord — toute source résolue qu'un
    démultiplexeur ffmpeg n'ouvrira pas (maillage, archive, JSON…) fait
    répondre 400 en nommant le libellé du clip et le fichier, et RIEN n'entre
    en file d'attente. Une image reste légitime (carton fixe V1, incrustation
    V2) et un son sur une piste audio : la frontière est « ce que ffmpeg sait
    ouvrir », pas « vidéo ». Une source DISPARUE n'est pas concernée : ce
    chemin reste inchangé.
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

    # P8 — PRÉ-VOL. Un rendu qui ne peut pas aboutir ne doit coûter ni une
    # entrée de file d'attente ni deux minutes d'attente : les sources sont
    # résolues ICI, avant le JobRecord, et celles qu'aucun démultiplexeur
    # n'ouvrira sont refusées NOMMÉMENT. Le 04/09/2026 un `model.glb` posé en
    # V1 par la construction automatique tuait ffmpeg à la 1700e ligne du
    # journal ; l'utilisateur lisait une tranche de stderr coupée au milieu
    # de la bannière de compilation. Une source DISPARUE n'est pas l'affaire
    # du pré-vol : ce chemin reste celui d'avant (échec nommé dans `_run`
    # pour V1, warning et clip ignoré pour les overlays et l'audio).
    refus = []
    for c in clips:
        m = meta.get(c.get("tr"))
        if not m or m["kind"] == "subs" or not isinstance(c.get("src"), dict):
            continue
        p = await _resolve_src(c.get("src"))
        if p is not None and not _ffmpeg_ouvrira(p):
            # P8-bis — le NOMBRE de fautifs était borné (`refus[:8]` plus bas),
            # la LONGUEUR de chacun ne l'était pas : `label`, `id` et `tr`
            # sont des chaînes CLIENTES arbitraires, et huit libellés de dix
            # mille caractères faisaient un `detail` de 80 ko. Le voisin
            # immédiat borne déjà de la même façon (`title` du JobRecord,
            # `[:60]`) ; on s'aligne. Le nom de fichier, lui, vient du disque
            # et le système de fichiers le borne déjà.
            dit = str(c.get("label") or c.get("id") or c.get("tr") or "?")[:60]
            refus.append(f"« {dit} » → {p.name}")
    if refus:
        raise HTTPException(
            400, f"Rendu impossible : {len(refus)} source(s) qu'aucun lecteur "
                 f"ffmpeg n'ouvrira — {' ; '.join(refus[:8])}. Un maillage 3D "
                 f"n'est pas un plan : retire ces clips de la timeline, ou "
                 f"remplace-les par une vidéo (mp4/mov/webm) ou une image "
                 f"(png/jpg).")

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
                    f"(karaoké={subs_info['karaoke']}, "
                    f"mot={subs_info.get('word_anim')} sur "
                    f"{subs_info.get('word_segments')}/"
                    f"{subs_info['segments']}) → {subs_ass.name}"
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
