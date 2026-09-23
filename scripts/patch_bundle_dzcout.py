# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcout.py
"""Assert-guarded patcher : la pastille de coût DIT ce qu'elle ne sait pas.

BASELINE : bundle POST-patch libpicker/montage (queue de chaîne au 05/09/2026).
Backup dédié : .js.bak_dzcout (état juste avant CE patch).
JAMAIS de repatch_all sur cette chaîne — la garde aval ci-dessous le rappelle.

POURQUOI. `GET /api/cost/usage` rend `{total_usd, by_provider}`. Depuis la
tâche 8b, un provider que `_job_to_cost` ne sait pas tarifer rend 0 sous la
clé `non-tarifé:<provider>` — « pour que le blanc porte un nom ». MESURÉ à ce
moment-là : la chaîne `by_provider` n'apparaissait NULLE PART dans le bundle.
La pastille n'affichait que `total_usd`, donc le blanc mourait avant l'écran
et un total INCOMPLET se présentait comme un total.

CE QUE CE PATCH CHANGE, ET RIEN D'AUTRE :
  L1  préambule `__dzCoutBlanc(u)` en tête de fichier — une fonction PURE de
      la carte `by_provider` : elle rend `{n, noms, puce, titre}`. Aucune
      lecture du DOM, aucun appel réseau : c'est ce qui la rend exécutable
      telle quelle sous node par `backend/tests/test_cout_pastille.py`, qui
      l'EXTRAIT du bundle livré plutôt que de la recopier.
  L2  l'infobulle de la pastille, jusqu'ici une phrase fixe en anglais,
      devient la liste de `by_provider` ligne à ligne, montant compris — et
      une ligne non tarifée y est nommée comme telle.
  L3  le total passe de « $x » à « ≥ $x » dès qu'un blanc existe, et une
      pastille ambre « · N non tarifé(s) » s'ajoute à côté.

LE NOM DU FOURNISSEUR EST AFFICHÉ SANS SON PRÉFIXE TECHNIQUE : `non-tarifé:`
est une convention de clé, pas un mot que l'utilisateur doit lire. Le préfixe
que ce fichier découpe et celui que `_job_to_cost` écrit sont deux littéraux
dans deux langages ; c'est le banc qui les fait mesurer l'un par l'autre.

CE QUE CE PATCH NE FAIT PAS : il ne rafraîchit pas la pastille (elle lit
`cost/usage` au montage du Shell, inchangé), il n'ajoute aucun compte de JOBS
(la carte ne le porte pas), et il ne touche à aucun autre octet.

Run :
    python scripts/patch_bundle_dzcout.py              # dépôt
    python scripts/patch_bundle_dzcout.py --check      # n'écrit rien
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "dzcout"
MARKER = "__dzCoutBlanc"
MARKER_ATTENDU = 7      # définition + window x2 + infobulle + total + puce x2

# Sondes des maillons AMONT : si l'un de ces comptes bouge, c'est qu'un
# patcher amont a été rejoué seul et a effacé ce qui le suivait.
#
# `montage` : 42 → 43 le 06/09/2026 (P13, tour 1 — revue). UNE référence de
# plus au contrat `DzTracks`, et rien d'autre : `DzTracks.dialogueTrack` dans
# le geste PAR PLAN du bloc subs (M24c ne suit plus `a1` par identifiant mais
# la piste de dialogue du projet, comme M24j et la route). Compté des DEUX
# côtés avant d'écrire ce nombre : 42 dans le bundle d'avant le tour 1
# (`str.count` en octets), 43 après le rejeu — les trois sections M24k…M24m
# et la couche n'en ajoutent aucune (commentaires compris).
#
# `montage` : 39 → 42 le 06/09/2026 (P13, « la transcription vise la piste
# de dialogue »). TROIS références de plus au contrat `DzTracks`, et rien
# d'autre : deux `DzTracks.subsSources` dans le bloc subs inliné (M24a, la
# ligne d'attente qui nomme ce qui part ; M24e, la pastille de coût sur la
# somme des clips de dialogue) et un `DzTracks.dialogueTrack` dans l'hôte
# (M24j, `subsSrcClips` fait partir les clips de la piste de dialogue du
# projet). Compté des DEUX côtés avant d'écrire ce nombre : 39 dans le
# bundle d'avant P13, 42 après (simulation en mémoire du rejeu de montage
# sur `.bak_montage`, `str.count` commentaires de la couche compris — la
# couche reste à 5, les sections passent de 34 à 37).
#
# `montage` : 38 → 39 le 06/09/2026 (tour 2 de P12). La revue a mesuré que
# la porte « Envoyer vers → Montage » (greffon libsend, `"v2"` en dur) posait
# un plan sur une incrustation SANS SON ET SANS UN MOT : UNE référence de
# plus au contrat, `DzTracks.overlayNote` (M22a, la phrase quand aucun jumeau
# ne parle), et rien d'autre — M22d (la réparation persistée) n'en ajoute
# aucune, et la reprise de `v1_non_video` (M22c) non plus. Compté des DEUX
# côtés avant d'écrire ce nombre (`bytes.count` sur le bundle) : 38 avant,
# 39 après ; la couche reste à 5.
#
# `montage` : 29 → 38 le 06/09/2026. P12 (« le son d'un plan suit sa vidéo »)
# ajoute NEUF références au contrat `DzTracks` dans le bundle, et rien
# d'autre : quatre dans la sonde d'`addAsset` (`wantsTwin`, `audioOf`,
# `askAudio`, `srcDurOr` — R_M17A), deux dans le trio id/historique
# (`uniqueId`, `twinPlan` — M22a), deux dans `svmApplyProject` (`dedupeIds`,
# `seqMax` — M22c) et une dans l'inspecteur (`extractBtn` — M23). Compté des
# DEUX côtés avant d'écrire ce nombre (`str.count` sur le texte du bundle,
# commentaires de la couche compris) : 29 dans le bundle d'avant P12, 38
# après — et la sonde a fait son travail : elle a refusé de tourner sur 38
# tant que cette ligne disait 29, et restauré son .bak (marqueur à 0 le
# temps de la mettre à jour, 7 au rejeu suivant).
#
# `montage` : 53 → 60 le 06/09/2026 (P16 — traduire les répliques). SEPT
# références de plus au contrat, toutes dans les deux sections M26a/M26b du
# patcher montage : `DzTracks.subsTrDefaut(`, `DzTracks.subsTrBody(`,
# `DzTracks.subsTrApply(` et `DzTracks.subsTrNote(` dans M26a (l'état, le
# geste), `DzTracks.subsTrEnabled(`, `DzTracks.subsTrLabel(` et
# `DzTracks.subsTrTitle(` dans M26b (la rangée) — aucun jeton en
# commentaire. La couche, elle, reste à 5 (mesuré : les fonctions neuves
# dzmSubsTr* n'écrivent pas le jeton, ni en code ni en commentaire).
# COMPTÉ DES DEUX CÔTÉS AVANT D'ÉCRIRE CE NOMBRE : 53 dans le bundle de
# f1b1006, 7 dans les sections (`(R_M26A+R_M26B).count`, ancres à 0), 60
# après rejeu — en octets, `str.count`.
#
# `montage` : 43 → 53 le 06/09/2026 (P14 — deux sortes de pistes vidéo, et
# v3 n'est plus un fantôme). DIX références de plus au contrat, toutes dans
# les douze sections M25a…M25l du patcher montage : NEUF
# `DzTracks.isOverlayTrack(` — les neuf portes de l'écran qui codaient « v2 »
# en dur (aperçu, payload, inspecteur, losanges, alignement 3×3, « position
# ici », poignées du lecteur, flèches et Échap du clavier) — et UN
# `DzTracks.overlayOrder(` (l'aperçu empile dans l'ordre des pistes). La
# couche, elle, reste à 5 (mesuré : `git show HEAD:…` 5, fichier de travail
# 5 — les deux fonctions neuves et `addDit` n'ajoutent pas le jeton, ni en
# code ni en commentaire). COMPTÉ DES DEUX CÔTÉS AVANT D'ÉCRIRE CE NOMBRE :
# 43 dans le bundle de 23fd81c, 10 dans les sections (`r.count - a.count`
# sur P.PATCHES M25*), 53 après rejeu — en octets, `str.count`.
#
# `montage` : 33 → 29 le 06/09/2026, et C'EST UNE BAISSE — la première de
# cette sonde. L'étape 6 du handoff « Barre Outils Flottante » (§5.1) retire
# les neuf contrôles du bandeau de transport, et QUATRE d'entre eux étaient
# des références au contrat : `DzTracks.TrackAdd` (les deux boutons de
# piste), `DzTracks.LibBtn`, `DzTracks.WordAnimChip` et `DzTracks.EmojiBtn`.
# `DzTracks.Projects` RESTE — son bouton part, sa liste demeure, parce que
# c'est elle que la barre flottante demande (M14, `nu:!0`) — et le bouton
# « texte », lui, n'était pas une référence au contrat mais un `<button>` nu.
# COMPTÉ DES DEUX CÔTÉS AVANT D'ÉCRIRE CE NOMBRE : 33 dans le bundle de
# b59c7ab, 29 après ; delta = −4, et les quatre sont nommés ci-dessus. LA
# SONDE A FAIT SON TRAVAIL une fois de plus : elle a refusé de tourner sur 29
# tant que cette ligne disait 33, et la chaîne s'est arrêtée là.
#
# `montage` : 32 → 33 le 05/09/2026 (TROISIÈME mise à jour du jour).
# L'étape 4 du handoff « Barre Outils Flottante » monte l'onglet OUTILS et la
# barre dans le bandeau de transport (section M19) : UNE référence de plus au
# contrat, `DzTracks.ToolDock`, et rien d'autre — le reste de la barre (le
# câblage, les deux composants, la persistance) vit dans la couche, qui est
# injectée en bloc et compte déjà ses cinq occurrences.
# COMPTÉ DES DEUX CÔTÉS AVANT D'ÉCRIRE CE NOMBRE : 32 dans le bundle de
# a3eaee3 (`git show HEAD:… | count`), 33 après M19 ; delta = 1 =
# `DzTracks.ToolDock`. Et LA SONDE A ENCORE FAIT SON TRAVAIL : elle a refusé
# de tourner sur 33 tant que cette ligne disait 32, et la chaîne s'est
# arrêtée là au lieu d'écrire un bundle à moitié réécrit.
#
# `montage` : 29 → 32 le 05/09/2026 (SECONDE mise à jour du jour). P11 (« un
# clip entre à la longueur de sa source ») ajoute TROIS références au contrat
# `DzTracks` dans le bundle, toutes dans `addAsset` : `DzTracks.clipLen` (le
# corps de `defaultLen`, dont les deux plafonds disparaissent),
# `DzTracks.needDur` et `DzTracks.askDur` (la découverte de la durée quand la
# base ne la porte pas). Compté des DEUX côtés avant d'écrire ce nombre :
# 29 dans le bundle d'avant P11, 32 après — et la sonde a de nouveau fait son
# travail, en refusant de tourner sur 32 tant que cette ligne disait 29.
#
# `montage` : 25 → 29 le 05/09/2026, et LA SONDE A FAIT SON TRAVAIL. P10 (la
# timeline qui s'étend au lieu de rogner) ajoute QUATRE références au contrat
# `DzTracks` dans le bundle — trois `DzTracks.fitDur` (l'ajout, le décalage
# clavier, le relâchement du glisser) et un `DzTracks.durCtl` (le réglage de
# durée de la barre de transport) — et rien d'autre. Compté des deux côtés
# avant d'écrire ce nombre : 25 dans le bundle d'avant P10, 29 après.
# CE QUI S'EST PASSÉ CE JOUR-LÀ, et qui vaut d'être écrit : les six commits de
# P7 ont été cueillis (cherry-pick) dans un arbre de travail où `.bak_dzcout`
# N'EXISTAIT PAS — les backups ne sont pas suivis par git. Le bundle est arrivé
# AVEC les sections dzcout, sans le backup qui les signale. La garde
# `guard_downstream` de patch_bundle_montage.py, qui cherche un `.bak_*` plus
# récent que le sien, était donc AVEUGLE : rejouer montage a restauré
# `.bak_montage` et effacé les sept marqueurs de dzcout, en silence et sans que
# rien ne le voie — sauf CETTE sonde, au rejeu suivant. Le remède est le rejeu
# de dzcout APRÈS montage (il est en queue de chaîne), qui recrée `.bak_dzcout`
# et rend la vue à la garde amont.
STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("print3d", "__dzPrint3d", 3),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
    # 21/09/2026 D-0 : 63 apres H1…H5/H7 (l'historique complet cable — trois
    # references de plus : DzTracks.histSnap dans dzmHistHost, et
    # DzTracks.histApply dans undo et dans redo). REMESURE le meme jour apres
    # le correctif « absent est un etat » : toujours 63 — la resynchro du bus
    # appelle `svmTrackBusSync(s.tracks)` NU, qui retombe deja sur
    # DZM_DEFAULT_TRACKS quand la cle manquait ; un `||DzTracks.DEFAULTS`
    # aurait ajoute deux jetons sans rien changer au comportement.
    # 21/09/2026 D-11 : 63 -> 69, MESURE apres rejeu (la chaine a refuse au
    # premier passage, « sonde montage x69 (want 63) »). SIX references de
    # plus, la plage I/O : rangeSet, rangeFrom et rippleCut dans la branche
    # de dispatch du clavier (R2), RangeBar sur la regle (R3), rangeFrom
    # dans le payload de sauvegarde (repli R4 dans R_M6) et rangeFrom a la
    # restauration (repli R5 dans R_M7).
    # 21/09/2026 D-11, revue de la tache 4 : 69 -> 71, MESURE apres rejeu
    # (la chaine a refuse, « sonde montage x71 (want 69) »). DEUX references
    # de plus, et rien d'autre : `DzTracks.cutOpts`, les options de coupe
    # {loopTracks, locked} sorties dans la couche parce que R_R2 et R_M12 les
    # rebatissaient a l'identique -- un appel dans chacune. La sortie tot de
    # R2 et les bornes de la bande n'en ajoutent aucune.
    # 21/09/2026 D-2, tache 6 (cablage des modes d'edition) : 71 -> 76,
    # MESURE apres rejeu (la chaine a refuse, « sonde montage x76 (want 71) »).
    # CINQ references de plus, nommees : DzTracks.ModeBar (la rangee de chips
    # dans le selecteur, repli « E2 » dans R_M15B), DzTracks.insere (l'appel
    # de R_M22A) et le `DzTracks.insere` cite par le COMMENTAIRE JS qui le
    # precede -- la sonde compte des occurrences de texte, commentaires
    # compris --, DzTracks.modeLabel et DzTracks.secs (la note dit le mode
    # applique et la vitesse de « remplir »). DzTracks.fitDur ne bouge pas :
    # l'appel a seulement DEMENAGE de R_M17A vers R_M22A, ou il se mesure sur
    # `dzIns.clips` au lieu du seul clip pose (1 -> 0 et 0 -> 1, mesure).
    # 21/09/2026 D-2, tour de correction : 76 -> 75, MESURE apres rejeu (la
    # chaine a refuse, « sonde montage x75 (want 76) »). UNE reference de
    # moins, NET, et les trois mouvements sont nommes : `DzTracks.secs` sort
    # (I-2 : c'est un formateur de DUREE, il arrondissait la vitesse 0,25 en
    # « x0,3 » -- la note la formate desormais sur place), les DEUX
    # `DzTracks.insere` cites par des COMMENTAIRES JS deviennent `insere()`
    # (la sonde compte du texte, commentaires compris), et `DzTracks.fitDur`
    # gagne un appel (3 -> 4 : `dzAv`, la fin reelle d'AVANT l'insertion, qui
    # borne la phrase de l'allongement).
    # 21/09/2026 D-3, tache 7 (roll, slip, slide) : 75 -> 78, MESURE apres
    # rejeu (la chaine a refuse, « sonde montage x78 (want 75) »). TROIS
    # references de plus, nommees : DzTracks.slip et DzTracks.slide dans
    # le `mv` de clipDown (T2), DzTracks.roll dans le `mv` de dzRollDown
    # (T4). T1, T3, T3b et T5 n'en ajoutent aucune : modificateurs lus,
    # appels a `dzRollDown` (fonction locale, pas un membre de DzTracks)
    # et texte d'infobulle.
    # 21/09/2026 D-5, tache 8 (les marqueurs) : 78 -> 85, MESURE apres
    # rejeu (la chaine a refuse, « sonde montage x85 (want 78) »). SEPT
    # references de plus, nommees : DzTracks.markerAdd et
    # DzTracks.markerNext dans la branche de dispatch du clavier (repli
    # « K2 » dans R_R2), DzTracks.Markers sur la regle (repli « K4 »
    # dans R_R3), DzTracks.MarkerIndex, DzTracks.markerRemove et
    # DzTracks.markerUpdate dans le panneau de l'index (K5b), et
    # DzTracks.markersFrom a la restauration (repli « K6 » dans R_M7).
    # K1 (les quatre actions), K3 (l'etat du panneau), K5 (la chip) et
    # la moitie SAUVEGARDE de K6 (`markers:(proj.markers||[])`, une
    # lecture nue du projet) n'en ajoutent aucune.
    # D-4 (21/09/2026, tache 9) : 85 -> 86 -- W2 ajoute UN appel de plus,
    # `DzTracks.swap(...)`, dans la branche de dispatch swap_left/swap_right
    # repliee dans R_R2. Mesure sous --check apres l'ajout.
    # D-20 (21/09/2026, tâche 2) : 86 -> 90 -- la galerie des
    # transitions. QUATRE références de plus, MESURÉES après rejeu (la
    # chaîne a refusé, « sonde montage x90 (want 86) ») et nommées :
    # DzTracks.TransGrid (la grille du popover de jonction, X2),
    # DzTracks.transList DEUX FOIS (X3, le `known` de l'inspecteur, et
    # X3b, les options du <select>) et DzTracks.transLabel (X4, le
    # libellé au niveau module). X1, le chargement du catalogue replié
    # dans R_M16REF, n'en ajoute aucune : c'est un fetch, pas un appel
    # à la couche. Un premier jet en comptait 91 -- la référence de trop
    # était dans un COMMENTAIRE JS de R_X2 (la sonde compte du texte,
    # commentaires compris) : la prose dit désormais « TransGrid() ».
    # `montage` : 90 -> 91 le 21/09/2026 (D-12, les fondus simples joues
    # en direct). UNE reference de plus au contrat, et une seule : le
    # `veil(` de V3, en tete de `liveSync`. V1 (la ref du voile, repliee
    # dans R_M16REF) et V2 (le `<i>` du cadre) n'en ajoutent aucune --
    # l'une est un `useRef`, l'autre un element de rendu. La prose de ces
    # trois sections est ecrite SANS le jeton (« la couche », « veil() »)
    # parce que la sonde compte du TEXTE, commentaires compris : c'est la
    # lecon du premier jet de X2, qui avait compte 91 pour un commentaire.
    # MESURE : la chaine a refuse, « sonde montage x91 (want 90) », AVANT
    # que ce nombre ne soit ecrit -- 90 dans le bundle de 1e0b1bc, +1 par
    # V3, 91 apres rejeu, en octets, `str.count`.
    # `montage` : 91 -> 94 le 21/09/2026 (D-21, tache 6 : le genre `title`,
    # la piste t1, poser un titre). TROIS references de plus, et trois
    # seulement : `titleNew(` et `titleTrack(` dans le geste `dzTtAdd`
    # (TT4a, replie dans R_M16REF), et `titleTrack(` dans la restauration
    # (TT3, replie dans R_M7). TT1 (le quatrieme genre de `trackKind`),
    # TT1b (le refus d'`addAsset`), TT2/TT2b (le payload de rendu) et TT5
    # (la chip « T+ », qui appelle `dzTtAdd`) n'en ajoutent AUCUNE : elles
    # ne parlent pas a la couche. La prose de ces sections est ecrite SANS
    # le jeton (« la couche », « titleTrack() ») parce que la sonde compte
    # du TEXTE, commentaires compris -- lecon du premier jet de X2.
    # MESURE : la chaine a refuse, « sonde montage x94 (want 91) », AVANT
    # que ce nombre ne soit ecrit.
    # `montage` : 94 -> 98 le 22/09/2026 (D-21, tache 7 : l'inspecteur des
    # titres et l'apercu vivant). QUATRE references de plus, et quatre
    # seulement : `TitleInspector` et `titleUpdate(` dans l'inspecteur
    # monte par TT6 (replie dans R_M12), `titleAt(` et `titleHtml(` dans
    # l'ecriture de l'apercu par TT8 (replie dans R_V3). TT7 (l'hote),
    # TT7ref (la ref et le catalogue), TT9/TT9b (les deux inspecteurs qui
    # se taisent), TT10 (le payload) et TT11 (le « + » de T1) n'en ajoutent
    # AUCUNE : elles ne parlent pas a la couche. La prose de ces sections
    # est ecrite SANS le jeton, meme lecon que ci-dessus.
    # MESURE : la chaine a refuse, « sonde montage x98 (want 94) », AVANT
    # que ce nombre ne soit ecrit.
    # 22/09/2026, E-4 (lot E-A, tache 5) : 98 -> 99. UNE de plus, par
    # EA5e : le bandeau de fin de rendu, monte a cote du popover. EA4
    # (le rendu final qui ne publie plus), EA5a..d (quatre libelles) et
    # le repli dzFin (R_M16REF) n'en ajoutent aucune. MESURE : la chaine
    # a refuse, « sonde montage x99 (want 98) », avant cette ligne.
    # 22/09/2026, D-13 (lot L3, tache 2) : 99 -> 104. CINQ de plus : l hote
    # des proprietes de plan (DZ1, `PlanProps`), les rectangles du lecteur
    # (DZ2, `DzRects`), le zoom en direct (DZ3, `dzOf(` + `dzCss(`) et le
    # payload (DZ4, `dzOf(`). Le repli `dzPlanSet` (R_M16REF) n en ajoute
    # aucune. MESURE : la chaine a refuse, « sonde montage x104 (want 99) »,
    # avant cette ligne.
    # 22/09/2026, revue de D-13 : 104 -> 103. DZ3 appelle `dzCss(c.dz,u)`
    # directement (rend "" sur absent/invalide) : plus de `dzOf(` la.
    # 22/09/2026, D-15 (lot L3, tache 4) : 103 -> 105. DEUX de plus, sans
    # section neuve : la rampe dans DZ1 (`rampe(`) et l interpolation dans le
    # payload DZ4 (`retimeOf(`, UNE occurrence via `rtD`). MESURE : la chaine
    # a refuse, « sonde montage x105 (want 103) », avant cette ligne.
    # 22/09/2026, D-16 (lot L3, tache 6) : 105 -> 106. UNE de plus, sans
    # section neuve : la stabilisation dans le payload DZ4 (`stabOf(`, UNE
    # occurrence via `sbD`). L hote (DZ1, stabJob/onStab) et le repli du
    # suivi de job (R_M16REF) n en ajoutent aucune. MESURE : la chaine a
    # refuse, « sonde montage x106 (want 105) », avant cette ligne.
    # 22/09/2026, revue de D-16 : 106 -> 108. DEUX de plus : la cle de
    # source canonique `srcKey(` dans DZ1 (stabJob) et dans le repli
    # dzStabStart (R_M16REF), a la place d un JSON.stringify a l ordre pres.
    # 22/09/2026, D-14 (lot L3, tache 7) : 108 -> 112. QUATRE de plus, en
    # huit sections KF1..KF5 : `mpLerp2(` dans svmOvTfAt (KF1, l echelle
    # interpolee), dans vOp de l inspecteur (KF3b) et dans liveSync (KF5,
    # l opacite en direct) ; `mpKeep(` dans svmMpPlace (KF2b). KF2, KF3a,
    # KF3c et KF4 n en ajoutent aucune (svmMpField, code nu).
    # 22/09/2026, D-9 (lot L3, tache 9) : 112 -> 114. DEUX de plus, dans le
    # repli dzAjAdd (R_M16REF) : `adjustNew(` (le clip de 3 s) et
    # `adjustTrack(` (la piste j1 nait avec le premier clip). AJ2a/AJ2b,
    # AJ6a/AJ6b et les replis TT1/M5/TT11/R1/R2/K5 n en ajoutent aucune.
    # MESURE : la chaine a refuse, « sonde montage x114 (want 112) ».
    # 23/09/2026, E-2 (lot E-B, tache 3) : 114 -> 115. UNE de plus, par
    # EB3 : le tiroir Medias monte dans .svm-mid (`MediaDrawer`, le
    # composant de la couche). EB1 (l etat), EB2 (la chip), EB2b..EB2f
    # (les cinq exclusions) et le repli du « + » video (R_TT11) n en
    # ajoutent aucune : `onAdd` appelle addAsset avec "v1" comme la porte
    # E-3, sans pickTrack (addAsset resout deja la piste, R_M16A). MESURE :
    # la chaine a refuse, « sonde montage x115 (want 114) », avant cette
    # ligne.
    # 23/09/2026, E-5 (lot E-B, tache 4) : 115 -> 117. DEUX de plus, toutes
    # deux dans des REPLIS : `finOf(` (dzLast, l etat du store a cote de
    # dzFin, R_M16REF) et `finStore(` (la persistance du rendu FINAL, R_EA4).
    # EB4 (le libelle « Preview ») et le bouton « Publier » (R_EA5D, qui ne
    # fait que setDzFin) n en ajoutent aucune. MESURE : la chaine a refuse,
    # « sonde montage x117 (want 115) », avant cette ligne.
    # 23/09/2026, E-8 (lot E-B, tache 6) : 117 -> 119. DEUX de plus, toutes
    # deux dans EB6b : `inspW(` a la lecture de la cle au montage (l etat
    # stIn) et `inspW(` a chaque mouvement de la poignee (inspDown). EB6a
    # (l aside a bascule, sa largeur, la poignee), le repli de la fermeture
    # (R_M13, `:null,`) et la chip (R_EB2, qui ne fait que setInspSt) n en
    # ajoutent aucune. MESURE : la chaine a refuse, « sonde montage x119
    # (want 117) », avant cette ligne.
    # 23/09/2026, E-9 (lot E-B, tache 7) : 119 -> 122. TROIS de plus, TOUS
    # dans des replis : `tlH(` dans l effet de montage qui borne la cle lue
    # sur .dzsvm.clientHeight (EB7a, repli R_EB6B), `tlH(` a chaque mouvement
    # de la poignee tlDown (EB7a, meme repli), et `durLbl(` sur le label du
    # clip (repli R_M16D, ancre consommee par M16d). EB7b (la poignee et le
    # data-h de .svm-tl) et la chip « durées » (R_EB2, qui ne fait que
    # setShowDur) n en ajoutent aucune. MESURE : la chaine a refuse, « sonde
    # montage x122 (want 119) », avant cette ligne.
    # 23/09/2026, D-7 (lot E-B, tache 8) : 122 -> 123. UNE de plus, dans EB8a :
    # `DzTracks.Minimap` (la mini-carte posee dans .svm-tl avant .svm-scroll).
    # EB8b (mmView/mmCalc, la fenetre visible) et le onSeek de l'hote (qui ne
    # touche que tlScrollRef) n en ajoutent aucune. MESURE : la chaine a refuse,
    # « sonde montage x123 (want 122) », avant cette ligne.
    # 23/09/2026, E-6 (lot E-C, tache 2) : 123 -> 128. CINQ de plus, dans
    # EC1 (dzFire, dzMenuProps) et le repli R_EB5A : `DzTracks.comboToKey(`
    # (la combo rejouee), `DzTracks.menuModel(` (les six rubriques),
    # `DzTracks.CtxMenu` (le composant rendu apres le voile),
    # `DzTracks.voisins(` (Transition… grisee sans voisin gauche) et
    # `DzTracks.remove(` (Supprimer la piste, la sequence de del()). EC2
    # (le bouton ☰), EC4/EC5 (les clics droits), R_M16REF (l etat), R_K7
    # (Echap) et R_M16 (dzReplaceArm) n en ajoutent aucune. MESURE : la
    # chaine a refuse, « sonde montage x128 (want 123) », avant cette ligne.
    # 23/09/2026, E-7 (lot E-C, tache 3) : 128 -> 129. UNE de plus, dans EC9 :
    # `DzTracks.Deliver` (le panneau Livraison, premier enfant de .svm-mid).
    # EC6 (l etat, l effet fetch, dzSetView -- repli R_M16REF), EC7 (data-view
    # sur la racine) et EC8 (la barre des vues) n en ajoutent aucune. MESURE :
    # la chaine a refuse, « sonde montage x129 (want 128) », avant cette ligne.
    ("montage", "DzTracks", 129),
]

# ── L1 — le préambule, fonction PURE de la carte ────────────────────────────
# Le libellé « fournisseurs » n'apparaît QUE dans la branche plurielle : la
# ligne `deux_blancs_accordent_le_pluriel` du banc serait sinon verte au
# singulier aussi, sans rien mesurer.
PREAMBULE = (
    "function __dzCoutBlanc(u){"
    'var P="non-tarifé:",b=(u&&u.by_provider)||{},k=Object.keys(b).sort(),'
    "nt=[],ls=[],i,x;"
    "for(i=0;i<k.length;i++){x=k[i];"
    "if(x.indexOf(P)===0){nt.push(x.slice(P.length));"
    'ls.push("  ? "+x.slice(P.length)'
    '+" — NON TARIFÉ : coût inconnu, absent de ce total")}'
    'else{ls.push("  · "+x+" — $"+b[x]'
    '+(x==="local"?" (opérations locales, sans dépense)":""))}}'
    'var t=k.length?"Dépense estimée sur cette app, par fournisseur :\\n"'
    '+ls.join("\\n"):"Aucune dépense estimée pour l\'instant.";'
    'if(nt.length){t+="\\n\\n⚠ Ce total est un MINORANT : "+nt.length'
    '+" fournisseur"+(nt.length>1?"s":"")+" sans tarif ("+nt.join(", ")'
    '+"). "+(nt.length>1?"Leur":"Son")+" coût réel n\'est PAS compté."}'
    'return{n:nt.length,noms:nt,puce:"· "+nt.length+" non tarifé"'
    '+(nt.length>1?"s":""),titre:t+"\\n\\nClic → Réglages."}}'
    "window.__dzCoutBlanc=__dzCoutBlanc;"
)

_A1 = '(function(){const t=document.createElement("link").relList;'
_A2 = ('title:"Estimated spend on this app + live provider balances. '
       'Click for Settings."')
_A3 = 'children:["$",Cu&&Cu.total_usd!=null?Cu.total_usd:"—"]}),'

_R3 = (
    'children:[__dzCoutBlanc(Cu).n?"≥ $":"$",'
    'Cu&&Cu.total_usd!=null?Cu.total_usd:"—"]}),'
    '__dzCoutBlanc(Cu).n?r.jsx("span",{style:{color:"var(--amber)"},'
    'children:__dzCoutBlanc(Cu).puce},"dzcoutblanc"):null,'
)

PATCHES = [
    ("L1-preambule", _A1, PREAMBULE + _A1),
    ("L2-infobulle", _A2, "title:__dzCoutBlanc(Cu).titre"),
    ("L3-total-et-puce", _A3, _R3),
]


def deltas():
    dc = sum(len(r) - len(a) for _t, a, r in PATCHES)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in PATCHES)
    return dc, db


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{TAG} doit rester le DERNIER maillon ; jamais de "
                "repatch_all sur cette chaine.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others:
        return False
    top = max(others)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def main():
    args = sys.argv[1:]
    check = "--check" in args
    dc, db = deltas()
    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        if s.count(MARKER):
            raise SystemExit(
                f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans "
                f"{src.name} — double application refusee. Une racine d'app "
                "installee se met a jour par COPIE du bundle du depot.")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). "
                                 "Aborting.")
        # L1 s'insere EN TETE : l'ancre doit etre le debut du fichier, sinon
        # la fonction atterrirait dans une portee quelconque.
        if not s.startswith(_A1):
            raise SystemExit(f"[L1] l'ancre n'est pas en tete du fichier. "
                             "Aborting.")
        for name, probe, want in STABLE_PROBES:
            if s.count(probe) != want:
                raise SystemExit(f"[sonde {name}] count={s.count(probe)} "
                                 f"(want {want}). Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK, marqueur absent, "
              f"{len(STABLE_PROBES)} sondes aux comptes")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return

    if not bak.exists():
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] marqueur present sans {bak.name} : etat ambigu, "
                "abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(f"[{TAG}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present "
                         "apres restore). Aborting.")
    if not s.startswith(_A1):
        raise SystemExit(f"[L1] l'ancre n'est pas en tete du fichier. "
                         "Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if len(after) != len(before) + db:
        problems.append(f"taille {len(after)} o, attendu {len(before) + db}")
    if len(s) != chars0 + dc:
        problems.append(f"caracteres {len(s)}, attendu {chars0 + dc}")
    if s.count(MARKER) != MARKER_ATTENDU:
        problems.append(f"marqueur x{s.count(MARKER)} "
                        f"(want {MARKER_ATTENDU})")
    if not s.startswith(PREAMBULE):
        problems.append("le preambule n'est pas en tete du fichier")
    for tag, _anchor, repl in PATCHES:
        if s.count(repl) != 1:
            problems.append(f"{tag} : remplacement x{s.count(repl)} (want 1)")
    if s.count(_A2) or s.count(_A3):
        problems.append("une ancre consommee est encore presente")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (la pastille de cout dit son blanc).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : & $PY tests/test_cout_pastille.py, puis DEPLOYER")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
