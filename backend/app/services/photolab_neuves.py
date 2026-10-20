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
"""

COMMANDES_NEUVES_FERMEES = frozenset({
    "brush.presets.importImage", "brush.presets.setCurrent",
    "brush.presets.update", "channel.target.layerMask", "document.move", "document.presets.delete",
    "document.presets.get", "document.presets.list", "document.presets.save", "document.recent.add",
    "document.recent.list", "document.sampleColor", "edit.deleteAndFillSelection", "edit.fillHistory",
    "edit.installedProfiles", "edit.transform.warpGrid", "file.export.presets.delete", "file.export.presets.get",
    "file.export.presets.list", "file.export.presets.save", "file.exrParts", "file.openExrParts",
    "file.print.page", "file.print.printers", "file.printers", "file.revealInFinder",
    "filter.other.colorToAlpha", "filter.render.relight", "gradient.presets.stop", "history.deleteSnapshot",
    "history.deleteState", "history.newDocument", "history.newSnapshot", "history.redo",
    "history.renameSnapshot", "history.selectSnapshot", "history.selectState", "history.undo",
    "image.detectFaces", "layer.artboard.addBeside", "layer.copyToDocument", "layer.fill.pattern.set",
    "layer.fill.solidColor.set", "layer.layerMask.edit", "layer.layerStyle.defaultFor", "layer.layerStyle.makeDefault",
    "layer.layerStyle.replace", "layer.layerStyle.transferEffects", "layer.list", "layer.mergeGroup",
    "layer.new.backgroundFromLayer", "layer.new.frame", "layer.rasterize.layerStyle", "layer.removeBackground",
    "layer.selectInRect", "layer.setEffectsVisible", "layer.setLabelColor", "layer.showOnly",
    "layer.smartFilter.transfer", "layer.smartObjects.convertToLayers", "layer.smartObjects.updateChanged", "layer.toggleLockTransparency",
    "layer.toggleMaskOverlay", "swatches.add", "swatches.delete", "swatches.deleteGroup",
    "swatches.export", "swatches.import", "swatches.list", "swatches.move",
    "swatches.newGroup", "swatches.rename", "swatches.renameGroup", "swatches.reset",
    "swatches.use", "tools.decreaseBrushHardness", "tools.decreaseBrushSize", "tools.increaseBrushHardness",
    "tools.increaseBrushSize", "tools.rotateBrush", "type.caret", "type.hitTest",
    "type.navigate", "view.editGuide", "view.resetRulerOrigin", "view.setRulerOrigin",
})
