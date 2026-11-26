# -*- coding: utf-8 -*-
"""t511 (RV1, 26/11/2026) — matière « VIDÉO » de l'Inspiration : étages 0 et 1 GRATUITS d'une vidéo de référence.

Spec docs/superpowers/specs/2026-11-13-reel-reference-design.md, § 3.1, § 3.2, décisions R1, R3, R4 (validées le 13/11).

R1 : on étend l'Inspiration (t313) — une inspiration de `matiere` « video » vit dans le même registre
(`DATA_ROOT/inspirations/<id>/inspiration.json`), HORS de la Bibliothèque : la source ne devient jamais un média de
l'utilisateur, ni le visuel d'un post (la garde « visuel ≠ capture » d'`inspiration.brouillon` ne s'applique pas à une
vidéo : elle n'est dans aucun dossier d'images).
R2 : l'application ne télécharge jamais la vidéo d'autrui : la vidéo est un FICHIER déposé par l'utilisateur (son
enregistrement d'écran, une vidéo reçue).
R3 : étage 0 (accueil : type, taille, durée, **présence du son**) et étage 1 (mesures : cadre, cadence, plans, silences,
boucle, planches d'images) sont locaux, par ffmpeg, sans aucune dépense. La lecture (étage 2) est RV2, sur devis.
R4 : on garde la FICHE (mesures), pas la source : la vidéo et les planches sont effacées `PURGE_JOURS` après l'analyse
(`purger`, appelée à chaque liste des inspirations) ; la fiche reste.

Fonctions PURES (bancs) : `lire_sonde`, `lire_son`, `lire_plans`, `boucle_depuis_images`, `rythme`, `cadre`, `fiche`,
`echeance`. Les appels à ffmpeg passent tous par `_lancer` (couture remplacée par les bancs).
Journaux : tailles, durées et nombres seulement.
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from app.services import inspiration as I

MATIERE = "video"
PURGE_JOURS = 7
OCTETS_MAX = 300 * 1024 * 1024        # un enregistrement d'écran d'une minute pèse de 20 à 150 Mo
DUREE_MAX_S = 600.0                   # 10 min : au-delà ce n'est plus un format court
EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
SEUIL_MUET_DB = -60.0                 # crête sous -60 dB : capture faite lecteur coupé, rien à transcrire
SEUIL_PLAN = 0.25                     # select=gt(scene,…) : mesuré sur le Reel de référence du 13/11
VOLET_S = 0.4                         # trois coupes en moins de 0,4 s = un volet de transition, pas trois plans
VUES_PAR_PLANCHE = 8                  # une image par seconde, 4 × 2 par planche
MAX_PLANCHES = 40
DELAI_S = 300

# messages fixes (L10 : scripts/i18n_l10_traductions.json)
M_FORMAT = "Vidéo attendue : MP4, MOV, M4V, WEBM ou MKV."
M_LOURDE = "Vidéo trop lourde : 300 Mo au plus."
M_LONGUE = "Vidéo trop longue : 10 minutes au plus."
M_ILLISIBLE = "Vidéo illisible : ffmpeg n'y trouve aucune image."
M_FFMPEG = "ffmpeg est introuvable : la vidéo ne peut pas être mesurée."
M_PAS_VIDEO = "Cette inspiration n'est pas une vidéo."
M_PURGEE = "La vidéo source a été effacée (7 jours après l'analyse) : seule la fiche reste."


class MesureImpossible(RuntimeError):
    pass


# ---- couture ffmpeg ---------------------------------------------------------------------------------------------------

def _lancer(cmd: list, binaire: bool = False):
    """(sortie, erreurs) d'ffmpeg / ffprobe. Point unique remplacé par les bancs."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=DELAI_S)
    except FileNotFoundError as e:
        raise MesureImpossible("ffmpeg est introuvable : la vidéo ne peut pas être mesurée.") from e
    except (subprocess.TimeoutExpired, OSError) as e:
        raise MesureImpossible("Vidéo illisible : ffmpeg n'y trouve aucune image.") from e
    out = r.stdout if binaire else r.stdout.decode("utf-8", "replace")
    return out, r.stderr.decode("utf-8", "replace")


# ---- fonctions pures --------------------------------------------------------------------------------------------------

def lire_sonde(texte_json: str) -> dict:
    """La sortie JSON de ffprobe -> {duree_s, largeur, hauteur, images_par_s, piste_audio, codec}."""
    try:
        d = json.loads(texte_json or "{}")
    except ValueError:
        d = {}
    flux = d.get("streams") or []
    v = next((s for s in flux if s.get("codec_type") == "video"), {}) or {}
    a = next((s for s in flux if s.get("codec_type") == "audio"), None)
    num, _, den = str(v.get("avg_frame_rate") or "0/1").partition("/")
    try:
        ips = float(num) / float(den or 1) if float(den or 1) else 0.0
    except ValueError:
        ips = 0.0
    try:
        duree = float((d.get("format") or {}).get("duration") or v.get("duration") or 0)
    except (TypeError, ValueError):
        duree = 0.0
    larg, haut = v.get("width"), v.get("height")
    # une vidéo tournée (téléphone) : la rotation échange largeur et hauteur à l'affichage
    rot = 0
    for sd in v.get("side_data_list") or []:
        try:
            rot = int(float(sd.get("rotation") or 0))
        except (TypeError, ValueError):
            pass
    try:
        rot = rot or int(float((v.get("tags") or {}).get("rotate") or 0))
    except (TypeError, ValueError):
        pass
    if abs(rot) % 180 == 90 and larg and haut:
        larg, haut = haut, larg
    return {"duree_s": round(duree, 3), "largeur": larg, "hauteur": haut,
            "images_par_s": round(ips, 3) if ips else None, "piste_audio": bool(a),
            "codec": v.get("codec_name") or ""}


def lire_son(stderr: str) -> dict:
    """La sortie de `silencedetect` + `volumedetect` -> niveaux, muet, silences [[début, fin], …]."""
    s = str(stderr or "")
    moy = re.search(r"mean_volume: (-?[\d.]+) dB", s)
    mx = re.search(r"max_volume: (-?[\d.]+) dB", s)
    debuts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", s)]
    fins = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", s)]
    crete = float(mx.group(1)) if mx else None
    return {"niveau_moyen_db": float(moy.group(1)) if moy else None, "niveau_max_db": crete,
            "muet": crete is None or crete < SEUIL_MUET_DB,
            "silences": [[round(max(0.0, a), 2), round(b, 2)] for a, b in zip(debuts, fins)]}


def lire_plans(stderr: str) -> dict:
    """La sortie `select=gt(scene,…),showinfo` -> {coupes_s, volets_s} : coupes triées, volets regroupés (< VOLET_S)."""
    t = sorted(round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", str(stderr or "")))
    coupes, volets = [], []
    for x in t:
        if x <= 0:
            continue
        if coupes and x - coupes[-1] < VOLET_S:
            if not volets or volets[-1] != coupes[-1]:
                volets.append(coupes[-1])
            continue
        coupes.append(x)
    return {"coupes_s": coupes, "volets_s": volets}


def boucle_depuis_images(images: list, cadence: int, duree: float) -> dict | None:
    """Cherche le décalage L (> 5 s) pour lequel l'image à t ressemble le plus à l'image à t + L.

    `images` : vignettes en gris de même taille (bytes), à `cadence` images par seconde. Une capture d'écran d'un Reel
    contient souvent plusieurs lectures : la vraie durée est alors la période. None sous 12 s d'images."""
    n = len(images)
    if n < cadence * 12 or not images or not images[0]:
        return None
    taille = len(images[0])

    def ecart(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / taille

    def moyen(lag):
        idx = range(0, n - lag, 2)
        return sum(ecart(images[i], images[i + lag]) for i in idx) / max(1, len(idx))

    meilleur = None
    for lag in range(cadence * 5, n - cadence * 3):
        e = moyen(lag)
        if meilleur is None or e < meilleur[1]:
            meilleur = (lag, e)
    if meilleur is None:
        return None
    ref = moyen(max(cadence * 5, n // 3))          # écart entre images sans rapport (un tiers de la durée)
    periode = meilleur[0] / cadence
    sure = meilleur[1] < 0.35 * ref and periode < duree - 3
    return {"periode_s": round(periode, 1) if sure else None, "ecart": round(meilleur[1], 2),
            "ecart_reference": round(ref, 2), "repetee": bool(sure)}


def cadre(largeur, hauteur) -> str:
    """« 9:16 », « 16:9 », « 1:1 », « 4:5 » ou « L×H » si aucun rapport courant à 3 % près."""
    try:
        l, h = int(largeur), int(hauteur)
    except (TypeError, ValueError):
        return ""
    if l <= 0 or h <= 0:
        return ""
    r = l / h
    for nom, v in (("9:16", 9 / 16), ("16:9", 16 / 9), ("1:1", 1.0), ("4:5", 4 / 5), ("3:4", 3 / 4), ("4:3", 4 / 3)):
        if abs(r - v) / v < 0.03:
            return nom
    return f"{l}×{h}"


def rythme(coupes: list, duree: float) -> dict:
    """Les tableaux (plans) entre les coupes : nombre, durées moyenne / min / max (s), plans par minute."""
    bornes = [0.0] + [c for c in coupes if 0 < c < duree] + [duree] if duree > 0 else []
    durees = [round(b - a, 2) for a, b in zip(bornes, bornes[1:]) if b - a > 0]
    if not durees:
        return {"plans": 0, "duree_moyenne_s": None, "duree_min_s": None, "duree_max_s": None, "plans_par_minute": None}
    return {"plans": len(durees), "duree_moyenne_s": round(statistics.mean(durees), 2),
            "duree_min_s": min(durees), "duree_max_s": max(durees),
            "plans_par_minute": round(len(durees) * 60.0 / duree, 1)}


def fiche(sonde: dict, son: dict | None, plans: dict, boucle: dict | None) -> dict:
    """La FICHE de la référence (format + rythme), calculée sur la période quand la capture contient plusieurs
    lectures. Aucune phrase ni image de la source : des nombres seulement."""
    duree = float(sonde.get("duree_s") or 0)
    periode = (boucle or {}).get("periode_s")
    utile = float(periode) if periode else duree
    coupes = [c for c in plans.get("coupes_s") or [] if c < utile]
    return {"format": {"duree_s": round(utile, 2), "duree_fichier_s": round(duree, 2),
                       "cadre": cadre(sonde.get("largeur"), sonde.get("hauteur")),
                       "largeur": sonde.get("largeur"), "hauteur": sonde.get("hauteur"),
                       "images_par_s": sonde.get("images_par_s"), "boucle": bool(periode),
                       "son": bool(sonde.get("piste_audio")) and not (son or {}).get("muet", True)},
            "rythme": rythme(coupes, utile),
            "silences": len([s for s in (son or {}).get("silences") or [] if s[0] < utile])}


def echeance(analyse_le: str, jours: int = PURGE_JOURS) -> str:
    """La date (isoformat UTC) où la source sera effacée."""
    t = datetime.fromisoformat(analyse_le)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (t + timedelta(days=jours)).isoformat(timespec="seconds")


# ---- mesures (ffmpeg) -------------------------------------------------------------------------------------------------

def _sonder(video: Path) -> dict:
    out, _ = _lancer(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    return lire_sonde(out)


def _son(video: Path) -> dict:
    _, err = _lancer(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
                      "-af", "silencedetect=noise=-35dB:d=0.4,volumedetect", "-f", "null", "-"])
    return lire_son(err)


def _plans(video: Path) -> dict:
    _, err = _lancer(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an",
                      "-vf", f"select='gt(scene,{SEUIL_PLAN})',showinfo", "-f", "null", "-"])
    return lire_plans(err)


def _boucle(video: Path, duree: float) -> dict | None:
    cote, cad = 24, 2
    brut, _ = _lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-an",
                       "-vf", f"fps={cad},scale={cote}:{cote},format=gray", "-f", "rawvideo", "-"], binaire=True)
    t = cote * cote
    images = [brut[i * t:(i + 1) * t] for i in range(len(brut or b"") // t)]
    return boucle_depuis_images(images, cad, duree)


def _planches(video: Path, dossier: Path, duree: float) -> list[str]:
    dossier.mkdir(parents=True, exist_ok=True)
    n = min(MAX_PLANCHES, max(1, int(duree // VUES_PAR_PLANCHE) + 1))
    cadence = 1 if duree <= MAX_PLANCHES * VUES_PAR_PLANCHE else VUES_PAR_PLANCHE * MAX_PLANCHES / duree
    _lancer(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-an",
             "-vf", f"fps={cadence:g},scale=270:-2,tile=4x2", "-frames:v", str(n),
             str(dossier / "vues_%02d.jpg")])
    return sorted(f.name for f in dossier.glob("vues_*.jpg"))


# ---- registre ---------------------------------------------------------------------------------------------------------

def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def extension_admise(nom: str) -> str:
    ext = Path(str(nom or "")).suffix.lower()
    if ext not in EXTENSIONS:
        raise I.RefusInspiration("Vidéo attendue : MP4, MOV, M4V, WEBM ou MKV.", "format")
    return ext


def nouvelle(*, nom: str, espace_id: str) -> tuple[str, Path]:
    """Réserve une inspiration vidéo : (id, chemin où écrire le fichier déposé). Refus de format avant toute écriture."""
    ext = extension_admise(nom)
    iid = uuid.uuid4().hex
    d = I._dossier(iid)
    d.mkdir(parents=True, exist_ok=True)
    return iid, d / ("source" + ext)


def abandonner(iid: str) -> None:
    shutil.rmtree(I._dossier(iid), ignore_errors=True)


def mesurer(iid: str, *, chemin: Path, espace_id: str, source_libelle: str = "", source_lien: str = "",
            langue: str = "fr") -> dict:
    """Étages 0 et 1 sur le fichier déposé (bloquant : à lancer dans un fil). Crée le registre. Un refus efface tout."""
    try:
        octets = chemin.stat().st_size
        if octets > OCTETS_MAX:
            raise I.RefusInspiration("Vidéo trop lourde : 300 Mo au plus.", "lourde")
        sonde = _sonder(chemin)
        duree = float(sonde.get("duree_s") or 0)
        if duree <= 0 or not sonde.get("largeur"):
            raise I.RefusInspiration("Vidéo illisible : ffmpeg n'y trouve aucune image.", "illisible")
        if duree > DUREE_MAX_S:
            raise I.RefusInspiration("Vidéo trop longue : 10 minutes au plus.", "longue")
        son = _son(chemin) if sonde.get("piste_audio") else {"muet": True, "silences": [], "niveau_max_db": None,
                                                                "niveau_moyen_db": None}
        plans = _plans(chemin)
        boucle = _boucle(chemin, duree)
        planches = _planches(chemin, chemin.parent / "planches", duree)
    except Exception:
        abandonner(iid)
        raise
    maintenant = _maintenant()
    rec = {"id": iid, "espace_id": espace_id, "cree": maintenant, "langue": langue if langue in ("fr", "en") else "fr",
           "matiere": MATIERE,
           "source": {"libelle": I._texte(source_libelle, I.MAX_SOURCE), "lien": I._texte(source_lien, I.MAX_SOURCE),
                      "le": maintenant, "octets": octets, "video": chemin.name},
           "texte_capte": "", "texte_colle": False, "ocr": {"moteur": "", "mots": 0, "raison": ""}, "palette": [],
           "video": {"etage0": {"octets": octets, "duree_s": sonde["duree_s"], "codec": sonde.get("codec"),
                                "piste_audio": sonde["piste_audio"], "son": not son.get("muet", True)},
                     "mesures": {"sonde": sonde, "son": son, "plans": plans, "boucle": boucle},
                     "fiche": fiche(sonde, son, plans, boucle), "planches": planches,
                     "analyse_le": maintenant, "purge_le": echeance(maintenant), "purgee": False},
           "analyse": None, "redaction": None, "brouillons": []}
    I._ecrire(rec)
    logger.info(f"inspiration {iid[:8]} : vidéo {octets} o, {sonde['duree_s']} s, "
                f"{rec['video']['fiche']['rythme']['plans']} plan(s), {len(planches)} planche(s), "
                f"son {'oui' if rec['video']['etage0']['son'] else 'non'}")
    return rec


def chemin_planche(iid: str, nom: str) -> Path:
    """Le fichier d'une planche (nom lu dans le registre, jamais un chemin fourni)."""
    rec = I.lire(iid)
    v = rec.get("video") or {}
    if rec.get("matiere") != MATIERE:
        raise I.RefusInspiration("Cette inspiration n'est pas une vidéo.", "matiere")
    if v.get("purgee"):
        raise I.RefusInspiration("La vidéo source a été effacée (7 jours après l'analyse) : seule la fiche reste.", "purgee")
    if nom not in (v.get("planches") or []):
        raise I.InspirationInconnue(I.M_INCONNUE)
    return I._dossier(iid) / "planches" / nom


def purger(maintenant: datetime | None = None) -> int:
    """R4 : efface la vidéo source et les planches des inspirations vidéo dont l'échéance est passée ; garde la fiche."""
    t = maintenant or datetime.now(timezone.utc)
    n = 0
    r = I._racine()
    if not r.is_dir():
        return 0
    for d in r.iterdir():
        if not I._ID.match(d.name):
            continue
        try:
            rec = I.lire(d.name)
        except I.InspirationInconnue:
            continue
        v = rec.get("video") or {}
        if rec.get("matiere") != MATIERE or v.get("purgee") or not v.get("purge_le"):
            continue
        try:
            due = datetime.fromisoformat(v["purge_le"])
        except ValueError:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due > t:
            continue
        nom = (rec.get("source") or {}).get("video")
        if nom:
            try:
                (d / nom).unlink(missing_ok=True)
            except OSError:
                continue
        shutil.rmtree(d / "planches", ignore_errors=True)
        v.update({"purgee": True, "planches": [], "purgee_le": t.isoformat(timespec="seconds")})
        rec["video"] = v
        I._ecrire(rec)
        n += 1
    if n:
        logger.info(f"inspiration : {n} vidéo(s) source effacée(s) (R4, {PURGE_JOURS} jours)")
    return n
