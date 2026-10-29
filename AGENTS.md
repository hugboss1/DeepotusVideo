# AGENTS.md — DeepotusVideo

Référence unique pour les agents de code (Claude Code, Cursor, Copilot…). `CLAUDE.md` y renvoie.
Pour aider l'UTILISATEUR de l'application, l'assistant intégré lit `docs/agent/AGENT.md`, pas ce fichier.

## Vue d'ensemble
DeepotusVideo est un studio local Windows, clavier d'abord, pour fabriquer des vidéos 9:16 virales et leurs
ressources. Il compte 15 écrans : Quick, Studio, Chapitres, Son & VFX, Montage, Planificateur, Modèles, News,
Bibliothèque, Game Assets, Vectorlab, Photolab, Avatar live, WhatsApp et Réglages. Un seul utilisateur. Le français est la langue
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
  applique encore. Le type `demonstration` (t353) naît seulement au rendez-vous d'un prospect
  (`espaces.creer_demonstration`), ne publie JAMAIS (refus dans `comptes.creer`, `whatsapp.creer_lien`,
  `regles_client.controler` code `demonstration`) et ne devient que `client`, à la signature
  (`espaces.convertir_demonstration`).
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
| `backend/app/services/veille.py` (+ `backend/app/services/veille_collecte.py`, `backend/app/services/veille_grille.py`, `backend/app/api/veille_routes.py`) | Veille concurrentielle par espace (t352 (27/10/2026)) : collecte niveau 1 HN / YouTube (yt-dlp, non embarqué) / App Store en lecture seule, plafonnée, auteurs hachés ; classement par lexique (sans dépense) ou importé ; rapport rangé dans le dossier veille de l'espace, daté ; routes /api/veille ; outils `veille_collecter` / `veille_lire` (boîte « veille ») ; écran `frontend/shared/dz-veille.js`, 3e onglet du tiroir F1 |
| `backend/app/services/prospects.py` (+ `backend/app/services/oppositions.py`, `backend/app/api/prospects_routes.py` ; t354 : `backend/app/services/prospects_sources.py`, `backend/app/services/prospects_score.py`, `backend/app/services/entreprises_registre.py`, `backend/app/services/recherche_web.py`) | Fiche Prospects par espace (t353 (27/10/2026)) : `prospects.json` de l'espace, `source` et `base_legale` exigées, transitions de statut bornées, purge 3 ans après le dernier contact venu du prospect (`purge_loop` dans `lifespan`), opposition = anonymisation, export, effacement ; registre GLOBAL des oppositions haché (DATA_ROOT/espaces/oppositions.json) ; routes /api/prospects (local seulement) ; espace démonstration au rdv ; écran `frontend/shared/dz-prospects.js`, 4e onglet du tiroir F1. Aucun envoi, aucune dépense |
| `backend/app/services/coffre.py` | Coffre à clés chiffré |
| `backend/app/services/espaces.py` | Espaces de marque |
| `backend/app/services/fiche_client.py` | Fiche d'un client (`client.json` par espace) : contact, mode de publication, consentements datés par canal, révocation, journal. Écritures locales seulement (t306 (25/10/2026)), lecture `GET` aussi ouverte aux appareils appairés : `GET/PUT /api/espaces/{id}/client`, `POST …/client/consentements`, `POST …/client/consentements/revoquer` |
| `frontend/dist/index.html` | Page de la SPA, scripts partagés |
| `frontend/shared/dz-i18n.js` | Runtime `dzT` |
| `frontend/shared/dz-plafonds.js` | Dialogue du 402 `dz_plafond` |
| `frontend/shared/dz-scan.js` | t312 (28/10/2026) : boîte SCAN (`window.__dzScan.ouvrir({hote, serie, inserer, creerChapitres, importerManuscrit})`) : dépôt / coller / choix de 1 à 10 images ou PDF, langue fr/en/auto, `POST /api/scan/lire`, aperçu modifiable aux mots incertains surlignés, secours Claude sur devis (`dz-plafonds`, `__dzDialogue.confirmer`), trois envois ; copie identique dans `frontend/dist/shared/`. Montée par la page autonome de l'Atelier (`frontend/atelier/atelier.js`, `scanBoutons` : `#scanBtn`, `#scanChapBtn`), aucun maillon de bundle ; bancs `scan.test.mjs`, `scan_atelier.test.mjs`, `test_scan_ecran` |
| `frontend/shared/dz-inspiration.js` | t313 (28/10/2026) : boîte INSPIRATION → contenu neuf (`window.__dzInspiration.ouvrir()`) : capture et source, matière et trois angles (Claude sur devis), carte de devis texte + visuel fal neuf, brouillon gardé (`/api/inspiration/*`) ; copie identique dans `frontend/dist/shared/`, balise dans `frontend/dist/index.html` ; ouverte par le bouton du Planificateur (maillon `dzinspiration`) ; bancs `inspiration.test.mjs`, `test_inspiration_ecran` |
| `backend/app/services/scan_ocr.py` (+ `scan_ocr.ps1`, `scan_nettoyage.py`, `scan_lecture.py`, `scan_pages.py`, `scan_vision.py`, `backend/app/api/scan_routes.py`) | Scan d'une page → texte (t312) : pont PowerShell → Windows.Media.Ocr (pas de Tesseract), nettoyage PUR (colonnes, césures, folios, titres courants, paragraphes, mots incertains), lecture partagée routes/outil d'agent, cache des pages 1 h (256 Mo), secours Claude vision sur devis (catégorie « atelier ») ; routes `/api/scan/*` locales ; outil `lire_texte_image` (boîte « scan ») ; mesure `scripts/scan_mesure.py` |
| `frontend/shared/dz-projet-canaux.js` | t307 (25/10/2026) : boîte des CANAUX d'un projet de la Bibliothèque (`window.__dzProjetCanaux.ouvrir(projet)`, comptes de l'espace du projet, `PUT /api/library/projets/{id}/canaux`, évènement `dz-projet-canaux`) et glyphes des canaux dans l'hôte `data-dz-projet-canaux` de la barre « Projet » ; copie identique dans `frontend/dist/shared/`. La barre vit dans la couche `frontend/patches/montage.js` (aides `dzPcB`/`dzPcEc`, saisie `scripts/i18n_l3/montage_i.py` + miroir G1 `scripts/icones/g1_generer.py`, puis `refresh_layer --layer montage`) — aucun maillon de queue ; banc `test_projets_canaux_ecran` |
| `frontend/shared/dz-espace-assistant.js` | t308 (26/10/2026) : ASSISTANT de création d'espace en quatre temps (`window.__dzEspaceAssistant.ouvrir(opts)` : type et identité, fiche client, canaux avec « Vérifier » sans publication, récapitulatif ; « Terminer » active et émet `dz-espace-cree`) ; copie identique dans `frontend/dist/shared/`. « Créer l'espace » de Réglages › Espaces l'ouvre par le maillon de queue `scripts/patch_bundle_dzassistant.py` (inverse `avant_dzassistant`, en tête de `avant_dzagentplan`) ; banc `test_espace_assistant_ecran` |
| `backend/app/services/whatsapp_diffusions.py` | t328 (28/10/2026) : DIFFUSIONS WhatsApp d'un post du Planificateur par l'API Broadcasts de Kapso (`configurer` modèle approuvé, paramètres, audience = contacts à accord saisi, devis ; `lancer` un seul essai de send, jamais renvoyé sans relecture ; `relire`, `a_relire` pour `tick`) ; stockage `whatsapp_diffusions.json` du dossier de l'espace ; adaptateur `publishers.register("whatsapp")`. Routes `GET/PUT /api/schedule/{post_id}/diffusion` et `POST …/diffusion/confirmer` (`backend/app/api/routes.py`). Un compte WhatsApp n'est cible d'un post qu'en diffusion, jamais précoché dans les canaux par défaut d'un projet |
| `frontend/shared/dz-diffusion-whatsapp.js` (+ `frontend/shared/i18n/diffusion.json`, `scripts/patch_bundle_dzdiffusion.py`) | t328 : panneau « Diffusion WhatsApp » de l'inspecteur d'un post (`window.__dzDiffusionWhatsapp.monter`) : modèle, paramètres, audience, devis, « Enregistrer la diffusion », suivi, « Relire », « Confirmer l'envoi » derrière `__dzDialogue.confirmer` ; le patcher pose le canal WhatsApp dans la table des canaux, `DzPostComptes` et l'étiquette de routage ; copie identique dans `frontend/dist/shared/` |
| `backend/app/services/mesh_pieces.py` (+ `mesh_lod.ROLES`/`densites`, `frontend/etabli/jeu.js`, `jeu.css`, `frontend/shared/i18n/pieces3d.json`) | t342 (29/10/2026) : PIÈCES MOBILES d'un maillage (îlots soudés par position → un nœud nommé par pièce, origine au centre, matières/UV recopiées ; voie IA `tripo3d/tripo/segment` sur fal : clé 503 → `confirme_cout` 409 → `_plafond` « moteurs3d ») et BUDGETS DE TRIANGLES par rôle (trois densités gltfpack mesurées, dossier `densites/` du job). Routes `/api/etabli/pieces`, `/pieces/ia`, `/densites` (+ `/fichier`, `/zip`) ; outils d'agent `pieces_analyser`, `budgets_triangles` (boîte « assets3d », lecture). jeu.js est un module à part : etabli.js est régénéré par la traduction L8 (`i18n_l8_generer.py --check`), ne pas le retoucher à la main |
| `backend/app/services/comparatif3d.py` (+ `backend/app/api/comparatif3d_routes.py`, `frontend/studio3d/comparer.html`, `comparer.js`, `comparer_calc.js`, `comparer.css`, `frontend/shared/i18n/comparatif3d.json`) | t344 (29/10/2026, B9 Scenario) : BANC COMPARATIF des moteurs image → 3D. « tir » : une image, N moteurs (≥ 2) en un clic — 400 → clé fal / service local 503 → 409 sans `confirme_cout` (devis total) → `plafonds.juger` sur le TOTAL → `_plafond` par tir (réf. `asset3d:<job>`) → N jobs asset3d en parallèle ; « existants » : GLB déjà générés, gratuit. Tableau mesuré par la fiche de maillage (tris, arêtes ouvertes / non-manifold, étanche, octets, temps, coût estimé / réel), stocké dans `outputs/assets3d/_comparatifs/`. « Garder celui-ci » : vue capturée → Bibliothèque (source assets3d, relation « comparatif », recette). Routes `/api/comparatif3d` ; outil d'agent `comparatif3d_lire` (boîte « assets3d », lecture). Page à part du 3D Studio (studio3d.js est généré par L9 : ne pas y toucher), grille propre (pas dz-comparateur) ; bancs `test_comparatif3d`, `frontend/studio3d/qa/comparer.test.mjs` |
| `backend/app/services/previs_plan.py` (+ `backend/app/services/video_refs.py`, `frontend/shared/dz-previs-plan.js`, `frontend/shared/i18n/previs.json`, `scripts/i18n_l8/t335.py`) | t335 (28/10/2026, A5 du lot Scenario) : « Previs → plan » d'un plan du storyboard — clip de previs (@Video1) + 1 à 4 style frames (@Image1…) → Seedance 2.5 reference-to-video (fal, `task` editing/reference), ou style frames seules → Veo 3.1 références. `video_refs` reste PUR (registre, argument, prix (entrée + sortie) × tarif × 0,6, bornes du clip) ; `previs_plan` sonde le clip, propose le prompt, chiffre et tire (coutures `_upload`/`_fal_subscribe`/`_download`) ; t336 (29/10/2026, A6) : `plan_conform` (PUR, plancher `video_refs.plancher_s` : Seedance 4 s, MiniMax 5 s ; « etirer » ×k ≤ 2 sinon « noir », au choix `conform` du corps ; cadence/format transcodés), `conformer_clip` (prévu au devis, fabriqué par ffmpeg au tir AVANT la garde), `recaler` (conform défait, dérive mesurée par corrélation des bords Pillow en Python pur — pas de numpy embarqué —, nombre d'images exact de la previs ; rangé dans `cost_meta`/recette, relu par `/previs/sources` « dernier_rendu »), banc `test_previs_conform_recalage`. Routes `GET /api/shots/{id}/previs/sources`, `POST …/previs/devis` (gratuit), `POST …/previs` (503 clé → 400 → 409 sans `confirme_cout` → plafond « chapitres » → job « previs » rattaché au plan, vidéo dans la Bibliothèque relation « previs » + recette). Bouton `act-previs` de la carte (saisie L8), boîte `window.__dzPrevisPlan.ouvrir` ; copie identique dans `frontend/dist/shared/` ; bancs `test_chapitres_previs_plan`, `test_previs_plan_ecran` |
| `backend/app/services/revue_plan.py` (+ `frontend/shared/dz-revue-plan.js`, `frontend/shared/dz-comparateur.js`, `frontend/shared/i18n/revueplan.json`, `frontend/shared/i18n/comparateur.json`, `scripts/i18n_l8/t337.py`) | t337 (29/10/2026, A7 + C4 Scenario) : REVUE du dernier rendu Previs → plan — mesures gratuites (dérive résiduelle par `previs_plan.mesurer_derive`, structure bords sans pourtour + luminance 16², identity_drift ; profondeur NON mesurée, dit), avis « directeur artistique » Claude vision PAYANT (3 planches previs | rendu + style frame, devis, `confirme_cout` + `max_usd`, CoutChange, `tirer_garde` catégorie « chapitres », jamais une garantie), rangés dans cost_meta.revue du job ; routes GET /shots/{id}/revue, POST …/revue/mesurer, …/revue/devis, …/revue/note. COMPARATEUR commun `window.__dzComparateur.ouvrir({a, b, fps})` / `monter(hote, opts)` : rideau, O / C, ← → image par image, images et vidéos ; branché sur la revue, la boîte Previs → plan et la dérive de l'image de production (act-derive-cmp). Outil `lire_revue_plan` (boîte « chapitres »). Bancs `test_revue_plan`, `test_revue_plan_ecran`, `frontend/shared/qa/comparateur.test.mjs` |
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
