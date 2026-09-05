# -*- coding: utf-8 -*-
"""P1 — MIROIR DU BUNDLE LIVRE. On lit le fichier que l'application charge
vraiment (frontend/dist/assets/index-BEOJX8L5.js), pas la source du patcher :
c'est la seule facon de voir qu'une section a ete effacee par un maillon
amont relance seul — le mode de panne qui a deja coute vingt-deux correctifs
a ce depot.

Trois familles de mesures :
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

Run : & $PY tests/test_montage_bundle.py   (depuis backend/)

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
import importlib.util, json, os, pathlib, re, shutil, subprocess, sys, tempfile
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

P = load("patch_bundle_montage", PATCHER)
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
check("P10_aucune_entree_d_historique_de_plus",
      "pushHistory" not in P.R_M17A
      and P.R_M17B.count("pushHistory();") == 1
      and P.R_M17F.count("pushHistory(h0)") == 1
      and "pushHistory" not in P.R_M17G,
      f"a={'pushHistory' in P.R_M17A} b={P.R_M17B.count('pushHistory();')} "
      f"f={P.R_M17F.count('pushHistory(h0)')} g={'pushHistory' in P.R_M17G}")
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

# La ligne qui dit que le banc a ROUGI plutot que MEURE : aucun appel garde
# n'a pose de temoin. Une panne de node fait rougir CETTE ligne EN PLUS de
# celles qu'elle emporte — et le banc va jusqu'a imprimer son compte.
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

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

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
