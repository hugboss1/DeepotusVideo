# -*- coding: utf-8 -*-
"""Piste de sous-titres `s1` du Montage — coeur du sous-titrage.

Modele de segment (le seul contrat public) ::

    {"id": "s1_0001", "start": 0.0, "end": 2.4, "text": "Bonjour le monde",
     "words": [{"w": "Bonjour", "start": 0.0,  "end": 0.9},
               {"w": "le",      "start": 0.9,  "end": 1.1},
               {"w": "monde",   "start": 1.1,  "end": 2.4}],
     "style": "pop"}

Le calage PAR MOT est ce qui rend le karaoke possible : c'est lui qui
alimente les balises ``\\k`` de l'ASS et le surlignage du mot actif dans
l'editeur. Quand il manque, `distribute_words` le fabrique proportionnellement
a la longueur des mots (avec une respiration apres la ponctuation).

Ce module est PUR : aucune I/O, aucun reseau, aucun `settings`. Il ecrit et
relit des chaines de caracteres, c'est la couche route qui les pose sur le
disque. Seule dependance optionnelle : PIL, uniquement pour MESURER la largeur
reelle d'une ligne avec la vraie fonte (controle qualite) — absent, le controle
retombe sur le comptage de caracteres.

Trois formats en ecriture :

* **SRT** — le format d'echange universel. Millisecondes, aucun style.
* **VTT** — idem, plus les balises temporelles par mot ``<00:00:01.500>``
  quand on les demande (`word_timings=True`) : notre VTT peut donc porter le
  karaoke, ce qu'un .srt ne sait pas faire.
* **ASS** (Advanced SubStation Alpha) — LE format qui compte. C'est lui qui
  porte le style reel (fonte, corps, contour, ombre, fond, marges,
  alignement) ET le karaoke natif (``\\k`` / ``\\kf`` / ``\\ko``). C'est ce
  fichier que ffmpeg grave via le filtre `subtitles=`.

Deux formats en lecture (SRT, VTT), tolerants aux variantes du terrain : BOM,
CRLF, virgule OU point decimal, numerotation absente, heures omises
(``00:00.000``), en-tete ``WEBVTT``, blocs ``NOTE``/``STYLE``/``REGION``,
identifiants de cue, reglages de cue (``line:90% align:center``), balises
``<i>``/``<c.jaune>``. Un aller-retour ecriture -> lecture conserve les temps
a la milliseconde.

Ce que la barre (Kapwing) ne fait pas et que l'on fait ici :
`check_quality` — vitesse de lecture en caracteres par seconde, segments trop
courts / trop longs, chevauchements, lignes trop larges (mesurees en PIXELS
avec la vraie fonte). Des avertissements nommes, chacun avec un correctif
applicable (`fix`), pas une note sur 10. `autofix` applique les correctifs
purement temporels.

Les fontes des prereglages sont celles EMBARQUEES dans l'app
(`backend/app/templates/_fonts`), pas des fontes systeme : une fonte absente
fait silencieusement retomber libass sur autre chose. `check_fonts()` verifie
que chaque fichier existe, et `ass_fontsdir()` donne le dossier a passer a
ffmpeg en `fontsdir=` pour que la resolution ne depende pas du poste.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

__all__ = [
    # modele
    "normalize_segments", "distribute_words", "karaoke_spans", "segment_cs",
    # ecriture
    "to_srt", "to_vtt", "to_ass",
    # lecture
    "parse_srt", "parse_vtt", "parse_subtitles", "sniff_format",
    # decoupe
    "auto_break", "auto_break_lines", "split_segment", "split_segments",
    # qualite
    "check_quality", "autofix",
    # correctifs negocies
    "plan_stretch", "plan_boundary", "plan_split", "plan_rewrap", "apply_plan",
    "room_before", "room_after",
    # styles / fontes
    "STYLES", "style_labels", "resolve_style", "ass_unsupported",
    "FONT_FILES", "fonts_dir", "ass_fontsdir", "font_path", "check_fonts",
    "font_line_height",
    # ffmpeg
    "subtitles_filter",
]

# ---------------------------------------------------------------------------
# Fontes embarquees
# ---------------------------------------------------------------------------

#: Nom de FAMILLE interne de la fonte -> fichier livre dans templates/_fonts.
#: Le nom de famille est celui lu dans la table `name` du TTF (verifie avec
#: PIL.ImageFont.getname) : c'est CE nom que libass cherche dans l'ASS. Mettre
#: le nom du fichier a la place donnerait un fallback silencieux.
FONT_FILES: dict[str, str] = {
    "Inter": "Inter.ttf",
    "IBM Plex Sans": "IBMPlexSans.ttf",
    "Space Grotesk": "SpaceGrotesk.ttf",
    "JetBrains Mono": "JetBrainsMono.ttf",
    "Anton": "Anton.ttf",
    "Archivo Black": "ArchivoBlack.ttf",
    "Bebas Neue": "BebasNeue.ttf",
    "Staatliches": "Staatliches.ttf",
    "Righteous": "Righteous.ttf",
    "Bungee": "Bungee.ttf",
    "Abril Fatface": "AbrilFatface.ttf",
    "Permanent Marker": "PermanentMarker.ttf",
    "Pacifico": "Pacifico.ttf",
    "Monoton": "Monoton.ttf",
    "Cinzel": "Cinzel.ttf",
    "Press Start 2P": "PressStart2P.ttf",
}
DEFAULT_FONT = "Inter"


def fonts_dir() -> Path:
    """Dossier des fontes embarquees (`backend/app/templates/_fonts`)."""
    return Path(__file__).resolve().parent.parent / "templates" / "_fonts"


def ass_fontsdir() -> str:
    """Chemin a passer a ffmpeg en `fontsdir=` du filtre `subtitles`."""
    return str(fonts_dir())


def font_path(family: str | None) -> Path | None:
    """Fichier de la fonte `family`, ou None si la famille est inconnue ou son
    fichier absent. Ne retombe PAS silencieusement sur une autre fonte : c'est
    a l'appelant de decider (cf. `resolve_style`)."""
    fn = FONT_FILES.get((family or "").strip())
    if not fn:
        # tolerance de casse : "anton" -> "Anton"
        low = (family or "").strip().lower()
        for k, v in FONT_FILES.items():
            if k.lower() == low:
                fn = v
                break
    if not fn:
        return None
    p = fonts_dir() / fn
    return p if p.exists() else None


#: Rapport MESURE entre le `Fontsize` d'un fichier ASS et l'em que libass
#: dessine reellement. Ce n'est pas un reglage : c'est la convention
#: VSFilter que libass reproduit — le corps ASS vaut la HAUTEUR DE LIGNE de
#: la fonte (usWinAscent + usWinDescent), pas son em.
#: Verifie a l'image sur huit familles embarquees (scratchpad/fontprobe3.py) :
#:   Anton 1,7316 mesure / 1,7334 metrique · Bungee 2,5806 / 2,5740
#:   Inter 1,4235 / 1,4302 · Bebas Neue 1,3029 / 1,3000
#:   Press Start 2P 1,3746 / 1,3740 · Staatliches 1,3115 / 1,3120
#: Sans cette correction, un « 110 px » regle au panneau sortait grave a
#: 110 / 1,43 = 77 px en Inter, et a 63 px en Anton : le defaut d'echelle
#: aperçu/rendu le plus visible de la piste.
_LH_CACHE: dict[str, float] = {}
_LH_FALLBACK = 1.2


def font_line_height(family: str | None) -> float:
    """Facteur `corps ASS / em dessine` de la fonte `family`.

    Lu dans la table OS/2 du .ttf embarque (usWinAscent + usWinDescent divises
    par head.unitsPerEm), en `struct` pur — pas de fontTools dans le runtime
    embarque. Retombe sur 1.2 si le fichier est illisible : mieux vaut une
    echelle approchee qu'une exception au milieu d'un rendu.
    """
    key = (family or "").strip().lower() or DEFAULT_FONT.lower()
    if key in _LH_CACHE:
        return _LH_CACHE[key]
    val = _LH_FALLBACK
    p = font_path(family) or font_path(DEFAULT_FONT)
    if p is not None:
        try:
            import struct

            b = p.read_bytes()
            n = struct.unpack(">H", b[4:6])[0]
            tabs = {}
            for i in range(n):
                o = 12 + 16 * i
                tabs[b[o:o + 4]] = struct.unpack(">II", b[o + 8:o + 16])[0]
            ho, o2 = tabs.get(b"head"), tabs.get(b"OS/2")
            if ho and o2:
                upm = struct.unpack(">H", b[ho + 18:ho + 20])[0]
                wa, wd = struct.unpack(">HH", b[o2 + 74:o2 + 78])
                if upm > 0 and (wa + wd) > 0:
                    val = max(0.5, min(4.0, (wa + wd) / float(upm)))
        except Exception:
            val = _LH_FALLBACK
    _LH_CACHE[key] = val
    return val


def check_fonts() -> dict:
    """Etat des fontes : {"dir", "ok": [familles], "missing": [familles]}.

    Appele par les tests et exposable par l'API : une famille listee dans
    FONT_FILES dont le .ttf a disparu du paquet doit se voir, pas se deviner
    au rendu.
    """
    d = fonts_dir()
    ok, missing = [], []
    for fam, fn in FONT_FILES.items():
        (ok if (d / fn).exists() else missing).append(fam)
    return {"dir": str(d), "ok": sorted(ok), "missing": sorted(missing)}


# ---------------------------------------------------------------------------
# Prereglages de style
# ---------------------------------------------------------------------------
#
# Cles du modele de style (valeurs REELLES, exprimees a la hauteur de
# reference `REF_HEIGHT` = 1080 px ; `to_ass` les met a l'echelle du canevas) :
#
#   label            libelle d'interface (francais)
#   font             famille (doit exister dans FONT_FILES)
#   size             corps en px @1080
#   color            couleur du texte "#RRGGBB"
#   karaoke_color    couleur du mot ACTIF (surlignage karaoke)
#   outline          epaisseur du contour en px @1080 (0 = pas de contour)
#   outline_color    couleur du contour
#   shadow           decalage d'ombre portee en px @1080 (0 = pas d'ombre)
#   shadow_color     couleur de l'ombre
#   back_mode        "none" | "wrap"  (fond en boite collee au texte)
#   back_color       couleur du fond
#   back_opacity     0..1
#   align            "left" | "center" | "right"
#   valign           "bottom" | "middle" | "top"
#   margin_v         marge verticale px @1080
#   margin_h         marges laterales px @1080
#   bold/italic/underline   0|1
#   uppercase        met le texte en capitales A L'ECRITURE ASS
#   spacing          interlettrage px @1080
#   line_height      interligne relatif (1.0 = normal) — NON representable en
#                    ASS, cf. `ass_unsupported`
#   chars_per_line   largeur de ligne conseillee pour ce corps (decoupe + QC)
#
REF_HEIGHT = 1080

_BASE_STYLE = {
    "label": "", "font": DEFAULT_FONT, "size": 64,
    "color": "#ffffff", "karaoke_color": "#ffd400",
    "outline": 3.0, "outline_color": "#000000",
    "shadow": 0.0, "shadow_color": "#000000",
    "back_mode": "none", "back_color": "#000000", "back_opacity": 0.0,
    "align": "center", "valign": "bottom",
    "margin_v": 110, "margin_h": 90,
    "bold": 0, "italic": 0, "underline": 0, "uppercase": 0,
    "spacing": 0.0, "line_height": 1.0, "chars_per_line": 42,
}


def _S(**kw) -> dict:
    s = dict(_BASE_STYLE)
    s.update(kw)
    return s


#: Neuf prereglages nommes en francais — l'equivalent des six de la barre
#: (Default, Pop Art, Highlighter, Butter, Dark Outline, Prime) plus trois.
#: Chacun est defini par des valeurs reelles et converti en style ASS.
STYLES: dict[str, dict] = {
    "standard": _S(
        label="Standard", font="Inter", size=62,
        color="#ffffff", karaoke_color="#ffd400",
        outline=3.5, outline_color="#000000", shadow=2.0,
        margin_v=110, chars_per_line=42),
    "pop": _S(
        label="Pop", font="Anton", size=92,
        color="#ffe600", karaoke_color="#ff2d55",
        outline=7.0, outline_color="#111111", shadow=0.0,
        uppercase=1, spacing=1.0, margin_v=180, chars_per_line=22),
    "surligneur": _S(
        label="Surligneur", font="Archivo Black", size=66,
        color="#111111", karaoke_color="#ffffff",
        outline=0.0, shadow=0.0,
        back_mode="wrap", back_color="#00e676", back_opacity=1.0,
        margin_v=150, chars_per_line=30),
    "beurre": _S(
        label="Beurre", font="Bebas Neue", size=96,
        color="#fff4d6", karaoke_color="#ffb703",
        outline=5.0, outline_color="#3a2a05", shadow=4.0,
        shadow_color="#3a2a05", uppercase=1, spacing=1.5,
        margin_v=160, chars_per_line=26),
    "contour_sombre": _S(
        label="Contour sombre", font="Inter", size=66, bold=1,
        color="#ffffff", karaoke_color="#8ab4ff",
        outline=8.0, outline_color="#0a0a0a", shadow=0.0,
        margin_v=120, chars_per_line=38),
    "prime": _S(
        label="Prime", font="Archivo Black", size=72,
        color="#ffffff", karaoke_color="#00e5ff",
        outline=3.0, outline_color="#000000", shadow=0.0,
        back_mode="wrap", back_color="#000000", back_opacity=0.62,
        margin_v=130, chars_per_line=32),
    "neon": _S(
        label="Neon", font="Righteous", size=74,
        color="#00fff0", karaoke_color="#ff00d4",
        outline=4.0, outline_color="#00343a", shadow=7.0,
        shadow_color="#00343a", margin_v=140, chars_per_line=30),
    "marqueur": _S(
        label="Marqueur", font="Permanent Marker", size=78,
        color="#ffffff", karaoke_color="#ff6b00",
        outline=5.0, outline_color="#151515", shadow=3.0,
        margin_v=150, chars_per_line=28),
    "sobre": _S(
        label="Sobre", font="IBM Plex Sans", size=54,
        color="#ffffff", karaoke_color="#ffffff",
        outline=0.0, shadow=0.0,
        back_mode="wrap", back_color="#000000", back_opacity=0.72,
        # 108 px @1080 = 10 % : le seul prereglage livre qui passait SOUS la
        # zone sure que l'apercu trace (il etait a 90 px, soit 8,3 %). Un
        # prereglage maison ne doit pas declencher notre propre avertissement.
        margin_v=108, chars_per_line=44),
}
DEFAULT_STYLE = "standard"

#: Proprietes du modele de style que l'ASS ne sait PAS porter. On les garde
#: dans le modele (l'apercu canvas les honore) mais on ne pretend pas les
#: graver : `to_ass` les ignore et l'interface peut les griser.
_ASS_UNSUPPORTED = {
    "line_height": "L'ASS n'a pas d'interligne : libass fixe l'écart des "
                   "lignes d'après le corps de la fonte.",
    "back_mode:band": "Un fond pleine largeur n'existe pas en ASS ; le fond "
                      "est une boîte collée au texte (BorderStyle 3).",
    "back_opacity:karaoke": "Fond translucide + karaoké : libass dessine une "
                            "boîte par mot, les recouvrements assombrissent "
                            "une barre à chaque frontière. Passez l'opacité "
                            "du fond à 100 %, ou coupez le karaoké.",
}


def ass_unsupported(style: dict | str | None = None,
                    karaoke: bool = False) -> dict:
    """Proprietes de `style` que `to_ass` ne peut pas graver fidelement, avec
    la raison. Le drapeau `karaoke` ajoute les incompatibilites propres au
    surlignage par mot."""
    st = resolve_style(style)
    out = {}
    if abs(float(st.get("line_height", 1.0)) - 1.0) > 1e-6:
        out["line_height"] = _ASS_UNSUPPORTED["line_height"]
    if str(st.get("back_mode")) == "band":
        out["back_mode"] = _ASS_UNSUPPORTED["back_mode:band"]
    if karaoke and _box_seams(st):
        out["back_opacity"] = _ASS_UNSUPPORTED["back_opacity:karaoke"]
    return out


def _box_seams(st: dict) -> bool:
    """Vrai si ce style produira des coutures entre les mots au karaoke.

    Constate au rendu : en BorderStyle 3, libass dessine UNE boite PAR groupe
    `\\k`. Deux boites voisines se recouvrent, et si elles sont translucides
    les alphas s'additionnent -> une barre plus sombre a chaque frontiere de
    mot. Opaque (back_opacity == 1), les boites sont identiques et la couture
    ne se voit pas.
    """
    return (st.get("back_mode") in ("wrap", "band")
            and 0.0 < float(st.get("back_opacity", 0.0)) < 1.0)


def style_labels() -> list[dict]:
    """Catalogue pour le panneau de style : [{id, label, font, size, ...}]."""
    return [{"id": k, "label": v["label"], "font": v["font"],
             "size": v["size"], "color": v["color"],
             "karaoke_color": v["karaoke_color"],
             "chars_per_line": v["chars_per_line"]}
            for k, v in STYLES.items()]


def resolve_style(style: dict | str | None) -> dict:
    """Style complet a partir d'un nom de preset, d'un dict partiel, ou des
    deux (`{"preset": "pop", "size": 70}`). Toute cle inconnue est ignoree,
    toute cle manquante prend la valeur du preset puis du style de base.

    La fonte est VERIFIEE : si son fichier n'est pas livre, on retombe
    explicitement sur DEFAULT_FONT et on le signale dans `font_fallback`
    plutot que de laisser libass choisir dans le dos de l'utilisateur.
    """
    if isinstance(style, str):
        base = STYLES.get(style) or STYLES[DEFAULT_STYLE]
        st = dict(base)
    elif isinstance(style, dict):
        pre = style.get("preset") or style.get("id")
        base = STYLES.get(str(pre)) if pre else None
        st = dict(base or STYLES[DEFAULT_STYLE])
        for k, v in style.items():
            if k in _BASE_STYLE and v is not None:
                st[k] = v
    else:
        st = dict(STYLES[DEFAULT_STYLE])

    st["font_fallback"] = None
    if font_path(st.get("font")) is None:
        st["font_fallback"] = st.get("font")
        st["font"] = DEFAULT_FONT
    # bornes dures : une valeur absurde ne doit jamais atteindre libass
    st["size"] = max(8.0, min(400.0, float(st.get("size", 64))))
    st["outline"] = max(0.0, min(40.0, float(st.get("outline", 0))))
    st["shadow"] = max(0.0, min(40.0, float(st.get("shadow", 0))))
    st["back_opacity"] = max(0.0, min(1.0, float(st.get("back_opacity", 0))))
    st["spacing"] = max(-20.0, min(40.0, float(st.get("spacing", 0))))
    st["line_height"] = max(0.5, min(3.0, float(st.get("line_height", 1.0))))
    st["margin_v"] = max(0, min(2000, int(st.get("margin_v", 100))))
    st["margin_h"] = max(0, min(2000, int(st.get("margin_h", 90))))
    st["chars_per_line"] = max(8, min(120, int(st.get("chars_per_line", 42))))
    if st.get("align") not in ("left", "center", "right"):
        st["align"] = "center"
    if st.get("valign") not in ("bottom", "middle", "top"):
        st["valign"] = "bottom"
    if st.get("back_mode") not in ("none", "wrap", "band"):
        st["back_mode"] = "none"
    return st


# ---------------------------------------------------------------------------
# Utilitaires temps / couleur / texte
# ---------------------------------------------------------------------------

def _f(v, default=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float(default)
    if x != x or x in (float("inf"), float("-inf")):
        return float(default)
    return x


def _rgb(hexstr: str | None, default="ffffff") -> tuple[int, int, int]:
    s = str(hexstr or "").lstrip("#").strip() or default
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6 or any(c not in "0123456789abcdefABCDEF" for c in s):
        s = default
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _ass_color(hexstr: str | None, alpha: float = 1.0) -> str:
    """&HAABBGGRR — attention, AA est une TRANSPARENCE (00 = opaque)."""
    r, g, b = _rgb(hexstr)
    a = int(round((1.0 - max(0.0, min(1.0, alpha))) * 255))
    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"


def _half_up(x: float) -> int:
    """Arrondi au plus proche, moities VERS LE HAUT.

    `round()` de Python arrondit les moities au pair (8.125 s -> 8.12 s et non
    8.13 s) : sur un horodatage cela retire discretement 5 ms a la fin d'un
    segment. Toute conversion de temps de ce module passe par ici, pour que
    SRT, VTT et ASS racontent exactement la meme chose.
    """
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def _ms(t: float) -> int:
    return _half_up(max(0.0, _f(t)) * 1000)


def _cs(t: float) -> int:
    """Temps en centiemes, base de TOUT l'ASS (son horodatage n'a pas plus de
    resolution)."""
    return _half_up(max(0.0, _f(t)) * 100)


def segment_cs(seg: dict) -> int:
    """Duree d'un segment en centiemes, TELLE QUE l'ASS l'affichera.

    Ce n'est pas `round((end - start) * 100)` : les deux horodatages sont
    arrondis separement dans le fichier, donc la duree reellement rendue est
    la difference des deux arrondis. C'est cette valeur-la que la somme des
    `\\k` doit egaler, sinon le karaoke derive d'un centieme sur les segments
    qui tombent pile entre deux.
    """
    a, b = _f(seg.get("start")), _f(seg.get("end"))
    if b < a:
        a, b = b, a
    return max(0, _cs(b) - _cs(a))


def _srt_time(t: float) -> str:
    ms = _ms(t)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_time(t: float) -> str:
    return _srt_time(t).replace(",", ".")


def _ass_time(t: float) -> str:
    """H:MM:SS.cc — l'ASS est au centieme, pas au millieme."""
    cs = _cs(t)
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    """Echappement du texte d'un evenement ASS (meme regle que ffmpeg) :
    `\\`, `{` et `}` prefixes, saut de ligne -> `\\N`."""
    s = str(text or "")
    s = s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s.replace("\n", "\\N")


_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")           # <i> <b> <c.jaune> <v X>
_TS_TAG_RE = re.compile(r"<(\d{1,2}:)?\d{1,2}:\d{1,2}[.,]\d{1,3}>")


def _strip_markup(s: str) -> str:
    return _TAG_RE.sub("", _TS_TAG_RE.sub("", s or "")).strip()


# ---------------------------------------------------------------------------
# Modele : normalisation et calage des mots
# ---------------------------------------------------------------------------

_WORD_SPLIT = re.compile(r"\s+")
_END_PUNCT_STRONG = ".!?\u2026"          # . ! ? …
_END_PUNCT_WEAK = ",;:\u2013\u2014"      # , ; : – —


def _words_of(text: str) -> list[str]:
    return [w for w in _WORD_SPLIT.split(str(text or "").replace("\n", " ")) if w]


def distribute_words(text: str, start: float, end: float) -> list[dict]:
    """Fabrique un calage par mot quand la transcription n'en fournit pas.

    Poids = longueur du mot + 1, majore d'une respiration apres la ponctuation
    (forte : +2.5, faible : +1.2). Les bornes se touchent exactement (pas de
    trou), le dernier mot finit precisement sur `end`.
    """
    ws = _words_of(text)
    a, b = _f(start), _f(end)
    if b < a:
        a, b = b, a
    if not ws:
        return []
    if b <= a:
        return [{"w": w, "start": a, "end": a} for w in ws]

    weights = []
    for w in ws:
        k = float(len(w)) + 1.0
        tail = w[-1] if w else ""
        if tail in _END_PUNCT_STRONG:
            k += 2.5
        elif tail in _END_PUNCT_WEAK:
            k += 1.2
        weights.append(k)
    total = sum(weights) or 1.0

    out, acc = [], 0.0
    for i, w in enumerate(ws):
        s = a + (b - a) * (acc / total)
        acc += weights[i]
        e = a + (b - a) * (acc / total)
        if i == len(ws) - 1:
            e = b
        out.append({"w": w, "start": round(s, 4), "end": round(e, 4)})
    return out


def _normalize_words(seg_words, text: str, start: float, end: float,
                     clamp: bool = True) -> list[dict]:
    """Nettoie une liste de mots fournie : bornage dans [start, end],
    monotonie forcee, mot vide ecarte. Liste absente ou vide -> repartition.

    `clamp=False` laisse passer les temps hors bornes tels quels : c'est ce
    dont `check_quality` a besoin pour VOIR l'incoherence au lieu de la
    reparer en silence.
    """
    if not isinstance(seg_words, (list, tuple)) or not seg_words:
        return distribute_words(text, start, end)
    out, prev = [], start
    for it in seg_words:
        if not isinstance(it, dict):
            continue
        w = str(it.get("w", it.get("word", ""))).strip()
        if not w:
            continue
        if clamp:
            s = max(start, min(end, _f(it.get("start"), prev)))
            e = max(start, min(end, _f(it.get("end"), s)))
            s = max(s, prev)
            e = max(e, s)
        else:
            s = _f(it.get("start"), prev)
            e = _f(it.get("end"), s)
        out.append({"w": w, "start": round(s, 4), "end": round(e, 4)})
        prev = e
    if not out:
        return distribute_words(text, start, end)
    if clamp:
        out[-1]["end"] = round(end, 4)
    return out


_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def normalize_segments(raw, *, prefix: str = "s1", sort: bool = True,
                       with_words: bool = True,
                       clamp_words: bool = True,
                       keep_empty: bool = False) -> list[dict]:
    """Met une liste brute au contrat : id, start<=end, text, words.

    Les segments sans texte sont ecartes (un blanc ne se grave pas). Le tri
    chronologique est actif par defaut ; on peut le couper pour verifier un
    desordre volontaire dans `check_quality`.

    `keep_empty=True` GARDE les segments vides. Indispensable au controle
    qualite et aux correctifs : sinon un seul sous-titre encore vide (le cas
    normal juste apres « + sous-titre ») decale d'un cran TOUS les indices
    renvoyes au panneau, et chaque avertissement s'affiche sur la carte du
    voisin. C'est un decalage silencieux, donc le pire genre.
    """
    segs = []
    for i, r in enumerate(raw or []):
        if not isinstance(r, dict):
            continue
        text = str(r.get("text", "")).replace("\r\n", "\n").replace("\r", "\n")
        text = "\n".join(ln.strip() for ln in text.split("\n")).strip()
        if not text and not keep_empty:
            continue
        s = max(0.0, _f(r.get("start")))
        e = max(0.0, _f(r.get("end"), s))
        if e < s:
            s, e = e, s
        sid = str(r.get("id") or "").strip()
        sid = _ID_RE.sub("", sid) or f"{prefix}_{i + 1:04d}"
        seg = {"id": sid, "start": round(s, 4), "end": round(e, 4), "text": text}
        if with_words:
            seg["words"] = _normalize_words(r.get("words"), text, s, e,
                                            clamp=clamp_words)
        st = r.get("style")
        if isinstance(st, (str, dict)) and st:
            seg["style"] = st
        segs.append(seg)
    if sort:
        segs.sort(key=lambda x: (x["start"], x["end"]))
    # ids uniques : deux segments avec le meme id casseraient l'editeur (une
    # edition partirait sur le mauvais). Le remplacant est cherche jusqu'a
    # trouver un libre — se contenter de l'index recreerait une collision avec
    # un id auto-genere plus haut.
    seen, out = set(), []
    for i, s in enumerate(segs):
        if s["id"] in seen:
            n = i + 1
            while f"{prefix}_{n:04d}" in seen:
                n += 1
            s = dict(s, id=f"{prefix}_{n:04d}")
        seen.add(s["id"])
        out.append(s)
    return out


# ---------------------------------------------------------------------------
# Karaoke
# ---------------------------------------------------------------------------

def karaoke_spans(seg: dict) -> list[tuple[int, str]]:
    """Decoupe karaoke d'un segment : [(duree_en_centiemes, mot), ...].

    Invariant garanti : ``sum(cs) == segment_cs(seg)``, c'est-a-dire la duree
    telle que l'ASS l'affiche. C'est l'invariant qui rend l'ASS lisible par
    libass — une somme de `\\k` inferieure a la duree laisse la fin de ligne
    non surlignee, une somme superieure fait deborder le karaoke sur la ligne
    suivante.

    Les silences INTER-mots sont absorbes par le `\\k` du mot qui suit : rien
    ne se perd, la somme reste exacte. Le silence de TETE (avant le premier
    mot) est absorbe de la meme facon par le premier mot.
    """
    start, end = _f(seg.get("start")), _f(seg.get("end"))
    if end < start:
        start, end = end, start
    total = segment_cs(seg)
    base_cs = _cs(start)
    words = _normalize_words(seg.get("words"), seg.get("text", ""), start, end)
    if not words:
        return []
    if total <= 0:
        return [(0, w["w"]) for w in words]

    spans, prev_cs = [], 0
    for i, w in enumerate(words):
        cum = _cs(_f(w["end"])) - base_cs
        cum = max(prev_cs, min(total, cum))
        if i == len(words) - 1:
            cum = total
        spans.append((cum - prev_cs, w["w"]))
        prev_cs = cum
    # filet de securite : l'arrondi ne doit jamais faire deriver la somme
    drift = total - sum(k for k, _ in spans)
    if drift:
        k, w = spans[-1]
        spans[-1] = (max(0, k + drift), w)
    return spans


_KARAOKE_TAGS = {"bond": "k", "balayage": "kf", "boite": "ko"}


def _karaoke_text(seg: dict, mode: str = "bond", uppercase: bool = False) -> str:
    tag = _KARAOKE_TAGS.get(str(mode), "k")
    spans = karaoke_spans(seg)
    if not spans:
        return _ass_escape(seg.get("text", ""))
    # Les sauts de ligne du texte doivent survivre au karaoke : on re-plie les
    # mots sur les lignes d'origine.
    lines = [ln for ln in str(seg.get("text", "")).split("\n")]
    counts = [len(_words_of(ln)) for ln in lines]
    out, idx = [], 0
    for n in counts:
        chunk = spans[idx:idx + n]
        idx += n
        out.append("".join(
            "{\\%s%d}%s " % (tag, k, _ass_escape(w.upper() if uppercase else w))
            for k, w in chunk).rstrip())
    if idx < len(spans):                      # mots en trop (texte re-plie)
        out.append("".join(
            "{\\%s%d}%s " % (tag, k, _ass_escape(w.upper() if uppercase else w))
            for k, w in spans[idx:]).rstrip())
    return "\\N".join(x for x in out if x)


# ---------------------------------------------------------------------------
# Ecriture : SRT / VTT / ASS
# ---------------------------------------------------------------------------

def to_srt(segments, *, newline: str = "\n") -> str:
    """SRT numerote, virgule decimale, une ligne blanche entre les blocs."""
    segs = normalize_segments(segments, with_words=False)
    blocks = []
    for i, s in enumerate(segs, 1):
        blocks.append(f"{i}{newline}"
                      f"{_srt_time(s['start'])} --> {_srt_time(s['end'])}{newline}"
                      f"{s['text'].replace(chr(10), newline)}{newline}")
    return newline.join(blocks)


def to_vtt(segments, *, word_timings: bool = False, newline: str = "\n") -> str:
    """WebVTT. `word_timings=True` insere les balises temporelles par mot
    (``<00:00:01.500>``) : notre .vtt porte alors le karaoke, ce qu'un .srt
    ne sait pas faire. Sans elles le fichier reste un VTT parfaitement banal.
    """
    segs = normalize_segments(segments, with_words=word_timings)
    out = [f"WEBVTT{newline}"]
    for s in segs:
        cue = (f"{_vtt_time(s['start'])} --> {_vtt_time(s['end'])}{newline}")
        if word_timings and s.get("words"):
            ws = s["words"]
            cue += ws[0]["w"] + "".join(
                f" <{_vtt_time(w['start'])}>{w['w']}" for w in ws[1:])
        else:
            cue += s["text"].replace("\n", newline)
        out.append(cue + newline)
    return newline.join(out)


_ASS_FORMAT_STYLE = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
    "MarginL, MarginR, MarginV, Encoding")
_ASS_FORMAT_EVENT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
    "Effect, Text")

_ALIGN_N = {("left", "bottom"): 1, ("center", "bottom"): 2, ("right", "bottom"): 3,
            ("left", "middle"): 4, ("center", "middle"): 5, ("right", "middle"): 6,
            ("left", "top"): 7, ("center", "top"): 8, ("right", "top"): 9}


def _ass_style_line(name: str, st: dict, scale: float, karaoke: bool) -> str:
    """Une ligne `Style:` du bloc [V4+ Styles].

    Karaoke : en ASS le texte demarre en SecondaryColour et bascule en
    PrimaryColour au fur et a mesure des `\\k`. Le mot ACTIF et la suite du
    texte deja "chante" prennent donc PrimaryColour. On inverse donc les deux
    couleurs selon que le karaoke est actif ou non — sinon un fichier sans
    karaoke sortirait entierement dans la couleur de surlignage.
    """
    base, active = st["color"], st["karaoke_color"]
    primary = _ass_color(active if karaoke else base)
    secondary = _ass_color(base if karaoke else active)
    box = st["back_mode"] in ("wrap", "band") and st["back_opacity"] > 0
    border_style = 3 if box else 1
    # BorderStyle 3 : Outline devient le rembourrage de la boite. Sans
    # rembourrage la boite colle aux jambages, ce qui est illisible.
    outline = st["outline"] * scale
    if box and outline < 1.0:
        outline = max(6.0 * scale, 1.0)
    # PIEGE libass/VSFilter : en BorderStyle 3, la boite est remplie avec
    # OutlineColour, PAS avec BackColour. Poser le fond dans BackColour donne
    # une boite de la couleur du CONTOUR — noire par defaut — sans la moindre
    # erreur de ffmpeg. BackColour ne sert qu'a l'ombre, dans les deux modes.
    outline_colour = _ass_color(st["back_color"], st["back_opacity"]) if box \
        else _ass_color(st["outline_color"])
    back_colour = _ass_color(st["shadow_color"],
                             0.55 if st["shadow"] > 0 else 0.0)
    # Le corps ecrit dans le fichier N'EST PAS l'em voulu : libass dessine
    # em = Fontsize / hauteur_de_ligne(fonte) (convention VSFilter, mesuree
    # a l'image). On pre-multiplie pour que le px regle au panneau soit le px
    # grave. Contour, ombre et interlettrage sont, eux, en pixels de script :
    # ils ne passent PAS par ce facteur.
    lh = font_line_height(st["font"])
    fields = [
        name,
        st["font"],
        f"{st['size'] * scale * lh:g}",
        primary, secondary,
        outline_colour,
        back_colour,
        "-1" if int(st["bold"]) else "0",
        "-1" if int(st["italic"]) else "0",
        "-1" if int(st["underline"]) else "0",
        "0",                                  # StrikeOut
        "100", "100",                         # ScaleX, ScaleY
        f"{st['spacing'] * scale:g}",
        "0",                                  # Angle
        str(border_style),
        f"{outline:g}",
        f"{st['shadow'] * scale:g}",
        str(_ALIGN_N[(st["align"], st["valign"])]),
        str(int(round(st["margin_h"] * scale))),
        str(int(round(st["margin_h"] * scale))),
        str(int(round(st["margin_v"] * scale))),
        "1",                                  # Encoding (1 = default)
    ]
    return "Style: " + ",".join(fields)


#: Animations d'entree REELLEMENT gravables, verifiees a l'image (pixels
#: mesures sur une gravure ffmpeg, pas deduites de la doc ASS) :
#:   * `fondu`  -> `\fad(in,0)`  : a 50 ms le texte est a 30 % de sa luminance,
#:                 a 1,5 s il est plein ;
#:   * `pop`    -> `\fscx/\fscy` + `\t` : le bloc est mesure plus petit et plus
#:                 bas au debut, a sa taille ensuite.
#: Duree en millisecondes. Tout le reste (montee, machine a ecrire) n'a pas
#: d'equivalent honnete et a ete RETIRE du panneau plutot que promis.
ANIM_MS = 220
_ANIMS = {
    "fondu": lambda ms: "{\\fad(%d,0)}" % ms,
    "pop": lambda ms: ("{\\fscx70\\fscy70\\t(0,%d,\\fscx100\\fscy100)}" % ms),
}
ANIMS = ("none", "fondu", "pop")


def anim_tag(anim: str | None, ms: int = ANIM_MS) -> str:
    """Prefixe ASS de l'animation d'entree, ou chaine vide."""
    f = _ANIMS.get(str(anim or "none"))
    return f(max(40, min(2000, int(ms)))) if f else ""


def to_ass(segments, style=None, *, canvas: tuple[int, int] = (1080, 1920),
           karaoke: bool = True, karaoke_mode: str = "bond",
           anim: str = "none", anim_ms: int = ANIM_MS,
           newline: str = "\n") -> str:
    """Fichier ASS complet — style REEL + karaoke natif.

    `style` : nom de preset, dict partiel, ou None. Un segment peut porter son
    propre `style` : chaque style distinct produit sa ligne [V4+ Styles], et
    l'evenement la reference par son nom.

    `canvas` : (largeur, hauteur) du rendu. PlayResX/Y sont poses dessus et
    toutes les mesures du style (corps, contour, ombre, marges, interlettrage),
    exprimees a REF_HEIGHT=1080, sont mises a l'echelle par hauteur/1080 : le
    meme preset rend pareil en 1080p et en 1920 de haut (9:16).
    """
    W, H = int(canvas[0] or 1080), int(canvas[1] or 1920)
    scale = (H / float(REF_HEIGHT)) if H > 0 else 1.0
    segs = normalize_segments(segments)

    default = resolve_style(style)
    styles: dict[str, dict] = {}
    names: list[str] = []

    def _register(st: dict) -> str:
        key = repr(sorted((k, str(v)) for k, v in st.items() if k != "label"))
        for nm, (k2, _s) in styles.items():
            if k2 == key:
                return nm
        nm = "Dz%d" % (len(styles) + 1)
        styles[nm] = (key, st)
        names.append(nm)
        return nm

    default_name = _register(default)
    pre = anim_tag(anim, anim_ms)

    events = []
    for s in segs:
        st = resolve_style(s["style"]) if s.get("style") else default
        nm = default_name if st is default else _register(st)
        txt = (_karaoke_text(s, karaoke_mode, bool(st["uppercase"])) if karaoke
               else _ass_escape(s["text"].upper() if st["uppercase"] else s["text"]))
        events.append(
            f"Dialogue: 0,{_ass_time(s['start'])},{_ass_time(s['end'])},"
            f"{nm},,0,0,0,,{pre}{txt}")

    head = [
        "[Script Info]",
        "; Genere par DeepotusVideoGen - piste de sous-titres s1",
        "ScriptType: v4.00+",
        "WrapStyle: 2",              # 2 = aucun repli automatique : nos \N font foi
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "",
        "[V4+ Styles]",
        _ASS_FORMAT_STYLE,
    ]
    head += [_ass_style_line(nm, styles[nm][1], scale, karaoke) for nm in names]
    head += ["", "[Events]", _ASS_FORMAT_EVENT] + events + [""]
    return newline.join(head)


# ---------------------------------------------------------------------------
# Lecture : SRT / VTT
# ---------------------------------------------------------------------------

_TS = r"(?:(\d{1,3}):)?(\d{1,2}):(\d{1,2})(?:[.,](\d{1,3}))?"
_CUE_RE = re.compile(rf"^\s*{_TS}\s*-->\s*{_TS}\s*(.*)$")
_INT_RE = re.compile(r"^\s*\d+\s*$")
_VTT_TS_INLINE = re.compile(rf"<{_TS}>")


def _ts(h, m, s, frac) -> float:
    ms = (frac or "").ljust(3, "0")[:3]
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0) + int(ms or 0) / 1000.0


def _clean_source(text: str) -> list[str]:
    """BOM retire, CRLF/CR normalises, lignes conservees telles quelles."""
    s = str(text or "")
    if s.startswith("\ufeff"):
        s = s[1:]
    s = s.replace("\ufeff", "")
    return s.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _scan_cues(text: str) -> list[dict]:
    """Scanner de cues commun SRT/VTT — tolerant par construction.

    Il ne suppose ni numerotation, ni format d'heure : il repere les lignes
    portant `-->`, puis prend pour texte tout ce qui suit jusqu'a la premiere
    ligne blanche (regle commune SRT/VTT) ou jusqu'a la cue suivante.

    Deux consequences utiles, gratuitement : un identifiant de cue VTT ou un
    index SRT, toujours situes AVANT le timestamp, ne sont jamais lus comme du
    texte ; et un bloc `NOTE` / `STYLE` / `REGION`, toujours precede d'une
    ligne blanche, sort du corps de la cue precedente. Reste le cas des
    fichiers sans ligne blanche du tout : on retire alors l'index accole a la
    cue suivante.
    """
    lines = _clean_source(text)
    marks = [i for i, ln in enumerate(lines) if "-->" in ln and _CUE_RE.match(ln)]
    cues = []
    for n, i in enumerate(marks):
        m = _CUE_RE.match(lines[i])
        stop = marks[n + 1] if n + 1 < len(marks) else len(lines)
        body, j = [], i + 1
        while j < stop and lines[j].strip():
            body.append(lines[j])
            j += 1
        # fichier sans ligne blanche : l'index de la cue suivante s'est colle
        # a la fin de ce corps (il touche directement le prochain timestamp).
        if body and n + 1 < len(marks) and j == stop and _INT_RE.match(body[-1]):
            body.pop()
        cues.append({"start": _ts(m.group(1), m.group(2), m.group(3), m.group(4)),
                     "end": _ts(m.group(5), m.group(6), m.group(7), m.group(8)),
                     "raw": "\n".join(body),
                     "settings": (m.group(9) or "").strip()})
    return cues


def _vtt_words(raw: str, start: float, end: float) -> list[dict]:
    """Extrait le calage par mot des balises `<00:00:01.500>` d'un cue VTT.
    Retourne [] si le cue n'en porte pas."""
    if not _VTT_TS_INLINE.search(raw or ""):
        return []
    parts = _VTT_TS_INLINE.split(raw)
    # split avec groupes : [texte, h, m, s, frac, texte, h, m, s, frac, ...]
    words, cursor = [], start
    head = _strip_markup(parts[0])
    if head:
        words.append({"w": head, "start": cursor, "end": cursor})
    i = 1
    while i + 4 <= len(parts):
        t = _ts(parts[i], parts[i + 1], parts[i + 2], parts[i + 3])
        chunk = _strip_markup(parts[i + 4])
        if words:
            words[-1]["end"] = t
        if chunk:
            words.append({"w": chunk, "start": t, "end": t})
        i += 5
    if words:
        words[-1]["end"] = end
    # un "mot" peut en fait contenir plusieurs mots (balise posee par phrase) :
    # on re-repartit a l'interieur pour ne jamais mentir sur le calage.
    out = []
    for w in words:
        toks = _words_of(w["w"])
        if len(toks) <= 1:
            if toks:
                out.append({"w": toks[0], "start": w["start"], "end": w["end"]})
        else:
            out.extend(distribute_words(w["w"], w["start"], w["end"]))
    return out


def parse_srt(text: str, *, prefix: str = "s1") -> list[dict]:
    """Lit un SRT. Tolere : BOM, CRLF, virgule OU point decimal, heures
    omises, numerotation absente ou fantaisiste, balises `<i>`/`<b>`."""
    segs = []
    for c in _scan_cues(text):
        body = _strip_markup(c["raw"]) if _TAG_RE.search(c["raw"]) else c["raw"].strip()
        if not body:
            continue
        segs.append({"start": c["start"], "end": c["end"], "text": body})
    return normalize_segments(segs, prefix=prefix)


def parse_vtt(text: str, *, prefix: str = "s1") -> list[dict]:
    """Lit un WebVTT. En plus des tolerances du SRT : en-tete `WEBVTT`, blocs
    `NOTE`/`STYLE`/`REGION`, identifiants de cue, reglages de cue apres le
    timestamp, balises `<c.classe>`, et **calage par mot** quand le cue porte
    des balises temporelles `<00:00:01.500>`."""
    segs = []
    for c in _scan_cues(text):
        raw = c["raw"]
        words = _vtt_words(raw, c["start"], c["end"])
        body = _strip_markup(raw)
        if not body:
            continue
        seg = {"start": c["start"], "end": c["end"], "text": body}
        if words:
            seg["words"] = words
        segs.append(seg)
    return normalize_segments(segs, prefix=prefix)


def sniff_format(text: str) -> str:
    """"vtt" | "srt" | "ass" | "unknown" — d'apres l'en-tete, pas l'extension."""
    head = "\n".join(_clean_source(text)[:12]).lstrip()
    if head.upper().startswith("WEBVTT"):
        return "vtt"
    if "[Script Info]" in head or "[V4+ Styles]" in head:
        return "ass"
    if _CUE_RE.search(head) or re.search(r"\d+:\d+:\d+,\d+\s*-->", head):
        return "srt"
    return "unknown"


def parse_subtitles(text: str, *, prefix: str = "s1") -> list[dict]:
    """Lecture avec detection de format (SRT ou VTT)."""
    return (parse_vtt if sniff_format(text) == "vtt" else parse_srt)(
        text, prefix=prefix)


# ---------------------------------------------------------------------------
# Decoupe automatique — le « Chars per subtitle » de la barre
# ---------------------------------------------------------------------------

def auto_break_lines(text: str, chars_per_line: int = 42) -> list[str]:
    """Coupe `text` en lignes d'au plus `chars_per_line` caracteres.

    Deux garanties :
      * on ne coupe JAMAIS a l'interieur d'un mot (un mot plus long que la
        limite occupe sa ligne entiere, il n'est pas tronconne) ;
      * on PREFERE couper juste apres une ponctuation. Une coupe apres un
        point / ! / ? / … est presque toujours la bonne : on l'accepte des
        que la ligne garde 35 % de la largeur permise. Apres une virgule /
        ; / : / tiret cadratin, le gain est moindre : on exige 50 %. En
        dessous, la ligne serait si courte que le remede vaudrait le mal.
    """
    limit = max(4, int(chars_per_line))
    words = _words_of(text)
    if not words:
        return []
    lines: list[str] = []
    i = 0
    while i < len(words):
        # remplissage glouton
        j, ln = i, ""
        while j < len(words):
            cand = words[j] if not ln else ln + " " + words[j]
            if len(cand) > limit and ln:
                break
            ln = cand
            j += 1
        # preference ponctuation : on recule d'au plus 3 mots
        if j < len(words) and (j - i) > 1:
            best = None
            for k in range(j - 1, max(i, j - 4) - 1, -1):
                if k <= i:
                    break
                tail = words[k - 1][-1] if words[k - 1] else ""
                strong = tail in _END_PUNCT_STRONG
                if not strong and tail not in _END_PUNCT_WEAK:
                    continue
                cut = " ".join(words[i:k])
                if len(cut) < (0.35 if strong else 0.50) * limit:
                    continue
                rank = 0 if strong else 1
                if best is None or rank < best[0]:
                    best = (rank, k, cut)
                if rank == 0:
                    break
            if best:
                _, k, cut = best
                lines.append(cut)
                i = k
                continue
        lines.append(ln)
        i = j
    return lines


def auto_break(text: str, chars_per_line: int = 42,
               max_lines: int = 2) -> list[list[str]]:
    """Decoupe complete : liste de BLOCS, chaque bloc etant une liste d'au plus
    `max_lines` lignes d'au plus `chars_per_line` caracteres.

    Un bloc = un sous-titre a l'ecran. `chars_per_line * max_lines` est donc
    exactement le « Chars per subtitle » de la barre, mais exprime en deux
    reglages qui ont un sens visuel (largeur de ligne, nombre de lignes) au
    lieu d'un seul curseur opaque.
    """
    lines = auto_break_lines(text, chars_per_line)
    n = max(1, int(max_lines))
    return [lines[k:k + n] for k in range(0, len(lines), n)] if lines else []


def split_segment(seg: dict, chars_per_line: int = 42, max_lines: int = 2,
                  *, prefix: str | None = None) -> list[dict]:
    """Eclate un segment trop long en plusieurs segments, cales sur les MOTS.

    Les temps de sortie viennent des `words` du segment (donc de la
    transcription), pas d'une regle de trois sur la duree : la coupe tombe
    exactement la ou le mot commence.
    """
    segs = normalize_segments([seg])
    if not segs:
        return []
    s = segs[0]
    blocks = auto_break(s["text"], chars_per_line, max_lines)
    if len(blocks) <= 1:
        return [s]
    words = s["words"]
    base = prefix or s["id"]
    out, idx = [], 0
    for b, block in enumerate(blocks):
        n = sum(len(_words_of(ln)) for ln in block)
        chunk = words[idx:idx + n]
        idx += n
        if not chunk:
            continue
        st = chunk[0]["start"] if b else s["start"]
        en = s["end"] if idx >= len(words) else chunk[-1]["end"]
        out.append({"id": f"{base}_{b + 1}", "start": st, "end": en,
                    "text": "\n".join(block), "words": chunk,
                    **({"style": s["style"]} if s.get("style") else {})})
    return normalize_segments(out, prefix=base)


def split_segments(segments, chars_per_line: int = 42,
                   max_lines: int = 2) -> list[dict]:
    """`split_segment` sur toute la piste."""
    out = []
    for s in normalize_segments(segments):
        out.extend(split_segment(s, chars_per_line, max_lines))
    return normalize_segments(out)


# ---------------------------------------------------------------------------
# Controle qualite — ce que la barre ne fait pas
# ---------------------------------------------------------------------------

CPS_WARN = 20.0        # au-dela, la lecture decroche (norme sous-titrage ~17)
CPS_ERROR = 27.0
MIN_DURATION = 1.0     # sous 1 s, l'oeil n'a pas le temps de se poser
MAX_DURATION = 7.0     # au-dela, le sous-titre "colle" a l'ecran
MIN_GAP = 0.08         # deux images a 25 i/s

_EPS = 1e-6


def _fr(x, dec: int = 2) -> str:
    """Nombre en francais : virgule decimale, zeros de queue retires."""
    s = "%.*f" % (dec, round(float(x), dec))
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return (s or "0").replace(".", ",")


def _fr_ms(x) -> str:
    return "%d ms" % int(round(float(x) * 1000))


def _rank(i) -> str:
    """Rang AFFICHE d'un segment (le panneau numerote a partir de 1)."""
    return "n°%d" % (int(i) + 1)


def _measure_px(line: str, st: dict, scale: float) -> float | None:
    """Largeur reelle de `line` en pixels avec la VRAIE fonte, ou None si PIL
    ou le fichier de fonte manque (le controle retombe alors sur le comptage
    de caracteres)."""
    p = font_path(st.get("font"))
    if p is None:
        return None
    try:
        from PIL import ImageFont
        f = ImageFont.truetype(str(p), max(4, int(round(st["size"] * scale))))
        w = f.getlength(line)
        sp = st.get("spacing", 0.0) * scale
        if sp:
            w += sp * max(0, len(line) - 1)
        return float(w)
    except Exception:
        return None


def _styles_used(segs, default: dict) -> list[tuple[str, dict, list[int]]]:
    """Styles distincts effectivement utilises : [(nom lisible, style resolu,
    indices des segments concernes)]. Les indices servent a poser
    l'avertissement de style LA OU on peut agir, pas dans le vide."""
    out: list[tuple[str, dict, list[int]]] = []
    seen: dict[str, int] = {}
    for i, s in enumerate(segs):
        raw = s.get("style") if isinstance(s, dict) else None
        key = raw if isinstance(raw, str) else (
            (raw or {}).get("preset") if isinstance(raw, dict) else None)
        key = str(key) if key else "(defaut)"
        if key not in seen:
            seen[key] = len(out)
            out.append((key, resolve_style(raw) if raw else default, []))
        out[seen[key]][2].append(i)
    return out


# ---------------------------------------------------------------------------
# Correctifs NEGOCIES
#
# Une piste de sous-titres est un systeme sous contraintes : chaque segment est
# borne par ses voisins. Un correctif d'un clic qui repare une ligne en cassant
# la suivante est PIRE que pas de correctif — l'utilisateur ne voit meme pas
# ce qu'il vient de detruire.
#
# Regle du module, verifiee par les tests (`test_subtitle_fixes.py`) :
#   * un plan ne cree JAMAIS de chevauchement qui n'existait pas ;
#   * un plan ne REDUIT JAMAIS un ecart deja sous `min_gap` ;
#   * si aucune solution ne respecte ces deux regles, il n'y a PAS de bouton :
#     `ok=False` et `blocked` dit pourquoi, en francais.
#
# Un plan qui touche un VOISIN est autorise, a une condition : il le DIT dans
# `effect`, avant le clic. C'est la troisieme voie — la renegociation — au lieu
# du silence ou du refus.
#
# Forme d'un plan ::
#
#     {"action": "etirer"|"separer"|"decouper"|"replier"|"fusionner"|None,
#      "ok": bool,
#      "label": "Etirer a 1,35 s",          # le texte du bouton
#      "effect": "Prend 190 ms de silence apres. Aucun voisin ne bouge.",
#      "ops": [{"op": "set"|"remove"|"replace", "index": i, "id": ...}, ...],
#      "touches": [indices des VOISINS deplaces],
#      "granted": 1.35, "requested": 1.35,
#      "blocked": "..." (si ok=False),
#      "alt": {plan} | None}                # la renegociation, quand elle existe
# ---------------------------------------------------------------------------


def _plan(action, ok, label, effect, ops=None, **kw) -> dict:
    d = {"action": action, "ok": bool(ok), "label": label, "effect": effect,
         "ops": list(ops or []), "touches": [], "alt": None}
    d.update(kw)
    return d


def _blocked(action, why, **kw) -> dict:
    return _plan(action, False, "", "", blocked=why, **kw)


def _set_op(segs, i, **fields) -> dict:
    op = {"op": "set", "index": int(i), "id": segs[i].get("id")}
    op.update(fields)
    return op


def room_after(segs, i, min_gap: float = MIN_GAP, media_dur=None) -> float:
    """Silence LIBRE apres le segment `i`, en secondes (jamais negatif).

    Si l'ecart avec le suivant est deja sous `min_gap`, la place libre vaut 0 :
    c'est ce zero qui empeche un correctif de grignoter une frontiere deja
    trop serree.
    """
    if i + 1 < len(segs):
        return max(0.0, segs[i + 1]["start"] - min_gap - segs[i]["end"])
    if media_dur is None:
        return float("inf")
    return max(0.0, float(media_dur) - segs[i]["end"])


def room_before(segs, i, min_gap: float = MIN_GAP) -> float:
    """Silence LIBRE avant le segment `i` (jamais negatif)."""
    if i > 0:
        return max(0.0, segs[i]["start"] - min_gap - segs[i - 1]["end"])
    return max(0.0, segs[i]["start"])


def plan_stretch(segs, i, target_dur: float, *, min_gap: float = MIN_GAP,
                 media_dur=None, why: str = "") -> dict:
    """Plan d'ETIREMENT du segment `i` jusqu'a `target_dur` secondes.

    Trois issues, aucune ne ment :

    1. le silence suffit -> on le prend, personne ne bouge ;
    2. il ne suffit qu'en partie -> le bouton annonce la duree REELLEMENT
       atteinte, et `alt` propose de decaler les suivants en disant combien ;
    3. rien n'est possible -> pas de bouton, `blocked` dit pourquoi.
    """
    s = segs[i]
    dur = s["end"] - s["start"]
    target = max(dur, float(target_dur))
    need = target - dur
    if need <= _EPS:
        return _blocked("etirer", "Le segment dure déjà assez longtemps.")

    after = room_after(segs, i, min_gap, media_dur)
    before = room_before(segs, i, min_gap)
    take_after = min(need, after)
    take_before = min(need - take_after, before)
    granted = dur + take_after + take_before
    new_start = round(s["start"] - take_before, 4)
    new_end = round(s["end"] + take_after, 4)

    # combien coute la renegociation : decaler les suivants du reste
    deficit = round(max(0.0, target - granted), 4)
    alt = None
    if deficit > 0.001 and i + 1 < len(segs):
        last_end = segs[-1]["end"] + deficit
        if media_dur is not None and last_end > float(media_dur) + _EPS:
            alt = _blocked(
                "etirer",
                "Décaler les suivants sortirait le dernier sous-titre de la "
                "vidéo (%s de trop)." % _fr_ms(last_end - float(media_dur)))
        else:
            n = len(segs) - (i + 1)
            ops = [_set_op(segs, i, start=new_start,
                           end=round(new_end + deficit, 4))]
            for j in range(i + 1, len(segs)):
                ops.append(_set_op(segs, j,
                                   start=round(segs[j]["start"] + deficit, 4),
                                   end=round(segs[j]["end"] + deficit, 4)))
            alt = _plan(
                "etirer", True,
                "Étirer à %s s en décalant la suite" % _fr(target),
                "Décale les %d sous-titres suivants de %s. Leur texte ne "
                "bougera plus avec la voix — à ne faire que si le montage "
                "suit." % (n, _fr_ms(deficit)),
                ops, touches=list(range(i + 1, len(segs))),
                granted=round(target, 3), requested=round(target, 3))

    if granted <= dur + _EPS:
        why_full = ("Aucun silence disponible : %s%s. Raccourcissez le texte, "
                    "ou fusionnez avec le voisin."
                    % (_gap_reason(segs, i, min_gap, media_dur),
                       (" " + why) if why else ""))
        p = _blocked("etirer", why_full)
        p["alt"] = alt
        return p

    got = round(granted, 3)
    full = got >= target - 0.005
    if full:
        eff = _stretch_effect(take_before, take_after)
    else:
        eff = ("%s Il faudrait %s s : le voisin ne laisse pas plus. %s"
               % (_stretch_effect(take_before, take_after), _fr(target),
                  "Le problème sera réduit, pas effacé."))
    p = _plan("etirer", True, "Étirer à %s s" % _fr(got), eff,
              [_set_op(segs, i, start=new_start, end=new_end)],
              granted=got, requested=round(target, 3))
    p["alt"] = alt
    return p


def _stretch_effect(before: float, after: float) -> str:
    bits = []
    if after > 0.001:
        bits.append("prend %s de silence après" % _fr_ms(after))
    if before > 0.001:
        bits.append("%s de silence avant" % _fr_ms(before))
    if not bits:
        return "Aucun voisin ne bouge."
    return "Le segment " + " et ".join(bits) + ". Aucun voisin ne bouge."


def _gap_reason(segs, i, min_gap, media_dur) -> str:
    if i + 1 < len(segs):
        g = segs[i + 1]["start"] - segs[i]["end"]
        return ("le %s commence %s après la fin de celui-ci (plancher %s)"
                % (_rank(i + 1), _fr_ms(max(0.0, g)), _fr_ms(min_gap)))
    if media_dur is not None:
        return "le segment finit déjà avec la vidéo"
    return "le voisin est collé"


def plan_boundary(segs, i, *, min_gap: float = MIN_GAP,
                  min_duration: float = MIN_DURATION) -> dict:
    """Plan de RENEGOCIATION de la frontiere entre `i-1` et `i`.

    Le defaut appartient a DEUX segments : le corriger sur un seul (raccourcir
    le precedent) est arbitraire et souvent impossible. On repartit donc
    l'effort entre les deux, proportionnellement a ce que chacun peut ceder
    sans passer sous `min_duration`, et on dit exactement ce que chacun perd.
    """
    if i < 1 or i >= len(segs):
        return _blocked("separer", "Pas de voisin avant ce segment.")
    prev, cur = segs[i - 1], segs[i]
    gap = cur["start"] - prev["end"]
    need = min_gap - gap
    if need <= _EPS:
        return _blocked("separer", "La frontière est déjà assez large.")

    dp = prev["end"] - prev["start"]
    dc = cur["end"] - cur["start"]
    give_p = max(0.0, dp - min_duration)
    give_c = max(0.0, dc - min_duration)
    total = give_p + give_c

    if total >= need - _EPS:
        take_p = need * (give_p / total) if total > 0 else 0.0
        take_c = need - take_p
        if take_c > give_c:
            take_c, take_p = give_c, need - give_c
        ops = [_set_op(segs, i - 1, end=round(prev["end"] - take_p, 4)),
               _set_op(segs, i, start=round(cur["start"] + take_c, 4))]
        eff = ("Le %s perd %s à la fin, le %s %s au début. Écart final %s, "
               "et les deux restent au-dessus de %s s."
               % (_rank(i - 1), _fr_ms(take_p), _rank(i), _fr_ms(take_c),
                  _fr_ms(min_gap), _fr(min_duration)))
        return _plan("separer", True,
                     "Séparer de %s" % _fr_ms(min_gap), eff, ops,
                     touches=[i - 1], granted=round(min_gap, 3),
                     requested=round(min_gap, 3))

    # pas assez de marge : on ne descend PAS sous le plancher en douce.
    merged_dur = cur["end"] - prev["start"]
    fus = None
    if merged_dur <= MAX_DURATION + _EPS:
        txt = (prev["text"] + " " + cur["text"]).strip()
        fus = _plan(
            "fusionner", True, "Fusionner les deux",
            "Le %s et le %s deviennent un seul sous-titre de %s s. "
            "Le texte est mis bout à bout, le calage par mot est refait."
            % (_rank(i - 1), _rank(i), _fr(merged_dur)),
            [_set_op(segs, i - 1, end=round(cur["end"], 4), text=txt,
                     words=None),
             {"op": "remove", "index": i, "id": cur.get("id")}],
            touches=[i], granted=round(merged_dur, 3))
    p = _blocked(
        "separer",
        "Impossible sans passer sous %s s : le %s dure %s s, le %s %s s, et il "
        "manque %s. Fusionnez-les, ou raccourcissez un texte."
        % (_fr(min_duration), _rank(i - 1), _fr(dp), _rank(i), _fr(dc),
           _fr_ms(need - total)))
    p["alt"] = fus
    return p


def plan_split(segs, i, st: dict, *, max_lines: int = 2,
               min_gap: float = MIN_GAP) -> dict:
    """Plan de DECOUPE d'un segment en plusieurs, cale sur les mots.

    Les mots se touchent : une coupe brute produirait deux sous-titres colles,
    donc un `intervalle_court` tout neuf — le correctif fabriquerait le defaut
    suivant. On ouvre donc `min_gap` a chaque coupe, aux depens de la fin du
    morceau de gauche, et on le dit.
    """
    parts = split_segment(segs[i], st["chars_per_line"], max_lines)
    if len(parts) < 2:
        return _blocked("decouper",
                        "Le texte tient en un seul bloc de %d caractères : "
                        "rien à découper." % st["chars_per_line"])
    for k in range(len(parts) - 1):
        a, b = parts[k], parts[k + 1]
        if b["start"] - a["end"] < min_gap - _EPS:
            a["end"] = round(max(a["start"] + 0.12, b["start"] - min_gap), 4)
            a["words"] = [w for w in (a.get("words") or [])]
            for w in a["words"]:
                w["end"] = min(w["end"], a["end"])
                w["start"] = min(w["start"], a["end"])
    durs = " + ".join(_fr(p["end"] - p["start"]) + " s" for p in parts)
    return _plan(
        "decouper", True, "Découper en %d sous-titres" % len(parts),
        "Le segment devient %d sous-titres (%s), coupés sur les mots avec %s "
        "de respiration entre eux. Les voisins ne bougent pas."
        % (len(parts), durs, _fr_ms(min_gap)),
        [{"op": "replace", "index": int(i), "id": segs[i].get("id"),
          "with": [{"start": p["start"], "end": p["end"], "text": p["text"],
                    "words": p.get("words")} for p in parts]}],
        granted=len(parts))


def plan_rewrap(segs, i, st: dict, *, max_lines: int = 2,
                chars: int | None = None) -> dict:
    """Plan de REPLI du texte (memes bornes) ou, s'il ne tient pas, de DECOUPE.

    Le bouton dit lequel des deux il va faire, avec le resultat : « Replier en
    2 lignes » n'a pas les memes consequences que « Decouper en 3 sous-titres »,
    et l'utilisateur doit le savoir AVANT de cliquer.
    """
    cpl = int(chars or st["chars_per_line"])
    flat = segs[i]["text"].replace("\n", " ")
    lines = auto_break_lines(flat, cpl)
    if len(lines) <= max_lines:
        new = "\n".join(lines)
        if new == segs[i]["text"]:
            return _blocked("replier",
                            "Le texte est déjà replié au mieux pour %d "
                            "caractères par ligne." % cpl)
        return _plan(
            "replier", True, "Replier en %d lignes" % len(lines),
            "Le texte est replié à %d caractères par ligne (%s). Le début, la "
            "fin et le calage par mot ne bougent pas."
            % (cpl, " / ".join("%d" % len(x) for x in lines)),
            [_set_op(segs, i, text=new)], granted=len(lines))
    p = plan_split(segs, i, dict(st, chars_per_line=cpl), max_lines=max_lines)
    if p["ok"]:
        p["effect"] = ("Le texte fait %d lignes à %d caractères : il ne tient "
                       "pas en %d. %s" % (len(lines), cpl, max_lines,
                                          p["effect"]))
    return p


def apply_plan(segments, plan: dict, *, prefix: str = "s1") -> list[dict]:
    """Applique un plan et rend la piste resultante (normalisee, triee).

    Les `ops` d'un plan sont des DONNEES (`{op, index, id, start, end, text}`),
    pas du code : le panneau les applique tel quel, par `id`, avec les memes
    trois verbes (`set` / `remove` / `replace`). C'est cette fonction qui sert
    de reference aux tests d'invariant — ce qui est verifie ici est
    exactement ce que le bouton produira.
    """
    # keep_empty=True : MEME indexation que `check_quality`, sinon un segment
    # encore vide decalerait les indices du plan et le correctif tomberait sur
    # le voisin.
    segs = [dict(s) for s in normalize_segments(segments, sort=False,
                                                keep_empty=True)]
    if not plan or not plan.get("ok"):
        return normalize_segments(segs, prefix=prefix, keep_empty=True)
    drop: set[int] = set()
    inject: dict[int, list[dict]] = {}
    for op in plan.get("ops") or []:
        i = int(op.get("index", -1))
        if i < 0 or i >= len(segs):
            continue
        kind = str(op.get("op") or "set")
        if kind == "remove":
            drop.add(i)
        elif kind == "replace":
            inject[i] = [dict(x) for x in (op.get("with") or [])]
            drop.add(i)
        else:
            s = segs[i]
            for k in ("start", "end", "text"):
                if op.get(k) is not None:
                    s[k] = op[k]
            if "words" in op:
                if op["words"] is None:
                    s["words"] = distribute_words(s["text"], s["start"], s["end"])
                else:
                    s["words"] = op["words"]
            elif op.get("start") is not None or op.get("end") is not None:
                # les bornes ont bouge : le calage par mot herite d'elles
                # devient faux. On le refait plutot que de laisser deriver.
                s["words"] = distribute_words(s["text"], s["start"], s["end"])
    out = []
    for i, s in enumerate(segs):
        if i in inject:
            out.extend(inject[i])
        if i not in drop:
            out.append(s)
    return normalize_segments(out, prefix=prefix, keep_empty=True)


def _w(code, severity, seg, index, message, *, value=None, limit=None,
       about=None, plan=None, fix=None):
    """Un avertissement.

    `index` est le segment sur la carte DUQUEL l'avertissement s'affiche, et
    c'est TOUJOURS celui dont la mesure a declenche la regle. `about` liste
    tous les segments concernes (deux, pour une frontiere) : le message les
    nomme par leur rang, pour qu'aucun lecteur n'ait a deviner.
    """
    d = {"code": code, "severity": severity, "index": index,
         "seg_id": seg.get("id") if isinstance(seg, dict) else None,
         "message": message,
         "about": list(about) if about is not None else (
             [] if index is None else [index])}
    if value is not None:
        d["value"] = round(float(value), 3) if isinstance(value, (int, float)) else value
    if limit is not None:
        d["limit"] = limit
    if plan is not None:
        d["plan"] = plan
    if fix:
        d["fix"] = fix
    return d


def check_quality(segments, style=None, canvas: tuple[int, int] | None = None,
                  *, cps_warn: float = CPS_WARN, cps_error: float = CPS_ERROR,
                  min_duration: float = MIN_DURATION,
                  max_duration: float = MAX_DURATION,
                  max_lines: int = 2, min_gap: float = MIN_GAP,
                  karaoke: bool = True, media_dur: float | None = None) -> list[dict]:
    """Avertissements exploitables sur une piste. PAS de note globale.

    Codes emis (severite "erreur" ou "avertissement"), avec leur ANCRAGE —
    le segment sur la carte duquel l'avertissement s'affiche :

    ==========================  ===========================================
    code                        ancre sur
    ==========================  ===========================================
    ``texte_vide``              le segment vide
    ``duree_nulle``             le segment (end <= start)
    ``trop_court``              le segment trop bref
    ``trop_long``               le segment trop long
    ``debit_eleve``             le segment trop dense
    ``debit_illisible``         le segment trop dense
    ``chevauchement``           le segment QUI COMMENCE TROP TOT (le second)
    ``intervalle_court``        le segment QUI COMMENCE TROP TOT (le second)
    ``ligne_trop_large``        le segment dont une ligne deborde
    ``trop_de_lignes``          le segment
    ``mots_incoherents``        le segment
    ``fond_translucide_karaoke`` aucun (regle de STYLE, index None)
    ==========================  ===========================================

    Les deux regles de FRONTIERE ont un pair : leur message nomme les deux
    segments par leur rang affiche, et `about` les liste. C'est ce qui rend
    l'ancrage verifiable — et un test le verrouille pour CHAQUE code
    (`test_subtitle_fixes.py::test_ancrage_*`).

    Chaque entree porte `plan` : un correctif NEGOCIE avec les voisins, avec
    son libelle et l'annonce de ses consequences (cf. `plan_stretch`). Un plan
    impossible n'a pas de bouton : `plan["ok"]` est faux et `plan["blocked"]`
    dit pourquoi.
    """
    # sort=False : un desordre chronologique doit se voir, pas se ranger tout
    # seul. clamp_words=False : un calage par mot hors bornes doit se voir
    # aussi, la normalisation le reparerait en silence. keep_empty=True :
    # l'INDEX renvoye doit designer la meme carte que celle du panneau — un
    # segment vide ecarte ici decalerait tous les avertissements suivants.
    segs = normalize_segments(segments, sort=False, clamp_words=False,
                              keep_empty=True)
    default = resolve_style(style)
    W, H = canvas if canvas else (None, None)
    scale = (H / float(REF_HEIGHT)) if H else 1.0
    out: list[dict] = []

    # Avertissements de STYLE : emis une fois par style utilise, pas par
    # segment (index None) — sinon une piste de 200 lignes noie l'editeur.
    # `segments` porte les segments concernes : le panneau peut les marquer.
    for key, st, idxs in _styles_used(segs, default):
        if karaoke and _box_seams(st):
            out.append({"code": "fond_translucide_karaoke",
                        "severity": "avertissement", "index": None,
                        "seg_id": None, "style": key, "about": list(idxs),
                        "message": _ASS_UNSUPPORTED["back_opacity:karaoke"],
                        "value": st["back_opacity"], "limit": 1.0,
                        "fix": {"champ": "back_opacity", "valeur": 1.0}})

    for i, s in enumerate(segs):
        st = resolve_style(s["style"]) if s.get("style") else default
        dur = s["end"] - s["start"]
        text = s["text"]
        flat = text.replace("\n", " ")

        # La FRONTIERE d'abord : elle ne depend que des bornes, et un segment
        # encore vide ne doit pas masquer le chevauchement qu'il cause.
        if i:
            prev = segs[i - 1]
            gap = s["start"] - prev["end"]
            if gap < -1e-6:
                out.append(_w("chevauchement", "erreur", s, i,
                              "Commence %s AVANT la fin du %s : les deux "
                              "s'afficheront ensemble."
                              % (_fr_ms(-gap), _rank(i - 1)),
                              value=-gap, about=[i - 1, i],
                              plan=plan_boundary(segs, i, min_gap=min_gap,
                                                 min_duration=min_duration)))
            elif gap < min_gap:
                out.append(_w("intervalle_court", "avertissement", s, i,
                              "Commence %s après la fin du %s : sous %s le "
                              "changement se verra comme un clignotement."
                              % (_fr_ms(gap), _rank(i - 1), _fr_ms(min_gap)),
                              value=gap, limit=min_gap, about=[i - 1, i],
                              plan=plan_boundary(segs, i, min_gap=min_gap,
                                                 min_duration=min_duration)))

        if not flat.strip():
            out.append(_w("texte_vide", "erreur", s, i,
                          "Segment sans texte : rien ne s'affichera, et il "
                          "sortira de l'export."))
            continue
        if dur <= 0:
            out.append(_w("duree_nulle", "erreur", s, i,
                          "Le segment ne dure rien (fin <= début).",
                          value=dur,
                          plan=plan_stretch(segs, i, min_duration,
                                            min_gap=min_gap,
                                            media_dur=media_dur)))
        else:
            if dur < min_duration - 1e-4:
                out.append(_w("trop_court", "avertissement", s, i,
                              "Segment de %s s : sous %s s l'œil n'a pas le "
                              "temps de se poser."
                              % (_fr(dur), _fr(min_duration)),
                              value=dur, limit=min_duration,
                              plan=plan_stretch(segs, i, min_duration,
                                                min_gap=min_gap,
                                                media_dur=media_dur)))
            if dur > max_duration + 1e-4:
                out.append(_w("trop_long", "avertissement", s, i,
                              "Segment de %s s : au-delà de %s s il faut le "
                              "couper en deux."
                              % (_fr(dur), _fr(max_duration)),
                              value=dur, limit=max_duration,
                              plan=plan_split(segs, i, st, max_lines=max_lines)))
            cps = len(flat) / dur
            if cps > cps_warn + 1e-6:
                need = len(flat) / cps_warn
                plan = plan_stretch(segs, i, need, min_gap=min_gap,
                                    media_dur=media_dur)
                if not plan["ok"] and not (plan.get("alt") or {}).get("ok"):
                    # pas de place : la seule issue est de raccourcir. On le
                    # dit au lieu d'agiter un bouton qui ne changerait rien.
                    plan = plan_split(segs, i, st, max_lines=max_lines) \
                        if len(flat) > st["chars_per_line"] else plan
                if cps > cps_error + 1e-6:
                    out.append(_w("debit_illisible", "erreur", s, i,
                                  "%s caractères/seconde : illisible."
                                  % _fr(cps, 1), value=cps, limit=cps_error,
                                  plan=plan))
                else:
                    out.append(_w("debit_eleve", "avertissement", s, i,
                                  "%s caractères/seconde : au-delà de %s, la "
                                  "lecture décroche."
                                  % (_fr(cps, 1), _fr(cps_warn)),
                                  value=cps, limit=cps_warn, plan=plan))

        lines = text.split("\n")
        if len(lines) > max_lines:
            out.append(_w("trop_de_lignes", "avertissement", s, i,
                          "%d lignes affichées (maximum %d)."
                          % (len(lines), max_lines),
                          value=len(lines), limit=max_lines,
                          plan=plan_rewrap(segs, i, st, max_lines=max_lines)))
        usable_px = (W - 2 * st["margin_h"] * scale) if W else None
        for ln in lines:
            px = _measure_px(ln, st, scale) if usable_px else None
            if px is not None and usable_px and px > usable_px:
                fit = max(8, int(len(ln) * usable_px / px))
                out.append(_w("ligne_trop_large", "avertissement", s, i,
                              "Ligne de %d px pour %d px utiles en %s %d : "
                              "elle dépassera du cadre."
                              % (round(px), round(usable_px), st["font"],
                                 round(st["size"] * scale)),
                              value=px, limit=round(usable_px, 1),
                              plan=plan_rewrap(segs, i, st,
                                               max_lines=max_lines,
                                               chars=fit)))
                break
            if px is None and len(ln) > st["chars_per_line"]:
                out.append(_w("ligne_trop_large", "avertissement", s, i,
                              "Ligne de %d caractères pour %d conseillés."
                              % (len(ln), st["chars_per_line"]),
                              value=len(ln), limit=st["chars_per_line"],
                              plan=plan_rewrap(segs, i, st,
                                               max_lines=max_lines)))
                break

        ws = s.get("words") or []
        bad = [w for w in ws
               if w["start"] < s["start"] - 1e-6 or w["end"] > s["end"] + 1e-6]
        if bad:
            out.append(_w("mots_incoherents", "erreur", s, i,
                          "%d mot(s) calés hors des bornes du segment — le "
                          "karaoké sortira faux." % len(bad),
                          value=len(bad),
                          plan=_plan("recaler", True, "Recaler les mots",
                                     "Les timings par mot sont refaits dans "
                                     "les bornes du segment. Le texte, le "
                                     "début et la fin ne bougent pas.",
                                     [_set_op(segs, i, words=None)])))
    return out


def autofix(segments, style=None, *, min_duration: float = MIN_DURATION,
            min_gap: float = MIN_GAP, max_duration: float = MAX_DURATION,
            split_long: bool = False) -> list[dict]:
    """Applique les correctifs TEMPORELS : chevauchements resorbes, segments
    trop courts allonges tant que la place existe, ordre chronologique retabli.
    Ne touche jamais au TEXTE (sauf `split_long=True`, qui recoupe les segments
    au-dela de `max_duration` avec `split_segment`).

    Le calage par mot est recalcule quand les bornes bougent, pour que le
    karaoke reste exact.
    """
    segs = normalize_segments(segments)
    for i, s in enumerate(segs):
        was = (s["start"], s["end"])
        if i:
            p = segs[i - 1]
            if s["start"] < p["end"]:
                s["start"] = round(p["end"], 4)
        if s["end"] - s["start"] < min_duration:
            room = (segs[i + 1]["start"] - min_gap) if i + 1 < len(segs) else None
            target = s["start"] + min_duration
            s["end"] = round(target if room is None else min(target, max(s["start"], room)), 4)
        if s["end"] <= s["start"]:
            s["end"] = round(s["start"] + 0.04, 4)   # une image a 25 i/s
        if (s["start"], s["end"]) != was:
            # les bornes ont bouge : le calage par mot herite d'elles devient
            # faux, on le refait plutot que de laisser le karaoke deriver.
            s["words"] = distribute_words(s["text"], s["start"], s["end"])
    if split_long:
        st = resolve_style(style)
        out = []
        for s in segs:
            if s["end"] - s["start"] > max_duration:
                out.extend(split_segment(s, st["chars_per_line"], 2))
            else:
                out.append(s)
        segs = out
    return normalize_segments(segs)


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------

def _ff_escape_path(p) -> str:
    """Echappement d'un chemin Windows pour un argument de filtergraph ffmpeg.

    Piege classique : `C:\\x\\y.ass` casse le filtergraph a deux endroits — le
    `:` separe les options du filtre, et `\\` est un echappement. La forme qui
    passe est `C\\:/x/y.ass` entre apostrophes.
    """
    s = str(p).replace("\\", "/")
    return s.replace("'", r"\'").replace(":", r"\:")


def subtitles_filter(ass_path, fontsdir=None) -> str:
    """Argument `-vf` grave-sous-titres, chemins echappes.

    `fontsdir` par defaut = les fontes EMBARQUEES : sans lui, libass cherche
    dans les fontes systeme et retombe silencieusement sur autre chose quand
    la famille du preset n'y est pas installee (Anton, Bebas Neue... ne sont
    pas des fontes Windows).
    """
    d = ass_fontsdir() if fontsdir is None else fontsdir
    f = f"subtitles='{_ff_escape_path(ass_path)}'"
    if d:
        f += f":fontsdir='{_ff_escape_path(d)}'"
    return f
