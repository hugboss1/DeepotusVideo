"""t144 — vfx : la couche entière frontend/patches/vfxrack.js (window.DzVfx), le rack d'effets vidéo monté dans
l'inspecteur du Montage ET dans le nœud Effects du Studio (version `inline`) — erreurs de vfxJson/vfxPost (montées
par fireNote au détourage), catalogue local de secours VFX_STATIC (libellés) et VFX_META (phrases d'aide), courbes de
rampe VFX_EASES (libellé de l'option), éditeur de Bézier VfxBezier, catégories de repli VFX_CATS_FB, bornes de repli
VFX_PBOUNDS (libellés), vfxNormCat (onglets « Tous » / « Autres »), vfxSummary, VfxThumb (pastilles de repli),
VfxAlert (bandeau de panne), VfxPanel (panneau d'effets), VfxBounds (bornes t0/t1 + rampe), VfxStack (pile d'effets,
détourage du sujet).

Libellés d'effets (VFX_STATIC.label, e.label, d.label) : seulement AFFICHÉS — tuiles, notes, aria-label, fantôme du
glisser. Le seul passage hors de la couche est la charge « dz-vfx » du glisser, et l'hôte (vfxAddTo, couche sonvfx)
RETIRE la clé `label` avant de ranger l'effet dans le clip ; le nœud Effects du Studio ne reçoit que onPick(type, eff)
sans libellé. Ils sont donc traduits. Les ids (type, catégorie, preset, valeur d'ease) ne le sont jamais.

Gardés : les noms d'effets identiques en anglais (Glitch, Halation, Bloom / Glow…), « Vignette », « Angle »,
« Format » et « LUT .cube » (identiques dans les deux langues), les clés d'URL de /api/effects/preview (type=,
source=, matte=), les valeurs de préréglage par défaut (« duotone ») et la valeur de menu « bezier » (comparées).
Les VFX_STATIC / VFX_EASES traduits sont évalués au chargement de la couche : dzT (dz-i18n.js) est chargé AVANT le
bundle, la langue est donc connue. Positions = base ecf945e4 (CRLF)."""
from outils import L, S, X

CIBLE = "vfxrack"

FRAGMENTS = {}

ENTREES = [
    # vfxJson / vfxPost : erreur levée, montée par fireNote (« Détourage : … »)
    L(4301, 'vfx.erreur.non_json', 'réponse non JSON', 'non-JSON response'),
    L(4782, 'vfx.erreur.non_json', 'réponse non JSON', 'non-JSON response'),

    # VFX_STATIC : catalogue local de secours — libellés affichés (l'hôte retire `label` avant de stocker)
    X(6155, 'identique dans les deux langues'),
    L(6338, 'vfx.effet.colorize', 'Colorisation', 'Colorize'),
    L(6521, 'vfx.effet.gradient', 'Dégradé', 'Gradient'),
    L(6594, 'vfx.effet.grain', 'Grain film', 'Film grain'),
    X(6649, 'identique dans les deux langues'),
    L(6700, 'vfx.effet.chroma', 'Aberration chromatique', 'Chromatic aberration'),
    X(6765, 'identique dans les deux langues'),
    X(6813, 'identique dans les deux langues'),
    X(6870, 'identique dans les deux langues'),
    X(6924, 'identique dans les deux langues'),
    L(6985, 'vfx.effet.letterbox', 'Letterbox ciné', 'Cinema letterbox'),
    X(7039, 'identique dans les deux langues'),
    L(7091, 'vfx.effet.sharpen', 'Netteté', 'Sharpen'),
    L(7139, 'vfx.effet.blur', 'Flou', 'Blur'),
    X(7186, 'identique dans les deux langues'),
    X(7244, 'identique dans les deux langues'),
    X(7294, 'identique dans les deux langues'),
    L(7357, 'vfx.effet.mirror', 'Miroir', 'Mirror'),
    L(7395, 'vfx.effet.invert', 'Négatif', 'Invert'),

    # VFX_META : phrase d'aide par effet (title des tuiles, corps du module ; la recherche y cherche aussi)
    L(7616, 'vfx.aide.grade', 'Étalonnage cinéma — 10 rendus, du teal & orange au noir contrasté.', 'Cinema grade — 10 looks, from teal & orange to high-contrast noir.'),
    L(7719, 'vfx.aide.colorize', 'Teinte unique : sépia, N&B, duotone, alerte rouge, or.', 'Single tint: sepia, B&W, duotone, red alert, gold.'),
    L(7810, 'vfx.aide.gradient', "Dégradé de deux couleurs fusionné sur l'image.", 'Two-color gradient blended over the image.'),
    L(7886, 'vfx.aide.vhs', 'Bande usée : lignes déplacées, bruit, chroma qui bave.', 'Worn tape: shifted lines, noise, bleeding chroma.'),
    L(7974, 'vfx.aide.oldfilm', 'Pellicule fatiguée : poussières, sautes, vignettage.', 'Tired film stock: dust, jumps, vignetting.'),
    L(8062, 'vfx.aide.scanlines', "Lignes de balayage d'un tube cathodique.", 'Scan lines of a cathode-ray tube.'),
    L(8134, 'vfx.aide.grain', "Grain argentique — de la texture sans salir l'image.", 'Film grain — texture without muddying the image.'),
    L(8221, 'vfx.aide.pixelate', 'Mosaïque — gros pixels, façon écran de 1998.', 'Mosaic — big pixels, 1998-screen style.'),
    L(8299, 'vfx.aide.bloom', 'Les hautes lumières débordent et rayonnent.', 'Highlights spill over and glow.'),
    L(8379, 'vfx.aide.halation', 'Halo chaud autour des sources vives, comme sur pellicule.', 'Warm halo around bright sources, like on film.'),
    L(8473, 'vfx.aide.vignette', 'Bords assombris : le regard va au centre.', 'Darkened edges: the eye goes to the center.'),
    L(8549, 'vfx.aide.dreamy', 'Voile doux — portraits, souvenirs, rêve.', 'Soft haze — portraits, memories, dreams.'),
    L(8624, 'vfx.aide.chroma', 'Franges colorées sur les bords, comme un objectif bon marché.', 'Colored fringes on the edges, like a cheap lens.'),
    L(8718, 'vfx.aide.blur', "Flou d'ensemble — arrière-plan ou transition.", 'Overall blur — background or transition.'),
    L(8799, 'vfx.aide.sharpen', 'Accentue les contours — à doser, ça crie vite.', 'Sharpens edges — go easy, it gets loud fast.'),
    L(8880, 'vfx.aide.glitch', 'Décrochages numériques, blocs déplacés.', 'Digital dropouts, shifted blocks.'),
    L(8955, 'vfx.aide.shake', "Caméra à l'épaule — impact, panique, course.", 'Handheld camera — impact, panic, running.'),
    L(9036, 'vfx.aide.mirror', "Symétrie verticale de l'image.", 'Vertical symmetry of the image.'),
    L(9103, 'vfx.aide.invert', 'Négatif — inversion complète des valeurs.', 'Negative — full inversion of values.'),
    L(9180, 'vfx.aide.letterbox', 'Bandes noires : le format scope, tout de suite.', 'Black bars: scope format, instantly.'),

    # VFX_EASES : libellé de l'option (o[1]) ; la valeur o[0] (nom d'ease du moteur) n'est pas touchée
    L(9418, 'vfx.courbe.douce', 'douce', 'smooth'),
    L(9437, 'vfx.courbe.lineaire', 'linéaire', 'linear'),
    L(9459, 'vfx.courbe.acceleree', 'accélérée', 'ease in'),
    L(9487, 'vfx.courbe.freinee', 'freinée', 'ease out'),
    L(9511, 'vfx.courbe.douce_2_sens', 'douce (2 sens)', 'ease in-out'),
    L(9546, 'vfx.courbe.sinus', 'sinus', 'sine'),
    L(9573, 'vfx.courbe.anticipation', 'anticipation', 'anticipate'),
    L(9602, 'vfx.courbe.depassement', 'dépassement', 'overshoot'),
    L(9636, 'vfx.courbe.retour', 'retour', 'back'),
    L(9663, 'vfx.courbe.rebond', 'rebond', 'bounce'),
    L(9882, 'vfx.courbe.main', 'courbe à la main…', 'hand-drawn curve…'),

    # VfxBezier : éditeur de courbe
    S(12739, '"Poignée "+(i+1)', 'dzT("vfx.bezier.poignee",{n:i+1})',
      {'vfx.bezier.poignee': ('Poignée {n}', 'Handle {n}')}),
    L(13759, 'vfx.bezier.courbe', 'Courbe de la rampe', 'Ramp curve'),
    L(14297, 'vfx.bezier.p1_temps', 'Poignée 1 — temps', 'Handle 1 — time'),
    L(14326, 'vfx.bezier.p1_intensite', 'Poignée 1 — intensité', 'Handle 1 — strength'),
    L(14367, 'vfx.bezier.p2_temps', 'Poignée 2 — temps', 'Handle 2 — time'),
    L(14396, 'vfx.bezier.p2_intensite', 'Poignée 2 — intensité', 'Handle 2 — strength'),

    # VFX_CATS_FB : libellés des catégories de repli (l'id, c[0], reste)
    L(14725, 'vfx.cat.couleur', 'Couleur', 'Color'),
    L(14745, 'vfx.cat.retro', 'Rétro', 'Retro'),
    L(14765, 'vfx.cat.lumiere', 'Lumière', 'Light'),
    L(14791, 'vfx.cat.optique', 'Optique', 'Optical'),
    L(14815, 'vfx.cat.mouvement', 'Mouvement', 'Motion'),
    L(14837, 'vfx.cat.cadre', 'Cadre', 'Frame'),

    # VFX_PBOUNDS : libellés de repli des paramètres (les bornes du backend gagnent)
    L(15073, 'vfx.param.intensite', 'Intensité', 'Strength'),
    L(15151, 'vfx.param.vitesse', 'Vitesse', 'Speed'),
    X(15227, 'identique dans les deux langues'),
    L(15303, 'vfx.param.opacite', 'Opacité', 'Opacity'),
    L(15376, 'vfx.param.centre_x', 'Centre X', 'Center X'),
    L(15450, 'vfx.param.centre_y', 'Centre Y', 'Center Y'),
    L(15510, 'vfx.param.couleur_1', 'Couleur 1', 'Color 1'),
    L(15562, 'vfx.param.couleur_2', 'Couleur 2', 'Color 2'),
    L(15636, 'vfx.param.fusion', 'Fusion', 'Blend'),
    X(15730, 'identique dans les deux langues'),
    L(15788, 'vfx.commun.prereglage', 'Préréglage', 'Preset'),
    X(15834, 'identique dans les deux langues'),

    # vfxNormCat : onglets « Autres » / « Tous » (libellés ; les ids autres/tous restent)
    L(17463, 'vfx.commun.autres', 'Autres', 'Other'),
    L(17485, 'vfx.commun.autres', 'Autres', 'Other'),
    L(17614, 'vfx.commun.tous', 'Tous', 'All'),

    # vfxDefaultsFor : préréglage par défaut, valeur envoyée au moteur
    X(23964, 'valeur de préréglage (envoyée au moteur, comparée par indexOf)'),

    # vfxSummary : résumé d'un effet replié
    L(24949, 'vfx.resume.sans_reglage', 'sans réglage', 'no settings'),

    # vfxPreviewUrl : clés de la requête /api/effects/preview
    X(25566, 'clé de requête envoyée au serveur'),
    X(25885, 'clé de requête envoyée au serveur'),
    X(26122, 'clé de requête envoyée au serveur'),

    # VfxThumb : pastilles de repli
    S(30032, '"Aperçu indisponible — ni /api/effects/preview ni /effect-thumbs "+\r\n        "ne rendent d\'image pour cet effet."',
      'dzT("vfx.vignette.indisponible")',
      {'vfx.vignette.indisponible': ("Aperçu indisponible — ni /api/effects/preview ni /effect-thumbs ne rendent d'image pour cet effet.",
                                     'Preview unavailable — neither /api/effects/preview nor /effect-thumbs returns an image for this effect.')}),
    L(30163, 'vfx.vignette.apercu_off', 'aperçu —', 'preview —'),
    S(30244, '"Aperçu générique — /api/effects/preview (rendu sur VOTRE plan) "+\r\n          "n\'est pas disponible ; ceci est la vignette de référence de l\'effet."',
      'dzT("vfx.vignette.generique")',
      {'vfx.vignette.generique': ("Aperçu générique — /api/effects/preview (rendu sur VOTRE plan) n'est pas disponible ; ceci est la vignette de référence de l'effet.",
                                  "Generic preview — /api/effects/preview (rendered on YOUR shot) is unavailable; this is the effect's reference thumbnail.")}),
    L(30412, 'vfx.vignette.gen', 'gén.', 'gen.'),

    # VfxAlert : bandeau de panne du service d'effets
    L(31943, 'vfx.alerte.tentative', 'Nouvelle tentative en cours…', 'Retrying now…'),
    S(31980, '"Reprise automatique — nouvelle tentative dans "+left+" s."',
      'dzT("vfx.alerte.reprise",{n:left})',
      {'vfx.alerte.reprise': ('Reprise automatique — nouvelle tentative dans {n} s.', 'Automatic recovery — retrying in {n} s.')}),
    S(32204, '"Ceci n\'est PAS le rack complet : liste de secours locale ("+n+" effets, "+\r\n     "posables), sans vignette rendue sur votre plan, sans les préréglages "+\r\n     "ni les bornes du moteur."',
      'dzT("vfx.alerte.secours",{n:n})',
      {'vfx.alerte.secours': ("Ceci n'est PAS le rack complet : liste de secours locale ({n} effets, posables), sans vignette rendue sur votre plan, sans les préréglages ni les bornes du moteur.",
                              'This is NOT the full rack: local fallback list ({n} effects, usable), with no thumbnail rendered on your shot, and without the engine presets or bounds.')}),
    S(32398, '"Les "+n+" effets ci-dessous datent d\'avant la panne et restent posables, "+\r\n     "mais AUCUNE vignette ne peut plus être rendue sur votre plan."',
      'dzT("vfx.alerte.avant_panne",{n:n})',
      {'vfx.alerte.avant_panne': ("Les {n} effets ci-dessous datent d'avant la panne et restent posables, mais AUCUNE vignette ne peut plus être rendue sur votre plan.",
                                  'The {n} effects below date from before the outage and can still be applied, but NO thumbnail can be rendered on your shot any more.')}),
    L(32842, 'vfx.alerte.titre', "Service d'effets injoignable — le backend ne répond pas.", 'Effects service unreachable — the backend is not responding.'),
    S(32969, '"/api/effects/catalog et /api/effects/preview sont muets sur "+\r\n        "127.0.0.1:8765. "+what+" Relancez DeepotusVideoGen ; le rack se "+\r\n        "remplira tout seul, sans rouvrir ce panneau."',
      'dzT("vfx.alerte.detail",{quoi:what})',
      {'vfx.alerte.detail': ('/api/effects/catalog et /api/effects/preview sont muets sur 127.0.0.1:8765. {quoi} Relancez DeepotusVideoGen ; le rack se remplira tout seul, sans rouvrir ce panneau.',
                             '/api/effects/catalog and /api/effects/preview are silent on 127.0.0.1:8765. {quoi} Restart DeepotusVideoGen; the rack will fill itself, without reopening this panel.')}),
    L(33327, 'vfx.alerte.reessayer_aide', 'Redemander /api/effects/catalog immédiatement', 'Request /api/effects/catalog again now'),
    L(33412, 'vfx.alerte.reessayer', 'Réessayer maintenant', 'Retry now'),

    # VfxPanel : panneau d'effets
    L(35090, 'vfx.commun.tous', 'Tous', 'All'),
    S(36159, '"« "+e.label+" » posé sur le clip — réglez-le dans la pile."',
      'dzT("vfx.panneau.pose",{nom:e.label})',
      {'vfx.panneau.pose': ('« {nom} » posé sur le clip — réglez-le dans la pile.', '“{nom}” applied to the clip — adjust it in the stack.')}),
    L(38254, 'vfx.tuile.aide_suite', '\n\nClic : poser · glisser sur un clip · F : favori', '\n\nClick: apply · drag onto a clip · F: favorite'),
    L(38319, 'vfx.tuile.aide', 'Clic : poser · glisser sur un clip · F : favori', 'Click: apply · drag onto a clip · F: favorite'),
    L(38820, 'vfx.tuile.retirer_fav', 'Retirer des favoris (F)', 'Remove from favorites (F)'),
    L(38846, 'vfx.tuile.ajouter_fav', 'Ajouter aux favoris (F)', 'Add to favorites (F)'),
    L(38901, 'vfx.tuile.retirer_fav_nom', 'Retirer des favoris : ', 'Remove from favorites: '),
    L(38926, 'vfx.tuile.ajouter_fav_nom', 'Ajouter aux favoris : ', 'Add to favorites: '),
    S(39136, '"Déjà dans la pile de ce clip ("+n+")"', 'dzT("vfx.tuile.deja",{n:n})',
      {'vfx.tuile.deja': ('Déjà dans la pile de ce clip ({n})', 'Already in this clip\'s stack ({n})')}),
    S(39580, '"Aucun effet pour « "+qn+" »."', 'dzT("vfx.panneau.aucun_pour",{q:qn})',
      {'vfx.panneau.aucun_pour': ('Aucun effet pour « {q} ».', 'No effect for “{q}”.')}),
    L(39635, 'vfx.panneau.aucun_favori', "Aucun effet favori pour l'instant.", 'No favorite effects yet.'),
    L(39684, 'vfx.panneau.aucun_categorie', 'Aucun effet dans cette catégorie.', 'No effects in this category.'),
    L(39825, 'vfx.panneau.effacer_recherche', 'Effacer la recherche', 'Clear search'),
    L(39932, 'vfx.panneau.favori_aide', "Survolez un effet et cliquez ★ (ou touche F) pour l'épingler ici.", 'Hover an effect and click ★ (or press F) to pin it here.'),
    L(40151, 'vfx.panneau.src_moteur', 'catalogue moteur', 'engine catalog'),
    L(40196, 'vfx.panneau.src_montage', 'catalogue Montage', 'Montage catalog'),
    L(40216, 'vfx.panneau.src_local', 'catalogue local (backend muet)', 'local catalog (backend silent)'),
    L(40431, 'vfx.panneau.aria', "Panneau d'effets vidéo", 'Video effects panel'),
    L(40583, 'vfx.panneau.titre', 'Effets', 'Effects'),
    L(40757, 'vfx.panneau.sur_plan_aide', 'Les vignettes sont rendues sur CE plan', 'Thumbnails are rendered on THIS shot'),
    S(40817, '"sur « "+clip.label+" »"', 'dzT("vfx.panneau.sur_plan",{nom:clip.label})',
      {'vfx.panneau.sur_plan': ('sur « {nom} »', 'on “{nom}”')}),
    L(40935, 'vfx.panneau.fermer', 'Fermer (Échap)', 'Close (Esc)'),
    L(40965, 'vfx.panneau.fermer_aria', "Fermer le panneau d'effets", 'Close the effects panel'),
    L(41262, 'vfx.panneau.rechercher', 'Rechercher un effet…', 'Search effects…'),
    L(41298, 'vfx.panneau.rechercher_aria', 'Rechercher un effet', 'Search effects'),
    S(41808, '"Favoris ("+(counts.fav||0)+")"', 'dzT("vfx.panneau.favoris_n",{n:counts.fav||0})',
      {'vfx.panneau.favoris_n': ('Favoris ({n})', 'Favorites ({n})')}),
    # pied du panneau : raccourcis (touches en <kbd>, texte autour)
    L(42292, 'vfx.pied.clic', 'clic', 'click'),
    L(42308, 'vfx.pied.choisir', ' choisir · ', ' choose · '),
    L(42322, 'vfx.pied.poser', ' poser · ', ' apply · '),
    L(42378, 'vfx.pied.glisser', 'glisser', 'drag'),
    L(42412, 'vfx.pied.sur_clip', ' sur un clip · ', ' onto a clip · '),
    L(42468, 'vfx.pied.favori', ' favori · ', ' favorite · '),
    L(42519, 'vfx.pied.recherche', ' recherche', ' search'),
    L(42583, 'vfx.pied.origine', "Origine du catalogue d'effets", 'Source of the effects catalog'),
    L(42921, 'vfx.pied.reessayer_aide', 'Redemander les vignettes à /api/effects/preview', 'Request the thumbnails from /api/effects/preview again'),
    L(43081, 'vfx.pied.reessayer', 'Réessayer les aperçus', 'Retry previews'),

    # VfxBounds : bornes t0/t1 + rampe
    L(44074, 'vfx.bornes.tout_plan_aide', "Repasser l'effet sur tout le plan", 'Apply the effect to the whole shot again'),
    L(44120, 'vfx.bornes.limiter_aide', "Limiter l'effet à un intervalle du plan (t0 → t1), avec rampe", 'Limit the effect to a range of the shot (t0 → t1), with a ramp'),
    L(44391, 'vfx.bornes.titre', 'Bornes temporelles', 'Time bounds'),
    L(44507, 'vfx.bornes.tout_plan', 'tout le plan', 'whole shot'),
    L(44691, 'vfx.bornes.debut', 'Début', 'Start'),
    L(44830, 'vfx.bornes.debut_aria', "Début de l'effet (s)", 'Effect start (s)'),
    L(45097, 'vfx.bornes.debut_precis', 'Début précis (s)', 'Exact start (s)'),
    L(45438, 'vfx.bornes.fin', 'Fin', 'End'),
    L(45575, 'vfx.bornes.fin_aria', "Fin de l'effet (s)", 'Effect end (s)'),
    L(45846, 'vfx.bornes.fin_precise', 'Fin précise (s)', 'Exact end (s)'),
    L(46190, 'vfx.bornes.rampe_entree', 'Rampe entrée', 'Ramp in'),
    L(46306, 'vfx.bornes.rampe_entree_duree', "Durée de la rampe d'entrée (s)", 'Ramp-in duration (s)'),
    X(46595, "valeur de menu comparée (e.target.value===\"bezier\")"),
    L(46653, 'vfx.bornes.courbe_entree', "Courbe de la rampe d'entrée", 'Ramp-in curve'),
    L(47056, 'vfx.bornes.courbe_entree', "Courbe de la rampe d'entrée", 'Ramp-in curve'),
    L(47251, 'vfx.bornes.rampe_sortie', 'Rampe sortie', 'Ramp out'),
    L(47367, 'vfx.bornes.rampe_sortie_duree', 'Durée de la rampe de sortie (s)', 'Ramp-out duration (s)'),
    X(47659, "valeur de menu comparée (e.target.value===\"bezier\")"),
    L(47718, 'vfx.bornes.courbe_sortie', 'Courbe de la rampe de sortie', 'Ramp-out curve'),
    L(48126, 'vfx.bornes.courbe_sortie', 'Courbe de la rampe de sortie', 'Ramp-out curve'),
    L(48513, 'vfx.bornes.note_shake', 'Camera shake : la rampe règle la FORCE de la secousse, de 0 au réglage choisi.', 'Camera shake: the ramp sets the STRENGTH of the shake, from 0 to the chosen setting.'),
    L(48686, 'vfx.bornes.note_shakezoom', "Secousse + zoom : entrée et sortie franches — le zoom sauterait s'il rampait.", 'Shake + zoom: hard in and out — the zoom would jump if it ramped.'),
    L(48835, 'vfx.bornes.note_hors', "Hors de l'intervalle, le plan reste intact.", 'Outside the range, the shot stays untouched.'),

    # VfxStack : pile d'effets du clip
    S(50140, '"« "+ce(f&&f.type).label+" » retiré de la pile."', 'dzT("vfx.pile.retire",{nom:ce(f&&f.type).label})',
      {'vfx.pile.retire': ('« {nom} » retiré de la pile.', '“{nom}” removed from the stack.')}),
    L(50730, 'vfx.pile.avant_note', 'Avant : toute la pile est contournée (le rendu ignore ces effets).', 'Before: the whole stack is bypassed (the render ignores these effects).'),
    L(50807, 'vfx.pile.apres_note', 'Après : la pile est réactivée.', 'After: the stack is re-enabled.'),
    L(50927, 'vfx.pile.videe', 'Pile vidée.', 'Stack cleared.'),
    X(51348, 'valeur de préréglage (comparée p===cur)'),
    L(51479, 'vfx.commun.prereglage', 'Préréglage', 'Preset'),
    S(51715, '"Préréglage « "+p+" »"', 'dzT("vfx.pile.prereglage_nom",{nom:p})',
      {'vfx.pile.prereglage_nom': ('Préréglage « {nom} »', 'Preset “{nom}”')}),
    L(52584, 'vfx.pile.lut_aide', "Nom d'un fichier .cube déposé dans le dossier LUT", 'Name of a .cube file placed in the LUT folder'),
    # détourage du sujet (BiRefNet, fal)
    L(55957, 'vfx.matte.devis_indisponible', 'devis indisponible', 'quote unavailable'),
    L(56137, 'vfx.matte.devis_indisponible', 'devis indisponible', 'quote unavailable'),
    L(56676, 'vfx.matte.sujet_detoure', 'Sujet détouré : ', 'Subject cut out: '),
    L(56826, 'vfx.matte.detourage_err', 'Détourage : ', 'Cutout: '),
    L(56978, 'vfx.matte.detourage_err', 'Détourage : ', 'Cutout: '),
    L(57096, 'vfx.matte.detourage_err', 'Détourage : ', 'Cutout: '),
    L(57438, 'vfx.matte.sujet_detoure', 'Sujet détouré : ', 'Subject cut out: '),
    L(57468, 'vfx.matte.sujet_non_detoure', 'Sujet non détouré', 'Subject not cut out'),
    L(57581, 'vfx.matte.modele', 'Modèle de détourage', 'Cutout model'),
    L(57933, 'vfx.matte.bouton_aide', 'BiRefNet vidéo via fal — prix non affiché par fal : à lire sur le tableau de bord après le tir', 'BiRefNet video via fal — price not shown by fal: check the dashboard after the run'),
    L(58090, 'vfx.matte.en_cours', 'détourage…', 'cutting out…'),
    L(58108, 'vfx.matte.confirmer', 'Confirmer le détourage', 'Confirm the cutout'),
    L(58145, 'vfx.matte.redetourer', 'Redétourer', 'Cut out again'),
    L(58158, 'vfx.matte.detourer', 'Détourer (fal)', 'Cut out (fal)'),
    L(58278, 'vfx.matte.retirer', 'retirer', 'remove'),
    L(58352, 'vfx.matte.devis', 'devis : ', 'quote: '),
    L(58435, 'vfx.matte.second_clic', ' · un second clic lance le détourage', ' · a second click starts the cutout'),
    # rangée d'un effet de la pile
    S(58989, '"Déplier les réglages de « "+d.label+" »"', 'dzT("vfx.pile.deplier",{nom:d.label})',
      {'vfx.pile.deplier': ('Déplier les réglages de « {nom} »', 'Expand the settings of “{nom}”')}),
    S(59576, '"Actif de "+vfxSec(f.t0)+" à "+vfxSec(f.t1)+" — "+vfxSummary(f,d)',
      'dzT("vfx.pile.actif",{t0:vfxSec(f.t0),t1:vfxSec(f.t1),resume:vfxSummary(f,d)})',
      {'vfx.pile.actif': ('Actif de {t0} à {t1} — {resume}', 'Active from {t0} to {t1} — {resume}')}),
    L(59956, 'vfx.pile.monter', 'Monter dans la pile', 'Move up the stack'),
    S(59991, '"Monter « "+d.label+" »"', 'dzT("vfx.pile.monter_nom",{nom:d.label})',
      {'vfx.pile.monter_nom': ('Monter « {nom} »', 'Move “{nom}” up')}),
    L(60171, 'vfx.pile.descendre', 'Descendre dans la pile', 'Move down the stack'),
    S(60209, '"Descendre « "+d.label+" »"', 'dzT("vfx.pile.descendre_nom",{nom:d.label})',
      {'vfx.pile.descendre_nom': ('Descendre « {nom} »', 'Move “{nom}” down')}),
    L(60601, 'vfx.pile.derriere_aide', 'Derrière le sujet détouré — clic : devant', 'Behind the cut-out subject — click: in front'),
    L(60645, 'vfx.pile.devant_aide', 'Devant le sujet — clic : derrière', 'In front of the subject — click: behind'),
    L(60721, 'vfx.pile.passer_devant', 'Passer devant le sujet : ', 'Move in front of the subject: '),
    L(60749, 'vfx.pile.passer_derriere', 'Passer derrière le sujet : ', 'Move behind the subject: '),
    L(60902, 'vfx.pile.derriere', 'derrière', 'behind'),
    L(60913, 'vfx.pile.devant', 'devant', 'in front'),
    L(61081, 'vfx.pile.reactiver_aide', "Réactiver — l'effet repart au rendu", 'Re-enable — the effect goes back into the render'),
    L(61133, 'vfx.pile.contourner_aide', "Contourner — l'effet reste dans la pile mais sort du rendu", 'Bypass — the effect stays in the stack but leaves the render'),
    L(61224, 'vfx.pile.reactiver', 'Réactiver ', 'Re-enable '),
    L(61237, 'vfx.pile.contourner', 'Contourner ', 'Bypass '),
    L(61403, 'vfx.pile.retirer', 'Retirer de la pile', 'Remove from the stack'),
    S(61437, '"Retirer « "+d.label+" »"', 'dzT("vfx.pile.retirer_nom",{nom:d.label})',
      {'vfx.pile.retirer_nom': ('Retirer « {nom} »', 'Remove “{nom}”')}),
    L(61847, 'vfx.pile.sans_reglage', "Cet effet n'a aucun réglage — il s'applique tel quel.", 'This effect has no settings — it applies as is.'),
    # en-tête et pied de la pile
    L(62204, 'vfx.pile.titre', "Pile d'effets", 'Effect stack'),
    L(62317, 'vfx.pile.vide', 'vide', 'empty'),
    L(62403, 'vfx.pile.ab_aria', 'Comparer avant / après', 'Compare before / after'),
    L(62565, 'vfx.pile.avant_aide', 'Avant — toute la pile est contournée', 'Before — the whole stack is bypassed'),
    L(62665, 'vfx.pile.avant', 'avant', 'before'),
    L(62801, 'vfx.pile.apres_aide', 'Après — la pile est appliquée', 'After — the stack is applied'),
    L(62895, 'vfx.pile.apres', 'après', 'after'),
    L(62990, 'vfx.pile.vider_aide', 'Retirer tous les effets de ce clip (annulable)', 'Remove all effects from this clip (undoable)'),
    L(63075, 'vfx.pile.vider', 'Vider', 'Clear'),
    L(63171, 'vfx.pile.ouvrir_panneau', "Ouvrir le panneau d'effets", 'Open the effects panel'),
    L(63259, 'vfx.pile.ajouter', '+ effet', '+ effect'),
    L(63505, 'vfx.pile.aucun', 'Aucun effet sur ce plan.', 'No effects on this shot.'),
    L(63600, 'vfx.pile.aucun_aide', "Ouvrez le panneau d'effets, ou glissez une vignette sur le clip.", 'Open the effects panel, or drag a thumbnail onto the clip.'),
    # t186 (G4, génération IA enrichie, 12/10/2026) — changement FONCTIONNEL du rack VFX posé APRÈS L4 : la rangée
    # « Sujet » (détourage d'un plan) choisit son modèle dans le registre unique du détourage vidéo (GET /api/matte-models :
    # les trois anciennes clés BiRefNet puis Bria VRMBG 3.0, VEED rapide, Pixelcut vidéo, SAM 3.1), avec le prix sur chaque
    # option, la mention de clé (choisissable sans clé), le sujet à garder pour SAM 3.1, le choix mémorisé (dz_detour_vfx).
    # Les clés detour.champ.* et ia.* vivent dans commun.json (hors des zones du lot).
    # La table réversible L4 exige : couche du poste == base ecf945e4 + substitutions ; d'où cette saisie (comme t183 pour
    # son_a.py). La table G1 (dzglyph_paires.json) repère les éditions de cette couche par POSITION : les retouches dans
    # VfxStack sont rendues à longueur égale par le commentaire de tête de la rangée ; le code neuf est posé APRÈS la
    # dernière édition G1 (avant vfxPatch1). Mêmes retouches dans RETOUCHES["VFXRACK"] de scripts/icones/g1_generer.py.
    S(54916, "/* ── T103 (D2b) : la rangée « Sujet » — détourer le plan (BiRefNet, fal) ──\r\n     PAYANT et au prix NON AFFICHÉ par fal : 1er clic = devis du backend (la\r\n     ligne dit « à mesurer »), 2e clic = tir. Le résultat part au Montage par\r\n     `dz-matte` {id, matte} : l'hôte le pose sur le plan, annulable. */",
      "/* ── T103 (D2b) + t186 (G4) : la rangée « Sujet » — détourer le plan ─────────────────────────────────────────────\r\n     PAYANT : 1er clic = devis, 2e clic = tir ; le modèle vient du registre\r\n     (vfxMatte*, fin de couche). Résultat au Montage par `dz-matte`. */", {}),
    S(55706, "body:JSON.stringify({kind:\"matte\",duration_s:vfxN(clip.end,0)-vfxN(clip.start,0)})",
      "body:JSON.stringify(vfxMatteDevis(vfxN(clip.end,0)-vfxN(clip.start,0)))", {}),
    S(55516, "if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;",
      "if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;if(vfxMatteSansSujet(fireNote))return;", {}),
    S(56317, "vfxPost(\"/api/matte\",{job_id:clip.src.job_id,model:VFX_MATTE.model})",
      "vfxPost(\"/api/matte\",vfxMatteCorps(clip.src.job_id))", {}),
    S(57613, "onChange:function(e){VFX_MATTE.model=e.target.value;VFX_MATTE.arm=null;",
      "onChange:function(e){vfxMatteChoix(e.target.value);VFX_MATTE.arm=null;", {}),
    S(57726, "children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:o.label},o.id)})}):null,",
      "children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:vfxMatteLbl(o)},o.id)})}):null,vfxMatteSujetRow(mtick),", {}),
    S(63789, "/* petit utilitaire : {clé: valeur} calculé",
      "/* ── t186 (G4) : le modèle du détourage d'un plan, pris dans le registre unique ──\r\n   GET /api/matte-models sert en tête les trois anciennes clés (BiRefNet v2 vidéo :\r\n   general, matting, portrait) puis les modèles vidéo du registre (Bria VRMBG 3.0, VEED\r\n   rapide, Pixelcut vidéo, SAM 3.1), chacun avec usd, unite, prompt, dispo, cle. Le\r\n   libellé porte le prix (règle unique prixUsd de DzModelesIA, sinon dzPrixUsd du maillon\r\n   encartsia) et, sans clé, la mention « clé X à ajouter dans Réglages » : l'option reste\r\n   CHOISISSABLE, POST /api/matte refuse en 503 avant toute dépense. SAM 3.1 exige le sujet\r\n   à garder (champ sous le sélecteur, refus avant l'envoi s'il est vide). Le choix est\r\n   mémorisé (localStorage dz_detour_vfx) ; défaut historique : general. Ces fonctions\r\n   vivent ICI, après la dernière édition G1 de la couche : la table dzglyph_paires.json\r\n   repère les éditions par position (les retouches plus haut sont à longueur égale). */\r\nvar VFX_DETOUR_LS=\"dz_detour_vfx\";\r\ntry{VFX_MATTE.model=localStorage.getItem(VFX_DETOUR_LS)||VFX_MATTE.model}catch(_e){}\r\nVFX_MATTE.sujet=\"\";\r\nfunction vfxMatteMod(id){var l=VFX_MATTE.models||[];for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}\r\n/* un modèle mémorisé que le serveur ne sert plus retombe sur la première option (general) */\r\nfunction vfxMatteValide(){var l=VFX_MATTE.models||[];if(l.length&&!vfxMatteMod(VFX_MATTE.model))VFX_MATTE.model=l[0].id}\r\nfunction vfxMattePrixUsd(usd,unite){\r\n  var f=(window.DzModelesIA&&window.DzModelesIA.prixUsd)||(typeof dzPrixUsd===\"function\"?dzPrixUsd:null);\r\n  return f?f(usd,unite):\"\"}\r\nfunction vfxMatteNom(o){var k=\"detour.modele.\"+String(o.id||\"\").replace(/-/g,\"_\");\r\n  return window.DZ_I18N&&window.DZ_I18N[k]?dzT(k):o.label}\r\nfunction vfxMatteLbl(o){var p=vfxMattePrixUsd(o.usd,o.unite);\r\n  return vfxMatteNom(o)+\" · \"+(p||dzT(\"ia.prix.a_mesurer\"))+(o.dispo===!1&&o.cle?\" · \"+dzT(\"ia.cle.a_ajouter\",{cle:o.cle}):\"\")}\r\nfunction vfxMatteChoix(v){VFX_MATTE.model=v;try{localStorage.setItem(VFX_DETOUR_LS,v)}catch(_e){}}\r\nfunction vfxMatteSujetReq(){var m=vfxMatteMod(VFX_MATTE.model);return!!(m&&m.prompt)}\r\nfunction vfxMatteSansSujet(note){vfxMatteValide();\r\n  if(!vfxMatteSujetReq()||String(VFX_MATTE.sujet||\"\").trim())return!1;\r\n  note(dzT(\"detour.champ.sujet_requis\"));return!0}\r\n/* le devis : BiRefNet (anciennes clés, birefnet-v2-video) garde le kind « matte » d'avant ; les autres : « detourage »\r\n   — copie JS de la règle unique du serveur, matte_service.op_devis (/matte et décor Avatar) */\r\nfunction vfxMatteDevis(dur){var m=vfxMatteMod(VFX_MATTE.model),reg=(m&&m.registre)||VFX_MATTE.model;\r\n  return reg===\"birefnet-v2-video\"||reg===\"general\"||reg===\"matting\"||reg===\"portrait\"?{kind:\"matte\",duration_s:dur}:{kind:\"detourage\",modele:reg,secondes:dur}}\r\nfunction vfxMatteCorps(job){var c={job_id:job,model:VFX_MATTE.model};\r\n  if(vfxMatteSujetReq())c.sujet=String(VFX_MATTE.sujet||\"\").trim();return c}\r\nfunction vfxMatteSujetRow(tick){\r\n  vfxMatteValide();\r\n  if(!vfxMatteSujetReq())return null;\r\n  return r.jsx(\"input\",{className:\"vfx-sel vfx-msujet\",type:\"text\",value:VFX_MATTE.sujet||\"\",\"data-dzdetsujet\":\"1\",\r\n    placeholder:dzT(\"detour.champ.sujet\"),\"aria-label\":dzT(\"detour.champ.sujet\"),\r\n    onChange:function(e){VFX_MATTE.sujet=e.target.value;VFX_MATTE.arm=null;tick(function(n){return n+1})}})}\r\n\r\n/* petit utilitaire : {clé: valeur} calculé", {}),
    # t188 (G6, génération IA enrichie, 12/10/2026) — changement FONCTIONNEL posé APRÈS L4 : les VFX IA
    # (registre vfx_ia, 12 gestes) — section « IA » du rack VFX sous « Détourer », rail « VFX IA » de Son &
    # VFX (cartes .svm-model), deux clics (devis du serveur puis tir). Avant la dernière édition G1 de la
    # couche, chaque fenêtre entre deux éditions G1 garde sa LONGUEUR et ses lignes (commentaires
    # compensés) ; le code neuf est en fin de couche. Mêmes retouches dans RETOUCHES de
    # scripts/icones/g1_generer.py.
    S(63306, '    matteRow(),',
      '    matteRow(),r.jsx(VfxIaRack,{clip:clip,onNote:fireNote}),',
      {}),
    S(64513, '  svc:VFX_SVC,retry:vfxRetryNow};',
      '  svc:VFX_SVC,retry:vfxRetryNow};\r\n\r\n/* ── t188 (G6) : VFX IA — une vidéo (ou une image) -> une vidéo retouchée, douze gestes ──────────────────────────\r\n   Le catalogue vient du BACKEND (GET /api/vfx-ia/modeles = /api/ia/catalogue?nature=vfx) : prix, unités,\r\n   options (choix, défauts, bornes), les 154 effets PixVerse (filtrables) — rien n\'est recopié ici. Un geste sans FAL_KEY reste\r\n   CHOISISSABLE, avec « clé FAL_KEY à ajouter dans Réglages » : POST /api/vfx-ia refuse en 503 au lancement,\r\n   avant toute dépense. PAYANT, deux clics : le 1er demande le devis (devis:true, LE chiffre de la garde des\r\n   plafonds), le 2e tire ; la réponse redit le même usd. Toute retouche de la saisie désarme le devis.\r\n   La vidéo rendue devient un job fini (Bibliothèque → Rendus, provenance « vfx_ia »). Partagé avec le rail\r\n   « VFX IA » de Son & VFX par window.DzVfx.ia. Ces fonctions vivent ICI, après la dernière édition G1 de la\r\n   couche : la table dzglyph_paires.json repère les éditions par position. */\r\nvar VFX_IA={cat:null,prom:null,imgs:null};\r\n/* le catalogue : SEULE une réponse ok (un tableau `modeles`) est gardée ; une erreur HTTP ou réseau REJETTE (l\'écran\r\n   dit l\'échec et propose « Réessayer », jamais « chargement… » à vie ni une liste vide). `frais` : relu à chaque\r\n   affichage (la mention « clé à ajouter » suit la clé posée entre-temps), le dernier bon catalogue montré en attendant */\r\nfunction vfxIaCatalogue(frais){\r\n  if(VFX_IA.cat&&!frais)return Promise.resolve(VFX_IA.cat);\r\n  if(!VFX_IA.prom)VFX_IA.prom=fetch("/api/vfx-ia/modeles")\r\n    .then(function(r2){if(!r2.ok)throw new Error("HTTP "+r2.status);return r2.json()})\r\n    .then(function(d){if(!d||!Array.isArray(d.modeles))throw new Error("catalogue");\r\n      VFX_IA.prom=null;VFX_IA.cat=d.modeles;return VFX_IA.cat})\r\n    .catch(function(e){VFX_IA.prom=null;throw e});\r\n  return VFX_IA.prom}\r\n/* les images de la Bibliothèque (image de la lumière, référence, image à animer), les plus récentes d\'abord ;\r\n   lues une fois, et seulement quand un geste en demande une */\r\nfunction vfxIaImages(){\r\n  if(VFX_IA.imgs)return Promise.resolve(VFX_IA.imgs);\r\n  return fetch("/api/images").then(function(r2){if(!r2.ok)throw new Error("HTTP "+r2.status);return r2.json()})\r\n    .then(function(d){VFX_IA.imgs=((d&&d.images)||[]).slice().sort(function(a,b){return (b.mtime||0)-(a.mtime||0)})\r\n      .slice(0,80).map(function(i){return i.filename});return VFX_IA.imgs})\r\n    .catch(function(){return []})}\r\n/* le geste choisi est mémorisé (dz_vfxia_geste) ; un stockage refusé n\'empêche rien */\r\nvar VFX_IA_LS="dz_vfxia_geste";\r\nfunction vfxIaGesteLu(){try{return localStorage.getItem(VFX_IA_LS)||""}catch(_e){return ""}}\r\nfunction vfxIaGesteEcrit(id){try{localStorage.setItem(VFX_IA_LS,id)}catch(_e){}}\r\n/* titre et phrase de chaque geste (la phrase dit à l\'utilisateur ce qu\'il doit donner) */\r\nfunction vfxIaTextes(){return {\r\n  "relight-h3":[dzT("vfx.ia.relight_h3.titre"),dzT("vfx.ia.relight_h3.phrase")],\r\n  "inserer-h3":[dzT("vfx.ia.inserer_h3.titre"),dzT("vfx.ia.inserer_h3.phrase")],\r\n  "effacer-perso":[dzT("vfx.ia.effacer_perso.titre"),dzT("vfx.ia.effacer_perso.phrase")],\r\n  "effacer-objet":[dzT("vfx.ia.effacer_objet.titre"),dzT("vfx.ia.effacer_objet.phrase")],\r\n  "jour-nuit":[dzT("vfx.ia.jour_nuit.titre"),dzT("vfx.ia.jour_nuit.phrase")],\r\n  "eau":[dzT("vfx.ia.eau.titre"),dzT("vfx.ia.eau.phrase")],\r\n  "coloriser":[dzT("vfx.ia.coloriser.titre"),dzT("vfx.ia.coloriser.phrase")],\r\n  "retoucher-kling":[dzT("vfx.ia.retoucher_kling.titre"),dzT("vfx.ia.retoucher_kling.phrase")],\r\n  "retoucher-flux3":[dzT("vfx.ia.retoucher_flux3.titre"),dzT("vfx.ia.retoucher_flux3.phrase")],\r\n  "recadrer":[dzT("vfx.ia.recadrer.titre"),dzT("vfx.ia.recadrer.phrase")],\r\n  "agrandir":[dzT("vfx.ia.agrandir.titre"),dzT("vfx.ia.agrandir.phrase")],\r\n  "effets-pixverse":[dzT("vfx.ia.effets_pixverse.titre"),dzT("vfx.ia.effets_pixverse.phrase")]}}\r\nfunction vfxIaTitre(m){var t=vfxIaTextes()[m.id];return t?t[0]:m.label}\r\nfunction vfxIaPhrase(m){var t=vfxIaTextes()[m.id];return t?t[1]:(m.phrase||"")}\r\nfunction vfxIaOptLbl(k){return ({resolution:dzT("vfx.ia.opt.resolution"),aspect_ratio:dzT("vfx.ia.opt.format"),\r\n  seed:dzT("vfx.ia.opt.graine"),start_time:dzT("vfx.ia.opt.debut"),resume_time:dzT("vfx.ia.opt.reprise"),\r\n  duration:dzT("vfx.ia.opt.duree"),color_match:dzT("vfx.ia.opt.couleurs"),\r\n  enable_prompt_expansion:dzT("vfx.ia.opt.enrichir"),mask_prompt:dzT("vfx.ia.opt.objet"),\r\n  enable_pass2_refinement:dzT("vfx.ia.opt.passe2"),upscale_factor:dzT("vfx.ia.opt.facteur"),\r\n  effect:dzT("vfx.ia.opt.effet")})[k]||k}\r\nfunction vfxIaUnite(u){return ({s:dzT("vfx.ia.unite.s"),mp:dzT("vfx.ia.unite.mp"),video:dzT("vfx.ia.unite.video"),\r\n  tranche10s:dzT("vfx.ia.unite.tranche10s"),effet:dzT("vfx.ia.unite.effet")})[u]||""}\r\n/* « $ » + la valeur arrondie au millième, au moins deux décimales (règle prixUsd de DzModelesIA) ; sous 0,01 $\r\n   (le mégapixel LTX : 0,0024075) cinq chiffres significatifs, sinon il s\'afficherait « $0.002 » ; nul -> "" */\r\nfunction vfxIaUsd(v){v=Number(v);if(!(v>0)||!isFinite(v))return "";\r\n  var s=v<0.01?String(Number(v.toPrecision(5))):(Math.round(v*1000)/1000).toFixed(3);\r\n  while(/\\.\\d{3,}$/.test(s)&&s.charAt(s.length-1)==="0")s=s.slice(0,-1);return "$"+s}\r\n/* `des` (Topaz) : le prix dépend de la taille de sortie, le catalogue sert la classe la plus basse -> « dès … » */\r\nfunction vfxIaPrix(m){var p=vfxIaUsd(m.usd);\r\n  return (p?(m.des?dzT("vfx.ia.des",{prix:p+vfxIaUnite(m.unite)}):p+vfxIaUnite(m.unite)):dzT("ia.prix.a_mesurer"))+(m.dispo===!1&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}\r\nfunction vfxIaVide(){return {prompt:"",image:"",opts:{},filtres:{}}}\r\n/* le corps de POST /api/vfx-ia : la source (clip_id = le job du plan), le geste, ce que l\'utilisateur a saisi,\r\n   l\'écran d\'origine (« rail » Son & VFX, « rack » Montage : la catégorie du plafond) */\r\nfunction vfxIaCorps(m,st,job,origine){var c={modele:m.id,origine:origine||"rail"},o={},k;\r\n  if(m.entree==="video"&&job)c.clip_id=job;\r\n  if(m.prompt&&String(st.prompt||"").trim())c.prompt=String(st.prompt).trim();\r\n  if(m.image&&st.image)c.image_filename=st.image;\r\n  for(k in st.opts)if(st.opts[k]!==""&&st.opts[k]!=null&&(m.options||{})[k])o[k]=st.opts[k];\r\n  c.options=o;return c}\r\n/* ce qui manque AVANT d\'appeler le serveur (le serveur refuse pareil, en 400) : null si tout y est */\r\nfunction vfxIaManque(m,st,job){var o=m.options||{},k;\r\n  if(m.entree==="video"&&!job)return dzT("vfx.ia.manque_video");\r\n  if(m.image==="requis"&&!st.image)return m.entree==="image"?dzT("vfx.ia.manque_image_animer"):dzT("vfx.ia.manque_image_lumiere");\r\n  if(m.prompt==="requis"&&!String(st.prompt||"").trim())return dzT("vfx.ia.manque_prompt");\r\n  for(k in o)if(o[k].requis&&(st.opts[k]===""||st.opts[k]==null))return dzT("vfx.ia.manque_option",{nom:vfxIaOptLbl(k)});\r\n  return null}\r\nfunction vfxIaPost(corps){\r\n  return fetch("/api/vfx-ia",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)})\r\n    .then(function(r2){return r2.json().catch(function(){return {}}).then(function(d){\r\n      if(!r2.ok){var x2=d&&d.detail;throw new Error(typeof x2==="string"?x2:(x2&&x2.message)||("HTTP "+r2.status))}\r\n      return d})})}\r\n/* le devis armé, SEULEMENT s\'il a été demandé pour la saisie affichée (un devis qui arrive tard pour une saisie\r\n   modifiée depuis n\'est ni montré ni tiré) */\r\nfunction vfxIaArme(arm,m,st,job,origine){\r\n  return arm&&m&&arm.sig===JSON.stringify(vfxIaCorps(m,st,job,origine))?arm:null}\r\n/* les deux clics : `arm` = le devis en attente ({sig, usd, detail}), valable pour CETTE saisie seulement */\r\nfunction vfxIaClic(m,st,job,g){\r\n  if(g.busy)return;var manque=vfxIaManque(m,st,job);if(manque){g.note(manque);return}\r\n  var corps=vfxIaCorps(m,st,job,g.origine),sig=JSON.stringify(corps);\r\n  if(!g.arm||g.arm.sig!==sig){\r\n    vfxIaPost(Object.assign({devis:!0},corps))\r\n      .then(function(d){g.setArm({sig:sig,usd:d.usd,detail:d.detail||""})})\r\n      .catch(function(e){g.setArm(null);g.note(dzT("vfx.ia.echec",{err:e.message}))});\r\n    return}\r\n  g.setArm(null);g.setBusy(!0);\r\n  vfxIaPost(corps).then(function(d){g.setBusy(!1);\r\n      g.note(dzT("vfx.ia.fait",{nom:d.filename,prix:vfxIaUsd(d.usd)||dzT("ia.prix.a_mesurer")}));\r\n      if(g.done)g.done(d)})\r\n    .catch(function(e){g.setBusy(!1);g.note(dzT("vfx.ia.echec",{err:e.message}))})}\r\nfunction vfxIaDevisTxt(arm){\r\n  return dzT("vfx.ia.devis",{prix:vfxIaUsd(arm.usd)||dzT("ia.prix.a_mesurer"),detail:arm.detail})}\r\n/* les champs d\'un geste, construits d\'après le SCHÉMA servi (aucune liste recopiée) ; `k` = classes de l\'hôte */\r\nfunction VfxIaChamps(props){\r\n  var m=props.m,st=props.st,k=props.k||{},o=m.options||{},out=[];\r\n  function setOpt(n,v){var no=Object.assign({},st.opts);no[n]=v;props.set({opts:no})}\r\n  if(m.prompt)out.push(r.jsx("textarea",{className:k.texte,rows:2,maxLength:1500,value:st.prompt,\r\n    "aria-label":dzT("vfx.ia.prompt"),\r\n    placeholder:m.prompt==="requis"?dzT("vfx.ia.prompt_requis"):dzT("vfx.ia.prompt_facultatif"),\r\n    onChange:function(e){props.set({prompt:e.target.value})}},"p"));\r\n  /* rééclairer : la référence est une image de LUMIÈRE (schéma : un rendu de sphère montrant l\'éclairage voulu) */\r\n  if(m.image==="requis"&&m.entree==="video")out.push(r.jsx("div",{className:k.aide,children:dzT("vfx.ia.image_lumiere_aide")},"ia"));\r\n  if(m.image)out.push(r.jsxs("select",{className:k.sel,value:st.image,"aria-label":dzT("vfx.ia.image"),\r\n    onChange:function(e){props.set({image:e.target.value})},children:[\r\n    r.jsx("option",{value:"",children:m.image==="requis"?(m.entree==="image"?dzT("vfx.ia.image_animer"):dzT("vfx.ia.image_lumiere"))\r\n      :dzT("vfx.ia.image_reference")},""),\r\n    (props.images||[]).map(function(f){return r.jsx("option",{value:f,children:f},f)})]},"i"));\r\n  Object.keys(o).forEach(function(n){var s=o[n],v=st.opts[n],lbl=vfxIaOptLbl(n)+(s.requis?" *":"");\r\n    /* une longue énumération (les 154 effets PixVerse) : un champ de filtre au-dessus du <select> ; le choix\r\n       courant reste toujours dans la liste */\r\n    if(s.choix&&s.choix.length>30){var fl=String((st.filtres||{})[n]||""),q=fl.trim().toLowerCase(),\r\n        cur=v!=null?String(v):"",vus=s.choix.filter(function(c){return !q||c.toLowerCase().indexOf(q)>=0||c===cur});\r\n      out.push(r.jsx("input",{className:k.sel,type:"search",value:fl,"aria-label":dzT("vfx.ia.filtrer"),\r\n        placeholder:dzT("vfx.ia.filtrer_n",{n:s.choix.length}),\r\n        onChange:function(e){var nf=Object.assign({},st.filtres||{});nf[n]=e.target.value;props.set({filtres:nf})}},n+"-f"));\r\n      out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),\r\n        r.jsxs("select",{className:k.sel,value:cur,"aria-label":lbl,\r\n          onChange:function(e){setOpt(n,e.target.value)},children:[\r\n          r.jsx("option",{value:"",children:dzT("vfx.ia.choisir_n",{n:vus.length})},""),\r\n          vus.map(function(c){return r.jsx("option",{value:c,children:c},c)})]})]},n))}\r\n    else if(s.choix)out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),\r\n      r.jsxs("select",{className:k.sel,value:v!=null?String(v):(s.defaut!=null?String(s.defaut):""),"aria-label":lbl,\r\n        onChange:function(e){setOpt(n,e.target.value)},children:[\r\n        s.defaut==null?r.jsx("option",{value:"",children:dzT("vfx.ia.choisir")},""):null,\r\n        s.choix.map(function(c){return r.jsx("option",{value:c,children:c},c)})]})]},n));\r\n    else if(s.bool)out.push(r.jsxs("label",{className:k.ligne,children:[\r\n      r.jsx("input",{type:"checkbox",checked:!!v,onChange:function(e){setOpt(n,e.target.checked)}}),\r\n      r.jsx("span",{className:k.lbl,children:lbl})]},n));\r\n    else if(s.num)out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),\r\n      r.jsx("input",{className:k.num,type:"number",min:s.num[0],max:s.num[1],step:s.entier?1:.125,\r\n        value:v!=null?v:(s.defaut!=null?s.defaut:""),"aria-label":lbl,placeholder:s.num[0]+" – "+s.num[1],\r\n        onChange:function(e){var t=e.target.value;setOpt(n,t===""?"":Number(t))}})]},n));\r\n    else out.push(r.jsxs("label",{className:k.ligne,children:[r.jsx("span",{className:k.lbl,children:lbl}),\r\n      r.jsx("input",{className:k.sel,type:"text",value:v||"","aria-label":lbl,maxLength:300,\r\n        onChange:function(e){setOpt(n,e.target.value)}})]},n))});\r\n  return r.jsx("div",{className:k.bloc,style:{display:"flex",flexDirection:"column",gap:6,marginTop:8},children:out})}\r\n/* la section « IA » du rack, sous « Détourer » : les gestes qui partent d\'une VIDÉO, sur le plan sélectionné */\r\nfunction VfxIaRack(props){\r\n  var US=x.useState,EF=x.useEffect,clip=props.clip;\r\n  var s1=US(VFX_IA.cat),cat=s1[0],setCat=s1[1];\r\n  var s2=US(vfxIaGesteLu()),mid=s2[0],setMid=s2[1];\r\n  var s3=US(vfxIaVide()),st=s3[0],setSt=s3[1];\r\n  var s4=US(null),arm=s4[0],setArm=s4[1];\r\n  var s5=US(!1),busy=s5[0],setBusy=s5[1];\r\n  var s6=US(VFX_IA.imgs||[]),imgs=s6[0],setImgs=s6[1];\r\n  var s7=US(!1),err=s7[0],setErr=s7[1];\r\n  function charger(v){setErr(!1);vfxIaCatalogue(!0).then(function(c){if(v.on)setCat(c)},function(){if(v.on)setErr(!0)})}\r\n  EF(function(){var v={on:!0};charger(v);return function(){v.on=!1}},[]);\r\n  EF(function(){setArm(null)},[clip&&clip.id]);\r\n  var vids=(cat||[]).filter(function(v){return v.entree==="video"});\r\n  var m=vids.filter(function(v){return v.id===mid})[0]||vids[0];\r\n  EF(function(){var v={on:!0};if(m&&m.image)vfxIaImages().then(function(l){if(v.on)setImgs(l)});\r\n    return function(){v.on=!1}},[m&&m.image?m.id:""]);\r\n  if(!clip||!clip.src||!clip.src.job_id)return null;\r\n  var job=clip.src.job_id,g={busy:busy,arm:arm,setArm:setArm,setBusy:setBusy,note:props.onNote,origine:"rack"};\r\n  var armOk=vfxIaArme(arm,m,st,job,"rack");\r\n  return r.jsxs("div",{className:"vfx-matte vfx-ia","data-dzvfxia":"rack",children:[\r\n    r.jsx("span",{className:"vfx-mlbl",children:dzT("vfx.ia.section")}),\r\n    vids.length?r.jsx("select",{className:"vfx-sel",value:m?m.id:"","aria-label":dzT("vfx.ia.geste"),\r\n      onChange:function(e){setMid(e.target.value);vfxIaGesteEcrit(e.target.value);setSt(vfxIaVide());setArm(null)},\r\n      children:vids.map(function(v){return r.jsx("option",{value:v.id,children:vfxIaTitre(v)+" · "+vfxIaPrix(v)},v.id)})})\r\n      :err?r.jsxs("div",{className:"vfx-mhint","data-dzvfxiaerr":"1",children:[dzT("vfx.ia.catalogue_echec")," ",\r\n        r.jsx("button",{className:"vfx-btn",onClick:function(){charger({on:!0})},children:dzT("vfx.ia.reessayer")})]})\r\n      :r.jsx("div",{className:"vfx-mhint",children:dzT("vfx.ia.chargement")}),\r\n    m?r.jsx("div",{className:"vfx-mhint vfx-iaphrase",children:vfxIaPhrase(m)}):null,\r\n    m?r.jsx(VfxIaChamps,{m:m,st:st,images:imgs,k:{bloc:"vfx-iachamps",texte:"vfx-sel vfx-iatexte",sel:"vfx-sel",\r\n      num:"vfx-sel vfx-ianum",ligne:"vfx-prow",lbl:"vfx-plabel",aide:"vfx-mhint"},\r\n      set:function(p){setSt(Object.assign({},st,p));setArm(null)}}):null,\r\n    m?r.jsx("button",{className:"vfx-btn","data-off":busy?"":void 0,title:dzT("vfx.ia.bouton_aide"),\r\n      onClick:function(){vfxIaClic(m,st,job,g)},\r\n      children:busy?dzT("vfx.ia.en_cours"):armOk?dzT("vfx.ia.confirmer"):dzT("vfx.ia.lancer")}):null,\r\n    armOk?r.jsx("div",{className:"vfx-mhint",children:vfxIaDevisTxt(armOk)}):null]})}\r\n/* t188 : les aides des VFX IA, pour le rail « VFX IA » de Son & VFX */\r\nwindow.DzVfx.ia={catalogue:vfxIaCatalogue,images:vfxIaImages,titre:vfxIaTitre,phrase:vfxIaPhrase,prix:vfxIaPrix,clic:vfxIaClic,devisTxt:vfxIaDevisTxt,Champs:VfxIaChamps,Rack:VfxIaRack,arme:vfxIaArme,\r\n  gesteLu:vfxIaGesteLu,gesteEcrit:vfxIaGesteEcrit,dernier:function(){return VFX_IA.cat}};',
      {'vfx.ia.relight_h3.titre': ('Rééclairer', 'Relight'), 'vfx.ia.relight_h3.phrase': ("Donnez une image de la LUMIÈRE voulue : l'IA éclaire le plan comme elle.", 'Provide an image of the LIGHTING you want: the AI lights the shot the same way.'), 'vfx.ia.image_lumiere_aide': ("La référence est une image de lumière, pas de la scène : idéalement une sphère éclairée comme le plan doit l'être (couleur, direction, contraste).", 'The reference is an image of the lighting, not of the scene: ideally a sphere lit the way the shot should be (color, direction, contrast).'), 'vfx.ia.des': ('dès {prix}', 'from {prix}'), 'vfx.ia.catalogue_echec': ("Le catalogue des VFX IA n'a pas pu être lu.", 'The AI VFX catalog could not be loaded.'), 'vfx.ia.reessayer': ('Réessayer', 'Retry'), 'vfx.ia.inserer_h3.titre': ('Insérer une scène', 'Insert a scene'), 'vfx.ia.inserer_h3.phrase': ("Dites où la scène commence, où le plan reprend, et ce qui s'y passe.", 'Say where the scene starts, where the shot resumes, and what happens in it.'), 'vfx.ia.effacer_perso.titre': ('Effacer un personnage', 'Remove a person'), 'vfx.ia.effacer_perso.phrase': ('Le décor reste, la personne disparaît (plaque propre).', 'The set stays, the person disappears (clean plate).'), 'vfx.ia.effacer_objet.titre': ('Effacer un objet', 'Remove an object'), 'vfx.ia.effacer_objet.phrase': ("Nommez l'objet à effacer, puis décrivez le fond qui doit le remplacer.", 'Name the object to remove, then describe the background that should replace it.'), 'vfx.ia.jour_nuit.titre': ('Jour → nuit', 'Day → night'), 'vfx.ia.jour_nuit.phrase': ('Le même plan, comme tourné de nuit.', 'The same shot, as if filmed at night.'), 'vfx.ia.eau.titre': ("Simulation d'eau", 'Water simulation'), 'vfx.ia.eau.phrase': ("Décrivez l'eau voulue : pluie, inondation, vagues…", 'Describe the water you want: rain, flood, waves…'), 'vfx.ia.coloriser.titre': ('Coloriser', 'Colorize'), 'vfx.ia.coloriser.phrase': ('Un plan en noir et blanc retrouve ses couleurs.', 'A black-and-white shot gets its colors back.'), 'vfx.ia.retoucher_kling.titre': ('Modifier par une phrase (Kling O3)', 'Edit with a sentence (Kling O3)'), 'vfx.ia.retoucher_kling.phrase': ('Décrivez le changement : le mouvement et le son du plan restent.', "Describe the change: the shot's motion and sound stay."), 'vfx.ia.retoucher_flux3.titre': ('Modifier par une phrase (rapide)', 'Edit with a sentence (fast)'), 'vfx.ia.retoucher_flux3.phrase': ('Décrivez le changement voulu ; rendu rapide en 720p.', 'Describe the change you want; fast render in 720p.'), 'vfx.ia.recadrer.titre': ('Changer le format', 'Change the format'), 'vfx.ia.recadrer.phrase': ("Choisissez le nouveau cadre (9:16, 16:9…) : l'IA complète les bords.", 'Pick the new frame (9:16, 16:9…): the AI fills in the edges.'), 'vfx.ia.agrandir.titre': ('Agrandir / netteté (Topaz)', 'Upscale / sharpen (Topaz)'), 'vfx.ia.agrandir.phrase': ('La vidéo gagne en taille et en netteté (x2 par défaut).', 'The video gains size and sharpness (x2 by default).'), 'vfx.ia.effets_pixverse.titre': ("Effet prêt à l'emploi (PixVerse)", 'Ready-made effect (PixVerse)'), 'vfx.ia.effets_pixverse.phrase': ('Choisissez une image et un effet : elle devient une courte vidéo animée.', 'Pick an image and an effect: it becomes a short animated video.'), 'vfx.ia.opt.resolution': ('Résolution', 'Resolution'), 'vfx.ia.opt.format': ('Format', 'Format'), 'vfx.ia.opt.graine': ('Graine', 'Seed'), 'vfx.ia.opt.debut': ('Début de la scène (s)', 'Scene start (s)'), 'vfx.ia.opt.reprise': ('Reprise du plan (s)', 'Shot resumes at (s)'), 'vfx.ia.opt.duree': ('Durée de la scène (s)', 'Scene length (s)'), 'vfx.ia.opt.couleurs': ('Raccorder les couleurs', 'Match colors'), 'vfx.ia.opt.enrichir': ('Enrichir la description', 'Expand the description'), 'vfx.ia.opt.objet': ('Objet à effacer', 'Object to remove'), 'vfx.ia.opt.passe2': ('Passe 2 (plus stable, plus chère)', 'Pass 2 (steadier, costs more)'), 'vfx.ia.opt.facteur': ('Facteur', 'Factor'), 'vfx.ia.opt.effet': ('Effet', 'Effect'), 'vfx.ia.unite.s': ('/s', '/s'), 'vfx.ia.unite.mp': ('/MP', '/MP'), 'vfx.ia.unite.video': ('/vidéo', '/video'), 'vfx.ia.unite.tranche10s': ('/10 s', '/10 s'), 'vfx.ia.unite.effet': ('/5 s', '/5 s'), 'vfx.ia.manque_video': ("Choisissez d'abord une vidéo source.", 'Pick a source video first.'), 'vfx.ia.manque_image_animer': ("Choisissez l'image à animer.", 'Pick the image to animate.'), 'vfx.ia.manque_image_lumiere': ("Choisissez l'image de la lumière voulue.", 'Pick the image of the lighting you want.'), 'vfx.ia.manque_prompt': ("Décrivez d'abord le changement voulu.", 'Describe the change you want first.'), 'vfx.ia.manque_option': ('Renseignez « {nom} ».', 'Fill in “{nom}”.'), 'vfx.ia.echec': ('Échec : {err}', 'Failed: {err}'), 'vfx.ia.fait': ('Vidéo ajoutée à la Bibliothèque (Rendus) : {nom} ({prix})', 'Video added to the Library (Renders): {nom} ({prix})'), 'vfx.ia.devis': ('Devis : {prix} — {detail} · cliquer encore pour lancer', 'Estimate: {prix} — {detail} · click again to run'), 'vfx.ia.prompt': ('Description', 'Description'), 'vfx.ia.prompt_requis': ('Décrivez le changement voulu (requis)', 'Describe the change you want (required)'), 'vfx.ia.prompt_facultatif': ('Description (facultative)', 'Description (optional)'), 'vfx.ia.image': ('Image', 'Image'), 'vfx.ia.image_animer': ('Image à animer…', 'Image to animate…'), 'vfx.ia.image_lumiere': ('Image de la lumière voulue…', 'Image of the lighting you want…'), 'vfx.ia.image_reference': ('Image de référence (facultative)', 'Reference image (optional)'), 'vfx.ia.choisir': ('Choisir…', 'Choose…'), 'vfx.ia.choisir_n': ('Choisir… ({n})', 'Choose… ({n})'), 'vfx.ia.filtrer': ('Filtrer la liste', 'Filter the list'), 'vfx.ia.filtrer_n': ('Filtrer les {n} choix…', 'Filter the {n} choices…'), 'vfx.ia.section': ('IA', 'AI'), 'vfx.ia.geste': ('Geste IA', 'AI action'), 'vfx.ia.chargement': ('Lecture du catalogue des VFX IA…', 'Loading the AI VFX catalog…'), 'vfx.ia.bouton_aide': ('1er clic : devis du serveur ; 2e clic : lancement (payant)', '1st click: server estimate; 2nd click: run (paid)'), 'vfx.ia.en_cours': ('génération…', 'generating…'), 'vfx.ia.confirmer': ('Lancer pour de bon', 'Run for real'), 'vfx.ia.lancer': ('Estimer puis lancer', 'Estimate, then run'), 'vfx.ia.rail': ('VFX IA', 'AI VFX'), 'vfx.ia.rail_desc': ('Rééclairer, effacer, coloriser, recadrer, agrandir — vidéo → vidéo', 'Relight, remove, colorize, reframe, upscale — video → video'), 'vfx.ia.rail_bas': ('Où va le résultat', 'Where the result goes'), 'vfx.ia.rail_note': ('La vidéo rendue entre dans la Bibliothèque (Rendus) et se pose dans le Montage.', 'The rendered video goes to the Library (Renders) and can be placed in the Montage.'), 'vfx.ia.indisponible': ("Le rack VFX n'est pas chargé : les VFX IA sont indisponibles.", 'The VFX rack is not loaded: AI VFX are unavailable.'), 'vfx.ia.source': ('Vidéo source', 'Source video'), 'vfx.ia.source_image': ("Ce geste part d'une image : choisissez-la plus bas.", 'This action starts from an image: pick it below.'), 'vfx.ia.aucune_video': ("Aucune vidéo terminée dans la Bibliothèque pour l'instant.", 'No finished video in the Library yet.'), 'vfx.ia.gestes': ('Gestes', 'Actions'), 'vfx.ia.resultat': ('Vidéo rendue', 'Rendered video'), 'vfx.ia.dans_biblio': ('{nom} — dans la Bibliothèque (Rendus), à poser dans le Montage', '{nom} — in the Library (Renders), ready to place in the Montage'), 'vfx.ia.ouvrir_montage': ('Ouvrir le Montage', 'Open Montage')}),
]
