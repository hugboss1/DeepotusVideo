"""t143 — montage_b : couche Montage (frontend/patches/montage.js), lignes 1036–1946 de la base be7f9e9f. Couvre :
le tiroir Texte (DzmTextDrawer : en-tête, mots cliquables et leurs bulles hésitation / mot béquille, boutons « couper
la sélection » et « retirer les N euh » avec leurs titres, erreurs de la lecture des mots), le bouton « étalonnage →
tous les plans » (dzmGradeAllBtn : titre selon le lot, libellé, note après application) et le popover des projets
nommés (DzmProjects : bouton, liste, cartes, armement ouvrir / supprimer / nouveau, enregistrer sous…, toutes ses
notes et erreurs).

Gardés : « UTC » (dzmProjWhen, identique dans les deux langues) et « clip » de dzmProjLine (n clip(s) : identique
en anglais, pluriel en « s » compris). Pas touchés (hors contrôle, ce sont des valeurs) : le nom par défaut
`nm="montage"`, qui part au serveur dans le nom de la copie de sûreté (dzmInstantaneNom), les kind
"hesitation"/"tic" comparés, les états d'armement "n"/"o"+id/"x"+id, et « ok » (bouton de validation du renommage).
« ouvrir » et « nouveau » ne sont pas signalés par le contrôle mais sont des libellés de bouton affichés : traduits.
Le suffixe « (copie) » cité dans le titre de Dupliquer est celui que le SERVEUR ajoute : laissé tel quel en anglais.

Les phrases coupées en morceaux concaténés (titres de couper / retirer, titre et note de l'étalonnage global, notes
d'ouverture et de suppression, titres des boutons de carte) sont recomposées en une seule clé (S) dont le code
`apres` garde AUTANT de fins de ligne que le code `avant`. Pluriels (« N plage(s) », « N autre(s) plan(s) »,
« N mot(s) souligné(s) », « N enregistré(s) ») : deux clés .._un / .._plusieurs, choisies dans le code. Le français
recomposé reproduit à l'octet ce que la concaténation produisait (les bancs node lisent le français)."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_REQ_IMPOSSIBLE = ('requête impossible', 'request not possible')
_SANS_NOM = ('sans nom', 'untitled')

_RETIRER_FIN = (" de la fin vers le début pour que les précédentes ne se décalent pas. Seules les HÉSITATIONS "
                "partent ainsi ; les mots béquille soulignés se coupent à la sélection, un par un. Annuler défait la "
                "coupe entièrement. La durée du projet ne bouge pas : la fin de la timeline est maintenant vide, "
                "raccourcissez-la si vous voulez.")
_RETIRER_FIN_EN = (" from the end to the start so the earlier ones do not shift. Only HESITATIONS go this way; the "
                   "underlined filler words are cut with the selection, one by one. Undo reverts the cut entirely. The "
                   "project duration does not change: the end of the timeline is now empty, shorten it if you like.")

_RECOPIER_FIN = (". Les bornes de temps de l'effet ne sont pas recopiées : l'étalonnage porte sur le plan entier. "
                 "Annuler restaure l'étalonnage de chaque plan tel qu'il était.")
_RECOPIER_FIN_EN = (". The effect's time bounds are not copied: the grade covers the whole clip. Undo restores each "
                    "clip's grade as it was.")
_APPLIQUE_FIN = ". Les bornes de temps ne sont pas recopiées. Annuler restaure l'étalonnage de chaque plan tel qu'il était."
_APPLIQUE_FIN_EN = ". Time bounds are not copied. Undo restores each clip's grade as it was."

ENTREES = [
    # DzmTextDrawer : lecture des mots de la narration (erreurs montrées dans le tiroir)
    L(63113, 'montage.texte.aucun_mot_cale', 'Aucun mot calé sur la narration.', 'No word aligned to the narration.'),
    L(63413, 'montage.texte.echec_requete', 'échec de la requête', 'request failed'),
    L(63615, 'montage.texte.rien_a_couper', 'Rien à couper : la sélection est vide.',
      'Nothing to cut: the selection is empty.'),
    L(63692, 'montage.texte.pas_de_receveur', 'Texte : rien pour recevoir la coupe.',
      'Text: nothing to receive the cut.'),

    # DzmTextDrawer : en-tête
    L(65887, 'montage.texte.titre', 'Texte', 'Text'),
    S(65986, 'words.length+" mots"', 'dzT("montage.texte.n_mots",{n:words.length})',
      {'montage.texte.n_mots': ('{n} mots', '{n} words')}),

    # DzmTextDrawer : bulle d'un mot
    L(66411, 'montage.texte.hesitation', 'Hésitation — ', 'Hesitation — '),
    S(66462, '"Mot béquille (mot plein : à couper à la "+\r\n                   "main, jamais en bloc) — "',
      'dzT("montage.texte.tic"\r\n                   )',
      {'montage.texte.tic': ('Mot béquille (mot plein : à couper à la main, jamais en bloc) — ',
                             'Filler word (a full word: cut it by hand, never in bulk) — ')}),
    L(66618, 'montage.texte.sans_temps', 'sans temps', 'no timing'),
    L(66646, 'montage.texte.mot_aide', ' · cliquer, Maj+clic ou glisser pour étendre la sélection',
      ' · click, Shift+click or drag to extend the selection'),

    # DzmTextDrawer : bouton « couper la sélection »
    S(67678, '"Couper de "+rgSel[0].toFixed(2)+" s à "+rgSel[1].toFixed(2)+\r\n            " s sur toutes les pistes non verrouillées : ce qui suit remonte. "+\r\n            "Annuler défait la coupe entièrement. La durée du projet ne bouge "+\r\n            "pas : la fin de la timeline est maintenant vide, raccourcissez-la "+\r\n            "si vous voulez."',
      'dzT("montage.texte.couper_aide",{a:rgSel[0].toFixed(2),b:rgSel[1].toFixed(2)}\r\n            \r\n            \r\n            \r\n            )',
      {'montage.texte.couper_aide': (
          'Couper de {a} s à {b} s sur toutes les pistes non verrouillées : ce qui suit remonte. Annuler défait la '
          'coupe entièrement. La durée du projet ne bouge pas : la fin de la timeline est maintenant vide, '
          'raccourcissez-la si vous voulez.',
          'Cut from {a} s to {b} s on all unlocked tracks: what follows moves up. Undo reverts the cut entirely. The '
          'project duration does not change: the end of the timeline is now empty, shorten it if you like.')}),
    S(68031, '"Sélectionnez des mots (clic, Maj+clic, ou clic-glissé du premier "+\r\n           "au dernier)"',
      'dzT("montage.texte.selectionner_aide"\r\n           )',
      {'montage.texte.selectionner_aide': (
          'Sélectionnez des mots (clic, Maj+clic, ou clic-glissé du premier au dernier)',
          'Select words (click, Shift+click, or click-drag from the first to the last)')}),
    L(68188, 'montage.texte.couper', 'couper la sélection', 'cut the selection'),

    # DzmTextDrawer : bouton « retirer les N euh »
    S(68333, '"Retirer "+hesMots.map(function(m){return "« "+m+" »"}).join(", ")+\r\n            " — "+hes.length+" plage"+(hes.length>1?"s":"")+", de la fin vers "+\r\n            "le début pour que les précédentes ne se décalent pas. Seules les "+\r\n            "HÉSITATIONS partent ainsi ; les mots béquille soulignés se "+\r\n            "coupent à la sélection, un par un. Annuler défait la coupe "+\r\n            "entièrement. La durée du projet ne bouge pas : la fin de la "+\r\n            "timeline est maintenant vide, raccourcissez-la si vous voulez."',
      'dzT(hes.length>1?"montage.texte.retirer_aide_plusieurs":"montage.texte.retirer_aide_un",\r\n            {mots:hesMots.map(function(m){return dzT("montage.texte.mot_cite",{m:m})}).join(", "),\r\n            n:hes.length}\r\n            \r\n            \r\n            \r\n            )',
      {'montage.texte.retirer_aide_un': ('Retirer {mots} — {n} plage,' + _RETIRER_FIN,
                                         'Remove {mots} — {n} range,' + _RETIRER_FIN_EN),
       'montage.texte.retirer_aide_plusieurs': ('Retirer {mots} — {n} plages,' + _RETIRER_FIN,
                                                'Remove {mots} — {n} ranges,' + _RETIRER_FIN_EN),
       'montage.texte.mot_cite': ('« {m} »', '“{m}”')}),
    S(68913, '"Aucune hésitation. Les "+spans.length+" mot"+\r\n             (spans.length>1?"s":"")+" souligné"+(spans.length>1?"s":"")+\r\n             " sont des mots PLEINS : à couper à la sélection, en les lisant."',
      '(spans.length>1?dzT("montage.texte.aucune_hesitation_plusieurs",{n:spans.length}):\r\n             dzT("montage.texte.aucune_hesitation_un",{n:spans.length})\r\n             )',
      {'montage.texte.aucune_hesitation_un': (
          'Aucune hésitation. Les {n} mot souligné sont des mots PLEINS : à couper à la sélection, en les lisant.',
          'No hesitation. The {n} underlined word is a FULL word: cut it with the selection, reading it.'),
       'montage.texte.aucune_hesitation_plusieurs': (
          'Aucune hésitation. Les {n} mots soulignés sont des mots PLEINS : à couper à la sélection, en les lisant.',
          'No hesitation. The {n} underlined words are FULL words: cut them with the selection, reading them.')}),
    L(69129, 'montage.texte.aucun_remplissage', 'Aucun mot de remplissage repéré dans cette narration',
      'No filler word found in this narration'),
    S(69308, '"retirer les "+hes.length+" « euh »"', 'dzT("montage.texte.retirer_euh",{n:hes.length})',
      {'montage.texte.retirer_euh': ('retirer les {n} « euh »', 'remove the {n} “uh”')}),
    L(69358, 'montage.texte.aucun_euh', 'aucun « euh »', 'no “uh”'),

    # dzmGradeAllBtn : titre selon le lot (plans à changer / déjà à jour / aucun autre plan)
    S(77733, '"Recopier l\'exposition, le contraste, la saturation et la "+\r\n        "température de ce plan sur "+pv.applied+" autre"+\r\n        (pv.applied>1?"s":"")+" plan"+(pv.applied>1?"s":"")+" "+TR+\r\n        (pv.replaced?(", dont "+pv.replaced+" dont l\'étalonnage actuel sera "+\r\n                      "REMPLACÉ"):"")+". Les bornes de temps de l\'effet ne "+\r\n        "sont pas recopiées : l\'étalonnage porte sur le plan entier. Annuler "+\r\n        "restaure l\'étalonnage de chaque plan tel qu\'il était."',
      'dzT(pv.applied>1?"montage.etalonnage.recopier_plusieurs":"montage.etalonnage.recopier_un",\r\n        {n:pv.applied,piste:TR,\r\n        \r\n        dont:pv.replaced?dzT("montage.etalonnage.dont_remplace",{n:pv.replaced}):""}\r\n                      \r\n        \r\n        )',
      {'montage.etalonnage.recopier_un': (
          "Recopier l'exposition, le contraste, la saturation et la température de ce plan sur {n} autre plan "
          "{piste}{dont}" + _RECOPIER_FIN,
          "Copy this clip's exposure, contrast, saturation and temperature to {n} other {piste} clip{dont}"
          + _RECOPIER_FIN_EN),
       'montage.etalonnage.recopier_plusieurs': (
          "Recopier l'exposition, le contraste, la saturation et la température de ce plan sur {n} autres plans "
          "{piste}{dont}" + _RECOPIER_FIN,
          "Copy this clip's exposure, contrast, saturation and temperature to {n} other {piste} clips{dont}"
          + _RECOPIER_FIN_EN),
       'montage.etalonnage.dont_remplace': (", dont {n} dont l'étalonnage actuel sera REMPLACÉ",
                                            ", {n} of which will have their current grade REPLACED")}),
    S(78267, '"Les "+pv.targets+" autres plans "+TR+" portent déjà exactement "+\r\n          "cet étalonnage."',
      'dzT("montage.etalonnage.deja_plusieurs",{n:pv.targets,piste:TR}\r\n          )',
      {'montage.etalonnage.deja_plusieurs': ('Les {n} autres plans {piste} portent déjà exactement cet étalonnage.',
                                             'The {n} other {piste} clips already carry exactly this grade.')}),
    S(78375, '"Le seul autre plan "+TR+" porte déjà exactement cet étalonnage."',
      'dzT("montage.etalonnage.deja_un",{piste:TR})',
      {'montage.etalonnage.deja_un': ('Le seul autre plan {piste} porte déjà exactement cet étalonnage.',
                                      'The only other {piste} clip already carries exactly this grade.')}),
    S(78451, '"Aucun autre plan "+TR+" : rien à étalonner ailleurs."',
      'dzT("montage.etalonnage.aucun_autre",{piste:TR})',
      {'montage.etalonnage.aucun_autre': ('Aucun autre plan {piste} : rien à étalonner ailleurs.',
                                          'No other {piste} clip: nothing else to grade.')}),
    # dzmGradeAllBtn : libellé (aussi préfixe de l'aria-label)
    S(78519, '"étalonnage → tous les plans "+TR', 'dzT("montage.etalonnage.tous_les_plans",{piste:TR})',
      {'montage.etalonnage.tous_les_plans': ('étalonnage → tous les plans {piste}', 'grade → all {piste} clips')}),
    # dzmGradeAllBtn : note après application
    S(79245, '"Étalonnage appliqué à "+res.applied+" plan"+\r\n        (res.applied>1?"s":"")+" "+TR+\r\n        (res.replaced?(" (dont "+res.replaced+" dont l\'étalonnage a été "+\r\n                       "remplacé)"):"")+\r\n        ". Les bornes de temps ne sont pas recopiées. Annuler restaure "+\r\n        "l\'étalonnage de chaque plan tel qu\'il était."',
      'dzT(res.applied>1?"montage.etalonnage.applique_plusieurs":"montage.etalonnage.applique_un",\r\n        {n:res.applied,piste:TR,\r\n        dont:res.replaced?dzT("montage.etalonnage.dont_a_ete_remplace",{n:res.replaced}):""}\r\n                       \r\n        \r\n        )',
      {'montage.etalonnage.applique_un': ('Étalonnage appliqué à {n} plan {piste}{dont}' + _APPLIQUE_FIN,
                                          'Grade applied to {n} {piste} clip{dont}' + _APPLIQUE_FIN_EN),
       'montage.etalonnage.applique_plusieurs': ('Étalonnage appliqué à {n} plans {piste}{dont}' + _APPLIQUE_FIN,
                                                 'Grade applied to {n} {piste} clips{dont}' + _APPLIQUE_FIN_EN),
       'montage.etalonnage.dont_a_ete_remplace': (" (dont {n} dont l'étalonnage a été remplacé)",
                                                  ' ({n} of which had their grade replaced)')}),

    # dzmProjWhen / dzmProjLine : ligne d'une carte de projet
    X(82302, 'suffixe « UTC » de la date stockée : identique dans les deux langues'),
    X(82541, '« n clip(s) » : identique en anglais (pluriel en s compris)'),

    # DzmProjects : erreurs et notes
    L(85412, 'montage.projets.requete_impossible', *_REQ_IMPOSSIBLE),
    S(88030, '"Liste des projets occupée — ouvrez « "+p.name+" » depuis ☰ › Projets."',
      'dzT("montage.projets.liste_occupee",{nom:p.name})',
      {'montage.projets.liste_occupee': ('Liste des projets occupée — ouvrez « {nom} » depuis ☰ › Projets.',
                                         'Project list busy — open “{nom}” from ☰ › Projects.')}),
    S(89471, '"Montage enregistré sous « "+d.name+" ». Les modifications "+\r\n          "suivantes y vont toutes seules, sans un geste de plus."',
      'dzT("montage.projets.enregistre_sous",{nom:d.name}\r\n          )',
      {'montage.projets.enregistre_sous': (
          'Montage enregistré sous « {nom} ». Les modifications suivantes y vont toutes seules, sans un geste de plus.',
          'Edit saved as “{nom}”. Further changes go there on their own, with no extra step.')}),
    S(91236, '"Copie de sûreté impossible ("+((e&&e.message)||"requête impossible")+\r\n            ") — ouverture annulée"',
      'dzT("montage.projets.surete_impossible",{e:(e&&e.message)||dzT("montage.projets.requete_impossible")}\r\n            )',
      {'montage.projets.surete_impossible': ('Copie de sûreté impossible ({e}) — ouverture annulée',
                                             'Safety copy failed ({e}) — opening cancelled'),
       'montage.projets.requete_impossible': _REQ_IMPOSSIBLE}),
    S(92148, '"« "+p.name+" » ouvert. Le montage précédent a été remplacé"+\r\n            (sauve?" — il est à l\'abri sous « "+sauve+" »"\r\n              :" : s\'il n\'était pas enregistré sous un nom, il n\'existe plus")+\r\n            ", et « annuler » ne le rend pas."',
      'dzT(sauve?"montage.projets.ouvert_copie":"montage.projets.ouvert_perdu",\r\n            {nom:p.name,copie:sauve}\r\n              \r\n            )',
      {'montage.projets.ouvert_copie': (
          "« {nom} » ouvert. Le montage précédent a été remplacé — il est à l'abri sous « {copie} », et « annuler » "
          "ne le rend pas.",
          '“{nom}” opened. The previous edit was replaced — it is safe under “{copie}”, and “undo” does not bring it '
          'back.'),
       'montage.projets.ouvert_perdu': (
          "« {nom} » ouvert. Le montage précédent a été remplacé : s'il n'était pas enregistré sous un nom, il "
          "n'existe plus, et « annuler » ne le rend pas.",
          '“{nom}” opened. The previous edit was replaced: if it was not saved under a name, it no longer exists, '
          'and “undo” does not bring it back.')}),
    S(92700, '"Réponse inattendue du serveur : rien n\'a été appliqué. "+\r\n            "Rechargez la page avant d\'enregistrer."',
      'dzT("montage.projets.reponse_inattendue"\r\n            )',
      {'montage.projets.reponse_inattendue': (
          "Réponse inattendue du serveur : rien n'a été appliqué. Rechargez la page avant d'enregistrer.",
          'Unexpected server response: nothing was applied. Reload the page before saving.')}),
    S(95463, '"Copie « "+d.name+" » créée. Le montage ouvert n\'a pas changé."',
      'dzT("montage.projets.copie_creee",{nom:d.name})',
      {'montage.projets.copie_creee': ("Copie « {nom} » créée. Le montage ouvert n'a pas changé.",
                                       'Copy “{nom}” created. The open edit has not changed.')}),
    S(95884, '"Nom inchangé : « "+d.name+" » — un champ vide garde l\'ancien nom."',
      'dzT("montage.projets.nom_inchange",{nom:d.name})',
      {'montage.projets.nom_inchange': ("Nom inchangé : « {nom} » — un champ vide garde l'ancien nom.",
                                        'Name unchanged: “{nom}” — an empty field keeps the old name.')}),
    S(95964, '"« "+p.name+" » renommé en « "+d.name+" »."',
      'dzT("montage.projets.renomme",{ancien:p.name,nom:d.name})',
      {'montage.projets.renomme': ('« {ancien} » renommé en « {nom} ».', '“{ancien}” renamed to “{nom}”.')}),
    S(98322, '"« "+p.name+" » supprimé — DÉFINITIVEMENT : le fichier est parti "+\r\n        "du disque, ni « annuler » ni rien d\'autre ne le rejoue."+\r\n        (p.id===pid?" La timeline affichée, elle, reste : elle n\'est simplement "+\r\n          "plus rattachée à aucun projet.":"")',
      'dzT("montage.projets.supprime",{nom:p.name,\r\n        \r\n        suite:p.id===pid?dzT("montage.projets.supprime_courant"\r\n          ):""})',
      {'montage.projets.supprime': (
          "« {nom} » supprimé — DÉFINITIVEMENT : le fichier est parti du disque, ni « annuler » ni rien d'autre ne le "
          "rejoue.{suite}",
          '“{nom}” deleted — PERMANENTLY: the file is gone from the disk, and neither “undo” nor anything else brings '
          'it back.{suite}'),
       'montage.projets.supprime_courant': (
          " La timeline affichée, elle, reste : elle n'est simplement plus rattachée à aucun projet.",
          ' The displayed timeline stays: it is simply no longer attached to any project.')}),

    # DzmProjects : carte d'un projet (nom, renommage, gestes)
    L(100236, 'montage.projets.nouveau_nom', 'Nouveau nom du projet', 'New project name'),
    L(100575, 'montage.mots.sans_nom', *_SANS_NOM),
    L(100593, 'montage.projets.ouvert', ' · ouvert', ' · open'),
    L(100682, 'montage.projets.montage_vide', 'montage vide', 'empty edit'),
    S(101033, '"Valider le nouveau nom (Entrée). Un champ vide garde "+\r\n                "l\'ancien nom."',
      'dzT("montage.projets.valider_nom"\r\n                )',
      {'montage.projets.valider_nom': ("Valider le nouveau nom (Entrée). Un champ vide garde l'ancien nom.",
                                       'Confirm the new name (Enter). An empty field keeps the old name.')}),
    S(101285, '"Renommer « "+(p.name||"")+" » — le montage lui-même "+\r\n                "n\'est pas touché"',
      'dzT("montage.projets.renommer_aide",{nom:p.name||""}\r\n                )',
      {'montage.projets.renommer_aide': ("Renommer « {nom} » — le montage lui-même n'est pas touché",
                                         'Rename “{nom}” — the edit itself is not touched')}),
    L(101480, 'montage.projets.renommer', 'renommer', 'rename'),
    S(101588, '"Dupliquer « "+(p.name||"")+" » — une copie indépendante, "+\r\n            "sous un nom suffixé « (copie) ». Rien d\'autre ne bouge."',
      'dzT("montage.projets.dupliquer_aide",{nom:p.name||""}\r\n            )',
      {'montage.projets.dupliquer_aide': (
          "Dupliquer « {nom} » — une copie indépendante, sous un nom suffixé « (copie) ». Rien d'autre ne bouge.",
          'Duplicate “{nom}” — an independent copy, under a name suffixed “(copie)”. Nothing else moves.')}),
    L(101770, 'montage.projets.dupliquer', 'dupliquer', 'duplicate'),
    S(102258, '"« "+(p.name||"")+" » est le montage ouvert — rien à comparer"',
      'dzT("montage.projets.comparer_courant",{nom:p.name||""})',
      {'montage.projets.comparer_courant': ('« {nom} » est le montage ouvert — rien à comparer',
                                            '“{nom}” is the open edit — nothing to compare')}),
    S(102335, '"Comparer « "+(p.name||"")+" » à la timeline courante (rien n\'est modifié)"',
      'dzT("montage.projets.comparer_aide",{nom:p.name||""})',
      {'montage.projets.comparer_aide': ("Comparer « {nom} » à la timeline courante (rien n'est modifié)",
                                         'Compare “{nom}” with the current timeline (nothing is changed)')}),
    S(102692, '"« "+(p.name||"")+" » est déjà le montage ouvert."',
      'dzT("montage.projets.deja_ouvert",{nom:p.name||""})',
      {'montage.projets.deja_ouvert': ('« {nom} » est déjà le montage ouvert.', '“{nom}” is already the open edit.')}),
    S(102779, '"Confirmer : OUVRIR « "+(p.name||"")+" » REMPLACE le montage "+\r\n               "affiché. S\'il n\'est pas enregistré sous un nom, il est perdu "+\r\n               "— « annuler » ne le rend pas."',
      'dzT("montage.projets.ouvrir_confirmer",{nom:p.name||""}\r\n               \r\n               )',
      {'montage.projets.ouvrir_confirmer': (
          "Confirmer : OUVRIR « {nom} » REMPLACE le montage affiché. S'il n'est pas enregistré sous un nom, il est "
          "perdu — « annuler » ne le rend pas.",
          'Confirm: OPENING “{nom}” REPLACES the displayed edit. If it is not saved under a name, it is lost — '
          '“undo” does not bring it back.')}),
    S(102988, '"Ouvrir « "+(p.name||"")+" » — cela REMPLACE le montage "+\r\n               "affiché (un second clic confirmera)"',
      'dzT("montage.projets.ouvrir_aide",{nom:p.name||""}\r\n               )',
      {'montage.projets.ouvrir_aide': ('Ouvrir « {nom} » — cela REMPLACE le montage affiché (un second clic confirmera)',
                                       'Open “{nom}” — this REPLACES the displayed edit (a second click will confirm)')}),
    L(103170, 'montage.projets.remplacer_arme', 'remplacer ?', 'replace?'),
    L(103184, 'montage.projets.ouvrir', 'ouvrir', 'open'),
    S(103357, '"Confirmer : supprimer « "+(p.name||"")+" » DÉFINITIVEMENT. "+\r\n             "Le fichier part du disque et rien ne le rejoue."',
      'dzT("montage.projets.supprimer_confirmer",{nom:p.name||""}\r\n             )',
      {'montage.projets.supprimer_confirmer': (
          'Confirmer : supprimer « {nom} » DÉFINITIVEMENT. Le fichier part du disque et rien ne le rejoue.',
          'Confirm: delete “{nom}” PERMANENTLY. The file leaves the disk and nothing brings it back.')}),
    S(103498, '"Supprimer « "+(p.name||"")+" » du disque, définitivement "+\r\n             "(un second clic confirmera)"',
      'dzT("montage.projets.supprimer_aide",{nom:p.name||""}\r\n             )',
      {'montage.projets.supprimer_aide': ('Supprimer « {nom} » du disque, définitivement (un second clic confirmera)',
                                          'Delete “{nom}” from the disk, permanently (a second click will confirm)')}),
    S(103628, '"Supprimer "+(p.name||"ce projet")',
      'dzT("montage.projets.supprimer_aria",{nom:p.name||dzT("montage.projets.ce_projet")})',
      {'montage.projets.supprimer_aria': ('Supprimer {nom}', 'Delete {nom}'),
       'montage.projets.ce_projet': ('ce projet', 'this project')}),
    L(103730, 'montage.projets.supprimer_arme', 'supprimer ?', 'delete?'),

    # DzmProjects : bouton « projets » (titre, aria-label, libellé)
    S(104052, '"Projets — ce montage est enregistré sous « "+nm+" » et suit vos "+\r\n          "modifications tout seul. La liste ouvre, duplique, renomme ou "+\r\n          "supprime les autres."',
      'dzT("montage.projets.bouton_nomme",{nom:nm}\r\n          \r\n          )',
      {'montage.projets.bouton_nomme': (
          'Projets — ce montage est enregistré sous « {nom} » et suit vos modifications tout seul. La liste ouvre, '
          'duplique, renomme ou supprime les autres.',
          'Projects — this edit is saved as “{nom}” and follows your changes on its own. The list opens, duplicates, '
          'renames or deletes the others.')}),
    S(104243, '"Projets — ce montage n\'a PAS de nom : il vit dans la timeline "+\r\n          "courante, et le prochain projet ouvert l\'écrasera sans retour. "+\r\n          "« Enregistrer sous… » lui en donne un."',
      'dzT("montage.projets.bouton_sans_nom"\r\n          \r\n          )',
      {'montage.projets.bouton_sans_nom': (
          "Projets — ce montage n'a PAS de nom : il vit dans la timeline courante, et le prochain projet ouvert "
          "l'écrasera sans retour. « Enregistrer sous… » lui en donne un.",
          'Projects — this edit has NO name: it lives in the current timeline, and the next project opened will '
          'overwrite it for good. “Save as…” gives it one.')}),
    S(104461, '"Projets"+(pid?" — enregistré sous "+nm\r\n                                 :" — ce montage n\'a pas de nom")',
      '(pid?dzT("montage.projets.aria_nomme",{nom:nm})\r\n                                 :dzT("montage.projets.aria_sans_nom"))',
      {'montage.projets.aria_nomme': ('Projets — enregistré sous {nom}', 'Projects — saved as {nom}'),
       'montage.projets.aria_sans_nom': ("Projets — ce montage n'a pas de nom", 'Projects — this edit has no name')}),
    L(104600, 'montage.projets.bouton', 'projets', 'projects'),

    # DzmProjects : popover (en-tête, enregistrer sous, nouveau, liste vide)
    L(104696, 'montage.projets.dialogue', 'Projets de montage', 'Edit projects'),
    L(104836, 'montage.projets.titre', 'Projets', 'Projects'),
    S(104929, 'rows.length+" enregistré"+(rows.length>1?"s":"")',
      '(rows.length>1?dzT("montage.projets.n_enregistres_plusieurs",{n:rows.length}):'
      'dzT("montage.projets.n_enregistres_un",{n:rows.length}))',
      {'montage.projets.n_enregistres_un': ('{n} enregistré', '{n} saved'),
       'montage.projets.n_enregistres_plusieurs': ('{n} enregistrés', '{n} saved')}),
    L(105137, 'montage.projets.nom_placeholder', 'nom du montage', 'edit name'),
    L(105167, 'montage.projets.nom', 'Nom du projet', 'Project name'),
    S(105428, '"Confirmer : créer un montage vide REMPLACE le montage affiché "+\r\n             "(enregistré d\'abord s\'il n\'a pas de nom)"',
      'dzT("montage.projets.nouveau_confirmer"\r\n             )',
      {'montage.projets.nouveau_confirmer': (
          "Confirmer : créer un montage vide REMPLACE le montage affiché (enregistré d'abord s'il n'a pas de nom)",
          'Confirm: creating an empty edit REPLACES the displayed edit (saved first if it has no name)')}),
    S(105565, '"Créer un montage vide et l\'ouvrir (le montage affiché est "+\r\n             "d\'abord enregistré s\'il n\'a pas de nom ; un second clic confirmera)"',
      'dzT("montage.projets.nouveau_aide"\r\n             )',
      {'montage.projets.nouveau_aide': (
          "Créer un montage vide et l'ouvrir (le montage affiché est d'abord enregistré s'il n'a pas de nom ; un "
          "second clic confirmera)",
          'Create an empty edit and open it (the displayed edit is saved first if it has no name; a second click '
          'will confirm)')}),
    L(105756, 'montage.projets.nouveau_arme', 'nouveau ?', 'new?'),
    L(105768, 'montage.projets.nouveau', 'nouveau', 'new'),
    S(105878, '"Enregistrer le montage AFFICHÉ comme un nouveau projet. "+\r\n            "Rien n\'est écrasé : c\'est un fichier de plus, et c\'est lui qui "+\r\n            "recevra les modifications suivantes. Champ vide : le nom "+\r\n            "courant est repris."',
      'dzT("montage.projets.enregistrer_sous_aide"\r\n            \r\n            \r\n            )',
      {'montage.projets.enregistrer_sous_aide': (
          "Enregistrer le montage AFFICHÉ comme un nouveau projet. Rien n'est écrasé : c'est un fichier de plus, et "
          "c'est lui qui recevra les modifications suivantes. Champ vide : le nom courant est repris.",
          'Save the DISPLAYED edit as a new project. Nothing is overwritten: it is one more file, and it is the one '
          'that will receive further changes. Empty field: the current name is reused.')}),
    L(106163, 'montage.projets.enregistrer_sous', 'enregistrer sous…', 'save as…'),
    S(106444, '"Aucun projet enregistré. « Enregistrer sous… » crée le "+\r\n            "premier ; jusque-là, le montage affiché est le seul, et ouvrir "+\r\n            "un projet l\'écraserait."',
      'dzT("montage.projets.aucun"\r\n            \r\n            )',
      {'montage.projets.aucun': (
          "Aucun projet enregistré. « Enregistrer sous… » crée le premier ; jusque-là, le montage affiché est le "
          "seul, et ouvrir un projet l'écraserait.",
          'No saved project. “Save as…” creates the first one; until then, the displayed edit is the only one, and '
          'opening a project would overwrite it.')}),
]
