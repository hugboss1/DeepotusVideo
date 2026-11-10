---
famille: hunyuan3d
natures: [modele3d]
ids: [hunyuan, hunyuan-local, hunyuan-3.1]
voies: [fal, local]
releve: 2026-11-09
source: scenario-3d (scenario-labs/skills, MIT) ; registres asset3d_service, moteurs3d_neufs, local3d_service, pricing (asset3d)
description: À utiliser quand on génère un modèle 3D avec Hunyuan3D (Tencent) : Hunyuan3D v2 par fal, Hunyuan 3D 3.1 Pro (image ou texte), Hunyuan3D 2.1 en local gratuit sur sa carte graphique (GPU, VRAM, LOCAL3D_URL) ; géométrie seule puis texture, PBR, budget de faces élevé, objet ou personnage depuis une seule image, modèle 3D sans dépense.
---
## Aperçu

Hunyuan3D reconstruit un maillage depuis **une seule** image ; Hunyuan 3D 3.1 sait aussi partir d'un texte.
Trois membres : v2 par fal, 3.1 Pro par fal (le plus réglable), et 2.1 en **local**, gratuit, servi par un service
GPU que l'utilisateur lance à côté de l'app (réglage `LOCAL3D_URL`). Aucun membre ne lit de vues multiples ni ne
pose un personnage. On les lance depuis Game Assets › 3D › Créer.

## Référence rapide

- [PROMPT] Image source : un sujet, centré, entier avec de la marge, fond uni, lumière égale sans ombre portée.
  Le membre ne voit qu'elle : les faces cachées sont inventées. Choisir l'angle qui montre le plus du sujet.
- [PROMPT] Créature à quatre pattes : à hauteur d'œil, de profil ou de trois quarts, toutes les pattes visibles et
  détachées du corps. Une vue de dessus cache le dessous et la hauteur.
- [PROMPT] Mode Texte (3.1 seulement) : une phrase anglaise, un objet, sa matière, sa forme, son style. Une image
  concept validée donne plus de contrôle.
- [CHOIX] Personnage à rigger : aucun membre n'a de paramètre de pose et l'écran refuse la T-pose ou l'A-pose.
  Fournir une image déjà en A-pose, bras écartés du torse.
- [CHOIX] Local (2.1) : gratuit et hors ligne, mais seulement si le service répond ; sinon la génération est
  refusée avant tout tir. La forme seule tient sur une carte moyenne ; la texture demande beaucoup plus de VRAM
  (README du modèle, relevé 2026-11). Sous ce seuil, le service rend une forme nue.
- [CHOIX] Local : le fond est retiré par le service ; l'image n'est envoyée à aucun fournisseur.
- [CHOIX] 3.1 : `generate_type` Geometry rend la forme seule (brouillon) ; Normal la rend texturée.
- [CHOIX] 3.1 : le budget de faces (`face_count`) part d'un plancher élevé. Pour un asset léger, générer puis
  réduire dans 3D Studio › Préparer (local, gratuit), ou prendre un autre membre qui vise le low-poly.
- [PIÈGE] 3.1 : PBR « au choix » (Membres) : le réglage `enable_pbr` est coupé par défaut. Le cocher dans la roue
  si les cartes PBR sont voulues.
- [COÛT] 3.1 : `enable_pbr` et un `face_count` fixé sont des suppléments, ajoutés au devis seulement s'ils sont
  posés. `enable_pbr` n'est pas compté avec Geometry.
- [COÛT] v2 : la géométrie seule coûte nettement moins que la version texturée (devis). Le brouillon se règle par
  la case Textures de l'ancien formulaire 3D ; Créer envoie toujours la texture pour v2.
- [COÛT] Brouillon d'abord : local gratuit ou Geometry, on juge la silhouette, puis le tir texturé.
- [MÉTHODE] Texture d'un brouillon validé : 3D Studio › Préparer › « Approuver la géométrie », puis l'écran Texture.
- [PIÈGE] Formats : v2 et 3.1 annoncent GLB et OBJ, le local GLB seul. Un autre format se convertit dans
  3D Studio › Exporter.
- [CHOIX] Pas encore dans l'app : seed et nombre d'étapes pour le local (l'app les fixe), texture seule d'un maillage
  existant par Hunyuan.

## Exemple

Brief : « une statue de gargouille pour mon décor, je veux d'abord voir la forme sans rien payer ».

Image : gargouille accroupie de trois quarts, ailes repliées, fond gris uni, lumière plate. Créer, mode Image,
Hunyuan3D 2.1 (local) : forme seule, gratuite. La silhouette convient ; même image, Hunyuan 3D 3.1, roue des
réglages : `generate_type` Normal, `enable_pbr` coché. Le devis montre le supplément PBR avant Générer.

Prompt de l'image concept, dans le générateur d'image :

```
A stone gargoyle crouching on a plinth, folded wings, three-quarter view at eye level, whole statue in frame with
margin, plain mid-grey background, soft even lighting, no cast shadow, no text.
```

## Erreurs fréquentes

- Lancer le local sans avoir démarré le service : refus immédiat, rien n'est payé, mais rien n'est fait.
- Attendre une texture du local sur une carte trop petite : la forme revient nue.
- Envoyer une vue de dessus : le dessous et l'épaisseur sortent faux.
- Fixer un `face_count` sans besoin : supplément payé pour un budget que le défaut tenait.
