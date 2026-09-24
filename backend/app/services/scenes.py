"""D-42 (L7-B, 24/09/2026) — les CHANGEMENTS DE PLAN d'un extrait de source.

`detect(path, src_in, dur, threshold=10.0)` lance ffmpeg sur l'extrait
[src_in, src_in + dur[ de `path` avec le filtre `scdet` et rend les instants de
coupe en secondes RELATIVES au début lu (triés, dédoublonnés à une image,
bornés à 200). Le Montage s'en sert pour « Découper aux changements de plan »
(clic droit sur un clip vidéo) : l'écran convertit ces instants en temps de
timeline (`dzmCutAt`, montage.js).

CE QUE ffmpeg 8.1.1 IMPRIME RÉELLEMENT — mesuré le 24/09/2026 (essentials
build, Windows 11) sur deux plans concaténés (testsrc2 2 s puis testsrc 2 s,
64×64, 30 i/s) :

* `scdet=threshold=10,metadata=print:file=-` (la forme du plan) sort TROIS
  lignes PAR IMAGE sur stdout — `frame:N pts:… pts_time:T`, puis
  `lavfi.scd.mafd=…`, `lavfi.scd.score=…` — et une quatrième,
  `lavfi.scd.time=T`, sur la seule image coupée (score 31,05 à 2,0 s ; les
  autres ≤ 0,77). 90 images → 272 lignes : 100 fois trop pour une heure de
  film. En parallèle, scdet journalise la coupe sur stderr
  (`lavfi.scd.score: 31.050, lavfi.scd.time: 2`), au niveau info.
* `metadata=mode=print:key=lavfi.scd.time:file=-` — la forme RETENUE — ne sort
  QUE les images qui portent la clé : une paire de lignes par coupe,
  `frame:60   pts:30720   pts_time:2` puis `lavfi.scd.time=2`. Le score
  n'est pas imprimé dans ce mode (seule la clé demandée l'est).
* `-ss 0.5 -t 3` AVANT `-i` : la coupe sort à `pts_time:1.5` — les temps
  sont relatifs au début lu. `setpts=PTS-STARTPTS` en tête du graphe le
  garantit pour tout démuxeur (mesuré identique ici) ; avec `-ss 1.234`, la
  première image décodée est la 38e (1,2667 s) et la coupe sort à 0,7333 au
  lieu de 0,766 : l'écart vaut moins d'une image, c'est la précision du
  découpage à l'image.
* seuil 40 (au-dessus de 31,05) : aucune ligne, rc 0 ; source grise
  uniforme : score 0 partout, aucune ligne, rc 0.

`parse` ne lit que les lignes `lavfi.scd.time=` (elles suffisent : leur valeur
EST le `pts_time` de la ligne `frame:` qui précède — mesuré) ; elle tolère
donc aussi la sortie bavarde sans `key=`. Deux coupes à une image l'une de
l'autre (écart ≤ 1/30 s + 1 ms : les valeurs imprimées sont arrondies à six
chiffres, 0.733333 → 0.766667 fait 0,033334) sont UNE transition : la
première est gardée. `t ≤ 0` n'est pas une coupe (le début du clip).

Cache : `outputs/montage_cache/<sha(chemin résolu, mtime_ns, srcIn, dur,
seuil)>_scenes.json` — celui de `montage_media` (même dossier, même écriture
atomique `_tmp_de` + `os.replace`). Une source modifiée change de clé. Le
cache n'est pas borné en nombre : un fichier de quelques octets par analyse
DEMANDÉE (clic droit), jamais par chargement d'écran. Un échec n'est jamais
mis en cache.

Échecs : source illisible ou ffmpeg en erreur / absent / hors délai →
`montage_media.MediaError` (message lisible), que la route traduit en 415 par
`_media_http`. Timeout PROPORTIONNEL : 2 × durée + 60 s, plancher 120 s
(`timeout_de`) — scdet décode chaque image.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from app.services import montage_media as _MM

MAX_COUPES = 200
_UNE_IMAGE = 1 / 30
_RE_TIME = re.compile(r"^lavfi\.scd\.time=([-+0-9.eE]+)\s*$")


def timeout_de(dur) -> int:
    """Délai d'attente de l'analyse : 2 × durée + 60 s, plancher 120 s."""
    try:
        d = float(dur)
    except (TypeError, ValueError):
        return 120
    if not math.isfinite(d) or d <= 0:
        return 120
    return max(120, int(d * 2) + 60)


def parse(texte) -> list:
    """Les instants de coupe de la sortie `metadata=print` de scdet : triés,
    arrondis au millième, dédoublonnés à une image, `t > 0`, ≤ 200."""
    vus = []
    for ligne in str(texte or "").splitlines():
        m = _RE_TIME.match(ligne.strip())
        if not m:
            continue
        try:
            t = float(m.group(1))
        except ValueError:
            continue
        if math.isfinite(t) and t > 0:
            vus.append(t)
    vus.sort()
    out = []
    for t in vus:
        if out and t - out[-1] <= _UNE_IMAGE + 1e-3:
            continue
        out.append(t)
        if len(out) >= MAX_COUPES:
            break
    return [round(t, 3) for t in out]


def _ffmpeg(cmd: list, timeout: int):
    """Le lanceur : `montage_media._run` (tout échec d'exécution → MediaError).
    Point unique que le banc remplace par un espion."""
    return _MM._run(cmd, timeout=timeout, quoi="l'analyse des changements de plan")


def _cle(path: Path, src_in: float, dur: float, threshold: float) -> Path:
    try:
        mtime = path.stat().st_mtime_ns
    except OSError as e:
        raise _MM.MediaError("source illisible : %s" % path.name) from e
    brut = "%s|%d|%.3f|%.3f|%.3f|scenes" % (path.resolve(), mtime, src_in, dur, threshold)
    key = hashlib.sha1(brut.encode("utf-8")).hexdigest()[:20]
    return _MM._cache_dir() / ("%s_scenes.json" % key)


def detect(path, src_in, dur, threshold: float = 10.0) -> list:
    """Les coupes de [src_in, src_in + dur[ de `path`, en secondes relatives
    au début lu. Cache disque (voir l'en-tête) ; `MediaError` sur tout échec."""
    p = Path(path)
    si, du, th = max(0.0, float(src_in)), float(dur), float(threshold)
    out = _cle(p, si, du, th)
    if out.exists():
        try:
            v = json.loads(out.read_text(encoding="utf-8"))
            if isinstance(v, list):
                return [float(t) for t in v]
        except (OSError, ValueError, TypeError):
            pass                        # cache illisible : on refait l'analyse
    r = _ffmpeg(["ffmpeg", "-hide_banner", "-nostats", "-v", "error",
                 "-ss", "%.3f" % si, "-t", "%.3f" % du, "-i", str(p),
                 "-an", "-sn", "-dn", "-vf",
                 "setpts=PTS-STARTPTS,scdet=threshold=%g,"
                 "metadata=mode=print:key=lavfi.scd.time:file=-" % th,
                 "-f", "null", "-"], timeout_de(du))
    if r.returncode != 0:
        raise _MM.MediaError("analyse des changements de plan impossible pour « %s » — %s"
                             % (p.name, _MM._lignes_utiles(r.stderr)))
    times = parse((r.stdout or b"").decode("utf-8", errors="replace"))
    tmp = _MM._tmp_de(out)
    try:
        tmp.write_text(json.dumps(times), encoding="utf-8")
        _MM._ecrire(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return times
