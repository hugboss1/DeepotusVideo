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

Mécanique vidéo : segments V1 ordonnés (src_in via -ss, durée exacte
tpad/trim), enchaînés par xfade (map _XFADE de template_service, « cut » =
fondu 1 image). Audio : clips A1/A3 posés à leur position timeline (adelay),
musique A2 en boucle coupée à la durée, gains dB par canal, mixage PAR CLIP
optionnel (gain −24..+12 dB multiplié au gain de bus, fondus afade 0..3 s à
courbe lin/douce/expo/log par côté — lin n'émet pas de curve= ;
musique : fade_in au démarrage, fade_out calé sur la fin du rendu), ducking
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
inchangée. Effets par clip :
moteur Effects/Mask existant (effects_engine.build_chain) sur chaque
segment V1 — catalogue exposé par GET /api/montage/effects. src_in audio :
les clips A1/A3 lisent leur source à partir de srcIn (atrim décalé).

Tout est local ffmpeg → 0 crédit, l'UI l'affiche avant déclenchement
(règle produit). Trous V1 : rendus en NOIR (segments lavfi à leur durée
timeline, compensée du chevauchement xfade des frontières pour que le clip
suivant retombe sur sa position — l'audio posé en adelay reste aligné).
"""
from __future__ import annotations

import asyncio
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


# ---------------------------------------------------------------- project ---

@router.get("/project")
async def montage_project(limit: int = 4):
    """Timeline initiale depuis la Bibliothèque : les `limit` derniers rendus/
    uploads finis en V1 (bout à bout, sans trous), la voix off la plus récente
    en A1, une musique (nom contenant theme/music/bgm/…) en A2."""
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
    return {"ok": True, "has_assets": has,
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
                           audio_only=False):
    """Commande ffmpeg complète (sync, testable). v1/v2/a_clips/music portent
    des chemins déjà résolus + durées sondées.

    R1 audio : a_clips/music acceptent en plus `fx_chain` (fragment ffmpeg
    déjà construit par sfx_service.fx_chain, "" = aucun) et `speed` (0.0 =
    inchangé, sinon 0.5–2 → atempo, la durée effective du clip devient
    d/speed) ; `ducking` accepte le bool historique OU un dict
    {threshold, ratio, attack, release} (sfx_service.parse_ducking).
    R2 : `fade_in_curve` / `fade_out_curve` (lin|douce|expo|log, voir
    _fade_curve) sur a_clips ET music — lin/absent n'émet pas de curve=.
    Sans ces champs, la commande émise est identique octet pour octet à
    l'historique (non-régression testée).

    audio_only=True (POST /measure) : MÊME graphe audio — mêmes durées de
    segments V1 (total, fondus musique, maître de durée), mêmes chaînes de
    mix — mais aucune vidéo ouverte ni décodée ; le mix sort dans ebur128
    (LUFS I / TP / LRA) et la sortie est jetée (-f null)."""
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
            d = round(min(want, avail), 3)
            if not audio_only:
                if s["src_in"] > 0:
                    inputs.extend(["-ss", str(s["src_in"])])
                inputs.extend(["-t", str(d), "-i", str(s["path"])])
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
            chain = (f"{sf},tpad=stop_mode=clone:stop_duration={seg_durs[k]},"
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
        parts.append(
            f"[{idx}:a]atrim={round(sin, 3)}:{round(sin + d, 3)},"
            f"asetpts=PTS-STARTPTS,{proc}{fades}"
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
    for j, o in enumerate(sorted(v2, key=lambda k2: k2["start"])):
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
            if abs(tf["rotate"]) >= 0.05:
                rad = round(tf["rotate"] * math.pi / 180.0, 6)
                och += (f",rotate={rad}:ow=rotw({rad}):oh=roth({rad}):c=none")
            och += f",setpts=PTS-STARTPTS+{st}/TB"
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
        parts.append(
            f"[{idx}:a]{mproc}{mf}aresample=async=1,aformat=sample_rates=44100:"
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
            parts.append("[vall]asplit=2[vsc][vmix]")
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
                           "effects": (c.get("effects")
                                       if isinstance(c.get("effects"), list)
                                       else None)})
            v2 = []
            for c in clips:
                if c.get("tr") != "v2":
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
                           "tf": _ov_transform(c)})
            a_clips, music = [], None
            for c in clips:
                if c.get("tr") not in ("a1", "a2", "a3"):
                    continue
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
                if c["tr"] == "a2" and music is None:
                    music = {"path": p,
                             "gain": g_music if not gdb else
                             round(g_music * _db_to_gain(gdb), 4),
                             "fade_in": c_fi, "fade_out": c_fo,
                             "fade_in_curve": c.get("fade_in_curve"),
                             "fade_out_curve": c.get("fade_out_curve"),
                             "fx_chain": fx_ch, "speed": spd}
                else:
                    base = g_voice if c["tr"] == "a1" else g_sfx
                    a_clips.append({
                        "tr": "a1" if c["tr"] == "a1" else "a3",
                        "path": p, "src_dur": sdur or 9999.0,
                        "src_in": max(0.0, float(c.get("srcIn") or 0)),
                        "start": max(0.0, float(c.get("start") or 0)),
                        "end": float(c.get("end") or 0),
                        "gain": base if not gdb else
                        round(base * _db_to_gain(gdb), 4),
                        "fade_in": c_fi, "fade_out": c_fo,
                        "fade_in_curve": c.get("fade_in_curve"),
                        "fade_out_curve": c.get("fade_out_curve"),
                        "fx_chain": fx_ch, "speed": spd})

            async with async_session_factory() as session:
                jr = await session.get(JobRecord, job_id)
                jr.progress = 30
                jr.current_step = ("Rendu ffmpeg (aperçu 480p)" if preview
                                   else "Rendu ffmpeg")
                await session.commit()

            cmd, total = _build_montage_command(
                v1, v2, a_clips, music, w=w, h=h, fps=fps,
                mix_db=mix, ducking=ducking,
                duration_master=duration_master, preview=preview, out=out)
            fx_n = sum(len(c["effects"] or []) for c in v1)
            logger.info(f"montage {short}: {len(v1)} clips V1 ({fx_n} effets), "
                        f"{len(v2)} overlays V2, {len(a_clips)} audio, "
                        f"musique={music is not None}, "
                        f"total≈{total}s → {out_name}")
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
                   "effects": None})
    a_clips, music = [], None
    for c in clips:
        if c.get("tr") not in ("a1", "a2", "a3"):
            continue
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
        if c["tr"] == "a2" and music is None:
            music = {"path": p,
                     "gain": g_music if not gdb else
                     round(g_music * _db_to_gain(gdb), 4),
                     "fade_in": c_fi, "fade_out": c_fo,
                     "fade_in_curve": c.get("fade_in_curve"),
                     "fade_out_curve": c.get("fade_out_curve"),
                     "fx_chain": fx_ch, "speed": spd}
        else:
            base = g_voice if c["tr"] == "a1" else g_sfx
            a_clips.append({
                "tr": "a1" if c["tr"] == "a1" else "a3",
                "path": p, "src_dur": sdur or 9999.0,
                "src_in": max(0.0, float(c.get("srcIn") or 0)),
                "start": max(0.0, float(c.get("start") or 0)),
                "end": float(c.get("end") or 0),
                "gain": base if not gdb else
                round(base * _db_to_gain(gdb), 4),
                "fade_in": c_fi, "fade_out": c_fo,
                "fade_in_curve": c.get("fade_in_curve"),
                "fade_out_curve": c.get("fade_out_curve"),
                "fx_chain": fx_ch, "speed": spd})

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
