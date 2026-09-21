# -*- coding: utf-8 -*-
"""D-21 (21/09/2026) — CLIPS TITRE : huit gabarits animes dans la charte, rendus
en ASS par le MEME moteur que les sous-titres (libass, fontes embarquees).

POURQUOI DE L'ASS ET PAS DU « FUSION » : la gravure des sous-titres existe
deja, elle est eprouvee (fontsdir embarque, echappement des chemins Windows,
dernier maillon video de la commande ffmpeg) et elle ne coute AUCUNE
dependance neuve. Un titre n'est rien d'autre qu'un evenement ASS avec ses
tags d'animation (`\\fad`, `\\move`, `\\t`). En contrepartie on renonce a tout
ce que l'ASS ne sait pas faire : pas de style par caractere, pas de 3D, pas de
degrade — c'est de l'ASS, pas du Fusion, et le catalogue de gabarits est
volontairement ferme (huit) plutot qu'un editeur libre.

MODELE DE CLIP : un clip titre est
`{tr:"t1", kind:"title", start, end, title:{template, text, sub?, color?,
font?, size?}}` — **SANS `src`** : `_resolve_src` ne le voit jamais,
`POST /save` et `GET /project` le gardent tel quel (mesure du 21/09/2026).

Tout ce qui touche a l'ASS est repris de `subtitle_service` et n'est PAS
recopie : `_ass_color` (mesure du 21/09/2026 : rend bien `&HAABBGGRR`,
`_ass_color("#e6b23c") == "&H003CB2E6"` — aucun `_bgr` local n'est ecrit),
`_ass_time`, `_ass_escape`, `_ASS_FORMAT_STYLE`, `_ASS_FORMAT_EVENT`,
`REF_HEIGHT`, `FONT_FILES` et `subtitles_filter`. Les seize familles de
`FONT_FILES` ont ete re-verifiees a `PIL.ImageFont.truetype(...).getname()`
le 21/09/2026 : les huit familles citees ci-dessous en sont bien des cles.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

from app.config import settings
from app.services import subtitle_service as S

#: La charte. Les noms sont ceux du client ; seules ces cinq couleurs sont
#: acceptees (un `color` hors charte retombe sur celle du gabarit).
BRAND = {"or": "#e6b23c", "cyan": "#00e5ff", "encre": "#14181d",
         "blanc": "#eef2f6", "rouge": "#e5484d"}

#: gabarit -> police (nom de FAMILLE de FONT_FILES), taille a 1080 p, couleur
#: de la charte, couleur de boite (ou None), ancrage \an, y relatif,
#: entree/sortie en ms, tags d'animation.
#:
#: `anim` est formate avec {in}, {in2}, {y}, {x0}, {x1}. Un gabarit dont
#: l'animation contient un \move n'ecrit PAS de \pos : en ASS les deux tags
#: se disputent le meme champ de position et le dernier gagnerait en silence.
TEMPLATES = {
    "plein_cadre":     {"font": "Anton",          "size": 120, "color": "or",    "box": None,
                        "an": 5, "y": .50, "in": 300, "out": 300,
                        "anim": "\\fscx80\\fscy80\\t(0,{in},\\fscx100\\fscy100)"},
    "tiers_inferieur": {"font": "Bebas Neue",     "size": 64,  "color": "blanc", "box": "or",
                        "an": 1, "y": .80, "in": 260, "out": 200,
                        "anim": "\\move({x0},{y},{x1},{y},0,{in})"},
    "legende":         {"font": "Inter",          "size": 40,  "color": "blanc", "box": "encre",
                        "an": 2, "y": .90, "in": 200, "out": 200, "anim": ""},
    "compteur":        {"font": "JetBrains Mono", "size": 96,  "color": "cyan",  "box": None,
                        "an": 5, "y": .50, "in": 120, "out": 120,
                        "anim": "\\fscx140\\fscy140\\t(0,{in},\\fscx100\\fscy100)"},
    "chapitre":        {"font": "Cinzel",         "size": 80,  "color": "blanc", "box": None,
                        "an": 4, "y": .50, "in": 400, "out": 300,
                        "anim": "\\move({x0},{y},{x1},{y},0,{in})"},
    "citation":        {"font": "Abril Fatface",  "size": 56,  "color": "blanc", "box": None,
                        "an": 5, "y": .45, "in": 500, "out": 400, "anim": ""},
    "hashtag":         {"font": "Bungee",         "size": 72,  "color": "or",    "box": "encre",
                        "an": 3, "y": .12, "in": 200, "out": 200,
                        "anim": "\\fscx60\\fscy60\\t(0,{in},\\fscx100\\fscy100)"},
    "cta":             {"font": "Archivo Black",  "size": 68,  "color": "encre", "box": "or",
                        "an": 5, "y": .85, "in": 220, "out": 220,
                        "anim": "\\fscx90\\fscy90\\t(0,{in},\\fscx105\\fscy105)"
                                "\\t({in},{in2},\\fscx100\\fscy100)"},
}
DEFAULT_TEMPLATE = "plein_cadre"
MAX_TEXT = 120
MAX_SUB = 160

#: Ancrages \an par bande : 1/2/3 = bas, 4/5/6 = milieu, 7/8/9 = haut.
_AN_BAS = (1, 2, 3)


def _num(v, d=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else d
    except (TypeError, ValueError):
        return d


def title_spec(clip: dict) -> dict | None:
    """Assainit un clip titre -> spec, ou None s'il n'y a rien a ecrire."""
    if not isinstance(clip, dict):
        return None
    t = clip.get("title") if isinstance(clip.get("title"), dict) else {}
    text = str(t.get("text") or "").strip()[:MAX_TEXT]
    if not text:
        return None
    tpl = str(t.get("template") or DEFAULT_TEMPLATE)
    if tpl not in TEMPLATES:
        tpl = DEFAULT_TEMPLATE
    start, end = round(_num(clip.get("start")), 3), round(_num(clip.get("end")), 3)
    if end <= start:
        return None
    color = str(t.get("color") or TEMPLATES[tpl]["color"])
    if color not in BRAND:
        color = TEMPLATES[tpl]["color"]
    font = str(t.get("font") or TEMPLATES[tpl]["font"])
    if font not in S.FONT_FILES:
        font = TEMPLATES[tpl]["font"]
    size = int(max(24, min(200, _num(t.get("size"), TEMPLATES[tpl]["size"]))))
    return {"template": tpl, "text": text,
            "sub": str(t.get("sub") or "").strip()[:MAX_SUB],
            "color": color, "font": font, "size": size, "start": start, "end": end}


def _wrap(text: str, w: int, size: int) -> str:
    """Repli automatique par LARGEUR APPROCHEE.

    L'en-tete porte `WrapStyle: 2` (repli automatique desactive, comme
    `subtitle_service.to_ass`) : sans cette fonction, un titre long deborderait
    du cadre en silence. On ne mesure pas la fonte (ce serait ouvrir Pillow a
    chaque evenement) : on prend 0,55 em de large par caractere en moyenne sur
    90 % du cadre, soit `W*0.9/(size*0.55)` caracteres par ligne, jamais moins
    de 8. Les sauts de ligne poses par l'auteur sont respectes ; un mot plus
    long qu'une ligne est coupe net.
    """
    per = max(8, int(w * 0.9 / max(1.0, size * 0.55)))
    out: list[str] = []
    for para in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        ligne = ""
        for mot in para.split(" "):
            while len(mot) > per:
                if ligne:
                    out.append(ligne)
                    ligne = ""
                out.append(mot[:per])
                mot = mot[per:]
            if not mot:
                continue
            cand = mot if not ligne else ligne + " " + mot
            if len(cand) > per:
                out.append(ligne)
                ligne = mot
            else:
                ligne = cand
        out.append(ligne)
    return "\n".join(out)


def _style_line(name: str, font: str, size: int, couleur: str,
                boite: str | None, an: int) -> str:
    """Une ligne `Style:` du bloc [V4+ Styles], format `_ASS_FORMAT_STYLE`.

    21/09/2026 — libass dessine la boite de `BorderStyle: 3` avec la
    OutlineColour (et non la BackColour de VSFilter) : la couleur de boite est
    donc portee par les DEUX champs, sinon un `cta` (encre sur or) serait du
    noir sur noir. Sans boite, le contour reprend l'encre de la charte.
    """
    prim = S._ass_color(BRAND[couleur])
    if boite:
        bord, back, bs = S._ass_color(BRAND[boite]), S._ass_color(BRAND[boite]), 3
    else:
        bord, back, bs = S._ass_color(BRAND["encre"]), "&H80000000", 1
    return (f"Style: {name},{font},{size},{prim},{prim},{bord},{back},"
            f"0,0,0,0,100,100,0,0,{bs},2,0,{an},40,40,40,1")


def _ass_text(spec: dict, canvas: tuple[int, int]) -> str:
    """Le fichier ASS complet d'UN titre : en-tete, deux styles, un ou deux
    evenements (le titre, puis le sous-texte s'il y en a un)."""
    W, H = int(canvas[0]), int(canvas[1])
    tpl = TEMPLATES[spec["template"]]
    scale = H / S.REF_HEIGHT
    size = max(8, int(round(spec["size"] * scale)))
    subsize = max(12, int(round(size * .45)))
    boite = tpl["box"]
    # Sur une boite claire (or) un sous-texte blanc serait illisible : il
    # reprend alors l'encre, comme le titre.
    coul_sub = "encre" if spec["color"] == "encre" else "blanc"

    lines = ["[Script Info]",
             "; Genere par DeepotusVideoGen - clip titre de la piste t1",
             "ScriptType: v4.00+",
             "WrapStyle: 2",
             "ScaledBorderAndShadow: yes",
             "YCbCr Matrix: TV.709",
             f"PlayResX: {W}",
             f"PlayResY: {H}",
             "",
             "[V4+ Styles]",
             S._ASS_FORMAT_STYLE,
             _style_line("DzT", spec["font"], size, spec["color"], boite, tpl["an"]),
             _style_line("DzS", spec["font"], subsize, coul_sub, boite, tpl["an"]),
             "", "[Events]", S._ASS_FORMAT_EVENT]

    dur_ms = int(round((spec["end"] - spec["start"]) * 1000))
    # Entree et sortie bornees au TIERS du clip : un clip de 0,3 s garde une
    # entree de 100 ms au lieu des 300 ms du gabarit.
    fin = min(tpl["in"], max(0, dur_ms // 3))
    fout = min(tpl["out"], max(0, dur_ms // 3))
    y = int(round(H * tpl["y"]))
    xa = {1: 40, 4: 40, 7: 40, 2: W // 2, 5: W // 2, 8: W // 2,
          3: W - 40, 6: W - 40, 9: W - 40}[tpl["an"]]
    anim = tpl["anim"].format(**{"in": fin, "in2": fin * 2, "y": y,
                                 "x0": xa - int(W * .15), "x1": xa})
    # Un \move porte deja la position : lui ajouter un \pos les ferait se
    # disputer le meme champ (mesure du 21/09/2026 : a t = start + in + 0,1 s
    # le texte est bien a sa place finale x1).
    posi = "" if "\\move(" in anim else "\\pos(%d,%d)" % (xa, y)
    pre = "{\\an%d%s\\fad(%d,%d)%s}" % (tpl["an"], posi, fin, fout, anim)
    t0, t1 = S._ass_time(spec["start"]), S._ass_time(spec["end"])
    lines.append("Dialogue: 0,%s,%s,DzT,,0,0,0,,%s%s"
                 % (t0, t1, pre, S._ass_escape(_wrap(spec["text"], W, size))))

    if spec["sub"]:
        # Ou va le sous-texte ? Avec un ancrage BAS (1/2/3) le titre occupe la
        # bande AU-DESSUS de `y` : poser le sous-texte plus bas le ferait
        # sortir du cadre sur un tiers inferieur. Il passe donc au-dessus
        # (accroche typographique). Pour les ancrages milieu et haut le titre
        # descend depuis `y` : le sous-texte va dessous.
        if tpl["an"] in _AN_BAS:
            ysub = y - int(round(size * 1.05))
        else:
            ysub = y + int(round(size * 1.05))
        pre2 = "{\\an%d\\pos(%d,%d)\\fad(%d,%d)}" % (tpl["an"], xa, ysub, fin, fout)
        lines.append("Dialogue: 1,%s,%s,DzS,,0,0,0,,%s%s"
                     % (t0, t1, pre2, S._ass_escape(_wrap(spec["sub"], W, subsize))))
    return "\n".join(lines) + "\n"


def to_ass_title(spec: dict, canvas: tuple[int, int], stem: str) -> Path | None:
    """Ecrit l'ASS du titre dans `outputs/subtitles/` et rend son chemin.

    UTF-8 **sans BOM** : libass decale la premiere ligne quand le fichier en
    porte un (meme regle que `_subs_ass`)."""
    if not spec:
        return None
    out_dir = settings.outputs_path / "subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([spec, list(canvas), 1],
                                  sort_keys=True).encode("utf-8")).hexdigest()[:10]
    p = out_dir / f"title_{stem}_{key}.ass"
    p.write_bytes(_ass_text(spec, canvas).encode("utf-8"))
    return p


def render_title_png(spec: dict, w: int, h: int, t: float = 1.0) -> Path | None:
    """Apercu : le titre grave sur un fond uni de la charte, une image a `t`.

    Cache par cle dans le dossier d'apercu des effets, meme motif tmp ->
    `replace` et meme verrou par destination que `effects_preview` — dont les
    fonctions `ffmpeg_bin()`, `cache_dir()` et `_frame_lock()` sont REUTILISEES
    telles quelles (mesure du 21/09/2026 : elles existent bien sous ces noms).

    21/09/2026 — le fond est ecrit `color=c=0x14181d` : la forme `#14181d`
    passe aussi (les deux rendent la meme image sur l'ffmpeg 8.1.1 livre), mais
    la forme `0x` ne risque rien dans un argument qui voisine un filtergraph.
    Le `.ass` passe par `subtitles_filter()` : construire le filtre a la main
    laisserait le chemin Windows non echappe (un `C:` casse le graphe).
    """
    from app.services.effects_preview import ffmpeg_bin, cache_dir, _frame_lock

    ass = to_ass_title(spec, (w, h), "prev")
    if not ass:
        return None
    key = hashlib.sha1(json.dumps([spec, w, h, round(float(t), 2), 1],
                                  sort_keys=True).encode("utf-8")).hexdigest()[:24]
    out = cache_dir() / f"tt_{key}.png"
    if out.is_file():
        return out
    with _frame_lock(out.name):
        if out.is_file():
            return out
        tmp = out.with_name(out.stem + ".tmp.png")
        fond = BRAND["encre"].lstrip("#")
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "lavfi",
               "-i", f"color=c=0x{fond}:s={int(w)}x{int(h)}:r=25:d={float(t) + 0.5:.3f}",
               "-vf", S.subtitles_filter(str(ass)),
               "-ss", f"{float(t):.3f}", "-frames:v", "1", "-update", "1", str(tmp)]
        subprocess.run(cmd, check=False, capture_output=True, timeout=60)
        if tmp.is_file() and tmp.stat().st_size:
            tmp.replace(out)
            return out
        if tmp.is_file():
            tmp.unlink()
        return None
