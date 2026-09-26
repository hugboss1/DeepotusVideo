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
        # -- « TT2 » (D-21, 21/09/2026) : LES CARTONS DE TITRE PASSENT LE
        # FILTRE. REPLI, et c'est une MESURE : la ligne
        # `      clips:clips.filter(function(c){return c.src}).map(...)` vaut
        # bien 1 dans .bak_montage, mais elle est l'ANCRE A_M5 -- consommee
        # par CE remplacement, qui la reprend en queue. Une section a part
        # l'aurait donc cherchee dans un bundle ou M5 l'a deja reecrite :
        # `--check` (qui ne regarde que le .bak) aurait dit oui, et la chaine
        # aurait abandonne au rejeu. Meme technique que R4/R5 dans R_M6/R_M7.
        # UN TITRE EST UN CLIP SANS `src` : sans ce `||c.kind==="title"`, il
        # ne quittait JAMAIS le client et le backend n'avait rien a graver.
        # LA GARDE `c.src.job_id` DE LA VITESSE, TROIS LIGNES PLUS BAS, EST
        # DEJA SURE : elle est precedee de `c.tr==="v1"&&`, et un carton vit
        # sur t1 -- le court-circuit sort AVANT la lecture (mesure du
        # 21/09/2026 sur le texte du .bak, que rien ne reecrit ici).
        # AJ3 (D-9, 22/09/2026) : le clip d'AJUSTEMENT passe aussi -- sans
        # `src`, comme un carton ; `kind` est joint pour TOUT clip par TT2b
        # et `effects` est dans le litteral `o` du .bak (mesure) : le backend
        # le collecte dans adjust_clips par le genre de sa piste (`j1`).
        '      clips:clips.filter(function(c){return c.src||c.kind==="title"||c.kind==="adjust"})'
        ".map(function(c){")

# ── M6 : autosave ───────────────────────────────────────────────────────────
A_M6 = "      duration_master:durMaster,ducking:ducking,clips:clips,"
R_M6 = ("      duration_master:durMaster,ducking:ducking,clips:clips,\n"
        "      /* sans cette clé, une piste ajoutée disparaissait au rechargement\n"
        "         et les clips qu'elle portait retombaient sur une piste inconnue,\n"
        "         donc hors du rendu — silencieusement. */\n"
        "      tracks:svmTracksPayload(proj),\n"
        # E-1 (22/09/2026) — LE DRAPEAU `vide` PART AVEC LA SAUVEGARDE, et
        # seulement quand il est vrai : `void 0` est omis par JSON.stringify,
        # le payload d'avant est rendu octet pour octet. REPLI, ancre
        # consommée, mesurée 22/09 : la ligne `tracks:svmTracksPayload(proj),`
        # vaut 0 dans .bak_montage (R_M6 la pose) et 2 dans le bundle (R_M5
        # la pose aussi, dans le payload de RENDU — le plan la situait là,
        # la mesure la situe ici, dans svmSavePayload, le seul qui nourrit
        # POST /save). Le `proj` est celui de la fermeture de l'écran, où
        # svmApplyProject a posé `vide` (R_M7).
        "      vide:proj.vide===!0?!0:void 0,\n"
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
# -- « TT3 » (D-21, 21/09/2026) : LA PISTE DES TITRES REVIENT AVEC LE PROJET.
# REPLI, et c'est une MESURE : `tracks:svmTracksFrom(d.tracks)` vaut 0 dans
# .bak_montage -- c'est CE remplacement-ci qui l'ecrit. Meme technique que
# R5 et K6.
# LA PISTE N'EST POSEE QUE S'IL Y A UN CARTON A PORTER. Une sauvegarde d'un
# projet SANS titre ne gagne donc pas une bande vide au rechargement ; une
# sauvegarde d'avant D-21 qui porterait des cartons (impossible aujourd'hui,
# possible demain si la piste est retiree a la main puis le projet rouvert)
# la retrouve.
# `_t` EST TESTE AVANT : `svmTracksFrom` rend `null` quand la liste est
# illisible ou qu'elle a perdu v1, et « null » veut dire « garde les six
# defauts » -- qui portent DEJA t1. `titleTrack(null)` aurait rendu une liste
# d'UNE piste (t1 seule), c'est-a-dire un montage sans V1.
# LE GENRE, LUI, N'A PAS BESOIN DE REPLI : mesure du 21/09/2026 (banc
# d'edition, `tt_la_restauration_garde_le_genre_title_et_l_habillage`),
# `svmTracksFrom` GARDE un `kind:"title"` et lui rend son habillage.
R_M7 = ('var np={demo:!1,tracks:(function(){var _t=svmTracksFrom(d.tracks);'
        'return _t&&(d.clips||[]).some(function(c){return c&&c.kind==="title"})'
        '?DzTracks.titleTrack(_t):_t})(),'
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
        'name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",'
        # E-1 (22/09/2026) — ET LE DRAPEAU REVIENT AVEC LE PROJET, dans le
        # `np` que `setProj(np)` reçoit (mesuré : c'est le seul `np` de
        # svmApplyProject). REPLI, ancre consommée, mesurée 22/09 : `ratio:`
        # est le texte que CE remplacement pose (0 dans .bak_montage). Faux
        # sinon, jamais absent : un projet ordinaire ne porte pas la clé.
        'vide:d.vide===!0,')

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
         # ── L7-B D-41 (24/09/2026, tache 6) : REPLI ici (aucune ancre neuve). La demande d'OUVERTURE d'un projet
         # cree par les auto-clips du tiroir Medias : {n, id, name}, un COMPTEUR `n` comme dzProjReq (meme raison :
         # la liste des projets garde son etat d'ouverture). EB3 la pose (onOpenProject du tiroir), M14 la lit
         # (openProj) -- la liste ouvre par le chemin MEME de « ouvrir » (surete, onBefore, open, onOpen).
         # NOMS MESURES LIBRES le 24/09/2026 : stDzAc, dzAcOpen, setDzAcOpen -- 0 dans .bak_montage et le livre.
         "  /* L7-B D-41 (24/09/2026, tâche 6) : la demande d'ouverture d'un projet créé par\n"
         "     les auto-clips du tiroir Médias — {n, id, name}, un COMPTEUR comme dzProjReq ;\n"
         "     la liste des projets l'ouvre par le chemin de « ouvrir ». */\n"
         "  var stDzAc=x.useState(null),dzAcOpen=stDzAc[0],setDzAcOpen=stDzAc[1];\n"
         # ── E-10 (lot E-C, tache 4, 23/09/2026) : LA BARRE ANCREE dans le
         # bandeau de transport. Un booleen PERSISTE (dz_svm_tb_dock, try/catch,
         # le motif de dz_svm_showdur), passe en prop `docked` au Dock (R_M19)
         # qui pose data-docked ; ☰ › Affichage le bascule (R_EC1). ICI et pas
         # dans R_M16REF : c'est l'etat de la MEME barre que dzTbReq, et le pin
         # E-7 compte `localStorage` x1 dans R_M16REF (temoin de « la vue
         # n'est pas persistee »). Ecart date par rapport au plan.
         "  /* E-10 (lot E-C, tâche 4, 23/09/2026) : la barre d'outils ANCRÉE dans le\n"
         "     bandeau — un booléen persisté (clé ci-dessous), passé en prop `docked`\n"
         "     au Dock ; l'entrée ☰ › Affichage le bascule. */\n"
         '  var stTbD=x.useState(function(){try{return localStorage.getItem("dz_svm_tb_dock")==="1"}catch(_e){return !1}}),'
         "dzTbDock=stTbD[0],setDzTbDock=stTbD[1];\n"
         '  function dzTbDockToggle(){setDzTbDock(function(v){var n=!v;try{localStorage.setItem("dz_svm_tb_dock",n?"1":"0")}catch(_e){}return n})}\n'
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
         # L7-B D-41 (24/09/2026, tache 6) : REPLI -- la demande d'ouverture venue des auto-clips (R_M11, EB3)
         '          /* L7-B D-41 : ouvrir le projet créé par les auto-clips (compteur) */\n'
         '          openProj:dzAcOpen,\n'
         '          payload:function(){return svmSavePayload()},\n'
         '          onBefore:function(){'
         'if(saveAbortRef.current){try{saveAbortRef.current.abort()}catch(_e){}}'
         'saveSeqRef.current++;setSaveInfo(null)},\n'
         '          onFail:function(){if(dirty)svmDoSave(++saveSeqRef.current)},\n'
         '          onOpen:function(d){return svmApplyProject(d)},\n'
         # L7 D-39 (24/09/2026, tache 4) : L7d1 REPLIE ici (l'ancre `r.jsx(DzTracks.Projects,{` du plan est nee
         # de CE remplacement, x0 dans .bak_montage). « ⇄ » d'une ligne : GET du projet (MESURE : la route rend
         # le record DIRECT, `d.clips`), diff pur de la couche contre la timeline courante (clipsRef), le nom
         # courant par dzProjRef, puis le popover `diff` ; un projet illisible (404, panne) est DIT, rien ne change.
         '          /* L7 D-39 (24/09/2026, tâche 4) : « ⇄ » d\'une ligne — lit l\'autre projet, le compare à la timeline\n'
         '             courante (le diff pur de la couche) et ouvre le popover « diff » ; rien n\'est modifié */\n'
         '          onDiff:function(p){fetch("/api/montage/projects/"+encodeURIComponent(p.id))'
         '.then(function(rp){if(!rp.ok)throw new Error("HTTP "+rp.status);return rp.json()})'
         '.then(function(d){setDiffSt({diff:DzTracks.diff(clipsRef.current,(d&&d.clips)||[]),'
         'nomA:(dzProjRef.current&&dzProjRef.current.name)||"",nomB:p.name||""});setPop("diff")})'
         '.catch(function(){fireNote("Projet illisible — comparaison impossible")})},\n'
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
         # -- « TT6 » (D-21, 22/09/2026) : L'INSPECTEUR DU CARTON ------------
         # REPLIE dans R_M12 parce que l'ancre naturelle (la ligne du
         # TextDrawer, derniere de ce remplacement) vaut 0 dans .bak_montage :
         # c'est CE remplacement qui l'ecrit. Meme mesure que E1/K3/X1/V1.
         # POSE AVANT le TextDrawer et non apres, et c'est une MESURE contre
         # la lettre du plan : la colonne d'inspection se lit de haut en bas
         # et les trois lignes qui PRECEDENT l'ancre (`transInspector()` et
         # ses voisines) sont les inspecteurs du clip SELECTIONNE. Le tiroir
         # de texte, lui, est un panneau de PROJET (il liste toute la
         # narration) et il ferme la colonne. Glisser l'inspecteur du carton
         # sous lui l'aurait mis a un ecran de son clip.
         # LA GARDE EST `trackKind(sel.tr)==="title"` ET NON `sel.tr==="t1"` :
         # le plan ecrivait l'egalite sur l'identifiant. TT1 a fait de `t`
         # l'INITIALE du genre -- une seconde piste de titres (t2) serait
         # restee sans inspecteur, et la garde aurait dit autre chose que les
         # seize autres sites du bundle, qui interrogent tous `trackKind`.
         # AUCUN INSTANTANE POUR UN PATCH REFUSE, et c'est l'IDENTITE qui le
         # dit : `titleUpdate` rend le MEME tableau quand rien n'a bouge
         # (texte vide, gabarit qui ne survit pas a l'assainissement, valeur
         # identique). Sans ce test, un blur sur un champ non touche aurait
         # empile une entree d'historique qui ne defait rien et allume « NON
         # ENREGISTRE ». L'inspecteur filtre DEJA le blur inchange ; les deux
         # gardes ne couvrent pas le meme cas et ne se remplacent pas.
         # UN REFUS DE TEXTE VIDE SE DIT, ET REND LE CHAMP A SA VALEUR
         # (22/09/2026) : sans ces deux lignes, effacer le titre ne faisait
         # RIEN -- pas de note, pas de setClips, donc pas de re-rendu, donc
         # un input reste VIDE a l'ecran alors que le carton a garde son
         # texte. Le jeton `dzTtNonce` entre dans la cle des deux champs :
         # l'incrementer force le remontage et le champ se recolle. Le
         # setter FONCTIONNEL, parce que ce rappel peut tenir une fermeture
         # perimee (l'inspecteur n'est re-rendu qu'au changement de `sel`).
         # LA FENETRE DE 600 ms EST CELLE DE `nudgeHistAt` (M17b) et de
         # `dzDurHistAt` (H6), et elle est ici pour le CLAVIER : la reglette
         # de corps remonte au relachement, et chaque fleche est un `keyup`
         # -- cinq crans faisaient cinq instantanes, et « annuler » remontait
         # cran par cran.
         # ELLE NE COUVRE QUE LA TAILLE, ET C'EST UNE CORRECTION (22/09/2026,
         # re-revue) : posee sur TOUS les reglages, elle coalescait des
         # gestes HETEROGENES -- taper un texte puis cliquer un gabarit 50 ms
         # plus tard ne faisait qu'UNE entree, et « annuler » defaisait les
         # deux d'un coup. Les deux precedents cites ne bornent chacun qu'UN
         # reglage (`nudgeHistAt` le deplacement d'un overlay, `dzDurHistAt`
         # la duree du projet) : la fenetre y est le prix d'une RAFALE sur le
         # MEME reglage, jamais un melange. Le texte, le gabarit, la couleur
         # et la police poussent donc SEC, et remettent l'horloge a zero pour
         # que la rafale suivante recommence par un instantane a elle.
         # `pushHistory` AVANT `setClips`, comme partout ailleurs dans ce
         # composant : l'instantane doit porter l'etat D'AVANT.
         '        sel&&trackKind(sel.tr)==="title"'
         '?r.jsx(DzTracks.TitleInspector,{clip:sel,\n'
         '          gabarits:dzTitles&&dzTitles.gabarits,\n'
         '          fonts:dzTitles&&dzTitles.fonts,'
         'colors:dzTitles&&dzTitles.colors,nonce:dzTtNonce,\n'
         '          onChange:function(id,p){\n'
         '            var cs=DzTracks.titleUpdate(clipsRef.current,id,p);\n'
         '            if(cs===clipsRef.current){\n'
         '              if(p&&typeof p.text==="string"&&!p.text.trim()){\n'
         '                fireNote("Un carton sans texte n\'est pas un '
         'carton — le titre précédent est conservé.");\n'
         '                setDzTtNonce(function(dzK){return dzK+1})}\n'
         '              return}\n'
         '            var dzTtN=Date.now();\n'
         '            if(p.size==null){pushHistory();dzTtHistAt.current=0}\n'
         '            else{if(dzTtN-dzTtHistAt.current>600)pushHistory();\n'
         '              dzTtHistAt.current=dzTtN}\n'
         '            setClips(cs);setDirty(!0)}}):null,\n'
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
R_M13 = (
         # -- « TT9b » (D-21, 22/09/2026) : LA PILE D'EFFETS SE TAIT AUSSI
         # SUR UN CARTON. REPLI dans R_M13 parce que l'ancre EST la ligne
         # que M13 reecrit (elle vaut 1 dans .bak_montage et 0 apres M13) :
         # une section a part aurait passe `--check` pour abandonner au
         # rejeu -- meme mesure que TT1b dans R_M15.
         # POURQUOI : `vfxStackSection()` rend « Effets sur ce clip » avec
         # son bouton « remplacer le plan », qui appelle `openPicker(sel.tr)`
         # -- soit `openPicker("t1")` sur un carton, c'est-a-dire le
         # selecteur d'assets ouvert sur la piste qui n'en recoit aucun.
         # TT1b arretait le degat DANS `addAsset` (avec une note), mais
         # l'ecran proposait encore le geste. Un carton n'a pas davantage
         # d'effets video : il n'a pas de `src`, la chaine `_fx` du payload
         # ne le voit jamais.
         # `trackKind(sel.tr)` POUR LES DEUX GENRES, et pas deux egalites
         # sur des identifiants : c'est la forme des seize autres sites du
         # bundle, et une piste s2 ou t2 y serait traitee comme sa soeur.
         '        (sel&&(trackKind(sel.tr)==="subs"'
         '||trackKind(sel.tr)==="title")?null:vfxStackSection()),\n'
         '        /* P4 — le geste GLOBAL de l\'étalonnage : les quatre valeurs\n'
         '           du plan sélectionné recopiées sur tous les autres plans\n'
         '           réels de SA piste (pas « v1 » en dur : un plan V2 peut\n'
         '           porter un grade_basic). RÉVERSIBLE : un seul pushHistory\n'
         '           pour le lot ; « annuler » rend à chaque plan son\n'
         '           étalonnage d\'avant — déduit de trois faits mesurés, mais\n'
         '           rien ne l\'EXERCE (undo est un hook du composant). */\n'
         # -- « EB6a-fermeture » (E-8, lot E-B tache 6, 23/09/2026) : LA
         # FERMETURE DE L'ASIDE REND null QUAND L'INSPECTEUR EST REPLIE.
         # REPLI dans R_M13 parce que l'ancre de la fermeture EST la ligne
         # que M13 reecrit (1 dans .bak_montage, 1 dans le patcher, 0 dans
         # le livre -- le plan l'annoncait 1/0/1 : ECART mesure). L'ouverture
         # `inspOn?r.jsxs("aside",...` est la section EB6a ; ce `:null` en
         # est la seconde moitie, TT9b et P4 restent tels quels. MESURE
         # (node --check a refuse `]})]}):null,` au premier jet) : le PREMIER
         # `]})` ferme l'aside, le SECOND ferme .svm-mid (l'aside en est le
         # dernier enfant, `/* timeline */` suit) -> `]}):null]}),`.
         '        DzTracks.gradeAllBtn(sel,clips,setClips,pushHistory,setDirty,'
         'fireNote)]}):null]}),')

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
# La garde demo des tiroirs (E-2, documentee a R_EB2) -- definie ICI parce que
# R_M16REF (E-7, dzSetView) et R_EB2 / R_EC1 la reprennent ; une seule ecriture.
_EB_GARDE = ('if(proj.demo){fireNote("Ajout d\'assets : disponible sur un projet '
             'réel — la démo reste une maquette.");return}')
A_M16REF = "  var durRef=x.useRef(proj.dur);durRef.current=proj.dur;"
R_M16REF = (A_M16REF + "\n"
            "  /* P9 — les PISTES du projet, relues à chaque rendu, pour que\n"
            "     `addAsset` ne décide jamais sur un `proj` périmé (le greffon\n"
            "     « Envoyer vers → Montage » l'appelle depuis la fermeture du\n"
            "     premier rendu). Même motif que durRef, juste au-dessus. */\n"
            "  var dzTracksRef=x.useRef(null);"
            "dzTracksRef.current=svmTracksOf(proj);\n"
            # ── D-13 (22/09/2026, L3 tache 2) : LE GESTE DES PROPRIETES DE PLAN
            # REPLIE ICI, meme mesure que E1/TT4a : la ligne `dzTracksRef` vaut
            # 0 dans .bak_montage. UNE fonction pour l'hote (DZ1) ET les
            # rectangles (DZ2) : un patch de clip, les cles `undefined`
            # retirees, UNE entree d'historique par rafale de 600 ms (un
            # glisser = un « Annuler »), `heavy` force l'entree (un select).
            # La date de la rafale est une REF : un `var` du corps serait
            # recree a chaque rendu et chaque `setClips` re-rend. La piste
            # VERROUILLEE refuse (forme de `ovHandleDown` ; l'hote et les
            # rectangles ne se montent que sur v1).
            "  var dzPlanHist=x.useRef(0);\n"
            "  function dzPlanSet(patch,heavy){var tl=trackStRef.current.v1;if(tl&&tl.l)return;\n"
            "    var id=selRef.current,now=Date.now();\n"
            "    if(heavy||now-dzPlanHist.current>600)pushHistory();dzPlanHist.current=now;\n"
            "    setClips(clipsRef.current.map(function(k){if(k.id!==id)return k;var nk=Object.assign({},k,patch);\n"
            "      Object.keys(patch).forEach(function(q){if(patch[q]===void 0)delete nk[q]});return nk}));setDirty(!0)}\n"
            # ── D-16 (22/09/2026, L3 tache 6) : L'ANALYSE DE STABILISATION
            # REPLIEE ICI (meme mesure : l'ancre est posee par ce remplacement).
            # Un etat PAR SOURCE (cle = JSON de `src`, comme le cache backend
            # est par source) : {status,progress,error}. POST /api/montage/stab
            # rend {ok,ready,job_id} (contrat de /proxy) : `ready` = analyse
            # deja en cache -> done sans job ; sinon suivi par GET /api/jobs/
            # {id} toutes les 1,5 s (la cadence de launchRender), `status`
            # MESURE en minuscules (`JobStatus.DONE.value`, launchRender
            # compare `d.status==="done"` nu). L'etat passe a « running » AVANT
            # le POST : le bouton est desactive des le clic (pas de double
            # demande). Toute erreur -- refus HTTP ({detail}), reseau, job
            # introuvable -- finit en « failed » AVEC message : le plan
            # avalait l'erreur du polling (`.catch(function(){})`), ce qui
            # laissait la chip a « analyse n % » et le bouton mort pour de bon.
            # Le polling s'ETEINT au demontage : `put` ne pose rien et la
            # replanification s'arrete si `dzAliveRef` (P9, plus bas dans ce
            # meme corps -- resolue a l'appel) est tombee. Les sorties
            # precoces sont des `return put(...)` : le pin P9 compte les
            # `;return}` du corps (quatre) et la garde `if(!dzAliveRef...` (une)
            # -- ce repli n'en ajoute aucun.
            "  var stDzStab=x.useState({}),dzStabJobs=stDzStab[0],setDzStabJobs=stDzStab[1];\n"
            "  function dzStabStart(src){var key=DzTracks.srcKey(src);\n"
            "    var put=function(v){if(dzAliveRef.current)setDzStabJobs(function(m){var n=Object.assign({},m);n[key]=v;return n})};\n"
            '    var tick=function(id){fetch("/api/jobs/"+id).then(function(r3){return r3.json()}).then(function(j){\n'
            '      var st=j&&j.status;if(!st)return put({status:"failed",error:(j&&j.detail)||"job introuvable"});\n'
            '      var fin=st==="done"||st==="failed";put({status:fin?st:"running",progress:Number(j.progress)||0,error:j.error||null});\n'
            "      if(!fin&&dzAliveRef.current)setTimeout(function(){tick(id)},1500)})\n"
            '      .catch(function(e){put({status:"failed",error:String(e)})})};\n'
            '    put({status:"running",progress:0});\n'
            '    fetch("/api/montage/stab",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:src})})\n'
            "      .then(function(r2){return r2.json().then(function(d){return {ok:r2.ok,d:d}})}).then(function(o){\n"
            '        if(o.ok&&o.d&&o.d.ready)return put({status:"done"});\n'
            '        if(!o.ok||!o.d||!o.d.job_id)return put({status:"failed",error:(o.d&&(o.d.detail||o.d.error))||"refus"});\n'
            '        put({status:"running",progress:10});tick(o.d.job_id)})\n'
            '      .catch(function(e){put({status:"failed",error:String(e)})})}\n'
            # ── E-4 (22/09/2026) : LE BANDEAU DE FIN DE RENDU ─────────
            # REPLIÉ ICI, même mesure que E1 : la ligne vaut 0 dans
            # .bak_montage. Posé par EA4 (rendu final « done »), consommé
            # par EA5e (le bandeau de la couche), effacé par « Fermer ».
            "  var stDzFin=x.useState(null),dzFin=stDzFin[0],setDzFin=stDzFin[1];\n"
            # ── E-11 (lot E-B, tache 5, 23/09/2026) : LE VOILE VU PAR ECHAP.
            # REPLIÉ ICI (0 dans .bak_montage), à côté de dzFin. `onKey`
            # (window keydown) a des deps sans `pop` ni `dzFin` : une lecture
            # directe serait périmée -- même motif que dzMkOnRef. `pop` (stA,
            # :1716 du livré) est déclaré avant cette ligne.
            # ── E-6 (lot E-C, tache 2, 23/09/2026) : LE MENU OUVERT -- REPLIE ICI,
            # AVANT dzScrimRef qui le lit une ligne plus bas (une ancre libre plus
            # loin -- delClip, EC1 -- laisserait le ref en retard d'un rendu : le
            # `var` hoiste vaudrait undefined au moment de l'ecriture). Forme :
            # {kind:"main"|"clip"|"track", id, x, y, rubs|items} construite A
            # L'OUVERTURE par dzMenuProps (EC1), jamais a chaque rendu.
            "  var stMn=x.useState(null),dzMenu=stMn[0],setDzMenu=stMn[1];\n"
            "  var dzScrimRef=x.useRef(!1);dzScrimRef.current=!!(pop||dzFin||dzMenu);\n"
            # ── E-14 (lot E-C, tache 5, 23/09/2026) : LE TROU SELECTIONNE -- REPLIE
            # ICI (0 dans .bak_montage), a cote de dzScrimRef et sur le MEME motif :
            # onKey (window keydown) a des deps sans gapSel, le ref est pose a
            # chaque rendu. Forme {tr,a,b} ou null ; pose par le clic dans le vide
            # d'une lane (EC10), lu par le rendu (EC11) et par Suppr (EC13), efface
            # par Suppr, Echap (R_K7) et le clic sur un clip (EC14).
            "  var stGap=x.useState(null),gapSel=stGap[0],setGapSel=stGap[1];\n"
            "  var gapSelRef=x.useRef(null);gapSelRef.current=gapSel;\n"
            # ── L5 D-32 (24/09/2026, tache 6) : LA LIGHTBOX DES PLANS OUVERTE -- REPLIEE ICI, meme motif que gapSel :
            # onKey (window keydown) a des deps sans dzLb, le ref est pose a chaque rendu et lu par Echap (R_K7) ;
            # ouverte par ☰ › Affichage (R_EC1), rendue dans R_EB5A, fermee par dzLbPick / le voile / « Fermer » /
            # Echap. PAS dans dzScrimRef (ligne epinglee) : la lightbox porte son propre voile.
            "  var stLb=x.useState(!1),dzLb=stLb[0],setDzLb=stLb[1];\n"
            "  var dzLbRef=x.useRef(!1);dzLbRef.current=dzLb;\n"
            # REVUE T5 (23/09/2026) : LE TROU S'EFFACE QUAND LES CLIPS CHANGENT.
            # Mesure : gapSel survivait aux 55 `setClips(` du bundle (undo/redo,
            # dropOnTrack, blade, range_cut, remplacement...) -- un media depose
            # dans le trou puis Suppr reculait le clip droit PAR-DESSUS lui, et
            # le pointille restait dessine sur des bornes qui n'etaient plus un
            # trou. Un effet sur [clips] couvre TOUS les mutateurs ; sur null,
            # setGapSel(null) est un bail-out React (cout nul) ; apres Suppr
            # (qui pose deja null) l'effet re-pose null = no-op.
            "  x.useEffect(function(){setGapSel(null)},[clips]);\n"
            # ── E-5 (lot E-B, tache 4, 23/09/2026) : LE DERNIER RENDU FINAL
            # PAR PROJET. REPLIÉ ICI comme dzFin (0 dans .bak_montage). Deux
            # états DISTINCTS : dzFin = le bandeau est visible ; ce store =
            # il y a eu un rendu final (localStorage dz_montage_lastfin, par
            # project_id, "_" quand le projet n'est pas nommé). Lu UNE fois
            # au montage (try/catch), écrit par le poll du rendu final (R_EA4),
            # jamais par « Fermer » (R_EA5E) ni par le lancement (EA6).
            # `proj` est déclaré avant (stP, :1717 < :1766 dans le livré).
            '  var stDzFS=x.useState(function(){try{return JSON.parse(localStorage.getItem("dz_montage_lastfin")||"{}")||{}}catch(_e){return {}}}),dzFinStore=stDzFS[0],setDzFinStore=stDzFS[1];\n'
            '  var dzLast=DzTracks.finOf(dzFinStore,proj.project_id||"_");\n'
            # ── L6 D-26 (25/09/2026, tache 6) : LA BASCULE DE LA VOIX OFF -- REPLIEE ICI (0 dans .bak_montage), APRES dzLast :
            # posee entre dzLbRef et stDzFS, elle ecartait dzLast de stDzFin au-dela des 700 o que le pin EB du store mesure
            # (703 en octets CRLF, MESURE) -- on ne desserre pas le pin, on pose la ligne plus loin. La puce de la couche
            # (section L6vo1) y inscrit sa bascule a chaque rendu et la retire au demontage ; onKey (action vo_record, repli
            # de R_R2) la lit a l'appel. Un ref, pas un etat : aucun rendu de plus.
            '  var dzVoRef=x.useRef(null);\n'
            # ── E-7 (lot E-C, tache 3, 23/09/2026) : LES TROIS VUES (Medias · Montage ·
            # Livraison). REPLIE ICI (0 dans .bak_montage), APRES dzLast que le panneau
            # lit (EC9). `view` est un etat de SESSION -- decision 4 : aucun
            # localStorage, chaque ouverture repart sur l'ecran complet ("montage").
            # (kbPanel declare son propre `var view` LOCAL -- une ombre interne a cette
            # fonction, sans effet sur l'hote ; « setView » vaut 8 dans l'amont : le
            # setter s'appelle setVw.) dzJobs = l'historique GET /api/jobs?providers=
            # montage&q=<nom>&limit=24 (E-B ; PAR TITRE, aucun project_id en base --
            # ecart date), recharge a chaque entree en « livraison » ; vivant/demonte
            # par le drapeau local de l'effet (motif du tiroir sous-titres, couche
            # :1053) ET dzAliveRef (P9, plus bas dans ce corps, resolue a l'appel).
            # dzSetView(« medias ») = LA garde demo de la chip (meme phrase, comptee :
            # sur la maquette, note et la vue ne change PAS), puis les memes setters
            # que la chip : tiroir Medias ouvert, les trois autres fermes.
            # ECART MESURE A L'ECRAN (23/09/2026) : en « livraison », le panneau ne
            # faisait que 150 px a cote d'un tiroir Medias reste ouvert (340) et de
            # l'inspecteur (300) dans un .svm-mid de 928 px -> la vue Livraison FERME
            # les quatre tiroirs (memes setters, setMedOn(!1) x6 -> x7) et la feuille
            # donne au panneau min-width:320px (le plan ecrivait 0).
            '  var stVw=x.useState("montage"),view=stVw[0],setVw=stVw[1];\n'
            "  var stDzJ=x.useState([]),dzJobs=stDzJ[0],setDzJobs=stDzJ[1];\n"
            '  x.useEffect(function(){if(view==="livraison"){var alive=!0;\n'
            '    fetch("/api/jobs?providers=montage&limit=24&q="+encodeURIComponent(proj.name||"")).then(function(r2){return r2.json()})\n'
            '      .then(function(j){if(alive&&dzAliveRef.current)setDzJobs(Array.isArray(j)?j:[])}).catch(function(){});\n'
            # REVUE T3 (23/09/2026) : dependance [view, proj.name] -- proj.name change
            # SANS remonter DzMontage (ouvrir / renommer en place via
            # DzTracks.Projects -> setProj) : avec [view] seule, la vue Livraison
            # gardait la liste de l'ancien titre. ECARTS dates (revue) : la vue
            # Livraison ferme le tiroir Narration comme toute bascule croisee (le
            # choix dz_narr_open n'est pas reecrit, il revient au prochain montage) ;
            # `dzAliveRef.current` dans ce `then` est redondant avec `alive` (laisse).
            '    return function(){alive=!1}}},[view,proj.name]);\n'
            '  function dzSetView(v){if(v==="medias"){' + _EB_GARDE + 'setMedTr("");setMedOn(!0);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}\n'
            '    if(v==="livraison"){setMedOn(!1);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}setVw(v)}\n'
            # ── L4 (23/09/2026, tache 4) : LES REGLAGES DE LIVRAISON -- REPLIES ICI
            # (0 dans .bak_montage), APRES dzSetView. dzDel = {preset?, fps?, loudness?,
            # rangeOnly?} lu UNE fois de localStorage dz_montage_deliver (try/catch,
            # objet ou {} -- AUCUN id de preset en dur : sans `preset`, rien n'est poste
            # et le backend retombe sur master), ecrit par dzDelSet (UNE ecriture) ;
            # dzDelRef pose a CHAQUE rendu : renderPayload est appele depuis
            # launchRender / doMeasure, une lecture directe de l'etat y serait perimee
            # (motif durRef). dzApi = la reponse de GET /api/montage/deliver-presets
            # ({builtins, fps, presets}), relue a CHAQUE ouverture du popover de rendu
            # (effet [pop], vivant par drapeau local + dzAliveRef resolue a l'appel).
            # dzSavePreset : le nom par window.prompt -- ECART DATE 23/09/2026 : le
            # Montage n'a AUCUN dialogue maison (DzTracks.dialogue / dzmDialogue /
            # svmDialog x0 ; VL.dialogue est celui du Vectorlab) ; slug [a-z0-9_] <= 32 ;
            # base = la base REELLE (un preset maison choisi donne SA base, aucun
            # choix = le premier builtin SERVI) ; PUT de la liste courante + le nouveau
            # (un id deja pris est remplace) ; la reponse {presets} remplace
            # dzApi.presets et le nouveau preset devient le choix courant.
            # REVUE T4 (23/09/2026) : la case « Rendre la plage I/O seulement » N'EST PAS
            # persistee -- cochee sur le projet A, elle restait cochee sur le projet B
            # (rendu partiel a l'insu de l'utilisateur). L'etat React la garde pour la
            # session ; l'ecriture la retire (rangeOnly:void 0, que JSON.stringify
            # omet) et la lecture initiale l'efface aussi (temoin : une cle rangeOnly
            # ecrite a la main dans localStorage ne revient jamais).
            # ECARTS DATES (revue T4, 23/09/2026) : un preset maison dont l'id est
            # deja pris est REMPLACE en silence par « Enregistrer » (le PUT remplace
            # la liste) ; GET /deliver-presets en panne -> select vide (deux groupes
            # null) -> rien de poste -> master ; la pastille compare la mesure de
            # SESSION (lufs, setLufs) : elle n'est pas remise a null au changement de
            # projet ; « Ajouter a la file » est grise sur `busy` (rendu du meme type)
            # alors que la garde R_EA6 refuse TOUT job non echoue (heritee du bouton or).
            '  var stDzDel=x.useState(function(){try{var v=JSON.parse(localStorage.getItem("dz_montage_deliver")||"null");if(!v||typeof v!=="object")return {};delete v.rangeOnly;return v}catch(_e){return {}}}),dzDel=stDzDel[0],setDzDel=stDzDel[1];\n'
            '  var dzDelRef=x.useRef(null);dzDelRef.current=dzDel;\n'
            '  var stDzApi=x.useState(null),dzApi=stDzApi[0],setDzApi=stDzApi[1];\n'
            '  x.useEffect(function(){if(pop!=="render")return;var alive=!0;\n'
            '    fetch("/api/montage/deliver-presets").then(function(r2){return r2.json()}).then(function(j){if(alive&&dzAliveRef.current&&j&&typeof j==="object")setDzApi(j)}).catch(function(){});\n'
            '    return function(){alive=!1}},[pop]);\n'
            '  function dzDelSet(p){setDzDel(function(d){var n=Object.assign({},d,p);try{localStorage.setItem("dz_montage_deliver",JSON.stringify(Object.assign({},n,{rangeOnly:void 0})))}catch(_e){}return n})}\n'
            '  function dzSavePreset(){var lbl=window.prompt("Nom du preset maison (preset + cadence actuels)");if(!lbl)return;\n'
            '    var id=String(lbl).toLowerCase().replace(/[^a-z0-9_]+/g,"_").replace(/^_+|_+$/g,"").slice(0,32)||"maison";\n'
            '    var tous=dzApi&&Array.isArray(dzApi.presets)?dzApi.presets:[],bi=dzApi&&Array.isArray(dzApi.builtins)?dzApi.builtins:[];\n'
            '    var base=dzDel.preset||(bi[0]&&bi[0].id)||null,m=tous.filter(function(p){return p&&p.id===base})[0];if(m)base=m.base;\n'
            '    var f=Number(dzDel.fps),cur=tous.filter(function(p){return p&&p.id!==id});\n'
            '    fetch("/api/montage/deliver-presets",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({presets:cur.concat([{id:id,label:String(lbl),base:base,fps:isFinite(f)&&f>0?f:null,crf:null}])})})\n'
            '      .then(function(r2){return r2.json().catch(function(){return null}).then(function(j){return {ok:r2.ok,j:j}})})\n'
            '      .then(function(o){if(!o.ok||!o.j){fireNote("Preset refusé : "+((o.j&&(o.j.detail||o.j.error))||"échec"));return}\n'
            '        if(dzAliveRef.current){setDzApi(function(a){return Object.assign({},a||{},{presets:Array.isArray(o.j.presets)?o.j.presets:[]})});dzDelSet({preset:id})}\n'
            '        fireNote("Preset maison « "+lbl+" » enregistré ("+id+").")})\n'
            '      .catch(function(e){fireNote("Preset non enregistré : "+String(e&&e.message||e))})}\n'
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
            # -- « TT4a » (D-21, 21/09/2026) : POSER UN TITRE, LE GESTE --
            # REPLIE ICI, meme mesure que « E1 », « K3 », « X1 » et « V1 » :
            # la ligne `dzTracksRef` qui sert d'ancre a ce remplacement vaut
            # 0 dans .bak_montage.
            # UNE FONCTION DECLAREE, ET C'EST LE PRECEDENT `dzMkToggle` : le
            # geste a DEUX declencheurs -- le raccourci (TT4, dans le `onKey`
            # d'un `useEffect`, d'ou aucune fonction ne sort) et la chip
            # « T+ » (TT5, dans l'arbre rendu). L'ecrire aux deux endroits
            # aurait fait deux sources de verite pour un meme bouton.
            # Declaration HISSEE dans le corps du composant : l'ordre
            # d'ecriture par rapport a `svmTracksSet` (M4b) et aux refs n'y
            # change rien, et tout est resolu a l'APPEL.
            # UN SEUL INSTANTANE D'HISTORIQUE, ET C'EST MESURE :
            # `svmTracksSet` (M4b) fait deja `pushHistory()` avant d'ecrire
            # les pistes. Poser un titre est UN geste -- deux instantanes
            # auraient fait « Annuler » deux fois : la piste sans le carton,
            # puis le carton sans la piste. Les DEUX branches en paient donc
            # EXACTEMENT un : `svmTracksSet` quand t1 manque, `pushHistory`
            # quand `titleTrack` rend le MEME tableau (mesure, banc
            # d'edition `tt_une_piste_deja_la_rend_le_meme_tableau`) -- et
            # aucun `setProj` inutile dans ce second cas.
            # PAS DE GARDE `if(!t)` : le texte est le LITTERAL « Titre » et
            # `titleNew` ne rend `null` que sur un texte vide -- un bras mort
            # que rien n'aurait pu faire rougir (meme lecon que le
            # `dzSw===clipsRef.current` ecarte a la revue du 21/09/2026).
            "  function dzTtAdd(){"
            'var t=DzTracks.titleNew({template:"tiers_inferieur",text:"Titre"},'
            'phRef.current,clipsRef.current,"t1");\n'
            "    var ts=svmTracksOf(dzProjRef.current),ts2=DzTracks.titleTrack(ts);\n"
            "    if(ts2!==ts)svmTracksSet(ts2);else pushHistory();\n"
            "    setClips(clipsRef.current.concat([t]));setSelId(t.id);setDirty(!0);\n"
            '    fireNote("Titre posé à "+t.start.toFixed(2)+" s sur T1 — "'
            '+"l\'inspecteur règle le gabarit et le texte.")}\n'
            # -- « AJ4 » (D-9, 22/09/2026) : POSER UN CLIP D'AJUSTEMENT -----
            # Modele EXACT de dzTtAdd : la piste j1 nait ici si elle manque
            # (`adjustTrack`, sous t1 ; svmTracksSet pousse DEJA l'historique,
            # sinon on pousse nous-memes), puis le clip de 3 s a la tete.
            # `adjustNew` rend null sur un projet vide ou une tete negative :
            # rien n'est pose, rien n'est pousse, la note le dit. Trois
            # portes appellent CE geste : le « + » de j1 (TT11), la chip
            # « J+ » (K5) et Maj+J (R1/R2) -- une seule source de verite.
            "  function dzAjAdd(){"
            'var c=DzTracks.adjustNew(phRef.current,clipsRef.current,"j1");\n'
            '    if(!c){fireNote("Rien à ajuster ici — pose d\'abord un plan");return}\n'
            "    var ts=svmTracksOf(dzProjRef.current),ts2=DzTracks.adjustTrack(ts);\n"
            "    if(ts2!==ts)svmTracksSet(ts2);else pushHistory();\n"
            "    setClips(clipsRef.current.concat([c]));setSelId(c.id);setDirty(!0);\n"
            '    fireNote("Clip d\'ajustement posé sur J1 — ouvre le rack VFX pour lui donner des effets")}\n'
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
            # ── « X1 » (D-20) : LE CATALOGUE DES TRANSITIONS ─────────
            # REPLIÉ ICI, même mesure que « E1 » et « K3 » ci-dessus :
            # l'ancre de ce remplacement (`dzTracksRef`) vaut 0 dans
            # .bak_montage. GET /api/montage/transitions rend les six
            # familles, leurs libellés et le drapeau `live` (tâche 1).
            # LE CATALOGUE EST POSÉ DEUX FOIS, ET C'EST NÉCESSAIRE :
            # dans l'ÉTAT (la galerie X2 et le <select> X3b vivent dans
            # le composant et doivent se re-rendre quand il arrive) et
            # sur `window.__dzTransCat` (X4 retouche `svmTransLabel`,
            # qui est au niveau MODULE — hors de tout composant, elle ne
            # peut lire aucun état ; c'est elle qui titre le losange de
            # jonction et l'étendue de la timeline).
            # UNE SEULE FOIS : l'effet a des dépendances VIDES. Le
            # catalogue est une constante du serveur (la table _XFADE),
            # pas une donnée de projet.
            # L'ÉCHEC EST SILENCIEUX ET C'EST ASSUMÉ : sans catalogue,
            # `dzmTransList` retombe sur les sept transitions
            # historiques du bundle — l'écran reste exactement celui
            # d'avant D-20 au lieu de se vider.
            # `al` annule la pose après démontage (StrictMode rejoue les
            # effets `[]` en double : sans lui, un setState sur un arbre
            # démonté, le no-op silencieux de React 18).
            "  var stDzCat=x.useState(null),dzTransCat=stDzCat[0],"
            "setDzTransCat=stDzCat[1];\n"
            "  x.useEffect(function(){var al=!0;\n"
            "    fetch(\"/api/montage/transitions\")\n"
            "      .then(function(rp){return rp.ok?rp.json():null})\n"
            "      .then(function(d){if(al&&d&&Array.isArray(d.familles)){\n"
            "        window.__dzTransCat=d;setDzTransCat(d)}})\n"
            "      .catch(function(){});\n"
            "    return function(){al=!1}},[]);\n"
            # ── « V1 » (D-12) : LA REF DU VOILE DU LECTEUR ───────────
            # REPLIÉE ICI, même mesure que « E1 », « K3 » et « X1 »
            # ci-dessus : l'ancre de ce remplacement (`dzTracksRef`)
            # vaut 0 dans .bak_montage, donc aucune section ne peut la
            # prendre pour ancre.
            # UNE REF ET PAS UN ÉTAT, et c'est la nature du voile qui
            # l'impose : il change à CHAQUE frame (la boucle `step`
            # fait `setPh`, donc `liveSync` tourne à chaque frame). Un
            # état aurait re-rendu l'arbre entier soixante fois par
            # seconde pour deux propriétés de style. C'est exactement
            # le parti pris des deux hôtes du lecteur (`liveHostRef`,
            # `liveOvRef`), remplis impérativement eux aussi.
            "  var dzVeilRef=x.useRef(null);\n"
            # ── « TT7ref » (D-21, 22/09/2026) : L'HÔTE DE L'APERÇU DE
            # TITRE ET LE CATALOGUE DES GABARITS ──────────────────────
            # REPLIÉS ICI, même mesure que « E1 », « K3 », « X1 » et
            # « V1 » : l'ancre de ce remplacement (`dzTracksRef`) vaut 0
            # dans .bak_montage.
            # L'HÔTE EST UNE REF, PAS UN ÉTAT, et pour la raison du
            # voile : `liveSync` le remplit IMPÉRATIVEMENT à chaque
            # frame (TT8). Un état aurait re-rendu l'arbre entier
            # soixante fois par seconde pour une chaîne de HTML.
            # LE CATALOGUE EST UN ÉTAT, lui, et c'est la raison inverse :
            # l'inspecteur (TT6) est du JSX, il doit se re-rendre quand
            # les huit gabarits arrivent. Il n'est PAS posé sur `window`
            # — contrairement au catalogue des transitions (X1), qui
            # devait être lisible depuis `svmTransLabel`, fonction de
            # niveau MODULE. Ici tout le monde est dans le composant.
            # UNE SEULE FOIS (dépendances VIDES) : les huit gabarits,
            # les seize polices et les cinq couleurs sont des constantes
            # du serveur, pas des données de projet.
            # L'ÉCHEC EST SILENCIEUX ET ASSUMÉ, comme X1 : sans
            # catalogue l'inspecteur rend zéro vignette et ses deux
            # `<select>` sont réduits à « (du gabarit) » — le carton
            # reste réglable par son texte, et le rendu garde ses
            # défauts. Une erreur à l'écran pour un panneau de confort
            # aurait été plus bruyante qu'utile.
            # `al` annule la pose après démontage (StrictMode rejoue les
            # effets `[]` en double).
            # L'HORLOGE DE RAFALE DE L'INSPECTEUR : meme fenetre de 600 ms
            # que `nudgeHistAt` (M17b), `dzDurHistAt` (H6) et
            # `dzStyleHistAt`. La reglette de corps remonte a chaque
            # RELACHEMENT, et au CLAVIER chaque fleche est un `keyup` :
            # cinq crans faisaient cinq instantanes, et « annuler » remontait
            # cran par cran. Une REF et pas un etat : elle ne se lit qu'a
            # l'interieur du rappel, personne ne se re-rend pour elle.
            # ET LE JETON DE REMONTAGE DU CHAMP TEXTE : incremente quand
            # l'hote REFUSE un patch (texte vide). Le clip ne bouge pas,
            # donc la cle porteuse de valeur ne bougerait pas, donc React
            # garderait a l'ecran l'input VIDE alors que le carton a garde
            # son texte. Un ETAT ici, et pas une ref : c'est precisement un
            # re-rendu qu'on veut.
            "  var dzTtHistAt=x.useRef(0);\n"
            "  var stDzTtN=x.useState(0),dzTtNonce=stDzTtN[0],"
            "setDzTtNonce=stDzTtN[1];\n"
            "  var dzTtHostRef=x.useRef(null);\n"
            "  var stDzTt=x.useState(null),dzTitles=stDzTt[0],"
            "setDzTitles=stDzTt[1];\n"
            "  x.useEffect(function(){var al=!0;\n"
            '    fetch("/api/montage/titles")\n'
            "      .then(function(rp){return rp.ok?rp.json():null})\n"
            "      .then(function(d){if(al&&d&&Array.isArray(d.gabarits))"
            "setDzTitles(d)})\n"
            "      .catch(function(){});\n"
            "    return function(){al=!1}},[]);\n"
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
# E-9 (lot E-B, tache 7, 23/09/2026) — REPLI : le label du clip passe par
# DzTracks.durLbl (« label · m:ss » quand la chip « durées » est allumee, le
# label seul sinon) ; l'ancre A_M16D est CONSOMMEE par M16d (0 dans le livre),
# le remplacement la reprenait en tete : c'est cette tete qui change.
R_M16D = (A_M16D.replace('children:c.label}),',
                         'children:DzTracks.durLbl(c.label,c.start,c.end,showDur)}),') + '\n'
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
         # -- « TT1b » (D-21, 21/09/2026) : UNE PISTE DE TITRES NE RECOIT
         # AUCUN ASSET. REPLI dans R_M15 parce que l'ancre naturelle
         # (`    var tr2=trId||"v2",d=durRef.current;`) vaut 1 dans
         # .bak_montage mais 0 dans le bundle patche -- M15 la reecrit, et
         # une section a part aurait passe `--check` pour abandonner au
         # rejeu. Elle est donc posee ICI, en TETE de R_M15.
         # POURQUOI ELLE EXISTE, ET C'EST UN ECART MESURE CONTRE LE PLAN :
         # celui-ci annoncait qu'`addAsset` refuserait t1 « comme il refuse
         # s1 ». MESURE du 21/09/2026 : `addAsset` n'interroge PAS
         # `trackKind` -- il ne teste que le VERROU de piste. Les seize
         # egalites de `trackKind` ferment le glisser-depose (`svmDragOk`,
         # `dropOnTrack`) et la pile d'effets, mais PAS le bouton « + » de
         # l'en-tete de piste : son `onClick` n'aiguille que sur « subs » et
         # retombe sinon sur `openPicker`, qui appelle `addAsset`. Sans cette
         # garde, le « + » de T1 posait un PLAN VIDEO sur la piste des
         # titres -- un clip que le backend collecte comme carton, que
         # `title_spec` refuse faute de `title`, et qui disparaissait du
         # rendu en ne laissant qu'une ligne de journal.
         # LE COURT-CIRCUIT EST LE PREMIER DE TOUS, avant meme le mode
         # remplacement : une piste de titres ne recoit pas davantage un
         # remplacement qu'un ajout, et le mode ne doit pas etre CONSOMME
         # par un refus.
         # `svmKeyLabelNow` PLUTOT QUE `svmKeyLabel` : la premiere est
         # declaree au niveau MODULE (une seule definition, 3 appels dans le
         # .bak) et lit la keymap vivante de localStorage -- aucune
         # discussion de portee, et la note ne ment pas apres un remappage.
         '    if(trackKind(trId||"v2")==="title"){\n'
         '      fireNote("La piste des titres ne reçoit que des cartons — "'
         # LA PHRASE NE REPREND PAS CELLE DE L'INDEX DES MARQUEURS (« … en
         # pose un a la tete de lecture. ») : cette formule-la est comptee a
         # UN par la ligne `D5_I5_les_trois_textes_lisent_la_keymap_vivante`,
         # qui verifie qu'elle n'a pas disparu. Deux phrases identiques
         # auraient fait rougir une ligne qui n'a rien a voir avec D-21.
         '+svmKeyLabelNow("title_add")+" en pose un.");\n'
         '      setOvPick("");return}\n'
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
         # E-6 (lot E-C, tache 2, 23/09/2026) : le geste d'armement du bouton
         # (verrou de piste, ref + miroir, ouverture du selecteur) est EXTRAIT
         # en dzReplaceArm(sel) -- EC1, fonction de l'hote -- pour que le menu
         # contextuel du clip et ce bouton fassent EXACTEMENT la meme chose.
         "        DzTracks.replaceBtn(sel,function(){dzReplaceArm(sel)}),\n"
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
         # E-10 (lot E-C, tache 4, 23/09/2026) : `docked`, l'etat de R_M11 --
         # le Dock le pose en data-docked sur la barre SEULE (l'onglet garde
         # son sens : il replie la barre ancree a zero largeur), la feuille
         # met la barre en flux (position:static) en TETE de ce bandeau : elle
         # se place a gauche des boutons de transport, sans autre changement.
         'docked:dzTbDock,toggleReq:dzTbReq,keyLbl:svmKeyLabel("toolbar"),'
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
          "      srcTracks:svmTracksOf(proj),\n"
          # L7 D-22 (24/09/2026, tache 6) : REPLIE ici (cette queue de props est nee de CE remplacement) --
          # la traduction « dans une nouvelle piste » : la piste S<n> nait (subsNew ; svmTracksSet = historique
          # D-0, bus, projet, NON ENREGISTRE), ses repliques sont des clips neufs tr:"s<n>" (subsCopy), S1 intacte.
          # Revue T6 : les pistes sont lues sur dzProjRef.current (tenu a jour a chaque rendu, .bak:1932, le
          # meme que dzmHistHost) et non sur le `proj` capture par le rendu qui a monte le tiroir -- une piste
          # ajoutee PENDANT la requete de traduction est vue.
          "      /* L7 D-22 (24/09/2026) : la traduction « dans une nouvelle piste » — S<n> naît, ses répliques sont des clips neufs, S1 intacte */\n"
          '      onNewTrack:function(lang,segs){var r2=DzTracks.subsNew(svmTracksOf(dzProjRef.current),lang);svmTracksSet(r2.tracks);\n'
          '        setClips(function(cs){return DzTracks.subsCopy(cs,"s1",r2.id,segs)});setDirty(!0);\n'
          '        fireNote("Piste "+r2.id.toUpperCase()+" ("+lang+") créée avec "+(segs||[]).length+" répliques — S1 intacte ; clic droit sur la tête de "+r2.id.toUpperCase()+" pour la graver au rendu.")}})}')
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
    # L7 D-22 (24/09/2026, tache 6) : REPLIE ici (l'etat de traduction est ne de CE remplacement) -- la cible
    # « dans une nouvelle piste » : cochee, le resultat part a l'hote par props.onNewTrack(cible, repliques)
    # au lieu de props.onChange (S1 reecrite). Le tiroir n'a ni setClips ni setProj (bloc subs, mesure) :
    # c'est un rappel par les props, pose par R_M24H. Un useState de plus (544 -> 545).
    "  /* L7 D-22 (24/09/2026) : traduire DANS UNE NOUVELLE PISTE S<n> — S1 reste intacte (hôte : onNewTrack) */\n"
    "  var s9c=x.useState(!1),dzNewTr=s9c[0],setDzNewTr=s9c[1];\n"
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
    "        if(dzNewTr&&props.onNewTrack)props.onNewTrack(dzTo,dzNext);\n"
    "        else if(props.onChange)props.onChange(dzNext,!0);\n"
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
    # L7 D-22 (24/09/2026, tache 6) : la case « nouvelle piste » (title, E-12) apres la cible ; l'infobulle du
    # bouton dit alors ce qui nait (S<n>) et ce que « Annuler » retire, a la place de subsTrTitle (S1 reecrite).
    "      /* L7 D-22 (24/09/2026) : traduire dans une nouvelle piste S<n> (S1 intacte) au lieu de réécrire S1 */\n"
    '      r.jsxs("label",{className:"sub-trlang sub-trnew",title:"Coché : la traduction naît dans une nouvelle piste de sous-titres S2, S3… (S1 reste intacte ; la piste gravée au rendu se choisit par clic droit sur sa tête). Décoché : S1 est réécrite.",children:[\n'
    '        r.jsx("input",{type:"checkbox",checked:dzNewTr,"aria-label":"Traduire dans une nouvelle piste",onChange:function(e){setDzNewTr(e.target.checked)}},"c"),\n'
    '        r.jsx("span",{className:"sub-trlangl",children:"nouvelle piste"},"l")]},"nt"),\n'
    "      (function(){\n"
    "        var dzOn=DzTracks.subsTrEnabled(dzTrN,dzTe,!!(trJob&&trJob.busy));\n"
    '        return subsActBtn({fam:"fix",\n'
    "          label:DzTracks.subsTrLabel(dzTo,SUBS_LANGS),\n"
    '          but:"traduire les répliques",quiet:!0,disabled:!dzOn.on,\n'
    '          cost:trJob&&trJob.busy?"en cours…":dzTe.ok\n'
    '            ?subsLangLab(dzTo)+" · "+(dzTe.provider||"LLM")+" · "+subsUsd(dzTe.usd)\n'
    '            :(dzTe.st==="vide"?"aucune réplique":"coût indisponible"),\n'
    '          apres:dzOn.on?(dzNewTr?"Les "+dzTrN+" répliques traduites naissent dans une nouvelle piste S2, S3… — S1 reste intacte ; « Annuler » retire la piste et ses répliques.":DzTracks.subsTrTitle(dzTrN)):dzOn.pourquoi,\n'
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
        ' {id:"marker_index",sec:"Montage",lbl:"marqueurs : l\'index",combo:"Ctrl+M"},'
        # -- \u00ab W1 \u00bb (D-4, 21/09/2026) : LES DEUX ACTIONS DE L'ECHANGE --------
        # REPLIEE ICI, meme technique que K1 : l'ancre du plan (\u00ab apres la
        # ligne marker_index de K1 \u00bb) n'existe pas dans .bak_montage -- c'est
        # K1, juste au-dessus, qui la pose. Une section qui la prendrait pour
        # ancre serait refusee par `--check`, qui ne regarde que le .bak.
        # COMBOS MESUREES LIBRES le 21/09/2026 sur la table SVM_ACTIONS du
        # .bak_montage : ni \u00ab Ctrl+\u2190 \u00bb, ni \u00ab Ctrl+\u2192 \u00bb n'y figurent (seuls \u00ab
        # Ctrl+\u2191 \u00bb et \u00ab Ctrl+\u2193 \u00bb le sont, par K1), et aucune des deux n'est
        # dans SVM_COMBO_RESERVED. LE NOM DES FLECHES SOUS CTRL vient de
        # `svmComboOfEvent` : `SVM_EV_NAMES` mappe ArrowLeft/ArrowRight sur
        # les CARACTERES \u00ab \u2190 \u00bb/\u00ab \u2192 \u00bb, et le prefixe \u00ab Ctrl+ \u00bb est concatene
        # tel quel -- donc \u00ab Ctrl+\u2190 \u00bb, jamais \u00ab Ctrl+ArrowLeft \u00bb.
        # CONTEXTE MESURE (M25k, fl\u00e8ches de l'overlay) : `ovArrow` n'est
        # invoque QUE pour les quatre actions `step_back`/`step_fwd`/
        # `cut_prev`/`cut_next` (branche dediee dans `onKey`, plus haut dans
        # le meme composant) ; `swap_left`/`swap_right` ne passent jamais par
        # cette branche, donc Ctrl+\u2190 / Ctrl+\u2192 ne sont PAS captures par
        # l'overlay -- pas besoin d'Alt+\u2190/\u2192 de repli.
        '\n {id:"swap_left",sec:"Montage",lbl:"echanger avec le plan precedent",combo:"Ctrl+\u2190"},\n'
        ' {id:"swap_right",sec:"Montage",lbl:"echanger avec le plan suivant",combo:"Ctrl+\u2192"},'
        # -- « TT4 » (D-21, 21/09/2026), premiere moitie : POSER UN TITRE ---
        # REPLIEE ICI, meme technique que K1 et W1 : l'ancre naturelle (la
        # ligne `swap_right` ci-dessus) est un texte que CE remplacement
        # POSE -- 0 dans .bak_montage, 1 dans le bundle livre.
        # COMBO MESUREE LIBRE le 21/09/2026 sur .bak_montage : `combo:"Maj+T"`
        # vaut 0 (et `combo:"Alt+T"` aussi, repli non necessaire) ; `combo:"T"`
        # vaut 1, c'est le panneau Narration. « Maj+T » n'est pas dans
        # SVM_COMBO_RESERVED (qui ne porte que Ctrl+T et Ctrl+Maj+T).
        # « Maj+T » NE SERA PAS CONFONDUE AVEC « T » : MESURE du dispatch,
        # `onKey` cherche d'abord `m[combo]` EXACT et ne retombe sur la
        # variante sans Maj que si la combo complete est INCONNUE de la
        # table -- elle y est desormais. Meme raisonnement que « Maj+M ».
        '\n {id:"title_add",sec:"Montage",lbl:"titre : poser un carton a la tete",combo:"Maj+T"},'
        # -- « AJ5 » (D-9, 22/09/2026) : POSER UN CLIP D'AJUSTEMENT ----------
        # Meme porte que les titres (Maj+T / T+), PAS un bouton de la barre
        # flottante : le plan de la barre est confronte au design.md (§2.4,
        # §3 onze traces pinnes six fois, §6) et au cablage (dix boutons,
        # TB7, _ATTENDU_B7) -- un 4e bouton PISTES aurait coute une douzaine
        # de pins et une ligne de handoff pour un geste que dzAjAdd fait
        # deja (la piste nait avec le premier clip, comme t1). COMBO MESUREE
        # LIBRE le 22/09/2026 : `combo:"Maj+J"` vaut 0 dans .bak_montage ;
        # `combo:"J"` y vaut 1 et le dispatch cherche la combo EXACTE d'abord.
        '\n {id:"adjust_add",sec:"Montage",lbl:"ajustement : poser un clip a la tete",combo:"Maj+J"},'
        # -- « L7a1 » (L7 D-10, 24/09/2026) : LA TRANSITION PAR DEFAUT A LA COUPE
        # REPLIEE ICI : l'entree adjust_add (l'ancre du plan) est x0 dans
        # .bak_montage -- c'est CE remplacement qui la pose. COMBO : le plan
        # disait « Ctrl+T » (Resolve) et « Ctrl+Maj+T » en repli ; MESURE
        # (B:1641) : les DEUX sont dans SVM_COMBO_RESERVED (nouvel onglet,
        # onglet rouvert). « Alt+T » est libre (x0 dans .bak_montage) et non
        # reservee ; « T » reste a la narration, le dispatch cherchant d'abord
        # la combo EXACTE (meme raisonnement que « Maj+T »).
        '\n {id:"trans_add",sec:"Montage",lbl:"transition : fondu à la coupe du plan sélectionné",combo:"Alt+T"},'
        # -- « L7b1 » (L7 D-6, 24/09/2026) : LE PRESSE-PAPIERS DE CLIPS, REPLIE
        # ICI (meme raison que L7a1 : l'entree adjust_add est x0 dans
        # .bak_montage). COMBOS MESUREES (B:1641) : « Ctrl+C » et « Ctrl+V » ne
        # sont PAS dans SVM_COMBO_RESERVED (seule « Ctrl+Maj+C » l'est) et ne
        # sont le defaut d'aucune action (x0 dans .bak_montage) -- le plan
        # tient, pas de repli Ctrl+Maj. Le Ctrl+C natif reste aux champs de
        # saisie : onKey sort avant tout dispatch sur input/textarea/select/
        # contentEditable (B:3376). Rubrique du menu ☰ : « Édition », par
        # DZM_MENU_RUB de la couche (copy/paste y sont ranges).
        '\n {id:"copy",sec:"Montage",lbl:"copier le clip (entre projets)",combo:"Ctrl+C"},'
        '\n {id:"paste",sec:"Montage",lbl:"coller le clip du presse-papiers à la tête de lecture",combo:"Ctrl+V"},'
        # -- « L5 » (D-32, 24/09/2026, tache 6) : COPIER / COLLER LE GRADE, REPLIES ICI (meme raison que L7b1 :
        # l'entree `paste` est x0 dans .bak_montage). COMBOS MESUREES (B:1655) : « Ctrl+Maj+C » est dans
        # SVM_COMBO_RESERVED (inspecteur des DevTools) -> « Ctrl+Alt+C » / « Ctrl+Alt+V », ni reservees ni prises
        # (x0 dans .bak_montage, x0 comme combo de toute autre entree de la table patchee ; « Alt+C » = la lame,
        # combo DIFFERENTE : le dispatch cherche la combo EXACTE d'abord). Leurs variantes Maj (« Ctrl+Alt+Maj+C/V »)
        # ne retombent sur rien : le repli Maj n'agit que pour les ids de SVM_SHIFT_VARIANTS (ni grade_copy ni
        # grade_paste). Sous Windows Ctrl+Alt = AltGr : AltGr+C / AltGr+V ne produisent aucun caractere en AZERTY
        # francais, et svmComboOfEvent retombe de toute facon sur la lettre PHYSIQUE (e.code) sous Alt. Rubrique
        # du menu ☰ : « Édition » (DZM_MENU_RUB de la couche).
        '\n {id:"grade_copy",sec:"Montage",lbl:"grade : copier (effets couleur et masque du plan sélectionné)",combo:"Ctrl+Alt+C"},'
        '\n {id:"grade_paste",sec:"Montage",lbl:"grade : coller sur le plan sélectionné",combo:"Ctrl+Alt+V"},'
        # -- « L6 » (D-26, 25/09/2026, tache 6) : ENREGISTRER UNE VOIX OFF, REPLIE ICI (meme raison que L5 : l'entree
        # `grade_paste` est x0 dans .bak_montage). COMBO MESUREE (B:1534-1587 + B:1657) : « Alt+R » n'est le defaut d'aucune
        # action (x0 dans .bak_montage, x0 dans la table patchee), n'est PAS dans SVM_COMBO_RESERVED (qui ne porte que
        # Ctrl+R / Ctrl+Maj+R) et svmComboReserved ne la refuse pas (ni touche F, ni Echap, ni Tab) ; aucun gestionnaire
        # du bundle ni des couches ne lit `KeyR` (x0). « R » reste au ripple : le dispatch cherche la combo EXACTE d'abord,
        # et sous Alt svmComboOfEvent retombe sur la lettre PHYSIQUE (e.code), donc AZERTY / QWERTY donnent « Alt+R ».
        # sec « Audio » : la ligne du panneau « ? » ; rubrique du menu ☰ : « Édition » (DZM_MENU_RUB de la couche, dite).
        '\n {id:"vo_record",sec:"Audio",lbl:"voix off : enregistrer / arrêter une prise au micro (lecture du montage)",combo:"Alt+R"},')

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
        '      if(id==="marker_index"){dzMkToggle();return}\n'
        # -- « W2 » (D-4) : LE DISPATCH DE L'ECHANGE -------------------------
        # REPLIE ICI pour la meme raison que K2 : l'ancre du plan (« apres la
        # branche marker_index ») est le texte que CE remplacement-ci pose --
        # 0 dans le .bak. PORTEE MESUREE dans le MEME corps de composant que
        # K2 : `clipsRef`, `selRef` (27 occurrences dans le .bak, `delClip`
        # le lit deja), `trackStRef`, `fireNote`, `pushHistory`, `setClips`,
        # `setDirty` y sont tous declares. `DzTracks.swap` rend TOUJOURS un
        # tableau NEUF (`cs.map(...)` ou `cs.slice()`, jamais `clips`
        # lui-meme) -- `dzSw===clipsRef.current` serait donc FAUX a chaque
        # appel, un bras mort ECARTE (revue du 21/09/2026, M3) --
        # `dzSw.every(function(k,i){return k===clipsRef.current[i]})` suffit
        # SEUL a voir la sortie tot : identite de reference ELEMENT PAR
        # ELEMENT, pas d'egalite de valeurs a construire (contrairement a la
        # plage, R_R2 plus haut).
        '      if(id==="swap_left"||id==="swap_right"){'
        'var dzC=(clipsRef.current||[]).filter(function(k){'
        'return k&&k.id===selRef.current})[0];'
        'if(!dzC){fireNote("Échanger : sélectionnez d\'abord un plan.");return}'
        'if(trackStRef.current[dzC.tr]&&trackStRef.current[dzC.tr].l){'
        'fireNote("Piste "+dzC.tr.toUpperCase()+" verrouillée.");return}'
        'var dzSw=DzTracks.swap(clipsRef.current,dzC.id,id==="swap_left"?-1:1);'
        'if(dzSw.every(function(k,i){return k===clipsRef.current[i]})){'
        'fireNote("Aucun plan voisin de ce côté.");return}'
        'pushHistory();setClips(dzSw);setDirty(!0);'
        'fireNote("« "+(dzC.label||dzC.id)+" » échangé avec le plan "'
        '+(id==="swap_left"?"précédent":"suivant")+".");return}'
        # -- « TT4 » (D-21), seconde moitie : LE DISPATCH DU TITRE ----------
        # REPLIE ICI pour la meme raison que K2 et W2 : l'ancre est la
        # branche `swap_left` que CE remplacement-ci pose (0 dans le .bak).
        # UN SEUL `pushHistory`, ET C'EST MESURE. `svmTracksSet` (M4b) fait
        # deja `pushHistory();svmTrackBusSync(ts);setProj(...);setDirty(!0)`.
        # Poser un titre est UN geste : l'instantane doit donc etre pris UNE
        # fois, AVANT la piste ET avant le clip -- sinon « Annuler » rendait
        # la piste sans le carton, puis le carton sans la piste.
        # LES DEUX BRANCHES PAIENT EXACTEMENT UN INSTANTANE : quand t1
        # manque, c'est `svmTracksSet` qui le pousse ; quand elle est deja
        # la, `titleTrack` rend le MEME tableau (mesure, banc d'edition
        # `tt_une_piste_deja_la_rend_le_meme_tableau`) et on pousse
        # nous-memes. Aucun `setProj` inutile dans le second cas.
        # LE GESTE VIT DANS `dzTtAdd` (TT4a, replie dans R_M16REF) ET PAS
        # ICI : la chip « T+ » (TT5) le declenche aussi, et le dispatch du
        # clavier est enferme dans le `onKey` d'un `useEffect` -- aucune
        # fonction n'en sort. Ecrire le geste aux DEUX endroits aurait fait
        # deux sources de verite pour un meme bouton, exactement ce que le
        # §5.1 du handoff interdit ; `dzMkToggle` est le precedent (K2, K5
        # et K7 l'appellent tous les trois).
        '\n      if(id==="title_add"){dzTtAdd();return}'
        '\n      if(id==="adjust_add"){dzAjAdd();return}'
        # -- « L7a2 » (L7 D-10, 24/09/2026) : LE DISPATCH DE trans_add, REPLIE ICI
        # (l'ancre du plan, la branche adjust_add, est x0 dans .bak_montage).
        # PORTEE MESUREE : clipsRef / selRef / trackStRef / fireNote sont
        # ceux des branches voisines (swap_left) ; `svmSetTransType(id,t)`
        # (B:3931) et `svmTransS(c)` (B:1226) sont des declarations de
        # fonction hissees, dans DzMontage et au module. Le geste est CELUI
        # du losange (openTransPop -> svmSetTransType) : un pushHistory, la
        # duree par svmTransS (0.4 s par defaut, le losange la regle).
        # REFUS dits : pas de plan V1 selectionne ; V1 verrouillee ; pas de
        # coupe a GAUCHE (le backend force « cut » sur le premier clip,
        # montage_service.py:1888 -- une transition y serait muette).
        '\n      if(id==="trans_add"){var dzTc=(clipsRef.current||[]).filter(function(k){return k&&k.id===selRef.current&&k.tr==="v1"})[0];'
        'if(!dzTc){fireNote("Transition : sélectionnez d\'abord un plan de V1.");return}'
        'if(trackStRef.current.v1&&trackStRef.current.v1.l){fireNote("Piste V1 verrouillée.");return}'
        'if(!DzTracks.voisins(clipsRef.current,dzTc).g){fireNote("Transition : « "+(dzTc.label||dzTc.id)+" » n\'a pas de coupe à sa gauche.");return}'
        'svmSetTransType(dzTc.id,"fade");fireNote("Fondu de "+svmTransS(dzTc).toFixed(1)+" s posé à la coupe de « "+(dzTc.label||dzTc.id)+" » — le losange en règle la durée.");return}'
        # -- « L7b2 » (L7 D-6, 24/09/2026) : COPIER / COLLER, REPLIES ICI (meme
        # raison que L7a2). PORTEE MESUREE, celle d'addAsset (B:4406-4431) :
        # clipsRef / selRef / trackStRef / fireNote (branches voisines),
        # phRef (la tete, B:1755), dzTracksRef.current||svmTracksOf(proj)
        # (les pistes, B:4355), dzModeRef (le mode d'edition, B:1835),
        # dzProjRef.current.range (la plage), ovSeq (le numero d'ordre,
        # CONSOMME seulement quand le collage est accepte -- comme addAsset),
        # locked = le meme objet {tr:!0} bati sur trackStRef. Le stockage est
        # localStorage["dz_montage_clipboard"] = {v:1,at,clip}, lu et ecrit en
        # try/catch (navigation privee, quota) ; la version et la piste sont
        # jugees par DzTracks.clipPaste (pur, bance [26]) ; un collage accepte
        # fait UN pushHistory AVANT setClips (modele delClipById B:2123), puis
        # setSelId(id reel) + setDirty. Refus : `id` null -> la note de la
        # couche, rien d'ecrit, rien dans la pile. La demo est une maquette
        # (proj.demo, comme sfxInsert B:4497) : on n'y colle pas.
        '\n      if(id==="copy"){var dzCp=(clipsRef.current||[]).filter(function(k){return k&&k.id===selRef.current})[0];'
        'if(!dzCp){fireNote("Copier : sélectionnez d\'abord un clip.");return}'
        'try{localStorage.setItem("dz_montage_clipboard",JSON.stringify({v:1,at:new Date().toISOString(),clip:DzTracks.clipCopy(dzCp)}))}catch(e){fireNote("Presse-papiers indisponible dans ce navigateur (stockage refusé).");return}'
        'fireNote("« "+(dzCp.label||dzCp.id)+" » copié — "+(svmKeyLabelNow("paste")||"Coller")+" le colle à la tête de lecture, dans ce projet ou dans un autre.");return}'
        '\n      if(id==="paste"){if(dzProjRef.current&&dzProjRef.current.demo){fireNote("Coller : disponible sur un projet réel — la démo est une maquette.");return}'
        'var dzPs=null;try{dzPs=JSON.parse(localStorage.getItem("dz_montage_clipboard")||"null")}catch(e){dzPs=null}'
        'var dzPq=ovSeq.current+1,dzPr=DzTracks.clipPaste(clipsRef.current||[],dzPs,{head:phRef.current,tracks:dzTracksRef.current||svmTracksOf(dzProjRef.current),mode:dzModeRef.current,seq:dzPq,'
        'range:dzProjRef.current&&dzProjRef.current.range,locked:(function(){var o={},k;for(k in trackStRef.current)if(trackStRef.current[k]&&trackStRef.current[k].l)o[k]=!0;return o})()});'
        'if(dzPr.id==null){fireNote(dzPr.note||"Rien n\'a été collé.");return}'
        'ovSeq.current=dzPq;pushHistory();setClips(dzPr.clips);setSelId(dzPr.id);setDirty(!0);'
        'fireNote("« "+(dzPs.clip.label||dzPr.id)+" » collé sur "+String(dzPr.track).toUpperCase()+" à "+svmShort(Number(dzPr.start)||0)+(dzPr.mode!=="ecraser"?" (mode « "+DzTracks.modeLabel(dzPr.mode)+" »)":"")+(dzPr.note?" — "+dzPr.note:"")+".");return}'
        # -- « L5 » (D-32, 24/09/2026, tache 6) : LE DISPATCH DU GRADE, REPLIE ICI (meme raison que L7b2). LE GESTE
        # VIT DANS dzGradeCopy / dzGradePaste (replis de R_EC1), que le menu de clip appelle AUSSI -- une seule
        # source de verite (precedent dzTtAdd / dzMkToggle) ; eux-memes passent par DzTracks.gradeCopyDo /
        # gradePasteDo, les gestes du panneau Etalonnage (un stockage, une phrase).
        '\n      if(id==="grade_copy"){dzGradeCopy(selRef.current);return}'
        '\n      if(id==="grade_paste"){dzGradePaste(selRef.current);return}'
        # -- « L6 » (D-26, 25/09/2026, tache 6) : LE DISPATCH DE LA VOIX OFF, REPLIE ICI (meme raison que L5). Le geste vit
        # dans la puce (la couche) : elle inscrit sa bascule dans dzVoRef (repli de R_M16REF) a chaque rendu et l'en retire au
        # demontage -- le clavier et le clic font LE MEME geste (une source de verite, comme dzGradeCopy). Sans puce montee,
        # la frappe est DITE, jamais muette.
        '\n      if(id==="vo_record"){if(typeof dzVoRef.current==="function")dzVoRef.current();else fireNote("Voix off : l\'enregistreur n\'est pas prêt.");return}')

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
        'children:"\u25c6 "+((proj.markers||[]).length)}),'
        # -- « TT5 » (D-21, 21/09/2026) : LA CHIP « T+ » ---------------------
        # REPLIEE ICI : l'ancre du plan (« a cote de ◆ n ») est la chip des
        # marqueurs que CE remplacement-ci pose -- 0 dans .bak_montage.
        # ELLE NE PORTE PAS D'ETAT (`data-on`) : poser un titre est un GESTE,
        # pas une bascule, contrairement a « ripple » et a l'index des
        # marqueurs. Son `aria-label` suit la regle de M21 : sous largeur
        # reduite les chips passent en glyphe seul, et « T+ » nu serait leur
        # nom accessible.
        # LA COMBO VIENT DE LA KEYMAP VIVANTE (`svmKeyLabel`, declaree dans
        # ce composant) : l'action est remappable par le panneau « ? », et
        # une infobulle qui dirait « Maj+T » en dur MENTIRAIT apres un
        # remappage. Meme lecon que I-5.
        '\n          r.jsx("button",{className:"svm-toolchip",'
        '"aria-label":"poser un titre",'
        'title:"Poser un titre à la tête ("+svmKeyLabel("title_add")+")",'
        'onClick:function(){dzTtAdd()},'
        'children:"T+"}),'
        # -- « AJ5 » (D-9, 22/09/2026) : LA CHIP « J+ », modele exact de T+.
        '\n          r.jsx("button",{className:"svm-toolchip",'
        '"aria-label":"poser un clip d\'ajustement",'
        'title:"Poser un clip d\'ajustement à la tête ("+svmKeyLabel("adjust_add")+")",'
        'onClick:function(){dzAjAdd()},'
        'children:"J+"}),')

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
# L5 D-32 (24/09/2026, tache 6 ; revue T6, I1) : LA LIGHTBOX EST MODALE AU CLAVIER -- la garde vient AVANT la branche
# Echap (meme forme que celle de `kbRef` juste au-dessus dans onKey) : sous le voile, Espace lançait la lecture et
# Suppr / Ctrl+Z modifiaient la timeline, un popover ouvert par raccourci passait au-dessus (z 20 > 19). Seul Echap
# agit : il la ferme. Son ref est pose dans R_M16REF (la ligne epinglee de dzScrimRef ne bouge pas).
R_K7 = ('if(dzLbRef.current){if(e.key==="Escape"){e.preventDefault();setDzLb(!1)}return}'
        ' /* D-32 : lightbox ouverte = modale au clavier, seul Échap agit (il la ferme) ; l\'Échap de l\'overlay décrit plus haut suit */\n'
        '      if(e.key==="Escape"){\n'
        "        if(dzMkOnRef.current){e.preventDefault();dzMkToggle(!1);return}\n"
        # E-11 (lot E-B, tache 5, 23/09/2026) : ECHAP FERME LE VOILE ET CE
        # QU'IL PORTE (popover preview/rendu, bandeau de fin). REPLI : la
        # branche Escape de onKey est consommee par K7 (le plan supposait
        # R_R2 : ecart mesure). Apres l'index des marqueurs (ouvert par
        # dessus, il se ferme d'abord), avant le repli ovEsc de l'overlay.
        # E-14 (lot E-C, tache 5, 23/09/2026) : LE TROU SELECTIONNE S'EFFACE
        # AVANT le voile (un trou sous un popover : Echap efface d'abord le
        # trou, le popover au second Echap) -- meme repli, meme branche.
        "        if(gapSelRef.current){e.preventDefault();setGapSel(null);return}\n"
        # E-6 (lot E-C, tache 2, 23/09/2026) : ... et le menu ☰ / contextuel
        # (dzMenu, porte par le meme ref) -- meme repli, meme branche.
        "        if(dzScrimRef.current){e.preventDefault();setPop(\"\");setDzFin(null);setDzMenu(null);return}\n"
        "        if(kbAudioRef.current&&kbAudioRef.current.ovEsc&&"
        "kbAudioRef.current.ovEsc())e.preventDefault();\n"
        "        return}")


# ══ D-20 (21/09/2026) — LA GALERIE DES TRANSITIONS, CÔTÉ ÉCRAN ═════════
# Le bundle ne connaissait que SEPT transitions (`SVM_TRANS`, niveau
# module). L'ffmpeg livré en porte 58, que le backend sert maintenant par
# familles (GET /api/montage/transitions, tâche 1). Les quatre sections
# ci-dessous branchent l'écran dessus SANS toucher ni à `SVM_TRANS` (les
# sept restent le repli hors-ligne et la liste des libellés FR) ni aux
# sept règles `.svm-tprev[data-tt]` de son-vfx-montage.css (intouchable).
# X1 est REPLIÉ dans R_M16REF (son ancre vaut 0 dans .bak_montage) ; les
# quatre ancres ci-dessous valent 1/1 dans .bak_montage — mesuré le
# 21/09/2026 — et aucune section antérieure n'y touche.

# ── X2 : la grille de sept tuiles devient la galerie par familles ─────
# L'ANCRE EST LE BLOC ENTIER, de la <div class=svm-transgrid> jusqu'à la
# dernière tuile incluse : un remplacement de la seule PREMIÈRE ligne
# aurait laissé derrière lui le corps du `map` — neuf lignes orphelines
# et un bundle que `node --check` refuse. Ce qui SUIT (le curseur de
# durée, « Appliquer à toutes les coupes ») n'est pas dans l'ancre.
A_X2 = ('      r.jsx("div",{className:"svm-transgrid",children:SVM_TRANS.map(function(o){\n'
        '        return r.jsxs("button",{className:"svm-transtile","data-sel":base===o[0]?"":void 0,\n'
        '          title:o[1]+" ("+o[0]+")",\n'
        '          onClick:function(){svmSetTransType(jc.id,o[0])},children:[\n'
        '          /* micro-scène A/B — aperçu animé du type ; la tuile sélectionnée est\n'
        "             figée sur l'état final, reduced-motion la rend statique */\n"
        '          r.jsxs("span",{className:"svm-tprev","data-tt":o[0],"aria-hidden":!0,children:[\n'
        '            r.jsx("i",{className:"svm-ta"}),r.jsx("i",{className:"svm-tb"})]}),\n'
        '          r.jsx("span",{className:"svm-ttl",children:o[1]})]},o[0])})}),')
R_X2 = ('      /* D-20 — LA GALERIE. Les sept tuiles cèdent la place à\n'
        '         TransGrid() de la couche : « coupe », puis les historiques du\n'
        '         bundle qui ne sont pas au catalogue, puis les six\n'
        '         familles servies. La couche garde `.svm-transtile`,\n'
        '         `.svm-tprev` et `data-tt` — les règles du bundle\n'
        "         continuent d'animer la moitié gauche, de mettre en\n"
        '         pause hors survol et de figer la tuile choisie ;\n'
        "         `data-fam` et `data-dir` n'ajoutent que l'animation de\n"
        '         la moitié droite, dans montage.css. */\n'
        '      r.jsx(DzTracks.TransGrid,{legacy:SVM_TRANS,cat:dzTransCat,cur:base,\n'
        '        onPick:function(id){svmSetTransType(jc.id,id)}}),')

# ── X3 : « ce nom est-il connu ? » se demande à la LISTE COMPLÈTE ──────
# Sans cette section, un `wipetl` choisi dans la galerie serait revenu
# dans l'inspecteur étiqueté « wipetl (hérité) » ET en double (une fois
# comme option d'héritage, une fois dans sa famille) : `known` ne
# regardait que les sept de SVM_TRANS. L'option « (hérité) » garde tout
# son sens pour un nom qui n'est NI au catalogue NI dans les sept — un
# vieux projet, ou un catalogue qui n'est pas arrivé.
A_X3 = "    var known=SVM_TRANS.some(function(o){return o[0]===base});"
R_X3 = ('    var known=DzTracks.transList(SVM_TRANS,dzTransCat).some(function(f){\n'
        '      return f.items.some(function(it){return it.id===base})});')

# ── X3b : le <select> liste tout le catalogue, une option par nom ─────
# « famille · libellé » plutôt qu'un <optgroup> : le <select> porte la
# classe `.svm-secbtn` du bundle et un optgroup y serait rendu par le
# système, hors charte. La forme dit la même chose sans une règle de plus.
A_X3B = ('            .concat(SVM_TRANS.map(function(o){\n'
         '              return r.jsx("option",{value:o[0],children:o[1]},o[0])}))}),')
R_X3B = ('            .concat(DzTracks.transList(SVM_TRANS,dzTransCat)\n'
         '              .reduce(function(a,f){return a.concat(f.items.map(function(it){\n'
         '                return r.jsx("option",{value:it.id,\n'
         '                  children:f.label+" · "+it.label},it.id)}))},[]))}),')

# ── X4 : le libellé du losange et de l'étendue vient du catalogue ──────
# `svmTransLabel` est au niveau MODULE (elle sert au losange de jonction,
# à l'infobulle de l'étendue et au titre du clip) : elle ne peut lire
# aucun état de composant, d'où `window.__dzTransCat`, posé par l'effet de
# X1 EN MÊME TEMPS que l'état. Sans catalogue (page fraîche, serveur
# muet), la couche retombe sur les sept libellés de SVM_TRANS puis sur le
# nom nu — exactement ce que faisait la ligne remplacée.
A_X4 = "  var f=SVM_TRANS.find(function(o){return o[0]===b});return f?f[1]:b}"
R_X4 = "  return DzTracks.transLabel(b,SVM_TRANS,window.__dzTransCat||null)}"


# ══ D-12 (21/09/2026) — LES FONDUS SIMPLES JOUÉS EN DIRECT ════════════
# Le lecteur vivant ne montre qu'UN clip à la fois (`svmActiveV1`) : à la
# jonction, l'image bascule sèchement quelle que soit la transition. Les
# 58 `xfade` restent invisibles avant Preview, ce que la galerie dit déjà
# (« visible après Preview ») — mais les trois fondus que le catalogue
# marque `live` (fade, fadeblack, fadewhite) SE JOUENT, par un voile.
# V1 est REPLIÉE dans R_M16REF (son ancre vaut 0 dans .bak_montage) ; les
# deux ancres ci-dessous valent 1/1 dans .bak_montage — mesuré le
# 21/09/2026 — et aucune section antérieure ne touche au cadre du lecteur
# ni au corps de `liveSync`.

# ── V2 : le voile est un enfant du cadre, juste après les deux couches ──
# L'ANCRE EST LA LIGNE DU « trou » : elle suit IMMÉDIATEMENT `.svm-liveov`,
# et c'est la seule place possible. Le voile doit couvrir le fond ET les
# overlays (donc après eux dans le DOM) sans couvrir les sous-titres, le
# cadre de sélection ni les guides (donc avant eux, et SANS `z-index` :
# mesuré, aucun de ces trois voisins n'en porte, l'ordre du DOM suffit).
# CONDITIONNÉ PAR `liveOn`, comme les deux couches : en aperçu 480p c'est
# un `<video>` qui joue le rendu, transitions COMPRISES — y superposer un
# voile les jouerait DEUX FOIS.
A_V2 = ('liveOn&&!liveClip?r.jsx("div",{className:"svm-livegap",'
        'children:"trou"}):null,')
R_V2 = (
        # -- « TT7 » (D-21, 22/09/2026) : L'HOTE DE L'APERCU DE TITRE ------
        # REPLIE ICI, et c'est le plan lui-meme qui le prevoit : l'ancre
        # (la ligne du « trou ») est CONSOMMEE par V2, posee en tache 3.
        # EN TETE DU REMPLACEMENT, ET AVEC SON PROPRE COMMENTAIRE : la
        # premiere redaction posait la ligne SOUS le commentaire « D-12 --
        # LE VOILE DES FONDUS EN DIRECT », qui decrit le voile et pas
        # l'hote de titre -- a l'ecran du bundle, le commentaire semblait
        # documenter la ligne suivante, qui n'etait plus la sienne
        # (correctif du 22/09/2026).
        # AVANT LE VOILE DANS LE DOM, et c'est une TRANCHE, pas un detail.
        # Au rendu, la gravure ASS des titres est chainee AVANT S1 mais
        # APRES les `xfade` (tache 5, mesure) : un fondu au raccord passe
        # donc PAR-DESSUS le titre, alors qu'il ne touche pas aux
        # sous-titres. L'ecran doit dire la meme chose -- le titre est
        # SOUS le voile, les sous-titres DESSUS. Sans z-index : dans
        # `.svm-frame` tous les enfants sont absolus et aucun des voisins
        # qui comptent n'en porte, l'ordre du DOM suffit (meme mesure que
        # V2).
        # CONDITIONNE PAR `liveOn` comme le voile et les deux couches : en
        # apercu 480p c'est un `<video>` qui joue le rendu, titre GRAVE
        # compris -- y superposer l'apercu HTML l'aurait affiche DEUX fois,
        # et le faux par-dessus le vrai.
        # VIDE AU MONTAGE : `liveSync` (TT8) ecrit son `innerHTML` a la
        # premiere frame. Aucun enfant JSX, donc React ne se bat jamais
        # avec l'ecriture imperative.
        "/* D-21 — L'APERÇU VIVANT DU CARTON. Vide, et écrit\n"
        "             impérativement par `liveSync` à chaque frame. POSÉ\n"
        "             AVANT LE VOILE : au rendu, les titres sont gravés\n"
        "             APRÈS les `xfade`, donc un fondu passe par-dessus le\n"
        "             titre — et pas par-dessus les sous-titres. */\n"
        '          liveOn?r.jsx("div",{className:"svm-livetitle",'
        'ref:dzTtHostRef,"aria-hidden":!0}):null,\n'
        "          /* D-12 — LE VOILE DES FONDUS EN DIRECT. Vide, transparent au\n"
        "             repos, et écrit impérativement par `liveSync` (couleur +\n"
        "             opacité) à chaque frame : le lecteur vivant n'a qu'un\n"
        "             hôte, donc pas de crossfade A/B — un voile dit OÙ tombe\n"
        "             la transition et COMBIEN elle dure. */\n"
        '          liveOn?r.jsx("i",{className:"svm-xfveil",ref:dzVeilRef,'
        '"aria-hidden":!0}):null,\n'
        '          ') + A_V2

# ── V3 : l'écriture, EN TÊTE de `liveSync` ────────────────────────────
# EN TÊTE, et pas ailleurs : `liveSync` sort tôt (`if(!host||!ov){…return}`)
# quand les deux hôtes ne sont pas encore montés, et le voile doit quand
# même être remis à zéro dans ce cas — sinon un voile plein survivrait à un
# passage en aperçu 480p. La ref est donc lue AVANT `var host=`.
#
# MESURE QUI AUTORISE CETTE FORME (21/09/2026) : `liveSync` ne réécrit
# JAMAIS `liveHostRef.current.style.*` plus bas dans son corps — les cinq
# seules occurrences de `host.` y sont `_svmKey`, `firstChild`,
# `removeChild` et `appendChild`. Le repli prévu par le plan (poser
# l'opacité sur `liveVideoRef.current`) n'a donc pas lieu d'être.
#
# ET POURTANT L'HÔTE N'EST PAS TOUCHÉ, ce qui est un ÉCART ASSUMÉ avec le
# plan : il demandait, pour « dim » (le fondu simple), `host.style.opacity
# = 1 - alpha`. DEUX MESURES l'écartent.
#   1. `.svm-live{background:#000}` et `.svm-frame` porte un DAMIER
#      (`repeating-linear-gradient` panel2/panel3). Baisser l'opacité de
#      l'hôte ne fait pas apparaître du noir : elle fait apparaître le
#      DAMIER. Le résultat voulu — « l'image s'efface sur le noir du
#      lecteur » — est obtenu EXACTEMENT par un voile noir à alpha :
#      a·noir + (1−a)·image, soit l'image à (1−a) SUR DU NOIR. Les deux
#      calculs ne diffèrent que par ce qu'il y a dessous, et c'est là que
#      la forme du plan se trompait.
#   2. L'élément média est PARTAGÉ (pool LRU par source) et l'hôte change
#      d'enfant AU RACCORD, c'est-à-dire au milieu du fondu : une opacité
#      posée sur l'ancien enfant lui survivrait dans le pool.
# « dim » reste un verdict DISTINCT dans la couche (le mécanisme, pas la
# couleur) : le jour où le lecteur aura deux hôtes, c'est lui qui dira
# qu'il faut croiser plutôt que voiler.
A_V3 = "  function liveSync(){"
R_V3 = (A_V3 + "\n"
        "    /* D-12 — LE VOILE DES TROIS FONDUS JOUABLES EN DIRECT. En TÊTE :\n"
        "       `liveSync` sort tôt quand les hôtes ne sont pas montés, et le\n"
        "       voile doit être remis à zéro même dans ce cas.\n"
        "       LA TÊTE EST BORNÉE COMME CELLE DE L'IMAGE, pas brute : le clip\n"
        "       montré est choisi sur `min(ph, dur-0.001)` (trois lignes plus\n"
        "       bas) — voiler sur `ph` aurait fait, à la toute fin de la\n"
        "       timeline, un voile qui ne correspond plus à l'image affichée.\n"
        "       « dim » (le fondu simple) est voilé EN NOIR comme `fadeblack`,\n"
        "       et c'est assumé : avec un hôte unique les deux se voient\n"
        "       PAREIL à l'écran — seul le rendu ffmpeg les sépare (l'un\n"
        "       croise deux images, l'autre passe par le noir). La couche\n"
        "       garde le verdict distinct ; l'écran ne peut pas encore le\n"
        "       montrer. L'hôte n'est jamais touché : il est noir, et rien\n"
        "       n'est écrit sur un élément média partagé par le pool.\n"
        "       LA SIGNATURE `_dzVeil` ÉVITE L'ÉCRITURE INUTILE : `liveSync`\n"
        "       tourne à CHAQUE frame et le voile est nul presque tout le\n"
        "       temps — sans elle, deux écritures de style par frame pour\n"
        "       rien. Même parade que `_svmTfSig` et `_svmKey` plus bas. */\n"
        "    var dzVe=dzVeilRef.current;\n"
        "    if(dzVe){\n"
        "      var dzVt=Math.min(phRef.current,Math.max(0,durRef.current-.001));\n"
        "      var dzVv=DzTracks.veil(clipsRef.current,dzVt);\n"
        '      var dzVk=dzVv.color+"|"+dzVv.alpha;\n'
        "      if(dzVe._dzVeil!==dzVk){dzVe._dzVeil=dzVk;\n"
        '        dzVe.style.background=(dzVv.color&&dzVv.color!=="dim")?dzVv.color:"#000";\n'
        "        dzVe.style.opacity=String(dzVv.alpha||0)}}\n"
        "    /* TT8 (D-21) — L'APERCU VIVANT DU CARTON, au meme endroit et\n"
        "       pour les memes raisons que le voile : EN TETE, parce que\n"
        "       `liveSync` sort tot quand les hotes ne sont pas montes et\n"
        "       que l'apercu doit etre EFFACE meme dans ce cas -- sinon un\n"
        "       titre survivrait a un passage en apercu 480p, ou l'image\n"
        "       porte deja le titre GRAVE : on l'aurait vu en double.\n"
        "       LA TETE EST BORNEE COMME CELLE DU VOILE (`dzVt`), pas brute :\n"
        "       le clip montre est choisi sur `min(ph, dur-0.001)`, et un\n"
        "       carton qui finit exactement a la fin de la timeline aurait\n"
        "       disparu une frame avant l'image qu'il accompagne.\n"
        "       LA SIGNATURE `_dzHtml` EVITE L'ECRITURE INUTILE : `liveSync`\n"
        "       tourne a CHAQUE frame et la chaine est la meme pendant toute\n"
        "       la duree du carton. Sans elle, un `innerHTML` par frame --\n"
        "       donc un sous-arbre DETRUIT et RECONSTRUIT soixante fois par\n"
        "       seconde, ce qui aurait relance l'animation CSS d'entree en\n"
        "       boucle et rendu le titre illisible. Meme parade que\n"
        "       `_dzVeil` ci-dessus, `_svmTfSig` et `_svmKey` plus bas.\n"
        "       LA COUCHE ECHAPPE LE TEXTE (`ttEsc`) : il vient de\n"
        "       l'utilisateur et il part en `innerHTML`. */\n"
        "    var dzTtH=dzTtHostRef.current;\n"
        "    if(dzTtH){\n"
        "      var dzTtT=Math.min(phRef.current,Math.max(0,durRef.current-.001));\n"
        "      var dzTtC=DzTracks.titleAt(clipsRef.current,dzTtT);\n"
        '      var dzTtX=dzTtC?DzTracks.titleHtml(dzTtC,dzTtT):"";\n'
        "      if(dzTtH._dzHtml!==dzTtX){dzTtH._dzHtml=dzTtX;dzTtH.innerHTML=dzTtX}}")


# ══════════════════════════════════════════════════════════════════════════
# D-21 (21/09/2026, tache 6) — LE GENRE `title` ET CE QUE LE CARTON EMPORTE
# ══════════════════════════════════════════════════════════════════════════
# Les SIX autres morceaux du lot (TT1b, TT2, TT3, TT4 en deux moities, TT5)
# visent des textes que d'autres remplacements POSENT, ou une ancre CONSOMMEE
# (A_M5) : ils sont REPLIES la-bas, chacun avec sa mesure. Ces deux ancres-ci
# valent 1/1 dans .bak_montage et aucune section anterieure n'y touche.
#
# TT1 : LE QUATRIEME GENRE DE PISTE. `trackKind` ne lit que l'INITIALE de
# l'identifiant, et c'est la recette ecrite au-dessus de lui dans le bundle :
# « le declarer ici suffit a ce que tout le reste refuse deja ce qu'il faut ».
# MESURE du 21/09/2026 : les SEIZE appels de `trackKind` dans .bak_montage
# sont TOUS des EGALITES (`==="video"`, `==="audio"`, `==="subs"`), relevees
# une a une -- un genre « title » ne trouve donc le sien nulle part, et t1
# refuse le depot d'asset (`svmDragOk`, `dropOnTrack`), la pile d'effets, le
# mixage par clip et l'inspecteur audio, exactement comme S1. Le SEUL trou
# etait le bouton « + » de l'en-tete, qui ne passe pas par `trackKind` :
# TT1b le ferme dans `addAsset`.
# ET LA LETTRE ETAIT LIBRE : les 18 occurrences de `id:"t` du .bak sont des
# ports de noeuds (`id:"text"`, `id:"ticker"`), des gabarits (`id:"tpl_…"`),
# des sujets, des canaux (`id:"telegram"`) et des voix (`id:"tide"`) -- AUCUN
# identifiant de PISTE ne commence par « t ». Relevees une a une.
A_TT1 = ('  function trackKind(trId){var k=String(trId||"").charAt(0);\n'
         '    return k==="a"?"audio":k==="s"?"subs":"video"}')
# AJ1 (D-9, 22/09/2026) : « j » = adjust, REPLI ici (la ligne est celle que
# TT1 reecrit). MESURE : `id:"j` vaut 8 dans .bak_montage, tous des `job_…`/
# `jog_…` -- aucun identifiant de PISTE. Meme table que dzmKindOf (couche).
R_TT1 = ('  function trackKind(trId){var k=String(trId||"").charAt(0);\n'
         '    return k==="a"?"audio":k==="s"?"subs":k==="t"?"title":k==="j"?"adjust":"video"}')

# TT2b : CE QUE LE CARTON EMPORTE AU RENDU. Le backend reconnait un titre a
# la PISTE (`_tracks_meta[tr].kind === "title"`, mesure de la tache 5) et lit
# `c.title` -- sans cette cle, le clip partait NU et `title_spec` rendait
# `None` : un carton compte « ignore » dans le journal, invisible a l'ecran.
# `kind` PART AUSSI, et ce n'est pas une redondance : c'est la cle que le
# filtre de R_M5 (TT2) interroge pour laisser passer un clip sans `src`, et
# le backend a de quoi journaliser un carton pose sur une piste qui n'est PAS
# de titres.
# LE PAYLOAD D'UN PROJET SANS CARTON NE CHANGE PAS D'UN OCTET : les deux
# valeurs sont `undefined` sur tous les autres clips, et `JSON.stringify`
# OMET une cle dont la valeur est `undefined` -- la cle EXISTE dans l'objet,
# elle est ABSENTE de la chaine. MESURE AU BANC, sous node :
# `D21_TT2b_un_projet_sans_carton_envoie_le_payload_d_avant` de
# test_montage_bundle.py (ajoutee le 22/09/2026 ; la premiere redaction de
# cette prose annoncait la mesure sans la fournir).
A_TT2B = ('        var o={tr:c.tr,src:c.src,start:c.start,end:c.end,'
          'srcIn:c.srcIn||0,')
R_TT2B = ('        var o={tr:c.tr,src:c.src,start:c.start,end:c.end,'
          'srcIn:c.srcIn||0,kind:c.kind,title:c.title,')

# TT9 : L'INSPECTEUR In/Out/Duree SE TAIT SUR UN CARTON. (Sa jumelle TT9b,
# la pile d'effets, est REPLIEE dans R_M13, dont l'ancre est la ligne meme
# qu'il fallait reecrire.)
# POURQUOI : « une fenetre de source, ca ne veut rien dire pour une ligne de
# texte » -- le commentaire du bundle, ecrit pour S1, vaut MOT POUR MOT pour
# un carton, qui n'a pas de `src` non plus. La section rendait donc In, Out,
# Duree et Vitesse sur un clip sans source : quatre reglages qui ne
# s'appliquent a rien, et un `svmSetV1Speed` qui aurait ecrit une `speed` sur
# un titre.
# LA SECTION « Sous-titre » PREND LE RELAIS POUR S1 ; pour un carton, c'est
# l'inspecteur de titre (TT6) qui le prend, pose quatre lignes plus bas dans
# la meme colonne.
A_TT9 = '          return sel&&sel.tr==="s1"?null'
R_TT9 = ('          return sel&&(trackKind(sel.tr)==="subs"'
         '||trackKind(sel.tr)==="title")?null')

# TT10 : `c.src.job_id` SUR UN CLIP QUI PEUT NE PAS AVOIR DE `src`.
# TT2 (tache 6) a fait sauter l'invariant du payload -- `renderPayload`
# jetait tout clip sans `src` (`clips.filter(function(c){return c.src})`), et
# c'est justement ce filtre que TT2 a ouvert pour laisser passer les cartons.
# Toute ligne du corps de la boucle qui DEREFERENCE `c.src` leve desormais un
# TypeError sur le premier carton : « Cannot read properties of undefined
# (reading 'job_id') ». Mesure : c'est la SEULE des lignes de la boucle a le
# faire (les autres lisent `c.effects`, `c.opacity`, `c.gain`… sur `c`).
# LA CORRECTION GARDE LE SENS : `c.src&&c.src.job_id` dit « un VRAI plan
# video », ce que la ligne voulait deja dire -- un clip sans source n'en est
# pas un, et un carton ne defile pas.
A_TT10 = ('        if(c.tr==="v1"&&c.src.job_id&&typeof c.speed==="number"'
          '&&c.speed>0&&')
R_TT10 = ('        if(c.tr==="v1"&&c.src&&c.src.job_id&&'
          'typeof c.speed==="number"&&c.speed>0&&')

# TT11 : LE « + » DE L'EN-TETE DE T1 DISAIT ET FAISAIT FAUX.
# L'infobulle promettait « Ajouter une image ou un rendu a la tete de
# lecture » (quatrieme branche du ternaire, celle qui ramasse tout ce qui
# n'est ni subs ni audio) et le clic ouvrait `openPicker("t1")` : le
# selecteur d'assets, sur la piste qui n'en recoit aucun. TT1b rattrapait la
# chute DANS `addAsset` -- une note, et rien de pose. Le bouton mentait donc
# deux fois : sur ce qu'il propose et sur ce qu'il fait.
# IL POSE MAINTENANT UN CARTON, par le MEME `dzTtAdd` que le raccourci (TT4)
# et la chip « T+ » (TT5) : troisieme declencheur, zero troisieme ecriture du
# geste. Les deux autres branches sont intactes.
# L'INFOBULLE NE REPREND PAS LA PHRASE DE TT1b (« La piste des titres ne
# recoit que des cartons — … en pose un »), et c'est une MESURE : cette
# phrase-la est comptee a UN par `D5_I5_les_trois_textes_lisent_la_keymap_
# vivante`, et un bouton qui POSE un carton ne peut pas dire « Maj+T en pose
# un » -- ce serait renvoyer ailleurs pour ce qu'il fait lui-meme. Elle dit
# le geste ET la restriction, et elle lit la keymap VIVANTE
# (`svmKeyLabelNow`, niveau MODULE) comme les quatre autres textes de D-5/
# D-21.
A_TT11 = ('                :"Ajouter une image ou un rendu à la tête de '
          'lecture",\n'
          '              onClick:function(){\n'
          '                if(trackKind(tr.id)==="subs"){subsAddHere();'
          'return}\n'
          '                openPicker(tr.id)},children:"+"},"add");')
# AJ4 (D-9, 22/09/2026) : le « + » de l'en-tete de j1 pose un clip
# d'ajustement (dzAjAdd, replie dans R_M16REF) -- REPLI ici, la ligne est
# celle que TT11 reecrit.
# EB3 (E-2, 23/09/2026) : le « + » d'une piste VIDEO ouvre le tiroir Medias
# (medTr = la piste visee, medOn, les trois autres tiroirs fermes) -- REPLI
# ici, meme ligne. ECART DATE au plan (23/09/2026) : `openPicker(tr.id)`
# n'a qu'UN appelant dans .bak_montage (:5365, ce « + ») ; le rediriger
# sans porte de secours rendrait le selecteur Images (ovPicker, garde par
# le dementi 7 pour « lier » une image) INATTEIGNABLE sur V1/V2. Maj+clic
# garde cette porte, et l'infobulle le dit. L'audio passe toujours par
# `openPicker` (sons a lier), sans changement.
# ECARTS DATES (revue 23/09/2026) : (1) le « + » AUDIO ouvre ovPicker SANS
# fermer le tiroir Medias -- meme comportement que Sons/Narration face au
# selecteur ; l'exclusivite irait dans openPicker, pas ici. (2) « seul
# appelant » vaut pour .bak_montage : le bundle PATCHE porte aussi
# `openPicker(sel.tr)` (inspecteur) et `badSrc(...openPicker(c.tr))`, tous
# deux lies a un clip EXISTANT -- aucune porte pour lier une image sur une
# piste vide autre que ce « + ». (3) Piste verrouillee : le refus vient au
# clic sur une rangee (addAsset, note « verrouillée »), plus tard
# qu'openPicker qui refusait a l'ouverture. (4) A 1280 px avec inspecteur
# (300) + tiroir (340) + gouttieres, le lecteur garde ~370 px : accepte.
R_TT11 = ('                :trackKind(tr.id)==="adjust"\n'
          '                ?"Poser un clip d\'ajustement de 3 s à la tête de '
          'lecture — ses effets s\'appliquent à tout ce qui est dessous"\n'
          '                :trackKind(tr.id)==="title"\n'
          '                ?"Poser un carton de titre à la tête de lecture ("'
          '+svmKeyLabelNow("title_add")+") — la piste des titres ne reçoit '
          'aucun autre média"\n'
          '                :trackKind(tr.id)==="video"\n'
          '                ?"Ouvrir le tiroir Médias — un rendu vidéo à la tête '
          'de lecture (Maj+clic : lier une image par le sélecteur)"\n'
          '                :"Ajouter une image ou un rendu à la tête de '
          'lecture",\n'
          '              onClick:function(e){\n'
          '                if(trackKind(tr.id)==="subs"){subsAddHere();'
          'return}\n'
          '                if(trackKind(tr.id)==="adjust"){dzAjAdd();return}\n'
          '                if(trackKind(tr.id)==="title"){dzTtAdd();return}\n'
          '                if(trackKind(tr.id)==="video"&&!(e&&e.shiftKey)){'
          'if(proj.demo){fireNote("Ajout d\'assets : disponible sur un projet '
          'réel — la démo reste une maquette.");return}'
          'setMedTr(tr.id);setMedOn(!0);setSfxOn(!1);setSubsOn(!1);'
          'setNarrOn(!1);return}\n'
          '                openPicker(tr.id)},children:"+"},"add");')


# ── EA1 (E-3, 22/09/2026) : LA PORTE « ENVOYER VERS… » DE LA BIBLIOTHÈQUE
# VISE V1. La greffe S4 de libsend (AMONT, intouchable) est REMPLACÉE ici, à
# l'identique sauf le 5e argument de la branche vidéo : "v1" — addAsset
# (M16a) prend v1 si elle existe, sinon pickTrack ; sur une piste PLEIN
# CADRE, wantsTwin est vrai et le jumeau A1 est posé (M22a/M22b). Sur "v2"
# la vidéo arrivait MUETTE (incrustation, jamais sondée) et, sans piste v2,
# INVISIBLE (sauvegarde du 04/09). L'IMAGE reste une incrustation "v2".
# La couche porte la vieille phrase dans une prose datée du 06/09 (« vise
# "v2" EN DUR ») : le banc compte donc la forme CODE, queue `}catch` incluse.
A_EA1 = ('  x.useEffect(function(){var p=null;try{p=window.__dzMontageAdd;'
         'delete window.__dzMontageAdd}catch(_e){}'
         'if(!p)return;setTimeout(function(){try{if(p.image)'
         'addAsset({image:p.image},p.image,"image",0,"v2");'
         'else if(p.job_id)addAsset({job_id:p.job_id},p.title||p.job_id,'
         '"video",p.dur||0,"v2")}catch(_e2){}},450)},[]);'
         'function defaultLen(kind,srcDur){')
R_EA1 = A_EA1.replace('"video",p.dur||0,"v2")', '"video",p.dur||0,"v1")')
assert A_EA1 != R_EA1

# ── EA2 (E-3) : CHAPITRES — « Ouvrir dans le Montage » AVANT « Send to
# Scheduler ». Même boîte aux lettres que la Bibliothèque
# (`window.__dzMontageAdd`, consommée par EA1 au montage de l'écran), même
# navigation que le bouton voisin (CustomEvent deepotus:navigate — le seul
# mécanisme portable : `__dzSendNav` est enfermé dans le bloc libsend).
# `K` étale ses props (`...l`) : `title` passe. `epJob` et `title` sont les
# locales du composant (le bouton voisin les lit déjà). Le job `episode` ne
# stocke AUCUNE durée de scène : UN plan, pas un par scène (écart daté).
_EA_NAV = ('window.dispatchEvent(new CustomEvent("deepotus:navigate",'
           '{detail:{view:"montage"}}))')
# E-4 : Chapitres pose « cet épisode », Studio « ce rendu » (revue du 22/09).
_EA_TIP = ('title:"Poser %s sur la piste V1 du Montage, à la tête de '
           'lecture, avec son son",')
A_EA2 = ('r.jsx(K,{variant:"primary",size:"sm",icon:"calendar",'
         'onClick:sendEpisodeToScheduler,children:"Send to Scheduler"})')
R_EA2 = ('r.jsx(K,{variant:"outline",size:"sm",icon:"film",' + _EA_TIP % "cet épisode" +
         'onClick:function(){window.__dzMontageAdd={job_id:epJob,'
         'title:title||"Épisode"};' + _EA_NAV + '},'
         'children:"Ouvrir dans le Montage"}),' + A_EA2)

# ── EA3 (E-3) : STUDIO — même bouton dans la rangée du résultat (déjà
# flex/gap:8). `children:` y est un ÉLÉMENT unique : l'ancre court jusqu'à
# la FIN de l'expression (mesurée 1/1) et la rangée passe en tableau clé
# ("mont", "dl") ; l'<a> « Download » est repris tel quel. `n.title` n'est
# pas lu ailleurs dans ce bloc : repli « Rendu Studio ».
_EA3_A = ('r.jsx("a",{href:D.jobVideoUrl(n.id),download:!0,'
          'style:{flex:1,textDecoration:"none"},children:r.jsx(K,{'
          'variant:"outline",size:"sm",icon:"download",style:{width:"100%"},'
          'children:"Download"})}')
A_EA3 = ('r.jsx("div",{style:{marginTop:10,display:"flex",gap:8},children:'
         + _EA3_A + ')})')
R_EA3 = ('r.jsx("div",{style:{marginTop:10,display:"flex",gap:8},children:['
         'r.jsx(K,{variant:"outline",size:"sm",icon:"film",' + _EA_TIP % "ce rendu" +
         'onClick:function(){window.__dzMontageAdd={job_id:n.id,'
         'title:n.title||"Rendu Studio"};' + _EA_NAV + '},'
         'children:"Ouvrir dans le Montage"},"mont"),'
         + _EA3_A + ',"dl")]})')

# ── EA4 (E-4, 22/09/2026) : LE RENDU FINAL NE CRÉE PLUS RIEN DANS LE
# SCHEDULER. L'ancien `else` du poll (rendu « done », kind final) postait un
# brouillon sur /api/schedule puis NAVIGUAIT (`props.go("scheduler")`) sans
# rien demander. Il pose désormais l'état `dzFin` (REPLIÉ dans R_M16REF —
# son texte vaut 0 dans .bak_montage), que le bandeau de la couche consomme
# (EA5e). L'ancre est le bloc ENTIER, de `var run=` à la queue `})}}` : le
# remplacement rend les MÊMES accolades que l'ancre consomme (`)` de
# fireNote, `}` du else, `}` du `if(d.status==="done")`) — `node --check`
# tranche. `proj.project_id` est posé par R_M7 (`onNamed`) : "" si absent,
# le bandeau l'omet alors du payload (`||void 0`).
A_EA4 = ('            var run=new Date();run.setDate(run.getDate()+1);run.setHours(9,0,0,0);\n'
         '            fetch("/api/schedule",{method:"POST",headers:{"Content-Type":"application/json"},\n'
         '              body:JSON.stringify({title:proj.name,caption:proj.name+" \U0001F419",channels:["x","telegram"],\n'
         '                run_at:run.toISOString(),status:"draft",mode:"assisted",job_id:job.id})})\n'
         '              .then(function(res){return res.json()}).then(function(p2){\n'
         '                setJob(null);setPop("");setDirty(!1);\n'
         '                fireNote("Rendu final terminé — brouillon ajouté au Scheduler.");\n'
         '                if(p2&&p2.id){setTimeout(function(){\n'
         '                  window.dispatchEvent(new CustomEvent("deepotus:select-post",{detail:{id:p2.id}}))},400)}\n'
         '                props.go&&setTimeout(function(){props.go("scheduler")},900)})\n'
         '              .catch(function(){setJob(null);setPop("");\n'
         '                fireNote("Rendu terminé (Bibliothèque) — création du brouillon Scheduler impossible.")})}}')
# E-5 (lot E-B, tache 4, 23/09/2026) : le rendu FINAL écrit aussi le store du
# dernier rendu (repli, l'ancre est ce bloc) — setter FONCTIONNEL : la fermeture
# de l'intervalle ne lit pas un store périmé ; l'écriture localStorage est dans
# le setter, idempotente. La branche preview (setPreviewUrl) reste sans dzFin.
R_EA4 = ('            setJob(null);setPop("");setDirty(!1);\n'
         '            setDzFin({job_id:job.id,name:proj.name,project_id:proj.project_id||""});\n'
         '            setDzFinStore(function(s){var n=DzTracks.finStore(s,proj.project_id||"_",{job_id:job.id,name:proj.name,at:Date.now()});'
         'try{localStorage.setItem("dz_montage_lastfin",JSON.stringify(n))}catch(_e){}return n});\n'
         '            fireNote("Rendu final terminé — « Envoyer vers le Scheduler » pour le publier.")}}')
assert A_EA4.count("}") - A_EA4.count("{") == R_EA4.count("}") - R_EA4.count("{") == 2

# ── EA5a..EA5d (E-4) : LE POPOVER ET LA BARRE NE PROMETTENT PLUS DE
# PUBLICATION. Quatre littéraux, chacun sur une ligne unique (1/1 mesuré) ;
# le bouton d'action (EA5d-bis) porte aussi « Lancer l'aperçu » : seul le
# littéral change dans la ligne.
_EC15_DEMO = '"Rendu indisponible sur la démo — ouvre un projet réel"'
A_EA5A = '      r.jsx("div",{className:"svm-poptitle",children:isR?"Rendre & publier":"Preview 480p"}),'
R_EA5A = A_EA5A.replace('"Rendre & publier"', '"Rendre (master 1080)"')
A_EA5B = ('      isR?r.jsxs("div",{className:"svm-popline",children:[r.jsx("span",{children:"publication · brouillon Scheduler"}),'
          'r.jsx("span",{className:"svm-cost",children:"gratuit"})]}):null,')
R_EA5B = A_EA5B.replace('"publication · brouillon Scheduler"', '"publication · à la demande, après le rendu"')
A_EA5C = '          "Rendu local 1080 (aucun crédit consommé), puis brouillon dans le Scheduler — rien n\'est publié sans ta validation.":'
R_EA5C = ('          "Rendu local 1080 (aucun crédit consommé). À la fin, un bandeau propose l\'envoi vers le Scheduler '
          '— rien n\'est publié sans ta validation.":')
A_EA5D = '        r.jsx("button",{className:"svm-goldbtn",onClick:function(){setPop(pop==="render"?"":"render")},children:"Rendre & publier →"}),'
# E-5 (lot E-B, tache 4, 23/09/2026) : « Publier » SUIT le bouton or. MESURE :
# la ligne qui suit dans .bak_montage est le commentaire « tiroir Sons »,
# consommé par A_EB2 -> le bouton est un REPLI ici (le libellé « Rendre → »
# reste x1, pin E-4). Grisé avec infobulle quand le projet n'a aucun rendu
# final mémorisé ; sinon rouvre le bandeau sur ce rendu (project_id repris
# de proj : le store ne le porte pas) après avoir fermé le popover (EA5e :
# jamais les deux ouverts).
# E-12 (lot E-C, tache 6, 23/09/2026) : l'infobulle du bouton or, REPLI ici
# (ancre consommee par EA5d) — il OUVRE le panneau, il ne lance rien.
_EC15_OR = 'svm-goldbtn",title:"Rendu final (master 1080, local) — ouvre le panneau de rendu",onClick:'
R_EA5D = (A_EA5D.replace('"Rendre & publier →"', '"Rendre →"').replace('svm-goldbtn",onClick:', _EC15_OR) + '\n'
          '        /* E-5 : « Publier » = le dernier rendu FINAL de ce projet (mémoire par projet), sinon grisé */\n'
          '        r.jsx("button",{className:"svm-secbtn svm-pubbtn",disabled:!dzLast,'
          'title:dzLast?"Envoyer le dernier rendu final au Scheduler":"Aucun rendu final pour ce projet",\n'
          '          onClick:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}},'
          'children:"Publier"}),')
A_EA5D2 = '            children:busy?(job.progress+"%"):(isR?"Rendre & publier":"Lancer l\'aperçu")})]})]})}'
# L4 (23/09/2026, tache 4) : « Ajouter a la file » (D-36), REPLI ICI -- la rangee de
# boutons est l'hote consomme par EA5d2 (sa ligne est REECRITE). Le bouton est
# RENDU TOUJOURS (regle E-12 : un bouton d'outil se grise, ne disparait pas) :
# grise hors rendu final (la file ne prend que des finals -- le backend rend 400
# avec un apercu), pendant un rendu du meme type (busy) et sur la demo, chaque
# etat dit dans l'infobulle. launchRender(!1,!0) : final, en file (L4c/L4d).
R_EA5D2 = (A_EA5D2.replace('"Rendre & publier"', '"Rendre"').replace(')})]})]})}', ')}),\n'
           '          r.jsx("button",{className:"svm-secbtn svm-queuebtn",disabled:!isR||busy||proj.demo,'
           'title:proj.demo?' + _EC15_DEMO + ':!isR?"La file locale ne prend que des rendus finaux":busy?"Un rendu de ce type est déjà en cours":'
           '"Ajouter ce rendu final à la file locale (rendus en série, l\'écran reste libre)",'
           'onClick:function(){if(isR&&!busy)launchRender(!1,!0)},children:"Ajouter à la file"})]})]})}'))
assert R_EA5D2.count('"Ajouter à la file"') == 1 and R_EA5D2.count('la file"})]})]})}') == 1 and R_EA5D2.count(')})]})]})}') == 0 and R_EA5D2.count("title:") == 1
for _a, _r in ((A_EA5A, R_EA5A), (A_EA5B, R_EA5B), (A_EA5C, R_EA5C),
               (A_EA5D, R_EA5D), (A_EA5D2, R_EA5D2)):
    assert _a != _r

# ── EA5e (E-4) : LE BANDEAU DE FIN, monté à côté du popover dans la liste
# des couches flottantes (ancre = les deux lignes voisines `popover(),` /
# `fxPicker(),`, 1/1 — le plan la disait à huit espaces, la mesure en donne
# QUATRE). Les canaux cochés sont mémorisés (dz_montage_channels) AVANT
# l'envoi ; un refus HTTP remonte son `detail` au bandeau ; le post créé est
# présélectionné pour la prochaine visite du Scheduler (deepotus:select-post),
# SANS navigation forcée. Le bandeau et le popover ne sont jamais ouverts
# ensemble : `setPop("")` précède `setDzFin` (EA4).
A_EA5E = ('    popover(),\n'
          '    fxPicker(),')
R_EA5E = ('    popover(),\n'
          '    dzFin?r.jsx(DzTracks.FinBandeau,{fin:dzFin,memo:(function(){try{return JSON.parse(localStorage.getItem("dz_montage_channels")||"null")}catch(_e){return null}})(),\n'
          '      onSend:function(f){try{localStorage.setItem("dz_montage_channels",JSON.stringify(f.channels))}catch(_e){}\n'
          '        return fetch("/api/montage/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(f)})\n'
          '          .then(function(res){return res.ok?res.json():res.json().catch(function(){return null}).then(function(j){throw (j&&j.detail)||res.status})})\n'
          '          .then(function(d){var id=d&&d.post&&d.post.id;if(id)window.dispatchEvent(new CustomEvent("deepotus:select-post",{detail:{id:id}}))})},\n'
          '      onLib:function(){window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}))},\n'
          '      onClose:function(){setDzFin(null)}}):null,\n'
          '    fxPicker(),')

# ── EA6 (E-4, revue du 22/09/2026) : LE BANDEAU SE FERME AU LANCEMENT D'UN
# RENDU. Sans cela, un second rendu bandeau ouvert REUTILISAIT l'instance
# (monture sans `key`) : « Brouillon ajouté » restait affiché et le bouton
# désarmé pour le NOUVEAU job, heure/légende/cases périmées, et le popover
# s'ouvrait PAR-DESSUS (même `.svm-pop` absolu). Le passage par null
# remonte le composant à neuf au prochain `setDzFin` (EA4). Ancre : la
# garde de `launchRender`, 1/1 dans .bak_montage.
A_EA6 = 'if(proj.demo||(job&&job.status!=="failed"))return;'
R_EA6 = A_EA6 + 'setDzFin(null);'

# ══════════════════════════════════════════════════════════════════════════
# D-13 (22/09/2026, lot L3, tache 2) — LE ZOOM DYNAMIQUE COTE ECRAN
# ══════════════════════════════════════════════════════════════════════════
# Quatre ancres du bundle d'origine, toutes 1/1 dans .bak_montage et 0 dans
# ce patcher (mesurees le 22/09) : l'appel `ovInspector()` de l'aside, la
# derniere ligne du cadre `.svm-tf`, la ligne `lv._svmClip=c.id;` de
# liveSync, la ligne d'arrondi de la vitesse du payload. Le geste commun
# (`dzPlanSet`) et sa rafale d'historique sont REPLIES dans R_M16REF, a cote
# de `dzTracksRef` (ligne posee par ce remplacement, 0 dans .bak_montage).
#
# ECARTS MESURES AVEC LE PLAN :
#   - la tete de lecture de l'aside s'appelle `ph` (l'etat `st3`), pas `phc` ;
#   - `var dzPlanHist={t:0}` dans le corps du composant aurait ete RECREE a
#     chaque rendu (chaque `setClips` re-rend) : la rafale de 600 ms n'aurait
#     jamais tenu. C'est une ref (`x.useRef(0)`), comme `durRef` juste au-dessus ;
#   - le zoom en direct n'est PAS replie dans R_V3 : en tete de liveSync ni
#     le clip actif ni la <video> ne sont connus (ils sont calcules plus bas).
#     L'ancre `lv._svmClip=c.id;` est 1/1, et la, `lv`, `c` et `t` sont
#     exactement ceux du lecteur -- section propre DZ3 ;
#   - les rectangles vont DANS `.svm-tf` (position:absolute;inset:0 du cadre,
#     z-index:3, hors vzoom -- mesure de la feuille du bundle) et non apres :
#     pose apres, `.dzm-dzwrap` aurait ete recouvert par les hotes `.svm-live`
#     (transform => contexte d'empilement) et les % auraient ete ceux du cadre
#     de toute facon ; le cadre est mesure au pointerdown depuis le wrap.
A_DZ1 = "        ovInspector(),"
R_DZ1 = ('        /* D-13 : les proprietes de plan (clip V1 reel seulement) */\n'
         '        sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id?r.jsx(DzTracks.PlanProps,{clip:sel,\n'
         '          u:sel.end>sel.start?Math.max(0,Math.min(1,(ph-sel.start)/(sel.end-sel.start))):0,\n'
         # D-15 (L3 tache 4) : la vitesse et la tete pour l'interpolation et la
         # rampe -- PAS de nouvelle ancre, tout tient dans ce remplacement. La
         # rampe fend a la tete (DzTracks.rampe, meme regle que dzmCarve),
         # refuse la piste verrouillee comme svmSetV1Speed, UNE entree
         # d'historique, et selectionne la partie droite (setSelId, la forme
         # d'addAsset). Noms MESURES dans le .bak : fireNote (svmUseNote),
         # pushHistory(), setSelId, clipsRef/selRef.current, setDirty(!0).
         '          speed:svmSpeedOf(sel),head:ph,\n'
         '          onRampe:function(t,sL,sR){var tl=trackStRef.current.v1;if(tl&&tl.l){fireNote("Piste V1 verrouillée — division bloquée.");return}\n'
         '            var res=DzTracks.rampe(clipsRef.current,selRef.current,t,sL,sR);\n'
         '            if(res.refus){fireNote(res.refus==="bord"?"Trop près d\'un bord (0,3 s)":"Impossible de diviser ici");return}\n'
         '            pushHistory();setClips(res.clips);setSelId(res.right);setDirty(!0)},\n'
         # D-16 (L3 tache 6) : l'etat du job d'analyse de CETTE source (par
         # cle JSON de `src`, comme le cache backend est par source) et le
         # declencheur -- PAS d'ancre neuve, l'etat et le geste sont replies
         # dans R_M16REF (dzStabJobs / dzStabStart).
         # revue : la cle est CANONIQUE (`srcKey`, cles triees -- la regle
         # tranchee pour dzmTwinClip), jamais un JSON.stringify a l ordre pres.
         '          stabJob:dzStabJobs[DzTracks.srcKey(sel.src)]||null,onStab:function(){dzStabStart(sel.src)},\n'
         # L7-B D-40 (24/09/2026, tache 4) : LE CADRAGE -- repli ici, AUCUNE ancre
         # neuve (DZ1 finit comme avant). `srcWH` = dimensions de la source lues sur
         # l'element du lecteur vivant de CETTE source, SANS le creer (Map.get du pool,
         # role "b" -- la forme de svmOvMediaHW) : [0,0] si le pool ne l'a pas ou si
         # les metadonnees ne sont pas lues (la couche dit alors « pas encore lues »,
         # rien n'est grise). `ratio` = svmRatioW(proj.ratio), le ratio du cadre.
         # `onReframe` : POST /api/montage/reframe {src, srcIn, dur = (end-start) x
         # vitesse, duree de SOURCE}, note PENDANT l'analyse ; a la reponse, la garde
         # d'obsolescence de dzSceneCut (8517a25) : l'empreinte (srcIn, vitesse,
         # start, end) du plan ENVOYE doit etre celle du plan A LA REPONSE, sinon
         # refus dit sans ecriture ; plan supprime ou V1 verrouillee -> refus dit.
         # L'ecriture vise le clip `id` (jamais selRef : la selection a pu changer),
         # pushHistory() PUIS setClips ; un resultat `centre` du tracker retire le
         # champ et le dit (« Peu de mouvement : centré. »). Rend la promesse (la
         # couche desactive le bouton jusqu'a sa fin). AUCUN DzTracks ici.
         # REVUE du 24/09/2026 : (1) l'empreinte porte aussi l'IDENTITE de la source
         # (svmSrcKey du bundle, portee module, .bak x1 : j:/a:/i: -- la forme sans
         # DzTracks, sonde inchangee) : « Remplacer la source » garde l'id et souvent
         # srcIn/start/end, les points de l'ANCIENNE source auraient ete ecrits ; (2)
         # le MODE du cadrage aussi (la couche gele les modes pendant l'analyse, un
         # annuler pourrait encore le changer) ; (3) srcWH lit naturalWidth/Height
         # d'une image du pool (plan image sur V1 -- l'hote ne monte que sur un rendu
         # video aujourd'hui, date dans la couche).
         '          ratio:svmRatioW(proj.ratio),srcWH:(function(){var pl=livePoolRef.current,it=pl&&pl.get(livePoolKey(sel.src,"b"));\n'
         '            return it?[it.el.videoWidth||it.el.naturalWidth||0,it.el.videoHeight||it.el.naturalHeight||0]:[0,0]})(),\n'
         '          onReframe:function(){var id=sel.id,c=clipsRef.current.find(function(k){return k.id===id});\n'
         '            if(!c||!c.src||!c.src.job_id){fireNote("Analyse du mouvement : réservée aux clips vidéo rendus.");return Promise.resolve()}\n'
         '            function dzRfSg(k){return [Number(k.srcIn)||0,svmSpeedOf(k),Number(k.start)||0,Number(k.end)||0,svmSrcKey(k.src),\n'
         '              k.reframe&&typeof k.reframe==="object"?String(k.reframe.mode):""].join("|")}\n'
         '            var sg=dzRfSg(c),du=Math.round(Math.max(0,(c.end-c.start)*svmSpeedOf(c))*1e3)/1e3;\n'
         '            if(!(du>0)){fireNote("Analyse du mouvement refusée : plan de durée nulle.");return Promise.resolve()}\n'
         '            fireNote("Analyse du mouvement…");\n'
         '            return fetch("/api/montage/reframe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:c.src,srcIn:Number(c.srcIn)||0,dur:du})})\n'
         '              .then(function(res){return res.json().catch(function(){return {}}).then(function(j){\n'
         '                if(!res.ok)throw new Error((j&&typeof j.detail==="string"&&j.detail)||("HTTP "+res.status));return j})})\n'
         '              .then(function(j){var k2=clipsRef.current.find(function(k){return k.id===id});\n'
         '                if(!k2){fireNote("Analyse du mouvement : le plan a disparu — rien n\'est écrit.");return}\n'
         '                if(dzRfSg(k2)!==sg){fireNote("Analyse du mouvement refusée : le plan a changé pendant l\'analyse — relancez.");return}\n'
         '                var tl=trackStRef.current.v1;if(tl&&tl.l){fireNote("Piste V1 verrouillée — cadrage non écrit.");return}\n'
         # revue finale du lot (24/09/2026) : les points du CHAMP sont en temps ABSOLU de source -- la reponse
         # (relative au srcIn ENVOYE, qui est aussi celui du plan : l'empreinte l'a verifie) est decalee ici.
         '                var si=Number(c.srcIn)||0,pts=(j&&j.mode==="suivi"&&Array.isArray(j.points)?j.points:[])\n'
         '                  .map(function(q){return {t:Math.round((si+Number(q.t))*1e3)/1e3,x:q.x}});\n'
         '                pushHistory();setClips(clipsRef.current.map(function(k){if(k.id!==id)return k;var nk=Object.assign({},k);\n'
         '                  if(pts.length)nk.reframe={mode:"suivi",points:pts};else delete nk.reframe;return nk}));setDirty(!0);\n'
         '                fireNote(pts.length?"Mouvement suivi : "+pts.length+" points.":"Peu de mouvement : centré.")})\n'
         '              .catch(function(e){fireNote("Analyse du mouvement refusée : "+((e&&e.message)||"erreur réseau"))})},\n'
         '          onChange:dzPlanSet}):null,\n'
         + A_DZ1 + "\n"
         # L5 D-27 D-29 D-30 D-28 (24/09/2026, tache 5) : LE PANNEAU « ETALONNAGE » -- repli ici, AUCUNE ancre neuve.
         # MEME garde que PlanProps (clip V1 rendu), monte UNE fois, APRES ovInspector() (le rack d'effets, que le
         # panneau ecrit, reste au-dessus ; le pin d'adjacence `onChange:dzPlanSet}):null,` + `ovInspector(),` de DZ1
         # ne bouge pas -- ecart date au plan, qui disait « a cote de PlanProps »). `clips` = la timeline (le plan
         # precedent de l'accord), `ph` = la tete, `locked` = la forme de dzPlanSet (V1 verrouillee : la couche grise
         # et le dit, le geste commun refuserait de toute facon), onChange = dzPlanSet (rafale de 600 ms), notes par
         # fireNote. Le reseau (grade-frame, color-match) est dans la COUCHE : l'hote ne porte aucune route.
         '        /* L5 : le panneau Etalonnage (clip V1 reel seulement, meme garde que les proprietes de plan) */\n'
         '        sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id?r.jsx(DzTracks.GradePanel,{clip:sel,\n'
         # revue T5 (24/09/2026, I-3) : `playing` (l'etat de lecture de DzMontage, celui que recoivent les scopes) --
         # pendant la lecture le panneau ne construit ni ne serialise le corps de l'apercu, aucun minuteur
         '          clips:clips,head:ph,playing:playing,locked:!!(trackStRef.current.v1&&trackStRef.current.v1.l),onNote:fireNote,onChange:dzPlanSet}):null,')
A_DZ2 = '            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef})]}):null,'
R_DZ2 = ('            r.jsx("div",{className:"svm-tfbadge",ref:tfBadgeRef}),\n'
         # L5 D-30 (24/09/2026, tache 5) : LE CONTOUR DU MASQUE du clip V1 selectionne -- repli ici (le plan proposait
         # R_L7BRF1 ou une section L5m1 en queue : `.svm-tf` est DEJA le cadre en %, hors vzoom, au-dessus des hotes --
         # mesure de D-13 -- et le masque est en fractions du cadre ; liveSync aurait du creer l'element a la main).
         # Pose AVANT les rectangles du zoom (ils restent dessus, eux sont saisissables ; la boite ne l'est pas).
         '            /* L5 D-30 : le contour du masque du clip V1 selectionne (sous les rectangles du zoom) */\n'
         '            sel&&sel.tr==="v1"&&sel.mask?r.jsx(DzTracks.MaskBox,{clip:sel}):null,\n'
         '            /* D-13 : les deux fenetres du zoom dynamique du clip V1 selectionne */\n'
         '            sel&&sel.tr==="v1"&&sel.dz?r.jsx(DzTracks.DzRects,{dz:sel.dz,\n'
         '              onChange:function(nd){dzPlanSet({dz:nd})}}):null]}):null,')
A_DZ3 = "      lv._svmClip=c.id;"
R_DZ3 = (A_DZ3 + "\n"
         "      /* D-13 : le zoom dynamique EN DIRECT -- meme geometrie que le zoompan\n"
         "         du rendu, sur la <video> active ; ecrit seulement s'il change --\n"
         "         l'origine 0 0 est posee par la feuille (.svm-live>.svm-livemedia) */\n"
         '      var dzT=DzTracks.dzCss(c.dz,(t-c.start)/Math.max(.04,c.end-c.start));\n'
         '      if(lv.style.transform!==dzT)lv.style.transform=dzT;')
A_DZ4 = "           Math.abs(c.speed-1)>1e-6)o.speed=Math.round(c.speed*100)/100;"
R_DZ4 = (A_DZ4 + "\n"
         "        /* D-13 : le zoom dynamique -- joint seulement s'il existe (payload d'avant sinon) */\n"
         '        var dzD=c.tr==="v1"&&DzTracks.dzOf(c);if(dzD)o.dz=dzD;\n'
         # D-15 (L3 tache 4) : l'interpolation ne vaut qu'AVEC une vitesse
         # (`o.speed` n'est pose que sur un V1 reel a vitesse != 1, ligne
         # d'ancre) -- payload d'avant octet pour octet sinon.
         "        /* D-15 : l'interpolation du retime -- jointe seulement avec une vitesse */\n"
         '        var rtD=o.speed&&DzTracks.retimeOf(c);if(rtD)o.retime=rtD;\n'
         # D-16 (L3 tache 6) : la stabilisation, jointe seulement si elle
         # existe (normalisee par la couche, UNE occurrence de `stabOf(` via
         # `sbD` -- la sonde compte chaque jeton) ; payload d'avant sinon.
         "        /* D-16 : la stabilisation -- jointe seulement si elle existe */\n"
         '        var sbD=c.tr==="v1"&&DzTracks.stabOf(c);if(sbD)o.stab=sbD;\n'
         # L7-B D-40 (24/09/2026, tache 4) : le cadrage, joint seulement HORS centre
         # (la couche rend null pour centre / illisible : payload d'avant sinon ; les
         # points gardes en mode centre ou manuel ne partent pas).
         "        /* L7-B D-40 : le cadrage -- joint seulement hors centre */\n"
         # revue finale : le payload porte les points ABSOLUS (reframePayload) -- le serveur applique la meme
         # regle que la couche (srcIn courant soustrait, fenetre, points de bord).
         '        var rfD=c.tr==="v1"&&DzTracks.reframePayload(c);if(rfD)o.reframe=rfD;\n'
         # L5 D-30 (24/09/2026, tache 5) : LE MASQUE -- joint seulement s'il est lisible ET qu'un effet actif part
         # (o.effects, deja filtre des `off` plus haut : sans effet le rendu l'ignore -> payload d'avant). MESURE
         # 24/09 : la MEME map de renderPayload construit les clips V1 ET les overlays V2 (le bloc
         # isOverlayTrack vient plus bas dans la meme fonction) -- UNE ligne couvre les deux ; `trackKind` (bundle)
         # dit « video » pour v1, v2, v3… et jamais pour a*, s*, t*, j* ; un clip sans source (titre) ne l'emporte pas.
         "        /* L5 D-30 : le masque (V1 et overlays V2) -- joint seulement lisible et avec des effets actifs */\n"
         '        var mkD=o.effects&&c.src&&trackKind(c.tr)==="video"&&DzTracks.maskOf(c.mask);if(mkD)o.mask=mkD;')

# ══ D-14 (L3 tache 7, 22/09/2026) — KEYFRAMES D'ECHELLE ET D'OPACITE ═══════
# Le contrat du rendu (T7a) : `motion_points[{t,x,y,rotate?,scale?,opacity?}]`,
# un point sans la cle ne participe pas a cette animation, sans porteur la
# statique reste. MESURE dans le .bak (toutes 1/1, 0 dans ce patcher) :
#   KF1  svmOvTfAt fige `scale:base.scale` — devient la lerp sur les porteurs
#        (defaut : la statique). Le lecteur vivant, le cadre de selection et
#        l'inspecteur lisent svmOvTfAt : l'echelle en direct vient de la.
#   KF2  svmMpApply aligne les statiques x/y/rotate sur un point UNIQUE
#        (invariant d'honnetete : il ne part pas au rendu) — scale/opacity
#        suivent la meme regle, sinon lecteur (lerp) et rendu (statique)
#        divergeraient a un point. LE PLAN visait ici « garder scale/opacity
#        des points » : `res.pts` recopie deja les points non touches
#        (pts.slice()) — ce qui les PERDAIT est svmMpPlace (KF2b).
#   KF2b svmMpPlace construit un point NEUF {t,x,y,rotate} : le patch
#        {scale:v} de svmMpField et les cles du point ecrase tombaient.
#        DzTracks.mpKeep les reporte (patch, sinon point ecrase, bornes).
#   KF3a le champ Echelle : avec une trajectoire, il ecrit le point le plus
#        proche de la tete (svmMpField, comme Rotation) ; l'infobulle « ne se
#        keyframe pas » devient celle des autres champs (kfTT).
#   KF3b vOp lit l'opacite interpolee a la tete quand une trajectoire existe.
#   KF3c le curseur Opacite ecrit le point (svmMpField porte son historique).
#   KF4  le payload joint q.scale (0,001) / q.opacity (0,01) quand presents.
#        Le plan disait ce bloc CONSOMME par M25c : M25c ne consomme que sa
#        premiere ligne `if(c.tr==="v2"){` ; la ligne `q.rotate=` est libre.
#   KF5  liveSync : l'opacite appliquee a l'overlay vivant est interpolee
#        (`t` global, `k` le clip — noms mesures) ; hors R_V3 (mesure 0).
#   KF2c (revue) svmMpRemove : quand il reste UN point, il alignait x/y/rotate
#        seulement — scale/opacity suivent, meme convention que KF2.
# ECART DATE (22/09/2026) : quatre commentaires du bundle disent encore que
# l'echelle ne se keyframe pas (svmOvTfAt, payload, section Trajectoire,
# svmMpRemove) : perimes, non touches, KF1/KF4 font foi.
A_KF1 = "          scale:base.scale,"
R_KF1 = '          scale:DzTracks.mpLerp2(mp,tl,"scale",base.scale),'
A_KF2 = "        x:one?one.x:t.x,y:one?one.y:t.y,scale:t.scale,"
R_KF2 = ("        x:one?one.x:t.x,y:one?one.y:t.y,scale:one&&one.scale!=null?one.scale:t.scale,\n"
         "        opacity:one&&one.opacity!=null?(one.opacity>=1?void 0:one.opacity):k.opacity,")
A_KF2B = "      rotate:Math.min(180,Math.max(-180,Math.round((Number(vals.rotate)||0)*10)/10))};"
R_KF2B = (A_KF2B + "\n"
          "    /* D-14 : scale/opacity du patch, sinon du point écrasé (bornes du backend) */\n"
          "    DzTracks.mpKeep(np,vals,bi>=0?pts[bi]:null);")
A_KF2C = "      if(np.length===1){nk.x=np[0].x;nk.y=np[0].y;nk.rotate=np[0].rotate}"
R_KF2C = ("      if(np.length===1){nk.x=np[0].x;nk.y=np[0].y;nk.rotate=np[0].rotate;"
          "if(np[0].scale!=null)nk.scale=np[0].scale;"
          "if(np[0].opacity!=null)nk.opacity=np[0].opacity>=1?void 0:np[0].opacity}")
A_KF3A = ('          title:"Largeur de l\'overlay en % de celle du canvas (100 = pleine largeur)"+\n'
          '            (mp?" — l\'échelle ne se keyframe pas : valeur unique pour toute la durée":""),\n'
          '          "aria-label":"Échelle (%)",\n'
          '          onChange:function(e){var v=Number(e.target.value);\n'
          '            if(isFinite(v)&&v>0)svmOvTfField({scale:Math.min(3,Math.max(.05,v/100))})}}),')
R_KF3A = ('          title:"Largeur de l\'overlay en % de celle du canvas (100 = pleine largeur)"+kfTT,\n'
          '          "aria-label":"Échelle (%)",\n'
          '          onChange:function(e){var v=Number(e.target.value);\n'
          '            if(!isFinite(v)||v<=0)return;v=Math.min(3,Math.max(.05,v/100));\n'
          '            if(mp)svmMpField(sel,{scale:v});else svmOvTfField({scale:v})}}),')
A_KF3B = "    var vOp=Math.round((sel.opacity==null?1:sel.opacity)*100);"
R_KF3B = ('    var vOp=Math.round((mp?DzTracks.mpLerp2(mp,phc-sel.start,"opacity",sel.opacity==null?1:sel.opacity)'
          ':(sel.opacity==null?1:sel.opacity))*100);')
A_KF3C = ('          title:"Opacité de l\'overlay ("+vOp+" %)","aria-label":"Opacité de l\'overlay",\n'
          '          onChange:function(e){var nv=Number(e.target.value)/100;var id=selRef.current;')
R_KF3C = ('          title:"Opacité de l\'overlay ("+vOp+" %)"+kfTT,"aria-label":"Opacité de l\'overlay",\n'
          '          onChange:function(e){var nv=Number(e.target.value)/100;var id=selRef.current;\n'
          '            if(mp){svmMpField(sel,{opacity:nv});return}')
A_KF4 = "                q.rotate=Math.round(Number(p.rotate)*10)/10;"
R_KF4 = (A_KF4 + "\n"
         "              /* D-14 : échelle / opacité par point — jointes seulement si présentes */\n"
         "              if(p.scale!=null&&isFinite(Number(p.scale)))q.scale=Math.round(Number(p.scale)*1000)/1000;\n"
         "              if(p.opacity!=null&&isFinite(Number(p.opacity)))q.opacity=Math.round(Number(p.opacity)*100)/100;")
# ── AJ2 (D-9, 22/09/2026) : LE RACK VFX SUR UN CLIP SANS SOURCE ───────────
# La garde du rack exigeait `sel.src` ET une piste video : un clip
# d'ajustement n'a pas de source, il est accepte par son GENRE. Le lecteur
# vivant ne joue pas ses effets (aucun clip sans `src` n'y entre : mesure,
# svmActiveV1 et liveSync exigent `c.src`) -- le rack le DIT, par un
# SvmLabel au-dessus de la pile (le Stack n'a pas de zone de note : mesure).
# AJ2a ouvre le Fragment, AJ2b le referme sur la ligne qui rend la section
# historique (1/1 dans .bak_montage, patcher 0 -- PAS `vfxStackSection`,
# bak 2 / patcher 3).
A_AJ2A = ('    if(d&&d.Stack&&sel&&sel.src&&trackKind(sel.tr)==="video")\n'
          '      return r.jsx(d.Stack,{effects:sel.effects||[],clip:sel,')
R_AJ2A = ('    if(d&&d.Stack&&sel&&((sel.src&&trackKind(sel.tr)==="video")||sel.kind==="adjust"))\n'
          '      return r.jsxs(r.Fragment,{children:[sel.kind==="adjust"?r.jsx(SvmLabel,'
          '{style:{margin:"20px 0 10px"},children:"Ajustement — ses effets s\'appliquent '
          'à tout ce qui est dessous, visibles après Preview"}):null,\n'
          '      r.jsx(d.Stack,{effects:sel.effects||[],clip:sel,')
A_AJ2B = ('          setDirty(!0)}});\n'
          '    return vfxLegacySection()}')
R_AJ2B = ('          setDirty(!0)}})]});\n'
          '    return vfxLegacySection()}')

# ── AJ6 (D-9) : LE CLIP D'AJUSTEMENT SE LIT SUR LA TIMELINE ────────────────
# `data-kind` sur chaque clip (undefined = attribut absent, comme data-narr),
# et les HACHURES : celles du fantome de narration, dans le `style` inline
# (un style inline gagne sur la feuille ; poser le meme gradient en CSS
# aurait exige `!important` -- mesure : `background:` est inline). Aucune
# ligne de montage.css.
A_AJ6A = '                    "data-media":media&&tr.id==="v1"?"":void 0,'
R_AJ6A = (A_AJ6A + '\n'
          '                    "data-kind":c.kind||void 0,\n'
          # L7 D-8 (24/09/2026, tache 3) : L7c1 REPLIE ici (l'ancre `"data-kind"` du plan est nee de CE
          # remplacement, x0 dans .bak_montage). La carte boMap n'a d'entrees que pour V1 : undefined =
          # attribut absent ailleurs, comme data-kind ; montage.css dessine le lisere.
          '                    "data-boring":boMap[c.id]||void 0,')
A_AJ6B = ('background:isPh?"repeating-linear-gradient(-45deg,transparent 0 5px, '
          'color-mix(in srgb, var("+tr.c+") 26%, transparent) 5px 6px)":')
R_AJ6B = ('background:isPh||c.kind==="adjust"?"repeating-linear-gradient(-45deg,transparent 0 5px, '
          'color-mix(in srgb, var("+tr.c+") 26%, transparent) 5px 6px)":')

# ── AJ7 (D-9, revue 23/09/2026) : LA POSE D'UN EFFET ATTEINT LE CLIP
# D'AJUSTEMENT. MESURE (preuve ecran Playwright) : « Vignette » sur j1u1
# laissait `effects []` -- `vfxAddTo` (V5 du patcher vfxrack, amont, 1/1
# dans .bak_montage) refusait un clip SANS `src` puis une piste qui n'est
# pas « video ». Les deux gardes restent ENTIERES pour tout autre clip
# (V1 en temoin) ; l'ajustement passe par son GENRE, comme au rack (AJ2).
A_AJ7 = ('    if(!c.src){fireNote("Effets par clip : disponibles sur les clips '
         'réels (Bibliothèque) — la démo reste une maquette.");return !1}\n'
         '    if(trackKind(c.tr)!=="video"){fireNote("Un effet vidéo se pose '
         'sur un clip V1 ou V2.");return !1}')
R_AJ7 = ('    if(c.kind!=="adjust"&&!c.src){fireNote("Effets par clip : disponibles sur les clips '
         'réels (Bibliothèque) — la démo reste une maquette.");return !1}\n'
         '    if(c.kind!=="adjust"&&trackKind(c.tr)!=="video"){fireNote("Un effet vidéo se pose '
         'sur un clip V1 ou V2.");return !1}')

A_KF5 = '      el.style.opacity=k.opacity==null?"":String(k.opacity);'
R_KF5 = ('      /* D-14 : opacité interpolée sur les points porteurs (statique sinon) */\n'
         '      var kOp=DzTracks.mpLerp2(svmMpOf(k)||[],t-k.start,"opacity",k.opacity==null?1:k.opacity);\n'
         '      el.style.opacity=kOp>=1?"":String(Math.round(kOp*100)/100);')

# ── EB1 (E-2, lot E-B tache 3, 23/09/2026) : L'ETAT DU TIROIR MEDIAS ────────
# `medOn` (ouvert) et `medTr` ("" = ouvert par la chip de la barre, sinon
# l'id de la piste video dont le « + » l'a ouvert : le tiroir vise cette
# piste, `onAdd` la passe a addAsset). Poses DEVANT `stO` (ovPick), qui est
# l'etat du selecteur historique : les deux se lisent cote a cote. MESURE :
# `medOn`, `medTr`, `stMed`, `stMT` sont libres dans .bak_montage (0).
A_EB1 = '  var stO=x.useState(""),ovPick=stO[0],setOvPick=stO[1];'
R_EB1 = ('  var stMed=x.useState(!1),medOn=stMed[0],setMedOn=stMed[1]; '
         '/* E-2 : tiroir Médias (rendus vidéo) ouvert */\n'
         '  var stMT=x.useState(""),medTr=stMT[0],setMedTr=stMT[1]; '
         '/* "" = ouvert par la chip, sinon la piste vidéo dont le « + » a '
         'ouvert le tiroir */\n'
         + A_EB1)

# ── EB2 (E-2) : LA CHIP « médias » DE LA BARRE DE TITRE, DEVANT « sons » ──
# REVUE 23/09/2026 : LA DEMO. `openPicker` refusait la demo (« la demo reste
# une maquette ») et `addAsset` n'a AUCUNE garde `proj.demo` -- l'invariant
# du bundle (:1828) dit que ses appelants sont tous gardes. La chip et le
# « + » video (R_TT11) ouvraient le tiroir sans regarder `proj.demo` : un
# clic sur une rangee aurait pose un clip dans la maquette. Les DEUX
# handlers portent la MEME garde, MEME phrase qu'openPicker (comptee).
# (E-7, 23/09/2026) `_EB_GARDE` est definie PLUS HAUT, avant A_M16REF : R_M16REF la
# reprend pour dzSetView(« medias ») -- la meme phrase, comptee par le banc.
# Meme famille que « sons » et « narration » (svm-themechip, data-on,
# aria-pressed). Ouvrir le tiroir Medias FERME les trois autres tiroirs de
# .svm-mid (sons, sous-titres, narration) : ils sont EXCLUSIFS (mesure
# .bak:5000-5007, un seul emplacement a gauche du lecteur). `setMedTr("")` :
# depuis la barre, aucune piste n'est visee (addAsset prendra "v1", comme la
# porte E-3). L'ancre est le commentaire + la premiere ligne de la chip
# « sons » (1 dans .bak) ; le remplacement la REPREND.
# ── EB6c (E-8, lot E-B tache 6, 23/09/2026) : LA CHIP « inspecteur » ─────
# REPLI dans R_EB2 : l'ancre naturelle (le chip « sons ») est CONSOMMEE par
# EB2 (elle vaut 0 apres EB2, une section a part passerait `--check` puis
# abandonnerait au rejeu -- meme mesure que TT9b dans R_M13). Meme famille
# que « médias » (svm-themechip, data-on, aria-pressed). Le clic bascule
# `on` et GARDE `w` (setter fonctionnel : la fermeture ne lit pas un etat
# perime), puis persiste dans try/catch (cle dz_svm_insp, prefixe dz_).
# Elle ne parle pas a la couche : la sonde de dzcout ne bouge pas ici.
_EB6_CHIP = ('        /* E-8 : l\'inspecteur a bascule — REPLI dans R_EB2 (l\'ancre de « sons » est\n           consommee par EB2) ; la poignee et la memoire vivent dans EB6a/EB6b */\n        r.jsx("button",{className:"svm-themechip svm-inspchip","data-on":inspOn?"":void 0,\n          "aria-pressed":inspOn,\n          title:"Inspecteur — replier ou rouvrir la colonne de droite (le lecteur prend la place)",\n          onClick:function(){setInspSt(function(s){var n={on:!s.on,w:s.w};try{localStorage.setItem("dz_svm_insp",JSON.stringify(n))}catch(_e){}return n})},children:"inspecteur"}),\n')

# ── EB7c (E-9, lot E-B tache 7, 23/09/2026) : LA CHIP « durées » — REPLI
# dans R_EB2 apres « inspecteur » (meme raison qu'EB6c : l'ancre de « sons »
# est consommee par EB2). Bascule showDur par setter fonctionnel et persiste
# "1"/"0" dans dz_svm_showdur (try/catch). Elle ne parle pas a la couche :
# c'est le repli R_M16D (le label du clip) qui appelle durLbl.
_EB7_CHIP = ('        /* E-9 : durées sur les clips — REPLI dans R_EB2 (même ancre consommée qu\'E-8) */\n'
             '        r.jsx("button",{className:"svm-themechip svm-durchip","data-on":showDur?"":void 0,\n'
             '          "aria-pressed":showDur,\n'
             '          title:"Durées — afficher la durée de chaque clip à côté de son nom",\n'
             '          onClick:function(){setShowDur(function(v){var n=!v;try{localStorage.setItem("dz_svm_showdur",n?"1":"0")}catch(_e){}return n})},children:"durées"}),\n')

A_EB2 = ('        /* tiroir Sons (DzSfx) — chip jumelle de « narration », les deux '
         'tiroirs\n'
         '           sont exclusifs ; sans la couche DzSfx la chip n\'existe pas */\n'
         '        svmSfx()?r.jsx("button",{className:"svm-themechip svm-sfxchip",'
         '"data-on":sfxOn?"":void 0,')
R_EB2 = ('        /* E-2 : tiroir Médias — les rendus vidéo terminés, paginés, avec '
         'chips de\n'
         '           provenance ; quatrième tiroir de .svm-mid, exclusif avec les '
         'trois autres */\n'
         '        r.jsx("button",{className:"svm-themechip svm-medchip",'
         '"data-on":medOn?"":void 0,\n'
         '          "aria-pressed":medOn,\n'
         '          title:"Tiroir Médias — vos rendus vidéo terminés, à glisser '
         'ou à cliquer vers une piste vidéo",\n'
         '          onClick:function(){' + _EB_GARDE + 'setMedTr("");setMedOn(!medOn);setSfxOn(!1);'
         'setSubsOn(!1);setNarrOn(!1)},children:"médias"}),\n'
         + _EB6_CHIP
         + _EB7_CHIP
         + A_EB2)

# ── EB2b..EB2f (E-2) : LES CINQ PORTES DES AUTRES TIROIRS FERMENT MEDIAS ──
# MESURE (.bak_montage) : les exclusions sfx/subs/narr s'ecrivent a CINQ
# endroits, tous libres dans le patcher (0) et uniques dans .bak (1) :
#   :1772-1774 sfxToggle   (`setNarrOn(!1)},[]);` -- ferme narration)
#   :1841-1847 narrToggle  (`setSfxOn(!1)},[]);`  -- ferme sons)
#   :3576 subsAddHere      (`setSelId(s.id);setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);`)
#   :3579 subsToggle       (`setSubsOn(function(v){return !v});...`)
#   :3713 bouton « éditeur » du panneau S1 (`onClick:function(){setSubsOn(!0);...`)
# Chacune recoit `setMedOn(!1)`. `setSubsOn(!0)` n'a que DEUX occurrences
# (3576, 3713) ; le raccourci « sounds_drawer » (:2958) et « narration »
# (:3003) passent par sfxToggle / narrToggle : couverts. `setMedOn` est un
# setter React (stable) : l'appeler dans un useCallback a deps [] est sur.
A_EB2B = '    setNarrOn(!1)},[]);'
R_EB2B = '    setNarrOn(!1);setMedOn(!1)},[]);'
A_EB2C = '    setSfxOn(!1)},[]);'
R_EB2C = '    setSfxOn(!1);setMedOn(!1)},[]);'
A_EB2D = '    setSelId(s.id);setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);'
R_EB2D = '    setSelId(s.id);setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);setMedOn(!1);'
A_EB2E = '    setSubsOn(function(v){return !v});setSfxOn(!1);setNarrOn(!1)}'
R_EB2E = '    setSubsOn(function(v){return !v});setSfxOn(!1);setNarrOn(!1);setMedOn(!1)}'
A_EB2F = '          onClick:function(){setSubsOn(!0);setSfxOn(!1);setNarrOn(!1)},'
R_EB2F = '          onClick:function(){setSubsOn(!0);setSfxOn(!1);setNarrOn(!1);setMedOn(!1)},'

# ── EB3 (E-2) : LE TIROIR MONTE DANS .svm-mid, APRES NARRATION ──────────────
# Le composant vit dans la couche (T2, `MediaDrawer`, hooks toujours
# appeles) : l'hote le monte EN PERMANENCE et bascule `open`. `onAdd` pose
# le job a la TETE DE LECTURE avec le jumeau A1, EXACTEMENT comme la porte
# E-3 (R_EA1, `__dzMontageAdd`) : `addAsset({job_id},titre||job_id,"video",
# duree||0,"v1")`, SANS sixieme argument (`atTime==null` -> phRef, mesure
# .bak:3752-3756) ; sur "v1" (plein cadre) `wantsTwin` est vrai et l'audio
# jumeau est pose (M22a/M22b). Quand le tiroir a ete ouvert par le « + »
# d'une piste, `medTr` la remplace ("v2" -> incrustation, sans jumeau).
# ECART DATE au plan (23/09/2026) : pas de `pickTrack(tracks,"video")` ici
# -- addAsset (R_M16A) resout DEJA une piste absente par pickTrack, et la
# porte E-3 passe "v1" pour obtenir le jumeau ; un second pickTrack dans
# l'hote serait une deuxieme ecriture du meme choix. La sonde de dzcout ne
# monte donc que de UN (le composant). `exts:null` : le serveur juge
# l'extension (`video=1`, T1), la couche juge le statut (T2).
A_EB3 = ('      subsPanel(),\n'
         '      narrPanel(),')
R_EB3 = (A_EB3 + '\n'
         '      /* E-2 : tiroir Médias (rendus vidéo) — même emplacement, exclusif */\n'
         '      r.jsx(DzTracks.MediaDrawer,{open:medOn,trId:medTr,exts:null,'
         'onClose:function(){setMedOn(!1)},dragPayload:dragPayload,\n'
         '        onAdd:function(j){addAsset({job_id:j.job_id},j.title||j.job_id,'
         '"video",j.duration_s||0,medTr||"v1")},\n'
         # L7-B D-41 (24/09/2026, tache 6) : REPLI -- le popover des auto-clips (couche) demande l'ouverture du
         # projet qu'il vient de creer ; l'hote incremente le compteur que M14 passe a la liste des projets
         '        /* L7-B D-41 : le projet créé par les auto-clips est ouvert par la liste des projets (compteur) */\n'
         '        onOpenProject:function(p){setDzAcOpen(function(v){return {n:((v&&v.n)||0)+1,'
         'id:p&&p.id,name:p&&p.name}})}}),')

# ── EB4 (E-5, lot E-B tache 4, 23/09/2026) : LA BARRE DIT « Preview » ──────
# Le bouton garde son handler (setPop preview) ; seul le libellé change,
# « Preview · Rendre · Publier » comme Resolve (E-5). MESURE : la ligne est
# libre (1 dans .bak, 0 dans le patcher) ; « Preview 480p (gratuit) » survit
# UNE fois dans le livré, l'infobulle de la chip 480p du lecteur (:5093),
# qui n'est pas la barre. « Rendre » = EA5d ; « Publier » = repli R_EA5D.
# MESURE (banc, 23/09) : `children:"Preview"}),` seul vaut DEUX dans le livré
# (le Studio minifié, graphe Mh, en porte un) -> l'ancre est la LIGNE ENTIÈRE.
A_EB4 = '        r.jsx("button",{className:"svm-secbtn",onClick:function(){setPop(pop==="preview"?"":"preview")},children:"Preview 480p (gratuit)"}),'
R_EB4 = A_EB4.replace('"Preview 480p (gratuit)"', '"Preview"')
# E-12 (lot E-C, tache 6, 23/09/2026) : l'infobulle, REPLI ici (l'ancre est
# consommee par EB4) — l'aperçu est gratuit et local, la barre le dit.
R_EB4 = R_EB4.replace('svm-secbtn",onClick:', 'svm-secbtn",title:"Aperçu 480p — gratuit, local, aucun crédit",onClick:')

# ── EB5a (E-11, lot E-B tache 5, 23/09/2026) : LE VOILE SOUS LES POPOVERS
# QUI ARMENT UN MODE. Meme geste que le voile de kbPanel (.svm-kbscrim :
# clic = fermer, stopPropagation sur le popover), mais SEULEMENT sous
# popover() (pop = "preview"|"render") et sous le bandeau de fin (dzFin) :
# ovPicker reste SANS voile, un voile inset:0 couvrirait la timeline et
# tuerait le glisser vers les bandes que R_M15B assume (ecart date contre
# la conception). MESURE : l'ancre `transPopover(),` / `kbPanel(),` est
# libre (1/0/1) ; dans le DOM le voile vient APRES popover(), le bandeau
# (R_EA5E) et ovPicker() -- sans z-index il les COUVRIRAIT : la feuille
# le met a 19, sous .svm-pop (20, son-vfx-montage.css:388), parade
# independante de l'ordre DOM (retenue par le plan). Le clic sur le voile
# ferme les deux (setPop + setDzFin) : le bandeau et le popover ne sont
# jamais ouverts ensemble (EA5e), fermer les deux est idempotent.
# ── EC3 (E-6, lot E-C tache 2, 23/09/2026) : LE VOILE PORTE AUSSI LE MENU
# (pop||dzFin||dzMenu) et son clic ferme les trois ; le menu ☰ / contextuel
# (DzTracks.CtxMenu, la couche T1) est rendu JUSTE APRES le voile et AVANT
# kbPanel -- REPLI ici : l'ancre `transPopover(),\n kbPanel(),` est CONSOMMEE
# par EB5a (mesure : 0 dans le livre). Le menu est un .svm-pop (z 20) : il
# passe au-dessus du voile (19) comme les popovers. L'etat dzMenu vit dans
# R_M16REF (a cote de dzScrimRef, qui le lit), Echap dans R_K7.
EC3_MENU = '    dzMenu?r.jsx(DzTracks.CtxMenu,Object.assign({onClose:function(){setDzMenu(null)}},dzMenu)):null,'
A_EB5A = ('    transPopover(),\n'
          '    kbPanel(),')
R_EB5A = ('    transPopover(),\n'
          '    (pop||dzFin||dzMenu)?r.jsx("div",{className:"svm-modescrim",onClick:function(){setPop("");setDzFin(null);setDzMenu(null)}}):null,\n'
          + EC3_MENU + '\n'
          # L5 D-32 (24/09/2026, tache 6) : LA LIGHTBOX DES PLANS, REPLIEE ICI (meme ancre consommee que EC3) -- apres le
          # menu, avant kbPanel ; son propre voile .dzm-lbscrim (z 19, celui de .svm-modescrim) porte la grille ; l'etat
          # dzLb vit dans R_M16REF, dzLbPick dans R_EC1, Echap dans R_K7.
          '    dzLb?r.jsx(DzTracks.Lightbox,{clips:clips,onPick:function(c){dzLbPick(c.id)},onClose:function(){setDzLb(!1)}}):null,\n'
          '    kbPanel(),')

# ── EB5b (E-11) : LA RACINE DE popover() ARRETE LE CLIC (motif kbPanel) ──
# Le voile est un FRERE du popover (pas son parent comme .svm-kbscrim) : un
# clic dans le popover ne remonte donc pas au voile par le DOM ; le
# stopPropagation est celui du motif, garde defensive contre tout ecouteur
# de clic pose plus haut (mesure : aucun aujourd'hui). MESURE : la racine
# `className:"svm-pop",children:[` a quatre espaces et SANS style est
# libre (1/0/1) -- ovPicker porte `style:{top:96}` et n'est pas touche ; le
# bandeau (couche, DzmFinBandeau) porte le sien dans montage.js.
A_EB5B = '    return r.jsxs("div",{className:"svm-pop",children:['
R_EB5B = '    return r.jsxs("div",{className:"svm-pop",onClick:function(e){e.stopPropagation()},children:['

# ── EB6a (E-8, lot E-B tache 6, 23/09/2026) : L'ASIDE A BASCULE, LARGEUR
# ET POIGNEE. `inspOn?` conditionne l'aside entier (replie = absent du DOM,
# le lecteur prend la place : .svm-mid est un flex et .svm-playerzone y est
# flex:1) ; `style:{width:inspW}` remplace les 300px de la feuille amont
# (.svm-insp{width:300px;flex:none}, son-vfx-montage.css:233) ; `data-w`
# est le TEMOIN mesurable a l'ecran (getAttribute). La poignee est le
# PREMIER enfant de l'aside, absolue a gauche (montage.css), 6 px.
# « La timeline reprend la largeur » (conception E-8) : DEJA VRAI, .svm-tl
# est SOEUR de .svm-mid sous .dzsvm.svm-col -- rien a ecrire (mesure
# 23/09/2026). MESURE : l'ouverture est libre (1/0/1) ; la fermeture est
# l'ancre de M13 (1/1/0) -> son `:null` est REPLIE dans R_M13, AVANT le
# `]})` qui ferme .svm-mid (l'aside en est le dernier enfant).
A_EB6A = '      r.jsxs("aside",{className:"svm-insp",children:['
R_EB6A = ('      inspOn?r.jsxs("aside",{className:"svm-insp",style:{width:inspW},"data-w":inspW,children:['
          'r.jsx("div",{className:"svm-insphandle",onPointerDown:inspDown,'
          'title:"Glisser pour redimensionner l\'inspecteur (260–480 px)"}),')

# ── EB6b (E-8) : L'ETAT ET LA POIGNEE, SUR `stA` (pop) ─────────────────────
# L'etat nait de la cle dz_svm_insp (JSON {on,w}) : `on` vaut vrai sauf
# `false` explicite, `w` passe par DzTracks.inspW (260..480, 300 sur tout ce
# qui n'est pas un nombre fini -- une cle corrompue ne rend pas un inspecteur
# de 260 sans un mot). `inspDown` copie le motif WINDOW de la couche
# (dzmTbSaisie : pointermove / pointerup / pointercancel sur window, retires
# au relachement) et PAS ovGesture (setPointerCapture sur le cadre du
# lecteur, un element qui survit au geste ; ici l'aside peut disparaitre a
# la chip). Bouton gauche seul ; la largeur est bornee a CHAQUE mouvement ;
# la persistance n'a lieu qu'au relachement (jamais dans pointermove : des
# centaines d'ecritures). `last` garde la derniere largeur bornee : un
# pointercancel sans coordonnees ne vaut pas « geste nul ». MESURE : `stA`
# est libre (1/0/1, EB1 ayant pris `stO`) ; stDzFin (R_M16REF) vient APRES.
# ── EB7a (E-9, lot E-B tache 7, 23/09/2026) : LES ETATS tlH ET showDur, ET
# LA POIGNEE tlDown — REPLI dans R_EB6B (l'ancre `stA` est NEE d'un
# remplacement : EB6b l'a reprise en tete, une section a part passerait
# `--check` puis abandonnerait au rejeu, meme mesure que TT9b dans R_M13).
# `tlH` : la cle dz_svm_tlh lue BRUTE au montage (Number, null si vide, 0 ou
# NaN) — la hauteur de .dzsvm n'est pas connue avant le premier rendu — puis
# BORNEE dans un effet de montage ([]) sur .dzsvm.clientHeight par
# DzTracks.tlH (30..70 %, null sinon) : la forme la plus simple qui borne
# toujours (une cle corrompue ou une fenetre plus petite qu'hier ne rend pas
# une timeline hors bornes). `showDur` : "1"/"0". `tlDown` copie le motif
# WINDOW d'inspDown (trois ecouteurs retires au relachement, bouton gauche
# seul, persistance au relachement seulement) ; la poignee est le FRERE
# PRECEDENT de .svm-tl (EB7b) : `e.currentTarget.nextElementSibling` donne
# la hauteur de depart quand aucun choix n'est pose (tlH null -> la hauteur
# rendue par le plafond historique) ; tirer vers le HAUT agrandit.
_EB7_ETAT = ('\n'
             '  /* E-9 : la timeline — hauteur choisie (dz_svm_tlh, 30–70 % de .dzsvm) et durées sur les clips (dz_svm_showdur) */\n'
             '  var stTl=x.useState(function(){try{var v=Number(localStorage.getItem("dz_svm_tlh"));return v>0?v:null}catch(_e){return null}}),'
             'tlH=stTl[0],setTlH=stTl[1];\n'
             '  x.useEffect(function(){var el=document.querySelector(".dzsvm");if(el&&tlH!=null)setTlH(DzTracks.tlH(tlH,el.clientHeight))},[]);\n'
             '  var stSd=x.useState(function(){try{return localStorage.getItem("dz_svm_showdur")==="1"}catch(_e){return !1}}),'
             'showDur=stSd[0],setShowDur=stSd[1];\n'
             '  function tlDown(e){if(e.button!==0)return;e.preventDefault();\n'
             '    var sy=e.clientY,el=document.querySelector(".dzsvm"),total=el?el.clientHeight:0,'
             'tl=e.currentTarget.nextElementSibling,sh=tlH||(tl?tl.offsetHeight:0),w=window,last=tlH;\n'
             '    function mv(ev){last=DzTracks.tlH(sh+(sy-ev.clientY),total);setTlH(last)}\n'
             '    function up(){w.removeEventListener("pointermove",mv);w.removeEventListener("pointerup",up);'
             'w.removeEventListener("pointercancel",up);\n'
             '      try{if(last!=null)localStorage.setItem("dz_svm_tlh",String(last))}catch(_e){}}\n'
             '    w.addEventListener("pointermove",mv);w.addEventListener("pointerup",up);'
             'w.addEventListener("pointercancel",up)}\n'
             # L7 D-8 (24/09/2026, tache 3) : L7c1 REPLIE ici (l'etat vit avec ses freres E-9 ; `clips`
             # nait B:1708, AVANT : la memo lit un etat declare). Le defaut vient de la couche (boringDef,
             # UNE reference), la memoire dz_svm_boring est lue en try/catch ; la carte id -> "long"|"jump"
             # est memoisee sur [clips,bo] et VIDE quand la detection est eteinte (aucun calcul, aucun attribut).
             '  /* L7 D-8 (24/09/2026, tâche 3) : le boring detector — réglages {on,maxS,minFrames} (mémoire dz_svm_boring,\n'
             '     défaut boringDef de la couche, éteint) et la carte id → "long"|"jump" de V1, mémoïsée sur [clips,bo], vide si éteint */\n'
             '  var stBo=x.useState(function(){var d=Object.assign({on:!1},DzTracks.boringDef);'
             'try{return Object.assign(d,JSON.parse(localStorage.getItem("dz_svm_boring")||"{}")||{})}catch(_e){return d}}),bo=stBo[0],setBo=stBo[1];\n'
             '  var boMap=x.useMemo(function(){return bo.on?DzTracks.boring(clips,bo):{}},[clips,bo]);\n'
             # L7 D-39 (24/09/2026, tache 4) : l'etat du popover « diff » vit avec ses freres (aucune ancre libre
             # pour lui : `bo` est ne de ce repli). {diff,nomA,nomB} pose par onDiff (R_M14), lu par la garde de
             # popover() (R_L7C3) ; null tant qu'aucune comparaison n'a ete demandee.
             '  /* L7 D-39 (24/09/2026, tâche 4) : la dernière comparaison {diff,nomA,nomB} — posée par « ⇄ » (Projets), montrée par pop==="diff" */\n'
             '  var stDf=x.useState(null),diffSt=stDf[0],setDiffSt=stDf[1];\n'
             # L7 D-3b (24/09/2026, tache 4-bis) : l'etat des vignettes A/B de la jonction en edition vit avec ses
             # freres (aucune ancre libre pour lui, meme raison que diffSt). {a,b : dataURL ou null, k : la cle
             # « source@seconde|source@seconde » qui date les deux images} ; rempli par l'effet de L7g1, lu par la
             # rangee de L7g2 ; k vide tant qu'aucune jonction video/video n'est en edition.
             '  /* L7 D-3b (24/09/2026, tâche 4-bis) : les vignettes A/B de la jonction en édition — {a,b : image ou null, k : clé « source@seconde|source@seconde »} */\n'
             '  var stAb=x.useState({a:null,b:null,k:""}),abSt=stAb[0],setAbSt=stAb[1];')

A_EB6B = '  var stA=x.useState(""),pop=stA[0],setPop=stA[1];'
R_EB6B = (A_EB6B + '\n'
          '  /* E-8 : l\'inspecteur — ouvert ? largeur 260–480 (mémoire dz_svm_insp) */\n'
          '  var stIn=x.useState(function(){try{var s=JSON.parse(localStorage.getItem("dz_svm_insp")||"{}")||{};'
          'return{on:s.on!==!1,w:DzTracks.inspW(s.w)}}catch(_e){return{on:!0,w:300}}}),'
          'inspSt=stIn[0],setInspSt=stIn[1],inspOn=inspSt.on,inspW=inspSt.w;\n'
          '  function inspDown(e){if(e.button!==0)return;e.preventDefault();\n'
          '    var sx=e.clientX,sw=inspW,w=window,last=sw;\n'
          '    function mv(ev){last=DzTracks.inspW(sw+(sx-ev.clientX));setInspSt({on:!0,w:last})}\n'
          '    function up(){w.removeEventListener("pointermove",mv);w.removeEventListener("pointerup",up);'
          'w.removeEventListener("pointercancel",up);\n'
          '      try{localStorage.setItem("dz_svm_insp",JSON.stringify({on:!0,w:last}))}catch(_e){}}\n'
          '    w.addEventListener("pointermove",mv);w.addEventListener("pointerup",up);'
          'w.addEventListener("pointercancel",up)}'
          + _EB7_ETAT)

# ── EB7b (E-9, lot E-B tache 7, 23/09/2026) : LA POIGNEE AU-DESSUS DE LA
# TIMELINE, `data-h` ET LA HAUTEUR INLINE. MESURE (.bak:5218) : la racine de
# .svm-tl a QUATRE espaces (le plan en ecrivait six : ECART date), libre
# 1/0/1. La poignee est le FRERE PRECEDENT de .svm-tl (soeurs sous
# .dzsvm.svm-col, apres .svm-mid) : tirer vers le HAUT agrandit la timeline
# (startH + (startY - clientY)). `data-h` est le temoin mesurable a l'ecran
# et le selecteur de la feuille (`.dzsvm .svm-tl[data-h]{max-height:none;
# min-height:0}`) ; sans choix (tlH null) ni data-h ni height : le plafond
# historique de montage.css:18 reste (affirmation dementie n°5 du plan).
A_EB7B = '    r.jsxs("div",{className:"svm-tl",children:['
R_EB7B = ('    r.jsx("div",{className:"svm-tlhandle",onPointerDown:tlDown,'
          'title:"Glisser pour régler la hauteur de la timeline (30–70 %)"}),\n'
          '    r.jsxs("div",{className:"svm-tl","data-h":tlH||void 0,style:tlH?{height:tlH}:void 0,children:[')

# ── EB8a (D-7, lot E-B tache 8, 23/09/2026) : LA MINI-CARTE DE LA TIMELINE.
# La conception la voulait « au-dessus de la regle » ; dans .svm-lanes
# (width:zoomPct%) elle suivrait le zoom. MESURE (.bak:5338) : l'ouverture de
# .svm-scroll est libre 1/0/1 (six espaces) ; la carte est inseree AVANT elle,
# dans .svm-tl, apres .svm-trans, HORS zoom (affirmation dementie n°6 du plan).
# Noms de portee mesures dans DzMontage : `clips` (st1, .bak:1692),
# `svmTracksOf(proj)` (les pistes, comme dzTracksRef .bak:1762), `dur`
# (= proj.dur, .bak:1870). La gouttiere .svm-gutter (88 px, sticky) est DANS
# .svm-lanes (.bak:5342) donc dans scrollWidth : deduite, comme le zoom deduit
# deja `W-88` / `mx-88` (.bak:2822-2824). Le « clic = centrer » vit ICI :
# l'hote est seul a tenir tlScrollRef ; la couche ne rend que des fractions.
A_EB8A = '      r.jsx("div",{className:"svm-scroll",ref:tlScrollRef,children:'
R_EB8A = ('      /* D-7 : mini-carte HORS zoom — un rect par clip, la fenêtre visible ; clic = centrer .svm-scroll\n'
          '         (la gouttière de 88 px est dans .svm-lanes donc dans scrollWidth : déduite, comme le zoom fait W-88) */\n'
          '      r.jsx(DzTracks.Minimap,{clips:clips,tracks:svmTracksOf(proj),dur:dur,viewFrac:mmView,'
          'onSeek:function(f){var el=tlScrollRef.current;if(!el)return;var w=el.scrollWidth-88;'
          'el.scrollLeft=Math.max(0,f*w-(el.clientWidth-88)/2)}}),\n'
          + A_EB8A)

# ── EB8b (D-7) : LA FENETRE VISIBLE [a,b]. MESURE (.bak:2827-2828) : le
# useLayoutEffect [zoomPct] qui rejoue le scrollLeft en attente est libre
# 1/0/1 et CONSERVE ; en queue : l'etat mmView [0,1], mmCalc (useCallback
# stable, [] — la forme de zoomApply .bak:2816), un effet qui POSE l'ecouteur
# scroll sur tlScrollRef.current et le RETIRE au demontage (motif de l'effet
# wheel .bak:2831-2836), et un effet [zoomPct] : apres le layout, .svm-lanes a
# sa largeur neuve. setMmView garde l'objet quand rien ne change (pas de
# rendu a chaque evenement scroll identique).
A_EB8B = '      tlScrollRef.current.scrollLeft=pendScrollRef.current;pendScrollRef.current=null}},[zoomPct]);'
R_EB8B = (A_EB8B + '\n'
          '  /* D-7 : la fenêtre visible de la mini-carte — [a,b] en fractions de la largeur défilable (gouttière 88 px déduite),\n'
          '     recalculée au défilement de .svm-scroll (écouteur posé au montage, retiré au démontage) et à chaque zoom */\n'
          '  var stMm=x.useState([0,1]),mmView=stMm[0],setMmView=stMm[1];\n'
          '  var mmCalc=x.useCallback(function(){var el=tlScrollRef.current;if(!el)return;var w=el.scrollWidth-88;\n'
          '    var a=w>0?Math.max(0,Math.min(1,el.scrollLeft/w)):0,b=w>0?Math.max(a,Math.min(1,(el.scrollLeft+el.clientWidth-88)/w)):1;\n'
          '    setMmView(function(p){return p[0]===a&&p[1]===b?p:[a,b]})},[]);\n'
          '  x.useEffect(function(){var el=tlScrollRef.current;if(!el)return;el.addEventListener("scroll",mmCalc);mmCalc();\n'
          '    return function(){el.removeEventListener("scroll",mmCalc)}},[mmCalc]);\n'
          '  x.useEffect(function(){mmCalc()},[zoomPct,mmCalc]);')

# ══ E-6 (lot E-C, tache 2, 23/09/2026) — LE MENU ☰ ET LES MENUS CONTEXTUELS ═
# Decisions 1..3 du plan : PAS de dispatch(id) -- une entree a raccourci
# REJOUE sa combo par un KeyboardEvent synthetique sur window (onKey reste
# l'unique dispatch ; MESURE : onKey ne filtre que e.target input / textarea /
# select / contentEditable, window passe -- T1 l'a verifie 45/45 aller-retour) ;
# six rubriques par le modele de la couche (DzTracks.menuModel) ; UN composant
# (DzTracks.CtxMenu) pour ☰ et les deux menus contextuels. Les entrees SANS
# raccourci appellent les fonctions de l'hote, mesurees une a une (voir EC1).
# MESURES 23/09/2026 : SVM_ACTIONS est la table COMPLETE (45 entrees : R_R1
# insere dans le litteral, SVM_ACTION_BY_ID la reprend) ; aucun lien « Guide »
# dans le rail du Montage (les seuls `guide` du bundle sont les guides
# d'alignement tfGuide) -> l'entree Aide › Guide est OMISE (ecart date) ;
# keys_panel (« ? ») est dans Aide PAR LE MODELE -> pas de « Raccourcis »
# double ; svmKeyLabel(id) rend "" sans surcharge -> le modele retombe sur la
# combo de la table ; la couche n'a PAS de o.anchor -> x,y calcules ici depuis
# getBoundingClientRect() du bouton (left, bottom+4). .dzsvm est
# position:absolute;inset:0 : les coordonnees client sont RAMENEES a son
# repere (le motif d'openTransPopAt) et bornees a sa largeur-270 (la couche
# borne encore a la fenetre : sans effet quand le rail est a gauche).
# QUATRE ancres LIBRES (1/0/1 mesurees) : delClip (EC1), svm-title (EC2), le
# onPointerDown du clip (EC4), le svm-thead (EC5). Replis : l'etat dans
# R_M16REF, le voile + le rendu dans R_EB5A, Echap dans R_K7, le bouton
# « remplacer » dans R_M16 (dzReplaceArm).
# ECARTS dates : « Remplacer la source… » est grise SANS src seulement (le plan
# disait « ou pas V1 » ; le geste R_M16 accepte les pistes audio, dzmReplaceBtn
# n'exige que src) ; « Couper a la tete » reprend la tolerance de blade
# (.05 s de chaque bord) ; les bascules (Inspecteur, Medias, Durees, vitesse
# courante) montrent « ✓ » dans la colonne de la combo ; la note de
# « Supprimer la piste » est plus courte que celle de del() (pas le rappel du
# bouton qui la recree), la sequence d'etat est la meme.
A_EC1 = "  var delClip=x.useCallback(function(){delClipById(selRef.current)},[delClipById]);"
R_EC1 = (A_EC1 + "\n"
         '  /* ── E-6 (lot E-C, tâche 2, 23/09/2026) : LE MENU ☰ ET LES MENUS CONTEXTUELS ──\n'
         '     dzFire(id) rejoue la combo VIVANTE d\'une action (svmKeyLabel, repli table) par un\n'
         '     KeyboardEvent synthétique sur window : onKey reste l\'unique dispatch (il ne filtre\n'
         '     que les champs de saisie). dzReplaceArm = le geste du bouton « remplacer » (R_M16),\n'
         '     extrait : le bouton ET le menu du clip l\'appellent. dzMenuProps(kind,o) construit les\n'
         '     entrées À L\'OUVERTURE (mémorisées dans dzMenu, jamais reconstruites au rendu) ; x,y\n'
         '     ramenés au repère de .dzsvm (position:absolute;inset:0 — motif d\'openTransPopAt). */\n'
         '  function dzFire(id){var a=SVM_ACTION_BY_ID[id],k=DzTracks.comboToKey(svmKeyLabel(id)||(a&&a.combo)||"");\n'
         '    if(k)window.dispatchEvent(new KeyboardEvent("keydown",Object.assign({bubbles:!0,cancelable:!0},k)))}\n'
         '  function dzReplaceArm(sel){\n'
         '    if(trackStRef.current[sel.tr]&&trackStRef.current[sel.tr].l){\n'
         '      fireNote("Piste "+sel.tr.toUpperCase()+" verrouillée — "+\n'
         '        "déverrouillez-la pour remplacer la source de ce "+\n'
         '        "plan.");return}\n'
         '    dzmReplaceRef.current={id:sel.id,tr:sel.tr,\n'
         '      label:sel.label};\n'
         '    setDzmArm({tr:sel.tr,label:sel.label});\n'
         '    /* déjà ouvert sur cette piste : rouvrir le REFERMERAIT (le sélecteur bascule), et le\n'
         '       mode resterait armé sur un panneau fermé. C\'est `setDzmArm` — et non `openPicker` —\n'
         '       qui re-rend dans ce cas-là, sans quoi le panneau resterait intitulé « Ajouter sur la\n'
         '       piste V1 » pendant qu\'il remplace. */\n'
         '    if(ovPick!==sel.tr)openPicker(sel.tr)}\n'
         # -- « L7Ba » (L7-B D-37, 24/09/2026) : LE GESTE D'EXPORT, replie ici avec ses
         # deux entrees. La route lit la timeline SAUVEGARDEE (`_load_saved`) : on
         # pousse d'abord la sauvegarde (POST /save, le corps de l'autosave
         # svmSavePayload -- declaration hissee du meme composant), PUIS
         # GET /export ; le nom vient du Content-Disposition du serveur (une seule
         # autorite de nommage), le telechargement par subsDownload (module, .bak x1,
         # le chemin de D-10 et D-22 -- jamais recopie). Refus dits par fireNote :
         # demo (jamais sauvegardee), sauvegarde refusee, `detail` du 400, reseau.
         '  function dzExportTl(fmt){var lib=fmt==="edl"?"EDL":"FCPXML",ext=fmt==="edl"?".edl":".fcpxml";\n'
         '    if(proj.demo){fireNote("Export "+lib+" : disponible sur un projet réel — la démo n\'est pas sauvegardée.");return}\n'
         '    fireNote("Export "+lib+" en cours…");\n'
         '    fetch("/api/montage/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(svmSavePayload())})\n'
         '      .then(function(res){if(!res.ok)throw new Error("sauvegarde refusée ("+res.status+")");return fetch("/api/montage/export?format="+fmt)})\n'
         '      .then(function(res){return res.text().then(function(t){\n'
         '        if(!res.ok){var m="";try{m=(JSON.parse(t)||{}).detail||""}catch(_e){}throw new Error(m||("HTTP "+res.status))}\n'
         '        var mm=/filename="([^"]+)"/.exec(res.headers.get("Content-Disposition")||"");return {nom:mm?mm[1]:"montage"+ext,t:t}})})\n'
         '      .then(function(o){if(subsDownload(o.nom,o.t,fmt==="edl"?"text/plain":"application/xml"))fireNote(lib+" exporté : "+o.nom+" — à importer dans Resolve ou Final Cut Pro");else fireNote("Export impossible dans ce navigateur")})\n'
         '      .catch(function(e){fireNote("Export "+lib+" refusé : "+((e&&e.message)||"erreur réseau"))})}\n'
         # -- « L7Bb » (L7-B D-42, 24/09/2026) : LE GESTE « Decouper aux changements de
         # plan », replie ici avec son entree (le menu de clip est ne de CE remplacement,
         # x0 dans .bak_montage). Garde du clip (video rendue : src.job_id) et du verrou
         # AVANT l'appel ; POST /scenes avec srcIn et la duree de SOURCE consommee
         # ((end-start) x vitesse, la loi de la lame) ; la reponse est appliquee au clip
         # tel qu'il est A LA REPONSE (clipsRef, jamais la copie du clic : l'analyse
         # prend du temps) par DzTracks.cutAt, avec le verrou de DzTracks.cutOpts ;
         # pushHistory() PUIS setClips (annuler ramene le clip entier), setDirty ; la
         # note dit « n coupes » ou le refus (detail du 4xx, reseau).
         '  function dzSceneCut(id){var c=clipsRef.current.find(function(k){return k.id===id});\n'
         '    if(!c||!c.src||!c.src.job_id){fireNote("Découpe aux changements de plan : réservée aux clips vidéo rendus.");return}\n'
         '    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){fireNote("Piste "+c.tr.toUpperCase()+" verrouillée — déverrouillez-la pour découper ce plan.");return}\n'
         '    var sp=typeof c.speed==="number"&&c.speed>0?c.speed:1,du=Math.round(Math.max(0,(c.end-c.start)*sp)*1e3)/1e3;\n'
         # revue D-42 (24/09/2026) : REPONSE OBSOLETE -- l'empreinte (srcIn, vitesse, start, end) du plan
         # ENVOYE est gardee ; a la reponse, un plan dont l'un d'eux a change (trim, slip, vitesse) est
         # refuse, DIT, sans ecriture : les instants rendus ne valent que pour la fenetre analysee. Un plan
         # supprime passe a la couche (refus « Clip introuvable »).
         # revue D-40 (24/09/2026) : l'IDENTITE de la source entre dans l'empreinte (svmSrcKey, module,
         # sans DzTracks) -- « Remplacer la source » pendant l'analyse garde l'id et souvent les bornes.
         '    function dzSg(k){return [Number(k.srcIn)||0,typeof k.speed==="number"&&k.speed>0?k.speed:1,Number(k.start)||0,Number(k.end)||0,svmSrcKey(k.src)].join("|")}\n'
         '    var sg=dzSg(c);\n'
         '    fireNote("Analyse des changements de plan…");\n'
         '    fetch("/api/montage/scenes",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({src:c.src,srcIn:Number(c.srcIn)||0,dur:du})})\n'
         '      .then(function(res){return res.json().catch(function(){return {}}).then(function(j){\n'
         '        if(!res.ok)throw new Error((j&&typeof j.detail==="string"&&j.detail)||("HTTP "+res.status));return j})})\n'
         '      .then(function(j){var k2=clipsRef.current.find(function(k){return k.id===id});\n'
         '        if(k2&&dzSg(k2)!==sg){fireNote("Découpe aux changements de plan refusée : le plan a changé pendant l\'analyse — relancez.");return}\n'
         '        var r2=DzTracks.cutAt(clipsRef.current,id,j&&j.times,DzTracks.cutOpts(proj,trackStRef.current));\n'
         '        if(r2.refus){fireNote(r2.note);return}\n'
         '        pushHistory();setClips(r2.clips);setDirty(!0);fireNote(r2.note)})\n'
         '      .catch(function(e){fireNote("Découpe aux changements de plan refusée : "+((e&&e.message)||"erreur réseau"))})}\n'
         '  function dzMenuProps(kind,o){\n'
         '    var id=o.id,ph=phRef.current,cs=clipsRef.current,rr=rootRef.current?rootRef.current.getBoundingClientRect():{left:0,top:0,width:window.innerWidth};\n'
         '    var base={kind:kind,id:id,x:Math.max(0,Math.min(o.x-rr.left,rr.width-270)),y:Math.max(0,o.y-rr.top)};\n'
         '    if(kind==="main"){\n'
         '      var rubs=DzTracks.menuModel(SVM_ACTIONS,svmKeyLabel).map(function(g){return {rub:g.rub,items:g.items.map(function(a){return {lbl:a.lbl,combo:a.combo,run:function(){dzFire(a.id)}}})}});\n'
         '      rubs.unshift({rub:"Projet",items:[\n'
         '        {lbl:"Projets…",run:function(){setDzProjReq(function(n){return n+1})}},\n'
         '        {lbl:"Preview 480p",run:function(){setPop("preview")}},\n'
         '        {lbl:"Rendre…",run:function(){setPop("render")}},\n'
         '        {lbl:"Publier",off:!dzLast,run:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}}},\n'
         # -- « L7Ba » (L7-B D-37, 24/09/2026) : EXPORT EDL / FCPXML, REPLIE ICI : la
         # rubrique Projet (l'ancre du plan, `dzMenuProps`) est nee de CE remplacement,
         # x0 dans .bak_montage. Le `title` de chaque entree est son libelle (DzmCtxMenu
         # pose title:it.lbl, deja audite par E-12) -- libelles explicites, pas de champ
         # neuf dans la couche (le pin `title:it.lbl` du banc edition et de la
         # campagne EC reste intact). Le geste est dzExportTl (plus bas).
         '        {lbl:"Exporter EDL…",run:function(){dzExportTl("edl")}},\n'
         '        {lbl:"Exporter FCPXML…",run:function(){dzExportTl("fcpxml")}}]});\n'
         '      var aff=rubs.filter(function(g){return g.rub==="Affichage"})[0];\n'
         '      if(!aff){aff={rub:"Affichage",items:[]};rubs.splice(rubs.length-1,0,aff)}\n'
         '      aff.items=aff.items.concat([\n'
         '        {lbl:"Inspecteur",combo:inspOn?"✓":"",run:function(){setInspSt(function(s){var n={on:!s.on,w:s.w};try{localStorage.setItem("dz_svm_insp",JSON.stringify(n))}catch(_e){}return n})}},\n'
         '        {lbl:"Médias",combo:medOn?"✓":"",run:function(){' + _EB_GARDE + 'setMedTr("");setMedOn(!medOn);setSfxOn(!1);setSubsOn(!1);setNarrOn(!1)}},\n'
         '        {lbl:"Durées sur les clips",combo:showDur?"✓":"",run:function(){setShowDur(function(v){var n=!v;try{localStorage.setItem("dz_svm_showdur",n?"1":"0")}catch(_e){}return n})}},\n'
         # L7 D-8 (24/09/2026, tache 3) : L7c2 REPLIE ici (l'entree « Durées sur les clips » du plan est nee
         # de CE remplacement, x0 dans .bak_montage) -- l'entree OUVRE le popover (setPop("boring")), la
         # bascule est dans le popover ; « actif » dans la colonne des combos quand la detection est allumee
         # (pas « ✓ » : ce n'est pas la bascule elle-meme, et le banc E-10 pinne les cinq coches).
         '        {lbl:"Plans trop longs / jump cuts…",combo:bo.on?"actif":"",run:function(){setPop("boring")}},\n'
         # L5 D-32 (24/09/2026, tache 6) : REPLIE ici -- la lightbox des plans (etat dzLb, plus haut dans ce remplacement)
         '        {lbl:"Lightbox des plans",run:function(){setDzLb(!0)}},\n'
         # E-10 (lot E-C, tache 4) : la bascule d'ancrage de la barre (etat R_M11).
         '        {lbl:"Ancrer la barre d\'outils",combo:dzTbDock?"✓":"",run:function(){dzTbDockToggle()}}]);\n'
         '      return Object.assign(base,{rubs:rubs})}\n'
         '    if(kind==="clip"){var c=cs.find(function(k){return k.id===id});if(!c)return null;\n'
         '      var v1=c.tr==="v1",sp=svmSpeedOf(c),g=DzTracks.voisins(cs,c).g;\n'
         '      return Object.assign(base,{items:[\n'
         '        {lbl:"Couper à la tête",combo:svmKeyLabel("blade"),off:!(ph>c.start+.05&&ph<c.end-.05),run:function(){dzFire("blade")}},\n'
         # -- « L7Bb » (L7-B D-42) : TOUJOURS rendue, grisee hors d'un clip video rendu
         # (src.job_id sur une piste video : le jumeau audio d'un plan porte aussi le
         # job_id, il est exclu par le genre de piste) ; title = libelle (DzmCtxMenu).
         '        {lbl:"Découper aux changements de plan",off:!(c.src&&c.src.job_id)||trackKind(c.tr)!=="video",run:function(){dzSceneCut(id)}},\n'
         '        {lbl:"Supprimer",combo:svmKeyLabel("delete"),run:function(){delClipById(id)}},\n'
         '        {lbl:"Remplacer la source…",off:!c.src,run:function(){dzReplaceArm(c)}},\n'
         '        {lbl:"Effets…",off:trackKind(c.tr)==="audio",run:function(){setFxPick(!0)}},\n'
         # L5 D-32 (24/09/2026, tache 6) : REPLIE ici -- les deux entrees du grade, AVANT le separateur existant (le
         # compte `{sep:!0}` == 4 ne bouge pas). Toujours rendues ; grisees : rien a prendre (gradeTake null) /
         # aucun grade copie (gradeRead, lu A L'OUVERTURE), piste non video, demo. Le geste = dzGradeCopy/Paste(id).
         '        {lbl:"Copier le grade",combo:svmKeyLabel("grade_copy"),off:!DzTracks.gradeTake(c),run:function(){dzGradeCopy(id)}},\n'
         '        {lbl:"Coller le grade",combo:svmKeyLabel("grade_paste"),off:!!proj.demo||trackKind(c.tr)!=="video"||!DzTracks.gradeRead(),run:function(){dzGradePaste(id)}},{sep:!0}]\n'
         '        .concat([.25,.5,.75,1,1.5,2].map(function(v){return {lbl:"Vitesse "+Math.round(v*100)+" %",combo:Math.abs(sp-v)<1e-6?"✓":"",off:!v1||!c.src||!c.src.job_id,run:function(){svmSetV1Speed(id,v)}}}))\n'
         '        .concat([{sep:!0},{lbl:"Transition…",off:!g,run:function(){openTransPopAt(id,o.x)}}])})}\n'
         '    if(kind==="track"){var ts=svmTracksOf(proj),t=ts.find(function(k){return k.id===id});if(!t)return null;\n'
         '      var bus=SVM_TRACK_BUS[id],lk=!!(trackSt[id]&&trackSt[id].l),bs=id==="v1"||id==="s1",n=cs.filter(function(k){return k.tr===id}).length;\n'
         '      return Object.assign(base,{items:[\n'
         '        {lbl:lk?"Déverrouiller":"Verrouiller",run:function(){svmTrackLock(id)}},\n'
         '        {lbl:"Muet",off:!bus,run:function(){svmTrackMute(id)}},\n'
         '        {lbl:"Solo",off:!bus,run:function(){svmTrackSolo(id,!1)}},{sep:!0}]\n'
         # L7 D-22 (24/09/2026, tache 6) : REPLIE ici (le menu de piste est ne de CE remplacement, x0 dans
         # .bak_montage) -- pour une piste de sous-titres (trackKind, pas une egalite avec s1) : « Graver cette
         # piste au rendu » (svmTracksSet : historique D-0, bus, projet, NON ENREGISTRE ; « gravee » dans la
         # colonne des combos quand c'est deja elle -- pas « ✓ », le banc E-10 pinne les cinq coches), l'export
         # .srt/.vtt/.txt de SES clips par les fonctions locales du bloc subs (subsToSrt/Vtt/Txt + subsDownload,
         # meme scope module -- T1 l'a mesure pour subsDownload ; nom <projet>-s<n>.<fmt>, memes types MIME que
         # doExport du tiroir), « Nouvelle piste de langue… » (window.prompt NATIF -- ecart date : pas de
         # dialogue maison dans le Montage ; la piste nait VIDE, « Traduire vers » + case « nouvelle piste »
         # la remplit). Un separateur de plus : {sep:!0} 3 -> 4.
         '        /* L7 D-22 (24/09/2026, tâche 6) : une piste de sous-titres — graver, exporter ses clips, nouvelle piste de langue */\n'
         '        .concat(trackKind(id)==="subs"?(function(){var bid=DzTracks.subsBurnId(ts),segs=cs.filter(function(k){return k.tr===id});\n'
         '          function dzSubsExp(fmt){var txt=fmt==="srt"?subsToSrt(segs,subsStyleNow()):fmt==="vtt"?subsToVtt(segs,subsStyleNow()):subsToTxt(segs);\n'
         '            if(!txt.trim()){fireNote("Rien à exporter — la piste "+(t.name||id)+" est vide.");return}\n'
         '            var base=String(proj.name||"sous-titres").replace(/[^\\w\\-. ]+/g,"_")+"-"+id;\n'
         '            fireNote(subsDownload(base+"."+fmt,txt,fmt==="vtt"?"text/vtt":fmt==="srt"?"application/x-subrip":"text/plain")?"Fichier "+base+"."+fmt+" écrit — local, sans compte.":"Téléchargement refusé par le navigateur.")}\n'
         '          return [{lbl:bid===id?"Gravée au rendu":"Graver cette piste au rendu",combo:bid===id?"gravée":"",off:bid===id,run:function(){svmTracksSet(DzTracks.subsBurn(ts,id));\n'
         '              fireNote("Piste "+(t.name||id)+" gravée au rendu — les autres pistes de sous-titres restent à l\'écran seulement.")}},\n'
         '            {lbl:"Exporter .srt",off:!n,run:function(){dzSubsExp("srt")}},{lbl:"Exporter .vtt",off:!n,run:function(){dzSubsExp("vtt")}},{lbl:"Exporter .txt",off:!n,run:function(){dzSubsExp("txt")}},\n'
         '            {lbl:"Nouvelle piste de langue…",run:function(){var lg=window.prompt("Langue de la nouvelle piste de sous-titres (en, de, es…)","en");if(lg==null)return;\n'
         '              var r2=DzTracks.subsNew(ts,lg);svmTracksSet(r2.tracks);\n'
         '              fireNote("Piste "+r2.id.toUpperCase()+(String(lg).trim()?" ("+String(lg).trim()+")":"")+" ajoutée, vide — « Traduire vers » dans le tiroir Sous-titres, case « nouvelle piste », la remplit.")}},{sep:!0}]})():[])\n'
         '        .concat([\n'
         '        {lbl:"Supprimer la piste",off:bs,run:function(){svmTracksSet(DzTracks.remove(ts,id));\n'
         '          if(n)setClips(function(cs2){return (cs2||[]).filter(function(k){return k.tr!==id})});\n'
         '          fireNote("Piste "+(t.name||id)+" retirée"+(n?" avec "+n+" clip"+(n>1?"s":"")+" — annuler ramène les clips":"")+".")}}])})}\n'
         '    return null}\n'
         # -- « L5 » (D-31 D-32, 24/09/2026, tache 6) : LA LIGHTBOX ET LE GRADE, replies ici, APRES dzMenuProps (les bancs decoupent dzExportTl..dzSceneCut..dzMenuProps : rien ne
         # s'y intercale ; le menu est ne de CE
         # remplacement, x0 dans .bak_montage). L'ETAT de la lightbox et son ref sont dans R_M16REF (EC1 ne porte AUCUN
         # hook : pin EC1_dzMenuProps_..._sans_hook) ; dzLbPick = le plan
         # RELU a la reponse (la grille est un instantane de l'ouverture) : ferme, selectionne, tete au debut.
         # dzGradeCopy / dzGradePaste(id) = LE geste du clavier (R_R2) ET du menu de clip : refus dits (aucun plan,
         # demo, piste non video, piste verrouillee), puis DzTracks.gradeCopyDo / gradePasteDo (les gestes du
         # panneau) ; coller = pushHistory() UNE fois, puis setClips + setDirty. Portee : clipsRef, dzProjRef,
         # trackStRef, trackKind, fireNote, pushHistory, seekTo -- ceux des gestes voisins (dzSceneCut, paste).
         '  /* L5 D-31 D-32 : le choix d\'un plan dans la lightbox et les gestes du grade (clavier + menu de clip) */\n'
         '  function dzLbPick(id){var k=clipsRef.current.find(function(q){return q.id===id});setDzLb(!1);\n'
         '    if(!k){fireNote("Lightbox : ce plan n\'existe plus.");return}\n'
         '    setSelId(k.id);seekTo(k.start)}\n'
         '  function dzGradeCopy(id){var c=clipsRef.current.find(function(k){return k.id===id});\n'
         '    if(!c){fireNote("Copier le grade : sélectionnez d\'abord un plan.");return}\n'
         '    fireNote(DzTracks.gradeCopyDo(c).note)}\n'
         '  function dzGradePaste(id){\n'
         '    if(dzProjRef.current&&dzProjRef.current.demo){fireNote("Coller le grade : disponible sur un projet réel — la démo est une maquette.");return}\n'
         '    var c=clipsRef.current.find(function(k){return k.id===id});\n'
         '    if(!c){fireNote("Coller le grade : sélectionnez d\'abord un plan.");return}\n'
         '    if(trackKind(c.tr)!=="video"){fireNote("Coller le grade : réservé aux plans vidéo (V1 et pistes d\'overlay).");return}\n'
         '    if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){fireNote("Piste "+c.tr.toUpperCase()+" verrouillée — déverrouillez-la pour coller le grade.");return}\n'
         '    var q=DzTracks.gradePasteDo(c);if(!q.clip){fireNote(q.note);return}\n'
         '    pushHistory();setClips(clipsRef.current.map(function(k){return k.id===c.id?q.clip:k}));setDirty(!0);fireNote(q.note)}')
# L7 D-22 (24/09/2026) : un quatrieme separateur, entre les entrees de sous-titres et « Supprimer la piste »
assert R_EC1.count("{sep:!0}") == 4 and R_EC1.count("dzmReplaceRef.current={") == 1
assert EC3_MENU in R_EB5A
# EC2 : le bouton ☰ AVANT le titre « Montage » (ancre libre 1/0/1) ; le clic
# sur le bouton pendant que le menu est ouvert tombe en fait sur le voile
# (inset:0, au-dessus de la barre) qui ferme : la branche « refermer » du
# bouton est une ceinture, aria-expanded le temoin.
A_EC2 = '      r.jsx("span",{className:"svm-title",children:"Montage"}),'
R_EC2 = ('      r.jsx("button",{className:"svm-secbtn svm-menubtn",title:"Menu — actions et raccourcis","aria-haspopup":"menu",'
         '"aria-expanded":!!(dzMenu&&dzMenu.kind==="main"),onClick:function(e){if(dzMenu&&dzMenu.kind==="main"){setDzMenu(null);return}'
         'var b=e.currentTarget.getBoundingClientRect();setDzMenu(dzMenuProps("main",{x:b.left,y:b.bottom+4}))},children:"☰"}),\n'
         + A_EC2)
# EC4 : clic droit sur un clip -> selection + menu au pointeur (preventDefault :
# pas de menu natif ; stopPropagation : le .svm-vph du lecteur a son propre
# onContextMenu, seul autre site -- 1 -> 3 avec EC5).
A_EC4 = '                    onPointerDown:function(e){clipDown(e,c,e.currentTarget.parentElement)},'
R_EC4 = (A_EC4 + '\n'
         '                    onContextMenu:function(e){e.preventDefault();e.stopPropagation();setSelId(c.id);setDzMenu(dzMenuProps("clip",{x:e.clientX,y:e.clientY,id:c.id}))},')
# EC5 : clic droit sur l'en-tete d'une piste (les deux formes, bus ou non,
# partagent cette racine).
A_EC5 = '              r.jsxs("div",{className:"svm-thead"+(bus?" svm-thead-a":""),children:'
R_EC5 = A_EC5.replace("children:",
                      'onContextMenu:function(e){e.preventDefault();setDzMenu(dzMenuProps("track",{x:e.clientX,y:e.clientY,id:tr.id}))},children:')
for _a, _r in ((A_EC1, R_EC1), (A_EC2, R_EC2), (A_EC4, R_EC4)):
    assert _a != _r and _a in _r
assert A_EC5 != R_EC5 and R_EC5.startswith(A_EC5[:-9]) and R_EC5.endswith("children:")
# ── E-7 (lot E-C, tache 3, 23/09/2026) : LES TROIS VUES ─────────────────────
# MESURES (1/0/1) : la racine .dzsvm (EC7), la fin de .dzsvm (EC8 -- le DERNIER
# `]})` de la ligne ferme .dzsvm : `]})` svm-scroll, `})` la fermeture-appel,
# `]})` .svm-tl, `]})` .dzsvm, `}` DzMontage ; node --check tranche) et l'ouverture
# de .svm-mid (EC9). L'etat (view, dzJobs, l'effet, dzSetView) est un REPLI dans
# R_M16REF. ECARTS dates : « Voir dans la Bibliotheque » = le chemin EXACT du
# bandeau E-4 (CustomEvent deepotus:navigate -> library ; le plan ecrivait
# props.go("library"), qui n'existe pas dans ce composant) ; presets = D-35 ;
# le panneau est le PREMIER enfant de .svm-mid, a cote du lecteur (la timeline
# et sa poignee sont masquees par la feuille en Medias / Livraison).
A_EC7 = '  return r.jsxs("div",{className:"dzsvm svm-col",ref:rootRef,"data-svm-theme":theme==="light"?"light":void 0,children:['
R_EC7 = A_EC7.replace('ref:rootRef,', 'ref:rootRef,"data-view":view,')
A_EC8 = '          r.jsx("div",{className:"svm-translabel",ref:transLabelRef})]})})]})]})}'
EC8_VIEWS = ('    r.jsx("div",{className:"svm-views",role:"tablist",children:[["medias","Médias"],["montage","Montage"],["livraison","Livraison"]].map(function(v){'
             'return r.jsx("button",{className:"svm-viewbtn",role:"tab","aria-selected":view===v[0],"data-on":view===v[0]?"":void 0,title:"Vue "+v[1],'
             'onClick:function(){dzSetView(v[0])},children:v[1]},v[0])})})]})}')
R_EC8 = (A_EC8[:-4] + ',\n'
         '    /* E-7 : la barre des vues, dernier enfant de .dzsvm (tablist ; data-on = la vue courante) */\n'
         + EC8_VIEWS)
A_EC9 = '    r.jsxs("div",{className:"svm-mid",children:['
R_EC9 = (A_EC9 + '\n'
         '      /* E-7 : le panneau Livraison (le composant Deliver de la couche) -- memes gestes que la barre de titre (Preview / Rendre / Publier = R_EA5D),\n'
         '         historique dzJobs (EC6), « Voir dans la Bibliothèque » = le chemin du bandeau de fin */\n'
         '      view==="livraison"?r.jsx(DzTracks.Deliver,{nom:proj.name,onPreview:function(){setPop("preview")},onRender:function(){setPop("render")},'
         'onPublish:function(){if(dzLast){setPop("");setDzFin(Object.assign({project_id:proj.project_id||""},dzLast))}},publishOn:!!dzLast,lastFin:dzLast,jobs:dzJobs,'
         'onOpenLib:function(){window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}))}}):null,')
for _a, _r in ((A_EC7, R_EC7), (A_EC8, R_EC8), (A_EC9, R_EC9)):
    assert _a != _r and _r.count(_a[:40]) == 1
assert R_EC7.count('"data-view":view,') == 1 and A_EC8.endswith("]})]})}") and R_EC8.endswith("]})}")
# la barre REPRENDS la fermeture retiree : autant de `]})` qu'avant, un `}` final
assert R_EC8.count("]})") == A_EC8.count("]})") == 3 and R_EC9.count("DzTracks.Deliver") == 1
assert R_M16REF.count('x.useState("montage")') == 1 and R_M16REF.count("function dzSetView(v){") == 1 and _EB_GARDE in R_M16REF

# ══ E-13 / E-14 (lot E-C, tache 5, 23/09/2026) — LA TETE DANS L'INSPECTEUR,
# LE TROU SELECTIONNE ═══════════════════════════════════════════════════════
# E-13 : « tête à HH:MM:SS:FF · +HH:MM:SS:FF dans le plan » (ou « hors du
# plan ») en tete de l'inspecteur, par DzTracks.teteTxt (couche, pure) et le
# formateur svmTcFF de .svm-tcmain (30 i/s, decision 7 : pas de « ·ii »).
# ECART MESURE (23/09/2026) : le plan voulait un REPLI dans R_EB6A (apres la
# poignee) ; ce remplacement est pinne OCTET POUR OCTET par le banc bundle
# ([EB] E-8 : `getattr(P,"R_EB6A")==_EB8_R`). L'ancre du PREMIER enfant
# d'origine de l'aside, « Clip sélectionné », est libre (1/0/1) et SUIT la
# poignee : section EC12, meme place a l'ecran (poignee, en-tete, label).
A_EC12 = '        r.jsx(SvmLabel,{children:"Clip sélectionné"}),'
R_EC12 = ('        r.jsx("div",{className:"svm-insphead",title:"Tête de lecture (HH:MM:SS:image à 30 i/s)",children:DzTracks.teteTxt(ph,sel,svmTcFF)}),\n'
          + A_EC12)
# E-14 : selectionner un trou, Suppr = ripple SUR LA PISTE (decision 8 :
# DzTracks.trouRipple ne decale que les clips de cette piste apres le trou --
# ecart date : le jumeau A1 ne suit pas, comme D-4 ; DzTracks.rippleCut,
# lui, agit sur TOUTES les pistes et sert range_cut). La queue de piste n'est
# pas un trou (DzTracks.trou rend null sans clip suivant), ni un vide < 0,05 s.
# EC10 : le clic dans le VIDE d'une lane. MESURE : .svm-lane n'avait ni
# onPointerDown ni onClick (onDragOver/onDrop seuls) ; la tete ne se pose que
# par la regle (rulerDown). Cible = la lane ELLE-MEME (e.target===
# e.currentTarget : un clip est un enfant, il garde clipDown ; .svm-gap de V1
# est pointer-events:none et .svm-gapsel aussi -- le clic y retombe sur la
# lane), bouton gauche, hors demo (proj.demo : la maquette ne s'edite pas).
# ECART MESURE : `phFromEvent(e,lane)` deduirait la gouttiere de 88 px une
# SECONDE fois (.svm-lane est flex:1 A COTE de .svm-thead 88 px ; les clips
# sont poses en % de la lane elle-meme) -> le temps est lu sur le rect de la
# lane, le cadre exact des clips. Pas de stopPropagation : rien n'ecoutait.
# ECARTS DATES (revue T5, 23/09/2026) : le clip selectionne LE RESTE apres
# un clic dans le vide (le dernier cliche gagne : trou ET clip peuvent etre
# selectionnes, Suppr prend le trou d'abord) ; les MARQUEURS (D-5) ne suivent
# pas le ripple du trou, comme le jumeau A1 ; le seuil de 0,05 s est
# flottant (6,05-6 < 0,05 en IEEE : un tel trou est refuse -- assume).
A_EC10 = '                onDrop:function(e){dropOnTrack(e,tr.id,e.currentTarget)},'
R_EC10 = (A_EC10 + '\n'
          '                onPointerDown:function(e){if(e.button!==0||e.target!==e.currentTarget||proj.demo)return;'
          'var rc=e.currentTarget.getBoundingClientRect();var t=(e.clientX-rc.left)/rc.width*durRef.current;'
          'var g=DzTracks.trou(clipsRef.current,tr.id,t);setGapSel(g?{tr:tr.id,a:g.a,b:g.b}:null)},')
# EC11 : le rendu du trou, dans la lane de SA piste, en % de dur comme les
# clips et svmV1Gaps (ancre libre : la ligne des trous noirs de V1).
A_EC11 = '                tr.id==="v1"?svmV1Gaps(clips,dur):null,'
R_EC11 = (A_EC11 + '\n'
          '                gapSel&&gapSel.tr===tr.id?r.jsx("div",{className:"svm-gapsel",style:{left:(gapSel.a/dur*100)+"%",width:((gapSel.b-gapSel.a)/dur*100)+"%"},'
          'title:"Trou sélectionné — Suppr le referme (ripple sur cette piste)"}):null,')
# EC13 : Suppr. La branche `if(id==="delete"){` est libre (1/0/1) ; le trou
# passe AVANT le losange d'automation (vpDel) et le clip (delClip). La
# sequence est CELLE de delClipById : verrou de piste (meme phrase, meme
# ref), pushHistory() (empile clipsRef.current), setClips, setDirty(!0),
# note. gapSelRef (pas gapSel) : onKey est un ecouteur window aux deps figees.
A_EC13 = '      if(id==="delete"){'
R_EC13 = (A_EC13 + '\n'
          '        /* E-14 : un trou sélectionné passe avant le losange et le clip */\n'
          '        if(gapSelRef.current){var gs=gapSelRef.current;if(trackStRef.current[gs.tr]&&trackStRef.current[gs.tr].l){fireNote("Piste "+gs.tr.toUpperCase()+" verrouillée — déverrouillez-la pour refermer le trou.");return}\n'
          '          pushHistory();setClips(DzTracks.trouRipple(clipsRef.current,gs.tr,gs.a,gs.b));setDirty(!0);setGapSel(null);'
          'fireNote("Trou de "+svmShort(gs.b-gs.a)+" refermé sur "+gs.tr.toUpperCase());return}')
# EC14 : un clic sur un clip efface le trou (ancre libre : la tete de clipDown).
A_EC14 = '  function clipDown(e,c,laneEl){'
R_EC14 = A_EC14 + '\n    if(gapSelRef.current)setGapSel(null); /* E-14 : un clic sur un clip efface le trou sélectionné */'
for _a, _r in ((A_EC10, R_EC10), (A_EC11, R_EC11), (A_EC12, R_EC12), (A_EC13, R_EC13), (A_EC14, R_EC14)):
    assert _a != _r and _r.count(_a) == 1
assert R_M16REF.count("gapSelRef.current=gapSel;") == 1 and R_K7.count("setGapSel(null)") == 1
assert R_M16REF.count("},[clips]);") == 1 and R_M16REF.find("},[clips]);") > R_M16REF.find("gapSelRef.current=gapSel;")
assert R_K7.find("dzMkOnRef") < R_K7.find("setGapSel(null)") < R_K7.find("dzScrimRef")

# ══ E-12 (lot E-C, tache 6, 23/09/2026) — UN BOUTON SE GRISE, NE DISPARAIT
# PAS ; INFOBULLE OBLIGATOIRE ═══════════════════════════════════════════════
# Banc de SOURCES : backend/tests/test_montage_ergonomie.py (regle 1 : tout
# bouton svm-tbtn/dzm-tbb/svm-secbtn/svm-goldbtn/svm-minibtn/svm-viewbtn/
# svm-menuitem/svm-menubtn porte `title:` ; regle 2 : aucun bouton d'outil
# rendu selon l'etat, les contextuels toleres pinnes et dates).
# MESURES (23/09/2026, livre cc34c2c) : douze sites du bundle sans `title`
# dans DzMontage, dont ONZE sur des ancres LIBRES (1 dans .bak_montage, 0 dans
# le patcher) -> sections EC15a..EC15k ; les deux autres (« Preview » = R_EB4,
# « Rendre → » = R_EA5D) sont des hotes deja consommes -> repli dans le
# remplacement (title ajoute, banc [EB] realigne). Deux boutons DISPARAISSAIENT
# sur la demo (`proj.demo?null:` x2 dans .bak) : le bouton or du popover de
# rendu (Reessayer / Rendre / Lancer l'apercu) et « bibliotheque » -> rendus
# TOUJOURS, `disabled:proj.demo` + infobulle qui le dit. Handlers mesures :
# launchRender porte `if(proj.demo||(job&&job.status!=="failed"))return;`
# (.bak) ; setLibArm(!0) est inatteignable sous `disabled`. Le grise du
# bouton or reprend le style inline du busy (aucune regle :disabled pour
# .svm-goldbtn en amont, mesure) ; « bibliotheque » a `.svm-secbtn:disabled`
# (montage.css:1355, E-5). « (Echap) » n'est ecrit que la ou Echap ferme
# VRAIMENT (R_K7 : dzScrimRef -> setPop("") ; kbPanel : setKbOn(!1)) ; les
# selecteurs d'effets et d'overlay n'ecoutent pas Echap (mesure) : pas de
# promesse.
# (_EC15_DEMO est defini avec EA5, plus haut : R_EA5D2 le reprend pour « Ajouter a la file »)
A_EC15A = '        r.jsx("button",{className:"svm-secbtn",onClick:function(){setPop("");if(failed)setJob(null)},children:"Fermer"}),'
R_EC15A = A_EC15A.replace('svm-secbtn",onClick:', 'svm-secbtn",title:"Fermer ce panneau (Échap)",onClick:')
A_EC15B = ('        proj.demo?null:\n'
           '          failed?r.jsx("button",{className:"svm-goldbtn",onClick:function(){launchRender(!isR)},children:"Réessayer"}):')
R_EC15B = ('          failed?r.jsx("button",{className:"svm-goldbtn",disabled:proj.demo,title:proj.demo?' + _EC15_DEMO
           + ':"Relancer le rendu qui a échoué",onClick:function(){launchRender(!isR)},children:"Réessayer"}):')
A_EC15C = '          r.jsx("button",{className:"svm-goldbtn",disabled:busy,style:busy?{opacity:.55,cursor:"default"}:null,'
R_EC15C = ('          r.jsx("button",{className:"svm-goldbtn",disabled:busy||proj.demo,style:(busy||proj.demo)?{opacity:.55,cursor:"default"}:null,'
           'title:proj.demo?' + _EC15_DEMO + ':(isR?"Lancer le rendu final (master 1080, local)":"Lancer l\'aperçu 480p (gratuit, local)"),')
A_EC15D = 'r.jsx("button",{className:"svm-secbtn",onClick:function(){setFxPick(!1)},children:"Fermer"})'
R_EC15D = A_EC15D.replace('svm-secbtn",onClick:', 'svm-secbtn",title:"Fermer le sélecteur d\'effets",onClick:')
A_EC15E = 'r.jsx("button",{className:"svm-secbtn",onClick:function(){setOvPick("")},children:"Fermer"})'
R_EC15E = A_EC15E.replace('svm-secbtn",onClick:', 'svm-secbtn",title:"Fermer le sélecteur d\'overlay",onClick:')
A_EC15F = 'r.jsx("button",{className:"svm-secbtn",onClick:function(){setKbOn(!1)},children:"Fermer"})'
R_EC15F = A_EC15F.replace('svm-secbtn",onClick:', 'svm-secbtn",title:"Fermer le panneau des raccourcis (Échap)",onClick:')
A_EC15G = ('      r.jsx("button",{className:"svm-minibtn",onClick:function(){\n'
           '        var id=selRef.current,i2=fxEdit.i;')
R_EC15G = A_EC15G.replace('svm-minibtn",onClick:', 'svm-minibtn",title:"Retirer cet effet du plan",onClick:')
A_EC15H = ('              r.jsx("button",{className:"svm-minibtn",\n'
           '                onClick:function(){setKmOv({});svmKmSave({});')
R_EC15H = A_EC15H.replace('svm-minibtn",\n', 'svm-minibtn",\n                title:"Confirmer : tous les raccourcis reviennent au défaut",\n')
A_EC15I = ('              r.jsx("button",{className:"svm-minibtn svm-kbno",\n'
           '                onClick:function(){setKbConfirm(!1)},children:"non"})')
R_EC15I = A_EC15I.replace('svm-kbno",\n', 'svm-kbno",\n                title:"Garder les raccourcis personnalisés",\n')
A_EC15J = ('        r.jsx("button",{className:"svm-minibtn",\n'
           '          onClick:function(e){e.stopPropagation();setNarrArm("")},children:"Non"})')
R_EC15J = A_EC15J.replace('svm-minibtn",\n', 'svm-minibtn",\n          title:"Annuler — aucune voix générée, aucun crédit consommé",\n')
A_EC15K = ('      proj.demo?null:libArm?\n'
           '        r.jsxs("span",{className:"svm-libconfirm",children:[\n'
           '          r.jsx("span",{children:"écraser la sauvegarde ?"}),\n'
           '          r.jsx("button",{className:"svm-minibtn",onClick:svmLibReset,children:"oui"}),\n'
           '          r.jsx("button",{className:"svm-minibtn svm-kbno",\n'
           '            onClick:function(){setLibArm(!1)},children:"non"})]}):\n'
           '        r.jsx("button",{className:"svm-secbtn svm-libbtn",\n'
           '          title:"Réinitialiser depuis la Bibliothèque — écrase la sauvegarde",\n'
           '          onClick:function(){setLibArm(!0)},children:"bibliothèque"}),')
R_EC15K = ('      libArm?\n'
           '        r.jsxs("span",{className:"svm-libconfirm",children:[\n'
           '          r.jsx("span",{children:"écraser la sauvegarde ?"}),\n'
           '          r.jsx("button",{className:"svm-minibtn",title:"Confirmer : la sauvegarde est écrasée par la Bibliothèque",onClick:svmLibReset,children:"oui"}),\n'
           '          r.jsx("button",{className:"svm-minibtn svm-kbno",\n'
           '            title:"Garder la sauvegarde",\n'
           '            onClick:function(){setLibArm(!1)},children:"non"})]}):\n'
           '        r.jsx("button",{className:"svm-secbtn svm-libbtn",disabled:proj.demo,\n'
           '          title:proj.demo?"Réinitialisation indisponible sur la démo":"Réinitialiser depuis la Bibliothèque — écrase la sauvegarde",\n'
           '          onClick:function(){setLibArm(!0)},children:"bibliothèque"}),')
# ══ L4 (23/09/2026, tache 4) — LES REGLAGES DE LIVRAISON DANS LE POPOVER DE
# RENDU, LE PAYLOAD, LA FILE ═══════════════════════════════════════════════
# Decisions 5-8 du plan L4. MESURES (23/09/2026, .bak_montage) : les six
# ancres ci-dessous valent 1 dans .bak_montage, 0 dans le patcher avant ce lot
# (la ligne cout `"$0.00"})]}),` ; `function renderPayload(preview){` + sa
# premiere ligne ; `return o})}}` + `function launchRender(preview){` ; le
# setJob « Envoi… » ; `body:JSON.stringify(renderPayload(preview))})` ; le
# `.then(function(o){` de launchRender + sa ligne d'echec ; son `.catch`).
# L4b : la rangee DzTracks.DeliverRow (couche) sous la ligne cout, rendu final
# seulement (isR) ; lufs = l'etat pose par setLufs(m) (doMeasure, .bak:4494,
# declare :1779 -- popover() est appelee au rendu, l'etat est en portee).
# L4c : renderPayload(preview, queue) -- `return {` devient `var _b={` et la
# fermeture de l'objet est suivie de `return preview?_b:DzTracks.
# deliverPayload(_b, dzDelRef.current + {range:proj.range, queue})` : l'apercu
# ET /measure (renderPayload(!0)) restent EXACTEMENT le payload historique.
# L4d : launchRender(preview, queue) -- en file, AUCUN `job` suivi (decision
# 7 : pas de setJob, pas de poll ; le badge de la vue Livraison suit GET
# /api/jobs) : la reponse {queued:true, position, message} donne la note et
# ferme le popover ; un refus ({detail}) ou une panne reseau sont DITS.
# La garde `if(proj.demo||(job&&job.status!=="failed"))return;` (R_EA6) est
# INCHANGEE : un rendu direct en cours refuse aussi la file (le bouton est
# grise `busy` dans R_EA5D2).
A_L4B = 'r.jsx("span",{className:"svm-cost",children:"$0.00"})]}),'
R_L4B = (A_L4B + '\n'
         '      /* L4 (D-35/D-24/D-38) : preset, cadence, loudness + pastille, plage I/O, preset maison -- rendu final seulement */\n'
         '      isR?r.jsx(DzTracks.DeliverRow,{opts:dzDel,api:dzApi,lufs:lufs,hasRange:!!DzTracks.rangeFrom(proj.range),onChange:dzDelSet,onSavePreset:dzSavePreset}):null,')
A_L4C1 = ('  function renderPayload(preview){\n'
          '    return {name:proj.name,ratio:proj.ratio,preview:preview,')
R_L4C1 = ('  function renderPayload(preview,queue){\n'
          '    var _b={name:proj.name,ratio:proj.ratio,preview:preview,')
A_L4C2 = ('        return o})}}\n'
          '  function launchRender(preview){')
R_L4C2 = ('        return o})};\n'
          '    /* L4 : hors apercu, les reglages de livraison (dzDelRef, frais) et la plage du projet entrent par la couche ; `queue` (D-36) vient de launchRender */\n'
          '    return preview?_b:DzTracks.deliverPayload(_b,Object.assign({},dzDelRef.current,{range:proj.range,queue:queue===!0}))}\n'
          '  function launchRender(preview,queue){')
A_L4D1 = '    setJob({id:null,kind:preview?"preview":"final",status:"queued",progress:0,step:"Envoi…",error:null});'
R_L4D1 = '    if(!queue)' + A_L4D1.lstrip()
A_L4D2 = '      body:JSON.stringify(renderPayload(preview))})'
R_L4D2 = '      body:JSON.stringify(renderPayload(preview,queue))})'
A_L4D3 = ('      .then(function(o){\n'
          '        if(!o.ok||!o.d.job_id){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",')
R_L4D3 = ('      .then(function(o){\n'
          '        /* L4 (D-36) : en file, aucun `job` suivi (le badge de la vue Livraison suit GET /api/jobs) : note + fermeture, ou refus dit */\n'
          '        if(queue){if(o.ok&&o.d&&o.d.queued){fireNote(o.d.message||"Ajouté à la file");setPop("")}else fireNote("File refusée : "+((o.d&&(o.d.detail||o.d.error))||"échec"));return}\n'
          '        if(!o.ok||!o.d.job_id){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",')
A_L4D4 = '      .catch(function(e){setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",error:String(e)})})}'
R_L4D4 = '      .catch(function(e){if(queue){fireNote("File : "+String(e));return}setJob({id:null,kind:preview?"preview":"final",status:"failed",progress:0,step:"",error:String(e)})})}'
L4 = [("L4b-rangee-de-livraison-sous-la-ligne-cout", A_L4B, R_L4B),
      ("L4c1-renderPayload-preview-queue-var-b", A_L4C1, R_L4C1),
      ("L4c2-renderPayload-deliverPayload-et-launchRender-queue", A_L4C2, R_L4C2),
      ("L4d1-pas-de-job-suivi-en-file", A_L4D1, R_L4D1),
      ("L4d2-payload-avec-queue", A_L4D2, R_L4D2),
      ("L4d3-reponse-en-file-note-et-fermeture", A_L4D3, R_L4D3),
      ("L4d4-panne-reseau-en-file-dite", A_L4D4, R_L4D4)]
for _n, _a, _r in L4:
    assert _a != _r and _a.strip()[:10] in _r, _n   # 10 : la tete de l'ancre (L4c2 reecrit `return o})}}` des le `}}`, L4d1 prefixe l'indentation)

# ══ L7 D-10 (24/09/2026, tache 1) — PRESET RESOLVE, EXPORT / IMPORT DU MAPPAGE ═══
# Le plan prevoyait trois sections ; MESURE sur .bak_montage : l'entree adjust_add
# de SVM_ACTIONS et sa branche de dispatch sont x0 (posees par R_R1 / R_R2) ->
# L7a1 et L7a2 sont REPLIEES dans ces deux remplacements (voir « L7a1 », « L7a2 »
# plus haut). Reste L7a3, ancre LIBRE (1/0/1) : le commentaire « Réinitialiser
# tout » du panneau « ? ». TROIS boutons `svm-secbtn svm-kbio` inseres AVANT le
# conditionnel nOv?(...), rendus TOUJOURS (regle E-12), chacun avec title :
#  - « Preset Resolve » : DzTracks.kmPreset("resolve") -> setKmOv + svmKmSave (le
#    chemin exact de « Réinitialiser tout » et du remappage d'une ligne) ; le
#    preset REMPLACE les overrides (un preset est un etat entier, pas un delta) ;
#  - « Exporter… » : DzTracks.kmExport(kmOv) -> subsDownload(name,text,mime), le
#    helper de telechargement du bloc subs (module, .bak x1, blob revoque a 400 ms)
#    -- jamais recopie ;
#  - « Importer… » : <input type=file accept=.json> cree a la volee, FileReader,
#    DzTracks.kmImport(txt, SVM_ACTIONS, svmComboCanon, svmComboReserved) -- les
#    trois juges du bundle, passes en parametres ; ok -> setKmOv + svmKmSave +
#    note « n importes, m ignores » ; sinon « Fichier illisible » / « Version ».
# Les retours passent par fireNote : kbMsg est {id,msg} PAR LIGNE (B:2004), il
# n'y a pas de message global dans le panneau. setKbEdit("") + setKbMsg(null)
# comme « Réinitialiser tout » : une capture en cours ou un refus inline
# n'a plus de sens apres un changement d'etat entier.
A_L7A3 = "          /* « Réinitialiser tout » — visible dès qu'un override existe,"
R_L7A3 = (
    '          r.jsx("button",{className:"svm-secbtn svm-kbio",title:"Preset Resolve : pose O (sortie), Ctrl+B (lame), Alt+O (barre d\'outils) — Ctrl+T reste au navigateur, la transition est sur Alt+T",\n'
    '            onClick:function(){var pr=DzTracks.kmPreset("resolve");if(!pr){fireNote("Preset introuvable");return}setKmOv(pr);svmKmSave(pr);setKbEdit("");setKbMsg(null);\n'
    '              fireNote("Preset Resolve appliqué : O = sortie, Ctrl+B = lame, Alt+O = barre d\'outils — JKL, I et Alt+T étaient déjà là")},\n'
    '            children:"Preset Resolve"}),\n'
    '          r.jsx("button",{className:"svm-secbtn svm-kbio",title:"Exporter les raccourcis personnalisés (deepotus-raccourcis.json)",\n'
    '            onClick:function(){if(!subsDownload("deepotus-raccourcis.json",DzTracks.kmExport(kmOv),"application/json")){fireNote("Export impossible dans ce navigateur");return}\n'
    '              fireNote(nOv?nOv+" raccourci"+(nOv>1?"s":"")+" personnalisé"+(nOv>1?"s":"")+" exporté"+(nOv>1?"s":""):"Aucun raccourci personnalisé — fichier vide exporté")},\n'
    '            children:"Exporter…"}),\n'
    '          r.jsx("button",{className:"svm-secbtn svm-kbio",title:"Importer un fichier de raccourcis JSON — les actions inconnues et les touches réservées sont ignorées",\n'
    '            onClick:function(){var inp=document.createElement("input");inp.type="file";inp.accept=".json,application/json";\n'
    '              inp.onchange=function(){var f=inp.files&&inp.files[0];if(!f)return;var rd=new FileReader();\n'
    '                rd.onload=function(){var rs=DzTracks.kmImport(String(rd.result||""),SVM_ACTIONS,svmComboCanon,svmComboReserved);\n'
    '                  if(!rs.ok){fireNote(rs.raison==="json"?"Fichier illisible — ce n\'est pas du JSON":"Version de fichier inconnue (attendu : version 1)");return}\n'
    '                  setKmOv(rs.keymap);svmKmSave(rs.keymap);setKbEdit("");setKbMsg(null);var nk=Object.keys(rs.keymap).length,ni=rs.ignores.length;\n'
    '                  fireNote(nk+" raccourci"+(nk>1?"s":"")+" importé"+(nk>1?"s":"")+(ni?" — "+ni+" ignoré"+(ni>1?"s":"")+" (action inconnue, touche réservée ou illisible)":""))};\n'
    '                rd.onerror=function(){fireNote("Fichier illisible")};rd.readAsText(f)};\n'
    '              inp.click()},\n'
    '            children:"Importer…"}),\n'
    + A_L7A3)
# ══ L7 D-6 (24/09/2026, tache 2, revue I-1) — LE TEXTE SELECTIONNE GARDE SON Ctrl+C ═
# onKey ecoute window : hors champ de saisie, `e.preventDefault()` (B:3416)
# precede toutes les branches et AVALAIT la copie native d'un texte
# selectionne a la souris (une note, un libelle de clip, une entree de la
# Bibliotheque). Ancre LIBRE 1/0/1 (trois lignes : sounds_drawer, le
# preventDefault, keys_panel) : quand l'action est `copy` et qu'une selection
# de texte est vivante, on SORT avant le preventDefault -- le navigateur copie
# le texte, le clip n'est pas touche. Aucun DzTracks : la sonde ne bouge pas.
A_L7B3 = ('      if(id==="sounds_drawer"){if(svmSfx()){e.preventDefault();sfxToggle()}return}\n'
          '      e.preventDefault();\n'
          '      if(id==="keys_panel"){setKbOn(function(v){return !v});return}')
R_L7B3 = ('      if(id==="sounds_drawer"){if(svmSfx()){e.preventDefault();sfxToggle()}return}\n'
          '      if(id==="copy"&&window.getSelection&&String(window.getSelection())!=="")return;\n'
          '      e.preventDefault();\n'
          '      if(id==="keys_panel"){setKbOn(function(v){return !v});return}')
# ══ L7 D-8 (24/09/2026, tache 3) — BORING DETECTOR : PLANS TROP LONGS ET JUMP CUTS ═
# Le plan prevoyait trois sections ; MESURE sur .bak_montage : les trois ancres
# du plan (`"data-kind"`, l'etat showDur, l'entree « Durées sur les clips ») sont
# x0 -- nees des remplacements R_AJ6A, R_EB6B (_EB7_ETAT) et R_EC1 -> L7c1 et
# L7c2 sont REPLIEES dans ces trois remplacements. Reste L7c3, ancre LIBRE
# (1/0/1, trois lignes) : le commentaire de popover(), sa tete et sa garde
# `if(!pop)return null;`. MESURE : popover() rend pour TOUT `pop` non vide
# (`isR=pop==="render"`, sinon la forme Preview) -- un `pop==="boring"` y
# tomberait dans l'aperçu 480p ; la garde du popover de rendu DELEGUE donc a
# boringPopover() avant de lire isR. Le rendu reste `popover(),` (R_EA5E),
# sous le voile (pop||...) et Echap (dzScrimRef) : rien d'autre a cabler.
# Le popover : case « Activer », deux champs numeriques bornes (2..60 s,
# 1..60 images -- la forme de fieldNum, closure d'ovInspector hors de portee :
# `svm-transdur` + type number, meme classe), un compte des plans marques, un
# « Fermer » titre (E-12) ; chaque changement est persiste (dz_svm_boring,
# try/catch) et l'etat repart de bo -- la carte suit par la memo.
A_L7C3 = ('  /* popover de confirmation — coût affiché avant tout déclenchement (règle produit) */\n'
          '  function popover(){\n'
          '    if(!pop)return null;')
R_L7C3 = ('  /* L7 D-8 (24/09/2026, tâche 3) : le popover « Plans trop longs / jump cuts » (☰ › Affichage) — la case\n'
          '     allume la carte, les deux champs bornent le juge, chaque changement est persisté (dz_svm_boring) */\n'
          '  function boringPopover(){\n'
          '    function boSet(p){setBo(function(b){var n=Object.assign({},b,p);try{localStorage.setItem("dz_svm_boring",JSON.stringify({on:!!n.on,maxS:n.maxS,minFrames:n.minFrames}))}catch(_e){}return n})}\n'
          '    function boNum(k,lo,hi,raw){var v=Math.round(Number(raw));if(!isFinite(v))return;var p={};p[k]=Math.min(hi,Math.max(lo,v));boSet(p)}\n'
          '    var nb=Object.keys(boMap).length,nj=Object.keys(boMap).filter(function(k){return boMap[k]==="jump"}).length;\n'
          '    return r.jsxs("div",{className:"svm-pop svm-boringpop",onClick:function(e){e.stopPropagation()},children:[\n'
          '      r.jsx("div",{className:"svm-poptitle",children:"Plans trop longs / jump cuts"}),\n'
          '      r.jsx("div",{className:"svm-popnote",children:"Sur V1 : liseré gris pointillé = plan plus long que le seuil ; liseré rouge = jump cut (même source reprise presque au même point, à la coupe)."}),\n'
          '      r.jsxs("label",{className:"svm-delrange svm-boringon",title:"Marquer sur la timeline les plans trop longs et les jump cuts de V1",children:[\n'
          '        r.jsx("input",{type:"checkbox",checked:!!bo.on,onChange:function(e){boSet({on:!!e.target.checked})}})," Activer"]}),\n'
          '      r.jsxs("div",{className:"svm-fadegain svm-boringrow",children:[\n'
          '        r.jsx("span",{className:"svm-fxeditname",children:"Plus long que (s)"}),\n'
          '        r.jsx("input",{className:"svm-transdur",type:"number",min:2,max:60,step:1,value:bo.maxS,title:"Un plan de V1 plus long que ce seuil (2 à 60 s) est marqué « long »",onChange:function(e){boNum("maxS",2,60,e.target.value)}})]}),\n'
          '      r.jsxs("div",{className:"svm-fadegain svm-boringrow",children:[\n'
          '        r.jsx("span",{className:"svm-fxeditname",children:"Jump cut si écart < (images)"}),\n'
          '        r.jsx("input",{className:"svm-transdur",type:"number",min:1,max:60,step:1,value:bo.minFrames,title:"Deux plans V1 de la même source, en contact, dont la reprise est à moins de n images (1 à 60, à 30 i/s) : jump cut",onChange:function(e){boNum("minFrames",1,60,e.target.value)}})]}),\n'
          '      r.jsx("div",{className:"svm-popnote",children:bo.on?(nb?nb+" plan"+(nb>1?"s":"")+" marqué"+(nb>1?"s":"")+" sur V1 ("+nj+" jump cut"+(nj>1?"s":"")+")":"Aucun plan à signaler sur V1"):"Détection éteinte"}),\n'
          '      r.jsx("div",{className:"svm-poprow",children:\n'
          '        r.jsx("button",{className:"svm-secbtn",title:"Fermer ce panneau (Échap)",onClick:function(){setPop("")},children:"Fermer"})})]})}\n'
          + A_L7C3 + '\n'
          # L7 D-39 (24/09/2026, tache 4) : L7d1 REPLIE ici -- la garde delegue le popover « diff » a la vue de
          # la couche (DzTracks.DiffView, qui lit `r` a l'appel) AVANT la branche boring et AVANT isR ; sans etat
          # (diffSt null) la garde passe. La section reste UNE (ancre 1/0/1 conservee, queue `boring` intacte).
          # revue 24/09 : un `diff` SANS etat rend null -- jamais le popover generique (isR/Preview) sur ce pop
          '    if(pop==="diff")return diffSt?r.jsx(DzTracks.DiffView,Object.assign({onClose:function(){setPop("")}},diffSt)):null;\n'
          '    if(pop==="boring")return boringPopover();')
# ══ L7 D-3b (24/09/2026, tache 4-bis) — VIGNETTES A/B ET ROLL D'UNE IMAGE A LA JONCTION ═
# MESURES contre le plan : (1) le popover de jonction n'est PAS `pop==="trans"`
# mais l'etat `transPop` {id: clip de DROITE, x} (B:1757), ferme par son propre
# effet [transPop] (clic exterieur, Echap) -- la DERNIERE ligne de cet effet est
# une ancre LIBRE 1/0/1 : L7g1 y pose, en portee de DzMontage, le calcul de la
# jonction (clip droit, voisin gauche par la couche -- meme mesure que le roll
# --, les deux secondes de source par la couche, la cle « source@seconde|
# source@seconde »), l'effet garde par la cle qui demande les deux vignettes a
# svmThumb (l'OBJET src, comme SvmFilmstrip ; le rappel relit le cache a
# l'arrivee) et abRoll. (2) la rangee « Durée » de transPopover() est une ancre
# LIBRE 1/0/1 (trois lignes) : L7g2 pose la rangee A/B AVANT elle. (3) l'etat
# abSt est REPLIE en queue de _EB7_ETAT (R_EB6B), avec diffSt. (4) dzmRoll
# refuse en rendant un tableau NEUF de contenu identique : le refus se lit sur
# le start du clip droit, et il est DIT. (5) svmLeftNeighbor (la garde de
# transPopover) et dzmVoisins s'accordent sur V1 (meme tolerance 0,1 s) : la
# couche est la seule mesure de la jonction, comme pour le roll a la souris.
# Rangee TOUJOURS rendue, boutons grises quand la jonction n'est pas deux
# videos en contact (E-12) ; Maj = dix images ; vignette sans image = fond
# (aucun src : pas d'icone cassee). 174 -> 176 ancres ; sonde 146 -> 149.
A_L7G1 = '      window.removeEventListener("keydown",onEsc,!0)}},[transPop]);'
R_L7G1 = (A_L7G1 + '\n'
          '  /* L7 D-3b (24/09/2026, tâche 4-bis) : la jonction en édition — le clip de droite, son voisin de gauche (même mesure\n'
          '     que le roll), les deux secondes de source (dernière image de A, première de B) et la clé qui date les vignettes */\n'
          '  var dzAbJ=transPop?clips.filter(function(k){return k&&k.id===transPop.id})[0]||null:null,'
          'dzAbG=dzAbJ?DzTracks.voisins(clips,dzAbJ).g:null,\n'
          '      dzAbS=DzTracks.abSecs(dzAbG,dzAbJ),'
          'dzAbK=dzAbS?svmSrcKey(dzAbG.src)+"@"+dzAbS.a+"|"+svmSrcKey(dzAbJ.src)+"@"+dzAbS.b:"",\n'
          '      abOk=!!dzAbK,abA=abSt.k===dzAbK?abSt.a:null,abB=abSt.k===dzAbK?abSt.b:null;\n'
          '  /* les deps sont la clé seule : elle encode source ET seconde des deux côtés, un roll ou un autre losange la changent */\n'
          '  x.useEffect(function(){\n'
          '    if(!dzAbK){setAbSt(function(s){return s.k?{a:null,b:null,k:""}:s});return}\n'
          '    var alive=!0;\n'
          '    /* revue 24/09 : le rappel n\'est inscrit qu\'au premier passage (reg) — relu depuis le cache à chaque arrivée, jamais empilé en double */\n'
          '    function lire(reg){if(!alive)return;var cb=reg?lire:null,a=svmThumb(dzAbG.src,dzAbS.a,cb),b=svmThumb(dzAbJ.src,dzAbS.b,cb);setAbSt({a:a,b:b,k:dzAbK})}\n'
          '    lire(!0);return function(){alive=!1}},[dzAbK]);\n'
          '  /* le roll de n images (signé) à la jonction en édition : verrou dit, borne dite, historique avant l\'écriture ;\n'
          '     n/30 : 30 i/s en dur, la cadence du rendu et du juge des jump cuts (revue 24/09 : le roll borné est DIT, k images seulement) */\n'
          '  function abRoll(n){\n'
          '    if(!dzAbJ||!dzAbG)return;\n'
          '    if(trackStRef.current[dzAbJ.tr]&&trackStRef.current[dzAbJ.tr].l){fireNote("Piste "+String(dzAbJ.tr).toUpperCase()+" verrouillée.");return}\n'
          '    var cs=clipsRef.current,r2=DzTracks.roll(cs,dzAbG.id,dzAbJ.id,n/30),q=r2.filter(function(k){return k&&k.id===dzAbJ.id})[0];\n'
          '    var dit=DzTracks.abRollDit(dzAbJ.start,q?q.start:dzAbJ.start,n);\n'
          '    if(!dit.k){fireNote("Jonction à sa borne — chaque plan garde au moins 0,3 s et B ne remonte pas avant le début de sa source.");return}\n'
          '    pushHistory();setClips(r2);setDirty(!0);\n'
          '    if(dit.partiel)fireNote("Borne atteinte : "+Math.abs(dit.k)+" image"+(Math.abs(dit.k)>1?"s":"")+" seulement")}')
A_L7G2 = ('      r.jsxs("div",{className:"svm-fxedit",style:{marginTop:10},children:[\n'
          '        r.jsx("span",{className:"svm-fxeditname",children:"Durée"}),\n'
          '        r.jsx("span",{className:"svm-transbound","aria-hidden":!0,children:"0.1 s"}),')
R_L7G2 = ('      /* L7 D-3b (24/09/2026, tâche 4-bis) : A/B à la jonction — la dernière image du plan gauche, la première du plan\n'
          '         droit (vignettes du navigateur, au 1/30 s près) et le roll d\'une image (Maj : dix) ; rangée TOUJOURS rendue,\n'
          '         grisée quand les deux plans ne sont pas des vidéos en contact */\n'
          '      r.jsxs("div",{className:"svm-abrow",children:[\n'
          '        r.jsx("img",{className:"svm-abthumb",src:abA||void 0,alt:"","data-ab":"a",draggable:!1,title:"A — dernière image du plan de gauche"}),\n'
          '        r.jsx("button",{className:"svm-secbtn svm-abbtn",disabled:!abOk,"aria-disabled":!abOk,'
          'title:"Reculer la jonction d\'une image (Maj : dix) — A raccourcit, B s\'allonge",onClick:function(e){abRoll(e.shiftKey?-10:-1)},children:"◀ −1"}),\n'
          '        r.jsx("button",{className:"svm-secbtn svm-abbtn",disabled:!abOk,"aria-disabled":!abOk,'
          'title:"Avancer la jonction d\'une image (Maj : dix) — A s\'allonge, B raccourcit",onClick:function(e){abRoll(e.shiftKey?10:1)},children:"+1 ▶"}),\n'
          '        r.jsx("img",{className:"svm-abthumb",src:abB||void 0,alt:"","data-ab":"b",draggable:!1,title:"B — première image du plan de droite"})]}),\n'
          + A_L7G2)
# ══ L7 D-19 (24/09/2026, tache 5, moitie CLIENT) — COINS ARRONDIS ET OMBRE PORTEE D'UN OVERLAY ═
# Le backend (37b8d57) lit `radius` (entier 0..200) et `shadow` (0|1) au meme
# niveau que x/y/scale/rotate dans _ov_transform ; poses seuls ils rendent tf
# non-None (chaine transformee plein cadre). Le client fait de MEME : la couche
# rend {radius, shadow} bornes (dzmOvExtra, pur), lus UNE fois dans svmOvTfOf
# (L7e2a/b) -- donc l'inspecteur, l'apercu et le payload voient la meme mesure.
# MESURES contre le plan (qui prevoyait quatre sections L7e1..L7e4) : ONZE
# ancres, toutes LIBRES 1/0/1, parce que (1) svmOvTfAt (.bak:1503) REBATIT un
# objet {x,y,scale,rotate} quand des keyframes existent : sans L7e5, coins et
# ombre disparaissaient de l'apercu des qu'un point etait pose ; (2) liveSync
# (.bak:2751) et le geste (.bak:3003) gardent une SIGNATURE x|y|scale|rotate
# avant d'appeler svmApplyTf : sans L7e6/L7e7b un rayon change n'etait jamais
# re-applique ; (3) le geste (.bak:2984) construit `cur` sans les deux cles :
# les coins sautaient pendant le glisser (L7e7a) ; (4) svmOvTfReset
# (.bak:3119) ne retirait que quatre cles : « plein cadre » gardait un rayon
# que le rendu portait alors en chaine transformee (L7e8). Le rayon de
# l'apercu est ramene a l'echelle affichee par la largeur du cadre (.svm-liveov
# = inset:0 du cadre au ratio du projet ; 1920 de large si paysage, 1080 sinon
# -- la regle de _CANVAS et du canvasW des sous-titres, .bak:4250) ; cadre non
# mesurable : rayon brut, apercu approximatif (date). renderPayload n'emet
# x/y/rotate que hors defaut : un rayon seul part avec o.scale=1 (tf non nul)
# et o.radius -- MESURE par le banc bundle. Les deux champs passent par
# svmOvTfField : historique par rafale de 600 ms (ovHistAt), comme l'opacite.
# Keyframes D-14 : radius/shadow restent STATIQUES (pas dans svmMpField), date.
# 176 -> 187 ancres ; sonde 150 -> 151 (DzTracks.ovExtra dans svmOvTfOf).
A_L7E1 = '        r.jsx("span",{className:"svm-rangeval",children:vOp+" %"})]}),'
R_L7E1 = (A_L7E1 + '\n'
          '      /* L7 D-19 (24/09/2026, tâche 5) : coins arrondis (px du canvas, 0..200) et ombre portée — statiques même avec des\n'
          '         keyframes (D-14) ; écrits par svmOvTfField (historique par rafale de 600 ms, comme l\'opacité) */\n'
          '      r.jsxs("div",{className:"svm-fadegain",children:[\n'
          '        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Coins"}),\n'
          '        fieldNum({min:0,max:200,step:5,value:t.radius||0,\n'
          '          title:"Rayon des coins de l\'overlay en px du canvas (0 = coins droits, 200 au plus) — statique, les keyframes ne l\'animent pas",\n'
          '          "aria-label":"Coins (px)",\n'
          '          onChange:function(e){var v=Number(e.target.value);\n'
          '            if(!isFinite(v))return;svmOvTfField({radius:Math.max(0,Math.min(200,Math.round(v)))})}}),\n'
          '        r.jsx("span",{className:"svm-rangeval",style:{width:"auto"},children:"px"})]}),\n'
          '      r.jsxs("div",{className:"svm-fadegain",children:[\n'
          '        r.jsx("span",{className:"svm-fxeditname",style:{width:50},children:"Ombre"}),\n'
          '        r.jsxs("label",{className:"svm-delrange svm-ovshadow",'
          'title:"Ombre portée sous l\'overlay (noir à 55 %, décalée de 6 px au rendu) — statique, retirée par « plein cadre »",children:[\n'
          '          r.jsx("input",{type:"checkbox",checked:!!t.shadow,"aria-label":"Ombre portée",'
          'onChange:function(e){svmOvTfField({shadow:e.target.checked?1:0})}})," portée"]})]}),')
A_L7E2A = '  if(!c||(c.x==null&&c.y==null&&c.scale==null&&c.rotate==null))return null;'
R_L7E2A = ('  /* L7 D-19 (24/09/2026) : un rayon > 0 ou une ombre matérialisent aussi l\'état « transformé » — le rendu fait de même\n'
           '     (plein cadre par défaut) ; la couche borne les deux (entier 0..200, 0|1) */\n'
           '  var ex=DzTracks.ovExtra(c);\n'
           '  if(!c||(c.x==null&&c.y==null&&c.scale==null&&c.rotate==null&&!ex.radius&&!ex.shadow))return null;')
A_L7E2B = '          rotate:Math.min(180,Math.max(-180,n(c.rotate,0)))}}'
R_L7E2B = ('          rotate:Math.min(180,Math.max(-180,n(c.rotate,0))),\n'
           '          radius:ex.radius,shadow:ex.shadow}}')
A_L7E3 = '            if(Math.abs(tf.rotate)>=.05)o.rotate=tf.rotate}'
R_L7E3 = ('            if(Math.abs(tf.rotate)>=.05)o.rotate=tf.rotate;\n'
          '            /* L7 D-19 : coins et ombre, joints seulement hors défaut (tf est non nul dès que l\'un des deux est posé) */\n'
          '            if(tf.radius>0)o.radius=tf.radius;if(tf.shadow)o.shadow=1}')
A_L7E4A = '    el.style.transform="translate(-50%,-50%) rotate("+tf.rotate+"deg)"}'
R_L7E4A = ('    el.style.transform="translate(-50%,-50%) rotate("+tf.rotate+"deg)";\n'
           '    /* L7 D-19 : coins et ombre de l\'aperçu — le rayon (px d\'un canvas de 1920 de large en paysage, 1080 sinon) est ramené\n'
           '       à l\'échelle affichée par la largeur du cadre ; cadre non mesurable (volet caché) : rayon brut, aperçu approximatif */\n'
           '    var rad=tf.radius||0,pe=el.parentElement,pw=pe?pe.clientWidth:0,pk=pw>0?pw/(pw>pe.clientHeight?1920:1080):1;\n'
           '    el.style.borderRadius=rad>0?Math.round(rad*pk*100)/100+"px":"";\n'
           '    el.style.boxShadow=tf.shadow?"6px 6px 12px rgba(0,0,0,.55)":""}')
A_L7E4B = '    el.style.left="";el.style.top="";el.style.width="";el.style.transform=""}}'
R_L7E4B = ('    el.style.left="";el.style.top="";el.style.width="";el.style.transform="";\n'
           '    el.style.borderRadius="";el.style.boxShadow=""}}')
A_L7E5 = '          rotate:mr==null?base.rotate:Math.min(180,Math.max(-180,mr))}}'
R_L7E5 = ('          rotate:mr==null?base.rotate:Math.min(180,Math.max(-180,mr)),\n'
          '          /* L7 D-19 : coins et ombre restent la statique — jamais keyframés */\n'
          '          radius:base.radius||0,shadow:base.shadow||0}}')
A_L7E6 = '      var tsig=ktf?ktf.x+"|"+ktf.y+"|"+ktf.scale+"|"+ktf.rotate:"";'
R_L7E6 = ('      /* L7 D-19 : coins et ombre entrent dans la signature — un rayon changé est ré-appliqué */\n'
          '      var tsig=ktf?ktf.x+"|"+ktf.y+"|"+ktf.scale+"|"+ktf.rotate+"|"+(ktf.radius||0)+"|"+(ktf.shadow||0):"";')
A_L7E7A = '    var cur={id:k.id,x:t0.x,y:t0.y,scale:t0.scale,rotate:t0.rotate};'
R_L7E7A = ('    /* L7 D-19 : le geste garde coins et ombre à l\'aperçu (jamais écrits par lui : p ne porte que x/y/scale/rotate) */\n'
           '    var cur={id:k.id,x:t0.x,y:t0.y,scale:t0.scale,rotate:t0.rotate,radius:t0.radius||0,shadow:t0.shadow||0};')
A_L7E7B = '      if(el2){var tsig=cur.x+"|"+cur.y+"|"+cur.scale+"|"+cur.rotate;'
R_L7E7B = '      if(el2){var tsig=cur.x+"|"+cur.y+"|"+cur.scale+"|"+cur.rotate+"|"+(cur.radius||0)+"|"+(cur.shadow||0);'
A_L7E8 = '      delete nk.x;delete nk.y;delete nk.scale;delete nk.rotate;'
R_L7E8 = (A_L7E8 + '\n'
          '      delete nk.radius;delete nk.shadow; /* L7 D-19 : plein cadre = sans coins ni ombre (la chaîne cover du rendu les ignorerait) */')
# ══ L7-B D-40 (revue du 24/09/2026) — L'APERCU DU CADRAGE, VIDEO OU IMAGE DU FOND V1 ═══════════
# T4 posait l'apercu dans R_DZ3 (dans `if(lv&&c){`) : une IMAGE sur V1 n'y passe jamais (liveVideoRef
# n'est pose que pour une video). Section propre, AVANT le commentaire des overlays V2 (1/0/1 dans
# .bak_montage, mesure) : `lv`, `c`, `t` et `host` du lecteur sont connus ; l'element est la <video>
# active, sinon l'<img> du fond. Dimensions de l'element (videoWidth||naturalWidth), cadre = la boite de
# l'element ; la couche rend « p% 50% » ou "" (pas de cadrage, source pas plus large, cadre non mesure).
# Ecrite seulement si elle change ; "" rend la position par defaut (l'element du pool est reutilise).
A_L7BRF1 = "    /* overlays V2 actifs à t, au-dessus du fond, opacité appliquée */"
R_L7BRF1 = ("    /* L7-B D-40 : le cadrage EN DIRECT -- la fenetre du crop du rendu, a la tete en temps de source,\n"
            "       sur la <video> active ou l'<img> du fond V1 */\n"
            '    var rfEl=c?(lv||(host.firstChild&&host.firstChild.tagName==="IMG"?host.firstChild:null)):null;\n'
            "    if(rfEl){var rfP=DzTracks.reframeCss(c,(t-c.start)*svmSpeedOf(c),rfEl.videoWidth||rfEl.naturalWidth,\n"
            "      rfEl.videoHeight||rfEl.naturalHeight,rfEl.clientWidth,rfEl.clientHeight);\n"
            "      if(rfEl.style.objectPosition!==rfP)rfEl.style.objectPosition=rfP}\n"
            + A_L7BRF1)
L7A = [("L7a3-preset-resolve-export-import-du-mappage", A_L7A3, R_L7A3),
       ("L7b3-le-texte-selectionne-garde-son-Ctrl-C", A_L7B3, R_L7B3),
       ("L7c3-popover-plans-trop-longs-jump-cuts", A_L7C3, R_L7C3),
       ("L7g1-jonction-en-edition-vignettes-A-B-et-abRoll", A_L7G1, R_L7G1),
       ("L7g2-rangee-A-B-du-popover-de-jonction", A_L7G2, R_L7G2),
       ("L7e1-inspecteur-coins-et-ombre", A_L7E1, R_L7E1),
       ("L7e2a-svmOvTfOf-garde-radius-shadow", A_L7E2A, R_L7E2A),
       ("L7e2b-svmOvTfOf-porte-radius-shadow", A_L7E2B, R_L7E2B),
       ("L7e3-renderPayload-emet-radius-shadow", A_L7E3, R_L7E3),
       ("L7e4a-svmApplyTf-apercu-coins-et-ombre", A_L7E4A, R_L7E4A),
       ("L7e4b-svmApplyTf-retour-au-cover", A_L7E4B, R_L7E4B),
       ("L7e5-svmOvTfAt-garde-la-statique", A_L7E5, R_L7E5),
       ("L7e6-liveSync-signature", A_L7E6, R_L7E6),
       ("L7e7a-geste-cur-porte-radius-shadow", A_L7E7A, R_L7E7A),
       ("L7e7b-geste-signature", A_L7E7B, R_L7E7B),
       ("L7e8-reset-retire-radius-shadow", A_L7E8, R_L7E8)]
_L7E = [t for t in L7A if t[0].startswith("L7e")]
# deux remplacements CONTIENNENT leur ancre (e1, e8 : ajout apres) ; les neuf autres la REECRIVENT (meme tete de ligne)
assert len(_L7E) == 11 and sum(t[1] in t[2] for t in _L7E) == 2 and R_L7E1.startswith(A_L7E1) and R_L7E8.startswith(A_L7E8)
# les neuf autres gardent la TETE de leur ancre (apres un eventuel commentaire de tete) : la ligne n'est pas remplacee par autre chose
assert all(t[1].lstrip()[:20] in t[2] for t in _L7E)
assert R_L7E1.count("fieldNum(") == 1 and R_L7E1.count('type:"checkbox"') == 1 and R_L7E1.count("title:") == 2 and R_L7E1.count("svmOvTfField(") == 2
assert R_L7E1.count("svmOvTfField({radius:") == 1 and R_L7E1.count("svmOvTfField({shadow:e.target.checked?1:0})") == 1 and R_L7E1.count("svmMpField(") == 0 and R_L7E1.count("DzTracks") == 0
assert R_L7E2A.count("DzTracks.ovExtra(c)") == 1 and R_L7E2A.count("&&!ex.radius&&!ex.shadow))return null;") == 1 and R_L7E2B.count("radius:ex.radius,shadow:ex.shadow}}") == 1
assert R_L7E3.count("if(tf.radius>0)o.radius=tf.radius;if(tf.shadow)o.shadow=1}") == 1 and R_L7E3.count("o.radius=") == 1 and R_L7E3.count("o.shadow=1") == 1
assert R_L7E4A.count("el.style.borderRadius=") == 1 and R_L7E4A.count('el.style.boxShadow=tf.shadow?"6px 6px 12px rgba(0,0,0,.55)":""') == 1 and R_L7E4A.count("?1920:1080") == 1
assert R_L7E4B.count('el.style.borderRadius="";el.style.boxShadow=""') == 1 and R_L7E5.count("radius:base.radius||0,shadow:base.shadow||0}}") == 1
assert R_L7E6.count('+"|"+(ktf.radius||0)+"|"+(ktf.shadow||0)') == 1 and R_L7E7B.count('+"|"+(cur.radius||0)+"|"+(cur.shadow||0)') == 1
assert R_L7E7A.count("radius:t0.radius||0,shadow:t0.shadow||0}") == 1 and R_L7E8.count("delete nk.radius;delete nk.shadow;") == 1
assert sum(t[2].count("DzTracks") for t in _L7E) == 1
# ══ L7 D-22 (24/09/2026, tache 6) — PISTES DE SOUS-TITRES PAR LANGUE, UNE SEULE GRAVEE ═
# Perimetre MINIMAL et date (decision n°7) : une piste S2… est une copie de S1 (traduite par le tiroir, case
# « nouvelle piste » -- replis R_M26A/R_M26B/R_M24H ; ou vide -- menu de piste, repli R_EC1) ; ses repliques sont
# des clips tr:"s2" ; l'EDITEUR reste sur S1. MESURE : subsSegsOf (.bak:3540) a NEUF appelants (verdict,
# couverture, emojis, tiroir, overlay, chip…) -- on ne change que subsPayload (L7f1) : la piste GRAVEE est
# DzTracks.subsBurnId(pistes) (la marquee burn:true, sinon "s1" -- le comportement d'avant a l'octet pres).
# L7f2 : data-sub par GENRE (trackKind, comme le plan) + data-burn CALCULE par subsBurnId et non lu sur tr.burn
# (ecart au plan, date : sans marque, s1 est gravee et doit le montrer -- tr.burn est absent par defaut).
# Les deux ancres sont LIBRES 1/0/1 dans .bak_montage ; les trois autres sites sont des replis (ancres nees de
# remplacements). Backend : _tracks_meta accepte tout kind et ignore lang/burn/name (mesure, rien ne change).
A_L7F1 = '    var segs=d.sort(subsSegsOf(clipsRef.current)).filter(function(s){'
R_L7F1 = ('    /* L7 D-22 (24/09/2026, tâche 6) : seule la piste de sous-titres marquée « gravée » part au rendu (s1 sans marque —\n'
          "       subsBurnId de la couche) ; l'éditeur, le verdict, la couverture et les emojis restent sur s1 (subsSegsOf, inchangé) */\n"
          '    var bid=DzTracks.subsBurnId(svmTracksOf(proj));\n'
          '    var segs=d.sort((clipsRef.current||[]).filter(function(c){return c.tr===bid})).filter(function(s){')
A_L7F2 = '            return r.jsxs("div",{className:"svm-track","data-sub":tr.id==="s1"?"":void 0,'
R_L7F2 = ('            /* L7 D-22 (24/09/2026) : data-sub par genre (S2… aussi), data-burn sur la piste que le rendu grave (s1 sans marque) */\n'
          '            return r.jsxs("div",{className:"svm-track","data-sub":trackKind(tr.id)==="subs"?"":void 0,'
          '"data-burn":trackKind(tr.id)==="subs"&&DzTracks.subsBurnId(svmTracksOf(proj))===tr.id?"":void 0,')
# Revue T6 (24/09/2026) : (1) l'APERCU VIVANT (subsOverlay) lisait subsSegsOf(clips) = s1 alors que Preview et
# Rendu gravent la piste marquee -- il filtre par subsBurnId lui aussi (L7f5 ; ancre sur QUATRE lignes : la ligne
# `var segs=subsSegsOf(clips);` existe deux fois dans le .bak, subsOverlay et le lecteur karaoke) ; l'editeur, le
# verdict, la couverture et les emojis restent sur s1 (date : subsSegsOf( x7 ailleurs). (2) `data-hidden` ne se
# posait que sur s1 : un clip s2 masque se dessinait normal et ne partait pas au rendu sans signe -- par genre
# (L7f6, comme data-sub). Ancres libres 1/0/1.
A_L7F5 = ('  function subsOverlay(){\n'
          '    var d=subsLayer();\n'
          '    if(!d||!d.Overlay)return null;\n'
          '    var segs=subsSegsOf(clips);')
R_L7F5 = ('  function subsOverlay(){\n'
          '    var d=subsLayer();\n'
          '    if(!d||!d.Overlay)return null;\n'
          "    /* L7 D-22 (revue T6, 24/09/2026) : l'aperçu montre la piste que le rendu grave (subsBurnId) — l'éditeur reste sur s1 */\n"
          '    var dzBid=DzTracks.subsBurnId(svmTracksOf(proj));\n'
          '    var segs=(clips||[]).filter(function(c){return c.tr===dzBid});')
A_L7F6 = '                    "data-hidden":tr.id==="s1"&&c.hidden?"":void 0,'
R_L7F6 = '                    "data-hidden":trackKind(tr.id)==="subs"&&c.hidden?"":void 0, /* L7 D-22 (revue T6) : masqué se voit sur toute piste subs */'
L7A += [("L7f1-subsPayload-grave-la-piste-marquee", A_L7F1, R_L7F1),
        ("L7f2-data-sub-par-genre-et-data-burn", A_L7F2, R_L7F2),
        ("L7f5-subsOverlay-montre-la-piste-gravee", A_L7F5, R_L7F5),
        ("L7f6-data-hidden-sur-toute-piste-subs", A_L7F6, R_L7F6)]
assert R_L7F5.startswith(A_L7F5[:A_L7F5.rfind("\n")]) and R_L7F5.count("subsSegsOf(") == 0 and R_L7F5.count("DzTracks.subsBurnId(svmTracksOf(proj))") == 1 and R_L7F5.count("c.tr===dzBid") == 1
assert R_L7F6.count('trackKind(tr.id)==="subs"&&c.hidden') == 1 and R_L7F6.count('tr.id==="s1"') == 0
assert R_L7F1.count("DzTracks.subsBurnId(svmTracksOf(proj))") == 1 and R_L7F1.count("subsSegsOf(") == 0 and R_L7F1.count("subsSegsOf") == 1 and R_L7F1.count("c.tr===bid") == 1 and A_L7F1 not in R_L7F1
assert R_L7F2.count('"data-burn":') == 1 and R_L7F2.count('trackKind(tr.id)==="subs"') == 2 and R_L7F2.count('tr.id==="s1"') == 0 and R_L7F2.count("DzTracks.subsBurnId(") == 1
assert R_EC1.count("DzTracks.subsBurnId(ts)") == 1 and R_EC1.count("DzTracks.subsBurn(ts,id)") == 1 and R_EC1.count("DzTracks.subsNew(ts,lg)") == 1 and R_EC1.count("window.prompt(") == 1
assert R_EC1.count('lbl:"Exporter .srt"') == 1 and R_EC1.count('lbl:"Exporter .vtt"') == 1 and R_EC1.count('lbl:"Exporter .txt"') == 1 and R_EC1.count('"Nouvelle piste de langue…"') == 1
assert R_EC1.count('combo:bid===id?"gravée":""') == 1 and R_EC1.count("subsToSrt(") == 1 and R_EC1.count("subsToVtt(") == 1 and R_EC1.count("subsToTxt(") == 1 and R_EC1.count("subsDownload(") == 2
# L7-B D-37 (24/09/2026) : subsDownload x2 dans R_EC1 -- D-22 (la piste) + dzExportTl (repli L7Ba) ;
# le geste d'export : sauvegarde PUIS export, deux entrees de la rubrique Projet, un seul appel chacune
assert R_EC1.count("function dzExportTl(fmt){") == 1 and R_EC1.count('run:function(){dzExportTl("edl")}') == 1 and R_EC1.count('run:function(){dzExportTl("fcpxml")}') == 1
assert R_EC1.count('fetch("/api/montage/export?format="+fmt)') == 1 and R_EC1.count("JSON.stringify(svmSavePayload())") == 1 and R_EC1.find("function dzExportTl(fmt){") < R_EC1.find("  function dzMenuProps(kind,o){")
# L7-B D-42 (24/09/2026) : le geste « Decouper aux changements de plan » et son entree du menu de clip, repliés dans R_EC1
assert R_EC1.count("  function dzSceneCut(id){") == 1 and R_EC1.count("run:function(){dzSceneCut(id)}") == 1 and R_EC1.count('fetch("/api/montage/scenes",') == 1
# L7-B D-40 (24/09/2026, tache 4) : le cadrage replie dans R_DZ1 (hote), R_DZ3 (apercu vivant), R_DZ4 (payload) -- aucune section neuve
assert R_DZ1.count("onReframe:function(){var id=sel.id,") == 1 and R_DZ1.count('fetch("/api/montage/reframe",') == 1 and R_DZ1.count("var sg=dzRfSg(c),") == 1
assert R_DZ1.find("var sg=dzRfSg(c),") < R_DZ1.find('fetch("/api/montage/reframe",') < R_DZ1.find("if(dzRfSg(k2)!==sg){") < R_DZ1.find("pushHistory();setClips(clipsRef.current.map(")
# L5 (24/09/2026, tache 5) : 3 -> 4 `DzTracks.` (GradePanel) ; DZ1 ne FINIT plus par ovInspector() -- le panneau
# Etalonnage vient juste APRES (meme garde) ; l'adjacence PlanProps -> ovInspector() reste, une fois.
assert R_DZ1.count("DzTracks.") == 4 and R_DZ1.count("          onChange:dzPlanSet}):null,\n" + A_DZ1 + "\n") == 1 and R_DZ1.count("pl.get(livePoolKey(sel.src,\"b\"))") == 1
assert R_DZ1.endswith('onNote:fireNote,onChange:dzPlanSet}):null,') and R_DZ1.count('?r.jsx(DzTracks.GradePanel,{clip:sel,') == 1
assert R_DZ1.count('sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id?r.jsx(DzTracks.') == 2
assert R_DZ2.count("r.jsx(DzTracks.MaskBox,{clip:sel})") == 1 and R_DZ2.find("DzTracks.MaskBox") < R_DZ2.find("DzTracks.DzRects")
assert R_DZ4.count("DzTracks.maskOf(c.mask);if(mkD)o.mask=mkD;") == 1 and R_DZ4.find("var rfD=") < R_DZ4.find("var mkD=")
assert R_DZ3.count("reframe") == 0 and R_DZ3.endswith("if(lv.style.transform!==dzT)lv.style.transform=dzT;")
assert R_DZ1.count("svmSrcKey(k.src)") == 1 and R_EC1.count(",svmSrcKey(k.src)].join(\"|\")}") == 1
assert R_L7BRF1.startswith(A_L7BRF1) is False and R_L7BRF1.endswith(A_L7BRF1) and R_L7BRF1.count("DzTracks.reframeCss(c,(t-c.start)*svmSpeedOf(c),") == 1
assert R_L7BRF1.count('if(rfEl.style.objectPosition!==rfP)rfEl.style.objectPosition=rfP}') == 1 and R_L7BRF1.count("DzTracks") == 1
assert R_DZ4.count('var rfD=c.tr==="v1"&&DzTracks.reframePayload(c);if(rfD)o.reframe=rfD;') == 1 and R_DZ1.count("var si=Number(c.srcIn)||0,pts=") == 1 and R_DZ4.find("var sbD=") < R_DZ4.find("var rfD=")
assert R_EC1.count("var sg=dzSg(c);") == 1 and R_EC1.count("if(k2&&dzSg(k2)!==sg){") == 1 and R_EC1.find("if(k2&&dzSg(k2)!==sg){") < R_EC1.find("DzTracks.cutAt(clipsRef.current,id,")
assert R_EC1.count("DzTracks.cutAt(clipsRef.current,id,") == 1 and R_EC1.count("DzTracks.cutOpts(proj,trackStRef.current)") == 1 and R_EC1.count("pushHistory();setClips(r2.clips);setDirty(!0);") == 1
assert R_EC1.find("  function dzSceneCut(id){") < R_EC1.find("  function dzMenuProps(kind,o){") < R_EC1.find('lbl:"Couper à la tête"') < R_EC1.find('lbl:"Découper aux changements de plan"') < R_EC1.find('lbl:"Supprimer",combo:')
assert R_M26A.count("x.useState(!1),dzNewTr=s9c[0],setDzNewTr=s9c[1];") == 1 and R_M26A.count("props.onNewTrack(dzTo,dzNext)") == 1 and R_M26A.count("if(props.onChange)props.onChange(dzNext,!0);") == 1
assert R_M26B.count('"aria-label":"Traduire dans une nouvelle piste"') == 1 and R_M26B.count("sub-trnew") == 1 and R_M26B.count("dzNewTr?") == 1 and R_M26B.count("title:") == 2
assert R_M24H.count("onNewTrack:function(lang,segs){") == 1 and R_M24H.count("DzTracks.subsNew(svmTracksOf(dzProjRef.current),lang)") == 1 and R_M24H.count("svmTracksOf(proj)") == 1 and R_M24H.count('DzTracks.subsCopy(cs,"s1",r2.id,segs)') == 1
assert R_L7G1.startswith(A_L7G1) and R_L7G1.count("svmThumb(") == 2 and R_L7G1.count("DzTracks.voisins(") == 1 and R_L7G1.count("DzTracks.abSecs(") == 1
# revue 24/09 : abRollDit (quatrieme reference), trois fireNote (verrou, borne, partiel), rappel inscrit UNE fois (reg)
assert R_L7G1.count("DzTracks.roll(") == 1 and R_L7G1.count("DzTracks.abRollDit(") == 1 and R_L7G1.count("DzTracks") == 4 and R_L7G1.count("fireNote(") == 3 and R_L7G1.count("},[dzAbK]);") == 1
assert R_L7G1.find("pushHistory();") < R_L7G1.find("setClips(r2)") < R_L7G1.find("setDirty(!0);") < R_L7G1.find("if(dit.partiel)fireNote(") and R_L7G1.count("pushHistory(") == 1
assert R_L7G1.count("cb=reg?lire:null") == 1 and R_L7G1.count(",cb)") == 2 and R_L7G1.count("lire(!0);") == 1 and R_L7G1.count(",lire)") == 0
assert R_L7G2.endswith(A_L7G2) and R_L7G2.count("title:") == 4 and R_L7G2.count('className:"svm-abthumb"') == 2 and R_L7G2.count("DzTracks") == 0
assert R_L7G2.count('disabled:!abOk,"aria-disabled":!abOk,') == 2 and R_L7G2.count("abRoll(e.shiftKey?") == 2 and R_L7G2.count("svm-abrow") == 1
assert _EB7_ETAT.endswith('  var stAb=x.useState({a:null,b:null,k:""}),abSt=stAb[0],setAbSt=stAb[1];') and _EB7_ETAT.count("abSt") == 1
assert A_L7C3 in R_L7C3 and R_L7C3.endswith('    if(pop==="boring")return boringPopover();') and R_L7C3.count("function boringPopover(){") == 1
# L7 D-39 (24/09/2026, tache 4) : la garde `diff` (UNE reference DzTracks.DiffView) precede la garde boring
assert R_L7C3.count("title:") == 4 and R_L7C3.count('localStorage.setItem("dz_svm_boring",') == 1 and R_L7C3.count("DzTracks") == 1
assert R_L7C3.count('    if(pop==="diff")return diffSt?r.jsx(DzTracks.DiffView,Object.assign({onClose:function(){setPop("")}},diffSt)):null;\n    if(pop==="boring")return boringPopover();') == 1
assert R_M14.count("onDiff:function(p){") == 1 and R_M14.count("DzTracks.diff(") == 1 and R_M14.count('fetch("/api/montage/projects/"+') == 1 and R_M14.count("setDiffSt(") == 1 and R_M14.count('setPop("diff")') == 1
# MESURE : quatre DzTracks dans _EB7_ETAT (tlH x2 de E-9, boringDef + boring de L7c1) -- l'etat diffSt n'en ajoute aucun
assert _EB7_ETAT.count("var stDf=x.useState(null),diffSt=stDf[0],setDiffSt=stDf[1];") == 1 and _EB7_ETAT.count("DzTracks") == 4
assert R_L7C3.count('className:"svm-transdur",type:"number"') == 2 and R_L7C3.count("boSet(") == 3 and R_L7C3.count("e.stopPropagation()") == 1
assert _EB7_ETAT.count("DzTracks.boringDef") == 1 and _EB7_ETAT.count("DzTracks.boring(") == 1 and _EB7_ETAT.count('localStorage.getItem("dz_svm_boring")') == 1
assert R_AJ6A.count('"data-boring":boMap[c.id]||void 0,') == 1 and R_EC1.count('run:function(){setPop("boring")}') == 1 and R_EC1.count('?"✓":""') == 5
assert R_L7B3.count("window.getSelection") == 2 and R_L7B3.startswith(A_L7B3.split("\n")[0]) and R_L7B3.endswith(A_L7B3.split("\n")[2])
assert R_L7A3.endswith(A_L7A3) and R_L7A3.count("svm-kbio") == 3 and R_L7A3.count("title:") == 3
assert R_L7A3.count("setKmOv(") == 2 and R_L7A3.count("svmKmSave(") == 2 and R_L7A3.count("fireNote(") == 7
assert R_L7A3.count('subsDownload("deepotus-raccourcis.json",') == 1 and R_L7A3.count("SVM_ACTIONS,svmComboCanon,svmComboReserved") == 1
assert R_R1.count('id:"trans_add"') == 1 and R_R2.count('svmSetTransType(dzTc.id,"fade")') == 1 and R_R2.count("DzTracks.voisins(") == 1
# L7 D-6 (24/09/2026, tache 2) : deux actions (L7b1, repli R_R1) et deux branches (L7b2, repli R_R2) -- aucune
# section neuve (les ancres du plan sont consommees) ; le presse-papiers est lu x1 / ecrit x1, en try/catch
assert R_R1.count('id:"copy"') == 1 and R_R1.count('id:"paste"') == 1 and R_R1.count('combo:"Ctrl+C"') == 1 and R_R1.count('combo:"Ctrl+V"') == 1
assert R_R2.count('if(id==="copy"){') == 1 and R_R2.count('if(id==="paste"){') == 1 and R_R2.count("DzTracks.clipCopy(") == 1 and R_R2.count("DzTracks.clipPaste(") == 1
assert R_R2.count('localStorage.setItem("dz_montage_clipboard",') == 1 and R_R2.count('localStorage.getItem("dz_montage_clipboard")') == 1 and R_R2.count("dz_montage_clipboard") == 2
assert R_R2.find('if(id==="trans_add"){') < R_R2.find('if(id==="copy"){') < R_R2.find('if(id==="paste"){')
assert R_R2.find("ovSeq.current=dzPq;pushHistory();setClips(dzPr.clips);setSelId(dzPr.id);setDirty(!0);") > 0
assert R_L4C2.count("DzTracks.deliverPayload(") == 1 and R_L4B.count("DzTracks.DeliverRow") == 1 and R_L4B.count("DzTracks.rangeFrom(") == 1
assert R_L4D3.count("o.d.queued") == 1 and R_L4D1.startswith("    if(!queue)setJob(") and R_L4C2.count("queue:queue===!0") == 1
assert R_M16REF.count("dz_montage_deliver") == 2 and R_M16REF.count("/api/montage/deliver-presets") == 2 and R_M16REF.count("window.prompt(") == 1
assert R_M16REF.count("rangeOnly:void 0") == 1 and R_M16REF.count("delete v.rangeOnly;") == 1

EC15 = [("EC15a-title-fermer-popover-de-rendu", A_EC15A, R_EC15A),
        ("EC15b-bouton-or-reessayer-grise-sur-la-demo", A_EC15B, R_EC15B),
        ("EC15c-bouton-or-rendre-grise-sur-la-demo", A_EC15C, R_EC15C),
        ("EC15d-title-fermer-selecteur-effets", A_EC15D, R_EC15D),
        ("EC15e-title-fermer-selecteur-overlay", A_EC15E, R_EC15E),
        ("EC15f-title-fermer-raccourcis", A_EC15F, R_EC15F),
        ("EC15g-title-retirer-effet", A_EC15G, R_EC15G),
        ("EC15h-title-raccourcis-oui", A_EC15H, R_EC15H),
        ("EC15i-title-raccourcis-non", A_EC15I, R_EC15I),
        ("EC15j-title-narration-non", A_EC15J, R_EC15J),
        ("EC15k-bibliotheque-grisee-sur-la-demo", A_EC15K, R_EC15K)]
for _n, _a, _r in EC15:
    assert _a != _r and _r.count("title:") == _a.count("title:") + (2 if _n.startswith("EC15k") else 1), _n
assert R_EC15B.count("proj.demo?null:") == 0 and R_EC15K.count("proj.demo?null:") == 0
assert R_EC15B.count("disabled:proj.demo,") == 1 and R_EC15K.count('svm-libbtn",disabled:proj.demo,') == 1
assert R_EC15C.count("disabled:busy||proj.demo,") == 1 and R_EC15C.count("(busy||proj.demo)?") == 1
assert R_EB4.count("title:") == 1 and R_EA5D.count('"Rendre →"') == 1 and R_EA5D.count("title:") == 2

# ══ L5 D-31 D-32 (24/09/2026, tache 6) — SCOPES, LIGHTBOX, COPIER / COLLER LE GRADE ══════════════════════════
# Replis : les deux actions (R_R1), leur dispatch (R_R2), la rubrique « Édition » (DZM_MENU_RUB, couche), l'etat de
# la lightbox + les gestes du grade + l'entree ☰ › Affichage + les deux entrees du menu de clip (R_EC1), la lightbox
# rendue (R_EB5A), Echap (R_K7). UNE section neuve, parce qu'aucun remplacement ne touche la zone du lecteur :
# L5sc1 -- LES SCOPES SOUS LA BARRE DU LECTEUR. ANCRE MESUREE 24/09/2026 : la fin du bouton « plein ecran » qui
# ferme `.svm-playerbar` puis `.svm-playerzone` vaut 1/0/1 (x1 dans .bak_montage, touchee par aucune section, x1
# dans le bundle livre). Le composant (DzTracks.Scopes) devient le DERNIER enfant de `.svm-playerzone` : sous la
# barre en paysage (colonne), a droite de la barre en portrait (data-side, rangee). Props : la timeline, la tete,
# l'etat de lecture (st4 du bundle : `playing`) -- les scopes ne demandent RIEN pendant la lecture.
# CORRECTIF PREUVE ECRAN (24/09/2026) : MESURE Playwright 1400 x 900 -- sous la barre, la puce tombait sous la barre
# OUTILS flottante (z 8, pied de la zone). Meme ancre, la puce devient le DERNIER enfant de la BARRE (apres « plein
# ecran ») ; la barre passe en tete de la zone par la feuille (order:-1) et l'encart est porte dans le cadre.
A_L5SC1 = '            onClick:svmFullscreen,children:"plein écran ("+svmKeyLabel("fullscreen")+")"})]})]}),'
R_L5SC1 = ('            onClick:svmFullscreen,children:"plein écran ("+svmKeyLabel("fullscreen")+")"}),\n'
           '          /* L5 D-31 : la puce des scopes du plan V1 sous la tête (bascule mémorisée, encart dans le cadre) */\n'
           '          r.jsx(DzTracks.Scopes,{clips:clips,head:ph,playing:playing})]})]}),')
L5 = [("L5sc1-scopes-sous-la-barre-du-lecteur", A_L5SC1, R_L5SC1)]
assert R_L5SC1.count("DzTracks.") == 1 and R_L5SC1.endswith("playing:playing})]})]}),") and A_L5SC1.count("]})]}),") == 1
assert R_R1.count('combo:"Ctrl+Alt+C"') == 1 and R_R1.count('combo:"Ctrl+Alt+V"') == 1 and R_R1.find('id:"paste"') < R_R1.find('id:"grade_copy"') < R_R1.find('id:"grade_paste"')
assert R_R2.count('if(id==="grade_copy"){dzGradeCopy(selRef.current);return}') == 1 and R_R2.count('if(id==="grade_paste"){dzGradePaste(selRef.current);return}') == 1
assert R_EC1.count("function dzGradeCopy(id){") == 1 and R_EC1.count("function dzGradePaste(id){") == 1 and R_EC1.count("pushHistory();setClips(clipsRef.current.map(function(k){return k.id===c.id?q.clip:k}))") == 1
assert R_EC1.count("run:function(){dzGradeCopy(id)}") == 1 and R_EC1.count("run:function(){dzGradePaste(id)}") == 1 and R_EC1.count('{lbl:"Lightbox des plans",run:function(){setDzLb(!0)}}') == 1
assert R_EB5A.count("r.jsx(DzTracks.Lightbox,") == 1 and R_K7.count('if(dzLbRef.current){if(e.key==="Escape"){e.preventDefault();setDzLb(!1)}return}') == 1 and R_K7.startswith("if(dzLbRef.current){")

# ══ L6 D-23 D-25 (25/09/2026, tache 5) — RACK ETENDU, « APPRENDRE LE BRUIT », ECOUTE RENDUE DU SON D'UN PLAN ══════════
# PREMIERE FOIS que des sections du patcher montage entrent dans le bloc SFXSTUDIO (rack SvxRack, SVX_FX_DEFS,
# svxCleanParams, svxModSummary, paramRow) : le maillon amont `sfxstudio` n'a PAS de .bak dans cette copie, sa source
# frontend/patches/sfxstudio.js est INTOUCHABLE -- le bloc se patche ici, depuis .bak_montage, a chaque rejeu. Les ancres
# L6fx1..L6fx5 sont donc des LIGNES DE sfxstudio.js telles que .bak_montage les porte : un maillon amont reconstruit
# depuis une source modifiee doit garder ces lignes, sinon le --check le dit (ancre 0) -- jamais en silence.
# ANCRES MESUREES 25/09/2026 : les sept valent 1/0/1 (x1 dans .bak_montage, touchees par aucune section, x1 livrees).
# MESURES qui decident de la forme (lecture du bloc, 25/09) :
#   * svxCleanParams NE GARDE QUE les params DECLARES et arrondit a 1 decimale (`pd.step<1?1:0`) : learn_in / learn_out
#     etaient PERDUS a la premiere retouche d'un curseur du debruiteur -> declares, caches (`hide:1`, paramRow rend null)
#     et arrondis au MILLIEME (`dec:3`, lu par L6fx3 ; les params sans `dec` gardent la regle d'avant, octet pour octet) ;
#   * un `seg` NUMERIQUE ne marche pas : svxCleanParams compare String(v) a o[0] en strict (un 60 nombre retombe sur le
#     defaut) et paramRow ecrit « Mode » / « Mode du filtre » en dur -> `dehum.base` est un CURSEUR 50..60 pas 10 (le
#     constructeur backend arrondit : >= 55 -> 60) ;
#   * le graphe Web Audio du rack lit des types NOMMES (on.eq3, on.stereo…) : eq6 / dehum y sont ignores -> live:0
#     (« Écouter (rendu) »), comme le plan le fixe.
# ORDRE D'AFFICHAGE = ORDRE DE CHAINE (_FX_ORDER de sfx_service) : « Anti-ronflement » AVANT l'egaliseur 3 bandes,
# « Égaliseur 6 bandes » APRES le debruiteur. ECART AU PLAN (date 25/09) : le plan posait eq6 ET dehum apres la ligne
# eq3 ; le rack montrant la chaine dans son ordre de rendu, dehum vient avant (svxEmitFx emet dans l'ordre du
# catalogue, le backend retrie de toute facon).
A_L6FX1 = ('   Ordre de chaîne fixe : filter → eq3 → denoise → deesser → compressor →\n'
           '   distortion → echo → reverb → stereo → normalize. live:1 = audible dans\n'
           '   l\'audition Web Audio du rack ; live:0 = « Écouter (rendu) » (ffmpeg). */\n'
           'var SVX_FX_DEFS=[\n'
           ' {type:"filter",label:"Filtre",live:1,params:[\n'
           '   {k:"mode",kind:"seg",opts:[["low","grave"],["high","aigu"],["band","bande"]],d:"low"},\n'
           '   {k:"freq",label:"Fréq",min:20,max:20000,d:1000,step:1,unit:"Hz",log:1},\n'
           '   {k:"q",label:"Q",min:0.1,max:10,d:1,step:0.1,unit:""}]},\n'
           ' {type:"eq3",label:"Égaliseur",live:1,params:[')
R_L6FX1 = ('   Ordre de chaîne fixe : filter → dehum → eq3 → denoise → eq6 → deesser →\n'
           '   compressor → distortion → echo → reverb → stereo → normalize (L6, 25/09/2026 :\n'
           '   dehum et eq6 insérés, ordre relatif des dix d\'avant inchangé). live:1 = audible dans\n'
           '   l\'audition Web Audio du rack ; live:0 = « Écouter (rendu) » (ffmpeg). */\n'
           'var SVX_FX_DEFS=[\n'
           ' {type:"filter",label:"Filtre",live:1,params:[\n'
           '   {k:"mode",kind:"seg",opts:[["low","grave"],["high","aigu"],["band","bande"]],d:"low"},\n'
           '   {k:"freq",label:"Fréq",min:20,max:20000,d:1000,step:1,unit:"Hz",log:1},\n'
           '   {k:"q",label:"Q",min:0.1,max:10,d:1,step:0.1,unit:""}]},\n'
           ' {type:"dehum",label:"Anti-ronflement",live:0,params:[\n'
           '   {k:"base",label:"Secteur",min:50,max:60,d:50,step:10,unit:"Hz"},\n'
           '   {k:"harmonics",label:"Harmon.",min:1,max:6,d:4,step:1,unit:""},\n'
           '   {k:"amount",label:"Dosage",min:0,max:100,d:100,step:1,unit:"%"}]},\n'
           ' {type:"eq3",label:"Égaliseur",live:1,params:[')
# le debruiteur gagne le plancher (visible) et la plage apprise (cachee, au millieme) ; eq6 le suit (ordre de chaine)
A_L6FX2 = (' {type:"denoise",label:"Débruiteur",live:0,params:[\n'
           '   {k:"amount",label:"Réduction",min:0,max:97,d:12,step:1,unit:"dB"}]},')
R_L6FX2 = (' {type:"denoise",label:"Débruiteur",live:0,params:[\n'
           '   {k:"amount",label:"Réduction",min:0,max:97,d:12,step:1,unit:"dB"},\n'
           '   {k:"nf",label:"Plancher 0=auto",min:-80,max:0,d:0,step:1,unit:"dB",tip:"Plancher du débruiteur : 0 = auto, −20 au plus (le rendu ramène −19…−1 à −20)"},\n'
           '   {k:"learn_in",label:"Appris de",min:0,max:86400,d:0,step:0.001,dec:3,unit:"s",hide:1},\n'
           '   {k:"learn_out",label:"Appris à",min:0,max:86400,d:0,step:0.001,dec:3,unit:"s",hide:1}]},\n'
           ' {type:"eq6",label:"Égaliseur 6 bandes",live:0,params:[\n'
           '   {k:"hp_hz",label:"Passe-haut",min:0,max:300,d:0,step:1,unit:"Hz"},\n'
           '   {k:"ls_f",label:"Grave Hz",min:30,max:500,d:100,step:1,unit:"Hz",log:1},\n'
           '   {k:"ls_g",label:"Grave dB",min:-12,max:12,d:0,step:0.5,unit:"dB"},\n'
           '   {k:"p1_f",label:"Cloche 1 Hz",min:40,max:16000,d:250,step:1,unit:"Hz",log:1},\n'
           '   {k:"p1_g",label:"Cloche 1 dB",min:-12,max:12,d:0,step:0.5,unit:"dB"},\n'
           '   {k:"p1_q",label:"Q1",min:0.3,max:8,d:1,step:0.1,unit:""},\n'
           '   {k:"p2_f",label:"Cloche 2 Hz",min:40,max:16000,d:800,step:1,unit:"Hz",log:1},\n'
           '   {k:"p2_g",label:"Cloche 2 dB",min:-12,max:12,d:0,step:0.5,unit:"dB"},\n'
           '   {k:"p2_q",label:"Q2",min:0.3,max:8,d:1,step:0.1,unit:""},\n'
           '   {k:"p3_f",label:"Cloche 3 Hz",min:40,max:16000,d:2500,step:1,unit:"Hz",log:1},\n'
           '   {k:"p3_g",label:"Cloche 3 dB",min:-12,max:12,d:0,step:0.5,unit:"dB"},\n'
           '   {k:"p3_q",label:"Q3",min:0.3,max:8,d:1,step:0.1,unit:""},\n'
           '   {k:"p4_f",label:"Cloche 4 Hz",min:40,max:16000,d:6000,step:1,unit:"Hz",log:1},\n'
           '   {k:"p4_g",label:"Cloche 4 dB",min:-12,max:12,d:0,step:0.5,unit:"dB"},\n'
           '   {k:"p4_q",label:"Q4",min:0.3,max:8,d:1,step:0.1,unit:""},\n'
           '   {k:"hs_f",label:"Aigu Hz",min:1000,max:16000,d:8000,step:1,unit:"Hz",log:1},\n'
           '   {k:"hs_g",label:"Aigu dB",min:-12,max:12,d:0,step:0.5,unit:"dB"}]},')
# l'arrondi d'un param : `dec` quand il est declare (plage apprise au millieme), sinon la regle d'avant
A_L6FX3 = '      p[pd.k]=svxRound(n,pd.step<1?1:0)}});'
R_L6FX3 = '      p[pd.k]=svxRound(n,pd.dec!=null?pd.dec:(pd.step<1?1:0))}});'
# les resumes du module replie : eq6 (bandes actives, passe-haut), dehum (secteur, harmoniques, dosage), debruiteur
# (plancher, « appris ») -- la meme garde 0,2 s que learn_of (LEARN_MIN - 1e-9 : 1,2 - 1,0 = 0,1999... en JS) ; le plancher affiche est la valeur EFFECTIVE du rendu
# (_fx_denoise : nf <= -0,5 borne a [-80, -20], sinon automatique -- revue T5 25/09 : « -5 » affiche, -20 rendu)
A_L6FX4 = '    case "denoise":return p.amount+" dB";'
R_L6FX4 = ('    case "denoise":return p.amount+" dB"+(Number(p.nf)<=-.5?" · plancher "+Math.max(-80,Math.min(-20,Number(p.nf)))+" dB":"")+((Number(p.learn_out)||0)-(Number(p.learn_in)||0)>=.2-1e-9?" · appris":"");\n'
           '    case "eq6":{var nb=["ls","p1","p2","p3","p4","hs"].filter(function(b){return Math.abs(Number(p[b+"_g"])||0)>=.05}).length;\n'
           '      return (p.hp_hz>0?"PH "+Math.round(p.hp_hz)+" Hz · ":"")+(nb?nb+" bande"+(nb>1?"s":""):"neutre")}\n'
           '    case "dehum":return (p.base>=55?60:50)+" Hz ×"+p.harmonics+" · "+p.amount+" %";')
# une rangee cachee (plage apprise) ne se rend pas -- le param reste dans le module (svxCleanParams le garde)
# et le libelle d'une rangee porte son `tip` en title quand il est declare (le plancher : « 0 = auto, -20 au plus ») --
# revue T5 25/09 : l'ancre s'etend jusqu'au libelle (aucune autre section ne touche ces lignes, compte 1/1 sur le .bak)
A_L6FX5 = ('  function paramRow(def,pd,p,on){\n'
           '    var v=p[pd.k];\n'
           '    if(pd.kind==="seg")\n'
           '      return r.jsxs("div",{className:"svx-prow",children:[\n'
           '        r.jsx("span",{className:"svx-plabel",children:"Mode"}),\n'
           '        r.jsx("div",{className:"svx-gseg",role:"radiogroup","aria-label":"Mode du filtre",\n'
           '          children:pd.opts.map(function(o){\n'
           '          return r.jsx("button",{className:"svx-gsegbtn",role:"radio",\n'
           '            "aria-checked":v===o[0],"data-on":v===o[0]?"":void 0,\n'
           '            onClick:function(){setParam(def.type,pd.k,o[0])},children:o[1]},o[0])})})]},pd.k);\n'
           '    var sv,smin,smax,sstep;\n'
           '    if(pd.log){smin=0;smax=1000;sstep=1;\n'
           '      sv=Math.round(1000*Math.log(svxClamp(v,pd.min,pd.max)/pd.min)/Math.log(pd.max/pd.min))}\n'
           '    else{smin=pd.min;smax=pd.max;sstep=pd.step;sv=v}\n'
           '    var disp=pd.step<1?svxRound(v,1):Math.round(v);\n'
           '    return r.jsxs("div",{className:"svx-prow","data-dim":on?void 0:"",children:[\n'
           '      r.jsx("span",{className:"svx-plabel",children:pd.label}),')
R_L6FX5 = ('  function paramRow(def,pd,p,on){\n'
           '    if(pd.hide)return null;\n'
           '    var v=p[pd.k];\n'
           '    if(pd.kind==="seg")\n'
           '      return r.jsxs("div",{className:"svx-prow",children:[\n'
           '        r.jsx("span",{className:"svx-plabel",children:"Mode"}),\n'
           '        r.jsx("div",{className:"svx-gseg",role:"radiogroup","aria-label":"Mode du filtre",\n'
           '          children:pd.opts.map(function(o){\n'
           '          return r.jsx("button",{className:"svx-gsegbtn",role:"radio",\n'
           '            "aria-checked":v===o[0],"data-on":v===o[0]?"":void 0,\n'
           '            onClick:function(){setParam(def.type,pd.k,o[0])},children:o[1]},o[0])})})]},pd.k);\n'
           '    var sv,smin,smax,sstep;\n'
           '    if(pd.log){smin=0;smax=1000;sstep=1;\n'
           '      sv=Math.round(1000*Math.log(svxClamp(v,pd.min,pd.max)/pd.min)/Math.log(pd.max/pd.min))}\n'
           '    else{smin=pd.min;smax=pd.max;sstep=pd.step;sv=v}\n'
           '    var disp=pd.step<1?svxRound(v,1):Math.round(v);\n'
           '    return r.jsxs("div",{className:"svx-prow","data-dim":on?void 0:"",children:[\n'
           '      r.jsx("span",{className:"svx-plabel",title:pd.tip||void 0,children:pd.label}),')
# DECISION 6 DU PLAN : l'ecoute rendue accepte le son d'un plan {job_id} (la route POST /api/audio/audition le resout
# deja, routes.py : `elif payload.get("job_id")` -> fichier du job) ; UN SEUL champ part : `job_id` D'ABORD quand le
# clip le porte (l'ordre de _resolve_src du rendu : l'ecoute entend la meme source que le rendu -- revue T5 25/09),
# sinon `filename` (son de la Bibliotheque). Seul le clip sans source audio lisible est refuse, et le dit.
A_L6AU1 = ('    if(!c||!c.src||!c.src.audio){\n'
           '      fireNote("Écoute rendue : disponible pour les sons de la Bibliothèque — le son d\'un plan vidéo s\'entend via la Preview 480p.");return}\n'
           '    stopAudition();narrStop();\n'
           '    if(playingRef.current)setPlaying(!1); /* jamais deux flux à la fois */\n'
           '    var body={filename:c.src.audio,src_in:c.srcIn||0,\n'
           '      len:Math.min(12,Math.max(.2,c.end-c.start)),\n'
           '      gain_db:Math.round(Number(c.gain)||0),\n'
           '      speed:typeof c.speed==="number"&&c.speed>0?c.speed:1,\n'
           '      fx:Array.isArray(fx)?fx:[]};')
R_L6AU1 = ('    if(!c||!c.src||!(c.src.audio||c.src.job_id)){\n'
           '      fireNote("Écoute rendue : ce clip n\'a pas de source audio lisible (ni son de la Bibliothèque, ni son d\'un plan).");return}\n'
           '    stopAudition();narrStop();\n'
           '    if(playingRef.current)setPlaying(!1); /* jamais deux flux à la fois */\n'
           '    /* L6 (25/09/2026) : le son d\'un plan s\'écoute rendu lui aussi (la route résout le job en son fichier rendu) */\n'
           '    var body={src_in:c.srcIn||0,\n'
           '      len:Math.min(12,Math.max(.2,c.end-c.start)),\n'
           '      gain_db:Math.round(Number(c.gain)||0),\n'
           '      speed:typeof c.speed==="number"&&c.speed>0?c.speed:1,\n'
           '      fx:Array.isArray(fx)?fx:[]};\n'
           '    if(c.src.job_id)body.job_id=String(c.src.job_id);else body.filename=c.src.audio;')
# « APPRENDRE LE BRUIT » : le composant de la couche (NoiseLearn), monte sous le rack de l'inspecteur audio, DANS le
# fragment du rack (sans couche SFX le rack est absent : le debruiteur qu'il ecrit n'a pas d'editeur). Monte avec la cle
# sel.id : si la selection change pendant la mesure, le composant est demonte et la reponse JETEE ; sinon elle
# s'applique au clip vise par son id, a sa liste fx COURANTE (ses effets ont pu changer pendant la mesure) ; `music`
# (la musique bouclee : le rendu n'applique que le plancher) ; `demo` grise. UNE reference a la couche (sonde +1).
A_L6NL1 = '          onAudition:sfxAudition},sel.id)]}):null]})}'
R_L6NL1 = ('          onAudition:sfxAudition},sel.id),\n'
           '        /* L6 D-25 : « Apprendre le bruit » / « Oublier » sous le rack — plage I/O du projet ; réponse appliquée au\n'
           '           clip visé (par son id) sur sa liste d\'effets courante, jetée si la sélection change pendant la mesure */\n'
           '        r.jsx(DzTracks.NoiseLearn,{clip:sel,range:proj.range,demo:!!proj.demo,music:isMus,onNote:fireNote,\n'
           '          onFx:function(id,f){var k=clipsRef.current.find(function(q){return q.id===id});\n'
           '            if(k)svmSetClipAudio(id,{fx:f(Array.isArray(k.fx)?k.fx:[])})}},sel.id)]}):null]})}')
# ══ L6 D-26 (25/09/2026, tache 6) — L'ENREGISTREUR DE VOIX OFF ════════════════════════════════════════════════════
# Replis : l'action vo_record (R_R1, « Alt+R » mesuree libre), son dispatch (R_R2), la bascule dzVoRef (R_M16REF), la
# rubrique « Édition » (DZM_MENU_RUB, couche). UNE section neuve, parce qu'aucun remplacement ne touche la rangee des
# puces de la barre du haut :
# L6vo1 -- LA PUCE « ● voix off » APRES « narration ». ANCRE MESUREE 25/09/2026 : la fin du bouton « narration »
# (`onClick:narrToggle,children:"narration"}),`) vaut 1/0/1 (x1 dans .bak_montage, touchee par aucune section, x1 dans
# le bundle livre). Le composant (DzTracks.VoiceRec) tient le micro et l'enregistreur ; l'HOTE fournit :
#   onStart -> {t0, pj} : t0 = la tete (phRef) au debut de la prise, pj = l'IDENTITE du projet a ce moment
#              (dzProjRef.current.project_id, le nom a defaut -- revue T6 : svmApplyProject garde la MEME instance de la
#              puce, et une prise commencee dans un projet se posait dans le suivant, au t0 de l'ancien) ; lance la
#              lecture (setSpd(1) + setPlaying(!0), le geste MESURE de l'action « play », B:3518) : on parle sur l'image ;
#   onStop  -> setPlaying(!1) (le geste MESURE de « jog_pause ») ;
#   onDone(f, d, t0, pj) -> projet change depuis le debut de la prise : RIEN n'est pose, la note le dit (la prise est
#              dans la Bibliotheque). Sinon la POSE : piste = DzTracks.dialogueTrack (jamais pickTrack, qui peut rendre A2 musique) ; sans
#              piste de dialogue, ou piste VERROUILLEE, le refus est DIT et la prise reste dans la Bibliotheque (la route
#              l'y a deja rangee) ; sinon addAsset({audio:f}, « Voix off n », "audio", d, piste, t0) avec le MODE
#              D'EDITION FORCE A « ecraser » LE TEMPS DE L'APPEL : addAsset lit dzModeRef.current SYNCHRONEMENT dans
#              DzTracks.insere (B:4556) et dans sa note (« remplir » -> « Plage effacee ») ; la prise a une duree > 0
#              (la puce refuse une duree illisible) et le projet n'est pas la demo (la puce est grisee) : addAsset ne
#              part ni mesurer la duree ni attendre la timeline -- aucun chemin differe ne relirait le mode non force.
#              Le mode REMPLACEMENT arme (dzmReplaceRef, P6) est suspendu de meme : sans cela une prise ferait de
#              {audio} la source du plan a remplacer. Les deux refs sont remises dans un finally ; MAIS (revue T6,
#              mesure B:2332) la pose fait setOvPick("") et l'effet [ovPick] desarme alors le remplacement (ovPick !==
#              rp.tr) : en pratique un remplacement arme est DESARME par la pose d'une prise -- le finally ne le garde
#              que le temps de l'appel. Puis, SEULEMENT si la prise est reellement posee (ovSeq.current a avance : addAsset
#              ne le consomme qu'une fois l'insertion acceptee ; chacun de ses refus le dit deja par sa note), la tete va
#              a t0 + d (seekTo) : les prises successives s'enchainent.
# Quatre references a la couche (sonde +4) : VoiceRec, dialogueTrack, voLabel, voCount.
A_L6VO1 = '          onClick:narrToggle,children:"narration"}),'
R_L6VO1 = (A_L6VO1 + '\n'
           '        /* L6 D-26 : la puce ● voix off — enregistre au micro pendant la lecture ; la prise est posée sur la piste de\n'
           '           dialogue à l\'instant où elle a commencé, en mode « écraser » forcé, puis la tête va à sa fin */\n'
           '        r.jsx(DzTracks.VoiceRec,{demo:!!proj.demo,ctl:dzVoRef,combo:svmKeyLabel("vo_record"),onNote:fireNote,\n'
           '          onStart:function(){var t=Math.max(0,Number(phRef.current)||0),p=dzProjRef.current;setSpd(1);setPlaying(!0);\n'
           '            return {t0:t,pj:String(p&&(p.project_id||p.name)||"")}},\n'
           '          onStop:function(){setPlaying(!1)},\n'
           '          onDone:function(f,d,t0,pj){var pc=dzProjRef.current;\n'
           '            if(pj!==String(pc&&(pc.project_id||pc.name)||"")){fireNote("Prise « "+f+" » enregistrée dans la Bibliothèque ; le projet a changé pendant la prise, elle n\'a pas été posée.");return}\n'
           '            var ts=dzTracksRef.current||svmTracksOf(proj),tr=DzTracks.dialogueTrack(ts);\n'
           '            if(!tr){fireNote("Prise « "+f+" » enregistrée dans la Bibliothèque, mais ce projet n\'a pas de piste de dialogue : ajoutez une piste audio, puis posez-la depuis le tiroir Sons.");return}\n'
           '            if(trackStRef.current[tr]&&trackStRef.current[tr].l){fireNote("Piste "+tr.toUpperCase()+" verrouillée — déverrouillez-la pour ajouter. La prise « "+f+" » reste dans la Bibliothèque.");return}\n'
           '            var m0=dzModeRef.current,rp=dzmReplaceRef.current,q0=ovSeq.current;dzModeRef.current="ecraser";dzmReplaceRef.current=null;\n'
           '            try{addAsset({audio:f},DzTracks.voLabel(DzTracks.voCount(clipsRef.current||[])),"audio",d,tr,t0)}\n'
           '            finally{dzModeRef.current=m0;dzmReplaceRef.current=rp}\n'
           '            if(ovSeq.current!==q0)seekTo(t0+d)}}),')

L6 = [("L6fx1-catalogue-ordre-de-chaine-et-anti-ronflement", A_L6FX1, R_L6FX1),
      ("L6fx2-debruiteur-plancher-plage-apprise-et-eq6", A_L6FX2, R_L6FX2),
      ("L6fx3-arrondi-au-millieme-par-dec", A_L6FX3, R_L6FX3),
      ("L6fx4-resumes-eq6-dehum-debruiteur-appris", A_L6FX4, R_L6FX4),
      ("L6fx5-rangee-cachee-non-rendue", A_L6FX5, R_L6FX5),
      ("L6au1-ecoute-rendue-du-son-d-un-plan", A_L6AU1, R_L6AU1),
      ("L6nl1-apprendre-le-bruit-sous-le-rack", A_L6NL1, R_L6NL1),
      ("L6vo1-puce-voix-off-apres-narration", A_L6VO1, R_L6VO1)]
for _n, _a, _r in L6:
    assert _a != _r and _r.count("DzTracks") == (1 if _n.startswith("L6nl1") else 4 if _n.startswith("L6vo1") else 0), _n
assert R_L6VO1.startswith(A_L6VO1 + "\n") and R_L6VO1.endswith("if(ovSeq.current!==q0)seekTo(t0+d)}}),") and R_L6VO1.count('dzModeRef.current="ecraser"') == 1
assert R_L6VO1.find('dzModeRef.current="ecraser"') < R_L6VO1.find("try{addAsset(") < R_L6VO1.find("finally{dzModeRef.current=m0;dzmReplaceRef.current=rp}") < R_L6VO1.find("seekTo(t0+d)")
assert R_L6FX1.endswith(A_L6FX1.split("\n")[-1]) and R_L6FX1.count('{type:"dehum",') == 1 and R_L6FX1.find('type:"dehum"') < R_L6FX1.find('type:"eq3"')
assert R_L6FX2.startswith(A_L6FX2[:-3]) and R_L6FX2.count("hide:1") == 2 and R_L6FX2.count("dec:3") == 2 and R_L6FX2.count('{k:"') == 21
assert R_L6FX5.count("if(pd.hide)return null;") == 1 and R_L6FX5.count("title:pd.tip||void 0,") == 1 and R_L6AU1.count("body.job_id=String(c.src.job_id)") == 1 and R_L6AU1.count("filename:") == 0
assert R_L6NL1.startswith("          onAudition:sfxAudition},sel.id),\n") and R_L6NL1.endswith("},sel.id)]}):null]})}")

# ══ RETOURS L6 (26/09/2026, tache 4) — L'IMAGE ETALONNEE DANS LA FENETRE PRINCIPALE, A L'ARRET ══════════════════════
# Le lecteur vivant montre les sources BRUTES (decision L5 n°9) : les effets d'un plan, appliques au rendu, y etaient
# invisibles (retour de l'utilisateur, 26/09). UNE section neuve, aucun repli :
# R6gl1 -- LE COMPOSANT DzmGradeLive (couche) monte dans le cadre du lecteur, ENTRE la couche V1 (.svm-live) et les
# overlays V2 (.svm-liveov) : V2, titres, voile des fondus, cadre de selection et sous-titres restent AU-DESSUS par
# l'ordre du DOM (aucun z-index, comme le voile D-12). ANCRE MESUREE 26/09/2026 : l'ouverture de la couche des overlays
# (`liveOn?r.jsx("div",{className:"svm-liveov",ref:liveOvRef,`) vaut 1/0/1 (x1 dans .bak_montage, touchee par aucune
# section, x1 dans le bundle livre) ; elle est GARDEE en queue du remplacement. Monte sous `liveOn` comme ses voisines
# (jamais sur la demo ni avec un rendu d'apercu charge). Les noms de l'hote sont MESURES dans DzMontage : `clips`,
# `ph` (la tete), `playing`, `vzoom` (le zoom molette du viewport), `proj.ratio` (le ratio du cadre et du payload de
# rendu). UNE reference a la couche (sonde 177 -> 178).
A_R6GL1 = 'liveOn?r.jsx("div",{className:"svm-liveov",ref:liveOvRef,'
R_R6GL1 = ('/* retours L6 (26/09) : l\'image etalonnee du plan V1 sous la tete, a l\'arret -- sous les overlays V2 */\n'
           '          liveOn?r.jsx(DzTracks.GradeLive,{clips:clips,head:ph,playing:playing,vzoom:vzoom,ratio:proj.ratio}):null,\n'
           '          ' + A_R6GL1)
R6 = [("R6gl1-image-etalonnee-dans-le-lecteur-a-l-arret", A_R6GL1, R_R6GL1)]
assert R_R6GL1.endswith(A_R6GL1) and R_R6GL1.count("DzTracks") == 1 and R_R6GL1.count(A_R6GL1) == 1


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
           ("K7-echap-ferme-index", A_K7, R_K7),
           # D-20 (21/09/2026) - la galerie des transitions. X1 est
           # REPLIE dans R_M16REF (ancre posee par un remplacement,
           # comptee 0 dans .bak_montage). Les quatre ancres ci-dessous
           # valent 1/1 dans .bak_montage ET dans le bundle patche :
           # aucune section anterieure ne touche ni a SVM_TRANS, ni a
           # transPopover, ni a transInspector, ni a svmTransLabel.
           ("X2-galerie-transitions", A_X2, R_X2),
           ("X3-select-connu", A_X3, R_X3),
           ("X3b-select-catalogue", A_X3B, R_X3B),
           ("X4-libelle-catalogue", A_X4, R_X4),
           # D-12 (21/09/2026) - les fondus simples en direct. V1 est
           # REPLIEE dans R_M16REF (ancre posee par un remplacement,
           # comptee 0 dans .bak_montage). Les deux ancres ci-dessous
           # valent 1/1 dans .bak_montage ET dans le bundle patche :
           # aucune section anterieure ne touche au cadre du lecteur
           # ni au corps de `liveSync`. V2 passe AVANT V3, mais
           # l'ordre n'a aucune importance ici : les deux ancres sont
           # disjointes et ni l'une ni l'autre n'est creee par un
           # remplacement.
           ("V2-voile-cadre", A_V2, R_V2),
           ("V3-voile-livesync", A_V3, R_V3),
           # D-21 (21/09/2026) - le genre `title` et la piste t1. TT1b, TT2,
           # TT3, TT4 (deux moities) et TT5 sont REPLIES dans R_M15, R_M5,
           # R_M7, R_R1/R_R2 et R_K5 (ancres posees par un remplacement, ou
           # consommee pour A_M5). Les deux ancres ci-dessous valent 1/1
           # dans .bak_montage ET dans le bundle patche : aucune section
           # anterieure ne touche ni a `trackKind` ni a la ligne `var o=`
           # du payload de rendu (TT2 ne reecrit que le FILTRE, deux lignes
           # plus haut).
           ("TT1-genre-title", A_TT1, R_TT1),
           ("TT2b-payload-carton", A_TT2B, R_TT2B),
           # D-21 (22/09/2026, tache 7) — les restes de la revue de la
           # tache 6. TT6 (l'inspecteur), TT7 (l'hote de l'apercu), TT8
           # (son ecriture) et TT9b (la pile d'effets) sont REPLIES dans
           # R_M12, R_V2, R_V3 et R_M13 : leurs ancres sont des lignes que
           # ces remplacements POSENT ou REECRIVENT. Ces trois-ci valent
           # 1/1 dans .bak_montage.
           ("TT9-inout-carton", A_TT9, R_TT9),
           ("TT10-payload-src-mou", A_TT10, R_TT10),
           ("TT11-plus-de-t1-pose-un-carton", A_TT11, R_TT11),
           # E-3 (22/09/2026) : la porte sur V1, les deux boutons. EA1 REPREND
           # la greffe S4 de libsend (1/1 dans .bak_montage) ; EA2/EA3 sont
           # des ancres du bundle d'origine, 1/1 aussi.
           ("EA1-porte-bibliotheque-v1", A_EA1, R_EA1),
           ("EA2-chapitres-ouvrir-montage", A_EA2, R_EA2),
           ("EA3-studio-ouvrir-montage", A_EA3, R_EA3),
           # E-4 (22/09/2026) : rendre SANS publier ; le bandeau de fin.
           ("EA4-rendu-final-sans-scheduler", A_EA4, R_EA4),
           ("EA5a-popover-titre-rendre", A_EA5A, R_EA5A),
           ("EA5b-popover-ligne-a-la-demande", A_EA5B, R_EA5B),
           ("EA5c-popover-note-bandeau", A_EA5C, R_EA5C),
           ("EA5d-barre-rendre", A_EA5D, R_EA5D),
           ("EA5d2-popover-bouton-rendre", A_EA5D2, R_EA5D2),
           ("EA5e-bandeau-de-fin", A_EA5E, R_EA5E),
           ("EA6-bandeau-ferme-au-lancement", A_EA6, R_EA6),
           # D-13 (22/09/2026, L3 tache 2) : quatre ancres du bundle d'origine,
           # 1/1 dans .bak_montage ; dzPlanSet est replie dans R_M16REF.
           # L7-B D-40 (revue du 24/09/2026) : l apercu du cadrage (video OU image du fond V1), ancre libre
           # 1/0/1 -- posee AVANT DZ1 et non en queue : les pins de la queue (L4, L7A, L7e, L7f...) comptent
           # par index negatif, et l ordre est indifferent (ancre independante des autres sections).
           ("L7Brf1-apercu-du-cadrage-video-ou-image", A_L7BRF1, R_L7BRF1),
           ("DZ1-proprietes-de-plan", A_DZ1, R_DZ1),
           ("DZ2-rectangles-du-lecteur", A_DZ2, R_DZ2),
           ("DZ3-zoom-en-direct", A_DZ3, R_DZ3),
           ("DZ4-payload-dz", A_DZ4, R_DZ4),
           # D-14 (L3 tache 7) — keyframes d'echelle et d'opacite, en queue.
           ("KF1-echelle-interpolee", A_KF1, R_KF1),
           ("KF2-point-unique-aligne", A_KF2, R_KF2),
           ("KF2b-point-garde-echelle-opacite", A_KF2B, R_KF2B),
           ("KF2c-point-restant-aligne", A_KF2C, R_KF2C),
           ("KF3a-champ-echelle", A_KF3A, R_KF3A),
           ("KF3b-opacite-a-la-tete", A_KF3B, R_KF3B),
           ("KF3c-curseur-opacite", A_KF3C, R_KF3C),
           ("KF4-payload-scale-opacity", A_KF4, R_KF4),
           ("KF5-opacite-en-direct", A_KF5, R_KF5),
           # D-9 (L3 tache 9) — le rack sur un clip sans source, les hachures.
           ("AJ2a-rack-accepte-l-ajustement", A_AJ2A, R_AJ2A),
           ("AJ2b-rack-referme-le-fragment", A_AJ2B, R_AJ2B),
           ("AJ6a-data-kind-sur-le-clip", A_AJ6A, R_AJ6A),
           ("AJ6b-hachures-de-l-ajustement", A_AJ6B, R_AJ6B),
           ("AJ7-pose-d-effet-sur-l-ajustement", A_AJ7, R_AJ7),
           # E-B (lot E-B, 23/09/2026) : prefixe EB, en queue.
           ("EB1-etat-du-tiroir-medias", A_EB1, R_EB1),
           ("EB2-chip-medias-barre-de-titre", A_EB2, R_EB2),
           ("EB2b-sons-ferme-medias", A_EB2B, R_EB2B),
           ("EB2c-narration-ferme-medias", A_EB2C, R_EB2C),
           ("EB2d-sous-titre-ajoute-ferme-medias", A_EB2D, R_EB2D),
           ("EB2e-bascule-sous-titres-ferme-medias", A_EB2E, R_EB2E),
           ("EB2f-editeur-sous-titres-ferme-medias", A_EB2F, R_EB2F),
           ("EB3-tiroir-medias-dans-svm-mid", A_EB3, R_EB3),
           # E-5 (tache 4) : une section ; Publier/store/persistance sont repliés.
           ("EB4-libelle-preview", A_EB4, R_EB4),
           # E-11 (tache 5) : deux sections ; Echap (R_K7) et le ref (R_M16REF) sont replies.
           ("EB5a-voile-sous-les-popovers-de-mode", A_EB5A, R_EB5A),
           ("EB5b-popover-arrete-le-clic", A_EB5B, R_EB5B),
           # E-8 (tache 6) : deux sections ; la fermeture (R_M13) et la chip (R_EB2) sont replies.
           ("EB6a-inspecteur-a-bascule-et-poignee", A_EB6A, R_EB6A),
           ("EB6b-etat-et-poignee-de-l-inspecteur", A_EB6B, R_EB6B),
           ("EB7b-poignee-de-la-timeline-et-data-h", A_EB7B, R_EB7B),
           ("EB8a-mini-carte-avant-svm-scroll", A_EB8A, R_EB8A),
           ("EB8b-fenetre-visible-de-la-mini-carte", A_EB8B, R_EB8B),
           # ── LOT E-C (23/09/2026) ── E-6 (tache 2) : quatre sections ; l'etat
           # (R_M16REF), le voile + le rendu (R_EB5A), Echap (R_K7) et le bouton
           # « remplacer » (R_M16, dzReplaceArm) sont replies.
           ("EC1-menu-fonctions-de-l-hote", A_EC1, R_EC1),
           ("EC2-bouton-menu-dans-la-barre-de-titre", A_EC2, R_EC2),
           ("EC4-clic-droit-sur-un-clip", A_EC4, R_EC4),
           ("EC5-clic-droit-sur-une-piste", A_EC5, R_EC5),
           # E-7 (tache 3) : trois sections ; l'etat, l'effet et dzSetView sont
           # replies dans R_M16REF.
           ("EC7-data-view-sur-la-racine", A_EC7, R_EC7),
           ("EC8-barre-des-vues-en-bas-de-dzsvm", A_EC8, R_EC8),
           ("EC9-panneau-livraison-dans-svm-mid", A_EC9, R_EC9),
           # E-13 / E-14 (tache 5) : cinq sections sur des ancres libres ; l'etat
           # gapSel + gapSelRef (R_M16REF) et Echap (R_K7) sont replies.
           ("EC10-clic-dans-le-vide-d-une-lane", A_EC10, R_EC10),
           ("EC11-rendu-du-trou-selectionne", A_EC11, R_EC11),
           ("EC12-tete-de-lecture-dans-l-inspecteur", A_EC12, R_EC12),
           ("EC13-suppr-referme-le-trou", A_EC13, R_EC13),
           ("EC14-clic-sur-un-clip-efface-le-trou", A_EC14, R_EC14)] + EC15 + L4 + L7A + L5 + L6 + R6
           # retours L6 (26/09/2026, tache 4) : UNE section EN QUEUE, apres L6 (R6gl1, l'image etalonnee dans le lecteur).
           # L6 (25/09/2026, tache 5) : SEPT sections EN QUEUE, apres L5 (cinq dans le bloc SFXSTUDIO -- une premiere --,
           # l'ecoute rendue du son d'un plan, le bouton « Apprendre le bruit » sous le rack) ; aucun repli.
           # L5 (24/09/2026, tache 6) : UNE section neuve EN QUEUE (L5sc1, les scopes sous le lecteur) ; tout le reste
           # de la tache est replie (R_R1, R_R2, R_EC1, R_EB5A, R_K7).
           # L4 (23/09/2026, tache 4) : sept sections sur des ancres libres ; l'etat
           # (R_M16REF) et « Ajouter a la file » (R_EA5D2) sont replies.
           # E-12 (tache 6) : onze sections EC15a..k sur des ancres libres ;
           # « Preview » (R_EB4) et « Rendre → » (R_EA5D) sont replies.


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
