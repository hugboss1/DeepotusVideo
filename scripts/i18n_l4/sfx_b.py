"""t144 — sfx_b : couche frontend/patches/sfxstudio.js, lignes 852 à la fin de la base ecf945e4.

Couvre : la fin de l'état vide du tiroir Sons (emptyState), la carte d'un son généré (genCard), le panneau Générer
(genPanel : prompt, durée, variations, fidélité, coût estimé ElevenLabs, résultats, historique), la tête, les onglets,
les filtres (recherche, recherche par description, tri, origine, pré-écoute au survol) et la barre de raccourcis du
tiroir Sons (SvxDrawer) ; le rack d'effets par clip (SvxRack : notes, interrupteurs de module, presets, audition live
et rendue) ; la métrologie maître (SvxMeter : barre RMS/pic, LED de saturation, détails LUFS).

Gardés : les valeurs que le code compare ou passe à Web Audio (« highpass », « bandpass » = BiquadFilterNode.type ;
« red », « amber » = data-z de la barre, lu par le CSS) ; les mesures identiques dans les deux langues (« RMS »,
« LUFS », « dBFS », « dBTP », « TP », « LRA », « auto », « live »). Les valeurs d'options (value:"recent", o[0] de
l'origine, td[0] des onglets) ne sont pas des littéraux d'affichage et ne sont pas touchées ; seuls leurs libellés
le sont. Les touches du pied (« Espace », « Entrée ») ont une autre traduction ailleurs (Photolab : espace de
travail, entrée de courbe) : contexte=True.
Phrases recomposées : « Arrêter/Écouter {nom} », « Télécharger « {nom} » », coûts en crédits, « Favoris ({n}) »,
« Chercher par DESCRIPTION ({n} sons indexés) », note de preset, aria « {module} — {param} (valeur) »,
« Activer/Désactiver — {module} », compte d'effets actifs et inconnus (pluriel .un / .plusieurs), « Appliquer le
preset », note « au rendu uniquement », infobulle RMS/pic, « PIC {v} ».
"""
from outils import L, S, X

CIBLE = "sfxstudio"

FRAGMENTS = {}

ENTREES = [
    # SvxDrawer › emptyState : message selon l'onglet, boutons
    L(49108, 'sfx.vide.aucun_sfx', "Aucun effet sonore pour l'instant.", 'No sound effects yet.'),
    L(49153, 'sfx.vide.bibliotheque_vide', 'Votre bibliothèque de sons est vide.', 'Your sound library is empty.'),
    L(49514, 'sfx.commun.importer_son', 'Importer un son', 'Upload sound'),
    L(49642, 'sfx.vide.generer_sfx', 'Générer un SFX', 'Generate an SFX'),
    L(49730, 'sfx.vide.deposer', 'Vous pouvez aussi déposer des fichiers audio ici.', 'You can also drop audio files here.'),

    # SvxDrawer › genCard : carte d'un son généré
    L(50258, 'sfx.carte.aide', 'Clic / Espace : préécoute · glisser vers une piste A', 'Click / Space: preview · drag onto an A track'),
    S(50510, '(playing?"Arrêter ":"Écouter ")+it.name',
      '(playing?dzT("sfx.carte.arreter_nom",{nom:it.name}):dzT("sfx.carte.ecouter_nom",{nom:it.name}))',
      {'sfx.carte.arreter_nom': ('Arrêter {nom}', 'Stop {nom}'),
       'sfx.carte.ecouter_nom': ('Écouter {nom}', 'Play {nom}')}),
    L(51179, 'sfx.carte.nouveau_nom', 'Nouveau nom', 'New name'),
    L(51682, 'sfx.carte.inserer_aide', 'Insérer au playhead — piste A3 (SFX)', 'Insert at the playhead — track A3 (SFX)'),
    L(51819, 'sfx.commun.inserer', 'Insérer', 'Insert'),
    S(51945, '"Télécharger « "+it.name+" »"',
      'dzT("sfx.carte.telecharger_nom",{nom:it.name})',
      {'sfx.carte.telecharger_nom': ('Télécharger « {nom} »', 'Download “{nom}”')}),
    L(52049, 'sfx.commun.telecharger', 'Télécharger', 'Download'),
    L(52191, 'sfx.commun.valider', 'Valider', 'Confirm'),
    L(52406, 'sfx.commun.renommer', 'Renommer', 'Rename'),
    L(52574, 'sfx.commun.supprimer', 'Supprimer', 'Delete'),

    # SvxDrawer › genPanel : générer un SFX (ElevenLabs)
    L(52769, 'sfx.gen.decrire', 'Décrire le son', 'Describe the sound'),
    L(52881, 'sfx.gen.exemple', '« verre brisé sur du carrelage », « vent dans une grotte »…', '“glass shattering on tiles”, “wind in a cave”…'),
    L(52980, 'sfx.gen.description_aria', 'Description du son à générer', 'Description of the sound to generate'),
    L(53503, 'sfx.commun.duree', 'Durée', 'Duration'),
    L(53607, 'sfx.gen.auto_aide', 'ElevenLabs choisit la durée la plus naturelle', 'ElevenLabs picks the most natural duration'),
    X(53713, 'identique dans les deux langues (« auto »)'),
    L(53859, 'sfx.gen.duree_secondes', 'Durée (secondes)', 'Duration (seconds)'),
    L(54140, 'sfx.gen.duree_precise', 'Durée précise (secondes)', 'Exact duration (seconds)'),
    L(54477, 'sfx.gen.variations', 'Variations', 'Variations'),
    L(54579, 'sfx.gen.nombre_variations', 'Nombre de variations', 'Number of variations'),
    L(54960, 'sfx.gen.fidelite', 'Fidélité', 'Fidelity'),
    L(55092, 'sfx.gen.fidelite_aria', 'Fidélité au texte (prompt influence)', 'Fidelity to the text (prompt influence)'),
    L(55149, 'sfx.gen.fidelite_aide', 'Haut : colle au texte · bas : plus créatif (30 % par défaut)', 'High: sticks to the text · low: more creative (30 % by default)'),
    L(55486, 'sfx.gen.estimation_aide', 'Estimation avant génération — ~40 crédits ElevenLabs par seconde et par variation', 'Estimate before generating — ~40 ElevenLabs credits per second and per variation'),
    S(55602, '"≈ 40 crédits/s · total selon durée générée":"≈ "+cost+" crédits"',
      'svxSfxCout(gDur,gVar,1):svxSfxCout(gDur,gVar,0)      ',   # t187 : le prix du modèle choisi (fin de couche)
      {'sfx.gen.cout_auto': ('≈ 40 crédits/s · total selon durée générée', '≈ 40 credits/s · total depends on generated duration'),
       'sfx.gen.cout': ('≈ {n} crédits', '≈ {n} credits')}),
    L(55965, 'sfx.gen.en_cours', 'Génération… (~10 s)', 'Generating… (~10 s)'),
    L(55990, 'sfx.commun.generer', 'Générer', 'Generate'),
    L(56149, 'sfx.gen.resultats', 'Résultats', 'Results'),
    L(56252, 'sfx.gen.cout_reel_aide', 'Coût réel estimé de la dernière génération — 40 crédits × durée générée × variations', 'Estimated actual cost of the last generation — 40 credits × generated duration × variations'),
    S(56362, '"≈ "+gCost+" crédits utilisés"',
      'dzT("sfx.gen.cout_utilise",{n:gCost})',
      {'sfx.gen.cout_utilise': ('≈ {n} crédits utilisés', '≈ {n} credits used')}),
    L(56599, 'sfx.gen.recentes', 'Générations récentes', 'Recent generations'),
    L(56780, 'sfx.gen.reprendre', 'Reprendre ce prompt', 'Reuse this prompt'),

    # SvxDrawer : tête du tiroir
    L(57379, 'sfx.tiroir.aria', 'Tiroir Sons', 'Sounds drawer'),
    L(57973, 'sfx.tiroir.titre', 'Sons', 'Sounds'),
    L(58120, 'sfx.tiroir.rafraichir_aide', 'Rafraîchir la bibliothèque', 'Refresh the library'),
    L(58172, 'sfx.commun.rafraichir', 'Rafraîchir', 'Refresh'),
    L(58309, 'sfx.tiroir.importer_aide', 'Importer des fichiers audio (mp3, wav, m4a, ogg, flac…)', 'Import audio files (mp3, wav, m4a, ogg, flac…)'),
    L(58390, 'sfx.commun.importer_son', 'Importer un son', 'Upload sound'),
    L(58650, 'sfx.tiroir.fermer_aide', 'Fermer (B)', 'Close (B)'),
    L(58686, 'sfx.tiroir.fermer_aria', 'Fermer le tiroir Sons', 'Close the Sounds drawer'),

    # SvxDrawer : onglets
    L(59060, 'sfx.commun.favoris', 'Favoris', 'Favorites'),
    S(59116, '"Favoris ("+counts.fav+")"',
      'dzT("sfx.tiroir.favoris_n",{n:counts.fav})',
      {'sfx.tiroir.favoris_n': ('Favoris ({n})', 'Favorites ({n})')}),
    L(59583, 'sfx.commun.generer', 'Générer', 'Generate'),

    # SvxDrawer : filtres (recherche, recherche par description, tri, origine, pré-écoute)
    L(59840, 'sfx.filtres.decrire_placeholder', 'Décrire le son cherché, puis Entrée — « une porte lourde qui grince »', 'Describe the sound you want, then Enter — “a heavy creaking door”'),
    L(59912, 'sfx.filtres.rechercher_placeholder', 'Rechercher (nom, prompt)…', 'Search (name, prompt)…'),
    L(59965, 'sfx.filtres.rechercher_aria', 'Rechercher un son', 'Search for a sound'),
    S(60380, '"Chercher par DESCRIPTION ("+(ssStatus.indexed||0)+" sons indexés)"',
      'dzT("sfx.filtres.semantique_pret",{n:ssStatus.indexed||0})',
      {'sfx.filtres.semantique_pret': ('Chercher par DESCRIPTION ({n} sons indexés)', 'Search by DESCRIPTION ({n} sounds indexed)')}),
    L(60488, 'sfx.filtres.semantique_indispo', 'recherche par description indisponible', 'search by description unavailable'),
    L(60577, 'sfx.filtres.semantique_aria', 'Recherche par description', 'Search by description'),
    L(60859, 'sfx.filtres.indexer_aide', 'Indexer les sons nouveaux ou modifiés (service local, gratuit)', 'Index new or changed sounds (local service, free)'),
    L(60995, 'sfx.filtres.indexer', 'indexer', 'index'),
    L(61082, 'sfx.filtres.reindexer_aide', 'Tout réindexer depuis zéro — après un changement de modèle du service', 'Reindex everything from scratch — after the service model changes'),
    L(61206, 'sfx.filtres.reindexer', 'tout réindexer', 'reindex all'),
    L(61312, 'sfx.filtres.trier_aria', 'Trier la bibliothèque', 'Sort the library'),
    L(61342, 'sfx.filtres.tri', 'Tri', 'Sort'),
    L(61464, 'sfx.filtres.tri_recents', 'Récents', 'Recent'),
    L(61523, 'sfx.filtres.tri_nom', 'Nom', 'Name'),
    L(61580, 'sfx.commun.duree', 'Durée', 'Duration'),
    L(61637, 'sfx.filtres.tri_favoris', "Favoris d'abord", 'Favorites first'),
    L(61707, 'sfx.filtres.tri_anciens', 'Plus anciens', 'Oldest'),
    L(61794, 'sfx.filtres.origine', 'Origine', 'Source'),
    L(61832, 'sfx.filtres.origine_tous', 'Tous', 'All'),
    L(61849, 'sfx.filtres.origine_miens', 'Mes sons', 'My sounds'),
    L(61874, 'sfx.filtres.origine_catalogue', 'Catalogue', 'Catalog'),
    L(62084, 'sfx.filtres.catalogue_aide', 'Les sons du catalogue de démarrage (CC0)', 'Sounds from the starter catalog (CC0)'),
    L(62142, 'sfx.filtres.miens_aide', 'Vos sons : générés, importés, dérivés', 'Your sounds: generated, imported, derived'),
    L(62384, 'sfx.filtres.survol_actif', 'Pré-écoute au survol : active (350 ms)', 'Preview on hover: on (350 ms)'),
    L(62425, 'sfx.filtres.survol_coupe', 'Pré-écoute au survol : coupée', 'Preview on hover: off'),
    L(62505, 'sfx.filtres.survol_aria', 'Pré-écoute au survol', 'Preview on hover'),

    # SvxDrawer : barre des raccourcis (touche + action)
    L(63017, 'sfx.touches.espace', 'Espace', 'Space', contexte=True),
    L(63028, 'sfx.touches.preecoute', ' préécoute', ' preview'),
    L(63106, 'sfx.touches.naviguer', ' naviguer', ' navigate'),
    L(63176, 'sfx.touches.entree', 'Entrée', 'Enter', contexte=True),
    L(63187, 'sfx.touches.inserer', ' insérer', ' insert'),
    L(63262, 'sfx.touches.favori', ' favori', ' favorite'),
    L(63330, 'sfx.touches.suppr', 'Suppr', 'Del', contexte=True),
    L(63340, 'sfx.touches.supprimer', ' supprimer', ' delete'),
    L(63417, 'sfx.touches.recherche', ' recherche', ' search'),
    L(63512, 'sfx.touches.fermer', ' fermer', ' close'),

    # SvxRack : notes (fireNote)
    L(66539, 'sfx.rack.chaine_reinitialisee', "Chaîne d'effets réinitialisée.", 'Effects chain reset.'),
    S(66908, '"Preset « "+p.label+" » appliqué — la chaîne précédente est remplacée (annulable)."',
      'dzT("sfx.rack.preset_applique",{preset:p.label})',
      {'sfx.rack.preset_applique': ('Preset « {preset} » appliqué — la chaîne précédente est remplacée (annulable).', 'Preset “{preset}” applied — the previous chain is replaced (undoable).')}),
    X(68189, 'BiquadFilterNode.type (Web Audio), comparé à P.flt.type'),
    X(68216, 'BiquadFilterNode.type (Web Audio), comparé à P.flt.type'),
    L(70263, 'sfx.commun.decodage_impossible', 'Décodage impossible (codec non lu par le navigateur).', 'Cannot decode (codec not supported by the browser).'),
    L(73586, 'sfx.rack.sans_source', 'Pas de source audio sur ce clip.', 'No audio source on this clip.'),
    L(73663, 'sfx.rack.sans_webaudio', 'Web Audio indisponible dans ce navigateur.', 'Web Audio is unavailable in this browser.'),
    L(73876, 'sfx.commun.decodage_impossible', 'Décodage impossible (codec non lu par le navigateur).', 'Cannot decode (codec not supported by the browser).'),

    # SvxRack › paramRow : réglages d'un module
    L(75102, 'sfx.rack.mode', 'Mode', 'Mode'),
    L(75186, 'sfx.rack.mode_filtre', 'Mode du filtre', 'Filter mode'),
    S(76426, 'def.label+" — "+pd.label+" (valeur)"',
      'dzT("sfx.rack.param_valeur",{module:def.label,param:pd.label})',
      {'sfx.rack.param_valeur': ('{module} — {param} (valeur)', '{module} — {param} (value)')}),

    # SvxRack › moduleRow : interrupteur, étiquette live / rendu
    S(77644, '(on?"Désactiver":"Activer")+" — "+def.label',
      '(on?dzT("sfx.rack.desactiver_aide",{module:def.label}):dzT("sfx.rack.activer_aide",{module:def.label}))',
      {'sfx.rack.desactiver_aide': ('Désactiver — {module}', 'Disable — {module}'),
       'sfx.rack.activer_aide': ('Activer — {module}', 'Enable — {module}')}),
    S(77713, '(on?"Désactiver ":"Activer ")+def.label',
      '(on?dzT("sfx.rack.desactiver_module",{module:def.label}):dzT("sfx.rack.activer_module",{module:def.label}))',
      {'sfx.rack.desactiver_module': ('Désactiver {module}', 'Disable {module}'),
       'sfx.rack.activer_module': ('Activer {module}', 'Enable {module}')}),
    L(78052, 'sfx.rack.live_aide', "Audible dans l'audition live Web Audio", 'Audible in the live Web Audio preview'),
    L(78107, 'sfx.rack.rendu_aide', 'Audible via « Écouter (rendu) » (ffmpeg) uniquement', 'Audible only via “Play (render)” (ffmpeg)'),
    X(78191, 'identique dans les deux langues (« live »)'),
    L(78198, 'sfx.rack.rendu', 'rendu', 'render'),

    # SvxRack : tête (compte, inconnus, réinitialiser) et presets
    S(78766, 'activeCount+" actif"+(activeCount>1?"s":"")',
      '(activeCount>1?dzT("sfx.rack.actifs.plusieurs",{n:activeCount}):dzT("sfx.rack.actifs.un",{n:activeCount}))',
      {'sfx.rack.actifs.un': ('{n} actif', '{n} active'),
       'sfx.rack.actifs.plusieurs': ('{n} actifs', '{n} active')}),
    L(78810, 'sfx.rack.aucun_effet', 'aucun effet', 'no effect'),
    L(78914, 'sfx.rack.inconnus_aide', "Effets d'une version plus récente — conservés tels quels dans le rendu", 'Effects from a newer version — kept as is in the render'),
    S(79006, '"+"+norm.unknown.length+" inconnu"+(norm.unknown.length>1?"s":"")',
      '(norm.unknown.length>1?dzT("sfx.rack.inconnus.plusieurs",{n:norm.unknown.length}):dzT("sfx.rack.inconnus.un",{n:norm.unknown.length}))',
      {'sfx.rack.inconnus.un': ('+{n} inconnu', '+{n} unknown'),
       'sfx.rack.inconnus.plusieurs': ('+{n} inconnus', '+{n} unknown')}),
    L(79197, 'sfx.rack.reinitialiser_aide', 'Retirer tous les effets du clip (annulable)', 'Remove all effects from the clip (undoable)'),
    L(79279, 'sfx.commun.reinitialiser', 'Réinitialiser', 'Reset'),
    S(79591, '"Appliquer le preset « "+p.label+" » (remplace la chaîne)"',
      'dzT("sfx.rack.appliquer_preset",{preset:p.label})',
      {'sfx.rack.appliquer_preset': ('Appliquer le preset « {preset} » (remplace la chaîne)', 'Apply the “{preset}” preset (replaces the chain)')}),
    L(79781, 'sfx.rack.preset_modifie_aide', "Preset modifié depuis l'application", 'Preset changed since it was applied'),
    L(79840, 'sfx.rack.modifie', 'modifié', 'modified'),

    # SvxRack : audition live / rendue
    L(80024, 'sfx.rack.arreter_audition', "Arrêter l'audition", 'Stop the preview'),
    L(80057, 'sfx.rack.ecouter_aide', 'Écouter le segment du clip en boucle, effets appliqués en direct (Web Audio) — fondus non simulés', 'Loop the clip segment with effects applied live (Web Audio) — fades not simulated'),
    L(80312, 'sfx.commun.chargement', 'chargement…', 'loading…'),
    L(80349, 'sfx.rack.stop', '▮▮ Stop', '▮▮ Stop'),
    L(80359, 'sfx.rack.ecouter', '▶ Écouter', '▶ Play'),
    L(80518, 'sfx.rack.rendu_ecoute_aide', 'Rendu ffmpeg exact du segment avec la chaîne complète (débruiteur, dé-esseur, normalisation compris)', 'Exact ffmpeg render of the segment with the full chain (denoiser, de-esser, normalization included)'),
    L(80776, 'sfx.rack.rendu_en_cours', 'rendu…', 'rendering…'),
    L(80800, 'sfx.rack.ecouter_rendu', 'Écouter (rendu)', 'Play (render)'),
    S(80981, 'nonLiveOn.join(" · ")+" : au rendu uniquement — passez par « Écouter (rendu) »."',
      'dzT("sfx.rack.au_rendu",{liste:nonLiveOn.join(" · ")})',
      {'sfx.rack.au_rendu': ('{liste} : au rendu uniquement — passez par « Écouter (rendu) ».', '{liste}: render only — use “Play (render)”.')}),

    # SvxMeter : barre, LED de saturation, chiffres
    L(83466, 'sfx.metre.cible_aide', 'Cible réseaux sociaux : −14 LUFS (mesurée via « Mesurer le mix »)', 'Social media target: −14 LUFS (measured via “Measure the mix”)'),
    X(82715, 'data-z de la barre, lu par le CSS (zone de couleur)'),
    X(82729, 'data-z de la barre, lu par le CSS (zone de couleur)'),
    L(83860, 'sfx.metre.aria', 'Niveau de sortie maître', 'Master output level'),
    L(84103, 'sfx.metre.saturation_aide', 'Saturation détectée (≥ 0 dBFS) — cliquer pour réinitialiser', 'Clipping detected (≥ 0 dBFS) — click to reset'),
    L(84175, 'sfx.metre.aucune_saturation', 'Aucune saturation', 'No clipping'),
    L(84224, 'sfx.metre.saturation_aria', 'Saturation détectée — réinitialiser', 'Clipping detected — reset'),
    L(84262, 'sfx.metre.aucune_saturation', 'Aucune saturation', 'No clipping'),
    S(84416, '"RMS "+svxDb1(rdb)+" · pic "+svxDb1(hold)+" dBFS — clic : détails"',
      'dzT("sfx.metre.barre_aide",{rms:svxDb1(rdb),pic:svxDb1(hold)})',
      {'sfx.metre.barre_aide': ('RMS {rms} · pic {pic} dBFS — clic : détails', 'RMS {rms} · peak {pic} dBFS — click: details')}),
    L(84493, 'sfx.metre.repos_aide', 'Au repos — lancez la lecture pour le niveau · clic : détails', 'Idle — start playback to see the level · click: details'),
    X(84764, 'identique dans les deux langues (« RMS »)'),
    X(84783, 'identique dans les deux langues (« RMS — »)'),
    S(84863, '"PIC "+svxDb1(hold)',
      'dzT("sfx.metre.pic",{v:svxDb1(hold)})',
      {'sfx.metre.pic': ('PIC {v}', 'PEAK {v}')}),
    L(84883, 'sfx.metre.pic_vide', 'PIC —', 'PEAK —'),
    L(84983, 'sfx.metre.momentanee_aide', 'Loudness momentanée (fenêtre 400 ms, pondération K)', 'Momentary loudness (400 ms window, K-weighting)'),
    X(85075, 'unité identique dans les deux langues (LUFS)'),

    # SvxMeter : panneau des détails
    L(85174, 'sfx.metre.details_aria', 'Détails du niveau de sortie', 'Output level details'),
    L(85306, 'sfx.metre.sortie_maitre', 'Sortie maître', 'Master output'),
    L(85384, 'sfx.metre.fermer_aide', 'Fermer (Échap)', 'Close (Esc)'),
    L(85426, 'sfx.metre.fermer_aria', 'Fermer les détails', 'Close details'),
    X(85872, 'identique dans les deux langues (« RMS »)'),
    X(85891, 'unité identique dans les deux langues (dBFS)'),
    L(85899, 'sfx.metre.rms_repos', 'RMS — (au repos)', 'RMS — (idle)'),
    S(85961, '"PIC "+svxDb1(hold)',
      'dzT("sfx.metre.pic",{v:svxDb1(hold)})',
      {'sfx.metre.pic': ('PIC {v}', 'PEAK {v}')}),
    X(85981, 'unité identique dans les deux langues (dBFS)'),
    L(85989, 'sfx.metre.pic_vide', 'PIC —', 'PEAK —'),
    L(86091, 'sfx.metre.loudness_mix', 'Loudness du mix', 'Mix loudness'),
    L(86196, 'sfx.metre.momentanee_reel_aide', 'Loudness momentanée — temps réel pendant la lecture (fenêtre 400 ms, pondération K)', 'Momentary loudness — real time during playback (400 ms window, K-weighting)'),
    L(86364, 'sfx.metre.momentane', 'momentané', 'momentary'),
    X(86427, 'unité identique dans les deux langues (LUFS)'),
    L(86549, 'sfx.metre.integree', 'Loudness intégrée', 'Integrated loudness'),
    X(86606, 'unité identique dans les deux langues (LUFS)'),
    L(86648, 'sfx.metre.vrai_pic', 'Vrai pic', 'True peak'),
    X(86668, 'sigle identique dans les deux langues (TP = true peak)'),
    X(86698, 'unité identique dans les deux langues (dBTP)'),
    L(86740, 'sfx.metre.plage', 'Plage de loudness', 'Loudness range'),
    X(86769, 'sigle identique dans les deux langues (LRA)'),
    L(86914, 'sfx.metre.ecart_aide', 'Écart à la cible réseaux sociaux (−14 LUFS)', 'Deviation from the social media target (−14 LUFS)'),
    L(86995, 'sfx.metre.vs_cible', ' dB vs cible', ' dB vs target'),
    L(87084, 'sfx.metre.pas_mesure', 'Pas encore mesuré — « Mesurer le mix » analyse le mix audio complet (ebur128, gratuit).', 'Not measured yet — “Measure the mix” analyzes the full audio mix (ebur128, free).'),
    L(87305, 'sfx.metre.cible', 'cible réseaux : −14 LUFS', 'social target: −14 LUFS'),
    L(87637, 'sfx.metre.mesure_en_cours', 'mesure…', 'measuring…'),
    L(87666, 'sfx.metre.mesurer', 'Mesurer le mix', 'Measure the mix'),
    L(87762, 'sfx.metre.fermer_indice', 'Échap ou clic dehors pour fermer', 'Esc or click outside to close'),
    L(87797, 'sfx.metre.figer_indice', 'clic sur la barre : figer le panneau', 'click the bar: pin the panel'),
    # t187 (G5, génération IA enrichie, 12/10/2026) — changement FONCTIONNEL posé APRÈS L4 : le modèle du
    # bruitage (registre sfx_service, natures sfx_texte / sfx_video), son prix lu au devis du serveur, et
    # « Depuis la vidéo » sur le clip sélectionné. Les retouches avant la dernière édition G1 de la couche
    # gardent la LONGUEUR (commentaire ou indentation compensés) ; le code neuf est en fin de couche.
    # Mêmes retouches dans RETOUCHES de scripts/icones/g1_generer.py.
    S(53191, '      r.jsx("div",{className:"svx-gex",children:SVX_EXAMPLES.map(function(ex){',
      '      svxSfxR(gAuto?0:gDur,gVar,props.clip,gPrompt,refresh,fireNote),r.jsx("div",{className:"svx-gex",children:SVX_EXAMPLES.map(function(ex){',
      {}),
    S(57079, '  /* T101 (plan-son-vfx T5) : `inline` = monté dans la page (Bibliothèque → Audio), toujours ouvert, sans « Fermer » */',
      '  /* T101 : `inline` = dans la page, sans « Fermer »  */',
      {}),
    S(87854, '/* ── export contrat ──────────────────────────────────────────────────────── */\r\nwindow.DzSfx={ready:!0,Drawer:SvxDrawer,Rack:SvxRack,Meter:SvxMeter,\r\n  genSfx:svxGenSfx,fxPresets:svxFxPresets};',
      '/* ── t187 (G5, génération IA enrichie) : le MODÈLE du bruitage, texte ET vidéo ──────────\r\n   Le registre des bruitages (backend sfx_service.SFX_MODELS) est servi par GET\r\n   /api/ia/catalogue (natures sfx_texte et sfx_video) : chaque option porte son prix (lu au\r\n   catalogue) et, sans clé, la mention « clé X à ajouter dans Réglages » — elle reste\r\n   CHOISISSABLE (jamais disabled) : la route refuse en 503 avant toute dépense. Le choix est\r\n   commun au tiroir Sons et à la carte SFX de Son & VFX (localStorage dz_sfx_modele et\r\n   dz_sfx_modele_video ; vide = le défaut du serveur : ElevenLabs direct, ou son jumeau via\r\n   fal sans clé ElevenLabs). Le PRIX annoncé est le devis du SERVEUR — POST /api/cost/estimate\r\n   (kind « sfx ») pour une description, POST /api/audio/sfx-video avec devis:true pour un\r\n   clip — le même chiffre que la garde des plafonds, avant ET après le clic. « Depuis la\r\n   vidéo » (clip vidéo sélectionné dans la timeline) : 1er clic = arme, 2e clic = tir.\r\n   Ces fonctions vivent APRÈS la dernière édition G1 de la couche (table dzglyph_paires.json :\r\n   éditions repérées par position) ; un useReducer (et non useState) rafraîchit l\'affichage. */\r\nvar SVX_SFXM={texte:"",video:"",voix:!1,cat:{},prix:{},subs:[],arm:null,busy:!1};\r\nvar SVX_SFXM_LS="dz_sfx_modele",SVX_SFXM_LSV="dz_sfx_modele_video";\r\ntry{SVX_SFXM.texte=localStorage.getItem(SVX_SFXM_LS)||"";SVX_SFXM.video=localStorage.getItem(SVX_SFXM_LSV)||""}catch(_e){}\r\n/* les libellés du catalogue arrivent en français : ceux qui portent un suffixe à traduire passent par dzT */\r\nvar SVX_SFXM_NOMS={"sonilo-video":dzT("son.sfx.libelle.sonilo_video"),\r\n  "mirelo-video":dzT("son.sfx.libelle.mirelo_video"),"kling-v2a":dzT("son.sfx.libelle.kling_v2a")};\r\nfunction svxSfxPing(){SVX_SFXM.subs.slice().forEach(function(f){try{f()}catch(_e){}})}\r\nfunction svxSfxAbonne(t){\r\n  x.useEffect(function(){SVX_SFXM.subs.push(t);\r\n    return function(){var i=SVX_SFXM.subs.indexOf(t);if(i>=0)SVX_SFXM.subs.splice(i,1)}},[])}\r\nfunction svxSfxCat(nat){\r\n  var c=SVX_SFXM.cat[nat];if(c)return c.l;\r\n  SVX_SFXM.cat[nat]={l:null};\r\n  fetch("/api/ia/catalogue?nature="+nat).then(function(res){return res.ok?res.json():null})\r\n    .then(function(d){SVX_SFXM.cat[nat]={l:(d&&d.modeles)||[]};svxSfxPing()})\r\n    .catch(function(){SVX_SFXM.cat[nat]={l:[]};svxSfxPing()});\r\n  return null}\r\nfunction svxSfxMod(nat,id){var l=svxSfxCat(nat)||[];\r\n  for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}\r\n/* le modèle EFFECTIF : le choix mémorisé s\'il est encore servi, sinon le défaut du serveur */\r\nfunction svxSfxEff(nat){\r\n  var l=svxSfxCat(nat)||[],v=nat==="sfx_video"?SVX_SFXM.video:SVX_SFXM.texte;\r\n  if(v&&svxSfxMod(nat,v))return v;\r\n  if(nat==="sfx_video")return l.length?l[0].id:"";\r\n  var d=svxSfxMod(nat,"elevenlabs-direct"),f=svxSfxMod(nat,"elevenlabs-v2-fal");\r\n  return d&&d.dispo===!1&&f&&f.dispo!==!1?f.id:"elevenlabs-direct"}\r\nfunction svxSfxUsd(m){var v=Number(m&&m.usd);\r\n  if(!(v>0)||!isFinite(v))return dzT("ia.prix.a_mesurer");\r\n  return "$"+String(Math.round(v*10000)/10000)+(m.unite==="s"?"/s":m.unite==="video"?" / "+dzT("son.sfx.unite_video"):"")}\r\nfunction svxSfxTexte(m){\r\n  return (SVX_SFXM_NOMS[m.id]||m.label||m.id)+" · "+svxSfxUsd(m)\r\n    +(m.dispo===!1&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}\r\nfunction svxSfxChoisir(nat,v){\r\n  if(nat==="sfx_video")SVX_SFXM.video=v;else SVX_SFXM.texte=v;\r\n  SVX_SFXM.arm=null;\r\n  try{localStorage.setItem(nat==="sfx_video"?SVX_SFXM_LSV:SVX_SFXM_LS,v)}catch(_e){}\r\n  svxSfxPing()}\r\n/* le corps de POST /api/audio/sfx reçoit le modèle CHOISI (rien : le défaut du serveur) */\r\nfunction svxSfxCorps(body,o){\r\n  var m=o&&o.modele!=null?String(o.modele):SVX_SFXM.texte,c=SVX_SFXM.cat.sfx_texte;\r\n  if(m&&(!c||!c.l||svxSfxMod("sfx_texte",m)))body.modele=m}\r\n/* le devis du serveur, mis en cache par corps : undefined pendant la lecture, null si refusé */\r\nfunction svxSfxDevis(url,body){\r\n  var k=url+" "+JSON.stringify(body),e=SVX_SFXM.prix[k];\r\n  if(e)return e.usd;\r\n  SVX_SFXM.prix[k]={usd:void 0};\r\n  fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})\r\n    .then(function(res){return res.ok?res.json():null})\r\n    .then(function(d){var u=d&&(typeof d.total_usd==="number"?d.total_usd:typeof d.usd==="number"?d.usd:null);\r\n      SVX_SFXM.prix[k]={usd:u==null?null:u};svxSfxPing()})\r\n    .catch(function(){SVX_SFXM.prix[k]={usd:null};svxSfxPing()});\r\n  return void 0}\r\nfunction svxSfxPrixTxt(usd){\r\n  return usd===void 0?dzT("sfx.action.prix_attente"):usd==null?"—"\r\n    :usd>0?"~$"+usd.toFixed(usd<0.1?3:2):dzT("ia.prix.a_mesurer")}\r\n/* l\'ancienne estimation en crédits ne parle que pour ElevenLabs direct ; un modèle fal a son prix à côté du sélecteur */\r\nfunction svxSfxCout(dur,n,auto){\r\n  if(svxSfxEff("sfx_texte")!=="elevenlabs-direct")return "";\r\n  return auto?dzT("sfx.gen.cout_auto"):dzT("sfx.gen.cout",{n:Math.round(40*dur)*n})}\r\n/* le sélecteur sfx_texte + SON prix (devis du serveur pour cette durée et ces variations) */\r\nfunction SvxSfxChoix(props){\r\n  var t=x.useReducer(function(n){return n+1},0)[1];\r\n  svxSfxAbonne(t);\r\n  var l=svxSfxCat("sfx_texte"),v=svxSfxEff("sfx_texte"),d=Number(props.dur)>0?Number(props.dur):null;\r\n  var usd=l?svxSfxDevis("/api/cost/estimate",{kind:"sfx",modele:v,secondes:d,\r\n    echantillons:Math.max(1,Math.min(4,Math.round(Number(props.n)||1)))}):void 0;\r\n  return r.jsxs("span",{className:"svx-sfxm","data-dzsfxm":"texte",children:[\r\n    r.jsx("select",{className:"svx-select svx-sfxmsel",value:v,\r\n      "aria-label":dzT("son.sfx.modele"),title:dzT("son.sfx.modele"),\r\n      onChange:function(e){svxSfxChoisir("sfx_texte",e.target.value)},\r\n      children:(l||[]).map(function(m){return r.jsx("option",{value:m.id,children:svxSfxTexte(m)},m.id)})}),\r\n    r.jsx("span",{className:"svm-genprice svx-sfxmprix",title:dzT("son.sfx.prix_modele"),\r\n      children:svxSfxPrixTxt(usd)})]})}\r\n/* « Depuis la vidéo » : le clip VIDÉO sélectionné dans la timeline (job rendu) part à un modèle sfx_video */\r\nfunction svxSfxClipVideo(c){return !!(c&&c.src&&c.src.job_id&&!/^a/.test(String(c.tr||"")))}\r\nfunction SvxSfxVideo(props){\r\n  var t=x.useReducer(function(n){return n+1},0)[1];\r\n  svxSfxAbonne(t);\r\n  var c=props.clip,l=svxSfxCat("sfx_video"),v=svxSfxEff("sfx_video"),m=svxSfxMod("sfx_video",v);\r\n  var corps={clip_id:String(c.src.job_id),modele:v};\r\n  if(m&&m.voix)corps.garder_voix=!!SVX_SFXM.voix;\r\n  var usd=l&&v?svxSfxDevis("/api/audio/sfx-video",Object.assign({devis:!0},corps)):void 0;\r\n  var p=String(props.prompt||"").trim(),cle=JSON.stringify(corps)+"|"+p,armed=SVX_SFXM.arm===cle;\r\n  function go(){\r\n    if(SVX_SFXM.busy||!v)return;\r\n    if(m&&m.prompt&&!p){props.note(dzT("son.sfx.decrire_video"));return}\r\n    if(!armed){SVX_SFXM.arm=cle;t();return}\r\n    SVX_SFXM.arm=null;SVX_SFXM.busy=!0;t();\r\n    fetch("/api/audio/sfx-video",{method:"POST",headers:{"Content-Type":"application/json"},\r\n      body:JSON.stringify(Object.assign({prompt:p},corps))})\r\n      .then(function(res){return res.json().catch(function(){return {}})\r\n        .then(function(d){if(!res.ok)throw new Error(d.detail&&d.detail.message||d.detail||dzT("sfx.action.echec_code",{code:res.status}));return d})})\r\n      .then(function(d){SVX_SFXM.busy=!1;t();if(props.refresh)props.refresh();\r\n        var it=(d.items||[])[0];\r\n        props.note(dzT("son.sfx.video_fait",{nom:it?it.filename:"—",prix:svxSfxPrixTxt(typeof d.usd==="number"?d.usd:null)})\r\n          +((d.videos||[]).length?" "+dzT("son.sfx.video_sonorisee"):""))})\r\n      .catch(function(e){SVX_SFXM.busy=!1;t();props.note(String(e&&e.message||e))})}\r\n  return r.jsxs("div",{className:"svx-sfxv","data-dzsfxv":"1",children:[\r\n    r.jsx(SvmLabel,{children:dzT("son.sfx.depuis_video")}),\r\n    r.jsx("div",{className:"svx-note",children:dzT("son.sfx.video_aide",{clip:c.label||c.id||""})}),\r\n    r.jsxs("div",{className:"svx-grow",children:[\r\n      r.jsx("select",{className:"svx-select svx-sfxmsel",value:v,"data-dzsfxm":"video",\r\n        "aria-label":dzT("son.sfx.modele"),title:dzT("son.sfx.modele"),\r\n        onChange:function(e){svxSfxChoisir("sfx_video",e.target.value)},\r\n        children:(l||[]).map(function(o){return r.jsx("option",{value:o.id,children:svxSfxTexte(o)},o.id)})}),\r\n      m&&m.voix?r.jsxs("label",{className:"svx-sfxvoix",children:[\r\n        r.jsx("input",{type:"checkbox",checked:!!SVX_SFXM.voix,"data-dzsfxvoix":"1",\r\n          onChange:function(e){SVX_SFXM.voix=!!e.target.checked;SVX_SFXM.arm=null;t()}}),\r\n        dzT("son.sfx.garder_voix")]}):null]}),\r\n    r.jsx("button",{className:"svm-goldbtn svx-gold"+(armed?" svx-armed":""),"data-dzsfxvgo":"1",\r\n      "data-busy":SVX_SFXM.busy?"":void 0,disabled:!!SVX_SFXM.busy,\r\n      title:armed?dzT("sfx.action.armee",{prix:svxSfxPrixTxt(usd)}):dzT("son.sfx.prix_modele"),\r\n      onClick:go,children:SVX_SFXM.busy?dzT("sfx.gen.en_cours")\r\n        :armed?svxSfxPrixTxt(usd)+" — "+dzT("son.sfx.confirmer")\r\n        :dzT("son.sfx.depuis_video")+" · "+svxSfxPrixTxt(usd)})]})}\r\n/* la rangée « Modèle » de l\'onglet Générer du tiroir, puis le bruitage du clip vidéo sélectionné (Montage) ;\r\n   `clip` undefined = tiroir hors Montage (Bibliothèque) : rien ; null ou non vidéo : l\'indication */\r\nfunction svxSfxR(dur,n,clip,prompt,refresh,note){\r\n  return r.jsxs(r.Fragment,{children:[\r\n    r.jsxs("div",{className:"svx-grow svx-sfxmrow",children:[\r\n      r.jsx("span",{className:"svx-glabel",children:dzT("son.sfx.modele")}),\r\n      r.jsx(SvxSfxChoix,{dur:dur,n:n})]}),\r\n    clip===void 0?null:svxSfxClipVideo(clip)\r\n      ?r.jsx(SvxSfxVideo,{clip:clip,prompt:prompt,refresh:refresh,note:note})\r\n      :r.jsx("div",{className:"svx-note svx-sfxvnone",children:dzT("son.sfx.video_sans_clip")})]})}\r\n\r\n/* ── export contrat ──────────────────────────────────────────────────────── */\r\nwindow.DzSfx={ready:!0,Drawer:SvxDrawer,Rack:SvxRack,Meter:SvxMeter,\r\n  genSfx:svxGenSfx,fxPresets:svxFxPresets,Choix:SvxSfxChoix};',
      {'son.sfx.modele': ('Modèle', 'Model'), 'son.sfx.depuis_video': ('Depuis la vidéo', 'From the video'), 'son.sfx.garder_voix': ('Garder la voix', 'Keep the voice'), 'son.sfx.prix_modele': ('Prix du modèle choisi — devis du serveur, le même que la garde des plafonds', 'Price of the chosen model — server estimate, the same one the spending caps check'), 'son.sfx.unite_video': ('vidéo', 'video'), 'son.sfx.libelle.sonilo_video': ('Sonilo 1.1 (vidéo)', 'Sonilo 1.1 (video)'), 'son.sfx.libelle.mirelo_video': ('Mirelo SFX 1.6 (vidéo sonorisée)', 'Mirelo SFX 1.6 (video with sound)'), 'son.sfx.libelle.kling_v2a': ('Kling vidéo → son', 'Kling video → sound'), 'son.sfx.confirmer': ('cliquer encore pour lancer', 'click again to run'), 'son.sfx.decrire_video': ("Décrivez d'abord le son voulu : ce modèle l'exige.", 'Describe the sound first: this model requires it.'), 'son.sfx.video_fait': ('Bruitage ajouté à la Bibliothèque : {nom} ({prix})', 'Sound effect added to the Library: {nom} ({prix})'), 'son.sfx.video_sonorisee': ('La vidéo sonorisée est dans la Bibliothèque (Rendus).', 'The video with sound is in the Library (Renders).'), 'son.sfx.video_aide': ('Bruiter le clip vidéo sélectionné : {clip}', 'Add sound effects to the selected video clip: {clip}'), 'son.sfx.video_sans_clip': ('Sélectionnez un clip vidéo dans la timeline pour le bruiter.', 'Select a video clip on the timeline to add sound effects to it.')}),
]
