# -*- coding: utf-8 -*-
"""D-37 (L7-B, 24/09/2026) — EXPORT de la timeline du Montage vers un autre
logiciel de montage : EDL CMX 3600 et FCPXML. Service PUR : aucune E/S, aucun
état ; la route (`GET /api/montage/export`, montage_service.py) résout les
sources, sonde leurs durées et passe tout ici.

ENTRÉES
  rec     la timeline sauvegardée (`_load_saved()` : {name, ratio, tracks,
          clips[]}) — les champs de clip lus sont CEUX du rendu V1
          (`src`, `srcIn`, `start`, `end`, `transition`, `transition_s`,
          `speed`, `label`) ;
  resolve {src_key(src): {path, dur?, audio?, video?}} — une entrée par
          source RÉSOLUE ; une source absente du dict est « introuvable » ;
  meta    `_tracks_meta(rec.tracks)` de montage_service (la loi de
          classement des clips, jamais recopiée) ; absent → déduction
          minimale par l'initiale (a… audio, s… sous-titres, sinon vidéo).

EDL (CMX 3600, 30 i/s NON-DROP, CRLF)
  `TITLE:`, `FCM: NON-DROP FRAME`, puis les événements V1 (piste `V`), puis
  l'audio (première piste audio déclarée `A`, les suivantes `A2`, `A3`…).
  Bobine `AX` (fichier sans bobine), le chemin dans `* SOURCE FILE:`, le NOM
  DU FICHIER dans `* FROM CLIP NAME:` / `* TO CLIP NAME:` (la clé de
  reconnexion de Resolve et Premiere — décision de revue du 24/09/2026 ; le
  libellé de l'app passe dans `* CLIP LABEL:`). Timecodes source depuis 00:00:00:00 (les
  fichiers de l'app n'ont pas de TC embarqué) ; timecodes d'enregistrement =
  la timeline (00:00:00:00 = t 0).
  Transitions V1 : `fade`/`dissolve` (et les clés historiques `xfade`,
  `crossfade`, qui rendent un fondu — `_XFADE` de montage_service) →
  événement `D` de la durée en images, précédé de la ligne SORTANTE à
  longueur nulle (convention CMX) : le plan V1 précédent s'il est jointif,
  le noir `BL` après un trou (> 0,1 s, le seuil du rendu) ; les autres
  transitions → coupe `C` + `* TRANSITION: <nom> (non exportée)`. Le premier
  plan collé à t 0 n'a pas de transition entrante (le rendu non plus).
  Durée du fondu bornée COMME LE RENDU : ≤ durée du plan entrant − 0,1 s et
  ≤ son début − 0,1 s (le « total » du rendu), au moins une image.
  ÉCART DATÉ 24/09/2026 (revue) — FORME CMX GARDÉE : le fondu de l'EDL
  COMMENCE à la coupe et consomme `d` images de POIGNÉE du plan sortant
  au-delà de sa sortie ; le rendu, lui, pose l'xfade à `offset = total −
  tau` : il MANGE la queue du plan sortant, sans poignée. Les deux ne
  montrent donc pas les mêmes images pendant le fondu. Quand la durée
  sondée de la source sortante est connue et que `so + d·vitesse` la
  dépasse : `* HANDLES: insuffisantes (n images)` sous l'événement, n =
  images de poignée DISPONIBLES après la sortie. Durée inconnue : rien
  n'est dit. La route sonde la durée pour les DEUX formats (EDL et FCPXML)
  depuis `140c3d5` ; seule une sonde en échec laisse la durée inconnue.
  Plus de 999 événements : arrêt et `* TRUNCATED: …` (numéro sur 3 chiffres).
  Vitesse V1 (0,25..4, `_v1_speed`) : durée source = durée timeline ×
  vitesse, ligne `M2` (vitesse × 30 en i/s) + `* SPEED: <x>`.
  ÉCART DATÉ 24/09/2026 : le plan disait « M2 non émis » — il EST émis,
  parce que sans lui un logiciel qui relit l'EDL lit une durée source ≠
  durée d'enregistrement sans savoir pourquoi ; c'est la ligne standard CMX
  de l'effet de vitesse. L'import réel dans DaVinci Resolve reste à faire
  par l'UTILISATEUR (hors session).
  Cadrage D-40 (revue finale du lot, 24/09/2026) : un plan V1 au cadrage non
  centré (le verdict de `montage_service._reframe_of`, importé à l'appel) porte
  `* REFRAME: <suivi|manuel> (non exporté)` sous son événement ; en FCPXML, un
  commentaire neutralisé `REFRAME: … (non exporté en FCPXML)` suit l'asset-clip.
  Vitesse AUDIO (atempo) : `* SPEED: <x> (audio, non exportée)`, source =
  durée timeline. Piste audio en boucle (musique) : `* LOOP: non exportée`.
  Sans source (titres, sous-titres, ajustement), overlays (EDL mono-piste
  vidéo) et sources introuvables : `* SKIPPED: <genre> <libellé>` en fin de
  liste (sous-titres regroupés : `subs s1 (n segments)`).

FCPXML — VERSION « 1.9 ». SOURCE : documentation Apple lue par WebFetch le
24/09/2026 (developer.apple.com/documentation/professional-video-applications
/fcpxml-reference, pages `fcpxml`, `asset`, `timeMap`) : « FCPXML 1.9 requires
Final Cut Pro 10.4.9 or later » ; depuis 1.9 le chemin du média est porté
par l'enfant `media-rep` (`kind`, `src`) et non plus par `asset@src` ; seul
`resources` est obligatoire sous `fcpxml`. La version COURANTE d'Apple est
plus récente (1.14 d'après une recherche web du même jour, FCP 11.1 ; la page
Apple rendue en JS n'a pas livré le numéro) : 1.9 est retenue parce que
c'est la forme la plus ancienne qui a `media-rep` — relue par Final Cut Pro
récent ET par les versions de DaVinci Resolve qui plafonnent plus bas. NON
VÉRIFIÉ par un import réel (ni FCP ni Resolve dans la session).
  Forme : `resources/format` (1/30s, taille du canvas du projet) ; un
  `asset` par source (`uid` = md5 du chemin, `start` 0s, `duration` sondée
  ou, à défaut, le plus loin consommé ; `hasVideo`/`hasAudio` ;
  PAS de `format` sur l'asset — ses dimensions réelles ne sont pas connues
  ici, l'attribut est implicite) + `media-rep kind="original-media"
  src="file:///…"` ; `library/event/project/sequence/spine`.
  Spine : un `asset-clip` par plan V1 (`offset`/`start`/`duration` en
  `n/30s`, `srcEnable="video"` si la source a du son — le rendu ignore le son
  embarqué d'un plan V1), `gap` pour un trou, `gap` final si l'audio
  déborde. Vitesse ≠ 1 → `timeMap` (timept time 0s→0s, puis durée/vitesse
  → durée de l'asset, `interp="linear"`) et `start` en temps LOCAL
  (srcIn / vitesse). Audio : `asset-clip lane="-k"` (k = rang de la piste
  audio) ANCRÉ sous l'élément du spine qui couvre son début, `offset` dans
  le temps local du parent (start du parent + écart), `audioRole`
  dialogue/music/effects selon le bus, `srcEnable="audio"` si la source a
  de l'image. Transitions : NON exportées en FCPXML (un `transition` exige
  des poignées de média des deux côtés) — dites en commentaire
  `TRANSITION: <nom> <d> s (non exportée en FCPXML)`. Sauts : commentaires
  `SKIPPED: …` comme l'EDL. Tout texte de commentaire passe par
  `_commentaire` (`--` espacé, espace finale : XML 1.0 §2.5). Plans V1 qui
  se chevauchent : le suivant commence à la fin du précédent et son `start`
  avance d'autant.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

_DISSOLVES = ("fade", "dissolve", "xfade", "crossfade")
_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus",
               ".aiff", ".aif", ".wma")
_ROLES = {"dialogue": "dialogue", "musique": "music", "sfx": "effects"}
_GAP_S = 0.1       # le seuil de trou du rendu (_build_montage_command)


def src_key(src) -> str:
    """Clé stable d'une source de clip (le dict `src`), ou "" sans source."""
    if not isinstance(src, dict) or not src:
        return ""
    return json.dumps(src, sort_keys=True, ensure_ascii=False)


def _num(v, defaut=0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return defaut
    return f if math.isfinite(f) else defaut


def _speed(c) -> float:
    """La vitesse V1 telle que `_v1_speed` la lit : 0,25..4, invalide → 1."""
    f = _num(c.get("speed"), 1.0)
    if f <= 0:
        return 1.0
    f = max(0.25, min(4.0, f))
    return 1.0 if abs(f - 1.0) < 1e-6 else f


def _fmt_speed(s: float) -> str:
    return ("%.3f" % s).rstrip("0").rstrip(".")


def _trans(c) -> str:
    return (str(c.get("transition") or "cut").split() or ["cut"])[0].lower()


def _cadrage(c) -> str:
    """Le mode d'un cadrage NON centré (« suivi » | « manuel ») ou "" — le
    verdict même du rendu (`montage_service._reframe_of`, importé à l'appel :
    montage_service importe ce module)."""
    if not isinstance(c.get("reframe"), dict):
        return ""
    from app.services.montage_service import _reframe_of
    rf = _reframe_of(c)
    return rf["mode"] if rf else ""


def _libelle(c, defaut="") -> str:
    s = str(c.get("label") or c.get("text") or c.get("id") or defaut)
    return "".join(ch for ch in s if ord(ch) >= 32 and ch != "\x7f").strip()[:120]


def _meta(rec, meta) -> dict:
    if isinstance(meta, dict) and meta:
        return meta
    out = {}
    for t in rec.get("tracks") or [{"id": "v1"}, {"id": "a1"}, {"id": "a2"}, {"id": "a3"}]:
        if isinstance(t, dict) and t.get("id"):
            tid = str(t["id"])
            kind = str(t.get("kind") or {"a": "audio", "s": "subs"}.get(tid[:1], "video"))
            bus = str(t.get("bus") or {"a1": "dialogue", "a2": "musique"}.get(tid, "sfx"))
            out[tid] = {"kind": kind, "bus": bus, "loop": bool(t.get("loop")) and kind == "audio"}
    return out


def _is_video(info) -> bool:
    if "video" in info and info["video"] is not None:
        return bool(info["video"])
    return Path(str(info.get("path") or "")).suffix.lower() not in _AUDIO_EXTS


def _classer(rec, resolve, meta):
    """(v1, audio[(rang, piste, bus, loop, clip)], sauts[str]) — un clip
    n'est exporté que si sa source est RÉSOLUE."""
    m = _meta(rec, meta)
    audio_ids = [tid for tid, t in m.items() if t.get("kind") == "audio"]
    v1, aud, sauts, subs = [], [], [], {}
    for c in rec.get("clips") or []:
        if not isinstance(c, dict):
            continue
        tr = str(c.get("tr") or "")
        t = m.get(tr)
        kind = (t or {}).get("kind", "inconnu")
        if kind == "subs":
            subs[tr] = subs.get(tr, 0) + 1
            continue
        if kind in ("title", "adjust") or t is None or kind not in ("video", "audio"):
            sauts.append("%s %s" % (kind, _libelle(c, tr)))
            continue
        if kind == "video" and tr != "v1":
            sauts.append("overlay %s" % _libelle(c, tr))
            continue
        if _num(c.get("end")) - _num(c.get("start")) <= 0:
            continue
        info = resolve.get(src_key(c.get("src"))) if isinstance(resolve, dict) else None
        if not info or not info.get("path"):
            sauts.append("source introuvable %s" % _libelle(c, tr))
            continue
        if kind == "video":
            v1.append(c)
        else:
            aud.append((audio_ids.index(tr), tr, t.get("bus", "sfx"), bool(t.get("loop")), c))
    for tr, n in subs.items():
        sauts.append("subs %s (%d segment%s)" % (tr, n, "s" if n > 1 else ""))
    v1.sort(key=lambda c: _num(c.get("start")))
    aud.sort(key=lambda a: (a[0], _num(a[4].get("start"))))
    return v1, aud, sauts


def _fr(sec: float, fps: int) -> int:
    return int(round(max(0.0, sec) * fps))


# ─────────────────────────────────────────────────────────────── EDL ───

def _tc(f: int, fps: int) -> str:
    f = max(0, int(f))
    h, r = divmod(f, 3600 * fps)
    m, r = divmod(r, 60 * fps)
    s, ff = divmod(r, fps)
    return "%02d:%02d:%02d:%02d" % (h, m, s, ff)


def _ev(n, reel, piste, tr, dur, si, so, ri, ro, fps) -> str:
    return "%03d  %-8s %-5s %-4s %-3s %s %s %s %s" % (
        n, reel, piste, tr, dur, _tc(si, fps), _tc(so, fps), _tc(ri, fps), _tc(ro, fps))


def _nom_fichier(info) -> str:
    """La clé de reconnexion d'un logiciel qui relit l'EDL : le NOM du fichier."""
    return Path(str(info.get("path") or "")).name


def _poignee(info, so, besoin, fps):
    """Images de poignée DISPONIBLES après `so` (sortie source du plan
    sortant) si la durée sondée est connue et ne couvre pas `besoin`, sinon
    None (assez, ou durée inconnue : rien à dire)."""
    d = _num(info.get("dur"), 0.0)
    if d <= 0:
        return None
    dispo = _fr(d, fps) - so
    return max(0, dispo) if dispo < besoin else None


_EDL_MAX = 999     # le numéro d'événement CMX tient en trois chiffres


def to_edl(rec, resolve, fps=30, meta=None) -> str:
    fps = int(fps) if int(fps or 0) > 0 else 30
    rec = rec if isinstance(rec, dict) else {}
    titre = _libelle({"label": rec.get("name")}, "montage")[:70] or "montage"
    out = ["TITLE: " + titre, "FCM: NON-DROP FRAME", ""]
    v1, aud, sauts = _classer(rec, resolve or {}, meta)
    n = 0
    tronque = False
    prev = None                       # (clip, so, fin en s, info, vitesse)
    for c in v1:
        info = resolve[src_key(c.get("src"))]
        sp = _speed(c)
        ri, ro = _fr(_num(c.get("start")), fps), _fr(_num(c.get("end")), fps)
        if ro <= ri:
            continue
        if n >= _EDL_MAX:
            tronque = True
            break
        si = _fr(_num(c.get("srcIn")), fps)
        so = si + int(round((ro - ri) * sp))
        n += 1
        tn = _trans(c)
        debut, fin = _num(c.get("start")), _num(c.get("end"))
        trou = debut - (prev[2] if prev else 0.0) > _GAP_S
        bloc = []
        if tn in _DISSOLVES and (prev is not None or trou):
            # la durée bornée comme au rendu : tau ≤ seg − 0,1 et ≤ total − 0,1
            tau = _num(c.get("transition_s"), 0.4) or 0.4
            tau = min(tau, max(0.1, (fin - debut) - 0.1), max(0.1, debut - 0.1))
            d = max(1, min(_EDL_MAX, ro - ri, _fr(tau, fps)))
            hd = None
            if prev is not None and not trou:
                bloc.append(_ev(n, "AX", "V", "C", "", prev[1], prev[1], ri, ri, fps))
                de = _nom_fichier(prev[3])
                hd = _poignee(prev[3], prev[1], int(round(d * prev[4])), fps)
            else:
                bloc.append(_ev(n, "BL", "V", "C", "", 0, 0, ri, ri, fps))
                de = None
            bloc.append(_ev(n, "AX", "V", "D", "%03d" % d, si, so, ri, ro, fps))
            if sp != 1.0:
                bloc.append("M2   %-8s %05.1f                %s" % ("AX", fps * sp, _tc(si, fps)))
            if de is not None:
                bloc.append("* FROM CLIP NAME: " + de)
            bloc.append("* TO CLIP NAME: " + _nom_fichier(info))
            bloc.append("* CLIP LABEL: " + _libelle(c, "plan"))
            if hd is not None:
                bloc.append("* HANDLES: insuffisantes (%d images)" % hd)
        else:
            bloc.append(_ev(n, "AX", "V", "C", "", si, so, ri, ro, fps))
            if sp != 1.0:
                bloc.append("M2   %-8s %05.1f                %s" % ("AX", fps * sp, _tc(si, fps)))
            bloc.append("* FROM CLIP NAME: " + _nom_fichier(info))
            bloc.append("* CLIP LABEL: " + _libelle(c, "plan"))
            if tn not in ("cut", "") and tn not in _DISSOLVES:
                bloc.append("* TRANSITION: %s (non exportée)" % tn)
        if sp != 1.0:
            bloc.append("* SPEED: " + _fmt_speed(sp))
        rfm = _cadrage(c)
        if rfm:
            bloc.append("* REFRAME: %s (non exporté)" % rfm)
        bloc.append("* SOURCE FILE: " + str(info["path"]))
        out += bloc + [""]
        prev = (c, so, fin, info, sp)
    for rang, tr, bus, loop, c in ([] if tronque else aud):
        info = resolve[src_key(c.get("src"))]
        ri, ro = _fr(_num(c.get("start")), fps), _fr(_num(c.get("end")), fps)
        if ro <= ri:
            continue
        if n >= _EDL_MAX:
            tronque = True
            break
        si = _fr(_num(c.get("srcIn")), fps)
        n += 1
        piste = "A" if rang == 0 else "A%d" % (rang + 1)
        bloc = [_ev(n, "AX", piste, "C", "", si, si + (ro - ri), ri, ro, fps),
                "* FROM CLIP NAME: " + _nom_fichier(info),
                "* CLIP LABEL: " + _libelle(c, tr)]
        asp = _num(c.get("speed"), 1.0)
        if asp > 0 and abs(asp - 1.0) > 1e-6:
            bloc.append("* SPEED: %s (audio, non exportée)" % _fmt_speed(asp))
        if loop:
            bloc.append("* LOOP: non exportée")
        bloc.append("* SOURCE FILE: " + str(info["path"]))
        out += bloc + [""]
    if tronque:
        out += ["* TRUNCATED: plus de %d événements — la suite n'est pas exportée" % _EDL_MAX, ""]
    for s in sauts:
        out.append("* SKIPPED: " + s)
    if sauts:
        out.append("")
    return "\r\n".join(out) + "\r\n"


# ─────────────────────────────────────────────────────────── FCPXML ───

def _commentaire(txt: str):
    """Un commentaire XML SÛR : `--` est interdit dans un commentaire et un
    `-` final fermerait `--->` (XML 1.0 §2.5) — un libellé `x--y-` rendait le
    FCPXML illisible (revue du 24/09/2026). Les tirets doublés sont espacés,
    le tiret final suivi d'une espace."""
    t = str(txt)
    while "--" in t:
        t = t.replace("--", "- -")
    return ET.Comment(" " + t + " ")      # l'espace finale : jamais `-` devant `-->`


def _t(f: int, fps: int) -> str:
    return "0s" if f <= 0 else "%d/%ds" % (f, fps)


def to_fcpxml(rec, resolve, fps=30, size=(1080, 1920), meta=None) -> str:
    fps = int(fps) if int(fps or 0) > 0 else 30
    rec = rec if isinstance(rec, dict) else {}
    resolve = resolve or {}
    try:
        w, h = int(size[0]), int(size[1])
    except (TypeError, ValueError, IndexError):
        w, h = 1080, 1920
    nom = _libelle({"label": rec.get("name")}, "montage") or "montage"
    v1, aud, sauts = _classer(rec, resolve, meta)

    root = ET.Element("fcpxml", {"version": "1.9"})
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", {"id": "r1", "frameDuration": "1/%ds" % fps,
                                  "width": str(w), "height": str(h)})
    # les assets : un par source utilisée, durée = sondée ou le plus loin consommé
    besoin = {}
    for c in v1:
        k = src_key(c.get("src"))
        fin = _num(c.get("srcIn")) + (_num(c.get("end")) - _num(c.get("start"))) * _speed(c)
        besoin[k] = max(besoin.get(k, 0.0), fin)
    for a in aud:
        c = a[4]
        k = src_key(c.get("src"))
        besoin[k] = max(besoin.get(k, 0.0), _num(c.get("srcIn")) + _num(c.get("end")) - _num(c.get("start")))
    ids, adur, avid, aaud = {}, {}, {}, {}
    for i, k in enumerate(besoin):
        info = resolve[k]
        p = str(info["path"])
        rid = "r%d" % (i + 2)
        ids[k] = rid
        d = _num(info.get("dur"), 0.0)
        adur[k] = _fr(d if d > 0 else besoin[k], fps)
        avid[k] = _is_video(info)
        aaud[k] = bool(info.get("audio")) if info.get("audio") is not None else not avid[k]
        at = {"id": rid, "name": Path(p).stem, "uid": hashlib.md5(p.encode("utf-8")).hexdigest().upper(),
              "start": "0s", "duration": _t(adur[k], fps)}
        if avid[k]:
            at["hasVideo"] = "1"
        if aaud[k]:
            at.update({"hasAudio": "1", "audioSources": "1", "audioChannels": "2", "audioRate": "48000"})
        asset = ET.SubElement(res, "asset", at)
        ET.SubElement(asset, "media-rep", {"kind": "original-media", "src": Path(p).resolve().as_uri()})

    lib = ET.SubElement(root, "library")
    ev = ET.SubElement(lib, "event", {"name": "Deepotus"})
    proj = ET.SubElement(ev, "project", {"name": nom})
    seq = ET.SubElement(proj, "sequence", {"format": "r1", "duration": "0s", "tcStart": "0s",
                                           "tcFormat": "NDF", "audioLayout": "stereo", "audioRate": "48k"})
    for s in sauts:
        seq.append(_commentaire("SKIPPED: %s" % s))
    spine = ET.SubElement(seq, "spine")
    elems = []                         # (offset, durée, élément, start local, vitesse)
    cur = 0
    for c in v1:
        k = src_key(c.get("src"))
        sp = _speed(c)
        ri, ro = _fr(_num(c.get("start")), fps), _fr(_num(c.get("end")), fps)
        # chevauchement V1 : le plan commence à `cur` et sa source AVANCE d'autant
        # (revue 24/09/2026 : `start` restait sur srcIn, décalage mesuré de 6 images)
        avance = max(0, cur - ri)
        ri = max(ri, cur)
        if ro <= ri:
            continue
        if ri > cur:
            g = ET.SubElement(spine, "gap", {"name": "Trou", "offset": _t(cur, fps),
                                             "start": "0s", "duration": _t(ri - cur, fps)})
            elems.append((cur, ri - cur, g, 0, 1.0))
        tn = _trans(c)
        if tn not in ("cut", "") and elems:
            spine.append(_commentaire("TRANSITION: %s %s s (non exportée en FCPXML)" % (
                tn, _fmt_speed(_num(c.get("transition_s"), 0.4) or 0.4))))
        si = _fr(_num(c.get("srcIn")), fps)
        st = int(round(si / sp)) + avance
        at = {"ref": ids[k], "name": _libelle(c, "plan"), "offset": _t(ri, fps),
              "start": _t(st, fps), "duration": _t(ro - ri, fps)}
        if aaud[k]:
            at["srcEnable"] = "video"
        el = ET.SubElement(spine, "asset-clip", at)
        if sp != 1.0:
            tm = ET.SubElement(el, "timeMap")
            ET.SubElement(tm, "timept", {"time": "0s", "value": "0s", "interp": "linear"})
            ET.SubElement(tm, "timept", {"time": _t(int(round(adur[k] / sp)), fps),
                                         "value": _t(adur[k], fps), "interp": "linear"})
        rfm = _cadrage(c)
        if rfm:
            spine.append(_commentaire("REFRAME: %s (non exporté en FCPXML)" % rfm))
        elems.append((ri, ro - ri, el, st, sp))
        cur = ro
    fin_a = max([_fr(_num(a[4].get("end")), fps) for a in aud] or [0])
    if fin_a > cur:
        g = ET.SubElement(spine, "gap", {"name": "Trou", "offset": _t(cur, fps),
                                         "start": "0s", "duration": _t(fin_a - cur, fps)})
        elems.append((cur, fin_a - cur, g, 0, 1.0))
        cur = fin_a
    seq.set("duration", _t(cur, fps))
    for rang, tr, bus, loop, c in aud:
        k = src_key(c.get("src"))
        ri, ro = _fr(_num(c.get("start")), fps), _fr(_num(c.get("end")), fps)
        if ro <= ri:
            continue
        par = next((e for e in elems if e[0] <= ri < e[0] + e[1]), None)
        if par is None:
            continue
        at = {"ref": ids[k], "lane": str(-(rang + 1)), "name": _libelle(c, tr),
              "offset": _t(par[3] + (ri - par[0]), fps), "start": _t(_fr(_num(c.get("srcIn")), fps), fps),
              "duration": _t(ro - ri, fps), "audioRole": _ROLES.get(bus, "effects")}
        if avid[k]:
            at["srcEnable"] = "audio"
        ET.SubElement(par[2], "asset-clip", at)
    ET.indent(root, space="  ")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n'
            + ET.tostring(root, encoding="unicode") + "\n")
