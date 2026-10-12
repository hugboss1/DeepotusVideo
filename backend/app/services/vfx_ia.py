# -*- coding: utf-8 -*-
"""t188 (G6, plan « Génération IA enrichie ») — les VFX IA : une vidéo (ou une image) -> une vidéo retouchée.

UN registre (`REGISTRE`, 12 gestes, tous servis par la clé fal), schémas fal relus le 12/10/2026 :
  · relight-h3       minimax/h3-max/relight : video_url + reference_image_url REQUIS ; resolution 480P|768P|1080P|2K
                     (défaut chez nous 768P), aspect_ratio (défaut chez nous « adaptive » : le schéma pose 16:9, qui
                     recadrerait une source verticale), seed. Source de 15 s au plus et de 56 images au moins à 24 i/s
                     (environ 2,34 s), schéma ; la référence est un RENDU DE SPHÈRE montrant l'éclairage voulu.
  · inserer-h3       minimax/h3-max/insert-video : video_url, start_time (1,625 à 60 s), resume_time (> 1,625 et <= 60 s)
                     REQUIS ;
                     prompt, duration (scène générée, 5 à 13 s, défaut 5 — TOUJOURS envoyée : c'est elle qui est
                     facturée), resolution 480p|768p, reference_image_urls, color_match, enable_prompt_expansion, seed.
  · effacer-perso    fal-ai/ltx-2.3-quality/clean-plate      } video_url requis ; prompt, resolution 480p|720p (côté
  · jour-nuit        fal-ai/ltx-2.3-quality/day-to-night     } COURT, l'autre suit le format de la source), seed ;
  · eau              fal-ai/ltx-2.3-quality/water-simulation } num_frames / frames_per_second calculés ICI depuis la
  · coloriser        fal-ai/ltx-2.3-quality/colorization     } durée de la source (24 i/s, 9 à 481 images : au-delà,
                     refus nommé, jamais de coupe muette) ; budget IC-LoRA du schéma (« ~6 s en 720p, ~15 s en 480p »,
                     422 au-delà) : 145 images au plus en 720p, 361 en 480p, refus nommé avant la garde.
                     enable_detail_refine n'est JAMAIS envoyé (x4 le prix).
  · effacer-objet    fal-ai/void-video-inpainting : video_url + prompt (le fond voulu) REQUIS ; mask_prompt (l'objet à
                     effacer, exigé chez nous : sans masque vidéo fourni, c'est lui qui fait générer le masque SAM 3),
                     enable_pass2_refinement.
  · retoucher-kling  fal-ai/kling-video/o3/pro/video-to-video/edit : prompt + video_url REQUIS ; keep_audio TOUJOURS
                     True (le son du plan reste) ; image_urls (une image de référence). Source .mp4/.mov de 3 à 15 s,
                     côtés de 720 à 3 840 px, 200 Mo au plus.
  · retoucher-flux3  blackforestlabs/flux-3/edit-video : prompt + video_url REQUIS. MP4 de MOINS de 15 s et de 50 Mo.
  · recadrer         fal-ai/ltx-2.3/reframe : video_url ; aspect_ratio 1:1|4:5|5:4|9:16|16:9 (défaut chez nous 9:16),
                     resolution 720p|1080p (défaut chez nous 720p ; le schéma pose 1080p, deux fois plus cher). 60 s au
                     plus (schéma).
  · agrandir         topaz/upscale/video/precision : video_url ; upscale_factor 1 à 4 (défaut 2), model « Proteus ».
  · effets-pixverse  fal-ai/pixverse/v5.5/effects : effect + image_url REQUIS ; duration 5|8|10, resolution
                     360p|540p|720p|1080p (1080p interdit en 10 s : refus nommé). Une IMAGE -> une vidéo.

PRIX (pages fal relues le 12/10/2026 ; les tarifs vivent dans pricing.DEFAULTS, `pricing.taux_vfx` est LA fonction de
taux, `unites` ci-dessous la quantité) : unité « s » (seconde de source, ou de scène générée pour l'insertion), « mp »
(mégapixel généré = largeur x hauteur x images, arrondi au MP supérieur), « video », « tranche10s » (Topaz : tranche
de 10 s de SORTIE arrondie une fois par travail, classe de résolution = CÔTÉ COURT de sortie), « effet » (PixVerse : la
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
from app.i18n import Message, Nom, Refus   # t192 : refus traduisibles (texte = le français)

PROMPT_MAX = 1500
FPS_LTX = 24                        # images par seconde envoyées aux quatre effets LTX (défaut du schéma)
IMAGES_LTX = (9, 481)               # num_frames du schéma LTX
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
       video_s=None, video_ext=None, image_champ=None, strict=False, images_min=None, cote=None, octets_max=None):
    """Une entrée du registre. `prompt` / `image` : None (le geste n'en prend pas), "facultatif" ou "requis" ;
    `image_champ` : le champ fal de l'image (chaîne, ou liste si le champ est une liste d'URL). Bornes de la SOURCE
    relues au schéma : `video_s` (secondes ; `strict` : la borne haute est exclue, « under 15 seconds »),
    `images_min` (à 24 i/s), `cote` (px, côté court et côté long), `octets_max` (Mo décimaux, prudent)."""
    return {"label": label, "endpoint": endpoint, "unite": unite, "prix": prix, "phrase": phrase, "entree": entree,
            "prompt": prompt, "image": image, "image_champ": image_champ, "options": dict(options or {}),
            "fixe": dict(fixe or {}), "video_s": video_s, "video_ext": tuple(video_ext) if video_ext else None,
            "strict": bool(strict), "images_min": images_min, "cote": cote, "octets_max": octets_max}


# ORDRE = ordre des cartes (rail Son & VFX, section IA du rack). `phrase` : la phrase de l'utilisateur (l'écran la
# traduit par vfx.ia.<id>.phrase ; celle-ci sert au catalogue et aux messages).
REGISTRE: dict[str, dict] = {
    "relight-h3": _g(
        "Rééclairer (MiniMax H3)", "minimax/h3-max/relight", "s", "vfx_relight_usd_per_s",
        "Rééclairer : donnez une image de la LUMIÈRE voulue (idéalement une sphère éclairée comme la scène doit l'être).",
        image="requis", image_champ="reference_image_url", images_min=56,
        options={"resolution": _o(("480P", "768P", "1080P", "2K"), "768P"),
                 "aspect_ratio": _o(("adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"), "adaptive"),
                 "seed": _SEED},
        video_s=(0.0, 15.0)),
    "inserer-h3": _g(
        "Insérer une scène (MiniMax H3)", "minimax/h3-max/insert-video", "s", "vfx_insert_usd_per_s",
        "Insérer une scène : dites où elle commence, où le plan reprend, et ce qui s'y passe.",
        prompt="facultatif", image="facultatif", image_champ=["reference_image_urls"],
        options={"start_time": _o(num=(1.625, 60.0), requis=True),
                 "resume_time": _o(num=(1.625, 60.0), requis=True),   # > 1,625 STRICT (vérifié plus bas)
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
        video_s=(3.0, 15.0), video_ext=(".mp4", ".mov"), cote=(720, 3840), octets_max=200),
    "retoucher-flux3": _g(
        "Modifier par une phrase (rapide)", "blackforestlabs/flux-3/edit-video", "s", "vfx_flux3_edit_usd_per_s",
        "Modifier par une phrase, en rapide : décrivez le changement voulu.", prompt="requis",
        video_s=(0.0, 15.0), video_ext=(".mp4",), strict=True, octets_max=50),
    "recadrer": _g(
        "Changer le format (9:16 ↔ 16:9)", "fal-ai/ltx-2.3/reframe", "s", "vfx_reframe_usd_per_s",
        "Changer le format : choisissez le nouveau cadre, l'IA complète les bords.",
        options={"aspect_ratio": _o(("1:1", "4:5", "5:4", "9:16", "16:9"), "9:16"),
                 "resolution": _o(("720p", "1080p"), "720p")}, video_s=(0.0, 60.0)),
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
    valeur hors énumération, nombre hors bornes, texte qui n'est pas une chaîne, option requise absente ->
    ValueError nommée (la route en fait un 400 AVANT la garde). Les règles croisées (1080p interdit en 10 s, reprise
    avant le début ou à 1,625 s pile) sont vérifiées ici aussi."""
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
                raise Refus("vfx.ia.option_requise", modele=Nom(mid, e['label']), nom=nom)
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
                raise Refus("vfx.ia.option_bornes", modele=Nom(mid, e['label']), nom=nom, lo=f"{lo:g}", hi=f"{hi:g}",
                            x=f"{x:g}")
            if spec["entier"]:
                if x != int(x):
                    raise ValueError(f"{e['label']} : {nom} attend un entier")
                x = int(x)
            out[nom] = x
        else:   # texte libre (mask_prompt) : une CHAÎNE, rien d'autre
            if not isinstance(v, str):
                raise ValueError(f"{e['label']} : {nom} attend un texte")
            s = v.strip()
            if not s:
                if spec["requis"]:
                    raise Refus("vfx.ia.option_requise", modele=Nom(mid, e['label']), nom=nom)
                continue
            if len(s) > 300:
                raise Refus("vfx.ia.option_trop_longue", modele=Nom(mid, e['label']), nom=nom, n=len(s))
            out[nom] = s
    if mid == "inserer-h3":
        if out["resume_time"] <= 1.625:   # exclusiveMinimum du schéma
            raise Refus("vfx.ia.reprise_apres", modele=Nom(mid, e['label']), x=f"{out['resume_time']:g}")
        if out["resume_time"] < out["start_time"]:
            raise Refus("vfx.ia.reprise_avant_debut", modele=Nom(mid, e['label']), reprise=f"{out['resume_time']:g}",
                        debut=f"{out['start_time']:g}")
    if mid == "effets-pixverse" and out.get("duration") == "10" and out.get("resolution") == "1080p":
        raise Refus("vfx.ia.pixverse_1080p", modele=Nom(mid, e['label']))
    return out


def options_completees(mid: str, options) -> dict:
    """Les options d'une demande DÉJÀ validée (ou brutes, au catalogue), les défauts du geste comblant ce qui manque —
    partagée par `unites` (la quantité) et pricing.taux_vfx (le taux)."""
    e = REGISTRE[mid]
    o = dict(options or {})
    for nom, spec in e["options"].items():
        if o.get(nom) in (None, "") and spec["defaut"] is not None:
            o[nom] = spec["defaut"]
    return o


def prompt_valide(mid: str, prompt) -> str:
    """La description nettoyée ; ValueError si le geste l'exige et qu'elle manque, ou si elle est trop longue."""
    e = entree(mid)
    p = str(prompt or "").strip()
    if len(p) > PROMPT_MAX:
        raise Refus("ia.prompt.trop_long", modele=Nom(mid, e['label']), n=len(p), max=PROMPT_MAX)
    if e["prompt"] == "requis" and not p:
        raise Refus("vfx.ia.prompt_requis", modele=Nom(mid, e['label']))
    return p if e["prompt"] else ""


def image_refusee(mid: str, presente: bool) -> str | None:
    """LE refus d'image (route et build_request) : image exigée absente, ou image donnée à un geste qui n'en prend
    pas ; None si tout va."""
    e = entree(mid)
    if presente and not e["image"]:
        return Message("vfx.ia.sans_image", modele=Nom(mid, e['label']))
    if not presente and e["image"] == "requis":
        return Message("vfx.ia.image_a_animer" if e["entree"] == "image" else "vfx.ia.image_lumiere",
                       modele=Nom(mid, e['label']))
    return None


def images_ltx(secondes) -> int:
    """num_frames envoyé aux effets LTX : la durée de la source à 24 i/s, arrondie à l'image supérieure (une
    tolérance d'un millionième d'image absorbe l'erreur de flottant), 9 images au moins. La même fonction chiffre le
    devis et fabrique la requête, sur la MÊME durée (celle de l'op)."""
    try:
        s = max(0.0, float(secondes or 0))
    except (TypeError, ValueError):
        s = 0.0
    return max(IMAGES_LTX[0], int(math.ceil(s * FPS_LTX - 1e-6)))


# budget IC-LoRA des effets LTX quality (schéma : « roughly 6s at 720p or 15s at 480p », 422 au-delà), en images à
# 24 i/s : 6 s x 24 + 1 et 15 s x 24 + 1 (le compte d'images LTX est de la forme 8k + 1)
BUDGET_LTX = {"720p": 145, "480p": 361}


def source_refusee(mid: str, chemin, secondes, options=None, dims=None, octets=None) -> str | None:
    """La raison NOMMÉE pour laquelle ce geste refuse cette source, None si elle passe — la route en fait un 400
    AVANT la garde. Bornes relues au schéma : format, durée (bornes, borne haute exclue si `strict`), images
    minimales à 24 i/s (relight), budget IC-LoRA LTX selon la résolution choisie, côtés en px (Kling), poids."""
    e = entree(mid)
    ext = Path(str(chemin)).suffix.lower()
    if e["entree"] == "image":
        return None if ext in EXT_IMAGE else Message("vfx.ia.source_image", modele=Nom(mid, e['label']),
                                                      exts=', '.join(EXT_IMAGE))
    if e["video_ext"] and ext not in e["video_ext"]:
        return Message("ia.video.format" if ext else "ia.video.format_sans_ext", modele=Nom(mid, e['label']),
                       exts=', '.join(e['video_ext']), ext=ext)
    try:
        s = float(secondes or 0)
    except (TypeError, ValueError):
        s = 0.0
    b = e["video_s"]
    if b and (not b[0] <= s <= b[1] or (e["strict"] and s >= b[1])):
        cle = "ia.video.duree_plage" if b[0] else "ia.video.duree_moins" if e["strict"] else "ia.video.duree_max"
        return Message(cle, modele=Nom(mid, e['label']), lo=f"{b[0]:g}", hi=f"{b[1]:g}", s=f"{s:.1f}")
    if e["images_min"] and s * FPS_LTX < e["images_min"] - 1e-6:
        return Message("vfx.ia.images_min", modele=Nom(mid, e['label']), n=e['images_min'], fps=FPS_LTX,
                       sec=f"{e['images_min'] / FPS_LTX:.2f}", s=f"{s:.1f}")
    if e["unite"] == "mp":
        res = options_completees(mid, options).get("resolution") or "720p"
        n = images_ltx(s)
        if n > IMAGES_LTX[1]:
            return Message("vfx.ia.images_max", modele=Nom(mid, e['label']), n=IMAGES_LTX[1], fps=FPS_LTX,
                           sec=f"{IMAGES_LTX[1] / FPS_LTX:.1f}", s=f"{s:.1f}")
        if n > BUDGET_LTX.get(res, BUDGET_LTX["720p"]):
            m = BUDGET_LTX[res]
            return Message("vfx.ia.budget_720p" if res == "720p" else "vfx.ia.budget", modele=Nom(mid, e['label']),
                           res=res, m=m, fps=FPS_LTX, sec=f"{(m - 1) / FPS_LTX:g}", n=n, s=f"{s:.1f}")
    if e["cote"] and dims and dims[0] and dims[1]:
        lo, hi = e["cote"]
        if min(dims) < lo or max(dims) > hi:
            return Message("vfx.ia.cotes", modele=Nom(mid, e['label']), lo=lo, hi=hi, l=dims[0], h=dims[1])
    if e["octets_max"] and octets is not None:
        lim = e["octets_max"] * 1_000_000
        if octets > lim or (e["strict"] and octets >= lim):
            return Message("vfx.ia.poids_moins" if e['strict'] else "vfx.ia.poids_max", modele=Nom(mid, e['label']),
                           max=e['octets_max'], o=f"{octets / 1e6:.1f}")
    return None


def insertion_refusee(opts: dict, secondes) -> str | None:
    """Insérer une scène : la reprise doit tomber DANS la vidéo source."""
    try:
        s = float(secondes or 0)
    except (TypeError, ValueError):
        s = 0.0
    if opts.get("start_time", 0) > s or opts.get("resume_time", 0) > s:
        return Message("vfx.ia.insertion_hors", debut=f"{opts.get('start_time', 0):g}",
                       reprise=f"{opts.get('resume_time', 0):g}", s=f"{s:.1f}")
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
    refus = image_refusee(mid, bool(img))
    if refus:
        raise ValueError(refus)
    if img:
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


def classe_topaz(largeur, hauteur, facteur) -> str:
    """La classe de prix Topaz : le CÔTÉ COURT de sortie (côté court de la source x facteur) — <= 720 « 720p »,
    <= 1080 « 1080p », au-delà « 4k » (un 1080x1920 vertical est un « 1080p »). Dimensions inconnues : 1080 supposé
    (prudent : x2 = 4k)."""
    try:
        cotes = [float(c) for c in (largeur, hauteur) if c and float(c) > 0]
    except (TypeError, ValueError):
        cotes = []
    court = min(cotes) if cotes else 1080.0
    try:
        f = float(facteur or 2)
    except (TypeError, ValueError):
        f = 2.0
    s = court * f
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
    hauteur} (options validées ou brutes : options_completees comble les défauts)."""
    e = REGISTRE[mid]
    o = options_completees(mid, op.get("options"))
    try:
        sec = max(0.0, float(op.get("secondes") or 0))
    except (TypeError, ValueError):
        sec = 0.0
    u = e["unite"]
    if u == "s":
        if mid == "inserer-h3":
            d = float(o.get("duration") or 5)
            return d, Message("vfx.det.scene", d=f"{d:g}", res=o.get('resolution'))
        res = o.get("resolution")
        return sec, f"{sec:g} s" + (f" · {res}" if res else "")
    if u == "mp":
        mp, imgs, lw, lh = megapixels(sec, o.get("resolution"), op.get("largeur"), op.get("hauteur"))
        return mp, f"{lw}x{lh} x {imgs} images = {mp} MP"
    if u == "tranche10s":
        t = max(1, int(math.ceil(sec / 10 - 1e-9)))
        cl = classe_topaz(op.get("largeur"), op.get("hauteur"), o.get("upscale_factor"))
        return t, Message("vfx.det.topaz", sec=f"{sec:g}", t=t, cl=cl)
    if u == "effet":
        return 1, f"{o.get('duration')} s · {o.get('resolution')}"
    # « video » : une vidéo ; la passe 2 et le masque SAM 3 sont dans le taux
    return 1, Message(("vfx.det.passe2" if o.get("enable_pass2_refinement") else "vfx.det.passe1")
                      + ("_masque" if o.get("mask_prompt") else ""))


def op_vfx(mid: str, secondes=None, options=None, largeur=None, hauteur=None) -> dict:
    """L'op de devis (pricing.estimate, kind « vfx_ia ») d'une demande — LE même pour le devis, la garde, l'`usd`
    rendu après le tir et la requête (la route passe `op["secondes"]` au tir)."""
    entree(mid)
    return {"kind": "vfx_ia", "modele": str(mid), "secondes": None if secondes is None else round(float(secondes), 3),
            "options": dict(options or {}), "largeur": largeur, "hauteur": hauteur}


# ─────────────────────────────── source (ffprobe) ─────────────────────────

def dimensions(path: Path) -> tuple:
    """(largeur, hauteur) AFFICHÉES du premier flux vidéo (ffprobe) : une rotation de 90° ou 270° (side_data
    « rotation », ou l'ancienne balise « rotate ») échange les deux côtés — un téléphone filme en 1920x1080 tourné.
    (None, None) si illisible."""
    import json
    from app.services.sfx_service import _bin
    try:
        out = subprocess.run(
            [_bin("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height:stream_tags=rotate:stream_side_data=rotation", "-of", "json", str(path)],
            check=False, capture_output=True, text=True, timeout=30).stdout
        st = (json.loads(out or "{}").get("streams") or [{}])[0]
        w, h = int(st.get("width") or 0), int(st.get("height") or 0)
        if w <= 0 or h <= 0:
            return None, None
        rot = 0.0
        for sd in st.get("side_data_list") or []:
            if "rotation" in sd:
                rot = float(sd["rotation"])
        if not rot and (st.get("tags") or {}).get("rotate"):
            rot = float(st["tags"]["rotate"])
        if int(round(abs(rot))) % 180 == 90:
            w, h = h, w
        return w, h
    except (ValueError, TypeError, IndexError, KeyError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
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


appliquer = appliquer_vfx   # le nom du plan (t188, « async appliquer ») ; le recensement des dépenses suit `appliquer_vfx`
