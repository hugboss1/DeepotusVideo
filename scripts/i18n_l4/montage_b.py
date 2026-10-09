"""t144 — montage_b : écran Montage (DzMontage, couche frontend/patches/son-vfx-montage.js), lignes 4232–5180 de la
base. Couvre : la fin de l'inspecteur de sous-titre, le sélecteur d'assets (openPicker, ovPicker : titre, mode
remplacement, notes de pose, Images / Rendus vidéo), toutes les notes d'addAsset (remplacement refusé, piste
verrouillée, piste absente, timeline allongée, mode d'édition appliqué, vitesse), l'insertion depuis le tiroir Sons,
la pose d'effets du rack VFX (clic, dépôt sur la bande, sélecteur historique), les notes de dépôt, le rendu
(launchRender, suivi du job, popover de confirmation Preview 480p / Rendre, file locale), le popover « Plans trop
longs / jump cuts », l'inspecteur Overlay (position, alignement 3×3, échelle, rotation, opacité, coins, ombre,
trajectoire), les fondus du clip d'ajustement et la section « Effets sur ce clip ».

Gardés : le sélecteur CSS « [data-nbid=" » (querySelector), les valeurs CSS « 1 1 auto » (flex), l'URL
« url('/api/images/ » (style backgroundImage), « Overlay », « Rotation » et « · rotation » (identiques dans les deux
langues). Pas touchés non plus (hors contrôle, ce sont des valeurs) : kind "preview"/"final", "audio"/"video"
comparés, et le mot du genre de piste `rkd` (« audio », « video », « title ») montré tel quel dans la note de
remplacement refusé. Le mot « vidéo » de `dzMot` n'est lu que par des notes affichées : traduit.
Les phrases coupées en morceaux concaténés sur plusieurs lignes sont recomposées en une seule clé (S) dont le code
`apres` garde AUTANT de fins de ligne que le code `avant` (le contrôle des restes attribue un littéral à son groupe
par son numéro de ligne : la couche ne doit pas perdre de lignes) ; les
pluriels du popover jump cuts et du compteur de trajectoire passent par deux clés .._un / .._plusieurs."""
from outils import L, S, X

CIBLE = "sonvfx"

FRAGMENTS = {}

_DEMO_EFFETS = ('Effets par clip : disponibles sur les clips réels (Bibliothèque) — la démo reste une maquette.',
                'Per-clip effects: available on real clips (Library) — the demo stays a mock-up.')
_INDISPO = ('Rendu indisponible sur la démo — ouvre un projet réel', 'Render unavailable in the demo — open a real project')
_FERMER_PANNEAU = ('Fermer ce panneau (Échap)', 'Close this panel (Esc)')
_FERMER = ('Fermer', 'Close')
_SON_DEPOT = ('Un son se dépose sur A1, A2 ou A3.', 'A sound goes on A1, A2 or A3.')
_VERROU_AJOUT = ('Piste {piste} verrouillée — déverrouillez-la pour ajouter.', 'Track {piste} locked — unlock it to add.')
_GLISSER = ('{nom} — cliquer ou glisser', '{nom} — click or drag')

ENTREES = [
    # inspecteur de sous-titre (fin)
    L(272168, 'montage.soustitre.titre', 'Sous-titre', 'Subtitle', contexte=True),
    L(272278, 'montage.soustitre.placeholder', 'Texte du sous-titre…', 'Subtitle text…'),
    L(272314, 'montage.soustitre.texte', 'Texte du sous-titre', 'Subtitle text'),
    L(272670, 'montage.soustitre.bornes_aide', 'Début et fin — réglables au clip près dans le tiroir',
      'Start and end — fine-tune them in the drawer'),
    L(272856, 'montage.soustitre.editeur_aide', "Ouvrir l'éditeur de sous-titres (liste, découpe, style, export)",
      'Open the subtitle editor (list, split, style, export)'),
    L(273029, 'montage.soustitre.editeur', 'éditeur', 'editor'),

    # openPicker : ouverture du sélecteur d'assets
    L(273519, 'montage.selecteur.demo', "Ajout d'assets : disponible sur un projet réel — la démo reste une maquette.",
      'Adding assets: available on a real project — the demo stays a mock-up.'),
    S(273664, '"Piste "+trId.toUpperCase()+" verrouillée — déverrouillez-la pour ajouter."',
      'dzT("montage.commun.piste_verrouillee_ajouter",{piste:trId.toUpperCase()})',
      {'montage.commun.piste_verrouillee_ajouter': _VERROU_AJOUT}),
    S(274981, '"Règle d\'extensions vidéo indisponible "+\r\n        "(GET /api/montage/media-rules) — la liste « Rendus vidéo » n\'est "+\r\n        "PAS filtrée : elle peut proposer des planches de sprites ou des "+\r\n        "maillages 3D, que le rendu refusera."',
      'dzT("montage.selecteur.regle_absente"\r\n        \r\n        \r\n        )',
      {'montage.selecteur.regle_absente': (
          "Règle d'extensions vidéo indisponible (GET /api/montage/media-rules) — la liste « Rendus vidéo » n'est PAS "
          "filtrée : elle peut proposer des planches de sprites ou des maillages 3D, que le rendu refusera.",
          'Video extension rule unavailable (GET /api/montage/media-rules) — the “Video renders” list is NOT '
          'filtered: it may offer sprite sheets or 3D meshes, which the render will refuse.')}),

    # addAsset : piste des titres, mode remplacement
    S(278374, '"La piste des titres ne reçoit que des cartons — "+svmKeyLabelNow("title_add")+" en pose un."',
      'dzT("montage.ajout.piste_titres",{touche:svmKeyLabelNow("title_add")})',
      {'montage.ajout.piste_titres': ('La piste des titres ne reçoit que des cartons — {touche} en pose un.',
                                      'The titles track only takes title cards — {touche} adds one.')}),
    S(280803, '"Le plan à remplacer n\'est plus dans la "+\r\n        "timeline : rien n\'a changé, et « "+label+" » n\'a pas été "+\r\n        "posé. Sélectionnez un plan puis « Remplacer la source… », "+\r\n        "ou « Bibliothèque… » pour l\'ajouter comme clip de "+\r\n        "plus."',
      'dzT("montage.remplacer.plan_absent",\r\n        \r\n        {nom:label}\r\n        \r\n        )',
      {'montage.remplacer.plan_absent': (
          "Le plan à remplacer n'est plus dans la timeline : rien n'a changé, et « {nom} » n'a pas été posé. "
          "Sélectionnez un plan puis « Remplacer la source… », ou « Bibliothèque… » pour l'ajouter comme clip de plus.",
          'The clip to replace is no longer in the timeline: nothing changed, and “{nom}” was not placed. '
          'Select a clip then “Replace source…”, or “Library…” to add it as an extra clip.')}),
    S(281216, '"« "+label+" » est "+(akd==="audio"?"un son":\r\n          "une image ou une vidéo")+" : impossible d\'en faire la "+\r\n          "source d\'un plan de la piste "+rk.tr.toUpperCase()+\r\n          " ("+rkd+"). Rien n\'a changé, et rien n\'a été posé — "+\r\n          "choisissez une source du même genre, ou "+\r\n          "« Bibliothèque… » pour l\'ajouter comme clip de "+\r\n          "plus."',
      'dzT("montage.remplacer.genre",{nom:label,\r\n          genre:akd==="audio"?dzT("montage.remplacer.un_son"):\r\n          dzT("montage.remplacer.une_image"),\r\n          piste:rk.tr.toUpperCase(),\r\n          type:rkd\r\n          \r\n          })',
      {'montage.remplacer.genre': (
          "« {nom} » est {genre} : impossible d'en faire la source d'un plan de la piste {piste} ({type}). Rien n'a "
          "changé, et rien n'a été posé — choisissez une source du même genre, ou « Bibliothèque… » pour l'ajouter "
          "comme clip de plus.",
          '“{nom}” is {genre}: it cannot become the source of a clip on track {piste} ({type}). Nothing changed and '
          'nothing was placed — pick a source of the same kind, or “Library…” to add it as an extra clip.'),
       'montage.remplacer.un_son': ('un son', 'a sound'),
       'montage.remplacer.une_image': ('une image ou une vidéo', 'an image or a video')}),
    S(281692, '"Piste "+rk.tr.toUpperCase()+" verrouillée — "+\r\n          "déverrouillez-la pour remplacer la source de ce "+\r\n          "plan."',
      'dzT("montage.remplacer.piste_verrouillee",\r\n          {piste:rk.tr.toUpperCase()}\r\n          )',
      {'montage.remplacer.piste_verrouillee': (
          'Piste {piste} verrouillée — déverrouillez-la pour remplacer la source de ce plan.',
          "Track {piste} locked — unlock it to replace this clip's source.")}),

    # addAsset : piste résolue, refus, note de pose
    L(282532, 'montage.ajout.mot_video', 'vidéo', 'video'),
    S(282677, '"« "+label+" » n\'a pas été posé : ce projet ne "+\r\n      "porte aucune piste "+dzMot+". Ajoutez-en une avec "+\r\n      "« + piste "+dzMot+" » dans la barre de transport, puis "+\r\n      "recommencez."',
      'dzT("montage.ajout.aucune_piste",\r\n      {nom:label,\r\n      mot:dzMot}\r\n      )',
      {'montage.ajout.aucune_piste': (
          "« {nom} » n'a pas été posé : ce projet ne porte aucune piste {mot}. Ajoutez-en une avec « + piste {mot} » "
          "dans la barre de transport, puis recommencez.",
          '“{nom}” was not placed: this project has no {mot} track. Add one with “+ {mot} track” in the transport '
          'bar, then try again.')}),
    S(286913, '"Piste "+String(tr2).toUpperCase()+" verrouillée — "+\r\n          "déverrouillez-la pour ajouter."',
      'dzT("montage.commun.piste_verrouillee_ajouter",\r\n          {piste:String(tr2).toUpperCase()})',
      {'montage.commun.piste_verrouillee_ajouter': _VERROU_AJOUT}),
    S(287023, '"Piste "+String(dzIns.track).toUpperCase()+" verrouillée — "+\r\n          "rien n\'a été posé. Déverrouillez-la, ou choisissez un "+\r\n          "autre mode d\'édition."',
      'dzT("montage.ajout.piste_verrouillee_mode",\r\n          {piste:String(dzIns.track).toUpperCase()}\r\n          )',
      {'montage.ajout.piste_verrouillee_mode': (
          "Piste {piste} verrouillée — rien n'a été posé. Déverrouillez-la, ou choisissez un autre mode d'édition.",
          'Track {piste} locked — nothing was placed. Unlock it, or pick another edit mode.')}),
    S(287822, '" La timeline a été allongée de "+\r\n      svmRuler(Math.round(d))+" à "+svmRuler(Math.round(dzGrew))+\r\n      (dzAv>d?" pour tenir tout ce qu\'elle porte."\r\n        :" : le clip garde sa longueur entière au lieu d\'être rogné sur "+\r\n          "la fin du projet.")+\r\n      " « Annuler » retire le clip, et "+\r\n      "rend aussi la durée d\'avant."',
      'dzT("montage.ajout.allongee",{\r\n      de:svmRuler(Math.round(d)),a:svmRuler(Math.round(dzGrew)),\r\n      raison:dzAv>d?dzT("montage.ajout.allongee_tenir")\r\n        :dzT("montage.ajout.allongee_garde")\r\n          \r\n      \r\n      })',
      {'montage.ajout.allongee': (
          " La timeline a été allongée de {de} à {a}{raison} « Annuler » retire le clip, et rend aussi la durée "
          "d'avant.",
          ' The timeline was extended from {de} to {a}{raison} “Undo” removes the clip and restores the previous '
          'duration too.'),
       'montage.ajout.allongee_tenir': (" pour tenir tout ce qu'elle porte.", ' to fit everything on it.'),
       'montage.ajout.allongee_garde': (
           " : le clip garde sa longueur entière au lieu d'être rogné sur la fin du projet.",
           ': the clip keeps its full length instead of being trimmed at the end of the project.')}),
    S(288583, '" Posé sur la piste "+\r\n      "libre au-dessus (mode « au-dessus »)."',
      'dzT("montage.ajout.pose_au_dessus"\r\n      )',
      {'montage.ajout.pose_au_dessus': (' Posé sur la piste libre au-dessus (mode « au-dessus »).',
                                        ' Placed on the free track above (“above” mode).')}),
    S(288698, '" Mode « "+\r\n      DzTracks.modeLabel(dzIns.mode)+" »."',
      'dzT("montage.ajout.mode",{mode:\r\n      DzTracks.modeLabel(dzIns.mode)})',
      {'montage.ajout.mode': (' Mode « {mode} ».', ' “{mode}” mode.')}),
    S(288823, '" Vitesse ×"+String(dzP.speed).replace(".",",")+"."',
      'dzT("montage.ajout.vitesse",{v:String(dzP.speed).replace(".",",")})',
      {'montage.ajout.vitesse': (' Vitesse ×{v}.', ' Speed ×{v}.')}),
    L(288958, 'montage.ajout.plage_effacee', ' Plage effacée : posé en écraser.', ' Range cleared: placed in overwrite.'),
    S(289950, '"« "+label+" » ajouté sur "+tr2.toUpperCase()+" à "\r\n      +svmShort(st)+" — glissez / rognez sur la piste."',
      'dzT("montage.ajout.ajoute",{nom:label,piste:tr2.toUpperCase(),\r\n      t:svmShort(st)})',
      {'montage.ajout.ajoute': ('« {nom} » ajouté sur {piste} à {t} — glissez / rognez sur la piste.',
                                '“{nom}” added on {piste} at {t} — drag / trim it on the track.')}),
    S(290076, '" La piste "+dzMoved+" n\'existe pas dans ce projet : le "+\r\n        "clip vient d\'être posé sur "+tr2.toUpperCase()+" à la place"+\r\n        (tr2==="v1"?", où il s\'AJOUTE À LA SUITE des plans au lieu de "+\r\n          "s\'incruster par-dessus":"")+\r\n        ". « + piste "+dzMot+" » recrée le plus petit identifiant "+\r\n        "libre : cliquez jusqu\'à voir "+dzMoved+", puis remontez-y le "+\r\n        "clip — les clips déjà posés sur cette piste absente y "+\r\n        "réapparaîtront aussi."',
      'dzT("montage.ajout.piste_absente",{piste:dzMoved,\r\n        cible:tr2.toUpperCase(),\r\n        suite:tr2==="v1"?dzT("montage.ajout.piste_absente_v1")\r\n          :"",\r\n        mot:dzMot\r\n        \r\n        \r\n        })',
      {'montage.ajout.piste_absente': (
          " La piste {piste} n'existe pas dans ce projet : le clip vient d'être posé sur {cible} à la place{suite}. "
          "« + piste {mot} » recrée le plus petit identifiant libre : cliquez jusqu'à voir {piste}, puis remontez-y "
          "le clip — les clips déjà posés sur cette piste absente y réapparaîtront aussi.",
          ' Track {piste} does not exist in this project: the clip was placed on {cible} instead{suite}. '
          '“+ {mot} track” recreates the lowest free identifier: click until you see {piste}, then move the clip '
          'back up there — clips already placed on that missing track will reappear too.'),
       'montage.ajout.piste_absente_v1': (", où il s'AJOUTE À LA SUITE des plans au lieu de s'incruster par-dessus",
                                          ', where it is APPENDED AFTER the clips instead of being overlaid')}),

    # sfxInsert : insertion depuis le tiroir Sons
    L(290866, 'montage.sons.insertion_demo',
      "Insertion : disponible sur un projet réel — générez ou importez d'abord une vidéo, la timeline se remplira.",
      'Insertion: available on a real project — generate or import a video first, the timeline will fill up.'),
    L(291039, 'montage.sons.insertion_impossible', 'Insertion impossible — fichier audio introuvable.',
      'Cannot insert — audio file not found.'),

    # rack VFX : pose d'un effet (vfxAddTo, vfxDropEffect)
    L(291838, 'montage.effets.demo', *_DEMO_EFFETS),
    L(292010, 'montage.effets.video_seulement', 'Un effet vidéo se pose sur un clip V1 ou V2.',
      'A video effect goes on a V1 or V2 clip.'),
    S(292148, '"Piste "+c.tr.toUpperCase()+" verrouillée — déverrouillez-la pour poser un effet."',
      'dzT("montage.effets.piste_verrouillee",{piste:c.tr.toUpperCase()})',
      {'montage.effets.piste_verrouillee': ('Piste {piste} verrouillée — déverrouillez-la pour poser un effet.',
                                            'Track {piste} locked — unlock it to add an effect.')}),
    L(292615, 'montage.effets.depot_demo', "Dépôt d'effet : disponible sur un projet réel — la démo reste une maquette.",
      'Effect drop: available on a real project — the demo stays a mock-up.'),
    L(293070, 'montage.effets.aucun_clip', "Aucun clip sous le curseur — déposez l'effet sur un clip.",
      'No clip under the cursor — drop the effect on a clip.'),
    S(293185, '"Effet « "+(eff.label||eff.type)+" » posé sur « "+hit.label+" » — réglable dans la pile."',
      'dzT("montage.effets.pose_sur",{effet:eff.label||eff.type,clip:hit.label})',
      {'montage.effets.pose_sur': ('Effet « {effet} » posé sur « {clip} » — réglable dans la pile.',
                                   'Effect “{effet}” added to “{clip}” — adjustable in the stack.')}),

    # glisser-déposer sur les bandes
    L(295073, 'montage.depot.son', *_SON_DEPOT),
    L(295149, 'montage.depot.demo', 'Dépôt : disponible sur un projet réel — la démo reste une maquette.',
      'Drop: available on a real project — the demo stays a mock-up.'),
    L(295735, 'montage.depot.son', *_SON_DEPOT),
    L(295772, 'montage.depot.video', 'Cet asset se dépose sur V1 ou V2.', 'This asset goes on V1 or V2.'),

    # launchRender et suivi du job (étape et erreur montrées dans le popover)
    L(303336, 'montage.rendu.envoi', 'Envoi…', 'Sending…'),
    L(303830, 'montage.rendu.ajoute_file', 'Ajouté à la file', 'Added to the queue'),
    S(303875, '"File refusée : "+((o.d&&(o.d.detail||o.d.error))||"échec")',
      'dzT("montage.rendu.file_refusee",{e:(o.d&&(o.d.detail||o.d.error))||dzT("montage.rendu.echec")})',
      {'montage.rendu.file_refusee': ('File refusée : {e}', 'Queue refused: {e}'),
       'montage.rendu.echec': ('échec', 'failed')}),
    L(304108, 'montage.rendu.echec_lancement', 'échec du lancement', 'launch failed'),
    L(304235, 'montage.rendu.en_file', 'En file', 'Queued'),
    S(304305, '"File : "+String(e)', 'dzT("montage.rendu.file_erreur",{e:String(e)})',
      {'montage.rendu.file_erreur': ('File : {e}', 'Queue: {e}')}),
    S(305015, '"Aperçu 480p prêt — branché dans le lecteur ("+(d.duration_real_s||d.duration_s||"?")+" s)."',
      'dzT("montage.rendu.apercu_pret",{s:d.duration_real_s||d.duration_s||"?"})',
      {'montage.rendu.apercu_pret': ('Aperçu 480p prêt — branché dans le lecteur ({s} s).',
                                     '480p preview ready — loaded in the player ({s} s).')}),
    L(305506, 'montage.rendu.final_termine', 'Rendu final terminé — « Envoyer vers le Scheduler » pour le publier.',
      'Final render done — “Send to Scheduler” to publish it.'),
    L(305724, 'montage.rendu.echec_rendu', 'échec du rendu', 'render failed'),
    X(307218, 'sélecteur CSS (querySelector [data-nbid])'),

    # popover « Plans trop longs / jump cuts »
    L(308422, 'montage.boring.titre', 'Plans trop longs / jump cuts', 'Overlong clips / jump cuts'),
    L(308509, 'montage.boring.note',
      'Sur V1 : liseré gris pointillé = plan plus long que le seuil ; liseré rouge = jump cut (même source reprise '
      'presque au même point, à la coupe).',
      'On V1: dotted grey edge = clip longer than the threshold; red edge = jump cut (same source resumed at almost '
      'the same point, at the cut).'),
    L(308725, 'montage.boring.activer_aide', 'Marquer sur la timeline les plans trop longs et les jump cuts de V1',
      "Mark V1's overlong clips and jump cuts on the timeline"),
    L(308917, 'montage.boring.activer', ' Activer', ' Enable'),
    L(309062, 'montage.boring.plus_long', 'Plus long que (s)', 'Longer than (s)'),
    L(309188, 'montage.boring.plus_long_aide', 'Un plan de V1 plus long que ce seuil (2 à 60 s) est marqué « long »',
      'A V1 clip longer than this threshold (2 to 60 s) is marked “long”'),
    L(309450, 'montage.boring.ecart', 'Jump cut si écart < (images)', 'Jump cut if gap < (frames)'),
    L(309592, 'montage.boring.ecart_aide',
      'Deux plans V1 de la même source, en contact, dont la reprise est à moins de n images (1 à 60, à 30 i/s) : '
      'jump cut',
      'Two touching V1 clips from the same source, resuming less than n frames apart (1 to 60, at 30 fps): jump cut'),
    S(309839, 'nb+" plan"+(nb>1?"s":"")+" marqué"+(nb>1?"s":"")+" sur V1 ("+nj+" jump cut"+(nj>1?"s":"")+")"',
      '(function(j){return nb>1?dzT("montage.boring.marques_plusieurs",{n:nb,j:j}):'
      'dzT("montage.boring.marques_un",{n:nb,j:j})})(nj>1?dzT("montage.boring.jumps_plusieurs",{n:nj}):'
      'dzT("montage.boring.jumps_un",{n:nj}))',
      {'montage.boring.marques_un': ('{n} plan marqué sur V1 ({j})', '{n} clip marked on V1 ({j})'),
       'montage.boring.marques_plusieurs': ('{n} plans marqués sur V1 ({j})', '{n} clips marked on V1 ({j})'),
       'montage.boring.jumps_un': ('{n} jump cut', '{n} jump cut'),
       'montage.boring.jumps_plusieurs': ('{n} jump cuts', '{n} jump cuts')}),
    L(309933, 'montage.boring.aucun', 'Aucun plan à signaler sur V1', 'No clip to flag on V1'),
    L(309965, 'montage.boring.eteinte', 'Détection éteinte', 'Detection off'),
    L(310095, 'montage.commun.fermer_ce_panneau_echap', *_FERMER_PANNEAU),
    L(310163, 'montage.commun.fermer', *_FERMER),

    # popover de confirmation du rendu (Preview 480p / Rendre)
    L(310793, 'montage.rendu.titre_rendre', 'Rendre (master 1080)', 'Render (1080 master)'),
    L(310816, 'montage.rendu.titre_preview', 'Preview 480p', '480p preview'),
    S(310916, '"rendu ffmpeg (local) · "+svmRuler(Math.round(dur))',
      'dzT("montage.rendu.ligne_rendu",{d:svmRuler(Math.round(dur))})',
      {'montage.rendu.ligne_rendu': ('rendu ffmpeg (local) · {d}', 'ffmpeg render (local) · {d}')}),
    S(310968, '"aperçu ffmpeg 480p (local) · "+svmRuler(Math.round(dur))',
      'dzT("montage.rendu.ligne_apercu",{d:svmRuler(Math.round(dur))})',
      {'montage.rendu.ligne_apercu': ('aperçu ffmpeg 480p (local) · {d}', 'ffmpeg 480p preview (local) · {d}')}),
    L(311454, 'montage.rendu.publication', 'publication · à la demande, après le rendu',
      'publishing · on demand, after the render'),
    L(311545, 'montage.rendu.gratuit', 'gratuit', 'free'),
    L(311639, 'montage.rendu.demo',
      "Timeline de démonstration — aucune source réelle à rendre. Génère ou importe d'abord une vidéo (Studio, "
      "Quick, Épisodes ou upload) : la timeline se remplira depuis la Bibliothèque.",
      'Demo timeline — no real source to render. Generate or import a video first (Studio, Quick, Episodes or '
      'upload): the timeline will fill from the Library.'),
    L(311887, 'montage.rendu.en_cours', 'Rendu en cours — ', 'Rendering — '),
    L(312036, 'montage.rendu.echec_prefixe', 'Échec : ', 'Failed: '),
    L(312132, 'montage.rendu.note_final',
      "Rendu local 1080 (aucun crédit consommé). À la fin, un bandeau propose l'envoi vers le Scheduler — rien "
      "n'est publié sans ta validation.",
      'Local 1080 render (no credits used). When it finishes, a banner offers to send it to the Scheduler — '
      'nothing is published without your approval.'),
    L(312283, 'montage.rendu.note_apercu',
      "L'aperçu basse résolution est gratuit et local — il ne consomme jamais de crédits. Le résultat se branche "
      "dans le lecteur.",
      'The low-resolution preview is free and local — it never uses credits. The result loads in the player.'),
    L(312520, 'montage.commun.fermer_ce_panneau_echap', *_FERMER_PANNEAU),
    L(312611, 'montage.commun.fermer', *_FERMER),
    L(312716, 'montage.rendu.indisponible_demo', *_INDISPO),
    L(312772, 'montage.rendu.relancer_aide', 'Relancer le rendu qui a échoué', 'Rerun the failed render'),
    L(312853, 'montage.commun.reessayer', 'Réessayer', 'Retry'),
    L(313020, 'montage.rendu.indisponible_demo', *_INDISPO),
    L(313081, 'montage.rendu.lancer_final_aide', 'Lancer le rendu final (master 1080, local)',
      'Start the final render (1080 master, local)'),
    L(313126, 'montage.rendu.lancer_apercu_aide', "Lancer l'aperçu 480p (gratuit, local)",
      'Start the 480p preview (free, local)'),
    L(313281, 'montage.rendu.rendre', 'Rendre', 'Render'),
    L(313290, 'montage.rendu.lancer_apercu', "Lancer l'aperçu", 'Start preview'),
    L(313422, 'montage.rendu.indisponible_demo', *_INDISPO),
    L(313483, 'montage.rendu.file_finaux', 'La file locale ne prend que des rendus finaux',
      'The local queue only takes final renders'),
    L(313536, 'montage.rendu.deja_en_cours', 'Un rendu de ce type est déjà en cours',
      'A render of this type is already running'),
    L(313576, 'montage.rendu.file_aide',
      "Ajouter ce rendu final à la file locale (rendus en série, l'écran reste libre)",
      'Add this final render to the local queue (renders run one after another, the screen stays free)'),
    L(313720, 'montage.rendu.ajouter_file', 'Ajouter à la file', 'Add to queue'),

    # sélecteur d'effets (panneau du rack, sélecteur historique)
    S(314462, '"Effet « "+((meta&&meta.label)||eff.type)+" » posé — réglable dans la pile."',
      'dzT("montage.effets.pose",{effet:(meta&&meta.label)||eff.type})',
      {'montage.effets.pose': ('Effet « {effet} » posé — réglable dans la pile.',
                               'Effect “{effet}” added — adjustable in the stack.')}),
    L(314833, 'montage.effets.ajouter_titre', 'Ajouter un effet — moteur Effects / Mask',
      'Add an effect — Effects / Mask engine'),
    S(315456, '"Effet « "+((fxCat[t3]&&fxCat[t3].label)||t3)+" » ajouté — appliqué au rendu du clip."',
      'dzT("montage.effets.ajoute",{effet:(fxCat[t3]&&fxCat[t3].label)||t3})',
      {'montage.effets.ajoute': ('Effet « {effet} » ajouté — appliqué au rendu du clip.',
                                 'Effect “{effet}” added — applied when the clip renders.')}),
    L(315718, 'montage.effets.fermer_selecteur', "Fermer le sélecteur d'effets", 'Close the effect picker'),
    L(315792, 'montage.commun.fermer', *_FERMER),

    # inspecteur Overlay : en-tête, X / Y, alignement
    L(316761, 'montage.overlay.kf_aide', ' · écrit le point le plus proche de la tête (≤ 0,15 s) ou en pose un',
      ' · writes the point nearest the playhead (≤ 0.15 s) or adds one'),
    X(317527, 'valeur CSS (flex)'),
    X(317548, 'identique dans les deux langues'),
    L(317635, 'montage.overlay.plein_cadre_aide',
      "Revenir au plein cadre (équivaut au double-clic sur l'overlay dans le lecteur)",
      'Back to full frame (same as double-clicking the overlay in the player)'),
    L(317720, 'montage.overlay.plein_cadre_trajectoire', ' — retire aussi la trajectoire',
      ' — also removes the motion path'),
    L(317827, 'montage.overlay.plein_cadre', 'plein cadre', 'full frame'),
    L(318079, 'montage.overlay.x_aide', 'X du centre en % du canvas (50 = centré) — flèches : ±0,5',
      'Center X in % of the canvas (50 = centered) — arrows: ±0.5'),
    L(318169, 'montage.overlay.x', 'Position X (%)', 'X position (%)'),
    L(318567, 'montage.overlay.y_aide', 'Y du centre en % du canvas (50 = centré) — flèches : ±0,5',
      'Center Y in % of the canvas (50 = centered) — arrows: ±0.5'),
    L(318657, 'montage.overlay.y', 'Position Y (%)', 'Y position (%)'),
    L(319160, 'montage.overlay.aligner', 'Aligner', 'Align'),
    L(319256, 'montage.overlay.alignement', "Alignement rapide de l'overlay (marge 4 %)",
      'Quick overlay alignment (4% margin)'),
    # libellé de case : « en haut à gauche » -> « top left », « au centre » -> « center »
    L(319411, 'montage.overlay.en_haut', 'en haut', 'top'),
    L(319428, 'montage.overlay.en_bas', 'en bas', 'bottom'),
    L(319437, 'montage.overlay.au_centre', 'au centre', 'center'),
    L(319474, 'montage.overlay.a_gauche', ' à gauche', ' left'),
    L(319493, 'montage.overlay.a_droite', ' à droite', ' right'),
    L(319516, 'montage.overlay.au_centre_x', ' au centre', ' center'),
    S(319611, '"Coller l\'overlay "+lbl+" — bord réel à 4 % du bord du canvas"',
      'dzT("montage.overlay.coller",{pos:lbl})',
      {'montage.overlay.coller': ("Coller l'overlay {pos} — bord réel à 4 % du bord du canvas",
                                  'Snap the overlay to the {pos} — real edge at 4% from the canvas edge')}),
    S(319708, '"Aligner l\'overlay "+lbl', 'dzT("montage.overlay.aligner_pos",{pos:lbl})',
      {'montage.overlay.aligner_pos': ("Aligner l'overlay {pos}", 'Align the overlay to the {pos}')}),

    # inspecteur Overlay : échelle, rotation, opacité, coins, ombre
    L(320023, 'montage.overlay.echelle', 'Échelle', 'Scale'),
    L(320124, 'montage.overlay.echelle_aide', "Largeur de l'overlay en % de celle du canvas (100 = pleine largeur)",
      'Overlay width in % of the canvas width (100 = full width)'),
    L(320224, 'montage.overlay.echelle_pc', 'Échelle (%)', 'Scale (%)'),
    X(320677, 'identique dans les deux langues'),
    L(320785, 'montage.overlay.rotation_aide', 'Rotation en degrés (−180 à 180) — aimant 0 / ±45 / 90 dans le lecteur',
      'Rotation in degrees (−180 to 180) — snaps to 0 / ±45 / 90 in the player'),
    L(320887, 'montage.overlay.rotation_degres', 'Rotation (degrés)', 'Rotation (degrees)'),
    L(321355, 'montage.overlay.opacite', 'Opacité', 'Opacity'),
    S(321477, '"Opacité de l\'overlay ("+vOp+" %)"', 'dzT("montage.overlay.opacite_val",{v:vOp})',
      {'montage.overlay.opacite_val': ("Opacité de l'overlay ({v} %)", 'Overlay opacity ({v}%)')}),
    L(321530, 'montage.overlay.opacite_overlay', "Opacité de l'overlay", 'Overlay opacity'),
    L(322412, 'montage.overlay.coins', 'Coins', 'Corners'),
    L(322499, 'montage.overlay.coins_aide',
      "Rayon des coins de l'overlay en px du canvas (0 = coins droits, 200 au plus) — statique, les keyframes ne "
      "l'animent pas",
      'Overlay corner radius in canvas px (0 = square corners, 200 max) — static, keyframes do not animate it'),
    L(322646, 'montage.overlay.coins_px', 'Coins (px)', 'Corners (px)'),
    L(323047, 'montage.overlay.ombre', 'Ombre', 'Shadow'),
    L(323127, 'montage.overlay.ombre_aide',
      "Ombre portée sous l'overlay (noir à 55 %, décalée de 6 px au rendu) — statique, retirée par « plein cadre »",
      'Drop shadow under the overlay (black at 55%, offset 6 px in the render) — static, removed by “full frame”'),
    L(323322, 'montage.overlay.ombre_portee', 'Ombre portée', 'Drop Shadow'),
    L(323405, 'montage.overlay.portee', ' portée', ' cast'),

    # inspecteur Overlay : trajectoire (keyframes de position)
    X(323872, 'valeur CSS (flex)'),
    L(323893, 'montage.trajectoire.titre', 'Trajectoire', 'Motion path'),
    S(323978, 'mp.length+" point"+(mp.length>1?"s":"")+" sur "+SVM_MP_CAP+" (contrat du rendu)"',
      '(mp.length>1?dzT("montage.trajectoire.points_plusieurs",{n:mp.length,max:SVM_MP_CAP})'
      ':dzT("montage.trajectoire.points_un",{n:mp.length,max:SVM_MP_CAP}))',
      {'montage.trajectoire.points_un': ('{n} point sur {max} (contrat du rendu)', '{n} point of {max} (render limit)'),
       'montage.trajectoire.points_plusieurs': ('{n} points sur {max} (contrat du rendu)',
                                                '{n} points of {max} (render limit)')}),
    L(324190, 'montage.trajectoire.poser_aide',
      "Pose (ou écrase à ≤ 0,15 s) un point de position à la tête de lecture — x / y / rotation courants ; 2 points "
      "ou plus animent l'overlay au rendu (interpolation linéaire)",
      'Sets (or overwrites within ≤ 0.15 s) a position point at the playhead — current x / y / rotation; 2 or more '
      'points animate the overlay in the render (linear interpolation)'),
    L(324400, 'montage.trajectoire.poser', '◇ position ici', '◇ position here'),
    L(324612, 'montage.trajectoire.caler', 'Caler la tête sur ce point', 'Move the playhead to this point'),
    X(324667, 'identique dans les deux langues'),
    L(325151, 'montage.trajectoire.retirer', 'Retirer ce point', 'Remove this point'),
    S(325199, '"Retirer le point à "+svmShort(p.t)', 'dzT("montage.trajectoire.retirer_a",{t:svmShort(p.t)})',
      {'montage.trajectoire.retirer_a': ('Retirer le point à {t}', 'Remove the point at {t}')}),
    X(325485, 'valeur CSS (flex)'),
    L(325532, 'montage.trajectoire.un_seul', 'un seul point — il en faut 2 pour animer au rendu',
      'only one point — 2 are needed to animate in the render'),
    S(325801, '"position"+(nR>1?" et rotation":"")+\r\n                  " interpolées linéairement au rendu · l\'échelle reste fixe"',
      '(nR>1?dzT("montage.trajectoire.interp_pos_rot")\r\n                  :dzT("montage.trajectoire.interp_pos"))',
      {'montage.trajectoire.interp_pos_rot': (
          "position et rotation interpolées linéairement au rendu · l'échelle reste fixe",
          'position and rotation interpolated linearly in the render · scale stays fixed'),
       'montage.trajectoire.interp_pos': (
           "position interpolées linéairement au rendu · l'échelle reste fixe",
           'position interpolated linearly in the render · scale stays fixed')}),
    L(325994, 'montage.trajectoire.aucun',
      "aucun point — « ◇ position ici » fige x / y / rotation à la tête ; 2 points ou plus créent le mouvement (le "
      "drag du lecteur édite alors le point le plus proche ≤ 0,15 s, sinon en pose un)",
      'no point — “◇ position here” freezes x / y / rotation at the playhead; 2 or more points create motion '
      '(dragging in the player then edits the nearest point ≤ 0.15 s, or adds one)'),
    L(326264, 'montage.overlay.plein_cadre_note',
      "plein cadre (cover) — saisissez l'overlay dans le lecteur pour le déplacer, le redimensionner ou le tourner",
      'full frame (cover) — grab the overlay in the player to move, resize or rotate it'),

    # clip d'ajustement : titre de section, fondus
    L(328645, 'montage.ajustement.titre',
      "Ajustement — ses effets s'appliquent à tout ce qui est dessous, visibles après Preview",
      'Adjustment — its effects apply to everything below, visible after Preview'),
    S(330984, 'lbl+" du clip d\'ajustement (s)"', 'dzT("montage.ajustement.champ_aria",{champ:lbl})',
      {'montage.ajustement.champ_aria': ("{champ} du clip d'ajustement (s)", '{champ} of the adjustment clip (s)')}),
    S(331034, '(which==="out"?"Les effets qui finissent avec le clip s\'éteignent":"Les effets qui commencent avec le clip s\'allument")+\r\n            " en douceur sur cette durée (0 à "+(Math.round(half*10)/10)+" s, la moitié du clip) — visible après Preview"',
      'dzT("montage.ajustement.fondu_aide",{effet:which==="out"?dzT("montage.ajustement.eteignent")'
      ':dzT("montage.ajustement.allument"),\r\n            max:Math.round(half*10)/10})',
      {'montage.ajustement.fondu_aide': (
          '{effet} en douceur sur cette durée (0 à {max} s, la moitié du clip) — visible après Preview',
          '{effet} smoothly over this duration (0 to {max} s, half the clip) — visible after Preview'),
       'montage.ajustement.eteignent': ("Les effets qui finissent avec le clip s'éteignent",
                                        'Effects that end with the clip fade out'),
       'montage.ajustement.allument': ("Les effets qui commencent avec le clip s'allument",
                                       'Effects that start with the clip fade in')}),
    L(331421, 'montage.ajustement.fondu_entree', "Fondu d'entrée", 'Fade in'),
    L(331451, 'montage.ajustement.fondu_sortie', 'Fondu de sortie', 'Fade out'),

    # section « Effets sur ce clip » (chips historiques) et réglage d'un effet
    L(331609, 'montage.effets.sur_ce_clip', 'Effets sur ce clip', 'Effects on this clip'),
    L(332302, 'montage.effets.regler_aide', "Régler / retirer l'effet", 'Adjust / remove the effect'),
    L(332656, 'montage.effets.demo', *_DEMO_EFFETS),
    L(332808, 'montage.effets.catalogue_absent', "Catalogue d'effets indisponible — backend à relancer ?",
      'Effect catalog unavailable — restart the backend?'),
    L(332928, 'montage.effets.ajouter', '+ effet', '+ effect'),
    S(333555, '"Intensité de l\'effet "+lbl', 'dzT("montage.effets.intensite",{effet:lbl})',
      {'montage.effets.intensite': ("Intensité de l'effet {effet}", '{effet} effect intensity')}),
    L(334026, 'montage.effets.sans_intensite', "sans réglage d'intensité", 'no intensity setting'),
    L(334224, 'montage.effets.retirer_aide', 'Retirer cet effet du plan', 'Remove this effect from the clip'),
    L(334588, 'montage.effets.retirer', 'retirer', 'remove'),

    # ovPicker : sélecteur d'assets (titre, mode remplacement, notes, listes)
    S(335632, '"Remplacer la source de « "+(dzmA.label||"ce plan")+" »"',
      'dzT("montage.selecteur.remplacer_titre",{nom:dzmA.label||dzT("montage.selecteur.ce_plan")})',
      {'montage.selecteur.remplacer_titre': ('Remplacer la source de « {nom} »', 'Replace the source of “{nom}”'),
       'montage.selecteur.ce_plan': ('ce plan', 'this clip')}),
    S(335701, '"Ajouter sur la piste "+tr2.toUpperCase()',
      'dzT("montage.selecteur.ajouter_titre",{piste:tr2.toUpperCase()})',
      {'montage.selecteur.ajouter_titre': ('Ajouter sur la piste {piste}', 'Add to track {piste}')}),
    S(335936, '"Le prochain élément choisi REMPLACERA la source de ce plan (piste "+dzmA.tr.toUpperCase()+") au lieu d\'être posé : ses bornes, ses effets, sa transition et son mixage restent en place. Un glisser-déposer compte aussi comme un choix — la piste et l\'instant du dépôt sont alors ignorés. Fermez ce panneau pour annuler."',
      'dzT("montage.selecteur.remplacer_note",{piste:dzmA.tr.toUpperCase()})',
      {'montage.selecteur.remplacer_note': (
          "Le prochain élément choisi REMPLACERA la source de ce plan (piste {piste}) au lieu d'être posé : ses "
          "bornes, ses effets, sa transition et son mixage restent en place. Un glisser-déposer compte aussi comme un "
          "choix — la piste et l'instant du dépôt sont alors ignorés. Fermez ce panneau pour annuler.",
          "The next item you pick will REPLACE this clip's source (track {piste}) instead of being placed: its "
          'bounds, effects, transition and mix stay in place. A drag-and-drop also counts as a pick — the drop '
          'track and time are then ignored. Close this panel to cancel.')}),
    S(336280, '"Posé à la tête de lecture ("+svmShort(ph)+"). A1 = dialogue, A2 = musique (ducking auto), A3 = SFX."',
      'dzT("montage.selecteur.note_audio",{t:svmShort(ph)})',
      {'montage.selecteur.note_audio': (
          'Posé à la tête de lecture ({t}). A1 = dialogue, A2 = musique (ducking auto), A3 = SFX.',
          'Placed at the playhead ({t}). A1 = dialogue, A2 = music (auto ducking), A3 = SFX.')}),
    S(336408, '"Posé à la tête de lecture ("+svmShort(ph)+") — ou déposez directement sur une bande ou le viewport. Les PNG gardent leur transparence."',
      'dzT("montage.selecteur.note_video",{t:svmShort(ph)})',
      {'montage.selecteur.note_video': (
          'Posé à la tête de lecture ({t}) — ou déposez directement sur une bande ou le viewport. Les PNG gardent '
          'leur transparence.',
          'Placed at the playhead ({t}) — or drop straight onto a lane or the viewport. PNGs keep their '
          'transparency.')}),
    L(336613, 'montage.selecteur.images', 'Images (Bibliothèque)', 'Images (Library)'),
    S(336831, 'im.name+" — cliquer ou glisser"', 'dzT("montage.selecteur.cliquer_glisser",{nom:im.name})',
      {'montage.selecteur.cliquer_glisser': _GLISSER}),
    X(337001, "URL d'image (style backgroundImage)"),
    L(337255, 'montage.selecteur.aucune_image', 'aucune image dans la Bibliothèque', 'no image in the Library'),
    L(337359, 'montage.selecteur.rendus_video', 'Rendus vidéo', 'Video renders'),
    S(337639, 'v3.title+" — cliquer ou glisser"', 'dzT("montage.selecteur.cliquer_glisser",{nom:v3.title})',
      {'montage.selecteur.cliquer_glisser': _GLISSER}),
]
