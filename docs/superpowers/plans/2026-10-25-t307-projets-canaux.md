# t307 — Projets orientés vers leurs canaux : plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** chaque projet de la Bibliothèque choisit ses canaux, c'est-à-dire des comptes de diffusion **de son
espace**. Tout ce qui naît pendant qu'il est le projet actif de son espace vise ces canaux par défaut.

**Architecture :**
- La table `library_projects` gagne une colonne `canaux`, qui contient une liste JSON d'identifiants de comptes
  `services/comptes.py`. C'est la même forme que `scheduled_posts.comptes` (t204), contrôlée par la même garde
  `comptes.verifier_cibles` (compte inconnu 404, compte d'un autre espace 409, forme 400).
- `library_projects.canaux_par_defaut(eid)` rend les canaux du projet actif de l'espace `eid`. Deux créateurs de
  posts s'en servent quand on ne leur donne aucune cible : `POST /api/schedule` et l'outil de l'agent
  `creer_brouillons`.
- À l'écran, une boîte de dialogue partagée (`frontend/shared/dz-projet-canaux.js`) choisit les canaux d'un
  projet. Un maillon de queue neuf, `dzcanaux`, ajoute dans la barre des projets de la Bibliothèque
  (`DzProjetsBar`) les icônes des canaux du projet et un bouton « Canaux ».

**Tech Stack :** Python embarqué, FastAPI, SQLAlchemy (auto-migration `ADD COLUMN`), bancs autonomes ; SPA patchée
par une chaîne de maillons ; scripts partagés `frontend/shared` (copie identique dans `frontend/dist/shared`) ; `dzT`.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §5.4. La feuille de route est dans
`docs/superpowers/plans/2026-10-25-boite-a-outils.md`, tâche t307.

## Global Constraints

- Python : `$PY = $env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. On lance les bancs depuis
  `backend/` ; chaque banc insère `backend/` lui-même et pose un `DEEPOTUS_DATA_DIR` temporaire, avec les clés vidées.
- Français partout, ajouts datés `t307 (25/10/2026)`, commits `<zone> : <quoi> (t307)`.
- Un canal de projet est un **identifiant de compte** de `comptes.py` (`c…` ou `historique-<plateforme>`), jamais
  un nom de plateforme. Un compte d'un autre espace que le projet est refusé (409). C'est la garde de t204, réutilisée
  et non réécrite.
- L'espace d'un projet est `p.espace_id or "deepotus"`. L'espace actif ne sert jamais de valeur par défaut pour
  juger un projet.
- `espaces.lire()` migre et écrit : jamais depuis une boucle de fond.
- Messages neufs qui remontent à l'écran : ils entrent dans `scripts/i18n_l10_traductions.json` (indentation
  1 espace, CRLF, ordre d'origine), puis on lance `PYTHONUTF8=1 $PY scripts/i18n_l10_erreurs.py`. `--check` doit
  rester propre.
- Écran : aucune chaîne en dur (`dzT`, FR + EN ; une phrase FR = une traduction, on cherche le texte FR existant
  avant d'en écrire un) ; les icônes viennent de la suite Deepotus Glyph (pas d'emoji) ; les angles sont vifs
  (DESIGN.md).
- Bundle : il n'est jamais reconstruit. On le lit et on l'écrit **en octets** (helpers `lire`/`ecrire` de
  `patch_bundle_montage.py`). Le nouveau maillon de queue ajoute son **inverse** dans
  `backend/tests/_i18n_l1_aide.py`, appelé en tête de l'inverse du maillon de queue actuel le plus récent. Le maillon
  `version` reste le dernier. Après tout rejeu, `python scripts/repatch_all.py --list` doit être entièrement `OK`.
- Preuve à l'écran sur un backend de preuve (port 8799 ou voisin, données temporaires, aucune clé), **jamais 8765**.
- Série ciblée avant chaque commit :
  - neufs : `test_projets_canaux`, et `test_projets_canaux_ecran` pour la tâche 4 ;
  - existants : `test_library_projets`, `test_library_projets_ecran`, `test_espaces_scheduler`,
    `test_espaces_comptes`, `test_agent_outils`, `test_agent_boucle`, `test_espaces_type_client`, `test_i18n_l10` ;
  - pour la tâche 4 en plus : `test_i18n_l0`, `test_i18n_l1`, `test_i18n_l2`.

  Les rouges préexistants sur `origin/main` 4074424f se notent, preuve à l'appui (ex. `test_espaces_client` : ancre
  `dzespace` x0).

## Review Focus

1. Un compte supprimé après avoir été choisi pour un projet : il disparaît de la vue du projet et des canaux par
   défaut, sans erreur (tâches 1 et 3).
2. Le projet actif de l'espace B ne sert jamais de défaut à un post de l'espace A (tâche 3).
3. Un créateur qui donne lui-même `channels` ou `comptes` n'est jamais écrasé par les canaux du projet (tâche 3).
4. Les comptes historiques (`historique-x`…) de Deepotus sont des canaux valides pour un projet Deepotus, et
   seulement pour lui (tâche 1).
5. La boîte de dialogue ne propose que les comptes de l'espace du projet, même quand un autre espace est actif
   (tâche 4).

---

### Task 1 : la colonne `canaux` et le service (t307)

**Files :**
- Modify : `backend/app/services/storage.py:396-412` : `LibraryProject.canaux: Mapped[Optional[str]] =
  mapped_column(Text, nullable=True)` ; `LIBRARY_PROJECTS_COLUMNS` (ligne ~804) gagne `("canaux", "TEXT")`
- Modify : `backend/app/services/library_projects.py` (`_vue`, `poser_canaux`, `canaux_par_defaut`, `_canaux_lus`)
- Create : `backend/tests/test_projets_canaux.py` (sections 1 et 2)

**Interfaces :**
- Consumes : `comptes.verifier_cibles(espace_id, ids) -> list[vue]` (KeyError, PermissionError, ValueError) ;
  `comptes.obtenir(cid)` ; `library_projects.cle_actif(eid)`.
- Produces :
  - `_canaux_lus(p) -> list[str]` : le JSON de `p.canaux`. Il ne garde que les identifiants dont `comptes.obtenir`
    réussit, sans jamais lever d'erreur.
  - `_vue(p, n)` gagne `"canaux": _canaux_lus(p)`.
  - `async poser_canaux(pid: str, ids) -> dict` : `KeyError(pid)` si le projet est inconnu. Les exceptions de
    `verifier_cibles(p.espace_id or "deepotus", ids)` remontent telles quelles. Il écrit
    `json.dumps([v["id"] for v in vues])`, ou `None` si la liste est vide, et rend `_vue(p)` relu.
  - `async canaux_par_defaut(eid: str) -> list[str]` : les canaux lus du projet actif de l'espace `eid`, avec la clé
    `cle_actif(eid)`. On ne passe **pas** par `actif()`, qui lit l'espace courant. Pas de projet actif → `[]`.

- [ ] **Étape 1 : écrire les sections 1 et 2 du banc.** Le banc suit le modèle de `test_espaces_scheduler.py` :
  data-dir temporaire, base SQLite temporaire, `storage.init_db()` exécuté, deux espaces (`deepotus` et un client
  `B` créé par `espaces.creer`), un compte X dans chaque espace (`comptes.creer`, avec les champs publics seulement
  ; voir `test_espaces_comptes.py` pour la forme).
  ```python
  # 1. poser et lire
  p = run(LP.creer("Lancement")) ; check("1a vue neuve : aucun canal", p["canaux"] == [])
  v = run(LP.poser_canaux(p["id"], [cx_deepotus]))
  check("1b canal posé", v["canaux"] == [cx_deepotus])
  check("1c historique admis pour Deepotus", run(LP.poser_canaux(p["id"], ["historique-x"]))["canaux"] == ["historique-x"])
  check("1d compte d'un autre espace refusé", _leve_async(PermissionError, LP.poser_canaux, p["id"], [cx_B]))
  check("1e compte inconnu refusé", _leve_async(KeyError, LP.poser_canaux, p["id"], ["c_inconnu"]))
  check("1f forme refusée", _leve_async(ValueError, LP.poser_canaux, p["id"], "cx"))
  check("1g projet inconnu", _leve_async(KeyError, LP.poser_canaux, "proj_00000000", []))
  check("1h liste vide = aucun canal", run(LP.poser_canaux(p["id"], []))["canaux"] == [])
  # compte supprimé après coup : disparaît sans erreur
  run(LP.poser_canaux(p["id"], [cx_deepotus])); comptes.supprimer(cx_deepotus)
  check("1i compte supprimé ignoré", run(LP.lister(espace="deepotus"))[0]["canaux"] == [])
  # 2. canaux par défaut
  check("2a aucun projet actif", run(LP.canaux_par_defaut("deepotus")) == [])
  # projet de B (créé sous espaces.sous_espace(B)) avec cx_B, posé actif pour B (clé cle_actif(B))
  check("2b défaut de B = canaux du projet actif de B", run(LP.canaux_par_defaut(B)) == [cx_B])
  check("2c Deepotus ne reçoit jamais le défaut de B", run(LP.canaux_par_defaut("deepotus")) == [])
  ```
  `run` = `asyncio.run` ; `_leve_async(exc, fn, *a)` est un utilitaire du banc. Pour poser le projet actif de B, on
  écrit la ligne `AtelierSetting(cle_actif(B))`, ou on appelle `poser_actif` dans `espaces.sous_espace(B)`. On
  vérifie le nom réel de ces aides dans le code avant d'écrire.
- [ ] **Étape 2 : lancer.** On attend un FAIL (`KeyError: 'canaux'` ou `AttributeError`).
- [ ] **Étape 3 : implémenter.** Colonne, auto-migration et fonctions. `lister`, `modifier`, `contenu` et `actif`
  ne changent pas de forme, en dehors de la clé ajoutée par `_vue`.
- [ ] **Étape 4 : lancer** `test_projets_canaux`, `test_library_projets` et `test_espaces_scheduler`. Ils doivent être
  verts. Si un banc existant fige la forme exacte de `_vue` (liste des clés), on met à jour son attente et on le
  dit dans le commit.
- [ ] **Étape 5 : mutations.** (a) Ne pas filtrer les comptes disparus : 1i rougit. (b) Juger l'espace avec
  l'espace courant au lieu de `p.espace_id` : 1d ou 2c rougit. On fait une copie avant, on restaure et on vérifie
  avec `cmp`.
- [ ] **Étape 6 : commit.** `projets : canaux d'un projet et canaux par défaut (t307)`.

### Task 2 : la route `PUT /api/library/projets/{pid}/canaux` (t307)

**Files :**
- Modify : `backend/app/api/routes.py`, après `library_modifier_projet` (~4328)
- Modify : `scripts/i18n_l10_traductions.json`, puis régénérer (messages neufs seulement)
- Test : `backend/tests/test_projets_canaux.py` (section 3)

**Interfaces :**
- Consumes : `LP.poser_canaux` (tâche 1).
- Produces : `PUT /api/library/projets/{pid}/canaux`, corps `{"canaux": [ids]}` → la vue du projet. On réutilise
  le corps de `_corps_objet`. Projet inconnu → 404 `Projet inconnu : <pid>`. Compte inconnu → 404 (même message
  que `_poser_comptes`). Autre espace → 409. Forme → 400. La garde d'écriture locale de `main.py` s'applique déjà :
  un appareil appairé reçoit 403 (on le prouve, on n'ajoute rien).

- [ ] **Étape 1 : écrire la section 3 du banc** (`TestClient(app)` local, puis
  `TestClient(app, client=("192.168.1.20", 50000))` avec `tests/_jeton_appareil.entetes(app)`) :
  ```python
  check("3a PUT 200 et vue relue", r.status_code == 200 and r.json()["canaux"] == [cx])
  check("3b autre espace 409", put(pid, [cx_B]).status_code == 409)
  check("3c compte inconnu 404", put(pid, ["c_inconnu"]).status_code == 404)
  check("3d projet inconnu 404", put("proj_00000000", []).status_code == 404)
  check("3e forme 400", client.put(f"/api/library/projets/{pid}/canaux", json={"canaux": "x"}).status_code == 400)
  check("3f GET /library/projets porte canaux", "canaux" in client.get("/api/library/projets").json()["projets"][0])
  check("3g appareil appairé : 403", lan.put(f"/api/library/projets/{pid}/canaux", json={"canaux": []}, headers=H).status_code == 403)
  ```
  Distinguer « projet inconnu » de « compte inconnu » : `poser_canaux` lève `KeyError(pid)` pour le projet, et
  `verifier_cibles` lève `KeyError(cid)`. La route regarde d'abord si le projet existe (lecture via `LP.contenu`, ou
  un petit `LP.existe(pid)` si c'est plus simple ; dire lequel).
- [ ] **Étape 2 : lancer.** On attend un FAIL (404 ou 405 sur la route absente).
- [ ] **Étape 3 : implémenter** la route et les messages L10.
- [ ] **Étape 4 : lancer** la série ciblée.
- [ ] **Étape 5 : commit.** `projets : route des canaux d'un projet (t307)`.

### Task 3 : les créateurs de posts héritent des canaux du projet actif (t307)

**Files :**
- Modify : `backend/app/api/routes.py` (création de post, ~8745 : après la pose de `p.espace_id`)
- Modify : `backend/app/services/agent_outils.py` (`creer_brouillons`, ~600-625)
- Test : `backend/tests/test_projets_canaux.py` (section 4)

**Interfaces :**
- Consumes : `LP.canaux_par_defaut(eid)` (tâche 1) ; `_poser_comptes(p, ids)` (routes.py, t204).
- Produces :
  - `POST /api/schedule` : si le corps n'a **ni** `comptes` **ni** `channels`, et que `canaux_par_defaut(p.espace_id)`
    n'est pas vide, on appelle `_poser_comptes(p, ces_ids)`. Les canaux du post suivent alors ses comptes. Sinon, le
    comportement d'avant ne change pas.
  - `creer_brouillons` : pour un post **sans** clé `canaux`, si les canaux par défaut de l'espace de la campagne
    (`_espace(ctx)`) ne sont pas vides, le brouillon reçoit `comptes` = ces ids et `channels` = leurs plateformes,
    dans l'ordre et sans doublon (`comptes.verifier_cibles`). Sinon, on garde le comportement d'avant (`["x"]`). Un
    post qui donne `canaux` garde ses canaux. Le résumé de l'outil dit `canaux du projet` quand ils ont servi.

- [ ] **Étape 1 : écrire la section 4 du banc.**
  ```python
  check("4a post sans cible → comptes du projet actif", post({"caption": "a"}).json()["comptes"] == [cx])
  check("4b channels donnés → rien d'hérité", post({"caption": "b", "channels": ["telegram"]}).json()["comptes"] == [])
  check("4c comptes donnés → gardés", post({"caption": "c", "comptes": ["historique-x"]}).json()["comptes"] == ["historique-x"])
  check("4d post de l'espace B → défaut de B, jamais celui de Deepotus", post({"caption": "d", "espace_id": B}).json()["comptes"] in ([], [cx_B]))
  # agent : appel direct à agent_outils.executer("creer_brouillons", {...}, Ctx(cid, espace_id=…, etat_porte="validee"))
  check("4e brouillon de l'agent sans canaux → comptes du projet", brouillon_sans_canaux_comptes == [cx])
  check("4f brouillon avec canaux → gardés", brouillon_avec_canaux_channels == "telegram")
  ```
  On fixe 4d à une valeur exacte une fois l'état du projet actif de B posé dans le banc. Pour 4e, on vérifie dans
  `test_agent_outils.py` comment une conversation est mise à l'état « porte validée ».
- [ ] **Étape 2 : lancer.** On attend un FAIL sur 4a et 4e.
- [ ] **Étape 3 : implémenter.** Une seule lecture de `canaux_par_defaut` par appel. Aucune lecture depuis une
  boucle de fond.
- [ ] **Étape 4 : lancer** la série ciblée, en particulier `test_espaces_scheduler`, `test_agent_outils` et
  `test_agent_boucle` (ils créent des posts et des brouillons sans projet actif : leur comportement ne doit pas
  changer).
- [ ] **Étape 5 : mutations.** (a) Hériter même quand `channels` est donné : 4b rougit. (b) Lire le défaut de
  l'espace courant au lieu de celui du post : 4d rougit.
- [ ] **Étape 6 : commit.** `projets : les posts et brouillons visent les canaux du projet actif (t307)`.

### Task 4 : l'écran — canaux dans la barre des projets (t307)

**Files :**
- Create : `frontend/shared/dz-projet-canaux.js` (et sa copie identique `frontend/dist/shared/dz-projet-canaux.js`),
  chargé par `frontend/dist/index.html` comme les autres scripts partagés
- Create : `frontend/shared/i18n/projets.json` (clés `projets.canaux.*`), assemblé par `scripts/i18n_assembler.py`
- Create : `frontend/patches/projet-canaux.js` (source de la couche), `scripts/patch_bundle_dzcanaux.py` (maillon
  de queue)
- Modify : `backend/tests/_i18n_l1_aide.py` (inverse `avant_dzcanaux`)
- Create : `backend/tests/test_projets_canaux_ecran.py` (banc du maillon, aller-retour, sonde node)
- Modify : `docs/agent/AGENT.md`, `docs/agent/ancres.json` et les fiches du catalogue (skill `connaissance-agent`) ;
  `AGENTS.md` (ligne `dz-projet-canaux.js` / maillon `dzcanaux`)

**Interfaces :**
- Consumes : `GET /api/library/projets` (`canaux` dans chaque vue) ; `PUT /api/library/projets/{pid}/canaux` ;
  `GET /api/comptes?espace=<id>`, la liste existante de comptes par espace (`list_comptes`, routes.py ~8451 : on
  vérifie la forme renvoyée) ; les icônes Deepotus Glyph des plateformes déjà utilisées par `DzPostComptes` (t204).
- Produces :
  - `window.__dzProjetCanaux.ouvrir(projet)` : `projet` = la vue du projet (`id`, `nom`, `espace_id`, `canaux`).
    Elle ouvre une boîte de dialogue qui liste **les comptes de l'espace du projet**, une case par compte (icône de
    plateforme, libellé, handle). Le bouton « Enregistrer » envoie le `PUT`, puis appelle l'événement
    `dz-projet-canaux` (`CustomEvent`, `detail` = la vue relue), pour que la barre se rafraîchisse. Les erreurs 409
    et 404 sont affichées dans la boîte, par `dzT`.
  - Le maillon `dzcanaux` ajoute à `DzProjetsBar` (défini dans le maillon `libsons`, **ne pas modifier ce
    maillon**) : (a) les icônes des canaux du projet sélectionné à côté de son nom, avec un titre au survol qui
    nomme les comptes ; (b) un bouton « Canaux » (icône Glyph, avec le libellé `dzT('projets.canaux.bouton')`) qui
    appelle `__dzProjetCanaux.ouvrir` ; (c) l'écoute de `dz-projet-canaux` pour relire la liste des projets.
  - Clés i18n (FR, EN) : `projets.canaux.bouton` (« Canaux » / « Channels »), `projets.canaux.titre`
    (« Canaux du projet {nom} » / « Channels of project {nom} »), `projets.canaux.aucun_compte`, `projets.canaux.enregistrer`,
    `projets.canaux.erreur_espace`. On cherche d'abord chaque texte FR dans `frontend/shared/i18n/*.json`, pour
    reprendre une traduction qui existe déjà.

- [ ] **Étape 1 : relever.**
  - le maillon de queue actuel le plus récent (avant `version`) et son inverse : lire `scripts/repatch_all.py
    --list` sur une copie du bundle installé si les `.bak` manquent dans le worktree, `backend/tests/_i18n_l1_aide.py`
    et la note de mémoire `chaine-patchers-bundle` dans
    `C:\Users\olivi\.claude\projects\C--Users-olivi-DeepotusVideo\memory\` (ainsi que `patcher-lit-le-bundle-en-octets`
    et `planificateur-debordement`) ;
  - la forme exacte de `DzProjetsBar` dans le bundle et le jeton qu'un maillon aval y compte peut-être.

  On écrit ce relevé en tête du rapport.
- [ ] **Étape 2 : écrire le banc `test_projets_canaux_ecran.py`.**
  - Le maillon s'applique une fois (`--check` est propre) et chaque paire d'ancres est présente une seule fois.
  - L'aller-retour `avant_dzcanaux` rend le bundle d'avant, octet pour octet.
  - CRLF préservé : `count(b"\r\n") > 15000` et `count(b"\n") == count(b"\r\n")`. Le patcher ne contient pas
    `read_text(`.
  - `frontend/shared/dz-projet-canaux.js` est identique à sa copie de `dist/shared`.
  - Sonde node de `dz-projet-canaux.js` avec un faux `fetch` : la boîte ne liste que les comptes de l'espace du
    projet (Review Focus 5), le `PUT` porte la bonne liste et un 409 affiche le message traduit.
  - Les clés `projets.canaux.*` existent en FR et en EN.
- [ ] **Étape 3 : lancer.** On attend un FAIL (maillon absent).
- [ ] **Étape 4 : implémenter.** Script partagé, i18n, couche, maillon, inverse dans `_i18n_l1_aide.py`, puis
  index.html charge le script. Ensuite, `repatch_all.py --list` doit être entièrement `OK`, avec `version` en
  dernier.
- [ ] **Étape 5 : lancer** la série ciblée de la tâche 4 (dont `test_i18n_l0`, `test_i18n_l1`, `test_i18n_l2`, qui
  défont les maillons de queue, et les bancs de la Bibliothèque).
- [ ] **Étape 6 : preuve à l'écran** sur un backend de preuve, port 8799 ou voisin, avec un `DEEPOTUS_DATA_DIR`
  temporaire et sans aucune clé, dans le navigateur intégré, en FR puis en EN. Créer deux espaces, chacun avec un
  compte, et un projet dans le premier. Puis : ouvrir « Canaux », cocher le compte, enregistrer, et voir l'icône à
  côté du projet. Vérifier que le compte de l'autre espace n'est pas proposé. Ranger les captures dans
  `docs/superpowers/specs/assets/2026-10-25-t307/`.
- [ ] **Étape 7 : catalogue de l'assistant.** Suivre le skill `connaissance-agent` : une fiche pour le bouton
  « Canaux » et la boîte de dialogue, l'ancre dans `ancres.json` et une phrase dans `AGENT.md`. Ses bancs
  (`test_agent_catalogue`, `catalogue.py --check`) doivent être verts.
- [ ] **Étape 8 : commit(s).** `projets : canaux dans la barre des projets (t307)` et
  `agent : l'assistant connaît les canaux d'un projet (t307)`.
