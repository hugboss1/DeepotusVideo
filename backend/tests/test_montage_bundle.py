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

Run : & $PY tests/test_montage_bundle.py   (depuis backend/)"""
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
r = subprocess.run(["node", "--check", str(BUNDLE)], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
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
    r = subprocess.run(["node", "--input-type=module", "--check"], stdin=_fh,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
check("node_check_module", r.returncode == 0, (r.stderr or "")[-300:])

print("\n[3] le cœur de la couche, EXÉCUTÉ sous node")
shim = pathlib.Path(TMP) / "shim.js"
# La table SVM_TRACKS du bundle est EXTRAITE et exécutée à côté de la couche.
# DZM_DEFAULT_TRACKS la recopie (nom, type, hauteur, couleur, rang de mixage)
# en y ajoutant kind/bus/loop : sans cette comparaison, les deux tables
# pourraient diverger et l'écran des six pistes historiques changerait
# d'aspect sans que rien ne le dise.
_i = s.index(nl("var SVM_TRACKS=["))
_j = s.index(nl("}];"), _i) + len(nl("}];"))
SVM_SRC = s[_i:_j]
if SVM_SRC.count("{id:") != 6:
    check("bundle_svm_tracks_extraite", False, f"{SVM_SRC.count('{id:')} entrées")
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
console.log(JSON.stringify(out));
"""
# "use strict" en PROLOGUE du shim : concatene, celui de montage.js n'est
# plus une directive mais une expression morte, et le cœur tournerait
# RELACHE ici alors que le navigateur l'execute strict (module). Une
# affectation a une variable non declaree passerait au banc et leverait a
# l'ecran.
shim.write_text('"use strict";\n' + "var window={};var SVM_TRACK_BUS={};\n"
                + SVM_SRC.replace("\r\n", "\n") + "\n" + src + "\n" + probe,
                encoding="utf-8")
r = subprocess.run(["node", str(shim)], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
if r.returncode != 0:
    check("js_shim_execute", False, (r.stderr or "")[-500:])
    d = {}
else:
    check("js_shim_execute", True)
    d = json.loads(r.stdout.strip().splitlines()[-1])

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
check("js_from_sans_v1_refuse", d.get("from_sans_v1") is None,
      str(d.get("from_sans_v1")))
check("js_from_vide_refuse", d.get("from_vide") is None, str(d.get("from_vide")))
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

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
