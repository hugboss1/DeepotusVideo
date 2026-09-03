# -*- coding: utf-8 -*-
"""Pont entre le style d'INTERFACE des sous-titres et le style du MOTEUR.

Deux vocabulaires coexistent, et c'est voulu :

* `frontend/patches/subs.js` decrit un style avec les mots d'un panneau
  (`bgOn`, `outW`, `marginV`, `karOn`, `maxChars`...), en pixels du CANEVAS
  DE RENDU ramene a sa LARGEUR de reference (1080 en portrait, 1920 en
  paysage — cf. `subsOverlay`, qui met l'apercu a cette echelle).
* `subtitle_service.py` decrit un style avec les mots d'un fichier ASS
  (`outline`, `back_opacity`, `margin_v`, `chars_per_line`...), en pixels
  ramenes a une HAUTEUR de reference de 1080 (`to_ass` remet a l'echelle par
  hauteur/1080).

Sans conversion explicite, un « 42 px » du panneau sortirait a 75 px au
rendu en 9:16 (rapport 1920/1080) : l'apercu mentirait. Ce module fait la
conversion dans les deux sens, canevas connu, pour que **le style vu dans
l'apercu soit celui qui sort au rendu**.

Il est PUR : aucune I/O, aucun reseau, aucun `settings`. Il ne fait que
traduire des dictionnaires.

── Les reglages qui ne survivaient pas a la gravure ────────────────────────
Six reglages etaient proposes a l'ecran sans jamais atteindre la video. Un
reglage qui n'agit pas sur le livrable n'a rien a faire dans un panneau de
style : chacun a donc ete tranche, apres MESURE sur une vraie gravure ffmpeg
(pixels lus a l'image, pas deduits de la doc ASS).

===========================  =========  ====================================
reglage                      decision   pourquoi
===========================  =========  ====================================
coins arrondis du fond       RETIRE     libass ne dessine que la boite a
                                        angles droits (BorderStyle 3).
flou d'ombre                 RETIRE     l'ombre ASS est une copie decalee
                                        dure ; aucun flou n'existe.
interligne                   RETIRE     libass fixe l'ecart des lignes a
                                        1,000 x le corps (mesure : 40 px a
                                        corps 40, 80 a 80, idem Anton et
                                        Bebas). L'apercu est cale dessus.
fond pleine largeur          RETIRE     BorderStyle 4 rend EXACTEMENT comme
                                        le 3 (mesure : 258 px contre 260 sur
                                        640) — la promesse etait vide.
animations d'entree          2 GRAVEES  fondu = `\\fad`, pop = `\\t` sur
                             2 RETIREES l'echelle : verifies a l'image.
                                        Montee et machine a ecrire n'ont pas
                                        d'equivalent honnete.
karaoke « echelle »          RETIRE     l'ASS ne sait que basculer une
                                        couleur ; restent remplissage et
                                        boite.
===========================  =========  ====================================

Il reste des ecarts NOMMES (`ui_unsupported`) que l'on ne peut pas supprimer
sans amputer : contour + fond simultanes, fond translucide sous karaoke,
karaoke « boite » sans fond. Ils sont dits, pas caches.
"""
from __future__ import annotations

from app.services import subtitle_service as S

__all__ = [
    "UI_FONT_ALIAS", "ui_font", "ui_to_style", "style_to_ui",
    "ui_karaoke", "ui_karaoke_mode", "ui_anim", "ui_unsupported", "ui_presets",
    "ui_wrap", "ui_wrap_segments", "UI_ANIMS", "UI_LINE_HEIGHT",
    "canvas_for_ratio", "REF_W_PORTRAIT", "REF_W_LANDSCAPE",
]

#: Interligne REEL de libass, mesure sur gravure : exactement 1,000 x le
#: `Fontsize` du fichier ASS, quelles que soient la fonte et la taille.
#: Ce 1,0 est donc un rapport au CORPS DU FICHIER, pas a l'em dessine : depuis
#: la correction d'echelle de `to_ass`, Fontsize = em x
#: `S.font_line_height(fonte)`, et l'apercu doit poser CE rapport en
#: `line-height` (il le recoit dans `/api/subtitles/fonts`). Le reglage
#: « interligne » a disparu du panneau parce qu'il ne pouvait rien changer au
#: fichier livre.
UI_LINE_HEIGHT = 1.0

#: Largeur de reference de l'apercu (subsOverlay : `canvasW`).
REF_W_PORTRAIT = 1080
REF_W_LANDSCAPE = 1920

#: Fontes SYSTEME proposees par le repli du panneau -> fonte EMBARQUEE la plus
#: proche. Le panneau bascule sur les familles embarquees des que
#: GET /api/subtitles/fonts repond ; cette table couvre les styles deja
#: enregistres avant, et les .srt importes d'ailleurs.
UI_FONT_ALIAS: dict[str, str] = {
    "impact": "Anton",
    "haettenschweiler": "Anton",
    "bahnschrift": "Bebas Neue",
    "bahnschrift condensed": "Bebas Neue",
    "arial narrow": "Bebas Neue",
    "arial black": "Archivo Black",
    "franklin gothic medium": "Archivo Black",
    "georgia": "Cinzel",
    "times new roman": "Cinzel",
    "garamond": "Cinzel",
    "courier new": "JetBrains Mono",
    "consolas": "JetBrains Mono",
    "comic sans ms": "Permanent Marker",
    "segoe script": "Permanent Marker",
    "brush script mt": "Pacifico",
    "segoe ui": "Inter",
    "arial": "Inter",
    "helvetica": "Inter",
    "verdana": "Inter",
    "tahoma": "Inter",
    "trebuchet ms": "Inter",
    "calibri": "Inter",
    "roboto": "Inter",
    "system-ui": "Inter",
    "sans-serif": "Inter",
}


def ui_font(name: str | None) -> str:
    """Famille du panneau -> famille EMBARQUEE reellement gravable.

    Une famille embarquee passe telle quelle ; une fonte systeme prend son
    alias ; l'inconnu retombe sur `Inter` (jamais sur le silence de libass).
    """
    raw = (name or "").strip()
    if S.font_path(raw) is not None:
        # font_path tolere la casse : on renvoie le nom canonique
        low = raw.lower()
        for fam in S.FONT_FILES:
            if fam.lower() == low:
                return fam
        return raw
    return UI_FONT_ALIAS.get(raw.lower(), S.DEFAULT_FONT)


def canvas_for_ratio(ratio: str | None, preview: bool = False) -> tuple[int, int]:
    """`"9:16"` -> (1080, 1920). Meme table que `montage_service._CANVAS`."""
    table = {"9:16": (1080, 1920), "16:9": (1920, 1080),
             "1:1": (1080, 1080), "4:5": (1080, 1350)}
    w, h = table.get(str(ratio or "9:16"), (1080, 1920))
    if preview:
        w, h = w // 4, h // 4
        w, h = w - w % 2, h - h % 2
    return w, h


def _num(v, default=0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float(default)
    return f if f == f else float(default)     # NaN -> defaut


def _hex6(v, default="#000000") -> str:
    """`#RRGGBB` ou `#RRGGBBAA` -> `#RRGGBB` (l'alpha part ailleurs)."""
    s = str(v or "").strip()
    if len(s) == 9 and s.startswith("#"):
        s = s[:7]
    if len(s) != 7 or not s.startswith("#"):
        return default
    try:
        int(s[1:], 16)
    except ValueError:
        return default
    return s.lower()


def _hex_alpha(v, default=1.0) -> float:
    """Alpha d'un `#RRGGBBAA` (1.0 si la couleur n'en porte pas)."""
    s = str(v or "").strip()
    if len(s) == 9 and s.startswith("#"):
        try:
            return int(s[7:], 16) / 255.0
        except ValueError:
            return default
    return default


def _scale(canvas: tuple[int, int]) -> float:
    """Facteur px-apercu -> px-@1080-de-haut, pour un canevas donne.

    px reels a l'ecran      = ui * W / refW           (regle de subsOverlay)
    px reels au rendu ASS   = valeur * H / 1080       (regle de to_ass)
    => valeur = ui * (W / refW) * (1080 / H)
    """
    w, h = int(canvas[0] or 1080), int(canvas[1] or 1920)
    ref_w = REF_W_LANDSCAPE if w > h else REF_W_PORTRAIT
    if h <= 0 or ref_w <= 0:
        return 1.0
    return (w / float(ref_w)) * (S.REF_HEIGHT / float(h))


def ui_wrap(text: str, max_chars, style: dict | None = None,
            canvas: tuple[int, int] | None = None) -> list[str]:
    """Coupe en lignes comme le PANNEAU, sur ses DEUX criteres.

    Le fichier ASS est ecrit en ``WrapStyle: 2`` : libass ne replie rien tout
    seul, seules les coupes qu'on y met sont gravees. Il faut donc reproduire
    ici ce que l'apercu fait — et l'apercu coupe pour deux raisons, pas une :

    1. `maxChars` (`subsLines` de subs.js, remplissage glouton par mots) ;
    2. la LARGEUR du cadre : le bloc de texte occupe `width` % du lecteur et
       le navigateur replie ce qui deborde. C'est ce second critere qui
       manquait, et le defaut se voyait a l'image : le panneau montrait trois
       lignes, la gravure sortait une ligne unique qui debordait des deux
       cotes du cadre (constate sur un rendu reel, pas deduit).

    La largeur est MESUREE avec la vraie fonte quand PIL est la
    (`_measure_px`) ; sans PIL, seul le critere de caracteres s'applique et
    l'avertissement `ligne_trop_large` de `check_quality` reste le filet.
    Un mot n'est jamais tronconne ; un texte deja porteur de retours a la
    ligne est respecte tel quel.
    """
    t = str(text or "")
    if "\n" in t:
        return t.split("\n")
    mc = max(8, int(_num(max_chars, 42)))

    usable = None
    scale = 1.0
    if style and canvas:
        w, h = int(canvas[0] or 1080), int(canvas[1] or 1920)
        scale = (h / float(S.REF_HEIGHT)) if h else 1.0
        usable = max(1.0, w - 2 * style["margin_h"] * scale)

    def _too_wide(line: str) -> bool:
        if usable is None:
            return False
        px = S._measure_px(line, style, scale)
        return px is not None and px > usable

    lines, cur = [], ""
    for w in t.split():
        if not cur:
            cur = w
            continue
        cand = cur + " " + w
        if len(cand) <= mc and not _too_wide(cand):
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def ui_wrap_segments(segments, max_chars, style: dict | None = None,
                     canvas: tuple[int, int] | None = None) -> list[dict]:
    """Applique `ui_wrap` au texte de chaque segment (le calage par mot n'est
    pas touche : `to_ass` re-plie les `\\k` sur les lignes qu'il trouve)."""
    out = []
    for s in segments or []:
        if not isinstance(s, dict):
            continue
        s = dict(s)
        s["text"] = "\n".join(ui_wrap(s.get("text", ""), max_chars,
                                      style, canvas))
        out.append(s)
    return out


def ui_karaoke(ui: dict | None) -> bool:
    return bool((ui or {}).get("karOn", True))


#: `karMode` du panneau -> tag ASS de `to_ass`. « remplissage » se grave en
#: `\k` (bascule de couleur), « boite » en `\ko` — qui, en BorderStyle 3,
#: colore la BOITE du mot (verifie a l'image : la surface coloree passe de
#: 7 117 a 13 858 px entre deux instants du meme evenement).
#: « echelle » a ete RETIRE du panneau : l'ASS ne sait pas grossir un mot au
#: milieu d'une ligne. Un style enregistre avant le retrait retombe sur
#: « remplissage », et `ui_unsupported` le dit.
_KMODE = {"fill": "bond", "box": "boite", "scale": "bond"}

#: Animations d'entree du panneau -> animation gravable de `to_ass`.
#: « montee » et « machine a ecrire » ont ete RETIREES : rien ne les grave
#: honnetement. Un style enregistre avant le retrait retombe sur « aucune ».
UI_ANIMS = {"none": "none", "fade": "fondu", "fondu": "fondu", "pop": "pop"}


def ui_karaoke_mode(ui: dict | None) -> str:
    return _KMODE.get(str((ui or {}).get("karMode") or "fill"), "bond")


def ui_anim(ui: dict | None) -> str:
    """Animation d'entree REELLEMENT gravable pour ce style de panneau."""
    return UI_ANIMS.get(str((ui or {}).get("anim") or "none"), "none")


#: Animation MOT PAR MOT du panneau -> animation gravable de `to_ass`.
#: « couleur » n'a pas d'entree a lui : c'est deja ce que fait le karaoke
#: `\k` (bascule SecondaryColour -> PrimaryColour au temps du mot), il n'y a
#: donc rien a poser en plus et surtout rien a poser en `\pos` — un mot
#: colore reste dans le flux de la ligne. Le panneau garde le mot pour
#: nommer ce qui se passe ; le moteur, lui, ne fait que du karaoke.
UI_WORD_ANIMS = {"none": "none", "couleur": "none",
                 "rebond": "rebond", "glow": "glow"}


def ui_word_anim(ui: dict | None) -> str:
    """Animation par MOT reellement gravable pour ce style de panneau."""
    return UI_WORD_ANIMS.get(str((ui or {}).get("wordAnim") or "none"), "none")


def ui_to_style(ui: dict | None, canvas: tuple[int, int] = (1080, 1920)) -> dict:
    """Style du panneau -> style du moteur, resolu (`resolve_style`).

    `canvas` est le canevas REEL du rendu (apercu 480p compris) : c'est lui
    qui fixe la conversion des tailles. Un dict vide donne le style par
    defaut du panneau converti — jamais une surprise.
    """
    u = dict(ui or {})
    k = _scale(canvas)

    size = _num(u.get("size"), 42)
    out_on = bool(u.get("outOn", True))
    sh_on = bool(u.get("shOn", False))
    bg_on = bool(u.get("bgOn", True))
    bg_mode = str(u.get("bgMode") or "wrap")
    if bg_mode not in ("wrap", "fill"):
        bg_mode = "wrap"

    # Ombre ASS = UNE copie decalee en bas a droite, d'une seule profondeur :
    # ni decalage X/Y separes, ni flou. Le panneau n'expose donc qu'un
    # « decalage » (`shOff`) ; les anciens styles portant shX/shY sont repris
    # par leur plus grand decalage, faute de mieux.
    depth = 0.0
    if sh_on:
        if u.get("shOff") is not None:
            depth = abs(_num(u.get("shOff"), 3))
        else:
            depth = max(abs(_num(u.get("shX"), 0)), abs(_num(u.get("shY"), 3)))

    # Defauts alignes sur ceux du panneau (frontend/patches/subs.js) : largeur
    # 80 % = marges laterales de 10 %, marge du bord 13 %. Les deux tombent
    # au-dessus des reperes que l'apercu TRACE (zone sure 10 %, bande d'UI des
    # reseaux 13 %) : un style incomplet ne doit pas se retrouver grave sous la
    # ligne que le meme ecran dessine.
    width_pct = max(20.0, min(100.0, _num(u.get("width"), 80)))
    w = int(canvas[0] or 1080)
    h = int(canvas[1] or 1920)
    # marge laterale : (100-width)/2 % de la LARGEUR reelle, exprimee @1080 de haut
    margin_h = ((100.0 - width_pct) / 200.0) * w * (S.REF_HEIGHT / float(h or 1080))
    # marge verticale : marginV % de la HAUTEUR reelle, exprimee @1080 de haut
    margin_v = max(0.0, min(45.0, _num(u.get("marginV"), 13))) / 100.0 * S.REF_HEIGHT

    # En BorderStyle 3 (fond en boite), libass reutilise `Outline` comme
    # REMBOURRAGE de la boite : le contour du texte n'existe plus, et c'est le
    # rembourrage du panneau (`bgPad`) qui doit atterrir la. Poser `outW` a la
    # place donnerait une boite collee aux jambages, illisible.
    if bg_on:
        outline = _num(u.get("bgPad"), 12) * k
    elif out_on:
        outline = _num(u.get("outW"), 3) * k
    else:
        outline = 0.0

    st = {
        "font": ui_font(u.get("font")),
        "size": size * k,
        "color": _hex6(u.get("color"), "#ffffff"),
        "karaoke_color": _hex6(u.get("karBox") if str(u.get("karMode")) == "box"
                               else u.get("karColor"), "#ffd400"),
        "outline": outline,
        "outline_color": _hex6(u.get("outColor"), "#000000"),
        "shadow": depth * k,
        "shadow_color": _hex6(u.get("shColor"), "#000000"),
        # « plein » n'existe plus : BorderStyle 4 rend comme le 3 (mesure).
        # Un style enregistre qui le demande encore recoit la boite ajustee,
        # et `ui_unsupported` explique pourquoi.
        "back_mode": "wrap" if bg_on else "none",
        "back_color": _hex6(u.get("bgColor"), "#000000"),
        "back_opacity": (max(0.0, min(100.0, _num(u.get("bgOpacity"), 64))) / 100.0
                         if bg_on else 0.0),
        "align": str(u.get("align") or "center"),
        "valign": str(u.get("valign") or "bottom"),
        "margin_v": int(round(margin_v)),
        "margin_h": int(round(margin_h)),
        "bold": 1 if _num(u.get("weight"), 700) >= 600 else 0,
        "italic": 1 if u.get("italic") else 0,
        "underline": 1 if u.get("underline") else 0,
        "uppercase": 1 if u.get("upper") else 0,
        "spacing": _num(u.get("tracking"), 0) * k,
        # l'interligne n'est plus un reglage : libass le fixe a 1,000 x le
        # corps, mesure a l'image. Poser autre chose serait un mensonge de
        # plus dans le fichier de style.
        "line_height": UI_LINE_HEIGHT,
        "chars_per_line": int(max(8, min(120, _num(u.get("maxChars"), 42)))),
    }
    # `preset` n'est PAS transmis : le panneau envoie toujours le style
    # RESOLU (preset + retouches). Le reprendre ferait revivre les valeurs du
    # preset moteur par-dessus les retouches de l'utilisateur.
    return S.resolve_style(st)


def style_to_ui(style: dict | str | None,
                canvas: tuple[int, int] = (1080, 1920)) -> dict:
    """Style du moteur -> style du panneau (l'aller-retour du `ui_to_style`).

    Sert a exposer les prereglages du MOTEUR dans le vocabulaire du panneau :
    une seule source de verite (`subtitle_service.STYLES`), deux vues.
    """
    st = S.resolve_style(style)
    k = _scale(canvas) or 1.0
    w = int(canvas[0] or 1080)
    h = int(canvas[1] or 1920)
    box = st["back_mode"] in ("wrap", "band") and st["back_opacity"] > 0
    # inverses exacts des formules de ui_to_style
    width_pct = 100.0 - (st["margin_h"] * 200.0
                         / max(1.0, w * (S.REF_HEIGHT / float(h or 1080))))
    return {
        "font": st["font"],
        "size": round(st["size"] / k, 1),
        "weight": 800 if st["bold"] else 500,
        "italic": bool(st["italic"]),
        "underline": bool(st["underline"]),
        "upper": bool(st["uppercase"]),
        "tracking": round(st["spacing"] / k, 2),
        "align": st["align"], "valign": st["valign"],
        "color": st["color"],
        "maxChars": int(st["chars_per_line"]),
        "maxLines": 2,
        "width": int(round(max(20.0, min(100.0, width_pct)))),
        "marginV": int(round(st["margin_v"] * 100.0 / S.REF_HEIGHT)),
        "bgOn": bool(box),
        "bgColor": st["back_color"],
        "bgOpacity": int(round(st["back_opacity"] * 100)),
        # boite : l'epaisseur `outline` du moteur EST le rembourrage
        "bgPad": round(st["outline"] / k, 1) if box else 12,
        "outOn": st["outline"] > 0 and not box,
        "outColor": st["outline_color"],
        "outW": 0.0 if box else round(st["outline"] / k, 1),
        "shOn": st["shadow"] > 0,
        "shColor": st["shadow_color"],
        "shOff": round(st["shadow"] / k, 1),
        "karOn": True,
        "karColor": st["karaoke_color"],
        "karMode": "fill",
        "karBox": st["karaoke_color"],
        "anim": "none",
    }


def ui_presets(canvas: tuple[int, int] = (1080, 1920)) -> list[dict]:
    """Les prereglages du MOTEUR, dans le vocabulaire du panneau.

    C'est ce que sert `GET /api/subtitles/presets` : les neuf styles qui
    savent reellement se graver, avec leurs fontes embarquees — au lieu du
    repli local du panneau, qui propose des fontes systeme que libass ne
    trouvera pas forcement.
    """
    out = []
    for pid, st in S.STYLES.items():
        out.append({"id": pid, "label": st["label"],
                    "style": style_to_ui(st, canvas)})
    return out


#: Ecarts qui SUBSISTENT entre l'apercu et la gravure. Message a
#: l'utilisateur, pas au developpeur : il doit pouvoir decider (changer le
#: style, ou accepter). Les reglages qui ne pouvaient RIEN produire au rendu
#: ne sont plus la-dedans : ils ont ete retires du panneau (cf. l'entete).
_UI_UNSUPPORTED = {
    "outOn": "Contour du texte AVEC un fond : en ASS la boite de fond consomme "
             "l'epaisseur de contour (elle s'en sert comme rembourrage). Au "
             "rendu le texte n'aura pas de lisere — coupez le fond, ou "
             "acceptez la boite seule.",
    "karMode": "Karaoke « boite » SANS fond derriere le texte : la boite du "
               "mot est celle du fond. Sans fond, le rendu colorera le "
               "contour du mot au lieu de peindre une boite. Activez le fond, "
               "ou passez en « remplissage ».",
    # heritage : styles enregistres AVANT le retrait de ces reglages
    "legacy:bgRadius": "Coins arrondis du fond : ce reglage a ete retire, "
                       "libass ne dessine qu'une boite a angles droits. Le "
                       "style enregistre en garde une valeur, sans effet.",
    "legacy:shBlur": "Flou d'ombre : ce reglage a ete retire, l'ombre ASS est "
                     "une copie decalee dure. La valeur enregistree n'a plus "
                     "d'effet.",
    "legacy:lh": "Interligne : ce reglage a ete retire, libass fixe l'ecart "
                 "des lignes a 1,000 x le corps. L'apercu suit desormais la "
                 "gravure.",
    "legacy:bgMode": "Fond « plein » (pleine largeur) : ce mode a ete retire, "
                     "l'ASS ne sait faire qu'une boite collee au texte. Le "
                     "fond sera ajuste au texte.",
    "legacy:anim": "Animation « {a} » : elle a ete retiree faute d'equivalent "
                   "gravable. Restent le fondu et le pop, qui eux sortent "
                   "vraiment dans la video.",
    "legacy:karScale": "Karaoke « echelle » : ce mode a ete retire, l'ASS ne "
                       "sait pas grossir un mot au milieu d'une ligne. Le "
                       "rendu utilisera « remplissage ».",
}


def ui_unsupported(ui: dict | None, canvas: tuple[int, int] = (1080, 1920)) -> dict:
    """Ce qui, dans CE style de panneau, ne sortira pas au rendu — avec la
    raison. Complete par les limites propres au moteur (`ass_unsupported`).

    Deux familles :

    * les ecarts VIVANTS (contour sous un fond, karaoke boite sans fond,
      fond translucide sous karaoke) — le panneau les affiche a cote du
      reglage fautif, on peut les corriger ;
    * l'HERITAGE (`legacy:*`) — un style enregistre avant que le reglage ne
      soit retire du panneau. On ne le grave pas, on ne le cache pas non plus :
      l'utilisateur doit comprendre pourquoi son ancien reglage n'agit plus.
    """
    u = dict(ui or {})
    out: dict[str, str] = {}
    bg_on = bool(u.get("bgOn", True))
    if bg_on and bool(u.get("outOn")) and _num(u.get("outW"), 3) > 0.5:
        out["outOn"] = _UI_UNSUPPORTED["outOn"]
    kar_on = bool(u.get("karOn", True))
    kmode = str(u.get("karMode") or "fill")
    if kar_on and kmode == "box" and not bg_on:
        out["karMode"] = _UI_UNSUPPORTED["karMode"]

    # heritage
    if bg_on and _num(u.get("bgRadius"), 0) > 0.5:
        out["legacy:bgRadius"] = _UI_UNSUPPORTED["legacy:bgRadius"]
    if bg_on and str(u.get("bgMode") or "wrap") == "fill":
        out["legacy:bgMode"] = _UI_UNSUPPORTED["legacy:bgMode"]
    if bool(u.get("shOn")) and _num(u.get("shBlur"), 0) > 0.5:
        out["legacy:shBlur"] = _UI_UNSUPPORTED["legacy:shBlur"]
    if u.get("lh") is not None and abs(_num(u.get("lh"), 1.0) - 1.0) > 1e-6:
        out["legacy:lh"] = _UI_UNSUPPORTED["legacy:lh"]
    anim = str(u.get("anim") or "none")
    if anim not in UI_ANIMS:
        out["legacy:anim"] = _UI_UNSUPPORTED["legacy:anim"].format(a=anim)
    if kar_on and kmode == "scale":
        out["legacy:karScale"] = _UI_UNSUPPORTED["legacy:karScale"]

    st = ui_to_style(u, canvas)
    out.update(S.ass_unsupported(st, karaoke=ui_karaoke(u)))
    if st.get("font_fallback"):
        out["font"] = (f"Fonte « {st['font_fallback']} » non embarquee : le "
                       f"rendu utilisera « {st['font']} ». Choisissez une "
                       f"fonte de la liste du moteur pour que l'apercu et le "
                       f"rendu coincident.")
    return out
