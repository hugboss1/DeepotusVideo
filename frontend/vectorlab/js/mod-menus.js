// mod-menus.js — la barre de menus d'Affinity pour le Vectorlab : dix
// menus, entrées {id, libelle, raccourci?, action, ouvre?} ou "-"
// (séparateur). `action` est un NOM que l'UI résout (mod-charpente) ;
// `ouvre` désigne un onglet de la pile à montrer. Feuille pure ;
// l'inventaire du 18/09 donne l'ordre et les libellés, seules les entrées
// réalisables par le Vectorlab sont là.
const e = (id, libelle, action, raccourci, extra) => ({ id, libelle, action, raccourci: raccourci || "", ...(extra || {}) });
export const MENUS_BARRE = [
  { titre: "Fichier", entrees: [
    e("accueil", "Accueil (Bibliothèque)", "biblio", "ctrl+alt+h"), "-",
    e("nouveau", "Nouveau…", "nouveau", "ctrl+n"), e("ouvrir", "Ouvrir…", "biblio", "ctrl+o"), "-",
    e("sauver", "Enregistrer", "sauver", "ctrl+s"), e("brouillon", "Restaurer le brouillon", "brouillon"), "-",
    e("inserer", "Insérer une image…", "imageFichier", "ctrl+shift+m"), e("insererBiblio", "Insérer depuis la Bibliothèque…", "imageBiblio"), e("coller", "Nouveau depuis Presse-papiers", "imageColler"), e("generer", "Nouveau traitement d'image (IA)…", "imageGenerer"), e("gpx", "Importer un GPX…", "gpx", "", { ouvre: "carte" }), "-",
    e("exporter", "Exporter…", "exporter", "ctrl+alt+shift+s", { ouvre: "exporter" }), e("exporterSvg", "Exporter SVG", "expSvg"), e("exporterPng", "Exporter PNG 2×", "expPng2"), e("print3d", "Impression 3D…", "expPrint3d"), e("bible", "Vers la Bible…", "expBible"), "-",
    e("metadonnees", "Configuration du document…", "configDoc"),
  ] },
  { titre: "Edition", entrees: [
    e("annuler", "Annuler", "annuler", "ctrl+z"), e("refaire", "Rétablir", "refaire", "ctrl+shift+z"), "-",
    e("toutSelectionner", "Tout sélectionner", "toutSelectionner", "ctrl+a"), e("deselectionner", "Désélectionner", "deselectionner", "escape"), e("selAttribut", "Sélectionner par attribut…", "selAttribut"), "-",
    e("copier", "Copier", "copier", "ctrl+c"), e("collerObj", "Coller", "coller", "ctrl+v"), e("dupliquer", "Dupliquer", "dupliquer", "ctrl+d"), e("puissance", "Dupliquer en puissance…", "puissance"), e("supprimer", "Supprimer", "supprimer", "delete"), "-",
    e("style", "Créer un style", "creerStyle"), e("instantane", "Ajouter un instantané", "instantane"), "-",
    e("parametres", "Paramètres…", "parametres", "ctrl+,"),
  ] },
  { titre: "Document", entrees: [
    e("configDoc", "Configuration…", "configDoc"), e("unites", "Unité d'affichage suivante", "unite"), "-",
    e("planches", "Planches…", "ouvrir", "", { ouvre: "planches" }), e("reperes", "Marges et fond perdu…", "ouvrir", "", { ouvre: "reperes" }), e("grilleDoc", "Grille du document…", "ouvrir", "", { ouvre: "grille" }), e("plateau", "Plateau et terrains…", "ouvrir", "", { ouvre: "plateau" }), e("carte", "Carte réelle…", "ouvrir", "", { ouvre: "carte" }), "-",
    e("instantaneDoc", "Ajouter un instantané", "instantane"), e("historique", "Historique…", "ouvrir", "", { ouvre: "historique" }),
  ] },
  { titre: "Texte", entrees: [
    e("poserTexte", "Outil Texte", "outil:texte", "t"), e("polices", "Typographies…", "flyout:texte"), e("editer", "Éditer le texte sélectionné", "editerTexte"), "-",
    e("vectoriserTexteMenu", "Convertir en courbes", "vectoriserTexte", "ctrl+enter"), e("vectoriserGlyphes", "Convertir en courbes par glyphe", "vectoriserGlyphes"), e("logo3d", "Logo 3D…", "expPrint3d"), "-",
    e("panneauTexte", "Panneau Texte…", "ouvrir", "", { ouvre: "texte" }),
  ] },
  { titre: "Vecteur", entrees: [
    e("vectoriserTexte", "Convertir en courbes", "vectoriserTexte", "ctrl+enter"), e("symbole", "Créer un symbole", "symboleCreer"), "-",
    e("boolUnion", "Géométrie : Union", "bool:union"), e("boolSoustraction", "Géométrie : Soustraction", "bool:soustraction"), e("boolIntersection", "Géométrie : Intersection", "bool:intersection"), e("boolDivision", "Géométrie : Division", "bool:division"), "-",
    e("grouper", "Grouper", "grouper", "ctrl+g"), e("degrouper", "Dégrouper", "degrouper", "ctrl+shift+g"), "-",
    e("joindre", "Relier les courbes", "noeuds:joindre"), e("inverser", "Inverser le sens", "noeuds:inverser"), e("diviser", "Diviser au nœud", "noeuds:diviser"), e("coins", "Arrondir les coins", "noeuds:coins"), "-",
    e("tracerImage", "Traçage d'image…", "imageVectoriser"), e("formes", "Formes paramétriques…", "flyout:forme"),
  ] },
  { titre: "Pixel", entrees: [
    e("pxCalque", "Nouveau calque pixel (poser une image)", "imageBiblio", "ctrl+shift+n"), e("pxEditer", "Éditer les pixels", "pxEditer"), "-",
    e("pxTout", "Tout sélectionner", "pixel:tout"), e("pxAucune", "Désélectionner", "pixel:aucune"), e("pxInverser", "Inverser la sélection", "pixel:inverser", "ctrl+i"), e("pxCroitre", "Croître", "pixel:croitre"), e("pxContracter", "Contracter", "pixel:contracter"), e("pxCouleur", "Sélectionner par couleur", "pixel:couleur"), "-",
    e("pxPanneau", "Réglages et filtres…", "ouvrir", "", { ouvre: "pixel" }), e("pxArt", "Pixel-art vers Tilelab…", "ouvrir", "", { ouvre: "pixel" }),
  ] },
  { titre: "Calque", entrees: [
    e("calqueNouveau", "Nouveau calque", "calqueNouveau"), e("calqueRenommer", "Renommer le calque", "calqueRenommer"), e("calqueSupprimer", "Supprimer le calque", "calqueSupprimer"), "-",
    e("grouperC", "Grouper", "grouper", "ctrl+g"), e("degrouperC", "Dégrouper", "degrouper", "ctrl+shift+g"), "-",
    e("verrouiller", "Verrouiller / déverrouiller le calque", "calqueVerrou"), e("masquer", "Masquer / afficher le calque", "calqueOeil"), "-",
    e("devant", "Tout devant", "ordre:devant"), e("avant", "Un cran devant", "ordre:avant"), e("arriere", "Un cran derrière", "ordre:arriere"), e("derriere", "Tout derrière", "ordre:derriere"), "-",
    e("effets", "Effets de calque…", "ouvrir", "", { ouvre: "apparence" }), e("panneauCalques", "Panneau Calques…", "ouvrir", "", { ouvre: "calques" }),
  ] },
  { titre: "Affichage", entrees: [
    e("zoomAjuster", "Zoom : ajuster", "zoomAjuster", "ctrl+0"), e("zoomCent", "Zoom : 100 %", "zoomCent", "ctrl+1"), "-",
    e("grille", "Grille", "grille", "g"), e("aimant", "Magnétisme aux objets", "aimant"), e("unite", "Unité des règles", "unite"), "-",
    e("persVecteur", "Persona Vecteur", "persona:vecteur"), e("persPixel", "Persona Pixel", "persona:pixel"),
  ] },
  { titre: "Fenêtre", entrees: [
    e("wCouleur", "Couleur", "ouvrir", "", { ouvre: "couleur" }), e("wApparence", "Apparence", "ouvrir", "", { ouvre: "apparence" }), e("wTexte", "Texte", "ouvrir", "", { ouvre: "texte" }), "-",
    e("wCalques", "Calques", "ouvrir", "", { ouvre: "calques" }), e("wTrace", "Tracé", "ouvrir", "", { ouvre: "trace" }), e("wImage", "Image", "ouvrir", "", { ouvre: "image" }), e("wStock", "Stock (Bibliothèque)", "ouvrir", "", { ouvre: "stock" }), "-",
    e("wTransformer", "Transformer", "ouvrir", "", { ouvre: "transformer" }), e("wNavigateur", "Navigateur", "ouvrir", "", { ouvre: "navigateur" }), e("wHistorique", "Historique", "ouvrir", "", { ouvre: "historique" }), e("wExporter", "Exporter", "ouvrir", "", { ouvre: "exporter" }),
  ] },
  { titre: "Aide", entrees: [
    e("raccourcis", "Raccourcis clavier…", "raccourcis", "f1"), e("guide", "Guide du Vectorlab…", "guide"), "-", e("apropos", "À propos…", "apropos"),
  ] },
];
const LIB = { ctrl: "Ctrl", shift: "Maj", alt: "Alt", enter: "Entrée", escape: "Échap", delete: "Suppr", ",": "," };
export function raccourci_de(entree) {
  const r = entree && entree.raccourci;
  if (!r) return "";
  return r.split("+").map((k) => LIB[k] || (k.length === 1 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1))).join("+");
}
export function menus_construire(menus, peut) {
  return (menus || []).map((m) => ({ titre: m.titre, entrees: m.entrees.map((x) => x === "-" ? "-" : { ...x, desactive: peut ? !peut(x.action, x) : false }) }));
}
export const menu_trouver = (menus, titre) => (menus || []).find((m) => m.titre === titre) || null;
