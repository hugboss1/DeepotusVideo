"""t143 — montage_e : couche Montage (window.DzTracks, frontend/patches/montage.js), lignes 3530–6345 de la base.
Couvre : le câblage de la barre d'outils (dzmTbCablage : titres des boutons PISTES et Bibliothèque), sa géométrie
(étiquette ARIA de la barre, « Raccourci : », onglet d'appel, boutons ⌖ et ×), la bande de plage I/O (DzmRange),
les modes d'insertion (libellés de DZM_MODES, phrases de DZM_MODE_T, notes de dzmInsere : écrêtage de vitesse, repli
« au-dessus », jumeau verrouillé ; DzmModeBar), les marqueurs (DzmMarkers, DzmMarkerIndex), la grille des
transitions (DzmTransGrid : familles « coupe » et « historiques », « visible après Preview »), l'inspecteur de carton
titre (DzmTitleInspector), le bandeau de fin de rendu (DzmFinBandeau), la vue Livraison (DzmDeliver), le texte de
tête de l'inspecteur (dzmTeteTxt) et les statuts de job (dzmDelStatut).

Gardés (X) : les sélecteurs CSS (« .dzm-tbb,.dzm-tbwb », « .dzm-tbtab,… », « .svm-transbtns,… ») ; les libellés de
DZM_BD_RETIRES (« + piste vidéo », « + piste audio », « Bibliothèque… ») : une table de LARGEUR (longueur × px par
caractère) que le banc rapproche du libellé réel du bandeau, jamais affichée ; « Transitions — » (identique en
anglais, le nom de famille vient du serveur, déjà traduit) ; les entités HTML de dzmTtEsc et le gabarit HTML du
carton (« <div class="dzm-tt », « </div> ») ; les paramètres d'URL « &text= » / « &sub= » ; « Ajustement » (label
ENREGISTRÉ dans le projet par dzmAdjustNew) ; « montage neuf » et « (non nommé) » (noms de projet envoyés au serveur
et stockés) ; « Montage » (légende par défaut envoyée au Scheduler) ; les noms propres Telegram / Instagram ;
« (aperçu 480p) » (suffixe posé par montage_service sur le titre du job et COMPARÉ par indexOf) ; les cibles de
loudness (« −14 YouTube · TikTok », « −16 podcast », « −23 EBU », identiques en anglais) ; « Standard » / « Maison »
(clés de groupe COMPARÉES par grp(), libellés traduits au site d'affichage, groupe montage_f).
Les ids des modes (ecraser, inserer…) et des familles de transitions sont des valeurs : seuls les libellés passent par
dzT. « Titre » de la vignette part dans l'URL de /title-preview, mais seulement pour dessiner l'aperçu (rien n'est
stocké) : traduit. Les phrases coupées en morceaux concaténés sont recomposées en une clé (S) qui garde autant de
fins de ligne que le code d'origine."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_FERMER = ('Fermer', 'Close')
_TITRE = ('Titre', 'Title')
_VOIR_BIBLIO = ('Voir dans la Bibliothèque', 'View in the Library')
_DU_GABARIT = ('(du gabarit{v})', '(from template{v})')

ENTREES = [
    # dzmTbCablage : titres des boutons PISTES et Bibliothèque de la barre d'outils
    S(209225, '"Ajouter une piste vidéo plein cadre — ses plans "+\r\n      "RECOUVRENT V1 pendant leur durée et leur son est extrait sur la "+\r\n      "piste de dialogue ; ses plans ont leurs transitions, leur vitesse et "+\r\n      "leurs effets, comme V1 (fondus visibles dans l\'aperçu rendu) ; V1 reste "+\r\n      "la séquence maîtresse (durée)."',
      'dzT("montage.cablage.piste_video"\r\n      \r\n      \r\n      \r\n      )',
      {'montage.cablage.piste_video': (
          "Ajouter une piste vidéo plein cadre — ses plans RECOUVRENT V1 pendant leur durée et leur son est extrait "
          "sur la piste de dialogue ; ses plans ont leurs transitions, leur vitesse et leurs effets, comme V1 (fondus "
          "visibles dans l'aperçu rendu) ; V1 reste la séquence maîtresse (durée).",
          'Add a full-frame video track — its clips COVER V1 for their duration and their sound is extracted to the '
          'dialogue track; its clips have their transitions, speed and effects, like V1 (fades visible in the '
          'rendered preview); V1 remains the master sequence (duration).')}),
    S(209723, '"Ajouter une piste d\'incrustation — image dans l\'image, "+\r\n      "réglable (position, échelle, rotation, opacité), muette ; ses plans "+\r\n      "ont aussi transitions, vitesse et effets."',
      'dzT("montage.cablage.piste_incrust"\r\n      \r\n      )',
      {'montage.cablage.piste_incrust': (
          "Ajouter une piste d'incrustation — image dans l'image, réglable (position, échelle, rotation, opacité), "
          "muette ; ses plans ont aussi transitions, vitesse et effets.",
          'Add an overlay track — picture in picture, adjustable (position, scale, rotation, opacity), muted; its '
          'clips also have transitions, speed and effects.')}),
    S(210078, '"Ajouter une piste audio — posée sous les pistes audio "+\r\n      "existantes, au-dessus des sous-titres."',
      'dzT("montage.cablage.piste_audio"\r\n      )',
      {'montage.cablage.piste_audio': (
          'Ajouter une piste audio — posée sous les pistes audio existantes, au-dessus des sous-titres.',
          'Add an audio track — placed below the existing audio tracks, above the subtitles.')}),
    S(211027, '"Ouvrir la Bibliothèque et poser une vidéo, une image ou un "+\r\n        "rendu sur la piste "+String(vid).toUpperCase()+", à la tête de "+\r\n        "lecture — c\'est la piste vidéo la plus haute du projet."',
      'dzT("montage.cablage.bibliotheque",{piste:String(vid).toUpperCase()}\r\n        \r\n        )',
      {'montage.cablage.bibliotheque': (
          "Ouvrir la Bibliothèque et poser une vidéo, une image ou un rendu sur la piste {piste}, à la tête de "
          "lecture — c'est la piste vidéo la plus haute du projet.",
          "Open the Library and place a video, an image or a render on track {piste}, at the playhead — it is the "
          "project's topmost video track.")}),
    S(211279, '"Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le "+\r\n        "clip. « vidéo » du groupe PISTES en crée une."',
      'dzT("montage.cablage.sans_video"\r\n        )',
      {'montage.cablage.sans_video': (
          'Aucune piste vidéo dans ce projet : rien ne pourrait recevoir le clip. « vidéo » du groupe PISTES en '
          'crée une.',
          'No video track in this project: nothing could receive the clip. “video” in the TRACKS group creates '
          'one.')}),

    # géométrie de la barre : sélecteur du roving, étiquette ARIA, combo, onglet d'appel, ⌖ et ×
    X(236229, 'sélecteur CSS (querySelectorAll du roving)'),
    L(236271, 'montage.barre_outils.aria', 'Outils de création', 'Creation tools'),
    S(242349, '" Raccourci : "+s+"."', 'dzT("montage.barre_outils.raccourci",{touche:s})',
      {'montage.barre_outils.raccourci': (' Raccourci : {touche}.', ' Shortcut: {touche}.')}),
    L(243132, 'montage.barre_outils.ouvrir', "Ouvrir la barre d'outils de création.", 'Open the creation toolbar.'),
    L(248675, 'montage.barre_outils.recentrer', "Recentrer la barre d'outils", 'Recenter the toolbar'),
    L(248958, 'montage.barre_outils.replier', "Replier la barre d'outils", 'Collapse the toolbar'),

    # DZM_BD_RETIRES : table de largeur du bandeau, jamais affichée ; sélecteurs CSS des blocs
    X(270065, 'table de largeur (longueur × px par caractère) rapprochée par le banc du libellé du bandeau'),
    X(270134, 'table de largeur (longueur × px par caractère) rapprochée par le banc du libellé du bandeau'),
    X(270202, 'table de largeur (longueur × px par caractère) rapprochée par le banc du libellé du bandeau'),
    X(277152, 'sélecteur CSS'),
    X(277628, 'sélecteur CSS'),

    # DzmRange : la bande de la plage I/O
    S(284949, '"Plage "+rg.in.toFixed(2)+" s → "+rg.out.toFixed(2)+" s — I : entrée, "+\r\n      "U : sortie, X : effacer, Maj+X : couper la plage (toutes pistes, ripple)"',
      'dzT("montage.plage_bande.aide",{a:rg.in.toFixed(2),b:rg.out.toFixed(2)}\r\n      )',
      {'montage.plage_bande.aide': (
          'Plage {a} s → {b} s — I : entrée, U : sortie, X : effacer, Maj+X : couper la plage (toutes pistes, ripple)',
          'Range {a} s → {b} s — I: in, U: out, X: clear, Shift+X: cut the range (all tracks, ripple)')}),

    # DZM_MODES : libellés des modes d'insertion (les ids sont des valeurs)
    L(290811, 'montage.modes.ecraser', 'écraser', 'overwrite'),
    L(290833, 'montage.modes.inserer', 'insérer', 'insert'),
    L(290855, 'montage.modes.fin', 'en fin', 'at end'),
    L(290875, 'montage.modes.dessus', 'au-dessus', 'above'),
    L(290906, 'montage.modes.ripple_ecraser', 'écraser en ripple', 'ripple overwrite'),
    L(290942, 'montage.modes.remplir', 'remplir la plage', 'fill range'),

    # dzmInsereUn / dzmInsere : notes affichées par l'appelant
    L(295691, 'montage.insertion.vitesse_max', 'vitesse écrêtée à ×4 (source trop longue pour la plage)',
      'speed clipped to ×4 (source too long for the range)'),
    L(295757, 'montage.insertion.vitesse_min', 'vitesse écrêtée à ×0,25 (source trop courte pour la plage)',
      'speed clipped to ×0.25 (source too short for the range)'),
    S(297915, '"aucune piste libre au-dessus : posé sur "+String(tr==null?"":tr).toUpperCase()',
      'dzT("montage.insertion.aucune_libre",{piste:String(tr==null?"":tr).toUpperCase()})',
      {'montage.insertion.aucune_libre': ('aucune piste libre au-dessus : posé sur {piste}',
                                          'no free track above: placed on {piste}')}),
    S(298539, '"piste "+String(tw.tr).toUpperCase()+\r\n        " verrouillée : le son n\'a pas été posé"',
      'dzT("montage.insertion.jumeau_verrou",{piste:String(tw.tr).toUpperCase()}\r\n        )',
      {'montage.insertion.jumeau_verrou': ("piste {piste} verrouillée : le son n'a pas été posé",
                                           'track {piste} locked: the sound was not placed')}),

    # DZM_MODE_T et DzmModeBar : la rangée des modes du sélecteur d'assets
    L(300261, 'montage.modes.ecraser_aide', 'Écraser : le clip se pose à la tête et rogne ou fend ce qui est dessous.',
      'Overwrite: the clip goes at the playhead and trims or splits what is underneath.'),
    L(300348, 'montage.modes.inserer_aide', 'Insérer : fend à la tête et pousse la suite de la piste (ripple).',
      'Insert: splits at the playhead and pushes the rest of the track (ripple).'),
    L(300424, 'montage.modes.fin_aide', 'En fin : après le dernier clip de la piste, la tête est ignorée.',
      'At end: after the last clip of the track, the playhead is ignored.'),
    L(300502, 'montage.modes.dessus_aide',
      'Au-dessus : sur la piste vidéo libre la plus proche au-dessus (titres, PIP).',
      'Above: on the nearest free video track above (titles, PIP).'),
    L(300600, 'montage.modes.ripple_ecraser_aide',
      'Écraser en ripple : remplace le clip sous la tête, la suite se recale à la nouvelle durée.',
      'Ripple overwrite: replaces the clip under the playhead, the rest realigns to the new duration.'),
    L(300705, 'montage.modes.remplir_aide',
      'Remplir la plage : bornes = plage I/O, vitesse calculée pour la remplir (V1).',
      'Fill range: bounds = I/O range, speed computed to fill it (V1).'),
    L(300988, 'montage.modes.aria', "Mode d'édition", 'Edit mode'),
    L(301339, 'montage.modes.sans_plage', " — posez d'abord une plage (I / U).", ' — set a range first (I / U).'),

    # DzmMarkers : les losanges sur la règle
    L(316456, 'montage.marqueurs.combo_repli', 'Maj+M', 'Shift+M'),
    S(316820, '"Marqueur "+dzTc(m.t)', 'dzT("montage.marqueurs.aria",{t:dzTc(m.t)})',
      {'montage.marqueurs.aria': ('Marqueur {t}', 'Marker {t}')}),
    L(316893, 'montage.marqueurs.defaut', 'marqueur', 'marker'),
    S(316955, '"\\nclic : aller · "+dzmMarkerCombo()+" à la tête : retirer"',
      'dzT("montage.marqueurs.aide_clic",{touche:dzmMarkerCombo()})',
      {'montage.marqueurs.aide_clic': ('\nclic : aller · {touche} à la tête : retirer',
                                       '\nclick: go · {touche} at the playhead: remove')}),

    # DzmMarkerIndex : l'index des marqueurs
    S(318575, '"Marqueurs — "+ms.length', 'dzT("montage.marqueurs.titre",{n:ms.length})',
      {'montage.marqueurs.titre': ('Marqueurs — {n}', 'Markers — {n}')}),
    L(318753, 'montage.marqueurs.aller', 'aller à ce marqueur', 'go to this marker'),
    S(318941, '"Couleur du marqueur "+dzTc(m.t)', 'dzT("montage.marqueurs.couleur",{t:dzTc(m.t)})',
      {'montage.marqueurs.couleur': ('Couleur du marqueur {t}', 'Marker color {t}')}),
    L(320541, 'montage.marqueurs.titre_placeholder', 'titre', 'title'),
    S(320562, '"Titre du marqueur "+dzTc(m.t)', 'dzT("montage.marqueurs.titre_aria",{t:dzTc(m.t)})',
      {'montage.marqueurs.titre_aria': ('Titre du marqueur {t}', 'Marker title {t}')}),
    L(320788, 'montage.marqueurs.retirer_aide', 'Retirer ce marqueur', 'Remove this marker'),
    S(320835, '"Retirer le marqueur "+dzTc(m.t)', 'dzT("montage.marqueurs.retirer_aria",{t:dzTc(m.t)})',
      {'montage.marqueurs.retirer_aria': ('Retirer le marqueur {t}', 'Remove marker {t}')}),
    S(321034, '"Aucun marqueur — "+dzmMarkerCombo()+\r\n          " en pose un à la tête de lecture."',
      'dzT("montage.marqueurs.aucun",{touche:dzmMarkerCombo()}\r\n          )',
      {'montage.marqueurs.aucun': ('Aucun marqueur — {touche} en pose un à la tête de lecture.',
                                   'No markers — {touche} adds one at the playhead.')}),
    L(321225, 'montage.marqueurs.fermer_aide', "Fermer l'index des marqueurs", 'Close the marker index'),
    L(321296, 'montage.mots.fermer', *_FERMER),

    # dzmTransList / DzmTransGrid : familles locales (les ids sont des valeurs) et infobulle
    L(331038, 'montage.transgrille.coupe', 'coupe', 'cut'),
    L(331751, 'montage.transgrille.historiques', 'historiques', 'legacy'),
    X(333399, 'identique en anglais (« Transitions — » + nom de famille servi par le serveur)'),
    L(334058, 'montage.transgrille.apres_preview', ' — visible après Preview', ' — visible after preview'),

    # dzmTtEsc : entités HTML ; dzmAdjustNew : label stocké ; dzmTtHtml : gabarit HTML du carton
    X(341246, 'entité HTML'),
    X(341268, 'entité HTML'),
    X(341289, 'entité HTML'),
    X(341314, 'entité HTML'),
    X(345434, 'label ENREGISTRÉ dans le projet (clip d\'ajustement)'),
    X(347492, 'gabarit HTML'),
    X(347611, 'gabarit HTML'),

    # DzmTitleInspector : l'inspecteur du carton titre
    L(357498, 'montage.mots.titre', *_TITRE),
    L(357617, 'montage.carton_insp.titre', 'Titre — gabarit', 'Title — template'),
    L(358149, 'montage.carton_insp.gabarits_aria', 'Gabarits de titre', 'Title templates'),
    X(358673, "paramètre d'URL"),
    L(358714, 'montage.mots.titre', *_TITRE),
    X(358749, "paramètre d'URL"),
    L(358959, 'montage.carton_insp.indisponibles', 'Gabarits indisponibles — le texte reste réglable.',
      'Templates unavailable — the text stays adjustable.'),
    L(359120, 'montage.mots.texte', 'Texte', 'Text'),
    L(359239, 'montage.mots.titre', *_TITRE),
    L(359270, 'montage.carton_insp.texte_aria', 'Texte du carton', 'Title card text'),
    L(359554, 'montage.carton_insp.sous_texte', 'Sous-texte', 'Subtext'),
    L(359677, 'montage.carton_insp.aucun', '(aucun)', '(none)'),
    L(359710, 'montage.carton_insp.sous_texte_aria', 'Sous-texte du carton', 'Title card subtext'),
    L(359999, 'montage.mots.couleur', 'Couleur', 'Color'),
    L(360135, 'montage.carton_insp.couleur_aria', 'Couleur du carton', 'Title card color'),
    S(360280, '"(du gabarit"+(gab&&gab.color?" — "+gab.color:"")+")"',
      'dzT("montage.carton_insp.du_gabarit",{v:gab&&gab.color?" — "+gab.color:""})',
      {'montage.carton_insp.du_gabarit': _DU_GABARIT}),
    L(360595, 'montage.mots.police', 'Police', 'Font'),
    L(360728, 'montage.carton_insp.police_aria', 'Police du carton', 'Title card font'),
    S(360870, '"(du gabarit"+(gab&&gab.font?" — "+gab.font:"")+")"',
      'dzT("montage.carton_insp.du_gabarit",{v:gab&&gab.font?" — "+gab.font:""})',
      {'montage.carton_insp.du_gabarit': _DU_GABARIT}),
    L(361184, 'montage.mots.taille', 'Taille', 'Size'),
    L(361337, 'montage.carton_insp.taille_aria', 'Corps du titre à 1080 p, en pixels', 'Title size at 1080p, in pixels'),
    S(361674, '"Le placement et l\'animation viennent du gabarit. "+\r\n        "L\'aperçu du lecteur est approché : Preview 480p fait foi."',
      'dzT("montage.carton_insp.note"\r\n        )',
      {'montage.carton_insp.note': (
          "Le placement et l'animation viennent du gabarit. L'aperçu du lecteur est approché : Preview 480p fait foi.",
          'Placement and animation come from the template. The player preview is approximate: the 480p preview is '
          'authoritative.')}),

    # dzmProjetNeuf / dzmInstantaneNom : noms de projet envoyés au serveur ; canaux ; légende par défaut
    X(362357, 'nom de projet envoyé au serveur (POST /projects) et stocké'),
    X(362681, 'nom de la copie de sûreté, envoyé au serveur et stocké'),
    X(363352, 'nom propre'),
    X(363399, 'nom propre'),
    X(364179, 'légende par défaut envoyée au Scheduler (stockée)'),

    # DzmFinBandeau : le bandeau de fin de rendu
    L(364435, 'montage.fin.ok', 'Brouillon ajouté au Scheduler', 'Draft added to the Scheduler'),
    L(365228, 'montage.fin.titre', 'Rendu terminé', 'Render finished'),
    L(365711, 'montage.fin.legende', 'légende', 'caption'),
    L(365988, 'montage.fin.envoyer_aide',
      "Envoyer ce rendu au Scheduler (brouillon, rien n'est publié sans validation)",
      'Send this render to the Scheduler (draft, nothing is published without approval)'),
    S(366336, '"Envoi impossible : "+String(e)', 'dzT("montage.fin.envoi_impossible",{e:String(e)})',
      {'montage.fin.envoi_impossible': ('Envoi impossible : {e}', 'Sending failed: {e}')}),
    L(366381, 'montage.fin.envoyer', 'Envoyer vers le Scheduler', 'Send to the Scheduler'),
    L(366464, 'montage.fin.biblio_aide', 'Ouvrir la Bibliothèque sur ce rendu', 'Open the Library on this render'),
    L(366550, 'montage.livraison.voir_biblio', *_VOIR_BIBLIO),
    L(366633, 'montage.fin.fermer_aide', 'Fermer le bandeau (Échap)', 'Close the banner (Esc)'),
    L(366713, 'montage.mots.fermer', *_FERMER),

    # DzmDeliver : la vue Livraison
    X(368021, "suffixe posé par montage_service sur le titre du job, COMPARÉ par indexOf"),
    L(369073, 'montage.livraison.apercu', 'aperçu', 'preview'),
    L(369486, 'montage.livraison.titre', 'Livraison', 'Delivery'),
    L(369607, 'montage.livraison.preview_aide', 'Aperçu 480p — rapide, pour vérifier le montage',
      '480p preview — fast, to check the edit'),
    L(369712, 'montage.livraison.preview', 'Preview 480p', '480p preview'),
    L(369783, 'montage.livraison.rendre_aide', 'Rendu final (master 1080), aucun crédit consommé',
      'Final render (1080 master), no credits used'),
    L(369888, 'montage.livraison.rendre', 'Rendre…', 'Render…'),
    L(369987, 'montage.livraison.publier_aide', 'Envoyer le dernier rendu final au Scheduler',
      'Send the latest final render to the Scheduler'),
    L(370033, 'montage.livraison.publier_vide', 'Aucun rendu final pour ce projet', 'No final render for this project'),
    L(370139, 'montage.livraison.publier', 'Publier ce rendu', 'Publish this render'),
    S(370218, '"Dernier rendu final : "+String(lf.name||"")+" · "+dzmDelDate(lf.at)',
      'dzT("montage.livraison.dernier",{nom:String(lf.name||""),date:dzmDelDate(lf.at)})',
      {'montage.livraison.dernier': ('Dernier rendu final : {nom} · {date}', 'Latest final render: {nom} · {date}')}),
    L(370287, 'montage.livraison.dernier_aucun', 'Dernier rendu final : aucun', 'Latest final render: none'),
    L(370534, 'montage.livraison.aucun', 'Aucun rendu pour ce projet.', 'No renders for this project.'),
    L(370619, 'montage.livraison.biblio_aide', 'Ouvrir la Bibliothèque sur les rendus vidéo',
      'Open the Library on video renders'),
    L(370721, 'montage.livraison.voir_biblio', *_VOIR_BIBLIO),

    # dzmTeteTxt : la tête dans l'inspecteur
    S(372591, '"tête à "+f(p)', 'dzT("montage.tete_txt.a",{t:f(p)})',
      {'montage.tete_txt.a': ('tête à {t}', 'playhead at {t}')}),
    S(372747, '" · +"+f(p-Number(sel.start))+" dans le plan"', 'dzT("montage.tete_txt.dans",{t:f(p-Number(sel.start))})',
      {'montage.tete_txt.dans': (' · +{t} dans le plan', ' · +{t} into the clip')}),
    L(372793, 'montage.tete_txt.hors', ' · hors du plan', ' · outside the clip'),

    # réglages de livraison : cibles de loudness, groupes de presets, statuts de job
    X(375880, 'identique en anglais (cible de loudness et ses plateformes)'),
    X(375909, 'identique en anglais (cible de loudness)'),
    X(375929, 'identique en anglais (cible de loudness)'),
    X(376661, 'clé de groupe COMPARÉE par grp() ; libellé traduit au site d\'affichage'),
    X(376692, 'clé de groupe COMPARÉE par grp() ; libellé traduit au site d\'affichage'),
    L(377357, 'montage.livraison.statut_file', 'en file', 'queued'),
    S(377391, '"en cours "+p+" %"', 'dzT("montage.livraison.statut_en_cours",{p:p})',
      {'montage.livraison.statut_en_cours': ('en cours {p} %', 'in progress {p}%')}),
    L(377422, 'montage.livraison.statut_termine', 'terminé', 'done'),
    L(377446, 'montage.livraison.statut_echec', 'échec', 'failed'),
    # onglet de la barre d'outils flottante (mot seul en capitales, que le contrôle lexical ne voit pas)
    L(243532, 'montage.barre_outils.onglet', 'OUTILS', 'TOOLS'),
]
