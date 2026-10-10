"""t143 — montage_f : couche frontend/patches/montage.js, lignes 6346–7067 de la base be7f9e9f. Couvre : la ligne
d'options de livraison (DzmDeliverRow : preset, cadence, loudness, plage I/O, « Enregistrer ce réglage… »), l'état de
l'analyse de stabilisation (dzmStabState), l'hôte des propriétés de plan (DzmPlanProps : zoom dynamique, courbe,
fenêtres, interpolation du retime, rampe, stabilisation, cadrage centré / suivi / manuel, analyse du mouvement), les
deux rectangles du zoom dans le lecteur (DzmDzRects), le tiroir Médias (provenance, recherche, chips de note,
étoiles, auto-clips d'une ligne, messages de chargement / de note refusée) et les phrases des auto-clips
(estimation de la transcription payante, origine du texte, origine du score).

Gardés (X) :
- les fragments d'URL de GET /api/jobs (« &offset= », « &video=1 », « &min_rating= ») et le morceau de transform CSS
  « %) scale( » ;
- les groupes de provenance de DZM_PROV_LBL (« Studio », « Chapitres », « News », « Templates », « Importés »,
  « Montages ») et « Tout » : ce sont des VALEURS — dzmProvChips / dzmMediaFiltre les comparent (`g!=="Tout"`,
  `chips.indexOf(groupe)`, `dzmProvGroupe(...)!==g`), l'état `groupe` part de « Tout ». Ils sont traduits au SITE
  D'AFFICHAGE par une petite table dzmProvAff (posée sur la ligne de dzmProvGroupe, sans ajouter de ligne ; clés
  d'objet non citées pour ne pas créer de littéral) : chip du filtre et chip de groupe d'une ligne. Un provider
  inconnu reste montré tel quel ;
- le groupe d'optgroup « Maison » (et « Standard ») : `grp(g)` filtre `p.groupe===g` — valeur ; le libellé
  « Maison » est traduit au site d'affichage (`label:`), « Standard » est le même mot en anglais ;
- les titres de DZM_NOTE_CHIPS (tableau de MODULE : un dzT à l'évaluation du module tournerait avant la langue et
  hors des bancs) : traduits au site d'affichage (title des chips de note, par le seuil n[0]) ;
- mots identiques dans les deux langues : « preset », « loudness », « Zoom », « points », « min », « — Good Take ».
Valeurs non signalées et laissées sans entrée : `ease` "lin"/"doux", `crop` "keep"/"black", les modes
"in"/"out"/"custom"/"off", "nearest"/"blend"/"flow", `data-k` "fin"/"debut", `data-st` "busy"/"suivi", "seedance".
Phrases recomposées (S) : la pastille LUFS, l'état de l'analyse de stabilisation, les fenêtres du zoom, le titre
« Suivre le mouvement analysé (n points) », les titres des rectangles du zoom (Fin/Début + « du zoom… » en deux
clés entières), les messages du tiroir (chargement impossible, note refusée, aide d'une ligne, auto-clips de « … »,
étoiles, aucun rendu noté), l'estimation et l'origine du texte des auto-clips.
"""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_AUCUNE = ('aucune', 'none')
_IDENTIQUE = 'identique dans les deux langues'
_PROV = 'groupe de provenance : valeur comparée (filtre, chips) — traduit à l\'affichage par dzmProvAff'
_TOUT = 'valeur du filtre de groupe (état, comparaisons) — traduite à l\'affichage par dzmProvAff'
_NOTE = 'titre de chip dans un tableau de module — traduit au site d\'affichage (title des chips de note)'

ENTREES = [
    # DzmDeliverRow : options de livraison du rendu final
    L(378190, 'montage.livraison.absent', ' (absent)', ' (missing)'),
    L(378357, 'montage.livraison.mesurer_dabord', "mesurez d'abord (bouton « mesurer » du bandeau Son)",
      'measure first (“measure” button in the Sound bar)'),
    S(378411, '"mesure "+dzmLoudTxt(li)+" LUFS · cible "+(lz==null?"aucune":dzmLoudTxt(lz))',
      'dzT("montage.livraison.mesure",{m:dzmLoudTxt(li),c:lz==null?dzT("montage.mots.aucune"):dzmLoudTxt(lz)})',
      {'montage.livraison.mesure': ('mesure {m} LUFS · cible {c}', 'measured {m} LUFS · target {c}'),
       'montage.mots.aucune': _AUCUNE}),
    S(377771, 'label:g,', 'label:g==="Maison"?dzT("montage.livraison.groupe_maison"):g,',
      {'montage.livraison.groupe_maison': ('Maison', 'Custom')}),
    X(378612, _IDENTIQUE),
    L(378652, 'montage.livraison.preset_aide',
      'Preset de sortie (codec, taille, conteneur) — les presets maison suivent les standards',
      'Output preset (codec, size, container) — custom presets come after the standard ones'),
    X(378821, 'groupe de preset : valeur comparée (p.groupe===g), identique en anglais'),
    X(378837, 'groupe de preset : valeur comparée (p.groupe===g) — traduit au site d\'affichage (label:)'),
    L(378879, 'montage.livraison.cadence', 'cadence', 'frame rate'),
    L(378919, 'montage.livraison.cadence_aide', "Cadence d'images du rendu final — « projet » laisse celle du preset",
      'Frame rate of the final render — “project” keeps the preset’s'),
    L(379167, 'montage.livraison.cadence_projet', 'projet (30)', 'project (30)'),
    X(379326, _IDENTIQUE),
    L(379424, 'montage.livraison.loudness_aide',
      'Normalisation de loudness en deux passes (ffmpeg loudnorm) — « aucune » laisse le mix tel quel',
      'Two-pass loudness normalization (ffmpeg loudnorm) — “none” leaves the mix as is'),
    L(379679, 'montage.mots.aucune', *_AUCUNE),
    L(379964, 'montage.livraison.plage_aide',
      "Ne rendre que la plage I/O de la timeline (coupe de sortie — sous-titres et titres gardent l'horloge globale)",
      'Render only the timeline I/O range (output cut — subtitles and titles keep the global clock)'),
    L(380156, 'montage.livraison.plage_seule', 'Rendre la plage I/O seulement', 'Render the I/O range only'),
    L(380255, 'montage.livraison.plage_seule_case', ' Rendre la plage I/O seulement', ' Render the I/O range only'),
    L(380371, 'montage.livraison.enregistrer_aide',
      'Enregistrer preset + cadence comme preset maison (un nom est demandé)',
      'Save preset + frame rate as a custom preset (you will be asked for a name)'),
    L(380507, 'montage.livraison.enregistrer', 'Enregistrer ce réglage…', 'Save this setting…'),

    # dzmDzCss : transformation CSS de la <video>
    X(383571, 'expression CSS (transform)'),

    # dzmStabState : état de l'analyse de stabilisation (chip de la ligne « Stabilis. »)
    L(386708, 'montage.stabilisation.a_analyser', 'à analyser', 'to analyze'),
    L(386755, 'montage.stabilisation.analysee', 'analysée', 'analyzed'),
    S(386802, '"échec : "+String(job.error||"?")', 'dzT("montage.stabilisation.echec",{e:String(job.error||"?")})',
      {'montage.stabilisation.echec': ('échec : {e}', 'failed: {e}')}),
    S(386847, '"analyse "+Math.round(Number(job.progress)||0)+" %"',
      'dzT("montage.stabilisation.analyse",{p:Math.round(Number(job.progress)||0)})',
      {'montage.stabilisation.analyse': ('analyse {p} %', 'analyzing {p}%')}),

    # DzmPlanProps : zoom dynamique
    L(397881, 'montage.proprietes.zoom_dyn', 'Zoom dyn.', 'Dyn. zoom'),
    L(397966, 'montage.mots.aucun', 'aucun', 'none'),
    L(397981, 'montage.proprietes.zoom_avant', 'zoom avant', 'zoom in'),
    L(398002, 'montage.proprietes.zoom_arriere', 'zoom arrière', 'zoom out'),
    L(398028, 'montage.proprietes.personnalise', 'personnalisé', 'custom'),
    L(398178, 'montage.proprietes.zoom_aide',
      'Zoom dynamique : deux fenêtres, début (vert) et fin (rouge) du plan — glisser les rectangles dans le lecteur, '
      'le rendu interpole',
      'Dynamic zoom: two windows, start (green) and end (red) of the clip — drag the rectangles in the player, the '
      'render interpolates'),
    L(398348, 'montage.proprietes.courbe', 'Courbe', 'Easing'),
    L(398378, 'montage.proprietes.douce', 'douce', 'smooth'),
    L(398394, 'montage.proprietes.lineaire', 'linéaire', 'linear'),
    L(398462, 'montage.proprietes.zoom_interp', 'Interpolation du zoom', 'Zoom interpolation'),
    L(398519, 'montage.proprietes.fenetres', 'Fenêtres', 'Windows'),
    S(398587, '"début "+Math.round(dz.w0*100)+" % · fin "+Math.round(dz.w1*100)+" %"',
      'dzT("montage.proprietes.fenetres_val",{a:Math.round(dz.w0*100),b:Math.round(dz.w1*100)})',
      {'montage.proprietes.fenetres_val': ('début {a} % · fin {b} %', 'start {a}% · end {b}%')}),

    # DzmPlanProps : interpolation du retime, rampe
    L(398791, 'montage.proprietes.interpolation', 'Interpolation', 'Interpolation'),
    L(398837, 'montage.proprietes.image_voisine', 'image voisine', 'nearest frame'),
    L(398863, 'montage.proprietes.fondu_images', "fondu d'images", 'frame blending'),
    L(398889, 'montage.proprietes.flux_optique', 'flux optique (lent)', 'optical flow (slow)'),
    L(398985, 'montage.proprietes.retime_sans_effet', "Sans effet à 100 % — change d'abord la vitesse",
      'No effect at 100% — change the speed first'),
    L(399034, 'montage.proprietes.retime_aide',
      'Qualité du retime (D-15) : fondu = flou de mouvement, flux optique = images intermédiaires calculées',
      'Retime quality (D-15): blending = motion blur, optical flow = computed in-between frames'),
    L(399247, 'montage.proprietes.rampe', 'Rampe', 'Ramp'),
    L(399390, 'montage.proprietes.rampe_aide',
      'Diviser le plan à la tête : la partie gauche garde sa vitesse, la droite passe à la vitesse choisie',
      'Split the clip at the playhead: the left part keeps its speed, the right part takes the chosen speed'),
    L(399492, 'montage.proprietes.rampe_bords', 'Placer la tête à 0,3 s au moins des deux bords du plan',
      'Place the playhead at least 0.3 s from both edges of the clip'),
    L(399647, 'montage.proprietes.diviser', 'Diviser à la tête →', 'Split at playhead →'),
    L(399831, 'montage.proprietes.vitesse_droite', 'Vitesse de la partie droite', 'Speed of the right part'),

    # DzmPlanProps : stabilisation
    L(400521, 'montage.proprietes.stabilis', 'Stabilis.', 'Stabilize'),
    L(400649, 'montage.proprietes.stabiliser_aide', 'Stabiliser le plan (vidstab, deux passes au rendu)',
      'Stabilize the clip (vidstab, two passes at render)'),
    L(400876, 'montage.proprietes.analyser_aide', 'Analyser la source maintenant (sinon le rendu le fera, plus long)',
      'Analyze the source now (otherwise the render will, taking longer)'),
    L(401024, 'montage.mots.analyser', 'Analyser', 'Analyze'),
    L(401558, 'montage.proprietes.lissage', 'Lissage', 'Smoothing', contexte=True),
    L(401568, 'montage.proprietes.lissage_aide', 'Fenêtre de lissage (images) — 15 par défaut',
      'Smoothing window (frames) — 15 by default'),
    X(401650, _IDENTIQUE),
    L(401657, 'montage.proprietes.zoom_fixe_aide', 'Zoom fixe en % pour cacher les bords (0 = optzoom)',
      'Fixed zoom in % to hide the edges (0 = optzoom)'),
    L(401732, 'montage.proprietes.bords', 'Bords', 'Edges', contexte=True),
    L(401761, 'montage.proprietes.garder', 'garder', 'keep'),
    L(401780, 'montage.proprietes.noir', 'noir', 'black'),
    L(401867, 'montage.proprietes.bords_aide', 'Que faire des bords découverts', 'What to do with uncovered edges'),

    # DzmPlanProps : cadrage (centré / suivi / manuel), position, analyse du mouvement
    L(403771, 'montage.cadrage.sans_effet',
      "Sans effet sur ce plan : la source n'est pas plus large que le cadre du projet — le recadrage horizontal ne "
      "déplace rien",
      'No effect on this clip: the source is not wider than the project frame — horizontal reframing moves nothing'),
    L(403919, 'montage.cadrage.dimensions_inconnues',
      ' (dimensions de la source pas encore lues : placez la tête sur le plan)',
      ' (source dimensions not read yet: put the playhead on the clip)'),
    L(404010, 'montage.cadrage.analyse_en_cours', 'Analyse du mouvement en cours sur ce plan — les modes reviennent à la fin',
      'Motion analysis running on this clip — the modes come back when it ends'),
    L(404641, 'montage.cadrage.titre', 'Cadrage', 'Framing'),
    L(404730, 'montage.cadrage.centre', 'Centré', 'Center'),
    L(404752, 'montage.cadrage.centre_aide',
      "Cadrage centré (historique) — les points d'une analyse restent gardés pour « Suivre »",
      'Centered framing (legacy) — the points of an analysis are kept for “Track”'),
    L(404947, 'montage.cadrage.suivre', 'Suivre', 'Track'),
    S(404989, '"Suivre le mouvement analysé ("+rfPts.length+" points)"',
      'dzT("montage.cadrage.suivre_points",{n:rfPts.length})',
      {'montage.cadrage.suivre_points': ('Suivre le mouvement analysé ({n} points)',
                                         'Track the analyzed motion ({n} points)')}),
    L(405045, 'montage.cadrage.suivre_aide', 'Suivre le mouvement : analyse la source puis fait glisser la fenêtre',
      'Track the motion: analyzes the source then slides the window'),
    L(405251, 'montage.cadrage.manuel', 'Manuel', 'Manual'),
    L(405286, 'montage.cadrage.manuel_aide', 'Position fixe de la fenêtre, réglée au curseur',
      'Fixed window position, set with the slider'),
    L(405584, 'montage.cadrage.position', 'Position', 'Position'),
    L(405757, 'montage.cadrage.position_aria', 'Position horizontale du cadrage', 'Horizontal framing position'),
    L(405833, 'montage.cadrage.position_aide',
      'Position horizontale de la fenêtre dans la source : 0 % à gauche, 100 % à droite',
      'Horizontal position of the window in the source: 0% left, 100% right'),
    L(406197, 'montage.cadrage.mouvement', 'Mouvement', 'Motion'),
    L(406377, 'montage.cadrage.analyser_aide',
      "Analyser le mouvement de l'extrait (srcIn, durée de source) et passer en « Suivre »",
      'Analyze the motion of the excerpt (srcIn, source duration) and switch to “Track”'),
    L(406504, 'montage.cadrage.analyser', 'Analyser le mouvement', 'Analyze motion'),
    L(406648, 'montage.cadrage.analyse', 'analyse…', 'analyzing…'),
    X(406694, _IDENTIQUE),
    L(406823, 'montage.proprietes.titre', 'Propriétés du plan', 'Clip properties'),

    # DzmDzRects : les deux rectangles du zoom dans le lecteur
    S(408793, '(k?"Fin":"Début")+" du zoom — glisser : déplacer · coin : échelle"',
      '(k?dzT("montage.rect_zoom.fin_aide"):dzT("montage.rect_zoom.debut_aide"))',
      {'montage.rect_zoom.fin_aide': ('Fin du zoom — glisser : déplacer · coin : échelle',
                                      'Zoom end — drag: move · corner: scale'),
       'montage.rect_zoom.debut_aide': ('Début du zoom — glisser : déplacer · coin : échelle',
                                        'Zoom start — drag: move · corner: scale')}),
    L(408962, 'montage.mots.fin', 'fin', 'end'),
    L(408968, 'montage.mots.debut', 'début', 'start'),

    # tiroir Médias : provenance (valeurs gardées, affichage par dzmProvAff)
    X(410062, _PROV), X(410078, _PROV), X(410099, _PROV), X(410118, _PROV), X(410134, _PROV),
    X(410155, _PROV), X(410172, _PROV), X(410188, _PROV), X(410204, _PROV), X(410223, _PROV),
    S(410237, 'function dzmProvGroupe(p){',
      'function dzmProvAff(g){var t={Tout:dzT("montage.mots.tout"),Chapitres:dzT("montage.mots.chapitres"),'
      'Importés:dzT("montage.mots.importes"),Montages:dzT("montage.mots.montages")};'
      'return Object.prototype.hasOwnProperty.call(t,g)?t[g]:g}function dzmProvGroupe(p){',
      {'montage.mots.tout': ('Tout', 'All'),
       'montage.mots.chapitres': ('Chapitres', 'Chapters'),
       'montage.mots.importes': ('Importés', 'Imported'),
       'montage.mots.montages': ('Montages', 'Edits')}),
    X(410450, _TOUT), X(410842, _TOUT), X(410957, _TOUT),

    # tiroir Médias : chips de note (titres traduits au site d'affichage)
    X(411929, _NOTE), X(412013, _NOTE),
    X(414208, _TOUT),

    # tiroir Médias : chargement (URL gardée), note refusée
    X(416481, 'URL de GET /api/jobs'), X(416496, 'URL de GET /api/jobs'), X(416563, 'URL de GET /api/jobs'),
    S(417921, '"Rendus : chargement impossible ("+String((e&&e.message)||e)+")"',
      'dzT("montage.tiroir_medias.chargement_impossible",{e:String((e&&e.message)||e)})',
      {'montage.tiroir_medias.chargement_impossible': ('Rendus : chargement impossible ({e})',
                                                       'Renders: cannot load ({e})')}),
    S(420628, '"Note refusée : "+String((e&&e.message)||"erreur réseau")+" — note d\'avant remise."',
      'dzT("montage.tiroir_medias.note_refusee",{e:String((e&&e.message)||dzT("montage.mots.erreur_reseau"))})',
      {'montage.tiroir_medias.note_refusee': ("Note refusée : {e} — note d'avant remise.",
                                              'Rating refused: {e} — previous rating restored.'),
       'montage.mots.erreur_reseau': ('erreur réseau', 'network error')}),
    X(420912, _TOUT),

    # tiroir Médias : une ligne (aide, groupe, auto-clips, étoiles)
    S(421178, 'lbl+" — Glisser vers une bande, ou cliquer pour poser sur "+(o.trId||"la piste vidéo")',
      'dzT("montage.tiroir_medias.ligne_aide",{nom:lbl,piste:o.trId||dzT("montage.tiroir_medias.piste_video")})',
      {'montage.tiroir_medias.ligne_aide': ('{nom} — Glisser vers une bande, ou cliquer pour poser sur {piste}',
                                            '{nom} — Drag onto a lane, or click to place on {piste}'),
       'montage.tiroir_medias.piste_video': ('la piste vidéo', 'the video track')}),
    S(421949, 'children:dzmProvGroupe(j.provider)', 'children:dzmProvAff(dzmProvGroupe(j.provider))', {}),
    L(422291, 'montage.autoclips.bouton_aide',
      'Auto-clips — proposer des extraits de 15 à 60 s de ce rendu (texte connu gratuit ; transcription payante '
      'seulement après confirmation)',
      'Auto-clips — suggest 15 to 60 s excerpts from this render (known text free; paid transcription only after '
      'confirmation)'),
    S(422457, '"Auto-clips de « "+lbl+" »"', 'dzT("montage.autoclips.de",{nom:lbl})',
      {'montage.autoclips.de': ('Auto-clips de « {nom} »', 'Auto-clips of “{nom}”')}),
    L(422707, 'montage.autoclips.bouton', '✂ auto-clips', '✂ auto-clips'),
    S(423398, 'i===cur?"Retirer la note ("+i+" ★)":"Noter "+i+" ★"',
      'i===cur?dzT("montage.tiroir_medias.retirer_note",{n:i}):dzT("montage.tiroir_medias.noter",{n:i})',
      {'montage.tiroir_medias.retirer_note': ('Retirer la note ({n} ★)', 'Remove the rating ({n} ★)'),
       'montage.tiroir_medias.noter': ('Noter {n} ★', 'Rate {n} ★')}),
    X(423457, _IDENTIQUE),

    # tiroir Médias : en-tête, recherche, chips, états de la liste, « Plus »
    L(423919, 'montage.tiroir_medias.titre', 'Médias — rendus vidéo', 'Media — video renders'),
    L(424023, 'montage.tiroir_medias.fermer_aide', 'Fermer le tiroir Médias', 'Close the Media drawer'),
    L(424103, 'montage.mots.fermer', 'Fermer', 'Close'),
    L(424193, 'montage.tiroir_medias.rechercher', 'Rechercher un titre…', 'Search a title…'),
    S(424470, 'children:c},c)', 'children:dzmProvAff(c)},c)', {}),
    L(424854, 'montage.tiroir_medias.retirer_filtre', 'Retirer le filtre de note — tous les rendus',
      'Remove the rating filter — all renders'),
    S(424899, ':n[2],', ':n[0]===5?dzT("montage.tiroir_medias.note5_aide"):dzT("montage.tiroir_medias.note3_aide"),',
      {'montage.tiroir_medias.note3_aide': ('Ne montrer que les rendus notés 3 ★ ou plus (filtré par le serveur)',
                                            'Show only renders rated 3 ★ or more (filtered by the server)'),
       'montage.tiroir_medias.note5_aide': ('Ne montrer que les Good Take (5 ★, filtré par le serveur)',
                                            'Show only Good Takes (5 ★, filtered by the server)')}),
    L(425294, 'montage.tiroir_medias.aucun_groupe', 'Aucun rendu dans ce groupe.', 'No render in this group.'),
    S(425332, '"Aucun rendu noté "+(minNote>=5?"5 ★":minNote+" ★ ou plus")+"."',
      '(minNote>=5?dzT("montage.tiroir_medias.aucun_note5"):dzT("montage.tiroir_medias.aucun_note_plus",{n:minNote}))',
      {'montage.tiroir_medias.aucun_note5': ('Aucun rendu noté 5 ★.', 'No render rated 5 ★.'),
       'montage.tiroir_medias.aucun_note_plus': ('Aucun rendu noté {n} ★ ou plus.', 'No render rated {n} ★ or more.')}),
    L(425396, 'montage.tiroir_medias.aucun_rendu', 'Aucun rendu vidéo terminé.', 'No finished video render.'),
    L(425526, 'montage.tiroir_medias.plus_aide', 'Charger les rendus suivants', 'Load the next renders'),
    L(425617, 'montage.tiroir_medias.plus', 'Plus', 'More', contexte=True),

    # auto-clips : estimation de la transcription payante, origine du texte, origine du score
    L(430901, 'montage.autoclips.pas_payante', 'Pas de transcription payante possible', 'No paid transcription available'),
    X(431048, 'unité identique dans les deux langues'),
    S(431103, '"Transcription payante : ≈ "+dzmAcUsd(est.usd)+" · "+d+" · "+String(est.label||est.provider||"fournisseur inconnu")',
      'dzT("montage.autoclips.estimation",{c:dzmAcUsd(est.usd),d:d,f:String(est.label||est.provider||'
      'dzT("montage.autoclips.fournisseur_inconnu"))})',
      {'montage.autoclips.estimation': ('Transcription payante : ≈ {c} · {d} · {f}', 'Paid transcription: ≈ {c} · {d} · {f}'),
       'montage.autoclips.fournisseur_inconnu': ('fournisseur inconnu', 'unknown provider')}),
    L(431520, 'montage.autoclips.texte_connu', 'texte connu calé sur le son (gratuit)',
      'known text aligned to the audio (free)'),
    S(431605, '"transcription déjà payée, réutilisée ("+m[1]+")"', 'dzT("montage.autoclips.deja_payee",{f:m[1]})',
      {'montage.autoclips.deja_payee': ('transcription déjà payée, réutilisée ({f})',
                                        'transcription already paid, reused ({f})')}),
    S(431694, '"transcription payée ("+m[1]+")"', 'dzT("montage.autoclips.payee",{f:m[1]})',
      {'montage.autoclips.payee': ('transcription payée ({f})', 'paid transcription ({f})')}),
    S(431738, '"texte : "+(s||"?")', 'dzT("montage.autoclips.texte",{t:s||"?"})',
      {'montage.autoclips.texte': ('texte : {t}', 'text: {t}')}),
    L(432006, 'montage.autoclips.ia_mot', 'IA', 'AI'),
    L(432011, 'montage.autoclips.heuristique', 'heuristique', 'heuristic'),
]
