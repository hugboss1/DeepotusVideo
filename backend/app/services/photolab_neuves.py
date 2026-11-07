# -*- coding: utf-8 -*-
"""t251 (Photolab M2, 20/10/2026) — les 142 commandes que photocraft 0.10.0 ajoute à 0.3.0, FERMÉES au Photolab.

La montée de moteur ne doit rien ouvrir en douce : la liste blanche du pont (photolab_registre.verifier) suit le
registre du moteur, qui gagne ces commandes avec 0.10. Elles restent refusées tant qu'un lot ne les ouvre pas
une à une (plan 2026-10-20-photolab-photocraft-0.10 : M3 retouche, M4 sélection, M5 plume et texte, M6 Actions,
M7 calques/historique/nuancier, M8 formats) — ouvrir = retirer l'id d'ici, avec son banc.

Liste = ids de tests/photocraft_commandes_0.10.0.json absents de tests/photocraft_commandes_0.3.0.json (le banc
test_photolab_registre le recalcule et compare).

Ouvertes depuis (retirées d'ici, avec leurs bancs) :
  t252 (M3, 20/10) : paint.patch, paint.contentAwareMove, paint.patternStamp, paint.redEye, paint.remove,
                     paint.setSymmetry, paint.symmetryFromPath, paint.symmetryDisable
  t253 (M4, 20/10) : select.magneticLasso, select.float, select.drop, select.loadLuminosity, image.perspectiveCrop,
                     view.colorSamplers.add / move / delete / clear / list
  t254 (M5, 20/10) : path.moveAnchors, path.moveHandle, path.bendSegment, path.convertPoint, path.addAnchor,
                     path.deleteAnchor, path.transform, path.clippingPath.set / clear, path.style.copyFill / copyStroke /
                     pasteFill / pasteStroke, type.createSelection, type.attachToPath, type.detachFromPath,
                     type.increaseSize / decreaseSize / increaseSizeMore / decreaseSizeMore
                     (type.hitTest, caret, navigate restent fermées : la saisie se fait dans l'éditeur de l'écran)
  t255 (M6, 20/10) : les 18 actions.* (panneau Actions) — assignSet, conditional, delete, dialog, get, insert, list,
                     load, move, photoshopStep, play, record, rename, save, setColor, stop, stopMessage, toggle
                     (formes vérifiées par photolab_registre._v_actions / verifier_etape)
  t256 (M7, 20/10) : calques — layer.removeBackground, filter.render.relight, filter.other.colorToAlpha,
                     layer.showOnly, layer.toggleLockTransparency, layer.setLabelColor, layer.mergeGroup,
                     layer.copyToDocument, layer.new.frame, layer.artboard.addBeside, layer.layerStyle.transferEffects /
                     makeDefault / defaultFor, layer.layerMask.edit, layer.smartObjects.convertToLayers,
                     layer.new.backgroundFromLayer, layer.rasterize.layerStyle (formes : photolab_registre._v_m7)
                     (layer.layerStyle.replace reste fermée : le dialogue Style de calque applique effet par effet ;
                     layer.smartObjects.updateChanged / relinkToFile / replaceContents / exportContents / convertToLinked :
                     le moteur 0.10 les DÉSACTIVE en automation — « uses ambient filesystem paths »)
  t256 (M7 PR 2, 20/10) : instantanés et document d'après un état — history.newSnapshot, deleteSnapshot,
                     renameSnapshot, selectSnapshot, newDocument (panneau Historique). history.undo / redo / selectState /
                     deleteState restent fermées : le panneau annule déjà par /historique. Les swatches.* restent fermées
                     à /executer : seules les routes /nuancier/importer et /nuancier/exporter les jouent (photolab_nuancier)
  t256 (M7 PR 3, 20/10) : edit.transform.warpGrid — le maillage de Ctrl+T › Déformer (grille Par défaut / 3 / 4 / 5 ;
                     découpe qui garde la surface) ; la validation passe par edit.transform.warp {warp} (0.3.0, déjà ouverte)
"""

COMMANDES_NEUVES_FERMEES = frozenset({
    "brush.presets.importImage", "brush.presets.setCurrent", "brush.presets.update", "channel.target.layerMask",
    "document.move", "document.presets.delete", "document.presets.get", "document.presets.list",
    "document.presets.save", "document.recent.add", "document.recent.list", "document.sampleColor",
    "edit.deleteAndFillSelection", "edit.fillHistory", "edit.installedProfiles", "file.export.presets.delete",
    "file.export.presets.get", "file.export.presets.list", "file.export.presets.save", "file.exrParts",
    "file.openExrParts", "file.print.page", "file.print.printers", "file.printers", "file.revealInFinder",
    "gradient.presets.stop", "history.deleteState", "history.redo", "history.selectState", "history.undo",
    "image.detectFaces", "layer.fill.pattern.set", "layer.fill.solidColor.set", "layer.layerStyle.replace",
    "layer.list", "layer.selectInRect", "layer.setEffectsVisible", "layer.smartFilter.transfer",
    "layer.smartObjects.updateChanged", "layer.toggleMaskOverlay", "swatches.add", "swatches.delete",
    "swatches.deleteGroup", "swatches.export", "swatches.import", "swatches.list", "swatches.move",
    "swatches.newGroup", "swatches.rename", "swatches.renameGroup", "swatches.reset", "swatches.use",
    "tools.decreaseBrushHardness", "tools.decreaseBrushSize", "tools.increaseBrushHardness",
    "tools.increaseBrushSize", "tools.rotateBrush", "type.caret", "type.hitTest", "type.navigate", "view.editGuide",
    "view.resetRulerOrigin", "view.setRulerOrigin",
})

# Montée 0.21.0 (07/11/2026) : les 75 commandes que photocraft 0.21.0 ajoute à 0.10.0, fermées de la même façon.
# Liste = ids de tests/photocraft_commandes_0.21.0.json absents de tests/photocraft_commandes_0.10.0.json.
COMMANDES_NEUVES_021 = frozenset({
    "actions.newSet", "actions.setHistory", "actions.setPlayback", "brush.mixer.clean", "brush.mixer.load",
    "brush.mixer.sample", "file.approveMemory", "help.checkForUpdates", "history.clear", "history.options",
    "history.setSource", "history.stepBackward", "history.stepForward", "layer.frame.convert", "layer.frame.fit",
    "layer.frame.info", "layer.frame.set", "layer.frame.setContent", "layer.layerStyle.contours.delete",
    "layer.layerStyle.contours.list", "layer.layerStyle.contours.load", "layer.layerStyle.contours.new",
    "layer.layerStyle.contours.save", "layer.smartObjects.embedAllLinked", "layer.smartObjects.exportSvg",
    "layer.smartObjects.updateSvg", "layer.smartObjects.updateVectorSource", "layer.xmpMetadata",
    "layerComp.reorder", "paint.artHistoryBrush", "paint.mixerLoad", "path.addToSelection",
    "path.mergeShapeComponents", "path.setOperation", "path.subtractFromSelection", "shape.presets.importCsh",
    "style.presets.exportAsl", "style.presets.importAsl", "tools.firstBrush", "tools.lastBrush", "tools.nextBrush",
    "tools.previousBrush", "type.fillPath", "type.font.favorite", "type.font.library",
    "type.openType.numerals.default", "type.openType.numerals.lining", "type.openType.numerals.oldstyle",
    "type.openType.numerals.proportional", "type.openType.numerals.proportionalLining",
    "type.openType.numerals.proportionalOldstyle", "type.openType.numerals.tabular",
    "type.openType.numerals.tabularLining", "type.openType.numerals.tabularOldstyle",
    "type.openType.stylisticSets.set1", "type.openType.stylisticSets.set10", "type.openType.stylisticSets.set11",
    "type.openType.stylisticSets.set12", "type.openType.stylisticSets.set13", "type.openType.stylisticSets.set14",
    "type.openType.stylisticSets.set15", "type.openType.stylisticSets.set16", "type.openType.stylisticSets.set17",
    "type.openType.stylisticSets.set18", "type.openType.stylisticSets.set19", "type.openType.stylisticSets.set2",
    "type.openType.stylisticSets.set20", "type.openType.stylisticSets.set3", "type.openType.stylisticSets.set4",
    "type.openType.stylisticSets.set5", "type.openType.stylisticSets.set6", "type.openType.stylisticSets.set7",
    "type.openType.stylisticSets.set8", "type.openType.stylisticSets.set9", "updates.status",
})
# Ouvertes depuis (avec leurs bancs) :
#   t417 (N7, 07/11) : layer.frame.* (Calque › Cadre).
#   t416 (N6, 07/11) : aucune ouverte à /executer : style.presets.importAsl / exportAsl et shape.presets.importCsh passent par
#                      /bibliotheques/*. layer.layerStyle.contours.* restent fermées : aucun champ Contour au dialogue.
#   t414 (N4, 07/11) : Mélangeur (mixerLoad, load, clean), Forme d'art d'historique, source de l'historique, pinceau
#                      précédent / suivant / premier / dernier. brush.mixer.sample et la clé mixerState restent fermés.
#   t413 (N3, 07/11) : path.setOperation, path.mergeShapeComponents. shape.create et shape.edit sortent du gel (angles
#                      arrondis, flèches). path.addToSelection / subtractFromSelection restent fermées : path.toSelection
#                      fait déjà la même chose par `mode`.
#   t415 (N5, 07/11) : history.clear. history.options et actions.setHistory passent par /options/moteur ; stepForward et
#                      stepBackward doublent Annuler / Rétablir ; actions.newSet n'a ni suppression ni renommage au moteur,
#                      les jeux vides restent à l'écran ; setPlayback ne rythme pas la lecture hors de l'app native.
#   t412 (N2, 07/11) : styles de chiffres, jeux stylistiques, Texte dans une forme. type.font.* reste fermée : les favoris
#                      sont gardés par l'écran, la commande écrirait les préférences du moteur.
OUVERTES_021 = frozenset({f"type.openType.numerals.{c}" for c in (
    "default", "lining", "oldstyle", "proportional", "tabular", "proportionalLining", "tabularLining", "proportionalOldstyle",
    "tabularOldstyle")} | {f"type.openType.stylisticSets.set{n}" for n in range(1, 21)} | {"type.fillPath"}
    | {"history.clear", "path.setOperation", "path.mergeShapeComponents"}
    | {"layer.frame.set", "layer.frame.info", "layer.frame.convert", "layer.frame.setContent", "layer.frame.fit"}
    | {"paint.artHistoryBrush", "paint.mixerLoad", "brush.mixer.load", "brush.mixer.clean", "history.setSource", "tools.previousBrush", "tools.nextBrush", "tools.firstBrush", "tools.lastBrush"})
COMMANDES_NEUVES_FERMEES = COMMANDES_NEUVES_FERMEES | (COMMANDES_NEUVES_021 - OUVERTES_021)
