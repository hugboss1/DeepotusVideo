# Boîte à outils de l'agent — feuille de route et plan détaillé A0-A1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** ranger les outils de l'agent en boîtes, une par fonctionnalité (A0), puis donner aux espaces un type et
aux clients une fiche avec mode de publication et consentements datés (A1). Ce sont les deux socles des lots
suivants.

**Architecture :**
- Un module `agent_boites.py` déclare les boîtes au-dessus du registre plat `agent_outils.OUTILS`. Ce registre
  reste inchangé à l'octet pour l'agent Campagnes. `executer` refuse tout outil hors de la boîte de l'agent du tour.
- Le type d'espace vit dans `espaces.json`. La fiche client est un fichier de l'espace (`client.json`, liste
  blanche de `espaces.chemin`), servi par quatre routes locales et transporté par le paquet d'espace (t210).

**Tech Stack :** Python 3 (python embarqué), FastAPI, bancs autonomes `tests/test_*.py` (`check(label, cond)`,
data-dir temporaire), aucune dépendance neuve.

**Spec :** `docs/superpowers/specs/2026-10-25-boite-a-outils-design.md` (§4 pour A0, §5.2 et §11 bis pour A1).
Spec jumelle mobile : `C:\Users\olivi\deepotus-mobile-boite\docs\superpowers\specs\2026-10-25-boite-a-outils-mobile-design.md`.

## Feuille de route (tâches du suivi)

Chaque lot a sa session, sa branche `chantier/boite-<lot>` (base `origin/main`) et sa PR. On demande l'accord de
l'utilisateur avant chaque lot. Le **plan détaillé** d'un lot s'écrit à son démarrage, dans
`docs/superpowers/plans/`, après avoir relevé les formats réels. Seuls A0 et A1 sont détaillés ici.

| Tâche | Lot | Contenu (spec) | Taille | Après |
|---|---|---|---|---|
| t305 | A0 Boîtes de l'agent | §4 — ce plan, tâches 1-3 | M | — |
| t306 | A1 Type d'espace et fiche client | §5.2, §11 bis — ce plan, tâches 4-7 | M | t305 |
| t307 | A3 Projets → canaux | §5.4 : colonne `canaux` (`canal_id`), garde 409, héritage des cibles, sélecteur (maillon) | M | t306 |
| t308 | A2 Assistant de création et vérification des canaux | §5.3 : assistant en 4 temps (maillon), `verifier(compte)` sans publication par plateforme, canal « porté par le téléphone » | L | t307 |
| t309 | A4 Validation client et sécurités | §5.5 : état « à valider », 409 au Planificateur, confirmation nominative, révocation → pause, journal, bandeau « pour qui » | L | t308 |
| t310 | B1 WhatsApp : canal et adaptateur Kapso | §6.1, §6.3 : plateforme `whatsapp` (clé par compte), `services/whatsapp.py`, règles 24 h, accord, STOP, prix Meta dans `pricing`, plafonds | L | t306 |
| t311 | B2 Agent WhatsApp et page WhatsApp | §6.2, §6.4, §6.5 : boîte `whatsapp`, boucle d'outils, brouillon ou auto, page conversations, validation par boutons | L | t310, t309 |
| t312 | C1 Scan : texte | §7.2 : Windows.Media.Ocr (mesuré contre Tesseract), secours Claude vision avec devis, nettoyage, envoi Atelier et Chapitres, boîte `scan` | M | t305 |
| t313 | C3 Inspiration → contenu neuf | §7.4 : angles, carte de devis, brouillon du projet, gardes anti-copie (12 mots) | M | t312, t307 |
| t314 | C2 Scan : illustration → motion | §7.3 : détourage, vectorisation, calques nommés, envoi Animation, ordre de révélation | M | t312 |
| t315 | D1 Capture : enregistreur et sécurité | §8.1-8.3 : Element Capture, voix, caméra, piste des clics, `data-dz-secret`, compositeur canvas | L | t305 |
| t316 | D2 Skins et éditeur | §8.5 | L | t315 |
| t317 | D3 Montage après coup | §8.4 : zooms auto, coupes, chapitres, formats, rendu, Recast en option | L | t316 |
| t318 | D4 Live multi-destinations | §8.6 : WebSocket → ffmpeg → RTMP `tee`, Twitch, YouTube, Kick, RTMP personnalisé, annonce Discord | L | t316 |
| t319 | D5 Tutoriel et parcours partagés | §8.7 : brouillon de tutoriel, `.dzparcours`, rejeu avec le pointeur | M | t317 |
| t320 | Z Clôture : guide, traduction, catalogue | Chapitres du guide, `dzT` FR et EN, `connaissance-agent` sur tout ce qui reste | M | t319 |
| t321 | Compagnon M4 : WhatsApp | Spec mobile §3 | L | t311 |
| t322 | Compagnon M5 : contenu neuf | Spec mobile §4 | M | t313 |
| t323 | Compagnon M6 : capture | Spec mobile §5 (module `dz-capture`) | L | t316 |
| t324 | Compagnon M7 : live | Spec mobile §5 (module RTMP) | L | t318, t323 |

M1 à M3 (clients, projets → canaux, validation) sont **fondus** dans les tâches existantes du lot 4 : L4.2 (compte
client) et L4.3 (Planificateur autonome). Leurs notes au suivi le disent.

## Global Constraints

- Python : `$PY = $env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. Il ignore PYTHONPATH : chaque banc
  insère `backend/` lui-même. On lance depuis `backend/` : `& $PY tests/<banc>.py`.
- Chaque banc pose `DEEPOTUS_DATA_DIR` temporaire et vide les clés (modèle : en-tête de `tests/test_espaces_socle.py`).
- Noms, commentaires et messages en français. Chaque ajout est daté et rattaché à sa tâche (`t305`, `t306`).
- Tout `HTTPException` ou `ValueError` neuf qui remonte à l'écran entre dans `scripts/i18n_l10_traductions.json`
  (indentation 1 espace, CRLF, ordre d'origine), puis `python scripts/i18n_l10_erreurs.py`.
- Écritures : `_require_localhost(request)` sur chaque route qui écrit. Aucune entrée neuve dans
  `_ECRITURES_OUVERTES` dans A0 et A1.
- `espaces.lire()` migre et écrit : on ne l'appelle jamais depuis une boucle de fond.
- La migration de l'espace `deepotus` reste à l'octet (`test_espaces_socle` doit rester vert).
- Messages de commit : `<zone> : <quoi> (tNNN)`, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Avant chaque commit, on lance la série ciblée : bancs neufs, `test_agent_outils`, `test_agent_boucle`,
  `test_agent_campagnes_routes`, `test_agent_campagnes_appareil`, `test_espaces_socle`, `test_espaces_client`,
  `test_espaces_comptes`. Un rouge déjà rouge sur `origin/main` se note, il n'est pas imputé au lot.

## Review Focus

1. Le modèle appelle un outil qui existe mais n'est pas dans la boîte de son agent : refus `{"ok": False}` sans
   exécution (tâche 2).
2. L'espace client parent d'un produit est archivé : le produit garde son client responsable, et donc ses gardes
   (tâche 4).
3. Un `client.json` édité à la main contient une clé inconnue, ou une clé qui ressemble à un secret : elle est
   ignorée à la lecture et jamais exportée (tâches 5 et 6).
4. Un paquet d'espace ancien n'a pas de `mode_publication` : on applique `valide_par_client`, le plus prudent
   (tâches 5 et 6).
5. On veut retirer le type `client` à un espace qui a des consentements en cours : refus, pour que le client ne
   perde pas ses gardes en silence (tâche 4).

---

### Task 1 : figer les définitions actuelles de l'agent Campagnes (t305)

**Files :**
- Create : `backend/tests/_agent_definitions_capture.py` (écrit la fixture)
- Create : `backend/tests/agent_definitions_campagnes.json` (fixture : `ao.definitions()` à e0d6e51e)
- Create : `backend/tests/test_agent_boites.py` (banc ; section 1 seulement à cette tâche)

**Interfaces :**
- Consumes : `agent_outils.definitions() -> list[dict]` (existant).
- Produces : la fixture `agent_definitions_campagnes.json`, lue par la tâche 2.

- [ ] **Étape 1 : écrire le capteur.** `_agent_definitions_capture.py` importe `app.services.agent_outils`, puis
  écrit `json.dumps(ao.definitions(), ensure_ascii=False, indent=1, sort_keys=True)` dans la fixture, en UTF-8 avec
  des fins de ligne LF.
- [ ] **Étape 2 : lancer le capteur sur le code inchangé.** `& $PY tests/_agent_definitions_capture.py`. On attend
  un fichier qui contient 10 objets, et `git diff --stat` ne montre que les fichiers neufs.
- [ ] **Étape 3 : écrire la section 1 du banc.**
  ```python
  # 1. Compatibilité : Campagnes voit exactement les mêmes outils qu'à e0d6e51e
  fige = json.loads((_ICI / "agent_definitions_campagnes.json").read_text(encoding="utf-8"))
  check("1a definitions() inchangées à l'octet", ao.definitions() == fige)
  check("1b dix outils", len(fige) == 10)
  ```
- [ ] **Étape 4 : lancer.** `& $PY tests/test_agent_boites.py`. On attend `2 passed, 0 failed`.
- [ ] **Étape 5 : commit.** `agent : définitions de Campagnes figées avant les boîtes (t305)`.

### Task 2 : `agent_boites.py` et le refus hors boîte (t305)

**Files :**
- Create : `backend/app/services/agent_boites.py`
- Modify : `backend/app/services/agent_outils.py` (`Ctx` gagne `agent` ; `executer` contrôle la boîte)
- Modify : `backend/app/services/agent_campagnes.py:189,246` (`ao.definitions()` → `boites.definitions_pour("campagnes")`)
- Test : `backend/tests/test_agent_boites.py` (sections 2 et 3)

**Interfaces :**
- Consumes : `agent_outils.OUTILS: dict[str, dict]` (clés : `nature`, `fn`, `description`, `schema`).
- Produces :
  - `NATURES: tuple = ("lecture", "ecriture", "carte")`
  - `BOITES: dict[str, dict]` : chaque valeur vaut `{"libelle": str (clé dzT "agent.boites.<id>"), "outils": list[str],
    "agents": list[str], "mobile": bool}`. A0 ne déclare que `"campagnes"` : les dix outils, `agents=["campagnes"]`,
    `mobile=True`. Les autres boîtes sont ajoutées par leur lot (C1 `scan`, B2 `whatsapp`, etc.).
  - `boite_de(outil: str) -> str | None`
  - `outils_pour(agent: str) -> list[str]`, dans l'ordre de `OUTILS`
  - `definitions_pour(agent: str) -> list[dict]`, au même format que `agent_outils.definitions()`
  - `paquet_mobile() -> list[dict]` : `[{"id", "libelle", "outils": definitions}]` pour les boîtes `mobile`
  - `verifier() -> list[str]` : la liste des incohérences (vide = sain)
  - `agent_outils.Ctx.agent: str = "campagnes"`

- [ ] **Étape 1 : écrire les sections 2 et 3 du banc.**
  ```python
  from app.services import agent_boites as B
  # 2. Invariants des boîtes
  check("2a registre sain", B.verifier() == [], B.verifier())
  check("2b chaque outil a exactement une boîte",
        all(sum(o in b["outils"] for b in B.BOITES.values()) == 1 for o in ao.OUTILS))
  check("2c natures connues", all(ao.OUTILS[o]["nature"] in B.NATURES for b in B.BOITES.values() for o in b["outils"]))
  check("2d Campagnes inchangé via les boîtes", B.definitions_pour("campagnes") == fige)
  check("2e agent inconnu = aucun outil", B.definitions_pour("personne") == [])
  check("2f paquet mobile", [b["id"] for b in B.paquet_mobile()] == ["campagnes"]
        and B.paquet_mobile()[0]["outils"] == fige)
  # 3. Le refus hors boîte (asyncio.run)
  r = asyncio.run(ao.executer("lire_espace", {}, ao.Ctx(cid="c1", agent="whatsapp")))
  check("3a outil hors de la boîte refusé", r["ok"] is False and "boîte" in r["resume"])
  r = asyncio.run(ao.executer("chercher_app", {"question": "vectorlab"}, ao.Ctx(cid="c1")))
  check("3b Campagnes garde ses outils", r["ok"] is True)
  ```
- [ ] **Étape 2 : lancer.** On attend un FAIL `No module named 'app.services.agent_boites'`.
- [ ] **Étape 3 : écrire `agent_boites.py`.** Il importe `agent_outils as ao` au niveau du module.
  `verifier()` signale :
  - un outil de boîte absent de `OUTILS` ;
  - un outil de `OUTILS` sans boîte ;
  - un outil présent dans deux boîtes ;
  - une nature hors de `NATURES` ;
  - un `libelle` qui ne commence pas par `agent.boites.`.
- [ ] **Étape 4 : brancher le refus dans `agent_outils.executer`.** Juste après la recherche de `o`, faire un
  import local `from app.services import agent_boites` (pas de cycle au chargement). Si
  `nom not in agent_boites.outils_pour(ctx.agent)`, renvoyer `_res(False, f"{nom} : hors de la boîte de l'agent
  {ctx.agent}")`.
- [ ] **Étape 5 : faire lire les boîtes à `agent_campagnes`.** Aux lignes 189 et 246, remplacer
  `ao.definitions()` par `agent_boites.definitions_pour("campagnes")`. `ao.definitions()` reste en place : elle est
  utilisée par la fixture.
- [ ] **Étape 6 : lancer.** `test_agent_boites` (`10 passed, 0 failed`), puis la série ciblée des Global Constraints : aucun
  rouge neuf.
- [ ] **Étape 7 : mutations.**
  - retirer le refus de l'étape 4 → 3a rougit ;
  - mettre `chercher_app` dans deux boîtes → 2a et 2b rougissent ;
  - changer `mobile` en False → 2f rougit.

  On restaure en copiant les sources avant, et on vérifie avec `cmp` après.
- [ ] **Étape 8 : commit.** `agent : boîtes à outils par fonctionnalité, refus hors boîte (t305)`.

### Task 3 : boîtes dans le paquet du compagnon et documentation (t305)

**Files :**
- Modify : `backend/app/api/agent_campagnes_routes.py:318` (`_paquet` ajoute `boites.json`)
- Modify : `AGENTS.md` (table « Fichiers clés » : ligne `backend/app/services/agent_boites.py`)
- Modify : `frontend/shared/i18n/*.json`, via `scripts/i18n_assembler.py` : clé `agent.boites.campagnes`
  (FR « Campagnes », EN « Campaigns ») ; chercher le texte FR avant d'écrire (une phrase FR = une traduction)
- Test : `backend/tests/test_agent_boites.py` (section 4)

**Interfaces :**
- Consumes : `agent_boites.paquet_mobile()`.
- Produces : `GET /api/agent/campagnes/paquet` → `fichiers["boites.json"]` =
  `json.dumps(paquet_mobile(), ensure_ascii=False, indent=2, sort_keys=True)`. La version change en conséquence.

- [ ] **Étape 1 : écrire la section 4 du banc.**
  ```python
  # 4. Le paquet du compagnon transporte les boîtes
  from app.api import agent_campagnes_routes as R
  p = R._paquet(None)
  check("4a boites.json servi", "boites.json" in p["fichiers"])
  check("4b contenu = paquet_mobile", json.loads(p["fichiers"]["boites.json"]) == B.paquet_mobile())
  ```
- [ ] **Étape 2 : lancer.** On attend que 4a soit FAIL.
- [ ] **Étape 3 : ajouter `boites.json` dans `_paquet`.** On l'ajoute avant le tri final, pour que la version
  reste déterministe.
- [ ] **Étape 4 : relancer.** On attend `test_agent_boites` vert, et `test_agent_campagnes_appareil` vert. S'il fige
  la liste des fichiers du paquet, ajouter `boites.json` à la liste attendue et le noter dans le message de commit.
- [ ] **Étape 5 : ajouter la ligne d'AGENTS.md, la clé i18n et lancer l'assembleur.**
  `python scripts/i18n_assembler.py` (puis `--check` s'il existe). `test_i18n_l0` doit rester vert.
- [ ] **Étape 6 : commit et PR.** Le commit : `agent : boîtes servies au compagnon, doc (t305)`. La PR t305 vise
  `main`. Rien de visible à l'écran, donc pas de fiche `connaissance-agent`. On installe seulement avec l'accord de
  l'utilisateur, selon la méthode du dépôt (table `git hash-object`).

### Task 4 : type d'espace, parent, client responsable (t306)

**Files :**
- Modify : `backend/app/services/espaces.py` (`TYPES`, `creer`, `modifier`, `_vue`, `client_responsable`)
- Modify : `backend/app/api/routes.py:7976,8016` (docstrings : `type`, `parent` acceptés ; erreurs 400 et 409)
- Create : `backend/tests/test_espaces_type_client.py` (sections 1 et 2)

**Interfaces :**
- Produces :
  - `TYPES: tuple = ("marque", "produit", "client")`
  - `_vue(...)` gagne `"type"` (absent du JSON = `"marque"`, sans réécriture) et `"parent"` (`str | None`)
  - `creer(champs)` accepte `type` (défaut `"marque"`) et `parent`, seulement si `type == "produit"`. Le parent doit
    exister et être de type `marque` ou `client`. Toute autre combinaison lève `ValueError`.
  - `modifier(eid, champs)` accepte `type` et `parent`, avec les mêmes règles. Passer de `client` à un autre type
    lève `ConflitClient(ValueError)` si `fiche_client.consentements_en_cours(eid)` n'est pas vide (import local). La
    route le traduit en 409.
  - `client_responsable(eid: str | None = None) -> str | None` : `eid` s'il est de type `client`, sinon son parent
    s'il est de type `client`, même archivé, sinon `None`. Aucune écriture.

- [ ] **Étape 1 : écrire les sections 1 et 2 du banc** (data-dir temporaire, comme `test_espaces_socle`).
  ```python
  E = espaces
  check("1a Deepotus est une marque", E.actif()["type"] == "marque" and E.actif()["parent"] is None)
  octets = (E.dossier() / "espaces.json").read_bytes(); E.lister()
  check("1b lire n'écrit pas le type", (E.dossier() / "espaces.json").read_bytes() == octets)
  c = E.creer({"nom": "Boulangerie Lune", "type": "client"})
  p = E.creer({"nom": "Pain du matin", "type": "produit", "parent": c["id"]})
  check("1c produit d'un client", p["type"] == "produit" and p["parent"] == c["id"])
  check("1d type inconnu refusé", _leve(ValueError, E.creer, {"nom": "x", "type": "agence"}))
  check("1e parent sur une marque refusé", _leve(ValueError, E.creer, {"nom": "x", "type": "marque", "parent": c["id"]}))
  check("1f produit d'un produit refusé", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": p["id"]}))
  check("1g parent inconnu refusé", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": "esp_00000000"}))
  # 2. Client responsable
  check("2a client lui-même", E.client_responsable(c["id"]) == c["id"])
  check("2b produit → son client", E.client_responsable(p["id"]) == c["id"])
  check("2c marque → aucun", E.client_responsable("deepotus") is None)
  E.archiver(c["id"])
  check("2d client archivé reste responsable", E.client_responsable(p["id"]) == c["id"])
  ```
  `_leve(exc, fn, *a)` est un petit utilitaire du banc. 2e (retirer le type client avec un consentement en cours,
  refus 409) est écrit à la tâche 5, car il demande la fiche.
- [ ] **Étape 2 : lancer.** On attend que 1a soit FAIL (`KeyError: 'type'`).
- [ ] **Étape 3 : implémenter dans `espaces.py`.** `creer` écrit `type` et `parent` dans l'entrée ; une marque ou
  un client a `parent: None`. `archiver` n'est pas modifié.
- [ ] **Étape 4 : passer les routes.** `POST /espaces` et `POST /espaces/{id}` laissent passer `type` et `parent`.
  `ConflitClient` donne 409, avant `ValueError` qui donne 400. Les messages neufs entrent dans
  `i18n_l10_traductions.json`.
- [ ] **Étape 5 : lancer.** On attend `test_espaces_type_client` vert, puis `test_espaces_socle`,
  `test_espaces_client`, `test_espaces_onboarding` et `test_espaces_ecran` verts.
- [ ] **Étape 6 : commit.** `espaces : type marque/produit/client, parent, client responsable (t306)`.

### Task 5 : la fiche client et ses consentements (t306)

**Files :**
- Create : `backend/app/services/fiche_client.py`
- Modify : `backend/app/services/espaces.py:39` (`FICHIERS` gagne `"client.json"`)
- Modify : `backend/app/api/routes.py` (quatre routes après `/espaces/{espace_id}/persona`)
- Create : `backend/tests/fixtures_client_v1.json` (fixture de format, pour le compagnon L4.2)
- Test : `backend/tests/test_espaces_type_client.py` (sections 3 et 4)

**Interfaces :**
- Consumes : `espaces.chemin(eid, "client.json")`, `espaces.lire()`, `espaces._ecrire_json`.
- Produces :
  - `CANAL_ID = re.compile(r"^[a-z_]{2,20}:[A-Za-z0-9_.@-]{1,120}$")`
  - `MODES = ("valide_par_client", "publie_en_son_nom")`, défaut `"valide_par_client"`
  - `MOYENS = ("ecrit", "whatsapp", "doigt")`
  - Format v1 :
    ```json
    {"version": 1, "societe": "", "contact": {"nom": "", "email": "", "whatsapp": ""}, "pays": "", "langue": "fr",
     "notes": "", "mode_publication": "valide_par_client",
     "consentements": [{"canal_id": "x:123", "permis": ["publier"], "date": "ISO", "moyen": "ecrit", "revoque_le": null}],
     "journal": [{"quand": "ISO", "quoi": "mode|consentement|revocation|publication|validation|import", "canal_id": "x:123", "qui": "utilisateur|client|telephone"}]}
    ```
  - `lire(eid) -> dict` : la fiche normalisée. Les clés inconnues sont ignorées, et les valeurs absentes sont
    remplacées par les défauts. `KeyError` si l'espace est inconnu, `ValueError` s'il n'est pas de type `client`.
  - `ecrire(eid, champs) -> dict` : modifie `societe`, `contact`, `pays` (ISO 3166 alpha-2 ou vide), `langue`
    (`fr` | `en`), `notes` (4000 caractères au plus) et `mode_publication`. Un changement de mode est noté au journal.
    Les clés `consentements` et `journal` sont refusées ici (`ValueError`).
  - `ajouter_consentement(eid, canal_id, permis: list[str], moyen) -> dict` : nouvelle ligne datée, et journal
    `consentement`.
  - `revoquer(eid, canal_id) -> dict` : pose `revoque_le` sur la ligne en cours, et journal `revocation`.
    `KeyError` s'il n'y a rien à révoquer.
  - `consentements_en_cours(eid) -> list[dict]` (`revoque_le is None`)
  - `consentement_en_cours(eid, canal_id) -> bool`
  - `noter(eid, quoi, canal_id, qui) -> None` (journal, 2000 lignes au plus, les plus anciennes sortent)
  - `valider(doc) -> dict` : normalisation pure, partagée par `lire` et l'import (tâche 6)
  - Routes, toutes avec `_require_localhost` sauf le GET :
    - `GET /espaces/{id}/client`
    - `PUT /espaces/{id}/client`
    - `POST /espaces/{id}/client/consentements` (corps `{canal_id, permis, moyen}`)
    - `POST /espaces/{id}/client/consentements/revoquer` (corps `{canal_id}`)

    Inconnu → 404. Pas de type client, ou entrée fautive → 400.

- [ ] **Étape 1 : écrire les sections 3 et 4 du banc.**
  ```python
  from app.services import fiche_client as F
  f = F.lire(c["id"])
  check("3a défauts prudents", f["mode_publication"] == "valide_par_client" and f["consentements"] == [])
  check("3b marque sans fiche", _leve(ValueError, F.lire, "deepotus"))
  F.ecrire(c["id"], {"societe": "Lune SARL", "mode_publication": "publie_en_son_nom", "jeton_x": "sk-123"})
  brut = E.chemin(c["id"], "client.json").read_text(encoding="utf-8")
  check("3c clé inconnue jamais écrite", "jeton_x" not in brut and "sk-123" not in brut)
  check("3d changement de mode au journal", F.lire(c["id"])["journal"][-1]["quoi"] == "mode")
  check("3e canal_id fautif refusé", _leve(ValueError, F.ajouter_consentement, c["id"], "x 123", ["publier"], "ecrit"))
  F.ajouter_consentement(c["id"], "instagram:17841400000", ["publier"], "doigt")
  check("3f consentement en cours", F.consentement_en_cours(c["id"], "instagram:17841400000"))
  check("3g écrire ne touche pas aux consentements", _leve(ValueError, F.ecrire, c["id"], {"consentements": []}))
  # 2e : le type client ne se retire pas tant qu'un consentement court
  check("2e retrait du type client refusé", _leve(E.ConflitClient, E.modifier, c["id"], {"type": "marque"}))
  F.revoquer(c["id"], "instagram:17841400000")
  check("3h révoqué", not F.consentement_en_cours(c["id"], "instagram:17841400000")
        and F.lire(c["id"])["journal"][-1]["quoi"] == "revocation")
  # 4. Routes (TestClient local, puis client réseau → 403 sur les écritures)
  ```
  Section 4 : GET 200, PUT 200, POST consentement 200, revoquer 200 puis 404 au second appel, espace inconnu 404,
  et `TestClient(app, client=("192.168.1.20", 50000))` avec un jeton (`tests/_jeton_appareil.entetes(app)`) → 403
  sur le PUT.- [ ] **Étape 2 : lancer.** On attend un FAIL `No module named 'app.services.fiche_client'`.
- [ ] **Étape 3 : implémenter `fiche_client.py` et les routes.** On écrit par `espaces._ecrire_json`, qui gère le
  remplacement atomique et la reprise sous Windows. Les messages neufs vont dans `i18n_l10_traductions.json`.
- [ ] **Étape 4 : écrire la fixture.** On produit `fixtures_client_v1.json` avec `F.valider` sur un exemple
  complet (deux consentements, dont un révoqué, et trois lignes de journal), et le banc vérifie
  `F.valider(fixture) == fixture`. C'est le format que L4.2 reprend côté téléphone.
- [ ] **Étape 5 : lancer.** On attend `test_espaces_type_client` vert, puis la série ciblée, puis
  `test_i18n_l10` (pas de rouge neuf par rapport à `origin/main`).
- [ ] **Étape 6 : mutations.**
  - défaut `publie_en_son_nom` → 3a rougit ;
  - accepter les clés inconnues → 3c rougit ;
  - `consentement_en_cours` sans contrôle de `revoque_le` → 3h rougit ;
  - retirer `ConflitClient` → 2e rougit.
- [ ] **Étape 7 : commit.** `espaces : fiche client, mode de publication, consentements datés (t306)`.

### Task 6 : la fiche dans le paquet d'espace (t306)

**Files :**
- Modify : `backend/app/services/espaces_paquet.py:35` (`_JSONS` gagne `"client.json"` ; `exporter` écrit
  `type` et `parent` dans `espace.json` et la fiche validée ; `importer` les relit)
- Test : `backend/tests/test_espaces_type_client.py` (section 5)

**Interfaces :**
- Consumes : `fiche_client.valider`, `espaces.creer`.
- Produces :
  - un export d'espace client contient `client.json` = `fiche_client.valider(fiche)` ;
  - à l'import, l'espace neuf garde le `type`. Le `parent` est gardé s'il existe dans l'instance, sinon il est retiré
    et signalé dans `ignores`. Une fiche sans `mode_publication` reçoit `valide_par_client`.

- [ ] **Étape 1 : écrire la section 5 du banc.**
  - export du client `c` → zip qui contient `client.json` sans `sk-` ni `jeton` ;
  - import → espace neuf de type `client`, fiche identique hors `journal`, avec une ligne `import` ajoutée ;
  - paquet dont la fiche n'a pas de `mode_publication` → `valide_par_client` ;
  - import d'un produit dont le parent est absent → `parent is None` et motif dans `ignores`.
- [ ] **Étape 2 : lancer.** On attend un FAIL.
- [ ] **Étape 3 : implémenter.** On respecte la règle de t210 : tout est validé **avant** la première écriture,
  avec un retour arrière complet en cas d'échec.
- [ ] **Étape 4 : lancer.** On attend `test_espaces_type_client` et `test_espaces_client` (111 contrôles) verts.
- [ ] **Étape 5 : commit.** `espaces : la fiche client voyage dans le paquet d'espace (t306)`.

### Task 7 : documentation et PR (t306)

**Files :**
- Modify : `AGENTS.md` (ligne `backend/app/services/fiche_client.py`, et une phrase sous « Architecture » : type
  d'espace et client responsable)
- Modify : `docs/agent/AGENT.md`, seulement si un libellé visible a changé (aucun en A1 : l'assistant de création
  arrive en t308)

- [ ] **Étape 1 : mettre à jour AGENTS.md.**
- [ ] **Étape 2 : passer la série ciblée complète et noter les rouges préexistants** (comparés à `origin/main`).
- [ ] **Étape 3 : commit et PR t306.** Le commit : `espaces : doc type et fiche client (t306)`. On installe avec
  l'accord de l'utilisateur : table `git hash-object` juste avant la copie, sauvegarde `_backup_predeploy_<date>-t306`,
  pas de migration de base (les fichiers JSON se lisent avec leurs défauts).
