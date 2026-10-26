# t326 : petits défauts de l'assistant d'espace et de la vérification — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** corriger les sept défauts relevés à la relecture finale de t308 (fiche t326 du suivi), sans toucher au bundle.

**Architecture :** trois couches déjà en place depuis t308 : le service (`comptes.py`, `verif_canaux.py`), les routes (`routes.py` : `/settings/keys`, `_oauth_callback`) avec la traduction L10 à la sortie, et les scripts partagés chargés par `index.html` (`dz-espace-assistant.js`, `dz-projet-canaux.js`, `dz-champ-ia.js`). Aucun de ces scripts n'est dans le bundle : **le bundle `index-BEOJX8L5.js` n'est pas modifié par t326**.

**Tech Stack :** FastAPI/Python (python embarqué `%LOCALAPPDATA%/DeepotusVideoGen/runtime/python/python.exe`), JS vanilla ES5, bancs maison `backend/tests/test_*.py` (scripts `check(...)`, lancés depuis `backend/` avec `PYTHONUTF8=1`, un par un).

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` (§5.3, §5.5, §11 bis). Source des défauts : fiche t326 du suivi et `.superpowers/sdd/2026-10-26-t308-assistant-espace/final-review.md` (M-2, M-4, M-5, M-6) / `final-rereview.md` du worktree `boite-assistant-espace`.

## Global Constraints

- Base : `origin/main` 646b6d97. Branche `chantier/boite-petits-defauts`. Ne rien pousser.
- Aucun secret dans un résultat, un message, un journal ou une URL.
- Aucun appel réseau réel dans les bancs ni dans la preuve (backend de preuve sur **8799**, données temporaires, sans clé). Ne jamais toucher **8765**.
- Tout fichier de `frontend/shared/` modifié est recopié octet pour octet dans `frontend/dist/shared/` (`cmp` identique).
- Toute clé `dzT` neuve va dans `frontend/shared/i18n/espaces.json` (FR et EN), puis `python scripts/i18n_assembler.py` ; `dz-i18n-dico.js` shared == dist.
- Tout message serveur neuf passe par L10 : entrée dans `scripts/i18n_l10_traductions.json`, `python scripts/i18n_l10_erreurs.py` puis `--check` propre.
- Les commentaires de code sont en français, datés « t326 (26/10/2026) », dans le style des fichiers touchés.
- ~25 bancs sont déjà rouges sur main : toujours comparer base et HEAD, ne pas « réparer » un banc rouge sans lien.

## Review Focus

1. Un compte **historique** vérifié dont une clé plate est réécrite dans Réglages › Connected accounts : la pastille doit retomber à « non vérifié » et `canal_id` à None ; une vérification en vol à ce moment ne doit rien ranger (banc dans la tâche 1 et la tâche 2).
2. Une écriture de `/settings/keys` qui **échoue** (409 coffre verrouillé, clé refusée 400) ne doit pas effacer la vérification : on périme seulement après validation (banc tâche 2).
3. Le rappel OAuth où `oublier_verification` lève autre chose que KeyError (OSError d'écriture) : le jeton est rangé, la page est un succès qui demande de revérifier, jamais une 500 (banc tâche 2).
4. Tab et Maj+Tab dans les trois boîtes : le focus ne sort jamais de la boîte, y compris quand le focus est sur un élément hors boîte au moment du Tab, et seuls les éléments visibles et actifs sont parcourus (banc tâche 3).
5. Annuler / Échap à l'étape 1 **sans** espace créé ferme sans question ; après l'étape 1 la question apparaît, et « Continuer » ramène à l'étape où l'on était sans rien perdre (banc tâche 3).

---

### Task 1 : service — identité et date justes (défauts 2, 3, 4 côté service)

**Files :**
- Modify : `backend/app/services/comptes.py` (`revision`, `_perimer`, `oublier_verification`, `noter_verification`, nouvelle `perimer_historiques`)
- Modify : `backend/app/services/verif_canaux.py` (`_portee`, `verifier`)
- Test : `backend/tests/test_verif_canaux.py` (nouvelle section « t326 », bancs `T1..`)

**Interfaces :**
- Produces :
  - `comptes.revision(cid) -> str | None` : pour `historique-<p>` rend désormais `str(doc.get("rev_historiques", {}).get(p) or "")` (plus None) ; KeyError si `<p>` n'est pas dans `PLATEFORMES`.
  - `comptes._perimer(doc, cid)` : pour `historique-<p>`, change aussi `doc.setdefault("rev_historiques", {})[p]`.
  - `comptes.perimer_historiques(noms: list[str]) -> list[str]` : pour chaque nom de `noms` présent dans `_CHAMP_PLAT`, périme `historique-<plateforme>` (une seule écriture) ; rend les ids périmés triés. Ne lève pas pour un nom inconnu.
  - `comptes.noter_verification(cid, res, rev=None)` : garde de révision aussi pour un historique ; `date` = `res["date"]` si c'est une chaîne ISO lisible par `datetime.fromisoformat` (rendue `isoformat(timespec="seconds")`), sinon maintenant.
  - `verif_canaux._portee(pp)` : pour `telephone_verifie`, le résultat porte `date = pp["verifie_le"]`.
  - `verif_canaux.verifier(cid) -> dict` : quand `noter_verification` rend None (garde de révision), la vue rendue porte `"ecartee": True` ; sinon pas de clé `ecartee`.

- [ ] **Step 1 : écrire les bancs rouges** dans `test_verif_canaux.py`, section `# ---- t326`, avec les fausses fonctions réseau déjà en place dans ce banc :
  - `T1a` : `comptes.revision("historique-telegram") == ""` avant toute péremption, puis `!= ""` et différente après `comptes.perimer_historiques(["TELEGRAM_BOT_TOKEN"])`. (Le banc existant `C1` qui attend `None` pour un historique est mis à jour : il attend une chaîne.)
  - `T1b` : un historique vérifié vert avec `id_distant` → `perimer_historiques(["TELEGRAM_CHAT_ID"])` rend `["historique-telegram"]`, la vue de l'historique a `verification is None` et `canal_id is None`.
  - `T1c` : `perimer_historiques(["OPENAI_API_KEY", "INCONNU"]) == []` et le fichier des comptes n'est pas réécrit (mtime ou contenu identique).
  - `T1d` : vérification en vol sur `historique-telegram` (fausse `_get` qui appelle `perimer_historiques([...])` avant de répondre vert) → rien n'est rangé et la vue rendue par `verif_canaux.verifier` a `ecartee is True`.
  - `T1e` : même scénario sur un compte d'espace (fausse `_get` qui appelle `comptes.poser(cid, {...})`) → `ecartee is True` ; une vérification normale n'a pas la clé `ecartee`.
  - `T1f` : `porter_par_telephone(cid, {..., "verifie_le": "2026-10-20T08:15:00", "etat": "vert", "id_distant": "123"})` puis `verifier(cid)` → `verification["date"] == "2026-10-20T08:15:00"`.
  - `T1g` : `noter_verification(cid, {"etat": "vert", "date": "pas une date"})` → la date rangée est celle de maintenant (préfixe `datetime.now().date().isoformat()`).
- [ ] **Step 2 : lancer et voir rouge** : `cd backend && PYTHONUTF8=1 "$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" tests/test_verif_canaux.py` → les `T1*` FAIL, le reste comme sur la base.
- [ ] **Step 3 : implémenter** les interfaces ci-dessus. `perimer_historiques` lit le doc une fois, appelle `_perimer` pour chaque plateforme concernée, écrit une fois seulement s'il y en a. Mettre à jour la docstring de section « Un compte HISTORIQUE … n'est PAS effacée » : elle l'est désormais par `perimer_historiques`.
- [ ] **Step 4 : relancer** le banc : tout `T1*` PASS, aucun banc de ce fichier ne régresse par rapport à la base.
- [ ] **Step 5 : commit** `t326 T1 : révision des comptes historiques, vérification écartée signalée, date du téléphone`.

### Task 2 : routes et L10 (défauts 3 côté route, 5, 6)

**Files :**
- Modify : `backend/app/api/routes.py` (`set_key`, `_oauth_callback`)
- Modify : `scripts/i18n_l10_erreurs.py` (`ERREURS` += `"CoffreVerrouille"`)
- Modify : `scripts/i18n_l10_traductions.json`, regénérer `backend/app/i18n/erreurs.json`
- Test : `backend/tests/test_verif_canaux.py` (bancs `T2*`), `backend/tests/test_i18n_l10.py` si un banc y compte les gabarits

**Interfaces :**
- Consumes : `comptes.perimer_historiques(noms)` (tâche 1), `comptes.oublier_verification(cid)` (t308).

- [ ] **Step 1 : bancs rouges** (`TestClient` de l'app, `DEEPOTUS_DATA_DIR` temporaire, `.env` temporaire comme les bancs existants qui appellent `/settings/keys` ; repérer le patron dans `test_guides_et_cles.py`) :
  - `T2a` : historique telegram vérifié vert → `POST /api/settings/keys {"name":"TELEGRAM_CHAT_ID","value":"-1001"}` → 200 et la vérification de `historique-telegram` est None.
  - `T2b` : clé refusée (`{"name":"PAS_AUTORISEE"}` → 400) et coffre posé fermé avec un secret telegram (→ 409) : la vérification est **gardée** dans les deux cas.
  - `T2c` : rappel OAuth YouTube simulé (fausse `exchange_code`, patron des bancs F de t308) avec `comptes.oublier_verification` remplacée par une fonction qui lève `OSError("disque plein")` → code 200, la page contient « revérifiez » (FR) et le jeton a été rangé ; aucune 500.
  - `T2d` : `python scripts/i18n_l10_erreurs.py --check` code 0 ; `erreurs.texte("Coffre verrouillé : le coffre est fermé", "en") == "Vault locked: the vault is closed"` (via le gabarit `Coffre verrouillé : {e}` et la nouvelle entrée exacte).
- [ ] **Step 2 : voir rouge.**
- [ ] **Step 3 : implémenter**
  - `set_key` : après la boucle de validation des noms (donc après les 400) **et** après le refus 409 du coffre, appeler `comptes.perimer_historiques([noms des entrées])` une fois, avant toute écriture (même règle que `poser` : périmer d'abord). Le périmètre ne dépend pas de la valeur (vide = effacer compte aussi).
  - `_oauth_callback` : sortir `oublier_verification` du `try … except KeyError` principal dans son propre `try` : `KeyError` → la page 404 actuelle ; toute autre `Exception` → `logger.warning("t326 oubli de vérification après OAuth : %s", type(e).__name__)` (le nom du type seulement, jamais le message) et la page de succès avec la phrase en plus « Vérification d'avant non effacée : revérifiez ce compte. » Ce texte est rendu par `_oauth_page` : le passer par L10 s'il passe par un `HTTPException` ; sinon le mettre dans le dictionnaire comme les autres textes de `_oauth_page` (suivre ce que fait l'existant pour « Jeton gardé dans le coffre »).
  - L10 : ajouter `"CoffreVerrouille"` à `ERREURS` ; traduire chaque gabarit neuf que `--manquants` liste (les messages de `coffre.py`, `comptes.py`, `fournisseurs_llm.py`, `serveurs_locaux.py`, `verif_canaux.py`), par exemple `"le coffre est fermé"` → `"the vault is closed"`, `"le coffre est fermé : ouvrez-le avant d'enregistrer un secret"` → `"the vault is closed: open it before saving a secret"`. Regénérer `erreurs.json`.
- [ ] **Step 4 : bancs verts** : `test_verif_canaux.py`, `test_i18n_l10.py`, `test_guides_et_cles.py` — comparer à la base.
- [ ] **Step 5 : commit** `t326 T2 : clés plates périment l'historique, rappel OAuth sans 500, CoffreVerrouille traduit`.

### Task 3 : écran — Annuler, vérification écartée, piège du focus (défauts 1, 2 côté écran, 7)

**Files :**
- Modify : `frontend/shared/dz-espace-assistant.js` (+ copie `frontend/dist/shared/`)
- Modify : `frontend/shared/dz-projet-canaux.js` (+ copie)
- Modify : `frontend/shared/dz-champ-ia.js` (`dialogueMaison`, + copie)
- Modify : `frontend/shared/i18n/espaces.json`, regénérer `dz-i18n-dico.js` (shared et dist)
- Test : `backend/tests/test_espace_assistant_ecran.py`, `backend/tests/test_projets_canaux_ecran.py`, `backend/tests/test_champ_ia.py` (faux DOM sous node déjà en place)

**Interfaces :**
- Consumes : la vue de `/verifier` porte `ecartee: true` (tâche 1).
- Produces : clés `espaces.assistant.ecartee` (FR « Le compte a changé pendant la vérification : revérifiez. » / EN « The account changed during the check: check it again. »), `espaces.assistant.annuler_cree` (FR « L'espace « {nom} » est déjà créé. Il reste dans la liste des espaces ; archivez-le si vous n'en voulez pas. » / EN « The space “{nom}” has already been created. It stays in the list of spaces; archive it if you don't want it. »), `espaces.assistant.annuler_fermer` (« Fermer » / « Close »), `espaces.assistant.annuler_continuer` (« Continuer » / « Continue »).

- [ ] **Step 1 : bancs rouges**
  - `test_espace_assistant_ecran.py` :
    - `A1` : étape 1, aucun espace créé, clic Annuler → la boîte se ferme, la promesse rend null, aucune question.
    - `A2` : après l'étape 1 (`st.id` posé), clic Annuler → la boîte reste, un panneau `[data-dz-assistant-annuler-cree]` montre le texte `annuler_cree` avec le nom ; « Continuer » le retire et l'étape courante est inchangée ; « Fermer » ferme et rend l'id. Échap suit le même chemin que Annuler.
    - `A3` : `/verifier` (faux serveur) rend `{compte: {..., verification: null, ecartee: true}}` → le message de la plateforme est le texte `ecartee` ; `__dzEspaceAssistant.detail(vue)` et le survol de `pastille(vue)` disent ce texte pour une vue `ecartee` sans vérification.
    - `A4` : Tab sur le dernier élément focalisable de la boîte ramène au premier, Maj+Tab sur le premier va au dernier ; un élément `disabled` ou caché n'est jamais choisi ; focus hors boîte + Tab → premier élément de la boîte.
  - `test_projets_canaux_ecran.py` `A5` et `test_champ_ia.py` `A6` : même contrat Tab que `A4` pour la boîte des canaux et pour `dialogueMaison`.
- [ ] **Step 2 : voir rouge.**
- [ ] **Step 3 : implémenter**
  - Annuler : `annuler` et Échap appellent `demanderFin()` : sans `st.id` → `fin(null)` ; avec `st.id` → affiche le panneau dans la boîte (pas un second voile), focus sur « Continuer ».
  - Écartée : dans `verifier(p)` de l'assistant, si `j.compte.ecartee` → `st.msgs[p] = T("espaces.assistant.ecartee")`. `etatDe` rend `code: "ecartee"` pour une vue `ecartee` sans vérification ; `survol` et `detail` disent alors `T("espaces.assistant.ecartee")`.
  - Piège du focus : dans chacun des trois fichiers, une fonction locale `pieger(ev, boite)` appelée depuis le gestionnaire `keydown` existant quand `ev.key === "Tab"` : focalisables = `boite.querySelectorAll("button, input, select, textarea, a[href], [tabindex]:not([tabindex='-1'])")` filtrés sur `!disabled` et visibles (`offsetParent !== null` quand la propriété existe, sinon garder) ; `preventDefault` puis focus du suivant/précédent en boucle. Pas de fichier partagé neuf (chaque script reste autonome, comme `dialogue.js` qui a déjà le sien).
  - Copier shared → dist pour les trois fichiers, ajouter les clés, `python scripts/i18n_assembler.py`.
- [ ] **Step 4 : bancs verts** : les trois bancs, plus `test_dialogues_partout.py` ; `cmp` shared/dist des fichiers touchés et du dico.
- [ ] **Step 5 : commit** `t326 T3 : Annuler signale l'espace créé, vérification écartée expliquée, Tab piégé dans les boîtes`.

### Task 4 : catalogue de l'agent et preuve à l'écran

**Files :**
- Modify : `docs/agent/catalogue/*.json`, `docs/agent/AGENT.md` si une fiche change (skill `connaissance-agent`)
- Create : captures de preuve dans `.superpowers/sdd/2026-10-26-t326-petits-defauts/preuve/` (non versionné)

- [ ] **Step 1 :** suivre la skill `connaissance-agent` : `catalogue.py --check` ; mettre à jour le rôle de `espaces.assistant.annuler` (il signale un espace déjà créé) et de la pastille (vérification écartée) ; `--check` propre, `test_agent_catalogue` comme la base.
- [ ] **Step 2 : preuve sur 8799** : backend de preuve (`DEEPOTUS_DATA_DIR` temporaire, aucune clé, port 8799), ouvrir l'assistant, franchir l'étape 1, cliquer Annuler → capture du panneau FR puis EN. Aucun « Vérifier » réel.
- [ ] **Step 3 : commit** `t326 T4 : catalogue de l'agent`.
