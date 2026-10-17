# Studio, Animation — personnaliser une direction et régler l'effort du modèle (relevé du 18/10/2026)

Suite de `2026-10-17-studio-animation-releve.md` (§ B). Demande de l'utilisateur, 18/10 : réinspecter le catalogue de
référence, dont les animations montrent maintenant toutes une page « personnaliser » ; identifier la structure de ses
prompts et les champs qui permettent de les modifier ; ajouter le réglage de l'**effort** du modèle IA choisi.

**Licence (§ B3, inchangé).** Rien du contenu du site n'entre dans le dépôt : aucun titre, pseudo, texte ou extrait de
prompt, aucune liste d'entrées. Le relevé détaillé (comptes, libellés, effets des curseurs) est HORS DÉPÔT, dans les
notes partagées de la session (`prompt-motion-personnalisation-releve-20261018.md`). Ci-dessous, seulement la
MÉCANIQUE, décrite avec nos mots.

**Décision de l'utilisateur (18/10) : tableau P1-P9 validé ; tâches t239, t240 et t241 insérées AVANT t236**
(plan `docs/superpowers/plans/2026-10-17-studio-animation.md`).

## 1. Ce qui a été relevé (lecture seule, volet navigateur intégré)

Une page de personnalisation demandée par l'utilisateur, l'index, puis les 235 pages lues pour des statistiques.
Aucun envoi ; une clé de stockage local écrite par le site pendant un essai a été supprimée.

### 1.1 Deux familles de pages

| Famille | Part | Mécanique |
|---|---|---|
| **Prompt réécrit à parties variables** | ~90 % | Le prompt est réécrit et testé ; 4 à 6 parties sont des **variables**. Chaque champ a un libellé, une aide d'une ligne et un texte d'exemple = la valeur par défaut, qui est exactement la partie surlignée dans le prompt. Champ vide → défaut ; rempli → remplace la partie. |
| **Prompt intact + bloc de précisions** | ~8 % | Le prompt n'est pas modifié. Des champs fixes (à quoi sert la vidéo, format, durée, couleurs, police, autre chose) produisent un bloc ajouté **après** le prompt : « mes précisions ; là où elles diffèrent du prompt, elles priment ». Les valeurs sont gardées dans le navigateur pour le prompt suivant. |
| **Gabarits** (2) | — | Écrits pour être personnalisés : « tout ce qu'on voudrait changer est un champ ». Même mécanique que la première famille. |

### 1.2 Champs

- **Communs presque partout** : Format (4 tailles : 16:9, 9:16, 1:1, 4:5), Durée (s, conseil 15-30), Tempo (BPM,
  « chaque mouvement tombe sur le temps », conseil 100-128).
- **Propres au sujet**, par familles : vitrine (concept, police, palette), produit (produit, marque, fin), explication
  (sujet, public), récit (histoire, voix, son), plus des champs uniques.

### 1.3 Trois curseurs à cinq crans, sur toutes les pages

| Curseur | Pôles | Effet |
|---|---|---|
| Créativité | prudent ↔ libre | cran du milieu = prompt tel quel ; les autres AJOUTENT une phrase de consigne en fin de la partie « direction » |
| Rythme | calme ↔ frénétique | idem, sur la cadence des changements (tenue d'un temps … chaque demi-temps et plus vite) |
| Finition | rapide ↔ obsessionnelle | phrase ajoutée en fin de la partie « construction » : nombre de passes de revue avant le rendu final |

### 1.4 Structure des prompts (sections balisées)

`inputs` (ce que le modèle doit demander d'abord) · `direction` (concept, police, palette, caméra, techniques, liste
d'interdits) · `structure` (tempo, découpage par mesures, boucle) · `build` (étapes techniques) · `gotchas` (pièges) ·
`start` (première action et livrable). Quatre combinaisons couvrent presque tout ; `build` décrit TOUJOURS un agent qui
écrit une page animée et la rend en vidéo image par image.

### 1.5 Le modèle et l'effort

Toutes les pages recommandent le même modèle de pointe **à l'effort maximal**. Chez nous, aucun moteur ne règle
l'effort aujourd'hui (`moteurs_texte.tirer` n'a pas ce paramètre).

Côté Anthropic (documentation à jour) : `output_config.effort` = `low` | `medium` | `high` | `xhigh` | `max`.
- Opus 5.5 / Haiku 5.5 : défaut `medium` ; les autres modèles récents : défaut `high`.
- `xhigh` : à partir d'Opus 4.7.
- Haiku 4.5 le REFUSE. Les niveaux se décident donc sur le modèle réellement choisi (nœud, sinon Réglages ›
  Valeurs par défaut, où l'utilisateur sélectionne déjà `claude-opus-5-5`), jamais sur un défaut figé du code.

Les autres moteurs ont leur propre réglage, à relever modèle par modèle au plan, sans le supposer : OpenAI (modèles de
raisonnement), Gemini (réflexion), Ollama / serveurs locaux (selon le modèle), fournisseurs libres (selon l'API).

## 2. Tableau d'écart

| # | Chez eux | Aujourd'hui chez nous (t231-t235) | Décision proposée |
|---|---|---|---|
| P1 | Parties variables dans le prompt, champ = défaut surligné | Fiches maison : consigne figée ; skill : consigne éditable en bloc | **Fiches maison à champs** : chaque fiche (écrite par nous) déclare ses `champs` (id, libellé FR/EN, aide, défaut, type texte / nombre / liste, bornes) et sa consigne les cite par `{{id}}`. Direction motion affiche une rubrique « Personnaliser » générée depuis la fiche ; valeurs dans le nœud ; t234 substitue (vide → défaut). |
| P2 | Prompt intact + bloc « mes précisions priment » | Import d'un prompt : texte en lecture seule | **Bloc de précisions** pour les prompts importés et les skills : champs fixes (à quoi ça sert, durée, couleurs, police, autre chose), ajoutés APRÈS la consigne avec la règle « en cas de conflit, mes précisions priment ». Le texte importé reste intact (attribution). |
| P3 | Champs communs : format, durée, tempo | Format = celui du Rendu, durée = celle de l'Animation, pas de tempo | Ajouter **Tempo (BPM)** à Direction motion (le repli et le moteur calent `start` sur les temps) ; format et durée restent lus sur le graphe, avec un **remplacement** possible dans le nœud. |
| P4 | Police et palette en champs | Police et couleurs = kit de marque de l'espace actif | Garder le kit par défaut ; champs **Police / Palette** facultatifs qui le remplacent pour cette direction. |
| P5 | Curseurs Créativité / Rythme / Finition, 5 crans, milieu = neutre | Rien | **Trois curseurs** dans Direction motion, phrases de consigne écrites par nous (FR/EN). En option A : Créativité et Rythme → consigne ; Finition → validation (repli plus strict à « rapide », seconde passe de vérification des bornes et de la lisibilité à « soignée »). En option B : nombre de passes de revue. |
| P6 | Une partie « inputs » : le modèle demande avant de commencer | Le chorégraphe ne demande rien | Ne pas reproduire (A est un appel unique) ; les champs du nœud jouent ce rôle. |
| P7 | Recommandation « modèle de pointe, effort max » | Moteur + modèle + bulle de coût, sans effort | **Sélecteur d'effort** dans Direction motion, à côté du modèle : « Auto (défaut du modèle) », puis les niveaux que CE moteur et CE modèle acceptent (exposés par `GET /api/motion/moteurs`). `moteurs_texte.tirer(…, effort=)` le traduit par fournisseur ; un niveau non accepté n'est jamais envoyé (un modèle ancien n'offre qu'« Auto », dit dans la bulle) ; le choix de
modèle offre toute la liste publiée, comme Réglages › Valeurs par défaut, celui des Réglages présélectionné (18/10). L'estimation de coût AVANT l'appel tient compte de l'effort (sortie maximale plus grande), sous les plafonds. |
| P8 | Valeurs gardées dans le navigateur pour le prompt suivant | Valeurs gardées dans le nœud | Garder dans le nœud ; un bouton « Reprendre mes précisions » réutilise celles du dernier nœud Direction motion. |
| P9 | Prompts écrits pour un agent qui code et rend une page animée | Option A (JSON borné) livrée ; B (t238) en attente | Les sections `direction` / `structure` nourrissent A ; `build` / `gotchas` ne servent qu'à **B**. À rappeler au moment de trancher t238. |

## 3. Effets sur le plan (à valider avant toute ligne de code)

- **Backend** (après t234) : champs des fiches, bloc de précisions, curseurs, tempo, effort → `motion_choregraphe`,
  `moteurs_texte.tirer(effort)`, `GET /api/motion/moteurs` (niveaux d'effort par moteur et modèle), et les 11 fiches
  maison réécrites avec leurs champs.
- **Bundle** (après t235, dans le maillon dzmotion) : rubrique « Personnaliser » générée, curseurs, effort, tempo,
  remplacements de format et de durée.
- **t236** (bandeau Bibliothèque) : le formulaire d'import gagne l'aperçu du bloc de précisions.
- Banc de garde G3 : les phrases de nos curseurs et nos champs sont écrits par nous ; la garde reste le juge.
