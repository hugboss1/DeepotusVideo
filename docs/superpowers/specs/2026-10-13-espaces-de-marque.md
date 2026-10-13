# Espaces de marque : plusieurs marques, personas et canaux sur une instance (13/10/2026)

## Besoin

Une seule installation de DeepotusVideo doit servir plusieurs marques ou projets :
- **Deepotus** : le jeu, le jeton et l'application, diffusés sur les mêmes canaux ;
- **Rippled** : la future plateforme, avec ses propres comptes ;
- **un client** qui achète une prestation de promotion et confie ses propres canaux.

Pour chaque marque, il faut :
- un persona défini précisément, par un onboarding mené avec l'utilisateur ;
- une identité visuelle ;
- ses kits de marque ;
- ses comptes de diffusion (plusieurs X, Telegram, etc.) ;
- des contenus de départ propres à la marque, à commencer par les modèles de prompt de Quick.

## État actuel (relevé du code, 13/10)

| Sujet | Aujourd'hui | Problème |
|---|---|---|
| Persona backend | `personas/deepotus.json` unique. `Pipeline(persona_id="deepotus")` en dur (routes.py l.94). Lu par prompt_engine, elevenlabs, news_voice, music, marketing, autoclips. | Un seul persona possible. |
| Persona écran | `PERSONA_PRESETS` codé en dur (persona.jsx), état React en mémoire seulement (shell.jsx l.531). | Rien n'est enregistré, et ce n'est pas relié au backend. |
| Kits de marque | `brand_kits.py` : jusqu'à 50 kits, un kit actif global (`assets/branding/kits.json`). | Les kits ne sont rattachés à aucune marque. |
| Comptes | Clés plates uniques dans config.py et le coffre DZKV1 (`X_ACCESS_TOKEN`, `TELEGRAM_CHAT_ID`…). | Un seul compte par plateforme. |
| Scheduler | `scheduled_posts.channels` = CSV de plateformes. | Aucun compte, aucune marque. |
| Quick | `PROMPT_TEMPLATES`, `PROMPT_CATS`, `ING` et `VIBES` codés en dur (prompts.jsx, screens.jsx). | Le contenu est 100 % Deepotus. |
| Bibliothèque | Projets #78 (`library_projects`) avec un projet actif. | Pas de marque. |
| Dépenses | Plafonds globaux, table `depenses` sans projet. | Impossible de chiffrer une prestation client. |
| Codé en dur | news_rank l.31, news_chain l.107, schemas l.503, prompt_engine l.83-96, music l.219, skill deepotus-comms. | Fuite de Deepotus dans les autres marques. |

## Conception

### D1. Une entité « Espace de marque », un espace actif
Un **espace** porte :
- un persona ;
- une identité visuelle ;
- un kit de marque par défaut, plus ses autres kits ;
- ses comptes de diffusion ;
- ses contenus de départ (modèles Quick, vibes, ingrédients, hashtags, voix) ;
- ses projets de Bibliothèque et ses dépenses.

Comme pour le kit actif, il y a **un espace actif à la fois**. Le sélecteur se trouve dans la carte de marque en bas de la barre latérale (là où s'affiche aujourd'hui « From the deep, for the deep »). Changer d'espace change le kit, le persona, la liste Quick, les comptes proposés et les filtres de la Bibliothèque et du Scheduler.

Stockage :
- table `espaces` : `id`, `nom`, `slug`, `kit_id`, `couleur`, `created_at`, `archive` ;
- `atelier_settings.espace_actif` ;
- fichiers de l'espace sous `DATA_ROOT/espaces/<id>/` : `persona.json`, `identite/`, `contenus.json`.

**Migration** : au premier lancement, l'existant devient l'espace `deepotus` **à l'octet** : persona, kit `deepotus`, clés plates converties en comptes, liste Quick actuelle. Aucune régression pour l'utilisateur actuel.

### D2. Persona v2 enregistré par espace
`persona.json` v2 est un sur-ensemble du fichier actuel :
- **identité** : nom, handle, une phrase de mission, produits ;
- **audience** ;
- **ton** : registres, mots à employer et mots bannis, catchphrase, langues ;
- **vibe_keywords**, negative prompt et hashtags ;
- **voix** : `voice_ids` et modes ;
- **visuel** : renvoi vers D4 ;
- **templates**.

Le moteur de prompt, la TTS, News, la musique, le marketing et les clips lisent **le persona de l'espace actif** (ou d'un espace donné, pour les tâches de fond). `persona_id="deepotus"` en dur disparaît. L'écran Persona lit et écrit ce fichier par l'API, ce qui met fin à l'état React volatile.

### D3. Onboarding du persona (assistant guidé)
Il se lance à la création d'un espace ou depuis Réglages › Persona. L'assistant compte huit étapes, toutes modifiables plus tard :

1. **Ce que l'on promeut** : produit ou service, URL, une phrase de pitch. Si une URL est donnée, l'assistant la lit pour proposer des réponses.
2. **Audience** : qui, où, ce que ces personnes aiment ou rejettent.
3. **Personnage** : mascotte ou personnage, humain, abstrait, ou marque sans incarnation ; description physique.
4. **Ton et voix** : choix entre des paires de curseurs (sérieux ↔ mème, oracle ↔ copain…), exemples de phrases à garder ou à rejeter, langues, voix TTS choisie à l'écoute.
5. **Univers visuel** : l'assistant montre des **planches d'ambiance comparatives** (4 vignettes générées à bas coût et devisées sous plafond). L'utilisateur choisit ou rejette ; on en tire palette, éclairage, cadrage, textures et époque.
6. **Références** : dépôt d'images (logo, mascotte, photos produit, captures d'anciennes publications), prises dans la Bibliothèque ou le disque.
7. **Interdits** : sujets, couleurs, mots et concurrents à éviter ; contraintes légales (crypto : pas de promesse de gain, par exemple).
8. **Synthèse** : un LLM rédige la fiche persona v2 et la **planche d'identité** (D4), puis génère les contenus de départ (D5). L'utilisateur relit, corrige et valide. Rien n'est écrit sans validation.

Comme pour le reste de l'application, l'assistant fonctionne sans LLM en mode manuel (formulaire). Le LLM rédige seulement sur demande et sous plafond.

### D4. Identité visuelle par persona
Le dossier `identite/` de l'espace contient :
- le logo ;
- les références de la mascotte ou du personnage (1 à 6 images) ;
- les photos produit ;
- la palette (hex et rôles) ;
- les typographies ;
- un style écrit (descripteurs, comme dans le skill vitrail : jamais de nom d'artiste) ;
- une planche d'identité générée et validée.

Usage dans l'application :
- injection des descripteurs dans les prompts (à la place du « DNA » Deepotus en dur) ;
- **images de référence** passées aux modèles qui les acceptent (image→vidéo, édition, avatar) ;
- couleurs et logo du kit par défaut de l'espace.

### D5. Contenus de départ générés par espace
`contenus.json` contient :
- les modèles de prompt Quick (même forme que `PROMPT_TEMPLATES` : id, titre, sous-titre, catégorie, prompt, icône) ;
- les catégories ;
- les ingrédients du générateur (`ING`) ;
- les vibes ;
- les modèles backend (`templates` du persona) ;
- les hashtags.

**Au premier démarrage d'un persona, Quick affiche ses modèles à lui** au lieu de la liste Deepotus. Le bouton « Générer » de la carte Prompt templates permet ensuite d'en produire d'autres, ou de régénérer une catégorie. Pour Deepotus, `contenus.json` reprend la liste actuelle à l'identique.

### D6. Comptes de diffusion multiples
Table `comptes_diffusion` : `id`, `espace_id`, `plateforme` (x, telegram, instagram, youtube, tiktok…), `libelle`, `handle`, `etat`, `created_at`.

- Les secrets restent dans le coffre DZKV1, sous des **noms espacés** (`compte.<id>.X_ACCESS_TOKEN`).
- Les anciennes clés plates sont migrées vers le compte « Deepotus » de chaque plateforme et restent lisibles en repli tant que la migration n'est pas faite.
- OAuth (YouTube, TikTok) **par compte** : le jeton tournant est réécrit dans le compte qui l'a produit.
- Les publishers reçoivent un compte au lieu de lire `config`.
- Plusieurs comptes de la même plateforme peuvent coexister dans un espace (par exemple deux X).

### D7. Scheduler par espace et par compte
- `scheduled_posts` reçoit `espace_id` et `cibles` (une liste de `compte_id`). `channels` reste lisible pour les anciens posts.
- Écran : filtre par espace (l'espace actif par défaut) et choix des comptes cibles parmi ceux **de l'espace du post**.
- **Garde** : une publication vers un compte d'un autre espace est refusée (409). Un post client ne peut pas partir sur un compte Deepotus.
- Métriques, séries et quotas (Instagram 100/24 h) sont comptés **par compte**.

### D8. Bibliothèque, dépenses, plafonds
- Les projets #78 sont rattachés à un espace.
- La Bibliothèque est filtrée par espace (avec un « tous » possible), et les rendus sont rangés dans l'espace actif.
- `depenses` reçoit `espace_id`. On peut ainsi afficher les dépenses par espace et **exporter un relevé pour facturer un client**.
- Plafond **optionnel par espace**, en plus du plafond global.

### D9. Isolation et client
- Export ou import d'un espace : persona, identité, contenus, kits et comptes **sans secrets** (les secrets se ressaisissent). Cela permet de remettre un dossier au client.
- Archivage d'un espace.
- Le skill `deepotus-comms` est paramétré par espace (persona et comptes de l'espace).

### D10. Le reste codé en dur
News (prompt de classement, titre, User-Agent neutre), musique, schemas, prompt_engine et prompts.jsx lisent l'espace actif. Les mots « deepotus » ne restent que dans les données de l'espace `deepotus`.

## Décisions prises par défaut (à contester)
- On parle d'« espace » (et non de workspace) dans l'interface, avec le libellé « Marque » en sous-titre. En anglais : « Brand space ».
- Un espace actif global, comme le kit actif, plutôt qu'un choix d'espace dans chaque écran. Les tâches de fond retiennent l'espace de leur création.
- Pas de multi-utilisateur ni de comptes de connexion : une seule personne utilise l'instance, et l'espace sert à séparer les contenus, pas à gérer des droits.
- Migration à l'octet de Deepotus avant toute autre chose.

## Ordre de livraison
Voir `docs/superpowers/plans/2026-10-13-espaces-de-marque.md` (tâches t200 à t211 du suivi).
