---
famille: foley
natures: [sfx_video]
ids: [kling-v2a, hunyuan-foley, thinksound]
voies: [fal]
releve: 2026-11-09
source: scenario-audio (scenario-labs/skills, MIT) ; registre sfx_service (schémas fal relus le 12/10/2026)
description: À utiliser quand on fait un bruitage synchronisé (foley) depuis un clip vidéo du Montage avec Kling vidéo → son, Hunyuan Video Foley ou ThinkSound, qu'on veut une vidéo sonorisée ou une piste son calée sur l'image, qu'un bruitage vidéo est refusé (format, durée, description manquante) ou qu'une musique de fond inattendue apparaît.
---
## Aperçu

Trois modèles qui écoutent l'image d'un clip et en tirent le bruitage : pas, chocs, frottements, ambiance, calés
sur ce qui bouge. **Kling vidéo → son** rend une piste son seule. **Hunyuan Video Foley** et **ThinkSound** rendent
la **vidéo sonorisée** : l'app la range dans la Bibliothèque (Rendus) et en extrait la piste son, rangée dans les
sons. Écran unique : Montage, clip vidéo sélectionné dans la timeline, tiroir Sons › Générer › « Depuis la vidéo »,
sélecteur « Modèle ». La description vient du champ « Décrire le son » du même onglet.

## Référence rapide

- [PROMPT] L'image décide **quand** chaque son arrive ; la description dit **ce qu'il est**. Nommer les sources
  visibles et leur matière (« leather boots on wet cobblestones »), pas l'action déjà montrée.
- [PROMPT] Nommer les sons en positif. Pour une piste sans musique, décrire seulement les bruits ; ne pas écrire
  « no music ».
- [PIÈGE] Kling vidéo → son et Hunyuan Video Foley exigent une description : sans elle, l'app refuse avant tout
  tir (« Décrivez d'abord le son voulu »). ThinkSound s'en passe.
- [PIÈGE] Kling vidéo → son n'accepte qu'un clip `.mp4` ou `.mov` dans une plage de durée courte ; hors de là, le
  refus nomme la plage, avant tout tir. Sa description est courte : le refus donne la limite, l'app ne la coupe
  jamais.
- [CHOIX] Kling vidéo → son : l'app coupe sa musique de fond (sans cela, le fournisseur en ajoute une par défaut).
  On n'obtient que le bruitage, à poser sous le clip d'origine.
- [CHOIX] Piste son seule, image d'origine intacte : Kling vidéo → son. Vidéo sonorisée prête à poser : Hunyuan
  Video Foley ou ThinkSound.
- [CHOIX] Aucune case « Garder la voix » : rien ne demande à ces modèles de garder la parole d'un plan dialogué
  (son sort exact est à confirmer). Bruiter de préférence un plan sans parole et mixer la voix au Montage.
- [MÉTHODE] Un plan à la fois. Plusieurs plans dans un même clip mélangent les ambiances ; couper le clip au plan
  utile avant.
- [MÉTHODE] Écouter le rendu en le regardant, aux moments de contact (pied au sol, objet posé) : un son en avance ou
  en retard se voit tout de suite.
- [MÉTHODE] Le bouton s'arme en deux clics : le premier montre le devis du serveur, le second tire.
- [COÛT] Kling vidéo → son : prix fixe par vidéo, quelle que soit sa durée dans la plage permise.
- [COÛT] Hunyuan Video Foley et ThinkSound sont « prix à mesurer » : chiffrés à zéro, facturés par fal, le plafond
  ne les freine pas. ThinkSound est facturé au temps de calcul, inconnu d'avance. Un seul essai court d'abord.
- [CHOIX] Kling vidéo → son est un modèle de bruitage ; il n'a rien à voir avec les générateurs vidéo Kling.
- [CHOIX] Pas encore dans l'app : musique de fond de Kling, mode ASMR de Kling, réglages propres de Hunyuan et
  de ThinkSound.

## Exemple

Brief : « mon plan de cuisine est muet : ail qui grésille, cuillère en bois qui racle la poêle ; je veux la vidéo
sonorisée ».

Réglages : Montage, le clip coupé au seul plan de la poêle, sélectionné ; tiroir Sons (B) › Générer, modèle
Hunyuan Video Foley. Dans « Décrire le son » :

```
garlic sizzling in hot olive oil in a steel pan, a wooden spoon scraping the pan bottom, quiet home kitchen
```

« Depuis la vidéo » : premier clic, le devis (prix à mesurer) ; second clic, le tir. La vidéo sonorisée arrive dans
la Bibliothèque (Rendus), sa piste dans les sons. Le grésillement est en retard sur la cuillère : relancer avec la
même description, ou essayer ThinkSound sur le même clip.

## Erreurs fréquentes

- Lancer Kling vidéo → son ou Hunyuan sans description : refus immédiat.
- Envoyer à Kling un `.webm` ou un clip trop long : refus ; convertir ou couper d'abord.
- Bruiter un clip de plusieurs plans d'un coup : les sons se mélangent d'un plan à l'autre.
- Se fier au devis à zéro de Hunyuan ou ThinkSound pour une série : le prix réel est facturé par fal.
