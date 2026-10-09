"""Traduction L4 (t144) : les catalogues SERVEUR des écrans Son & VFX et Montage -> backend/app/i18n/messages.json.

  python scripts/i18n_l4_serveur.py          ajoute / met à jour les clés du lot dans messages.json (les autres restent)
  python scripts/i18n_l4_serveur.py --check  code 1 si messages.json n'est pas à jour

Le français de chaque clé est LU dans la table source (effects_engine, montage_service, titles) au moment de la
génération : la table est la référence. L'anglais est écrit ici, une ligne par clé. Une clé dont la source n'a pas de
traduction ici est une erreur (le générateur refuse), comme une traduction dont la clé n'existe plus dans la source.
Lancé avec le python EMBARQUÉ (il importe l'application : pydantic-settings) — voir backend/app/i18n/catalogues.py.
"""
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
MESSAGES = RACINE / "backend" / "app" / "i18n" / "messages.json"
PREFIXES = ("effets.", "transitions.", "livraison.", "titres.gabarit.")

EN = {
    # effets : nom et aide
    "effets.grade.nom": "LUT / Grade",
    "effets.grade.aide": "Color moods, or your own .cube LUT.",
    "effets.grade_basic.nom": "Basic adjustments",
    "effets.grade_basic.aide": "Exposure, contrast, saturation, temperature — under the LUT.",
    "effets.wheels.nom": "Lift / gamma / gain wheels",
    "effets.wheels.aide": "Shadows, midtones, highlights: one setting per channel.",
    "effets.curves.nom": "Curves",
    "effets.curves.aide": "Master and RGB point curves — set in the Grading panel.",
    "effets.huesat.nom": "Hue / saturation by color",
    "effets.huesat.aide": "Hue or saturation of a color range; amount 10 = full desaturation.",
    "effets.lumsat.nom": "Saturation by luminance",
    "effets.lumsat.aide": "Lum vs Sat curve: saturation of shadows, midtones and highlights (100% = unchanged).",
    "effets.satsat.nom": "Saturation by saturation",
    "effets.satsat.aide": "Sat vs Sat curve: dull, medium or vivid colors, each from 0 to 200% (100% = unchanged).",
    "effets.colormatch.nom": "Color match",
    "effets.colormatch.aide": "Matches this clip to the statistics of another one (Grading panel).",
    "effets.monochrome.nom": "Monochrome",
    "effets.monochrome.aide": "Black and white through a color filter.",
    "effets.colorize.nom": "Colorize",
    "effets.colorize.aide": "Sepia, black and white, duotone, matrix.",
    "effets.invert.nom": "Invert",
    "effets.invert.aide": "Inverts every color.",
    "effets.posterize.nom": "Posterize",
    "effets.posterize.aide": "Reduces the number of levels: flat areas, screen-print style.",
    "effets.denoise.nom": "Denoise",
    "effets.denoise.aide": "Reduces video noise: hqdn3d (strong) or atadenoise (gentle).",
    "effets.deflicker.nom": "Deflicker",
    "effets.deflicker.aide": "Smooths brightness changes from one frame to the next.",
    "effets.deband.nom": "Deband",
    "effets.deband.aide": "Softens the visible steps in gradients.",
    "effets.vhs.nom": "VHS",
    "effets.vhs.aide": "Worn tape: shaky lines, chroma bleed, noise.",
    "effets.scanlines.nom": "Scanlines / CRT",
    "effets.scanlines.aide": "Scan lines of a cathode-ray tube.",
    "effets.oldfilm.nom": "Old film",
    "effets.oldfilm.aide": "Faded grade, dust, vignette.",
    "effets.grain.nom": "Film grain",
    "effets.grain.aide": "Animated silver-halide grain.",
    "effets.filmburn.nom": "Film burn",
    "effets.filmburn.aide": "A hot spot eating the film.",
    "effets.dither.nom": "Dither",
    "effets.dither.aide": "Ordered Bayer dither: gradients as dots, print style.",
    "effets.bloom.nom": "Bloom / Glow",
    "effets.bloom.aide": "Highlights spill over.",
    "effets.halation.nom": "Halation",
    "effets.halation.aide": "Red halo around the lights, like on film.",
    "effets.vignette.nom": "Vignette",
    "effets.vignette.aide": "Darkens the edges, draws the eye in.",
    "effets.gradient.nom": "Linear gradient",
    "effets.gradient.aide": "A two-color wash over the whole image.",
    "effets.radial.nom": "Radial gradient",
    "effets.radial.aide": "A colored halo placed wherever you want.",
    "effets.lightleak.nom": "Light leak",
    "effets.lightleak.aide": "Stray light coming in from an edge of the frame.",
    "effets.rain.nom": "Rain",
    "effets.rain.aide": "Procedural shower overlaid on the image.",
    "effets.snow.nom": "Snow",
    "effets.snow.aide": "Procedural snowflakes overlaid on the image.",
    "effets.embers.nom": "Embers",
    "effets.embers.aide": "Rising orange sparks.",
    "effets.chroma.nom": "Chromatic aberration",
    "effets.chroma.aide": "Red/blue offset along a straight line.",
    "effets.glitch.nom": "Glitch",
    "effets.glitch.aide": "Digital breaks, noise and layer offsets.",
    "effets.prism.nom": "Prism",
    "effets.prism.aide": "Radial aberration: the offset grows toward the edges.",
    "effets.ripple.nom": "Ripple",
    "effets.ripple.aide": "Animated sine wave over the whole image.",
    "effets.swirl.nom": "Swirl",
    "effets.swirl.aide": "A rotation that fades from the center to the edges.",
    "effets.lensdistort.nom": "Lens distortion",
    "effets.lensdistort.aide": "Barrel (fisheye), pincushion, or correct: straightens a wide angle (the inverse of barrel).",
    "effets.blur.nom": "Blur",
    "effets.blur.aide": "Gaussian blur.",
    "effets.dirblur.nom": "Directional blur",
    "effets.dirblur.aide": "Motion streak along an angle.",
    "effets.zoomblur.nom": "Radial zoom blur",
    "effets.zoomblur.aide": "Streaks from the center, a propulsion effect.",
    "effets.shake.nom": "Camera shake",
    "effets.shake.aide": "Frame shake.",
    "effets.shakezoom.nom": "Shake + zoom",
    "effets.shakezoom.aide": "Handheld camera: tight reframing, roll and shake.",
    "effets.tmix.nom": "Frame trail",
    "effets.tmix.aide": "Blends successive frames: a trail or temporal smoothing.",
    "effets.letterbox.nom": "Letterbox",
    "effets.letterbox.aide": "Black bars at the chosen aspect ratio.",
    "effets.mirror.nom": "Mirror",
    "effets.mirror.aide": "Left/right symmetry.",
    "effets.kaleido.nom": "Kaleidoscope",
    "effets.kaleido.aide": "4-way symmetry, kaleidoscope pattern.",
    "effets.chromakey.nom": "Chroma key",
    "effets.chromakey.aide": "Makes one color transparent — on an overlaid clip (V2).",
    "effets.pixelate.nom": "Pixelate",
    "effets.pixelate.aide": "Big pixels, censorship or retro-game style.",
    "effets.sharpen.nom": "Sharpen",
    "effets.sharpen.aide": "Boosts detail: unsharp (classic) or cas (adaptive).",
    "effets.dreamy.nom": "Soft / Dreamy",
    "effets.dreamy.aide": "A diffuse veil over the highlights.",
    "effets.glowedge.nom": "Glowing edges",
    "effets.glowedge.aide": "Outlines light up, neon style.",
    "effets.paper.nom": "Paper texture",
    "effets.paper.aide": "Sheet grain, cream tint, darkened corners.",
    # effets : catégories
    "effets.cat.etalonnage": "Grading",
    "effets.cat.correction": "Correction",
    "effets.cat.retro": "Retro",
    "effets.cat.lumiere": "Light",
    "effets.cat.atmosphere": "Atmosphere",
    "effets.cat.distorsion": "Distortion",
    "effets.cat.mouvement": "Motion",
    "effets.cat.cadrage": "Framing",
    "effets.cat.stylisation": "Stylization",
    # effets : libellés des paramètres (clé = slug du libellé français)
    "effets.param.angle": "Angle",
    "effets.param.centre_x": "Center X",
    "effets.param.centre_y": "Center Y",
    "effets.param.contraste": "Contrast",
    "effets.param.couleur_1": "Color 1",
    "effets.param.couleur_2": "Color 2",
    "effets.param.couleur_cle": "Key color",
    "effets.param.couleurs": "Colors",
    "effets.param.couleurs_moyennes": "Medium colors (%)",
    "effets.param.couleurs_ternes": "Dull colors (%)",
    "effets.param.couleurs_vives": "Vivid colors (%)",
    "effets.param.debordement": "Spill",
    "effets.param.decalage_u": "Offset U",
    "effets.param.decalage_v": "Offset V",
    "effets.param.decalage_y": "Offset Y",
    "effets.param.exposition": "Exposure",
    "effets.param.fondu_du_bord": "Edge feather",
    "effets.param.force": "Amount",
    "effets.param.format": "Format",
    "effets.param.fusion": "Blend",
    "effets.param.gain_u": "Gain U",
    "effets.param.gain_v": "Gain V",
    "effets.param.gain_y": "Gain Y",
    "effets.param.gain_bleu": "Blue gain",
    "effets.param.gain_rouge": "Red gain",
    "effets.param.gain_vert": "Green gain",
    "effets.param.gamma_bleu": "Blue gamma",
    "effets.param.gamma_rouge": "Red gamma",
    "effets.param.gamma_vert": "Green gamma",
    "effets.param.hautes_lumieres": "Highlights (%)",
    "effets.param.images": "Frames",
    "effets.param.intensite": "Strength",
    "effets.param.lut_cube": "LUT .cube",
    "effets.param.lift_bleu": "Blue lift",
    "effets.param.lift_rouge": "Red lift",
    "effets.param.lift_vert": "Green lift",
    "effets.param.mode": "Mode",
    "effets.param.ombres": "Shadows (%)",
    "effets.param.opacite": "Opacity",
    "effets.param.prereglage": "Preset",
    "effets.param.saturation": "Saturation",
    "effets.param.similarite": "Similarity",
    "effets.param.teinte": "Hue",
    "effets.param.teinte_bleue": "Blue tint",
    "effets.param.teinte_rouge": "Red tint",
    "effets.param.temperature": "Temperature",
    "effets.param.tons_moyens": "Midtones (%)",
    "effets.param.vitesse": "Speed",
    # transitions : familles
    "transitions.famille.fondus": "fades",
    "transitions.famille.glissements": "slides",
    "transitions.famille.volets": "wipes",
    "transitions.famille.formes": "shapes",
    "transitions.famille.zooms": "zooms",
    "transitions.famille.pixels": "pixels",
    # transitions : libellés (l'id xfade reste la valeur)
    "transitions.fade": "fade",
    "transitions.fadeblack": "fade to black",
    "transitions.fadewhite": "fade to white",
    "transitions.fadegrays": "fade to gray",
    "transitions.fadefast": "fast fade",
    "transitions.fadeslow": "slow fade",
    "transitions.dissolve": "dissolve",
    "transitions.distance": "distance",
    "transitions.slideleft": "slide left",
    "transitions.slideright": "slide right",
    "transitions.slideup": "slide up",
    "transitions.slidedown": "slide down",
    "transitions.coverleft": "cover left",
    "transitions.coverright": "cover right",
    "transitions.coverup": "cover up",
    "transitions.coverdown": "cover down",
    "transitions.revealleft": "reveal left",
    "transitions.revealright": "reveal right",
    "transitions.revealup": "reveal up",
    "transitions.revealdown": "reveal down",
    "transitions.wipeleft": "wipe left",
    "transitions.wiperight": "wipe right",
    "transitions.wipeup": "wipe up",
    "transitions.wipedown": "wipe down",
    "transitions.wipetl": "wipe ↖",
    "transitions.wipetr": "wipe ↗",
    "transitions.wipebl": "wipe ↙",
    "transitions.wipebr": "wipe ↘",
    "transitions.smoothleft": "smooth wipe left",
    "transitions.smoothright": "smooth wipe right",
    "transitions.smoothup": "smooth wipe up",
    "transitions.smoothdown": "smooth wipe down",
    "transitions.diagtl": "diagonal ↖",
    "transitions.diagtr": "diagonal ↗",
    "transitions.diagbl": "diagonal ↙",
    "transitions.diagbr": "diagonal ↘",
    "transitions.circlecrop": "circle (crop)",
    "transitions.rectcrop": "rectangle (crop)",
    "transitions.circleopen": "circle open",
    "transitions.circleclose": "circle close",
    "transitions.vertopen": "vertical curtain open",
    "transitions.vertclose": "vertical curtain close",
    "transitions.horzopen": "horizontal curtain open",
    "transitions.horzclose": "horizontal curtain close",
    "transitions.radial": "radial sweep",
    "transitions.zoomin": "zoom in",
    "transitions.squeezeh": "horizontal squeeze",
    "transitions.squeezev": "vertical squeeze",
    "transitions.pixelize": "pixelize",
    "transitions.hblur": "horizontal blur",
    "transitions.hlslice": "slices → right",
    "transitions.hrslice": "slices → left",
    "transitions.vuslice": "slices ↑",
    "transitions.vdslice": "slices ↓",
    "transitions.hlwind": "wind → right",
    "transitions.hrwind": "wind → left",
    "transitions.vuwind": "wind ↑",
    "transitions.vdwind": "wind ↓",
    # préréglages de livraison
    "livraison.master_1080": "Master 1080 (H.264)",
    "livraison.web_4k": "Web 4K (H.264)",
    "livraison.social_720": "Social 720 (light H.264)",
    "livraison.prores422": "ProRes 422 (editing)",
    "livraison.hevc": "HEVC 1080 (H.265)",
    "livraison.webm_vp9": "WebM VP9",
    "livraison.audio_aac": "Audio only AAC (.m4a)",
    "livraison.audio_mp3": "Audio only MP3",
    "livraison.audio_wav": "Audio only WAV",
    "livraison.gif_480": "Animated GIF 480",
    # gabarits de titre
    "titres.gabarit.plein_cadre": "full frame",
    "titres.gabarit.tiers_inferieur": "lower third",
    "titres.gabarit.legende": "caption",
    "titres.gabarit.compteur": "counter",
    "titres.gabarit.chapitre": "chapter",
    "titres.gabarit.citation": "quote",
    "titres.gabarit.hashtag": "hashtag",
    "titres.gabarit.cta": "call to action",
}


def sources() -> dict:
    """clé -> texte français, lu dans les tables du serveur."""
    from app.i18n.catalogues import slug
    from app.services import effects_engine as fx, montage_service as M, titles as TI
    fr = {}
    for typ, spec in fx.catalog().items():
        if typ == "lut":
            continue                                   # alias de grade
        fr[f"effets.{typ}.nom"] = spec["label"]
        fr[f"effets.{typ}.aide"] = spec["hint"]
        for b in spec["bounds"].values():
            if b.get("label"):
                fr["effets.param." + slug(b["label"])] = b["label"]
    for cid, lab in fx.CATEGORIES:
        fr[f"effets.cat.{cid}"] = lab
    for f in M.transitions_catalog()["familles"]:
        fr[f"transitions.famille.{f['id']}"] = f["label"]
        for it in f["items"]:
            fr[f"transitions.{it['id']}"] = it["label"]
    for k, v in M._DELIVER.items():
        fr[f"livraison.{k}"] = v["label"]
    for k in TI.TEMPLATES:
        fr[f"titres.gabarit.{k}"] = TI.LABELS.get(k, k)
    return fr


def attendu() -> bytes:
    fr = sources()
    manque, orphelines = sorted(set(fr) - set(EN)), sorted(set(EN) - set(fr))
    if manque or orphelines:
        raise SystemExit(f"traductions manquantes {manque[:10]} / sans source {orphelines[:10]}")
    actuel = json.loads(MESSAGES.read_text("utf-8"))
    neuf = {k: v for k, v in actuel.items() if not k.startswith(PREFIXES)}
    for k in sorted(fr):
        neuf[k] = {"fr": fr[k], "en": EN[k]}
    return ("{\n" + ",\n".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                                for k, v in neuf.items()) + "\n}\n").encode("utf-8")


def main(args):
    b = attendu()
    if "--check" in args:
        ok = MESSAGES.read_bytes().replace(b"\r\n", b"\n") == b
        print("à jour" if ok else "PÉRIMÉ : python scripts/i18n_l4_serveur.py (python embarqué)")
        return 0 if ok else 1
    MESSAGES.write_bytes(b)
    print(f"{MESSAGES.relative_to(RACINE)} : {len(json.loads(b))} clés")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
