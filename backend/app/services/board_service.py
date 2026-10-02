"""v1.20.2 (Atelier) — planches de référence COMPOSITES.

Leçon des rounds de test: les modèles de diffusion sont peu fiables sur les
mises en page multi-panneaux (vues manquantes, chevauchements, flou,
identité qui dérive). Méthode studio à la place:
1. chaque vue/panneau est générée SÉPARÉMENT (une figure ou un cadre par
   image — ce que la diffusion fait le mieux, net et bien proportionné);
2. l'identité entre panneaux est garantie par chaînage Kontext sur le
   premier panneau (ou sur l'image d'inspiration de l'utilisateur);
3. la planche finale est assemblée PAR CODE (PIL): layout 100% garanti,
   rangées propres, gouttières régulières, bande de palette pour les
   ambiances. Chaque panneau garde son seed → recette entièrement rejouable.
"""
from pathlib import Path
from uuid import uuid4

from PIL import Image
from loguru import logger

_GUTTER = 28
_BG = (242, 239, 233)   # fond papier clair, façon model sheet
_SHARP = (", sharp focus, crisp details, high detail, flat light studio "
          "background, absolutely no text, no titles, no lettering")

# Plans de panneaux par kind: (clé, prompt, chaîné_sur (None = panneau
# maître, sinon clé du panneau de référence), taille du panneau maître).
# Le sujet+description+style sont injectés par l'appelant sur le maître;
# les panneaux chaînés reçoivent un rappel court + le style.
#
# Personnage v5 (retour terrain): le HEADSHOT d'abord — un gros plan porte
# un signal d'identité bien plus fort pour le chaînage Kontext qu'une
# silhouette plein pied. Ordre: visage face (maître) → visages profils →
# corps face (chaîné sur le visage) → corps profils/dos (chaînés sur le
# corps face pour la constance de la tenue). Composition en COLONNES
# ALIGNÉES: chaque visage au-dessus de son corps correspondant.
PANEL_PLANS: dict[str, dict] = {
    # v6: les profils DROITS sont dérivés par MIROIR logiciel du profil
    # gauche (la diffusion confond gauche/droite — le miroir garantit une
    # direction opposée au pixel près, et économise 2 générations).
    #
    # v7 (leçon tests A/B canons): les panneaux CORPS portent la taille
    # sentinelle "CANON" → l'appelant impose le cadre vertical du canon de
    # proportions (resolution_mode Kontext / aspect_ratio Banana / size
    # OpenAI). Sans cela le modèle edit sort dans le cadre 3:4 du headshot
    # de référence → corps tassé (~5 têtes) ou coupé aux genoux. Les
    # prompts corps DOIVENT: (1) commander un "zoom far out" (Kontext obéit
    # aux instructions de recadrage), (2) exiger marge au-dessus de la tête
    # ET sous les pieds, (3) placer {PROPORTIONS} — canon du style — après.
    "character": {
        "panels": [
            # {FACE} = traits du visage selon le canon du style (yeux manga,
            # yeux-points ligne claire, gros nez…) — le maître fixe le style.
            ("face_front", "head-and-shoulders close-up portrait, front view, "
                           "looking at the camera, centered, {FACE}" + _SHARP,
             None, "portrait_4_3"),
            ("face_left", "the exact same person, same face, same hairstyle: "
                          "head-and-shoulders close-up portrait, LEFT PROFILE "
                          "view, nose pointing to the left of the frame"
                          + _SHARP, "face_front", None),
            # {PROPORTIONS} = canon de proportions du style (DA) injecté par
            # l'appelant — De Vinci, manga, ligne claire, gros-nez, comics…
            ("front", "zoom far out to reveal the FULL BODY of the exact "
                      "same person, same face and hairstyle: standing "
                      "neutral pose seen from a distance, front view facing "
                      "the camera, arms relaxed at the sides, the ENTIRE "
                      "figure from the top of the hair to the soles of the "
                      "feet inside the frame with empty margin above the "
                      "head and below the feet, {PROPORTIONS}" + _SHARP,
             "face_front", "CANON"),
            ("left", "the exact same character, identical outfit, hairstyle "
                     "and colors: full body LEFT PROFILE view, nose pointing "
                     "to the left of the frame, standing neutral pose, the "
                     "entire figure head to feet inside the frame with "
                     "margin above the head and below the feet, same body "
                     "proportions as the reference" + _SHARP,
             "front", "CANON"),
            ("back", "the exact same character, identical outfit, hairstyle "
                     "and colors: full body BACK view (seen from behind), "
                     "standing neutral pose, the entire figure head to feet "
                     "inside the frame with margin above the head and below "
                     "the feet, same body proportions as the reference"
                     + _SHARP, "front", "CANON"),
        ],
        "mirrors": {"face_right": "face_left", "right": "left"},
        "compose": "character",   # colonnes alignées visage↑corps
        "palette": False,
    },
    "place": {
        "panels": [
            ("wide", "wide establishing shot of the location, no characters"
                     + _SHARP, None, "landscape_16_9"),
            ("angle", "the exact same location, same architecture, palette "
                      "and light: REVERSE ANGLE seen from the opposite end, "
                      "clearly different viewpoint, no characters" + _SHARP,
             "wide", None),
            ("detail", "the exact same location: close-up on one key "
                       "characteristic detail" + _SHARP, "wide", None),
        ],
        "rows": [["wide", "angle", "detail"]],
        "row_heights": [400],
        "palette": False,
    },
    "object": {
        "panels": [
            ("front", "product-style reference of the object, front view, "
                      "centered, plain background" + _SHARP, None, "square_hd"),
            ("three_quarter", "the exact same object, identical design: "
                              "three-quarter view" + _SHARP, "front", None),
            ("back", "the exact same object, identical design: back view"
                     + _SHARP, "front", None),
            ("detail", "the exact same object: macro close-up on a "
                       "characteristic detail" + _SHARP, "front", None),
        ],
        "rows": [["front", "three_quarter", "back", "detail"]],
        "row_heights": [360],
        "palette": False,
    },
    "ambiance": {
        "panels": [
            ("f1", "atmosphere keyframe: the light, weather and emotional "
                   "tone of the mood" + _SHARP, None, "landscape_16_9"),
            ("f2", "the exact same atmosphere, light and palette: a clearly "
                   "different framing from another viewpoint" + _SHARP,
             "f1", None),
            ("f3", "the exact same atmosphere, light and palette: a third "
                   "framing, much closer, intimate" + _SHARP, "f1", None),
        ],
        "rows": [["f1", "f2", "f3"]],
        "row_heights": [380],
        "palette": True,   # bande de palette calculée par code
    },
    "date": {
        "panels": [
            ("f1", "evocative era/period reference frame: architecture and "
                   "street life of the time" + _SHARP, None, "landscape_16_9"),
            ("f2", "the exact same era and palette: costumes and people"
                   + _SHARP, "f1", None),
            ("f3", "the exact same era and palette: technology and objects "
                   "of the time" + _SHARP, "f1", None),
        ],
        "rows": [["f1", "f2", "f3"]],
        "row_heights": [380],
        "palette": False,
    },
    # Décor v5 (retour terrain): des ANGLES réellement différents — la
    # variation vient de points de vue explicites, pas d'un vague "second
    # framing" qui produisait trois images quasi identiques.
    "decor": {
        "panels": [
            ("v1", "set-dressing reference: overall view of the set "
                   "elements, furniture and materials, eye-level" + _SHARP,
             None, "landscape_16_9"),
            ("v2", "the exact same set, palette and materials: REVERSE "
                   "ANGLE seen from the opposite side of the room, clearly "
                   "different viewpoint" + _SHARP, "v1", None),
            ("v3", "the exact same set: LOW ANGLE view from about 45 "
                   "degrees to the side, dramatic perspective" + _SHARP,
             "v1", None),
            ("v4", "the exact same set: macro close-up on the most "
                   "characteristic texture or material" + _SHARP, "v1", None),
        ],
        "rows": [["v1", "v2", "v3", "v4"]],
        "row_heights": [360],
        "palette": False,
    },
}


def _load(images_path: Path, fname: str) -> Image.Image:
    return Image.open(images_path / fname).convert("RGB")


def _palette_colors(images_path: Path, fnames: list[str], n: int = 8):
    ims = [_load(images_path, f).resize((64, 64)) for f in fnames]
    strip = Image.new("RGB", (64 * len(ims), 64))
    for i, im in enumerate(ims):
        strip.paste(im, (64 * i, 0))
    q = strip.quantize(colors=n)
    pal = q.getpalette()[:n * 3]
    # tâche #62 : moins de `n` couleurs distinctes -> palette plus courte ; un triplet tronqué faisait planter la planche
    return [tuple(pal[i * 3:i * 3 + 3]) for i in range(len(pal) // 3)]


def mirror_panel(images_path: Path, fname: str) -> str:
    """Profil droit = miroir logiciel du profil gauche: direction opposée
    garantie au pixel près (la diffusion confond gauche/droite)."""
    from PIL import ImageOps
    out = ImageOps.mirror(_load(images_path, fname))
    nf = f"gen_{uuid4().hex[:8]}.png"
    out.save(images_path / nf)
    return nf


def compose_character_board(images_path: Path, panels: dict[str, str],
                            face_h: int = 300, body_h: int = 560) -> str:
    """Planche personnage en COLONNES ALIGNÉES: 4 colonnes (front, left,
    right, back); le headshot correspondant est posé au-dessus de chaque
    corps (pas de visage pour la colonne dos). Layout garanti par code."""
    order = ["front", "left", "right", "back"]
    face_of = {"front": "face_front", "left": "face_left",
               "right": "face_right", "back": None}
    bodies, faces = {}, {}
    for k in order:
        im = _load(images_path, panels[k])
        w = max(1, round(im.width * body_h / im.height))
        bodies[k] = im.resize((w, body_h), Image.LANCZOS)
        fk = face_of[k]
        if fk and fk in panels:
            fim = _load(images_path, panels[fk])
            fw = max(1, round(fim.width * face_h / fim.height))
            faces[k] = fim.resize((fw, face_h), Image.LANCZOS)
    col_w = {k: max(bodies[k].width, faces[k].width if k in faces else 0)
             for k in order}
    W = _GUTTER + sum(col_w.values()) + _GUTTER * (len(order) - 1) + _GUTTER
    H = _GUTTER + face_h + _GUTTER + body_h + _GUTTER
    board = Image.new("RGB", (W, H), _BG)
    x = _GUTTER
    for k in order:
        if k in faces:
            fx = x + (col_w[k] - faces[k].width) // 2
            board.paste(faces[k], (fx, _GUTTER))
        bx = x + (col_w[k] - bodies[k].width) // 2
        board.paste(bodies[k], (bx, _GUTTER + face_h + _GUTTER))
        x += col_w[k] + _GUTTER
    fname = f"board_{uuid4().hex[:8]}.png"
    board.save(images_path / fname)
    logger.info(f"board personnage composé: {fname} ({W}x{H}, colonnes alignées)")
    return fname


def _bandes(kind: str) -> list[tuple[int, list[str]]] | None:
    """Les bandes d'une planche composée par CE code : [(hauteur, clés de la bande, dans l'ordre)]."""
    plan = PANEL_PLANS.get(kind)
    if not plan:
        return None
    if plan.get("compose") == "character":
        return [(300, ["face_front", "face_left", "face_right"]), (560, ["front", "left", "right", "back"])]
    return list(zip(plan.get("row_heights") or [], plan.get("rows") or []))


def decouper_planche(images_path: Path, board: str, kind: str) -> dict[str, str] | None:
    """Tâche #62 (décision de l'utilisateur, 02/10) — les VUES d'une planche composée, retrouvées sans régénérer. La
    planche est posée par `compose_character_board` / `compose_board` : bandes de hauteur connue, séparées et bordées
    de gouttières, fond uni `_BG`, PNG sans perte. Dans chaque bande, les panneaux sont les colonnes qui ne sont pas
    du fond. La géométrie est VÉRIFIÉE (hauteur totale, nombre de panneaux par bande) : une planche qui ne colle pas
    rend None — jamais de vues fausses. Les vues sont écrites une fois (`<planche>_<clé>.png`) puis réutilisées."""
    from PIL import ImageChops
    bandes = _bandes(kind)
    src = images_path / Path(str(board)).name
    if not bandes or not src.is_file():
        return None
    try:
        im = Image.open(src).convert("RGB")
    except Exception:  # noqa: BLE001 — une image illisible n'a pas de vues
        return None
    plan = PANEL_PLANS.get(kind) or {}
    attendu = sum(h for h, _ in bandes) + _GUTTER * (len(bandes) + 1)
    if plan.get("palette"):
        attendu += 46 + _GUTTER
    if im.height != attendu:
        return None
    vues: dict[str, str] = {}
    y = _GUTTER
    for h, cles in bandes:
        bande = im.crop((0, y, im.width, y + h))
        diff = ImageChops.difference(bande, Image.new("RGB", bande.size, _BG)).convert("L")
        xs = diff.point(lambda v: 255 if v else 0).getprojection()[0]
        runs, debut = [], None
        for x, plein in enumerate(list(xs) + [0]):
            if plein and debut is None:
                debut = x
            elif not plein and debut is not None:
                if x - debut >= 4:
                    runs.append((debut, x))
                debut = None
        if len(runs) != len(cles):
            return None
        for (x0, x1), cle in zip(runs, cles):
            nom = f"{src.stem}_{cle}.png"
            if not (images_path / nom).is_file():       # chaque panneau est collé à la hauteur exacte de sa bande
                bande.crop((x0, 0, x1, h)).save(images_path / nom)
            vues[cle] = nom
        y += h + _GUTTER
    return vues


def compose_board(images_path: Path, rows: list[list[str]],
                  row_heights: list[int],
                  palette_from: list[str] | None = None) -> str:
    """Assemble les panneaux en une planche (layout garanti par code).
    Retourne le filename du board écrit dans la Library."""
    prepared: list[list[Image.Image]] = []
    for r, fnames in enumerate(rows):
        ims = []
        for f in fnames:
            im = _load(images_path, f)
            h = row_heights[r]
            w = max(1, round(im.width * h / im.height))
            ims.append(im.resize((w, h), Image.LANCZOS))
        prepared.append(ims)
    widths = [sum(im.width for im in row) + _GUTTER * (len(row) + 1)
              for row in prepared]
    W = max(widths)
    pal_h = 46 if palette_from else 0
    H = (sum(row_heights) + _GUTTER * (len(prepared) + 1)
         + (pal_h + _GUTTER if palette_from else 0))
    board = Image.new("RGB", (W, H), _BG)
    y = _GUTTER
    for r, row in enumerate(prepared):
        row_w = sum(im.width for im in row) + _GUTTER * (len(row) - 1)
        x = max(_GUTTER, (W - row_w) // 2)
        for im in row:
            board.paste(im, (x, y))
            x += im.width + _GUTTER
        y += row_heights[r] + _GUTTER
    if palette_from:
        colors = _palette_colors(images_path, palette_from)
        sw = (W - 2 * _GUTTER) // max(1, len(colors))
        for i, c in enumerate(colors):
            board.paste(Image.new("RGB", (max(1, sw - 6), pal_h), c),
                        (_GUTTER + i * sw, y))
    fname = f"board_{uuid4().hex[:8]}.png"
    board.save(images_path / fname)
    logger.info(f"board composé: {fname} ({W}x{H}, {sum(len(r) for r in rows)} panneaux)")
    return fname
