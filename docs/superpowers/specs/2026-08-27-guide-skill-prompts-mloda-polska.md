# Młoda Polska — Guide pédagogique et skill de prompts visuels
## Créer des illustrations inspirées du mouvement sans copier les œuvres

**But du document :** concevoir un skill de génération d’images qui aide à comprendre et réinterpréter les codes visuels de la Jeune Pologne (*Młoda Polska*, env. 1890–1918). Il sert à la fois de grammaire de prompt, d’outil d’analyse comparée et de guide de création.

**Principe directeur :** produire des images originales qui reprennent des caractéristiques générales de courants, de techniques et de préoccupations plastiques. Ne pas demander la copie, la reconstruction ou la variation minimale d’une œuvre identifiable ; ne pas imiter de manière servile la « signature » d’un artiste précis.

---

# 1. Carte du mouvement

## Une modernité polonaise plurielle

Młoda Polska est un modernisme polonais : il combine symbolisme, Art nouveau / Sécession, impressionnisme, postimpressionnisme, synthétisme, renouveau du folklore et arts décoratifs. Cracovie est l’un de ses foyers majeurs ; le mouvement traverse également la peinture, le vitrail, le théâtre, la littérature, le mobilier, le textile et l’architecture intérieure.

Pour un générateur d’images, il ne faut donc pas traiter « Młoda Polska » comme un filtre unique. Le bon modèle est une **bibliothèque de familles visuelles** : vitrail sacré moderniste, symbolisme allégorique, portrait atmosphérique, paysage dramatique, folklore décoratif, impressionnisme urbain, synthétisme et arts appliqués.

## Palette de familles

| Famille | Effet dominant | Référents historiques | Meilleure application générative |
|---|---|---|---|
| Vitrail Art nouveau sacré | Lumière intérieure, ligne et monumentalité | Stanisław Wyspiański, Józef Mehoffer | Chapelles fictives, fenêtres, affiches verticales, décors muraux |
| Symbolisme national et mythologique | Allégorie, rêve, tension existentielle | Jacek Malczewski, Wojciech Weiss | Scènes narratives, couvertures, concepts de jeu |
| Portrait atmosphérique | Silence, psychologie, demi-teintes | Olga Boznańska | Personnages, portraits éditoriaux, concept art intimiste |
| Folklore moderniste | Costume, rite, couleur décorative | Teodor Axentowicz, Włodzimierz Tetmajer | Scènes de village, mode, worldbuilding culturel |
| Paysage monumental | Météo, horizon, force de la terre | Ferdynand Ruszczyc | Environnements, matte paintings, couvertures |
| Paysage lumineux | Touche, saison, perception | Leon Wyczółkowski, Józef Pankiewicz | Environnements naturels, scènes urbaines, plein air |
| Synthétisme | Aplats, formes condensées, calme | Władysław Ślewiński | Affiches, décors de jeu, natures mortes, intérieurs |
| Arts décoratifs | Motifs, mobilier, textile, intégration | Wyspiański, Mehoffer, ateliers de Cracovie | UI décorative, ornements, vitraux, design d’objets |

---

# 2. Règles du skill

## Objectif : transférer des codes, pas reproduire

Le skill doit transformer une demande en prompt à partir de paramètres visuels observables : composition, matière, médium simulé, intensité de ligne, palette, traitement de la lumière, densité ornementale, symbolisme, époque évoquée et sujet.

À éviter dans les prompts :

- « reproduis [titre d’œuvre] »
- « copie exactement le tableau de… »
- « dans le style exact de [artiste] »
- « refaire la même composition avec un autre personnage »
- Toute demande qui vise à reconstituer une œuvre ou un personnage reconnaissable.

À privilégier :

- « vitrail Art nouveau polonais du tournant du XXe siècle »
- « symbolisme d’Europe centrale, allégorie nationale imaginaire »
- « portrait à la palette gris-vert, lumière diffuse et matière fondue »
- « paysage rural monumental sous un ciel chargé »
- « scène folklorique moderniste, motifs textiles et couleurs décoratives »

## Formule universelle de prompt

Utiliser ce modèle :

```text
[SUJET ORIGINAL], [ACTION / ÉTAT], dans une interprétation [FAMILLE VISUELLE],
composition [CADRAGE + STRUCTURE], palette [COULEURS], lumière [QUALITÉ],
traitement [LIGNE + MATIÈRE + TEXTURE], décor [MOTIFS / ENVIRONNEMENT],
ambiance [ÉMOTION], médium simulé [VITRAIL / PASTEL / HUILE / AFFICHE],
modernisme polonais de la fin du XIXe et du début du XXe siècle,
œuvre entièrement originale, sans reproduire de tableau existant, sans texte ni signature.
```

## Variables à exposer dans le skill

| Variable | Valeurs suggérées | Rôle |
|---|---|---|
| `sujet` | saint imaginaire, astronome, joueuse, villageois, jardin, créature mythique | Le contenu narratif original |
| `famille` | vitrail, symbolisme, portrait, folklore, paysage, synthétisme, décoratif | Le système visuel principal |
| `composition` | verticale axiale, frise, diagonale dramatique, portrait buste, horizon bas | La lisibilité de l’image |
| `palette` | cobalt-or, vert mousse, gris perle, ocre-rouge, bleu de Prusse | L’identité émotionnelle |
| `lumiere` | transmise, voilée, crépusculaire, solaire, tempétueuse | Le moteur atmosphérique |
| `motifs` | iris, pavots, blés, rubans, insectes, vitraux géométriques, textiles | Le vocabulaire décoratif |
| `intensite` | 1 à 5 | Quantité de symbolisme, d’ornement et de dramatisation |
| `usage` | affiche, carte, environnement de jeu, couverture, vitrail fictif, étude pédagogique | Ajuste le format et la densité |

---

# 3. Les grandes grammaires visuelles

## A. Vitrail sacré moderniste
### Références pédagogiques : Wyspiański et Mehoffer

Cette famille s’appuie sur des formes cernées par une ligne sombre, sur des champs de couleur saturée et sur une lumière qui semble venir de l’intérieur de l’image. Le sujet peut être religieux, mythologique, cosmique ou totalement fictif ; la structure doit rester lisible de loin, comme une fenêtre monumentale.

### Codes formels

- Format vertical ou ogival, composition frontale et ascendante.
- Contours noirs / brun foncé, épais mais souples.
- Couleurs franches : bleu cobalt, rouge rubis, vert émeraude, jaune doré, violet profond.
- Motifs naturalistes stylisés : iris, lys, tournesols, feuillages, nuages, rayons, oiseaux.
- Fragments de verre irréguliers, plomb visible, contrastes conçus pour la lumière traversante.
- Hiérarchie simple : figure centrale, halo ou énergie rayonnante, bordure ornementale.

### Prompt modèle

```text
Vitrail monumental pour une chapelle imaginaire, une astronome mystique élève une sphère céleste,
composition verticale dans une baie ogivale, figure frontale entourée d’iris et de constellations,
verre cobalt, rouge rubis, jaune doré et vert émeraude, lumière traversante très intense,
contours de plomb sombres et sinueux, motifs floraux Art nouveau, rayons solaires géométriques,
modernisme polonais fin XIXe-début XXe siècle, image originale, sans texte, sans signature.
```

### Négatif / garde-fous

```text
Ne pas reproduire une fenêtre connue, ne pas utiliser de personnage religieux reconnaissable,
ne pas inclure de logos, de texte lisible, de photo réaliste, de 3D plastique, ni d’esthétique néon cyberpunk.
```

### Exercice pédagogique

Créer trois versions du même sujet :

1. Intensité ornementale faible : figure, halo, deux motifs floraux.
2. Intensité moyenne : bordure, végétaux, fragments de verre variés.
3. Intensité élevée : décor cosmique, végétal, héraldique et architectural intégré.

Comparer la lisibilité à distance, la hiérarchie des masses colorées et l’équilibre entre narration et ornement.

---

## B. Symbolisme allégorique
### Références pédagogiques : Malczewski et Weiss

Le symbolisme de Młoda Polska traduit des problèmes historiques, politiques, spirituels ou intimes en scènes irréelles. Pour générer une image pertinente, ne pas partir d’un « monstre décoratif » : commencer par une idée abstraite – mémoire, exil, désir de liberté, création, vieillissement, conflit intérieur – et lui donner une forme narrative.

### Codes formels

- Personnage pensif ou isolé, souvent placé face à une apparition.
- Mélange du quotidien et du mythique : atelier, champ, gare, forêt, ruine, chambre ; faune, ange, muse, figure masquée, messagère.
- Perspective légèrement instable ou espace théâtral.
- Couleurs terreuses et profondes : brun, vert sombre, bleu nuit, rouge oxydé, ivoire.
- Gestes suspendus, regards absents, densité émotionnelle.
- Accessoires comme symboles : échelle, masque, lettre, épée, fleur fanée, miroir, oiseau, instrument.

### Prompt modèle

```text
Allégorie symboliste originale de la mémoire collective : une cartographe solitaire dans un atelier ancien,
observe une grande carte déchirée tandis que trois figures mythiques traversent une porte ouverte,
composition théâtrale avec diagonale ascendante, palette brun terre, vert profond, bleu nuit et rouge oxydé,
lumière de fin d’orage, huile sur toile à texture visible, gestes suspendus et regards énigmatiques,
symbolisme d’Europe centrale vers 1900, modernisme polonais, œuvre originale, sans texte ni signature.
```

### Questions d’analyse

- Quelle idée invisible l’image cherche-t-elle à rendre visible ?
- Quel objet porte le symbole principal ?
- La scène est-elle une histoire, un rêve ou une vision intérieure ?
- Où se trouve la tension : dans le regard, la météo, les gestes ou les oppositions de couleurs ?

---

## C. Portrait atmosphérique
### Référence pédagogique : Olga Boznańska

Cette famille repose sur la retenue. Elle évite le portrait « héroïque » ou très net : l’image est une présence psychologique. Le modèle paraît proche mais difficile à saisir, comme si l’air, le silence et la matière de la peinture enveloppaient son visage.

### Codes formels

- Cadrage buste ou trois-quarts, pose calme, regard direct ou légèrement détourné.
- Fond indécis : intérieur sombre, rideau, fenêtre froide, mur texturé, jardin flou.
- Palette réduite : gris perle, vert de cendre, bleu ardoise, brun violet, rose éteint.
- Bords fondus, détails concentrés autour des yeux et des mains.
- Lumière diffuse, sans contraste dur ; texture de peinture granuleuse ou brossée.
- Émotion : distance, fragilité, réserve, pensée, mélancolie calme.

### Prompt modèle

```text
Portrait original d’une archiviste dans son atelier, cadrage buste de trois-quarts,
visage calme et regard légèrement détourné, fond de bibliothèque flou aux verts gris et bleus ardoise,
lumière froide venant d’une fenêtre latérale, contours fondus, matière d’huile granuleuse,
palette sourde gris perle, brun violet, vert de cendre, psychologie silencieuse,
portrait moderniste polonais du tournant du XXe siècle, œuvre originale, sans texte ni signature.
```

### Erreurs fréquentes

- Trop de netteté photographique : réduire les détails hors visage.
- Palette trop saturée : limiter à trois ou quatre familles de tons.
- Décor trop descriptif : faire du fond une atmosphère, pas une illustration narrative.
- Expression caricaturale : préférer un état d’attention ou de retrait.

---

## D. Folklore moderniste
### Références pédagogiques : Axentowicz et Tetmajer

La Jeune Pologne utilise les traditions rurales, les montagnes et les costumes populaires comme matériaux de modernité. Le prompt doit éviter l’imagerie touristique : construire une scène avec un rite, un geste, une texture textile ou un rapport social précis.

### Codes formels

- Costumes structurés par broderies, rubans, perles, châles, coiffes et gilets.
- Palette chaude et claire : rouge carmin, blanc cassé, noir velours, bleu outremer, ocre, vert herbe.
- Gestes rituels : danse, départ, bénédiction, marché, cueillette, veillée, mariage fictif.
- Alternance entre portraits élégants et scènes collectives.
- Décor rural traité comme une scène : arbres, maison en bois, montagne, champs, fleurs.
- Simplification décorative des tissus et des silhouettes.

### Prompt modèle

```text
Scène folklorique moderniste originale dans un village de montagne fictif,
une jeune musicienne en manteau brodé traverse une place au crépuscule pendant une fête des récoltes,
composition en frise avec rubans, textiles et bouquets stylisés, rouge carmin, noir velours,
blanc cassé, bleu profond et ocre, lumière dorée et brume légère,
peinture décorative d’Europe centrale vers 1900, élégance Art nouveau, image originale, sans texte ni signature.
```

### Exercice pédagogique

Générer un même sujet dans deux modes :

- **Portrait élégant** : une seule personne, fond simplifié, textile très détaillé.
- **Scène communautaire** : plusieurs figures, rythme de frise, décor et rite plus importants.

Comparer le rôle de l’ornement, de la narration et de la couleur.

---

## E. Paysage monumental et dramatique
### Référence pédagogique : Ferdynand Ruszczyc

Le paysage devient un protagoniste. L’être humain, s’il existe, est petit face au relief, au vent et au ciel. Une bonne génération doit donner au terrain un poids matériel et au climat une fonction émotionnelle.

### Codes formels

- Horizon bas et ciel occupant plus de la moitié de l’image.
- Grand arbre, grange, moulin, chemin ou attelage comme point d’ancrage.
- Nuages massifs, lumière d’orage, vent visible dans les herbes ou les branches.
- Terre brun rouge, vert sombre, bleu gris, blanc de nuage, reflets froids.
- Personnages secondaires, presque absorbés par le paysage.
- Sens de l’effort, du cycle des saisons, de la solitude ou de la persistance.

### Prompt modèle

```text
Paysage rural symboliste original : une fermière et deux bœufs labourent une pente sombre,
sous un immense ciel d’orage éclairé par une trouée blanche, horizon très bas,
composition monumentale, terre brun rouge et vert profond, nuages bleu gris et blancs lourds,
huile sur toile expressive, vent dans les herbes, sentiment de persévérance et de solitude,
modernisme polonais vers 1900, œuvre originale, sans texte ni signature.
```

### Réglage de composition

- `horizon = 20–35 %` pour maximiser l’effet de ciel.
- `sujet_humain = 5–15 %` de la hauteur d’image pour maintenir l’échelle monumentale.
- `dynamique_meteo = 4–5 / 5` pour une scène dramatique.

---

## F. Impressionnisme urbain et plein air
### Références pédagogiques : Pankiewicz et Wyczółkowski

Ici, l’intérêt principal est la lumière telle qu’elle transforme les choses. Les personnages, marchés, rues, champs et jardins existent surtout comme prétextes à une vibration de touches colorées, à une saison ou à une heure du jour.

### Codes formels

- Touche visible et légère, non lissée.
- Couleurs modulées par la lumière : ombres bleues, jaunes chauds, gris colorés.
- Sujet ordinaire : marché, promenade, quai, café, jardin, récolte, rue pluvieuse.
- Cadrage pris sur le vif, parfois légèrement décentré.
- Air, poussière, brume ou soleil comme sujet réel de l’image.
- Peu de symboles explicites ; priorité à la perception.

### Prompt modèle

```text
Scène de plein air originale : marché aux fleurs dans une ville d’Europe centrale imaginaire,
passants sous des auvents clairs après une pluie de printemps, cadrage oblique pris sur le vif,
touches d’huile visibles, ombres bleu lavande, roses, jaunes pâles, verts frais et gris lumineux,
atmosphère humide et vibrante, impressionnisme polonais autour de 1900,
œuvre originale, sans texte ni signature.
```

### Test pédagogique

Utiliser le même décor à trois heures : matin froid, midi solaire, soir pluvieux. L’objectif est de constater que la lumière change davantage l’identité de l’image que le sujet lui-même.

---

## G. Synthétisme et formes condensées
### Référence pédagogique : Władysław Ślewiński

Le synthétisme privilégie les masses, les aplats et la stabilité de la composition. Il convient parfaitement à la création d’affiches, de cartes, de scènes de jeu, de décors et de natures mortes contemporaines inspirées d’une modernité de 1900.

### Codes formels

- Trois à six grandes masses dominantes, peu de détails dispersés.
- Contours souples ou couleurs nettement séparées.
- Palette limitée, souvent sourde mais franche.
- Motifs simples : chaise, fenêtre, chat, vase, colline, mer, barque, figure assise.
- Espace aplati, profondeur réduite.
- Atmosphère méditative, intime ou silencieuse.

### Prompt modèle

```text
Intérieur synthétiste original : une lectrice endormie près d’une fenêtre ouverte,
forme compacte sur un canapé vert profond, un chat noir au premier plan, vase ocre sur une table,
composition simplifiée en grands aplats, contours souples, palette vert mousse, noir, ocre et rose éteint,
profondeur réduite, huile mate, modernisme européen vers 1900,
œuvre originale, sans texte ni signature.
```

---

# 4. Atlas des référents

## Stanisław Wyspiański (1869–1907)

### À étudier

- Vitraux et polychromies de l’église Saint-François-d’Assise de Cracovie.
- Projet monumental **Dieu le Père – « Que la lumière soit ! »**.
- Projet **Apollo : système solaire de Copernic**.
- Pastels de portraits, paysages de Cracovie et conceptions de mobilier.
- Théâtre : *Les Noces*, *La Libération*, *Akropolis*.

### Codes transférables

- Ligne décorative énergique.
- Végétal stylisé et motifs floraux.
- Lumière colorée, contraste de vitrail.
- Figure centrale structurée par un cadre architectural.
- Art total : image, décor, objet et espace pensés ensemble.

### Prompt d’entraînement

```text
Panneau décoratif original pour une bibliothèque civique imaginaire,
une figure allégorique de la connaissance tenant une lampe entourée de fleurs stylisées et de motifs stellaires,
structure verticale, contours sombres fluides, cobalt, ambre, rubis et vert émeraude,
verre coloré et décoration Art nouveau, modernisme polonais fin XIXe-début XXe siècle,
œuvre originale, sans texte ni signature.
```

## Józef Mehoffer (1869–1946)

### À étudier

- **Étrange jardin** (*Dziwny ogród*, 1903).
- Vitraux de la collégiale Saint-Nicolas de Fribourg.
- Cartons de vitraux, affiches, décors et projets d’arts appliqués.
- Vitraux pour la cathédrale du Wawel réalisés à partir de ses dessins.

### Codes transférables

- Décor profus, presque joaillier.
- Jardin comme espace symbolique et merveilleux.
- Tissus, fleurs, insectes et fruits comme signes visuels.
- Personnages paisibles au milieu d’un environnement très actif.
- Couleurs riches, saturées, souvent équilibrées par des zones de repos.

### Prompt d’entraînement

```text
Jardin symboliste original au début de l’été, une famille imaginaire lit sous des arbres fruitiers,
une libellule surdimensionnée traverse la lumière au-dessus d’eux,
feuillages, rubans floraux et textiles décoratifs denses, bleu outremer, vert profond, rouge et or,
composition lumineuse et foisonnante, Art nouveau d’Europe centrale vers 1900,
œuvre originale, sans texte ni signature.
```

## Jacek Malczewski (1854–1929)

### À étudier

- **Mélancolie** (*Melancholia*, 1890–1894).
- **Le Cercle vicieux** (*Błędne koło*, 1895–1897).
- **Veillée de Noël en Sibérie** (1892).
- Séries et variations autour de Thanatos, des muses, des faunes et de l’autoportrait.

### Codes transférables

- Allégorie complexe, personnages réels et mythiques cohabitant.
- Récit ouvert, sans solution immédiate.
- Théâtralité, symboles matériels et tension historique.
- Figure humaine placée entre mémoire, imaginaire et contrainte.

### Prompt d’entraînement

```text
Scène symboliste originale : un jeune relieur travaille dans une imprimerie abandonnée,
une muse masquée, un faune discret et une silhouette vêtue de blanc apparaissent parmi les feuilles volantes,
composition dramatique, huile texturée, brun terre, bleu profond, ivoire et rouge assourdi,
allégorie de la mémoire et de la création, modernisme d’Europe centrale autour de 1900,
œuvre originale, sans texte ni signature.
```

## Olga Boznańska (1865–1940)

### À étudier

- **Fille aux chrysanthèmes** (1894).
- Portraits de femmes, d’enfants et autoportraits.
- Intérieurs, natures mortes et portraits réalisés entre Munich et Paris.

### Codes transférables

- Sujet proche et fonds atmosphériques.
- Gris colorés, verts de cendre, bleus sourds.
- Contours effacés, présence psychologique.
- Détails concentrés dans le regard, les mains ou un objet discret.

### Prompt d’entraînement

```text
Portrait original d’un jeune violoniste assis dans un salon calme,
regard absent, main posée sur l’étui de son instrument, fond vert gris fondu,
lumière froide et diffuse, touches d’huile visibles, gris perle, bleu ardoise, brun violet,
ambiance retenue et psychologique, portrait moderniste polonais vers 1900,
œuvre originale, sans texte ni signature.
```

## Leon Wyczółkowski (1852–1936)

### À étudier

- **Labourage en Ukraine** (*Orka na Ukrainie*).
- Paysages de montagne et séries de plein air.
- Lithographies et recherches tardives sur la matière graphique.

### Codes transférables

- Lumière saisonnière, attention à la matière du sol.
- Travail rural, paysages ouverts et couleurs atmosphériques.
- Alternance entre observation directe et stylisation colorée.

### Prompt d’entraînement

```text
Paysage de plein air original : récolte dans une vallée de montagne fictive,
ouvriers très petits dans un champ lumineux, attelage et meules au loin,
touches visibles, bleu pâle, ocre, vert frais et blanc chaud, air d’été légèrement poussiéreux,
peinture de plein air polonaise du tournant du XXe siècle, œuvre originale, sans texte ni signature.
```

## Józef Pankiewicz (1866–1940)

### À étudier

- **Marché aux fleurs devant l’église Sainte-Marie à Cracovie** (1889).
- Portrait d’une jeune fille en robe rouge (Józefa Oderfeld, 1897).
- Paysages du Midi et travaux postimpressionnistes ultérieurs.

### Codes transférables

- Vie urbaine ou quotidienne sous une lumière changeante.
- Touche impressionniste et gris colorés.
- Cadrage vivant, presque photographique mais peint.
- Relations subtiles entre tons chauds et ombres froides.

### Prompt d’entraînement

```text
Place urbaine originale après la pluie, vendeuses de fleurs sous des parasols clairs,
façades anciennes floues à l’arrière-plan, passants portant des paniers,
composition vive prise sur le vif, rose pâle, jaune crème, vert frais, ombres bleu lavande,
touches impressionnistes visibles, Pologne moderniste vers 1900, œuvre originale, sans texte ni signature.
```

## Władysław Ślewiński (1856–1918)

### À étudier

- **Femme endormie avec un chat** (1896).
- Paysages bretons, natures mortes et paysages polonais.
- Relations avec Pont-Aven et le synthétisme.

### Codes transférables

- Formes simplifiées et aplats de couleur.
- Intérieur tranquille, personnage immobile, nature morte réduite à l’essentiel.
- Couleurs peu nombreuses, composition stable.

### Prompt d’entraînement

```text
Nature morte synthétiste originale : trois poires, un bol bleu et une branche de romarin sur une nappe ocre,
composition frontale, grands aplats de couleur, contours doux, vert mousse, ocre, bleu profond et crème,
peinture mate, espace aplati et silencieux, modernisme vers 1900, œuvre originale, sans texte ni signature.
```

## Teodor Axentowicz (1859–1938)

### À étudier

- **La Rousse** (*Ruda*, 1899).
- Portraits féminins au pastel.
- Scènes et costumes houtsouls, sujets folkloriques des Carpates.

### Codes transférables

- Profil ou trois-quarts élégant.
- Tissu et chevelure comme rythme décoratif.
- Pastel velouté, teintes chaudes contre fonds froids.
- Folklore comme langage de prestige, non comme caricature.

### Prompt d’entraînement

```text
Portrait pastel original d’une danseuse de montagne fictive,
profil calme, chevelure cuivrée et foulard brodé, fond bleu vert très doux,
rouge carmin, ivoire, cuivre et bleu de Prusse, matière pastel veloutée,
élégance folklorique moderniste d’Europe centrale vers 1900,
œuvre originale, sans texte ni signature.
```

## Włodzimierz Tetmajer (1861–1923)

### À étudier

- Scènes rurales de Bronowice et de Petite-Pologne.
- Noces paysannes, costumes, rites et paysages agricoles.
- Polychromies et décorations associées au Wawel.

### Codes transférables

- Communauté paysanne et scène rituelle.
- Costumes, lumière chaude, narration collective.
- Végétation, architecture de bois et éléments domestiques.

### Prompt d’entraînement

```text
Noces rurales fictives à l’aube, groupe de villageois devant une maison en bois décorée de fleurs,
rythme de frise, costumes brodés, paniers, rubans et instruments, rouge, blanc, vert et ocre,
lumière chaude et peinture décorative, modernisme polonais vers 1900,
œuvre originale, sans texte ni signature.
```

## Ferdynand Ruszczyc (1870–1936)

### À étudier

- **La Terre** (*Ziemia*, 1898).
- **Néc Mergitur** (1904–1905).
- **Moulin d’hiver** et paysages nocturnes.

### Codes transférables

- Paysage comme drame émotionnel.
- Ciel massif et terrain lourd.
- Architecture rurale ou arbre solitaire comme symbole.

### Prompt d’entraînement

```text
Paysage symboliste original : moulin abandonné au bord d’un champ détrempé,
un seul corbeau passe devant un ciel énorme de nuages blancs et bleu gris,
horizon bas, terre brune et herbes vert sombre, lumière froide après l’orage,
composition monumentale et mélancolique, huile sur toile vers 1900,
œuvre originale, sans texte ni signature.
```

## Wojciech Weiss (1875–1950)

### À étudier

- **Mélancolique** (*Melancholik*, 1898).
- **Démon** (1904).
- Peintures de figures et évolution vers un chromatisme plus lumineux.

### Codes transférables

- Psychologie exacerbée et fond expressif.
- Figure moderne, souvent isolée.
- Couleurs terreuses traversées par un accent vif, par exemple une fleur jaune ou un rouge sombre.

### Prompt d’entraînement

```text
Portrait symboliste original d’un étudiant assis dans une chambre étroite,
regard vers le sol, une fleur jaune épinglée à sa veste sombre,
fond tourbillonnant brun rouge et vert olive, lumière intérieure faible,
huile expressive, intériorité fin-de-siècle, modernisme polonais vers 1900,
œuvre originale, sans texte ni signature.
```

## Jan Stanisławski (1860–1907)

### À étudier

- Petits paysages d’Ukraine, jardins, arbres, champs et meules.
- Son rôle de pédagogue dans le renouvellement du paysage polonais.

### Codes transférables

- Petit format mental : concentration, économie, densité.
- Nature organisée en rythmes de couleur.
- Peu de narration, beaucoup de structure et de sensation.

### Prompt d’entraînement

```text
Petit paysage moderniste original : un vieux poirier au bord d’un champ après une pluie d’été,
composition très condensée, grandes masses vertes et terre ocre, ciel bleu gris,
touches visibles mais contrôlées, format intime, peinture de paysage polonais vers 1900,
œuvre originale, sans texte ni signature.
```

## Jan Matejko (1838–1893) — Précurseur

### À étudier

- **Stańczyk** (1862).
- **Rejtan ou La chute de la Pologne** (1866).
- **La Bataille de Grunwald** (1878).
- Polychromies de Sainte-Marie à Cracovie.

### Codes transférables

Matejko sert surtout à comprendre le fond historique et national sur lequel la Jeune Pologne construit ses symboles. Pour la génération d’images, retenir la dramaturgie historique, les tissus, les gestes et les scènes collectives ; éviter de recréer des batailles ou compositions précises existantes.

### Prompt d’entraînement

```text
Scène historique fictive dans une salle de conseil médiévale imaginaire,
une diplomate seule tient une lettre scellée pendant qu’un groupe de nobles débat à l’arrière-plan,
compositions de gestes expressifs, bannières et tissus riches, lumière dramatique de chandelles,
peinture d’histoire polonaise du XIXe siècle comme contexte, œuvre originale, sans texte ni signature.
```

---

# 5. Générateur de prompts : pseudo-algorithme

## Entrées utilisateur

```yaml
sujet: "une gardienne de phare dans une ville lacustre imaginaire"
famille: "vitrail sacré moderniste"
intensite_ornement: 4
intensite_symbolisme: 3
palette: "cobalt, ambre, rouge rubis, vert émeraude"
format: "vertical 2:3"
usage: "affiche pédagogique"
```

## Transformation

```text
1. Identifier la famille visuelle dominante.
2. Sélectionner 3 à 6 codes formels issus de cette famille.
3. Ajouter un sujet et une narration entièrement originaux.
4. Définir cadrage, hiérarchie et qualité de lumière.
5. Limiter la palette à 3–5 couleurs majeures.
6. Ajouter médium et texture simulés.
7. Ajouter les garde-fous : originalité, sans texte, sans signature, sans reproduction d’œuvre existante.
8. Générer une version longue, une version courte et une variante négative.
```

## Sortie attendue

```text
Affiche verticale originale représentant une gardienne de phare dans une ville lacustre imaginaire,
composition axiale dans une baie ogivale, figure centrale portant une lanterne,
cerclée de roseaux, d’étoiles et de vagues stylisées, fragments de verre cobalt, ambre,
rouge rubis et vert émeraude, lumière traversante intense, contours de plomb fluides,
motifs Art nouveau d’Europe centrale vers 1900, haute lisibilité à distance,
œuvre entièrement originale, sans texte, sans signature, sans reproduction d’œuvre existante.
```

---

# 6. Matrice de mélange contrôlé

## Combinaisons cohérentes

| Base | Ajout limité | Résultat attendu |
|---|---|---|
| Vitrail Wyspiański | Paysage Ruszczyc | Vitrail de tempête, ciel monumental, plantes stylisées |
| Ornement Mehoffer | Folklore Axentowicz | Scène rituelle raffinée, textiles et jardin symbolique |
| Symbolisme Malczewski | Portrait Boznańska | Allégorie intime, peu de figures, tension psychologique |
| Impressionnisme Pankiewicz | Paysage Wyczółkowski | Plein air lumineux, marché ou récolte, lumière saisonnière |
| Synthétisme Ślewiński | Décoratif cracovien | Affiche ou intérieur à grands aplats et motifs floraux |
| Weiss | Ruszczyc | Personnage mélancolique dans un paysage orageux |

## Mélanges à traiter avec prudence

- Vitrail saturé + portrait de demi-teintes : choisir une dominante, sinon l’image devient incohérente.
- Impressionnisme léger + allégorie complexe : réduire le nombre de symboles.
- Folklore détaillé + synthétisme : simplifier les costumes à quelques motifs structurants.
- Décoratif très dense + paysage dramatique : réserver l’ornement au cadre ou aux bordures.

---

# 7. Prompts prêts à l’emploi

## Vitrail — connaissance et cosmos

```text
Vitrail Art nouveau original dans une fenêtre ogivale, une cartographe céleste trace des routes parmi les constellations,
figure centrale en robe bleu cobalt, iris stylisés, astrolabe, croissant de lune et rayons dorés,
verre rubis, ambre, émeraude et violet, contours de plomb sombres et souples,
lumière traversante, modernisme polonais fin XIXe-début XXe siècle,
œuvre originale, sans texte, sans signature.
```

## Symbolisme — exil et mémoire

```text
Allégorie symboliste originale : un voyageur assis sur une malle ancienne regarde une ville lointaine,
une figure ailée tient une clef rouillée, tandis qu’un animal imaginaire traverse un champ de coquelicots,
huile sur toile texturée, vert sombre, brun, bleu nuit, rouge assourdi et ivoire,
composition théâtrale, atmosphère de rêve et de mémoire, Europe centrale vers 1900,
sans texte, sans signature, sans reproduction d’œuvre existante.
```

## Portrait — silence et présence

```text
Portrait original d’une botaniste âgée devant une serre embuée,
cadrage buste, visage calme, main tenant un carnet fermé, fond vert gris et bleu ardoise,
lumière diffuse, contours fondus, matière granuleuse d’huile, quelques détails précis dans les yeux,
portrait moderniste polonais vers 1900, palette sourde et introspective,
sans texte, sans signature.
```

## Folklore — scène de rite fictif

```text
Illustration originale d’une procession nocturne dans un village imaginaire des Carpates,
figures en costumes brodés portent des lanternes et des gerbes de blé,
composition en frise, rouges carmin, blancs cassés, noirs velours, verts et ors,
motifs de rubans et de fleurs stylisés, élégance Art nouveau, peinture décorative vers 1900,
sans texte, sans signature.
```

## Paysage — nature monumentale

```text
Paysage original de haute plaine après l’orage, petit attelage sur une route de terre,
un immense ciel de nuages blancs et bleu gris occupe les deux tiers de l’image,
herbes pliées par le vent, grange solitaire, terre brun rouge et vert profond,
huile expressive, paysage symboliste polonais vers 1900,
sans texte, sans signature.
```

## Impressionnisme — ville et lumière

```text
Scène originale dans un jardin public à l’heure dorée, lecteurs et enfants près d’un kiosque,
cadrage spontané, touches d’huile visibles, ombres bleu lavande, jaunes chauds, roses pâles et verts frais,
lumière vibrante, impressionnisme polonais de plein air vers 1900,
sans texte, sans signature.
```

## Synthétisme — intérieur calme

```text
Intérieur original avec une musicienne assoupie sur un fauteuil, chat noir et vase de fleurs sauvages,
quatre grandes masses colorées, profondeur réduite, vert mousse, ocre, bleu nuit et rose sourd,
contours souples, huile mate, composition stable et silencieuse,
synthétisme européen vers 1900, sans texte, sans signature.
```

---

# 8. Fiche pédagogique par image générée

Utiliser cette fiche avec chaque image afin de transformer la génération en apprentissage.

```markdown
## Titre de l’image

- Sujet original :
- Famille visuelle dominante :
- Référents pédagogiques :
- Médium simulé :
- Composition :
- Palette :
- Source de lumière :
- Motifs décoratifs :
- Symbole principal :
- Émotion recherchée :
- Niveau d’ornement (1–5) :
- Niveau de narration (1–5) :
- Ce qui évoque Młoda Polska :
- Ce qui différencie l’image des œuvres historiques :
- Ajustement à tester ensuite :
```

## Questions de critique

- L’image est-elle lisible avant que ses détails soient examinés ?
- Le choix de la lumière soutient-il la famille visuelle ?
- La palette est-elle assez limitée pour former un langage cohérent ?
- Le décor enrichit-il le sujet ou le masque-t-il ?
- Le symbole peut-il être compris sans explication exhaustive ?
- Le prompt produit-il une création autonome plutôt qu’une citation visuelle trop proche d’une œuvre précise ?

---

# 9. Exercices progressifs

## Exercice 1 — Même sujet, sept familles

Sujet imposé : **« une messagère traverse une ville après la pluie »**.

Générer sept images, une par famille : vitrail, symbolisme, portrait, folklore, paysage dramatique, impressionnisme, synthétisme. L’objectif est d’isoler ce que change réellement une grammaire visuelle : structure, lumière, palette, symboles et degré de détail.

## Exercice 2 — Palette avant sujet

Choisir l’une des palettes suivantes et imaginer un sujet après coup :

- Cobalt, rubis, émeraude, ambre : vitrail et sacré moderniste.
- Gris perle, vert de cendre, bleu ardoise : portrait atmosphérique.
- Brun rouge, bleu gris, blanc lourd, vert sombre : paysage dramatique.
- Rouge carmin, noir velours, ivoire, ocre : folklore décoratif.
- Rose pâle, jaune crème, ombre lavande, vert frais : impressionnisme de plein air.

## Exercice 3 — De l’ornement au récit

Créer une image de jardin selon trois niveaux :

1. Jardin uniquement décoratif.
2. Jardin avec personnage et action discrète.
3. Jardin devenant une allégorie explicite par un symbole unique (insecte, porte, clef, miroir ou étoile).

## Exercice 4 — Art total

Partir d’un motif original, par exemple « iris nocturne et astrolabe ». Générer ensuite :

- Un vitrail.
- Un papier peint.
- Une couverture de livre.
- Une chaise ou un panneau de mobilier.
- Une affiche.

Analyser comment le motif garde son identité tout en s’adaptant au médium.

---

# 10. Checklist de sortie du skill

Avant de retourner un prompt, vérifier :

- Le sujet est original et ne réutilise pas une composition ou un personnage iconique.
- Une seule famille visuelle reste dominante.
- La composition est décrite, pas seulement « le style ».
- La palette contient un nombre limité de couleurs cohérentes.
- La lumière est explicitement définie.
- Le niveau de décoratif et de symbolisme correspond à l’usage demandé.
- Le médium simulé est précisé.
- Le prompt exclut le texte, les signatures et les reproductions d’œuvres existantes.
- Une courte note pédagogique explique les codes mobilisés.

---

# 11. Modèle de réponse du skill

```markdown
## Direction visuelle

**Famille :** [famille retenue]  
**Codes mobilisés :** [3 à 5 codes]  
**Pourquoi :** [une phrase pédagogique]

## Prompt

```text
[prompt complet]
```

## Variante

```text
[variante : autre lumière, autre niveau d’ornement ou autre cadrage]
```

## À éviter

```text
[contraintes et négatif]
```

## Lecture pédagogique

- Composition : [analyse]
- Couleur : [analyse]
- Lumière : [analyse]
- Symbolisme / décor : [analyse]
- Référents de la Jeune Pologne : [familles ou artistes, sans prétendre copier une œuvre]
```

---

# Conclusion de curation

Un bon skill Młoda Polska ne répond pas seulement « fais une image à la manière de ». Il apprend à traduire une intention en vocabulaire formel : le vitrail travaille la lumière et la ligne ; le symbolisme transforme une idée en allégorie ; le portrait travaille la présence silencieuse ; le folklore transforme le costume et le rite en décor moderne ; le paysage fait de la météo un état intérieur ; le synthétisme organise les formes en masses mémorables.

L’objectif final est de permettre à un utilisateur de générer des images contemporaines, originales et cohérentes, tout en étant capable d’expliquer précisément ce qui les rattache aux différentes sensibilités de la Jeune Pologne.
