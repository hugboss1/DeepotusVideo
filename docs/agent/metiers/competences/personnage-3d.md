## Compétence : personnage 3D de bout en bout

La chaîne d'un personnage, dans l'ordre — un contrôle à chaque étape, jamais l'étape suivante sur un défaut connu :
1. **Fiche** : partir de l'entité de la bible des Chapitres (Atelier Chapitre) : silhouette, tenue, palette, 3 mots
   de style. Une image de face en pose A, fond neutre, membres écartés du corps (le rig en dépend).
2. **Image → 3D** dans le Studio 3D (moteur choisi d'après le comparatif ; Tripo et Meshy riggent un bipède).
3. **Contrôle** dans l'Établi : pièces flottantes, normales, trous ; triangles MESURÉS contre le budget du rôle.
4. **Topologie** : réduire en gardant les UV (décimation) pour un rendu ; des quads propres seulement s'il sera
   déformé de près (visage parlant).
5. **Rig** : bipède du moteur ou rig local ; tester trois poses extrêmes avant d'animer.
6. **Visage** : un personnage généré n'a pas de visage animable — l'animation faciale sculpte des clés DZ_
   (mâchoire, sourire, clignements) autour de repères ; la bouche étant peinte, elle « parle » par le menton.
7. **Export** : .glb pour le web et le Studio 3D, rapport de poids, densités (LOD) si plusieurs distances.
Garder la même fiche pour toutes les déclinaisons du personnage : c'est elle qui tient la ressemblance.
