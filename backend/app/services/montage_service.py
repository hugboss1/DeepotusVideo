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
  GET  /api/montage/transitions   D-20 — les 58 xfade de l'ffmpeg livré, par
                              familles, avec le drapeau `live` (jouable en
                              direct par le lecteur vivant). Catalogue SERVI :
                              le client n'en a aucune copie.
  GET  /api/montage/titles    D-21 — les huit gabarits de titre (libellé FR,
                              fonte, corps, couleur, boîte, animation).
  GET  /api/montage/title-preview  D-21 — l'aperçu PNG 9:16 d'un titre, gravé
                              par le MÊME ASS que le rendu ; largeur bornée
                              96..640, cache d'un jour, 400 sans texte.
  GET  /api/montage/peaks     P7 — l'enveloppe d'onde d'une source, précalculée
                              et mise en cache (JSON rendu par `peaks`, jamais
                              un chemin : voir la route). `bins` écrêté
                              8..2000.
  GET  /api/montage/strip     P7 — une planche de vignettes (JPEG), VIDÉO
                              seulement (`_is_video_artifact`).
  POST /api/montage/proxy     P7 — fabrique l'aperçu 480p en tâche de fond
                              (JobRecord provider="montage_proxy", SANS aucun
                              chemin d'artefact : un cache n'est pas un plan).
  GET  /api/montage/proxy     P7 — sert cet aperçu s'il existe, 404 sinon.
                              Les quatre sont bornées à la boucle locale et
                              calculées par `montage_media` ; leur cache vit
                              dans outputs/montage_cache/, hors de tout
                              dossier que le dépôt énumère.
  GET  /api/montage/export    D-37 — la timeline SAUVEGARDÉE en EDL CMX 3600
                              (?format=edl) ou FCPXML 1.9 (?format=fcpxml),
                              pièce jointe texte ; calcul PUR dans
                              `edl_export`, sources résolues et sondées ici.
                              400 : format inconnu, aucune timeline.
  POST /api/montage/scenes    D-42 — {src, srcIn, dur, threshold?} → {ok,
                              times} : les changements de plan (scdet) de
                              l'extrait, en secondes relatives à srcIn ;
                              `scenes.detect`, cache dans montage_cache/.
                              400 paramètres, 404 source, 415 non vidéo.
  POST /api/montage/reframe   D-40 — {src, srcIn, dur} → {ok, mode, points,
                              fps, x?, motion} : le suivi horizontal du
                              mouvement de l'extrait (`reframe.motion_track`,
                              cache dans montage_cache/) pour le champ V1
                              `reframe`. 400 paramètres, 404, 415.
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
from datetime import datetime as _dt, timedelta as _td, timezone as _tz
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from loguru import logger
from sqlalchemy import func, or_, select

from app.config import settings
from app.models.schemas import JobStatus
from app.services import autoclips as _autoclips
from app.services import edl_export as _edl
from app.services import mask_region as _mr
from app.services import reframe as _reframe
from app.services import scenes as _scenes
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

# D-20 (21/09/2026) — LES 58 TRANSITIONS DE L'FFMPEG LIVRÉ (8.1.1 essentials,
# `-h filter=xfade`, indices 0…57), par familles. Chaque nom xfade est SA
# PROPRE clé : le client stocke des noms nus (svmTransBase garde le premier
# mot) et cette table est la seule autorité — GET /transitions la sert, le
# client n'en a pas de copie. Les neuf clés historiques restent au-dessus.
_XFADE_FAMILIES = {
    "fondus":      {"label": "fondus",      "noms": ["fade", "fadeblack", "fadewhite", "fadegrays",
                                                     "fadefast", "fadeslow", "dissolve", "distance"]},
    "glissements": {"label": "glissements", "noms": ["slideleft", "slideright", "slideup", "slidedown",
                                                     "coverleft", "coverright", "coverup", "coverdown",
                                                     "revealleft", "revealright", "revealup", "revealdown"]},
    "volets":      {"label": "volets",      "noms": ["wipeleft", "wiperight", "wipeup", "wipedown",
                                                     "wipetl", "wipetr", "wipebl", "wipebr",
                                                     "smoothleft", "smoothright", "smoothup", "smoothdown",
                                                     "diagtl", "diagtr", "diagbl", "diagbr"]},
    "formes":      {"label": "formes",      "noms": ["circlecrop", "rectcrop", "circleopen", "circleclose",
                                                     "vertopen", "vertclose", "horzopen", "horzclose", "radial"]},
    "zooms":       {"label": "zooms",       "noms": ["zoomin", "squeezeh", "squeezev"]},
    # `distance` (famille fondus) n'a ni direction ni forme, juste un mélange
    # pixel à pixel — plus proche d'un fondu que des cinq autres familles.
    "pixels":      {"label": "pixels",      "noms": ["pixelize", "hblur", "hlslice", "hrslice", "vuslice",
                                                     "vdslice", "hlwind", "hrwind", "vuwind", "vdwind"]},
}
# `update` plutôt qu'une boucle `for _f/_n` : cette dernière laissait `_f` et
# `_n` en variables de MODULE (fuite constatée en revue).
_XFADE.update({n: (n, None) for f in _XFADE_FAMILIES.values() for n in f["noms"]
               if n not in _XFADE})
# Ceux que le lecteur VIVANT sait jouer en CSS (D-12) : un voile noir/blanc,
# ou une baisse d'opacité — tout le reste n'est visible qu'après Preview.
_XFADE_LIVE = ("fade", "fadeblack", "fadewhite")
_XFADE_LABELS = {  # libellés français du catalogue ; le nom xfade reste l'id
    "fade": "fondu", "fadeblack": "fondu noir", "fadewhite": "fondu blanc",
    "fadegrays": "fondu gris", "fadefast": "fondu rapide", "fadeslow": "fondu lent",
    "dissolve": "dissolution", "distance": "distance",
    "slideleft": "glisse à gauche", "slideright": "glisse à droite",
    "slideup": "glisse en haut", "slidedown": "glisse en bas",
    "coverleft": "couvre à gauche", "coverright": "couvre à droite",
    "coverup": "couvre en haut", "coverdown": "couvre en bas",
    "revealleft": "révèle à gauche", "revealright": "révèle à droite",
    "revealup": "révèle en haut", "revealdown": "révèle en bas",
    "wipeleft": "volet gauche", "wiperight": "volet droit",
    "wipeup": "volet haut", "wipedown": "volet bas",
    "wipetl": "volet ↖", "wipetr": "volet ↗", "wipebl": "volet ↙", "wipebr": "volet ↘",
    "smoothleft": "volet doux gauche", "smoothright": "volet doux droit",
    "smoothup": "volet doux haut", "smoothdown": "volet doux bas",
    "diagtl": "diagonale ↖", "diagtr": "diagonale ↗",
    "diagbl": "diagonale ↙", "diagbr": "diagonale ↘",
    "circlecrop": "cercle (recadre)", "rectcrop": "rectangle (recadre)",
    "circleopen": "cercle ouvre", "circleclose": "cercle ferme",
    "vertopen": "rideau vertical ouvre", "vertclose": "rideau vertical ferme",
    "horzopen": "rideau horizontal ouvre", "horzclose": "rideau horizontal ferme",
    "radial": "balayage radial",
    "zoomin": "zoom avant", "squeezeh": "écrase horizontal", "squeezev": "écrase vertical",
    "pixelize": "pixélisé", "hblur": "flou horizontal",
    "hlslice": "tranches → droite", "hrslice": "tranches → gauche",
    "vuslice": "tranches ↑", "vdslice": "tranches ↓",
    "hlwind": "vent → droite", "hrwind": "vent → gauche",
    "vuwind": "vent ↑", "vdwind": "vent ↓",
}


def transitions_catalog() -> dict:
    """Le catalogue que le client affiche : familles ordonnées, items {id, label, live}."""
    return {"familles": [
        {"id": k, "label": f["label"],
         "items": [{"id": n, "label": _XFADE_LABELS.get(n, n), "live": n in _XFADE_LIVE}
                   for n in f["noms"]]}
        for k, f in _XFADE_FAMILIES.items()]}


# 4:5 était proposé par les menus du bundle et géré par animation_service,
# mais absent d'ici : un montage en 4:5 retombait silencieusement en 9:16.
_CANVAS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
           "4:5": (1080, 1350)}
_MUSIC_HINT = ("theme", "music", "bgm", "track", "musique", "instrumental")

# --- D-35 (23/09/2026) : PRESETS DE SORTIE ---------------------------------
# Un preset ne fixe PAS le ratio (il reste celui du projet) mais la CLASSE
# de taille `side`, l'encodeur, le pix_fmt, l'audio, l'extension et les
# drapeaux de conteneur. `master_1080` reproduit OCTET POUR OCTET la queue
# historique de `_build_montage_command` (banc l4 [1] : `BUILD()` ==
# `BUILD(preset="master_1080")`). ÉCART DATÉ (23/09/2026) avec le plan L4,
# qui écrit « side = grand côté » : ses propres checks (`dims("16:9", 720)
# == (1280, 720)`, `dims("9:16", 2160) == (2160, 3840)`, `dims("4:5", 1080)
# == (1080, 1350)`) imposent le PETIT côté — c'est la classe usuelle 720p /
# 1080p / 2160p, c'est elle qui est implémentée. `hevc` porte deux
# candidats (`vcodec_alt`) : le premier dont l'encodeur RÉPOND à un
# encodage réel (`_encoder_ok`) l'emporte — mesuré le 23/09/2026 :
# hevc_amf et hevc_qsv sont LISTÉS par `ffmpeg -encoders` mais ÉCHOUENT,
# la liste ne prouve rien. Les presets audio seuls décodent tout de même
# la vidéo (le graphe est celui du rendu, la vidéo part dans `nullsink`) :
# `side` 480 borne ce travail inutile — reste daté, pas un graphe audio
# séparé. GIF : 12 i/s, côté 480, palette par palettegen/paletteuse, pas
# d'audio (`-an`, le mix part dans `anullsink`).
_DELIVER_FPS = (24, 25, 30, 60)
_DELIVER = {
    "master_1080": {
        "label": "Master 1080 (H.264)", "side": 1080, "fps": 30,
        "vcodec": ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                   "-preset", "medium", "-crf", "20"],
        "pix_fmt": "yuv420p", "acodec": ["-c:a", "aac", "-b:a", "192k"],
        "ext": ".mp4", "flags": ["-movflags", "+faststart"]},
    "web_4k": {
        "label": "Web 4K (H.264)", "side": 2160, "fps": 30,
        "vcodec": ["-c:v", "libx264", "-profile:v", "high", "-level", "5.1",
                   "-preset", "medium", "-crf", "18"],
        "pix_fmt": "yuv420p", "acodec": ["-c:a", "aac", "-b:a", "256k"],
        "ext": ".mp4", "flags": ["-movflags", "+faststart"]},
    "social_720": {
        "label": "Réseaux 720 (H.264 léger)", "side": 720, "fps": 30,
        "vcodec": ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                   "-preset", "medium", "-crf", "23"],
        "pix_fmt": "yuv420p", "acodec": ["-c:a", "aac", "-b:a", "128k"],
        "ext": ".mp4", "flags": ["-movflags", "+faststart"]},
    "prores422": {
        "label": "ProRes 422 (montage)", "side": 1080, "fps": 30,
        "vcodec": ["-c:v", "prores_ks", "-profile:v", "2"],
        "pix_fmt": "yuv422p10le", "acodec": ["-c:a", "pcm_s16le"],
        "ext": ".mov", "flags": []},
    "hevc": {
        "label": "HEVC 1080 (H.265)", "side": 1080, "fps": 30,
        "vcodec_alt": [["-c:v", "hevc_nvenc", "-preset", "p5", "-cq", "24"],
                       ["-c:v", "libx265", "-preset", "medium", "-crf", "24"]],
        "pix_fmt": "yuv420p", "acodec": ["-c:a", "aac", "-b:a", "192k"],
        "ext": ".mp4", "flags": ["-tag:v", "hvc1", "-movflags", "+faststart"]},
    "webm_vp9": {
        "label": "WebM VP9", "side": 1080, "fps": 30,
        "vcodec": ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0",
                   "-row-mt", "1"],
        "pix_fmt": "yuv420p", "acodec": ["-c:a", "libopus", "-b:a", "128k"],
        "ext": ".webm", "flags": []},
    "audio_aac": {
        "label": "Audio seul AAC (.m4a)", "side": 480, "fps": 30,
        "audio_only": True, "acodec": ["-c:a", "aac", "-b:a", "192k"],
        "ext": ".m4a", "flags": ["-movflags", "+faststart"]},
    "audio_mp3": {
        "label": "Audio seul MP3", "side": 480, "fps": 30,
        "audio_only": True, "acodec": ["-c:a", "libmp3lame", "-q:a", "2"],
        "ext": ".mp3", "flags": []},
    "audio_wav": {
        "label": "Audio seul WAV", "side": 480, "fps": 30,
        "audio_only": True, "acodec": ["-c:a", "pcm_s16le"],
        "ext": ".wav", "flags": []},
    "gif_480": {
        "label": "GIF animé 480", "side": 480, "fps": 12,
        "gif": True, "ext": ".gif", "flags": []},
}
_DELIVER_DEFAUT = "master_1080"
_ENCODER_CACHE: dict[str, bool] = {}

# --- D-24 (23/09/2026) : LOUDNESS NORMÉE EN DEUX PASSES ---------------------
# Cibles : −14 LUFS (YouTube / TikTok), −16 (podcast), −23 (EBU R128). La
# passe 1 = le graphe audio de `/measure` (chemin `audio_only=True` de
# `_build_montage_command`, mêmes entrées, même mix) dont le maillon ebur128
# est remplacé par `loudnorm=…:print_format=json` ; la passe 2 = le maillon
# `[outa]loudnorm=…:measured_*:linear=true,aresample=48000[outn]` mappé à la
# place de `[outa]` dans la commande finale. `linear=true` avec les valeurs
# mesurées = un GAIN CONSTANT (pas de compression dynamique) tant que le vrai
# pic reste sous TP ; sans passe 1, loudnorm travaille en dynamique et
# modèle la voix — c'est pourquoi `loud_measured` est OBLIGATOIRE. L'aperçu et
# le mix vide (anullsrc) n'ont pas de loudnorm.
_LOUD_TARGETS = (-14, -16, -23)
_LOUD_KEYS = ("I", "TP", "LRA", "thresh", "offset")
_LOUD_JSON_KEYS = {"input_i": "I", "input_tp": "TP", "input_lra": "LRA",
                   "input_thresh": "thresh", "target_offset": "offset"}
_LOUD_JSON_RE = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.S)


def _lnum(v) -> str:
    """Nombre → chaîne ffmpeg courte (4 décimales max, sans zéros ni notation
    scientifique) : -20.10 → -20.1, -3.0 → -3, 0.0 → 0."""
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _loud_target(loudness) -> int:
    """Cible validée (int de `_LOUD_TARGETS`) ou ValueError. Un booléen et
    une chaîne sont refusés : le payload doit porter un NOMBRE."""
    if isinstance(loudness, bool) or not isinstance(loudness, (int, float)):
        raise ValueError(f"loudness invalide {loudness!r} — "
                         f"{', '.join(map(str, _LOUD_TARGETS))} LUFS")
    t = int(loudness)
    if t != loudness or t not in _LOUD_TARGETS:
        raise ValueError(f"loudness invalide {loudness!r} — "
                         f"{', '.join(map(str, _LOUD_TARGETS))} LUFS")
    return t


def _loudnorm_parse(stderr: str):
    """DERNIER bloc JSON de loudnorm dans le stderr ffmpeg → {I, TP, LRA,
    thresh, offset} (floats) ; None sans bloc, bloc illisible ou valeur
    manquante / nan. Pure."""
    blocs = _LOUD_JSON_RE.findall(stderr or "")
    if not blocs:
        return None
    try:
        d = json.loads(blocs[-1])
    except ValueError:
        return None
    out = {}
    for k_json, k in _LOUD_JSON_KEYS.items():
        try:
            v = float(d.get(k_json))
        except (TypeError, ValueError):
            return None
        if v != v:                                   # nan
            return None
        out[k] = v
    return out


def _loudnorm_chain(target: int, measured: dict) -> str:
    """Maillon de passe 2 (sans étiquettes) : loudnorm linéaire avec les
    valeurs mesurées, puis rééchantillonnage 48 kHz (loudnorm sort en 192 kHz
    et l'encodeur AAC/MP3/Opus attend une cadence usuelle)."""
    if not isinstance(measured, dict) or any(k not in measured for k in _LOUD_KEYS):
        raise ValueError("loudness : la passe 1 (mesure) est obligatoire avant "
                         "le rendu normalisé — `loud_measured` absent ou incomplet")
    m = {k: _lnum(measured[k]) for k in _LOUD_KEYS}
    return (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['I']}:"
            f"measured_TP={m['TP']}:measured_LRA={m['LRA']}:"
            f"measured_thresh={m['thresh']}:offset={m['offset']}:"
            f"linear=true:print_format=summary,aresample=48000")


# --- D-38 (23/09/2026) : RENDU PARTIEL DE LA PLAGE I/O -----------------------
def _range_args(range_out, total: float):
    """`(a, b)` en secondes → (`["-ss", a]`, durée de sortie) validés contre
    `total` : a ≥ 0, b > a, a < total, fin bornée au total. None → ([],
    total) — commande historique. La coupe est une coupe de SORTIE : décodé
    jusqu'à la fin de la plage, rien n'est encodé avant `a` (mesuré le
    23/09/2026 : plage [1,2] sur 30 s = 0,51 s contre 5,38 s pour le tout) ;
    sous-titres / titres / marqueurs gardent l'horloge globale.
    Invalide → ValueError « plage »."""
    if range_out is None:
        return [], total
    try:
        a, b = range_out
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        raise ValueError(f"plage invalide {range_out!r} — attendu (début, fin) "
                         f"en secondes")
    if a != a or b != b or a < 0 or b <= a or a >= float(total):
        raise ValueError(f"plage invalide [{_lnum(a) if a == a else a}, "
                         f"{_lnum(b) if b == b else b}] sur {_lnum(total)} s — "
                         f"début ≥ 0, fin > début, début < durée")
    return ["-ss", str(a)], round(min(b, float(total)) - a, 3)


def _deliver_dims(ratio: str, side: int) -> tuple[int, int]:
    """`_CANVAS[ratio]` mis à l'échelle pour que son PETIT côté vaille
    `side`, arrondi pair (yuv420p exige des dimensions paires). Ratio
    inconnu → 9:16, comme `/render`."""
    w0, h0 = _CANVAS.get(ratio, _CANVAS["9:16"])
    k = float(side) / float(min(w0, h0))
    w, h = int(round(w0 * k)), int(round(h0 * k))
    return w - w % 2, h - h % 2


def _encoder_ok(name: str) -> bool:
    """L'encodeur RÉPOND-il ? Sonde par un encodage réel d'UNE image
    (`-f lavfi color … -frames:v 1 -f null -`), mise en cache par
    processus. Un nom inconnu, un binaire absent ou un délai dépassé
    valent False — jamais une exception."""
    name = str(name or "")
    if name in _ENCODER_CACHE:
        return _ENCODER_CACHE[name]
    ok = False
    if re.fullmatch(r"[a-z0-9_]+", name):
        try:
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                 "color=c=black:s=64x64:d=0.1", "-frames:v", "1",
                 "-c:v", name, "-f", "null", "-"],
                capture_output=True, timeout=20)
            ok = r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
    _ENCODER_CACHE[name] = ok
    return ok


def _deliver_resolve(pid, fps=None, maison=None) -> dict:
    """`preset_id` → dict EFFECTIF (copie), pure. Inconnu / None → master ;
    un preset maison (`{id, label, base, fps?, crf?}` dans `maison`) = son
    `base` + surcharges ; `fps` du payload (24|25|30|60) l'emporte sur le
    preset, sauf pour le GIF (cadence fixée par le preset). `crf` maison
    remplace la valeur qui suit `-crf` (ou `-cq`) de chaque candidat."""
    pid = str(pid) if pid is not None else ""
    base_id, fps_m, crf_m, label_m = pid, None, None, None
    for m in (maison or []):
        if isinstance(m, dict) and m.get("id") == pid and m.get("base") in _DELIVER:
            base_id = m["base"]
            fps_m, crf_m = m.get("fps"), m.get("crf")
            label_m = str(m.get("label") or "").strip() or None
            break
    src = _DELIVER.get(base_id) or _DELIVER[_DELIVER_DEFAUT]
    spec = json.loads(json.dumps(src))
    spec["id"] = base_id if base_id in _DELIVER else _DELIVER_DEFAUT
    if label_m:
        spec["label"] = label_m            # le titre du job portera CE libellé
    if not spec.get("gif"):
        for cand in (fps, fps_m):
            try:
                if cand is not None and int(cand) in _DELIVER_FPS:
                    spec["fps"] = int(cand)
                    break
            except (TypeError, ValueError):
                continue
    if crf_m is not None:
        try:
            crf_v = str(max(0, min(51, int(crf_m))))
        except (TypeError, ValueError):
            crf_v = None
        if crf_v is not None:
            for args in [spec.get("vcodec")] + list(spec.get("vcodec_alt") or []):
                if not args:
                    continue
                for flag in ("-crf", "-cq"):
                    if flag in args:
                        args[args.index(flag) + 1] = crf_v
    return spec


def _deliver_tail(spec: dict | None, preview: bool, fps, total, inputs, parts,
                  amap, out, cur, subs_filter=None, ss=()):
    """La QUEUE de `_build_montage_command` : dernier maillon vidéo + options
    d'encodage + fichier. `spec` None ou aperçu → queue historique (x264
    veryfast/crf 30 en aperçu, master 1080 sinon), octet pour octet.
    D-38 : `ss` (`["-ss", a]` ou vide) est posé JUSTE AVANT `-t` — `total`
    est alors la durée de SORTIE (`_range_args`), pas celle du montage."""
    if preview or not spec:
        gravure = f"{subs_filter}," if subs_filter else ""
        parts.append(f"[{cur}]{gravure}format=yuv420p[outv]")
        preset, crf, abr = (("veryfast", "30", "128k") if preview
                            else ("medium", "20", "192k"))
        return ["ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(parts),
                "-map", "[outv]", "-map", amap,
                *ss, "-t", str(round(total, 3)),
                "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
                "-r", str(fps), "-c:a", "aac", "-b:a", abr,
                "-movflags", "+faststart", str(out)]
    out = Path(out)
    ext = str(spec.get("ext") or ".mp4")
    if out.suffix.lower() != ext:
        out = out.with_suffix(ext)
    gravure = f"{subs_filter}," if subs_filter else ""
    if spec.get("audio_only"):
        # La vidéo composée est JETÉE (nullsink) : un graphe dont une
        # sortie étiquetée n'est pas mappée fait échouer ffmpeg.
        parts.append(f"[{cur}]{gravure}nullsink")
        return ["ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(parts),
                "-vn", "-map", amap, *ss, "-t", str(round(total, 3)),
                *spec.get("acodec", []), *spec.get("flags", []), str(out)]
    if spec.get("gif"):
        gfps = int(spec.get("fps") or 12)
        parts.append(f"[{cur}]{gravure}fps={gfps},split[g0][g1];"
                     f"[g0]palettegen[pal];[g1][pal]paletteuse[outv]")
        if amap.startswith("["):
            parts.append(f"{amap}anullsink")
        return ["ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(parts),
                "-map", "[outv]", "-an", *ss, "-t", str(round(total, 3)),
                "-r", str(gfps), *spec.get("flags", []), str(out)]
    pix = str(spec.get("pix_fmt") or "yuv420p")
    parts.append(f"[{cur}]{gravure}format={pix}[outv]")
    vcodec = spec.get("vcodec")
    if not vcodec:
        alts = list(spec.get("vcodec_alt") or [])
        vcodec = alts[-1] if alts else _DELIVER[_DELIVER_DEFAUT]["vcodec"]
        for cand in alts:
            if _encoder_ok(cand[1]):
                vcodec = cand
                break
    return ["ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(parts),
            "-map", "[outv]", "-map", amap,
            *ss, "-t", str(round(total, 3)),
            *vcodec, "-pix_fmt", pix, "-r", str(fps),
            *spec.get("acodec", []), *spec.get("flags", []), str(out)]

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

# E-1 (22/09/2026) — UN MONTAGE NEUF EST VIDE, ET LE RESTE. Drapeau opt-in
# `vide` : posé par POST /projects {vide:true}, gardé par _save_record quand
# le client le renvoie, lu par GET /project pour NE PAS reconstruire depuis
# la Bibliothèque, et par open pour ne pas rendre 409. Sans lui, tout est
# octet pour octet l'historique (les deux 400 épinglés restent).
# Les sept pistes d'un montage neuf sans `tracks` : miroir de
# DZM_DEFAULT_TRACKS (frontend/patches/montage.js:166) réduit à ce que
# `_tracks_meta` lit, tenu par un banc croisé (tâche 6).
_CLIENT_DEFAULT_TRACKS = [{"id": "t1", "kind": "title"},
                          {"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                          {"id": "a1", "kind": "audio", "bus": "dialogue"},
                          {"id": "a2", "kind": "audio", "bus": "musique", "loop": True},
                          {"id": "a3", "kind": "audio", "bus": "sfx"},
                          {"id": "s1", "kind": "subs"}]


def _tracks_meta(raw) -> dict:
    """{id: {kind, bus, loop, layer}} — la LOI de classement des clips.

    `raw` est la clé `tracks` du payload : une liste de {id, kind, bus?,
    loop?} dans l'ordre d'affichage, du HAUT vers le BAS. Absente ou vide
    ⇒ `_LEGACY_TRACKS`, et tout le reste du service se comporte comme
    avant, argument pour argument.

    `kind` manquant se déduit de l'initiale (a… audio, s… sous-titres,
    sinon vidéo) ; `bus` inconnu retombe sur `sfx` (jamais de bus inventé
    dans le mixage) ; `loop` n'a de sens que sur une piste audio.

    Genres CONNUS du rendu : `video` (V1 et overlays), `audio` (les trois
    bus), `subs` (S1, gravée en dernier) et, depuis D-21 (21/09/2026),
    `title` — une piste de cartons, dont les clips n'ont PAS de `src` et
    sont gravés en ASS avant S1 (cf. `_titles_ass`). Une piste `title` ne
    gagne ni `layer` (elle n'est pas composée par overlay) ni bus de mixage.
    Il n'y a toujours AUCUNE liste blanche de genres : un `kind` inconnu
    reste déclarable, et ses clips restent simplement inertes au rendu — ce
    comportement est mesuré, et D-21 ne le change pas.
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

# P7 — le `provider` des travaux de PRÉCALCUL (aperçu 480p pour le balayage).
# Ce n'est pas un rendu : c'est un CACHE, et il ne doit jamais réapparaître
# comme un plan ni comme une « version plus récente » d'un plan. Deux
# verrous, chacun tenu par sa propre ligne de banc :
#   1. le JobRecord de `POST /proxy` ne porte AUCUN chemin d'artefact
#      (`final_video_path` et `video_path` restent NULS) — donc il est
#      écarté par TOUT FILTRE qui exige un artefact, à commencer par celui du
#      sélecteur d'assets du bundle : `status==="done" && (video_path ||
#      final_video_path)` (P9). C'est le verrou principal, et il ne coûte
#      rien : le chemin du proxy se déduit de la source (`montage_media`),
#      l'écran n'a donc jamais besoin de le lire sur le job.
#      CE QUE CE VERROU NE FAIT PAS, et le commentaire l'a affirmé à tort
#      jusqu'au 05/09/2026 : il ne rend pas le job invisible des FENÊTRES.
#      Un filtre écarte une ligne APRÈS l'avoir reçue — la ligne a donc
#      occupé sa place dans la fenêtre. MESURÉ : `GET /api/jobs` servait les
#      50 jobs les plus récents SANS filtre de provider, et le sélecteur
#      d'assets du Montage lit ces 50 lignes, filtre, puis coupe à 12 :
#      cinquante proxys et la liste « Rendus vidéo » est VIDE, base pleine de
#      rendus. `GET /api/cost/usage` faisait pire — il sommait tous les jobs
#      `done` sans filtre, et `_job_to_cost` retombait sur sa branche
#      « campaign » par défaut : 0,403 USD par proxy (mesuré aux tarifs par
#      défaut), imputés à `fal`, pour un transcodage ffmpeg local et gratuit.
#      LES DEUX FENÊTRES SONT DONC FILTRÉES À LA SOURCE, chacune dans son
#      `where` et avant son `limit` — `Pipeline.list_jobs` et
#      `routes.cost_usage`, toutes deux par `coalesce(provider, '')`, jamais
#      par un `!=` nu. C'est un TROISIÈME verrou, de budget, pas une copie
#      des deux autres, et il a ses trois lignes de banc
#      (`test_montage_media.py`, N-P18 / N-P19 / N-P20).
#   2. les DEUX requêtes qui construisent une timeline (`montage_project`) ou
#      proposent un remplacement (`montage_newer`) écartent ce `provider`
#      NOMMÉMENT. C'est une garde de RÉGRESSION contre le verrou 1 : le jour
#      où quelqu'un « répare » le job en lui rendant son fichier, la timeline
#      ne se remplira pas de proxys 480p pour autant.
# La garde 2 est écrite dans le `where` et NON répétée en Python, à la
# différence de la liste blanche d'extensions. Ce n'est pas un oubli : le
# `where` et la boucle divergent sur le CHEMIN (l'un voit la chaîne stockée,
# l'autre l'extension analysée — cf. le fichier nommé « .mp4 » de P8-bis),
# jamais sur `provider`, qui est une colonne comparée entière des deux côtés.
# Un second test Python serait ici du code que rien ne peut faire rougir
# seul.
_PROXY_PROVIDER = "montage_proxy"
# D-16 : l'analyse vidstab (`POST /stab`) est le second précalcul PAR SOURCE
# suivi par un job sans artefact — même statut que le proxy partout où l'on
# filtre par `provider` : `/newer` (ici), `pipeline.list_jobs` (GET /api/jobs)
# et `cost_usage` (routes.py) ; tenu par la section [6] de test_montage_l3.
_STAB_PROVIDER = "montage_stab"


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
    numérique, NaN) : ignorée avec warning, le champ retombe à son défaut.

    D-19 (24/09/2026) : `radius` = rayon des coins en px (entier 0..200,
    `int(round())`) et `shadow` = ombre portée (0|1 : numérique ≥ 0,5 ou
    True → 1). Posé seul (> 0), l'un ou l'autre rend `tf` non-None avec les
    défauts x/y/scale/rotate — la chaîne AVEC transformation est nécessaire
    pour porter `geq` et le split d'ombre (écart daté : un overlay « cover »
    qui ne reçoit qu'un rayon passe en chaîne transformée plein cadre)."""
    spec = {"x": (-0.5, 1.5, 0.5), "y": (-0.5, 1.5, 0.5),
            "scale": (0.05, 3.0, 1.0), "rotate": (-180.0, 180.0, 0.0),
            "radius": (0, 200, 0), "shadow": (0, 1, 0)}
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
        if key == "shadow":
            out[key] = 1 if f >= 0.5 else 0
        elif key == "radius":
            out[key] = int(max(lo, min(hi, int(round(f)))))
        else:
            out[key] = max(lo, min(hi, f))
        # radius/shadow à 0 ne font pas naître une transformation
        seen = seen or key not in ("radius", "shadow") or out[key] > 0
    return out if seen else None


# R4b : keyframes de position par overlay V2 — champ optionnel
# ``motion_points`` : [{t, x, y, rotate?}] (max 8). t en secondes LOCALES au
# clip (0..durée, clampé), x/y/rotate : mêmes clamps que _ov_transform. Au
# rendu, les expressions x/y du filtre overlay deviennent des interpolations
# LINÉAIRES par morceaux du temps GLOBAL du montage (le filtre overlay est
# posé sur le flux composité : son t est celui de enable='between(t,st,en)' —
# chaque point local devient start + t). La rotation s'anime sur l'horloge
# LOCALE du flux overlay (le filtre rotate précède le setpts de décalage).
# D-14 (22/09/2026) : l'ÉCHELLE et l'OPACITÉ s'animent aussi, sur la même
# horloge LOCALE — points `scale` → pad rgba + zoompan (z='…it…'), points
# `opacity` → sendcmd sur colorchannelmixer@mpo<j> aa. MESURÉ sur ffmpeg
# 8.1.1 (scratchpad d14/mesure.py) : le candidat `sendcmd` sur `scale@mps w`
# rend 0 et scale CHANGE la taille de ses images (showinfo 100x50 → 300x150)
# mais `overlay` garde la taille INITIALE de sa 2e entrée (100 px mesurés à
# t=0,2 ET t=2,5) — donc zoompan, qui ne fait QUE grossir (z clampé 1..10 par
# le filtre) : l'overlay est posé à sa largeur MINIMALE puis grossi.
_MP_MAX_POINTS = 8


def _motion_points(c: dict) -> list | None:
    """Champ optionnel ``motion_points`` d'un overlay V2 : [{t, x, y,
    rotate?, scale?, opacity?}] → liste TRIÉE de 6-uplets
    (t, x, y, rotate|None, scale|None, opacity|None), ou None.

    t clampé 0..durée du clip (end−start), x/y clampés −0.5..1.5, rotate
    −180..180, scale 0.05..3 (mêmes bornes que _ov_transform), opacity 0..1
    — un champ optionnel absent ou invalide (non numérique, NaN) reste None
    avec warning : le point ne participe pas à cette animation-là. Entrées
    invalides (non-dict, t/x/y non numériques, NaN) ignorées avec warning ;
    au-delà de 8 points triés le surplus est ignoré (warning) ; doublons de
    t (< 5 ms) fusionnés, le dernier gagne (une pente y diviserait par ~0).
    Champ absent, vide ou entièrement invalide → None : la chaîne émise
    reste STRICTEMENT l'historique (non-régression testée)."""
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
        opt = []
        for key, lo, hi in (("rotate", -180.0, 180.0), ("scale", 0.05, 3.0),
                            ("opacity", 0.0, 1.0)):
            v = p.get(key) if isinstance(p, dict) else None
            if v is not None:
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    v = float("nan")
                if v != v:
                    logger.warning(f"montage: {key} de point invalide, "
                                   f"ignoré — {lbl}")
                    v = None
                else:
                    v = max(lo, min(hi, v))
            opt.append(v)
        t = max(0.0, round(t, 3))
        if dur > 0:
            t = min(t, round(dur, 3))
        pts.append((t, max(-0.5, min(1.5, xx)), max(-0.5, min(1.5, yy)), *opt))
    pts.sort(key=lambda q: q[0])
    if len(pts) > _MP_MAX_POINTS:
        logger.warning(f"montage: {len(pts)} points de position (max "
                       f"{_MP_MAX_POINTS}), surplus ignoré — {lbl}")
        pts = pts[:_MP_MAX_POINTS]
    out: list = []
    for q in pts:
        if out and q[0] - out[-1][0] < 0.005:
            out[-1] = (out[-1][0], *q[1:])
            continue
        out.append(q)
    return out or None


def _mp_lerp_expr(pts: list, var: str = "t") -> str:
    """Interpolation linéaire par morceaux pour des paires (t, v) TRIÉES —
    même gabarit d'expression que :func:`_vp_expr` (constante avant le
    premier point / après le dernier), sans conversion finale : sert aux
    expressions x/y (pixels, temps global) et a (radians, temps local) des
    overlays animés, et au z de zoompan (D-14, ``var="it"`` : zoompan ne
    connaît pas `t`, son horloge est `it`). Toujours posée entre quotes
    simples dans le filtergraph (les virgules de if(…) y sont sans
    ambiguïté)."""
    n = sfx_service.fnum
    if len(pts) == 1:
        return n(pts[0][1])
    expr = n(pts[-1][1])
    for k in range(len(pts) - 1, 0, -1):
        t0, v0 = pts[k - 1]
        t1, v1 = pts[k]
        seg = f"{n(v0)}+({n(v1 - v0)})*({var}-{n(t0)})/{n(t1 - t0)}"
        expr = f"if(lt({var},{n(t1)}),{seg},{expr})"
    return f"if(lt({var},{n(pts[0][0])}),{n(pts[0][1])},{expr})"


def _mp_cmds(pairs: list, target: str, opt: str, fmt) -> str:
    """D-14 : commandes ``sendcmd`` pour des paires (t, v) TRIÉES — UNE
    commande ``[expr]`` PAR SEGMENT « t0-t1 [expr] target opt v0+(dv)*TI »
    (TI ∈ 0..1 dans l'intervalle, évaluée par image), puis une commande plate
    finale qui cloue la dernière valeur ; jointes par « \\; » (le « ; » nu
    est aussi le séparateur du filtergraph : précédent
    effects_engine._opacity_cmds). Écart au plan : l'échantillonnage à
    _RAMP_STEP (25 commandes/s) faisait 28 824 caractères pour 30 s de clés
    — au-delà du plafond CreateProcess (32 767) ; ``[expr]`` MESURÉ le
    22/09/2026 sur ffmpeg 8.1.1 (rc 0, alpha 0,90/0,58/0,20/0,54/0,76 à
    t=0,2/1,0/1,9/2,5/2,9 pour 1→0,2→0,8) : ≤ 7 segments, ~300 caractères.
    Piège mesuré : AUCUNE virgule dans l'expression (lerp(a,b,TI) casse le
    parseur même entre quotes) — d'où v0+(dv)*TI."""
    n = sfx_service.fnum
    segs = [f"{n(t0)}-{n(t1)} [expr] {target} {opt} {n(v0)}+({n(v1 - v0)})*TI"
            for (t0, v0), (t1, v1) in zip(pairs, pairs[1:])]
    return "\\;".join(segs + [f"{n(pairs[-1][0])} {target} {opt} {fmt(pairs[-1][1])}"])


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


# D-13 (22/09/2026) — DYNAMIC ZOOM. Champ optionnel `dz` d'un clip V1 :
# {x0, y0, w0, x1, y1, w1, ease?} en FRACTIONS du cadre (le segment est
# déjà recadré au ratio du canvas par scale/crop, donc la hauteur de la
# fenêtre est la MÊME fraction que sa largeur). w ∈ [0.1, 1], x et y ∈
# [0, 1−w]. Plein cadre aux deux bouts = aucun zoom (None). MESURÉ le
# 22/09 : `crop=w='…t…'` ÉCHOUE à la configuration (−22) et `scale:eval=
# frame` fige la taille — seul `zoompan` tient, et il doit venir APRÈS
# `fps=` (avant, il dupliquerait chaque image d'un flux retimé).
_DZ_EASES = ("doux", "lin")


def _dz_spec(c: dict) -> dict | None:
    raw = c.get("dz")
    if not isinstance(raw, dict):
        return None
    lbl = c.get("label") or c.get("tr") or "v1"
    out: dict = {}
    for k in ("x0", "y0", "w0", "x1", "y1", "w1"):
        try:
            f = float(raw.get(k))
        except (TypeError, ValueError):
            f = float("nan")
        if f != f:  # NaN / absent — jamais dans un filtergraph
            logger.warning(f"montage: dz.{k} invalide ({raw.get(k)!r}), zoom ignoré — {lbl}")
            return None
        out[k] = f
    for i in ("0", "1"):
        out["w" + i] = max(0.1, min(1.0, out["w" + i]))
        out["x" + i] = max(0.0, min(1.0 - out["w" + i], out["x" + i]))
        out["y" + i] = max(0.0, min(1.0 - out["w" + i], out["y" + i]))
    if all(abs(out[k]) < 1e-6 for k in ("x0", "y0", "x1", "y1")) and out["w0"] >= 1.0 and out["w1"] >= 1.0:
        return None
    out["ease"] = raw.get("ease") if raw.get("ease") in _DZ_EASES else "doux"
    return out


def _dz_filter(dz: dict, w: int, h: int, fps: int, dur: float) -> str:
    """Le zoompan d'un segment : u = clip(it/dur, 0, 1) (smoothstep si `doux`),
    z = 1/lerp(w0,w1), x/y = iw·lerp(x0,x1) / ih·lerp(y0,y1). d=1 : une image
    de sortie par image d'entrée, durée et compte d'images préservés (mesure)."""
    n = sfx_service.fnum
    d = max(0.04, float(dur))
    u = f"clip(it/{n(d)},0,1)"
    if dz.get("ease") == "doux":
        u = f"({u})*({u})*(3-2*({u}))"

    def lerp(a: float, b: float) -> str:
        return f"({n(a)}+({n(b - a)})*({u}))"

    return (f"zoompan=z='1/{lerp(dz['w0'], dz['w1'])}'"
            f":x='iw*{lerp(dz['x0'], dz['x1'])}'"
            f":y='ih*{lerp(dz['y0'], dz['y1'])}'"
            f":d=1:s={w}x{h}:fps={fps}")


# D-40 (L7-B, 24/09/2026) — RECADRAGE. Champ optionnel `reframe` d'un clip
# V1 : {mode: "centre"|"suivi"|"manuel", x?, points?}. Le cover historique
# centre la fenêtre (`crop={w}:{h}`) ; `manuel` la pose à `x` (fraction de la
# largeur de la source, centre de la fenêtre), `suivi` la fait glisser le long
# de `points` [{t, x}]. FORMAT DU CHAMP (revue finale du lot, 24/09/2026) : t
# en secondes ABSOLUES de la source (le client pose srcIn_analyse + t_relatif
# à la réception de /reframe). Pourquoi : la lame, la découpe aux plans, la
# coupe ripple et le rognage de tête AVANCENT srcIn et COPIENT le champ — en
# temps relatif, le morceau droit d'un plan [0,10] suivi 0,2→0,8 coupé à 5 s
# cadrait 0,2→0,5 au lieu de 0,5→0,8. En absolu, le champ reste attaché à la
# source et chaque morceau lit sa fenêtre. `_reframe_of` rend, lui, des t
# RELATIFS au srcIn COURANT (le temps LOCAL du flux au point du crop, qui
# précède setpts=PTS/speed : MESURÉ, voir reframe.py), bornés à
# (end − start) × vitesse. Aucun marqueur de format : les projets de la
# branche n'ont jamais été livrés, et un champ relatif posé à srcIn 0 se lit
# pareil. `centre` = None (chaîne
# historique octet pour octet). MESURÉ le 24/09 : un `x` animé de crop passe
# dans ffmpeg 8.1.1 (seuls w/h sont figés à la configuration, −22 de D-13).
_RF_MODES = ("centre", "suivi", "manuel")
_RF_MAX_POINTS = 240
_RF_TOL = 0.004             # simplification RDP du rendu (fraction de largeur)


def _rf_num(v) -> float | None:
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _rf_lerp_val(pts: list, t: float) -> float:
    """x(t) sur des paires (t, x) TRIÉES : constante avant le premier point et
    après le dernier, linéaire entre — la règle de _mp_lerp_expr et de
    dzmReframeAt côté client (mêmes opérations, dans le même ordre)."""
    if t < pts[0][0]:
        return pts[0][1]
    for i in range(1, len(pts)):
        if t < pts[i][0]:
            t0, x0 = pts[i - 1]
            t1, x1 = pts[i]
            return x0 + (x1 - x0) * (t - t0) / (t1 - t0)
    return pts[-1][1]


def _reframe_of(c: dict) -> dict | None:
    """clips V1 [].reframe → None (centré, historique) | {"mode": "manuel",
    "x"} | {"mode": "suivi", "points": [(t, x)…]} — les points du CHAMP sont
    en secondes ABSOLUES de source ; ceux RENDUS sont relatifs au srcIn
    courant (a = srcIn borné à 0) : fenêtre [a, a + (end − start) × vitesse]
    (sans durée lisible, bornée à gauche seulement) ; x borné à [0, 1] ; les
    points hors fenêtre tombent, et un point de BORD interpolé (constante
    au-delà du dernier) est posé en a ou en a + durée s'il en est tombé de ce
    côté ; puis t − a arrondi au millième, dédoublonnés à 5 ms (le dernier
    gagne), au plus 240 (sous-échantillonnés régulièrement). Même règle que
    dzmReframeOf (client). Champ, mode ou x illisible, ou aucun point
    valable : warning et None — jamais dans un filtergraph. Un point
    illisible parmi d'autres est ignoré (warning)."""
    raw = c.get("reframe")
    if raw is None:
        return None
    lbl = c.get("label") or c.get("tr") or "v1"
    if not isinstance(raw, dict) or raw.get("mode") not in _RF_MODES:
        logger.warning(f"montage: reframe invalide ({str(raw)[:80]!r}), "
                       f"cadrage centré — {lbl}")
        return None
    mode = raw["mode"]
    if mode == "centre":
        return None
    if mode == "manuel":
        x = _rf_num(raw.get("x"))
        if x is None:
            logger.warning(f"montage: reframe manuel sans x lisible "
                           f"({raw.get('x')!r}), cadrage centré — {lbl}")
            return None
        return {"mode": "manuel", "x": max(0.0, min(1.0, x))}
    pts_in = raw.get("points")
    if not isinstance(pts_in, list):
        logger.warning(f"montage: reframe suivi sans points, cadrage centré — {lbl}")
        return None
    spd = _v1_speed(c) or 1.0
    s0, s1 = _rf_num(c.get("start")), _rf_num(c.get("end"))
    dur = (s1 - s0) * spd if s0 is not None and s1 is not None else 0.0
    a = _rf_num(c.get("srcIn"))
    a = max(0.0, a) if a is not None else 0.0
    b_ = a + dur if dur > 0 else None
    pts, bad = [], 0
    for q in pts_in:
        if isinstance(q, dict):
            t, x = _rf_num(q.get("t")), _rf_num(q.get("x"))
        elif isinstance(q, (list, tuple)) and len(q) == 2:
            t, x = _rf_num(q[0]), _rf_num(q[1])
        else:
            t = x = None
        if t is None or x is None:
            bad += 1
            continue
        pts.append((t, max(0.0, min(1.0, x))))
    if bad:
        logger.warning(f"montage: reframe — {bad} point(s) illisible(s) "
                       f"ignoré(s) — {lbl}")
    pts.sort(key=lambda q: q[0])
    win: list = []
    if pts:
        win = [q for q in pts if q[0] >= a and (b_ is None or q[0] <= b_)]
        if pts[0][0] < a and not (win and win[0][0] == a):
            win.insert(0, (a, _rf_lerp_val(pts, a)))
        if b_ is not None and pts[-1][0] > b_ and not (win and win[-1][0] == b_):
            win.append((b_, _rf_lerp_val(pts, b_)))
    out: list = []
    for q in [(round(t - a, 3), x) for t, x in win]:
        if out and q[0] - out[-1][0] < 0.005:
            out[-1] = q
            continue
        out.append(q)
    if not out:
        logger.warning(f"montage: reframe suivi sans point valable, cadrage "
                       f"centré — {lbl}")
        return None
    if len(out) > _RF_MAX_POINTS:
        logger.warning(f"montage: reframe — {len(out)} points (max "
                       f"{_RF_MAX_POINTS}), sous-échantillonnés — {lbl}")
        n = len(out)
        out = [out[round(k * (n - 1) / (_RF_MAX_POINTS - 1))]
               for k in range(_RF_MAX_POINTS)]
    return {"mode": "suivi", "points": out}


def _rf_lerp_expr(pts: list, var: str = "t") -> str:
    """La MÊME interpolation linéaire par morceaux que :func:`_mp_lerp_expr`
    (constante avant le premier point et après le dernier), mais en ARBRE
    ÉQUILIBRÉ de if(lt(…)) : profondeur ~log2(n) au lieu de n. MESURÉ en revue
    le 24/09/2026 (ffmpeg 8.1.1, crop x) : l'expression en CHAÎNE de
    `_mp_lerp_expr` échoue à la configuration (−22, « Invalid argument ») au-
    delà de 93 points dans `clip(iw*(…)-w/2,0,iw-w)` (96 nue) — l'analyseur
    d'expressions borne sa récursion. `_mp_lerp_expr` reste juste pour ses
    usages (8 et 12 points au plus) ; le recadrage peut en porter 240."""
    n = sfx_service.fnum
    if len(pts) == 1:
        return n(pts[0][1])

    def seg(k: int) -> str:
        (t0, v0), (t1, v1) = pts[k], pts[k + 1]
        return f"{n(v0)}+({n(v1 - v0)})*({var}-{n(t0)})/{n(t1 - t0)}"

    def arbre(a: int, b: int) -> str:          # segments a .. b-1
        if b - a == 1:
            return seg(a)
        m = (a + b) // 2
        return f"if(lt({var},{n(pts[m][0])}),{arbre(a, m)},{arbre(m, b)})"

    return (f"if(lt({var},{n(pts[0][0])}),{n(pts[0][1])},"
            f"if(lt({var},{n(pts[-1][0])}),{arbre(0, len(pts) - 1)},{n(pts[-1][1])}))")


def _reframe_crop(rf: dict | None, w: int, h: int) -> str:
    """Le `crop` de la chaîne cover V1 : `crop={w}:{h}` sans recadrage
    (historique), sinon la fenêtre centrée sur iw·x, bornée au cadre :
    `crop={w}:{h}:x='clip(iw*X-{w/2},0,iw-{w})':y=(ih-{h})/2` — X constant
    (manuel) ou `_rf_lerp_expr` (arbre équilibré) des points simplifiés (RDP, tolérance
    _RF_TOL : 240 points bruts feraient ~13 000 caractères par clip, plafond
    CreateProcess 32 767) en `t` LOCAL du flux (mesuré, voir reframe.py).
    Une source plus haute que le cadre (iw == w) : x reste 0, rien ne bouge."""
    base = f"crop={w}:{h}"
    if not isinstance(rf, dict):
        return base
    n = sfx_service.fnum
    if rf.get("mode") == "manuel":
        xe = n(rf["x"])
    elif rf.get("mode") == "suivi" and rf.get("points"):
        xe = f"({_rf_lerp_expr(_reframe.simplifier(list(rf['points']), _RF_TOL))})"
    else:
        return base
    return f"{base}:x='clip(iw*{xe}-{n(w / 2)},0,iw-{w})':y=(ih-{h})/2"


def _probe_dims(path: Path) -> tuple | None:
    """(largeur, hauteur) AFFICHÉES du premier flux vidéo par ffprobe, ou None.

    Rotation (revue L7-B, mesurée le 24/09/2026 sur ffmpeg/ffprobe 8.1.1,
    sources 64×36 remuxées par `-display_rotation 90|-90|180`) : ffprobe
    rend toujours `width=64,height=36` codés et la matrice d'affichage dans
    `side_data_list[].rotation` (90, -90, -180) ; `tags.rotate` (ancien
    muxeur) est lu aussi. Le rendu AUTOROTATE (showinfo dans un
    -filter_complex : `s:36x64` pour 90, `s:64x36` pour 180) : un quart de
    tour impair PERMUTE donc largeur et hauteur, sinon rien."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries",
             "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
             "-of", "json", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout
        s = (json.loads(out or "{}").get("streams") or [])[0]
        a, b = int(s["width"]), int(s["height"])
        rot = (s.get("tags") or {}).get("rotate")
        for sd in s.get("side_data_list") or []:
            if isinstance(sd, dict) and "rotation" in sd:
                rot = sd["rotation"]
        if rot is not None and round(float(rot) / 90) % 2:
            a, b = b, a
        return a, b
    except (ValueError, IndexError, KeyError, TypeError, AttributeError,
            FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def _reframe_utile(iw: int, ih: int, w: int, h: int) -> bool:
    """Vrai si le cover laisse de la largeur à balayer : la source mise à
    l'échelle par force_original_aspect_ratio=increase est plus LARGE que le
    cadre. Une source plus haute (ou de même ratio) : iw == w après scale,
    x reste 0 — le recadrage n'a aucun effet horizontal."""
    if iw <= 0 or ih <= 0 or w <= 0 or h <= 0:
        return True
    k = max(w / iw, h / ih)
    return iw * k > w + 1


# D-15 (22/09/2026) — RETIME. Champ optionnel `retime` d'un clip V1 :
# "nearest" (historique : fps= duplique ou saute, None) | "blend" (tblend
# moyenne deux images voisines : flou de mouvement au ralenti, traîne à
# l'accéléré) | "flow" (minterpolate à compensation de mouvement, LENT).
# Sans vitesse, aucun sens : ignoré. MESURÉ le 22/09 (revue) : `flow` va
# AVANT `fps=` (minterpolate fabrique ses images à la cadence demandée) ;
# `blend` va APRÈS `fps=` — posé avant, à ×0,5, tblend donne (A+B)/2,(A+B)/2,
# (B+C)/2… (tout flou, aucune intermédiaire) ; après : A,(A+B)/2,B,(B+C)/2…
# = le Frame Blend de Resolve. tblend CONSOMME la première image (sortie à
# partir de pts 1/fps : 49 images sur 50, mesuré) et le trim aval coupait
# le segment d'une image (99 / 3,960 s) → setpts=PTS-STARTPTS juste après
# rebase à 0, le tpad aval clone la dernière (100 / 4,000 s mesurés). scd au
# défaut ffmpeg (fdiff) : scd=none interpolerait à travers une coupe interne.
_RETIME = {"blend": "tblend=all_mode=average,setpts=PTS-STARTPTS",
           "flow": "minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"}


def _v1_retime(c: dict) -> str | None:
    v = c.get("retime")
    return v if isinstance(v, str) and v in _RETIME else None


# D-16 (22/09/2026) — STABILISATION. Champ optionnel `stab` d'un clip V1 :
# {on, smooth 1..100 (défaut 15), crop "keep"|"black", zoom −30..30}. Le
# fichier .trf est résolu PAR SOURCE au rendu (`montage_media.stab_detect`,
# cache chemin+mtime) — jamais envoyé par le client. Dans la chaîne, la
# transformation lit la source ENTIÈRE puis `trim` fait le travail de
# -ss/-t (mesuré : les transformations sont indexées par image d'entrée).
def _v1_stab(c: dict) -> dict | None:
    raw = c.get("stab")
    if not isinstance(raw, dict) or not raw.get("on"):
        return None

    def num(k, lo, hi, dv):
        try:
            f = float(raw.get(k, dv))
        except (TypeError, ValueError):
            f = float("nan")
        return int(round(max(lo, min(hi, f)))) if f == f else int(dv)
    return {"smooth": num("smooth", 1, 100, 15),
            "crop": "black" if raw.get("crop") == "black" else "keep",
            "zoom": num("zoom", -30, 30, 0)}


def _v1_stab_trf(s: dict) -> Path | None:
    """Le `.trf` d'un segment V1 stabilisé, ou None (segment historique).
    `stab` sans `trf`, ou `trf` disparu (cache purgé entre l'analyse et le
    rendu) : on prévient et on rend le plan NON stabilisé plutôt qu'un rendu
    qui échoue — la commande reste alors celle de l'historique."""
    st = s.get("stab")
    if not isinstance(st, dict):
        return None
    trf = st.get("trf")
    if trf and Path(trf).is_file():
        return Path(trf)
    logger.warning(f"montage: stabilisation sans analyse (.trf absent), plan "
                   f"rendu tel quel — {Path(str(s.get('path') or '')).name}")
    return None


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


# D-5 : les SIX couleurs de marqueur, celles de DZM_MARKER_COLORS dans
# frontend/patches/montage.js. Une couleur inconnue retombe sur « or »,
# des DEUX côtés — le client ne peut pas être la seule garde.
_MONTAGE_MARKER_COLORS = ("or", "rouge", "vert", "bleu", "violet", "cyan")
# Et l'ÉCART MINIMAL entre deux marqueurs, celui de DZM_MARKER_EPS dans la
# couche. Deux marqueurs plus proches que cela ne sont pas deux marqueurs :
# le second est injoignable au clavier, et la bascule Maj+M retirerait le
# premier des deux. L'écart est refusé À PARTIR de cette valeur, bornes
# comprises (cf. le commentaire du filtre, plus bas).
_MONTAGE_MARKER_EPS = 0.15


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
    if body.get("vide") is True:    # E-1 (voir le bloc au-dessus de _CLIENT_DEFAULT_TRACKS)
        data["vide"] = True
    # D-11 : la plage d'entrée/sortie {in, out} en secondes. Assainie ICI —
    # deux nombres finis, 0 <= in < out — et pas seulement à l'écran : le
    # payload n'est pas de confiance (un autre client, une version plus
    # ancienne de la couche). Absente ou invalide : la clé n'est PAS
    # stockée, et GET /project ne la resert donc pas — rien ne change pour
    # un montage qui n'a jamais posé de plage.
    rg = body.get("range")
    if isinstance(rg, dict):
        try:
            a, b = float(rg.get("in")), float(rg.get("out"))
            # `math.isfinite` plutot que le seul `a == a` du plan : MESURE du
            # 21/09/2026 — `float("Infinity")` passe `b == b` ET `0 <= a < b`,
            # et un `inf` stocke ressort en `Infinity` dans le JSON du fichier,
            # que json.loads relit mais qu aucun JSON.parse de navigateur
            # n accepte. isfinite couvre NaN et les deux infinis d un coup.
            if math.isfinite(a) and math.isfinite(b) and 0 <= a < b:
                data["range"] = {"in": round(a, 3), "out": round(b, 3)}
        except (TypeError, ValueError):
            pass
    # D-5 : les MARQUEURS de la règle, {t, color, title, note}. Assainis ICI
    # et pas seulement à l'écran, pour la raison qui vaut déjà pour `range` :
    # le payload n'est pas de confiance (un autre client, une version plus
    # ancienne de la couche, un fichier édité à la main). Les entrées
    # illisibles sont JETÉES une à une — pas la liste entière : un seul
    # marqueur abîmé ne doit pas emporter les quarante autres.
    # L'IDENTIFIANT N'EST PAS STOCKÉ : le client le régénère (`markersFrom`,
    # m1..mN). Deux marqueurs d'un vieux fichier pouvaient porter le même, et
    # « retirer » en aurait retiré deux.
    # LISTE VIDE : la clé n'est PAS écrite, exactement comme `range` — un
    # montage dont on vient de retirer le dernier marqueur revient donc sans
    # marqueur, et rien ne change pour un montage qui n'en a jamais eu.
    # I-2 (revue du 21/09/2026) : L'INVARIANT D'ESPACEMENT EST TENU ICI
    # AUSSI. Le client ne peut pas en être la seule garde — une timeline
    # écrite par un autre client, ou un fichier édité à la main, pouvait
    # porter 1,00 et 1,12 : le second était INJOIGNABLE par « marqueur
    # suivant / précédent », qui saute tout ce qui est à moins d'un
    # `DZM_MARKER_EPS` de la tête. Le TRI PRÉCÈDE le filtre (c'est toujours
    # le premier de deux voisins qui reste), et les doublons exacts tombent
    # par la même règle — distance nulle. Le plafond s'applique APRÈS :
    # 200 marqueurs UTILES, pas 200 entrées dont la moitié serait jetée.
    # Même ordre, à la constante près, que `dzmMarkersFrom` de la couche.
    mks = body.get("markers")
    if isinstance(mks, list):
        brut = []
        for m in mks:
            if not isinstance(m, dict):
                continue
            t = m.get("t")
            # `float("")` LÈVE, et c'est voulu : une chaîne vide n'est pas un
            # temps. Le client dit la même chose depuis `dzmMarkerT` — avant
            # lui, `Number("")` valait ZÉRO côté écran et le marqueur
            # disparaissait au rechargement sans un mot.
            if isinstance(t, bool) or t is None:
                continue
            try:
                t = float(t)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(t) or t < 0:
                continue
            col = m.get("color")
            brut.append({
                "t": round(t, 3),
                "color": col if col in _MONTAGE_MARKER_COLORS else "or",
                "title": ("" if m.get("title") is None
                          else str(m.get("title")))[:200],
                "note": ("" if m.get("note") is None
                         else str(m.get("note")))[:1000],
            })
        out_mk = []
        for m in sorted(brut, key=lambda e: e["t"]):
            if len(out_mk) >= 200:
                break
            # R-1 (seconde revue du 21/09/2026) : LA BORNE EST LARGE, PAS
            # STRICTE. `markerNext` saute tout ce qui n'est pas
            # `t > v + EPS` : un couple à EXACTEMENT 0,150 s passait un
            # filtre strict et restait injoignable DANS LES DEUX SENS
            # (mesure : 697 couples au millième entre 0 et 10 s).
            # `markerAdd` traitait déjà « exactement EPS » comme trop
            # proche : les trois bornes disent maintenant la même chose.
            # Le 1e-9 est la même tolérance de flottant que côté client —
            # 1.15 - 1.0 vaut 0.15000000000000013 en double.
            if (out_mk
                    and m["t"] - out_mk[-1]["t"]
                    <= _MONTAGE_MARKER_EPS + 1e-9):
                continue
            out_mk.append(m)
        if out_mk:
            data["markers"] = out_mk
    # Le plafond de VOLUME vit ici, avec la normalisation (revue E-1 du
    # 22/09/2026 : la branche `vide` de POST /projects écrivait 10 Mo).
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > _SAVE_MAX_BYTES:
        raise HTTPException(400, "Sauvegarde refusée — plus de 2 Mo.")
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
    meta = {"id": d.get("id") or fallback_id or None,
            "name": d.get("name"),
            "updated_at": d.get("saved_at"),
            "clips": len(d.get("clips") or []),
            "ratio": d.get("ratio"),
            "duration": d.get("duration")}
    if d.get("vide") is True:                     # E-1 — clé absente sinon
        meta["vide"] = True
    return meta


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

    P7 : les jobs de PRÉCALCUL (`provider="montage_proxy"`, l'aperçu 480p du
    balayage) sont écartés NOMMÉMENT par la requête. Un cache n'est pas un
    plan — cf. `_PROXY_PROVIDER`, et la section [2-sexies] de
    `tests/test_montage_sources.py`.

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
        if saved.get("vide") is True or any(c.get("tr") == "v1" for c in kept):
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
            if isinstance(saved.get("range"), dict):
                out["range"] = saved["range"]         # D-11 (cf. POST /save)
            if isinstance(saved.get("markers"), list):
                out["markers"] = saved["markers"]     # D-5 (cf. POST /save)
            if saved.get("vide") is True:
                out["vide"] = True                    # E-1 (cf. POST /save)
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
            # P7 — les aperçus de balayage ne sont pas des plans. Dans le
            # `where` et pas seulement dans la boucle, pour la raison MESURÉE
            # de P8-bis : ce qui traverse la requête MANGE la fenêtre de 60.
            # Cinquante clips proxifiés suffiraient à rendre `has_assets`
            # faux et à faire retomber l'écran sur sa démo, base pleine de
            # rendus. `coalesce` et non `!=` nu : `NULL != 'x'` vaut NULL en
            # SQL et écarterait les 13 jobs à `provider` NUL de la base
            # réelle (le piège déjà payé dans `montage_newer`).
            .where(func.coalesce(JobRecord.provider, "") != _PROXY_PROVIDER)
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

    4-bis. `notin_(("montage", "montage_proxy"))` — P7. « montage_proxy »
       n'est PAS « montage » : le `!=` d'origine laissait passer les jobs de
       PRÉCALCUL de la lecture fluide, et le cache 480p d'un plan aurait été
       proposé comme la « version plus récente » de ce plan-là. La route qui
       les crée ne leur donne aucun chemin d'artefact (verrou 1, cf.
       `_PROXY_PROVIDER`) ; cette clause est le verrou de RÉGRESSION, et sa
       ligne de banc pose donc la forme régressée
       (`test_montage_remplacer.py`, `newer_n_offre_pas_un_proxy_de_scrub`).

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
            # P7 : « montage_proxy » N'EST PAS « montage ». Le `!=` d'origine
            # le laissait passer — un aperçu 480p de balayage aurait été
            # proposé comme la « version plus récente » du plan dont il est
            # le cache. `notin_` sur le même `coalesce`, pour la raison de la
            # décision 4 ci-dessus : un `provider` NUL ne doit pas tomber.
            .where(func.coalesce(JobRecord.provider, "")
                   .notin_(("montage", _PROXY_PROVIDER, _STAB_PROVIDER)))
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


@router.get("/transitions")
async def montage_transitions():
    """D-20 — les 58 transitions xfade par familles, avec le drapeau `live`
    (jouable en direct dans le lecteur vivant). Le client n'en a pas de copie."""
    return transitions_catalog()


@router.get("/titles")
async def montage_titles():
    """D-21 — les huit gabarits de titre, leur libellé français et ce qui les
    distingue à l'œil (fonte, corps à 1080 p, couleur de charte, couleur de
    boîte, tags d'animation). Le client n'en a aucune copie : même précédent
    que `GET /transitions`, `GET /effects` et `GET /media-rules`.

    `fonts` ET `colors` PARTENT AVEC (22/09/2026) : l'inspecteur de titres
    offre les seize familles embarquées et les cinq couleurs de la charte,
    et `DzSubs.FONTS` — l'autre source que le client aurait pu lire — ne les
    porte PAS (mesuré : `SUBS_FONTS_FB` est une liste de douze polices
    SYSTÈME, « Segoe UI », « Arial », « Impact »… — aucune n'est gravable
    par libass, qui ne voit que le `fontsdir` embarqué). Les deux tables
    sont celles que `title_spec` interroge pour accepter ou remplacer ;
    servir autre chose aurait fait proposer à l'écran des valeurs que le
    rendu remplace en silence."""
    from app.services import titles as TI
    return {"gabarits": [
        {"id": k, "label": TI.LABELS.get(k, k), "font": t["font"],
         "size": t["size"], "color": t["color"], "box": t["box"],
         "anim": t["anim"]}
        for k, t in TI.TEMPLATES.items()],
        "fonts": list(TI.S.FONT_FILES), "colors": list(TI.BRAND)}


def _prev_w(raw, defaut: int = 270) -> int:
    """Largeur d'aperçu BORNÉE 96..640 et PAIRE.

    Le paramètre est reçu en CHAÎNE et non en `int` : FastAPI répondrait 422
    sur `w=abc`, alors qu'un aperçu est un confort — une largeur illisible
    doit retomber sur le défaut, pas refuser l'image. La borne haute n'est
    pas cosmétique : chaque largeur inédite grave un `.ass` et un PNG de
    plus dans le cache, donc une largeur libre serait un cache sans fond.

    `OverflowError` est attrapé au même titre que `ValueError` : `float("inf")`
    et `float("1e400")` valent tous deux l'infini, et `int(inf)` LÈVE — la
    route rendait alors un 500 là où sa promesse est le repli (mesuré le
    21/09/2026, `w=inf`).
    """
    try:
        w = int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        w = defaut
    w = max(96, min(640, w))
    return w - w % 2


@router.get("/title-preview")
async def montage_title_preview(template: str = "", text: str = "", sub: str = "",
                                color: str = "", font: str = "", size: str = "",
                                w: str = "270"):
    """D-21 — l'aperçu PNG d'un titre, gravé par le même ASS que le rendu.

    Cadre VERTICAL 9:16 (hauteur = largeur × 16/9, paire) : l'aperçu montre
    le titre dans le format du montage court, où le placement des gabarits a
    été mesuré. Le PNG est rendu dans un THREAD (ffmpeg dure ~0,3 s) et
    servi avec un `Cache-Control` d'un jour — la clé de cache contient le
    spec entier et `titles.FORMAT_V`, donc un nouveau réglage donne une
    nouvelle URL et jamais une image périmée.

    400 quand il n'y a rien à écrire (texte vide : `title_spec` rend None) —
    la faute est du client. 503 quand ffmpeg n'a rendu aucune image : c'est
    l'outil qui manque, pas la requête qui est fautive.
    """
    from app.services import titles as TI
    ww = _prev_w(w)
    hh = ww * 16 // 9
    hh -= hh % 2
    spec = TI.title_spec({"title": {"template": template, "text": text, "sub": sub,
                                    "color": color, "font": font, "size": size},
                          "start": 0, "end": 3})
    if not spec:
        raise HTTPException(400, "Aperçu de titre : il n'y a rien à écrire — "
                                 "donne un texte.")
    p = await asyncio.to_thread(TI.render_title_png, spec, ww, hh)
    if p is None or not Path(p).is_file():
        raise HTTPException(503, "Aperçu de titre : ffmpeg n'a rendu aucune "
                                 "image — réessaie, ou lance le rendu.")
    return FileResponse(str(p), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/effects")
async def montage_effects():
    """Catalogue du moteur Effects / Mask pour le sélecteur d'effets par clip
    de l'inspecteur (labels FR + paramètres par type)."""
    from app.services import effects_engine
    return {"effects": effects_engine.catalog()}


def media_rules() -> dict:
    """La règle « vidéo » sous forme de FONCTION PURE — l'unique juge, lu par
    la route `GET /media-rules` (le client) ET par `GET /api/jobs?video=1`
    (routes.py, E-2 du 23/09/2026 : le tiroir Médias pagine côté serveur,
    le serveur doit donc juger avec la MÊME règle que le client). Mesuré le
    23/09/2026 : la règle est faite d'extensions seulement (`_VIDEO_EXTS`),
    pas de liste de providers — `video=1` n'en invente pas une. Un espion
    posé sur ce nom (test_montage_eb.py [2]) prouve que les deux routes y
    passent et qu'une extension changée ici traverse jusqu'à la requête."""
    return {"video_exts": list(_VIDEO_EXTS)}


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
    et le dit à l'écran ; il ne devine pas une liste de son côté.

    E-2 (23/09/2026) : le dict vient de `media_rules()`, jamais reconstruit
    ici — sinon deux juges."""
    return media_rules()


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
    if body.get("vide") is True:        # E-1 : un montage NEUF, sans un clip
        tr = body.get("tracks")
        cur = _save_record({"name": body.get("name"), "clips": [], "duration": 30,
                            "vide": True,
                            "tracks": tr if isinstance(tr, list) and tr
                            else _CLIENT_DEFAULT_TRACKS})
    elif isinstance(tl, dict) and isinstance(tl.get("clips"), list):
        cur = _save_record(tl)          # même normalisation (et plafond) que POST /save
    else:
        cur = await asyncio.to_thread(_load_saved)
    if cur is None or (not cur.get("clips") and cur.get("vide") is not True):
        raise HTTPException(400, "Aucune timeline à enregistrer.")
    rec = await _nouveau_projet(cur, body.get("name"), cur.get("name"), courant=True)
    return {"ok": True, **_project_meta(rec)}


async def _nouveau_projet(cur: dict, name, fallback, *, courant: bool) -> dict:
    """Un projet NEUF depuis une timeline normalisée (`_save_record`) : un
    identifiant `m_…`, le nom nettoyé, l'écriture atomique sous `_ecrit`.
    `courant=True` (POST /projects) en fait aussi la timeline courante ;
    `False` (POST /autoclips/create) laisse le courant intouché. Partagée
    depuis la revue D-41 du 24/09/2026 (M7)."""
    pid = f"m_{uuid4().hex[:8]}"
    rec = dict(cur, id=pid, project_id=pid, name=_project_name(name, fallback))
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_json_atomic,
                                    _project_path(pid, create=True), rec)
            if courant:
                await asyncio.to_thread(_write_saved, rec)
        except OSError as e:
            raise HTTPException(500, f"Écriture du projet impossible : {e}")
    return rec


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
    if not ouvrable and d.get("vide") is not True:   # E-1 : un vide s'ouvre
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


# D-37 (L7-B, 24/09/2026) — EXPORT EDL / FCPXML de la timeline SAUVEGARDÉE.
# Le client pousse d'abord sa sauvegarde (POST /save) puis appelle cette
# route : c'est le disque qui fait foi, comme pour GET /project. Le format
# est jugé AVANT toute lecture ; les sources sont résolues UNE fois chacune
# par `_resolve_src` (la même loi que le rendu), sondées (durée, son) pour les
# DEUX formats — revue du 24/09/2026 : sans la durée, l'EDL ne pouvait pas dire
# `* HANDLES: insuffisantes`. Le calcul est PUR (`edl_export`).
_EXPORT_FORMATS = {"edl": (".edl", "text/plain; charset=utf-8"),
                   "fcpxml": (".fcpxml", "application/xml; charset=utf-8")}


@router.get("/export")
async def montage_export(request: Request, format: str = ""):
    # revue finale du lot (24/09/2026) : la route livre des CHEMINS du disque
    # (SOURCE FILE, media-rep) — boucle locale seulement, comme les précalculs ;
    # la sauvegarde est lue hors de la boucle d'événements.
    _require_local(request)
    fmt = str(format or "").strip().lower()
    if fmt not in _EXPORT_FORMATS:
        raise HTTPException(400, "Format d'export inconnu — edl ou fcpxml.")
    rec = await asyncio.to_thread(_load_saved)
    clips = [c for c in (rec or {}).get("clips") or [] if isinstance(c, dict)]
    if not clips:
        raise HTTPException(400, "Aucune timeline sauvegardée à exporter.")
    meta = _tracks_meta(rec.get("tracks"))
    loop = asyncio.get_running_loop()
    resolve = {}
    for c in clips:
        k = _edl.src_key(c.get("src"))
        if not k or k in resolve:
            continue
        p = await _resolve_src(c.get("src"))
        if p is None:
            continue
        info = {"path": str(p), "video": p.suffix.lower() not in _AUDIO_EXTS}
        if p.suffix.lower() not in _IMAGE_EXTS:
            info["dur"] = await loop.run_in_executor(None, _probe_duration, p)
            info["audio"] = await loop.run_in_executor(None, _has_audio_stream, p)
        resolve[k] = info
    if fmt == "edl":
        texte = _edl.to_edl(rec, resolve, fps=30, meta=meta)
    else:
        texte = _edl.to_fcpxml(rec, resolve, fps=30, size=_CANVAS.get(
            str(rec.get("ratio") or "9:16"), _CANVAS["9:16"]), meta=meta)
    ext, mime = _EXPORT_FORMATS[fmt]
    nom = re.sub(r"[^A-Za-z0-9._-]+", "_", str(rec.get("name") or "")).strip("._") or "montage"
    return Response(content=texte.encode("utf-8"), media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="{nom[:60]}{ext}"'})


# D-42 (L7-B, 24/09/2026) — LES CHANGEMENTS DE PLAN d'un extrait de source,
# pour « Découper aux changements de plan » (menu contextuel d'un clip
# vidéo). Paramètres jugés AVANT toute résolution (400) ; la source passe par
# `_media_source` (boucle locale, 404 introuvable, 415 non vidéo — la même
# garde que les précalculs) ; le calcul est `scenes.detect` (cache disque,
# MediaError → 415 nommé par `_media_http`). `times` en secondes RELATIVES au
# `srcIn` demandé ; l'écran les convertit en temps de timeline (`dzmCutAt`).
_SCENES_DUR_MAX = 4 * 3600.0


def _scenes_num(v, nom: str, *, mini: float, maxi: float, strict: bool) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise HTTPException(400, f"{nom} illisible.")
    if not math.isfinite(f) or f > maxi or (f <= mini if strict else f < mini):
        raise HTTPException(400, f"{nom} hors bornes.")
    return f


@router.post("/scenes")
async def montage_scenes(request: Request):
    body = await _json_body(request)
    src_in = _scenes_num(body.get("srcIn", 0), "srcIn", mini=0.0, maxi=_SCENES_DUR_MAX * 6, strict=False)
    dur = _scenes_num(body.get("dur"), "dur", mini=0.0, maxi=_SCENES_DUR_MAX, strict=True)
    th = _scenes_num(body.get("threshold", 10.0), "threshold", mini=0.0, maxi=100.0, strict=True)
    p = await _media_source(request, body.get("src"), video=True)
    try:
        times = await asyncio.to_thread(_scenes.detect, p, src_in, dur, threshold=th)
    except Exception as e:
        raise _media_http(e)
    return {"ok": True, "times": times}


# D-25 (L6, 25/09/2026) — « APPRENDRE LE BRUIT » : le RMS d'une plage de
# bruit seul d'une source audio (le son d'un plan `{job_id}`, un son
# `{audio}`…), pour le plancher `nf` du débruiteur. Garde locale d'abord
# (403), plage jugée avant toute résolution (400 : 0,2 ≤ t1 − t0 ≤ 30 s,
# t0 ≥ 0), source par `_media_source(video=False)` (404), sans piste audio
# 415, plage commençant au-delà de la fin de la source 400. La plage passe
# par les filtres AMONT du vocabulaire présents dans `fx` (filter, dehum,
# eq3 — ceux que le préfixe traverse au rendu, dans l'ordre du vocabulaire)
# puis `astats` (RMS global ; son « Noise floor dB » n'est PAS utilisable,
# mesuré). Plage muette (RMS −inf) → 200 {ok:false, reason:"muet"} ; sinon
# {ok:true, rms_db, nf_db = sfx_service.nf_of(rms), t0, t1}.
_NP_MIN, _NP_MAX = 0.2, 30.0
_NP_UPSTREAM = ("filter", "dehum", "eq3")
_NP_RMS = re.compile(r"RMS level dB:\s*(-?inf|-?nan|-?[\d.]+)")


def _noise_profile_cmd(p: Path, t0: float, t1: float, fx: list[dict]) -> list[str]:
    """Commande pure de la mesure : -ss/-t AVANT -i, filtres amont, astats."""
    ch = sfx_service.fx_chain([e for e in fx if e.get("type") in _NP_UPSTREAM])
    af = (ch + "," if ch else "") + ("astats=measure_overall=RMS_level:"
                                     "measure_perchannel=none")
    return ["ffmpeg", "-hide_banner", "-nostats", "-ss", str(round(t0, 3)),
            "-t", str(round(t1 - t0, 3)), "-i", str(p), "-vn", "-af", af,
            "-f", "null", "-"]


@router.post("/noise-profile")
async def montage_noise_profile(request: Request):
    _require_local(request)
    body = await _json_body(request)
    t0 = _scenes_num(body.get("t0"), "t0", mini=0.0, maxi=_SCENES_DUR_MAX * 6, strict=False)
    t1 = _scenes_num(body.get("t1"), "t1", mini=0.0, maxi=_SCENES_DUR_MAX * 6 + _NP_MAX, strict=True)
    if not (_NP_MIN - 1e-9 <= t1 - t0 <= _NP_MAX + 1e-9):
        raise HTTPException(400, f"plage de bruit de {round(t1 - t0, 3)} s — "
                                 f"attendu {_NP_MIN} à {_NP_MAX:g} s.")
    raw_fx = body.get("fx")
    fx = sfx_service.sanitize_fx(raw_fx, "noise-profile") if isinstance(raw_fx, list) else []
    p = await _media_source(request, body.get("src"), video=False)
    if not await asyncio.to_thread(_has_audio_stream, p):
        raise HTTPException(415, f"« {p.name} » n'a pas de piste audio.")
    sdur = await asyncio.to_thread(_probe_duration, p)
    if sdur and t0 >= sdur - _NP_MIN + 1e-9:
        raise HTTPException(400, f"plage de bruit au-delà de la fin de "
                                 f"« {p.name} » ({round(sdur, 3)} s).")
    cmd = _noise_profile_cmd(p, t0, t1, fx)
    try:
        r = await asyncio.to_thread(_ff_run, cmd, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        raise HTTPException(502, "Mesure du bruit interrompue — ffmpeg a dépassé 60 s.")
    except (FileNotFoundError, OSError) as e:
        raise HTTPException(502, f"ffmpeg indisponible : {e}")
    if r.returncode != 0:
        # Revue L6 T2 : ffmpeg recopie le chemin COMPLET de la source dans
        # stderr — le message n'en garde que le nom de fichier.
        err = ((r.stderr or "").replace(str(p), p.name)
               .replace(str(p.parent), "").replace(p.parent.as_posix(), ""))
        raise HTTPException(502, f"Mesure du bruit échouée ({r.returncode}) : "
                                 f"{err[-400:]}")
    vals = _NP_RMS.findall(r.stderr or "")
    if not vals:
        raise HTTPException(502, "Mesure du bruit : astats n'a rien rendu.")
    try:
        rms = float(vals[-1])
        nf = sfx_service.nf_of(rms)
    except ValueError:
        return {"ok": False, "reason": "muet", "t0": t0, "t1": t1}
    return {"ok": True, "rms_db": round(rms, 2), "nf_db": nf, "t0": t0, "t1": t1}


# D-40 (L7-B, 24/09/2026) — LE SUIVI DU MOUVEMENT d'un extrait de source,
# pour « Suivre le mouvement » (section Cadrage de l'inspecteur d'un clip V1).
# Mêmes gardes que /scenes : paramètres jugés AVANT toute résolution (400),
# source par `_media_source` (404 / 415), calcul `reframe.motion_track`
# (cache disque, MediaError → 415 nommé). `points[].t` en secondes de
# SOURCE relatives au `srcIn` demandé.
@router.post("/reframe")
async def montage_reframe(request: Request):
    body = await _json_body(request)
    src_in = _scenes_num(body.get("srcIn", 0), "srcIn", mini=0.0, maxi=_SCENES_DUR_MAX * 6, strict=False)
    dur = _scenes_num(body.get("dur"), "dur", mini=0.0, maxi=_SCENES_DUR_MAX, strict=True)
    p = await _media_source(request, body.get("src"), video=True)
    try:
        res = await asyncio.to_thread(_reframe.motion_track, p, src_in, dur)
    except Exception as e:
        raise _media_http(e)
    return {"ok": True, **res}


# D-41 (L7-B, 24/09/2026) — AUTO-CLIPS d'une source parlée. Deux routes :
# `POST /autoclips` propose des extraits notés (service PUR `autoclips`),
# `POST /autoclips/create` en fait un PROJET nommé. Paramètres jugés AVANT
# toute résolution (400) ; source par `_media_source` (404 / 415 non vidéo).
# LE TEXTE : fourni (`text`) ou celui d'un chapitre (`chapter_id` →
# `Chapter.script_text`) → `align_to_audio` sur la source ELLE-MÊME (ffprobe
# + silencedetect lisent la piste son d'un mp4 : aucune extraction, mesuré
# par le banc [4] sur testsrc2+sine), gratuit. Sans texte : l'ESTIMATION
# (`estimate_transcription`) revient `{ok:false, estimate}` tant que
# `confirm` n'est pas `true` — puis `transcribe` (payant, synchrone : l'écran
# attend la réponse, comme /reframe). Un `confirm` sans clé configurée rend
# le même `{ok:false, estimate}` (estimate.ok false, `reason` lisible).
# REVUE du 24/09/2026 : la route reste SYNCHRONE (décision du contrôleur,
# datée) et les mots transcrits sont MIS EN CACHE (I1) sous
# `outputs/montage_cache/<sha(chemin résolu, taille, mtime_ns, fournisseur,
# langue)>_stt.json` — écriture atomique, jamais sur échec : une relance
# (« Lancer » une seconde fois, un autre `n`, `llm:false`) ne repaie pas, et
# la réponse le dit (`transcript: "stt:<f>:cache"`, sans `confirm` requis).
# `llm:false` (I4) : heuristique seule, aucun appel au modèle. `text` et
# `chapter_id` ensemble : 400 (M4). Durée sondée nulle : pas d'estimation
# (M5, `ok:false` dit).
_AUTOCLIPS_TEXT_MAX = 200_000
_AUTOCLIPS_SEGS_MAX = 2000
# Revue T6 (24/09/2026) — LE PLAFOND DE COÛT CONFIRMÉ. `confirm:true` exige
# `max_usd` : l'`usd` de l'estimation que l'utilisateur a VUE et cochée. Avant
# de payer, l'estimation refaite ici ne doit pas le dépasser de plus que cette
# tolérance d'arrondi (l'`usd` est rendu arrondi à 4 décimales par
# estimate_transcription) — sinon 409, rien n'est lancé. Défense serveur d'une
# faille client mesurée le 24/09/2026 (case cochée pour 0,05 $ restée cochée
# sous une nouvelle estimation à 0,40 $).
_AUTOCLIPS_USD_TOL = 0.0005
# Clôture L7-B (T8, 24/09/2026) — L'ARGENT, TROIS RESTES DES REVUES :
#  . VERROU par clé de cache de transcription (source, taille, mtime,
#    fournisseur, langue — la clé même de `_autoclips_stt_cle`) : une
#    transcription payante déjà EN COURS sur la même clé rend 409 « déjà en
#    cours » sans appeler `transcribe` (deux « Lancer » payants en parallèle,
#    deux onglets, payaient deux fois : le cache n'est écrit qu'au retour).
#    Test-et-pose SANS `await` entre les deux (la boucle est mono-fil), le
#    verrou est libéré en `finally` (échec compris). Ensemble du module,
#    borné par nature (une entrée par transcription en vol).
#  . Le 409 « coût dépassé » rend la NOUVELLE estimation dans son corps
#    (`estimate`, à côté de `detail`) : le client l'affiche NON cochée.
#  . `confirm:true` SANS `max_usd` n'est refusé (400) que sur le CHEMIN
#    PAYANT ; texte connu, chapitre ou transcription en cache : accepté.
_AUTOCLIPS_STT_EN_COURS: set[str] = set()


def _autoclips_stt_cle(p: Path, pid, lang) -> Path | None:
    import hashlib
    from app.services import montage_media as _MM
    try:
        st = p.stat()
    except OSError:
        return None
    brut = "%s|%d|%d|%s|%s|stt" % (p.resolve(), st.st_size, st.st_mtime_ns,
                                   pid or "", lang or "auto")
    key = hashlib.sha1(brut.encode("utf-8")).hexdigest()[:20]
    return _MM._cache_dir() / ("%s_stt.json" % key)


def _autoclips_stt_lire(cle: Path | None) -> dict | None:
    if cle is None or not cle.is_file():
        return None
    try:
        v = json.loads(cle.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None                     # cache illisible : on refait
    if not isinstance(v, dict) or not isinstance(v.get("words"), list) or not v["words"]:
        return None
    return v


def _autoclips_stt_ecrire(cle: Path | None, res: dict) -> None:
    from app.services import montage_media as _MM
    words = res.get("words") if isinstance(res, dict) else None
    if cle is None or not isinstance(words, list) or not words:
        return
    tmp = _MM._tmp_de(cle)
    try:
        tmp.write_text(json.dumps({"source": res.get("source"), "words": words,
                                   "audio_duration_s": res.get("audio_duration_s"),
                                   "end": res.get("end")}, ensure_ascii=False),
                       encoding="utf-8")
        _MM._ecrire(tmp, cle)
    except OSError as e:
        logger.warning(f"montage: cache de transcription non écrit — {e}")
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _autoclips_str(v, nom: str, maxi: int) -> str:
    if v is None:
        return ""
    if not isinstance(v, str) or len(v) > maxi:
        raise HTTPException(400, f"{nom} illisible ou trop long.")
    return v.strip()


def _autoclips_src(v):
    if not isinstance(v, (dict, str)) or not v:
        raise HTTPException(400, "src illisible.")
    return v


@router.post("/autoclips")
async def montage_autoclips(request: Request):
    from app.services import transcribe_service as T
    body = await _json_body(request)
    src = _autoclips_src(body.get("src"))
    text = _autoclips_str(body.get("text"), "text", _AUTOCLIPS_TEXT_MAX)
    chapter_id = _autoclips_str(body.get("chapter_id"), "chapter_id", 36)
    persona = _autoclips_str(body.get("persona"), "persona", 60) or None
    lang_raw = _autoclips_str(body.get("lang"), "lang", 5).lower()
    lang_stt = None if lang_raw in ("", "auto") else lang_raw
    provider = _autoclips_str(body.get("provider"), "provider", 20) or None
    n = body.get("n", 4)
    if isinstance(n, bool) or not isinstance(n, (int, float)) or not 1 <= n <= 8 or n != int(n):
        raise HTTPException(400, "n hors bornes — un entier de 1 à 8.")
    if text and chapter_id:             # M4 : deux textes, lequel ? on ne devine pas
        raise HTTPException(400, "text ou chapter_id, pas les deux.")
    use_llm = body.get("llm", True)     # I4 : « Classer avec l'IA » (défaut vrai)
    if not isinstance(use_llm, bool):
        raise HTTPException(400, "llm illisible — true ou false.")
    confirm = body.get("confirm") is True
    max_usd = body.get("max_usd")
    p = await _media_source(request, src, video=True)
    transcript = "align"
    if not text and chapter_id:
        from app.services.storage import Chapter
        async with async_session_factory() as session:
            ch = await session.get(Chapter, chapter_id)
        if ch is None:
            raise HTTPException(404, "Chapitre introuvable.")
        text = str(ch.script_text or "").strip()
        if not text:
            raise HTTPException(400, "Ce chapitre n'a pas de texte à caler.")
        transcript = "chapitre"
    if text:
        try:
            res = await asyncio.to_thread(T.align_to_audio, text, p, start=0.0,
                                          lang=lang_stt or "fr")
        except (ValueError, OSError) as e:
            raise HTTPException(400, f"Calage impossible : {e}")
    else:
        dur = await asyncio.to_thread(_probe_duration, p)
        try:
            est = T.estimate_transcription(dur, provider)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if dur <= 0:                    # M5 : on n'annonce pas un coût nul
            return {"ok": False, "estimate": dict(est, ok=False),
                    "reason": f"Durée de « {p.name} » illisible : aucune "
                              f"estimation possible, rien n'est lancé."}
        cle = _autoclips_stt_cle(p, est.get("provider"), lang_stt) if est.get("ok") else None
        res = await asyncio.to_thread(_autoclips_stt_lire, cle) if cle else None
        if res is not None:             # I1 : déjà payée, rendue gratuitement
            transcript = "stt:%s:cache" % (res.get("source") or "?")
        else:
            if not confirm or not est.get("ok"):
                return {"ok": False, "estimate": est,
                        "reason": est.get("reason") or "Transcription payante : "
                                  "confirmez le coût annoncé (confirm:true), ou "
                                  "donnez le texte connu (gratuit)."}
            if (isinstance(max_usd, bool) or not isinstance(max_usd, (int, float))
                    or not math.isfinite(max_usd) or max_usd < 0):
                raise HTTPException(400, "confirm:true exige max_usd : le coût annoncé que vous "
                                         "avez accepté (nombre ≥ 0) — rien n'est lancé.")
            usd = float(est.get("usd") or 0.0)
            if usd > float(max_usd) + _AUTOCLIPS_USD_TOL:
                return JSONResponse(status_code=409, content={
                    "detail": f"Coût estimé {usd:.4f} $ supérieur au plafond confirmé "
                              f"{float(max_usd):.4f} $ — rien n'est lancé, cochez puis "
                              f"confirmez le nouveau coût.",
                    "estimate": est})
            verrou = str(cle) if cle is not None else "src:%s|%s|%s" % (p.resolve(), est.get("provider"), lang_stt)
            if verrou in _AUTOCLIPS_STT_EN_COURS:
                raise HTTPException(409, "Transcription de cette source déjà en cours — rien "
                                         "n'est relancé ; relancez à son retour (elle sera "
                                         "rendue par le cache, sans repayer).")
            _AUTOCLIPS_STT_EN_COURS.add(verrou)
            try:
                try:
                    res = await asyncio.to_thread(T.transcribe, p, provider=provider,
                                                  language=lang_stt)
                except Exception as e:
                    raise HTTPException(502, f"Transcription impossible : {e}")
                await asyncio.to_thread(_autoclips_stt_ecrire, cle, res)
            finally:
                _AUTOCLIPS_STT_EN_COURS.discard(verrou)
            transcript = "stt:%s" % (res.get("source") or "?")
    words = res.get("words") or []
    # Revue L7-B : windows() mesurée à 1,3 s pour 18 000 mots — elle passe
    # dans le MÊME thread que score, jamais sur la boucle.
    def _fenetres_et_score():
        ws = _autoclips.windows(words)
        return ws, _autoclips.score(ws, None if use_llm else False, n, persona)
    wins, out = await asyncio.to_thread(_fenetres_et_score)
    return {"ok": True, "source": out["source"], "transcript": transcript,
            "words": len(words), "windows": len(wins),
            "duration": round(float(res.get("audio_duration_s") or res.get("end") or 0.0), 3),
            "clips": out["clips"]}


def _autoclips_num(v, nom: str) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise HTTPException(400, f"clip.{nom} illisible.")
    if isinstance(v, bool) or not math.isfinite(f) or f < 0 or f > _SCENES_DUR_MAX * 6:
        raise HTTPException(400, f"clip.{nom} hors bornes.")
    return f


@router.post("/autoclips/create")
async def montage_autoclips_create(request: Request):
    """{src, clip:{start, end, segments?, title?}, name?} → un PROJET NEUF
    (V1 = la fenêtre, A1 « son du plan » si la source a du son, S1 = les
    segments décalés de −start et coupés à [0, dur]) → `{ok, project_id, …}`.
    Le projet est ÉCRIT, pas ouvert : la timeline courante n'est pas touchée
    (l'écran l'ouvre ensuite par POST /projects/{pid}/open, geste E-1)."""
    body = await _json_body(request)
    src = _autoclips_src(body.get("src"))
    clip = body.get("clip")
    if not isinstance(clip, dict):
        raise HTTPException(400, "clip illisible.")
    start = _autoclips_num(clip.get("start"), "start")
    end = _autoclips_num(clip.get("end"), "end")
    if end - start < 0.3:
        raise HTTPException(400, "clip trop court (end − start < 0,3 s).")
    segs = clip.get("segments", [])
    if not isinstance(segs, list) or len(segs) > _AUTOCLIPS_SEGS_MAX:
        raise HTTPException(400, "clip.segments illisible ou trop long.")
    name = body.get("name")
    if name is not None and not isinstance(name, str):
        raise HTTPException(400, "name illisible.")
    p = await _media_source(request, src, video=True)
    if not isinstance(src, dict):
        src = _src_query(src)
    sdur = await asyncio.to_thread(_probe_duration, p)
    if sdur <= 0:                       # M1 : sans durée, aucune fenêtre n'est sûre
        raise HTTPException(415, f"Durée de « {p.name} » illisible : projet non créé.")
    end = min(end, sdur)
    if end - start < 0.3:               # M1 : la garde APRÈS le bornage
        raise HTTPException(400, "Le clip commence après la fin de la source "
                                 "(ou en garde moins de 0,3 s).")
    dur = round(end - start, 3)
    titre = str(clip.get("title") or "").strip()[:48]
    label = (titre or p.stem)[:48]
    clips = [{"tr": "v1", "id": "v1_ac", "label": label, "src": src,
              "srcIn": round(start, 3), "start": 0.0, "end": dur,
              "transition": "cut", "transition_s": 0.0}]
    if await asyncio.to_thread(_has_audio_stream, p):
        clips.append({"tr": "a1", "id": "a1_ac", "label": f"{label[:40]} · son du plan",
                      "src": src, "srcIn": round(start, 3), "start": 0.0, "end": dur})
    k = 0
    for sg in segs:
        if not isinstance(sg, dict):
            continue
        a = max(0.0, _f_or(sg.get("start")) - start)
        b = min(dur, _f_or(sg.get("end")) - start)
        txt = str(sg.get("text") or "").strip()
        if not txt or b - a < 0.05:
            continue
        k += 1
        s1 = {"tr": "s1", "id": f"s1ac{k:04d}", "start": round(a, 3), "end": round(b, 3),
              "text": txt, "label": txt if len(txt) <= 46 else txt[:45] + "…"}
        ws = []
        for w in sg.get("words") or []:
            if not isinstance(w, dict) or not str(w.get("w") or "").strip():
                continue
            ws.append({"w": str(w["w"]), "start": round(min(max(_f_or(w.get("start")) - start, a), b), 3),
                       "end": round(min(max(_f_or(w.get("end")) - start, a), b), 3)})
        if ws:
            s1["words"] = ws
        clips.append(s1)
    cur = _save_record({"name": name or titre or f"{p.stem} · auto-clip", "ratio": "9:16",
                        "duration": dur, "mix": {}, "clips": clips,
                        "tracks": _CLIENT_DEFAULT_TRACKS})
    rec = await _nouveau_projet(cur, name, titre or f"{p.stem} · auto-clip", courant=False)
    return {"ok": True, "project_id": rec["id"], **_project_meta(rec)}


def _f_or(v, d: float = 0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return d
    return f if math.isfinite(f) else d


def _rescale(a: int, b: int, c: int) -> int:
    """av_rescale de ffmpeg (arrondi au plus proche, moitié vers le haut)."""
    return (a * b + c // 2) // c if c > 0 else a


def _ov_fx_dims(dims, ow: int, oh: int, mode: str) -> tuple:
    """L5 — taille RÉELLE d'un overlay V2 après sa mise à l'échelle, pour le
    contexte des effets (pad, scale, hstack… s'appuient sur ctx w/h : une
    taille fausse ferait échouer le graphe). `dims` = (largeur, hauteur)
    sondées par /render, None → (ow, oh) tels quels.
    mode "-2" : `scale={ow}:-2` → h = av_rescale(ow, ih, iw·2)·2 ;
    mode "dec" : `scale=w={ow}:h={oh}:force_original_aspect_ratio=decrease`
    → (min(ow, av_rescale(oh, iw, ih)), min(oh, av_rescale(ow, ih, iw)))."""
    try:
        iw, ih = int(dims[0]), int(dims[1])
    except (TypeError, ValueError, IndexError):
        return ow, oh
    if iw <= 0 or ih <= 0:
        return ow, oh
    if mode == "-2":
        return ow, max(2, _rescale(ow, ih, iw * 2) * 2)
    return min(ow, _rescale(oh, iw, ih)), min(oh, _rescale(ow, ih, iw))


def _build_montage_command(v1, v2, a_clips, music, *, w, h, fps, mix_db,
                           ducking, duration_master, preview, out,
                           audio_only=False, subs_ass=None, titles_ass=None,
                           adjust_clips=None, preset=None, loudness=None,
                           loud_measured=None, range_out=None):
    """Commande ffmpeg complète (sync, testable). v1/v2/a_clips/music portent
    des chemins déjà résolus + durées sondées.

    D-24 : `loudness` ∈ _LOUD_TARGETS (sinon ValueError) ; en rendu final avec
    un vrai mix, `loud_measured` (dict de `_loudnorm_pass1`) est OBLIGATOIRE
    et la chaîne `[outa]loudnorm=…linear=true…,aresample=48000[outn]` est
    mappée à la place de `[outa]` ; aperçu / anullsrc / audio_only : rien.
    D-38 : `range_out=(a, b)` → `-ss a` juste avant `-t min(b,total)-a`
    (validé par `_range_args`, ValueError sinon) — sur la mesure audio
    seule aussi, pour que la passe 1 mesure ce que le fichier contiendra.

    R1 audio : a_clips/music acceptent en plus `fx_chain` (fragment ffmpeg
    déjà construit par sfx_service.fx_chain, "" = aucun) et `speed` (0.0 =
    inchangé, sinon 0.5–2 → atempo, la durée effective du clip devient
    d/speed) ; `ducking` accepte le bool historique OU un dict
    {threshold, ratio, attack, release} (sfx_service.parse_ducking).
    L6 D-25 : a_clips acceptent `fx_list` (liste normalisée sanitize_fx) ;
    si `sfx_service.learn_of(fx_list)` rend (a, b) et que a est dans la
    source, une SECONDE entrée `-ss a -t L -i path` fournit un préfixe de
    bruit de P = round(L·48000) échantillons exacts, concaténé devant le
    clip et appris puis retiré par le denoise (`afftdn@dn{n}`) ; l'entrée
    suivante décale donc idx de 2. La musique ignore l'apprentissage
    (plancher seul). Sans apprentissage : commande inchangée.
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
    des points portent rotate (cadre fixe hypot(iw,ih)) ; `mp` sans `tf` :
    défauts centre / échelle 1.
    D-14 : les 6-uplets de `mp` portent aussi scale|None et opacity|None —
    des points d'échelle différents → pad rgba + zoompan (z='…it…', toile
    fixe owmax × min(2·owmax, 3·h), média posé à owmin ; zoompan clampe z à
    10, donc smin ≥ smax/10 avec warning) ; des points d'opacité différents
    → sendcmd en tête de chaîne sur colorchannelmixer@mpo<j> aa (une
    commande [expr] par segment, TI ∈ 0..1, plus une plate finale) ; points
    tous égaux → filtre statique, la valeur des points fait foi sur `tf` /
    `opacity`. Aucun point porteur → chaîne de L2 octet pour octet.
    C4 : `speed` sur v1 (0.0 = inchangé, sinon 0.25..4 déjà clampé par
    _v1_speed) — l'input lit d·speed s de source (-t, borné au disponible)
    et setpts=PTS/speed AVANT fps remet le flux à la durée timeline ; la
    durée du segment (seg_durs) et donc offsets xfade / total / adelay ne
    bougent pas ; AUCUN atempo (l'audio V1 n'entre pas dans le graphe).
    D-13 : `dz` sur v1 (None = inchangé, sinon dict déjà clampé par _dz_spec :
    fenêtre {x0,y0,w0}→{x1,y1,w1} en fractions du cadre, ease doux|lin) —
    UN `zoompan` à d=1 (_dz_filter) posé APRÈS `fps={fps}` (donc après le
    `setpts=PTS/speed` de C4, sur un débit déjà constant : aucune image
    dupliquée) et AVANT `format=yuv420p` ; le temps est `it` borné à la durée
    du segment, tpad/trim/xfade en aval ne voient aucune différence.
    D-15 : `retime` sur v1 ("blend" | "flow", None = inchangé) — n'a de sens
    qu'AVEC `speed`. Ordre : setpts → [minterpolate] → fps → [tblend] →
    [zoompan] → format. `flow` (minterpolate mci à la cadence du canvas) va
    AVANT `fps=` ; `blend` (tblend moyenne) va APRÈS `fps=`, sur le flux déjà
    rematérialisé (A,(A+B)/2,B,… = Frame Blend) ; tpad/trim ramènent à
    seg_durs[k]. Sans vitesse : ignoré, chaîne historique.
    D-16 : `stab` sur v1 (None = inchangé, sinon {smooth, crop, zoom, trf}
    — clampé par _v1_stab, `trf` posé par /render après stab_detect). Avec
    un `trf` existant, l'entrée n'est plus tronquée par -ss/-t (le .trf est
    indexé par image d'ENTRÉE) et la chaîne commence par
    `vidstabtransform=input='…':smoothing:crop:zoom:optzoom=1:interpol=
    bilinear,trim=start=src_in:duration=d_src,setpts=PTS-STARTPTS,` avant
    `scale=`. `stab` sans `trf` (ou `trf` disparu) : warning, plan historique.
    L'audio d'une entrée V1 n'entre jamais dans le graphe (MESURÉ) : l'entrée
    entière ne désynchronise rien.
    D-40 : `reframe` sur v1 (None = inchangé, sinon dict nettoyé par
    _reframe_of) — seul le `crop={w}:{h}` du cover devient
    `crop={w}:{h}:x='clip(iw*X-w/2,0,iw-w)':y=(ih-h)/2` (_reframe_crop), X
    constant (manuel) ou interpolé en `t` LOCAL du flux lu (suivi ; le crop
    précède setpts=PTS/speed, donc t = temps de source depuis srcIn —
    mesuré le 24/09, voir reframe.py). Voies vitesse, zoom et stabilisation
    comprises ; overlays V2 intacts.
    S1 : `subs_ass` = chemin d'un fichier ASS déjà écrit (piste de
    sous-titres). Il devient le DERNIER maillon de la chaîne vidéo, juste
    avant `format=yuv420p` : le texte passe donc au-dessus des overlays V2 et
    couvre l'extension du maître de durée. None (défaut) : chaîne historique
    intacte, octet pour octet.
    D-21 : `titles_ass` = liste de chemins ASS (un par clip TITRE, déjà
    triés par début). Ils sont gravés JUSTE AVANT `subs_ass` — `[tt0]`,
    `[tt1]`… — pour que S1 reste le dernier maillon vidéo. Liste vide ou
    None (défaut) : chaîne historique intacte, octet pour octet. Le graphe
    `audio_only` n'ouvre aucune vidéo et rend AVANT ce bloc : un titre n'y
    entre jamais.
    D-9 (22/09/2026) : `adjust_clips` = liste de {start, end, effects} —
    les clips d'une piste d'AJUSTEMENT (genre `adjust`, sans source). Chaque
    clip est un post-pass `[aj{j}]` posé par `effects_engine.build_chain`
    sur le cadre COMPOSÉ (après le dernier overlay et le maître de durée),
    AVANT les titres et S1 — comme chez Resolve, où un clip d'ajustement
    agit sur tout ce qui est dessous. L'horloge y est GLOBALE : [start,
    end] devient t0/t1 de chaque effet (bornage de `_timed`, split +
    sendcmd + blend, jamais `enable=`) ; un effet qui porte déjà t0/t1
    (bornes LOCALES posées par le rack) est ramené dans [start, end] ; hors
    du clip ou < 0,05 s : l'effet est ignoré, jamais plein cadre (revue
    23/09/2026). Clip sans effet connu, bornes illisibles ou hors durée :
    rien n'est émis.
    None ou liste vide (défaut) : chaîne historique intacte, octet pour
    octet.
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
    # D-24 : la cible est validée AVANT tout travail — une cible hors liste
    # est une faute de l'appelant, pas un rendu « à peu près ».
    loud_t = _loud_target(loudness) if loudness is not None else None
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

    seg_durs, seg_idx, seg_stab = [], [], {}   # seg_stab : k → (trf, d_src)
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
                # D-16 : un plan stabilisé lit sa source ENTIÈRE (ni -ss ni
                # -t) — vidstabtransform indexe le .trf par image d'entrée ;
                # le trim se fait dans la chaîne (voir le bloc `k in seg_stab`
                # plus bas).
                # MESURÉ (grep ":a]") : l'audio d'une entrée V1 n'est jamais
                # référencé dans le graphe — aucune désynchronisation.
                trf = _v1_stab_trf(s)
                if trf is None:
                    if s["src_in"] > 0:
                        inputs.extend(["-ss", str(s["src_in"])])
                    inputs.extend(["-t", str(d_src), "-i", str(s["path"])])
                else:
                    inputs.extend(["-i", str(s["path"])])
                    seg_stab[len(seg_durs)] = (trf, d_src)
            seg_durs.append(d)
        if not audio_only:
            seg_idx.append(idx)
            idx += 1
    if not audio_only:
        sf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h},setsar=1,fps={fps},format=yuv420p")
        from app.services import effects_engine as _fx
        from app.services.subtitle_service import _ff_escape_path   # D-16
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
            # D-13 : dynamic zoom — zoompan (d=1) inséré APRÈS fps={fps},
            # donc sur le flux déjà rematérialisé à débit constant, et AVANT
            # format=yuv420p. Sans `dz` : dzp vide, préfixe historique.
            dzf = s.get("dz")
            dzp = f",{_dz_filter(dzf, w, h, fps, seg_durs[k])}" if isinstance(dzf, dict) else ""
            # D-40 : recadrage — seul le `crop` du cover change (fenêtre à x
            # fixe ou animé) ; sans `reframe` : crp = crop={w}:{h}, historique.
            crp = _reframe_crop(s.get("reframe"), w, h)
            if spd:
                # D-15 : retime — `flow` (minterpolate) AVANT fps=, `blend`
                # (tblend) APRÈS fps= et avant le zoompan (voir _RETIME).
                # Sans `retime` connu : rtp vide, préfixe C4 historique.
                rt = _v1_retime(s)
                rtp = f",{_RETIME[rt].format(fps=fps)}" if rt else ""
                pre = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                       f"{crp},setsar=1,"
                       f"setpts=PTS/{sfx_service.fnum(spd)}{rtp if rt == 'flow' else ''},"
                       f"fps={fps}{rtp if rt == 'blend' else ''}{dzp},format=yuv420p")
            else:
                pre = sf if not dzp and crp == f"crop={w}:{h}" else (
                    f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                    f"{crp},setsar=1,fps={fps}{dzp},format=yuv420p")
            # D-16 : stabilisation — vidstabtransform sur la source entière
            # PUIS trim=start=src_in:duration=d_src (ce que -ss/-t faisaient),
            # AVANT le recadrage : les bords découverts (crop=keep|black,
            # zoom) se décident à la résolution de la source. Segment absent
            # de seg_stab : préfixe historique octet pour octet.
            if k in seg_stab:
                trf, d_src = seg_stab[k]
                st = s["stab"]
                pre = (f"vidstabtransform=input='{_ff_escape_path(trf)}':"
                       f"smoothing={st['smooth']}:crop={st['crop']}:zoom={st['zoom']}:"
                       f"optzoom=1:interpol=bilinear,"
                       f"trim=start={sfx_service.fnum(s['src_in'])}:"
                       f"duration={sfx_service.fnum(d_src)},"
                       f"setpts=PTS-STARTPTS,{pre}")
            chain = (f"{pre},tpad=stop_mode=clone:stop_duration={seg_durs[k]},"
                     f"trim=0:{seg_durs[k]},setpts=PTS-STARTPTS")
            reff = s.get("effects")
            # D-30 : masque statique — limite la pile d'effets du clip ; sans
            # effet (ou masque invalide) il est ignoré, chaîne historique.
            rmk = _mr.mask_of(s.get("mask")) if reff else None
            if reff and rmk:
                # split → effets → alphamerge du masque (calculé UNE fois,
                # bouclé) → overlay sur l'original. `shortest=1` : MESURÉ
                # 24/09/2026 (9.0.1 = 8.1.1), sans lui le graphe ne finit
                # jamais (masque infini) ; avec : 60 images pour 2 s à 30 i/s.
                parts.append(f"[{seg_idx[k]}:v]{chain}[n{k}pre]")
                parts.append(f"[n{k}pre]split[mo{k}][me{k}]")
                parts += _fx.build_chain(reff, f"me{k}", f"mf{k}",
                                         f"cfx{k}",
                                         {"w": w, "h": h, "dur": seg_durs[k], "fps": fps})
                parts.append(f"[mf{k}]format=yuva420p[mfa{k}]")
                parts.append(_mr.mask_graph(rmk, w, h, fps, f"mk{k}"))
                parts.append(f"[mfa{k}][mk{k}]alphamerge[mm{k}]")
                parts.append(f"[mo{k}][mm{k}]overlay=0:0:shortest=1,"
                             f"format=yuv420p[n{k}]")
            elif reff:
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
        # L6 D-25 : bruit APPRIS. Le premier denoise de `fx_list` (liste
        # normalisée posée par /render et /measure) désigne une plage de
        # bruit seul en secondes de SOURCE ; elle entre comme SECONDE entrée
        # de la même source (`-ss a -t L`), forcée à P échantillons exacts à
        # 48 kHz (un préfixe plus court — fin de source, décodeur en retard
        # au seek — décalerait le retrait), concaténée DEVANT le clip,
        # traverse les filtres amont du vocabulaire (filter, dehum, eq3),
        # est apprise par `afftdn@dn{n}` (n unique dans le graphe) puis
        # retirée DANS le denoise : fondus et automation restent sur
        # l'horloge locale du clip. MESURÉ le 25/09/2026 : l'`asplit` du
        # plan bufférise tout le clip quand le préfixe est placé après lui
        # (359 460 Kio pour 10 min contre 19 100 avec une seconde entrée).
        # Plage entièrement hors de la source, ou durée de source INCONNUE
        # : pas de préfixe — MESURÉ : une entrée `-ss` au-delà de la fin ne
        # rend aucun paquet et fait échouer TOUT le rendu (« Nothing was
        # written into output file »). Revue T2 : la durée SONDÉE brute
        # voyage à part (`src_dur_sonde`, None = inconnue) — le repli 9999
        # de `src_dur` n'est plus lu comme une durée (une source réelle de
        # plus de 2 h 46 garde son apprentissage) ; un dict sans la clé
        # (bancs) lit `src_dur`. Sans apprentissage : chaîne inchangée
        # octet pour octet.
        lrn = sfx_service.learn_of(c.get("fx_list") or [])
        sd = c["src_dur_sonde"] if "src_dur_sonde" in c else c.get("src_dur")
        if lrn and (sd is None or
                    lrn[0] >= float(sd) - sfx_service.LEARN_MIN):
            logger.warning(f"montage: plage de bruit {lrn[0]}–{lrn[1]} s hors "
                           f"de la source ou durée inconnue ({sd} s) "
                           f"— apprentissage ignoré ({Path(str(c['path'])).name})")
            lrn = None
        l6pre = ""
        if lrn:
            L = round(lrn[1] - lrn[0], 3)
            P = int(round(L * sfx_service.DN_RATE))
            fxc = sfx_service.fx_chain(c["fx_list"], uid=f"{n}", prefix_s=L)
            inputs.extend(["-ss", str(round(lrn[0], 3)), "-t", str(L),
                           "-i", str(c["path"])])
            parts.append(f"[{idx + 1}:a]asetpts=PTS-STARTPTS,"
                         f"aresample={sfx_service.DN_RATE},atrim=end_sample={P},"
                         f"apad=whole_len={P}[l6p{n}]")
            parts.append(f"[{idx}:a]atrim={round(sin, 3)}:{round(sin + d, 3)},"
                         f"asetpts=PTS-STARTPTS,{proc}"
                         f"aresample={sfx_service.DN_RATE}[l6c{n}]")
            l6pre = f"[l6p{n}][l6c{n}]concat=n=2:v=0:a=1,"
            proc = ""
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
        head = (l6pre if lrn else
                f"[{idx}:a]atrim={round(sin, 3)}:{round(sin + d, 3)},"
                f"asetpts=PTS-STARTPTS,")
        parts.append(
            f"{head}{proc}{fades}{autom}"
            f"aresample=async=1,aformat=sample_rates=44100:"
            f"channel_layouts=stereo,volume={c['gain']},"
            f"adelay={dly}|{dly}[{'va' if c['tr'] == 'a1' else 'sa'}{n}]")
        (voice_lbl if c["tr"] == "a1" else sfx_lbl).append(
            f"[{'va' if c['tr'] == 'a1' else 'sa'}{n}]")
        idx += 2 if lrn else 1

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
            cut, fxw, fxh = len(och), w, h      # L5 : fin de la mise à l'échelle
            if op is not None and 0.0 <= op < 1.0:
                och += f",format=yuva420p,colorchannelmixer=aa={round(op, 3)}"
            och += f",setpts=PTS-STARTPTS+{st}/TB"
            pos = ""
            shadow = False
            if o.get("radius") or o.get("shadow"):
                # D-19 : jamais depuis /render (_ov_transform les porte dans
                # tf) — un appelant direct qui les pose à côté d'un tf None
                # est prévenu, la chaîne cover reste bit à bit.
                logger.warning(f"montage: overlay radius/shadow ignorés sur la "
                               f"chaîne cover (sans transformation) — overlay {j}")
        else:
            # Overlay transformé : largeur = scale·W (paire, hauteur suit le
            # ratio source), rotation sur fond transparent (rgba + c=none),
            # centre posé à (x·W, y·H) via les constantes w/h du filtre
            # overlay. L'opacité existante se compose (aa multiplie l'alpha),
            # l'alpha des PNG est préservé de bout en bout.
            # D-14 : points d'échelle / d'opacité — comme pour la rotation,
            # les points qui portent le champ FONT FOI sur la valeur statique
            # (tf["scale"], `opacity` du clip) ; tous égaux → filtre statique.
            sc_pts = [(q[0], q[4]) for q in mp if q[4] is not None] if mp else []
            op_pts = [(q[0], q[5]) for q in mp if q[5] is not None] if mp else []
            scale = tf["scale"]
            if sc_pts and len({round(s, 3) for _t, s in sc_pts}) == 1:
                scale, sc_pts = sc_pts[0][1], []
            if op_pts and len({round(v, 3) for _t, v in op_pts}) == 1:
                op, op_pts = op_pts[0][1], []
            if sc_pts:
                # Échelle animée (mesuré 22/09/2026, voir _MP_MAX_POINTS) :
                # `overlay` ignore un changement de taille de sa 2e entrée,
                # donc zoompan sur une toile FIXE owmax × 2·owmax (ratios
                # jusqu'à 1:2 entiers, au-delà `decrease` réduit) où le média
                # est posé à sa largeur MINIMALE puis grossi de z = s(t)/smin
                # (zoompan clampe z à 1..10 : smin remonte à smax/10). Horloge
                # `it` = celle de sendcmd et de rotate (pts locaux, avant le
                # setpts). Écart daté : le média est ré-agrandi depuis owmin
                # (zoompan ne sait que grossir), pas rendu à sa résolution
                # max — net jusqu'à ~2× (smax/smin ≤ 2), flou au-delà.
                smax = max(s for _t, s in sc_pts)
                s_lo = min(s for _t, s in sc_pts)
                smin = max(smax / 10.0, s_lo)
                if s_lo < smin:
                    logger.warning(f"montage: échelle minimale {s_lo:.2f} "
                                   f"relevée à {smin:.2f} (zoompan ×10 max) "
                                   f"— overlay {j}")
                fw = max(2, int(round(w * smax / 2.0)) * 2)
                # Rognage vertical invisible (y clampé −0,5..1,5 : une ligne à
                # plus de 1,5·h du centre n'est jamais dans le cadre) — avec
                # rotate + média très haut les coins tournés peuvent manquer.
                fh = max(2, min(2 * fw, 3 * h) // 2 * 2)
                owmin = max(2, int(round(w * smin / 2.0)) * 2)
                och = (f"scale=w={owmin}:h={fh}:force_original_aspect_ratio="
                       f"decrease,setsar=1,fps={fps},format=rgba")
                fxw, fxh = _ov_fx_dims(o.get("dims"), owmin, fh, "dec")
            else:
                ow2 = max(2, int(round(w * scale / 2.0)) * 2)
                och = f"scale={ow2}:-2,setsar=1,fps={fps},format=rgba"
                fxw, fxh = _ov_fx_dims(o.get("dims"), ow2, h, "-2")
            cut = len(och)                      # L5 : fin de la mise à l'échelle
            if op_pts:
                # Opacité animée : aa de colorchannelmixer n'est pas une
                # expression mais une option commandable (« T ») — sendcmd en
                # tête de chaîne, une commande [expr] par segment (TI 0..1)
                # + une plate finale, constante hors bornes (aa initial =
                # 1re clé).
                cmds = _mp_cmds(op_pts, f"colorchannelmixer@mpo{j}", "aa",
                                lambda v: "%.3f" % v)
                cut += len(f"sendcmd=c='{cmds}',")  # L5 : sendcmd reste en tête
                och = (f"sendcmd=c='{cmds}',{och},"
                       f"colorchannelmixer@mpo{j}=aa={round(op_pts[0][1], 3)}")
            elif op is not None and 0.0 <= op < 1.0:
                och += f",colorchannelmixer=aa={round(op, 3)}"
            # D-19 : coins arrondis — masque d'alpha par geq APRÈS l'opacité
            # (aa multiplie l'alpha, le masque ensuite) et AVANT la rotation
            # (les coins tournent avec l'image). Le rayon est borné DANS
            # l'expression sur la taille réelle (la hauteur n'est connue
            # qu'après `scale=-2`) — `min` de ffmpeg n'accepte que DEUX
            # arguments (mesuré 24/09/2026, 8.1.1 : la forme à trois rend
            # « Error initializing filters »), d'où l'imbrication. Pas sur
            # l'échelle animée (D-14) : zoompan re-échantillonne la toile.
            # Revue 24/09/2026 : le rayon du client est en px du canvas
            # natif (1080 de petit côté / 1920 en paysage — `pk` du client)
            # alors que w/h sont ceux du rendu (aperçu = canvas/4, preset
            # 2160) → mis à l'échelle par k = w / (1080|1920), ≥ 1 px. Coût
            # mesuré (revue 24/09/2026, 1080p) : geq ≈ 0,105 s/image, ×29
            # la chaîne nue — un masque statique (`alphamerge` d'un masque
            # calculé une fois) est noté pour L7-B, pas fait.
            k = w / (1080.0 if w <= h else 1920.0)
            rrad = int(tf.get("radius") or 0)
            rrad = max(1, int(round(rrad * k))) if rrad > 0 else 0
            shadow = bool(tf.get("shadow"))
            if sc_pts and (rrad > 0 or shadow):
                if rrad > 0:
                    logger.warning(f"montage: overlay radius ignoré (échelle "
                                   f"animée) — overlay {j}")
                if shadow:
                    logger.warning(f"montage: overlay shadow ignoré (échelle "
                                   f"animée) — overlay {j}")
                rrad, shadow = 0, False
            if rrad > 0:
                rm = f"min({rrad},min(W/2,H/2))"
                och += (f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                        f"a='alpha(X,Y)*(1-gt(hypot(max(abs(X-W/2)-(W/2-{rm}),0),"
                        f"max(abs(Y-H/2)-(H/2-{rm}),0)),{rm}))'")
            if sc_pts:
                zp = [(t, max(smin, s) / smin) for t, s in sc_pts]
                och += (f",pad=w={fw}:h={fh}:x=(ow-iw)/2:y=(oh-ih)/2:color=black@0,"
                        f"zoompan=z='{_mp_lerp_expr(zp, 'it')}':x='(iw-iw/zoom)/2'"
                        f":y='(ih-ih/zoom)/2':d=1:s={fw}x{fh}:fps={fps}")
            # R4b : la rotation s'anime si des points portent rotate — angle
            # interpolé (radians) sur l'horloge LOCALE du flux overlay (le
            # setpts de décalage vient après). Le cadre de sortie devient le
            # carré FIXE hypot(iw,ih) (rotw/roth dépendraient de t, que les
            # expressions ow/oh n'évaluent qu'à l'init) : le média reste
            # centré dedans, la pose x/y « centre − w/2 » ne change pas.
            rot_pts = [(q[0], q[3]) for q in mp if q[3] is not None] if mp else []
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
                xpts = [(round(st + q[0], 3), round(w * q[1], 2)) for q in mp]
                ypts = [(round(st + q[0], 3), round(h * q[2], 2)) for q in mp]
                pos = (f"x='({_mp_lerp_expr(xpts)})-w/2'"
                       f":y='({_mp_lerp_expr(ypts)})-h/2':")
            else:
                cx = round(w * tf["x"], 2)
                cy = round(h * tf["y"], 2)
                pos = f"x={cx}-w/2:y={cy}-h/2:"
        # L5 (décision 5 du plan) : pile d'effets du clip V2 — rendue juste
        # APRÈS la mise à l'échelle (`cut`) et AVANT opacité / coins /
        # rotation / décalage, puis `format=rgba` pour garder l'alpha (PNG,
        # chromakey). Masque D-30 : maskedmerge gbrap à QUATRE plans (alpha
        # compris — mesuré 24/09/2026 : alphamerge + overlay rendait OPAQUE
        # la partie transparente d'un PNG dans le masque) ; le masque est
        # calculé DIRECTEMENT à la taille de l'overlay (fxw × fxh, exacte :
        # _ov_fx_dims mesurée contre `scale` ; cover = w × h). Revue T2
        # second tour : plus de scale2ref (DÉPRÉCIÉ, 8.1.1 et 9.0.1
        # l'impriment). Sans effet : osrc/och historiques, octet pour octet.
        osrc = f"[{idx}:v]"
        oeff = o.get("effects")
        if oeff and tf is not None:
            # Chaîne transformée sans dimensions lisibles (ffprobe en échec) :
            # la taille réelle de l'overlay est inconnue, et 16 effets du
            # catalogue (pad, crop, hstack… sur ctx w/h) font tomber le graphe
            # avec une taille fausse (mesuré 24/09/2026) → pile et masque
            # ignorés, le rendu passe. Cover : taille w × h sans les dims.
            try:
                dok = int(o["dims"][0]) > 0 and int(o["dims"][1]) > 0
            except (KeyError, TypeError, ValueError, IndexError):
                dok = False
            if not dok:
                logger.warning(f"montage: dimensions de l'overlay {j} illisibles "
                               f"— pile d'effets (et masque) ignorée")
                oeff = None
        if oeff:
            from app.services import effects_engine as _fx2
            # fmt : l'enveloppe `_timed` (effets bornés t0/t1) travaille en
            # gbrap — en yuv420p elle perdait alpha et chroma hors fenêtre.
            fctx = {"w": fxw, "h": fxh, "dur": d, "fps": fps, "fmt": "gbrap"}
            parts.append(f"[{idx}:v]{och[:cut]}[ofi{j}]")
            # Revue T2 (mesuré 24/09/2026, ffmpeg 9.0.1) : 14 effets du
            # catalogue (vignette, bloom, vhs…) et toute enveloppe `_timed`
            # (passée par yuv420p) PERDENT l'alpha — le cadre transparent
            # d'un PNG devenait noir opaque sur tout le clip. Alpha final =
            # alpha d'ORIGINE × alpha de sortie de la pile (255 si elle n'en
            # a pas ; chromakey en CRÉE) : les deux branches en gbrap, puis
            # blend c3_mode=multiply (c0..c2 : normal à opacité 1 = la pile
            # telle quelle). Pas de gris intermédiaire (piège de plage 235).
            # Revue T2 second tour (mesuré 24/09/2026, 8.1.1 et 9.0.1) : la
            # pile recevait l'alpha d'origine et le RENDAIT pour ~28 effets
            # (grade_basic neutre, invert, curves, wheels…) → alpha AU CARRÉ
            # (PNG rouge α=128 sur bleu : 128,0,124 → 62,0,189). La pile
            # reçoit donc une copie OPAQUE (lutrgb=a=255) : alpha final =
            # alpha d'origine pour 48/50 effets, chromakey juste. Écarts
            # datés (24/09/2026, balayage des 50 effets × plein/borné ×
            # masque, 8.1.1 et 9.0.1 : 200/200 rendus à 50 images) : `glitch`
            # crée son propre alpha (multiplié, écart 48/255), `grain` s'écarte
            # de 7/255. Coût (1080×1920, 300 images) : lutrgb ≈ +0,6 ms/image ;
            # l'enveloppe `_timed` en gbrap ≈ 3 ms/image contre 1 en yuv420p.
            omk = _mr.mask_of(o.get("mask"))
            if omk:
                parts.append(f"[ofi{j}]format=rgba,split[omo{j}][ome{j}]")
                parts.append(f"[ome{j}]lutrgb=a=255[oma{j}]")
                parts += _fx2.build_chain(oeff, f"oma{j}", f"omf{j}", f"ofe{j}", fctx)
                parts.append(f"[omo{j}]format=gbrap,split[omb{j}][omq{j}]")
                parts.append(f"[omf{j}]format=gbrap[omg{j}]")
                parts.append(f"[omg{j}][omq{j}]blend=c3_mode=multiply[omh{j}]")
                parts.append(_mr.mask_graph(omk, fxw, fxh, fps, f"omk{j}",
                                            planes="gbrap", loop=False))
                parts.append(f"[omb{j}][omh{j}][omk{j}]maskedmerge[ofx{j}]")
            else:
                parts.append(f"[ofi{j}]format=rgba,split[ofo{j}][ofs{j}]")
                parts.append(f"[ofs{j}]lutrgb=a=255[ofa{j}]")
                parts += _fx2.build_chain(oeff, f"ofa{j}", f"ofq{j}", f"ofe{j}", fctx)
                parts.append(f"[ofq{j}]format=gbrap[ofg{j}]")
                parts.append(f"[ofo{j}]format=gbrap[ofb{j}]")
                parts.append(f"[ofg{j}][ofb{j}]blend=c3_mode=multiply[ofx{j}]")
            osrc, och = f"[ofx{j}]", "format=rgba" + och[cut:]
        if shadow:
            # D-19 : ombre portée — le flux (setpts compris : les deux côtés
            # du split héritent du même PTS) est doublé : l'image paddée de
            # 3u, l'ombre (noir à 55 %) paddée décalée de u PUIS floutée u
            # (revue 24/09/2026 : boxblur AVANT pad floutait un alpha
            # constant dans son propre cadre — bord net, alpha 0 → 140 sur
            # 1 px ; après pad le dégradé existe), u = 6 px à l'échelle k
            # (≥ 1) ; l'ombre SOUS l'image par overlay=0:0:format=auto (rgba
            # conservé) ; le label [ov{j}] et le maillon de composition
            # restent ceux de la chaîne nue. Écart daté : w/h du maillon de
            # pose = taille paddée — le canvas transparent s'étend de 3u
            # (re-revue 24/09/2026 : à 2u le dégradé était coupé à droite/en
            # bas, alpha 75/51/41 au dernier rang puis 0 ; à 3u : 17/5/1 —
            # marge droite 2u ≥ u+1),
            # l'image reste centrée sur sa pose « centre − w/2 ».
            u = max(1, int(round(6 * k)))
            parts.append(f"{osrc}{och}[oa{j}]")
            parts.append(f"[oa{j}]split[oo{j}][os{j}]")
            parts.append(f"[oo{j}]pad=iw+{6 * u}:ih+{6 * u}:{3 * u}:{3 * u}:"
                         f"color=black@0[op{j}]")
            parts.append(f"[os{j}]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,"
                         f"pad=iw+{6 * u}:ih+{6 * u}:{4 * u}:{4 * u}:color=black@0,"
                         f"boxblur={u}[osp{j}]")
            parts.append(f"[osp{j}][op{j}]overlay=0:0:format=auto[ov{j}]")
        else:
            parts.append(f"{osrc}{och}[ov{j}]")
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

    # D-38 : la plage de sortie est validée contre le total RÉEL (celui du
    # graphe, après le maître de durée) ; `total_out` = durée écrite, `total`
    # reste la durée du montage (valeur retournée, journal).
    ss, total_out = _range_args(range_out, total)

    if audio_only:
        # Mesure : le mix complet part dans ebur128 (framelog=verbose masque
        # le log par trame, seul le Summary sort au niveau info) puis est
        # jeté — aucun encodage, aucune vidéo.
        src = amap if amap.startswith("[") else f"[{amap}]"
        parts.append(f"{src}ebur128=peak=true:framelog=verbose[emeas]")
        cmd = ["ffmpeg", "-hide_banner", "-nostats", *inputs,
               "-filter_complex", ";".join(parts),
               "-map", "[emeas]", *ss, "-t", str(round(total_out, 3)),
               "-f", "null", "-"]
        return cmd, total

    # D-24 : passe 2. Après [outa] (aresample seul ou amix), en rendu FINAL
    # seulement et seulement s'il y a un vrai mix (anullsrc = silence, rien à
    # normaliser) : la chaîne loudnorm linéaire avec les valeurs de la passe
    # 1 sort en [outn], mappé à la place de [outa]. Sans passe 1 → ValueError
    # (`_loudnorm_chain`) : un loudnorm dynamique n'est pas ce que promet
    # « normalisée ».
    if loud_t is not None and not preview and amap.startswith("["):
        parts.append(f"{amap}{_loudnorm_chain(loud_t, loud_measured)}[outn]")
        amap = "[outn]"

    # --- D-9 (22/09/2026) : PISTE D'AJUSTEMENT ---------------------------
    # Chaque clip est un post-pass BORNÉ sur le cadre composé (V1 + overlays
    # + maître de durée), avant les titres et S1 — comme les clips
    # d'ajustement de Resolve, qui agissent sur tout ce qui est dessous. Le
    # bornage est celui de effects_engine._timed (t0/t1 → split + sendcmd +
    # blend, PAS enable=), en horloge GLOBALE ici (aucun setpts entre le
    # cadre composé et ce maillon). Un effet qui porte déjà t0/t1 (bornes
    # LOCALES posées par le rack) est ramené dans [start, end]. Sans clip
    # exploitable : rien n'est émis (commande historique) — build_chain([])
    # rendrait `[in]null[out]` et changerait la commande ; c'est `if not
    # bounded` (revue du 23/09/2026) qui l'empêche, la garde `not effs` en
    # amont n'est plus qu'un raccourci (mutation SURVIVANTE mesurée le
    # 23/09/2026, tests/mutations_montage_l3.py). `_fx` est le même module que celui des
    # segments V1 (lié plus haut, sous le même `if not audio_only:` — le
    # post-pass vient après le return d'audio_only). `total` est la durée
    # APRÈS le maître de durée : un clip qui déborde est coupé à la fin
    # réelle de la vidéo, un clip qui commence après elle est ignoré.
    for j, aj in enumerate(adjust_clips or []):
        if not isinstance(aj, dict):
            continue
        try:
            a0 = max(0.0, float(aj.get("start") or 0))
            a1 = min(float(total), float(aj.get("end") or 0))
        except (TypeError, ValueError):
            continue
        effs = [e for e in (aj.get("effects") or [])
                if isinstance(e, dict) and e.get("type") in _fx.EFFECTS]
        if a1 - a0 < 0.05 or not effs:
            continue
        bounded = []
        for e in effs:
            e2 = dict(e)
            try:
                lt0 = max(0.0, float(e.get("t0") or 0))
                lt1 = (float(e.get("t1")) if e.get("t1") is not None
                       else (a1 - a0))
            except (TypeError, ValueError):
                lt0, lt1 = 0.0, a1 - a0
            e2["t0"] = round(a0 + lt0, 3)
            e2["t1"] = round(min(a1, a0 + lt1), 3)
            # Revue (23/09/2026) : bornes locales HORS du clip ou < 0,05 s
            # → _timed rendrait la chaîne NUE (effet plein cadre, 0..total,
            # mesuré : `[n0]vignette=angle=0.600[aj0]` sans sendcmd). Rien.
            if e2["t1"] - e2["t0"] < 0.05:
                continue
            bounded.append(e2)
        if not bounded:
            continue
        parts += _fx.build_chain(bounded, cur, f"aj{j}", f"ajfx{j}",
                                 {"w": w, "h": h, "dur": total, "fps": fps})
        cur = f"aj{j}"

    # --- T1 : GRAVURE des TITRES (D-21, 21/09/2026) ---------------------
    # Un `.ass` par clip titre, gravé par le MÊME filtre que S1 — donc avec
    # le même `fontsdir` embarqué et le même échappement de chemin. Les
    # titres passent AVANT les sous-titres : S1 reste le dernier maillon
    # vidéo, un sous-titre ne doit jamais se retrouver sous un carton.
    # `cur` est repris à chaque maillon, si bien que le
    # `,format=yuv420p[outv]` d'après se pose sur `[tt{n-1}]` quand il n'y a
    # pas de S1 (mesuré : `[tt0]format=yuv420p[outv]`) — les deux branches
    # ci-dessous partent de `cur`, aucune ne suppose un nom de maillon.
    # Un titre qui DÉPASSE la fin de V1 n'est pas prolongé : la sortie est
    # coupée par `-t total` comme tout le reste, et l'événement ASS qui
    # courait encore disparaît avec l'image. Resolve, lui, allonge la
    # timeline jusqu'au dernier clip de n'importe quelle piste — écart à
    # dater dans la conception à la tâche 8.
    if titles_ass or subs_ass:
        from app.services.subtitle_service import subtitles_filter
    for j, tpath in enumerate(titles_ass or []):
        parts.append(f"[{cur}]{subtitles_filter(tpath)}[tt{j}]")
        cur = f"tt{j}"

    # --- S1 : GRAVURE des sous-titres (dernier maillon de la chaîne vidéo) ---
    # `fontsdir` n'est pas une précaution : sans lui libass cherche dans les
    # fontes SYSTÈME, ne trouve pas les fontes embarquées (Anton, Bebas Neue,
    # Archivo Black… ne sont pas des fontes Windows) et retombe SILENCIEUSEMENT
    # sur une autre — le rendu cesserait de ressembler à l'aperçu sans qu'aucune
    # erreur ffmpeg ne le signale. subtitles_filter() le pose toujours.
    # D-35 (23/09/2026) : le dernier maillon vidéo et la queue d'encodage
    # sont PARAMÉTRÉS par le preset de sortie (`_deliver_tail`). `preset`
    # est un dict RÉSOLU (`/render` passe par `_deliver_resolve`) ; une
    # chaîne est résolue ici sur les seuls presets intégrés (un id maison
    # n'est PAS connu de cette fonction — inconnu → master) ; l'aperçu
    # ignore le preset (queue historique 480p / x264 veryfast). Un `fps`
    # hors de `_DELIVER_FPS` avec un preset est une faute (ValueError) —
    # sans preset, la cadence historique de l'appelant est acceptée telle
    # quelle (les bancs l2/l3 rendent à 25).
    if isinstance(preset, str):
        preset = _deliver_resolve(preset, None)
    spec = preset if isinstance(preset, dict) else None
    # Revue T2 (23/09/2026, mesuré par le banc) : le GIF est EXEMPTÉ — /render
    # lui passe `fps = spec["fps"] = 12`, sa queue écrit `-r 12` elle-même ;
    # la garde le faisait échouer (« cadence 12 hors de… ») sur tout GIF
    # rendu par /render, ce qu'aucun espion T1 ne couvrait.
    if spec and not preview and not spec.get("gif") and int(fps) not in _DELIVER_FPS:
        raise ValueError(f"cadence {fps} hors de {_DELIVER_FPS}")
    cmd = _deliver_tail(spec, preview, fps, total_out, inputs, parts, amap, out,
                        cur, subtitles_filter(subs_ass) if subs_ass else None,
                        ss=ss)
    # Revue T2 (23/09/2026, MESURÉ sur « preuve e3 », ffmpeg 8.1.1 essentials) :
    # un clip à la fois STABILISÉ (vidstabtransform, D-16) et RETIMÉ EN FLUX
    # (minterpolate, D-15) plante ffmpeg par violation d'accès (0xC0000005,
    # rc 3221225477, frame=0 puis crash) de façon ALÉATOIRE — 3/4 et 2/3
    # sur la même commande, à 720 comme à 1080, avec OU sans loudnorm, à 25
    # comme à 30 i/s ; sans vidstab 0/3, sans minterpolate 0/3, et avec
    # `-filter_complex_threads 1` 0/6 — mais 3/6 dès que DEUX ffmpeg tournent
    # en même temps (preuve L4 du 23/09 au soir : 3 rendus sur 3 plantés
    # sous le serveur pendant que Chrome tournait). Sous la même charge :
    # `-threads 1` sur les DÉCODEURS 0/6, les deux drapeaux 0/8, sans l'un
    # des deux filtres 0/6. C'est une course entre les threads de décodage
    # h264 et la paire vidstab + minterpolate, pas un format non négocié :
    # les décodeurs ET le graphe passent alors sur un seul thread (minterpolate
    # domine de toute façon le temps, +2 s sur 34 mesurés ; l'encodeur garde
    # ses threads, `-threads` avant les entrées ne le touche pas). Revue
    # finale du lot (23/09) : `-threads` est une option PAR FICHIER (AVOption
    # codec, `ED.VA` dans `ffmpeg -h full`) — posée devant UNE entrée elle
    # ne couvre que celle-là, et le clip stab + flow n'est pas forcément la
    # première de V1 (tri par `start`) : elle est donc posée devant CHAQUE
    # `-i` du graphe, celui de la lavfi comprise. Les graphes
    # sans cette paire gardent leurs threads (commande historique octet pour
    # octet).
    if not audio_only:
        graphe = ";".join(parts)
        if "vidstabtransform=" in graphe and "minterpolate=" in graphe:
            k = cmd.index("-filter_complex")
            cmd[k:k] = ["-filter_complex_threads", "1"]
            for k in [i for i, t in enumerate(cmd) if t == "-i"][::-1]:
                cmd[k:k] = ["-threads", "1"]
    return cmd, total


def _loudnorm_pass1_cmd(v1, v2, a_clips, music, *, loudness, **kw):
    """Commande de la PASSE 1 (D-24), pure : EXACTEMENT le chemin
    `audio_only=True` de `_build_montage_command` (mêmes entrées, même graphe
    audio, même `-t`/`-ss`) dont le maillon `ebur128…[emeas]` est remplacé
    par `loudnorm=I=T:TP=-1.5:LRA=11:print_format=json[emeas]` → `-f null -`.
    → (cmd, total) ; cmd None quand le mix est vide (anullsrc : rien à
    mesurer, et `_build_montage_command` n'y posera aucun loudnorm)."""
    t = _loud_target(loudness)
    kw.pop("audio_only", None)
    kw.pop("out", None)
    kw.pop("preview", None)
    cmd, total = _build_montage_command(v1, v2, a_clips, music, preview=False,
                                        out=None, audio_only=True, **kw)
    i = cmd.index("-filter_complex") + 1
    if "anullsrc=" in " ".join(cmd[:i]):
        return None, total
    cmd[i] = cmd[i].replace(
        "ebur128=peak=true:framelog=verbose[emeas]",
        f"loudnorm=I={t}:TP=-1.5:LRA=11:print_format=json[emeas]")
    return cmd, total


def _loudnorm_pass1(v1, v2, a_clips, music, *, loudness, **kw):
    """Exécute la passe 1 (sync, ≤ 180 s comme /measure) → dict
    {I, TP, LRA, thresh, offset} pour `loud_measured`, None sans mix ;
    RuntimeError nommée si ffmpeg échoue, dépasse le délai ou ne rend pas
    de JSON."""
    cmd, _total = _loudnorm_pass1_cmd(v1, v2, a_clips, music, loudness=loudness,
                                      **kw)
    if cmd is None:
        return None
    try:
        r = _ff_run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise RuntimeError("mesure loudness (passe 1) interrompue — ffmpeg a "
                           "dépassé 3 min.")
    except (FileNotFoundError, OSError) as e:
        raise RuntimeError(f"mesure loudness (passe 1) : ffmpeg indisponible — {e}")
    if r.returncode != 0:
        raise RuntimeError(f"mesure loudness (passe 1) échouée ({r.returncode}) : "
                           f"{(r.stderr or '')[-400:]}")
    vals = _loudnorm_parse(r.stderr)
    if vals is None:
        raise RuntimeError("mesure loudness (passe 1) : aucun résumé JSON de "
                           "loudnorm dans la sortie ffmpeg.")
    # Revue (23/09/2026, mesuré) : un mix RÉEL mais MUET (piste à zéro, clip
    # muté, pad vide) rend input_i "-inf" / target_offset "inf" avec rc 0 ;
    # transmis en passe 2, ffmpeg refuse (« out of range [-99 - 0] »). Rien
    # à normaliser → None (même sort qu'anullsrc). SURTOUT PAS un clamp à
    # −99 : il amplifierait un bruit de fond de +85 dB.
    if not math.isfinite(vals["I"]):
        logger.info("montage loudnorm passe 1 : mix silencieux (I=-inf) — "
                    "pas de normalisation")
        return None
    logger.info(f"montage loudnorm passe 1 : I={vals['I']} TP={vals['TP']} "
                f"LRA={vals['LRA']} thresh={vals['thresh']} "
                f"offset={vals['offset']} (cible {loudness})")
    return vals


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


def _titles_ass(clips, meta: dict, canvas: tuple[int, int],
                stem: str) -> tuple[list[str], dict]:
    """D-21 — les clips TITRE de la timeline → (chemins des ASS, infos).

    Un clip titre vit sur une piste de genre `title` (cf. `_tracks_meta`) et
    n'a PAS de `src` : c'est `titles.title_spec` qui décide s'il y a quelque
    chose à graver (texte vide, `title` qui n'est pas un dict, durée nulle…
    → None, clip ignoré SANS lever). L'ordre rendu est celui du DÉBUT des
    clips, pas celui du tableau `clips` : deux titres qui se recouvrent sont
    alors empilés dans l'ordre où le spectateur les voit apparaître.

    Fonction à part, et non quelques lignes dans `montage_render` : c'est la
    seule forme sous laquelle la collecte est jouable par un banc sans
    lancer un rendu complet (le pré-vol P8 exige une source qu'ffmpeg ouvre).

    `infos` = {titres, ignores} — un clip titre ÉCARTÉ est compté et
    journalisé, jamais avalé en silence : sans ce compte, un carton dont le
    texte est vide disparaîtrait du rendu sans laisser de trace, et
    l'utilisateur chercherait dans ffmpeg une faute qui est dans sa timeline
    (même précédent que `info["unsupported"]` de `_subs_ass`).
    """
    from app.services import titles as TI
    specs, ignores = [], 0
    for c in clips or []:
        if not isinstance(c, dict):
            continue
        if (meta.get(str(c.get("tr"))) or {}).get("kind") != "title":
            continue
        s = TI.title_spec(c)
        if s:
            specs.append(s)
        else:
            ignores += 1
    specs.sort(key=lambda s: s.get("start", 0.0))
    out = []
    for i, s in enumerate(specs):
        p = TI.to_ass_title(s, canvas, f"{stem}_t{i}")
        if p is not None:
            out.append(str(p))
        else:
            ignores += 1
    if ignores:
        logger.warning(f"montage {stem}: {ignores} clip(s) titre ignoré(s) — "
                       f"texte vide, durée nulle ou `title` illisible ; "
                       f"{len(out)} titre(s) gravé(s).")
    return out, {"titres": len(out), "ignores": ignores}


# ------------------------------------------------ D-35 presets maison ------
# `deliver_presets.json` à côté de `montage_saved.json` (même data dir, même
# écriture atomique, même verrou `_ecrit`). Un preset maison n'est qu'un
# base + surcharges : {id, label, base, fps?, crf?} — aucun codec libre.
_PRESET_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_PRESETS_MAX = 50


def _deliver_presets_path() -> Path:
    return settings.images_path.parent / "deliver_presets.json"


def _load_deliver_presets() -> list:
    """Liste des presets maison, [] si absent / illisible / de forme
    inattendue — jamais une exception (le rendu ne doit pas échouer sur
    un fichier de presets corrompu)."""
    path = _deliver_presets_path()
    try:
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("montage: deliver_presets.json illisible — ignoré")
        return []
    lst = data.get("presets") if isinstance(data, dict) else data
    if not isinstance(lst, list):
        return []
    try:
        return _valider_presets(lst)
    except ValueError as e:
        logger.warning(f"montage: deliver_presets.json invalide ({e}) — ignoré")
        return []


def _valider_presets(lst) -> list:
    """Forme canonique ou ValueError nommée : `id` slug `^[a-z0-9_]{1,32}$`
    (ni un id intégré, ni doublon), `label` 1..60, `base` ∈ _DELIVER,
    `fps` ∈ _DELIVER_FPS | None, `crf` 0..51 | None, ≤ 50 entrées."""
    if not isinstance(lst, list):
        raise ValueError("liste attendue")
    if len(lst) > _PRESETS_MAX:
        raise ValueError(f"au plus {_PRESETS_MAX} presets maison")
    out, vus = [], set()
    for i, p in enumerate(lst):
        if not isinstance(p, dict):
            raise ValueError(f"preset n°{i + 1} : objet attendu")
        pid = p.get("id")
        if not isinstance(pid, str) or not _PRESET_ID_RE.match(pid):
            raise ValueError(f"preset n°{i + 1} : id invalide {pid!r} "
                             f"(a-z, 0-9, _ ; 1 à 32 caractères)")
        if pid in _DELIVER or pid in vus:
            raise ValueError(f"preset n°{i + 1} : id {pid!r} déjà pris")
        label = str(p.get("label") or "").strip()[:60]
        if not label:
            raise ValueError(f"preset {pid!r} : libellé vide")
        base = p.get("base")
        if base not in _DELIVER:
            raise ValueError(f"preset {pid!r} : base inconnue {base!r}")
        fps = p.get("fps")
        if fps is not None:
            if isinstance(fps, bool) or not isinstance(fps, int) or fps not in _DELIVER_FPS:
                raise ValueError(f"preset {pid!r} : fps {fps!r} hors de "
                                 f"{_DELIVER_FPS}")
        crf = p.get("crf")
        if crf is not None:
            if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
                raise ValueError(f"preset {pid!r} : crf {crf!r} hors de 0..51")
        vus.add(pid)
        out.append({"id": pid, "label": label, "base": base, "fps": fps,
                    "crf": crf})
    return out


@router.get("/deliver-presets")
async def montage_deliver_presets():
    """{builtins:[{id,label}], fps:[…], presets:[…maison]} — le client n'a
    AUCUNE liste en dur : les presets intégrés ET la liste des cadences
    viennent d'ici."""
    presets = await asyncio.to_thread(_load_deliver_presets)
    return {"builtins": [{"id": k, "label": v["label"]} for k, v in _DELIVER.items()],
            "fps": list(_DELIVER_FPS), "presets": presets}


@router.put("/deliver-presets")
async def montage_deliver_presets_put(request: Request):
    """Body : {presets:[{id,label,base,fps?,crf?}]} (ou la liste nue) →
    REMPLACE la liste entière, validée, écrite atomiquement sous verrou."""
    try:
        body = await request.json()
    except Exception:
        body = None
    lst = body.get("presets") if isinstance(body, dict) else body
    try:
        presets = _valider_presets(lst)
    except ValueError as e:
        raise HTTPException(400, f"Presets refusés : {e}")
    async with _ecrit:
        try:
            await asyncio.to_thread(_write_json_atomic, _deliver_presets_path(),
                                    {"presets": presets})
        except OSError as e:
            raise HTTPException(500, f"sauvegarde impossible : {e}")
    return {"ok": True, "presets": presets}


# Revue D-40 (24/09/2026) — COMMANDE LONGUE. CreateProcess refuse une ligne
# de plus de 32 767 caractères (WinError 206) : MESURÉ en revue, quatre clips
# V1 en mode suivi à points bruités font 38 013 caractères. Au-delà de
# _CMD_MAX (mesuré par subprocess.list2cmdline, la forme que Windows reçoit),
# le graphe part dans un fichier UTF-8 temporaire et `-filter_complex <g>`
# devient `-/filter_complex <fichier>` — la forme MESURÉE le 24/09 sur ffmpeg
# 8.1.1 (rc 0 ; `-filter_complex_script` passe encore mais s'annonce
# « deprecated, use -/filter_complex … instead »). Le fichier est lu par le
# même analyseur que l'argument : contenu identique, quotes comprises. Sous
# le seuil, ou sans -filter_complex : commande inchangée octet pour octet.
# Rendu (_run_ffmpeg), passe 1 loudnorm et /measure passent tous par ici.
_CMD_MAX = 30000


def _ff_run(cmd, **kw):
    """`subprocess.run(cmd, **kw)`, graphe long écrit dans un fichier (voir
    plus haut) et supprimé après l'exécution, succès ou échec."""
    fichier = None
    if "-filter_complex" in cmd and len(subprocess.list2cmdline(
            [str(a) for a in cmd])) > _CMD_MAX:
        import tempfile
        i = cmd.index("-filter_complex")
        fd, nom = tempfile.mkstemp(prefix="dzgraphe_", suffix=".txt")
        # Revue L7-B : le chemin est retenu AVANT l'écriture — un write qui
        # lève (disque plein, encodage) ne laisse pas le fichier derrière lui.
        fichier = Path(nom)
        try:
            with open(fd, "w", encoding="utf-8", newline="") as f:
                f.write(cmd[i + 1])
        except BaseException:
            _ff_menage(fichier)
            raise
        cmd = list(cmd[:i]) + ["-/filter_complex", nom] + list(cmd[i + 2:])
    try:
        return subprocess.run(cmd, **kw)
    finally:
        if fichier is not None:
            _ff_menage(fichier)


def _ff_menage(fichier: Path) -> None:
    """Supprime le graphe temporaire ; un OSError (fichier verrouillé par
    l'antivirus…) est journalisé, jamais levé : il ne masque ni le résultat
    de ffmpeg ni l'exception d'origine."""
    try:
        fichier.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"montage: graphe temporaire non supprimé {fichier} : {e}")


def _run_ffmpeg(cmd, out: Path) -> Path:
    try:
        r = _ff_run(cmd, capture_output=True, text=True,
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


# D-36 (23/09/2026) — FILE LOCALE DE RENDUS EN SÉRIE. Mesuré avant : deux
# `POST /render` = deux ffmpeg en parallèle (ni verrou ni file, `_run` part en
# `background_tasks`). Avec `queue:true` le job naît `queued` (statut EXISTANT
# de `JobStatus`, `progress` 0, `current_step` « En file ») et `_run` est
# poussé dans `_RENDER_QUEUE`, servie par UN worker asyncio créé au premier
# usage ; sans `queue`, comportement historique (immédiat, chevauchement
# autorisé). Pas de priorité ni d'annulation : une file, un worker, l'ordre
# d'arrivée. `_RENDER_PENDING` compte les jobs en file EN COMPTANT celui que
# le worker tient : c'est la `position` rendue (1 = prochain/en cours) —
# écart daté 23/09/2026 avec le `q.qsize()` du plan, qui exclut l'élément
# déjà pris et rendrait 1 au deuxième POST.
# Limites datées (revue 23/09/2026) : pas d'annulation au shutdown —
# `app/main.py` n'annule que news/sched/warm ; un ffmpeg en cours bloque la
# sortie comme le chemin historique — et pas de reprise des jobs `queued`
# orphelins après relance (comme les `generating_video` historiques). Pas de
# plafond sur la file ; les jobs `queued` d'une boucle précédente (worker
# recréé par `_ensure_worker`, async sans await — laissé tel quel, daté) ne
# sont jamais repris.
_RENDER_QUEUE: asyncio.Queue | None = None
_RENDER_WORKER: asyncio.Task | None = None
_RENDER_PENDING = 0


async def _render_worker():
    global _RENDER_PENDING
    q = _RENDER_QUEUE
    while True:
        fn = await q.get()
        try:
            await fn()
        except Exception as e:                      # _run attrape déjà tout
            logger.exception(f"montage: job en file échoué hors _run : {e}")
        finally:
            _RENDER_PENDING = max(0, _RENDER_PENDING - 1)
            q.task_done()


async def _ensure_worker() -> asyncio.Queue:
    """La file et son worker, créés sur la boucle COURANTE ; recréés si le
    task est mort/annulé ou appartient à une autre boucle (TestClient qui
    rouvre, relance)."""
    global _RENDER_QUEUE, _RENDER_WORKER, _RENDER_PENDING
    loop = asyncio.get_running_loop()
    vivant = (_RENDER_WORKER is not None and not _RENDER_WORKER.done()
              and _RENDER_WORKER.get_loop() is loop)
    if not vivant or _RENDER_QUEUE is None:
        _RENDER_QUEUE = asyncio.Queue()
        _RENDER_PENDING = 0
        _RENDER_WORKER = loop.create_task(_render_worker())
    return _RENDER_QUEUE


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
    global _RENDER_PENDING                      # D-36
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
    queue = bool(body.get("queue"))            # D-36
    if queue and preview:
        raise HTTPException(400, "la file est réservée aux rendus finaux — "
                                 "un aperçu se rend tout de suite.")
    ratio = str(body.get("ratio") or "9:16")
    w, h = _CANVAS.get(ratio, _CANVAS["9:16"])
    # D-35 : `fps` du payload (24|25|30|60, sinon 400) et `preset` → dict
    # résolu (intégré ou maison, inconnu → master). L'aperçu reste 480p /
    # 30 i/s / x264 quel que soit le preset ; le final prend la classe de
    # taille du preset sur le ratio du PROJET et l'extension du preset.
    fps_in = body.get("fps")
    if fps_in is not None:
        try:
            fps_ok = int(fps_in) in _DELIVER_FPS and not isinstance(fps_in, bool)
        except (TypeError, ValueError):
            fps_ok = False
        if not fps_ok:
            raise HTTPException(400, f"Cadence {fps_in!r} refusée — "
                                     f"{', '.join(map(str, _DELIVER_FPS))}.")
    spec = _deliver_resolve(body.get("preset"), fps_in, _load_deliver_presets())
    if preview:
        w, h = w // 4, h // 4
        w, h = w - w % 2, h - h % 2
        fps = 30
    else:
        w, h = _deliver_dims(ratio, int(spec["side"]))
        fps = int(spec["fps"])
    # D-24 : `loudness` None ou ∈ _LOUD_TARGETS (nombre, pas une chaîne) —
    # sinon 400 avant tout travail. D-38 : `range` None ou [a, b] validé ici
    # contre le total ESTIMÉ (max(end) des clips ; la commande revalide sur
    # le total réel) — sinon 400 « plage invalide ».
    loudness = body.get("loudness")
    if loudness is not None:
        try:
            loudness = _loud_target(loudness)
        except ValueError as e:
            raise HTTPException(400, f"loudness invalide — {e}")
    range_in = body.get("range")
    range_out = None
    if range_in is not None:
        total_est = 0.0
        for c in clips:
            try:
                total_est = max(total_est, float(c.get("end") or 0))
            except (TypeError, ValueError):
                continue
        if not isinstance(range_in, (list, tuple)) or len(range_in) != 2:
            raise HTTPException(400, f"plage invalide {range_in!r} — attendu "
                                     f"[début, fin] en secondes")
        try:
            _ss_chk, _ = _range_args(tuple(range_in), total_est)
            range_out = (float(range_in[0]), float(range_in[1]))
        except (ValueError, TypeError) as e:
            msg = str(e)
            raise HTTPException(400, msg if msg.startswith("plage invalide")
                                else f"plage invalide — {msg}")
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
    out_name = (f"montage_{short}_preview.mp4" if preview
                else f"montage_{short}{spec['ext']}")
    out = settings.outputs_path / "videos" / out_name
    title = (str(body.get("name") or "montage")[:60]
             + (" (aperçu 480p)" if preview else ""))
    # T2 (23/09/2026) : le titre du job final porte le preset quand ce n'est
    # pas le master — libellé intégré ou libellé MAISON (conservé par
    # `_deliver_resolve`), pour que la vue Livraison dise ce qui a été rendu.
    if not preview and spec.get("label") != _DELIVER[_DELIVER_DEFAUT]["label"]:
        title += f" ({spec['label']})"

    async with async_session_factory() as session:
        session.add(JobRecord(
            id=job_id,
            status=(JobStatus.QUEUED.value if queue
                    else JobStatus.GENERATING_VIDEO.value),
            progress=0 if queue else 10,
            title=title, image_filename=out_name, aspect_ratio=ratio,
            provider="montage",
            current_step="En file" if queue else "Préparation des sources"))
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
        nonlocal loudness          # remis à None si la passe 1 ne mesure rien
        try:
            loop = asyncio.get_running_loop()
            if queue:
                # D-36 : c'est ICI que « queued » devient « en cours ».
                async with async_session_factory() as session:
                    jr = await session.get(JobRecord, job_id)
                    if jr is not None:
                        jr.status = JobStatus.GENERATING_VIDEO.value
                        jr.progress = 10
                        jr.current_step = "Préparation des sources"
                        await session.commit()
            v1 = []
            for c in v1_in:
                p = await _resolve_src(c.get("src"))
                if p is None:
                    await _fail(f"Source vidéo introuvable : "
                                f"{c.get('label') or c.get('src')}")
                    return
                sdur = await loop.run_in_executor(None, _probe_duration, p)
                if _v1_retime(c) == "flow":
                    logger.info(f"montage: retime flow (minterpolate mci, LENT) — "
                                f"{c.get('label') or c.get('src')}")
                st = _v1_stab(c)
                if st:
                    # D-16 : l'analyse manquante se fait ICI, dans le job de
                    # rendu (déjà en tâche de fond) — le cache par source
                    # rend l'appel immédiat si POST /stab l'a déjà faite.
                    from app.services import montage_media as MM
                    async with async_session_factory() as session:
                        jr = await session.get(JobRecord, job_id)
                        if jr is not None:
                            jr.current_step = "Analyse de stabilisation"
                            await session.commit()
                    logger.info(f"montage: analyse de stabilisation (vidstabdetect, "
                                f"LENT) — {c.get('label') or c.get('src')}")
                    try:
                        trf = await asyncio.to_thread(MM.stab_detect, p)
                    except Exception as e:
                        await _fail(f"Stabilisation impossible : {e}")
                        return
                    st["trf"] = str(trf)
                rf = _reframe_of(c)     # D-40 — None = historique
                if rf is not None:
                    dims = await loop.run_in_executor(None, _probe_dims, p)
                    if dims and not _reframe_utile(dims[0], dims[1], w, h):
                        logger.info(f"montage: recadrage sans effet horizontal "
                                    f"(source {dims[0]}×{dims[1]} au moins aussi "
                                    f"haute que le cadre {w}×{h}) — "
                                    f"{c.get('label') or c.get('src')}")
                v1.append({"path": p, "src_dur": sdur or 9999.0,
                           "src_in": max(0.0, float(c.get("srcIn") or 0)),
                           "start": float(c.get("start") or 0),
                           "end": float(c.get("end") or 0),
                           "transition": c.get("transition"),
                           "transition_s": c.get("transition_s"),
                           "speed": _v1_speed(c),  # C4 — 0.0 = historique
                           "dz": _dz_spec(c),      # D-13 — None = historique
                           "reframe": rf,          # D-40 — None = historique
                           "retime": _v1_retime(c),  # D-15 — None = historique
                           "stab": st,             # D-16 — None = historique
                           "effects": (c.get("effects")
                                       if isinstance(c.get("effects"), list)
                                       else None)})
                rmk = _mr.mask_of(c.get("mask"))   # D-30 — absent = historique
                if rmk:
                    v1[-1]["mask"] = rmk
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
                # L5 : pile d'effets et masque D-30 des overlays — clés
                # ABSENTES sans pile / masque valides (dict historique). La
                # taille de la source est sondée pour le contexte des effets
                # (voir _ov_fx_dims) seulement quand une pile est posée.
                # Revue T2 second tour : une pile sans AUCUN type connu du
                # moteur ne rend rien (build_chain → null) — ni clé, ni sonde
                # ffprobe (la liste gardée reste entière quand un type l'est).
                from app.services import effects_engine as _fxr
                oeff = ([e for e in c["effects"] if isinstance(e, dict)]
                        if isinstance(c.get("effects"), list) else [])
                if not any(isinstance(e.get("type"), str)
                           and e["type"] in _fxr.EFFECTS for e in oeff):
                    oeff = []
                omk = _mr.mask_of(c.get("mask"))
                if omk:
                    v2[-1]["mask"] = omk
                if oeff:
                    v2[-1]["effects"] = oeff
                    # Restes L5 (24/09/2026, re-revue T2) : la chaîne COVER
                    # (ni transformation ni points de mouvement) a la taille
                    # w × h sans les dims — seule la chaîne transformée sonde.
                    if v2[-1]["tf"] is not None or v2[-1]["mp"]:
                        dims = await loop.run_in_executor(None, _probe_dims, p)
                        if dims:
                            v2[-1]["dims"] = tuple(dims)
            # D-9 : les clips d'une piste de genre `adjust` (sans `src`) →
            # post-pass bornés sur le cadre composé. Un clip sans effets est
            # transmis (effects == []) et la commande l'ignore ; une piste
            # inconnue de `meta` reste inerte comme avant.
            adjust = [{"start": float(c.get("start") or 0),
                       "end": float(c.get("end") or 0),
                       "effects": (c.get("effects")
                                   if isinstance(c.get("effects"), list) else [])}
                      for c in clips
                      if (meta.get(str(c.get("tr"))) or {}).get("kind") == "adjust"]
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
                # L6 : la liste NORMALISÉE suit le clip (`fx_list`) — le
                # builder y lit le bruit appris (learn_of) ; la chaîne sans
                # apprentissage reste celle-ci.
                fx_l = (sfx_service.sanitize_fx(
                    c.get("fx"), str(c.get("label") or c.get("tr")))
                    if c.get("fx") else [])
                fx_ch = sfx_service.fx_chain(fx_l) if c.get("fx") else ""
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
                             "fx_chain": fx_ch, "fx_list": fx_l, "speed": spd,
                             "volume_points": vp}
                else:
                    base = {"dialogue": g_voice, "musique": g_music,
                            "sfx": g_sfx}[bus]
                    a_clips.append({
                        "tr": "a1" if bus == "dialogue" else "a3",
                        "path": p, "src_dur": sdur or 9999.0,
                        "src_dur_sonde": sdur or None,   # revue L6 T2
                        "src_in": max(0.0, float(c.get("srcIn") or 0)),
                        "start": max(0.0, float(c.get("start") or 0)),
                        "end": float(c.get("end") or 0),
                        "gain": base if not gdb else
                        round(base * _db_to_gain(gdb), 4),
                        "fade_in": c_fi, "fade_out": c_fo,
                        "fade_in_curve": c.get("fade_in_curve"),
                        "fade_out_curve": c.get("fade_out_curve"),
                        "fx_chain": fx_ch, "fx_list": fx_l, "speed": spd,
                        "volume_points": vp})

            # D-24 : PASSE 1 (mesure) AVANT la commande finale, en rendu
            # final seulement — l'aperçu n'est pas normalisé. Son échec est
            # l'échec du job (message nommé), jamais un rendu « sans ».
            loud_measured = None
            # M1 (revue 23/09/2026) : le GIF jette le mix dans anullsink —
            # aucune passe 1 ; l'audio seul la garde. Mix vide OU muet (passe
            # 1 → None) : même sort qu'anullsrc, la commande part sans loudness.
            # Écart daté : le délai de la passe 1 est FIXE (180 s, ≈ 80 min de
            # mix mono-source) ; la plage est validée sur le total ESTIMÉ ici
            # et sur le total RÉEL dans la commande — un maître de durée plus
            # court donne un job failed « plage », pas un 400.
            if loudness is not None and not preview and not spec.get("gif"):
                async with async_session_factory() as session:
                    jr = await session.get(JobRecord, job_id)
                    jr.progress = 20
                    jr.current_step = f"Mesure loudness (cible {loudness} LUFS)"
                    await session.commit()
                loud_measured = await asyncio.to_thread(
                    _loudnorm_pass1, v1, v2, a_clips, music, loudness=loudness,
                    w=w, h=h, fps=fps, mix_db=mix, ducking=ducking,
                    duration_master=duration_master, adjust_clips=adjust,
                    range_out=range_out)
                if loud_measured is None:
                    loudness = None
            elif spec.get("gif"):
                loudness = None

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

            # D-21 : les clips TITRE (piste de genre `title`, sans `src`) →
            # un ASS chacun, écrits AVANT la commande comme celui de S1, au
            # canevas RÉEL du rendu (aperçu 480p compris, pour que les corps
            # suivent). Aucun clip titre : liste vide, commande historique.
            titles_ass, titles_info = await asyncio.to_thread(
                _titles_ass, clips, meta, (w, h), f"montage_{short}")

            cmd, total = _build_montage_command(
                v1, v2, a_clips, music, w=w, h=h, fps=fps,
                mix_db=mix, ducking=ducking,
                duration_master=duration_master, preview=preview, out=out,
                subs_ass=subs_ass, titles_ass=titles_ass, adjust_clips=adjust,
                preset=spec, loudness=loudness, loud_measured=loud_measured,
                range_out=range_out)
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
            if titles_ass:
                logger.info(f"montage {short}: {titles_info['titres']} titre(s) "
                            f"gravé(s) avant S1 "
                            f"({titles_info['ignores']} ignoré(s)) — "
                            f"{', '.join(Path(p).name for p in titles_ass[:4])}")
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

    if queue:
        q = await _ensure_worker()
        _RENDER_PENDING += 1
        position = _RENDER_PENDING
        q.put_nowait(_run)
        return {"ok": True, "job_id": job_id, "preview": False,
                "queued": True, "position": position,
                "message": f"Ajouté à la file — position {position} ; "
                           f"suivi dans la vue Livraison."}
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
        fx_l = (sfx_service.sanitize_fx(      # L6 : fx_list, comme /render
            c.get("fx"), str(c.get("label") or c.get("tr")))
            if c.get("fx") else [])
        fx_ch = sfx_service.fx_chain(fx_l) if c.get("fx") else ""
        spd = sfx_service.clamp_speed(c.get("speed"))
        vp = _volume_points(c)  # R4 : la mesure entend l'automation du rendu
        if m["loop"] and music is None:   # P1 — même règle qu'au rendu
            music = {"path": p,
                     "gain": g_music if not gdb else
                     round(g_music * _db_to_gain(gdb), 4),
                     "fade_in": c_fi, "fade_out": c_fo,
                     "fade_in_curve": c.get("fade_in_curve"),
                     "fade_out_curve": c.get("fade_out_curve"),
                     "fx_chain": fx_ch, "fx_list": fx_l, "speed": spd,
                     "volume_points": vp}
        else:
            base = {"dialogue": g_voice, "musique": g_music, "sfx": g_sfx}[bus]
            a_clips.append({
                "tr": "a1" if bus == "dialogue" else "a3",
                "path": p, "src_dur": sdur or 9999.0,
                "src_dur_sonde": sdur or None,           # revue L6 T2
                "src_in": max(0.0, float(c.get("srcIn") or 0)),
                "start": max(0.0, float(c.get("start") or 0)),
                "end": float(c.get("end") or 0),
                "gain": base if not gdb else
                round(base * _db_to_gain(gdb), 4),
                "fade_in": c_fi, "fade_out": c_fo,
                "fade_in_curve": c.get("fade_in_curve"),
                "fade_out_curve": c.get("fade_out_curve"),
                "fx_chain": fx_ch, "fx_list": fx_l, "speed": spd,
                "volume_points": vp})

    cmd, total = _build_montage_command(
        v1, [], a_clips, music, w=1080, h=1920, fps=30, mix_db=mix,
        ducking=ducking, duration_master=duration_master, preview=False,
        out=None, audio_only=True)

    def _measure():
        return _ff_run(cmd, capture_output=True, text=True, timeout=180)
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


# ----------------------------------------------------- lecture fluide (P7) ---
# Tâche 8, moitié BACKEND : de quoi rendre le balayage instantané sans que
# l'écran ait à décoder quoi que ce soit pendant qu'on glisse la tête de
# lecture. Quatre routes, un seul module de calcul (`montage_media`), un seul
# vocabulaire de source (`_resolve_src`, celui du Montage — job_id / audio /
# image / file_path). L'ÉCRAN n'est pas touché ici : ces routes n'ont pas
# encore de lecteur, et c'est dit — dette assumée jusqu'aux sections M17–M19.
#
#   GET  /peaks?src=<json>&bins=    l'enveloppe d'onde, en JSON
#   GET  /strip?src=<json>&n=&w=&h= une planche de vignettes, en JPEG
#   POST /proxy  {src}              fabrique l'aperçu 480p en tâche de fond
#   GET  /proxy?src=<json>          sert l'aperçu s'il existe, 404 sinon
#   GET  /duration?src=<json>       la durée de la source (P11), en secondes
#
# CE QUE CES ROUTES OUVRENT, ET CE QU'ON EN FAIT — la question ne se posait
# pas pour les routes de Montage existantes, qui CONSOMMENT une source dans
# un rendu ; celles-ci en rendent le CONTENU dérivé (un JPEG, un mp4, un
# JSON). Or `_resolve_src` accepte `{file_path}`, et c'est un chemin absolu
# LIBRE. Ce qui a été mesuré avant de trancher (05/09/2026) :
#   * `settings.HOST` vaut « 127.0.0.1 » (config.py l. 102) et ni un `.env`
#     ni le lanceur ne le surchargent (`grep -n HOST scripts/launch.ps1` :
#     aucune ligne) — le serveur est DÉJÀ borné à la boucle locale ;
#   * CORS n'est monté que sous `DEEPOTUS_DEV=1` (main.py l. 182) : une page
#     étrangère peut DÉCLENCHER un GET vers 127.0.0.1 mais ne peut pas en
#     LIRE la réponse ;
#   * `{file_path}` est un usage LÉGITIME et vivant du Montage : les
#     incrustations d'emoji le posent tel quel (frontend/patches/montage.js
#     l. 331, chemin produit par `POST /api/subtitles/emoji-hints`). Le
#     bannir casserait une fonction livrée.
# DÉCISION : on ne restreint pas le vocabulaire de `src` — on restreint
# l'APPELANT, en réutilisant la seule définition de « boucle locale » du
# dépôt (`routes._require_localhost`, déjà appliquée à 14 endroits sur la
# surface des clés d'API). Le geste ne coûte rien à un utilisateur réel
# (l'app est déjà en 127.0.0.1) et ferme le cas que cette fonction-là nomme
# elle-même : « même si HOST était mal configuré en 0.0.0.0 ».
# CE QUI RESTE OUVERT, DIT PLUTÔT QUE TU : un appelant DÉJÀ sur la machine
# peut obtenir la planche d'une vidéo ou l'onde d'un son qu'il pouvait de
# toute façon lire lui-même. Ces routes n'élargissent donc pas ce qu'un
# processus local atteint ; elles élargissent ce que la PAGE atteint, et la
# page est de même origine.


def _require_local(request: Request) -> None:
    """Refuse tout appelant hors boucle locale.

    RÉUTILISE `routes._require_localhost` — la liste des hôtes acceptés n'est
    écrite qu'UNE fois dans le dépôt, et une seconde copie ici aurait divergé
    (l'argument de P9 pour `/media-rules`, appliqué à une liste de sécurité).
    Seul le MESSAGE est reformulé : celui d'origine parle des réglages."""
    from app.api.routes import _require_localhost
    try:
        _require_localhost(request)
    except HTTPException:
        raise HTTPException(
            403, "Les précalculs du Montage ne sont accessibles que depuis "
                 "la machine qui exécute l'application.")


def _src_query(raw) -> dict | None:
    """Le `src` d'une chaîne de requête : du JSON, ou rien.

    Un `src` illisible n'est PAS une erreur 500 : c'est une source
    introuvable, et l'appelant lit le même 404 que pour un job supprimé."""
    try:
        v = json.loads(raw or "")
    except (TypeError, ValueError):
        return None
    return v if isinstance(v, dict) else None


async def _media_source(request: Request, src, *, video: bool) -> Path:
    """La source résolue d'une route de précalcul, gardée de bout en bout.

    `video=True` exige une VIDÉO au sens de `_is_video_artifact` — la MÊME
    autorité que la construction de timeline et que le sélecteur d'assets
    (`GET /media-rules`), jamais une seconde liste. Ce n'est pas une garde
    contre un plantage : MESURÉ (scratchpad/mesure2.py), ffmpeg RÉUSSIT le
    filmstrip et l'aperçu d'un PNG, et l'aperçu d'un `.wav` (un mp4 sans
    image). Sans cette garde, une planche de sprites ou un son rendraient un
    aperçu silencieusement faux — la classe de défaut exacte que P8 et le
    lot 3 ont fermée ailleurs. Le 415 nomme le fichier ; l'écran garde alors
    le fond qu'il sait déjà dessiner (image fixe en V1, rien ailleurs)."""
    _require_local(request)
    p = await _resolve_src(src if isinstance(src, dict) else _src_query(src))
    if p is None:
        raise HTTPException(404, "Source introuvable pour ce précalcul.")
    if video and not _is_video_artifact(p):
        raise HTTPException(
            415, f"« {p.name} » n'est pas une vidéo : ce précalcul n'est "
                 f"possible que sur {', '.join(_VIDEO_EXTS)}.")
    return p


def _media_http(e: Exception) -> HTTPException:
    """Une `MediaError` devient un 415 NOMMÉ, tout le reste un 502.

    La frontière est celle du diagnostic : `MediaError` porte un message
    construit pour être lu (ffmpeg absent, source sans flux audio, sortie
    ffmpeg réduite à ses lignes utiles) ; le reste est un défaut de code
    qu'il vaut mieux voir passer pour ce qu'il est."""
    from app.services.montage_media import MediaError
    if isinstance(e, MediaError):
        return HTTPException(415, str(e))
    logger.exception("montage: precalcul en erreur")
    return HTTPException(502, f"Précalcul impossible : {e}")


@router.get("/duration")
async def montage_duration(request: Request, src: str = ""):
    """La durée de `src`, en secondes. `{ok, dur, name}`.

    P11 — LA MOITIÉ BACKEND DE « un clip entre à la longueur de sa source ».
    L'écran ne connaît la durée d'un asset que si la base la porte ; MESURÉ le
    05/09/2026 sur un instantané COHÉRENT de la base de l'utilisateur
    (`sqlite3.connect('file:…?mode=ro', uri=True).backup(dst)` — 120 jobs,
    contre 106 pour une copie d'octets du seul `.db`, qui ignore le WAL) :
    `duration_s` est NULL pour DEUX de ses trois vidéos, et pour toute la
    famille `template`. Sans cette route, ces clips-là entrent sur un chiffre
    par défaut quoi qu'on fasse du plafond. Le sélecteur d'assets, lui, ne
    voit jamais `duration_real_s` : ce champ n'est calculé que par
    `GET /jobs/{id}`, un job à la fois, pas par la LISTE que le sélecteur
    charge.

    RIEN N'EST RECOPIÉ. La résolution de `src` est `_resolve_src` (le seul
    vocabulaire de source du Montage : job_id / audio / image / file_path),
    la garde de boucle locale et le 404 viennent de `_media_source`, et la
    mesure est `_probe_duration` — la même fonction que le rendu, que la
    construction de timeline et que `montage_media._dur`, qui n'en est qu'une
    vue depuis l'autre module.

    `video=False`, ET C'EST DÉLIBÉRÉ : un clip AUDIO doit lui aussi entrer à
    sa longueur, et la question posée ici (« combien de temps dure ce
    fichier ? ») a un sens pour un son comme pour une vidéo. Le piège de P7 —
    ffprobe rend « video » sur un PNG — ne mord PAS ici : on lit
    `format=duration`, pas `codec_type`, et MESURÉ sur les images de
    l'utilisateur ffprobe rend « N/A » (rc=0), donc `_probe_duration` rend
    0.0. Une image répond donc « je ne sais pas », ce qui est la vérité, et
    non une durée inventée.

    `dur: 0` VEUT DIRE « INCONNUE », JAMAIS « NULLE » : c'est le repli de
    `_probe_duration` pour ffprobe absent, source illisible, fichier sans
    durée. L'écran le lit ainsi et pose alors le clip sur son repli — en le
    disant. Une source RÉSOLUE mais non mesurable rend donc 200 avec `dur: 0`
    et non une erreur : elle existe, c'est sa durée qu'on ignore.

    COÛT, PROTOCOLE NOMMÉ : un ffprobe par appel, et un appel seulement quand
    un clip est posé sans durée connue — jamais au chargement de l'écran.
    Médiane de 12 appels après 3 de chauffe (`perf_counter`, ffprobe
    8.1.1-essentials_build, Windows 11 / AMD64) sur les vidéos RÉELLES de
    l'utilisateur : 72,4 ms (kapwing_sample, 8,3 Mo), 85,2 ms (Memecoin,
    6,9 Mo), 74,5 ms (sentry_bot, 6,2 Mo), 59,9 ms et 56,4 ms sur deux
    autres. `asyncio.to_thread` : la boucle d'événements n'attend pas.

    PAS DE CACHE ICI, ET C'EST UN CHOIX DÉCLARÉ. `routes._probe_seconds` en
    porte un (clé (chemin, mtime_ns), 512 entrées) mais c'est un AUTRE
    prober : délai d'attente de 15 s au lieu de 30, et `None` au lieu de 0.0
    quand il échoue. Les fondre en un seul est une tâche à part ; s'appuyer
    sur celui-là ici aurait fait entrer sa convention de retour dans le
    Montage par la bande. À 56–85 ms par pose de clip, l'absence de cache ne
    se voit pas."""
    p = await _media_source(request, src, video=False)
    dur = await asyncio.to_thread(_probe_duration, p)
    return {"ok": True, "dur": round(float(dur or 0.0), 3), "name": p.name}


@router.get("/has-audio")
async def montage_has_audio(request: Request, src: str = ""):
    """« Cette source porte-t-elle un flux audio ? » — `{ok, has_audio, name, dur}`.

    P12 — LA MOITIÉ BACKEND DE « le son d'un plan suit sa vidéo ». Le rendu
    n'entre JAMAIS l'audio embarqué d'un clip vidéo dans le graphe (`[idx:v]`
    seul, cf. `_run`) : sans clip jumeau sur la piste de dialogue, un plan
    parlant sort muet. La construction automatique (`montage_project`) pose
    ce jumeau depuis `_has_audio_stream` — mais AUCUNE route ne disait à
    l'écran « cette source a du son », et `addAsset` (sept portes) posait un
    clip vidéo et rien d'autre. MESURÉ le 06/09/2026 : `/duration` rend
    `{ok, dur, name}` (format=duration, pas de flux), `/media-rules` rend
    `{video_exts}`, `/peaks` est un décodage ffmpeg complet qui rend 415 sur
    une vidéo muette — pas une sonde. `_has_audio_stream` n'était exposée par
    rien.

    RIEN N'EST RECOPIÉ, c'est le motif de `/duration` : `_media_source`
    (résolution, garde de boucle locale, 404), `_has_audio_stream` (LA
    fonction que la construction de timeline et le rendu appellent déjà) et
    `_probe_duration` — la durée est rendue EN PRIME, parce qu'une seule
    sonde suffit aux deux besoins de l'écran (le verdict et la longueur du
    clip) et que l'appelant n'a alors qu'un aller-retour à attendre.

    `video=False`, COMME `/duration` : la question a un sens pour un son
    (qui a un flux audio) comme pour une vidéo ; une image répond `false`
    (aucun flux `a`) et `dur: 0`, ce qui est la vérité. Une source RÉSOLUE
    mais non sondable (ffprobe absent, fichier tronqué) rend 200 et
    `has_audio: false` — `_has_audio_stream` retombe sur `False` — et non
    une erreur : elle existe, c'est son contenu qu'on ignore. L'écran
    distingue les deux par `dur` (0 = rien n'a été mesuré) et le dit :
    `twinPlan` et `extract` (montage.js) sortent « non-sondable » — « la
    source n'a pas pu être sondée (aucune durée mesurable : fichier vide ou
    illisible) » — et non « muet ». Ce n'est pas un cas d'école : le
    « demo complete videogen brute.mp4 » (job f331277e) de la sauvegarde de
    l'utilisateur fait 0 octet sur disque (mesuré le 06/09/2026, base en
    copie `mode=ro`), et `route_has_audio_un_fichier_vide_repond_faux_et_
    zero_sans_echouer` ([7-bis] de test_montage_media.py) tient ce cas ici.

    Les deux sondes tournent EN PARALLÈLE (`asyncio.gather` sur deux
    `to_thread`) : deux ffprobe, ≈ 40–65 ms CHACUNE — chronométrées
    ELLES-MÊMES le 06/09/2026 (time.perf_counter autour du subprocess.run,
    quatre envois réels de l'utilisateur × trois passes, ffprobe 8.1.1) :
    `select_streams a` 39–63 ms, `format=duration` 39–62 ms sur les mêmes
    fichiers, le fichier de 0 octet le plus rapide (≈ 40 ms), le
    kapwing_sample (8 Mo) le plus lent (≈ 62 ms). La boucle d'événements
    n'attend ni l'une ni l'autre. Pas de cache ici, pour la raison dite
    dans la docstring de `/duration` ; le cache vit côté écran (un même
    fichier posé deux fois n'est sondé qu'une fois)."""
    p = await _media_source(request, src, video=False)
    has, dur = await asyncio.gather(asyncio.to_thread(_has_audio_stream, p),
                                    asyncio.to_thread(_probe_duration, p))
    return {"ok": True, "has_audio": bool(has), "name": p.name,
            "dur": round(float(dur or 0.0), 3)}


@router.get("/peaks")
async def montage_peaks(request: Request, src: str = "", bins: int = 300):
    """L'enveloppe d'onde de `src`, servie depuis le cache (JSON).

    `{peaks: [0..1] × bins, dur, bins}`. `bins` est écrêté à 8..2000 par
    `montage_media`, et c'est la valeur ÉCRÊTÉE qui décide aussi du fichier
    servi — sans quoi la route rendrait le chemin d'un `bins` jamais calculé.

    PAS de garde vidéo ici, et c'est voulu : l'onde d'un plan V1 (« le son du
    plan ») est exactement ce que la timeline veut dessiner. Ce qui est
    refusé, c'est une source dont ffmpeg ne tire AUCUN échantillon — 415 qui
    la nomme, plutôt qu'une onde plate qui affirmerait un silence.

    ON REND CE QUE `peaks` CALCULE, jamais un fichier de cache. La route
    passait par `peaks_path`, qui appelait `peaks`, JETAIT son dict et
    reconstruisait un chemin : sur la seule branche où `peaks` répond sans
    mettre en cache — l'ONDE PARTIELLE, ffmpeg s'est plaint mais a produit
    des octets — le fichier n'existait pas et cette route levait un 502. Le
    client ne pouvait donc JAMAIS recevoir cette onde-là. Le cache n'est pas
    perdu pour autant : c'est `peaks` qui le relit, en tête de fonction, et
    la ligne `pics_relus_du_cache_sans_recalcul` le mesure toujours."""
    from app.services import montage_media as MM
    p = await _media_source(request, src, video=False)
    try:
        return await asyncio.to_thread(MM.peaks, p, bins)
    except Exception as e:
        raise _media_http(e)


@router.post("/publish")
async def montage_publish(request: Request):
    """E-4 (22/09/2026) — le brouillon Scheduler est créé ICI, à la demande,
    jamais en effet de bord d'un rendu. Body : {job_id, channels?, run_at?,
    caption?, title?, project_id?}. Canaux filtrés par la liste blanche du
    plan (plan_schema._CHANNELS), ["x"] à défaut ; run_at = maintenant + 2 h
    (naïf UTC, comme le Scheduler le stocke) à défaut ; project_id voyage
    dans `brief` (colonne Text JSON existante : pas de migration). `run_at`
    est parsé ICI (ISO 8601, « Z » admis, un fuseau fourni ramené en UTC
    naïf — revue E-4) et c'est ICI que le 400 « run_at invalide » est émis,
    pas par le Scheduler. Même fabrique que lui (create_scheduled_post),
    importée LAZY comme routes.py importe ce module dans l'autre sens."""
    body = await _json_body(request)
    jid = str(body.get("job_id") or "").strip()
    if not jid:
        raise HTTPException(400, "job_id manquant.")
    async with async_session_factory() as session:
        job = await session.get(JobRecord, jid)
    if job is None:
        raise HTTPException(404, "Rendu introuvable.")
    fp = job.final_video_path or job.video_path
    # Revue E-4 : `_is_video_artifact` ne juge que le suffixe — un rendu dont
    # le fichier a disparu n'est pas publiable.
    if (str(job.status) != JobStatus.DONE.value or not fp
            or not _is_video_artifact(Path(fp)) or not Path(fp).is_file()):
        raise HTTPException(409, "Ce rendu n'est pas terminé (ou n'est pas une vidéo).")
    from app.services.plan_schema import _CHANNELS
    chs = body.get("channels") if isinstance(body.get("channels"), list) else []
    ch = [c for c in chs if isinstance(c, str) and c in _CHANNELS] or ["x"]
    # Revue E-4 : le Scheduler stocke run_at NAÏF et jette un fuseau fourni
    # (« +02:00 » devenait 09:00 UTC, 2 h en retard) — ramené en UTC ici.
    if body.get("run_at") in (None, ""):
        run_at = (_dt.utcnow() + _td(hours=2)).replace(microsecond=0)
    else:
        try:
            run_at = _dt.fromisoformat(str(body["run_at"]).strip().replace("Z", ""))
        except ValueError:
            raise HTTPException(400, "run_at invalide.")
        if run_at.tzinfo is not None:
            run_at = run_at.astimezone(_tz.utc).replace(tzinfo=None)
    titre = (body["title"] if isinstance(body.get("title"), str) and body["title"].strip()
             else (job.title or "Montage"))[:200]
    post = {"title": titre,
            "caption": (body["caption"] if isinstance(body.get("caption"), str) else titre)[:4000],
            "channels": ch, "run_at": run_at.isoformat(), "status": "draft", "mode": "assisted", "job_id": jid}
    pid = body.get("project_id")
    if isinstance(pid, str) and pid:
        post["brief"] = {"project_id": pid}
    from app.api.routes import create_scheduled_post
    return {"ok": True, "post": await create_scheduled_post(post)}


@router.get("/strip")
async def montage_strip(request: Request, src: str = "", n: int = 12,
                        w: int = 78, h: int = 44):
    """Une planche de `n` vignettes `w`×`h` (JPEG), servie depuis le cache."""
    from app.services import montage_media as MM
    p = await _media_source(request, src, video=True)
    try:
        out = await asyncio.to_thread(MM.strip, p, n, w, h)
    except Exception as e:
        raise _media_http(e)
    return FileResponse(out, media_type="image/jpeg")


# D-28 / D-31 / D-32 (L5, 24/09/2026) — ACCORD DE COULEUR, SCOPES, IMAGE
# ÉTALONNÉE. Trois routes de précalcul (garde `_media_source` : 403 hors
# boucle locale, 404 source introuvable, 415 non-vidéo) sur les services
# purs `color_match` et `grading` ; le calcul part en `to_thread`. Bornes
# communes : `t` fini ≥ 0 (au-delà de la durée, `grading` recule à
# durée − 0,1 : MESURÉ, `-ss` hors durée ne rend AUCUNE image avec un code 0),
# `effects` liste d'au plus 16 objets (sinon 400), `mask` assaini par
# `mask_of` (invalide → ignoré, comme au rendu).
_GRADE_EFFECTS_MAX = 16
_GRADE_W_DEFAUT = 240     # les bornes 96..640 sont celles de `_prev_w` (re-revue 4bda880 : constantes mortes ôtées)


def _grade_t(v) -> float:
    return _scenes_num(0.0 if v is None else v, "t", mini=0.0, maxi=86400.0, strict=False)


def _grade_effects(v) -> list:
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(e, dict) for e in v):
        raise HTTPException(400, "effects doit être une liste d'effets.")
    if len(v) > _GRADE_EFFECTS_MAX:
        raise HTTPException(400, f"Au plus {_GRADE_EFFECTS_MAX} effets par image étalonnée.")
    return v


def _grade_w(v) -> int:
    """Largeur de l'image étalonnée : MÊME règle que `_prev_w` — illisible
    (absent, texte, NaN, infini) → défaut 240, bornée 96..640, PAIRE.
    Restes L5 (24/09/2026) : `w=0`/négatif rendait 400 alors que `w=1` était
    ramené à 96 — une largeur est un confort, jamais un refus."""
    return _prev_w(v, _GRADE_W_DEFAUT)


@router.post("/color-match")
async def montage_color_match(request: Request):
    """Body `{target:{src,t}, ref?:{src,t}, auto?:bool}` → `{ok, effect, ref,
    target}` : l'effet `colormatch` qui aligne la cible sur la référence (ou,
    `auto`, sur des cibles neutres — `ref` est alors `null`). Ni `ref` ni
    `auto` → 400."""
    from app.services import color_match as CM
    _require_local(request)
    body = await _json_body(request)
    tgt = body.get("target") if isinstance(body.get("target"), dict) else {}
    ref = body.get("ref") if isinstance(body.get("ref"), dict) else None
    if ref is None and body.get("auto") is not True:
        raise HTTPException(400, "Il faut une référence (ref) ou auto: true.")
    t_tgt = _grade_t(tgt.get("t"))
    t_ref = _grade_t(ref.get("t")) if ref is not None else 0.0
    p_tgt = await _media_source(request, tgt.get("src"), video=True)
    p_ref = await _media_source(request, ref.get("src"), video=True) if ref is not None else None
    try:
        if p_ref is not None:
            # Restes L5 (24/09/2026) : les deux ffmpeg partent ENSEMBLE — la
            # première exception remonte (gather sans return_exceptions).
            s_tgt, s_ref = await asyncio.gather(
                asyncio.to_thread(CM.frame_stats, p_tgt, t_tgt),
                asyncio.to_thread(CM.frame_stats, p_ref, t_ref))
            eff = CM.match_effect(s_ref, s_tgt)
        else:
            s_tgt = await asyncio.to_thread(CM.frame_stats, p_tgt, t_tgt)
            s_ref, eff = None, CM.auto_effect(s_tgt)
    except Exception as e:
        raise _media_http(e)
    return {"ok": True, "effect": eff, "ref": s_ref, "target": s_tgt}


# Restes L5 (24/09/2026) : au plus DEUX calculs de scopes (ffmpeg) à la fois —
# le client les redemande à chaque arrêt de la tête de lecture. Sémaphore créé
# PARESSEUSEMENT sur la boucle courante et recréé si la boucle change (même
# piège que `_ensure_worker` : un objet asyncio lié à une autre boucle casse
# sous TestClient / après relance).
_SCOPES_MAX = 2
_SCOPES_SEM: tuple | None = None       # (boucle, asyncio.Semaphore)


def _scopes_sem() -> asyncio.Semaphore:
    global _SCOPES_SEM
    loop = asyncio.get_running_loop()
    if _SCOPES_SEM is None or _SCOPES_SEM[0] is not loop:
        _SCOPES_SEM = (loop, asyncio.Semaphore(_SCOPES_MAX))
    return _SCOPES_SEM[1]


@router.post("/scopes")
async def montage_scopes(request: Request):
    """Body `{src, t, effects?, mask?}` → PNG 512×512 (waveform, vectorscope,
    histogramme) de l'image ÉTALONNÉE. `no-store` : le client le redemande à
    chaque arrêt, le cache disque suffit."""
    from app.services import grading as GR
    _require_local(request)
    body = await _json_body(request)
    t = _grade_t(body.get("t"))
    effs = _grade_effects(body.get("effects"))
    p = await _media_source(request, body.get("src"), video=True)
    try:
        async with _scopes_sem():
            # re-revue 4bda880 (24/09) : le client a pu PARTIR pendant l'attente du sémaphore (tête déplacée : le
            # client abandonne sa requête) — alors rien ne se calcule : 499 (« client closed request », convention
            # nginx), sans corps, que personne ne lira ; ffmpeg n'est pas lancé et la place se libère aussitôt.
            if await request.is_disconnected():
                return Response(status_code=499)
            out = await asyncio.to_thread(GR.scopes_png, p, t, effs, body.get("mask"))
    except Exception as e:
        raise _media_http(e)
    return FileResponse(out, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/grade-frame")
async def montage_grade_frame(request: Request):
    """Body `{src, t, effects?, mask?, w?}` → JPEG de l'image étalonnée
    (`w` 96..640 pair, défaut 240) — aperçu du panneau Étalonnage et
    vignettes de la lightbox."""
    from app.services import grading as GR
    _require_local(request)
    body = await _json_body(request)
    t = _grade_t(body.get("t"))
    effs = _grade_effects(body.get("effects"))
    w = _grade_w(body.get("w"))
    p = await _media_source(request, body.get("src"), video=True)
    try:
        out = await asyncio.to_thread(GR.graded_frame, p, t, effs, body.get("mask"), w, "jpg")
    except Exception as e:
        raise _media_http(e)
    return FileResponse(out, media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=3600"})


@router.post("/proxy")
async def montage_proxy_build(request: Request,
                              background_tasks: BackgroundTasks):
    """Fabrique l'aperçu 480p de `src` en tâche de fond. Body : `{src}`.

    Réponse : `{ok, ready, job_id}`. `ready: true` (et `job_id: null`) quand
    le cache le porte déjà — aucun travail, aucun job. Sinon un `JobRecord`
    `provider="montage_proxy"` à suivre par `GET /api/jobs/{id}`.

    CE JOB NE PORTE AUCUN CHEMIN D'ARTEFACT, et c'est le cœur de la
    décision : voir `_PROXY_PROVIDER` plus haut. Le fichier se retrouve par
    `GET /proxy?src=…`, dont la clé de cache est une fonction de la source —
    l'écran n'a donc jamais besoin de lire ce chemin sur le job, et rien de
    ce qui interroge un artefact ne peut confondre un cache avec un plan."""
    from app.services import montage_media as MM
    return await _precalcul_de_fond(
        request, background_tasks, MM.proxy_path, MM.proxy,
        provider=_PROXY_PROVIDER, prefix="proxy",
        step="Aperçu 480p", step_done="Aperçu prêt")


async def _precalcul_de_fond(request, background_tasks, path_fn, build_fn, *,
                             provider, prefix, step, step_done):
    """Le corps commun de `POST /proxy` et `POST /stab` (D-16) : un précalcul
    PAR SOURCE, en tâche de fond, suivi par un `JobRecord` sans artefact.
    `path_fn(p)` rend le chemin de cache sans rien fabriquer, `build_fn(p)`
    fabrique (bloquant, passé à `to_thread`). Réponse `{ok, ready, job_id}`."""
    body = await _json_body(request)
    p = await _media_source(request, body.get("src"), video=True)
    try:
        out = await asyncio.to_thread(path_fn, p)
    except Exception as e:
        raise _media_http(e)
    if out.exists():
        return {"ok": True, "ready": True, "job_id": None}

    job_id = str(uuid4())
    async with async_session_factory() as session:
        session.add(JobRecord(
            id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=10,
            title=f"{prefix} — {p.name}"[:60],
            provider=provider,
            # `image_filename` est NON NUL en base (storage.py l. 24) : il
            # faut donc y écrire quelque chose. On suit la forme déjà en
            # usage pour les jobs qui n'ont pas d'image — `asset3d_<…>`,
            # `sprite_<court>` (routes.py) — c'est-à-dire un libellé SANS
            # EXTENSION : aucun filtre par extension ne peut le prendre pour
            # un média, et il dit ce qu'il est.
            image_filename=f"{provider}_{job_id[:8]}",
            # final_video_path / video_path : DÉLIBÉRÉMENT absents. Un cache
            # n'est pas un artefact — voir `_PROXY_PROVIDER` en tête.
            current_step=step))
        await session.commit()

    async def _run():
        try:
            await asyncio.to_thread(build_fn, p)
        except Exception as e:
            logger.warning(f"montage: {step.lower()} echoue — {e}")
            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                if jr is not None:
                    jr.status = JobStatus.FAILED.value
                    jr.error = str(e)[:2000]
                    jr.current_step = "Échec"
                    await session.commit()
            return
        async with async_session_factory() as session:
            jr = await session.get(JobRecord, job_id)
            if jr is not None:
                jr.status = JobStatus.DONE.value
                jr.progress = 100
                jr.current_step = step_done
                jr.completed_at = _dt.utcnow()
                await session.commit()

    background_tasks.add_task(_run)
    return {"ok": True, "ready": False, "job_id": job_id}


@router.post("/stab")
async def montage_stab_build(request: Request,
                             background_tasks: BackgroundTasks):
    """D-16 — lance (ou confirme) l'analyse vidstab d'une source ; même
    contrat que `POST /proxy` : `{ok, ready, job_id}`, suivi par
    `GET /api/jobs/{id}` (provider `montage_stab`, sans artefact). Le rendu
    fait lui-même l'analyse manquante ; cette route sert à l'anticiper."""
    from app.services import montage_media as MM
    return await _precalcul_de_fond(
        request, background_tasks, MM.stab_path, MM.stab_detect,
        provider=_STAB_PROVIDER, prefix="stab",
        step="Analyse de stabilisation", step_done="Analyse prête")


@router.get("/stab")
async def montage_stab_state(request: Request, src: str = ""):
    """`{ready}` — l'analyse vidstab de `src` est-elle en cache ? Ne fabrique
    jamais (même règle que `GET /proxy`) ; le `.trf` n'est jamais servi."""
    from app.services import montage_media as MM
    p = await _media_source(request, src, video=True)
    try:
        out = await asyncio.to_thread(MM.stab_path, p)
    except Exception as e:
        raise _media_http(e)
    return {"ready": out.exists()}


@router.get("/proxy")
async def montage_proxy_get(request: Request, src: str = ""):
    """L'aperçu 480p de `src` s'il est déjà fabriqué, 404 sinon.

    404 et non une fabrication à la volée : un aperçu prend des secondes, et
    une route de LECTURE qui encoderait bloquerait le premier balayage au
    lieu de l'accélérer. C'est `POST /proxy` qui fabrique."""
    from app.services import montage_media as MM
    p = await _media_source(request, src, video=True)
    try:
        out = await asyncio.to_thread(MM.proxy_path, p)
    except Exception as e:
        raise _media_http(e)
    if not out.exists():
        raise HTTPException(
            404, "Aperçu 480p pas encore fabriqué — POST /api/montage/proxy "
                 "le met en file.")
    return FileResponse(out, media_type="video/mp4")
