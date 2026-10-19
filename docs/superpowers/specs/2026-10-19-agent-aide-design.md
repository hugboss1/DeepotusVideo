# Assistant « Demander à Deepotus » — conception (19/10/2026)

Mise à jour 19/10/2026 : reflète la livraison A0-A4 (A5, A6 et A7 restent à faire). Les sections décrivent ce qui est livré ; l'intention d'origine est conservée.

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
Objet `{version, note, ancres}`. Chaque ancre :
```json
{ "id": "quick.generer", "ecran": "quick", "selecteur": "button…", "libelle": "…",
  "texte": {"fr": "Générer", "en": "Generate"}, "partout": false, "reglages": null, "cadre": null,
  "fr": "Bouton Générer", "en": "Generate button" }
```
- Champs : `id`, `ecran`, `selecteur`, `libelle`, `texte{fr,en}` (texte visible servant à retrouver
  l'élément), `partout` (ancre du rail ou de la coque, valable sur tout écran), `reglages` (section à ouvrir),
  `cadre` (chemin du lab en iframe, `/vectorlab/`…, ou `null`), `fr`, `en` (libellés de la bulle).
- Il n'y a **pas** d'attribut `data-dz-ancre` : les sélecteurs sont relevés sur la page réelle (à la main, FR et EN).
- 54 ancres : 14 du rail, 11 de Réglages, 23 d'écrans (Quick, Studio, Montage, Bibliothèque) et 6 de labs (Vectorlab, Photolab), relevées FR et EN sur la page réelle.
- Les ancres de Réglages ouvrent la section (événement `dz-reglages-section` et `?section=`) **sans pointeur**,
  c'est voulu : la rubrique ouverte suffit.

## 2. Serveur

`backend/app/services/agent_aide.py` + `backend/app/api/agent_routes.py`.

- `POST /api/agent/demander`
  requête `{question, historique[≤ 10], ecran, lang, moteur}` →
  réponse `{texte, actions, moteur, nom, rejets, sans_cle}`. Trois formes d'action :
  `{type:"point", cible, ecran, selecteur, texte, cadre, reglages, partout, libelle, fr, en}`,
  `{type:"aller", cible}`, `{type:"guide", cible, fr, en}`.
- Système assemblé, dans cet ordre : `AGENT.md` + chapitres + « Je veux… » + **toutes** les ancres (celles de
  l'écran ou « partout ») + vues, puis le contexte (écran, espace de marque, langue) **en dernier**, borné à une
  ligne : le préfixe est identique d'une question à l'autre.
- Moteur : choisi dans le tiroir (`localStorage` `dz_agent_moteur`) ; en automatique Anthropic › OpenAI › Gemini ›
  premier configuré. Jamais de repli d'un moteur demandé vers un autre ; un modèle fautif est refusé.
- Appel : `tirer_garde(..., categorie="aide", effort="low")` avec `MAX_TOKENS` = 2000 (les moteurs qui raisonnent
  comptent la réflexion dans la sortie ; l'effort n'est appliqué que si le modèle l'accepte). Catégorie **« aide »**
  dans `plafonds.CATEGORIES`.
- Cache : seulement le cache implicite du préfixe chez OpenAI et Gemini. Pas de `cache_control` Anthropic pour
  l'instant (à faire plus tard).
- Balises de sortie, analysées côté serveur : `[POINT:<ancre>]`, `[ALLER:<vue>]`, `[GUIDE:<chapitre>]`. Inconnues :
  retirées et comptées (`rejets`). `MAX_ACTIONS` = 6, dédoublonnage ; AGENT.md demande ≤ 3 balises. Réponse faite
  seulement de balises : texte de repli (« Voici où regarder : »). Réponse vide sans action : message d'excuse et
  action guide `tour`.
- Sans moteur configuré : réponse sans LLM (`sans_cle: true`) avec pointage `reglages.cles` et guide `cles`.
- `GET /api/agent/etat` → `{moteur, moteurs[{moteur, nom, cout}], ancres, chapitres}`.
- Garde : localhost comme le reste ; question bornée (2 000 car.), historique borné.

### Vision en secours (A5, hors périmètre de la livraison A0-A4)
Prévu, non livré : `[VOIR]`, `[POINT:x,y]`, paramètre `image`, moteurs capables de vision.
1. Le modèle répond `[VOIR]` quand aucune ancre ne convient.
2. Le tiroir **demande** à l'utilisateur (coût estimé affiché).
3. Capture dans la page (canvas de la zone visible), réduite à ≤ 1280 px.
4. Second `POST /api/agent/demander` avec `image` → `[POINT:x,y:libellé]` en coordonnées de la capture.

## 3. Interface

`frontend/shared/dz-agent.js` (+ copie identique `frontend/dist/shared/`),
chargé par `frontend/dist/index.html` comme `dz-plafonds.js`. Fichiers livrés : `dz-agent.js` (tiroir),
`dz-agent-logique.js` (logique pure, testée sous node), `dz-agent-pointeur.js` (calque), `dz-agent-cadre.js` (labs).

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
  (sondage toutes les 150 ms pendant 4 s ; pas de `MutationObserver`).
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

Tests réels : `backend/tests/test_agents_md.py`, `test_agent_connaissance.py` (chapitres, ancres et écrans cités
existent), `test_agent_aide.py` (balises, moteur simulé, repli, `MAX_TOKENS`/effort), `test_agent_ecran.py`
(copies `frontend/dist/shared` identiques, i18n FR/EN, branchement) et `frontend/shared/qa/agent_logique.test.mjs`
(logique pure sous node). Le relevé des sélecteurs sur la page réelle a été fait à la main : il n'y a pas de banc
sur le backend de preuve (le script de service des preuves du guide est `scripts/guide/serve_guide.py`, port 8809,
et non plus 8799). Preuve à l'écran faite en FR et en EN, lab en iframe compris (halo vérifié sur le bon outil). Reste à faire : un test de sélecteurs automatisé.

## 6. Lots

| Lot | Contenu |
|---|---|
| A0 (livré) | `AGENTS.md` racine pour les agents de code (+ `CLAUDE.md` qui y renvoie) |
| A1 (livré) | `docs/agent/AGENT.md` + `ancres.json` + tests de cohérence |
| A2 (livré) | Service + routes + catégorie de plafond « aide » + réglage du moteur |
| A3 (livré) | Tiroir, F1, boutons d'action, i18n |
| A4 (livré) | Pointeur (courbe, halo, navigation, iframes) |
| A5 | Vision en secours |
| A6 | Voix : dictée (micro navigateur) + lecture par le TTS existant |
| A7 | Chapitre du guide « Demander à Deepotus » (skill guide-deepotus) |

### A0 — `AGENTS.md` racine
Sur le modèle de Clicky : Vue d'ensemble · Architecture (backend FastAPI,
bundle `frontend/dist` patché par `scripts/patch_bundle_*.py`, labs en pages
autonomes, `/shared`) · Fichiers clés · Lancer et tester (python embarqué,
backend de preuve `scripts/guide/serve_guide.py` (8809), `repatch_all.py`, `run-tests.ps1`) · Conventions
(français langue de référence, `dzT`, plafonds sur toute route payante,
copies identiques `dist/shared`, jamais reconstruire `dist` depuis `src`) ·
Git (branches `chantier/*`/`claude/*`, PR, installation vérifiée par
`git hash-object`) · Tenir ce fichier à jour.
`CLAUDE.md` à la racine renvoie vers `AGENTS.md` (pas de lien symbolique sous
Windows).

## Risques

- **Sélecteurs fragiles** dans un bundle minifié patché : les ancres sont relevées
  sur la page réelle et une ancre introuvable renvoie vers le guide. Un test automatisé de sélecteurs reste à faire.
- **Dérive de `AGENT.md`** : tests de cohérence + section « tenir à jour » +
  ligne dans la checklist du skill guide-deepotus.
- **Coût** : Moteur choisi par l'utilisateur + cache implicite du préfixe (OpenAI, Gemini) ; vision seulement après accord explicite.
