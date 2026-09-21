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


def _pos_y(ligne):
    """y d'un evenement : 2e argument d'un `\\move(`, sinon 2e d'un `\\pos(`."""
    m = re.search(r"\\move\(([-\d]+),([-\d]+),", ligne or "")
    if m:
        return int(m.group(2))
    m = re.search(r"\\pos\(([-\d]+),([-\d]+)\)", ligne or "")
    return int(m.group(2)) if m else None


check("d21_huit_gabarits_dans_l_ordre",
      list(TEMPLATES) == ["plein_cadre", "tiers_inferieur", "legende", "compteur",
                          "chapitre", "citation", "hashtag", "cta"],
      list(TEMPLATES))
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
      and title_spec({"title": {"template": "cta"}, "start": 0, "end": 1}) is None)
p = to_ass_title(spec, (1080, 1920), "t_banc")
txt = _txt(p)
try:
    _bom = p.read_bytes().startswith(b"\xef\xbb\xbf") if p is not None and p.is_file() else True
except Exception:
    _bom = True
check("d21_le_fichier_ass_existe_sans_bom", bool(txt) and not _bom, str(p))
check("d21_la_fonte_est_embarquee_par_son_nom_de_famille",
      ",Bebas Neue," in txt and "PlayResX: 1080" in txt, txt[:300])
check("d21_deux_evenements_titre_et_sous_texte", txt.count("Dialogue:") == 2, txt.count("Dialogue:"))
check("d21_l_animation_d_entree_et_de_sortie_est_ecrite",
      "\\fad(" in txt and ("\\move(" in txt or "\\t(" in txt))
check("d21_les_bornes_sont_celles_du_clip",
      "0:00:02.00" in txt and "0:00:06.00" in txt, txt[-300:])
check("d21_la_couleur_or_de_la_charte_en_bgr", "&H003CB2E6" in txt)
# Un `\move` porte DEJA la position : un `\pos` dans le meme evenement se
# disputerait le meme champ. Temoin positif d'abord (le `\move` est bien la).
_evs = [l for l in txt.splitlines() if l.startswith("Dialogue:")]
_ev_titre = _evs[0] if _evs else ""
_ev_sub = _evs[1] if len(_evs) > 1 else ""
check("d21_un_gabarit_a_move_n_ecrit_pas_de_pos",
      "\\move(" in _ev_titre and "\\pos(" not in _ev_titre, _ev_titre[:160])
# Ancrage BAS (\an1) : le titre occupe la bande AU-DESSUS de son y, donc le
# sous-texte passe plus haut encore — sinon il sortirait du cadre.
_yt, _ys = _pos_y(_ev_titre), _pos_y(_ev_sub)
check("d21_en_ancrage_bas_le_sous_texte_est_au_dessus_du_titre",
      _yt is not None and _ys is not None and _ys < _yt, (_yt, _ys))
# Entree/sortie bornees au TIERS du clip : 0,3 s -> 100 ms, pas les 260 ms du
# gabarit tiers_inferieur.
_court = _txt(to_ass_title(title_spec({"title": {"template": "tiers_inferieur", "text": "court"},
                                       "start": 0, "end": 0.3}), (1080, 1920), "t_court"))
check("d21_l_entree_et_la_sortie_sont_bornees_au_tiers_du_clip",
      bool(_court) and "\\fad(100,100)" in _court,
      next((l for l in _court.splitlines() if l.startswith("Dialogue:")), "")[:120])
# WrapStyle 2 = aucun repli automatique de libass : c'est titles.py qui replie
# par largeur approchee (W*0,9 / (taille*0,55) caracteres par ligne).
_long = _txt(to_ass_title(title_spec({"title": {"template": "citation",
                                                "text": "mot " * 25}, "start": 0, "end": 4}),
                          (1080, 1920), "t_long"))
check("d21_un_texte_long_se_replie_en_plusieurs_lignes",
      bool(_long) and _long.count("\\N") >= 2, _long.count("\\N"))

# ---- MESURE A L'IMAGE : ffmpeg grave le .ass sur un fond uni 540x960, PIL
# compte les pixels clairs bande par bande. Le tableau des bandes attendues
# est celui de la conception D-21 (21/09/2026).
png = render_title_png(spec, 540, 960, t=3.0)   # t = start + 1 s
im = _im(png)
check("d21_le_tiers_inferieur_porte_du_texte_et_le_haut_rien",
      im is not None and clairs(im, .70, .90) > 150 and clairs(im, 0, .20) < 20,
      (clairs(im, .70, .90), clairs(im, 0, .20)))
# Le \an1 ancre le texte par son coin BAS-gauche a y = 0,80 H : rien ne doit
# descendre sous cette ligne. Sans cette bande, un \an7 (texte pendu SOUS
# l'ancre, 80 %-86 %) resterait dans les 70-90 % et passerait inapercu —
# mesure du 21/09/2026 : la mutation an 1 -> 7 ne rougit QUE grace a ceci.
check("d21_le_tiers_inferieur_ne_descend_pas_sous_son_ancrage",
      im is not None and clairs(im, .70, .80) > 150 and clairs(im, .82, .98) < 20,
      (clairs(im, .70, .80), clairs(im, .82, .98)))
# Le `\move` part de x0 = xa - W*0,15 : a t = start + entree + 0,1 s le texte
# doit avoir FINI sa course, donc porter autant de pixels qu'a t = 3 s.
_im_move = _im(render_title_png(title_spec({"title": {"template": "tiers_inferieur",
                                                      "text": "Abysse"}, "start": 2, "end": 6}),
                                540, 960, t=2.36))
check("d21_le_mouvement_d_entree_est_fini_juste_apres_l_entree",
      _im_move is not None and clairs(_im_move, .70, .90) > 150
      and clairs(_im_move, 0, .20) < 20,
      (clairs(_im_move, .70, .90), clairs(_im_move, 0, .20)))
spec2 = title_spec({"title": {"template": "plein_cadre", "text": "GRAND TITRE"},
                    "start": 0, "end": 3})
im2 = _im(render_title_png(spec2, 540, 960, t=1.5))
check("d21_le_plein_cadre_est_centre",
      im2 is not None and clairs(im2, .40, .60) > 300 and clairs(im2, 0, .15) < 20,
      (clairs(im2, .40, .60), clairs(im2, 0, .15)))
im3 = _im(render_title_png(title_spec({"title": {"template": "legende", "text": "Legende ici bas"},
                                       "start": 0, "end": 4}), 540, 960, t=1.5))
check("d21_la_legende_est_au_ras_du_bord_bas",
      im3 is not None and clairs(im3, .85, .95) > 150 and clairs(im3, 0, .20) < 20,
      (clairs(im3, .85, .95), clairs(im3, 0, .20)))
im4 = _im(render_title_png(title_spec({"title": {"template": "hashtag", "text": "#deepotus"},
                                       "start": 0, "end": 4}), 540, 960, t=1.5))
check("d21_le_hashtag_est_en_haut_du_cadre",
      im4 is not None and clairs(im4, .05, .20) > 150 and clairs(im4, .40, .60) < 20,
      (clairs(im4, .05, .20), clairs(im4, .40, .60)))
im5 = _im(render_title_png(title_spec({"title": {"template": "cta", "text": "ABONNE-TOI"},
                                       "start": 0, "end": 4}), 540, 960, t=1.5))
check("d21_le_cta_est_juste_au_dessus_du_bas",
      im5 is not None and clairs(im5, .78, .92) > 150 and clairs(im5, 0, .20) < 20,
      (clairs(im5, .78, .92), clairs(im5, 0, .20)))
_tous = [to_ass_title(title_spec({"title": {"template": k, "text": "x", "sub": "y"},
                                  "start": 0, "end": 2}), (1920, 1080), "t_" + k)
         for k in TEMPLATES]
check("d21_chaque_gabarit_produit_un_ass_valide",
      len(_tous) == 8 and all(f is not None and f.is_file() and _txt(f).count("Dialogue:") == 2
                              for f in _tous),
      [str(f) for f in _tous if f is None or not f.is_file()][:3])

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
sys.exit(1 if fail else 0)
