# -*- coding: utf-8 -*-
"""t317 (28/10/2026) (lot D3 « montage après coup des captures ») — le MONTAGE façon Screen Studio d'une capture de
t315. Plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec 2026-10-25-boite-a-outils-design.md §8.4.

Le brut et la piste des clics (`<id>.dzclics.json`) ne sont jamais modifiés : un document `montage.json` (version 1),
proposé d'après la piste puis ajusté dans l'éditeur, décrit
- les ZOOMS {id, t0, t1, k, x, y} (ms de la source, centre 0..1) : un par geste, jamais deux qui se chevauchent ;
- les COUPES {id, t0, t1, mode accelerer|couper, vitesse 2|4|8|16} : les attentes de génération ;
- les CHAPITRES {id, t, titre, ecran} : les changements d'écran ;
- le FORMAT 16:9 | 9:16 | 1:1 (le recadrage suit les zooms) et les SOUS-TITRES {source aucun|texte|transcrire, texte,
  langue}.
Le rendu (UN ffmpeg) part de la piste `scene` (caviardée à chaque image et habillée par le skin, §8.2-8.3) : zoompan
sur le temps d'entrée, recadrage au format, segments accélérés ou retirés, chapitres en métadonnées. Les formules de
zoom sont les mêmes que l'aperçu de l'éditeur (dz-montage-capture-logique.js, `zoomA`).
Aucun réseau, aucune dépense ici (la transcription payante est gardée par la route). Journaux : ids et nombres."""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from app.services import capture as C

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
TAILLES = FORMATS
VITESSES = (2, 4, 8, 16)
MODES_COUPE = ("accelerer", "couper")
SOURCES_ST = ("aucun", "texte", "transcrire")
LANGUES = ("fr", "en")
K_DEFAUT, K_MIN, K_MAX = 1.8, 1.1, 2.5
AVANT, APRES = 500, 1500            # fenêtre d'un zoom autour d'un clic (ms)
JOINT, ECART = 800, 0.35            # un clic à moins de 800 ms de la fin et 0,35 du centre rejoint le zoom
ZOOM_MAX = 8000                     # un zoom dure 8 s au plus
RAMPE = 400                         # montée et descente d'un zoom (ms, smoothstep)
GEN_MIN, GEN_MARGE = 3000, 500      # une attente de génération d'au moins 3 s ; on garde 0,5 s de chaque côté
CHAP_MIN = 3000                     # un chapitre de moins de 3 s est absorbé par le précédent
MAX_ZOOMS, MAX_COUPES, MAX_CHAPITRES = 200, 200, 100
MAX_TITRE, MAX_TEXTE = 80, 20000
FPS = 30
ID_ELT = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


class RefusMontage(ValueError):
    """Un montage refusé : `statut` = le code HTTP. Levée avec un message littéral (L10)."""
    def __init__(self, message: str, statut: int = 400):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return C.racine()


# ── outils ──

def _nb(v):
    """Un nombre fini, jamais un booléen ni un texte (None sinon)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def _borne(v, lo, hi):
    return max(lo, min(hi, v))


def _nid(prefixe: str) -> str:
    return prefixe + secrets.token_hex(4)


def _ecran_sur(v) -> str:
    return v if isinstance(v, str) and C.ECRAN_SUR.match(v) else ""


def _titre(v) -> str:
    if not isinstance(v, str):
        return ""
    v = "".join(c for c in v if not unicodedata.category(c).startswith("C"))
    return " ".join(v.split())[:MAX_TITRE]


def _k(k) -> float:
    k = _nb(k)
    return round(_borne(k, K_MIN, K_MAX), 3) if k is not None else K_DEFAUT


# ── proposition ──

def _zooms_auto(evts: list, k: float) -> list[dict]:
    groupes: list[dict] = []
    for e in evts:
        if e.get("type") != "clic" or e.get("secret"):
            continue
        t, x, y = _nb(e.get("t")), _nb(e.get("x")), _nb(e.get("y"))
        if t is None or x is None or y is None:
            continue
        g = groupes[-1] if groupes else None
        if (g and t < g["t1"] + JOINT and abs(x - g["cx"]) < ECART and abs(y - g["cy"]) < ECART
                and t + APRES - g["t0"] <= ZOOM_MAX):
            g["xs"].append(x); g["ys"].append(y)
            g["t1"], g["dernier"] = int(t + APRES), t
            g["cx"], g["cy"] = sum(g["xs"]) / len(g["xs"]), sum(g["ys"]) / len(g["ys"])
            continue
        t0 = int(max(0, t - AVANT))
        if g and t0 < g["t1"]:                         # chevauchement : on partage au milieu des deux clics
            mil = int((g["dernier"] + t) / 2) if g["dernier"] < t else int(t)
            g["t1"] = max(g["t0"] + 201, mil)
            t0 = g["t1"]
        groupes.append({"t0": t0, "t1": int(t + APRES), "xs": [x], "ys": [y], "cx": x, "cy": y, "dernier": t})
    return [{"id": f"z{i + 1}", "t0": g["t0"], "t1": g["t1"], "k": k, "x": round(g["cx"], 4), "y": round(g["cy"], 4)}
            for i, g in enumerate(groupes)]


def _coupes_auto(evts: list) -> list[dict]:
    debuts: dict[str, int] = {}
    brutes = []
    for e in evts:
        t = _nb(e.get("t"))
        if t is None or not isinstance(e.get("job_id"), str):
            continue
        if e.get("type") == "generation_debut":
            debuts.setdefault(e["job_id"], int(t))
        elif e.get("type") == "generation_fin" and e["job_id"] in debuts:
            a = debuts.pop(e["job_id"])
            if t - a >= GEN_MIN:
                brutes.append((a + GEN_MARGE, int(t) - GEN_MARGE))
    out: list[list[int]] = []
    for a, b in sorted(brutes):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [{"id": f"c{i + 1}", "t0": a, "t1": b, "mode": "accelerer", "vitesse": 8} for i, (a, b) in enumerate(out)]


def _chapitres_auto(evts: list, duree: int) -> list[dict]:
    brut: list[list] = []
    for e in evts:
        t = _nb(e.get("t"))
        if e.get("type") != "ecran" or t is None:
            continue
        ec = _ecran_sur(e.get("ecran"))
        if not ec or (brut and brut[-1][1] == ec):
            continue
        brut.append([int(t), ec])
    if not brut:
        brut = [[0, ""]]
    brut[0][0] = 0
    garde: list[list] = []
    for i, (t, ec) in enumerate(brut):
        fin = brut[i + 1][0] if i + 1 < len(brut) else max(duree, t)
        if garde and fin - t < CHAP_MIN:
            continue                                   # absorbé par le précédent
        if garde and garde[-1][1] == ec:
            continue
        garde.append([t, ec])
    return [{"id": f"h{i + 1}", "t": t, "titre": "", "ecran": ec} for i, (t, ec) in enumerate(garde)]


def proposer(clics, *, k=None) -> dict:
    """Le montage proposé d'après la piste des clics (format v1 du plan) ; une piste illisible donne un montage vide."""
    doc = clics if isinstance(clics, dict) else {}
    evts = [e for e in (doc.get("evenements") or []) if isinstance(e, dict)] if isinstance(doc.get("evenements"),
                                                                                            list) else []
    evts.sort(key=lambda e: _nb(e.get("t")) or 0)
    duree = int(_nb(doc.get("duree_ms")) or 0)
    return {"version": 1, "capture_id": doc.get("id") if isinstance(doc.get("id"), str) and C.ID.match(doc["id"]) else "",
            "format": "16:9", "zooms": _zooms_auto(evts, _k(k)), "coupes": _coupes_auto(evts),
            "chapitres": _chapitres_auto(evts, duree), "sous_titres": {"source": "aucun", "texte": "", "langue": "fr"}}


# ── validation (le serveur seul juge du format) ──

def _id(v, prefixe: str, vus: set) -> str:
    i = v if isinstance(v, str) and ID_ELT.match(v) and v not in vus else _nid(prefixe)
    vus.add(i)
    return i


def valider(m, duree_ms, capture_id: str) -> dict:
    """Le montage envoyé par l'écran, relu par LISTE BLANCHE ; RefusMontage(400) s'il est illisible ou s'il retire
    toute la vidéo."""
    if not isinstance(m, dict):
        raise RefusMontage("Montage illisible.", 400)
    duree = int(_nb(duree_ms) or 0)
    vus: set = set()

    def temps(e):
        a, b = _nb(e.get("t0")), _nb(e.get("t1"))
        if a is None or b is None:
            return None
        a, b = int(_borne(a, 0, duree)), int(_borne(b, 0, duree))
        return (a, b) if b > a + 200 else None

    zooms = []
    for z in (m.get("zooms") if isinstance(m.get("zooms"), list) else []):
        if not isinstance(z, dict) or len(zooms) >= MAX_ZOOMS:
            continue
        tt, x, y = temps(z), _nb(z.get("x")), _nb(z.get("y"))
        if tt is None or x is None or y is None:
            continue
        zooms.append({"id": _id(z.get("id"), "z", vus), "t0": tt[0], "t1": tt[1], "k": _k(z.get("k")),
                      "x": round(_borne(x, 0, 1), 4), "y": round(_borne(y, 0, 1), 4)})
    zooms.sort(key=lambda z: z["t0"])
    propres = []
    for z in zooms:                                     # jamais deux zooms qui se chevauchent : le suivant est rogné
        if propres and z["t0"] < propres[-1]["t1"]:
            z["t0"] = propres[-1]["t1"]
            if z["t1"] <= z["t0"] + 200:
                continue
        propres.append(z)

    coupes = []
    for c in (m.get("coupes") if isinstance(m.get("coupes"), list) else []):
        if not isinstance(c, dict) or len(coupes) >= MAX_COUPES:
            continue
        tt = temps(c)
        if tt is None:
            continue
        v = c.get("vitesse")
        coupes.append({"id": _id(c.get("id"), "c", vus), "t0": tt[0], "t1": tt[1],
                       "mode": c.get("mode") if c.get("mode") in MODES_COUPE else "accelerer",
                       "vitesse": v if v in VITESSES and not isinstance(v, bool) else 8})
    coupes.sort(key=lambda c: c["t0"])
    fusion: list[dict] = []
    for c in coupes:
        if fusion and c["t0"] <= fusion[-1]["t1"]:
            p = fusion[-1]
            if (c["mode"], c["vitesse"]) == (p["mode"], p["vitesse"]):
                p["t1"] = max(p["t1"], c["t1"])
                continue
            c["t0"] = p["t1"]                          # revue finale : deux modes différents ne se fondent pas
            if c["t1"] <= c["t0"] + 200:
                continue
        fusion.append(c)
    gardee = duree - sum(c["t1"] - c["t0"] for c in fusion if c["mode"] == "couper")
    if duree and gardee < 500:
        raise RefusMontage("Les coupes retirent toute la vidéo.", 400)

    chapitres = []
    for h in (m.get("chapitres") if isinstance(m.get("chapitres"), list) else []):
        if not isinstance(h, dict) or len(chapitres) >= MAX_CHAPITRES:
            continue
        t = _nb(h.get("t"))
        if t is None:
            continue
        chapitres.append({"id": _id(h.get("id"), "h", vus), "t": int(_borne(t, 0, duree)), "titre": _titre(h.get("titre")),
                          "ecran": _ecran_sur(h.get("ecran"))})
    chapitres.sort(key=lambda h: h["t"])

    st = m.get("sous_titres") if isinstance(m.get("sous_titres"), dict) else {}
    texte = st.get("texte") if isinstance(st.get("texte"), str) else ""
    return {"version": 1, "capture_id": capture_id,
            "format": m.get("format") if m.get("format") in FORMATS else "16:9",
            "zooms": propres, "coupes": fusion, "chapitres": chapitres,
            "sous_titres": {"source": st.get("source") if st.get("source") in SOURCES_ST else "aucun",
                            "texte": texte[:MAX_TEXTE], "langue": st.get("langue") if st.get("langue") in LANGUES else "fr"}}


# ── temps de sortie ──

def segments(m: dict, duree_ms) -> list[tuple[int, int, int]]:
    """Les morceaux gardés, dans l'ordre : (début, fin, vitesse) en ms de la source ; une coupe « couper » disparaît."""
    duree = int(duree_ms or 0)
    out, t = [], 0
    for c in sorted(m.get("coupes") or [], key=lambda c: c["t0"]):
        a, b = max(t, c["t0"]), min(duree, c["t1"])
        if b <= a:
            continue
        if a > t:
            out.append((t, a, 1))
        if c["mode"] == "accelerer":
            out.append((a, b, int(c["vitesse"])))
        t = b
    if t < duree:
        out.append((t, duree, 1))
    return out


def vers_sortie(t_ms, segs) -> float:
    """L'instant de la vidéo montée qui montre l'instant `t_ms` de la source (dans une coupe : le début du morceau
    suivant)."""
    acc = 0.0
    for a, b, v in segs:
        if t_ms < a:
            return acc
        if t_ms <= b:
            r = acc + (t_ms - a) / v
            return int(r) if float(r).is_integer() else r
        acc += (b - a) / v
    return int(acc) if float(acc).is_integer() else acc


def _libelle(h: dict, i: int) -> str:
    return h.get("titre") or (h.get("ecran") or "").replace("_", " ").replace("-", " ").capitalize() or str(i + 1)


def chapitres_sortie(m: dict, segs) -> list[dict]:
    out: list[dict] = []
    for i, h in enumerate(sorted(m.get("chapitres") or [], key=lambda h: h["t"])):
        t = int(round(vers_sortie(h["t"], segs)))
        if out and out[-1]["t"] == t:
            out[-1] = {"t": t, "titre": _libelle(h, i)}       # deux chapitres au même instant : le dernier
        else:
            out.append({"t": t, "titre": _libelle(h, i)})
    if out:
        out[0]["t"] = 0                                 # YouTube ignore des chapitres qui ne commencent pas à 00:00
    return out


def _horloge(ms: int) -> str:
    s = int(ms // 1000)
    h, r = divmod(s, 3600)
    return f"{h}:{r // 60:02d}:{r % 60:02d}" if h else f"{r // 60:02d}:{r % 60:02d}"


def texte_chapitres(ch) -> str:
    """Les chapitres au format des descriptions YouTube (« 00:00 Titre », une ligne chacun)."""
    return "\n".join(f"{_horloge(c['t'])} {c['titre']}" for c in ch)


def _meta_esc(s: str) -> str:
    return re.sub(r"([=;#\\\n])", r"\\\1", s)


def ffmetadata(ch, total_ms) -> str:
    lignes = [";FFMETADATA1"]
    for i, c in enumerate(ch):
        fin = ch[i + 1]["t"] if i + 1 < len(ch) else int(total_ms)
        if fin <= c["t"]:
            continue
        lignes += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={c['t']}", f"END={fin}", f"title={_meta_esc(c['titre'])}"]
    return "\n".join(lignes) + "\n"


# ── zooms ──

def _ss(s: float) -> float:
    return s * s * (3 - 2 * s)


def _rampe_ms(z) -> float:
    return min(RAMPE, (z["t1"] - z["t0"]) / 2)


def zoom_a(m: dict, t_ms) -> tuple[float, float, float]:
    """(niveau, centre x, centre y) à l'instant `t_ms` de la source : 1 hors des zooms, montée et descente douces."""
    z_, cx, cy = 1.0, 0.5, 0.5
    for z in m.get("zooms") or []:
        if not (z["t0"] <= t_ms <= z["t1"]):
            continue
        r = _rampe_ms(z)
        e = _ss(_borne((t_ms - z["t0"]) / r, 0, 1)) * _ss(_borne((z["t1"] - t_ms) / r, 0, 1))
        z_ += (z["k"] - 1) * e
        cx += (z["x"] - 0.5) * e
        cy += (z["y"] - 0.5) * e
    return z_, cx, cy


def _n(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def expressions(m: dict, var: str = "it") -> dict:
    """Les mêmes formules que `zoom_a`, en expressions ffmpeg du temps `var` (secondes)."""
    zs = m.get("zooms") or []
    if not zs:
        return {"z": "1", "cx": "0.5", "cy": "0.5"}
    tz, tx, ty = [], [], []
    for z in zs:
        a, b, r = z["t0"] / 1000, z["t1"] / 1000, _rampe_ms(z) / 1000
        s1 = f"clip(({var}-{_n(a)})/{_n(r)},0,1)"
        s2 = f"clip(({_n(b)}-{var})/{_n(r)},0,1)"
        env = f"between({var},{_n(a)},{_n(b)})*({s1}*{s1}*(3-2*{s1}))*({s2}*{s2}*(3-2*{s2}))"
        tz.append(f"({_n(z['k'] - 1)})*{env}")
        tx.append(f"({_n(z['x'] - 0.5)})*{env}")
        ty.append(f"({_n(z['y'] - 0.5)})*{env}")
    return {"z": "1+" + "+".join(tz), "cx": "0.5+" + "+".join(tx), "cy": "0.5+" + "+".join(ty)}


def cadre_format(fmt: str, largeur: int, hauteur: int) -> tuple[int, int]:
    """La fenêtre (paire) au rapport du format, la plus grande possible dans l'image source."""
    ol, oh = FORMATS.get(fmt, FORMATS["16:9"])
    if largeur / hauteur > ol / oh:
        h = hauteur
        l = int(round(h * ol / oh))
    else:
        l = largeur
        h = int(round(l * oh / ol))
    return max(2, l - l % 2), max(2, h - h % 2)


# ── ffmpeg ──

def _ffmpeg() -> str:
    from app.services.effects_preview import ffmpeg_bin
    return ffmpeg_bin()


def _ffprobe() -> str:
    ff = Path(_ffmpeg())
    cand = ff.with_name("ffprobe" + ff.suffix)
    return str(cand) if cand.is_file() else (shutil.which("ffprobe") or "ffprobe")


_VERROUS: dict[str, threading.Lock] = {}
_VERROUS_GARDE = threading.Lock()


def _verrou(cid: str) -> threading.Lock:
    with _VERROUS_GARDE:
        return _VERROUS.setdefault(cid, threading.Lock())


def remuxer(cid: str, piste: str = "scene") -> Path:
    """Une piste WebM de MediaRecorder (ni durée ni index) remuxée sans réencodage dans `<piste>.remux.webm`, gardée
    tant que le brut ne change pas. Une piste MP4 est rendue telle quelle. Un remux à la fois par capture (revue
    finale I5 : l'aperçu et le rendu peuvent le demander ensemble), temporaire unique."""
    src = C.chemin_piste(cid, piste)
    if src is None or src.stat().st_size == 0:
        raise RefusMontage("La capture n'a reçu aucune image.", 409)
    if src.suffix != ".webm":
        return src
    out = src.with_name(f"{piste}.remux.webm")
    with _verrou(cid):
        if out.is_file() and out.stat().st_mtime_ns >= src.stat().st_mtime_ns and out.stat().st_size > 0:
            return out
        fd, nom = tempfile.mkstemp(prefix=f"{piste}.remux.", suffix=".tmp.webm", dir=src.parent)
        os.close(fd)
        tmp = Path(nom)
        try:
            r = subprocess.run([_ffmpeg(), "-y", "-v", "error", "-fflags", "+genpts", "-i", str(src), "-c", "copy",
                                "-f", "webm", str(tmp)], capture_output=True, timeout=1800)
        except subprocess.TimeoutExpired:
            r = None
        if r is None or r.returncode != 0 or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            raise RefusMontage("La piste de la capture est illisible.", 422)
        tmp.replace(out)
    return out


def sonder(p: Path) -> dict:
    r = subprocess.run([_ffprobe(), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)],
                       capture_output=True, text=True, timeout=120)
    try:
        j = json.loads(r.stdout or "{}")
        v = next(s for s in j.get("streams", []) if s.get("codec_type") == "video")
    except (ValueError, StopIteration):
        raise RefusMontage("La piste de la capture est illisible.", 422) from None
    d = _nb(float(j.get("format", {}).get("duration") or 0)) or 0
    return {"largeur": int(v.get("width") or 0), "hauteur": int(v.get("height") or 0), "duree_ms": int(d * 1000),
            "audio": any(s.get("codec_type") == "audio" for s in j.get("streams", []))}


def graphe(m: dict, segs, src: dict, fmt: str) -> str:
    """Le graphe de filtres du rendu (aucun chemin dedans)."""
    W, H = src["largeur"] - src["largeur"] % 2, src["hauteur"] - src["hauteur"] % 2
    cw, ch = cadre_format(fmt, W, H)
    ol, oh = FORMATS.get(fmt, FORMATS["16:9"])
    ei, et = expressions(m, "it"), expressions(m, "t")
    zp = (f"zoompan=z='{ei['z']}':x='clip(({ei['cx']})*iw-iw/zoom/2,0,iw-iw/zoom)'"
          f":y='clip(({ei['cy']})*ih-ih/zoom/2,0,ih-ih/zoom)':d=1:s={W}x{H}:fps={FPS}")

    # là où le centre du zoom tombe dans l'image zoomée (0,5 quand le zoom n'est pas collé au bord)
    def u(c, dim):
        z = f"({et['z']})"
        return f"((({c})*{dim}-clip(({c})*{dim}-{dim}/{z}/2,0,{dim}-{dim}/{z}))*{z}/{dim})"
    cx, cy = u(et["cx"], W), u(et["cy"], H)
    crop = (f"crop=w={cw}:h={ch}:x='clip({cx}*iw-{cw}/2,0,iw-{cw})':y='clip({cy}*ih-{ch}/2,0,ih-{ch})'")
    n = len(segs)
    parts = [f"[0:v]setpts=PTS-STARTPTS,fps={FPS},{zp},{crop},scale={ol}:{oh},setsar=1,format=yuv420p,split={n}"
             + "".join(f"[v{i}]" for i in range(n))]
    normaux = [i for i, s in enumerate(segs) if s[2] == 1] if src.get("audio") else []
    if normaux:
        parts.append(f"[0:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,asplit={len(normaux)}"
                     + "".join(f"[a{i}]" for i in normaux))
    fin = ""
    for i, (a, b, v) in enumerate(segs):
        parts.append(f"[v{i}]trim=start={_n(a / 1000)}:end={_n(b / 1000)},setpts=(PTS-STARTPTS)/{v}[s{i}]")
        if i in normaux:
            parts.append(f"[a{i}]atrim=start={_n(a / 1000)}:end={_n(b / 1000)},asetpts=PTS-STARTPTS[t{i}]")
        else:                                      # accéléré (ou source muette) : silence de la durée de sortie
            parts.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={_n((b - a) / v / 1000)}[t{i}]")
        fin += f"[s{i}][t{i}]"
    parts.append(f"{fin}concat=n={n}:v=1:a=1[v][a]")
    return ";\n".join(parts)


def _nom_sortie(dossier: Path, cid: str, fmt: str) -> Path:
    base = f"montage_{datetime.now().strftime('%Y%m%d-%H%M%S')}_{cid}_{fmt.replace(':', 'x')}"
    p, i = dossier / f"{base}.mp4", 2
    while p.exists():
        p, i = dossier / f"{base}-{i}.mp4", i + 1
    return p


def rendre(cid: str, m: dict, dest_dossier: Path) -> dict:
    """Rend le montage `m` (déjà validé) de la capture : {fichier, duree_ms, chapitres, texte}. Le mp4 n'apparaît
    qu'après un ffmpeg réussi."""
    src = remuxer(cid, "scene")
    info = sonder(src)
    duree = info["duree_ms"] or int(C.lire(cid)["session"].get("duree_ms") or 0)
    if not duree or not info["largeur"]:
        raise RefusMontage("La piste de la capture est illisible.", 422)
    segs = segments(m, duree)
    if not segs:
        raise RefusMontage("Les coupes retirent toute la vidéo.", 400)
    total = sum((b - a) / v for a, b, v in segs)
    ch = chapitres_sortie(m, segs)
    dest_dossier.mkdir(parents=True, exist_ok=True)
    dest = _nom_sortie(dest_dossier, cid, m.get("format") or "16:9")
    with tempfile.TemporaryDirectory(prefix="dzmontage_") as d:
        g, meta = Path(d) / "graphe.txt", Path(d) / "chapitres.txt"
        g.write_text(graphe(m, segs, info, m.get("format") or "16:9"), "utf-8")
        meta.write_text(ffmetadata(ch, int(total)), "utf-8")
        tmp = dest.with_name(dest.stem + ".tmp.mp4")
        try:
            r = subprocess.run([_ffmpeg(), "-y", "-v", "error", "-i", str(src), "-i", str(meta), "-/filter_complex",
                                str(g), "-map", "[v]", "-map", "[a]", "-map_metadata", "1", "-map_chapters", "1",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(tmp)],
                               capture_output=True, timeout=7200)
        except subprocess.TimeoutExpired:
            tmp.unlink(missing_ok=True)
            raise RefusMontage("Le rendu du montage a échoué.", 500) from None
        if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1024:
            tmp.unlink(missing_ok=True)
            from loguru import logger
            logger.warning(f"montage {cid} : ffmpeg en échec ({r.returncode}) "
                           + r.stderr.decode("utf-8", "replace")[-300:].replace(str(src), "<scene>"))
            raise RefusMontage("Le rendu du montage a échoué.", 500)
        tmp.replace(dest)
    return {"fichier": dest, "duree_ms": int(total), "chapitres": ch, "texte": texte_chapitres(ch)}


# ── montage enregistré ──

def lire_montage(cid: str) -> dict | None:
    """Le montage enregistré, None s'il manque ou s'il est illisible (revue finale I4 : la capture reste montable)."""
    f = C._dossier(cid) / "montage.json"
    try:
        m = json.loads(f.read_text("utf-8")) if f.is_file() else None
    except (ValueError, OSError):
        return None
    return m if isinstance(m, dict) else None


def ecrire_montage(cid: str, m: dict) -> None:
    d = C._dossier(cid)
    fd, nom = tempfile.mkstemp(prefix="montage.", suffix=".json.tmp", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    Path(nom).replace(d / "montage.json")
