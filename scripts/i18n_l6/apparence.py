"""t146 — apparence : panneau Apparence + et pinceau vectoriel (js/mod-apparence2.js), panneau Apparence/Style
(js/mod-style.js), nuancier et harmonies (js/mod-couleur.js), effets/motifs purs (js/mod-effets.js), Sélecteur de
couleur (js/mod-pipetteui.js, js/mod-pipette.js), familles d'outils (js/mod-familles.js).

GARDÉ : les ids comparés ou stockés (cle « couleur »/« largeur » des champs d'effet, types « texte »/« image »/
« calque », valeurs d'alignement « gauche… » écrites dans le document — l'option reçoit value= et le libellé est
traduit à part, attributs « fond »/« contour »/« type » de selection_par_attribut, noms de champ « largeur »/« pas »
cités par les messages de validation), noms d'icônes dz-*, sélecteurs, chemins de module, textes identiques dans les
deux langues (« Global », « Image », « transparent »…).
Les messages d'erreur des ops/validations (couleur attendue, effet inconnu, déjà dans la palette…) sont traduits :
ils remontent au toast. Les lettres de canaux du nuancier (V → G, J → Y, N → K) sont des clés « contexte ».
"""
from outils import L, S, X

A = "js/mod-apparence2.js"
ST = "js/mod-style.js"
C = "js/mod-couleur.js"
EF = "js/mod-effets.js"
PU = "js/mod-pipetteui.js"
P = "js/mod-pipette.js"
F = "js/mod-familles.js"

ICONE = "nom d'icône dz-*, pas affiché"


def tr(cle):
    return '${T("' + cle + '")}'


ENTREES = [
    # ───────────────────────── mod-apparence2.js ─────────────────────────
    X(A, 14, '"./mod-couleur.js"', "chemin de module"),
    L(A, 21, '"Pinceau vectoriel à profil — largeur, profil et angle dans Apparence + (J)"',
      "vectorlab.apparence.outil_pinceauv",
      "Pinceau vectoriel à profil — largeur, profil et angle dans Apparence + (J)",
      "Vector brush with profile — width, profile and angle in Appearance + (J)"),
    L(A, 24, '"dessiner : le trait devient un chemin fermé rempli, à la largeur et au profil choisis (plat, fuseau, calligraphie)"',
      "vectorlab.apparence.hint_pinceauv",
      "dessiner : le trait devient un chemin fermé rempli, à la largeur et au profil choisis (plat, fuseau, calligraphie)",
      "draw: the stroke becomes a filled closed path, at the chosen width and profile (flat, taper, calligraphy)"),
]

# les libellés des champs d'effet (lib), la clé (cle) reste
_CHAMP = {"flou": ("flou", "blur"), "couleur": ("couleur", "color"), "profondeur": ("profondeur", "depth"),
          "largeur": ("largeur", "width")}
for ligne, libs in [(29, ["flou", "couleur"]), (30, ["flou", "couleur"]), (31, ["flou", "couleur"]),
                    (32, ["profondeur", "flou"]), (33, ["largeur", "couleur"]), (34, ["couleur"])]:
    for lib in libs:
        cle = "vectorlab.apparence.champ_" + lib
        ENTREES.append(S(A, ligne, f'lib: "{lib}"', f'lib: T("{cle}")', {cle: _CHAMP[lib]}))
    ENTREES.append(L(A, ligne, '"opacité"', "vectorlab.apparence.champ_opacite", "opacité", "opacity"))
for ligne in (29, 30, 31, 33, 34):
    ENTREES.append(X(A, ligne, '"couleur"', "cle du champ d'effet (comparée, écrite dans le document)", n=2))
ENTREES += [
    L(A, 32, '"lumière °"', "vectorlab.apparence.champ_lumiere", "lumière °", "light °"),
    X(A, 33, '"largeur"', "cle du champ d'effet (écrite dans le document)", n=2),
    X(A, 41, '"couleur"', "cle du champ comparée"),
    S(A, 53, '`flou ${e.flou}`', 'T("vectorlab.apparence.flou_n", { n: e.flou })',
      {"vectorlab.apparence.flou_n": ("flou {n}", "blur {n}")}),
    X(A, 137, '"texte"', "type d'objet comparé"),
    S(A, 141,
      '<div class="ap-ligne a2-edition" title="Édition du symbole en place : ses objets sont dans le calque « ${esc((d.calques.find((c) => c.id === ed.calque) || {}).nom || "")} ». Terminer réécrit le symbole — toutes ses instances suivent."><b style="flex:1">✎ Symbole « ${esc((symboles[ed.sid] || {}).nom || ed.sid)} »</b>',
      '<div class="ap-ligne a2-edition" title="${T("vectorlab.apparence.edition_titre", { calque: esc((d.calques.find((c) => c.id === ed.calque) || {}).nom || "") })}"><b style="flex:1">✎ ${T("vectorlab.apparence.edition_symbole", { nom: esc((symboles[ed.sid] || {}).nom || ed.sid) })}</b>',
      {"vectorlab.apparence.edition_titre": (
          "Édition du symbole en place : ses objets sont dans le calque « {calque} ». Terminer réécrit le symbole — toutes ses instances suivent.",
          "Editing the symbol in place: its objects are on the layer “{calque}”. Finish rewrites the symbol — all its instances follow."),
       "vectorlab.apparence.edition_symbole": ("Symbole « {nom} »", "Symbol “{nom}”")}),
    S(A, 142,
      '''title="Réécrit le symbole depuis le calque d'édition (Échap, sélection vide)">Terminer</button><button id="a2SymAnnule" title="Jette les modifications du calque d'édition">Abandonner</button>''',
      'title="' + tr("vectorlab.apparence.terminer_titre") + '">' + tr("vectorlab.apparence.terminer")
      + '</button><button id="a2SymAnnule" title="' + tr("vectorlab.apparence.abandonner_titre") + '">'
      + tr("vectorlab.apparence.abandonner") + '</button>',
      {"vectorlab.apparence.terminer_titre": ("Réécrit le symbole depuis le calque d'édition (Échap, sélection vide)",
                                               "Rewrites the symbol from the editing layer (Esc, empty selection)"),
       "vectorlab.apparence.terminer": ("Terminer", "Done"),
       "vectorlab.apparence.abandonner_titre": ("Jette les modifications du calque d'édition",
                                                 "Discards the changes made on the editing layer"),
       "vectorlab.apparence.abandonner": ("Abandonner", "Discard")}),
    S(A, 143, '<summary class="px-tete">Effets${', '<summary class="px-tete">' + tr("vectorlab.apparence.effets") + '${',
      {"vectorlab.apparence.effets": ("Effets", "Effects")}),
]
for ligne in (144, 153):
    ENTREES.append(S(A, ligne, 'title="Retirer" aria-label="Retirer"',
                     'title="' + tr("vectorlab.apparence.retirer") + '" aria-label="' + tr("vectorlab.apparence.retirer") + '"',
                     {"vectorlab.apparence.retirer": ("Retirer", "Remove")}))
for ligne in (144, 153, 159, 168, 174):
    ENTREES.append(X(A, ligne, '"dz-action-supprimer"', ICONE))
for ligne in (149, 154, 169, 175):
    ENTREES.append(X(A, ligne, '"dz-action-ajouter"', ICONE))
ENTREES += [
    L(A, 146, '''"Couleur de l'effet"''', "vectorlab.apparence.couleur_effet", "Couleur de l'effet", "Effect color"),
    S(A, 149, ''' title="Ajoute l'effet à la sélection" aria-label="Ajoute l'effet à la sélection">''',
      ' title="' + tr("vectorlab.apparence.fx_plus") + '" aria-label="' + tr("vectorlab.apparence.fx_plus") + '">',
      {"vectorlab.apparence.fx_plus": ("Ajoute l'effet à la sélection", "Adds the effect to the selection")}),
    S(A, 151, '<summary class="px-tete">Fusion &amp; contours</summary>',
      '<summary class="px-tete">' + tr("vectorlab.apparence.fusion_contours") + '</summary>',
      {"vectorlab.apparence.fusion_contours": ("Fusion & contours", "Blend & strokes")}),
    S(A, 152, '<span>Fusion</span>', '<span>' + tr("vectorlab.apparence.fusion") + '</span>',
      {"vectorlab.apparence.fusion": ("Fusion", "Blend")}),
    L(A, 153, '"Couleur du contour"', "vectorlab.apparence.couleur_contour", "Couleur du contour", "Stroke color"),
    S(A, 153, '" title="Épaisseur"/>', '" title="' + tr("vectorlab.apparence.epaisseur") + '"/>',
      {"vectorlab.apparence.epaisseur": ("Épaisseur", "Thickness")}),
    S(A, 154, ' title="Ajoute un contour supplémentaire (derrière, plus large)">',
      ' title="' + tr("vectorlab.apparence.contour_plus") + '">',
      {"vectorlab.apparence.contour_plus": ("Ajoute un contour supplémentaire (derrière, plus large)",
                                            "Adds an extra stroke (behind, wider)")}),
    S(A, 154, ')}contour</button>', ')}' + tr("vectorlab.apparence.contour_btn") + '</button>',
      {"vectorlab.apparence.contour_btn": ("contour", "stroke")}),
    S(A, 156, '<summary class="px-tete">Remplissage +</summary>',
      '<summary class="px-tete">' + tr("vectorlab.apparence.remplissage_plus") + '</summary>',
      {"vectorlab.apparence.remplissage_plus": ("Remplissage +", "Fill +")}),
    S(A, 157, ''' title="Dégradé conique centré sur l'objet">''', ' title="' + tr("vectorlab.apparence.conique_titre") + '">',
      {"vectorlab.apparence.conique_titre": ("Dégradé conique centré sur l'objet", "Conical gradient centered on the object")}),
    S(A, 157, '<span class="dzi-lib">Conique</span>', '<span class="dzi-lib">' + tr("vectorlab.apparence.conique") + '</span>',
      {"vectorlab.apparence.conique": ("Conique", "Conical")}),
    S(A, 158, ' title="Dégradé de transparence (masque de gauche à droite)">', ' title="' + tr("vectorlab.apparence.transp_titre") + '">',
      {"vectorlab.apparence.transp_titre": ("Dégradé de transparence (masque de gauche à droite)",
                                            "Transparency gradient (mask from left to right)")}),
    X(A, 158, '"dz-outil-vec-transparence"', ICONE),
    S(A, 158, '<span class="dzi-lib">Transparence</span>', '<span class="dzi-lib">' + tr("vectorlab.apparence.transparence") + '</span>',
      {"vectorlab.apparence.transparence": ("Transparence", "Transparency")}),
    S(A, 159, ' title="Retire le masque de transparence">', ' title="' + tr("vectorlab.apparence.masque_x_titre") + '">',
      {"vectorlab.apparence.masque_x_titre": ("Retire le masque de transparence", "Removes the transparency mask")}),
    S(A, 159, '<span class="dzi-lib">masque</span>', '<span class="dzi-lib">' + tr("vectorlab.apparence.masque") + '</span>',
      {"vectorlab.apparence.masque": ("masque", "mask")}),
    S(A, 160,
      '</select>\r\n          <input type="number" id="a2MotifPas" min="1" value="8" title="Pas (px)"/>',
      '</select>\r\n          <input type="number" id="a2MotifPas" min="1" value="8" title="' + tr("vectorlab.apparence.motif_pas") + '"/>',
      {"vectorlab.apparence.motif_pas": ("Pas (px)", "Spacing (px)")}),
    S(A, 162, ''' title="Remplit la sélection d'un motif (couleur du contour courant)">''', ' title="' + tr("vectorlab.apparence.motif_titre") + '">',
      {"vectorlab.apparence.motif_titre": ("Remplit la sélection d'un motif (couleur du contour courant)",
                                           "Fills the selection with a pattern (current stroke color)")}),
    S(A, 162, ')}motif</button>', ')}' + tr("vectorlab.apparence.motif") + '</button>',
      {"vectorlab.apparence.motif": ("motif", "pattern")}),
    S(A, 163, ' title="Coller dans : le PREMIER objet sélectionné rogne les autres">', ' title="' + tr("vectorlab.apparence.ecreter_titre") + '">',
      {"vectorlab.apparence.ecreter_titre": ("Coller dans : le PREMIER objet sélectionné rogne les autres",
                                             "Paste inside: the FIRST selected object clips the others")}),
    X(A, 163, '"dz-calque-ecretage"', ICONE),
    S(A, 163, 'coller dans</button>', tr("vectorlab.apparence.coller_dans") + '</button>',
      {"vectorlab.apparence.coller_dans": ("coller dans", "paste inside")}),
    S(A, 164, ' title="Libère les objets rognés">libérer</button>',
      ' title="' + tr("vectorlab.apparence.liberer_titre") + '">' + tr("vectorlab.apparence.liberer") + '</button>',
      {"vectorlab.apparence.liberer_titre": ("Libère les objets rognés", "Releases the clipped objects"),
       "vectorlab.apparence.liberer": ("libérer", "release")}),
    S(A, 166, '<summary class="px-tete">Couleurs globales</summary>',
      '<summary class="px-tete">' + tr("vectorlab.apparence.globales") + '</summary>',
      {"vectorlab.apparence.globales": ("Couleurs globales", "Global colors")}),
    L(A, 167, '"Changer la teinte partout"', "vectorlab.apparence.glob_teinte", "Changer la teinte partout", "Change the color everywhere"),
    S(A, 168, ' title="Fond de la sélection = cette couleur globale">fond</button>',
      ' title="' + tr("vectorlab.apparence.glob_fond_titre") + '">' + tr("vectorlab.apparence.glob_fond") + '</button>',
      {"vectorlab.apparence.glob_fond_titre": ("Fond de la sélection = cette couleur globale", "Selection fill = this global color"),
       "vectorlab.apparence.glob_fond": ("fond", "fill")}),
    S(A, 168, ' title="Contour = cette couleur">contour</button>',
      ' title="' + tr("vectorlab.apparence.glob_contour_titre") + '">' + tr("vectorlab.apparence.contour_btn") + '</button>',
      {"vectorlab.apparence.glob_contour_titre": ("Contour = cette couleur", "Stroke = this color"),
       "vectorlab.apparence.contour_btn": ("contour", "stroke")}),
    S(A, 168, '" title="Supprimer (les références deviennent des hex)" aria-label="Supprimer la couleur globale">',
      '" title="' + tr("vectorlab.apparence.glob_x_titre") + '" aria-label="' + tr("vectorlab.apparence.glob_x") + '">',
      {"vectorlab.apparence.glob_x_titre": ("Supprimer (les références deviennent des hex)", "Delete (references become hex values)"),
       "vectorlab.apparence.glob_x": ("Supprimer la couleur globale", "Delete the global color")}),
    S(A, 169, 'placeholder="nom"', 'placeholder="' + tr("vectorlab.apparence.nom") + '"',
      {"vectorlab.apparence.nom": ("nom", "name")}),
    L(A, 169, '"Couleur à enregistrer"', "vectorlab.apparence.glob_hex", "Couleur à enregistrer", "Color to save"),
    S(A, 169, '<button id="a2GlobPlus" title="Enregistre une couleur globale" aria-label="Enregistre une couleur globale">',
      '<button id="a2GlobPlus" title="' + tr("vectorlab.apparence.glob_plus") + '" aria-label="' + tr("vectorlab.apparence.glob_plus") + '">',
      {"vectorlab.apparence.glob_plus": ("Enregistre une couleur globale", "Saves a global color")}),
    S(A, 170, '''</select><button id="a2HarmGen" title="Génère l'harmonie depuis la couleur de fond et l'ajoute à la palette du document">harmonie</button>''',
      '</select><button id="a2HarmGen" title="' + tr("vectorlab.apparence.harmonie_titre") + '">' + tr("vectorlab.apparence.harmonie") + '</button>',
      {"vectorlab.apparence.harmonie_titre": ("Génère l'harmonie depuis la couleur de fond et l'ajoute à la palette du document",
                                              "Generates the harmony from the fill color and adds it to the document palette"),
       "vectorlab.apparence.harmonie": ("harmonie", "harmony")}),
    X(A, 171, '<button class="px-pastille" data-couleur="', "HTML : attribut data-couleur, pas affiché"),
    S(A, 171, 'title="${c} — clic : fond de la sélection"', 'title="${T("vectorlab.apparence.harmonie_pastille", { c })}"',
      {"vectorlab.apparence.harmonie_pastille": ("{c} — clic : fond de la sélection", "{c} — click: selection fill")}),
    S(A, 173, '''<summary class="px-tete">Styles d'objet</summary>''',
      '<summary class="px-tete">' + tr("vectorlab.apparence.styles") + '</summary>',
      {"vectorlab.apparence.styles": ("Styles d'objet", "Object styles")}),
    S(A, 174, ' title="Applique (copie) ce style à la sélection">appliquer</button>',
      ' title="' + tr("vectorlab.apparence.st_app_titre") + '">' + tr("vectorlab.apparence.appliquer") + '</button>',
      {"vectorlab.apparence.st_app_titre": ("Applique (copie) ce style à la sélection", "Applies (copies) this style to the selection"),
       "vectorlab.apparence.appliquer": ("appliquer", "apply")}),
    S(A, 174, '" title="Supprimer le style" aria-label="Supprimer le style">',
      '" title="' + tr("vectorlab.apparence.st_x") + '" aria-label="' + tr("vectorlab.apparence.st_x") + '">',
      {"vectorlab.apparence.st_x": ("Supprimer le style", "Delete style")}),
    S(A, 174, '\r\n        <div class="ap-ligne"><input type="text" id="a2StNom" placeholder="nom du style"',
      '\r\n        <div class="ap-ligne"><input type="text" id="a2StNom" placeholder="' + tr("vectorlab.apparence.st_nom") + '"',
      {"vectorlab.apparence.st_nom": ("nom du style", "style name")}),
    S(A, 175, ''' title="Enregistre l'apparence de la sélection sous ce nom" aria-label="Enregistre l'apparence de la sélection sous ce nom">''',
      ' title="' + tr("vectorlab.apparence.st_plus") + '" aria-label="' + tr("vectorlab.apparence.st_plus") + '">',
      {"vectorlab.apparence.st_plus": ("Enregistre l'apparence de la sélection sous ce nom", "Saves the selection's appearance under this name")}),
    S(A, 177, '<details open><summary class="px-tete">Texte +</summary>',
      '<details open><summary class="px-tete">' + tr("vectorlab.apparence.texte_plus") + '</summary>',
      {"vectorlab.apparence.texte_plus": ("Texte +", "Text +")}),
    X(A, 178, '"texte"', "type d'objet comparé"),
    S(A, 178,
      '<div class="ap-ligne"><span>Cadre</span><input type="number" id="a2CadreW" min="1" value="200" title="Largeur"/><input type="number" id="a2CadreH" min="1" value="100" title="Hauteur"/><button id="a2EnCadre" title="Le texte devient un cadre à paragraphes">',
      '<div class="ap-ligne"><span>' + tr("vectorlab.apparence.cadre") + '</span><input type="number" id="a2CadreW" min="1" value="200" title="'
      + tr("vectorlab.apparence.largeur") + '"/><input type="number" id="a2CadreH" min="1" value="100" title="' + tr("vectorlab.apparence.hauteur")
      + '"/><button id="a2EnCadre" title="' + tr("vectorlab.apparence.en_cadre_titre") + '">',
      {"vectorlab.apparence.cadre": ("Cadre", "Frame"),
       "vectorlab.apparence.largeur": ("Largeur", "Width"),
       "vectorlab.apparence.hauteur": ("Hauteur", "Height"),
       "vectorlab.apparence.en_cadre_titre": ("Le texte devient un cadre à paragraphes", "The text becomes a paragraph frame")}),
    S(A, 178, ')}cadre</button>', ')}' + tr("vectorlab.apparence.cadre_btn") + '</button>',
      {"vectorlab.apparence.cadre_btn": ("cadre", "frame")}),
    S(A, 179, '<span>Aligner</span>', '<span>' + tr("vectorlab.apparence.aligner") + '</span>',
      {"vectorlab.apparence.aligner": ("Aligner", "Align")}),
    S(A, 179, '<option${(s.aligner || "gauche") === a ? " selected" : ""}>${a}</option>',
      '<option value="${a}"${(s.aligner || "gauche") === a ? " selected" : ""}>${({ gauche: T("vectorlab.apparence.aligner_gauche"), centre: T("vectorlab.apparence.aligner_centre"), droite: T("vectorlab.apparence.aligner_droite"), justifie: T("vectorlab.apparence.aligner_justifie") })[a] || a}</option>',
      {"vectorlab.apparence.aligner_gauche": ("gauche", "left"),
       "vectorlab.apparence.aligner_centre": ("centre", "center"),
       "vectorlab.apparence.aligner_droite": ("droite", "right"),
       "vectorlab.apparence.aligner_justifie": ("justifié", "justified")}),
    S(A, 180, '<span>Interl.</span>', '<span>' + tr("vectorlab.apparence.interl") + '</span>',
      {"vectorlab.apparence.interl": ("Interl.", "Leading")}),
    S(A, 180, 'title="Interligne (× corps)"', 'title="' + tr("vectorlab.apparence.interligne_titre") + '"',
      {"vectorlab.apparence.interligne_titre": ("Interligne (× corps)", "Leading (× font size)")}),
    S(A, 180, '" title="Retrait de première ligne (px)"/></div>', '" title="' + tr("vectorlab.apparence.retrait_titre") + '"/></div>',
      {"vectorlab.apparence.retrait_titre": ("Retrait de première ligne (px)", "First-line indent (px)")}),
    S(A, 181, ' title="Sélectionner le texte PUIS un chemin : le texte se pose sur le chemin et le SUIT quand il change">',
      ' title="' + tr("vectorlab.apparence.sur_chemin_titre") + '">',
      {"vectorlab.apparence.sur_chemin_titre": ("Sélectionner le texte PUIS un chemin : le texte se pose sur le chemin et le SUIT quand il change",
                                                "Select the text THEN a path: the text sits on the path and FOLLOWS it when it changes")}),
    X(A, 181, '"dz-outil-vec-texte-sur-chemin"', ICONE),
    S(A, 181, 'sur le chemin</button></div>', tr("vectorlab.apparence.sur_chemin") + '</button></div>',
      {"vectorlab.apparence.sur_chemin": ("sur le chemin", "on path")}),
    S(A, 182,
      '<div class="ap-ligne"><i class="px-note" style="flex:1">suit le chemin ${esc(o1.chemin)}</i><button id="a2Detacher" title="Le texte ne suit plus son chemin : son tracé actuel est figé">',
      '<div class="ap-ligne"><i class="px-note" style="flex:1">${T("vectorlab.apparence.suit_chemin", { chemin: esc(o1.chemin) })}</i><button id="a2Detacher" title="'
      + tr("vectorlab.apparence.detacher_texte_titre") + '">',
      {"vectorlab.apparence.suit_chemin": ("suit le chemin {chemin}", "follows path {chemin}"),
       "vectorlab.apparence.detacher_texte_titre": ("Le texte ne suit plus son chemin : son tracé actuel est figé",
                                                    "The text no longer follows its path: its current shape is frozen")}),
]
for ligne in (182, 186):
    ENTREES.append(S(A, ligne, 'détacher</button></div>', tr("vectorlab.apparence.detacher") + '</button></div>',
                     {"vectorlab.apparence.detacher": ("détacher", "detach")}))
ENTREES += [
    S(A, 183, '<div class="ap-ligne"><span>Décalage</span>', '<div class="ap-ligne"><span>' + tr("vectorlab.apparence.decalage") + '</span>',
      {"vectorlab.apparence.decalage": ("Décalage", "Offset")}),
    S(A, 185, '<summary class="px-tete">Contour vivant</summary>',
      '<summary class="px-tete">' + tr("vectorlab.apparence.vivant") + '</summary>',
      {"vectorlab.apparence.vivant": ("Contour vivant", "Live contour")}),
    S(A, 186,
      '${esc(o1.derive.decalage)} px autour de ${esc(o1.derive.source)} — se recalcule quand la source change</i><button id="a2Detacher" title="Le contour ne suit plus sa source : il devient un chemin ordinaire">',
      '${T("vectorlab.apparence.vivant_note", { d: esc(o1.derive.decalage), source: esc(o1.derive.source) })}</i><button id="a2Detacher" title="'
      + tr("vectorlab.apparence.vivant_detacher_titre") + '">',
      {"vectorlab.apparence.vivant_note": ("{d} px autour de {source} — se recalcule quand la source change",
                                           "{d} px around {source} — recomputed when the source changes"),
       "vectorlab.apparence.vivant_detacher_titre": ("Le contour ne suit plus sa source : il devient un chemin ordinaire",
                                                     "The contour no longer follows its source: it becomes an ordinary path")}),
    S(A, 188,
      '><summary class="px-tete">Pinceau vectoriel (J)</summary>\r\n        <div class="ap-ligne"><span>Largeur</span>',
      '><summary class="px-tete">' + tr("vectorlab.apparence.pinceauv") + '</summary>\r\n        <div class="ap-ligne"><span>'
      + tr("vectorlab.apparence.largeur") + '</span>',
      {"vectorlab.apparence.pinceauv": ("Pinceau vectoriel (J)", "Vector brush (J)"),
       "vectorlab.apparence.largeur": ("Largeur", "Width")}),
    S(A, 190, '" title="Angle de la plume (calligraphie)"/>', '" title="' + tr("vectorlab.apparence.angle_plume") + '"/>',
      {"vectorlab.apparence.angle_plume": ("Angle de la plume (calligraphie)", "Nib angle (calligraphy)")}),
    L(A, 239, '"nom de couleur globale requis"', "vectorlab.apparence.glob_nom_requis", "nom de couleur globale requis", "global color name required"),
    S(A, 247, '`harmonie ${type} : ${pal.join(" ")}`', 'T("vectorlab.apparence.harmonie_toast", { type, pal: pal.join(" ") })',
      {"vectorlab.apparence.harmonie_toast": ("harmonie {type} : {pal}", "{type} harmony: {pal}")}),
    X(A, 249, '"#a2HarmPal [data-couleur]"', "sélecteur CSS"),
    L(A, 251, '"nom de style requis"', "vectorlab.apparence.st_nom_requis", "nom de style requis", "style name required"),
    L(A, 290, '"édition du symbole en place — modifier ses objets, puis Échap (sélection vide) ou « Terminer »"',
      "vectorlab.apparence.edition_toast",
      "édition du symbole en place — modifier ses objets, puis Échap (sélection vide) ou « Terminer »",
      "editing the symbol in place — change its objects, then Esc (empty selection) or “Finish”"),
    S(A, 299, '`symbole réécrit (${n} objet(s)) — toutes ses instances suivent`',
      'T("vectorlab.apparence.symbole_reecrit", { n })',
      {"vectorlab.apparence.symbole_reecrit": ("symbole réécrit ({n} objet(s)) — toutes ses instances suivent",
                                               "symbol rewritten ({n} object(s)) — all its instances follow")}),

    # ───────────────────────── mod-style.js ─────────────────────────
    L(ST, 17, '"plein"', "vectorlab.style.trait_plein", "plein", "solid"),
    L(ST, 17, '"tirets"', "vectorlab.style.trait_tirets", "tirets", "dashed"),
    L(ST, 17, '"points"', "vectorlab.style.trait_points", "points", "dotted"),
    L(ST, 46, '"sélectionne UN objet pour poser un dégradé"', "vectorlab.style.degrade_un",
      "sélectionne UN objet pour poser un dégradé", "select ONE object to apply a gradient"),
    S(ST, 104, '"\r\n               title="X de la sélection (${suf})"', '"\r\n               title="${T("vectorlab.style.x_titre", { suf })}"',
      {"vectorlab.style.x_titre": ("X de la sélection ({suf})", "Selection X ({suf})")}),
    S(ST, 106, '"\r\n               title="Y de la sélection (${suf})"', '"\r\n               title="${T("vectorlab.style.y_titre", { suf })}"',
      {"vectorlab.style.y_titre": ("Y de la sélection ({suf})", "Selection Y ({suf})")}),
    S(ST, 109, '<span>L · H</span>', '<span>' + tr("vectorlab.style.l_h") + '</span>',
      {"vectorlab.style.l_h": ("L · H", "W · H")}),
    S(ST, 110, '"\r\n               title="Largeur (${suf})"', '"\r\n               title="${T("vectorlab.style.largeur_titre", { suf })}"',
      {"vectorlab.style.largeur_titre": ("Largeur ({suf})", "Width ({suf})")}),
    S(ST, 112, '"\r\n               title="Hauteur (${suf})"', '"\r\n               title="${T("vectorlab.style.hauteur_titre", { suf })}"',
      {"vectorlab.style.hauteur_titre": ("Hauteur ({suf})", "Height ({suf})")}),
    S(ST, 117, '<span>Fond</span>', '<span>' + tr("vectorlab.style.fond") + '</span>',
      {"vectorlab.style.fond": ("Fond", "Fill")}),
    S(ST, 119, '"\r\n                title="Couleur de fond — ouvre le nuancier (RGB, CMJN, hex, palettes)">',
      '"\r\n                title="' + tr("vectorlab.style.fond_titre") + '">',
      {"vectorlab.style.fond_titre": ("Couleur de fond — ouvre le nuancier (RGB, CMJN, hex, palettes)",
                                      "Fill color — opens the color picker (RGB, CMYK, hex, palettes)")}),
    S(ST, 121, '"\r\n                title="Sans fond" aria-label="Sans fond">',
      '"\r\n                title="' + tr("vectorlab.style.sans_fond") + '" aria-label="' + tr("vectorlab.style.sans_fond") + '">',
      {"vectorlab.style.sans_fond": ("Sans fond", "No fill", "contexte")}),
    X(ST, 122, '"dz-edit-sans-couleur"', ICONE),
    S(ST, 122, '</button>\r\n        <button id="apGradL" title="Dégradé linéaire (sélection unique)" aria-label="Dégradé linéaire">',
      '</button>\r\n        <button id="apGradL" title="' + tr("vectorlab.style.grad_l_titre") + '" aria-label="' + tr("vectorlab.style.grad_l") + '">',
      {"vectorlab.style.grad_l_titre": ("Dégradé linéaire (sélection unique)", "Linear gradient (single selection)"),
       "vectorlab.style.grad_l": ("Dégradé linéaire", "Linear gradient")}),
    S(ST, 123, '</button>\r\n        <button id="apGradR" title="Dégradé radial (sélection unique)" aria-label="Dégradé radial">',
      '</button>\r\n        <button id="apGradR" title="' + tr("vectorlab.style.grad_r_titre") + '" aria-label="' + tr("vectorlab.style.grad_r") + '">',
      {"vectorlab.style.grad_r_titre": ("Dégradé radial (sélection unique)", "Radial gradient (single selection)"),
       "vectorlab.style.grad_r": ("Dégradé radial", "Radial gradient")}),
    S(ST, 126, '<span>Contour</span>', '<span>' + tr("vectorlab.style.contour") + '</span>',
      {"vectorlab.style.contour": ("Contour", "Stroke")}),
    S(ST, 129, '"\r\n                title="Couleur de contour — ouvre le nuancier">',
      '"\r\n                title="' + tr("vectorlab.style.contour_titre") + '">',
      {"vectorlab.style.contour_titre": ("Couleur de contour — ouvre le nuancier", "Stroke color — opens the color picker")}),
    S(ST, 132, '"\r\n                title="Sans contour" aria-label="Sans contour">',
      '"\r\n                title="' + tr("vectorlab.style.sans_contour") + '" aria-label="' + tr("vectorlab.style.sans_contour") + '">',
      {"vectorlab.style.sans_contour": ("Sans contour", "No stroke")}),
    X(ST, 133, '"dz-edit-sans-contour"', ICONE),
    S(ST, 135,
      '" title="Épaisseur"/>\r\n      </div>\r\n      <div class="ap-ligne"><span>Trait</span>\r\n        <select id="apPointilles" title="Pointillés">',
      '" title="' + tr("vectorlab.style.epaisseur") + '"/>\r\n      </div>\r\n      <div class="ap-ligne"><span>' + tr("vectorlab.style.trait")
      + '</span>\r\n        <select id="apPointilles" title="' + tr("vectorlab.style.pointilles") + '">',
      {"vectorlab.style.epaisseur": ("Épaisseur", "Thickness"),
       "vectorlab.style.trait": ("Trait", "Line style", "contexte"),
       "vectorlab.style.pointilles": ("Pointillés", "Dashes", "contexte")}),
    S(ST, 140, '</select>\r\n        <select id="apJoint" title="Joint des angles">',
      '</select>\r\n        <select id="apJoint" title="' + tr("vectorlab.style.joint") + '">',
      {"vectorlab.style.joint": ("Joint des angles", "Corner join")}),
    S(ST, 143, '</select>\r\n      </div>\r\n      <div class="ap-ligne"><span>Opacité</span>',
      '</select>\r\n      </div>\r\n      <div class="ap-ligne"><span>' + tr("vectorlab.style.opacite") + '</span>',
      {"vectorlab.style.opacite": ("Opacité", "Opacity")}),
    S(ST, 149, '<span>Incliner</span>', '<span>' + tr("vectorlab.style.incliner") + '</span>',
      {"vectorlab.style.incliner": ("Incliner", "Skew")}),
    S(ST, 150, 'title="Inclinaison horizontale skewX (°)"', 'title="' + tr("vectorlab.style.kx_titre") + '"',
      {"vectorlab.style.kx_titre": ("Inclinaison horizontale skewX (°)", "Horizontal skew skewX (°)")}),
    S(ST, 151, 'title="Inclinaison verticale skewY (°)"', 'title="' + tr("vectorlab.style.ky_titre") + '"',
      {"vectorlab.style.ky_titre": ("Inclinaison verticale skewY (°)", "Vertical skew skewY (°)")}),
    S(ST, 152, ' title="Incline la sélection autour du pivot (⌖ déplaçable sur la scène)" aria-label="Incliner la sélection">',
      ' title="' + tr("vectorlab.style.incliner_titre") + '" aria-label="' + tr("vectorlab.style.incliner_sel") + '">',
      {"vectorlab.style.incliner_titre": ("Incline la sélection autour du pivot (⌖ déplaçable sur la scène)",
                                          "Skews the selection around the pivot (⌖ can be moved on the canvas)"),
       "vectorlab.style.incliner_sel": ("Incliner la sélection", "Skew the selection")}),
    S(ST, 152, '</button>\r\n        <button id="apPivotRaz" title="Ramène le pivot au centre de la sélection" aria-label="Ramène le pivot au centre de la sélection">',
      '</button>\r\n        <button id="apPivotRaz" title="' + tr("vectorlab.style.pivot_raz") + '" aria-label="' + tr("vectorlab.style.pivot_raz") + '">',
      {"vectorlab.style.pivot_raz": ("Ramène le pivot au centre de la sélection", "Moves the pivot back to the center of the selection")}),
    S(ST, 153,
      '</button>\r\n      </div>\r\n      <div class="ap-ligne"><span>Puissance</span>\r\n'
      '        <input type="number" id="apPn" min="1" max="200" value="3" title="Nombre de copies"/>\r\n'
      '        <input type="number" id="apPdx" step="any" value="20" title="Décalage X par copie (px)"/>\r\n'
      '        <input type="number" id="apPdy" step="any" value="0" title="Décalage Y par copie (px)"/>\r\n'
      '      </div>\r\n      <div class="ap-ligne"><span></span>\r\n'
      '        <input type="number" id="apProt" step="1" value="0" title="Rotation par copie (°)"/>\r\n'
      '        <input type="number" id="apPech" step="0.05" min="0.05" value="1" title="Échelle par copie"/>',
      '</button>\r\n      </div>\r\n      <div class="ap-ligne"><span>' + tr("vectorlab.style.puissance") + '</span>\r\n'
      '        <input type="number" id="apPn" min="1" max="200" value="3" title="' + tr("vectorlab.style.p_n") + '"/>\r\n'
      '        <input type="number" id="apPdx" step="any" value="20" title="' + tr("vectorlab.style.p_dx") + '"/>\r\n'
      '        <input type="number" id="apPdy" step="any" value="0" title="' + tr("vectorlab.style.p_dy") + '"/>\r\n'
      '      </div>\r\n      <div class="ap-ligne"><span></span>\r\n'
      '        <input type="number" id="apProt" step="1" value="0" title="' + tr("vectorlab.style.p_rot") + '"/>\r\n'
      '        <input type="number" id="apPech" step="0.05" min="0.05" value="1" title="' + tr("vectorlab.style.p_ech") + '"/>',
      {"vectorlab.style.puissance": ("Puissance", "Power"),
       "vectorlab.style.p_n": ("Nombre de copies", "Number of copies"),
       "vectorlab.style.p_dx": ("Décalage X par copie (px)", "X offset per copy (px)"),
       "vectorlab.style.p_dy": ("Décalage Y par copie (px)", "Y offset per copy (px)"),
       "vectorlab.style.p_rot": ("Rotation par copie (°)", "Rotation per copy (°)"),
       "vectorlab.style.p_ech": ("Échelle par copie", "Scale per copy")}),
    S(ST, 163, ' title="Duplication puissance : n copies qui répètent la transformation (nombre, décalage X · Y, rotation, échelle)" aria-label="Duplication puissance">',
      ' title="' + tr("vectorlab.style.puissance_titre") + '" aria-label="' + tr("vectorlab.style.puissance_btn") + '">',
      {"vectorlab.style.puissance_titre": ("Duplication puissance : n copies qui répètent la transformation (nombre, décalage X · Y, rotation, échelle)",
                                           "Power duplicate: n copies that repeat the transformation (count, X · Y offset, rotation, scale)"),
       "vectorlab.style.puissance_btn": ("Duplication puissance", "Power duplicate")}),
    S(ST, 165, '<span>Attribut</span>', '<span>' + tr("vectorlab.style.attribut") + '</span>',
      {"vectorlab.style.attribut": ("Attribut", "Attribute")}),
    S(ST, 166, '${["fond", "contour", "type"].map((k) => ',
      '${[["fond", T("vectorlab.style.attr_fond")], ["contour", T("vectorlab.style.attr_contour")], ["type", T("vectorlab.style.attr_type")]].map(([k, lib]) => ',
      {"vectorlab.style.attr_fond": ("fond", "fill"),
       "vectorlab.style.attr_contour": ("contour", "stroke"),
       "vectorlab.style.attr_type": ("type", "type")}),
    S(ST, 166, ' title="Sélectionner tous les objets de même ${k}">${k}</button>',
      ' title="${T("vectorlab.style.attr_titre", { k: lib })}">${lib}</button>',
      {"vectorlab.style.attr_titre": ("Sélectionner tous les objets de même {k}", "Select all objects with the same {k}")}),
    S(ST, 166,
      '\r\n      </div>\r\n      <div class="ap-ligne"><span>Décaler</span>\r\n        <input type="number" id="apDecal" step="any" value="5" title="Décalage en px : + vers le dehors, − vers le dedans"/>',
      '\r\n      </div>\r\n      <div class="ap-ligne"><span>' + tr("vectorlab.style.decaler") + '</span>\r\n        <input type="number" id="apDecal" step="any" value="5" title="'
      + tr("vectorlab.style.decal_titre") + '"/>',
      {"vectorlab.style.decaler": ("Décaler", "Offset"),
       "vectorlab.style.decal_titre": ("Décalage en px : + vers le dehors, − vers le dedans", "Offset in px: + outward, − inward")}),
    S(ST, 170, ''' title="Crée un chemin décalé (copie au-dessus de l'original)">décaler</button>''',
      ' title="' + tr("vectorlab.style.decaler_titre") + '">' + tr("vectorlab.style.decaler_btn") + '</button>',
      {"vectorlab.style.decaler_titre": ("Crée un chemin décalé (copie au-dessus de l'original)", "Creates an offset path (copy above the original)"),
       "vectorlab.style.decaler_btn": ("décaler", "offset")}),
    S(ST, 173, '<span>Rayon</span>', '<span>' + tr("vectorlab.style.rayon") + '</span>',
      {"vectorlab.style.rayon": ("Rayon", "Radius")}),
    S(ST, 175, '''"\r\n               title="Rayon d'angle du rectangle (px du document, borné à min(L,H)/2 ; 0 = angles vifs)"/>''',
      '"\r\n               title="' + tr("vectorlab.style.rayon_titre") + '"/>',
      {"vectorlab.style.rayon_titre": ("Rayon d'angle du rectangle (px du document, borné à min(L,H)/2 ; 0 = angles vifs)",
                                       "Rectangle corner radius (document px, capped at min(W,H)/2; 0 = sharp corners)")}),
    S(ST, 179, '<div class="ap-stops" title="Stops du dégradé du fond">',
      '<div class="ap-stops" title="' + tr("vectorlab.style.stops_titre") + '">',
      {"vectorlab.style.stops_titre": ("Stops du dégradé du fond", "Fill gradient stops")}),
    S(ST, 182, '"\r\n                  title="Couleur du stop — ouvre le nuancier">',
      '"\r\n                  title="' + tr("vectorlab.style.stop_titre") + '">',
      {"vectorlab.style.stop_titre": ("Couleur du stop — ouvre le nuancier", "Stop color — opens the color picker")}),
    S(ST, 186, '" title="Retirer ce stop" aria-label="Retirer ce stop">',
      '" title="' + tr("vectorlab.style.stop_x") + '" aria-label="' + tr("vectorlab.style.stop_x") + '">',
      {"vectorlab.style.stop_x": ("Retirer ce stop", "Remove this stop")}),
    X(ST, 186, '"dz-action-supprimer"', ICONE),
    S(ST, 187, '\r\n        <button id="apStopPlus" title="Ajouter un stop médian">',
      '\r\n        <button id="apStopPlus" title="' + tr("vectorlab.style.stop_plus") + '">',
      {"vectorlab.style.stop_plus": ("Ajouter un stop médian", "Add a middle stop")}),
    X(ST, 188, '"dz-action-ajouter"', ICONE),
    S(ST, 188, ')}stop</button>', ')}' + tr("vectorlab.style.stop") + '</button>',
      {"vectorlab.style.stop": ("stop", "stop")}),

    # ───────────────────────── mod-couleur.js ─────────────────────────
    S(C, 11, '`couleur attendue en #RRGGBB : ${hex}`', 'T("vectorlab.couleur.err_hex_en", { hex })',
      {"vectorlab.couleur.err_hex_en": ("couleur attendue en #RRGGBB : {hex}", "color expected as #RRGGBB: {hex}")}),
    L(C, 105, '"Complémentaire"', "vectorlab.couleur.harm_complementaire", "Complémentaire", "Complementary"),
    L(C, 106, '"Analogue"', "vectorlab.couleur.harm_analogue", "Analogue", "Analogous"),
    L(C, 107, '"Triade"', "vectorlab.couleur.harm_triade", "Triade", "Triadic"),
    L(C, 108, '"Tétrade"', "vectorlab.couleur.harm_tetrade", "Tétrade", "Tetradic"),
    L(C, 109, '"Monochrome"', "vectorlab.couleur.harm_monochrome", "Monochrome", "Monochrome"),
    S(C, 112, '`couleur #RRGGBB attendue : ${hex}`', 'T("vectorlab.couleur.err_hex", { v: hex })',
      {"vectorlab.couleur.err_hex": ("couleur #RRGGBB attendue : {v}", "#RRGGBB color expected: {v}")}),
    S(C, 113, '`harmonie inconnue : ${type}`', 'T("vectorlab.couleur.harm_inconnue", { type })',
      {"vectorlab.couleur.harm_inconnue": ("harmonie inconnue : {type}", "unknown harmony: {type}")}),
    S(C, 149, '`déjà dans la palette : ${h}`', 'T("vectorlab.couleur.deja_palette", { h })',
      {"vectorlab.couleur.deja_palette": ("déjà dans la palette : {h}", "already in the palette: {h}")}),
    S(C, 159, '`absente de la palette : ${h}`', 'T("vectorlab.couleur.absente_palette", { h })',
      {"vectorlab.couleur.absente_palette": ("absente de la palette : {h}", "not in the palette: {h}")}),
    S(C, 174,
      '\r\n      <canvas id="nuSV" width="188" height="132" title="Saturation / valeur"></canvas>\r\n'
      '      <vl-curseur-couleur id="nuH" mode="teinte" value="0" title="Teinte"></vl-curseur-couleur>\r\n'
      '      <div class="nu-ligne">\r\n'
      '        <span class="nu-bloc" id="nuAvant" title="Couleur d\'origine"></span>\r\n'
      '        <span class="nu-bloc" id="nuApres" title="Nouvelle couleur"></span>\r\n'
      '        <input id="nuHex" type="text" maxlength="7" spellcheck="false"\r\n'
      '               title="Hexadécimal #RRGGBB"/>\r\n'
      '      </div>\r\n'
      '      <div class="nu-ligne nu-champs">\r\n'
      '        <label>R<input data-rgb="r" type="number" min="0" max="255"/></label>\r\n'
      '        <label>V<input data-rgb="g" type="number" min="0" max="255"/></label>\r\n'
      '        <label>B<input data-rgb="b" type="number" min="0" max="255"/></label>\r\n'
      '      </div>\r\n'
      '      <div class="nu-ligne nu-champs"\r\n'
      '           title="CMJN indicatif — conversion naïve, sans profil ICC">\r\n'
      '        <label>C<input data-cmjn="c" type="number" min="0" max="100"/></label>\r\n'
      '        <label>M<input data-cmjn="m" type="number" min="0" max="100"/></label>\r\n'
      '        <label>J<input data-cmjn="j" type="number" min="0" max="100"/></label>\r\n'
      '        <label>N<input data-cmjn="n" type="number" min="0" max="100"/></label>\r\n'
      '      </div>\r\n'
      '      <div class="nu-tete">Palette du document\r\n'
      '        <button id="nuPalPlus"\r\n'
      '          title="Ajouter la couleur courante à la palette du document (annulable, sauvée avec lui)" aria-label="Ajouter la couleur courante à la palette du document">',
      '\r\n      <canvas id="nuSV" width="188" height="132" title="' + tr("vectorlab.couleur.sv") + '"></canvas>\r\n'
      '      <vl-curseur-couleur id="nuH" mode="teinte" value="0" title="' + tr("vectorlab.couleur.teinte") + '"></vl-curseur-couleur>\r\n'
      '      <div class="nu-ligne">\r\n'
      '        <span class="nu-bloc" id="nuAvant" title="' + tr("vectorlab.couleur.origine") + '"></span>\r\n'
      '        <span class="nu-bloc" id="nuApres" title="' + tr("vectorlab.couleur.nouvelle") + '"></span>\r\n'
      '        <input id="nuHex" type="text" maxlength="7" spellcheck="false"\r\n'
      '               title="' + tr("vectorlab.couleur.hexa") + '"/>\r\n'
      '      </div>\r\n'
      '      <div class="nu-ligne nu-champs">\r\n'
      '        <label>R<input data-rgb="r" type="number" min="0" max="255"/></label>\r\n'
      '        <label>' + tr("vectorlab.couleur.canal_v") + '<input data-rgb="g" type="number" min="0" max="255"/></label>\r\n'
      '        <label>B<input data-rgb="b" type="number" min="0" max="255"/></label>\r\n'
      '      </div>\r\n'
      '      <div class="nu-ligne nu-champs"\r\n'
      '           title="' + tr("vectorlab.couleur.cmjn_titre") + '">\r\n'
      '        <label>C<input data-cmjn="c" type="number" min="0" max="100"/></label>\r\n'
      '        <label>M<input data-cmjn="m" type="number" min="0" max="100"/></label>\r\n'
      '        <label>' + tr("vectorlab.couleur.canal_j") + '<input data-cmjn="j" type="number" min="0" max="100"/></label>\r\n'
      '        <label>' + tr("vectorlab.couleur.canal_n") + '<input data-cmjn="n" type="number" min="0" max="100"/></label>\r\n'
      '      </div>\r\n'
      '      <div class="nu-tete">' + tr("vectorlab.couleur.palette_doc") + '\r\n'
      '        <button id="nuPalPlus"\r\n'
      '          title="' + tr("vectorlab.couleur.pal_plus_titre") + '" aria-label="' + tr("vectorlab.couleur.pal_plus") + '">',
      {"vectorlab.couleur.sv": ("Saturation / valeur", "Saturation / value"),
       "vectorlab.couleur.teinte": ("Teinte", "Hue"),
       "vectorlab.couleur.origine": ("Couleur d'origine", "Original color"),
       "vectorlab.couleur.nouvelle": ("Nouvelle couleur", "New color"),
       "vectorlab.couleur.hexa": ("Hexadécimal #RRGGBB", "Hexadecimal #RRGGBB"),
       "vectorlab.couleur.canal_v": ("V", "G", "contexte"),
       "vectorlab.couleur.cmjn_titre": ("CMJN indicatif — conversion naïve, sans profil ICC",
                                        "Approximate CMYK — naive conversion, no ICC profile"),
       "vectorlab.couleur.canal_j": ("J", "Y", "contexte"),
       "vectorlab.couleur.canal_n": ("N", "K", "contexte"),
       "vectorlab.couleur.palette_doc": ("Palette du document", "Document palette"),
       "vectorlab.couleur.pal_plus_titre": ("Ajouter la couleur courante à la palette du document (annulable, sauvée avec lui)",
                                            "Add the current color to the document palette (undoable, saved with it)"),
       "vectorlab.couleur.pal_plus": ("Ajouter la couleur courante à la palette du document",
                                      "Add the current color to the document palette")}),
    X(C, 197, '"dz-action-ajouter"', ICONE),
    S(C, 197,
      '</button>\r\n      </div>\r\n      <div id="nuPalDoc" class="nu-sw"\r\n'
      '           title="Clic : prendre — clic droit : retirer de la palette"></div>\r\n'
      '      <div class="nu-tete">Nuances</div>\r\n'
      '      <div id="nuPalDef" class="nu-sw"></div>\r\n'
      '      <div class="nu-tete">Récentes</div>\r\n'
      '      <div id="nuRecentes" class="nu-sw"></div>\r\n'
      '      <div class="nu-ligne nu-fin">\r\n'
      '        <button id="nuOk" class="primaire">Appliquer</button>\r\n'
      '        <button id="nuAnnul">Annuler</button>',
      '</button>\r\n      </div>\r\n      <div id="nuPalDoc" class="nu-sw"\r\n'
      '           title="' + tr("vectorlab.couleur.paldoc_titre") + '"></div>\r\n'
      '      <div class="nu-tete">' + tr("vectorlab.couleur.nuances") + '</div>\r\n'
      '      <div id="nuPalDef" class="nu-sw"></div>\r\n'
      '      <div class="nu-tete">' + tr("vectorlab.couleur.recentes") + '</div>\r\n'
      '      <div id="nuRecentes" class="nu-sw"></div>\r\n'
      '      <div class="nu-ligne nu-fin">\r\n'
      '        <button id="nuOk" class="primaire">' + tr("vectorlab.couleur.appliquer") + '</button>\r\n'
      '        <button id="nuAnnul">' + tr("vectorlab.couleur.annuler") + '</button>',
      {"vectorlab.couleur.paldoc_titre": ("Clic : prendre — clic droit : retirer de la palette",
                                          "Click: pick — right-click: remove from the palette"),
       "vectorlab.couleur.nuances": ("Nuances", "Shades"),
       "vectorlab.couleur.recentes": ("Récentes", "Recent"),
       "vectorlab.couleur.appliquer": ("Appliquer", "Apply"),
       "vectorlab.couleur.annuler": ("Annuler", "Cancel")}),
    L(C, 233, '" — clic droit : retirer"', "vectorlab.couleur.clic_droit_retirer", " — clic droit : retirer", " — right-click: remove"),

    # ───────────────────────── mod-effets.js ─────────────────────────
    S(EF, 9, '`couleur #RRGGBB attendue : ${v}`', 'T("vectorlab.effets.err_hex", { v })',
      {"vectorlab.effets.err_hex": ("couleur #RRGGBB attendue : {v}", "#RRGGBB color expected: {v}")}),
    S(EF, 10, '`${ou} : entre ${min} et ${max}`', 'T("vectorlab.effets.err_borne", { ou, min, max })',
      {"vectorlab.effets.err_borne": ("{ou} : entre {min} et {max}", "{ou}: between {min} and {max}")}),
    L(EF, 15, '"Ombre externe"', "vectorlab.effets.ombre", "Ombre externe", "Outer Shadow"),
    L(EF, 16, '"Ombre interne"', "vectorlab.effets.ombre_interne", "Ombre interne", "Inner Shadow"),
    L(EF, 17, '"Lueur externe"', "vectorlab.effets.lueur", "Lueur externe", "Outer Glow"),
    L(EF, 18, '"Biseau"', "vectorlab.effets.biseau", "Biseau", "Bevel"),
    L(EF, 19, '"Contour"', "vectorlab.effets.contour", "Contour", "Stroke"),
    L(EF, 20, '"Incrustation couleur"', "vectorlab.effets.incrustation", "Incrustation couleur", "Color Overlay"),
    S(EF, 31, '`effet inconnu : ${type}`', 'T("vectorlab.effets.inconnu", { type })',
      {"vectorlab.effets.inconnu": ("effet inconnu : {type}", "unknown effect: {type}")}),
    L(EF, 35, '"effets : liste attendue"', "vectorlab.effets.liste_attendue", "effets : liste attendue", "effects: list expected"),
    S(EF, 37, '`effet inconnu : ${e && e.type}`', 'T("vectorlab.effets.inconnu", { type: e && e.type })',
      {"vectorlab.effets.inconnu": ("effet inconnu : {type}", "unknown effect: {type}")}),
    X(EF, 42, '"largeur"', "nom du champ du document cité par la validation"),
    L(EF, 129, '"Hachures"', "vectorlab.effets.motif_hachures", "Hachures", "Hatching"),
    L(EF, 130, '"Points"', "vectorlab.effets.motif_points", "Points", "Dots"),
    L(EF, 131, '"Damier"', "vectorlab.effets.motif_damier", "Damier", "Checkerboard"),
    L(EF, 132, '"Grille"', "vectorlab.effets.motif_grille", "Grille", "Grid"),
    S(EF, 136, '`motif inconnu : ${type}`', 'T("vectorlab.effets.motif_inconnu", { type })',
      {"vectorlab.effets.motif_inconnu": ("motif inconnu : {type}", "unknown pattern: {type}")}),
    S(EF, 140, '`motif inconnu : ${m && m.type}`', 'T("vectorlab.effets.motif_inconnu", { type: m && m.type })',
      {"vectorlab.effets.motif_inconnu": ("motif inconnu : {type}", "unknown pattern: {type}")}),
    X(EF, 141, '"pas"', "nom du champ du motif cité par la validation"),
    L(EF, 179, '"conique : stops requis"', "vectorlab.effets.conique_stops", "conique : stops requis", "conical: stops required"),

    # ───────────────────────── mod-pipetteui.js ─────────────────────────
    X(PU, 28, '"image"', "sélecteur d'élément SVG", n=2),
    X(PU, 29, '"image-rendering:"', "propriété CSS"),
    X(PU, 47, '"calque"', "id de source comparé"),
    X(PU, 48, '"[data-calque]"', "sélecteur CSS"),
    X(PU, 48, '"data-calque"', "attribut data-*"),
    L(PU, 55, '"rendu illisible"', "vectorlab.pipette.rendu_illisible", "rendu illisible", "unreadable render"),
    X(PU, 55, '"data:image/svg+xml;charset=utf-8,"', "préfixe d'URL data:"),
    S(PU, 76, '`R : ${e.r}  G : ${e.g}  B : ${e.b}`', 'T("vectorlab.pipette.rgb", { r: e.r, g: e.g, b: e.b })',
      {"vectorlab.pipette.rgb": ("R : {r}  G : {g}  B : {b}", "R: {r}  G: {g}  B: {b}")}),
    X(PU, 76, '"transparent"', "texte identique dans les deux langues"),
    L(PU, 84, '"transparent — couleur inchangée"', "vectorlab.pipette.transparent", "transparent — couleur inchangée",
      "transparent — color unchanged"),
    S(PU, 87, '`${d.action} de la sélection : ${hex}`',
      'T(d.action === "fond" ? "vectorlab.pipette.fond_sel" : "vectorlab.pipette.contour_sel", { hex })',
      {"vectorlab.pipette.fond_sel": ("fond de la sélection : {hex}", "selection fill: {hex}"),
       "vectorlab.pipette.contour_sel": ("contour de la sélection : {hex}", "selection stroke: {hex}")}),
    S(PU, 90, '`couleur courante : ${hex} — les nouveaux objets la prendront`', 'T("vectorlab.pipette.courante", { hex })',
      {"vectorlab.pipette.courante": ("couleur courante : {hex} — les nouveaux objets la prendront",
                                      "current color: {hex} — new objects will use it")}),
    L(PU, 101, '"pipette : "', "vectorlab.pipette.erreur", "pipette : ", "eyedropper: "),
    L(PU, 116, '''"Cliquer ou Glisser pour prélever une couleur — Ctrl : le style de l'objet · Maj : loupe · Alt : appliquer à la sélection"''',
      "vectorlab.pipette.hint",
      "Cliquer ou Glisser pour prélever une couleur — Ctrl : le style de l'objet · Maj : loupe · Alt : appliquer à la sélection",
      "Click or Drag to pick a color — Ctrl: the object's style · Shift: magnifier · Alt: apply to selection"),

    # ───────────────────────── mod-pipette.js ─────────────────────────
    X(P, 12, '"calque"', "id de source stocké et comparé"),
    L(P, 12, '"Calque courant"', "vectorlab.pipette.source_calque", "Calque courant", "Current layer"),
    L(P, 43, '"Appliquer à la sélection"', "vectorlab.pipette.appliquer", "Appliquer à la sélection", "Apply to selection"),
    L(P, 43, '"La couleur prélevée va au fond de la sélection (clic droit : au contour) — Alt inverse"', "vectorlab.pipette.appliquer_titre",
      "La couleur prélevée va au fond de la sélection (clic droit : au contour) — Alt inverse",
      "The picked color goes to the selection fill (right-click: to the stroke) — Alt inverts"),
    L(P, 44, '"Agrandissement"', "vectorlab.pipette.loupe", "Agrandissement", "Magnifier", contexte=True),
    L(P, 44, '"La loupe pendant le prélèvement — Maj inverse"', "vectorlab.pipette.loupe_titre",
      "La loupe pendant le prélèvement — Maj inverse", "The magnifier while picking — Shift inverts"),
    L(P, 46, '"Rayon"', "vectorlab.pipette.rayon", "Rayon", "Radius"),

    # ───────────────────────── mod-familles.js ─────────────────────────
    S(F, 44, '`Outil ${x.nom}`', 'T("vectorlab.familles.outil", { nom: x.nom })',
      {"vectorlab.familles.outil": ("Outil {nom}", "{nom} Tool")}),
    X(F, 9, '"forme"', "id d'outil"),
    X(F, 11, '"texte"', "id de famille / d'outil", n=2),
    X(F, 12, '"image"', "id de famille / d'outil", n=2),
    X(F, 12, '"Image"', "texte identique dans les deux langues"),
    X(F, 12, '"Image (menu)"', "texte identique dans les deux langues"),
]

# les noms des familles et de leurs membres : (ligne, littéral, rôle, en, n)
_FAM = [
    (6, "Déplacer", "deplacer", "Move", 2),
    (7, "Nœuds", "noeuds", "Nodes", 1), (7, "Nœud", "noeud", "Node", 1), (7, "Coin", "coin", "Corner", 1),
    (8, "Plume", "plume", "Pen", 2), (8, "Crayon", "crayon", "Pencil", 1), (8, "Pinceau vectoriel", "pinceauv", "Vector Brush", 1),
    (9, "Formes", "formes", "Shapes", 1), (9, "Ligne", "ligne", "Line", 1), (9, "Forme paramétrique", "forme", "Parametric shape", 1),
    (10, "Constructeur", "constructeur_famille", "Builder", 1), (10, "Constructeur de formes", "constructeur", "Shape Builder", 1),
    (10, "Couteau", "couteau", "Knife", 1), (10, "Gomme vectorielle", "gomme", "Vector Eraser", 1),
    (11, "Texte", "texte", "Text", 2), (11, "Cadre de texte", "cadre", "Frame Text", 1),
    (12, "Recadrer", "recadrer", "Crop", 1),
    (13, "Dégradé", "degrade", "Gradient", 2), (13, "Transparence", "transparence", "Transparency", 1),
    (14, "Apparence", "apparence", "Appearance", 1), (14, "Apparence (menu)", "apparence_menu", "Appearance (menu)", 1),
    (15, "Symboles", "symboles", "Symbols", 1), (15, "Symboles (menu)", "symboles_menu", "Symbols (menu)", 1),
    (16, "Mesure", "mesure", "Measure", 2), (16, "Pipette", "pipette", "Eyedropper", 1),
    (17, "Tuiles", "tuiles", "Tiles", 1), (17, "Pinceau de tuiles", "tuiles_pinceau", "Tile Brush", 1),
    (18, "Plan de travail", "planche", "Artboard", 2),
    (19, "IA", "ia", "AI", 1), (19, "Illustration IA", "ia_illustration", "AI Illustration", 1),
    (20, "Sélection de pixels", "pxselection", "Pixel Selection", 1), (20, "Sélection rectangle", "px_selrect", "Rectangular Marquee", 1),
    (20, "Baguette magique", "px_baguette", "Magic Wand", 1),
    (21, "Pinceau", "px_pinceau", "Brush", 2), (21, "Gomme", "px_gomme", "Eraser", 1), (21, "Tampon de clonage", "px_cloner", "Clone Stamp", 1),
    (22, "Retouche", "pxretouche", "Retouch", 1), (22, "Flou", "px_flou", "Blur", 1),
    (22, "Éclaircir (densité −)", "px_eclaircir", "Dodge (density −)", 1), (22, "Assombrir (densité +)", "px_assombrir", "Burn (density +)", 1),
    (23, "Seau", "pxseau", "Bucket", 1), (23, "Pot de peinture", "px_seau", "Paint Bucket", 1),
    (24, "Crayon pixel", "px_crayon", "Pixel Pencil", 1), (24, "Ligne pixel", "px_ligne", "Pixel Line", 1),
    (24, "Rectangle pixel", "px_rectpx", "Pixel Rectangle", 1),
    (25, "Vue", "vue", "View", 1), (25, "Main", "main", "Hand", 1), (25, "Loupe", "loupe", "Zoom", 1),
    (26, "Tranche", "tranche", "Slice", 1), (26, "Tranche d'export", "tranche_export", "Export Slice", 1),
]
for ligne, fr, role, en, n in _FAM:
    ENTREES.append(L(F, ligne, f'"{fr}"', "vectorlab.familles." + role, fr, en, n=n))
