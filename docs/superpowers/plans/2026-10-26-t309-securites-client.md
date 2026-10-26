# t309 (A4) : validation client et sécurités de publication — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** appliquer côté serveur et à l'écran les règles d'un client (§5.5) : consentement en cours exigé par canal, état « à valider » en mode `valide_par_client`, confirmation nominative en mode `publie_en_son_nom`, pause des posts d'un canal révoqué, journal lisible, bandeau « pour qui ».

**Architecture :** un service neuf `regles_client.py` décide (une seule source de vérité, appelée par les routes, la boucle et `fire_post`, avec un chemin de lecture BRUTE pour la boucle) ; deux colonnes neuves sur `scheduled_posts` ; les routes du Planificateur et de la fiche client l'appliquent ; à l'écran, un maillon de queue `dzgardeclient` (après `dzcanauxpre`) rend visibles les 409 du Planificateur et l'état « à valider », et deux scripts externes (`dz-garde-client.js`, `dz-pour-qui.js`) portent la confirmation nominative, la fiche client (consentements, révocation, journal, posts à valider) et le bandeau.

**Tech Stack :** FastAPI/SQLAlchemy async (sqlite), JS vanilla ES5 hors bundle, maillon de bundle en octets/CRLF, bancs maison sous python embarqué et node.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §5.5 (et §5.2, §5.3 dernière phrase, §11 bis « un produit rattaché à un client suit ses règles »). Relevé du code : `.superpowers/sdd/t309-releve.md` (copie du relevé du 26/10, lignes et offsets exacts).

## Global Constraints

- Base : `chantier/boite-petits-defauts` (t326) à c0faef59, elle-même sur `origin/main` 646b6d97 ; à fusionner après t326. Branche `chantier/boite-securites-client`. Ne rien pousser.
- Le client qui gouverne un post = `espaces.client_responsable(post.espace_id)` (lui-même, ou le parent client d'un produit). Pas de client → aucune règle t309 (Deepotus et les marques ne changent pas de comportement).
- Un canal est couvert si son `canal_id` (vérification t308) a un consentement **en cours** (`revoque_le is None`) dans la fiche du client. `canal_id` None = jamais couvert.
- La boucle (`marketing.tick`), `fire_post` et `sync_lot` ne lisent les fichiers qu'en BRUT (jamais `espaces.lire()` ni `fiche_client.lire()`, qui migrent et écrivent).
- Le format `client.json` v1 est partagé avec le compagnon : on n'y ajoute aucun champ ; les lignes de journal restent `{quand, quoi, canal_id, qui}` avec `quoi` ∈ `fiche_client.QUOI` existant (`publication`, `validation`, `revocation`, `consentement`…).
- Aucun secret dans une réponse, un journal, une URL. Aucun appel réseau réel dans les bancs ni la preuve. Backend de preuve sur 8799 (ou un port libre ≥ 8790 si 8799 est occupé — ne jamais tuer un processus qu'on n'a pas lancé), données temporaires, sans clé, `news_service.refresh_if_stale` neutralisée dans le lanceur de preuve. Jamais 8765.
- Bundle : seulement par le maillon `scripts/patch_bundle_dzgardeclient.py` (octets, CRLF, sondes amont, aller-retour vérifié, `.bak` supprimé) ; inverse `avant_dzgardeclient` appelé EN TÊTE de `avant_dzcanauxpre` dans `backend/tests/_i18n_l1_aide.py`. Aucun remplacement dans un bloc `/*__DZ_*_BEGIN__*/`. Épingles inchangées : `x.useState(` ×731, `v2.8.0` ×4, `DzTracks` ×181, `await window.__dzDialogue.confirmer(` ×30 (les dialogues neufs passent par un script externe).
- `frontend/shared/*.js` touché = copie octet pour octet dans `frontend/dist/shared/` ; scripts neufs chargés par `frontend/dist/index.html` après `dz-espace-assistant.js`. Clés `dzT` FR/EN dans `frontend/shared/i18n/*.json` + `scripts/i18n_assembler.py`. Messages serveur par L10 (`--check` propre).
- ~25 bancs déjà rouges sur main : comparer base et HEAD.

## Décisions (prises au plan, à vérifier en relecture)

1. **Consentement dans les deux modes.** §5.3 : « pour un client, chaque canal demande un consentement daté avant d'être utilisable en publication ». La garde « consentement en cours » vaut donc en `valide_par_client` comme en `publie_en_son_nom`.
2. **« À valider » repose sur une date, pas seulement sur l'état.** Colonne `valide_client_le` (DATETIME, None). En `valide_par_client`, programmer (passer à `scheduled` ou `ready`, `/fire`, lot, fil) exige `valide_client_le`. L'état `a_valider` est l'affichage d'un post de client non validé ; `POST /schedule` crée `a_valider` au lieu de `draft` pour un client en `valide_par_client`. Tout changement de contenu (title, caption, source_image, job_id) remet `valide_client_le` à None et un post `scheduled`/`ready` repasse `a_valider`.
3. **Réponse du client saisie au PC.** L'envoi par WhatsApp est B2, le partage natif est mobile. t309 livre `POST /schedule/{id}/validation-client {reponse: "valide"|"corriger", moyen: "ecrit"|"whatsapp"|"doigt"}` (localhost) : date, journal `validation` par canal du post (`qui="client"`), et un bouton « Réponse du client » dans la fiche (tâche 5).
4. **Confirmation nominative = preuve dans le corps.** En `publie_en_son_nom`, programmer exige `confirme_client == <id du client>` dans le corps du POST/PATCH (ou de `/fire`) ; sinon 409 de code `confirmation` qui nomme le client et les canaux. La colonne `confirme_client` (String 40) garde l'id confirmé ; le contenu ou les comptes qui changent l'effacent. Le fil hérite de la confirmation du parent.
5. **Révocation = filtre de la boucle, comme t210.** Aucun état « en pause » neuf : `tick` saute un post de client dont un canal n'est plus couvert (ou, en `valide_par_client`, non validé) ; il repart seul quand un consentement neuf court. `POST …/consentements/revoquer` rend `en_pause` (nombre de posts `scheduled|ready` des espaces gouvernés par ce client qui visent ce canal). `fire_post` refuse aussi (dernière ligne de défense) et `sync_lot` n'emporte pas un post en pause.
6. **Refus = 409 structuré.** `regles_client.RefusClient(PermissionError)` porte `code` ∈ {`a_valider`, `consentement`, `confirmation`}, `client` (id), `nom` (société de la fiche, sinon nom de l'espace), `canaux` (liste de `canal_id` ou de libellés de comptes). Les routes rendent `HTTPException(409, {"message": str(e), "code", "client", "nom", "canaux"})` ; `RefusClient` est ajouté à `ERREURS` de L10 pour traduire `message`.
7. **Bandeau et fiche hors bundle.** `dz-pour-qui.js` insère le bandeau après `main > header` sur les vues `quick`, `studio`, `scheduler`, `library` (la Capture n'existe pas encore) : pastille de couleur, nom de l'espace, projet actif ; liseré de la couleur de l'espace + mention « Client » dans un espace gouverné par un client, avec un bouton « Fiche client » qui ouvre la boîte de la fiche (consentements avec Révoquer / Ajouter, posts à valider avec « Réponse du client », journal).

## Review Focus

1. Un post de client programmé AVANT t309 (aucun consentement, aucune validation) : il ne part plus (pause de la boucle) et n'est pas perdu ; ajouter le consentement le fait repartir (tâche 3).
2. Un produit sous un client : mêmes règles, même nom de client dans le 409, même fiche (tâche 1).
3. Un PATCH qui ne change que `run_at` d'un post déjà programmé et confirmé ne redemande rien ; un PATCH qui change les comptes ou le texte retire validation/confirmation (tâche 2).
4. Le Planificateur ne doit jamais afficher « programmé » après un 409 : l'état local est rechargé et le message dit pourquoi (tâche 4).
5. Fiche ou comptes illisibles pendant la boucle : la boucle ne s'arrête pas ; un post de client dont on ne peut pas prouver la couverture ne part pas (refus par défaut), un post sans client part comme avant (tâche 3).

---

### Task 1 : service `regles_client` et colonnes

**Files :** Create `backend/app/services/regles_client.py` ; Modify `backend/app/services/storage.py` (colonnes `valide_client_le` DATETIME, `confirme_client` VARCHAR(40) + `SCHEDULED_POSTS_COLUMNS`) ; Modify `scripts/i18n_l10_erreurs.py` (`ERREURS` += `"RefusClient"`), `scripts/i18n_l10_traductions.json`, `backend/app/i18n/erreurs.json` ; Test : create `backend/tests/test_regles_client.py`.

**Interfaces (Produces) :**
- `class RefusClient(PermissionError)` : `__init__(self, message, code, client, nom, canaux)` ; attributs du même nom.
- `exigences(espace_id, comptes_ids, brut=False) -> dict | None` : None sans client ; sinon `{"client": id, "nom": str, "mode": "valide_par_client"|"publie_en_son_nom", "canaux": [{"compte": cid, "libelle": str, "canal_id": str|None, "couvert": bool}], "non_couverts": [libellés]}`. `brut=True` : lit `espaces.json`, `client.json` et `comptes.json` sans migration (lecteurs privés `_brut_*`, à la manière de `marketing._espaces_archives`) ; toute erreur de lecture d'un espace gouverné → `{"client": id-ou-"?", "illisible": True, ...}` traité comme non couvert.
- `controler(post, confirme=None, brut=False) -> dict | None` : `post` a `espace_id`, `comptes` (JSON str ou liste), `valide_client_le`, `confirme_client`. Rend les exigences si tout va ; lève `RefusClient` dans cet ordre : `consentement` (au moins un canal non couvert, ou aucun compte ciblé), `a_valider` (mode `valide_par_client` et `valide_client_le` None), `confirmation` (mode `publie_en_son_nom` et `(confirme or post.confirme_client) != client`).
- `statut_initial(espace_id, demande) -> str` : `"a_valider"` pour un client en `valide_par_client` quand `demande == "draft"`, sinon `demande`.
- `en_pause(post) -> bool` : `controler(post, brut=True)` lève `consentement` ou `a_valider` (la confirmation n'est pas redemandée à l'heure de partir : elle a été donnée).
- Messages FR (gabarits L10) : `consentement` → `"aucun consentement en cours du client « {nom} » pour : {canaux}"` ; `a_valider` → `"post à valider par le client « {nom} » avant d'être programmé"` ; `confirmation` → `"confirmez la publication au nom du client « {nom} » sur : {canaux}"`. EN : `"no current consent from client “{nom}” for: {canaux}"`, `"post awaiting approval by client “{nom}” before it can be scheduled"`, `"confirm publishing on behalf of client “{nom}” on: {canaux}"`.

- [ ] **Step 1 : bancs rouges** `test_regles_client.py` (données temporaires, aucun réseau ; vérifications posées par `comptes.noter_verification` avec un `id_distant`, consentements par `fiche_client.ajouter_consentement`) :
  - R1 espace marque → `exigences` None, `controler` rend None, `statut_initial(e,"draft") == "draft"`.
  - R2 client `valide_par_client`, compte vérifié, consentement en cours, post non validé → `RefusClient` code `a_valider`, `nom` = société de la fiche ; validé → passe.
  - R3 canal non vérifié (canal_id None) → code `consentement`, `canaux` contient le libellé du compte.
  - R4 `publie_en_son_nom` couvert : sans confirmation → `confirmation` ; `confirme=<id client>` → passe ; `confirme="autre"` → `confirmation`.
  - R5 produit dont le parent est le client → mêmes refus, `client` = id du parent.
  - R6 révocation → `en_pause(post)` True ; nouveau consentement → False.
  - R7 `brut=True` donne les mêmes verdicts que `brut=False` sur R2-R6, et n'écrit aucun fichier (contenu de `espaces.json`/`client.json`/`comptes.json` identique avant/après) ; `client.json` corrompu → `en_pause` True, aucune exception.
  - R8 colonnes : un `ScheduledPost` neuf a `valide_client_le is None`, `confirme_client is None` ; une base existante gagne les colonnes par l'auto-ALTER.
  - R9 `i18n_l10_erreurs.py --check` code 0 et `texte(<message consentement FR>, "en")` rend l'anglais.
- [ ] **Step 2 : voir rouge.** **Step 3 : implémenter.** **Step 4 : vert** (`test_regles_client.py`, `test_espaces_type_client.py`, `test_i18n_l10.py`). **Step 5 : commit** `t309 T1 : règles d'un client (consentement, validation, confirmation)`.

### Task 2 : routes du Planificateur et de la fiche

**Files :** Modify `backend/app/api/routes.py` (`create_scheduled_post`, `update_scheduled_post`, `validate_lot`, route du fil, `/schedule/{id}/fire`, `list_schedule`, `_post_to_dict`, route `…/consentements/revoquer`) ; Modify `backend/app/services/marketing.py` (`materialize_plan` : `statut_initial`, et un post de client n'y est jamais créé `scheduled`) ; Test : create `backend/tests/test_securites_client.py`.

**Interfaces :**
- Consumes : tâche 1.
- Produces :
  - `_post_to_dict` gagne `valide_client_le` (ISO|None) et `confirme_client`.
  - `GET /api/schedule/{id}/client` → `{"exigences": dict|None}` (lecture seule, sans secret).
  - `POST /api/schedule/{id}/validation-client` (localhost) `{reponse, moyen}` → `{"post": …}` ; 400 réponse/moyen inconnus ; 404 post inconnu ; 409 post sans client.
  - 409 `RefusClient` → `HTTPException(409, {"message","code","client","nom","canaux"})`.
  - `POST …/consentements/revoquer` rend en plus `"en_pause": int`.

- [ ] **Step 1 : bancs rouges** (`TestClient`, sqlite temporaire, patron de `test_canaux_preremplis.py`) :
  - S1 POST dans un client `valide_par_client` sans statut → `status == "a_valider"` ; avec `status:"scheduled"` → 409 code `a_valider`, nom du client dans `message`, rien en base.
  - S2 PATCH `status:"scheduled"` d'un post `a_valider` → 409 ; après `validation-client {reponse:"valide", moyen:"ecrit"}` → 200, `valide_client_le` posé, `status` `draft`, journal de la fiche : une ligne `validation` `qui="client"` par canal ; puis PATCH scheduled → 200.
  - S3 PATCH `caption` d'un post validé et programmé → `valide_client_le` None et `status == "a_valider"` ; PATCH `run_at` seul → inchangé.
  - S4 `publie_en_son_nom` : PATCH scheduled sans `confirme_client` → 409 code `confirmation` ; avec la bonne valeur → 200, `confirme_client` gardé ; changement de `comptes` → `confirme_client` None.
  - S5 canal sans consentement → 409 `consentement` dans les deux modes ; `/fire` d'un tel post → 409 sans publier (fausse `publishers.publish` qui compte ses appels : 0).
  - S6 `POST /schedule/validate` : un post de client non conforme est dans `skipped` avec la raison (message du refus) ; les autres posts sont validés comme avant.
  - S7 fil sur un parent confirmé : l'enfant hérite `confirme_client` et passe ; parent non validé (`valide_par_client`) → 409.
  - S8 `GET /schedule` liste un post `a_valider` hors fenêtre ; `GET /schedule/{id}/client` rend les exigences (aucune clé `secret`/`token` dans le JSON).
  - S9 révocation : deux posts programmés sur le canal, un sur un autre canal → `en_pause == 2`.
  - S10 Deepotus et une marque : aucun comportement changé (POST draft reste draft, PATCH scheduled passe).
  - S11 `materialize_plan` dans un client → aucun post `scheduled`.
- [ ] **Step 2 : rouge. Step 3 : implémenter** (contrôle placé AVANT `session.commit()`, comme les refus existants ; ordre des champs du PATCH : contenu → efface validation/confirmation, comptes → efface confirmation, puis statut demandé → `controler(post, confirme=body.get("confirme_client"))`). **Step 4 : vert** + bancs du Planificateur existants (`test_espaces_scheduler.py`, `test_scheduler_validate.py`, `test_scheduler_threads.py`, `test_canaux_preremplis.py`, `test_espaces_type_client.py`) comparés à la base. **Step 5 : commit** `t309 T2 : le Planificateur applique les règles du client`.

### Task 3 : boucle, publication et journal

**Files :** Modify `backend/app/services/marketing.py` (`tick`, `fire_post`, `posts_en_attente` inchangé), `backend/app/services/sync_lot.py` ; Test : `backend/tests/test_securites_client.py` (section B).

**Interfaces :** Consumes `regles_client.en_pause`, `regles_client.controler(..., brut=True)`, `fiche_client.noter`.

- [ ] **Step 1 : bancs rouges**
  - B1 post de client programmé, canal révoqué → `asyncio.run(MK.tick([date]))` ne le publie pas (fausse `publish` : 0 appel), statut toujours `scheduled` ; nouveau consentement → le tick suivant le publie.
  - B2 post de client programmé AVANT t309 (posé directement en base, sans validation) en `valide_par_client` → sauté par le tick, pas d'erreur.
  - B3 `fire_post` d'un post non couvert (appel direct) → aucune publication, `status` remis à `a_valider` (valide_par_client) ou `draft` (publie_en_son_nom), `error` = message du refus.
  - B4 publication réussie d'un post de client → une ligne de journal `publication` par canal publié (`qui="utilisateur"`), aucune pour un post de marque.
  - B5 `client.json` illisible pendant le tick → la boucle continue, le post de client ne part pas, un post de marque part.
  - B6 `sync_lot` : un post en pause n'est pas dans le lot du téléphone.
- [ ] **Step 2 : rouge. Step 3 : implémenter** (filtre juste après celui de t210 ; `fire_post` contrôle avant la boucle `for cle, ch, cid in cibles` ; journal après chaque publication réussie, jamais bloquant : une erreur d'écriture du journal est journalisée par son type seulement). **Step 4 : vert** + `test_espaces_client.py`, `test_scheduler_publish.py`, `test_scheduler_validate.py`, `test_sync_lot.py` comparés à la base. **Step 5 : commit** `t309 T3 : révocation en pause, dernière ligne de défense, journal des publications`.

### Task 4 : Planificateur — 409 visibles, état « à valider », confirmation nominative

**Files :** Create `scripts/patch_bundle_dzgardeclient.py` ; Modify `frontend/dist/assets/index-BEOJX8L5.js` (par le maillon seulement) ; Modify `backend/tests/_i18n_l1_aide.py` (`avant_dzgardeclient` en tête de `avant_dzcanauxpre`) ; Create `frontend/shared/dz-garde-client.js` (+ copie dist) ; Modify `frontend/dist/index.html` ; Modify `frontend/shared/i18n/planif_news.json` (ou un `planif_client.json` neuf) + dico ; Test : create `backend/tests/test_garde_client_ecran.py`.

**Interfaces :**
- Consumes : 409 structuré et `GET /schedule/{id}/client` (tâche 2).
- Produces : `window.__dzGardeClient = {patch(id, corps, envoyer) -> Promise<json|null>, etiquette(statut) -> str|null}`.
- Maillon (paires hors couche, toutes derrière `window.__dzGardeClient&&`) :
  - G1 `D.updateScheduledPost` (@336494) : si `window.__dzGardeClient`, déléguer à `window.__dzGardeClient.patch(e, t, <fetch d'origine>)`, sinon le code d'origine inchangé.
  - G2 `Lm` (@1016300) : un `x.useEffect` (pas de `useState`) qui écoute `deepotus:schedule-recharger` et appelle `reloadPosts`.
  - G3 libellé, couleur et tonalité de `a_valider` dans les tables d'états (`wh`, `Rm`, libellés `scheduler.etat.*`) : ambre comme `ready`.
- `dz-garde-client.js` : `patch` envoie ; sur 409 `code:"confirmation"` → `__dzDialogue.confirmer(T("scheduler.client.confirmer",{nom, canaux}), {titre: T("scheduler.client.confirmer_titre"), ok: T("scheduler.client.confirmer_ok")})` → oui : renvoie avec `confirme_client: client` ; non : `deepotus:schedule-recharger`, rend null. Autre 409 client → `__dzDialogue.informer(message)` + `deepotus:schedule-recharger`, rend null. Toute autre réponse : comportement d'origine (json si ok, sinon null).
- Clés : `scheduler.etat.a_valider` (« À valider » / « Awaiting approval »), `scheduler.client.confirmer` (« Publier au nom de {nom} sur {canaux} ? Le consentement du client est en cours pour ces canaux. » / « Publish on behalf of {nom} on {canaux}? The client's consent is current for these channels. »), `scheduler.client.confirmer_titre` (« Publication au nom du client » / « Publishing on behalf of the client »), `scheduler.client.confirmer_ok` (« Publier en son nom » / « Publish on their behalf »).

- [ ] **Step 1 : bancs rouges** `test_garde_client_ecran.py` : [M] le maillon sur une copie du bundle : sondes amont, `defaire(appliquer(b)) == b` à l'octet, aucune paire dans un bloc `/*__DZ_*_BEGIN__*/`, épingles inchangées, chaîne inverse (`avant_dzcanauxpre` appelle `avant_dzgardeclient` d'abord) ; [F] sous node avec faux DOM/faux fetch : 409 `confirmation` → dialogue nommant le client, oui → second PATCH avec `confirme_client`, non → évènement de rechargement et null ; 409 `a_valider` → `informer` + rechargement ; 200 → json ; [G] la fonction G1 extraite du bundle patché délègue quand `__dzGardeClient` existe et garde l'ancien comportement sinon.
- [ ] **Step 2 : rouge. Step 3 : implémenter** (modèles : `patch_bundle_dzcanauxpre.py`, `patch_bundle_dzschedconf.py`, `test_planif_confirmations.py`). Appliquer le maillon au bundle du worktree. **Step 4 : vert** + `test_canaux_preremplis.py`, `test_espace_assistant_ecran.py`, `test_dialogue_bundle.py`, `test_scheduler_bundle.py`, `test_planif_confirmations.py` comparés à la base. **Step 5 : commit** `t309 T4 : le Planificateur montre les refus du client et demande la confirmation nominative`.

### Task 5 : bandeau « pour qui » et fiche client

**Files :** Create `frontend/shared/dz-pour-qui.js` (+ copie dist), Modify `frontend/dist/index.html`, `frontend/shared/i18n/espaces.json` + dico ; Test : create `backend/tests/test_pour_qui_ecran.py`.

**Interfaces :** Consumes `GET /api/espaces`, `GET /api/library/projets/actif`, `GET/POST /api/espaces/{id}/client…`, `GET /api/espaces/{id}/recapitulatif` (canaux et `canal_id`), `GET /api/schedule?espace=<id>` (posts `a_valider`), `POST /api/schedule/{id}/validation-client`. Produces `window.__dzPourQui = {rafraichir(), ouvrirFiche(espaceId)}`.

- Bandeau `[data-dz-pour-qui]` inséré après `main > header` pour `dz_view` ∈ {quick, studio, scheduler, library} (relu à chaque mutation de `#root` et à `deepotus:navigate`, `deepotus:espace-refresh`, `dz-projets`) : pastille couleur, nom de l'espace, « Projet : <nom> » si un projet est actif. Espace gouverné par un client : liseré gauche 3 px de la couleur de l'espace, mention « Client : <nom du client> », bouton « Fiche client ».
- Boîte de la fiche (même charte que `dz-espace-assistant.js`, Tab piégé comme en t326) : consentements (canal, date, moyen, « Révoquer » avec confirmation qui annonce le nombre de posts mis en pause rendu par la route), « Ajouter un consentement » (canal choisi parmi les `canal_id` du récapitulatif, moyen), posts « à valider » avec « Validé par le client » / « À corriger » (moyen), journal (plus récent d'abord, 50 lignes).
- Clés `espaces.pourqui.*` FR/EN (libellés ci-dessus).

- [ ] **Step 1 : bancs rouges** sous node (faux DOM, faux fetch, patron de `test_projets_canaux_ecran.py`) : P1 bandeau présent sur scheduler, absent sur settings ; P2 liseré et bouton seulement pour un espace client ou un produit sous client ; P3 Révoquer appelle la route et affiche `en_pause` ; P4 Ajouter envoie `{canal_id, permis:["publier"], moyen}` ; P5 « Validé par le client » appelle `validation-client` puis émet `deepotus:schedule-recharger` ; P6 journal trié, au plus 50 lignes ; P7 EN : aucun texte français dans le bandeau ni la boîte ; P8 shared == dist, index.html charge le script une fois.
- [ ] **Step 2 : rouge. Step 3 : implémenter. Step 4 : vert** + `test_espace_assistant_ecran.py`, `test_projets_canaux_ecran.py`. **Step 5 : commit** `t309 T5 : bandeau pour qui et fiche client`.

### Task 6 : catalogue de l'agent et preuve

- [ ] **Step 1 :** skill `connaissance-agent` : fiches du Planificateur (état « à valider », confirmation), de la fiche client et du bandeau ; AGENT.md (règles du client, l.65-68) ; `catalogue.py --check` propre ; ne pas commiter les JSON seulement réécrits en LF.
- [ ] **Step 2 : preuve** sur backend de preuve (voir Global Constraints) : un espace client avec un compte à vérification posée en base (aucun « Vérifier » réel), consentement ajouté par la fiche, post « à valider » au Planificateur, refus 409 visible, « Validé par le client », programmation acceptée ; un espace `publie_en_son_nom` : dialogue nominatif ; révocation → « 1 post en pause ». Captures FR et EN dans `.superpowers/sdd/<plan>/preuve/`.
- [ ] **Step 3 : commit** `t309 T6 : catalogue de l'agent`.
