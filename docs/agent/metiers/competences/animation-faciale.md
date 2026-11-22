## Compétence : animation faciale (synchronisation labiale, expressions)

`visage_preparer` calcule, sans rien dépenser, l'animation d'une réplique : visèmes (formes de bouche A–H et repos X),
commandes du visage (noms ARKit : jawOpen, mouthSmileLeft, eyeBlinkLeft…), expressions, clignements.
La pose dans Blender est un geste de l'utilisateur : Scène Blender (Blender ouvert) ou arrière-plan sur un .blend /
.glb du dossier de données, ou `scripts/blender/animer_visage.py`. Trois cas, choisis tout seuls :
- **clés de forme** ARKit, visèmes Oculus / VRM : animées telles quelles (le plus fidèle) ;
- **os du visage** (personnages de Blender Studio, Rigify, Auto-Rig Pro) : mâchoire, coins des lèvres, paupières,
  sourcils trouvés par leur nom ; un os qui bouge à l'envers se corrige par un réglage d'os (gain −1) ;
- **personnage généré** : des clés DZ_ sont sculptées autour de repères (bouche, yeux) réglables.
Qualité : la meilleure synchro vient d'un minutage réel (JSON de Rhubarb Lip Sync sur la voix) ; à défaut, le texte
étiré sur la durée du WAV ; l'énergie du WAV ferme la bouche dans les silences. Une expression par intention, pas
plus de deux à la fois ; clignements toutes les 2 à 5 s. Pour une vidéo déjà tournée, la synchro labiale vidéo
(Kling, payante) reste l'autre voie.
