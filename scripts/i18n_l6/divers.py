"""t146 — divers : les petits modules du Vectorlab — la pile de droite (mod-pile : notes vides, Échantillons,
Navigateur, Histogramme), les formes paramétriques (noms du menu Forme + messages de paramètres), les modes de la
Plume et ses messages, l'outil Nœuds, le brouillon automatique (témoin, dialogue de restauration), le panneau Export
(mod-persona), les tranches d'export (modes, formats), les profils du pinceau vectoriel, l'aide didactique (« Aide : »),
et les messages d'erreur MONTRÉS (VL.executer et les panneaux attrapent les Error et les affichent par toast) des
modules purs : solide / relief / extrusion (impression 3D), pixel-art, pixel, nœuds, GPX, objets vivants, grille.

GARDÉ (X) : ids et valeurs du document (« forme », « texte », « aucun », « document », « calques »), le vocabulaire
COMPARÉ aux libellés de rangées de mod-style (VERS_TRAIT : « Pointillés », « Décaler » — voir le bilan : si le groupe
du panneau Apparence traduit ces libellés, la redistribution Transformer/Trait de mod-pile ne les reconnaît plus en
anglais), les erreurs d'invariant interne jamais provoquées par l'écran (forme / poignée inconnue, tramage ou mode de
pipette hors liste, spécification de plateau absente), les validations de fiche didactique (servent à FILTRER
aide/index.json, jamais affichées), les en-têtes de fichiers exportés (STL/GLB). Les autres messages techniques de
schéma (grille: type/orientation/origine/echelle, plateau: mode, mode de tranche — ce dernier sous un `const T` local
de tranches_de, en zone morte) restent tels quels : sans allure française, jamais provoqués par l'écran.
"""
from outils import L, S, X

P = "js/mod-pile.js"
F = "js/mod-formes.js"
SO = "js/mod-solide.js"
B = "js/mod-brouillon.js"
TR = "js/mod-tranches.js"
PA = "js/mod-pixelart.js"
PE = "js/mod-persona.js"
NO = "js/mod-noeuds.js"
PL = "js/mod-plumeui.js"
RE = "js/mod-relief.js"
PX = "js/mod-pixel.js"
GE = "js/mod-geo.js"
VI = "js/mod-vivants.js"
NU = "js/mod-noeudui.js"
GR = "js/mod-grille.js"
DI = "js/mod-didact.js"
SU = "js/mod-selectionui.js"
EX = "js/mod-extrude.js"
CR = "js/mod-crayon.js"
PV = "js/mod-pinceauvec.js"

ENTREES = [
    # ── mod-pile : la pile de droite ──
    X(P, 16, '"Pointillés"', "vocabulaire COMPARÉ au libellé de rangée de mod-style (redistribution vers Trait)"),
    X(P, 16, '"Décaler"', "vocabulaire COMPARÉ au libellé de rangée de mod-style (redistribution vers Trait)"),
    S(P, 32,
      '`<div class="onglets"></div><button class="groupe-repli" title="Replier / déplier ce groupe" aria-label="Replier / déplier ce groupe">',
      '`<div class="onglets"></div><button class="groupe-repli" title="${T("vectorlab.pile.replier")}" aria-label="${T("vectorlab.pile.replier")}">',
      {"vectorlab.pile.replier": ("Replier / déplier ce groupe", "Collapse / expand this group")}),
    S(P, 87,
      '`<p class="px-note">Sélectionner un objet : position, taille, inclinaison et duplication en puissance.</p>`',
      '`<p class="px-note">${T("vectorlab.pile.transformer_vide")}</p>`',
      {"vectorlab.pile.transformer_vide": (
          "Sélectionner un objet : position, taille, inclinaison et duplication en puissance.",
          "Select an object: position, size, shear and power duplicate.")}),
    S(P, 88,
      '`<p class="px-note">Le contour de la sélection ou des prochains objets.</p>`',
      '`<p class="px-note">${T("vectorlab.pile.trait_vide")}</p>`',
      {"vectorlab.pile.trait_vide": ("Le contour de la sélection ou des prochains objets.",
                                     "The stroke of the selection or of the next objects.")}),
    S(P, 97,
      ' — clic : fond de la sélection · Maj+clic : contour"',
      ' — ${T("vectorlab.pile.ech_case")}"',
      {"vectorlab.pile.ech_case": ("clic : fond de la sélection · Maj+clic : contour",
                                   "click: selection fill · Shift+click: stroke")}),
    S(P, 97,
      '</div><p class="px-note">La palette du document (bouton Ajouter du nuancier pour y ajouter).</p>`',
      '</div><p class="px-note">${T("vectorlab.pile.ech_note")}</p>`',
      {"vectorlab.pile.ech_note": ("La palette du document (bouton Ajouter du nuancier pour y ajouter).",
                                   "The document palette (use the color picker's Add button to add to it).")}),
    S(P, 98,
      '`<p class="px-note">Aucun échantillon — le nuancier (pastille Fond) ajoute une couleur à la palette du document.</p>`',
      '`<p class="px-note">${T("vectorlab.pile.ech_vide")}</p>`',
      {"vectorlab.pile.ech_vide": (
          "Aucun échantillon — le nuancier (pastille Fond) ajoute une couleur à la palette du document.",
          "No swatches — the color picker (Fill chip) adds a color to the document palette.")}),
    S(P, 111,
      '`<p class="px-note">Aucun document.</p>`',
      '`<p class="px-note">${T("vectorlab.pile.aucun_doc")}</p>`',
      {"vectorlab.pile.aucun_doc": ("Aucun document.", "No document.")}),
    S(P, 113,
      'px"><div class="nav-page"></div><div class="nav-cadre"></div></div>\r\n        <div class="ap-ligne nav-zoom"><button id="navMoins" title="Zoom arrière" aria-label="Zoom arrière">',
      'px"><div class="nav-page"></div><div class="nav-cadre"></div></div>\r\n        <div class="ap-ligne nav-zoom"><button id="navMoins" title="${T("vectorlab.pile.zoom_arriere")}" aria-label="${T("vectorlab.pile.zoom_arriere")}">',
      {"vectorlab.pile.zoom_arriere": ("Zoom arrière", "Zoom out")}),
    S(P, 114,
      '<button id="navPlus" title="Zoom avant" aria-label="Zoom avant">',
      '<button id="navPlus" title="${T("vectorlab.pile.zoom_avant")}" aria-label="${T("vectorlab.pile.zoom_avant")}">',
      {"vectorlab.pile.zoom_avant": ("Zoom avant", "Zoom in")}),
    S(P, 149,
      "`<p class=\"px-note\">Éditer les pixels d'une image (persona Pixel, « Éditer les pixels ») pour lire son histogramme.</p>`",
      '`<p class="px-note">${T("vectorlab.pile.hist_vide")}</p>`',
      {"vectorlab.pile.hist_vide": (
          "Éditer les pixels d'une image (persona Pixel, « Éditer les pixels ») pour lire son histogramme.",
          "Edit an image's pixels (Pixel persona, “Edit pixels”) to read its histogram.")}),
    S(P, 151,
      'aria-label="Histogramme"',
      'aria-label="${T("vectorlab.pile.histogramme")}"',
      {"vectorlab.pile.histogramme": ("Histogramme", "Histogram")}),
    S(P, 152,
      '<div class="hist-stats"><span>Moyenne : ',
      '<div class="hist-stats"><span>${T("vectorlab.pile.hist_moyenne")} ',
      {"vectorlab.pile.hist_moyenne": ("Moyenne :", "Mean:")}),
    S(P, 152,
      '</span><span>Écart-type : ',
      '</span><span>${T("vectorlab.pile.hist_ecart")} ',
      {"vectorlab.pile.hist_ecart": ("Écart-type :", "Std dev:")}),
    S(P, 152,
      '</span><span>Médiane : ',
      '</span><span>${T("vectorlab.pile.hist_mediane")} ',
      {"vectorlab.pile.hist_mediane": ("Médiane :", "Median:")}),
    S(P, 152,
      '</span><span>Pixels : ',
      '</span><span>${T("vectorlab.pile.hist_pixels")} ',
      {"vectorlab.pile.hist_pixels": ("Pixels :", "Pixels:")}),

    # ── mod-formes : noms du menu Forme + paramètres ──
    L(F, 8, '"Polygone"', "vectorlab.formes.polygone", "Polygone", "Polygon"),
    L(F, 9, '"Hexagone"', "vectorlab.formes.hexagone", "Hexagone", "Hexagon"),
    L(F, 10, '"Étoile"', "vectorlab.formes.etoile", "Étoile", "Star"),
    L(F, 11, '"Engrenage"', "vectorlab.formes.engrenage", "Engrenage", "Cog"),
    L(F, 12, '"Flèche"', "vectorlab.formes.fleche", "Flèche", "Arrow"),
    L(F, 14, '"Spirale"', "vectorlab.formes.spirale", "Spirale", "Spiral"),
    X(F, 22, '"forme"', "type d'objet du document"),
    X(F, 32, '`forme inconnue : ${nom}`', "invariant interne (id de forme hors liste), jamais provoqué par l'écran"),
    L(F, 37, '"forme : params requis"', "vectorlab.formes.err_params", "forme : params requis", "shape: parameters required"),
    L(F, 40, '"polygone : n entier ≥ 3"', "vectorlab.formes.err_polygone", "polygone : n entier ≥ 3", "polygon: n must be an integer ≥ 3"),
    L(F, 42, '"étoile : n entier ≥ 3"', "vectorlab.formes.err_etoile_n", "étoile : n entier ≥ 3", "star: n must be an integer ≥ 3"),
    L(F, 43, '"étoile : ratio dans ]0, 1["', "vectorlab.formes.err_etoile_ratio", "étoile : ratio dans ]0, 1[", "star: ratio within ]0, 1["),
    L(F, 46, '"engrenage : dents entier ≥ 3"', "vectorlab.formes.err_dents", "engrenage : dents entier ≥ 3", "cog: teeth must be an integer ≥ 3"),
    L(F, 47, '"engrenage : profondeur > 0"', "vectorlab.formes.err_profondeur", "engrenage : profondeur > 0", "cog: depth > 0"),
    L(F, 50, '"flèche : longueur, largeur, tête > 0"', "vectorlab.formes.err_fleche", "flèche : longueur, largeur, tête > 0", "arrow: length, width, head > 0"),
    L(F, 52, '"donut : ratio dans ]0, 1["', "vectorlab.formes.err_donut", "donut : ratio dans ]0, 1[", "donut: ratio within ]0, 1["),
    L(F, 54, '"spirale : tours > 0"', "vectorlab.formes.err_tours", "spirale : tours > 0", "spiral: turns > 0"),
    X(F, 57, '`forme inconnue : ${nom}`', "invariant interne (id de forme hors liste), jamais provoqué par l'écran"),
    L(F, 72, '"forme : rayon > 0 requis"', "vectorlab.formes.err_rayon", "forme : rayon > 0 requis", "shape: radius > 0 required"),
    X(F, 118, '`forme inconnue : ${o.forme}`', "invariant interne (id de forme hors liste), jamais provoqué par l'écran"),
    X(F, 141, '`poignée inconnue : ${cle}`', "invariant interne (clé de poignée hors liste)"),

    # ── mod-solide : impression 3D ──
    X(SO, 33, '"texte"', "type d'objet du document"),
    L(SO, 73, '"retrait : distance ≥ 0 requise"', "vectorlab.solide.err_retrait", "retrait : distance ≥ 0 requise", "inset: distance ≥ 0 required"),
    L(SO, 107, '"dépouille : hauteur > 0 requise"', "vectorlab.solide.err_depouille_h", "dépouille : hauteur > 0 requise", "draft: height > 0 required"),
    S(SO, 108,
      '`dépouille : angle entre −${DEPOUILLE_MAX}° et ${DEPOUILLE_MAX}°`',
      'T("vectorlab.solide.err_depouille_angle", { max: DEPOUILLE_MAX })',
      {"vectorlab.solide.err_depouille_angle": ("dépouille : angle entre −{max}° et {max}°", "draft: angle between −{max}° and {max}°")}),
    L(SO, 128, '"biseau : hauteur > 0 requise"', "vectorlab.solide.err_biseau_h", "biseau : hauteur > 0 requise", "bevel: height > 0 required"),
    L(SO, 129, '"biseau : retrait ≥ 0 requis"', "vectorlab.solide.err_biseau_retrait", "biseau : retrait ≥ 0 requis", "bevel: inset ≥ 0 required"),
    L(SO, 130, '"biseau : le retrait doit rester sous la hauteur"', "vectorlab.solide.err_biseau_sous", "biseau : le retrait doit rester sous la hauteur", "bevel: the inset must stay below the height"),
    L(SO, 146, '"évidement : hauteur > 0 requise"', "vectorlab.solide.err_evide_h", "évidement : hauteur > 0 requise", "hollow: height > 0 required"),
    S(SO, 148,
      '`évidement : mur ≥ ${MUR_MIN_MM} mm (deux passes de buse)`',
      'T("vectorlab.solide.err_evide_mur", { mm: MUR_MIN_MM })',
      {"vectorlab.solide.err_evide_mur": ("évidement : mur ≥ {mm} mm (deux passes de buse)", "hollow: wall ≥ {mm} mm (two nozzle passes)")}),
    L(SO, 150, '"évidement : plancher ≥ 0 et sous la hauteur"', "vectorlab.solide.err_evide_plancher", "évidement : plancher ≥ 0 et sous la hauteur", "hollow: floor ≥ 0 and below the height"),
    L(SO, 153, '"évidement : mur trop épais pour cette forme (elle se vide)"', "vectorlab.solide.err_evide_epais", "évidement : mur trop épais pour cette forme (elle se vide)", "hollow: wall too thick for this shape (it empties out)"),
    L(SO, 187, '"GLB : aucun triangle"', "vectorlab.solide.err_glb", "GLB : aucun triangle", "GLB: no triangles"),
    X(SO, 222, '"Deepotus Vectorlab"', "nom propre écrit dans le fichier GLB exporté"),
    L(SO, 326, '"pixel-art : cellule en mm > 0"', "vectorlab.solide.err_cellule", "pixel-art : cellule en mm > 0", "pixel art: cell size in mm > 0"),

    # ── mod-brouillon : la sauvegarde automatique ──
    S(B, 23,
      '`brouillon du ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`',
      'T("vectorlab.brouillon.libelle", { heure: `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}` })',
      {"vectorlab.brouillon.libelle": ("brouillon du {heure}", "draft from {heure}")}),
    S(B, 37,
      '"État d\'enregistrement · " + brouillon_libelle(b) + " (non sauvé au serveur)"',
      'T("vectorlab.brouillon.temoin_brouillon", { libelle: brouillon_libelle(b) })',
      {"vectorlab.brouillon.temoin_brouillon": ("État d'enregistrement · {libelle} (non sauvé au serveur)",
                                                "Save status · {libelle} (not saved to the server)")}),
    S(B, 50,
      "`Un ${brouillon_libelle(b)} de ce document n'a pas été sauvé.\\n`\r\n"
      "                + `Repartir du serveur = version ${etat.meta.version} ; le brouillon est alors oublié.`",
      'T("vectorlab.brouillon.confirmer", { libelle: brouillon_libelle(b), version: etat.meta.version })',
      {"vectorlab.brouillon.confirmer": (
          "Un {libelle} de ce document n'a pas été sauvé.\nRepartir du serveur = version {version} ; le brouillon est alors oublié.",
          "A {libelle} of this document was not saved.\nStarting over from the server = version {version}; the draft is then discarded.")}),
    L(B, 52, '"Brouillon non sauvé"', "vectorlab.brouillon.titre", "Brouillon non sauvé", "Unsaved draft"),
    L(B, 52, '"Restaurer"', "vectorlab.brouillon.restaurer", "Restaurer", "Restore"),
    L(B, 52, '"Repartir du serveur"', "vectorlab.brouillon.repartir", "Repartir du serveur", "Start over from the server"),
    S(B, 54,
      '"brouillon illisible : " + e.message',
      'T("vectorlab.brouillon.illisible", { err: e.message })',
      {"vectorlab.brouillon.illisible": ("brouillon illisible : {err}", "unreadable draft: {err}")}),
    L(B, 58, '"brouillon restauré — Sauver pour l\'écrire au serveur"', "vectorlab.brouillon.restaure",
      "brouillon restauré — Sauver pour l'écrire au serveur", "draft restored — Save to write it to the server"),
    L(B, 65, '"État d\'enregistrement"', "vectorlab.brouillon.temoin", "État d'enregistrement", "Save status"),

    # ── mod-tranches : modes et formats d'export ──
    X(TR, 9, '"document"', "id de mode de tranche"),
    L(TR, 9, '"Document entier"', "vectorlab.tranches.document", "Document entier", "Whole document"),
    L(TR, 10, '"Chaque planche"', "vectorlab.tranches.planches", "Chaque planche", "Each artboard"),
    X(TR, 11, '"calques"', "id de mode de tranche"),
    L(TR, 11, '"Chaque calque visible"', "vectorlab.tranches.calques", "Chaque calque visible", "Each visible layer"),
    L(TR, 12, '"Chaque objet sélectionné"', "vectorlab.tranches.objets", "Chaque objet sélectionné", "Each selected object"),
    L(TR, 13, '"Tranches dessinées"', "vectorlab.tranches.dessinees", "Tranches dessinées", "Drawn slices"),
    L(TR, 20, '"PDF (impression)"', "vectorlab.tranches.pdf", "PDF (impression)", "PDF (print)"),
    L(TR, 21, '"DXF (découpe)"', "vectorlab.tranches.dxf", "DXF (découpe)", "DXF (cutting)"),
    X(TR, 34, '"document"', "id de mode de tranche comparé (switch)"),
    X(TR, 36, '"calques"', "id de mode de tranche comparé (switch)"),

    # ── mod-pixelart ──
    L(PA, 95, '"quantifier : palette vide"', "vectorlab.pixelart.err_quantifier", "quantifier : palette vide", "quantize: empty palette"),
    L(PA, 113, '"tramage : palette vide"', "vectorlab.pixelart.err_tramage", "tramage : palette vide", "dithering: empty palette"),
    L(PA, 125, '"tramage : palette vide"', "vectorlab.pixelart.err_tramage", "tramage : palette vide", "dithering: empty palette"),
    X(PA, 139, '"aucun"', "id de tramage (DITHERS), valeur comparée"),
    X(PA, 140, '"aucun"', "id de tramage par défaut, valeur comparée"),
    L(PA, 141, '"rastériser : largeur cible ≥ 1"', "vectorlab.pixelart.err_rasteriser", "rastériser : largeur cible ≥ 1", "rasterize: target width ≥ 1"),
    X(PA, 142, '"rastériser : tramage aucun, ordonne ou floyd"', "invariant interne : nomme les ids de tramage du code"),
    L(PA, 149, '"pixeliser : largeur cible ≥ 1 requise"', "vectorlab.pixelart.err_pixeliser", "pixeliser : largeur cible ≥ 1 requise", "pixelate: target width ≥ 1 required"),
    L(PA, 175, '"feuille : aucune tuile"', "vectorlab.pixelart.err_feuille_vide", "feuille : aucune tuile", "sheet: no tiles"),
    L(PA, 177, '"feuille : toutes les tuiles doivent avoir la même taille"', "vectorlab.pixelart.err_feuille_taille",
      "feuille : toutes les tuiles doivent avoir la même taille", "sheet: all tiles must have the same size"),
    L(PA, 188, '"bande : aucun cadre"', "vectorlab.pixelart.err_bande", "bande : aucun cadre", "strip: no frames"),
    X(PA, 329, '"pipette : mode exact, moyenne ou dominante"', "invariant interne : nomme les ids de mode de pipette du code"),
    L(PA, 397, '"agrandir : facteur ≥ 1"', "vectorlab.pixelart.err_agrandir", "agrandir : facteur ≥ 1", "upscale: factor ≥ 1"),

    # ── mod-pixel ──
    L(PX, 10, '"tampon : taille ≥ 1 requise"', "vectorlab.pixelart.err_tampon", "tampon : taille ≥ 1 requise", "buffer: size ≥ 1 required"),
    S(PX, 16,
      '`couleur hex attendue : ${hex}`',
      'T("vectorlab.pixelart.err_hex", { hex })',
      {"vectorlab.pixelart.err_hex": ("couleur hex attendue : {hex}", "hex color expected: {hex}")}),
    L(PX, 92, '"point hors du tampon"', "vectorlab.pixelart.err_hors_tampon", "point hors du tampon", "point outside the buffer"),
    L(PX, 195, '"courbes : deux points au moins"', "vectorlab.pixelart.err_courbes", "courbes : deux points au moins", "curves: at least two points"),
    L(PX, 290, '"extraire : aucune sélection"', "vectorlab.pixelart.err_extraire", "extraire : aucune sélection", "extract: no selection"),

    # ── mod-persona : personas + panneau Export ──
    L(PE, 10, '"Vecteur"', "vectorlab.persona.vecteur", "Vecteur", "Vector"),
    L(PE, 10, '"Dessin vectoriel : formes, chemins, nœuds, booléens, texte"', "vectorlab.persona.vecteur_titre",
      "Dessin vectoriel : formes, chemins, nœuds, booléens, texte", "Vector drawing: shapes, paths, nodes, Booleans, text"),
    L(PE, 11, '"Retouche des calques image au pixel et mode pixel-art vers le Tilelab"', "vectorlab.persona.pixel_titre",
      "Retouche des calques image au pixel et mode pixel-art vers le Tilelab",
      "Pixel-level retouching of image layers, and pixel-art mode for the Tilelab"),
    X(PE, 19, '"image"', "id d'outil comparé"),
    L(PE, 69, '"SVG (serveur)"', "vectorlab.persona.exp_svg", "SVG (serveur)", "SVG (server)"),
    L(PE, 69, '"Compile ici, stocké au serveur, servi sur export.svg"', "vectorlab.persona.exp_svg_titre",
      "Compile ici, stocké au serveur, servi sur export.svg", "Compiled here, stored on the server, served as export.svg"),
    L(PE, 70, '"PNG taille du document → Library"', "vectorlab.persona.exp_png1_titre",
      "PNG taille du document → Library", "PNG at document size → Library"),
    L(PE, 71, '"PNG double → Library"', "vectorlab.persona.exp_png2_titre", "PNG double → Library", "PNG at double size → Library"),
    L(PE, 72, '"PNG quadruple → Library"', "vectorlab.persona.exp_png4_titre", "PNG quadruple → Library", "PNG at quadruple size → Library"),
    L(PE, 73, '"Exporte en 2× vers les images d\'inspiration d\'une entité de la bible"', "vectorlab.persona.exp_bible_titre",
      "Exporte en 2× vers les images d'inspiration d'une entité de la bible",
      "Exports at 2× to the inspiration images of a bible entity"),
    L(PE, 74, '"Impression 3D…"', "vectorlab.persona.exp_print3d", "Impression 3D…", "3D Print…"),
    L(PE, 74, '"Calques en relief, plateau de tuiles, logo — STL + 3MF"', "vectorlab.persona.exp_print3d_titre",
      "Calques en relief, plateau de tuiles, logo — STL + 3MF", "Relief layers, tile board, logo — STL + 3MF"),
    S(PE, 76,
      '`<div class="ap-ligne"><label title="Compile sans le fond du document">',
      '`<div class="ap-ligne"><label title="${T("vectorlab.persona.transparent_titre")}">',
      {"vectorlab.persona.transparent_titre": ("Compile sans le fond du document", "Compiles without the document background")}),
    S(PE, 76,
      '/> fond transparent</label></div>`',
      '/> ${T("vectorlab.persona.transparent")}</label></div>`',
      {"vectorlab.persona.transparent": ("fond transparent", "transparent background")}),
    S(PE, 78,
      "`<p class=\"px-note\">Les planches s'exportent depuis leur panneau (persona Vecteur).</p>`",
      '`<p class="px-note">${T("vectorlab.persona.planches_note")}</p>`',
      {"vectorlab.persona.planches_note": ("Les planches s'exportent depuis leur panneau (persona Vecteur).",
                                           "Artboards are exported from their own panel (Vector persona).")}),
    L(PE, 81, '"export indisponible"', "vectorlab.persona.export_indispo", "export indisponible", "export unavailable"),

    # ── mod-noeuds / mod-noeudui : l'outil Nœuds ──
    S(NO, 14,
      '`objet ${id}: pas un chemin`',
      'T("vectorlab.noeuds.err_pas_chemin", { id })',
      {"vectorlab.noeuds.err_pas_chemin": ("objet {id}: pas un chemin", "object {id}: not a path")}),
    S(NO, 18,
      '`chemin introuvable (ou calque verrouillé): ${id}`',
      'T("vectorlab.noeuds.err_introuvable", { id })',
      {"vectorlab.noeuds.err_introuvable": ("chemin introuvable (ou calque verrouillé): {id}", "path not found (or layer locked): {id}")}),
    L(NO, 55, '"aligner : deux ancres au moins"', "vectorlab.noeuds.err_aligner", "aligner : deux ancres au moins", "align: at least two anchors"),
    L(NO, 68, '"transformer : boîte de départ vide"', "vectorlab.noeuds.err_transformer", "transformer : boîte de départ vide", "transform: empty starting box"),
    L(NO, 87, '"diviser : choisir une ancre après la première"', "vectorlab.noeuds.err_diviser", "diviser : choisir une ancre après la première", "split: pick an anchor after the first one"),
    L(NO, 103, '"diviser : segment non divisible"', "vectorlab.noeuds.err_diviser_seg", "diviser : segment non divisible", "split: segment cannot be split"),
    L(NO, 126, '"joindre : les deux chemins doivent être ouverts"', "vectorlab.noeuds.err_joindre_ouverts", "joindre : les deux chemins doivent être ouverts", "join: both paths must be open"),
    L(NO, 127, '"joindre : chemin B sans départ"', "vectorlab.noeuds.err_joindre_depart", "joindre : chemin B sans départ", "join: path B has no start point"),
    L(NO, 137, '"coins : rayon > 0 requis"', "vectorlab.noeuds.err_coins", "coins : rayon > 0 requis", "corners: radius > 0 required"),
    X(NO, 150, '"forme"', "type d'objet du document comparé"),
    L(NU, 18,
      '"cliquer un nœud pour le sélectionner, Maj ajoute · glisser un nœud, une poignée (Alt casse la tangente, Maj contraint) ou un segment · double-clic sur un segment insère un nœud, sur un nœud le convertit · Suppr retire en lissant"',
      "vectorlab.noeuds.hint",
      "cliquer un nœud pour le sélectionner, Maj ajoute · glisser un nœud, une poignée (Alt casse la tangente, Maj contraint) ou un segment · double-clic sur un segment insère un nœud, sur un nœud le convertit · Suppr retire en lissant",
      "click a node to select it, Shift adds · drag a node, a handle (Alt breaks the tangent, Shift constrains) or a segment · double-click a segment to insert a node, a node to convert it · Del removes it while smoothing"),
    L(NU, 105, '"chemin introuvable"', "vectorlab.noeuds.err_chemin", "chemin introuvable", "path not found"),
    L(NU, 152, '"aligner : sélectionner au moins deux nœuds (lasso ou Maj+clic)"', "vectorlab.noeuds.err_aligner_sel",
      "aligner : sélectionner au moins deux nœuds (lasso ou Maj+clic)", "align: select at least two nodes (lasso or Shift+click)"),
    L(NU, 154, '"intelligent : choisir un nœud"', "vectorlab.noeuds.err_intelligent", "intelligent : choisir un nœud", "smart: pick a node"),

    # ── mod-plumeui : la Plume ──
    L(PL, 14, '"Plume"', "vectorlab.plume.mode_plume", "Plume", "Pen"),
    L(PL, 14, '"Intelligent"', "vectorlab.plume.mode_intelligent", "Intelligent", "Smart"),
    L(PL, 14, '"Polygone"', "vectorlab.formes.polygone", "Polygone", "Polygon"),
    L(PL, 14, '"Ligne"', "vectorlab.plume.mode_ligne", "Ligne", "Line"),
    L(PL, 15,
      "\"cliquer ou glisser pour prolonger une courbe depuis sa fin · clic droit pour créer une ligne droite · glisser + Maj pour contraindre la tangente d'un nœud · Alt pour ignorer le magnétisme · Retour arrière retire le dernier nœud · Entrée ou Échap finit\"",
      "vectorlab.plume.hint",
      "cliquer ou glisser pour prolonger une courbe depuis sa fin · clic droit pour créer une ligne droite · glisser + Maj pour contraindre la tangente d'un nœud · Alt pour ignorer le magnétisme · Retour arrière retire le dernier nœud · Entrée ou Échap finit",
      "click or drag to extend a curve from its end · right-click to create a straight line · drag + Shift to constrain a node's tangent · Alt to ignore snapping · Backspace removes the last node · Enter or Esc finishes"),
    L(PL, 62, '"chemin prolongé introuvable"', "vectorlab.plume.err_prolonge", "chemin prolongé introuvable", "extended path not found"),
    L(PL, 146, '"plume : aucun chemin"', "vectorlab.plume.aucun_chemin", "plume : aucun chemin", "pen: no path"),
    L(PL, 153, '"plume : aucun chemin"', "vectorlab.plume.aucun_chemin", "plume : aucun chemin", "pen: no path"),
    L(PL, 153, '"fractionner : choisir une ancre intérieure (outil Nœuds)"', "vectorlab.plume.fractionner",
      "fractionner : choisir une ancre intérieure (outil Nœuds)", "break: pick an inner anchor (Node tool)"),
    L(PL, 157, '"relier : sélectionner deux chemins ouverts"', "vectorlab.plume.relier",
      "relier : sélectionner deux chemins ouverts", "join: select two open paths"),

    # ── mod-relief : impression 3D (relief, ruban, tenons) ──
    L(RE, 25, '"relief : grille d\'au moins 2 × 2 requise"', "vectorlab.relief.err_grille", "relief : grille d'au moins 2 × 2 requise", "relief: grid of at least 2 × 2 required"),
    L(RE, 26, '"relief : socle > 0 mm requis"', "vectorlab.relief.err_socle", "relief : socle > 0 mm requis", "relief: base > 0 mm required"),
    L(RE, 27, '"relief : largeur et mm/m > 0 requis"', "vectorlab.relief.err_largeur", "relief : largeur et mm/m > 0 requis", "relief: width and mm/m > 0 required"),
    L(RE, 34, '"relief : 0 < profondeur de logement < socle"', "vectorlab.relief.err_logement", "relief : 0 < profondeur de logement < socle", "relief: 0 < socket depth < base"),
    L(RE, 97, '"ruban : épaisseur > 0 mm requise"', "vectorlab.relief.err_ruban_ep", "ruban : épaisseur > 0 mm requise", "ribbon: thickness > 0 mm required"),
    L(RE, 103, '"ruban : deux points distincts au moins"', "vectorlab.relief.err_ruban_points", "ruban : deux points distincts au moins", "ribbon: at least two distinct points"),
    L(RE, 104, '"ruban : hauteur > 0 mm à chaque point"', "vectorlab.relief.err_ruban_h", "ruban : hauteur > 0 mm à chaque point", "ribbon: height > 0 mm at every point"),
    L(RE, 157, '"tenons : socle trop mince (1,6 mm au moins)"', "vectorlab.relief.tenons_mince", "tenons : socle trop mince (1,6 mm au moins)", "pegs: base too thin (at least 1.6 mm)"),
    L(RE, 166, '"tenons : dalle trop étroite pour un logement"', "vectorlab.relief.tenons_etroite", "tenons : dalle trop étroite pour un logement", "pegs: slab too narrow for a socket"),
    L(RE, 168, '"tenons : arête trop courte pour un logement"', "vectorlab.relief.tenons_courte", "tenons : arête trop courte pour un logement", "pegs: edge too short for a socket"),

    # ── mod-geo : import GPX ──
    L(GE, 21, '"GPX : un point sans lat/lon numériques"', "vectorlab.geo.err_point", "GPX : un point sans lat/lon numériques", "GPX: a point without numeric lat/lon"),
    L(GE, 30, '"GPX : pas un fichier GPX (balise <gpx> absente)"', "vectorlab.geo.err_fichier", "GPX : pas un fichier GPX (balise <gpx> absente)", "GPX: not a GPX file (no <gpx> tag)"),
    L(GE, 41, '"GPX : aucun point (trkpt, rtept, wpt)"', "vectorlab.geo.err_aucun", "GPX : aucun point (trkpt, rtept, wpt)", "GPX: no points (trkpt, rtept, wpt)"),
    S(GE, 82,
      '" class="profil-alti" role="img" aria-label="profil altimétrique">`',
      '" class="profil-alti" role="img" aria-label="${T("vectorlab.geo.profil")}">`',
      {"vectorlab.geo.profil": ("profil altimétrique", "elevation profile")}),

    # ── mod-vivants : objets vivants ──
    X(VI, 32, '"forme"', "type d'objet du document comparé"),
    X(VI, 35, '"forme"', "type d'objet du document comparé"),
    S(VI, 59,
      '`objet introuvable: ${id}`',
      'T("vectorlab.vivants.err_introuvable", { id })',
      {"vectorlab.vivants.err_introuvable": ("objet introuvable: {id}", "object not found: {id}")}),
    S(VI, 62,
      '`${id} : ni contour vivant ni texte lié à un chemin`',
      'T("vectorlab.vivants.err_detacher", { id })',
      {"vectorlab.vivants.err_detacher": ("{id} : ni contour vivant ni texte lié à un chemin", "{id}: neither a live outline nor text on a path")}),

    # ── mod-grille : grille et plateau ──
    L(GR, 16, '"grille: pas > 0 requis"', "vectorlab.grille.err_pas", "grille: pas > 0 requis", "grid: spacing > 0 required"),
    X(GR, 73, '"plateau: spécification requise"', "invariant interne (appel sans spécification), jamais provoqué par l'écran"),
    L(GR, 77, '"plateau: rayon entier 0..60"', "vectorlab.grille.err_rayon", "plateau: rayon entier 0..60", "board: radius must be an integer 0..60"),
    L(GR, 86, '"plateau: colonnes et lignes entières 1..120"', "vectorlab.grille.err_rect", "plateau: colonnes et lignes entières 1..120", "board: columns and rows must be integers 1..120"),

    # ── mod-didact : l'aide didactique ──
    X(DI, 24, "'’\\-][\\p{L}\\p{N}]+)*/gu);","fragment de regex (le contrôle lit mal la classe de caractères)"),
    X(DI, 30, '"id manquant"', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    X(DI, 31, '"titre manquant"', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    X(DI, 33, '"phrase manquante"', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    X(DI, 34, '`phrase de ${n} mots (max ${DIDACT_MOTS_MAX})`', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    X(DI, 35, '"fichier .webp ou .png attendu"', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    X(DI, 36, '"version entière attendue"', "validation de fiche : sert à FILTRER aide/index.json, jamais affichée"),
    S(DI, 138,
      '"Aide : " + f.titre',
      'T("vectorlab.didact.aide", { titre: f.titre })',
      {"vectorlab.didact.aide": ("Aide : {titre}", "Help: {titre}")}, n=2),

    # ── divers ──
    X(SU, 68, '"forme"', "type d'objet du document comparé"),
    L(EX, 64, '"extrusion : trou hors de son contour"', "vectorlab.extrude.err_trou", "extrusion : trou hors de son contour", "extrusion: hole outside its outline"),
    L(EX, 152, '"extrusion : hauteur > 0 requise"', "vectorlab.extrude.err_hauteur", "extrusion : hauteur > 0 requise", "extrusion: height > 0 required"),
    X(EX, 193, '"Deepotus Vectorlab - extrusion STL (mm)"', "en-tête écrit dans le fichier STL exporté"),
    L(CR, 39, '"crayon : au moins deux points"', "vectorlab.divers.err_crayon", "crayon : au moins deux points", "pencil: at least two points"),
    L(PV, 8, '"Plat"', "vectorlab.divers.profil_plat", "Plat", "Flat"),
    L(PV, 9, '"Fuseau"', "vectorlab.divers.profil_fuseau", "Fuseau", "Taper"),
    L(PV, 10, '"Calligraphie"', "vectorlab.divers.profil_calligraphie", "Calligraphie", "Calligraphic"),
    L(PV, 22, '"trait : deux points au moins"', "vectorlab.divers.err_trait", "trait : deux points au moins", "stroke: at least two points"),
]
