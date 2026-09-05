# -*- coding: utf-8 -*-
"""Précalculs du Montage : pics d'onde, filmstrip, proxy 480p.

Tâche 8 / P7 (« lecture fluide — mesurer, précalculer »), MOITIÉ BACKEND. Ce
module ne sert AUCUNE route et ne connaît AUCUNE règle du Montage : il
calcule, met en cache, et rend un chemin ou un dict. Les décisions de
vocabulaire (ce qu'est une source, ce qui est une vidéo, qui a le droit
d'appeler) vivent dans `montage_service`, où elles étaient déjà.

Le cache vit sous ``outputs/montage_cache/<sha(chemin, mtime, genre)>_<genre>.*``
— un dossier NEUF, séparé d'``outputs/videos/`` où vivent les rendus.
MESURÉ (``grep -rn "outputs_path" backend/app --include=*.py``, 05/09/2026) :
aucune route n'énumère ``outputs/`` récursivement ; les deux seuls parcours
(routes.py l. 257 et 274) cherchent un fichier PAR NOM à la racine
d'``outputs/`` et d'``images/``, donc jamais dans un sous-dossier. Rien de ce
qui est écrit ici n'est donc visible de la Bibliothèque, du sélecteur
d'assets ni d'un `src` de Montage.

CE QU'ON PEUT PERDRE EN PURGEANT CE DOSSIER (faute n°4 du chantier — « un
geste destructif sans retour ») : RIEN qui ne se recalcule. Tout fichier de
ce cache est une fonction pure de (contenu de la source, genre, paramètres) ;
la clé porte le ``st_mtime_ns`` de la source, donc une source modifiée obtient
une nouvelle clé au lieu d'un résultat périmé. Un ``rm -rf montage_cache``
coûte le temps de recalcul, jamais une donnée. Conséquence assumée : les
anciennes clés d'un fichier modifié ne sont JAMAIS effacées — ce cache ne se
purge pas tout seul, et c'est dit ici plutôt que promis ailleurs.

ÉCRITURE ATOMIQUE, et ce n'est pas de la coquetterie : ``ffmpeg -y`` TRONQUE
sa sortie avant de la réécrire. Un second appel pour la même source pendant
qu'un ``FileResponse`` sert déjà le fichier servirait des octets vides. On
écrit donc dans un temporaire à nom unique puis ``os.replace`` — le même
raisonnement, et le même remède, que `forge3d.py` (l. 3842) a déjà écrits
pour un `copyfile`.

stdlib pure : pas de numpy, et pas de PIL non plus — le décodage des pics
tient dans `array('b')`, et les images sont écrites par ffmpeg, jamais lues
ici (c'est le banc qui les ouvre, avec PIL). La conséquence de « sans
numpy » est mesurée et dite dans `peaks`.
"""
from __future__ import annotations

import array
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings


class MediaError(RuntimeError):
    """Échec de précalcul PORTEUR D'UN MESSAGE lisible par l'utilisateur.

    Tout ce qui peut échouer ici (ffmpeg absent, source illisible, source sans
    flux audio, sous-processus en erreur) sort par CE type-là, jamais par un
    `CalledProcessError` ni un `FileNotFoundError` nu : les routes le
    traduisent en 4xx nommé, et le banc peut le distinguer d'un plantage."""


# Le genre (`kind`) porte ses paramètres dans son nom — « peaks120 »,
# « strip6x78x44 », « proxy » — pour que deux réglages ne se marchent pas
# dessus dans le cache. L'EXTENSION se lit sur la FAMILLE, c'est-à-dire le
# préfixe alphabétique, et sur rien d'autre.
# LE PLAN écrivait `{"proxy": ".mp4"}.get(kind.rstrip("0123456789"), ".json"
# if kind.startswith("peaks") else ".jpg")`. MESURÉ avant d'être recopié
# (scratchpad/mesure_plan.py, section [1]) : `"strip12x78x44"
# .rstrip("0123456789")` rend `"strip12x78x"` — le `x` final arrête le
# `rstrip` — et non `"strip"`. L'extension `.jpg` sortait donc du REPLI du
# `.get`, par accident : elle aurait été identique pour n'importe quel genre
# inconnu, y compris une faute de frappe. Les trois familles recevaient bien
# leur extension (peaks → .json, proxy → .mp4, strip → .jpg, vérifié sur sept
# valeurs), mais une seule des trois par le chemin prévu. On lit donc la
# famille explicitement, et un genre inconnu LÈVE au lieu de devenir un .jpg.
_EXT = {"peaks": ".json", "strip": ".jpg", "proxy": ".mp4"}
_RE_FAMILLE = re.compile(r"^[a-z]+")

# 2 000 échantillons par seconde : 300 cases pour 10 minutes de musique font
# encore 4 000 échantillons par case. C'est un DÉFAUT, pas une mesure.
_RATE = 2000

# Bornes des paramètres CLIENTS. Ce ne sont pas des mesures : ce sont des
# bornes, posées pour la même raison que le `[:60]` du libellé au pré-vol de
# `montage_render` (P8-bis) — `bins`, `n`, `w`, `h` arrivent par la barre
# d'adresse. Sans elles, `bins=10_000_000` construit une liste de dix
# millions de flottants et `n=999,w=320` demande à ffmpeg une image de
# 319 680 pixels de large.
_BINS_MIN, _BINS_MAX = 8, 2000
_N_MAX, _WH_MIN, _WH_MAX = 60, 8, 320


def _famille(kind: str) -> str:
    m = _RE_FAMILLE.match(str(kind or ""))
    return m.group(0) if m else ""


def _cache_dir() -> Path:
    d = settings.outputs_path / "montage_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(src, kind: str) -> Path:
    """Le chemin de cache de `src` pour ce `kind`. Lève `MediaError` si la
    source est illisible (`stat` fait partie de la CLÉ) ou si la famille du
    genre est inconnue — un genre inconnu ne doit pas se transformer en un
    `.jpg` silencieux."""
    ext = _EXT.get(_famille(kind))
    if ext is None:
        raise MediaError("genre de précalcul inconnu : %r" % (kind,))
    p = Path(src)
    try:
        mtime = p.stat().st_mtime_ns
    except OSError as e:
        raise MediaError("source illisible : %s" % p.name) from e
    key = hashlib.sha1(
        ("%s|%d|%s" % (p.resolve(), mtime, kind)).encode("utf-8")).hexdigest()[:20]
    return _cache_dir() / ("%s_%s%s" % (key, kind, ext))


def _dur(src) -> float:
    """Durée ffprobe de `src`, ou 0.0.

    RÉUTILISE `montage_service._probe_duration` — l'import est TARDIF et il le
    faut : `montage_service` importe ce module pour ses routes, et un import
    de module à module dans les deux sens serait un cycle. La copie locale que
    le plan proposait aurait divergé à la première correction, exactement
    l'argument que P9 a déjà écrit pour `/media-rules`."""
    from app.services.montage_service import _probe_duration
    return _probe_duration(Path(src))


def _lignes_utiles(stderr: bytes) -> str:
    """Le diagnostic ffmpeg, par le MÊME lecteur que le rendu.

    RÉUTILISE `montage_service._ffmpeg_lignes_utiles` (neuf motifs, mesurés en
    P8/P8-bis) : sans motif reconnu on rend la fin brute, comme
    `_run_ffmpeg`."""
    from app.services.montage_service import _ffmpeg_lignes_utiles
    txt = (stderr or b"").decode("utf-8", errors="replace")
    lignes = _ffmpeg_lignes_utiles(txt)
    return " | ".join(lignes) if lignes else txt[-400:].strip()


def _run(cmd: list, *, timeout: int, quoi: str):
    """`subprocess.run` dont TOUT échec d'exécution sort en `MediaError`.

    `ffmpeg` absent lève `FileNotFoundError` (MESURÉ : `[WinError 2]`), une
    source sur un disque disparu lève `OSError`, un encodage sans fin lève
    `TimeoutExpired` — trois exceptions nues qui, non attrapées, sortent en
    500 sans message et tuent un banc au lieu de le faire rougir."""
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise MediaError(
            "ffmpeg est introuvable : %s ne peut pas être précalculé." % quoi) from e
    except subprocess.TimeoutExpired as e:
        raise MediaError("%s a dépassé %d s." % (quoi, timeout)) from e
    except OSError as e:
        raise MediaError("%s a échoué : %s" % (quoi, e)) from e


def _ecrire(tmp: Path, out: Path) -> Path:
    """`tmp` devient `out` d'un seul coup. Voir l'écriture atomique en tête."""
    os.replace(tmp, out)
    return out


def _tmp_de(out: Path) -> Path:
    """Un temporaire unique QUI GARDE L'EXTENSION FINALE.

    MESURÉ, et ce n'est pas un détail de style : avec un nom finissant par
    « .tmp », ffmpeg n'a plus de muxer à déduire et rend « Error opening
    output file … | Error opening output files: Invalid argument » — le
    filmstrip comme l'aperçu échouaient à 100 %. L'extension reste donc en
    dernier, l'unicité s'intercale avant."""
    return out.with_name("%s.%s.tmp%s" % (out.stem, uuid4().hex[:8], out.suffix))


def _bins(bins) -> int:
    try:
        b = int(bins)
    except (TypeError, ValueError):
        b = 300
    return max(_BINS_MIN, min(_BINS_MAX, b))


def peaks(src, bins: int = 300, rate: int = _RATE) -> dict:
    """Enveloppe d'onde de `src` : `{peaks: [0..1] × bins, dur, bins}`.

    Décodage ffmpeg en `s8` mono `rate` Hz, crête absolue par case, normalisée
    par la crête GLOBALE du morceau (donc relative : un extrait discret
    remplit sa bande autant qu'un extrait fort — c'est ce qu'on veut d'une
    forme d'onde de montage, pas un vumètre).

    TROIS ÉCARTS AU CODE DU PLAN, chacun mesuré (scratchpad/mesure_plan.py,
    mesure2.py, mesure3.py — ffmpeg 8.1.1-essentials_build, Windows 11 26200).

    1. LA NORMALISATION. Le plan écrivait `mx = max(pk) or 1` puis
       `round(v / mx, 3) if mx > 1 else 0.0`. MESURÉ : un sinus à −52 dB
       décode en `s8` avec une crête de 1, donc `mx == 1`, donc DES ZÉROS
       PARTOUT — le même dessin, au bit près, que du silence numérique. Le
       balayage du seuil donne `max|x| = 2` à −40 et −42 dBFS, et `1` à −44,
       −46, −50 et −60 dBFS (le `1` est un plancher de dither, il ne descend
       jamais à 0) : TOUT ce qui est sous ≈ −44 dBFS était rendu muet. Ici,
       seule la vraie crête nulle rend des zéros — `anullsrc` décode
       effectivement en `s8` tout à zéro (MESURÉ : 4 000 octets, une seule
       valeur distincte, 0), donc le silence reste distinguable.
    2. LA RÉPARTITION DES CASES. Le plan écrivait `step = max(1, n // bins)`,
       ce qui laisse les cases de queue VIDES quand la source est plus courte
       que `bins` échantillons. MESURÉ sur un fichier de 0,05 s (100
       échantillons à 2 000 Hz, 300 cases) : 97 cases porteuses et 203 cases
       à 0,0 — deux tiers de la forme d'onde en silence INVENTÉ. Les bornes
       sont donc proportionnelles, et la borne haute forcée d'au moins un
       échantillon : la même mesure rend 300 cases sur 300.
    3. AUCUN FLUX AUDIO ≠ SILENCE. Le plan faisait `n = max(1, len(a))`, donc
       une source muette rendait `dur = 0.001` et une onde plate. MESURÉ : un
       PNG comme un `.mp4` sans piste audio rendent 0 octet et `rc = -22`.
       Rendre une onde plate serait AFFIRMER un silence qu'on n'a pas mesuré ;
       on lève, et la route répond 415 en le nommant.

    LIMITE ASSUMÉE du `s8` (« sans numpy ») : 8 bits par échantillon, donc une
    crête sous ≈ −44 dBFS est indiscernable de la suivante. C'est le prix du
    décodage stdlib, et c'est mesuré ci-dessus, pas supposé."""
    bins = _bins(bins)
    out = _cache_path(src, "peaks%d" % bins)
    if out.exists():
        try:
            cache = json.loads(out.read_text(encoding="utf-8"))
            if isinstance(cache, dict) and isinstance(cache.get("peaks"), list):
                return cache
        except (OSError, ValueError):
            pass   # cache illisible : on recalcule, jamais on ne lève
    r = _run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1",
              "-ar", str(rate), "-f", "s8", "-"],
             timeout=120, quoi="la lecture de l'onde")
    a = array.array("b")
    a.frombytes(r.stdout)
    n = len(a)
    if n == 0:
        raise MediaError(
            "aucun flux audio décodable dans « %s » — %s"
            % (Path(src).name, _lignes_utiles(r.stderr)))
    pk = []
    for i in range(bins):
        d0 = (i * n) // bins
        d1 = max(((i + 1) * n) // bins, d0 + 1)
        seg = a[d0:d1]
        # `max(seg)` / `-min(seg)` et non `max(abs(int(v)) for v in seg)` :
        # la seconde forme fait deux appels Python PAR ÉCHANTILLON. MESURÉ
        # (scratchpad/mesure_boucle.py, array de 1 200 000 octets aléatoires
        # = 10 min à 2 000 Hz, 300 cases, 3 tours, médiane, même python que
        # les bancs) : 49,0 ms contre 121,1 ms, pour des sorties IDENTIQUES
        # (l'égalité des deux listes est vérifiée par le script). Le gain est
        # de 72 ms sur le pire cas plausible ; ce n'est pas énorme, c'est
        # gratuit, et c'est mesuré plutôt que supposé.
        pk.append(max(max(seg, default=0), -min(seg, default=0)))
    mx = max(pk)
    data = {"peaks": [round(v / mx, 3) for v in pk] if mx else [0.0] * bins,
            "dur": round(n / float(rate), 3), "bins": bins}
    if r.returncode != 0:
        # Des octets sont sortis, mais ffmpeg s'est plaint : on RÉPOND (une
        # onde partielle vaut mieux qu'une bande vide) et on NE FIGE PAS.
        # La clé de cache ne porte que le `mtime` de la source : une entrée
        # écrite ici resterait servie même après réparation du décodeur.
        logger.warning(f"montage_media: onde partielle (rc={r.returncode}) "
                       f"pour {Path(src).name} — non mise en cache")
        return data
    tmp = _tmp_de(out)
    try:
        tmp.write_text(json.dumps(data), encoding="utf-8")
        _ecrire(tmp, out)
    except OSError as e:
        logger.warning(f"montage_media: cache de pics non écrit ({e})")
        try:
            tmp.unlink()
        except OSError:
            pass
    return data


def peaks_path(src, bins: int = 300) -> Path:
    """Le FICHIER de cache des pics, calculé si besoin. Une seule borne de
    `bins` pour la route et pour `peaks` — sinon la route servirait le chemin
    d'un `bins` que le calcul a déjà écrêté."""
    bins = _bins(bins)
    peaks(src, bins=bins)
    return _cache_path(src, "peaks%d" % bins)


def strip(src, n: int = 12, w: int = 78, h: int = 44) -> Path:
    """Une planche de `n` vignettes `w`×`h` côte à côte (JPEG), en cache.

    APPELÉE SUR UNE VIDÉO — c'est la route qui le garantit, et il le faut :
    MESURÉ, ffmpeg RÉUSSIT sur un PNG (rc=0, une image de 468×44 faite de six
    copies du même carton) et ÉCHOUE sur un `.wav` (« Output file does not
    contain any stream ») comme sur un `.glb` (« Invalid data found »). Sans
    garde en amont, la moitié des non-vidéos rendrait une planche muette de
    sens plutôt qu'une erreur."""
    n = max(1, min(_N_MAX, int(n)))
    w = max(_WH_MIN, min(_WH_MAX, int(w)))
    h = max(_WH_MIN, min(_WH_MAX, int(h)))
    out = _cache_path(src, "strip%dx%dx%d" % (n, w, h))
    if out.exists():
        return out
    dur = max(0.1, _dur(src))
    fps = max(0.01, n / dur)
    tmp = _tmp_de(out)
    r = _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf",
              "fps=%.4f,scale=%d:%d:force_original_aspect_ratio=increase,"
              "crop=%d:%d,tile=%dx1" % (fps, w, h, w, h, n),
              "-frames:v", "1", "-q:v", "5", str(tmp)],
             timeout=180, quoi="le filmstrip")
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise MediaError("filmstrip impossible pour « %s » — %s"
                         % (Path(src).name, _lignes_utiles(r.stderr)))
    return _ecrire(tmp, out)


def proxy_path(src) -> Path:
    """Le chemin du proxy, SANS le construire. La route `GET /proxy` s'en sert
    pour répondre 404 tant que le travail de fond n'a pas fini."""
    return _cache_path(src, "proxy")


def proxy(src) -> Path:
    """Un aperçu 480p à images clés rapprochées, en cache.

    `-g 15` est un GOP de QUINZE IMAGES — pas « une image clé toutes les
    0,5 s », comme le disait le plan. MESURÉ sur une source à 25 i/s de 4 s :
    7 images clés, à 0,000 / 0,600 / 1,200 / 1,800 / 2,400 / 3,000 / 3,600 s,
    soit 0,6 s d'intervalle. L'intervalle en SECONDES suit la cadence de la
    source (0,5 s à 30 i/s, 0,6 s à 25 i/s) ; ce qui est constant, et ce qui
    rend le balayage instantané, c'est le nombre d'images à décoder depuis la
    clé précédente : quinze, au pire.

    Durée et hauteur MESURÉES sur la même source : 4,000 s pour une source de
    4 s sans audio, 4,017 s avec audio (le dernier paquet AAC déborde), et
    480 pixels de haut dans les deux cas.

    APPELÉE SUR UNE VIDÉO, garantie par la route : MESURÉ, ffmpeg réussit sur
    un `.wav` (il rend un mp4 SANS image, `-vf scale` étant simplement ignoré)
    et sur un PNG (un mp4 d'une image fixe). Les deux sont des « aperçus »
    parfaitement inutilisables que rien ne signalerait."""
    out = proxy_path(src)
    if out.exists():
        return out
    tmp = _tmp_de(out)
    r = _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=-2:480",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
              "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
              "-movflags", "+faststart", str(tmp)],
             timeout=600, quoi="l'aperçu 480p")
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise MediaError("aperçu 480p impossible pour « %s » — %s"
                         % (Path(src).name, _lignes_utiles(r.stderr)))
    return _ecrire(tmp, out)
