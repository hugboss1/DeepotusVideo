# t308 — Assistant de création d'espace et vérification des canaux : plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** créer un espace devient un assistant en quatre temps (type et identité, fiche client, canaux, récapitulatif).
Chaque canal se **vérifie sans rien publier**. Le résultat (vert, orange avec la raison, rouge) est enregistré avec sa
date, il est visible dans Réglages › Espaces, et le Planificateur signale un canal non vérifié.

**Architecture :**
- Un service neuf, `backend/app/services/verif_canaux.py`, fait un appel de lecture par plateforme sous
  `comptes.sous_compte(cid)` :
  - X : `users/me` ;
  - Telegram : `getMe` puis `getChat` ;
  - YouTube : `channels?mine=true` ;
  - Instagram : `/{ig-id}?fields=username` ;
  - TikTok : `user/info`.

  Il ne publie **jamais** (contrairement à `/api/channels/test` pour Telegram, qui envoie un message ; cette route ne
  change pas). Il rend `{etat, raison, date, id_distant, nom_distant}`.
- `comptes.py` range le dernier résultat par compte dans `comptes.json`, sous une clé de premier niveau
  `verifications`. Cela vaut aussi pour les comptes historiques. La vue d'un compte le porte (`verification`). Réécrire
  un identifiant efface la vérification, devenue périmée.
- Le résultat fixe aussi le **`canal_id`** du canal, `<plateforme>:<id distant>` (§11 bis). C'est la clé des
  consentements (t306). Le récapitulatif s'en sert pour dire quels consentements manquent.
- Un compte peut être **porté par le téléphone** (§11 bis) : le PC ne lit jamais ses jetons, et « Vérifier » rend la
  dernière déclaration du téléphone. t308 pose le modèle et le service, sans route ouverte au téléphone : cette écriture
  viendra avec L4.2 (§10).
- À l'écran :
  - l'assistant est une boîte de dialogue partagée, `frontend/shared/dz-espace-assistant.js` ;
  - un maillon de queue neuf, `dzassistant`, branche cette boîte sur « Nouvel espace » dans Réglages › Espaces ;
  - le même maillon ajoute « Vérifier » et la pastille d'état dans `DzComptesEspace`, et le signal « non vérifié »
    dans `DzPostComptes` du Planificateur.

  Ces composants sont posés par le maillon `dzespace`. Ce maillon n'est **pas** dans une couche à égalité d'octets
  (comme le bloc MONTAGE) : on vérifie ce point à l'étape 1 de la tâche 4.

**Tech Stack :** Python embarqué, FastAPI, httpx (et tweepy pour X), bancs autonomes avec des appels réseau remplacés ;
SPA patchée par une chaîne de maillons ; scripts partagés `frontend/shared` (copie identique dans `frontend/dist/shared`) ;
`dzT`.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §5.3, §5.5 (consentement par canal) et §11 bis
(`canal_id`, canal porté par le téléphone). Feuille de route : `docs/superpowers/plans/2026-10-25-boite-a-outils.md`,
t308.

## Global Constraints

- Python : `$PY = $env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. On lance les bancs depuis `backend/` ;
  chaque banc insère `backend/` lui-même et pose un `DEEPOTUS_DATA_DIR` temporaire, avec les clés vidées. **Aucun banc
  ne touche le réseau** : les appels HTTP sont remplacés, comme dans `test_diagnostic`.
- Français partout, ajouts datés `t308 (26/10/2026)`, commits `<zone> : <quoi> (t308)`.
- Une vérification **ne publie rien, ne dépense rien et n'envoie aucun message**. Aucune valeur secrète n'apparaît
  dans un résultat, un journal, une URL de réponse ou un message d'erreur (`_sans`/`_scrub`, comme dans
  `diagnostic.py`).
- États : `vert` (le compte répond et on lit son identité), `orange` (indéterminé : réseau, HTTP 5xx ou 429, champ
  requis manquant, TikTok non audité ; la raison est dite), `rouge` (refusé : 401/403, jeton invalide, chat
  introuvable). Un canal sans vérification est « non vérifié ». Il reste **enregistrable**.
- `canal_id` = `<plateforme>:<id distant>`, avec l'expression de t306 (`fiche_client.CANAL_ID`). Ce n'est jamais un
  identifiant de compte `c…`.
- Les routes qui lisent des secrets passent par `_require_localhost`. Un appareil appairé reçoit un 403
  (`_garde_ecritures_locales`). `_ECRITURES_OUVERTES` ne grandit pas.
- `espaces.lire()` migre et écrit : jamais depuis une boucle de fond.
- Messages neufs qui remontent à l'écran : `scripts/i18n_l10_traductions.json` (indentation 1 espace, CRLF, ordre
  d'origine), puis `PYTHONUTF8=1 $PY scripts/i18n_l10_erreurs.py` ; `--check` doit rester propre.
- Écran :
  - aucune chaîne en dur (`dzT`, FR et EN ; une phrase FR = une traduction, on cherche d'abord le texte FR existant) ;
  - les icônes viennent de Deepotus Glyph (glyphes `dz-reseau-*` pour les plateformes), jamais d'emoji ;
  - les angles des boîtes sont vifs, et un bouton posé parmi d'autres suit ses voisins (précédent t307).
- Bundle :
  - il n'est jamais reconstruit ; on le lit et on l'écrit en octets (helpers `lire`/`ecrire` de
    `patch_bundle_montage.py`) ;
  - le maillon de queue neuf ajoute son inverse dans `backend/tests/_i18n_l1_aide.py`, appelé en tête de l'inverse
    du maillon de queue actuel le plus récent ;
  - `version` reste le dernier maillon ;
  - **aucune écriture dans un bloc de couche à égalité d'octets** (MONTAGE, SON-VFX…) : si une cible y vit, on
    prend la voie de la couche (t307 : saisie L3 et compensation G1), après décision du contrôleur.
- Preuve à l'écran sur un backend de preuve (port 8799 ou voisin libre, données temporaires, aucune clé), **jamais
  8765**.
- Série ciblée avant chaque commit :
  - neufs : `test_verif_canaux`, et `test_espace_assistant_ecran` pour les tâches 4 et 5 ;
  - existants : `test_espaces_comptes`, `test_espaces_socle`, `test_espaces_onboarding`,
    `test_espaces_type_client`, `test_espaces_scheduler`, `test_diagnostic`, `test_i18n_l10`, `test_projets_canaux` ;
  - pour les tâches 4 et 5 en plus : `test_i18n_l0`, `test_i18n_l1`, `test_i18n_l2`, `test_agent_catalogue`.

  Rouges préexistants sur `origin/main` 2330b389 : `test_espaces_client` (ancre `dzespace` x0), `test_icones_g1` 3.5.

## Review Focus

1. **Un jeton dans une erreur.** Un 401 de TikTok, Telegram (le jeton est dans l'URL `bot<jeton>`) ou Instagram (le
   jeton est dans la query) remonte avec un texte qui ne contient aucune valeur secrète du compte. Bancs dans la
   tâche 1.
2. **Le compte change après la vérification.** Réécrire un champ (secret ou public) efface la vérification, et la vue
   redevient « non vérifié ». Banc dans la tâche 2.
3. **Telegram ne reçoit aucun message.** `verifier` n'appelle jamais `sendMessage` ni
   `marketing.publish_telegram`. Banc dans la tâche 1 (le faux client refuse toute URL `send*`).
4. **Un client sans `canal_id`.** Le récapitulatif d'un espace client dit « consentement manquant » pour un canal
   jamais vérifié (`canal_id` inconnu), au lieu de le croire couvert. Banc dans la tâche 3.
5. **Le téléphone porte le canal.** Un compte porté par le téléphone ne lit jamais ses secrets à la vérification, même
   si un secret du même nom existe au coffre. Banc dans la tâche 2.

---

### Task 1 : le service de vérification sans publication (t308)

**Files :**
- Create : `backend/app/services/verif_canaux.py`
- Create : `backend/tests/test_verif_canaux.py`

**Interfaces :**
- Consumes :
  - `comptes.sous_compte(cid)`, `comptes.cred`, `comptes.disponible(p)`, `comptes.PLATEFORMES` ;
  - `youtube_publisher.access_token()`, `tiktok_publisher.access_token()` et leurs `_scrub`,
    `instagram_publisher._graph()` ;
  - `marketing._x_client()` (tweepy `get_me`) ;
  - les aides `_res`/`_msg`/`_sans` de `diagnostic.py`, à **réemployer** par import, pas à recopier.
- Produces :
  - `async verif_canaux.verifier_plateforme(plateforme: str) -> dict`, appelé sous `sous_compte`. Il rend
    `{"etat": "vert"|"orange"|"rouge", "raison": str, "id_distant": str|None, "nom_distant": str|None}`.
  - Valeurs par plateforme :
    - X : `id_distant` = `data.id`, `nom_distant` = `@username` ;
    - Telegram : `getMe` doit être `ok`, puis `getChat(chat_id=TELEGRAM_CHAT_ID)` ; `id_distant` = l'id du chat,
      `nom_distant` = son titre ou `@username` ;
    - YouTube : `id_distant` = `items[0].id`, `nom_distant` = `snippet.title` ;
    - Instagram : `id_distant` = l'id rendu, `nom_distant` = `@username` ;
    - TikTok : `GET /v2/user/info/?fields=open_id,display_name` ; `id_distant` = `open_id`, `nom_distant` =
      `display_name`. Si `TIKTOK_AUDITED` est faux, c'est `orange` avec la raison « compte non audité : publication
      privée seulement ».
  - Champs requis manquants (`not disponible(p)`) : `orange`, raison « identifiants incomplets : <champs> » (les
    noms des champs, jamais leurs valeurs).
  - Toute exception devient `orange` (réseau) ou `rouge` (refus), et ne remonte jamais.
  - Hooks remplaçables au banc : `verif_canaux._get(url, headers=None, params=None)` et `verif_canaux._x_me()`.

- [ ] **Étape 1 : écrire `test_verif_canaux.py`.**
  - Pour chaque plateforme, trois cas avec de faux hooks : vert (identité lue), rouge (401) et orange (500, puis
    exception réseau). On vérifie `id_distant` et `nom_distant`.
  - Review Focus 1 : on pose des secrets reconnaissables (`SECRET-TG-123`…) et on fait renvoyer au faux hook une
    erreur qui les contient (URL Telegram, query Instagram) ; aucune sortie ne contient ces valeurs.
  - Review Focus 3 : le faux `_get` lève une erreur sur toute URL qui contient `/send` ; Telegram passe.
  - Champs manquants : `orange` avec les noms des champs.
  - TikTok non audité : `orange`.
- [ ] **Étape 2 : lancer.** On attend un FAIL (module absent).
- [ ] **Étape 3 : implémenter** `verif_canaux.py`. Docstring daté, sans dupliquer les aides de `diagnostic.py`.
- [ ] **Étape 4 : lancer** `test_verif_canaux`, puis `test_diagnostic` (qui doit rester vert).
- [ ] **Étape 5 : commit.** `canaux : vérification sans publication par plateforme (t308)`.

### Task 2 : la vérification enregistrée, le canal porté par le téléphone et la route (t308)

**Files :**
- Modify : `backend/app/services/comptes.py`, `backend/app/services/verif_canaux.py`, `backend/app/api/routes.py`
  (après `delete_compte`)
- Modify : `scripts/i18n_l10_traductions.json`, puis lancer `scripts/i18n_l10_erreurs.py`
- Test : `backend/tests/test_verif_canaux.py`

**Interfaces :**
- Consumes : la tâche 1 (`verifier_plateforme`).
- Produces :
  - `comptes.noter_verification(cid: str, res: dict) -> dict` range `{etat, raison, date (ISO secondes),
    id_distant, nom_distant}` dans `doc["verifications"][cid]` (une clé de premier niveau de `comptes.json`, créée à
    la volée ; `_lire` la tolère absente). Cela vaut aussi pour `historique-<p>`. La fonction rend la vérification
    rangée.
  - `comptes.canal_id(vue: dict) -> str | None` rend `f"{plateforme}:{id_distant}"` si la vérification porte un
    `id_distant` qui passe `fiche_client.CANAL_ID`, sinon `None`.
  - `_vue` et `_historiques` portent `"verification": <dict ou None>` et `"canal_id": <str ou None>`.
  - Effacement : `poser(cid, …)` retire `verifications[cid]` dès qu'il écrit un champ, et `supprimer(cid)` le
    retire aussi. Un compte historique reste lié aux clés plates : son effacement à la réécriture de ces clés n'est
    pas demandé, on le note en commentaire.
  - **Canal porté par le téléphone** : une entrée de compte peut porter `"porte_par": {"appareil_id": str,
    "appareil_nom": str, "verifie_le": ISO|None, "etat": "vert"|"orange"|"rouge"|None, "id_distant": str|None}`.
    - `comptes.porter_par_telephone(cid, declaration: dict) -> dict` est un service seulement, **sans route** :
      l'écriture du téléphone viendra en L4.2. Il valide les champs, refuse un compte historique
      (`CompteHistorique`) et rend la vue.
    - La vue porte `"porte_par"`, sans aucune valeur secrète.
  - `async verif_canaux.verifier(cid: str) -> dict` :
    - si le compte est porté par le téléphone : aucun appel réseau, aucune lecture de secret ; la raison est
      « porté par le téléphone, vérifié le <date> » ou « porté par le téléphone, jamais vérifié » (`orange`), et
      l'`id_distant` vient de la déclaration ;
    - sinon : `with comptes.sous_compte(cid): verifier_plateforme(p)`.

    Dans les deux cas, il finit par `noter_verification`, puis rend la vue du compte relue.
  - Route `POST /api/comptes/{compte_id}/verifier` :
    - passe par `_require_localhost` ;
    - un compte inconnu donne un 404 par `_compte_erreur` ;
    - elle rend `{"compte": <vue>}`.

- [ ] **Étape 1 : écrire les bancs** (dans `test_verif_canaux.py`, section « enregistrée ») :
  - aller-retour `noter_verification` → la vue porte `verification` et `canal_id` ;
  - Review Focus 2 : `poser` efface la vérification ;
  - `supprimer` la retire ;
  - historique : la vérification est rangée et relue ;
  - Review Focus 5 : un compte porté par le téléphone, avec un secret posé au même nom, ne déclenche aucun appel
    (le faux `_get` lève une erreur s'il est appelé) et ne lit aucun secret (`comptes._valeur_secrete` remplacé par une
    fonction qui lève) ; la raison contient la date de la déclaration ;
  - route : 200 avec la vue, 404 si le compte est inconnu, 403 avec le jeton d'un appareil appairé (même méthode que
    le banc 3g de t307), jamais de secret dans la réponse ;
  - `canal_id` rejette un `id_distant` qui ne passe pas `CANAL_ID`.
- [ ] **Étape 2 : lancer.** On attend un FAIL.
- [ ] **Étape 3 : implémenter.** Ajouter les messages neufs à L10 et lancer le générateur, puis `--check`.
- [ ] **Étape 4 : lancer** la série ciblée, en particulier `test_espaces_comptes` : le format de la vue s'élargit,
  rien ne doit casser.
- [ ] **Étape 5 : commit.** `canaux : vérification datée par compte, canal porté par le téléphone (t308)`.

### Task 3 : le récapitulatif d'un espace et les raisons d'import en deux langues (t308)

**Files :**
- Modify : `backend/app/services/espaces.py` (ou un module neuf `backend/app/services/recap_espace.py` si
  `espaces.py` grossit trop : au choix de l'implémenteur, justifié dans le rapport), `backend/app/api/routes.py`
- Modify : `backend/app/services/espaces_paquet.py` (les raisons d'`ignores`, report de t306)
- Modify : `scripts/i18n_l10_traductions.json` (et son générateur)
- Test : `backend/tests/test_verif_canaux.py` (section « récapitulatif ») ; le banc existant de l'import (il faut le
  retrouver : `test_espaces_type_client` porte les `ignores` de t306)

**Interfaces :**
- Consumes : `comptes.lister(eid)` (avec `verification`, `canal_id`), `fiche_client.lire(eid)`,
  `fiche_client.consentement_en_cours(eid, canal_id)` (t306 : on vérifie la signature réelle),
  `espaces.client_responsable(eid)`.
- Produces :
  - `recapitulatif(eid: str) -> dict` :

    ```
    {"espace_id", "type", "client_responsable": eid|None, "mode_publication": str|None,
     "canaux": [{"compte": id, "plateforme", "libelle", "etat": "vert"|"orange"|"rouge"|"non_verifie",
                 "verifie_le": ISO|None, "canal_id": str|None,
                 "consentement": "en_cours"|"manquant"|"sans_objet"}],
     "manques": {"non_verifies": int, "consentements": int}}
    ```

    - `consentement` vaut `sans_objet` si l'espace n'a pas de client responsable.
    - Il vaut `manquant` si `canal_id` est `None` (Review Focus 4) ou si aucun consentement ne court pour ce `canal_id`.
    - Un produit suit son client (§11 bis) : le mode et les consentements sont ceux du client responsable.
  - Route `GET /api/espaces/{eid}/recapitulatif` : lecture seule ; un espace inconnu donne un 404.
  - Les raisons d'`ignores` d'`espaces_paquet.py` passent par le mécanisme L10 (FR/EN). On relève d'abord comment
    L10 traite un message à valeurs interpolées (dans `scripts/i18n_l10_erreurs.py`). S'il ne sait pas le faire, on
    décompose en message fixe et valeur entre guillemets, sans perdre d'information.

- [ ] **Étape 1 : écrire les bancs :**
  - espace marque : `sans_objet` partout ;
  - client avec un canal vérifié et un consentement en cours → `en_cours` ;
  - client avec un canal vérifié sans consentement → `manquant` ;
  - client avec un canal non vérifié → `manquant` et `non_verifie` (Review Focus 4) ;
  - produit rattaché au client → mode et consentements du client ;
  - route 200 et 404 ;
  - `ignores` : chaque raison a sa traduction anglaise (`--check` L10 propre).
- [ ] **Étape 2 : lancer.** On attend un FAIL.
- [ ] **Étape 3 : implémenter.**
- [ ] **Étape 4 : lancer** la série ciblée.
- [ ] **Étape 5 : commit.** `espaces : récapitulatif des canaux et des consentements, raisons d'import traduites (t308)`.

### Task 4 : l'assistant en quatre temps à l'écran (t308)

**Files :**
- Create : `frontend/shared/dz-espace-assistant.js` (et sa copie identique `frontend/dist/shared/`), chargé par
  `frontend/dist/index.html`
- Modify : `frontend/shared/i18n/espaces.json` (clés `espaces.assistant.*`), assemblé par `scripts/i18n_assembler.py`
- Create : `scripts/patch_bundle_dzassistant.py` (maillon de queue ; s'il en faut une, sa source dans
  `frontend/patches/`)
- Modify : `backend/tests/_i18n_l1_aide.py` (inverse `avant_dzassistant`, en tête de l'inverse du maillon de queue
  actuel le plus récent ; t307 n'en a pas ajouté : c'est `avant_dzagentplan`, à vérifier)
- Create : `backend/tests/test_espace_assistant_ecran.py`
- Modify : catalogue de l'assistant (skill `connaissance-agent`), `docs/agent/AGENT.md`, `ancres.json`, `AGENTS.md`

**Interfaces :**
- Consumes :
  - `POST /api/espaces` (création : on relève la forme exacte qu'accepte le serveur : nom, couleur, kit, type,
    parent) ;
  - `PUT /api/espaces/{id}/client` (t306) ;
  - `GET`/`POST /api/comptes`, `POST /api/comptes/{id}` (valeurs), les routes OAuth existantes par compte
    (`/api/oauth/youtube/start`, `/api/oauth/tiktok/start`, avec `compte`, comme `DzComptesEspace`) ;
  - `POST /api/comptes/{id}/verifier` (tâche 2) ;
  - `GET /api/espaces/{id}/recapitulatif` (tâche 3) ;
  - `GET /api/comptes` → `plateformes` (champs, requis, oauth).
- Produces :
  - `window.__dzEspaceAssistant.ouvrir(opts?)`, qui ouvre la boîte (angles vifs, charte de `dialogue.js`) en quatre
    temps, avec Précédent / Suivant et un fil d'étapes :
    1. **Type et identité** : nom, couleur, kit, type (marque, produit ou client), parent (pour un produit : la
       liste des marques et des clients). « Suivant » crée l'espace : une seule fois, ensuite il le modifie.
    2. **Fiche** : seulement pour un client (sinon on saute l'étape). Société, contact, pays, langue, mode de
       publication. Elle est écrite par `PUT …/client`.
    3. **Canaux** : une case par plateforme. Pour chaque plateforme cochée, les champs requis (les champs secrets en
       type mot de passe, jamais relus), ou « Connecter » pour OAuth ; puis « Vérifier », qui affiche la pastille
       (vert, orange avec la raison, rouge) et la date. On peut passer à l'étape suivante sans vérifier : le canal
       est marqué « non vérifié ».
    4. **Récapitulatif** : canaux et état, mode de publication, consentements manquants (« ajoutez le
       consentement du client pour ce canal dans sa fiche »). « Terminer » active l'espace et ferme la boîte.
  - L'événement `dz-espace-cree` (`detail` = id de l'espace) est envoyé à la fin, pour que les écrans se relisent
    (`deepotus:espace-refresh`, comme `dzEspActiver`).
  - Le maillon `dzassistant` fait que l'action « Nouvel espace » de `DzEspaces` appelle
    `__dzEspaceAssistant.ouvrir()`. Le reste de `DzEspaces` ne change pas. Le formulaire rapide existant reste
    joignable seulement si le relevé montre qu'un banc ou un écran en dépend ; sinon il est remplacé.
  - Clés `espaces.assistant.*` (FR, EN). On cherche d'abord les textes FR existants (`espaces.nouveau.*`,
    `commun.action.*`).

- [ ] **Étape 1 : relever.**
  - Le maillon de queue le plus récent et son inverse (note de mémoire `chaine-patchers-bundle` dans
    `C:\Users\olivi\.claude\projects\C--Users-olivi-DeepotusVideo\memory\`).
  - **Où vivent `DzEspaces`, `DzComptesEspace` et `DzPostComptes` dans le bundle** : sortie du maillon
    `dzespace` (milieu de chaîne) ou bloc d'une couche à égalité d'octets ? On mesure, comme t307.
    - Si l'une de ces cibles est dans un bloc de couche, ou si un banc interdit à un maillon de queue d'écrire dans
      la sortie de `dzespace` : on s'arrête avec le statut **BLOCKED**, les mesures et les chemins possibles. On ne
      contourne pas.
  - La forme de « Nouvel espace » aujourd'hui (bouton, formulaire, route).
  - Les jetons qu'un maillon aval compte (`x.useState(` 731, `v2.8.0` ×4, `DzTracks`, confirmations).

  On écrit ce relevé en tête du rapport.
- [ ] **Étape 2 : écrire `test_espace_assistant_ecran.py`.**
  - Le maillon s'applique une fois (`--check` est propre) et chaque ancre est unique.
  - L'aller-retour `avant_dzassistant` rend le bundle d'avant, octet pour octet. CRLF préservé
    (`count(b"\n") == count(b"\r\n")`).
  - Le script partagé est identique à sa copie de `dist`, et `index.html` le charge.
  - Sonde node du script avec un faux `fetch` :
    - l'étape 2 est sautée pour une marque ;
    - « Suivant » à l'étape 1 crée l'espace une seule fois (deux clics → un seul `POST`) ;
    - un champ secret n'est jamais prérempli depuis une réponse ;
    - « Vérifier » appelle `/verifier` et affiche l'état ;
    - le récapitulatif liste un consentement manquant pour un client.
  - Les clés `espaces.assistant.*` existent en FR et en EN.
- [ ] **Étape 3 : lancer.** On attend un FAIL.
- [ ] **Étape 4 : implémenter.** Script partagé, i18n, maillon et inverse, balise dans `index.html`. Ensuite
  `repatch_all.py --list` (ou son équivalent si les `.bak` manquent) et la chaîne des inverses doivent être verts, avec
  `version` en dernier.
- [ ] **Étape 5 : lancer** la série ciblée des tâches 4 et 5.
- [ ] **Étape 6 : preuve à l'écran** (backend de preuve, données temporaires, aucune clé, navigateur intégré, FR
  puis EN) :
  - créer un client « Oracle Club » avec sa fiche, puis cocher Telegram avec de faux identifiants ; « Vérifier »
    affiche rouge ou orange avec la raison, sans clé réelle ;
  - le récapitulatif montre « non vérifié » et le consentement manquant ;
  - « Terminer » active l'espace.

  Captures dans `docs/superpowers/specs/assets/2026-10-26-t308/`.
- [ ] **Étape 7 : catalogue de l'assistant** (skill `connaissance-agent`) : fiches de l'assistant et de
  « Vérifier », ancre, parcours dans `AGENT.md`. `test_agent_catalogue` et `catalogue.py --check` doivent être verts.
- [ ] **Étape 8 : commit(s).** `espaces : assistant de création en quatre temps (t308)` et
  `agent : l'assistant connaît la création d'espace guidée (t308)`.

### Task 5 : l'état de vérification dans Réglages › Espaces et au Planificateur (t308)

**Files :**
- Modify : `scripts/patch_bundle_dzassistant.py` (paires neuves du même maillon), `backend/tests/_i18n_l1_aide.py`
  (le même inverse lit les paires), `frontend/shared/dz-espace-assistant.js` (aide partagée de pastille, réemployée
  par l'assistant), `frontend/shared/i18n/espaces.json`
- Test : `backend/tests/test_espace_assistant_ecran.py`
- Modify : catalogue (skill `connaissance-agent`)

**Interfaces :**
- Consumes : `verification` et `canal_id` dans les vues de `GET /api/comptes` (tâche 2) ;
  `POST /api/comptes/{id}/verifier`.
- Produces :
  - `window.__dzEspaceAssistant.pastille(vue) -> HTMLElement`, qui rend la pastille d'état (glyphe Deepotus,
    couleur, titre au survol « vérifié le … : raison » ou « non vérifié »). Une seule aide sert aux trois écrans.
  - `DzComptesEspace` (Réglages › Espaces) : à côté de chaque compte, la pastille et un bouton « Vérifier », qui
    appelle la route et relit la liste.
  - `DzPostComptes` (éditeur de post du Planificateur) : un compte coché qui n'est pas `vert` porte la mention
    « non vérifié » (ou l'état) à côté de son libellé. Le Planificateur **signale** sans bloquer : la programmation
    n'est pas refusée en t308 ; l'application des règles client est le travail de t309.

- [ ] **Étape 1 : écrire les bancs** (sonde node et paires) : la pastille pour les quatre états ; le bouton
  « Vérifier » appelle la route ; le Planificateur affiche « non vérifié » pour un compte sans vérification et rien
  pour un compte vert ; l'aller-retour de l'inverse reste à l'octet.
- [ ] **Étape 2 : lancer.** On attend un FAIL.
- [ ] **Étape 3 : implémenter.**
- [ ] **Étape 4 : lancer** la série ciblée des tâches 4 et 5, ainsi que les bancs du Planificateur qui comptent des
  jetons dans `DzPostComptes` (on les trouve avec `rg "DzPostComptes" backend/tests`).
- [ ] **Étape 5 : preuve à l'écran** (FR et EN) : pastille et « Vérifier » dans Réglages › Espaces, « non vérifié »
  dans l'éditeur de post. Captures dans le même dossier.
- [ ] **Étape 6 : catalogue** (fiche « Vérifier » de Réglages › Espaces).
- [ ] **Étape 7 : commit.** `espaces : état de vérification des canaux dans les Réglages et le Planificateur (t308)`.
