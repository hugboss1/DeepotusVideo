# -*- coding: utf-8 -*-
"""P1 — MIROIR DU BUNDLE LIVRE. On lit le fichier que l'application charge
vraiment (frontend/dist/assets/index-BEOJX8L5.js), pas la source du patcher :
c'est la seule facon de voir qu'une section a ete effacee par un maillon
amont relance seul — le mode de panne qui a deja coute vingt-deux correctifs
a ce depot.

Quatre familles de mesures :
  [1] le bloc `montage` est present UNE fois, et chacun des couples
      ancre -> remplacement de scripts/patch_bundle_montage.py (importe par
      importlib : aucune copie, aucune derive possible) est retrouve UNE fois
      dans le bundle. Quand le remplacement ne REPREND pas l'ancre, elle doit
      avoir DISPARU : sinon le patch a ete applique deux fois, ou pas du tout
      au bon endroit.
  [2] `node --check` sur le bundle : la chaine de patchs n'a pas casse la
      syntaxe.
  [3] le CŒUR de la couche EXECUTE sous node. On ecrit un shim
      (var window={}; var SVM_TRACK_BUS={}; + montage.js) puis on le lance
      par FICHIER — JAMAIS `node -e` : la ligne de commande Windows plafonne
      a 32 767 caracteres et montage.js la depasserait tot ou tard, avec un
      echec qui ne ressemble a rien.
  [4] LE CABLAGE de l'ecran EXECUTE, ajoute le 05/09/2026 (section [3-bis]).
      Le cœur pur etait couvert a fond ; le FIL entre ce cœur et l'ecran ne
      l'etait par RIEN — `addAsset`, `nudge`, `up()` et l'`onSet` du
      transport ne tournaient sous aucun banc, et NEUF mutations qui
      remettent le bug rapporte par l'utilisateur laissaient le compte a
      504/0. Un second shim EXTRAIT DU BUNDLE LIVRE, mot pour mot, les
      quatre morceaux de cablage (plus `defaultLen`, `svmShort`,
      `svmSpeedOf`, `trackKind`, `svmKbSelClip`) et les joue avec les refs
      et les setters de l'ecran bouchonnes. Les neuf rougissent.

Run : & $PY tests/test_montage_bundle.py   (depuis backend/)

COMPTE DE REFERENCE, 05/09/2026 (fin de journee, apres M9c) : 536 lignes.
Sans `node` sur le PATH, 534 — les deux `*_rend_un_objet_json` vivent dans la
branche « node a tourne » et ne sont pas emises, c'est par CONSTRUCTION et
non par accident. Il en valait 524 le matin : M9c en apporte DOUZE, dont TROIS
que la boucle sur `P.PATCHES` emet toute seule pour la nouvelle section
(_remplace, _ancre_consommee, couche_ne_cite_pas_l_ancre_de_).

LA REGLE DES ASSERTIONS NEGATIVES, PASSEE SUR CE BANC LE 05/09/2026. Elle
vient de l'en-tete de test_montage_media.py : un TEMOIN DISTINGUABLE, ou le
repli VIDE d'une garde, SE RETOURNE CONTRE TOUTE NEGATION. `a != b`,
`not (…)`, `x not in y`, `== []`, `== ""`, `is None` sont VRAIS PAR
CONSTRUCTION entre deux temoins comme sur un `{}` ou une `[]` de repli : la
ligne verdit sans avoir rien mesure. LA REGLE : toute assertion negative doit
d'abord exiger que ses operandes SOIENT ce qu'ils pretendent etre, et
seulement ensuite les comparer.

  LA FAUTE N°6 D'ABORD. Ce banc appelait `node` NU trois fois (deux
  `node --check`, puis le shim). MESURE le 05/09/2026 avec
  `PATH=C:/Windows/System32;C:/Windows` : FileNotFoundError au PREMIER
  `node --check`, 238 des 326 lignes imprimees, AUCUNE ligne de compte,
  QUATRE-VINGT-HUIT assertions emportees en silence. La garde `NODE()` rend
  un sous-processus-temoin (`returncode` negatif, `stdout` vide, `stderr`
  porteur du temoin NUMEROTE) ; meme relance : 244/82, et LE COMPTE EST
  IMPRIME. Une ligne `aucun_appel_n_a_plante` a ete ajoutee en queue, comme
  dans les trois autres bancs de la famille — c'est elle qui fait passer le
  compte de reference de 326 a 327.
  LES TROIS CHIFFRES CI-DESSUS (326, 244/82, 241/85) SONT CEUX DU CHANTIER
  P10-P11 ET NE SE REPRODUISENT PLUS TELS QUELS : le banc a grossi depuis.
  Meme relance aujourd'hui, `PATH=C:/Windows/System32;C:/Windows` : 337/197
  sur 534, et LE COMPTE EST IMPRIME — c'est CELA que la garde protege, pas
  un chiffre. (325/197 sur 522 le matin, avant M9c : les douze lignes de la
  section vivent hors de la branche node, elles verdissent donc les deux
  fois.)
  L'ETAT VIDE ET LES TROIS REPAREES :
      PATH=C:/Windows/System32;C:/Windows & $PY tests/test_montage_bundle.py
  `d` retombe sur le dict VIDE des que node ne rend pas d'objet JSON, et
  `{}.get(x)` vaut `None` : les trois lignes ecrites `d.get(x) is None`
  etaient VERTES sans qu'une instruction de JS ait tourne —
  js_from_sans_v1_refuse, js_from_vide_refuse, js_bouton_null_sans
  _etalonnage. Elles exigent desormais que la CLE SOIT LA (`"x" in d`), ce
  que le shim garantit puisqu'il l'ecrit toujours, fut-ce a `null`.
  PREUVE : meme relance sans node, 244/82 avant, 241/85 apres. Croisement
  automatique (scratchpad/croise.py) sur les ~90 lignes qui lisent `d` :
  ZERO reste verte.
  DECLARE, ET NON MESURE : les ~230 lignes qui lisent `s` (le bundle livre)
  ou `P.R_*` (le patcher) ne sont pas couvertes par ce levier — un bundle
  VIDE les emporterait autrement. Le banc refuse de partir si l'un des cinq
  fichiers manque (`fichier_absent`, 0/1) ; il ne dit rien d'un fichier
  present mais vide. C'est une dette assumee, ecrite plutot que sous-entendue.
"""
import importlib.util, json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
LAYER = ROOT / "frontend" / "patches" / "montage.js"
PATCHER = ROOT / "scripts" / "patch_bundle_montage.py"
HTML = ROOT / "frontend" / "dist" / "index.html"
CSS = ROOT / "frontend" / "dist" / "shared" / "montage.css"
TMP = tempfile.mkdtemp(prefix="dzmb_")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


_plantages = 0


def temoin(e):
    """TEMOIN d'un appel qui a LEVE — meme parade que test_montage_sources.py
    et test_montage_remplacer.py. NUMEROTE (deux echecs ne se valent jamais)
    et DISTINGUABLE (jamais `None`, jamais `""`)."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


class _NodeEchec:
    """Sous-processus `node` qui n'a pas pu S'EXECUTER. `returncode` NEGATIF
    (jamais 0), `stdout` VIDE, `stderr` porteur du temoin."""

    def __init__(self, t):
        self.returncode = -1
        self.stdout = ""
        self.stderr = t


def NODE(args, **kw):
    """`subprocess.run` garde. MESURE le 05/09/2026, banc relance avec
    `PATH=C:/Windows/System32;C:/Windows` : sans cette garde le banc MOURAIT
    au premier `node --check` (l. 1210) — 238 des 326 lignes imprimees,
    AUCUNE ligne de compte, 88 assertions emportees EN SILENCE. Faute n°6."""
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", **kw)
    except Exception as e:
        t = temoin(e)
        print(f"  ----  node a leve : {t}")
        return _NodeEchec(t)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


for p in (BUNDLE, LAYER, PATCHER, HTML, CSS):
    if not p.is_file():
        print(f"  FAIL  fichier_absent {p}")
        print("\n=== 0 passed, 1 failed ===")
        sys.exit(1)

# FAUTE N°6, SIXIEME MORSURE — LA MEME FAMILLE QUE `NODE()`. `p.is_file()`
# ci-dessus ne garde que l'ABSENCE : un patcher PRESENT mais qui LEVE a
# l'import (faute de syntaxe, `SystemExit` d'une garde, dependance absente)
# tuait ce banc AVANT sa premiere ligne — rc=1, une trace, AUCUNE ligne de
# compte. MESURE le 05/09/2026 : `raise RuntimeError(…)` pose au premier
# niveau de scripts/patch_bundle_montage.py, banc lance depuis backend/ —
# AVANT, zero ligne imprimee et aucun compte ; APRES,
# `FAIL patcher_importable RuntimeError: … ·ECHEC#1` puis
# `=== 0 passed, 1 failed ===`, rc=1.
# CETTE LIGNE-CI EST PLUS ANCIENNE QUE LES DEUX DE dzcout, et elle est fermee
# ICI PLUTOT QU'AILLEURS parce qu'elle porte exactement la meme propriete :
# c'etait une aggravation, pas une nouveaute, et la laisser ouverte aurait
# fait dependre la survie du banc de l'ordre des deux imports.
# L'ARRET EST IMMEDIAT, ET C'EST DELIBERE : sans `P`, les ~200 lignes qui
# lisent `P.R_*` leveraient une AttributeError chacune. La forme est celle de
# `fichier_absent` juste au-dessus — un banc qui ne peut pas partir le DIT en
# un mot, avec un compte, au lieu de mourir.
try:
    P = load("patch_bundle_montage", PATCHER)
except BaseException as _e:          # SystemExit compris : il n'hérite pas d'Exception
    print(f"  FAIL  patcher_importable {temoin(_e)}")
    print("\n=== 0 passed, 1 failed ===")
    sys.exit(1)
s = BUNDLE.read_bytes().decode("utf-8-sig")
crlf = "\r\n" in s
def nl(t):
    t = t.replace("\r\n", "\n")
    return t.replace("\n", "\r\n") if crlf else t

print(f"\n[1] le bloc injecte et ses {len(P.PATCHES)} sections, dans le "
      f"bundle LIVRE")
check("bloc_montage_unique", s.count(P.BEGIN) == 1 and s.count(P.END) == 1,
      f"{s.count(P.BEGIN)} BEGIN, {s.count(P.END)} END")
# le contenu du bloc EST la source de la couche : un bloc vide passerait les
# comptes d'ancres sans que rien ne fonctionne à l'écran.
src = LAYER.read_bytes().decode("utf-8-sig")
# LE bloc doit ETRE la couche, octet pour octet. Sans cette ligne le banc
# pouvait benir un bundle qui n'EXECUTE PAS le code qu'il mesure : la section
# [3] charge la couche depuis le FICHIER, pas depuis le bundle. MESURE : en
# remplacant le corps de `dzmRippleCut` dans montage.js SANS rejouer le
# patcher, le banc restait entierement vert. C'est exactement le mode de
# panne que l'en-tete de ce fichier dit combattre.
_i = s.find(nl(P.BEGIN))
_j = s.find(nl(P.END), _i if _i >= 0 else 0)
_bloc = s[_i + len(nl(P.BEGIN)):_j].strip() if _i >= 0 and _j > _i else ""
check("bloc_EST_la_couche_octet_pour_octet", _bloc == nl(src).strip(),
      f"bloc={len(_bloc)} o, couche={len(nl(src).strip())} o — le bundle "
      f"n'execute pas le fichier que ce banc mesure")
check("bloc_contient_la_couche", nl("window.DzTracks=DzTracks;") in s
      and nl("function svmTrackBusSync(ts){") in s,
      "le bloc ne porte pas l'export de la couche")
for tag, a, r in P.PATCHES:
    check(tag + "_remplace", s.count(nl(r)) == 1, f"count={s.count(nl(r))}")
    # L'ancre ne doit avoir DISPARU que lorsque le remplacement ne la reprend
    # pas. Huit des onze sections l'englobent (en tête ou en queue) : y exiger
    # zéro serait un test faux, vert seulement si le patch n'a rien fait.
    if a not in r:
        check(tag + "_ancre_consommee", s.count(nl(a)) == 0,
              f"count={s.count(nl(a))}")
# ── M9c (05/09/2026) : LE « + » N'EST PLUS SOUS LA SURIMPRESSION ────────────
# Défaut rapporté par l'utilisateur : « sur la piste V1 vidéo, le bouton
# "ajouter une vidéo" est caché par l'overlay de déplacement lorsque la souris
# passe dessus ». CE BANC NE PEUT PAS OUVRIR UN NAVIGATEUR : ce qui est
# mesurable ici est la STRUCTURE — dans quelle rangée d'en-tête vit le bouton
# d'ajout, et si cette rangée est celle que `.dzm-hb` recouvre.
# LA RÉINSERTION EST REPLIÉE DANS `R_M9b` (l'ancre A_M9b est déjà consommée
# par M9b, exactement comme M10 dans R_M8) : les lignes ci-dessous sont donc
# LITTÉRALES et non tirées de `P.R_M9b`. Sans elles, retirer le greffon du
# patcher puis rejouer la chaîne laisserait le banc entièrement vert.
_HROWS = re.findall(
    r'className:"(svm-tnamerow|svm-ttyperow|svm-thbtns)",children:\['
    r'(.*?)\]\},"(\w\w)"\)', s.replace("\r\n", "\n"), re.S)
# CONJOINT DE TOUTES LES NÉGATIONS QUI SUIVENT : sans cette ligne, une
# extraction qui rendrait `[]` (regex périmée, bundle amputé) rendrait vraies
# « le bouton n'est pas dans la rangée du nom » et toutes ses sœurs.
check("M9_les_quatre_rangees_d_en_tete_sont_lisibles",
      len(_HROWS) == 4
      and [k for _c, _t, k in _HROWS] == ["nr", "br", "nr", "tr"]
      and [c for c, _t, _k in _HROWS] == ["svm-tnamerow", "svm-thbtns",
                                          "svm-tnamerow", "svm-ttyperow"],
      f"rangees={[(c, k) for c, _t, k in _HROWS]}")
# LA LIGNE QUI ROUGIT SI LE « + » REVIENT DANS LA RANGÉE DU NOM. Elle rougit
# aussi s'il DISPARAÎT (`['br']`) ou s'il se duplique : c'est une égalité à
# une liste ordonnée, pas une absence.
_HADD = [k for _c, t, k in _HROWS if re.search(r"\bthAdd\b", t)]
check("M9c_le_bouton_ajouter_vit_dans_la_rangee_du_BAS_des_deux_familles",
      _HADD == ["br", "tr"],
      f"il vit dans les rangees {_HADD} (attendu ['br', 'tr'] — 'nr' est la "
      f"rangee du haut, celle que la surimpression recouvre)")
# LES DEUX MOITIÉS DU DÉPLACEMENT, LITTÉRALES : le retrait (M9c) et la
# réinsertion (repliée dans R_M9b).
_N_NOM = s.count(nl('children:tr.name})]},"nr"),'))
_N_RESTE = s.count(nl('thAdd]},"nr"),'))
_N_TYPE = s.count(nl('children:[thType,thLock,thAdd]},"tr"),'))
check("M9c_la_rangee_du_nom_video_ne_porte_plus_que_le_nom",
      _N_NOM == 1 and _N_RESTE == 0,
      f"nom_seul={_N_NOM} (veut 1) · reste_du_bouton={_N_RESTE} (veut 0)")
check("M9c_la_rangee_du_type_video_porte_le_bouton_en_dernier",
      _N_TYPE == 1, f"count={_N_TYPE}")
# CONTRÔLE À DEUX FACES. M9c et le greffon replié dans R_M9b DÉPLACENT un
# identifiant du bundle : compter les usages ne dirait rien d'un rebuild qui
# renommerait sa DÉCLARATION — le nom serait libre et l'en-tête lèverait au
# premier rendu, sans que `node --check` (JS valide) ni aucun compte
# d'ancre ne le voie. On exige donc la déclaration ET les deux usages, et que
# le nom n'apparaisse NULLE PART AILLEURS : 1 + 2 = 3, borné par `\b…\b`.
_N_DECL = s.count(nl('var thAdd=r.jsx("button",{className:"svm-ovadd",'))
_N_TOT = len(re.findall(r"\bthAdd\b", s.replace("\r\n", "\n")))
check("M9c_le_bouton_ajouter_est_declare_et_appele_sous_le_meme_nom",
      _N_DECL == 1 and _N_TOT == 3 and _HADD == ["br", "tr"],
      f"declaration={_N_DECL} (veut 1) · occurrences={_N_TOT} (veut 3 : "
      f"la declaration + les rangees {_HADD})")
# LA PISTE AUDIO NE BOUGE PAS : son « + » était déjà au bon endroit, et son
# en-tête porte en plus M, S, le verrou et un fader.
_N_BR = s.count(nl('children:[thAdd,thM,thS,thLock]},"br"),'))
_N_NRA = s.count(nl('thType]},"nr"),'))
_N_FAD = s.count(nl("thFader]"))
check("M9a_l_en_tete_audio_est_inchange",
      _N_BR == 1 and _N_NRA == 1 and _N_FAD == 1,
      f"br={_N_BR} nr_audio={_N_NRA} fader={_N_FAD} (veut 1, 1, 1)")

# POURQUOI « nr » EST LA RANGÉE RECOUVERTE. `.dzm-hb` est en position absolue
# dans `.svm-thead`, ancrée par `top:` (jamais `bottom:`), et l'en-tête empile
# ses rangées du haut vers le bas (`flex-direction:column`) : la première
# rangée est donc celle qui passe sous la surimpression. Les deux faits sont
# LUS dans les deux feuilles, pas supposés.
_HDCSS = ROOT / "frontend" / "dist" / "shared" / "son-vfx-montage.css"
try:
    _HDCSS = _HDCSS.read_text(encoding="utf-8")
except Exception as _e:                     # absent, illisible, encodage
    _HDCSS = temoin(_e)                     # TÉMOIN distinguable : jamais ""


def _regle(css_txt, sel):
    """Corps de la règle `sel` (sélecteur littéral, accolade comprise).

    Rend `None` — jamais `""` — quand la règle manque : un corps vide
    satisferait toutes les négations de la ligne appelante."""
    i = css_txt.find(sel)
    if i < 0:
        return None
    j = css_txt.find("}", i)
    return css_txt[i + len(sel):j] if j > i else None


_R_HB = _regle(CSS.read_text(encoding="utf-8"), ".dzsvm .dzm-hb{")
_R_THEAD = _regle(_HDCSS, ".svm-thead{")
check("la_surimpression_recouvre_la_PREMIERE_rangee_de_l_en_tete",
      _R_HB is not None and _R_THEAD is not None
      and "position:absolute" in _R_HB
      and re.search(r"\btop:\s*\d+px", _R_HB) is not None
      and re.search(r"\bbottom:\s*\d", _R_HB) is None
      and "flex-direction:column" in _R_THEAD,
      f"hb={_R_HB!r} thead={_R_THEAD!r}")


# LE « + » TIENT-IL DANS LA RANGÉE DU BAS SANS DÉBORDER DES 88 px ? Les sept
# nombres sont LUS dans son-vfx-montage.css et le NOMBRE D'ENFANTS de chaque
# rangée dans le bundle : rien n'est recopié ici.
def _px(corps, prop):
    m = re.search(r"\b" + prop + r":\s*(\d+)px", corps or "")
    return int(m.group(1)) if m else None


_R_TTROW = _regle(_HDCSS, ".svm-ttyperow{")
_R_THBTNS = _regle(_HDCSS, ".svm-thbtns{")
_R_TKBTN = _regle(_HDCSS, ".svm-tkbtn{")
_R_OVADD = _regle(_HDCSS, ".svm-ovadd{")
_R_TTYPE = _regle(_HDCSS, ".svm-ttyperow .svm-ttype{")
_R_MINI = _regle(_HDCSS, ".svm-minibtn{")
_m_pad = re.search(r"\bpadding:\s*\d+px\s+(\d+)px", _R_THEAD or "")
_W = _px(_R_THEAD, "width")
_PAD = int(_m_pad.group(1)) if _m_pad else None
_GAP = _px(_R_TTROW, "gap")
_GAPB = _px(_R_THBTNS, "gap")
_LOCK = _px(_R_TKBTN, "width")
_PLUS = _px(_R_OVADD, "width")
_N = [len(t.strip().split(",")) for _c, t, k in _HROWS if k == "tr"]
_NB = [len(t.strip().split(",")) for _c, t, k in _HROWS if k == "br"]
_N = _N[0] if _N else 0
_NB = _NB[0] if _NB else 0
_UTILE = _W - 2 * _PAD if None not in (_W, _PAD) else None
# rangée du type (vidéo/sous-titres) : un verrou + le « + », le libellé prend
# le reste. rangée des boutons (audio) : le « + » + trois micro-boutons —
# c'est la rangée que montage.css appelle DÉJÀ « pleine » (67 px sur 74).
_FIXE = (_LOCK + _PLUS + _GAP * (_N - 1)
         if None not in (_LOCK, _PLUS, _GAP) and _N >= 2 else None)
_FIXEB = (_PLUS + _LOCK * (_NB - 1) + _GAPB * (_NB - 1)
          if None not in (_LOCK, _PLUS, _GAPB) and _NB >= 2 else None)
# TROIS CLAUSES, PARCE QUE LA PREMIÈRE NE MORD PAS. « Ça rentre dans 74 px »
# est trop lâche pour voir un bouton élargi : MESURÉ le 05/09/2026 en portant
# `.svm-ovadd` de 16 à 40px — 60 < 74, la ligne restait VERTE, le nombre lu
# dans la CSS était décoratif. Les deux autres clauses l'ont fait rougir : la
# rangée des boutons audio crèverait le budget (91 > 74), et dans la rangée
# du type le libellé n'aurait plus que 14px là où les boutons en prendraient
# 60. BORNE MESURÉE, en élargissant le bouton d'un pixel à la fois : 16 vert
# (libellé 38, boutons 36), 17 vert (37 contre 37, l'égalité passe), 18 ROUGE.
# La tolérance est donc d'UN pixel, et c'est écrit ici pour que le prochain
# élargissement sonne au lieu de rogner le libellé en silence.
check("le_bouton_tient_dans_la_rangee_du_bas_video",
      _UTILE is not None and _FIXE is not None and _FIXEB is not None
      and _N == 3 and _NB == 4
      and _FIXE < _UTILE and _FIXEB <= _UTILE
      and _UTILE - _FIXE >= _FIXE,
      f"utile={_UTILE} (largeur {_W} − 2 × padding {_PAD}) · "
      f"type: fixes={_FIXE} libelle={None if _UTILE is None or _FIXE is None else _UTILE - _FIXE} "
      f"(verrou {_LOCK} + bouton {_PLUS} + {_N - 1} × gap {_GAP}, {_N} enfants) · "
      f"audio: fixes={_FIXEB} ({_NB} enfants, gap {_GAPB})")
# ET POURQUOI RIEN NE DÉBORDE QUAND LE LIBELLÉ, LUI, EST TROP LONG : c'est le
# libellé qui absorbe TOUT le serrage (il rétrécit et met des points de
# suspension), pendant que les deux boutons gardent leur taille.
# DETTE ÉCRAN ASSUMÉE : « overlay/VFX » et « sous-titres » (11 caractères,
# ≈ 51 px en mono 8 px) ne tiennent plus dans les ~38 px restants et
# s'abrègent ; `title:tr.type` porte le libellé entier au survol. Aucune de
# ces deux lignes ne prétend avoir mesuré le RENDU — seulement le mécanisme.
check("le_libelle_du_type_absorbe_le_serrage_au_lieu_de_deborder",
      _R_TTYPE is not None and _R_MINI is not None
      and "flex:1 1 auto" in _R_TTYPE and "min-width:0" in _R_TTYPE
      and "overflow:hidden" in _R_TTYPE
      and "text-overflow:ellipsis" in _R_TTYPE
      and "flex:none" in _R_MINI
      and s.count(nl("title:tr.type")) == 1,
      f"ttype={_R_TTYPE!r} minibtn={_R_MINI!r} "
      f"title={s.count(nl('title:tr.type'))}")
# M10 (P2) : la chip « mot » et le bouton « emoji » vivent DANS R_M8 — l'ancre
# A_M8 est déjà consommée par M8. `R_M8` CONTENANT `R_M10`, un bundle amputé de
# la chip échouerait déjà sur « M8-toolbar_remplace » : cette ligne ne rattrape
# donc pas ce cas-là. Ce qu'elle rattrape : retirer `R_M10` de `R_M8` DANS LE
# PATCHER puis rejouer la chaîne — le bundle reste cohérent, M8 se retrouve
# tout seul et passe, et seule cette ligne (avec la suivante) voit le trou.
check("M10-chip_remplace", s.count(nl(P.R_M10)) == 1, f"count={s.count(nl(P.R_M10))}")
# `DzMontage` est DÉJÀ une fonction de premier niveau du bundle (l'écran
# Montage). La couche ne doit référencer que `DzTracks` : `DzTracks.` compté
# ici, `DzMontage.` (l'appel qu'écrivait le plan) interdit.
check("M10_utilise_DzTracks_pas_DzMontage",
      "DzMontage.WordAnimChip" not in s and "DzTracks.WordAnimChip" in s
      and "DzTracks.EmojiBtn" in s)
# R_M10 APPELLE six identifiants du bundle que rien ne gardait. `node --check`
# ne peut pas les voir (c'est du JS valide : un nom libre ne lève qu'à
# l'exécution) et compter R_M10 ne prouve que ce que le patch a écrit. Un
# rebuild qui renommerait `subsSegsOf` laisserait tout vert, et la chip
# lèverait au PREMIER clic.
# Le contrôle est donc à DEUX FACES : vérifier seulement la déclaration
# laisserait passer un R_M10 qui appelle un AUTRE nom (mesuré : renommer
# l'appel en `subsSegsOfRENOMME` gardait les 58 lignes vertes) ; vérifier
# seulement l'appel ne verrait pas le rebuild. On exige les deux, et qu'ils
# portent le MÊME nom — recherche BORNÉE (`\b…\b`), car un simple `in` était
# encore leurré, `subsSegsOf` étant sous-chaîne de `subsSegsOfRENOMME`.
# `fireNote=nt[1]` apparaît sept fois — c'est le même motif dans plusieurs
# composants ; ce qui compte est qu'il en reste au moins un.
for _nm, _decl in (("subsSegsOf", "function subsSegsOf(cs){"),
                   ("subsStyleSet", "function subsStyleSet(patch){"),
                   ("pushHistory", "var pushHistory=x.useCallback("),
                   ("setClips", "setClips=st1[1]"),
                   ("setDirty", "setDirty=st8[1]"),
                   ("fireNote", "fireNote=nt[1]")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), P.R_M10) is not None
    check("M10_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# L'ANNULATION est garantie par CONSTRUCTION, pas par une mesure : pushHistory
# et undo sont des hooks du composant, hors de portée du shim node — qui ne
# joue que la couche pure. Ce que cette ligne épingle est l'ORDRE des deux
# appels dans le bundle livré, pas leur effet. Bon côté de ce montage : `onAdd`
# étant appelé depuis le `.then()`, pushHistory lit l'état au moment de la
# réponse et non du clic — l'instantané reste juste si l'utilisateur a bougé
# un clip pendant la requête.
check("M10_emoji_pousse_l_historique_avant_d_ajouter",
      s.count(nl("onAdd:function(cs){pushHistory();setClips(")) == 1,
      f'count={s.count(nl("onAdd:function(cs){pushHistory();setClips("))}')

print("\n[1-bis] P3 — le bouton « texte », le panneau, et la coupe par plage")
# M11b vit DANS R_M8, comme M10 : meme raison (A_M8 deja consommee). Meme
# limite aussi — un bundle ampute echouerait deja sur M8-toolbar_remplace ;
# ce que cette ligne rattrape est le retrait de R_M11b DANS LE PATCHER.
check("M11b-bouton_texte_dans_la_barre", s.count(nl(P.R_M11b)) == 1,
      f"count={s.count(nl(P.R_M11b))}")
check("M11_etat_declare_une_fois",
      s.count(nl("var stDzTx=x.useState(!1),dzTextOn=stDzTx[0],"
                 "setDzTextOn=stDzTx[1];")) == 1)
# UN NOM NEUF NE DOIT RIEN ECRASER, et la mesure doit DECIDER. L'ancienne
# ligne ne decidait rien : elle comptait la SOUS-CHAINE `stTx` (7 dans le
# bundle) alors que `\bstTx\b` en vaut 0 — les sept sont des morceaux de
# `costTxt`, dans une autre fonction — et son premier terme etait de toute
# facon toujours vrai. La mesure qui decide : les trois identifiants de M11
# n'apparaissent NULLE PART ailleurs que dans les sections qui les ecrivent.
for _nm in ("stDzTx", "dzTextOn", "setDzTextOn"):
    _dehors = s.count(_nm) - (P.R_M11 + P.R_M11b + P.R_M12).count(_nm)
    check("M11_nom_" + _nm + "_n_ecrase_rien", _dehors == 0,
          f"{_nm} apparait {_dehors}x hors des sections qui l'ecrivent")
check("M12_utilise_DzTracks_pas_DzMontage",
      "DzMontage.TextDrawer" not in s and "DzMontage.rippleCut" not in s
      and s.count("DzTracks.TextDrawer") == 1
      and s.count("DzTracks.rippleCut") == 1)
# Le CŒUR de P3 doit etre DANS le bloc livre, pas seulement dans la source du
# patcher : sans cette ligne, un bloc vide passerait les comptes d'ancres.
check("bloc_contient_rippleCut", nl("rippleCut:dzmRippleCut,") in s
      and nl("function dzmRippleCut(clips,t0,t1,opts){") in s)
check("bloc_contient_withWords", nl("withWords:dzmWithWords,") in s
      and nl("function dzmWithWords(clips,aligned){") in s)
# La couche est INJECTEE dans le bundle : une ancre CITEE dans un de ses
# commentaires s'y compte une fois de plus, et le patcher abandonne au rejeu
# suivant (« anchor count=2 »). MESURE pendant l'ecriture de P3 : c'est
# exactement ce qui est arrive, sur l'ancre de M12, pour une ancre recopiee
# telle quelle dans une phrase d'explication. Le controle est GENERAL, pas
# nominatif : il vaut pour toute ancre que la chaine ajoutera plus tard.
# FINS DE LIGNE NORMALISEES DES DEUX COTES. montage.js est en CRLF (655
# lignes), les litteraux du patcher en LF : sur une ancre MULTILIGNE,
# `src.count()` aurait rendu 0 POUR TOUJOURS et ce controle serait passe au
# vert A VIDE — le defaut meme qu'il est cense empecher.
_src_lf = src.replace("\r\n", "\n")
for _tag, _a, _r in P.PATCHES:
    _n = _src_lf.count(_a.replace("\r\n", "\n"))
    check("couche_ne_cite_pas_l_ancre_de_" + _tag, _n == 0,
          f"la couche cite {_n}x l'ancre de {_tag} — le prochain "
          f"rejeu du patcher abandonnera")
# La mesure qui JUSTIFIE le repli de M12, REJOUEE : une mesure ecrite en
# commentaire et jamais relancee se perime. L'ancre que le plan preferait
# n'existe toujours pas dans ce bundle — et aucun commentaire ne l'y remet.
check("M12_ancre_du_plan_toujours_absente", s.count("subsDrawer") == 0,
      f"count={s.count('subsDrawer')} — soit le repli de M12 n'a plus lieu "
      f"d'etre, soit un commentaire a reintroduit le jeton")
# M12 doit RECOLLER les mots avant de couper : sans cet appel, fendre un bloc
# de narration laisse la phrase entière sur les deux moitiés.
check("M12_recolle_les_mots_avant_de_couper",
      s.count(nl("var cs=DzTracks.withWords(clipsRef.current||[],al),rm=0;")) == 1
      and re.search(r"DzTracks\.withWords\([\s\S]{0,400}DzTracks\.rippleCut\(", s)
      is not None,
      f'count={s.count(nl("var cs=DzTracks.withWords(clipsRef.current||[],al),rm=0;"))}')
# Meme controle a DEUX FACES que M10 : les identifiants du bundle que R_M12
# appelle doivent exister, et sous le MEME nom. Recherche bornee (\b…\b) —
# un simple `in` serait leurre par une sous-chaine.
for _nm, _decl in (("trackSt", "var stTS=x.useState({}),trackSt=stTS[0],"
                               "setTrackSt=stTS[1];"),
                   ("clipsRef", "var clipsRef="),
                   ("svmTracksOf", "function svmTracksOf(proj){"),
                   ("pushHistory", "var pushHistory=x.useCallback("),
                   ("setClips", "setClips=st1[1]"),
                   # `setProj` a QUITTE R_M12 avec le renoncement a toucher
                   # `proj.dur` (voir M12_ne_touche_pas_a_la_duree_du_projet).
                   ("proj", "proj=stP[0],setProj=stP[1];"),
                   ("setDirty", "setDirty=st8[1]"),
                   ("fireNote", "fireNote=nt[1]")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), P.R_M12) is not None
    check("M12_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# LE geste destructif de P3 : rippleCut RETIRE du montage. `pushHistory()`
# doit le PRECEDER, et une seule fois pour tout le lot — « annuler » defait
# le geste, pas ses dix-sept morceaux. Ce que l'annulation restaure
# exactement : les clips et le mixage (tout ce que l'historique de ce bundle
# memorise) ; PAS `proj.dur`, raccourci d'autant. C'est un reste ASSUME, dit
# dans la note de chaque coupe et dans le titre des deux boutons.
check("M12_pousse_l_historique_avant_de_couper",
      len(re.findall(r"pushHistory\(\);[\s\S]{0,420}DzTracks\.rippleCut\(",
                     s)) == 1,
      str(len(re.findall(r"pushHistory\(\);[\s\S]{0,420}DzTracks\.rippleCut\(", s))))
check("M12_un_seul_pushHistory_pour_le_lot",
      P.R_M12.count("pushHistory()") == 1, str(P.R_M12.count("pushHistory()")))
# I4 — M12 NE TOUCHE PLUS a la duree du projet, et c'est ce qui rend
# « annuler » COMPLET. `pushHistory` ne memorise que {clips, mixDb} ; pire,
# la restauration au chargement fait
# `dur:Math.max(1,Number(d.duration)||maxEnd)`, donc une duree SAUVEGARDEE
# l'emporte sur les clips : couper, annuler, laisser l'autosave passer,
# rouvrir rendait une timeline plus courte que ses propres clips.
check("M12_ne_touche_pas_a_la_duree_du_projet",
      "p.dur" not in P.R_M12 and "proj.dur" not in P.R_M12,
      "R_M12 ecrit encore dans la duree du projet")
check("M12_dit_que_la_duree_ne_bouge_pas",
      "La durée du projet ne bouge pas" in P.R_M12,
      "la note de coupe ne dit pas ce qu'il advient de la duree")
# M6 — les mots PRETES par withWords ne sont pas persistes dans le projet :
# inertes au rendu, mais ils gonfleraient la sauvegarde d'une copie de toute
# la narration, mot par mot, que rien ne relit.
check("M12_retire_les_mots_pretes",
      s.count(nl("setClips(DzTracks.dropWords(cs,svmTracksOf(proj)")) == 1
      and nl("function dzmDropWords(clips,keepTracks){") in s,
      "les mots de la narration resteraient dans la sauvegarde")
check("css_porte_le_marquage_des_remplissages",
      ".dzm-txtb[data-filler]" in CSS.read_text(encoding="utf-8"),
      "montage.css ne marque pas les mots de remplissage")
# Le marquage doit RESTER LISIBLE quand le mot est selectionne : mesure, le
# rouge du soulignement sur le fond accent tombait a 1,60 de contraste (4,79
# au repos), donc il disparaissait — au moment precis ou l'on glisse sur une
# plage pour verifier ce qu'elle contient.
check("css_garde_le_marquage_visible_en_selection",
      ".dzm-txtb[data-filler][data-on]" in CSS.read_text(encoding="utf-8"),
      "un mot de remplissage selectionne perd son soulignement")
# I6 — le panneau au CLAVIER. Un <button> active a Entree ou Espace emet un
# `click`, JAMAIS un `mousedown` : sans `onClick`, les boutons de mot
# portaient `aria-pressed`, etaient tous dans l'ordre de tabulation, et ne
# faisaient rien.
check("panneau_texte_repond_au_clavier",
      nl("onClick:function(e){selTo(i,e&&e.shiftKey)}") in s,
      "les boutons de mot n'ont toujours que des ecouteurs de souris")
# I5 — le bouton EN BLOC ne prend que les hesitations, et son titre NOMME les
# mots qu'il emporte. Mesure : une narration francaise sans une hesitation
# rendait cinq plages, dont « Voilà », « Enfin », « genre », « quoi ».
check("bouton_en_bloc_ne_prend_que_les_hesitations",
      nl('var hes=spans.filter(function(s){return s.kind==="hesitation"});') in s
      and nl("onClick:function(){cut(hes.map(function(s){") in s,
      "le bouton en bloc emporte encore les mots pleins")
check("bouton_en_bloc_nomme_les_mots_qu_il_emporte",
      nl('title:hes.length\n          ?("Retirer "+hesMots.map(') in s,
      "le titre du bouton ne dit pas quels mots partent")
# MESURE : son-vfx-montage.css n'a aucune regle `.svm-tbtn[data-on]` (grep
# 04/09/2026 — la barre n'avait jamais eu de bouton a bascule). Sans une
# regle A NOUS, l'etat ouvert du panneau ne se verrait pas du tout.
check("css_porte_l_etat_ouvert_du_bouton_texte",
      ".dzm-txton[data-on]" in CSS.read_text(encoding="utf-8")
      and "dzm-txton" in P.R_M11b,
      "l'etat retenu du bouton « texte » n'est pas habille")

print("\n[1-quater] P4 — le bouton « étalonnage → tous les plans » (M13)")
# L'ancre du plan (`        transInspector(),`) n'a PAS été retenue, et la
# mesure qui l'écarte est REJOUÉE ici plutôt que laissée en commentaire : elle
# est bien LIBRE (R_M12 la reprend en tête, donc elle survit à M12), mais elle
# poserait le bouton à un écran de la pile d'effets qu'il recopie. Si un jour
# elle valait autre chose que 1, ce commentaire mentirait sans le dire.
check("M13_ancre_du_plan_libre_mais_ecartee",
      s.count(nl("        transInspector(),")) == 1
      and "transInspector" not in P.A_M13,
      f"count={s.count(nl('        transInspector(),'))}")
# `DzMontage.gradeAllBtn` était l'appel du plan : c'est le nom d'une fonction
# de PREMIER NIVEAU du bundle (l'écran Montage). Interdit — voir
# node_check_module.
check("M13_utilise_DzTracks_pas_DzMontage",
      "DzMontage.gradeAllBtn" not in s and s.count("DzTracks.gradeAllBtn") == 1,
      f"count={s.count('DzTracks.gradeAllBtn')}")
# Contrôle à DEUX FACES, comme M10 et M12 : chaque identifiant du bundle que
# R_M13 appelle doit exister, et sous le MÊME nom (recherche bornée).
# UNE RÉSERVE, dite plutôt que tue : pour `sel`, la face « appelée » ne décide
# rien — R_M13 REPREND l'ancre, qui contient déjà `sel&&sel.tr`. Le jeton y
# serait donc même si l'argument disparaissait de l'appel. C'est la face
# DÉCLARATION qui porte la mesure pour lui (un rebuild renommant `sel` la fait
# rougir) ; pour les cinq autres, les deux faces décident — mesuré, retirer
# `setDirty` ou renommer `fireNote` dans R_M13 fait rougir leur ligne, seule.
for _nm, _decl in (("sel", "var sel=clips.find("),
                   ("clips", "clips=st1[0]"),
                   ("setClips", "setClips=st1[1]"),
                   ("pushHistory", "var pushHistory=x.useCallback("),
                   ("setDirty", "setDirty=st8[1]"),
                   ("fireNote", "fireNote=nt[1]")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), P.R_M13) is not None
    check("M13_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# `setDirty` est l'ÉCART AU PLAN (cinq arguments chez lui, six ici). La mesure
# qui l'impose : l'autosave du bundle ne part que si `dirty`. Sans ce
# sixième argument, un lot appliqué juste après une sauvegarde réussie ne
# serait jamais envoyé — et rien ne le dirait. On vérifie donc que la GARDE
# existe toujours dans le bundle : le jour où elle disparaîtrait, cet
# argument deviendrait du bruit et ce banc doit le faire savoir.
_garde = s.count(nl("if(proj.demo||!dirty)return;")) - src.count(
    "if(proj.demo||!dirty)return;")
check("M13_setDirty_justifie_par_la_garde_de_l_autosave",
      _garde == 1 and "setDirty" in P.R_M13,
      f"garde presente {_garde}x hors de la couche")
# ... et il faut que la COUCHE s'en serve. Le passer en argument sans jamais
# l'appeler laisserait le lot hors de l'autosave, et les deux lignes
# ci-dessus resteraient vertes : mesure faite, c'est exactement ce qui
# arrivait avant celle-ci.
check("M13_la_couche_allume_vraiment_le_drapeau",
      s.count(nl("if(setDirty)setDirty(!0);")) == 1,
      f'count={s.count(nl("if(setDirty)setDirty(!0);"))}')
# LE geste destructif de P4 : il ÉCRASE l'étalonnage des autres plans.
# `pushHistory` doit le précéder, une seule fois pour tout le lot.
check("M13_pousse_l_historique_avant_d_ecrire",
      nl("if(pushHistory)pushHistory();\n      if(setClips)setClips(res.clips);")
      in s, "l'ordre pushHistory -> setClips n'est pas celui du bundle livré")
check("M13_un_seul_pushHistory_pour_le_lot",
      src.count("pushHistory()") == 1, str(src.count("pushHistory()")))
# Le CŒUR de P4 doit être DANS le bloc livré, pas seulement dans la source.
check("bloc_contient_gradeAll",
      nl("gradeAllBtn:dzmGradeAllBtn,gradeAll:dzmGradeAll,") in s
      and nl("function dzmGradeAll(clips,srcId,trackId){") in s)
check("css_porte_le_bouton_d_etalonnage_global",
      ".dzm-gall{" in CSS.read_text(encoding="utf-8").replace(" ", "")
      .replace("\n", "").replace("\r", "")
      and "dzm-gall" in src, "montage.css n'habille pas le bouton de M13")

print("\n[1-quinquies] P5 — le popover « projets » (M14)")
# M14 vit DANS R_M8, comme M10 et M11b : A_M8 est deja consommee par M8 et la
# barre de transport n'offre pas de seconde ancre unique. MEME LIMITE que
# `M10-chip_remplace`, et pour la meme raison : `R_M8` CONTENANT `R_M14`, un
# bundle ampute du popover echouerait DEJA sur « M8-toolbar_remplace » — cette
# ligne-ci ne rattrape donc pas ce cas-la. Ce qu'elle rattrape : retirer
# `R_M14` de `R_M8` DANS LE PATCHER puis rejouer la chaine — le bundle reste
# coherent, M8 se retrouve tout seul et passe, et seule cette ligne (avec les
# suivantes) voit le trou.
check("M14-projets_remplace", s.count(nl(P.R_M14)) == 1,
      f"count={s.count(nl(P.R_M14))}")
# `DzMontage.Projects` etait l'appel du plan — nom d'une fonction de PREMIER
# NIVEAU du bundle (l'ecran Montage). Interdit, cf. node_check_module.
check("M14_utilise_DzTracks_pas_DzMontage",
      "DzMontage.Projects" not in s and s.count("DzTracks.Projects") == 1,
      f"count={s.count('DzTracks.Projects')}")
# Controle a DEUX FACES, comme M10, M12 et M13 : chaque identifiant du bundle
# que R_M14 appelle doit exister, et sous le MEME nom (recherche bornee).
# RESERVE, dite plutot que tue : pour `proj`, la face « appelee » decide peu —
# R_M14 lit `proj.name` ET `proj.project_id`, deux jetons distincts, mais un
# rebuild qui renommerait l'etat ferait rougir la face DECLARATION.
for _nm, _decl in (("proj", "proj=stP[0],setProj=stP[1];"),
                   ("setProj", "proj=stP[0],setProj=stP[1];"),
                   ("svmApplyProject", "function svmApplyProject(d){"),
                   ("saveAbortRef",
                    "var saveSeqRef=x.useRef(0),saveAbortRef=x.useRef(null);"),
                   ("saveSeqRef",
                    "var saveSeqRef=x.useRef(0),saveAbortRef=x.useRef(null);"),
                   ("setSaveInfo",
                    "var stSv=x.useState(null),saveInfo=stSv[0],setSaveInfo=stSv[1];"),
                   # les trois jetons ajoutes le 04/09/2026 (C1 et I3) : le
                   # payload de l'autosave descend dans le popover, et
                   # `onFail` relance la sauvegarde qu'`onBefore` a annulee.
                   ("svmSavePayload", "function svmSavePayload(){"),
                   ("svmDoSave", "function svmDoSave(seq){"),
                   ("dirty", "var st8=x.useState(!0),dirty=st8[0],setDirty=st8[1];"),
                   ("fireNote", "fireNote=nt[1]")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), P.R_M14) is not None
    check("M14_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# `project_id` doit voyager DANS LES DEUX SENS, et ces deux lignes sont les
# SEULES a le voir : la boucle des couples ancre -> remplacement suit le
# patcher par importlib, donc retirer la cle des litteraux R_M6 / R_M7 la
# laisserait entierement verte. Sans R_M6, un projet nomme cesse de suivre
# les editions ; sans R_M7, rouvrir l'application oublie de quel projet la
# timeline etait le brouillon — et le premier autosave venu casse le lien.
check("M6_autosave_joint_le_project_id",
      "project_id:proj.project_id," in P.R_M6
      and s.count(nl("project_id:proj.project_id,")) == 1,
      f"count={s.count(nl('project_id:proj.project_id,'))}")
check("M7_restauration_rend_le_project_id",
      "project_id:d.project_id," in P.R_M7
      and s.count(nl("project_id:d.project_id,")) == 1,
      f"count={s.count(nl('project_id:d.project_id,'))}")
# LES DEUX GESTES DESTRUCTIFS de P5 — ouvrir (qui ECRASE la timeline
# affichee) et supprimer (qui retire un fichier du disque) — ARMENT avant de
# frapper. `data-arm`, jamais de modale : cet ecran n'en a aucune, et une
# boite systeme gele la page, donc l'autosave, le temps qu'on lise.
check("M14_les_deux_gestes_arment",
      s.count(nl('if(arm!=="o"+p.id){setArm("o"+p.id);return}')) == 1
      and s.count(nl('if(arm!=="x"+p.id){setArm("x"+p.id);return}')) == 1,
      "un des deux gestes destructifs frappe au premier clic")
# ... et le LIBELLE change avec l'armement. La couleur seule ne dit pas ce que
# le second clic fera : elle dit seulement que quelque chose a change.
check("M14_l_armement_change_le_libelle",
      nl('children:oArm?"remplacer ?":"ouvrir"') in s
      and nl('children:xArm?"supprimer ?":"×"') in s,
      "un bouton arme garde son libelle de repos")
# `onBefore` PRECEDE L'OUVERTURE, et LA SEULE. C'est la que l'editeur annule
# son autosave en vol : sans lui, une sauvegarde partie 1,4 s plus tot arrive
# APRES et rend au courant le montage qu'on vient de quitter — le serveur ne
# peut pas distinguer les deux, la course que le bouton « bibliotheque » du
# bundle desamorce deja ainsi.
# LA SUPPRESSION NE L'APPELLE PLUS, correction du 04/09/2026 : le serveur y
# ferme la course a DEUX verrous (POST /save ne retient `project_id` que s'il
# designe un fichier EXISTANT, et ne miroite que dans celui-la — mesure,
# test_montage_projets.py [10] et [16]). Annuler l'autosave la etait une
# perte seche : `onBefore` ne touche que deux useRef et `setSaveInfo`, qui
# n'est PAS dans les dependances de l'effet d'autosave — supprimer un projet
# QUI N'EST PAS LE SIEN n'appelle pas `onNamed`, donc `proj` ne change pas,
# donc rien ne replanifie la sauvegarde annulee.
_doOpen = re.search(r"function doOpen\(p\)\{.*?send\(url\(p\.id\)\+\"/open\"",
                    s, re.S)
_doDel = re.search(r"function doDel\(p\)\{.*?req\(url\(p\.id\),"
                   r"\{method:\"DELETE\"\}\)", s, re.S)
_nBefore = len(re.findall(r"if\(props\.onBefore\)props\.onBefore\(\);", s))
check("M14_onBefore_precede_l_ouverture_et_elle_seule",
      _nBefore == 1
      # l'APPEL, jamais le mot : `doDel` PARLE d'`onBefore` en commentaire
      # (il dit pourquoi il ne l'appelle plus), et chercher le jeton nu
      # rendait cette ligne rouge sur une couche pourtant correcte — mesure du
      # 04/09/2026, premier tir.
      and _doOpen is not None
      and "if(props.onBefore)props.onBefore();" in _doOpen.group(0)
      and _doDel is not None
      and "if(props.onBefore)props.onBefore();" not in _doDel.group(0),
      f"appels={_nBefore} "
      f"dans_doOpen={_doOpen is not None and 'props.onBefore();' in _doOpen.group(0)}"
      f" dans_doDel={_doDel is not None and 'props.onBefore();' in _doDel.group(0)}")
# ... et quand l'ouverture ECHOUE (409 « projet inouvrable », panne reseau),
# l'autosave annule est RELANCE. Sans `onFail`, la sauvegarde que
# l'utilisateur croyait partie n'attendait que sa prochaine edition : le
# badge restait honnete (`dirty` demeure vrai) mais plus rien ne la
# reprogrammait. NON MESURE A L'ECRAN — dette navigateur.
_doOpenPlein = re.search(r"function doOpen\(p\)\{.*?function doDup\(p\)\{",
                         s, re.S)
check("M14_l_ouverture_ratee_relance_l_autosave_annule",
      "onFail:function(){if(dirty)svmDoSave(++saveSeqRef.current)}," in P.R_M14
      and s.count(nl("if(props.onFail)props.onFail()")) == 1
      and _doOpenPlein is not None
      and ".catch(function(e){fail(e);if(props.onFail)props.onFail()})"
      in _doOpenPlein.group(0),
      f"R_M14={'onFail' in P.R_M14} "
      f"appels={s.count(nl('if(props.onFail)props.onFail()'))} "
      f"dans_doOpen={_doOpenPlein is not None and 'onFail' in _doOpenPlein.group(0)}")
# C1 — « Enregistrer sous… » envoie la TIMELINE AFFICHEE avec le nom.
# MESURE du 04/09/2026 : sans elle, `POST /projects` ne lisait que
# montage_saved.json, et deux etats courants n'en ont pas (installation
# neuve ; l'instant qui suit le bouton « bibliotheque ») — l'ecran montrait
# une timeline et le popover repondait 400 « aucune timeline courante ». Le
# reste du temps le disque avait jusqu'a 1,5 s de retard : 7 clips affiches,
# 1 clip nomme, alors que le titre du bouton promet « le montage AFFICHE ».
check("M14_enregistrer_sous_envoie_la_timeline_affichee",
      "payload:function(){return svmSavePayload()}," in P.R_M14
      and s.count(nl("var tl=(props&&props.payload)?props.payload():null;")) == 1
      and s.count(nl('{name:(nv||"").trim(),timeline:tl})')) == 1,
      "saveAs ne poste toujours que le nom")
# M2 — les boutons de ligne s'ETEIGNENT pendant une requete. Ils sortaient
# deja tous sur `if(busy)return`, mais aucun ne portait `disabled` : ils
# restaient cliquables et INERTES, sans le moindre retour. `load()` partant a
# chaque ouverture du popover, les premiers clics d'une ouverture tombaient
# precisement la. Quatre boutons simples + « ouvrir », qui cumule avec `mine`.
check("M14_les_boutons_de_ligne_s_eteignent_pendant_une_requete",
      s.count(nl("disabled:off,")) == 4
      and s.count(nl('disabled:mine||off,"aria-disabled":mine||off,')) == 1
      and s.count(nl("var off=!!busy;")) == 1,
      f"disabled:off={s.count(nl('disabled:off,'))}")
check("M14_la_feuille_habille_deja_le_bouton_eteint",
      ".dzm-projbtn:disabled" in CSS.read_text(encoding="utf-8"),
      "aucun style pour un bouton de ligne eteint")
# `onNamed` n'est appele QUE si l'ecran a VRAIMENT applique le projet.
# Rattacher le projet a une timeline restee l'ANCIENNE ferait ecrire celle-ci
# dans le projet qu'on vient d'ouvrir, au premier autosave : le geste aurait
# detruit ce qu'il pretendait ouvrir. (Le serveur refuse deja d'ouvrir un
# projet sans plan vivant — 409, cf. test_montage_projets.py section [13] ;
# cette ligne garde l'ORDRE cote ecran, qui vaut pour toute autre reponse que
# l'ecran ne saurait appliquer.)
check("M14_onNamed_apres_l_application_reussie",
      s.count(nl("if(props.onOpen&&props.onOpen(d)){\n"
                 "          if(props.onNamed)props.onNamed(p.id,p.name);")) == 1,
      "le projet est rattache avant que l'ecran ait applique quoi que ce soit")
check("M14_l_editeur_annule_vraiment_l_autosave_en_vol",
      "saveAbortRef.current.abort()" in P.R_M14
      and "saveSeqRef.current++" in P.R_M14,
      "onBefore ne fait pas ce que son nom promet")
# CE QUI NE REVIENT PAS doit etre DIT — dans la NOTE, celle qui s'affiche
# APRES le geste, pas seulement dans le titre du bouton qui, lui, disparait
# avec le curseur. L'historique de cet ecran ne memorise que {clips, mixDb},
# et l'application d'un projet le remet a zero : ni le montage remplace ni le
# fichier supprime ne se rejouent.
# LES DEUX LIGNES SONT ANCREES SUR LE CORPS DE LA NOTE, et c'est une
# correction : la version d'avant cherchait « DÉFINITIVEMENT » N'IMPORTE OU
# dans la couche. MUTATION VERIFIEE le 04/09/2026 — en retirant le mot de la
# note de suppression, le banc restait a 166/0, le jeton survivant dans le
# titre du bouton arme. Une assertion qui reste verte quand on supprime ce
# qu'elle teste ne teste rien.
check("M14_la_note_d_ouverture_dit_que_rien_ne_revient",
      s.count(nl('« annuler » ne le rend pas.")}')) == 1,
      f"count={s.count(nl(chr(171) + ' annuler ' + chr(187)))}")
check("M14_la_note_de_suppression_dit_definitivement",
      s.count(nl(' » supprimé — DÉFINITIVEMENT : le fichier est parti "+')) == 1,
      "la note de suppression ne dit plus que le fichier ne revient pas")
# PAS de `setDirty` dans R_M14, et c'est un choix : au retour de chacune de
# ces routes le serveur a DEJA ecrit le courant ET le projet. Allumer
# « NON ENREGISTRE » juste apres une ouverture reussie ferait mentir le badge.
check("M14_n_allume_pas_le_drapeau_pour_rien",
      "setDirty" not in P.R_M14, "R_M14 marque le projet modifie sans raison")
# Le CŒUR de P5 doit etre DANS le bloc livre, pas seulement dans la source.
check("bloc_contient_Projects",
      nl("Projects:DzmProjects,projLine:dzmProjLine,projWhen:dzmProjWhen,") in s
      and nl("var DzmProjects=function(props){") in s)
check("css_porte_le_popover_projets",
      ".dzm-projp{" in CSS.read_text(encoding="utf-8").replace(" ", "")
      .replace("\n", "").replace("\r", "")
      and ".dzm-projbtn[data-arm]" in CSS.read_text(encoding="utf-8")
      and "dzm-projp" in src, "montage.css n'habille pas le popover")
check("css_porte_l_etat_ouvert_du_bouton_projets",
      ".dzm-projb[data-on]" in CSS.read_text(encoding="utf-8")
      and "dzm-projb" in src,
      "l'etat ouvert du bouton « projets » n'est pas habille")

print("\n[1-quater] P9 — « Bibliothèque… », la piste résolue, le champ enfin lu")
SERVICE = ROOT / "backend" / "app" / "services" / "montage_service.py"
SVC = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
check("service_montage_lisible", bool(SVC), f"{SERVICE} illisible")
# ── le bouton, replie dans R_M8 comme M10 / M11b / M14 ────────────────────
check("M16lib-bouton_bibliotheque_dans_la_barre",
      s.count(nl(P.R_M16LIB)) == 1, f"count={s.count(nl(P.R_M16LIB))}")
check("M16lib_utilise_DzTracks_pas_DzMontage",
      "DzMontage.LibBtn" not in s and s.count("DzTracks.LibBtn") == 1,
      f'count={s.count("DzTracks.LibBtn")}')
# Le libelle EST le mot de l'utilisateur (« depuis la bibliotheque »), pas
# « + clip ». Il vit dans la couche, donc on le mesure dans le bundle livre.
check("M16lib_le_libelle_est_le_mot_de_l_utilisateur",
      nl('children:"Bibliothèque…"},"lib")') in s,
      "le bouton ne s'appelle plus « Bibliothèque… »")
# Controle a DEUX FACES, comme M10/M12/M13/M14 : R_M16LIB appelle trois
# identifiants du bundle ; verifier la seule declaration laisserait passer un
# appel renomme, verifier le seul appel ne verrait pas un rebuild.
for _nm, _decl in (("openPicker", "function openPicker(trId){"),
                   ("svmTracksOf", "function svmTracksOf(proj){"),
                   ("fireNote", "fireNote=nt[1]")):
    _ap = re.search(r"\b%s\b" % re.escape(_nm), P.R_M16LIB) is not None
    check("M16lib_appelle_" + _nm + "_qui_est_declare",
          _ap and s.count(nl(_decl)) >= 1,
          f"appelé={_ap} déclaré={s.count(nl(_decl))} ({_decl})")
# MESURE qui fonde le bouton : avant P9, `openPicker` n'etait appele QU'A UN
# endroit — le « + » de 14 px d'un en-tete de piste. Deux appels apres P9 :
# celui-la, et le notre. TROIS depuis P6 (04/09/2026), et le troisieme est
# NOMME ici : « Remplacer la source… » de l'inspecteur (section M16src),
# qui ouvre le meme selecteur apres avoir arme le mode remplacement. Un
# QUATRIEME voudrait dire que quelqu'un a repose la question sans le dire.
# Le détail imprimait `findall(r"openPicker.")` — le POINT est un joker, il
# comptait aussi `openPicker,` et `openPicker;` : 7 là où la condition mesure
# 3 - 1 = 2. Un détail d'échec qui n'est pas la quantité testée envoie celui
# qui débogue chercher trois appelants fantômes.
_op_tot = len(re.findall(r"openPicker\(", s))
_op_decl = s.count("function openPicker(")
check("M16lib_openPicker_a_exactement_trois_appelants",
      _op_tot - _op_decl == 3,
      f"« openPicker( »={_op_tot} déclaration={_op_decl} "
      f"appelants={_op_tot - _op_decl} (attendu 3)")
# ... et le troisieme est bien CELUI-LA. Sans cette ligne, le compte
# ci-dessus resterait vert si l'appel de P6 disparaissait et qu'un autre
# apparaissait ailleurs — un compte n'est pas une identite.
check("M16src_le_troisieme_appelant_est_le_bouton_de_remplacement",
      "openPicker(sel.tr)" in P.R_M16 and s.count(nl("openPicker(sel.tr)")) == 1,
      f'count={s.count(nl("openPicker(sel.tr)"))}')
# ── les libelles qui mentaient ────────────────────────────────────────────
check("M16_les_boutons_de_piste_disent_qu_ils_ajoutent_une_piste",
      nl('children:"+ piste vidéo"') in s and nl('children:"+ piste audio"') in s
      and s.count(nl('children:"+ vidéo"')) == 0
      and s.count(nl('children:"+ audio"')) == 0,
      "« + vidéo » / « + audio » ajoutent une PISTE et ne le disent pas")
# ── addAsset : la piste v2 en dur a disparu ───────────────────────────────
# Le détail comptait `"var tr2=trId||\"` — un guillemet de tête et une
# contre-oblique qui n'existent nulle part dans le bundle : la chaîne vaut
# TOUJOURS 0, et l'échec aurait affiché « count=0 » en même temps qu'il
# reprochait une occurrence. On imprime la quantité que la condition mesure.
_tr2_dur = s.count(nl('var tr2=trId||"v2"'))
check("M16a_la_piste_v2_en_dur_a_disparu", _tr2_dur == 0,
      f"« var tr2=trId||\"v2\" »={_tr2_dur} (attendu 0)")
# LES DEUX SECTIONS P9 DU CORPS DU COMPOSANT, ensemble. `dzAddWhenReady` a
# quitté `addAsset` pour R_M16REF (elle n'y était joignable par aucun
# démontage) : les identifiants qu'elle appelle vivent donc désormais dans
# R_M16REF, et mesurer R_M16A SEULE laisserait la moitié du greffon sans
# contrôle. Le couple est déjà le motif employé plus bas pour
# `dzTracksRef` / `dzMoved` / `dzReadyRef`.
_P9C = P.R_M16REF + P.R_M16A
# `addAsset` — LE TROU. Mesuré le 04/09/2026 : en renommant la déclaration
# `function addAsset(src,label,kind,srcDur,trId,atTime){` en `addAssetX` dans
# le bundle LIVRÉ, le banc restait à 255 passed, 0 failed — alors que les sept
# appelants et la relance de `dzAddWhenReady` étaient morts, et que
# `node --check` passe (un nom libre est du JavaScript parfaitement valide).
# C'est exactement la classe de panne que ce contrôle à deux faces existe pour
# attraper. (`svmTracksOf` est déjà couvert par la boucle de M16lib.)
for _nm, _decl in (("pickTrack", "function dzmPickTrack(ts,kind){"),
                   ("dzTracksRef", "var dzTracksRef=x.useRef(null);"),
                   ("durRef", "var durRef=x.useRef(proj.dur);"),
                   ("fireNote", "fireNote=nt[1]"),
                   ("addAsset",
                    "function addAsset(src,label,kind,srcDur,trId,atTime){")):
    _ap = re.search(r"\b%s\b" % re.escape(_nm), _P9C) is not None
    check("M16a_appelle_" + _nm + "_qui_est_declare",
          _ap and s.count(nl(_decl)) >= 1,
          f"appelé={_ap} déclaré={s.count(nl(_decl))} ({_decl})")
# LE GREFFON AMONT EST INTACT, et c'est le point : la correction se porte en
# AVAL. Si cette ligne rougit, quelqu'un a edite patch_bundle_libsend.py — le
# maillon dont le rejeu solitaire efface tout ce qui suit.
check("M16a_le_greffon_amont_n_a_pas_ete_touche",
      s.count(nl('addAsset({job_id:p.job_id},p.title||p.job_id,'
                 '"video",p.dur||0,"v2")')) == 1
      and s.count("window.__dzMontageAdd") >= 1,
      "le greffon libsend a bougé — la correction devait rester en aval")
# LES TROIS REFUS SORTENT AVANT `pushHistory()` : un clip refusé ne doit pas
# laisser derrière lui une entrée d'historique qui ne défait rien.
_a0 = s.find(nl(P.R_M16A))
_a1 = s.find(nl(P.R_M16B), _a0 if _a0 >= 0 else 0)
_body = s[_a0:_a1] if _a0 >= 0 and _a1 > _a0 else ""
# `pushHistory();` AVEC le point-virgule : c'est l'APPEL. Sans lui la mesure
# tombait sur la mention `pushHistory()` du commentaire de la section, 800
# caractères plus haut que l'appel — et la ligne rougissait à tort.
# QUATRE `;return}` dans la section : les trois refus PLUS le relais de
# `dzAddWhenReady` vers addAsset. Un refus dont on retirerait le `return`
# tomberait dans `pushHistory()` et poserait le clip quand même — l'ordre
# textuel seul ne le verrait pas, puisque la note resterait au même endroit.
#
# `rfind` / `find`, JAMAIS `rindex` / `index` — c'est la FAUTE N°6 du
# chantier, et la doctrine `temoin()` / `J()` / `CO()` de
# test_montage_sources.py interdit exactement ce motif : un banc doit ROUGIR,
# pas MOURIR. MESURE du 04/09/2026, rejouée : en reformulant les deux notes
# de refus dans le patcher — une passe de relecture parfaitement plausible —
# `--check` reste OK, le patcher se rejoue, et le `rindex` NU d'ici levait
# `ValueError: substring not found` : traceback, exit 1, AUCUNE ligne de
# compte imprimée, 239 des 254 assertions jamais jouées (la section [2]
# `node --check`, la section [3] du cœur sous node, et tout le reste de
# [1-quater]). Le voisin `index` était, lui, déjà protégé par le
# `count == 1` qui le précède dans le `and`.
# Les deux repères valent -1 quand ils manquent, et la ligne EXIGE qu'ils
# aient été trouvés : un `>= 0` oublié ferait passer `-1 < 3807` au VERT sur
# une note disparue — on aurait remplacé une mort par une assertion creuse.
_i_refus = _body.rfind(nl("n'a pas été posé"))
_i_push = _body.find("pushHistory();")
# Compté sur LE COUPLE : deux des quatre `;return}` (le relais vers addAsset
# et le refus du plafond) ont suivi `dzAddWhenReady` dans R_M16REF. Le total
# du greffon P9 est inchangé — c'est lui qui compte, pas sa répartition.
_n_ret = _P9C.count(";return}")
check("M16a_refuse_avant_de_pousser_l_historique",
      bool(_body) and _body.count("pushHistory();") == 1 and _n_ret == 4
      and _i_refus >= 0 and _i_push >= 0 and _i_refus < _i_push,
      f"dernier refus={_i_refus} pushHistory();={_i_push} "
      f"returns={_n_ret} corps={len(_body)} o "
      "— un refus laisse une entrée d'historique derrière lui")
# L'ATTENTE est bornée ET dite : le greffon amont, lui, avale tout dans un
# catch muet. Le plafond est de 20 s (`Date.now()+20000`) — un CHOIX, pas une
# mesure ; le dernier conjoint lit cette VALEUR dans le code livré. Il y
# lisait naguère la phrase « PLAFOND CHOISI, pas une mesure », c'est-à-dire un
# COMMENTAIRE : une assertion sur une orthographe, rouge à la moindre
# reformulation et verte avec les bons mots, pendant que le plafond réel
# pouvait glisser sans un bruit. Le commentaire qui l'accompagnait annonçait
# d'ailleurs « 6 s » quand le code bornait à 20 s.
# LA GARDE ELLE-MEME, pas seulement le texte de la note. MESURE : en
# desarmant la condition, le banc restait ENTIEREMENT vert parce que les
# chaines de la note survivaient a la mutation. La ligne qui decide est la
# premiere.
# LA CONDITION EST `dzReadyRef`, PAS `dur > 0` — et c'est une RECTIFICATION du
# brief de la tache, mesuree : l'etat initial du composant est
# `{demo:!0,…,dur:SVM_DEMO_DUR,…}` avec `var SVM_DEMO_DUR=64` (son-vfx-
# montage.js l.820), donc `durRef.current` ne vaut JAMAIS 0 et une garde
# `dur > 0` aurait ete du code mort. Ce que le retard de GET /project casse
# vraiment : `proj` reste la MAQUETTE (sans `tracks`, donc les six pistes
# historiques, v2 comprise) et `svmApplyProject` fait ensuite `setClips(cs)`,
# qui remplace la liste entiere — le clip pose entre-temps est efface.
check("M16a_l_attente_est_bornee_et_dite",
      "if(!dzReadyRef.current){dzAddWhenReady(" in P.R_M16A
      and "Date.now()>=until" in P.R_M16REF
      and "if(dzReadyRef.current){addAsset(" in P.R_M16REF
      and "n'a pas été posé : " in P.R_M16REF
      and "Date.now()+20000);return}" in P.R_M16A,
      "l'attente n'est pas armée, pas bornée à 20 s, ou son échec est muet")
# ── LE MINUTEUR S'ÉTEINT AU DÉMONTAGE ────────────────────────────────────
# LE point le plus grave de la revue de qualité du 04/09/2026, et il n'était
# pas mesuré : `DzMontage` est monté CONDITIONNELLEMENT — quitter l'onglet le
# démonte, et la chaîne d'attente continuait de se replanifier seule jusqu'au
# plafond avant de crier dans un arbre mort (no-op silencieux de React 18).
# MESURE, en rejouant le texte LIVRÉ d'alors sous node avec une horloge
# simulée et un démontage à 300 ms : 167 reprogrammations, 20 040 ms
# d'horloge, 1 note émise dans le vide, 0 clip posé. Ni le clip, NI le
# message : le silence même que cette tâche supprime partout ailleurs.
check("M16ref_DzMontage_est_monte_conditionnellement",
      s.count(nl('s==="montage"&&r.jsx(DzMontage,{variant:e,go:a})')) == 1,
      "le montage conditionnel a changé — la garde d'extinction doit être "
      "re-justifiée avant d'être gardée")
check("M16ref_l_attente_s_eteint_au_demontage",
      "var dzAliveRef=x.useRef(!0)" in P.R_M16REF
      and "dzAliveRef.current=!1" in P.R_M16REF
      and s.count(nl("if(!dzAliveRef.current)return;")) == 1,
      "la chaîne d'attente survit au démontage : ni clip, ni message")
# LE RÉARMEMENT AU MONTAGE, pas seulement l'extinction : un effet `[]` est
# rejoué en double sous StrictMode (mount → unmount → mount), et sans cette
# ligne l'écran serait mort pour de bon dès le premier aller-retour.
check("M16ref_le_remontage_rearme_l_attente",
      s.count(nl("x.useEffect(function(){dzAliveRef.current=!0;")) == 1,
      "le démontage éteint définitivement — StrictMode suffirait à le figer")
check("M16ref_le_minuteur_en_vol_est_annule",
      "dzWaitRef.current=setTimeout(" in P.R_M16REF
      and s.count(nl("clearTimeout(dzWaitRef.current)")) == 1,
      "le minuteur en vol n'est pas annulé au démontage")
check("M16ref_l_attente_a_quitte_addAsset",
      "function dzAddWhenReady(" in P.R_M16REF
      and "function dzAddWhenReady(" not in P.R_M16A
      and s.count(nl("function dzAddWhenReady(")) == 1,
      "`dzAddWhenReady` est recréée à chaque appel, et hors de portée du "
      "démontage")
for _nv in ("dzAliveRef", "dzWaitRef"):
    _dh = s.count(_nv) - P.R_M16REF.count(_nv)
    check("M16ref_nom_" + _nv + "_n_ecrase_rien", _dh == 0,
          f"{_nv} apparaît {_dh}x hors de la section qui l'écrit")
# LA MESURE QUI FONDE CE CHOIX, REJOUEE — sinon elle se perime en silence :
# la duree de depart n'est pas nulle, et `setClips` de svmApplyProject
# remplace bien la liste entiere.
check("M16a_la_duree_de_depart_n_est_pas_nulle",
      s.count(nl("var SVM_DEMO_DUR=64;")) == 1
      and s.count(nl("dur:SVM_DEMO_DUR,mixDb:SVM_DEMO_MIX})")) == 1,
      "SVM_DEMO_DUR a bougé — la garde `dzReadyRef` doit être re-justifiée")
check("M16a_le_chargement_du_projet_remplace_les_clips",
      s.count(nl("setClips(cs);setSelId(first?first.id:\"\");")) == 1,
      "svmApplyProject ne remplace plus la liste : la course a changé de forme")
# `dzReadyRef` suit CHAQUE rendu, comme dzTracksRef.
check("M16ref_l_etat_pret_suit_chaque_rendu",
      s.count(nl("dzReadyRef.current=!proj.demo;")) == 1,
      f'count={s.count(nl("dzReadyRef.current=!proj.demo;"))}')
_deh3 = s.count("dzReadyRef") - (P.R_M16REF + P.R_M16A).count("dzReadyRef")
check("M16ref_nom_dzReadyRef_n_ecrase_rien", _deh3 == 0,
      f"dzReadyRef apparaît {_deh3}x hors des sections qui l'écrivent")
# MEME MESURE, meme conclusion : `if(0){fireNote(…)…return}` laissait tout
# vert — le refus etait mort et son texte toujours la.
check("M16a_refuse_quand_aucune_piste_ne_convient",
      "if(!tr2){fireNote(" in P.R_M16A
      and "porte aucune piste " in P.R_M16A,
      "le refus ne s'arme pas : un clip partirait dans le vide sans un mot")
# ── la ref des pistes suit CHAQUE rendu ───────────────────────────────────
check("M16ref_la_ref_suit_chaque_rendu",
      s.count(nl("dzTracksRef.current=svmTracksOf(proj);")) == 1,
      f'count={s.count(nl("dzTracksRef.current=svmTracksOf(proj);"))}')
_dehors = s.count("dzTracksRef") - (P.R_M16REF + P.R_M16A).count("dzTracksRef")
check("M16ref_nom_dzTracksRef_n_ecrase_rien", _dehors == 0,
      f"dzTracksRef apparaît {_dehors}x hors des sections qui l'écrivent")
# ── la note dit OU le clip a atterri, et nomme la sortie ──────────────────
# `(dzMoved?` — LA CONDITION, pas la seule presence du nom. MESURE : en la
# remplacant par `(0?`, la note redevenait muette sur la piste reelle et le
# banc restait vert, `dzMoved` figurant encore dans la branche morte.
check("M16b_la_note_nomme_la_piste_reelle_et_la_sortie",
      s.count(nl(P.R_M16B)) == 1 and "(dzMoved?" in P.R_M16B
      and '« + piste "+dzMot+" »' in P.R_M16B
      and "dzMoved" in P.R_M16A,
      f"count={s.count(nl(P.R_M16B))}")
# LE MOT DE LA PISTE EST CHOISI, PAS ÉCRIT EN DUR. La note annonçait « + piste
# vidéo » même pour une piste AUDIO, alors que le refus voisin choisissait
# déjà le mot. CHEMIN ATTEIGNABLE, lu dans le bundle livré : `svmSfxTrackOf`
# rend a1/a2/a3 EN DUR et `dzmRemove` ne protège que v1 et s1 — un projet dont
# A3 a été retiré, puis un bruitage inséré depuis le tiroir Sons, et la note
# disait « Recréer A3 avec « + piste vidéo » ».
# LES DEUX EMPLOIS lisent le MÊME `dzMot` : mesurer la seule note laisserait
# passer un refus retombé en dur, et réciproquement.
check("M16b_le_mot_de_la_piste_est_choisi_pas_ecrit_en_dur",
      'var dzMot=dzWant==="audio"?"audio":"vidéo";' in P.R_M16A
      and '« + piste "+dzMot+" »' in P.R_M16A
      and '« + piste "+dzMot+" »' in P.R_M16B
      and "« + piste vidéo »" not in P.R_M16B
      and "« + piste vidéo »" not in P.R_M16A,
      "la note ou le refus nomme « vidéo » en dur — faux sur une piste audio")
check("M16b_svmSfxTrackOf_peut_toujours_nommer_une_piste_absente",
      s.count(nl('function svmSfxTrackOf(kind){return kind==="voix"?"a1":'
                 'kind==="musique"?"a2":"a3"}')) == 1
      and s.count(nl('return (id==="v1"||id==="s1")?ts:'
                     'ts.filter(function(t){return t.id!==id})')) == 1,
      "la mesure qui fonde le choix du mot a bougé — a1/a2/a3 en dur, et "
      "dzmRemove ne protège que v1 et s1")
# CE QUE LA NOTE DIT DU CLIP QU'ON POSE, et pas seulement des anciens. Sans
# V2, `pickTrack` rend `v1` — la piste de FOND, que le rendu CONCATÈNE
# (`v1_in` trié par `start`) : le film gagne un plan de plus, pas une
# incrustation, alors que le libellé de la Bibliothèque promet un « overlay ».
# La piste n'est PAS créée d'office, et le commentaire de la section porte les
# deux mesures qui l'interdisent (`dzmAdd` rend le plus petit identifiant
# libre — donc `a2`, bus « musique », pour une demande « a3 » sur [v1,a1,s1] —
# et `pushHistory` ne mémorise que {clips, mixDb}, donc une piste créée
# survivrait à « annuler » et l'autosave l'écrirait dans le projet).
check("M16b_la_note_dit_ce_qui_arrive_au_clip_qu_on_pose",
      "clip vient d'être posé sur \"+tr2.toUpperCase()" in P.R_M16B
      and '(tr2==="v1"?' in P.R_M16B
      and "s'AJOUTE À LA SUITE des plans" in P.R_M16B,
      "la note explique la piste absente sans dire ce que devient le clip "
      "qu'on vient de poser")
check("M16b_v1_est_bien_une_sequence_concatenee",
      SVC.count('v1_in = sorted([c for c in clips if c.get("tr") == "v1"],')
      == 2,
      "V1 n'est plus la séquence concaténée — la phrase de la note ment")
_deh2 = s.count("dzMoved") - (P.R_M16A + P.R_M16B).count("dzMoved")
check("M16b_nom_dzMoved_n_ecrase_rien", _deh2 == 0,
      f"dzMoved apparaît {_deh2}x hors des sections qui l'écrivent")
# ── le sélecteur applique LA règle du rendu ───────────────────────────────
check("M16c_le_selecteur_interroge_la_route_du_backend",
      s.count(nl('fetch("/api/montage/media-rules")')) == 1
      and s.count("DzTracks.isVideoJob") == 1,
      f'route={s.count(nl(chr(34)+"/api/montage/media-rules"+chr(34)))}')
check("M16c_l_ancien_critere_a_disparu",
      s.count(nl('j3.status==="done"&&(j3.video_path||j3.final_video_path)')) == 0,
      "le critère fautif de P8 vit encore dans le sélecteur")
# LA REGLE N'EST PAS RECOPIEE. Une seconde liste d'extensions en JavaScript
# divergerait de `_VIDEO_EXTS` au premier format ajouté : la couche ne doit en
# citer AUCUNE. Mesure sur le fichier de la couche, pas sur le patcher.
_copiees = [e for e in (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")
            if e in src]
check("M16c_la_couche_ne_recopie_aucune_extension", _copiees == [],
      f"la couche cite {_copiees} — c'est la seconde copie qu'on refuse")
check("M16c_dit_a_l_ecran_qu_il_ne_filtre_pas",
      "if(!xt)fireNote(" in P.R_M16C and "PAS filtrée" in P.R_M16C,
      "une règle injoignable passerait sans un mot")
# LA ROUTE EXISTE, et elle sert LA MEME liste que le pré-vol du rendu :
# contrôle à deux faces, côté serveur cette fois.
check("backend_sert_la_regle_d_extensions",
      SVC.count('@router.get("/media-rules")') == 1
      and SVC.count('return {"video_exts": list(_VIDEO_EXTS)}') == 1,
      "GET /api/montage/media-rules absente ou ne sert pas _VIDEO_EXTS")
# LA FONCTION ENTIERE, en-tete comprise. MESURE : la sous-chaine
# `return p.suffix.lower() in _VIDEO_EXTS` vaut 2 dans ce fichier — la
# seconde est la premiere moitie de `_ffmpeg_ouvrira`, qui teste
# `_VIDEO_EXTS + _IMAGE_EXTS + _AUDIO_EXTS`. Vider `_is_video_artifact`
# laissait donc la ligne VERTE.
# Cette ligne ne mesure que la FORME de la règle, jamais son CONTENU — et
# c'était le trou : des trois maillons, la route suivait, le filtre client
# suivait, et le banc RECOPIAIT la liste dans sa sonde node. Le contenu est
# désormais tenu ailleurs, par l'EXTRACTION qui alimente cette sonde (voir
# `backend_la_liste_video_est_extractible_pour_le_banc`, section [3]).
check("backend_la_regle_servie_est_celle_du_rendu",
      SVC.count("_VIDEO_EXTS = (") == 1
      and SVC.count("def _is_video_artifact(p: Path) -> bool:\n"
                    "    return p.suffix.lower() in _VIDEO_EXTS\n") == 1,
      "_VIDEO_EXTS n'est plus la règle unique du rendu")
# ── `v1_non_video` enfin LU ───────────────────────────────────────────────
check("backend_signale_toujours_les_clips_v1_non_video",
      SVC.count('out["v1_non_video"] = non_video') == 1,
      "le champ que M16d lit n'est plus produit")
check("M7_la_restauration_porte_le_champ_jusqu_a_la_timeline",
      "v1NonVideo:Array.isArray(d.v1_non_video)" in P.R_M7
      and s.count(nl("v1NonVideo:Array.isArray(d.v1_non_video)")) == 1,
      "le champ n'arrive pas jusqu'à `proj`")
# `c.tr==="v1"` EN PLUS de l'appartenance a la liste : le champ ne porte que
# des clips V1, mais un clip DEPLACE sur une piste d'incrustation ne doit plus
# etre marque — une image y est parfaitement legitime (le pre-vol la laisse
# passer, cf. `backend_le_prevol_laisse_passer_une_image`).
check("M16d_marque_les_clips_signales",
      s.count(nl(P.R_M16D)) == 1 and "proj.v1NonVideo" in P.R_M16D
      and 'c.tr==="v1"&&' in P.R_M16D,
      f"count={s.count(nl(P.R_M16D))}")
check("M16d_utilise_DzTracks_pas_DzMontage",
      "DzMontage.badSrc" not in s and s.count("DzTracks.badSrc") == 1,
      f'count={s.count("DzTracks.badSrc")}')
# LA SORTIE EST OFFERTE SUR PLACE — le même geste que « Bibliothèque… », et
# sur la piste DU CLIP, pas sur une piste devinée.
check("M16d_offre_la_sortie_sur_place",
      "openPicker(c.tr)" in P.R_M16D,
      "la chip signale sans offrir de sortie")
# ── la feuille habille les deux nouveautés ────────────────────────────────
_css = CSS.read_text(encoding="utf-8")
check("css_porte_le_bouton_bibliotheque",
      ".dzm-libb{" in _css.replace(" ", "").replace("\n", "").replace("\r", "")
      and "dzm-libb" in src, "montage.css n'habille pas « Bibliothèque… »")
check("css_porte_la_chip_pas_une_video",
      ".dzm-badsrc{" in _css.replace(" ", "").replace("\n", "").replace("\r", "")
      and ".dzm-badsrc:hover" in _css and "dzm-badsrc" in src,
      "montage.css n'habille pas la chip « pas une vidéo »")
# Le CŒUR de P9 doit être DANS le bloc livré, pas seulement dans la source.
check("bloc_contient_pickTrack_et_isVideoJob",
      nl("pickTrack:dzmPickTrack,isVideoJob:dzmIsVideoJob,") in s
      and nl("function dzmIsVideoJob(j,exts){") in s)

print("\n[1-sexies] P6 — remplacer la source d'un plan (M4b, M15, M16src)")
# Les deux couples ancre -> remplacement sont deja mesures par la boucle du
# debut (importlib : aucune copie). Ce qui suit tient ce que cette boucle ne
# peut pas voir.
#
# L'ANCRE DE M16src, ET CELLE QUE LE PLAN CROYAIT CONSOMMEE. Le plan
# annoncait `        transInspector(),` « deja consommee par M13 » : elle ne
# l'est pas — elle vaut 1 (R_M12 la reprend en tete) et la ligne
# `M13_ancre_du_plan_libre_mais_ecartee` ci-dessus le tient deja. P6 ne l'a
# pas prise NON PLUS, et pour une raison qui lui est propre : son bouton se
# pose ENTRE la fenetre « In / Out » qu'il recale et l'inspecteur de
# transition qu'il conserve. Cette ligne-ci mesure que l'ancre RETENUE est
# bien celle-la, et pas `transInspector(),` reprise en douce.
check("M16src_ancre_choisie_est_celle_de_l_inspecteur_de_sous_titres",
      P.A_M16 == "        subsInspector()," and "transInspector" not in P.A_M16
      and s.count(nl("        subsInspector(),")) == 1,
      f'A_M16={P.A_M16!r} count={s.count(nl("        subsInspector(),"))}')
# `DzMontage.replaceSrc` / `DzMontage.NewerHint` etaient les appels du plan —
# TROISIEME fois qu'il ecrit ce nom, qui est celui d'une fonction de PREMIER
# NIVEAU du bundle. Interdit, cf. node_check_module.
check("M16src_utilise_DzTracks_pas_DzMontage",
      "DzMontage.replaceSrc" not in s and "DzMontage.NewerHint" not in s
      and "DzMontage.replaceBtn" not in s and "DzMontage.revertBtn" not in s
      and s.count("DzTracks.replaceBtn") == 1
      and s.count("DzTracks.NewerHint") == 1,
      f'replaceBtn={s.count("DzTracks.replaceBtn")} '
      f'NewerHint={s.count("DzTracks.NewerHint")}')
# Controle a DEUX FACES, comme M10/M12/M13/M14/M16lib : chaque identifiant du
# bundle appele par R_M15 ou R_M16 doit exister, et sous le MEME nom
# (recherche bornee). Verifier une seule face laisse passer un renommage :
# mesure de la semaine derniere, renommer `addAsset` laissait le banc a 255/0
# alors que sept appelants etaient morts.
for _tag, _R, _noms in (
        ("M15", "R_M15",
         (("clipsRef", "var clipsRef=x.useRef(clips);clipsRef.current=clips;"),
          ("trackStRef", "trackStRef.current[c.tr]"),
          ("setOvPick", "setOvPick=stO[1]"),
          ("setClips", "setClips=st1[1]"),
          ("setSelId", "selRef.current=selId;"),
          ("pushHistory", "var pushHistory=x.useCallback("),
          ("setDirty", "setDirty=st8[1]"),
          ("fireNote", "fireNote=nt[1]"),
          # P6 (revue) : le refus de genre lit le MÊME `trackKind` que le
          # dépôt sur une bande — la PISTE est donc classée par une seule
          # règle en JavaScript. L'ASSET, lui, est classé PLUS STRICTEMENT
          # ici que par le dépôt : celui-ci teste `p.kind==="audio"` seul
          # (index-BEOJX8L5.js:4042), M15 teste
          # `kind==="audio"||(src&&src.audio)`. Ce n'est pas une divergence
          # subie mais un écart assumé : le dépôt reçoit un `p` de la
          # Bibliothèque, toujours porteur de `kind` ; M15 court-circuite
          # TOUS les appelants d'`addAsset`, `sfxInsert` compris, et la
          # seconde moitié du OU ferme un `src` audio dont le `kind` serait
          # menteur ou absent. Refuser plus large ne peut que refuser un
          # remplacement, jamais en laisser passer un mauvais.
          ("trackKind", 'function trackKind(trId){var k=String(trId||"")'
                        '.charAt(0);'),
          ("setDzmArm", "setDzmArm=stDZA[1];"))),
        ("M16src", "R_M16",
         (("sel", "var sel=clips.find("),
          ("ovPick", "ovPick=stO[0]"),
          ("openPicker", "function openPicker(trId){"),
          ("clipsRef", "var clipsRef=x.useRef(clips);clipsRef.current=clips;"),
          ("trackStRef", "trackStRef.current[c.tr]"),
          ("setClips", "setClips=st1[1]"),
          ("pushHistory", "var pushHistory=x.useCallback("),
          ("setDirty", "setDirty=st8[1]"),
          ("fireNote", "fireNote=nt[1]"),
          ("setDzmArm", "setDzmArm=stDZA[1];"),
          ("addAsset",
           "function addAsset(src,label,kind,srcDur,trId,atTime){"))),
        # M15b vit DANS `ovPicker`, dont le corps appartient au greffon amont
        # (son-vfx-montage.js, fichier qu'on ne touche pas) : ses référents
        # sont donc ceux d'ovPicker, plus le miroir posé par M4b.
        ("M15b", "R_M15B",
         (("dzmArm", "var stDZA=x.useState(null),dzmArm=stDZA[0],"),
          ("ovPick", "ovPick=stO[0]"),
          ("trackKind", 'function trackKind(trId){var k=String(trId||"")'
                        '.charAt(0);'),
          ("svmShort", "function svmShort(s){"),
          ("ph", "var st3=x.useState(18.4),ph=st3[0],setPh=st3[1];")))):
    _txt = getattr(P, _R)
    for _nm, _decl in _noms:
        _ap = re.search(r"\b%s\b" % re.escape(_nm), _txt) is not None
        check(_tag + "_appelle_" + _nm + "_qui_est_declare",
              _ap and s.count(nl(_decl)) >= 1,
              f"appelé={_ap} déclaré={s.count(nl(_decl))} ({_decl})")
# LE MODE EST DECLARE PAR M4b, et il est DESARME. Sans l'effet, un selecteur
# ferme sans choisir — ou rouvert sur une AUTRE piste — laissait le mode arme,
# et le clip suivant venait ecraser la source d'un plan que l'utilisateur ne
# regardait plus. Les DEUX lignes : la ref, et son extinction.
check("M4b_declare_la_ref_du_mode_remplacement",
      s.count(nl("  var dzmReplaceRef=x.useRef(null);")) == 1
      and "dzmReplaceRef" in P.R_M4b,
      f'count={s.count(nl("  var dzmReplaceRef=x.useRef(null);"))}')
check("M4b_desarme_le_mode_quand_le_selecteur_change",
      s.count(nl("    if(rp&&ovPick!==rp.tr){dzmReplaceRef.current=null;\n"
                 "      setDzmArm(null)}},[ovPick]);")) == 1,
      "le mode remplacement n'a pas d'extinction")
# LE MIROIR D'AFFICHAGE du mode. Une ref ne re-rend pas : sans cet état, le
# sélecteur ne pouvait pas DIRE qu'il est armé au moment où il l'est. La ref
# reste la seule autorité que lit `addAsset` — l'état ne décide de RIEN, et
# les deux lignes ci-dessous le tiennent ensemble (déclaration + extinction,
# la seconde étant déjà mesurée juste au-dessus).
check("M4b_declare_le_miroir_d_affichage_du_mode",
      s.count(nl("  var stDZA=x.useState(null),dzmArm=stDZA[0],"
                 "setDzmArm=stDZA[1];")) == 1
      and "dzmArm" in P.R_M4b,
      "le mode armé n'a pas de miroir d'affichage")
# LES DEUX SITES D'ARMEMENT ARMENT LES DEUX CHOSES. « Le miroir ne peut pas
# diverger de la ref » est la propriete qui rend M15b fiable, et elle tenait
# a un DETAIL du site appelant : `DzmNewerHint.onPick` armait la ref SEULE
# (sans `label`, sans `setDzmArm`), et cela ne se voyait pas parce qu'il
# appelle `addAsset` de facon SYNCHRONE dans le meme gestionnaire — aucun
# rendu ne s'intercale, M15 eteint le miroir avant qu'il ne s'affiche. Une
# surete qui repose sur la synchronie d'un appelant ne survit pas au premier
# `await` qu'on y ajoutera : le mode resterait arme et le selecteur, rouvert,
# se dirait encore « Ajouter sur la piste V1 » — la faute exacte que M15b
# ferme. Les deux sites ecrivent donc la meme paire, et cette ligne COMPTE
# les deux moities ensemble, dans le patcher ET dans le livre : elles ne
# peuvent plus se desolidariser en silence. Un `in` ne l'aurait pas vu — il
# etait deja vert sur la version asymetrique.
_arm_ref = P.R_M16.count("dzmReplaceRef.current={")
_arm_mir = P.R_M16.count("setDzmArm({")
check("les_deux_sites_arment_la_ref_ET_le_miroir",
      _arm_ref == 2 and _arm_mir == 2
      and s.count(nl("dzmReplaceRef.current={")) == 2
      and s.count(nl("setDzmArm({")) == 2
      # ...et l'armement du rappel porte le LIBELLE, comme celui du bouton :
      # c'est lui que le titre du sélecteur affiche.
      and nl("          onPick:function(c){dzmReplaceRef.current={id:sel.id,\n"
             "            tr:sel.tr,label:sel.label};\n"
             "            setDzmArm({tr:sel.tr,label:sel.label});") in s,
      f'patcher ref={_arm_ref} miroir={_arm_mir} · '
      f'livré ref={s.count(nl("dzmReplaceRef.current={"))} '
      f'miroir={s.count(nl("setDzmArm({"))}')
# ET LE COMPTE DES EXTINCTIONS LEUR REPOND : deux armements, deux
# extinctions (l'effet de desarmement de M4b, et M15 quand il consomme le
# mode). Compter un seul cote laisserait passer un armement de plus.
check("chaque_armement_a_son_extinction",
      s.count(nl("dzmReplaceRef.current=null")) == 2
      and s.count(nl("setDzmArm(null)")) == 2,
      f'ref={s.count(nl("dzmReplaceRef.current=null"))} '
      f'miroir={s.count(nl("setDzmArm(null)"))}')
# GESTE DESTRUCTIF : `pushHistory` AVANT l'ecriture, une seule entree pour le
# geste — dans les DEUX sens (remplacer, et revenir en arriere).
check("M15_pousse_l_historique_avant_d_ecrire",
      nl("      pushHistory();\n"
         "      setClips(rcs.map(function(k){return k.id===rc.id?rr.clip:k}));")
      in s, "l'ordre pushHistory -> setClips n'est pas celui du bundle livré")
check("M16src_le_retour_arriere_pousse_aussi_l_historique",
      nl("          var rv=DzTracks.revertSrc(sel);if(!rv)return;\n"
         "          pushHistory();") in s,
      "« Revenir à la version précédente » écrit sans instantané")
# LES TROIS REFUS SORTENT AVANT toute ecriture : aucun geste destructif n'a
# eu lieu quand le plan vise a disparu, quand le genre ne correspond pas, ou
# quand sa piste est verrouillee.
#
# FAUTE N°6, CINQUIEME MORSURE — corrigee ici. Ces bornes etaient lues avec
# `str.index`, qui LEVE ; les arguments de `check()` sont evalues AVANT
# l'appel ; et c'est du code de MODULE, hors de tout `try`. MESURE DEUX FOIS
# le 05/09/2026, sur ce banc-ci :
#   MD1 — le refus `if(!rk)` retire de R_M15 (une garde qu'un refactor
#         jugerait redondante) : rc=1, ValueError: substring not found,
#         206 assertions imprimees sur 304, AUCUN bilan. 98 perdues en
#         silence, dont TOUTE la section [3] (le cœur execute sous node).
#   MD2 — « verrouillée » reformule en « bloquée » dans le message affiche
#         — une simple reformulation de texte utilisateur : mort identique,
#         206/304.
# Trois sous-chaines sont exposees, dont un MESSAGE UTILISATEUR : la chose la
# plus susceptible d'etre reecrite du lot. `find` rend -1 au lieu de lever, et
# le detail NOMME celle qui a disparu — c'est le detail qui devient le temoin.
_M15_BORNES = ("if(!rk)", "rkd!==akd", "verrouillée")
_m15 = dict((_n, P.R_M15.find(_n)) for _n in _M15_BORNES + ("pushHistory()",))
_m15_abs = [_n for _n, _i in _m15.items() if _i < 0]
check("M15_les_trois_refus_precedent_pushHistory",
      not _m15_abs
      and all(_m15[_n] < _m15["pushHistory()"] for _n in _M15_BORNES),
      ("sous-chaîne(s) ABSENTE(S) de R_M15 : " + ", ".join(_m15_abs)
       if _m15_abs else f"un refus passe après l'instantané — {_m15}"))
# LE REFUS DE GENRE, celui qui manquait. Le sélecteur n'a NI voile NI
# backdrop (`.svm-pop` : absolute, top 52, right 18, width 300, z-index 20 —
# lu dans shared/son-vfx-montage.css) : tout le reste de l'écran reste
# cliquable pendant que le mode est armé, et `sfxInsert` (tiroir Sons, état
# `sfxOn` INDÉPENDANT d'`ovPick`) appelle `addAsset({audio:fn},…,"audio",…)`.
# MESURÉ sous node : `replaceSrc` accepte l'objet tel quel — le `src` d'un
# plan V1 devenait `{audio:"…"}`, bornes/effets/transition conservés et fin
# ramenée à la durée du .wav. Aucun contrôle de genre nulle part.
check("M15_refuse_un_genre_incompatible",
      'var rkd=trackKind(rk.tr);' in P.R_M15
      and 'var akd=(kind==="audio"||(src&&src.audio))?"audio":"video";'
      in P.R_M15
      and "if(rkd!==akd){" in P.R_M15
      and nl('      var rkd=trackKind(rk.tr);') in s,
      "un son peut encore devenir la source d'un plan vidéo")
# ET LE GENRE PASSE AVANT LE VERROU : déverrouiller la piste ne rendrait pas
# un .wav valide pour un plan vidéo, et le message du verrou enverrait
# l'utilisateur dans le mur.
check("M15_le_genre_est_refuse_avant_le_verrou",
      _m15["rkd!==akd"] > 0 and _m15["verrouillée"] > 0
      and _m15["rkd!==akd"] < _m15["verrouillée"],
      f'genre à {_m15["rkd!==akd"]}, verrou à {_m15["verrouillée"]}')
# LE VERROU DE PISTE, sur la piste DU PLAN VISE (pas celle qu'addAsset
# resoudrait) — l'idiome du composant, applique a sa propre cible.
check("M15_refuse_sur_une_piste_verrouillee",
      "trackStRef.current[rk.tr]&&trackStRef.current[rk.tr].l" in P.R_M15,
      "le remplacement ignore le verrou de piste")
check("M16src_n_arme_pas_sur_une_piste_verrouillee",
      "trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l" in P.R_M16,
      "le bouton arme le mode alors que le sélecteur refusera d'ouvrir")
# « REVENIR À LA VERSION PRÉCÉDENTE » IGNORAIT LE VERROU. Ce geste réécrit
# `src`, `label`, `srcIn` ET `end` — donc le bord droit du clip sur la
# timeline. M15 refuse sur une piste verrouillée, M16src refuse même d'ARMER,
# et le retour arrière passait sans rien demander : le SEUL geste destructif
# de cet écran à le faire. La garde est posée AVANT `revertSrc` (donc avant
# `pushHistory`), et le compte ci-dessous vaut 2 dans le remplacement — une
# fois pour armer, une fois pour revenir. Compter, pas seulement chercher :
# un `in` restait vert sur la version qui n'en avait qu'une.
_m16_verrous = P.R_M16.count(
    "trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l")
check("M16src_le_retour_arriere_refuse_sur_une_piste_verrouillee",
      _m16_verrous == 2
      and P.R_M16.find("rendre à ce plan sa source") > 0
      and (P.R_M16.find("rendre à ce plan sa source")
           < P.R_M16.find("DzTracks.revertSrc(sel)")),
      f'{_m16_verrous} garde(s) de verrou dans M16src '
      f'(2 attendues : armer, revenir)')
# M15 court-circuite AVANT la resolution de piste posee par la tache 16 : un
# remplacement garde la piste du plan et n'en choisit aucune. L'ORDRE se lit
# dans le bundle LIVRE, pas dans l'intention.
_i15 = s.find(nl("if(dzmReplaceRef.current){"))
_i16a = s.find(nl("var dzTs=dzTracksRef.current||svmTracksOf(proj);"))
check("M15_court_circuite_avant_la_resolution_de_piste",
      _i15 > 0 and _i16a > 0 and _i15 < _i16a,
      f"mode remplacement à {_i15}, résolution de piste à {_i16a}")
# M15b — LE SÉLECTEUR DIT QU'IL EST ARMÉ. Le panneau continuait de
# s'intituler « Ajouter sur la piste V1 » et de promettre « Posé à la tête de
# lecture » pendant que le mode remplaçait : deux phrases que le mode rend
# fausses, sur le seul écran regardé au moment de choisir. `ovPicker` vit
# dans son-vfx-montage.js (qu'on ne touche pas) — la correction est donc une
# section EN AVAL de la chaîne `montage`, sur une ancre mesurée unique.
# LES DEUX MOITIÉS : le titre conditionnel ET la note conditionnelle. Une
# seule des deux aurait laissé un panneau qui se contredit.
check("M15b_le_titre_du_selecteur_nomme_le_plan_quand_le_mode_est_arme",
      nl('      r.jsx("div",{className:"svm-poptitle",children:dzmA\n'
         '        ?("Remplacer la source de « "+(dzmA.label||"ce plan")'
         '+" »")\n'
         '        :("Ajouter sur la piste "+tr2.toUpperCase())}),') in s,
      "le sélecteur s'intitule encore « Ajouter » pendant qu'il remplace")
# LA PISTE EST COMPARÉE, comme dans l'effet de désarmement de M4b. Sans
# cette égalité, un sélecteur rouvert sur une AUTRE piste aurait affiché
# « Remplacer… » le temps d'une image : l'effet de désarmement s'exécute
# APRÈS le rendu. La condition d'affichage est la même que celle de
# l'armement — pas une seconde règle qui pourrait dériver.
check("M15b_le_titre_arme_ne_vaut_que_pour_la_piste_du_plan",
      nl('    var dzmA=(dzmArm&&dzmArm.tr===tr2)?dzmArm:null;') in s
      and "dzmArm.tr===tr2" in P.R_M15B,
      "le panneau peut s'annoncer armé sur une piste qui ne l'est pas")
check("M15b_la_note_du_selecteur_dit_ce_que_le_prochain_choix_fera",
      "children:dzmA?(\"Le prochain élément choisi REMPLACERA la source"
      in P.R_M15B
      and "REMPLACERA la source de ce plan" in s
      # la note DÉCLARE le glisser-déposer, qui passe par le même addAsset
      # et jette la piste visée comme l'instant du dépôt.
      and "Un glisser-déposer compte aussi comme un choix" in s
      and "Fermez ce panneau pour annuler" in s,
      "la note du sélecteur promet encore « Posé à la tête de lecture »")
# ET L'ANCIENNE NOTE SURVIT POUR LE MODE NORMAL : la section remplace deux
# phrases, elle n'en supprime aucune. Le compte 1 dit que le mode normal
# garde exactement son texte — et qu'il ne l'a pas gagné DEUX fois.
check("M15b_le_mode_normal_garde_son_texte",
      s.count(nl('Posé à la tête de lecture ("+svmShort(ph)+"). '
                 'A1 = dialogue')) == 1
      and s.count(nl("Ajouter sur la piste \"+tr2.toUpperCase()")) == 1,
      "le texte du mode normal a été perdu ou dupliqué")
# LE MIROIR EST ARMÉ ET ÉTEINT AUX DEUX BOUTS : posé par M16src (avec le
# libellé que le titre affiche), éteint par M15 dès la consommation. Sans
# l'extinction, un panneau rouvert après un remplacement se serait intitulé
# « Remplacer la source de … » alors que le mode était retombé.
check("M15b_le_miroir_est_arme_par_le_bouton_et_eteint_a_la_consommation",
      "setDzmArm({tr:sel.tr,label:sel.label});" in P.R_M16
      and "label:sel.label};" in P.R_M16
      and "dzmReplaceRef.current=null;\n      setDzmArm(null);" in P.R_M15,
      "le miroir d'affichage n'est pas tenu aux deux bouts")
# ── la feuille habille les nouveautés de P6 ───────────────────────────────
_css6 = _css.replace(" ", "").replace("\n", "").replace("\r", "")
check("css_porte_les_deux_boutons_de_remplacement",
      ".dzm-repl," in _css6 and ".dzm-revert{" in _css6
      and "dzm-repl" in src and "dzm-revert" in src,
      "montage.css n'habille pas « Remplacer la source… »")
check("css_porte_le_rappel_version_plus_recente",
      ".dzm-newerb{" in _css6 and ".dzm-newerb:hover" in _css6
      and "dzm-newerb" in src,
      "montage.css n'habille pas le rappel « version plus récente »")
# Le CŒUR de P6 doit être DANS le bloc livré, pas seulement dans la source.
check("bloc_contient_replaceSrc_et_revertSrc",
      nl("replaceSrc:dzmReplaceSrc,revertSrc:dzmRevertSrc,") in s
      and nl("function dzmReplaceSrc(c,src,label,srcDur,now){") in s
      and nl("function dzmRevertSrc(c){") in s)

print("\n[1-septies] P10 — la timeline s'etend au lieu de rogner (M17a…M17g)")
# LE DEFAUT, mot pour mot : « j'ai voulu ajouter trois videos depuis la
# bibliotheque, or la timeline est fixe, je suis oblige de raccourcir des
# pistes video pour les faire rentrer ». TROIS gestes rognaient contre
# `proj.dur` EN SILENCE, et RIEN n'ecrivait `proj.dur` apres le chargement.
#
# CINQ FORMES DE ROGNAGE, comptees a ZERO dans le bundle LIVRE. Les lignes
# `M17*_ancre_consommee` ci-dessus prouvent que l'ancre EXACTE a disparu ;
# celles-ci prouvent que le PLAFOND lui-meme a disparu — une reecriture qui
# le remettrait sous une autre ponctuation passerait les premieres.
for _lbl, _txt in (("ajout_point_de_depart", "Math.max(0,d-1)"),
                   ("ajout_fin", "Math.min(d,st+defaultLen"),
                   ("nudge_clavier", "Math.min(Math.max(0,d-len)"),
                   ("deplacement_souris", "Math.min(durRef.current-len"),
                   ("bord_droit", "var lim=durRef.current")):
    check("P10_le_rognage_a_disparu_" + _lbl, s.count(nl(_txt)) == 0,
          f"count={s.count(nl(_txt))}")
# `ripMax` ne servait QU'au plafond du bord droit : il part avec lui. Le
# commentaire de M17c ne le nomme pas — c'est ce qui rend ce compte possible.
check("P10_ripMax_n_est_plus_calcule", s.count("ripMax") == 0,
      f"count={s.count('ripMax')}")
# LE DEFAUT DE FOND, retourne : `proj.dur` avait UN seul ecrivain (le
# chargement) et QUATRE rogneurs. Il a maintenant QUATRE ecrivains — l'ajout,
# le nudge, le relachement du glisser, et le reglage explicite — et l'ecrivain
# historique est toujours la. Un `4` nu serait un chiffre creux : les quatre
# sections sont nommees une a une juste apres.
check("P10_la_duree_a_enfin_des_ecrivains",
      s.count(nl("Object.assign({},p,{dur:")) == 4
      and s.count(nl("dur:Math.max(1,Number(d.duration)||maxEnd)")) == 1,
      f"ecrivains={s.count(nl('Object.assign({},p,{dur:'))} "
      f"chargement={s.count(nl('dur:Math.max(1,Number(d.duration)||maxEnd)'))}")
for _t, _r in (("M17a_ajout", P.R_M17A), ("M17b_nudge", P.R_M17B),
               ("M17f_relachement", P.R_M17F), ("M17g_transport", P.R_M17G)):
    check("P10_" + _t + "_ecrit_bien_la_duree",
          "Object.assign({},p,{dur:" in _r, _r[:80])
# L'AGRANDISSEMENT EST DIT, ET CHIFFRE. « Un agrandissement silencieux est
# aussi desagreable qu'un rognage silencieux » : la note de l'ajout porte les
# DEUX durees. Elle est assemblee par M17a (`dzTail`) et emise par M16b, qui
# la concatene — les deux moitieds sont comptees ensemble, sans quoi retirer
# `+dzTail` de la note laissait la phrase construite et jamais affichee.
check("P10_M17a_la_note_dit_l_allongement_et_de_combien",
      "dzTail" in P.R_M17A and "+dzTail)}" in P.R_M16B
      and "La timeline a été allongée de " in P.R_M17A
      and "svmRuler(Math.round(dzGrew))" in P.R_M17A,
      "la note de l'ajout ne dit plus que la timeline a grandi")
# `DzTracks`, JAMAIS `DzMontage` : le bundle declare deja `function DzMontage`
# au premier niveau, et redeclarer ce nom est une SyntaxError en semantique
# MODULE — celle sous laquelle index.html charge le bundle.
check("P10_utilise_DzTracks_pas_DzMontage",
      "DzMontage.fitDur" not in s and "DzMontage.durCtl" not in s
      and s.count("DzTracks.fitDur") == 3 and s.count("DzTracks.durCtl") == 1,
      f"fitDur={s.count('DzTracks.fitDur')} durCtl={s.count('DzTracks.durCtl')}")
# CONTROLE A DEUX FACES pour CHAQUE identifiant du bundle appele par une
# section P10 : declaration ET appel, recherche BORNEE. Mesure du chantier :
# renommer `addAsset` laissait un banc a 255/0 alors que sept appelants
# etaient morts — verifier une seule face ne voit rien.
_P10SRC = P.R_M17A + P.R_M17B + P.R_M17C + P.R_M17D + P.R_M17E + P.R_M17F \
    + P.R_M17G
for _nm, _decl in (("defaultLen", "function defaultLen(kind,srcDur){"),
                   ("svmRuler", "function svmRuler(s){"),
                   ("setProj", "proj=stP[0],setProj=stP[1];"),
                   ("setClips", "setClips=st1[1]"),
                   ("setDirty", "setDirty=st8[1]"),
                   ("fireNote", "fireNote=nt[1]"),
                   ("pushHistory", "var pushHistory=x.useCallback("),
                   ("clipsRef", "var clipsRef="),
                   ("durRef", "var durRef=x.useRef(proj.dur);"),
                   ("nudgeHistAt", "var nudgeHistAt="),
                   ("tickStep", "var tickStep=[2,3,5,6,10,15,20,30,60]"),
                   ("doSnap", "function doSnap(v){if(!snap)return v;")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), _P10SRC) is not None
    check("P10_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# LA COUCHE APPELLE `svmRuler` DU BUNDLE au lieu de recopier le format m:ss.
# Deux faces la aussi : l'appel dans montage.js, la declaration dans le
# bundle. Une copie dans la couche divergerait au premier changement.
#
# RECTIFICATION MESUREE le 05/09/2026, et c'est la FAUTE N°2 prise sur le
# fait : chercher `\bsvmRuler\b` dans la couche ENTIERE etait une assertion
# CREUSE. Le commentaire d'en-tete de `fitDur` cite « svmRuler(Math.round(dur))
# » en toutes lettres — la mutation qui RECOPIE le format m:ss dans
# `dzmDurTxt` (donc qui n'appelle plus rien) laissait cette ligne VERTE, et la
# table de mutations l'a montre. On cherche donc dans la couche PRIVEE DE SES
# COMMENTAIRES, et l'on exige que le decommentage ait vraiment eu lieu : sans
# ces deux conjoints, une regexp de strip qui cesserait de mordre rendrait la
# ligne creuse a nouveau, en silence.
_src_code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
_ap_ruler = re.search(r"\bsvmRuler\(", _src_code) is not None
check("P10_la_couche_appelle_le_svmRuler_du_bundle",
      len(_src_code) < len(src) and "window.DzTracks=DzTracks;" in _src_code
      and _ap_ruler and s.count(nl("function svmRuler(s){")) == 1
      and "function svmRuler" not in src,
      f"appelé={_ap_ruler} déclaré={s.count(nl('function svmRuler(s){'))} "
      f"code={len(_src_code)}/{len(src)} o")
# ETENDRE EST SANS RISQUE POUR LE RENDU, et c'est mesure DES DEUX COTES.
# Cote client : `renderPayload` n'emporte AUCUNE cle `duration` (seulement
# `duration_master`, un booleen). Cote serveur : la duree postee n'est lue que
# par POST /save, et `_build_montage_command` recalcule `total` depuis
# `seg_durs`. Sans cette paire, P10 changerait la duree du FILM sans le dire.
# `find`, jamais `index` (faute n°6) : les deux reperes valent -1 quand ils
# manquent, et la ligne EXIGE qu'ils aient ete trouves.
_rp0 = s.find(nl("  function renderPayload(preview){"))
_rp1 = s.find(nl("  function launchRender(preview){"), _rp0 if _rp0 >= 0 else 0)
_RP = s[_rp0:_rp1] if _rp0 >= 0 and _rp1 > _rp0 else ""
check("P10_le_payload_de_rendu_n_emporte_pas_la_duree",
      bool(_RP) and "duration:" not in _RP and "duration_master:" in _RP,
      f"payload={len(_RP)} o, duration:={'duration:' in _RP}")
check("P10_le_backend_recalcule_la_duree_du_film",
      SVC.count('cur, total = "n0", seg_durs[0]') == 2
      and SVC.count('dur = float(body.get("duration") or 0)') == 1,
      f"seg_durs={SVC.count('cur, total = ' + chr(34) + 'n0' + chr(34) + ', seg_durs[0]')} "
      f"save={SVC.count('dur = float(body.get(' + chr(34) + 'duration' + chr(34) + ') or 0)')}")
# AUCUNE ENTREE D'HISTORIQUE DE PLUS. `pushHistory` ne memorise que
# {clips, mixDb} : une entree posee pour un geste qui ne change NI l'un NI
# l'autre donnerait un « annuler » qui ne retourne rien. M17a s'appuie sur le
# `pushHistory()` deja present dans addAsset (la ligne
# `M16a_refuse_avant_de_pousser_l_historique` compte 1 dans ce corps), M17b et
# M17f reprennent celui d'avant a l'identique, M17g n'en pose aucun.
# LA LIGNE VISE LE CODE, PAS LA PROSE — et elle a mordu : P11 a ajoute a
# M17a un commentaire qui NOMME `pushHistory` (« on sort ici, avant
# pushHistory ») pour dire justement qu'il n'en pose pas. La ligne rougissait
# sur une explication exacte. C'est la faute n°2 dans sa seconde forme, celle
# deja attrapee sur P10 avec `svmRuler` : une recherche de jeton qui trouve le
# commentaire au lieu du code. `_code` retire les blocs `/* … */` — et la
# ligne EXIGE qu'il en reste du code, sans quoi un stripper trop gourmand
# rendrait toutes ces negations vertes sur du vide.
def _code(js):
    """Le fragment SANS ses commentaires de bloc."""
    return re.sub(r"/\*.*?\*/", "", js, flags=re.S)


check("P10_aucune_entree_d_historique_de_plus",
      "pushHistory" not in _code(P.R_M17A)
      and "pushHistory" in P.R_M17A          # le commentaire, lui, le NOMME
      and "DzTracks.fitDur" in _code(P.R_M17A)
      and P.R_M17B.count("pushHistory();") == 1
      and P.R_M17F.count("pushHistory(h0)") == 1
      and "pushHistory" not in _code(P.R_M17G),
      f"a={'pushHistory' in _code(P.R_M17A)} "
      f"a_code={len(_code(P.R_M17A))}/{len(P.R_M17A)} o "
      f"b={P.R_M17B.count('pushHistory();')} "
      f"f={P.R_M17F.count('pushHistory(h0)')} "
      f"g={'pushHistory' in _code(P.R_M17G)}")
# LA RESERVE CENTRALE, DITE PARTOUT : `proj.dur` n'entre pas dans
# l'historique. Etendre puis annuler rend les clips, PAS la duree. Les trois
# notes de geste le disent et NOMMENT le retour ; le controle explicite le dit
# a chacune des siennes par `DZM_DUR_UNDO`, concatene dans `put`.
for _t, _r in (("M17a_ajout", P.R_M17A), ("M17b_nudge", P.R_M17B),
               ("M17f_relachement", P.R_M17F)):
    check("P10_" + _t + "_dit_que_annuler_ne_rend_pas_la_duree",
          "NE raccourcit PAS" in _r and "réglage de durée" in _r,
          "la note ne dit pas ce qu'« annuler » ne restaure pas")
check("P10_le_controle_dit_la_reserve_a_chacune_de_ses_notes",
      "« Annuler » ne rend pas la durée du projet" in src
      and src.count("msg+DZM_DUR_UNDO") == 1
      and src.count("function put(nv,msg){if(set)set(nv);"
                    "if(note)note(msg+DZM_DUR_UNDO)}") == 1,
      "les notes du contrôle ne passent plus toutes par `put`")
# M17f ETEND AU RELACHEMENT, PAS PENDANT LE GESTE — et c'est une MESURE, pas
# un gout. `pxPerS` est capture UNE fois au pointerdown ; une duree qui
# grandirait pendant le glissement re-rendrait les bandes a une autre echelle
# sans que `pxPerS` bouge, et le clip se decrocherait du curseur.
_mv0 = s.find(nl("    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;"))
_mv1 = s.find(nl('    function up(){tgt.removeEventListener("pointermove",mv);'),
              _mv0 if _mv0 >= 0 else 0)
_MV = s[_mv0:_mv1] if _mv0 >= 0 and _mv1 > _mv0 else ""
check("P10_le_geste_n_ecrit_pas_la_duree_pendant_qu_il_dure",
      bool(_MV) and "setProj" not in _MV and "DzTracks.fitDur" not in _MV,
      f"corps de mv={len(_MV)} o")
check("P10_l_echelle_du_geste_reste_figee_au_pointerdown",
      s.count(nl("var rect=laneEl.getBoundingClientRect(),"
                 "pxPerS=rect.width/durRef.current;")) == 1,
      "pxPerS n'est plus capturé une seule fois")
# M17f prend TOUS les clips, pas seulement celui qu'on tient : en ripple, ce
# sont les plans ENTRAINES qui sortent du champ, jamais celui qu'on rogne.
check("P10_le_relachement_mesure_tous_les_clips",
      "DzTracks.fitDur(clipsRef.current,durRef.current,0)" in P.R_M17F,
      "le relâchement ne regarde pas la timeline entière")
# LE PAS EST LA GRADUATION QUE LA REGLE DESSINE DEJA — pas un chiffre choisi.
check("P10_le_pas_du_reglage_est_la_graduation_de_la_regle",
      "step:tickStep" in P.R_M17G
      and s.count(nl("  var tickStep=[2,3,5,6,10,15,20,30,60]"
                     ".find(function(s){return dur/s<=11})||60;")) == 1,
      "le pas n'est plus celui de la règle")
# LE TOTAL RESTE AFFICHE : il demenage dans le controle, il ne disparait pas.
check("P10_le_total_reste_affiche_dans_le_transport",
      'dzmDurTxt(d)+" total"' in src and '" %"]}),' in P.R_M17G
      and s.count(nl('" %"]}),')) == 1,
      "le nombre affiché a disparu de la barre de transport")
check("css_habille_le_reglage_de_duree",
      ".dzm-durctl{" in CSS.read_text(encoding="utf-8").replace("\n", "")
      and '.dzm-durctl::before{content:"·"' in CSS.read_text(encoding="utf-8")
      and ".dzm-durb{" in CSS.read_text(encoding="utf-8").replace("\n", "")
      and ".dzm-durf{" in CSS.read_text(encoding="utf-8").replace("\n", ""),
      "montage.css n'habille pas le réglage de durée")
# ── P11 : LE SECOND PLAFOND, DANS LE BUNDLE LIVRE ─────────────────────────
# P10 a rendu la timeline extensible ; ces lignes-ci mesurent que la SOURCE
# n'est plus tronquee au moment ou on la pose. Les deux plafonds sont comptes
# a ZERO, mais un compte a zero est vrai sur un fichier vide comme sur une
# fonction supprimee : chaque negation exige d'abord que `defaultLen` SOIT
# LA et qu'elle delegue.
check("P11_defaultLen_existe_toujours_et_delegue_a_la_couche",
      s.count(nl("function defaultLen(kind,srcDur){")) == 1
      and s.count(nl("return DzTracks.clipLen(kind,srcDur,"
                     "{image:4,audio:8,video:6});")) == 1,
      f'decl={s.count(nl("function defaultLen(kind,srcDur){"))} '
      f'delegue={s.count(nl("return DzTracks.clipLen(kind,srcDur,"))}')
check("P11_le_plafond_video_de_six_secondes_a_disparu",
      s.count(nl("function defaultLen(kind,srcDur){")) == 1
      and s.count(nl("Math.min(6,srcDur||6)")) == 0,
      f'{s.count(nl("Math.min(6,srcDur||6)"))} restant(s)')
check("P11_le_plafond_audio_de_huit_secondes_a_disparu",
      s.count(nl("function defaultLen(kind,srcDur){")) == 1
      and s.count(nl("Math.min(8,srcDur||8)")) == 0,
      f'{s.count(nl("Math.min(8,srcDur||8)"))} restant(s)')
# LES TROIS REPLIS RESTENT DES CHIFFRES DU BUNDLE : la couche ne devient pas
# leur autorite, elle les RECOIT. C'est la meme regle que `_VIDEO_EXTS` servi
# par le backend en P9.
# DEUX occurrences dans le bundle livre, et c'est EXACTEMENT ce qu'on veut :
# une dans `defaultLen` (le bundle PASSE ses replis) et une dans la couche
# injectee (le repli de secours). La seconde est comptee a part dans `src`,
# donc la premiere est bien hors de la couche — sans ce conjoint, une couche
# qui porterait les deux passerait.
check("P11_les_trois_replis_sont_passes_par_le_bundle",
      s.count(nl("{image:4,audio:8,video:6}")) == 2
      and src.count("{image:4,audio:8,video:6}") == 1,
      f'bundle={s.count(nl("{image:4,audio:8,video:6}"))} '
      f'couche={src.count("{image:4,audio:8,video:6}")}')
# DEUX FACES pour chaque identifiant du bundle que la section appelle, et
# pour chaque identifiant de la couche que le bundle appelle.
for _lbl, _decl, _appel in (
        ("defaultLen", nl("function defaultLen(kind,srcDur){"),
         nl("var dzCl=defaultLen(kind,srcDur);")),
        ("addAsset", nl("function addAsset(src,label,kind,srcDur,trId,"
                        "atTime){"),
         nl("addAsset(src,label,kind,dzV>0?dzV:-1,trId,st)"))):
    check("P11_deux_faces_" + _lbl,
          s.count(_decl) == 1 and s.count(_appel) == 1,
          f"decl={s.count(_decl)} appel={s.count(_appel)}")
for _nom in ("clipLen", "needDur", "askDur"):
    check("P11_deux_faces_DzTracks_" + _nom,
          s.count(nl("DzTracks." + _nom + "(")) == 1
          and src.count(_nom + ":dzm" + _nom[0].upper() + _nom[1:]) == 1,
          f'bundle={s.count(nl("DzTracks." + _nom + "("))} '
          f'couche={src.count(_nom + ":dzm" + _nom[0].upper() + _nom[1:])}')
# LA DECOUVERTE SORT AVANT `pushHistory` : rien ne doit etre ecrit avant que
# la longueur ne soit connue, sinon un « annuler » retirerait un clip que la
# mesure allait remplacer. Mesure sur les POSITIONS dans le corps d'addAsset,
# `find` jamais `index` (faute n°6) : les trois reperes valent -1 quand ils
# manquent, et la ligne EXIGE qu'ils aient ete trouves ET ordonnes.
_aa0 = s.find(nl("function addAsset(src,label,kind,srcDur,trId,atTime){"))
_ask = s.find(nl("DzTracks.askDur(src,{done:function(dzV){"),
              _aa0 if _aa0 >= 0 else 0)
# LE `pushHistory` DE L'AJOUT, pas le premier venu : le court-circuit de
# remplacement (P6) en pose un AVANT, plus haut dans le meme corps. C'est
# `setClips(clipsRef.current.concat(` qui identifie l'ajout sans ambiguite.
_ph = s.find(nl("setClips(clipsRef.current.concat("),
             _aa0 if _aa0 >= 0 else 0)
check("P11_la_mesure_sort_avant_que_l_historique_ne_soit_pousse",
      _aa0 >= 0 and _ask > _aa0 and _ph > _ask,
      f"addAsset={_aa0} askDur={_ask} ajout={_ph}")
# ECART DECLARE, MESURE PLUTOT QUE TU : un REMPLACEMENT de source (P6) ne
# passe PAS par la decouverte — son court-circuit rend la main avant. Une
# source de remplacement sans duree connue ne recale donc toujours pas sa
# fenetre (`replaceSrc` en a besoin). C'est une tache a part, et cette ligne
# la tient VRAIE : le jour ou le court-circuit passerait apres la mesure,
# elle rougit et la reserve du commit cesse d'etre exacte.
_rep = s.find(nl("setSelId(rc.id);setDirty(!0);fireNote(rr.note);return}"),
              _aa0 if _aa0 >= 0 else 0)
check("P11_un_remplacement_de_source_ne_passe_pas_par_la_mesure",
      _aa0 >= 0 and _rep > _aa0 and _ask > _rep,
      f"addAsset={_aa0} remplacement={_rep} askDur={_ask}")
# LE VERROU DE RECURSION, DANS LE BUNDLE : le rappel repasse un nombre
# NEGATIF quand la mesure a echoue, et `needDur` le lit comme « deja
# demande » (ligne js_needdur_non_quand_elle_est_negative...).
check("P11_le_rappel_porte_le_verrou_de_recursion",
      s.count(nl("addAsset(src,label,kind,dzV>0?dzV:-1,trId,st)")) == 1,
      f'{s.count(nl("addAsset(src,label,kind,dzV>0?dzV:-1,trId,st)"))}')
# LE REPLI EST DIT A L'ECRAN : la note de `clipLen` est CONCATENEE dans celle
# que `fireNote` emet a l'ajout. Sans cette ligne, `clipLen` pourrait rendre
# une note parfaite que personne n'afficherait.
check("P11_la_note_du_clip_entre_dans_celle_de_l_ajout",
      s.count(nl("var dzTail=dzCl.note+(dzGrew?")) == 1
      and s.count(nl('+dzTail)}')) == 1,
      f'dzTail={s.count(nl("var dzTail=dzCl.note+(dzGrew?"))} '
      f'fireNote={s.count(nl("+dzTail)}"))}')
# LA ROUTE, DES DEUX COTES DU FIL : la couche l'appelle, le service la sert.
check("P11_la_route_de_duree_existe_des_deux_cotes",
      src.count('"/api/montage/duration?src="') == 1
      and SVC.count('@router.get("/duration")') == 1
      and SVC.count("async def montage_duration(") == 1,
      f'couche={src.count(chr(34) + "/api/montage/duration?src=" + chr(34))} '
      f'route={SVC.count(chr(34) + "@router.get(" + chr(34))}')
# LA ROUTE NE RECOPIE NI LA RESOLUTION NI LA MESURE : elle appelle celles qui
# existent. Une copie aurait diverge a la premiere correction — l'argument de
# P9 pour `/media-rules`, applique ici.
check("P11_la_route_reutilise_la_resolution_et_la_sonde",
      SVC.count("p = await _media_source(request, src, video=False)") == 2
      and SVC.count("dur = await asyncio.to_thread(_probe_duration, p)") == 1,
      f'media_source={SVC.count("p = await _media_source(request, src, video=False)")} '
      f'probe={SVC.count("dur = await asyncio.to_thread(_probe_duration, p)")}')

# ── LA CHAINE AVAL, MESUREE ICI PLUTOT QUE DECOUVERTE AU REJEU SUIVANT ────
# CE QUI A MORDU PENDANT P10, ET QUI A FAILLI MORDRE ICI. `patch_bundle_
# dzcout.py` est un maillon AVAL de `montage` ; sa garde `guard_downstream`
# cherche un `.bak_*` plus recent que le sien, or les `.bak_*` NE SONT PAS
# SUIVIS PAR GIT. Six commits cueillis ont apporte un bundle deja patche par
# dzcout mais SANS son backup : la garde etait AVEUGLE, et rejouer montage a
# efface les sept marqueurs `__dzCoutBlanc` en silence. Ce qui l'a rattrape
# n'est aucune assertion de montage, c'est la SONDE AMONT de dzcout.
# LES DEUX LIGNES CI-DESSOUS FONT DE CETTE SONDE UNE MESURE DU BANC : le jour
# ou une section ajoute une reference a `DzTracks` sans mettre le nombre a
# jour, c'est ICI que ca rougit, avant le rejeu.
# LE COMPTE EST EN OCCURRENCES, PAS EN LIGNES : le bundle est minifie et
# `grep -c` compterait des lignes.
_DZCOUT = ROOT / "scripts" / "patch_bundle_dzcout.py"
# CES DEUX LIGNES TUAIENT LE BANC — faute n°6, sixieme morsure, et la
# variante la plus fourbe : `_DZCOUT.is_file()` ne garde que l'ABSENCE.
# MESURE le 05/09/2026, sur scripts/patch_bundle_dzcout.py :
#   · une faute de syntaxe               -> SyntaxError a l'import
#   · un QUATRIEME champ dans une entree
#     de STABLE_PROBES                   -> ValueError: too many values
#   · une levee au premier niveau        -> l'exception telle quelle
# Dans les TROIS cas, AVANT : rc=1, une trace, 313 des 524 lignes imprimees,
# AUCUNE ligne de compte — DEUX CENT ONZE assertions emportees en silence,
# dont les sections [2], [3] et [3-bis] entieres. APRES, meme relance :
# 521/3, le temoin NUMEROTE dans le detail des deux lignes, et le compte EST
# imprime (la ligne `aucun_appel_n_a_plante` de la queue rougit en plus).
# LE DEPAQUETAGE EST DANS LE `try`, PAS SEULEMENT L'IMPORT : c'est lui qui
# leve sur un quatrieme champ, et il est aussi neuf que l'import.
_DC, _sonde, _dcErr = None, {}, ""
if not _DZCOUT.is_file():
    _dcErr = f"{_DZCOUT} introuvable"
else:
    try:
        _DC = load("patch_bundle_dzcout", _DZCOUT)
        _sonde = dict((t, n) for t, _m, n in _DC.STABLE_PROBES)
    except BaseException as _e:       # SystemExit compris
        _DC, _sonde, _dcErr = None, {}, temoin(_e)
# LE CONJOINT `_DC is not None` N'EST PAS UN ORNEMENT : `_sonde.get(...)`
# rendrait `None` sur le dict de repli, et `None == s.count(...)` serait FAUX
# — la ligne rougirait, mais en accusant la sonde au lieu de l'import. Le
# detail porte desormais le temoin, et dit LEQUEL des deux a lache.
check("chaine_la_sonde_amont_de_dzcout_compte_juste_les_DzTracks",
      _DC is not None and _sonde.get("montage") == s.count("DzTracks"),
      f'{_dcErr or ""} sonde={_sonde.get("montage")} '
      f'bundle={s.count("DzTracks")}')
check("chaine_les_sept_marqueurs_de_dzcout_sont_toujours_la",
      _DC is not None and s.count(_DC.MARKER) == _DC.MARKER_ATTENDU == 7,
      f'{_dcErr or ""} '
      f'bundle={s.count(_DC.MARKER) if _DC is not None else "?"} '
      f'attendu={getattr(_DC, "MARKER_ATTENDU", "?")}')

# ── DETTE D'ECRAN, CONSIGNEE ET NON DEVINEE (etape 5 de la tache) ─────────
# LE ZOOM N'EST PAS REECRIT. Le defilement horizontal EXISTE DEJA et il est
# bon : `.svm-scroll{flex:1; overflow:auto}`, pistes en `width:zoomPct%`,
# quatre paliers, Ctrl+molette continu avec conservation du point sous le
# curseur. Ce qui manque est qu'on le TROUVE, et cela ne se mesure qu'a
# l'ecran — aucune de ces lignes ne pretend l'avoir mesure. Elles epinglent
# le mecanisme pour que la dette reste VRAIE : le jour ou l'infobulle ou les
# paliers changent, la note de dette du commit cesse d'etre exacte et cette
# ligne rougit.
_SVMCSS = (ROOT / "frontend" / "dist" / "shared" / "son-vfx-montage.css")
_SVMCSS = _SVMCSS.read_text(encoding="utf-8") if _SVMCSS.is_file() else ""
check("dette_ecran_le_defilement_du_zoom_existe_et_n_a_pas_bouge",
      bool(_SVMCSS) and ".svm-scroll{flex:1; overflow:auto" in _SVMCSS
      and s.count(nl("SVM_ZOOMW=[100,150,220,320]")) == 1
      and s.count("Ctrl+molette : zoom continu centré sur le curseur") == 1,
      "le mécanisme de zoom a bougé — la dette consignée n'est plus exacte")
# LA SEULE BORNE HAUTE MESUREE : la regle cesse de graduer a 40 traits (pas
# maximal 60 s, donc 40 min). Elle ne casse rien et ne justifie pas un refus
# dans `dzmDurCtl` — elle est CONSIGNEE, pas contournee en silence.
check("dette_ecran_la_regle_cesse_de_graduer_a_40_traits",
      s.count(nl("&&ticks.length<40;")) == 1,
      f"count={s.count(nl('&&ticks.length<40;'))}")

print("\n[1-ter] feuille de style et index.html")
check("css_liee_index_html", "shared/montage.css" in
      HTML.read_bytes().decode("utf-8-sig"))
check("css_porte_la_chip_mot",
      ".dzm-wabtn[data-on]" in CSS.read_text(encoding="utf-8"),
      "montage.css n'habille pas l'état retenu de la chip")
# subs.css fige .svm-tl à 356px : sans reprise, une septième piste resterait
# sous la ligne de flottaison. C'est le seul point où montage.css DOIT gagner.
check("css_reprend_la_hauteur_de_timeline",
      ".svm-tl{height:auto" in CSS.read_text(encoding="utf-8").replace(" ", "")
      .replace("\n", ""), "montage.css ne reprend pas .svm-tl")

print("\n[2] node --check sur le bundle entier — sémantique SCRIPT puis MODULE")
r = NODE(["node", "--check", str(BUNDLE)])
check("node_check", r.returncode == 0, (r.stderr or "")[-300:])
# `node --check <fichier.js>` lit le bundle en semantique SCRIPT : deux
# declarations du meme nom au premier niveau y sont LEGALES. index.html le
# charge en <script type="module">, ou elles sont une SyntaxError. C'est
# EXACTEMENT le conflit `function DzMontage` / `var DzMontage` qui a impose
# le renommage en DzTracks : MESURE le 04/09/2026, le check SCRIPT reste
# rc=0 sur un bundle ou l'on remet DzMontage, seul le check MODULE sort
# rc=1 « Identifier 'DzMontage' has already been declared ». Sans cette
# ligne, cette classe d'erreur n'apparait qu'au chargement du navigateur.
# Par stdin : pas de copie .mjs de 1,4 Mo a ecrire puis a nettoyer.
with BUNDLE.open("rb") as _fh:
    r = NODE(["node", "--input-type=module", "--check"], stdin=_fh)
check("node_check_module", r.returncode == 0, (r.stderr or "")[-300:])

print("\n[3] le cœur de la couche, EXÉCUTÉ sous node")
shim = pathlib.Path(TMP) / "shim.js"
# La table SVM_TRACKS du bundle est EXTRAITE et exécutée à côté de la couche.
# DZM_DEFAULT_TRACKS la recopie (nom, type, hauteur, couleur, rang de mixage)
# en y ajoutant kind/bus/loop : sans cette comparaison, les deux tables
# pourraient diverger et l'écran des six pistes historiques changerait
# d'aspect sans que rien ne le dise.
# MEME FAMILLE QUE LA LIGNE 614 (faute n°6), et pire : ces deux `index` NUS
# n'étaient sous AUCUN `check`. Le jour où le minifieur renomme `SVM_TRACKS`
# ou change la ponctuation de fin de table, le banc mourait ICI — avant la
# section [3] tout entière et avant sa ligne de compte. `find` rend -1, le
# repli « table vide » existait déjà, et l'échec est désormais DIT avec les
# deux indices.
_i = s.find(nl("var SVM_TRACKS=["))
_k = s.find(nl("}];"), _i) if _i >= 0 else -1
_j = _k + len(nl("}];")) if _k >= 0 else -1
SVM_SRC = s[_i:_j] if _i >= 0 and _j > _i else ""
_n_entrees = SVM_SRC.count("{id:")
if _n_entrees != 6:
    check("bundle_svm_tracks_extraite", False,
          f"début={_i} fin={_j} entrées={_n_entrees} (attendu 6)")
    SVM_SRC = "var SVM_TRACKS=[];"
else:
    check("bundle_svm_tracks_extraite", True)
probe = """
var out={};
var T=window.DzTracks;
out.skin_len=(SVM_TRACKS.length===T.DEFAULTS.length);
out.skin_diff=SVM_TRACKS.map(function(t,i){
  var d=T.DEFAULTS[i]||{},bad=[];
  ["id","name","type","h","c","mix"].forEach(function(k){
    if(t[k]!==d[k])bad.push(k+" "+JSON.stringify(t[k])+" ≠ "+JSON.stringify(d[k]))});
  return bad.join(", ")}).filter(function(z){return z});
out.move_a3_up=T.move(T.tracksOf(null),"a3",-1).map(function(t){return t.id});
out.move_v1_up=T.move(T.tracksOf(null),"v1",-1).map(function(t){return t.id});
out.base=T.tracksOf(null).map(function(t){return t.id});
out.add_video=T.add(T.tracksOf(null),"video").map(function(t){return t.id});
out.add_audio=T.add(T.tracksOf(null),"audio").map(function(t){return t.id});
out.rm_v1=T.remove(T.tracksOf(null),"v1").map(function(t){return t.id});
/* s1 est l'AUTRE piste de base : rien ne sait la recreer (dzmAdd ne
   fabrique que des v… et des a…) et les sous-titres SONT ses clips */
out.rm_s1=T.remove(T.tracksOf(null),"s1").map(function(t){return t.id});
out.rm_a2=T.remove(T.tracksOf(null),"a2").map(function(t){return t.id});
/* v2 ne peut pas descendre sous v1 : groupes différents */
out.move_v2_down=T.move(T.tracksOf(null),"v2",1).map(function(t){return t.id});
/* glisser v2 tout en bas : la frontière de groupe arrête le déplacement */
out.drag_v2_to_s1=T.moveTo(T.tracksOf(null),"v2","s1",!0).map(function(t){return t.id});
/* et un glisser qui REUSSIT : A1 lachee sous A3, dans son groupe */
out.moveto_a1_apres_a3=T.moveTo(T.tracksOf(null),"a1","a3",!0).map(function(t){return t.id});
/* SVM_TRACK_BUS muté EN PLACE : c'est CE mécanisme qui évite neuf ancres */
var ref=SVM_TRACK_BUS;
T.busSync(T.tracksOf(null));
out.bus_defaut=JSON.parse(JSON.stringify(SVM_TRACK_BUS));
T.busSync([{id:"v1",kind:"video"},{id:"a7",kind:"audio",bus:"musique",loop:!0}]);
out.bus_perso=JSON.parse(JSON.stringify(SVM_TRACK_BUS));
out.bus_meme_objet=(ref===SVM_TRACK_BUS);
/* payload envoyé au backend, et retour de sauvegarde */
out.payload=T.payload(null);
var rt=T.from([{id:"v3",kind:"video"},{id:"v1",kind:"video"},
                {id:"a1",kind:"audio",bus:"dialogue"}]);
out.from_ids=rt.map(function(t){return t.id});
out.from_v3_habillee=(rt[0].h>0&&!!rt[0].name&&!!rt[0].type);
out.from_sans_v1=T.from([{id:"v3",kind:"video"}]);
out.from_vide=T.from(null);
/* deux fois le meme id : la seconde entree est ignoree, pas empilee —
   deux pistes de meme identifiant se disputeraient les memes clips */
var dbl=T.from([{id:"v1",kind:"video"},{id:"v1",kind:"video"},{id:"a1",kind:"audio"}]);
out.from_doublons=dbl?dbl.map(function(t){return t.id}):null;
/* P2 — les suggestions d'emoji en clips d'overlay. La piste visée est la
   PREMIÈRE piste vidéo qui n'est pas V1, donc la plus haute : sur les six
   pistes historiques c'est v2, et si l'on ajoute v3 au-dessus c'est v3. */
var HINT=[{t:1.2,word:"feu",emoji:"F",file:"1f525",png:"C:/x/1f525.png"}];
out.emoji_defaut=T.emojiClips(HINT,T.tracksOf(null),7);
out.emoji_v3=T.emojiClips(HINT,T.add(T.tracksOf(null),"video"),7)
  .map(function(c){return c.tr});
/* pas une seule piste d'overlay : rien n'est posé plutôt qu'un clip perdu */
out.emoji_sans_overlay=T.emojiClips(HINT,[{id:"v1",kind:"video"},
  {id:"s1",kind:"subs"}],7);
/* une suggestion sans PNG n'est pas un clip : _resolve_src rendrait None et
   le rendu la jetterait en silence */
out.emoji_sans_png=T.emojiClips([{t:1,word:"feu"}],T.tracksOf(null),7);
out.word_anims=(T.WORD_ANIMS||[]).map(function(o){return o.v});
/* P4 — l'etalonnage recopie sur tous les plans de la piste du plan
   selectionne. CŒUR PUR, joue ici. */
function GCL(){return [
  {tr:"v1",id:"a",start:0,end:2,src:{job_id:1},effects:[
    {type:"grade",preset:"teal_orange"},
    /* LES SIX cles de temps, pas les deux premieres : `VfxBounds` de
       vfxrack.js est rendu pour CHAQUE effet ouvert de la pile — mesure, le
       panneau n'est conditionne par rien — et il pose fade_in, fade_out,
       ease_in, ease_out au meme titre que t0/t1, sur grade_basic comme sur
       les autres. Avec seulement t0/t1 ici, reduire DZM_GRADE_TIMING a
       ["t0","t1"] laissait le banc a 139/0 : quatre des six cles n'etaient
       exercees par rien. */
    {type:"grade_basic",exposure:20,temperature:3200,t0:0.5,t1:1.5,
     fade_in:0.2,fade_out:0.3,ease_in:"smooth",ease_out:"linear"}]},
  {tr:"v1",id:"b",start:2,end:4,src:{job_id:2}},
  {tr:"v1",id:"c",start:4,end:6,src:{job_id:3},effects:[
    {type:"grade_basic",exposure:-40},{type:"vignette",intensity:50}]},
  {tr:"v1",id:"d",start:6,end:8},                       /* demo : pas de src */
  {tr:"v2",id:"e",start:0,end:2,src:{job_id:4}},        /* autre piste */
  {tr:"v1",id:"f",start:8,end:10,src:{job_id:5},effects:[
    {type:"grade_basic",exposure:20,temperature:3200}]}] /* deja identique */}
/* IN est l'entree GARDEE : `GCL()` reconstruit un tableau NEUF a chaque
   appel, donc `G.clips[5]===GCL()[5]` etait TOUJOURS faux et seule la
   comparaison JSON decidait. Mesure : remplacer un `return c` par
   `return Object.assign({},c)` dans dzmGradeAll laissait le banc vert. */
var IN=GCL();
var G=T.gradeAll(IN,"a","v1");
out.g_compte=[G.targets,G.applied,G.replaced];
/* INSTANTANES, pas des references : la sonde MUTE `G.clips[1]` plus bas pour
   verifier l'independance des copies, et un JSON.stringify final aurait lu la
   valeur d'APRES. Mesure : g_b remontait `exposure:99` et faisait rougir une
   assertion qui n'avait rien a voir. */
out.g_b=JSON.parse(JSON.stringify(G.clips[1].effects));
/* les cles de temps SURVIVANTES dans la copie, nommees une par une : `g_b`
   rougit pour n'importe quel ecart, celle-ci dit LAQUELLE a fui. */
out.g_b_rampe=Object.keys(G.clips[1].effects[0]).filter(function(k){
  return ["t0","t1","fade_in","fade_out","ease_in","ease_out"].indexOf(k)>=0});
out.g_c=JSON.parse(JSON.stringify(G.clips[2].effects));
out.g_d=G.clips[3].effects===void 0;
out.g_e=G.clips[4].effects===void 0;
out.g_f_intacte=(G.clips[5]===IN[5]);
out.g_source_intacte=(G.clips[0]===IN[0]);
/* [b] chaque plan a SA copie : toucher l'une ne doit pas toucher l'autre */
G.clips[1].effects[0].exposure=99;
out.g_copies_independantes=G.clips[2].effects[0].exposure;
/* rien a propager : le plan source ne porte pas d'etalonnage */
var G2=T.gradeAll(GCL(),"b","v1");
out.g_sans_source=[G2.targets,G2.applied,G2.replaced];
out.g_sans_source_intact=(G2.clips===null||G2.clips.length===6);
/* entrees molles : clips nul, identifiant inconnu */
out.g_nul=T.gradeAll(null,"a","v1").applied;
out.g_inconnu=T.gradeAll(GCL(),"zzz","v1").applied;
out.gradeOf_absent=T.gradeOf({effects:[{type:"vignette"}]});
/* ── B1 : la piste visee est CELLE DU PLAN SELECTIONNE ──────────────────────
   Mesure de la version d'avant, « v1 » EN DUR : plan V2 etalonne selectionne,
   le bouton s'affichait ACTIF, ecrasait les DEUX plans V1 ([2, 2, 2]) et ne
   touchait aucun clip V2. Ces trois lignes referment ce trou : la mutation
   qui vise `"v2"` laissait le banc a 128/0. */
function GV(){return [
  {tr:"v1",id:"a",start:0,end:2,src:{job_id:1},effects:[
    {type:"grade_basic",exposure:20}]},
  {tr:"v1",id:"b",start:2,end:4,src:{job_id:2},effects:[
    {type:"grade_basic",exposure:-40}]},
  {tr:"v2",id:"e",start:0,end:2,src:{job_id:4},effects:[
    {type:"grade_basic",exposure:70,temperature:3200}]},
  {tr:"v2",id:"g",start:2,end:4,src:{job_id:5}}]}
var IV=GV();
var GB=T.gradeAll(IV,"e","v2");
out.gv_compte=[GB.targets,GB.applied,GB.replaced];
out.gv_v1_intact=(GB.clips[0]===IV[0]&&GB.clips[1]===IV[1]);
out.gv_v2_ecrit=JSON.parse(JSON.stringify(GB.clips[3].effects||null));
/* ── le CORPS du bouton, EXECUTE (stub `r` du shim) ─────────────────────────
   C'est lui qui choisit la piste, et c'est lui qui mentait. Six mutations de
   ce corps — dont museler la note et vider la phrase des bornes de temps —
   laissaient le banc a 128/0 : rien ne l'appelait. */
function BTN(sel,cs){return T.gradeAllBtn(sel,cs,null,null,null,null)}
var BV=BTN(IV[2],GV());
out.bv_libelle=BV&&BV.p.children;
out.bv_titre=BV&&BV.p.title;
out.bv_actif=!!BV&&!BV.p.disabled;
var B1=BTN(GCL()[0],GCL());
out.b_libelle=B1&&B1.p.children;
out.b_titre=B1&&B1.p.title;
out.b_aria=B1&&B1.p["aria-label"];
out.b_actif=!!B1&&!B1.p.disabled;
/* pas d'etalonnage sur le plan selectionne : NULL, pas un bouton mort */
out.b_sans_etalonnage=BTN(GCL()[1],GCL());
/* UNE seule autre cible, deja identique : « Le seul autre plan V1 » — et pas
   « Les 1 autre plan V1 porte deja… », qui etait la phrase livree */
var UN=[{tr:"v1",id:"a",start:0,end:2,src:{job_id:1},effects:[
           {type:"grade_basic",exposure:20}]},
        {tr:"v1",id:"b",start:2,end:4,src:{job_id:2},effects:[
           {type:"grade_basic",exposure:20}]}];
var BU=BTN(UN[0],UN);
out.b_un_titre=BU&&BU.p.title;
out.b_un_aria=BU&&BU.p["aria-label"];
out.b_un_mort=!!BU&&!!BU.p.disabled;
/* aucune autre cible du tout */
var SEUL=[{tr:"v1",id:"a",start:0,end:2,src:{job_id:1},effects:[
             {type:"grade_basic",exposure:20}]}];
var BS=BTN(SEUL[0],SEUL);
out.b_seul_titre=BS&&BS.p.title;
out.b_seul_mort=!!BS&&!!BS.p.disabled;
/* le GESTE : pushHistory AVANT setClips, une seule fois, drapeau allume,
   note emise — l'ordre est celui du journal */
var jr=[],ecrit=null,msg=null;
var BG=T.gradeAllBtn(GCL()[0],GCL(),
  function(c){jr.push("setClips");ecrit=c},
  function(){jr.push("pushHistory")},
  function(v){jr.push("setDirty="+v)},
  function(m){jr.push("note");msg=m});
BG.p.onClick();
out.b_journal=jr;
out.b_note=msg;
out.b_ecrit=ecrit?ecrit.length:0;
/* LE MEME GESTE, HORS V1 : la note n'existe qu'une fois le bouton CLIQUE, et
   rien ne le cliquait sur V2. Mesure : retirer `+hors` de la NOTE (en laissant
   celui du titre) laissait le banc a 139/0 — l'avertissement du rendu n'etait
   garde que dans le titre, alors que P4 revendiquait « le titre ET la note ». */
var msgv=null;
T.gradeAllBtn(GV()[2],GV(),function(c){},function(){},function(v){},
  function(m){msgv=m}).p.onClick();
out.bv_note=msgv;
/* cas de bord [d] : DEUX grade_basic sur une cible — seul le PREMIER est
   remplace, le second survit. Assume, donc epingle. */
var DEUX=[{tr:"v1",id:"a",start:0,end:2,src:{job_id:1},effects:[
             {type:"grade_basic",exposure:20}]},
          {tr:"v1",id:"b",start:2,end:4,src:{job_id:2},effects:[
             {type:"grade_basic",exposure:-40},
             {type:"grade_basic",contrast:150}]}];
out.g_deux_grades=JSON.parse(JSON.stringify(
  T.gradeAll(DEUX,"a","v1").clips[1].effects));
/* P5 — la ligne de resume d'un projet et sa date. PURES, et SANS FUSEAU :
   `toLocaleString` aurait rendu une chaine differente selon la machine, donc
   intestable ici. C'est pourquoi la date est rendue telle qu'elle est
   stockee, avec le suffixe qui le dit. */
out.pl_plein=T.projLine({clips:3,ratio:"9:16",duration:12.25,
  updated_at:"2026-09-04T13:42:36Z"});
out.pl_un=T.projLine({clips:1,ratio:"16:9",duration:4});
out.pl_vide=T.projLine(null);
out.pl_zero=T.projLine({clips:0,duration:0,ratio:""});
out.pw_bon=T.projWhen("2026-01-02T03:04:05Z");
out.pw_casse=T.projWhen("pas une date");
out.pw_nul=T.projWhen(null);
/* ── P9 : la piste RESOLUE, le filtre du selecteur, les deux commandes ──── */
/* CAP = les pistes MESUREES dans la sauvegarde reelle du 04/09/2026 : il n'y
   a PAS de v2, et c'est tout le defaut. `trId||"v2"` posait le clip la. */
var CAP=[{id:"v1",kind:"video"},{id:"a2",kind:"audio"},{id:"a1",kind:"audio"},
         {id:"a3",kind:"audio"},{id:"s1",kind:"subs"}];
out.pick_v=T.pickTrack(CAP,"video");
out.pick_a=T.pickTrack(CAP,"audio");
out.pick_s=T.pickTrack(CAP,"subs");
/* SANS `kind` : le genre se deduit de l'identifiant (une liste restauree
   d'une vieille sauvegarde n'a que des `id`), et la premiere piste VIDEO
   n'est pas la premiere piste tout court. */
out.pick_1re=T.pickTrack([{id:"a1"},{id:"v3"},{id:"v1"}],"video");
out.pick_aucune=T.pickTrack([{id:"a1",kind:"audio"},{id:"s1",kind:"subs"}],"video");
out.pick_vide=T.pickTrack([],"video");
out.pick_nul=T.pickTrack(null,"video");
/* EXTS est la liste que le BACKEND sert (_VIDEO_EXTS), EXTRAITE de
   montage_service.py juste avant l'ecriture du shim — elle n'est ecrite NULLE
   PART dans la couche, c'est ce que `M16c_la_couche_ne_recopie_aucune_
   extension` verifie, et elle n'est plus RECOPIEE ici non plus.
   POURQUOI (revue de qualite du 04/09/2026) : des trois maillons de la regle,
   la route suivait (`list(_VIDEO_EXTS)`) et le filtre client suivait (aucune
   extension en JS) — seul le banc portait une copie figee. Retirer `.mp4` de
   `_VIDEO_EXTS` laissait donc 255 lignes VERTES sur une application qui ne
   sait plus poser un mp4. Avec l'injection, cette mutation fait rougir
   `job_video_acceptee` et `job_extension_insensible_a_la_casse`, et elles
   seules. */
var EXTS=__DZ_VIDEO_EXTS__;
out.jv_mp4=T.isVideoJob({status:"done",final_video_path:"C:/x/a.mp4"},EXTS);
/* LES DEUX CAS DE P8, ceux que le selecteur proposait encore */
out.jv_planche=T.isVideoJob({status:"done",video_path:"C:/x/sprites.png"},EXTS);
out.jv_maillage=T.isVideoJob({status:"done",final_video_path:"C:/x/m.glb"},EXTS);
out.jv_encours=T.isVideoJob({status:"running",final_video_path:"C:/x/a.mp4"},EXTS);
/* `final_video_path` PRIME : c'est l'ordre de `_resolve_src` cote serveur
   (`jr.final_video_path or jr.video_path`). L'ancien critere prenait le
   PREMIER des deux qui existe — sur ce job-la, les deux divergent. */
out.jv_final_prime=T.isVideoJob({status:"done",video_path:"C:/x/a.mp4",
  final_video_path:"C:/x/b.png"},EXTS);
out.jv_majuscules=T.isVideoJob({status:"done",final_video_path:"C:/x/A.MP4"},EXTS);
out.jv_preview=T.isVideoJob({status:"done",provider:"montage",
  image_filename:"z_preview.png",final_video_path:"C:/x/a.mp4"},EXTS);
out.jv_sans_chemin=T.isVideoJob({status:"done"},EXTS);
/* regle INJOIGNABLE : on ne filtre pas, et le selecteur le DIT a l'ecran.
   Une liste vide en dur aurait affiche « aucun rendu video termine » sur une
   Bibliotheque pleine. */
out.jv_sans_regle=T.isVideoJob({status:"done",video_path:"C:/x/sprites.png"},null);
/* un nom qui CONTIENT une extension video sans en porter une : `endsWith`
   naif aurait dit oui sur « a.mp4.zip » — le suffixe est extrait, comme
   `Path(...).suffix` cote serveur. */
out.jv_faux_ami=T.isVideoJob({status:"done",final_video_path:"C:/x/a.mp4.zip"},EXTS);
out.jv_nul=T.isVideoJob(null,EXTS);
/* ── le bouton « Bibliotheque… » ─────────────────────────────────────────── */
var lpick=null;
var lb=T.LibBtn({tracks:CAP,onPick:function(id){lpick=id},note:function(m){}});
lb.p.onClick();
out.lib_pick=lpick;
out.lib_label=lb.p.children;
out.lib_titre_nomme_la_piste=lb.p.title.indexOf("V1")>=0;
/* AUCUNE piste video : le bouton ne s'eteint pas — il DIT pourquoi et nomme
   la sortie. Un bouton grise sans explication oblige a deviner, et c'est le
   defaut que toute cette tache repare. */
var lm=null,lp2=null;
T.LibBtn({tracks:[{id:"a1",kind:"audio"}],onPick:function(id){lp2=id},
  note:function(m){lm=m}}).p.onClick();
out.lib_sans_piste_note=lm;
out.lib_sans_piste_n_ouvre_rien=(lp2===null);
/* ── la chip « pas une video » ───────────────────────────────────────────── */
var bfix=null,bstop=0;
function EV(){return {stopPropagation:function(){bstop++}}}
var bc=T.badSrc({id:"c3",tr:"v1"},function(c){bfix=c.id});
out.bad_label=bc.p.children;
bc.p.onPointerDown(EV());
bc.p.onClick(EV());
out.bad_fix=bfix;
/* DEUX arrets : sans celui du pointerdown, le clic amorcerait le
   deplacement du clip qui est SOUS la chip. */
out.bad_arrete_les_deux=bstop;
out.bad_titre_echec=bc.p.title.indexOf("fera échouer le rendu")>=0;
out.bad_titre_carton=bc.p.title.indexOf("carton fixe")>=0;
/* ══ P10 — LA DUREE QUE LE PROJET DOIT AVOIR, ET SON REGLAGE ══════════════
   `fitDur` est PURE : elle se joue ici en entier, y compris ses entrees
   molles. `LEVE:` au lieu d'une exception : un `clips` nul qui ferait lever
   la fonction emporterait TOUTE la section [3] — rougir, pas mourir. */
function FD(a,b,c){try{return T.fitDur(a,b,c)}catch(e){return "LEVE:"+e.name}}
out.dur_min=T.DUR_MIN;
out.fd_vide=FD([],16,0);
out.fd_nul=FD(null,16,0);
out.fd_indefini=FD(void 0,16,0);
out.fd_rentre=FD([{end:6}],16,0);
out.fd_depasse=FD([{end:20}],16,0);
out.fd_depasse_fractionnaire=FD([{end:20.2}],16,0);
out.fd_prend_le_max_pas_le_dernier=FD([{end:20},{end:4},{end:12}],16,0);
out.fd_marge=FD([{end:20}],16,2);
out.fd_marge_negative=FD([{end:20}],16,-5);
out.fd_marge_illisible=FD([{end:20}],16,"x");
/* pas de clip = pas de queue a laisser : une timeline vide ne s'allonge pas
   toute seule sous pretexte qu'on a demande une marge. */
out.fd_marge_sans_clip=FD([],1,3);
out.fd_end_illisible=FD([{end:"abc"},{end:6}],16,0);
out.fd_end_infini=FD([{end:Infinity}],16,0);
out.fd_end_absent=FD([{}],16,0);
out.fd_clip_nul=FD([null,{end:6}],16,0);
out.fd_dur_nulle=FD(null,0,0);
out.fd_dur_negative=FD(null,-9,0);
out.fd_dur_illisible=FD(null,"abc",0);
out.fd_dur_infinie=FD([{end:5}],Infinity,0);
out.fd_dur_fractionnaire_gardee=FD([{end:5}],16.5,0);
out.fd_ne_raccourcit_jamais=FD([{end:3}],30,0);
/* LE CAS DE L'UTILISATEUR, joue tel quel : projet de 16 s, tete de lecture a
   14 s, video de 6 s posee la — donc un clip qui finit a 20 s. */
out.fd_cas_utilisateur=FD([{end:20}],16,0);
/* ── le reglage explicite, dans la barre de transport ──────────────────── */
function DKID(el,k){var c=(el&&el.p&&el.p.children)||[],i;
  for(i=0;i<c.length;i++)if(c[i]&&c[i].k===k)return c[i];return null}
function DCTL(dur,step,clips){
  var got=[],msgs=[];
  var el=T.durCtl({dur:dur,step:step,clips:clips,
    onSet:function(v){got.push(v)},note:function(m){msgs.push(m)}});
  return {el:el,got:got,msgs:msgs}}
function DCLIC(o,k){var b=DKID(o.el,k);if(!b)return !1;b.p.onClick();return !0}
var CL20=[{end:20}];
var dA=DCTL(30,2,CL20);
out.dc_classe=dA.el.p.className;
out.dc_valeur=(DKID(dA.el,"v")||{p:{}}).p.children;
out.dc_kids=(dA.el.p.children||[]).map(function(z){return z&&z.k});
out.dc_plus_ok=DCLIC(dA,"p");
out.dc_plus_valeur=dA.got[0];
out.dc_plus_note=dA.msgs[0];
var dA2=DCTL(30,2,CL20);
out.dc_moins_ok=DCLIC(dA2,"m");
out.dc_moins_valeur=dA2.got[0];
var dA3=DCTL(30,2,CL20);
out.dc_ajuste_ok=DCLIC(dA3,"f");
out.dc_ajuste_valeur=dA3.got[0];
out.dc_ajuste_note=dA3.msgs[0];
/* B — le pas TOMBERAIT sous la fin du dernier clip : il s'ARRETE dessus et
   le dit. Ce n'est pas un refus, et la difference se voit dans la note. */
var dB=DCTL(21,2,CL20);
out.dc_arret_ok=DCLIC(dB,"m");
out.dc_arret_valeur=dB.got[0];
out.dc_arret_note=dB.msgs[0];
/* C — DEJA sur la fin du dernier clip : REFUS. Rien n'est ecrit, et la note
   dit ce qui se serait passe. « ajuster » a disparu : rien a retirer. */
var dC=DCTL(20,2,CL20);
out.dc_refus_kids=(dC.el.p.children||[]).map(function(z){return z&&z.k});
out.dc_refus_clic=DCLIC(dC,"m");
out.dc_refus_ecritures=dC.got.length;
out.dc_refus_notes=dC.msgs.length;
out.dc_refus_note=dC.msgs[0];
/* D — timeline vide : « ajuster » ramene au PLANCHER de 1 s, celui de
   svmApplyProject, et « − » y est refuse. */
var dD=DCTL(16,2,[]);
out.dc_vide_ajuste=DCLIC(dD,"f");
out.dc_vide_valeur=dD.got[0];
var dE=DCTL(1,2,[]);
out.dc_plancher_clic=DCLIC(dE,"m");
out.dc_plancher_ecritures=dE.got.length;
/* E — entrees illisibles : la duree retombe sur le plancher, le pas sur 1 s */
var dF=DCTL("abc",0,null);
out.dc_mou_valeur=(DKID(dF.el,"v")||{p:{}}).p.children;
out.dc_mou_plus=DCLIC(dF,"p")&&dF.got[0];
/* LA RESERVE CENTRALE est dans CHACUNE des notes emises par le controle —
   `dc_notes_comptees` empeche ce `every` d'etre vrai sur du vide. */
out.dc_toutes_les_notes_disent_la_reserve=[dA.msgs,dA3.msgs,dB.msgs]
  .reduce(function(a,b){return a.concat(b)},[])
  .every(function(m){return m.indexOf("« Annuler » ne rend pas la durée")>=0});
out.dc_notes_comptees=dA.msgs.length+dA3.msgs.length+dB.msgs.length;
/* un « − » nu ne dit pas de combien : les trois elements nomment le pas */
out.dc_titres_nomment_le_pas=["m","v","p"].every(function(k){
  var b=DKID(dA.el,k);return !!b&&b.p.title.indexOf("2 s")>=0});
out.dc_aria=["m","p"].map(function(k){return DKID(dA.el,k).p["aria-label"]});
out.secs=[T.secs(2),T.secs(.5),T.secs(10),T.secs("x")];
/* ══ P11 — LA LONGUEUR D'UN CLIP, ET LA DECOUVERTE DE CELLE DE SA SOURCE ══
   `clipLen` et `needDur` sont PURES : elles se jouent ici en entier. `askDur`
   ne l'est pas, mais ses deux dependances impures sont INJECTEES — un
   `fetch` factice SYNCHRONE et un `timer` qu'on declenche a la main — donc
   tout son chemin reseau se joue ici aussi, au lieu de rester une dette de
   navigateur. `LEVE:` plutot qu'une exception : rougir, pas mourir. */
function CL(k,v,d){try{var o=T.clipLen(k,v,d);
    return {len:o.len,origine:o.origine,note:o.note}}
  catch(e){return {len:"LEVE:"+e.name,origine:"LEVE",note:"LEVE"}}}
function ND(k,v){try{return T.needDur(k,v)}catch(e){return "LEVE:"+e.name}}
/* LES TROIS REPLIS TELS QUE LE BUNDLE LES PASSE — pas une invention du banc :
   la ligne `P11_defaultLen_delegue_a_la_couche` les compte dans le bundle
   LIVRE, et c'est ce meme triplet qui est joue ici. */
var BD={image:4,audio:8,video:6};
out.cl_defauts_de_secours=T.CLIP_DEFAUTS;
out.cl_video_16=CL("video",15.973,BD);
out.cl_video_21=CL("video",21.233,BD);
/* PLUS COURTE QUE L'ANCIEN PLAFOND : le repli n'est pas devenu un plancher. */
out.cl_video_courte=CL("video",3.5,BD);
out.cl_video_minuscule=CL("video",0.2,BD);
out.cl_video_zero=CL("video",0,BD);
out.cl_video_negatif=CL("video",-5,BD);
out.cl_video_nan=CL("video",NaN,BD);
out.cl_video_texte=CL("video","abc",BD);
out.cl_video_absent=CL("video",void 0,BD);
out.cl_video_infini=CL("video",Infinity,BD);
out.cl_audio_source=CL("audio",184.2,BD);
out.cl_audio_inconnu=CL("audio",0,BD);
out.cl_image=CL("image",0,BD);
/* UNE IMAGE N'A PAS DE LONGUEUR : la duree passee est ignoree, comme avant. */
out.cl_image_avec_duree=CL("image",30,BD);
/* LES REPLIS SONT CEUX DE L'APPELANT : la couche n'est pas leur autorite. */
out.cl_defauts_recus=CL("video",0,{image:1,audio:2,video:10});
out.cl_defauts_illisibles=CL("video",0,{video:"x"});
out.cl_defauts_negatifs=CL("audio",0,{audio:-3});
out.cl_defauts_absents=CL("video",0);
out.cl_defauts_nuls=CL("video",0,null);
out.cl_arrondi_au_millieme=CL("video",15.9731234,BD).len;
/* UN GENRE INCONNU EST TRAITE COMME UNE VIDEO — c'est ce que faisait la
   fonction du bundle (son dernier `return` etait le cas par defaut). */
out.cl_genre_inconnu=CL("sous-titre",0,BD);
/* ── faut-il aller demander ? ─────────────────────────────────────────────── */
out.nd_image=ND("image",0);
out.nd_image_avec_duree=ND("image",30);
out.nd_video_connue=ND("video",15.973);
out.nd_video_zero=ND("video",0);
out.nd_video_absente=ND("video",void 0);
out.nd_video_texte=ND("video","abc");
out.nd_video_infinie=ND("video",Infinity);
/* LE VERROU DE RECURSION : un nombre NEGATIF veut dire « deja demande ». */
out.nd_video_negative=ND("video",-1);
out.nd_audio_zero=ND("audio",0);
/* ── la mesure, avec un `fetch` factice SYNCHRONE ────────────────────────── */
/* Une promesse native resoudrait en micro-tache, DONC apres le
   `console.log` final : le banc lirait des `undefined` partout et serait
   vert sans avoir rien mesure. Ce thenable-ci resout SUR PLACE. */
/* Il DEBOBINE ce que le rappel rend, comme une vraie promesse : sans cela,
   le second `.then` recevait le thenable de `json()` au lieu du corps, et la
   ligne du corps illisible verdissait sur « mesure ». */
function SYNC(v){return {
  then:function(cb){var r;try{r=cb(v)}catch(e){return SYNCERR(e)}
    return (r&&typeof r.then==="function")?r:SYNC(r)},
  catch:function(){return SYNC(v)}}}
function SYNCERR(e){return {
  then:function(){return SYNCERR(e)},
  catch:function(cb){cb(e);return SYNC(void 0)}}}
var adURL=null,adAppels=0;
function FETCH(rep){return function(u){adURL=u;adAppels++;return SYNC(rep)}}
function REP(ok,corps){return {ok:ok,json:function(){return SYNC(corps)}}}
function JAMAIS(){}                    /* un timer qui ne se declenche pas */
function TOUT_DE_SUITE(fn){fn()}       /* ... et un qui gagne la course */
function AD(o){
  var vus=[];
  o.done=function(v,pq){vus.push([v,pq])};
  try{T.askDur({job_id:"j1"},o)}catch(e){vus.push(["LEVE:"+e.name,"LEVE"])}
  return {n:vus.length,premier:vus[0]||null}}
out.ad_delai_par_defaut=T.DUR_DELAI;
adURL=null;adAppels=0;
var a1=AD({fetch:FETCH(REP(!0,{ok:!0,dur:21.233,name:"sentry_bot.mp4"})),
           timer:JAMAIS});
out.ad_mesure=a1.premier;
out.ad_une_seule_reponse=a1.n;
out.ad_url=adURL;
/* `dur: 0` = INCONNUE, jamais « nulle » : la sortie est nommee « mesure »
   (le serveur a bien repondu) mais la duree ne vaut rien d'exploitable. */
out.ad_mesure_inconnue=AD({fetch:FETCH(REP(!0,{ok:!0,dur:0})),
                           timer:JAMAIS}).premier;
out.ad_http_refuse=AD({fetch:FETCH(REP(!1,null)),timer:JAMAIS}).premier;
out.ad_json_illisible=AD({fetch:FETCH(REP(!0,null)),timer:JAMAIS}).premier;
out.ad_reseau_leve=AD({fetch:function(){throw new Error("boom")},
                       timer:JAMAIS}).premier;
out.ad_promesse_rejetee=AD({fetch:function(){return SYNCERR(new Error("ko"))},
                            timer:JAMAIS}).premier;
out.ad_sans_reseau=AD({fetch:null,timer:JAMAIS}).premier;
/* SANS FETCH, AUCUN APPEL — et le compteur le prouve : sans lui, `fetch:null`
   pourrait rendre « sans-reseau » APRES avoir appele autre chose. */
adAppels=0;AD({fetch:null,timer:JAMAIS});
out.ad_sans_reseau_zero_appel=adAppels;
/* LA COURSE. Le delai gagne, la reponse arrive quand meme : UNE seule
   sortie, celle du delai. Le compteur d'appels prouve que la reponse EST
   passee — sans lui, un `askDur` qui ne demanderait jamais rien serait vert. */
adAppels=0;
var a2=AD({fetch:FETCH(REP(!0,{ok:!0,dur:21.233})),timer:TOUT_DE_SUITE});
out.ad_delai_gagne=a2.premier;
out.ad_delai_une_seule_reponse=a2.n;
out.ad_delai_la_reponse_est_bien_passee=adAppels;
/* UN `src` QUE `JSON.stringify` REFUSE (cycle) : sortie nommee, aucun appel. */
adAppels=0;
var circ={};circ.self=circ;
var vusC=[];
try{T.askDur(circ,{fetch:FETCH(REP(!0,{ok:!0,dur:9})),timer:JAMAIS,
  done:function(v,pq){vusC.push([v,pq])}})}
catch(e){vusC.push(["LEVE:"+e.name,"LEVE"])}
out.ad_src_illisible=vusC[0]||null;
out.ad_src_illisible_zero_appel=adAppels;
/* SANS `done` : la fonction ne doit pas lever (repli en fonction vide). */
try{T.askDur({job_id:"j"},{fetch:FETCH(REP(!0,{ok:!0,dur:3})),timer:JAMAIS});
  out.ad_sans_done="ok"}
catch(e){out.ad_sans_done="LEVE:"+e.name}
/* UN DELAI ILLISIBLE RETOMBE SUR LE DEFAUT — mesure par ce que le timer
   RECOIT, pas par une lecture de variable interne. */
var msVu=null;
T.askDur({job_id:"j"},{fetch:FETCH(REP(!0,{ok:!0,dur:3})),
  timer:function(fn,ms){msVu=ms},delai:"abc",done:JAMAIS});
out.ad_delai_illisible=msVu;
var msVu2=null;
T.askDur({job_id:"j"},{fetch:FETCH(REP(!0,{ok:!0,dur:3})),
  timer:function(fn,ms){msVu2=ms},delai:250,done:JAMAIS});
out.ad_delai_recu=msVu2;
/* ══ BARRE D'OUTILS — LES DIX TRACES ET LE BOUTON D'ACTION (etapes 2 et 3) ══
   L'ALLER-RETOUR EST LA MESURE. La couche garde les traces en CHAINE — le
   texte du §3, au caractere pres — et les traduit une fois au chargement.
   `tbSerial` refait le chemin inverse : si la traduction perd un attribut ou
   en reordonne un, elle ne rend plus le texte de depart. Le banc compare ces
   dix chaines au §3 lu DANS design.md : ni la couche ni le banc ne recopient
   un trace, ils le lisent au meme endroit.

   FAUTE N°6, SEPTIEME MORSURE, TROUVEE DANS CE BLOC MEME. Ecrite sans
   `TBG`, cette sonde lisait `T.tbIcons["piste-video"][0][1]` NUEMENT.
   MESURE : en faisant rendre une liste VIDE a `dzmTbParse` (mutation M3),
   `undefined[1]` levait, node sortait en erreur, et le repli `d = {}` du
   harnais emportait CENT QUATRE-VINGT-DIX-SEPT lignes — dont les ~150 de
   P4/P10/P11 qui n'ont rien a voir avec la barre. Le banc rougissait et
   imprimait son compte, il ne mourait pas ; mais UNE panne de parseur ne
   doit pas noircir tout le reste. Avec `TBG`, la meme mutation ne rougit
   plus que les lignes de la barre. Le temoin est DISTINGUABLE — jamais
   `null`, jamais `""` — et nomme le type de la levee. */
function TBG(fn){try{var v=fn();return v===void 0?"INDEFINI":v}
  catch(e){return "LEVE:"+e.name}}
out.tb_noms=Object.keys(T.tbTraces);
out.tb_aller_retour={};
Object.keys(T.tbTraces).forEach(function(k){
  out.tb_aller_retour[k]=TBG(function(){return T.tbSerial(T.tbIcons[k])})});
out.tb_groupes=T.TB_GROUPES;
out.tb_px=[T.TB_PX,T.TB_PX_GRIP];
/* LE NOMBRE D'ELEMENTS PAR TRACE. Sans lui, un parseur qui ne rendrait
   RIEN passerait l'aller-retour : les deux cotes vaudraient "". */
out.tb_elements=Object.keys(T.tbIcons).map(function(k){
  var v=T.tbIcons[k];
  return [k,(v&&typeof v.length==="number")?v.length:"LEVE"]});
out.tb_balises=TBG(function(){
  return T.tbIcons["piste-video"].map(function(e){return e[0]})});
out.tb_attrs=TBG(function(){return T.tbIcons["piste-video"][0][1]});
/* Le camelCase : aucun des dix traces n'en a besoin aujourd'hui, la ligne
   le mesure donc sur une entree faite pour ca. */
out.tb_camel=TBG(function(){
  return T.tbParse('<path fill-rule="evenodd" d="M0 0z"/>')[0][1]});
out.tb_parse_vide=TBG(function(){
  return [T.tbParse("").length,T.tbParse(null).length]});
/* ── L'ICONE, RENDUE ─────────────────────────────────────────────────── */
var tbIc=T.TbIcon({name:"emoji"});
out.tb_i_balise=TBG(function(){return tbIc.t});
out.tb_i_props=TBG(function(){return [tbIc.p.viewBox,tbIc.p.fill,
  tbIc.p.width,tbIc.p.height,tbIc.p["aria-hidden"],tbIc.p.className,
  tbIc.p.focusable]});
out.tb_i_enfants=TBG(function(){
  return tbIc.p.children.map(function(z){return z.t})});
out.tb_i_cles=TBG(function(){
  return tbIc.p.children.map(function(z){return z.k})});
out.tb_i_taille=TBG(function(){
  return T.TbIcon({name:"poignee",size:14}).p.width});
out.tb_i_taille_illisible=TBG(function(){
  return T.TbIcon({name:"emoji",size:"abc"}).p.width});
out.tb_i_taille_negative=TBG(function(){
  return T.TbIcon({name:"emoji",size:-4}).p.width});
/* NULL, et pas un `<svg>` vide : `TbIcon` doit RENDRE null, pas lever. Le
   `try` distingue les deux — `LEVE:` n'est pas `null`. */
out.tb_i_inconnue=TBG(function(){
  var v=T.TbIcon({name:"pasunicone"});return v===null?null:v});
out.tb_i_sans_nom=TBG(function(){var v=T.TbIcon();return v===null?null:v});
/* AUCUNE COULEUR DANS L'ICONE : `currentColor` et rien d'autre (§3). */
out.tb_i_sans_couleur=TBG(function(){
  var j=JSON.stringify(tbIc);
  return j.indexOf("#")<0&&j.indexOf("oklch")<0});
/* ── LE BOUTON D'ACTION, RENDU, DANS SES ETATS (§2.3) ────────────────── */
function TBB(o){return T.ToolBtn(o)}
function TBC(b){return (b&&b.p&&typeof b.p.className==="string")
  ?b.p.className:"LEVE"}
function TBP(b,k){return (b&&b.p&&(k in b.p))?b.p[k]:"ABSENT"}
var tbRepos=TBB({group:"pistes",icon:"piste-video",label:"vidéo"});
out.tb_b_balise=TBG(function(){return tbRepos.t});
out.tb_b_type=TBP(tbRepos,"type");
out.tb_b_classe=TBC(tbRepos);
out.tb_b_grp=TBP(tbRepos,"data-grp");
out.tb_b_titre=TBP(tbRepos,"title");
out.tb_b_aria=TBP(tbRepos,"aria-label");
out.tb_b_pressed_absent=TBG(function(){
  return !("aria-pressed" in tbRepos.p)});
out.tb_b_enfants=TBG(function(){
  return tbRepos.p.children.map(function(z){return z&&z.t})});
out.tb_b_libelle=TBG(function(){return tbRepos.p.children[1].p.children});
out.tb_b_libelle_classe=TBG(function(){
  return tbRepos.p.children[1].p.className});
out.tb_b_desactive=TBP(tbRepos,"disabled");
/* Les cinq groupes donnent cinq classes de teinte, une chacun. */
out.tb_b_classes=TBG(function(){return T.TB_GROUPES.map(function(g){
  return TBC(TBB({group:g,icon:"texte",label:"x"}))})});
/* GROUPE INCONNU : pas de classe de teinte, pas de `data-grp` — jamais une
   classe `dzm-g-rouge` que la feuille ne connaitrait pas. */
var tbMauvais=TBB({group:"rouge",icon:"texte",label:"x"});
out.tb_b_groupe_inconnu=TBC(tbMauvais);
out.tb_b_groupe_inconnu_data=TBG(function(){
  return !("data-grp" in tbMauvais.p)});
/* BASCULE — les trois valeurs d'`aria-pressed` et les deux classes. */
var tbOn=TBB({group:"mot",icon:"glow",label:"glow",toggle:!0,active:!0});
var tbOff=TBB({group:"mot",icon:"glow",label:"glow",toggle:!0,active:!1});
var tbMix=TBB({group:"mot",icon:"glow",label:"glow",toggle:!0,active:"mixed"});
out.tb_t_on=[TBC(tbOn),TBP(tbOn,"aria-pressed")];
out.tb_t_off=[TBC(tbOff),TBP(tbOff,"aria-pressed")];
out.tb_t_mix=[TBC(tbMix),TBP(tbMix,"aria-pressed")];
/* UNE ACTION SIMPLE N'A PAS D'ETAT : un `active` passe par erreur est
   ignore, et aucun `aria-pressed` n'est pose. */
var tbFaux=TBB({group:"pistes",icon:"piste-video",label:"v",active:!0});
out.tb_t_sans_bascule=[TBC(tbFaux),
  TBG(function(){return !("aria-pressed" in tbFaux.p)})];
/* SOLO — la classe de la colonne a bouton unique. */
out.tb_b_solo=TBC(TBB({group:"biblio",icon:"bibliotheque",label:"lier",
  solo:!0}));
/* LE CLIC, ET LE REFUS QUAND LE BOUTON EST ETEINT. */
var tbClics=0;
out.tb_b_clic=TBG(function(){
  TBB({group:"pistes",icon:"texte",label:"x",
    onAct:function(){tbClics++}}).p.onClick();
  return tbClics});
var tbClics2=0;
var tbMort=TBB({group:"mot",icon:"glow",label:"g",toggle:!0,disabled:!0,
  onAct:function(){tbClics2++}});
out.tb_b_clic_eteint=TBG(function(){tbMort.p.onClick();return tbClics2});
out.tb_b_eteint=[TBC(tbMort),TBP(tbMort,"disabled")];
out.tb_b_clic_sans_action=TBG(function(){
  TBB({group:"pistes",icon:"texte",label:"x"}).p.onClick();return "ok"});
/* MODE COMPACT : le libelle reste dans le DOM, `title` et `aria-label` le
   reprennent quand rien n'est donne — c'est ce qui interdit par
   construction un mode compact sans infobulle (§2.3). */
var tbT=TBB({group:"ajouts",icon:"emoji",label:"emoji",
  title:"Insérer un emoji",aria:"Insérer un emoji à la tête de lecture"});
out.tb_b_titre_donne=[TBP(tbT,"title"),TBP(tbT,"aria-label")];
/* AUCUNE COULEUR DANS LE BOUTON : ni hexa, ni oklch, ni `var(--…)`. La
   teinte passe par la classe, jamais par une chaine fabriquee en JS. */
out.tb_b_sans_couleur=TBG(function(){
  var j=JSON.stringify([tbRepos,tbOn,tbMix,tbMort,tbMauvais]);
  return j.indexOf("#")<0&&j.indexOf("oklch")<0&&j.indexOf("var(--")<0});
console.log(JSON.stringify(out));
"""
# "use strict" en PROLOGUE du shim : concatene, celui de montage.js n'est
# plus une directive mais une expression morte, et le cœur tournerait
# RELACHE ici alors que le navigateur l'execute strict (module). Une
# affectation a une variable non declaree passerait au banc et leverait a
# l'ecran.
# STUB `r` (le jsx du bundle) : sans lui, le CORPS des composants n'est pas
# executable ici et six mutations de dzmGradeAllBtn — dont museler la note —
# laissaient le banc a 128/0. Il rend l'appel tel quel : {t, p, k} = balise,
# proprietes, cle. Cinq lignes pour mesurer un bouton entier.
JSX = 'var r={jsx:function(t,p,k){return{t:t,p:p,k:k}},jsxs:null};\n'
# `_VIDEO_EXTS` VENUE DU SERVICE, pas recopiee. Le repli n'est PAS la liste
# vide : `dzmIsVideoJob` traite `[]` comme une regle PRESENTE (seul `null` la
# dit injoignable) et ecarterait tout, d'ou une dizaine de lignes rouges qui
# ne diraient pas d'ou vient le mal. On retombe sur le seul `.mp4` — les cas
# planche/maillage/faux-ami restent justes — et la ligne dediee ci-dessous
# rougit SEULE. Rougir, pas mourir : le `groupe(1)` d'un `re.search` absent
# aurait leve, et emporte les 80 assertions de la section [3].
_m_exts = re.search(r"_VIDEO_EXTS = \(([^)]*)\)", SVC)
_exts_svc = re.findall(r'"([^"]+)"', _m_exts.group(1)) if _m_exts else []
check("backend_la_liste_video_est_extractible_pour_le_banc",
      len(_exts_svc) >= 1 and all(e.startswith(".") for e in _exts_svc),
      f"_VIDEO_EXTS illisible dans {SERVICE.name} : {_exts_svc}")
# `svmRuler` / `svmPad2` du BUNDLE, extraites et jouees a cote de la
# couche. La couche les APPELLE (elle est injectee dans la meme portee
# module) au lieu de recopier le format m:ss : une seconde version
# divergerait de la premiere au premier changement. Le repli EST le texte
# exact que la ligne ci-dessous exige de trouver dans le bundle — ce n'est
# donc pas une copie qui puisse deriver en silence : le jour ou le bundle
# change ces deux fonctions, CETTE ligne rougit, seule, et les ~45 lignes
# de P10 restent lisibles au lieu d'etre emportees par un ReferenceError
# sous node (faute n°6 : rougir, pas mourir).
_PAD2 = 'function svmPad2(n){n=Math.floor(n);return (n<10?"0":"")+n}'
_RULER = ('function svmRuler(s){var m=Math.floor(s/60);'
          'return m+":"+svmPad2(s-m*60)}')
check("bundle_svmRuler_et_svmPad2_extraites",
      s.count(nl(_PAD2)) == 1 and s.count(nl(_RULER)) == 1,
      f"pad2={s.count(nl(_PAD2))} ruler={s.count(nl(_RULER))}")
RULER_SRC = _PAD2 + "\n" + _RULER + "\n"
shim.write_text('"use strict";\n' + "var window={};var SVM_TRACK_BUS={};\n" + JSX
                + SVM_SRC.replace("\r\n", "\n") + "\n"
                + RULER_SRC + src + "\n"
                + probe.replace("__DZ_VIDEO_EXTS__",
                                json.dumps(_exts_svc or [".mp4"])),
                encoding="utf-8")
r = NODE(["node", str(shim)])
if r.returncode != 0:
    check("js_shim_execute", False, (r.stderr or "")[-500:])
    d = {}
else:
    check("js_shim_execute", True)
    # TROISIEME ligne de la même famille : `splitlines()[-1]` sur une sortie
    # vide lève IndexError, et `json.loads` sur une dernière ligne qui n'est
    # pas du JSON lève JSONDecodeError — node peut sortir rc=0 dans les deux
    # cas (un `console.log` déplacé suffit). Le `if r.returncode != 0`
    # ci-dessus ne couvrait ni l'un ni l'autre. Rougir, pas mourir : `d`
    # retombe sur le dict vide, et les ~90 lignes suivantes rougissent une à
    # une en lisant `d.get(…)` au lieu d'être emportées en silence.
    _lignes = r.stdout.strip().splitlines()
    _derniere = _lignes[-1] if _lignes else ""
    try:
        d = json.loads(_derniere) if _derniere else None
        _mal = "" if isinstance(d, dict) and d else "sortie sans objet JSON"
    except Exception as _e:
        d, _mal = None, "%s: %s" % (type(_e).__name__, _e)
    if not isinstance(d, dict):
        d = {}
    check("js_shim_rend_un_objet_json", _mal == "",
          f"{_mal} — {len(_lignes)} ligne(s), dernière={_derniere[:120]!r}")

BASE = ["v2", "v1", "a1", "a2", "a3", "s1"]
check("js_defauts_identiques_a_SVM_TRACKS", d.get("base") == BASE, str(d.get("base")))
# LE point de non-divergence : mêmes six pistes, mêmes noms, mêmes hauteurs,
# mêmes couleurs que la table du bundle. C'est ce qui garantit que l'écran
# par défaut est identique au pixel après ce patch.
check("js_defauts_meme_habillage_que_le_bundle",
      d.get("skin_len") is True and d.get("skin_diff") == [],
      f'len={d.get("skin_len")} diff={d.get("skin_diff")}')
check("js_move_a3_monte", d.get("move_a3_up") == ["v2", "v1", "a1", "a3", "a2", "s1"],
      str(d.get("move_a3_up")))
check("js_move_v1_refuse", d.get("move_v1_up") == BASE, str(d.get("move_v1_up")))
check("js_move_v2_descend_refuse", d.get("move_v2_down") == BASE,
      str(d.get("move_v2_down")))
check("js_drag_v2_bloque_au_groupe", d.get("drag_v2_to_s1") == BASE,
      str(d.get("drag_v2_to_s1")))
# le cas qui RÉUSSIT : sans lui, un moveTo qui ne bougerait jamais rien
# passerait le banc.
check("js_drag_a1_sous_a3",
      d.get("moveto_a1_apres_a3") == ["v2", "v1", "a2", "a3", "a1", "s1"],
      str(d.get("moveto_a1_apres_a3")))
check("js_add_video_en_v3_tout_en_haut",
      d.get("add_video") == ["v3"] + BASE, str(d.get("add_video")))
check("js_add_audio_en_a4_avant_s1",
      d.get("add_audio") == ["v2", "v1", "a1", "a2", "a3", "a4", "s1"],
      str(d.get("add_audio")))
check("js_remove_v1_refuse", d.get("rm_v1") == BASE, str(d.get("rm_v1")))
# B1 : retirer S1 emportait TOUS les sous-titres (ce sont ses clips), rien
# ne savait la recréer, et l'autosave figeait la perte au rechargement.
check("js_remove_s1_refuse", d.get("rm_s1") == BASE, str(d.get("rm_s1")))
check("js_remove_a2", d.get("rm_a2") == ["v2", "v1", "a1", "a3", "s1"],
      str(d.get("rm_a2")))
check("js_bus_defaut_identique_au_bundle",
      d.get("bus_defaut") == {"a1": "dialogue", "a2": "musique", "a3": "sfx"},
      str(d.get("bus_defaut")))
check("js_bus_perso_remplace_tout", d.get("bus_perso") == {"a7": "musique"},
      str(d.get("bus_perso")))
check("js_bus_mute_en_place", d.get("bus_meme_objet") is True,
      "svmTrackBusSync a REMPLACÉ l'objet — les neuf lecteurs du bundle "
      "garderaient l'ancien")
check("js_payload_minimal",
      d.get("payload") == [{"id": "v2", "kind": "video"},
                           {"id": "v1", "kind": "video"},
                           {"id": "a1", "kind": "audio", "bus": "dialogue"},
                           {"id": "a2", "kind": "audio", "bus": "musique", "loop": True},
                           {"id": "a3", "kind": "audio", "bus": "sfx"},
                           {"id": "s1", "kind": "subs"}], str(d.get("payload")))
check("js_from_conserve_ordre", d.get("from_ids") == ["v3", "v1", "a1"],
      str(d.get("from_ids")))
# le payload serveur ne porte ni nom, ni hauteur, ni couleur : sans le repli
# dzmSkin, une piste v3 restaurée revenait en bande de 0 px, invisible, et
# pourtant porteuse de clips.
check("js_from_rhabille_piste_neuve", d.get("from_v3_habillee") is True,
      "v3 restaurée sans nom / sans hauteur")
# `is None` SUR UN DICT QUI PEUT ETRE VIDE : `d` retombe sur `{}` des que
# node ne rend pas d'objet JSON, et `{}.get(x)` vaut `None` — la ligne
# verdit sans qu'une instruction de JS ait tourne. MESURE le 05/09/2026
# (banc relance sans node) : ces deux lignes et `js_bouton_null_sans_
# etalonnage` etaient VERTES. On exige donc que la CLE SOIT LA — le shim la
# pose toujours, fut-ce a `null` — avant de lire sa valeur.
check("js_from_sans_v1_refuse",
      "from_sans_v1" in d and d["from_sans_v1"] is None,
      str(d.get("from_sans_v1")))
check("js_from_vide_refuse", "from_vide" in d and d["from_vide"] is None,
      str(d.get("from_vide")))
check("js_from_ignore_les_doublons", d.get("from_doublons") == ["v1", "a1"],
      str(d.get("from_doublons")))
ec = (d.get("emoji_defaut") or [None])[0]
check("js_emoji_clip_sur_v2", isinstance(ec, dict) and ec.get("tr") == "v2",
      str(ec))
check("js_emoji_clip_cale_sur_le_mot",
      isinstance(ec, dict) and ec.get("start") == 1.2 and ec.get("end") == 2.0,
      str(ec and (ec.get("start"), ec.get("end"))))
check("js_emoji_clip_porte_le_png",
      isinstance(ec, dict) and (ec.get("src") or {}).get("file_path")
      == "C:/x/1f525.png", str(ec and ec.get("src")))
check("js_emoji_suit_la_piste_la_plus_haute", d.get("emoji_v3") == ["v3"],
      str(d.get("emoji_v3")))
check("js_emoji_sans_overlay_ne_pose_rien", d.get("emoji_sans_overlay") == [],
      str(d.get("emoji_sans_overlay")))
check("js_emoji_sans_png_ecarte", d.get("emoji_sans_png") == [],
      str(d.get("emoji_sans_png")))
# les trois valeurs de la chip, dans l'ordre : « couleur » d'abord, c'est le
# comportement HISTORIQUE et le défaut — la chip ne change rien sans clic.
check("js_chip_trois_valeurs",
      d.get("word_anims") == ["couleur", "rebond", "glow"],
      str(d.get("word_anims")))

# ── P4 : gradeAll, le cœur pur du bouton « à tous les plans » ───────────────
# Six clips : a (source, avec LUT + étalonnage borné dans le temps), b (V1
# sans effet), c (V1 avec un AUTRE étalonnage + une vignette), d (démo, sans
# `src`), e (piste v2), f (V1 portant DÉJÀ exactement l'étalonnage de a).
# Donc 3 cibles (b, c, f — et pas d ni e), 2 modifiées, 1 remplacée.
check("js_grade_compte_cibles_et_modifies", d.get("g_compte") == [3, 2, 1],
      str(d.get("g_compte")))
# [a] les bornes de TEMPS ne se recopient pas : les SIX clés de la source
# restent chez elle. Sans cette règle, un étalonnage limité à [0,5 s ; 1,5 s]
# sur un plan de 2 s couvrait presque tout un plan plus court — et sa rampe
# (fondu d'entrée/de sortie, courbes) partait avec lui.
check("js_grade_ne_recopie_pas_les_bornes_de_temps",
      d.get("g_b") == [{"type": "grade_basic", "exposure": 20,
                        "temperature": 3200}], str(d.get("g_b")))
# La MÊME règle, nommée clé par clé. `VfxBounds` (vfxrack.js) est rendu pour
# chaque effet ouvert de la pile, `grade_basic` compris, et pose fade_in,
# fade_out, ease_in et ease_out au même titre que t0/t1 : la fixture les porte
# toutes les six. Avant, seules t0/t1 y étaient et réduire `DZM_GRADE_TIMING`
# à ["t0","t1"] laissait ce banc à 139/0.
check("js_grade_ne_recopie_aucune_borne_de_rampe",
      d.get("g_b_rampe") == [],
      f'cles de temps passees dans la copie : {d.get("g_b_rampe")}')
# le plan qui portait un AUTRE étalonnage : celui-ci est remplacé EN PLACE
# (rang 0 de la pile), la vignette qui suivait reste où elle était.
check("js_grade_remplace_en_place_et_garde_le_reste",
      d.get("g_c") == [{"type": "grade_basic", "exposure": 20,
                        "temperature": 3200},
                       {"type": "vignette", "intensity": 50}],
      str(d.get("g_c")))
check("js_grade_ignore_la_demo_sans_src", d.get("g_d") is True, str(d.get("g_d")))
check("js_grade_ignore_les_autres_pistes", d.get("g_e") is True, str(d.get("g_e")))
# [c] un plan déjà identique n'est pas réécrit — il ne compte pas dans le lot
# et sa ligne ne bouge pas.
check("js_grade_laisse_le_plan_deja_identique",
      d.get("g_f_intacte") is True, str(d.get("g_f_intacte")))
check("js_grade_ne_touche_pas_la_source",
      d.get("g_source_intacte") is True, str(d.get("g_source_intacte")))
# [b] LE piège : une seule copie partagée aurait fait de tout réglage
# ultérieur sur un plan un réglage sur TOUS. Mesure directe — on écrit 99 sur
# la copie de `b`, on relit celle de `c`.
check("js_grade_une_copie_par_plan", d.get("g_copies_independantes") == 20,
      f'exposition de c apres ecriture sur b : {d.get("g_copies_independantes")}')
check("js_grade_sans_etalonnage_source_ne_fait_rien",
      d.get("g_sans_source") == [0, 0, 0]
      and d.get("g_sans_source_intact") is True,
      f'{d.get("g_sans_source")} / {d.get("g_sans_source_intact")}')
check("js_grade_entrees_molles",
      d.get("g_nul") == 0 and d.get("g_inconnu") == 0
      and d.get("gradeOf_absent") is None,
      f'nul={d.get("g_nul")} inconnu={d.get("g_inconnu")} '
      f'gradeOf={d.get("gradeOf_absent")}')
# [d] cas de bord ASSUMÉ : deux `grade_basic` empilés sur une cible. Seul le
# PREMIER est remplacé, le second survit — le geste ne touche que la ligne que
# `dzmGradeOf` désigne, il ne fait pas le ménage dans une pile posée à la
# main. Épinglé pour que ce choix ne dérive pas en silence.
check("js_grade_ne_remplace_que_le_premier",
      d.get("g_deux_grades") == [{"type": "grade_basic", "exposure": 20},
                                 {"type": "grade_basic", "contrast": 150}],
      str(d.get("g_deux_grades")))

# ── P4 / B1 : la PISTE visée est celle du plan sélectionné ──────────────────
# LE défaut que ces lignes referment : `dzmGradeAllBtn` codait « v1 » EN DUR
# aux deux appels. Mesuré, plan V2 étalonné sélectionné — le bouton était
# ACTIF, écrasait l'étalonnage des DEUX plans V1 ([2, 2, 2]) et ne touchait
# aucun clip V2. Rien ne le voyait : la mutation qui vise « v2 » laissait ce
# banc à 128/0.
check("js_grade_source_v2_ne_touche_pas_v1",
      d.get("gv_compte") == [1, 1, 0] and d.get("gv_v1_intact") is True
      and d.get("gv_v2_ecrit") == [{"type": "grade_basic", "exposure": 70,
                                    "temperature": 3200}],
      f'{d.get("gv_compte")} v1_intact={d.get("gv_v1_intact")} '
      f'v2={d.get("gv_v2_ecrit")}')
check("js_bouton_suit_la_piste_du_plan",
      d.get("bv_libelle") == "étalonnage → tous les plans V2"
      and d.get("bv_actif") is True
      and "sur 1 autre plan V2." in (d.get("bv_titre") or ""),
      f'{d.get("bv_libelle")} | {d.get("bv_titre")}')
# MESURE backend : `montage_service.py` n'appelle `build_chain` QUE dans la
# boucle des segments V1, et le dictionnaire d'un overlay V2 ne porte même pas
# de clé `effects`. Un étalonnage posé sur V2 ne rend NULLE PART — le bouton
# le DIT plutôt que de disparaître : la lacune est antérieure à lui et vaut
# aussi pour l'effet posé à la main.
# L'avertissement est épinglé ENTIER, ses DEUX phrases : la première dit que
# le rendu ne l'emporte pas, la seconde dit CE QUI SE VERRA ET OÙ — et c'est
# elle qui répond à « alors pourquoi ce bouton marche-t-il ? ». Mesure : avec
# un motif sur la seule première phrase, supprimer la seconde laissait le banc
# à 139/0. `endswith` épingle aussi sa PLACE : l'avertissement finit le texte,
# il ne s'insère pas au milieu de la phrase qui décrit le lot.
_AV = (" ATTENTION — mesuré : le rendu n'emporte pas les effets des pistes "
       "d'overlay. Sur V2, cet étalonnage se verra dans l'inspecteur et dans "
       "l'aperçu, pas dans la vidéo exportée.")
check("js_bouton_hors_v1_avertit_du_rendu",
      (d.get("bv_titre") or "").endswith(_AV)
      and "ATTENTION" not in (d.get("b_titre") or ""),
      f'V2:{d.get("bv_titre")!r} | V1 porte ATTENTION : '
      f'{"ATTENTION" in (d.get("b_titre") or "")}')
# ET DANS LA NOTE, pas seulement dans le titre. P4 revendiquait « hors V1, le
# titre ET la note portent l'avertissement » : sous banc ce n'était vrai qu'à
# moitié — retirer `+hors` de la note laissait ce banc à 139/0, parce que rien
# ne CLIQUAIT le bouton V2 et que la note V1, elle, vaut la chaîne vide.
check("js_bouton_hors_v1_avertit_aussi_dans_la_note",
      (d.get("bv_note") or "").endswith(_AV)
      and "ATTENTION" not in (d.get("b_note") or ""),
      f'note V2 : {d.get("bv_note")!r}')

# ── P4 : le CORPS du bouton, exécuté (stub `r` du shim) ─────────────────────
# Avant le stub, RIEN n'appelait ce corps : six mutations — museler la note,
# vider la phrase des bornes de temps, retourner un bouton toujours actif —
# laissaient le banc à 128/0. Les trois états du titre sont mesurés ici.
check("js_bouton_titre_du_lot",
      d.get("b_titre") == "Recopier l'exposition, le contraste, la saturation "
      "et la température de ce plan sur 2 autres plans V1, dont 1 dont "
      "l'étalonnage actuel sera REMPLACÉ. Les bornes de temps de l'effet ne "
      "sont pas recopiées : l'étalonnage porte sur le plan entier. Annuler "
      "restaure l'étalonnage de chaque plan tel qu'il était."
      and d.get("b_libelle") == "étalonnage → tous les plans V1"
      and d.get("b_actif") is True, str(d.get("b_titre")))
# UNE seule cible déjà identique. La phrase livrée disait « Les 1 autre plan
# V1 porte déjà… » : le pluriel se décidait sur `targets>1` mais l'article
# restait « Les ».
check("js_bouton_une_seule_cible_deja_identique",
      d.get("b_un_titre") == "Le seul autre plan V1 porte déjà exactement "
                             "cet étalonnage."
      and d.get("b_un_mort") is True, str(d.get("b_un_titre")))
check("js_bouton_aucune_cible",
      d.get("b_seul_titre") == "Aucun autre plan V1 : rien à étalonner "
                               "ailleurs."
      and d.get("b_seul_mort") is True, str(d.get("b_seul_titre")))
# Pas d'étalonnage sur le plan sélectionné : NULL, pas un bouton mort.
# meme piege, meme remede que [js_from_sans_v1_refuse] : la cle d'abord.
check("js_bouton_null_sans_etalonnage",
      "b_sans_etalonnage" in d and d["b_sans_etalonnage"] is None,
      str(d.get("b_sans_etalonnage")))
# `aria-label` : l'ÉTAT y est replié. Un aria-label figé masquait la seule
# phrase qui dit pourquoi le bouton est éteint — quand il existe, les lecteurs
# d'écran n'annoncent plus le `title`. Le libellé visible en reste le PRÉFIXE
# (WCAG « Label in Name »), sinon la commande vocale ne trouve plus le bouton.
# QUATRIEME ligne de la famille de la faute n°6, et la plus retorse : ces
# concatenations s'appliquaient NUEMENT au retour de `d.get(…)`. MESURE du
# 04/09/2026 : quand la sonde node ne rend pas d'objet — et le repli
# `d = {}` du `if r.returncode != 0` ci-dessus mene EXACTEMENT la — la ligne
# levait `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'`
# apres 46 lignes deja rougies, sans jamais imprimer le compte. Le repli qui
# devait sauver le banc ne le sauvait pas. Les trois `isinstance` d'abord :
# le `and` court-circuite, plus rien ne se concatene a None.
_b_lib = d.get("b_libelle")
_b_tit = d.get("b_titre")
_b_un_tit = d.get("b_un_titre")
check("js_bouton_aria_replie_l_etat",
      isinstance(_b_lib, str) and isinstance(_b_tit, str)
      and isinstance(_b_un_tit, str)
      and d.get("b_aria") == _b_lib + " — " + _b_tit
      and d.get("b_un_aria") == _b_lib + " — " + _b_un_tit,
      str(d.get("b_un_aria")))
# LE geste, joué : historique poussé AVANT l'écriture, drapeau `dirty` allumé,
# note émise — dans cet ordre, et le lot complet rendu à setClips.
check("js_bouton_geste_ordre_et_drapeau",
      d.get("b_journal") == ["pushHistory", "setClips", "setDirty=true",
                             "note"] and d.get("b_ecrit") == 6,
      f'{d.get("b_journal")} ecrit={d.get("b_ecrit")}')
check("js_bouton_note_dit_ce_qui_a_change",
      d.get("b_note") == "Étalonnage appliqué à 2 plans V1 (dont 1 dont "
      "l'étalonnage a été remplacé). Les bornes de temps ne sont pas "
      "recopiées. Annuler restaure l'étalonnage de chaque plan tel qu'il "
      "était.", str(d.get("b_note")))

# ── P5 : le cœur pur, EXECUTE ────────────────────────────────────────────
# Ce que la ligne de resume doit trancher entre deux montages : le NOMBRE de
# plans et la DATE. Jamais l'identifiant, qui n'apprend rien a personne.
check("js_proj_ligne_complete",
      d.get("pl_plein") == "3 clips · 9:16 · 12,3 s · 04/09 13:42 UTC",
      str(d.get("pl_plein")))
# le SINGULIER, et la virgule decimale : la meme phrase que « Le seul autre
# plan V1 » de P4 corrigeait deja une fois.
check("js_proj_ligne_singulier", d.get("pl_un") == "1 clip · 16:9 · 4,0 s",
      str(d.get("pl_un")))
# entrees molles : rien du tout, et un projet vide. Une ligne VIDE ferait une
# rangee sans repere ; « 0 clip » dit au moins qu'il n'y a rien dedans.
check("js_proj_ligne_molle",
      d.get("pl_vide") == "0 clip" and d.get("pl_zero") == "0 clip",
      f'{d.get("pl_vide")} / {d.get("pl_zero")}')
check("js_proj_date_sans_fuseau", d.get("pw_bon") == "02/01 03:04 UTC",
      str(d.get("pw_bon")))
# une date illisible rend "" — donc la ligne se contente de ce qu'elle sait,
# au lieu d'afficher « NaN/NaN » ou « Invalid Date ».
check("js_proj_date_illisible_rend_vide",
      d.get("pw_casse") == "" and d.get("pw_nul") == "",
      f'{d.get("pw_casse")!r} / {d.get("pw_nul")!r}')

# ── P9 : le cœur pur, EXECUTE ────────────────────────────────────────────
# LE CAS MESURE. Sur les pistes de la sauvegarde reelle — [v1, a2, a1, a3,
# s1], sans v2 — la piste video resolue est v1. C'est la ligne qui dit que le
# clip cesse d'aller dans le vide.
check("pick_video_sans_v2", d.get("pick_v") == "v1", str(d.get("pick_v")))
# le PARAMETRE `kind` decide vraiment : sur les MEMES pistes, l'audio rend a2.
check("pick_audio_sur_les_memes_pistes", d.get("pick_a") == "a2",
      str(d.get("pick_a")))
check("pick_subs_sur_les_memes_pistes", d.get("pick_s") == "s1",
      str(d.get("pick_s")))
# la PREMIERE du genre, pas la premiere tout court — et sans `kind` declare,
# donc en deduisant le genre de l'identifiant.
check("pick_video_prend_la_premiere", d.get("pick_1re") == "v3",
      str(d.get("pick_1re")))
# aucune piste du genre : "" — un refus, pas un identifiant invente.
check("pick_sans_piste_du_genre", d.get("pick_aucune") == "",
      repr(d.get("pick_aucune")))
check("pick_entrees_molles",
      d.get("pick_vide") == "" and d.get("pick_nul") == "",
      f'{d.get("pick_vide")!r} / {d.get("pick_nul")!r}')
# ── le filtre du selecteur, applique a la lettre du backend ──────────────
check("job_video_acceptee", d.get("jv_mp4") is True, str(d.get("jv_mp4")))
# LES DEUX FAMILLES QUE P8 ECARTE et que le selecteur proposait encore.
check("job_planche_sprite_ecartee", d.get("jv_planche") is False,
      str(d.get("jv_planche")))
check("job_maillage_ecarte", d.get("jv_maillage") is False,
      str(d.get("jv_maillage")))
check("job_pas_fini_ecarte", d.get("jv_encours") is False,
      str(d.get("jv_encours")))
# L'ORDRE des deux chemins est celui du serveur : le fini prime sur le brut.
check("job_final_video_path_prime_sur_video_path",
      d.get("jv_final_prime") is False, str(d.get("jv_final_prime")))
check("job_extension_insensible_a_la_casse", d.get("jv_majuscules") is True,
      str(d.get("jv_majuscules")))
check("job_previsualisation_de_montage_ecartee", d.get("jv_preview") is False,
      str(d.get("jv_preview")))
check("job_sans_artefact_ecarte",
      d.get("jv_sans_chemin") is False and d.get("jv_nul") is False,
      f'{d.get("jv_sans_chemin")} / {d.get("jv_nul")}')
# REGLE INJOIGNABLE : on ne filtre pas — et R_M16C le dit a l'ecran (ligne
# `M16c_dit_a_l_ecran_qu_il_ne_filtre_pas`). C'est le seul repli honnete :
# une liste vide aurait menti, une liste ecrite ici serait la seconde copie.
check("job_sans_regle_ne_filtre_pas", d.get("jv_sans_regle") is True,
      str(d.get("jv_sans_regle")))
# le suffixe est EXTRAIT, pas cherche en fin de chaine : « a.mp4.zip » n'est
# pas une video, et un `endsWith` naif aurait dit oui.
check("job_faux_ami_mp4_zip_ecarte", d.get("jv_faux_ami") is False,
      str(d.get("jv_faux_ami")))
# ── le bouton « Bibliotheque… » ──────────────────────────────────────────
check("libbtn_ouvre_sur_la_piste_resolue", d.get("lib_pick") == "v1",
      str(d.get("lib_pick")))
check("libbtn_porte_le_mot_de_l_utilisateur",
      d.get("lib_label") == "Bibliothèque…", str(d.get("lib_label")))
check("libbtn_dit_sur_quelle_piste_il_posera",
      d.get("lib_titre_nomme_la_piste") is True,
      str(d.get("lib_titre_nomme_la_piste")))
# SANS piste video : rien n'est ouvert, et la note NOMME la sortie.
check("libbtn_sans_piste_video_n_ouvre_rien",
      d.get("lib_sans_piste_n_ouvre_rien") is True,
      str(d.get("lib_sans_piste_n_ouvre_rien")))
check("libbtn_sans_piste_video_nomme_la_sortie",
      d.get("lib_sans_piste_note") == "Aucune piste vidéo dans ce projet — "
      "« + piste vidéo » en crée une, puis « Bibliothèque… » y posera le clip.",
      str(d.get("lib_sans_piste_note")))
# ── la chip « pas une video » ────────────────────────────────────────────
check("chip_non_video_dit_ce_qu_elle_est",
      d.get("bad_label") == "pas une vidéo", str(d.get("bad_label")))
check("chip_non_video_offre_la_sortie", d.get("bad_fix") == "c3",
      str(d.get("bad_fix")))
# DEUX arrets de propagation : sans celui du pointerdown, le clic amorcerait
# le deplacement du clip qui est SOUS la chip.
check("chip_non_video_n_amorce_pas_le_deplacement",
      d.get("bad_arrete_les_deux") == 2, str(d.get("bad_arrete_les_deux")))
# LA CHIP DIT LES DEUX CAS, et c'est une RECTIFICATION du brief de la tache.
# « POST /render refuse deja ces clips en 400 » n'est vrai que pour une PARTIE
# d'entre eux : `v1_non_video` liste ce qui n'est pas dans `_VIDEO_EXTS` (6
# extensions), le pre-vol refuse ce que `_ffmpeg_ouvrira` rejette, c'est-a-dire
# hors de `_VIDEO_EXTS + _IMAGE_EXTS + _AUDIO_EXTS`, et `_IMAGE_EXTS` contient
# `.png` (montage_service.py l.1488). Une planche de sprites PNG est donc
# SIGNALEE et PASSE le pre-vol — elle se rend en carton fixe ; un maillage
# .glb est signale ET refuse. Promettre un refus qui n'arrive pas aurait ete
# le meme defaut, a l'envers.
check("chip_non_video_distingue_l_echec_du_carton_fixe",
      d.get("bad_titre_echec") is True and d.get("bad_titre_carton") is True,
      f'echec={d.get("bad_titre_echec")} carton={d.get("bad_titre_carton")}')
# LA MESURE QUI FONDE CETTE FORMULATION, REJOUEE : sans elle, la phrase de la
# chip se perimerait au premier changement de `_IMAGE_EXTS`.
check("backend_le_prevol_laisse_passer_une_image",
      '_IMAGE_EXTS = (".png"' in SVC
      and "return p.suffix.lower() in _VIDEO_EXTS + _IMAGE_EXTS + _AUDIO_EXTS"
      in SVC,
      "le pre-vol ne laisse plus passer les images — la chip ment maintenant")

# ── P10 : la duree que le projet DOIT avoir (fitDur), jouee sous node ──────
# `dur` est un PLANCHER, jamais un plafond : `fitDur` ne raccourcit JAMAIS.
# Chaque ligne ci-dessous a ete rejouee par MUTATION de la couche : la table
# du commit dit laquelle rougit pour chacune.
check("js_fitdur_duree_min_est_le_plancher_de_svmApplyProject",
      d.get("dur_min") == 1, str(d.get("dur_min")))
for _lbl, _k, _att in (
        ("timeline_vide", "fd_vide", 16),
        ("clips_nuls", "fd_nul", 16),
        ("clips_indefinis", "fd_indefini", 16),
        ("clip_qui_rentre", "fd_rentre", 16),
        ("clip_qui_depasse", "fd_depasse", 20),
        ("clip_fractionnaire_arrondi_au_plafond",
         "fd_depasse_fractionnaire", 21),
        ("le_max_pas_le_dernier", "fd_prend_le_max_pas_le_dernier", 20),
        ("marge_de_queue", "fd_marge", 22),
        ("marge_negative_ignoree", "fd_marge_negative", 20),
        ("marge_illisible_ignoree", "fd_marge_illisible", 20),
        ("marge_sans_clip_ne_fait_rien", "fd_marge_sans_clip", 1),
        ("end_illisible_ignore", "fd_end_illisible", 16),
        ("end_infini_ignore", "fd_end_infini", 16),
        ("end_absent_ignore", "fd_end_absent", 16),
        ("clip_nul_ignore", "fd_clip_nul", 16),
        ("duree_nulle_retombe_sur_le_plancher", "fd_dur_nulle", 1),
        ("duree_negative_retombe_sur_le_plancher", "fd_dur_negative", 1),
        ("duree_illisible_retombe_sur_le_plancher", "fd_dur_illisible", 1),
        ("duree_infinie_retombe_sur_le_plancher", "fd_dur_infinie", 5),
        ("duree_fractionnaire_gardee_telle_quelle",
         "fd_dur_fractionnaire_gardee", 16.5),
        ("ne_raccourcit_jamais", "fd_ne_raccourcit_jamais", 30),
        ("cas_de_l_utilisateur_16s_plus_un_clip_a_20s",
         "fd_cas_utilisateur", 20)):
    check("js_fitdur_" + _lbl, d.get(_k) == _att,
          f"{d.get(_k)!r} attendu {_att!r}")

# ── P10 : le reglage explicite de la duree (dzmDurCtl), joue sous node ─────
check("js_durctl_est_un_groupe_du_transport",
      d.get("dc_classe") == "dzm-durctl", str(d.get("dc_classe")))
# LE NOMBRE AFFICHE NE DISPARAIT PAS : il demenage dans le controle, au meme
# format (`svmRuler` du bundle, jamais recopie).
check("js_durctl_montre_le_total_au_format_du_bundle",
      d.get("dc_valeur") == "0:30 total", str(d.get("dc_valeur")))
check("js_durctl_quatre_elements_quand_il_y_a_du_vide",
      d.get("dc_kids") == ["m", "v", "p", "f"], str(d.get("dc_kids")))
check("js_durctl_allonge_d_une_graduation",
      d.get("dc_plus_ok") is True and d.get("dc_plus_valeur") == 32,
      f'{d.get("dc_plus_ok")} / {d.get("dc_plus_valeur")}')
check("js_durctl_la_note_de_l_allongement_dit_les_deux_valeurs_et_le_pas",
      isinstance(d.get("dc_plus_note"), str)
      and "Timeline allongée de 0:30 à 0:32 (+2 s)" in d.get("dc_plus_note"),
      str(d.get("dc_plus_note"))[:160])
check("js_durctl_raccourcit_d_une_graduation",
      d.get("dc_moins_ok") is True and d.get("dc_moins_valeur") == 28,
      f'{d.get("dc_moins_ok")} / {d.get("dc_moins_valeur")}')
# « ajuster » PAIE LA DETTE DE P3 : sa note disait « raccourcissez-la si vous
# voulez » alors que RIEN ne permettait de la raccourcir.
check("js_durctl_ajuste_la_timeline_a_son_contenu",
      d.get("dc_ajuste_ok") is True and d.get("dc_ajuste_valeur") == 20,
      f'{d.get("dc_ajuste_ok")} / {d.get("dc_ajuste_valeur")}')
check("js_durctl_la_note_de_l_ajustement_chiffre_le_vide_retire",
      isinstance(d.get("dc_ajuste_note"), str)
      and "0:30 → 0:20" in d.get("dc_ajuste_note")
      and "10 s de queue vide" in d.get("dc_ajuste_note"),
      str(d.get("dc_ajuste_note"))[:160])
# LE PAS QUI TOMBERAIT SOUS LE CONTENU S'ARRETE DESSUS — et le DIT. Ce n'est
# pas le refus : la valeur change, elle s'arrete juste plus tot.
check("js_durctl_le_pas_s_arrete_sur_la_fin_du_dernier_clip",
      d.get("dc_arret_ok") is True and d.get("dc_arret_valeur") == 20
      and isinstance(d.get("dc_arret_note"), str)
      and "s'est arrêté sur la fin du dernier clip" in d.get("dc_arret_note"),
      f'{d.get("dc_arret_valeur")} — {str(d.get("dc_arret_note"))[:120]}')
# LE REFUS : geste destructif A L'ECRAN (les clips ne sont pas supprimes, mais
# `left:c.start/dur*100+"%"` les pousse hors de la bande et plus rien ne les
# montre). REFUSE, JAMAIS EN SILENCE — et le zero d'ecritures n'est lu que si
# le bouton a EXISTE, a ete CLIQUE, et qu'UNE note est sortie : sans ces trois
# conjoints, `dc_refus_ecritures == 0` serait vert sur un bouton disparu.
check("js_durctl_refuse_de_descendre_sous_le_dernier_clip",
      d.get("dc_refus_clic") is True and d.get("dc_refus_notes") == 1
      and d.get("dc_refus_ecritures") == 0
      and isinstance(d.get("dc_refus_note"), str)
      and "ferait sortir des clips du champ" in d.get("dc_refus_note"),
      f'clic={d.get("dc_refus_clic")} notes={d.get("dc_refus_notes")} '
      f'ecritures={d.get("dc_refus_ecritures")} '
      f'{str(d.get("dc_refus_note"))[:120]}')
# « ajuster » N'EXISTE PAS quand il n'y a rien a retirer : il disparait, il ne
# s'eteint pas. La liste EXIGE les trois autres — un controle vide passerait
# un simple « pas de f ».
check("js_durctl_pas_d_ajuster_quand_il_n_y_a_rien_a_retirer",
      d.get("dc_refus_kids") == ["m", "v", "p"], str(d.get("dc_refus_kids")))
check("js_durctl_timeline_vide_ajuste_au_plancher",
      d.get("dc_vide_ajuste") is True and d.get("dc_vide_valeur") == 1,
      f'{d.get("dc_vide_ajuste")} / {d.get("dc_vide_valeur")}')
check("js_durctl_le_plancher_d_une_seconde_est_refuse_aussi",
      d.get("dc_plancher_clic") is True
      and d.get("dc_plancher_ecritures") == 0,
      f'clic={d.get("dc_plancher_clic")} '
      f'ecritures={d.get("dc_plancher_ecritures")}')
check("js_durctl_entrees_illisibles_retombent_sur_le_plancher_et_un_pas_de_1s",
      d.get("dc_mou_valeur") == "0:01 total" and d.get("dc_mou_plus") == 2,
      f'{d.get("dc_mou_valeur")!r} / {d.get("dc_mou_plus")!r}')
# LA RESERVE CENTRALE DANS CHAQUE NOTE. Le `every` du sondage est vrai sur du
# vide : le compte des notes est le conjoint qui l'en empeche.
check("js_durctl_chaque_note_dit_que_annuler_ne_rend_pas_la_duree",
      d.get("dc_notes_comptees") == 3
      and d.get("dc_toutes_les_notes_disent_la_reserve") is True,
      f'notes={d.get("dc_notes_comptees")} '
      f'reserve={d.get("dc_toutes_les_notes_disent_la_reserve")}')
check("js_durctl_les_titres_nomment_le_pas",
      d.get("dc_titres_nomment_le_pas") is True,
      str(d.get("dc_titres_nomment_le_pas")))
# aria-label = ce que le bouton FAIT, avec son pas : « − » seul n'est pas
# annonçable.
check("js_durctl_les_boutons_sont_annoncables",
      d.get("dc_aria") == ["Raccourcir la timeline de 2 s",
                           "Allonger la timeline de 2 s"],
      str(d.get("dc_aria")))
check("js_durctl_les_secondes_en_francais",
      d.get("secs") == ["2 s", "0,5 s", "10 s", "0 s"], str(d.get("secs")))


# ── P11 : la longueur d'un clip, jouee sous node ──────────────────────────
# `clipLen` est PURE : chaque ligne ci-dessous a ete rejouee par MUTATION de
# la couche ; la table du commit dit laquelle rougit pour chacune.
#
# LE POINT DE TOUTE LA TACHE : une source de 21 s entre a 21 s. Le repli du
# bundle (6 s pour une video, 8 pour un son) ne s'applique plus QUE lorsque
# la duree est inconnue — et il est alors DIT.
def _cl(k):
    """Le triplet {len, origine} d'une entree de `clipLen`, ou un temoin.

    `d.get(k)` vaut `None` quand le shim n'a pas tourne : sans ce repli
    DISTINGUABLE, `.get("len")` leverait et emporterait la section entiere
    (faute n°6), et un `== None` verdirait sur du vide (faute n°2)."""
    v = d.get(k)
    if not isinstance(v, dict):
        return {"len": "ABSENT:%r" % (v,), "origine": "ABSENT"}
    return v


for _lbl, _k, _len, _org in (
        ("la_video_de_16s_entre_a_16s", "cl_video_16", 15.973, "source"),
        ("la_video_de_21s_entre_a_21s", "cl_video_21", 21.233, "source"),
        ("une_source_plus_courte_que_le_repli_garde_sa_longueur",
         "cl_video_courte", 3.5, "source"),
        ("une_source_minuscule_reste_minuscule",
         "cl_video_minuscule", 0.2, "source"),
        ("duree_nulle_retombe_sur_le_repli", "cl_video_zero", 6, "repli"),
        ("duree_negative_retombe_sur_le_repli",
         "cl_video_negatif", 6, "repli"),
        ("duree_nan_retombe_sur_le_repli", "cl_video_nan", 6, "repli"),
        ("duree_non_numerique_retombe_sur_le_repli",
         "cl_video_texte", 6, "repli"),
        ("duree_absente_retombe_sur_le_repli", "cl_video_absent", 6, "repli"),
        ("duree_infinie_retombe_sur_le_repli", "cl_video_infini", 6, "repli"),
        ("un_son_entre_a_sa_longueur", "cl_audio_source", 184.2, "source"),
        ("un_son_inconnu_retombe_sur_huit_secondes",
         "cl_audio_inconnu", 8, "repli"),
        ("une_image_vaut_quatre_secondes", "cl_image", 4, "image"),
        ("une_image_ignore_la_duree_qu_on_lui_passe",
         "cl_image_avec_duree", 4, "image"),
        ("les_replis_sont_ceux_de_l_appelant",
         "cl_defauts_recus", 10, "repli"),
        ("un_repli_illisible_retombe_sur_celui_de_la_couche",
         "cl_defauts_illisibles", 6, "repli"),
        ("un_repli_negatif_retombe_sur_celui_de_la_couche",
         "cl_defauts_negatifs", 8, "repli"),
        ("sans_replis_ceux_de_la_couche", "cl_defauts_absents", 6, "repli"),
        ("des_replis_nuls_ne_font_pas_lever", "cl_defauts_nuls", 6, "repli"),
        ("un_genre_inconnu_est_traite_comme_une_video",
         "cl_genre_inconnu", 6, "repli")):
    _v = _cl(_k)
    check("js_cliplen_" + _lbl,
          _v.get("len") == _len and _v.get("origine") == _org,
          f'{_v.get("len")!r}/{_v.get("origine")!r} attendu {_len!r}/{_org!r}')
check("js_cliplen_la_longueur_est_arrondie_au_millieme",
      d.get("cl_arrondi_au_millieme") == 15.973,
      str(d.get("cl_arrondi_au_millieme")))
check("js_cliplen_la_couche_garde_les_trois_replis_du_bundle_en_secours",
      d.get("cl_defauts_de_secours") == {"image": 4, "audio": 8, "video": 6},
      str(d.get("cl_defauts_de_secours")))
# LE REPLI EST DIT, ET C'EST LA MOITIE HONNETE DE LA TACHE : un clip pose a
# 6 s parce que l'application ignore la vraie longueur ne doit pas se faire
# passer pour une source de 6 s. La ligne exige que la note NOMME le chiffre
# ET dise que ce n'est pas celui de la source.
# L'ACCORD DE LA BRANCHE VIDEO, AJOUTE LE 05/09/2026. La branche AUDIO avait
# sa ligne depuis P11 ; la branche VIDEO n'en avait pas, et la phrase livree
# etait « Cette vidéo a été posé à 6 s ». MESURE : remettre la faute laissait
# le banc a 504/0 — un texte que l'utilisateur LIT a chaque source non
# mesurable, garde par rien.
check("js_cliplen_le_repli_video_est_DIT_et_accorde",
      "6 s" in _cl("cl_video_zero").get("note", "")
      and "PAR DÉFAUT" in _cl("cl_video_zero").get("note", "")
      and "pas la sienne" in _cl("cl_video_zero").get("note", "")
      and "Cette vidéo a été posée" in _cl("cl_video_zero").get("note", ""),
      str(_cl("cl_video_zero").get("note"))[:200])
check("js_cliplen_le_repli_audio_est_DIT_et_accorde",
      "8 s" in _cl("cl_audio_inconnu").get("note", "")
      and "Ce son" in _cl("cl_audio_inconnu").get("note", ""),
      str(_cl("cl_audio_inconnu").get("note"))[:200])
check("js_cliplen_le_repli_dit_quoi_faire",
      "Rognez le bord droit" in _cl("cl_video_zero").get("note", ""),
      str(_cl("cl_video_zero").get("note"))[:200])
# LA LONGUEUR CONNUE EST DITE AUSSI, avec la virgule decimale du francais.
check("js_cliplen_la_longueur_de_source_est_dite_en_francais",
      "21,2 s" in _cl("cl_video_21").get("note", "")
      and "ENTIÈRE" in _cl("cl_video_21").get("note", ""),
      str(_cl("cl_video_21").get("note"))[:200])
# UNE IMAGE N'A RIEN A CONFESSER : ses 4 s sont un cadrage, pas une
# ignorance. Le `== ""` d'une note ABSENTE serait vert : la ligne exige donc
# d'abord que les DEUX autres notes existent et disent quelque chose.
check("js_cliplen_une_image_ne_confesse_rien",
      _cl("cl_image").get("note") == ""
      and len(_cl("cl_video_zero").get("note", "")) > 40
      and len(_cl("cl_video_21").get("note", "")) > 20,
      f'image={_cl("cl_image").get("note")!r} '
      f'repli={len(_cl("cl_video_zero").get("note", ""))} '
      f'source={len(_cl("cl_video_21").get("note", ""))}')

# ── P11 : faut-il aller demander la duree ? ───────────────────────────────
for _lbl, _k, _att in (
        ("jamais_pour_une_image", "nd_image", False),
        ("jamais_pour_une_image_meme_datee", "nd_image_avec_duree", False),
        ("jamais_quand_on_la_connait", "nd_video_connue", False),
        ("oui_quand_elle_est_nulle", "nd_video_zero", True),
        ("oui_quand_elle_est_absente", "nd_video_absente", True),
        ("oui_quand_elle_est_illisible", "nd_video_texte", True),
        ("oui_quand_elle_est_infinie", "nd_video_infinie", True),
        ("non_quand_elle_est_negative_le_verrou_de_recursion",
         "nd_video_negative", False),
        ("oui_pour_un_son_sans_duree", "nd_audio_zero", True)):
    check("js_needdur_" + _lbl, d.get(_k) is _att, repr(d.get(_k)))

# ── P11 : la mesure elle-meme (askDur), jouee sous node ───────────────────
# CE N'EST PAS UNE DETTE DE NAVIGATEUR : `fetch` et `setTimeout` sont
# INJECTES, donc tout le chemin reseau se joue ici. `done` est appelee UNE
# SEULE FOIS, toujours, et la sortie prise est NOMMEE.
def _ad(k):
    v = d.get(k)
    return v if isinstance(v, list) and len(v) == 2 else ["ABSENT:%r" % (v,),
                                                          "ABSENT"]


for _lbl, _k, _att in (
        ("la_mesure_revient_telle_quelle", "ad_mesure", [21.233, "mesure"]),
        ("une_duree_nulle_veut_dire_inconnue", "ad_mesure_inconnue",
         [0, "mesure"]),
        ("un_refus_http_ne_ment_pas", "ad_http_refuse", [0, "refus"]),
        ("un_corps_illisible_ne_ment_pas", "ad_json_illisible", [0, "refus"]),
        ("un_reseau_qui_leve_ne_tue_rien", "ad_reseau_leve", [0, "erreur"]),
        ("une_promesse_rejetee_ne_tue_rien", "ad_promesse_rejetee",
         [0, "erreur"]),
        ("sans_fetch_la_sortie_est_nommee", "ad_sans_reseau",
         [0, "sans-reseau"]),
        ("le_delai_gagne_la_course", "ad_delai_gagne", [0, "delai"]),
        ("un_src_illisible_sort_nomme", "ad_src_illisible",
         [0, "src-illisible"])):
    check("js_askdur_" + _lbl, _ad(_k) == _att, repr(_ad(_k)))
# LES TROIS LIGNES CI-DESSOUS SONT DES COMPTES, donc des negations deguisees :
# « une seule reponse », « zero appel ». Chacune serait VRAIE PAR CONSTRUCTION
# sur un `askDur` qui ne ferait rien du tout. Le conjoint est a chaque fois la
# sortie ATTENDUE : le compte n'est lu que si la fonction a bien repondu ce
# qu'on lui demandait. MESURE : sans ces conjoints, aucune des vingt-sept
# mutations jouees ne les rougissait — trois lignes vertes qui ne mesuraient
# rien (faute n°2).
check("js_askdur_une_seule_reponse_sur_le_chemin_normal",
      _ad("ad_mesure") == [21.233, "mesure"]
      and d.get("ad_une_seule_reponse") == 1,
      f'{_ad("ad_mesure")!r} n={d.get("ad_une_seule_reponse")!r}')
# LE VERROU DE LA COURSE. `ad_delai_une_seule_reponse == 1` serait vert sur un
# `askDur` qui n'appellerait JAMAIS le reseau : le compteur d'appels est le
# conjoint qui l'en empeche — la reponse est bien passee, elle a ete ignoree.
check("js_askdur_la_reponse_tardive_ne_pose_pas_un_second_clip",
      d.get("ad_delai_une_seule_reponse") == 1
      and d.get("ad_delai_la_reponse_est_bien_passee") == 1,
      f'reponses={d.get("ad_delai_une_seule_reponse")} '
      f'appels={d.get("ad_delai_la_reponse_est_bien_passee")}')
check("js_askdur_sans_fetch_aucun_appel_n_est_tente",
      _ad("ad_sans_reseau") == [0, "sans-reseau"]
      and d.get("ad_sans_reseau_zero_appel") == 0,
      f'{_ad("ad_sans_reseau")!r} '
      f'appels={d.get("ad_sans_reseau_zero_appel")!r}')
check("js_askdur_un_src_illisible_n_appelle_rien",
      _ad("ad_src_illisible") == [0, "src-illisible"]
      and d.get("ad_src_illisible_zero_appel") == 0,
      f'{_ad("ad_src_illisible")!r} '
      f'appels={d.get("ad_src_illisible_zero_appel")!r}')
# CETTE LIGNE-CI A UNE MOITIE FAIBLE, ET C'EST DIT PLUTOT QUE CACHE.
# LA MOITIE COMPORTEMENTALE NE MESURE RIEN : le `TypeError` du rappel absent
# est rattrape par le `catch` qui entoure la chaine de promesses, et `askDur`
# ne leve donc PAS, repli ou pas — `ad_sans_done` vaut "ok" des deux cotes.
# LE CHIFFRE, CORRIGE LE 05/09/2026 (faute n°1 — la table de mutations du
# commit P11 disait « M35 -> 0, DECLARE » alors que sa propre prose decrivait
# le conjoint qui la rougit). MESURE, mutation M35 rejouee a l'identique
# (`var fin=typeof o.done==="function"?o.done:function(){};` ->
# `var fin=o.done;` dans frontend/patches/montage.js, chaine rejouee) :
# 503 passed, 1 failed — CETTE ligne, et elle seule. Ce n'est donc pas la
# moitie comportementale qui la sauve, c'est la SECONDE : le repli explicite
# exige dans la couche LIVREE. Le chiffre honnete est 1, pas 0.
check("js_askdur_sans_rappel_elle_ne_leve_pas",
      d.get("ad_sans_done") == "ok"
      and src.count('var fin=typeof o.done==="function"?o.done:function(){};')
      == 1,
      f'{d.get("ad_sans_done")!r} repli={src.count("var fin=typeof o.done")}')
# L'URL EST CELLE DE LA ROUTE, et le `src` y voyage en JSON encode. La ligne
# de banc du backend (`test_montage_media.py`, section [7]) mesure l'AUTRE
# bout du meme fil.
check("js_askdur_l_url_est_celle_de_la_route",
      isinstance(d.get("ad_url"), str)
      and d["ad_url"] == "/api/montage/duration?src=" + urllib.parse.quote(
          '{"job_id":"j1"}', safe=""),
      repr(d.get("ad_url")))
check("js_askdur_le_delai_par_defaut_est_celui_de_la_couche",
      d.get("ad_delai_par_defaut") == 1500,
      repr(d.get("ad_delai_par_defaut")))
check("js_askdur_un_delai_illisible_retombe_sur_le_defaut",
      d.get("ad_delai_illisible") == 1500 and d.get("ad_delai_recu") == 250,
      f'illisible={d.get("ad_delai_illisible")} recu={d.get("ad_delai_recu")}')

print("\n[3-bis] LE CABLAGE DE L'ECRAN, EXECUTE — addAsset, nudge, le "
      "glisser, le reglage")
# POURQUOI CETTE SECTION EXISTE, ET CE QU'ELLE A COUTE DE NE PAS EXISTER.
# Le CŒUR pur (fitDur, clipLen, needDur, askDur, durCtl) est couvert a fond :
# quarante mutations, tout rougit. Le FIL entre ce cœur et l'ecran ne l'etait
# PAS — `addAsset`, `nudge`, `up()` et l'`onSet` du transport ne sont
# executes par aucun banc. MESURE le 05/09/2026, NEUF mutations qui REMETTENT
# LE BUG RAPPORTE PAR L'UTILISATEUR, chacune avec la chaine de patchs
# rejouee : les neuf laissaient le banc a 504 passed, 0 failed.
#
#   patch_bundle_montage.py:1156  en=Math.min(d,st+dzCl.len)   le rognage de fin
#   :1142  st ramene sous d-2                                  le rognage du depart
#   :1163  if(dzGrew) -> if(!1)                                 la note ment
#   :1157  dzGrew=0                                            idem
#   :1164  {dur:dzGrew} -> {dur:d}                             la meme duree reecrite
#   :1201  if(dzNd>d) -> if(!1)                                le clavier n'etend plus
#   :1278  if(dzUd>durRef.current) -> if(!1)                   le glisser n'etend plus
#   :1315  onSet qui n'ecrit rien                              le reglage est mort
#   :1152  if(!1&&DzTracks.needDur(…))                         tout entre a 6 s
#
# POURQUOI LE TEXTE NE POUVAIT PAS LES VOIR, deux formes nommees :
#   · DEUX RESULTATS COMPARES L'UN A L'AUTRE. `M17*_remplace` compare le
#     bundle a `P.R_M17*` — or dans ce depot le bundle EST ENGENDRE par le
#     patcher. Muter le patcher deplace les DEUX cotes ensemble : la paire ne
#     peut pas rougir sur un changement reel.
#   · SOUS-CHAINE. `P10_M17{a,b,f,g}_ecrit_bien_la_duree` n'est que
#     `"Object.assign({},p,{dur:" in _r` — le texte, jamais la GARDE posee
#     devant. Et `P10_le_rognage_a_disparu_*` compte des LITTERAUX
#     (`"Math.min(d,st+defaultLen"`) : un rognage reecrit contre `dzCl.len`,
#     l'orthographe ACTUELLE du code, ne les touche pas.
#
# CE QUE CETTE SECTION FAIT A LA PLACE : elle EXTRAIT DU BUNDLE LIVRE les
# quatre morceaux de cablage, mot pour mot, et les JOUE sous node avec les
# refs et les setters de l'ecran bouchonnes. Rien n'est recopie — les blocs
# sont des tranches de `s`, et la ligne `cablage_extrait_du_bundle_livre`
# rougit SEULE le jour ou l'un d'eux devient introuvable (rougir, pas mourir :
# les blocs manquants retombent sur du vide et le shim ne partira pas).
_sn = s.replace("\r\n", "\n")
_cabManque = []


def _bloc(nom, debut, fin):
    """La tranche du bundle de `debut` (INCLUS) a `fin` (EXCLU).

    LES DEUX BORNES SONT DES SIGNATURES DE FONCTION, JAMAIS DES BOUTS DE
    PHRASE, et c'est une correction MESUREE : avec une borne de fin prise
    DANS le corps (`return DzTracks.clipLen(kind,srcDur,{image:4,…});`), la
    mutation M19 — qui reecrit PRECISEMENT cette ligne — perdait
    l'extraction et emportait les dix-neuf lignes de cablage d'un coup, en
    accusant l'extraction au lieu du comportement (502/21). Avec des bornes
    de signature, M19 laisse l'extraction intacte et ne rougit que la ou elle
    mord. Introuvable : chaine VIDE + un nom dans `_cabManque`, jamais une
    exception — rougir, pas mourir."""
    i = _sn.find(debut)
    j = _sn.find(fin, i + len(debut)) if i >= 0 else -1
    if i < 0 or j < 0:
        _cabManque.append(nom)
        return ""
    return _sn[i:j]


def _ligne(nom, txt):
    """Une declaration d'une seule piece, exigee UNE fois dans le bundle."""
    if _sn.count(txt) != 1:
        _cabManque.append("%s(%d)" % (nom, _sn.count(txt)))
        return ""
    return txt


# LES FONCTIONS DU BUNDLE QUE LE CABLAGE APPELLE — extraites, jamais
# recopiees : `svmShort` (l'instant dit dans la note de l'ajout), `svmSpeedOf`
# (le rognage gauche), `trackKind` (le refus de genre du remplacement) et
# `svmKbSelClip` (le clip que le clavier decale). Une copie divergerait au
# premier changement du bundle, exactement comme svmRuler/svmPad2.
_SHORT = _ligne("svmShort", 'function svmShort(s){var d=Math.round(s*10),'
                'm=Math.floor(d/600),r2=d%600;return svmPad2(m)+":"+'
                'svmPad2(Math.floor(r2/10))+"."+(r2%10)}')
_SPEED = _ligne("svmSpeedOf", 'function svmSpeedOf(c){return c&&typeof '
                'c.speed==="number"&&c.speed>0?c.speed:1}')
_KIND = _ligne("trackKind", 'function trackKind(trId){var k=String(trId||"")'
               '.charAt(0);\n    return k==="a"?"audio":k==="s"?"subs":'
               '"video"}')
_KBSEL = _ligne("svmKbSelClip", 'function svmKbSelClip(){var id=selRef.current;'
                '\n    return clipsRef.current.find(function(k){'
                'return k.id===id})||null}')
# LES TROIS TRANCHES DE CABLAGE, prises entre deux VOISINS du bundle.
# `defaultLen` est COLLEE a `addAsset` — c'est le maillon que M18a a reecrit,
# et son unique appelant ; `svmEdgeAt` est collee a `clipDown` et n'existe
# que pour elle, si bien qu'une seule tranche porte le geste entier
# (pointerdown, mv, up). Les commentaires qui trainent en queue de tranche
# sont du COMMENTAIRE : ils ne coutent rien sous node.
_ADD = _bloc("defaultLen+addAsset", "function defaultLen(kind,srcDur){",
             "function sfxInsert(item,opts){")
_NUDGE = _bloc("nudge", "nudge:function(fr){", "gain:function(dd){")
_CLIPDOWN = _bloc("svmEdgeAt+clipDown", "function svmEdgeAt(clientX,cRect){",
                  "function svmMixSet(name,db){")
# L'`onSet` DU TRANSPORT est une EXPRESSION, pas une declaration : on prend
# l'appel entier `DzTracks.durCtl({…})` et on l'enveloppe dans une fonction
# dont les parametres portent EXACTEMENT les noms libres qu'il lit. La
# virgule de queue est retiree — c'est celle de la liste d'enfants du JSX.
_DURCTL = _bloc("durCtl", "DzTracks.durCtl({dur:dur,",
                "/* rappels permanents").rstrip().rstrip(",")
check("cablage_extrait_du_bundle_livre", _cabManque == [],
      f"introuvables dans le bundle : {_cabManque}")
# CE QUE CE HARNAIS N'AFFIRME PAS, ecrit plutot que sous-entendu.
#   · IL NE JOUE PAS REACT. `setProj` prend ici l'etat courant et l'applique
#     SUR PLACE ; le vrai composant met la mise a jour en file et re-rend. Ce
#     que ces lignes mesurent est donc CE QUI EST ECRIT et DANS QUEL ORDRE,
#     jamais le rendu ni le regroupement des `setState`. Le journal `J.proj`
#     est la liste des ECRITURES, pas des rendus.
#   · `askDur` EST BOUCHONNEE sur le chemin de la decouverte, et c'est le
#     SEUL bouchon pose sur la couche : sa mecanique interne (le delai, la
#     course, les six sorties nommees) est jouee a fond par la section [3]
#     avec un `fetch` factice. Ce qui est mesure ici est le FIL — la garde
#     qui decide, l'argument transmis, le rappel qui repose le clip.
#   · LE DOM EST UN STUB. `EL` rend un rectangle, une capture de pointeur qui
#     ne fait rien et deux ecouteurs. Rien ici ne mesure la mise en page CSS
#     ni ce que le clip a l'air de faire PENDANT le geste — le depassement
#     visuel reste une dette d'ecran, declaree et non mesuree.
#   · LA COUCHE EST CHARGEE DEPUIS LE FICHIER (`src`), comme en section [3],
#     et non decoupee du bundle. C'est licite parce que
#     `bloc_EST_la_couche_octet_pour_octet` l'exige deja : le jour ou les deux
#     divergent, CETTE ligne-la rougit. Le CABLAGE, lui, ne vient QUE du
#     bundle — il n'existe nulle part ailleurs.

_ENV = r"""
/* ══ L'ECRAN, BOUCHONNE ════════════════════════════════════════════════════
   Les refs et les setters du composant Montage, remplaces par des objets qui
   ENREGISTRENT. Aucune ligne du code mesure n'est recopiee ici : addAsset,
   nudge, svmEdgeAt+clipDown et l'onSet du transport sont les CHAINES EXACTES
   du bundle livre, injectees par le banc. */
function ECRAN(o){
  o=o||{};
  var J={proj:[],clips:[],sel:[],dirty:0,notes:[],pick:[],hist:0,snapT:[],
         arm:[],attente:[]};
  var proj={dur:Number(o.dur)||16,demo:!1,mixDb:{}};
  var durRef={current:proj.dur};
  var clipsRef={current:(o.clips||[]).slice()};
  var phRef={current:Number(o.ph)||0};
  var mixRef={current:{}};
  var selRef={current:o.sel||null};
  var ovSeq={current:0};
  var nudgeHistAt={current:0};
  var ovKeysOffRef={current:!1};
  var dzReadyRef={current:o.pasPrete?!1:!0};
  var dzTracksRef={current:o.pistes||null};
  var trackStRef={current:o.verrous||{}};
  var dzmReplaceRef={current:o.remplace||null};
  var ripple=!!o.ripple,snap=!!o.snap;
  function setProj(fn){proj=fn(proj);durRef.current=proj.dur;
    J.proj.push(proj.dur)}
  function setClips(cs){clipsRef.current=cs;J.clips.push(cs.length)}
  function setSelId(id){selRef.current=id;J.sel.push(id)}
  function setDirty(v){J.dirty++}
  function setOvPick(v){J.pick.push(v)}
  function setSnapT(v){J.snapT.push(v)}
  function setDzmArm(v){J.arm.push(v)}
  function fireNote(t){J.notes.push(String(t))}
  function pushHistory(h){J.hist++}
  function dzAddWhenReady(a,b,c,e,f,g,h){J.attente.push([b,c,e,f,g])}
  function svmKeyLabel(k){return "["+k+"]"}
  __KBSEL__
  __ADD__
  var KB={__NUDGE__};
  __CLIPDOWN__
  function DURCTL(dur,tickStep,clips){return __DURCTL__}
  return {addAsset:addAsset,nudge:KB.nudge,clipDown:clipDown,durCtl:DURCTL,
    J:J,etat:function(){return {dur:proj.dur,clips:clipsRef.current,
      sel:selRef.current}}}}
/* Un element de DOM juste assez reel pour un glisser : un rectangle, une
   capture de pointeur qui ne fait rien, et les deux ecouteurs qu'`up()` doit
   pouvoir retirer — on les rappelle par `_h`. */
function EL(rect){var h={};return {
  getBoundingClientRect:function(){return rect},
  setPointerCapture:function(){},
  addEventListener:function(n,f){h[n]=f},
  removeEventListener:function(n,f){delete h[n]},
  _h:h}}
function EV(x,tgt){return {clientX:x,pointerId:1,currentTarget:tgt,
  stopPropagation:function(){}}}
function RECT(l,w){return {left:l,right:l+w,width:w,top:0,bottom:40,
  height:40}}
function BORNES(cs){return cs.map(function(c){return [c.start,c.end]})}
"""

_PROBE = r"""
var out={};
/* `askDur` EST BOUCHONNEE POUR TOUTE LA SONDE, et pas seulement pour la
   section « decouverte » : c'est le SEUL bouchon pose sur la couche, et il
   est pose ICI, avant le premier appel.

   POURQUOI SI TOT — MESURE, et cherement. Avec le bouchon pose seulement
   devant E3, la mutation M11 (`needDur` rend TOUJOURS vrai) faisait appeler
   la VRAIE `askDur` depuis E1 : node lui prete son `fetch` global (URL
   relative -> rejet) ET son `setTimeout`, si bien qu'au bout de 1,5 s la
   sortie « delai » rappelait `addAsset` avec -1, que `needDur` disait encore
   « demande », et ainsi de suite — UNE BOUCLE INFINIE de 1,5 s par tour. Le
   banc ne rougissait pas : il NE FINISSAIT PAS, ce qui est pire que mourir.
   Le bouchon ne rend jamais la main de lui-meme : aucune recursion possible,
   quoi que fasse la garde. La mecanique interne de `askDur` (le delai, la
   course, les six sorties nommees) reste jouee a fond par la section [3]
   avec un `fetch` factice ; ce qui est mesure ICI est le FIL — la garde qui
   decide, l'argument transmis, le rappel qui repose le clip. */
var vraiAsk=window.DzTracks.askDur,askVus=[];
window.DzTracks.askDur=function(sr,op){askVus.push([sr,op])};
/* ── LE CAS DE L'UTILISATEUR, JOUE PAR L'ECRAN ───────────────────────────── */
var E1=ECRAN({dur:16});
E1.addAsset({job_id:7},"sentry_bot.mp4","video",21.233,"v1",0);
out.add_bornes=BORNES(E1.etat().clips);
out.add_dur=E1.etat().dur;
out.add_proj=E1.J.proj;
out.add_note=E1.J.notes[0]||"";
out.add_hist=E1.J.hist;
out.add_sel=E1.J.sel;
/* UNE DUREE CONNUE NE FAIT RIEN DEMANDER — negation, dont le conjoint est le
   clip effectivement pose a sa longueur. */
out.add_ask=askVus.length;
/* ── LE POINT DE DEPART N'EST PLUS RAMENE EN ARRIERE ─────────────────────── */
var E2=ECRAN({dur:16,ph:15.5});
E2.addAsset({job_id:8},"court.mp4","video",6,"v1",null);
out.st_bornes=BORNES(E2.etat().clips);
out.st_dur=E2.etat().dur;
/* ── LA DECOUVERTE : RIEN N'EST ECRIT AVANT LA MESURE ────────────────────── */
askVus.length=0;
var E3=ECRAN({dur:16});
E3.addAsset({job_id:9},"Memecoin.mp4","video",0,"v1",3);
out.ask_appels=askVus.length;
out.ask_src=askVus[0]?askVus[0][0]:null;
out.ask_avant_clips=E3.J.clips.length;
out.ask_avant_hist=E3.J.hist;
out.ask_avant_notes=E3.J.notes.length;
if(askVus[0])askVus[0][1].done(21.233);
out.ask_bornes=BORNES(E3.etat().clips);
out.ask_dur=E3.etat().dur;
out.ask_relance=askVus.length;
/* MESURE ECHOUEE : le verrou de recursion (un nombre NEGATIF), et le repli
   DIT. `ask_echec_relance` reste a 1 : la seconde passe ne redemande pas. */
askVus.length=0;
var E4=ECRAN({dur:16});
E4.addAsset({job_id:9},"Memecoin.mp4","video",0,"v1",3);
if(askVus[0])askVus[0][1].done(0);
out.ask_echec_bornes=BORNES(E4.etat().clips);
out.ask_echec_relance=askVus.length;
out.ask_echec_note=E4.J.notes[0]||"";
window.DzTracks.askDur=vraiAsk;
out.ask_rendue=(window.DzTracks.askDur===vraiAsk);
/* ── LE DECALAGE CLAVIER ─────────────────────────────────────────────────── */
var E5=ECRAN({dur:16,sel:"k",
  clips:[{tr:"v1",id:"k",label:"plan",start:10,end:16,src:{job_id:1}}]});
E5.nudge(30);
out.nd_bornes=BORNES(E5.etat().clips);
out.nd_dur=E5.etat().dur;
out.nd_proj=E5.J.proj;
out.nd_note=E5.J.notes[0]||"";
/* UN PAS QUI NE SORT PAS DU CHAMP NE DIT RIEN — et le clip a bien bouge :
   c'est le conjoint qui empeche cette negation d'etre vraie par
   construction sur un `nudge` qui ne ferait rien du tout. */
var E6=ECRAN({dur:16,sel:"k",
  clips:[{tr:"v1",id:"k",label:"plan",start:2,end:8,src:{job_id:1}}]});
E6.nudge(30);
out.nd2_bornes=BORNES(E6.etat().clips);
out.nd2_dur=E6.etat().dur;
out.nd2_notes=E6.J.notes.length;
out.nd2_proj=E6.J.proj.length;
/* ── LE GLISSER, RELACHE ─────────────────────────────────────────────────── */
/* pointerdown sur la bande, un pointermove, un pointerup : le geste ENTIER,
   par les ecouteurs que `clipDown` a poses elle-meme. */
function GLISSE(dur,clip,x0,x1){
  var E=ECRAN({dur:dur,clips:[clip]});
  var pxS=800/dur;
  var lane=EL(RECT(0,800));
  var band=EL(RECT(clip.start*pxS,(clip.end-clip.start)*pxS));
  E.clipDown(EV(x0,band),clip,lane);
  band._h.pointermove(EV(x1,band));
  band._h.pointerup(EV(x1,band));
  return {bornes:BORNES(E.etat().clips),dur:E.etat().dur,proj:E.J.proj,
    notes:E.J.notes,hist:E.J.hist,ecouteurs:Object.keys(band._h)}}
var CLIP={tr:"v1",id:"g",label:"plan",start:2,end:8,src:{job_id:1}};
var G1=GLISSE(16,CLIP,250,850);
out.up_bornes=G1.bornes;out.up_dur=G1.dur;out.up_proj=G1.proj;
out.up_note=G1.notes[0]||"";out.up_hist=G1.hist;
out.up_ecouteurs=G1.ecouteurs;
var G2=GLISSE(16,CLIP,250,300);
out.up2_bornes=G2.bornes;out.up2_dur=G2.dur;out.up2_notes=G2.notes.length;
out.up2_proj=G2.proj.length;
/* LE BORD DROIT, tire au-dela de la fin du projet : plus de plafond. */
var G3=GLISSE(16,CLIP,395,850);
out.br_bornes=G3.bornes;out.br_dur=G3.dur;out.br_note=G3.notes[0]||"";
/* ── LE REGLAGE EXPLICITE DE LA DUREE, DANS LE TRANSPORT ─────────────────── */
function BTN(ct,k){var ks=(ct&&ct.p&&ct.p.children)||[];
  for(var i=0;i<ks.length;i++)if(ks[i]&&ks[i].k===k)return ks[i];return null}
var E7=ECRAN({dur:16});
var CT=E7.durCtl(16,2,[{end:8}]);
out.ct_classe=(CT&&CT.p&&CT.p.className)||null;
out.ct_boutons=((CT&&CT.p&&CT.p.children)||[]).map(function(k){
  return k&&k.k});
var bp=BTN(CT,"p");if(bp&&bp.p.onClick)bp.p.onClick();
out.ct_plus=E7.J.proj.slice();
out.ct_dirty=E7.J.dirty;
out.ct_note=E7.J.notes[0]||"";
var E8=ECRAN({dur:16});
var bm=BTN(E8.durCtl(16,2,[{end:8}]),"m");if(bm&&bm.p.onClick)bm.p.onClick();
out.ct_moins=E8.J.proj.slice();
var E9=ECRAN({dur:16});
var bf=BTN(E9.durCtl(16,2,[{end:8}]),"f");if(bf&&bf.p.onClick)bf.p.onClick();
out.ct_ajuste=E9.J.proj.slice();
console.log(JSON.stringify(out));
"""

_env = (_ENV.replace("__KBSEL__", _KBSEL)
        .replace("__ADD__", _ADD).replace("__NUDGE__", _NUDGE)
        .replace("__CLIPDOWN__", _CLIPDOWN).replace("__DURCTL__", _DURCTL))
shim2 = pathlib.Path(TMP) / "shim2.js"
shim2.write_text('"use strict";\n' + "var window={};var SVM_TRACK_BUS={};\n"
                 + JSX + SVM_SRC.replace("\r\n", "\n") + "\n"
                 + RULER_SRC + _SHORT + "\n" + _SPEED + "\n" + _KIND + "\n"
                 + src + "\n" + _env + _PROBE, encoding="utf-8")
# LE DELAI EST UNE GARDE, PAS UN CONFORT, et il est MESURE : sans lui, la
# mutation M11 (`needDur` rend toujours vrai) faisait tourner ce shim SANS
# FIN — un banc qui ne finit pas ne rougit jamais. `subprocess.TimeoutExpired`
# est une Exception : `NODE()` la rattrape, tue l'enfant et rend le
# sous-processus-temoin, si bien qu'une boucle infinie devient une ligne
# ROUGE portant son temoin. Cent quatre-vingts secondes contre ~0,4 s
# mesurees : le chemin normal ne le rencontre jamais.
r = NODE(["node", str(shim2)], timeout=180)
if r.returncode != 0:
    check("js_cablage_shim_execute", False, (r.stderr or "")[-500:])
    w = {}
else:
    check("js_cablage_shim_execute", True)
    _l2 = r.stdout.strip().splitlines()
    _d2 = _l2[-1] if _l2 else ""
    try:
        w = json.loads(_d2) if _d2 else None
        _mal2 = "" if isinstance(w, dict) and w else "sortie sans objet JSON"
    except Exception as _e:
        w, _mal2 = None, "%s: %s" % (type(_e).__name__, _e)
    if not isinstance(w, dict):
        w = {}
    check("js_cablage_rend_un_objet_json", _mal2 == "",
          f"{_mal2} — {len(_l2)} ligne(s), dernière={_d2[:120]!r}")

# ── L'AJOUT : LE DEFAUT RAPPORTE, RETOURNE ────────────────────────────────
# « j'ai voulu ajouter trois videos depuis la bibliotheque, or la timeline est
# fixe ». Une source de 21,233 s posee a 0 dans un projet de 16 s : le clip
# entre ENTIER, et c'est la timeline qui grandit (22 s, l'arrondi au plafond
# de `fitDur`, pour que « 0:22 total » ne mente pas sur la fin du dernier
# clip). MUTATION :1156 (`en=Math.min(d,st+dzCl.len)`) -> le clip retombe a
# 0..16 et cette ligne rougit.
# `add_ask == 0` est le second membre : une duree CONNUE ne fait rien
# demander. C'est une negation, et son conjoint est le clip pose a sa
# longueur juste a cote — les deux ne peuvent pas etre vrais a vide.
check("js_add_le_clip_entre_a_la_longueur_de_sa_source",
      w.get("add_bornes") == [[0, 21.233]] and w.get("add_ask") == 0,
      f'{w.get("add_bornes")} mesures={w.get("add_ask")}')
# MUTATIONS :1163 (`if(!1)`), :1157 (`dzGrew=0`) et :1164 (`{dur:d}`) : les
# trois passent le texte, les trois rougissent ICI. `add_proj` est le journal
# des ecritures de `setProj` — un seul appel, avec la duree grandie.
check("js_add_la_timeline_s_allonge_pour_l_accueillir",
      w.get("add_dur") == 22 and w.get("add_proj") == [22],
      f'dur={w.get("add_dur")} ecritures={w.get("add_proj")}')
# L'AGRANDISSEMENT EST DIT, ET CHIFFRE DES DEUX BOUTS. La note porte AUSSI la
# longueur de la source (`dzCl.note`) et la reserve d'historique : c'est la
# phrase entiere que l'utilisateur lit.
check("js_add_l_allongement_est_DIT_et_chiffre",
      "La timeline a été allongée de 0:16 à 0:22" in w.get("add_note", "")
      and "la longueur ENTIÈRE de la source" in w.get("add_note", "")
      and "NE raccourcit PAS la timeline" in w.get("add_note", ""),
      repr(w.get("add_note"))[:220])
# UNE SEULE ENTREE D'HISTORIQUE, et le clip est SELECTIONNE — le conjoint qui
# empeche ce compte d'etre vrai par construction sur un addAsset muet.
check("js_add_une_seule_entree_d_historique",
      w.get("add_hist") == 1 and len(w.get("add_sel") or []) == 1,
      f'hist={w.get("add_hist")} sel={w.get("add_sel")}')
# MUTATION :1142 : la tete de lecture a 15,5 s dans un projet de 16 s. Le clip
# doit atterrir A 15,5 — `Math.max(0,d-1)` le ramenait a 15, `d-2` a 14.
check("js_add_le_point_de_depart_n_est_plus_ramene_en_arriere",
      w.get("st_bornes") == [[15.5, 21.5]] and w.get("st_dur") == 22,
      f'{w.get("st_bornes")} dur={w.get("st_dur")}')
# ── LA DECOUVERTE (P11) ───────────────────────────────────────────────────
# MUTATION :1152 (`if(!1&&DzTracks.needDur(…))`) : la mesure ne part jamais et
# tout entre a 6 s. Les trois comptes a zero sont des NEGATIONS — leur
# conjoint est l'appel MESURE et le `src` transmis tel quel.
check("js_add_la_mesure_part_AVANT_toute_ecriture",
      w.get("ask_appels") == 1 and w.get("ask_src") == {"job_id": 9}
      and w.get("ask_avant_clips") == 0 and w.get("ask_avant_hist") == 0
      and w.get("ask_avant_notes") == 0,
      f'appels={w.get("ask_appels")} src={w.get("ask_src")} '
      f'clips={w.get("ask_avant_clips")} hist={w.get("ask_avant_hist")} '
      f'notes={w.get("ask_avant_notes")}')
# LE RAPPEL REPART DU MEME POINT : `st` vaut toujours 3 (l'instant du CLIC,
# pas 85 ms plus tard), la longueur est celle mesuree, la timeline suit — et
# `ask_relance` prouve qu'on n'a pas redemande.
check("js_add_le_rappel_repose_le_clip_a_la_mesure",
      w.get("ask_bornes") == [[3, 24.233]] and w.get("ask_dur") == 25
      and w.get("ask_relance") == 1,
      f'{w.get("ask_bornes")} dur={w.get("ask_dur")} '
      f'relances={w.get("ask_relance")}')
# MESURE ECHOUEE : le verrou de recursion tient (UNE demande, pas deux) et le
# repli est DIT — avec l'accord de la branche video.
check("js_add_une_mesure_echouee_ne_reboucle_pas_et_le_DIT",
      w.get("ask_echec_bornes") == [[3, 9]]
      and w.get("ask_echec_relance") == 1
      and "Cette vidéo a été posée à 6 s" in w.get("ask_echec_note", "")
      and w.get("ask_rendue") is True,
      f'{w.get("ask_echec_bornes")} relances={w.get("ask_echec_relance")} '
      f'{repr(w.get("ask_echec_note"))[:160]}')
# ── LE DECALAGE CLAVIER ───────────────────────────────────────────────────
# MUTATION :1201 (`if(!1)`) : un clip de 10 a 16 pousse d'une seconde finit a
# 17 dans un projet de 16 — la timeline doit suivre.
check("js_nudge_le_decalage_etend_la_timeline",
      w.get("nd_bornes") == [[11, 17]] and w.get("nd_dur") == 17
      and w.get("nd_proj") == [17],
      f'{w.get("nd_bornes")} dur={w.get("nd_dur")} '
      f'ecritures={w.get("nd_proj")}')
check("js_nudge_l_allongement_est_DIT_et_nomme_le_clip",
      w.get("nd_note", "").startswith("Timeline allongée à 0:17")
      and "« plan »" in w.get("nd_note", "")
      and "NE raccourcit PAS la timeline" in w.get("nd_note", ""),
      repr(w.get("nd_note"))[:200])
# LA NOTE NE PARLE QUE QUAND LA DUREE CHANGE VRAIMENT : une touche maintenue
# vaut trente pas par seconde. Le conjoint est le deplacement REEL du clip.
check("js_nudge_un_pas_qui_ne_sort_pas_du_champ_ne_dit_rien",
      w.get("nd2_bornes") == [[3, 9]] and w.get("nd2_dur") == 16
      and w.get("nd2_notes") == 0 and w.get("nd2_proj") == 0,
      f'{w.get("nd2_bornes")} dur={w.get("nd2_dur")} '
      f'notes={w.get("nd2_notes")} ecritures={w.get("nd2_proj")}')
# ── LE GLISSER, ET SON RELACHEMENT ────────────────────────────────────────
# MUTATION :1278 (`if(!1)`) : un clip de 2 a 8 tire de douze secondes finit a
# 20 dans un projet de 16. `up_ecouteurs` prouve que le geste s'est bien
# DEFAIT — les deux ecouteurs retires, pas un glisser reste accroche.
check("js_glisser_le_relachement_etend_la_timeline",
      w.get("up_bornes") == [[14, 20]] and w.get("up_dur") == 20
      and w.get("up_proj") == [20] and w.get("up_ecouteurs") == [],
      f'{w.get("up_bornes")} dur={w.get("up_dur")} '
      f'ecritures={w.get("up_proj")} ecouteurs={w.get("up_ecouteurs")}')
check("js_glisser_l_allongement_est_DIT_avec_les_deux_durees",
      "Timeline allongée de 0:16 à 0:20" in w.get("up_note", "")
      and "rien n'a été rogné" in w.get("up_note", "")
      and w.get("up_hist") == 1,
      f'{repr(w.get("up_note"))[:200]} hist={w.get("up_hist")}')
# UN GLISSER QUI RESTE DANS LE CHAMP N'ALLONGE RIEN ET NE DIT RIEN — conjoint :
# le clip a bel et bien bouge (2..8 -> 3..9).
check("js_glisser_qui_reste_dans_le_champ_ne_dit_rien",
      w.get("up2_bornes") == [[3, 9]] and w.get("up2_dur") == 16
      and w.get("up2_notes") == 0 and w.get("up2_proj") == 0,
      f'{w.get("up2_bornes")} dur={w.get("up2_dur")} '
      f'notes={w.get("up2_notes")} ecritures={w.get("up2_proj")}')
# LE BORD DROIT (M17d) : le rognage va ou on le tire, la timeline le rattrape
# au relachement.
check("js_glisser_le_bord_droit_n_est_plus_plafonne",
      w.get("br_bornes") == [[2, 17.1]] and w.get("br_dur") == 18
      and "Timeline allongée de 0:16 à 0:18" in w.get("br_note", ""),
      f'{w.get("br_bornes")} dur={w.get("br_dur")} '
      f'{repr(w.get("br_note"))[:120]}')
# ── LE REGLAGE EXPLICITE, DANS LE TRANSPORT ───────────────────────────────
# MUTATION :1315 (l'`onSet` qui n'ecrit rien) : les trois boutons du controle
# sont CLIQUES ici, et c'est leur ecriture qu'on lit. « ajuster » paie la
# dette de P3 (ramener la fin sur le dernier clip : 16 -> 8).
check("js_transport_le_reglage_ecrit_la_duree",
      w.get("ct_plus") == [18] and w.get("ct_moins") == [14]
      and w.get("ct_ajuste") == [8] and w.get("ct_dirty") == 1,
      f'+={w.get("ct_plus")} -={w.get("ct_moins")} '
      f'ajuste={w.get("ct_ajuste")} dirty={w.get("ct_dirty")}')
check("js_transport_le_controle_porte_ses_quatre_boutons",
      w.get("ct_classe") == "dzm-durctl"
      and w.get("ct_boutons") == ["m", "v", "p", "f"]
      and "(+2 s)" in w.get("ct_note", "")
      and "ne rend pas la durée du projet" in w.get("ct_note", ""),
      f'{w.get("ct_classe")} {w.get("ct_boutons")} '
      f'{repr(w.get("ct_note"))[:140]}')

# ══════════════════════════════════════════════════════════════════════════
# [6] LA BARRE D'OUTILS DEPORTABLE — etapes 1, 2 et 3 du §9 du handoff
# « Barre Outils Flottante » (Design d'icônes applicatives/
# design_handoff_barre_outils/design.md). RIEN DE CE LOT N'EST MONTE A
# L'ECRAN : ces lignes mesurent des TOKENS, dix TRACES et un COMPOSANT.
# Aucune ne pretend qu'une barre existe — elle n'existe pas encore.
# ══════════════════════════════════════════════════════════════════════════
print("\n[6] la barre d'outils deportable — tokens, dix traces, bouton")

HANDOFF = (ROOT / "Design d'icônes applicatives"
           / "design_handoff_barre_outils" / "design.md")
TOK_SRC = ROOT / "frontend" / "shared" / "deepotus.tokens.css"
TOK_DEP = ROOT / "frontend" / "dist" / "shared" / "deepotus.tokens.css"
THEME2 = ROOT / "frontend" / "dist" / "theme-v2.css"


def _lire(p):
    """Contenu d'un fichier, ou "" — GARDEE. Faute n°6 : toute lecture de
    fichier avant un `check` doit l'etre, et le temoin numerote fait rougir
    `aucun_appel_n_a_plante` en plus de la ligne qui lira le vide."""
    try:
        return p.read_text(encoding="utf-8")
    except BaseException as e:
        print(f"  ----  lecture impossible de {p.name} : {temoin(e)}")
        return ""


# ── les dix traces, LUS DANS LE HANDOFF ────────────────────────────────────
# Ni la couche ni ce banc ne recopient un trace : les deux le lisent ici.
_TB_CLE = {"piste vidéo": "piste-video", "piste audio": "piste-audio",
           "bibliothèque": "bibliotheque", "couleur": "couleur",
           "rebond": "rebond", "glow": "glow", "emoji": "emoji",
           "texte": "texte", "projets": "projets", "poignée": "poignee"}
_HO = _lire(HANDOFF)
_TB_SPEC = {}
try:
    _sec = _HO[_HO.index("## 3. Les neuf icônes"):
               _HO.index("## 4. Comportement")]
    for _l in _sec.splitlines():
        if not _l.startswith("| **"):
            continue
        _c = [x.strip() for x in _l.strip().strip("|").split("|")]
        _n = re.sub(r"\*|\s*\(.*", "", _c[0]).strip()
        if _n in _TB_CLE and len(_c) > 2 and len(_c[2]) > 2 \
                and _c[2][0] == "`" and _c[2][-1] == "`":
            _TB_SPEC[_TB_CLE[_n]] = _c[2][1:-1]
except BaseException as _e:
    print(f"  ----  §3 du handoff illisible : {temoin(_e)}")
    _TB_SPEC = {}
_TB_ORDRE = list(_TB_SPEC)
check("tb_les_dix_traces_sont_lisibles_dans_le_handoff",
      len(_TB_SPEC) == 10 and all(v.startswith("<") and v.endswith("/>")
                                  for v in _TB_SPEC.values()),
      f"{len(_TB_SPEC)} trace(s) extraits de {HANDOFF.name} : {_TB_ORDRE}")

# LA COUCHE PORTE LE TEXTE DU §3, CLE ET VALEUR, AU CARACTERE PRES. La forme
# exigee est celle que la couche ecrit : deux lignes par icone, apostrophes
# simples. Un trace retape « presque » pareil ne passe pas.
_srcn = src.replace("\r\n", "\n")
_APO = "'"


def _paire(k, v):
    return '  "%s":\n    %s%s%s,' % (k, _APO, v, _APO)


check("tb_la_couche_porte_les_dix_traces_du_handoff_au_caractere_pres",
      len(_TB_SPEC) == 10
      and all(_paire(k, v) in _srcn for k, v in _TB_SPEC.items()),
      "traces divergents : "
      + str([k for k, v in _TB_SPEC.items() if _paire(k, v) not in _srcn]))
# ET LE BUNDLE LIVRE LES PORTE AUSSI — `bloc_EST_la_couche_octet_pour_octet`
# l'implique deja ; cette ligne le DIT sur le fichier que le navigateur
# charge, et rougirait seule si le patcher n'avait pas ete rejoue.
check("tb_le_bundle_livre_porte_les_dix_traces",
      len(_TB_SPEC) == 10 and all(nl(v) in s for v in _TB_SPEC.values()),
      "traces absents du bundle : "
      + str([k for k, v in _TB_SPEC.items() if nl(v) not in s]))

# ── L'ALLER-RETOUR, JOUE SOUS NODE : le controle a deux faces ──────────────
check("tb_l_aller_retour_rend_exactement_le_trace_du_handoff",
      len(_TB_SPEC) == 10 and isinstance(d.get("tb_aller_retour"), dict)
      and d["tb_aller_retour"] == _TB_SPEC,
      "ecarts : " + str([k for k in _TB_SPEC
                         if (d.get("tb_aller_retour") or {}).get(k)
                         != _TB_SPEC[k]]))
# UN ALLER-RETOUR EST VRAI SUR DU VIDE des deux cotes : cette ligne exige que
# chaque trace ait rendu SES elements, et le compte vient du handoff.
check("tb_chaque_trace_rend_le_nombre_d_elements_du_handoff",
      len(_TB_SPEC) == 10
      and d.get("tb_elements") == [[k, _TB_SPEC[k].count("<")]
                                   for k in _TB_ORDRE],
      str(d.get("tb_elements")))
check("tb_les_balises_et_les_attributs_sont_ceux_du_dessin",
      d.get("tb_balises") == ["rect", "rect", "path"]
      and d.get("tb_attrs") == {"x": "2.6", "y": "4.2", "width": "18.8",
                                "height": "5.6", "opacity": ".34"},
      f'{d.get("tb_balises")} {d.get("tb_attrs")}')
# camelCase : sans lui React laisserait tomber un `fill-rule` en silence.
check("tb_un_attribut_compose_passe_en_camelCase_pour_React",
      d.get("tb_camel") == {"fillRule": "evenodd", "d": "M0 0z"},
      str(d.get("tb_camel")))
check("tb_un_trace_vide_ou_nul_ne_leve_pas",
      d.get("tb_parse_vide") == [0, 0], str(d.get("tb_parse_vide")))

# ── L'ICONE (§3) ───────────────────────────────────────────────────────────
check("tb_l_icone_est_une_grille_24_rendue_a_18_px_en_currentColor",
      d.get("tb_i_balise") == "svg"
      and d.get("tb_i_props") == ["0 0 24 24", "currentColor", 18, 18,
                                  True, "dzm-tbi", "false"]
      and d.get("tb_px") == [18, 14],
      f'{d.get("tb_i_props")} px={d.get("tb_px")}')
check("tb_l_icone_pose_une_cle_par_element",
      d.get("tb_i_enfants") == ["rect", "rect", "rect", "rect"]
      and d.get("tb_i_cles") == ["t0", "t1", "t2", "t3"],
      f'{d.get("tb_i_enfants")} {d.get("tb_i_cles")}')
check("tb_la_taille_est_reglable_et_une_taille_illisible_retombe_sur_18",
      d.get("tb_i_taille") == 14 and d.get("tb_i_taille_illisible") == 18
      and d.get("tb_i_taille_negative") == 18,
      f'{d.get("tb_i_taille")} {d.get("tb_i_taille_illisible")} '
      f'{d.get("tb_i_taille_negative")}')
# NULL, pas un <svg> vide, qui serait un trou invisible. LA CLE D'ABORD :
# `{}.get(x)` vaut None et rendrait ces deux lignes vertes sur une sonde qui
# n'a pas tourne — meme piege que `js_bouton_null_sans_etalonnage`.
check("tb_une_icone_inconnue_rend_null_plutot_qu_un_svg_vide",
      "tb_i_inconnue" in d and d["tb_i_inconnue"] is None
      and "tb_i_sans_nom" in d and d["tb_i_sans_nom"] is None,
      f'{d.get("tb_i_inconnue")} {d.get("tb_i_sans_nom")}')
check("tb_l_icone_n_ecrit_aucune_couleur",
      d.get("tb_i_sans_couleur") is True, str(d.get("tb_i_sans_couleur")))

# ── LE BOUTON D'ACTION (§2.3) ──────────────────────────────────────────────
check("tb_le_bouton_au_repos_porte_sa_classe_de_groupe_et_ses_deux_enfants",
      d.get("tb_b_balise") == "button" and d.get("tb_b_type") == "button"
      and d.get("tb_b_classe") == "dzm-tbb dzm-g-pistes"
      and d.get("tb_b_grp") == "pistes"
      and d.get("tb_b_enfants") == ["svg", "span"]
      and d.get("tb_b_libelle") == "vidéo"
      and d.get("tb_b_libelle_classe") == "dzm-tbl"
      and d.get("tb_b_desactive") is False,
      f'{d.get("tb_b_classe")} {d.get("tb_b_enfants")} '
      f'{d.get("tb_b_libelle")!r}')
# LE LIBELLE EST LE REPLI DE title ET DE aria-label : c'est ce qui rend le
# mode compact impossible SANS infobulle (§2.3), sans que l'appelant y pense.
check("tb_le_libelle_sert_de_repli_a_l_infobulle_et_a_l_aria_label",
      d.get("tb_b_titre") == "vidéo" and d.get("tb_b_aria") == "vidéo"
      and d.get("tb_b_titre_donne") == ["Insérer un emoji",
                                        "Insérer un emoji à la tête de "
                                        "lecture"],
      f'{d.get("tb_b_titre")!r} {d.get("tb_b_titre_donne")}')
check("tb_les_cinq_groupes_donnent_cinq_classes_de_teinte",
      d.get("tb_groupes") == ["pistes", "biblio", "mot", "ajouts", "projets"]
      and d.get("tb_b_classes") == ["dzm-tbb dzm-g-pistes",
                                    "dzm-tbb dzm-g-biblio",
                                    "dzm-tbb dzm-g-mot",
                                    "dzm-tbb dzm-g-ajouts",
                                    "dzm-tbb dzm-g-projets"],
      f'{d.get("tb_groupes")} {d.get("tb_b_classes")}')
# LE ROUGE N'EST PAS UN GROUPE, et la ligne ne se contente pas de le nier :
# elle exige d'abord que la liste FASSE CINQ.
check("tb_le_rouge_du_destructif_n_est_pas_un_groupe_de_la_barre",
      isinstance(d.get("tb_groupes"), list) and len(d["tb_groupes"]) == 5
      and "cartes" not in d["tb_groupes"] and "rouge" not in d["tb_groupes"],
      str(d.get("tb_groupes")))
check("tb_un_groupe_inconnu_ne_fabrique_pas_de_classe_ni_de_data",
      d.get("tb_b_groupe_inconnu") == "dzm-tbb"
      and d.get("tb_b_groupe_inconnu_data") is True,
      f'{d.get("tb_b_groupe_inconnu")!r} '
      f'{d.get("tb_b_groupe_inconnu_data")}')
check("tb_la_bascule_porte_ses_trois_etats_de_aria_pressed",
      d.get("tb_t_on") == ["dzm-tbb dzm-g-mot dzm-on", "true"]
      and d.get("tb_t_off") == ["dzm-tbb dzm-g-mot", "false"]
      and d.get("tb_t_mix") == ["dzm-tbb dzm-g-mot dzm-mix", "mixed"],
      f'{d.get("tb_t_on")} {d.get("tb_t_off")} {d.get("tb_t_mix")}')
# UNE ACTION SIMPLE N'A PAS D'ETAT : un `active` passe par erreur ne doit ni
# allumer le bouton ni poser un `aria-pressed` qui mentirait.
check("tb_une_action_simple_ignore_active_et_ne_pose_pas_aria_pressed",
      d.get("tb_t_sans_bascule") == ["dzm-tbb dzm-g-pistes", True]
      and d.get("tb_b_pressed_absent") is True,
      f'{d.get("tb_t_sans_bascule")} {d.get("tb_b_pressed_absent")}')
check("tb_le_groupe_a_bouton_unique_a_sa_classe_de_largeur",
      d.get("tb_b_solo") == "dzm-tbb dzm-g-biblio dzm-solo",
      str(d.get("tb_b_solo")))
check("tb_le_clic_agit_et_un_bouton_eteint_refuse_le_sien",
      d.get("tb_b_clic") == 1 and d.get("tb_b_clic_eteint") == 0
      and d.get("tb_b_eteint") == ["dzm-tbb dzm-g-mot", True]
      and d.get("tb_b_clic_sans_action") == "ok",
      f'{d.get("tb_b_clic")} / {d.get("tb_b_clic_eteint")} '
      f'{d.get("tb_b_eteint")} {d.get("tb_b_clic_sans_action")}')
check("tb_le_bouton_n_ecrit_aucune_couleur_ni_nom_de_variable_css",
      d.get("tb_b_sans_couleur") is True, str(d.get("tb_b_sans_couleur")))

# ── PARENTE (§3) : `bibliothèque` EST le glyphe `Library` du rail ──────────
# Le rail de navigation appelle son entree Library par la CLE `folder`, et le
# handoff d'aout a remplace le trace de cette cle. LES DEUX FACES sont
# mesurees : la cle que le rail demande, et le trace que la carte lui rend.
_fi = s.find(nl('folder:r.jsxs("g",{fill:"currentColor",children:['))
_fj = s.find(nl("]})"), _fi) if _fi >= 0 else -1
_FOLD = s[_fi:_fj] if _fi >= 0 and _fj > _fi else ""
_bib = _TB_SPEC.get("bibliotheque", "")
_bib_d = re.findall(r'd="([^"]*)"', _bib)
_bib_o = re.findall(r'opacity="([^"]*)"', _bib)
check("tb_bibliotheque_EST_le_glyphe_Library_du_rail_de_navigation",
      bool(_FOLD) and len(_bib_d) == 2 and len(_bib_o) == 1
      and _FOLD.count('r.jsx("path"') == 2
      and all(nl('d:"%s"' % x) in _FOLD for x in _bib_d)
      and nl('opacity:"%s"' % _bib_o[0]) in _FOLD
      and nl('{id:"library",label:"Library",icon:"folder"') in s,
      f"folder={len(_FOLD)} o, d={len(_bib_d)}, opacite={_bib_o} — "
      f"les deux tracés ont divergé")

# ── ETAPE 1 : LES TOKENS, DANS LES TROIS FEUILLES ─────────────────────────
# LE PIEGE, MESURE AU HANDOFF D'AOUT : la page du bundle NE CHARGE PAS la
# feuille partagee — dist/index.html ne lie que theme-v2.css et les feuilles
# de module. theme-v2 REDEFINIT les valeurs : c'est sa convention de couche.
# Un token pose dans une seule des deux est MORT a l'ecran, sans erreur.
# LA TROISIEME EST LA COPIE DEPLOYEE de la source (§15-bis, « copié
# dist/shared/ ») : elle est servie a /shared/ et les pages de module
# l'importent. Elle doit rester la source, octet pour octet.
_TOKENS = ["--grp-pistes:oklch(.72 .13 200)",
           "--grp-biblio:oklch(.72 .13 255)",
           "--grp-mot:oklch(.72 .13 300)", "--grp-ajouts:oklch(.72 .13 80)",
           "--grp-projets:oklch(.72 .13 145)",
           "--grp-fill:oklch(from var(--grp) l c h / .16)",
           "--grp-line:var(--grp)", "--bar-srf:#13171c", "--bar-brd:#2a323b",
           "--bar-shadow:0 14px 34px rgba(0,0,0,.62)",
           "--dur-bar-open:220ms", "--dur-bar-snap:180ms"]
_T_SRC, _T_DEP, _T2 = _lire(TOK_SRC), _lire(TOK_DEP), _lire(THEME2)
for _nom, _txt in (("source", _T_SRC), ("copie_deployee", _T_DEP),
                   ("theme_v2_du_bundle", _T2)):
    check("tb_les_douze_tokens_sont_dans_la_feuille_" + _nom,
          bool(_txt) and all(_k in _txt for _k in _TOKENS),
          f"{len(_txt)} o — manquants : "
          + str([_k for _k in _TOKENS if _k not in _txt]))
check("tb_la_copie_deployee_est_la_source_octet_pour_octet",
      bool(_T_SRC) and _T_SRC == _T_DEP,
      f"source={len(_T_SRC)} o copie={len(_T_DEP)} o")
# LE ROUGE RESTE DEHORS (§1.2). Negation ACCOMPAGNEE : la ligne exige d'abord
# que les cinq teintes soient la, sinon elle serait vraie d'un fichier vide.
check("tb_aucun_groupe_ne_prend_le_rouge_du_destructif",
      all(_k in _T2 for _k in _TOKENS[:5]) and "--grp-cartes" not in _T2
      and "--grp-rouge" not in _T2
      and "oklch(.72 .13 25)" not in _T2.split("--grp-pistes")[-1],
      "une teinte de groupe a pris le rouge")
# AUCUNE VARIANTE CLAIRE POUR --grp-*, et c'est delibere : --bar-srf est un
# litteral sombre que le theme ne suit pas. Abaisser la clarte a .52 comme
# --cat-* le fait rendrait les cinq teintes illisibles SUR CE FOND.
# Conjoint : le bloc clair des --cat-*, lui, est toujours la.
check("tb_les_teintes_de_groupe_ne_suivent_pas_le_theme_clair",
      "--cat-3d:oklch(.52 .12 255)" in _T2
      and "--grp-pistes:oklch(.52" not in _T2
      and "--grp-mot:oklch(.52" not in _T2,
      "un --grp-* a gagne une variante claire")

# ── ETAPE 1 (suite) : LA PASSE DE CONTRASTE DU §9.8, CALCULEE ──────────────
# PROTOCOLE, NOMME : OKLCH -> OKLab -> LMS -> sRGB lineaire (CSS Color 4,
# matrices inverses de la specification), ecretage a [0,1], composition
# source-over de --grp-fill (alpha .16) SUR --bar-srf dans l'espace sRGB NON
# lineaire — ce que fait un navigateur d'une couche translucide — puis
# luminance relative et rapport WCAG 2.x (L1+.05)/(L2+.05).
# LES ENTREES SONT LUES DANS LA FEUILLE : aucune n'est recopiee ici.
_M2I = ((1.0, 0.3963377773761749, 0.2158037573099136),
        (1.0, -0.1055613458156586, -0.0638541728258133),
        (1.0, -0.0894841775298119, -1.2914855480194092))
_M1I = ((4.0767416621, -3.3077115913, 0.2309699292),
        (-1.2684380046, 2.6097574011, -0.3413193965),
        (-0.0041960863, -0.7034186147, 1.7076147010))


def _oklch(L, C, h):
    import math
    a = (L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))
    lms = [sum(_M2I[i][j] * a[j] for j in range(3)) ** 3 for i in range(3)]
    lin = [sum(_M1I[i][j] * lms[j] for j in range(3)) for i in range(3)]
    return [min(1.0, max(0.0, 12.92 * v if v <= 0.0031308
                         else 1.055 * (v ** (1 / 2.4)) - 0.055)) for v in lin]


def _hexf(t):
    t = t.lstrip("#")
    return [int(t[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _lum(c):
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
         for x in c]
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


# LE PROTOCOLE EST VALIDE CONTRE UNE MESURE ANTERIEURE ET INDEPENDANTE : les
# six chiffres publies le 26/08 (DESIGN.md §15-bis, --cat-ink #14181d sur
# l'aplat de categorie). S'il les refait a 0,005 pres, il n'a pas ete ecrit
# pour rendre le resultat qui arrange le lot d'aujourd'hui.
_CTRL = ((255, 7.18), (300, 6.87), (200, 7.65), (145, 7.55),
         (80, 7.09), (25, 6.80))
check("tb_le_protocole_de_contraste_refait_les_six_chiffres_du_26_08",
      all(abs(_ratio(_hexf("#14181d"), _oklch(.72, .13, _h)) - _v) < .005
          for _h, _v in _CTRL),
      str([round(_ratio(_hexf("#14181d"), _oklch(.72, .13, _h)), 2)
           for _h, _v in _CTRL]))
_m_bar = re.search(r"--bar-srf:\s*(#[0-9a-fA-F]{6})", _T2)
_m_ink = re.search(r"--ink-strong:\s*(#[0-9a-fA-F]{6})", _T2)
_m_alpha = re.search(
    r"--grp-fill:oklch\(from var\(--grp\) l c h / ([\d.]+)\)", _T2)
_HUES = re.findall(r"--grp-(pistes|biblio|mot|ajouts|projets):"
                   r"oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)", _T2)
check("tb_les_entrees_du_calcul_de_contraste_sont_lues_dans_la_feuille",
      len(_HUES) == 5 and _m_bar is not None and _m_ink is not None
      and _m_alpha is not None,
      f"teintes={len(_HUES)} bar={bool(_m_bar)} ink={bool(_m_ink)} "
      f"alpha={bool(_m_alpha)}")
# --txt-hi N'EXISTE PAS dans cette base : le handoff le nomme, DESIGN.md
# §15-bis le fait correspondre a --ink-strong, et c'est --ink-strong que la
# chaine de repli de la regle resout. LES DEUX SONT MESURES — celui du
# handoff (#eef2f6) et celui de l'ecran.
check("tb_txt_hi_du_handoff_est_bien_ink_strong_dans_cette_base",
      "--ink-strong:" in _T2 and "--txt-hi:" not in _T2,
      "--txt-hi existe desormais : la correspondance du §15-bis a change")
_CONTRASTES = []
if len(_HUES) == 5 and _m_bar and _m_ink and _m_alpha:
    _bar = _hexf(_m_bar.group(1))
    _al = float(_m_alpha.group(1))
    for _n, _L, _C, _h in _HUES:
        _t = _oklch(float(_L), float(_C), float(_h))
        _f = [_al * _t[i] + (1 - _al) * _bar[i] for i in range(3)]
        _CONTRASTES.append((_n, _ratio(_hexf("#eef2f6"), _f),
                            _ratio(_hexf(_m_ink.group(1)), _f)))
        print("  ....  contraste %-8s sur --grp-fill : #eef2f6 %5.2f:1 · "
              "%s %5.2f:1" % (_n, _CONTRASTES[-1][1], _m_ink.group(1),
                              _CONTRASTES[-1][2]))
check("tb_les_cinq_teintes_passent_4_5_1_du_9_8_avec_les_deux_encres",
      len(_CONTRASTES) == 5
      and all(a >= 4.5 and b >= 4.5 for _n, a, b in _CONTRASTES),
      str([(n, round(a, 2), round(b, 2)) for n, a, b in _CONTRASTES]))

# ── ETAPE 3 : LA FEUILLE HABILLE LES ETATS DU §2.3 ────────────────────────
_MC = _lire(CSS)
_R_TBB = _regle(_MC, ".dzsvm .dzm-tbb{")
_R_TBL = _regle(_MC, ".dzsvm .dzm-tbl{")
_R_HOV = _regle(_MC, ".dzsvm .dzm-tbb:hover{")
_R_ACT = _regle(_MC, ".dzsvm .dzm-tbb:active{")
_R_ON = _regle(_MC, ".dzsvm .dzm-tbb.dzm-on{")
_R_ONC = _regle(_MC, ".dzsvm .dzm-tbb.dzm-on .dzm-tbl{")
_R_MIX = _regle(_MC, ".dzsvm .dzm-tbb.dzm-mix{")
_R_DIS = _regle(_MC, ".dzsvm .dzm-tbb[disabled]{")
_R_SOL = _regle(_MC, ".dzsvm .dzm-tbb.dzm-solo{")
check("tb_la_geometrie_du_bouton_est_celle_du_2_3",
      _R_TBB is not None and "width:60px" in _R_TBB
      and "padding:7px 0 6px" in _R_TBB
      and "flex-direction:column" in _R_TBB and "gap:6px" in _R_TBB
      and "border:1px solid transparent" in _R_TBB
      and "border-radius:0" in _R_TBB
      and "transition:background .14s ease, border-color .14s ease" in _R_TBB
      and _R_SOL is not None and "width:70px" in _R_SOL,
      f"tbb={_R_TBB!r}")
# LE POINT CENTRAL DU §2.3 : l'icone GARDE la teinte de son groupe au repos.
check("tb_l_icone_garde_la_teinte_de_son_groupe_au_repos",
      _R_TBB is not None and "color:var(--grp," in _R_TBB
      and "background:transparent" in _R_TBB, f"tbb={_R_TBB!r}")
# LE DERIVE EST RECALCULE LA OU --grp EST POSEE, et c'est une MESURE, pas un
# gout : une propriete personnalisee est substituee au calcul de SON element
# puis heritee DEJA RESOLUE. Un --grp-fill declare seulement sur :root y
# resoudrait le --grp de :root, et les neuf boutons auraient le meme fond —
# c'est pour cette raison exacte que le bundle n'emploie jamais --cat-fill.
# Le conjoint : les cinq classes qui POSENT --grp sur ce meme element.
check("tb_le_derive_est_recalcule_la_ou_la_teinte_de_groupe_est_posee",
      _R_TBB is not None
      and "--grp-fill:oklch(from var(--grp) l c h / .16)" in _R_TBB
      and "--grp-line:var(--grp)" in _R_TBB
      and all((".dzsvm .dzm-g-%s{--grp:var(--grp-%s," % (_g, _g)) in _MC
              for _g in ("pistes", "biblio", "mot", "ajouts", "projets")),
      f"tbb={_R_TBB!r}")
check("tb_l_etat_survol_est_celui_du_tableau",
      _R_HOV is not None and "background:var(--srf-hover," in _R_HOV
      and "border-color:var(--brd-hard," in _R_HOV, f"hover={_R_HOV!r}")
check("tb_l_etat_enfonce_est_celui_du_tableau",
      _R_ACT is not None and "transform:scale(.94) translateY(1px)" in _R_ACT
      and "var(--dur-press," in _R_ACT and "var(--ease-pop," in _R_ACT,
      f"active={_R_ACT!r}")
# ACTIF : INVERSION FRANCHE. L'icone ET le libelle passent en encre haute,
# sinon la couleur resterait le seul porteur de l'etat (§4.5).
check("tb_l_etat_actif_inverse_le_fond_la_bordure_l_icone_et_le_libelle",
      _R_ON is not None and _R_ONC is not None
      and "background:var(--grp-fill," in _R_ON
      and "border-color:var(--grp-line," in _R_ON
      and "color:var(--txt-hi," in _R_ONC
      and "var(--ink-strong," in _R_ONC,
      f"on={_R_ON!r} onc={_R_ONC!r}")
check("tb_les_deux_etats_de_la_bascule_du_4_3_sont_habilles",
      _R_MIX is not None and "background:transparent" in _R_MIX
      and "border-color:var(--grp-line," in _R_MIX
      and _R_DIS is not None and "opacity:.38" in _R_DIS
      and "cursor:not-allowed" in _R_DIS,
      f"mix={_R_MIX!r} dis={_R_DIS!r}")
# MASQUABLE, PAS SUPPRIMABLE : le libelle est toujours dans le DOM, c'est la
# feuille qui l'eteint. La sonde node mesure l'autre moitie.
check("tb_le_libelle_est_masquable_par_token_et_non_supprime",
      _R_TBL is not None and "display:var(--lbl," in _R_TBL
      and "font-size:9.5px" in _R_TBL and "var(--f-mono," in _R_TBL,
      f"tbl={_R_TBL!r}")
# « aucun enfoncement » (§4.5) : le coupe-circuit global de la feuille de
# tokens ramene les DUREES a 1 ms, il ne retire pas une transformation.
_i_rm = _MC.find("@media (prefers-reduced-motion:reduce){")
check("tb_le_mouvement_reduit_retire_l_enfoncement",
      _i_rm >= 0 and "transform:none" in _MC[_i_rm:_i_rm + 260]
      and ".dzm-tbb:active" in _MC[_i_rm:_i_rm + 260],
      f"bloc={_MC[_i_rm:_i_rm + 200]!r}")

# ── CE QUE CE LOT NE FAIT PAS, EPINGLE ────────────────────────────────────
# Les etapes 4 a 8 du §9 ne sont pas livrees, et la barre n'est montee NULLE
# PART : aucune section du patcher ne pose une des classes de ce lot. Le jour
# ou l'etape 4 arrive, CETTE ligne rougit — elle est le rappel que l'etat
# connu a change, pas une interdiction. Les neuf controles du bandeau fixe
# sont donc toujours la : le §5.1 (leur retrait) est l'etape 6.
_SECTIONS = "".join(r for _t, _a, r in P.PATCHES)
check("tb_etape_4_a_8_non_livrees_aucune_section_ne_monte_la_barre",
      "dzm-tbb" not in _SECTIONS and "ToolBtn" not in _SECTIONS
      and "DzTracks.TbIcon" not in _SECTIONS
      and len(_SECTIONS) > 10000,
      f"{len(_SECTIONS)} o de sections — une section monte deja la barre")

# LA LIGNE QUI DIT QUE LE BANC A ROUGI PLUTOT QUE MEURE : aucun appel garde
# n'a pose de temoin. Une panne de node — introuvable, ou un shim qui tourne
# sans fin et que le delai coupe — fait rougir CETTE ligne EN PLUS de celles
# qu'elle emporte, et le banc va jusqu'a imprimer son compte.
# ELLE A ETE DEPLACEE ICI LE 05/09/2026, ET C'EST UNE CORRECTION : elle vivait
# au milieu du fichier, avant les sections [3] et [3-bis], et ne voyait donc
# AUCUN temoin pose apres elle. Sa promesse — « aucun appel garde n'a leve » —
# n'etait vraie que de la premiere moitie du banc. Une ligne de queue doit
# etre EN QUEUE ; les sections s'ajoutent, elle doit rester la derniere.

check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
