# MODELES.md — contrat des fiches modèle

Ce fichier est pour les mainteneurs et les agents de code qui écrivent ou modifient une fiche. Il n'est **jamais** servi
à l'assistant ni à l'utilisateur. Il adapte à Deepotus l'AGENTS.md de scenario-labs/skills (MIT, relu le 09/11/2026,
commit b96506d). La conception et ses raisons sont dans
`docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md`.

## À quoi sert une fiche

- Une fiche dit **comment bien se servir d'une famille de modèles**. Elle couvre l'écriture du prompt, les pièges, le
  moment où la choisir et la logique de coût.
- Les **paramètres** ne sont pas dans la fiche :
  - durées, formats, résolutions, image de fin, audio, négatif, seed ;
  - prix ;
  - clé présente.

  Ils vivent dans les registres (`fal_service.VIDEO_MODELS`, `pricing._IMAGE_MODELS`, `music_service.MUSIC_MODELS`…),
  lus par `catalogue_ia`. Au moment de servir une fiche, `services/modeles_fiches.py` y **ajoute** un bloc « Membres »
  généré depuis ces registres.
- Elle est lue par l'agent (outil `modele_fiche`) et par l'utilisateur (le « ? » à côté d'un sélecteur de modèle).
  Elle existe donc en **français et en anglais**.

## Où sont les fichiers

```
docs/agent/modeles/MODELES.md        ce contrat (mainteneurs)
docs/agent/modeles/README.md         sources, dates de relevé, mentions de licence (mainteneurs)
docs/agent/modeles/fr/_commun.md     tronc commun, servi avec chaque fiche
docs/agent/modeles/en/_commun.md     sa traduction
docs/agent/modeles/fr/<famille>.md   une fiche par famille
docs/agent/modeles/en/<famille>.md   sa traduction, même nom de fichier
```

- Le nom de fichier est la `famille`, en minuscules, chiffres et tirets.
- Il est **permanent** : jamais de numéro de version (`seedance`, pas `seedance-2-5`).
- Le README n'est ni servi ni lié depuis une fiche : un lecteur pourrait prendre des notes de maintenance pour des
  consignes.

## Front-matter

```
---
famille: seedance
natures: [video_i2v, video_fl]
ids: [seedance-v1-pro, seedance-2, seedance-2-fast, seedance-2.5]
voies: [fal]
releve: 2026-11-09
source: scenario-seedance, scenario-seedance-drafts (scenario-labs/skills, MIT)
description: À utiliser quand …
---
```

- **`natures`** : les natures de `catalogue_ia.natures()` que la famille sert.
  - Une famille dont les modèles n'ont encore aucune nature dans le catalogue (voix, génération 3D) en reçoit une
    **avant** sa fiche.
- **`ids`** : la liste exacte des ids de ces natures qui appartiennent à la famille.
  - Un id appartient à **une seule** fiche.
  - Les ids sont identiques en FR et en EN.
- **`voies`** : les voies présentes (`fal`, `openai`, `gemini`, `elevenlabs`, `meshy`, `heygen`, `local`).
- **`releve`** : la date où les faits de la fiche ont été vérifiés (AAAA-MM-JJ).
- **`source`** : d'où viennent les faits. On cite un skill MIT par son nom, et un relevé fal par sa date.
- **`description`** :
  - elle commence par « À utiliser quand » (EN : « Use when ») et fait 500 caractères au plus ;
  - elle nomme les **situations** qui déclenchent la fiche, jamais le résumé de son contenu ;
  - elle est riche en mots qu'un agent chercherait ;
  - les noms de versions y sont permis (« Seedance 2.5 et 2.0 »), pour qu'une recherche par version trouve la fiche.

Le `_commun.md` porte seulement `famille: _commun`, `releve`, `source` et `description`.

## Corps

- **Quatre parties, dans cet ordre, avec ces titres de niveau 2 :**
  - FR : `## Aperçu`, `## Référence rapide`, `## Exemple`, `## Erreurs fréquentes` ;
  - EN : `## Overview`, `## Quick reference`, `## Example`, `## Common mistakes`.
- **Budget** : 600 mots en cible, **1200 au plus** pour une fiche, 700 pour `_commun.md`.
  - Pourquoi : le corps entre dans le contexte de l'agent à chaque lecture et concurrence la tâche.
  - On dépense les mots sur ce que l'agent devinerait **mal**, pas sur de la prose.
  - Au-delà du budget : couper d'abord, scinder en dernier.
- **Référence rapide** : des puces étiquetées, une idée par puce.
  - `[PROMPT]` : comment écrire.
  - `[PIÈGE]` : erreur et correctif.
  - `[CHOIX]` : quand la prendre ou non.
  - `[COÛT]` : logique de coût.
  - `[MÉTHODE]` : procédure.
  - EN : `[PROMPT]`, `[PITFALL]`, `[CHOICE]`, `[COST]`, `[METHOD]`.
- **Exemple** : **un** cas complet. Il contient le brief de l'utilisateur, le prompt écrit pour ce modèle et les
  réglages choisis. Un excellent exemple vaut mieux que trois moyens.
- **Erreurs fréquentes** : ce que l'agent ou l'utilisateur fait de travers en premier, et le correctif.

## Règles de fond

1. **Les versions sont des données, pas une identité.**
   - Une famille regroupe un fournisseur et une lignée (Seedance, Kling, Veo…).
   - On ne la scinde que si des membres qui coexistent produisent des types de sortie différents, jamais par
     version.
2. **Aucun plafond du registre n'est recopié dans un corps** : durées, formats, résolutions, prix.
   - Le bloc « Membres » les affiche.
   - Une fiche peut dire « le plus long des membres » ou « lire la durée maximale dans Membres », jamais « jusqu'à
     15 s ».
   - Un chiffre qui ne vient pas d'un registre (coût relatif, nombre de références) est **daté** : « (relevé
     2026-11) ».
3. **Les méthodes et les rôles métier ne nomment pas de modèle génératif.**
   - Ils demandent une **capacité** (une nature : image vers vidéo, musique, détourage…) ; l'agent la résout par
     `recommander_modele` (contraintes, fiches, coût) puis la fiche du choix, et relit son prompt par
     `verifier_prompt` avant un tir payant.
   - Seuls les outils locaux et déterministes ont un nom fixe, parce qu'ils n'ont pas de concurrent : ffmpeg, rembg
     local, htdemucs, Photolab, les briques (`mesurer`, `comparer`, `conformer`).
   - Les champs de **données** `modeles` et `equivalents` de `knowledge/methodes.json` et les `exemples` (les mots de
     l'utilisateur) sont exemptés.
4. **Toute étape payante dit ce qui se passe sans surveillance.**
   - Elle passe par devis, `plafonds.verifier` et `confirme_cout`.
   - Une fiche ne promet jamais une confirmation que le serveur n'impose pas.
   - « Brouillon d'abord » est dit quand un membre le permet.
5. **Le devis est un modèle de prix.** Quand l'écart avec la facture est connu (facturation aux jetons, minimum
   facturé), la fiche le dit.
6. **Aucune marque de divulgation imposée.** Une fiche ne dit jamais d'incruster un filigrane ou une mention « IA » :
   c'est à l'utilisateur d'en décider.
7. **Reformuler, ne pas copier.**
   - Les faits viennent de sources publiques : skills MIT de Scenario, schémas fal relus, essais.
   - Ils sont **réécrits**.
   - Le README tient la liste des sources ; `docs/licences/scenario-mit.md` tient la mention MIT.

## Écriture

- Commencer par la consigne ou le fait. Pas de préambule, pas de résumé final.
- Un fait par phrase, environ 20 mots ; au-delà de 40 mots, couper ou faire une liste.
- Garder les mots de condition : seulement, sauf, jamais, avant, après. Concis ne veut pas dire télégraphique.
- Ne donner une raison que si elle évite une erreur, en une proposition.
- Ne marquer une prudence que sur un fait qui change (un chiffre daté). Le reste s'écrit à plat.
- Dire une fois, puis s'arrêter. Avant de supprimer un doublon, comparer point par point : un même sujet ne veut pas
  dire un même contenu.
- Changer une règle commune, c'est la chercher dans `_commun.md` et dans toutes les fiches, et la corriger partout dans
  la même PR.
- Les prompts d'exemple sont écrits **dans la langue que le modèle comprend le mieux** (souvent l'anglais), y compris
  dans la fiche française ; le texte autour est traduit.
- Pas de langage marketing.

### Glossaire

| Terme | Sens | Pas |
|---|---|---|
| modèle | un id d'un registre (`seedance-2.5`) | une fiche |
| famille | les modèles d'une même lignée, une fiche | un fournisseur |
| membre | un modèle dans sa famille | une version de fiche |
| voie | le chemin d'appel et sa clé (`fal`, `openai`, `local`…) | le fournisseur |
| jumeau | le même modèle servi par l'autre voie | une alternative |
| nature | une capacité de `catalogue_ia` (`video_i2v`, `musique`…) | un écran |
| tir | une génération payante | un essai gratuit |
| devis | le prix calculé avant un tir | la facture |
| fiche | un fichier `<famille>.md` | une méthode |
| méthode | une fiche de `knowledge/methodes.json` | une fiche modèle |
| boîte | un groupe d'outils d'agent (`agent_boites`) | un outil |

## Validation

- **Banc `backend/tests/test_modeles_fiches.py`** : front-matter, budget, plan, parité FR/EN, ids existants, couverture,
  chiffres du registre absents, aucun nom de modèle dans les rôles métier ni dans le texte des méthodes.
  - **Couverture** : dès qu'une nature a une fiche, **chacun** de ses ids doit appartenir à une fiche.
  - Ajouter un modèle au registre sans le ranger dans une fiche fait donc rougir le banc.
- **Mutations** : `python scripts/mutations_modeles_fiches.py`. Chaque mutation doit être tuée.
- **Épreuve d'application**, avant de fusionner un lot de fiches :
  - sur le backend de preuve sans clé, on soumet des briefs types à l'agent ;
  - on note s'il lit la bonne fiche, choisit un membre compatible et écrit un prompt conforme ;
  - aucun tir ;
  - la transcription est jointe à la PR.
- **Nouveau modèle** = une entrée de registre + un prix + son id dans le front-matter d'une fiche FR **et** EN. Les
  menus, l'agent et le « ? » suivent seuls.
