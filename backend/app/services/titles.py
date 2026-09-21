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
`text` est OBLIGATOIRE et doit etre une chaine : un clip qui ne porterait
qu'un `sub` ne produit AUCUN evenement et ce `sub` est PERDU (`title_spec`
rend None). C'est voulu — un sous-texte sans titre n'a pas de place dans les
huit gabarits ; le client doit refuser ce cas en amont.

Tout ce qui touche a l'ASS est repris de `subtitle_service` et n'est PAS
recopie : `_ass_color` (mesure du 21/09/2026 : rend bien `&HAABBGGRR`,
`_ass_color("#e6b23c") == "&H003CB2E6"` — aucun `_bgr` local n'est ecrit),
`_ass_time`, `_ass_escape`, `_ASS_FORMAT_STYLE`, `_ASS_FORMAT_EVENT`,
`REF_HEIGHT`, `FONT_FILES`, `font_line_height` et `subtitles_filter`. Les
seize familles de `FONT_FILES` ont ete re-verifiees a
`PIL.ImageFont.truetype(...).getname()` le 21/09/2026 : les huit familles
citees ci-dessous en sont bien des cles.

ECARTS ASSUMES PAR RAPPORT A LA CONCEPTION D-21 (a reporter en Tache 8) :

* **la boite est OPAQUE**. La conception ecrivait une boite a `&H60`
  (semi-transparente). Mesure du 21/09/2026 : en `BorderStyle: 3` libass
  remplit la boite avec la **OutlineColour** et non la BackColour de
  VSFilter ; porter la couleur de boite dans les deux champs, opaque, est la
  seule forme qui donne un `cta` (encre sur or) lisible. Une boite a 62 %
  laisserait le fond video remonter dans le titre.
* **le contour, hors boite, est l'ENCRE de la charte** et non le noir pur
  `&H00000000` de la conception : l'encre `#14181d` est ce que le reste de
  l'application pose derriere le texte.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import threading
from pathlib import Path

from loguru import logger

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
_AN_MILIEU = (4, 5, 6)

#: Version du FORMAT produit, derniere composante des cles de cache. Elle
#: n'est pas cosmetique : deux versions de ce module qui gravent le meme spec
#: differemment doivent donner des cles differentes, sinon un `.ass` ou un
#: `.png` d'une version precedente serait reservi depuis le cache. A INCREMENTER
#: des que `_ass_text` ou la commande ffmpeg change.
FORMAT_V = 2

#: Apercu : duree bornee du clip normalise, et instant par defaut.
_PREV_DUR_MIN, _PREV_DUR_MAX = 0.2, 10.0

#: Caracteres de controle a retirer d'un texte (sauf \n, conserve comme
#: saut de ligne volontaire par `_wrap`).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_STEM_RE = re.compile(r"[^A-Za-z0-9_-]")


def _num(v, d=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else d
    except (TypeError, ValueError):
        return d


def _propre(s: str, n: int) -> str:
    """Texte d'auteur assaini : caracteres de controle retires (ils
    passeraient tels quels dans le `.ass` et libass s'y perdrait), CRLF
    ramenes a \\n, puis borne a `n` caracteres."""
    s = str(s).replace("\r\n", "\n").replace("\r", "\n")
    return _CTRL_RE.sub("", s).strip()[:n]


def title_spec(clip: dict) -> dict | None:
    """Assainit un clip titre -> spec, ou None s'il n'y a rien a ecrire."""
    if not isinstance(clip, dict):
        return None
    t = clip.get("title") if isinstance(clip.get("title"), dict) else {}
    # `text` doit etre une CHAINE : un nombre ou une liste venus du client ne
    # sont pas convertis en silence, ils font un clip sans titre.
    if not isinstance(t.get("text"), str):
        return None
    text = _propre(t.get("text"), MAX_TEXT)
    if not text:
        return None
    tpl = t.get("template") if isinstance(t.get("template"), str) else ""
    if tpl not in TEMPLATES:
        tpl = DEFAULT_TEMPLATE
    start, end = round(_num(clip.get("start")), 3), round(_num(clip.get("end")), 3)
    if end <= start:
        return None
    color = t.get("color") if isinstance(t.get("color"), str) else ""
    if color not in BRAND:
        color = TEMPLATES[tpl]["color"]
    font = t.get("font") if isinstance(t.get("font"), str) else ""
    if font not in S.FONT_FILES:
        font = TEMPLATES[tpl]["font"]
    size = int(max(24, min(200, _num(t.get("size"), TEMPLATES[tpl]["size"]))))
    sub = _propre(t.get("sub"), MAX_SUB) if isinstance(t.get("sub"), str) else ""
    return {"template": tpl, "text": text, "sub": sub,
            "color": color, "font": font, "size": size, "start": start, "end": end}


def _wrap(text: str, w: int, size: int) -> str:
    """Repli automatique par LARGEUR APPROCHEE.

    L'en-tete porte `WrapStyle: 2` (repli automatique desactive, comme
    `subtitle_service.to_ass`) : sans cette fonction, un titre long deborderait
    du cadre en silence. On ne mesure pas la fonte (ce serait ouvrir Pillow a
    chaque evenement) : on prend 0,55 em de large par caractere en moyenne sur
    90 % du cadre, soit `W*0.9/(size*0.55)` caracteres par ligne, jamais moins
    de 8. `size` est ici l'em DESSINE en pixels, avant le facteur
    `font_line_height` de la ligne `Style:` — c'est bien la largeur du glyphe
    qui compte, pas la hauteur de ligne. Les sauts de ligne poses par l'auteur
    sont respectes ; un mot plus long qu'une ligne est coupe net.
    """
    per = max(8, int(w * 0.9 / max(1.0, size * 0.55)))
    out: list[str] = []
    for para in str(text).split("\n"):
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
                boite: str | None, an: int, marge: int) -> str:
    """Une ligne `Style:` du bloc [V4+ Styles], format `_ASS_FORMAT_STYLE`.

    21/09/2026 — deux pieges de libass, tous deux deja documentes dans
    `_ass_style_line` du service de sous-titres et repris ici :

    * le corps ecrit dans le fichier N'EST PAS l'em dessine : libass dessine
      `em = Fontsize / font_line_height(fonte)`. On pre-multiplie donc par ce
      facteur pour que le px voulu soit le px grave. Sans lui, un `hashtag` en
      Bungee (facteur 2,574) a 72 serait dessine a ~28 px ;
    * en `BorderStyle: 3` la boite est remplie avec la OutlineColour, pas avec
      la BackColour : la couleur de boite est portee par les DEUX champs,
      sinon un `cta` (encre sur or) serait du noir sur noir.
    """
    prim = S._ass_color(BRAND[couleur])
    corps = size * S.font_line_height(font)
    if boite:
        bord, back, bs = S._ass_color(BRAND[boite]), S._ass_color(BRAND[boite]), 3
    else:
        bord, back, bs = S._ass_color(BRAND["encre"]), "&H80000000", 1
    return (f"Style: {name},{font},{corps:g},{prim},{prim},{bord},{back},"
            f"0,0,0,0,100,100,0,0,{bs},2,0,{an},{marge},{marge},{marge},1")


def _ass_text(spec: dict, canvas: tuple[int, int]) -> str:
    """Le fichier ASS complet d'UN titre : en-tete, deux styles, un ou deux
    evenements (le titre, puis le sous-texte s'il y en a un)."""
    W, H = int(canvas[0]), int(canvas[1])
    tpl = TEMPLATES[spec["template"]]
    scale = H / S.REF_HEIGHT
    size = max(8, int(round(spec["size"] * scale)))
    subsize = max(12, int(round(size * .45)))
    marge = max(4, int(round(40 * scale)))
    boite = tpl["box"]
    # Lisibilite du sous-texte : c'est la BOITE qui decide, pas la couleur du
    # titre. Sur une boite claire (or, blanc) un sous-texte blanc serait
    # illisible — il passe a l'encre.
    coul_sub = "encre" if boite in ("or", "blanc") else "blanc"

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
             _style_line("DzT", spec["font"], size, spec["color"], boite, tpl["an"], marge),
             _style_line("DzS", spec["font"], subsize, coul_sub, boite, tpl["an"], marge),
             "", "[Events]", S._ASS_FORMAT_EVENT]

    dur_ms = int(round((spec["end"] - spec["start"]) * 1000))
    # Entree et sortie bornees au TIERS du clip : un clip de 0,3 s garde une
    # entree de 100 ms au lieu des 300 ms du gabarit.
    fin = min(tpl["in"], max(0, dur_ms // 3))
    fout = min(tpl["out"], max(0, dur_ms // 3))
    y = int(round(H * tpl["y"]))
    xa = {1: marge, 4: marge, 7: marge, 2: W // 2, 5: W // 2, 8: W // 2,
          3: W - marge, 6: W - marge, 9: W - marge}[tpl["an"]]
    anim = tpl["anim"].format(**{"in": fin, "in2": fin * 2, "y": y,
                                 "x0": xa - int(W * .15), "x1": xa})
    # Un \move porte deja la position : lui ajouter un \pos les ferait se
    # disputer le meme champ (mesure du 21/09/2026 : a t = start + in + 0,1 s
    # le texte est bien a sa place finale x1).
    posi = "" if "\\move(" in anim else "\\pos(%d,%d)" % (xa, y)
    pre = "{\\an%d%s\\fad(%d,%d)%s}" % (tpl["an"], posi, fin, fout, anim)
    t0, t1 = S._ass_time(spec["start"]), S._ass_time(spec["end"])
    corps = _wrap(spec["text"], W, size)
    lines.append("Dialogue: 0,%s,%s,DzT,,0,0,0,,%s%s"
                 % (t0, t1, pre, S._ass_escape(corps)))

    if spec["sub"]:
        # OU VA LE SOUS-TEXTE ? Sous la demi-hauteur REELLE du bloc de titre,
        # qui depend du NOMBRE DE LIGNES qu'a produites `_wrap` : une citation
        # repliee sur cinq lignes aurait sinon son sous-texte grave PAR-DESSUS
        # la quatrieme (mesure du 21/09/2026). L'avance de ligne de libass
        # est le champ Fontsize, donc `size * font_line_height(fonte)`.
        #
        # Selon l'ancrage, le bloc de titre s'etend depuis `y` :
        #   bas (1/2/3)     -> entierement AU-DESSUS  -> le sous-texte monte
        #   milieu (4/5/6)  -> a cheval, demi de part et d'autre
        #   haut (7/8/9)    -> entierement AU-DESSOUS -> le sous-texte descend
        n = corps.count("\n") + 1
        av = size * S.font_line_height(spec["font"])
        if tpl["an"] in _AN_BAS:
            ysub = y - int(round(av * (n + 0.25)))
        elif tpl["an"] in _AN_MILIEU:
            ysub = y + int(round(av * (n / 2 + 0.75)))
        else:
            ysub = y + int(round(av * (n + 0.25)))
        pre2 = "{\\an%d\\pos(%d,%d)\\fad(%d,%d)}" % (tpl["an"], xa, ysub, fin, fout)
        lines.append("Dialogue: 1,%s,%s,DzS,,0,0,0,,%s%s"
                     % (t0, t1, pre2, S._ass_escape(_wrap(spec["sub"], W, subsize))))
    return "\n".join(lines) + "\n"


def _stem(s: str) -> str:
    """Un `stem` vient d'un identifiant de clip ou d'un nom de projet : il
    devient un NOM DE FICHIER, donc tout ce qui n'est pas alphanumerique est
    remplace (un `..\\` s'y glisserait sinon)."""
    return _STEM_RE.sub("_", str(s or "t"))[:40] or "t"


def _tmp_voisin(dst: Path) -> Path:
    """Fichier temporaire propre a CE processus et a CE fil (meme motif que
    `effects_preview._extract_frame`) : deux rendus concurrents du meme titre
    ne s'ecrasent pas a mi-ecriture."""
    return dst.with_name(f"{dst.stem}.{os.getpid()}-{threading.get_ident()}.tmp{dst.suffix}")


def to_ass_title(spec: dict, canvas: tuple[int, int], stem: str,
                 dest: Path | None = None) -> Path | None:
    """Ecrit l'ASS du titre et rend son chemin.

    `dest` par defaut = `outputs/subtitles/` (a cote des `.ass` de la piste
    s1). L'apercu, lui, passe son propre dossier de cache : ses fichiers
    n'ont rien a faire dans le dossier des sous-titres du montage.

    Le contenu est entierement determine par la cle (spec + canevas + version
    de format) : un fichier deja present est donc RENDU TEL QUEL, sans
    reecriture. Sinon l'ecriture passe par un temporaire puis `replace`, pour
    qu'un lecteur concurrent ne voie jamais un `.ass` a moitie ecrit.

    UTF-8 **sans BOM** : libass decale la premiere ligne quand le fichier en
    porte un (meme regle que `_subs_ass`).
    """
    if not spec:
        return None
    out_dir = Path(dest) if dest is not None else settings.outputs_path / "subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([spec, list(canvas), FORMAT_V],
                                  sort_keys=True).encode("utf-8")).hexdigest()[:10]
    p = out_dir / f"title_{_stem(stem)}_{key}.ass"
    if p.is_file():
        return p
    tmp = _tmp_voisin(p)
    tmp.write_bytes(_ass_text(spec, canvas).encode("utf-8"))
    tmp.replace(p)
    return p


def _spec_apercu(spec: dict, t: float | None) -> tuple[dict, float]:
    """Spec NORMALISEE pour un apercu, et l'instant absolu a extraire.

    Un apercu ne connait pas la place du clip dans la timeline : le titre y
    commence toujours a 0. Sans cette normalisation, l'apercu d'un clip pose
    a 30 s serait grave a 30 s et l'image extraite a 1 s serait VIDE — puis
    mise en cache, donc vide pour toujours (mesure du 21/09/2026).

    `t` est compte DEPUIS LE DEBUT DU TITRE. None = `min(1, duree/2)`, soit
    apres l'animation d'entree de tous les gabarits sur un clip normal.
    """
    dur = max(_PREV_DUR_MIN, min(_PREV_DUR_MAX, _num(spec.get("end")) - _num(spec.get("start"))))
    s = dict(spec)
    s["start"], s["end"] = 0.0, round(dur, 3)
    tt = min(1.0, dur / 2) if t is None else _num(t, 0.0)
    return s, max(0.0, min(tt, dur - 0.01))


def render_title_png(spec: dict, w: int, h: int, t: float | None = None) -> Path | None:
    """Apercu : le titre grave sur un fond uni de la charte, une image a `t`
    secondes APRES LE DEBUT DU TITRE (cf. `_spec_apercu`).

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

    if not spec:
        return None
    s, tt = _spec_apercu(spec, t)
    cache = cache_dir()
    ass = to_ass_title(s, (w, h), "prev", dest=cache)
    if not ass:
        return None
    key = hashlib.sha1(json.dumps([s, w, h, round(tt, 2), FORMAT_V],
                                  sort_keys=True).encode("utf-8")).hexdigest()[:24]
    out = cache / f"tt_{key}.png"
    if out.is_file():
        return out
    with _frame_lock(out.name):
        if out.is_file():
            return out
        tmp = _tmp_voisin(out)
        fond = BRAND["encre"].lstrip("#")
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error",
               "-f", "lavfi",
               "-i", f"color=c=0x{fond}:s={int(w)}x{int(h)}:r=25:d={s['end'] + 0.5:.3f}",
               "-vf", S.subtitles_filter(str(ass)),
               "-ss", f"{tt:.3f}", "-frames:v", "1", "-update", "1", str(tmp)]
        try:
            r = subprocess.run(cmd, check=False, capture_output=True, timeout=60)
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("apercu de titre : ffmpeg injoignable ({})", e)
            return None
        if r.returncode != 0:
            err = (r.stderr or b"").decode("utf-8", "replace")[-400:]
            logger.warning("apercu de titre : ffmpeg a rendu {} ({})", r.returncode, err)
        if tmp.is_file() and tmp.stat().st_size:
            tmp.replace(out)
            return out
        if tmp.is_file():
            tmp.unlink()
        return None
