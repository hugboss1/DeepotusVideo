# -*- coding: utf-8 -*-
"""P2 — SOUS-TITRES ANIMES MOT PAR MOT. Banc-MIROIR : on lit le FICHIER ASS
ecrit sur le disque et la TRAME rendue par ffmpeg, jamais le code qui pretend
les produire. En-tete recopie de test_montage_pistes_dyn.py (env, _exe, check,
sh, fixture, frame, mean_rgb, v1_spec).
Run : & $PY tests/test_subs_animes.py   (depuis backend/)

CE QUI EST FERME ICI
  [1] `wordAnim` non nul => l'ASS porte UN evenement par mot, chacun pose en
      `\\pos` a sa place dans la ligne centree et anime par `\\t`. Le mot 2
      commence a SON temps a lui, pas a celui de la replique.
  [2] MIROIR a l'image : un mot SEUL est plus GROS au sommet du rebond
      (130 ms) qu'une fois pose (400 ms) — surface de pixels clairs mesuree
      dans la bande basse de la trame. Et `wordAnim:"none"` ne pose AUCUN
      `\\pos` : la ligne karaoke historique est intacte.
  [3] le VOCABULAIRE du panneau (`subtitle_ui.ui_word_anim`) : « couleur » —
      la valeur que M10 envoie PAR DEFAUT — et toute valeur inconnue
      retombent sur `none`, donc sur le karaoke et sur aucun `\\pos` ;
      « rebond » et « glow » se rendent eux-memes. Et la BALISE du glow
      (`\\bord1\\t(0,160,\\bord6)\\t(160,320,\\bord2)`) est LUE dans l'ASS,
      sur chacun de ses evenements.
  [4] la replique qui ne tient pas sur UNE ligne retombe sur le karaoke `\\k`
      et le DIT (`info["word_anim_skipped"]`) — trop de CARACTERES, ou trop
      de PIXELS : 28 « M » tiennent dans les 30 caracteres permis et debordent
      quand meme (280 px pour 226,4 utiles).
  [5] MIROIR a l'image : `align` decide d'ou PART la ligne — barycentre des
      pixels clairs, gauche < centre < droite.
  [6] emoji par mot-cle : `emoji_hints` rend, pour chaque mot-cle reconnu, le
      temps du MOT et un PNG qui existe vraiment sous app/assets/emoji, et il
      suit l'ELISION (« l'or », « d'or ») ;
  [7] la meme chose par la route POST /api/subtitles/emoji-hints.
  [8] un mot cale APRES la fin de la replique DISPARAISSAIT du rendu (61 px
      contre 174 mesures a 1,0 s) : on retombe sur le karaoke, et on le DIT.
  [9] ce qui est PERDU volontairement, et doit etre dit : le fondu d'entree du
      BLOC ne se pose pas sur des evenements de mots ; « couleur » ne fait
      rien quand le karaoke est eteint ; sans PIL la mesure est impossible.

CE QUE CE BANC N'AFFIRME PAS. Le `glow` n'est pas mesure A L'IMAGE : la
surface d'un contour qui grossit puis retombe se confond avec celle du
rebond, et le banc ne saurait pas dire lequel des deux il regarde. Seule sa
BALISE est verifiee — section [3], et c'est tout ce qui est affirme de lui.
La chip du bundle n'est pas exercee ici : c'est test_montage_bundle.py qui
compte ses ancres. Et le rapport de `_subs_ass` n'est lu QUE par ces bancs :
en production son seul lecteur est une ligne de journal — le panneau
n'apprend rien d'un rebond qui n'a pas eu lieu. Reste ASSUME.

HORS PERIMETRE, constate : `POST /api/subtitles/export?format=ass` ne connait
pas `word_anim`, donc le .ass TELECHARGE n'est pas celui qui est grave. Ce
n'est pas une regression de P2 — cette route ignore deja `anim` de la meme
facon ; la corriger toucherait le vocabulaire d'export, qui n'est pas du
ressort de cette tache.

LA REGLE DES ASSERTIONS NEGATIVES, PASSEE SUR CE BANC LE 05/09/2026. Elle
vient de l'en-tete de test_montage_media.py : un TEMOIN DISTINGUABLE, ou le
repli VIDE d'une garde, SE RETOURNE CONTRE TOUTE NEGATION. `a != b`,
`not (…)`, `x not in y`, `== []`, `== ""`, `is None` sont VRAIS PAR
CONSTRUCTION entre deux temoins comme sur un `{}` ou une `[]` de repli : la
ligne verdit sans avoir rien mesure. LA REGLE : toute assertion negative doit
d'abord exiger que ses operandes SOIENT ce qu'ils pretendent etre, et
seulement ensuite les comparer.

  L'ETAT VIDE DE CE BANC, DEUX LEVIERS :
      & $PY scratchpad/vide2.py ass    tests/test_subs_animes.py
      & $PY scratchpad/vide2.py api503 tests/test_subs_animes.py
  Le premier relit VIDE tout fichier `.ass` — la fixture ECRITE mais SANS
  CONTENU, c'est-a-dire un `_subs_ass` qui n'emettrait plus le moindre
  evenement. Le second rend toute route `/api/…` en 503.
  MESURE, PREMIER LEVIER — avant : 54/65 vertes, dont CINQ qui lisaient un
  ASS de zero octet. Apres : 49/65. Les cinq :
    * sans_wordAnim_ass_inchange — exige le repli karaoke (`\k`) d'abord ;
    * glow_ne_rebondit_pas — exige la balise du glow, mesuree par la ligne
      qui la precede et REPRISE plutot que supposee ;
    * longue_replique_sans_pos — exige le `\k` du repli ;
    * fondu_absent_des_evenements_de_mots — elle NOMME les evenements de
      mots : on exige qu'il y en ait (`\pos(`) ;
    * couleur_sans_karaoke_ne_fait_rien — DEUX negations et aucune autre
      ligne ne lit `tK` : on exige l'unique evenement ET le texte de la
      replique avant de nier `\k` et `\pos(`.
  Les quatre autres lignes de la meme famille (couleur_ne_pose_aucun_mot,
  trop_large_sans_pos, calage_casse_retombe_en_karaoke,
  sans_mesure_retombe_en_karaoke) portaient DEJA leur `"\k" in t` : elles
  rougissent seules, et c'est la forme qui a servi de modele aux cinq autres.
  MESURE, SECOND LEVIER — une seule ligne restait verte : route_ne_modifie
  _rien, dont les deux negations etaient vraies du `{}` de repli. Elle exige
  desormais la reponse mesuree par `route_deux_suggestions` (60/5 apres,
  contre 61/4 avant). Croisement automatique : ZERO reste verte.
  ET UN `.json()` NU DE MOINS, cote pistes : voir les bancs
  test_montage_pistes_rendu.py et test_montage_pistes_dyn.py, meme journee,
  meme parade.
"""
import json, os, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp2_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand   # la commande sous test lance un "ffmpeg" NU : il faut le PATH
    print(f"SKIP: {name} introuvable — le banc-miroir ne peut rien mesurer")
    sys.exit(0)


FF, FP = _exe("ffmpeg"), _exe("ffprobe")
from PIL import Image                                   # noqa: E402
from app.services import subtitle_service as S          # noqa: E402
from app.services import subtitle_ui as SU              # noqa: E402
from app.services import montage_service as M           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

def fixture(label, cmd):
    """Une source qui ne se cree pas doit mourir ICI (meme garde-fou que P0)."""
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture {label} : {r.stderr[-400:]}")
        sys.exit(1)

V1 = os.path.join(TMP, "v1.mp4")
fixture("v1", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
               "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])

def frame(path, t):
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    sh([FF, "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png])
    return Image.open(png).convert("RGB")

def mean_rgb(im, box=None):
    if box: im = im.crop(box)
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 1) for i in range(3))

def v1_spec():
    return [{"path": V1, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
             "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]


UI = {"font": "Anton", "size": 52, "upper": True, "color": "#ffffff", "outOn": True, "outW": 4,
      "karOn": True, "karColor": "#ffd23f", "karMode": "fill", "anim": "none", "wordAnim": "rebond",
      "align": "center", "valign": "bottom", "marginV": 20, "width": 84, "maxChars": 30}
SEG = [{"start": 0.5, "end": 2.5, "text": "SOUS LA SURFACE",
        "words": [{"w": "SOUS", "start": 0.5, "end": 1.1}, {"w": "LA", "start": 1.1, "end": 1.5},
                  {"w": "SURFACE", "start": 1.5, "end": 2.5}]}]

print("\n[1] l'ASS porte un événement par mot, positionné et animé")
p, info = M._subs_ass({"style": UI, "segments": SEG}, (270, 480), "anim1")
txt = p.read_text(encoding="utf-8"); ev = [l for l in txt.splitlines() if l.startswith("Dialogue:")]
check("trois_evenements_mots", len(ev) == 3, str(len(ev)))
check("chaque_mot_pose", all("\\pos(" in l for l in ev))
check("chaque_mot_rebondit", all("\\t(0,120,\\fscx115\\fscy115)" in l for l in ev))
# le `if len(ev) > 1` n'affaiblit rien : sans deuxieme evenement l'assertion
# est FAUSSE (chaine vide != "0:00:01.10"). Il evite seulement qu'un banc rouge
# meure sur une IndexError avant d'avoir dit tout ce qu'il avait a dire.
check("mot_2_commence_a_1s10",
      (ev[1].split(",")[1] if len(ev) > 1 else "") == "0:00:01.10",
      ev[1][:40] if len(ev) > 1 else f"{len(ev)} événement(s)")
check("info_word_anim", info.get("word_anim") == "rebond")

print("\n[2] miroir : un mot SEUL est plus GROS au sommet du rebond (130 ms) qu'une fois posé (400 ms)")
SEG1 = [{"start": 0.5, "end": 2.5, "text": "SURFACE", "words": [{"w": "SURFACE", "start": 0.5, "end": 2.5}]}]
p1, _ = M._subs_ass({"style": UI, "segments": SEG1}, (270, 480), "anim2")
out = os.path.join(TMP, "anim.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False,
                                  duration_master=False, preview=False, out=out, subs_ass=p1)
r = sh(cmd); check("anim_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
def text_px(t):
    im = frame(out, t).convert("L"); w, h = im.size
    band = im.crop((0, int(h * .55), w, h)); return sum(1 for v in band.getdata() if v > 200)
a, b = text_px(0.63), text_px(0.9)
# CHIFFRES MESURES sur CETTE copie, trois rendus identiques (ffmpeg embarque,
# Anton, 270x480, un mot seul) : 222 px eclaires a 130 ms contre 191 une fois
# pose, soit 1,1623. Sans animation les deux valent 200 (mesure du banc ROUGE,
# avant implementation) : le rapport est alors 1,0000. Le seuil retenu est
# 1,10 : la mesure le depasse de 5,7 % (1,1623/1,10) et le cas « rien ne
# bouge » reste 10 % en dessous. Ce n'est PAS le milieu des deux — il vaut
# 1,0812 : le seuil est place a 61,6 % du chemin, volontairement plus pres de
# la mesure que du repos. Le 1,15 qu'ecrivait le plan tenait a 1,1 % pres, et ses
# valeurs (« ~113 % », « aire x1,28 ») etaient une attente, pas une mesure :
# 113,5 % est bien l'echelle demandee a 130 ms, mais la surface d'un texte
# contoure ne suit pas le carre de l'echelle.
print(f"      mesure : {a} px à 130 ms, {b} px à 400 ms, rapport {a / b:.4f}")
check("rebond_plus_gros_au_debut", a > b * 1.10, f"{a} px à 130 ms, {b} px à 400 ms")
# UNE NEGATION SUR UN TEXTE D'ASS DOIT D'ABORD EXIGER UN ASS. MESURE le
# 05/09/2026 (banc relance avec tout `.ass` relu VIDE, `scratchpad/vide2.py
# ass`) : cette ligne etait VERTE sur un fichier de zero octet. Le repli
# karaoke est ce que `wordAnim="none"` DOIT produire — on l'exige, puis on
# nie le `\pos`. Meme forme que `couleur_ne_pose_aucun_mot` plus bas.
_t0 = M._subs_ass({"style": dict(UI, wordAnim="none"), "segments": SEG},
                  (270, 480), "anim0")[0].read_text(encoding="utf-8")
check("sans_wordAnim_ass_inchange", "\\k" in _t0 and "\\pos(" not in _t0,
      "%d o" % len(_t0))

print("\n[3] le vocabulaire du panneau, et la balise du glow")
# « couleur » est la valeur que M10 envoie PAR DÉFAUT. Rien ne l'exerçait :
# elle doit retomber sur le karaoké `\k`, donc sur AUCUN `\pos`.
check("ui_couleur_est_none", SU.ui_word_anim({"wordAnim": "couleur"}) == "none",
      SU.ui_word_anim({"wordAnim": "couleur"}))
check("ui_inconnu_est_none", SU.ui_word_anim({"wordAnim": "zigzag"}) == "none",
      SU.ui_word_anim({"wordAnim": "zigzag"}))
check("ui_absent_est_none",
      SU.ui_word_anim({}) == "none" and SU.ui_word_anim(None) == "none",
      f"{SU.ui_word_anim({})} / {SU.ui_word_anim(None)}")
check("ui_rebond_et_glow_se_rendent",
      SU.ui_word_anim({"wordAnim": "rebond"}) == "rebond"
      and SU.ui_word_anim({"wordAnim": "glow"}) == "glow",
      f'{SU.ui_word_anim({"wordAnim": "rebond"})} / '
      f'{SU.ui_word_anim({"wordAnim": "glow"})}')
check("ui_vocabulaire_complet",
      sorted(SU.UI_WORD_ANIMS) == ["couleur", "glow", "none", "rebond"],
      str(sorted(SU.UI_WORD_ANIMS)))
# Les deux lignes ci-dessus comparent chacune à un LITTÉRAL recopié : elles ne
# voient donc pas les deux vocabulaires DIVERGER. Ajouter "shake" à
# WORD_ANIMS + _WORD_TAGS sans l'offrir au panneau les laissait vertes toutes
# les deux. On compare donc les ensembles ENTRE EUX — moteur, panneau, chip.
check("vocabulaires_panneau_et_moteur_accordes",
      set(SU.UI_WORD_ANIMS.values()) == set(S.WORD_ANIMS),
      f"panneau→{sorted(set(SU.UI_WORD_ANIMS.values()))} "
      f"moteur→{sorted(S.WORD_ANIMS)}")
check("chaque_anim_moteur_a_sa_balise",
      set(S._WORD_TAGS) | {"none"} == set(S.WORD_ANIMS),
      f"balises→{sorted(S._WORD_TAGS)} moteur→{sorted(S.WORD_ANIMS)}")
# et la CHIP du bundle, lue dans sa source : une valeur que le moteur connaît
# mais que la chip n'offre pas est inatteignable depuis l'écran.
_LAYER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "frontend", "patches", "montage.js")
_chip = set(re.findall(r'\{v:"([a-z]+)"',
                       open(_LAYER, encoding="utf-8").read()))
check("chip_offre_le_vocabulaire_du_panneau",
      _chip == set(SU.UI_WORD_ANIMS) - {"none"},
      f"chip→{sorted(_chip)} panneau→{sorted(set(SU.UI_WORD_ANIMS) - {'none'})}")
pC, infoC = M._subs_ass({"style": dict(UI, wordAnim="couleur"),
                         "segments": SEG}, (270, 480), "anim4")
tC = pC.read_text(encoding="utf-8")
check("couleur_ne_pose_aucun_mot", "\\pos(" not in tC and "\\k" in tC)
check("couleur_dite_none_dans_info", infoC.get("word_anim") == "none",
      str(infoC.get("word_anim")))
pG, infoG = M._subs_ass({"style": dict(UI, wordAnim="glow"),
                         "segments": SEG}, (270, 480), "anim5")
tG = pG.read_text(encoding="utf-8")
evG = [l for l in tG.splitlines() if l.startswith("Dialogue:")]
check("glow_un_evenement_par_mot", len(evG) == 3, str(len(evG)))
_glow_pose = bool(evG) and all(
    "\\bord1\\t(0,160,\\bord6)\\t(160,320,\\bord2)" in l for l in evG)
check("glow_pose_sa_balise", _glow_pose,
      evG[0][:90] if evG else "aucun événement")
# le glow n'emprunte RIEN au rebond : sans cette ligne, un _WORD_TAGS qui
# rendrait la balise du rebond pour les deux passerait le banc.
# meme piege, meme remede : un ASS vide ne rebondit pas non plus. La balise
# du glow, mesuree juste au-dessus, est la condition — reprise ici plutot que
# supposee.
check("glow_ne_rebondit_pas", _glow_pose and "\\fscx115" not in tG,
      "%d o, %d événement(s)" % (len(tG), len(evG)))
check("glow_dit_son_nom", infoG.get("word_anim") == "glow",
      str(infoG.get("word_anim")))

print("\n[4] une réplique qui ne tient pas sur UNE ligne retombe sur le karaoké — et le DIT")
LONG = [{"start": 0.5, "end": 4.0,
         "text": "SOUS LA SURFACE LA MARÉE MONTE ENCORE PLUS HAUT QUE HIER",
         "words": None}]
pL, infoL = M._subs_ass({"style": UI, "segments": LONG}, (270, 480), "anim3")
tL = pL.read_text(encoding="utf-8")
evL = [l for l in tL.splitlines() if l.startswith("Dialogue:")]
check("longue_replique_un_seul_evenement", len(evL) == 1, str(len(evL)))
# le repli karaoke est la condition du « sans \pos » : sans lui, un ASS vide
# passerait. MESURE (ASS relus vides) : verte.
check("longue_replique_sans_pos", "\\k" in tL and "\\pos(" not in tL,
      "%d o" % len(tL))
check("longue_replique_en_karaoke", "\\k" in tL)
check("longue_replique_dite_dans_info", infoL.get("word_anim_skipped") == [0],
      str(infoL.get("word_anim_skipped")))
check("longue_replique_dite_dans_unsupported",
      any("wordAnim:" in u for u in infoL.get("unsupported") or []),
      str(infoL.get("unsupported")))
# et le compteur de l'autre sens : la replique COURTE, elle, est bien animee
check("courte_replique_comptee", info.get("word_segments") == 1,
      str(info.get("word_segments")))
# Le compte de CARACTÈRES ne suffisait pas : MESURÉ, 28 « M » en Anton 52 font
# 280 px pour 226,4 px utiles (marges du style à width:84), passaient le seuil
# de 30 caractères, et le premier mot sortait à \pos(-5,384) — hors cadre à
# gauche. 29 M → 290 px et 30 M → 300 px faisaient de même.
LARGE = [{"start": 0.5, "end": 2.5, "text": "M" * 28,
          "words": [{"w": "M" * 28, "start": 0.5, "end": 2.5}]}]
pW, infoW = M._subs_ass({"style": UI, "segments": LARGE}, (270, 480), "anim3b")
tW = pW.read_text(encoding="utf-8")
check("trop_large_sans_pos", "\\pos(" not in tW and "\\k" in tW)
check("trop_large_dit_dans_info", infoW.get("word_anim_skipped") == [0],
      str(infoW.get("word_anim_skipped")))
_stW = SU.ui_to_style(UI, (270, 480))
_pxW = S._measure_px("M" * 28, _stW, 480 / 1080.0)
_utile = 270 - 2 * _stW["margin_h"] * (480 / 1080.0)
print(f"      mesure : 28 « M » = {_pxW:.1f} px pour {_utile:.1f} px utiles, "
      f"soit {len('M' * 28)} caractères sur {_stW['chars_per_line']} permis")

print("\n[5] miroir : `align` décide d'où part la ligne — mesuré au barycentre des pixels")
def centroid_x(path, t):
    im = frame(path, t).convert("L"); w, h = im.size
    band = im.crop((0, int(h * .55), w, h))
    px = list(band.getdata()); bw = band.size[0]
    s = n = 0
    for i, v in enumerate(px):
        if v > 200:
            s += i % bw; n += 1
    return (s / float(n)) if n else -1.0
def render_align(al, stem):
    pa, _ = M._subs_ass({"style": dict(UI, align=al), "segments": SEG1}, (270, 480), stem)
    o = os.path.join(TMP, stem + ".mp4")
    c, _ = M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={},
                                    ducking=False, duration_master=False, preview=False,
                                    out=o, subs_ass=pa)
    rr = sh(c)
    check(f"align_{al}_ffmpeg_ok", rr.returncode == 0, rr.stderr[-300:])
    return centroid_x(o, 0.9)
cxl, cxr = render_align("left", "animL"), render_align("right", "animR")
cxc = centroid_x(out, 0.9)          # le rendu centré de la section [2]
print(f"      barycentres x (canevas 270 px) : gauche {cxl:.1f} · centre {cxc:.1f} · droite {cxr:.1f}")
check("align_gauche_puis_centre_puis_droite", cxl < cxc < cxr, f"{cxl:.1f} {cxc:.1f} {cxr:.1f}")
check("align_centre_est_centre", abs(cxc - 135.0) < 8.0, f"{cxc:.1f} pour 135 attendu")
# INTERLETTRAGE. `_measure_px(" ")` mesure UN caractère, donc ZÉRO intervalle :
# il n'ajoute aucun `spacing`, alors que l'espace d'une vraie ligne en porte
# DEUX. MESURÉ à tracking=3 : somme des mots + 2 espaces = 88,50 px quand la
# même chaîne mesurée d'un coup en fait 91,50 — 3,00 px perdus, donc la ligne
# posée mot à mot était plus SERRÉE que celle que libass dessine. Nul au défaut
# (tracking=0 : 81,00 des deux côtés), mais le panneau règle ce curseur.
_sc = 480 / 1080.0
_st3 = SU.ui_to_style(dict(UI, tracking=3), (270, 480))
_mots = ["SOUS", "LA", "SURFACE"]
_somme = sum(S._measure_px(m, _st3, _sc) for m in _mots) + S._word_space_px(_st3, _sc) * 2
_dun_coup = S._measure_px(" ".join(_mots), _st3, _sc)
print(f"      interlettrage 3 : mot à mot {_somme:.2f} px · d'un coup {_dun_coup:.2f} px")
check("interlettrage_ne_derive_pas", abs(_somme - _dun_coup) < 0.01,
      f"{_somme:.2f} px mot à mot contre {_dun_coup:.2f} px d'un coup")

print("\n[6] emoji par mot-clé : le temps du MOT, un PNG qui existe")
HS = S.emoji_hints([{"text": "le feu sacré", "start": 1.0, "end": 2.0,
                     "words": [{"w": "le", "start": 1.0, "end": 1.2},
                               {"w": "feu", "start": 1.2, "end": 1.6},
                               {"w": "sacré", "start": 1.6, "end": 2.0}]}])
check("un_seul_emoji_suggere", len(HS) == 1, str(HS))
check("emoji_cale_sur_le_mot", bool(HS) and HS[0]["t"] == 1.2, str(HS[:1]))
check("emoji_png_existe", bool(HS) and os.path.isfile(HS[0]["png"]),
      str(HS[0]["png"]) if HS else "-")
check("emoji_url_servie", bool(HS) and HS[0]["url"] == "/emoji/1f525.png",
      str(HS[0]["url"]) if HS else "-")
# accents et ponctuation : « Fusée ! » et « fusee » tombent au même endroit,
# sinon la suggestion raterait un mot sur deux dans un texte réel.
HS2 = S.emoji_hints([{"text": "Fusée ! fusee", "start": 0.0, "end": 2.0,
                      "words": [{"w": "Fusée", "start": 0.0, "end": 0.5},
                                {"w": "!", "start": 0.5, "end": 0.6},
                                {"w": "fusee", "start": 0.6, "end": 2.0}]}])
check("emoji_insensible_accents_ponctuation",
      [h["file"] for h in HS2] == ["1f680", "1f680"], str(HS2))
check("emoji_manifeste_lu", len(S.emoji_manifest()) > 100, str(len(S.emoji_manifest())))
check("emoji_dossier_est_celui_des_routes",
      S.emoji_dir().name == "emoji" and S.emoji_dir().parent.name == "assets"
      and S.emoji_dir().parent.parent.name == "app", str(S.emoji_dir()))
# ÉLISION. `_fold` ne retirait la ponctuation qu'aux EXTRÉMITÉS : l'apostrophe
# interne restait, et la forme la PLUS COURANTE du nom était manquée. MESURÉ :
# « la ruée vers l'or » et « une pièce d'or » ne proposaient RIEN, quand « or
# il se trouve que » proposait la pièce. Des deux erreurs, le silence coûtait
# plus cher que le faux positif — celui-ci se voit et se supprime d'un clic.
def _hint_files(phrase):
    mots, t, ws = phrase.split(), 0.0, []
    for m in mots:
        ws.append({"w": m, "start": round(t, 2), "end": round(t + 0.3, 2)})
        t += 0.3
    return [h["file"] for h in S.emoji_hints(
        [{"text": phrase, "start": 0.0, "end": round(t, 2), "words": ws}])]
check("emoji_suit_l_elision",
      _hint_files("la ruée vers l'or") == ["1fa99"]
      and _hint_files("une pièce d'or") == ["1fa99"]
      and _hint_files("l’or du temps") == ["1fa99"],
      f'{_hint_files("la ruée vers l\'or")} / {_hint_files("une pièce d\'or")} '
      f'/ {_hint_files("l’or du temps")}')
# et l'élision ne mange PAS un mot qui commence par les mêmes lettres :
# « aujourd'hui » n'est pas une élision, « cl'or » non plus.
check("elision_ne_mord_pas_sur_le_reste",
      S._fold("aujourd'hui") == "aujourd'hui" and S._fold("cl'or") == "cl'or"
      and S._fold("l'or") == "or" and S._fold("l’or") == "or",
      f'{S._fold("aujourd\'hui")} / {S._fold("cl\'or")} / {S._fold("l\'or")}')

print("\n[7] par la ROUTE POST /api/subtitles/emoji-hints")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
with TestClient(app) as cli:
    rr = cli.post("/api/subtitles/emoji-hints", json={"segments": [
        {"start": 0.0, "end": 2.0, "text": "la vague et la fusée",
         "words": [{"w": "la", "start": 0.0, "end": 0.2},
                   {"w": "vague", "start": 0.2, "end": 0.8},
                   {"w": "et", "start": 0.8, "end": 1.0},
                   {"w": "la", "start": 1.0, "end": 1.2},
                   {"w": "fusée", "start": 1.2, "end": 2.0}]}]})
    check("route_200", rr.status_code == 200, rr.text[:200])
    dd = rr.json() if rr.status_code == 200 else {}
    check("route_deux_suggestions", dd.get("count") == 2, str(dd)[:200])
    check("route_dans_l_ordre_du_temps",
          [h["t"] for h in dd.get("hints") or []] == [0.2, 1.2],
          str([h.get("t") for h in dd.get("hints") or []]))
    # meme piege, meme remede que dans test_montage_texte.py : `dd` vaut `{}`
    # des que la route n'a pas rendu 200, et les deux negations sont alors
    # vraies. MESURE le 05/09/2026 (`scratchpad/vide2.py api503`) : VERTE.
    check("route_ne_modifie_rien",
          dd.get("count") == 2
          and "segments" not in dd and "clips" not in dd,
          str(sorted(dd.keys())))
    # `count: 0` seul ne distingue pas « aucun mot-clé dans ce texte » de
    # « manifeste illisible » — et le bouton accusait alors le texte de
    # l'utilisateur. `manifest` sépare les deux cas.
    check("route_dit_la_taille_du_manifeste",
          dd.get("manifest") == len(S.emoji_manifest()) > 100,
          str(dd.get("manifest")))

print("\n[8] un mot calé APRÈS la fin de la réplique : il DISPARAÎTRAIT du rendu")
# MESURÉ, trois rendus identiques : le second mot, ramené par _normalize_words
# sur `end`, sortait en événement 2,00→2,00 que libass ne dessine pas — 61 px
# éclairés à 1,0 s en « rebond » contre 174 en karaoké. Et le rapport disait
# word_segments:1, word_anim_skipped:[] : tout allait bien.
CASSE = [{"start": 0.0, "end": 2.0, "text": "UN DEUX",
          "words": [{"w": "UN", "start": 0.0, "end": 0.5},
                    {"w": "DEUX", "start": 9.0, "end": 9.5}]}]
pB, infoB = M._subs_ass({"style": UI, "segments": CASSE}, (270, 480), "anim6")
tB = pB.read_text(encoding="utf-8")
check("calage_casse_retombe_en_karaoke", "\\pos(" not in tB and "\\k" in tB)
check("calage_casse_dit_dans_info", infoB.get("word_anim_broken") == [0],
      str(infoB.get("word_anim_broken")))
check("calage_casse_pas_compte_comme_anime", infoB.get("word_segments") == 0,
      str(infoB.get("word_segments")))
check("calage_casse_dit_dans_unsupported",
      any("commence après la fin" in u for u in infoB.get("unsupported") or []),
      str(infoB.get("unsupported")))
# MIROIR : la ligne entière est de nouveau à l'écran à 1,0 s.
outB = os.path.join(TMP, "casse.mp4")
cmdB, _ = M._build_montage_command(v1_spec(), [], [], None, w=270, h=480, fps=30, mix_db={},
                                   ducking=False, duration_master=False, preview=False,
                                   out=outB, subs_ass=pB)
rB = sh(cmdB); check("calage_casse_ffmpeg_ok", rB.returncode == 0, rB.stderr[-300:])
def band_px(path, t):
    im = frame(path, t).convert("L"); w, h = im.size
    band = im.crop((0, int(h * .55), w, h)); return sum(1 for v in band.getdata() if v > 200)
nB = band_px(outB, 1.0)
print(f"      mesure : {nB} px à 1,0 s (61 avant le correctif, 174 attendus en karaoké)")
check("calage_casse_ligne_entiere_a_l_ecran", nB > 120, f"{nB} px à 1,0 s")

print("\n[9] ce qui est PERDU et doit être dit : fondu du bloc, couleur sans karaoké, mesure impossible")
# I1 — l'animation d'ENTRÉE du bloc ne se pose pas sur les événements de mots.
# MESURÉ : `anim="fade"` + rebond produit un ASS SANS le moindre \fad, quand le
# même style en karaoké en porte un. On ne le grave pas ; on le DIT.
pA, infoA = M._subs_ass({"style": dict(UI, anim="fade"), "segments": SEG},
                        (270, 480), "anim7")
# CE QUE CETTE LIGNE NOMME, ce sont les EVENEMENTS DE MOTS : il faut donc
# qu'il y en ait. MESURE (ASS relus vides) : verte sur zero octet, c'est-a-dire
# sur un fichier sans le moindre evenement de mot.
_tA = pA.read_text(encoding="utf-8")
check("fondu_absent_des_evenements_de_mots",
      "\\pos(" in _tA and "\\fad(" not in _tA, "%d o" % len(_tA))
check("fondu_present_en_karaoke",
      "\\fad(" in M._subs_ass({"style": dict(UI, anim="fade", wordAnim="couleur"),
                               "segments": SEG}, (270, 480), "anim7b")[0]
      .read_text(encoding="utf-8"))
check("fondu_perdu_dit_dans_unsupported",
      any(u.startswith("anim:") for u in infoA.get("unsupported") or []),
      str(infoA.get("unsupported")))
# I5 — « couleur » EST le karaoké : karaoké éteint, elle ne fait plus rien.
# MESURÉ : ni \k, ni \pos, word_anim = none, et unsupported était muet.
pK, infoK = M._subs_ass({"style": dict(UI, karOn=False, wordAnim="couleur"),
                         "segments": SEG}, (270, 480), "anim8")
tK = pK.read_text(encoding="utf-8")
# LES DEUX CONDITIONS SONT DES NEGATIONS — le cas le plus expose de tous, et
# la seule ligne qui lise `tK`. MESURE (ASS relus vides) : verte. On exige
# donc que l'ASS porte bien ses evenements ET le texte de la replique, avant
# de dire que ni le karaoke ni le placement par mot n'y sont.
_evK = [l for l in tK.splitlines() if l.startswith("Dialogue:")]
check("couleur_sans_karaoke_ne_fait_rien",
      len(_evK) == 1 and "SOUS LA SURFACE" in tK
      and "\\k" not in tK and "\\pos(" not in tK,
      "%d événement(s), %d o" % (len(_evK), len(tK)))
check("couleur_sans_karaoke_dit_dans_unsupported",
      any("EST le karaoké" in u for u in infoK.get("unsupported") or []),
      str(infoK.get("unsupported")))
# I3 — le repli « mesure impossible » : on neutralise _measure_px, comme le
# ferait une machine sans PIL ou sans le fichier de fonte.
_orig_measure = S._measure_px
try:
    S._measure_px = lambda *a, **k: None
    pM, infoM = M._subs_ass({"style": UI, "segments": SEG}, (270, 480), "anim9")
finally:
    S._measure_px = _orig_measure
tM = pM.read_text(encoding="utf-8")
check("sans_mesure_retombe_en_karaoke", "\\pos(" not in tM and "\\k" in tM)
check("sans_mesure_dit_les_index", infoM.get("word_anim_unmeasured") == [0],
      str(infoM.get("word_anim_unmeasured")))
check("sans_mesure_dit_dans_unsupported",
      any("mesure impossible" in u for u in infoM.get("unsupported") or []),
      str(infoM.get("unsupported")))
check("sans_mesure_rien_compte_comme_anime", infoM.get("word_segments") == 0,
      str(infoM.get("word_segments")))
# la neutralisation est bien DÉFAITE : sans ce contrôle, une fuite ferait
# passer les sections suivantes pour des mesures alors qu'elles ne mesurent rien.
check("mesure_retablie_apres_le_repli",
      S._measure_px("SURFACE", SU.ui_to_style(UI, (270, 480)), 480 / 1080.0) is not None)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
