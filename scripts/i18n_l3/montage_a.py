"""t143 — montage_a : couche Montage (frontend/patches/montage.js), lignes 1–1035 de la base. Couvre : la note de
dzmAddDit (la phrase qui dit la piste ajoutée : audio, vidéo plein cadre, incrustation), les trois animations de
sous-titres mot par mot (DZM_WORD_ANIMS : libellés et aides), DzmTrackAdd (« + piste vidéo » / « + piste audio »),
DzmLibBtn (« Bibliothèque… »), la chip « pas une vidéo » (dzmBadSrcChip), DzmTrackBtns (▲ ▼ × d'un en-tête de
piste : notes de déplacement refusé, de piste de base, de retrait ; titres et aria), la chip « mot » (DzmWordAnimChip)
et l'action emoji (dzmEmojiGo, DZM_EMO_TITRE, DzmEmojiBtn).

Gardés : « use strict » (directive), le type de piste « vidéo » partout où il est une VALEUR (table des pistes par
défaut, habillage dzmSkin, payload envoyé au serveur par svmTracksPayload, comparaisons `type==="vidéo"` de dzmAdd et
dzmAddDit), les combinaisons de repli « Maj+T » / « Maj+J » de dzmCombo (même format que le libellé de la keymap
vivante svmKeyLabelNow, qui les remplace dès qu'elle répond). Pas touchés non plus (hors contrôle, ce sont des
valeurs) : les genres « audio » / « subs » / « title » / « adjust » de dzmKindOf et dzmPickTrack, les valeurs `v` des
animations (« couleur », « rebond », « glow » : enregistrées dans le style), le bus montré tel quel (« sfx »,
« dialogue », « musique » : identifiants du mixage), « glow » et « emoji » (identiques dans les deux langues).
Les libellés et aides de DZM_WORD_ANIMS et DZM_EMO_TITRE sont des constantes de module : dzT y est appelé au chargement,
comme DZ_ANIM_TYPES de L2 (un changement de langue recharge la page).
Les phrases coupées en morceaux concaténés sur plusieurs lignes sont recomposées en une seule clé (S) dont le code
`apres` garde AUTANT de fins de ligne que le code `avant` ; les pluriels « clip(s) » / « emoji posé(s) » passent par
deux clés .un / .plusieurs."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_VIDEO_VALEUR = "type de piste « vidéo » : valeur stockée (table des pistes, habillage) et comparée (===)"
_RETIRER_ARIA = ('Retirer la piste {piste}', 'Remove track {piste}')

ENTREES = [
    # directive
    X(10426, 'directive JavaScript « use strict »'),

    # DZM_DEFAULT_TRACKS, dzmSkin, svmTracksPayload, dzmAdd : le type « vidéo » est une valeur
    X(11733, _VIDEO_VALEUR),
    X(14466, _VIDEO_VALEUR),
    X(14523, _VIDEO_VALEUR),
    X(17970, _VIDEO_VALEUR),
    X(17985, "type de piste « vidéo » envoyé au backend (payload tracks, autosave)"),
    X(22124, _VIDEO_VALEUR),
    X(22540, _VIDEO_VALEUR),
    X(22558, _VIDEO_VALEUR),

    # dzmAddDit : la note qui dit la piste ajoutée
    S(23804, '"Piste "+nom+" ajoutée — audio, bus "+\r\n    String(neuf.bus||"sfx")+(neuf.loop?", bouclée":"")+" : une bande vide, "+\r\n    "sous les pistes audio existantes."',
      'dzT("montage.pistes.ajoutee_audio",{piste:nom,\r\n    bus:String(neuf.bus||"sfx"),boucle:neuf.loop?dzT("montage.pistes.bouclee"):""}\r\n    )',
      {'montage.pistes.ajoutee_audio': (
          'Piste {piste} ajoutée — audio, bus {bus}{boucle} : une bande vide, sous les pistes audio existantes.',
          'Track {piste} added — audio, bus {bus}{boucle}: an empty strip, below the existing audio tracks.'),
       'montage.pistes.bouclee': (', bouclée', ', looped')}),
    X(23980, _VIDEO_VALEUR),
    S(23993, '"Piste "+nom+" ajoutée — vidéo plein cadre : "+\r\n    "ses plans recouvrent V1 pendant leur durée et leur son est extrait sur "+\r\n    "la piste de dialogue ; ses plans ont leurs transitions, leur vitesse et "+\r\n    "leurs effets, comme V1 ; V1 reste la séquence maîtresse (durée)."',
      'dzT("montage.pistes.ajoutee_video",{piste:nom}\r\n    \r\n    \r\n    )',
      {'montage.pistes.ajoutee_video': (
          'Piste {piste} ajoutée — vidéo plein cadre : ses plans recouvrent V1 pendant leur durée et leur son est '
          'extrait sur la piste de dialogue ; ses plans ont leurs transitions, leur vitesse et leurs effets, comme '
          'V1 ; V1 reste la séquence maîtresse (durée).',
          'Track {piste} added — full-frame video: its clips cover V1 for their duration and their sound is '
          'extracted onto the dialogue track; its clips have their own transitions, speed and effects, like V1; '
          'V1 remains the master sequence (duration).')}),
    S(24288, '"Piste "+nom+" ajoutée — incrustation"+\r\n    (ty==="overlay/VFX"?" (overlay/VFX, la piste historique)":"")+\r\n    " : image dans l\'image, réglable (position, échelle, rotation, "+\r\n    "opacité), muette ; ses plans ont aussi transitions, vitesse et effets."',
      'dzT("montage.pistes.ajoutee_incrustation",{piste:nom,\r\n    historique:ty==="overlay/VFX"?dzT("montage.pistes.historique"):""}\r\n    \r\n    )',
      {'montage.pistes.ajoutee_incrustation': (
          "Piste {piste} ajoutée — incrustation{historique} : image dans l'image, réglable (position, échelle, "
          "rotation, opacité), muette ; ses plans ont aussi transitions, vitesse et effets.",
          'Track {piste} added — overlay{historique}: picture-in-picture, adjustable (position, scale, rotation, '
          'opacity), muted; its clips also have transitions, speed and effects.'),
       'montage.pistes.historique': (' (overlay/VFX, la piste historique)', ' (overlay/VFX, the original track)')}),

    # DZM_WORD_ANIMS : animations des sous-titres mot par mot (libellé de chip + aide)
    L(30112, 'montage.motanim.couleur', 'couleur', 'color'),
    S(30124, '"Le mot actif change de couleur (karaoké). "+\r\n   "Rien n\'est déplacé : les répliques sur plusieurs lignes en profitent aussi."',
      'dzT("montage.motanim.couleur_aide"\r\n   )',
      {'montage.motanim.couleur_aide': (
          "Le mot actif change de couleur (karaoké). Rien n'est déplacé : les répliques sur plusieurs lignes en "
          "profitent aussi.",
          'The active word changes color (karaoke). Nothing moves: lines spanning several rows benefit too.')}),
    L(30270, 'montage.motanim.rebond', 'rebond', 'bounce'),
    S(30281, '"Chaque mot entre en grossissant, puis se pose. "+\r\n   "Mesuré à l\'image : 222 pixels éclairés à 130 ms contre 191 une fois posé "+\r\n   "(×1,16). Réservé aux répliques qui tiennent sur UNE ligne — les autres "+\r\n   "gardent la couleur."',
      'dzT("montage.motanim.rebond_aide"\r\n   \r\n   \r\n   )',
      {'montage.motanim.rebond_aide': (
          "Chaque mot entre en grossissant, puis se pose. Mesuré à l'image : 222 pixels éclairés à 130 ms contre 191 "
          "une fois posé (×1,16). Réservé aux répliques qui tiennent sur UNE ligne — les autres gardent la couleur.",
          'Each word grows in, then settles. Measured on the image: 222 lit pixels at 130 ms versus 191 once settled '
          '(×1.16). Only for lines that fit on ONE row — the others keep the color.')}),
    S(30543, '"Chaque mot pousse son contour puis le laisse "+\r\n   "retomber. Mêmes limites que le rebond : une seule ligne."',
      'dzT("montage.motanim.glow_aide"\r\n   )',
      {'montage.motanim.glow_aide': (
          'Chaque mot pousse son contour puis le laisse retomber. Mêmes limites que le rebond : une seule ligne.',
          'Each word pushes its outline out then lets it fall back. Same limits as bounce: a single row.')}),

    # DzmTrackAdd : « + piste vidéo » / « + piste audio »
    S(42999, '"Ajouter une PISTE vidéo plein cadre (une bande vide) — posée "+\r\n        "tout en haut ; ses plans recouvrent V1 pendant leur durée. Pour "+\r\n        "poser un clip, c\'est « Bibliothèque… »."',
      'dzT("montage.pistes.ajouter_video_aide"\r\n        \r\n        )',
      {'montage.pistes.ajouter_video_aide': (
          "Ajouter une PISTE vidéo plein cadre (une bande vide) — posée tout en haut ; ses plans recouvrent V1 "
          "pendant leur durée. Pour poser un clip, c'est « Bibliothèque… ».",
          'Add a full-frame video TRACK (an empty strip) — placed at the very top; its clips cover V1 for their '
          'duration. To place a clip, use “Library…”.')}),
    L(43213, 'montage.pistes.ajouter_video_aria', 'Ajouter une piste vidéo plein cadre', 'Add a full-frame video track'),
    L(43301, 'montage.pistes.ajouter_video', '+ piste vidéo', '+ video track'),
    S(43389, '"Ajouter une PISTE audio (une bande vide) — posée sous les pistes "+\r\n        "audio existantes, au-dessus des sous-titres. Bus BRUITAGES, sauf si "+\r\n        "l\'identifiant libre est celui d\'une piste historique retirée (A1, "+\r\n        "A2) : elle revient alors avec son bus d\'origine et son habillage."',
      'dzT("montage.pistes.ajouter_audio_aide"\r\n        \r\n        \r\n        )',
      {'montage.pistes.ajouter_audio_aide': (
          "Ajouter une PISTE audio (une bande vide) — posée sous les pistes audio existantes, au-dessus des "
          "sous-titres. Bus BRUITAGES, sauf si l'identifiant libre est celui d'une piste historique retirée (A1, "
          "A2) : elle revient alors avec son bus d'origine et son habillage.",
          'Add an audio TRACK (an empty strip) — placed below the existing audio tracks, above the subtitles. SFX '
          'bus, unless the free identifier is that of a removed original track (A1, A2): it then comes back with '
          'its original bus and look.')}),
    L(43716, 'montage.pistes.ajouter_audio_aria', 'Ajouter une piste audio', 'Add an audio track'),
    L(43792, 'montage.pistes.ajouter_audio', '+ piste audio', '+ audio track'),

    # DzmLibBtn : « Bibliothèque… » de la barre de transport
    S(44788, '"Ouvrir la Bibliothèque et poser une vidéo, une image ou un "+\r\n        "rendu sur la piste "+id.toUpperCase()+", à la tête de lecture — "+\r\n        "c\'est la piste vidéo la plus haute du projet."',
      'dzT("montage.pistes.biblio_aide",{piste:\r\n        id.toUpperCase()}\r\n        )',
      {'montage.pistes.biblio_aide': (
          "Ouvrir la Bibliothèque et poser une vidéo, une image ou un rendu sur la piste {piste}, à la tête de "
          "lecture — c'est la piste vidéo la plus haute du projet.",
          'Open the Library and place a video, an image or a render on track {piste}, at the playhead — it is the '
          "project's topmost video track.")}),
    S(44995, '"Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le "+\r\n        "clip. « + piste vidéo » en crée une."',
      'dzT("montage.pistes.biblio_sans_video"\r\n        )',
      {'montage.pistes.biblio_sans_video': (
          'Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le clip. « + piste vidéo » en crée une.',
          'No video track in this project: nothing could receive the clip. “+ video track” creates one.')}),
    L(45132, 'montage.pistes.biblio_aria', 'Ouvrir la Bibliothèque pour ajouter un clip',
      'Open the Library to add a clip'),
    S(45251, '"Aucune piste vidéo dans ce "+\r\n        "projet — « + piste vidéo » en crée une, puis « Bibliothèque… » y "+\r\n        "posera le clip."',
      'dzT("montage.pistes.biblio_sans_video_note"\r\n        \r\n        )',
      {'montage.pistes.biblio_sans_video_note': (
          'Aucune piste vidéo dans ce projet — « + piste vidéo » en crée une, puis « Bibliothèque… » y posera le '
          'clip.',
          'No video track in this project — “+ video track” creates one, then “Library…” will place the clip '
          'there.')}),
    L(45459, 'montage.pistes.bibliotheque', 'Bibliothèque…', 'Library…'),

    # dzmBadSrcChip : clip V1 qui n'est pas une vidéo
    S(47083, '"Ce plan n\'est pas une vidéo : son fichier ne porte pas "+\r\n      "d\'extension vidéo (planche de sprites, maillage 3D, archive…). Un "+\r\n      "maillage ou une archive fera échouer le rendu, qui les nommera ; une "+\r\n      "image passera le contrôle mais se rendra en carton fixe. Cliquez "+\r\n      "pour rouvrir la Bibliothèque et poser un vrai rendu à sa place, puis "+\r\n      "retirez celui-ci."',
      'dzT("montage.pistes.pas_video_aide"\r\n      \r\n      \r\n      \r\n      \r\n      )',
      {'montage.pistes.pas_video_aide': (
          "Ce plan n'est pas une vidéo : son fichier ne porte pas d'extension vidéo (planche de sprites, maillage "
          "3D, archive…). Un maillage ou une archive fera échouer le rendu, qui les nommera ; une image passera le "
          "contrôle mais se rendra en carton fixe. Cliquez pour rouvrir la Bibliothèque et poser un vrai rendu à sa "
          "place, puis retirez celui-ci.",
          'This clip is not a video: its file has no video extension (sprite sheet, 3D mesh, archive…). A mesh or '
          'an archive will make the render fail, which will name them; an image will pass the check but render as '
          'a still card. Click to reopen the Library and place a real render in its place, then remove this one.')}),
    L(47501, 'montage.pistes.pas_video_aria', "Plan qui n'est pas une vidéo — ouvrir la Bibliothèque",
      'Clip that is not a video — open the Library'),
    L(47754, 'montage.pistes.pas_video', 'pas une vidéo', 'not a video'),

    # DzmTrackBtns : déplacement refusé (▲ ▼)
    S(48685, '"« "+(tr.name||tr.id)+" » ne peut pas aller plus "+\r\n      (d<0?"haut":"bas")+" — les overlays restent au-dessus de V1, l\'audio "+\r\n      "au milieu, les sous-titres en bas."',
      '(d<0?dzT("montage.pistes.bloquee_haut",{nom:tr.name||tr.id}):\r\n      dzT("montage.pistes.bloquee_bas",{nom:tr.name||tr.id})\r\n      )',
      {'montage.pistes.bloquee_haut': (
          "« {nom} » ne peut pas aller plus haut — les overlays restent au-dessus de V1, l'audio au milieu, les "
          "sous-titres en bas.",
          '“{nom}” cannot go any higher — overlays stay above V1, audio in the middle, subtitles at the bottom.'),
       'montage.pistes.bloquee_bas': (
          "« {nom} » ne peut pas aller plus bas — les overlays restent au-dessus de V1, l'audio au milieu, les "
          "sous-titres en bas.",
          '“{nom}” cannot go any lower — overlays stay above V1, audio in the middle, subtitles at the bottom.')}),
    # DzmTrackBtns : pistes de base (× refusé)
    S(48942, '"S1 est la seule piste de sous-titres et rien ne sait la recréer : "+\r\n       "elle ne peut pas être retirée."',
      'dzT("montage.pistes.s1_base_note"\r\n       )',
      {'montage.pistes.s1_base_note': (
          'S1 est la seule piste de sous-titres et rien ne sait la recréer : elle ne peut pas être retirée.',
          'S1 is the only subtitle track and nothing can recreate it: it cannot be removed.')}),
    S(49061, '"V1 est la piste de base du montage : elle ne peut pas être "+\r\n       "retirée."',
      'dzT("montage.pistes.v1_base_note"\r\n       )',
      {'montage.pistes.v1_base_note': (
          'V1 est la piste de base du montage : elle ne peut pas être retirée.',
          'V1 is the base track of the edit: it cannot be removed.')}),
    # DzmTrackBtns : note de retrait
    S(50400, '"Piste "+(tr.name||tr.id)+" retirée"+\r\n      (n?" avec "+n+" clip"+(n>1?"s":""):"")+',
      '(!n?dzT("montage.pistes.retiree",{piste:tr.name||tr.id}):\r\n      n>1?dzT("montage.pistes.retiree_clips.plusieurs",{piste:tr.name||tr.id,n:n}):dzT("montage.pistes.retiree_clips.un",{piste:tr.name||tr.id,n:n}))+',
      {'montage.pistes.retiree': ('Piste {piste} retirée', 'Track {piste} removed'),
       'montage.pistes.retiree_clips.un': ('Piste {piste} retirée avec {n} clip', 'Track {piste} removed with {n} clip'),
       'montage.pistes.retiree_clips.plusieurs': ('Piste {piste} retirée avec {n} clips',
                                                  'Track {piste} removed with {n} clips')}),
    L(50495, 'montage.pistes.retiree_suite', ' — annuler ramène les clips ; la piste, elle, ',
      ' — undo brings the clips back; the track itself '),
    S(50581, '"revient avec "+dzmCombo("title_add","Maj+T")+\r\n           ", qui repose un carton (même identifiant)."',
      'dzT("montage.pistes.revient_titre",{touche:dzmCombo("title_add","Maj+T")}\r\n           )',
      {'montage.pistes.revient_titre': ('revient avec {touche}, qui repose un carton (même identifiant).',
                                        'comes back with {touche}, which places a title card again (same identifier).')}),
    X(50618, 'combinaison de repli de dzmCombo : même format que le libellé de la keymap vivante (svmKeyLabelNow)'),
    S(50950, '"revient avec "+dzmCombo("adjust_add","Maj+J")+\r\n           ", qui repose un clip d\'ajustement (même identifiant)."',
      'dzT("montage.pistes.revient_ajustement",{touche:dzmCombo("adjust_add","Maj+J")}\r\n           )',
      {'montage.pistes.revient_ajustement': (
          "revient avec {touche}, qui repose un clip d'ajustement (même identifiant).",
          'comes back with {touche}, which places an adjustment clip again (same identifier).')}),
    X(50988, 'combinaison de repli de dzmCombo : même format que le libellé de la keymap vivante (svmKeyLabelNow)'),
    S(51078, '"se rajoute par « + "+(kd==="audio"?"audio":"vidéo")+\r\n           " » (même identifiant)."',
      '(kd==="audio"?dzT("montage.pistes.se_rajoute_audio"):dzT("montage.pistes.se_rajoute_video")\r\n           )',
      {'montage.pistes.se_rajoute_audio': ('se rajoute par « + audio » (même identifiant).',
                                           'is added back with “+ audio” (same identifier).'),
       'montage.pistes.se_rajoute_video': ('se rajoute par « + vidéo » (même identifiant).',
                                           'is added back with “+ video” (same identifier).')}),
    # DzmTrackBtns : poignée, ▲ ▼ ×
    L(51245, 'montage.pistes.poignee_aide', 'Glisser pour réordonner la piste (ou ▲ ▼)',
      'Drag to reorder the track (or ▲ ▼)'),
    S(52237, '"Monter "+(tr.name||tr.id)+" d\'un rang — une piste plus haute est "+\r\n        "composée AU-DESSUS au rendu"',
      'dzT("montage.pistes.monter_aide",{piste:tr.name||tr.id}\r\n        )',
      {'montage.pistes.monter_aide': (
          "Monter {piste} d'un rang — une piste plus haute est composée AU-DESSUS au rendu",
          'Move {piste} up one level — a higher track is composited ON TOP in the render')}),
    S(52366, '"Monter la piste "+(tr.name||tr.id)',
      'dzT("montage.pistes.monter_aria",{piste:tr.name||tr.id})',
      {'montage.pistes.monter_aria': ('Monter la piste {piste}', 'Move track {piste} up')}),
    S(52550, '"Descendre "+(tr.name||tr.id)+" d\'un rang"',
      'dzT("montage.pistes.descendre_aide",{piste:tr.name||tr.id})',
      {'montage.pistes.descendre_aide': ("Descendre {piste} d'un rang", 'Move {piste} down one level')}),
    S(52614, '"Descendre la piste "+(tr.name||tr.id)',
      'dzT("montage.pistes.descendre_aria",{piste:tr.name||tr.id})',
      {'montage.pistes.descendre_aria': ('Descendre la piste {piste}', 'Move track {piste} down')}),
    L(52870, 'montage.pistes.s1_base_aide', 'S1 est la seule piste de sous-titres — elle ne se retire pas',
      'S1 is the only subtitle track — it cannot be removed'),
    L(52945, 'montage.pistes.v1_base_aide', 'V1 est la piste de base du montage — elle ne se retire pas',
      'V1 is the base track of the edit — it cannot be removed'),
    S(53024, '"Confirmer : retirer "+(tr.name||tr.id)+" ET ses "+n+" clip"+\r\n              (n>1?"s":"")+" — annuler ramène les clips"',
      '(n>1?dzT("montage.pistes.confirmer_retrait.plusieurs",{piste:tr.name||tr.id,n:n}):\r\n              dzT("montage.pistes.confirmer_retrait.un",{piste:tr.name||tr.id,n:n}))',
      {'montage.pistes.confirmer_retrait.un': ('Confirmer : retirer {piste} ET ses {n} clip — annuler ramène les clips',
                                               'Confirm: remove {piste} AND its {n} clip — undo brings the clips back'),
       'montage.pistes.confirmer_retrait.plusieurs': (
           'Confirmer : retirer {piste} ET ses {n} clips — annuler ramène les clips',
           'Confirm: remove {piste} AND its {n} clips — undo brings the clips back')}),
    S(53159, '"Retirer la piste "+(tr.name||tr.id)+" ("+n+" clip"+(n>1?"s":"")+\r\n              " — un second clic confirmera)"',
      '(n>1?dzT("montage.pistes.retirer_clips.plusieurs",{piste:tr.name||tr.id,n:n}):\r\n              dzT("montage.pistes.retirer_clips.un",{piste:tr.name||tr.id,n:n}))',
      {'montage.pistes.retirer_clips.un': ('Retirer la piste {piste} ({n} clip — un second clic confirmera)',
                                           'Remove track {piste} ({n} clip — a second click will confirm)'),
       'montage.pistes.retirer_clips.plusieurs': ('Retirer la piste {piste} ({n} clips — un second clic confirmera)',
                                                  'Remove track {piste} ({n} clips — a second click will confirm)')}),
    S(53283, '"Retirer la piste "+(tr.name||tr.id)+" (vide)"',
      'dzT("montage.pistes.retirer_vide",{piste:tr.name||tr.id})',
      {'montage.pistes.retirer_vide': ('Retirer la piste {piste} (vide)', 'Remove track {piste} (empty)')}),
    S(53351, '"Retirer la piste "+(tr.name||tr.id)',
      'dzT("montage.pistes.retirer_aria",{piste:tr.name||tr.id})',
      {'montage.pistes.retirer_aria': _RETIRER_ARIA}),

    # DzmWordAnimChip : la chip « mot : couleur / rebond / glow »
    L(54224, 'montage.motanim.aria', 'Animation des sous-titres, mot par mot', 'Subtitle animation, word by word'),
    L(54343, 'montage.motanim.mot', 'mot', 'word'),

    # dzmEmojiGo : l'action emoji (notes)
    S(56853, '"Aucun sous-titre : les emoji se posent sur les MOTS d\'une "+\r\n      "réplique. Écrivez la piste S1 d\'abord."',
      'dzT("montage.emoji.sans_soustitre"\r\n      )',
      {'montage.emoji.sans_soustitre': (
          "Aucun sous-titre : les emoji se posent sur les MOTS d'une réplique. Écrivez la piste S1 d'abord.",
          'No subtitles: emoji are placed on the WORDS of a line. Write track S1 first.')}),
    L(57035, 'montage.emoji.sans_hote', 'Emoji : rien pour recevoir les clips.', 'Emoji: nothing to receive the clips.'),
    L(57285, 'montage.emoji.sans_reseau', 'Emoji : ce navigateur ne sait pas interroger le serveur.',
      'Emoji: this browser cannot query the server.'),
    S(57678, '"Aucun mot-clé reconnu — les mots suivis sont "+\r\n        "feu, lune, vague, poulpe, or, fusée."',
      'dzT("montage.emoji.aucun_mot_cle"\r\n        )',
      {'montage.emoji.aucun_mot_cle': (
          'Aucun mot-clé reconnu — les mots suivis sont feu, lune, vague, poulpe, or, fusée.',
          'No keyword recognized — the tracked words are feu, lune, vague, poulpe, or, fusée.')}),
    S(57864, '"Aucune piste vidéo d\'overlay pour les poser : "+\r\n        "ajoutez-en une par « + vidéo »."',
      'dzT("montage.emoji.sans_overlay"\r\n        )',
      {'montage.emoji.sans_overlay': (
          "Aucune piste vidéo d'overlay pour les poser : ajoutez-en une par « + vidéo ».",
          'No overlay video track to place them on: add one with “+ video”.')}),
    S(57998, 'cs.length+" emoji posé"+(cs.length>1?"s":"")+" sur "+cs[0].tr+\r\n        " — annuler les retire tous."',
      '(cs.length>1?dzT("montage.emoji.poses.plusieurs",{n:cs.length,piste:cs[0].tr}):dzT("montage.emoji.poses.un",{n:cs.length,piste:cs[0].tr})\r\n        )',
      {'montage.emoji.poses.un': ('{n} emoji posé sur {piste} — annuler les retire tous.',
                                  '{n} emoji placed on {piste} — undo removes them all.'),
       'montage.emoji.poses.plusieurs': ('{n} emoji posés sur {piste} — annuler les retire tous.',
                                         '{n} emoji placed on {piste} — undo removes them all.')}),
    S(58148, '"Emoji : "+((e&&e.message)||"échec de la requête")',
      'dzT("montage.emoji.erreur",{e:(e&&e.message)||dzT("montage.emoji.echec_requete")})',
      {'montage.emoji.erreur': ('Emoji : {e}', 'Emoji: {e}'),
       'montage.emoji.echec_requete': ('échec de la requête', 'request failed')}),

    # DZM_EMO_TITRE, DzmEmojiBtn : le bouton « emoji » du bandeau
    S(58494, '"Poser un emoji sur les mots-clés des sous-titres (feu, "+\r\n  "lune, vague, poulpe, or, fusée) — un clip par mot, sur la piste "+\r\n  "d\'overlay la plus haute. Annuler les retire."',
      'dzT("montage.emoji.bouton_aide"\r\n  \r\n  )',
      {'montage.emoji.bouton_aide': (
          "Poser un emoji sur les mots-clés des sous-titres (feu, lune, vague, poulpe, or, fusée) — un clip par mot, "
          "sur la piste d'overlay la plus haute. Annuler les retire.",
          'Place an emoji on the subtitle keywords (feu, lune, vague, poulpe, or, fusée) — one clip per word, on '
          'the topmost overlay track. Undo removes them.')}),
    L(58875, 'montage.emoji.bouton_aria', 'Poser les emoji des mots-clés', 'Place emoji on the keywords'),
]
