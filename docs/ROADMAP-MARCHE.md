# Roadmap marché — Deepotus Video Gen

> Rédigé le 6 août 2026, à partir de l'audit technique (`AUDIT-2026-08.md`) et
> d'une revue de l'état du marché : générateurs vidéo (Runway Gen-4.5, Kling
> 3.0, Veo 3.1, Luma Ray3), outils d'automatisation sociale (OpusClip,
> AutoShorts, Zebracat, Revid), éditeurs nodaux (ComfyUI, Figma Weave, Flora),
> et plateformes de vente (Lemon Squeezy, Paddle).

## 1. Le positionnement à tenir

Trois faits de marché définissent la fenêtre de tir.

**L'angoisse des crédits est le premier motif de churn.** Un Américain paie en
moyenne 66 $/mois répartis sur quatre outils IA, et 53 % déclarent résilier
puis se réabonner au gré des besoins. Le grief n'est pas le prix affiché mais
l'imprévisibilité : les crédits fondent sans avertissement, on découvre la
déduction après avoir cliqué sur « générer ». Les concurrents directs facturent
15 à 70 $/mois en crédits (OpusClip 15–29 $, AutoShorts 19–69 $, Zebracat
19–199 $, Revid 32–166 $).

**Un fournisseur peut disparaître du jour au lendemain.** OpenAI a fermé Sora
en mars 2026 — application grand public, API, et un partenariat Disney à un
milliard. Tout produit adossé à un seul modèle est mortel.

**La vidéo IA ne tourne pas en local.** Les modèles qui comptent sont des API
cloud à poids fermés. Une app de bureau ne peut donc pas vendre « l'IA chez
vous » ; elle vend *le studio* chez vous, et le calcul chez les fournisseurs.

D'où le message, qui doit être la première phrase de la page de vente :

> **Payez le logiciel une fois. Payez l'IA au prix coûtant, directement aux
> fournisseurs. Aucun abonnement, aucune marge sur vos générations, et vos
> projets restent sur votre machine.**

Le corollaire commercial : le multi-fournisseur n'est pas une case à cocher,
c'est l'argument de survie. « Quand un modèle ferme, vous changez de moteur
dans un menu déroulant — vous ne changez pas d'outil. » L'app route déjà
fal.ai, HeyGen, ElevenLabs, OpenAI, Gemini, Meshy : c'est un actif à mettre en
avant, pas un détail d'implémentation.

## 2. Priorité 0 — bloquants de la mise en vente

Détaillés dans l'audit. Rappel condensé, dans l'ordre :

1. Signer l'installeur (SmartScreen tue la conversion sur un `.exe` de 2,6 Go
   d'éditeur inconnu).
2. Découpler la marque : persona par défaut neutre, deepotus livré en exemple.
   Aujourd'hui un acheteur reçoit le cockpit memecoin de l'auteur.
3. Canal de distribution public + vérification de mise à jour dans l'app.
4. Vérifier les licences des six polices « display » et le build ffmpeg (GPL).
5. Tester l'installation avec un nom d'utilisateur long (risque MAX_PATH).

L'EULA, les logs de support et le correctif gltfpack sont déjà livrés.

## 3. Priorité 1 — les fonctionnalités qui convertissent

### 3.1 Le mur de cohérence (le plus gros différenciateur disponible)

C'est le problème n°1 non résolu du marché : 29 % des vidéos IA présentent des
incohérences, et au-delà de trente secondes le personnage dérive — cheveux,
visage, proportions. Tous les concurrents échouent dessus.

L'app a déjà les briques : l'Atelier tient une bible d'entités avec planches
de référence, seeds et styles ; le casting voix associe une voix par
personnage. Il manque le liant :

- **Fiche personnage verrouillée** : une entité de la bible devient un objet
  réutilisable (planche de référence + seed + prompt d'identité + voix), qu'on
  glisse dans n'importe quel nœud Studio, épisode ou plan de montage.
- **Injection automatique** de la référence dans chaque génération qui cite le
  personnage, sans que l'utilisateur reconstruise son prompt.
- **Contrôle de dérive** : comparer chaque nouveau plan à la planche de
  référence et signaler visuellement quand la ressemblance décroche, avant que
  l'utilisateur ait payé dix générations.

C'est la fonctionnalité à mettre en démonstration sur la page de vente. Elle
justifie à elle seule le prix.

### 3.2 Transformer le widget de coût en argument de vente

Le widget estime déjà. Il doit devenir le remède explicite à l'angoisse des
crédits :

- **Plafond de dépense** paramétrable (jour / semaine / mois) avec blocage
  effectif, pas seulement une estimation. Aujourd'hui rien n'empêche une
  boucle de brûler un budget.
- **Coût affiché avant confirmation** sur toute action payante, avec le solde
  restant du fournisseur quand son API l'expose (Meshy le fait déjà).
- **Journal de dépense** exportable par projet et par fournisseur — un
  freelance refacture ses générations à son client.
- **Comparateur de moteurs** au moment du choix : « ce plan coûte 0,12 $ en
  Kling 3.0, 0,31 $ en Veo 3.1 » — la valeur du multi-fournisseur rendue
  visible à l'instant de la décision.

### 3.3 Élargir le marché adressable au-delà du crypto

Le châssis est générique ; seul le contenu par défaut ne l'est pas. Trois
verticales à faible coût d'ajout, chacune n'étant qu'un jeu de personas, de
templates et de presets :

- **Chaînes « faceless »** (le marché d'AutoShorts et Revid) : storytelling,
  listicles, histoires horrifiques, vulgarisation.
- **Petits commerces et artisans** : présentation de produit, avant/après,
  témoignage — format vertical, publication programmée.
- **Auteurs et éditeurs** : la fonctionnalité Épisodes (roman → chapitres
  narrés illustrés) est unique sur le marché et n'est vendue par personne.
  C'est peut-être le meilleur produit caché de l'application.

### 3.4 Ce que les concurrents ont et qui manque

- **Repurposing d'une vidéo longue en shorts** — le cœur d'OpusClip, absent
  ici. L'app sait déjà découper, monter, sous-titrer : il manque l'import
  d'une vidéo longue, la détection des moments forts et l'export en série.
- **Sous-titres animés** (karaoké mot à mot) : standard absolu du format
  vertical, et le moteur de texte animé existe déjà (nœud Animation).
- **Recadrage automatique 16:9 → 9:16** avec suivi du sujet.

## 4. Priorité 2 — l'UX qui fait rester

L'application a déjà ce que le marché considère comme l'avenir : un canvas
nodal. C'est la catégorie de 2026 (Figma a racheté Weavy, Flora lève, ComfyUI
reste la référence). Il faut en tirer parti au lieu de le traiter comme un
écran parmi douze.

**Le problème d'ergonomie principal est le nombre d'écrans.** Studio,
Scheduler, Bibliothèque, Montage, Son & VFX, Épisodes, Atelier, Game Assets,
Sprite Lab, Tile Lab, 3D Studio, News : douze surfaces dont plusieurs sont des
pages autonomes iframées. Un nouvel acheteur ne sait pas par où entrer.

- **Un écran d'accueil orienté intention**, pas navigation : « Faire un clip »,
  « Publier ma semaine », « Adapter un texte », « Créer des assets de jeu ».
  Chaque intention ouvre le bon écran préchargé.
- **Modèles de départ** : six graphes Studio prêts à l'emploi plutôt qu'un
  canvas vide. Le canvas vide est le principal point d'abandon des outils
  nodaux.
- **Fusionner les sous-écrans** : Sprite Lab, Tile Lab et Game Assets sont trois
  entrées pour une même intention.
- **Premier rendu en moins de cinq minutes**, sans clé si possible : un mode
  démonstration avec des assets locaux (le mode `MESHY_MOCK` prouve que le
  motif est déjà maîtrisé) pour que l'acheteur voie le produit fonctionner
  avant de créer un compte fournisseur.
- **Reprendre où on s'est arrêté** : les rendus sont longs, l'utilisateur part
  ailleurs. Une notification système à la fin d'un rendu, et une file
  d'attente visible depuis n'importe quel écran.

Ce qu'il ne faut **pas** faire : ajouter des écrans. La direction visuelle
Cinema est bonne et cohérente ; l'effort doit porter sur la réduction du
nombre de portes d'entrée.

## 5. Priorité 3 — la version hébergée à crédits

L'audit liste les blocages architecturaux : SQLite et chemins locaux sans
dimension locataire, sécurité fondée sur « être sur localhost », configuration
qui réécrit un `.env` et exige un redémarrage, boucles et singletons
mono-utilisateur, rendus qui appellent un ffmpeg local.

La migration est un vrai projet, à ne pas lancer avant d'avoir vendu. L'ordre
qui limite la casse :

1. Introduire une notion de compte et d'identité **dans l'app de bureau**
   (même mono-utilisateur) pour que le code cesse de supposer un seul monde.
2. Sortir les clés et réglages du `.env` vers la base, appliqués à chaud.
3. Extraire le rendu dans une file de travaux séparée du processus web.
4. Alors seulement : Postgres, stockage objet, et facturation à crédits avec
   les clés de la plateforme.

Le modèle hybride est le plus défendable commercialement : **achat unique BYO**
pour ceux qui veulent le prix coûtant, **crédits prépayés** pour ceux qui ne
veulent pas créer six comptes fournisseurs. Les mêmes écrans, deux modes
d'approvisionnement.

## 6. Prix et distribution

- **Vendre via un marchand de référence** (Lemon Squeezy ou Paddle) : 5 % +
  0,50 $ par transaction, TVA et facturation gérées, clés de licence
  intégrées. Pour un vendeur solo en France, c'est le seul moyen raisonnable
  de vendre mondialement sans monter une infrastructure de conformité. Lemon
  Squeezy pour démarrer, Paddle si le volume et les besoins d'abonnement
  arrivent.
- **Structure de prix** : un tarif unique lisible (une licence, machines
  personnelles), une remise de lancement limitée dans le temps, et une
  politique de mise à jour explicite — « mises à jour de la version majeure
  incluses » est la formulation la plus honnête et la plus vendeuse face à
  l'abonnement.
- **Argumentaire chiffré** sur la page de vente : le prix d'achat unique
  comparé au coût annuel des concurrents (180 à 800 $/an). C'est le calcul que
  l'acheteur fait de toute façon ; autant le faire pour lui.
- **Vérification de licence hors ligne** (clé signée validée localement) :
  suffisante pour un achat unique, et cohérente avec la promesse « tout reste
  sur votre machine ». Une activation en ligne obligatoire contredirait le
  positionnement.

## 7. Ce qu'il ne faut pas faire

- **Ne pas courir après la génération de modèles.** Runway, Kling et Google
  ont des milliards ; la valeur de ce produit est l'orchestration, la
  cohérence et le flux de travail, pas le modèle.
- **Ne pas ajouter de fonctionnalités avant d'avoir découplé la marque et
  signé l'installeur.** Aucune fonctionnalité ne compense un produit qu'on ne
  peut pas installer ou qui parle d'un memecoin qu'on ne connaît pas.
- **Ne pas basculer en abonnement** après avoir vendu un achat unique : c'est
  le meilleur moyen de perdre la communauté qui aura porté le lancement.
- **Ne pas promettre l'hébergé trop tôt.** Le dire comme une intention, pas
  comme une date.

---

## Séquence recommandée

| Étape | Contenu | Objectif |
|---|---|---|
| 1 | Signature, marque neutre, distribution, licences polices | Pouvoir vendre |
| 2 | Accueil par intention, modèles de départ, mode démonstration | Que l'acheteur réussisse son premier rendu |
| 3 | Fiche personnage verrouillée + contrôle de dérive | La raison d'acheter plutôt qu'un abonnement |
| 4 | Plafonds de dépense, journal de coûts, comparateur de moteurs | Retirer l'angoisse des crédits, l'argument de vente |
| 5 | Repurposing vidéo longue, sous-titres animés, recadrage suivi | Rattraper le standard du format vertical |
| 6 | Verticales (faceless, commerces, auteurs) | Élargir au-delà du crypto |
| 7 | Préparation multi-locataire, puis crédits hébergés | Deuxième source de revenus |
