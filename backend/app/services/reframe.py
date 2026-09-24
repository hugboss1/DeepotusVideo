"""D-40 (L7-B, 24/09/2026) — le RECADRAGE PAR ÉNERGIE DE MOUVEMENT.

`motion_track(path, src_in, dur, fps=4, width=96, noise=12)` suit
horizontalement ce qui BOUGE dans l'extrait [src_in, src_in + dur[ de `path`
et rend `{mode, points, fps, x?, motion}` :

* `mode == "suivi"` : `points = [{t, x}]` — `t` en secondes RELATIVES au
  début lu (le `srcIn` du clip, en temps de SOURCE : c'est aussi le `t` que
  voit le `crop` de la chaîne cover, voir plus bas), `x` en fraction de la
  largeur de la source (0 = bord gauche, 1 = bord droit) : le centre voulu
  de la fenêtre de recadrage. Au plus 240 points (`MAX_POINTS`).
* `mode == "centre"` : trop peu de mouvement (plus de 20 % des paires
  d'images sans colonne au-dessus du bruit, ou moins de deux images) —
  `points = []`, `x = 0.5`.
* `motion` : la part des paires d'images où un mouvement a été vu (0..1) ;
  `images` : le nombre d'images lues (moins de deux → `MediaError`).

Méthode (numpy, cv2 et scipy sont ABSENTS du python embarqué — mesuré le
24/09) : ffmpeg écrit l'extrait en PNG gris `fps=4,scale=96:-2` dans un
dossier temporaire ; pour chaque paire d'images voisines,
`PIL.ImageChops.difference` puis `resize((w, 1), BOX)` = l'énergie de
mouvement MOYENNE de chaque colonne ; le barycentre des colonnes au-dessus
de `noise` (poids `v − noise`) est la position du mouvement, datée au milieu
de la paire ((i + ½)/fps) ; lissage EMA 0,5. Lecture au fil de l'eau
(revue du 24/09/2026) : chaque PNG est chargé, comparé à l'image précédente
SEULE puis supprimé — mémoire constante quelle que soit la durée.

MESURE DE L'ÉTAPE 1 — ffmpeg 8.1.1 essentials, Windows 11, 24/09/2026
(source 480×270 à 30 i/s, carré blanc de 60 px dont le centre vaut
70 + 95·T en temps ABSOLU de la source, rendu 152×270 lu en gris brut) :

* `crop=152:270:x='…t…':y=(ih-270)/2` — un `x` ANIMÉ — PASSE (rc 0) sur la
  chaîne cover réelle `scale=…:force_original_aspect_ratio=increase,crop=…,
  setsar=1,fps=30,format=yuv420p,tpad…,trim…,setpts=PTS-STARTPTS`, alors que
  le témoin `crop=w='152+t'` échoue toujours (−22, comme D-13 l'a mesuré) :
  `w`/`h` sont évalués une fois, `x`/`y` à chaque image.
* `t` dans ce crop est le temps LOCAL du flux lu : avec `-ss 1 -t 2` avant
  `-i`, `x = 70+95*(t+1)-76` garde le carré centré (colonne 75,5 aux images
  0/15/30/45) ; l'hypothèse « temps global » (`x = 70+95*t-76`) le décale
  (142,5…146,5). Même mesure sur la voie D-16 (`trim=start=1:duration=2,
  setpts=PTS-STARTPTS` avant le scale) : 75,5.
* VITESSE (C4) : le crop est posé AVANT `setpts=PTS/speed` ; à ×2, `t` y
  est donc le temps de SOURCE depuis `srcIn` (carré centré avec la même
  expression). D'où l'unité des points : secondes de SOURCE depuis srcIn —
  exactement ce que rend ce tracker, et, à ×1, le temps du clip ; bornés
  par `(end − start) × vitesse` côté rendu (`_reframe_of`). Le client (T4)
  convertit la tête de lecture par `(tête − start) × vitesse`, comme
  `/scenes` (D-42).
* Une expression par morceaux `if(lt(t,…),…)` à virgules, entre quotes
  simples, passe telle quelle dans `-filter_complex` (colonne 95,5 attendue
  ≈ 96). Aucun repli `sendcmd` n'a été nécessaire.
* REVUE (24/09/2026) : l'expression en CHAÎNE (`_mp_lerp_expr`) échoue à
  la configuration (−22) au-delà de 93 points dans le crop — l'analyseur
  d'expressions borne sa récursion ; le rendu utilise donc un ARBRE
  équilibré (`montage_service._rf_lerp_expr`, profondeur ~log2 n). Et une
  ligne de commande de plus de 30 000 caractères passe son graphe par
  `-/filter_complex <fichier>` (`montage_service._ff_run`).

Cache : `outputs/montage_cache/<sha(chemin résolu, mtime_ns, srcIn, dur,
fps, largeur, bruit)>_reframe.json` — le dossier et l'écriture atomique de
`montage_media`, comme `scenes`. Un échec n'est jamais mis en cache.

Échecs : source illisible, ffmpeg absent / en erreur / hors délai →
`montage_media.MediaError` (la route la traduit par `_media_http`). Délai
PROPORTIONNEL : `scenes.timeout_de` (2 × durée + 60 s, plancher 120 s).
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from app.services import montage_media as _MM
from app.services.scenes import timeout_de

MAX_POINTS = 240
SANS_MOUVEMENT_MAX = 0.20      # au-delà : « centre »
EMA = 0.5


def _ffmpeg(cmd: list, timeout: int):
    """Le lanceur : `montage_media._run` (tout échec d'exécution → MediaError).
    Point unique que le banc remplace par un espion."""
    return _MM._run(cmd, timeout=timeout, quoi="l'analyse du mouvement")


def _cle(path: Path, src_in: float, dur: float, fps: float, width: int, noise: float) -> Path:
    try:
        mtime = path.stat().st_mtime_ns
    except OSError as e:
        raise _MM.MediaError("source illisible : %s" % path.name) from e
    brut = "%s|%d|%.3f|%.3f|%.3f|%d|%.3f|reframe" % (path.resolve(), mtime, src_in, dur,
                                                     fps, width, noise)
    key = hashlib.sha1(brut.encode("utf-8")).hexdigest()[:20]
    return _MM._cache_dir() / ("%s_reframe.json" % key)


def barycentre(a, b, noise: float):
    """Position (0..1) du mouvement entre deux images PIL de même taille, ou
    None quand aucune colonne ne dépasse `noise` (énergie moyenne 0..255)."""
    from PIL import Image, ImageChops
    d = ImageChops.difference(a.convert("L"), b.convert("L"))
    w = d.size[0]
    cols = list(d.resize((w, 1), Image.BOX).getdata())
    tot = acc = 0.0
    for i, v in enumerate(cols):
        if v > noise:
            p = v - noise
            tot += p
            acc += (i + 0.5) * p
    return None if tot <= 0 else acc / tot / w


def suivre(images, fps: float, noise: float = 12) -> dict:
    """Le cœur PUR du tracker sur une suite d'images PIL (dans l'ordre, à
    `fps` images par seconde) — voir l'en-tête. `images` est un ITÉRABLE lu
    une seule fois, au fil de l'eau : seule l'image précédente est gardée
    (mémoire constante, revue du 24/09/2026). Le résultat porte `images`, le
    nombre d'images lues."""
    vus, prev, n_img = [], None, 0
    for im in images:
        n_img += 1
        if prev is not None:
            x = barycentre(prev, im, noise)
            if x is not None:
                vus.append(((n_img - 1.5) / fps, x))
        prev = im
    paires = max(0, n_img - 1)
    motion = (len(vus) / paires) if paires else 0.0
    if paires == 0 or (paires - len(vus)) > SANS_MOUVEMENT_MAX * paires:
        return {"mode": "centre", "x": 0.5, "points": [], "fps": fps,
                "motion": round(motion, 3), "images": n_img}
    pts, s = [], None
    for t, x in vus:
        s = x if s is None else EMA * x + (1 - EMA) * s
        pts.append({"t": round(t, 3), "x": round(min(1.0, max(0.0, s)), 4)})
    if len(pts) > MAX_POINTS:
        n = len(pts)
        pts = [pts[round(k * (n - 1) / (MAX_POINTS - 1))] for k in range(MAX_POINTS)]
    return {"mode": "suivi", "points": pts, "fps": fps, "motion": round(motion, 3),
            "images": n_img}


def _lire(dossier: Path):
    """Les PNG de `dossier` dans l'ordre, chacun chargé puis SUPPRIMÉ aussitôt
    (le disque se vide au fil de la lecture). Point que le banc espionne."""
    from PIL import Image
    for f in sorted(dossier.glob("f_*.png")):
        with Image.open(f) as im:
            g = im.convert("L")
        f.unlink(missing_ok=True)
        yield g


def motion_track(path, src_in, dur, fps: float = 4, width: int = 96, noise: float = 12) -> dict:
    """Le suivi du mouvement de [src_in, src_in + dur[ de `path` (voir
    l'en-tête). Cache disque ; `MediaError` sur tout échec, moins de deux
    images lues compris."""
    p = Path(path)
    si, du = max(0.0, float(src_in)), float(dur)
    fp = min(30.0, max(0.5, float(fps)))
    wd = int(min(480, max(16, int(width))))
    wd += wd % 2                                  # scale=W:-2 : W pair
    nz = min(254.0, max(0.0, float(noise)))
    out = _cle(p, si, du, fp, wd, nz)
    if out.exists():
        try:
            v = json.loads(out.read_text(encoding="utf-8"))
            if isinstance(v, dict) and v.get("mode") in ("suivi", "centre"):
                return v
        except (OSError, ValueError, TypeError):
            pass                        # cache illisible : on refait l'analyse
    with tempfile.TemporaryDirectory(prefix="dzrf_") as tmpd:
        r = _ffmpeg(["ffmpeg", "-hide_banner", "-nostats", "-v", "error",
                     "-ss", "%.3f" % si, "-t", "%.3f" % du, "-i", str(p),
                     "-an", "-sn", "-dn", "-vf",
                     "setpts=PTS-STARTPTS,fps=%g,scale=%d:-2,format=gray" % (fp, wd),
                     "-start_number", "0", str(Path(tmpd) / "f_%05d.png")], timeout_de(du))
        if r.returncode != 0:
            raise _MM.MediaError("analyse du mouvement impossible pour « %s » — %s"
                                 % (p.name, _MM._lignes_utiles(r.stderr)))
        res = suivre(_lire(Path(tmpd)), fp, nz)
    if res.get("images", 0) < 2:
        # un extrait trop court (ou sans image décodable) ne se suit pas ;
        # un résultat vide n'est jamais mis en cache.
        raise _MM.MediaError("analyse du mouvement impossible pour « %s » — %d image(s) "
                             "lue(s), il en faut deux" % (p.name, res.get("images", 0)))
    tmp = _MM._tmp_de(out)
    try:
        tmp.write_text(json.dumps(res), encoding="utf-8")
        _MM._ecrire(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return res


def simplifier(pairs: list, tol: float = 0.004) -> list:
    """Ramer-Douglas-Peucker sur des paires (t, x) TRIÉES : garde les
    extrémités et tout point qui s'écarte de plus de `tol` (fraction de la
    largeur) de la corde — l'expression ffmpeg du rendu reste courte (240
    points bruts ≈ 13 000 caractères par clip, plafond CreateProcess 32 767)
    sans déplacer le cadre de plus de `tol`."""
    if len(pairs) <= 2:
        return list(pairs)
    garde = [False] * len(pairs)
    garde[0] = garde[-1] = True
    pile = [(0, len(pairs) - 1)]
    while pile:
        a, b = pile.pop()
        (t0, x0), (t1, x1) = pairs[a], pairs[b]
        dmax, imax = 0.0, -1
        for i in range(a + 1, b):
            t, x = pairs[i]
            xl = x0 + (x1 - x0) * ((t - t0) / (t1 - t0) if t1 > t0 else 0.0)
            d = abs(x - xl)
            if d > dmax:
                dmax, imax = d, i
        if imax >= 0 and dmax > tol:
            garde[imax] = True
            pile.append((a, imax))
            pile.append((imax, b))
    return [q for q, g in zip(pairs, garde) if g]
