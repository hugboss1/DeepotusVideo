# -*- coding: utf-8 -*-
"""SFX (gauntlet audio R1) — génération ElevenLabs + vocabulaire d'effets.

Trois responsabilités, partagées entre les routes audio (routes.py) et le
rendu Montage (montage_service.py) :

1. Génération de bruitages ElevenLabs (POST /v1/sound-generation) —
   `generate_sfx` : 1 à 4 variations séquentielles, sauvegarde atomique dans
   le dossier audio de la Bibliothèque + sidecar `_sfx_meta.json`
   (prompt / kind / created — servi par GET /api/audio/meta pour les tags et
   la recherche du tiroir Sons). Erreurs remontées `SfxError(status, msg)`
   préfixées « ElevenLabs: » (pattern maison des toasts fournisseur).

2. Vocabulaire FX partagé backend/frontend (contrat R1) — `sanitize_fx`
   clampe/valide `clips[].fx` (types inconnus ignorés avec warning) et
   `fx_chain` le traduit en fragment de filtergraph ffmpeg, dans l'ordre de
   chaîne FIXE : filter → eq3 → denoise → deesser → compressor → distortion
   → echo → reverb → stereo → normalize → (gain existant en aval).
   `clamp_speed` normalise clips[].speed (0.5–2, 0.0 = inchangé) et
   `parse_ducking` accepte le bool historique OU l'objet
   {enabled, ratio, attack_ms, release_ms, threshold}.

3. Aperçu / mesure — `build_audition_command` (extrait ≤ 12 s traité → WAV,
   -ss avant -i : latence < 2 s) et `parse_ebur128` (LUFS I / TP / LRA du
   stderr ffmpeg pour POST /api/montage/measure).

Aucune dépendance vers montage_service (imports à sens unique) ; ffmpeg /
ffprobe résolus via PATH comme partout ailleurs (le launcher ajoute
<app>\\bin au PATH en prod).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

_SFX_URL = "https://api.elevenlabs.io/v1/sound-generation"


class SfxError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _audio_dir() -> Path:
    p = settings.images_path.parent / "audio"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout.strip()
        return max(0.0, float(out))
    except (ValueError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return 0.0


def _g(v: float) -> str:
    """Nombre → chaîne ffmpeg déterministe (4 décimales max, sans zéros)."""
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


fnum = _g  # alias public (montage_service : atempo / sidechaincompress)


# ────────────────────────────── sidecar meta ───────────────────────────────

def _meta_path() -> Path:
    return _audio_dir() / "_sfx_meta.json"


def load_meta() -> dict:
    p = _meta_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"sfx meta illisible ({e}) — reparti de zéro")
        return {}


def record_meta(filename: str, entry: dict) -> None:
    """Ajoute/écrase l'entrée d'un fichier (écriture atomique .part→rename)."""
    meta = load_meta()
    meta[str(filename)] = entry
    p = _meta_path()
    tmp = p.with_name(p.name + ".part")
    try:
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, p)
    except Exception as e:
        logger.warning(f"sfx meta non sauvée ({filename}): {e}")
        tmp.unlink(missing_ok=True)


def known_meta() -> dict:
    """Sidecar filtré aux fichiers encore présents (pour GET /api/audio/meta)."""
    d = _audio_dir()
    return {fn: e for fn, e in load_meta().items()
            if isinstance(e, dict) and (d / Path(fn).name).is_file()}


_MUSIC_HINT = ("theme", "music", "bgm", "track", "musique", "instrumental")


def classify_kind(filename: str) -> str:
    """Kind par défaut d'un fichier importé (tags du tiroir Sons) : le nom
    évoque une musique → « musique », sinon « import »."""
    low = (filename or "").lower()
    return "musique" if any(h in low for h in _MUSIC_HINT) else "import"


# ─────────────────────── génération ElevenLabs SFX ─────────────────────────

def _slug(prompt: str) -> str:
    flat = unicodedata.normalize("NFKD", prompt).encode("ascii", "ignore")
    s = re.sub(r"[^a-z0-9]+", "_", flat.decode("ascii").lower()).strip("_")
    return s[:28].strip("_") or "sfx"


def _eleven_detail(r: httpx.Response) -> str:
    """Message d'erreur lisible depuis la réponse ElevenLabs (JSON ou texte)."""
    try:
        data = r.json()
        det = data.get("detail")
        if isinstance(det, dict):
            return str(det.get("message") or det.get("status") or det)[:300]
        if det:
            return str(det)[:300]
        return str(data)[:300]
    except Exception:
        return (r.text or f"HTTP {r.status_code}")[:300]


def generate_sfx(prompt: str, duration_s: float | None = None,
                 prompt_influence: float = 0.3,
                 variations: int = 1) -> tuple[list[dict], str | None]:
    """Génère 1–4 variations (appels séquentiels) → [{filename,url,name,
    size_kb,dur}], warning éventuel si une variation tardive a échoué.

    duration_s None = durée choisie par le modèle ; sinon clamp 0.5–22 s.
    Sauvegarde `sfx_<slug>_<hhmmss><n>.mp3` + sidecar (kind « sfx »).
    Bloquant (httpx sync) — à appeler via run_in_executor.
    """
    key = (settings.ELEVENLABS_API_KEY or "").strip()
    if not key:
        raise SfxError(400, "ElevenLabs: aucune clé API — ajoute-la dans "
                            "Réglages → Clés pour générer des bruitages.")
    prompt = (prompt or "").strip()
    if not prompt:
        raise SfxError(400, "ElevenLabs: prompt vide.")
    body: dict = {"text": prompt[:450],
                  "prompt_influence": round(
                      max(0.0, min(1.0, float(prompt_influence))), 3)}
    if duration_s is not None:
        body["duration_seconds"] = round(
            max(0.5, min(22.0, float(duration_s))), 2)
    variations = max(1, min(4, int(variations)))

    folder = _audio_dir()
    stamp = datetime.now().strftime("%H%M%S")
    slug = _slug(prompt)
    items: list[dict] = []
    warning: str | None = None
    with httpx.Client(verify=SSL_VERIFY, timeout=90.0) as client:
        for n in range(1, variations + 1):
            try:
                r = client.post(_SFX_URL, headers={"xi-api-key": key},
                                json=body)
            except httpx.HTTPError as e:
                msg = f"ElevenLabs: réseau injoignable — {e}"
                if items:
                    warning = msg
                    break
                raise SfxError(502, msg)
            if r.status_code != 200:
                st = r.status_code if 400 <= r.status_code < 500 else 502
                msg = f"ElevenLabs: {_eleven_detail(r)}"
                if items:                    # garder les variations réussies
                    warning = msg
                    break
                raise SfxError(st, msg)
            if not r.content:
                raise SfxError(502, "ElevenLabs: réponse audio vide.")
            fn = f"sfx_{slug}_{stamp}{n}.mp3"
            dest = folder / fn
            while dest.exists():             # collision (même prompt+seconde)
                fn = f"sfx_{slug}_{stamp}{n}_{os.urandom(2).hex()}.mp3"
                dest = folder / fn
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(r.content)
            os.replace(tmp, dest)
            dur = round(_probe_duration(dest), 2)
            record_meta(fn, {"prompt": prompt[:450], "kind": "sfx",
                             "duration_s": body.get("duration_seconds"),
                             "prompt_influence": body["prompt_influence"],
                             "created": datetime.now().isoformat(
                                 timespec="seconds")})
            items.append({"filename": fn, "url": f"/api/audio/{fn}",
                          "name": fn, "size_kb": dest.stat().st_size // 1024,
                          "dur": dur})
            logger.info(f"sfx: {fn} ({items[-1]['size_kb']} KB, {dur}s) — "
                        f"« {prompt[:60]} »")
    return items, warning


# ──────────────────── vocabulaire FX (contrat partagé) ─────────────────────

# Ordre de chaîne FIXE (contrat) — l'ordre d'arrivée du payload est ignoré.
_FX_ORDER = ("filter", "eq3", "denoise", "deesser", "compressor",
             "distortion", "echo", "reverb", "stereo", "normalize")

# type → {param: (lo, hi, défaut)} ; « mode » du filtre traité à part (enum).
_FX_PARAMS: dict[str, dict[str, tuple[float, float, float]]] = {
    "filter": {"freq": (20.0, 20000.0, 1000.0), "q": (0.1, 10.0, 1.0)},
    "eq3": {"bass_db": (-12.0, 12.0, 0.0), "mid_db": (-12.0, 12.0, 0.0),
            "treble_db": (-12.0, 12.0, 0.0)},
    "echo": {"time_ms": (20.0, 1500.0, 300.0), "feedback": (0.0, 90.0, 30.0),
             "mix": (0.0, 100.0, 30.0)},
    "reverb": {"mix": (0.0, 100.0, 30.0), "decay_s": (0.2, 8.0, 2.0)},
    "distortion": {"drive": (0.0, 100.0, 20.0)},
    "stereo": {"pan": (-100.0, 100.0, 0.0), "width": (0.0, 200.0, 100.0)},
    "compressor": {"threshold_db": (-60.0, 0.0, -20.0), "ratio": (1.0, 20.0, 4.0),
                   "attack_ms": (1.0, 500.0, 50.0),
                   "release_ms": (10.0, 2000.0, 250.0)},
    "denoise": {"amount": (0.0, 97.0, 12.0)},
    "deesser": {"intensity": (0.0, 100.0, 50.0)},
    "normalize": {"target_lufs": (-30.0, -10.0, -16.0)},
}
_FILTER_MODES = {"low": "lowpass", "high": "highpass", "band": "bandpass"}


def sanitize_fx(raw, label: str = "") -> list[dict]:
    """clips[].fx → liste normalisée [{type, params}] clampée au contrat.

    Types inconnus / entrées malformées : ignorés avec warning (jamais
    d'erreur — le rendu continue). {enabled:false} = module coupé, ignoré.
    Accepte les params à plat ({type, freq…}) ou imbriqués ({type, params}).
    """
    out: list[dict] = []
    if not isinstance(raw, list):
        if raw not in (None, [], ()):  # scalaire/objet inattendu
            logger.warning(f"montage: fx non-liste ignoré ({type(raw).__name__})"
                           f"{' — ' + label if label else ''}")
        return out
    for e in raw:
        if not isinstance(e, dict):
            logger.warning(f"montage: entrée fx malformée ignorée ({e!r:.60})"
                           f"{' — ' + label if label else ''}")
            continue
        t = str(e.get("type") or "").strip().lower()
        if t not in _FX_PARAMS:
            logger.warning(f"montage: type fx inconnu « {t or '?'} » ignoré"
                           f"{' — ' + label if label else ''}")
            continue
        if e.get("enabled") is False:
            continue
        src = e.get("params") if isinstance(e.get("params"), dict) else e
        params: dict = {}
        for k, (lo, hi, dv) in _FX_PARAMS[t].items():
            v = src.get(k, dv)
            try:
                f = float(v)
            except (TypeError, ValueError):
                f = float("nan")
            if f != f:  # NaN — jamais propagé dans un filtergraph
                logger.warning(f"montage: fx {t}.{k} invalide ({v!r}), défaut"
                               f"{' — ' + label if label else ''}")
                f = dv
            params[k] = max(lo, min(hi, f))
        if t == "filter":
            mode = str(src.get("mode") or "low").strip().lower()
            params["mode"] = mode if mode in _FILTER_MODES else "low"
        out.append({"type": t, "params": params})
    return out


def _fx_filter(p: dict) -> str:
    return (f"{_FILTER_MODES[p['mode']]}=f={_g(p['freq'])}"
            f":width_type=q:w={_g(p['q'])}")


def _fx_eq3(p: dict) -> str:
    bands = []
    if abs(p["bass_db"]) >= 0.05:
        bands.append(f"bass=g={_g(p['bass_db'])}:f=110")
    if abs(p["mid_db"]) >= 0.05:
        bands.append(f"equalizer=f=1000:t=q:w=1:g={_g(p['mid_db'])}")
    if abs(p["treble_db"]) >= 0.05:
        bands.append(f"treble=g={_g(p['treble_db'])}:f=8000")
    return ",".join(bands)


def _fx_echo(p: dict) -> str:
    if p["mix"] < 0.5:
        return ""
    t = max(1, int(round(p["time_ms"])))
    fb = max(0.01, min(0.9, p["feedback"] / 100.0))
    delays, decays, d = [], [], 1.0
    for k in range(1, 4):                       # 3 répétitions t, 2t, 3t
        d *= fb
        if d < 0.005 and delays:
            break
        delays.append(str(t * k))
        decays.append(_g(max(0.005, d)))
    og = _g(max(0.01, min(1.0, p["mix"] / 100.0)))
    return f"aecho=0.9:{og}:{'|'.join(delays)}:{'|'.join(decays)}"


def _fx_reverb(p: dict) -> str:
    if p["mix"] < 0.5:
        return ""
    dec = p["decay_s"]
    delays = [str(max(1, int(round(dec * 1000 * f))))
              for f in (0.043, 0.101, 0.187, 0.313)]  # 4 taps espacés
    gper = max(0.2, min(0.75, 0.3 + dec * 0.055))     # decays ∝ decay_s
    decays, d = [], 1.0
    for _ in range(4):
        d *= gper
        decays.append(_g(max(0.005, d)))
    og = _g(max(0.01, min(1.0, p["mix"] / 100.0)))
    return f"aecho=0.9:{og}:{'|'.join(delays)}:{'|'.join(decays)}"


def _fx_distortion(p: dict) -> str:
    if p["drive"] < 0.5:
        return ""
    pre = 1.0 + p["drive"] * 0.19               # drive 100 → ×20 avant clip
    return f"volume={_g(pre)},asoftclip=type=atan"


def _fx_stereo(p: dict) -> str:
    opts = []
    if abs(p["pan"]) >= 0.5:
        opts.append(f"balance_out={_g(p['pan'] / 100.0)}")
    if p["width"] < 99.5:                       # mono-mix partiel
        opts.append(f"slev={_g(p['width'] / 100.0)}")
    parts = []
    if opts:
        parts.append("stereotools=" + ":".join(opts))
    if p["width"] > 100.5:                      # élargissement
        t = max(0.0, min(1.0, (p["width"] - 100.0) / 100.0))
        parts.append(f"stereowiden=delay=15:feedback={_g(0.2 + 0.25 * t)}"
                     f":crossfeed={_g(0.15 + 0.35 * t)}:drymix=0.85")
    return ",".join(parts)


def _fx_compressor(p: dict) -> str:
    lin = 10.0 ** (p["threshold_db"] / 20.0)
    return (f"acompressor=threshold={_g(max(0.001, lin))}"
            f":ratio={_g(p['ratio'])}:attack={_g(p['attack_ms'])}"
            f":release={_g(p['release_ms'])}")


def _fx_denoise(p: dict) -> str:
    return f"afftdn=nr={_g(p['amount'])}" if p["amount"] >= 0.5 else ""


def _fx_deesser(p: dict) -> str:
    return (f"deesser=i={_g(p['intensity'] / 100.0)}"
            if p["intensity"] >= 0.5 else "")


def _fx_normalize(p: dict) -> str:
    return f"loudnorm=I={_g(p['target_lufs'])}:TP=-1.5:LRA=11"


_FX_BUILD = {"filter": _fx_filter, "eq3": _fx_eq3, "echo": _fx_echo,
             "reverb": _fx_reverb, "distortion": _fx_distortion,
             "stereo": _fx_stereo, "compressor": _fx_compressor,
             "denoise": _fx_denoise, "deesser": _fx_deesser,
             "normalize": _fx_normalize}


def fx_chain(fx: list[dict]) -> str:
    """Liste normalisée (sanitize_fx) → fragment de filtergraph ffmpeg
    (« aecho=…,acompressor=… »), ordre de chaîne fixe, "" si vide/no-op."""
    ordered = sorted((e for e in fx or ()),
                     key=lambda e: _FX_ORDER.index(e["type"]))
    frags = [f for e in ordered
             if (f := _FX_BUILD[e["type"]](e["params"]))]
    return ",".join(frags)


def clamp_speed(v) -> float:
    """clips[].speed → 0.0 (= inchangé, aucun atempo) ou 0.5–2 clampé."""
    if v is None:
        return 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f != f or abs(f - 1.0) < 1e-3:
        return 0.0
    return max(0.5, min(2.0, f))


def parse_ducking(v):
    """Champ ducking du payload render : bool historique OU objet
    {enabled, ratio, attack_ms, release_ms, threshold}.

    → bool (legacy, True = paramètres historiques en dur) ou dict
    {threshold, ratio, attack, release} clampé, False si désactivé."""
    if not isinstance(v, dict):
        return bool(v)
    if not v.get("enabled", True):
        return False
    out = {}
    for key, dst, lo, hi, dv in (("ratio", "ratio", 2.0, 20.0, 6.0),
                                 ("attack_ms", "attack", 5.0, 500.0, 50.0),
                                 ("release_ms", "release", 50.0, 2000.0, 400.0),
                                 ("threshold", "threshold", 0.01, 0.3, 0.05)):
        try:
            f = float(v.get(key, dv))
        except (TypeError, ValueError):
            f = dv
        if f != f:
            f = dv
        out[dst] = max(lo, min(hi, f))
    return out


# ─────────────────────────── audition & mesure ─────────────────────────────

def build_audition_command(src: Path, out: Path, *, src_in: float = 0.0,
                           length: float = 4.0, gain_db: float = 0.0,
                           speed: float = 0.0, fx: list[dict] | None = None
                           ) -> list[str]:
    """Extrait traité → WAV 44.1 k stéréo. -ss/-t AVANT -i (seek démuxeur,
    aucun décodage vidéo : -vn) — latence visée < 2 s sur ≤ 12 s.
    Chaîne : atempo → FX (ordre contrat) → volume (gain existant en dernier)."""
    af = []
    if speed:
        af.append(f"atempo={_g(speed)}")
    ch = fx_chain(fx or [])
    if ch:
        af.append(ch)
    if abs(gain_db) >= 0.05:
        af.append(f"volume={_g(10.0 ** (gain_db / 20.0))}")
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    if src_in > 0:
        cmd += ["-ss", str(round(src_in, 3))]
    cmd += ["-t", str(round(max(0.1, min(12.0, length)), 3)), "-i", str(src),
            "-vn"]
    if af:
        cmd += ["-af", ",".join(af)]
    cmd += ["-ar", "44100", "-ac", "2", "-f", "wav", str(out)]
    return cmd


_EBUR_I = re.compile(r"I:\s+(-?[\d.]+|nan)\s+LUFS")
_EBUR_LRA = re.compile(r"LRA:\s+(-?[\d.]+|nan)\s+LU")
_EBUR_PEAK = re.compile(r"Peak:\s+(-?[\d.]+|nan)\s+dBFS")


def parse_ebur128(stderr: str) -> dict:
    """Résumé du filtre ebur128 (stderr ffmpeg) → {lufs_i, tp, lra}
    (None par champ si absent/nan). Prend la DERNIÈRE occurrence (Summary)."""
    def _last(rx):
        m = rx.findall(stderr or "")
        if not m or m[-1] == "nan":
            return None
        try:
            return float(m[-1])
        except ValueError:
            return None
    return {"lufs_i": _last(_EBUR_I), "tp": _last(_EBUR_PEAK),
            "lra": _last(_EBUR_LRA)}
