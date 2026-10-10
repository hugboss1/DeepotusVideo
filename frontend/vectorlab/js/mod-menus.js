import { T } from "./mod-i18n.js";
// mod-menus.js — la barre de menus d'Affinity pour le Vectorlab : dix
// menus, entrées {id, libelle, raccourci?, action, ouvre?} ou "-"
// (séparateur). `action` est un NOM que l'UI résout (mod-charpente) ;
// `ouvre` désigne un onglet de la pile à montrer. Feuille pure ;
// l'inventaire du 18/09 donne l'ordre et les libellés, seules les entrées
// réalisables par le Vectorlab sont là.
const e = (id, libelle, action, raccourci, extra) => ({ id, libelle, action, raccourci: raccourci || "", ...(extra || {}) });
export const MENUS_BARRE = [
  { titre: T("vectorlab.menus.t_fichier"), entrees: [
    e("accueil", T("vectorlab.menus.accueil"), "biblio", "ctrl+alt+h"), "-",
    e("nouveau", T("vectorlab.menus.nouveau"), "nouveau", "ctrl+n"), e("ouvrir", T("vectorlab.menus.ouvrir"), "biblio", "ctrl+o"), "-",
    e("sauver", T("vectorlab.menus.sauver"), "sauver", "ctrl+s"), e("brouillon", T("vectorlab.menus.brouillon"), "brouillon"), "-",
    e("inserer", T("vectorlab.menus.inserer"), "imageFichier", "ctrl+shift+m"), e("insererBiblio", T("vectorlab.menus.inserer_biblio"), "imageBiblio"), e("coller", T("vectorlab.menus.coller_nouveau"), "imageColler"), e("generer", T("vectorlab.menus.generer"), "imageGenerer"), e("gpx", T("vectorlab.menus.gpx"), "gpx", "", { ouvre: "carte" }), "-",
    e("exporter", T("vectorlab.menus.exporter"), "exporter", "ctrl+alt+shift+s", { ouvre: "exporter" }), e("exporterSvg", T("vectorlab.menus.exporter_svg"), "expSvg"), e("exporterPng", T("vectorlab.menus.exporter_png"), "expPng2"), e("print3d", T("vectorlab.menus.print3d"), "expPrint3d"), e("bible", T("vectorlab.menus.bible"), "expBible"), "-",
    e("metadonnees", T("vectorlab.menus.metadonnees"), "configDoc"),
  ] },
  { titre: T("vectorlab.menus.t_edition"), entrees: [
    e("annuler", T("vectorlab.menus.annuler"), "annuler", "ctrl+z"), e("refaire", T("vectorlab.menus.refaire"), "refaire", "ctrl+shift+z"), "-",
    e("toutSelectionner", T("vectorlab.menus.tout_selectionner"), "toutSelectionner", "ctrl+a"), e("deselectionner", T("vectorlab.menus.deselectionner"), "deselectionner", "escape"), e("selAttribut", T("vectorlab.menus.sel_attribut"), "selAttribut"), "-",
    e("copier", T("vectorlab.menus.copier"), "copier", "ctrl+c"), e("collerObj", T("vectorlab.menus.coller"), "coller", "ctrl+v"), e("dupliquer", T("vectorlab.menus.dupliquer"), "dupliquer", "ctrl+d"), e("puissance", T("vectorlab.menus.puissance"), "puissance"), e("supprimer", T("vectorlab.menus.supprimer"), "supprimer", "delete"), "-",
    e("style", T("vectorlab.menus.style"), "creerStyle"), e("instantane", T("vectorlab.menus.instantane"), "instantane"), "-",
    e("parametres", T("vectorlab.menus.parametres"), "parametres", "ctrl+,"),
  ] },
  { titre: "Document", entrees: [
    e("configDoc", T("vectorlab.menus.config_doc"), "configDoc"), e("unites", T("vectorlab.menus.unites"), "unite"), "-",
    e("planches", T("vectorlab.menus.planches"), "ouvrir", "", { ouvre: "planches" }), e("reperes", T("vectorlab.menus.reperes"), "ouvrir", "", { ouvre: "reperes" }), e("grilleDoc", T("vectorlab.menus.grille_doc"), "ouvrir", "", { ouvre: "grille" }), e("plateau", T("vectorlab.menus.plateau"), "ouvrir", "", { ouvre: "plateau" }), e("carte", T("vectorlab.menus.carte"), "ouvrir", "", { ouvre: "carte" }), "-",
    e("instantaneDoc", T("vectorlab.menus.instantane"), "instantane"), e("historique", T("vectorlab.menus.historique"), "ouvrir", "", { ouvre: "historique" }),
  ] },
  { titre: T("vectorlab.menus.t_texte"), entrees: [
    e("poserTexte", T("vectorlab.menus.poser_texte"), "outil:texte", "t"), e("polices", T("vectorlab.menus.polices"), "flyout:texte"), e("editer", T("vectorlab.menus.editer"), "editerTexte"), "-",
    e("vectoriserTexteMenu", T("vectorlab.menus.vectoriser"), "vectoriserTexte", "ctrl+enter"), e("vectoriserGlyphes", T("vectorlab.menus.vectoriser_glyphes"), "vectoriserGlyphes"), e("logo3d", T("vectorlab.menus.logo3d"), "expPrint3d"), "-",
    e("panneauTexte", T("vectorlab.menus.panneau_texte"), "ouvrir", "", { ouvre: "texte" }),
  ] },
  { titre: T("vectorlab.menus.t_vecteur"), entrees: [
    e("vectoriserTexte", T("vectorlab.menus.vectoriser"), "vectoriserTexte", "ctrl+enter"), e("symbole", T("vectorlab.menus.symbole"), "symboleCreer"), "-",
    e("boolUnion", T("vectorlab.menus.bool_union"), "bool:union"), e("boolSoustraction", T("vectorlab.menus.bool_soustraction"), "bool:soustraction"), e("boolIntersection", T("vectorlab.menus.bool_intersection"), "bool:intersection"), e("boolDivision", T("vectorlab.menus.bool_division"), "bool:division"), "-",
    e("grouper", T("vectorlab.menus.grouper"), "grouper", "ctrl+g"), e("degrouper", T("vectorlab.menus.degrouper"), "degrouper", "ctrl+shift+g"), "-",
    e("joindre", T("vectorlab.menus.joindre"), "noeuds:joindre"), e("inverser", T("vectorlab.menus.inverser"), "noeuds:inverser"), e("diviser", T("vectorlab.menus.diviser"), "noeuds:diviser"), e("coins", T("vectorlab.menus.coins"), "noeuds:coins"), "-",
    e("tracerImage", T("vectorlab.menus.tracer_image"), "imageVectoriser"), e("formes", T("vectorlab.menus.formes"), "flyout:forme"),
  ] },
  { titre: "Pixel", entrees: [
    e("pxCalque", T("vectorlab.menus.px_calque"), "imageBiblio", "ctrl+shift+n"), e("pxEditer", T("vectorlab.menus.px_editer"), "pxEditer"), "-",
    e("pxTout", T("vectorlab.menus.tout_selectionner"), "pixel:tout"), e("pxAucune", T("vectorlab.menus.deselectionner"), "pixel:aucune"), e("pxInverser", T("vectorlab.menus.px_inverser"), "pixel:inverser", "ctrl+i"), e("pxCroitre", T("vectorlab.menus.px_croitre"), "pixel:croitre"), e("pxContracter", T("vectorlab.menus.px_contracter"), "pixel:contracter"), e("pxCouleur", T("vectorlab.menus.px_couleur"), "pixel:couleur"), "-",
    e("pxPanneau", T("vectorlab.menus.px_panneau"), "ouvrir", "", { ouvre: "pixel" }), e("pxArt", T("vectorlab.menus.px_art"), "ouvrir", "", { ouvre: "pixel" }),
  ] },
  { titre: T("vectorlab.menus.t_calque"), entrees: [
    e("calqueNouveau", T("vectorlab.menus.calque_nouveau"), "calqueNouveau"), e("calqueRenommer", T("vectorlab.menus.calque_renommer"), "calqueRenommer"), e("calqueSupprimer", T("vectorlab.menus.calque_supprimer"), "calqueSupprimer"), "-",
    e("grouperC", T("vectorlab.menus.grouper"), "grouper", "ctrl+g"), e("degrouperC", T("vectorlab.menus.degrouper"), "degrouper", "ctrl+shift+g"), "-",
    e("verrouiller", T("vectorlab.menus.verrouiller"), "calqueVerrou"), e("masquer", T("vectorlab.menus.masquer"), "calqueOeil"), "-",
    e("devant", T("vectorlab.menus.devant"), "ordre:devant"), e("avant", T("vectorlab.menus.avant"), "ordre:avant"), e("arriere", T("vectorlab.menus.arriere"), "ordre:arriere"), e("derriere", T("vectorlab.menus.derriere"), "ordre:derriere"), "-",
    e("effets", T("vectorlab.menus.effets"), "ouvrir", "", { ouvre: "apparence" }), e("panneauCalques", T("vectorlab.menus.panneau_calques"), "ouvrir", "", { ouvre: "calques" }),
  ] },
  { titre: T("vectorlab.menus.t_affichage"), entrees: [
    e("zoomAjuster", T("vectorlab.menus.zoom_ajuster"), "zoomAjuster", "ctrl+0"), e("zoomCent", T("vectorlab.menus.zoom_cent"), "zoomCent", "ctrl+1"), "-",
    e("grille", T("vectorlab.menus.grille"), "grille", "g"), e("aimant", T("vectorlab.menus.aimant"), "aimant"), e("unite", T("vectorlab.menus.unite"), "unite"), "-",
    e("persVecteur", T("vectorlab.menus.pers_vecteur"), "persona:vecteur"), e("persPixel", T("vectorlab.menus.pers_pixel"), "persona:pixel"),
  ] },
  { titre: T("vectorlab.menus.t_fenetre"), entrees: [
    e("wCouleur", T("vectorlab.menus.w_couleur"), "ouvrir", "", { ouvre: "couleur" }), e("wApparence", T("vectorlab.menus.w_apparence"), "ouvrir", "", { ouvre: "apparence" }), e("wTexte", T("vectorlab.menus.t_texte"), "ouvrir", "", { ouvre: "texte" }), "-",
    e("wCalques", T("vectorlab.menus.w_calques"), "ouvrir", "", { ouvre: "calques" }), e("wTrace", T("vectorlab.menus.w_trace"), "ouvrir", "", { ouvre: "trace" }), e("wImage", "Image", "ouvrir", "", { ouvre: "image" }), e("wStock", T("vectorlab.menus.w_stock"), "ouvrir", "", { ouvre: "stock" }), "-",
    e("wTransformer", T("vectorlab.menus.w_transformer"), "ouvrir", "", { ouvre: "transformer" }), e("wNavigateur", T("vectorlab.menus.w_navigateur"), "ouvrir", "", { ouvre: "navigateur" }), e("wHistorique", T("vectorlab.menus.w_historique"), "ouvrir", "", { ouvre: "historique" }), e("wExporter", T("vectorlab.menus.w_exporter"), "ouvrir", "", { ouvre: "exporter" }),
  ] },
  { titre: T("vectorlab.menus.t_aide"), entrees: [
    e("raccourcis", T("vectorlab.menus.raccourcis"), "raccourcis", "f1"), e("guide", T("vectorlab.menus.guide"), "guide"), "-", e("apropos", T("vectorlab.menus.apropos"), "apropos"),
  ] },
];
const LIB = { ctrl: "Ctrl", shift: T("vectorlab.menus.touche_maj"), alt: "Alt", enter: T("vectorlab.menus.touche_entree"), escape: T("vectorlab.menus.touche_echap"), delete: T("vectorlab.menus.touche_suppr"), ",": "," };
export function raccourci_de(entree) {
  const r = entree && entree.raccourci;
  if (!r) return "";
  return r.split("+").map((k) => LIB[k] || (k.length === 1 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1))).join("+");
}
export function menus_construire(menus, peut) {
  return (menus || []).map((m) => ({ titre: m.titre, entrees: m.entrees.map((x) => x === "-" ? "-" : { ...x, desactive: peut ? !peut(x.action, x) : false }) }));
}
export const menu_trouver = (menus, titre) => (menus || []).find((m) => m.titre === titre) || null;
