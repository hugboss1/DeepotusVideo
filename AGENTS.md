# AGENTS.md — DeepotusVideo

Référence unique pour les agents de code (Claude Code, Cursor, Copilot…). `CLAUDE.md` y renvoie.
Pour aider l'UTILISATEUR de l'application, l'assistant intégré lit `docs/agent/AGENT.md`, pas ce fichier.

## Vue d'ensemble
DeepotusVideo est un studio local Windows, clavier d'abord, pour fabriquer des vidéos 9:16 virales et leurs
ressources. Il compte 14 écrans : Quick, Studio, Chapitres, Son & VFX, Montage, Planificateur, Modèles, News,
Bibliothèque, Game Assets, Vectorlab, Photolab, Avatar live et Réglages. Un seul utilisateur. Le français est la langue
de référence, l'anglais en est la traduction. Le produit est décrit dans `PRODUCT.md`, la direction visuelle dans
`DESIGN.md`.

## Architecture
- **Backend** FastAPI dans `backend/app` : les routes sont dans `api/`, les services dans `services/`, l'application
  dans `main.py`. Les données de l'utilisateur sont dans `%LOCALAPPDATA%\DeepotusVideoGenData` ;
  `%LOCALAPPDATA%\DeepotusVideoGen` est le dossier de l'application (Python embarqué).
- **SPA** : le bundle `frontend/dist/assets/index-*.js` est **prébâti puis patché**. On ne le reconstruit jamais
  depuis `frontend/src` (voir `frontend/SOURCE.md`). Toute modification passe par un script
  `scripts/patch_bundle_<tag>.py` (paires d'ancres uniques, sonde amont, `.bak_<tag>`, `--check`), et toute la chaîne
  se rejoue avec `scripts/repatch_all.py`.
- **Labs** : des pages autonomes `frontend/<lab>/index.html` avec leurs `js/mod-*.js`, affichées dans un cadre
  intégré de la SPA.
- **Scripts partagés** : la source est `frontend/shared/`, la copie identique est `frontend/dist/shared/`, le tout
  servi à `/shared/`.
- **LLM** : `backend/app/services/moteurs_texte.py`. `tirer` fait un seul appel, sans repli muet. `tirer_garde` passe
  par le plafond.
- **Dépenses** : toute route payante appelle `plafonds.verifier`, sinon le banc `test_plafonds_garde` échoue.
- **Clés** : le coffre est dans `services/coffre.py`, en localhost seulement.
- **Espaces** : un espace a un type (`marque`, `produit` ou `client`, dans `services/espaces.py`). Un produit peut avoir
  un parent (une marque ou un client) ; `espaces.client_responsable` remonte au parent pour trouver le client
  responsable. Les règles de publication s'y brancheront en t309 (validation client et sécurités) ; rien ne les
  applique encore.
- **Traduction** : `dzT(clé)` côté écran (`frontend/shared/i18n/*.json`, assemblés par
  `scripts/i18n_assembler.py`) ; côté serveur, `app.i18n`.

## Fichiers clés
| Fichier | Rôle |
|---|---|
| `backend/app/main.py` | Application, montages statiques, routeurs |
| `backend/app/api/routes.py` | Routes historiques (énorme ; préférer un routeur dédié) |
| `backend/app/api/settings_routes.py` | Réglages, index de recherche des Réglages |
| `backend/app/services/moteurs_texte.py` | Registre des moteurs de texte, `tirer`, `tirer_garde` |
| `backend/app/services/plafonds.py` | Plafonds de dépense mensuels |
| `backend/app/services/agent_boites.py` | Boîtes à outils de l'agent par fonctionnalité (`BOITES`, `outils_pour`, `paquet_mobile`) ; hors boîte = refus ; servies au compagnon dans `boites.json` du paquet |
| `backend/app/services/coffre.py` | Coffre à clés chiffré |
| `backend/app/services/espaces.py` | Espaces de marque |
| `backend/app/services/fiche_client.py` | Fiche d'un client (`client.json` par espace) : contact, mode de publication, consentements datés par canal, révocation, journal. Écritures locales seulement (t306 (25/10/2026)), lecture `GET` aussi ouverte aux appareils appairés : `GET/PUT /api/espaces/{id}/client`, `POST …/client/consentements`, `POST …/client/consentements/revoquer` |
| `frontend/dist/index.html` | Page de la SPA, scripts partagés |
| `frontend/shared/dz-i18n.js` | Runtime `dzT` |
| `frontend/shared/dz-plafonds.js` | Dialogue du 402 `dz_plafond` |
| `frontend/shared/dz-projet-canaux.js` | t307 (25/10/2026) : boîte des CANAUX d'un projet de la Bibliothèque (`window.__dzProjetCanaux.ouvrir(projet)`, comptes de l'espace du projet, `PUT /api/library/projets/{id}/canaux`, évènement `dz-projet-canaux`) et glyphes des canaux dans l'hôte `data-dz-projet-canaux` de la barre « Projet » ; copie identique dans `frontend/dist/shared/`. La barre vit dans la couche `frontend/patches/montage.js` (aides `dzPcB`/`dzPcEc`, saisie `scripts/i18n_l3/montage_i.py` + miroir G1 `scripts/icones/g1_generer.py`, puis `refresh_layer --layer montage`) — aucun maillon de queue ; banc `test_projets_canaux_ecran` |
| `frontend/shared/dz-espace-assistant.js` | t308 (26/10/2026) : ASSISTANT de création d'espace en quatre temps (`window.__dzEspaceAssistant.ouvrir(opts)` : type et identité, fiche client, canaux avec « Vérifier » sans publication, récapitulatif ; « Terminer » active et émet `dz-espace-cree`) ; copie identique dans `frontend/dist/shared/`. « Créer l'espace » de Réglages › Espaces l'ouvre par le maillon de queue `scripts/patch_bundle_dzassistant.py` (inverse `avant_dzassistant`, en tête de `avant_dzagentplan`) ; banc `test_espace_assistant_ecran` |
| `frontend/SOURCE.md` | Pourquoi le bundle ne se reconstruit pas |
| `scripts/repatch_all.py` | Rejoue la chaîne des patchers |
| `scripts/i18n_assembler.py` | Assemble le dictionnaire FR/EN |
| `scripts/guide/construire_guide.py` | Construit le guide utilisateur |
| `scripts/guide/serve_guide.py` | Backend de preuve (8809, sans clé) |
| `docs/guide/src/chapitres.json` | Chapitres du guide (lisibles par machine) |

## Lancer et tester
- Python embarqué : `$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. Il ignore PYTHONPATH : chaque banc
  insère `backend/` lui-même. On lance depuis `backend/` : `& $PY tests/<banc>.py`.
- Suite complète : `.\scripts\run-tests.ps1`.
- Bancs des labs et de `/shared` : `node frontend/<lab>/qa/<banc>.test.mjs`.
- Illustrations animées des gestes VFX IA (t275) : `& $PY scripts/sonvfx_illustrations.py [id…]` rend les pages
  `scripts/sonvfx_illus/<id>.html` dans `frontend/dist/sonvfx/illus/` ; `--jeu post` rend celles des presets de
  post-traitement (t278, `scripts/sonvfx_illus_post/` → `frontend/dist/sonvfx/illus-post/`) ; `--check` vérifie que
  les deux jeux sont à jour.
- Preuve à l'écran : `& $PY scripts/guide/serve_guide.py` (port 8809). Ne jamais toucher au 8765 de l'utilisateur.
- Installation : comparer les empreintes avec `git hash-object`, jamais sha256.

## Conventions
- Noms et commentaires en français. Chaque fonctionnalité est datée et rattachée à sa tâche (`t237`, `#387`…).
- Aucune chaîne visible en dur : `dzT`, avec une clé FR et une clé EN.
- Une copie `frontend/dist/shared` est identique à sa source, et un banc le vérifie.
- Un modèle sans clé reste choisissable et n'est jamais grisé : le refus arrive au lancement (503), avant le plafond.
- On n'écrit jamais une clé dans un journal, une URL ou une réponse.
- Les bancs arrivent avant le code (TDD). Les bancs de patch ont leur inverse.

## Git
- Une branche par chantier : `chantier/<sujet>` ou `claude/<sujet>`. Une PR par lot. Jamais de push forcé sur main.
- Dans un worktree partagé : `git commit --only <fichiers>`.
- Message en français, au format `<zone> : <quoi> (tNNN)`.

## Tenir ce fichier à jour
Quand l'architecture, une commande ou une convention change, mets à jour ce fichier dans la même PR. Quand une
fonctionnalité visible est livrée, mets aussi à jour `docs/agent/AGENT.md` et `docs/agent/ancres.json`.
