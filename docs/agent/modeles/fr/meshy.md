---
famille: meshy
natures: [modele3d]
ids: [meshy-7.1]
voies: [fal]
releve: 2026-11-09
source: scenario-meshy, scenario-3d (scenario-labs/skills, MIT) ; registres moteurs3d_neufs, pose3d, pricing (asset3d)
description: À utiliser quand on génère un modèle 3D avec Meshy 7.1 par fal : image ou texte vers 3D, personnage à rigger en A-pose ou T-pose, topologie triangle ou quad, nombre de polygones cible, remaillage, symétrie, géométrie seule puis texture, PBR, résolution de géométrie, export GLB FBX OBJ USDZ ; à distinguer de la retexture et du rig Meshy du 3D Studio.
---
## Aperçu

Meshy 7.1 reconstruit un maillage depuis **une** image ou depuis un texte, par fal. Il pose un personnage en
T-pose ou en A-pose et règle sa topologie à la source (triangles ou quads, polygones cibles, remaillage, symétrie).
On le lance depuis Game Assets › 3D › Créer, réglages dans la roue. La retexture et le rig du 3D Studio passent par
la clé Meshy, hors de ce membre.

## Référence rapide

- [PROMPT] Image source : un sujet, centré, entier avec de la marge, fond uni, lumière égale sans ombre portée ni
  texte. Une seule image part : les faces cachées sont inventées.
- [PROMPT] Mode Texte : une phrase anglaise, un sujet, sa matière, sa silhouette, son style, et la pose s'il s'agit
  d'un personnage. Une image concept validée donne plus de contrôle.
- [PROMPT] Le champ « Sujet » de Créer ne part pas en mode Image : seule l'image compte.
- [CHOIX] Personnage à rigger : choisir A-pose ou T-pose dans Créer (l'A-pose donne en général un meilleur rig :
  bras à environ 45°, espace net entre membres et torse). Pour un objet, l'écran refuse la pose.
- [CHOIX] `topology` : triangle pour un moteur de jeu, quad pour retravailler le maillage dans un logiciel 3D.
  glTF ne stocke que des triangles : le GLB d'un tir quad arrive triangulé.
- [PIÈGE] `target_polycount` n'agit que pendant le remaillage (`should_remesh`, actif par défaut). Avec le
  remaillage coupé, l'app refuse le polycount plutôt que de le payer pour rien.
- [CHOIX] `should_remesh` coupé : maillage brut du modèle, plus dense. Le garder actif pour un budget de faces.
- [CHOIX] `symmetry_mode` : auto par défaut ; on pour un sujet symétrique (véhicule, armure), off pour un sujet
  asymétrique (pose de marche, objet tenu d'une main).
- [CHOIX] `geometry_resolution` : finesse de la forme. Monter seulement pour un objet à petits détails.
- [PIÈGE] PBR « au choix » (Membres) : `enable_pbr` est coupé par défaut. Le cocher pour avoir les cartes PBR.
- [CHOIX] `model_type` n'a qu'une valeur, standard : la topologie intelligente de Meshy est un autre service, absent
  de l'app.
- [COÛT] Brouillon d'abord : `should_texture` décoché dans la roue, le tir coûte moins (devis). On juge la
  silhouette, puis on relance texturé, ou on texture le maillage validé.
- [COÛT] Le prix des Membres est celui du tir texturé par défaut. Plusieurs images en Multi-images ou une quantité
  supérieure à un : un tir payé chacun.
- [MÉTHODE] Texture d'un brouillon validé : 3D Studio › Préparer › « Approuver la géométrie », puis l'écran Texture
  (retexture Meshy, facturée en crédits Meshy, clé Meshy exigée).
- [MÉTHODE] Rig : 3D Studio › Rig, sur le maillage approuvé. Le rig n'est pas fait par ce membre.
- [CHOIX] Pas encore dans l'app pour ce membre : vues multiples, image de texture distincte, garder le maillage
  d'avant remaillage, hauteur réelle en mètres.

## Exemple

Brief : « un chevalier en armure pour mon jeu, à rigger et animer ensuite ».

Image : le chevalier validé, de face, corps entier, en A-pose, fond gris uni, lumière plate. Créer, mode Image,
Meshy 7.1, pose A-pose. Roue des réglages : `topology` triangle, `target_polycount` à un budget de personnage de
jeu, `should_remesh` actif, `symmetry_mode` on, `should_texture` décoché pour le brouillon.

Le brouillon validé dans Préparer, la texture se fait dans l'écran Texture avec l'image source comme référence, puis
le rig dans l'écran Rig.

Prompt de l'image concept, dans le générateur d'image :

```
A knight in full plate armor standing in an A-pose, arms straight and angled down away from the body, full body
head to feet, front view, plain mid-grey background, soft even lighting, no cast shadow, no text.
```

## Erreurs fréquentes

- Fixer `target_polycount` puis couper le remaillage : refusé avant envoi.
- Choisir quad pour un moteur de jeu temps réel : le GLB est triangulé de toute façon.
- Oublier `enable_pbr` et s'étonner d'un matériau sans cartes métal et rugosité.
- Confondre ce membre et la retexture du 3D Studio : deux clés, deux factures.
