# -*- coding: utf-8 -*-
"""Post-traitement de Son & VFX (t276, 22/10/2026) : une PILE ordonnée de presets appliquée à un rendu choisi.

Un maillon de pile : {preset: id de effects_engine.POST_PILE, intensite: 0-100, masque: bool, params: {...}}.
Chaque preset est un effet du moteur (`effects_engine.build_chain`, la chaîne du rack du Montage) : l'intensité passe
à son paramètre `intensity` quand il en a un, sinon à un mélange dry/wet (LUT, bandes cinéma). Un maillon masqué ou à
0 % ne rend rien. Les paramètres passent par `effects_preview.coerce_params` (bornes du catalogue, couleurs hexa,
LUT confinée) : rien du client n'atteint ffmpeg autrement.

L'APERÇU et le RENDU partagent le même `-filter_complex` (`graphe`) : les effets sont calculés à la taille de la
source, puis l'aperçu seulement est réduit pour l'écran. L'aperçu prend l'image par une recherche en SORTIE (`-ss`
après `-i`) : ffmpeg décode depuis le début, les effets temporels (grain, VHS, secousse) voient les mêmes images que
le rendu, et l'image de l'aperçu à t est celle du rendu à t (à l'encodage près). Une source .webm (particules, VP9 +
alpha) est lue par libvpx-vp9 et posée sur du noir.

Gratuit : ffmpeg local, aucune clé, aucun plafond. Les presets de pile enregistrés vivent dans le dossier des données
(`post_presets.json`, à côté de outputs) et survivent aux mises à jour.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from app.config import settings
from app.services import effects_engine as FX

#: Nombre maximal de maillons d'une pile.
PILE_MAX = 24
#: Intensité d'un maillon qui n'en donne pas (ou une illisible).
INTENSITE_DEFAUT = 60
#: Largeur d'un aperçu réduit pour l'écran, bornée.
LARGEUR_MIN, LARGEUR_MAX = 64, 1920
#: Version du rendu d'aperçu (change la clé du cache).
_VERSION = 1


def _ff(nom: str = "ffmpeg") -> str:
    from app.services.sfx_service import _bin
    return _bin(nom)


# ------------------------------------------------------------------ la pile ---
def normaliser(pile) -> list[dict]:
    """La pile reçue → maillons propres {id, preset, intensite, masque, params}. ValueError si elle est refusée."""
    if not isinstance(pile, list):
        raise ValueError("la pile doit être une liste de maillons")
    if len(pile) > PILE_MAX:
        raise ValueError(f"pile trop longue : {len(pile)} maillons (au plus {PILE_MAX})")
    from app.services.effects_preview import coerce_params
    out = []
    for m in pile:
        if not isinstance(m, dict):
            raise ValueError("un maillon de pile doit être un objet")
        pid = str(m.get("preset") or "")
        d = FX.POST_PILE.get(pid)
        if d is None:
            raise ValueError(f"preset de post-traitement inconnu : {pid[:40]!r}")
        try:
            v = float(m.get("intensite", INTENSITE_DEFAUT))
            v = INTENSITE_DEFAUT if math.isnan(v) else v
        except (TypeError, ValueError):
            v = INTENSITE_DEFAUT
        brut = m.get("params") if isinstance(m.get("params"), dict) else {}
        params = coerce_params(d["type"], {k: brut[k] for k in d["params"] if k in brut})
        uid = "".join(c for c in str(m.get("id") or "") if c.isalnum() or c in "-_")[:32]
        out.append({"id": uid, "preset": pid, "intensite": int(round(max(0.0, min(100.0, v)))),
                    "masque": bool(m.get("masque")), "params": params})
    return out


def effets(pile) -> list[dict]:
    """Les effets du moteur que la pile rend, dans l'ordre : maillons visibles et non nuls seulement. Un effet sans
    intensité propre porte `_mix` (0-100), le mélange dry/wet que `chaine` pose autour de lui."""
    cat = {p["id"]: p for p in FX.post_catalogue()}
    out = []
    for m in normaliser(pile):
        if m["masque"] or m["intensite"] <= 0:
            continue
        c = cat[m["preset"]]
        eff = {"type": c["type"]}
        for p, b in c["bounds"].items():
            if b.get("default") not in (None, ""):
                eff[p] = b["default"]
        eff.update(m["params"])
        if c["intensite"]:
            eff["intensity"] = m["intensite"]
        else:
            eff["_mix"] = m["intensite"]
        out.append(eff)
    return out


def chaine(pile, in_lbl: str, out_lbl: str, ctx: dict) -> list[str]:
    """Les instructions de filtergraph de la pile, de [in_lbl] à [out_lbl] ; pile vide : un simple passage."""
    effs = effets(pile)
    if not effs:
        return [f"[{in_lbl}]null[{out_lbl}]"]
    st, cur = [], in_lbl
    for k, eff in enumerate(effs):
        nxt = out_lbl if k == len(effs) - 1 else f"pp{k}o"
        u = f"pp{k}"
        mix = eff.pop("_mix", None)
        if mix is None or mix >= 100:
            st += FX.build_chain([eff], cur, nxt, u, ctx)
        else:
            st.append(f"[{cur}]split=2[{u}d][{u}s]")
            st += FX.build_chain([eff], f"{u}s", f"{u}w", u, ctx)
            st += [f"[{u}w]format=gbrp[{u}w2]", f"[{u}d]format=gbrp[{u}d2]",
                   f"[{u}w2][{u}d2]blend=all_mode=normal:all_opacity={mix / 100.0:.2f}[{nxt}]"]
        cur = nxt
    return st


# ---------------------------------------------------------------- la source ---
_INFOS: dict[tuple, dict] = {}
_INFOS_VERROU = threading.Lock()


def infos(video) -> dict:
    """{w, h, fps, dur, audio} de la vidéo (ffprobe), mis en cache par (chemin, date, taille)."""
    p = Path(video)
    st = p.stat()
    cle = (str(p), int(st.st_mtime), st.st_size)
    with _INFOS_VERROU:
        if cle in _INFOS:
            return dict(_INFOS[cle])
    r = subprocess.run([_ff("ffprobe"), "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,avg_frame_rate,r_frame_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True, timeout=60)
    d = json.loads(r.stdout or "{}")
    vs = [s for s in d.get("streams") or [] if s.get("codec_type") == "video"]
    if not vs:
        raise ValueError("aucune image vidéo dans cette source")
    v = vs[0]

    def _cad(s):
        try:
            a, b = str(s or "0/1").split("/")
            return float(a) / float(b) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0
    fps = _cad(v.get("avg_frame_rate")) or _cad(v.get("r_frame_rate")) or 30.0
    try:
        dur = float((d.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        dur = 0.0
    out = {"w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
           "fps": int(round(fps)) if 1 <= fps <= 240 else 30, "dur": dur,
           "audio": any(s.get("codec_type") == "audio" for s in d.get("streams") or [])}
    with _INFOS_VERROU:
        _INFOS[cle] = out
    return dict(out)


def _decodeur(p: Path) -> list[str]:
    """.webm (particules, VP9 + alpha) : libvpx-vp9, le décodeur natif ignore l'alpha."""
    from app.services.matte_service import decodeur_entree
    return decodeur_entree(p)


def graphe(video, pile, largeur: int | None = None) -> str:
    """Le `-filter_complex` commun à l'aperçu et au rendu : [0:v] → [pv] (taille de la source, paire) ; avec
    `largeur`, l'aperçu ajoute la réduction [pv] → [pa]."""
    p = Path(video)
    i = infos(p)
    w, h = FX._even(i["w"]), FX._even(i["h"])
    if p.suffix.lower() == ".webm":
        tete = [f"color=c=black:s={w}x{h}:r={i['fps']}[pbg]", f"[0:v]scale={w}:{h},format=rgba[pfg]",
                "[pbg][pfg]overlay=shortest=1:format=auto,setsar=1,format=yuv420p[pin]"]
    else:
        tete = [f"[0:v]scale={w}:{h},setsar=1,format=yuv420p[pin]"]
    st = tete + chaine(pile, "pin", "pout", {"w": w, "h": h, "fps": i["fps"], "dur": i["dur"]})
    st.append("[pout]format=yuv420p[pv]")
    if largeur:
        st.append(f"[pv]scale={_largeur(largeur)}:-2[pa]")
    return ";".join(st)


def _largeur(v) -> int:
    try:
        v = int(float(v))
    except (TypeError, ValueError):
        v = LARGEUR_MAX
    return max(LARGEUR_MIN, min(LARGEUR_MAX, v)) // 2 * 2


def _instant(video, t) -> float:
    i = infos(video)
    try:
        t = float(t)
        t = 0.0 if math.isnan(t) else t
    except (TypeError, ValueError):
        t = 0.0
    fin = max(0.0, i["dur"] - 1.0 / max(1, i["fps"]))
    return max(0.0, min(fin, t))


def commande_apercu(video, pile, t, dest, largeur: int | None = None) -> list[str]:
    p = Path(video)
    return [_ff(), "-y", "-v", "error", *_decodeur(p), "-i", str(p),
            "-filter_complex", graphe(p, pile, largeur), "-map", "[pa]" if largeur else "[pv]",
            "-ss", f"{_instant(p, t):.3f}", "-frames:v", "1", "-update", "1", str(dest)]


def commande_rendu(video, pile, dest) -> list[str]:
    p = Path(video)
    return [_ff(), "-y", "-v", "error", *_decodeur(p), "-i", str(p),
            "-filter_complex", graphe(p, pile), "-map", "[pv]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dest)]


# ------------------------------------------------------------ aperçu, rendu ---
def apercu(video, pile, t, largeur: int | None = None) -> Path:
    """L'image PNG de la pile appliquée à la source à l'instant t (cache disque : la même demande ne relance pas
    ffmpeg). RuntimeError si ffmpeg n'a rien produit."""
    from app.services import effects_preview as FXP
    p = Path(video)
    st = p.stat()
    cle = hashlib.sha1(json.dumps([normaliser(pile), str(p.resolve()), int(st.st_mtime), st.st_size,
                                   round(_instant(p, t), 3), _largeur(largeur) if largeur else 0, _VERSION],
                                  sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
    out = FXP.cache_dir() / f"post_{cle}.png"
    if out.is_file() and out.stat().st_size:
        return out
    with FXP._frame_lock(out.name):
        if out.is_file() and out.stat().st_size:
            return out
        tmp = out.with_name(f"{out.stem}.{os.getpid()}-{threading.get_ident()}.tmp.png")
        try:
            r = subprocess.run(commande_apercu(p, pile, t, tmp, largeur), capture_output=True, text=True,
                               timeout=300)
            if r.returncode != 0 or not tmp.is_file() or not tmp.stat().st_size:
                der = (r.stderr or "").strip().splitlines()
                raise RuntimeError(f"aperçu impossible : {der[-1][:200] if der else 'sortie vide'}")
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
    FXP._prune_cache(keep=300, motifs=("post_*.png",))
    return out


def rendre(video, pile, dest, on_progress=None) -> Path:
    """Rend toute la source à travers la pile vers `dest` (MP4 H.264, son gardé). ValueError si la pile ne rend
    rien ; RuntimeError si ffmpeg échoue. `on_progress(fraction)` reçoit l'avancement."""
    if not effets(pile):
        raise ValueError("la pile ne rend rien : chaque maillon est masqué ou à 0 %")
    p, dest = Path(video), Path(dest)
    dur = infos(p)["dur"] or 0.0
    tmp = dest.with_name(f"{dest.stem}.tmp{dest.suffix}")
    cmd = commande_rendu(p, pile, tmp)
    cmd[1:1] = ["-progress", "pipe:1", "-nostats"]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                          errors="replace")
    err: list[str] = []
    lecteur = threading.Thread(target=lambda: err.extend(pr.stderr.read().splitlines()), daemon=True)
    lecteur.start()
    try:
        for ligne in pr.stdout:
            if on_progress and dur > 0 and ligne.startswith("out_time_ms="):
                try:
                    on_progress(max(0.0, min(1.0, int(ligne.split("=", 1)[1]) / 1e6 / dur)))
                except (ValueError, TypeError):
                    pass
        pr.wait(timeout=3600)
        lecteur.join(timeout=5)
        if pr.returncode != 0 or not tmp.is_file() or not tmp.stat().st_size:
            raise RuntimeError(f"rendu impossible : {err[-1][:200] if err else 'sortie vide'}")
        tmp.replace(dest)
    finally:
        if pr.poll() is None:
            pr.kill()
        tmp.unlink(missing_ok=True)
    return dest


# ---------------------------------------------------- presets de pile gardés ---
_PRESETS_VERROU = threading.Lock()


def presets_fichier() -> Path:
    return settings.outputs_path.parent / "post_presets.json"


def presets() -> list[dict]:
    f = presets_fichier()
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [p for p in d if isinstance(p, dict) and p.get("id")] if isinstance(d, list) else []


def _ecrire(lst):
    f = presets_fichier()
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(lst, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def enregistrer_preset(nom, pile) -> dict:
    nom = " ".join(str(nom or "").split())[:60]
    if not nom:
        raise ValueError("donnez un nom au preset de pile")
    propre = normaliser(pile)
    if not propre:
        raise ValueError("la pile est vide")
    e = {"id": uuid.uuid4().hex[:12], "nom": nom, "pile": propre, "cree": int(time.time())}
    with _PRESETS_VERROU:
        _ecrire([e] + presets())
    return e


def supprimer_preset(pid) -> bool:
    with _PRESETS_VERROU:
        lst = presets()
        reste = [p for p in lst if p.get("id") != str(pid)]
        if len(reste) == len(lst):
            return False
        _ecrire(reste)
    return True
