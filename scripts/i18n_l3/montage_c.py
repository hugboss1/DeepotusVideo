"""t143 — montage_c : couche Montage (frontend/patches/montage.js), lignes 1947–2724 de la base. Couvre : le sort du
trou laissé par un plan raccourci (dzmGapFate), le remplacement de source d'un plan et son retour (dzmReplaceSrc,
dzmRevertSrc : notes et avertissements ; dzmReplaceBtn, dzmRevertBtn : boutons de l'inspecteur), le rappel « versions
plus récentes » (DZM_NEWER_H, dzmNewerLine, DzmNewerHint), le contrôle de durée de la timeline dans la barre de
transport (DZM_DUR_UNDO, dzmDurCtl : notes, infobulles, bouton « ajuster »), la longueur d'un clip posé (dzmClipLen),
l'envoi de la piste de dialogue à la transcription (dzmSubsSources : étape et note) et la traduction des répliques de
S1 (dzmSubsTrLabel, dzmSubsTrEnabled, dzmSubsTrTitle, dzmSubsTrNote).

Gardés : « audio » de dzmClipLen (genre de clip, clé de DZM_CLIP_DEFAUTS), « mesure » de dzmAskDur (motif rendu au
rappel et comparé ailleurs : v.pourquoi==="mesure"), « total » (identique dans les deux langues). Aucune valeur
ENREGISTRÉE dans ce bloc n'est traduite : dzmReplaceSrc/dzmRevertSrc écrivent dans le clip le label REÇU (k.label=
label||o.label, last.label), jamais « ce plan » ni « sans titre », qui ne servent qu'aux notes et aux infobulles ;
dzmSubsTrApply écrit le texte traduit, pas un littéral.
Phrases recomposées (S) : les notes coupées en morceaux concaténés deviennent une seule clé à variables ; le suffixe
de dzmGapFate passe par {suite}, le « (cadrage centré) » du suivi par {centre}, les compteurs « version(s) »,
« réplique(s) », « clip(s) », « fichier(s) » par deux clés .un / .plusieurs. Chaque S garde AUTANT de fins de ligne
que le code d'origine. La virgule décimale de dzmSecs/dzmNewerLine (« 0,5 s ») n'est pas touchée : c'est du code, pas
un littéral."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_CE_PLAN = ('ce plan', 'this clip')
_SANS_TITRE = ('sans titre', 'untitled')

ENTREES = [
    # dzmGapFate : ce que devient le trou laissé derrière un plan raccourci (suffixe de la note de remplacement)
    S(114144, '" — sur une piste son, aucune piste ne réapparaît en dessous : "+\r\n      "ce trou-là s\'entend. Sauf sur une piste BOUCLÉE (A2 par défaut), "+\r\n      "dont le rendu ignore les bornes de son premier clip et joue la "+\r\n      "source d\'un bout à l\'autre du film."',
      'dzT("montage.trou_fin.son"\r\n      \r\n      \r\n      )',
      {'montage.trou_fin.son': (
          " — sur une piste son, aucune piste ne réapparaît en dessous : ce trou-là s'entend. Sauf sur une piste "
          "BOUCLÉE (A2 par défaut), dont le rendu ignore les bornes de son premier clip et joue la source d'un bout à "
          "l'autre du film.",
          ' — on an audio track, no track shows through underneath: this gap is audible. Except on a LOOPED track '
          '(A2 by default), whose render ignores the bounds of its first clip and plays the source from start to end '
          'of the film.')}),
    L(114463, 'montage.trou_fin.noir', ", rendu en noir à l'export.", ', rendered black on export.'),
    S(114499, '" — sur une piste d\'incrustation, c\'est la piste du dessous qui "+\r\n     "réapparaît."',
      'dzT("montage.trou_fin.incrustation"\r\n     )',
      {'montage.trou_fin.incrustation': (" — sur une piste d'incrustation, c'est la piste du dessous qui réapparaît.",
                                         ' — on an overlay track, the track underneath shows through.')}),

    # dzmReplaceSrc : remplacer la source d'un plan (suivi du mouvement, avertissements, note)
    S(115941, '" Le suivi du mouvement de l\'ancienne source est retiré"+(rfOld.mode==="suivi"?" (cadrage centré)":"")+\r\n      " — relancez « Analyser le mouvement »."',
      'dzT("montage.source_plan.suivi_retire",{centre:rfOld.mode==="suivi"?dzT("montage.source_plan.cadrage_centre"):""}\r\n      )',
      {'montage.source_plan.suivi_retire': (
          " Le suivi du mouvement de l'ancienne source est retiré{centre} — relancez « Analyser le mouvement ».",
          ' Motion tracking from the old source is removed{centre} — run “Analyze motion” again.'),
       'montage.source_plan.cadrage_centre': (' (cadrage centré)', ' (centered framing)')}),
    S(116117, '"Durée de la nouvelle source inconnue : les bornes du plan n\'ont "+\r\n      "pas pu être vérifiées — contrôlez sa fin."',
      'dzT("montage.source_plan.duree_inconnue"\r\n      )',
      {'montage.source_plan.duree_inconnue': (
          "Durée de la nouvelle source inconnue : les bornes du plan n'ont pas pu être vérifiées — contrôlez sa fin.",
          'New source duration unknown: the clip bounds could not be checked — check its end.')}),
    S(116384, '"La nouvelle source ne dure que "+d.toFixed(2)+" s : le plan a "+\r\n        "été raccourci de "+len.toFixed(2)+" s à "+(d/sp).toFixed(2)+" s, "+\r\n        "et la timeline garde un trou derrière lui"+dzmGapFate(o.tr)',
      'dzT("montage.source_plan.raccourci",{d:d.toFixed(2),\r\n        de:len.toFixed(2),a:(d/sp).toFixed(2),\r\n        suite:dzmGapFate(o.tr)})',
      {'montage.source_plan.raccourci': (
          'La nouvelle source ne dure que {d} s : le plan a été raccourci de {de} s à {a} s, et la timeline garde un '
          'trou derrière lui{suite}',
          'The new source only lasts {d} s: the clip was shortened from {de} s to {a} s, and the timeline keeps a gap '
          'behind it{suite}')}),
    S(116614, '"Point d\'entrée ramené à 0 : la nouvelle source ("+\r\n      d.toFixed(2)+" s) ne va pas assez loin pour l\'ancien. Le plan garde "+\r\n      "sa durée, il ne montre plus le même morceau."',
      'dzT("montage.source_plan.entree_zero",{d:\r\n      d.toFixed(2)}\r\n      )',
      {'montage.source_plan.entree_zero': (
          "Point d'entrée ramené à 0 : la nouvelle source ({d} s) ne va pas assez loin pour l'ancien. Le plan garde "
          "sa durée, il ne montre plus le même morceau.",
          'In point reset to 0: the new source ({d} s) does not reach far enough for the old one. The clip keeps its '
          'duration, but no longer shows the same portion.')}),
    S(116838, '"Source de « "+(o.label||"ce plan")+" » remplacée par « "+\r\n      (k.label||"")+" ». Bornes, effets, transition et mixage conservés."+\r\n      (warn?" "+warn:"")+rfDit+" Annuler restaure les clips et le mixage — pas la "+\r\n      "durée du projet ni les pistes ; « Revenir à la version précédente » "+\r\n      "rend aussi l\'ancienne source."',
      'dzT("montage.source_plan.remplacee",{ancien:o.label||dzT("montage.mots.ce_plan"),\r\n      nouveau:k.label||"",\r\n      suite:(warn?" "+warn:"")+rfDit}\r\n      \r\n      )',
      {'montage.source_plan.remplacee': (
          "Source de « {ancien} » remplacée par « {nouveau} ». Bornes, effets, transition et mixage conservés.{suite} "
          "Annuler restaure les clips et le mixage — pas la durée du projet ni les pistes ; « Revenir à la version "
          "précédente » rend aussi l'ancienne source.",
          'Source of “{ancien}” replaced with “{nouveau}”. Bounds, effects, transition and mix kept.{suite} Undo '
          'restores the clips and the mix — not the project duration or the tracks; “Revert to previous version” '
          'also restores the old source.'),
       'montage.mots.ce_plan': _CE_PLAN}),

    # dzmRevertSrc : rendre au plan sa source précédente
    S(118143, '"Source précédente rendue : « "+(last.label||"sans titre")+" », "+\r\n      "avec son point d\'entrée et sa fin d\'alors."+\r\n      (rest.length?(" "+rest.length+" version"+(rest.length>1?"s":"")+\r\n        " plus ancienne"+(rest.length>1?"s":"")+" en mémoire."):\r\n        " C\'était la dernière en mémoire.")',
      'dzT("montage.source_plan.rendue",{nom:last.label||dzT("montage.mots.sans_titre"),\r\n      suite:\r\n      (rest.length?(rest.length>1?dzT("montage.source_plan.anciennes.plusieurs",{n:rest.length})\r\n        :dzT("montage.source_plan.anciennes.un",{n:rest.length})):\r\n        dzT("montage.source_plan.derniere"))})',
      {'montage.source_plan.rendue': (
          "Source précédente rendue : « {nom} », avec son point d'entrée et sa fin d'alors.{suite}",
          'Previous source restored: “{nom}”, with its in point and end from back then.{suite}'),
       'montage.source_plan.anciennes.un': (' {n} version plus ancienne en mémoire.', ' {n} older version in memory.'),
       'montage.source_plan.anciennes.plusieurs': (' {n} versions plus anciennes en mémoire.',
                                                    ' {n} older versions in memory.'),
       'montage.source_plan.derniere': (" C'était la dernière en mémoire.", ' That was the last one in memory.'),
       'montage.mots.sans_titre': _SANS_TITRE}),

    # dzmReplaceBtn : bouton « Remplacer la source… » de l'inspecteur
    S(118825, '"Échanger le fichier source de ce plan sans toucher au montage : "+\r\n      "ses bornes sur la timeline, ses effets, sa transition et son mixage "+\r\n      "restent en place. La Bibliothèque s\'ouvre ; le clip que vous y "+\r\n      "choisirez remplacera la source au lieu d\'être ajouté."',
      'dzT("montage.source_plan.remplacer_aide"\r\n      \r\n      \r\n      )',
      {'montage.source_plan.remplacer_aide': (
          "Échanger le fichier source de ce plan sans toucher au montage : ses bornes sur la timeline, ses effets, sa "
          "transition et son mixage restent en place. La Bibliothèque s'ouvre ; le clip que vous y choisirez "
          "remplacera la source au lieu d'être ajouté.",
          "Swap this clip's source file without touching the edit: its timeline bounds, effects, transition and mix "
          'stay in place. The Library opens; the clip you pick there will replace the source instead of being '
          'added.')}),
    S(119128, '"Remplacer la source de "+(sel.label||"ce plan")',
      'dzT("montage.source_plan.remplacer_aria",{nom:sel.label||dzT("montage.mots.ce_plan")})',
      {'montage.source_plan.remplacer_aria': ('Remplacer la source de {nom}', 'Replace source of {nom}'),
       'montage.mots.ce_plan': _CE_PLAN}),
    L(119235, 'montage.source_plan.remplacer', 'Remplacer la source…', 'Replace source…'),

    # dzmRevertBtn : bouton « Revenir à la version précédente » de l'inspecteur
    S(119508, '"Rendre à ce plan sa source précédente, « "+\r\n      (last.label||"sans titre")+" », avec le point d\'entrée et la fin "+\r\n      "qu\'il avait alors. "+h.length+" version"+(h.length>1?"s":"")+\r\n      " en mémoire (10 au plus, les plus anciennes tombent)."',
      '(h.length>1?dzT("montage.source_plan.revenir_aide.plusieurs",{nom:last.label||dzT("montage.mots.sans_titre"),n:h.length})\r\n      :dzT("montage.source_plan.revenir_aide.un",{nom:last.label||dzT("montage.mots.sans_titre"),n:h.length})\r\n      \r\n      )',
      {'montage.source_plan.revenir_aide.un': (
          "Rendre à ce plan sa source précédente, « {nom} », avec le point d'entrée et la fin qu'il avait alors. {n} "
          "version en mémoire (10 au plus, les plus anciennes tombent).",
          'Give this clip back its previous source, “{nom}”, with the in point and end it had then. {n} version in '
          'memory (10 max, the oldest drop off).'),
       'montage.source_plan.revenir_aide.plusieurs': (
          "Rendre à ce plan sa source précédente, « {nom} », avec le point d'entrée et la fin qu'il avait alors. {n} "
          "versions en mémoire (10 au plus, les plus anciennes tombent).",
          'Give this clip back its previous source, “{nom}”, with the in point and end it had then. {n} versions in '
          'memory (10 max, the oldest drop off).'),
       'montage.mots.sans_titre': _SANS_TITRE}),
    S(119780, '"Revenir à la source précédente de "+(sel.label||"ce plan")',
      'dzT("montage.source_plan.revenir_aria",{nom:sel.label||dzT("montage.mots.ce_plan")})',
      {'montage.source_plan.revenir_aria': ('Revenir à la source précédente de {nom}',
                                            'Revert to the previous source of {nom}'),
       'montage.mots.ce_plan': _CE_PLAN}),
    L(119904, 'montage.source_plan.revenir', 'Revenir à la version précédente', 'Revert to previous version'),

    # DZM_NEWER_H, dzmNewerLine, DzmNewerHint : le rappel « rendus plus récents portant ce titre »
    L(124357, 'montage.versions.entete', 'Rendus plus récents portant ce titre', 'Newer renders with this title'),
    L(124598, 'montage.versions.duree_inconnue', 'durée inconnue', 'unknown duration'),
    L(124649, 'montage.mots.sans_titre', 'sans titre', 'untitled'),
    L(124691, 'montage.versions.remplacer', ' — remplacer', ' — replace'),
    S(125939, '"Versions plus récentes : recherche "+\r\n        "impossible (le service n\'a pas répondu)."',
      'dzT("montage.versions.erreur"\r\n        )',
      {'montage.versions.erreur': ("Versions plus récentes : recherche impossible (le service n'a pas répondu).",
                                   'Newer versions: search failed (the service did not respond).')}),
    S(126417, '"Rapprochement par le TITRE du rendu — une heuristique, pas un "+\r\n        "lien enregistré : rien en base ne relie deux rendus du même plan. "+\r\n        "Le titre étant la clé du rapprochement, TOUS les candidats le "+\r\n        "partagent : ce qui les distingue, c\'est la date et la durée "+\r\n        "portées par la ligne. Vérifiez-les avant de remplacer."+\r\n        (c.completed_at?(" Terminé le "+dzmProjWhen(c.completed_at,1)+"."):"")',
      'dzT("montage.versions.aide",{fin:\r\n        \r\n        \r\n        \r\n        \r\n        c.completed_at?dzT("montage.versions.termine",{date:dzmProjWhen(c.completed_at,1)}):""})',
      {'montage.versions.aide': (
          "Rapprochement par le TITRE du rendu — une heuristique, pas un lien enregistré : rien en base ne relie deux "
          "rendus du même plan. Le titre étant la clé du rapprochement, TOUS les candidats le partagent : ce qui les "
          "distingue, c'est la date et la durée portées par la ligne. Vérifiez-les avant de remplacer.{fin}",
          'Matched by render TITLE — a heuristic, not a saved link: nothing in the database links two renders of the '
          'same clip. Since the title is the matching key, ALL candidates share it: what sets them apart is the date '
          'and duration on the line. Check them before replacing.{fin}'),
       'montage.versions.termine': (' Terminé le {date}.', ' Finished {date}.')}),

    # DZM_DUR_UNDO : rappel commun des notes et infobulles du contrôle de durée
    S(131169, '" « Annuler » (Ctrl+Z) rend aussi la durée du projet : elle "+\r\n  "entre dans l\'historique depuis le 21/09/2026, avec les pistes, le style "+\r\n  "des sous-titres, la plage et les marqueurs."',
      'dzT("montage.duree_tl.annuler"\r\n  \r\n  )',
      {'montage.duree_tl.annuler': (
          " « Annuler » (Ctrl+Z) rend aussi la durée du projet : elle entre dans l'historique depuis le 21/09/2026, "
          "avec les pistes, le style des sous-titres, la plage et les marqueurs.",
          ' “Undo” (Ctrl+Z) also restores the project duration: it has been part of the history since 21/09/2026, '
          'along with the tracks, the subtitle style, the range and the markers.')}),

    # dzmDurCtl : notes des gestes − / + / ajuster
    S(133961, '"La timeline fait déjà la longueur de son "+\r\n      "contenu ("+dzmDurTxt(fit)+", fin du dernier clip) : la raccourcir "+\r\n      "ferait sortir des clips du champ — ils ne seraient pas supprimés, "+\r\n      "mais plus rien ne les montrerait. Déplacez ou retirez d\'abord le "+\r\n      "dernier clip."',
      'dzT("montage.duree_tl.deja_minimale",{\r\n      fin:dzmDurTxt(fit)}\r\n      \r\n      \r\n      )',
      {'montage.duree_tl.deja_minimale': (
          "La timeline fait déjà la longueur de son contenu ({fin}, fin du dernier clip) : la raccourcir ferait sortir "
          "des clips du champ — ils ne seraient pas supprimés, mais plus rien ne les montrerait. Déplacez ou retirez "
          "d'abord le dernier clip.",
          'The timeline is already as long as its content ({fin}, end of the last clip): shortening it would push '
          'clips out of view — they would not be deleted, but nothing would show them anymore. Move or remove the '
          'last clip first.')}),
    S(134347, '"Timeline raccourcie de "+dzmDurTxt(d)+" à "+dzmDurTxt(nv)+\r\n      (nv>vise?(" — le pas de "+dzmSecs(stp)+" s\'est arrêté sur la fin du "+\r\n        "dernier clip : aucun clip ne sort du champ."):"")+\r\n      " Aucun clip n\'a bougé."',
      'dzT("montage.duree_tl.raccourcie",{de:dzmDurTxt(d),a:dzmDurTxt(nv),\r\n      arret:nv>vise?dzT("montage.duree_tl.pas_arrete",{pas:dzmSecs(stp)}):""}\r\n        \r\n      )',
      {'montage.duree_tl.raccourcie': ("Timeline raccourcie de {de} à {a}{arret} Aucun clip n'a bougé.",
                                       'Timeline shortened from {de} to {a}{arret} No clip moved.'),
       'montage.duree_tl.pas_arrete': (
           " — le pas de {pas} s'est arrêté sur la fin du dernier clip : aucun clip ne sort du champ.",
           ' — the {pas} step stopped at the end of the last clip: no clip leaves the view.')}),
    S(134655, '"Timeline allongée de "+dzmDurTxt(d)+" à "+dzmDurTxt(nv)+\r\n      " (+"+dzmSecs(stp)+"). Aucun clip n\'a bougé."',
      'dzT("montage.duree_tl.allongee",{de:dzmDurTxt(d),a:dzmDurTxt(nv),\r\n      pas:dzmSecs(stp)})',
      {'montage.duree_tl.allongee': ("Timeline allongée de {de} à {a} (+{pas}). Aucun clip n'a bougé.",
                                     'Timeline extended from {de} to {a} (+{pas}). No clip moved.')}),
    S(134803, '"Timeline ajustée à son contenu : "+dzmDurTxt(d)+" → "+\r\n      dzmDurTxt(fit)+", soit "+dzmSecs(vide)+" de queue vide retirés. "+\r\n      "Aucun clip n\'a bougé."',
      'dzT("montage.duree_tl.ajustee",{de:dzmDurTxt(d),\r\n      a:dzmDurTxt(fit),vide:dzmSecs(vide)}\r\n      )',
      {'montage.duree_tl.ajustee': (
          "Timeline ajustée à son contenu : {de} → {a}, soit {vide} de queue vide retirés. Aucun clip n'a bougé.",
          'Timeline fitted to its content: {de} → {a}, {vide} of empty tail removed. No clip moved.')}),

    # dzmDurCtl : boutons − / + / ajuster et valeur affichée
    S(135018, '"Raccourcir la timeline d\'une graduation ("+dzmSecs(stp)+"). Le "+\r\n      "raccourcissement s\'arrête sur la fin du dernier clip : aucun clip ne "+\r\n      "peut sortir du champ."',
      'dzT("montage.duree_tl.moins_aide",{pas:dzmSecs(stp)}\r\n      \r\n      )',
      {'montage.duree_tl.moins_aide': (
          "Raccourcir la timeline d'une graduation ({pas}). Le raccourcissement s'arrête sur la fin du dernier clip : "
          "aucun clip ne peut sortir du champ.",
          'Shorten the timeline by one tick ({pas}). Shortening stops at the end of the last clip: no clip can leave '
          'the view.')}),
    S(135217, '"Raccourcir la timeline de "+dzmSecs(stp)',
      'dzT("montage.duree_tl.moins_aria",{pas:dzmSecs(stp)})',
      {'montage.duree_tl.moins_aria': ('Raccourcir la timeline de {pas}', 'Shorten the timeline by {pas}')}),
    S(135325, '"Durée de la timeline — une BORNE D\'ÉDITION, pas une propriété "+\r\n        "du film : le rendu recalcule sa durée depuis les plans, cette "+\r\n        "valeur ne lui est jamais envoyée. Les boutons − et + la règlent "+\r\n        "d\'une graduation de la règle ("+dzmSecs(stp)+")."',
      'dzT("montage.duree_tl.valeur_aide",\r\n        \r\n        \r\n        {pas:dzmSecs(stp)})',
      {'montage.duree_tl.valeur_aide': (
          "Durée de la timeline — une BORNE D'ÉDITION, pas une propriété du film : le rendu recalcule sa durée depuis "
          "les plans, cette valeur ne lui est jamais envoyée. Les boutons − et + la règlent d'une graduation de la "
          "règle ({pas}).",
          'Timeline duration — an EDITING LIMIT, not a property of the film: the render recomputes its duration from '
          'the clips, this value is never sent to it. The − and + buttons adjust it by one ruler tick ({pas}).')}),
    X(135646, '« total » identique dans les deux langues'),
    S(135700, '"Allonger la timeline d\'une graduation ("+dzmSecs(stp)+")."',
      'dzT("montage.duree_tl.plus_aide",{pas:dzmSecs(stp)})',
      {'montage.duree_tl.plus_aide': ("Allonger la timeline d'une graduation ({pas}).",
                                      'Extend the timeline by one tick ({pas}).')}),
    S(135789, '"Allonger la timeline de "+dzmSecs(stp)',
      'dzT("montage.duree_tl.plus_aria",{pas:dzmSecs(stp)})',
      {'montage.duree_tl.plus_aria': ('Allonger la timeline de {pas}', 'Extend the timeline by {pas}')}),
    L(136044, 'montage.duree_tl.ajuster', 'ajuster', 'fit'),
    S(136060, '"Ramener la fin de la timeline sur le dernier clip : "+dzmSecs(vide)+\r\n    " de vide à retirer. Aucun clip ne bouge ni ne disparaît."',
      'dzT("montage.duree_tl.ajuster_aide",{vide:dzmSecs(vide)}\r\n    )',
      {'montage.duree_tl.ajuster_aide': (
          'Ramener la fin de la timeline sur le dernier clip : {vide} de vide à retirer. Aucun clip ne bouge ni ne '
          'disparaît.',
          'Bring the end of the timeline back to the last clip: {vide} of empty space to remove. No clip moves or '
          'disappears.')}),
    L(136213, 'montage.duree_tl.ajuster_aria', 'Ajuster la timeline à son contenu', 'Fit the timeline to its content'),

    # dzmClipLen : la longueur donnée au clip posé (note concaténée à celle de l'ajout)
    X(141877, 'genre de clip (« audio » / « video ») : clé de DZM_CLIP_DEFAUTS, jamais affiché'),
    S(142006, '" Le clip fait "+dzmSecs(v)+", la longueur ENTIÈRE de la source."',
      'dzT("montage.longueur.source",{d:dzmSecs(v)})',
      {'montage.longueur.source': (' Le clip fait {d}, la longueur ENTIÈRE de la source.',
                                   ' The clip is {d}, the FULL length of the source.')}),
    S(142412, '" "+(k==="audio"?"Ce son a été posé":"Cette vidéo a été posée")\r\n      +" à "+dzmSecs(r)+" — une longueur PAR DÉFAUT, pas la sienne : "+\r\n      "l\'application n\'a pas pu mesurer la durée de cette source. Rognez le "+\r\n      "bord droit du clip pour lui donner sa vraie longueur."',
      '(k==="audio"?dzT("montage.longueur.repli_son",{d:dzmSecs(r)})\r\n      :dzT("montage.longueur.repli_video",{d:dzmSecs(r)})\r\n      \r\n      )',
      {'montage.longueur.repli_son': (
          " Ce son a été posé à {d} — une longueur PAR DÉFAUT, pas la sienne : l'application n'a pas pu mesurer la "
          "durée de cette source. Rognez le bord droit du clip pour lui donner sa vraie longueur.",
          " This sound was placed at {d} — a DEFAULT length, not its own: the app could not measure this source's "
          "duration. Trim the clip's right edge to give it its real length."),
       'montage.longueur.repli_video': (
          " Cette vidéo a été posée à {d} — une longueur PAR DÉFAUT, pas la sienne : l'application n'a pas pu "
          "mesurer la durée de cette source. Rognez le bord droit du clip pour lui donner sa vraie longueur.",
          " This video was placed at {d} — a DEFAULT length, not its own: the app could not measure this source's "
          "duration. Trim the clip's right edge to give it its real length.")}),

    # dzmAskDur : motif rendu au rappel
    X(146177, 'motif technique rendu au rappel, comparé ailleurs (v.pourquoi==="mesure")'),

    # dzmSubsSources : envoi de la piste de dialogue à la transcription (étape affichée et note)
    S(152902, '"envoi…":n===1?"envoi de "+list[0].label+"…"\r\n        :"envoi de "+n+" clips de "+piste+"…"',
      'dzT("montage.transcription.envoi"):n===1?dzT("montage.transcription.envoi_un",{nom:list[0].label})\r\n        :dzT("montage.transcription.envoi_plusieurs",{n:n,piste:piste})',
      {'montage.transcription.envoi': ('envoi…', 'sending…'),
       'montage.transcription.envoi_un': ('envoi de {nom}…', 'sending {nom}…'),
       'montage.transcription.envoi_plusieurs': ('envoi de {n} clips de {piste}…', 'sending {n} clips from {piste}…')}),
    S(153024, '"Aucun clip de la piste "+(dial||"de dialogue").toUpperCase()+\r\n       " ne porte de son : la vidéo "+noms[0]+" de V1 est envoyée entière, "+\r\n       "ses répliques posées à son instant."',
      'dzT("montage.transcription.repli",{piste:(dial||dzT("montage.transcription.de_dialogue")).toUpperCase(),\r\n       nom:noms[0]}\r\n       )',
      {'montage.transcription.repli': (
          'Aucun clip de la piste {piste} ne porte de son : la vidéo {nom} de V1 est envoyée entière, ses répliques '
          'posées à son instant.',
          'No clip on the {piste} track has sound: the video {nom} from V1 is sent whole, its lines placed at its '
          'time.'),
       'montage.transcription.de_dialogue': ('de dialogue', 'dialogue')}),
    S(153220, '"Envoyé : "+n+" clip"+(n>1?"s":"")+\r\n       (keys.length<n?" ("+keys.length+" fichier"+(keys.length>1?"s":"")+")":"")+\r\n       " de la piste "+piste+" — "+noms.join(", ")+" — "+dzmSecs(total)+\r\n       " de son, chaque réplique posée à l\'instant de son clip. Chaque fichier "+\r\n       "part entier chez le moteur : un clip rogné coûte la durée de son fichier."',
      'dzT("montage.transcription.envoye",{clips:n>1?dzT("montage.transcription.clips.plusieurs",{n:n}):dzT("montage.transcription.clips.un",{n:n}),\r\n       fichiers:keys.length<n?(keys.length>1?dzT("montage.transcription.fichiers.plusieurs",{n:keys.length}):dzT("montage.transcription.fichiers.un",{n:keys.length})):"",\r\n       piste:piste,noms:noms.join(", "),duree:dzmSecs(total)}\r\n       \r\n       )',
      {'montage.transcription.envoye': (
          "Envoyé : {clips}{fichiers} de la piste {piste} — {noms} — {duree} de son, chaque réplique posée à "
          "l'instant de son clip. Chaque fichier part entier chez le moteur : un clip rogné coûte la durée de son "
          "fichier.",
          "Sent: {clips}{fichiers} from track {piste} — {noms} — {duree} of audio, each line placed at its clip's "
          "time. Each file goes whole to the engine: a trimmed clip costs its file's duration."),
       'montage.transcription.clips.un': ('{n} clip', '{n} clip'),
       'montage.transcription.clips.plusieurs': ('{n} clips', '{n} clips'),
       'montage.transcription.fichiers.un': (' ({n} fichier)', ' ({n} file)'),
       'montage.transcription.fichiers.plusieurs': (' ({n} fichiers)', ' ({n} files)')}),

    # dzmSubsTrLabel / Enabled / Title / Note : traduire les répliques de S1
    S(155017, '"Traduire vers "+dzmSubsTrLangLab(target,langs)',
      'dzT("montage.trad_s1.vers",{langue:dzmSubsTrLangLab(target,langs)})',
      {'montage.trad_s1.vers': ('Traduire vers {langue}', 'Translate to {langue}')}),
    L(155658, 'montage.trad_s1.occupe', 'Un travail est déjà en cours — attendez sa fin.',
      'A job is already running — wait for it to finish.'),
    L(155746, 'montage.trad_s1.vide', 'Aucune réplique à traduire : la piste S1 est vide.',
      'No line to translate: track S1 is empty.'),
    S(155876, '"Aucune clé LLM configurée (Réglages) — le coût ne peut pas être "+\r\n    "annoncé, donc rien n\'est lancé."',
      'dzT("montage.trad_s1.sans_cle"\r\n    )',
      {'montage.trad_s1.sans_cle': (
          "Aucune clé LLM configurée (Réglages) — le coût ne peut pas être annoncé, donc rien n'est lancé.",
          'No LLM key configured (Settings) — the cost cannot be announced, so nothing is started.')}),
    S(156066, '"REMPLACE le texte de la réplique de S1 par sa "+\r\n    "traduction ; son temps est conservé. « Annuler » de la timeline "+\r\n    "restaure le texte d\'avant (le remplacement pousse une entrée "+\r\n    "d\'historique avant d\'écrire). Piste S1 verrouillée : rien n\'est "+\r\n    "écrit, et l\'écran le dit."',
      'dzT("montage.trad_s1.aide.un"\r\n    \r\n    \r\n    \r\n    )',
      {'montage.trad_s1.aide.un': (
          "REMPLACE le texte de la réplique de S1 par sa traduction ; son temps est conservé. « Annuler » de la "
          "timeline restaure le texte d'avant (le remplacement pousse une entrée d'historique avant d'écrire). Piste "
          "S1 verrouillée : rien n'est écrit, et l'écran le dit.",
          'REPLACES the text of the S1 line with its translation; its timing is kept. The timeline’s “Undo” restores '
          'the previous text (the replacement pushes a history entry before writing). Track S1 locked: nothing is '
          'written, and the screen says so.')}),
    S(156376, '"REMPLACE le texte des "+n+" répliques de S1 par leur traduction ; "+\r\n    "leurs temps sont conservés. « Annuler » de la timeline restaure le "+\r\n    "texte d\'avant (le remplacement pousse une entrée d\'historique avant "+\r\n    "d\'écrire). Piste S1 verrouillée : rien n\'est écrit, et l\'écran le dit."',
      'dzT("montage.trad_s1.aide.plusieurs",{n:n}\r\n    \r\n    \r\n    )',
      {'montage.trad_s1.aide.plusieurs': (
          "REMPLACE le texte des {n} répliques de S1 par leur traduction ; leurs temps sont conservés. « Annuler » de "
          "la timeline restaure le texte d'avant (le remplacement pousse une entrée d'historique avant d'écrire). "
          "Piste S1 verrouillée : rien n'est écrit, et l'écran le dit.",
          'REPLACES the text of the {n} S1 lines with their translation; their timings are kept. The timeline’s '
          '“Undo” restores the previous text (the replacement pushes a history entry before writing). Track S1 '
          'locked: nothing is written, and the screen says so.')}),
    S(156729, 'n+" réplique"+(n>1?"s":"")+" traduite"+(n>1?"s":"")+" vers "+\r\n    dzmSubsTrLangLab(target,langs)+" — relisez, la machine se trompe."',
      '(n>1?dzT("montage.trad_s1.note.plusieurs",{n:n,langue:dzmSubsTrLangLab(target,langs)})\r\n    :dzT("montage.trad_s1.note.un",{n:n,langue:dzmSubsTrLangLab(target,langs)}))',
      {'montage.trad_s1.note.un': ('{n} réplique traduite vers {langue} — relisez, la machine se trompe.',
                                   '{n} line translated to {langue} — proofread it, machines make mistakes.'),
       'montage.trad_s1.note.plusieurs': ('{n} répliques traduites vers {langue} — relisez, la machine se trompe.',
                                          '{n} lines translated to {langue} — proofread them, machines make '
                                          'mistakes.')}),
]
