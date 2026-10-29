# -*- coding: utf-8 -*-
"""t335 (A5 du lot Scenario, 28/10/2026) — « Previs → plan » : le clip de previs d'un plan (@Video1) et ses style
frames (@Image1…) deviennent la vidéo du plan par Seedance 2.5 reference-to-video (fal), ou ses style frames seules
par Veo 3.1 reference-to-video. Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A5.

Partage des rôles :
  - `video_refs` (PUR) : le registre, l'argument fal, le prix, les bornes du clip ;
  - ce module : la sonde du clip (ffprobe), le PROMPT par défaut, le calcul du devis (même chiffre pour le devis
    gratuit, la garde des plafonds et l'usd rendu), le CONFORM (t336 / A6, `conformer_clip` : étirer puis
    ré-accélérer, compléter au noir puis couper, transcoder), le RECALAGE mesuré après le rendu (`recaler`) et le tir ;
  - la route (api/routes.py, /shots/{id}/previs…) : le plan, les fichiers confinés, 503 clé, 409 sans `confirme_cout`,
    plafonds « chapitres », job, Bibliothèque (provenance + recette).
AUCUN appel réseau hors des trois coutures `_upload`, `_fal_subscribe`, `_download` (celles de sfx_service, que les
bancs remplacent). Le tir `tirer_previs` est PAYANT : la route a passé la clé, la confirmation et la garde AVANT."""
from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings
from app.services import video_refs as VR

PROMPT_MAX = 2000
EXT_IMAGE = (".png", ".jpg", ".jpeg", ".webp")
EXT_CLIP = (".mp4", ".mov", ".m4v", ".mkv", ".webm")   # acceptés en ENTRÉE de la route ; le registre filtre ensuite


def infos_clip(path: Path) -> dict:
    """{secondes, largeur, hauteur, fps, octets, images, fps_r} du clip (ffprobe) ; des None quand la sonde échoue.
    t336 : `images` = le nombre d'images de la piste VIDÉO (paquets comptés : la durée du conteneur ment, piège de
    templates-coupe-fps) et `fps_r` la cadence exacte en fraction (« 24000/1001 »), que le recalage réutilise."""
    out = {"secondes": None, "largeur": None, "hauteur": None, "fps": None, "octets": None, "images": None,
           "fps_r": None}
    try:
        out["octets"] = Path(path).stat().st_size
    except OSError:
        return out
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate,nb_read_packets:format=duration", "-of", "json",
                            str(path)], capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        out["largeur"], out["hauteur"] = int(st.get("width") or 0) or None, int(st.get("height") or 0) or None
        num, _, den = str(st.get("r_frame_rate") or "0/1").partition("/")
        out["fps"] = round(float(num) / float(den or 1), 3) if float(den or 1) else None
        out["fps_r"] = f"{int(num)}/{int(den or 1)}" if out["fps"] else None
        out["images"] = int(st.get("nb_read_packets") or 0) or None
        out["secondes"] = round(float((d.get("format") or {}).get("duration") or 0), 3) or None
    except (ValueError, TypeError, OSError, subprocess.TimeoutExpired, ZeroDivisionError):
        pass
    return out


# ───────────────────── t336 (A6) : conform AVANT l'envoi, recalage APRÈS le rendu ─────────────────────
# Un modèle vidéo rend au moins `video_refs.plancher_s` secondes (Seedance 4 s, MiniMax 5 s). Un clip de previs plus
# court est donc CONFORMÉ avant l'envoi, de l'une de deux façons, au choix (dans la boîte « Previs → plan ») :
#   - « etirer » : ralenti ×k (k = plancher / durée) puis le RENDU ré-accéléré ×k — le mouvement garde sa forme ;
#   - « noir »   : complété d'images noires jusqu'au plancher, puis le rendu COUPÉ à la longueur de la previs.
# Choix automatique : « etirer » jusqu'à k ≤ 2 (un ralenti modéré se rend bien), « noir » au-delà (un ralenti ×4
# déforme le mouvement que le modèle doit garder). Une cadence hors 24-60 i/s ou un conteneur autre que MP4/MOV sont
# TRANSCODÉS (même durée). Le devis suit tout seul : il est calculé sur les secondes ENVOYÉES (le plancher).
# Après le rendu : la dérive en images contre la previs est MESURÉE (corrélation des bords image à image, sur des
# vignettes 64×64 en gris), puis le rendu est recalé par ffmpeg au nombre d'images EXACT de la previs, à sa cadence.
# Pièges tenus (montage, coupe-franche-cadence, templates-coupe-fps) : tout se compte en IMAGES, jamais en secondes
# flottantes — `-frames:v` exact, `tpad` clone en filet pour ne jamais manquer d'image, `setpts` puis `fps=` (la
# fraction exacte de la previs), `trim=start_frame` puis `setpts=PTS-STARTPTS`. numpy n'est PAS dans le python
# embarqué : la corrélation est faite en Python pur sur les cartes de bords de Pillow (64² × ~100 images : < 1 s).

MODES_CONFORM = ("etirer", "noir")
ETIRER_MAX = 2.0                 # au-delà de ce ralenti, le choix automatique passe au noir
VIGNETTE = 64                    # côté des vignettes de mesure
DERIVE_MAX = 12                  # images de dérive cherchées de part et d'autre
GAIN_FIABLE = 0.02               # écart de corrélation minimal pour croire une dérive non nulle


def _fps_txt(infos: dict) -> str:
    return str(infos.get("fps_r") or infos.get("fps") or 24)


def _images(infos: dict) -> int:
    n = infos.get("images")
    if n:
        return int(n)
    return max(1, int(round(float(infos.get("secondes") or 0) * float(infos.get("fps") or 24))))


def plan_conform(infos: dict, modele: str, choix: str | None = None, nom: str = "") -> dict | None:
    """PUR — ce que le conform FERA du clip (None : rien à faire, le clip part tel quel). `choix` : « etirer » |
    « noir » | None (automatique). Rend {mode, auto, choix_possibles, plancher_s, secondes_clip, images_previs,
    fps_previs, fps_envoye, images_envoyees, secondes_envoyees, facteur, transcode}. ValueError : choix inconnu."""
    m = VR.REGISTRE_REFS.get(modele) or {}
    if m.get("grammaire") != "video":
        return None
    if choix is not None and choix not in MODES_CONFORM:
        raise ValueError(f"conform « {choix} » inconnu ({', '.join(MODES_CONFORM)}).")
    fps = float(infos.get("fps") or 0)
    if fps <= 0:
        return None                                   # sonde ratée : clip_refuse le dira
    n = _images(infos)
    duree = n / fps
    flo, fhi = m.get("clip_fps") or (0, 1e9)
    fps_env = fps if flo - 0.01 <= fps <= fhi + 0.01 else float(min(max(fps, flo), fhi))
    ext = ("." + nom.rsplit(".", 1)[-1].lower()) if "." in nom else ""
    transcode = fps_env != fps or (bool(ext) and ext not in (m.get("clip_ext") or (ext,)))
    plancher = VR.plancher_s(modele)
    court = plancher > 0 and duree < plancher - 1e-6
    if not court and not transcode:
        return None
    if court:
        k = plancher / duree
        mode = choix or ("etirer" if k <= ETIRER_MAX + 1e-9 else "noir")
        images_env = int(math.ceil(plancher * fps_env - 1e-6))      # -t ceil : jamais sous le plancher
    else:
        k, mode = 1.0, "transcoder"
        images_env = int(round(duree * fps_env))
    return {"mode": mode, "auto": choix is None or not court, "choix_possibles": list(MODES_CONFORM) if court else [],
            "plancher_s": plancher, "secondes_clip": round(duree, 3), "images_previs": n,
            "fps_previs": _fps_txt(infos), "fps_envoye": fps_env, "images_envoyees": images_env,
            "secondes_envoyees": round(images_env / fps_env, 3),
            "facteur": round(k, 4) if mode == "etirer" else 1.0, "transcode": bool(transcode)}


def _ffmpeg(args: list[str], quoi: str) -> None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg ({quoi}) : {(r.stderr or '').strip()[-300:]}")


_PAIR = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
_X264 = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]


def executer_conform(path: Path, plan: dict, dossier: Path) -> Path:
    """Fabrique le clip conformé (MP4 H.264, `images_envoyees` images EXACTES à `fps_envoye`) dans `dossier`."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    dest = dossier / f"{Path(path).stem[:60]}_conf_{uuid4().hex[:6]}.mp4"
    fe, n = plan["fps_envoye"], int(plan["images_envoyees"])
    if plan["mode"] == "etirer":
        vf = f"setpts=PTS*{plan['facteur']},fps={fe},tpad=stop_mode=clone:stop={n}"
    elif plan["mode"] == "noir":
        vf = f"fps={fe},tpad=stop_mode=add:stop={n}:color=black"
    else:
        vf = f"fps={fe},tpad=stop_mode=clone:stop={n}"
    _ffmpeg(["-i", str(path), "-vf", f"{vf},{_PAIR}", "-frames:v", str(n), "-r", f"{fe:g}", *_X264, str(dest)],
            f"conform {plan['mode']}")
    return dest


def conformer_clip(path: Path, infos: dict, modele: str, duree_plan: float, choix: str | None = None,
                   executer: bool = False, dossier: Path | None = None) -> tuple[Path, dict, list[str]]:
    """t336 — rend (clip à envoyer, ses infos, notes). Sans conform à faire : l'identité. Sinon les infos rendues
    sont celles du clip ENVOYÉ (secondes = le plancher, cadence envoyée…) et portent `conform` (le plan) et
    `nom_envoye` : le devis et `video_refs.clip_refuse` les lisent. `executer` False (devis) : rien n'est écrit, le
    chemin reste celui de la previs ; True (tir) : le clip conformé est fabriqué par ffmpeg (dans `dossier`), sondé."""
    plan = plan_conform(infos, modele, choix, nom=Path(path).name)
    if plan is None:
        return Path(path), dict(infos), []
    if executer:
        dest = executer_conform(path, plan, Path(dossier or (settings.outputs_path / "uploads")))
        out = infos_clip(dest)
    else:
        dest = Path(path)
        out = dict(infos)
        out.update(secondes=plan["secondes_envoyees"], fps=plan["fps_envoye"], images=plan["images_envoyees"])
    out["conform"] = plan
    out["nom_envoye"] = dest.name if executer else Path(path).stem + ".mp4"
    note = {"etirer": f"clip {plan['secondes_clip']:.2f} s ralenti ×{plan['facteur']:.2f} jusqu'à "
                      f"{plan['secondes_envoyees']:.2f} s (plancher {plan['plancher_s']:g} s), rendu ré-accéléré",
            "noir": f"clip {plan['secondes_clip']:.2f} s complété au noir jusqu'à {plan['secondes_envoyees']:.2f} s "
                    f"(plancher {plan['plancher_s']:g} s), rendu coupé",
            "transcoder": f"clip transcodé en MP4 à {plan['fps_envoye']:g} i/s"}[plan["mode"]]
    return dest, out, [note]


def _vignettes(path: Path, filtre: str, fps_r: str) -> list[list[float]]:
    """Les images du clip après `filtre` puis `fps=fps_r`, en vignettes VIGNETTE² ; chacune rendue en carte de BORDS
    (Pillow FIND_EDGES, des deux signes), centrée et normée (produit scalaire = corrélation)."""
    from PIL import Image, ImageChops, ImageFilter, ImageOps
    chaine = ",".join(x for x in (filtre, f"fps={fps_r}", f"scale={VIGNETTE}:{VIGNETTE}", "format=gray") if x)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", chaine, "-f", "rawvideo", "-"],
                       capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg (mesure) : {r.stderr.decode('utf-8', 'replace').strip()[-300:]}")
    t = VIGNETTE * VIGNETTE
    out = []
    for i in range(len(r.stdout) // t):
        im = Image.frombytes("L", (VIGNETTE, VIGNETTE), r.stdout[i * t:(i + 1) * t])
        # bords des DEUX signes (le laplacien de Pillow écrête le négatif) : un rendu au look inversé garde ses bords
        bords = ImageChops.add(im.filter(ImageFilter.FIND_EDGES), ImageOps.invert(im).filter(ImageFilter.FIND_EDGES))
        v = list(bords.getdata())
        moy = sum(v) / t
        c = [x - moy for x in v]
        norme = math.sqrt(sum(x * x for x in c)) or 1.0
        out.append([x / norme for x in c])
    return out


def _score(p: list, r: list, d: int) -> float | None:
    """Corrélation moyenne des bords : image i de la previs contre l'image i + d du rendu, sur le recouvrement."""
    paires = [(p[i], r[i + d]) for i in range(len(p)) if 0 <= i + d < len(r)]
    if len(paires) < max(2, len(p) // 2):
        return None
    return sum(sum(a * b for a, b in zip(x, y)) for x, y in paires) / len(paires)


def mesurer_derive(previs: list, rendu: list) -> dict:
    """La dérive (en images) du rendu contre la previs : d > 0 = le rendu est EN RETARD de d images. Non `fiable`
    quand le meilleur décalage ne bat pas d = 0 d'au moins GAIN_FIABLE (plan fixe, rendu sans rapport) : d vaut 0."""
    lim = max(1, min(DERIVE_MAX, len(previs) // 3))
    scores = {}
    for d in range(-lim, lim + 1):
        s = _score(previs, rendu, d)
        if s is not None:
            scores[d] = s
    if not scores:
        return {"derive_images": 0, "fiable": False, "score": None, "score_zero": None}
    best = max(scores, key=lambda d: (round(scores[d], 6), -abs(d)))
    s0 = scores.get(0)
    fiable = best == 0 or s0 is None or scores[best] - s0 >= GAIN_FIABLE
    if not fiable:
        best = 0
    # un plan sans mouvement : tous les décalages se valent (écart < GAIN_FIABLE) — rien n'est mesuré
    plat = len(scores) > 1 and max(scores.values()) - min(scores.values()) < GAIN_FIABLE
    return {"derive_images": 0 if plat else best, "fiable": bool(fiable and not plat),
            "score": round(scores[best], 4), "score_zero": None if s0 is None else round(s0, 4)}


def _inverse(conform: dict | None) -> str:
    """Le filtre qui DÉFAIT le conform sur le rendu (avant la mesure et le recalage) ; le noir se coupe au compte."""
    if conform and conform.get("mode") == "etirer" and float(conform.get("facteur") or 1) != 1:
        return f"setpts=PTS/{conform['facteur']}"
    return ""


def phrase_derive(d: int, fiable: bool = True) -> str:
    """La phrase FR rangée dans la recette (l'écran compose la sienne, FR/EN, depuis les nombres)."""
    if not fiable:
        return "dérive : non mesurable (plan sans mouvement), longueur recalée"
    return f"dérive : {d:+d} image{'s' if abs(d) > 1 else ''}, recalée"


def recaler(rendu: Path, previs: Path, infos_previs: dict, conform: dict | None = None,
            dossier: Path | None = None) -> dict:
    """t336 — APRÈS le rendu : défait le conform (ré-accélère ×k ; le noir tombe au compte), MESURE la dérive en
    images contre la previs, puis recale (retire d images en tête si le rendu est en retard, clone la 1re s'il est en
    avance) au nombre d'images EXACT de la previs, à sa cadence exacte. Rend {video, derive_images, fiable, images,
    fps, score, phrase}. RuntimeError si ffmpeg échoue ou si le compte n'y est pas."""
    fps_r, n = _fps_txt(infos_previs), _images(infos_previs)
    inv = _inverse(conform)
    mesure = mesurer_derive(_vignettes(previs, "", fps_r), _vignettes(rendu, inv, fps_r))
    d = int(mesure["derive_images"])
    pas = [x for x in (inv, f"fps={fps_r}") if x]
    if d > 0:
        pas += [f"trim=start_frame={d}", "setpts=PTS-STARTPTS"]
    elif d < 0:
        pas += [f"tpad=start={-d}:start_mode=clone"]
    pas += [f"tpad=stop_mode=clone:stop={n}", _PAIR]
    dossier = Path(dossier or Path(rendu).parent)
    dossier.mkdir(parents=True, exist_ok=True)
    dest = dossier / f"{Path(rendu).stem[:60]}_recale.mp4"
    _ffmpeg(["-i", str(rendu), "-vf", ",".join(pas), "-frames:v", str(n), "-r", fps_r, *_X264, str(dest)],
            "recalage")
    images = infos_clip(dest).get("images")
    if images != n:
        raise RuntimeError(f"recalage : {images} images au lieu de {n}")
    return {"video": dest, "derive_images": d, "fiable": mesure["fiable"], "images": n, "fps": fps_r,
            "score": mesure["score"], "phrase": phrase_derive(d, mesure["fiable"])}


def prompt_defaut(modele: str, action: str, n_frames: int, style: str = "", legende: str = "") -> str:
    """Le prompt proposé (modifiable dans la fiche) : il NOMME chaque référence, comme les recettes de scenario.com
    (« le prompt nomme chaque forme ») — @Video1 pour le mouvement, @ImageN pour le look. t333 (A3) : `legende` =
    la légende de la previs colorée du Plateau (« green cylinders = cyprès »), qui nomme chaque forme de @Video1."""
    action = " ".join(str(action or "").split())
    style = " ".join(str(style or "").split())
    images = ", ".join(f"@Image{i}" for i in range(1, max(1, n_frames) + 1))
    if VR.REGISTRE_REFS[modele]["grammaire"] == "video":
        p = (f"Render @Video1 as the final shot with the look of {images}: keep the exact motion, camera and timing "
             f"of @Video1; take colours, light, materials and characters from {images}.")
    else:
        p = "A cinematic shot in the look of the reference images."
    if action:
        p += f" Action: {action}"
    legende = " ".join(str(legende or "").split())
    if legende and VR.REGISTRE_REFS[modele]["grammaire"] == "video":     # sans clip, rien à nommer
        p += f" In @Video1 — {legende}"
    if style:
        p += f" Style: {style}"
    return p[:PROMPT_MAX]


def calculer(modele: str, *, clip: dict | None, n_frames: int, tache: str | None, resolution: str | None,
             duree_plan: float) -> dict:
    """Le DEVIS (sans E/S) : {secondes_entree, secondes_sortie, resolution, tache, op, usd}. Seedance « editing » :
    la sortie suit le clip ; « reference » : la durée du plan, bornée 4-30 s. Veo références : 8 s natifs."""
    from app.services import pricing as _pr
    m = VR.REGISTRE_REFS[modele]
    if m["grammaire"] == "video":
        t = tache if tache in m["taches"] else m["taches"][0]
        res = resolution if resolution in m["resolutions"] else "720p"
        entree = float((clip or {}).get("secondes") or 0)
        if t == "editing":
            sortie = entree
        else:
            d = max(1, int(round(float(duree_plan or 4))))
            sortie = float(d if d in m["durees"] else min(m["durees"], key=lambda x: (abs(x - d), x)))
    else:
        t, entree = None, 0.0
        res = resolution if resolution in (m["resolutions"] or ()) else "720p"
        sortie = float(m["durees"][0])
    op = VR.op_devis(modele, sortie, secondes_entree=entree, resolution=res)
    return {"secondes_entree": round(entree, 3), "secondes_sortie": round(sortie, 3), "resolution": res,
            "tache": t, "op": op, "usd": _pr.estimate(op)["total_usd"]}


# ─────────────────────────────────── tir ──────────────────────────────────

async def _upload(path: Path) -> str:                               # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._upload(path)


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._fal_subscribe(endpoint, arguments)


async def _download(url: str, dest: Path) -> None:                  # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    await _S._download(url, dest)


def _url_video(res) -> str | None:
    if not isinstance(res, dict):
        return None
    v = res.get("video")
    if isinstance(v, dict) and v.get("url"):
        return str(v["url"])
    if isinstance(v, str) and v.startswith("http"):
        return v
    u = res.get("video_url") or res.get("url")
    return str(u) if u else None


async def tirer_previs(modele: str, *, clip: Path | None, frames: list[Path], prompt: str, tache: str | None,
                       resolution: str | None, duree: int, dossier: Path | None = None) -> dict:
    """Tire UN rendu du registre et range la vidéo. PAYANT : la route a passé la clé (503), la confirmation (409) et
    la garde des plafonds AVANT. Le clip et les style frames partent par `_upload` ; la vidéo rendue -> `dossier`
    (outputs/uploads par défaut, où « video_filename » la retrouve) sous `previs_<hex8>.mp4`.
    Rend {video: Path, seed, endpoint, arguments (sans URL), notes}. ValueError : requête invalide ; RuntimeError :
    réponse fal sans vidéo."""
    m = VR.REGISTRE_REFS[modele]
    entites = [{"nom": f.name, "face": f"http://a-blanc/{i}"} for i, f in enumerate(frames)]
    VR.construire(modele, prompt, entites, video_url="http://a-blanc/v" if clip else None, tache=tache,
                  duree=duree, resolution=resolution, aspect_ratio="9:16")      # refus AVANT tout envoi
    url_clip = await _upload(Path(clip)) if clip is not None else None
    urls = [await _upload(Path(f)) for f in frames]
    endpoint, args, notes = VR.construire(modele, prompt, [{"nom": f.name, "face": u} for f, u in zip(frames, urls)],
                                          video_url=url_clip, tache=tache, duree=duree, resolution=resolution,
                                          aspect_ratio="9:16")
    sans_url = {k: v for k, v in args.items() if k not in ("video_urls", "image_urls")}
    logger.info("previs → plan [{}] -> {} · {} · notes={}", modele, endpoint, sans_url, notes)
    res = await _fal_subscribe(endpoint, args)
    u = _url_video(res)
    if not u:
        cles = ", ".join(map(str, res)) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"fal.ai ({m['label']}) : aucune vidéo dans la réponse (clés : {cles})")
    d = Path(dossier or (settings.outputs_path / "uploads"))
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"previs_{uuid4().hex[:8]}.mp4"
    while dest.exists():
        dest = d / f"previs_{uuid4().hex[:8]}_{os.urandom(2).hex()}.mp4"
    await _download(u, dest)
    seed = res.get("seed") if isinstance(res, dict) else None
    return {"video": dest, "seed": seed if isinstance(seed, int) else None, "endpoint": endpoint,
            "arguments": sans_url, "notes": notes}
