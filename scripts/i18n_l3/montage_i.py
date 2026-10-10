"""t143 — montage_i : couche Montage (frontend/patches/montage.js), lignes 8926–fin de la base be7f9e9f. Couvre :
l'enregistrement d'une voix off au micro (DzmVoiceRec : notes d'erreur, toasts après sortie du Montage, aide et
libellé de la puce « ● voix off »), les scopes (DzmScopes : état, fenêtre flottante, aides), la lightbox des plans
(tuiles, titre, fermeture), les épingles du Studio (dzPinPreparer : messages renvoyés comme erreur du rendu) et le
lancement d'une recette depuis la Bibliothèque (dzRecLancerAvec : dialogues, choix, devis, confirmation, toast).

Gardés (X) : les types de nœuds COMPARÉS (« Seedance », « Concatenate », « Voiceover » dans dzPinRendu, dzPinTrouver,
dzPinRecolter, dzPropsNaissance) ; « Scopes » (identique dans les deux langues) ; « source(s) » du choix de recette
(identique) ; tout le SVG de dzMasqueSvg (balises et attributs d'un masque, jamais affichés) ; les unités CSS « px »
de dzTexteApercu ; les keyframes et durées CSS de dzAnimCss / dzAnimStyle ; le paramètre d'URL « ?provider= » de
dzVoListe ; le texte « Texte » de dzArcRayon (seulement mesuré pour estimer le rayon d'un arc, jamais affiché).
« épingle inconnue » est traduit : c'est la raison montrée par « Épingle retirée : {raison} », jamais comparée.

Phrases recomposées (S) : chaque note faite de morceaux concaténés devient UNE clé à variables ; la confirmation de
lancement d'une recette (trois lignes) garde ses deux fins de ligne dans le dzT(…) (le contrôle des restes range les
littéraux par numéro de ligne). Les bouts optionnels (« , n voix off », « , n nœud(s) réemployé(s) ») et la suite de
la note « réponse illisible » sont des clés à part, passées en variable."""
from outils import L, S, X

CIBLE = "montage"

FRAGMENTS = {}

_NON_ENREG = ('prise non enregistrée', 'take not saved')
_MICRO = ('Micro indisponible : {e}', 'Microphone unavailable: {e}')
_SCOPES = 'identique dans les deux langues (nom de l’outil)'
_LANCER_TITRE = ('Lancer une recette', 'Run a recipe')
_SVG = 'SVG technique du masque (balise / attribut), jamais affiché'
_PX = 'unité CSS (style calculé)'
_ANIM = 'CSS technique (keyframes / animation), jamais affiché'
_TYPE = 'type de nœud du Studio COMPARÉ (n.type===, de(…), type===)'

ENTREES = [
    # DzmVoiceRec : enregistrement d'une voix off au micro (notes, toasts, aide et libellé de la puce)
    L(572511, 'montage.prise.vide', "Prise vide : rien n'a été capté — prise non enregistrée",
      'Empty take: nothing was captured — take not saved'),
    S(573352, '"Voix off : la prise « "+d.filename+" » est dans la Bibliothèque — le Montage a été quitté pendant '
              'l\'envoi, elle n\'a pas été posée."',
      'dzT("montage.prise.quitte_biblio",{f:d.filename})',
      {'montage.prise.quitte_biblio': (
          "Voix off : la prise « {f} » est dans la Bibliothèque — le Montage a été quitté pendant l'envoi, elle n'a "
          "pas été posée.",
          'Voice-over: the take “{f}” is in the Library — the Montage was left during the upload, so it was not '
          'placed.')}),
    L(573495, 'montage.prise.quitte_illisible',
      'Voix off : réponse illisible du serveur après la sortie du Montage — prise non enregistrée.',
      'Voice-over: unreadable server response after leaving the Montage — take not saved.'),
    S(573736, '"Voix off : réponse illisible du serveur — "+(d&&d.filename?"la prise « "+d.filename+" » est dans la '
              'Bibliothèque, non posée":"prise non enregistrée")',
      'dzT("montage.prise.illisible",{suite:d&&d.filename?dzT("montage.prise.illisible_biblio",{f:d.filename})'
      ':dzT("montage.prise.non_enregistree")})',
      {'montage.prise.illisible': ('Voix off : réponse illisible du serveur — {suite}',
                                   'Voice-over: unreadable server response — {suite}'),
       'montage.prise.illisible_biblio': ('la prise « {f} » est dans la Bibliothèque, non posée',
                                          'the take “{f}” is in the Library, not placed'),
       'montage.prise.non_enregistree': _NON_ENREG}),
    S(573990, '"Voix off : envoi de la prise impossible ("+dzmVoErr(e)+") — prise non enregistrée."',
      'dzT("montage.prise.envoi_quitte",{e:dzmVoErr(e)})',
      {'montage.prise.envoi_quitte': ('Voix off : envoi de la prise impossible ({e}) — prise non enregistrée.',
                                      'Voice-over: could not upload the take ({e}) — take not saved.')}),
    S(574118, '"Envoi de la prise impossible : "+dzmVoErr(e)+" — prise non enregistrée"',
      'dzT("montage.prise.envoi_impossible",{e:dzmVoErr(e)})',
      {'montage.prise.envoi_impossible': ('Envoi de la prise impossible : {e} — prise non enregistrée',
                                          'Could not upload the take: {e} — take not saved')}),
    L(574237, 'montage.prise.demo', 'Voix off : disponible sur un projet réel — la démo est une maquette.',
      'Voice-over: available on a real project — the demo is a mock-up.'),
    L(574728, 'montage.prise.navigateur',
      "Micro indisponible : ce navigateur n'enregistre pas le son ici (page non sûre ou fonction absente)",
      'Microphone unavailable: this browser cannot record sound here (insecure page or missing feature)'),
    S(575342, '"Micro indisponible : "+dzmVoErr(e)', 'dzT("montage.prise.micro_indispo",{e:dzmVoErr(e)})',
      {'montage.prise.micro_indispo': _MICRO}),
    S(575585, '"Enregistreur arrêté : "+dzmVoErr(ev&&ev.error?ev.error:ev)',
      'dzT("montage.prise.enregistreur_arrete",{e:dzmVoErr(ev&&ev.error?ev.error:ev)})',
      {'montage.prise.enregistreur_arrete': ('Enregistreur arrêté : {e}', 'Recorder stopped: {e}')}),
    S(575952, '"Enregistrement impossible : "+dzmVoErr(e)',
      'dzT("montage.prise.enregistrement_impossible",{e:dzmVoErr(e)})',
      {'montage.prise.enregistrement_impossible': ('Enregistrement impossible : {e}', 'Could not record: {e}')}),
    S(576083, '"Micro indisponible : "+dzmVoErr(e)', 'dzT("montage.prise.micro_indispo",{e:dzmVoErr(e)})',
      {'montage.prise.micro_indispo': _MICRO}),
    S(576299, '"Arrêt impossible : "+dzmVoErr(e)+" — prise non enregistrée"',
      'dzT("montage.prise.arret_impossible",{e:dzmVoErr(e)})',
      {'montage.prise.arret_impossible': ('Arrêt impossible : {e} — prise non enregistrée',
                                          'Could not stop: {e} — take not saved')}),
    L(576499, 'montage.prise.micro_en_cours', 'Voix off : accès au micro en cours…',
      'Voice-over: accessing the microphone…'),
    L(576566, 'montage.prise.envoi_en_cours', "Voix off : prise en cours d'envoi…", 'Voice-over: uploading the take…'),
    L(576791, 'montage.prise.demo_aide', "Projet de démonstration : l'enregistrement d'une voix off est désactivé",
      'Demo project: voice-over recording is disabled'),
    L(576884, 'montage.prise.micro_aide', 'Accès au micro en cours — autorisez-le dans le navigateur',
      'Accessing the microphone — allow it in the browser'),
    L(576963, 'montage.prise.envoi_aide', 'Envoi de la prise en cours…', 'Uploading the take…'),
    S(577012, '"Arrêter la prise ("+el+")"+cb+" — elle sera posée sur la piste de dialogue à l\'instant où elle a '
              'commencé"',
      'dzT("montage.prise.arreter_aide",{t:el,touche:cb})',
      {'montage.prise.arreter_aide': (
          "Arrêter la prise ({t}){touche} — elle sera posée sur la piste de dialogue à l'instant où elle a commencé",
          'Stop the take ({t}){touche} — it will be placed on the dialogue track at the moment it started')}),
    S(577126, '"Enregistrer une voix off au micro"+cb+" — le montage est lu pendant la prise, qui est posée sur la '
              'piste de dialogue à la tête de lecture (mode « écraser »)"',
      'dzT("montage.prise.enregistrer_aide",{touche:cb})',
      {'montage.prise.enregistrer_aide': (
          'Enregistrer une voix off au micro{touche} — le montage est lu pendant la prise, qui est posée sur la piste '
          'de dialogue à la tête de lecture (mode « écraser »)',
          'Record a voice-over with the microphone{touche} — the edit plays during the take, which is placed on the '
          'dialogue track at the playhead (“overwrite” mode)')}),
    L(577525, 'montage.prise.puce_micro', 'micro…', 'mic…'),
    L(577547, 'montage.prise.puce_envoi', 'envoi…', 'sending…'),
    L(577556, 'montage.prise.puce', '● voix off', '● voice-over'),

    # DzmScopes : forme d'onde, vecteurscope, histogramme du plan sous la tête
    S(584257, '"Scopes indisponibles : "+((e&&e.message)||"erreur réseau")',
      'dzT("montage.scopes.indispo",{e:(e&&e.message)||dzT("montage.mots.erreur_reseau")})',
      {'montage.scopes.indispo': ('Scopes indisponibles : {e}', 'Scopes unavailable: {e}'),
       'montage.mots.erreur_reseau': ('erreur réseau', 'network error')}),
    L(587870, 'montage.scopes.lecture', "Lecture : les scopes se rafraîchissent à l'arrêt",
      'Playing: the scopes refresh when stopped'),
    L(587924, 'montage.scopes.aucun_plan', 'Aucun plan lisible sous la tête', 'No readable clip under the playhead'),
    L(587999, 'montage.scopes.mesure', 'Mesure en cours…', 'Measuring…'),
    X(588109, _SCOPES),
    L(588250, 'montage.scopes.deplacer', 'Déplacer la fenêtre des scopes (glisser la barre de titre)',
      'Move the scopes window (drag the title bar)'),
    X(588399, _SCOPES),
    L(588461, 'montage.scopes.fermer_aide', 'Fermer les scopes (comme la puce « Scopes » de la barre du lecteur)',
      'Close the scopes (like the “Scopes” chip in the player bar)'),
    L(588554, 'montage.scopes.fermer', 'Fermer les scopes', 'Close the scopes'),
    L(588761, 'montage.scopes.image', 'Scopes du plan sous la tête', 'Scopes of the clip under the playhead'),
    S(588807, '"Forme d\'onde (haut), vecteurscope et histogramme (bas) de l\'image étalonnée à "+body.t+" s de source"',
      'dzT("montage.scopes.image_aide",{t:body.t})',
      {'montage.scopes.image_aide': (
          "Forme d'onde (haut), vecteurscope et histogramme (bas) de l'image étalonnée à {t} s de source",
          'Waveform (top), vectorscope and histogram (bottom) of the graded frame at {t} s of source')}),
    S(589058, '"Redimensionner les scopes (carré, "+DZM_SCW_MIN+" à "+DZM_SCW_MAX+" px)"',
      'dzT("montage.scopes.redimensionner",{min:DZM_SCW_MIN,max:DZM_SCW_MAX})',
      {'montage.scopes.redimensionner': ('Redimensionner les scopes (carré, {min} à {max} px)',
                                         'Resize the scopes (square, {min} to {max} px)')}),
    L(589541, 'montage.scopes.masquer', 'Masquer les scopes', 'Hide the scopes'),
    L(589562, 'montage.scopes.afficher',
      "Afficher les scopes du plan V1 sous la tête (forme d'onde, vecteurscope, histogramme de l'image étalonnée) — "
      "rafraîchis à l'arrêt, jamais pendant la lecture",
      'Show the scopes of the V1 clip under the playhead (waveform, vectorscope, histogram of the graded frame) — '
      'refreshed when stopped, never during playback'),
    X(589754, _SCOPES),

    # DzmLightbox : la lightbox des plans de V1
    S(592751, '"Aller au plan « "+lbl+" » (début à "+dzmCoR(dzmRfNum(c.start),2)+" s) et le sélectionner"',
      'dzT("montage.lbplans.aller",{nom:lbl,t:dzmCoR(dzmRfNum(c.start),2)})',
      {'montage.lbplans.aller': ('Aller au plan « {nom} » (début à {t} s) et le sélectionner',
                                 'Go to clip “{nom}” (starts at {t} s) and select it')}),
    S(592923, '"Plan « "+lbl+" » étalonné"', 'dzT("montage.lbplans.etalonne",{nom:lbl})',
      {'montage.lbplans.etalonne': ('Plan « {nom} » étalonné', 'Clip “{nom}”, graded')}),
    L(593016, 'montage.lbplans.sans_source', 'sans source', 'no source'),
    L(593037, 'montage.lbplans.image_indispo', 'image indisponible', 'image unavailable'),
    L(593058, 'montage.lbplans.calcul', 'calcul…', 'computing…'),
    L(593355, 'montage.lbplans.titre', 'Lightbox des plans', 'Clip lightbox'),
    S(593494, '"Lightbox des plans · V1 ("+pl.length+")"', 'dzT("montage.lbplans.titre_n",{n:pl.length})',
      {'montage.lbplans.titre_n': ('Lightbox des plans · V1 ({n})', 'Clip lightbox · V1 ({n})')}),
    L(593605, 'montage.lbplans.fermer_aide', 'Fermer la lightbox (Échap, ou clic hors de la grille)',
      'Close the lightbox (Esc, or click outside the grid)'),
    L(593682, 'montage.mots.fermer', 'Fermer', 'Close'),
    L(593812, 'montage.lbplans.vide', 'Aucun plan sur V1', 'No clips on V1'),

    # dzPinRendu, dzPinReemploi, dzPinTrouver, dzPinRecolter : types de nœuds comparés
    X(606715, _TYPE),
    X(606775, _TYPE),
    X(606892, _TYPE),
    X(607512, _TYPE),
    X(610969, _TYPE),
    # dzPinPreparer : messages rendus comme erreur du rendu (renderLayoutTemplate -> {ok:false, error})
    L(608774, 'montage.epingles.verif_impossible',
      "Vérification des épingles impossible — rien n'est parti. Relancez dans un instant.",
      'Could not check the pins — nothing was sent. Try again in a moment.'),
    L(609007, 'montage.epingles.inconnue', 'épingle inconnue', 'unknown pin'),
    S(609221, '"Épingle périmée — "+perimes.join(" ; ")+". Elle est retirée et le coût recalculé : relancez pour '
              'régénérer."',
      'dzT("montage.epingles.perimee",{liste:perimes.join(" ; ")})',
      {'montage.epingles.perimee': (
          'Épingle périmée — {liste}. Elle est retirée et le coût recalculé : relancez pour régénérer.',
          'Stale pin — {liste}. It has been removed and the cost recalculated: run again to regenerate.')}),

    # dzRecLancerAvec : lancer une recette avec une image de la Bibliothèque
    L(633497, 'montage.recette.aucune',
      'Aucune recette : dans le Studio, fige un graphe composé avec le bouton « Recette ».',
      'No recipe: in the Studio, freeze a composed graph with the “Recipe” button.'),
    L(633590, 'montage.recette.lancer_titre', *_LANCER_TITRE),
    X(633741, 'identique dans les deux langues'),
    S(633764, '"Lancer quelle recette avec « "+image+" » ?"', 'dzT("montage.recette.laquelle",{image:image})',
      {'montage.recette.laquelle': ('Lancer quelle recette avec « {image} » ?', 'Run which recipe with “{image}”?')}),
    S(634030, '"Recette illisible ("+R.status+")."', 'dzT("montage.recette.illisible",{code:R.status})',
      {'montage.recette.illisible': ('Recette illisible ({code}).', 'Unreadable recipe ({code}).')}),
    L(634074, 'montage.recette.lancer_titre', *_LANCER_TITRE),
    S(634302, '"La recette « "+rec.name+" » n’a aucune image à remplacer."',
      'dzT("montage.recette.sans_image",{nom:rec.name})',
      {'montage.recette.sans_image': ('La recette « {nom} » n’a aucune image à remplacer.',
                                      'Recipe “{nom}” has no image to replace.')}),
    L(634369, 'montage.recette.lancer_titre', *_LANCER_TITRE),
    S(634494, 't.libelle+" (aujourd’hui : "+t.valeur+")"',
      'dzT("montage.recette.trou_valeur",{libelle:t.libelle,valeur:t.valeur})',
      {'montage.recette.trou_valeur': ('{libelle} (aujourd’hui : {valeur})', '{libelle} (currently: {valeur})')}),
    S(634546, '"« "+image+" » remplace quelle image ?"', 'dzT("montage.recette.quelle_image",{image:image})',
      {'montage.recette.quelle_image': ('« {image} » remplace quelle image ?', 'Which image does “{image}” replace?')}),
    S(634750, 't.libelle+" — garde-le ou change-le :"', 'dzT("montage.recette.texte_garder",{libelle:t.libelle})',
      {'montage.recette.texte_garder': ('{libelle} — garde-le ou change-le :', '{libelle} — keep it or change it:')}),
    S(634796, '"Recette « "+rec.name+" » ("+(i+1)+"/"+txts.length+")"',
      'dzT("montage.recette.texte_titre",{nom:rec.name,i:i+1,n:txts.length})',
      {'montage.recette.texte_titre': ('Recette « {nom} » ({i}/{n})', 'Recipe “{nom}” ({i}/{n})')}),
    L(634870, 'montage.mots.suivant', 'Suivant', 'Next'),
    S(635274, '"Devis impossible ("+Dv.status+")."', 'dzT("montage.recette.devis_code",{code:Dv.status})',
      {'montage.recette.devis_code': ('Devis impossible ({code}).', 'Quote failed ({code}).')}),
    L(635318, 'montage.recette.devis_titre', 'Devis impossible', 'Quote failed'),
    S(635424, '"Lancer « "+rec.name+" » avec « "+image+" » : ≈ $"+usd.toFixed(2)+" — "+dv.generations+" génération(s)"'
              '\r\n      +(dv.voix?", "+dv.voix+" voix off":"")+(dv.reemplois?", "+dv.reemplois+" nœud(s) réemployé(s) '
              'gratuitement":"")\r\n      +". Le rendu part dans la file ; plus cher que ce devis, il serait refusé '
              'avant toute génération."',
      'dzT("montage.recette.confirmer",{nom:rec.name,image:image,usd:usd.toFixed(2),n:dv.generations,'
      '\r\n      voix:dv.voix?dzT("montage.recette.confirmer_voix",{n:dv.voix}):"",'
      'reemplois:dv.reemplois?dzT("montage.recette.confirmer_reemplois",{n:dv.reemplois}):""\r\n      })',
      {'montage.recette.confirmer': (
          'Lancer « {nom} » avec « {image} » : ≈ ${usd} — {n} génération(s){voix}{reemplois}. Le rendu part dans la '
          'file ; plus cher que ce devis, il serait refusé avant toute génération.',
          'Run “{nom}” with “{image}”: ≈ ${usd} — {n} generation(s){voix}{reemplois}. The render goes into the '
          'queue; if it costs more than this quote, it is refused before any generation.'),
       'montage.recette.confirmer_voix': (', {n} voix off', ', {n} voice-over(s)'),
       'montage.recette.confirmer_reemplois': (', {n} nœud(s) réemployé(s) gratuitement',
                                               ', {n} node(s) reused for free')}),
    L(635760, 'montage.recette.lancer_la', 'Lancer la recette', 'Run the recipe'),
    S(635783, '"Lancer ($"+usd.toFixed(2)+")"', 'dzT("montage.recette.lancer_prix",{usd:usd.toFixed(2)})',
      {'montage.recette.lancer_prix': ('Lancer (${usd})', 'Run (${usd})')}),
    S(636137, '"Recette « "+rec.name+" » lancée (≈ $"+usd.toFixed(2)+") — le rendu est dans la file"',
      'dzT("montage.recette.lancee",{nom:rec.name,usd:usd.toFixed(2)})',
      {'montage.recette.lancee': ('Recette « {nom} » lancée (≈ ${usd}) — le rendu est dans la file',
                                  'Recipe “{nom}” launched (≈ ${usd}) — the render is in the queue')}),
    S(636289, '"Lancement refusé ("+Ln.status+")."', 'dzT("montage.recette.refus_code",{code:Ln.status})',
      {'montage.recette.refus_code': ('Lancement refusé ({code}).', 'Launch refused ({code}).')}),
    L(636333, 'montage.recette.refus_titre', 'Lancement refusé', 'Launch refused'),
    S(636402, '"Recette : "+String(e&&e.message||e)', 'dzT("montage.recette.erreur",{e:String(e&&e.message||e)})',
      {'montage.recette.erreur': ('Recette : {e}', 'Recipe: {e}')}),
    L(636446, 'montage.recette.lancer_titre', *_LANCER_TITRE),

    # dzPropsNaissance : types de nœuds comparés
    X(638744, _TYPE),
    X(638806, _TYPE),

    # dzMasqueSvg : le masque d'une région en SVG (technique)
    X(652905, _SVG), X(652957, _SVG), X(653015, _SVG), X(653059, _SVG), X(653082, _SVG), X(653098, _SVG),
    X(653114, _SVG), X(653220, _SVG), X(653397, _SVG), X(653427, _SVG), X(653442, _SVG), X(653567, _SVG),
    X(653615, _SVG), X(653641, _SVG), X(653660, _SVG), X(653677, _SVG), X(653721, _SVG), X(653751, _SVG),
    X(653769, _SVG), X(653788, _SVG), X(653866, _SVG), X(653930, _SVG), X(653964, _SVG),
    X(654008, 'URL data: CSS du masque (dzMasqueUrl)'),

    # dzTexteApercu : unités du style calculé
    X(662715, _PX), X(662820, _PX), X(662848, _PX), X(662878, _PX), X(663499, _PX),
    # dzArcRayon : texte par défaut seulement mesuré (estimation du rayon d'un arc), jamais affiché
    X(664223, 'texte mesuré pour estimer le rayon de l’arc, jamais affiché'),

    # dzAnimCss / dzAnimStyle : keyframes et durées CSS
    X(678686, _ANIM), X(678727, _ANIM), X(678766, _ANIM), X(678806, _ANIM), X(678840, _ANIM), X(678901, _ANIM),
    X(678943, _ANIM), X(678981, _ANIM), X(679022, _ANIM), X(679055, _ANIM), X(679142, _ANIM), X(679182, _ANIM),
    X(679597, _ANIM), X(679829, _ANIM),

    # dzVoListe : paramètre d'URL
    X(773964, 'paramètre de requête envoyé au serveur'),
]
