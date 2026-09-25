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
import math
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
# L6 : `dehum` et `eq6` insérés, ordre RELATIF des dix types d'avant inchangé
# (projets existants : commande identique). Le ronflement est ôté avant le
# débruiteur (le bruit est appris sur une source sans ronflement), l'EQ 6
# bandes vient APRÈS lui (il ne fausse pas le plancher `nf`).
_FX_ORDER = ("filter", "dehum", "eq3", "denoise", "eq6", "deesser", "compressor",
             "distortion", "echo", "reverb", "stereo", "normalize")

# Débruiteur (mesures L6 du 25/09, ffmpeg 8.1.1 = 9.0.1) : afftdn retarde le
# son de 1200 échantillons à 48 kHz et garde la longueur (les 25 dernières ms
# du clip étaient perdues) → fréquence imposée, apad devant, atrim derrière.
DN_RATE = 48000          # fréquence imposée avant afftdn
DN_DELAY = 1200          # retard d'afftdn à 48 kHz (mesuré)
LEARN_MAX = 1.0          # secondes de préfixe appris au plus
LEARN_MIN = 0.2          # plage d'apprentissage minimale (s)

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
    # nf 0 = automatique (omis) ; learn_in/out en secondes de SOURCE.
    "denoise": {"amount": (0.0, 97.0, 12.0), "nf": (-80.0, 0.0, 0.0),
                "learn_in": (0.0, 86400.0, 0.0),
                "learn_out": (0.0, 86400.0, 0.0)},
    "deesser": {"intensity": (0.0, 100.0, 50.0)},
    "normalize": {"target_lufs": (-30.0, -10.0, -16.0)},
    # L6 D-23 : passe-haut optionnel (0 = coupé), plateau grave, quatre
    # cloches, plateau aigu ; bornes serrées (g hors bornes ou f < 0 FONT
    # ÉCHOUER le rendu ffmpeg — mesuré).
    "eq6": {"hp_hz": (0.0, 300.0, 0.0),
            "ls_f": (30.0, 500.0, 100.0), "ls_g": (-12.0, 12.0, 0.0),
            "p1_f": (40.0, 16000.0, 250.0), "p1_g": (-12.0, 12.0, 0.0),
            "p1_q": (0.3, 8.0, 1.0),
            "p2_f": (40.0, 16000.0, 800.0), "p2_g": (-12.0, 12.0, 0.0),
            "p2_q": (0.3, 8.0, 1.0),
            "p3_f": (40.0, 16000.0, 2500.0), "p3_g": (-12.0, 12.0, 0.0),
            "p3_q": (0.3, 8.0, 1.0),
            "p4_f": (40.0, 16000.0, 6000.0), "p4_g": (-12.0, 12.0, 0.0),
            "p4_q": (0.3, 8.0, 1.0),
            "hs_f": (1000.0, 16000.0, 8000.0), "hs_g": (-12.0, 12.0, 0.0)},
    # L6 D-25 : fondamentale 50|60 (arrondie par le constructeur), crans aux
    # harmoniques, dosage linéaire en amplitude.
    "dehum": {"base": (50.0, 60.0, 50.0), "harmonics": (1.0, 6.0, 4.0),
              "amount": (0.0, 100.0, 100.0)},
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


def _fx_eq6(p: dict) -> str:
    """Égaliseur 6 bandes (biquads natifs : exacts, retard 0, identité à g=0).
    Seules les bandes |g| ≥ 0,05 sont émises ; tout neutre → "". Ouvert par
    `aformat=sample_fmts=fltp` : sur une source s16 un equalizer en dernier
    maillon écrête (mesuré)."""
    bands = []
    if p["hp_hz"] >= 20.0:                      # < 20 Hz = coupé
        bands.append(f"highpass=f={_g(p['hp_hz'])}")
    if abs(p["ls_g"]) >= 0.05:
        bands.append(f"lowshelf=f={_g(p['ls_f'])}:g={_g(p['ls_g'])}")
    for k in (1, 2, 3, 4):
        g = p[f"p{k}_g"]
        if abs(g) >= 0.05:
            bands.append(f"equalizer=f={_g(p[f'p{k}_f'])}:t=q"
                         f":w={_g(p[f'p{k}_q'])}:g={_g(g)}")
    if abs(p["hs_g"]) >= 0.05:
        bands.append(f"highshelf=f={_g(p['hs_f'])}:g={_g(p['hs_g'])}")
    return ",".join(["aformat=sample_fmts=fltp"] + bands) if bands else ""


def _fx_dehum(p: dict) -> str:
    """Anti-ronflement : cascade bandreject Q=10 aux harmoniques de la
    fondamentale (tient ±0,3 Hz de dérive ; voix −0,2 dB mesuré), `m` =
    dosage linéaire. anequalizer écarté (chaque canal à déclarer)."""
    if p["amount"] < 0.5:
        return ""
    base = 60 if p["base"] >= 55 else 50
    n = max(1, min(6, int(round(p["harmonics"]))))
    m = _g(p["amount"] / 100.0)
    return ",".join(f"bandreject=f={base * k}:width_type=q:w=10:m={m}"
                    for k in range(1, n + 1))


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


def pan_gains(pan: float) -> tuple[float, float]:
    """Loi de balance à PUISSANCE CONSTANTE normalisée (L6, mesurée) :
    θ = (p+1)·π/4, gL = min(1, √2·cos θ), gR = min(1, √2·sin θ), p ∈ [−1, 1]
    → 0 dB au centre, −5,33 dB à ±0,5, un canal éteint à ±1 (comme la
    `StereoPanner` WebAudio de l'audition du rack)."""
    p = max(-1.0, min(1.0, float(pan)))
    th = (p + 1.0) * math.pi / 4.0
    gl = min(1.0, math.sqrt(2.0) * math.cos(th))
    gr = min(1.0, math.sqrt(2.0) * math.sin(th))
    return max(0.0, gl), max(0.0, gr)


def _fx_stereo(p: dict) -> str:
    # Largeur d'abord, balance EN SORTIE ensuite (comme balance_out de
    # stereotools avant L6). `stereotools=balance_out` (loi LINÉAIRE,
    # −6,02 dB à ±0,5) remplacé par `pan` à puissance constante ; l'upmix
    # mono → stéréo de `aformat` coûte −3 dB/canal, déjà payé en aval de la
    # chaîne par clip (aformat=…stereo) : aucune perte neuve.
    # Revue T1 (I-2, mesuré 25/09/2026) : `stereotools=slev` REFUSE < 0,015625
    # sur les deux binaires (le curseur descend à 0 : rendu en échec) et `_g`
    # arrondit 0,015625 à 0,0156, encore hors bornes. Sous 1,6 % : vraie somme
    # mono par `pan` (même sortie que slev → 0 : −17,89 dB sur les deux canaux).
    parts = []
    if p["width"] < 1.6:                        # mono pur
        parts.append("aformat=channel_layouts=stereo,"
                     "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1")
    elif p["width"] < 99.5:                     # mono-mix partiel
        parts.append(f"stereotools=slev={_g(p['width'] / 100.0)}")
    if p["width"] > 100.5:                      # élargissement
        t = max(0.0, min(1.0, (p["width"] - 100.0) / 100.0))
        parts.append(f"stereowiden=delay=15:feedback={_g(0.2 + 0.25 * t)}"
                     f":crossfeed={_g(0.15 + 0.35 * t)}:drymix=0.85")
    if abs(p["pan"]) >= 0.5:
        gl, gr = pan_gains(p["pan"] / 100.0)
        parts.append(f"aformat=channel_layouts=stereo,"
                     f"pan=stereo|c0={_g(gl)}*c0|c1={_g(gr)}*c1")
    return ",".join(parts)


def _fx_compressor(p: dict) -> str:
    lin = 10.0 ** (p["threshold_db"] / 20.0)
    return (f"acompressor=threshold={_g(max(0.001, lin))}"
            f":ratio={_g(p['ratio'])}:attack={_g(p['attack_ms'])}"
            f":release={_g(p['release_ms'])}")


def _fx_denoise(p: dict, uid: str = "", prefix_s: float = 0.0) -> str:
    """Débruiteur afftdn, retard COMPENSÉ (1200 éch. à 48 kHz, mesuré) et
    trames remises à 4096 (afftdn sort des trames de 600 : les biquads en
    aval coûtaient ×2,3 ; `p=0` sinon la durée s'allonge).
    `nf` 0 = automatique (omis), sinon borné à [−80, −20] (bornes d'afftdn,
    qui REFUSE hors bornes). prefix_s > 0 : l'appelant a concaténé en tête
    prefix_s secondes de bruit seul ; il est appris par asendcmd sur une
    instance NOMMÉE `afftdn@dn<uid>` (un asendcmd vise toutes les instances
    du nom dans le graphe) puis retiré ici. `tn` jamais posé (il écrase le
    profil appris — mesuré)."""
    pre = int(round(prefix_s * DN_RATE)) if prefix_s > 0 else 0
    # Revue T1 (M-2) : uid filtré avant d'entrer dans un nom d'instance ; un
    # uid VIDE avec préfixe est REFUSÉ (un `afftdn@dn` partagé ferait piloter
    # l'apprentissage d'un clip par l'asendcmd d'un autre).
    uid = re.sub(r"[^0-9A-Za-z_]", "", str(uid or ""))
    if pre and p["amount"] >= 0.5 and not uid:
        raise ValueError("denoise appris : uid requis (unique dans le graphe)")
    if p["amount"] < 0.5:
        # module sans effet ; un préfixe éventuel doit quand même partir
        return (f"aresample={DN_RATE},atrim=start_sample={pre},"
                f"asetpts=PTS-STARTPTS" if pre else "")
    opts = f"nr={_g(p['amount'])}"
    nf = p.get("nf", 0.0)
    if nf <= -0.5:
        opts += f":nf={_g(max(-80.0, min(-20.0, nf)))}"
    parts = [f"aresample={DN_RATE}"]
    name = "afftdn"
    if pre:
        name = f"afftdn@dn{uid}"
        parts.append(f"asendcmd=c='0.0 {name} sn start;"
                     f"{_g(max(0.0, prefix_s - 0.05))} {name} sn stop'")
    parts += [f"apad=pad_len={DN_DELAY}", f"{name}={opts}",
              f"atrim=start_sample={DN_DELAY + pre}", "asetpts=PTS-STARTPTS",
              "asetnsamples=n=4096:p=0"]
    return ",".join(parts)


def learn_of(fx: list[dict]) -> tuple[float, float] | None:
    """(a, a+L) en secondes de SOURCE si le PREMIER denoise trouvé porte
    learn_out − learn_in ≥ LEARN_MIN ; L = min(learn_out − learn_in,
    LEARN_MAX), arrondi 1e-3. None s'il est coupé (amount < 0,5), si sa
    plage est trop courte, ou sans denoise (l'appelant ne préfixe pas) ;
    un denoise suivant n'est jamais consulté."""
    for e in fx or ():
        if not isinstance(e, dict) or e.get("type") != "denoise":
            continue
        p = e.get("params") or {}
        try:
            amount = float(p.get("amount", 12.0))
            a = float(p.get("learn_in", 0.0))
            b = float(p.get("learn_out", 0.0))
        except (TypeError, ValueError):
            return None
        if amount < 0.5 or not (math.isfinite(a) and math.isfinite(b)):
            return None
        if b - a < LEARN_MIN - 1e-9:
            return None
        a = round(max(0.0, a), 3)
        return a, round(a + min(b - a, LEARN_MAX), 3)
    return None


def nf_of(rms_db: float) -> int:
    """Plancher de bruit d'afftdn tiré du RMS d'une plage de bruit seul :
    clamp(round(rms_db + 10), −80, −20) (règle validée sur trois niveaux ;
    le « Noise floor dB » d'astats n'est PAS utilisable). Non fini →
    ValueError (plage muette)."""
    v = float(rms_db)
    if not math.isfinite(v):
        raise ValueError(f"RMS non fini : {rms_db!r}")
    return int(max(-80, min(-20, round(v + 10.0))))


def _fx_deesser(p: dict) -> str:
    return (f"deesser=i={_g(p['intensity'] / 100.0)}"
            if p["intensity"] >= 0.5 else "")


def _fx_normalize(p: dict) -> str:
    return f"loudnorm=I={_g(p['target_lufs'])}:TP=-1.5:LRA=11"


_FX_BUILD = {"filter": _fx_filter, "eq3": _fx_eq3, "echo": _fx_echo,
             "reverb": _fx_reverb, "distortion": _fx_distortion,
             "stereo": _fx_stereo, "compressor": _fx_compressor,
             "denoise": _fx_denoise, "deesser": _fx_deesser,
             "normalize": _fx_normalize, "eq6": _fx_eq6,
             "dehum": _fx_dehum}


def fx_chain(fx: list[dict], *, uid: str = "", prefix_s: float = 0.0) -> str:
    """Liste normalisée (sanitize_fx) → fragment de filtergraph ffmpeg
    (« aecho=…,acompressor=… »), ordre de chaîne fixe, "" si vide/no-op.

    prefix_s > 0 : l'appelant a concaténé en tête un préfixe de bruit de
    prefix_s secondes (plage learn_of) ; le PREMIER denoise l'apprend
    (afftdn@dn<uid>, uid UNIQUE dans le graphe) puis le retire — les filtres
    placés avant lui (filter, dehum, eq3) le traversent comme le clip. Sans
    denoise, prefix_s est ignoré (learn_of rend alors None : ne pas
    préfixer)."""
    ordered = sorted((e for e in fx or ()),
                     key=lambda e: _FX_ORDER.index(e["type"]))
    frags = []
    pending = prefix_s if prefix_s and prefix_s > 0 else 0.0
    for e in ordered:
        if e["type"] == "denoise":
            f = _fx_denoise(e["params"], uid, pending)
            pending = 0.0                       # un seul apprentissage
        else:
            f = _FX_BUILD[e["type"]](e["params"])
        if f:
            frags.append(f)
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
                           speed: float = 0.0, fx: list[dict] | None = None,
                           src_dur: float | None = None) -> list[str]:
    """Extrait traité → WAV 44.1 k stéréo. -ss/-t AVANT -i (seek démuxeur,
    aucun décodage vidéo : -vn) — latence visée < 2 s sur ≤ 12 s.
    Chaîne : atempo → FX (ordre contrat) → volume (gain existant en dernier).

    L6 : si learn_of(fx) rend (a, b), DEUX entrées de la même source
    (-ss a -t L puis -ss src_in -t length), le préfixe de bruit concaténé
    devant l'extrait (jamais d'atempo sur lui) traverse les filtres amont du
    vocabulaire et est appris puis retiré par le denoise. Sans apprentissage,
    commande inchangée octet pour octet.
    Revue T1 (I-1) : le préfixe est forcé à P = round(L·48000) échantillons
    exacts (une plage en partie hors de la source coupait le début de
    l'extrait) ; une plage qui COMMENCE au-delà de la fin de la source
    (`src_dur`, sondée par ffprobe si absent ; 0 = inconnue) n'est pas
    préfixée — MESURÉ : l'entrée vide fait échouer tout le graphe (rc 183)."""
    lrn = learn_of(fx or [])
    if lrn:
        dur = _probe_duration(src) if src_dur is None else float(src_dur or 0.0)
        if dur > 0 and lrn[0] >= dur - LEARN_MIN:
            lrn = None
    if lrn:
        return _build_audition_learned(src, out, lrn, src_in=src_in,
                                       length=length, gain_db=gain_db,
                                       speed=speed, fx=fx or [])
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


def _build_audition_learned(src: Path, out: Path, lrn: tuple[float, float], *,
                            src_in: float, length: float, gain_db: float,
                            speed: float, fx: list[dict]) -> list[str]:
    a, b = lrn
    L = round(b - a, 3)
    clip = [f"[1:a]asetpts=PTS-STARTPTS"]
    if speed:
        clip.append(f"atempo={_g(speed)}")
    clip.append(f"aresample={DN_RATE}[c]")
    tail = [f"[p][c]concat=n=2:v=0:a=1"]
    ch = fx_chain(fx, uid="a", prefix_s=L)
    if ch:
        tail.append(ch)
    if abs(gain_db) >= 0.05:
        tail.append(f"volume={_g(10.0 ** (gain_db / 20.0))}")
    P = int(round(L * DN_RATE))
    fc = (f"[0:a]asetpts=PTS-STARTPTS,aresample={DN_RATE},"
          f"atrim=end_sample={P},apad=whole_len={P}[p];"
          + ",".join(clip) + ";" + ",".join(tail) + "[o]")
    cmd = ["ffmpeg", "-y", "-hide_banner"]
    if a > 0:
        cmd += ["-ss", str(round(a, 3))]
    cmd += ["-t", str(L), "-i", str(src)]
    if src_in > 0:
        cmd += ["-ss", str(round(src_in, 3))]
    cmd += ["-t", str(round(max(0.1, min(12.0, length)), 3)), "-i", str(src),
            "-filter_complex", fc, "-map", "[o]", "-vn",
            "-ar", "44100", "-ac", "2", "-f", "wav", str(out)]
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
