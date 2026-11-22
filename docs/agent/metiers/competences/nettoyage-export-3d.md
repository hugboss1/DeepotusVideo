## Compétence : nettoyer, déplier, alléger, exporter

Outils libres de référence (licences compatibles avec la vente de l'app : MIT, Apache, zlib) :
- **Retopologie** : AutoRemesher (quads automatiques, organique) ; Quadriflow de Blender (perd les UV) ; décimation
  (garde les UV, sûre pour un modèle généré). RetopoFlow et PyMeshLab sont sous GPL : à conseiller, jamais à
  embarquer.
- **UV** : xatlas (dépliage et rangement automatiques, sans Blender) ; dans Blender, « Smart UV » puis rangement avec
  une marge en pixels ; viser une densité de texels égale sur tout le modèle.
- **Matières** : Material Maker (PBR procédural, MIT) ; ArmorPaint pour peindre à la main.
- **Densités et poids** : gltfpack (meshoptimizer) : `-si 0.5 / 0.25 / 0.125` pour trois densités, `-cc`
  (compression meshopt), `-tw` (textures WebP) ; glTF-Transform : `inspect`, `optimize`, `draco`, `resize`.
Contrôles avant de livrer : triangles mesurés par densité, poids du .glb (rapport_web_glb), textures en puissance de
2, aucune normale inversée, échelle réelle (1 unité = 1 m), pied du personnage à l'origine.
