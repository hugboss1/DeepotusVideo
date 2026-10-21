"""Atelier sonore — moteur de graphe audio (t270, 21/10/2026, plan 2026-10-21-optimisation-menus-son-vfx.md).

Un graphe {noeuds: [{id, type, params}], liens: [{de, vers, entree}]} est VALIDÉ (types, ports, cycle, une sortie,
sources présentes dans le dossier audio, paramètres ramenés dans leurs bornes) puis COMPILÉ en un seul
filter_complex ffmpeg, local et gratuit :
  - source    0 entrée   un fichier du dossier audio, mis au format commun (44,1 kHz, stéréo, flottant) ;
  - effet     1 entrée   un module du vocabulaire FX partagé avec le Montage (sfx_service._FX_PARAMS / _FX_BUILD) ;
  - gain, pan, tempo, hauteur, decalage   1 entrée ;
  - limiteur, chorus, flanger             1 entrée (t271) ;
  - plage     1 entrée   couper (début, fin), boucler, fondus d'entrée et de sortie ;
  - mix       2 à 8 entrées (amix, durée la plus longue, sans normalisation) ;
  - duck      2 entrées  principal, déclencheur (la chaîne de ducking partagée, sfx_service.ducking_filter) ;
  - sortie    1 entrée   une seule par graphe.
Seuls les ancêtres de la sortie sont compilés ; les autres nœuds (édition en cours sur le canevas) sont IGNORÉS et
listés. Une sortie lue par plusieurs nœuds passe par `asplit`. Un nœud neutre rend `anull`, jamais un fragment vide.
Refus : ValueError au message français (traduit à la sortie par i18n_l10_erreurs), la route rend 400.
Bloquantes : `rendre` et `apercu` lancent ffmpeg (à appeler en exécuteur) ; la ROUTE note la lignée (LI.noter).
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.services import sfx_service as SX

MAX_NOEUDS = 64
MAX_LIENS = 128
MAX_SOURCES = 16
APERCU_S = 10.0                  # longueur d'un aperçu
DUREE_MAX_S = 1800.0             # un rendu ne dépasse jamais 30 min
TAUX = 44100
FMT = f"aresample={TAUX},aformat=sample_fmts=fltp:sample_rates={TAUX}:channel_layouts=stereo"
_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}

# type → (entrées, {param: (lo, hi, défaut)}) ; « mix » lit son nombre d'entrées dans ses paramètres.
_TYPES: dict[str, tuple[int, dict[str, tuple[float, float, float]]]] = {
    "source": (0, {}),
    "effet": (1, {}),
    "gain": (1, {"db": (-40.0, 12.0, 0.0)}),
    "pan": (1, {"pan": (-100.0, 100.0, 0.0)}),
    "tempo": (1, {"facteur": (0.5, 2.0, 1.0)}),
    "hauteur": (1, {"demi_tons": (-12.0, 12.0, 0.0)}),
    "plage": (1, {"debut": (0.0, 3600.0, 0.0), "fin": (0.0, 3600.0, 0.0), "boucles": (1.0, 16.0, 1.0),
                  "fondu_entree": (0.0, 30.0, 0.0), "fondu_sortie": (0.0, 30.0, 0.0)}),
    "decalage": (1, {"secondes": (0.0, 600.0, 0.0)}),
    "mix": (2, {"entrees": (2.0, 8.0, 2.0)}),
    "duck": (2, {"ratio": (2.0, 20.0, 6.0), "attack_ms": (5.0, 500.0, 50.0), "release_ms": (50.0, 2000.0, 400.0),
                 "threshold": (0.01, 0.3, 0.05)}),
    "sortie": (1, {}),
    # t271 (écarts de t270 repris) : limiteur, chorus, flanger — bornes de ffmpeg (alimiter, chorus, flanger)
    "limiteur": (1, {"plafond_db": (-24.0, 0.0, -1.0), "attaque_ms": (0.1, 80.0, 5.0), "relache_ms": (1.0, 8000.0, 50.0)}),
    "chorus": (1, {"retard_ms": (20.0, 100.0, 40.0), "vitesse_hz": (0.1, 5.0, 0.5), "profondeur_ms": (0.5, 10.0, 2.0),
                   "melange": (0.0, 100.0, 50.0)}),
    "flanger": (1, {"retard_ms": (0.0, 30.0, 0.0), "profondeur_ms": (0.0, 10.0, 2.0), "retour": (-95.0, 95.0, 0.0),
                    "melange": (0.0, 100.0, 71.0), "vitesse_hz": (0.1, 10.0, 0.5)}),
}
_ENTIERS = {("mix", "entrees"), ("plage", "boucles")}


def catalogue() -> dict:
    """Ce que le canevas (t271) affiche : types, entrées, bornes ; les effets = le vocabulaire FX partagé."""
    return {"noeuds": [{"type": t, "entrees": e, "sorties": 0 if t == "sortie" else 1,
                        "params": {k: list(b) for k, b in p.items()}} for t, (e, p) in _TYPES.items()],
            "effets": {fx: {k: list(b) for k, b in p.items()} for fx, p in SX._FX_PARAMS.items()},
            "modes_filtre": sorted(SX._FILTER_MODES)}


def _borne(v, lo: float, hi: float, dv: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dv
    if not math.isfinite(f):
        return dv
    return max(lo, min(hi, f))


def _params(nid: str, typ: str, brut: dict) -> dict:
    if typ == "source":
        nom = Path(str(brut.get("fichier") or "")).name
        p = SX._audio_dir() / nom
        if not nom or p.suffix.lower() not in _EXTS or not p.is_file():
            raise ValueError(f"source introuvable : {nom or '?'} (nœud {nid})")
        return {"fichier": nom}
    if typ == "effet":
        fx = str(brut.get("fx") or "").strip().lower()
        if fx not in SX._FX_PARAMS:
            raise ValueError(f"effet inconnu : {fx or '?'} (nœud {nid})")
        norm = SX.sanitize_fx([{"type": fx, "params": brut}])
        return {"fx": fx, **norm[0]["params"]}
    out = {}
    for k, (lo, hi, dv) in _TYPES[typ][1].items():
        v = _borne(brut.get(k, dv), lo, hi, dv)
        out[k] = int(round(v)) if (typ, k) in _ENTIERS else v
    if typ == "plage":
        if out["fin"] and out["fin"] <= out["debut"]:
            raise ValueError(f"plage : la fin doit suivre le début (nœud {nid})")
        if not out["fin"] and (out["boucles"] > 1 or out["fondu_sortie"] > 0):
            raise ValueError(f"plage : une fin est requise pour boucler ou fondre en sortie (nœud {nid})")
    return out


def valider(graphe) -> dict:
    """→ {graphe (normalisé), params {id: …}, ordre [ids des ancêtres de la sortie, ordre topologique], ignores,
    sources [fichiers, ordre des entrées ffmpeg], liens {id: [(de, entree)…]}}. ValueError sinon."""
    if not isinstance(graphe, dict):
        raise ValueError("graphe : objet attendu ({noeuds, liens})")
    noeuds = graphe.get("noeuds") if isinstance(graphe.get("noeuds"), list) else []
    liens = graphe.get("liens") if isinstance(graphe.get("liens"), list) else []
    if len(noeuds) > MAX_NOEUDS:
        raise ValueError(f"graphe : {MAX_NOEUDS} nœuds au plus")
    if len(liens) > MAX_LIENS:
        raise ValueError(f"graphe : {MAX_LIENS} liens au plus")
    types, ids = {}, []
    for n in noeuds:
        nid = str((n or {}).get("id") or "") if isinstance(n, dict) else ""
        if not _ID.match(nid) or nid in types:
            raise ValueError(f"nœud : id manquant, mal formé ou en double ({nid or '?'})")
        typ = str(n.get("type") or "")
        if typ not in _TYPES:
            raise ValueError(f"nœud {nid} : type inconnu ({typ or '?'})")
        types[nid] = typ
        ids.append(nid)
    sorties = [i for i in ids if types[i] == "sortie"]
    if len(sorties) != 1:
        raise ValueError("graphe : une sortie et une seule")
    entrants: dict[str, dict[int, str]] = {i: {} for i in ids}
    for l in liens:
        if not isinstance(l, dict):
            raise ValueError("lien mal formé")
        de, vers = str(l.get("de") or ""), str(l.get("vers") or "")
        if de not in types or vers not in types:
            raise ValueError(f"lien vers un nœud inconnu ({de or '?'} → {vers or '?'})")
        try:
            e = int(l.get("entree", 0))
        except (TypeError, ValueError):
            e = -1
        if types[de] == "sortie":
            raise ValueError(f"nœud {de} : la sortie n'a pas de sortie")
        if e in entrants[vers]:
            raise ValueError(f"nœud {vers} : entrée {e} déjà reliée")
        entrants[vers][e] = de
    # ancêtres de la sortie : seuls eux sont validés en détail et compilés
    utiles, pile = set(), [sorties[0]]
    while pile:
        x = pile.pop()
        if x not in utiles:
            utiles.add(x)
            pile.extend(entrants[x].values())
    params = {}
    for i in ids:
        if i not in utiles:
            continue
        brut = next(n for n in noeuds if n.get("id") == i).get("params")
        params[i] = _params(i, types[i], brut if isinstance(brut, dict) else {})
        attendu = params[i]["entrees"] if types[i] == "mix" else _TYPES[types[i]][0]
        for e in entrants[i]:
            if not 0 <= e < attendu:
                raise ValueError(f"nœud {i} : entrée {e} hors bornes (0 à {attendu - 1})")
        for e in range(attendu):
            if e not in entrants[i]:
                raise ValueError(f"nœud {i} : entrée {e} libre")
    # ordre topologique stable (ordre de la liste à égalité) ; un reste = un cycle
    deg = {i: len(entrants[i]) for i in utiles}
    ordre = []
    pret = [i for i in ids if i in utiles and deg[i] == 0]
    while pret:
        x = pret.pop(0)
        ordre.append(x)
        for i in ids:
            if i in utiles and x in entrants[i].values():
                deg[i] -= list(entrants[i].values()).count(x)
                if deg[i] == 0:
                    pret.append(i)
                    pret.sort(key=ids.index)
    if len(ordre) != len(utiles):
        raise ValueError("graphe : cycle (un nœud dépend de lui-même)")
    sources = [params[i]["fichier"] for i in ordre if types[i] == "source"]
    if len(sources) > MAX_SOURCES:
        raise ValueError(f"graphe : {MAX_SOURCES} sources au plus")
    norm = {"noeuds": [{"id": i, "type": types[i], "params": params.get(i, {})} for i in ids if i in utiles],
            "liens": [{"de": de, "vers": v, "entree": e} for v in ids if v in utiles
                      for e, de in sorted(entrants[v].items())]}
    return {"ok": True, "graphe": norm, "params": params, "types": {i: types[i] for i in utiles}, "ordre": ordre,
            "ignores": [i for i in ids if i not in utiles], "sources": sources,
            "entrants": {i: entrants[i] for i in utiles}}


def _frag(typ: str, p: dict) -> str:
    """Le filtre d'un nœud à une ou deux entrées ; "" = neutre (rendu « anull »)."""
    g = SX._g
    if typ == "effet":
        fx = p["fx"]
        prm = {k: v for k, v in p.items() if k != "fx"}
        return SX._fx_denoise(prm) if fx == "denoise" else SX._FX_BUILD[fx](prm)
    if typ == "gain":
        return f"volume={g(p['db'])}dB" if abs(p["db"]) >= 0.05 else ""
    if typ == "pan":
        if abs(p["pan"]) < 0.5:
            return ""
        gl, gr = SX.pan_gains(p["pan"] / 100.0)
        return f"pan=stereo|c0={g(gl)}*c0|c1={g(gr)}*c1"
    if typ == "tempo":
        return f"atempo={g(p['facteur'])}" if abs(p["facteur"] - 1.0) >= 1e-3 else ""
    if typ == "hauteur":
        if abs(p["demi_tons"]) < 0.01:
            return ""
        rr = 2.0 ** (p["demi_tons"] / 12.0)
        return f"asetrate={int(round(TAUX * rr))},aresample={TAUX},atempo={g(1.0 / rr)}"
    if typ == "decalage":
        ms = int(round(p["secondes"] * 1000))
        return f"adelay={ms}:all=1" if ms > 0 else ""
    if typ == "plage":
        a, b, n = p["debut"], p["fin"], p["boucles"]
        parts = []
        if a > 0 or b > 0:
            parts.append(f"atrim=start={g(a)}" + (f":end={g(b)}" if b > 0 else "") + ",asetpts=PTS-STARTPTS")
        if n > 1:
            parts.append(f"aloop=loop={n - 1}:size={int(round((b - a) * TAUX))},asetpts=PTS-STARTPTS")
        if p["fondu_entree"] > 0:
            parts.append(f"afade=t=in:st=0:d={g(p['fondu_entree'])}")
        if p["fondu_sortie"] > 0:
            total = (b - a) * n
            fo = min(p["fondu_sortie"], total)
            parts.append(f"afade=t=out:st={g(max(0.0, total - fo))}:d={g(fo)}")
        return ",".join(parts)
    if typ == "limiteur":
        # niveau automatique coupé (level=0) : sinon alimiter remonte le signal au plafond
        return (f"alimiter=limit={g(max(0.0625, 10 ** (p['plafond_db'] / 20.0)))}:attack={g(p['attaque_ms'])}"
                f":release={g(p['relache_ms'])}:level=0")
    if typ == "chorus":
        if p["melange"] < 0.5:
            return ""
        return (f"chorus=0.7:0.9:{g(p['retard_ms'])}:{g(p['melange'] / 100.0)}:{g(p['vitesse_hz'])}"
                f":{g(p['profondeur_ms'])}")
    if typ == "flanger":
        if p["melange"] < 0.5:
            return ""
        return (f"flanger=delay={g(p['retard_ms'])}:depth={g(p['profondeur_ms'])}:regen={g(p['retour'])}"
                f":width={g(p['melange'])}:speed={g(p['vitesse_hz'])}")
    if typ == "mix":
        return f"amix=inputs={p['entrees']}:duration=longest:normalize=0"
    if typ == "duck":
        return SX.ducking_filter(SX.parse_ducking({"ratio": p["ratio"], "attack_ms": p["attack_ms"],
                                                   "release_ms": p["release_ms"], "threshold": p["threshold"]}))
    return ""


def compiler(v: dict) -> dict:
    """Graphe VALIDÉ → {filtre, entrees [Path], sortie "[sortie]"}. Étiquettes n<rang topologique>."""
    ordre, types, params, entrants = v["ordre"], v["types"], v["params"], v["entrants"]
    rang = {i: k for k, i in enumerate(ordre)}
    # lecteurs de chaque nœud, dans l'ordre où ils sont compilés (puis par entrée)
    lecteurs = {i: sorted(((rang[c], e) for c in ordre for e, de in entrants[c].items() if de == i)) for i in ordre}
    pris: dict[str, int] = {i: 0 for i in ordre}

    def lire(i: str) -> str:
        if len(lecteurs[i]) > 1:
            k = pris[i]
            pris[i] += 1
            return f"[n{rang[i]}_{k}]"
        return f"[n{rang[i]}]"

    def poser(i: str) -> str:
        k = len(lecteurs[i])
        if k > 1:
            return f",asplit={k}" + "".join(f"[n{rang[i]}_{j}]" for j in range(k))
        return f"[n{rang[i]}]"

    parts, entrees = [], []
    for i in ordre:
        t = types[i]
        if t == "source":
            parts.append(f"[{len(entrees)}:a]{FMT}{poser(i)}")
            entrees.append(SX._audio_dir() / params[i]["fichier"])
            continue
        if t != "duck":
            ins = "".join(lire(entrants[i][e]) for e in sorted(entrants[i]))
        else:
            # sidechaincompress s'arrête avec la plus courte de ses entrées : le déclencheur (une voix) prolongé par
            # du silence laisse le principal (la musique) jouer jusqu'au bout — comme l'apad du Montage
            princ, decl = lire(entrants[i][0]), lire(entrants[i][1])
            parts.append(f"{decl}apad[n{rang[i]}_sc]")
            ins = f"{princ}[n{rang[i]}_sc]"
        if t == "sortie":
            parts.append(f"{ins}anull[sortie]")
            continue
        f = _frag(t, params[i]) or "anull"
        parts.append(f"{ins}{f}{poser(i)}")
    return {"filtre": ";".join(parts), "entrees": entrees, "sortie": "[sortie]"}


def _ffmpeg(entrees: list[Path], filtre: str, carte: str, dest: Path, extra: list[str], delai: float) -> None:
    cmd = [SX._bin("ffmpeg"), "-y", "-hide_banner", "-v", "error"]
    for p in entrees:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex", filtre, "-map", carte, *extra, str(dest)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai)
    except (OSError, subprocess.TimeoutExpired) as e:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"rendu de l'atelier impossible : {e}") from e
    if r.returncode != 0 or not dest.is_file():
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"rendu de l'atelier impossible : {(r.stderr or '')[-300:]}")


def _slug(nom: str) -> str:
    s = unicodedata.normalize("NFKD", str(nom or "")[:40]).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def rendre(graphe, nom: str = "") -> dict:
    """Rendu complet en MP3 192 kbit/s dans le dossier audio : atelier_<nom>.mp3 (jamais d'écrasement), sidecar
    kind « atelier » (parents = les sources, graphe normalisé). Gratuit. Bloquante."""
    v = valider(graphe)
    c = compiler(v)
    d = SX._audio_dir()
    base = f"atelier_{_slug(nom) or _slug(Path(v['sources'][0]).stem)[:24] or 'piste'}"
    out, k = d / f"{base}.mp3", 2
    while out.exists():
        out, k = d / f"{base}_{k}.mp3", k + 1
    tmp = out.with_name(out.name + ".part")
    _ffmpeg(c["entrees"], c["filtre"], c["sortie"], tmp,
            ["-t", str(int(DUREE_MAX_S)), "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3"], 600)
    os.replace(tmp, out)
    dur = SX._probe_duration(out)
    SX.record_meta(out.name, {"kind": "atelier", "parents": v["sources"], "graphe": v["graphe"], "dur": dur,
                              "created": datetime.now().isoformat(timespec="seconds")})
    return {"ok": True, "filename": out.name, "url": f"/api/audio/{out.name}", "dur": round(dur, 2),
            "parent": v["sources"][0], "relation": "atelier", "usd": 0.0, "ignores": v["ignores"]}


def apercu(graphe, depuis: float = 0.0) -> Path:
    """Aperçu de 10 s au plus à partir de `depuis`, mono 22,05 kHz, MP3 96 kbit/s, dans un dossier temporaire des
    sorties (jamais dans la Bibliothèque) ; l'appelant le supprime après l'envoi. Gratuit. Bloquante."""
    v = valider(graphe)
    c = compiler(v)
    a = _borne(depuis, 0.0, DUREE_MAX_S, 0.0)
    filtre = (c["filtre"] + f";[sortie]atrim=start={SX._g(a)}:duration={SX._g(APERCU_S)},asetpts=PTS-STARTPTS,"
              "aresample=22050,aformat=channel_layouts=mono[apercu]")
    dossier = Path(settings.outputs_path) / "atelier_apercus"
    dossier.mkdir(parents=True, exist_ok=True)
    dest = dossier / f"apercu_{uuid.uuid4().hex[:10]}.mp3"
    _ffmpeg(c["entrees"], filtre, "[apercu]", dest, ["-c:a", "libmp3lame", "-b:a", "96k", "-f", "mp3"], 180)
    return dest
