# Assistant « Demander à Deepotus » — conception (19/10/2026)

Branche `chantier/agent-guide`, depuis origin/main 8fbde2ed.
Inspiration : `farzaa/clicky` (AGENTS.md + assistant qui pointe à l'écran).

## But

Aider l'utilisateur à comprendre **comment se servir de DeepotusVideo** sans
quitter l'application : il pose une question, l'assistant répond en quelques
étapes, l'emmène au bon écran, **pointe le bouton** et ouvre le chapitre du
guide qui va avec.

Décisions prises avec l'utilisateur :

| Question | Décision |
|---|---|
| Forme | Tiroir « Demander » **et** pointeur à la Clicky |
| Pointage | Ancres nommées d'abord, vision (capture d'écran) en secours |
| Voix | Texte d'abord ; dictée + lecture dans un lot ultérieur |
| Connaissance | `AGENT.md` écrit à la main + registre d'ancres + résumé généré du guide |
| En plus | Un `AGENTS.md` à la racine pour les agents de code (lot A0) |

Hors périmètre : l'assistant **n'exécute aucune action payante** (génération,
rendu, publication) ; il montre et explique, l'utilisateur clique.

## Existant sur lequel on s'appuie

- Guide lisible par machine : `docs/guide/src/chapitres.json` (≈ 40 chapitres,
  `id`, `famille`, `fr`/`en`, `ecrans`), `jeveux.json` (intentions → chapitres),
  liens `/guide/#<chapitreId>`.
- Navigation : `deepotus:navigate` / `?view=<id>` ; vues
  `quick, studio, assets3d, episodes, sonvfx, montage, scheduler, templates,
  news, library, settings, vectorlab, photolab, avatarlive`.
- Réglages : `GET /api/reglages/index`, `dzOuvrirReglages(section)`.
- LLM : `moteurs_texte.tirer_garde` (estimation + `plafonds.verifier`), clés du
  coffre, Haiku par défaut (`config.ANTHROPIC_MODEL`).
- i18n : `dzT`, `frontend/shared/i18n/*.json` assemblés par
  `scripts/i18n_assembler.py`.
- Scripts globaux chargés par `frontend/dist/index.html` (`/shared/dz-plafonds.js`,
  `dialogue.js`…) : un tiroir global s'ajoute **sans patcher le bundle**.
- Aucun assistant, aucune route de chat, aucun AGENTS.md n'existent aujourd'hui.

## 1. Connaissance — `docs/agent/`

### `AGENT.md`
Mode d'emploi **pour l'assistant** (pas pour les développeurs) :

1. Qui est l'utilisateur (PRODUCT.md : fondateur solo, vidéos 9:16, clavier d'abord).
2. Carte des 14 écrans : rôle en une ligne, chapitre du guide associé.
3. Parcours types (« faire une vidéo en Quick », « brancher une clé »,
   « monter une séquence », « programmer une publication », « changer d'espace
   de marque »…), chacun en ≤ 5 étapes avec ancres.
4. Pièges fréquents : clé manquante (modèle choisissable mais 503 au lancement),
   plafond atteint (402 `dz_plafond`), espace de marque actif, langue.
5. Règles de réponse : langue de l'utilisateur ; ≤ 5 étapes ; ne citer **que**
   des ancres et chapitres existants ; ne jamais promettre un bouton absent ;
   ne jamais lancer d'action payante ; format des balises (§ 2).
6. « Tenir ce fichier à jour » : toute fonctionnalité livrée ajoute sa ligne,
   ses ancres et son chapitre (comme la section *Self-Update* de Clicky).

### `ancres.json`
```json
[{ "id": "quick.generer", "ecran": "quick", "selecteur": "[data-dz-ancre='quick.generer'], button…",
   "cadre": null, "fr": "Bouton Générer", "en": "Generate button" }]
```
- `ecran` : une des vues ci-dessus ; `cadre` : chemin du lab en iframe
  (`/vectorlab/`…) ou `null`.
- `selecteur` : on privilégie un attribut stable ; à défaut un sélecteur relevé
  sur la page réelle.
- Premier jeu : ≈ 30 ancres (Quick, Studio, Montage, Réglages, Bibliothèque).
- Ancres spéciales sans sélecteur : `reglages.<section>` ouvre la rubrique via
  `dzOuvrirReglages`.

## 2. Serveur

`backend/app/services/agent_aide.py` + `backend/app/api/agent_routes.py`.

- `POST /api/agent/demander`
  `{question, historique[≤ 10], ecran, lang, image?}` →
  `{texte, actions:[{type, cible, libelle}], moteur, cout_estime}`.
- Système assemblé : `AGENT.md` + résumé `chapitres.json`/`jeveux.json` (titre
  et écrans, dans la langue) + ancres de l'écran courant (toutes les ancres en
  liste courte) + espace de marque actif (nom seulement) + langue. Préfixe
  stable pour profiter du cache de prompt.
- Appel : `tirer_garde(..., categorie="aide")`. Nouvelle catégorie **« aide »**
  dans `plafonds.CATEGORIES`. Moteur réglable dans Réglages › Défauts
  (clé `reglages.defauts.agent`), Haiku par défaut.
- Balises de sortie, analysées côté serveur :
  - `[POINT:<ancre>]` → `{type:"point"}`
  - `[ALLER:<vue>]` → `{type:"aller"}`
  - `[GUIDE:<chapitre>]` → `{type:"guide"}`
  - `[VOIR]` → `{type:"voir"}` (demande de capture, § vision)
  - `[POINT:x,y:<libellé>]` → uniquement en réponse à un appel avec image.
  Ancre, vue ou chapitre inconnus : balise **retirée**, compteur journalisé.
  Le texte rendu ne contient plus aucune balise.
- `GET /api/agent/etat` → moteur, clé présente, nombre d'ancres, vision
  disponible.
- Garde : routes en localhost comme le reste ; question bornée (2 000 car.),
  historique borné.

### Vision en secours
1. Le modèle répond `[VOIR]` quand aucune ancre ne convient.
2. Le tiroir **demande** à l'utilisateur (coût estimé affiché).
3. Capture dans la page (canvas de la zone visible), réduite à ≤ 1280 px.
4. Second `POST /api/agent/demander` avec `image` → `[POINT:x,y:libellé]` en
   coordonnées de la capture, converties en coordonnées écran par le tiroir.
Seuls les moteurs capables de vision sont proposés ; sinon le tiroir le dit.

## 3. Interface

`frontend/shared/dz-agent.js` (+ copie identique `frontend/dist/shared/`),
chargé par `frontend/dist/index.html` comme `dz-plafonds.js`.

- Bouton flottant « ? Demander » + raccourci **F1** → tiroir à droite.
- Style Editorial Lab (DESIGN.md / PRODUCT.md) ; libellés via `dzT`
  (`frontend/shared/i18n/agent.json`).
- Sous chaque réponse : boutons « Y aller », « Montre-moi », « Ouvrir le
  guide », construits depuis `actions`.
- Historique en `sessionStorage` (`dz_agent_hist`), envoyé seulement au moteur
  choisi.

### Pointeur
- Calque fixe au-dessus de tout : curseur lumineux qui suit une **courbe de
  Bézier** jusqu'à la cible, puis halo + bulle avec le libellé (≈ 3 s, ou
  jusqu'au clic).
- Cible sur un autre écran : `deepotus:navigate`, puis attente de l'élément
  (≤ 4 s, `MutationObserver`).
- Labs en iframe : `frontend/shared/dz-agent-cadre.js`, ajouté aux labs,
  répond par `postMessage` à `{dzAgent:"trouve", selecteur}` avec le rectangle
  de l'élément ; le calque compose avec la position de l'iframe. Origine
  vérifiée (même origine uniquement).
- Respect de `prefers-reduced-motion` : saut direct au halo.

## 4. Erreurs

| Cas | Comportement |
|---|---|
| Pas de clé pour le moteur | Message « Brancher une clé » + pointage `reglages.cles` (sans LLM) |
| Plafond « aide » atteint | 402 → confirmation habituelle (`X-DZ-Plafond: confirme`) |
| Ancre introuvable dans la page | « Je ne trouve pas ce bouton ici » + chapitre du guide |
| Moteur sans vision et `[VOIR]` | Le tiroir le dit et propose le guide |
| Erreur réseau / moteur | Message clair, question conservée pour réessayer |

## 5. Tests

- `backend/tests/test_agent_connaissance.py` : chaque chapitre cité dans
  `AGENT.md` existe dans `chapitres.json` ; chaque ancre citée existe dans
  `ancres.json` ; chaque `ecran` est une vue connue.
- `backend/tests/test_agent_balises.py` : analyse des balises (valides,
  inconnues retirées, texte hostile, balises imbriquées, coordonnées hors
  image).
- `backend/tests/test_agent_routes.py` : `demander` avec moteur simulé, garde
  plafond (`test_plafonds_garde` doit rester vert), bornes d'entrée.
- `backend/tests/test_agent_ancres_reelles.py` : sur le backend de preuve 8799,
  chaque sélecteur d'`ancres.json` trouve exactement un élément.
- Copies identiques `frontend/shared/dz-agent*.js` ↔ `frontend/dist/shared/`.
- Dictionnaire i18n complet FR/EN.
- Preuve à l'écran FR et EN : question → réponse → « Montre-moi » → curseur sur
  le bouton, y compris dans un lab en iframe.

## 6. Lots

| Lot | Contenu |
|---|---|
| A0 | `AGENTS.md` racine pour les agents de code (+ `CLAUDE.md` qui y renvoie) |
| A1 | `docs/agent/AGENT.md` + `ancres.json` + tests de cohérence |
| A2 | Service + routes + catégorie de plafond « aide » + réglage du moteur |
| A3 | Tiroir, F1, boutons d'action, i18n |
| A4 | Pointeur (courbe, halo, navigation, iframes) |
| A5 | Vision en secours |
| A6 | Voix : dictée (micro navigateur) + lecture par le TTS existant |
| A7 | Chapitre du guide « Demander à Deepotus » (skill guide-deepotus) |

### A0 — `AGENTS.md` racine
Sur le modèle de Clicky : Vue d'ensemble · Architecture (backend FastAPI,
bundle `frontend/dist` patché par `scripts/patch_bundle_*.py`, labs en pages
autonomes, `/shared`) · Fichiers clés · Lancer et tester (python embarqué,
backend de preuve 8799, `repatch_all.py`, `run-tests.ps1`) · Conventions
(français langue de référence, `dzT`, plafonds sur toute route payante,
copies identiques `dist/shared`, jamais reconstruire `dist` depuis `src`) ·
Git (branches `chantier/*`/`claude/*`, PR, installation vérifiée par
`git hash-object`) · Tenir ce fichier à jour.
`CLAUDE.md` à la racine renvoie vers `AGENTS.md` (pas de lien symbolique sous
Windows).

## Risques

- **Sélecteurs fragiles** dans un bundle minifié patché : on ajoute des
  attributs `data-dz-ancre` par patch quand c'est possible, et le test sur
  8799 casse dès qu'une ancre disparaît.
- **Dérive de `AGENT.md`** : tests de cohérence + section « tenir à jour » +
  ligne dans la checklist du skill guide-deepotus.
- **Coût** : Haiku + cache du préfixe ; vision seulement après accord explicite.
