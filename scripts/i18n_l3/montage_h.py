"""t143 — montage_h : couche Montage (frontend/patches/montage.js), lignes 7800–8925 de la base. Couvre : la découpe d'un
épisode en scènes (dzmScenesPose : notes de refus et de réussite), les onglets et roues du panneau d'étalonnage
(DZM_GP_TABS, DZM_GP_ROUES), le détail d'un refus HTTP du panneau (dzmGpFetch), le panneau d'étalonnage DzmGradePanel
(roues, maîtres, courbes, masque, accord de couleur, copier / coller le grade, aperçu étalonné), les notes de copie et
collage du grade (dzmGpNfx, dzmGradeCopyDo, dzmGradePasteDo), les notes de la pastille de l'image étalonnée
(DZM_GL_NOTES, dzmGlBadge), l'apprentissage du bruit (dzmLearnRange, DzmNoiseLearn) et les raisons d'un refus du micro
de la voix off (dzmVoErr).

Gardés : « Scène n », titre d'un marqueur ENREGISTRÉ dans le projet ; « Voix off n » (dzmVoLabel), nom donné au clip de
la prise par addAsset, donc ENREGISTRÉ ; « Lift », « Gamma », « Gain », « + Point », « Rectangle », « Ellipse »,
« Auto », « Grade » et l'unité « dB » (identiques dans les deux langues). Pas touchés (hors contrôle, ce sont des
valeurs) : les ids d'onglet et de roue (« m », « lift »…), les formes de masque (« none », « rect », « ellipse »), les
codes de refus (« clip », « plage »…), les ids de note du serveur (« stab-non-analysee »…), l'extension « ogg ».
Traduits hors contrôle parce qu'affichés : la lettre « L » (largeur) du masque (W), les mots « vitesse »,
« stabilisation », « ajustement » de la pastille (à côté d'« étalonné », signalé).
Les phrases composées sont recomposées en une clé (S) ; un S sur deux lignes garde ses deux lignes. Le pluriel de
dzmGpNfx passe par deux clés .._un / .._plusieurs. « erreur réseau » et « erreur inconnue » reprennent la traduction
déjà posée (montage.commun.erreur_reseau, quick.avatar.inconnue) sous une clé montage.mots.*."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_RESEAU = ('erreur réseau', 'network error')
_RIEN_COPIER = ('Rien à copier : ni effet couleur ni masque sur ce plan',
                'Nothing to copy: no color effect and no mask on this clip')
_AUCUN_GRADE = ("Aucun grade copié (Copier le grade d'abord)", 'No grade copied (Copy grade first)')
_PLAGE_IO = ('Posez une plage I/O (I puis U) sur un passage de bruit seul',
             'Set an I/O range (I then U) on a noise-only passage')

ENTREES = [
    # dzmScenesPose : découper un épisode aux scènes (notes de refus et de réussite)
    L(484477, 'montage.decoupe.plan_introuvable', "Plan introuvable — l'épisode n'a pas été découpé.",
      'Clip not found — the episode was not split.'),
    S(484850, '"Piste "+String(c.tr).toUpperCase()+\r\n    " verrouillée — l\'épisode reste en un seul plan."',
      'dzT("montage.decoupe.piste_verrouillee",{piste:String(c.tr).toUpperCase()}\r\n    )',
      {'montage.decoupe.piste_verrouillee': ("Piste {piste} verrouillée — l'épisode reste en un seul plan.",
                                             'Track {piste} locked — the episode stays as a single clip.')}),
    L(485229, 'montage.decoupe.aucune_borne', 'Aucune borne de scène dans ce plan — il reste entier.',
      'No scene boundary in this clip — it stays whole.'),
    S(485720, '" Le son du plan ("+String(tw.tr).toUpperCase()+") n\'a pas la même vitesse ou le même point d\'entrée : il reste entier."',
      'dzT("montage.decoupe.son_decale",{piste:String(tw.tr).toUpperCase()})',
      {'montage.decoupe.son_decale': (
          " Le son du plan ({piste}) n'a pas la même vitesse ou le même point d'entrée : il reste entier.",
          " The clip's sound ({piste}) does not have the same speed or in point: it stays whole.")}),
    S(485933, '" Piste "+String(tw.tr).toUpperCase()+" verrouillée : le son du plan reste entier."',
      'dzT("montage.decoupe.son_verrouille",{piste:String(tw.tr).toUpperCase()})',
      {'montage.decoupe.son_verrouille': (" Piste {piste} verrouillée : le son du plan reste entier.",
                                          " Track {piste} locked: the clip's sound stays whole.")}),
    X(486233, 'titre du marqueur ENREGISTRÉ dans le projet (« Scène n »)'),
    S(486345, '"Épisode découpé en "+(r.n+1)+" plans, un par scène, avec un marqueur par scène — « Annuler » le rend en un seul plan."',
      'dzT("montage.decoupe.fait",{n:r.n+1})',
      {'montage.decoupe.fait': (
          'Épisode découpé en {n} plans, un par scène, avec un marqueur par scène — « Annuler » le rend en un seul plan.',
          'Episode split into {n} clips, one per scene, with one marker per scene — “Undo” turns it back into a single '
          'clip.')}),

    # DZM_GP_TABS / DZM_GP_ROUES : onglets de courbe et roues du panneau d'étalonnage
    L(503623, 'montage.etalonnage.onglet_maitre', 'Courbe maître : les trois canaux ensemble',
      'Master curve: all three channels together'),
    L(503677, 'montage.etalonnage.onglet_rouge', 'Courbe du canal rouge', 'Red channel curve'),
    L(503717, 'montage.etalonnage.onglet_vert', 'Courbe du canal vert', 'Green channel curve'),
    L(503750, 'montage.etalonnage.onglet_bleu', 'Courbe du canal bleu', 'Blue channel curve'),
    X(503801, 'identique dans les deux langues (Lift)'),
    L(503808, 'montage.etalonnage.ombres', 'Ombres (lift)', 'Shadows (lift)'),
    X(503841, 'identique dans les deux langues (Gamma)'),
    L(503849, 'montage.etalonnage.tons_moyens', 'Tons moyens (gamma)', 'Midtones (gamma)'),
    X(503885, 'identique dans les deux langues (Gain)'),
    L(503892, 'montage.etalonnage.hautes_lumieres', 'Hautes lumières (gain)', 'Highlights (gain)'),

    # dzmGpFetch : détail d'un refus HTTP (route absente)
    L(506452, 'montage.etalonnage.route_absente', ' — route absente de ce serveur (backend à relancer)',
      ' — route missing on this server (restart the backend)'),

    # DzmGradePanel : verrou, aperçu étalonné, roues et maîtres
    L(513306, 'montage.etalonnage.v1_verrouillee', 'Piste V1 verrouillée — déverrouillez-la pour étalonner ce plan',
      'Track V1 locked — unlock it to grade this clip'),
    S(514957, '"Aperçu étalonné indisponible : "+((e&&e.message)||"erreur réseau")',
      'dzT("montage.etalonnage.apercu_indispo",{e:(e&&e.message)||dzT("montage.mots.erreur_reseau")})',
      {'montage.etalonnage.apercu_indispo': ('Aperçu étalonné indisponible : {e}', 'Graded preview unavailable: {e}'),
       'montage.mots.erreur_reseau': _RESEAU}),
    S(516609, '"Roue "+w[1]', 'dzT("montage.etalonnage.roue",{nom:w[1]})',
      {'montage.etalonnage.roue': ('Roue {nom}', '{nom} wheel')}),
    S(516649, 'w[2]+" : glisser le point vers une teinte — double-clic : remise à zéro"',
      'dzT("montage.etalonnage.roue_aide",{nom:w[2]})',
      {'montage.etalonnage.roue_aide': ('{nom} : glisser le point vers une teinte — double-clic : remise à zéro',
                                        '{nom}: drag the point toward a hue — double-click: reset')}),
    S(517061, '"Maître "+w[1]+" : les trois canaux ensemble"', 'dzT("montage.etalonnage.maitre_aide",{nom:w[1]})',
      {'montage.etalonnage.maitre_aide': ('Maître {nom} : les trois canaux ensemble',
                                          'Master {nom}: all three channels together')}),
    S(517120, '"Maître "+w[1]', 'dzT("montage.etalonnage.maitre",{nom:w[1]})',
      {'montage.etalonnage.maitre': ('Maître {nom}', 'Master {nom}')}),

    # DzmGradePanel : courbe (clic dans le canvas), masque
    L(517928, 'montage.etalonnage.courbe_pleine_note', 'Courbe : 16 points au plus — double-cliquez un point pour le retirer.',
      'Curve: 16 points at most — double-click a point to remove it.'),
    L(519033, 'montage.etalonnage.masque_sans_effet', 'Le masque limite les effets du plan : ajoutez-en un',
      "The mask limits the clip's effects: add one"),
    L(519327, 'montage.etalonnage.aucun_masque', 'Aucun masque posé', 'No mask set'),
    L(519561, 'montage.etalonnage.choisir_forme', "Choisir d'abord Rectangle ou Ellipse", 'Choose Rectangle or Ellipse first'),

    # DzmGradePanel : accord de couleur (notes)
    L(520536, 'montage.etalonnage.accord_en_cours', 'Accord en cours…', 'Matching…'),
    L(520808, 'montage.etalonnage.accord_auto_en_cours', 'Accord automatique…', 'Auto matching…'),
    L(520830, 'montage.etalonnage.accord_prec_en_cours', 'Accord sur le plan précédent…', 'Matching to the previous clip…'),
    L(521027, 'montage.etalonnage.accord_plan_change', 'Accord refusé : le plan a changé pendant le calcul — relancez.',
      'Match refused: the clip changed during the computation — run it again.'),
    L(521159, 'montage.etalonnage.accord_illisible', 'Accord refusé : réponse illisible du serveur.',
      'Match refused: unreadable server response.'),
    L(521295, 'montage.etalonnage.accord_auto_pose', 'Accord automatique posé (effet « Accord couleur »).',
      'Auto match applied (“Color match” effect).'),
    L(521349, 'montage.etalonnage.accord_prec_pose', 'Plan accordé sur le précédent (effet « Accord couleur »).',
      'Clip matched to the previous one (“Color match” effect).'),
    S(521452, '"Accord refusé : "+((e&&e.message)||"erreur réseau")',
      'dzT("montage.etalonnage.accord_refuse",{e:(e&&e.message)||dzT("montage.mots.erreur_reseau")})',
      {'montage.etalonnage.accord_refuse': ('Accord refusé : {e}', 'Match refused: {e}'),
       'montage.mots.erreur_reseau': _RESEAU}),

    # DzmGradePanel : message de l'aperçu, rangées Roues / Courbes
    L(522038, 'montage.etalonnage.lecture', "Lecture : l'aperçu se rafraîchit à l'arrêt",
      'Playing: the preview refreshes when stopped'),
    L(522127, 'montage.etalonnage.calcul_apercu', "calcul de l'aperçu…", 'computing the preview…'),
    L(522173, 'montage.etalonnage.roues', 'Roues', 'Wheels'),
    L(522273, 'montage.etalonnage.courbes', 'Courbes', 'Curves'),
    L(522719, 'montage.etalonnage.courbe', 'Courbe', 'Curve', contexte=True),
    L(522755, 'montage.etalonnage.courbe_aide',
      'Cliquer : ajouter un point · glisser : déplacer · double-clic : retirer (extrémités fixes en x)',
      'Click: add a point · drag: move · double-click: remove (end points fixed in x)'),
    L(523075, 'montage.etalonnage.courbe_pleine', '16 points au plus : double-cliquer un point pour le retirer',
      '16 points at most: double-click a point to remove it'),
    L(523137, 'montage.etalonnage.ajouter_point',
      'Ajouter un point au milieu du plus grand écart (16 au plus) — ou cliquer dans la courbe',
      'Add a point in the middle of the largest gap (16 at most) — or click in the curve'),
    X(523336, 'identique dans les deux langues (+ Point)'),
    L(523450, 'montage.etalonnage.deja_plat', 'Courbe déjà à plat sur ce canal', 'Curve already flat on this channel'),
    L(523484, 'montage.etalonnage.remettre_plat', 'Remettre ce canal à plat (identité)',
      'Reset this channel to flat (identity)'),
    L(523593, 'montage.etalonnage.a_plat', 'À plat', 'Flat'),

    # DzmGradePanel : rangée Masque (formes, réglettes, inversion)
    L(523720, 'montage.etalonnage.masque', 'Masque', 'Mask'),
    L(523855, 'montage.etalonnage.aucun', 'Aucun', 'None'),
    L(523863, 'montage.etalonnage.retirer_masque', 'Retirer le masque : les effets couvrent tout le cadre',
      'Remove the mask: the effects cover the whole frame'),
    X(523942, 'identique dans les deux langues (Rectangle)'),
    L(523954, 'montage.etalonnage.masque_rect', "Masque rectangulaire : les effets du plan ne s'appliquent que dedans",
      "Rectangular mask: the clip's effects only apply inside"),
    X(524051, 'identique dans les deux langues (Ellipse)'),
    L(524061, 'montage.etalonnage.masque_ellipse', "Masque elliptique : les effets du plan ne s'appliquent que dedans",
      "Elliptical mask: the clip's effects only apply inside"),
    L(524158, 'montage.etalonnage.bord_gauche', 'Bord gauche du masque (% du cadre)', 'Mask left edge (% of frame)'),
    L(524213, 'montage.etalonnage.bord_haut', 'Bord haut du masque (% du cadre)', 'Mask top edge (% of frame)'),
    L(524266, 'montage.etalonnage.lettre_largeur', 'L', 'W'),
    L(524274, 'montage.etalonnage.largeur', 'Largeur du masque (% du cadre)', 'Mask width (% of frame)'),
    L(524325, 'montage.etalonnage.hauteur', 'Hauteur du masque (% du cadre)', 'Mask height (% of frame)'),
    L(524379, 'montage.etalonnage.adouc', 'Adouc.', 'Feather'),
    L(524391, 'montage.etalonnage.adouc_aide', 'Adoucissement du bord (0 à 50 % du petit côté de la forme)',
      "Edge feathering (0 to 50% of the shape's shorter side)"),
    L(524600, 'montage.etalonnage.inverser_aide', "Inverser : les effets s'appliquent HORS de la forme",
      'Invert: the effects apply OUTSIDE the shape'),
    L(524679, 'montage.etalonnage.inverser_masque', 'Inverser le masque', 'Invert the mask'),
    L(524800, 'montage.etalonnage.inverser', ' Inverser', ' Invert'),

    # DzmGradePanel : rangée Accord
    L(524838, 'montage.etalonnage.accord', 'Accord', 'Match'),
    L(525020, 'montage.etalonnage.accorder_prec_aide',
      "Accorder ce plan sur le plan précédent de V1 (pose ou remplace l'effet « Accord couleur »)",
      'Match this clip to the previous V1 clip (adds or replaces the “Color match” effect)'),
    L(525113, 'montage.etalonnage.aucun_prec', 'Aucun plan précédent sur V1 : rien à accorder',
      'No previous clip on V1: nothing to match'),
    L(525213, 'montage.etalonnage.accorder_prec', 'Accorder sur le plan précédent', 'Match to previous clip'),
    L(525351, 'montage.etalonnage.accord_auto_aide',
      "Accord automatique : neutralise la dominante et étire le contraste (pose ou remplace l'effet « Accord couleur »)",
      'Auto match: neutralizes the color cast and stretches the contrast (adds or replaces the “Color match” effect)'),
    X(525518, 'identique dans les deux langues (Auto)'),

    # DzmGradePanel : rangée Grade (copier / coller)
    X(525550, 'identique dans les deux langues (Grade)'),
    L(525702, 'montage.etalonnage.copier_aide', 'Copier le grade de ce plan : effets couleur et masque',
      "Copy this clip's grade: color effects and mask"),
    L(525758, 'montage.etalonnage.rien_a_copier', *_RIEN_COPIER),
    L(525932, 'montage.etalonnage.copier', 'Copier le grade', 'Copy grade'),
    L(526049, 'montage.etalonnage.coller_aide',
      'Coller le grade copié : remplace les effets couleur de ce plan, les autres restent',
      "Paste the copied grade: replaces this clip's color effects, the others stay"),
    L(526134, 'montage.etalonnage.aucun_grade', *_AUCUN_GRADE),
    L(526353, 'montage.etalonnage.coller', 'Coller le grade', 'Paste grade'),

    # DzmGradePanel : rangée Aperçu, titre du panneau
    L(526395, 'montage.etalonnage.apercu', 'Aperçu', 'Preview'),
    L(526492, 'montage.etalonnage.image_alt', 'Image étalonnée du plan', 'Graded image of the clip'),
    S(526524, '"Image étalonnée (la pile d\'effets du plan rendue par ffmpeg) à "+img.t+" s de source"',
      'dzT("montage.etalonnage.image_aide",{t:img.t})',
      {'montage.etalonnage.image_aide': ("Image étalonnée (la pile d'effets du plan rendue par ffmpeg) à {t} s de source",
                                         "Graded image (the clip's effect stack rendered by ffmpeg) at {t} s of source")}),
    L(526800, 'montage.etalonnage.titre', 'Étalonnage', 'Grading'),

    # dzmGpNfx, dzmGradeCopyDo, dzmGradePasteDo : notes du presse-papiers du grade
    S(530885, 'n+" effet"+(n>1?"s":"")',
      'dzT(n>1?"montage.etalonnage.effets_plusieurs":"montage.etalonnage.effets_un",{n:n})',
      {'montage.etalonnage.effets_un': ('{n} effet', '{n} effect'),
       'montage.etalonnage.effets_plusieurs': ('{n} effets', '{n} effects')}),
    L(531002, 'montage.etalonnage.rien_a_copier', *_RIEN_COPIER),
    L(531104, 'montage.etalonnage.copie_refusee', 'Copie refusée : stockage du navigateur indisponible.',
      'Copy refused: browser storage unavailable.'),
    S(531183, '"Grade copié ("+dzmGpNfx(g)+")"', 'dzT("montage.etalonnage.grade_copie",{effets:dzmGpNfx(g)})',
      {'montage.etalonnage.grade_copie': ('Grade copié ({effets})', 'Grade copied ({effets})')}),
    L(531309, 'montage.etalonnage.aucun_grade', *_AUCUN_GRADE),
    S(531400, '"Grade collé ("+dzmGpNfx(g)+")"', 'dzT("montage.etalonnage.grade_colle",{effets:dzmGpNfx(g)})',
      {'montage.etalonnage.grade_colle': ('Grade collé ({effets})', 'Grade pasted ({effets})')}),

    # DZM_GL_NOTES (le libellé ; l'id reste) et dzmGlBadge : pastille de l'image étalonnée du lecteur
    L(531947, 'montage.pastille.stab_non_analysee', 'stabilisation non analysée', 'stabilization not analyzed'),
    L(531995, 'montage.pastille.stab_trop_loin', 'stabilisation : trop loin dans la source',
      'stabilization: too far into the source'),
    L(544719, 'montage.pastille.etalonne', 'étalonné', 'graded'),
    L(544757, 'montage.pastille.vitesse', 'vitesse', 'speed'),
    L(544852, 'montage.pastille.stabilisation', 'stabilisation', 'stabilization'),
    L(544928, 'montage.pastille.ajustement', 'ajustement', 'adjustment'),

    # dzmLearnRange : refus de l'apprentissage du bruit (la note ; le code de refus reste)
    L(557892, 'montage.bruit.aucun_clip', 'Aucun clip audio sélectionné : rien à apprendre',
      'No audio clip selected: nothing to learn'),
    L(558134, 'montage.bruit.debut_illisible', "Ce clip audio n'a pas de début lisible : rien à apprendre",
      'This audio clip has no readable start: nothing to learn'),
    L(558256, 'montage.bruit.poser_plage', *_PLAGE_IO),
    L(558600, 'montage.bruit.trop_courte', 'Plage trop courte : il faut au moins 0,2 s de bruit seul (dans la source)',
      'Range too short: at least 0.2 s of noise only is needed (in the source)'),
    L(558719, 'montage.bruit.trop_longue', 'Plage trop longue : 30 s de bruit seul au plus (dans la source)',
      'Range too long: 30 s of noise only at most (in the source)'),
    L(558852, 'montage.bruit.hors_source',
      'La plage sort de la source de ce clip : posez-la sur un passage que la source contient',
      "The range goes outside this clip's source: set it on a passage the source contains"),

    # dzmVoLabel : nom du clip d'une prise de voix off
    X(560491, 'nom du clip de la prise (« Voix off n »), ENREGISTRÉ dans le projet par addAsset'),

    # DzmNoiseLearn : bouton Apprendre le bruit (title), notes, bouton Oublier, état
    L(565188, 'montage.bruit.demo', "Projet de démonstration : l'apprentissage du bruit est désactivé",
      'Demo project: noise learning is disabled'),
    L(565266, 'montage.bruit.mesure_en_cours', 'Mesure du bruit en cours…', 'Measuring the noise…'),
    L(565310, 'montage.bruit.poser_plage_apprendre',
      'Posez une plage I/O (I puis U) sur un passage de bruit seul, puis apprenez-le',
      'Set an I/O range (I then U) on a noise-only passage, then learn it'),
    S(565405, '"Apprendre le bruit — "+lr.note', 'dzT("montage.bruit.apprendre_refus",{raison:lr.note})',
      {'montage.bruit.apprendre_refus': ('Apprendre le bruit — {raison}', 'Learn noise — {raison}')}),
    S(565443, '"Apprendre le bruit sur la plage I/O ("+lr.a+"–"+lr.b+" s de source) : son niveau règle le plancher du débruiteur, "\r\n      +"et le rendu apprend son timbre"',
      'dzT("montage.bruit.apprendre_aide",{a:lr.a,b:lr.b}\r\n      )',
      {'montage.bruit.apprendre_aide': (
          'Apprendre le bruit sur la plage I/O ({a}–{b} s de source) : son niveau règle le plancher du débruiteur, et '
          'le rendu apprend son timbre',
          'Learn the noise on the I/O range ({a}–{b} s of source): its level sets the denoiser floor, and the render '
          'learns its timbre')}),
    L(565610, 'montage.bruit.musique_bouclee', " — musique bouclée : seul le plancher s'applique au rendu",
      ' — looped music: only the floor applies to the render'),
    L(565994, 'montage.bruit.plage_muette', 'Plage muette : rien à apprendre', 'Silent range: nothing to learn'),
    L(566096, 'montage.bruit.reponse_illisible', 'Apprentissage : réponse illisible du serveur',
      'Learning: unreadable server response'),
    S(566232, '"Bruit appris sur "+a+"–"+b+" s (source) : plancher "+nf+" dB"',
      'dzT("montage.bruit.appris_note",{a:a,b:b,nf:nf})',
      {'montage.bruit.appris_note': ('Bruit appris sur {a}–{b} s (source) : plancher {nf} dB',
                                     'Noise learned on {a}–{b} s (source): floor {nf} dB')}),
    S(566382, '"Apprentissage impossible : "+((e&&e.message)||"erreur réseau")',
      'dzT("montage.bruit.impossible",{e:(e&&e.message)||dzT("montage.mots.erreur_reseau")})',
      {'montage.bruit.impossible': ('Apprentissage impossible : {e}', 'Learning failed: {e}'),
       'montage.mots.erreur_reseau': _RESEAU}),
    L(566538, 'montage.bruit.oublie', 'Bruit appris oublié : le débruiteur reste, plancher automatique',
      'Learned noise forgotten: the denoiser stays, automatic floor'),
    L(566797, 'montage.bruit.mesure', 'Mesure…', 'Measuring…'),
    L(566807, 'montage.bruit.apprendre', 'Apprendre le bruit', 'Learn noise'),
    S(566936, '"Oublier le bruit appris ("+ap.a+"–"+ap.b+" s de source, plancher "+(apNf!==null?apNf+" dB":"automatique")+") — le débruiteur reste"',
      'dzT("montage.bruit.oublier_aide",{a:ap.a,b:ap.b,plancher:apNf!==null?apNf+" dB":dzT("montage.bruit.automatique")})',
      {'montage.bruit.oublier_aide': ('Oublier le bruit appris ({a}–{b} s de source, plancher {plancher}) — le débruiteur reste',
                                      'Forget the learned noise ({a}–{b} s of source, floor {plancher}) — the denoiser stays'),
       'montage.bruit.automatique': ('automatique', 'automatic')}),
    X(567022, 'unité identique dans les deux langues ( dB), reste dans le code de remplacement'),
    L(567079, 'montage.bruit.rien_a_oublier', 'Aucun bruit appris sur ce clip : rien à oublier',
      'No learned noise on this clip: nothing to forget'),
    L(567162, 'montage.bruit.oublier', 'Oublier', 'Forget'),
    S(567265, '"appris "+ap.a+"–"+ap.b+" s · "+(apNf!==null?apNf+" dB":"auto")',
      'dzT("montage.bruit.appris_etat",{a:ap.a,b:ap.b,plancher:apNf!==null?apNf+" dB":"auto"})',
      {'montage.bruit.appris_etat': ('appris {a}–{b} s · {plancher}', 'learned {a}–{b} s · {plancher}')}),
    L(567329, 'montage.bruit.aucun_appris', 'aucun bruit appris', 'no learned noise'),

    # dzmVoErr : raison d'un refus du micro (voix off)
    L(568246, 'montage.micro.acces_refuse', 'accès au micro refusé', 'microphone access denied'),
    L(568360, 'montage.micro.aucun', 'aucun micro détecté', 'no microphone detected'),
    L(568442, 'montage.micro.occupe', 'micro occupé par une autre application', 'microphone in use by another application'),
    L(568584, 'montage.mots.erreur_inconnue', 'erreur inconnue', 'unknown error', contexte=True),
]
