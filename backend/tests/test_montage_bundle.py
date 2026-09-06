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

COMPTE DE REFERENCE, 06/09/2026 (etape 8 du handoff « Barre Outils
Flottante » — clavier, `role="toolbar"`, mouvement reduit) : 855 lignes, soit
SOIXANTE ET ONZE de plus que les 784 de l'etape 7, et le compte se decompose :
TRENTE-SEPT lignes ecrites une a une dans la section [6-quater] neuve,
VINGT-QUATRE que la boucle des jetons du Dock emet (vingt-trois jetons plus
la ligne de l'asymetrie Echap / fleches), TROIS pour les `aria-label` des
chips, et SEPT que la boucle sur `P.PATCHES` emet toute seule pour les trois
sections neuves du patcher — M20a, M20b, M21. QUATRE lignes ont ete
REECRITES plutot que supprimees, parce qu'elles ont fait leur travail en
rougissant : « l'etape 8 n'est toujours pas livree » (qui exigeait
`role:"toolbar"`, `tabIndex` et `aria-orientation` ABSENTS), celle du Dock
(dont le cablage est desormais hisse hors du rendu) et les deux qui
decoupaient le bloc de la barre par son en-tete de commentaire.
LA CAMPAGNE DE MUTATION QUI FONDE [6-quater] : CINQUANTE-DEUX mutations
APPLIQUEES — quarante-deux sur la couche et la feuille, DIX sur le PATCHER
(chacune suivie d'un rejeu complet de la chaine) — plus un temoin neutre, qui
ne fait rougir que le bruit de fond connu
(`bloc_EST_la_couche_octet_pour_octet`, rouge sur TOUTE mutation de la couche
tant que le patcher n'a pas ete rejoue). Toutes rouges.
UNE MESURE A CONTREDIT LA PREMIERE VERSION DE CE LOT, et elle ne vient pas
d'un mutant mais d'une lecture : `Echap` arretait sa propagation. Le bouton
`projets` de la barre ouvre le popover des projets SANS deplacer le focus,
qui reste donc DANS la barre ; ce popover ferme sur `Echap` par un ecouteur
`window` de phase MONTANTE, donc sous nous. Une frappe repliait la barre et
laissait le popover ouvert derriere, sans clavier pour le fermer. `Echap`
laisse desormais monter ; les FLECHES, elles, restent arretees.
DEUX MUTANTS ont survecu a la premiere passe et ont fait
reecrire ce qu'ils traversaient :
  • retirer le `stopPropagation` d'UNE des deux branches laissait la ligne
    verte — la meme instruction vit dans l'autre branche ET dans le clavier
    de la poignee (faute n°2, forme « sous-chaine que la chaine ecrit
    ailleurs ») ; la ligne compte desormais DANS `barKey` seul, verifie le
    compte du Dock entier, et epingle la POSITION du seul survivant ;
  • retourner la phrase d'attribution du mouvement reduit (« ne vient PAS de
    la feuille de tokens » -> « vient de ») ne faisait rien rougir : aucune
    ligne ne mesurait la RECTIFICATION elle-meme, seulement son effet.
UNE FAUTE N°6 A ETE COMMISE ET CORRIGEE PENDANT L'ECRITURE : `HTML` est un
`pathlib.Path`, pas du texte, et `"x" not in HTML` a TUE le banc au lieu de le
faire rougir. `_lire` / `_HTML` sont la parade, et elle etait deja la.

COMPTE PRECEDENT, 06/09/2026 (etape 5 du handoff — le deport) : 734 lignes,
soit QUATRE-VINGT-NEUF de plus que
les 645 de l'etape 4 : SOIXANTE-HUIT dans la section [6-ter] neuve, et
VINGT ET UNE dans [6-bis], qui grossit d'une boucle de dix-sept jetons sur le
Dock et de quatre lignes dedoublees. Cinq lignes de l'etape 4 qui
epinglaient l'etat inerte
(poignee morte, `⌖` eteint, « les etapes 5 a 8 ne sont pas livrees ») ont ete
REECRITES plutot que supprimees — elles ont fait exactement leur travail en
rougissant.
LA CAMPAGNE DE MUTATION QUI FONDE CETTE SECTION : SOIXANTE-QUINZE mutations
de la couche et de la feuille (plus un temoin neutre, qui ne doit rien faire
rougir), toutes rouges, chacune dans un rayon de une a quinze lignes — plus `bloc_EST_la_couche_octet_pour_octet`, qui rougit sur
TOUTE mutation de la couche tant que le patcher n'a pas ete rejoue, et qui est
le seul bruit de fond de ce harnais (mesure : une mutation neutre laisse le
banc a 726/1). CINQ mutants ont survecu a la premiere passe et ont fait
reecrire ce qu'ils traversaient : l'ancrage `bar.left - dx` (aucune sonde ne
partait d'un decalage non nul contre une borne), le plafond de remontee
d'arbre (une propriete de VIVACITE, que seule une mesure du nombre de pas
attrape), une garde en double dans un helper que rien ne pouvait atteindre
(supprimee — faute n°3), et DEUX jetons de source trop courts qui vivaient
aussi ailleurs (faute n°2, forme « sous-chaine »).

COMPTE PRECEDENT, 05/09/2026 (fin de journee, apres M9c) : 536 lignes.
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
# ══ ÉTAPE 6 DU HANDOFF (§5.1) : M10 A ÉTÉ VIDÉE ═══════════════════════════
# La chip « mot » et le bouton « emoji » ONT QUITTÉ le bandeau. Le §5.1
# l'exige (« Ne pas les laisser en double […] deux sources de vérité pour
# l'état des bascules ») et la barre flottante les porte depuis l'étape 7.
# UNE ABSENCE EST VRAIE D'UN FICHIER VIDE : cette ligne porte donc son
# CONJOINT, et il n'est pas décoratif — c'est la PORTE DE REMPLACEMENT, avec
# les quatre expressions que M10 écrivait, reprises MOT POUR MOT par R_M19.
# MESURÉE PAR MUTATION, dans les deux sens : en remettant `R_M10` dans `R_M8`
# et en rejouant la chaîne, les deux premiers comptes passent à 1 — rouge ; en
# retirant `wordAnim:` de R_M19 et en rejouant, le conjoint tombe — rouge
# aussi, et le détail nomme lequel des deux a lâché.
check("etape6_la_chip_mot_et_le_bouton_emoji_ont_quitte_le_bandeau",
      s.count("DzTracks.WordAnimChip") == 0
      and s.count("DzTracks.EmojiBtn") == 0
      and s.count(nl("r.jsx(DzTracks.ToolDock,{")) == 1
      and s.count(nl('wordAnim:(proj.subsStyle||{}).wordAnim||"couleur"')) == 1
      and s.count(nl("onWordAnim:function(v){subsStyleSet({wordAnim:v})}")) == 1
      and s.count(nl("emojiSegs:subsSegsOf(clips)")) == 1
      and s.count(nl("onEmojiAdd:dzEmoAdd")) == 1,
      f'chip={s.count("DzTracks.WordAnimChip")} '
      f'emoji={s.count("DzTracks.EmojiBtn")} '
      f'dock={s.count(nl("r.jsx(DzTracks.ToolDock,{"))} '
      f'wordAnim={s.count(nl(chr(34) + "couleur" + chr(34)))}')
# LES COMPOSANTS DÉMONTÉS RESTENT AU CONTRAT, et c'est un RESTE ASSUMÉ, dit
# plutôt que découvert : le §5.1 retire des contrôles DU BANDEAU, pas des
# composants d'une bibliothèque publique. Quatre briques exportées ne sont
# plus montées nulle part — le banc, lui, les joue toujours sous node.
_DEMONTES = ("WordAnimChip:DzmWordAnimChip", "EmojiBtn:DzmEmojiBtn",
             "TrackAdd:DzmTrackAdd", "LibBtn:DzmLibBtn")
check("etape6_les_quatre_composants_demontes_restent_au_contrat",
      all(_j in src for _j in _DEMONTES)
      and all(s.count(nl(_j)) == 1 for _j in _DEMONTES),
      f'{[_j for _j in _DEMONTES if _j not in src]} hors contrat')
for _nm, _decl in (("pushHistory", "var pushHistory=x.useCallback("),
                   ("setClips", "setClips=st1[1]"),
                   ("setDirty", "setDirty=st8[1]")):
    _appele = re.search(r"\b%s\b" % re.escape(_nm), P.R_M11) is not None
    check("M11_appelle_" + _nm + "_qui_est_declare",
          _appele and s.count(nl(_decl)) >= 1,
          f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# L'ANNULATION est garantie par CONSTRUCTION ici : `pushHistory` et `undo`
# sont des hooks du composant, hors de portée du shim node — qui ne joue que
# la couche pure. Ce que cette ligne épingle est l'ORDRE des deux appels dans
# le bundle livré. L'EFFET, lui, est mesuré : la section [6-quater] rejoue les
# neuf actions de la barre sur un faux écran qui reproduit cette sémantique.
# ÉTAPE 6 — IL N'Y A PLUS QU'UNE PORTE, ET C'EST CE QUI REFERME LE DOUBLON
# D'ATTENTE : `dzmEmojiGo` n'a pas de hook, chaque porte tenait le sien
# (`DzmEmojiBtn` d'un côté, le Dock de l'autre). Une porte est partie, une
# attente avec elle. LA DÉFINITION, ELLE, N'A PAS BOUGÉ DE PLACE : elle est
# toujours dans R_M11, le corps du composant, et c'est ce qui interdit de la
# recopier dans R_M19. Deux faces, comme avant : une seule définition, ET
# exactement un usage — l'ancien `onAdd:dzEmoAdd` doit avoir disparu.
# MESURÉE PAR MUTATION : en recopiant le corps dans R_M19 au lieu d'appeler
# `dzEmoAdd`, `_usages` tombe à 0 — rouge ; en remettant `R_M10` dans `R_M8`,
# il monte à 2 — rouge aussi.
_DEF_EMOADD = ("function dzEmoAdd(cs){pushHistory();"
               "setClips(function(k){return (k||[]).concat(cs)});"
               "setDirty(!0)}")
_usages = s.count(nl("onAdd:dzEmoAdd")) + s.count(nl("onEmojiAdd:dzEmoAdd"))
check("etape6_une_seule_porte_pose_les_emoji",
      s.count(nl(_DEF_EMOADD)) == 1 and _usages == 1
      and s.count(nl("onAdd:dzEmoAdd")) == 0
      and "onEmojiAdd:dzEmoAdd" in P.R_M19
      and _DEF_EMOADD in P.R_M11,
      f'definitions={s.count(nl(_DEF_EMOADD))} usages={_usages} '
      f'ancienne_porte={s.count(nl("onAdd:dzEmoAdd"))}')

print("\n[1-bis] P3 — le bouton « texte », le panneau, et la coupe par plage")
# ÉTAPE 6 (§5.1) : LE BOUTON « texte » A QUITTÉ LE BANDEAU. Sa classe
# `dzm-txton` n'était écrite que par R_M11b — elle vaut donc zéro partout, y
# compris dans la feuille, d'où les deux règles retirées de montage.css.
# L'ABSENCE PORTE SON CONJOINT : la bascule n'est pas perdue, la barre la
# tient (`textOn`/`onText` sur le MÊME état), et le panneau (M12) n'a pas
# bougé. Une ligne qui n'aurait mesuré que la disparition aurait été verte
# d'un bundle sans panneau du tout.
check("etape6_le_bouton_texte_a_quitte_le_bandeau",
      s.count("dzm-txton") == 0
      and "dzm-txton" not in CSS.read_text(encoding="utf-8")
      and s.count(nl("textOn:dzTextOn,onText:function(){"
                     "setDzTextOn(!dzTextOn)}")) == 1
      and s.count(nl("DzTracks.TextDrawer")) == 1,
      f'txton_bundle={s.count("dzm-txton")} '
      f'porte={s.count(nl("textOn:dzTextOn"))}')
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
    # M19 (etape 4 de la barre d'outils) emploie `dzTextOn` et
    # `setDzTextOn` a son tour : la barre est un SECOND point d'entree
    # sur le meme etat, pas un second etat. La ligne garde son sens —
    # ces noms n'apparaissent nulle part AILLEURS que dans les sections
    # qui les ecrivent — et rougirait encore si un tiers les employait.
    _dehors = s.count(_nm) - (P.R_M11 + P.R_M12 + P.R_M19).count(_nm)
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
# ÉTAPE 6 : l'état retenu du panneau « Texte » se lit désormais SUR LA BARRE,
# par la règle générale des bascules (`.dzm-tbb.dzm-on`), et non plus par une
# règle propre au bandeau. La ligne mesure les deux faces : la règle existe
# dans la feuille, ET la couche pose bien la classe qu'elle habille.
# Vérifier la seule feuille aurait laissé passer un renommage côté couche ;
# vérifier le seul JS n'aurait pas vu la règle disparaître.
check("css_porte_l_etat_retenu_des_bascules_de_la_barre",
      ".dzm-tbb.dzm-on" in CSS.read_text(encoding="utf-8")
      and "dzm-on" in src and "dzm-txton" not in src,
      "l'etat retenu des bascules de la barre n'est pas habille")

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
# DEUX depuis P12, et les deux sont NOMMES : `if(pushHistory)pushHistory();`
# est celui de gradeAllBtn (le lot), `o.pushHistory()` celui d'`extract`
# (un seul geste, un seul clip). Un troisieme rougirait ici, avec son nom.
check("M13_un_seul_pushHistory_pour_le_lot",
      src.count("if(pushHistory)pushHistory();") == 1
      and src.count("o.pushHistory()") == 1
      and src.count("pushHistory()") == 2,
      f'lot={src.count("if(pushHistory)pushHistory();")} '
      f'extract={src.count("o.pushHistory()")} '
      f'total={src.count("pushHistory()")}')
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
# ── ÉTAPE 6 (§5.1) : « Bibliothèque… » A QUITTÉ LE BANDEAU ────────────────
# Le bouton était posé dans R_M8 ; il n'y est plus. L'ABSENCE PORTE SON
# CONJOINT — la barre flottante reçoit le MÊME `openPicker` et résout la MÊME
# piste vidéo (`dzmPickTrack(ts,"video")`, dans `dzmTbCablage`) — sans quoi
# cette ligne serait verte d'un bundle où plus rien n'ouvrirait la
# Bibliothèque.
check("etape6_le_bouton_bibliotheque_a_quitte_le_bandeau",
      s.count("DzTracks.LibBtn") == 0
      and s.count(nl("onPick:openPicker")) == 1
      and "onPick:openPicker" in P.R_M19
      and nl('children:"Bibliothèque…"},"lib")') in s,
      f'libbtn={s.count("DzTracks.LibBtn")} '
      f'onPick={s.count(nl("onPick:openPicker"))}')
# Le libelle EST le mot de l'utilisateur (« depuis la bibliotheque »), pas
# « + clip ». Le composant reste dans la couche (reste assume, cf. plus haut),
# donc le libelle se mesure toujours dans le bundle livre.
check("M16lib_le_libelle_est_le_mot_de_l_utilisateur",
      nl('children:"Bibliothèque…"},"lib")') in s,
      "le bouton ne s'appelle plus « Bibliothèque… »")
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
# R_M23 (P12) la LIT — le bouton « Extraire le son » passe les pistes du
# projet a la couche par la meme ref que l'ajout, pour la meme raison.
_dehors = (s.count("dzTracksRef")
           - (P.R_M16REF + P.R_M16A + P.R_M23).count("dzTracksRef"))
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
      # TROIS depuis P12 : /duration, /has-audio et le premier appelant.
      SVC.count("p = await _media_source(request, src, video=False)") == 3
      and SVC.count("dur = await asyncio.to_thread(_probe_duration, p)") == 1,
      f'media_source={SVC.count("p = await _media_source(request, src, video=False)")} '
      f'probe={SVC.count("dur = await asyncio.to_thread(_probe_duration, p)")}')

# ══ P12 — LE SON D'UN PLAN SUIT SA VIDEO : les sections, dans le bundle ═══
# Les comptes generiques (`*_remplace`, `*_ancre_consommee`,
# `couche_ne_cite_pas_l_ancre_de_*`) couvrent M22a/M22b/M22c/M23 par la
# boucle sur P.PATCHES. Ce qui suit est ce qu'ils ne mesurent pas : l'ORDRE
# des sorties dans addAsset, l'unicite du concat, la place de la sonde dans
# R_M17A (un texte qui n'existe qu'apres patch), et les deux faces de chaque
# identifiant que ces sections lisent.
# L'ORDRE, sur les POSITIONS dans le corps d'addAsset (`find`, jamais
# `index`) : la sonde audio AVANT askDur, askDur AVANT pushHistory, le
# jumeau decide (twinPlan) AVANT pushHistory, pushHistory AVANT l'unique
# concat.
_aa0 = s.find(nl("function addAsset(src,label,kind,srcDur,trId,atTime){"))
_au = s.find(nl("DzTracks.askAudio(src,{done:function(){"), _aa0 if _aa0 >= 0 else 0)
_ask2 = s.find(nl("DzTracks.askDur(src,{done:function(dzV){"), _aa0 if _aa0 >= 0 else 0)
_tw = s.find(nl("DzTracks.twinPlan(dzNeuf,dzTs,clipsRef.current||[],dzAu,"),
             _aa0 if _aa0 >= 0 else 0)
_ph2 = s.find(nl("    pushHistory();\n    setClips(clipsRef.current.concat("),
              _aa0 if _aa0 >= 0 else 0)
check("P12_la_sonde_audio_sort_avant_la_duree_qui_sort_avant_l_historique",
      _aa0 >= 0 and _au > _aa0 and _ask2 > _au and _tw > _ask2 and _ph2 > _tw,
      f"addAsset={_aa0} askAudio={_au} askDur={_ask2} twinPlan={_tw} "
      f"pushHistory+concat={_ph2}")
# LE RAPPEL REPASSE LES MEMES ARGUMENTS (et `st`, l'instant du clic, comme
# askDur) ; la duree en prime passe par la couche (srcDurOr), pas par une
# seconde copie de needDur — `DzTracks.needDur(` reste a 1 (P11 le tient).
check("P12_le_rappel_repasse_les_memes_arguments",
      s.count(nl("DzTracks.askAudio(src,{done:function(){\n"
                 "      addAsset(src,label,kind,srcDur,trId,st)}});return}")) == 1
      and s.count(nl("srcDur=DzTracks.srcDurOr(kind,srcDur,dzAu);")) == 1,
      f'rappel={s.count(nl("addAsset(src,label,kind,srcDur,trId,st)"))} '
      f'srcDurOr={s.count(nl("srcDur=DzTracks.srcDurOr(kind,srcDur,dzAu);"))}')
# UN SEUL CONCAT, qui porte les deux clips ; l'ancienne ecriture a disparu.
check("P12_un_seul_concat_porte_le_plan_et_son_jumeau",
      s.count(nl("setClips(clipsRef.current.concat(dzTw&&dzTw.clip?"
                 "[dzNeuf,dzTw.clip]:[dzNeuf]));")) == 1
      and s.count(nl("setClips(clipsRef.current.concat([{tr:tr2,id:id,")) == 0
      and s.count(nl("setClips(clipsRef.current.concat(")) == 1,
      f'neuf={s.count(nl("setClips(clipsRef.current.concat(dzTw&&dzTw.clip?"))} '
      f'total={s.count(nl("setClips(clipsRef.current.concat("))}')
# LA PHRASE DU JUMEAU ENTRE DANS LA NOTE DE L'AJOUT par `dzTail`, sans que
# la fin de note de M16b ne bouge (`+dzTail)}` reste unique — P11 le tient).
check("P12_la_phrase_du_jumeau_entre_dans_la_note_de_l_ajout",
      s.count(nl("if(dzTw)dzTail+=dzTw.note;")) == 1
      and s.count(nl("+dzTail)}")) == 1,
      f'tail={s.count(nl("if(dzTw)dzTail+=dzTw.note;"))} '
      f'fin={s.count(nl("+dzTail)}"))}')
# L'IDENTIFIANT DE L'AJOUT PASSE PAR uniqueId, et l'ancienne forme a disparu.
check("P12_l_identifiant_de_l_ajout_passe_par_uniqueId",
      s.count(nl('var id=DzTracks.uniqueId(clipsRef.current||[],\n'
                 '      tr2+"u"+ovSeq.current+"_"+Math.round(st*10));')) == 1
      and s.count(nl('var id=tr2+"u"+ovSeq.current+"_"+Math.round(st*10);')) == 0,
      f'{s.count(nl("var id=DzTracks.uniqueId(clipsRef.current||[],"))}')
# svmApplyProject : le dedoublonnage AVANT `setClips(cs)`, et le re-semis du
# compteur — positions dans le corps.
_ap0 = s.find(nl("  function svmApplyProject(d){"))
_dd = s.find(nl("var dzDd=DzTracks.dedupeIds(cs);cs=dzDd.clips;"), _ap0 if _ap0 >= 0 else 0)
_sq = s.find(nl("ovSeq.current=Math.max(ovSeq.current,DzTracks.seqMax(cs));"),
             _ap0 if _ap0 >= 0 else 0)
_sc = s.find(nl("setClips(cs);setSelId(first?first.id:\"\");setPh(0);"),
             _ap0 if _ap0 >= 0 else 0)
check("P12_svmApplyProject_dedoublonne_et_re_seme_avant_d_ecrire",
      _ap0 >= 0 and _dd > _ap0 and _sq > _dd and _sc > _sq,
      f"apply={_ap0} dedupe={_dd} seq={_sq} setClips={_sc}")
# `ovSeq.current=` n'existait NULLE PART dans le bundle (mesure, fait n°3) :
# il existe maintenant UNE fois, au re-semis.
check("P12_le_compteur_est_re_seme_une_fois",
      s.count("ovSeq.current=Math.max(") == 1 and s.count("ovSeq.current=") == 1,
      f'{s.count("ovSeq.current=")}')
# M22a (tour 2) : quand aucun jumeau ne parle, l'incrustation est DITE — la
# branche `else` appelle `overlayNote`, declaree ET exportee par la couche.
check("P12_M22a_l_incrustation_est_dite_quand_le_jumeau_ne_parle_pas",
      s.count(nl("    if(dzTw)dzTail+=dzTw.note;\n"
                 "    else dzTail+=DzTracks.overlayNote(kind,dzTs,tr2);")) == 1
      and re.search(r"\bfunction dzmOverlayNote\(", src) is not None
      and src.count("overlayNote:dzmOverlayNote") == 1,
      f'{s.count(nl("else dzTail+=DzTracks.overlayNote(kind,dzTs,tr2);"))}')
# M22c (tour 2) : `v1_non_video` suit le renommage — une seule ecriture, et
# R_M7 la lit toujours APRES (deux faces : la ligne `v1NonVideo:` de M7).
_nv = nl("if(dzDd.renamed.length&&Array.isArray(d.v1_non_video))d.v1_non_video=")
check("P12_M22c_v1_non_video_suit_le_renommage_avant_que_M7_ne_le_lise",
      s.count(_nv) == 1
      and 0 <= s.find(_nv) < s.find(nl("v1NonVideo:Array.isArray(d.v1_non_video)")),
      f'{s.count(_nv)} nv={s.find(_nv)} m7={s.find(nl("v1NonVideo:Array.isArray(d.v1_non_video)"))}')
# M22d (tour 2) : `setDirty` de svmApplyProject suit le renommage d'une
# SAUVEGARDE — l'ancien `setDirty(!1)` n'y est plus, le nouveau y est une
# fois, et `d.saved` est ce que la meme fonction lit deja AVANT (`if(d.saved){`
# dans le corps de svmApplyProject — deux dans le bundle, un ici, mesure).
_sd = s.find(nl('    setClips(cs);setSelId(first?first.id:"");setPh(0);'
                'setDirty(!!(d.saved&&dzDd.renamed.length));\n'))
_sv = s.find("if(d.saved){", _ap0 if _ap0 >= 0 else 0)
check("P12_M22d_la_reparation_arme_l_autosauvegarde",
      s.count(nl('    setClips(cs);setSelId(first?first.id:"");setPh(0);'
                 'setDirty(!!(d.saved&&dzDd.renamed.length));\n')) == 1
      and s.count(nl('setPh(0);setDirty(!1);')) == 0
      and _ap0 >= 0 and _ap0 < _sv < _sd,
      f'neuf={s.count("setDirty(!!(d.saved&&dzDd.renamed.length));")} '
      f'ancien={s.count(nl("setPh(0);setDirty(!1);"))} apply={_ap0} saved={_sv} dirty={_sd}')
# LE BOUTON est pose AVANT `transInspector(),` — que R_M12 reprend en tete —
# et R_M12 reste contigu (sa ligne `_remplace` le tient aussi).
_bt = s.find(nl("DzTracks.extractBtn(sel,{tracks:dzTracksRef.current||svmTracksOf(proj),"))
_ti = s.find(nl("        transInspector(),"))
check("P12_le_bouton_precede_l_inspecteur_de_transition",
      _bt >= 0 and _ti > _bt and s.count(nl("        transInspector(),")) == 1
      and (_ti - _bt) < 600,
      f"bouton={_bt} transInspector={_ti}")
# DEUX FACES pour chaque identifiant de la couche que les sections appellent
# (un appel dans le bundle, un export dans la couche), et pour chaque
# identifiant du bundle que les sections lisent (une declaration, un appel
# borne `\b…\b` dans la section).
for _nom in ("wantsTwin", "audioOf", "askAudio", "srcDurOr", "uniqueId",
             "twinPlan", "dedupeIds", "seqMax", "extractBtn"):
    check("P12_deux_faces_DzTracks_" + _nom,
          s.count(nl("DzTracks." + _nom + "(")) == 1
          and src.count(_nom + ":dzm" + _nom[0].upper() + _nom[1:]) == 1,
          f'bundle={s.count(nl("DzTracks." + _nom + "("))} '
          f'couche={src.count(_nom + ":dzm" + _nom[0].upper() + _nom[1:])}')
for _sec, _r, _pairs in (
        ("M22a", P.R_M22A,
         (("ovSeq", "var ovSeq=x.useRef(0);"),
          ("clipsRef", "var clipsRef=x.useRef(clips);clipsRef.current=clips;"),
          ("trackStRef", "var trackStRef=x.useRef(trackSt);"),
          ("pushHistory", "var pushHistory=x.useCallback("),
          ("dzTs", "var dzTs=dzTracksRef.current||svmTracksOf(proj);"),
          ("dzAuOn", "var dzAuOn=DzTracks.wantsTwin(kind,dzTs,tr2);"),
          ("dzAu", "var dzAu=dzAuOn?DzTracks.audioOf(src):null;"),
          ("dzTail", "var dzTail=dzCl.note+(dzGrew?"))),
        ("M22b", P.R_M22B,
         (("dzNeuf", "var dzNeuf={tr:tr2,id:id,label:label,start:st,end:en,"),
          ("dzTw", "var dzTw=dzAuOn?DzTracks.twinPlan("),
          ("setClips", "setClips=st1[1]"),
          ("clipsRef", "var clipsRef=x.useRef(clips);clipsRef.current=clips;"))),
        ("M22c", P.R_M22C,
         (("cs", "var cs=(d.clips||[]).map(function(c,i){"),
          ("fireNote", "fireNote=nt[1]"),
          ("ovSeq", "var ovSeq=x.useRef(0);"))),
        ("M23", P.R_M23,
         (("sel", "var sel=clips.find("),
          ("dzTracksRef", "var dzTracksRef=x.useRef(null);"),
          ("svmTracksOf", "function svmTracksOf(proj){"),
          ("proj", "proj=stP[0],setProj=stP[1];"),
          ("clipsRef", "var clipsRef=x.useRef(clips);clipsRef.current=clips;"),
          ("trackStRef", "var trackStRef=x.useRef(trackSt);"),
          ("pushHistory", "var pushHistory=x.useCallback("),
          ("setClips", "setClips=st1[1]"),
          ("setDirty", "setDirty=st8[1]"),
          ("fireNote", "fireNote=nt[1]")))):
    for _nm, _decl in _pairs:
        _appele = re.search(r"\b%s\b" % re.escape(_nm), _r) is not None
        check("P12_" + _sec + "_appelle_" + _nm + "_qui_est_declare",
              _appele and s.count(nl(_decl)) >= 1,
              f"appelé={_appele} déclaré={s.count(nl(_decl))} ({_decl})")
# LA ROUTE, DES DEUX COTES DU FIL : la couche l'appelle, le service la sert
# — et reutilise la sonde du rendu (`_has_audio_stream`) et la mesure de
# duree, sans copie.
check("P12_la_route_has_audio_existe_des_deux_cotes",
      src.count('"/api/montage/has-audio?src="') == 1
      and SVC.count('@router.get("/has-audio")') == 1
      and SVC.count("async def montage_has_audio(") == 1,
      f'couche={src.count(chr(34) + "/api/montage/has-audio?src=" + chr(34))} '
      f'route={SVC.count(chr(34) + "@router.get(" + chr(34) + "/has-audio" + chr(34) + ")")}')
check("P12_la_route_reutilise_la_sonde_du_rendu",
      SVC.count("asyncio.to_thread(_has_audio_stream, p)") == 1
      and SVC.count("asyncio.to_thread(_probe_duration, p)") == 2,
      f'has_audio={SVC.count("asyncio.to_thread(_has_audio_stream, p)")} '
      f'probe={SVC.count("asyncio.to_thread(_probe_duration, p)")}')
# LA FEUILLE habille le bouton, sans toucher a la liste de P6.
check("css_porte_le_bouton_extraire_le_son",
      ".dzm-extract{" in _css.replace(" ", "").replace("\n", "").replace("\r", "")
      and "dzm-extract" in src,
      "montage.css n'habille pas « Extraire le son »")
# LA COUCHE NE CITE AUCUN identifiant minifie du bundle qu'elle ne declare
# pas : les noms neufs de P12 sont mesures LIBRES dans le bundle d'entree.
for _nm in ("dzAuOn", "dzAu", "dzNeuf", "dzTw", "dzDd", "DZM_AUDIO_CACHE"):
    _bak = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
    _dans_bak = (_bak.read_bytes().count(_nm.encode("utf-8"))
                 if _bak.is_file() else -1)
    check("P12_nom_" + _nm + "_etait_libre_dans_le_bundle_d_entree",
          _dans_bak == 0, f"{_nm} apparait {_dans_bak}x dans .bak_montage")

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
# ── DETTE D'ECRAN DE L'ETAPE 7 (le cablage du §6) ──────────────────
# DEUX MECANISMES QUE SEUL UN NAVIGATEUR VOIT, et aucune de ces lignes ne
# pretend les avoir mesures. Elles EPINGLENT le mecanisme pour que la note de
# dette du commit reste exacte : le jour ou il change, elles rougissent.
#   1. DEUX ETATS D'ATTENTE POUR EMOJI, un par porte — celui du bouton du
#      bandeau et celui du Dock. `dzmEmojiGo` n'a pas de hook et ne peut donc
#      pas les partager. Deux clics simultanes (un par porte) partent en deux
#      requetes : rien n'est detruit — chacune pousse l'historique avant
#      d'ajouter — mais les memes emoji sont poses deux fois. L'etape 6, qui
#      retire le bouton du bandeau, referme cette porte-la.
#   2. L'ORDRE `mousedown` PUIS `click` sur le bouton « projets » de la barre.
#      Le popover se ferme sur un `mousedown` HORS de sa boite — et le bouton
#      de la barre est hors de cette boite. C'est ce qui a impose un COMPTEUR
#      plutot qu'un booleen partage : le resultat NET est « ouverte » quel
#      que soit l'ordre, mais le rendu intermediaire ne se voit qu'a l'ecran.
check("dette_ecran_etape7_les_deux_mecanismes_que_seul_un_navigateur_voit",
      src.count('window.addEventListener("mousedown",down);') == 1
      and "if(box.current&&!box.current.contains(e.target))" in src
      # `var sb=x.useState(0),busy=...` vaut TROIS dans la couche (c'est
      # le motif d'attente de plusieurs composants) : la sous-chaine
      # seule ne decidait rien, il faut l'ancrer sur SON composant.
      and re.search(r"var DzmEmojiBtn=function\(props\)\{\s*"
                    r"var sb=x\.useState\(0\),busy=sb\[0\],"
                    r"setBusy=sb\[1\];", src) is not None
      and src.count("var sm=x.useState(0),emo=sm[0],setEmo=sm[1];") == 1,
      "les deux mecanismes de la note de dette ont bouge")
# ── CE QUE LE §4.3 DEMANDE ET QUE CETTE BASE N'A PAS : LE NUANCIER ANCRE ──
# MESURE, ET CONSIGNEE PLUTOT QU'INVENTEE. Le §4.3 veut que `MOT · couleur`
# ouvre un selecteur de teinte ANCRE SOUS LE BOUTON, limite a huit teintes
# (« pas un selecteur libre — un nuancier ouvert produit des sous-titres
# illisibles »). Rien de tel n'existe ici : AUCUN composant de nuancier, et
# le SEUL controle de couleur des sous-titres est un `<input type="color">`,
# c'est-a-dire le dialogue libre du systeme — exactement ce que le §4.3
# ecarte. Il ecrit `subsStyle` pour toute la piste S1, jamais un mot.
# CETTE LIGNE EST LA POUR QUE LE CONSTAT RESTE VRAI : le jour ou un nuancier
# entre dans cette base, elle rougit et l'ecart du groupe MOT est rediscute.
check("dette_ecran_etape7_aucun_nuancier_ancre_n_existe_dans_cette_base",
      s.count(nl('r.jsx("input",{className:"sub-color",type:"color",'
                 'value:subsHex6(st[k]),')) == 1
      and s.count(nl('col("karColor","Couleur du mot")')) == 1
      and s.count(nl("function subsStyleSet(patch){")) == 1
      # LE GARDE-FOU EST INSENSIBLE A LA CASSE, et c'est une CORRECTION
      # mesuree par mutation : la premiere ecriture cherchait "swatch"
      # et "Swatch", et un `DZM_TB_SWATCH` pose dans la couche passait
      # sans rougir. Faute n°2, et la meme famille que le `Select-String`
      # insensible a la casse de l'etape 5 : la casse decide, on ne la
      # devine pas. `nuancier` s'ajoute — le mot francais du §4.3.
      and "swatch" not in s.lower() and "nuancier" not in s.lower(),
      f'sub-color={s.count(nl(chr(34) + "sub-color" + chr(34)))} '
      f'swatch={s.lower().count("swatch")} '
      f'nuancier={s.lower().count("nuancier")}')

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
/* ══ P12 — LE SON D'UN PLAN SUIT SA VIDEO : le cœur pur ═══════════════════
   dialogueTrack, trackPlein / wantsTwin, uniqueId / dedupeIds / seqMax,
   twinClip, twinPlan, srcDurOr, le cache, askAudio (motif d'askDur : fetch
   et timer injectes, reponse SYNC) et extract (le moteur du bouton, `ask`
   bouchonne). `LEVE:` plutot qu'une exception : rougir, pas mourir. */
function P12(fn){try{return fn()}catch(e){return "LEVE:"+e.name}}
/* les pistes de la sauvegarde de l'utilisateur (06/09) et celle du 04/09 */
var TS_USER=[{id:"v3",kind:"video"},{id:"v2",kind:"video"},{id:"v1",kind:"video"},
  {id:"a1",kind:"audio",bus:"dialogue"},{id:"a2",kind:"audio",bus:"musique",loop:!0},
  {id:"a3",kind:"audio",bus:"sfx"},{id:"s1",kind:"subs"}];
var TS_0409=[{id:"v1",kind:"video"},{id:"a2",kind:"audio",bus:"musique",loop:!0},
  {id:"a1",kind:"audio",bus:"dialogue"},{id:"a3",kind:"audio",bus:"sfx"},
  {id:"s1",kind:"subs"}];
out.dt_defauts=P12(function(){return T.dialogueTrack(T.DEFAULTS)});
out.dt_0409=P12(function(){return T.dialogueTrack(TS_0409)});
/* LA MESURE QUI MOTIVE dialogueTrack : pickTrack rend la MUSIQUE la-dessus */
out.dt_0409_pick=P12(function(){return T.pickTrack(TS_0409,"audio")});
out.dt_bus_ailleurs=P12(function(){return T.dialogueTrack([{id:"v1"},
  {id:"a4",kind:"audio",bus:"dialogue"},{id:"a1",kind:"audio",bus:"sfx"}])});
out.dt_a1_sans_bus=P12(function(){return T.dialogueTrack([{id:"v1"},{id:"a1"}])});
out.dt_a1_bouclee=P12(function(){return T.dialogueTrack([{id:"v1"},
  {id:"a1",kind:"audio",loop:!0},{id:"a2",kind:"audio",bus:"dialogue",loop:!0}])});
out.dt_vide=P12(function(){return T.dialogueTrack([])});
out.dt_null=P12(function(){return T.dialogueTrack(null)});
out.dt_sans_audio=P12(function(){return T.dialogueTrack([{id:"v1"},{id:"s1"}])});
out.dt_a1_video=P12(function(){return T.dialogueTrack([{id:"a1",kind:"video"}])});
/* plein cadre / incrustation */
out.tp_v1=P12(function(){return T.trackPlein(T.DEFAULTS,"v1")});
out.tp_v2=P12(function(){return T.trackPlein(T.DEFAULTS,"v2")});
out.tp_v3_neuve=P12(function(){return T.trackPlein(T.add(T.DEFAULTS,"video"),"v3")});
out.tp_v1_nue=P12(function(){return T.trackPlein(TS_USER,"v1")});
out.tp_a1=P12(function(){return T.trackPlein(T.DEFAULTS,"a1")});
out.tp_absente=P12(function(){return T.trackPlein(T.DEFAULTS,"v9")});
out.tp_vide=P12(function(){return T.trackPlein([],"v1")});
out.tp_video_plein_neuve=P12(function(){return T.trackPlein(
  [{id:"v2",kind:"video",type:"vidéo"}],"v2")});
/* LA LISTE NUE ET SON HABILLAGE (tour 2) : le payload d'une sauvegarde nomme
   v2 SANS type, et une liste nue rend vrai pour v2 ; ce qui tient
   l'exemption est svmTracksFrom (dzmSkin a l'apply), mesure cote a cote. */
out.tp_user_v2_nue=P12(function(){return T.trackPlein(TS_USER,"v2")});
out.tp_from_v2=P12(function(){return T.trackPlein(T.from(TS_USER),"v2")});
out.tp_from_types=P12(function(){return T.from(TS_USER).slice(0,3)
  .map(function(t){return [t.id,t.type||""]})});
out.wt_user_v2=P12(function(){return [T.wantsTwin("video",TS_USER,"v2"),
  T.wantsTwin("video",T.from(TS_USER),"v2")]});
/* L'INCRUSTATION DITE (overlayNote) : la phrase pour v2 habillee, "" pour
   V1 (le jumeau parle), un son, une image, une piste absente ou d'un
   autre genre, une liste vide, null. */
out.on_v2=P12(function(){return T.overlayNote("video",T.from(TS_USER),"v2")});
out.on_v2_sans_dialogue=P12(function(){return T.overlayNote("video",
  [{id:"v1",kind:"video",type:"vidéo"},{id:"v2",kind:"video",type:"overlay"}],"v2")});
out.on_rien=P12(function(){return [T.overlayNote("video",T.from(TS_USER),"v1"),
  T.overlayNote("audio",T.from(TS_USER),"v2"),T.overlayNote("image",T.from(TS_USER),"v2"),
  T.overlayNote("video",T.from(TS_USER),"v9"),T.overlayNote("video",T.from(TS_USER),"a1"),
  T.overlayNote("video",[],"v2"),T.overlayNote("video",null,"v2")]});
out.wt=P12(function(){return [T.wantsTwin("video",T.DEFAULTS,"v1"),
  T.wantsTwin("audio",T.DEFAULTS,"v1"),T.wantsTwin("image",T.DEFAULTS,"v1"),
  T.wantsTwin("video",T.DEFAULTS,"v2")]});
/* identifiants — les doublons de la sauvegarde de l'utilisateur */
var CS_USER=[{tr:"a1",id:"a1_vo"},{tr:"v1",id:"v1u1_0"},{tr:"v1",id:"v1u2_0"},
  {tr:"v1",id:"v1u3_0"},{tr:"v1",id:"v1u1_0"},{tr:"v1",id:"v1u2_0"},
  {tr:"s1",id:"s1cmtpobgr366"}];
out.ui_libre=P12(function(){return T.uniqueId(CS_USER,"v1u4_0")});
out.ui_pris=P12(function(){return T.uniqueId(CS_USER,"v1u1_0")});
out.ui_pris_2=P12(function(){return T.uniqueId(CS_USER.concat([{id:"v1u1_0_2"}]),"v1u1_0")});
out.ui_vide=P12(function(){return [T.uniqueId([],"x"),T.uniqueId(null,"x")]});
var dd=P12(function(){return T.dedupeIds(CS_USER)});
out.dd_ids=dd&&dd.clips?dd.clips.map(function(c){return c.id}):"LEVE";
out.dd_renamed=dd&&dd.renamed?dd.renamed:"LEVE";
out.dd_entree_intacte=CS_USER.map(function(c){return c.id});
out.dd_premier_garde=dd&&dd.clips?dd.clips[1]===CS_USER[1]:"LEVE";
out.dd_sans_doublon=P12(function(){var o=T.dedupeIds([{id:"a"},{id:"b"}]);
  return [o.clips.map(function(c){return c.id}),o.renamed.length]});
out.dd_suffixe_deja_pris=P12(function(){return T.dedupeIds([{id:"k"},{id:"k_2"},{id:"k"}])
  .clips.map(function(c){return c.id})});
out.dd_sans_id=P12(function(){return T.dedupeIds([{id:"k"},{},{id:"k"}])
  .clips.map(function(c){return c.id===void 0?"ABSENT":c.id})});
out.dd_vide=P12(function(){var o=T.dedupeIds([]);return [o.clips.length,o.renamed.length]});
out.sm=P12(function(){return [T.seqMax(CS_USER),T.seqMax([]),
  T.seqMax([{id:"a1_vo"},{id:"s1cm"}]),T.seqMax([{id:"v1u12_5"},{id:"a1u7_0"}])]});
/* le jumeau — le kapwing_sample de l'utilisateur, tel qu'il est sur V1 */
var PLAN={tr:"v1",id:"v1u3_0",label:"kapwing_sample",start:28.876,end:50.509,
  src:{job_id:"a54e"},srcIn:0};
var jum=P12(function(){return T.twinClip(PLAN,"a1",CS_USER)});
out.tc_jumeau=jum;
out.tc_meme_src=!!jum&&jum.src===PLAN.src;
out.tc_srcin=P12(function(){return T.twinClip(Object.assign({},PLAN,{srcIn:2}),"a1",[]).srcIn});
out.tc_doublon_chevauche=P12(function(){return T.twinClip(PLAN,"a1",
  [{tr:"a1",id:"x",start:40,end:60,src:{job_id:"a54e"}}])});
out.tc_doublon_cles_ordre=P12(function(){return T.twinClip(
  {tr:"v1",id:"p",start:0,end:5,src:{file_path:"f",job_id:"j"}},"a1",
  [{tr:"a1",id:"x",start:0,end:5,src:{job_id:"j",file_path:"f"}}])});
out.tc_autre_src=P12(function(){return T.twinClip(PLAN,"a1",
  [{tr:"a1",id:"x",start:40,end:60,src:{job_id:"autre"}}])!==null});
out.tc_autre_piste=P12(function(){return T.twinClip(PLAN,"a1",
  [{tr:"a3",id:"x",start:40,end:60,src:{job_id:"a54e"}}])!==null});
out.tc_bord_a_bord=P12(function(){return T.twinClip(PLAN,"a1",
  [{tr:"a1",id:"x",start:0,end:28.876,src:{job_id:"a54e"}}])!==null});
out.tc_sans_src=P12(function(){return T.twinClip({tr:"v1",id:"p",start:0,end:5},"a1",[])});
out.tc_sans_piste=P12(function(){return T.twinClip(PLAN,"",[])});
out.tc_id_pris=P12(function(){return T.twinClip(PLAN,"a1",
  [{tr:"a1",id:"a1u3_0",start:0,end:1,src:{job_id:"z"}}]).id});
out.tc_id_hors_prefixe=P12(function(){return T.twinClip(
  {tr:"v1",id:"c4",label:"x",start:0,end:1,src:{job_id:"z"}},"a1",[]).id});
out.tc_id_absent=P12(function(){return T.twinClip(
  {tr:"v1",label:"x",start:0,end:1,src:{job_id:"z"}},"a1",[]).id});
out.tc_clips_null=P12(function(){return T.twinClip(PLAN,"a1",null)!==null});
/* la decision, et sa phrase */
var LOCK_A1=function(t){return t==="a1"};
function TP(v,ts,cs,lk){return P12(function(){
  var o=T.twinPlan(PLAN,ts||T.DEFAULTS,cs||[],v,lk);
  return [o.motif,o.clip?o.clip.tr:null,o.note]})}
out.tp_pose=TP({has_audio:!0,dur:15.973,pourquoi:"mesure"});
out.tp_muet=TP({has_audio:!1,dur:15.973,pourquoi:"mesure"});
out.tp_non_sonde=TP({has_audio:!1,dur:0,pourquoi:"delai"});
/* NON-SONDABLE ≠ MUET : une MESURE sans flux ET sans duree — ffprobe n'a
   rien pu lire (fichier vide ou illisible : le 0 octet de la sauvegarde de
   l'utilisateur). Le conjoint est tp_muet, juste au-dessus : le meme
   verdict avec une duree > 0 reste « muet ». */
out.tp_non_sondable=TP({has_audio:!1,dur:0,pourquoi:"mesure"});
/* LES JETONS DE SORTIE SONT TRADUITS avant l'ecran, les quatre. */
out.tp_pourquoi=["delai","refus","erreur","sans-reseau"].map(function(pq){
  return TP({has_audio:!1,dur:0,pourquoi:pq})[2]});
out.tp_sans_verdict=TP(null);
out.tp_sans_piste=TP({has_audio:!0,dur:1,pourquoi:"mesure"},
  [{id:"v1",kind:"video"},{id:"s1",kind:"subs"}]);
out.tp_verrou=TP({has_audio:!0,dur:1,pourquoi:"mesure"},null,[],LOCK_A1);
out.tp_doublon=TP({has_audio:!0,dur:1,pourquoi:"mesure"},null,
  [{tr:"a1",id:"x",start:30,end:40,src:{job_id:"a54e"}}]);
out.tp_0409_vise_a1=TP({has_audio:!0,dur:1,pourquoi:"mesure"},TS_0409);
/* la duree rendue en prime */
out.sd=P12(function(){return [T.srcDurOr("video",0,{has_audio:!0,dur:15.973}),
  T.srcDurOr("video",21.233,{has_audio:!0,dur:15.973}),
  T.srcDurOr("video",-1,{dur:9}),T.srcDurOr("video",0,{has_audio:!0,dur:0}),
  T.srcDurOr("video",0,null),T.srcDurOr("image",0,{dur:9})]});
/* le cache */
out.ao_inconnu=P12(function(){return T.audioOf({job_id:"jamais"})});
var circ2={};circ2.self=circ2;
out.ao_illisible=P12(function(){return T.audioOf(circ2)});
out.as_ecrit=P12(function(){return T.audioSet({job_id:"c1"},
  {has_audio:!0,dur:"3.5",pourquoi:"mesure"})});
out.ao_relu=P12(function(){return T.audioOf({job_id:"c1"})});
out.ao_copie=P12(function(){var a=T.audioOf({job_id:"c1"});a.has_audio=!1;
  return T.audioOf({job_id:"c1"}).has_audio});
out.as_illisible=P12(function(){return T.audioSet(circ2,{has_audio:!0})});
out.af_oublie=P12(function(){return [T.audioForget({job_id:"c1"}),
  T.audioOf({job_id:"c1"}),T.audioForget({job_id:"c1"})]});
/* askAudio, sur le motif d'askDur */
var aaURL=null,aaAppels=0;
function FETCHA(rep){return function(u){aaURL=u;aaAppels++;return SYNC(rep)}}
function AA(src,o){var vus=[];o.done=function(v,pq){vus.push([v,pq])};
  try{T.askAudio(src,o)}catch(e){vus.push(["LEVE:"+e.name,"LEVE"])}
  return {n:vus.length,premier:vus[0]||null}}
aaURL=null;aaAppels=0;
var b1=AA({job_id:"h1"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:15.973,
  name:"k.mp4"})),timer:JAMAIS});
out.aa_mesure=b1.premier;
out.aa_une_seule_reponse=b1.n;
out.aa_url=aaURL;
out.aa_cache_apres=T.audioOf({job_id:"h1"});
/* LA SECONDE DEMANDE NE SONDE PAS : sortie « cache », zero appel — et le
   verdict rendu est celui de la PREMIERE, pas ce que le reseau dirait. */
aaAppels=0;
var b1b=AA({job_id:"h1"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!1,dur:0})),
  timer:JAMAIS});
out.aa_cache=b1b.premier;
out.aa_cache_zero_appel=aaAppels;
out.aa_muet=AA({job_id:"h2"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!1,dur:4})),
  timer:JAMAIS}).premier;
out.aa_sans_champ=AA({job_id:"h3"},{fetch:FETCHA(REP(!0,{ok:!0,dur:4})),
  timer:JAMAIS}).premier;
out.aa_http_refuse=AA({job_id:"h4"},{fetch:FETCHA(REP(!1,null)),timer:JAMAIS}).premier;
out.aa_json_illisible=AA({job_id:"h5"},{fetch:FETCHA(REP(!0,null)),timer:JAMAIS}).premier;
out.aa_reseau_leve=AA({job_id:"h6"},{fetch:function(){throw new Error("boom")},
  timer:JAMAIS}).premier;
out.aa_promesse_rejetee=AA({job_id:"h7"},{fetch:function(){return SYNCERR(new Error("ko"))},
  timer:JAMAIS}).premier;
aaAppels=0;out.aa_sans_reseau=AA({job_id:"h8"},{fetch:null,timer:JAMAIS}).premier;
out.aa_sans_reseau_zero_appel=aaAppels;
aaAppels=0;
var b2=AA({job_id:"h9"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:3})),
  timer:TOUT_DE_SUITE});
out.aa_delai_gagne=b2.premier;
out.aa_delai_une_seule_reponse=b2.n;
out.aa_delai_la_reponse_est_bien_passee=aaAppels;
/* TOUTE SORTIE ECRIT LE CACHE — c'est le verrou de recursion de l'ajout */
out.aa_cache_sur_sorties=[T.audioOf({job_id:"h9"}),T.audioOf({job_id:"h4"}),
  T.audioOf({job_id:"h6"}),T.audioOf({job_id:"h8"})];
aaAppels=0;
var vusC2=[];
try{T.askAudio(circ2,{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:9})),
  timer:JAMAIS,done:function(v,pq){vusC2.push([v,pq])}})}
catch(e){vusC2.push(["LEVE:"+e.name,"LEVE"])}
out.aa_src_illisible=vusC2[0]||null;
out.aa_src_illisible_zero_appel=aaAppels;
try{T.askAudio({job_id:"h10"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:3})),
  timer:JAMAIS});out.aa_sans_done="ok"}
catch(e){out.aa_sans_done="LEVE:"+e.name}
var msVuA=null;
T.askAudio({job_id:"h11"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:3})),
  timer:function(fn,ms){msVuA=ms},delai:"abc",done:JAMAIS});
out.aa_delai_illisible=msVuA;
var msVuA2=null;
T.askAudio({job_id:"h12"},{fetch:FETCHA(REP(!0,{ok:!0,has_audio:!0,dur:3})),
  timer:function(fn,ms){msVuA2=ms},delai:250,done:JAMAIS});
out.aa_delai_recu=msVuA2;
/* extract : le moteur du bouton, avec un `ask` bouchonne et un hote qui
   ENREGISTRE (pushHistory, setClips, setDirty, note). */
function EX(sel,o){var J={hist:0,clips:null,dirty:0,notes:[],asks:0};
  o=o||{};
  var h={tracks:o.tracks||T.DEFAULTS,clips:function(){return o.clips||[]},
    locked:o.locked||function(){return !1},
    pushHistory:function(){J.hist++},setClips:function(c){J.clips=c},
    setDirty:function(){J.dirty++},note:function(t){J.notes.push(String(t))},
    ask:o.ask||function(src,oo){J.asks++;oo.done(o.verdict||null,"bouchon")}};
  var r2;try{r2=T.extract(sel,h)}catch(e){r2="LEVE:"+e.name}
  return {r:r2,hist:J.hist,n:J.clips?J.clips.length:null,
    ids:J.clips?J.clips.map(function(c){return c.id}):null,dirty:J.dirty,
    notes:J.notes,asks:J.asks,
    jumeau:J.clips&&J.clips.length?J.clips[J.clips.length-1]:null}}
var V_OUI={has_audio:!0,dur:15.973,pourquoi:"mesure"};
var V_NON={has_audio:!1,dur:15.973,pourquoi:"mesure"};
out.ex_pose=EX(PLAN,{clips:[PLAN],verdict:V_OUI});
out.ex_muet=EX(PLAN,{clips:[PLAN],verdict:V_NON});
out.ex_non_sonde=EX(PLAN,{clips:[PLAN],verdict:{has_audio:!1,dur:0,pourquoi:"delai"}});
out.ex_non_sondable=EX(PLAN,{clips:[PLAN],verdict:{has_audio:!1,dur:0,pourquoi:"mesure"}});
out.ex_sans_verdict=EX(PLAN,{clips:[PLAN],verdict:null});
out.ex_doublon=EX(PLAN,{clips:[PLAN,{tr:"a1",id:"a1u3_0",start:28.876,end:50.509,
  src:{job_id:"a54e"}}],verdict:V_OUI});
out.ex_plan_parti=EX(PLAN,{clips:[],verdict:V_OUI});
out.ex_sans_piste=EX(PLAN,{clips:[PLAN],verdict:V_OUI,
  tracks:[{id:"v1",kind:"video"},{id:"s1",kind:"subs"}]});
out.ex_verrou=EX(PLAN,{clips:[PLAN],verdict:V_OUI,locked:LOCK_A1});
out.ex_sans_src=EX({tr:"v1",id:"p"},{clips:[],verdict:V_OUI});
/* UNE IMAGE posee sur une piste video (src:{image}, deux portes du bundle
   le font) : refus DIT avant toute sonde. */
out.ex_image=EX({tr:"v1",id:"i",label:"carton.png",src:{image:"carton.png"}},
  {clips:[],verdict:V_OUI});
/* LE PLAN A BOUGE entre le clic et la reponse : le jumeau prend les bornes
   FRAICHES (celles du thunk), pas celles du `sel` fige au clic. */
var PLAN_BOUGE=Object.assign({},PLAN,{start:10,end:20,srcIn:5});
out.ex_bouge=EX(PLAN,{clips:[PLAN_BOUGE],verdict:V_OUI});
var PLAN_V2=Object.assign({},PLAN,{tr:"v2",id:"v2u1_0"});
out.ex_v2=EX(PLAN_V2,{clips:[PLAN_V2],verdict:V_OUI});
/* le clic OUBLIE un verdict en cache qui n'est PAS une mesure et redemande ;
   il GARDE une mesure. */
T.audioSet({job_id:"e1"},{has_audio:!1,dur:0,pourquoi:"delai"});
var PL_E1=Object.assign({},PLAN,{src:{job_id:"e1"}});
var exR=EX(PL_E1,{clips:[PL_E1],ask:function(src,oo){
  out.ex_oubli_avant_ask=T.audioOf({job_id:"e1"});oo.done(V_OUI,"bouchon")}});
out.ex_oubli_pose=exR.n;
T.audioSet({job_id:"e2"},V_NON);
EX(Object.assign({},PLAN,{src:{job_id:"e2"}}),{clips:[],ask:function(src,oo){
  out.ex_mesure_gardee=T.audioOf({job_id:"e2"});oo.done(V_NON,"bouchon")}});
/* le bouton lui-meme */
out.eb_v1=P12(function(){var b=T.extractBtn(PLAN,{tracks:T.DEFAULTS});
  return [b.t,b.k,b.p.className,b.p.children,b.p["aria-label"]]});
out.eb_v2=P12(function(){var b=T.extractBtn(PLAN_V2,{tracks:T.DEFAULTS});
  return b?b.p.children:null});
out.eb_sans_piste=P12(function(){var b=T.extractBtn(PLAN,{tracks:[{id:"v1",kind:"video"}]});
  return b?b.p.children:null});
out.eb_nuls=P12(function(){return [T.extractBtn({tr:"a1",id:"a",src:{audio:"x"}},{tracks:T.DEFAULTS}),
  T.extractBtn({tr:"v1",id:"a"},{tracks:T.DEFAULTS}),T.extractBtn(null,{}),
  T.extractBtn({tr:"v1",id:"i",src:{image:"carton.png"}},{tracks:T.DEFAULTS})]});
out.eb_titre=P12(function(){return T.extractBtn(PLAN,{tracks:T.DEFAULTS}).p.title});
out.eb_clic=P12(function(){var J=[];var b=T.extractBtn(PLAN,{tracks:T.DEFAULTS,
  clips:function(){return [PLAN]},setClips:function(c){J.push(c.length)},
  pushHistory:function(){},ask:function(s2,oo){oo.done(V_OUI,"b")}});
  b.p.onClick();return J});
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
/* ══ ETAPE 4 — LA BARRE ET SON ONGLET (§2.1, §2.2, §2.4, §4.1, §4.4) ══════
   TOUT CE QUI SE MESURE ICI EST PUR. Le seul morceau a hooks (`ToolDock`)
   n'est pas jouable sous node — pas de `x` — et il est mince pour cette
   raison exacte : le plan, le cablage, l'onglet et la barre se jouent, lui
   se lit dans la source et dans le bundle livre. */
/* LE PLAN DU §2.4, tel que la couche le porte. Le banc le compare au tableau
   lu DANS design.md : ni la couche ni le banc ne le recopient deux fois. */
out.tb_plan = TBG(function () {
  return T.TB_PLAN.map(function (g) {
    return [g.g, g.t, g.suf || "", g.type,
    g.btns.map(function (b) { return b.l })]
  })
});
out.tb_plan_icones = TBG(function () {
  var a = [];
  T.TB_PLAN.forEach(function (g) {
    g.btns.forEach(function (b) { a.push(b.i) })
  });
  return a
});
out.tb_plan_groupes = TBG(function () {
  return T.TB_PLAN.map(function (g) { return g.g })
});
/* ── LA PERSISTANCE (§4.4), MAGASIN INJECTE ─────────────────────────────
   Un faux magasin : sous node il n'y a pas de localStorage, et une fonction
   qu'on ne peut pas jouer n'est pas mesuree. `lu` et `ecrit` disent QUELLE
   cle a ete touchee — sans eux la ligne serait vraie d'une fonction qui
   ecrirait ailleurs. */
function MAG(v) {
  var m = { v: v, lu: null, ecrit: null };
  m.getItem = function (k) { m.lu = k; return m.v };
  m.setItem = function (k, x) { m.ecrit = [k, x] };
  return m
}
var mgV = MAG("1");
out.tb_open_lit_1 = TBG(function () { return [T.tbOpenGet(mgV), mgV.lu] });
out.tb_open_lit_0 = TBG(function () { return T.tbOpenGet(MAG("0")) });
out.tb_open_lit_absent = TBG(function () { return T.tbOpenGet(MAG(null)) });
out.tb_open_lit_autre = TBG(function () { return T.tbOpenGet(MAG("oui")) });
var mgE = MAG(null);
out.tb_open_ecrit = TBG(function () {
  return [T.tbOpenSet(!0, mgE), mgE.ecrit]
});
var mgE2 = MAG(null);
out.tb_open_ecrit_faux = TBG(function () {
  return [T.tbOpenSet(!1, mgE2), mgE2.ecrit]
});
/* UN MAGASIN QUI LEVE — navigation privee, politique de site restrictive :
   la barre perd la memoire, elle ne casse pas. */
var mgL = {
  getItem: function () { throw new Error("refus") },
  setItem: function () { throw new Error("refus") }
};
out.tb_open_magasin_qui_leve = TBG(function () {
  return [T.tbOpenGet(mgL), T.tbOpenSet(!0, mgL)]
});
/* SANS MAGASIN : retombe sur celui du navigateur, absent ici — faux, pas
   une levee. C'est ce qui rend l'ecran servable si localStorage manque. */
out.tb_open_sans_magasin = TBG(function () { return T.tbOpenGet() });
out.tb_cle = T.TB_CLE_OPEN;
out.tb_id = T.TB_ID;
/* ── LE CABLAGE (§6) — sept cables, deux eteints-et-dits ────────────────── */
var CAB_TS = [{ id: "v1", kind: "video" }, { id: "a1", kind: "audio" },
{ id: "s1", kind: "subs" }];
/* CONSTRUCTIONS GARDEES, faute n°6 : un contrat ampute (un export
   renomme, par exemple) faisait lever CES lignes-ci au premier niveau du
   shim, node sortait en erreur, et le repli `d = {}` du harnais emportait
   DEUX CENT VINGT-HUIT lignes dont la quasi-totalite n'a rien a voir avec
   la barre. Avec `TBG`, le temoin est distinguable — jamais `null`, jamais
   `""` — et seules les lignes de la barre rougissent. */
var cabPlein = TBG(function () {
  return T.tbCablage({
    tracks: CAB_TS, onTracks: function () { }, onPick: function () { },
    wordAnim: "rebond", onWordAnim: function () { },
    textOn: !0, onText: function () { },
    onEmoji: function () { }, emojiBusy: !1, onProjets: function () { }
  })
});
out.tb_c_cles = TBG(function () { return Object.keys(cabPlein).sort() });
out.tb_c_eteints = TBG(function () {
  return Object.keys(cabPlein).filter(function (k) {
    return cabPlein[k].disabled === !0
  }).sort()
});
out.tb_c_actions = TBG(function () {
  return Object.keys(cabPlein).filter(function (k) {
    return typeof cabPlein[k].act === "function"
  }).sort()
});
/* CHAQUE ACTION CABLEE APPELLE LA BONNE CHOSE, et on mesure CE QU'ELLE
   TRANSMET — pas seulement qu'elle a ete appelee. */
out.tb_c_video = TBG(function () {
  var vu = null;
  T.tbCablage({
    tracks: CAB_TS, onTracks: function (ts) {
      vu = ts.map(function (t) { return t.id })
    }
  })["piste-video"].act();
  return vu
});
out.tb_c_audio = TBG(function () {
  var vu = null;
  T.tbCablage({
    tracks: CAB_TS, onTracks: function (ts) {
      vu = ts.map(function (t) { return t.id })
    }
  })["piste-audio"].act();
  return vu
});
out.tb_c_lier = TBG(function () {
  var vu = [];
  T.tbCablage({
    tracks: CAB_TS, onPick: function (id) { vu.push(id) }
  })["bibliotheque"].act();
  return vu
});
/* SANS PISTE VIDEO : eteint, aucune action, et un titre DIFFERENT de celui
   qui nomme la piste. Les deux titres sont rendus, la comparaison se fait
   en Python. */
var cabSansV = TBG(function () {
  return T.tbCablage({
    tracks: [{ id: "a1", kind: "audio" }, { id: "s1", kind: "subs" }],
    onPick: function () { }
  })
});
out.tb_c_lier_sans_video = TBG(function () {
  return [cabSansV["bibliotheque"].disabled, cabSansV["bibliotheque"].act]
});
out.tb_c_lier_titres = TBG(function () {
  return [cabPlein["bibliotheque"].title, cabSansV["bibliotheque"].title]
});
/* MOT — trois bascules ; celle qui vaut la valeur du projet est allumee. */
out.tb_c_mot = TBG(function () {
  return ["couleur", "rebond", "glow"].map(function (k) {
    return [cabPlein[k].toggle, cabPlein[k].active, cabPlein[k].disabled]
  })
});
out.tb_c_mot_clic = TBG(function () {
  var vu = [];
  var c = T.tbCablage({ onWordAnim: function (v) { vu.push(v) } });
  c["glow"].act(); c["couleur"].act();
  return vu
});
out.tb_c_mot_defaut = TBG(function () {
  var c = T.tbCablage({ onWordAnim: function () { } });
  return ["couleur", "rebond", "glow"].map(function (k) { return c[k].active })
});
/* LES TROIS CLES SORTENT DE LA TABLE DES ANIMATIONS, pas d'une seconde
   liste : si DZM_WORD_ANIMS change, le cablage change avec elle. */
out.tb_c_mot_cles = TBG(function () {
  return T.WORD_ANIMS.map(function (a) { return a.v })
});
/* Le titre de chaque bascule REPREND celui de la table, plus l'ecart dit. */
out.tb_c_mot_titre_reprend = TBG(function () {
  return T.WORD_ANIMS.map(function (a) {
    return cabPlein[a.v].title.indexOf(a.t) === 0
      && cabPlein[a.v].title.length > a.t.length
  })
});
/* TEXTE */
out.tb_c_texte = TBG(function () {
  return [cabPlein["texte"].toggle, cabPlein["texte"].active,
  cabPlein["texte"].disabled]
});
out.tb_c_texte_clic = TBG(function () {
  var n = 0;
  T.tbCablage({ onText: function () { n++ } })["texte"].act();
  return n
});
out.tb_c_texte_eteint = TBG(function () {
  return T.tbCablage({ textOn: !1, onText: function () { } })["texte"].active
});
/* EMOJI ET PROJETS — les deux qui avaient resiste a l'etape 4. Ils sont
   CABLES desormais : vivants avec leur hote, eteints sans lui, et deux
   phrases DIFFERENTES dans les deux cas. */
out.tb_c_vivants = TBG(function () {
  return ["emoji", "projets"].map(function (k) {
    return [cabPlein[k].disabled, typeof cabPlein[k].act, cabPlein[k].title]
  })
});
var cabSansHote = TBG(function () { return T.tbCablage({ tracks: CAB_TS }) });
out.tb_c_muets = TBG(function () {
  return ["emoji", "projets"].map(function (k) {
    return [cabSansHote[k].disabled, cabSansHote[k].act, cabSansHote[k].title]
  })
});
/* AUCUN TITRE NE NOMME PLUS UNE ETAPE A VENIR : c'etait la marque des deux
   boutons eteints, et `dzmTbEtape7` a ete RETIREE avec eux. */
out.tb_c_titres = TBG(function () {
  return Object.keys(cabPlein).sort().map(function (k) {
    return cabPlein[k].title })
});
/* SANS HOTE : un cablage vide n'allume RIEN et ne leve pas — c'est ce qui
   arriverait si la section du patcher perdait ses proprietes. */
var cabVide = TBG(function () { return T.tbCablage() });
out.tb_c_vide = TBG(function () {
  return [Object.keys(cabVide).length,
  Object.keys(cabVide).filter(function (k) {
    return cabVide[k].disabled !== !0 || cabVide[k].act !== null
  }).length]
});
/* LA FRAME SUIVANTE (§4.4) — `requestAnimationFrame` doit etre appelee SUR
   son objet : detachee puis appelee nue, elle leve « Illegal invocation »
   sous Blink et WebKit. Le faux navigateur mesure `this`, ce qu'aucune
   lecture de source ne saurait faire. */
out.tb_frame_appelle_sur_son_objet = TBG(function () {
  var vu = [], w = {};
  w.requestAnimationFrame = function (f) {
    vu.push(["raf", this === w, typeof f]); return 7
  };
  w.cancelAnimationFrame = function (i) { vu.push(["cancel", this === w, i]) };
  var stop = T.tbFrame(w, function () { });
  stop();
  return vu
});
/* SANS NAVIGATEUR (node, un rendu serveur) : un minuteur, et un annulateur
   qui annule vraiment — pas une levee. */
out.tb_frame_sans_navigateur = TBG(function () {
  var stop = T.tbFrame(null, function () { });
  return typeof stop === "function" ? (stop(), "ok") : "pas de fonction"
});
/* UNE MOITIE DE PAIRE NE SUFFIT PAS : sans `cancelAnimationFrame`, on
   retombe sur le minuteur — sinon l'annulateur ne pourrait rien annuler. */
out.tb_frame_moteur_incomplet = TBG(function () {
  var n = 0, w = { requestAnimationFrame: function () { n++; return 1 } };
  var stop = T.tbFrame(w, function () { });
  stop();
  return [n, "ok"]
});
/* ── L'ONGLET (§2.1) ────────────────────────────────────────────────────── */
var tabO = TBG(function () { return T.ToolTab({ open: !0 }) });
var tabF = TBG(function () { return T.ToolTab({ open: !1 }) });
out.tb_o_balise = TBG(function () { return [tabO.t, TBP(tabO, "type")] });
out.tb_o_classe = TBC(tabO);
out.tb_o_aria = TBG(function () {
  return [TBP(tabO, "aria-expanded"), TBP(tabF, "aria-expanded"),
  TBP(tabO, "aria-controls")]
});
out.tb_o_enfants = TBG(function () {
  return tabO.p.children.map(function (z) { return z.p.className })
});
out.tb_o_pastilles = TBG(function () {
  return tabO.p.children[0].p.children.map(function (z) {
    return z.p.className
  })
});
out.tb_o_libelle = TBG(function () { return tabO.p.children[1].p.children });
out.tb_o_chevrons = TBG(function () {
  return [tabO.p.children[2].p.children, tabF.p.children[2].p.children]
});
out.tb_o_titres = TBG(function () {
  return [TBP(tabO, "title"), TBP(tabF, "title")]
});
out.tb_o_clic = TBG(function () {
  var n = 0;
  T.ToolTab({ open: !1, onToggle: function () { n++ } }).p.onClick();
  return n
});
out.tb_o_clic_sans_action = TBG(function () {
  T.ToolTab({ open: !1 }).p.onClick(); return "ok"
});
out.tb_o_sans_couleur = TBG(function () {
  var j = JSON.stringify([tabO, tabF]);
  return j.indexOf("#") < 0 && j.indexOf("oklch") < 0
    && j.indexOf("var(--") < 0
});
/* ── LA BARRE (§2.2) ────────────────────────────────────────────────────── */
var barO = TBG(function () {
  return T.ToolBar({ open: !0, anim: !0, items: cabPlein })
});
var barF = TBG(function () {
  return T.ToolBar({ open: !1, anim: !0, items: cabPlein })
});
var barN = TBG(function () {
  return T.ToolBar({ open: !0, items: cabPlein })
});
out.tb_r_balise = TBG(function () {
  return [barO.t, TBP(barO, "id"), TBC(barO)]
});
out.tb_r_off = TBG(function () {
  return [TBP(barO, "data-off"), TBP(barF, "data-off")]
});
out.tb_r_noanim = TBG(function () {
  return [TBP(barO, "data-noanim"), TBP(barN, "data-noanim")]
});
out.tb_r_zones = TBG(function () {
  return barO.p.children.map(function (z) { return z.p.className })
});
/* LA POIGNEE : le glyphe `poignee` du §3, a 14 px (§2.2a), porte par un
   BOUTON depuis l'etape 5. `aria-hidden` a quitte le bouton — un nœud
   focusable cache des technologies d'assistance est une faute — et il est
   reste sur le GLYPHE, qui n'a rien a annoncer que le bouton ne dise. */
out.tb_r_grip = TBG(function () {
  var g = barO.p.children[0];
  return [g.t, TBP(g, "type"), g.p.children.p.width, g.p.children.p.viewBox,
  g.p.children.p.children.length, TBP(g, "aria-hidden"),
  TBP(g.p.children, "aria-hidden")]
});
out.tb_r_grip_aria = TBG(function () {
  return TBP(barO.p.children[0], "aria-label")
});
out.tb_r_grip_titre = TBG(function () {
  return TBP(barO.p.children[0], "title")
});
out.tb_r_groupes = TBG(function () {
  return barO.p.children[1].p.children.map(function (z) {
    return [z.p.className, TBP(z, "data-last")]
  })
});
out.tb_r_entetes = TBG(function () {
  return barO.p.children[1].p.children.map(function (z) {
    return z.p.children[0].p.children.map(function (y) {
      return [y.p.className, y.p.children]
    })
  })
});
out.tb_r_boutons = TBG(function () {
  var a = [];
  barO.p.children[1].p.children.forEach(function (z) {
    z.p.children[1].p.children.forEach(function (b) {
      a.push([b.p.className, b.p.children[1].p.children,
      b.p.disabled, ("aria-pressed" in b.p) ? b.p["aria-pressed"] : "ABSENT"])
    })
  });
  return a
});
out.tb_r_win = TBG(function () {
  return barO.p.children[2].p.children.map(function (z) {
    return [z.p.className, z.p.children, TBP(z, "disabled"), TBP(z, "aria-label")]
  })
});
out.tb_r_replier = TBG(function () {
  var n = 0;
  T.ToolBar({
    open: !0, items: cabPlein, onClose: function () { n++ }
  }).p.children[2].p.children[1].p.onClick();
  return n
});
out.tb_r_replier_sans_action = TBG(function () {
  T.ToolBar({ open: !0, items: cabPlein })
    .p.children[2].p.children[1].p.onClick();
  return "ok"
});
/* SANS CABLAGE : la barre se peint quand meme, cinq colonnes, tout eteint —
   elle ne depend pas de ce qu'on lui donne pour exister. */
out.tb_r_sans_items = TBG(function () {
  var b = T.ToolBar({ open: !0 });
  var n = 0;
  b.p.children[1].p.children.forEach(function (z) {
    z.p.children[1].p.children.forEach(function (x) { if (!x.p.disabled)n++ })
  });
  return [b.p.children[1].p.children.length, n]
});
out.tb_r_sans_couleur = TBG(function () {
  var j = JSON.stringify(barO);
  return j.indexOf("#") < 0 && j.indexOf("oklch") < 0
    && j.indexOf("var(--") < 0
});
/* ── CE QUE L'ETAPE 5 AJOUTE A LA BARRE (§4.2) ──────────────────────────── */
/* LE DECALAGE PASSE PAR DEUX LONGUEURS, `--tbx` et `--tby`, pas par une
   transformation ecrite en JS : `transform` est deja prise par le repli du
   §4.1 et les deux se seraient ecrasees. */
out.tb_r_deport = TBG(function () {
  var b = T.ToolBar({ open: !0, anim: !0, items: cabPlein,
    off: { dx: 42, dy: -13 }, drag: !0 });
  return [b.p.style["--tbx"], b.p.style["--tby"], TBP(b, "data-drag")]
});
out.tb_r_deport_defaut = TBG(function () {
  return [barO.p.style["--tbx"], barO.p.style["--tby"],
  TBP(barO, "data-drag")]
});
/* UN DECALAGE POURRI NE PEINT PAS `NaNpx` : la regle CSS serait annulee et
   la barre sauterait a son ancrage sans un mot. */
out.tb_r_deport_pourri = TBG(function () {
  var b = T.ToolBar({ open: !0, off: { dx: "a", dy: NaN } });
  var c = T.ToolBar({ open: !0, off: null });
  return [b.p.style["--tbx"], b.p.style["--tby"], c.p.style["--tbx"]]
});
out.tb_r_ref = TBG(function () {
  var o = { current: null };
  return T.ToolBar({ open: !0, barRef: o }).p.ref === o
});
out.tb_r_grip_saisit = TBG(function () {
  var n = 0, k = 0;
  var b = T.ToolBar({ open: !0, onGrab: function () { n++ },
    onGripKey: function () { k++ } });
  b.p.children[0].p.onPointerDown({});
  b.p.children[0].p.onKeyDown({});
  return [n, k]
});
/* `⌖` EST VIVANT ET N'EST JAMAIS ETEINT (§4.2 : « il ne doit jamais être
   masqué »). Il reste cliquable meme quand il n'a rien a recentrer : un
   filet de securite qui se desarme des que l'etat le croit inutile n'en est
   plus un. Deux titres, selon la situation. */
out.tb_r_recentrer = TBG(function () {
  var n = 0;
  T.ToolBar({ open: !0, off: { dx: 5, dy: 0 },
    onRecentrer: function () { n++ } })
    .p.children[2].p.children[0].p.onClick();
  return n
});
out.tb_r_recentrer_sans_action = TBG(function () {
  T.ToolBar({ open: !0 }).p.children[2].p.children[0].p.onClick();
  return "ok"
});
out.tb_r_recentrer_titres = TBG(function () {
  return [TBP(T.ToolBar({ open: !0, off: { dx: 5, dy: 0 } })
    .p.children[2].p.children[0], "title"),
  TBP(T.ToolBar({ open: !0, off: { dx: 0, dy: 0 } })
    .p.children[2].p.children[0], "title")]
});
/* ══ BARRE D'OUTILS — LE DEPORT (etape 5 du §9 ; §4.2 et la cle `offset`) ══
   LE CŒUR EST PUR, DONC IL SE JOUE ICI. C'est tout l'objet de sa forme : le
   §9 previent que « c'est la que se logent les regressions », et un bornage
   ne se mesure pas autrement que par des nombres.
   LE PLATEAU DE REFERENCE, une fois pour toutes :
     conteneur (100,50) 1000 x 600  ->  bords 100 / 50 / 1100 / 650
     barre     (114,140)  400 x  74  a decalage NUL (dx=dy=0)
   d'ou, avec la marge de 8 px du §4.2 :
     dx dans [-6, 578]   (114-6=108=100+8 ; 108+578+400=1086=1100-8+... )
     dy dans [-82, 428]
   Ces quatre bornes sont RECALCULEES par le banc plus bas a partir des
   memes nombres : elles ne sont pas recopiees depuis ce commentaire. */
var DEPB = { left: 114, top: 140, width: 400, height: 74 };
var DEPC = { left: 100, top: 50, width: 1000, height: 600 };
function DEP(o) {
  var p = { bar: DEPB, cont: DEPC, dx: 0, dy: 0, mx: 0, my: 0, aim: !1 };
  Object.keys(o || {}).forEach(function (k) { p[k] = o[k] });
  return T.tbBorne(p)
}
function DEPXY(o) { var v = TBG(function () { return DEP(o) });
  return (v && typeof v === "object") ? [v.dx, v.dy] : v }
function DEPA(o) { var v = TBG(function () { return DEP(o) });
  return (v && typeof v === "object") ? [v.dx, v.dy, v.ax, v.ay] : v }

/* LES DEUX DISTANCES DU §4.2, TELLES QUE LA COUCHE LES PORTE. Le banc les
   compare a celles qu'il LIT dans le handoff : ni la couche ni lui ne les
   retapent. */
out.tb_d_distances = TBG(function () {
  return [T.TB_MARGE, T.TB_AIMANT, T.TB_PAS, T.TB_PAS_FIN]
});
/* LES QUATRE BORNES, MESUREES PAR L'EXTREME : un deplacement enorme dans
   chaque sens, et on regarde ou la barre s'arrete. */
out.tb_d_bornes = TBG(function () {
  return [DEP({ mx: -9e4 }).dx, DEP({ mx: 9e4 }).dx,
  DEP({ my: -9e4 }).dy, DEP({ my: 9e4 }).dy]
});
/* LA MARGE DE 8 px, LUE SUR LES BORDS DE LA BARRE et pas sur le decalage :
   [gauche, haut, droite, bas] — les quatre ecarts au conteneur, une fois la
   barre poussee contre chaque bord. Les quatre doivent valoir la marge. */
out.tb_d_marge = TBG(function () {
  var g = DEPB.left + DEP({ mx: -9e4 }).dx - DEPC.left;
  var h = DEPB.top + DEP({ my: -9e4 }).dy - DEPC.top;
  var d = (DEPC.left + DEPC.width)
    - (DEPB.left + DEP({ mx: 9e4 }).dx + DEPB.width);
  var b = (DEPC.top + DEPC.height)
    - (DEPB.top + DEP({ my: 9e4 }).dy + DEPB.height);
  return [g, h, d, b]
});
/* AU MILIEU, RIEN NE SE PASSE : le decalage vaut le deplacement, et la barre
   n'est pas « bornee » par accident. */
out.tb_d_libre = DEPXY({ mx: 50, my: 30 });
out.tb_d_libre_est_borne = TBG(function () { return DEP({ mx: 50 }).borne });
/* LE DECALAGE COURANT S'AJOUTE AU DEPLACEMENT — c'est ce qui fait que la
   geometrie se fige au `pointerdown` et que le geste reste relatif. La barre
   passee est celle QUI PORTE DEJA ce decalage. */
out.tb_d_cumul = DEPXY({ bar: { left: 214, top: 190, width: 400, height: 74 },
  dx: 100, dy: 50, mx: 20, my: 10 });
/* ET L'ANCRAGE EST BIEN DEDUIT (`bar.left - dx`), pas pris pour l'ancrage.
   LA LIGNE DU DESSUS NE LE VOYAIT PAS : au milieu du conteneur les deux
   lectures donnent le meme nombre. Il faut un decalage courant NON NUL ET un
   geste qui atteigne une borne — sinon le mutant qui oublie le `- dx`
   survit, et il a survecu a la premiere campagne. */
out.tb_d_cumul_borne = DEPXY({
  bar: { left: 214, top: 190, width: 400, height: 74 },
  dx: 100, dy: 50, mx: 9e4, my: 9e4 });

/* ── LES CAS LIMITES QUE LE §4.2 REND MORTELS ─────────────────────────── */
/* UNE BARRE PLUS GRANDE QUE LE CONTENEUR : aucune position n'est licite. On
   rend le bord d'ORIGINE (gauche/haut), pas le bord oppose : c'est celui de
   la POIGNEE, sans laquelle plus rien ne se deplace. */
out.tb_d_barre_trop_large = TBG(function () {
  var b = { left: 114, top: 140, width: 2000, height: 900 };
  return [DEP({ bar: b, mx: 9e4, my: 9e4 }).dx,
  DEP({ bar: b, mx: 9e4, my: 9e4 }).dy,
  DEP({ bar: b, mx: -9e4, my: -9e4 }).dx]
});
/* ET LE BORD RENDU EST BIEN CELUI DE LA MARGE : la barre trop large commence
   a 8 px du bord gauche du conteneur, pas ailleurs. */
out.tb_d_barre_trop_large_bord = TBG(function () {
  var b = { left: 114, top: 140, width: 2000, height: 900 };
  return DEPB.left + DEP({ bar: b, mx: 9e4 }).dx - DEPC.left
});
/* UN CONTENEUR DE TAILLE NULLE — l'ecran cache, ou la mise en page pas
   encore calculee. LE BORNAGE EST SAUTE, le decalage passe tel quel : c'est
   la RESTAURATION qui en mourrait sinon, un decalage valide ecrase par un
   rectangle qui n'existe pas encore. */
out.tb_d_conteneur_nul = TBG(function () {
  var v = DEP({ cont: { left: 0, top: 0, width: 0, height: 0 },
    dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
out.tb_d_conteneur_hauteur_nulle = TBG(function () {
  var v = DEP({ cont: { left: 100, top: 50, width: 1000, height: 0 },
    dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
/* DES RECTANGLES ILLISIBLES : absents, `NaN`, champs manquants. Meme repli,
   et JAMAIS une levee — un `throw` ici tuerait le geste en cours. */
out.tb_d_rect_absent = TBG(function () {
  var v = DEP({ cont: null, dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
out.tb_d_rect_nan = TBG(function () {
  var v = DEP({ cont: { left: NaN, top: 50, width: 1000, height: 600 },
    dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
out.tb_d_barre_absente = TBG(function () {
  var v = DEP({ bar: void 0, dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
out.tb_d_barre_sans_champs = TBG(function () {
  var v = DEP({ bar: { left: 1, top: 2 }, dx: 300, dy: 200 });
  return [v.dx, v.dy, v.borne]
});
/* UN DEPLACEMENT ENORME MAIS FINI : borne. UN DEPLACEMENT NON FINI
   (`Infinity`, `NaN`, une chaine) : IGNORE — il ne vient d'aucun pointeur
   reel, et le prendre pour un deplacement aurait colle la barre a un bord
   sans qu'on ait bouge. Les deux ne se valent pas, et les deux sont mesures. */
out.tb_d_enorme = DEPXY({ mx: 1e9, my: -1e9 });
out.tb_d_infini = DEPXY({ mx: Infinity, my: -Infinity });
out.tb_d_nan = DEPXY({ mx: NaN, my: NaN });
out.tb_d_texte = DEPXY({ mx: "300", my: null });
/* AUCUNE SORTIE N'EST `NaN`, QUOI QU'ON ENTRE. Un `NaN` dans une translation
   CSS ne leve pas : il ANNULE la regle, et la barre saute a son ancrage. */
out.tb_d_jamais_nan = TBG(function () {
  var v = T.tbBorne({ bar: "x", cont: [], dx: "a", dy: {}, mx: NaN,
    my: void 0, ph: "z", aim: !0 });
  return [isFinite(v.dx), isFinite(v.dy), v.dx, v.dy, v.borne]
});
out.tb_d_sans_argument = TBG(function () {
  var v = T.tbBorne();
  return [v.dx, v.dy, v.ax, v.ay, v.borne]
});

/* ── L'AIMANTATION (§4.2 : « à moins de 12 px », AU RELACHEMENT) ───────── */
/* LES QUATRE BORDS. A 11 px du bord la barre s'y colle ; a 12 px, non — le
   §4.2 dit « à MOINS de 12 px », et le banc mesure les deux cotes du seuil. */
/* ON POSE UN DEPLACEMENT (`mx`), PAS UN DECALAGE (`dx`), ET LA DIFFERENCE
   N'EST PAS COSMETIQUE : `dx` est le decalage QUE PORTE DEJA le rectangle
   qu'on passe, donc le poser sans bouger la barre deplace l'ANCRAGE et,
   avec lui, les quatre bornes. Premiere ecriture de ces sondes, elle a fait
   rougir six lignes d'un coup — c'est le cœur qui avait raison. */
out.tb_d_aim_gauche = TBG(function () {
  return [DEPA({ mx: -6 + 11, aim: !0 }), DEPA({ mx: -6 + 12, aim: !0 })]
});
out.tb_d_aim_droite = TBG(function () {
  return [DEPA({ mx: 578 - 11, aim: !0 }), DEPA({ mx: 578 - 12, aim: !0 })]
});
/* `mx: 200` DANS LES DEUX LIGNES VERTICALES, ET CE N'EST PAS DU BRUIT : a
   decalage nul la barre est a 6 px du bord gauche et s'y colle, ce qui
   aurait fait passer une aimantation horizontale pour une verticale. */
out.tb_d_aim_haut = TBG(function () {
  return [DEPA({ mx: 200, my: -82 + 11, aim: !0 }),
  DEPA({ mx: 200, my: -82 + 12, aim: !0 })]
});
out.tb_d_aim_bas = TBG(function () {
  return [DEPA({ mx: 200, my: 428 - 11, aim: !0 }),
  DEPA({ mx: 200, my: 428 - 12, aim: !0 })]
});
/* L'AXE DE LA TETE DE LECTURE. Elle est a x=300 ; le bord GAUCHE de la barre
   y arrive pour dx = 300-114 = 186. On lache a 9 px : ca colle, et le nom du
   bord aimante le dit (`tg`). Le bord DROIT y arriverait pour dx = -214,
   HORS BORNES : il n'est pas candidat. */
out.tb_d_aim_tete = TBG(function () {
  return [DEPA({ ph: 300, mx: 186 + 9, aim: !0 }),
  DEPA({ ph: 300, mx: 186 + 13, aim: !0 })]
});
/* LE BORD DROIT DE LA BARRE S'AIMANTE AUSSI (§4.2 : « un bord de la barre »).
   Tete a x=800 : le bord droit y arrive pour dx = 800-400-114 = 286. */
out.tb_d_aim_tete_bord_droit = TBG(function () {
  return DEPA({ ph: 800, mx: 286 + 7, aim: !0 })
});
/* LA TETE HORS DU CONTENEUR — elle defile avec `.svm-scroll` et s'eloigne
   avec le zoom. AUCUN AIMANT, et surtout AUCUN DEPLACEMENT : la barre reste
   ou le doigt l'a lachee. C'est la difference entre ecarter un candidat et
   re-pincer apres coup. */
out.tb_d_aim_tete_hors = TBG(function () {
  return [DEPA({ ph: 5000, mx: 200, aim: !0 }),
  DEPA({ ph: -5000, mx: 200, aim: !0 })]
});
out.tb_d_aim_sans_tete = TBG(function () {
  return [DEPA({ ph: null, mx: 200, aim: !0 }),
  DEPA({ ph: NaN, mx: 200, aim: !0 })]
});
/* PENDANT LE GESTE, AUCUNE AIMANTATION (§4.2 : « Au relâchement »). Meme
   position, meme plateau : `aim` faux ne colle rien. */
out.tb_d_aim_seulement_au_relachement = TBG(function () {
  return [DEPA({ mx: -6 + 3, ph: 300, aim: !1 }),
  DEPA({ mx: -6 + 3, ph: 300, aim: !0 })]
});
/* LE PLUS PROCHE GAGNE, pas le premier venu : tete a 108 (donc dx=-6, le
   bord gauche lui-meme) contre le bord gauche — et un cas ou la tete est
   plus proche que le bord. */
out.tb_d_aim_le_plus_proche = TBG(function () {
  return DEPA({ ph: 114 + 4, mx: 2, aim: !0 })
});
/* UNE BARRE TROP LARGE N'AIMANTE RIEN : aucune borne n'est atteignable,
   donc aucun candidat ne l'est. */
out.tb_d_aim_barre_trop_large = TBG(function () {
  var v = DEP({ bar: { left: 114, top: 140, width: 2000, height: 900 },
    ph: 300, aim: !0 });
  return [v.dx, v.ax, v.ay]
});

/* ── L'UNION DES DEUX ZONES (§4.2) ────────────────────────────────────── */
out.tb_d_boite = TBG(function () {
  var b = T.tbBoite({ left: 0, top: 400, width: 1000, height: 300 },
    { left: 0, top: 100, width: 1000, height: 300 });
  return [b.left, b.top, b.width, b.height]
});
out.tb_d_boite_un_seul = TBG(function () {
  var a = T.tbBoite({ left: 5, top: 6, width: 7, height: 8 }, null);
  var b = T.tbBoite(null, { left: 5, top: 6, width: 7, height: 8 });
  var c = T.tbBoite({ left: 5, top: 6, width: 0, height: 8 },
    { left: 5, top: 6, width: 7, height: 8 });
  return [[a.left, a.top, a.width, a.height],
  [b.left, b.top, b.width, b.height], [c.width, c.height]]
});
out.tb_d_boite_aucun = TBG(function () {
  return [T.tbBoite(null, null), T.tbBoite({ left: NaN }, void 0)]
});
/* LA PINCE, NUE : le cas `mn > mx` rend `mn`, pas `mx`. */
out.tb_d_pince = TBG(function () {
  return [T.tbPince(5, 0, 10), T.tbPince(-3, 0, 10), T.tbPince(99, 0, 10),
  T.tbPince(5, 10, 0), T.tbPince(0, 0, 0)]
});

/* ── LA PERSISTANCE DU DECALAGE (§4.4) ────────────────────────────────── */
function STORE(v) {
  var lu = [], ecrit = [];
  return { lu: lu, ecrit: ecrit,
    getItem: function (k) { lu.push(k); return v },
    setItem: function (k, x) { ecrit.push([k, x]) } }
}
out.tb_d_cle = T.TB_CLE_OFF;
out.tb_d_classe_geste = T.TB_CL_DRAG;
out.tb_d_off_lit = TBG(function () {
  var s = STORE('{"dx":120,"dy":-40}');
  var v = T.tbOffGet(s);
  return [v.dx, v.dy, s.lu]
});
/* TOUT CE QUI N'EST PAS UN COUPLE DE NOMBRES RETOMBE SUR L'ORIGINE — c'est
   le filet de securite de la cle : un `dz_svm_tb_off` corrompu a la main ne
   peut pas envoyer la barre hors de l'ecran, il la ramene chez elle. */
out.tb_d_off_replis = TBG(function () {
  return [null, "", "pas du json", "120", "null", "[1,2]",
  '{"dx":"a","dy":true}', '{"dy":9}'].map(function (v) {
    var o = T.tbOffGet(STORE(v));
    return [o.dx, o.dy]
  })
});
out.tb_d_off_ecrit = TBG(function () {
  var s = STORE(null);
  var v = T.tbOffSet({ dx: 12, dy: -7 }, s);
  return [s.ecrit, v.dx, v.dy]
});
out.tb_d_off_ecrit_propre = TBG(function () {
  var s = STORE(null);
  var v = T.tbOffSet({ dx: NaN, dy: "x", ax: "g" }, s);
  return [s.ecrit, v.dx, v.dy]
});
/* UN MAGASIN QUI LEVE — navigation privee, politique de site restrictive.
   La barre perd la MEMOIRE, jamais le mouvement en cours : `tbOffSet` rend
   quand meme le decalage demande. */
out.tb_d_off_magasin_qui_leve = TBG(function () {
  var s = { getItem: function () { throw new Error("nope") },
    setItem: function () { throw new Error("nope") } };
  var g = T.tbOffGet(s), e = T.tbOffSet({ dx: 4, dy: 5 }, s);
  return [g.dx, g.dy, e.dx, e.dy]
});
out.tb_d_off_sans_magasin = TBG(function () {
  var g = T.tbOffGet(null), e = T.tbOffSet({ dx: 4, dy: 5 }, null);
  return [g.dx, g.dy, e.dx, e.dy]
});

/* ── LE GESTE (§4.2) — SUR LA FENETRE, ET RENDU ENTIEREMENT ───────────── */
function FWIN() {
  var L = {};
  return { L: L,
    addEventListener: function (t, f) { (L[t] = L[t] || []).push(f) },
    removeEventListener: function (t, f) {
      var a = L[t] || [], i = a.indexOf(f); if (i >= 0) a.splice(i, 1)
    },
    feu: function (t, ev) { (L[t] || []).slice().forEach(function (f) { f(ev) }) },
    n: function () {
      var k = Object.keys(L), i, n = 0;
      for (i = 0; i < k.length; i++) n += L[k[i]].length;
      return n
    },
    types: function () {
      return Object.keys(L).filter(function (k) { return L[k].length }).sort()
    } }
}
function FCORPS() {
  var tr = [];
  return { tr: tr, classList: {
    add: function (c) { tr.push("+" + c) },
    remove: function (c) { tr.push("-" + c) } } }
}
function GEO(o) {
  var g = { bar: DEPB, cont: DEPC, ph: null, dx: 0, dy: 0, px: 500, py: 300 };
  Object.keys(o || {}).forEach(function (k) { g[k] = o[k] });
  return g
}
/* LES TROIS ECOUTEURS SONT SUR LA FENETRE, ET LA CLASSE EST SUR LE CORPS.
   C'est ce qu'aucune lecture de source ne dirait : `pointercancel` est un
   ajout au §4.2, sans lequel un geste repris par le systeme laisserait
   `grabbing` colle sur tout le document. */
out.tb_d_saisie_pose = TBG(function () {
  var w = FWIN(), c = FCORPS();
  T.tbSaisie(w, c, GEO(), function () { });
  return [w.types(), w.n(), c.tr]
});
out.tb_d_saisie_deplace = TBG(function () {
  var w = FWIN(), c = FCORPS(), vu = [];
  T.tbSaisie(w, c, GEO(), function (r, f) { vu.push([r.dx, r.dy, f, r.ax]) });
  w.feu("pointermove", { clientX: 560, clientY: 330 });
  w.feu("pointermove", { clientX: 400, clientY: 300 });
  return [vu, w.n()]
});
/* LE RELACHEMENT AIMANTE, ET LUI SEUL. Le meme point, lache : le bord
   gauche est a 3 px, il colle ; en cours de geste, non. */
out.tb_d_saisie_relache_aimante = TBG(function () {
  var w = FWIN(), c = FCORPS(), vu = [];
  T.tbSaisie(w, c, GEO(), function (r, f) { vu.push([r.dx, f, r.ax]) });
  w.feu("pointermove", { clientX: 497, clientY: 300 });
  w.feu("pointerup", { clientX: 497, clientY: 300 });
  return [vu, w.types(), w.n(), c.tr]
});
/* `pointercancel` TERMINE COMME UN RELACHEMENT : tout est rendu. */
out.tb_d_saisie_annulee = TBG(function () {
  var w = FWIN(), c = FCORPS(), vu = [];
  T.tbSaisie(w, c, GEO(), function (r, f) { vu.push([r.dx, f]) });
  w.feu("pointermove", { clientX: 560, clientY: 300 });
  w.feu("pointercancel", { clientX: 560, clientY: 300 });
  return [vu, w.n(), c.tr]
});
/* UN RELACHEMENT SANS COORDONNEES LISIBLES (cela arrive sur
   `pointercancel`) NE VAUT PAS « deplacement nul » : la derniere position
   connue est gardee, sinon la barre sauterait a sa place d'avant le geste. */
out.tb_d_saisie_sans_coordonnees = TBG(function () {
  var w = FWIN(), c = FCORPS(), vu = [];
  T.tbSaisie(w, c, GEO(), function (r, f) { vu.push([r.dx, f]) });
  w.feu("pointermove", { clientX: 560, clientY: 300 });
  w.feu("pointercancel", {});
  return vu
});
/* APRES LA FIN, PLUS RIEN — meme si un evenement traine. */
out.tb_d_saisie_apres_la_fin = TBG(function () {
  var w = FWIN(), c = FCORPS(), n = 0, gardes = [];
  T.tbSaisie(w, c, GEO(), function () { n++ });
  Object.keys(w.L).forEach(function (k) { gardes = gardes.concat(w.L[k]) });
  w.feu("pointerup", { clientX: 500, clientY: 300 });
  var apres = n;
  gardes.forEach(function (f) { f({ clientX: 900, clientY: 900 }) });
  return [apres, n]
});
/* L'ANNULATEUR — c'est lui que le demontage du composant appelle. Il retire
   les trois ecouteurs ET la classe, et il ne fait rien deux fois. */
out.tb_d_saisie_annulateur = TBG(function () {
  var w = FWIN(), c = FCORPS();
  var fin = T.tbSaisie(w, c, GEO(), function () { });
  fin(); fin(); fin();
  return [w.n(), c.tr]
});
/* SANS FENETRE, SANS POSE, SANS GEOMETRIE : un annulateur inoffensif, jamais
   une levee — c'est le chemin du rendu serveur et celui d'une barre pas
   encore posee. */
out.tb_d_saisie_sans_rien = TBG(function () {
  var a = T.tbSaisie(null, null, GEO(), function () { });
  var b = T.tbSaisie(FWIN(), null, null, function () { });
  var c = T.tbSaisie(FWIN(), null, GEO(), null);
  a(); b(); c();
  return [typeof a, typeof b, typeof c]
});
/* SANS CORPS (ou avec un corps sans `classList`) le geste marche quand
   meme : le curseur est un confort, le deplacement est la fonction. */
out.tb_d_saisie_sans_corps = TBG(function () {
  var w = FWIN(), vu = [];
  T.tbSaisie(w, {}, GEO(), function (r, f) { vu.push([r.dx, f]) });
  w.feu("pointerup", { clientX: 560, clientY: 300 });
  return [vu, w.n()]
});

/* ── LE CLAVIER DE LA POIGNEE (§4.5) ──────────────────────────────────── */
out.tb_d_touche = TBG(function () {
  return ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].map(function (k) {
    var a = T.tbTouche(k, !1), b = T.tbTouche(k, !0);
    return [a.mx, a.my, b.mx, b.my]
  })
});
/* UNE TOUCHE QUI N'EST PAS UNE FLECHE NE DEPLACE RIEN — et `constructor`
   non plus : un acces nu a l'objet aurait rendu la fonction heritee, donc
   « vraie », et un pas `NaN`. */
out.tb_d_touche_inconnue = TBG(function () {
  return ["a", "Enter", " ", "constructor", "toString", "__proto__", "",
    void 0, null].map(function (k) { return T.tbTouche(k, !1) })
});

/* ── LA MESURE DES RECTANGLES, SUR UN FAUX ARBRE ──────────────────────── */
function TBCL(s) {
  var a = String(s).split(" ");
  return { contains: function (c) { return a.indexOf(c) >= 0 } }
}
function FARBRE(o) {
  o = o || {};
  var rTl = ("tl" in o) ? o.tl : { left: 0, top: 400, width: 1000, height: 300 };
  var rMid = ("mid" in o) ? o.mid : { left: 0, top: 100, width: 1000, height: 300 };
  var rBar = ("bar" in o) ? o.bar : { left: 14, top: 442, width: 400, height: 74 };
  var rPh = ("ph" in o) ? o.ph : { left: 300, top: 420, width: 1, height: 280 };
  var mid = rMid ? { classList: TBCL("svm-mid"),
    getBoundingClientRect: function () { return rMid } } : null;
  var ph = rPh ? { classList: TBCL("svm-phline"),
    getBoundingClientRect: function () { return rPh } } : null;
  var racine = { classList: TBCL("dzsvm svm-col"),
    querySelector: function (s) { return s === ".svm-mid" ? mid : null } };
  var tl = o.sansTl ? null : { classList: TBCL("svm-tl"), parentNode: racine,
    getBoundingClientRect: function () { return rTl },
    querySelector: function (s) { return s === ".svm-phline" ? ph : null } };
  var trans = { classList: TBCL("svm-trans"), parentNode: tl || racine };
  return { classList: TBCL("dzm-tbar"), parentNode: trans,
    getBoundingClientRect: function () { return rBar } }
}
/* LE CONTENEUR RETENU EST L'UNION DE `.svm-mid` ET `.svm-tl` — « la zone
   timeline + zone de prévisualisation » du §4.2, tout l'ecran SOUS la barre
   de titre. Le faux arbre reproduit la chaine mesuree dans le bundle :
   barre -> .svm-trans -> .svm-tl -> .dzsvm.svm-col, avec `.svm-mid` chez le
   meme parent que `.svm-tl`. */
out.tb_d_conteneur = TBG(function () {
  var b = T.tbConteneur(FARBRE());
  return [b.left, b.top, b.width, b.height]
});
/* SANS `.svm-mid` — le bornage se RESSERRE sur la timeline seule au lieu de
   disparaitre. Sans `.svm-tl`, il n'y a plus rien a borner et on le dit. */
out.tb_d_conteneur_sans_mid = TBG(function () {
  var b = T.tbConteneur(FARBRE({ mid: null }));
  return [b.left, b.top, b.width, b.height]
});
out.tb_d_conteneur_sans_timeline = TBG(function () {
  return T.tbConteneur(FARBRE({ sansTl: !0 }))
});
out.tb_d_conteneur_sans_noeud = TBG(function () {
  return [T.tbConteneur(null), T.tbConteneur({})]
});
/* L'AXE DE LA TETE : le MILIEU du filet d'1 px, pas son bord. */
out.tb_d_tete = TBG(function () { return T.tbTete(FARBRE()) });
out.tb_d_tete_absente = TBG(function () {
  return [T.tbTete(FARBRE({ ph: null })), T.tbTete(FARBRE({ sansTl: !0 })),
  T.tbTete(null)]
});
/* LA REMONTEE D'ARBRE EST BORNEE : un cycle de parents ne doit pas boucler
   sans fin. On en fabrique un. */
out.tb_d_ancetre_cycle = TBG(function () {
  var n = 0;
  var a = { classList: { contains: function () { n++; return !1 } } };
  a.parentNode = a;
  var perdu = T.tbAncetre(a, "svm-tl");
  var b = { classList: TBCL("x") };
  b.parentNode = b;
  return [perdu, n, T.tbAncetre(b, "x") === b]
});
/* TOUTE LA GEOMETRIE EN UNE FOIS, AU `pointerdown` — la discipline de
   `clipDown`, qui fige `rect` et `pxPerS` a la saisie. */
out.tb_d_geo = TBG(function () {
  var g = T.tbGeo(FARBRE(), { dx: 3, dy: 4 }, { clientX: 500, clientY: 600 });
  return [g.bar.left, g.bar.top, g.cont.left, g.cont.top, g.cont.width,
  g.cont.height, g.ph, g.dx, g.dy, g.px, g.py]
});
out.tb_d_geo_sans_barre = TBG(function () {
  return [T.tbGeo(null, { dx: 1, dy: 2 }, {}),
  T.tbGeo(FARBRE({ bar: { left: 0, top: 0, width: 0, height: 0 } }), {}, {})]
});
/* ── LE RECADRAGE : LA BARRE RENTRE QUAND LA FENETRE RETRECIT ──────────
   LE FAUX ARBRE DOIT ETRE COHERENT : le rectangle de la barre est celui
   qu'elle a AUJOURD'HUI, decalage compris. On pose donc un rectangle
   deplace de 5000 ET un decalage de 5000 — l'ancrage redevient (14,442). */
out.tb_d_recadre = TBG(function () {
  var el = FARBRE({ bar: { left: 14 + 5000, top: 442 + 5000,
    width: 400, height: 74 } });
  var v = T.tbRecadre(el, { dx: 5000, dy: 5000 });
  return v ? [v.dx, v.dy] : v
});
/* RIEN A FAIRE = `null`, ET C'EST DISTINCT DE `{dx:0,dy:0}` : un decalage
   deja licite ne provoque ni ecriture ni rendu. */
out.tb_d_recadre_rien_a_faire = TBG(function () {
  var el = FARBRE({ bar: { left: 114, top: 492, width: 400, height: 74 } });
  return T.tbRecadre(el, { dx: 100, dy: 50 })
});
/* UN CONTENEUR NON MESURABLE NE RAMENE PAS LA BARRE A L'ORIGINE — c'est la
   meme regression que `dzmTbRect` refuse plus haut, et elle se rejouerait
   ici : au chargement, la mise en page n'est pas toujours calculee. */
out.tb_d_recadre_sans_conteneur = TBG(function () {
  return [T.tbRecadre(FARBRE({ sansTl: !0 }), { dx: 5000, dy: 5000 }),
  T.tbRecadre(null, { dx: 5000, dy: 5000 })]
});
/* L'ECOUTE DU REDIMENSIONNEMENT : posee sur la fenetre, et rendue par
   l'annulateur que le demontage appelle. */
out.tb_d_veille = TBG(function () {
  var w = FWIN(), n = 0;
  var stop = T.tbVeille(w, function () { n++ });
  var pose = [w.types(), w.n()];
  w.feu("resize", {});
  stop();
  return [pose, n, w.n()]
});
out.tb_d_veille_sans_rien = TBG(function () {
  var a = T.tbVeille(null, function () { });
  var b = T.tbVeille(FWIN(), null);
  a(); b();
  return [typeof a, typeof b]
});
/* LE FIL COMPLET, DU FAUX ARBRE AU DECALAGE BORNE : c'est le seul endroit
   ou les trois morceaux (mesure, geste, cœur) tournent ensemble.
   Conteneur mesure : (0,100) 1000 x 600 -> bornes dx [-6, 578] pour une
   barre de 400 large posee a x=14. Un geste de +9000 px s'y arrete, et le
   bord droit de la barre tombe alors a 8 px du bord du conteneur (592+400 =
   992 = 1000-8). */
out.tb_d_bout_en_bout = TBG(function () {
  var el = FARBRE(), w = FWIN(), c = FCORPS(), vu = [];
  var g = T.tbGeo(el, { dx: 0, dy: 0 }, { clientX: 100, clientY: 500 });
  T.tbSaisie(w, c, g, function (r, f) { vu.push([r.dx, r.dy, f, r.ax]) });
  w.feu("pointermove", { clientX: 9100, clientY: 500 });
  w.feu("pointerup", { clientX: 9100, clientY: 500 });
  return [vu, w.n(), c.tr,
  el.getBoundingClientRect().left + vu[vu.length - 1][0]]
});

/* ══ ETAPE 7 — LE CABLAGE DU §6 ET SES TROIS EXIGENCES, JOUES ═══════════
   TOUT CE QUI SUIT EST JOUE, pas lu. Un FAUX ECRAN reproduit la semantique
   MESUREE du bundle livre : `pushHistory` n'empile que {clips, mixDb},
   `undo` ne repose que ces deux-la, `svmTracksSet` pousse l'historique PUIS
   ecrit les pistes, `subsStyleSet` n'empile RIEN. Les neuf actions sont
   declenchees une par une, et l'on LIT ce qu'`undo` rend.
   LA TETE DE LECTURE EST UN ACCESSEUR COMPTE, pose sur l'objet MEME que
   `dzmTbCablage` recoit : une action qui la lirait — donc qui calculerait
   une position au lieu de la deleguer — se verrait aussitot. */
function THEN(v){return {__t:1,v:v,
  then:function(f){var r=f(this.v);return (r&&r.__t)?r:THEN(r)},
  catch:function(){return this}}}
/* POURQUOI UN FAUX `fetch` SYNCHRONE : le shim imprime `out` d'un trait, et
   une vraie promesse aurait rendu la main APRES l'impression — les lignes
   emoji auraient mesure du vide, en restant vertes. Le double deroule la
   chaine sur-le-champ. Ce qu'il ne mesure pas est DIT : l'ordonnancement
   des microtaches, et le chemin de rejet. */
var HINTS7=[{t:1.25,word:"feu",emoji:"F",file:"feu",png:"/emo/feu.png"},
            {t:3.5,word:"lune",emoji:"L",file:"lune",png:"/emo/lune.png"}];
function ECRAN7(){
  var e={clips:[{id:"c0",tr:"v2"}],mixDb:-6,
    tracks:[{id:"v2",kind:"video"},{id:"v1",kind:"video"},
            {id:"a1",kind:"audio"},{id:"s1",kind:"subs"}],
    subsStyle:{wordAnim:"couleur"},textOn:!1,
    hist:[],panneaux:[],notes:[],reqs:[],projReq:0,attente:"jamais",
    lus:0,ecrits:0,_ph:3.5};
  e.push=function(){e.hist.push({clips:e.clips,mixDb:e.mixDb})};
  e.undo=function(){if(!e.hist.length)return !1;
    var h=e.hist.pop();e.clips=h.clips;e.mixDb=h.mixDb;return !0};
  return e}
/* LES PROPRIETES QUE R_M19 PASSE, une par une, chacune branchee sur le faux
   ecran ; puis `dzmTbHote`, la fonction du Dock, qui decide si `emoji` est
   vivant. C'est la chaine complete moins les hooks. */
function PROPS7(e,occupe){
  var o={tracks:e.tracks,
    onTracks:function(ts){e.push();e.tracks=ts},
    onPick:function(){e.panneaux.push(Array.prototype.slice.call(arguments))},
    wordAnim:e.subsStyle.wordAnim,
    onWordAnim:function(v){e.subsStyle={wordAnim:v}},
    textOn:e.textOn,onText:function(){e.textOn=!e.textOn},
    emojiSegs:[{start:0,end:2,text:"le feu et la lune"}],
    note:function(m){e.notes.push(m)},
    onEmojiAdd:function(cs){e.push();e.clips=e.clips.concat(cs)},
    onProjets:function(){e.projReq++}};
  var h=T.tbHote(o,function(){
    T.emojiGo({segments:o.emojiSegs,tracks:o.tracks,note:o.note,
      onAdd:o.onEmojiAdd,busy:occupe===!0,
      setBusy:function(v){e.attente=v},
      fetch:function(u,op){e.reqs.push([u,(op||{}).method]);
        return THEN({json:function(){return THEN({hints:HINTS7})}})}})},
    occupe===!0);
  Object.defineProperty(h,"ph",{
    get:function(){e.lus++;return e._ph},
    set:function(v){e.ecrits++;e._ph=v},enumerable:!0,configurable:!0});
  return h}
var TB7=["piste-video","piste-audio","bibliotheque","couleur","rebond",
  "glow","emoji","texte","projets"];
/* LE TABLEAU DES NEUF : ce que chaque action pousse, ce qu'elle touche, ce
   qu'`undo` rend, et si elle a lu ou ecrit la tete de lecture. */
out.tb7_par_bouton=TBG(function(){
  return TB7.map(function(k){
    var e=ECRAN7(),h=PROPS7(e,!1),c=T.tbCablage(h);
    var c0=e.clips,t0=e.tracks,s0=e.subsStyle,x0=e.textOn;
    var lus0=e.lus,ecr0=e.ecrits;
    c[k].act();
    var pousse=e.hist.length;
    var touche=[e.clips!==c0,e.tracks!==t0,e.subsStyle!==s0,e.textOn!==x0,
                e.panneaux.length,e.projReq];
    var rendu=e.undo();
    return [k,pousse,touche,rendu,
      [e.clips===c0,e.tracks===t0,e.subsStyle===s0,e.textOn===x0],
      [e.lus-lus0,e.ecrits-ecr0]]})});
/* AUCUNE DES NEUF NE LIT NI N'ECRIT LA TETE DE LECTURE — le cablage
   lui-meme compris : le compteur part AVANT `tbCablage`. */
out.tb7_la_tete_de_lecture=TBG(function(){
  var e=ECRAN7(),h=PROPS7(e,!1);
  var l0=e.lus,r0=e.ecrits;
  var c=T.tbCablage(h),n=0;
  TB7.forEach(function(k){if(typeof c[k].act==="function"){c[k].act();n++}});
  return [n,e.lus-l0,e.ecrits-r0,e._ph]});
/* LA TABLE DES EFFETS, ET LES PHRASES QU'ELLE ECRIT. */
out.tb7_table=TBG(function(){
  return Object.keys(T.TB_EFFETS).sort().map(function(k){
    return [k,T.TB_EFFETS[k].h,T.TB_EFFETS[k].via,T.TB_EFFETS[k].tete]})});
out.tb7_phrases=TBG(function(){
  return TB7.map(function(k){return T.tbUndo(k)})});
out.tb7_undo_inconnu=TBG(function(){
  return [T.tbUndo("rien-de-tel"),T.tbUndo(),T.tbUndo("__proto__")]});
/* CHAQUE TITRE CABLE SE TERMINE PAR SA PHRASE, et il reste du texte devant :
   sans ce second terme, un titre REDUIT a la phrase passerait. */
var CAB7=TBG(function(){return T.tbCablage(PROPS7(ECRAN7(),!1))});
out.tb7_titres_finissent_par_la_phrase=TBG(function(){
  return TB7.map(function(k){
    var t=String(CAB7[k].title||""),u=T.tbUndo(k);
    return [u.length>40,t.slice(-u.length)===u,t.length-u.length>40]})});
/* L'ACTION EMOJI, JOUEE DE BOUT EN BOUT : une requete, deux clips poses sur
   la piste d'overlay la plus haute, aux dates des mots, l'historique pousse
   AVANT, l'attente rallumee puis eteinte, une note. */
out.tb7_emoji_pose_les_clips=TBG(function(){
  var e=ECRAN7(),c=T.tbCablage(PROPS7(e,!1));
  c["emoji"].act();
  return [e.reqs,e.clips.length,
    e.clips.slice(1).map(function(k){
      return [k.tr,k.start,Math.round((k.end-k.start)*100)/100]}),
    e.hist.length,e.attente,e.notes.length,
    e.undo(),e.clips.length]});
/* LES QUATRE REFUS, chacun son jeton : un `return` nu les aurait rendus
   indiscernables, et la ligne serait restee vraie d'une fonction muette. */
out.tb7_emoji_refus=TBG(function(){
  var n=[];
  function no(m){n.push(m)}
  return [T.emojiGo({busy:!0,note:no}),
    T.emojiGo({segments:[],note:no}),
    T.emojiGo({segments:[1],note:no}),
    T.emojiGo({segments:[1],onAdd:function(){},note:no,fetch:null}),
    n.length]});
/* UNE REPONSE SANS INDICE NE POUSSE RIEN : ni historique, ni clip. */
out.tb7_emoji_sans_indice=TBG(function(){
  var e=ECRAN7(),n=[];
  T.emojiGo({segments:[1],tracks:e.tracks,note:function(m){n.push(m)},
    onAdd:function(cs){e.push();e.clips=e.clips.concat(cs)},
    busy:!1,setBusy:function(v){e.attente=v},
    fetch:function(){return THEN({json:function(){
      return THEN({hints:[]})}})}});
  return [e.hist.length,e.clips.length,n.length,
    n[0].indexOf("Aucun mot-cl")===0,e.attente]});
/* PENDANT L'ATTENTE : eteint, sans action, et un titre QUI DIFFERE. */
out.tb7_emoji_attente=TBG(function(){
  var c=T.tbCablage(PROPS7(ECRAN7(),!0));
  return [c["emoji"].disabled,c["emoji"].act,c["emoji"].title]});
/* `dzmTbHote` — LA DECISION DU DOCK, jouee : sans receveur, pas d'action.
   ON REND LE GENRE, JAMAIS LA VALEUR, et c'est une CORRECTION mesuree par
   mutation : `JSON.stringify` remplace une FONCTION par `null` dans un
   tableau. La premiere ecriture rendait `h.onEmoji` tel quel, et le mutant
   qui allumait `emoji` SANS receveur passait — la fonction posee a tort
   arrivait ici sous la forme `null`, exactement la valeur attendue.
   Faute n°2, forme « deux resultats qui se ressemblent ». */
function GENRE7(v){return v===null?"null":typeof v}
out.tb7_hote=TBG(function(){
  var f=function(){};
  return [GENRE7(T.tbHote({tracks:[]},f,!1).onEmoji),
    GENRE7(T.tbHote({tracks:[],onEmojiAdd:f},f,!1).onEmoji),
    GENRE7(T.tbHote({tracks:[],onEmojiAdd:f},null,!1).onEmoji),
    T.tbHote({tracks:[],onEmojiAdd:f},f,!1).emojiBusy,
    T.tbHote({tracks:[],onEmojiAdd:f},f,!0).emojiBusy,
    T.tbHote().emojiBusy]});
/* IL COPIE, IL NE MUTE PAS : l'objet vient du bundle, qui le reconstruit a
   chaque rendu ; le muter ferait fuir l'attente d'un rendu au suivant. */
out.tb7_hote_ne_mute_pas=TBG(function(){
  var o={tracks:[1],onEmojiAdd:function(){}};
  var h=T.tbHote(o,function(){},!0);
  return [("onEmoji" in o),("emojiBusy" in o),h!==o,h.tracks===o.tracks,
    Object.keys(h).length-Object.keys(o).length]});
/* PROJETS — il OUVRE, et rien d'autre : deux clics, deux demandes, aucune
   ecriture de timeline, aucun pas d'historique, aucun projet ouvert. */
out.tb7_projets=TBG(function(){
  var e=ECRAN7(),c=T.tbCablage(PROPS7(e,!1));
  c["projets"].act();c["projets"].act();
  return [e.projReq,e.hist.length,e.clips.length,e.panneaux.length,
    e.lus,e.ecrits,e.notes.length]});
/* LIER — il ne transmet QUE la piste, jamais un temps : c'est ce qui laisse
   le placement (et donc « aimanter ») entierement a l'action existante. */
out.tb7_lier_ne_transmet_que_la_piste=TBG(function(){
  var e=ECRAN7(),c=T.tbCablage(PROPS7(e,!1));
  c["bibliotheque"].act();
  return [e.panneaux,e.lus,e.ecrits]});

/* ══ ETAPE 6 (§5) — LE BANDEAU REDISTRIBUE ═══════════════════════════════
   §5.1 — LA PLACE RENDUE : le banc la RECALCULE, il ne recopie pas le
   chiffre de la couche. Le protocole (6,0 px par caractere, boite
   `border-box`, intervalle compte avec le noeud) est ecrit dans la couche ;
   ici on verifie qu'il donne bien ce qu'il annonce, et que la table decrit
   NEUF controles — une ligne perdue rendrait un total plus petit sans
   qu'aucune ligne ne le dise. */
out.bd_retire=TBG(function(){var r=T.bdRetire();return [r.px,r.n,r.nb]});
out.bd_px_un=TBG(function(){
  return [T.bdPx({lbl:"texte",pad:16}),T.bdPx({lbl:"x",px:18,pad:99}),
    T.bdPx(null)]});
out.bd_libelles=TBG(function(){
  return T.bdRetires.map(function(e){return e.lbl})});
out.bd_ctl=TBG(function(){
  return T.bdRetires.filter(function(e){return e.ctl===!0})
    .map(function(e){return e.id}).sort()});
/* §5.3 — LE PLAN, PUR. Plateau de reference, une fois pour toutes :
     reste 600 (rang 0) · hints 100 (rang 1) · coupe 140 (2) · metre 80 (3)
     tctotal 40 (4)          -> besoin PLEIN = 960 */
var BDB=[{id:"reste",rang:0,px:600},{id:"hints",rang:1,px:100},
  {id:"coupe",rang:2,px:140},{id:"metre",rang:3,px:80},
  {id:"tctotal",rang:4,px:40}];
function BDP(w){var q=T.bdPlan(w,BDB);
  return [q.niveau,q.off.join("+"),q.besoin,q.ok]}
out.bd_plan_large=TBG(function(){return BDP(1200)});
out.bd_plan_juste=TBG(function(){return BDP(960)});
out.bd_plan_1=TBG(function(){return BDP(900)});
out.bd_plan_2=TBG(function(){return BDP(800)});
out.bd_plan_3=TBG(function(){return BDP(700)});
out.bd_plan_4=TBG(function(){return BDP(620)});
out.bd_plan_impossible=TBG(function(){return BDP(100)});
/* MONOTONE : le niveau ne baisse jamais quand la largeur baisse, et ce qui
   tombe a une largeur tombe encore a toutes les largeurs plus petites. Sans
   cette seconde clause, un plan pourrait rendre le meme NIVEAU en changeant
   ce qu'il sacrifie — la barre clignoterait au redimensionnement. */
out.bd_plan_monotone=TBG(function(){
  var prev=-1,niv=1,inc=1,dern=[],w,q,i;
  for(w=1300;w>=0;w-=10){
    q=T.bdPlan(w,BDB);
    if(q.niveau<prev)niv=0;
    for(i=0;i<dern.length;i++)if(q.off.indexOf(dern[i])<0)inc=0;
    dern=q.off;prev=q.niveau}
  return [niv,inc,prev]});
/* LA GARANTIE DU §5.3, MESUREE SUR 187 LARGEURS : a chacune, ou bien le plan
   TIENT, ou bien il a tout sacrifie ET LE DIT (`ok:!1`). Rien entre les deux
   — c'est ce qui interdit un bandeau qui deborde en silence. `menteur`
   compte les fois ou `ok` ne dit pas la verite de `besoin<=dispo`. */
out.bd_plan_garantie=TBG(function(){
  var w,bon=1,menteur=0,q;
  for(w=0;w<=1300;w+=7){
    q=T.bdPlan(w,BDB);
    if(q.ok!==(q.besoin<=w))menteur++;
    if(!q.ok&&q.off.length!==4)bon=0}
  return [bon,menteur]});
/* LES RANGS 0 NE TOMBENT JAMAIS, ET LA TABLE DE L'APPELANT N'EST PAS MUTEE :
   le tri porte sur une copie. Sans elle, l'ordre du §5.3 serait reordonne
   dans le tableau que l'appelant garde, et le second appel ne dirait plus la
   meme chose que le premier. */
out.bd_plan_rang0=TBG(function(){
  var t=[{id:"a",rang:0,px:500},{id:"b",rang:2,px:10},{id:"c",rang:1,px:10}];
  var avant=t.map(function(e){return e.id}).join("");
  var q=T.bdPlan(0,t);
  return [q.off.join("+"),avant,t.map(function(e){return e.id}).join("")]});
/* DEUX BLOCS DE MEME RANG tombent dans l'ordre de la TABLE, pas dans celui
   que le moteur de tri choisit — un tri instable rendrait l'ecran different
   d'un navigateur a l'autre. */
out.bd_plan_egalite=TBG(function(){
  var t=[{id:"z",rang:1,px:10},{id:"y",rang:1,px:10}];
  return T.bdPlan(0,t).off.join("+")});
/* ENTREES POURRIES : ni levee, ni NaN, ni negatif. */
out.bd_plan_pourri=TBG(function(){
  var a=T.bdPlan(null,null),b=T.bdPlan("x",[{id:"q",rang:1,px:-5}]);
  return [a.niveau,a.off.length,a.besoin,a.ok,b.besoin,b.off.join("+")]});
/* LA TABLE DES RANGS DE LA COUCHE — l'ordre du §5.3, lu la ou il est ecrit. */
out.bd_rangs=TBG(function(){
  return T.BD_RANGS.map(function(r){return r.id+":"+r.rang+":"+r.sel})});
out.bd_constantes=TBG(function(){
  return [T.BD_PX_ICONE,T.BD_PX_CAR,T.BD_GAP,T.BD_PX_SEP,T.BD_ATTR,
    T.BD_SEP,T.BD_HORS]});
/* ── L'HOTE DU §5.3, JOUE SUR UN FAUX BANDEAU ────────────────────────────
   IL TOUCHE LE DOM, DONC IL EST « DETTE NAVIGATEUR » — sauf que le DOM qu'il
   touche tient en huit methodes, et un faux les rend toutes. Ce qui reste
   dehors est la mise en page reelle (les largeurs viennent d'ici, pas d'un
   moteur de rendu) ; ce qui entre est TOUT le reste : l'exclusion des noeuds
   hors flux, le compte des intervalles et des filets, la memoire des blocs
   deja sacrifies, l'ecriture de l'attribut, et l'IDEMPOTENCE — mesurer apres
   avoir applique doit rendre le meme verdict, sinon la barre clignote.
   LE PLATEAU, une fois pour toutes (largeurs en px) :
     hors flux : onglet 90 · barre 600 · liste des projets 0
     en flux   : timecode 120 (dont durée totale 40) · transport 160 ·
                 annuler/rétablir 70 · outils+sous-titres 280 · métering 100 ·
                 zoom 110 · durée 80 · rappels 200 · « ? » 30
     9 enfants en flux -> 8 intervalles de 12 = 96 ; 4 filets de 13 = 52
     somme 1150 + 96 + 52 = 1298 px de BESOIN PLEIN. */
function BDEL(cls,w){
  var e={cls:String(cls),offsetWidth:w,scrollWidth:w,children:[],_a:{}};
  e.matches=function(sel){
    var l=String(sel).split(","),i,t;
    for(i=0;i<l.length;i++){
      t=l[i].trim();
      if(t.charAt(0)===".")t=t.slice(1);
      if((" "+e.cls+" ").indexOf(" "+t+" ")>=0)return !0}
    return !1};
  e.getAttribute=function(k){
    return Object.prototype.hasOwnProperty.call(e._a,k)?e._a[k]:null};
  e.setAttribute=function(k,v){e._a[k]=v};
  e.removeAttribute=function(k){delete e._a[k]};
  e.querySelector=function(sel){
    var i,r;
    for(i=0;i<e.children.length;i++){
      if(e.children[i].matches(sel))return e.children[i];
      r=e.children[i].querySelector(sel);
      if(r)return r}
    return null};
  e.querySelectorAll=function(sel){
    var out=[],i;
    for(i=0;i<e.children.length;i++){
      if(e.children[i].matches(sel))out.push(e.children[i]);
      out=out.concat(e.children[i].querySelectorAll(sel))}
    return out};
  return e}
function BDBAND(w){
  var b=BDEL("svm-trans",0);
  b.clientWidth=w;
  var tc=BDEL("svm-tcmain",120);
  tc.children=[BDEL("svm-tctotal",40)];
  b.children=[BDEL("dzm-tbtab",90),BDEL("dzm-tbar",600),tc,
    BDEL("svm-transbtns",160),BDEL("svm-transbtns",70),
    BDEL("svm-toolchips",280),BDEL("svm-meterslot",100),
    BDEL("svm-zoom",110),BDEL("dzm-durctl",80),
    BDEL("svm-hints",200),BDEL("dzm-proj",0),BDEL("svm-tbtn",30)];
  return b}
/* CE QUE LA FEUILLE FERAIT DU VERDICT — masquer, ou reduire les trois chips
   de coupe a leurs glyphes (280 -> 63, soit 3 x 21 px, la constante de la
   couche ET de la feuille). Sans cette moitie-la, l'idempotence ne se
   mesurerait pas : c'est justement quand le bandeau a CHANGE que le second
   tour doit dire la meme chose. */
function BDCSS(b){
  var off=" "+(b.getAttribute("data-bdoff")||"")+" ";
  function L(cls,v){
    var e=b.querySelector("."+cls);
    if(e){e.offsetWidth=v;e.scrollWidth=v}}
  L("svm-hints",off.indexOf(" hints ")>=0?0:200);
  L("svm-toolchips",off.indexOf(" coupe ")>=0?63:280);
  L("svm-meterslot",off.indexOf(" metre ")>=0?0:100);
  L("svm-tctotal",off.indexOf(" tctotal ")>=0?0:40);
  L("svm-tcmain",off.indexOf(" tctotal ")>=0?80:120);
  return b}
out.bd_hote=TBG(function(){
  var mem={},b=BDBAND(1400),r1,r2,r3,r4;
  r1=T.bdTour(b,mem);BDCSS(b);
  b.clientWidth=1100;r2=T.bdTour(b,mem);BDCSS(b);
  b.clientWidth=1100;r3=T.bdTour(b,mem);BDCSS(b);
  b.clientWidth=1150;r4=T.bdTour(b,mem);BDCSS(b);
  return [r1.mesure.plein,r1.plan.off.join("+"),r1.mesure.dispo,
    r2.mesure.plein,r2.plan.off.join("+"),
    r3.mesure.plein,r3.plan.off.join("+"),
    r4.mesure.plein,r4.plan.off.join("+"),
    b.getAttribute("data-bdoff")]});
/* LES NOEUDS HORS FLUX NE COUTENT RIEN — l'onglet, la barre et la liste des
   projets montee nue. MESURE PLUTOT QU'AFFIRMATION : le meme bandeau, prive
   de ces trois noeuds, doit demander EXACTEMENT la meme largeur. Sans le
   filtre, le premier vaudrait 2024 et le second 1298. */
out.bd_hors_flux=TBG(function(){
  var a=BDBAND(1400),b=BDBAND(1400);
  b.children=b.children.filter(function(e){
    return !e.matches(".dzm-tbtab,.dzm-tbar,.dzm-proj")});
  return [T.bdMesure(a,{}).plein,T.bdMesure(b,{}).plein]});
/* LES QUATRE BLOCS, LEURS LARGEURS ET LE RESTE : la somme doit redonner le
   besoin plein, sinon `dzmBdPlan` retirerait de la place qui n'existe pas. */
out.bd_blocs=TBG(function(){
  var q=T.bdMesure(BDBAND(1400),{});
  var t=0,i;for(i=0;i<q.blocs.length;i++)t+=q.blocs[i].px;
  return [q.blocs.map(function(x){return x.id+":"+x.px}),t,q.plein]});
/* SANS BANDEAU : `null`, jamais une levee. L'ecran peut monter avant que la
   mise en page existe. */
out.bd_hote_sans_bandeau=TBG(function(){
  return [T.bdMesure(null,{}),T.bdTour(null,{}),T.bdPose(null,{off:[]}),
    T.bdMesure({},{})]});

/* ══ ETAPE 8 — LE `tabindex` ROVING, SON CŒUR PUR (§4.5) ═════════════════
   « index courant + direction + liste des boutons actifs -> index suivant. »
   C'est la seule facon de mesurer la traversee des groupes sans navigateur :
   la fonction ne touche ni au DOM ni au focus, elle ne rend qu'un nombre. */
function RV(c,d,a){return T.tbRove(c,d,a)}
var A5=[!0,!0,!0,!0,!0];
/* AVANCE ET BOUCLE : le dernier -> le premier. Sans la boucle, le dernier
   bouton serait un cul-de-sac au clavier alors qu'il ne l'est pas a la
   souris. */
out.tb8_rove_avance=TBG(function(){
  return [RV(0,1,A5),RV(1,1,A5),RV(3,1,A5),RV(4,1,A5)]});
out.tb8_rove_recule=TBG(function(){
  return [RV(4,-1,A5),RV(1,-1,A5),RV(0,-1,A5)]});
/* LES ETEINTS SONT SAUTES, DANS LES DEUX SENS — un bouton `disabled` ne
   prend pas le focus, s'arreter dessus perdrait le parcours. */
var AD=[!0,!1,!1,!0,!1];
out.tb8_rove_saute_eteints=TBG(function(){
  return [RV(0,1,AD),RV(3,1,AD),RV(0,-1,AD),RV(3,-1,AD)]});
/* UN SEUL ACTIF : toute direction y revient, et la boucle TERMINE. */
out.tb8_rove_un_seul=TBG(function(){
  var a=[!1,!1,!0,!1];
  return [RV(2,1,a),RV(2,-1,a),RV(0,1,a)]});
/* AUCUN ACTIF, LISTE VIDE, LISTE ABSENTE : -1, jamais une levee ni une
   boucle infinie. -1 veut dire « aucun `tabindex=0` a poser ». */
out.tb8_rove_rien=TBG(function(){
  return [RV(0,1,[!1,!1]),RV(0,-1,[!1,!1]),RV(0,1,[]),RV(0,1,null),
    RV(0,1,void 0)]});
/* HORS BORNES : on repart du bord AMONT DU SENS DE MARCHE — avant le
   premier pour +1, apres le dernier pour -1. C'est ce qui fait que
   `tbRove(-1,1,a)` rend le PREMIER actif, et que « aller au suivant » et
   « aller au premier » sont la meme fonction (§4.1, focus a l'ouverture).
   `null` COERCE A ZERO et n'est donc PAS hors bornes ; `void 0` l'est.
   Les deux sont mesures pour que la coercion soit epinglee, pas subie. */
out.tb8_rove_hors_bornes=TBG(function(){
  return [RV(-1,1,A5),RV(99,1,A5),RV(NaN,1,A5),RV(1.5,1,A5),RV("2",1,A5),
    RV(void 0,1,A5),RV(null,1,A5),
    RV(-1,-1,A5),RV(99,-1,A5),RV(void 0,-1,A5),RV(null,-1,A5)]});
/* LA DIRECTION : seul un nombre NEGATIF recule ; tout le reste avance. */
out.tb8_rove_dir_valeurs=TBG(function(){
  return [RV(0,-5,A5),RV(0,0,A5),RV(0,"x",A5),RV(0,null,A5)]});
/* PARCOURS COMPLET : n pas rendent les n index, chacun UNE fois. C'est ce
   qui prouve que le pas vaut ±1 et qu'aucun bouton n'est inatteignable. */
out.tb8_rove_parcours=TBG(function(){
  var a=[!0,!0,!0,!0,!0,!0],vu=[],c=0,i;
  for(i=0;i<6;i++){c=T.tbRove(c,1,a);vu.push(c)}
  return vu});
/* L'ASSAINISSEMENT DU POINT D'ENTREE — et il DIFFERE de la navigation :
   un index perime retombe sur le PREMIER actif, jamais sur le suivant.
   C'est un point d'entree, pas un deplacement. */
out.tb8_rove_sain=TBG(function(){
  var a=[!1,!0,!1,!0];
  return [T.tbRoveSain(1,a),T.tbRoveSain(0,a),T.tbRoveSain(2,a),
    T.tbRoveSain(9,a),T.tbRoveSain(NaN,a),T.tbRoveSain(1.5,a),
    T.tbRoveSain(3,a),T.tbRoveSain(0,[!1,!1]),T.tbRoveSain(0,[]),
    T.tbRoveSain(0,null)]});
/* HORIZONTALE (§4.5, et `aria-orientation="horizontal"` le promet) : seules
   gauche/droite naviguent. Haut/bas restent a l'ecran — ce sont ses sauts de
   coupe. `constructor` et consorts : acces garde, pas un acces nu. */
out.tb8_dir_touches=TBG(function(){
  return ["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Home","End","a",
    "Escape","","constructor","toString","__proto__",void 0,null]
    .map(function(k){return T.tbRoveDir(k)})});
/* LE NOMBRE DE BOUTONS D'ACTION, DERIVE DU PLAN. Une liste vide ou absente
   retombe sur le plan reel : la barre ne peint jamais zero bouton. */
out.tb8_nb_act=TBG(function(){
  return [T.tbNbAct(),T.tbNbAct([{btns:[1,2,3]},{btns:[]},{}]),
    T.tbNbAct([]),T.tbNbAct(null)]});
/* L'ORDRE PLAT : neuf actions + `⌖` + `×`. Les deux derniers sont TOUJOURS
   atteignables (§4.2 : `⌖` « ne doit jamais etre masque »). */
out.tb8_actifs=TBG(function(){
  var p=T.tbActifs(cabPlein),s=T.tbActifs(cabSansHote),
      v=T.tbActifs(void 0),n=T.tbActifs(null);
  return [p.length,p.join(","),s.join(","),v.join(","),n.join(",")]});
/* ET LES DEUX COTES S'ACCORDENT, BOUTON PAR BOUTON. `dzmTbActifs` decide ce
   qui est atteignable, `DzmToolBar` decide ce qui est peint eteint : deux
   tables qui divergeraient feraient tomber le point d'entree sur un bouton
   `disabled`, c'est-a-dire nulle part. MESUREE PAR MUTATION : la version
   naive (« entree absente = rien a eteindre = actif ») rend `false` sur les
   deux derniers plateaux. */
function TB8LIRE(items){
  var b=T.ToolBar({open:!0,items:items,rove:-1}),a=[];
  b.p.children[1].p.children.forEach(function(z){
    z.p.children[1].p.children.forEach(function(x){a.push(!x.p.disabled)})});
  a.push(!b.p.children[2].p.children[0].p.disabled);
  a.push(!b.p.children[2].p.children[1].p.disabled);
  return a}
out.tb8_actifs_accorde_la_barre=TBG(function(){
  return [TB8LIRE(cabPlein).join(",")===T.tbActifs(cabPlein).join(","),
    TB8LIRE(cabSansHote).join(",")===T.tbActifs(cabSansHote).join(","),
    TB8LIRE(void 0).join(",")===T.tbActifs(void 0).join(","),
    TB8LIRE(void 0).join(",")]});
/* ── LE `tabindex` SUR LA BARRE PEINTE : UN SEUL 0, LES AUTRES A -1 ────── */
function TB8TABS(o){
  var b=T.ToolBar(o),a=[];
  b.p.children[1].p.children.forEach(function(z){
    z.p.children[1].p.children.forEach(function(x){a.push(x.p.tabIndex)})});
  a.push(b.p.children[2].p.children[0].p.tabIndex);
  a.push(b.p.children[2].p.children[1].p.tabIndex);
  return a}
function TB8UN(a){var n=0,i;for(i=0;i<a.length;i++)if(a[i]===0)n++;return n}
out.tb8_tabindex=TBG(function(){
  var t0=TB8TABS({open:!0,items:cabPlein,rove:0});
  var t5=TB8TABS({open:!0,items:cabPlein,rove:5});
  var tA=TB8TABS({open:!0,items:cabPlein,rove:9});
  var tB=TB8TABS({open:!0,items:cabPlein,rove:10});
  return [t0.length,t0.join(","),TB8UN(t0),TB8UN(t5),TB8UN(tA),TB8UN(tB),
    t5.indexOf(0),tA.indexOf(0),tB.indexOf(0)]});
/* UN INDEX PERIME NE FAIT PAS DISPARAITRE LE POINT D'ENTREE : sans hote,
   les neuf sont eteints et il tombe sur `⌖` (index 9). */
out.tb8_tabindex_assaini=TBG(function(){
  return [TB8TABS({open:!0,items:cabSansHote,rove:0}).indexOf(0),
    TB8TABS({open:!0,items:cabSansHote,rove:3}).indexOf(0),
    TB8TABS({open:!0,items:cabPlein,rove:99}).indexOf(0),
    TB8TABS({open:!0,items:cabPlein,rove:NaN}).indexOf(0),
    TB8TABS({open:!0,items:cabPlein}).indexOf(0),
    TB8UN(TB8TABS({open:!0,items:cabSansHote,rove:0}))]});
/* LA POIGNEE EST HORS DU GROUPE — la consigne de l'etape 5, tenue : elle ne
   porte AUCUN `tabIndex` et le selecteur du groupe ne la nomme pas. Sans
   cela, les fleches auraient deux sens sur le meme objet. */
out.tb8_poignee_hors_groupe=TBG(function(){
  var g=T.ToolBar({open:!0,items:cabPlein,rove:0}).p.children[0];
  return [g.p.className,("tabIndex" in g.p),T.TB_SEL_ROVE,
    T.TB_SEL_ROVE.indexOf("tbgrip")<0,
    T.TB_SEL_ROVE.indexOf("dzm-tbb")>=0,
    T.TB_SEL_ROVE.indexOf("dzm-tbwb")>=0]});
/* CHAQUE GROUPE EST UN `role="group"` NOMME (§4.5 : « la couleur n'est jamais
   le seul porteur d'information : chaque groupe a son en-tete en clair »).
   Le libellé est VERBATIM du §2.2, suffixe « — selection » compris, et il est
   compare a la table du plan — jamais recopie. */
out.tb8_groupes_nommes=TBG(function(){
  return T.ToolBar({open:!0,items:cabPlein}).p.children[1].p.children
    .map(function(z){return [z.p.role,z.p["aria-label"]]})});
out.tb8_groupes_le_plan_dit_la_meme_chose=TBG(function(){
  return T.TB_PLAN.map(function(g){return g.t+(g.suf?" "+g.suf:"")})});
/* `role="toolbar"` ET SES DEUX ATTRIBUTS, VERBATIM DU §4.5. */
out.tb8_role=TBG(function(){
  var b=T.ToolBar({open:!0,items:cabPlein,onBarKey:function(){}});
  var c=T.ToolBar({open:!0,items:cabPlein});
  return [b.p.role,b.p["aria-orientation"],b.p["aria-label"],
    typeof b.p.onKeyDown,typeof c.p.onKeyDown]});
/* LE BOUTON D'ACTION : TROIS ETATS, DONT L'ABSENCE. Un appelant qui monte
   un bouton HORS d'une barre roving ne doit pas heriter d'un -1. */
out.tb8_btn_tab=TBG(function(){
  var a=TBB({group:"pistes",icon:"texte",label:"t",tab:!0});
  var b=TBB({group:"pistes",icon:"texte",label:"t",tab:!1});
  var c=TBB({group:"pistes",icon:"texte",label:"t"});
  var d2=TBB({group:"pistes",icon:"texte",label:"t",tab:1});
  return [a.p.tabIndex,b.p.tabIndex,("tabIndex" in c.p),("tabIndex" in d2.p)]});
/* ── LES TROIS AIDES DE DOM, SUR UN FAUX ARBRE ─────────────────────────── */
function TB8EL(){var e={foc:0};e.focus=function(){e.foc++};return e}
/* `tbBoutons` COPIE ce que le DOM rend : une NodeList vivante changerait
   sous nos pieds entre la mesure et le focus. */
out.tb8_boutons=TBG(function(){
  var vu=[],l=[TB8EL(),TB8EL()];
  var r1=T.tbBoutons({querySelectorAll:function(s){vu.push(s);return l}});
  return [vu,r1.length,r1!==l,Array.isArray(r1)]});
out.tb8_boutons_sans_dom=TBG(function(){
  return [T.tbBoutons(null).length,T.tbBoutons({}).length,
    T.tbBoutons({querySelectorAll:42}).length,
    T.tbBoutons({querySelectorAll:function(){throw new Error("x")}}).length]});
out.tb8_idx=TBG(function(){
  var a=TB8EL(),b=TB8EL(),c=TB8EL(),l=[a,b,c];
  return [T.tbIdx(l,a),T.tbIdx(l,c),T.tbIdx(l,TB8EL()),T.tbIdx(l,null),
    T.tbIdx(null,a),T.tbIdx([],a)]});
/* `tbFocus` REND CE QU'IL A FAIT, et il ne fait rien hors bornes, sur un
   nœud sans `focus`, ou sur un index qui n'est pas un nombre. */
out.tb8_focus=TBG(function(){
  var a=TB8EL(),b=TB8EL(),l=[a,b];
  var r=[T.tbFocus(l,1),T.tbFocus(l,9),T.tbFocus(l,-1),T.tbFocus(l,"1"),
    T.tbFocus([{}],0),T.tbFocus(null,0),T.tbFocus(l,1.5)];
  return [r,a.foc,b.foc]});
/* « RENDRE » LE FOCUS SUPPOSE QU'ON L'AVAIT : le raccourci replie depuis
   n'importe ou, et y deplacer le focus serait le VOLER. `contains` absent ou
   qui leve : faux, jamais une levee. Le nœud LUI-MEME compte pour dedans. */
out.tb8_dedans=TBG(function(){
  var kid={},autre={};
  var bar={contains:function(e){return e===kid}};
  var casse={contains:function(){throw new Error("x")}};
  return [T.tbDedans(bar,kid),T.tbDedans(bar,autre),T.tbDedans(bar,bar),
    T.tbDedans(bar,null),T.tbDedans(null,kid),T.tbDedans({},kid),
    T.tbDedans(casse,kid),T.tbDedans(null,null)]});
/* LA COMBO DITE SUR L'ONGLET — jamais une parenthese vide. */
out.tb8_combo=TBG(function(){
  return [T.tbCombo("O"),T.tbCombo("  Maj+O "),T.tbCombo(""),T.tbCombo("   "),
    T.tbCombo(null),T.tbCombo(void 0),T.tbCombo(42)]});
out.tb8_onglet=TBG(function(){
  var o={};
  return [T.ToolTab({open:!1,keyLbl:"O"}).p.title,
    T.ToolTab({open:!0,keyLbl:"O"}).p.title,
    T.ToolTab({open:!1}).p.title,
    T.ToolTab({open:!0,tabRef:o}).p.ref===o]});

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
      # DEUX depuis P12 : askAudio reprend le motif d'askDur ligne pour
      # ligne, ce repli compris (js_askaudio_sans_rappel_elle_ne_leve_pas).
      and src.count('var fin=typeof o.done==="function"?o.done:function(){};')
      == 2,
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

# ── P12 : le son d'un plan suit sa video — le cœur pur, sous node ─────────
# LA PISTE DE DIALOGUE. `dt_0409_pick == "a2"` est LA MESURE qui motive la
# fonction : sur les pistes de la sauvegarde du 04/09, pickTrack rend la
# MUSIQUE (bouclee, duckee). Le conjoint est dialogueTrack qui rend a1 sur la
# meme liste — les deux ne peuvent pas etre vrais sur une fonction qui
# recopierait pickTrack.
check("js_dialogue_vise_le_bus_dialogue_et_non_la_premiere_piste_audio",
      d.get("dt_0409") == "a1" and d.get("dt_0409_pick") == "a2"
      and d.get("dt_defauts") == "a1",
      f'dialogue={d.get("dt_0409")!r} pickTrack={d.get("dt_0409_pick")!r} '
      f'defauts={d.get("dt_defauts")!r}')
check("js_dialogue_le_bus_prime_sur_l_identifiant",
      d.get("dt_bus_ailleurs") == "a4", repr(d.get("dt_bus_ailleurs")))
check("js_dialogue_a1_par_identifiant_quand_aucun_bus_ne_le_dit",
      d.get("dt_a1_sans_bus") == "a1", repr(d.get("dt_a1_sans_bus")))
# JAMAIS UNE PISTE BOUCLEE — ni par le bus, ni par l'identifiant. Le conjoint
# (`dt_a1_sans_bus == "a1"`) empeche cette negation d'etre vraie sur une
# fonction qui rendrait "" partout.
check("js_dialogue_jamais_une_piste_bouclee",
      d.get("dt_a1_bouclee") == "" and d.get("dt_a1_sans_bus") == "a1",
      f'bouclee={d.get("dt_a1_bouclee")!r} a1={d.get("dt_a1_sans_bus")!r}')
check("js_dialogue_etats_vides_rendent_une_chaine_vide",
      d.get("dt_vide") == "" and d.get("dt_null") == ""
      and d.get("dt_sans_audio") == "" and d.get("dt_a1_video") == ""
      and d.get("dt_defauts") == "a1",
      f'vide={d.get("dt_vide")!r} null={d.get("dt_null")!r} '
      f'sans_audio={d.get("dt_sans_audio")!r} a1_video={d.get("dt_a1_video")!r}')
# PLEIN CADRE OU INCRUSTATION : V1 (type « vidéo ») recoit un jumeau ; la V2
# historique (« overlay/VFX ») et toute piste neuve de dzmAdd (« overlay »)
# non ; une piste sans type (payload nu) compte comme plein cadre ; une piste
# vidéo neuve typee « vidéo » (tache 20) en recoit un.
check("js_plein_v1_oui_v2_et_pistes_neuves_non",
      d.get("tp_v1") is True and d.get("tp_v2") is False
      and d.get("tp_v3_neuve") is False and d.get("tp_v1_nue") is True
      and d.get("tp_video_plein_neuve") is True,
      f'v1={d.get("tp_v1")} v2={d.get("tp_v2")} v3={d.get("tp_v3_neuve")} '
      f'nue={d.get("tp_v1_nue")} neuve_video={d.get("tp_video_plein_neuve")}')
# LA LISTE NUE ET SON HABILLAGE (tour 2) : le payload d'une sauvegarde nomme
# v2 SANS type, et une liste nue rend VRAI pour v2 — ce qui tient l'exemption
# des incrustations est svmTracksFrom (dzmSkin a l'apply : v3 « overlay »,
# v2 « overlay/VFX », v1 « vidéo »), mesure ici cote a cote, et non
# trackPlein seule.
check("js_plein_une_liste_nue_rend_vrai_pour_v2_et_svmTracksFrom_l_habille",
      d.get("tp_user_v2_nue") is True and d.get("tp_from_v2") is False
      and d.get("wt_user_v2") == [True, False]
      and d.get("tp_from_types") == [["v3", "overlay"], ["v2", "overlay/VFX"],
                                     ["v1", "vidéo"]],
      f'nue={d.get("tp_user_v2_nue")} habillee={d.get("tp_from_v2")} '
      f'wantsTwin={d.get("wt_user_v2")} types={d.get("tp_from_types")}')
# L'INCRUSTATION DITE : la phrase nomme la piste et la cible, "" partout ou
# il n'y a rien a dire — sept etats, dont deux vides (conjoints de la phrase).
check("js_overlayNote_dit_l_incrustation_et_se_tait_ailleurs",
      d.get("on_v2") == " Posé sur V2 (incrustation) : le son de ce plan n'a "
      "PAS été extrait — sélectionnez-le puis « Extraire le son → A1 » dans "
      "l'inspecteur."
      and str(d.get("on_v2_sans_dialogue", "")).endswith(
          "« Extraire le son » dans l'inspecteur.")
      and d.get("on_rien") == [""] * 7,
      f'{repr(d.get("on_v2"))[:120]} '
      f'sans_dialogue={repr(d.get("on_v2_sans_dialogue"))[-60:]} '
      f'rien={d.get("on_rien")}')
check("js_plein_etats_vides_et_autres_genres_rendent_faux",
      d.get("tp_a1") is False and d.get("tp_absente") is False
      and d.get("tp_vide") is False and d.get("tp_v1") is True,
      f'a1={d.get("tp_a1")} absente={d.get("tp_absente")} vide={d.get("tp_vide")}')
check("js_wantsTwin_video_sur_plein_cadre_seulement",
      d.get("wt") == [True, False, False, False], repr(d.get("wt")))
# LES IDENTIFIANTS. `uniqueId` : libre tel quel, sinon _2, _3 (le plus petit
# n libre, a partir de 2).
check("js_uniqueId_libre_tel_quel_sinon_suffixe_minimal",
      d.get("ui_libre") == "v1u4_0" and d.get("ui_pris") == "v1u1_0_2"
      and d.get("ui_pris_2") == "v1u1_0_3" and d.get("ui_vide") == ["x", "x"],
      f'{d.get("ui_libre")!r} {d.get("ui_pris")!r} {d.get("ui_pris_2")!r} '
      f'{d.get("ui_vide")!r}')
# `dedupeIds` sur les DOUBLONS REELS de la sauvegarde de l'utilisateur
# (lecture seule, 06/09/2026) : le PREMIER garde son id — le meme objet, pas
# une copie — les suivants sont renommes, l'entree n'est pas mutee.
check("js_dedupe_le_premier_garde_son_id_les_suivants_sont_renommes",
      d.get("dd_ids") == ["a1_vo", "v1u1_0", "v1u2_0", "v1u3_0", "v1u1_0_2",
                          "v1u2_0_2", "s1cmtpobgr366"]
      and d.get("dd_renamed") == [{"de": "v1u1_0", "en": "v1u1_0_2"},
                                  {"de": "v1u2_0", "en": "v1u2_0_2"}]
      and d.get("dd_premier_garde") is True,
      f'{d.get("dd_ids")} {d.get("dd_renamed")} premier={d.get("dd_premier_garde")}')
check("js_dedupe_ne_mute_pas_l_entree",
      d.get("dd_entree_intacte") == ["a1_vo", "v1u1_0", "v1u2_0", "v1u3_0",
                                     "v1u1_0", "v1u2_0", "s1cmtpobgr366"]
      and d.get("dd_renamed") not in (None, "LEVE", []),
      f'{d.get("dd_entree_intacte")}')
# UN SUFFIXE DEJA PRIS PLUS LOIN dans le tableau n'est pas repris : k, k_2, k
# donne k_3, pas un second k_2.
check("js_dedupe_ne_reprend_pas_un_suffixe_deja_porte_plus_loin",
      d.get("dd_suffixe_deja_pris") == ["k", "k_2", "k_3"],
      repr(d.get("dd_suffixe_deja_pris")))
check("js_dedupe_etats_vides_sans_id_et_sans_doublon",
      d.get("dd_sans_id") == ["k", "ABSENT", "k_2"]
      and d.get("dd_sans_doublon") == [["a", "b"], 0]
      and d.get("dd_vide") == [0, 0],
      f'{d.get("dd_sans_id")} {d.get("dd_sans_doublon")} {d.get("dd_vide")}')
check("js_seqMax_le_plus_grand_u_n_rencontre_zero_sinon",
      d.get("sm") == [3, 0, 0, 12], repr(d.get("sm")))
# LE JUMEAU du kapwing_sample de l'utilisateur, tel qu'il est sur V1 :
# meme source (le MEME objet), memes bornes, meme point d'entree, sur a1,
# libelle « … · son du plan » (celui de la construction automatique),
# identifiant a1u3_0 (le prefixe de piste echange).
check("js_twin_le_jumeau_est_la_copie_sonore_du_plan",
      d.get("tc_jumeau") == {"tr": "a1", "id": "a1u3_0",
                             "label": "kapwing_sample · son du plan",
                             "start": 28.876, "end": 50.509,
                             "src": {"job_id": "a54e"}, "srcIn": 0}
      and d.get("tc_meme_src") is True and d.get("tc_srcin") == 2,
      f'{d.get("tc_jumeau")} meme_src={d.get("tc_meme_src")} '
      f'srcIn={d.get("tc_srcin")}')
# LE REFUS DU DOUBLON : meme source, meme piste, plage qui CHEVAUCHE — y
# compris avec les cles de `src` dans un autre ordre (JSON des cles triees).
# Les trois conjoints (autre source, autre piste, bord a bord) empechent ces
# deux negations d'etre vraies sur un twinClip qui rendrait null partout.
check("js_twin_null_si_le_son_est_deja_la",
      d.get("tc_doublon_chevauche") is None
      and d.get("tc_doublon_cles_ordre") is None
      and d.get("tc_autre_src") is True and d.get("tc_autre_piste") is True
      and d.get("tc_bord_a_bord") is True,
      f'chevauche={d.get("tc_doublon_chevauche")} '
      f'cles={d.get("tc_doublon_cles_ordre")} autre_src={d.get("tc_autre_src")} '
      f'autre_piste={d.get("tc_autre_piste")} bord={d.get("tc_bord_a_bord")}')
check("js_twin_etats_vides_rendent_null",
      d.get("tc_sans_src") is None and d.get("tc_sans_piste") is None
      and d.get("tc_clips_null") is True,
      f'sans_src={d.get("tc_sans_src")} sans_piste={d.get("tc_sans_piste")} '
      f'clips_null={d.get("tc_clips_null")}')
check("js_twin_l_identifiant_est_unique_et_lisible",
      d.get("tc_id_pris") == "a1u3_0_2" and d.get("tc_id_hors_prefixe") == "a1_c4"
      and d.get("tc_id_absent") == "a1_son",
      f'{d.get("tc_id_pris")!r} {d.get("tc_id_hors_prefixe")!r} '
      f'{d.get("tc_id_absent")!r}')
# LA DECISION, chaque sortie NOMMEE et DITE.
def _tp(k):
    v = d.get(k)
    return v if isinstance(v, list) and len(v) == 3 else ["ABSENT:%r" % (v,), None, ""]


check("js_twinPlan_pose_sur_a1_et_dit_qu_annuler_retire_les_deux",
      _tp("tp_pose")[0] == "pose" and _tp("tp_pose")[1] == "a1"
      and "Son du plan extrait sur A1" in _tp("tp_pose")[2]
      and "retire les DEUX clips" in _tp("tp_pose")[2],
      repr(_tp("tp_pose"))[:220])
check("js_twinPlan_muet_est_DIT",
      _tp("tp_muet")[0] == "muet" and _tp("tp_muet")[1] is None
      and "n'a pas de piste audio" in _tp("tp_muet")[2],
      repr(_tp("tp_muet"))[:200])
check("js_twinPlan_non_sonde_est_DIT_avec_sa_raison",
      _tp("tp_non_sonde")[0] == "non-sonde"
      and "(délai dépassé)" in _tp("tp_non_sonde")[2]
      and _tp("tp_sans_verdict")[0] == "non-sonde"
      and "Extraire le son" in _tp("tp_sans_verdict")[2],
      f'{_tp("tp_non_sonde")!r} {_tp("tp_sans_verdict")!r}'[:300])
# NON-SONDABLE N'EST PAS DIT MUET : une MESURE sans flux ET sans duree (le
# fichier de 0 octet de la sauvegarde de l'utilisateur) sort nommee a part,
# avec sa phrase, et JAMAIS « n'a pas de piste audio ». Le conjoint est
# tp_muet (meme verdict, duree 15,973) qui reste « muet » — une fonction qui
# dirait « non-sondable » a tout `has_audio:false` ne passe pas.
check("js_twinPlan_non_sondable_n_est_pas_dit_muet",
      _tp("tp_non_sondable")[0] == "non-sondable"
      and _tp("tp_non_sondable")[1] is None
      and "n'a pas pu être sondée" in _tp("tp_non_sondable")[2]
      and "fichier vide ou illisible" in _tp("tp_non_sondable")[2]
      and "n'a pas de piste audio" not in _tp("tp_non_sondable")[2]
      and _tp("tp_muet")[0] == "muet",
      f'{_tp("tp_non_sondable")!r} muet={_tp("tp_muet")[0]!r}'[:300])
# LES JETONS SONT TRADUITS : aucune note ne montre « (delai) », « (refus) »,
# « (erreur) », « (sans-reseau) » tels quels ; chacune porte sa phrase.
_pq = d.get("tp_pourquoi") if isinstance(d.get("tp_pourquoi"), list) else []
check("js_twinPlan_les_jetons_de_la_sonde_sont_traduits",
      len(_pq) == 4
      and all(isinstance(t, str) and "(" + tok + ")" not in t and mot in t
              for t, tok, mot in zip(_pq, ("delai", "refus", "erreur",
                                            "sans-reseau"),
                                     ("(délai dépassé)", "(le serveur a refusé)",
                                      "(erreur réseau)", "(hors ligne)"))),
      repr(_pq)[:400])
check("js_twinPlan_sans_piste_de_dialogue_dit_plus_piste_audio",
      _tp("tp_sans_piste")[0] == "sans-piste" and _tp("tp_sans_piste")[1] is None
      and "« + piste audio »" in _tp("tp_sans_piste")[2],
      repr(_tp("tp_sans_piste"))[:200])
check("js_twinPlan_verrou_et_doublon_sont_DITS",
      _tp("tp_verrou")[0] == "verrou" and "A1 verrouillée" in _tp("tp_verrou")[2]
      and _tp("tp_doublon")[0] == "doublon"
      and "déjà présent sur A1" in _tp("tp_doublon")[2],
      f'{_tp("tp_verrou")!r} {_tp("tp_doublon")!r}'[:300])
check("js_twinPlan_vise_a1_sur_les_pistes_du_04_09",
      _tp("tp_0409_vise_a1")[0] == "pose" and _tp("tp_0409_vise_a1")[1] == "a1",
      repr(_tp("tp_0409_vise_a1"))[:120])
# LA DUREE EN PRIME : prise quand elle manque, jamais quand on la connait,
# jamais sur le verrou negatif d'askDur, jamais pour une image.
check("js_srcDurOr_prend_la_duree_de_la_sonde_seulement_quand_elle_manque",
      d.get("sd") == [15.973, 21.233, -1, 0, 0, 0], repr(d.get("sd")))
# LE CACHE. Une source inconnue rend null (la question doit etre posee) ; une
# source illisible rend un verdict tout fait (elle ne peut pas l'etre).
check("js_audioOf_inconnu_null_illisible_verdict_tout_fait",
      d.get("ao_inconnu") is None
      and d.get("ao_illisible") == {"has_audio": False, "dur": 0,
                                    "pourquoi": "src-illisible"},
      f'inconnu={d.get("ao_inconnu")} illisible={d.get("ao_illisible")}')
check("js_audioSet_normalise_et_audioOf_relit_une_copie",
      d.get("as_ecrit") == {"has_audio": True, "dur": 3.5, "pourquoi": "mesure"}
      and d.get("ao_relu") == {"has_audio": True, "dur": 3.5, "pourquoi": "mesure"}
      and d.get("ao_copie") is True and d.get("as_illisible") is None,
      f'{d.get("as_ecrit")} {d.get("ao_relu")} copie={d.get("ao_copie")} '
      f'illisible={d.get("as_illisible")}')
check("js_audioForget_oublie_une_fois",
      d.get("af_oublie") == [True, None, False], repr(d.get("af_oublie")))
# askAudio, LE MOTIF D'askDur : `done` UNE fois, sortie nommee, url de la
# route, cache ecrit avant `done` sur TOUTE sortie.
def _aa(k):
    v = d.get(k)
    return v if isinstance(v, list) and len(v) == 2 else ["ABSENT:%r" % (v,),
                                                          "ABSENT"]


check("js_askaudio_la_mesure_revient_telle_quelle",
      _aa("aa_mesure") == [{"has_audio": True, "dur": 15.973,
                            "pourquoi": "mesure"}, "mesure"]
      and d.get("aa_une_seule_reponse") == 1,
      f'{_aa("aa_mesure")!r} n={d.get("aa_une_seule_reponse")!r}')
check("js_askaudio_l_url_est_celle_de_la_route",
      isinstance(d.get("aa_url"), str)
      and d["aa_url"] == "/api/montage/has-audio?src=" + urllib.parse.quote(
          '{"job_id":"h1"}', safe=""),
      repr(d.get("aa_url")))
# UN MEME FICHIER N'EST SONDE QU'UNE FOIS : la seconde demande sort « cache »
# avec le PREMIER verdict, sans un appel — le fetch de la seconde disait le
# contraire, et n'a pas ete lu.
check("js_askaudio_une_source_deja_sondee_repond_du_cache_sans_appel",
      d.get("aa_cache_apres") == {"has_audio": True, "dur": 15.973,
                                  "pourquoi": "mesure"}
      and _aa("aa_cache") == [{"has_audio": True, "dur": 15.973,
                               "pourquoi": "mesure"}, "cache"]
      and d.get("aa_cache_zero_appel") == 0,
      f'apres={d.get("aa_cache_apres")} cache={_aa("aa_cache")!r} '
      f'appels={d.get("aa_cache_zero_appel")}')
for _lbl, _k, _att in (
        ("muet_mesure", "aa_muet",
         [{"has_audio": False, "dur": 4, "pourquoi": "mesure"}, "mesure"]),
        ("un_corps_sans_le_champ_est_un_refus", "aa_sans_champ",
         [{"has_audio": False, "dur": 0, "pourquoi": "refus"}, "refus"]),
        ("un_refus_http_ne_ment_pas", "aa_http_refuse",
         [{"has_audio": False, "dur": 0, "pourquoi": "refus"}, "refus"]),
        ("un_corps_illisible_ne_ment_pas", "aa_json_illisible",
         [{"has_audio": False, "dur": 0, "pourquoi": "refus"}, "refus"]),
        ("un_reseau_qui_leve_ne_tue_rien", "aa_reseau_leve",
         [{"has_audio": False, "dur": 0, "pourquoi": "erreur"}, "erreur"]),
        ("une_promesse_rejetee_ne_tue_rien", "aa_promesse_rejetee",
         [{"has_audio": False, "dur": 0, "pourquoi": "erreur"}, "erreur"]),
        ("sans_fetch_la_sortie_est_nommee", "aa_sans_reseau",
         [{"has_audio": False, "dur": 0, "pourquoi": "sans-reseau"},
          "sans-reseau"]),
        ("le_delai_gagne_la_course", "aa_delai_gagne",
         [{"has_audio": False, "dur": 0, "pourquoi": "delai"}, "delai"]),
        ("un_src_illisible_sort_nomme", "aa_src_illisible",
         [{"has_audio": False, "dur": 0, "pourquoi": "src-illisible"},
          "src-illisible"])):
    check("js_askaudio_" + _lbl, _aa(_k) == _att, repr(_aa(_k)))
check("js_askaudio_la_reponse_tardive_ne_fait_rien",
      d.get("aa_delai_une_seule_reponse") == 1
      and d.get("aa_delai_la_reponse_est_bien_passee") == 1,
      f'reponses={d.get("aa_delai_une_seule_reponse")} '
      f'appels={d.get("aa_delai_la_reponse_est_bien_passee")}')
check("js_askaudio_sans_fetch_et_sans_src_aucun_appel",
      d.get("aa_sans_reseau_zero_appel") == 0
      and d.get("aa_src_illisible_zero_appel") == 0
      and _aa("aa_sans_reseau")[1] == "sans-reseau"
      and _aa("aa_src_illisible")[1] == "src-illisible",
      f'sans_reseau={d.get("aa_sans_reseau_zero_appel")} '
      f'illisible={d.get("aa_src_illisible_zero_appel")}')
# LE VERROU : TOUTE sortie ecrit le cache — delai, refus, erreur, sans-reseau
# — avec sa raison. C'est ce qui rend le rappel d'addAsset non recursif, et
# ce que [3-bis] reproduit en supprimant l'ecriture.
check("js_askaudio_toute_sortie_ecrit_le_cache_avec_sa_raison",
      d.get("aa_cache_sur_sorties") == [
          {"has_audio": False, "dur": 0, "pourquoi": "delai"},
          {"has_audio": False, "dur": 0, "pourquoi": "refus"},
          {"has_audio": False, "dur": 0, "pourquoi": "erreur"},
          {"has_audio": False, "dur": 0, "pourquoi": "sans-reseau"}],
      repr(d.get("aa_cache_sur_sorties")))
check("js_askaudio_sans_rappel_elle_ne_leve_pas",
      d.get("aa_sans_done") == "ok", repr(d.get("aa_sans_done")))
check("js_askaudio_le_delai_est_celui_de_la_couche",
      d.get("aa_delai_illisible") == 1500 and d.get("aa_delai_recu") == 250,
      f'illisible={d.get("aa_delai_illisible")} recu={d.get("aa_delai_recu")}')
# extract — LE MOTEUR DU BOUTON. Un seul historique, un seul concat, le
# jumeau derriere le plan, le drapeau, la note qui nomme piste et libelle.
def _ex(k):
    v = d.get(k)
    return v if isinstance(v, dict) else {"r": "ABSENT:%r" % (v,), "notes": []}


check("js_extract_pose_le_jumeau_en_un_geste",
      _ex("ex_pose").get("r") is True and _ex("ex_pose").get("hist") == 1
      and _ex("ex_pose").get("ids") == ["v1u3_0", "a1u3_0"]
      and _ex("ex_pose").get("dirty") == 1 and _ex("ex_pose").get("asks") == 1
      and len(_ex("ex_pose").get("notes") or []) == 1
      and "Son de « kapwing_sample » extrait sur A1" in _ex("ex_pose")["notes"][0]
      and "« Annuler »" in _ex("ex_pose")["notes"][0],
      repr(_ex("ex_pose"))[:300])
# LES REFUS APRES LA SONDE : rien d'ecrit (hist 0, clips null), note DITE. Le
# conjoint de chacune de ces negations est `ex_pose` juste au-dessus.
for _lbl, _k, _mot in (("muet", "ex_muet", "n'a pas de piste audio"),
                       ("non_sonde", "ex_non_sonde",
                        "n'a pas abouti (délai dépassé)"),
                       ("non_sondable", "ex_non_sondable",
                        "n'a pas pu être sondé (aucune durée mesurable"),
                       ("sans_verdict", "ex_sans_verdict", "n'a pas abouti"),
                       ("doublon", "ex_doublon", "est déjà sur A1"),
                       ("plan_parti", "ex_plan_parti",
                        "n'est plus dans la timeline")):
    check("js_extract_refus_" + _lbl + "_est_DIT_et_rien_n_est_ecrit",
          _ex(_k).get("r") is True and _ex(_k).get("hist") == 0
          and _ex(_k).get("n") is None and _ex(_k).get("asks") == 1
          and len(_ex(_k).get("notes") or []) == 1
          and _mot in _ex(_k)["notes"][0]
          and _ex("ex_pose").get("hist") == 1,
          repr(_ex(_k))[:260])
# LES REFUS AVANT LA SONDE : aucune demande n'est faite (asks 0).
for _lbl, _k, _mot in (("sans_piste_de_dialogue", "ex_sans_piste",
                        "« + piste audio »"),
                       ("piste_verrouillee", "ex_verrou", "A1 verrouillée"),
                       ("sans_source", "ex_sans_src", "rien à extraire"),
                       ("image", "ex_image", "est une image")):
    check("js_extract_refus_" + _lbl + "_avant_toute_sonde",
          _ex(_k).get("r") is False and _ex(_k).get("asks") == 0
          and _ex(_k).get("hist") == 0
          and len(_ex(_k).get("notes") or []) == 1
          and _mot in _ex(_k)["notes"][0]
          and _ex("ex_pose").get("asks") == 1,
          repr(_ex(_k))[:260])
# NON-SONDABLE N'EST PAS DIT MUET ici non plus : la phrase du 0 octet ne
# contient pas celle du plan muet, et le conjoint ex_muet la contient.
check("js_extract_non_sondable_n_est_pas_dit_muet",
      "n'a pas de piste audio" not in (_ex("ex_non_sondable").get("notes") or [""])[0]
      and "fichier vide ou illisible" in (_ex("ex_non_sondable").get("notes") or [""])[0]
      and "n'a pas de piste audio" in (_ex("ex_muet").get("notes") or [""])[0],
      f'{_ex("ex_non_sondable").get("notes")!r} {_ex("ex_muet").get("notes")!r}'[:300])
# LE CLIP EST RELU AU MOMENT DE LA REPONSE : deplace entre le clic et la
# sonde (28,876→50,509 au clic, 10→20 avec srcIn 5 a la reponse), le jumeau
# prend les bornes FRAICHES. Le conjoint est ex_pose, dont le jumeau garde
# celles du clic parce que le plan n'a pas bouge.
check("js_extract_relit_le_clip_frais_a_la_reponse",
      _ex("ex_bouge").get("jumeau") == {"tr": "a1", "id": "a1u3_0",
                                        "label": "kapwing_sample · son du plan",
                                        "start": 10, "end": 20,
                                        "src": {"job_id": "a54e"}, "srcIn": 5}
      and (_ex("ex_pose").get("jumeau") or {}).get("start") == 28.876,
      f'{_ex("ex_bouge").get("jumeau")} pose={_ex("ex_pose").get("jumeau")}')
# V2 AUSSI : le bouton vaut pour tout clip video a source, pas pour V1 seule.
check("js_extract_vaut_pour_une_incrustation_aussi",
      _ex("ex_v2").get("ids") == ["v2u1_0", "a1u1_0"] and _ex("ex_v2").get("hist") == 1,
      repr(_ex("ex_v2"))[:200])
# UN CLIC EST UN GESTE : un verdict en cache qui n'est PAS une mesure est
# oublie avant de redemander (null au moment de l'`ask`), et la pose suit ;
# une MESURE en cache est gardee.
check("js_extract_oublie_un_verdict_non_mesure_et_garde_une_mesure",
      d.get("ex_oubli_avant_ask") is None and d.get("ex_oubli_pose") == 2
      and d.get("ex_mesure_gardee") == {"has_audio": False, "dur": 15.973,
                                        "pourquoi": "mesure"},
      f'avant={d.get("ex_oubli_avant_ask")} pose={d.get("ex_oubli_pose")} '
      f'gardee={d.get("ex_mesure_gardee")}')
# LE BOUTON : un `button` a cle, classe, libelle qui nomme la piste,
# aria-label, titre qui dit le refus et l'annulation ; null hors d'un clip
# video a source.
check("js_extractBtn_nomme_la_piste_visee",
      d.get("eb_v1") == ["button", "dzmextr", "svm-secbtn dzm-extract",
                         "Extraire le son → A1",
                         "Extraire le son de kapwing_sample vers A1"]
      and d.get("eb_v2") == "Extraire le son → A1",
      f'{d.get("eb_v1")} v2={d.get("eb_v2")!r}')
check("js_extractBtn_sans_piste_de_dialogue_le_dit",
      d.get("eb_sans_piste") == "Extraire le son (aucune piste de dialogue)",
      repr(d.get("eb_sans_piste")))
# … ni pour une IMAGE posee sur une piste video (src:{image}) : la quatrieme.
check("js_extractBtn_null_hors_d_un_clip_video_a_source",
      d.get("eb_nuls") == [None, None, None, None] and d.get("eb_v2") is not None,
      repr(d.get("eb_nuls")))
check("js_extractBtn_le_titre_dit_le_refus_et_l_annulation",
      isinstance(d.get("eb_titre"), str)
      and "n'a pas de piste audio" in d["eb_titre"]
      and "déjà sur A1" in d["eb_titre"] and "« Annuler »" in d["eb_titre"]
      and "sort muet" in d["eb_titre"],
      repr(d.get("eb_titre"))[:240])
check("js_extractBtn_le_clic_appelle_le_moteur",
      d.get("eb_clic") == [2], repr(d.get("eb_clic")))

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
# P12 — `svmApplyProject`, la tranche ENTIERE, de sa signature a l'effet
# de montage qui la suit (le premier `x.useEffect(function(){var alive=!0;`
# APRES elle — neuf dans le bundle, `_bloc` prend le premier qui suit).
_APPLY = _bloc("svmApplyProject", "  function svmApplyProject(d){",
               "  x.useEffect(function(){var alive=!0;")
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
         arm:[],attente:[],dirtyV:[]};
  var proj={dur:Number(o.dur)||16,demo:!1,mixDb:{}};
  var durRef={current:proj.dur};
  var clipsRef={current:(o.clips||[]).slice()};
  var phRef={current:Number(o.ph)||0};
  var mixRef={current:{}};
  var selRef={current:o.sel||null};
  var ovSeq={current:Number(o.seq)||0};
  var nudgeHistAt={current:0};
  var ovKeysOffRef={current:!1};
  var dzReadyRef={current:o.pasPrete?!1:!0};
  var dzTracksRef={current:o.pistes||null};
  var trackStRef={current:o.verrous||{}};
  var dzmReplaceRef={current:o.remplace||null};
  var ripple=!!o.ripple,snap=!!o.snap;
  /* P12 — svmApplyProject ecrit un OBJET, addAsset une fonction : les
     deux formes du setter de React. */
  function setProj(fn){proj=typeof fn==="function"?fn(proj):fn;
    durRef.current=proj.dur;J.proj.push(proj.dur)}
  function setClips(cs){clipsRef.current=cs;J.clips.push(cs.length)}
  function setSelId(id){selRef.current=id;J.sel.push(id)}
  /* P12 (tour 2) — la VALEUR passee a setDirty est journalisee : c'est
     elle qui arme ou desarme l'autosauvegarde du bundle. */
  function setDirty(v){J.dirty++;J.dirtyV.push(!!v)}
  function setOvPick(v){J.pick.push(v)}
  function setSnapT(v){J.snapT.push(v)}
  function setDzmArm(v){J.arm.push(v)}
  function fireNote(t){J.notes.push(String(t))}
  function pushHistory(h){J.hist++}
  function dzAddWhenReady(a,b,c,e,f,g,h){J.attente.push([b,c,e,f,g])}
  function svmKeyLabel(k){return "["+k+"]"}
  /* P12 — l'hote de svmApplyProject : ce qu'elle ecrit est journalise,
     l'historique est une ref comme dans le bundle. `SVM_DEMO_MIX` est
     le repli du mixage ; `localStorage` n'existe pas sous node et le
     bundle l'enveloppe deja d'un try. */
  var histRef={current:{u:[],r:[]}},SVM_DEMO_MIX={};
  J.ph=[];J.apply=[];J.saveInfo=[];
  function setPh(v){J.ph.push(v)}
  function setHistTick(f){}
  function setDurMaster(v){}
  function setDucking(v){}
  function setSaveInfo(v){J.saveInfo.push(v)}
  __KBSEL__
  __ADD__
  var KB={__NUDGE__};
  __CLIPDOWN__
  function DURCTL(dur,tickStep,clips){return __DURCTL__}
  __APPLY__
  return {addAsset:addAsset,nudge:KB.nudge,clipDown:clipDown,durCtl:DURCTL,
    seq:function(){return ovSeq.current},apply:svmApplyProject,
    projet:function(){return proj},
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
/* P12 — `askAudio` EST BOUCHONNEE DE LA MEME FACON, et pour la meme raison :
   la vraie irait chercher `fetch` chez node (URL relative -> rejet) et
   repondrait en micro-tache, APRES les lectures synchrones de cette sonde.
   Le bouchon ENREGISTRE ; `REPOND` joue la reponse comme la vraie l'aurait
   fait — le cache ECRIT, puis `done`. `REPOND_SANS_CACHE` joue la reponse
   SANS l'ecriture : c'est la mutation qui prouve que le verrou de recursion
   est bien le cache, et rien d'autre. */
var vraiAu=window.DzTracks.askAudio,auVus=[];
window.DzTracks.askAudio=function(sr,op){auVus.push([sr,op])};
function REPOND(v){var c=auVus[auVus.length-1];if(!c)return !1;
  window.DzTracks.audioSet(c[0],v);c[1].done(window.DzTracks.audioOf(c[0]),"bouchon");return !0}
function REPOND_SANS_CACHE(v){var c=auVus[auVus.length-1];if(!c)return !1;
  c[1].done(v,"bouchon");return !0}
var OUI={has_audio:!0,dur:21.233,pourquoi:"mesure"};
var NON={has_audio:!1,dur:21.233,pourquoi:"mesure"};
/* ── LE CAS DE L'UTILISATEUR, JOUE PAR L'ECRAN — ET SON JUMEAU (P12) ─────── */
var E1=ECRAN({dur:16});
E1.addAsset({job_id:7},"sentry_bot.mp4","video",21.233,"v1",0);
/* RIEN N'EST ECRIT AVANT LE VERDICT : la sonde audio est partie, une fois,
   avec le `src` tel quel, et ni clip, ni historique, ni note. */
out.au_appels=auVus.length;
out.au_src=auVus[0]?auVus[0][0]:null;
out.au_avant=[E1.J.clips.length,E1.J.hist,E1.J.notes.length,askVus.length];
REPOND(OUI);
out.add_bornes=BORNES(E1.etat().clips);
out.add_pistes=E1.etat().clips.map(function(c){return c.tr});
out.add_ids=E1.etat().clips.map(function(c){return c.id});
out.add_jumeau=E1.etat().clips[1]||null;
out.add_dur=E1.etat().dur;
out.add_proj=E1.J.proj;
out.add_note=E1.J.notes[0]||"";
out.add_notes=E1.J.notes.length;
out.add_hist=E1.J.hist;
out.add_sel=E1.J.sel;
out.add_ecritures=E1.J.clips;
/* UNE DUREE CONNUE NE FAIT RIEN DEMANDER A askDur — negation, dont le
   conjoint est le clip effectivement pose a sa longueur. */
out.add_ask=askVus.length;
/* LE RAPPEL N'A PAS REDEMANDE : une sonde, pas deux. */
out.au_relance=auVus.length;
/* ── LE VERDICT « MUET » : un seul clip, et c'est DIT ───────────────────── */
var E1b=ECRAN({dur:16});
E1b.addAsset({job_id:70},"Memecoin.mp4","video",16,"v1",0);
REPOND(NON);
out.muet_bornes=BORNES(E1b.etat().clips);
out.muet_pistes=E1b.etat().clips.map(function(c){return c.tr});
out.muet_note=E1b.J.notes[0]||"";
out.muet_hist=E1b.J.hist;
/* ── PAS DE PISTE DE DIALOGUE : un seul clip, la note dit « + piste audio »,
   et la piste BOUCLEE a2 n'a pas ete prise ────────────────────────────── */
var E1c=ECRAN({dur:16,pistes:[{id:"v1",kind:"video",type:"vidéo"},
  {id:"a2",kind:"audio",bus:"musique",loop:!0},{id:"s1",kind:"subs"}]});
E1c.addAsset({job_id:71},"parle.mp4","video",5,"v1",0);
REPOND(OUI);
out.sanspiste_pistes=E1c.etat().clips.map(function(c){return c.tr});
out.sanspiste_note=E1c.J.notes[0]||"";
/* ── UNE INCRUSTATION (v2) : aucune sonde, un seul clip — et c'est DIT ──── */
var nAu=auVus.length;
var E1d=ECRAN({dur:16});
E1d.addAsset({job_id:72},"b-roll.mp4","video",5,"v2",0);
out.overlay_sondes=auVus.length-nAu;
out.overlay_pistes=E1d.etat().clips.map(function(c){return c.tr});
out.overlay_hist=E1d.J.hist;
out.overlay_note=E1d.J.notes[0]||"";
out.overlay_notes=E1d.J.notes.length;
/* ── UN SON (kind audio) : aucune sonde ─────────────────────────────────── */
nAu=auVus.length;
var E1e=ECRAN({dur:16});
E1e.addAsset({audio:"voix.wav"},"voix","audio",3,"a1",0);
out.audio_sondes=auVus.length-nAu;
out.audio_pistes=E1e.etat().clips.map(function(c){return c.tr});
/* ── LA PISTE DE DIALOGUE VERROUILLEE : le plan est pose, pas le jumeau,
   et c'est DIT ──────────────────────────────────────────────────────────── */
var E1f=ECRAN({dur:16,verrous:{a1:{l:!0}}});
E1f.addAsset({job_id:73},"parle2.mp4","video",5,"v1",0);
REPOND(OUI);
out.verrou_pistes=E1f.etat().clips.map(function(c){return c.tr});
out.verrou_note=E1f.J.notes[0]||"";
/* ── LE DOUBLON : le son est deja sur A1 a cette plage, pas de second ────── */
var E1g=ECRAN({dur:16,clips:[{tr:"a1",id:"a1_deja",label:"deja",start:0,end:5,
  src:{job_id:74},srcIn:0}]});
E1g.addAsset({job_id:74},"parle3.mp4","video",5,"v1",0);
REPOND(OUI);
out.doublon_pistes=E1g.etat().clips.map(function(c){return c.tr});
out.doublon_note=E1g.J.notes[0]||"";
/* ── LE VERROU DE RECURSION EST LE CACHE — la mutation jouee ─────────────── */
nAu=auVus.length;
var E1h=ECRAN({dur:16});
E1h.addAsset({job_id:99},"boucle.mp4","video",5,"v1",0);
REPOND_SANS_CACHE(OUI);           /* `done` sans ecriture : addAsset REDEMANDE */
out.verrou_sans_cache_sondes=auVus.length-nAu;
out.verrou_sans_cache_clips=E1h.etat().clips.length;
REPOND(OUI);                      /* avec l'ecriture : il pose et s'arrete */
out.verrou_avec_cache_sondes=auVus.length-nAu;
out.verrou_avec_cache_clips=E1h.etat().clips.length;
/* ── UN MEME FICHIER POSE DEUX FOIS N'EST SONDE QU'UNE FOIS ─────────────── */
nAu=auVus.length;
var E1i=ECRAN({dur:16});
E1i.addAsset({job_id:7},"sentry_bot.mp4","video",21.233,"v1",30);
out.cache_sondes=auVus.length-nAu;
out.cache_bornes=BORNES(E1i.etat().clips);
/* ── LE POINT DE DEPART N'EST PLUS RAMENE EN ARRIERE ─────────────────────── */
var E2=ECRAN({dur:16,ph:15.5});
E2.addAsset({job_id:8},"court.mp4","video",6,"v1",null);
REPOND(NON);
out.st_bornes=BORNES(E2.etat().clips);
out.st_dur=E2.etat().dur;
/* ── LA DECOUVERTE : RIEN N'EST ECRIT AVANT LA MESURE ────────────────────── */
/* Le verdict audio est MESURE sans duree (dur 0) : askDur doit encore partir,
   et c'est bien elle qui est mesuree ici, comme avant P12. */
askVus.length=0;
var E3=ECRAN({dur:16});
E3.addAsset({job_id:9},"Memecoin.mp4","video",0,"v1",3);
REPOND({has_audio:!1,dur:0,pourquoi:"mesure"});
out.ask_appels=askVus.length;
out.ask_src=askVus[0]?askVus[0][0]:null;
out.ask_avant_clips=E3.J.clips.length;
out.ask_avant_hist=E3.J.hist;
out.ask_avant_notes=E3.J.notes.length;
if(askVus[0])askVus[0][1].done(21.233);
out.ask_bornes=BORNES(E3.etat().clips);
out.ask_dur=E3.etat().dur;
out.ask_relance=askVus.length;
/* le verdict « mesure, sans flux, sans duree » est DIT non-sondable */
out.ask_note=E3.J.notes[0]||"";
/* LA DUREE EN PRIME : un verdict qui PORTE la duree epargne askDur, et le
   clip entre a cette longueur — une seule sonde pour les deux besoins. */
askVus.length=0;
var E3b=ECRAN({dur:16});
E3b.addAsset({job_id:90},"kapwing_sample.mp4","video",0,"v1",3);
REPOND({has_audio:!0,dur:15.973,pourquoi:"mesure"});
out.prime_askdur=askVus.length;
out.prime_bornes=BORNES(E3b.etat().clips);
out.prime_dur=E3b.etat().dur;
/* MESURE ECHOUEE : le verrou de recursion (un nombre NEGATIF), et le repli
   DIT. `ask_echec_relance` reste a 1 : la seconde passe ne redemande pas.
   Le verdict audio de job_id 9 est DEJA en cache (E3) : aucune sonde audio
   de plus — c'est `echec_sondes_audio` qui le mesure. */
askVus.length=0;nAu=auVus.length;
var E4=ECRAN({dur:16});
E4.addAsset({job_id:9},"Memecoin.mp4","video",0,"v1",3);
out.echec_sondes_audio=auVus.length-nAu;
if(askVus[0])askVus[0][1].done(0);
out.ask_echec_bornes=BORNES(E4.etat().clips);
out.ask_echec_relance=askVus.length;
out.ask_echec_note=E4.J.notes[0]||"";
/* ── svmApplyProject : LES IDENTIFIANTS EN DOUBLE DE LA SAUVEGARDE ───────── */
/* Les deux paires de la sauvegarde de l'utilisateur (v1u1_0 x2, v1u2_0 x2),
   les pistes de sa sauvegarde, le vestige A1. */
var SAUVE={ok:!0,has_assets:!0,saved:!0,name:"montage_bibliotheque",ratio:"9:16",
  duration:55,mix:{dialogue:-6},saved_at:"2026-09-06T10:00:00",
  v1_non_video:["v1u1_0"],
  tracks:[{id:"v3",kind:"video"},{id:"v2",kind:"video"},{id:"v1",kind:"video"},
    {id:"a1",kind:"audio",bus:"dialogue"},{id:"a2",kind:"audio",bus:"musique",loop:!0},
    {id:"a3",kind:"audio",bus:"sfx"},{id:"s1",kind:"subs"}],
  clips:[{tr:"a1",id:"a1_vo",label:"s1_drift",start:0,end:11.842,src:{audio:"s1_drift.mp3"},srcIn:0},
    {tr:"v1",id:"v1u1_0",label:"kapwing_sample",start:28.876,end:50.509,src:{job_id:"a54e"},srcIn:0},
    {tr:"v1",id:"v1u2_0",label:"Memecoin",start:0.079,end:16.079,src:{job_id:"9a8a"},srcIn:0},
    {tr:"v1",id:"v1u3_0",label:"demo",start:16.079,end:28.876,src:{job_id:"f331"},srcIn:2},
    {tr:"v1",id:"v1u1_0",label:"tweet",start:28.876,end:50.509,src:{job_id:"8407"},srcIn:0},
    {tr:"v1",id:"v1u2_0",label:"kapwing_sample",start:0.079,end:16.079,src:{job_id:"a54e"},srcIn:0},
    {tr:"s1",id:"s1cmtpobgr366",label:"Sous la surface,",start:0.079,end:0.819}]};
var EA=ECRAN({dur:16});
/* une COPIE de surface par apply : `v1_non_video` de SAUVE reste le temoin
   de « l'entree n'est pas mutee » (ap_nv_source). */
var apOk;try{apOk=EA.apply(Object.assign({},SAUVE))}catch(e){apOk="LEVE:"+e.name}
out.ap_ok=apOk;
var apCs=EA.J.clips.length?EA.etat().clips:[];
out.ap_ids=apCs.map(function(c){return c.id});
out.ap_ids_distincts=(function(){var seen={},n=0;apCs.forEach(function(c){
  if(!seen[c.id]){seen[c.id]=1;n++}});return n})();
out.ap_note=EA.J.notes[0]||"";
out.ap_notes=EA.J.notes.length;
out.ap_seq=EA.seq();
out.ap_sel=EA.J.sel;
out.ap_dirty=EA.J.dirtyV;
out.ap_nv=EA.projet().v1NonVideo;
out.ap_nv_source=SAUVE.v1_non_video;
/* SANS DOUBLON : aucune note, la sequence quand meme re-semee. */
var EA2=ECRAN({dur:16});
try{EA2.apply(Object.assign({},SAUVE,{clips:SAUVE.clips.slice(0,4)}))}catch(e){}
out.ap2_notes=EA2.J.notes.length;
out.ap2_seq=EA2.seq();
out.ap2_dirty=EA2.J.dirtyV;
out.ap2_nv=EA2.projet().v1NonVideo;
/* UNE CONSTRUCTION DEPUIS LA BIBLIOTHEQUE (saved faux) portant les memes
   doublons : renommes et dits, mais JAMAIS marquee modifiee — l'enregistrer
   en ferait la source a la place de la Bibliotheque. */
var EA3=ECRAN({dur:16});
try{EA3.apply(Object.assign({},SAUVE,{saved:!1}))}catch(e){}
out.ap3_dirty=EA3.J.dirtyV;
out.ap3_note=EA3.J.notes[0]||"";
out.ap3_ids_distincts=(function(){var seen={},n=0;
  (EA3.J.clips.length?EA3.etat().clips:[]).forEach(function(c){
    if(!seen[c.id]){seen[c.id]=1;n++}});return n})();
/* UN AJOUT APRES CHARGEMENT NE REPREND JAMAIS UN ID EXISTANT : re-seme, le
   compteur passe au-dessus (v1u4_0) ; non re-seme, `uniqueId` suffixe. */
var EB=ECRAN({dur:55,clips:apCs,seq:EA.seq()});
EB.addAsset({job_id:"neuf"},"neuf.mp4","video",4,"v1",0);
REPOND(NON);
out.apres_id=EB.etat().clips.length>apCs.length?EB.etat().clips[EB.etat().clips.length-1].id:null;
var EB2=ECRAN({dur:55,clips:apCs,seq:0});
EB2.addAsset({job_id:"neuf2"},"neuf2.mp4","video",4,"v1",0);
REPOND(NON);
out.apres_id_sans_semis=EB2.etat().clips.length>apCs.length?EB2.etat().clips[EB2.etat().clips.length-1].id:null;
out.apres_ids_distincts=(function(){var seen={},n=0,cs=EB2.etat().clips;cs.forEach(function(c){
  if(!seen[c.id]){seen[c.id]=1;n++}});return [n,cs.length]})();
window.DzTracks.askDur=vraiAsk;
window.DzTracks.askAudio=vraiAu;
out.ask_rendue=(window.DzTracks.askDur===vraiAsk&&window.DzTracks.askAudio===vraiAu);
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
        .replace("__CLIPDOWN__", _CLIPDOWN).replace("__DURCTL__", _DURCTL)
        .replace("__APPLY__", _APPLY))
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

# ── L'AJOUT : LE DEFAUT RAPPORTE, RETOURNE — ET SON JUMEAU (P12) ─────────
# « j'ai voulu ajouter trois videos depuis la bibliotheque, or la timeline est
# fixe ». Une source de 21,233 s posee a 0 dans un projet de 16 s : le clip
# entre ENTIER, et c'est la timeline qui grandit (22 s, l'arrondi au plafond
# de `fitDur`, pour que « 0:22 total » ne mente pas sur la fin du dernier
# clip). MUTATION :1156 (`en=Math.min(d,st+dzCl.len)`) -> le clip retombe a
# 0..16 et cette ligne rougit.
# DEPUIS P12, DEUX PAIRES DE BORNES : le plan sur V1 et son jumeau sur A1,
# memes bornes — le bouchon a repondu « a du son ». `add_ask == 0` est le
# second membre : une duree CONNUE ne fait rien demander a askDur. C'est une
# negation, et son conjoint est le clip pose a sa longueur juste a cote.
check("js_add_le_clip_entre_a_la_longueur_de_sa_source",
      w.get("add_bornes") == [[0, 21.233], [0, 21.233]] and w.get("add_ask") == 0
      and w.get("add_pistes") == ["v1", "a1"],
      f'{w.get("add_bornes")} pistes={w.get("add_pistes")} '
      f'mesures={w.get("add_ask")}')
# LA SONDE PART AVANT TOUTE ECRITURE, une fois, avec le `src` tel quel — et le
# rappel ne redemande pas (`au_relance == 1`, conjoint : le jumeau pose).
check("js_add_son_la_sonde_part_AVANT_toute_ecriture_et_une_seule_fois",
      w.get("au_appels") == 1 and w.get("au_src") == {"job_id": 7}
      and w.get("au_avant") == [0, 0, 0, 0] and w.get("au_relance") == 1
      and w.get("add_pistes") == ["v1", "a1"],
      f'appels={w.get("au_appels")} src={w.get("au_src")} '
      f'avant={w.get("au_avant")} relance={w.get("au_relance")}')
# LE JUMEAU, tel qu'il est ecrit : piste a1, identifiant a1u1_0 (le prefixe
# de piste echange, unique), libelle « … · son du plan », meme source, memes
# bornes, srcIn 0.
check("js_add_son_le_jumeau_est_la_copie_sonore_du_plan",
      w.get("add_jumeau") == {"tr": "a1", "id": "a1u1_0",
                              "label": "sentry_bot.mp4 · son du plan",
                              "start": 0, "end": 21.233, "src": {"job_id": 7},
                              "srcIn": 0}
      and w.get("add_ids") == ["v1u1_0", "a1u1_0"],
      f'{w.get("add_jumeau")} ids={w.get("add_ids")}')
# MUTATIONS :1163 (`if(!1)`), :1157 (`dzGrew=0`) et :1164 (`{dur:d}`) : les
# trois passent le texte, les trois rougissent ICI. `add_proj` est le journal
# des ecritures de `setProj` — un seul appel, avec la duree grandie.
check("js_add_la_timeline_s_allonge_pour_l_accueillir",
      w.get("add_dur") == 22 and w.get("add_proj") == [22],
      f'dur={w.get("add_dur")} ecritures={w.get("add_proj")}')
# L'AGRANDISSEMENT EST DIT, ET CHIFFRE DES DEUX BOUTS. La note porte AUSSI la
# longueur de la source (`dzCl.note`), la reserve d'historique, ET la phrase
# du jumeau (P12) : c'est la phrase entiere que l'utilisateur lit, en UNE
# note.
check("js_add_l_allongement_est_DIT_et_chiffre",
      "La timeline a été allongée de 0:16 à 0:22" in w.get("add_note", "")
      and "la longueur ENTIÈRE de la source" in w.get("add_note", "")
      and "NE raccourcit PAS la timeline" in w.get("add_note", ""),
      repr(w.get("add_note"))[:220])
check("js_add_son_la_note_dit_le_jumeau_la_piste_et_l_annulation",
      "Son du plan extrait sur A1" in w.get("add_note", "")
      and "« sentry_bot.mp4 · son du plan »" in w.get("add_note", "")
      and "retire les DEUX clips" in w.get("add_note", "")
      and w.get("add_notes") == 1,
      f'{repr(w.get("add_note"))[-260:]} notes={w.get("add_notes")}')
# UNE SEULE ENTREE D'HISTORIQUE, UNE SEULE ECRITURE DE CLIPS (deux clips dans
# UN concat), et c'est le PLAN qui est selectionne, pas le jumeau. CE QUE CE
# HARNAIS NE REPRODUIT PAS, DIT : dans le bundle, deux `setClips(clipsRef.
# current.concat(…))` dans le meme gestionnaire PERDENT le premier clip —
# `clipsRef.current=clips` n'est rafraichi qu'au rendu (bundle 1723). Le
# `setClips` d'ECRAN, lui, rafraichit `clipsRef.current` SUR-LE-CHAMP :
# la mutation « jumeau dans un second setClips » y laisse les DEUX clips
# (add_bornes reste [[0,21.233],[0,21.233]], mesure le 06/09/2026). La
# garde contre cette mutation est donc le COMPTE d'ecritures `[2]` ci-
# dessous, plus l'epingle statique `P12_un_seul_concat` — pas la perte.
check("js_add_une_seule_entree_d_historique",
      w.get("add_hist") == 1 and w.get("add_sel") == ["v1u1_0"]
      and w.get("add_ecritures") == [2],
      f'hist={w.get("add_hist")} sel={w.get("add_sel")} '
      f'ecritures={w.get("add_ecritures")}')
# LE VERDICT « MUET » : un seul clip, un seul historique, et c'est DIT.
check("js_add_son_muet_un_seul_clip_et_c_est_DIT",
      w.get("muet_bornes") == [[0, 16]] and w.get("muet_pistes") == ["v1"]
      and "n'a pas de piste audio" in w.get("muet_note", "")
      and w.get("muet_hist") == 1,
      f'{w.get("muet_bornes")} {w.get("muet_pistes")} hist={w.get("muet_hist")} '
      f'{repr(w.get("muet_note"))[-160:]}')
# PAS DE PISTE DE DIALOGUE (a2 bouclee ne compte pas) : un seul clip, la note
# dit « + piste audio ».
check("js_add_son_sans_piste_de_dialogue_le_dit_et_ne_prend_pas_la_musique",
      w.get("sanspiste_pistes") == ["v1"]
      and "« + piste audio »" in w.get("sanspiste_note", "")
      and "MUETTE" in w.get("sanspiste_note", ""),
      f'{w.get("sanspiste_pistes")} {repr(w.get("sanspiste_note"))[-200:]}')
# UNE INCRUSTATION ET UN SON NE SONT PAS SONDES — negations, dont le conjoint
# est le clip pose (un seul, sur la piste demandee).
check("js_add_son_une_incrustation_n_est_pas_sondee",
      w.get("overlay_sondes") == 0 and w.get("overlay_pistes") == ["v2"]
      and w.get("overlay_hist") == 1,
      f'sondes={w.get("overlay_sondes")} pistes={w.get("overlay_pistes")} '
      f'hist={w.get("overlay_hist")}')
# … ET C'EST DIT (tour 2) : la porte « Envoyer vers → Montage » vise « v2 »
# en dur (greffon libsend du bundle, 1 occurrence, mesure) — un plan y
# arrivait sans son et sans un mot. La note nomme la piste, dit que rien n'a
# ete extrait et renvoie au bouton avec sa cible ; le conjoint est la note
# de E1 (V1, jumeau pose), qui ne porte PAS cette phrase. MUTATION :
# `overlayNote` rend "" -> rouge ici.
check("js_add_son_une_incrustation_est_DITE_et_renvoie_au_bouton",
      "Posé sur V2 (incrustation)" in w.get("overlay_note", "")
      and "n'a PAS été extrait" in w.get("overlay_note", "")
      and "« Extraire le son → A1 »" in w.get("overlay_note", "")
      and w.get("overlay_notes") == 1
      and "n'a PAS été extrait" not in w.get("add_note", ""),
      f'notes={w.get("overlay_notes")} {repr(w.get("overlay_note"))[-200:]}')
check("js_add_son_un_son_n_est_pas_sonde",
      w.get("audio_sondes") == 0 and w.get("audio_pistes") == ["a1"],
      f'sondes={w.get("audio_sondes")} pistes={w.get("audio_pistes")}')
# LA PISTE DE DIALOGUE VERROUILLEE : le plan est pose, pas le jumeau, DIT.
check("js_add_son_piste_verrouillee_pose_le_plan_sans_jumeau_et_le_dit",
      w.get("verrou_pistes") == ["v1"]
      and "A1 verrouillée" in w.get("verrou_note", ""),
      f'{w.get("verrou_pistes")} {repr(w.get("verrou_note"))[-160:]}')
# LE DOUBLON : le son est deja sur A1 a cette plage, pas de second exemplaire.
check("js_add_son_pas_de_second_exemplaire_et_c_est_DIT",
      w.get("doublon_pistes") == ["a1", "v1"]
      and "déjà présent sur A1" in w.get("doublon_note", ""),
      f'{w.get("doublon_pistes")} {repr(w.get("doublon_note"))[-160:]}')
# LE VERROU DE RECURSION EST LE CACHE, ET RIEN D'AUTRE — la mutation jouee :
# une reponse SANS ecriture du cache fait REDEMANDER (2 sondes, 0 clip), la
# meme reponse AVEC l'ecriture pose et s'arrete (2 sondes en tout, 2 clips).
check("js_add_son_le_verrou_de_recursion_EST_le_cache",
      w.get("verrou_sans_cache_sondes") == 2
      and w.get("verrou_sans_cache_clips") == 0
      and w.get("verrou_avec_cache_sondes") == 2
      and w.get("verrou_avec_cache_clips") == 2,
      f'sans={w.get("verrou_sans_cache_sondes")}/{w.get("verrou_sans_cache_clips")} '
      f'avec={w.get("verrou_avec_cache_sondes")}/{w.get("verrou_avec_cache_clips")}')
# UN MEME FICHIER POSE DEUX FOIS N'EST SONDE QU'UNE FOIS : job_id 7 est en
# cache depuis E1 — zero sonde, et le jumeau est pose quand meme (a 30 s).
# LES BORNES SONT ARRONDIES AU MILLIEME ICI, ET C'EST DIT : `en=st+dzCl.len`
# n'est pas arrondi dans le bundle, et 30 + 21,233 rend 51,233000000000004
# en flottant (MESURE le 06/09/2026). Bruit PREEXISTANT (P11 arrondit `len`,
# pas la somme), invisible a st = 0 — declare en dette, pas corrige ici.
check("js_add_son_un_meme_fichier_n_est_sonde_qu_une_fois",
      w.get("cache_sondes") == 0
      and [[round(a, 3), round(b, 3)] for a, b in (w.get("cache_bornes") or [])]
      == [[30, 51.233], [30, 51.233]],
      f'sondes={w.get("cache_sondes")} {w.get("cache_bornes")}')
# MUTATION :1142 : la tete de lecture a 15,5 s dans un projet de 16 s. Le clip
# doit atterrir A 15,5 — `Math.max(0,d-1)` le ramenait a 15, `d-2` a 14.
check("js_add_le_point_de_depart_n_est_plus_ramene_en_arriere",
      w.get("st_bornes") == [[15.5, 21.5]] and w.get("st_dur") == 22,
      f'{w.get("st_bornes")} dur={w.get("st_dur")}')
# ── LA DECOUVERTE (P11) ───────────────────────────────────────────────────
# MUTATION :1152 (`if(!1&&DzTracks.needDur(…))`) : la mesure ne part jamais et
# tout entre a 6 s. Les trois comptes a zero sont des NEGATIONS — leur
# conjoint est l'appel MESURE et le `src` transmis tel quel. Depuis P12 le
# verdict audio (sans duree) precede : askDur part APRES lui, toujours avant
# toute ecriture.
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
# NON-SONDABLE, SUR LE CHEMIN EXECUTE : le verdict de E3 (mesure, sans flux,
# sans duree — le fichier de 0 octet) est DIT « n'a pas pu être sondée »,
# jamais « n'a pas de piste audio » ; le conjoint est la note de E1b (muet,
# duree 21,233) qui, elle, le dit.
check("js_add_son_non_sondable_est_DIT_et_n_est_pas_dit_muet",
      "n'a pas pu être sondée" in w.get("ask_note", "")
      and "fichier vide ou illisible" in w.get("ask_note", "")
      and "n'a pas de piste audio" not in w.get("ask_note", "")
      and "n'a pas de piste audio" in w.get("muet_note", ""),
      f'{repr(w.get("ask_note"))[-200:]} muet={repr(w.get("muet_note"))[-80:]}')
# LA DUREE EN PRIME (P12) : un verdict qui PORTE la duree epargne askDur
# (zero appel — negation dont le conjoint est le clip pose A CETTE longueur,
# 15,973 s, avec son jumeau).
check("js_add_son_la_duree_en_prime_epargne_askDur",
      w.get("prime_askdur") == 0
      and w.get("prime_bornes") == [[3, 18.973], [3, 18.973]]
      and w.get("prime_dur") == 19,
      f'askDur={w.get("prime_askdur")} {w.get("prime_bornes")} '
      f'dur={w.get("prime_dur")}')
# MESURE ECHOUEE : le verrou de recursion tient (UNE demande, pas deux) et le
# repli est DIT — avec l'accord de la branche video. Et le verdict audio de
# job_id 9, en cache depuis E3, n'est PAS redemande.
check("js_add_une_mesure_echouee_ne_reboucle_pas_et_le_DIT",
      w.get("ask_echec_bornes") == [[3, 9]]
      and w.get("ask_echec_relance") == 1
      and w.get("echec_sondes_audio") == 0
      and "Cette vidéo a été posée à 6 s" in w.get("ask_echec_note", "")
      and w.get("ask_rendue") is True,
      f'{w.get("ask_echec_bornes")} relances={w.get("ask_echec_relance")} '
      f'audio={w.get("echec_sondes_audio")} '
      f'{repr(w.get("ask_echec_note"))[:160]}')
# ── svmApplyProject : LES IDENTIFIANTS EN DOUBLE (fait n°3) ───────────────
# La sauvegarde de l'utilisateur porte v1u1_0 deux fois et v1u2_0 deux fois.
# Charges, les sept clips ressortent avec SEPT identifiants distincts, le
# premier de chaque paire garde le sien, et c'est DIT (une note, qui nomme
# les renommages). MUTATION : retirer `dedupeIds` de R_M22C -> 5 distincts.
check("js_apply_les_doublons_sont_renommes_et_c_est_DIT",
      w.get("ap_ok") is True and w.get("ap_ids_distincts") == 7
      and w.get("ap_ids") == ["a1_vo", "v1u1_0", "v1u2_0", "v1u3_0",
                              "v1u1_0_2", "v1u2_0_2", "s1cmtpobgr366"]
      and w.get("ap_notes") == 1
      and "2 clips portaient un identifiant déjà pris" in w.get("ap_note", "")
      and "v1u1_0 → v1u1_0_2" in w.get("ap_note", "")
      and "v1u2_0 → v1u2_0_2" in w.get("ap_note", "")
      and "ce sera enregistré automatiquement dans un instant" in w.get("ap_note", ""),
      f'ok={w.get("ap_ok")} distincts={w.get("ap_ids_distincts")} '
      f'{w.get("ap_ids")} notes={w.get("ap_notes")} '
      f'{repr(w.get("ap_note"))[:200]}')
# LE COMPTEUR EST RE-SEME au plus grand u<n> de la sauvegarde (3), et le
# premier plan V1 reste selectionne comme avant. Sans doublon : pas de note,
# le compteur re-seme quand meme (conjoint de la negation).
check("js_apply_re_seme_le_compteur_et_ne_parle_que_s_il_a_renomme",
      w.get("ap_seq") == 3 and w.get("ap_sel") == ["v1u1_0"]
      and w.get("ap2_notes") == 0 and w.get("ap2_seq") == 3,
      f'seq={w.get("ap_seq")} sel={w.get("ap_sel")} '
      f'sans_doublon: notes={w.get("ap2_notes")} seq={w.get("ap2_seq")}')
# LA REPARATION EST PERSISTEE (tour 2) : `setDirty` recoit VRAI sur une
# sauvegarde renommee — l'autosauvegarde, gardee par `dirty` (bundle
# `if(proj.demo||!dirty)return;`), ecrit les ids repares 1,5 s plus tard, et
# c'est le SEUL enregistrement qui existe (`svmDoSave(` : trois sites, aucun
# bouton, aucun raccourci ; « Enregistrer sous… » cree un projet neuf —
# mesure le 06/09/2026). FAUX sans doublon (conjoint), et la note le dit.
# MUTATION : remettre `setDirty(!1)` dans R_M22D -> ap_dirty [False], cette
# ligne seule.
check("js_apply_la_reparation_arme_l_autosauvegarde_et_le_dit",
      w.get("ap_dirty") == [True] and w.get("ap2_dirty") == [False]
      and "ce sera enregistré automatiquement dans un instant" in w.get("ap_note", "")
      and w.get("ap2_notes") == 0,
      f'dirty={w.get("ap_dirty")} sans_doublon={w.get("ap2_dirty")} '
      f'{repr(w.get("ap_note"))[-120:]}')
# UNE CONSTRUCTION DE BIBLIOTHEQUE (saved faux) aux memes doublons : renommee
# et DITE, mais jamais marquee modifiee — l'enregistrer en ferait la source
# a la place de la Bibliotheque ; la note dit que rien n'est enregistre.
check("js_apply_une_construction_de_bibliotheque_n_est_jamais_marquee_modifiee",
      w.get("ap3_dirty") == [False] and w.get("ap3_ids_distincts") == 7
      and "rien n'est enregistré tant que vous ne modifiez rien" in w.get("ap3_note", "")
      and "enregistré automatiquement" not in w.get("ap3_note", ""),
      f'dirty={w.get("ap3_dirty")} distincts={w.get("ap3_ids_distincts")} '
      f'{repr(w.get("ap3_note"))[-160:]}')
# `v1_non_video` SUIT LE RENOMMAGE : le contrat backend (montage_service,
# docstring de montage_project) en fait une liste d'IDENTIFIANTS, et l'ecran
# marque par `indexOf(c.id)` — l'id neuf est AJOUTE (les deux exemplaires
# etaient marques, ils le restent). Sans doublon la liste est rendue telle
# quelle, et l'entree n'est pas mutee (conjoints).
check("js_apply_v1NonVideo_suit_le_renommage",
      w.get("ap_nv") == ["v1u1_0", "v1u1_0_2"] and w.get("ap2_nv") == ["v1u1_0"]
      and w.get("ap_nv_source") == ["v1u1_0"],
      f'nv={w.get("ap_nv")} sans_doublon={w.get("ap2_nv")} '
      f'source={w.get("ap_nv_source")}')
# UN AJOUT APRES CHARGEMENT NE REPREND JAMAIS UN ID EXISTANT — par les DEUX
# voies : re-seme, le compteur passe au-dessus (v1u4_0 ; MUTATION : retirer
# le re-semis -> v1u1_0_3) ; non re-seme, `uniqueId` suffixe (v1u1_0_3, car
# v1u1_0 ET v1u1_0_2 sont deja pris ;
# MUTATION : retirer `uniqueId` de R_M22A -> v1u1_0, en double).
check("js_apply_puis_ajout_ne_reprend_jamais_un_id_existant",
      w.get("apres_id") == "v1u4_0"
      and w.get("apres_id_sans_semis") == "v1u1_0_3"
      and w.get("apres_ids_distincts") == [8, 8],
      f'reseme={w.get("apres_id")!r} sans_semis={w.get("apres_id_sans_semis")!r} '
      f'distincts={w.get("apres_ids_distincts")}')
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

# ══ ETAPE 4 — LA BARRE ET SON ONGLET ══════════════════════════════════════
print("\n[6-bis] la barre d'outils — l'onglet, la barre, l'ouverture, la cle")

# ── LE CONTENU DU §2.4, LU DANS LE HANDOFF ────────────────────────────────
# Meme protocole que les dix traces du §3 : ni la couche ni ce banc ne
# recopient le tableau, les deux le lisent ici.
_PLAN_SPEC = []
try:
    _s24 = _HO[_HO.index("### 2.4 Contenu, verbatim"):
               _HO.index("## 3. Les neuf icônes")]
    for _l in _s24.splitlines():
        if not _l.startswith("| `"):
            continue
        _c = [x.strip() for x in _l.strip().strip("|").split("|")]
        if len(_c) != 4:
            continue
        _PLAN_SPEC.append((_c[0].strip("`"), _c[1],
                           [x.strip().strip("`") for x in _c[2].split("·")],
                           _c[3].strip("*")))
except BaseException as _e:
    print(f"  ----  §2.4 du handoff illisible : {temoin(_e)}")
    _PLAN_SPEC = []
check("tb_le_contenu_du_2_4_est_lisible_dans_le_handoff",
      len(_PLAN_SPEC) == 5
      and sum(len(b) for _t, _h, b, _y in _PLAN_SPEC) == 9
      and [t for t, _h, _b, _y in _PLAN_SPEC] == [
          "PISTES", "BIBLIOTHÈQUE", "MOT — sélection", "AJOUTS", "PROJETS"],
      f"{len(_PLAN_SPEC)} ligne(s) extraites : "
      f"{[t for t, _h, _b, _y in _PLAN_SPEC]}")
# LA COUCHE PORTE CE TABLEAU, en-tetes, suffixe, libelles et type. L'en-tete
# du groupe MOT est recompose (`t` + espace + `suf`) : c'est la forme du
# §2.2b, qui separe le mot du suffixe pour pouvoir le peindre a part.
_PLAN_VU = d.get("tb_plan")
check("tb_la_couche_porte_le_contenu_verbatim_du_2_4",
      len(_PLAN_SPEC) == 5 and isinstance(_PLAN_VU, list)
      and len(_PLAN_VU) == 5
      and all(
          (_PLAN_VU[_i][1] + (" " + _PLAN_VU[_i][2] if _PLAN_VU[_i][2] else ""))
          == _PLAN_SPEC[_i][0]
          and _PLAN_VU[_i][4] == _PLAN_SPEC[_i][2]
          and _PLAN_VU[_i][3] == _PLAN_SPEC[_i][3]
          for _i in range(5)),
      f"plan={_PLAN_VU}")
# LES NEUF BOUTONS PORTENT LES NEUF ICONES DU §3, une chacune, et la dixieme
# (la poignee) n'est PAS un bouton — elle est la poignee de la barre.
check("tb_les_neuf_boutons_portent_les_neuf_icones_du_3_une_chacune",
      len(_TB_SPEC) == 10 and isinstance(d.get("tb_plan_icones"), list)
      and len(d["tb_plan_icones"]) == 9
      and sorted(d["tb_plan_icones"]) == sorted(set(_TB_SPEC) - {"poignee"}),
      f'{d.get("tb_plan_icones")}')
check("tb_les_cinq_colonnes_sont_les_cinq_groupes_dans_l_ordre",
      d.get("tb_plan_groupes") == d.get("tb_groupes")
      and d.get("tb_plan_groupes") == ["pistes", "biblio", "mot", "ajouts",
                                       "projets"],
      f'{d.get("tb_plan_groupes")} vs {d.get("tb_groupes")}')

# ── LA PERSISTANCE (§4.4) — L'ECART DE NOMMAGE, DECLARE DANS LES DEUX SENS ─
# Le §4.4 demande `deepotus.toolbar.open` ; la maison dit `dz_*`. MESURE le
# 05/09/2026 sur le bundle livre : VINGT-CINQ cles `dz_*` distinctes contre
# TROIS `deepotus.*` — et les trois vivent dans frontend/src, hors de portee
# de cette chaine. Le §4.4 lui-meme tranche : « dans le même espace de
# nommage que les panneaux existants ». CETTE LIGNE REJOUE LA MESURE : le
# jour ou la maison bascule vers `deepotus.*`, elle rougit et la clef doit
# etre rediscutee — elle ne se perime pas en silence.
_CLES = set(re.findall(r'(?:localStorage|sessionStorage)\.'
                       r'(?:get|set|remove)Item\(\s*"([^"]+)"', s))
_DZ = {k for k in _CLES if k.startswith("dz_")}
_DEEP = {k for k in _CLES if k.startswith("deepotus.")}
check("tb_la_convention_de_cles_de_la_maison_est_toujours_dz_",
      len(_DZ) >= 20 and len(_DZ) > len(_DEEP) * 4
      and "dz_svm_theme" in _DZ and "dz_narr_open" in _DZ,
      f"{len(_DZ)} cles dz_* contre {len(_DEEP)} deepotus.* — "
      f"deepotus.*={sorted(_DEEP)}")
# LA CLE EST POSEE PAR UNE CONSTANTE, pas par un litteral en ligne : la
# regex ci-dessus, qui lit `getItem("…")`, ne la voit donc pas — et c'est
# voulu, une cle nommee une fois ne peut pas diverger d'elle-meme. Ce qui se
# mesure ici : le litteral EST dans le bundle, une seule fois, il porte le
# prefixe de la maison ET celui de cet ecran (`dz_svm_`, comme
# `dz_svm_theme`), il n'entre en collision avec AUCUNE cle deja employee, et
# le nom du handoff n'est nulle part — l'ecart est fait, pas seulement dit.
_LIT = '"' + str(d.get("tb_cle")) + '"'
check("tb_la_cle_suit_la_maison_et_le_prefixe_de_cet_ecran",
      d.get("tb_cle") == "dz_svm_tb_open"
      and d["tb_cle"].startswith("dz_svm_") and s.count(nl(_LIT)) == 1
      and d["tb_cle"] not in _DZ
      and '"deepotus.toolbar' not in s
      and "'deepotus.toolbar" not in s,
      f'cle={d.get("tb_cle")!r} litteraux={s.count(nl(_LIT))} '
      f'collision={d.get("tb_cle") in _DZ}')
# LA FORME suit `dz_narr_open` : "1" / "0". Le magasin est INJECTE, donc la
# ligne mesure QUELLE cle est lue et QUOI est ecrit — pas seulement que la
# fonction rend un booleen.
# ETAPE 6 — LE DEFAUT S'INVERSE, ET C'EST LA DECISION DE CETTE ETAPE.
# L'etape 4 lisait "1" comme ouvert et TOUT LE RESTE comme replie, en ecrivant
# sa raison : « tant que l'etape 6 n'a pas retire les neuf controles, ouvrir
# par defaut montrerait une barre qui double une rangee deja la ». Cette
# etape-ci retire les neuf. La raison a disparu ET SON CONTRAIRE EST ARRIVE :
# replie par defaut, un utilisateur qui n'a jamais vu l'onglet n'aurait AUCUN
# moyen d'ajouter une piste, de lier la Bibliotheque ni d'ouvrir ses projets.
# Le §9 s'interdit exactement cet etat.
# LA MEMOIRE EST PRESERVEE DANS LES DEUX SENS, et c'est ce que les quatre
# lectures mesurent : "0" replie (qui a replie reste replie), "1" ouvre (qui a
# ouvert reste ouvert), et SEULE l'absence de cle change de sens. La valeur
# inconnue ("oui") ouvre aussi : la cle n'est jamais ecrite autrement que par
# `tbOpenSet`, donc une valeur etrangere vient d'ailleurs et ne doit pas
# priver l'ecran de ses neuf actions.
check("tb_open_seul_0_replie_et_l_absence_de_cle_ouvre",
      d.get("tb_open_lit_1") == [True, "dz_svm_tb_open"]
      and d.get("tb_open_lit_0") is False
      and d.get("tb_open_lit_absent") is True
      and d.get("tb_open_lit_autre") is True,
      f'"1"={d.get("tb_open_lit_1")} "0"={d.get("tb_open_lit_0")} '
      f'absente={d.get("tb_open_lit_absent")} '
      f'inconnue={d.get("tb_open_lit_autre")}')
check("tb_open_ecrit_la_bonne_cle_et_rend_ce_qu_elle_a_ecrit",
      d.get("tb_open_ecrit") == [True, ["dz_svm_tb_open", "1"]]
      and d.get("tb_open_ecrit_faux") == [False, ["dz_svm_tb_open", "0"]],
      f'{d.get("tb_open_ecrit")} {d.get("tb_open_ecrit_faux")}')
# UN MAGASIN QUI LEVE — navigation privee, politique de site restrictive.
# La barre perd la MEMOIRE, jamais la bascule : `tbOpenSet` rend quand meme
# la valeur demandee, donc l'ecran suit le clic.
# ETAPE 6 : SANS MEMOIRE, LA BARRE S'OUVRE. C'est le meme raisonnement que
# pour l'absence de cle, pousse au cas ou il n'y a PAS de magasin du tout :
# mieux vaut montrer les neuf actions que les cacher pour toujours a qui
# navigue en prive. La bascule, elle, repond quand meme — c'est le second
# terme, et il n'a pas change.
check("tb_un_magasin_indisponible_ouvre_et_ne_casse_pas_la_bascule",
      d.get("tb_open_magasin_qui_leve") == [True, True]
      and d.get("tb_open_sans_magasin") is True,
      f'{d.get("tb_open_magasin_qui_leve")} '
      f'{d.get("tb_open_sans_magasin")}')

# ── LE CABLAGE : LES NEUF, CABLES (ETAPE 7) ────────────────────────
# La regle du lot n'a pas change : la ou l'action existe, on la CABLE — la
# barre est un nouveau point d'entree, pas une nouvelle implementation — et
# la ou l'ecran n'a rien donne, le bouton est ETEINT et son `title` le dit.
# CE QUI A CHANGE : les deux qui restaient eteints le sont maintenant AVEC
# leur hote. `emoji` tenait a un `fetch` enferme dans son bouton, sorti en
# `dzmEmojiGo` ; `projets` a une ouverture enfermee dans son popover, ouverte
# par une DEMANDE (`openReq`). Ni l'un ni l'autre n'a ete reecrit.
_CABLES = ["bibliotheque", "couleur", "emoji", "glow", "piste-audio",
           "piste-video", "projets", "rebond", "texte"]
check("tb_le_cablage_rend_une_entree_par_bouton_du_plan",
      d.get("tb_c_cles") == sorted(set(_TB_SPEC) - {"poignee"}),
      f'{d.get("tb_c_cles")}')
check("tb_les_neuf_boutons_sont_cables_et_aucun_n_est_eteint",
      d.get("tb_c_actions") == _CABLES
      and d.get("tb_c_eteints") == []
      and len(_CABLES) == 9,
      f'cables={d.get("tb_c_actions")} eteints={d.get("tb_c_eteints")}')
# CE QUE L'ACTION TRANSMET, pas seulement qu'elle a ete appelee : une piste
# video nait EN HAUT, une piste audio juste au-dessus des sous-titres, et les
# identifiants sont les plus petits libres — c'est `dzmAdd`, la meme fonction
# que le bouton du bandeau. Une action qui appellerait autre chose rendrait
# une autre liste.
check("tb_pistes_video_et_audio_appellent_la_meme_action_que_le_bandeau",
      d.get("tb_c_video") == ["v2", "v1", "a1", "s1"]
      and d.get("tb_c_audio") == ["v1", "a1", "a2", "s1"],
      f'video={d.get("tb_c_video")} audio={d.get("tb_c_audio")}')
check("tb_lier_ouvre_le_selecteur_sur_la_piste_video_resolue",
      d.get("tb_c_lier") == ["v1"], f'{d.get("tb_c_lier")}')
# SANS PISTE VIDEO : eteint, aucune action, et un titre QUI DIFFERE — il
# nomme la sortie au lieu de laisser deviner.
_LT = d.get("tb_c_lier_titres")
check("tb_lier_s_eteint_sans_piste_video_et_le_dit_autrement",
      d.get("tb_c_lier_sans_video") == [True, None]
      and isinstance(_LT, list) and len(_LT) == 2
      and _LT[0] != _LT[1] and len(_LT[0]) > 40 and len(_LT[1]) > 40
      and "V1" in _LT[0] and "V1" not in _LT[1],
      f'{d.get("tb_c_lier_sans_video")} titres={_LT}')
# MOT — trois bascules ; celle qui vaut la valeur du projet est allumee, et
# le clic transmet la valeur du bouton.
check("tb_les_trois_bascules_de_MOT_refletent_la_valeur_du_projet",
      d.get("tb_c_mot") == [[True, False, False], [True, True, False],
                            [True, False, False]]
      and d.get("tb_c_mot_defaut") == [True, False, False],
      f'{d.get("tb_c_mot")} defaut={d.get("tb_c_mot_defaut")}')
check("tb_le_clic_d_une_bascule_de_MOT_transmet_SA_valeur",
      d.get("tb_c_mot_clic") == ["glow", "couleur"],
      f'{d.get("tb_c_mot_clic")}')
# LES TROIS CLES SORTENT DE LA TABLE DES ANIMATIONS, et leurs titres AUSSI :
# une seconde liste aurait divergé de celle que la chip du bandeau emploie.
check("tb_les_trois_bascules_sortent_de_la_table_des_animations",
      d.get("tb_c_mot_cles") == ["couleur", "rebond", "glow"]
      and d.get("tb_c_mot_titre_reprend") == [True, True, True],
      f'{d.get("tb_c_mot_cles")} {d.get("tb_c_mot_titre_reprend")}')
check("tb_texte_est_une_bascule_cablee_sur_l_etat_du_panneau",
      d.get("tb_c_texte") == [True, True, False]
      and d.get("tb_c_texte_clic") == 1
      and d.get("tb_c_texte_eteint") is False,
      f'{d.get("tb_c_texte")} clic={d.get("tb_c_texte_clic")} '
      f'eteint={d.get("tb_c_texte_eteint")}')
# LES DEUX QUI AVAIENT RESISTE A L'ETAPE 4 : VIVANTS avec leur hote, eteints
# sans lui. Les deux faces sont mesurees — sans la premiere, un cablage qui
# aurait perdu les deux actions passerait la seconde ; sans la seconde, un
# cablage qui allumerait tout sans rien verifier passerait la premiere.
_VI = d.get("tb_c_vivants")
check("tb_emoji_et_projets_sont_cables_et_leur_titre_dit_ce_qu_ils_font",
      isinstance(_VI, list) and len(_VI) == 2
      and all(x[0] is False and x[1] == "function" and len(x[2]) > 120
              for x in _VI)
      and _VI[0][2] != _VI[1][2],
      f'{_VI}')
# SANS HOTE : eteints, sans action, et la MEME phrase — c'est le meme motif
# (l'ecran ne leur a rien donne), et deux formulations pour une seule cause
# auraient laisse croire a deux. Elle differe des deux titres vivants
# ci-dessus, et la ligne l'exige.
_MU = d.get("tb_c_muets")
check("tb_emoji_et_projets_s_eteignent_sans_hote_et_le_disent",
      isinstance(_MU, list) and len(_MU) == 2
      and all(x[0] is True and x[1] is None and len(x[2]) > 60 for x in _MU)
      and _MU[0][2] == _MU[1][2]
      and isinstance(_VI, list) and len(_VI) == 2
      and _MU[0][2] != _VI[0][2] and _MU[1][2] != _VI[1][2],
      f'{_MU}')
# AUCUN TITRE NE RENVOIE PLUS A UNE ETAPE A VENIR. Conjoints positifs : neuf
# titres, tous longs, tous distincts — sans eux la negation serait vraie d'un
# cablage vide.
_TI = d.get("tb_c_titres")
check("tb_aucun_titre_ne_promet_plus_une_etape_a_venir",
      isinstance(_TI, list) and len(_TI) == 9
      and len(set(_TI)) == 9 and all(len(t) > 60 for t in _TI)
      and not any(("étape 7" in t) or ("étape 8" in t)
                  or ("pour l'instant" in t) or ("pas encore" in t)
                  for t in _TI),
      f'{[t[:40] for t in (_TI or [])]}')
# ET LA PHRASE QUI LES PORTAIT A DISPARU DE LA COUCHE : une fonction morte
# injectee dans le bundle est une fonction morte de plus. Conjoint positif :
# le mot survit dans un COMMENTAIRE (qui dit pourquoi elle est partie), il ne
# survit pas dans le code.
check("tb_la_phrase_des_boutons_eteints_a_ete_retiree_du_code",
      "function dzmTbEtape7(" not in src
      and "dzmTbEtape7" not in _code(src)
      and "dzmTbEtape7" in src
      and len(_code(src)) > 60000,
      "dzmTbEtape7 vit encore dans le code de la couche")
# UN CABLAGE SANS HOTE n'allume RIEN : c'est l'etat qu'aurait la barre si la
# section du patcher perdait ses proprietes, et il doit etre inoffensif.
check("tb_un_cablage_sans_hote_eteint_les_neuf_boutons",
      d.get("tb_c_vide") == [9, 0], f'{d.get("tb_c_vide")}')

# ── LE DOCK, LU DANS LA SOURCE ────────────────────────────────────────────
# C'est le seul morceau a hooks du lot, donc le seul que node ne joue pas :
# ce que cette ligne epingle est exactement ce que la mesure ne peut pas
# atteindre. ELLE A ETE ECRITE APRES UNE MUTATION QUI PASSAIT : retirer
# l'appel a `dzmTbFrame` du Dock — donc supprimer la restauration sans
# animation du §4.4 — laissait le banc a 643/0, parce que `dzmTbFrame` etait
# mesuree pour elle-meme et personne ne verifiait qu'on l'APPELLE.
# Les bornes de taille sont un conjoint positif : sans elles, toutes les
# negations seraient vraies d'un bloc introuvable.
_i_dk = src.find("function DzmToolDock(o){")
_j_dk = src.find("\n/* ", _i_dk) if _i_dk >= 0 else -1
_DOCK = src[_i_dk:_j_dk] if 0 <= _i_dk < _j_dk else "DOCK-INTROUVABLE"
# ETAPE 6 : `dzmBdTour(bd,bdMem.current)` REJOINT LA LISTE, et pour la meme
# raison que `dzmTbFrame` a l'etape 4 — la fonction est mesuree pour
# elle-meme plus bas, mais RIEN ne dirait que le Dock l'APPELLE. Le bandeau
# est trouve par `dzmTbAncetre(bar.current,"svm-trans")` : le jeton porte la
# classe, sans quoi un remontee vers un autre parent passerait inapercue.
check("tb_le_dock_restaure_persiste_rend_les_deux_et_serre_le_bandeau",
      # LES BORNES ENCADRENT LES DEUX FINS DE LIGNE : la copie de travail est
      # en CRLF, un clone frais peut etre en LF, et le Dock pese ~600 octets
      # de plus dans le premier cas. Une borne calee sur l'un des deux
      # rougirait sur l'autre sans rien mesurer de vrai.
      2500 < len(_DOCK) < 16000
      and "x.useState(dzmTbOpenGet)" in _DOCK
      and "dzmTbOpenSet(!v)" in _DOCK and "dzmTbOpenSet(!1)" in _DOCK
      and "x.useEffect(" in _DOCK and "dzmTbFrame(" in _DOCK
      and "DzmToolTab({" in _DOCK and "DzmToolBar({" in _DOCK
      # ETAPE 8 : le cablage est HISSE hors du rendu (il sert AUSSI a savoir
      # quels boutons sont atteignables), et la barre le recoit tel quel.
      # Les DEUX jetons, sinon un `items:items` sans source resterait vert.
      and "var items=dzmTbCablage(dzmTbHote(o,emoji,!!emo));" in _DOCK
      and "items:items," in _DOCK
      and "anim:anim" in _DOCK
      and 'dzmTbAncetre(bar.current,"svm-trans")' in _DOCK
      and "dzmBdTour(bd,bdMem.current)" in _DOCK,
      f"dock={len(_DOCK)} o : {_DOCK[:160]!r}")
# LE DEPORT PASSE PAR LE DOCK, ET C'EST LA SEULE PIECE QUE NODE NE JOUE PAS :
# le cœur, le geste, la mesure des rectangles et le clavier sont tous joues
# plus haut, mais RIEN ne dirait qu'ils sont APPELES. Meme parade que pour
# `dzmTbFrame` a l'etape 4 — la mutation qui avait fonde cette ligne
# (retirer l'appel, garder la fonction) laissait le banc entierement vert.
# Chaque jeton est une piece differente du §4.2 : la restauration, le geste,
# la geometrie figee a la saisie, l'ecriture au relachement, le clavier du
# §4.5, l'annulateur du demontage et le recentrage.
# LES JETONS SONT DES INSTRUCTIONS ENTIERES, PAS DES NOMS. MESURE : deux
# mutants ont survecu a la premiere campagne parce que `dzmTbTouche(` reste
# vrai d'un `var p=null&&dzmTbTouche(...)` et que `fin.current()` vit AUSSI
# dans `saisir` — la sous-chaine etait trouvee ailleurs (faute n°2).
for _tk in ("x.useState(dzmTbOffGet)", "dzmTbGeo(bar.current",
            "dzmTbSaisie(w,doc&&doc.body", "dzmTbOffSet(res)",
            "var p=dzmTbTouche(e&&e.key,e&&e.shiftKey===!0);",
            "dzmTbBorne({", "dzmTbOffSet({dx:0,dy:0})",
            "if(fin.current){fin.current();fin.current=null}",
            "dzmTbRecadre(bar.current,offRef.current)",
            "    recadrer();", "return dzmTbVeille(", "offRef.current=off;",
            "onGrab:saisir", "onGripKey:clavier",
            "onRecentrer:recentrer", "barRef:bar", "off:off", "drag:drag"):
    check("tb_le_dock_porte_" + re.sub(r"\W+", "_", _tk).strip("_"),
          _tk in _DOCK, f"absent du Dock ({len(_DOCK)} o)")
# LE DECALAGE EST RESTAURE PAR UN INITIALISEUR PARESSEUX, comme `open` : la
# forme appelee (`dzmTbOffGet()`) aurait relu localStorage a chaque rendu de
# l'ecran — et l'ecran se redessine a chaque image pendant la lecture.
check("tb_le_decalage_de_depart_est_un_initialiseur_paresseux",
      "x.useState(dzmTbOffGet)" in _DOCK
      and "x.useState(dzmTbOffGet())" not in _DOCK,
      f"dock={_DOCK[:200]!r}")
# LE MAGASIN N'EST ECRIT QU'AU RELACHEMENT ET AU RECENTRAGE, jamais a chaque
# `pointermove` : un `setItem` par image de geste, pour une seule position
# qui compte. La mesure est le COMPTE d'appels dans le Dock — QUATRE, et
# chacun repond a un moment nomme : le relachement, la fleche, le
# recentrage, le recadrage. Un cinquieme voudrait dire qu'un chemin ecrit
# sans qu'on l'ait decide.
check("tb_le_decalage_n_est_ecrit_qu_aux_quatre_moments_qui_comptent",
      _DOCK.count("dzmTbOffSet(") == 4
      and _DOCK.count("if(fini){setDrag(!1);dzmTbOffSet(res)") == 1
      and _DOCK.count("if(v)setOff(dzmTbOffSet(v))") == 1,
      f'{_DOCK.count("dzmTbOffSet(")} appel(s) a dzmTbOffSet dans le Dock '
      f'— attendu 4 : relachement, fleche, recentrage, recadrage')
# L'ETAT DE DEPART EST LU, PAS DEVINE : `x.useState(dzmTbOpenGet)` passe la
# fonction en initialiseur PARESSEUX — React l'appelle une fois, sans
# argument, donc sur le magasin du navigateur. `x.useState(dzmTbOpenGet())`
# aurait relu localStorage a chaque rendu de l'ecran.
check("tb_l_etat_de_depart_est_un_initialiseur_paresseux",
      "x.useState(dzmTbOpenGet)" in _DOCK
      and "x.useState(dzmTbOpenGet())" not in _DOCK,
      f"dock={_DOCK[:160]!r}")

# ── LA FRAME SUIVANTE (§4.4) ──────────────────────────────────────────────
# LE §4.4 dit « poser l'état final, réactiver les transitions à la frame
# suivante ». Ce chemin ne s'execute qu'au montage du composant a hooks, hors
# de portee du banc — d'ou son extraction en fonction pure. ET ELLE A TROUVE
# UN DEFAUT REEL : la premiere ecriture gardait `w.requestAnimationFrame`
# dans une variable puis l'appelait nue, ce qui leve « Illegal invocation »
# sous Blink et WebKit. Le faux navigateur mesure `this` ; aucune lecture de
# source ne l'aurait vu.
check("tb_la_frame_suivante_appelle_raf_sur_son_objet",
      d.get("tb_frame_appelle_sur_son_objet") == [["raf", True, "function"],
                                                  ["cancel", True, 7]],
      f'{d.get("tb_frame_appelle_sur_son_objet")}')
check("tb_sans_navigateur_ou_avec_une_demi_paire_on_retombe_sur_un_minuteur",
      d.get("tb_frame_sans_navigateur") == "ok"
      and d.get("tb_frame_moteur_incomplet") == [0, "ok"],
      f'{d.get("tb_frame_sans_navigateur")} '
      f'{d.get("tb_frame_moteur_incomplet")}')

# ── L'ONGLET (§2.1) ───────────────────────────────────────────────────────
check("tb_l_onglet_est_un_bouton_qui_porte_aria_expanded_et_aria_controls",
      d.get("tb_o_balise") == ["button", "button"]
      and d.get("tb_o_classe") == "dzm-tbtab"
      and d.get("tb_o_aria") == ["true", "false", "dzm-toolbar"]
      and d.get("tb_id") == "dzm-toolbar",
      f'{d.get("tb_o_balise")} {d.get("tb_o_classe")} {d.get("tb_o_aria")}')
# LES CINQ PASTILLES SONT L'APERCU DU CONTENU (§2.1) : cinq, dans l'ordre des
# groupes, chacune portant la classe de teinte de son groupe.
check("tb_l_onglet_montre_les_cinq_pastilles_puis_OUTILS_puis_le_chevron",
      d.get("tb_o_enfants") == ["dzm-tbdots", "dzm-tblbl", "dzm-tbchev"]
      and d.get("tb_o_pastilles") == ["dzm-tbdot dzm-g-" + _g
                                      for _g in ("pistes", "biblio", "mot",
                                                 "ajouts", "projets")]
      and d.get("tb_o_libelle") == "OUTILS"
      and d.get("tb_o_chevrons") == ["▾", "▴"],
      f'{d.get("tb_o_enfants")} {d.get("tb_o_pastilles")} '
      f'{d.get("tb_o_libelle")!r} {d.get("tb_o_chevrons")}')
_OT = d.get("tb_o_titres")
check("tb_l_onglet_bascule_et_dit_ce_qu_il_fera",
      d.get("tb_o_clic") == 1 and d.get("tb_o_clic_sans_action") == "ok"
      and isinstance(_OT, list) and len(_OT) == 2 and _OT[0] != _OT[1]
      and len(_OT[0]) > 10 and len(_OT[1]) > 10,
      f'clic={d.get("tb_o_clic")} titres={_OT}')
check("tb_l_onglet_n_ecrit_aucune_couleur_ni_nom_de_variable_css",
      d.get("tb_o_sans_couleur") is True, str(d.get("tb_o_sans_couleur")))

# ── LA BARRE (§2.2) ───────────────────────────────────────────────────────
check("tb_la_barre_porte_l_id_que_l_onglet_commande",
      d.get("tb_r_balise") == ["div", "dzm-toolbar", "dzm-tbar"]
      and d.get("tb_r_zones") == ["dzm-tbgrip", "dzm-tbzone", "dzm-tbwin"],
      f'{d.get("tb_r_balise")} {d.get("tb_r_zones")}')
# OUVERTE, `data-off` EST ABSENT (React ne pose pas un attribut `undefined`) ;
# repliee, il vaut la chaine vide. Meme mecanique pour `data-noanim`, qui dit
# « pose l'etat final sans transition » au premier rendu (§4.4).
check("tb_l_etat_replie_et_l_etat_sans_animation_passent_par_deux_attributs",
      d.get("tb_r_off") == [None, ""] and d.get("tb_r_noanim") == [None, ""],
      f'off={d.get("tb_r_off")} noanim={d.get("tb_r_noanim")}')
# LA POIGNEE porte le glyphe `poignee` du §3 a 14 px (§2.2a), ses six points
# — et depuis l'etape 5 c'est un BOUTON. `aria-hidden` a quitte le bouton
# (un nœud focusable cache des technologies d'assistance est une faute) et
# est reste sur le GLYPHE ; l'`aria-label` porte le sens.
check("tb_la_poignee_est_un_bouton_qui_porte_le_glyphe_du_3_a_14_px",
      d.get("tb_r_grip") == ["button", "button", 14, "0 0 24 24", 6,
                             "ABSENT", True],
      f'{d.get("tb_r_grip")}')
# SON TITRE DIT LES TROIS GESTES qu'elle accepte et la regle que
# l'utilisateur peut constater — plus « pas encore active ». Les deux pas du
# §4.5 y sont EN CLAIR : une infobulle qui tairait le clavier le rendrait
# introuvable.
_GT = d.get("tb_r_grip_titre")
check("tb_le_titre_de_la_poignee_nomme_le_glisser_et_les_deux_pas",
      isinstance(_GT, str) and len(_GT) > 120
      and "glisser" in _GT and "flèches" in _GT and "Maj" in _GT
      and "8 px" in _GT and "1 px" in _GT
      and "étape 5" not in _GT
      and d.get("tb_r_grip_aria") == "Déplacer la barre d'outils",
      f'{_GT!r} aria={d.get("tb_r_grip_aria")!r}')
# LE FILET DE SEPARATION S'ARRETE AU DERNIER GROUPE (§2.2b) : `data-last` est
# pose par le JS, pas devine par `:last-child`.
check("tb_les_cinq_colonnes_portent_leur_teinte_et_le_dernier_filet_tombe",
      d.get("tb_r_groupes") == [["dzm-tbgrp dzm-g-pistes", None],
                                ["dzm-tbgrp dzm-g-biblio", None],
                                ["dzm-tbgrp dzm-g-mot", None],
                                ["dzm-tbgrp dzm-g-ajouts", None],
                                ["dzm-tbgrp dzm-g-projets", ""]],
      f'{d.get("tb_r_groupes")}')
check("tb_l_entete_MOT_porte_son_suffixe_dans_un_element_a_part",
      d.get("tb_r_entetes") == [[["dzm-tbht", "PISTES"]],
                                [["dzm-tbht", "BIBLIOTHÈQUE"]],
                                [["dzm-tbht", "MOT"],
                                 ["dzm-tbsuf", " — sélection"]],
                                [["dzm-tbht", "AJOUTS"]],
                                [["dzm-tbht", "PROJETS"]]],
      f'{d.get("tb_r_entetes")}')
# LES NEUF BOUTONS, DANS L'ORDRE, AVEC LEUR ETAT : les deux colonnes a bouton
# unique sont en `dzm-solo`, les quatre bascules portent `aria-pressed`, les
# deux muets sont `disabled`. C'est la photographie complete de la barre.
check("tb_les_neuf_boutons_sont_peints_avec_leur_etat",
      d.get("tb_r_boutons") == [
          ["dzm-tbb dzm-g-pistes", "vidéo", False, "ABSENT"],
          ["dzm-tbb dzm-g-pistes", "audio", False, "ABSENT"],
          ["dzm-tbb dzm-g-biblio dzm-solo", "lier", False, "ABSENT"],
          ["dzm-tbb dzm-g-mot", "couleur", False, "false"],
          ["dzm-tbb dzm-g-mot dzm-on", "rebond", False, "true"],
          ["dzm-tbb dzm-g-mot", "glow", False, "false"],
          ["dzm-tbb dzm-g-ajouts", "emoji", False, "ABSENT"],
          ["dzm-tbb dzm-g-ajouts dzm-on", "texte", False, "true"],
          ["dzm-tbb dzm-g-projets dzm-solo", "projets", False, "ABSENT"]],
      f'{d.get("tb_r_boutons")}')
# LES DEUX CONTROLES DE FENETRE (§2.2c), VIVANTS TOUS LES DEUX depuis
# l'etape 5. NI L'UN NI L'AUTRE N'EST `disabled` : le §4.2 dit de `⌖` qu'« il
# ne doit jamais être masqué », et un filet de securite qui se desarme des que
# l'etat le croit inutile n'en est plus un — il reste cliquable meme a
# decalage nul, ou il ne fait rien de visible.
check("tb_les_deux_controles_de_fenetre_sont_vivants",
      d.get("tb_r_win") == [
          ["dzm-tbwb dzm-tbrc", "⌖", "ABSENT",
           "Recentrer la barre d'outils"],
          ["dzm-tbwb dzm-tbcl", "×", "ABSENT", "Replier la barre d'outils"]]
      and d.get("tb_r_replier") == 1
      and d.get("tb_r_replier_sans_action") == "ok"
      and d.get("tb_r_recentrer") == 1
      and d.get("tb_r_recentrer_sans_action") == "ok",
      f'{d.get("tb_r_win")} replier={d.get("tb_r_replier")} '
      f'recentrer={d.get("tb_r_recentrer")}')
# DEUX TITRES, ET ILS DIFFERENT : « ramène » quand la barre est deportee,
# « déjà à sa place » quand elle ne l'est pas. Un seul titre aurait promis un
# effet la ou il n'y en a aucun.
_RT = d.get("tb_r_recentrer_titres")
check("tb_le_recentrage_dit_laquelle_des_deux_situations_est_en_cours",
      isinstance(_RT, list) and len(_RT) == 2 and _RT[0] != _RT[1]
      and len(_RT[0]) > 40 and len(_RT[1]) > 40
      and "origine" in _RT[0] and "origine" in _RT[1]
      and "déjà" not in _RT[0] and "déjà" in _RT[1],
      f'{_RT}')
# SANS CABLAGE la barre existe quand meme — cinq colonnes — et AUCUN de ses
# neuf boutons n'est vivant. Le repli d'une entree manquante n'est pas `{}` :
# `{}` aurait rendu neuf boutons d'apparence vivante sans action derriere.
check("tb_une_barre_sans_cablage_n_allume_aucun_bouton",
      d.get("tb_r_sans_items") == [5, 0], f'{d.get("tb_r_sans_items")}')
check("tb_la_barre_n_ecrit_aucune_couleur_ni_nom_de_variable_css",
      d.get("tb_r_sans_couleur") is True, str(d.get("tb_r_sans_couleur")))

# ── L'ANCRAGE, REMESURE PAR LE BANC ───────────────────────────────────────
# LE POINT OU CE TRAVAIL POUVAIT ECHOUER EN SILENCE. Le §2.1 le dit lui-meme :
# « Vérifier qu'aucun conteneur parent ne le rogne ». La mesure est rejouee
# ici pour qu'elle ne se perime pas : le jour ou une feuille pose un overflow
# sur `.svm-tl`, l'onglet serait coupe a l'ecran et RIEN d'autre ne le dirait.


def _sansc(t):
    """Feuille SANS ses commentaires — indispensable : son-vfx-montage.css
    parle de `.svm-scroll (déjà overflow:auto)` DANS un commentaire au-dessus
    de `.svm-tl`, et un lecteur naif l'attribuerait a la regle."""
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)


def _REGLES(txt):
    """Toutes les regles d'une feuille, commentaires retires : (selecteur,
    corps). Facteur commun de plusieurs lignes ci-dessous."""
    return list(re.finditer(r"([^{}]*)\{([^{}]*)\}", _sansc(txt)))


def _corps_de(txt, fin):
    """Corps de toutes les regles dont un selecteur FINIT par `fin`."""
    out = []
    for _m in re.finditer(r"([^{}]*)\{([^{}]*)\}", _sansc(txt)):
        if any(x.strip().endswith(fin) for x in _m.group(1).split(",")):
            out.append(_m.group(2))
    return out


_TL = (_corps_de(_HDCSS, ".svm-tl") + _corps_de(_MC, ".svm-tl")
       + _corps_de(_lire(ROOT / "frontend" / "dist" / "shared" / "subs.css"),
                   ".svm-tl"))
_TRANS = _corps_de(_MC, ".svm-trans") + _corps_de(_HDCSS, ".svm-trans")
_RACINE = _corps_de(_HDCSS, ".dzsvm")
check("tb_aucun_parent_de_l_onglet_ne_le_rogne",
      len(_TL) == 3 and not any("overflow" in b for b in _TL)
      and len(_RACINE) >= 1
      and any("overflow:hidden" in b and "position:absolute" in b
              for b in _RACINE),
      f"regles .svm-tl={len(_TL)} avec overflow="
      f"{[b for b in _TL if 'overflow' in b]} ; racine={len(_RACINE)}")
# LE BLOC CONTENEUR : sans `position:relative` sur le bandeau, `top:-21px`
# se calerait sur la racine de l'ecran et l'onglet partirait en haut de page.
# ETAPE 6 (§5.2) — LE BANDEAU PASSE DE 34 A 46 px, GAGNE SES DEUX FILETS ET
# VERROUILLE `flex-wrap`. Trois regles le nomment desormais : deux dans
# /shared/montage.css (l'ancrage de l'onglet, puis la geometrie du §5.2) et
# celle de la feuille amont, INCHANGEE — elle n'est pas a nous. La ligne
# exige les DEUX hauteurs : si la notre disparaissait, la 34 px reprendrait la
# main et aucun banc ne l'aurait dit.
check("tb_le_bandeau_est_le_bloc_conteneur_de_l_onglet_et_fait_46px",
      len(_TRANS) == 3
      and any("position:relative" in b and "overflow:visible" in b
              for b in _TRANS)
      and any("height:46px" in b and "flex-wrap:nowrap" in b
              and "border-top:1px solid" in b
              and "border-bottom:1px solid" in b for b in _TRANS)
      and any("height:34px" in b for b in _TRANS),
      f"{_TRANS}")
# LA CASCADE : la regle qui passe le bandeau en `relative` doit etre chargee
# APRES celle qui le laisse `static`. Mesure sur le fichier que le navigateur
# lit, pas sur une intention.
_HTML = _lire(ROOT / "frontend" / "dist" / "index.html")
_i_sv = _HTML.find("/shared/son-vfx-montage.css")
_i_mc = _HTML.find("/shared/montage.css")
check("tb_montage_css_est_chargee_apres_son_vfx_montage_css",
      _i_sv >= 0 and _i_mc > _i_sv, f"son-vfx={_i_sv} montage={_i_mc}")
# LE z-index, REDERIVE. 8 n'est pas un gout : c'est le seul entier libre
# entre le plafond du CONTENU de la timeline et le premier POPOVER. Si l'un
# des deux bouge, cette ligne rougit et le nombre doit etre rediscute.
_ZT = []
for _f in (_MC, _HDCSS,
           _lire(ROOT / "frontend" / "dist" / "shared" / "subs.css")):
    for _m in re.finditer(r"([^{}]*)\{([^{}]*z-index:\s*(-?\d+)[^{}]*)\}",
                          _sansc(_f)):
        _ZT.append((_m.group(1).strip(), int(_m.group(3))))
_ZB = [v for sel, v in _ZT if "dzm-tbar" in sel or "dzm-tbtab" in sel]
_ZA = [v for sel, v in _ZT if "dzm-tbar" not in sel and "dzm-tbtab" not in sel]
check("tb_le_z_index_8_est_le_seul_entier_libre_entre_le_contenu_et_les_popovers",
      len(_ZB) == 2 and set(_ZB) == {8}
      and len(_ZA) >= 20 and 8 not in _ZA
      and max(v for v in _ZA if v < 8) == 7
      and min(v for v in _ZA if v > 8) == 9,
      f"barre={_ZB} ; sous={sorted(v for v in _ZA if v < 8)[-3:]} ; "
      f"dessus={sorted(v for v in _ZA if v > 8)[:3]}")

# ── LA FEUILLE HABILLE L'ONGLET ET LA BARRE ───────────────────────────────
# LE BLOC DE LA BARRE dans la feuille, borne par son en-tete : les
# negations ci-dessous ne doivent porter QUE sur lui. `cursor:grab` vit
# deja plus haut, sur `.dzm-hb`, et une negation a l'echelle du fichier
# rougirait sur du code etranger a ce lot.
# LE DECOUPAGE PART DU  OUVRANT, pas du texte de l'en-tete : couper au
# milieu d'un commentaire laisse son contenu sans marqueur d'ouverture, et
# le retrait des commentaires ne le voit plus. Mesure : la phrase « pas de
# cursor:grab » survivait a _sansc et faisait rougir sa propre negation.
_i_mc4 = _MC.rfind("/*", 0, _MC.find("L'ONGLET ET LA BARRE (handoff"))
# LE BLOC DE L'ETAPE 5 COMMENCE OU CELUI DE L'ETAPE 4 S'ARRETE. Sans cette
# borne, `_MC_TB4` avalait le bloc du deport et sa negation « pas de
# cursor:grab » rougissait sur du code qui a le droit d'en poser un.
_i_mc5 = _MC.rfind("/*", 0, _MC.find("LE DÉPORT (handoff"))
_MC_TB4 = (_sansc(_MC[_i_mc4:_i_mc5]) if 0 <= _i_mc4 < _i_mc5
           else "BLOC-INTROUVABLE")
_MC_TB5 = _sansc(_MC[_i_mc5:]) if _i_mc5 >= 0 else "BLOC-INTROUVABLE"
_R_TAB = _regle(_MC, ".dzsvm .dzm-tbtab{")
_R_TABO = _regle(_MC, '.dzsvm .dzm-tbtab[aria-expanded="true"]{')
_R_DOT = _regle(_MC, ".dzsvm .dzm-tbdot{")
_R_DOTS = _regle(_MC, ".dzsvm .dzm-tbdots{")
_R_BAR = _regle(_MC, ".dzsvm .dzm-tbar{")
_R_BOFF = _regle(_MC, ".dzsvm .dzm-tbar[data-off]{")
_R_BNA = _regle(_MC, ".dzsvm .dzm-tbar[data-noanim]{")
_R_GRIP = _regle(_MC, ".dzsvm .dzm-tbgrip{")
_R_GRIPH = _regle(_MC, ".dzsvm .dzm-tbgrip:hover{")
_R_GRIPD = _regle(_MC, ".dzsvm .dzm-tbar[data-drag] .dzm-tbgrip{")
_R_BDRAG = _regle(_MC, ".dzsvm .dzm-tbar[data-drag]{")
_R_CORPS = _regle(_MC, "body.dzm-tbdrag, body.dzm-tbdrag *{")
_R_ZONE = _regle(_MC, ".dzsvm .dzm-tbzone{")
_R_GRP = _regle(_MC, ".dzsvm .dzm-tbgrp{")
_R_GRPL = _regle(_MC, ".dzsvm .dzm-tbgrp[data-last]{")
_R_HEAD = _regle(_MC, ".dzsvm .dzm-tbhead{")
_R_SUF = _regle(_MC, ".dzsvm .dzm-tbsuf{")
_R_WIN = _regle(_MC, ".dzsvm .dzm-tbwin{")
_R_WB = _regle(_MC, ".dzsvm .dzm-tbwb{")
_R_WBD = _regle(_MC, ".dzsvm .dzm-tbwb[disabled]{")
_R_WBH = _regle(_MC, ".dzsvm .dzm-tbwb:hover:not([disabled]){")
check("tb_la_geometrie_de_l_onglet_est_celle_du_2_1",
      _R_TAB is not None and "top:-21px" in _R_TAB and "left:14px" in _R_TAB
      and "height:21px" in _R_TAB and "padding:0 11px" in _R_TAB
      and "border-bottom:0" in _R_TAB and "border-radius:0" in _R_TAB
      and "gap:8px" in _R_TAB and "font-size:10px" in _R_TAB
      and "letter-spacing:.1em" in _R_TAB
      and _R_DOTS is not None and "gap:2px" in _R_DOTS
      and _R_DOT is not None and "width:5px" in _R_DOT
      and "height:5px" in _R_DOT,
      f"tab={_R_TAB!r} dot={_R_DOT!r}")
# LES DEUX ETATS DE L'ONGLET viennent du tableau du §2.1, et la porte est
# `aria-expanded` : l'apparence ne peut pas dire « ouvert » pendant que le
# lecteur d'ecran annonce « replie ».
check("tb_l_onglet_ouvert_se_lit_d_une_piece_avec_la_barre",
      _R_TAB is not None and "background:var(--srf-raised," in _R_TAB
      and "color:var(--txt-mid," in _R_TAB
      and _R_TABO is not None and "background:var(--srf-panel," in _R_TABO
      and "color:var(--txt-hi," in _R_TABO,
      f"tab={_R_TAB!r} ouvert={_R_TABO!r}")
check("tb_la_geometrie_de_la_barre_est_celle_du_2_2",
      _R_BAR is not None and "position:absolute" in _R_BAR
      and "left:14px" in _R_BAR and "top:calc(100% + 8px)" in _R_BAR
      and "display:flex" in _R_BAR and "align-items:stretch" in _R_BAR
      and "border-radius:0" in _R_BAR
      and "background:var(--bar-srf," in _R_BAR
      and "border:1px solid var(--bar-brd," in _R_BAR
      and "box-shadow:var(--bar-shadow," in _R_BAR,
      f"bar={_R_BAR!r}")
# L'OMBRE PORTEE EST LE SEUL SIGNAL DE FLOTTEMENT (§1.3) : ni flou
# d'arriere-plan, ni fond translucide — la timeline defile dessous et les
# icones deviendraient illisibles pendant la lecture. Conjoint positif :
# l'ombre EST la.
check("tb_la_barre_flotte_par_son_ombre_et_par_rien_d_autre",
      _R_BAR is not None and "box-shadow:var(--bar-shadow," in _R_BAR
      and "backdrop-filter" not in _MC
      and "background:var(--bar-srf," in _R_BAR,
      f"bar={_R_BAR!r}")
# LE REPLI (§4.1) : opacite et 6 px, JAMAIS la hauteur. La `visibility` est
# retardee a la fin de la transition pour que le repli s'anime, puis elle
# retire les neuf boutons du parcours de tabulation.
check("tb_le_repli_anime_l_opacite_et_six_pixels_jamais_la_hauteur",
      _R_BOFF is not None and "opacity:0" in _R_BOFF
      and "transform:translateY(6px)" in _R_BOFF
      and "visibility:hidden" in _R_BOFF
      and "pointer-events:none" in _R_BOFF
      and "height" not in _R_BOFF
      and "var(--dur-bar-open," in _R_BOFF
      and "var(--ease-panel," in _R_BOFF
      and "visibility 0s linear var(--dur-bar-open," in _R_BOFF,
      f"off={_R_BOFF!r}")
check("tb_la_restauration_pose_l_etat_final_sans_transition",
      _R_BNA is not None and "transition:none" in _R_BNA, f"{_R_BNA!r}")
# LA POIGNEE SAISIT, ET LA FEUILLE LE DIT AVEC ELLE : `cursor:grab`, un etat
# de survol, et la remise a zero du `<button>` qu'elle est devenue. Les trois
# vivent dans le bloc du DEPORT, pas dans celui de l'etape 4 : la negation
# ci-dessous porte sur le bloc de l'etape 4 SEUL, avec son conjoint positif
# de taille — sans lui elle serait vraie d'un bloc introuvable.
check("tb_la_poignee_saisit_et_la_feuille_le_dit",
      _R_GRIP is not None and "width:26px" in _R_GRIP
      and "cursor:grab" in _R_GRIP
      and "touch-action:none" in _R_GRIP
      and "padding:0" in _R_GRIP and "border:0" in _R_GRIP
      and "background:var(--srf-raised," in _R_GRIP
      and "border-right:1px solid var(--brd-hard," in _R_GRIP
      and _R_GRIPH is not None
      and "background:var(--srf-hover," in _R_GRIPH
      and "color:var(--txt-mid," in _R_GRIPH
      and len(_MC_TB4) > 2000 and "cursor:grab" not in _MC_TB4
      and len(_MC_TB5) > 800,
      f"grip={_R_GRIP!r} hover={_R_GRIPH!r} tb4={len(_MC_TB4)} "
      f"tb5={len(_MC_TB5)}")
check("tb_les_colonnes_de_groupe_ont_leur_gouttiere_et_leur_filet",
      _R_ZONE is not None and "padding:9px 10px 8px" in _R_ZONE
      and _R_GRP is not None and "padding:0 11px" in _R_GRP
      and "border-right:1px solid var(--brd-soft," in _R_GRP
      and _R_GRPL is not None and "border-right:0" in _R_GRPL
      and _R_HEAD is not None and "font-size:8.5px" in _R_HEAD
      and "letter-spacing:.14em" in _R_HEAD
      and "padding:0 4px 7px" in _R_HEAD
      and "color:var(--grp," in _R_HEAD
      and _R_SUF is not None and "opacity:.5" in _R_SUF
      and "letter-spacing:.06em" in _R_SUF,
      f"zone={_R_ZONE!r} grp={_R_GRP!r} head={_R_HEAD!r} suf={_R_SUF!r}")
check("tb_les_controles_de_fenetre_sont_habilles_et_la_regle_eteinte_reste",
      _R_WIN is not None and "width:26px" in _R_WIN
      and "border-left:1px solid var(--brd-hard," in _R_WIN
      and _R_WB is not None and "flex:1" in _R_WB
      and _R_WBH is not None and "color:var(--accent," in _R_WBH
      and "background:#1e242b" in _R_WBH
      and _R_WBD is not None and "opacity:.38" in _R_WBD
      and "cursor:not-allowed" in _R_WBD,
      f"win={_R_WIN!r} wb={_R_WB!r} hover={_R_WBH!r} dis={_R_WBD!r}")

# ── CE QUE CE LOT FAIT, ET CE QU'IL NE FAIT PAS ───────────────────────────
# L'ANCIENNE LIGNE DISAIT « aucune section ne monte la barre » EN CHERCHANT
# `dzm-tbb`, `ToolBtn` et `DzTracks.TbIcon` DANS LES SECTIONS. Elle est
# restee VERTE quand l'etape 4 a monte la barre : la section monte un Dock
# qui monte la barre qui monte les boutons, et aucun des trois jetons
# cherches n'y apparait. C'etait une assertion verte sur ce qu'elle croyait
# tester — faute n°2. Elle est remplacee par une mesure qui DECIDE : la
# section qui monte le dock existe, une seule fois, et elle passe les six
# proprietes du cablage.
_SECTIONS = "".join(r for _t, _a, r in P.PATCHES)
# LES SIX PROPRIETES SONT MESUREES DANS LA SECTION, PAS DANS LE BUNDLE, et
# c'est une correction : la premiere version cherchait `onPick:openPicker`
# DANS LE BUNDLE. MESURE par mutation — la propriete retiree de R_M19, le
# banc restait a 632/0 : M8 ecrit deja `onPick:openPicker` pour le bouton
# « Bibliothèque… », et la sous-chaine etait donc trouvee ailleurs. Faute
# n°2, forme « sous-chaine ». Les deux faces sont gardees desormais : la
# propriete est DANS la section, et le bundle en porte le compte attendu —
# UN SEUL `onPick:openPicker` DEPUIS L'ETAPE 6 : le bouton du bandeau est
# parti, la barre est la seule porte. Un seul de chacune des cinq autres.
# ETAPE 7 : QUATRE PROPRIETES DE PLUS, mesurees de la meme facon — dans la
# section ET dans le bundle. Elles ferment le §6 : les trois ingredients de
# l'action emoji (deja passes a M10, a l'identique) et la demande d'ouverture
# de la liste des projets.
_P_M19 = ("tracks:svmTracksOf(proj)", "onTracks:svmTracksSet",
          "onPick:openPicker", "wordAnim:(proj.subsStyle||{}).wordAnim",
          "onWordAnim:function(v){subsStyleSet(", "textOn:dzTextOn",
          "onText:function(){setDzTextOn(!dzTextOn)}",
          "emojiSegs:subsSegsOf(clips)", "note:fireNote",
          "onEmojiAdd:dzEmoAdd",
          "onProjets:function(){setDzProjReq(function(n){return n+1})}")
check("tb_une_seule_section_monte_le_dock_et_lui_passe_le_cablage",
      _SECTIONS.count("DzTracks.ToolDock") == 1
      and s.count(nl("r.jsx(DzTracks.ToolDock,{")) == 1
      and all(_p in P.R_M19 for _p in _P_M19)
      and all(nl(_p) in s for _p in _P_M19)
      and s.count(nl("onPick:openPicker")) == 1
      and s.count(nl("onTracks:svmTracksSet")) == 1
      and len(_SECTIONS) > 10000,
      f'{_SECTIONS.count("DzTracks.ToolDock")} section(s) ; manquantes dans '
      f'R_M19 : {[p for p in _P_M19 if p not in P.R_M19]} ; '
      f'onPick={s.count(nl("onPick:openPicker"))}')
# CONTROLE A DEUX FACES, comme M10/M12/M13/M14/M16lib : R_M19 appelle sept
# identifiants du bundle et UN du contrat de la couche. Verifier la seule
# declaration laisserait passer un appel renomme ; verifier le seul appel ne
# verrait pas la declaration disparaitre. MESURE qui fonde cette forme :
# renommer `addAsset` avait laisse un banc a 255/0 avec sept appelants morts.
# `ToolDock` est le cas le plus expose : le patcher ecrit `DzTracks.ToolDock`
# dans le bundle, et si la couche renommait son export, la section
# appellerait `undefined` — le bundle passerait `node --check`, l'ecran
# leverait au premier rendu, et le texte cherche serait toujours la.
for _nm, _decl in (("svmTracksOf", "function svmTracksOf(proj){"),
                   ("svmTracksSet", "function svmTracksSet(ts){"),
                   ("openPicker", "function openPicker(trId){"),
                   ("subsStyleSet", "function subsStyleSet(patch){"),
                   ("dzTextOn", "var stDzTx=x.useState(!1),dzTextOn="),
                   ("setDzTextOn", "setDzTextOn=stDzTx[1];"),
                   ("proj", "proj=stP[0],setProj=stP[1];"),
                   # etape 7 — les quatre du cablage du §6
                   ("subsSegsOf", "function subsSegsOf(cs){"),
                   ("clips", "clips=st1[0],setClips=st1[1]"),
                   ("fireNote", "fireNote=nt[1]"),
                   ("dzEmoAdd", "function dzEmoAdd(cs){pushHistory();"),
                   ("setDzProjReq", "setDzProjReq=stDzPj[1];")):
    _ap = re.search(r"\b%s\b" % re.escape(_nm), P.R_M19) is not None
    check("M19_appelle_" + _nm + "_qui_est_declare",
          _ap and s.count(nl(_decl)) >= 1,
          f"appele={_ap} declare={s.count(nl(_decl))} ({_decl})")
check("M19_ToolDock_est_exporte_par_le_contrat_de_la_couche",
      "DzTracks.ToolDock" in P.R_M19
      and "ToolDock:DzmToolDock" in src
      and s.count(nl("ToolDock:DzmToolDock")) == 1
      and "function DzmToolDock(" in src,
      f'contrat={"ToolDock:DzmToolDock" in src} '
      f'bundle={s.count(nl("ToolDock:DzmToolDock"))}')
# Les deux autres composants de l'etape 4 sont exportes eux aussi : ils ne
# sont appeles que par le Dock aujourd'hui, mais c'est par eux que le banc
# les joue sous node — sans l'export, cinquante lignes plus haut rougiraient
# et aucune ne dirait pourquoi.
check("tb_l_onglet_la_barre_et_le_cablage_sont_dans_le_contrat",
      all(_x in src for _x in ("ToolTab:DzmToolTab", "ToolBar:DzmToolBar",
                               "tbCablage:dzmTbCablage",
                               "tbOpenGet:dzmTbOpenGet",
                               "tbOpenSet:dzmTbOpenSet",
                               "TB_PLAN:DZM_TB_PLAN",
                               "TB_CLE_OPEN:DZM_TB_CLE_OPEN"))
      and all(s.count(nl(_x)) == 1 for _x in ("ToolTab:DzmToolTab",
                                              "ToolBar:DzmToolBar")),
      "le contrat a perdu une des pieces de l'etape 4")
# L'ONGLET ET LA BARRE SONT DEUX ENFANTS DU BANDEAU : c'est ce qui rend
# `top:-21px` relatif AU BANDEAU (§2.1), et donc tout le §2.1.
# LA MESURE EST STRUCTURELLE, pas positionnelle : l'ancre EST l'ouverture du
# bandeau, elle est unique dans le bundle, le remplacement la REPREND en
# tete, et le dock est pose dans ce qui suit — donc dans les `children` du
# bandeau. Une version anterieure comparait des INDEX (« le dock avant le
# timecode ») : elle epinglait un fait vrai mais sans consequence — les deux
# noeuds sont absolus, l'ordre entre freres ne change rien a l'ecran — et
# elle restait verte sur ce qui compte.
check("tb_le_dock_est_monte_dans_le_bandeau_de_transport",
      P.A_M19 == 'r.jsxs("div",{className:"svm-trans",children:['
      and s.count(nl(P.A_M19)) == 1
      and P.R_M19.startswith(P.A_M19)
      and "r.jsx(DzTracks.ToolDock,{" in P.R_M19[len(P.A_M19):],
      f"ancre={P.A_M19!r} reprise={P.R_M19.startswith(P.A_M19)} "
      f"occurrences={s.count(nl(P.A_M19))}")
# ETAPES 6 A 8, TOUJOURS DEHORS — et la ligne le mesure sur la COUCHE, pas
# sur les sections : c'est la couche qui porterait `role="toolbar"`, le
# `tabindex` roving et `Echap`. Conjoint positif d'abord, sinon la ligne
# serait vraie d'un fichier vide.
# L'ETAPE 5 EST DEDANS DESORMAIS, et les deux conjoints positifs le disent :
# `pointermove` et `pointerdown` sont attendus PRESENTS. La ligne d'avant les
# exigeait absents ; elle a fait exactement son travail — c'est elle qui a
# impose de la reecrire au lieu de laisser le reste dehors sans surveillance.
_i_tb4 = src.find("DU \u00a79 : LA BARRE, SON ONGLET, SON D\u00c9PORT, SON")
_j_tb4 = src.find("/* \u2500\u2500 export contrat", _i_tb4) if _i_tb4 >= 0 else -1
_SRC_TB = src[_i_tb4:_j_tb4] if 0 <= _i_tb4 < _j_tb4 else "BLOC-INTROUVABLE"
# L'ETAPE 7 EST DEDANS DESORMAIS, et les conjoints positifs le disent : le
# Dock appelle `dzmTbHote` et `dzmEmojiGo`. La ligne d'avant exigeait
# `pointermove` present (etape 5) ; celle-ci ajoute les deux jetons de
# l'etape 7. ETAPE 6 LIVREE : le bloc porte maintenant le §5 (la table des
# retires et le plan de degradation), et c'est un CONJOINT POSITIF de plus.
# L'ETAPE 8 EST DEDANS DESORMAIS, et les conjoints positifs le disent : le
# `role`, l'orientation, le libelle de la barre, le `tabindex` roving et le
# gestionnaire de touches de la barre. La ligne d'avant exigeait ces jetons
# ABSENTS ; elle a fait exactement son travail en rougissant, et elle est
# REECRITE, pas supprimee.
# `role:"toolbar"` AVEC LA SYNTAXE DE PROPRIETE : le jeton `role="toolbar"`
# vit AUSSI dans deux commentaires de la couche (ceux qui annoncaient
# l'etape), et le chercher nu aurait rendu cette ligne verte sur un
# commentaire (faute n°2, forme « jeton trouve dans un commentaire »).
check("tb_l_etape_8_est_livree",
      len(_SRC_TB) > 6000 and "function DzmToolBar(" in _SRC_TB
      and "function DzmToolDock(" in _SRC_TB
      and "pointermove" in _SRC_TB and "onPointerDown" in _SRC_TB
      and "function dzmTbHote(" in _SRC_TB
      and "dzmEmojiGo({segments:o.emojiSegs" in _SRC_TB
      and "function dzmBdPlan(" in _SRC_TB
      and "DZM_BD_RETIRES=[" in _SRC_TB
      and 'role:"toolbar"' in _code(_SRC_TB)
      and '"aria-orientation":"horizontal"' in _code(_SRC_TB)
      and '"aria-label":DZM_TB_A_BARRE' in _code(_SRC_TB)
      and "onKeyDown:o.onBarKey" in _code(_SRC_TB)
      # LE ROVING EST BIEN CELUI DE LA BARRE, pas un `tabIndex` pose au
      # hasard : l'index plat des neuf, puis les deux index des controles
      # de fenetre, derives de `dzmTbNbAct()`.
      and "tab:ti===rove," in _code(_SRC_TB)
      and "tabIndex:rove===nAct?0:-1," in _code(_SRC_TB)
      and "tabIndex:rove===nAct+1?0:-1," in _code(_SRC_TB)
      # ET LE BOUTON D'ACTION SAIT LE PORTER — il vit HORS de ce bloc
      # (juste au-dessus), d'ou la mesure sur la couche entiere.
      and "if(o.tab===!0)p.tabIndex=0;" in _code(src)
      and "else if(o.tab===!1)p.tabIndex=-1;" in _code(src),
      f"bloc={len(_SRC_TB)} o — un morceau de l'etape 8 manque, ou le bloc "
      f"de la barre est introuvable")
# LA DUPLICATION EST SOLDEE (§5.1). Cette ligne remplace le rappel du reste
# assume qui vivait ici, et elle mesure la SOLDE, des deux cotes : les cinq
# jetons que les sections posaient dans le bandeau ont disparu de la chaine —
# SAUF `DzTracks.Projects`, qui reste parce que ce n'est pas un controle mais
# le panneau qu'un controle de la barre ouvre, et il est monte NU.
# UNE ABSENCE SEULE SERAIT VRAIE D'UN PATCHER VIDE : le conjoint est la
# section M19, qui monte le Dock et lui passe le cablage, et le `nu:!0` qui
# prouve que la liste des projets n'a plus de bouton a elle.
_PARTIS = ("DzTracks.TrackAdd", "DzTracks.LibBtn", "DzTracks.WordAnimChip",
           "DzTracks.EmojiBtn", "dzm-txton")
_RESTANTS = [_j for _j in _PARTIS if _j in _SECTIONS]
check("tb_les_neuf_controles_ont_quitte_le_bandeau",
      not _RESTANTS
      and _SECTIONS.count("DzTracks.Projects") == 1
      and "nu:!0" in _SECTIONS
      and _SECTIONS.count("DzTracks.ToolDock") == 1,
      f'restants={_RESTANTS} projets={_SECTIONS.count("DzTracks.Projects")} '
      f'nu={"nu:!0" in _SECTIONS}')
# UNE SEULE SOURCE POUR MOT, ET PLUS QU'UNE SEULE LECTURE. La chip du bandeau
# lisait `proj.subsStyle` a cote de la barre ; elle est partie, il ne reste
# que la barre. Le §5.1 est tenu au mot (« deux sources de vérité pour l'état
# des bascules ») : il n'y a plus qu'une porte, et elle LIT le projet.
# LE CONJOINT EST L'ECRITURE : `onWordAnim` doit exister, sinon « une seule
# lecture » serait vrai d'un ecran ou plus rien ne peint MOT.
check("tb_la_barre_est_la_seule_a_lire_la_source_de_MOT",
      s.count(nl('(proj.subsStyle||{}).wordAnim||"couleur"')) == 1
      and s.count(nl("onWordAnim:function(v){subsStyleSet({wordAnim:v})}")) == 1
      and s.count(nl("onChange:function(v){subsStyleSet({wordAnim:v})}")) == 0,
      f'lectures={s.count(nl(chr(34) + "couleur" + chr(34)))}')

# ══════════════════════════════════════════════════════════════════════════
# [6-ter] LE DEPORT — etape 5 du §9 du handoff (§4.2, et de §4.4 la seule
# cle `offset`). LE §9 PREVIENT : « Tester d'abord le bornage : c'est là que
# se logent les régressions. » Le cœur est donc une fonction PURE, jouee sous
# node ; ces lignes lisent des NOMBRES, pas des intentions.
# ══════════════════════════════════════════════════════════════════════════
print("\n[6-ter] la barre d'outils — le deport : bornage, aimantation, cle")

# ── LES QUATRE DISTANCES, LUES DANS LE HANDOFF ────────────────────────────
# Meme protocole que les dix traces du §3 et le tableau du §2.4 : ni la
# couche ni ce banc ne retapent un chiffre, les deux le lisent ici. Le jour
# ou le handoff dirait 10 px de marge, CETTE ligne rougirait avec la
# suivante, et le nombre serait rediscute au lieu de se perimer en silence.
_S42 = _S45 = ""
try:
    _S42 = _HO[_HO.index("### 4.2 Déport"):_HO.index("### 4.3 Bascules")]
    _S45 = _HO[_HO.index("### 4.5 Clavier"):_HO.index("## 5. Redistribution")]
except BaseException as _e:
    print(f"  ----  §4.2 / §4.5 du handoff illisibles : {temoin(_e)}")
# LES ESPACES SONT DES `\s+` : le §4.2 revient a la ligne AU MILIEU de
# « à moins\n de 12 px », et une regex a espace simple ne le voyait pas —
# `_DIST` retombait a vide et QUATORZE lignes rougissaient d'un coup. C'est
# la faute n°6 sous sa variante « rougir trop large », attrapee ici.
_m_mrg = re.search(r"marge\s+de\s+(\d+)\s*px", _S42)
_m_aim = re.search(r"à\s+moins\s+de\s+(\d+)\s*px", _S42)
_m_pas = re.search(r"flèches\s*=\s*déplacement\s+de\s+(\d+)\s*px,\s*"
                   r"`Maj\s*\+\s*flèches`\s*=\s*(\d+)\s*px", _S45)
_DIST = ([int(_m_mrg.group(1)), int(_m_aim.group(1)),
          int(_m_pas.group(1)), int(_m_pas.group(2))]
         if (_m_mrg and _m_aim and _m_pas) else [])
check("tb_d_les_quatre_distances_sont_lisibles_dans_le_handoff",
      len(_DIST) == 4 and all(1 <= v <= 64 for v in _DIST)
      and len(_S42) > 800 and len(_S45) > 500,
      f"distances={_DIST} §4.2={len(_S42)} o §4.5={len(_S45)} o")
check("tb_d_la_couche_porte_les_quatre_distances_du_handoff",
      len(_DIST) == 4 and d.get("tb_d_distances") == _DIST,
      f'couche={d.get("tb_d_distances")} handoff={_DIST}')

# ── LE BORNAGE (§4.2) ─────────────────────────────────────────────────────
# LES QUATRE BORNES, DERIVEES DES MEMES NOMBRES QUE LA SONDE : le plateau est
# un conteneur (100,50) de 1000 x 600 et une barre (114,140) de 400 x 74. La
# marge vient du HANDOFF, pas d'ici — si elle changeait, ces quatre nombres
# suivraient et la ligne resterait juste.
_MG = _DIST[0] if len(_DIST) == 4 else None
_BORNES = ([100 + _MG - 114, 1100 - _MG - 400 - 114,
            50 + _MG - 140, 650 - _MG - 74 - 140] if _MG is not None else [])
check("tb_d_les_quatre_bornes_sont_celles_du_conteneur_moins_la_marge",
      len(_BORNES) == 4 and d.get("tb_d_bornes") == _BORNES,
      f'mesure={d.get("tb_d_bornes")} attendu={_BORNES}')
# ET LA MARGE SE LIT SUR LES BORDS DE LA BARRE, pas sur le decalage : les
# quatre ecarts au conteneur, la barre poussee contre chaque bord.
check("tb_d_la_barre_s_arrete_a_la_marge_des_quatre_bords",
      _MG is not None and d.get("tb_d_marge") == [_MG, _MG, _MG, _MG],
      f'{d.get("tb_d_marge")} attendu 4x{_MG}')
# AU MILIEU, LE DECALAGE VAUT LE DEPLACEMENT — et `borne` dit que le bornage
# a bien eu lieu. Sans ce second conjoint, une fonction qui rendrait toujours
# l'entree telle quelle passerait cette ligne.
check("tb_d_au_milieu_le_decalage_vaut_le_deplacement",
      d.get("tb_d_libre") == [50, 30]
      and d.get("tb_d_libre_est_borne") is True,
      f'{d.get("tb_d_libre")} borne={d.get("tb_d_libre_est_borne")}')
# LE DECALAGE COURANT S'AJOUTE AU DEPLACEMENT, et l'ancrage est DEDUIT de la
# barre : la meme barre, deja deportee de 100, rend 120 pour 20 px de geste.
# ET L'ANCRAGE EST DEDUIT DE LA BARRE (`bar.left - dx`) : la seconde
# mesure part du MEME plateau, decale de 100, et pousse jusqu'a la borne. La
# premiere seule ne suffisait pas — au milieu du conteneur les deux lectures
# donnent le meme nombre, et le mutant qui oublie le `- dx` a survecu a la
# premiere campagne. C'est la campagne qui a ecrit cette ligne.
check("tb_d_le_decalage_courant_s_ajoute_au_deplacement",
      len(_BORNES) == 4 and d.get("tb_d_cumul") == [120, 60]
      and d.get("tb_d_cumul_borne") == [_BORNES[1], _BORNES[3]],
      f'{d.get("tb_d_cumul")} borne={d.get("tb_d_cumul_borne")} '
      f'attendu={[_BORNES[1], _BORNES[3]]}')

# ── LES CAS LIMITES, CEUX QUE LE §4.2 REND MORTELS ────────────────────────
# UNE BARRE PLUS GRANDE QUE LE CONTENEUR : le bord d'ORIGINE, celui de la
# poignee — pas le bord oppose. Un `Math.min(mx, Math.max(mn, v))` naif
# aurait rendu l'autre, et la poignee serait sortie a gauche.
check("tb_d_une_barre_trop_grande_garde_sa_poignee_atteignable",
      len(_BORNES) == 4
      and d.get("tb_d_barre_trop_large") == [_BORNES[0], _BORNES[2],
                                             _BORNES[0]]
      and d.get("tb_d_barre_trop_large_bord") == _MG,
      f'{d.get("tb_d_barre_trop_large")} '
      f'bord={d.get("tb_d_barre_trop_large_bord")}')
# UN CONTENEUR DE TAILLE NULLE, DES RECTANGLES `NaN` OU ABSENTS : le bornage
# est SAUTE et le decalage passe tel quel. C'est la RESTAURATION qui en
# mourrait sinon — un decalage valide, borne contre une mise en page pas
# encore calculee, serait ramene a zero sans un mot. `borne` a faux est le
# temoin DISTINGUABLE de ce chemin : sans lui, « le decalage n'a pas bouge »
# serait vrai aussi d'un bornage qui aurait tourne et n'aurait rien eu a
# corriger.
for _k, _lb in (("tb_d_conteneur_nul", "un conteneur de taille nulle"),
                ("tb_d_conteneur_hauteur_nulle", "une hauteur nulle"),
                ("tb_d_rect_absent", "un conteneur absent"),
                ("tb_d_rect_nan", "un conteneur NaN"),
                ("tb_d_barre_absente", "une barre absente"),
                ("tb_d_barre_sans_champs", "une barre sans dimensions")):
    check("tb_d_" + _k[5:] + "_saute_le_bornage",
          d.get(_k) == [300, 200, False], f'{_lb} : {d.get(_k)}')
# UN DEPLACEMENT ENORME MAIS FINI EST BORNE ; UN DEPLACEMENT NON FINI EST
# IGNORE. Les deux ne se valent pas : le premier vient d'un vrai geste, le
# second d'un evenement casse, et le confondre avec un deplacement aurait
# colle la barre a un bord sans qu'on ait bouge.
check("tb_d_un_deplacement_enorme_est_borne_un_deplacement_absurde_ignore",
      len(_BORNES) == 4
      and d.get("tb_d_enorme") == [_BORNES[1], _BORNES[2]]
      and d.get("tb_d_infini") == [0, 0] and d.get("tb_d_nan") == [0, 0]
      and d.get("tb_d_texte") == [0, 0],
      f'enorme={d.get("tb_d_enorme")} infini={d.get("tb_d_infini")} '
      f'nan={d.get("tb_d_nan")} texte={d.get("tb_d_texte")}')
# AUCUNE SORTIE N'EST `NaN`, QUOI QU'ON ENTRE. Un `NaN` dans une translation
# CSS ne leve pas : il ANNULE la regle, et la barre saute a son ancrage sans
# que rien ne le dise.
check("tb_d_rien_ne_sort_jamais_en_nan",
      d.get("tb_d_jamais_nan") == [True, True, 0, 0, False]
      and d.get("tb_d_sans_argument") == [0, 0, "", "", False],
      f'{d.get("tb_d_jamais_nan")} nu={d.get("tb_d_sans_argument")}')

# ── L'AIMANTATION (§4.2) ──────────────────────────────────────────────────
# LES QUATRE BORDS, ET LES DEUX COTES DU SEUIL. « à MOINS de 12 px » : a 11
# ca colle, a 12 non. Une ligne qui n'aurait mesure que le cote « ca colle »
# aurait laisse passer un seuil de 100 px.
_SL = _DIST[1] if len(_DIST) == 4 else None
if len(_BORNES) == 4 and _SL is not None:
    for _k, _i, _nom, _sens in (("tb_d_aim_gauche", 0, "g", +1),
                                ("tb_d_aim_droite", 1, "d", -1),
                                ("tb_d_aim_haut", 2, "h", +1),
                                ("tb_d_aim_bas", 3, "b", -1)):
        _vert = _i >= 2
        _fixe = 200 if _vert else 0
        _colle = ([_fixe, _BORNES[_i], "", _nom] if _vert
                  else [_BORNES[_i], 0, _nom, ""])
        _libre = ([_fixe, _BORNES[_i] + _sens * _SL, "", ""] if _vert
                  else [_BORNES[_i] + _sens * _SL, 0, "", ""])
        check("tb_d_aimantation_au_bord_" + _nom + "_et_pas_au_dela_du_seuil",
              d.get(_k) == [_colle, _libre],
              f'{_k}={d.get(_k)} attendu {[_colle, _libre]}')
# L'AXE DE LA TETE DE LECTURE, LES DEUX BORDS DE LA BARRE (§4.2 : « un bord
# de la barre », pas « le bord gauche »). `tg` = bord gauche sur l'axe,
# `td` = bord droit.
check("tb_d_les_deux_bords_de_la_barre_s_aimantent_a_l_axe_de_la_tete",
      d.get("tb_d_aim_tete") == [[186, 0, "tg", ""], [199, 0, "", ""]]
      and d.get("tb_d_aim_tete_bord_droit") == [286, 0, "td", ""],
      f'gauche={d.get("tb_d_aim_tete")} '
      f'droit={d.get("tb_d_aim_tete_bord_droit")}')
# LA TETE HORS DU CONTENEUR — elle defile avec `.svm-scroll` et s'eloigne
# avec le zoom. AUCUN AIMANT, ET SURTOUT AUCUN DEPLACEMENT : la barre reste
# ou le doigt l'a lachee. C'est ce que « ecarter le candidat » fait et que
# « re-pincer apres coup » n'aurait pas fait — la barre aurait saute au bord.
check("tb_d_une_tete_hors_du_conteneur_n_aimante_ni_ne_deplace",
      d.get("tb_d_aim_tete_hors") == [[200, 0, "", ""], [200, 0, "", ""]]
      and d.get("tb_d_aim_sans_tete") == [[200, 0, "", ""], [200, 0, "", ""]],
      f'hors={d.get("tb_d_aim_tete_hors")} '
      f'sans={d.get("tb_d_aim_sans_tete")}')
# L'AIMANTATION EST « AU RELACHEMENT » (§4.2), pas pendant le geste : la
# meme position, le meme plateau, deux resultats.
check("tb_d_l_aimantation_n_a_lieu_qu_au_relachement",
      len(_BORNES) == 4
      and d.get("tb_d_aim_seulement_au_relachement")
      == [[_BORNES[0] + 3, 0, "", ""], [_BORNES[0], 0, "g", ""]],
      f'{d.get("tb_d_aim_seulement_au_relachement")}')
# LE PLUS PROCHE GAGNE : la tete a 4 px bat le bord a 8 px. Sans cela, le
# premier candidat de la liste aurait toujours gagne.
check("tb_d_le_candidat_le_plus_proche_gagne",
      d.get("tb_d_aim_le_plus_proche") == [4, 0, "tg", ""],
      f'{d.get("tb_d_aim_le_plus_proche")}')
# UNE BARRE TROP LARGE N'AIMANTE RIEN : aucune borne n'est atteignable, donc
# aucun candidat ne l'est. La barre s'arrete au bord d'origine, et le nom du
# bord aimante reste VIDE — le distinguo compte, il dit que rien n'a colle.
check("tb_d_une_barre_trop_large_n_aimante_rien",
      len(_BORNES) == 4
      and d.get("tb_d_aim_barre_trop_large") == [_BORNES[0], "", ""],
      f'{d.get("tb_d_aim_barre_trop_large")}')

# ── L'UNION DES DEUX ZONES, ET LA PINCE ───────────────────────────────────
check("tb_d_le_conteneur_est_l_union_des_deux_rectangles",
      d.get("tb_d_boite") == [0, 100, 1000, 600],
      f'{d.get("tb_d_boite")}')
check("tb_d_un_seul_rectangle_lisible_resserre_le_bornage",
      d.get("tb_d_boite_un_seul") == [[5, 6, 7, 8], [5, 6, 7, 8], [7, 8]]
      and d.get("tb_d_boite_aucun") == [None, None],
      f'{d.get("tb_d_boite_un_seul")} aucun={d.get("tb_d_boite_aucun")}')
check("tb_d_la_pince_rend_le_bord_d_origine_quand_les_bornes_se_croisent",
      d.get("tb_d_pince") == [5, 0, 10, 10, 0], f'{d.get("tb_d_pince")}')

# ── LA CLE DU DECALAGE (§4.4) — MEME ECART DECLARE QUE `dz_svm_tb_open` ───
# `_DZ` a ete recense plus haut sur le bundle livre ; la cle est posee par
# une constante, donc elle n'y figure pas et ne peut entrer en collision avec
# rien. Le nom du handoff (`deepotus.toolbar.offset`) n'est nulle part :
# l'ecart est FAIT, pas seulement dit.
_LIT5 = '"' + str(d.get("tb_d_cle")) + '"'
check("tb_d_la_cle_du_decalage_suit_la_maison_et_le_prefixe_de_l_ecran",
      d.get("tb_d_cle") == "dz_svm_tb_off"
      and d["tb_d_cle"].startswith("dz_svm_tb_")
      and d["tb_d_cle"] != d.get("tb_cle")
      and s.count(nl(_LIT5)) == 1
      and d["tb_d_cle"] not in _DZ
      and '"deepotus.toolbar' not in s and "'deepotus.toolbar" not in s,
      f'cle={d.get("tb_d_cle")!r} litteraux={s.count(nl(_LIT5))} '
      f'collision={d.get("tb_d_cle") in _DZ}')
# LA FORME EST DU JSON, comme `dz_svm_keymap` — la seule cle `dz_*` de cette
# base qui stocke autre chose qu'une chaine plate, et le banc le REJOUE.
check("tb_d_le_json_est_la_forme_de_la_maison_pour_une_cle_composee",
      s.count(nl('"dz_svm_keymap"')) >= 1
      and "JSON.parse" in src and "JSON.stringify" in src,
      "dz_svm_keymap introuvable dans le bundle — la forme JSON n'a plus de "
      "precedent dans la maison, la cle doit etre rediscutee")
check("tb_d_le_decalage_se_relit_tel_qu_il_a_ete_ecrit",
      d.get("tb_d_off_lit") == [120, -40, ["dz_svm_tb_off"]]
      and d.get("tb_d_off_ecrit")
      == [[["dz_svm_tb_off", '{"dx":12,"dy":-7}']], 12, -7],
      f'lu={d.get("tb_d_off_lit")} ecrit={d.get("tb_d_off_ecrit")}')
# TOUT CE QUI N'EST PAS UN NOMBRE RETOMBE SUR L'ORIGINE, CHAMP PAR CHAMP —
# c'est le filet de securite de la cle : un `dz_svm_tb_off` corrompu a la
# main ne peut pas envoyer la barre hors de l'ecran, il la ramene chez elle.
# LE DERNIER CAS N'EST PAS `[0, 0]`, ET C'EST VOULU : un objet a moitie
# lisible garde ce qui l'est. Sans lui, une fonction qui rendrait TOUJOURS
# l'origine passerait les huit lignes.
check("tb_d_un_decalage_corrompu_ramene_la_barre_chez_elle",
      d.get("tb_d_off_replis") == [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0],
                                   [0, 0], [0, 0], [0, 9]],
      f'{d.get("tb_d_off_replis")}')
check("tb_d_le_decalage_ecrit_est_toujours_un_couple_de_nombres",
      d.get("tb_d_off_ecrit_propre")
      == [[["dz_svm_tb_off", '{"dx":0,"dy":0}']], 0, 0],
      f'{d.get("tb_d_off_ecrit_propre")}')
# UN MAGASIN QUI LEVE : la barre perd la MEMOIRE, jamais le mouvement en
# cours — `tbOffSet` rend quand meme le decalage demande.
check("tb_d_un_magasin_indisponible_ne_casse_pas_le_deplacement",
      d.get("tb_d_off_magasin_qui_leve") == [0, 0, 4, 5]
      and d.get("tb_d_off_sans_magasin") == [0, 0, 4, 5],
      f'leve={d.get("tb_d_off_magasin_qui_leve")} '
      f'sans={d.get("tb_d_off_sans_magasin")}')

# ── LE GESTE (§4.2) ───────────────────────────────────────────────────────
# LES ECOUTEURS SONT SUR LA FENETRE, PAS SUR L'ELEMENT. C'est le §4.2 au mot,
# et c'est une DIVERGENCE MESUREE d'avec la maison : `clipDown` du bundle
# pose les siens sur `e.currentTarget` et s'en tire par `setPointerCapture`.
# Les deux faces sont gardees — le precedent EST la, et on ne le suit pas.
# LA MESURE PORTE SUR LE CORPS DE `clipDown`, PAS SUR LE FICHIER : les deux
# jetons vivent QUATRE fois chacun dans le bundle (clipDown, fadeDown et deux
# autres glissers), et une recherche a l'echelle du fichier aurait ete verte
# meme si clipDown, lui, avait change de forme. Bornes de taille en conjoint
# positif : sans elles la ligne serait vraie d'un bloc introuvable.
_i_cd = s.find(nl("function clipDown(e,c,laneEl){"))
_j_cd = s.find(nl("function svmMixSet("), _i_cd) if _i_cd >= 0 else -1
_CD = s[_i_cd:_j_cd] if 0 <= _i_cd < _j_cd else "CLIPDOWN-INTROUVABLE"
check("bundle_clipDown_pose_ses_ecouteurs_sur_l_element_et_capture",
      2000 < len(_CD) < 9000
      and nl('tgt.addEventListener("pointermove",mv)') in _CD
      and nl('tgt.addEventListener("pointerup",up)') in _CD
      and nl("tgt.setPointerCapture(e.pointerId)") in _CD
      and "window.addEventListener" not in _CD,
      f"clipDown={len(_CD)} o — le precedent a change : la divergence du "
      f"§4.2 doit etre rediscutee")
check("tb_d_le_geste_ecoute_la_fenetre_et_marque_le_corps",
      d.get("tb_d_saisie_pose") == [["pointercancel", "pointermove",
                                     "pointerup"], 3, ["+dzm-tbdrag"]],
      f'{d.get("tb_d_saisie_pose")}')
# LA COUCHE NE POSE AUCUN ECOUTEUR DE POINTEUR SUR L'ELEMENT : la sonde
# ci-dessus mesure ce qu'elle a recu, celle-ci mesure qu'il n'y a pas de
# second chemin. Conjoint positif d'abord.
# LA COUCHE N'A PAS DE SECOND CHEMIN : dans le bloc de la barre, les QUATRE
# mentions de `addEventListener` — la garde plus les trois poses — portent
# toutes le prefixe `w.`, et autant pour le retrait. Et la couche ENTIERE
# n'appelle jamais `setPointerCapture` : c'est la forme de la maison qu'on
# ecarte, et l'ecarter a moitie aurait donne deux chemins concurrents.
# `.setPointerCapture(` AVEC LA PARENTHESE : le nom seul apparait une fois,
# dans le commentaire qui explique la divergence — chercher le jeton nu
# aurait fait rougir la ligne sur son propre commentaire (faute n°2).
check("tb_d_la_couche_n_ecoute_le_pointeur_que_sur_la_fenetre",
      _SRC_TB.count('addEventListener("pointer') == 3
      and _SRC_TB.count('w.addEventListener("pointer') == 3
      and _SRC_TB.count('removeEventListener("pointer') == 3
      and _SRC_TB.count('w.removeEventListener("pointer') == 3
      and _SRC_TB.count("addEventListener") > 3
      and _SRC_TB.count("addEventListener")
      == _SRC_TB.count("w.addEventListener")
      and _SRC_TB.count("removeEventListener")
      == _SRC_TB.count("w.removeEventListener")
      and src.count(".setPointerCapture(") == 0
      and src.count("setPointerCapture") == 1,
      f'pointeur={_SRC_TB.count(chr(34) + "pointer")} '
      f'add={_SRC_TB.count("addEventListener")} '
      f'w.add={_SRC_TB.count("w.addEventListener")} '
      f'capture={src.count(".setPointerCapture(")}')
# LE DEPLACEMENT SUIT LE POINTEUR ET EST BORNE A CHAQUE IMAGE, SANS AIMANTER.
check("tb_d_le_geste_borne_a_chaque_image_sans_aimanter",
      d.get("tb_d_saisie_deplace") == [[[60, 30, False, ""],
                                        [-6, 0, False, ""]], 3],
      f'{d.get("tb_d_saisie_deplace")}')
# LE RELACHEMENT AIMANTE, PUIS REND TOUT : les trois ecouteurs et la classe
# du corps. Le meme point, lache, colle au bord ; en cours de geste, non.
check("tb_d_le_relachement_aimante_puis_rend_tout",
      d.get("tb_d_saisie_relache_aimante")
      == [[[-3, False, ""], [-6, True, "g"]], [], 0,
          ["+dzm-tbdrag", "-dzm-tbdrag"]],
      f'{d.get("tb_d_saisie_relache_aimante")}')
# `pointercancel` TERMINE COMME UN RELACHEMENT — un ajout au §4.2, qui ne le
# nomme pas. Sans lui, un geste repris par le systeme laisserait `grabbing`
# colle sur tout le document : le geste destructif sans retour.
check("tb_d_une_annulation_de_pointeur_termine_et_rend_le_curseur",
      d.get("tb_d_saisie_annulee") == [[[60, False], [60, True]], 0,
                                       ["+dzm-tbdrag", "-dzm-tbdrag"]],
      f'{d.get("tb_d_saisie_annulee")}')
# UN RELACHEMENT SANS COORDONNEES LISIBLES NE VAUT PAS « deplacement nul » :
# la derniere position connue est gardee. Le temoin est DISTINGUABLE — sans
# cette garde le decalage retomberait a 0, qui s'aimanterait au bord gauche
# (6 px) et non a 60.
check("tb_d_un_relachement_sans_coordonnees_garde_la_derniere_position",
      d.get("tb_d_saisie_sans_coordonnees") == [[60, False], [60, True]],
      f'{d.get("tb_d_saisie_sans_coordonnees")}')
# APRES LA FIN, PLUS RIEN : un evenement qui traine ne rappelle pas la pose.
check("tb_d_apres_la_fin_un_evenement_qui_traine_ne_fait_rien",
      d.get("tb_d_saisie_apres_la_fin") == [1, 1],
      f'{d.get("tb_d_saisie_apres_la_fin")}')
# L'ANNULATEUR — celui que le demontage du composant appelle. Il retire les
# trois ecouteurs ET la classe, et il ne fait rien deux fois : une seconde
# `remove` sur le corps serait inoffensive, mais elle dirait que la garde
# `vif` ne garde rien.
check("tb_d_l_annulateur_rend_tout_et_ne_le_fait_qu_une_fois",
      d.get("tb_d_saisie_annulateur") == [0, ["+dzm-tbdrag", "-dzm-tbdrag"]],
      f'{d.get("tb_d_saisie_annulateur")}')
# SANS FENETRE, SANS GEOMETRIE, SANS POSE : un annulateur inoffensif, jamais
# une levee — c'est le chemin d'un rendu serveur et celui d'une barre pas
# encore posee dans le document.
check("tb_d_sans_fenetre_ni_geometrie_le_geste_ne_leve_pas",
      d.get("tb_d_saisie_sans_rien") == ["function", "function", "function"],
      f'{d.get("tb_d_saisie_sans_rien")}')
# SANS CORPS UTILISABLE, LE GESTE MARCHE QUAND MEME : le curseur est un
# confort, le deplacement est la fonction.
check("tb_d_sans_corps_le_deplacement_marche_quand_meme",
      d.get("tb_d_saisie_sans_corps") == [[[60, True]], 0],
      f'{d.get("tb_d_saisie_sans_corps")}')

# ── LE CLAVIER DE LA POIGNEE (§4.5) ───────────────────────────────────────
# LIVRE ICI, PAS A L'ETAPE 8, ET C'EST UN CHOIX : le §4.5 ecrit lui-meme
# « Un objet déplaçable à la souris seule n'est pas accessible ». Les pas
# viennent du HANDOFF (lus plus haut), pas d'ici.
_PS = _DIST[2] if len(_DIST) == 4 else None
_PF = _DIST[3] if len(_DIST) == 4 else None
check("tb_d_les_quatre_fleches_deplacent_du_pas_du_handoff",
      _PS is not None
      and d.get("tb_d_touche") == [[-_PS, 0, -_PF, 0], [_PS, 0, _PF, 0],
                                   [0, -_PS, 0, -_PF], [0, _PS, 0, _PF]],
      f'{d.get("tb_d_touche")} pas={_PS}/{_PF}')
# UNE TOUCHE QUI N'EST PAS UNE FLECHE NE DEPLACE RIEN — `constructor` et
# `__proto__` compris : un acces nu a la table aurait rendu la fonction
# heritee, donc « vraie », et un pas `NaN` sur une touche que personne n'a
# mappee. Conjoint positif : la ligne du dessus prouve que la table repond.
check("tb_d_aucune_autre_touche_ne_deplace_la_barre",
      isinstance(d.get("tb_d_touche_inconnue"), list)
      and len(d["tb_d_touche_inconnue"]) == 9
      and all(v is None for v in d["tb_d_touche_inconnue"]),
      f'{d.get("tb_d_touche_inconnue")}')

# ── LA MESURE DES RECTANGLES : LE CONTENEUR RETENU ────────────────────────
# LE §4.2 DIT « la zone timeline + zone de prévisualisation ». DANS CETTE
# BASE ce sont DEUX nœuds freres — `.svm-mid` (lecteur + inspecteur) puis
# `.svm-tl` (la timeline, dont `.svm-trans` est le premier enfant) — tous
# deux enfants directs de la racine `.dzsvm.svm-col`. Le rectangle retenu est
# leur UNION : tout l'ecran SOUS la barre de titre.
# LES TROIS FAITS QUI FONDENT CE CHOIX SONT REJOUES ICI, pas seulement ecrits
# en commentaire : les deux nœuds existent une fois chacun dans le bundle, la
# racine est le SEUL ancetre rogneur, et ni `.svm-tl` ni `.svm-mid` ne
# declarent d'overflow — sans quoi la barre serait coupee bien avant la
# borne, et le §4.2 ne serait pas tenu.
_SVCSS = _lire(ROOT / "frontend" / "dist" / "shared" / "son-vfx-montage.css")
_R_MID = _regle(_SVCSS, ".svm-mid{")
_R_TLR = _regle(_SVCSS, ".svm-tl{")
# DEUX REGLES `.dzsvm{` DANS CETTE FEUILLE : le bloc de TOKENS (l.20) puis
# la RACINE (l.49). `_regle` rend la premiere ; c'est la seconde qu'on veut,
# et on la designe par ce qu'elle contient, pas par son rang.
_R_RAC = None
for _m_rac in re.finditer(r"\.dzsvm\{([^{}]*)\}", _sansc(_SVCSS)):
    if "position:absolute" in _m_rac.group(1):
        _R_RAC = _m_rac.group(1)
check("tb_d_les_deux_zones_du_4_2_sont_deux_noeuds_uniques_du_bundle",
      s.count(nl('className:"svm-mid"')) == 1
      and s.count(nl('className:"svm-tl"')) == 1
      and s.count(nl('className:"svm-trans"')) == 1
      and s.count(nl('className:"svm-phline"')) == 1,
      f'mid={s.count(nl(chr(34) + "svm-mid" + chr(34)))} '
      f'tl={s.count(nl(chr(34) + "svm-tl" + chr(34)))}')
check("tb_d_ni_la_timeline_ni_la_zone_de_previsualisation_ne_rognent",
      _R_MID is not None and "overflow" not in _R_MID
      and _R_TLR is not None and "overflow" not in _R_TLR
      and len(_R_MID) > 20 and len(_R_TLR) > 40,
      f"mid={_R_MID!r} tl={_R_TLR!r}")
# LA RACINE, ELLE, ROGNE — et c'est ce qui rend le bornage SUFFISANT : tout
# le rectangle retenu est dedans, donc aucun pixel de la barre n'est coupe,
# donc elle reste recuperable (§4.2 : « Une barre à moitié sortie de l'écran
# n'est pas récupérable »).
check("tb_d_la_racine_est_le_seul_ancetre_rogneur_et_contient_le_conteneur",
      _R_RAC is not None and "overflow:hidden" in _R_RAC
      and "position:absolute" in _R_RAC and "inset:0" in _R_RAC,
      f"racine={_R_RAC!r}")
# ET LE FIL JOUE SOUS NODE, SUR UN FAUX ARBRE QUI REPRODUIT CETTE CHAINE :
# barre -> .svm-trans -> .svm-tl -> .dzsvm.svm-col, `.svm-mid` chez le meme
# parent. `.svm-tl` (0,400) 1000x300 et `.svm-mid` (0,100) 1000x300 -> union
# (0,100) 1000x600.
check("tb_d_le_conteneur_mesure_est_l_union_des_deux_zones",
      d.get("tb_d_conteneur") == [0, 100, 1000, 600],
      f'{d.get("tb_d_conteneur")}')
# SANS `.svm-mid` le bornage se RESSERRE sur la timeline seule au lieu de
# disparaitre ; sans `.svm-tl` il n'y a plus rien a borner, et on le DIT
# plutot que de rendre un rectangle invente.
check("tb_d_le_conteneur_se_resserre_ou_se_declare_introuvable",
      d.get("tb_d_conteneur_sans_mid") == [0, 400, 1000, 300]
      and d.get("tb_d_conteneur_sans_timeline") is None
      and d.get("tb_d_conteneur_sans_noeud") == [None, None],
      f'sans_mid={d.get("tb_d_conteneur_sans_mid")} '
      f'sans_tl={d.get("tb_d_conteneur_sans_timeline")} '
      f'sans_noeud={d.get("tb_d_conteneur_sans_noeud")}')
# L'AXE DE LA TETE : le MILIEU du filet, pas son bord. Le filet fait 1 px
# (son-vfx-montage.css) et il est rendu SANS condition dans `.svm-lanes` —
# son abscisse est donc lisible au relachement, ce que le §4.2 exige.
_R_PH = _regle(_SVCSS, ".svm-phline{")
check("tb_d_l_axe_de_la_tete_est_le_milieu_du_filet_toujours_rendu",
      d.get("tb_d_tete") == 300.5
      and d.get("tb_d_tete_absente") == [None, None, None]
      and _R_PH is not None and "width:1px" in _R_PH
      and "position:absolute" in _R_PH,
      f'tete={d.get("tb_d_tete")} absente={d.get("tb_d_tete_absente")} '
      f'regle={_R_PH!r}')
# LA REMONTEE D'ARBRE EST BORNEE : un cycle de parents ne doit pas boucler
# sans fin. Le banc en fabrique un.
# LE PLAFOND EST UNE PROPRIETE DE VIVACITE, PAS DE RESULTAT : un cycle rend
# `null` avec ou sans lui, il met seulement l'eternite a le faire. LA MESURE
# EST DONC LE NOMBRE DE PAS — un mutant qui monte le plafond a 4000 rougit
# ici, alors qu'une comparaison du seul resultat le laissait passer. C'est la
# campagne qui a ecrit cette ligne.
_AC = d.get("tb_d_ancetre_cycle")
check("tb_d_la_remontee_d_arbre_ne_boucle_pas_sur_un_cycle",
      isinstance(_AC, list) and len(_AC) == 3
      and _AC[0] is None and isinstance(_AC[1], int)
      and 0 < _AC[1] <= 64 and _AC[2] is True,
      f'{_AC} — pas de remontee avant abandon')
# TOUTE LA GEOMETRIE EN UNE FOIS, AU `pointerdown` — la discipline de
# `clipDown`, qui fige `rect` et `pxPerS` a la saisie. Mesurer a chaque
# image aurait fait bouger les bornes sous le geste : la timeline se
# redessine pendant la lecture.
check("tb_d_la_geometrie_est_figee_en_une_fois_a_la_saisie",
      d.get("tb_d_geo") == [14, 442, 0, 100, 1000, 600, 300.5, 3, 4, 500, 600]
      and d.get("tb_d_geo_sans_barre") == [None, None],
      f'{d.get("tb_d_geo")} sans={d.get("tb_d_geo_sans_barre")}')
# LE FIL COMPLET, DU FAUX ARBRE AU DECALAGE BORNE : mesure, geste et cœur
# ensemble. Un geste de +9000 px s'arrete a la borne, et le bord droit de la
# barre tombe a la marge du bord du conteneur.
check("tb_d_bout_en_bout_un_geste_enorme_s_arrete_a_la_marge",
      _MG is not None
      and d.get("tb_d_bout_en_bout") == [[[578, 0, False, ""],
                                          [578, 0, True, "d"]], 0,
                                         ["+dzm-tbdrag", "-dzm-tbdrag"], 592]
      and 592 + 400 == 1000 - _MG,
      f'{d.get("tb_d_bout_en_bout")}')

# ── LE RECADRAGE (§4.2) ───────────────────────────────────────────────────
# LE TROU QUE CECI BOUCHE : le decalage est stocke en RELATIF, donc la barre
# garde sa place quand la fenetre change de taille — mais « sa place » peut
# sortir du conteneur quand celui-ci retrecit, et le §4.2 dit qu'une barre a
# moitie sortie n'est pas recuperable. `⌖` voyage AVEC la barre et
# deviendrait injoignable ; l'onglet OUTILS, lui, ne bouge jamais, mais il ne
# sait que replier. On recadre donc, au montage et a chaque `resize`.
check("tb_d_la_barre_rentre_quand_le_conteneur_retrecit",
      len(_BORNES) == 4
      and d.get("tb_d_recadre") == [_BORNES[1], 176],
      f'{d.get("tb_d_recadre")} attendu={[_BORNES[1] if _BORNES else None, 176]}')
# `null` = RIEN A FAIRE, et c'est distinct de `{dx:0,dy:0}` : un decalage
# deja licite ne provoque ni ecriture ni rendu, et un conteneur NON MESURABLE
# ne ramene surtout pas la barre a l'origine — c'est la meme regression que
# le bornage refuse plus haut, et le chargement la rejouerait.
check("tb_d_le_recadrage_ne_touche_a_rien_quand_il_n_y_a_rien_a_faire",
      d.get("tb_d_recadre_rien_a_faire") is None
      and d.get("tb_d_recadre_sans_conteneur") == [None, None],
      f'rien={d.get("tb_d_recadre_rien_a_faire")} '
      f'sans={d.get("tb_d_recadre_sans_conteneur")}')
check("tb_d_le_redimensionnement_est_ecoute_sur_la_fenetre_et_rendu",
      d.get("tb_d_veille") == [[["resize"], 1], 1, 0]
      and d.get("tb_d_veille_sans_rien") == ["function", "function"],
      f'{d.get("tb_d_veille")} sans={d.get("tb_d_veille_sans_rien")}')

# ── LA FEUILLE HABILLE LE DEPORT ──────────────────────────────────────────
# LA TRANSLATION PASSE PAR `translate`, PAS PAR `transform` : `transform` est
# deja prise par le repli du §4.1 (`translateY(6px)`), et les deux se
# seraient ecrasees. `translate` est independante et se transitionne a part,
# donc l'aimantation s'anime sur `--dur-bar-snap` (180 ms) pendant que
# l'ouverture garde `--dur-bar-open` (220 ms). AUCUN MINUTEUR.
check("tb_d_le_decalage_passe_par_translate_et_s_anime_sur_dur_bar_snap",
      _R_BAR is not None
      and "translate:var(--tbx, 0px) var(--tby, 0px)" in _R_BAR
      and "translate var(--dur-bar-snap," in _R_BAR
      and "transform var(--dur-bar-open," in _R_BAR
      and _R_BOFF is not None and "transform:translateY(6px)" in _R_BOFF
      and "translate" not in _R_BOFF.split("transition")[0]
      .replace("transform:translateY(6px)", ""),
      f"bar={_R_BAR!r}")
# PENDANT LE GESTE, AUCUNE TRANSITION : sans cette regle la barre suivrait le
# pointeur avec 180 ms de retard.
check("tb_d_le_geste_coupe_la_transition",
      _R_BDRAG is not None and "transition:none" in _R_BDRAG,
      f"{_R_BDRAG!r}")
check("tb_d_la_poignee_montre_grabbing_pendant_le_geste",
      _R_GRIPD is not None and "cursor:grabbing" in _R_GRIPD,
      f"{_R_GRIPD!r}")
# LE CURSEUR SUR TOUT LE DOCUMENT ET LA SELECTION COUPEE (§4.2). La classe
# est celle que la couche pose, lue dans le contrat — pas une chaine retapee
# ici. CONTROLE A DEUX FACES : la regle existe dans la feuille, et le nom
# vient du JS.
check("tb_d_le_curseur_et_la_selection_sont_pris_sur_tout_le_document",
      d.get("tb_d_classe_geste") == "dzm-tbdrag"
      and _R_CORPS is not None
      and "cursor:grabbing !important" in _R_CORPS
      and "user-select:none" in _R_CORPS
      and _MC.count("body.dzm-tbdrag") == 2,
      f'classe={d.get("tb_d_classe_geste")!r} regle={_R_CORPS!r}')
# LE MOUVEMENT REDUIT (§4.5 : « aimantation immédiate ») EST SERVI PAR UNE
# REGLE QUI EXISTE DEJA, et la mesure CORRIGE une attribution de l'etape 3 :
# le coupe-circuit ne vient pas de shared/deepotus.tokens.css — dist/index.html
# ne charge PAS cette feuille — mais de son-vfx-montage.css, chargee l.17.
check("tb_d_le_coupe_circuit_de_mouvement_reduit_couvre_bien_cet_ecran",
      "prefers-reduced-motion" in _SVCSS
      and re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*"
                    r"\.dzsvm \*[^}]*transition-duration:\s*\.001ms\s*"
                    r"!important", _SVCSS) is not None
      and "/shared/deepotus.tokens.css" not in _HTML
      and _HTML.find("/shared/son-vfx-montage.css") > 0,
      "le coupe-circuit global de son-vfx-montage.css a change : "
      "l'aimantation n'est plus immediate sous mouvement reduit")

# ── LA BARRE PEINT LE DEPORT ──────────────────────────────────────────────
check("tb_d_la_barre_peint_le_decalage_en_deux_longueurs",
      d.get("tb_r_deport") == ["42px", "-13px", ""]
      and d.get("tb_r_deport_defaut") == ["0px", "0px", None],
      f'{d.get("tb_r_deport")} defaut={d.get("tb_r_deport_defaut")}')
# UN DECALAGE POURRI NE PEINT PAS `NaNpx` : la regle CSS serait ANNULEE, et
# la barre sauterait a son ancrage sans un mot.
check("tb_d_un_decalage_pourri_ne_peint_jamais_nan",
      d.get("tb_r_deport_pourri") == ["0px", "0px", "0px"],
      f'{d.get("tb_r_deport_pourri")}')
# `⌖` N'EST JAMAIS MASQUE, MEME EN MODE COMPACT (§4.2 : « il ne doit jamais
# être masqué en mode compact »). LE SEUL LEVIER DE MASQUAGE DE CETTE BARRE
# est `--lbl`, et il ne s'applique QU'AU libelle des boutons d'action : une
# seule lecture de `var(--lbl` dans toute la feuille, et elle est dans
# `.dzm-tbl`. Les deux colonnes de bord, elles, sont en `display:flex` en
# dur. Conjoint positif d'abord : le levier EXISTE.
_R_LBL = _regle(_MC, ".dzsvm .dzm-tbl{")
# ETAPE 6 : LA FEUILLE PORTE MAINTENANT DES `display:none` — ce sont les
# sacrifices du §5.3, et ils ne visent QUE des noeuds du bandeau. La ligne ne
# peut donc plus dire « aucun display:none ici » ; elle dit ce qu'elle voulait
# dire depuis le debut : AUCUN noeud de la barre ne se masque. Les regles qui
# masquent sont comptees et leur selecteur doit porter `[data-bdoff` — un
# `display:none` pose ailleurs, ou visant un `.dzm-`, rougit.
_MASQUES = list(re.finditer(r"([^{}]*)\{([^{}]*display:none[^{}]*)\}",
                            _sansc(_MC)))
check("tb_d_seul_le_libelle_est_masquable_jamais_le_recentrage",
      _R_LBL is not None and "display:var(--lbl, block)" in _R_LBL
      and _sansc(_MC).count("var(--lbl") == 1
      and _R_WIN is not None and "display:flex" in _R_WIN
      and _R_WB is not None and "display:flex" in _R_WB
      and "--lbl" not in _R_WIN and "--lbl" not in _R_WB
      and len(_MASQUES) == 3
      and all("[data-bdoff" in _m.group(1) for _m in _MASQUES)
      and not any(".dzm-" in _m.group(1) for _m in _MASQUES),
      f'lbl={_R_LBL!r} lectures={_sansc(_MC).count("var(--lbl")} '
      f'masques={[_m.group(1).strip()[:60] for _m in _MASQUES]}')
check("tb_d_la_barre_rend_sa_reference_et_sa_poignee_saisit",
      d.get("tb_r_ref") is True and d.get("tb_r_grip_saisit") == [1, 1],
      f'ref={d.get("tb_r_ref")} saisit={d.get("tb_r_grip_saisit")}')

# ═══════════════════════════════════════════════════════════════════════════
# [6-quater] LES TROIS EXIGENCES TRANSVERSALES DU §6, JOUEES — ETAPE 7
# Le §6 en demande trois : le MEME historique d'annulation, AUCUN deplacement
# de la tete de lecture, et le respect d'« aimanter » pour les insertions a la
# tete. Elles ne se lisent pas, elles se MESURENT : les neuf actions sont
# rejouees sur un faux ecran qui reproduit la semantique du bundle livre, et
# ces lignes lisent ce qui en sort.
# ═══════════════════════════════════════════════════════════════════════════
print("\n[6-quater] la barre d'outils — le cablage du §6 et ses trois "
      "exigences")

_B7 = d.get("tb7_par_bouton")
# LES NEUF SONT CEUX DU §2.4, ET LA LISTE N'EST PAS RETAPEE ICI : elle vient
# de `tb_plan_icones`, deja compare au tableau du handoff plus haut. Le jour
# ou un bouton s'ajoute au plan sans passer par le cablage, cette ligne le
# dit avant toutes les autres.
_NEUF = d.get("tb_plan_icones")
check("tb7_les_neuf_actions_du_plan_sont_jouees",
      isinstance(_B7, list) and isinstance(_NEUF, list) and len(_NEUF) == 9
      and [r[0] for r in _B7] == _NEUF,
      f'joues={[r[0] for r in (_B7 or [])]} plan={_NEUF}')

# ── EXIGENCE 1 — « TOUTES LES ACTIONS PASSENT PAR LE MEME HISTORIQUE » ────
# IL N'Y EN A QU'UN, et la barre n'en cree pas un second : chaque action qui
# ecrit passe par le `pushHistory` de l'ecran. MAIS CE QU'IL REND DIFFERE, et
# c'est la mesure qui le dit :
#   • les deux PISTES poussent une entree qui ne contient que des clips
#     INCHANGES — `Ctrl+Z` la consomme et ne defait rien de visible ;
#   • les emoji poussent une entree qui REND les clips ;
#   • MOT, texte et projets ne poussent RIEN : `Ctrl+Z` defait le geste
#     d'avant.
# LE TABLEAU EST EPINGLE EN ENTIER, ligne par ligne. Chaque colonne est
# nommee dans le commentaire qui la precede ; une action qui changerait de
# comportement changerait sa ligne, et la ligne rougirait seule.
#           cle           pousse  [clips,pistes,style,texte,panneaux,projReq]
#                                 undo?  [clips,pistes,style,texte RENDUS ?]
#                                        [tete lue, tete ecrite]
_F, _V = False, True
_ATTENDU_B7 = [
    ["piste-video", 1, [_F, _V, _F, _F, 0, 0], _V, [_V, _F, _V, _V], [0, 0]],
    ["piste-audio", 1, [_F, _V, _F, _F, 0, 0], _V, [_V, _F, _V, _V], [0, 0]],
    ["bibliotheque", 0, [_F, _F, _F, _F, 1, 0], _F, [_V, _V, _V, _V], [0, 0]],
    ["couleur", 0, [_F, _F, _V, _F, 0, 0], _F, [_V, _V, _F, _V], [0, 0]],
    ["rebond", 0, [_F, _F, _V, _F, 0, 0], _F, [_V, _V, _F, _V], [0, 0]],
    ["glow", 0, [_F, _F, _V, _F, 0, 0], _F, [_V, _V, _F, _V], [0, 0]],
    ["emoji", 1, [_V, _F, _F, _F, 0, 0], _V, [_V, _V, _V, _V], [0, 0]],
    ["texte", 0, [_F, _F, _F, _V, 0, 0], _F, [_V, _V, _V, _F], [0, 0]],
    ["projets", 0, [_F, _F, _F, _F, 0, 1], _F, [_V, _V, _V, _V], [0, 0]]]
check("tb7_exigence1_ce_que_chaque_action_pousse_et_ce_qu_annuler_rend",
      _B7 == _ATTENDU_B7,
      f'{_B7}')
# LA TABLE `DZM_TB_EFFETS` NE DECRIT PAS UNE INTENTION : le genre est DEDUIT
# du comportement observe, puis compare a celui qu'elle annonce. Une table
# qui mentirait — ou une action qui changerait sans que la phrase suive —
# rougirait ici. C'est ce qui empeche les neuf infobulles de deriver.
_T7 = d.get("tb7_table")


def _genre_observe(row):
    """Le genre DEDUIT de ce que l'action a fait, jamais lu dans la table."""
    _k, _pousse, _touche, _rendu, _apres, _tete = row
    _clips, _pistes, _style, _txt, _panneaux, _proj = _touche
    if _panneaux or _proj:
        return ("clips" if _panneaux else "projet"), "panneau"
    if _pousse == 1 and _pistes and _apres[1] is False:
        return "piste", "direct"
    if _pousse == 1 and _clips and _rendu and _apres[0] is True:
        return "clips", "direct"
    if _pousse == 0 and _style and _apres[2] is False:
        return "style", "direct"
    if _pousse == 0 and _txt and _apres[3] is False:
        return "panneau", "direct"
    return "?", "?"


_OBS = dict((r[0], _genre_observe(r)) for r in (_B7 or []))
_DEC = dict((t[0], (t[1], t[2])) for t in (_T7 or []))
check("tb7_la_table_des_effets_dit_ce_que_les_actions_font_vraiment",
      len(_OBS) == 9 and _OBS == _DEC
      and all(x[0] != "?" for x in _OBS.values()),
      f'observe={_OBS}\n      declare={_DEC}')
# LES CINQ PHRASES, ET LEUR PLACE. Chaque titre cable SE TERMINE par celle de
# son genre, et il reste du texte devant : sans ce second terme, un titre
# REDUIT a la phrase passerait. Un genre inconnu rend la chaine VIDE — mieux
# qu'« undefined » dans une infobulle, et la ligne au-dessus rougirait.
_PH7 = d.get("tb7_phrases")
check("tb7_chaque_titre_finit_par_la_phrase_de_son_genre",
      d.get("tb7_titres_finissent_par_la_phrase")
      == [[True, True, True]] * 9,
      f'{d.get("tb7_titres_finissent_par_la_phrase")}')
check("tb7_cinq_phrases_pour_neuf_boutons_et_aucune_vide",
      isinstance(_PH7, list) and len(_PH7) == 9
      and len(set(_PH7)) == 5 and all(len(x) > 60 for x in _PH7)
      and d.get("tb7_undo_inconnu") == ["", "", ""],
      f'{len(set(_PH7 or []))} phrase(s) distinctes ; '
      f'inconnu={d.get("tb7_undo_inconnu")}')

# ── EXIGENCE 2 — « AUCUNE ACTION NE DEPLACE LA TETE DE LECTURE » ─────────
# TROIS MESURES, ET AUCUNE N'EST UNE LECTURE D'INTENTION.
# 1. LES NEUF ACTIONS SONT JOUEES sur un objet dont `ph` est un ACCESSEUR
#    compte : ni lue, ni ecrite, et la valeur n'a pas bouge.
check("tb7_exigence2_les_neuf_actions_ne_lisent_ni_n_ecrivent_la_tete",
      d.get("tb7_la_tete_de_lecture") == [9, 0, 0, 3.5],
      f'{d.get("tb7_la_tete_de_lecture")} (attendu [9, 0, 0, 3.5])')
# 2. TOUTE LA CHAINE DE PATCHS NE NOMME NI `setPh` NI `seekTo`. Conjoints
#    positifs d'abord : les deux textes existent et sont gros, et le bundle
#    porte bien les huit `setPh(` qu'on lui connait — sans eux, la negation
#    serait vraie d'un fichier vide.
check("tb7_exigence2_la_chaine_ne_nomme_jamais_setPh_ni_seekTo",
      len(_SECTIONS) > 10000 and len(_code(src)) > 60000
      and s.count(nl("setPh(")) == 8
      and "setPh" not in _SECTIONS and "seekTo" not in _SECTIONS
      and "setPh" not in _code(src) and "seekTo" not in _code(src),
      f'setPh dans le bundle={s.count(nl("setPh("))} '
      f'sections={len(_SECTIONS)} o couche={len(_code(src))} o')
# 3. LE SEUL `setPh` QUI RAMENE A ZERO EST CELUI DE `svmApplyProject`, et
#    aucun des neuf chemins ne l'atteint : `projets` OUVRE la liste, il
#    n'ouvre aucun projet (mesure ci-dessous, `tb7_projets`). Le titre le
#    dit a l'utilisateur, mot pour mot.
check("tb7_exigence2_ouvrir_un_projet_est_le_seul_chemin_qui_bouge_la_tete",
      s.count(nl("setClips(cs);setSelId(first?first.id:\"\");setPh(0);"
                 "setDirty(!!(d.saved&&dzDd.renamed.length));")) == 1
      and s.count(nl("histRef.current={u:[],r:[]};")) >= 1
      and "onOpen:function(d){return svmApplyProject(d)}" in P.R_M14
      and "svmApplyProject" not in P.R_M19
      and "ramène la tête à zéro" in src,
      "svmApplyProject n'est plus le seul a remettre la tete a zero, ou la "
      "barre l'appelle")

# ── EXIGENCE 3 — « LES INSERTIONS A LA TETE RESPECTENT AIMANTER » ────────
# CE QUE CETTE BASE EN FAIT, MESURE : `aimanter` (`snap`) n'est LU qu'a un
# seul endroit du bundle, `doSnap`, dans le GLISSEMENT d'un clip. Aucune
# insertion ne le consulte — ni `addAsset`, ni `subsAddHere`, ni les emoji.
# LA BARRE N'EN POSE PAS UNE SECONDE REGLE : elle ne calcule aucune position.
# Le seul de ses neuf boutons qui mene a une insertion a la tete est
# « lier », et il ne transmet QUE la piste — le placement reste entier a
# `openPicker`, donc identique a celui du « + » d'en-tete de piste.
# MESUREE PAR MUTATION : en faisant passer un second argument a `p.onPick`,
# la ligne rougit.
check("tb7_exigence3_lier_ne_transmet_que_la_piste_et_delegue_le_placement",
      d.get("tb7_lier_ne_transmet_que_la_piste") == [[["v2"]], 0, 0],
      f'{d.get("tb7_lier_ne_transmet_que_la_piste")}')
_CODE_TB = _code(_SRC_TB)
check("tb7_exigence3_aimanter_n_a_qu_un_lecteur_et_la_barre_n_en_est_pas_un",
      s.count(nl("function doSnap(v){if(!snap)return v;"
                 "var t=8/pxPerS,best=v;")) == 1
      and s.count(nl("var st6=x.useState(!0),snap=st6[0],"
                     "setSnap=st6[1];")) == 1
      and len(_CODE_TB) > 8000 and len(P.R_M19) > 400
      and "snap" not in _CODE_TB and "Snap" not in _CODE_TB
      and "snap" not in P.R_M19 and "Snap" not in P.R_M19
      # LE COMMENTAIRE, LUI, DIT LA REGLE : sans ce conjoint, effacer
      # l'explication laisserait la ligne verte.
      and "AUCUNE insertion ne le" in _SRC_TB,
      f'doSnap={s.count(nl("function doSnap(v){if(!snap)return v;"))} '
      f'code_barre={len(_CODE_TB)} o snap={"snap" in _CODE_TB} '
      f'M19={"snap" in P.R_M19}')

# ── EMOJI — L'ACTION SORTIE DU BOUTON, JOUEE DE BOUT EN BOUT ───────────
# UNE requete, DEUX clips poses sur la piste d'overlay la plus haute AUX
# DATES DES MOTS (1,25 s et 3,5 s — ce sont les `t` des indices, pas la tete
# de lecture, qui vaut 3,5 : le second coincide, le premier prouve que ce
# n'est pas elle), duree 0,8 s, l'historique pousse AVANT, l'attente allumee
# puis eteinte, une note, et `undo` qui rend la timeline de depart.
check("tb7_emoji_pose_un_clip_par_mot_reconnu_et_annuler_les_retire",
      d.get("tb7_emoji_pose_les_clips")
      == [[["/api/subtitles/emoji-hints", "POST"]], 3,
          [["v2", 1.25, 0.8], ["v2", 3.5, 0.8]], 1, 0, 1, True, 1],
      f'{d.get("tb7_emoji_pose_les_clips")}')
# LES QUATRE REFUS, CHACUN SON JETON. Un `return` nu les aurait rendus
# indiscernables, et la ligne serait restee vraie d'une fonction muette :
# trois d'entre eux ecrivent une note, le premier (deja occupee) n'en ecrit
# pas — c'est le compte qui le dit.
check("tb7_emoji_refuse_en_nommant_le_refus",
      d.get("tb7_emoji_refus")
      == ["occupe", "sans-soustitre", "sans-hote", "sans-reseau", 3],
      f'{d.get("tb7_emoji_refus")}')
check("tb7_emoji_une_reponse_sans_indice_ne_pousse_rien",
      d.get("tb7_emoji_sans_indice") == [0, 1, 1, True, 0],
      f'{d.get("tb7_emoji_sans_indice")}')
# PENDANT L'ATTENTE : eteint, SANS action, et un titre QUI DIFFERE de celui
# du bouton vivant — sinon le bouton s'eteindrait sans dire pourquoi.
_AT = d.get("tb7_emoji_attente")
check("tb7_emoji_s_eteint_pendant_l_attente_et_le_dit",
      isinstance(_AT, list) and _AT[0] is True and _AT[1] is None
      and len(_AT[2]) > 60
      and isinstance(_VI, list) and _AT[2] != _VI[0][2],
      f'{_AT}')
# `dzmTbHote` — LA DECISION DU DOCK, JOUEE : sans receveur, pas d'action ;
# sans fonction d'appel non plus. Les deux moities comptent, et la ligne
# les separe.
check("tb7_le_dock_n_allume_emoji_que_s_il_a_de_quoi_recevoir_les_clips",
      d.get("tb7_hote") == ["null", "function", "null", False, True, False],
      f'{d.get("tb7_hote")}')
check("tb7_le_dock_copie_les_proprietes_de_l_ecran_et_ne_les_mute_pas",
      d.get("tb7_hote_ne_mute_pas") == [False, False, True, True, 2],
      f'{d.get("tb7_hote_ne_mute_pas")}')
# L'UNE APPELLE L'AUTRE : sans cette ligne, `dzmEmojiGo` pourrait etre
# mesuree pour elle-meme pendant que le bouton du bandeau garde une copie.
# MEME PARADE QUE POUR `dzmTbFrame` a l'etape 4 : le jeton est une
# INSTRUCTION entiere, pas un nom.
check("tb7_les_deux_portes_appellent_la_meme_action_emoji",
      src.count("function dzmEmojiGo(p){") == 1
      and src.count("dzmEmojiGo({") == 2
      and "onClick:function(){dzmEmojiGo({segments:props&&props.segments," in src
      and "dzmEmojiGo({segments:o.emojiSegs,tracks:o.tracks,note:o.note," in src
      and "emojiGo:dzmEmojiGo" in src
      and s.count(nl("function dzmEmojiGo(p){")) == 1,
      f'definitions={src.count("function dzmEmojiGo(p){")} '
      f'appels={src.count("dzmEmojiGo({")}')

# ── PROJETS — IL OUVRE, ET RIEN D'AUTRE ─────────────────────────
# DEUX clics, DEUX demandes — le §6 dit OUVRE, pas BASCULE, et un compteur
# ne referme jamais par accident. Aucune ecriture de timeline, aucun pas
# d'historique, aucun projet ouvert, aucune note.
check("tb7_projets_ouvre_la_liste_et_ne_touche_a_rien_d_autre",
      d.get("tb7_projets") == [2, 0, 1, 0, 0, 0, 0],
      f'{d.get("tb7_projets")}')
# LE COMPTEUR VA JUSQU'AU POPOVER, ET LE POPOVER L'ECOUTE. Controle a DEUX
# FACES : la section le passe, la couche le lit, et la garde `oreq<=0`
# empeche la liste de s'ouvrir toute seule au montage.
_i_pj = src.find("var oreq=Number(props&&props.openReq)||0;")
_EFF_PJ = src[_i_pj:_i_pj + 220] if _i_pj >= 0 else "INTROUVABLE"
check("tb7_la_demande_d_ouverture_va_de_la_barre_au_popover",
      "onProjets:function(){setDzProjReq(function(n){return n+1})}" in P.R_M19
      and "openReq:dzProjReq" in P.R_M14
      and "var stDzPj=x.useState(0),dzProjReq=stDzPj[0]," in P.R_M11
      and _i_pj >= 0
      and "if(oreq<=0)return;" in _EFF_PJ
      and "setOp(!0);setArm(\"\");setRen(null);load()},[oreq]);" in _EFF_PJ,
      f'effet={_EFF_PJ[:180]!r}')
# ET LA CONFIRMATION QUE LE §6 EXIGE (« demander confirmation avant de
# quitter ») EXISTAIT DEJA, plus stricte que demandee : le popover arme le
# bouton « ouvrir » et ne remplace le montage qu'au SECOND clic, que le
# projet courant soit modifie ou non.
check("tb7_ouvrir_un_projet_demande_toujours_confirmation",
      'if(arm!=="o"+p.id){setArm("o"+p.id);return}' in src
      and "children:oArm?\"remplacer ?\":\"ouvrir\"" in src
      and s.count(nl('if(arm!=="o"+p.id){setArm("o"+p.id);return}')) == 1,
      "le second clic de confirmation a disparu de doOpen")


# ═══════════════════════════════════════════════════════════════════════════
# [6-quinquies] LE BANDEAU REDISTRIBUE — ETAPE 6 DU §9 (§5.1, §5.2, §5.3)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[6-quinquies] §5 — le bandeau redistribué : retrait, place, "
      "dégradation")

# ── §5.1, LA PREUVE MAITRESSE ─────────────────────────────────────────────
# LES NEUF QUI ONT QUITTE LE BANDEAU SONT EXACTEMENT LES NEUF QUE LA BARRE
# PORTE. C'est la ligne qui interdit qu'un controle devienne introuvable :
# elle rapproche la table des RETIRES (couche, §5.1) des clefs du PLAN de la
# barre (couche, §2.4, deja confrontee au design.md plus haut) et du CABLAGE
# joue sous node (les neuf `act`, tous non nuls). Trois listes, un seul
# ensemble. Si l'une des trois bougeait seule, cette ligne rougirait — c'est
# le geste destructif de cette etape, et c'est son garde-fou.
check("bd_les_neuf_retires_sont_exactement_les_neuf_de_la_barre",
      d.get("bd_ctl") == sorted(_CABLES)
      and d.get("tb_c_cles") == sorted(_CABLES)
      and d.get("tb_c_actions") == _CABLES
      and d.get("tb_c_eteints") == [],
      f'retires={d.get("bd_ctl")} plan={d.get("tb_c_cles")} '
      f'cables={d.get("tb_c_actions")} eteints={d.get("tb_c_eteints")}')
# LES LIBELLES DE LA TABLE SONT CEUX DES COMPOSANTS, pas une seconde
# redaction. CONTROLE A DEUX FACES : chaque libelle doit exister DANS la
# couche entre guillemets (la face « ce que l'ecran ecrivait ») et la table
# doit en porter dix — les neuf controles plus l'etiquette `mot`, que le §5.1
# nomme lui aussi (« l'étiquette MOT et ses trois options »).
_LBL_BD = d.get("bd_libelles") or []
_LBL_ABS = [x for x in _LBL_BD if '"%s"' % x not in src]
check("bd_les_libelles_retires_sont_ceux_des_composants",
      len(_LBL_BD) == 10 and not _LBL_ABS
      and "+ piste vidéo" in _LBL_BD and "Bibliothèque…" in _LBL_BD
      and "projets" in _LBL_BD,
      f'{len(_LBL_BD)} libellés, introuvables dans la couche : {_LBL_ABS}')
# LA PLACE RENDUE, RECALCULEE SOUS NODE. 697 px n'est pas un chiffre tape
# ici : c'est la somme que `dzmBdRetire` rend, et les deux cotes doivent
# tomber d'accord. Le PROTOCOLE est nomme dans la couche (avance 0,6 em de
# JetBrains Mono a 10 px = 6,0 px/caractere, boite `border-box`, intervalle
# compte avec le noeud) et la RESERVE aussi : c'est une largeur NOMINALE,
# une fonte de repli en rendrait moins.
# LE DETAIL DE `bdPx` EST LA POUR QUE LE TOTAL NE SOIT PAS UNE BOITE NOIRE :
# un bouton de 5 caracteres a 16 px de rembourrage fait 48, et un `px` en dur
# l'emporte sur le calcul (l'etiquette `mot`, seule de son espece).
check("bd_la_place_rendue_vaut_697px_pour_neuf_controles",
      d.get("bd_retire") == [697, 9, 10]
      and d.get("bd_px_un") == [48, 18, 2],
      f'retire={d.get("bd_retire")} px={d.get("bd_px_un")}')

# ── §5.2, LA GEOMETRIE ────────────────────────────────────────────────────
# LES SEPARATEURS : 1 px, 26 px de haut, 12 px de vide de chaque cote — le
# §5.2 au mot (« séparateurs verticaux de 1 px --brd-hard avec
# margin: 0 12px »). L'arithmetique est ecrite dans la feuille ; ici on
# mesure qu'elle y est ECRITE : `gap:12px` (amont) + `margin-left:13px` = 25,
# filet a `left:-13px`, donc 12 de chaque cote.
_SEPS = [_m for _m in re.finditer(r"([^{}]*)\{([^{}]*)\}", _sansc(_MC))
         if "left:-13px" in _m.group(2)]
check("bd_les_separateurs_du_5_2_font_1px_sur_26_avec_12px_de_vide",
      len(_SEPS) == 2
      and all("width:1px" in _m.group(2) and "height:26px" in _m.group(2)
              and "top:50%" in _m.group(2)
              and "margin-top:-13px" in _m.group(2)
              and "--brd-hard" in _m.group(2) for _m in _SEPS)
      and "margin-left:13px" in _sansc(_MC)
      and "margin-left:19px" in _sansc(_MC),
      f'{len(_SEPS)} règle(s) de filet')
# LE ZOOM EST POUSSE A DROITE, ET L'INTERCALAIRE DU §5.2 EXISTE DEJA : la
# feuille AMONT donne `margin-left:auto` a `.svm-zoom` (l.324). MESURE PLUTOT
# QUE SUPPOSITION — c'est ce qui a evite d'en ajouter un second, qui aurait
# ramene le zoom au milieu du bandeau. La ligne exige les deux faces : la
# regle amont porte bien `margin-left:auto`, ET la notre ne la remplace pas.
_ZOOM_AMONT = _regle(_HDCSS, ".svm-zoom{")
_ZOOM_NOUS = [_m.group(2) for _m in re.finditer(r"([^{}]*)\{([^{}]*)\}",
                                                _sansc(_MC))
              if any(x.strip().endswith(".svm-zoom") for x in
                     _m.group(1).split(","))]
check("bd_le_zoom_est_pousse_a_droite_par_l_intercalaire_qui_existait",
      _ZOOM_AMONT is not None and "margin-left:auto" in _ZOOM_AMONT
      and len(_ZOOM_NOUS) == 2
      and not any("margin-left" in b for b in _ZOOM_NOUS)
      and sum(1 for b in _ZOOM_NOUS if "order:1" in b) == 1,
      f'amont={_ZOOM_AMONT!r} nous={_ZOOM_NOUS}')
# ET IL EST LE DERNIER BLOC, pas seulement pousse : le §5.2 (item 7) met le
# zoom et `ajuster` en queue. Les rappels et le « ? », qui les suivaient dans
# le flux, passent devant par `order` — SANS un noeud de plus dans le bandeau.
# LES DEUX MEMBRES DU BLOC PORTENT LE MEME `order`, sinon `ajuster` resterait
# derriere pendant que le zoom passerait devant.
# LA RECHERCHE EST BORNEE, ET C'EST UNE MESURE, PAS UNE PRECAUTION : `order:1`
# est SOUS-CHAINE de `border:1px`, et la premiere version de cette ligne
# ramassait DIX-HUIT regles — toutes celles qui portent un filet. Faute n°2,
# attrapee par le detail d'echec, qui imprimait les dix-huit selecteurs.
_ORD = [_m.group(1) for _m in _REGLES(_MC)
        if re.search(r"(^|[;\s])order:1(;|$)", _m.group(2).strip())]
check("bd_le_zoom_et_ajuster_sont_le_dernier_bloc_du_bandeau",
      len(_ORD) == 1 and ".svm-zoom" in _ORD[0] and ".dzm-durctl" in _ORD[0]
      and len(re.findall(r"(^|[;\s{])order:", _sansc(_MC))) == 1,
      f'{_ORD}')
# LE STYLE COMMUN DES BOUTONS (§5.2) — 26 px, 0 9px, 11 px, filet, radius 0.
# SCOPE AU BANDEAU : `.svm-tbtn` sert aussi l'inspecteur et les en-tetes de
# piste, que le §5 ne touche pas. Le bouton de lecture garde son or, et sa
# regle doit venir APRES celle qui lui rendrait un filet.
_BTN = _regle(_MC, ".dzsvm .svm-trans > .svm-tbtn{")
_GOLD = _regle(_MC, ".dzsvm .svm-trans > .svm-transbtns > .svm-tbtn.svm-gold{")
check("bd_les_boutons_du_bandeau_suivent_le_style_commun_du_5_2",
      _BTN is not None and _GOLD is not None
      and all(_x in _BTN for _x in ("height:26px", "padding:0 9px",
                                    "font-size:11px", "border-radius:0",
                                    "--brd-hard", "--srf-raised"))
      and "border-color:transparent" in _GOLD and "--accent" in _GOLD
      and _MC.index(".svm-tbtn.svm-gold{") > _MC.index(
          ".dzsvm .svm-trans > .svm-tbtn{"),
      f'btn={_BTN!r} gold={_GOLD!r}')
# LA LISTE DES PROJETS, MONTEE NUE : hors flux (sinon elle ouvrirait un
# intervalle de 12 px pour rien) et ancree A DROITE, loin de la barre
# flottante qui vit a `left:14px`. Le popover suit son ancre : `right:0`.
# CONJOINT : le composant sait etre nu, et la section le lui demande.
_NU = _regle(_MC, ".dzsvm .svm-trans > .dzm-proj[data-nu]{")
_NUP = _regle(_MC, '.dzsvm .dzm-proj[data-nu] > .dzm-projp{')
check("bd_la_liste_des_projets_est_montee_nue_et_ancree_a_droite",
      _NU is not None and _NUP is not None
      and "position:absolute" in _NU and "right:14px" in _NU
      and "width:0" in _NU
      and "left:auto" in _NUP and "right:0" in _NUP
      and "var nu=!!(props&&props.nu);" in src
      and "nu?null:r.jsx(" in src
      and '"data-nu":nu?"":void 0' in src
      and "nu:!0" in P.R_M14,
      f'nu={_NU!r} popover={_NUP!r}')

# ── §5.3, LA DEGRADATION ──────────────────────────────────────────────────
# L'ORDRE DE SACRIFICE, LU DANS LA COUCHE : quatre rangs, dans l'ordre du
# §5.3 adapte a ce qui existe (le detail rang par rang est ecrit dans la
# couche, avec le principe du rang d'origine).
check("bd_l_ordre_de_sacrifice_suit_le_5_3",
      d.get("bd_rangs") == ["hints:1:.svm-hints",
                            "coupe:2:.svm-toolchips",
                            "metre:3:.svm-meterslot",
                            "tctotal:4:.svm-tctotal"],
      f'{d.get("bd_rangs")}')
# LE PLAN, SUR LE PLATEAU DE REFERENCE (besoin plein 960). Sept largeurs,
# sept verdicts, chacun ecrit en entier — un plan qui rendrait le bon niveau
# en sacrifiant autre chose rougirait ici.
check("bd_plan_1200_et_960_ne_sacrifient_rien",
      d.get("bd_plan_large") == [0, "", 960, True]
      and d.get("bd_plan_juste") == [0, "", 960, True],
      f'{d.get("bd_plan_large")} / {d.get("bd_plan_juste")}')
check("bd_plan_900_ne_perd_que_les_rappels",
      d.get("bd_plan_1") == [1, "hints", 860, True], f'{d.get("bd_plan_1")}')
check("bd_plan_800_perd_aussi_les_libelles_de_coupe",
      d.get("bd_plan_2") == [2, "hints+coupe", 720, True],
      f'{d.get("bd_plan_2")}')
check("bd_plan_700_perd_aussi_le_metering",
      d.get("bd_plan_3") == [3, "hints+coupe+metre", 640, True],
      f'{d.get("bd_plan_3")}')
check("bd_plan_620_perd_aussi_la_duree_totale",
      d.get("bd_plan_4") == [4, "hints+coupe+metre+tctotal", 600, True],
      f'{d.get("bd_plan_4")}')
# QUAND MEME LE DERNIER RANG NE SUFFIT PAS, LA FONCTION LE DIT au lieu de
# promettre. `ok:!1` n'est pas une erreur, c'est un aveu : le bandeau
# debordera, et c'est ecrit noir sur blanc plutot que decouvert a l'ecran.
check("bd_plan_impossible_sacrifie_tout_et_avoue",
      d.get("bd_plan_impossible") == [4, "hints+coupe+metre+tctotal",
                                      600, False],
      f'{d.get("bd_plan_impossible")}')
# LA GARANTIE DU §5.3 (« jamais deux lignes, jamais de défilement »),
# MESUREE : sur 187 largeurs de 0 a 1300, `ok` dit toujours la verite de
# `besoin<=dispo`, et un plan qui ne tient pas a TOUT sacrifie. C'est la
# seule facon de mesurer cette promesse sans navigateur — et c'est pour cela
# que le coeur est pur.
check("bd_la_garantie_du_5_3_tient_sur_187_largeurs",
      d.get("bd_plan_garantie") == [1, 0], f'{d.get("bd_plan_garantie")}')
# MONOTONE ET INCLUSIF : le niveau ne remonte jamais quand la largeur baisse,
# et ce qui est tombe ne se releve pas en chemin — sans quoi la barre
# clignoterait pendant un redimensionnement.
check("bd_le_plan_est_monotone_et_inclusif",
      d.get("bd_plan_monotone") == [1, 1, 4],
      f'{d.get("bd_plan_monotone")}')
# LES RANGS 0 NE TOMBENT JAMAIS (le transport, les sous-titres, le zoom,
# l'onglet), ET LA TABLE DE L'APPELANT N'EST PAS MUTEE.
check("bd_le_rang_0_ne_tombe_jamais_et_la_table_n_est_pas_mutee",
      d.get("bd_plan_rang0") == ["c+b", "abc", "abc"],
      f'{d.get("bd_plan_rang0")}')
check("bd_deux_blocs_de_meme_rang_tombent_dans_l_ordre_de_la_table",
      d.get("bd_plan_egalite") == "z+y", f'{d.get("bd_plan_egalite")}')
check("bd_une_entree_pourrie_ne_leve_ni_ne_rend_nan",
      d.get("bd_plan_pourri") == [0, 0, 0, True, 0, ""],
      f'{d.get("bd_plan_pourri")}')
# LES CONSTANTES DE L'HOTE, ET LEUR FACE DANS LA FEUILLE. `BD_PX_ICONE` dit
# ce que coute un outil de coupe reduit a son glyphe ; la feuille doit poser
# EXACTEMENT ces nombres, sans quoi la constante mentirait sur ce que le
# navigateur dessine et le rang 2 viserait a cote. Controle a DEUX FACES.
_COMPACT = _regle(_MC, '.dzsvm .svm-trans[data-bdoff~="coupe"] .svm-toolchips\n'
                       '  > .svm-toolchip:nth-child(-n+3){')
_GLYPHE = _regle(_MC, '.dzsvm .svm-trans[data-bdoff~="coupe"] .svm-toolchips\n'
                      '  > .svm-toolchip:nth-child(-n+3)::before{')
check("bd_l_icone_de_coupe_coute_21px_dans_la_couche_et_dans_la_feuille",
      d.get("bd_constantes") is not None
      and d["bd_constantes"][0] == 21
      and d["bd_constantes"][1] == 6
      and d["bd_constantes"][2] == 12
      and d["bd_constantes"][3] == 13
      and d["bd_constantes"][4] == "data-bdoff"
      and _COMPACT is not None and "padding:0 4px" in _COMPACT
      and "font-size:0" in _COMPACT
      and _GLYPHE is not None and "width:11px" in _GLYPHE,
      f'constantes={d.get("bd_constantes")} compact={_COMPACT!r} '
      f'glyphe={_GLYPHE!r}')
# LES TROIS GLYPHES DU MODE COMPACT, ET LEURS INFOBULLES. Le §5.3 demande
# « icônes seules AVEC infobulles » et le §2.3 l'interdit sans elles : les
# trois `title` existent DEJA dans le bundle, ecrits par l'amont — c'est
# mesure ici plutot que suppose. LA QUATRIEME CHIP N'EST PAS TOUCHEE : le
# §5.3 protege les sous-titres, et ses deux compteurs seraient illisibles.
_T_COUPE = ('title:"aimanter les bords, la tête et 0 ("',
            'title:"couper le clip sélectionné à la tête ("',
            'title:"refermer les trous — suppression et rognage droit sur V1 ("')
check("bd_les_trois_outils_de_coupe_ont_deja_leur_infobulle",
      all(s.count(nl(_t)) == 1 for _t in _T_COUPE)
      and _sansc(_MC).count("nth-child(-n+3)") == 2
      and _sansc(_MC).count("nth-child(4)") == 2,
      f'infobulles={[s.count(nl(_t)) for _t in _T_COUPE]}')
# `:nth-child(4)` ET PAS `:last-child`, ET C'EST LE PIEGE QU'ON EVITE : la
# chip des sous-titres n'existe que si la piste S1 existe (le bundle rend
# `null` sinon). `:last-child` aurait decore `ripple` — qui n'est pas un bloc
# a part — les jours ou elle manque. La ligne mesure les deux : le selecteur
# retenu, et l'absence de l'autre dans tout le fichier.
check("bd_le_filet_des_sous_titres_ne_se_deplace_pas_quand_la_chip_manque",
      "nth-child(4)" in _sansc(_MC)
      and "last-child" not in _sansc(_MC)
      and nl("if(!subsLayer())return null;") in s,
      "le filet du bloc « sous-titres » suit le dernier enfant")

# ── L'HOTE, MESURE (et non plus seulement decrit) ─────────────────────────
# LE BESOIN PLEIN DU PLATEAU vaut 1298 px, et les trois nombres qui le font
# sont ecrits dans le commentaire de la sonde : 1150 de contenu, 96
# d'intervalles (8 x 12), 52 de filets (4 x 13). LA PREMIERE MESURE NE
# SACRIFIE RIEN a 1400 px de bandeau (1372 disponibles).
# PUIS LE BANDEAU RETRECIT A 1100 (1072 disponibles) : les rappels et les
# libelles de coupe tombent, dans cet ordre.
# PUIS ON REMESURE SANS RIEN CHANGER D'AUTRE — c'est L'IDEMPOTENCE, et c'est
# la propriete qui empeche la barre de clignoter : le bandeau a change (les
# rappels sont masques, les chips reduites), et le besoin PLEIN doit se
# reconstituer a l'identique grace a la memoire des largeurs.
# PUIS IL S'ELARGIT A 1150 : les libelles de coupe REVIENNENT, les rappels
# non. Sans la memoire, le besoin plein serait tombe a 869 et TOUT serait
# revenu — pour un bandeau qui demande 1298 dans 1122. C'est la mutation qui
# fonde cette ligne : en supprimant `mem`, le quatrieme verdict passe de
# « hints » a « » et le bandeau deborde en silence.
check("bd_l_hote_mesure_applique_et_ne_derive_pas",
      d.get("bd_hote") == [1298, "", 1372,
                           1298, "hints+coupe",
                           1298, "hints+coupe",
                           1298, "hints", "hints"],
      f'{d.get("bd_hote")}')
check("bd_les_noeuds_hors_flux_ne_coutent_rien",
      d.get("bd_hors_flux") == [1298, 1298], f'{d.get("bd_hors_flux")}')
# LA SOMME DES BLOCS EST LE BESOIN PLEIN, au pixel : `reste` absorbe tout ce
# qui ne se sacrifie pas. Si elle ne l'etait pas, `dzmBdPlan` retirerait de la
# place qui n'existe pas et s'arreterait trop tot.
check("bd_la_somme_des_blocs_redonne_le_besoin_plein",
      d.get("bd_blocs") is not None
      and d["bd_blocs"][0] == ["hints:212", "coupe:217", "metre:125",
                               "tctotal:40", "reste:704"]
      and d["bd_blocs"][1] == d["bd_blocs"][2] == 1298,
      f'{d.get("bd_blocs")}')
# SANS BANDEAU — l'ecran peut monter avant que la mise en page existe, et un
# objet sans `querySelector` n'est pas un bandeau. `null`, jamais une levee.
check("bd_l_hote_sans_bandeau_rend_null_au_lieu_de_lever",
      d.get("bd_hote_sans_bandeau") == [None, None, None, None],
      f'{d.get("bd_hote_sans_bandeau")}')

# ══ [6-quater] ETAPE 8 DU HANDOFF — CLAVIER, `role="toolbar"`, MOUVEMENT
#    REDUIT (§4.5) ET LE RACCOURCI (§4.1) ═══════════════════════════════════
#
# LE CŒUR DU ROVING EST PUR ET JOUE SOUS NODE : « index courant + direction +
# liste des boutons actifs -> index suivant ». C'est la seule facon de mesurer
# la traversee des groupes sans navigateur. Ce qui reste dehors est nomme en
# fin de section : le focus reel, l'ordre de tabulation vu par le navigateur,
# et ce qu'un lecteur d'ecran annonce.

# ── LE CŒUR, PUR ──────────────────────────────────────────────────────────
check("tb8_le_roving_avance_et_boucle",
      d.get("tb8_rove_avance") == [1, 2, 4, 0], f'{d.get("tb8_rove_avance")}')
check("tb8_le_roving_recule_et_boucle",
      d.get("tb8_rove_recule") == [3, 0, 4], f'{d.get("tb8_rove_recule")}')
# LES ETEINTS SONT SAUTES, DANS LES DEUX SENS. Plateau [actif, x, x, actif, x] :
# depuis 0 en avant -> 3 ; depuis 3 en avant -> 0 (les deux derniers eteints,
# on boucle) ; depuis 0 en arriere -> 3 ; depuis 3 en arriere -> 0.
check("tb8_le_roving_saute_les_boutons_eteints",
      d.get("tb8_rove_saute_eteints") == [3, 0, 3, 0],
      f'{d.get("tb8_rove_saute_eteints")}')
check("tb8_le_roving_avec_un_seul_actif_y_revient",
      d.get("tb8_rove_un_seul") == [2, 2, 2], f'{d.get("tb8_rove_un_seul")}')
# -1 = « aucun `tabindex=0` a poser » : une barre sans rien d'atteignable se
# SAUTE, elle ne piege pas le focus sur un bouton mort. Aucune levee, aucune
# boucle infinie — les cinq plateaux degeneres passent par la meme sortie.
check("tb8_le_roving_sans_actif_rend_moins_un",
      d.get("tb8_rove_rien") == [-1, -1, -1, -1, -1],
      f'{d.get("tb8_rove_rien")}')
# HORS BORNES : on repart du bord AMONT du sens de marche. Les onze cas
# couvrent l'index negatif, l'index trop grand, `NaN`, le non-entier, la
# chaine numerique (ACCEPTEE, c'est le meme index), `undefined` et `null` —
# ces deux derniers DIFFERENT, et c'est epingle : `Number(null)` vaut 0, donc
# `null` designe le bouton 0 et n'est pas hors bornes.
check("tb8_le_roving_hors_bornes_repart_du_bord_amont",
      d.get("tb8_rove_hors_bornes") == [0, 0, 0, 0, 3, 0, 1,
                                        4, 4, 4, 4],
      f'{d.get("tb8_rove_hors_bornes")}')
check("tb8_seule_une_direction_negative_recule",
      d.get("tb8_rove_dir_valeurs") == [4, 1, 1, 1],
      f'{d.get("tb8_rove_dir_valeurs")}')
# LE PARCOURS EST COMPLET ET SANS DOUBLON : six pas rendent les six index.
# C'est ce qui prouve que le pas vaut ±1 — un pas de 2 sur six boutons en
# laisserait trois inatteignables sans qu'aucun autre cas ne le voie.
check("tb8_le_roving_visite_chaque_bouton_une_fois",
      d.get("tb8_rove_parcours") == [1, 2, 3, 4, 5, 0],
      f'{d.get("tb8_rove_parcours")}')
# L'ASSAINISSEMENT DIFFERE DE LA NAVIGATION, et le troisieme element le dit :
# depuis l'index 2 (eteint), `tbRoveSain` rend 1 — le PREMIER actif — la ou
# `tbRove(2,1,…)` rendrait 3. Un point d'entree n'est pas un deplacement.
check("tb8_le_point_d_entree_est_assaini_vers_le_premier_actif",
      d.get("tb8_rove_sain") == [1, 1, 1, 1, 1, 1, 3, -1, -1, -1],
      f'{d.get("tb8_rove_sain")}')
# HORIZONTALE (§4.5) : gauche/droite seulement. Haut/bas restent a l'ecran —
# ce sont ses sauts de coupe, et les voler ici serait un raccourci de plus qui
# ne dit pas son nom. `constructor`, `toString`, `__proto__` : acces GARDE,
# sinon la table heritee aurait rendu une fonction, donc une direction
# « vraie » (meme piege que `dzmTbTouche` a l'etape 5).
check("tb8_seules_les_fleches_horizontales_naviguent",
      d.get("tb8_dir_touches") == [-1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      f'{d.get("tb8_dir_touches")}')
check("tb8_le_nombre_de_boutons_vient_du_plan",
      d.get("tb8_nb_act") == [9, 3, 9, 9], f'{d.get("tb8_nb_act")}')

# ── L'ORDRE PLAT, ET SON ACCORD AVEC LA BARRE PEINTE ──────────────────────
# ONZE ENTREES : les neuf actions puis `⌖` et `×`. Ces deux-la sont TOUJOURS
# atteignables — le §4.2 l'exige pour `⌖` (« il ne doit jamais etre masque »),
# et `×` est la seule facon de replier au clavier.
_A_PLEIN = ",".join(["true"] * 11)
_A_ETEINT = ",".join(["false"] * 9 + ["true", "true"])
check("tb8_l_ordre_plat_compte_neuf_actions_plus_deux_controles",
      d.get("tb8_actifs") is not None
      and d["tb8_actifs"][0] == 11
      and d["tb8_actifs"][1] == _A_PLEIN
      and d["tb8_actifs"][2] == _A_ETEINT
      and d["tb8_actifs"][3] == _A_ETEINT
      and d["tb8_actifs"][4] == _A_ETEINT,
      f'{d.get("tb8_actifs")}')
# LES DEUX COTES S'ACCORDENT, BOUTON PAR BOUTON, SUR TROIS PLATEAUX. Sans cet
# accord, le point d'entree du parcours tomberait sur un bouton `disabled`,
# c'est-a-dire nulle part. MESUREE PAR MUTATION : la version naive de
# `dzmTbActifs` (« entree absente = rien a eteindre = actif ») fait rougir
# les deux derniers plateaux, et elle seule.
check("tb8_les_actifs_et_la_barre_peinte_disent_la_meme_chose",
      d.get("tb8_actifs_accorde_la_barre") == [True, True, True, _A_ETEINT],
      f'{d.get("tb8_actifs_accorde_la_barre")}')

# ── LE `tabindex` ROVING SUR LA BARRE PEINTE ──────────────────────────────
# « Un seul point d'entree dans l'ordre de tabulation » (§4.5), mesure sur les
# ONZE boutons : exactement un `0`, dix `-1`, et le `0` est a l'index demande.
_T0 = ",".join(["0"] + ["-1"] * 10)
check("tb8_un_seul_point_d_entree_et_il_suit_l_index",
      d.get("tb8_tabindex") == [11, _T0, 1, 1, 1, 1, 5, 9, 10],
      f'{d.get("tb8_tabindex")}')
# UN INDEX PERIME NE FAIT PAS DISPARAITRE LE POINT D'ENTREE. Sans hote les
# neuf actions sont eteintes : il tombe sur `⌖` (index 9), et il y a toujours
# EXACTEMENT un `0`. Les trois derniers cas sont l'index trop grand, `NaN` et
# l'absence de propriete.
check("tb8_un_index_perime_retombe_sur_le_premier_actif",
      d.get("tb8_tabindex_assaini") == [9, 9, 0, 0, 0, 1],
      f'{d.get("tb8_tabindex_assaini")}')
# LA CONSIGNE DE L'ETAPE 5, TENUE : la poignee est HORS du groupe. Ses fleches
# deplacent la barre, celles du groupe deplacent le focus — le meme geste ne
# peut pas faire les deux sur le meme objet. Elle ne porte AUCUN `tabIndex`
# (elle garde donc son propre arret de tabulation, ecart declare) et le
# selecteur du groupe ne la nomme pas.
check("tb8_la_poignee_est_hors_du_groupe_roving",
      d.get("tb8_poignee_hors_groupe") == ["dzm-tbgrip", False,
                                           ".dzm-tbb,.dzm-tbwb",
                                           True, True, True],
      f'{d.get("tb8_poignee_hors_groupe")}')
# « LA COULEUR N'EST JAMAIS LE SEUL PORTEUR D'INFORMATION : chaque groupe a
# son en-tete en clair » (§4.5). Il l'avait A L'ŒIL et a l'œil seulement : un
# `<span>` pose au-dessus d'une rangee de boutons n'est RATTACHE a rien, et le
# nom accessible de « video » etait « video », sans rien qui dise de quoi.
# LES LIBELLES NE SONT PAS RECOPIES ICI : la ligne compare le rendu au PLAN,
# qui est lui-meme compare au §2.2 lu dans design.md plus haut — un seul
# endroit ou le texte vit, comme pour les dix traces du §3.
check("tb8_chaque_groupe_est_un_role_group_nomme_par_son_en_tete",
      d.get("tb8_groupes_nommes") is not None
      and len(d["tb8_groupes_nommes"]) == 5
      and all(r == "group" for r, _ in d["tb8_groupes_nommes"])
      and [n for _, n in d["tb8_groupes_nommes"]]
      == d.get("tb8_groupes_le_plan_dit_la_meme_chose")
      # LE SUFFIXE DU GROUPE MOT EN FAIT PARTIE (§2.2, verbatim) : sans lui,
      # « MOT » ne dirait pas qu'il agit sur la selection.
      and "MOT — sélection" in [n for _, n in d["tb8_groupes_nommes"]],
      f'{d.get("tb8_groupes_nommes")}')
# `role="toolbar"`, VERBATIM DU §4.5, avec ses deux attributs. Le dernier
# element est le conjoint qui empeche un `onKeyDown` code en dur : sans
# gestionnaire fourni, la barre n'en pose pas.
check("tb8_la_barre_est_un_role_toolbar_nomme_et_oriente",
      d.get("tb8_role") == ["toolbar", "horizontal", "Outils de création",
                            "function", "undefined"],
      f'{d.get("tb8_role")}')
# LE BOUTON D'ACTION PORTE TROIS ETATS, DONT L'ABSENCE — un appelant qui monte
# un bouton HORS d'une barre roving ne doit pas heriter d'un `-1` qui le
# sortirait du parcours. Le quatrieme cas (`tab:1`, truthy mais pas `true`)
# ne pose rien : le contrat est strict, comme celui de `toggle` et `disabled`.
check("tb8_le_bouton_porte_trois_etats_de_tabindex",
      d.get("tb8_btn_tab") == [0, -1, False, False],
      f'{d.get("tb8_btn_tab")}')

# ── LES TROIS AIDES DE DOM, JOUEES SUR UN FAUX ARBRE ──────────────────────
# `tbBoutons` interroge le DOM avec LE selecteur du groupe et COPIE ce qu'il
# rend : une NodeList vivante changerait sous nos pieds entre la mesure et le
# focus.
check("tb8_les_boutons_sont_lus_par_le_selecteur_du_groupe_et_copies",
      d.get("tb8_boutons") == [[".dzm-tbb,.dzm-tbwb"], 2, True, True],
      f'{d.get("tb8_boutons")}')
# SANS DOM, SANS METHODE, AVEC UNE METHODE QUI LEVE : liste vide, jamais une
# levee. L'ecran peut monter avant que la barre existe.
check("tb8_les_boutons_sans_dom_rendent_une_liste_vide",
      d.get("tb8_boutons_sans_dom") == [0, 0, 0, 0],
      f'{d.get("tb8_boutons_sans_dom")}')
check("tb8_l_index_du_noeud_focalise",
      d.get("tb8_idx") == [0, 2, -1, -1, -1, -1], f'{d.get("tb8_idx")}')
# `tbFocus` REND CE QU'IL A FAIT, et il ne fait rien hors bornes, sur un nœud
# sans `focus`, sur un index qui n'est pas un nombre ou qui n'est pas entier.
# Les deux compteurs finaux sont le conjoint positif : un seul appel a porte.
check("tb8_le_focus_ne_part_que_sur_un_noeud_focalisable",
      d.get("tb8_focus") == [[True, False, False, False, False, False, False],
                             0, 1],
      f'{d.get("tb8_focus")}')

# « RENDRE LE FOCUS A L'ONGLET » (§4.5) SUPPOSE QU'ON L'AVAIT. Echap ne part
# que du dedans, mais LE RACCOURCI REPLIE DEPUIS N'IMPORTE OU — la timeline,
# un en-tete de piste, l'inspecteur. Y deplacer le focus ne serait pas le
# rendre, ce serait le VOLER, et le voler coute cher : un `<button>` focalise
# consomme la barre d'espace, c'est-a-dire la lecture. Le nœud LUI-MEME
# compte pour dedans ; un `contains` absent ou qui leve rend faux.
check("tb8_le_focus_n_est_rendu_que_s_il_etait_dans_la_barre",
      d.get("tb8_dedans") == [True, False, True, False, False, False,
                              False, False],
      f'{d.get("tb8_dedans")}')

# ── LE RACCOURCI, DIT SUR L'ONGLET ────────────────────────────────────────
# La combo n'est pas ecrite dans la couche : elle vient de
# `svmKeyLabel("toolbar")`, donc de la keymap VIVANTE. Un remappage se lit sur
# l'onglet comme il se lit deja sur la chip « lame ». Sans combo : rien
# d'ajoute, jamais une parenthese vide.
check("tb8_la_combo_est_dite_ou_rien_ne_l_est",
      d.get("tb8_combo") == [" Raccourci : O.", " Raccourci : Maj+O.",
                             "", "", "", "", ""],
      f'{d.get("tb8_combo")}')
check("tb8_l_onglet_dit_le_raccourci_et_recoit_sa_reference",
      d.get("tb8_onglet") == [
          "Ouvrir la barre d'outils de création. Raccourci : O.",
          "Replier la barre d'outils sur son onglet. Raccourci : O.",
          "Ouvrir la barre d'outils de création.",
          True],
      f'{d.get("tb8_onglet")}')

# ── LE DOCK : CE QUE NODE NE JOUE PAS, LU DANS LA SOURCE ──────────────────
# C'est le seul morceau a hooks du lot. Meme parade qu'aux etapes 4, 5 et 7 :
# le cœur est mesure pour lui-meme plus haut, mais RIEN ne dirait qu'il est
# APPELE. Chaque jeton est une INSTRUCTION ENTIERE, pas un nom — la mesure de
# l'etape 5 (deux mutants ont survecu a des jetons trop courts) tient encore.
for _tk8 in (
        # ECHAP : replie ET rend le focus a l'onglet (§4.5). Les deux moities
        # dans le meme appel : `replier` fait les deux, et `onClose` la
        # reutilise — le `×` du clavier laissait sinon le focus nulle part.
        'if(e.key==="Escape"){',
        "replier();return}",
        "function replier(){setOpen(dzmTbOpenSet(!1));rendreFocus()}",
        "onClose:replier",
        # ET LA GARDE EST SUR LES DEUX CHEMINS DE REPLI — Echap/`×` par
        # `replier`, le raccourci par son effet. Sans elle, `O` frappe depuis
        # la timeline aurait tire le focus jusqu'a l'onglet.
        "if(dzmTbDedans(bar.current,doc&&doc.activeElement))focusOnglet()}",
        # LES FLECHES : la direction vient du cœur pur, l'index courant du
        # nœud reellement focalise, et on ne navigue pas si les deux
        # longueurs different.
        "var d=dzmTbRoveDir(e.key);",
        "var l=dzmTbBoutons(bar.current),a=dzmTbActifs(items);",
        "if(l.length!==a.length)return;",
        "var i=dzmTbIdx(l,doc&&doc.activeElement);",
        "var j=dzmTbRove(i,d,a);",
        "setRove(j);dzmTbFocus(l,j)}",
        "onBarKey:barKey",
        # LE FOCUS A L'OUVERTURE (§4.1) — sur le GESTE seulement : `vuOpen`
        # garde le montage, sinon la barre (ouverte par defaut depuis
        # l'etape 6) volerait le focus a chaque chargement de l'ecran.
        "if(vuOpen.current===null){vuOpen.current=open;return}",
        "if(open&&!vuOpen.current){",
        "var k=dzmTbRove(-1,1,dzmTbActifs(items));",
        "if(k>=0){setRove(k);dzmTbFocus(dzmTbBoutons(bar.current),k)}}",
        # LE RACCOURCI RECU COMME UNE DEMANDE, et sa garde de montage.
        "var treq=Number(o.toggleReq)||0;",
        "if(treq<=0)return;",
        "var v=!openRef.current;",
        "if(!v)rendreFocus()},[treq]);",
        "openRef.current=open;",
        # L'ONGLET RECOIT SA REFERENCE ET LA COMBO VIVANTE.
        "tabRef:onglet,keyLbl:o.keyLbl",
        "rove:rove,onBarKey:barKey",
):
    check("tb8_dock_" + re.sub(r"[^a-z0-9]+", "_", _tk8.lower()).strip("_")[:58],
          _tk8 in _DOCK, f"absent du Dock : {_tk8!r}")
# LES DEUX BRANCHES ARRETENT CHACUNE LA PROPAGATION, ET C'EST UN COMPTE, PAS
# UNE SOUS-CHAINE. MESUREE PAR MUTATION : retirer le `stopPropagation` de la
# SEULE branche Echap laissait la ligne verte, parce que la meme instruction
# vit dans la branche des fleches (faute n°2, forme « sous-chaine que la
# chaine ecrit ailleurs »). Ce que chacune empeche est different :
#   • Echap — le gestionnaire global de l'ecran rendrait AUSSI les fleches
#     d'un overlay selectionne a la tete de lecture, deux gestes pour une
#     frappe ;
#   • les fleches — elles deplaceraient AUSSI la tete de lecture
#     (`step_back` / `step_fwd`), ce que la poignee evite deja pour les
#     siennes depuis l'etape 5, et par la meme mesure.
_i_bk = _DOCK.find("  function barKey(e){")
_j_bk = _DOCK.find("\n  function ", _i_bk + 10) if _i_bk >= 0 else -1
_BARKEY = _DOCK[_i_bk:_j_bk] if 0 <= _i_bk < _j_bk else "BARKEY-INTROUVABLE"
# L'ASYMETRIE DES DEUX BRANCHES, ET C'EST UNE MESURE QUI A CORRIGE LA
# PREMIERE VERSION DE CE BLOC. `barKey` porte DEUX `preventDefault` et UN
# SEUL `stopPropagation`, et le seul est celui des FLECHES :
#   • ECHAP LAISSE MONTER — le bouton `projets` de la barre ouvre le popover
#     des projets SANS deplacer le focus, qui reste donc DANS la barre ; ce
#     popover ferme sur Echap par un ecouteur `window` de phase MONTANTE
#     (montage.js, effet `[op]`), donc sous nous. L'arreter etouffait cet
#     ecouteur : une frappe repliait la barre et laissait le popover ouvert
#     derriere, sans clavier pour le fermer. C'est aussi la regle que
#     `SVM_KEYS_INFO` ecrit — « Echap : fermer / annuler, touche fixe » ;
#   • LES FLECHES, ELLES, SONT ARRETEES — sans quoi elles deplaceraient AUSSI
#     la tete de lecture (`step_back` / `step_fwd`).
# LE COMPTE EST CELUI DE `barKey` SEUL : le clavier de la POIGNEE (`clavier`,
# etape 5) porte la meme paire, et compter sur tout le Dock rend DEUX — donc
# vert apres avoir retire celui des fleches (faute n°2, forme « sous-chaine
# que la chaine ecrit ailleurs » — mesuree, ce mutant a survecu a la premiere
# passe). LE CONJOINT DE POSITION est ce qui distingue les deux branches :
# le `stopPropagation` suit immediatement la resolution de direction.
check("tb8_dock_echap_laisse_monter_et_les_fleches_sont_arretees",
      300 < len(_BARKEY) < 1600
      and _BARKEY.count('if(typeof e.stopPropagation==="function")'
                        'e.stopPropagation();') == 1
      and _BARKEY.count('if(typeof e.preventDefault==="function")'
                        'e.preventDefault();') == 2
      and 0 < _BARKEY.find("var d=dzmTbRoveDir(e.key);")
      < _BARKEY.find('if(typeof e.stopPropagation==="function")'
                     "e.stopPropagation();")
      and _DOCK.count('if(typeof e.stopPropagation==="function")'
                      'e.stopPropagation();') == 2,
      f'barKey={len(_BARKEY)} o '
      f'stop={_BARKEY.count("e.stopPropagation();")} '
      f'prevent={_BARKEY.count("e.preventDefault();")} '
      f'dock={_DOCK.count("e.stopPropagation();")}')

# ── LE RACCOURCI, INSCRIT DANS LE MECANISME EXISTANT (§4.1) ───────────────
# LE POINT DUR DE CETTE ETAPE. Le §4.1 demande `T` ; `T` EST DEJA PRIS par
# `narration` dans le bundle livre. La touche retenue est `O` — l'initiale du
# libelle VERBATIM de l'onglet — et elle est declaree dans `SVM_ACTIONS`,
# c'est-a-dire REMAPPABLE (`dz_svm_keymap`) et LISTEE dans le panneau « ? ».
# Un ecouteur invente a cote aurait donne un raccourci invisible du panneau,
# donc introuvable, et non remappable.
_ACTS = re.search(r"var SVM_ACTIONS=\[(.*?)\];\r?\nvar SVM_ACTION_BY_ID",
                  s, re.S)
_ACTS = _ACTS.group(1) if _ACTS else ""
_COMBOS = re.findall(
    r'\{id:"([a-z_0-9]+)",sec:"([^"]+)",lbl:"[^"]*",combo:"([^"]+)"\}', _ACTS)
_BY_COMBO = {}
for _a, _sec, _c in _COMBOS:
    _BY_COMBO.setdefault(_c, []).append(_a)
# LE CONFLIT EST MESURE, PAS SUPPOSE : `T` appartient a `narration`, et il ne
# lui est PAS repris. Conjoint positif : la table est bien celle de l'ecran
# (elle porte les trente-trois actions, dont la nouvelle).
check("tb8_le_T_du_handoff_appartient_deja_a_la_narration",
      len(_COMBOS) == 33 and _BY_COMBO.get("T") == ["narration"],
      f"actions={len(_COMBOS)} T={_BY_COMBO.get('T')}")
# UNE COMBO PAR ACTION, ET AUCUNE EN DOUBLE : la nouvelle n'a rien vole.
# `svmKmMerge` resoudrait une collision en silence (retour au defaut) — c'est
# ici qu'elle doit se voir.
check("tb8_aucune_combo_par_defaut_n_est_prise_deux_fois",
      len(_COMBOS) == len(_BY_COMBO)
      and all(len(v) == 1 for v in _BY_COMBO.values()),
      f"{[k for k, v in _BY_COMBO.items() if len(v) > 1]}")
check("tb8_l_action_de_la_barre_est_dans_la_table_des_raccourcis",
      _BY_COMBO.get("O") == ["toolbar"]
      and s.count(nl(P.R_M20A.split("\n")[0])) == 1,
      f"O={_BY_COMBO.get('O')}")
# `O` EST LIBRE DES DEUX COTES : aucune autre action ne la porte (ci-dessus),
# et AUCUNE comparaison du bundle ne la lit — les seules occurrences de ces
# motifs sont `subsKeyOf` et `arm==="o"+p.id`, dont aucune n'est un raccourci.
check("tb8_la_touche_O_n_est_lue_par_aucun_autre_ecouteur",
      s.count('KeyO') == 5 and s.count('==="o"') == 1
      and s.count('==="O"') == 0 and s.count('key==="o"') == 0
      and s.count('subsKeyOf') == 5 and s.count('arm==="o"+p.id') == 1,
      f'KeyO={s.count("KeyO")} o={s.count("===" + chr(34) + "o" + chr(34))} '
      f'subsKeyOf={s.count("subsKeyOf")}')
# ET ELLE N'EST PAS RESERVEE : `svmComboReserved` refuse les touches du
# navigateur, les F<n>, Echap, Tab et Entree. « O » n'est dans aucune liste.
check("tb8_la_touche_O_n_est_pas_reservee_par_le_navigateur",
      s.count(nl('var SVM_COMBO_RESERVED={"Ctrl+R":1,')) == 1
      and '"O":1' not in s.split("function svmComboReserved")[0]
      .split("var SVM_COMBO_RESERVED=")[-1],
      "O figure dans SVM_COMBO_RESERVED")
# LA BRANCHE DE DISPATCH EXISTE : une action declaree sans branche serait un
# raccourci MORT, liste dans le panneau et sans effet. Elle DEMANDE la
# bascule (un compteur), elle ne pilote pas l'etat — qui vit dans le Dock,
# qui le persiste. `dzTbReq` est declare une fois et passe une fois.
check("tb8_le_raccourci_a_sa_branche_et_elle_demande_la_bascule",
      s.count(nl('if(id==="toolbar"){'
                 'setDzTbReq(function(n){return n+1});return}')) == 1
      and s.count(nl("var stDzTb=x.useState(0),dzTbReq=stDzTb[0],"
                     "setDzTbReq=stDzTb[1];")) == 1
      and s.count("toggleReq:dzTbReq,") == 1
      and s.count('keyLbl:svmKeyLabel("toolbar")') == 1
      and "toggleReq:dzTbReq," in P.R_M19,
      f'branche={s.count(nl(chr(34)))} '
      f'decl={s.count("var stDzTb=x.useState(0)")} '
      f'prop={s.count("toggleReq:dzTbReq,")}')
# LE PANNEAU « ? » LE LISTE : il boucle sur `SVM_ACTIONS` sans autre filtre
# que `sounds_drawer`. Cette ligne mesure les DEUX faces — la boucle est
# toujours celle-la (une seule occurrence dans le bundle), et la seule
# exception nommee est bien `sounds_drawer`.
check("tb8_le_panneau_des_raccourcis_liste_la_nouvelle_action",
      s.count(nl("SVM_ACTIONS.forEach(function(a){\r\n"
                 '      if(a.id==="sounds_drawer"&&!hasSfx)return;\r\n'
                 "      rows.push({act:a})});")) == 1,
      "la boucle de kbPanel a change de forme")

# ── LE NOM ACCESSIBLE DES TROIS CHIPS DE COUPE (§4.5) ─────────────────────
# « La couleur n'est jamais le seul porteur d'information » — et la FORME non
# plus. L'etape 6 passe ces trois chips en GLYPHE SEUL sous largeur reduite ;
# l'etape 8 leur donne un `aria-label` explicite, pour que leur nom ne
# dependre ni du contenu genere par `::before` ni du moteur.
# LES DEUX FACES : le `aria-label` dans le bundle, ET la regle de degradation
# dans la feuille — sans elle, ces `aria-label` repareraient un mal absent.
for _lbl8, _ct8 in (('"aria-label":"aimanter",', 1),
                    ('"aria-label":"lame · "+svmKeyLabel("blade"),', 1),
                    ('"aria-label":"ripple",', 1)):
    check("tb8_chip_" + re.sub(r"[^a-z]+", "_", _lbl8.lower()).strip("_")[:40],
          s.count(nl(_lbl8)) == _ct8, f"{_lbl8!r} x{s.count(nl(_lbl8))}")
check("tb8_les_trois_chips_degradees_gardent_un_nom_et_une_infobulle",
      _MC.count('[data-bdoff~="coupe"] .svm-toolchips') == 5
      and "font-size:0" in _MC
      and _MC.count(".svm-toolchip:nth-child(-n+3)") == 2
      # QUATRE CHIPS DANS LE CONTENEUR, TROIS QUI SE DEGRADENT : la
      # quatrieme est celle des sous-titres, que le §5.3 protege — ses deux
      # compteurs seraient illisibles reduits a un glyphe, et elle n'a donc
      # pas besoin d'un nom explicite. C'est `:nth-child(-n+3)` qui trace la
      # frontiere, des deux cotes.
      and s.count('className:"svm-toolchip"') == 4
      # LE `title` NE BOUGE PAS : il reste la description, et c'est lui que
      # l'infobulle du mode compact affiche (§2.3).
      and s.count(nl('title:"aimanter les bords, la tête et 0 ("')) == 1
      and s.count(nl('title:"couper le clip sélectionné à la tête ("')) == 1
      and s.count(nl('title:"refermer les trous — suppression et rognage '
                     'droit sur V1 ("')) == 1,
      f'coupe={_MC.count(chr(91) + "data-bdoff~=" + chr(34) + "coupe" + chr(34) + "] .svm-toolchips")} '
      f'chips={s.count(chr(34) + "svm-toolchip" + chr(34))}')

# ── MOUVEMENT REDUIT (§4.5) : LES TROIS EXIGENCES, ET QUI LES TIENT ───────
# 1. « durees a 1 ms » et 2. « aimantation immediate » : SERVIES PAR UNE REGLE
#    QUI EXISTAIT DEJA — son-vfx-montage.css l.1028, `.dzsvm *` sous
#    `prefers-reduced-motion:reduce`, qui ramene `animation-duration` et
#    `transition-duration` a .001 ms. La barre vit dans `.dzsvm`, et TOUT son
#    mouvement est en CSS : l'ouverture et le repli (`opacity`/`transform` sur
#    `--dur-bar-open`) et l'aimantation (`translate` sur `--dur-bar-snap`).
#    AUCUN MINUTEUR, aucune animation pilotee en JS — c'est ce que la
#    troisieme moitie de cette ligne mesure, et c'est ce qui rend la premiere
#    vraie. `setTimeout` survit dans `dzmTbFrame`, qui est un REPLI de
#    `requestAnimationFrame` a delai zero : il ne dessine pas, il attend une
#    frame.
# 3. « aucun enfoncement » : LA SEULE QUI DEMANDAIT UNE REGLE NEUVE, posee a
#    l'etape 3 — le coupe-circuit borne les DUREES, il ne RETIRE pas une
#    transformation, qui resterait appliquee en un saut tant que le doigt
#    appuie.
# `_lire` PLUTOT QUE `read_text` : une feuille absente ou illisible doit
# faire ROUGIR cette ligne, pas TUER le banc (faute n°6). `_lire` rend un
# temoin distinguable, jamais "".
_SVMCSS = _lire(ROOT / "frontend" / "dist" / "shared" / "son-vfx-montage.css")
_COUPE = _regle(_SVMCSS, ".dzsvm *, .dzsvm *::before, .dzsvm *::after{")
check("tb8_le_coupe_circuit_du_mouvement_reduit_vient_de_son_vfx_montage",
      _COUPE is not None
      and "transition-duration:.001ms!important" in _COUPE
      and "animation-duration:.001ms!important" in _COUPE
      and "@media (prefers-reduced-motion:reduce){" in _SVMCSS
      # ET IL N'EST PAS DANS LA FEUILLE DE TOKENS, que dist/index.html NE
      # CHARGE PAS : c'est la rectification d'attribution de l'etape 5, et
      # la feuille la PORTE — sans ce conjoint, retourner la phrase du
      # commentaire (« vient de » au lieu de « ne vient PAS de ») laissait
      # le banc entierement vert.
      and "deepotus.tokens.css" not in _HTML
      and "son-vfx-montage.css" in _HTML
      and _MC.count("ne vient PAS de shared/deepotus.tokens.css") == 2,
      f"coupe={_COUPE!r} "
      f'rectif={_MC.count("ne vient PAS de shared/deepotus.tokens.css")}')
check("tb8_l_enfoncement_est_retire_et_le_delai_du_repli_aussi",
      _regle(_MC, ".dzsvm .dzm-tbb:active{transform:none") is not None
      and _regle(_MC, ".dzsvm .dzm-tbar[data-off]{transition-delay:0s")
      is not None
      and _MC.count("@media (prefers-reduced-motion:reduce){") == 2
      # ET L'ATTRIBUTION EST CORRIGEE DANS LES DEUX COMMENTAIRES : c'est un
      # commentaire qui mentait, la meme famille de faute que la chaine a
      # deja payee deux fois. DEUX, un par bloc de mouvement reduit —
      # l'enfoncement (etape 3, corrige ici) et le delai du repli (etape 8).
      # Le compte, pas la sous-chaine : corriger l'un et laisser l'autre
      # aurait laisse la ligne verte.
      and _MC.count("son-vfx-montage.css l.1028") == 2
      and "de la feuille de\n   tokens" not in _MC,
      f'media={_MC.count("@media (prefers-reduced-motion:reduce){")} '
      f'attribution={_MC.count("son-vfx-montage.css l.1028")}')
# LE MOUVEMENT DE LA BARRE EST ENTIEREMENT EN CSS — c'est ce qui rend le
# coupe-circuit suffisant pour les deux premieres exigences. Conjoint positif
# d'abord : le bloc existe et il est gros.
_CODE_TB8 = _code(_SRC_TB)
_i_frm = _CODE_TB8.find("function dzmTbFrame(")
_j_frm = _CODE_TB8.find("\nfunction ", _i_frm + 10) if _i_frm >= 0 else -1
_HORS_FRM = ((_CODE_TB8[:_i_frm] + _CODE_TB8[_j_frm:])
             if 0 <= _i_frm < _j_frm else "BLOC-INTROUVABLE")
check("tb8_aucun_mouvement_de_la_barre_n_est_pilote_en_javascript",
      len(_CODE_TB8) > 8000 and len(_HORS_FRM) > 8000
      # LES SEULS `requestAnimationFrame` / `setTimeout` DU BLOC vivent dans
      # `dzmTbFrame`, dont le travail est d'ATTENDRE UNE FRAME pour rendre la
      # main aux transitions (§4.4) : il ne dessine pas, il ne compte pas de
      # pas. Partout ailleurs dans le bloc : zero.
      and _CODE_TB8.count("function dzmTbFrame(") == 1
      and "requestAnimationFrame" not in _HORS_FRM
      and "setTimeout" not in _HORS_FRM
      and "setInterval" not in _CODE_TB8
      and ".animate(" not in _code(src)
      # ET LA FEUILLE N'ANIME RIEN NON PLUS : aucune `@keyframes`, donc tout
      # le mouvement de la barre est une TRANSITION — exactement ce que le
      # coupe-circuit borne.
      and "@keyframes" not in _MC,
      f"bloc={len(_CODE_TB8)} o hors_frame={len(_HORS_FRM)} o")

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
