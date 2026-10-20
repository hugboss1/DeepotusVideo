// mod-libelles.js — t258 (Photolab M9) : le libellé d'une commande du moteur hors de l'arbre des menus (étapes du
// panneau Actions, dialogues qu'il ouvre, états de l'Historique). Ordre, du plus prioritaire au repli :
//   1. le catalogue des menus (donnees/menus.json `entrees`) : nos libellés, inchangés ;
//   2. LIBELLES_COMMANDES : nos clés du dictionnaire pour les commandes que les lots M3-M8 ont ouvertes (la même
//      clé que l'outil, le menu ou l'état d'historique de l'écran quand il en a déjà une) ;
//   3. le repli de l'amont (menus.json `repli`) : libellé anglais du moteur, français du fr.tsv de photocraft v0.10.0
//      quand il l'a ;
//   4. l'id du moteur tel quel, brut (jamais traduit).
// Fonctions PURES (qa/libelles-m9.test.mjs).

export const LIBELLES_COMMANDES = {
  // t252 (M3) : retouche
  "paint.patch": "photolab.outil.patch",
  "paint.contentAwareMove": "photolab.outil.content_aware_move",
  "paint.patternStamp": "photolab.outil.pattern_stamp",
  "paint.redEye": "photolab.outil.red_eye",
  "paint.remove": "photolab.outil.remove",
  "paint.setSymmetry": "photolab.commande.paint.set_symmetry",
  "paint.symmetryFromPath": "photolab.commande.paint.symmetry_from_path",
  "paint.symmetryDisable": "photolab.commande.paint.symmetry_disable",
  // t253 (M4) : sélection, recadrage, échantillonneurs
  "select.magneticLasso": "photolab.outil.magnetic_lasso",
  "select.float": "photolab.commande.select.float",
  "select.drop": "photolab.commande.select.drop",
  "select.loadLuminosity": "photolab.menu.charger_luminosite",
  "image.perspectiveCrop": "photolab.outil.perspective_crop",
  "view.colorSamplers.add": "photolab.commande.view.color_samplers.add",
  "view.colorSamplers.move": "photolab.commande.view.color_samplers.move",
  "view.colorSamplers.delete": "photolab.commande.view.color_samplers.delete",
  "view.colorSamplers.clear": "photolab.commande.view.color_samplers.clear",
  "view.colorSamplers.list": "photolab.commande.view.color_samplers.list",
  // t254 (M5) : tracés et texte
  "path.moveAnchors": "photolab.histo.drag_anchor_points",
  "path.moveHandle": "photolab.histo.drag_direction_point",
  "path.bendSegment": "photolab.histo.drag_segment",
  "path.convertPoint": "photolab.outil.convert_point",
  "path.addAnchor": "photolab.outil.add_anchor_point",
  "path.deleteAnchor": "photolab.outil.delete_anchor_point",
  "path.transform": "photolab.traces.transformer",
  "path.clippingPath.set": "photolab.traces.detourage",
  "path.clippingPath.clear": "photolab.traces.detourage_retirer",
  "path.style.copyFill": "photolab.traces.copier_fond",
  "path.style.copyStroke": "photolab.traces.copier_contour",
  "path.style.pasteFill": "photolab.traces.coller_fond",
  "path.style.pasteStroke": "photolab.histo.paste_stroke",
  "type.createSelection": "photolab.histo.type_mask",
  "type.attachToPath": "photolab.histo.type_on_path",
  "type.detachFromPath": "photolab.histo.release_type",
  "type.increaseSize": "photolab.commande.type.increase_size",
  "type.decreaseSize": "photolab.commande.type.decrease_size",
  "type.increaseSizeMore": "photolab.commande.type.increase_size_more",
  "type.decreaseSizeMore": "photolab.commande.type.decrease_size_more",
  // t255 (M6) : panneau Actions
  "actions.assignSet": "photolab.commande.actions.assign_set",
  "actions.conditional": "photolab.commande.actions.conditional",
  "actions.delete": "photolab.commande.actions.delete",
  "actions.dialog": "photolab.commande.actions.dialog",
  "actions.get": "photolab.commande.actions.get",
  "actions.insert": "photolab.commande.actions.insert",
  "actions.list": "photolab.commande.actions.list",
  "actions.load": "photolab.actions.menu.charger",
  "actions.move": "photolab.commande.actions.move",
  "actions.photoshopStep": "photolab.commande.actions.photoshop_step",
  "actions.play": "photolab.commande.actions.play",
  "actions.record": "photolab.commande.actions.record",
  "actions.rename": "photolab.commande.actions.rename",
  "actions.save": "photolab.actions.menu.sauver",
  "actions.setColor": "photolab.commande.actions.set_color",
  "actions.stop": "photolab.commande.actions.stop",
  "actions.stopMessage": "photolab.actions.etape_arret",
  "actions.toggle": "photolab.commande.actions.toggle",
  // t256 (M7) : calques, historique, déformation
  "layer.removeBackground": "photolab.histo.retirer_arriere_plan",
  "filter.render.relight": "photolab.menu.reeclairer",
  "filter.other.colorToAlpha": "photolab.menu.couleur_alpha",
  "layer.showOnly": "photolab.histo.afficher_seul",
  "layer.toggleLockTransparency": "photolab.verrou.transparence",
  "layer.setLabelColor": "photolab.histo.couleur_calque",
  "layer.mergeGroup": "photolab.menu.fusionner_groupe",
  "layer.copyToDocument": "photolab.menu.copier_document",
  "layer.new.frame": "photolab.histo.nouveau_cadre",
  "layer.artboard.addBeside": "photolab.menu.plan_voisin",
  "layer.layerStyle.transferEffects": "photolab.histo.deplacer_effets",
  "layer.layerStyle.makeDefault": "photolab.commande.layer.layer_style.make_default",
  "layer.layerStyle.defaultFor": "photolab.commande.layer.layer_style.default_for",
  "layer.layerMask.edit": "photolab.histo.modifier_masque",
  "layer.smartObjects.convertToLayers": "photolab.menu.convertir_calques",
  "layer.new.backgroundFromLayer": "photolab.menu.arriere_plan_depuis_calque",
  "layer.rasterize.layerStyle": "photolab.histo.pixelliser_style",
  "history.newSnapshot": "photolab.historique.nouvel_instantane",
  "history.deleteSnapshot": "photolab.historique.supprimer_instantane",
  "history.renameSnapshot": "photolab.commande.history.rename_snapshot",
  "history.selectSnapshot": "photolab.commande.history.select_snapshot",
  "history.newDocument": "photolab.historique.nouveau_document",
  "edit.transform.warpGrid": "photolab.commande.edit.transform.warp_grid",
  // t257 (M8) : formats et exports — aucune commande moteur neuve hors de l'arbre (l'écran sert ses entrées).
};

const sansPoints = (s) => String(s).replace(/…$/, "").trim();

// Index du repli de l'amont (menus.json `repli` : {id: {libelle_en, libelle_fr?}}).
export function indexRepli(c) {
  return new Map(Object.entries((c && c.repli) || {}));
}

// catalogue : Map id -> entrée (mod-actions indexCatalogue), qui porte le repli en `.repli` ; t = dzT.
// Rend {texte} ; {texte, brut: true} pour l'id du moteur ; {texte, amont: true} pour un libellé du repli.
export function libelleCommande(id, catalogue, lang = "fr", t = (c) => c) {
  const e = catalogue && catalogue.get ? catalogue.get(id) : null;
  if (e) return { texte: sansPoints((lang === "en" ? e.libelle_en : e.libelle_fr) || e.libelle_fr || id) };
  const cle = LIBELLES_COMMANDES[id];
  if (cle && typeof t === "function") {
    const s = t(cle);
    if (typeof s === "string" && s !== "" && s !== cle) return { texte: sansPoints(s) };   // dzT rend la clé si elle manque
  }
  const r = catalogue && catalogue.repli && catalogue.repli.get ? catalogue.repli.get(id) : null;
  const amont = r && (lang === "en" ? r.libelle_en : r.libelle_fr);
  if (amont) return { texte: sansPoints(amont), amont: true };
  return { texte: id, brut: true };
}
