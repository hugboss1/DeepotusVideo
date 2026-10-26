# t310 — B1 : WhatsApp, canal et adaptateur Kapso — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** WhatsApp devient un canal d'espace, relié par un lien d'installation Kapso. Le backend sait lire et envoyer
par Kapso, sous les règles dures (accord, fenêtre de 24 h, STOP, désinscription marketing, prix, plafond par espace,
journal). WhatsApp ne devient **jamais** une cible de publication de posts.

**Architecture :**
- `services/kapso.py` est le client REST httpx (Platform et proxy WhatsApp), avec un seul hook réseau remplaçable au
  banc.
- `services/whatsapp.py` porte le canal : liaison, règles, stockage par espace (`espaces/<id>/whatsapp.json`), devis
  et envoi.
- La plateforme `whatsapp` de `comptes.py` garde la forme à 4 positions. Sa clé Kapso est **plate** et partagée.
- Routes `/api/comptes/{id}/whatsapp/*` et `/api/whatsapp/{id}/*`.
- Écran : un panneau de liaison dans l'assistant d'espace, plus un maillon de queue `dzwhatsapp` (ligne de clé dans
  Réglages, filtre de DzPostComptes).

**Tech Stack :** FastAPI, httpx async, SQLAlchemy async (aucune table neuve), JSON par espace, scripts de bancs
autonomes (Python embarqué), bancs d'écran sous node.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` §5.3, §6.1, §6.3 (mises à jour par t327).
L'API Kapso est relevée dans `docs/superpowers/specs/2026-10-27-kapso-releve.md`. Le relevé du code est dans
`.superpowers/sdd/t310-releve.md` (ignoré par git, lisible dans ce worktree) : à lire, il donne les chemins et les
lignes.

## Global Constraints

- **Aucun appel réseau réel**, ni aux bancs ni aux preuves. Tout passe par le hook `kapso._requete`, remplacé au banc.
- **Aucune clé, aucun jeton dans un journal, une URL, une réponse, un message d'erreur ou un fichier JSON.**
  - `X-API-Key` va toujours en en-tête.
  - Toute erreur fournisseur est nettoyée : clé Kapso, `token` d'un lien d'installation, `token=` d'un
    `download_url`.
  - Une erreur se journalise par `type(e).__name__` seul.
- WhatsApp **n'est pas une cible de publication** : rien dans `publishers._REGISTRY`, `plan_schema._CHANNELS`,
  `schedule_slots.DEFAULTS`, `quota.LIMITS` ou la table `_t` du bundle. `comptes.verifier_cibles` refuse un compte
  whatsapp.
- `PLATEFORMES` garde **4 positions** par entrée. Les particularités de whatsapp vivent dans des constantes à part.
- Le bundle n'est modifié que par le maillon de queue `scripts/patch_bundle_dzwhatsapp.py`, en octets et en CRLF.
  Son inverse va en tête de chaîne dans `backend/tests/_i18n_l1_aide.py`. Rien ne doit toucher l'intérieur d'un bloc
  `/*__DZ_*_BEGIN__*/`.
- Les textes d'écran passent par `dzT` (FR + EN dans `frontend/shared/i18n/*.json`, puis
  `scripts/i18n_assembler.py`). `frontend/shared` doit rester identique à `frontend/dist/shared`.
- Les messages du serveur passent par L10 : `scripts/i18n_l10_traductions.json`, puis
  `scripts/i18n_l10_erreurs.py`. Toute exception maison neuve va dans `ERREURS`.
- Bancs : depuis `backend/`, `PYTHONUTF8=1 "$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" tests/<banc>.py`,
  **un par un**. On compare toujours la base et HEAD : environ 25 bancs sont déjà rouges sur main.
- Docstrings datés `t310 (27/10/2026)`, en français, dans le style des modules voisins.
- Valeurs exactes de la spec : 1 000 messages de service gratuits par numéro et par mois ; 5 essais au plus sur 429
  (`Retry-After`, sinon 1, 2, 4, 8 s) ; lien d'installation valable 30 jours ; `meta_billing_mode` ∈
  `customer_managed` (par défaut) | `partner_managed`.

## Review Focus

1. **Fuite de secrets** : une erreur Kapso qui renvoie la clé, le `token` d'un lien ou un `download_url` dans son
   corps ne doit ressortir nulle part, ni dans la réponse, ni dans le journal, ni dans `whatsapp.json`. → bancs de la
   tâche 2 (Kapso) et de la tâche 6 (routes).
2. **Un compte whatsapp pris pour une cible de post** : par le Planificateur, un projet, l'agent ou le téléphone.
   → bancs de la tâche 1 (`verifier_cibles`) et de la tâche 7 (filtres d'écran).
3. **Clé Kapso absente, ou coffre fermé** : l'écran reste utilisable, la vérification répond orange
   `cle_kapso_absente`, aucune 500, et GET /api/comptes répond toujours. → tâches 1 et 3.
4. **Contact sans numéro (BSUID seul)** : l'identité, l'accord, le STOP et l'envoi par `recipient` marchent. Un modèle
   d'authentification vers un BSUID est refusé. → tâches 4 et 6.
5. **Liaison qui échoue ou traîne** : `failed` (avec `whatsapp_setup_error` affiché), `pending` toujours au bout de
   plusieurs « Vérifier », lien expiré, deux liens créés pour le même compte. Rien ne se range à moitié, et deux
   espaces ne prennent pas le même `phone_number_id`. → tâche 3.

---

### Task 1 : plateforme `whatsapp` et clé Kapso plate

**Files :**
- Modify :
  - `backend/app/services/comptes.py` ;
  - `backend/app/config.py` (Settings) ;
  - `backend/app/api/routes.py` (`_ALLOWED_ENV_KEYS`) ;
  - `backend/app/api/settings_routes.py` (`_CLES_ECRAN`, `RUBRIQUE_DE_CLE`) ;
  - `backend/app/services/coffre.py` (`SECRETES`) ;
  - `backend/app/services/appairage.py` (`CONSOLES`) ;
  - `backend/app/services/espaces_paquet.py` (export et import).
- Test :
  - Create `backend/tests/test_whatsapp_comptes.py` ;
  - Modify les bancs figés `test_espaces_comptes.py:202`, `test_reglages_diagnostic.py`, `test_index_reglages.py`,
    `test_appairage.py` (C2) et `test_scheduler_settings.py`, pour qu'ils connaissent `whatsapp` et
    `KAPSO_API_KEY`. Pour chacun, la valeur attendue change ; l'assertion n'est jamais supprimée.

**Interfaces :**
- Produces :
  - `PLATEFORMES["whatsapp"] = ("WhatsApp", [("KAPSO_CUSTOMER_ID", False), ("WHATSAPP_PHONE_ID", False),
    ("WHATSAPP_NUMERO", False), ("WHATSAPP_WABA_ID", False), ("WHATSAPP_FACTURATION_META", False)],
    ("WHATSAPP_PHONE_ID",), False)`.
  - `comptes.CLE_PLATE = {"whatsapp": "KAPSO_API_KEY"}`, `comptes.SANS_HISTORIQUE = frozenset({"whatsapp"})`,
    `comptes.NON_PUBLIABLES = frozenset({"whatsapp"})`.
  - `comptes.cle_kapso() -> str` : lit la clé plate par `settings.KAPSO_API_KEY`, puis `coffre.valeur`, ou "" si
    absente. Elle ne lève jamais, même coffre fermé.
  - `comptes.champs_poses_par_serveur("whatsapp") -> tuple` : tous les champs publics de whatsapp, posés par la
    liaison et jamais saisis.
  - `comptes.poser_publics_serveur(cid, valeurs: dict)` : écrit ces champs depuis le service (révision changée,
    vérification périmée, comme `poser`).
  - `_vue` ajoute `"cle_plate": {"nom": "KAPSO_API_KEY", "posee": bool}` pour un compte whatsapp.

- [ ] **Étape 1 : écrire `test_whatsapp_comptes.py`.**
  - (a) GET /api/comptes répond 200 et liste `whatsapp` dans `plateformes`, avec ses 5 champs publics et aucun champ
    `KAPSO_API_KEY`.
  - (b) Avec une clé plate posée et aucun compte : aucun compte `historique-whatsapp` n'apparaît.
  - (c) Un compte whatsapp sans `WHATSAPP_PHONE_ID` : `disponible` est faux. Avec phone_id mais sans clé : faux. Avec
    les deux : vrai.
  - (d) `POST /api/comptes/{id}` avec `valeurs` contenant un champ whatsapp, ou `KAPSO_API_KEY` : 400, rien d'écrit.
  - (e) `comptes.verifier_cibles` avec un compte whatsapp : ValueError « un compte WhatsApp n'est pas une cible de
    publication ». `R._poser_comptes` sur un post refuse de même (400).
  - (f) La vue ne contient jamais la valeur de la clé : clé `SECRET-KAPSO-123` posée, absente de tout le JSON rendu.
  - (g) Coffre posé et fermé : GET /api/comptes répond 200 et `cle_plate.posee` vaut faux, sans exception.
  - (h) L'export d'un paquet d'espace ne porte aucun champ whatsapp. L'import d'un paquet qui en contient les ignore :
    deux espaces ne partagent jamais un `WHATSAPP_PHONE_ID`.
  - (i) `KAPSO_API_KEY` appartient à `coffre.SECRETES`, `_ALLOWED_ENV_KEYS`, `RUBRIQUE_DE_CLE`, `appairage.CONSOLES`
    et `Settings`.
- [ ] **Étape 2 : lancer.** On attend des FAIL.
- [ ] **Étape 3 : implémenter.**
  - `_historiques` saute `SANS_HISTORIQUE`.
  - `disponible("whatsapp")` = `cle_kapso()` non vide ET requis du compte posés.
  - `poser`/`creer`/`modifier` refusent les champs de `champs_poses_par_serveur` et `KAPSO_API_KEY` dans `valeurs`
    (ValueError).
  - `verifier_cibles` et `_poser_comptes` refusent `NON_PUBLIABLES`.
  - `espaces_paquet` exclut whatsapp de l'export, et l'ignore à l'import.
  - La rubrique de `KAPSO_API_KEY` est celle des clés de canaux, rangée à côté de Telegram.
- [ ] **Étape 4 : lancer** le banc neuf, puis les cinq bancs figés modifiés, puis `test_espaces_comptes`,
  `test_verif_canaux`, `test_securites_client` et `test_espace_assistant_ecran`. Ils doivent être verts, ou rouges à
  l'identique de la base.
- [ ] **Étape 5 : commit** `whatsapp : plateforme d'espace et clé Kapso plate (t310)`.

### Task 2 : client REST Kapso

**Files :**
- Create : `backend/app/services/kapso.py`, `backend/tests/test_kapso.py`.

**Interfaces :**
- Consumes : `comptes.cle_kapso()`.
- Produces (toutes async ; seul `_requete` touche le réseau) :
  - `PLATFORM = "https://api.kapso.ai/platform/v1"`, `PROXY = "https://api.kapso.ai/meta/whatsapp/v24.0"`.
  - `async _requete(methode, url, *, json=None, params=None) -> tuple[int, object, dict]` : le **hook de banc**.
    Il fait `httpx.AsyncClient(verify=SSL_VERIFY, timeout=30, follow_redirects=False)` et met l'en-tête
    `X-API-Key`.
  - `class KapsoErreur(RuntimeError)`, avec les attributs :
    - `statut: int` ;
    - `code: str` (code fournisseur : `marketing_preference_stopped`, `thread_not_owner`, `131047`…, ou `reseau`,
      `cle_absente`) ;
    - `reessayable: bool` ;
    - `message` (nettoyé, 200 caractères au plus).
  - Plateforme :
    - `creer_customer(nom, externe) -> dict` ;
    - `creer_lien(customer_id, facturation, langue=None) -> {"id", "url", "expire_le", "statut"}` : le `token` du lien
      n'est **jamais** rendu ;
    - `liens(customer_id) -> list[dict]`, avec `id`, `statut`, `whatsapp_setup_status`, `whatsapp_setup_error`,
      `cree_le` ;
    - `numeros(customer_id) -> list[dict]`, avec `phone_number_id`, `display_phone_number`, `verified_name`,
      `quality_rating`, `status`, `business_account_id` ;
    - `numero(phone_number_id) -> dict` ;
    - `preferences_marketing(contact) -> bool | None` : vrai si `marketing_allowed`, ou si le 404 est « Marketing
      preference not found » ; None si le contact est inconnu.
  - Proxy :
    - `envoyer(phone_number_id, corps: dict) -> {"id", "statut"}` ;
    - `marquer_lu(phone_number_id, message_id)` ;
    - `messages(phone_number_id, *, depuis=None, apres=None, limite=100) -> (list, curseur_suivant)` ;
    - `conversations(phone_number_id, *, apres=None, limite=100) -> (list, curseur)` ;
    - `modeles(waba_id, *, statut="APPROVED") -> list[dict]` ;
    - `media(media_id, phone_number_id) -> bytes`. Il lit `download_url` et télécharge **aussitôt**, en HTTPS
      seulement, sans redirection, et refuse tout hôte autre que `api.kapso.ai`.

- [ ] **Étape 1 : écrire `test_kapso.py`**, avec un faux `_requete` qui enregistre les appels.
  - Chaque fonction : méthode, URL et corps exacts du relevé. L'en-tête porte la clé, la query jamais.
  - 429 : avec `Retry-After: 2`, puis 200 → un seul réessai, après 2 s (horloge `kapso._dormir` remplacée). Six 429
    de suite → `KapsoErreur(code="429")` après **5** essais.
  - Sans réessai : 422 `131047`, 422 `marketing_preference_stopped`, 409 `thread_not_owner`, 402
    `insufficient_credits`, 502. Chacun fait **un** appel et donne `reessayable=False`.
  - **Review Focus 1** : le faux renvoie un corps d'erreur contenant `SECRET-KAPSO-123`, un `token` de lien et
    `…media_download?token=ABC`. Ni `str(e)` ni `e.message` ni le journal capturé (loguru) n'en contiennent.
  - `creer_lien` : la réponse du faux porte `token`, absent du résultat.
  - Clé absente : `KapsoErreur(code="cle_absente")`, sans appel réseau.
  - `media` : un `download_url` vers un autre hôte, ou en http, est refusé. Une redirection 302 n'est pas suivie.
  - `envoyer` avec `recipient` (BSUID) et sans `to` : le corps ne porte pas `to`.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.**
  - L'erreur se lit sous les deux formes, Platform `{"error": str, "code"?}` et proxy
    `{"error": {"message", "code", "error_subcode"}}`.
  - Le nettoyage passe par `diagnostic._sans`, plus des regex pour `token=[^&\s]+` et `"token"\s*:\s*"[^"]+"`.
  - Aucun SDK.
- [ ] **Étape 4 : lancer** (PASS).
- [ ] **Étape 5 : commit** `whatsapp : client REST Kapso sans webhook (t310)`.

### Task 3 : liaison par lien d'installation et vérification

**Files :**
- Create : `backend/app/services/whatsapp.py` (partie liaison), `backend/tests/test_whatsapp_liaison.py`.
- Modify :
  - `backend/app/services/verif_canaux.py` (`_PAR_PLATEFORME["whatsapp"]`, `CODES`) ;
  - `backend/app/services/espaces.py` (`FICHIERS` : `whatsapp.json`) ;
  - `backend/app/api/routes.py` (routes de liaison) ;
  - `backend/tests/test_espace_assistant_ecran.py:440-447` (CODES).

**Interfaces :**
- Consumes : `kapso.*`, `comptes.poser_publics_serveur`, `fiche_client.ajouter_consentement`, `espaces.chemin`.
- Produces :
  - `whatsapp.FACTURATIONS = ("customer_managed", "partner_managed")`.
  - `async whatsapp.creer_lien(cid, facturation, consentement: dict | None, langue: str | None) -> dict`.
    - Le compte est whatsapp, et son espace existe.
    - Un espace `type=="client"` exige `consentement = {"moyen": ∈ fiche_client.MOYENS, "date": "AAAA-MM-JJ"}`.
      Sinon : ValueError « consentement daté du client exigé avant la liaison ».
    - Crée le customer s'il manque `KAPSO_CUSTOMER_ID` (`externe` = espace_id), puis le lien.
    - Range `KAPSO_CUSTOMER_ID` et `WHATSAPP_FACTURATION_META` dans le compte. Range la liaison
      `{lien_id, cree_le, expire_le, facturation, consentement}` dans `whatsapp.json`.
    - Rend `{"url", "expire_le", "facturation"}`.
    - Si une facturation différente est déjà rangée dans le compte : ValueError (« la facturation Meta ne se change
      plus : créez un nouveau compte WhatsApp »).
  - `async whatsapp.relire_liaison(cid) -> {"etat": "aucune"|"en_cours"|"terminee"|"echouee"|"expiree",
    "erreur": str|None, "numero": dict|None}`.
    - Sur `completed` : lit `numeros(customer_id)`, prend le numéro dont aucun autre compte ne porte déjà le
      `phone_number_id` (sinon `echouee`, erreur « ce numéro est déjà relié à l'espace X »), puis le range par
      `poser_publics_serveur` (`WHATSAPP_PHONE_ID`, `WHATSAPP_NUMERO`, `WHATSAPP_WABA_ID`).
    - Pour un espace client : `ajouter_consentement(eid, "whatsapp:<phone_id>", ["messages"], moyen)` avec le
      consentement de la liaison. Choix de Claude : la liaison vaut accord du client sur ce canal. Ce consentement
      est révocable dans la fiche client.
  - `verif_canaux._whatsapp()`, lecture seule :
    - pas de clé → orange `cle_kapso_absente` ;
    - pas de phone_id → `relire_liaison`, puis orange `liaison_en_cours`, ou rouge `liaison_echouee` avec l'erreur
      nettoyée ;
    - sinon `numero(phone_id)` : vert si `quality_rating` vaut GREEN ou null et que le statut est connecté, orange
      `qualite_basse` si YELLOW, rouge si RED ou si le numéro est déconnecté.
    - `id_distant` = phone_number_id, `nom_distant` = `verified_name`.
    - `CODES` reçoit `cle_kapso_absente`, `liaison_en_cours`, `liaison_echouee`, `qualite_basse`.
  - Routes (`_require_localhost` pour les écritures, erreurs par `_compte_erreur`, et `KapsoErreur` → 502 avec code
    et message nettoyés) :
    - `POST /api/comptes/{id}/whatsapp/lien` (corps `{facturation, consentement?, langue?}`) ;
    - `GET /api/comptes/{id}/whatsapp/liaison`.

- [ ] **Étape 1 : écrire `test_whatsapp_liaison.py`**, avec un faux Kapso à états.
  - Espace client sans consentement → 400.
  - Avec consentement : un customer créé, puis un lien. Le `token` n'apparaît ni dans la réponse ni dans
    `whatsapp.json` ni dans `comptes.json`.
  - Second lien pour le même compte : customer réutilisé, pas recréé. Facturation différente → 400.
  - `pending` → `en_cours`, et rien n'est rangé.
  - `failed` → `echouee`, avec l'erreur du fournisseur nettoyée.
  - `completed` : phone_id rangé, consentement `whatsapp:<id>` ajouté (espace client), vérification verte.
  - Même `phone_number_id` déjà porté par un autre compte → `echouee`, et rien n'est rangé (**Review Focus 5**).
  - Lien expiré → `expiree`.
  - Clé absente → la vérification est orange `cle_kapso_absente`, sans réseau (**Review Focus 3**).
  - Espace Deepotus (non client) : aucun consentement exigé, aucun consentement ajouté.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.** Chaque écriture de `whatsapp.json` passe par `espaces._ecrire_json` (atomique).
- [ ] **Étape 4 : lancer**, puis `test_verif_canaux`, `test_espace_assistant_ecran` et `test_espaces_comptes`.
- [ ] **Étape 5 : commit** `whatsapp : liaison par lien d'installation Kapso et vérification (t310)`.

### Task 4 : règles d'envoi et état par espace

**Files :**
- Modify : `backend/app/services/whatsapp.py` (règles, état).
- Create : `backend/tests/test_whatsapp_regles.py`.

**Interfaces :**
- Produces :
  - `whatsapp.identite(msg: dict) -> str` : `"bsuid:<from_user_id>"` si présent, sinon `"tel:<from>"`. L'inverse,
    `destinataire(identite) -> {"to": …} | {"recipient": …}`, applique la règle du relevé : `to` si l'identité est un
    numéro, sinon `recipient`.
  - `MOTS_STOP = ("stop", "arret", "arrêt", "arreter", "arrêter", "unsubscribe", "desabonner", "désabonner",
    "stopper")`, comparés sur le texte entier en minuscules, sans ponctuation finale.
  - `class WhatsappRefus(PermissionError)`, avec `code` ∈ `accord`, `stop`, `fenetre`, `marketing`, `plafond`,
    `consentement`, `prix`, `bsuid_authentification`, et `message`. Elle s'ajoute à `ERREURS` de
    `scripts/i18n_l10_erreurs.py`.
  - État dans `whatsapp.json`, clé `"etat"` :
    - `accords{identite: {date, source}}` ;
    - `stops{identite: date}` ;
    - `desinscrits_marketing{identite: date}` ;
    - `compteur{mois "AAAA-MM": {"sortants": n, "service": n}}` ;
    - `plafond_mois` (par défaut 1000, réglable) ;
    - `marche_defaut` (indicatif pays, par défaut "33") ;
    - `journal` : 2 000 lignes au plus, `{quand, sens, identite, type, categorie, statut, id}`, sans texte de
      message. Choix de Claude : le texte reste chez Kapso.
  - `noter_entrant(cid, msg)` : un entrant vaut accord pour la conversation (`source: "entrant"`) ; un texte STOP
    note le stop.
  - `noter_accord(cid, identite, source)`, `noter_stop(cid, identite)`, `noter_desinscription(cid, identite)`.
  - `controler(cid, identite, *, type: "texte"|"boutons"|"modele", categorie: str|None, dernier_entrant: datetime|None,
    maintenant: datetime)` lève `WhatsappRefus`, dans cet ordre :
    - `consentement` : espace client sans consentement en cours sur `whatsapp:<phone_id>` ;
    - `stop` ;
    - `accord` : aucun accord enregistré pour l'identité, qu'il vienne d'un entrant ou d'une saisie avec sa source.
      Choix de Claude : aucun envoi, modèle compris, sans accord ;
    - `fenetre` : texte ou boutons hors fenêtre de 24 h ;
    - `marketing` : modèle marketing vers un désinscrit ;
    - `bsuid_authentification` : modèle AUTHENTICATION vers un BSUID ;
    - `plafond` : `sortants` du mois ≥ `plafond_mois`.

- [ ] **Étape 1 : écrire `test_whatsapp_regles.py`**, à table : un cas par code de refus, et un cas qui passe pour
  chaque type.
  - Fenêtre : 23 h 59 ouverte, 24 h 01 fermée, avec l'horloge injectée.
  - STOP : « Stop », « STOP. », « arrêt » ; « stop ou encore ? » n'est pas un STOP.
  - **Review Focus 4** : un contact BSUID seul. Accord, STOP et envoi par `recipient` ; modèle AUTHENTICATION
    refusé.
  - Journal : 2 001 envois → 2 000 lignes, et aucune ligne ne contient le texte envoyé.
  - Le compteur passe au mois suivant.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.**
- [ ] **Étape 4 : lancer** (PASS).
- [ ] **Étape 5 : commit** `whatsapp : règles d'envoi, accords, STOP et plafond par espace (t310)`.

### Task 5 : prix Meta dans `pricing` et catégorie `whatsapp` de `plafonds`

**Files :**
- Modify :
  - `backend/app/services/pricing.py` (DEFAULTS, `estimate`) ;
  - `backend/app/services/plafonds.py` (`CATEGORIES`) ;
  - `backend/tests/test_constats_catalogue.py` ([Q]), s'il fige la liste.
- Create : `backend/tests/test_whatsapp_prix.py`.

**Interfaces :**
- Produces :
  - `pricing.DEFAULTS["whatsapp_meta_usd"] = {}` : marché (indicatif sans « + ») vers
    `{"marketing", "utility", "authentication", "service"}` en USD. Il est vide par défaut : la grille de Meta se
    saisit, elle ne s'invente pas.
  - `DEFAULTS["whatsapp_service_gratuits_mois"] = 1000`.
  - `estimate({"kind": "whatsapp", "categorie": ∈ {marketing, utility, authentication, service}, "marche": str,
    "service_deja_mois": int})` → une ligne `provider="meta"`.
    - Un service sous le seuil de gratuité donne une ligne à 0 « dans les 1 000 gratuits ».
    - Un marché ou une catégorie absents de la grille lèvent `ValueError("prix WhatsApp inconnu pour {marche} /
      {categorie} : saisissez la grille de Meta")`. Premier refus de ce genre dans `estimate` : il ne touche à aucun
      autre `kind`.
  - `plafonds.CATEGORIES` reçoit `"whatsapp"`.

- [ ] **Étape 1 : écrire `test_whatsapp_prix.py`.**
  - Grille vide → ValueError pour chaque catégorie.
  - Grille saisie (`pricing.save`) → montants exacts.
  - Service : à 999, ligne à 0 ; à 1 000, tarif plein.
  - `save` garde la grille imbriquée et rejette une catégorie inconnue.
  - Les autres `kind` donnent un devis inchangé : comparaison avec `test_pricing`, s'il existe.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.**
- [ ] **Étape 4 : lancer**, puis `test_constats_catalogue` et `test_plafonds_garde`.
- [ ] **Étape 5 : commit** `whatsapp : grille de prix Meta et catégorie de plafond (t310)`.

### Task 6 : lecture et envoi (routes)

**Files :**
- Modify :
  - `backend/app/services/whatsapp.py` (lecture et envoi) ;
  - `backend/app/api/routes.py` ;
  - `backend/tests/_recensement_payant.py` (`PUITS`) et `backend/tests/test_plafonds_garde.py` (`PAYANTES`).
- Create : `backend/tests/test_whatsapp_routes.py`.

**Interfaces :**
- Consumes : tâches 2 à 5, `plafonds.verifier(op, categorie="whatsapp", espace_id=…)`, `plafonds.rattacher`.
- Produces :
  - `async whatsapp.lire(cid, *, depuis: str|None) -> {"messages": [...], "suivant": str|None}`. Passe chaque entrant
    dans `noter_entrant` et rend les messages à plat :
    `{id, identite, sens, type, texte, quand, statut, media_id?}`. Le texte vient de Kapso, à la lecture seulement.
  - `async whatsapp.conversations(cid) -> list` : `{id, identite, nom, dernier_entrant, fenetre_ouverte: bool,
    stop: bool}`.
  - `async whatsapp.modeles(cid) -> list` : approuvés seulement. `{nom, langue, categorie, parametres: "nommes" |
    "positionnels", n_parametres}`, lus depuis `components`.
  - `async whatsapp.envoyer(cid, identite, envoi: dict) -> {"id", "statut", "devis"}`, dans cet ordre :
    - `controler` ;
    - catégorie de prix : texte ou boutons = `service`, modèle = sa catégorie ;
    - marché = indicatif du numéro, sinon `marche_defaut` ;
    - `plafonds.verifier`, puis `kapso.envoyer` ;
    - journal, compteurs, `rattacher` à l'id du message.
  - Les refus Kapso sans réessai sont notés : `marketing_preference_stopped` et `131050` → `noter_desinscription`.
    `131047` est rendu comme refus `fenetre`, jamais renvoyé en texte libre.
  - `envoi` = `{"type": "texte", "texte"}` | `{"type": "boutons", "texte", "boutons": [1 à 3 titres de 20
    caractères au plus]}` | `{"type": "modele", "nom", "langue", "parametres": list|dict}`.
  - Routes :
    - `GET /api/whatsapp/{cid}/conversations` ;
    - `GET /api/whatsapp/{cid}/messages?depuis=` ;
    - `GET /api/whatsapp/{cid}/modeles` ;
    - `POST /api/whatsapp/{cid}/envoyer` (localhost ; `WhatsappRefus` → 409 `{message, code}` ; 402 de plafond
      inchangé ; `KapsoErreur` → 502 nettoyé) ;
    - `POST /api/whatsapp/{cid}/accords` `{identite, source}` (localhost) ;
    - `POST /api/whatsapp/{cid}/stop` `{identite}` (localhost) ;
    - `GET /api/whatsapp/{cid}/medias/{media_id}` (localhost ; renvoie les octets, sans les garder sur disque).
  - Un compte non whatsapp, ou d'un autre espace que celui demandé : 404.

- [ ] **Étape 1 : écrire `test_whatsapp_routes.py`** (TestClient, faux `kapso._requete`, BD temporaire).
  - Envoi texte dans la fenêtre : un appel Kapso, une ligne `Depense` catégorie `whatsapp` et espace, le journal, le
    compteur.
  - Chaque `WhatsappRefus` → 409, aucun appel Kapso, aucune dépense.
  - Plafond en dollars de l'espace dépassé → 402 `dz_plafond`.
  - Grille vide → 409 `prix`, sans appel.
  - `marketing_preference_stopped` → désinscription notée, puis le second envoi est refusé avant Kapso.
  - Lecture : un entrant « STOP » → stop noté, et l'envoi suivant refusé.
  - **Review Focus 1** : un 502 dont le corps contient la clé et un `download_url` à jeton → réponse nettoyée.
  - **Review Focus 2** : `POST /api/schedule` avec un compte whatsapp en cible → 400.
  - `test_plafonds_garde` vert avec la route d'envoi dans `PAYANTES`.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.**
- [ ] **Étape 4 : lancer**, puis `test_plafonds_garde`, `test_securites_client` et `test_i18n_l10`.
- [ ] **Étape 5 : commit** `whatsapp : lecture et envoi par Kapso, sous les règles (t310)`.

### Task 7 : écrans (panneau de liaison, filtres, ligne de clé)

**Files :**
- Modify :
  - `frontend/shared/dz-espace-assistant.js` et `frontend/shared/dz-projet-canaux.js`, plus leurs copies dans
    `frontend/dist/shared/` ;
  - `frontend/shared/i18n/espaces.json`, `projets.json` et `reglages.json` ;
  - les dictionnaires assemblés.
- Create : `scripts/patch_bundle_dzwhatsapp.py`, `backend/tests/test_whatsapp_ecran.py`.
- Modify :
  - `backend/tests/_i18n_l1_aide.py` (inverse en tête de chaîne) ;
  - `frontend/dist/assets/index-BEOJX8L5.js` (par le maillon seulement).

**Interfaces :**
- Consumes : les routes des tâches 3 et 6, `vue.cle_plate`.
- Produces :
  - Dans `etape3()`, pour `p === "whatsapp"`, `panneauWhatsapp(compte)` remplace `champsDe(p)`. Aucun input de
    champ.
    - (1) Si `cle_plate.posee` est faux : un message « clé Kapso à saisir dans Réglages › Clés d'API », et rien
      d'autre.
    - (2) Espace client : moyen (écrit, WhatsApp, au doigt) et date du consentement à la liaison.
    - (3) Facturation Meta : deux radios. `customer_managed` est cochée par défaut ; l'aide dit que le choix est
      définitif.
    - (4) Bouton « Créer le lien », puis l'URL en lecture seule, un bouton « Copier » et l'expiration.
    - (5) « Vérifier » (le bouton existant) relit la liaison.
    - Attributs `data-dz-assistant-whatsapp-*`.
  - `dz-projet-canaux.js` : `comptes(espace)` exclut `plateforme === "whatsapp"`.
  - Le maillon `dzwhatsapp` porte deux paires, hors couches :
    - P1 : `dzFuNeuves()` reçoit `{k:"KAPSO_API_KEY", label:dzT("reglages.cles.kapso"), why:dzT("reglages.cles.kapso_why")}` ;
    - P2 : le sélecteur `DzPostComptes` exclut les comptes `plateforme==="whatsapp"`.
    - Marqueur `/*dzwhatsapp*/`, ancres uniques vérifiées, l'inverse remis en tête de chaîne.
  - Glyphe : si `scripts/icones/construire_suite.py` peut prendre l'icône simple-icons `whatsapp` en
    `dz-reseau-whatsapp`, l'ajouter et l'employer dans les deux `GLYPHES`. Sinon, garder le repli
    `dz-action-publier` et le noter au registre.

- [ ] **Étape 1 : écrire `test_whatsapp_ecran.py`** (node + `FAUX_DOM`, sur le modèle de
  `test_espace_assistant_ecran.py`).
  - Sans clé : le message s'affiche, sans bouton « Créer le lien ».
  - Espace client sans consentement : le bouton est désactivé.
  - Le clic envoie `POST …/whatsapp/lien` avec la facturation cochée, puis l'URL s'affiche.
  - Aucun `<input>` n'a pour nom un champ whatsapp ou `KAPSO_API_KEY`.
  - Dans la boîte des canaux, aucun compte whatsapp n'est proposé.
  - Bundle : marqueur ×1 ; `DzPostComptes` filtre whatsapp ; `dzFuNeuves` contient `KAPSO_API_KEY`.
  - Chaque clé `dzT` employée existe en FR et en EN, avec les mêmes variables.
- [ ] **Étape 2 : lancer** (FAIL).
- [ ] **Étape 3 : implémenter.**
  - Lancer `scripts/patch_bundle_dzwhatsapp.py`.
  - Lancer `scripts/i18n_assembler.py`, puis `--check`.
  - Copier `frontend/shared/*.js` vers `frontend/dist/shared/`.
- [ ] **Étape 4 : lancer** le banc neuf, puis `test_espace_assistant_ecran`, `test_projets_canaux_ecran`,
  `test_i18n_l0`, `test_i18n_l2`, `test_scheduler_bundle` et `test_etabli_canevas`.
- [ ] **Étape 5 : commit** `whatsapp : panneau de liaison, filtres de cibles et clé Kapso dans Réglages (t310)`.

### Task 8 : textes serveur, catalogue de l'agent, preuve sans réseau

**Files :**
- Modify :
  - `scripts/i18n_l10_traductions.json` et `backend/app/i18n/erreurs.json` (régénéré) ;
  - `docs/agent/catalogue/*.json`, `docs/agent/AGENT.md` et `docs/agent/ancres.json`, au besoin.
- Create : `docs/superpowers/specs/captures/t310/*.png` (FR et EN).

- [ ] **Étape 1 : textes serveur.** `scripts/i18n_l10_erreurs.py --manquants`, puis traduire FR et EN chaque
  message neuf, puis réécrire. `--check` est vert, et `test_i18n_l10` aussi.
- [ ] **Étape 2 : catalogue de l'agent.** Avec le skill `connaissance-agent` : lancer `scripts/agent/catalogue.py`,
  rédiger d'après le code les fiches neuves du panneau WhatsApp et de la ligne de clé, puis ajuster AGENT.md
  (WhatsApp = canal de conversation, pas une cible de post). `--check` et `test_agent_catalogue` doivent être verts.
- [ ] **Étape 3 : preuve sur le backend de preuve 8799**, avec des données temporaires, sans clé réelle et sans
  réseau. Le faux Kapso est injecté par un lanceur de preuve qui remplace `kapso._requete`, comme
  `serve_t325.py`.
  - Capturer en FR et en EN : le panneau sans clé, le panneau avec consentement et facturation, le lien créé, la
    liaison terminée avec la pastille verte, et Réglages › Clés d'API avec la ligne Kapso.
  - Ne jamais cliquer sur un vrai service.
- [ ] **Étape 4 : passage complet** des bancs touchés par le lot, base contre HEAD, consigné au registre.
- [ ] **Étape 5 : commit** `whatsapp : textes, catalogue de l'agent et preuve FR/EN (t310)`.
