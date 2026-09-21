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
  M8  barre de transport. ELLE A ÉTÉ VIDÉE PAR L'ÉTAPE 6 DU HANDOFF « Barre
      Outils Flottante » (§5.1) : elle posait « + piste vidéo » / « + piste
      audio », « Bibliothèque… », la chip « mot » et ses trois options,
      « emoji », « texte » et « projets » — les NEUF contrôles que le §5.1
      retire. Ils vivent désormais dans la barre flottante (M19), où l'étape 7
      les a câblés sur LES MÊMES actions. Il ne reste ici que la LISTE des
      projets, montée NUE : ce n'est pas un contrôle, c'est le panneau qu'un
      contrôle de la barre ouvre ;
  M9a/M9b en-tête de piste : poignée de glisser-déposer et ▲ ▼ ×, posés en
      SURIMPRESSION (l'en-tête fait 88 × 40–54 px et il est plein — mesuré,
      voir montage.css) ;
  M10 (P2) chip « mot : couleur / rebond / glow » + bouton « emoji » — RETIRÉS
      par l'étape 6 (§5.1). Ils vivaient DANS le remplacement de M8 ;
  M11 (P3) l'ÉTAT du panneau « Texte » (`dzTextOn`), déclaré dans le corps du
      composant — il RESTE, c'est M12 qui le lit ; son bouton de barre, lui,
      est parti avec les huit autres (M11b, étape 6) ;
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
      M8. M6 et M7 y gagnent la clé `project_id`, qui relie le brouillon
      courant à son projet. ÉTAPE 6 DU HANDOFF « Barre Outils Flottante » : il
      est monté NU (`nu:!0`) — son BOUTON a quitté le bandeau avec les huit
      autres, sa LISTE reste parce que c'est elle que la barre demande.
  M16 (P9) « Bibliothèque… », et la remise qui se perdait — quatre sections
      plus un repli :
        M16-lib  le bouton « Bibliothèque… » de la barre de transport —
                 RETIRÉ par l'étape 6 du handoff « Barre Outils Flottante »
                 (§5.1) ; c'est la barre flottante qui ouvre `openPicker` sur
                 la piste vidéo RÉSOLUE, par la même expression ;
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
  M19 l'onglet OUTILS et la barre flottante montés dans le bandeau ; depuis
      l'étape 8 elle passe aussi `toggleReq` (la demande de bascule du
      raccourci) et `keyLbl` (la combo VIVANTE, lue par `svmKeyLabel`) ;
  M20a/M20b (étape 8, §4.1) LE RACCOURCI, inscrit dans le mécanisme
      existant : une entrée de plus dans `SVM_ACTIONS` — donc remappable via
      `dz_svm_keymap` et LISTÉE dans le panneau « ? » — et sa branche dans la
      chaîne de dispatch du gestionnaire clavier. `T` est DÉJÀ PRIS par
      `narration` (mesuré) : la touche est `O`, l'initiale du libellé
      verbatim de l'onglet, mesurée libre. Voir le commentaire de A_M20A ;
  M21 (étape 8, §4.5) les trois `aria-label` des chips de coupe, dont le
      libellé passe en glyphe seul sous largeur réduite ;
  M22a/M22b/M22c/M23 (P12) LE SON D'UN PLAN SUIT SA VIDÉO : une vidéo
      posée sur une piste vidéo plein cadre reçoit un clip jumeau sur la
      piste de dialogue (sonde GET /has-audio, cache, un seul historique,
      un seul concat), les identifiants de clips deviennent uniques au
      chargement, et l'inspecteur gagne « Extraire le son → A1 » pour
      les plans déjà posés. R_M17A porte la sonde. Voir le bloc P12.
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

  H1…H7 (D-0, 21/09/2026) L'HISTORIQUE COMPLET. Ctrl+Z ne rendait que
      {clips, mixDb} ; il rend désormais AUSSI les pistes, la durée, le style
      des sous-titres, la plage et les marqueurs. Le cœur est PUR et vit dans
      la couche (`DzTracks.histSnap` / `histApply`) ; SIX sections et un pli
      le branchent :
        H1 `dzProjRef` (le projet relu à chaque rendu — `pushHistory`, `undo`
           et `redo` sont des useCallback à dépendances VIDES, ils ne voient
           jamais `proj`), `dzmHistHost()` qui en tire l'instantané, et les
           deux horloges de rafale `dzStyleHistAt` / `dzDurHistAt` ;
        H2 `pushHistory()` sans argument empile l'instantané COMPLET ;
        H3 `undo` et H4 `redo` restaurent tout l'instantané — corps entiers en
           ancre (`setClips(s.clips);` seul apparaît deux fois), clips rendus
           par `if("clips" in s)` (histApply ne les touche pas : ils vivent
           dans `clipsRef`, pas dans `proj`), et `svmTrackBusSync` resynchronisé
           sur les pistes revenues ;
        H5 le `h0` du glisser de clip capture l'état ENTIER — sans quoi le
           relâchement de M17f, qui ALLONGE la durée, empilait un h0 sans
           `dur` et « Annuler » rendait les clips mais pas la timeline ;
        « H6 » — le réglage explicite de durée — n'est PAS une section : son
           ancre serait posée par R_M17G, donc invisible de `--check` et
           absente du compte générique du banc. Le geste est REPLIÉ dans
           R_M17G (même motif que M10 dans R_M8) ;
        H7 le style S1 (`subsStyleSet`) entre dans l'historique. Comme le
           réglage de durée : une entrée par rafale de 600 ms — même fenêtre
           que `nudgeHistAt` (M17b).
      Les six phrases de l'écran qui disaient la réserve d'historique sont
      réécrites en conséquence (montage.js : DZM_DUR_UNDO, DZM_TB_H_CLIPS,
      DZM_TB_H_PISTE, DZM_TB_H_STYLE ; ici : R_M17A, R_M17B, R_M17F, et le
      commentaire de R_M17G). Pas de H8 : `svmTracksSet` appelle DÉJÀ
      `pushHistory()`, les pistes entrent d'elles-mêmes.

  R1/R2/R3 (D-11, 21/09/2026) LA PLAGE D'ENTRÉE / SORTIE. Quatre actions de
      plus dans SVM_ACTIONS — I, U, X et Maj+X — donc remappables via
      `dz_svm_keymap` et LISTÉES dans le panneau « ? », comme les autres (R1).
      La branche de dispatch (R2) calcule la plage suivante AVANT de rien
      pousser et SORT TÔT si elle n'a pas changé : une frappe stérile n'empile
      ni historique ni « NON ENREGISTRÉ ». Une demi-plage se dit par une note,
      la règle restant muette tant que les deux bouts ne sont pas posés.
      La bande sur la règle (R3) est montée juste après la gouttière.
      « R4 » (la clé `range` de la sauvegarde) et « R5 » (celle de la
      restauration) ne sont PAS des sections : elles sont REPLIÉES dans R_M6 et
      R_M7, dont elles visaient un texte POSÉ — comme `project_id` de M14 l'est
      déjà. Le cœur est pur et vit dans la couche (`DzTracks.rangeSet` /
      `rangeFrom` / `rangeLen` / `RangeBar`), avec `cutOpts`, les options de
      coupe que R2 et le tiroir Texte (M12) partagent désormais.

  « E1 » / « E2 » / « E3 » (D-2, 21/09/2026) LE CÂBLAGE DES MODES D'ÉDITION
      N'EST PAS FAIT DE SECTIONS, et c'est une MESURE qui l'impose : les trois
      textes qu'il vise valent **0 dans index-BEOJX8L5.js.bak_montage** (l'ENTRÉE
      de ce patcher, la seule qui décide) et 1 dans le bundle livré — ils
      n'existent QUE parce que trois remplacements les créent :
        · `var dzTracksRef=x.useRef(null);dzTracksRef.current=svmTracksOf(proj);`
          est écrit par R_M16REF ;
        · `:("Ajouter sur la piste "+tr2.toUpperCase())}),` par R_M15B ;
        · `setClips(clipsRef.current.concat(dzTw&&dzTw.clip?…))` par R_M22B.
      Une section à part serait donc REFUSÉE par `--check` (ancre à 0). Le
      câblage est REPLIÉ dans les remplacements qui créent l'ancre — la règle
      de la maison, déjà suivie par H6 (dans R_M17G) et R4/R5 (dans R_M6 /
      R_M7). LE COMPTE D'ANCRES RESTE 75. L'état du mode vit dans R_M16REF
      (« E1 » : `dzMode` + `dzModeRef`), la rangée de six chips dans R_M15B
      (« E2 » : `DzTracks.ModeBar`), et l'écriture du clip passe par
      `DzTracks.insere` dans R_M22A / R_M22B (« E3 »). R_M17A cède à R_M22A
      le calcul de l'allongement de la timeline : il doit désormais se mesurer
      sur les clips RENDUS par l'insertion, puisqu'en `inserer` / `fin` /
      `ripple_ecraser` la suite de la piste est POUSSÉE au-delà de `en`.
      « E4 » (tour de correction du 21/09/2026) EST, LUI, UNE VRAIE SECTION :
      son ancre — la garde de verrou qui testait la piste VISÉE — vient du
      greffon AMONT son-vfx-montage.js et vaut donc 1 dans .bak_montage
      (mesuré). Elle est DÉPLACÉE dans `insere()`, qui seul connaît la piste
      RÉELLE : en « au-dessus » avec V1 verrouillée et V2 libre, le geste
      était refusé alors que RIEN n'allait sur V1. Le compte d'ancres passe
      donc de 75 à 76, et `PATCHES` de 74 à 75 triplets.

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
        "      project_id:proj.project_id,\n"
        # D-11 (21/09/2026) — LA PLAGE PART AVEC LA SAUVEGARDE. C'est la
        # section « R4 » du plan, REPLIEE ici : son ancre
        # (`      project_id:proj.project_id,`) est un texte que CE
        # remplacement-ci POSE. MESURE sur .bak_montage (etat pre-patch, le
        # seul que `--check` regarde) : compte 0, donc une section a part
        # aurait abandonne au premier `--check` et aurait fait tomber
        # `M6-save_remplace` a 0 dans le banc du bundle. Meme technique que
        # H6 dans R_M17G, M10 dans R_M8 et M9c dans R_M9b.
        # `rangeFrom` ASSAINIT avant l'envoi : une plage a moitie posee (I
        # sans U) ou inversee part en `null`, et le backend n'a pas a s'en
        # defendre deux fois.
        "      range:DzTracks.rangeFrom(proj.range),\n"
        # D-5 (21/09/2026) -- LES MARQUEURS PARTENT AVEC LA SAUVEGARDE.
        # « K6 » du plan, REPLIE ici pour la meme raison que R4 : son ancre
        # est la ligne `range:` que CE remplacement pose (0 dans le .bak).
        # LA LISTE PART TELLE QUELLE, et une liste VIDE part aussi : le
        # backend ne stocke alors PAS la cle, donc un montage dont on vient
        # de retirer le dernier marqueur revient bien SANS marqueur -- la
        # cle absente et la liste vide disent la meme chose, et c'est voulu.
        # L'assainissement est fait DEUX FOIS (le backend au POST,
        # `markersFrom` au GET) : le payload n'est pas de confiance.
        "      markers:(proj.markers||[]),")

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
        # D-11 — ET LA PLAGE REVIENT AVEC LE PROJET. « R5 » du plan,
        # REPLIEE pour la meme raison que R4 : l'ancre du plan est le
        # texte `v1NonVideo:…` que CE remplacement pose (compte 0 dans
        # .bak_montage, mesure du 21/09/2026).
        'range:DzTracks.rangeFrom(d.range),'
        # D-5 -- ET LES MARQUEURS REVIENNENT AVEC LE PROJET. « K6 », seconde
        # moitie, REPLIEE pour la meme raison que R5. `markersFrom` REGENERE
        # les identifiants (m1..mN) : deux marqueurs d'un vieux fichier
        # pouvaient porter le meme, et `markerRemove` en aurait retire deux.
        'markers:DzTracks.markersFrom(d.markers),'
        'name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",')

# ── M8 : barre de transport ─────────────────────────────────────────────────
A_M8 = ('r.jsx("button",{className:"svm-tbtn",title:"Raccourcis ("'
        '+svmKeyLabel("keys_panel")+") — personnalisables",')

# ── M10 (P2) : LA CHIP « mot » ET LE BOUTON « emoji » — RETIRÉS DU BANDEAU
# ÉTAPE 6 DU HANDOFF (§5.1). Ils vivaient DANS R_M8 ; ils n'y sont plus, et
# ils ne sont remplacés par rien ICI : les quatre actions (`couleur`,
# `rebond`, `glow`, `emoji`) sont câblées dans la barre flottante depuis
# l'étape 7 — R_M19 leur passe `wordAnim`/`onWordAnim` et
# `emojiSegs`/`note`/`onEmojiAdd`, exactement les mêmes expressions que
# celles qui étaient écrites ici. Le §5.1 l'exige : « Ne pas les laisser en
# double. Un contrôle présent aux deux endroits […] crée deux sources de
# vérité pour l'état des bascules. »
# CE QUE CE RETRAIT REFERME, en plus de la place : le DOUBLON D'ATTENTE de
# la requête emoji. `dzmEmojiGo` n'a pas de hook, chaque porte tenait le
# sien — celui de `DzmEmojiBtn` et celui du Dock. Une porte disparaît, une
# attente disparaît avec elle.
# `DzmWordAnimChip` et `DzmEmojiBtn` RESTENT DANS LA COUCHE et au contrat :
# ce sont des composants publics et testés, et le §5.1 retire des contrôles
# DU BANDEAU, pas des composants d'une bibliothèque. Reste assumé, dit ici :
# deux composants exportés ne sont plus montés nulle part.

A_M11 = "  var stSu=x.useState(!1),subsOn=stSu[0],setSubsOn=stSu[1];"
# ÉTAPE 7 DU HANDOFF « Barre Outils Flottante » (§6) — DEUX DÉCLARATIONS DE
# PLUS, ET ELLES SONT ICI POUR LA MÊME RAISON QUE `dzTextOn` : un hook et une
# fonction se déclarent dans le CORPS du composant, pas dans un tableau
# `children`. Cette ancre est la seule de la chaîne qui soit dans le corps.
#   `dzEmoAdd` — L'AJOUT DES CLIPS D'EMOJI : `pushHistory()` PUIS l'ajout,
#     donc « annuler » les retire d'un coup. Elle servait les DEUX portes
#     (le bouton du bandeau et la barre) ; l'étape 6 a retiré la première,
#     et il n'en reste qu'une. La déclaration ne bouge pas : c'est toujours
#     depuis le corps du composant que la barre la reçoit, et la sortir
#     d'ici pour la recopier dans R_M19 aurait refait deux sources pour un
#     seul geste.
#   `dzProjReq` — LA DEMANDE D'OUVERTURE de la liste des projets, un
#     COMPTEUR. Le popover garde son état d'ouverture chez lui (il se ferme
#     sur un `mousedown` hors de sa boîte) ; un booléen piloté de l'extérieur
#     serait remis à faux par ce `mousedown` juste avant que le `click` le
#     remène à vrai. Un compteur n'a pas d'ordre à respecter : il DEMANDE.
# LES NOMS SONT MESURÉS LIBRES dans le bundle livré, comme `stDzTx` l'avait
# été : `stDzPj`, `dzProjReq`, `setDzProjReq`, `dzEmoAdd` — zéro occurrence
# chacun le 06/09/2026. Un `var` de même nom qu'un identifiant minifié
# existant l'écraserait en silence.
R_M11 = ("  /* P3 — panneau « Texte » (monter en LISANT). Son état est À LUI :\n"
         "     il ne vit pas dans la zone des tiroirs (Sons / Narration /\n"
         "     Sous-titres, mutuellement exclusifs) mais dans la COLONNE\n"
         "     D'INSPECTION, où il ne dispute sa place à personne. */\n"
         "  var stDzTx=x.useState(!1),dzTextOn=stDzTx[0],setDzTextOn=stDzTx[1];\n"
         "  /* étape 7 du handoff « Barre Outils Flottante » (§6) : la demande\n"
         "     d'ouverture de la liste des projets (un COMPTEUR, pas un\n"
         "     booléen — le popover se ferme seul sur le clic qui l'ouvre),\n"
         "     et l'ajout des emoji, PARTAGÉ par le bouton du bandeau et la\n"
         "     barre : `pushHistory()` puis l'ajout, donc « annuler » les\n"
         "     retire d'un coup. */\n"
         "  var stDzPj=x.useState(0),dzProjReq=stDzPj[0],"
         "setDzProjReq=stDzPj[1];\n"
         "  function dzEmoAdd(cs){pushHistory();"
         "setClips(function(k){return (k||[]).concat(cs)});setDirty(!0)}\n"
         "  /* étape 8 du handoff (§4.1) : LA DEMANDE DE BASCULE de la barre\n"
         "     d'outils, un COMPTEUR pour la même raison que `dzProjReq` —\n"
         "     l'état d'ouverture appartient au Dock, qui le persiste ; un\n"
         "     booléen piloté d'ici en aurait fait une seconde source. C'est\n"
         "     M20b, la branche du gestionnaire clavier, qui l'incrémente. */\n"
         "  var stDzTb=x.useState(0),dzTbReq=stDzTb[0],"
         "setDzTbReq=stDzTb[1];\n"
         + A_M11)

# ── M20a (étape 8, §4.1) : LE RACCOURCI, INSCRIT DANS LE MÉCANISME EXISTANT
# LE POINT DUR DE CETTE ÉTAPE, ET IL EST TRANCHÉ PAR LA MESURE. Le §4.1
# demande `T`. MESURÉ dans le bundle livré le 06/09/2026 : `SVM_ACTIONS`
# porte TRENTE-DEUX actions, et `{id:"narration",sec:"Affichage",…,combo:"T"}`
# tient déjà `T` — le panneau Narration (texte → voix). Le §5 du brief
# déconseille de la lui reprendre sans l'accord de l'utilisateur, et il a
# raison : `narration` est une action VIVANTE de cet écran, son raccourci est
# affiché dans le panneau « ? » et un utilisateur l'a peut-être dans les
# doigts. On ne le vole pas.
# LA TOUCHE RETENUE EST `O` — l'initiale du libellé VERBATIM de l'onglet,
# `OUTILS` (§2.1). Elle est mesurée LIBRE des deux côtés :
#   • aucune des 32 combos de `SVM_ACTIONS` ne vaut « O » (les vingt-six
#     lettres nues occupées sont B D F G J K L M N R S T ; libres : A C E H
#     I O P Q U V W X Y Z) ;
#   • aucune comparaison à la lettre « o » ou au code « KeyO » dans le
#     bundle : les six occurrences de ces motifs sont `subsKeyOf` (cinq) et
#     `arm==="o"+p.id` (une), aucune n'est un raccourci ;
#   • `svmComboReserved("O")` rend "" — ni touche du navigateur, ni Échap,
#     ni Tab, ni Entrée, ni F<n>.
# ELLE EST REMAPPABLE COMME LES AUTRES, et c'est tout l'intérêt de la poser
# ICI plutôt que dans un écouteur inventé à côté : `svmKmLoad` accepte
# désormais l'override `{"toolbar":"…"}` (elle rejette tout id absent de
# `SVM_ACTION_BY_ID`), `svmKmMerge` la fait entrer dans `toAct`, et
# `kbPanel` la LISTE — elle boucle sur `SVM_ACTIONS` sans filtre autre que
# `sounds_drawer`. Un raccourci qui ne serait pas dans cette table serait
# invisible du panneau, donc introuvable.
# SECTION `Affichage`, JUSTE AVANT `keys_panel` : c'est la section des
# panneaux qu'on ouvre et qu'on ferme, celle où vivent déjà `narration` et
# le panneau des raccourcis lui-même.
A_M20A = (' {id:"keys_panel",sec:"Affichage",lbl:"ouvrir / fermer ce panneau",'
          'combo:"?"},')
R_M20A = (' {id:"toolbar",sec:"Affichage",'
          'lbl:"barre d\'outils de création (onglet OUTILS)",combo:"O"},\n'
          + A_M20A)

# ── M20b (étape 8, §4.1) : LA BRANCHE DE DISPATCH
# Le gestionnaire clavier de l'écran est une chaîne de `if(id==="…")` ; une
# action déclarée sans branche serait un raccourci mort, listé dans le
# panneau et sans effet — exactement ce que ce chantier refuse.
# ELLE N'OUVRE PAS LA BARRE, ELLE LA DEMANDE : `setDzTbReq` incrémente le
# compteur de M11, que M19 passe au Dock. L'état d'ouverture reste dans le
# Dock, qui le persiste dans `dz_svm_tb_open` — une seule source.
# `setDzTbReq` est un setter de `useState` : stable d'un rendu à l'autre,
# donc la fermeture de `onKey` (dépendances figées) ne le voit jamais
# périmé, et la forme fonctionnelle `n+1` ne lit aucune valeur capturée.
A_M20B = '      if(id==="narration"){narrToggle();return}'
R_M20B = (A_M20B + "\n"
          "      /* étape 8 du handoff « Barre Outils Flottante » (§4.1) :\n"
          "         la barre d'outils de création. DEMANDE, pas ordre — le\n"
          "         Dock tient l'état et le persiste. */\n"
          '      if(id==="toolbar"){'
          'setDzTbReq(function(n){return n+1});return}')

# ── M21 (étape 8, §4.5) : LE NOM ACCESSIBLE DES TROIS CHIPS DE COUPE
# « La couleur n'est jamais le seul porteur d'information » — et la FORME non
# plus. L'étape 6 passe ces trois chips en GLYPHE SEUL sous largeur réduite
# (`font-size:0` + `::before`, montage.css l.839-849) et elle a consigné leur
# nom accessible comme reposant « sur leur `title` », non vérifié.
# MESURE DU 06/09/2026, ET ELLE CONTREDIT CETTE NOTE : aucune des trois ne
# porte d'`aria-label` — leur nom vient donc du CONTENU, et `title` n'est
# qu'un REPLI que l'algorithme accname (§4.3.2, étape 2I) n'atteint que si le
# contenu est vide. Or `font-size:0` n'est PAS un mécanisme de masquage : le
# nœud texte reste dans l'arbre d'accessibilité (seuls `display:none`,
# `visibility:hidden`, `hidden` et `aria-hidden` l'en sortent). Le nom
# accessible en mode dégradé n'est donc pas le `title` : c'est le libellé,
# PRÉCÉDÉ du glyphe du `::before` — accname prépend le contenu généré au nom
# calculé depuis le sous-arbre.
# CE QUI RESTE VRAI DE L'INQUIÉTUDE : ce nom-là dépend de deux détails de
# moteur (l'inclusion du contenu généré, historiquement inégale) et il porte
# un caractère de dessin — « ⇥aimanter » plutôt que « aimanter ». D'où ces
# trois `aria-label` EXPLICITES : le nom devient le libellé, identique dans
# les deux modes, indépendant du moteur, et il CONTIENT le texte visible
# (WCAG 2.5.3 « Label in Name »), y compris la combo vivante de « lame »,
# qui suit le remappage comme le fait déjà le contenu.
# LE `title` NE BOUGE PAS : il reste la description, et c'est lui que
# l'infobulle du mode compact affiche (§2.3 : « ne pas livrer un mode compact
# sans infobulles »).
A_M21 = (
    'r.jsxs("div",{className:"svm-toolchips",children:[\n'
    '          r.jsx("button",{className:"svm-toolchip","data-on":snap?"":void 0,\n'
    '            title:"aimanter les bords, la tête et 0 ("'
    '+svmKeyLabel("snap")+")",onClick:function(){setSnap(!snap)},'
    'children:"aimanter"}),\n'
    '          /* la chip AFFICHE la combo vivante — un remappage se lit ici aussi */\n'
    '          r.jsx("button",{className:"svm-toolchip",'
    'title:"couper le clip sélectionné à la tête ("+svmKeyLabel("blade")+")",'
    'onClick:blade,children:"lame · "+svmKeyLabel("blade")}),\n'
    '          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,\n'
    '            title:"refermer les trous — suppression et rognage droit sur V1 ("'
    '+svmKeyLabel("ripple")+")",onClick:function(){setRipple(!ripple)},'
    'children:"ripple"}),')
R_M21 = (
    'r.jsxs("div",{className:"svm-toolchips",children:[\n'
    '          /* étape 8 du handoff « Barre Outils Flottante » (§4.5) : les\n'
    '             trois `aria-label`. Sous largeur réduite ces chips passent\n'
    '             en glyphe seul (`font-size:0` + `::before`) ; sans nom\n'
    '             explicite, leur nom accessible y porterait le caractère de\n'
    '             dessin et dépendrait du moteur. Il reprend le texte\n'
    '             visible, combo vivante comprise. */\n'
    '          r.jsx("button",{className:"svm-toolchip","data-on":snap?"":void 0,\n'
    '            "aria-label":"aimanter",\n'
    '            title:"aimanter les bords, la tête et 0 ("'
    '+svmKeyLabel("snap")+")",onClick:function(){setSnap(!snap)},'
    'children:"aimanter"}),\n'
    '          /* la chip AFFICHE la combo vivante — un remappage se lit ici aussi */\n'
    '          r.jsx("button",{className:"svm-toolchip",'
    '"aria-label":"lame · "+svmKeyLabel("blade"),'
    'title:"couper le clip sélectionné à la tête ("+svmKeyLabel("blade")+")",'
    'onClick:blade,children:"lame · "+svmKeyLabel("blade")}),\n'
    '          r.jsx("button",{className:"svm-toolchip","data-on":ripple?"":void 0,\n'
    '            "aria-label":"ripple",\n'
    '            title:"refermer les trous — suppression et rognage droit sur V1 ("'
    '+svmKeyLabel("ripple")+")",onClick:function(){setRipple(!ripple)},'
    'children:"ripple"}),')

# ── M11b (P3) : le bouton « texte » — RETIRÉ DU BANDEAU (étape 6, §5.1)
# Même raison que M10, et la même contrepartie : la barre porte `texte` avec
# `textOn:dzTextOn` et `onText`, qui basculent le MÊME état. Le panneau
# lui-même (M12) ne bouge pas d'un pixel : c'est sa porte du bandeau qui
# part, pas lui.

# ── M14 (P5) : le popover « projets » — SEUL DES NEUF À RESTER MONTÉ, ET NU
# ÉTAPE 6 (§5.1) : `projets` quitte le bandeau comme les huit autres. Mais ce
# composant est DEUX choses — le bouton ET la liste qu'il ouvre — et la barre
# flottante n'ouvre pas une liste à elle : elle DEMANDE l'ouverture de
# celle-ci (`openReq`, un compteur, cf. l'étape 7). Retirer le nœud entier
# aurait donc rendu MORT le bouton `projets` de la barre, c'est-à-dire rendu
# un des neuf introuvable — exactement ce que le §9 s'interdit.
# D'où `nu:!0` : le BOUTON disparaît, la LISTE reste. Un seul contrôle, une
# seule liste, aucun doublon. La feuille sort alors `.dzm-proj` du flux et
# ancre le popover à DROITE du bandeau, loin de la barre flottante qui vit à
# gauche : sans quoi une liste de 300 px s'ouvrirait par-dessus elle.
# Le reste de cette section est inchangé et sa mesure tient toujours :
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
# TROIS verrous, et c'est le TROISIÈME — le verrou de module — qui rend le
# retrait légitime. test_montage_projets.py [16] joue l'entrelacement avec et
# sans lui — c'est la CONDITION de ce retrait, pas sa confirmation.
# `onBefore` : le bundle désamorce déjà exactement cette course pour le bouton
# « bibliothèque » ; ouvrir un projet et supprimer un projet sont le même cas.
# PAS de `setDirty` ici, et c'est délibéré : au retour de chacune de ces
# routes le serveur a DÉJÀ écrit le courant ET le projet.
# `DzTracks`, pas `DzMontage` : le bundle déclare DÉJÀ une fonction
# `DzMontage` au premier niveau — l'écran Montage lui-même — et redéclarer ce
# nom est une SyntaxError en sémantique MODULE, celle sous laquelle index.html
# charge le bundle. C'est `node_check_module` du miroir qui la voit.
R_M14 = ('r.jsx(DzTracks.Projects,{name:proj.name,projectId:proj.project_id,'
         'note:fireNote,\n'
         '          /* étape 6 (§5.1) : le BOUTON « projets » a quitté le\n'
         '             bandeau ; la LISTE reste, parce que c’est elle que\n'
         '             la barre d’outils demande. Montée NUE. */\n'
         '          nu:!0,\n'
         '          /* étape 7 : la barre d’outils ouvre CETTE liste-ci au\n'
         '             lieu d’en monter une seconde — un compteur, pas un\n'
         '             booléen. */\n'
         '          openReq:dzProjReq,\n'
         '          payload:function(){return svmSavePayload()},\n'
         '          onBefore:function(){'
         'if(saveAbortRef.current){try{saveAbortRef.current.abort()}catch(_e){}}'
         'saveSeqRef.current++;setSaveInfo(null)},\n'
         '          onFail:function(){if(dirty)svmDoSave(++saveSeqRef.current)},\n'
         '          onOpen:function(d){return svmApplyProject(d)},\n'
         '          onNamed:function(pid,nm){setProj(function(p){'
         'return Object.assign({},p,{project_id:pid,name:nm})})}}),')

# ── M16-lib (P9) : le bouton « Bibliothèque… » — RETIRÉ (étape 6, §5.1)
# Même raison que M10 et M11b. La barre porte `bibliotheque` et reçoit
# `onPick:openPicker` — le MÊME `openPicker`, la même piste résolue.
# `DzmLibBtn` reste dans la couche et au contrat, comme `DzmTrackAdd` :
# reste assumé, quatre composants exportés ne sont plus montés.

# ── M8 : CE QUE LA CHAÎNE LAISSE DANS LE BANDEAU ──────────────────────────
# ÉTAPE 6 (§5.1) — IL N'Y RESTE QUE LA LISTE DES PROJETS, ET ELLE EST NUE.
# Cette section posait SIX nœuds : « + piste vidéo » / « + piste audio »
# (`TrackAdd`), « Bibliothèque… », la chip « mot » et ses trois options,
# « emoji », « texte » et « projets ». Neuf contrôles, tous partis dans la
# barre flottante, où l'étape 7 les a câblés un par un sur LES MÊMES actions.
# Ce qui reste ici n'est pas un contrôle : c'est le panneau qu'un contrôle de
# la barre ouvre. Voir M14.
R_M8 = (R_M14 + '\n'
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
         '            var dzO=DzTracks.cutOpts(proj,trackSt);\n'
         '            pushHistory();\n'
         '            /* les mots calés du tiroir, recollés sur LEUR clip : sans\n'
         '               eux, fendre un bloc de narration laisserait la phrase\n'
         '               entière sur les deux moitiés. */\n'
         '            var cs=DzTracks.withWords(clipsRef.current||[],al),rm=0;\n'
         '            rs.forEach(function(p){\n'
         '              var res=DzTracks.rippleCut(cs,p[0],p[1],dzO);\n'
         '              cs=res.clips;rm+=res.removed});\n'
         '            rm=Math.round(rm*1000)/1000;\n'
         '            /* les mots prêtés ne servaient qu\'à répartir le texte :\n'
         '               les garder gonflerait la sauvegarde d\'une copie de\n'
         '               toute la narration, que rien ne relit. */\n'
         '            setClips(DzTracks.dropWords(cs,svmTracksOf(proj)\n'
         '              .filter(function(t){return t.kind===\"subs\"})\n'
         '              .map(function(t){return t.id})));\n'
         '            setDirty(!0);\n'
         '            var vk=Object.keys(dzO.locked);\n'
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

# ── M9a / M9b / M9c : en-tête de piste ───────────────────────────────────────
# Le groupe est un FRÈRE des rangées, pas un membre : il est positionné en
# absolu dans l'en-tête (voir montage.css — l'en-tête fait 88px de large et
# il est déjà plein, c'est mesuré). L'ancre est préfixe du remplacement :
# test_montage_bundle.py ne cherche donc pas à la voir disparaître.
#
# M9c — LE BOUTON D'AJOUT SORT DE SOUS LA SURIMPRESSION. Défaut rapporté par
# l'utilisateur le 05/09/2026 : « sur la piste V1 vidéo, le bouton "ajouter
# une vidéo" est caché par l'overlay de déplacement lorsque la souris passe
# dessus ».
#
# MESURÉ AVANT, dans le bundle LIVRÉ — les quatre rangées d'en-tête et leurs
# contrôles, extraits du fichier que l'application charge :
#     nr  svm-tnamerow  [thType]                 (piste audio)
#     br  svm-thbtns    [+, thM, thS, thLock]    (piste audio)
#     nr  svm-tnamerow  [+]                      (piste vidéo / sous-titres)
#     tr  svm-ttyperow  [thType, thLock]         (piste vidéo / sous-titres)
# Le bouton d'ajout des pistes vidéo/sous-titres est donc le SEUL contrôle
# logé dans la rangée du NOM, qui est la PREMIÈRE de l'en-tête. Or `.dzm-hb`
# est `position:absolute; top:2px; right:3px` (montage.css) dans un
# `.svm-thead` qui empile ses rangées du haut vers le bas, et `.svm-ovadd`
# porte `margin-left:auto` : le bouton est au bord DROIT de la rangée du
# haut, c'est-à-dire exactement le coin que la surimpression occupe. La
# collision est STRUCTURELLE, pas fortuite — et elle ne touche que cette
# famille : sur les pistes audio le même bouton vit dans la rangée du BAS,
# hors d'atteinte.
#
# LA SECONDE BRANCHE DU RAISONNEMENT DE L'UTILISATEUR NE TIENT PAS, et on ne
# la suit pas : la surimpression n'est pas inutile sur V1. Sa croix est bien
# inerte là (`dzmRemove` rend la liste inchangée pour v1 et s1), mais dès
# qu'une piste V2 existe V1 devient réordonnable — poignée et flèches sont
# vivantes. On garde donc la surimpression et on déplace le bouton : c'est la
# PREMIÈRE proposition de l'utilisateur, et elle vaut dans les deux cas.
#
# CE QUE LE DÉPLACEMENT COÛTE, MESURÉ SUR LA CSS. En LARGEUR : le contenu de
# l'en-tête vaut 88 − 2 × 7 de padding = 74px ; la rangée du type passe de
# deux à trois enfants, ses fixes valent verrou 14px (.svm-tkbtn) + bouton
# 16px (.svm-ovadd) + deux gaps de 3px = 36px, il reste donc 38px au libellé
# contre 57 avant. RIEN NE DÉBORDE des 88px : `.svm-minibtn` est `flex:none`
# et la taille minimale automatique tient le bouton à 16px, tandis que
# `.svm-ttyperow .svm-ttype` porte déjà
# `flex:1 1 auto; min-width:0; overflow:hidden; text-overflow:ellipsis` —
# c'est le libellé qui absorbe TOUT le serrage. CE QU'ON PERD, écrit plutôt
# que taise : « overlay/VFX » et « sous-titres » (11 caractères ≈ 51px en
# mono 8px) passent désormais en points de suspension ; « vidéo » (≈ 23px)
# est intouché, et `title:tr.type` porte déjà le libellé entier au survol. En
# HAUTEUR l'en-tête NE GRANDIT PAS : la rangée du nom perd son seul enfant
# de 16px et retombe sur la boîte de ligne du nom (police 10px, donc plus
# courte que 16), pendant que la rangée du type monte de 14 à 16. Le chiffre
# EXACT de cette boîte de ligne n'est pas mesuré ici — il ne se lit qu'à
# l'écran, et c'est porté à la dette navigateur ; ce qui est établi est le
# SENS : − d'un côté, + 2 de l'autre. Aucune règle CSS n'a donc à bouger, et
# aucune n'a bougé.
#
# LE GREFFON DE RÉINSERTION EST REPLIÉ DANS R_M9b, comme M10 dans R_M8 :
# l'ancre A_M9b est déjà consommée par M9b, il n'en reste aucune à quoi
# accrocher une section à part. test_montage_bundle.py porte donc des lignes
# LITTÉRALES qui voient sa disparition — sans elles, le retirer d'ici puis
# rejouer la chaîne laisserait le banc vert.
_HB = ("DzTracks.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,"
       "fireNote)")
A_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),'
R_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),\n                  ' + _HB + ','
A_M9b = 'children:[thType,thLock]},"tr")]}),'
R_M9b = ('children:[thType,thLock,thAdd]},"tr"),\n                  ' + _HB
         + ']}),')
# M9c — le RETRAIT. L'ancre part du nom de la piste pour rester unique : la
# rangée du nom des pistes audio se termine par le même `]},"nr"),` et seul
# le contrôle qui la précède les distingue. L'ancre n'est PAS reprise par le
# remplacement : le miroir exige donc de la voir disparaître.
A_M9c = ('children:tr.name}),\n'
         '                    thAdd]},"nr"),')
R_M9c = 'children:tr.name})]},"nr"),'

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
            # ── « E1 » (D-2) : L'ÉTAT DU MODE D'ÉDITION ──────────────
            # REPLIÉ ICI, et c'est une MESURE : la ligne `dzTracksRef`
            # ci-dessus vaut 0 dans .bak_montage (c'est CE remplacement
            # qui l'écrit) et 1 dans le bundle livré — une section qui la
            # prendrait pour ancre serait refusée par --check. Même motif
            # que H6 dans R_M17G.
            # L'ÉTAT *ET* LA REF, les deux : l'état fait se re-rendre la
            # rangée de chips (E2) ; la ref est ce que lit `addAsset` (E3),
            # qui peut être appelée depuis la fermeture du PREMIER rendu
            # (greffon `__dzMontageAdd`, note P9 juste au-dessus) — lire
            # `dzMode` de là rendrait toujours "ecraser".
            # LE MODE N'EST PAS PERSISTÉ : il vit le temps de l'onglet,
            # comme `ripple` et `snap` du bandeau, et repart à « écraser »
            # au rechargement. C'est le comportement de Resolve, où le mode
            # est un état d'outil et non une propriété du projet.
            '  var stDzM=x.useState("ecraser"),dzMode=stDzM[0],'
            "setDzMode=stDzM[1];\n"
            # -- « K3 » (D-5) : L'INDEX DES MARQUEURS EST-IL OUVERT ? --
            # REPLIE ICI, meme mesure que « E1 » juste au-dessus : la
            # ligne `dzTracksRef` qui sert d'ancre a ce remplacement vaut
            # 0 dans .bak_montage. L'etat vit le temps de l'onglet, comme
            # `dzMode`, `ripple` et `snap` : un panneau ouvert n'est pas
            # une propriete du projet. Pas de ref jumelle, contrairement a
            # `dzModeRef` : personne ne LIT cet etat depuis une fermeture
            # perimee -- K2 et K5 ne font que le BASCULER, par le setter
            # fonctionnel, qui recoit toujours la valeur vivante.
            "  var stDzMk=x.useState(!1),dzMkOn=stDzMk[0],setDzMkOn=stDzMk[1];\n"
            # I-4 (revue du 21/09/2026) : L'INDEX ET LE SELECTEUR D'ASSETS
            # SE RECOUVRAIENT. Les deux sont des `.svm-pop` a `top:96` et
            # rien ne fermait l'un quand l'autre s'ouvrait : deux panneaux
            # empiles au meme pixel, et le second illisible. La ref est
            # NECESSAIRE ici (contrairement a ce que disait la premiere
            # version de ce commentaire) : `dzMkToggle` doit LIRE l'etat
            # pour savoir si elle OUVRE -- et elle est appelee depuis
            # `onKey`, qui peut tenir une fermeture perimee.
            # LA BASCULE EST LE SEUL CHEMIN : K2 (le raccourci), K5 (la
            # chip) et K7 (Echap) l'appellent tous, donc l'exclusion ne
            # peut pas etre oubliee d'un cote.
            "  var dzMkOnRef=x.useRef(!1);dzMkOnRef.current=dzMkOn;\n"
            "  function dzMkToggle(v){"
            "var n=arguments.length?!!v:!dzMkOnRef.current;"
            'if(n)setOvPick("");setDzMkOn(n)}\n'
            # ET L'AUTRE SENS, par EFFET plutot que par une seconde retouche
            # d'`openPicker` : le selecteur s'ouvre depuis PLUSIEURS chemins
            # (le « + » d'en-tete de piste, le bouton « lier » de la barre,
            # le greffon « Envoyer vers -> Montage »), qui passent tous par
            # l'ETAT `ovPick`. Un effet sur cet etat les couvre tous ; une
            # ligne posee dans `openPicker` n'en aurait couvert qu'un.
            # MESURE : `var stO=x.useState(""),ovPick=stO[0]` est a l'offset
            # 784168 du .bak et l'ancre de CE remplacement a 785144 --
            # `ovPick` est donc DEJA declare, et l'effet lit sa vraie valeur.
            "  x.useEffect(function(){if(ovPick)setDzMkOn(!1)},[ovPick]);\n"
            "  var dzModeRef=x.useRef(dzMode);dzModeRef.current=dzMode;\n"
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
    # ── « E2 » (D-2) : LA RANGÉE DES SIX MODES ────────────────────
    # REPLIÉE ICI pour la même raison qu'E1 : la ligne du titre ci-dessus
    # vaut 0 dans .bak_montage (c'est CE remplacement qui l'écrit) et 1
    # dans le bundle livré. Elle est posée ENTRE le titre et la note : le
    # titre dit SUR QUELLE PISTE, la rangée dit COMMENT, la note dit OÙ.
    # `range` vient de `proj` et non d'une ref parce que ce panneau est
    # RENDU : il voit la plage courante, et la chip « remplir la plage »
    # s'éteint donc d'elle-même tant qu'I / U n'ont pas été frappés.
    # LA RANGÉE N'EXISTE PAS EN MODE REMPLACEMENT, et c'est une MESURE :
    # `addAsset` COURT-CIRCUITE sur `dzmReplaceRef.current` dès son
    # entrée (P6), AVANT la piste, avant la tête, avant le mode. Six
    # chips cliquables qui ne décident de rien sont un mensonge ; et le
    # titre du panneau dit déjà « Remplacer la source de … ».
    '      dzmA?null:r.jsx(DzTracks.ModeBar,{mode:dzMode,onMode:setDzMode,\n'
    '        range:proj.range}),\n'
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

# ── « E4 » (D-2, 21/09/2026) : LE VERROU SE JUGE APRÈS LE MODE ───────────
# LE DÉFAUT, MESURÉ : cette garde-ci teste la piste VISÉE, et elle précède le
# mode d'édition. En « au-dessus » avec V1 verrouillée et V2 libre, le geste
# était refusé alors que RIEN n'allait sur V1 : c'est V2 qui devait recevoir
# le clip. La garde n'est pas supprimée, elle est DÉPLACÉE — `dzmInsere`
# teste déjà `opts.locked[piste finale]` et rend `refus:"verrou"` avec la
# piste CONCERNÉE dans `track` (R_M22A). La phrase d'origine est reprise MOT
# POUR MOT quand la piste refusée est bien celle qu'on visait : sur ce
# chemin-là, rien ne change pour l'utilisateur.
# L'ANCRE EST UNE VRAIE SECTION, elle : son texte vaut 1 dans .bak_montage
# (mesuré) parce qu'il vient du greffon amont son-vfx-montage.js, qu'on ne
# touche PAS. C'est la seule des quatre « E » qui en soit une ; E1, E2 et E3
# visent des textes que d'autres remplacements POSENT. Le compte d'ancres
# passe donc de 75 à 76, et `PATCHES` de 74 à 75 triplets.
# CE QUE ÇA COÛTE, DIT : sur une piste verrouillée, la sonde audio
# (`askAudio`) part maintenant AVANT le refus — un aller-retour réseau,
# mis en cache, sans écriture. Aucun clip, aucun historique : les deux
# gardes qui comptent (`pushHistory`, `setClips`) restent derrière le refus.
A_E4 = '    if(trackStRef.current[tr2]&&trackStRef.current[tr2].l){\n      fireNote("Piste "+tr2.toUpperCase()+" verrouillée — déverrouillez-la pour ajouter.");return}\n'
R_E4 = ("    /* « E4 » (D-2) — LE VERROU DE PISTE SE JUGE APRÈS LE MODE, dans\n"
        "       `insere()` : le mode « au-dessus » CHANGE de piste, et\n"
        "       refuser ici sur la piste visée refusait un geste qui n'allait\n"
        "       pas s'y poser. Le refus, sa phrase d'origine comprise, vit\n"
        "       désormais au seul endroit qui connaît la piste RÉELLE. */\n")

A_M17A = ('    st=Math.min(Math.max(0,st),Math.max(0,d-1));\n'
          '    var en=Math.min(d,st+defaultLen(kind,srcDur));'
          'if(en-st<.5)st=Math.max(0,en-1);\n')
R_M17A = (
    "    /* P10 — LA TIMELINE S'ÉTEND, ELLE NE ROGNE PLUS. Le clip garde sa\n"
    "       longueur naturelle ; c'est la durée du projet qui grandit. La\n"
    "       garde des clips de moins d'une demi-seconde est celle d'avant :\n"
    "       elle vise les SOURCES minuscules, pas le plafond disparu. */\n"
    "    st=Math.max(0,st);\n"
    "    /* P11 — LA LONGUEUR DE LA SOURCE, DÉCOUVERTE QUAND ELLE MANQUE.\n"
    "       On sort ICI, avant `pushHistory` : rien n'est encore écrit, et le\n"
    "       rappel repart du même point avec la mesure. La piste REDEMANDÉE\n"
    "       est `trId`, pas la piste résolue — sinon l'explication « cette\n"
    "       piste n'existe pas dans ce projet » se perdrait au retour ; `st`\n"
    "       est repassé pour que le clip atterrisse là où la tête de lecture\n"
    "       était AU CLIC, pas 85 ms plus tard. Mesure échouée : on repasse un\n"
    "       nombre NÉGATIF, que `needDur` lit comme « déjà demandé » — c'est\n"
    "       le verrou de récursion, et il est éprouvé sous node. */\n"
    "    /* P12 — LE SON D'UN PLAN SUIT SA VIDÉO : le verdict « cette source\n"
    "       a-t-elle du son ? » est demandé ICI, avant la durée et avant\n"
    "       tout `pushHistory`, pour une vidéo posée sur une piste vidéo\n"
    "       PLEIN CADRE (V1 : type « vidéo », jamais une incrustation). Le\n"
    "       rappel repart des MÊMES arguments — c'est le CACHE du verdict,\n"
    "       écrit par askAudio sur toute sortie, qui le rend non récursif\n"
    "       (éprouvé sous node : un rappel sans cache redemande). La durée\n"
    "       rendue en prime épargne le second aller-retour d'askDur. */\n"
    "    var dzAuOn=DzTracks.wantsTwin(kind,dzTs,tr2);\n"
    "    var dzAu=dzAuOn?DzTracks.audioOf(src):null;\n"
    "    if(dzAuOn&&!dzAu){DzTracks.askAudio(src,{done:function(){\n"
    "      addAsset(src,label,kind,srcDur,trId,st)}});return}\n"
    "    srcDur=DzTracks.srcDurOr(kind,srcDur,dzAu);\n"
    "    if(DzTracks.needDur(kind,srcDur)){\n"
    "      DzTracks.askDur(src,{done:function(dzV){\n"
    "        addAsset(src,label,kind,dzV>0?dzV:-1,trId,st)}});return}\n"
    "    var dzCl=defaultLen(kind,srcDur);\n"
    "    var en=st+dzCl.len;if(en-st<.5)st=Math.max(0,en-1);\n")
# « E3 » (D-2, 21/09/2026) — CE QUI A QUITTÉ CETTE SECTION, ET POURQUOI.
# `dzFit` / `dzGrew` / `dzTail` / le `setProj(dur)` vivaient ICI, où le seul
# clip connu était celui qu'on s'apprêtait à poser : `fitDur([{end:en}],d,0)`.
# LES MODES D'ÉDITION RENDENT CETTE MESURE FAUSSE, et c'est mesurable : en
# `inserer`, `fin` et `ripple_ecraser`, `DzTracks.insere` POUSSE la suite de
# la piste — la fin réelle du montage dépasse alors `en`, et des clips
# vivraient au-delà de `proj.dur` (invisibles, non rendus par la règle).
# Le calcul est donc déplacé dans R_M22A, APRÈS l'insertion, où il se fait
# sur `dzIns.clips` — la timeline ENTIÈRE. L'ordre des phrases de la note ne
# change pas d'un mot : `dzCl.note` puis l'allongement puis le jumeau.
# CE QUI NE CHANGE PAS NON PLUS : `setProj(dur)` reste AVANT `pushHistory()`,
# et la note « Annuler … rend aussi la durée d'avant » reste VRAIE — mesuré
# le 21/09/2026 : `dzmHistHost()` lit `dzProjRef.current`, une ref réécrite
# au RENDU (`dzProjRef.current=proj`, à côté de `histRef`), jamais par
# `setProj` ; l'instantané pris par `pushHistory()` porte donc encore la
# durée D'AVANT, que `DzTracks.histApply` rend à « Annuler » depuis D-0.

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
    "          \"et n'a PAS été rogné pour autant. « Annuler » le ramène \"+\n"
    "          \"en place, et rend aussi la durée d'avant.\")}\n"
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
    '            "projet, et rien n\'a été rogné. « Annuler » rend les "+\n'
    '            "clips, et rend aussi la durée d\'avant.")}}}\n')

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
          '           est REFUSÉ, jamais fait en silence. Depuis D-0 (le\n'
          '           21/09/2026, « H6 », replié ICI) le geste ENTRE dans\n'
          '           l\'historique, une entrée par rafale de 600 ms, et\n'
          '           chaque note le dit. */\n'
          '        DzTracks.durCtl({dur:dur,step:tickStep,clips:clips,\n'
          '          /* D-0 — MÊME FENÊTRE QUE `nudgeHistAt` (M17b) : une\n'
          '             rafale de clics sur « + » vaut UNE entrée, pas trente. */\n'
          '          onSet:function(v){var dzN=Date.now();\n'
          '            if(dzN-dzDurHistAt.current>600)pushHistory();\n'
          '            dzDurHistAt.current=dzN;\n'
          '            setProj(function(p){'
          'return Object.assign({},p,{dur:v})});setDirty(!0)},\n'
          '          note:fireNote}),')

# ── M18a (P11) : LE SECOND PLAFOND, celui qui bornait la SOURCE ────────────
# L'ANCRE PORTE LE CORPS ENTIER de `defaultLen`, ses trois lignes d'un bloc.
# Comptée le 05/09/2026 : 1 dans le bundle livré, 1 dans .bak_montage — et
# chacune des trois lignes y vaut 1 séparément.
#
# CE QUE CE PLAFOND FAISAIT, MESURÉ SUR LA BASE DE L'UTILISATEUR (instantané
# COHÉRENT par `sqlite3 … .backup()`, qui fusionne le WAL : 120 jobs, contre
# 106 pour une copie d'octets du seul `.db`) : `kapwing_sample` porte
# `duration_s = 16` et entrait à 6 s — l'application CONNAISSAIT la durée et
# la jetait. `Memecoin` et `sentry_bot` portent `duration_s = NULL` : pour
# celles-là, lever le plafond ne change RIEN, il n'y a rien à lever. C'est
# pourquoi P11 ne se limite pas à cette ancre et ajoute la DÉCOUVERTE
# (M17a + DzTracks.askDur + GET /api/montage/duration).
#
# `defaultLen` CHANGE DE CONTRAT : il rendait un nombre, il rend désormais le
# descripteur de `DzTracks.clipLen` — {len, origine, note}. Le nom est celui
# du bundle et on ne le renomme pas (ce serait une ancre de plus pour un
# gain de lecture), mais son UNIQUE appelant est réécrit dans la même passe
# (M17a) : le banc compte l'appel des deux côtés.
#
# LES TROIS CHIFFRES RESTENT ÉCRITS ICI, ET C'EST VOULU : 4 s pour une image,
# 8 pour un son, 6 pour une vidéo sont les replis DU BUNDLE depuis toujours.
# Les passer en argument plutôt que de les laisser à la couche empêche
# celle-ci de devenir une seconde autorité sur des valeurs qui ne sont pas
# les siennes — même raisonnement que `_VIDEO_EXTS` servi par le backend en
# P9. La couche en garde une copie de secours, qui ne sert QUE si l'appelant
# n'en passe pas.
A_M18A = ('    if(kind==="image")return 4;\n'
          '    if(kind==="audio")return Math.min(8,srcDur||8);\n'
          '    return Math.min(6,srcDur||6);\n')
R_M18A = ("    /* P11 — plus de plafond : la longueur d'un clip est celle de\n"
          "       sa source quand on la connaît. Les trois replis restent, et\n"
          "       ils sont PASSÉS à la couche au lieu d'y être recopiés ; un\n"
          "       clip posé sur un repli le DIT (champ `note`). */\n"
          "    return DzTracks.clipLen(kind,srcDur,"
          "{image:4,audio:8,video:6});\n")

# ── M19 (étape 4 du handoff « Barre Outils Flottante », §9) : l'onglet OUTILS
#    et la barre, montés DANS le bandeau de transport ───────────────────────
# L'ANCRE EST L'OUVERTURE DU BANDEAU, et il en fallait une nouvelle : A_M8 est
# consommée par M8, et M10/M11b/M14 s'y greffent déjà. Mesurée UNIQUE le
# 05/09/2026 — une seule occurrence dans le bundle, comme `className:"svm-trans"`
# lui-même. C'est aussi la SEULE ancre qui place les deux nœuds au bon endroit :
# le §2.1 pose l'onglet à `top:-21px` RELATIVEMENT AU BANDEAU, il doit donc en
# être un enfant, et /shared/montage.css passe `.svm-trans` en `position:relative`
# pour cela (la chaîne des parents y est écrite en entier — aucun ne le rogne).
#
# LES DEUX NŒUDS SONT ABSOLUS, donc HORS FLUX : le bandeau est un conteneur
# flex à `gap:12px`, et un enfant en `position:absolute` n'est pas un élément
# flex — il ne prend pas de place et n'ouvre pas d'intervalle. Le bandeau garde
# donc exactement la largeur et les 34 px qu'il avait.
#
# `DzTracks.ToolDock`, PAS `DzMontage` : le bundle déclare déjà une fonction
# `DzMontage` au premier niveau (l'écran Montage lui-même), et redéclarer ce nom
# est une SyntaxError en sémantique module — celle sous laquelle index.html
# charge le bundle. Même raison qu'en M10 et M14.
#
# LES DIX PROPRIÉTÉS SONT LE CÂBLAGE DU §6 EN ENTIER (« la barre est un
# nouveau point d'entrée, pas une nouvelle implémentation »). Aucune n'ouvre
# une action neuve : chacune est une expression DÉJÀ écrite ailleurs dans ce
# patcher, reprise mot pour mot.
#   tracks / onTracks  — `svmTracksOf(proj)` et `svmTracksSet`, exactement ce que
#                        `DzTracks.TrackAdd` reçoit en M8 : même appel, autre porte
#   onPick             — `openPicker`, celui de « Bibliothèque… » en M8
#   wordAnim/onWordAnim— la MÊME expression qu'en M10 : `proj.subsStyle` est la
#                        source unique, la chip et la barre la LISENT toutes deux
#   textOn / onText    — l'état du panneau « Texte » de M11a, basculé comme en M11b
#   emojiSegs / note / onEmojiAdd — LES TROIS INGRÉDIENTS de M10, à l'identique.
#                        C'est le Dock qui appelle `DzTracks.emojiGo` avec eux :
#                        l'ÉTAT D'ATTENTE est un hook, il reste à chaque porte.
#   onProjets          — incrémente `dzProjReq` (M11a), que M14 passe au popover
#
# ÉTAPE 7 : `emoji` ET `projets` NE SONT PLUS ÉTEINTS, et ce qui les tenait
# éteints était NOMMÉ à l'étape 4 : leur action vivait À L'INTÉRIEUR de leur
# composant. La porte a été ouverte SANS déplacer l'état, ce qui aurait
# demandé de réécrire les deux composants :
#   • emoji — le `fetch` est sorti du bouton (`dzmEmojiGo`, au premier niveau
#     de la couche) ; les deux portes l'appellent, chacune avec SON attente.
#   • projets — le popover garde son ouverture chez lui et reçoit une DEMANDE
#     (`openReq`). C'est le seul moyen d'ouvrir sans lutter contre son propre
#     « clic dehors », qui se déclenche précisément sur le bouton de la barre.
#
# ÉTAPE 6 : LA DUPLICATION EST SOLDÉE. Les neuf contrôles ont quitté le
# bandeau (§5.1, voir M8/M10/M11b/M14/M16-lib, tous vidés) et cette barre-ci
# est désormais LEUR SEULE PORTE — c'est pourquoi l'étape 7 devait passer
# AVANT : retirer `emoji` ou `projets` du bandeau avant de les câbler ici les
# aurait rendus inatteignables partout, ce que le §9 s'interdit. Le sens de
# lecture de ces dix propriétés ne change pas d'un mot ; ce qui change, c'est
# qu'aucune n'a plus de jumelle dans le bandeau.
# UNE ATTENTE DE MOINS : l'état d'attente de la requête emoji était tenu par
# CHAQUE porte (`DzmEmojiBtn` et le Dock). Une porte est partie, une attente
# avec elle — il n'en reste qu'une, celle du Dock.
A_M19 = 'r.jsxs("div",{className:"svm-trans",children:['
R_M19 = (A_M19 + "\n"
         "        /* étapes 4 à 7 du handoff « Barre Outils Flottante » :\n"
         "           l'onglet OUTILS et la barre flottante, câblée sur les\n"
         "           actions de l'écran. Les deux nœuds sont absolus, donc\n"
         "           hors du flux flex de ce bandeau : rien n'y bouge. */\n"
         "        r.jsx(DzTracks.ToolDock,{tracks:svmTracksOf(proj),"
         "onTracks:svmTracksSet,onPick:openPicker,"
         "wordAnim:(proj.subsStyle||{}).wordAnim||\"couleur\","
         "onWordAnim:function(v){subsStyleSet({wordAnim:v})},"
         "textOn:dzTextOn,onText:function(){setDzTextOn(!dzTextOn)},"
         "emojiSegs:subsSegsOf(clips),note:fireNote,onEmojiAdd:dzEmoAdd,"
         # Étape 8 (§4.1) — DEUX PROPRIÉTÉS DE PLUS, ET RIEN D'AUTRE.
         # `toggleReq` : le compteur de demandes de bascule (M11 le déclare,
         # M20b l'incrémente). `keyLbl` : la combo VIVANTE du raccourci, lue
         # par `svmKeyLabel` — la même fonction qui fait suivre la chip
         # « lame » à un remappage. L'onglet la dit dans son `title` : un
         # raccourci qu'on ne peut lire nulle part n'existe qu'à moitié.
         'toggleReq:dzTbReq,keyLbl:svmKeyLabel("toolbar"),'
         "onProjets:function(){setDzProjReq(function(n){return n+1})}}),")

# ══ P12 — LE SON D'UN PLAN SUIT SA VIDÉO ═══════════════════════════════════
#
# LE DÉFAUT, MESURÉ (06/09/2026). Le rendu n'entre JAMAIS l'audio embarqué
# d'un clip vidéo dans le graphe ffmpeg (`[idx:v]` seul, montage_service
# `_run`) : sans clip jumeau sur la piste de dialogue, un plan parlant sort
# MUET. La construction automatique (`montage_project`) pose ce jumeau pour
# chaque job dont `_has_audio_stream` est vrai ; `addAsset`, point d'entrée
# des SEPT portes de l'écran, posait UN clip et rien d'autre. Le
# `kapwing_sample.mp4` de l'utilisateur (aac, 15,973 s, ffprobe) est sur V1
# de sa sauvegarde SANS jumeau — et la transcription tournait sur le vieux
# MP3 de la piste A1 (journal du 06/09, l. 42). Aucune route ne disait
# « cette source a un flux audio » : GET /has-audio (montage_service) le dit
# maintenant, durée en prime.
#
# CE QUE FONT LES CINQ SECTIONS, et l'ordre compte :
#   R_M17A (édité DANS sa chaîne — `var dzCl=defaultLen(kind,srcDur);` est un
#          texte qui n'existe qu'APRÈS patch, 1 dans le bundle livré, 0 dans
#          .bak_montage, mesuré) : la SONDE, avant la durée et avant tout
#          `pushHistory`. Sortie par `DzTracks.askAudio`, rappel avec les
#          mêmes arguments ; `st` repassé pour l'instant du clic, comme
#          askDur. Le CACHE est le verrou de récursion (test_montage_bundle
#          [3-bis] joue le rappel SANS cache : il redemande — c'est la preuve
#          que le verrou est bien lui).
#   M22a   (le trio `ovSeq++` / `id` / `pushHistory()` — 1/1 en CRLF, 0/0 en
#          LF, mesuré, d'où `nl()`) : l'identifiant passe par `uniqueId`
#          contre les clips existants, et le JUMEAU est décidé par
#          `twinPlan` (verdict, piste de dialogue, verrou, doublon) AVANT le
#          seul `pushHistory()` du geste ; sa phrase entre dans `dzTail`, la
#          note de l'ajout (M16b la lit telle quelle : `+dzTail)}` reste
#          l'unique fin de note, le banc le compte).
#   M22b   (l'unique écriture du clip) : UN `setClips(concat([clip, jumeau]))`.
#          Deux `setClips(clipsRef.current.concat(…))` dans le même
#          gestionnaire PERDRAIENT le premier — `clipsRef.current=clips` n'est
#          rafraîchi qu'au rendu (bundle 1723), mesuré. Un seul concat, un
#          seul historique : « Annuler » retire les deux.
#   M22c   (`svmApplyProject`, après la construction de `cs`) : les
#          identifiants en double sont renommés par `dedupeIds` (le PREMIER
#          garde le sien), c'est DIT, et `ovSeq` est re-semé au plus grand
#          `u<n>` — il repartait de zéro à chaque chargement (`ovSeq.current=`
#          : 0 occurrence dans le bundle, mesuré) et la sauvegarde de
#          l'utilisateur porte `v1u1_0` deux fois et `v1u2_0` deux fois.
#          `v1_non_video` (des IDENTIFIANTS) suit le renommage.
#   M22d   (`setDirty(!1);` + `histRef.current={u:[],r:[]};` de
#          svmApplyProject — 1/1 des deux côtés, mesuré en octets ; l'ancre
#          ne cite PAS le `setPh(0)` qui précède sur la même ligne, que la
#          garde tb7 du banc interdit aux sections) : `dirty` suit le
#          renommage d'une SAUVEGARDE, pour que l'autosauvegarde — le SEUL
#          enregistrement qui existe (`svmDoSave(` : trois sites, aucun
#          bouton, aucun raccourci ; « Enregistrer sous… » crée un projet
#          neuf) — écrive les ids réparés ; sans elle la note reviendrait à
#          chaque chargement. Une construction de Bibliothèque n'est jamais
#          marquée.
#   M23    (`transInspector(),` — 1/1 dans le bundle livré ET dans
#          .bak_montage ; R_M12 la reprend en tête, donc elle reste libre
#          après M12, et M23 s'insère AVANT elle : R_M12 reste contigu, la
#          ligne `M12-text-panel_remplace` du banc le tient) : le bouton
#          « Extraire le son → A1 » pour les plans DÉJÀ posés, visible sur
#          tout clip vidéo à source (V1, V2, V3…), même moteur — c'est lui
#          qui rend son son au kapwing_sample déjà sur V1.
#
# LA CIBLE N'EST PAS `pickTrack(ts,"audio")` : première piste audio de
# l'ordre d'affichage, elle rend `a2` — la MUSIQUE, bouclée et duckée — sur
# la sauvegarde du 04/09 ([v1, a2, a1, a3, s1]). `dialogueTrack` vise le bus
# « dialogue », sinon `a1`, jamais une piste `loop`.
#
# DÉCISION : AUTOMATIQUE, comme la construction automatique — pour TOUTE
# vidéo à flux audio posée sur une piste plein cadre, sans demander. Parce
# que le geste est réversible d'un seul « Annuler », que le doublon est
# refusé, et que les incrustations (B-roll) en sont exemptées par leur
# `type`. Le bouton de M23 est la porte pour tout le reste.
#
# RÉSERVE PORTÉE, PAS CORRIGÉE ICI : aucune liaison V1↔A1 n'existe
# (déplacement, rognage, vitesse, remplacement de source non propagés) —
# c'est déjà le cas des « son du plan » de la construction automatique, et
# le remplacement de source (P6) sort AVANT toute extraction.
A_M22A = ('    ovSeq.current++;\n'
          '    var id=tr2+"u"+ovSeq.current+"_"+Math.round(st*10);\n'
          '    pushHistory();')
R_M22A = (
    # ── « E3 » (D-2, 21/09/2026) : L'ÉCRITURE PASSE PAR LE MODE ─────────
    # REPLIÉ ICI ET DANS R_M22B, pas en section : `setClips(clipsRef.current
    # .concat(dzTw&&dzTw.clip?…))` vaut 0 dans .bak_montage (R_M22B l'écrit)
    # et 1 dans le bundle livré — une section serait refusée par --check.
    #
    # L'ORDRE EST LA PARTIE DIFFICILE, et il est mesuré :
    #  1. `dzSeq` est un CANDIDAT (`ovSeq.current+1`), pas un incrément. Le
    #     refus « verrou » sort SANS l'avoir consommé : un geste refusé ne
    #     doit pas trouer la numérotation des identifiants.
    #  2. `dzIns` est calculé AVANT `pushHistory()`. Un `return` sur refus
    #     APRÈS aurait laissé un instantané FANTÔME dans la pile, et le
    #     premier « Annuler » de l'utilisateur n'aurait rien fait.
    #  3. L'allongement (`dzFit`/`dzGrew`) se mesure sur `dzIns.clips`, la
    #     timeline ENTIÈRE : voir la note d'E3 au-dessus de R_M17A.
    #
    # LE REFUS « verrou » EST LE SEUL, depuis « E4 » (21/09/2026) : la garde
    # héritée qui testait la piste VISÉE a été déplacée ici, parce que le mode
    # « au-dessus » CHANGE de piste — refuser sur la piste visée refusait un
    # geste qui n'allait pas s'y poser. `dzmInsere` ne filtre les candidates
    # que sur le CHEVAUCHEMENT (`dzmOverlap`), jamais sur le verrou : c'est
    # donc `refus:"verrou"` + `track` qui décident, et les DEUX cas ont leur
    # phrase (piste visée : celle d'avant, mot pour mot ; autre piste : elle
    # la nomme et renvoie au mode, qui reste à l'écran).
    # `verrou_jumeau`, lui, EST un filet : `twinPlan` refuse déjà une piste de
    # dialogue verrouillée et rend `dzTw` nul avec sa phrase (banc
    # `verrou_note`) — le jeton n'a donc pas de chemin ici, et il n'est lu
    # que par `dzIns.note`, qui le dirait si jamais il en gagnait un.
    "    /* D-2 — LE MODE D'ÉDITION DÉCIDE DE L'ÉCRITURE. `dzModeRef` est\n"
    "       l'état de la rangée de chips du sélecteur ; `insere()` rend la\n"
    "       timeline ENTIÈRE, jumeau compris. Le numéro d'ordre n'est\n"
    "       CONSOMMÉ qu'une fois l'insertion acceptée, et le refus sort AVANT\n"
    "       `pushHistory()` : rien d'écrit, rien dans la pile d'annulation. */\n"
    "    var dzSeq=ovSeq.current+1;\n"
    "    /* P12 — l'identifiant est UNIQUE contre les clips existants (une\n"
    "       sauvegarde rechargée peut en porter d'anciens du même rang), et\n"
    "       le jumeau est décidé AVANT le seul pushHistory du geste : sa\n"
    "       phrase rejoint la note de l'ajout — et une incrustation, exemptée\n"
    "       de sonde, est DITE aussi (overlayNote), jamais tue. */\n"
    '    var id=DzTracks.uniqueId(clipsRef.current||[],\n'
    '      tr2+"u"+dzSeq+"_"+Math.round(st*10));\n'
    "    var dzNeuf={tr:tr2,id:id,label:label,start:st,end:en,src:src,srcIn:0};\n"
    "    var dzTw=dzAuOn?DzTracks.twinPlan(dzNeuf,dzTs,clipsRef.current||[],dzAu,\n"
    "      function(t){return !!(trackStRef.current[t]&&trackStRef.current[t].l)}):null;\n"
    # I-3 — `srcDur` PASSE PAR LES OPTIONS, PAS PAR LE CLIP. C'est une mesure
    # de la SOURCE : posée sur le clip, elle entrait dans la sauvegarde et
    # dans le payload de rendu (huit clés au lieu de sept, mesuré le
    # 21/09/2026). Seul le mode « remplir » la lit, pour calculer la vitesse ;
    # `dzmPose` retire désormais la clé de la copie posée, ce qui couvre aussi
    # l'appelant qui la mettrait quand même sur le clip.
    "    var dzIns=DzTracks.insere(clipsRef.current||[],dzNeuf,dzModeRef.current,\n"
    "      {tracks:dzTs,twin:dzTw&&dzTw.clip,head:phRef.current,\n"
    "       srcDur:Number(srcDur)||0,\n"
    "       range:dzProjRef.current&&dzProjRef.current.range,\n"
    "       locked:(function(){var o={},k;for(k in trackStRef.current)\n"
    "         if(trackStRef.current[k]&&trackStRef.current[k].l)o[k]=!0;\n"
    "         return o})()});\n"
    # I-5 — LE REFUS NE FERME PAS LE SÉLECTEUR : il disait « choisissez un
    # autre mode » en escamotant la rangée qui les porte. Les deux refus
    # frères du même corps (piste absente, source d'un autre genre) laissent
    # déjà le panneau ouvert ; celui-ci s'aligne.
    "    if(dzIns.refus===\"verrou\"){\n"
    "      fireNote(dzIns.track===tr2\n"
    "        ?(\"Piste \"+String(tr2).toUpperCase()+\" verrouillée — \"+\n"
    "          \"déverrouillez-la pour ajouter.\")\n"
    "        :(\"Piste \"+String(dzIns.track).toUpperCase()+\" verrouillée — \"+\n"
    "          \"rien n'a été posé. Déverrouillez-la, ou choisissez un \"+\n"
    "          \"autre mode d'édition.\"));return}\n"
    "    ovSeq.current=dzSeq;\n"
    "    /* LE CLIP RÉELLEMENT POSÉ : `dzmPose` RENOMME un identifiant déjà\n"
    "       pris, et « en fin » / « remplir » le posent à d'autres bornes que\n"
    "       [st,en[. On le relit par `dzIns.id` pour que la note dise la\n"
    "       position VRAIE et que la sélection porte sur le bon clip. */\n"
    "    var dzP=null,dzJ;\n"
    "    for(dzJ=0;dzJ<dzIns.clips.length;dzJ++)\n"
    "      if(dzIns.clips[dzJ]&&dzIns.clips[dzJ].id===dzIns.id)dzP=dzIns.clips[dzJ];\n"
    # CONFORMITÉ 5 — LA PHRASE DE L'ALLONGEMENT EST BORNÉE. « Le clip garde sa
    # longueur entière au lieu d'être rogné sur la fin du projet » est FAUSSE
    # quand la timeline débordait DÉJÀ (un projet dont `dur` a été raccourci
    # à la main porte des clips au-delà, et le contrôle de la barre de
    # transport le permet depuis P10) : ce n'est alors pas CE clip qui a fait
    # grandir la durée. `dzAv` mesure la fin réelle d'AVANT l'insertion.
    "    var dzAv=DzTracks.fitDur(clipsRef.current||[],d,0);\n"
    "    var dzFit=DzTracks.fitDur(dzIns.clips,d,0),dzGrew=dzFit>d?dzFit:0;\n"
    "    var dzTail=dzCl.note+(dzGrew?(\" La timeline a été allongée de \"+\n"
    "      svmRuler(Math.round(d))+\" à \"+svmRuler(Math.round(dzGrew))+\n"
    "      (dzAv>d?\" pour tenir tout ce qu'elle porte.\"\n"
    "        :\" : le clip garde sa longueur entière au lieu d'être rogné sur \"+\n"
    "          \"la fin du projet.\")+\n"
    "      \" « Annuler » retire le clip, et \"+\n"
    "      \"rend aussi la durée d'avant.\"):\"\");\n"
    "    if(dzTw)dzTail+=dzTw.note;\n"
    "    else dzTail+=DzTracks.overlayNote(kind,dzTs,tr2);\n"
    # M-5 — LA PISTE N'EST PAS RÉPÉTÉE : `tr2` vient d'être réaffecté à
    # `dzIns.track`, et la note principale dit déjà « ajouté sur V2 à … ».
    # Ce qu'il reste à dire est le MODE, et RIEN D'AUTRE. Une version de
    # cette phrase disait « la piste visée était occupée à cet instant » :
    # c'était FAUX, et c'est mesuré (21/09/2026, `dzmInsere` joué sous node,
    # pistes [v2, v1], clips VIDES, clip visé sur v1 en « dessus » →
    # `{track:"v2", refus:"", note:""}`). Le mode remonte TOUJOURS vers la
    # première piste libre du même genre au-dessus ; il ne regarde jamais
    # l'occupation de la piste visée. La note énonce donc le mode appliqué,
    # exactement comme la branche `else` juste en dessous.
    # I-2 — LA VITESSE EST FORMATÉE SUR PLACE. `DzTracks.secs` est un
    # formateur de DURÉE : il arrondit au dixième et rendait « ×0,3 » pour
    # une vitesse de 0,25 (mesuré le 21/09/2026), en plus de coller un « s »
    # qu'il fallait retirer après coup. Une virgule décimale suffit.
    "    /* D-2 — LE MODE APPLIQUÉ EST DIT, COURT. `dzIns.mode` est le mode\n"
    "       EFFECTIF : « au-dessus » rend toujours \"ecraser\" sur une autre\n"
    "       piste, c'est donc le changement de PISTE qui le trahit, et le\n"
    "       repli « aucune piste libre » parle par `dzIns.note`. */\n"
    "    if(dzIns.track&&dzIns.track!==tr2)dzTail+=\" Posé sur la piste \"+\n"
    "      \"libre au-dessus (mode « au-dessus »).\";\n"
    "    else if(dzIns.mode!==\"ecraser\")dzTail+=\" Mode « \"+\n"
    "      DzTracks.modeLabel(dzIns.mode)+\" ».\"+\n"
    "      ((dzP&&Number(dzP.speed)>0&&Number(dzP.speed)!==1)?\n"
    "        \" Vitesse ×\"+String(dzP.speed).replace(\".\",\",\")+\".\":\"\");\n"
    # I-1a — LE MODE DEMANDÉ N'EST PAS TOUJOURS LE MODE APPLIQUÉ. « remplir la
    # plage » retombe en « écraser » quand la plage a disparu entre le clic
    # sur la chip et l'ajout. R_R2 désarme désormais le mode quand la plage
    # devient nulle (X, Maj+X), mais la course reste possible : un
    # glisser-déposer, le greffon « Envoyer vers → Montage », un rappel
    # d'`askAudio` parti avant l'effacement. Le silence était le pire des cas :
    # le clip s'écrasait sous la tête sans un mot.
    "    if(dzModeRef.current===\"remplir\"&&dzIns.mode!==\"remplir\")\n"
    "      dzTail+=\" Plage effacée : posé en écraser.\";\n"
    # M-3 — la phrase du cœur entre dans une PHRASE : première lettre capitale.
    "    /* Le JETON `dzIns.refus` n'est jamais affiché : la phrase française\n"
    "       est `dzIns.note` (écrêtage de vitesse, aucune piste libre…), et\n"
    "       elle est capitalisée parce qu'elle suit un point. */\n"
    "    if(dzIns.note)dzTail+=\" \"+dzIns.note.charAt(0).toUpperCase()+\n"
    "      dzIns.note.slice(1)+\".\";\n"
    "    if(dzGrew)setProj(function(p){"
    "return Object.assign({},p,{dur:dzGrew})});\n"
    "    /* LA NOTE ET LA SÉLECTION DISENT LE RÉEL : `id`, `tr2` et `st` sont\n"
    "       RELUS sur le clip posé avant que la fin d'`addAsset` (setSelId,\n"
    "       fireNote) ne les emploie — c'est la même variable, pas une\n"
    "       seconde source de vérité. La phrase de la piste absente, le choix\n"
    "       des pistes et `overlayNote` ont déjà lu `tr2` au-dessus : leur\n"
    "       sens ne change pas. */\n"
    "    id=dzIns.id||id;tr2=dzIns.track||tr2;if(dzP)st=Number(dzP.start)||0;\n"
    "    pushHistory();")
A_M22B = ('setClips(clipsRef.current.concat([{tr:tr2,id:id,label:label,'
          'start:st,end:en,src:src,srcIn:0}]));')
# « E3 » (D-2) — L'UNIQUE ÉCRITURE passe désormais par `DzTracks.insere`, qui
# a déjà posé le clip ET son jumeau dans `dzIns.clips` : un `concat` ici
# doublerait le clip en « écraser » et perdrait la fente / le décalage des
# autres modes. Le banc bundle le NIE explicitement
# (`D2_addAsset_ecrit_par_insere_et_plus_par_concat`).
R_M22B = 'setClips(dzIns.clips);'
A_M22C = '    var first=cs.find(function(c){return c.tr==="v1"});'
R_M22C = (
    "    /* P12 — DES IDENTIFIANTS UNIQUES. `ovSeq` repart de zéro à chaque\n"
    "       chargement et la sauvegarde reprend `c.id` tel quel : deux clips\n"
    "       du même id se suppriment ensemble (`c.id!==id`) et le second n'est\n"
    "       jamais sélectionnable (`c.id===selId`). Le PREMIER garde le sien,\n"
    "       les suivants sont renommés, c'est dit, `v1_non_video` — des\n"
    "       IDENTIFIANTS, contrat du backend — suit le renommage (l'id neuf est\n"
    "       AJOUTÉ : les deux exemplaires étaient marqués, ils le restent), et\n"
    "       le compteur repart AU-DESSUS de tout ce que la sauvegarde porte. La\n"
    "       réparation est PERSISTÉE par M22d (l'autosauvegarde) sur une\n"
    "       sauvegarde, jamais sur une construction de Bibliothèque : la note\n"
    "       le dit dans les deux cas. */\n"
    "    var dzDd=DzTracks.dedupeIds(cs);cs=dzDd.clips;\n"
    "    if(dzDd.renamed.length&&Array.isArray(d.v1_non_video))d.v1_non_video=\n"
    "      d.v1_non_video.concat(dzDd.renamed.filter(function(k){\n"
    "        return d.v1_non_video.indexOf(k.de)>=0&&d.v1_non_video.indexOf(k.en)<0})\n"
    "      .map(function(k){return k.en}));\n"
    "    if(dzDd.renamed.length)fireNote(dzDd.renamed.length+\" clip\"+\n"
    '      (dzDd.renamed.length>1?"s portaient":" portait")+" un identifiant "+\n'
    '      "déjà pris dans cette sauvegarde ("+dzDd.renamed.map(function(k){\n'
    '        return k.de+" → "+k.en}).join(", ")+") : renommé"+\n'
    '      (dzDd.renamed.length>1?"s":"")+" pour que chaque plan se "+\n'
    '      "sélectionne et se supprime seul. Rien d\'autre n\'a changé"+\n'
    '      (d.saved?" — ce sera enregistré automatiquement dans un instant."\n'
    '        :" (timeline construite depuis la Bibliothèque : rien n\'est "+\n'
    '         "enregistré tant que vous ne modifiez rien)."));\n'
    "    ovSeq.current=Math.max(ovSeq.current,DzTracks.seqMax(cs));\n"
    + A_M22C)
A_M22D = ('setDirty(!1);\n'
          '    histRef.current={u:[],r:[]};')
R_M22D = (
    "setDirty(!!(d.saved&&dzDd.renamed.length));\n"
    "    /* P12 — LA RÉPARATION EST PERSISTÉE. `setDirty(!1)` désarmait ici\n"
    "       l'autosauvegarde (l'effet gardé par `dirty`, 1,5 s) juste après le\n"
    "       renommage de M22c, et AUCUN geste manuel n'enregistre le montage —\n"
    "       `svmDoSave(` n'a que trois sites dans le bundle (sa définition,\n"
    "       cet effet, la relance sur échec), « Enregistrer sous… » crée un\n"
    "       projet NEUF (mesuré le 06/09/2026) : la note serait revenue à\n"
    "       chaque chargement. Une SAUVEGARDE dont des ids ont été renommés est\n"
    "       donc marquée modifiée, et l'autosauvegarde écrit les ids réparés.\n"
    "       Une construction depuis la Bibliothèque (`saved` faux) ne l'est\n"
    "       JAMAIS : l'enregistrer en ferait la source à la place de la\n"
    "       Bibliothèque — et ses ids (`v1_<job>`, `a1_<job>`, `c<i>`) ne se\n"
    "       répètent pas. La note de M22c le dit dans les deux cas. */\n"
    "    histRef.current={u:[],r:[]};")
A_M23 = "        transInspector(),"
R_M23 = (
    "        /* P12 — « Extraire le son → A1 » : le son d'un plan DÉJÀ posé,\n"
    "           même moteur que l'ajout (sonde, cache, jumeau, refus DIT).\n"
    "           Posé juste avant l'inspecteur de transition, pour tout clip\n"
    "           vidéo porteur d'une source — V1, V2, V3. */\n"
    "        DzTracks.extractBtn(sel,{tracks:dzTracksRef.current||svmTracksOf(proj),\n"
    "          clips:function(){return clipsRef.current||[]},\n"
    "          locked:function(t){return !!(trackStRef.current[t]&&trackStRef.current[t].l)},\n"
    "          pushHistory:pushHistory,setClips:setClips,setDirty:setDirty,\n"
    "          note:fireNote}),\n"
    + A_M23)

# ── P13 — LA TRANSCRIPTION VISE LA PISTE DE DIALOGUE ET DIT CE QU'ELLE VA
# DÉPENSER (06/09/2026). Sept sections sur le BLOC SUBS INLINÉ (M24a…M24g),
# trois sur l'HÔTE (M24h…M24j) et, au tour 1, trois de plus sur le bloc subs
# (M24k…M24m, les libellés sous « auto »). `frontend/patches/subs.js` est
# INTOUCHABLE (pas de `.bak_subs`, ses ancres sont consommées, aucun banc ne
# compare le bloc inliné à sa source — mesuré) : ces sections portent la
# correction EN AVAL, et le bloc inliné diverge désormais de subs.js sur les
# lignes qu'elles remplacent (le banc bundle les compte).
# Mesuré avant d'écrire (06/09, en octets, CRLF) : chaque ancre est 1/1 dans
# le bundle ET dans .bak_montage ; A_M24F, A_M24G, A_M24D et A_M24J sont
# multilignes (0 en LF, 1 en CRLF — `nl()` les aligne) ; les noms neufs
# (`dzSs`, `dzSsAll`, `srcTracks`, `subsSources`, `dzDial`) sont 0/0.
# CE QUE LE CLIENT FAISAIT, MESURÉ : `function transcribe(plan){` envoyait
# TOUJOURS `src:props.srcRef` (premier a1 porteur d'une source, sinon
# premier v1 — `subsSrcRef()`, hôte), donc le repli serveur n'était jamais
# atteint et le vieux MP3 de A1 partait à la place du plan ; le geste PAR
# PLAN filtrait `cl` aux clips chevauchant le plan et gardait `av[0].src`
# dans l'ordre du tableau, sans tri ; AUCUN décalage côté client — le
# résultat `got` n'est filtré qu'à la fenêtre du plan (`dans`). Le décalage
# vit donc UNE fois, dans la route (`start − srcIn`), et le client ne décale
# toujours pas.
# M24a — la ligne d'attente nomme ce qui part (même fonction pure que la
# pastille : DzTracks.subsSources).
A_M24A = 'setTrJob({busy:!0,step:plan?"plan "+plan.n+"…":"envoi…",pct:0});'
R_M24A = (
    "/* P13 — la ligne d'attente nomme ce qui part : les clips de la piste\n"
    "       de dialogue (sinon la première V1), par la même fonction pure\n"
    "       que la pastille de coût. */\n"
    "    var dzSs=DzTracks.subsSources(props.srcClips,props.srcTracks);\n"
    '    setTrJob({busy:!0,step:plan?"plan "+plan.n+"…":dzSs.step,pct:0});')
# M24b — sans plan, `src` part NUL : la route vise la piste de dialogue.
A_M24B = "var cl=props.srcClips||null,srcRef=props.srcRef||null;"
R_M24B = (
    "var cl=props.srcClips||null,srcRef=null;\n"
    "    /* P13 — sans plan, `src` part NUL : la route vise elle-même la piste\n"
    "       de dialogue — tous ses clips porteurs d'une source, transcrits un\n"
    "       par un, leurs mots décalés de `start − srcIn` et coupés au clip.\n"
    "       `props.srcRef` (le premier a1, sinon le premier v1, jamais\n"
    "       décalé) n'est plus envoyé : c'est lui qui faisait transcrire le\n"
    "       vieux MP3 de A1 au lieu du plan (journal du 06/09/2026). */")
# M24c — le geste par plan trie : a1 d'abord, puis `start` ; sans clip
# porteur qui chevauche le plan, rien ne part (et c'est dit) — avant, le
# premier a1 de TOUTE la timeline partait, contre paiement, pour rien.
A_M24C = (
    'var av=cl.filter(function(c){return c.src&&(c.tr==="a1"||c.tr==="v1")});\n'
    "      if(av.length)srcRef=av[0].src}")
R_M24C = (
    "/* P13 — la piste de dialogue du projet d'abord (bus « dialogue », sinon\n"
    "         a1 : le son du plan), puis v1, et au plus tôt : c'est le clip\n"
    "         porteur que la route retrouve pour décaler les répliques. Rien\n"
    "         qui chevauche : rien ne part, et c'est dit — avant, le premier\n"
    "         a1 de toute la timeline partait, contre paiement, hors du plan.\n"
    "         TOUR 1 (revue du 06/09) : le filtre suivait `a1` PAR IDENTIFIANT\n"
    "         alors que subsSrcClips (M24j) et la route visent la piste de\n"
    "         dialogue — sur une piste a4 de bus dialogue, le geste par plan\n"
    "         envoyait la V1 entière et disait « Aucun clip A1 ». */\n"
    '      var dzTd=DzTracks.dialogueTrack(props.srcTracks)||"a1",\n'
    '          av=cl.filter(function(c){return c.src&&(c.tr===dzTd||c.tr==="v1")})\n'
    '        .sort(function(p,q){return (p.tr===dzTd?0:1)-(q.tr===dzTd?0:1)\n'
    "          ||subsN(p.start,0)-subsN(q.start,0)});\n"
    "      if(!av.length){setTrJob(null);\n"
    '        note2("Aucun clip "+dzTd.toUpperCase()+" ou V1 porteur d\'une source '
    'ne chevauche le plan n° "+plan.n+" — rien n\'est envoyé.");return}\n'
    "      srcRef=av[0].src}")
# M24d — les pistes partent avec la requête : la route applique la loi du
# rendu (`_tracks_meta`) aux clips qu'elle reçoit.
A_M24D = ("{src:srcRef,clips:cl,\n"
          "       lang:lang,cps:subsN(style.maxChars,42)})")
R_M24D = ("{src:srcRef,clips:cl,\n"
          "       /* P13 — les pistes du projet : la route y lit la piste de\n"
          "          dialogue (même loi que le rendu). */\n"
          "       tracks:props.srcTracks||null,\n"
          "       lang:lang,cps:subsN(style.maxChars,42)})")
# M24e — la pastille annonce CE QUI PART, l'infobulle nomme les sources.
A_M24E = "var trAll=subsCostOf(trFree,subsN(props.dur,0),lang);"
R_M24E = (
    "/* P13 — la pastille annonce CE QUI PART : la somme des durées des clips\n"
    "     de la piste de dialogue porteurs d'une source (sinon la première\n"
    "     V1), par la fonction pure de la couche ; la durée du projet ne sert\n"
    "     plus que quand rien n'est à envoyer. L'infobulle nomme les sources\n"
    "     (libellé, nombre, secondes) avant le prix — jamais quand le geste ne\n"
    "     peut pas partir (`ko` : aucun moteur configuré, bouton désactivé) :\n"
    "     l'infobulle d'un geste impossible ne commence pas par « Envoyé ». */\n"
    "  var dzSsAll=DzTracks.subsSources(props.srcClips,props.srcTracks);\n"
    "  var trAll=subsCostOf(trFree,dzSsAll.total>0?dzSsAll.total\n"
    "    :subsN(props.dur,0),lang);\n"
    '  if(!trAll.free&&!trAll.ko&&dzSsAll.dit)trAll.apres=dzSsAll.dit+" "+trAll.apres;')
# M24f — la langue « auto » en tête, et dix langues de plus. CONNAISSANCE
# EXTERNE AU DÉPÔT, déclarée comme telle : nl, pl, ru, uk, tr, ar, ja, zh,
# ko, hi sont des codes ISO-639-1, transmis tels quels (ElevenLabs
# `language_code`, OpenAI `language`) — le fournisseur tranche ce qu'il
# accepte ; rien dans le dépôt ne les valide. Le DÉFAUT reste « fr »
# (`localStorage.getItem("dz_subs_lang")||"fr"`, intouché, 1/1 mesuré).
A_M24F = ('var SUBS_LANGS=[["fr","français"],["en","anglais"],["es","espagnol"],\n'
          '  ["de","allemand"],["it","italien"],["pt","portugais"]];')
R_M24F = ('/* P13 — « auto » en TÊTE : la route transmet `None` au moteur, qui\n'
          '   détecte lui-même (la branche `if language:` de transcribe() était\n'
          '   morte : la route forçait « fr »). Les dix codes après « pt » sont\n'
          '   une CONNAISSANCE EXTERNE AU DÉPÔT (ISO-639-1), transmis tels quels :\n'
          '   le fournisseur tranche. Le défaut reste « fr ». */\n'
          'var SUBS_LANGS=[["auto","détection par le moteur"],\n'
          '  ["fr","français"],["en","anglais"],["es","espagnol"],\n'
          '  ["de","allemand"],["it","italien"],["pt","portugais"],\n'
          '  ["nl","néerlandais"],["pl","polonais"],["ru","russe"],["uk","ukrainien"],\n'
          '  ["tr","turc"],["ar","arabe"],["ja","japonais"],["zh","chinois"],\n'
          '  ["ko","coréen"],["hi","hindi"]];')
# M24g — sous « auto », la détection n'a rien à contredire : « ok ».
A_M24G = ('var etat=!det.total?"vide":det.sur?(det.code===lang?"ok":"contre")\n'
          '        :"flou";')
R_M24G = ('var etat=!det.total?"vide":det.sur\n'
          '        /* P13 — « auto » n\'affirme aucune langue : la détection n\'a\n'
          '           rien à contredire, l\'état est « ok » (la ligne dit ce qui\n'
          '           a été lu, et sur combien de mots). */\n'
          '        ?((lang==="auto"||det.code===lang)?"ok":"contre")\n'
          '        :"flou";')
# M24h — l'HÔTE passe les pistes au tiroir (`props.srcClips` ne les porte
# pas : c'est une liste de {id,tr,src,name,start,end}, mesuré).
A_M24H = "onPlanFlag:subsPlanFlag})}"
R_M24H = ("onPlanFlag:subsPlanFlag,\n"
          "      /* P13 — les pistes du projet, pour que le tiroir et la route\n"
          "         visent la même piste de dialogue. */\n"
          "      srcTracks:svmTracksOf(proj)})}")
# M24i — l'HÔTE envoie `srcIn` : sans lui, la route ne peut retrancher que
# `start` et un clip ROGNÉ à gauche verrait ses répliques décalées de
# `srcIn` (mesuré : `subsSrcClips` n'écrivait que id/tr/src/name/start/end).
A_M24I = "name:c.name||c.label||null,"
R_M24I = ("name:c.name||c.label||null,\n"
          "               /* P13 — `srcIn` : la route décale de `start − srcIn`. */\n"
          "               srcIn:Math.round(subsNum(c.srcIn)*1e3)/1e3,")
# M24j — l'HÔTE fait partir les clips de la piste de dialogue du projet,
# même sous un autre identifiant que a1 : sans cela, la loi des pistes de
# la route (`tracks`) ne verrait jamais leurs clips (mesuré : le filtre ne
# laissait passer que a1, a3, v1).
A_M24J = ("function subsSrcClips(cs){\n"
          "    return ((cs||clipsRef.current)||[]).filter(function(c){\n"
          '      return c.tr==="a1"||c.tr==="a3"||c.tr==="v1"})')
R_M24J = ("function subsSrcClips(cs){\n"
          "    /* P13 — la piste de dialogue du projet (bus « dialogue », sinon\n"
          "       a1) fait partie de ce que la transcription reçoit, même sous\n"
          "       un autre identifiant : c'est elle que la route vise. */\n"
          "    var dzDial=DzTracks.dialogueTrack(svmTracksOf(proj));\n"
          "    return ((cs||clipsRef.current)||[]).filter(function(c){\n"
          '      return c.tr==="a1"||c.tr==="a3"||c.tr==="v1"||c.tr===dzDial})')

# M24k / M24l / M24m — LES LIBELLÉS SOUS « AUTO » (tour 1, revue du 06/09).
# `subsLangLab("auto")` rend l'entrée du sélecteur, « détection par le
# moteur », que subsCostOf injectait dans des phrases écrites pour un NOM de
# langue (« détection par le moteur · elevenlabs · … », « langue détection
# par le moteur : … »), et la note de détection en état « ok » disait « la
# langue lue est d'accord avec le sélecteur » alors que, sous « auto », le
# sélecteur n'affirme rien (M24g force « ok »). Trois ancres 1/1 (bundle ET
# .bak_montage, mesuré en octets ; M24l et M24m sur deux lignes CRLF).
A_M24K = 'return {txt:subsLangLab(lang)+" · "+subsMoteurNom(court)+" · "+subsUsd(usd)+'
R_M24K = ('/* P13 — sous « auto » la pastille dit « langue auto », pas l\'entrée du\n'
          '     sélecteur (« détection par le moteur · elevenlabs · … »). */\n'
          '  return {txt:(lang==="auto"?"langue auto":subsLangLab(lang))+" · "+'
          'subsMoteurNom(court)+" · "+subsUsd(usd)+')
A_M24L = ('", langue "+\n'
          '      subsLangLab(lang)+" : "+subsUsd(usd)+" pour "+subsFr(d,1)+" s de son ("+')
R_M24L = ('", langue "+\n'
          '      /* P13 — sous « auto » : « détectée par le moteur ». */\n'
          '      (lang==="auto"?"détectée par le moteur":subsLangLab(lang))+" : "+'
          'subsUsd(usd)+" pour "+subsFr(d,1)+" s de son ("+')
A_M24M = ('title:etat==="ok"\n'
          '          ?"La langue lue sur le contenu est d\'accord avec le sélecteur : "+')
R_M24M = ('title:etat==="ok"\n'
          '          /* P13 — sous « auto » le sélecteur n\'affirme rien : la ligne dit\n'
          '             ce que le moteur fera, et ce que le contenu a montré. */\n'
          '          ?(lang==="auto"?"Sous « auto » le moteur détecte lui-même la langue ; '
          'lue sur le contenu : "\n'
          '            :"La langue lue sur le contenu est d\'accord avec le sélecteur : ")+')

# ══ P14 — DEUX SORTES DE PISTES VIDÉO, ET V3 N'EST PLUS UN FANTÔME ═════════
#
# LE DÉFAUT, MESURÉ (06/09/2026, en octets, bundle ET .bak_montage). Le seul
# geste vivant qui ajoute une piste vidéo (« vidéo » du groupe PISTES de la
# barre flottante) fabriquait `v`+n libre habillé « overlay » — et le rendu
# traite TOUTE piste vidéo ≠ v1 en incrustation (montage_service
# `_tracks_meta`, `kind == "video" and tid != "v1"`). Mais l'écran, lui,
# codait « v2 » EN DUR : NEUF portes (`"v2"` dans le code de l'écran, hors
# démo `svmDemoClips`, table `SVM_TRACKS` et greffon libsend) et QUATRE
# verrous de piste (`trackStRef.current.v2`, 8 occurrences = 4 sites × 2).
# Le plan n'en nommait que quatre (aperçu, payload, inspecteur, losanges) ;
# les cinq autres — alignement 3×3 (`svmOvAlign`), « ◇ position ici »
# (`svmMpHere`), poignées du lecteur (`ovHandleDown`), flèches (`ovArrow`)
# et Échap (`ovEsc`) du clavier — auraient laissé à V3 un inspecteur dont
# aucun champ n'écrit et un cadre qu'aucune poignée ne saisit. Dès que V2
# existait, « vidéo » créait v3, et un clip posé dessus était un FANTÔME :
# invisible dans l'aperçu, sans inspecteur, parti cover plein cadre au
# rendu. La sauvegarde de l'utilisateur porte tracks [v3, v2, v1, a1, a2,
# a3, s1] — c'est exactement cette piste.
#
# LA RÈGLE, ÉCRITE UNE FOIS : `DzTracks.isOverlayTrack(trId, tracks)` —
# « piste de genre vidéo autre que v1 », le genre lu dans les pistes du
# projet (`dzTracksRef.current`, la ref de M16ref relue à chaque rendu) et
# sinon dans l'initiale de l'identifiant, comme `trackKind` du bundle. Les
# treize sites la lisent ; aucun ne garde « v2 ».
#
# LE VERROU SUIT LA PISTE : `trackStRef.current[k.tr]` au lieu de `.v2` —
# c'est la forme que R_M22A emploie déjà pour la piste de dialogue
# (`trackStRef.current[t]&&trackStRef.current[t].l`).
#
# L'ORDRE D'EMPILEMENT DE L'APERÇU (M25a/M25b). Mesuré : `ov` reçoit ses
# enfants par `appendChild` dans l'ordre de `Object.keys(act)` — l'ordre des
# CLIPS — et un enfant déjà là n'est jamais déplacé ; deux pistes
# d'incrustation se superposaient donc au hasard, quand le rendu compose la
# piste listée le plus haut AU-DESSUS (`layer` = `reversed(ov)`,
# montage_service 204-207). `DzTracks.overlayOrder` rend l'ordre d'ajout au
# DOM (le plus bas d'abord) ; la boucle le suit, et REMET EN QUEUE un enfant
# déjà là quand l'ordre a changé (`appendChild` déplace sans recréer :
# observateur et gestionnaires conservés). GARDE DE SIGNATURE, comme
# `_svmTfSig` juste en dessous : `ov._dzOrdSig` mémorise l'ordre ; tant que
# l'ensemble actif et son ordre ne bougent pas, AUCUNE écriture DOM. Un
# enfant CRÉÉ pendant la boucle force la remise en queue de ceux qui le
# suivent (`dzReord=!0`) : il est né en fin de liste, ceux d'au-dessus
# doivent repasser après lui.
#
# CE QUE LE MONTAGE ACTUEL DE L'UTILISATEUR DEVIENT : sa piste v3 (habillée
# « overlay » à la restauration, le payload n'a pas de type) devient VISIBLE
# dans l'aperçu, avec inspecteur, poignées, clavier ; ses clips éventuels y
# restent des incrustations, et le rendu ne change pas d'un octet.
#
# ANCRES : chacune vaut EXACTEMENT 1 dans le bundle ET dans .bak_montage,
# mesurée en octets (CRLF) le 06/09/2026 ; `if(!c||c.tr!=="v2"||!c.src)return;`
# vaut DEUX (svmOvAlign, svmMpHere), d'où les ancres à trois lignes qui
# nomment la fonction. Aucune ne tombe dans le bloc `defaultLen…sfxInsert`
# que le harnais [3-bis] exécute (918872–928557 ; la plus proche, le
# payload, est à 937723 — mesuré).
A_M25A = ('      if(k.tr==="v2"&&k.src&&(k.src.job_id||k.src.image)'
          '&&k.start<=t&&t<k.end)act[k.id]=k});')
R_M25A = (
    "      if(DzTracks.isOverlayTrack(k.tr,dzTracksRef.current)&&k.src&&"
    "(k.src.job_id||k.src.image)&&k.start<=t&&t<k.end)act[k.id]=k});\n"
    "    /* P14 — l'ORDRE d'empilement suit l'ordre des pistes (la plus haute\n"
    "       listée au-dessus, même loi que `layer` au rendu) : `dzOrd` est\n"
    "       l'ordre d'ajout au DOM, le plus bas d'abord ; `dzReord` ne vaut\n"
    "       vrai que si l'ensemble actif ou son ordre a changé — sinon aucune\n"
    "       écriture DOM, comme la garde de signature de la transformation. */\n"
    "    var dzOrd=DzTracks.overlayOrder(Object.keys(act),cs,dzTracksRef.current),\n"
    '        dzOrdSig=dzOrd.join("|"),dzReord=ov._dzOrdSig!==dzOrdSig;\n'
    "    ov._dzOrdSig=dzOrdSig;")
A_M25B = ('    Object.keys(act).forEach(function(id){\n'
          '      var k=act[id],el=null;\n'
          '      for(var i2=0;i2<ov.children.length;i2++){\n'
          '        if(ov.children[i2]._svmId===id){el=ov.children[i2];break}}\n'
          '      if(!el){var it2=livePoolGet(k.src,"o");el=it2.el;\n'
          '        el._svmId=id;el._svmKey=livePoolKey(k.src,"o");ov.appendChild(el);\n'
          '        if(tfRoRef.current)tfRoRef.current.observe(el)}')
R_M25B = (
    "    dzOrd.forEach(function(id){\n"
    "      var k=act[id],el=null;\n"
    "      for(var i2=0;i2<ov.children.length;i2++){\n"
    "        if(ov.children[i2]._svmId===id){el=ov.children[i2];break}}\n"
    '      if(!el){var it2=livePoolGet(k.src,"o");el=it2.el;\n'
    '        el._svmId=id;el._svmKey=livePoolKey(k.src,"o");ov.appendChild(el);\n'
    "        if(tfRoRef.current)tfRoRef.current.observe(el);dzReord=!0}\n"
    "      /* P14 — un enfant déjà là est REMIS EN QUEUE quand l'ordre a\n"
    "         changé : appendChild déplace sans recréer ; rien n'est touché\n"
    "         quand `dzReord` est faux. */\n"
    "      else if(dzReord)ov.appendChild(el);")
A_M25C = '        if(c.tr==="v2"){'
R_M25C = '        if(DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)){'
A_M25D = '    if(!sel||sel.tr!=="v2"||!sel.src)return null;'
R_M25D = ('    if(!sel||!DzTracks.isOverlayTrack(sel.tr,dzTracksRef.current)'
          '||!sel.src)return null;')
A_M25E = 'tr.id==="v2"?(svmMpOf(c)||[]).map(function(p,pi){'
R_M25E = ('DzTracks.isOverlayTrack(tr.id,dzTracksRef.current)'
          '?(svmMpOf(c)||[]).map(function(p,pi){')
# Les quatre verrous : ovOvDown (sélection seule), ovOvDbl, ovHandleDown,
# ovArrow. `k`/`c` est le clip lu deux lignes plus haut dans chaque site.
A_M25F = ('    if(trackStRef.current.v2&&trackStRef.current.v2.l)return; '
          '/* verrou : sélection seule */')
R_M25F = ('    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return; '
          '/* verrou : sélection seule */')
A_M25G = ('    if(!k||(!svmOvTfOf(k)&&!svmMpOf(k)))return;\n'
          '    if(trackStRef.current.v2&&trackStRef.current.v2.l)return;')
R_M25G = ('    if(!k||(!svmOvTfOf(k)&&!svmMpOf(k)))return;\n'
          '    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return;')
A_M25H = ('    if(!k||k.tr!=="v2"||!k.src)return;\n'
          '    if(trackStRef.current.v2&&trackStRef.current.v2.l)return;\n'
          '    if(e.button!==0)return;')
R_M25H = ('    if(!k||!DzTracks.isOverlayTrack(k.tr,dzTracksRef.current)||!k.src)return;\n'
          '    if(trackStRef.current[k.tr]&&trackStRef.current[k.tr].l)return;\n'
          '    if(e.button!==0)return;')
A_M25I = ('  function svmOvAlign(gx,gy){\n'
          '    var c=clipsRef.current.find(function(k){return k.id===selRef.current});\n'
          '    if(!c||c.tr!=="v2"||!c.src)return;')
R_M25I = ('  function svmOvAlign(gx,gy){\n'
          '    var c=clipsRef.current.find(function(k){return k.id===selRef.current});\n'
          '    if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return;')
A_M25J = ('  function svmMpHere(){\n'
          '    var c=clipsRef.current.find(function(k){return k.id===selRef.current});\n'
          '    if(!c||c.tr!=="v2"||!c.src)return;')
R_M25J = ('  function svmMpHere(){\n'
          '    var c=clipsRef.current.find(function(k){return k.id===selRef.current});\n'
          '    if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return;')
A_M25K = ('      if(!c||c.tr!=="v2"||!c.src)return !1;\n'
          '      if(ovKeysOffRef.current)return !1;\n'
          '      if(trackStRef.current.v2&&trackStRef.current.v2.l)return !1;')
R_M25K = ('      if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)||!c.src)return !1;\n'
          '      if(ovKeysOffRef.current)return !1;\n'
          '      if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l)return !1;')
A_M25L = '      if(!c||c.tr!=="v2"||!c.src||ovKeysOffRef.current)return !1;'
R_M25L = ('      if(!c||!DzTracks.isOverlayTrack(c.tr,dzTracksRef.current)'
          '||!c.src||ovKeysOffRef.current)return !1;')


# ══ P16 — TRADUIRE LES RÉPLIQUES (06/09/2026, tâche 22) ═════════════════════
#
# LE MANQUE, MESURÉ : aucune route ni aucun geste de traduction de
# sous-titres n'existait dans l'application (le seul `translate_video` du
# dépôt est HeyGen, jamais appelé) — remontée de l'utilisateur : « … ne
# serait-ce que pour pouvoir la traduire ». Le serveur gagne
# POST /api/subtitles/translate et GET /api/subtitles/translate/estimate
# (routes.py, service subs_translate_service — contrat strict « N lignes
# numérotées », 400 si le compte diffère, temps conservés) ; l'écran gagne,
# dans la rangée `.sub-trrow` de l'onglet Répliques, une langue CIBLE
# (« vers », mêmes langues que SUBS_LANGS SANS « auto » — on traduit VERS
# une langue nommée) et un bouton « Traduire vers … » avec pastille de coût.
#
# DEUX sections sur le bloc subs inliné (subs.js INTOUCHABLE — même règle
# que M24) : M26a pose l'état (cible `dz_subs_to`, défaut « en » quand la
# transcription est « fr » — subsTrDefaut de la couche), l'estimation (GET
# /translate/estimate, re-demandée à 400 ms de battement quand le texte ou
# la cible change — une petite fonction dédiée, PAS une copie de SUBS_EST)
# et le geste (dzTraduire) ; M26b pose le sélecteur et le bouton. Le cœur
# calculable (corps de la requête, droit de partir, libellés, fusion du
# résultat) vit dans la couche (DzTracks.subsTr*), joué sous node par le
# banc bundle.
#
# LE GESTE EMPLOIE fetch DIRECT plutôt que subsPost, et c'est MESURÉ :
# subsJson jette « réponse non JSON » sur tout `!res.ok` et PERDRAIT la
# raison du 400/502 que la route écrit — ici elle est LUE dans le corps
# JSON de l'erreur puis AFFICHÉE (« Traduction refusée (400) : la
# traduction a rendu 2 lignes sur 3 … »).
#
# CE QU'« ANNULER » FAIT, MESURÉ : l'application passe par
# props.onChange(next,!0) → subsCommit de l'hôte, `heavy` vrai → UN
# pushHistory() AVANT l'écriture — un « Annuler » de la timeline restaure
# les répliques d'avant ; S1 verrouillée, subsCommit refuse et le dit,
# rien n'est écrit. L'infobulle du bouton (subsTrTitle, couche) écrit
# cette vérité mot pour mot.
#
# Ancres mesurées le 06/09 (en octets, CRLF) : chacune 1/1 dans le bundle
# ET dans .bak_montage ; A_M26B est multiligne (0 en LF, 1 en CRLF).
# Les noms neufs (dzTo, dzTe, dzTrN, dzTrChars, dzTraduire, dz_subs_to,
# subsTr*) étaient 0/0 des deux côtés EN RECHERCHE BORNÉE (… —
# mesuré : `dzTo` et `subsTr` NUS apparaissent dans des identifiants
# plus longs du bundle, 12 et 3 fois ; le banc borne donc lui aussi). Aucune des deux ancres ne tombe dans
# le bloc `defaultLen…sfxInsert` que le harnais [3-bis] exécute. AUCUN
# confirm() : la pastille et l'infobulle sont la convention du dépôt.
# M26a — l'état, l'estimation, le geste (juste après les hooks du tiroir,
# `segs`/`lang`/`trJob` déjà déclarés, AVANT le `if(!open)return null`).
A_M26A = "  x.useEffect(function(){if(open)subsProbe()},[open]);"
R_M26A = (
    "  x.useEffect(function(){if(open)subsProbe()},[open]);\n"
    "  /* P16 — LA CIBLE et le COÛT de la traduction, puis le geste. */\n"
    "  var s9=x.useState(function(){\n"
    '    try{var dzV=localStorage.getItem("dz_subs_to");if(dzV)return dzV}catch(_e){}\n'
    "    return DzTracks.subsTrDefaut(lang)}),dzTo=s9[0],setDzTo=s9[1];\n"
    '  var s9b=x.useState({st:"?"}),dzTe=s9b[0],setDzTe=s9b[1];\n'
    "  var dzTrN=segs.length,\n"
    '      dzTrChars=segs.reduce(function(a,sg){return a+String(sg.text||"").length},0);\n'
    "  x.useEffect(function(){\n"
    '    if(!open||!dzTrN){setDzTe({st:"vide"});return}\n'
    "    var dzKill=setTimeout(function(){\n"
    '      subsJson("/api/subtitles/translate/estimate?chars="+dzTrChars+\n'
    '        "&target="+encodeURIComponent(dzTo)).then(function(a){\n'
    '        setDzTe(a&&a.ok?{st:"ok",ok:!0,usd:subsN(a.usd,0),\n'
    '            provider:String(a.provider||"")}\n'
    '          :{st:"none",reason:String((a&&a.reason)||\n'
    '            "Aucune clé LLM configurée (Réglages).")})},\n'
    '      function(){setDzTe({st:"down",reason:"Le backend ne répond pas : "+\n'
    "        \"le coût ne peut pas être annoncé, donc rien n'est lancé.\"})})},400);\n"
    "    return function(){clearTimeout(dzKill)}},[open,dzTrN,dzTrChars,dzTo]);\n"
    "  function dzTraduire(){\n"
    "    var dzBody=DzTracks.subsTrBody(segs,dzTo,lang);\n"
    "    if(!dzBody||(trJob&&trJob.busy))return;\n"
    '    setTrJob({busy:!0,step:"traduction de "+subsPl(dzTrN,"réplique")+\n'
    '      " vers "+subsLangLab(dzTo)+"…",pct:0});\n'
    "    /* fetch DIRECT : subsPost jette « réponse non JSON » sur tout\n"
    "       !res.ok (mesuré) et perdrait la raison du 400/502 que la route\n"
    "       écrit — ici elle est lue puis affichée. */\n"
    '    fetch("/api/subtitles/translate",{method:"POST",\n'
    '      headers:{"Content-Type":"application/json"},\n'
    "      body:JSON.stringify(dzBody)})\n"
    "      .then(function(res){return res.json().then(\n"
    "        function(dd){return {res:res,d:dd}},\n"
    "        function(){return {res:res,d:null}})})\n"
    "      .then(function(o){\n"
    "        setTrJob(null);\n"
    "        if(!o.res.ok){\n"
    '          note2("Traduction refusée ("+o.res.status+") : "+\n'
    '            String((o.d&&o.d.detail)||"raison non fournie"));return}\n'
    "        var dzNext=DzTracks.subsTrApply(segs,(o.d&&o.d.segments)||[],subsLabelOf);\n"
    '        if(!dzNext){note2("Réponse illisible : le compte des répliques "+\n'
    "          \"ne correspond pas — rien n'a été écrit.\");return}\n"
    "        if(props.onChange)props.onChange(dzNext,!0);\n"
    "        note2(DzTracks.subsTrNote(dzNext.length,dzTo,SUBS_LANGS))},\n"
    "      function(){setTrJob(null);\n"
    '        note2("Traduction indisponible : POST /api/subtitles/translate "+\n'
    '          "ne répond pas — le backend est-il lancé ?")})}')
# M26b — le sélecteur « vers » et le bouton, dans la rangée `.sub-trrow`,
# juste après le sélecteur de langue de la transcription. Les classes
# `.sub-trlang`/`.sub-sel` sont RÉUTILISÉES : aucune règle CSS neuve
# (mesuré : .sub-trrow porte flex-wrap:wrap, subs.css — la rangée replie
# ses enfants toute seule).
A_M26B = ('          children:SUBS_LANGS.map(function(o){\n'
          '            return r.jsx("option",{value:o[0],children:o[1]},o[0])})},"s")]},"lg"),')
R_M26B = (
    "          children:SUBS_LANGS.map(function(o){\n"
    '            return r.jsx("option",{value:o[0],children:o[1]},o[0])})},"s")]},"lg"),\n'
    "      /* P16 — TRADUIRE : la cible (sans « auto » — on traduit VERS une\n"
    "         langue nommée), puis le bouton qui dit ce qu'il remplace, son\n"
    "         prix, et ce qu'« Annuler » fait (mesuré — subsTrTitle). */\n"
    '      r.jsxs("label",{className:"sub-trlang",children:[\n'
    '        r.jsx("span",{className:"sub-trlangl",children:"vers"},"l"),\n'
    '        r.jsx("select",{className:"sub-sel",value:dzTo,\n'
    '          "aria-label":"Langue cible de la traduction",\n'
    '          title:"Langue vers laquelle « Traduire » réécrit le texte des "+\n'
    '            "répliques. Leurs temps ne bougent pas.",\n'
    "          onChange:function(e){var dzV=e.target.value;setDzTo(dzV);\n"
    '            try{localStorage.setItem("dz_subs_to",dzV)}catch(_e){}},\n'
    '          children:SUBS_LANGS.filter(function(o){return o[0]!=="auto"})\n'
    "            .map(function(o){\n"
    '              return r.jsx("option",{value:o[0],children:o[1]},o[0])})},"s")]},"tg"),\n'
    "      (function(){\n"
    "        var dzOn=DzTracks.subsTrEnabled(dzTrN,dzTe,!!(trJob&&trJob.busy));\n"
    '        return subsActBtn({fam:"fix",\n'
    "          label:DzTracks.subsTrLabel(dzTo,SUBS_LANGS),\n"
    '          but:"traduire les répliques",quiet:!0,disabled:!dzOn.on,\n'
    '          cost:trJob&&trJob.busy?"en cours…":dzTe.ok\n'
    '            ?subsLangLab(dzTo)+" · "+(dzTe.provider||"LLM")+" · "+subsUsd(dzTe.usd)\n'
    '            :(dzTe.st==="vide"?"aucune réplique":"coût indisponible"),\n'
    "          apres:dzOn.on?DzTracks.subsTrTitle(dzTrN):dzOn.pourquoi,\n"
    '          onClick:dzTraduire,k:"trad"})})(),')

# ══════════════════════════════════════════════════════════════════════════
# D-0 (21/09/2026) — L'HISTORIQUE COMPLET, CÂBLÉ. Le cœur est PUR et vit dans
# la couche (`DzTracks.histSnap` / `histApply`, joués sous node par
# backend/tests/test_montage_historique.py) ; ces sept sections le BRANCHENT.
# ══════════════════════════════════════════════════════════════════════════

# ── H1 (D-0) : la ref du projet et l'instantané complet, à côté de histRef ─
# `pushHistory`, `undo` et `redo` sont des useCallback à dépendances vides :
# ils ne voient JAMAIS `proj` — d'où une ref relue à chaque rendu, même motif
# que `dzTracksRef` (M16ref). MESURÉ : `proj` est déclaré PLUS HAUT dans le
# même corps de composant (`var stP=x.useState({demo:!0,…}),proj=…`), donc
# AVANT cette ligne ; l'affectation à chaque rendu lit bien la valeur du
# rendu courant et non `undefined`. Pas de chiffre ici : la distance en
# octets dépend de la borne qu'on choisit et se périme au premier patch
# amont — c'est l'ORDRE qui compte, et il est stable.
# `dzmHistHost()` est LE seul lecteur de l'état courant pour l'historique :
# les gestes qui capturaient h0 à la main passent par lui (H5), les autres
# gardent leur {clips, mixDb} — histApply s'en accommode (banc L0 [1],
# « partiel »).
# L'ANCRE REPREND LE COMMENTAIRE DE FIN DE LIGNE (« piles annuler /
# rétablir ») : sans lui, le remplacement l'aurait poussé sur la dernière
# ligne insérée, où il aurait décrit `dzDurHistAt` au lieu de `histRef`.
A_H1 = "var histRef=x.useRef({u:[],r:[]}); /* piles annuler / rétablir */"
R_H1 = (A_H1 + "\n"
        "  var dzProjRef=x.useRef(null);dzProjRef.current=proj;\n"
        "  function dzmHistHost(){return DzTracks.histSnap({clips:clipsRef.current,"
        "mixDb:mixRef.current,proj:dzProjRef.current})}\n"
        "  var dzStyleHistAt=x.useRef(0);\n"
        "  var dzDurHistAt=x.useRef(0);")

# ── H2 (D-0) : ce que pushHistory empile sans argument ─────────────────────
A_H2 = "h.u.push(prev||{clips:clipsRef.current,mixDb:mixRef.current});"
R_H2 = "h.u.push(prev||dzmHistHost());"

# ── H3 / H4 (D-0) : undo et redo restaurent TOUT l'instantané ──────────────
# Le corps entier est l'ancre : `setClips(s.clips);` seul apparaît deux fois.
# `histApply` IGNORE DÉLIBÉRÉMENT la clé `clips` (les clips ne vivent pas
# dans `proj` mais dans `clipsRef`/`setClips`) : c'est le `if("clips" in s)`
# juste au-dessus qui les rend, et lui seul.
A_H3 = ("var undo=x.useCallback(function(){\n"
        "    var h=histRef.current;if(!h.u.length)return;\n"
        "    var s=h.u.pop();\n"
        "    h.r.push({clips:clipsRef.current,mixDb:mixRef.current});\n"
        "    if(h.r.length>60)h.r.shift();\n"
        "    setClips(s.clips);\n"
        "    setProj(function(p){return Object.assign({},p,{mixDb:s.mixDb})});\n"
        "    setDirty(!0);setHistTick(function(t){return t+1})},[]);")
R_H3 = ("var undo=x.useCallback(function(){\n"
        "    var h=histRef.current;if(!h.u.length)return;\n"
        "    var s=h.u.pop();\n"
        "    h.r.push(dzmHistHost());\n"
        "    if(h.r.length>60)h.r.shift();\n"
        "    if(\"clips\" in s)setClips(s.clips);\n"
        "    /* D-0 — pistes, durée, style S1, plage, marqueurs reviennent avec\n"
        "       le mixage ; SVM_TRACK_BUS suit les pistes restaurées. `histApply`\n"
        "       ne touche PAS aux clips : c'est la ligne du dessus qui les rend.\n"
        "       L'APPEL EST NU EXPRÈS : `s.tracks` vaut `undefined` quand le\n"
        "       projet d'avant n'avait pas la clé, et `svmTrackBusSync` retombe\n"
        "       alors sur DZM_DEFAULT_TRACKS — la table même que `svmTracksOf`\n"
        "       rend sans `proj.tracks` (mesuré sous node le 21/09/2026 : les\n"
        "       trois bus sont identiques). */\n"
        "    if(\"tracks\" in s)svmTrackBusSync(s.tracks);\n"
        "    setProj(function(p){return DzTracks.histApply(p,s)});\n"
        "    setDirty(!0);setHistTick(function(t){return t+1})},[]);")
A_H4 = A_H3.replace("var undo=", "var redo=").replace("!h.u.length", "!h.r.length") \
           .replace("h.u.pop()", "h.r.pop()").replace("h.r.push(", "h.u.push(") \
           .replace("h.r.length>60)h.r.shift", "h.u.length>60)h.u.shift")
R_H4 = R_H3.replace("var undo=", "var redo=").replace("!h.u.length", "!h.r.length") \
           .replace("h.u.pop()", "h.r.pop()").replace("h.r.push(", "h.u.push(") \
           .replace("h.r.length>60)h.r.shift", "h.u.length>60)h.u.shift")

# ── H5 (D-0) : le h0 du glisser de clip capture l'état ENTIER ──────────────
# Sans quoi le relâchement de M17f (qui allonge la durée) empilait un h0 sans
# `dur`, et « Annuler » rendait les clips mais pas la timeline.
A_H5 = "var h0={clips:clipsRef.current,mixDb:mixRef.current},snapAt=null;"
R_H5 = "var h0=dzmHistHost(),snapAt=null;"

# ── H6 (D-0) : le réglage de durée entre dans l'historique ─────────────────
# PAS DE SECTION H6. MESURÉ le 21/09/2026 : son ancre — la ligne `onSet` du
# contrôle de durée — n'existe pas dans le bundle d'entrée, elle est POSÉE
# par R_M17G. Une section de plus y aurait cassé DEUX invariants du banc :
# `--check`, qui compte les ancres sur le seul état PRÉ-patch, déclarait H6
# introuvable ; et la boucle générique `M17g-transport-duree_remplace`
# comptait 0, puisque R_M17G n'apparaissait plus verbatim dans le bundle.
# La modification est donc REPLIÉE dans R_M17G, exactement comme M10 dans
# R_M8 et M9c dans R_M9b. Le banc la mesure sous node (`ct_hist`).

# ── H7 (D-0) : le style S1 entre dans l'historique (même fenêtre) ──────────
A_H7 = "function subsStyleSet(patch){"
R_H7 = ("function subsStyleSet(patch){\n"
        "    var dzN=Date.now();if(dzN-dzStyleHistAt.current>600)pushHistory();"
        "dzStyleHistAt.current=dzN;")

# ── D-11 (21/09/2026) : LA PLAGE D'ENTREE / SORTIE ─────────────────────────
# Trois sections seulement : les deux dernieres du plan (« R4 » la sauvegarde,
# « R5 » la restauration) sont REPLIEES dans R_M6 et R_M7, dont elles visaient
# un texte POSE — voir les commentaires la-bas.
#
# ── R1 (D-11) : quatre actions dans SVM_ACTIONS (remappables, listees) ─────
# Lettres MESUREES libres le 21/09/2026 sur la table SVM_ACTIONS du bundle
# d'entree : I, U, X et Maj+X n'y sont pris par personne (B D F G J K L M N R
# S T le sont, C sous Alt, Z sous Ctrl et sous Maj).
A_R1 = ' {id:"ripple",sec:"Montage",lbl:"ripple — refermer les trous",combo:"R"},'
R_R1 = (A_R1 + "\n"
        ' {id:"range_in",sec:"Montage",lbl:"plage : point d\'entrée à la tête",combo:"I"},\n'
        ' {id:"range_out",sec:"Montage",lbl:"plage : point de sortie à la tête",combo:"U"},\n'
        ' {id:"range_clear",sec:"Montage",lbl:"plage : effacer",combo:"X"},\n'
        ' {id:"range_cut",sec:"Montage",lbl:"plage : couper (toutes pistes, ripple)",combo:"Maj+X"},'
        # -- « K1 » (D-5, 21/09/2026) : LES QUATRE ACTIONS DES MARQUEURS ---
        # REPLIEES ICI, et c'est une MESURE : la ligne `range_cut` ci-dessus
        # vaut 0 dans .bak_montage (c'est CE remplacement qui l'ecrit) et 1
        # dans le bundle livre -- une section qui la prendrait pour ancre
        # serait refusee par `--check`, qui ne regarde que l'etat pre-patch.
        # Meme technique que R4/R5 dans R_M6/R_M7 et H6 dans R_M17G.
        # COMBOS MESUREES LIBRES le 21/09/2026 sur la table SVM_ACTIONS du
        # bundle d'entree : elle porte « M » (muet) mais NI « Maj+M », NI
        # « Ctrl+M », NI « Ctrl+haut », NI « Ctrl+bas ». Aucune des quatre
        # n'est dans SVM_COMBO_RESERVED (Ctrl+R/W/T/N, Ctrl+Maj+I/J/C,
        # Alt+F4).
        # LE NOM DES FLECHES SOUS CTRL SE LIT DANS `svmComboOfEvent` :
        # SVM_EV_NAMES mappe ArrowUp / ArrowDown sur les CARACTERES fleches
        # et le prefixe « Ctrl+ » est concatene tel quel -- donc « Ctrl+ »
        # suivi de la fleche, jamais « Ctrl+ArrowUp ».
        # « Maj+M » NE SERA PAS CONFONDUE AVEC « M » (muet) : le dispatch
        # cherche d'abord `m[combo]` EXACT et ne retombe sur la variante
        # sans Maj que lorsque la combo complete est inconnue de la table.
        # Elle y est desormais.
        '\n {id:"marker_toggle",sec:"Montage",lbl:"marqueur : poser / retirer a la tete",combo:"Maj+M"},\n'
        ' {id:"marker_prev",sec:"Montage",lbl:"marqueur precedent",combo:"Ctrl+\u2191"},\n'
        ' {id:"marker_next",sec:"Montage",lbl:"marqueur suivant",combo:"Ctrl+\u2193"},\n'
        ' {id:"marker_index",sec:"Montage",lbl:"marqueurs : l\'index",combo:"Ctrl+M"},')

# ── R2 (D-11) : la branche de dispatch ─────────────────────────────────────
# PORTEE MESUREE dans `onKey` (meme corps de composant, closure) : `phRef`,
# `clipsRef`, `trackStRef`, `fireNote`, `pushHistory`, `setProj`, `setClips`,
# `setDirty` y sont declares par le bundle ; `svmTracksOf` est une fonction de
# la couche injectee dans le MEME scope module ; `dzProjRef` vient de H1, qui
# passe avant (ordre de PATCHES). `blade()`, juste au-dessus, lit deja
# `phRef.current`.
# SORTIE TOT (revue du 21/09/2026). La branche I / U / X calcule D'ABORD la
# plage suivante, puis la compare a l'ancienne : `dzmRangeSet` rend
# `range||null` quand rien ne change (tete illisible, `which` inconnu) et
# `null` sur « clear ». Sans cette sortie tot, chaque frappe sterile empilait
# un instantane d'historique et allumait « NON ENREGISTRE » pour rien.
# `dzCur` REPLIE `undefined` SUR `null`, et ce n'est pas une precaution : le
# projet de DEPART du bundle est `useState({demo:!0,name:"teaser_abyss",...})`
# -- MESURE du 21/09/2026, il n'a PAS de cle `range`, et il n'en gagne une que
# par svmApplyProject (R_M7), c'est-a-dire apres un chargement de projet. Sur
# la demo, `proj.range` vaut donc `undefined` ; `rangeSet` rend `null` ; et
# `null===undefined` est FAUX. X sur une plage vide au demarrage poussait
# l'historique et allumait « NON ENREGISTRE » -- exactement le defaut que la
# sortie tot devait fermer. Compare a `dzCur`, X sort.
# EGALITE DE VALEURS en second terme : `rangeSet` construit un objet NEUF a
# chaque "in" / "out", meme quand la tete n'a pas bouge d'un pouce. I puis I
# au meme playhead rendait deux objets distincts mais IDENTIQUES en valeurs,
# et l'identite seule ne pouvait pas le voir.
# UNE DEMI-PLAGE SE DIT (M-4) : apres I seul, ou apres U seul, une note dit
# quelle touche pose l'autre bout. La bande de la regle, elle, se tait tant
# que la plage n'est pas COMPLETE (R3) : sans la note, l'utilisateur n'avait
# AUCUN retour entre la premiere frappe et la seconde.
# `cutOpts` : la paire {loopTracks, locked} etait construite ICI et dans
# R_M12, a l'identique. Elle vit maintenant dans la couche, une seule fois.
# ECART ASSUME CONTRE LE PLAN, MESURE : `dzmRippleCut` rend
# `{clips, removed}` ou `removed` est la LONGUEUR RETIREE EN SECONDES
# (`return {clips:out,removed:len}`, montage.js), PAS un nombre de clips. La
# note du plan disait « N clip(s) retire(s) » et aurait donc menti a chaque
# coupe. Elle dit maintenant les secondes.
A_R2 = 'if(id==="ripple"){setRipple(function(v){return !v});return}'
R_R2 = (A_R2 + "\n"
        '      if(id==="range_in"||id==="range_out"||id==="range_clear"){'
        'var dzW=id.slice(6);'
        'var dzCur=(dzProjRef.current&&dzProjRef.current.range)||null;'
        'var dzNx=DzTracks.rangeSet(dzCur,dzW,phRef.current,'
        'dzProjRef.current&&dzProjRef.current.dur);'
        'if(dzNx===dzCur||(dzNx&&dzCur&&dzNx.in===dzCur.in&&dzNx.out===dzCur.out))return;'
        'pushHistory();setProj(function(p){return Object.assign({},p,{range:dzNx})});'
        'setDirty(!0);'
        # D-2 (21/09/2026) — EFFACER LA PLAGE DÉSARME « remplir la plage ».
        # Sans cette ligne, X laissait `dzModeRef.current` à "remplir"
        # pendant que la chip devenait GRISÉE : le prochain ajout tombait
        # dans le repli silencieux de `dzmInsereUn` (`if(!rg) … ecraser`)
        # et écrasait sous la tête sans un mot. Le mode suit la plage.
        'if(!dzNx&&dzModeRef.current==="remplir")setDzMode("ecraser");'
        'if(dzNx&&dzNx.in!=null&&dzNx.out==null)'
        'fireNote("Entrée à "+dzNx.in.toFixed(2)+" s — U pose la sortie");'
        'else if(dzNx&&dzNx.out!=null&&dzNx.in==null)'
        'fireNote("Sortie à "+dzNx.out.toFixed(2)+" s — I pose l\'entrée");'
        'return}\n'
        '      if(id==="range_cut"){var dzRg=DzTracks.rangeFrom(dzProjRef.current&&dzProjRef.current.range);'
        'if(!dzRg){fireNote("Aucune plage : I pose l\'entrée, U la sortie.");return}'
        'var dzRc=DzTracks.rippleCut(clipsRef.current,dzRg.in,dzRg.out,'
        'DzTracks.cutOpts(dzProjRef.current,trackStRef.current));'
        'pushHistory();setClips(dzRc.clips);'
        'setProj(function(p){return Object.assign({},p,{range:null})});setDirty(!0);'
        # D-2 — même désarmement pour Maj+X, qui met `range:null`.
        'if(dzModeRef.current==="remplir")setDzMode("ecraser");'
        'fireNote("Plage "+dzRg.in.toFixed(2)+" → "+dzRg.out.toFixed(2)+" s coupée sur toutes les pistes — "+dzRc.removed.toFixed(2)+" s retirés, la suite remonte.");return}'
        # -- « K2 » (D-5) : LE DISPATCH DES QUATRE MARQUEURS ---------------
        # REPLIE ICI pour la meme raison que K1 : l'ancre du plan est la
        # branche `range_cut` que CE remplacement-ci pose (0 dans le .bak).
        # PORTEE : `phRef`, `fireNote`, `pushHistory`, `setProj`, `setDirty`
        # et `seekTo` sont declares par le bundle dans le MEME corps de
        # composant ; `dzProjRef` vient de H1 et `setDzMkOn` de K3, tous deux
        # AVANT dans l'ordre de PATCHES. `seekTo` est un `x.useCallback`
        # declare a l'offset 809767 du .bak, la branche de dispatch a
        # 855826 : il precede, et il prend des SECONDES (`setPh(p)` puis
        # `v.currentTime = Math.min(p, v.duration||p)`) -- la meme unite que
        # `markerNext`, qui rend un `t`.
        # LE PLAFOND SE DIT AU LIEU DE SE TAIRE : `markerAdd` rend une COPIE
        # inchangee au-dela de 200 marqueurs (et sur une tete illisible).
        # Sans cette sortie tot, la frappe sterile empilait un instantane
        # d'historique identique et allumait « NON ENREGISTRE » pour rien --
        # exactement le defaut que la sortie tot de la plage a ferme.
        '\n      if(id==="marker_toggle"){'
        'var dzMkL=(dzProjRef.current&&dzProjRef.current.markers)||[];'
        'var dzMkT=Number(phRef.current)||0,dzMkN=DzTracks.markerAdd(dzMkL,dzMkT,{});'
        # LA NOTE NE MENT PLUS SUR LA CAUSE (revue du 21/09/2026) :
        # elle disait « 200 au maximum » meme quand `markerAdd` avait
        # refuse pour une tout autre raison. Les deux cas sont
        # desormais DISTINGUES -- le plafond, et une tete de lecture
        # illisible (`dzmMarkerT` rend `null` sur NaN, sur l'infini,
        # sur un negatif, sur une chaine vide).
        'if(dzMkN.length===dzMkL.length){'
        'fireNote(dzMkL.length>=200'
        '?"Plafond atteint \u2014 200 marqueurs au maximum par montage."'
        ':"T\u00eate de lecture illisible \u2014 marqueur non pos\u00e9.");return}'
        'pushHistory();'
        'setProj(function(p){return Object.assign({},p,{markers:dzMkN})});setDirty(!0);'
        'fireNote(dzMkN.length<dzMkL.length'
        '?("Marqueur retir\u00e9 \u00e0 "+dzMkT.toFixed(2)+" s.")'
        # I-5 : LA COMBO VIENT DE LA KEYMAP VIVANTE, jamais du texte.
        # Les quatre actions sont remappables (panneau « ? ») et une
        # note qui dit « Ctrl+M » apres un remappage MENT.
        # `svmKeyLabel` est declaree DANS ce composant
        # (`return km.byId[id]||…`) : elle lit la keymap fusionnee du
        # rendu courant, exactement comme la chip « lame ».
        ':("Marqueur pos\u00e9 \u00e0 "+dzMkT.toFixed(2)+" s \u2014 "'
        '+svmKeyLabel("marker_index")+" : l\'index."));return}\n'
        '      if(id==="marker_prev"||id==="marker_next"){'
        'var dzMkD=id==="marker_next"?1:-1;'
        'var dzMkG=DzTracks.markerNext(dzProjRef.current&&dzProjRef.current.markers,'
        'phRef.current,dzMkD);'
        'if(dzMkG!=null)seekTo(dzMkG);'
        'else fireNote("Aucun marqueur "+(dzMkD>0?"apr\u00e8s":"avant")+" la t\u00eate.");return}\n'
        '      if(id==="marker_index"){dzMkToggle();return}')

# ── R3 (D-11) : la bande sur la regle, apres la gouttiere ──────────────────
# `DzmRangeBar` rend `null` tant que la plage n'est pas COMPLETE : la regle
# reste exactement celle d'avant jusqu'a ce que I et U aient ete frappes.
A_R3 = 'r.jsx("div",{className:"svm-gutter"}),'
# « K4 » (D-5) : LES LOSANGES DES MARQUEURS, REPLIES ICI. L'ancre du plan
# (« apres RangeBar ») est le texte que CE remplacement-ci pose : 0 dans
# .bak_montage. Ils viennent APRES la bande de plage dans l'ordre du DOM et
# portent un `z-index` superieur (4 contre 3, montage.css) : un marqueur pose
# dans une plage reste cliquable. `DzmMarkers` rend un TABLEAU (`ms.map`), que
# React aplatit dans les enfants de la regle -- pas un conteneur de plus, donc
# rien ne s'interpose entre `.svm-ruler` et les elements absolus qu'elle cale.
R_R3 = (A_R3 + 'r.jsx(DzTracks.RangeBar,{range:proj.range,dur:dur}),'
        'r.jsx(DzTracks.Markers,{markers:proj.markers,dur:dur,onSeek:seekTo}),')

# ── D-3 (21/09/2026) : ROLL, SLIP, SLIDE ───────────────────────────────────
# T1 : les modificateurs sont lus AU POINTERDOWN, une seule fois -- le geste
# ne change pas de nature en cours de route. `svmEdgeAt` a deja pose `edge`
# juste avant, et le verrou de piste a deja rendu la main plus haut : une
# piste verrouillee ne slippe ni ne slide.
A_T1 = "var x0=e.clientX,s0=c.start,e0=c.end,moved=!1,tgt=e.currentTarget;"
R_T1 = (A_T1 + "\n"
        '    var dzSlip=!!e.altKey&&edge==="m",dzSlide=!!e.shiftKey&&!e.altKey&&edge==="m";\n'
        "    var dzSd=Number(c.srcDur)||0;")
# MESURE du 21/09/2026 : `c.srcDur` vaut 0 occurrence dans le bundle -- aucun
# cache de duree de source par clip n'existe cote ecran. `dzSd` vaut donc 0
# et `dzmSlip` n'applique que la borne BASSE (srcIn >= 0) ; la borne haute
# reste inconnue a l'ecran et c'est le rendu qui borne au disponible.
# ECART ASSUME ET DATE : « D-3 : borne haute du slip non bornee a l'ecran ».

# T2 : slip et slide rejouent depuis `h0` (etat du pointerdown), AVANT la
# branche historique de `mv` -- pas de derive, et `up()` n'a rien a
# court-circuiter : MESURE du 21/09/2026, `up()` de `clipDown` ne recalcule
# aucun clip depuis `s0/e0`, il lit `clipsRef.current` pour `fitDur` et
# pousse `h0` dans l'historique. Les deux gestes lui conviennent tels quels.
A_T2 = "      snapAt=null;\n      var w=0,delta=0;"
R_T2 = ("      snapAt=null;\n"
        "      if(dzSlip){setClips(DzTracks.slip(h0.clips,c.id,ds,{srcDur:dzSd}));return}\n"
        "      if(dzSlide){var dzNs=doSnap(s0+ds);setClips(DzTracks.slide(h0.clips,c.id,dzNs-s0));setSnapT(snapAt);return}\n"
        "      var w=0,delta=0;")

# T3 : Alt sur la poignee GAUCHE de l'etendue de transition.
A_T3 = "onPointerDown:function(e){transSpanDown(e,j2.right,-1,j2.t)}}),"
R_T3 = "onPointerDown:function(e){if(e.altKey){dzRollDown(e,j2);return}transSpanDown(e,j2.right,-1,j2.t)}}),"

# T3b : ECART CONTESTE ET ASSUME (21/09/2026). Le plan ne prevoyait que T3,
# mais MESURE : `.svm-transspan` (et donc ses deux poignees) n'est rendu que
# si `on`, c'est-a-dire si la jonction PORTE une transition -- sur une coupe
# franche, l'ancre de T3 n'existe pas dans le DOM et le roll serait
# INATTEIGNABLE, alors que le roll de Resolve vise precisement la coupe. Le
# losange `.svm-junc`, lui, est rendu SANS condition pour chaque jonction :
# c'est lui qui rend le geste atteignable partout.
# I3 (revue du 21/09/2026) : `preventDefault()` sur le pointerdown NE
# SUPPRIME PAS le `click` qui suit -- apres un Alt+glisser sur le losange,
# `openTransPop` s'ouvrait par-dessus le roll qu'on venait de faire.
# L'ancre est ETENDUE jusqu'au `onClick` pour le neutraliser dans la MEME
# section (elle vaut 1/1 dans le .bak, mesure du 21/09/2026 ; le `onClick`
# seul vaut 1 lui aussi, mais l'etendre garde les deux mains du meme geste
# dans le meme remplacement).
A_T3B = ('                      "aria-label":"Transition entre "+j2.left.label+" et "+j2.right.label,\n'
         "                      onPointerDown:function(e){e.stopPropagation()},\n"
         "                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},\n"
         "                      onPointerLeave:transHoverHide,\n"
         "                      onClick:function(e){e.stopPropagation();openTransPop(j2.right.id,e)}})]}")
R_T3B = ('                      "aria-label":"Transition entre "+j2.left.label+" et "+j2.right.label,\n'
         "                      onPointerDown:function(e){if(e.altKey){dzRollDown(e,j2);return}e.stopPropagation()},\n"
         "                      onPointerEnter:function(){transHoverShow(j2.t,transHoverTxt(j2.right,on,s2))},\n"
         "                      onPointerLeave:transHoverHide,\n"
         "                      onClick:function(e){e.stopPropagation();if(e.altKey)return;openTransPop(j2.right.id,e)}})]}")

# T4 : le geste de roll, a cote de `transSpanDown` -- DANS le composant,
# donc `trackStRef`, `durRef`, `setClips`, `setDirty`, `pushHistory`,
# `dzmHistHost` et `transHoverShow/Hide` sont tous en portee (mesure : ce
# sont exactement ceux qu'utilise `transSpanDown`, juste en dessous).
# La piste est remontee par la CLASSE `.svm-lane` et non par un nombre de
# parents : le losange en est fils direct, les poignees a deux crans.
A_T4 = "function transSpanDown(e,jc,edge,t){"
R_T4 = ("function dzRollDown(e,j2){\n"
        "    e.stopPropagation();e.preventDefault();\n"
        "    var tgt=e.currentTarget;\n"
        '    var lane=tgt.closest?tgt.closest(".svm-lane"):null;\n'
        "    if(!lane)return;\n"
        "    if(trackStRef.current[j2.right.tr]&&trackStRef.current[j2.right.tr].l)return;\n"
        "    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}\n"
        "    var pxPerS=Math.max(1,lane.getBoundingClientRect().width)/durRef.current;\n"
        "    var x0=e.clientX,h0=dzmHistHost(),moved=!1;\n"
        '    transHoverShow(j2.t,"roll");\n'
        "    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;\n"
        "      if(Math.abs(ev.clientX-x0)>3)moved=!0;if(!moved)return;\n"
        '      transHoverShow(j2.t,"roll "+(ds>=0?"+":"")+ds.toFixed(2)+" s");\n'
        "      setClips(DzTracks.roll(h0.clips,j2.left.id,j2.right.id,ds))}\n"
        '    function up(){tgt.removeEventListener("pointermove",mv);tgt.removeEventListener("pointerup",up);\n'
        "      transHoverHide();if(moved){setDirty(!0);pushHistory(h0)}}\n"
        '    tgt.addEventListener("pointermove",mv);tgt.addEventListener("pointerup",up)}\n'
        "  function transSpanDown(e,jc,edge,t){")

# T5 : le titre des clips DIT les trois gestes -- c'est la seule decouverte
# possible, le curseur contextuel n'etant pas livre (ecart assume et date :
# « D-3 : curseur contextuel non livre », rien dans montage.css).
A_T5 = '" — bords : rogner / allonger · centre : déplacer"'
R_T5 = ('" — bords : rogner / allonger · centre : déplacer · '
        'Alt+centre : slip · Maj+centre : slide · Alt+losange : roll"')


# -- D-5 (21/09/2026) : LA CHIP « losange n » ET LE PANNEAU DE L'INDEX ------
# Les SEULES deux sections du lot : K1, K2, K3, K4 et K6 visaient des textes
# que d'autres remplacements POSENT, et sont donc REPLIEES la-bas (voir leurs
# commentaires). Ces deux ancres-ci, elles, valent 1/1 dans .bak_montage.
#
# -- K5 : la chip des marqueurs, dans la rangee d'outils ---------------------
# L'ANCRE N'EST PAS LA LIGNE ENTIERE, ET C'EST UNE MESURE. La ligne complete
# de la chip `ripple` est REECRITE par la section M21 (qui lui ajoute un
# `"aria-label":"ripple",`), laquelle passe AVANT dans l'ordre de PATCHES :
# une ancre prise sur la ligne entiere du .bak ne se retrouverait plus dans la
# chaine au moment ou K5 s'applique. La QUEUE de la ligne, elle, est reprise
# MOT POUR MOT par R_M21 -- comptee 1 dans .bak_montage ET 1 apres M21.
# La chip neuve prend le meme `aria-label` que ses trois voisines pour la
# raison que M21 a ecrite : sous largeur reduite elles passent en glyphe seul
# (`font-size:0` + `::before`), et le losange nu serait leur nom accessible.
A_K5 = 'onClick:function(){setRipple(!ripple)},children:"ripple"}),'
R_K5 = (A_K5 + "\n"
        '          r.jsx("button",{className:"svm-toolchip",'
        '"data-on":dzMkOn?"":void 0,\n'
        '            "aria-label":"marqueurs",\n'
        '            title:"Marqueurs \u2014 index ("+svmKeyLabel("marker_index")'
        '+") \u00b7 "+svmKeyLabel("marker_toggle")'
        '+" pose/retire \u00e0 la t\u00eate",'
        'onClick:function(){dzMkToggle()},'
        'children:"\u25c6 "+((proj.markers||[]).length)}),')

# -- K5b : le panneau de l'index, parmi les popovers -------------------------
# POSE JUSTE APRES `ovPicker()`, au milieu des autres panneaux flottants : il
# herite ainsi de leur contexte d'empilement et se ferme comme eux.
# L'HISTOIRE N'EST POUSSEE QU'AU CHANGEMENT REEL, et c'est la lecon de la
# sortie tot de R2 : un `pushHistory()` PAR FRAPPE remplissait la pile lettre
# a lettre et « Annuler » remontait le titre caractere par caractere. DEUX
# parades, et elles sont dans la COUCHE, pas ici : le champ de titre est
# NON CONTROLE (`defaultValue`) et ne remonte qu'au `blur` ou sur Entree, et
# `DzmMarkerIndex` ne rappelle `onChange` que si la valeur a VRAIMENT change.
# La couleur, elle, part tout de suite -- un <select> ne se frappe pas en
# rafale.
A_K5B = "    ovPicker(),"
R_K5B = (A_K5B + "\n"
         "    dzMkOn?r.jsx(DzTracks.MarkerIndex,{markers:proj.markers,"
         "onSeek:seekTo,\n"
         "      onClose:function(){setDzMkOn(!1)},\n"
         "      onRemove:function(id){pushHistory();"
         "setProj(function(p){return Object.assign({},p,"
         "{markers:DzTracks.markerRemove(p.markers,id)})});setDirty(!0)},\n"
         "      onChange:function(id,patch){pushHistory();"
         "setProj(function(p){return Object.assign({},p,"
         "{markers:DzTracks.markerUpdate(p.markers,id,patch)})});setDirty(!0)}"
         "}):null,")


# ── K7 (D-5) : ECHAP FERME L'INDEX ────────────────────────────────────────
# LA VOIE EST CELLE DU BUNDLE, pas une seconde. MESURE du 21/09/2026 : trois
# panneaux se ferment sur Echap, chacun a sa facon -- `kbPanel` par une
# branche de `onKey` sous le voile, `transPopover` par un `keydown` de
# fenetre en capture, et le champ de recherche par son propre `onKeyDown`.
# La quatrieme voie est la BRANCHE `Escape` DE `onKey`, qui existe deja (1/1
# dans le .bak) et qui rendait la main quand aucun overlay n'etait
# selectionne : c'est la que l'index se ferme, AVANT ce repli. Rien de neuf
# n'est ecoute, et l'ordre est celui qu'on attend -- Echap ferme d'abord le
# panneau ouvert, et ne retombe sur les fleches de l'overlay qu'ensuite.
A_K7 = ('if(e.key==="Escape"){\n'
        "        if(kbAudioRef.current&&kbAudioRef.current.ovEsc&&"
        "kbAudioRef.current.ovEsc())e.preventDefault();\n"
        "        return}")
R_K7 = ('if(e.key==="Escape"){\n'
        "        if(dzMkOnRef.current){e.preventDefault();dzMkToggle(!1);return}\n"
        "        if(kbAudioRef.current&&kbAudioRef.current.ovEsc&&"
        "kbAudioRef.current.ovEsc())e.preventDefault();\n"
        "        return}")


PATCHES = [("M3-tracks", A_M3, R_M3), ("M4-bus", A_M4, R_M4),
           ("M4b-setter", A_M4b, R_M4b),
           ("M5-payload", A_M5, R_M5), ("M6-save", A_M6, R_M6),
           ("M7-apply", A_M7, R_M7), ("M8-toolbar", A_M8, R_M8),
           ("M9a-head-audio", A_M9a, R_M9a), ("M9b-head-video", A_M9b, R_M9b),
           ("M9c-plus-hors-surimpression", A_M9c, R_M9c),
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
           ("E4-verrou-apres-mode", A_E4, R_E4),
           ("M17a-ajout-etend", A_M17A, R_M17A),
           ("M17b-nudge-etend", A_M17B, R_M17B),
           ("M17c-ripmax-mort", A_M17C, R_M17C),
           ("M17d-bord-droit-etend", A_M17D, R_M17D),
           ("M17e-deplacement-etend", A_M17E, R_M17E),
           ("M17f-relachement-ajuste", A_M17F, R_M17F),
           ("M17g-transport-duree", A_M17G, R_M17G),
           # P11 — un clip entre à la longueur de sa source.
           ("M18a-plafond-source", A_M18A, R_M18A),
           # Étape 4 du handoff « Barre Outils Flottante ».
           ("M19-barre-outils", A_M19, R_M19),
           # Étape 8 du handoff : le raccourci (§4.1) et le nom accessible
           # des chips dégradées (§4.5).
           ("M20a-raccourci-action", A_M20A, R_M20A),
           ("M20b-raccourci-dispatch", A_M20B, R_M20B),
           ("M21-chips-nom-accessible", A_M21, R_M21),
           # P12 — le son d'un plan suit sa vidéo. M22a/M22b vivent dans
           # addAsset APRÈS la sonde que R_M17A porte ; M22c dans
           # svmApplyProject ; M23 dans l'inspecteur, AVANT l'ancre que
           # R_M12 reprend en tête (l'ordre n'y change rien, mesuré).
           ("M22a-jumeau-decide", A_M22A, R_M22A),
           ("M22b-jumeau-ecrit", A_M22B, R_M22B),
           ("M22c-ids-uniques", A_M22C, R_M22C),
           ("M22d-reparation-persistee", A_M22D, R_M22D),
           ("M23-extraire-le-son", A_M23, R_M23),
           # P13 — la transcription vise la piste de dialogue. M24a…M24g sur
           # le bloc subs inliné (subs.js intouchable : porté EN AVAL), M24h…
           # M24j sur l'hôte. Aucune de ces ancres n'est touchée par une
           # section antérieure (1/1 dans le bundle patché ET dans le .bak).
           ("M24a-step-nomme-la-source", A_M24A, R_M24A),
           ("M24b-src-nul-sans-plan", A_M24B, R_M24B),
           ("M24c-plan-trie-a1-puis-start", A_M24C, R_M24C),
           ("M24d-tracks-partent", A_M24D, R_M24D),
           ("M24e-pastille-somme-des-clips", A_M24E, R_M24E),
           ("M24f-langue-auto-et-liste", A_M24F, R_M24F),
           ("M24g-auto-jamais-contre", A_M24G, R_M24G),
           ("M24h-hote-passe-les-pistes", A_M24H, R_M24H),
           ("M24i-hote-envoie-srcin", A_M24I, R_M24I),
           ("M24j-hote-clips-de-dialogue", A_M24J, R_M24J),
           # Tour 1 (revue du 06/09) : les libellés sous « auto », bloc subs.
           ("M24k-pastille-langue-auto", A_M24K, R_M24K),
           ("M24l-infobulle-langue-auto", A_M24L, R_M24L),
           ("M24m-note-detection-sous-auto", A_M24M, R_M24M),
           # P14 — deux sortes de pistes vidéo : les treize sites « v2 » de
           # l'écran lisent la règle du rendu (isOverlayTrack), l'aperçu
           # empile dans l'ordre des pistes (overlayOrder), le verrou suit la
           # piste. Aucune de ces ancres n'est touchée par une section
           # antérieure (1/1 dans le bundle patché ET dans le .bak).
           ("M25a-apercu-regle-et-ordre", A_M25A, R_M25A),
           ("M25b-apercu-empile-dans-l-ordre", A_M25B, R_M25B),
           ("M25c-payload-transformation", A_M25C, R_M25C),
           ("M25d-inspecteur-overlay", A_M25D, R_M25D),
           ("M25e-losanges-de-trajectoire", A_M25E, R_M25E),
           ("M25f-verrou-saisie", A_M25F, R_M25F),
           ("M25g-verrou-double-clic", A_M25G, R_M25G),
           ("M25h-poignees-du-lecteur", A_M25H, R_M25H),
           ("M25i-alignement-3x3", A_M25I, R_M25I),
           ("M25j-position-ici", A_M25J, R_M25J),
           ("M25k-fleches-du-clavier", A_M25K, R_M25K),
           ("M25l-echap-du-clavier", A_M25L, R_M25L),
           # P16 — traduire les répliques : l'état/le geste puis
           # la rangée. Aucune de ces ancres n'est touchée par une
           # section antérieure (1/1 dans le bundle patché ET le .bak).
           ("M26a-traduction-etat-et-geste", A_M26A, R_M26A),
           ("M26b-traduction-rangee", A_M26B, R_M26B),
           # D-0 (21/09/2026) — l'historique complet : la ref et
           # l'instantané, la pile, undo/redo, le h0 du glisser, la
           # durée et le style. Aucune de ces ancres n'est touchée par
           # une section antérieure (H6 vit DANS le remplacement de
           # M17g, qui passe avant).
           ("H1-hist-ref", A_H1, R_H1), ("H2-hist-push", A_H2, R_H2),
           ("H3-hist-undo", A_H3, R_H3), ("H4-hist-redo", A_H4, R_H4),
           ("H5-hist-h0-clip", A_H5, R_H5),
           ("H7-hist-style", A_H7, R_H7),
           # D-11 (21/09/2026) — la plage I/O. R4 et R5 du plan sont
           # repliees dans R_M6 et R_M7 (ancres POSEES, compte 0 dans
           # .bak_montage). Les trois ancres ci-dessous valent 1/1 dans
           # le bundle d'entree et aucune section anterieure n'y touche.
           ("R1-plage-actions", A_R1, R_R1),
           ("R2-plage-dispatch", A_R2, R_R2),
           ("R3-plage-regle", A_R3, R_R3),
           # D-3 (21/09/2026) — roll, slip, slide. Les six ancres valent
           # 1/1 dans le .bak_montage ET dans le bundle patche : aucune
           # section anterieure ne les touche. T4 pose `dzRollDown` que
           # T3 et T3b appellent (ordre indifferent : declaration de
           # fonction, hissee dans le corps du composant).
           ("T1-trim-modificateurs", A_T1, R_T1),
           ("T2-trim-slip-slide", A_T2, R_T2),
           ("T3-trim-roll-poignee", A_T3, R_T3),
           ("T3b-trim-roll-losange", A_T3B, R_T3B),
           ("T4-trim-roll-geste", A_T4, R_T4),
           ("T5-trim-titre", A_T5, R_T5),
           # D-5 (21/09/2026) - les marqueurs. DEUX sections seulement :
           # K1, K2, K3, K4 et K6 sont REPLIEES dans R_R1, R_R2, R_M16REF,
           # R_R3, R_M6 et R_M7, dont elles visaient un texte POSE (ancres
           # comptees 0 dans .bak_montage). Les deux ancres ci-dessous
           # valent 1/1 dans le bundle d'entree ; celle de K5 est la QUEUE
           # de la ligne de la chip `ripple`, que M21 (qui passe avant)
           # reecrit en tete mais reprend mot pour mot en queue.
           ("K5-chip-marqueurs", A_K5, R_K5),
           ("K5b-index-marqueurs", A_K5B, R_K5B),
           # K7 : Echap. Ancre 1/1 dans .bak_montage, et aucune section
           # anterieure n'y touche. `dzMkOnRef` et `dzMkToggle` viennent de
           # K3, replie dans R_M16REF, qui passe AVANT (ordre de PATCHES) --
           # et `dzMkToggle` est une DECLARATION de fonction, hissee dans le
           # corps du composant : l'ordre d'ecriture n'y change rien.
           ("K7-echap-ferme-index", A_K7, R_K7)]


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
        # CE CONTRÔLE NE VOIT QUE L'ÉTAT D'ENTRÉE : une section dont l'ancre
        # serait POSÉE par une section antérieure y compterait 0. C'est la
        # raison pour laquelle une telle modification est REPLIÉE dans la
        # section qui pose son ancre (voir « H6 » dans R_M17G), jamais
        # ajoutée à PATCHES.
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
