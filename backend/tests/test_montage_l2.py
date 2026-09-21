# -*- coding: utf-8 -*-
"""L2 — TRANSITIONS (D-20), TITRES (D-21), FONDUS EN DIRECT (D-12) cote
backend. En-tete recopie de test_montage_projets.py (env, check, J) : dossier
de donnees NEUF par execution, TestClient sans port ouvert, toute reponse
passee par `J()` et tout acces un `.get` — un banc qui meurt sur un `.json()`
nu ne dit pas quelles assertions manquent.
Run : & $PY tests/test_montage_l2.py   (depuis backend/)

[1] D-20 LE CATALOGUE DES TRANSITIONS. `_XFADE` (montage_service) porte deja
neuf cles historiques (nom libre -> (nom xfade, duree imposee|None)) lues par
`_build_montage_command`. L'ffmpeg livre (8.1.1 essentials, `-h filter=xfade`)
accepte 58 transitions (indices 0..57) ; parmi les neuf cles historiques,
trois (fade, dissolve, fadeblack) SONT deja des noms xfade a part entiere —
`flash` en revanche est un ALIAS dont la VALEUR est `fadewhite`, pas une cle
xfade elle-meme. Ce lot ajoute les 58 comme cles a part entiere (chacune sa propre cle),
les range en six familles nommees pour le selecteur client, leur donne un
libelle francais, et marque celles jouables EN DIRECT par le lecteur vivant
(D-12 : un voile noir/blanc ou une baisse d'opacite en CSS — tout le reste
n'est visible qu'apres Preview). GET /api/montage/transitions sert ce
catalogue : le client n'en a AUCUNE copie, meme precedent que GET /effects et
GET /media-rules.

L'ETAT VIDE DE CE BANC : avant l'implementation, `MS._XFADE_FAMILIES` et
`MS._XFADE_LABELS` n'existent pas du tout (AttributeError sur un acces nu) —
`A(nom, defaut)` (ci-dessous) les lit par `getattr` pour que cette absence
FASSE ROUGIR les assertions au lieu de TUER le banc avant qu'il ait fini de
parler (meme raison que `J()` sur les reponses HTTP). La route elle-meme est
absente (404) -> `J()` rend `{}`, donc `d20_la_route_rend_les_familles_et_le_
direct` rougit aussi. Regle des assertions negatives : la negation de cette
section (« le direct ne couvre QUE les fondus simples ») est precedee d'un
temoin positif (`r.status_code == 200` d'abord, jamais une negation nue).

[2] D-21 `titles.py`. Un clip titre est un clip SANS `src` sur la piste `t1` ;
`titles.py` le traduit en ASS (huit gabarits, charte, animations `\\fad` /
`\\move` / `\\t`) et sait en graver un APERCU au format PNG avec l'ffmpeg
livre. Le banc ne se contente pas de relire le texte du `.ass` : il MESURE A
L'IMAGE, avec Pillow, que chaque gabarit pose bien son texte dans la bande du
cadre qu'il annonce — le tiers inferieur en bas, le plein cadre au centre, la
legende au ras du bord, le hashtag en haut, le cta juste au-dessus du bas.
C'est la seule assertion qui demasque une inversion d'ancrage `\\an` : le
fichier ASS resterait parfaitement « valide » avec un `\\an7` a la place du
`\\an1`.

Ce que la section mesure en plus du placement : que le corps ecrit dans la
ligne `Style:` est bien PRE-MULTIPLIE par `font_line_height` (libass divise
par ce facteur, sinon un Bungee a 72 serait dessine a 28 px), que le
sous-texte ne se grave pas PAR-DESSUS un titre replie sur plusieurs lignes,
que l'apercu d'un clip pose a 30 s n'est pas une image vide mise en cache,
que les `.ass` d'apercu ne fuient pas dans le dossier des sous-titres du
montage, et qu'une table de six entrees HOSTILES (`None`, une chaine, un
`title` qui n'est pas un dict, une taille en toutes lettres, un `start` NaN,
un `end` en chaine) ne fait jamais LEVER `title_spec`.

L'ETAT VIDE DE LA SECTION [2] : avant l'implementation le module
`app.services.titles` n'existe pas du tout — l'import est donc protege et
`TI` vaut alors un objet vide dont tout attribut manque, ce qui fait ROUGIR
chaque check au lieu de tuer le banc a l'import (meme raison que `A()` en
[1]). Les lectures d'image et de fichier sont toutes gardees : `_im()` rend
None si le PNG n'a pas ete produit, `clairs(None, ...)` rend -1 (donc jamais
> 150), `_txt()` rend "" si le `.ass` n'existe pas. Les negations de la
section (« le haut ne porte rien », « sans texte pas de titre », « pas de
`\\pos` quand il y a un `\\move` ») sont toutes precedees, dans la MEME
expression, du temoin positif qui etablit que la mesure a eu lieu.
"""
import json, os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl2_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON, ou {} — le banc doit ROUGIR, pas mourir sur un .json() nu."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

print("\n[1] D-20 le catalogue des transitions est servi par le backend")
from app.services import montage_service as MS


def A(nom, defaut):
    """`getattr` module — un attribut ABSENT (avant l'implementation) doit
    faire ROUGIR les checks qui le lisent, jamais TUER le banc sur un
    AttributeError nu."""
    return getattr(MS, nom, defaut)


XFADE = A("_XFADE", {})
FAMILIES = A("_XFADE_FAMILIES", {})
LABELS = A("_XFADE_LABELS", {})
LIVE = A("_XFADE_LIVE", ())

XF58 = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown "
        "circlecrop rectcrop distance fadeblack fadewhite radial smoothleft smoothright "
        "smoothup smoothdown circleopen circleclose vertopen vertclose horzopen horzclose "
        "dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice vuslice vdslice "
        "hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast "
        "fadeslow hlwind hrwind vuwind vdwind coverleft coverright coverup coverdown "
        "revealleft revealright revealup revealdown").split()
check("d20_les_58_xfade_sont_des_cles_de_la_table",
      all(n in XFADE and XFADE[n][0] == n for n in XF58),
      [n for n in XF58 if n not in XFADE][:5])
check("d20_les_neuf_cles_historiques_sont_gardees_telles_quelles",
      XFADE.get("cut") == ("fade", 0.04) and XFADE.get("glitch") == ("pixelize", None)
      and XFADE.get("slide") == ("slideleft", None) and XFADE.get("flash") == ("fadewhite", None)
      and XFADE.get("crossfade") == ("fade", None))
check("d20_chaque_xfade_a_une_famille_et_une_seule",
      sorted(n for f in FAMILIES.values() for n in f.get("noms", [])) == sorted(XF58),
      len([n for f in FAMILIES.values() for n in f.get("noms", [])]))
check("d20_six_familles_nommees",
      list(FAMILIES) == ["fondus", "glissements", "volets", "formes", "zooms", "pixels"])
r = c.get("/api/montage/transitions"); d = J(r)
check("d20_la_route_rend_les_familles_et_le_direct",
      r.status_code == 200 and isinstance(d.get("familles"), list) and len(d["familles"]) == 6
      and sum(len(f.get("items", [])) for f in d["familles"]) == 58
      and all(set(i) >= {"id", "label", "live"} for f in d["familles"] for i in f["items"]),
      str(d)[:200])
# Un libelle FRANCAIS, pas seulement une cle presente : chaque `label` de la
# REPONSE doit differer de son `id` — sauf `distance`, dont le libelle EST le
# nom (aucune traduction plus parlante). `distance` verifie explicitement
# l'egalite plutot que d'etre exclu en silence : une famille qui livrerait un
# item sans le distinguer de `distance` doit quand meme rougir.
_items = [i for f in d.get("familles", []) for i in f.get("items", [])]
check("d20_chaque_libelle_est_ecrit_en_francais_non_vide",
      r.status_code == 200 and len(_items) == 58
      and all(isinstance(i.get("label"), str) and i["label"] for i in _items)
      and all(i["label"] != i["id"] for i in _items if i["id"] != "distance")
      and next((i["label"] for i in _items if i["id"] == "distance"), None) == "distance",
      str(_items)[:200])
check("d20_le_direct_ne_couvre_que_les_fondus_simples",
      r.status_code == 200
      and sorted(i["id"] for i in _items if i.get("live")) == ["fade", "fadeblack", "fadewhite"])
# Le repli sur une coupe franche est verifie sur le CODE DE PRODUCTION, pas
# reimplemente ici : deux segments V1 dont le second porte une transition
# INCONNUE ("zzz") -> `_build_montage_command` doit emettre le xfade "fade"
# a 0,04 s (le repli `_XFADE["cut"]`), jamais un filtre nomme "zzz". Forme
# des arguments recopiee du plus petit appel vert de
# tests/test_montage_pistes_rendu.py (v1_spec/ov_spec).
_v1_zzz = [
    {"path": "V1_A.mp4", "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 2.0,
     "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None},
    {"path": "V1_B.mp4", "src_dur": 4.0, "src_in": 0.0, "start": 2.0, "end": 4.0,
     "transition": "zzz", "transition_s": 0.0, "speed": 0.0, "effects": None},
]
_cmd_zzz, _ = MS._build_montage_command(_v1_zzz, [], [], None, w=64, h=64, fps=30,
                                        mix_db={}, ducking=False, duration_master=False,
                                        preview=True, out="zzz.mp4")
_flat = " ".join(_cmd_zzz)
check("d20_un_nom_inconnu_retombe_toujours_en_coupe_franche",
      "transition=fade:duration=0.04" in _flat and "transition=zzz" not in _flat,
      _flat[:300])

print("\n[2] D-21 titles.py : huit gabarits ASS dans la charte")
import re                                              # noqa: E402
from PIL import Image                                  # noqa: E402
from app.config import settings as SET                 # noqa: E402
from app.services import subtitle_service as S         # noqa: E402

#: Les seize familles EMBARQUEES : une fonte de gabarit qui n'en serait pas
#: une cle donnerait un fallback libass silencieux.
S_FONTS = getattr(S, "FONT_FILES", {})

try:
    from app.services import titles as TI
except Exception:                       # module absent : l'etat vide de [2]
    class _Vide:
        pass
    TI = _Vide()


def T(nom, defaut):
    """Meme role que `A()` en [1], sur `titles` : un attribut ABSENT fait
    ROUGIR les checks qui le lisent, jamais mourir le banc."""
    return getattr(TI, nom, defaut)


def _rien(*a, **k):
    return None


TEMPLATES = T("TEMPLATES", {})
BRAND = T("BRAND", {})
title_spec = T("title_spec", _rien)
to_ass_title = T("to_ass_title", _rien)
render_title_png = T("render_title_png", _rien)


def _txt(p):
    """Texte d'un `.ass`, ou "" — aucune lecture nue (faute n6)."""
    try:
        return p.read_text(encoding="utf-8") if p is not None and p.is_file() else ""
    except Exception:
        return ""


def _im(p):
    """Image en niveaux de gris, ou None si le PNG n'a pas ete produit."""
    try:
        return Image.open(p).convert("L") if p is not None and p.is_file() else None
    except Exception:
        return None


def clairs(im, y0, y1):
    """Pixels CLAIRS (> 150) dans la bande [y0, y1] de la hauteur. -1 quand
    il n'y a pas d'image : jamais confondu avec « la bande est vide » (0).
    `histogram()` plutot que `getdata()` (deprecie en Pillow 14) : sur une
    image "L" la somme des classes 151..255 est exactement le meme compte."""
    if im is None:
        return -1
    w, h = im.size
    return sum(im.crop((0, int(h * y0), w, int(h * y1))).histogram()[151:])


def sombres(im, y0, y1):
    """Pixels SOMBRES (< 60) dans la bande. Sur un gabarit a BOITE claire (or)
    la bande est claire meme sans une lettre : ce sont les pixels sombres qui
    prouvent que du TEXTE y est grave, pas seulement le rectangle."""
    if im is None:
        return -1
    w, h = im.size
    return sum(im.crop((0, int(h * y0), w, int(h * y1))).histogram()[:60])


def bords(im, frac=.02):
    """Pixels CLAIRS dans les `frac` colonnes de gauche ET de droite du cadre.

    C'est la mesure de DEBORDEMENT horizontal : `WrapStyle: 2` coupe le repli
    de libass, donc un titre trop large pour sa ligne sort du cadre et se fait
    rogner par ffmpeg sans le moindre avertissement. -1 quand il n'y a pas
    d'image."""
    if im is None:
        return -1
    w, h = im.size
    k = max(1, int(w * frac))
    return (sum(im.crop((0, 0, k, h)).histogram()[151:])
            + sum(im.crop((w - k, 0, w, h)).histogram()[151:]))


def _ev(txt, n):
    """n-ieme ligne `Dialogue:`, ou "" (faute n6)."""
    evs = [l for l in txt.splitlines() if l.startswith("Dialogue:")]
    return evs[n] if len(evs) > n else ""


def _style(txt, nom):
    """Ligne `Style: <nom>,`, ou ""."""
    return next((l for l in txt.splitlines() if l.startswith("Style: " + nom + ",")), "")


def _pos_y(ligne):
    """y d'un evenement : 2e argument d'un `\\move(`, sinon 2e d'un `\\pos(`."""
    m = re.search(r"\\move\(([-\d]+),([-\d]+),", ligne or "")
    if m:
        return int(m.group(2))
    m = re.search(r"\\pos\(([-\d]+),([-\d]+)\)", ligne or "")
    return int(m.group(2)) if m else None


def _corps(ligne_style):
    """Champ Fontsize d'une ligne `Style:` (3e), ou -1."""
    ch = (ligne_style or "").split(",")
    try:
        return float(ch[2])
    except (IndexError, ValueError):
        return -1.0


check("d21_huit_gabarits_dans_l_ordre",
      list(TEMPLATES) == ["plein_cadre", "tiers_inferieur", "legende", "compteur",
                          "chapitre", "citation", "hashtag", "cta"],
      list(TEMPLATES))
# Les huit gabarits ne peuvent nommer que des fontes EMBARQUEES et des
# couleurs de la charte : une fonte absente de FONT_FILES donnerait un
# fallback libass silencieux, une couleur hors BRAND ferait lever _style_line.
check("d21_chaque_gabarit_nomme_une_fonte_embarquee",
      len(TEMPLATES) == 8 and all(g.get("font") in S_FONTS for g in TEMPLATES.values()),
      [g.get("font") for g in TEMPLATES.values() if g.get("font") not in S_FONTS])
check("d21_chaque_gabarit_nomme_des_couleurs_de_la_charte",
      len(TEMPLATES) == 8 and len(BRAND) == 5
      and all(g.get("color") in BRAND and (g.get("box") is None or g.get("box") in BRAND)
              for g in TEMPLATES.values()),
      [(g.get("color"), g.get("box")) for g in TEMPLATES.values()
       if g.get("color") not in BRAND or (g.get("box") is not None and g.get("box") not in BRAND)])
spec = title_spec({"tr": "t1", "id": "x", "start": 2, "end": 6,
                   "title": {"template": "tiers_inferieur", "text": "Abysse", "sub": "épisode 3"}})
spec = spec if isinstance(spec, dict) else {}
check("d21_le_spec_est_assaini",
      spec.get("template") == "tiers_inferieur" and spec.get("text") == "Abysse"
      and spec.get("sub") == "épisode 3" and spec.get("start") == 2.0 and spec.get("end") == 6.0,
      spec)
_zzz = title_spec({"title": {"template": "zzz", "text": "t"}, "start": 0, "end": 1})
check("d21_un_gabarit_inconnu_retombe_sur_plein_cadre",
      isinstance(_zzz, dict) and _zzz.get("template") == "plein_cadre", _zzz)
# Temoin positif AVANT la negation : le meme gabarit AVEC texte rend bien un
# spec, sans texte il rend None.
check("d21_sans_texte_pas_de_titre",
      isinstance(title_spec({"title": {"template": "cta", "text": "ok"}, "start": 0, "end": 1}), dict)
      and title_spec({"title": {"template": "cta"}, "start": 0, "end": 1}) is None,
      title_spec({"title": {"template": "cta"}, "start": 0, "end": 1}))
# SIX ENTREES HOSTILES : rien de ce qui vient du client ne doit LEVER. Chacune
# rend None (rien a graver) ou un spec entierement borne. Le temoin positif
# (une entree saine rend bien un spec) est la ligne au-dessus.
_HOSTILES = [
    ("clip_none", None),
    ("clip_chaine", "x"),
    ("title_pas_un_dict", {"title": "Abysse", "start": 0, "end": 2}),
    ("size_texte", {"title": {"template": "cta", "text": "ok", "size": "gros"}, "start": 0, "end": 2}),
    ("start_nan", {"title": {"template": "cta", "text": "ok"}, "start": float("nan"), "end": 2}),
    ("end_chaine", {"title": {"template": "cta", "text": "ok"}, "start": 0, "end": "2"}),
]
_hres, _hmal = [], []
for _nom, _cl in _HOSTILES:
    try:
        _s = title_spec(_cl)
    except Exception as e:                     # une levee = un banc rouge, pas un banc mort
        _hres.append((_nom, "LEVE", repr(e)))
        continue
    if _s is None:
        _hres.append((_nom, "none", None))
    elif (isinstance(_s, dict) and _s.get("template") in TEMPLATES
          and isinstance(_s.get("size"), int) and 24 <= _s["size"] <= 200
          and isinstance(_s.get("start"), float) and isinstance(_s.get("end"), float)
          and _s["end"] > _s["start"]):
        _hres.append((_nom, "borne", None))
    else:
        _hmal.append((_nom, _s))
check("d21_six_entrees_hostiles_ne_levent_jamais_et_sortent_bornees",
      len(_hres) == 6 and not _hmal and all(r[1] in ("none", "borne") for r in _hres),
      (_hmal or [r for r in _hres if r[1] == "LEVE"])[:3])
p = to_ass_title(spec, (1080, 1920), "t_banc")
txt = _txt(p)
try:
    _bom = p.read_bytes().startswith(b"\xef\xbb\xbf") if p is not None and p.is_file() else True
except Exception:
    _bom = True
check("d21_le_fichier_ass_existe_sans_bom", bool(txt) and not _bom, str(p))
check("d21_la_fonte_est_embarquee_par_son_nom_de_famille",
      ",Bebas Neue," in txt and "PlayResX: 1080" in txt, txt[:300])
# L'en-tete doit couper le repli automatique de libass (c'est titles.py qui
# replie) et mettre contour et ombre a l'echelle du script.
check("d21_l_entete_coupe_le_repli_de_libass_et_met_le_contour_a_l_echelle",
      "WrapStyle: 2" in txt and "ScaledBorderAndShadow: yes" in txt, txt[:300])
check("d21_deux_evenements_titre_et_sous_texte", txt.count("Dialogue:") == 2, txt.count("Dialogue:"))
check("d21_l_animation_d_entree_et_de_sortie_est_ecrite",
      "\\fad(" in txt and ("\\move(" in txt or "\\t(" in txt), _ev(txt, 0)[:160])
check("d21_les_bornes_sont_celles_du_clip",
      "0:00:02.00" in txt and "0:00:06.00" in txt, txt[-300:])
check("d21_la_couleur_or_de_la_charte_en_bgr", "&H003CB2E6" in txt, _style(txt, "DzT"))
# Le corps ECRIT n'est pas l'em dessine : libass divise par la hauteur de
# ligne de la fonte. `_style_line` pre-multiplie, comme `_ass_style_line` du
# service de sous-titres. Bebas Neue = 1,3 ; a 1920 p le tiers inferieur est
# a 64*1920/1080 = 114 px d'em, donc 148,2 dans le fichier.
check("d21_le_corps_ecrit_est_premultiplie_par_la_hauteur_de_ligne",
      abs(_corps(_style(txt, "DzT")) - 114 * S.font_line_height("Bebas Neue")) < 0.6,
      (_corps(_style(txt, "DzT")), S.font_line_height("Bebas Neue")))
# La lisibilite du sous-texte est decidee par la BOITE, pas par la couleur du
# titre : `tiers_inferieur` a une boite OR, son sous-texte passe a l'encre
# (&H001D1814) et non en blanc (&H00F6F2EE).
check("d21_sur_une_boite_claire_le_sous_texte_passe_a_l_encre",
      _style(txt, "DzS").startswith("Style: DzS,Bebas Neue,")
      and S._ass_color(BRAND.get("encre", "#14181d")) in _style(txt, "DzS")
      and S._ass_color(BRAND.get("blanc", "#eef2f6")) not in _style(txt, "DzS"),
      _style(txt, "DzS"))
# Un `\move` porte DEJA la position : un `\pos` dans le meme evenement se
# disputerait le meme champ. Temoin positif d'abord (le `\move` est bien la).
_ev_titre, _ev_sub = _ev(txt, 0), _ev(txt, 1)
check("d21_un_gabarit_a_move_n_ecrit_pas_de_pos",
      "\\move(" in _ev_titre and "\\pos(" not in _ev_titre, _ev_titre[:160])
# Ancrage BAS (\an1) : le titre occupe la bande AU-DESSUS de son y, donc le
# sous-texte passe plus haut encore — sinon il sortirait du cadre.
_yt, _ys = _pos_y(_ev_titre), _pos_y(_ev_sub)
check("d21_en_ancrage_bas_le_sous_texte_est_au_dessus_du_titre",
      _yt is not None and _ys is not None and _ys < _yt, (_yt, _ys))
# LE SOUS-TEXTE NE SE GRAVE PAS SUR UN TITRE MULTI-LIGNES. Une citation
# repliee sur plusieurs lignes occupe, autour de son ancre \an5, une
# demi-hauteur de `n * avance / 2` : le `\pos` du sous-texte doit tomber SOUS
# ce bloc. Mesure du 21/09/2026 : avant correction le sub etait grave sur la
# 4e ligne de la citation.
_lg = _txt(to_ass_title(title_spec(
    {"title": {"template": "citation",
               "text": "Le silence eternel de ces espaces infinis m effraie beaucoup",
               "sub": "Blaise"}, "start": 0, "end": 5}), (1080, 1920), "t_cit"))
_lt, _lsb = _ev(_lg, 0), _ev(_lg, 1)
_n = _lt.count("\\N") + 1 if _lt else 0
_av = _corps(_style(_lg, "DzT"))
_yct, _ycs = _pos_y(_lt), _pos_y(_lsb)
check("d21_le_sous_texte_ne_se_grave_pas_sur_un_titre_multi_lignes",
      _n >= 3 and _av > 0 and _yct is not None and _ycs is not None
      and _ycs > _yct + _n * _av / 2,
      (_n, _av, _yct, _ycs))
# Entree/sortie bornees au TIERS du clip : 0,3 s -> 100 ms, pas les 260 ms du
# gabarit tiers_inferieur.
_court = _txt(to_ass_title(title_spec({"title": {"template": "tiers_inferieur", "text": "court"},
                                       "start": 0, "end": 0.3}), (1080, 1920), "t_court"))
check("d21_l_entree_et_la_sortie_sont_bornees_au_tiers_du_clip",
      bool(_court) and "\\fad(100,100)" in _court, _ev(_court, 0)[:140])
# WrapStyle 2 = aucun repli automatique de libass : c'est titles.py qui replie
# par largeur approchee (W*0,9 / (taille*0,55) caracteres par ligne).
_long = _txt(to_ass_title(title_spec({"title": {"template": "citation",
                                                "text": "mot " * 25}, "start": 0, "end": 4}),
                          (1080, 1920), "t_long"))
check("d21_un_texte_long_se_replie_en_plusieurs_lignes",
      bool(_long) and _long.count("\\N") >= 2, _long.count("\\N"))

# ---- MESURE A L'IMAGE : ffmpeg grave le .ass sur un fond uni 540x960, PIL
# compte les pixels clairs bande par bande. Le tableau des bandes attendues
# est celui de la conception D-21 (21/09/2026). `t` est compte DEPUIS LE DEBUT
# DU TITRE (le clip est normalise a start=0 pour l'apercu) ; None = au milieu,
# borne a 1 s.
png = render_title_png(spec, 540, 960, t=1.0)
im = _im(png)
check("d21_le_tiers_inferieur_porte_du_texte_et_le_haut_rien",
      im is not None and clairs(im, .70, .90) > 150 and clairs(im, 0, .20) < 20,
      (clairs(im, .70, .90), clairs(im, 0, .20)))
# Le \an1 ancre le texte par son coin BAS-gauche a y = 0,80 H : rien ne doit
# descendre sous cette ligne. Sans cette bande, un \an7 (texte pendu SOUS
# l'ancre) resterait dans les 70-90 % et passerait inapercu — mesure du
# 21/09/2026 : la mutation an 1 -> 7 ne rougit QUE grace a ceci. La boite OR
# etant elle-meme claire, on exige AUSSI des pixels sombres : ce sont les
# lettres, pas le rectangle. A LIRE AVEC PRUDENCE sur CE gabarit : son titre
# est BLANC sur la boite or, ce sont donc surtout le contour et le SOUS-TEXTE
# a l'encre (cf. le check de la boite claire) qui fournissent ces pixels
# sombres — la contrainte forte de placement reste la bande .82-.98 vide.
check("d21_le_tiers_inferieur_ne_descend_pas_sous_son_ancrage",
      im is not None and clairs(im, .70, .80) > 150 and sombres(im, .70, .80) > 150
      and clairs(im, .82, .98) < 20,
      (clairs(im, .70, .80), sombres(im, .70, .80), clairs(im, .82, .98)))
# Le `\move` part de x0 = xa - W*0,15 : a t = entree + 0,1 s le texte doit
# avoir FINI sa course, donc porter autant de pixels qu'au milieu du clip.
_im_move = _im(render_title_png(title_spec({"title": {"template": "tiers_inferieur",
                                                      "text": "Abysse"}, "start": 2, "end": 6}),
                                540, 960, t=0.36))
check("d21_le_mouvement_d_entree_est_fini_juste_apres_l_entree",
      _im_move is not None and clairs(_im_move, .70, .80) > 150
      and clairs(_im_move, .82, .98) < 20,
      (clairs(_im_move, .70, .80), clairs(_im_move, .82, .98)))
spec2 = title_spec({"title": {"template": "plein_cadre", "text": "GRAND TITRE"},
                    "start": 0, "end": 3})
im2 = _im(render_title_png(spec2, 540, 960))
check("d21_le_plein_cadre_est_centre",
      im2 is not None and clairs(im2, .40, .60) > 300 and clairs(im2, 0, .15) < 20,
      (clairs(im2, .40, .60), clairs(im2, 0, .15)))
im3 = _im(render_title_png(title_spec({"title": {"template": "legende", "text": "Legende ici bas"},
                                       "start": 0, "end": 4}), 540, 960))
check("d21_la_legende_est_au_ras_du_bord_bas",
      im3 is not None and clairs(im3, .85, .95) > 150 and clairs(im3, 0, .20) < 20,
      (clairs(im3, .85, .95), clairs(im3, 0, .20)))
im4 = _im(render_title_png(title_spec({"title": {"template": "hashtag", "text": "#deepotus"},
                                       "start": 0, "end": 4}), 540, 960))
check("d21_le_hashtag_est_en_haut_du_cadre",
      im4 is not None and clairs(im4, .05, .20) > 150 and clairs(im4, .40, .60) < 20,
      (clairs(im4, .05, .20), clairs(im4, .40, .60)))
im5 = _im(render_title_png(title_spec({"title": {"template": "cta", "text": "ABONNE-TOI"},
                                       "start": 0, "end": 4}), 540, 960))
check("d21_le_cta_est_juste_au_dessus_du_bas",
      im5 is not None and clairs(im5, .78, .92) > 150 and sombres(im5, .78, .92) > 150
      and clairs(im5, 0, .20) < 20,
      (clairs(im5, .78, .92), sombres(im5, .78, .92), clairs(im5, 0, .20)))
# L'APERCU D'UN CLIP POSE TARD DANS LA TIMELINE. Sans normalisation a start=0,
# le titre serait grave a 30 s et l'image extraite a 1 s serait VIDE — puis
# mise en cache, donc vide pour toujours. La duree du clip normalise est en
# outre bornee a 10 s : au-dela, l'apercu ne ferait que faire generer a ffmpeg
# des secondes de fond uni jamais regardees, et `t = min(1, duree/2)` tomberait
# de toute facon a 1 s.
im6 = _im(render_title_png(title_spec({"title": {"template": "plein_cadre", "text": "TARDIF"},
                                       "start": 30, "end": 34}), 540, 960))
check("d21_l_apercu_d_un_clip_pose_a_30_s_n_est_pas_vide",
      im6 is not None and clairs(im6, .40, .60) > 300, clairs(im6, .40, .60))
# Les .ass d'apercu vivent dans le cache d'apercu, PAS dans le dossier des
# sous-titres du montage. Temoin positif : les apercus ci-dessus ont bien
# produit des images, donc des .ass, avant cette negation.
_subs = SET.outputs_path / "subtitles"
_fuites = sorted(q.name for q in _subs.glob("title_prev_*")) if _subs.is_dir() else []
check("d21_les_ass_d_apercu_ne_fuient_pas_dans_le_dossier_des_sous_titres",
      im6 is not None and _subs.is_dir() and not _fuites, _fuites[:3])
# LE TITRE NE DOIT PAS DEBORDER DU CADRE. Deux gabarits dans les deux fontes
# les plus LARGES des seize embarquees (Archivo Black 0,769 em de majuscule,
# Cinzel 0,681) et un texte en capitales : aucun pixel clair dans les 2 % de
# colonnes de gauche ni de droite. Mesures du 21/09/2026 sur 540 px, bbox
# horizontale : avec « 0,55 em par caractere » `chapitre` rendait (40, 539) —
# rogne a droite ; avec l'avance MOYENNE des majuscules, encore (40, 539) ;
# avec la largeur reellement mesuree, (37, 499) et `cta` (43, 496).
for _tpl in ("cta", "chapitre"):
    _imb = _im(render_title_png(title_spec({"title": {"template": _tpl,
                                                      "text": "COMMUNAUTE MONDIALE"},
                                            "start": 0, "end": 4}), 540, 960))
    check("d21_le_titre_ne_deborde_pas_du_cadre_" + _tpl,
          _imb is not None and clairs(_imb, .10, .95) > 150 and bords(_imb) == 0,
          (clairs(_imb, .10, .95), bords(_imb)))
# Le pire cas de largeur : des M et des W, sur les trois gabarits qui
# touchaient les DEUX bords avant correction.
for _tpl in ("plein_cadre", "legende", "citation"):
    _imw = _im(render_title_png(title_spec({"title": {"template": _tpl,
                                                      "text": "MMMMMMM WWWWWWW MMMMMMM"},
                                            "start": 0, "end": 4}), 540, 960))
    check("d21_le_pire_cas_de_largeur_tient_dans_le_cadre_" + _tpl,
          _imw is not None and clairs(_imw, .05, .98) > 150 and bords(_imw) == 0,
          (clairs(_imw, .05, .98), bords(_imw)))
_tous = [to_ass_title(title_spec({"title": {"template": k, "text": "x", "sub": "y"},
                                  "start": 0, "end": 2}), (1920, 1080), "t_" + k)
         for k in TEMPLATES]
check("d21_chaque_gabarit_produit_un_ass_valide",
      len(_tous) == 8 and all(f is not None and f.is_file() and _txt(f).count("Dialogue:") == 2
                              for f in _tous),
      [str(f) for f in _tous if f is None or not f.is_file()][:3])


print("\n[3] D-21 la piste t1 est gravee avant S1, routes titles et title-preview")
import io                                              # noqa: E402
import pathlib                                         # noqa: E402
import subprocess                                      # noqa: E402

# La section ne lance ffmpeg QUE la ou elle mesure une image : la commande de
# rendu est mesuree comme TEXTE (elle n'est jamais executee), donc un fichier
# d'un octet suffit a la porter. Le rendu reel de la fin de section, lui, veut
# une VRAIE source (le pre-vol P8 refuse ce qu'aucun demultiplexeur n'ouvre) :
# elle est fabriquee par ffmpeg juste avant.
V1F = str(pathlib.Path(TMP) / "v1.mp4")
pathlib.Path(V1F).write_bytes(b"x")


def TL(name="titres", n=1, dur=4, src=None):
    """Timeline minimale — recopiee de tests/test_montage_projets.py."""
    return {"name": name, "ratio": "9:16", "duration": dur, "mix": {},
            "clips": [{"tr": "v1", "id": "v%d" % i, "start": 0, "end": 4,
                       "src": {"file_path": src or V1F}} for i in range(n)]}


def wipe_courant():
    """Le COURANT efface — l'etat vide de la persistance de cette section."""
    try:
        (pathlib.Path(TMP) / "montage_saved.json").unlink()
    except OSError:
        pass


def V1SPEC(**kw):
    """Forme d'un clip V1 pour `_build_montage_command`, RECOPIEE du plus
    petit appel vert de tests/test_montage_pistes_rendu.py (`v1_spec()`)."""
    d = {"path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def BUILD(**kw):
    """`_build_montage_command` avec les arguments constants de la section.
    Un `TypeError` (mot-cle `titles_ass` pas encore accepte : l'ETAT VIDE de
    cette section) rend un temoin au lieu de tuer le banc — les checks
    rougissent alors au lieu de disparaitre."""
    a = {"w": 64, "h": 64, "fps": 25, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": True,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    try:
        cmd, _ = MS._build_montage_command([V1SPEC()], [], [], None, **a)
    except TypeError as e:
        return "TypeError: %s" % e
    return FLAT(cmd)


meta = MS._tracks_meta([{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"},
                        {"id": "s1", "kind": "subs"}])
check("d21_tracks_meta_declare_le_genre_title",
      (meta.get("t1") or {}).get("kind") == "title", meta.get("t1"))
# Une piste de titres n'est NI une couche video composee (elle ne gagne aucun
# rang) NI une piste audio bouclee : la negation est precedee, dans la MEME
# expression, du temoin positif qui etablit que la piste a bien ete declaree.
check("d21_la_piste_titre_n_est_ni_une_couche_video_ni_une_boucle",
      (meta.get("t1") or {}).get("kind") == "title"
      and (meta.get("t1") or {}).get("layer") == 0
      and (meta.get("t1") or {}).get("loop") is False,
      meta.get("t1"))

wipe_courant()
_tl = TL("titres", n=2)
_tl["tracks"] = [{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}]
_tl["clips"].append({"tr": "t1", "id": "tt1", "kind": "title", "start": 1, "end": 3,
                     "title": {"template": "tiers_inferieur", "text": "Abysse",
                               "sub": "ep. 3"}})
_rs = c.post("/api/montage/save", json=_tl)
_cur = J(c.get("/api/montage/project"))
check("d21_le_clip_titre_survit_a_la_sauvegarde",
      _rs.status_code == 200
      and any(k.get("tr") == "t1" and (k.get("title") or {}).get("text") == "Abysse"
              for k in (_cur.get("clips") or [])),
      str(_cur.get("clips"))[:200])

# --- la commande : les titres AVANT S1 -------------------------------------
_t0 = os.path.join(TMP, "t0.ass")
_t1 = os.path.join(TMP, "t1.ass")
_sa = os.path.join(TMP, "s.ass")
for _p in (_t0, _t1, _sa):
    pathlib.Path(_p).write_text("x", encoding="utf-8")

_fc = BUILD(titles_ass=[_t0], subs_ass=_sa)
_it, _isb = _fc.find("t0.ass"), _fc.find("s.ass")
check("d21_le_titre_est_grave_avant_les_sous_titres",
      0 <= _it < _isb and "[tt0]" in _fc, (_it, _isb, _fc[-240:]))
_fc2 = BUILD(titles_ass=[_t0, _t1], subs_ass=_sa)
check("d21_deux_titres_sont_chaines_dans_l_ordre",
      _fc2.find("t0.ass") >= 0
      and _fc2.find("t0.ass") < _fc2.find("t1.ass") < _fc2.find("s.ass")
      and "[tt0]" in _fc2 and "[tt1]" in _fc2 and "[tt0]subtitles=" in _fc2,
      _fc2[-300:])
# SANS S1 mais AVEC un titre : la sortie doit rester produite — le dernier
# maillon `format=yuv420p[outv]` se pose alors sur le titre, pas sur S1.
_fc3 = BUILD(titles_ass=[_t0])
check("d21_sans_sous_titres_la_sortie_reste_produite",
      "[tt0]" in _fc3 and "[outv]" in _fc3 and "[tt0]format=yuv420p[outv]" in _fc3,
      _fc3[-240:])
_fc0 = BUILD()
check("d21_sans_titre_la_commande_est_intacte",
      "[outv]" in _fc0 and "tt0" not in _fc0, _fc0[-240:])
# Non-regression : ajouter le mot-cle ne doit RIEN changer a la commande
# historique. Le temoin positif est la presence de `[outv]` dans `_fc0`.
check("d21_une_liste_de_titres_vide_vaut_l_absence_de_titres",
      "[outv]" in _fc0 and BUILD(titles_ass=[]) == _fc0 and BUILD(titles_ass=None) == _fc0,
      (_fc0[-160:], BUILD(titles_ass=[])[-160:]))

# --- la collecte des clips titre du rendu ----------------------------------
_meta2 = MS._tracks_meta([{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}])
_clips_t = [
    {"tr": "v1", "id": "v0", "start": 0, "end": 6, "src": {"file_path": V1F}},
    {"tr": "t1", "id": "b", "kind": "title", "start": 4, "end": 5,
     "title": {"template": "cta", "text": "Abonnez-vous"}},
    {"tr": "t1", "id": "a", "kind": "title", "start": 1, "end": 2,
     "title": {"template": "plein_cadre", "text": "Abysse"}},
    {"tr": "t1", "id": "vide", "kind": "title", "start": 2, "end": 3,
     "title": {"template": "cta", "text": "   "}},
    "pas un dict",
]
_coll = getattr(MS, "_titles_ass", None)


def COLL(clips, meta_, stem):
    """(chemins, infos) de `_titles_ass`, ou un temoin — la fonction ABSENTE
    (etat vide) doit faire rougir, jamais tuer le banc."""
    if not callable(_coll):
        return None, {}
    v = _coll(clips, meta_, (540, 960), stem)
    return v if isinstance(v, tuple) and len(v) == 2 else (v, {})


_ass_t, _inf_t = COLL(_clips_t, _meta2, "banc_t")
check("d21_la_collecte_range_les_titres_par_debut_et_ignore_le_vide",
      isinstance(_ass_t, list) and len(_ass_t) == 2
      and all(os.path.isfile(p) for p in _ass_t)
      and "Abysse" in pathlib.Path(_ass_t[0]).read_text(encoding="utf-8")
      and "Abonnez-vous" in pathlib.Path(_ass_t[1]).read_text(encoding="utf-8"),
      [os.path.basename(p) for p in _ass_t] if isinstance(_ass_t, list) else _ass_t)
# Un clip titre ECARTE (texte de trois espaces) est COMPTE, pas avale : sans
# ce compte, un carton vide disparaitrait du rendu sans laisser de trace.
check("d21_le_clip_titre_sans_texte_est_compte_comme_ignore",
      isinstance(_ass_t, list) and len(_ass_t) == 2
      and (_inf_t or {}).get("titres") == 2 and (_inf_t or {}).get("ignores") == 1,
      _inf_t)
# L'etat vide de la collecte : la MEME liste de clips, mais aucune piste de
# genre `title` declaree — negation precedee du temoin positif ci-dessus.
_ass_0, _inf_0 = COLL(_clips_t, MS._tracks_meta([{"id": "v1", "kind": "video"}]),
                      "banc_0")
check("d21_sans_piste_titre_la_collecte_ne_grave_rien",
      isinstance(_ass_t, list) and len(_ass_t) == 2 and _ass_0 == []
      and (_inf_0 or {}).get("ignores") == 0, (_ass_0, _inf_0))

# --- le rendu transmet vraiment ces ASS ------------------------------------
# Une VRAIE source : le pre-vol P8 refuse ce qu'aucun demultiplexeur n'ouvre,
# donc le fichier d'un octet ne passerait pas /render. Rien n'est encode ici :
# `_run_ffmpeg` est remplace par un no-op le temps de l'appel, et
# `_build_montage_command` par un espion qui note `titles_ass` puis delegue.
_REAL = str(pathlib.Path(TMP) / "reel.mp4")
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    subprocess.run([_fb(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=s=64x64:r=10:d=1", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", _REAL], check=False, capture_output=True, timeout=60)
except Exception as _e:                    # ffmpeg injoignable : le check rougit
    print("  (ffmpeg injoignable pour la source reelle : %s)" % _e)
_cap = {}
_vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg


def _espion(*a, **k):
    _cap["titles_ass"] = k.get("titles_ass")
    return _vrai_build(*a, **k)


_tlr = TL("rendu", n=1, src=_REAL)
_tlr["preview"] = True
_tlr["tracks"] = [{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}]
_tlr["clips"] += [
    {"tr": "t1", "id": "z", "kind": "title", "start": 2, "end": 3,
     "title": {"template": "cta", "text": "Abonnez-vous"}},
    {"tr": "t1", "id": "y", "kind": "title", "start": 0, "end": 1,
     "title": {"template": "plein_cadre", "text": "Abysse"}},
    {"tr": "t1", "id": "x", "kind": "title", "start": 1, "end": 2,
     "title": {"template": "cta", "text": ""}},
]
MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
try:
    _rr = c.post("/api/montage/render", json=_tlr)
finally:
    MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
_tta = _cap.get("titles_ass")
check("d21_le_rendu_transmet_les_ass_des_titres_au_graphe",
      _rr.status_code == 200 and isinstance(_tta, list) and len(_tta) == 2
      and all(os.path.isfile(p) for p in _tta)
      and "Abysse" in pathlib.Path(_tta[0]).read_text(encoding="utf-8"),
      (_rr.status_code, _tta))

# --- GET /titles -----------------------------------------------------------
r = c.get("/api/montage/titles"); d = J(r)
_gab = d.get("gabarits") or []
check("d21_la_route_titles_liste_les_huit_gabarits",
      r.status_code == 200 and [g.get("id") for g in _gab] == list(T("TEMPLATES", {})),
      str(d)[:200])
# La table des libelles couvre EXACTEMENT les gabarits : une entree perdue
# parmi les quatre dont le libelle vaut l'identifiant (compteur, chapitre,
# citation, hashtag) passerait sinon au vert par le repli `LABELS.get(k, k)`.
check("d21_la_table_des_libelles_couvre_exactement_les_gabarits",
      set(T("LABELS", {})) == set(T("TEMPLATES", {})) != set(),
      sorted(set(T("LABELS", {})) ^ set(T("TEMPLATES", {}))))
check("d21_chaque_gabarit_porte_son_libelle_francais_et_sa_fonte",
      r.status_code == 200 and len(_gab) == 8
      and all(set(g) >= {"id", "label", "font", "size", "color", "box", "anim"}
              for g in _gab)
      and all(isinstance(g.get("label"), str) and g["label"] for g in _gab)
      # Quatre identifiants SONT deja des mots francais (compteur, chapitre,
      # citation, hashtag) : leur libelle vaut leur id, et c'est verifie
      # EXPLICITEMENT plutot qu'exclu en silence (meme precedent que
      # `distance` en [1]). Les quatre autres doivent, eux, avoir ete
      # traduits — c'est la que se voit une table oubliee.
      and {g["id"]: g["label"] for g in _gab if g["id"] in
           ("compteur", "chapitre", "citation", "hashtag")}
      == {"compteur": "compteur", "chapitre": "chapitre",
          "citation": "citation", "hashtag": "hashtag"}
      and {g["id"]: g["label"] for g in _gab if g["id"] in
           ("plein_cadre", "tiers_inferieur", "legende", "cta")}
      == {"plein_cadre": "plein cadre", "tiers_inferieur": "tiers inférieur",
          "legende": "légende", "cta": "appel à l'action"},
      str(_gab)[:240])
# D-21 (tache 7) : LES SEIZE POLICES ET LES CINQ COULEURS PARTENT AVEC LES
# GABARITS. L'inspecteur du client les offre dans deux `<select>`, et il n'en
# a AUCUNE copie -- meme regle que les huit gabarits. Les deux listes sont
# celles que `title_spec` interroge (`font not in S.FONT_FILES`, `color not
# in BRAND`) : servir autre chose aurait fait proposer a l'ecran des valeurs
# que le rendu remplace en silence. La mesure porte sur l'IDENTITE avec les
# tables du service, pas sur un compte -- un compte serait reste vert apres
# un renommage.
_subs_ff = list(getattr(S, "FONT_FILES", {}))
check("d21_la_route_titles_sert_les_seize_polices_gravables",
      r.status_code == 200 and len(_subs_ff) == 16
      and d.get("fonts") == _subs_ff,
      f'servies={d.get("fonts")} service={_subs_ff}')
check("d21_la_route_titles_sert_les_cinq_couleurs_de_la_charte",
      r.status_code == 200 and d.get("colors") == list(T("BRAND", {}))
      and len(d.get("colors") or []) == 5,
      f'servies={d.get("colors")} charte={list(T("BRAND", {}))}')
# ET L'INSPECTEUR N'EN A AUCUNE COPIE : ni les seize familles, ni les cinq
# noms de la charte, ni leurs hex ne sont ecrits dans son corps — il ne
# connait que ses proprietes. LA MESURE PORTE SUR LE CORPS DE LA FONCTION et
# non sur le fichier entier, et c'est une MESURE : la couche porte deja une
# table `DZM_MARKER_COLORS` (D-5) dont trois noms — « or », « cyan »,
# « rouge » — sont ceux de la charte par coincidence (les hex, eux,
# different). Une ligne sur le fichier entier rougissait sur ce faux positif.
# La negation etablit d'abord que le corps a ete TROUVE et qu'il est long.
_CJS = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "patches" / "montage.js"
_cjs = _CJS.read_text(encoding="utf-8") if _CJS.is_file() else ""
_i7a = _cjs.find("function DzmTitleInspector(")
_i7b = _cjs.find("/* ── export contrat", _i7a) if _i7a >= 0 else -1
_corps7 = _cjs[_i7a:_i7b] if 0 <= _i7a < _i7b else ""
_fuite7 = ([f for f in _subs_ff if ('"%s"' % f) in _corps7]
           + [k for k in T("BRAND", {}) if ('"%s"' % k) in _corps7]
           + [v for v in T("BRAND", {}).values() if v in _corps7])
check("d21_l_inspecteur_ne_recopie_ni_les_polices_ni_les_couleurs",
      len(_corps7) > 2000 and not _fuite7,
      f"corps={len(_corps7)} o fuites={_fuite7}")

# --- GET /title-preview ----------------------------------------------------


def _png(resp):
    """Dimensions du PNG rendu, ou None — jamais un `Image.open` nu."""
    try:
        return Image.open(io.BytesIO(resp.content)).size
    except Exception:
        return None


r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abonnez-vous", "w": 270})
check("d21_l_apercu_est_un_png",
      r.status_code == 200
      and r.headers.get("content-type", "").startswith("image/png")
      and len(r.content) > 500, (r.status_code, r.headers.get("content-type")))
check("d21_l_apercu_est_vertical_a_la_largeur_demandee",
      r.status_code == 200 and _png(r) == (270, 480), _png(r))
check("d21_l_apercu_porte_un_cache_control",
      r.status_code == 200
      and r.headers.get("cache-control", "") == "public, max-age=86400",
      r.headers.get("cache-control"))
# Le CACHE : une seconde requete identique doit servir le MEME fichier, pas en
# regraver un. Mesure DIRECTE sur le disque (horodatage en nanosecondes du PNG
# du cache) ; temoin positif : le fichier existe avant la seconde requete.
_spec_p = T("title_spec", _rien)({"title": {"template": "cta", "text": "Abonnez-vous"},
                                  "start": 0, "end": 3})
_pp = T("render_title_png", _rien)(_spec_p, 270, 480)
_mt0 = os.stat(_pp).st_mtime_ns if _pp and os.path.isfile(_pp) else None
r2 = c.get("/api/montage/title-preview",
           params={"template": "cta", "text": "Abonnez-vous", "w": 270})
_mt1 = os.stat(_pp).st_mtime_ns if _pp and os.path.isfile(_pp) else None
check("d21_un_second_apercu_identique_sort_du_cache",
      _mt0 is not None and r2.status_code == 200
      and r2.headers.get("content-type", "").startswith("image/png")
      and _mt1 == _mt0 and len(r2.content) == len(r.content), (_mt0, _mt1))
r = c.get("/api/montage/title-preview",
          params={"template": "gabarit_inconnu", "text": "Abysse", "w": 270})
check("d21_un_gabarit_inconnu_replie_sur_plein_cadre",
      r.status_code == 200 and _png(r) == (270, 480), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abysse", "w": 5000})
check("d21_la_largeur_de_l_apercu_est_bornee_en_haut",
      r.status_code == 200 and _png(r) == (640, 1136), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abysse", "w": 10})
check("d21_la_largeur_de_l_apercu_est_bornee_en_bas",
      r.status_code == 200 and _png(r) == (96, 170), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abysse", "w": "abc"})
check("d21_une_largeur_illisible_retombe_sur_le_defaut",
      r.status_code == 200 and _png(r) == (270, 480), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abysse", "w": "inf"})
check("d21_une_largeur_infinie_retombe_sur_le_defaut",
      r.status_code == 200 and _png(r) == (270, 480), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview",
          params={"template": "cta", "text": "Abysse", "w": 271})
check("d21_une_largeur_impaire_est_ramenee_au_pair_inferieur",
      r.status_code == 200 and _png(r) == (270, 480), (r.status_code, _png(r)))
r = c.get("/api/montage/title-preview", params={"template": "cta", "text": ""})
check("d21_l_apercu_sans_texte_est_un_400", r.status_code == 400, r.status_code)
# Les PARAMETRES arrivent vraiment jusqu'a la gravure : `sub` et `color`
# changent les OCTETS du PNG. Temoin positif d'abord (les trois reponses sont
# des PNG lisibles), puis l'inegalite.
_rn = c.get("/api/montage/title-preview",
            params={"template": "legende", "text": "Abysse", "w": 270})
_rs2 = c.get("/api/montage/title-preview",
             params={"template": "legende", "text": "Abysse", "sub": "ep. 3",
                     "w": 270})
_rc = c.get("/api/montage/title-preview",
            params={"template": "legende", "text": "Abysse", "color": "rouge",
                    "w": 270})
check("d21_le_sous_texte_change_l_image_de_l_apercu",
      _png(_rn) == (270, 480) and _png(_rs2) == (270, 480)
      and _rn.content != _rs2.content, (len(_rn.content), len(_rs2.content)))
check("d21_la_couleur_de_charte_change_l_image_de_l_apercu",
      _png(_rn) == (270, 480) and _png(_rc) == (270, 480)
      and _rn.content != _rc.content, (len(_rn.content), len(_rc.content)))
# 503 et non 500 quand ffmpeg ne rend rien : l'outil manque, la requete est
# valide. Mesure par remplacement de `render_title_png` (la route l'importe a
# l'appel), restaure aussitot.
_vrai_png = T("render_title_png", _rien)
try:
    TI.render_title_png = lambda *a, **k: None
    _r503 = c.get("/api/montage/title-preview",
                  params={"template": "cta", "text": "Abysse", "w": 270})
finally:
    TI.render_title_png = _vrai_png
check("d21_un_apercu_que_ffmpeg_ne_rend_pas_est_un_503",
      _r503.status_code == 503, _r503.status_code)

# --- le cache d'apercu est BORNE -------------------------------------------
# Le dossier d'apercu est partage avec les vignettes d'effets : son balayage
# doit connaitre les DEUX fichiers que pose un apercu de titre (le PNG et son
# ASS). `keep` est reduit le temps de la mesure, sans quoi il faudrait 800
# apercus pour voir la borne.
from app.services import effects_preview as EP            # noqa: E402


def _cnt(motif):
    return len([p for p in EP.cache_dir().glob(motif) if ".tmp." not in p.name])


_vrai_prune = EP._prune_cache
try:
    EP._prune_cache = lambda keep=2, motifs=None: _vrai_prune(
        2, motifs if motifs is not None else EP._CACHE_MOTIFS)
    for _i in range(6):
        c.get("/api/montage/title-preview",
              params={"template": "cta", "text": "purge %d" % _i, "w": 270})
finally:
    EP._prune_cache = _vrai_prune
_npng, _nass = _cnt("tt_*.png"), _cnt("title_prev_*.ass")
check("d21_le_cache_des_apercus_de_titre_est_borne",
      _npng > 0 and _npng <= 2 and _nass > 0 and _nass <= 2, (_npng, _nass))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
sys.exit(1 if fail else 0)
