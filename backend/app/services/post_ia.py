# -*- coding: utf-8 -*-
"""Post-traitement de Son & VFX : générateurs IA selon les clés (t277, 22/10/2026, plan 2026-10-21-optimisation-menus-
son-vfx.md).

Les générateurs du catalogue_ia qui TRANSFORMENT une vidéo deviennent des maillons PAYANTS de la pile de t276 (un
maillon IA : {ia: "<nature>:<modèle>", prompt, options, masque}), à côté des presets locaux :
  fal         les gestes VFX IA vidéo → vidéo sans image requise (style : Kling O3, Flux 3 ; agrandir : Topaz ; les
              autres gestes), l'interpolation d'images FILM, les bruitages vidéo → son (registre sfx_service) ;
  decart      Lucy Restyle, servi par fal (decart/lucy-restyle) ;
  elevenlabs  l'habillage sonore : ElevenLabs SFX en direct (ELEVENLABS_API_KEY) ou son jumeau par fal (FAL_KEY).
Relevé sur fal le 22/10/2026 (llms.txt de chaque modèle) : FILM `fal-ai/film/video` (video_url, num_frames 1-4 ;
0,0013 $ par seconde de CALCUL, durée inconnue d'avance → « prix à mesurer ») ; Lucy Restyle `decart/lucy-restyle`
(prompt requis, video_url ; 0,01 $ par seconde de vidéo). Aucun modèle de STABILISATION n'existe sur fal à cette date :
il n'est pas livré.

Un générateur sans clé reste LISTÉ et choisissable (décision du 11/10/2026) : le rendu est refusé en 503 au lancement,
avant la garde des plafonds. Le devis (`op_devis`) réutilise les ops de chaque registre (vfx_ia.op_vfx,
sfx_service.op_sfx, kind « post_ia » d'ici) : un seul chiffre pour le devis, la garde et le coût rangé.
Les maillons IA ne s'appliquent qu'au RENDU : l'aperçu ne montre que les maillons locaux (`locaux`). Au rendu, la
pile est découpée en étapes (`etapes`) : un groupe de presets locaux passe par post_pile.rendre, un maillon IA par
`appliquer_maillon` (le PUITS du recensement payant). Les appels réseau passent par trois coutures (`_upload`,
`_fal_subscribe`, `_download`, celles de sfx_service) et `_eleven_direct`, que les bancs remplacent.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.services import post_pile as PP

FOURNISSEURS = ("fal", "decart", "elevenlabs")
#: Longueur maximale d'une consigne de maillon IA.
PROMPT_MAX = 2000
#: Bornes de la phrase de « Décrire le look » et de la pile proposée.
PHRASE_MAX = 400
PROPOSITION_MAX = 6
#: Les bruitages texte proposés comme habillage sonore : ElevenLabs, direct puis par fal.
SFX_HABILLAGE = ("elevenlabs-direct", "elevenlabs-v2-fal")
#: La famille d'un geste VFX IA dans la section « Générer ».
_FAMILLES_VFX = {"retoucher-kling": "style", "retoucher-flux3": "style", "agrandir": "agrandir"}


def _o(choix=None, defaut=None, num=None, entier=False, bool_=False, requis=False):
    """Une option, au schéma de vfx_ia (l'écran construit ses champs d'après lui)."""
    return {"choix": tuple(choix) if choix else None, "defaut": defaut, "num": num, "entier": bool(entier),
            "bool": bool(bool_), "requis": bool(requis)}


def _m(label, fournisseur, famille, endpoint, usd, unite, prompt=None, options=None, fixe=None):
    return {"label": label, "fournisseur": fournisseur, "famille": famille, "endpoint": endpoint, "usd": usd,
            "unite": unite, "prompt": prompt, "options": dict(options or {}), "fixe": dict(fixe or {})}


# Nature « video_post » du catalogue_ia : les modèles vidéo → vidéo qu'aucun autre registre ne porte.
MODELES: dict[str, dict] = {
    "interpoler-film": _m("Interpolation d'images (FILM)", "fal", "interpolation", "fal-ai/film/video", 0.0, "video",
                          options={"num_frames": _o(num=(1, 4), defaut=1, entier=True)},
                          fixe={"use_calculated_fps": True, "video_quality": "high"}),
    "restyle-decart": _m("Restyle (Decart Lucy)", "decart", "style", "decart/lucy-restyle", 0.01, "s",
                         prompt="requis", fixe={"enhance_prompt": True}),
}


# ───────────────────────────────────────────── les générateurs ─────────────────────────────────────────────

def _cle_dispo(cle) -> bool:
    return True if not cle else bool(str(getattr(settings, cle, "") or "").strip())


def _schema(opts: dict) -> dict:
    return {k: {"choix": list(s["choix"]) if s.get("choix") else None, "defaut": s.get("defaut"),
                "num": list(s["num"]) if s.get("num") else None, "entier": bool(s.get("entier")),
                "bool": bool(s.get("bool")), "requis": bool(s.get("requis"))} for k, s in (opts or {}).items()}


def generateurs() -> list[dict]:
    """Les générateurs de la section « Générer », dans l'ordre des fournisseurs (fal, decart, elevenlabs), lus dans le
    catalogue_ia et filtrés par NATURE : gestes vfx d'entrée vidéo sans image requise, nature « video_post »,
    bruitages vidéo → son, et l'habillage ElevenLabs. Sans clé : listés quand même (dispo False, clé nommée)."""
    from app.services import catalogue_ia as CI, vfx_ia as VI
    out = []
    for e in CI.lister("vfx"):
        r = VI.REGISTRE[e["id"]]
        if r["entree"] != "video" or r["image"] == "requis":
            continue
        out.append({**_fiche(e, "fal", _FAMILLES_VFX.get(e["id"], "vfx"), r["prompt"], "video"),
                    "options": _schema(r["options"])})
    for e in CI.lister("video_post"):
        m = MODELES[e["id"]]
        out.append({**_fiche(e, m["fournisseur"], m["famille"], m["prompt"], "video"), "options": _schema(m["options"])})
    for e in CI.lister("sfx_video"):
        out.append({**_fiche(e, "fal", "son", "requis" if e.get("prompt") else "facultatif", "son"), "options": {}})
    for e in CI.lister("sfx_texte"):
        if e["id"] in SFX_HABILLAGE:
            out.append({**_fiche(dict(e, nature="sfx"), "elevenlabs", "son", "requis", "son"), "options": {}})
    rang = {f: i for i, f in enumerate(FOURNISSEURS)}
    return sorted(out, key=lambda g: rang[g["fournisseur"]])   # tri stable : l'ordre des registres est gardé


def _fiche(e: dict, fournisseur: str, famille: str, prompt, sortie: str) -> dict:
    return {"id": f"{e['nature']}:{e['id']}", "nature": e["nature"], "modele": e["id"], "fournisseur": fournisseur,
            "famille": famille, "label": e["label"], "voie": e["voie"], "cle": e["cle"], "dispo": bool(e["dispo"]),
            "usd": e["usd"], "unite": e["unite"], "note": e.get("note") or "", "prompt": prompt, "sortie": sortie}


def _ids() -> dict:
    from app.services import vfx_ia as VI, sfx_service as SX
    ids = {f"vfx:{m}": ("vfx", m) for m in VI.ids()
           if VI.REGISTRE[m]["entree"] == "video" and VI.REGISTRE[m]["image"] != "requis"}
    ids.update({f"video_post:{m}": ("video_post", m) for m in MODELES})
    ids.update({f"sfx_video:{m}": ("sfx_video", m) for m in SX.ids_sfx(SX.SFX_VIDEO)})
    ids.update({f"sfx:{m}": ("sfx", m) for m in SFX_HABILLAGE})
    return ids


def generateur(gid) -> tuple:
    """(nature, modèle) d'un id de générateur ; ValueError nommée s'il est inconnu."""
    g = _ids().get(str(gid or ""))
    if g is None:
        raise ValueError(f"générateur IA inconnu : {str(gid)[:40]!r}")
    return g


def cle(gid) -> str | None:
    """Le NOM de la clé qu'exige un générateur (FAL_KEY, ELEVENLABS_API_KEY)."""
    from app.services import sfx_service as SX
    nature, mid = generateur(gid)
    return SX.cle_sfx(mid) if nature in ("sfx", "sfx_video") else "FAL_KEY"


# ───────────────────────────────────────────────── la pile ─────────────────────────────────────────────────

def est_ia(m) -> bool:
    return isinstance(m, dict) and bool(m.get("ia"))


def normaliser(pile) -> list[dict]:
    """La pile mixte → maillons propres, dans l'ordre : un preset local passe par post_pile.normaliser, un maillon IA
    devient {id, ia, prompt, options, masque}. ValueError si elle est refusée (forme, longueur, id inconnu)."""
    if not isinstance(pile, list):
        raise ValueError("la pile doit être une liste de maillons")
    if len(pile) > PP.PILE_MAX:
        raise ValueError(f"pile trop longue : {len(pile)} maillons (au plus {PP.PILE_MAX})")
    out = []
    for m in pile:
        if not est_ia(m):
            out.extend(PP.normaliser([m]))
            continue
        generateur(m["ia"])
        p = " ".join(str(m.get("prompt") or "").split())
        if len(p) > PROMPT_MAX:
            raise ValueError(f"consigne trop longue : {len(p)} caractères (au plus {PROMPT_MAX})")
        uid = "".join(c for c in str(m.get("id") or "") if c.isalnum() or c in "-_")[:32]
        out.append({"id": uid, "ia": str(m["ia"]), "prompt": p,
                    "options": dict(m["options"]) if isinstance(m.get("options"), dict) else {},
                    "masque": bool(m.get("masque"))})
    return out


def _options_post(mid: str, options: dict) -> dict:
    sch = MODELES[mid]["options"]
    for k in options:
        if k not in sch:
            raise ValueError(f"option inconnue pour {MODELES[mid]['label']} : {str(k)[:30]!r}")
    out = {}
    for k, s in sch.items():
        v = options.get(k, s["defaut"])
        if v is None:
            continue
        if s["num"]:
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"option {k} : un nombre est attendu")
            lo, hi = s["num"]
            if math.isnan(v) or not lo <= v <= hi:
                raise ValueError(f"option {k} hors bornes ({lo}-{hi})")
            v = int(round(v)) if s["entier"] else v
        out[k] = v
    return out


def valider(pile) -> list[dict]:
    """normaliser, puis chaque maillon IA validé contre son registre : consigne requise, options du schéma complétées
    de leurs défauts. ValueError nommée sinon (la route en fait un 400)."""
    from app.services import vfx_ia as VI, sfx_service as SX
    out = []
    for m in normaliser(pile):
        if not est_ia(m):
            out.append(m)
            continue
        nature, mid = generateur(m["ia"])
        m = dict(m)
        if nature == "vfx":
            m["prompt"] = VI.prompt_valide(mid, m["prompt"]) or ""
            m["options"] = VI.options_valides(mid, m["options"])
        elif nature == "video_post":
            if MODELES[mid]["prompt"] == "requis" and not m["prompt"]:
                raise ValueError(f"{MODELES[mid]['label']} : décrivez le style voulu")
            m["options"] = _options_post(mid, m["options"])
        else:
            e = SX.entree_sfx(mid)
            if (e["prompt_requis"] or nature == "sfx") and not m["prompt"]:
                raise ValueError(f"{e['label']} : décrivez le son voulu")
            if len(m["prompt"]) > e["prompt_max"]:
                raise ValueError(f"{e['label']} : consigne trop longue (au plus {e['prompt_max']} caractères)")
            m["options"] = {}
        out.append(m)
    return out


def locaux(pile) -> list[dict]:
    """Les seuls maillons locaux, dans l'ordre : ce que montre l'aperçu."""
    return [m for m in normaliser(pile) if not est_ia(m)]


def actifs_ia(pile) -> list[dict]:
    """Les maillons IA visibles (un maillon IA masqué ne part pas, ne coûte rien)."""
    return [m for m in normaliser(pile) if est_ia(m) and not m["masque"]]


def cles_manquantes(pile) -> list[str]:
    """Les clés absentes des maillons IA visibles, chacune une fois, dans l'ordre de la pile."""
    out = []
    for m in actifs_ia(pile):
        c = cle(m["ia"])
        if c and not _cle_dispo(c) and c not in out:
            out.append(c)
    return out


def sans_cle(pile) -> tuple | None:
    """(clé, nom du générateur) du PREMIER maillon IA visible dont la clé manque — le 503 le nomme ; None sinon."""
    noms = {g["id"]: g["label"] for g in generateurs()}
    for m in actifs_ia(pile):
        c = cle(m["ia"])
        if c and not _cle_dispo(c):
            return c, noms.get(m["ia"], m["ia"])
    return None


def etapes(pile) -> list[tuple]:
    """Les étapes du rendu : ("local", [presets consécutifs]) ou ("ia", maillon). Un groupe local qui ne rend rien
    (tout masqué ou à 0 %) et un maillon IA masqué sont écartés."""
    out, groupe = [], []

    def _vider():
        if groupe and PP.effets(groupe):
            out.append(("local", list(groupe)))
        groupe.clear()

    for m in pile:
        if est_ia(m):
            _vider()
            if not m["masque"]:
                out.append(("ia", m))
        else:
            groupe.append(m)
    _vider()
    return out


def refus_source(pile, chemin, secondes, dims=(None, None), octets=None) -> str | None:
    """La raison nommée pour laquelle un maillon IA refuse la source (format, durée, taille), None si elle passe."""
    from app.services import vfx_ia as VI, sfx_service as SX
    for m in actifs_ia(pile):
        nature, mid = generateur(m["ia"])
        r = None
        if nature == "vfx":
            r = VI.source_refusee(mid, chemin, secondes, m["options"], dims, octets)
        elif nature == "sfx_video":
            r = SX.video_refusee(mid, chemin, secondes)
        if r:
            return r
    return None


# ───────────────────────────────────────────────── le devis ─────────────────────────────────────────────────

def duree_habillage(secondes) -> float:
    """La durée d'un habillage sonore ElevenLabs : celle de la vidéo, bornée à 0,5-22 s."""
    return round(max(0.5, min(22.0, float(secondes or 0) or 0.5)), 3)


def op_maillon(m: dict, secondes, largeur=None, hauteur=None) -> dict:
    """L'op de devis d'UN maillon IA validé, celle de son registre."""
    from app.services import vfx_ia as VI, sfx_service as SX
    nature, mid = generateur(m["ia"])
    if nature == "vfx":
        return VI.op_vfx(mid, secondes, m["options"], largeur, hauteur)
    if nature == "video_post":
        return {"kind": "post_ia", "modele": mid, "secondes": round(float(secondes or 0), 3)}
    if nature == "sfx_video":
        return SX.op_sfx(mid, secondes)
    d = duree_habillage(secondes)
    return {"kind": "sfx", "duration_s": d} if mid == "elevenlabs-direct" else SX.op_sfx(mid, d)


def op_devis(pile, secondes, largeur=None, hauteur=None) -> dict:
    """L'op de devis de la pile : une part par maillon IA ACTIF (composition) — lu par /devis ET par la garde."""
    return {"kind": "composition", "parts": [op_maillon(m, secondes, largeur, hauteur) for m in actifs_ia(pile)]}


def ligne(op: dict) -> dict:
    """UNE ligne de pricing.estimate pour le kind « post_ia » (registre MODELES)."""
    from app.i18n import Message, Nom
    from app.services.pricing import _line
    mid = str(op.get("modele") or "")
    e = MODELES.get(mid)
    if e is None:
        return _line("fal", f"Post IA : modèle inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    nom = Nom(mid, e["label"])
    if e["unite"] == "s":
        s = max(0.0, float(op.get("secondes") or 0))
        return _line("fal", nom if e["usd"] else Message("pricing.a_mesurer", label=nom), s, "s", s * e["usd"])
    return _line("fal", nom if e["usd"] else Message("pricing.a_mesurer", label=nom), 1, "video", e["usd"])


# ───────────────────────────────────────────────── le tir ─────────────────────────────────────────────────

async def _upload(path: Path) -> str:                               # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._upload(path)


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._fal_subscribe(endpoint, arguments)


async def _download(url: str, dest: Path) -> None:                  # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    await _S._download(url, dest)


def _eleven_direct(prompt: str, duree: float):                      # couture : ElevenLabs SFX en direct (bloquant)
    from app.services import sfx_service as _S
    return _S.generate_sfx(prompt, duree)


async def appliquer_post(mid: str, video: Path, prompt: str, options: dict, dossier: Path) -> Path:
    """Tire UN modèle de la nature « video_post » (FILM, Lucy Restyle) et range la vidéo rendue dans `dossier`.
    PAYANT : la route a passé la clé (503) et la garde des plafonds AVANT."""
    from app.services.vfx_ia import _url_video
    e = MODELES[mid]
    args = dict(e["fixe"])
    args["video_url"] = await _upload(Path(video))
    if e["prompt"] and prompt:
        args["prompt"] = prompt
    args.update(options or {})
    res = await _fal_subscribe(e["endpoint"], args)
    u = _url_video(res)
    if not u:
        cles = ", ".join(map(str, res)) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"fal.ai ({e['label']}) : aucune vidéo dans la réponse (clés : {cles})")
    dest = Path(dossier) / f"postia_{uuid4().hex[:8]}.mp4"
    await _download(u, dest)
    return dest


def _ff(nom="ffmpeg") -> str:
    from app.services.sfx_service import _bin
    return _bin(nom)


def mixer_son(video: Path, son: Path, dest: Path) -> Path:
    """La vidéo avec le son posé dessous (ffmpeg local) : mélangé au son d'origine s'il y en a un, prolongé ou coupé à
    la durée de la vidéo. RuntimeError si ffmpeg échoue."""
    i = PP.infos(video)
    dur = f"{max(0.04, float(i['dur'] or 0)):.3f}"
    graphe = ("[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" if i.get("audio")
              else "[1:a]apad[a]")
    cmd = [_ff(), "-y", "-v", "error", *PP._decodeur(Path(video)), "-i", str(video), "-i", str(son),
           "-filter_complex", graphe, "-map", "0:v", "-map", "[a]", "-t", dur,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not Path(dest).is_file():
        der = (r.stderr or "").strip().splitlines()
        raise RuntimeError(f"habillage sonore impossible : {der[-1][:200] if der else 'sortie vide'}")
    return Path(dest)


async def habiller(mid: str, video: Path, prompt: str, secondes, dossier: Path) -> Path:
    """L'habillage sonore : le son généré (ElevenLabs direct ou par fal, ou un bruitage vidéo → son de fal) posé sous
    la vidéo. PAYANT : la route a passé la clé et la garde AVANT."""
    from app.services import sfx_service as SX
    loop = asyncio.get_running_loop()
    e = SX.entree_sfx(mid)
    if mid == "elevenlabs-direct":
        items, _ = await loop.run_in_executor(None, _eleven_direct, prompt, duree_habillage(secondes))
    elif e["nature"] == SX.SFX_TEXTE:
        items = (await SX.generer_sfx(mid, prompt=prompt, duree=duree_habillage(secondes)))["items"]
    else:
        items = (await SX.generer_sfx(mid, prompt=prompt or None, video=Path(video), dossier_video=Path(dossier)))["items"]
    if not items:
        raise RuntimeError(f"{e['label']} : aucun son rendu")
    son = SX._audio_dir() / items[0]["filename"]
    dest = Path(dossier) / f"habille_{uuid4().hex[:8]}.mp4"
    return await asyncio.to_thread(mixer_son, Path(video), son, dest)


async def appliquer_maillon(m: dict, video: Path, secondes, dossier: Path) -> Path:
    """Applique UN maillon IA validé à la vidéo courante et rend la vidéo produite (dans `dossier`). PAYANT."""
    from app.services import vfx_ia as VI
    nature, mid = generateur(m["ia"])
    if nature == "vfx":
        res = await VI.appliquer_vfx(mid, video=Path(video), prompt=m["prompt"] or None, options=m["options"],
                                     secondes=secondes, dossier=Path(dossier))
        return await asyncio.to_thread(garder_son, Path(video), Path(res["video"]), Path(dossier))
    if nature == "video_post":
        sortie = await appliquer_post(mid, Path(video), m["prompt"], m["options"], Path(dossier))
        return await asyncio.to_thread(garder_son, Path(video), sortie, Path(dossier))
    return await habiller(mid, Path(video), m["prompt"], secondes, Path(dossier))


def garder_son(entree: Path, sortie: Path, dossier: Path) -> Path:
    """Un générateur d'image qui rend une vidéo MUETTE (Topaz, FILM…) ne fait pas perdre le son de la pile : la piste
    son de l'entrée est reposée sur la sortie (ffmpeg local, image copiée). Sortie rendue telle quelle sinon."""
    try:
        if not PP.infos(entree).get("audio") or PP.infos(sortie).get("audio"):
            return sortie
    except (ValueError, OSError, subprocess.SubprocessError):
        return sortie
    dest = Path(dossier) / f"son_{uuid4().hex[:8]}.mp4"
    cmd = [_ff(), "-y", "-v", "error", "-i", str(sortie), "-i", str(entree), "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return dest if r.returncode == 0 and dest.is_file() and dest.stat().st_size else sortie


def finaliser(src: Path, dest: Path) -> Path:
    """La dernière vidéo de la chaîne → `dest` en MP4 H.264 (copiée telle quelle si elle en est déjà un)."""
    src, dest = Path(src), Path(dest)
    if src.suffix.lower() == ".mp4":
        shutil.copyfile(src, dest)
        return dest
    cmd = [_ff(), "-y", "-v", "error", *PP._decodeur(src), "-i", str(src), "-map", "0:v", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac",
           "-movflags", "+faststart", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0 or not dest.is_file():
        der = (r.stderr or "").strip().splitlines()
        raise RuntimeError(f"rendu impossible : {der[-1][:200] if der else 'sortie vide'}")
    return dest


# ───────────────────────────────────────────── décrire le look ─────────────────────────────────────────────

def systeme_decrire() -> str:
    """La consigne système de « Décrire le look » : le catalogue des presets LOCAUX, leurs réglages et le format JSON."""
    from app.services import effects_engine as FX
    lignes = []
    for p in FX.post_catalogue():
        reg = []
        for k, b in (p.get("bounds") or {}).items():
            if b.get("type") == "range":
                reg.append(f"{k} {b.get('min')}..{b.get('max')}")
            elif b.get("type") == "choice":
                reg.append(f"{k} in {'|'.join(map(str, b.get('choices') or []))}")
            elif b.get("type") == "color":
                reg.append(f"{k} #rrggbb")
        lignes.append(f"- {p['id']} ({p['cat']})" + (f" params: {', '.join(reg)}" if reg else ""))
    return ("You are a film colorist. Turn the user's description of a look into a post-processing stack made ONLY of "
            "these local presets, applied in order:\n" + "\n".join(lignes) +
            f"\nUse at most {PROPOSITION_MAX} presets. Answer with JSON only: "
            '{"pile": [{"preset": "<id>", "intensite": 0-100, "params": {}}]}')


def _json_de(texte: str):
    t = str(texte or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    # l'objet ou la liste qui OUVRE le texte d'abord (une liste nue contient des objets)
    for o, f in sorted((("{", "}"), ("[", "]")), key=lambda c: t.find(c[0]) if c[0] in t else len(t)):
        i, j = t.find(o), t.rfind(f)
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                continue
    return None


def pile_proposee(texte: str) -> list[dict]:
    """La réponse du moteur → une pile de presets LOCAUX valide : presets inconnus écartés, intensités bornées par
    post_pile.normaliser, au plus PROPOSITION_MAX maillons. ValueError si rien n'est lisible."""
    from app.services import effects_engine as FX
    d = _json_de(texte)
    brut = d.get("pile") if isinstance(d, dict) else d
    if not isinstance(brut, list):
        raise ValueError("réponse du moteur illisible : aucune pile")
    pile = []
    for m in brut:
        if not isinstance(m, dict) or str(m.get("preset") or "") not in FX.POST_PILE:
            continue
        pile.append({"preset": m["preset"], "intensite": m.get("intensite", PP.INTENSITE_DEFAUT),
                     "params": m.get("params") if isinstance(m.get("params"), dict) else {}})
        if len(pile) >= PROPOSITION_MAX:
            break
    if not pile:
        raise ValueError("réponse du moteur illisible : aucun preset connu")
    return [{"preset": m["preset"], "intensite": m["intensite"], "masque": False, "params": m["params"]}
            for m in PP.normaliser(pile)]
