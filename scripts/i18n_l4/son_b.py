"""t144 — son_b : couche frontend/patches/son-vfx-montage.js, lignes 564–1569 de la base. L'écran Son & VFX DzSonVfx
(rail des générateurs et son panneau bas contextuel, éditeur de voix, voix off dirigée T102/T7, mix voix + musique
ducké T102/T8, carte SFX — génération réelle ou maquette —, presets de post-traitement, barre de titre et mesure
LUFS) ; puis les données et helpers partagés avec le Montage : clips de démo, pistes SVM_TRACKS, formats SVM_RATIOS,
bus du mixeur, trous V1, transitions SVM_TRANS, courbes de fondu SVM_FADE_CURVES(_TT), et la table des raccourcis
SVM_ACTIONS / SVM_KEYS_INFO avec la canonisation des combos (svmComboOfEvent, svmComboCanon, svmComboReserved).
Les libellés de raccourcis servent surtout l'écran Montage : zone `son.` gardée quand même (objet `raccourci`).

Gardés (X), et pourquoi :
- les SECTIONS de raccourcis (sec « Lecture », « Montage », « Affichage », « Audio », et SVM_KEY_SECTIONS) : comparées
  entre elles par le filtre du panneau Raccourcis ET par dzmMenuRub (montage.js : a.sec==="Audio" / "Affichage") ;
  l'affichage des en-têtes de section se traduit au site d'affichage (groupe montage_c), pas ici ;
- toutes les COMBOS (combo:"Espace", "Maj+X"…, SVM_EV_NAMES, SVM_EV_NAMED_SET, SVM_COMBO_WORDS, SVM_COMBO_RESERVED,
  les préfixes « Ctrl+ », « Alt+ », « Maj+ », e.code "Space") : le code les ANALYSE, les compare et les stocke dans
  dz_svm_keymap ; les touches « Ctrl » et « Échap » de SVM_KEYS_INFO restent comme les combos affichées à côté ;
- les données de démo du Montage (libellés de clips, texte de narration, noms de fichiers) : stockées dans le projet ;
- le type de piste « vidéo » : comparé par montage.js (t.type==="vidéo") ;
- les unités et textes identiques dans les deux langues (« dB », « 0 dB », « Pause », « Audio », « Ducking »,
  « ducking », « auto », « 9:16 · vertical », « 4:5 · feed », « zoom 100 % ») et le CSS (« var( », « deg) »,
  « 1 1 auto »).
"""
from outils import L, S, X

CIBLE = "sonvfx"
FRAGMENTS = {}

_SEC = "section de raccourci : comparée par le filtre de sections du panneau et par dzmMenuRub (montage.js)"
_COMBO = "combo de raccourci : analysée, comparée et stockée (dz_svm_keymap) — une valeur, pas un libellé"
_DB = "identique dans les deux langues"

ENTREES = [
    # DzSonVfx : fichier courant de l'éditeur (pastille)
    L(43326, 'son.editeur.pastille_biblio', 'bibliothèque', 'library'),
    # DzSonVfx : écoutes (un seul flux), aperçus de voix
    L(44261, 'son.commun.lecture_bloquee', "Lecture bloquée par le navigateur — cliquez d'abord dans la page.",
      'Playback blocked by the browser — click in the page first.'),
    L(44859, 'son.commun.lecture_bloquee', "Lecture bloquée par le navigateur — cliquez d'abord dans la page.",
      'Playback blocked by the browser — click in the page first.'),
    L(46025, 'son.voix.apercu_indispo', 'Aperçu de voix indisponible.', 'Voice preview unavailable.'),
    L(46079, 'son.voix.apercu_eleven', 'Les aperçus de voix arrivent avec ElevenLabs connecté (Réglages → clés API).',
      'Voice previews come with ElevenLabs connected (Settings → API keys).'),
    L(46502, 'son.commun.lecture_bloquee', "Lecture bloquée par le navigateur — cliquez d'abord dans la page.",
      'Playback blocked by the browser — click in the page first.'),
    # DzSonVfx : génération SFX (erreurs montrées dans la carte)
    L(46854, 'son.sfx.decrire_dabord', "Décris d'abord le son — ex : « impact sourd et grave, réverbération courte ».",
      'Describe the sound first — e.g. “dull, deep impact, short reverb”.'),
    L(47198, 'son.sfx.aucun_son_retourne', 'aucun son retourné', 'no sound returned'),

    # DzSonVfx : panneau bas du rail (voix, familles, musique, post)
    L(48118, 'son.commun.voix', 'Voix', 'Voice'),
    L(48250, 'son.voix.chargement', 'chargement des voix…', 'loading voices…'),
    L(48998, 'son.voix.ecouter', 'Écouter la voix', 'Preview voice'),
    S(49029, '"Écouter "+v.name', 'dzT("son.sfx.ecouter_nom",{nom:v.name})',
      {'son.sfx.ecouter_nom': ('Écouter {nom}', 'Play {nom}')}),
    L(49266, 'son.rail.familles_sons', 'Familles de sons', 'Sound families'),
    L(49526, 'son.rail.familles_textures', 'Familles de textures', 'Texture families'),
    L(49796, 'son.rail.sans_cle', 'Sans clé, tout de suite', 'No key, right away'),
    L(49905, 'son.rail.jingles_note',
      'La famille « Jingles » du catalogue livré contient 85 stingers courts (victoire, échec, transition), '
      'utilisables sans aucune clé.',
      'The “Jingles” family of the bundled catalog holds 85 short stingers (win, fail, transition), usable '
      'without any key.'),
    L(50205, 'son.rail.ouvrir_jingles', 'Ouvrir les jingles livrés →', 'Open the bundled jingles →'),
    L(50337, 'son.rail.ou_applique', "Où ça s'applique", 'Where it applies'),
    L(50439, 'son.rail.post_note',
      "Le post-traitement s'applique au rendu, via le nœud Render du Studio (moteur Effects / Mask, ffmpeg local, "
      "gratuit).",
      "Post-processing applies at render time, through the Studio's Render node (Effects / Mask engine, local "
      "ffmpeg, free)."),

    # DzSonVfx : rail gauche
    L(50677, 'son.rail.generateurs', 'Générateurs', 'Generators'),
    X(51032, 'CSS (var(--couleur))'),

    # DzSonVfx : carte éditeur de voix (forme d'onde, outils)
    L(51786, 'son.editeur.se_deplacer', 'Se déplacer', 'Seek'),
    X(52159, _DB),
    L(52167, 'son.commun.lecture', 'Lecture', 'Play', contexte=True),
    X(52198, _DB),
    L(52206, 'son.commun.lecture', 'Lecture', 'Play', contexte=True),
    # outils : le nom sert d'affichage, de clé React et de morceau des notes ci-dessous (jamais comparé)
    L(52253, 'son.editeur.rogner', 'Rogner', 'Trim'),
    L(52262, 'son.editeur.fondu', 'Fondu', 'Fade', contexte=True),
    X(52270, _DB),
    L(52280, 'son.editeur.normaliser', 'Normaliser', 'Normalize'),
    L(52293, 'son.editeur.de_esser', 'Dé-esser', 'De-ess'),
    S(52596, '"« "+t+" » : disponible par clip dans le Montage — "+svmKeyLabelNow("sounds_drawer")+" ouvre le tiroir '
             'Sons, l\'inspecteur Clip audio porte gain, fondus, vitesse et rack d\'effets."',
      'dzT("son.editeur.outil_montage",{outil:t,touche:svmKeyLabelNow("sounds_drawer")})',
      {'son.editeur.outil_montage': (
          "« {outil} » : disponible par clip dans le Montage — {touche} ouvre le tiroir Sons, l'inspecteur Clip audio "
          "porte gain, fondus, vitesse et rack d'effets.",
          '“{outil}”: available per clip in Montage — {touche} opens the Sounds drawer; the Audio clip inspector '
          'holds gain, fades, speed and the effects rack.')}),
    S(52790, '"« "+t+" » arrive avec le backend d\'édition audio — cible produit, rien n\'est facturé."',
      'dzT("son.editeur.outil_cible",{outil:t})',
      {'son.editeur.outil_cible': (
          "« {outil} » arrive avec le backend d'édition audio — cible produit, rien n'est facturé.",
          '“{outil}” comes with the audio editing backend — product target, nothing is billed.')}),
    L(53029, 'son.editeur.envoyer_montage', 'Envoyer au montage →', 'Send to Montage →'),

    # DzSonVfx : voix off dirigée (T102/T7)
    L(54024, 'son.commun.echec_mot', 'échec', 'failed'),
    L(54176, 'son.editeur.pastille_generee', 'générée', 'generated'),
    S(54217, '"Voix générée : "+d.filename+((d.notes||[]).length?" — "+d.notes.join(" · "):"")',
      'dzT("son.vo.generee",{nom:d.filename,notes:(d.notes||[]).length?" — "+d.notes.join(" · "):""})',
      {'son.vo.generee': ('Voix générée : {nom}{notes}', 'Voice generated: {nom}{notes}')}),
    S(54350, '"Voix : "+String(e&&e.message||e)', 'dzT("son.vo.erreur",{e:String(e&&e.message||e)})',
      {'son.vo.erreur': ('Voix : {e}', 'Voice: {e}')}),
    L(54821, 'son.vo.titre', 'Voix off dirigée', 'Directed voice-over'),
    L(54924, 'son.vo.balises_aide', 'clique une balise pour la poser en tête (4 au plus) — Eleven v3 les joue',
      'click a tag to put it at the start (4 max) — Eleven v3 performs them'),
    L(55114, 'son.vo.texte', 'Texte de la voix off', 'Voice-over text'),
    L(55157, 'son.vo.texte_exemple', 'Texte de la voix off — « Sous la surface, quelque chose remonte… »',
      'Voice-over text — “Beneath the surface, something rises…”'),
    L(55364, 'son.vo.chargement_balises', 'chargement des balises…', 'loading tags…'),
    L(55878, 'son.vo.balise_speciale', 'spécial — à manier en connaissance de cause', 'special — use with care'),
    L(55924, 'son.vo.balise_v3', 'balise Eleven v3', 'Eleven v3 tag'),
    L(56254, 'son.vo.voicebox_sans_balises',
      "Voicebox n'interprète pas les balises v3 — elles seraient retirées du texte (la réponse le dira).",
      'Voicebox does not interpret v3 tags — they would be stripped from the text (the response will say so).'),
    L(56362, 'son.vo.balises_cle', 'Balises v3 : il faut une clé ElevenLabs (Réglages → clés API).',
      'v3 tags: an ElevenLabs key is required (Settings → API keys).'),
    L(56476, 'son.vo.apercu_aide', 'ce qui part au modèle, au caractère près',
      'what is sent to the model, character for character'),
    L(56537, 'son.vo.apercu', 'part au modèle : ', 'sent to the model: '),
    X(56766, 'CSS (flex)'),
    L(56813, 'son.vo.devis_indispo', 'devis indisponible — un second clic génère quand même',
      'quote unavailable — a second click generates anyway'),
    S(56881, '"devis : ~$"+voArm.usd.toFixed(3)+" — un second clic génère"',
      'dzT("son.vo.devis",{usd:voArm.usd.toFixed(3)})',
      {'son.vo.devis': ('devis : ~${usd} — un second clic génère', 'quote: ~${usd} — a second click generates')}),
    L(57091, 'son.vo.synthese', 'synthèse…', 'synthesizing…'),
    L(57109, 'son.vo.confirmer', 'Confirmer et générer', 'Confirm and generate'),
    L(57132, 'son.vo.generer', 'Générer la voix', 'Generate voice'),

    # DzSonVfx : mix voix + musique ducké (T102/T8)
    L(57865, 'son.commun.echec_mot', 'échec', 'failed'),
    S(57974, '"Mix posé en Bibliothèque (Musique) : "+d.filename', 'dzT("son.mix.pose",{nom:d.filename})',
      {'son.mix.pose': ('Mix posé en Bibliothèque (Musique) : {nom}', 'Mix saved to the Library (Music): {nom}')}),
    S(58078, '"Mix : "+String(e&&e.message||e)', 'dzT("son.mix.erreur",{e:String(e&&e.message||e)})',
      {'son.mix.erreur': ('Mix : {e}', 'Mix: {e}')}),
    L(58292, 'son.mix.titre', 'Mix voix + musique', 'Voice + music mix'),
    L(58368, 'son.mix.ffmpeg_local', 'ffmpeg local', 'local ffmpeg'),
    L(58392, 'son.commun.gratuit', 'gratuit', 'free'),
    L(58458, 'son.mix.voix', 'voix : ', 'voice: '),
    L(58498, 'son.mix.generer_voix', '— génère une voix off', '— generate a voice-over'),
    L(58532, 'son.mix.musique', ' · musique : ', ' · music: '),
    L(58578, 'son.mix.generer_musique', '— génère une musique', '— generate a music track'),
    X(58747, _DB),
    S(58941, '"ratio "+SVM_DUCK[k].ratio+", seuil "+SVM_DUCK[k].threshold',
      'dzT("son.mix.preset_aide",{ratio:SVM_DUCK[k].ratio,seuil:SVM_DUCK[k].threshold})',
      {'son.mix.preset_aide': ('ratio {ratio}, seuil {seuil}', 'ratio {ratio}, threshold {seuil}')}),
    L(59219, 'son.mix.mixage', 'mixage…', 'mixing…'),
    L(59229, 'son.mix.ecouter', 'Écouter le mix ducké', 'Play the ducked mix'),
    S(59313, '"dans la Bibliothèque (Musique) : "+mixRes.filename', 'dzT("son.mix.resultat",{nom:mixRes.filename})',
      {'son.mix.resultat': ('dans la Bibliothèque (Musique) : {nom}', 'in the Library (Music): {nom}')}),

    # DzSonVfx : panneau cible produit (post-traitement)
    L(59652, 'son.cible.tag', 'Cible produit', 'Product target'),
    L(59850, 'son.cible.post_titre', "Le post-traitement s'applique au rendu", 'Post-processing applies at render time'),
    L(59891, 'son.cible.post_corps',
      'Grain, glow, aberration et transitions passent par le moteur Effects / Mask existant sur le nœud Render '
      '(gratuit, ffmpeg local). À configurer dans Studio → Render.',
      'Grain, glow, aberration and transitions go through the existing Effects / Mask engine on the Render node '
      '(free, local ffmpeg). Set it up in Studio → Render.'),

    # DzSonVfx : carte SFX (génération réelle par la couche DzSfx)
    L(60388, 'son.sfx.titre_generer', 'Générer des SFX', 'Generate SFX'),
    L(60475, 'son.sfx.prix_aide', '2 variations par génération — crédits ElevenLabs',
      '2 variations per generation — ElevenLabs credits'),
    L(60721, 'son.sfx.prompt_exemple', 'Décris le son — « vague qui claque sur un rocher, grave »',
      'Describe the sound — “wave slapping a rock, deep”'),
    L(60806, 'son.sfx.prompt', 'Description du son à générer', 'Description of the sound to generate'),
    L(61107, 'son.sfx.duree_aide', 'Durée en secondes (0,5 à 22) — 0 : durée choisie par le modèle',
      'Duration in seconds (0.5 to 22) — 0: duration chosen by the model'),
    L(61197, 'son.sfx.duree', 'Durée du son en secondes (0 : automatique)', 'Sound duration in seconds (0: automatic)'),
    X(61440, _DB),
    L(61564, 'son.sfx.generer_aide',
      'Générer 2 variations (~$0.03 — crédits ElevenLabs), sauvegardées dans la Bibliothèque (sons)',
      'Generate 2 variations (~$0.03 — ElevenLabs credits), saved to the Library (sounds)'),
    L(61743, 'son.commun.generation', 'génération…', 'generating…'),
    L(61757, 'son.commun.generer', 'Générer', 'Generate'),
    L(61857, 'son.commun.echec', 'Échec : ', 'Failed: '),
    X(62223, _DB),
    L(62231, 'son.commun.ecouter', 'Écouter', 'Play'),
    S(62270, '"Écouter "+(it.name||"variation "+(i2+1))',
      'dzT("son.sfx.ecouter_nom",{nom:it.name||dzT("son.sfx.variation",{n:i2+1})})',
      {'son.sfx.ecouter_nom': ('Écouter {nom}', 'Play {nom}'),
       'son.sfx.variation': ('variation {n}', 'variation {n}')}),
    S(62472, '"variation "+(i2+1)', 'dzT("son.sfx.variation",{n:i2+1})',
      {'son.sfx.variation': ('variation {n}', 'variation {n}')}),
    X(62810, 'CSS (flex)'),
    L(62845, 'son.sfx.sauvegardes', 'sauvegardés dans la Bibliothèque (sons) — le tiroir Sons du Montage les liste',
      'saved to the Library (sounds) — the Montage Sounds drawer lists them'),
    L(63079, 'son.sfx.ouvrir_montage', 'Ouvrir le Montage →', 'Open Montage →'),
    S(63170, '"deux variations jouables par génération — chaque son rejoint la Bibliothèque et le tiroir Sons du '
             'Montage ("+svmKeyLabelNow("sounds_drawer")+")"',
      'dzT("son.sfx.note",{touche:svmKeyLabelNow("sounds_drawer")})',
      {'son.sfx.note': ('deux variations jouables par génération — chaque son rejoint la Bibliothèque et le tiroir '
                        'Sons du Montage ({touche})',
                        'two playable variations per generation — each sound joins the Library and the Montage '
                        'Sounds drawer ({touche})')}),
    # DzSonVfx : carte SFX maquette (couche DzSfx absente)
    L(63405, 'son.sfx.pack_titre', 'Pack SFX généré', 'Generated SFX pack'),
    L(63623, 'son.commun.ecouter', 'Écouter', 'Play'),
    S(63646, '"Écouter "+s2.name', 'dzT("son.sfx.ecouter_nom",{nom:s2.name})',
      {'son.sfx.ecouter_nom': ('Écouter {nom}', 'Play {nom}')}),
    L(63707, 'son.sfx.sans_backend', "La génération de SFX n'a pas encore de backend — ces lignes sont la cible produit.",
      'SFX generation has no backend yet — these rows are the product target.'),

    # DzSonVfx : presets de post-traitement
    L(64371, 'son.post.titre', 'Presets de post-traitement', 'Post-processing presets'),
    L(64987, 'son.post.note', 'Les presets post passent par le moteur Effects / Mask existant au rendu (gratuit).',
      'Post presets go through the existing Effects / Mask engine at render time (free).'),

    # DzSonVfx : barre de titre, onglets, mesure LUFS
    L(66332, 'son.ecran.titre', 'Son & VFX', 'Sound & VFX'),
    X(66529, _DB),
    L(66663, 'son.ecran.onglet_vfx', 'VFX particules', 'Particle VFX'),
    L(66808, 'son.ecran.onglet_post', 'Post-traitement', 'Post-processing'),
    S(67183, '"dernière mesure ebur128"+(lastLufs.name?" — "+lastLufs.name:"")+" (Montage → Mesurer)"',
      'dzT("son.lufs.titre",{nom:lastLufs.name?" — "+lastLufs.name:""})',
      {'son.lufs.titre': ('dernière mesure ebur128{nom} (Montage → Mesurer)',
                          'last ebur128 measurement{nom} (Montage → Measure)')}),
    S(67294, '"dernier mix "+(Math.round(Number(lastLufs.i)*10)/10)+" LUFS I"',
      'dzT("son.lufs.dernier_mix",{i:Math.round(Number(lastLufs.i)*10)/10})',
      {'son.lufs.dernier_mix': ('dernier mix {i} LUFS I', 'last mix {i} LUFS I')}),
    S(67405, '" · pic vrai "+(Math.round(Number(lastLufs.tp)*10)/10)+" dBTP"',
      'dzT("son.lufs.pic_vrai",{tp:Math.round(Number(lastLufs.tp)*10)/10})',
      {'son.lufs.pic_vrai': (' · pic vrai {tp} dBTP', ' · true peak {tp} dBTP')}),

    # svmDemoClips : clips de démo du Montage — libellés et narration stockés dans le projet
    X(68014, 'libellé de clip de démo : stocké dans le projet'),
    X(68316, 'libellé de clip de démo : stocké dans le projet'),
    X(68436, "nom d'effet de démo : stocké dans le projet"),
    X(68460, "nom d'effet de démo : stocké dans le projet"),
    X(68742, 'texte de narration de démo : stocké dans le projet (champ du tiroir Narration)'),
    X(68932, 'texte de narration de démo : stocké dans le projet (champ du tiroir Narration)'),
    X(69060, 'libellé de clip de démo : stocké dans le projet'),
    X(69136, 'libellé de clip de démo : stocké dans le projet'),
    X(69195, 'libellé de clip de démo : stocké dans le projet'),
    X(69253, 'libellé de clip de démo : stocké dans le projet'),
    # SVM_TRACKS : type de piste
    X(69454, 'type de piste : comparé par montage.js (t.type==="vidéo")'),
    # SVM_RATIOS : libellés des formats (la valeur est l'élément 0, gardée)
    X(70536, _DB),
    X(70562, _DB),
    L(70601, 'son.format.carre', '1:1 · carré', '1:1 · square'),
    L(70624, 'son.format.paysage', '16:9 · paysage', '16:9 · landscape'),
    # svmBusDbTxt, svmMixRows : unités
    X(71004, _DB),
    X(71040, _DB),
    X(71231, _DB),
    X(71255, _DB),
    # svmV1Gaps : hachures des trous V1
    L(71692, 'son.piste.trou', 'trou — rendu en noir', 'gap — rendered black'),
    # SVM_TRANS : libellés des transitions (l'id backend, élément 0, est gardé)
    L(72162, 'son.transition.coupe_seche', 'coupe sèche', 'hard cut'),
    L(72185, 'son.transition.fondu', 'fondu', 'fade'),
    L(72206, 'son.transition.dissolution', 'dissolution', 'dissolve'),
    L(72237, 'son.transition.fondu_noir', 'fondu noir', 'fade to black'),
    L(72261, 'son.transition.pixelise', 'pixélisé', 'pixelate'),
    L(72282, 'son.transition.glissement', 'glissement', 'slide'),
    L(72305, 'son.transition.fondu_blanc', 'fondu blanc', 'fade to white'),
    # svmDbTxt, svmVpDbTxt : unités
    X(74262, _DB),
    X(74288, _DB),
    X(74294, _DB),
    X(76673, _DB),
    # SVM_FADE_CURVES / SVM_FADE_CURVE_TT : courbes de fondu (l'id, élément 0 / clé, est gardé)
    L(74569, 'son.courbe.lineaire', 'linéaire', 'linear'),
    L(74590, 'son.courbe.douce', 'douce', 'smooth'),
    L(74659, 'son.courbe.lineaire_aide', 'linéaire — défaut du rendu', 'linear — render default'),
    L(74698, 'son.courbe.douce_aide', 'douce — S sinusoïdal, entrée/sortie feutrées',
      'smooth — sine S-curve, soft in/out'),
    L(74754, 'son.courbe.expo_aide', 'expo — décollage tardif, arrivée brusque', 'expo — late take-off, abrupt arrival'),
    L(74805, 'son.courbe.log_aide', 'log — décollage rapide, arrivée feutrée', 'log — quick take-off, soft arrival'),
    # svmApplyTf : CSS
    X(86665, 'CSS (rotate(…deg))'),

    # SVM_ACTIONS : libellés des raccourcis (sections et combos gardées, voir plus bas)
    L(90419, 'son.raccourci.play', 'lecture / pause', 'play / pause'),
    L(90489, 'son.raccourci.jog_back', 'molette arrière — ×1 ×2 ×4', 'shuttle reverse — ×1 ×2 ×4'),
    L(90566, 'son.raccourci.jog_pause', 'molette : pause', 'shuttle: pause'),
    L(90630, 'son.raccourci.jog_fwd', 'molette avant — ×1 ×2 ×4', 'shuttle forward — ×1 ×2 ×4'),
    L(90705, 'son.raccourci.step_back', "reculer d'1 image (Maj : 10)", 'back 1 frame (Shift: 10)'),
    L(90783, 'son.raccourci.step_fwd', "avancer d'1 image (Maj : 10)", 'forward 1 frame (Shift: 10)'),
    L(90861, 'son.raccourci.cut_prev', 'coupe précédente', 'previous cut'),
    L(90927, 'son.raccourci.cut_next', 'coupe suivante', 'next cut'),
    L(90987, 'son.raccourci.home', 'début du montage', 'start of the edit'),
    L(91051, 'son.raccourci.end', 'fin du montage', 'end of the edit'),
    L(91119, 'son.raccourci.fullscreen', 'plein écran du cadre', 'frame full screen'),
    L(91190, 'son.raccourci.safezones', 'zones sûres (tiers, centre, marges)', 'safe zones (thirds, center, margins)'),
    L(91273, 'son.raccourci.delete', 'supprimer le clip (ou le losange ◇) sélectionné',
      'delete the selected clip (or diamond ◇)'),
    L(91371, 'son.raccourci.blade', 'lame — couper à la tête', 'blade — cut at the playhead'),
    L(91444, 'son.raccourci.undo', 'annuler', 'undo', contexte=True),
    L(91502, 'son.raccourci.redo', 'rétablir (Ctrl+Maj+annuler aussi)', 'redo (Ctrl+Shift+undo too)'),
    L(91586, 'son.raccourci.snap', 'aimanter (bords, tête, 0)', 'snap (edges, playhead, 0)'),
    L(91659, 'son.raccourci.ripple', 'ripple — refermer les trous', 'ripple — close the gaps'),
    L(91736, 'son.raccourci.range_in', "plage : point d'entrée à la tête", 'range: in point at the playhead'),
    L(91819, 'son.raccourci.range_out', 'plage : point de sortie à la tête', 'range: out point at the playhead'),
    L(91905, 'son.raccourci.range_clear', 'plage : effacer', 'range: clear'),
    L(91971, 'son.raccourci.range_cut', 'plage : couper (toutes pistes, ripple)', 'range: cut (all tracks, ripple)'),
    L(92068, 'son.raccourci.marker_toggle', 'marqueur : poser / retirer a la tete', 'marker: add / remove at the playhead'),
    L(92161, 'son.raccourci.marker_prev', 'marqueur precedent', 'previous marker'),
    L(92237, 'son.raccourci.marker_next', 'marqueur suivant', 'next marker'),
    L(92312, 'son.raccourci.marker_index', "marqueurs : l'index", 'markers: index'),
    L(92387, 'son.raccourci.swap_left', 'echanger avec le plan precedent', 'swap with the previous shot'),
    L(92475, 'son.raccourci.swap_right', 'echanger avec le plan suivant', 'swap with the next shot'),
    L(92560, 'son.raccourci.title_add', 'titre : poser un carton a la tete', 'title: add a title card at the playhead'),
    L(92649, 'son.raccourci.adjust_add', 'ajustement : poser un clip a la tete', 'adjustment: add a clip at the playhead'),
    L(92740, 'son.raccourci.trans_add', 'transition : fondu à la coupe du plan sélectionné',
      "transition: fade at the selected shot's cut"),
    L(92839, 'son.raccourci.copy', 'copier le clip (entre projets)', 'copy the clip (across projects)'),
    L(92921, 'son.raccourci.paste', 'coller le clip du presse-papiers à la tête de lecture',
      'paste the clipboard clip at the playhead'),
    L(93031, 'son.raccourci.grade_copy', 'grade : copier (effets couleur et masque du plan sélectionné)',
      'grade: copy (color effects and mask of the selected shot)'),
    L(93154, 'son.raccourci.grade_paste', 'grade : coller sur le plan sélectionné', 'grade: paste onto the selected shot'),
    L(93250, 'son.raccourci.vo_record', 'voix off : enregistrer / arrêter une prise au micro (lecture du montage)',
      'voice-over: record / stop a mic take (plays the edit)'),
    L(93377, 'son.raccourci.zoom_in', 'zoom avant (crans)', 'zoom in (steps)'),
    L(93452, 'son.raccourci.zoom_out', 'zoom arrière (crans)', 'zoom out (steps)'),
    X(93528, _DB),
    L(93595, 'son.raccourci.narration', 'panneau Narration (texte → voix)', 'Narration panel (text → voice)'),
    L(93678, 'son.raccourci.toolbar', "barre d'outils de création (onglet OUTILS)", 'creation toolbar (TOOLS tab)'),
    L(93774, 'son.raccourci.keys_panel', 'ouvrir / fermer ce panneau', 'open / close this panel'),
    L(94080, 'son.raccourci.sounds_drawer', 'tiroir Sons — bibliothèque + génération',
      'Sounds drawer — library + generation'),
    L(94163, 'son.raccourci.mute', 'muet — piste du clip audio sélectionné', 'mute — track of the selected audio clip'),
    L(94245, 'son.raccourci.solo', "solo d'écoute (Maj : multi-solo)", 'listening solo (Shift: multi-solo)'),
    L(94330, 'son.raccourci.fade_in_cycle', "fondu d'entrée — cycle 0 / 0,3 / 0,6 / 1 s",
      'fade in — cycle 0 / 0.3 / 0.6 / 1 s'),
    L(94426, 'son.raccourci.fade_out_cycle', 'fondu de sortie — même cycle', 'fade out — same cycle'),
    L(94508, 'son.raccourci.nudge_left', "décaler le clip d'1 image ← (Maj : 10)", 'nudge the clip 1 frame ← (Shift: 10)'),
    L(94601, 'son.raccourci.nudge_right', "décaler le clip d'1 image → (Maj : 10)",
      'nudge the clip 1 frame → (Shift: 10)'),
    L(94690, 'son.raccourci.gain_up', 'gain du clip audio +1 dB', 'audio clip gain +1 dB'),
    L(94767, 'son.raccourci.gain_down', 'gain du clip audio −1 dB', 'audio clip gain −1 dB'),
    # SVM_ACTIONS / SVM_KEY_SECTIONS / SVM_KEYS_INFO : sections (comparées)
    *[X(p, _SEC) for p in (
        90405, 90475, 90552, 90616, 90691, 90769, 90847, 90913, 90973, 91037, 91105, 91176, 91259, 91357, 91430,
        91488, 91572, 91645, 91722, 91805, 91891, 91957, 92054, 92147, 92223, 92298, 92373, 92461, 92546, 92635,
        92726, 92825, 92907, 93017, 93140, 93238, 93361, 93436, 93512, 93579, 93662, 93758, 94068, 94151, 94233,
        94318, 94414, 94496, 94589, 94678, 94755, 94921, 94931, 94941, 94953, 95149, 95239, 95413, 95507)],
    # SVM_ACTIONS : combos par défaut (analysées, comparées, stockées)
    *[X(p, _COMBO) for p in (
        90443, 91012, 91074, 91329, 91403, 91460, 91544, 92018, 92113, 92188, 92262, 92340, 92427, 92513, 92602,
        92694, 92798, 92878, 92983, 93101, 93201, 93331, 93404, 93481, 93547, 94463, 94555, 94648, 94723, 94800)],

    # SVM_KEYS_INFO : rappels non remappables (gestes souris, touche fixe)
    L(95165, 'son.raccourci.info_bord', 'bord de clip', 'clip edge'),
    L(95185, 'son.raccourci.info_rogner', 'glisser : rogner / allonger (geste souris)',
      'drag: trim / extend (mouse gesture)'),
    L(95309, 'son.raccourci.info_overlay',
      'overlay sélectionné : ces touches le déplacent de 0,5 % (Maj 2 % · Échap les rend à la tête)',
      'selected overlay: these keys move it by 0.5% (Shift 2% · Esc hands them back to the playhead)'),
    X(95431, "nom de touche : écrit comme les combos affichées à côté (gardées)"),
    L(95438, 'son.raccourci.info_molette', 'molette', 'wheel'),
    L(95453, 'son.raccourci.info_zoom', 'zoom continu sur le curseur (geste souris)',
      'continuous zoom at the cursor (mouse gesture)'),
    X(95525, "nom de touche : écrit comme les combos affichées à côté (gardées)"),
    L(95538, 'son.raccourci.info_echap', "fermer / annuler — touche fixe (panneaux, capture, flèches d'overlay)",
      'close / cancel — fixed key (panels, capture, overlay arrows)'),

    # SVM_EV_NAMES, SVM_EV_NAMED_SET, svmComboOfEvent : noms canoniques des touches (valeurs de combo)
    *[X(p, _COMBO) for p in (96314, 96332, 96407, 96425, 96438, 96453, 96465, 96481, 96493, 96582, 96593, 96745,
                             97369, 97391, 97434)],
    X(96732, 'KeyboardEvent.code comparé'),
    # SVM_COMBO_WORDS, svmComboCanon : canonisation d'une combo stockée
    *[X(p, _COMBO) for p in (97628, 97643, 97658, 97670, 97691, 97704, 97715, 97728, 97743, 97762, 97777, 97789,
                             98587, 98604, 98629)],
    # SVM_COMBO_RESERVED : combos refusées (clés d'objet comparées)
    *[X(p, _COMBO) for p in (98800, 98811, 98826, 98837, 98856, 98867, 98882, 98893, 98908, 98925, 98942, 98957,
                             98972, 98987)],
    # svmComboReserved : raison affichée inline (aussi lue comme booléen par svmKmLoad : non vide dans les deux langues)
    L(99066, 'son.raccourci.reserve_navigateur', 'raccourci du navigateur', 'browser shortcut'),
    L(99158, 'son.raccourci.reserve_touches_f', 'touches F réservées au navigateur', 'F keys are reserved for the browser'),
    X(99206, _COMBO),
    L(99221, 'son.raccourci.reserve_echap', "Échap reste la touche d'annulation", 'Esc stays the cancel key'),
    X(99270, _COMBO),
    L(99283, 'son.raccourci.reserve_tab', 'réservée à la navigation clavier', 'reserved for keyboard navigation'),
    X(99330, _COMBO),
    X(99344, _COMBO),
    L(99360, 'son.raccourci.reserve_entree', "réservée à l'activation des boutons", 'reserved for activating buttons'),
]
