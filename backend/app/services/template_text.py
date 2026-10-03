# -*- coding: utf-8 -*-
"""Plan-templates T4 (tache #74 du suivi, PR C, 03/10/2026) — TEXTE ADAPTATIF et EFFETS pour les textes, sous-titres,
badges et tickers des gabarits.

Champs d'une region (tous facultatifs) :
    "text_fit": true | false            couper en lignes (mots entiers) PUIS reduire jusqu'a tenir dans la case, sans
                                        descendre sous "text_min_size" (12 par defaut) ; « … » en dernier recours.
                                        (le ticker defile : il n'est jamais ajuste)
    "text_effects": {"stroke": {"px", "color"}, "shadow": {"dx", "dy", "blur", "color", "opacity"},
                     "box": {"color", "opacity", "radius", "pad"}, "gradient": {"c0", "c1", "direction"}}
Decisions de l'utilisateur (03/10) : couper en lignes puis reduire, taille mini reglable ; contour reglable, ombre nette
ou floue, fond (coins arrondis), degrade ; textes + sous-titres + badge + ticker ; SANS reglage, rendu IDENTIQUE au pixel
(template_service n'appelle ce module que si la region porte text_fit ou text_effects).
Rendu : drawtext NATIF tant que possible (lignes calculees ici avec la vraie fonte ; contour = borderw ; ombre nette =
shadowx/y ; fond carre = box) — il garde la pulsation et le contour par defaut ; une IMAGE (Pillow) seulement pour
l'ombre floue, le degrade et le fond arrondi.
"""
from __future__ import annotations

import re
from pathlib import Path

TYPES = ("text", "text_slot", "badge", "ticker")
MIN_DEFAUT = 12
INTERLIGNE = 1.2
ELLIPSE = "…"
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _n(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def actif(r: dict) -> bool:
    return bool(r.get("text_fit")) or bool(r.get("text_effects"))


def verifier_textes(regions) -> None:
    """ValueError qui nomme la region et le champ (appele par TemplateEngine._validate)."""
    for r in regions or []:
        if "text_fit" not in r and "text_effects" not in r and "text_min_size" not in r:
            continue
        rid = r.get("id")
        if r.get("type") not in TYPES:
            raise ValueError(f"Region {rid} : l'ajustement et les effets de texte valent pour {', '.join(TYPES)}.")
        if "text_fit" in r and not isinstance(r["text_fit"], bool):
            raise ValueError(f"Region {rid} : text_fit est vrai ou faux.")
        if "text_min_size" in r and not (_n(r["text_min_size"]) and 6 <= r["text_min_size"] <= 400):
            raise ValueError(f"Region {rid} : text_min_size doit être entre 6 et 400.")
        e = r.get("text_effects")
        if e is None:
            continue
        if not isinstance(e, dict) or set(e) - {"stroke", "shadow", "box", "gradient"}:
            raise ValueError(f"Region {rid} : text_effects accepte stroke, shadow, box, gradient.")
        bornes = {"stroke": {"px": (0, 40)}, "shadow": {"dx": (-200, 200), "dy": (-200, 200), "blur": (0, 60), "opacity": (0, 1)},
                  "box": {"opacity": (0, 1), "radius": (0, 400), "pad": (0, 200)}, "gradient": {}}
        couleurs = {"stroke": ("color",), "shadow": ("color",), "box": ("color",), "gradient": ("c0", "c1")}
        for nom, sous in e.items():
            if not isinstance(sous, dict):
                raise ValueError(f"Region {rid} : text_effects.{nom} doit être un objet.")
            for ch, (lo, hi) in bornes[nom].items():
                if ch in sous and not (_n(sous[ch]) and lo <= sous[ch] <= hi):
                    raise ValueError(f"Region {rid} : text_effects.{nom}.{ch} doit être entre {lo} et {hi}.")
            for ch in couleurs[nom]:
                if ch in sous and not (isinstance(sous[ch], str) and _COULEUR.match(sous[ch])):
                    raise ValueError(f"Region {rid} : text_effects.{nom}.{ch} doit être #RRGGBB.")
            if nom == "gradient" and sous.get("direction", "vertical") not in ("vertical", "horizontal"):
                raise ValueError(f"Region {rid} : text_effects.gradient.direction est vertical ou horizontal.")


def _police(chemin, taille):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(str(chemin), int(taille)) if chemin else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def hauteur_ligne(police) -> int:
    a, d = police.getmetrics()
    return int(round((a + d) * INTERLIGNE))


def couper(texte: str, police, largeur: float) -> list:
    """Lignes de mots entiers qui tiennent dans `largeur` (mesure reelle) ; les sauts de ligne de l'auteur sont
    gardes ; un mot plus large qu'une ligne est coupe a la lettre."""
    out = []
    for para in str(texte).split("\n"):
        mots, cour = para.split(" "), ""
        for m in mots:
            essai = (cour + " " + m) if cour else m
            if police.getlength(essai) <= largeur:
                cour = essai
                continue
            if cour:
                out.append(cour)
            cour = ""
            while m and police.getlength(m) > largeur:      # mot trop long : coupe a la lettre
                k = len(m)
                while k > 1 and police.getlength(m[:k]) > largeur:
                    k -= 1
                out.append(m[:k])
                m = m[k:]
            cour = m
        out.append(cour)
    return out


def ajuster(texte: str, chemin_police, taille: int, largeur: int, hauteur: int, taille_min: int = MIN_DEFAUT) -> tuple:
    """(taille, lignes, tronque) : couper en lignes, puis REDUIRE jusqu'a tenir en largeur ET en hauteur ; a la taille
    minimale, les lignes en trop sont retirees et la derniere finit par « … »."""
    taille_min = max(6, min(int(taille_min), int(taille)))
    t = int(taille)
    while True:
        pol = _police(chemin_police, t)
        lignes = couper(texte, pol, largeur)
        if len(lignes) * hauteur_ligne(pol) <= hauteur and all(pol.getlength(l) <= largeur for l in lignes):
            return t, lignes, False
        if t <= taille_min:
            break
        t = max(taille_min, int(t * 0.92) if t > 20 else t - 1)
    pol = _police(chemin_police, t)
    garde = max(1, int(hauteur // max(1, hauteur_ligne(pol))))
    lignes = couper(texte, pol, largeur)
    tronque = len(lignes) > garde
    lignes = lignes[:garde]
    if tronque:
        der = lignes[-1].rstrip()
        while der and pol.getlength(der + ELLIPSE) > largeur:
            der = der[:-1].rstrip()
        lignes[-1] = der + ELLIPSE
    return t, lignes, tronque


def effets(r: dict) -> dict:
    return r.get("text_effects") or {}


def besoin_image(e: dict) -> bool:
    """L'ombre floue, le degrade et le fond arrondi passent par une image ; le reste reste en drawtext natif."""
    sh, bx = e.get("shadow") or {}, e.get("box") or {}
    # « gradient » PRESENT suffit (un {} vide veut les couleurs par defaut — un test de verite le ratait, trouve par le banc)
    return e.get("gradient") is not None or float(sh.get("blur", 0) or 0) > 0 or float(bx.get("radius", 0) or 0) > 0


def _hx(c, defaut):
    return (c or defaut).lstrip("#").lower()


def drawtext_options(e: dict) -> str:
    """Les options drawtext NATIVES : contour (remplace le contour par defaut de 3 px), ombre nette, fond carre."""
    o = []
    st = e.get("stroke")
    if st is not None:
        o.append(f"borderw={int(round(st.get('px', 0)))}:bordercolor=0x{_hx(st.get('color'), '#02060d')}")
    sh = e.get("shadow")
    if sh:   # une ombre FLOUE n'arrive jamais ici : besoin_image() l'envoie a l'image
        o.append(f"shadowx={int(round(sh.get('dx', 4)))}:shadowy={int(round(sh.get('dy', 4)))}:"
                 f"shadowcolor=0x{_hx(sh.get('color'), '#000000')}@{float(sh.get('opacity', 0.6)):.2f}")
    bx = e.get("box")
    if bx and not float(bx.get("radius", 0) or 0) > 0:
        o.append(f"box=1:boxcolor=0x{_hx(bx.get('color'), '#000000')}@{float(bx.get('opacity', 0.6)):.2f}:"
                 f"boxborderw={int(round(bx.get('pad', 12)))}")
    return ":".join(o)


def rendre_png(lignes: list, chemin_police, taille: int, couleur: str, e: dict, w: int, h: int,
               aligne: str, vertical: str, chemin: Path) -> tuple:
    """Le bloc de texte en image RGBA (w x h) avec ses effets : fond arrondi, ombre (floue), contour, degrade.
    `aligne` left|center, `vertical` top|middle. Rend (chemin, largeur et hauteur du bloc dessine)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageColor
    pol = _police(chemin_police, taille)
    lh = hauteur_ligne(pol)
    larg = [pol.getlength(l) for l in lignes] or [0]
    bw, bh = int(max(larg)), lh * len(lignes)
    # l'ENCRE du bloc (du haut des lettres de la 1re ligne au bas de la derniere) : c'est elle qu'on centre et que le
    # fond entoure — centrer la boite de ligne laissait le texte haut dans son fond (vu a l'ecran sur un badge)
    hb = [pol.getbbox(l) for l in (lignes[0], lignes[-1])] if lignes and any(lignes) else [(0, 0, 0, lh), (0, 0, 0, lh)]
    e_haut, e_bas = hb[0][1], (len(lignes) - 1) * lh + hb[1][3]
    x0 = (w - bw) // 2 if aligne == "center" else 0
    y0 = (h - (e_bas - e_haut)) // 2 - e_haut if vertical == "middle" else 0
    st = e.get("stroke") or {}
    sw = int(round(st.get("px", 3))) if e.get("stroke") is not None else 3
    scol = ImageColor.getrgb(st.get("color") or "#02060d") + ((255,) if e.get("stroke") is not None else (166,))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bx = e.get("box")
    if bx:
        pad = int(round(bx.get("pad", 12)))
        c = ImageColor.getrgb(bx.get("color") or "#000000") + (int(255 * float(bx.get("opacity", 0.6))),)
        ImageDraw.Draw(im).rounded_rectangle((x0 - pad, y0 + e_haut - pad, x0 + bw + pad, y0 + e_bas + pad), radius=int(bx.get("radius", 0)), fill=c)

    def masque_texte(dx=0, dy=0, contour=0):
        m = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(m)
        for i, l in enumerate(lignes):
            lx = x0 + ((bw - larg[i]) // 2 if aligne == "center" else 0)
            d.text((lx + dx, y0 + i * lh + dy), l, font=pol, fill=255, stroke_width=contour, stroke_fill=255)
        return m

    sh = e.get("shadow")
    if sh:
        ms = masque_texte(int(round(sh.get("dx", 4))), int(round(sh.get("dy", 4))), sw)
        if float(sh.get("blur", 0) or 0) > 0:
            ms = ms.filter(ImageFilter.GaussianBlur(float(sh["blur"]) / 2))
        couche = Image.new("RGBA", (w, h), ImageColor.getrgb(sh.get("color") or "#000000") + (0,))
        couche.putalpha(ms.point(lambda v: int(v * float(sh.get("opacity", 0.6)))))
        im = Image.alpha_composite(im, couche)
    if sw > 0:
        mc = masque_texte(contour=sw)
        couche = Image.new("RGBA", (w, h), scol[:3] + (0,))
        couche.putalpha(mc.point(lambda v: int(v * scol[3] / 255)))
        im = Image.alpha_composite(im, couche)
    mt = masque_texte()
    g = e.get("gradient")
    if g:
        c0, c1 = ImageColor.getrgb(g.get("c0", "#ffffff")), ImageColor.getrgb(g.get("c1", "#00e5ff"))
        vert = g.get("direction", "vertical") == "vertical"
        L = max(1, (e_bas - e_haut) if vert else bw)   # vertical : de l'encre du haut a celle du bas
        ya = y0 + e_haut
        bande = Image.new("RGB", (1, L) if vert else (L, 1))       # une BANDE de L pixels, etiree : pas de boucle sur l'image
        for i in range(L):
            k = i / max(1, L - 1)
            bande.putpixel((0, i) if vert else (i, 0), tuple(int(a + (b - a) * k) for a, b in zip(c0, c1)))
        grad = Image.new("RGB", (w, h), c0)
        if vert:
            grad.paste(c1, (0, min(h, ya + L), w, h)) if ya + L < h else None
            grad.paste(bande.resize((w, L)), (0, ya))
        else:
            grad.paste(c1, (min(w, x0 + L), 0, w, h)) if x0 + L < w else None
            grad.paste(bande.resize((L, h)), (x0, 0))
        grad = grad.convert("RGBA")
        grad.putalpha(mt)
        im = Image.alpha_composite(im, grad)
    else:
        couche = Image.new("RGBA", (w, h), ImageColor.getrgb("#" + couleur.lstrip("#")) + (0,))
        couche.putalpha(mt)
        im = Image.alpha_composite(im, couche)
    im.save(chemin)
    return chemin, bw, bh


def apercu(engine, region: dict, fond, dossier: Path) -> bytes:
    """Tache #74 PR D — « Aperçu exact » de l'editeur : la case SEULE, rendue par le VRAI moteur (meme ffmpeg, meme
    ajustement, memes effets, meme encodage que le rendu final), dans une toile a sa taille ; PNG d'une image. Gratuit
    (rien de paye) ; image fixe : la pulsation est retiree, le ticker est saisi quand son texte est entre dans la case.
    ValueError (case illisible, type hors texte, reglage invalide) -> 400 cote route."""
    import copy
    import uuid
    from app.services.composition_service import _run_ffmpeg
    if not isinstance(region, dict) or region.get("type") not in TYPES:
        raise ValueError(f"L'aperçu exact vaut pour {', '.join(TYPES)}.")
    try:
        w, h = int(region["width"]), int(region["height"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Case illisible (width / height).")
    if not (8 <= w <= 4096 and 8 <= h <= 4096):
        raise ValueError("La case doit mesurer entre 8 et 4096 px.")
    r = copy.deepcopy(region)
    r.update(x=0, y=0, id=str(r.get("id") or "apercu"))
    r.pop("effect", None)
    t = 0.0
    if r["type"] == "ticker":            # le texte entre par la droite : a la moitie de la case
        t = round(min(5.0, w * 0.5 / max(1.0, float(r.get("speed", 120) or 120))), 2)
    fond = fond if isinstance(fond, str) and _COULEUR.match(fond) else "#101010"
    tpl = {"id": "apercu_texte", "name": "Aperçu", "regions": [r],
           "canvas": {"width": w + w % 2, "height": h + h % 2, "fps": 10, "duration_s": round(t + 0.3, 2), "background_color": fond}}
    nom = f"apercu_texte_{uuid.uuid4().hex[:10]}"
    mp4, png = dossier / f"{nom}.mp4", dossier / f"{nom}.png"
    try:
        engine.render(nom, {}, mp4, template=tpl)
        _run_ffmpeg(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1",
                     "-vf", f"format=rgb24,crop={w}:{h}:0:0", str(png)], png)   # en RGB : sur du yuv420p, crop arrondit une taille impaire (trouve par le banc)
        return png.read_bytes()
    finally:
        for p in (mp4, png):
            p.unlink(missing_ok=True)
