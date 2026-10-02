"""Tâche #63 (plan chapitres T10, 02/10/2026) — l'animatique : les plans du storyboard montés en vidéo 9:16 AVANT
toute génération vidéo payante. Un montage de RÉPÉTITION, jamais publié : 540×960, 30 i/s (décision du 02/10),
non noté en Bibliothèque, écrasé à chaque rendu.

Règle de durée (Boords) : une voix témoin attachée à un plan FIXE sa durée ; sans voix, la durée réglée du plan.
`plan()` est PUR — ni disque ni réseau. Image : celle de PRODUCTION (#62) prime sur le croquis ; sans l'une ni
l'autre, un CARTON PIL (numéro + action) — un noir muet passerait pour une panne.

Le son, corrigé du plan du 03/09 (mesuré au ffmpeg réel) : des clips tantôt sonores tantôt muets (`-an`) enchaînés
par le démultiplexeur concat PERDENT la piste (muet en tête) ou la DÉCALENT (muet au milieu). Ici les clips vidéo
sont tous muets, puis UNE piste son est construite — chaque voix, ou un silence exact, recalés à la durée RÉELLE du
clip (en images entières) — et posée sur la vidéo. Aucune dérive, quel que soit l'ordre.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LARGEUR, HAUTEUR, IPS = 540, 960, 30
FOND_CARTON = (12, 14, 18)
ENCRE = (222, 228, 236)
ACCENT = (86, 200, 226)          # le cyan du produit : action / génération
DUREE_MINI = 0.8                 # sous ce seuil, un audio n'est pas une voix
TEXTE_MINI = 3                   # sous ce nombre de caractères, pas de voix témoin
POLICES = (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/arial.ttf"))
_ID_SUR = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _cadre(d: float) -> float:
    """La durée qu'un clip AURA vraiment : un nombre entier d'images."""
    return round(max(1, round(float(d) * IPS)) / IPS, 3)


def texte_plan(s: dict) -> str:
    return (s.get("action") or s.get("source_text") or "").strip()


def cle_voix(texte: str, voice_id: str | None, langue: str) -> str:
    """La clé de cache d'une voix témoin : même texte, même voix, même langue -> même fichier, jamais repayé."""
    return hashlib.sha1(f"{voice_id or ''}|{langue}|{texte}".encode("utf-8")).hexdigest()[:16]


def plan(shots: list[dict], voix: dict | None = None, mini: float = DUREE_MINI) -> list[dict]:
    """Le plan de montage. PUR. `shots` = dicts de _shot_dict ; `voix` = {shot_id: durée mesurée}.
    Entrée : {idx, shot_id, image, texte, dur, source_duree, carton}."""
    voix = voix or {}
    out = []
    for i, s in enumerate(sorted(shots, key=lambda x: x.get("idx", 0))):
        img = s.get("image") or s.get("sketch_image") or None
        dv = float(voix.get(s.get("id")) or 0)
        if dv >= mini:
            dur, src = _cadre(dv), "voix"
        else:
            dur, src = _cadre(s.get("duration_s") or 4.0), "plan"
        out.append({"idx": i, "shot_id": s.get("id"), "image": img, "texte": texte_plan(s),
                    "dur": dur, "source_duree": src, "carton": img is None,
                    "energie": s.get("energy")})          # tâche #66 : le « reel » choisit les plans par énergie
    return out


def duree_totale(entrees: list[dict]) -> float:
    return round(sum(e["dur"] for e in entrees), 3)


def _police(taille: int):
    for p in POLICES:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), taille)
            except OSError:
                continue
    return ImageFont.load_default()


def carton(titre: str, texte: str, dest: Path, w: int = LARGEUR, h: int = HAUTEUR) -> Path:
    """La carte de secours d'un plan sans image : le numéro du plan et son action, au cadre de sortie. PIL seul."""
    im = Image.new("RGB", (w, h), FOND_CARTON)
    d = ImageDraw.Draw(im)
    k = w / 1080
    ft, ptit = _police(int(40 * k)), _police(int(58 * k))
    marge = int(80 * k)
    d.text((marge, h // 2 - int(260 * k)), titre, font=ptit, fill=ACCENT)
    d.line([(marge, h // 2 - int(180 * k)), (w - marge, h // 2 - int(180 * k))], fill=ACCENT, width=max(1, int(3 * k)))
    y = h // 2 - int(130 * k)
    for ligne in textwrap.wrap(texte or "(pas d'action décrite)", width=34)[:12]:
        d.text((marge, y), ligne, font=ft, fill=ENCRE)
        y += int(56 * k)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return dest


def dossier(outputs: Path, chapter_id: str, creer: bool = False) -> Path:
    """outputs/animatique/<chapitre>. Un identifiant douteux (`..`, séparateurs) est REFUSÉ ; un GET ne crée rien."""
    if not _ID_SUR.match(chapter_id or ""):
        raise ValueError(f"identifiant de chapitre refusé : {chapter_id!r}")
    d = Path(outputs) / "animatique" / chapter_id
    if creer:
        d.mkdir(parents=True, exist_ok=True)
    return d


def purger(d: Path) -> None:
    """Les clips d'un rendu précédent (plus long) ne survivent pas au suivant ; le cache des voix, si."""
    for motif in ("p[0-9][0-9][0-9].mp4", "p[0-9][0-9][0-9].png", "animatique*.mp4", "animatique*.m4a", MANIFESTE):
        for f in d.glob(motif):
            f.unlink(missing_ok=True)


def _ffmpeg(cmd: list[str], quoi: str) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{quoi} : {(e.stderr or '')[-300:]}") from e


def filtre_audio(entrees: list[dict], audios: dict) -> tuple[list[Path], str]:
    """(fichiers d'entrée, filter_complex) de LA piste son : par plan, sa voix recalée (rééchantillonnée, complétée,
    coupée) ou un silence, à la durée RÉELLE du clip ; puis concat. PUR. L'entrée 0 est la vidéo."""
    fichiers: list[Path] = []
    morceaux, etiquettes = [], []
    for k, e in enumerate(entrees):
        a = audios.get(e["shot_id"])
        if a is not None and Path(a).is_file():
            fichiers.append(Path(a))
            src = (f"[{len(fichiers)}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                   f"apad,atrim=0:{e['dur']}")
        else:
            src = f"anullsrc=r=44100:cl=stereo,atrim=0:{e['dur']}"
        morceaux.append(f"{src},asetpts=N/SR/TB[a{k}]")
        etiquettes.append(f"[a{k}]")
    morceaux.append("".join(etiquettes) + f"concat=n={len(entrees)}:v=0:a=1[a]")
    return fichiers, ";".join(morceaux)


MANIFESTE = "animatique.json"


def ecrire_manifeste(sortie: Path, entrees: list[dict], audios: dict) -> Path:
    """Tâche #66 : CE QUI A ÉTÉ MONTÉ, écrit APRÈS un rendu réussi (purgé avant le suivant) — les plans dans l'ordre,
    leur clip, leur durée réelle, leur voix témoin. Les sorties vers le Montage lisent CE fichier, pas un recalcul : un
    recalcul sans les durées des voix divergerait des clips."""
    import json as _json
    d = {"version": 1, "ips": IPS, "largeur": LARGEUR, "hauteur": HAUTEUR,
         "plans": [{"idx": e["idx"], "shot_id": e["shot_id"], "clip": f"p{e['idx']:03d}.mp4", "dur": e["dur"],
                    "source_duree": e["source_duree"], "texte": e["texte"], "energie": e.get("energie"),
                    "voix": (Path(audios[e["shot_id"]]).relative_to(sortie).as_posix()
                             if e["shot_id"] in audios and Path(audios[e["shot_id"]]).is_relative_to(sortie) else None)}
                   for e in entrees]}
    f = sortie / MANIFESTE
    f.write_text(_json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return f


def lire_manifeste(sortie: Path) -> dict | None:
    import json as _json
    try:
        return _json.loads((sortie / MANIFESTE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rendre(entrees: list[dict], *, images: Path, sortie: Path, audios: dict | None = None, progres=None) -> Path:
    """Monte l'animatique : un clip MUET par plan (pXXX.mp4, gardés), la concaténation, puis — s'il y a au moins
    une voix — la piste son unique posée dessus. `progres(i, n)` avant chaque plan."""
    from app.services.ffmpeg_service import FFmpegMerger
    audios = {k: v for k, v in (audios or {}).items() if v is not None and Path(v).is_file()}
    sortie.mkdir(parents=True, exist_ok=True)
    purger(sortie)
    clips, n = [], len(entrees)
    for e in entrees:
        if progres:
            progres(e["idx"] + 1, n)
        img = None if e["carton"] else Path(images) / Path(e["image"]).name
        if img is None or not img.is_file():
            img = carton(f"PLAN {e['idx'] + 1}", e["texte"], sortie / f"p{e['idx']:03d}.png")
        clip = sortie / f"p{e['idx']:03d}.mp4"
        FFmpegMerger.scene_clip(img, None, clip, motion="still", dur=e["dur"], w=LARGEUR, h=HAUTEUR, fps=IPS)
        clips.append(clip)
    final = sortie / "animatique.mp4"
    if not audios:
        FFmpegMerger.concat_clips(clips, final)
        ecrire_manifeste(sortie, entrees, audios)
        return final
    muet = sortie / "animatique_muet.mp4"
    FFmpegMerger.concat_clips(clips, muet)
    fichiers, filtre = filtre_audio(entrees, audios)
    cmd = ["ffmpeg", "-y", "-i", str(muet)]
    for f in fichiers:
        cmd += ["-i", str(f)]
    if len(filtre) > 6000:                       # la ligne de commande Windows plafonne à ~32 000 caractères
        script = sortie / "animatique_filtre.txt"
        script.write_text(filtre, encoding="utf-8")
        cmd += ["-/filter_complex", str(script)]
    else:
        cmd += ["-filter_complex", filtre]
    cmd += ["-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(final)]
    _ffmpeg(cmd, "piste son de l'animatique")
    muet.unlink(missing_ok=True)
    ecrire_manifeste(sortie, entrees, audios)
    return final
