# -*- coding: utf-8 -*-
"""Plan-templates T5-T6 (tache #75 du suivi, 03/10/2026) — IMAGE FIXE d'un gabarit et VIGNETTES au contenu reel.

Decisions de l'utilisateur (03/10) :
- les cases image/video d'un gabarit recoivent un ECHANTILLON choisi (une image de la Bibliotheque, gardee dans le
  gabarit : metadata.samples = {slot_name: nom de fichier}) ; faute d'echantillon, une MIRE neutre au nom de la case ;
- l'image est tiree du graphe AVANT l'encodage video (RGB, pleine qualite) ; la video, elle, ne change pas a l'octet ;
- instant reglable, 1 s par defaut (a t = 0 un ticker est vide et une pulsation a moitie) ;
- sequentiel : l'acte qui joue a cet instant ;
- export PNG, JPEG ou WebP vers la Bibliotheque (source « Templates ») avec sa recette ;
- vignettes de galerie a la demande, en cache (cle : gabarit RESOLU — le kit de marque compte — et echantillons),
  une a la fois.
Le plan echouait sur toute case vide (_slot_path leve), laissait la piste son non branchee, et cachait la vignette sans
le kit ni file d'attente. Gratuit partout : ffmpeg et Pillow locaux, jamais un fournisseur paye.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path

FORMATS = {"png": ("PNG", ".png", "image/png"), "jpeg": ("JPEG", ".jpg", "image/jpeg"), "webp": ("WEBP", ".webp", "image/webp")}
EXT_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
INSTANT_DEFAUT = 1.0
VIGNETTE_MAX = 360          # plus grand cote d'une vignette (la galerie l'affiche a 252 au plus, ecrans denses compris)
_CASES = ("video_slot", "image_slot")
VERSION_VIGNETTE = "2"      # a changer si le dessin des vignettes change : invalide tout le cache


def verifier_echantillons(tpl: dict) -> None:
    """ValueError qui nomme le champ : metadata.samples = {slot_name d'une case image/video : nom de fichier image}."""
    md = (tpl or {}).get("metadata")
    if not isinstance(md, dict) or "samples" not in md:
        return
    ech = md["samples"]
    if not isinstance(ech, dict):
        raise ValueError("metadata.samples attend {nom de case : image}.")
    cases = {r.get("slot_name") for r in tpl.get("regions") or [] if r.get("type") in _CASES}
    for nom, fichier in ech.items():
        if nom not in cases:
            raise ValueError(f"metadata.samples : « {nom} » n'est pas une case image ou vidéo de ce gabarit.")
        if not isinstance(fichier, str) or Path(fichier).name != fichier or Path(fichier).suffix.lower() not in EXT_IMAGES:
            raise ValueError(f"metadata.samples.{nom} : un nom d'image de la Bibliothèque (png, jpg, webp) est attendu.")


def mire(region: dict, chemin: Path) -> Path:
    """Une mire NEUTRE a la taille de la case (bornee a 1280) : fond sombre a bandes, cadre, nom de la case."""
    from PIL import Image, ImageDraw, ImageFont
    w0, h0 = max(8, int(region.get("width") or 320)), max(8, int(region.get("height") or 180))
    k = min(1.0, 1280 / max(w0, h0))   # borne PROPORTIONNELLE : borner chaque cote a part deformait la mire, que le
    w, h = max(8, round(w0 * k)), max(8, round(h0 * k))   # cadrage « cover » rognait ensuite (vu sur la preuve)
    im = Image.new("RGB", (w, h), (14, 22, 34))
    d = ImageDraw.Draw(im)
    pas = max(12, min(w, h) // 8)
    for k in range(-h, w, pas * 2):
        d.polygon([(k, 0), (k + pas, 0), (k + pas + h, h), (k + h, h)], fill=(20, 32, 48))
    d.rectangle((0, 0, w - 1, h - 1), outline=(0, 229, 255), width=max(1, min(w, h) // 90))
    nom = str(region.get("slot_label") or region.get("slot_name") or "case")
    marque = "VIDÉO" if region.get("type") == "video_slot" else "IMAGE"
    from app.services.template_service import TemplateEngine
    fonte = str(TemplateEngine().font_path(None))

    def police(taille, texte):          # la plus grande taille (<= taille) dont le texte tient dans 90 % de la largeur
        while True:
            try:
                p = ImageFont.truetype(fonte, taille)
            except OSError:
                return ImageFont.load_default()
            if taille <= 8 or p.getlength(texte) <= w * 0.9:
                return p
            taille = max(8, int(taille * 0.9))
    for texte, pol, dy, coul in ((nom, police(max(10, min(w, h) // 9), nom), -0.08, (226, 232, 240)),
                                 (marque, police(max(8, min(w, h) // 16), marque), 0.12, (0, 229, 255))):
        b = d.textbbox((0, 0), texte, font=pol)
        d.text(((w - (b[2] - b[0])) / 2 - b[0], h * (0.5 + dy) - (b[3] - b[1]) / 2 - b[1]), texte, font=pol, fill=coul)
    im.save(chemin)
    return chemin


def _images_dir() -> Path:
    from app.config import settings
    return Path(settings.images_path)


def echantillon(tpl: dict, slot_name: str) -> Path | None:
    """Le fichier d'echantillon d'une case, s'il est dans la Bibliotheque (jamais hors du dossier des images)."""
    nom = ((tpl.get("metadata") or {}).get("samples") or {}).get(slot_name) if isinstance(tpl.get("metadata"), dict) else None
    if not isinstance(nom, str):
        return None
    p = _images_dir() / Path(nom).name
    return p if p.is_file() and p.suffix.lower() in EXT_IMAGES else None


def preparer(tpl: dict, work: Path) -> tuple:
    """(gabarit a rendre, slot_values) : chaque case image/video remplie par son echantillon ou une mire ; une case
    video remplie d'une IMAGE devient une case image (en boucle)."""
    t = copy.deepcopy(tpl)
    slots = {}
    for r in t.get("regions") or []:
        if r.get("type") not in _CASES or not r.get("slot_name"):
            continue
        p = echantillon(tpl, r["slot_name"]) or mire(r, work / f"mire_{uuid.uuid4().hex[:8]}.png")
        slots[r["slot_name"]] = {"path": p}
        if r["type"] == "video_slot":   # en sequentiel, un acte image sans longueur dure deja 4 s (build_sequential_command)
            r["type"] = "image_slot"
    return t, slots


def rendre(engine, tpl: dict, at_s: float, fmt: str, dossier: Path) -> bytes:
    """Les octets de l'image fixe (png | jpeg | webp). ValueError : format, instant ou gabarit invalides."""
    if fmt not in FORMATS:
        raise ValueError(f"Format inconnu : {fmt} — png, jpeg ou webp.")
    try:
        at = float(at_s)
    except (TypeError, ValueError):
        raise ValueError("L'instant doit être un nombre de secondes.")
    if not 0 <= at <= 3600:
        raise ValueError("L'instant doit être entre 0 et 3600 s.")
    from PIL import Image
    import io
    work = dossier / f"still_{uuid.uuid4().hex[:10]}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        t, slots = preparer(engine.resoudre(tpl), work)
        png = engine.render_still(t.get("id") or "still", slots, work / "image.png", template=t, at_s=at)
        if fmt == "png":
            return png.read_bytes()
        im = Image.open(png).convert("RGB")
        out = io.BytesIO()
        im.save(out, FORMATS[fmt][0], quality=92 if fmt == "jpeg" else 90)
        return out.getvalue()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cle_vignette(engine, tpl: dict) -> str:
    """Le gabarit RESOLU (kit actif compris), ses echantillons (nom, taille, date) et la version du dessin."""
    res = engine.resoudre(tpl)
    ech = {}
    for r in res.get("regions") or []:
        if r.get("type") in _CASES and r.get("slot_name"):
            p = echantillon(res, r["slot_name"])
            ech[r["slot_name"]] = [p.name, p.stat().st_size, int(p.stat().st_mtime)] if p else None
    brut = json.dumps({"t": res, "e": ech, "v": VERSION_VIGNETTE}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:20]


def vignette(engine, tpl: dict, cache: Path, dossier: Path) -> Path:
    """Le fichier WebP de la vignette (360 px au plus grand cote), en cache ; les anciennes du meme gabarit partent."""
    from PIL import Image
    import io
    tid = str(tpl.get("id") or "sans_id")
    cle = cle_vignette(engine, tpl)
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{tid}_{cle}.webp"
    if f.is_file():
        return f
    im = Image.open(io.BytesIO(rendre(engine, tpl, INSTANT_DEFAUT, "png", dossier))).convert("RGB")
    im.thumbnail((VIGNETTE_MAX, VIGNETTE_MAX))
    tmp = f.with_suffix(".tmp")
    im.save(tmp, "WEBP", quality=85)
    tmp.replace(f)
    for vieux in cache.glob(f"{tid}_*.webp"):   # le NOM exact : « tpl_news_* » attrape aussi « tpl_news_reel_<cle> »
        if vieux != f and vieux.stem.rsplit("_", 1)[0] == tid:
            try:
                vieux.unlink(missing_ok=True)
            except OSError:            # encore servie (Windows la verrouille) : elle partira au prochain calcul
                pass
    return f
