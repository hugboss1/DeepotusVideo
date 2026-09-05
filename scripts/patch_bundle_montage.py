# -*- coding: utf-8 -*-
# scripts/patch_bundle_montage.py
"""Patcher assert-gardé : PISTES DYNAMIQUES (P1) du Montage.

Ce que le patch fait, en une phrase : la couche `window.DzTracks`, injectée
EN QUEUE après `subs`, remplace la table figée SVM_TRACKS par un état du
projet — les pistes s'ajoutent, se retirent, se réordonnent, et leur ORDRE
décide de la composition au rendu (montage_service._tracks_meta, champ
`layer`).

BASELINE : bundle POST-patch subs (dernier patch en date de la chaîne bundle).
Backup dédié : .js.bak_montage (état juste avant CE patch).
Position dans la chaîne : EN QUEUE, après `subs`.

AVERTISSEMENT DE CHAÎNE — lire avant de toucher quoi que ce soit, il n'est pas
recopié pour la forme. Une passe qualité a déjà effacé neuf éditions du rack
VFX parce que ses sections vivaient À L'INTÉRIEUR d'un bloc injecté en amont
et qu'un patcher amont a été relancé seul. MESURÉ LE 03/09/2026 SUR CETTE
COPIE : le bloc `sonvfx` du bundle contient AUJOURD'HUI les remplacements
V3/V4/V6/V8/V9 de patch_bundle_vfxrack.py et S3…S17 de patch_bundle_subs.py —
vingt sections. Relancer patch_bundle_sonvfx.py réécrirait ce bloc EN PLACE
depuis sa source et les effacerait toutes, sans un mot, et RIEN ne peut les
rejouer ici : ni .bak_vfxrack ni .bak_subs n'existent dans cette copie (ils
sont gitignorés) et l'ancre V10 de vfxrack est déjà consommée. D'où ce
patcher : tag NEUF (`montage`), .bak dédié, EN QUEUE, et pas une seule
section posée à l'intérieur d'un bloc amont. Ne JAMAIS relancer un patcher
amont seul — `python scripts/repatch_all.py --from <tag>` rejoue la chaîne,
et `--list` la montre.

Sections :
  M1  injecte frontend/patches/montage.js (window.DzTracks) juste après le
      bloc subs — même scope module, alias r/x du bundle disponibles ;
  M2  lie /shared/montage.css dans dist/index.html (idempotent) ;
  M3  la timeline lit svmTracksOf(proj) au lieu de la constante SVM_TRACKS ;
  M4  svmApplyProject resynchronise SVM_TRACK_BUS sur les pistes restaurées ;
  M4b svmTracksSet — le POINT D'ÉCRITURE UNIQUE de proj.tracks (historique,
      bus, état, « NON ENREGISTRÉ ») ; sans lui chaque appelant réécrirait sa
      propre version de la même séquence ;
  M5  payload de rendu : clé `tracks` (le backend y lit l'ordre) ;
  M6  autosave : la même clé, pour que l'ordre survive au rechargement ;
  M7  restauration : proj.tracks reconstruit depuis la sauvegarde serveur ;
  M8  barre de transport : « + vidéo » / « + audio » ;
  M9a/M9b en-tête de piste : poignée de glisser-déposer et ▲ ▼ ×, posés en
      SURIMPRESSION (l'en-tête fait 88 × 40–54 px et il est plein — mesuré,
      voir montage.css) ;
  M10 (P2) chip « mot : couleur / rebond / glow » + bouton « emoji », posés
      DANS le remplacement de M8 (l'ancre A_M8 est déjà consommée, et la
      barre d'outils n'offre pas de seconde ancre unique).
  M11 (P3) l'ÉTAT du panneau « Texte » (`dzTextOn`), déclaré dans le corps du
      composant, et son bouton de barre — lui aussi DANS le remplacement de
      M8, pour la même raison qu'en M10 ;
  M12 (P3) le panneau « Texte » lui-même et la COUPE PAR PLAGE
      (`DzTracks.rippleCut`), posés dans la colonne d'inspection : mesuré, le
      bundle n'offre pas l'ancre `subsDrawer()` de la zone des tiroirs que le
      plan visait — voir le commentaire de A_M12.
  M13 (P4) le bouton « étalonnage → tous les plans <PISTE> », posé JUSTE SOUS
      la pile d'effets de l'inspecteur — pas sur l'ancre `transInspector(),`
      du plan (libre, mais à un écran de la pile qu'il copie) ; voir A_M13.
      La piste visée est celle du PLAN SÉLECTIONNÉ : mesuré, une version qui
      codait « v1 » en dur écrasait deux plans V1 quand un plan V2 étalonné
      était sélectionné. Voir le commentaire de dzmGradeAllBtn.
  M14 (P5) le popover « projets » (lister, enregistrer sous, ouvrir,
      dupliquer, renommer, supprimer), posé lui aussi DANS le remplacement de
      M8 — même raison qu'en M10 et M11b. M6 et M7 y gagnent la clé
      `project_id`, qui relie le brouillon courant à son projet.
  M16 (P9) « Bibliothèque… », et la remise qui se perdait — quatre sections
      plus un repli :
        M16-lib  le bouton « Bibliothèque… » de la barre de transport, posé
                 DANS le remplacement de M8 (A_M8 déjà consommée) ; il ouvre
                 `openPicker` sur la piste vidéo RÉSOLUE ;
        M16ref   `dzTracksRef` — les pistes du projet relues à chaque rendu,
                 parce que le greffon amont appelle l'addAsset du PREMIER ;
        M16a     `addAsset` pose sur une piste QUI EXISTE (fin de
                 `trId||"v2"`) et attend que la timeline soit chargée ;
        M16b     la note dit sur quelle piste le clip a atterri, et pourquoi ;
        M16c     le sélecteur « Rendus vidéo » applique LA règle du rendu
                 (GET /api/montage/media-rules → `_VIDEO_EXTS`), jamais une
                 copie JavaScript ;
        M16d     `v1_non_video` enfin LU : chip « pas une vidéo » cliquable
                 sur les clips V1 dont l'extension n'est pas vidéo — MESURÉ,
                 le rendu n'en refuse qu'une PARTIE : une planche PNG passe
                 le pré-vol (200) et se rend en carton fixe, un maillage
                 `.glb` est refusé (400) ; M7 y gagne la clé `v1NonVideo`,
                 qui porte le champ jusqu'à la timeline.
      Les libellés « + vidéo » / « + audio » deviennent « + piste vidéo » /
      « + piste audio » — édition de `DzmTrackAdd` DANS LA COUCHE, pas une
      section de plus.
  M15 / M16src (P6) REMPLACER LA SOURCE d'un plan sans perdre ses bornes, ses
      effets ni sa transition :
        M4b y gagne `dzmReplaceRef` (le plan visé, {id, tr, label}) ET son
                 DÉSARMEMENT — un effet accroché à l'état du sélecteur
                 d'assets, sans quoi un sélecteur fermé sans choisir laissait
                 le mode armé pour le clip suivant — plus `dzmArm`, le
                 MIROIR D'AFFICHAGE de cette ref (une ref ne re-rend pas ;
                 la ref reste la seule autorité que lit `addAsset`) ;
        M15      le mode remplacement en TÊTE du poseur de clips, avant toute
                 résolution de piste (un remplacement garde celle du plan),
                 avec ses TROIS refus posés avant l'instantané : plan
                 disparu, GENRE incompatible, piste verrouillée. Le refus de
                 genre ferme le seul chemin non assumable du court-circuit —
                 le tiroir Sons, dont l'état est indépendant du sélecteur —
                 et sa section dit ce que le mode prend et ce qu'il refuse ;
        M15b     le SÉLECTEUR DIT QU'IL EST ARMÉ : titre et note
                 conditionnels, en aval d'`ovPicker` (qui vit dans le
                 greffon amont, hors d'atteinte). Sans lui le panneau
                 promettait « Ajouter sur la piste V1 » et « Posé à la tête
                 de lecture » pendant qu'il remplaçait ;
        M16src   les deux boutons de l'inspecteur — « Remplacer la source… »
                 et « Revenir à la version précédente », le second GARDÉ PAR
                 LE VERROU DE PISTE comme le premier (il réécrit `end`, donc
                 le bord droit du clip) — plus le rappel « version plus
                 récente », qui interroge GET /api/montage/newer
                 (rapprochement PAR LE TITRE, dit heuristique dans la
                 réponse comme à l'écran ; la ligne porte donc la DATE et la
                 DURÉE, seuls discriminants entre des candidats qui
                 partagent leur titre par construction).
      Le CŒUR est pur et vit dans la couche (`DzTracks.replaceSrc` /
      `revertSrc`) ; backend/tests/test_montage_remplacer.py l'exécute sous
      node et mesure la route.

Mécanique identique à patch_bundle_subs.py : restauration du .bak dédié puis
ré-application, chaque ancre devant apparaître EXACTEMENT une fois, sinon
abandon sans rien écrire. Le miroir du résultat est
backend/tests/test_montage_bundle.py (comptes dans le bundle livré + le cœur
JS exécuté sous node).

Run :
    python scripts/patch_bundle_montage.py              # dépôt
    python scripts/patch_bundle_montage.py --root <dir> # app installée
    python scripts/patch_bundle_montage.py --check      # n'écrit rien
    python scripts/patch_bundle_montage.py --strip      # retire le patch

Compatible scripts/repatch_all.py : `--force-unchained` est accepté et ignoré.
"""
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
REL_HTML = pathlib.Path("frontend/dist/index.html")
PATCH_SRC = REPO / "frontend" / "patches" / "montage.js"
TAG = "montage"

BEGIN = "/*__DZ_MONTAGE_BEGIN__*/"
END = "/*__DZ_MONTAGE_END__*/"
ANCHOR_INJECT = "/*__DZ_SUBS_END__*/"

CSS_ANCHOR = '<link rel="stylesheet" href="/shared/subs.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/montage.css">'


# ── M3 : les pistes viennent du PROJET, plus de la constante ────────────────
A_M3 = "          SVM_TRACKS.map(function(tr){"
R_M3 = "          svmTracksOf(proj).map(function(tr){"

# ── M4 : bus resynchronisé à l'application d'un projet ──────────────────────
# SVM_TRACK_BUS est lu à neuf endroits du bloc sonvfx ; la couche le MUTE en
# place (voir montage.js) — une seule ancre au lieu de neuf.
A_M4 = "    setProj(np);"
R_M4 = "    svmTrackBusSync(np.tracks);\n    setProj(np);"

# ── M4b : le point d'écriture UNIQUE de proj.tracks ─────────────────────────
A_M4b = "  function svmApplyProject(d){"
R_M4b = ("  /* P1 — TOUTE écriture de proj.tracks passe ici : historique poussé,\n"
         "     SVM_TRACK_BUS resynchronisé, projet réécrit, « NON ENREGISTRÉ »\n"
         "     allumé. Deux appelants (la barre d'outils et les en-têtes de\n"
         "     piste) ; sans ce point unique, chacun aurait sa propre version de\n"
         "     la séquence et l'un des deux finirait par en oublier un morceau.\n"
         "     RESTE CONNU : l'historique ne mémorise que {clips, mixDb} — un\n"
         "     annuler après un retrait de piste ramène les CLIPS, pas la piste.\n"
         "     Ils redeviennent visibles dès qu'on rajoute une piste du même\n"
         "     genre : l'identifiant repris est le plus petit libre, donc le\n"
         "     leur. C'est dit dans la note du bouton, ce n'est pas silencieux. */\n"
         "  /* P6 — L'ARMEMENT DU MODE REMPLACEMENT, et son DÉSARMEMENT.\n"
         "     `{id, tr}` du plan dont on va échanger la source ; le prochain\n"
         "     asset choisi remplacera au lieu d'ajouter. Une REF et non un\n"
         "     état : le sélecteur d'assets appelle le poseur de clips depuis\n"
         "     une fermeture, et un état re-rendu n'y serait pas lu.\n"
         "     L'effet ci-dessous est la moitié qui manquait au plan : sans\n"
         "     lui, une armement suivi d'un sélecteur FERMÉ sans choisir — ou\n"
         "     rouvert sur une AUTRE piste — laissait le mode armé, et le clip\n"
         "     suivant venait écraser la source d'un plan que l'utilisateur ne\n"
         "     regardait plus. Le désarmement suit l'état du sélecteur\n"
         "     lui-même (`ovPick`), pas une copie de ses règles.\n"
         "     `dzmArm` est le MIROIR D'AFFICHAGE de cette ref, et rien de\n"
         "     plus : la ref reste la seule autorité que lit `addAsset`.\n"
         "     Il existe parce qu'une ref ne re-rend pas, et que le\n"
         "     sélecteur doit DIRE qu'il est armé au moment où il l'est —\n"
         "     y compris quand il était DÉJÀ ouvert sur la piste du plan et\n"
         "     que M16src ne le rouvre donc pas (le rouvrir le refermerait).\n"
         "     Un état SEUL ne suffirait pas : le rappel « version plus\n"
         "     récente » arme puis appelle `addAsset` dans le MÊME\n"
         "     gestionnaire, et un état posé là n'y serait pas relu. */\n"
         "  var dzmReplaceRef=x.useRef(null);\n"
         "  var stDZA=x.useState(null),dzmArm=stDZA[0],setDzmArm=stDZA[1];\n"
         "  x.useEffect(function(){var rp=dzmReplaceRef.current;\n"
         "    if(rp&&ovPick!==rp.tr){dzmReplaceRef.current=null;\n"
         "      setDzmArm(null)}},[ovPick]);\n"
         "  function svmTracksSet(ts){pushHistory();svmTrackBusSync(ts);"
         "setProj(function(p){return Object.assign({},p,{tracks:ts})});setDirty(!0)}\n"
         "  function svmApplyProject(d){")

# ── M5 : payload de rendu ───────────────────────────────────────────────────
A_M5 = "      clips:clips.filter(function(c){return c.src}).map(function(c){"
R_M5 = ("      /* P1 — l'ORDRE des pistes, du haut vers le bas : c'est lui que\n"
        "         montage_service._tracks_meta traduit en rang de composition\n"
        "         (`layer`) et en bus de mixage. Un backend qui ne connaît pas\n"
        "         encore la clé l'ignore et rend exactement ce qu'il rendait. */\n"
        "      tracks:svmTracksPayload(proj),\n"
        "      clips:clips.filter(function(c){return c.src}).map(function(c){")

# ── M6 : autosave ───────────────────────────────────────────────────────────
A_M6 = "      duration_master:durMaster,ducking:ducking,clips:clips,"
R_M6 = ("      duration_master:durMaster,ducking:ducking,clips:clips,\n"
        "      /* sans cette clé, une piste ajoutée disparaissait au rechargement\n"
        "         et les clips qu'elle portait retombaient sur une piste inconnue,\n"
        "         donc hors du rendu — silencieusement. */\n"
        "      tracks:svmTracksPayload(proj),\n"
        "      /* P5 — de quel projet NOMMÉ ce brouillon est le brouillon. Le\n"
        "         backend n'écrit dans le projet QUE si cette clé désigne un\n"
        "         fichier existant : sans elle (montage sans nom), rien ne\n"
        "         change, pas un fichier n'est semé. */\n"
        "      project_id:proj.project_id,")

# ── M7 : restauration ───────────────────────────────────────────────────────
# TROIS clés, et la troisième est de P9. `v1_non_video` est rendu par
# GET /project depuis P8 : des IDENTIFIANTS de clips V1 dont l'artefact n'est
# pas une vidéo, joignables un à un aux `clips` de la MÊME réponse (le
# contrat est arrêté dans la docstring de la route). Personne ne le lisait —
# le backend savait, l'écran se taisait, et POST /render refusait en 400
# APRÈS le clic. M16d le pose sur la timeline ; il transite par `proj` et non
# par les clips eux-mêmes, DÉLIBÉRÉMENT : `clips` part tel quel à l'autosave
# (cf. M6), un drapeau collé sur un clip y serait persisté et survivrait à sa
# propre correction. `proj`, lui, n'est jamais sérialisé en bloc.
# `null` quand la clé est absente : une réponse qui ne dit rien ne marque
# rien. RECTIFICATION du 04/09/2026 (revue de qualité) — la justification
# écrite ici était FAUSSE, et c'est le second commit d'affilée qui traque des
# commentaires qui mentent. Elle disait : « l'ouverture d'un projet nommé
# (POST /projects/{pid}/open) ne rend pas ce champ, et le marquage s'y éteint
# plutôt que de mentir. » La route ne le rend effectivement pas
# (montage_service.py) — mais sa réponse n'arrive JAMAIS jusqu'ici. MESURÉ
# dans le bundle livré : `doOpen` enchaîne
# `send(url(p.id)+"/open","POST").then(function(){return
# req("/api/montage/project")})`, et c'est CETTE seconde réponse qui va à
# `svmApplyProject`. Les TROIS appelants runtime de `svmApplyProject` sont
# alimentés par GET /project : l'effet de montage, la remise à zéro depuis la
# Bibliothèque, et l'ouverture d'un projet nommé. Le repli reste du bon code
# défensif — un backend antérieur à P8, ou une réponse tronquée, n'a pas la
# clé — mais il ne couvre pas le chemin qu'on lui prêtait.
A_M7 = 'var np={demo:!1,name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",'
R_M7 = ('var np={demo:!1,tracks:svmTracksFrom(d.tracks),'
        'project_id:d.project_id,'
        'v1NonVideo:Array.isArray(d.v1_non_video)?d.v1_non_video:null,'
        'name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",')

# ── M8 : barre de transport ─────────────────────────────────────────────────
A_M8 = ('r.jsx("button",{className:"svm-tbtn",title:"Raccourcis ("'
        '+svmKeyLabel("keys_panel")+") — personnalisables",')

# ── M10 (P2) : la chip « mot : couleur / rebond / glow » et le bouton emoji ──
# ELLES VIVENT DANS R_M8, pas dans une section à elles : l'ancre A_M8 est déjà
# CONSOMMÉE par M8, et il n'existe pas de seconde ancre unique dans cette barre
# d'outils. Le panneau de style, lui, vit dans un tiroir du bloc `sonvfx` que
# cette chaîne ne peut pas rouvrir (vingt sections amont s'y trouvent).
# `DzTracks`, pas `DzMontage` : le bundle déclare DÉJÀ une fonction DzMontage
# au premier niveau (l'écran Montage lui-même) — redéclarer ce nom est une
# SyntaxError en sémantique module, celle sous laquelle index.html charge le
# bundle. C'est ce que `node_check_module` de test_montage_bundle.py garde.
# Le bouton emoji est RÉVERSIBLE : `pushHistory()` avant l'ajout, donc
# « annuler » retire les clips posés, et ce sont des clips ordinaires.
R_M10 = ('r.jsx(DzTracks.WordAnimChip,{value:(proj.subsStyle||{}).wordAnim||"couleur",'
         'onChange:function(v){subsStyleSet({wordAnim:v})}}),\n'
         '        r.jsx(DzTracks.EmojiBtn,{segments:subsSegsOf(clips),'
         'tracks:svmTracksOf(proj),note:fireNote,'
         'onAdd:function(cs){pushHistory();'
         'setClips(function(k){return (k||[]).concat(cs)});setDirty(!0)}}),')

# ── M11a (P3) : l'ÉTAT du panneau « Texte » ────────────────────────────────
# Il lui faut une déclaration dans le CORPS du composant : R_M8 est un tableau
# `children`, on n'y déclare pas un hook. L'ancre choisie est la déclaration de
# l'état du tiroir Sous-titres — mesurée UNIQUE, et voisine par le sujet.
# `dzTextOn`, pas `textOn` : mesuré, `stTx` apparaît DÉJÀ sept fois dans le
# bundle minifié, et un `var` de même nom dans la même fonction écraserait
# silencieusement l'autre. `dzTextOn` / `stDzTx` : zéro occurrence.
A_M11 = "  var stSu=x.useState(!1),subsOn=stSu[0],setSubsOn=stSu[1];"
R_M11 = ("  /* P3 — panneau « Texte » (monter en LISANT). Son état est À LUI :\n"
         "     il ne vit pas dans la zone des tiroirs (Sons / Narration /\n"
         "     Sous-titres, mutuellement exclusifs) mais dans la COLONNE\n"
         "     D'INSPECTION, où il ne dispute sa place à personne. */\n"
         "  var stDzTx=x.useState(!1),dzTextOn=stDzTx[0],setDzTextOn=stDzTx[1];\n"
         + A_M11)

# ── M11b (P3) : le bouton « texte » de la barre — DANS R_M8, comme M10 ──────
R_M11b = ('r.jsx("button",{className:"svm-tbtn dzm-txton","data-on":dzTextOn?"":void 0,'
          '"aria-pressed":dzTextOn,'
          'title:"Monter par le TEXTE : la narration mot par mot dans la colonne '
          'de droite, les mots de remplissage marqués, et la sélection coupée sur '
          'toutes les pistes non verrouillées (ce qui suit remonte)",'
          '"aria-label":"Panneau Texte",'
          'onClick:function(){setDzTextOn(!dzTextOn)},children:"texte"}),')

# ── M14 (P5) : le popover « projets » — DANS R_M8, comme M10 et M11b ───────
# Même raison qu'elles : A_M8 est déjà consommée par M8 et la barre de
# transport n'offre pas de seconde ancre unique. Le plan disait « popover
# Projets dans R_M8 » — c'est bien là.
# `DzTracks`, pas `DzMontage` (que le plan écrivait, comme il écrivait déjà
# `DzMontage.gradeAllBtn` en P4) : le bundle déclare DÉJÀ une fonction
# `DzMontage` au premier niveau — l'écran Montage lui-même — et redéclarer ce
# nom est une SyntaxError en sémantique MODULE, celle sous laquelle index.html
# charge le bundle. Invisible pour `node --check` sur un .js ; c'est
# `node_check_module` de test_montage_bundle.py qui la voit.
# HUIT props au 04/09/2026 — `payload` et `onFail` s'ajoutent après revue.
# `payload` : « Enregistrer sous… » envoie la timeline AFFICHÉE avec le nom.
# MESURÉ, sans elle, `POST /projects` ne lisait que montage_saved.json — et
# deux états courants n'en ont pas (installation neuve, et l'instant qui suit
# le bouton « bibliothèque ») : l'écran montrait une timeline et le popover
# répondait 400 « aucune timeline courante ». Le reste du temps, le disque
# avait jusqu'à 1,5 s de retard : 7 clips affichés, 1 clip nommé.
# `onFail` : quand l'ouverture échoue (409, panne réseau), `onBefore` a déjà
# annulé l'autosave en vol et RIEN ne le replanifie — `setSaveInfo` n'est pas
# dans les dépendances de l'effet. `svmDoSave` le relance sur-le-champ.
# `doDel`, lui, n'appelle PLUS `onBefore` : le serveur ferme cette course-là à
# TROIS verrous, et c'est le TROISIÈME — le verrou de module, arrivé dans le
# même commit — qui rend le retrait légitime. Les deux premiers (`project_id`
# retenu seulement s'il désigne un fichier existant ; miroir seulement dans ce
# fichier) laissaient un TOCTOU de deux sauts de thread : sans le verrou,
# retirer `onBefore` ici rouvre « le courant reste lié à un projet supprimé ».
# test_montage_projets.py [16] joue l'entrelacement avec et sans lui — c'est
# la CONDITION de ce retrait, pas sa confirmation ; [10] ne mesure que le cas
# séquentiel. Le détail est dans la couche.
# SIX props, pas cinq : `onBefore` s'ajoute à la liste du plan. MESURE — le
# bundle désamorce déjà exactement cette course pour le bouton
# « bibliothèque » : il ABANDONNE la requête d'autosave en vol avant son
# DELETE, faute de quoi elle arrive après et ressuscite ce qu'on vient
# d'effacer. Ouvrir un projet et supprimer un projet sont le même cas : sans
# `onBefore`, une sauvegarde partie 1,4 s plus tôt réécrit le courant avec le
# montage qu'on vient de quitter.
# PAS de `setDirty` ici, et c'est délibéré : au retour de chacune de ces
# routes le serveur a DÉJÀ écrit le courant ET le projet. Allumer
# « NON ENREGISTRÉ » juste après une ouverture réussie ferait mentir le badge
# et déclencherait un autosave qui réécrirait à l'identique.
R_M14 = ('r.jsx(DzTracks.Projects,{name:proj.name,projectId:proj.project_id,'
         'note:fireNote,\n'
         '          payload:function(){return svmSavePayload()},\n'
         '          onBefore:function(){'
         'if(saveAbortRef.current){try{saveAbortRef.current.abort()}catch(_e){}}'
         'saveSeqRef.current++;setSaveInfo(null)},\n'
         '          onFail:function(){if(dirty)svmDoSave(++saveSeqRef.current)},\n'
         '          onOpen:function(d){return svmApplyProject(d)},\n'
         '          onNamed:function(pid,nm){setProj(function(p){'
         'return Object.assign({},p,{project_id:pid,name:nm})})}}),')

# ── M16-lib (P9) : le bouton « Bibliothèque… » — DANS R_M8, comme M10/M11b/M14
# MÊME RAISON QU'ELLES, et elle est mesurée : A_M8 est déjà consommée par M8
# et la barre de transport n'offre pas de seconde ancre unique.
# CE QUE CE BOUTON RÉPARE, mesuré dans le bundle livré : `openPicker` n'était
# appelé QU'À UN endroit — le « + » de 14 px d'un en-tête de piste, révélé au
# survol de cette piste-là (`onClick:function(){ if(trackKind(tr.id)==="subs")
# {subsAddHere();return} openPicker(tr.id)}`). Rien, dans la barre de
# transport, ne proposait d'ajouter un clip. Les boutons « + vidéo » /
# « + audio » posés par M8 ajoutent une PISTE ; l'utilisateur les a lus comme
# « ajouter une vidéo » et le libellé lui donnait raison — d'où leur
# rectification en « + piste vidéo » / « + piste audio », qui est une édition
# de `DzmTrackAdd` DANS LA COUCHE et non une section de plus.
# Le libellé est « Bibliothèque… », pas « + clip » : c'est le mot que
# l'utilisateur a employé.
R_M16LIB = ('r.jsx(DzTracks.LibBtn,{tracks:svmTracksOf(proj),note:fireNote,'
            'onPick:openPicker}),')

R_M8 = ('r.jsx(DzTracks.TrackAdd,{tracks:svmTracksOf(proj),onChange:svmTracksSet}),\n'
        '        ' + R_M16LIB + '\n'
        '        ' + R_M10 + '\n'
        '        ' + R_M11b + '\n'
        '        ' + R_M14 + '\n'
        '        /* bouton discret du panneau raccourcis — fin de transport */\n'
        '        ' + A_M8)

# ── M12 (P3) : le panneau « Texte », et la coupe par plage ──────────────────
# ANCRE MESURÉE, pas choisie. Le plan hésitait entre `      subsDrawer(),` et
# `        transInspector(),`. Comptés le 04/09/2026 dans le bundle livré ET
# dans .bak_montage : `subsDrawer` — la zone des tiroirs, celle que le plan
# préférait — n'apparaît PAS UNE FOIS (les tiroirs s'y nomment `subsPanel()`
# et `narrPanel()`) ; `        transInspector(),` vaut exactement 1. Le
# panneau se pose donc dans la COLONNE D'INSPECTION, sous les inspecteurs.
# L'ancre est PRÉFIXE du remplacement : test_montage_bundle.py ne cherche
# donc pas à la voir disparaître.
#
# LA COUPE EST RÉVERSIBLE, ENTIÈREMENT — et c'est pour cela que M12 NE
# TOUCHE PAS à `proj.dur`. `pushHistory()` précède la première rippleCut et
# mémorise {clips, mixDb} : « annuler » défait donc la coupe en entier.
# Raccourcir `proj.dur` aurait cassé cette propriété, et pas seulement à
# l'écran : MESURÉ, la restauration au chargement fait
# `dur:Math.max(1,Number(d.duration)||maxEnd)`, donc une durée SAUVEGARDÉE
# l'emporte sur les clips. Couper, annuler, laisser l'autosave passer,
# rouvrir : la timeline revenait plus courte que ses propres clips, dont la
# queue sortait du champ. (Le rendu, lui, était indemne — montage_service
# recalcule `total`.) Réparer `undo` pour qu'il rende aussi la durée demande
# des ancres qui ne sont pas uniques : c'est une tâche à part. On ne touche
# donc plus à la durée du tout, et la note le DIT — la fin de la timeline
# est vide après une coupe, à l'utilisateur de la raccourcir s'il veut.
A_M12 = "        transInspector(),"
R_M12 = (A_M12 + '\n'
         '        /* P3 — les coupes sont appliquées de la FIN vers le DÉBUT :\n'
         '           une coupe tardive ne décale pas les précédentes, donc les\n'
         '           plages restent justes sans être recalculées entre deux. Un\n'
         '           SEUL pushHistory pour le lot : « annuler » défait le geste,\n'
         '           pas ses dix-sept morceaux. */\n'
         '        r.jsx(DzTracks.TextDrawer,{open:dzTextOn,clips:clips,note:fireNote,\n'
         '          onCut:function(rg,al){\n'
         '            if(!rg||!rg.length)return;\n'
         '            var rs=rg.slice().sort(function(u,v){return v[0]-u[0]});\n'
         '            var lk={};Object.keys(trackSt||{}).forEach(function(k){\n'
         '              if(trackSt[k]&&trackSt[k].l)lk[k]=1});\n'
         '            var lt=svmTracksOf(proj).filter(function(t){return t.loop})\n'
         '              .map(function(t){return t.id});\n'
         '            pushHistory();\n'
         '            /* les mots calés du tiroir, recollés sur LEUR clip : sans\n'
         '               eux, fendre un bloc de narration laisserait la phrase\n'
         '               entière sur les deux moitiés. */\n'
         '            var cs=DzTracks.withWords(clipsRef.current||[],al),rm=0;\n'
         '            rs.forEach(function(p){\n'
         '              var res=DzTracks.rippleCut(cs,p[0],p[1],'
         '{loopTracks:lt,locked:lk});\n'
         '              cs=res.clips;rm+=res.removed});\n'
         '            rm=Math.round(rm*1000)/1000;\n'
         '            /* les mots prêtés ne servaient qu\'à répartir le texte :\n'
         '               les garder gonflerait la sauvegarde d\'une copie de\n'
         '               toute la narration, que rien ne relit. */\n'
         '            setClips(DzTracks.dropWords(cs,svmTracksOf(proj)\n'
         '              .filter(function(t){return t.kind===\"subs\"})\n'
         '              .map(function(t){return t.id})));\n'
         '            setDirty(!0);\n'
         '            var vk=Object.keys(lk);\n'
         '            fireNote(rs.length+" coupe"+(rs.length>1?"s":"")+" — "+\n'
         '              rm.toFixed(2)+\" s retirés. Annuler défait la coupe '
         'entièrement. La durée du projet ne bouge pas : la fin de la timeline '
         'est maintenant vide, raccourcissez-la si vous voulez.\"+\n'
         '              (vk.length?" Pistes verrouillées ("+vk.join(", ")'
         '.toUpperCase()+") : leurs clips n\'ont pas bougé.":""))}}),')

# ── M13 (P4) : « étalonnage → tous les plans <PISTE> » ──────────────────────
# ANCRE MESURÉE, pas héritée. Le plan visait `        transInspector(),` en
# supposant qu'elle serait libre. COMPTÉE le 04/09/2026 dans le bundle livré ET
# dans .bak_montage : elle vaut 1 dans les deux — M12 l'a bien consommée, mais
# `R_M12` la REPREND EN TÊTE, donc elle survit intacte au patch et une section
# M13 pourrait s'y accrocher sans rien casser. Elle N'A PAS été retenue pour
# autant : elle poserait le bouton au-dessus des inspecteurs Transition,
# Overlay, Clip audio ET de tout le bloc Mixage, à un écran de la pile
# d'effets dont il recopie une ligne. « Cet étalonnage » n'aurait plus de
# référent visible.
# L'ancre retenue est la DERNIÈRE ligne de la colonne d'inspection, celle qui
# rend la pile d'effets — comptée 1 elle aussi, dans les deux fichiers. Le
# bouton se pose juste dessous, contre ce qu'il copie.
# `DzTracks`, pas `DzMontage` (que le plan écrivait) : le bundle déclare DÉJÀ
# une fonction `DzMontage` au premier niveau, et redéclarer ce nom est une
# SyntaxError en sémantique MODULE — celle sous laquelle index.html charge le
# bundle, invisible pour `node --check` sur le .js. C'est ce que garde
# `node_check_module` de test_montage_bundle.py.
# SIX arguments, pas cinq : `setDirty` s'ajoute à la liste du plan. MESURE —
# l'autosave du bundle est gardé par `if(proj.demo||!dirty)return;` : sans
# `setDirty(!0)`, un lot appliqué juste après une sauvegarde réussie ne part
# jamais au serveur et se perd au rechargement, sans un mot.
# L'ancre n'est PAS reprise telle quelle dans le remplacement (le `)]` devient
# `),`) : test_montage_bundle.py exigera donc de la voir DISPARAÎTRE.
A_M13 = '        (sel&&sel.tr==="s1"?null:vfxStackSection())]})]}),'
R_M13 = ('        (sel&&sel.tr==="s1"?null:vfxStackSection()),\n'
         '        /* P4 — le geste GLOBAL de l\'étalonnage : les quatre valeurs\n'
         '           du plan sélectionné recopiées sur tous les autres plans\n'
         '           réels de SA piste (pas « v1 » en dur : un plan V2 peut\n'
         '           porter un grade_basic). RÉVERSIBLE : un seul pushHistory\n'
         '           pour le lot ; « annuler » rend à chaque plan son\n'
         '           étalonnage d\'avant — déduit de trois faits mesurés, mais\n'
         '           rien ne l\'EXERCE (undo est un hook du composant). */\n'
         '        DzTracks.gradeAllBtn(sel,clips,setClips,pushHistory,setDirty,'
         'fireNote)]})]}),')

# ── M9a / M9b : en-tête de piste ────────────────────────────────────────────
# Le groupe est un FRÈRE des rangées, pas un membre : il est positionné en
# absolu dans l'en-tête (voir montage.css — l'en-tête fait 88px de large et
# il est déjà plein, c'est mesuré). L'ancre est préfixe du remplacement :
# test_montage_bundle.py ne cherche donc pas à la voir disparaître.
_HB = ("DzTracks.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,"
       "fireNote)")
A_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),'
R_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),\n                  ' + _HB + ','
A_M9b = 'children:[thType,thLock]},"tr")]}),'
R_M9b = ('children:[thType,thLock]},"tr"),\n                  ' + _HB + ']}),')

# ══ P9 — « Bibliothèque… » qui pose un clip, et la remise qui se perdait ═══
#
# DEUX PIÈGES DE CHAÎNE, réglés ici une fois pour toutes :
#
# 1. `scripts/patch_bundle_libsend.py` (greffon S4, `GREFFE_MONTAGE`) est le
#    maillon qui POSE le défaut — il appelle `addAsset(…, "v2")` — mais il est
#    en AMONT. Le relancer seul effacerait ce que les maillons suivants ont
#    écrit : le mode de panne qui a déjà coûté vingt-deux correctifs au dépôt.
#    LA CORRECTION SE PORTE DONC ICI, EN AVAL, SUR `addAsset` : c'est addAsset
#    qui choisit la piste, et le corriger là répare ce greffon-là ET toute
#    remise future. Aucun octet de libsend n'est touché.
# 2. `frontend/patches/son-vfx-montage.js` ne peut PAS être édité : le bloc
#    correspondant du bundle porte les vingt sections V3/V4/V6/V8/V9 de
#    patch_bundle_vfxrack.py et S3…S17 de patch_bundle_subs.py, `.bak_vfxrack`
#    et `.bak_subs` sont absents de cette copie, et l'ancre V10 est consommée.
#    Éditer ce fichier et relancer son patcher effacerait les vingt sections
#    sans un mot et sans retour. Tout passe donc par des ancres, ici.
#
# ÉCART DÉCLARÉ (faute n°5 — « le code du plan est une intention »). Le plan
# annonçait une COLLISION D'ANCRE avec la tâche 7 : M15 revendique
# `  function addAsset(src,label,kind,srcDur,trId,atTime){`, et celle des deux
# tâches qui passe en second devait replier sa section dans le remplacement de
# l'autre. MESURE : cette section n'a pas besoin de cette ancre-là.
# `    var tr2=trId||"v2",d=durRef.current;` vaut EXACTEMENT 1 dans le bundle
# livré ET dans .bak_montage, et porte à elle seule les deux corrections.
# L'ancre de la tâche 7 reste donc LIBRE et intacte : il n'y a pas de repli à
# faire, dans un sens ni dans l'autre. C'est mieux que ce que le plan
# prévoyait, et c'est dit ici pour que la tâche 7 ne cherche pas un repli qui
# n'existe pas.

# ── M16-ref (P9) : les pistes du projet, FRAÎCHES, pour addAsset ────────────
# MESURE qui l'impose : le greffon amont consomme `window.__dzMontageAdd`
# depuis un `x.useEffect(…, [])`, donc il appelle l'`addAsset` du PREMIER
# rendu. Dans cette fermeture-là, `proj` est encore la maquette de démo
# (`{demo:!0,name:"teaser_abyss",…}`) — sans `tracks`, donc `svmTracksOf`
# retomberait sur DZM_DEFAULT_TRACKS, QUI CONTIENT v2. Lire `proj` depuis
# addAsset aurait rendu la correction inopérante sur le seul chemin qui l'a
# motivée. Une ref mise à jour à CHAQUE rendu est le motif déjà employé neuf
# fois dans ce composant (durRef, clipsRef, phRef, trackStRef…) ; on le
# reprend plutôt que d'en inventer un autre.
A_M16REF = "  var durRef=x.useRef(proj.dur);durRef.current=proj.dur;"
R_M16REF = (A_M16REF + "\n"
            "  /* P9 — les PISTES du projet, relues à chaque rendu, pour que\n"
            "     `addAsset` ne décide jamais sur un `proj` périmé (le greffon\n"
            "     « Envoyer vers → Montage » l'appelle depuis la fermeture du\n"
            "     premier rendu). Même motif que durRef, juste au-dessus. */\n"
            "  var dzTracksRef=x.useRef(null);"
            "dzTracksRef.current=svmTracksOf(proj);\n"
            "  /* P9 — « le VRAI projet est-il arrivé ? ». Tant que\n"
            "     `svmApplyProject` n'a pas remplacé la maquette, `proj` est la\n"
            "     démo : sans `tracks`, donc svmTracksOf retombe sur les six\n"
            "     pistes historiques — v2 COMPRISE. Un clip posé à cet\n"
            "     instant-là repartirait sur une v2 que le projet réel n'a pas,\n"
            "     et `setClips(cs)` de svmApplyProject l'effacerait de toute\n"
            "     façon en écrasant la liste entière. */\n"
            "  var dzReadyRef=x.useRef(!1);dzReadyRef.current=!proj.demo;\n"
            "  /* P9 — L'ATTENTE DE LA TIMELINE RÉELLE, ET SON EXTINCTION.\n"
            "     Elle vit ICI, dans le corps du composant, et non dans\n"
            "     `addAsset` : c'est le seul endroit d'où elle peut être\n"
            "     ANNULÉE. `DzMontage` est monté CONDITIONNELLEMENT\n"
            "     (`s===\"montage\"&&r.jsx(DzMontage,…)`) — quitter l'onglet le\n"
            "     DÉMONTE. Sans la garde ci-dessous, la chaîne continuait à se\n"
            "     replanifier toute seule jusqu'au plafond, puis `fireNote`\n"
            "     tapait dans un arbre démonté : no-op silencieux de React 18.\n"
            "     MESURÉ le 04/09/2026 en rejouant le texte LIVRÉ sous node,\n"
            "     horloge simulée, démontage à 300 ms : 167 reprogrammations,\n"
            "     20 040 ms d'horloge, 1 note émise dans le vide, 0 clip posé.\n"
            "     Ni le clip NI le message — exactement le silence que toute\n"
            "     cette tâche supprime ailleurs, et dans la fenêtre où l'on est\n"
            "     le plus tenté de partir puisque GET /project ffprobe chaque\n"
            "     asset. La garde EST la correction ; `clearTimeout` n'est que\n"
            "     la propreté (il épargne un dernier réveil de 120 ms).\n"
            "     UNE SEULE chaîne peut être en vol : tant que `dzReadyRef` est\n"
            "     faux, `proj.demo` est vrai, et les six autres appelants\n"
            "     d'`addAsset` sont derrière une garde `proj.demo` — le greffon\n"
            "     amont, lui, ne tire qu'une fois (son effet `[]` supprime\n"
            "     `window.__dzMontageAdd` avant même le setTimeout). Une seule\n"
            "     ref de minuteur suffit donc.\n"
            "     Le remontage RÉARME : un effet `[]` est rejoué en double sous\n"
            "     StrictMode, et sans cette ligne l'écran serait mort pour de\n"
            "     bon après le premier aller-retour. */\n"
            "  var dzAliveRef=x.useRef(!0),dzWaitRef=x.useRef(0);\n"
            "  x.useEffect(function(){dzAliveRef.current=!0;\n"
            "    return function(){dzAliveRef.current=!1;\n"
            "      if(dzWaitRef.current){clearTimeout(dzWaitRef.current);\n"
            "        dzWaitRef.current=0}}},[]);\n"
            "  function dzAddWhenReady(a1,b1,c1,d1,e1,f1,until){\n"
            "    dzWaitRef.current=0;\n"
            "    if(!dzAliveRef.current)return;\n"
            "    if(dzReadyRef.current){addAsset(a1,b1,c1,d1,e1,f1);return}\n"
            "    if(Date.now()>=until){fireNote(\"« \"+b1+\" » n'a pas été posé : \"+\n"
            "      \"la timeline réelle n'est jamais arrivée — la maquette de \"+\n"
            "      \"démonstration est toujours à l'écran. Enregistrez d'abord \"+\n"
            "      \"un montage, puis reposez le clip avec « Bibliothèque… ».\");"
            "return}\n"
            "    dzWaitRef.current=setTimeout(function(){\n"
            "      dzAddWhenReady(a1,b1,c1,d1,e1,f1,until)},120)}")

# ── M16a (P9) : addAsset pose sur une piste QUI EXISTE, et attend la durée ──
# CE QUI EST FAIT ICI, EXACTEMENT — l'étape demandait de « remplacer le
# `setTimeout(…, 450)` du greffon ». Ce setTimeout N'EST PAS remplacé, et ne
# peut pas l'être : il vit dans patch_bundle_libsend.py, maillon AMONT que la
# même étape interdit de toucher (le rejouer seul effacerait tout ce que la
# chaîne écrit ensuite) — la lettre du plan se contredisait elle-même.
# L'attente est posée EN AVAL et s'exécute APRÈS ces 450 ms : le greffon
# appelle quand bon lui semble, et c'est ici qu'on décide d'attendre, de
# poser, ou de refuser en le disant.
#
# (a) LA PISTE. `trId||"v2"` posait le clip sur une piste qui peut ne pas
#     exister, et rien ne le vérifiait. MESURÉ dans la sauvegarde réelle du
#     04/09/2026 : `tracks` vaut [v1, a2, a1, a3, s1] — il n'y a PAS de piste
#     v2. Le clip entrait dans `clips`, il était sauvegardé, il serait parti
#     au rendu en incrustation ; mais la timeline ne dessine que
#     `svmTracksOf(proj).map(…)` : il était invisible et inselectionnable.
#     « rien n'est apparu » était exact, et le clip était pourtant là.
# (b) LE RETARD DU GREFFON AMONT. Le brief donnait pour cause
#     « `durRef.current` encore 0 tant que GET /project n'a pas répondu ».
#     MESURÉ, C'EST FAUX : l'état initial est `{demo:!0,…,dur:SVM_DEMO_DUR,…}`
#     et `var SVM_DEMO_DUR=64` — la durée vaut 64 dès le premier rendu et ne
#     passe jamais par 0. Une garde `dur > 0` aurait été du code mort.
#     LA VRAIE COURSE est double : à 450 ms, si GET /project n'a pas répondu
#     (il ffprobe chaque asset), (i) `proj` est encore la MAQUETTE, sans
#     `tracks` — svmTracksOf retombe sur les six pistes historiques, v2
#     comprise ; (ii) `svmApplyProject` fait ensuite `setClips(cs)`, qui
#     REMPLACE la liste entière — le clip posé entre-temps est effacé.
#     On attend donc la seule condition qui compte : que la maquette ait cédé
#     la place. Les 20 s sont un PLAFOND CHOISI, pas une mesure — et l'échec
#     est DIT, là où le greffon amont enveloppe tout dans un `catch` muet.
#
# CE QUI A QUITTÉ CETTE SECTION (revue de qualité du 04/09/2026) :
# `dzAddWhenReady` est remontée dans R_M16REF. Trois raisons, la première
# étant un défaut : (1) déclarée dans `addAsset`, elle n'était joignable par
# AUCUN démontage — le minuteur ne s'annulait jamais ; (2) elle était recréée
# à chaque appel d'`addAsset` alors qu'elle ne ferme que sur `dzReadyRef`,
# `dzWaitRef`, `fireNote` et `addAsset` ; (3) son commentaire pesait 2 856
# octets EXPÉDIÉS DANS LE BUNDLE DE PRODUCTION — il est ici, en Python, où il
# ne coûte rien à l'utilisateur.
#
# AUCUN geste destructif n'a encore eu lieu aux refus : ils sortent AVANT
# `pushHistory()`.
A_M16A = '    var tr2=trId||"v2",d=durRef.current;'
R_M16A = (
    "    /* P9 — la piste RÉSOLUE, et l'attente de la timeline réelle (celle-\n"
    "       ci vit dans le corps du composant, plus haut : c'est le seul\n"
    "       endroit d'où le démontage de l'onglet peut l'éteindre). */\n"
    "    var d=durRef.current;\n"
    "    if(!dzReadyRef.current){dzAddWhenReady(src,label,kind,srcDur,trId,\n"
    "      atTime,Date.now()+20000);return}\n"
    "    var dzTs=dzTracksRef.current||svmTracksOf(proj);\n"
    "    var dzWant=kind===\"audio\"?\"audio\":\"video\";\n"
    "    var dzMot=dzWant===\"audio\"?\"audio\":\"vidéo\";\n"
    "    var tr2=(trId&&dzTs.some(function(t){return t&&t.id===trId}))?trId\n"
    "      :DzTracks.pickTrack(dzTs,dzWant);\n"
    "    if(!tr2){fireNote(\"« \"+label+\" » n'a pas été posé : ce projet ne \"+\n"
    "      \"porte aucune piste \"+dzMot+\". Ajoutez-en une avec \"+\n"
    "      \"« + piste \"+dzMot+\" » dans la barre de transport, puis \"+\n"
    "      \"recommencez.\");return}\n"
    "    var dzMoved=(trId&&tr2!==trId)?String(trId).toUpperCase():\"\";")

# ── M16b (P9) : la note dit où le clip a atterri, et ce que ça change ───────
# Le clip DÉJÀ invisible dans la sauvegarde ne se répare pas tout seul — cette
# section ne le déplace pas, elle dit la vérité sur le geste EN COURS.
#
# LE MOT EST CHOISI, PAS ÉCRIT EN DUR (revue de qualité) : la note annonçait
# « + piste vidéo » même pour une piste AUDIO, alors que le refus voisin
# choisissait déjà le mot. Le chemin est atteignable et lu : `svmSfxTrackOf`
# rend a1/a2/a3 EN DUR, et `dzmRemove` ne protège que v1 et s1 — un projet
# dont A3 a été retiré, puis un bruitage inséré depuis le tiroir Sons, et la
# note disait « Recréer A3 avec « + piste vidéo » ». Les deux emplois lisent
# désormais le même `dzMot`.
#
# CE QUE LA NOTE DIT MAINTENANT DU CLIP QU'ON POSE, et pas seulement des
# anciens : sans V2, `pickTrack` rend `v1` — la piste de FOND. Or V1 est une
# SÉQUENCE CONCATÉNÉE au rendu (montage_service.py : `v1_in` trié par `start`
# dans /render comme dans /loudness) : le film gagne UN PLAN DE PLUS, pas une
# incrustation, et `svmApplyProject` faisant `setPh(0)`, le clip atterrit à
# 0:00 sur le premier plan. C'est très supérieur à « invisible », mais ce
# n'est pas ce que le libellé de la Bibliothèque promet (« 🎞 Montage —
# overlay à la tête de lecture ») : la note le dit, en toutes lettres.
#
# CE QU'ON NE FAIT PAS, ET POURQUOI — la revue proposait de CRÉER la piste
# d'incrustation manquante par `dzmAdd` au lieu de retomber sur le fond.
# Refusé, sur deux mesures :
#   1. `dzmAdd` promet le plus PETIT identifiant libre, pas celui qu'on
#      demande. MESURÉ sous node le 04/09/2026 : sur [v1, a2, a1, a3, s1] la
#      demande « v2 » tombe juste — mais sur [v1, a1, s1] la demande « a3 »
#      (celle de `svmSfxTrackOf` pour un bruitage) rend `a2`, DE BUS
#      « musique ». On aurait créé une piste que personne n'a demandée, sous
#      un autre nom ET sur un autre bus de mixage, puis nommé « a3 » dans la
#      note. Le repli devrait de toute façon être avoué.
#   2. `pushHistory` ne mémorise que {clips, mixDb} : une piste créée
#      SURVIVRAIT à « annuler », et l'autosave l'écrirait dans le projet
#      enregistré (M6 sérialise `tracks`). L'application ferait au projet de
#      l'utilisateur un changement de structure qu'elle ne sait pas défaire,
#      sans le lui demander.
# Le repli, lui, est entièrement réversible : « annuler » retire le clip et
# rien d'autre n'a bougé.
#
# LA SORTIE EST NOMMÉE — ET LE TEXTE NE PROMET PAS PLUS QUE `dzmAdd` NE TIENT.
# Sur la sauvegarde réelle [v1, a2, a1, a3, s1], « + piste vidéo » recrée
# exactement `v2` : un clic. Mais la même règle du « plus petit identifiant
# libre » qui rend le bouton exact ici le rend APPROXIMATIF ailleurs — sur
# [v1, a1, s1], « + piste audio » rend `a2` avant de rendre `a3`. Écrire
# « Créez A3 avec « + piste audio » » aurait donc été un mensonge de plus dans
# une note dont tout l'objet est de ne pas mentir : elle dit la RÈGLE (« le
# plus petit identifiant libre ») et invite à cliquer jusqu'à voir la piste
# voulue. C'est vrai dans les deux cas, et cela explique le clic
# intermédiaire au lieu de le laisser surprendre.
A_M16B = ('    fireNote("« "+label+" » ajouté sur "+tr2.toUpperCase()+" à "'
          '+svmShort(st)+" — glissez / rognez sur la piste.")}')
R_M16B = (
    "    fireNote(\"« \"+label+\" » ajouté sur \"+tr2.toUpperCase()+\" à \"\n"
    "      +svmShort(st)+\" — glissez / rognez sur la piste.\"+\n"
    "      (dzMoved?\" La piste \"+dzMoved+\" n'existe pas dans ce projet : le \"+\n"
    "        \"clip vient d'être posé sur \"+tr2.toUpperCase()+\" à la place\"+\n"
    "        (tr2===\"v1\"?\", où il s'AJOUTE À LA SUITE des plans au lieu de \"+\n"
    "          \"s'incruster par-dessus\":\"\")+\n"
    "        \". « + piste \"+dzMot+\" » recrée le plus petit identifiant \"+\n"
    "        \"libre : cliquez jusqu'à voir \"+dzMoved+\", puis remontez-y le \"+\n"
    "        \"clip — les clips déjà posés sur cette piste absente y \"+\n"
    "        \"réapparaîtront aussi.\":\"\")+dzTail)}")

# ── M16c (P9) : le sélecteur applique LA règle du rendu, pas une copie ──────
# MESURE : `openPicker()` construisait sa liste « Rendus vidéo » avec
# EXACTEMENT le critère fautif que P8 vient de corriger côté serveur —
# `status === "done" && (video_path || final_video_path)`. Les planches
# `sprite2d` et les maillages `asset3d` y étaient donc encore proposés, et
# rien n'empêchait de reposer à la main les clips que P8 écarte.
# La règle N'EST PAS RÉÉCRITE en JavaScript : une seconde copie divergerait de
# la première au premier format ajouté. Le client interroge
# GET /api/montage/media-rules, qui sert `_VIDEO_EXTS` — la liste même que lit
# `_is_video_artifact`. Route injoignable : la liste n'est PAS filtrée et le
# sélecteur le DIT (une liste vide en dur aurait affiché « aucun rendu vidéo
# terminé » sur une Bibliothèque pleine ; une liste écrite ici serait la copie
# qu'on refuse).
# `final_video_path` PRIME sur `video_path` dans `DzTracks.isVideoJob` : c'est
# l'ordre de `_resolve_src` côté serveur (`jr.final_video_path or
# jr.video_path`). L'ancien critère prenait le premier des deux qui existe —
# sur un job dont le brut est un .mp4 et le fini un .png, les deux ne rendent
# pas la même chose, et c'est le serveur qui a raison.
A_M16C = (
    '    Promise.all([\n'
    '      fetch("/api/images").then(function(res){return res.json()})'
    '.catch(function(){return {}}),\n'
    '      fetch("/api/jobs").then(function(res){return res.json()})'
    '.catch(function(){return []}),\n'
    '      fetch("/api/audio").then(function(res){return res.json()})'
    '.catch(function(){return {}})\n'
    '    ]).then(function(rr){\n'
    '      var imgs=((rr[0]&&rr[0].images)||[]).slice(0,24)'
    '.map(function(im){return {name:im.filename}});\n'
    '      var vids=(Array.isArray(rr[1])?rr[1]:[]).filter(function(j3){\n'
    '        return j3.status==="done"&&(j3.video_path||j3.final_video_path)&&\n'
    '          !(j3.provider==="montage"&&String(j3.image_filename||"")'
    '.indexOf("_preview")>=0)})\n'
    '        .slice(0,12).map(function(j3){return {job_id:j3.job_id,'
    'title:j3.title||j3.job_id,\n'
    '          dur:Number(j3.duration_real_s||j3.duration_s)||0}});\n'
    '      var auds=((rr[2]&&rr[2].audio)||[]).slice(0,24).map(function(a3){\n'
    '        return {name:a3.name,kb:a3.size_kb}});\n'
    '      setSources({images:imgs,videos:vids,audios:auds});'
    'setOvPick(trId)});')
R_M16C = (
    '    Promise.all([\n'
    '      fetch("/api/images").then(function(res){return res.json()})'
    '.catch(function(){return {}}),\n'
    '      fetch("/api/jobs").then(function(res){return res.json()})'
    '.catch(function(){return []}),\n'
    '      fetch("/api/audio").then(function(res){return res.json()})'
    '.catch(function(){return {}}),\n'
    '      /* P9 — LA règle du rendu, servie par le backend. Pas une copie. */\n'
    '      fetch("/api/montage/media-rules").then(function(res){'
    'return res.json()}).catch(function(){return {}})\n'
    '    ]).then(function(rr){\n'
    '      var imgs=((rr[0]&&rr[0].images)||[]).slice(0,24)'
    '.map(function(im){return {name:im.filename}});\n'
    '      var xt=(rr[3]&&Array.isArray(rr[3].video_exts)&&rr[3].video_exts.length)\n'
    '        ?rr[3].video_exts:null;\n'
    '      var vids=(Array.isArray(rr[1])?rr[1]:[]).filter(function(j3){\n'
    '        return DzTracks.isVideoJob(j3,xt)})\n'
    '        .slice(0,12).map(function(j3){return {job_id:j3.job_id,'
    'title:j3.title||j3.job_id,\n'
    '          dur:Number(j3.duration_real_s||j3.duration_s)||0}});\n'
    '      var auds=((rr[2]&&rr[2].audio)||[]).slice(0,24).map(function(a3){\n'
    '        return {name:a3.name,kb:a3.size_kb}});\n'
    "      if(!xt)fireNote(\"Règle d'extensions vidéo indisponible \"+\n"
    '        "(GET /api/montage/media-rules) — la liste « Rendus vidéo » '
    'n\'est "+\n'
    '        "PAS filtrée : elle peut proposer des planches de sprites ou des "+\n'
    '        "maillages 3D, que le rendu refusera.");\n'
    '      setSources({images:imgs,videos:vids,audios:auds});'
    'setOvPick(trId)});')

# ── M16d (P9) : `v1_non_video` enfin LU, sur la timeline ────────────────────
# GET /project le rend depuis P8 — des identifiants de clips joignables aux
# `clips` de la même réponse — et AUCUNE interface ne le lisait. Le backend
# savait, l'écran se taisait, et POST /render refusait en 400 APRÈS le clic.
# Le marquage est là pour que l'utilisateur voie le problème AVANT de cliquer.
# La chip est un BOUTON : la voie de sortie est offerte SUR PLACE (elle rouvre
# la Bibliothèque sur la piste du clip) au lieu d'être devinée — le même geste
# que « Bibliothèque… ». `openPicker` est déclaré dans le corps du composant,
# comme cette rangée ; `tr` et `c` sont les variables de la boucle de pistes.
A_M16D = ('                      r.jsx("div",{className:"svm-cliplabel",'
          'children:c.label}),')
R_M16D = (A_M16D + '\n'
          '                      /* P9 — signalé AVANT le rendu, pas après son\n'
          '                         400 : ce plan n\'est pas une vidéo. */\n'
          '                      (c.tr==="v1"&&'
          '(proj.v1NonVideo||[]).indexOf(c.id)>=0)?\n'
          '                        DzTracks.badSrc(c,function(){'
          'openPicker(c.tr)}):null,')

# ══ P6 — REMPLACER LA SOURCE D'UN PLAN, SANS PERDRE SON MONTAGE ═══════════
#
# TROIS CHOSES QUE LE PLAN DISAIT ET QUI SONT FAUSSES, mesurées avant d'être
# écartées — c'est la faute n°5 du chantier (« le code du plan est une
# intention »), et elle se paie trois fois ici.
#
# 1. « COLLISION D'ANCRE avec la tâche 16 sur `addAsset` » : IL N'Y EN A PAS.
#    La tâche 16 a corrigé `addAsset` par une AUTRE ancre (la ligne de
#    résolution de piste), et celle que M15 revendique — la signature de la
#    fonction — vaut EXACTEMENT 1 dans le bundle livré ET dans .bak_montage.
#    Aucun repli à faire, dans un sens ni dans l'autre.
#
# 2. « `DzMontage.replaceSrc` / `DzMontage.NewerHint` » : NON. Le bundle
#    déclare DÉJÀ `function DzMontage` au premier niveau ; redéclarer ce nom
#    est une SyntaxError en sémantique MODULE — celle sous laquelle
#    index.html charge le bundle, invisible pour `node --check` sur le .js.
#    C'est la TROISIÈME fois que le plan écrit cette erreur (P4 et P5
#    l'avaient déjà corrigée) ; l'export est sous `DzTracks`, et
#    `node_check_module` de test_montage_bundle.py garde la propriété.
#
# 3. « `transInspector(),`, ancre DÉJÀ CONSOMMÉE par M13 → mettre le bouton
#    DANS R_M13 » : elle n'est PAS consommée — elle vaut 1 dans le bundle
#    livré comme dans .bak_montage (R_M12 la reprend en tête, R_M13 ne la
#    touche pas), et M13 l'avait écartée pour une raison qui lui est propre :
#    son bouton RECOPIE une ligne de la pile d'effets, qui vit tout en bas de
#    la colonne. Cette raison-là ne vaut pas pour P6.
#
# L'ANCRE DE M16, CHOISIE ET MESURÉE. Ce bouton n'a pas les mêmes référents
# que celui de M13 : il promet que les BORNES, les EFFETS et la TRANSITION ne
# bougent pas. Deux de ces trois garanties sont rendues juste au-dessus de
# l'ancre retenue — la fenêtre « In / Out » (le bloc de propriétés) et, deux
# lignes plus bas, l'inspecteur de transition. Le nom du plan sélectionné est
# trois lignes plus haut. Le bouton se pose donc ENTRE la fenêtre de source
# qu'il recale et la transition qu'il conserve, à portée du regard du clip
# sélectionné — et non au milieu du bloc Mixage, où `transInspector(),`
# l'aurait mis un cran plus bas, sous un inspecteur qui ne s'affiche que pour
# les plans V1. L'ancre retenue (l'inspecteur de sous-titres) vaut 1 dans le
# bundle livré ET dans .bak_montage ; aucune autre section ne la touche.
#
# L'ORDRE DE M15, VÉRIFIÉ ET DIT. La section s'insère juste après la
# signature d'`addAsset`, donc AVANT la résolution de piste posée par la
# tâche 16. C'est le bon ordre, et pour une raison de fond : un remplacement
# NE CHOISIT AUCUNE PISTE — il garde celle du plan. Laisser la résolution
# tourner d'abord aurait fait calculer, puis jeter, une piste ; et sur un
# projet sans piste vidéo elle REFUSE (« ce projet ne porte aucune piste
# vidéo ») — un remplacement sur une piste audio ou sur V1 aurait été bloqué
# par un message qui ne le concerne pas.
#
# GESTE DESTRUCTIF, DONC RÉVERSIBLE DEUX FOIS. `pushHistory()` précède
# l'écriture, une seule entrée pour le geste ; l'historique de cet écran ne
# mémorise que {clips, mixDb}, ce que la note DIT (ni la durée du projet ni
# les pistes — ce geste n'y touche pas, mais la limite est celle de
# l'historique et l'utilisateur la rencontrera). La seconde voie est
# `src_history`, empilée sur le clip et rendue par « Revenir à la version
# précédente » — elle survit à l'enregistrement, mesuré des deux côtés
# (le serveur range les clips tels quels, la restauration les recopie de
# même).
#
# LE VERROU DE PISTE est vérifié DEUX fois, et ce n'est pas une copie de
# règle : c'est l'idiome de ce composant, écrit HUIT fois dans le bundle
# (supprimer, lame, glisser, rogner…), chaque geste le posant sur SA cible.
# COMPTE MESURE le 04/09/2026, pas estime : le littéral
# `trackStRef.current[c.tr]&&trackStRef.current[c.tr].l` apparaît 8 fois
# dans `index-BEOJX8L5.js.bak_montage` (l'entrée de ce patcher) comme dans
# le bundle livré ; 12 lectures du verrou en tout dans l'entrée, dont la
# bascule `svmTrackLock` et le badge de la piste, qui ne sont pas des
# gestes. « six » était une estimation de mémoire, sous-évaluée.
# En M16 il évite d'ARMER pour rien (le sélecteur refuserait, et le mode
# resterait armé pour le clip suivant) ; en M15 il refuse le remplacement
# lui-même, sur la piste du PLAN VISÉ et non sur celle qu'`addAsset`
# résoudrait.

# ── M15 (P6) : le mode remplacement, en tête d'addAsset ────────────────────
A_M15 = "  function addAsset(src,label,kind,srcDur,trId,atTime){"
R_M15 = (A_M15 + "\n"
         "    /* P6 — MODE REMPLACEMENT, en court-circuit AVANT tout le reste :\n"
         "       un remplacement ne choisit pas de piste, il garde celle du\n"
         "       plan. Le mode est CONSOMMÉ dès l'entrée (une seule fois par\n"
         "       armement), et les TROIS refus sortent AVANT pushHistory.\n"
         "\n"
         "       CE COURT-CIRCUIT PREND TOUS LES APPELANTS D'`addAsset`, et\n"
         "       c'est DÉCLARÉ ici parce que ce n'est pas anodin. Le\n"
         "       sélecteur est un panneau de 300 px en haut à droite\n"
         "       (`.svm-pop` : position:absolute, top:52px, right:18px,\n"
         "       z-index:20 — MESURÉ dans shared/son-vfx-montage.css) et il\n"
         "       n'a NI voile NI backdrop : tout le reste de l'écran reste\n"
         "       cliquable pendant que le mode est armé, et le mode le reste\n"
         "       tant qu'`ovPick` ne bouge pas. Deux chemins arrivent donc\n"
         "       ici sans être des clics du sélecteur :\n"
         "         · le GLISSER-DÉPOSER d'une vignette sur une bande (les\n"
         "           vignettes sont `draggable:!0`). La piste visée et\n"
         "           l'instant du dépôt sont alors JETÉS — un remplacement\n"
         "           n'en veut pas — et le geste devient un remplacement.\n"
         "           C'est ASSUMÉ : glisser une vignette, c'est choisir dans\n"
         "           le sélecteur, et le titre du panneau dit que le\n"
         "           prochain choix remplacera (section M15b). Fermer le\n"
         "           panneau désarme.\n"
         "         · `sfxInsert` (tiroir Sons, dont l'état `sfxOn` est\n"
         "           INDÉPENDANT d'`ovPick` et rendu hors du panneau) :\n"
         "           `addAsset({audio:fn},…,\"audio\",…)`. Celui-là n'est PAS\n"
         "           assumable : MESURÉ sous node, `replaceSrc` accepte\n"
         "           l'objet tel quel et le `src` d'un plan V1 devenait\n"
         "           `{audio:\"…\"}` — avec ses bornes, ses effets et sa\n"
         "           transition, et la fin ramenée à la durée du .wav.\n"
         "           D'où le refus de GENRE ci-dessous, qui manquait.\n"
         "       Le genre passe AVANT le verrou : déverrouiller la piste ne\n"
         "       rendrait pas un son valide pour un plan vidéo, et envoyer\n"
         "       l'utilisateur déverrouiller serait l'envoyer dans le mur. */\n"
         "    if(dzmReplaceRef.current){\n"
         "      var rc=dzmReplaceRef.current;dzmReplaceRef.current=null;\n"
         "      setDzmArm(null);\n"
         "      var rcs=clipsRef.current||[],rk=null,ri;\n"
         "      for(ri=0;ri<rcs.length;ri++)if(rcs[ri].id===rc.id)rk=rcs[ri];\n"
         "      setOvPick(\"\");\n"
         "      if(!rk){fireNote(\"Le plan à remplacer n'est plus dans la \"+\n"
         "        \"timeline : rien n'a changé, et « \"+label+\" » n'a pas été \"+\n"
         "        \"posé. Sélectionnez un plan puis « Remplacer la source… », \"+\n"
         "        \"ou « Bibliothèque… » pour l'ajouter comme clip de \"+\n"
         "        \"plus.\");return}\n"
         "      var rkd=trackKind(rk.tr);\n"
         "      var akd=(kind===\"audio\"||(src&&src.audio))?\"audio\":\"video\";\n"
         "      if(rkd!==akd){\n"
         "        fireNote(\"« \"+label+\" » est \"+(akd===\"audio\"?\"un son\":\n"
         "          \"une image ou une vidéo\")+\" : impossible d'en faire la \"+\n"
         "          \"source d'un plan de la piste \"+rk.tr.toUpperCase()+\n"
         "          \" (\"+rkd+\"). Rien n'a changé, et rien n'a été posé — \"+\n"
         "          \"choisissez une source du même genre, ou \"+\n"
         "          \"« Bibliothèque… » pour l'ajouter comme clip de \"+\n"
         "          \"plus.\");return}\n"
         "      if(trackStRef.current[rk.tr]&&trackStRef.current[rk.tr].l){\n"
         "        fireNote(\"Piste \"+rk.tr.toUpperCase()+\" verrouillée — \"+\n"
         "          \"déverrouillez-la pour remplacer la source de ce \"+\n"
         "          \"plan.\");return}\n"
         "      var rr=DzTracks.replaceSrc(rk,src,label,srcDur);\n"
         "      pushHistory();\n"
         "      setClips(rcs.map(function(k){return k.id===rc.id?rr.clip:k}));\n"
         "      setSelId(rc.id);setDirty(!0);fireNote(rr.note);return}")

# ── M16 (P6) : les deux boutons et le rappel, dans l'inspecteur ────────────
A_M16 = "        subsInspector(),"
R_M16 = (A_M16 + "\n"
         "        /* P6 — le remplacement de source, posé ENTRE la fenêtre\n"
         "           « In / Out » qu'il recale et l'inspecteur de transition\n"
         "           qu'il conserve : les garanties du geste encadrent son\n"
         "           bouton. Voir le commentaire d'ancre dans le patcher. */\n"
         "        DzTracks.replaceBtn(sel,function(){\n"
         "          if(trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l){\n"
         "            fireNote(\"Piste \"+sel.tr.toUpperCase()+\" verrouillée — \"+\n"
         "              \"déverrouillez-la pour remplacer la source de ce \"+\n"
         "              \"plan.\");return}\n"
         "          dzmReplaceRef.current={id:sel.id,tr:sel.tr,\n"
         "            label:sel.label};\n"
         "          setDzmArm({tr:sel.tr,label:sel.label});\n"
         "          /* déjà ouvert sur cette piste : rouvrir le REFERMERAIT\n"
         "             (le sélecteur bascule), et le mode resterait armé sur\n"
         "             un panneau fermé. C'est `setDzmArm` — et non\n"
         "             `openPicker` — qui re-rend dans ce cas-là, sans quoi\n"
         "             le panneau resterait intitulé « Ajouter sur la piste\n"
         "             V1 » pendant qu'il remplace. */\n"
         "          if(ovPick!==sel.tr)openPicker(sel.tr)}),\n"
         "        DzTracks.revertBtn(sel,function(){\n"
         "          /* LE MÊME VERROU QUE M15 : ce geste réécrit `src`,\n"
         "             `label`, `srcIn` ET `end` — donc le bord droit du\n"
         "             clip sur la timeline. Sans cette garde, « Revenir à\n"
         "             la version précédente » était le SEUL des gestes\n"
         "             destructifs de cet écran à passer outre une piste\n"
         "             verrouillée, alors que M15 refuse de remplacer et\n"
         "             M16src refuse même d'ARMER. */\n"
         "          if(trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l){\n"
         "            fireNote(\"Piste \"+sel.tr.toUpperCase()+\" verrouillée \"+\n"
         "              \"— déverrouillez-la pour rendre à ce plan sa source \"+\n"
         "              \"précédente.\");return}\n"
         "          var rv=DzTracks.revertSrc(sel);if(!rv)return;\n"
         "          pushHistory();\n"
         "          setClips(clipsRef.current.map(function(k){\n"
         "            return k.id===sel.id?rv.clip:k}));\n"
         "          setDirty(!0);fireNote(rv.note)}),\n"
         "        r.jsx(DzTracks.NewerHint,{jobId:sel&&sel.src&&sel.src.job_id,\n"
         "          /* SECOND SITE D'ARMEMENT, écrit COMME LE PREMIER : la\n"
         "             ref ET son miroir, avec le libellé. Il pourrait s'en\n"
         "             passer AUJOURD'HUI — `addAsset` est appelé dans le\n"
         "             MÊME gestionnaire, donc aucun rendu ne s'intercale et\n"
         "             M15 éteint le miroir avant qu'il ne s'affiche ; les\n"
         "             deux écritures d'état sont regroupées par React et\n"
         "             n'aboutissent à rien. C'est écrit quand même parce que\n"
         "             cette sûreté-là tient à UNE propriété du site appelant\n"
         "             (sa synchronie), que rien n'oblige à durer : le jour où\n"
         "             ce gestionnaire attendrait quoi que ce soit avant\n"
         "             d'appeler `addAsset`, le mode serait armé et le\n"
         "             sélecteur, rouvert, se dirait encore « Ajouter sur la\n"
         "             piste V1 » — la faute exacte que M15b ferme. « La ref\n"
         "             et son miroir s'arment ensemble » devient ainsi une\n"
         "             règle STRUCTURELLE des deux sites, et le banc compte\n"
         "             les deux ensemble (`les_deux_sites_arment_la_ref_ET_le\n"
         "             _miroir`) : ils ne peuvent plus se désolidariser en\n"
         "             silence. */\n"
         "          onPick:function(c){dzmReplaceRef.current={id:sel.id,\n"
         "            tr:sel.tr,label:sel.label};\n"
         "            setDzmArm({tr:sel.tr,label:sel.label});\n"
         "            addAsset({job_id:c.job_id},c.title||c.job_id,\"video\",\n"
         "              Number(c.duration_s)||0,sel.tr)}},\"dzmnew\"),")

# ── M15b (P6) : LE SÉLECTEUR DIT QU'IL EST ARMÉ ───────────────────────────
# Le mode remplacement était INVISIBLE pendant qu'il était actif : le panneau
# continuait de s'intituler « Ajouter sur la piste V1 » et de promettre
# « Posé à la tête de lecture » — deux phrases que le mode rend FAUSSES, sur
# le seul écran où l'utilisateur regarde au moment de choisir.
#
# `ovPicker()` vit dans frontend/patches/son-vfx-montage.js, qu'on ne touche
# PAS (règle de chaîne : ce patcher est en queue, son .bak est le seul filet).
# La modification se fait donc EN AVAL, par une ancre de la chaîne `montage`
# — et l'ancre a été MESURÉE avant d'être écrite : le trio
# `var tr2=…` / `svm-poptitle` / `svm-popnote` d'ovPicker vaut 1 dans
# index-BEOJX8L5.js.bak_montage (l'ENTRÉE de ce patcher, celle qui décide) et
# 1 dans la source du greffon amont. DANS LE BUNDLE LIVRÉ il vaut 0, et ce
# n'est pas une anomalie : le livré est la SORTIE de ce patcher, où la ligne
# du titre est précisément celle qui a été remplacée. Une version antérieure
# de ce commentaire écrivait « 1 dans le bundle livré » — vrai avant le
# premier rejeu, faux ensuite, et c'est l'entrée qui décide de toute façon.
# Aucun autre `svm-poptitle` ne porte ce libellé : le fichier en compte
# CINQ en tout (mesuré), donc QUATRE autres popovers, qui ont chacun le sien
# — « Preview 480p » / « Rendre & publier », « Ajouter un effet — moteur
# Effects / Mask », « Raccourcis clavier », « Transition de coupe ».
#
# L'ANCRE EST MULTI-LIGNE, et c'est voulu : le titre SEUL aurait laissé la
# note « Posé à la tête de lecture » sous un titre qui dit le contraire. Les
# deux phrases fausses se corrigent ensemble ou pas du tout.
A_M15B = (
    '    var tr2=ovPick,audio=trackKind(tr2)==="audio";\n'
    '    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[\n'
    '      r.jsx("div",{className:"svm-poptitle",children:"Ajouter sur la '
    'piste "+tr2.toUpperCase()}),\n'
    '      r.jsx("div",{className:"svm-popnote",style:{marginTop:6},\n'
    '        children:audio?("Posé à la tête de lecture ("+svmShort(ph)+"). '
    'A1 = dialogue, A2 = musique (ducking auto), A3 = SFX.")\n'
    '                      :("Posé à la tête de lecture ("+svmShort(ph)+") — '
    'ou déposez directement sur une bande ou le viewport. Les PNG gardent '
    'leur transparence.")}),')
R_M15B = (
    '    var tr2=ovPick,audio=trackKind(tr2)==="audio";\n'
    '    /* P6 — LE MODE REMPLACEMENT EST VISIBLE PENDANT QU\'IL EST ARMÉ.\n'
    '       `dzmArm` est le miroir d\'affichage de `dzmReplaceRef` (voir\n'
    '       M4b) : la ref reste ce que lit `addAsset`, l\'état n\'est là que\n'
    '       pour que ce panneau se re-rende et change de discours.\n'
    '       LA PISTE EST COMPARÉE, comme dans l\'effet de désarmement : cet\n'
    '       effet s\'exécute APRÈS le rendu, donc un sélecteur rouvert sur\n'
    '       une AUTRE piste aurait affiché « Remplacer… » le temps d\'une\n'
    '       image avant de se corriger. La condition d\'affichage est la\n'
    '       même que celle de l\'armement, pas une seconde règle. */\n'
    '    var dzmA=(dzmArm&&dzmArm.tr===tr2)?dzmArm:null;\n'
    '    return r.jsxs("div",{className:"svm-pop",style:{top:96},children:[\n'
    '      r.jsx("div",{className:"svm-poptitle",children:dzmA\n'
    '        ?("Remplacer la source de « "+(dzmA.label||"ce plan")+" »")\n'
    '        :("Ajouter sur la piste "+tr2.toUpperCase())}),\n'
    '      r.jsx("div",{className:"svm-popnote",style:{marginTop:6},\n'
    '        children:dzmA?("Le prochain élément choisi REMPLACERA la '
    'source de ce plan (piste "+dzmA.tr.toUpperCase()+") au lieu d\'être '
    'posé : ses bornes, ses effets, sa transition et son mixage restent en '
    'place. Un glisser-déposer compte aussi comme un choix — la piste et '
    'l\'instant du dépôt sont alors ignorés. Fermez ce panneau pour '
    'annuler.")\n'
    '               :audio?("Posé à la tête de lecture ("+svmShort(ph)+"). '
    'A1 = dialogue, A2 = musique (ducking auto), A3 = SFX.")\n'
    '                      :("Posé à la tête de lecture ("+svmShort(ph)+") — '
    'ou déposez directement sur une bande ou le viewport. Les PNG gardent '
    'leur transparence.")}),')

# ══ P10 — LA TIMELINE S'ÉTEND AU LIEU DE ROGNER ═══════════════════════════
#
# LE DÉFAUT, rapporté par l'utilisateur le 05/09/2026 : « j'ai voulu ajouter
# trois vidéos depuis la bibliothèque, or la timeline est fixe, je suis obligé
# de raccourcir des pistes vidéo pour les faire rentrer ».
#
# CE QUI A ÉTÉ MESURÉ AVANT D'ÉCRIRE UNE LIGNE, dans le bundle livré ET dans
# .bak_montage (l'entrée de ce patcher, celle qui décide) :
#   · `setProj(` n'est JAMAIS appelé avec `dur`. La durée est fixée UNE fois,
#     au chargement (`SVM_DEMO_DUR=64` pour la maquette,
#     `dur:Math.max(1,Number(d.duration)||maxEnd)` dans `svmApplyProject`), et
#     la barre de transport ne fait que l'AFFICHER.
#   · TROIS gestes rognaient contre elle, tous les trois EN SILENCE : l'ajout
#     (`st=Math.min(…,d-1)` puis `en=Math.min(d,…)`), le décalage clavier
#     (`ns=Math.min(Math.max(0,d-len),…)`) et le glisser à la souris
#     (`ns=Math.min(durRef.current-len,…)` pour le déplacement,
#     `Math.min(lim,…)` pour le bord droit).
#   · ÉTENDRE EST SANS RISQUE POUR LE RENDU. `renderPayload()` n'emporte
#     AUCUNE clé `duration` — relu ligne à ligne dans le bundle : {name,
#     ratio, preview, subtitles, duration_master, ducking, mix, tracks,
#     clips} — et `_build_montage_command` recalcule `total` depuis
#     `seg_durs` (montage_service.py). La seule route qui lit la durée postée
#     est POST /save (l.794), qui la RANGE. `proj.dur` est une BORNE
#     D'ÉDITION, pas une propriété du film.
#
# CE QUI NE CHANGE PAS, ET QUI EST DIT PARTOUT : `proj.dur` N'ENTRE PAS DANS
# L'HISTORIQUE. `pushHistory` ne mémorise que {clips, mixDb}. Étendre puis
# annuler rend les clips, PAS la durée — c'est exactement le piège que P3
# avait choisi d'éviter en ne touchant pas à `dur`, et on y touche ici
# DÉLIBÉRÉMENT. CHACUNE des quatre notes de P10 le dit, et le RETOUR existe :
# le contrôle explicite de la barre de transport (M17h) raccourcit aussi bien
# qu'il allonge. Faire entrer `dur` dans l'historique demanderait de réécrire
# `pushHistory`, `undo` ET `redo` — trois fermetures du composant dont AUCUNE
# n'offre d'ancre unique (mesuré : `var pushHistory=x.useCallback(` vaut 1,
# mais son corps n'est pas isolable des deux autres sans reprendre tout le
# bloc d'historique) : c'est une tâche à part, et rien ici ne fait semblant
# de l'avoir faite.
#
# LE ZOOM N'EST PAS RÉÉCRIT, ET C'EST UNE MESURE : le défilement horizontal
# EXISTE DÉJÀ (`.svm-scroll{flex:1; overflow:auto}` dans
# shared/son-vfx-montage.css l.331, pistes en `width:zoomPct%`, paliers
# SVM_ZOOMW=[100,150,220,320], Ctrl+molette continu jusqu'à 800 % avec
# conservation du point sous le curseur). Il est bon ; ce qui manque est
# qu'on le TROUVE, et cela ne se mesure qu'à l'écran. Rien n'est deviné ici :
# c'est consigné comme dette d'écran dans test_montage_bundle.py.

# ── M17a (P10) : l'ajout ÉTEND au lieu de rogner ────────────────────────────
# L'ANCRE PORTE LES DEUX LIGNES, et il le faut : la première rognait le POINT
# DE DÉPART (`st` ramené sous `d-1`), la seconde rognait la FIN (`en` ramené
# sous `d`). Corriger l'une sans l'autre aurait laissé le rognage entier —
# une vidéo de 6 s posée à 14 s dans un projet de 16 s serait encore entrée
# à 2 s. Comptée le 05/09/2026 : 1 dans le bundle livré, 1 dans .bak_montage.
#
# LA GARDE DES CLIPS MINUSCULES EST REPRISE À L'IDENTIQUE, et ce n'est pas de
# la superstition : `defaultLen` rend `Math.min(6, srcDur||6)` pour une vidéo
# et `Math.min(8, srcDur||8)` pour un son — une source de 0,2 s donne donc un
# clip de 0,2 s, insaisissable à la souris, PLAFOND OU PAS. La ligne ne
# servait donc pas qu'au rognage, et la retirer aurait été une régression
# gratuite sur un chemin que rien d'autre ne couvre.
#
# `setProj` AVANT `pushHistory` : sans conséquence, et vérifié. L'historique
# ne mémorise que {clips, mixDb} — écrire `dur` avant ou après ne change RIEN
# à ce qu'il capture. On l'écrit ici parce que c'est ici que `dzFit` est
# connu, et que les lignes suivantes (ovSeq, id, pushHistory, setClips)
# appartiennent au bundle et ne sont pas dans cette ancre.
A_M17A = ('    st=Math.min(Math.max(0,st),Math.max(0,d-1));\n'
          '    var en=Math.min(d,st+defaultLen(kind,srcDur));'
          'if(en-st<.5)st=Math.max(0,en-1);\n')
R_M17A = (
    "    /* P10 — LA TIMELINE S'ÉTEND, ELLE NE ROGNE PLUS. Le clip garde sa\n"
    "       longueur naturelle ; c'est la durée du projet qui grandit. La\n"
    "       garde des clips de moins d'une demi-seconde est celle d'avant :\n"
    "       elle vise les SOURCES minuscules, pas le plafond disparu. */\n"
    "    st=Math.max(0,st);\n"
    "    var en=st+defaultLen(kind,srcDur);if(en-st<.5)st=Math.max(0,en-1);\n"
    "    var dzFit=DzTracks.fitDur([{end:en}],d,0),dzGrew=dzFit>d?dzFit:0;\n"
    "    var dzTail=dzGrew?(\" La timeline a été allongée de \"+\n"
    "      svmRuler(Math.round(d))+\" à \"+svmRuler(Math.round(dzGrew))+\n"
    "      \" : le clip garde sa longueur entière au lieu d'être rogné sur la \"+\n"
    "      \"fin du projet. « Annuler » retire le clip mais NE raccourcit PAS \"+\n"
    "      \"la timeline — le réglage de durée, à côté du zoom, la reprend.\"):\"\";\n"
    "    if(dzGrew)setProj(function(p){"
    "return Object.assign({},p,{dur:dzGrew})});\n")

# ── M17b (P10) : le décalage clavier étend au lieu de buter ─────────────────
# L'ANCRE PORTE LE CORPS ENTIER DE `nudge`, du plafond jusqu'à `setDirty(!0)`.
# La seule ligne du plafond n'aurait pas suffi : la durée doit être ÉCRITE et
# DITE après `setClips`, et ces lignes-là ne sont pas dans une ancre à elles.
# Comptée 1 dans le bundle livré et dans .bak_montage.
#
# LA NOTE NE PARLE QUE QUAND LA DURÉE CHANGE VRAIMENT, et c'est un chiffre du
# bundle, pas un réglage de confort : une touche maintenue vaut UN PAS DE
# 1/30 s (`c.start+fr/30`), donc trente notes par seconde si l'on parlait à
# chaque pas. `dzmFitDur` arrondissant à la seconde supérieure, la durée ne
# bouge qu'une fois par seconde de contenu gagné : la note suit exactement
# les changements réels.
A_M17B = (
    '      var ns=Math.min(Math.max(0,d-len),Math.max(0,c.start+fr/30));\n'
    "      ns=Math.round(ns*3000)/3000; /* multiple exact d'1/30 s : zéro dérive */\n"
    '      if(Math.abs(ns-c.start)<1e-6)return;\n'
    '      var now=Date.now();\n'
    '      if(now-nudgeHistAt.current>600)pushHistory();\n'
    '      nudgeHistAt.current=now;\n'
    '      setClips(clipsRef.current.map(function(k){\n'
    '        return k.id===c.id?Object.assign({},k,{start:ns,end:ns+len}):k}));\n'
    '      setDirty(!0)},\n')
R_M17B = (
    "      /* P10 — plus de plafond : le clip va où on le pousse, et la\n"
    "         timeline le suit. La note ne parle QUE quand la durée change\n"
    "         vraiment (une touche maintenue vaut 30 pas par seconde). */\n"
    "      var ns=Math.max(0,c.start+fr/30);\n"
    "      ns=Math.round(ns*3000)/3000; /* multiple exact d'1/30 s : zéro dérive */\n"
    "      if(Math.abs(ns-c.start)<1e-6)return;\n"
    "      var dzNd=DzTracks.fitDur([{end:ns+len}],d,0);\n"
    "      var now=Date.now();\n"
    "      if(now-nudgeHistAt.current>600)pushHistory();\n"
    "      nudgeHistAt.current=now;\n"
    "      setClips(clipsRef.current.map(function(k){\n"
    "        return k.id===c.id?Object.assign({},k,{start:ns,end:ns+len}):k}));\n"
    "      if(dzNd>d){setProj(function(p){"
    "return Object.assign({},p,{dur:dzNd})});\n"
    "        fireNote(\"Timeline allongée à \"+svmRuler(Math.round(dzNd))+\n"
    "          \" : « \"+(c.label||\"le clip\")+\" » dépasse la fin du projet, \"+\n"
    "          \"et n'a PAS été rogné pour autant. « Annuler » le ramène en \"+\n"
    "          \"place mais NE raccourcit PAS la timeline — le \"+\n"
    "          \"réglage de durée, à côté du zoom, la reprend.\")}\n"
    "      setDirty(!0)},\n")

# ── M17c (P10) : `ripMax` disparaît avec le plafond qu'il servait ───────────
# MESURE : `ripMax` apparaît CINQ fois dans le bundle — sa déclaration, deux
# emplois dans ce forEach, et DEUX dans la ligne de plafond que M17d
# supprime. Le laisser aurait été un calcul mort dans une fermeture rejouée à
# chaque pointerdown de clip. Après M17c + M17d, `ripMax` vaut 0 dans le
# bundle, et le banc le compte.
# LE COMMENTAIRE POSÉ DANS LE BUNDLE NE NOMME PAS `ripMax`, ET C'EST VOULU :
# il est EXPÉDIÉ AU NAVIGATEUR, et le banc compte l'identifiant à ZÉRO dans le
# fichier livré — une mention en commentaire aurait rendu ce compte impossible,
# ou l'aurait obligé à décrire sa propre exception. Le raisonnement vit ici, en
# Python, où il ne coûte rien à l'utilisateur (même règle que R_M16REF).
A_M17C = ('    var rip=ripple&&c.tr==="v1"&&edge==="r",orig={},ripMax=0;\n'
          '    if(rip)clipsRef.current.forEach(function(k){\n'
          '      if(k.id!==c.id&&k.tr===c.tr&&k.start>=e0-.001){\n'
          '        orig[k.id]={s:k.start,e:k.end};if(k.end>ripMax)ripMax=k.end}});\n')
R_M17C = ('    /* P10 — la fin du dernier plan entraîné ne se calcule plus :\n'
          "       elle ne servait qu'au plafond que M17d supprime. */\n"
          '    var rip=ripple&&c.tr==="v1"&&edge==="r",orig={};\n'
          '    if(rip)clipsRef.current.forEach(function(k){\n'
          '      if(k.id!==c.id&&k.tr===c.tr&&k.start>=e0-.001){\n'
          '        orig[k.id]={s:k.start,e:k.end}}});\n')

# ── M17d (P10) : le bord droit n'est plus plafonné ─────────────────────────
A_M17D = ('      if(edge==="r"){\n'
          '        var lim=durRef.current;\n'
          '        if(rip&&ripMax>0)lim=Math.min(lim,e0+(durRef.current-ripMax));\n'
          '        w=Math.max(s0+.3,Math.min(lim,doSnap(e0+ds)));delta=w-e0}\n')
R_M17D = ('      if(edge==="r"){\n'
          "        /* P10 — plus de plafond ni de limite de ripple : c'est\n"
          "           `up()` qui rallonge la timeline AU RELÂCHEMENT. */\n"
          '        w=Math.max(s0+.3,doSnap(e0+ds));delta=w-e0}\n')

# ── M17e (P10) : le déplacement n'est plus plafonné ────────────────────────
A_M17E = '          ns=Math.min(durRef.current-len,Math.max(0,ns));\n'
R_M17E = ('          /* P10 — le clip va où on le tire ; `up()` étend. */\n'
          '          ns=Math.max(0,ns);\n')

# ── M17f (P10) : le relâchement ajuste la durée, et le DIT ─────────────────
# POURQUOI AU RELÂCHEMENT ET PAS PENDANT LE GESTE — c'est la mesure qui
# décide, pas le goût. `pxPerS` est capturé UNE fois au pointerdown
# (`rect.width/durRef.current`) et `mv` s'en sert pour traduire les pixels en
# secondes. Une durée qui grandirait PENDANT le glissement re-rendrait les
# bandes à une autre échelle (les clips sont positionnés en
# `left:c.start/dur*100+"%"`) sans que `pxPerS` bouge : le clip se
# décrocherait du curseur, de plus en plus loin. En étendant au relâchement,
# le geste reste exact au pixel et la timeline se recale une seule fois.
# Pendant le geste, le clip dépasse visiblement la fin de la règle — c'est
# précisément ce qu'on veut montrer.
#
# `DzTracks.fitDur(clipsRef.current, …)` prend TOUS les clips, pas seulement
# celui qu'on tire : en mode ripple, ce sont les plans ENTRAÎNÉS qui sortent
# du champ, jamais celui qu'on rogne.
#
# `pushHistory(h0)` reste APRÈS, et à l'identique : il mémorise l'état du
# pointerdown, donc {clips, mixDb} — pas la durée. La note le dit.
A_M17F = ('    function up(){tgt.removeEventListener("pointermove",mv);'
          'tgt.removeEventListener("pointerup",up);\n'
          '      setSnapT(null);\n'
          '      if(moved){setDirty(!0);pushHistory(h0)}}\n')
R_M17F = (
    '    function up(){tgt.removeEventListener("pointermove",mv);'
    'tgt.removeEventListener("pointerup",up);\n'
    '      setSnapT(null);\n'
    '      if(moved){setDirty(!0);pushHistory(h0);\n'
    "        /* P10 — la timeline rattrape ce que le geste a poussé dehors.\n"
    "           TOUS les clips, pas seulement celui qu'on tient : en ripple,\n"
    "           ce sont les plans ENTRAÎNÉS qui sortent du champ. */\n"
    '        var dzUd=DzTracks.fitDur(clipsRef.current,durRef.current,0);\n'
    '        if(dzUd>durRef.current){var dzU0=durRef.current;\n'
    '          setProj(function(p){return Object.assign({},p,{dur:dzUd})});\n'
    '          fireNote("Timeline allongée de "+svmRuler(Math.round(dzU0))+'
    '" à "+\n'
    '            svmRuler(Math.round(dzUd))+" : le geste dépassait la fin du "+\n'
    '            "projet, et rien n\'a été rogné. « Annuler » rend les clips "+\n'
    '            "mais NE raccourcit PAS la timeline — le réglage de durée, "+\n'
    '            "à côté du zoom, la reprend.")}}}\n')

# ── M17g (P10) : le réglage explicite de la durée, dans le transport ───────
# L'ANCRE est la QUEUE de l'expression du zoom : `" % · "+svmRuler(…)+
# " total"]}),`, comptée 1 dans le bundle livré et dans .bak_montage. Le
# nombre affiché n'est pas supprimé — il DÉMÉNAGE dans le contrôle, entouré
# des deux boutons qui le règlent. Le séparateur « · » passe dans la feuille
# (`.dzm-durctl::before`) : laissé dans la chaîne, il aurait pendu tout seul
# le jour où le contrôle ne rendrait rien.
#
# LES CINQ IDENTIFIANTS DU BUNDLE QUE CETTE SECTION APPELLE sont gardés à
# DEUX FACES par le banc (déclaration ET appel, recherche bornée) : `dur`,
# `tickStep`, `clips`, `setProj`, `setDirty`, `fireNote`. `tickStep` est
# déclaré ~1 300 lignes plus haut DANS LE MÊME corps de composant — mesuré,
# pas supposé.
#
# LE PAS EST `tickStep`, LA GRADUATION QUE LA RÈGLE DESSINE DÉJÀ. Ce n'est
# pas un chiffre choisi : c'est celui que le bundle calcule pour ses propres
# traits (`[2,3,5,6,10,15,20,30,60].find(function(s){return dur/s<=11})||60`),
# donc un clic = un trait, à toutes les échelles. Le détail des bornes est
# dans la couche, au-dessus de `dzmDurCtl`.
A_M17G = '" % · "+svmRuler(Math.round(dur))+" total"]}),'
R_M17G = ('" %"]}),\n'
          '        /* P10 — la durée du projet CESSE D\'ÊTRE UN AFFICHAGE. Elle\n'
          '           s\'allonge et se raccourcit ici, d\'une graduation de la\n'
          '           règle à la fois ; raccourcir sous la fin du dernier clip\n'
          '           est REFUSÉ, jamais fait en silence. Le geste n\'entre pas\n'
          '           dans l\'historique (qui ne porte que {clips, mixDb}) et\n'
          '           chaque note le dit — le retour, c\'est ce contrôle. */\n'
          '        DzTracks.durCtl({dur:dur,step:tickStep,clips:clips,\n'
          '          onSet:function(v){setProj(function(p){'
          'return Object.assign({},p,{dur:v})});setDirty(!0)},\n'
          '          note:fireNote}),')

PATCHES = [("M3-tracks", A_M3, R_M3), ("M4-bus", A_M4, R_M4),
           ("M4b-setter", A_M4b, R_M4b),
           ("M5-payload", A_M5, R_M5), ("M6-save", A_M6, R_M6),
           ("M7-apply", A_M7, R_M7), ("M8-toolbar", A_M8, R_M8),
           ("M9a-head-audio", A_M9a, R_M9a), ("M9b-head-video", A_M9b, R_M9b),
           ("M11-text-state", A_M11, R_M11), ("M12-text-panel", A_M12, R_M12),
           ("M13-grade-all", A_M13, R_M13),
           ("M16ref-tracks-ref", A_M16REF, R_M16REF),
           ("M16a-piste-existante", A_M16A, R_M16A),
           ("M16b-note-piste", A_M16B, R_M16B),
           ("M16c-picker-filtre", A_M16C, R_M16C),
           ("M16d-marque-non-video", A_M16D, R_M16D),
           # P6. Le plan les nomme « M15 » et « M16 » ; le second porte ici un
           # suffixe parce que les cinq sections de P9 occupent DÉJÀ les noms
           # M16ref/M16a…M16d (la tâche 16 du plan, pas la section 16 de ce
           # patcher). Deux étiquettes identiques dans cette liste rendraient
           # illisibles les lignes de test_montage_bundle.py, qui les reprend.
           ("M15-remplace-mode", A_M15, R_M15),
           ("M15b-picker-arme", A_M15B, R_M15B),
           ("M16src-inspecteur-source", A_M16, R_M16),
           # P10 — la timeline s'étend au lieu de rogner.
           ("M17a-ajout-etend", A_M17A, R_M17A),
           ("M17b-nudge-etend", A_M17B, R_M17B),
           ("M17c-ripmax-mort", A_M17C, R_M17C),
           ("M17d-bord-droit-etend", A_M17D, R_M17D),
           ("M17e-deplacement-etend", A_M17E, R_M17E),
           ("M17f-relachement-ajuste", A_M17F, R_M17F),
           ("M17g-transport-duree", A_M17G, R_M17G)]


def nl(text, crlf):
    """Aligne les fins de ligne d'un fragment sur celles du fichier cible.

    Le bundle est un mélange : la partie minifiée n'a pas de saut de ligne,
    les blocs injectés (sonvfx, sfxstudio, vfxrack) sont en CRLF — git
    normalise les sources du dépôt à la sortie. Une ancre écrite en LF ne
    matcherait donc jamais : on la convertit avant toute comparaison.
    """
    t = text.replace("\r\n", "\n")
    return t.replace("\n", "\r\n") if crlf else t


def apply(s, anchor, replacement, tag):
    """Remplacement assert-gardé : l'ancre doit exister exactement une fois."""
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_text(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def write_text(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def patch_html(html, strip):
    """Lien /shared/montage.css — idempotent, indépendant du bundle."""
    ins = nl(CSS_INSERT, "\r\n" in html)
    if strip:
        if "shared/montage.css" in html:
            return html.replace(ins, "").replace(ins.strip(), ""), "lien css retiré"
        return html, ""
    if "shared/montage.css" in html:
        return html, ""
    if html.count(CSS_ANCHOR) != 1:
        raise SystemExit(f"[{TAG}] ancre css introuvable ou multiple. Aborting.")
    return html.replace(CSS_ANCHOR, CSS_ANCHOR + ins), "lien css ajouté"



def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est deja passe.

    CE MAILLON RESTAURE SON .bak PUIS REAPPLIQUE : sans cette garde, le
    relancer seul remet le bundle a l'etat d'AVANT lui et efface EN SILENCE
    tout ce que les maillons suivants ont ecrit. Mesure sur la chaine du
    2026-08-11 : materialforge seul = 23 couples ancre->remplacement detruits
    (21 in-bloc vfxrack/subs + 2 cardforge), vfxrack seul = 17, subs seul = 8.
    Le bundle reste syntaxiquement valide, tous les marqueurs BEGIN/END
    restent la, `node --check` passe : c'est exactement le mode de panne qui a
    deja coute 22 correctifs a ce depot. `--force-unchained` la desarme —
    c'est ce que passe repatch_all.py quand il rejoue TOUTE la chaine dans
    l'ordre.
    """
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). Le relancer seul effacerait ce que "
                "les maillons suivants ont ecrit — sans un mot. Rejouer la "
                "chaine entiere (repatch_all) ou forcer avec "
                "--force-unchained en connaissance de cause.")


def main():
    args = sys.argv[1:]
    root = pathlib.Path(".")
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    check = "--check" in args
    strip = "--strip" in args

    bundle = root / REL_BUNDLE
    html_path = root / REL_HTML
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    if not html_path.is_file():
        raise SystemExit(f"[{TAG}] index.html introuvable : {html_path}")
    if not PATCH_SRC.is_file():
        raise SystemExit(f"[{TAG}] source introuvable : {PATCH_SRC}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)

    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        # Contrôle à sec : on valide les ancres sur l'état PRÉ-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien écrire.
        src = bak if bak.exists() else bundle
        s, _ = read_text(src)
        crlf = "\r\n" in s
        if s.count(ANCHOR_INJECT) != 1:
            raise SystemExit(
                f"[M1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1) "
                f"dans {src.name}. Aborting.")
        for tag, anchor, _repl in PATCHES:
            n = s.count(nl(anchor, crlf))
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. Aborting.")
        print(f"[{TAG}] applicable sur {src} ({len(PATCHES) + 1} ancres OK)")
        return

    if strip:
        s, bom = read_text(bundle)
        done = []
        if BEGIN in s:
            head, rest = s.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            s = head.rstrip("\n") + tail.lstrip("\n")
            done.append("bloc retiré")
        if bak.exists():
            shutil.copy2(bak, bundle)
            done.append("bundle restauré depuis le .bak")
        else:
            write_text(bundle, s, bom)
        html, hbom = read_text(html_path)
        html, hmsg = patch_html(html, True)
        if hmsg:
            write_text(html_path, html, hbom)
            done.append(hmsg)
        print(f"[{TAG}] strip — {', '.join(done) or 'rien à faire'}")
        return

    if not bak.exists():
        shutil.copy2(bundle, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, bundle)

    s, bom = read_text(bundle)
    crlf = "\r\n" in s
    # M1 — injection de la couche, juste après le bloc subs
    component = PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = nl("\n" + BEGIN + "\n" + component + "\n" + END, crlf)
    if s.count(ANCHOR_INJECT) != 1:
        raise SystemExit(
            f"[M1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1). Aborting.")
    s = s.replace(ANCHOR_INJECT, ANCHOR_INJECT + block)
    # M3..M9 — ancres du bloc sonvfx (source injectée)
    for tag, anchor, repl in PATCHES:
        s = apply(s, nl(anchor, crlf), nl(repl, crlf), tag)
    write_text(bundle, s, bom)

    # M2 — feuille de style (index.html, hors chaîne des .bak)
    html, hbom = read_text(html_path)
    html, hmsg = patch_html(html, False)
    if hmsg:
        write_text(html_path, html, hbom)

    print("OK — bundle patché (pistes dynamiques : ordre, ajout, retrait, "
          "bus resynchronisé). Size:", bundle.stat().st_size,
          "| index.html:", hmsg or "inchangé")


if __name__ == "__main__":
    main()
