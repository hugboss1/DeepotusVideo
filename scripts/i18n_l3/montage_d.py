"""t143 — montage_d : couche Montage (frontend/patches/montage.js), lignes 2725–3529 de la base. Couvre :
dzmOverlayNote (note d'un plan posé sur une piste d'incrustation), dzmAudioPourquoi (la raison de la sonde audio en
clair), dzmTwinPlan (toutes les phrases du jumeau « son du plan » concaténées à la note d'ajout), dzmExtract (les
notes du bouton « Extraire le son »), dzmExtractBtn (son infobulle, son aria-label, son libellé), puis le début de la
barre d'outils flottante : en-têtes de groupe, suffixe « — sélection » et libellés des boutons de DZM_TB_PLAN,
infobulles DZM_TB_T_* / DZM_TB_A_GRIP, phrase « sans hôte », écarts dits à l'utilisateur (DZM_TB_*_ECART) et
phrases d'annulation DZM_TB_H_*.

Gardés : le libellé « · son du plan » du jumeau (dzmTwinClip : il est ENREGISTRÉ dans le projet comme label du clip,
et les bancs le lisent tel quel) ; l'infobulle de dzmExtractBtn le recompose donc avec le libellé du plan (variable
{clip}) au lieu de le traduire. Les onze tracés SVG des icônes (DZM_TB_TRACES : chaînes « au caractère près » que le
banc compare à design.md). Le champ `type` des groupes de DZM_TB_PLAN (« ouvre un panneau », « outils de
placement ») n'est jamais affiché : il ne sert qu'à la comparaison avec le §2.4 de design.md. Les valeurs ARIA
« mixed » / « true » / « false » d'aria-pressed. Pas touchés (valeurs) : les ids de groupes et de boutons (g, i), les
codes de la sonde (« delai », « refus »…) comparés dans dzmAudioPourquoi, les motifs de dzmTwinPlan, la clé de
stockage dz_svm_tb_open. Libellés de boutons identiques dans les deux langues (« audio », « glow », « emoji ») :
laissés tels quels.

Phrases recomposées : chaque note coupée en morceaux concaténés devient UNE clé (S) avec ses variables ({piste},
{nom}, {raison}, {clip}, {duree}, {cible}) ; le code `apres` garde AUTANT de fins de ligne que le code `avant`. Les
notes du jumeau commencent par une espace (l'appelant les CONCATÈNE à la sienne) : l'espace est dans fr et en.
« hors ligne » (raison de la sonde) a contexte=True : le dictionnaire le traduit « down » pour l'état du serveur dans
la coque ; ici c'est l'absence de réseau (« offline »)."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_CE_PLAN = ('ce plan', 'this clip')
_TRACE = "tracé SVG d'icône, repris au caractère près de design.md (le banc compare la chaîne)"
_TYPE = "champ `type` du plan de la barre : jamais affiché, comparé au §2.4 de design.md"

ENTREES = [
    # dzmOverlayNote : plan vidéo posé sur une piste d'incrustation
    S(159915, '" Posé sur "+String(id).toUpperCase()+" (incrustation) : le son de "+\r\n    "ce plan n\'a PAS été extrait — sélectionnez-le puis « Extraire le son"+\r\n    (tr?" → "+tr.toUpperCase():"")+" » dans l\'inspecteur."',
      'dzT("montage.extraire.note_incrust",{piste:String(id).toUpperCase(),\r\n    \r\n    cible:tr?" → "+tr.toUpperCase():""})',
      {'montage.extraire.note_incrust': (
          " Posé sur {piste} (incrustation) : le son de ce plan n'a PAS été extrait — sélectionnez-le puis "
          "« Extraire le son{cible} » dans l'inspecteur.",
          " Placed on {piste} (overlay): this clip's sound was NOT extracted — select it, then "
          "“Extract sound{cible}” in the inspector.")}),

    # dzmAudioPourquoi : la raison de la sonde, en clair (les codes comparés restent des valeurs)
    L(165404, 'montage.audio.pourquoi_delai', 'délai dépassé', 'timed out'),
    L(165432, 'montage.audio.pourquoi_refus', 'le serveur a refusé', 'the server refused'),
    L(165473, 'montage.audio.pourquoi_erreur', 'erreur réseau', 'network error'),
    L(165507, 'montage.audio.pourquoi_hors_ligne', 'hors ligne', 'offline', contexte=True),
    L(165546, 'montage.audio.pourquoi_illisible', 'source illisible', 'unreadable source'),
    L(165569, 'montage.audio.pourquoi_sans_reponse', 'sans réponse', 'no response'),

    # dzmTwinClip : le libellé du jumeau est enregistré dans le projet
    X(171901, "libellé du clip jumeau, ENREGISTRÉ dans le projet (lu tel quel par les bancs)"),

    # dzmTwinPlan : la décision du jumeau et sa phrase (concaténée à la note d'ajout)
    L(172582, 'montage.mots.ce_plan', *_CE_PLAN),
    S(172755, '" Son du plan : la source n\'a pas été "+\r\n    "sondée — rien n\'a été extrait. « Extraire le son » dans l\'inspecteur "+\r\n    "réessaie."',
      'dzT("montage.jumeau.non_sonde"\r\n    \r\n    )',
      {'montage.jumeau.non_sonde': (
          " Son du plan : la source n'a pas été sondée — rien n'a été extrait. « Extraire le son » dans "
          "l'inspecteur réessaie.",
          " Clip sound: the source was not probed — nothing was extracted. “Extract sound” in the inspector "
          "retries.")}),
    S(173512, '" Son du plan : "+\r\n        "la source n\'a pas pu être sondée (aucune durée mesurable : fichier "+\r\n        "vide ou illisible) — rien n\'a été extrait. Vérifiez le fichier, ou "+\r\n        "remplacez la source."',
      'dzT("montage.jumeau.non_sondable"\r\n        \r\n        \r\n        )',
      {'montage.jumeau.non_sondable': (
          " Son du plan : la source n'a pas pu être sondée (aucune durée mesurable : fichier vide ou illisible) — "
          "rien n'a été extrait. Vérifiez le fichier, ou remplacez la source.",
          " Clip sound: the source could not be probed (no measurable duration: empty or unreadable file) — "
          "nothing was extracted. Check the file, or replace the source.")}),
    S(173755, '" Cette vidéo n\'a pas de piste audio : rien "+\r\n        "n\'a été extrait."',
      'dzT("montage.jumeau.muet"\r\n        )',
      {'montage.jumeau.muet': (" Cette vidéo n'a pas de piste audio : rien n'a été extrait.",
                               " This video has no audio track: nothing was extracted.")}),
    S(173865, '" Son du plan : la sonde n\'a pas abouti ("+\r\n      dzmAudioPourquoi(v.pourquoi)+") — rien n\'a été extrait, et le rendu "+\r\n      "n\'emporte JAMAIS l\'audio embarqué d\'un plan. « Extraire le son » dans "+\r\n      "l\'inspecteur réessaie."',
      'dzT("montage.jumeau.sonde_echec",{raison:\r\n      dzmAudioPourquoi(v.pourquoi)}\r\n      \r\n      )',
      {'montage.jumeau.sonde_echec': (
          " Son du plan : la sonde n'a pas abouti ({raison}) — rien n'a été extrait, et le rendu n'emporte JAMAIS "
          "l'audio embarqué d'un plan. « Extraire le son » dans l'inspecteur réessaie.",
          " Clip sound: the probe failed ({raison}) — nothing was extracted, and the render NEVER carries a "
          "clip's embedded audio. “Extract sound” in the inspector retries.")}),
    S(174141, '" Cette vidéo a du son, mais ce projet "+\r\n    "n\'a pas de piste de dialogue : le rendu la jouera MUETTE. Ajoutez une "+\r\n    "piste avec « + piste audio », puis « Extraire le son » dans "+\r\n    "l\'inspecteur."',
      'dzT("montage.jumeau.sans_piste"\r\n    \r\n    \r\n    )',
      {'montage.jumeau.sans_piste': (
          " Cette vidéo a du son, mais ce projet n'a pas de piste de dialogue : le rendu la jouera MUETTE. Ajoutez "
          "une piste avec « + piste audio », puis « Extraire le son » dans l'inspecteur.",
          " This video has sound, but this project has no dialogue track: the render will play it MUTED. Add a "
          "track with “+ audio track”, then “Extract sound” in the inspector.")}),
    S(174424, '" Piste "+\r\n    TR+" verrouillée : le son de « "+L+" » n\'a PAS été extrait — "+\r\n    "déverrouillez-la, puis « Extraire le son » dans l\'inspecteur."',
      'dzT("montage.jumeau.verrou",{piste:\r\n    TR,nom:L}\r\n    )',
      {'montage.jumeau.verrou': (
          " Piste {piste} verrouillée : le son de « {nom} » n'a PAS été extrait — déverrouillez-la, puis "
          "« Extraire le son » dans l'inspecteur.",
          " Track {piste} locked: the sound of “{nom}” was NOT extracted — unlock it, then “Extract sound” in "
          "the inspector.")}),
    S(174644, '" Son du plan : déjà présent sur "+TR+\r\n    " (même source, même plage) — pas de second exemplaire."',
      'dzT("montage.jumeau.doublon",{piste:TR}\r\n    )',
      {'montage.jumeau.doublon': (" Son du plan : déjà présent sur {piste} (même source, même plage) — pas de "
                                  "second exemplaire.",
                                  " Clip sound: already on {piste} (same source, same range) — no second copy.")}),
    S(174770, '" Son du plan extrait sur "+TR+" (« "+j.label+" », "+\r\n    "mêmes bornes, même source) : « Annuler » (Ctrl+Z) retire les DEUX clips "+\r\n    "d\'un coup."',
      'dzT("montage.jumeau.pose",{piste:TR,nom:j.label}\r\n    \r\n    )',
      {'montage.jumeau.pose': (
          " Son du plan extrait sur {piste} (« {nom} », mêmes bornes, même source) : « Annuler » (Ctrl+Z) retire "
          "les DEUX clips d'un coup.",
          " Clip sound extracted to {piste} (“{nom}”, same bounds, same source): “Undo” (Ctrl+Z) removes BOTH "
          "clips at once.")}),

    # dzmExtract : le bouton « Extraire le son » des plans déjà posés
    L(176367, 'montage.mots.ce_plan', *_CE_PLAN),
    L(176397, 'montage.extraire.aucun_plan', "Aucun plan à source n'est sélectionné : rien à extraire.",
      'No clip with a source is selected: nothing to extract.'),
    S(176498, '"« "+L+" » est une image : elle n\'a pas de son à "+\r\n    "extraire."',
      'dzT("montage.extraire.image",{nom:L}\r\n    )',
      {'montage.extraire.image': ("« {nom} » est une image : elle n'a pas de son à extraire.",
                                  '“{nom}” is an image: it has no sound to extract.')}),
    S(176668, '"Ce projet n\'a pas de piste de dialogue : le son de « "+L+\r\n    " » n\'a pas été extrait. Ajoutez une piste avec « + piste audio », puis "+\r\n    "recommencez."',
      'dzT("montage.extraire.sans_piste",{nom:L}\r\n    \r\n    )',
      {'montage.extraire.sans_piste': (
          "Ce projet n'a pas de piste de dialogue : le son de « {nom} » n'a pas été extrait. Ajoutez une piste avec "
          "« + piste audio », puis recommencez.",
          'This project has no dialogue track: the sound of “{nom}” was not extracted. Add a track with '
          '“+ audio track”, then try again.')}),
    S(176894, '"Piste "+TR+\r\n    " verrouillée — déverrouillez-la pour y extraire le son de « "+L+" »."',
      'dzT("montage.extraire.verrou",{piste:TR,\r\n    nom:L})',
      {'montage.extraire.verrou': ('Piste {piste} verrouillée — déverrouillez-la pour y extraire le son de « {nom} ».',
                                   'Track {piste} locked — unlock it to extract the sound of “{nom}” onto it.')}),
    S(177283, '"La sonde audio de « "+L+" » n\'a pas abouti ("+\r\n          dzmAudioPourquoi((v&&v.pourquoi)||pq)+") : rien n\'a été posé. "+\r\n          "Réessayez dans un instant."',
      'dzT("montage.extraire.sonde_echec",{nom:L,raison:\r\n          dzmAudioPourquoi((v&&v.pourquoi)||pq)}\r\n          )',
      {'montage.extraire.sonde_echec': (
          "La sonde audio de « {nom} » n'a pas abouti ({raison}) : rien n'a été posé. Réessayez dans un instant.",
          'The audio probe of “{nom}” failed ({raison}): nothing was placed. Try again in a moment.')}),
    S(177486, '"« "+L+" » n\'a pas pu être sondé (aucune durée mesurable : fichier "+\r\n          "vide ou illisible) : rien à extraire. Vérifiez le fichier, ou "+\r\n          "remplacez la source."',
      'dzT("montage.extraire.non_sondable",{nom:L}\r\n          \r\n          )',
      {'montage.extraire.non_sondable': (
          "« {nom} » n'a pas pu être sondé (aucune durée mesurable : fichier vide ou illisible) : rien à extraire. "
          "Vérifiez le fichier, ou remplacez la source.",
          '“{nom}” could not be probed (no measurable duration: empty or unreadable file): nothing to extract. '
          'Check the file, or replace the source.')}),
    S(177677, '"« "+L+" » n\'a pas de piste audio : rien à extraire."',
      'dzT("montage.extraire.muet",{nom:L})',
      {'montage.extraire.muet': ("« {nom} » n'a pas de piste audio : rien à extraire.",
                                 '“{nom}” has no audio track: nothing to extract.')}),
    S(177905, '"« "+L+" » n\'est plus dans la timeline : rien n\'a été "+\r\n      "posé."',
      'dzT("montage.extraire.plan_absent",{nom:L}\r\n      )',
      {'montage.extraire.plan_absent': ("« {nom} » n'est plus dans la timeline : rien n'a été posé.",
                                        '“{nom}” is no longer in the timeline: nothing was placed.')}),
    S(178111, '"Le son de « "+L+" » est déjà sur "+TR+" (même source, "+\r\n      "même plage) : rien n\'a été ajouté."',
      'dzT("montage.extraire.doublon",{nom:L,piste:TR}\r\n      )',
      {'montage.extraire.doublon': (
          "Le son de « {nom} » est déjà sur {piste} (même source, même plage) : rien n'a été ajouté.",
          'The sound of “{nom}” is already on {piste} (same source, same range): nothing was added.')}),
    S(178413, '"Son de « "+L+" » extrait sur "+TR+" : « "+j.label+" », "+\r\n      dzmSecs(j.end-j.start)+", mêmes bornes et même source que le plan. "+\r\n      "« Annuler » (Ctrl+Z) le retire."',
      'dzT("montage.extraire.pose",{nom:L,piste:TR,clip:j.label,duree:\r\n      dzmSecs(j.end-j.start)}\r\n      )',
      {'montage.extraire.pose': (
          "Son de « {nom} » extrait sur {piste} : « {clip} », {duree}, mêmes bornes et même source que le plan. "
          "« Annuler » (Ctrl+Z) le retire.",
          'Sound of “{nom}” extracted to {piste}: “{clip}”, {duree}, same bounds and same source as the clip. '
          '“Undo” (Ctrl+Z) removes it.')}),

    # dzmExtractBtn : infobulle, aria-label et libellé du bouton (le libellé « · son du plan » reste celui du clip)
    L(179130, 'montage.mots.ce_plan', *_CE_PLAN),
    S(179226, '"Poser sur "+TR+" (piste de dialogue) un clip « "+L+" · son du plan » : "+\r\n       "même source, mêmes bornes, même point d\'entrée. Le rendu n\'emporte "+\r\n       "JAMAIS l\'audio embarqué d\'un plan vidéo — sans ce clip, ce plan "+\r\n       "sort muet. Refusé si la source n\'a pas de piste audio ou si ce son "+\r\n       "est déjà sur "+TR+" à cette plage. « Annuler » (Ctrl+Z) le retire."',
      'dzT("montage.extraire.bouton_aide",{piste:TR,clip:L+" · son du plan"}\r\n       \r\n       \r\n       \r\n       )',
      {'montage.extraire.bouton_aide': (
          "Poser sur {piste} (piste de dialogue) un clip « {clip} » : même source, mêmes bornes, même point "
          "d'entrée. Le rendu n'emporte JAMAIS l'audio embarqué d'un plan vidéo — sans ce clip, ce plan sort muet. "
          "Refusé si la source n'a pas de piste audio ou si ce son est déjà sur {piste} à cette plage. « Annuler » "
          "(Ctrl+Z) le retire.",
          'Places a clip “{clip}” on {piste} (dialogue track): same source, same bounds, same in point. The render '
          'NEVER carries a video clip\'s embedded audio — without this clip, the clip plays muted. Refused if the '
          'source has no audio track or if this sound is already on {piste} at this range. “Undo” (Ctrl+Z) '
          'removes it.')}),
    S(179620, '"Ce projet n\'a pas de piste de dialogue : ajoutez une piste avec "+\r\n       "« + piste audio » pour pouvoir extraire le son de ce plan."',
      'dzT("montage.extraire.bouton_sans_piste"\r\n       )',
      {'montage.extraire.bouton_sans_piste': (
          "Ce projet n'a pas de piste de dialogue : ajoutez une piste avec « + piste audio » pour pouvoir extraire "
          "le son de ce plan.",
          'This project has no dialogue track: add a track with “+ audio track” to be able to extract this '
          'clip\'s sound.')}),
    S(179777, '"Extraire le son de "+L+(tr?" vers "+TR:"")',
      '(tr?dzT("montage.extraire.aria_vers",{nom:L,piste:TR}):dzT("montage.extraire.aria",{nom:L}))',
      {'montage.extraire.aria_vers': ('Extraire le son de {nom} vers {piste}', 'Extract the sound of {nom} to {piste}'),
       'montage.extraire.aria': ('Extraire le son de {nom}', 'Extract the sound of {nom}')}),
    S(179883, '"Extraire le son → "+TR',
      'dzT("montage.extraire.bouton",{piste:TR})',
      {'montage.extraire.bouton': ('Extraire le son → {piste}', 'Extract sound → {piste}')}),
    L(179907, 'montage.extraire.bouton_sans_dialogue', 'Extraire le son (aucune piste de dialogue)',
      'Extract sound (no dialogue track)'),

    # DZM_TB_TRACES : les tracés des icônes de la barre
    X(182195, _TRACE),
    X(182399, _TRACE),
    X(182718, _TRACE),
    X(182898, _TRACE),
    X(183206, _TRACE),
    X(183449, _TRACE),
    X(183773, _TRACE),
    X(183995, _TRACE),
    X(184181, _TRACE),
    X(184310, _TRACE),
    X(184990, _TRACE),

    # DzmToolBtn : valeurs ARIA d'aria-pressed
    X(190126, "valeur ARIA d'aria-pressed (état indéterminé)"),
    X(190138, "valeur ARIA d'aria-pressed"),

    # DZM_TB_PLAN : en-têtes de groupe (affichés et aria-label du groupe), suffixe, libellés des boutons
    L(197552, 'montage.barre.groupe_pistes', 'PISTES', 'TRACKS'),
    L(197605, 'montage.barre.btn_video', 'vidéo', 'video'),
    L(197635, 'montage.barre.btn_incrust', 'incrust.', 'overlay'),
    L(197706, 'montage.barre.groupe_biblio', 'BIBLIOTHÈQUE', 'LIBRARY'),
    X(197726, _TYPE),
    L(197776, 'montage.barre.btn_lier', 'lier', 'link'),
    L(197801, 'montage.barre.groupe_mot', 'MOT', 'WORD'),
    L(197811, 'montage.barre.suffixe_selection', '— sélection', '— selection'),
    L(197855, 'montage.barre.btn_couleur', 'couleur', 'color'),
    L(197881, 'montage.barre.btn_rebond', 'rebond', 'bounce'),
    L(197942, 'montage.barre.groupe_ajouts', 'AJOUTS', 'ADD'),
    X(197956, _TYPE),
    L(198014, 'montage.barre.btn_texte', 'texte', 'text'),
    L(198054, 'montage.barre.groupe_projets', 'PROJETS', 'PROJECTS'),
    X(198069, _TYPE),
    L(198102, 'montage.barre.btn_projets', 'projets', 'projects'),

    # titres de la barre : bouton sans hôte, poignée, recentrer, replier, Texte
    S(198548, '"Action non fournie à la barre par l\'écran qui la "+\r\n  "monte — il n\'y a rien à déclencher."',
      'dzT("montage.barre.sans_hote"\r\n  )',
      {'montage.barre.sans_hote': (
          "Action non fournie à la barre par l'écran qui la monte — il n'y a rien à déclencher.",
          'Action not provided to the toolbar by the screen that mounts it — there is nothing to trigger.')}),
    S(198802, '"Poignée — glisser pour déplacer la barre d\'outils ; "+\r\n  "flèches pour la déplacer de 8 px, Maj + flèches de 1 px. Elle reste "+\r\n  "entièrement dans la timeline et la prévisualisation, à 8 px des bords, "+\r\n  "et s\'aimante aux bords et à la tête de lecture au relâchement."',
      'dzT("montage.barre.poignee_aide"\r\n  \r\n  \r\n  )',
      {'montage.barre.poignee_aide': (
          "Poignée — glisser pour déplacer la barre d'outils ; flèches pour la déplacer de 8 px, Maj + flèches de "
          "1 px. Elle reste entièrement dans la timeline et la prévisualisation, à 8 px des bords, et s'aimante "
          "aux bords et à la tête de lecture au relâchement.",
          'Handle — drag to move the toolbar; arrow keys move it by 8 px, Shift + arrows by 1 px. It stays '
          'entirely within the timeline and the preview, 8 px from the edges, and snaps to the edges and to the '
          'playhead on release.')}),
    L(199099, 'montage.barre.poignee', "Déplacer la barre d'outils", 'Move the toolbar'),
    S(199493, '"Recentrer la barre d\'outils — la ramène sous le "+\r\n  "bandeau de transport, à sa place d\'origine."',
      'dzT("montage.barre.recentrer"\r\n  )',
      {'montage.barre.recentrer': (
          "Recentrer la barre d'outils — la ramène sous le bandeau de transport, à sa place d'origine.",
          'Recenter the toolbar — brings it back under the transport bar, to its original place.')}),
    S(199619, '"Recentrer la barre d\'outils — elle est déjà à sa "+\r\n  "place d\'origine."',
      'dzT("montage.barre.recentree"\r\n  )',
      {'montage.barre.recentree': ("Recentrer la barre d'outils — elle est déjà à sa place d'origine.",
                                   'Recenter the toolbar — it is already in its original place.')}),
    L(199717, 'montage.barre.replier', "Replier la barre d'outils sur son onglet.", 'Collapse the toolbar onto its tab.'),
    S(199782, '"Ouvrir ou fermer le panneau « Texte » — la narration "+\r\n  "mot par mot dans la colonne de droite."',
      'dzT("montage.barre.texte_aide"\r\n  )',
      {'montage.barre.texte_aide': (
          "Ouvrir ou fermer le panneau « Texte » — la narration mot par mot dans la colonne de droite.",
          'Open or close the “Text” panel — the word-by-word narration in the right column.')}),

    # écarts dits à l'utilisateur (MOT, emoji, texte), emoji, projets
    S(200601, '" — Cette base porte UNE animation à la fois pour "+\r\n  "toute la piste de sous-titres, pas trois effets cumulables sur une "+\r\n  "sélection de mots : choisir celle-ci remplace la précédente."',
      'dzT("montage.barre.ecart_mot"\r\n  \r\n  )',
      {'montage.barre.ecart_mot': (
          " — Cette base porte UNE animation à la fois pour toute la piste de sous-titres, pas trois effets "
          "cumulables sur une sélection de mots : choisir celle-ci remplace la précédente.",
          ' — This base carries ONE animation at a time for the whole subtitle track, not three stackable '
          'effects on a word selection: choosing this one replaces the previous one.')}),
    S(201638, '" Cette base n\'a pas de sélecteur d\'emoji : elle pose "+\r\n  "d\'elle-même un clip par mot reconnu, là où ce mot est dit, et non un "+\r\n  "emoji choisi à la tête de lecture."',
      'dzT("montage.barre.ecart_emoji"\r\n  \r\n  )',
      {'montage.barre.ecart_emoji': (
          " Cette base n'a pas de sélecteur d'emoji : elle pose d'elle-même un clip par mot reconnu, là où ce mot "
          "est dit, et non un emoji choisi à la tête de lecture.",
          ' This base has no emoji picker: it places a clip by itself for each recognized word, where that word '
          'is spoken, rather than an emoji chosen at the playhead.')}),
    S(201834, '" Ce bouton ouvre un panneau, il ne pose pas de clip : "+\r\n  "pour écrire un sous-titre à la tête de lecture, le « + » de l\'en-tête de "+\r\n  "la piste S1."',
      'dzT("montage.barre.ecart_texte"\r\n  \r\n  )',
      {'montage.barre.ecart_texte': (
          " Ce bouton ouvre un panneau, il ne pose pas de clip : pour écrire un sous-titre à la tête de lecture, "
          "le « + » de l'en-tête de la piste S1.",
          ' This button opens a panel, it does not place a clip: to write a subtitle at the playhead, use the '
          '“+” in the S1 track header.')}),
    S(202011, '"Poser les emoji des mots-clés des sous-titres (feu, "+\r\n  "lune, vague, poulpe, or, fusée) — un clip de 0,8 s par mot reconnu, sur "+\r\n  "la piste vidéo d\'overlay la plus haute."',
      'dzT("montage.barre.emoji_aide"\r\n  \r\n  )',
      {'montage.barre.emoji_aide': (
          "Poser les emoji des mots-clés des sous-titres (feu, lune, vague, poulpe, or, fusée) — un clip de 0,8 s "
          "par mot reconnu, sur la piste vidéo d'overlay la plus haute.",
          'Place the emoji of the subtitle keywords (fire, moon, wave, octopus, gold, rocket) — a 0.8 s clip per '
          'recognized word, on the highest overlay video track.')}),
    S(202216, '"Emoji — la demande précédente est encore en cours ; "+\r\n  "le bouton se rallume à la réponse du serveur."',
      'dzT("montage.barre.emoji_occupe"\r\n  )',
      {'montage.barre.emoji_occupe': (
          "Emoji — la demande précédente est encore en cours ; le bouton se rallume à la réponse du serveur.",
          'Emoji — the previous request is still running; the button comes back on when the server responds.')}),
    S(202346, '"Ouvrir la liste des projets de montage — enregistrer "+\r\n  "sous un nom, ouvrir, dupliquer, renommer, supprimer."',
      'dzT("montage.barre.projets_aide"\r\n  )',
      {'montage.barre.projets_aide': (
          "Ouvrir la liste des projets de montage — enregistrer sous un nom, ouvrir, dupliquer, renommer, "
          "supprimer.",
          'Open the list of editing projects — save under a name, open, duplicate, rename, delete.')}),

    # DZM_TB_H_* : ce que « Annuler » rend, bouton par bouton
    S(203719, '" « Annuler » (Ctrl+Z) retire d\'un coup ce qui vient "+\r\n  "d\'être posé : l\'historique de cet écran mémorise tout l\'état du montage."',
      'dzT("montage.barre.annuler_clips"\r\n  )',
      {'montage.barre.annuler_clips': (
          " « Annuler » (Ctrl+Z) retire d'un coup ce qui vient d'être posé : l'historique de cet écran mémorise "
          "tout l'état du montage.",
          ' “Undo” (Ctrl+Z) removes what was just placed in one go: this screen\'s history records the whole '
          'editing state.')}),
    S(203874, '" « Annuler » (Ctrl+Z) retire la piste : l\'historique de "+\r\n  "cet écran mémorise les pistes depuis le 21/09/2026. Le « × » de l\'en-tête "+\r\n  "de la piste la retire aussi."',
      'dzT("montage.barre.annuler_piste"\r\n  \r\n  )',
      {'montage.barre.annuler_piste': (
          " « Annuler » (Ctrl+Z) retire la piste : l'historique de cet écran mémorise les pistes depuis le "
          "21/09/2026. Le « × » de l'en-tête de la piste la retire aussi.",
          ' “Undo” (Ctrl+Z) removes the track: this screen\'s history has recorded tracks since 2026-09-21. The '
          '“×” in the track header removes it too.')}),
    S(204070, '" « Annuler » (Ctrl+Z) revient dessus : ce réglage entre "+\r\n  "dans l\'historique (une entrée par rafale de 600 ms)."',
      'dzT("montage.barre.annuler_style"\r\n  )',
      {'montage.barre.annuler_style': (
          " « Annuler » (Ctrl+Z) revient dessus : ce réglage entre dans l'historique (une entrée par rafale de "
          "600 ms).",
          ' “Undo” (Ctrl+Z) reverts it: this setting goes into the history (one entry per 600 ms burst).')}),
    S(204211, '" Ouvrir ou fermer ce panneau n\'entre pas dans "+\r\n  "l\'historique et ne déplace pas la tête de lecture."',
      'dzT("montage.barre.annuler_panneau"\r\n  )',
      {'montage.barre.annuler_panneau': (
          " Ouvrir ou fermer ce panneau n'entre pas dans l'historique et ne déplace pas la tête de lecture.",
          ' Opening or closing this panel does not go into the history and does not move the playhead.')}),
    S(204339, '" Ouvrir la liste n\'entre pas dans l\'historique et ne "+\r\n  "déplace pas la tête de lecture. Ouvrir un PROJET, en revanche, remplace "+\r\n  "le montage affiché, VIDE l\'historique et ramène la tête à zéro : la liste "+\r\n  "demande confirmation avant."',
      'dzT("montage.barre.annuler_projet"\r\n  \r\n  \r\n  )',
      {'montage.barre.annuler_projet': (
          " Ouvrir la liste n'entre pas dans l'historique et ne déplace pas la tête de lecture. Ouvrir un PROJET, "
          "en revanche, remplace le montage affiché, VIDE l'historique et ramène la tête à zéro : la liste demande "
          "confirmation avant.",
          ' Opening the list does not go into the history and does not move the playhead. Opening a PROJECT, '
          'however, replaces the displayed edit, CLEARS the history and brings the playhead back to zero: the '
          'list asks for confirmation first.')}),
]
