"""t143 — montage_g : couche Montage (frontend/patches/montage.js), lignes 7068–7799 de la base. Couvre : la fin du
popover Auto-clips (DzmAutoclips : lancer, créer, messages, champs, liste des extraits), la mini-carte (DzmMinimap),
le menu ☰ et les menus contextuels (DzmCtxMenu : en-têtes de rubrique), le préréglage clavier Resolve, le
copier-coller de clips (dzmClipPaste : notes de refus), la comparaison de versions (DZM_DIFF_RUB, DzmDiffView) et la
découpe aux changements de plan (dzmCutAt : notes).

Gardés (X) :
- DZM_KEY_TOK : jetons de combo ANALYSÉS (« échap », « entrée ») et valeurs KeyboardEvent.key (« Delete », « Home »,
  « End », « Tab ») ; DZM_KM_PRESETS : combos « Alt+O », « Ctrl+B » (keymap enregistrée).
- DZM_MENU_ORDRE, DZM_MENU_RUB et dzmMenuRub : les rubriques sont des VALEURS — clés de regroupement, comparées à
  `a.sec` (« Audio », « Affichage » : sections de raccourcis de son-vfx-montage) et par l'hôte
  (g.rub==="Affichage"). Elles sont traduites au SITE D'AFFICHAGE, l'en-tête .svm-menurub de DzmCtxMenu (S) :
  Édition / Marqueurs / Affichage / Aide ; « Timeline » est identique en anglais ; « Projet » arrive déjà traduit
  par l'hôte (dzT("montage.menu.projet")).
- « (vide) » de dzmSubsLabelOf : libellé ENREGISTRÉ dans le clip de sous-titre (label), tenu à l'identique de
  subsLabelOf de subs.js.
- « (source  » de la comparaison : identique en anglais.

Phrases recomposées (S) : le message de fin d'analyse (pluriel « extrait(s) » + classement IA / heuristique), les
gabarits « Projet « … » créé », « Comparer : « … » → « … » », les coûts « (≈ … ) », le score, « Extrait n », les
notes de collage refusé et de découpe (pluriel « coupe(s) »)."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_FERMER = ('Fermer', 'Close')
_ANALYSE = ('Analyse…', 'Analyzing…')
_ERREUR = ('erreur réseau', 'network error')

ENTREES = [
    # DzmAutoclips : lancer l'analyse
    L(434111, 'montage.autoclips.source_illisible', "Source illisible — rien n'est lancé.",
      'Unreadable source — nothing was started.'),
    L(434313, 'montage.autoclips.transcription_en_cours', 'Transcription payante en cours, puis analyse…',
      'Paid transcription in progress, then analysis…'),
    L(434361, 'montage.autoclips.analyse', *_ANALYSE),
    S(434895, 'cs.length+" extrait"+(cs.length>1?"s":"")+" — "+dzmAcTrTxt(d.transcript)+" ; "\r\n'
              '            +(sc.indexOf("llm:")===0?"classés par l\'IA ("+sc.slice(4)+")":"classés par l\'heuristique (gratuit)")+"."',
      '(function(cl){return cs.length>1?dzT("montage.autoclips.extraits.plusieurs",{n:cs.length,transcription:dzmAcTrTxt(d.transcript),classement:cl}):\r\n'
      '            dzT("montage.autoclips.extraits.un",{n:cs.length,transcription:dzmAcTrTxt(d.transcript),classement:cl})})(sc.indexOf("llm:")===0?dzT("montage.autoclips.classes_ia",{modele:sc.slice(4)}):dzT("montage.autoclips.classes_heuristique"))',
      {'montage.autoclips.extraits.un': ('{n} extrait — {transcription} ; {classement}.',
                                         '{n} excerpt — {transcription}; {classement}.'),
       'montage.autoclips.extraits.plusieurs': ('{n} extraits — {transcription} ; {classement}.',
                                                '{n} excerpts — {transcription}; {classement}.'),
       'montage.autoclips.classes_ia': ("classés par l'IA ({modele})", 'ranked by AI ({modele})'),
       'montage.autoclips.classes_heuristique': ("classés par l'heuristique (gratuit)", 'ranked by heuristic (free)')}),
    L(435285, 'montage.autoclips.non_confirmee', "Transcription payante non confirmée — rien n'a été lancé.",
      'Paid transcription not confirmed — nothing was started.'),
    S(435498, '"Auto-clips refusés : "+String((e&&e.message)||"erreur réseau")',
      'dzT("montage.autoclips.refuses",{e:String((e&&e.message)||dzT("montage.mots.erreur_reseau"))})',
      {'montage.autoclips.refuses': ('Auto-clips refusés : {e}', 'Auto-clips refused: {e}'),
       'montage.mots.erreur_reseau': _ERREUR}),

    # DzmAutoclips : créer le projet d'un extrait
    L(435758, 'montage.autoclips.creation', 'Création du projet…', 'Creating the project…'),
    L(436190, 'montage.autoclips.reponse_inattendue', "Réponse inattendue : aucun projet n'a été créé.",
      'Unexpected response: no project was created.'),
    S(436514, '"Projet « "+nm+" » créé — ouverture demandée : il remplace le montage affiché, la liste des projets dit le résultat."',
      'dzT("montage.autoclips.cree_ouverture",{nom:nm})',
      {'montage.autoclips.cree_ouverture': (
          'Projet « {nom} » créé — ouverture demandée : il remplace le montage affiché, la liste des projets dit le '
          'résultat.',
          'Project “{nom}” created — opening requested: it replaces the displayed edit, the project list reports the '
          'result.')}),
    S(436655, '"Projet « "+nm+" » créé — ouvrez-le depuis la liste des projets."',
      'dzT("montage.autoclips.cree",{nom:nm})',
      {'montage.autoclips.cree': ('Projet « {nom} » créé — ouvrez-le depuis la liste des projets.',
                                  'Project “{nom}” created — open it from the project list.')}),
    S(436801, '"Création refusée : "+String((e&&e.message)||"erreur réseau")',
      'dzT("montage.autoclips.creation_refusee",{e:String((e&&e.message)||dzT("montage.mots.erreur_reseau"))})',
      {'montage.autoclips.creation_refusee': ('Création refusée : {e}', 'Creation refused: {e}'),
       'montage.mots.erreur_reseau': _ERREUR}),

    # DzmAutoclips : bouton de lancement (libellé et aide)
    L(437053, 'montage.autoclips.analyse', *_ANALYSE),
    L(437070, 'montage.autoclips.lancer_gratuit', 'Lancer (texte connu, gratuit)', 'Run (known text, free)'),
    S(437115, '"Payer et lancer (≈ "+dzmAcUsd(est.usd)+")"',
      'dzT("montage.autoclips.payer_lancer",{usd:dzmAcUsd(est.usd)})',
      {'montage.autoclips.payer_lancer': ('Payer et lancer (≈ {usd})', 'Pay and run (≈ {usd})')}),
    L(437159, 'montage.autoclips.estimer_lancer', 'Estimer / Lancer', 'Estimate / Run'),
    L(437197, 'montage.autoclips.lancer_gratuit_aide',
      'Cale le texte connu sur le son de la vidéo (gratuit), puis propose les extraits',
      "Aligns the known text with the video's audio (free), then suggests excerpts"),
    S(437298, '"Lance la transcription PAYANTE annoncée (≈ "+dzmAcUsd(est.usd)+"), puis propose les extraits"',
      'dzT("montage.autoclips.payer_lancer_aide",{usd:dzmAcUsd(est.usd)})',
      {'montage.autoclips.payer_lancer_aide': (
          'Lance la transcription PAYANTE annoncée (≈ {usd}), puis propose les extraits',
          'Runs the announced PAID transcription (≈ {usd}), then suggests excerpts')}),
    L(437399, 'montage.autoclips.estimer_aide',
      "Sans texte connu : demande d'abord le coût de la transcription — rien n'est payé sans la case « Payer la "
      "transcription »",
      'Without known text: asks for the transcription cost first — nothing is paid without the “Pay for '
      'transcription” box'),

    # DzmAutoclips : en-tête, source, champs
    L(437740, 'montage.autoclips.titre', 'Auto-clips — extraits de 15 à 60 s', 'Auto-clips — 15 to 60 s excerpts'),
    L(437846, 'montage.autoclips.fermer_aide', "Fermer les auto-clips (rien n'est lancé)",
      'Close auto-clips (nothing is started)'),
    L(437953, 'montage.mots.fermer', *_FERMER),
    S(438025, '"Source : "+String(o.label||"rendu")',
      'dzT("montage.autoclips.source",{nom:String(o.label||dzT("montage.mots.rendu"))})',
      {'montage.autoclips.source': ('Source : {nom}', 'Source: {nom}'),
       'montage.mots.rendu': ('rendu', 'render')}),
    L(438213, 'montage.autoclips.texte_placeholder', 'Texte connu (gratuit) — le texte dit dans la vidéo',
      'Known text (free) — the text spoken in the video'),
    L(438280, 'montage.autoclips.texte_aide',
      "Texte connu (gratuit) : le script dit dans la vidéo, calé sur le son sans transcription payante. Vide : la "
      "transcription payante est estimée d'abord.",
      'Known text (free): the script spoken in the video, aligned with the audio without paid transcription. '
      'Empty: the paid transcription is estimated first.'),
    L(438605, 'montage.autoclips.nombre_aide', "Nombre d'extraits proposés (1 à 8)",
      'Number of excerpts suggested (1 to 8)'),
    L(438652, 'montage.autoclips.extraits_label', 'Extraits ', 'Excerpts '),
    L(438899, 'montage.autoclips.langue_aide', 'Langue parlée dans la vidéo (calage du texte connu, transcription)',
      'Language spoken in the video (known-text alignment, transcription)'),
    L(439263, 'montage.autoclips.persona_placeholder', 'Persona (facultatif)', 'Persona (optional)'),
    L(439292, 'montage.autoclips.persona_aide',
      'Persona (facultatif, 60 caractères) : le public visé, ses mots-clés comptent dans le score',
      'Persona (optional, 60 characters): the target audience; its keywords count in the score'),
    L(439501, 'montage.autoclips.ia_aide',
      'Coché : un modèle de langue note et titre les extraits (quelques centimes). Décoché : score heuristique, '
      'gratuit.',
      'Checked: a language model scores and titles the excerpts (a few cents). Unchecked: heuristic score, free.'),
    L(439757, 'montage.autoclips.ia', "Classer avec l'IA (quelques centimes)", 'Rank with AI (a few cents)'),
    L(439988, 'montage.autoclips.payer_aide',
      "Cocher pour autoriser CETTE dépense au prochain « Lancer » — une seule fois ; décochée, rien n'est payé",
      'Check to allow THIS expense on the next “Run” — once only; unchecked, nothing is paid'),
    S(440243, '"Payer la transcription (≈ "+dzmAcUsd(est.usd)+")"',
      'dzT("montage.autoclips.payer",{usd:dzmAcUsd(est.usd)})',
      {'montage.autoclips.payer': ('Payer la transcription (≈ {usd})', 'Pay for transcription (≈ {usd})')}),

    # DzmAutoclips : liste des extraits proposés
    S(440770, '"Score 0–100 ("+(c.origine==="llm"?"IA":"heuristique")+")"',
      'dzT("montage.autoclips.score",{origine:c.origine==="llm"?dzT("montage.autoclips.origine_ia"):dzT("montage.autoclips.origine_heuristique")})',
      {'montage.autoclips.score': ('Score 0–100 ({origine})', 'Score 0–100 ({origine})'),
       'montage.autoclips.origine_ia': ('IA', 'AI'),
       'montage.autoclips.origine_heuristique': ('heuristique', 'heuristic')}),
    S(440968, '"Extrait "+(i+1)',
      'dzT("montage.autoclips.extrait_n",{n:i+1})',
      {'montage.autoclips.extrait_n': ('Extrait {n}', 'Excerpt {n}')}),
    L(441285, 'montage.autoclips.creer_confirmer_aide',
      "Confirmer : créer ce projet et l'OUVRIR — il remplace le montage affiché (un montage non nommé est d'abord mis "
      "à l'abri par la liste des projets)",
      'Confirm: create this project and OPEN it — it replaces the displayed edit (an unnamed edit is first saved '
      'aside by the project list)'),
    L(441447, 'montage.autoclips.creer_aide',
      'Créer un projet neuf avec cet extrait (V1, son du plan, sous-titres) — un second clic confirme',
      'Create a new project with this excerpt (V1, clip audio, subtitles) — a second click confirms'),
    L(441599, 'montage.autoclips.creer_ouvrir', 'Créer et ouvrir ?', 'Create and open?'),
    L(441619, 'montage.autoclips.creer', 'Créer le projet', 'Create project'),

    # DzmMinimap
    L(447832, 'montage.minimap.aide', 'Mini-carte — cliquer pour centrer la timeline',
      'Mini-map — click to center the timeline'),

    # DZM_KEY_TOK : jetons de combo analysés -> KeyboardEvent.key
    X(449200, 'valeur KeyboardEvent.key rejouée par dispatchEvent'),
    X(449209, 'jeton de combo ANALYSÉ (clé de DZM_KEY_TOK, comparée au morceau de la combo)'),
    X(449239, 'jeton de combo ANALYSÉ (clé de DZM_KEY_TOK, comparée au morceau de la combo)'),
    X(449330, 'valeur KeyboardEvent.key rejouée par dispatchEvent'),
    X(449343, 'valeur KeyboardEvent.key rejouée par dispatchEvent'),
    X(449355, 'valeur KeyboardEvent.key rejouée par dispatchEvent'),

    # DZM_MENU_ORDRE : rubriques = clés de regroupement (traduites à l'affichage, dans DzmCtxMenu)
    X(450439, 'rubrique = clé de regroupement de dzmMenuModel ; « Projet » est posé traduit par l\'hôte'),
    X(450448, 'rubrique = clé de regroupement de dzmMenuModel, traduite au site d\'affichage (DzmCtxMenu)'),
    X(450458, 'rubrique = clé de regroupement ; « Timeline » identique en anglais'),
    X(450469, 'rubrique = clé de regroupement de dzmMenuModel, traduite au site d\'affichage (DzmCtxMenu)'),
    X(450481,'rubrique comparée par l\'hôte (g.rub==="Affichage"), traduite au site d\'affichage'),
    X(450493, 'rubrique = clé de regroupement de dzmMenuModel, traduite au site d\'affichage (DzmCtxMenu)'),
]

# DZM_MENU_RUB : table id -> rubrique (valeurs de regroupement, voir DZM_MENU_ORDRE)
ENTREES += [X(p, 'rubrique = valeur de regroupement (DZM_MENU_ORDRE), traduite au site d\'affichage (DzmCtxMenu)')
            for p in (450526, 450541, 450558, 450575, 450598, 450618, 450640, 450660, 450684, 450705, 450726, 450748,
                      450770, 450790, 450814, 450839, 450854, 450869, 450888, 450964, 450980, 451094, 451116, 451226,
                      451366, 451390, 451414, 451439, 451463, 451484, 451504, 451524, 451546, 451576, 451599, 451621,
                      451648)]

ENTREES += [
    # dzmMenuRub : repli par section de raccourci (sections comparées de son-vfx-montage)
    X(451746, 'section de raccourci COMPARÉE (a.sec==="Audio", SVM_KEY_SECTIONS)'),
    X(451754, 'rubrique renvoyée = valeur de regroupement (DZM_MENU_ORDRE)'),
    X(451772, 'section de raccourci COMPARÉE (a.sec==="Affichage", SVM_KEY_SECTIONS)'),
    X(451784, 'rubrique renvoyée = valeur de regroupement (DZM_MENU_ORDRE)'),
    X(451796, 'rubrique renvoyée = valeur de regroupement (DZM_MENU_ORDRE)'),

    # DzmCtxMenu : l'en-tête de rubrique est le SITE D'AFFICHAGE (la valeur g.rub reste française)
    S(455080, '{className:"svm-menurub",children:g.rub}',
      '{className:"svm-menurub",children:g.rub==="Édition"?dzT("montage.menurub.edition"):g.rub==="Marqueurs"?'
      'dzT("montage.menurub.marqueurs"):g.rub==="Affichage"?dzT("montage.menurub.affichage"):g.rub==="Aide"?'
      'dzT("montage.menurub.aide"):g.rub}',
      {'montage.menurub.edition': ('Édition', 'Edit'),
       'montage.menurub.marqueurs': ('Marqueurs', 'Markers'),
       'montage.menurub.affichage': ('Affichage', 'View'),
       'montage.menurub.aide': ('Aide', 'Help')}),

    # DZM_KM_PRESETS : préréglage clavier Resolve
    X(456037, 'combo de touches enregistrée dans la keymap (analysée par svmComboCanon)'),
    X(456051, 'combo de touches enregistrée dans la keymap (analysée par svmComboCanon)'),

    # dzmClipPaste : notes de collage refusé
    L(460951, 'montage.collage.vide', "Presse-papiers vide — copiez d'abord un clip",
      'Clipboard empty — copy a clip first'),
    L(461100, 'montage.collage.version', "Presse-papiers d'une autre version", 'Clipboard from another version'),
    L(461816, 'montage.collage.sans_source', "Ce clip n'a pas de source (copié depuis la démo ?) — rien n'a été collé",
      'This clip has no source (copied from the demo?) — nothing was pasted'),
    S(462027, '"Aucune piste "+genre+" pour coller"',
      'dzT("montage.collage.aucune_piste",{genre:genre})',
      {'montage.collage.aucune_piste': ('Aucune piste {genre} pour coller', 'No {genre} track to paste into')}),
    S(462592, 'r.refus==="verrou"?"Piste "+String(r.track||tr).toUpperCase()+" verrouillée — rien n\'a été collé":"Rien n\'a été collé"',
      'r.refus==="verrou"?dzT("montage.collage.verrou",{piste:String(r.track||tr).toUpperCase()}):dzT("montage.collage.rien")',
      {'montage.collage.verrou': ("Piste {piste} verrouillée — rien n'a été collé", 'Track {piste} locked — nothing was pasted'),
       'montage.collage.rien': ("Rien n'a été collé", 'Nothing was pasted')}),

    # DZM_DIFF_RUB / DzmDiffView : comparaison de versions (libellés affichés ; la clé est rb[0])
    L(469149, 'montage.diff.ajoute', 'Ajouté', 'Added'),
    L(469158, 'montage.diff.ajoutes', 'Ajoutés', 'Added'),
    L(469180, 'montage.diff.supprime', 'Supprimé', 'Removed'),
    L(469191, 'montage.diff.supprimes', 'Supprimés', 'Removed'),
    L(469213, 'montage.diff.deplace', 'Déplacé', 'Moved'),
    L(469223, 'montage.diff.deplaces', 'Déplacés', 'Moved'),
    L(469250, 'montage.diff.rogne', 'Rogné', 'Trimmed'),
    L(469258, 'montage.diff.rognes', 'Rognés', 'Trimmed'),
    L(469279, 'montage.diff.modifie', 'Modifié', 'Changed'),
    L(469289, 'montage.diff.modifies', 'Modifiés', 'Changed'),
    X(469863, '« (source » identique en anglais'),
    S(470299, '"Comparer : « "+(o.nomA||"montage courant")+" » → « "+(o.nomB||"autre projet")+" »"',
      'dzT("montage.diff.titre",{a:o.nomA||dzT("montage.diff.courant"),b:o.nomB||dzT("montage.diff.autre")})',
      {'montage.diff.titre': ('Comparer : « {a} » → « {b} »', 'Compare: “{a}” → “{b}”'),
       'montage.diff.courant': ('montage courant', 'current edit'),
       'montage.diff.autre': ('autre projet', 'other project')}),
    L(471046, 'montage.diff.fermer_aide', 'Fermer la comparaison (Échap)', 'Close the comparison (Esc)'),
    L(471132, 'montage.mots.fermer', *_FERMER),

    # dzmSubsLabelOf : libellé enregistré
    X(477657, 'libellé ENREGISTRÉ dans le clip de sous-titre (label), tenu à l\'identique de subsLabelOf (subs.js)'),

    # dzmCutAt : découpe aux changements de plan (notes)
    L(481447, 'montage.decoupe.introuvable', 'Clip introuvable — rien à découper.', 'Clip not found — nothing to split.'),
    S(481561, '"Piste "+String(c.tr).toUpperCase()+" verrouillée — déverrouillez-la pour découper ce plan."',
      'dzT("montage.decoupe.verrou",{p:String(c.tr).toUpperCase()})',
      {'montage.decoupe.verrou': ('Piste {p} verrouillée — déverrouillez-la pour découper ce plan.',
                                  'Track {p} locked — unlock it to split this clip.')}),
    L(482251, 'montage.decoupe.aucune', 'Aucun changement de plan à découper dans ce clip.',
      'No scene change to split in this clip.'),
    S(482915, 'ps.length+" coupe"+(ps.length>1?"s":"")+" aux changements de plan"',
      '(ps.length>1?dzT("montage.decoupe.coupes.plusieurs",{n:ps.length}):dzT("montage.decoupe.coupes.un",{n:ps.length}))',
      {'montage.decoupe.coupes.un': ('{n} coupe aux changements de plan', '{n} cut at scene changes'),
       'montage.decoupe.coupes.plusieurs': ('{n} coupes aux changements de plan', '{n} cuts at scene changes')}),
]
