# -*- coding: utf-8 -*-
"""t188 (G6, plan « Génération IA enrichie ») — les VFX IA : une vidéo (ou une image) -> une vidéo retouchée.

UN registre (`REGISTRE`, 12 gestes, tous servis par la clé fal), schémas fal relus le 12/10/2026 :
  · relight-h3       minimax/h3-max/relight : video_url + reference_image_url REQUIS ; resolution 480P|768P|1080P|2K
                     (défaut chez nous 768P), aspect_ratio (défaut chez nous « adaptive » : le schéma pose 16:9, qui
                     recadrerait une source verticale), seed. Source de 15 s au plus (schéma).
  · inserer-h3       minimax/h3-max/insert-video : video_url, start_time (1,625 à 60 s), resume_time (<= 60 s) REQUIS ;
                     prompt, duration (scène générée, 5 à 13 s, défaut 5 — TOUJOURS envoyée : c'est elle qui est
                     facturée), resolution 480p|768p, reference_image_urls, color_match, enable_prompt_expansion, seed.
  · effacer-perso    fal-ai/ltx-2.3-quality/clean-plate      } video_url requis ; prompt, resolution 480p|720p (côté
  · jour-nuit        fal-ai/ltx-2.3-quality/day-to-night     } COURT, l'autre suit le format de la source), seed ;
  · eau              fal-ai/ltx-2.3-quality/water-simulation } num_frames / frames_per_second calculés ICI depuis la
  · coloriser        fal-ai/ltx-2.3-quality/colorization     } durée de la source (24 i/s, 9 à 481 images : au-delà,
                     refus nommé, jamais de coupe muette). enable_detail_refine n'est JAMAIS envoyé (x4 le prix).
  · effacer-objet    fal-ai/void-video-inpainting : video_url + prompt (le fond voulu) REQUIS ; mask_prompt (l'objet à
                     effacer, exigé chez nous : sans masque vidéo fourni, c'est lui qui fait générer le masque SAM 3),
                     enable_pass2_refinement.
  · retoucher-kling  fal-ai/kling-video/o3/pro/video-to-video/edit : prompt + video_url REQUIS ; keep_audio TOUJOURS
                     True (le son du plan reste) ; image_urls (une image de référence). Source .mp4/.mov de 3 à 15 s.
  · retoucher-flux3  blackforestlabs/flux-3/edit-video : prompt + video_url REQUIS. MP4 de moins de 15 s.
  · recadrer         fal-ai/ltx-2.3/reframe : video_url ; aspect_ratio 1:1|4:5|5:4|9:16|16:9 (défaut chez nous 9:16),
                     resolution 720p|1080p (défaut chez nous 720p ; le schéma pose 1080p, deux fois plus cher).
  · agrandir         topaz/upscale/video/precision : video_url ; upscale_factor 1 à 4 (défaut 2), model « Proteus ».
  · effets-pixverse  fal-ai/pixverse/v5.5/effects : effect + image_url REQUIS ; duration 5|8|10, resolution
                     360p|540p|720p|1080p (1080p interdit en 10 s : refus nommé). Une IMAGE -> une vidéo.

PRIX (pages fal relues le 12/10/2026 ; les tarifs vivent dans pricing.DEFAULTS, `pricing.taux_vfx` est LA fonction de
taux, `unites` ci-dessous la quantité) : unité « s » (seconde de source, ou de scène générée pour l'insertion), « mp »
(mégapixel généré = largeur x hauteur x images, arrondi au MP supérieur), « video », « tranche10s » (Topaz : tranche
de 10 s de SORTIE arrondie une fois par travail, classe de résolution = hauteur de sortie), « effet » (PixVerse : la
base 5 s par résolution, x2 en 8 s, x2,2 en 10 s). La colorisation n'affiche AUCUN prix : 0 « prix à mesurer ».

AUCUN appel réseau hors des trois coutures `_upload`, `_fal_subscribe`, `_download` (celles de sfx_service, que les
bancs remplacent par des enregistreurs). Le tir passe par la route POST /vfx-ia : 400 id -> 503 FAL_KEY -> 400 champ /
source / option -> garde des plafonds -> `appliquer_vfx`."""
from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

from loguru import logger

from app.config import settings

NATURE = "vfx"
PROMPT_MAX = 1500
FPS_LTX = 24                        # images par seconde envoyées aux quatre effets LTX (défaut du schéma)
IMAGES_LTX = (9, 481)               # num_frames du schéma LTX
EXT_VIDEO = (".mp4", ".mov", ".webm", ".m4v")
EXT_IMAGE = (".png", ".jpg", ".jpeg", ".webp")

# PixVerse v5.5 effects : la liste COMPLÈTE de l'énumération `effect` du schéma fal, relue le 12/10/2026 (154
# valeurs, dans l'ordre du schéma), recopiée À L'IDENTIQUE (casse, apostrophes, tirets, ponctuation) — décision
# de l'utilisateur du 12/10 : toute la liste, pas une sélection. Seule une valeur HORS de cette liste est refusée
# en 400, avant la garde. À relire au schéma si fal ajoute des effets (le banc compte 154).
EFFETS_PIXVERSE = (
    "Kiss Me AI", "Kiss", "Muscle Surge", "Warmth of Jesus", "Anything, Robot", "The Tiger Touch", "Hug",
    "Holy Wings", "Microwave", "Zombie Mode", "Squid Game", "Baby Face", "Black Myth: Wukong", "Long Hair Magic",
    "Leggy Run", "Fin-tastic Mermaid", "Punch Face", "Creepy Devil Smile", "Thunder God", "Eye Zoom Challenge",
    "Who's Arrested?", "Baby Arrived", "Werewolf Rage", "Bald Swipe", "BOOM DROP", "Huge Cutie", "Liquid Metal",
    "Sharksnap!", "Dust Me Away", "3D Figurine Factor", "Bikini Up", "My Girlfriends", "My Boyfriends",
    "Subject 3 Fever", "Earth Zoom", "Pole Dance", "Vroom Dance", "GhostFace Terror", "Dragon Evoker",
    "Skeletal Bae", "Summoning succubus", "Halloween Voodoo Doll", "3D Naked-Eye AD", "Package Explosion",
    "Dishes Served", "Ocean ad", "Supermarket AD", "Tree doll", "Come Feel My Abs", "The Bicep Flex",
    "London Elite Vibe", "Flora Nymph Gown", "Christmas Costume", "It's Snowy", "Reindeer Cruiser",
    "Snow Globe Maker", "Pet Christmas Outfit", "Adopt a Polar Pal", "Cat Christmas Box", "Starlight Gift Box",
    "Xmas Poster", "Pet Christmas Tree", "City Santa Hat", "Stocking Sweetie", "Christmas Night",
    "Xmas Front Page Karma", "Grinch's Xmas Hijack", "Giant Product", "Truck Fashion Shoot", "Beach AD",
    "Shoal Surround", "Mechanical Assembly", "Lighting AD", "Billboard AD", "Product close-up", "Parachute Delivery",
    "Dreamlike Cloud", "Macaron Machine", "Poster AD", "Truck AD", "Graffiti AD", "3D Figurine Factory",
    "The Exclusive First Class", "Art Zoom Challenge", "I Quit", "Hitchcock Dolly Zoom", "Smell the Lens",
    "I believe I can fly", "Strikout Dance", "Courtside Cam", "Pit Crew Moment", "K-Baseball Sprint",
    "Toddler Doodle", "Idol Ending", "Apex Dance", "OmniHero Forge", "Palm Decode", "The Age Ripple",
    "My Future Is Limitless", "Knee Slide", "Epic Goal Save", "Sideline Ball Boy", "Cup Celebration", "Victory Roar",
    "Vuvuzela Fan", "World Champion Lift", "Tunnel to Captain", "Liquid Soccer Morph", "Jump Into Crowd 2",
    "Golden Pitch Crasher", "Stadium Fan Cam", "Broadcast Moto GP", "The Grotesque Clay", "Rookie Star Card",
    "The Final Hug", "Sharp Post-Match Comment", "Street Maverick", "Pitch Legend", "One Step At A Time",
    "Birthday Mirror", "Superstar Lobby", "Final Battle Room", "Top of the World", "Mini Me Unboxed",
    "WonderPOP Surprise", "White Chicks", "Kiss me", "What a Day", "The Last Leap at Sunset",
    "Tiny Sticker Chef Chaos", "Mini Squeeze Toy", "Tearful Gunman", "Street Fashion Caricature", "Mini Me Makeover",
    "Street Art Awakening", "Hug Together", "ACAI dance Duet", "PUBG Winner Hit!", "Blocky Mini-Me",
    "Cheat Day Busted", "MiniSocial Recharge", "My Little Perler Charm", "Where did this cobweb come from?",
    "Holy Beast Summoning Technique", "IT'S THE FIRST OF THE MONTH", "Pet Editorial", "Three lifetime bond",
    "Pixel World", "Mint in Box", "Hands up, Hand", "Flora Nymph Go", "Somber Embrace", "Beam me up", "Suit Swagger",
)


def _o(choix=None, defaut=None, num=None, entier=False, bool_=False, requis=False, cible=None):
    """Une option d'un geste : `choix` (énumération), `num` (lo, hi), `bool_` ; `defaut` envoyé quand l'écran n'en
    dit rien (None : rien n'est envoyé) ; `cible` = le nom du champ fal (défaut : le même nom)."""
    return {"choix": tuple(choix) if choix else None, "defaut": defaut, "num": num, "entier": bool(entier),
            "bool": bool(bool_), "requis": bool(requis), "cible": cible}


_SEED = _o(num=(0, 2147483647), entier=True)
_LTX = {"resolution": _o(("480p", "720p"), "720p"), "seed": _SEED}


def _g(label, endpoint, unite, prix, phrase, entree="video", prompt=None, image=None, options=None, fixe=None,
       video_s=None, video_ext=None, image_champ=None):
    """Une entrée du registre. `prompt` / `image` : None (le geste n'en prend pas), "facultatif" ou "requis" ;
    `image_champ` : le champ fal de l'image (chaîne, ou liste si le champ est une liste d'URL)."""
    return {"label": label, "endpoint": endpoint, "unite": unite, "prix": prix, "phrase": phrase, "entree": entree,
            "prompt": prompt, "image": image, "image_champ": image_champ, "options": dict(options or {}),
            "fixe": dict(fixe or {}), "video_s": video_s, "video_ext": tuple(video_ext) if video_ext else None}


# ORDRE = ordre des cartes (rail Son & VFX, section IA du rack). `phrase` : la phrase de l'utilisateur (l'écran la
# traduit par vfx.ia.<id>.phrase ; celle-ci sert au catalogue et aux messages).
REGISTRE: dict[str, dict] = {
    "relight-h3": _g(
        "Rééclairer (MiniMax H3)", "minimax/h3-max/relight", "s", "vfx_relight_usd_per_s",
        "Rééclairer : donnez une image de la lumière voulue.", image="requis",
        image_champ="reference_image_url",
        options={"resolution": _o(("480P", "768P", "1080P", "2K"), "768P"),
                 "aspect_ratio": _o(("adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"), "adaptive"),
                 "seed": _SEED},
        video_s=(0.0, 15.0)),
    "inserer-h3": _g(
        "Insérer une scène (MiniMax H3)", "minimax/h3-max/insert-video", "s", "vfx_insert_usd_per_s",
        "Insérer une scène : dites où elle commence, où le plan reprend, et ce qui s'y passe.",
        prompt="facultatif", image="facultatif", image_champ=["reference_image_urls"],
        options={"start_time": _o(num=(1.625, 60.0), requis=True),
                 "resume_time": _o(num=(0.0, 60.0), requis=True),
                 "duration": _o(num=(5.0, 13.0), defaut=5),
                 "resolution": _o(("480p", "768p"), "768p"),
                 "color_match": _o(bool_=True), "enable_prompt_expansion": _o(bool_=True), "seed": _SEED},
        video_s=(0.0, 60.0)),
    "effacer-perso": _g(
        "Effacer un personnage (plaque propre)", "fal-ai/ltx-2.3-quality/clean-plate", "mp", "vfx_ltx_usd_per_mp",
        "Effacer un personnage : le décor reste, la personne disparaît.", prompt="facultatif", options=_LTX),
    "effacer-objet": _g(
        "Effacer un objet nommé", "fal-ai/void-video-inpainting", "video", "vfx_void_usd",
        "Effacer un objet : nommez-le, puis décrivez le fond qui doit le remplacer.", prompt="requis",
        options={"mask_prompt": _o(requis=True), "enable_pass2_refinement": _o(bool_=True), "seed": _SEED}),
    "jour-nuit": _g(
        "Jour → nuit", "fal-ai/ltx-2.3-quality/day-to-night", "mp", "vfx_ltx_usd_per_mp",
        "Jour → nuit : le même plan, tourné de nuit.", prompt="facultatif", options=_LTX),
    "eau": _g(
        "Simulation d'eau", "fal-ai/ltx-2.3-quality/water-simulation", "mp", "vfx_ltx_usd_per_mp",
        "Simulation d'eau : décrivez l'eau voulue (pluie, inondation, vagues…).", prompt="facultatif",
        options=_LTX),
    "coloriser": _g(
        "Coloriser", "fal-ai/ltx-2.3-quality/colorization", "mp", "vfx_colorisation_usd_per_mp",
        "Coloriser : un plan en noir et blanc retrouve ses couleurs.", prompt="facultatif", options=_LTX),
    "retoucher-kling": _g(
        "Modifier par une phrase (Kling O3)", "fal-ai/kling-video/o3/pro/video-to-video/edit", "s",
        "vfx_kling_edit_usd_per_s", "Modifier par une phrase : décrivez le changement, le mouvement et le son restent.",
        prompt="requis", image="facultatif", image_champ=["image_urls"], fixe={"keep_audio": True},
        video_s=(3.0, 15.0), video_ext=(".mp4", ".mov")),
    "retoucher-flux3": _g(
        "Modifier par une phrase (rapide)", "blackforestlabs/flux-3/edit-video", "s", "vfx_flux3_edit_usd_per_s",
        "Modifier par une phrase, en rapide : décrivez le changement voulu.", prompt="requis",
        video_s=(0.0, 15.0), video_ext=(".mp4",)),
    "recadrer": _g(
        "Changer le format (9:16 ↔ 16:9)", "fal-ai/ltx-2.3/reframe", "s", "vfx_reframe_usd_per_s",
        "Changer le format : choisissez le nouveau cadre, l'IA complète les bords.",
        options={"aspect_ratio": _o(("1:1", "4:5", "5:4", "9:16", "16:9"), "9:16"),
                 "resolution": _o(("720p", "1080p"), "720p")}),
    "agrandir": _g(
        "Agrandir / netteté (Topaz)", "topaz/upscale/video/precision", "tranche10s", "vfx_topaz_usd_per_10s",
        "Agrandir : la vidéo gagne en taille et en netteté (x2 par défaut).",
        options={"upscale_factor": _o(num=(1.0, 4.0), defaut=2)}, fixe={"model": "Proteus"}),
    "effets-pixverse": _g(
        "Effet prêt à l'emploi (PixVerse)", "fal-ai/pixverse/v5.5/effects", "effet", "vfx_pixverse_usd_5s",
        "Effet prêt à l'emploi : une image devient une courte vidéo animée.", entree="image", image="requis",
        image_champ="image_url",
        options={"effect": _o(EFFETS_PIXVERSE, requis=True), "duration": _o(("5", "8", "10"), "5"),
                 "resolution": _o(("360p", "540p", "720p", "1080p"), "720p")}),
}


def ids() -> list[str]:
    return list(REGISTRE)


def entree(mid: str) -> dict:
    """L'entrée d'un geste — ValueError nommée si l'id est hors du registre."""
    e = REGISTRE.get(str(mid or ""))
    if e is None:
        raise ValueError(f"geste VFX IA inconnu : {str(mid)[:40]!r} (connus : {', '.join(REGISTRE)})")
    return e


def cle_manquante(mid: str) -> str | None:
    """« FAL_KEY » si la clé fal n'est pas posée (tous les gestes passent par fal), sinon None."""
    return None if str(getattr(settings, "FAL_KEY", "") or "").strip() else "FAL_KEY"


# ─────────────────────────────── options ──────────────────────────────────

def options_valides(mid: str, options) -> dict:
    """Les options de l'écran, VALIDÉES contre le schéma du geste et complétées de leurs défauts : clé inconnue,
    valeur hors énumération, nombre hors bornes, option requise absente -> ValueError nommée (la route en fait un 400
    AVANT la garde). Les règles croisées (1080p interdit en 10 s, reprise avant le début) sont vérifiées ici aussi."""
    e = entree(mid)
    if options in (None, ""):
        options = {}
    if not isinstance(options, dict):
        raise ValueError("options : un objet {nom: valeur} est attendu")
    inconnues = sorted(set(map(str, options)) - set(e["options"]))
    if inconnues:
        permis = ", ".join(e["options"]) or "aucune"
        raise ValueError(f"{e['label']} : option inconnue {', '.join(inconnues)} (permises : {permis})")
    out = {}
    for nom, spec in e["options"].items():
        v = options.get(nom)
        if v in (None, ""):
            if spec["requis"]:
                raise ValueError(f"{e['label']} : l'option « {nom} » est requise")
            if spec["defaut"] is not None:
                out[nom] = spec["defaut"]
            continue
        if spec["choix"]:
            if str(v) not in spec["choix"]:
                raise ValueError(f"{e['label']} : « {str(v)[:40]} » refusé pour {nom} "
                                 f"(permis : {', '.join(spec['choix'][:12])}{'…' if len(spec['choix']) > 12 else ''})")
            out[nom] = str(v)
        elif spec["bool"]:
            if not isinstance(v, bool):
                raise ValueError(f"{e['label']} : {nom} attend vrai ou faux")
            out[nom] = v
        elif spec["num"]:
            if isinstance(v, bool):
                raise ValueError(f"{e['label']} : {nom} attend un nombre")
            try:
                x = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"{e['label']} : {nom} attend un nombre")
            lo, hi = spec["num"]
            if x != x or not lo <= x <= hi:
                raise ValueError(f"{e['label']} : {nom} doit valoir de {lo:g} à {hi:g} (reçu {x:g})")
            if spec["entier"]:
                if x != int(x):
                    raise ValueError(f"{e['label']} : {nom} attend un entier")
                x = int(x)
            out[nom] = x
        else:   # texte libre (mask_prompt)
            s = str(v).strip()
            if not s:
                if spec["requis"]:
                    raise ValueError(f"{e['label']} : l'option « {nom} » est requise")
                continue
            if len(s) > 300:
                raise ValueError(f"{e['label']} : {nom} trop long ({len(s)} caractères, 300 au plus)")
            out[nom] = s
    if mid == "inserer-h3" and out["resume_time"] < out["start_time"]:
        raise ValueError(f"{e['label']} : la reprise ({out['resume_time']:g} s) précède le début "
                         f"({out['start_time']:g} s)")
    if mid == "effets-pixverse" and out.get("duration") == "10" and out.get("resolution") == "1080p":
        raise ValueError(f"{e['label']} : 1080p n'existe pas en 10 s (5 ou 8 s en 1080p, ou 10 s en 720p)")
    return out


def prompt_valide(mid: str, prompt) -> str:
    """La description nettoyée ; ValueError si le geste l'exige et qu'elle manque, ou si elle est trop longue."""
    e = entree(mid)
    p = str(prompt or "").strip()
    if len(p) > PROMPT_MAX:
        raise ValueError(f"{e['label']} : description trop longue ({len(p)} caractères, {PROMPT_MAX} au plus)")
    if e["prompt"] == "requis" and not p:
        raise ValueError(f"{e['label']} : décrivez le changement voulu (« prompt » vide)")
    return p if e["prompt"] else ""


def images_ltx(secondes) -> int:
    """num_frames envoyé aux effets LTX : la durée de la source à 24 i/s, arrondie au-dessus (au quart d'image
    près), 9 images au moins. La même fonction chiffre le devis et fabrique la requête."""
    try:
        s = max(0.0, float(secondes or 0))
    except (TypeError, ValueError):
        s = 0.0
    n = s * FPS_LTX
    k = round(n)
    # une durée arrondie au millième (le devis) ne doit pas gagner une image : à moins d'un quart d'image près, on
    # garde l'image entière ; sinon on couvre la durée (arrondi au-dessus)
    return max(IMAGES_LTX[0], int(k if abs(n - k) < 0.25 else math.ceil(n)))


def source_refusee(mid: str, chemin, secondes) -> str | None:
    """La raison NOMMÉE pour laquelle ce geste refuse cette source (format, durée hors bornes, trop d'images LTX),
    None si elle passe. La route en fait un 400 AVANT la garde."""
    e = entree(mid)
    ext = Path(str(chemin)).suffix.lower()
    if e["entree"] == "image":
        return None if ext in EXT_IMAGE else f"{e['label']} part d'une image ({', '.join(EXT_IMAGE)})"
    if e["video_ext"] and ext not in e["video_ext"]:
        return f"{e['label']} n'accepte que {', '.join(e['video_ext'])} (vidéo {ext or 'sans extension'})"
    try:
        s = float(secondes or 0)
    except (TypeError, ValueError):
        s = 0.0
    b = e["video_s"]
    if b and not b[0] <= s <= b[1]:
        bas = f"de {b[0]:g} à {b[1]:g} s" if b[0] else f"{b[1]:g} s au plus"
        return f"{e['label']} : la vidéo doit durer {bas} (celle-ci : {s:.1f} s)"
    if e["unite"] == "mp" and images_ltx(s) > IMAGES_LTX[1]:
        return (f"{e['label']} : {IMAGES_LTX[1]} images au plus à {FPS_LTX} i/s, soit "
                f"{IMAGES_LTX[1] / FPS_LTX:.1f} s (celle-ci : {s:.1f} s) — coupez le plan d'abord")
    return None


def insertion_refusee(opts: dict, secondes) -> str | None:
    """Insérer une scène : la reprise doit tomber DANS la vidéo source."""
    try:
        s = float(secondes or 0)
    except (TypeError, ValueError):
        s = 0.0
    if opts.get("start_time", 0) > s or opts.get("resume_time", 0) > s:
        return (f"Insérer une scène : début ({opts.get('start_time', 0):g} s) et reprise "
                f"({opts.get('resume_time', 0):g} s) doivent tomber dans la vidéo ({s:.1f} s)")
    return None


# ──────────────────────────────── requête ─────────────────────────────────

def build_request(mid: str, video_url=None, image_url=None, prompt=None, options=None, secondes=None) -> tuple:
    """(endpoint, arguments) de l'appel fal d'un geste : les arguments fixes (keep_audio, model), la source (vidéo,
    ou image pour PixVerse), l'image de référence, la description, les options validées ; pour les effets LTX,
    num_frames + frames_per_second calculés depuis `secondes`. ValueError : id inconnu, source / image / description
    / option requise manquante, option hors schéma."""
    e = entree(mid)
    opts = options_valides(mid, options)
    p = prompt_valide(mid, prompt)
    args = dict(e["fixe"])
    if e["entree"] == "video":
        if not str(video_url or "").strip():
            raise ValueError(f"{e['label']} part d'une vidéo : aucune vidéo fournie")
        args["video_url"] = str(video_url)
    img = str(image_url or "").strip()
    if e["image"] == "requis" and not img:
        quoi = "l'image à animer" if e["entree"] == "image" else "l'image de la lumière voulue"
        raise ValueError(f"{e['label']} : donnez {quoi} (image_filename)")
    if img and e["image"]:
        ch = e["image_champ"]
        if isinstance(ch, list):
            args[ch[0]] = [img]
        else:
            args[ch] = img
    if p:
        args["prompt"] = p
    for nom, v in opts.items():
        args[e["options"][nom]["cible"] or nom] = v
    if e["unite"] == "mp" and secondes is not None:
        args["num_frames"] = min(IMAGES_LTX[1], images_ltx(secondes))
        args["frames_per_second"] = FPS_LTX
    return e["endpoint"], args


# ─────────────────────────────────── devis ────────────────────────────────

def _pair(n: float) -> int:
    k = int(math.ceil(n - 1e-9))
    return k + (k % 2)


def classe_topaz(hauteur, facteur) -> str:
    """La classe de prix Topaz : la HAUTEUR de sortie (hauteur source x facteur) — <= 720 « 720p », <= 1080 « 1080p »,
    au-delà « 4k ». Hauteur inconnue : 1080 supposée (prudent : x2 = 4k)."""
    try:
        h = float(hauteur or 0) or 1080.0
    except (TypeError, ValueError):
        h = 1080.0
    try:
        f = float(facteur or 2)
    except (TypeError, ValueError):
        f = 2.0
    s = h * f
    return "720p" if s <= 720 else "1080p" if s <= 1080 else "4k"


def megapixels(secondes, resolution, largeur=None, hauteur=None) -> tuple:
    """(MP facturés, images, largeur, hauteur) d'un effet LTX : la résolution choisie est le côté COURT (480 ou 720),
    l'autre suit le format de la source (pair, arrondi au-dessus ; 16:9 si les dimensions sont illisibles — 480p =
    854 x 480, 720p = 1280 x 720), images = num_frames envoyé ; MP = ceil(l x h x images / 1e6)."""
    court = 480 if str(resolution) == "480p" else 720
    try:
        w, h = float(largeur or 0), float(hauteur or 0)
    except (TypeError, ValueError):
        w = h = 0.0
    ratio = (max(w, h) / min(w, h)) if w > 0 and h > 0 else 16 / 9
    long_ = _pair(court * ratio)
    imgs = min(IMAGES_LTX[1], images_ltx(secondes))
    mp = int(math.ceil(court * long_ * imgs / 1e6 - 1e-9))
    portrait = h > w > 0
    lw, lh = (court, long_) if portrait else (long_, court)
    return mp, imgs, lw, lh


def unites(mid: str, op: dict) -> tuple:
    """(quantité, détail) facturés d'une demande, dans l'unité du geste. `op` : {secondes, options, largeur,
    hauteur} (options déjà validées ou brutes : les défauts du geste comblent ce qui manque)."""
    e = REGISTRE[mid]
    o = dict(op.get("options") or {})
    for nom, spec in e["options"].items():
        if o.get(nom) in (None, "") and spec["defaut"] is not None:
            o[nom] = spec["defaut"]
    try:
        sec = max(0.0, float(op.get("secondes") or 0))
    except (TypeError, ValueError):
        sec = 0.0
    u = e["unite"]
    if u == "s":
        if mid == "inserer-h3":
            d = float(o.get("duration") or 5)
            return d, f"scène générée {d:g} s · {o.get('resolution')}"
        res = o.get("resolution")
        return sec, f"{sec:g} s" + (f" · {res}" if res else "")
    if u == "mp":
        mp, imgs, lw, lh = megapixels(sec, o.get("resolution"), op.get("largeur"), op.get("hauteur"))
        return mp, f"{lw}x{lh} x {imgs} images = {mp} MP"
    if u == "tranche10s":
        t = max(1, int(math.ceil(sec / 10 - 1e-9)))
        return t, f"{sec:g} s -> {t} x 10 s · {classe_topaz(op.get('hauteur'), o.get('upscale_factor'))}"
    if u == "effet":
        return 1, f"{o.get('duration')} s · {o.get('resolution')}"
    # « video » : une vidéo ; la passe 2 et le masque SAM 3 sont dans le taux
    det = "passe 2" if o.get("enable_pass2_refinement") else "passe 1"
    if o.get("mask_prompt"):
        det += " + masque SAM 3"
    return 1, det


def op_vfx(mid: str, secondes=None, options=None, largeur=None, hauteur=None) -> dict:
    """L'op de devis (pricing.estimate, kind « vfx_ia ») d'une demande — LE même pour le devis, la garde et l'`usd`
    rendu après le tir."""
    entree(mid)
    return {"kind": "vfx_ia", "modele": str(mid), "secondes": None if secondes is None else round(float(secondes), 3),
            "options": dict(options or {}), "largeur": largeur, "hauteur": hauteur}


# ─────────────────────────────── source (ffprobe) ─────────────────────────

def dimensions(path: Path) -> tuple:
    """(largeur, hauteur) du premier flux vidéo (ffprobe), (None, None) si illisible."""
    from app.services.sfx_service import _bin
    try:
        out = subprocess.run(
            [_bin("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=p=0:s=x", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
        w, h = (int(x) for x in out[0].split("x")[:2])
        return (w, h) if w > 0 and h > 0 else (None, None)
    except (ValueError, IndexError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None, None


# ─────────────────────────────────── tir ──────────────────────────────────

async def _upload(path: Path) -> str:                               # seam (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._upload(path)


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._fal_subscribe(endpoint, arguments)


async def _download(url: str, dest: Path) -> None:                  # seam (celle de sfx_service)
    from app.services import sfx_service as _S
    await _S._download(url, dest)


def _url_video(res) -> str | None:
    if not isinstance(res, dict):
        return None
    v = res.get("video")
    for x in (v if isinstance(v, list) else [v]):
        u = x.get("url") if isinstance(x, dict) else (x if isinstance(x, str) and x.startswith("http") else None)
        if u:
            return str(u)
    return None


async def appliquer_vfx(mid: str, video: Path | None = None, image: Path | None = None, prompt=None,
                        options=None, secondes=None, dossier: Path | None = None) -> dict:
    """Tire UN geste du registre et range la vidéo rendue. PAYANT : la route a passé la clé (503) et la garde des
    plafonds AVANT. La source (vidéo, ou image pour PixVerse) et l'image de référence partent par `_upload` ; la
    vidéo rendue -> `dossier` (outputs/uploads par défaut) sous `vfxia_<hex8>.<ext>`. Rend {"video": Path,
    "seed": int|None}. ValueError : requête invalide ; RuntimeError : réponse fal sans vidéo."""
    from uuid import uuid4
    from app.services.sfx_service import _ext, _EXT_VIDEO
    e = entree(mid)
    build_request(mid, "http://a-blanc" if e["entree"] == "video" else None,
                  "http://a-blanc" if image is not None else None, prompt, options, secondes)
    url_video = url_image = None
    if e["entree"] == "video":
        if video is None or not Path(video).is_file():
            raise ValueError("vidéo source introuvable")
        url_video = await _upload(Path(video))
    if image is not None:
        if not Path(image).is_file():
            raise ValueError("image introuvable")
        url_image = await _upload(Path(image))
    endpoint, args = build_request(mid, url_video, url_image, prompt, options, secondes)
    logger.info("vfx_ia [{}] -> {} · args={}", mid, endpoint,
                {k: v for k, v in args.items() if k not in ("video_url", "image_url", "reference_image_url")})
    res = await _fal_subscribe(endpoint, args)
    u = _url_video(res)
    if not u:
        cles = ", ".join(map(str, res)) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"fal.ai ({e['label']}) : aucune vidéo dans la réponse (clés : {cles})")
    d = Path(dossier or (settings.outputs_path / "uploads"))
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"vfxia_{uuid4().hex[:8]}{_ext(u, '.mp4', _EXT_VIDEO)}"
    while dest.exists():
        dest = d / f"vfxia_{uuid4().hex[:8]}_{os.urandom(2).hex()}{dest.suffix}"
    await _download(u, dest)
    seed = res.get("seed") if isinstance(res, dict) else None
    return {"video": dest, "seed": seed if isinstance(seed, int) else None}


appliquer = appliquer_vfx   # le nom du plan (t188) ; le recensement des dépenses suit `appliquer_vfx`
