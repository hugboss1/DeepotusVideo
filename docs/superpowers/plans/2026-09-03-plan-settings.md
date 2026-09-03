# Settings — clés, diagnostic, plafonds, coffre, mises à jour — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à l'écran Settings de DeepotusVideoGen ce qui lui manque pour être crédible (diagnostic en un écran, plafonds de dépense gardés par le backend, test de clé à l'enregistrement avec guide, vérification de mise à jour, export manuel des données), puis ce qu'aucune référence ne fait (coffre à mot de passe maître dont l'archive chiffrée nourrit le téléphone, dépenses réel contre estimé par catégorie, recherche dans les réglages).

**Architecture:** Tout le mécanisme vit dans le backend (nouveaux modules `diagnostic`, `plafonds`, `guides_fournisseurs`, `mise_a_jour`, `export_donnees`, `dpapi`, `coffre`, un routeur `settings_routes.py` inclus dans `main.py` comme les routeurs montage/cards) ; l'écran Settings du bundle est patché par UN patcheur chaîné `scripts/patch_bundle_reglages.py` (tag neuf `reglages`, en queue après `seedance25`) qui grossit d'une section par tâche. La garde des plafonds est une seule fonction `plafonds.verifier(op, categorie, confirmation)` appelée en tête de chaque route payante ; la confirmation voyage dans un en-tête HTTP que le bundle rejoue via un seul wrapper de `fetch`. Le chiffrement est AES-256-GCM par la roue `cryptography` embarquée au build (mesure en Lot 2, tâche 14), PBKDF2-HMAC-SHA256 en stdlib, et DPAPI (`ctypes`, stdlib) protège au repos la clé dérivée « retenue sur ce PC ».

**Tech Stack:** Python 3.13 embarqué (stdlib + Pillow + les roues de `backend/requirements.txt`), FastAPI/SQLAlchemy async/SQLite, httpx, `cryptography` (ajoutée), bundle React minifié patché (`r` = jsx runtime, `x` = React, `te` = badge, `jt` = carte, `K` = bouton), bancs autonomes `backend/tests/test_<x>.py` lancés un par processus.

---

## Périmètre

Source : `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md` § R11 (réponses 1–8, bacs), § R12 (P2 : l'archive chiffrée de D1 est LUE par le téléphone — ici on la produit et on fige son format ; la lecture se planifie dans le plan mobile), § R9 P6 (poids sur disque par catégorie, réutilisé par le diagnostic).

**Lot 1 — parité, dans l'ordre** : P1 diagnostic en un écran · P2 plafonds de dépense · P3 test de clé à l'enregistrement + guide par fournisseur · P4 vérification de mise à jour · P5 export manuel des données.

**Lot 2 — différenciant** : D1 coffre à mot de passe maître + archive chiffrée (première tâche = MESURE avec table de décision) · D2 dépenses par catégorie, réel contre estimé · D3 recherche dans les réglages.

**Écarté** (E1 profils, E2 sauvegarde programmée, E3 coffres multiples) : rien n'est construit, voir la section « Écarté ».

### Ce que le code fait aujourd'hui (relu le 03/09/2026, lignes réelles)

- `backend/app/config.py` : `APP_VERSION = "2.6.0"` (l. 22), `DATA_ROOT` = `%LOCALAPPDATA%\DeepotusVideoGenData` (l. 25–36), `ENV_FILE = DATA_ROOT / ".env"` chargé avec `override=True` AVANT `Settings()` (l. 38–50) ; les clés sont des champs `str` de `Settings` (FAL_KEY, ELEVENLABS_API_KEY, HEYGEN_API_KEY, MESHY_API_KEY, FIGMA_TOKEN, ANTHROPIC/OPENAI/GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, X_* ×4, OLLAMA_URL).
- `backend/app/api/routes.py` (9 575 lignes) : `/health` l. 3460 ; `_ALLOWED_ENV_KEYS` l. 3502 (**sans FIGMA_TOKEN**, alors que l'import Figma le lit, l. 8807) ; `_read_env_file` l. 3525, `_mask` l. 3539, `_require_localhost` l. 3547 (accepte `testclient`), `GET/POST /settings/keys` l. 3555/3568 (réécrit le `.env` en clair, répond `restart_required: True`), `/settings/provider-defaults` l. 3621/3645, `/cost/estimate` l. 4158, `_job_to_cost` l. 4166, `/cost/usage` l. 4196 (**estimé, uniquement depuis les `JobRecord` finis** : `/images/generate`, `/audio/*`, `/materials/generate`, les LLM et le proxy Meshy ne créent pas de job, donc ne sont pas comptés), `/cost/balances` l. 4214 (HeyGen `remaining_quota`, ElevenLabs `/v1/user/subscription`, Voicebox local), `/cost/pricing` l. 4259/4265, `/atelier/settings` l. 4989/5066.
- **Aucun point d'entrée commun aux routes payantes** (mesuré) : `/generate` l. 2806, `/generate/batch` l. 2846, `/generate/heygen` l. 3025, `/generate/heygen-image` l. 3047, `/generate/heygen-cinematic` l. 3070, `/generate/composition` l. 3092, `/images/generate` l. 4424 → `_generate_image_core` l. 4442, `/audio/voiceover` l. 2405, `/audio/sfx` l. 2209, `/audio/music` l. 2269, `/episodes/render` l. 2680, `/assets/3d` l. 352, `/assets/3d/{job}/refine` l. 612, `/assets/3d/{job}/texturer` l. 718, `/assets/sprite` l. 1374, `/materials/generate` l. 7302, `/meshy/{path}` l. 1240, `/marketing/plan` l. 4273, `/news/script` l. 1949 ; côté cards : `services/cards/face.py:2503` (`/serie/generer`), `services/cards/forge3d.py:3004` (`/mesh3d/{nid}`). Chacune vérifie sa clé elle-même. `pricing.estimate` n'est appelé qu'en devis d'affichage (routes l. 538, 540, 779, 4163, 4171–4190 ; cards `face.py:2011`, `forge3d.py:420, 2906`).
- `backend/app/services/pricing.py` : `DEFAULTS` (dont `monthly_budget_usd: 0.0`, jamais lu par une garde), `load/save` sur `DATA_ROOT/pricing.json`, `estimate(op)` par `kind`.
- Coûts réels : `MeshyTaskRecord.consumed_credits` (`storage.py:71`, écrit par `meshy_service.record_state` l. 446) ; HeyGen : `HeyGenClient.remaining_quota()` (`heygen_service.py:175`) existe mais **aucun coût réel HeyGen n'est enregistré** ; `JobRecord.cost_meta` (`storage.py:52`) porte des entrées de calcul, pas de réel.
- `backend/app/main.py` : `lifespan` l. 118 (boot : `init_db`, `library_index.reconcilier()`, tâches `news_daily_loop` / `schedule_loop`), routeurs montage/cards inclus avec les marqueurs `__DZ_*_ROUTER_BEGIN/END__` l. 235–242, journal `DATA_ROOT/logs/deepotus-YYYY-MM-DD.log` (loguru, rotation 10 Mo, 14 jours).
- Build : `scripts/build-installer.ps1` l. 128–141 installe `backend/requirements.txt` par `pip install --target runtime\python\site-packages` avec le python de build (PATH, 3.13.15) ; l'installeur est l'asset de Release GitHub. **Mesuré le 03/09** : le runtime installé (`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python`, 200 paquets) ne contient ni `cryptography` ni `cffi` ; le python de build a `cryptography 46.0.7` et `cffi 2.0.0`. Le runtime embarqué porte déjà `_ctypes.pyd`, `libffi-8.dll`, `_hashlib.pyd`, `libcrypto-3.dll` : `ctypes`, `hashlib.pbkdf2_hmac` et `hashlib.scrypt` y marchent (vérifié en lançant le `python.exe` embarqué), **mais toujours aucun AES**.
- **Les clés sont lues à l'appel, jamais figées à l'import** (mesuré le 03/09) : zéro capture de clé au niveau module ; les 40 lectures de `settings.FAL_KEY` / `HEYGEN_API_KEY` / `MESHY_API_KEY` / `ELEVENLABS_API_KEY` sont toutes dans des corps de fonction, et la seule capture d'instance est `heygen_service.py:60` (`self.api_key = api_key or settings.HEYGEN_API_KEY`, relue à chaque `HeyGenClient()`). **Une seule exception** : `fal_service.py:34-35` recopie `settings.FAL_KEY` dans `os.environ["FAL_KEY"]` À L'IMPORT (le client fal lit l'environnement) — l'application à chaud de T8 doit donc écrire les DEUX, et c'est la raison pour laquelle `restart_required` peut enfin devenir faux.
- **Poids réel de `DATA_ROOT`** (mesuré le 03/09 : marche complète en **4,30 s**, 9 911 fichiers, **14 855 500 770 o**) : `assets` 8 329 588 860 (dont `assets/outputs` 7 048 698 064, `assets/images` 1 061 612 814, `assets/print3d` 184 812 948, `assets/audio` 34 022 210), `rebut_decks_2026-08-26` **6 515 793 339**, `deepotus.db` 4 599 808 (+ `-wal` 4 544 392), `logs` 834 541, `cardforge_series` 47 478, `cardforge_models` 10 796 ; 359 613 362 176 o libres sur le volume. Ces deux chiffres commandent deux choix : le cache de 300 s du diagnostic (T1 — 4,3 s par mesure, insupportable à chaque ouverture d'écran) et la case « exclure les rebuts » de l'export (T12 — 6,5 Gio sur 13,8, presque la moitié).
- Bundle `frontend/dist/assets/index-BEOJX8L5.js` : 1 395 299 o, 11 884 CRLF, 0 LF isolé ; chaîne détectée (`repatch_all.py --list`) : … `dzrailmotion` → `version` → `dznodecat` → `seedance25` (queue). L'écran Settings est un composant du bundle : barre latérale = tableau littéral `{k:"keys",l:"API keys"},…,{k:"pricing",l:"Pricing & budget"}` ; corps = `s==="keys"&&r.jsx(bm,{})`, … `s==="pricing"&&r.jsx(DzPricing,{})` ; `bm` = écran clés (tableau `Fu` des clés, lignes `Fu.map((k,c)=>…)`, grille `"220px 1fr auto auto"`) ; `DzPricing` = composant React déjà injecté (preuve que `x.useState`/`r.jsx` sont accessibles depuis une fonction injectée à la portée du module).

---

## Coût de patch

Un seul patcheur, `scripts/patch_bundle_reglages.py`, tag NEUF `reglages`, EN QUEUE de chaîne. Il grossit d'une section par tâche et se relance EN ENTIER à chaque fois (il restaure son `.bak_reglages` puis réapplique tout). **Huit ancres en tout**, toutes comptées à **1** dans le bundle du 03/09/2026 (vérifié avant d'écrire ce plan) ; les tâches suivantes réutilisent les mêmes ancres en allongeant leurs chaînes de remplacement, ce qui est le vrai coût marginal : quasi nul.

| Tâche | Côté | Coût de patch |
|---|---|---|
| T1, T2 (P1 moteur) | backend | `diagnostic.py`, `settings_routes.py`, montage dans `main.py` — **0 patch** |
| T3 (P1 écran) | bundle | **S1+S2+S3**, quatre ancres neuves : `}function DzPricing(){` (bloc de composants), `[{k:"keys",l:"API keys"},` (barre latérale), `const ym=["keys",` (**liste blanche des sections** — sans elle `?section=diag` retombe sur `accounts`), `s==="pricing"&&r.jsx(DzPricing,{})]})` (branches du corps) |
| T4, T5, T6 (P2 moteur) | backend | table `depenses`, `plafonds.py`, garde en tête de 21 routes, middleware de confirmation, coût réel Meshy/HeyGen — **0 patch** |
| T7 (P2 écran) | bundle | **S4** : `DzPlafonds` + l'IIFE qui enveloppe `window.fetch` (402 → barre de confirmation → rejeu avec l'en-tête). **0 ancre neuve** — le bloc S1 et la branche S3 suffisent |
| T8 (P3 moteur) | backend | `guides_fournisseurs.py`, `FIGMA_TOKEN` ouvert à l'écriture, application à chaud, test à l'enregistrement — **0 patch** |
| T9 (P3 écran) | bundle | **S5**, cinq ancres neuves : `,health:"has_meshy"}];function bm(){` (fin du tableau `Fu`), `gridTemplateColumns:"220px 1fr auto auto",gap:14` (la ligne passe à 5 colonnes), `children:h&&h.set?"set":"missing"}),` (insertion de `DzTestCle`), et les **deux** formes complètes du message de redémarrage — le fragment commun apparaît deux fois, donc on ancre sur les deux phrases entières |
| T10 (P4 moteur) | backend | `mise_a_jour.py`, quatre routes, tâche de fond au lancement — **0 patch** |
| T11 (P4 écran) | bundle | **S6** : bandeau en DOM pur + `DzMaj` dans `DzDiag`. **0 ancre neuve** (le bandeau ne touche aucun JSX) |
| T12 (P5 moteur) | backend | `export_donnees.py`, trois routes — **0 patch** |
| T13 (P5 écran) | bundle | **S7** : `DzExport` + entrée « Sauvegarde ». **0 ancre neuve** — S2a, S2b et S3 sont déjà consommées, on allonge |
| T14–T16 (D1 moteur) | backend + build | `requirements.txt` (+`cryptography`), garde d'import dans `build-installer.ps1`, `dpapi.py`, `coffre.py`, routes `/coffre/*`, `.env` vidé de ses secrets — **0 patch** |
| T17 (D1 écran) | bundle | **S8** : `DzCoffre` + entrée « Coffre ». **1 ancre ÉLARGIE** : celle de la pastille d'état d'une clé, reprise en incluant le ton, parce que `list_keys` rend désormais `set: null` (coffre verrouillé) et qu'une pastille rouge « missing » sur une clé qui existe serait un mensonge |
| T18 (D2) | backend + bundle | `plafonds.tableau()` + route `/depenses` ; **S9** : `DzDepenses` monté **deux fois** (Pricing & budget, et Diagnostic — la réponse 3 de R11 range les dépenses du mois parmi ce que le diagnostic doit montrer). **0 ancre neuve** |
| T19 (D3) | backend + bundle | route `/index` ; **S10**, une ancre neuve : `className:"upper",style:{padding:"0 10px 10px"},children:"Settings"}),` — le champ s'insère DANS la portée de `xm`, seul endroit du bundle où le setter de section est accessible, ce qui permet à un résultat d'OUVRIR sa section |
| T20 | tests | `mutations_settings.py` — **0 patch** |

**Règles du patcheur**, toutes tenues par le banc `test_patch_reglages.py` : backup dédié `.js.bak_reglages` ; marqueur `__dzReglages` ; garde de chaîne (`--force-unchained` pour `repatch_all.py`) ; `--check` n'écrit rien ; lecture et écriture VERBATIM (`newline=""`), refus si le bundle porte un LF isolé AVANT ou APRÈS ; le JS injecté ne contient **aucun saut de ligne** (dans un fichier 100 % CRLF, un `\n` seul EST une régression de fins de ligne) ; aucune ancre n'est imprimée (console Windows en cp1252) ; vérification par `python scripts/qa/inventory_bundle.py --diff avant.json`, dont les seuls écarts admis sont les noms de fonctions du bloc injecté.

**Position en queue, mesurée** : `.bak_seedance25` date du 28/08 18:14:55 et le bundle du 02/09 23:05:45 ; `shutil.copy2` préservant le mtime de la source, `.bak_reglages` naîtra daté du 02/09 et se rangera donc bien après `seedance25` dans la chaîne lue par `repatch_all.py --list`. Aucun `ensure_tail_order` n'est nécessaire ici (il existe dans `patch_bundle_cardforge.py` et `patch_bundle_card3d_library.py` pour les cas où le bundle est plus vieux que le dernier `.bak`).

**Après chaque patch** : copier le bundle vers `%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\` et comparer par `git hash-object` — **jamais** par un sha256 d'octets, que `core.autocrlf` ferait diverger sur tout l'arbre. Puis c'est **l'utilisateur** qui relance l'application.

---

## Références vérifiées

| Point | Source | Date | Statut |
|---|---|---|---|
| `GET /repos/{owner}/{repo}/releases/latest` ; champs `tag_name`, `name`, `body`, `html_url`, `published_at`, `assets[].name/size/browser_download_url` ; `Accept: application/vnd.github+json` | docs.github.com/en/rest/releases/releases | 03/09/2026 | vérifié |
| Le dépôt est public : `https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest` répond sans jeton — `tag_name: v2.6.0`, asset `DeepotusVideoGen-Setup-2.6.0.exe`, 129 635 836 o | appel réel (WebFetch) ; remote `git config --get remote.origin.url` = `https://github.com/hugboss1/DeepotusVideo.git` | 03/09/2026 | vérifié |
| `cryptography 50.0.1` embarquable : `pip download --only-binary=:all: --python-version 3.13 --platform win_amd64 "cryptography>=46"` rend TROIS roues — `cryptography-50.0.1-cp311-abi3-win_amd64.whl` **3 842 826 o** (abi3 → valable en 3.13), `cffi-2.1.1-cp313-cp313-win_amd64.whl` **185 688 o**, `pycparser-3.0-py3-none-any.whl` **48 172 o** ; total **4 076 686 o**, installées par `pip install --target` : **11 389 540 o** | `pip download` puis `pip install --target` réels | 03/09/2026 | **mesuré** |
| Ces roues marchent SOUS LE RUNTIME EMBARQUÉ : le `python.exe` de `%LOCALAPPDATA%\DeepotusVideoGen\runtime\python` (3.13.15) avec un `sys.path.insert` sur le dossier cible importe `cryptography 50.0.1` et fait l'aller-retour AES-256-GCM (`AESGCM.encrypt` / `decrypt`, AAD comprise). `PYTHONPATH` seul NE marche PAS : le `._pth` de l'embeddable ignore la variable — c'est `sys.path.insert` ou rien | exécution réelle du binaire installé | 03/09/2026 | **mesuré** |
| DPAPI par `ctypes` sous le MÊME runtime embarqué : `CryptProtectData` sur 19 o rend **246 o**, `CryptUnprotectData` rend l'original, une entropie différente échoue ; `hashlib.pbkdf2_hmac("sha256", …, 600 000)` = **0,42 s**, `hashlib.scrypt(n=2**15, r=8, p=1)` = **0,14 s** | exécution réelle | 03/09/2026 | **mesuré** |
| `CryptProtectData(pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)` dans `Crypt32.dll`, lié aux identifiants de session de l'utilisateur, `CRYPTPROTECT_UI_FORBIDDEN`, sortie à libérer par `LocalFree` | learn.microsoft.com (dpapi.h) | 03/09/2026 | vérifié |
| Telegram `https://api.telegram.org/bot<token>/getMe` → `{ok, result:{id, username, is_bot}}` | core.telegram.org/bots/api#getme | 03/09/2026 | vérifié |
| X `GET /2/users/me` → `data.id`, `data.username` (OAuth 2.0 user context documenté ; le chemin OAuth 1.0a de tweepy `Client.get_me()` : de mémoire) | docs.x.com | 03/09/2026 | partiel |
| Gemini `GET https://generativelanguage.googleapis.com/v1beta/models` → `models[].name` (clé en query dans la doc ; le dépôt impose l'en-tête `x-goog-api-key`, `tests/test_gemini_model.py`) | ai.google.dev/api/models | 03/09/2026 | vérifié |
| Anthropic `GET /v1/models` (sans bêta) ; en-têtes `x-api-key` + `anthropic-version: 2023-06-01` tels que `marketing.py:137` | skill claude-api (cache 24/06/2026) + code | 03/09/2026 | vérifié |
| fal : `Authorization: Key <clé>` ; statut d'une requête `GET https://queue.fal.run/{model}/requests/{id}/status` → 404 pour un id inconnu ; le 401 sur clé invalide n'est pas documenté | fal.ai/docs/model-endpoints/queue | 03/09/2026 | partiel (401 : à vérifier à l'essai manuel) |
| HeyGen `GET /v2/user/remaining_quota`, ElevenLabs `GET /v1/user/subscription`, Meshy `GET openapi/v1/balance` | code du dépôt (`heygen_service.py:181`, `routes.py:4237`, `meshy_service.py:61`) | 03/09/2026 | vérifié (déjà en production) |
| OpenAI `GET https://api.openai.com/v1/models` (Bearer) ; Figma `GET https://api.figma.com/v1/me` (`X-Figma-Token`) ; Ollama `GET {OLLAMA_URL}/api/tags` | docs inaccessibles (403) ou page d'intro seulement | 03/09/2026 | **de mémoire, à vérifier** à l'essai manuel de T8 |
| 1Password, Bitwarden, Raycast, VS Code, Docker Desktop, Obsidian | — | — | de mémoire, non utilisés comme argument |

Pièges hérités appliqués : mesurer avant d'affirmer ; bancs-miroirs (relire le `.env`, le `coffre.json`, l'archive, les réponses JSON — jamais le code qui prétend les produire) ; le navigateur voit, Python écrit ; un plan par catégorie.

---

## Lot 1 — parité

### Task 1 : Diagnostic — poids disque, journal, tests de clés (moteur)

**Files:**
- Create: `backend/app/services/diagnostic.py`
- Test: `backend/tests/test_diagnostic.py`

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Diagnostic en un écran (plan Settings T1) — poids disque par catégorie,
journal des erreurs, tests de clés par fournisseur. ZÉRO réseau : les deux
hooks HTTP du module sont remplacés.
Run: python tests/test_diagnostic.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import diagnostic as D                          # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

def test_poids_disque_par_categorie():
    (_tmp / "assets" / "images").mkdir(parents=True)
    (_tmp / "assets" / "images" / "a.png").write_bytes(b"x" * 1000)
    (_tmp / "logs").mkdir(); (_tmp / "logs" / "d.log").write_bytes(b"y" * 10)
    (_tmp / "rebut_decks_2026-08-26").mkdir()
    (_tmp / "rebut_decks_2026-08-26" / "z.bin").write_bytes(b"z" * 500)
    r = D.poids_disque(_tmp, cache_s=0)
    cats = {c["nom"]: c for c in r["categories"]}
    check(cats["Images (Bibliothèque)"]["octets"] == 1000, "images = 1000 o")
    check(cats["Images (Bibliothèque)"]["fichiers"] == 1, "images : 1 fichier")
    check(cats["Journal"]["octets"] == 10, "journal = 10 o")
    check(cats["Rebuts"]["octets"] == 500 and "rebut_decks_2026-08-26" in cats["Rebuts"]["chemin"], "rebut_* compté à part")
    check(r["total_octets"] == 1510, f"total = 1510 (lu {r['total_octets']})")
    check(r["libre_octets"] > 0, "espace libre lu")
    (_tmp / "assets" / "images" / "b.png").write_bytes(b"x" * 5)
    check(D.poids_disque(_tmp, cache_s=300)["total_octets"] == 1510, "cache 300 s tenu")
    check(D.poids_disque(_tmp, cache_s=0)["total_octets"] == 1515, "cache 0 = relu")

def test_journal_erreurs():
    lg = _tmp / "logs" / "deepotus-2026-09-03.log"
    lg.write_text("2026-09-03 10:00:00.000 | INFO     | app.x:f:1 - rien\n"
                  "2026-09-03 10:00:01.000 | WARNING  | app.y:g:2 - attention\n"
                  "2026-09-03 10:00:02.000 | ERROR    | app.z:h:3 - cassé\n", encoding="utf-8")
    j = D.journal_erreurs(_tmp / "logs", n=10)
    check([l["niveau"] for l in j] == ["WARNING", "ERROR"], "INFO filtré, ordre du fichier")
    check(j[1]["message"] == "cassé" and j[1]["quand"].startswith("2026-09-03 10:00:02"), "message et horodatage lus")

def _faux_http(reponses):
    async def _get(url, headers=None, timeout=15.0):
        for frag, (code, corps) in reponses.items():
            if frag in url: return code, corps
        return 599, {"detail": "url inattendue " + url}
    return _get

def test_tests_de_cles():
    async def sc():
        D._get = _faux_http({"queue.fal.run": (404, {"detail": "Request not found"}),
                             "api.elevenlabs.io": (200, {"character_count": 100, "character_limit": 1000}),
                             "api.meshy.ai": (200, {"balance": 8240}),
                             "api.anthropic.com": (401, {"error": {"message": "invalid x-api-key"}}),
                             "api.openai.com": (200, {"data": [{"id": "gpt-4o-mini"}]}),
                             "generativelanguage": (200, {"models": [{"name": "models/gemini-flash-latest"}]}),
                             "api.figma.com": (200, {"handle": "olivier"}),
                             "api.telegram.org": (200, {"ok": True, "result": {"username": "deepotus_bot"}}),
                             "11434": (200, {"models": [{"name": "qwen2.5:14b"}]})})
        r = {n: await D.tester_cle(n, "k") for n in ("FAL_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY",
             "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN", "OLLAMA_URL")}
        check(r["FAL_KEY"]["ok"] is True and "404" in r["FAL_KEY"]["message"], "fal : 404 sur id fictif = clé acceptée")
        check(r["ELEVENLABS_API_KEY"]["ok"] and r["ELEVENLABS_API_KEY"]["details"]["restant"] == 900, "11L : restant = limite − utilisé")
        check(r["MESHY_API_KEY"]["details"]["credits"] == 8240, "meshy : solde")
        check(r["ANTHROPIC_API_KEY"]["ok"] is False and "invalid x-api-key" in r["ANTHROPIC_API_KEY"]["message"], "anthropic : 401 → message du fournisseur")
        check(r["TELEGRAM_BOT_TOKEN"]["details"]["bot"] == "deepotus_bot", "telegram : username")
        check(all("clé" not in json.dumps(v).lower() or "k" not in json.dumps(v).split() for v in r.values()), "aucune valeur de clé recopiée")
        D._get = _faux_http({})
        r2 = await D.tester_cle("OPENAI_API_KEY", "k")
        check(r2["ok"] is None and "indéterminé" in r2["message"], "code inattendu → indéterminé, pas rouge")
        r3 = await D.tester_cle("X_API_KEY", "k")
        check(r3["ok"] is None and "quatre" in r3["message"], "X : test de groupe seulement")
    asyncio.run(sc())

test_poids_disque_par_categorie(); test_journal_erreurs(); test_tests_de_cles()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_diagnostic.py`
Expected : `ModuleNotFoundError: No module named 'app.services.diagnostic'`

- [ ] **Step 3 : écrire le module**

```python
"""Diagnostic en un écran (plan Settings, P1).

Trois mesures indépendantes : le poids de DATA_ROOT par catégorie (marche
sur disque, cache 300 s — 7,8 Go d'assets mesurés le 03/09), le journal
loguru filtré (WARNING/ERROR), et un test LÉGER par clé (appel authentifié
qui ne dépense rien). Les deux hooks `_get`/`_post` sont remplacés au banc.
"""
import asyncio, os, re, shutil, time
from pathlib import Path
import httpx
from app.config import DATA_ROOT, SSL_VERIFY, settings

CATEGORIES = [
    ("Images (Bibliothèque)", "assets/images"), ("Rendus vidéo", "assets/outputs/videos"),
    ("Rendus finaux", "assets/outputs/final"), ("Audio des rendus", "assets/outputs/audio"),
    ("Sous-titres", "assets/outputs/captions"), ("Audio (Bibliothèque)", "assets/audio"),
    ("3D Meshy", "assets/outputs/meshy3d"), ("Impression 3D", "assets/print3d"),
    ("Vectorlab", "assets/vector"), ("News", "assets/news"), ("Cardforge", "cardforge_models"),
    ("Séries Cardforge", "cardforge_series"), ("Journal", "logs"), ("Base de données", "deepotus.db"),
]
_cache: dict = {"t": 0.0, "racine": None, "val": None}


def _taille(p: Path) -> tuple[int, int]:
    if p.is_file():
        return p.stat().st_size, 1
    octets = fichiers = 0
    for racine, _d, fs in os.walk(p, onerror=lambda e: None):
        for f in fs:
            try:
                octets += os.stat(os.path.join(racine, f)).st_size; fichiers += 1
            except OSError:
                pass
    return octets, fichiers


def poids_disque(racine: Path = DATA_ROOT, cache_s: int = 300) -> dict:
    if _cache["val"] and _cache["racine"] == racine and time.time() - _cache["t"] < cache_s:
        return _cache["val"]
    cats, vus = [], []
    for nom, rel in CATEGORIES:
        p = racine / rel
        o, f = _taille(p) if p.exists() else (0, 0)
        cats.append({"nom": nom, "chemin": str(p), "octets": o, "fichiers": f}); vus.append(p)
    rebuts = sorted(x for x in racine.glob("rebut_*") if x.is_dir())
    ro = rf = 0
    for x in rebuts:
        o, f = _taille(x); ro += o; rf += f; vus.append(x)
    cats.append({"nom": "Rebuts", "chemin": " ; ".join(str(x) for x in rebuts), "octets": ro, "fichiers": rf})
    total, tf = _taille(racine)
    autre = total - sum(c["octets"] for c in cats)
    cats.append({"nom": "Autre", "chemin": str(racine), "octets": max(0, autre),
                 "fichiers": max(0, tf - sum(c["fichiers"] for c in cats))})
    try:
        libre = shutil.disk_usage(racine).free
    except OSError:
        libre = 0
    val = {"racine": str(racine), "categories": cats, "total_octets": total, "libre_octets": libre,
           "mesure_le": time.strftime("%Y-%m-%d %H:%M:%S")}
    _cache.update(t=time.time(), racine=racine, val=val)
    return val


_LIGNE = re.compile(r"^(\S+ \S+) \| (WARNING|ERROR|CRITICAL)\s*\| (\S+) - (.*)$")


def journal_erreurs(dossier: Path = DATA_ROOT / "logs", n: int = 50) -> list[dict]:
    fichiers = sorted(dossier.glob("deepotus-*.log")) if dossier.is_dir() else []
    out: list[dict] = []
    for f in fichiers[-3:]:
        for ligne in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _LIGNE.match(ligne)
            if m:
                out.append({"quand": m.group(1), "niveau": m.group(2), "ou": m.group(3), "message": m.group(4)})
    return out[-n:]


async def _get(url: str, headers: dict | None = None, timeout: float = 15.0):
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout) as c:
        r = await c.get(url, headers=headers or {})
    try:
        corps = r.json()
    except ValueError:
        corps = r.text[:200]
    return r.status_code, corps


def _msg(corps) -> str:
    if isinstance(corps, dict):
        e = corps.get("error") or corps.get("detail") or corps.get("message") or corps.get("description")
        if isinstance(e, dict):
            e = e.get("message") or str(e)
        return str(e or corps)[:200]
    return str(corps)[:200]


def _res(ok, message, **details):
    return {"ok": ok, "message": message, "details": details}


async def _simple(url, headers, ok_sur=(200,), libelle=""):
    code, corps = await _get(url, headers)
    if code in ok_sur:
        return code, corps, _res(True, f"clé acceptée ({libelle or code})")
    if code in (401, 403):
        return code, corps, _res(False, f"refusée ({code}) : {_msg(corps)}")
    return code, corps, _res(None, f"indéterminé (HTTP {code}) : {_msg(corps)}")


async def tester_cle(nom: str, valeur: str) -> dict:
    v = (valeur or "").strip()
    if not v:
        return _res(None, "vide")
    try:
        if nom == "FAL_KEY":
            code, corps, r = await _simple("https://queue.fal.run/fal-ai/flux/schnell/requests/"
                                           "00000000-0000-0000-0000-000000000000/status",
                                           {"Authorization": f"Key {v}"}, ok_sur=(404,),
                                           libelle="404 sur une requête fictive, comme attendu")
            return r
        if nom == "HEYGEN_API_KEY":
            from app.services.heygen_service import HeyGenClient
            q = await HeyGenClient(api_key=v).remaining_quota()
            return _res(True, "clé acceptée", credits=q.get("remaining_quota"))
        if nom == "ELEVENLABS_API_KEY":
            code, corps, r = await _simple("https://api.elevenlabs.io/v1/user/subscription", {"xi-api-key": v})
            if r["ok"] and isinstance(corps, dict):
                u, l = corps.get("character_count"), corps.get("character_limit")
                r["details"] = {"utilise": u, "limite": l, "restant": (l - u) if (u is not None and l is not None) else None}
            return r
        if nom == "MESHY_API_KEY":
            from app.services import meshy_service as MS
            code, corps, r = await _simple(f"{MS.MESHY_API}/openapi/v1/balance", {"Authorization": f"Bearer {v}"})
            if r["ok"] and isinstance(corps, dict):
                r["details"] = {"credits": corps.get("balance")}
            return r
        if nom == "ANTHROPIC_API_KEY":
            _c, _b, r = await _simple("https://api.anthropic.com/v1/models",
                                      {"x-api-key": v, "anthropic-version": "2023-06-01"})
            return r
        if nom == "OPENAI_API_KEY":
            _c, _b, r = await _simple("https://api.openai.com/v1/models", {"Authorization": f"Bearer {v}"})
            return r
        if nom == "GEMINI_API_KEY":
            _c, _b, r = await _simple("https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": v})
            return r
        if nom == "FIGMA_TOKEN":
            _c, corps, r = await _simple("https://api.figma.com/v1/me", {"X-Figma-Token": v})
            if r["ok"] and isinstance(corps, dict):
                r["details"] = {"compte": corps.get("handle")}
            return r
        if nom == "TELEGRAM_BOT_TOKEN":
            code, corps = await _get(f"https://api.telegram.org/bot{v}/getMe")
            if code == 200 and isinstance(corps, dict) and corps.get("ok"):
                return _res(True, "jeton accepté", bot=(corps.get("result") or {}).get("username"))
            return _res(False if code in (401, 404) else None, f"refusé ({code}) : {_msg(corps)}")
        if nom == "OLLAMA_URL":
            code, corps = await _get(f"{v.rstrip('/')}/api/tags", timeout=5.0)
            if code == 200 and isinstance(corps, dict):
                return _res(True, "Ollama joignable", modeles=[m.get("name") for m in corps.get("models", [])])
            return _res(False, f"injoignable ({code})")
        if nom.startswith("X_"):
            return _res(None, "les quatre clés X se testent ensemble (bouton du groupe « Connected accounts »)")
        return _res(None, "pas de test pour cette clé")
    except Exception as e:  # noqa: BLE001 — un test ne casse jamais l'écran
        return _res(False, f"erreur : {str(e)[:160]}")


async def tester_x(cles: dict) -> dict:
    """OAuth 1.0a via tweepy (déjà utilisé par marketing.py) — de mémoire : Client.get_me()."""
    if not all(cles.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        return _res(None, "il faut les quatre clés X")
    def _sync():
        import tweepy
        c = tweepy.Client(consumer_key=cles["X_API_KEY"], consumer_secret=cles["X_API_SECRET"],
                          access_token=cles["X_ACCESS_TOKEN"], access_token_secret=cles["X_ACCESS_SECRET"])
        return c.get_me()
    try:
        me = await asyncio.get_running_loop().run_in_executor(None, _sync)
        return _res(True, "compte X joint", compte=getattr(getattr(me, "data", None), "username", None))
    except Exception as e:  # noqa: BLE001
        return _res(False, f"refusé : {str(e)[:160]}")
```

- [ ] **Step 4 : lancer, constater le vert**

Run : `python tests/test_diagnostic.py`
Expected : 18 lignes `ok   …` puis `0 échec(s)`, code de sortie 0.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/diagnostic.py backend/tests/test_diagnostic.py
git commit -m 'reglages : diagnostic - poids disque, journal, tests de cles' -m 'Poids de DATA_ROOT par catégorie (rebut_* à part, cache 300 s), journal loguru filtré, un test léger par clé sans dépense ; réseau remplacé au banc.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 2 : Diagnostic — le routeur `/api/reglages` et ses deux routes

**Files:**
- Create: `backend/app/api/settings_routes.py`
- Modify: `backend/app/services/diagnostic.py` (ajout de `TESTABLES` + `testable()`)
- Modify: `backend/app/main.py:232` (juste après `# __DZ_CARDS_ROUTER_END__`)
- Test: `backend/tests/test_settings_routes.py`

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Routeur des réglages (plan Settings T2) — /api/reglages/diagnostic et
/api/reglages/diagnostic/cle.

Banc-miroir : il relit les RÉPONSES JSON du routeur monté sur l'application
réelle, jamais le module tout seul. Zéro réseau (le hook `_get` du module
diagnostic et le producteur de soldes sont remplacés).
Run: python tests/test_settings_routes.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
(_tmp / ".env").write_text("FAL_KEY=abcd1234efgh5678\nMESHY_API_KEY=\n", encoding="utf-8")

from fastapi.testclient import TestClient                         # noqa: E402
from app.main import app                                          # noqa: E402
from app.api import settings_routes as SR                         # noqa: E402
from app.services import diagnostic as D                          # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

async def _faux_soldes():
    return {"heygen": {"available": True, "credits": 766, "usd": 30.64}}
SR._soldes = _faux_soldes

async def _faux_get(url, headers=None, timeout=15.0):
    if "queue.fal.run" in url:
        return 404, {"detail": "Request not found"}
    return 401, {"error": {"message": "invalid key"}}
D._get = _faux_get

c = TestClient(app)   # sans `with` : le lifespan (init_db, boucles) ne part pas

def test_diagnostic_un_ecran():
    r = c.get("/api/reglages/diagnostic")
    check(r.status_code == 200, f"200 attendu (lu {r.status_code})")
    j = r.json()
    check(j["version"] == "2.6.0", f"version du .env de config (lu {j.get('version')})")
    noms = {k["cle"] for k in j["cles"]}
    check("FAL_KEY" in noms and "MESHY_API_KEY" in noms, "les clés autorisées sont listées")
    fal = [k for k in j["cles"] if k["cle"] == "FAL_KEY"][0]
    check(fal["definie"] is True and fal["testable"] is True, "FAL_KEY définie et testable")
    check("abcd1234efgh5678" not in json.dumps(j), "aucune valeur de clé en clair dans la réponse")
    check(fal["apercu"].startswith("abcd") and fal["apercu"].endswith("5678"), "aperçu masqué au format _mask")
    mes = [k for k in j["cles"] if k["cle"] == "MESHY_API_KEY"][0]
    check(mes["definie"] is False, "clé vide = non définie")
    check(j["disque"]["total_octets"] >= 0 and "categories" in j["disque"], "poids disque présent")
    check(isinstance(j["journal"], list), "journal présent (liste)")
    check(j["soldes"]["heygen"]["credits"] == 766, "soldes repris de /cost/balances")

def test_test_de_cle_relit_le_env():
    r = c.post("/api/reglages/diagnostic/cle", json={"nom": "FAL_KEY"})
    check(r.status_code == 200, f"200 attendu (lu {r.status_code})")
    check(r.json()["ok"] is True, "FAL_KEY relue du .env et acceptée (404 fal)")
    r2 = c.post("/api/reglages/diagnostic/cle", json={"nom": "OPENAI_API_KEY", "valeur": "sk-x"})
    check(r2.json()["ok"] is False, "valeur fournie : 401 → refusée")
    r3 = c.post("/api/reglages/diagnostic/cle", json={"nom": "PATH"})
    check(r3.status_code == 400 and "PATH" in r3.json()["detail"], "clé hors allowlist refusée en le disant")
    r4 = c.post("/api/reglages/diagnostic/cle", json={"nom": "X_API_KEY"})
    check(r4.json()["ok"] is None, "X : test de groupe, pas de verdict par clé")

test_diagnostic_un_ecran(); test_test_de_cle_relit_le_env()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_settings_routes.py`
Expected : `ModuleNotFoundError: No module named 'app.api.settings_routes'`

- [ ] **Step 3 : ajouter `TESTABLES` / `testable()` à `diagnostic.py`**

À coller à la fin de `backend/app/services/diagnostic.py` :

```python
# Les clés pour lesquelles `tester_cle` sait faire un appel authentifié qui
# ne dépense rien. Les autres (modèles, identifiants de voix, chat id…) sont
# des RÉGLAGES, pas des secrets à valider : l'écran n'affiche pas de bouton.
TESTABLES = {
    "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN",
    "TELEGRAM_BOT_TOKEN", "OLLAMA_URL",
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
}


def testable(nom: str) -> bool:
    return nom in TESTABLES
```

- [ ] **Step 4 : écrire le routeur**

`backend/app/api/settings_routes.py` :

```python
"""Routeur des réglages (plan Settings, 09/2026).

Tout ce que l'écran Settings gagne en 09/2026 vit ICI et pas dans les 9 575
lignes de `routes.py` : diagnostic, plafonds, guides fournisseurs, mise à
jour, export, coffre, index de recherche. Monté par `main.py` sous
`/api/reglages`, comme les routeurs montage et cards.

Toute route qui lit ou écrit des clés passe par `_local()` — la même garde de
bouclage que `routes._require_localhost` (un seul propriétaire de la règle).
"""
from fastapi import APIRouter, HTTPException, Request

from app.config import APP_VERSION

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


async def _soldes() -> dict:
    """Les soldes en direct : un seul producteur (`/cost/balances`), deux
    lecteurs (la pastille du bandeau et le diagnostic). Remplacé au banc."""
    from app.api.routes import cost_balances
    return await cost_balances()


@router.get("/diagnostic")
async def diagnostic_complet(request: Request):
    """L'écran unique de P1 : version, poids disque, journal, clés, soldes."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _mask, _read_env_file
    from app.services import diagnostic as D
    env = _read_env_file()
    cles = [{"cle": k, "definie": bool(env.get(k, "")),
             "apercu": _mask(env.get(k, "")), "testable": D.testable(k)}
            for k in sorted(_ALLOWED_ENV_KEYS)]
    try:
        soldes = await _soldes()
    except Exception as e:  # noqa: BLE001 — un solde muet ne masque pas le reste
        soldes = {"erreur": str(e)[:160]}
    return {"version": APP_VERSION, "disque": D.poids_disque(),
            "journal": D.journal_erreurs(), "cles": cles, "soldes": soldes}


@router.post("/diagnostic/cle")
async def diagnostic_cle(body: dict, request: Request):
    """Teste UNE clé. Sans `valeur`, la clé enregistrée est relue du `.env` :
    l'écran n'a jamais à renvoyer un secret au serveur pour le faire tester."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _read_env_file
    from app.services import diagnostic as D
    nom = str((body or {}).get("nom") or "").strip()
    if nom not in _ALLOWED_ENV_KEYS:
        raise HTTPException(400, f"clé inconnue ou non modifiable : {nom}")
    env = _read_env_file()
    if nom.startswith("X_"):
        return await D.tester_x(env)
    valeur = str((body or {}).get("valeur") or "") or env.get(nom, "")
    return await D.tester_cle(nom, valeur)
```

- [ ] **Step 5 : monter le routeur dans `main.py`**

Coller juste APRÈS la ligne `# __DZ_CARDS_ROUTER_END__` (`backend/app/main.py:232`) :

```python
# __DZ_REGLAGES_ROUTER_BEGIN__
from app.api.settings_routes import router as reglages_router
app.include_router(reglages_router, prefix="/api/reglages")
# __DZ_REGLAGES_ROUTER_END__
```

- [ ] **Step 6 : lancer, constater le vert**

Run : `python tests/test_settings_routes.py`
Expected : 15 lignes `ok   …` puis `0 échec(s)`, code de sortie 0.

- [ ] **Step 7 : commit**

```bash
git add backend/app/api/settings_routes.py backend/app/services/diagnostic.py backend/app/main.py backend/tests/test_settings_routes.py
git commit -m 'reglages : le routeur /api/reglages et le diagnostic en une route' -m 'Un routeur à part (montage/cards ont le même contrat) plutôt que de grossir les 9 575 lignes de routes.py. /diagnostic rend version, disque, journal, clés masquées et soldes ; /diagnostic/cle relit le .env pour ne jamais faire remonter un secret depuis le navigateur.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 3 : Diagnostic — l'écran (patcheur `reglages`, sections S1/S2/S3)

**Files:**
- Create: `scripts/patch_bundle_reglages.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur seul, jamais à la main)
- Test: `backend/tests/test_patch_reglages.py`

**Coût de patch** : tag NEUF `reglages`, backup `.js.bak_reglages`, position EN QUEUE (après `seedance25`). Trois ancres, chacune comptée **1** dans le bundle du 03/09 (vérifié) :

| Ancre | Compte | Ce qu'elle porte |
|---|---|---|
| `}function DzPricing(){` | 1 | S1 — point d'injection du bloc de composants, portée du module (celle où `bm` résout déjà `x`, `r`, `jt`, `te`, `K`) |
| `[{k:"keys",l:"API keys"},` | 1 | S2a — début du tableau de la barre latérale |
| `const ym=["keys",` | 1 | S2b — **liste blanche des sections** ; sans elle `?section=diag` retomberait sur `accounts` |
| `s==="pricing"&&r.jsx(DzPricing,{})]})` | 1 | S3 — fin des branches du corps |

- [ ] **Step 1 : écrire le banc du patcheur (rouge)**

```python
"""Le patcheur `reglages` (plan Settings T3) — banc-miroir du BUNDLE.

Il ne lit pas le script : il lance le patcheur sur une COPIE du bundle et
relit le fichier produit (ancres consommées, fins de ligne intactes,
idempotence, --check qui n'écrit rien). Aucune ancre n'est imprimée : la
console Windows est en cp1252.
Run: python tests/test_patch_reglages.py   (depuis backend/)"""
import os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = R / "frontend/dist/assets/index-BEOJX8L5.js"
SCRIPT = R / "scripts/patch_bundle_reglages.py"

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

def _bac():
    """Un bac de sable : arbre minimal frontend/dist/assets + le patcheur."""
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "frontend/dist/assets").mkdir(parents=True)
    (d / "scripts").mkdir()
    shutil.copy2(BUNDLE, d / "frontend/dist/assets" / BUNDLE.name)
    shutil.copy2(SCRIPT, d / "scripts" / SCRIPT.name)
    return d

def _run(d, *args):
    return subprocess.run([sys.executable, "scripts/patch_bundle_reglages.py", *args],
                          cwd=d, capture_output=True, timeout=300)

def test_patch():
    d = _bac()
    cible = d / "frontend/dist/assets" / BUNDLE.name
    avant = cible.read_bytes()
    r = _run(d, "--check")
    check(r.returncode == 0, f"--check sort 0 (lu {r.returncode})")
    check(cible.read_bytes() == avant, "--check n'écrit rien")
    r = _run(d)
    check(r.returncode == 0, f"patch sort 0 (lu {r.returncode}) : {r.stderr[-300:]!r}")
    s = cible.read_text(encoding="utf-8")
    check("function DzDiag(" in s, "DzDiag injecté")
    check("__dzReglages" in s, "marqueur du patch posé")
    check(s.count('{k:"diag",l:"Diagnostic"}') == 1, "une entrée de barre, une seule")
    check(s.count('s==="diag"&&r.jsx(DzDiag,{})') == 1, "une branche de corps, une seule")
    check('"diag","keys"' in s.replace(" ", ""), "section ajoutée à la liste blanche")
    b = cible.read_bytes()
    check(b.count(b"\n") == b.count(b"\r\n"), "aucun LF isolé introduit")
    check((d / "frontend/dist/assets" / (BUNDLE.name + ".bak_reglages")).exists(),
          "backup .bak_reglages écrit")
    taille1 = cible.stat().st_size
    r = _run(d)
    check(r.returncode == 0, "second passage : sort 0 (restaure puis réapplique)")
    check(cible.stat().st_size == taille1, "idempotent à l'octet près")
    shutil.rmtree(d, ignore_errors=True)

test_patch()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_patch_reglages.py`
Expected : `FileNotFoundError` sur `scripts/patch_bundle_reglages.py` (le banc copie le script avant de le lancer).

- [ ] **Step 3 : écrire le patcheur**

`scripts/patch_bundle_reglages.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_reglages.py
"""Patcheur assert-gardé : l'écran Settings de 09/2026 (plan Settings).

BASELINE : bundle POST-patch `seedance25` (queue de chaîne au 03/09/2026).
Backup dédié : .js.bak_reglages (l'état juste AVANT ce patch).

Sections, une par tâche du plan — chacune est ajoutée au fil de l'eau et le
script est relancé EN ENTIER (il restaure son .bak puis réapplique tout) :

  S1  bloc de composants injecté à la portée du module (là où `bm` résout
      déjà `x`, `r`, `jt`, `te`, `K`) : dzOct, DzDiag ;
  S2  entrée « Diagnostic » dans le tableau de la barre latérale ET dans la
      liste blanche `ym` des sections (sans quoi ?section=diag retombe sur
      « accounts ») ;
  S3  branche `s==="diag"` dans le corps.

Le JS injecté NE CONTIENT AUCUN SAUT DE LIGNE : le bundle est 100 % CRLF, un
`\\n` isolé y serait une régression de fins de ligne (garde en sortie). Les
chaînes Python ci-dessous sont donc concaténées par juxtaposition, pas par
triple-guillemets.

Run : python scripts/patch_bundle_reglages.py
      python scripts/patch_bundle_reglages.py --check   (n'écrit rien)
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_reglages")
MARQUEUR = "__dzReglages"


def guard_downstream(bak):
    """Refuse de tourner si un patcheur AVAL est déjà passé — voir repatch_all.py."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. Utiliser : "
                f"python scripts/repatch_all.py --from reglages")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── S1 : le bloc de composants (une seule ligne, sans aucun \n) ─────────────

S1 = (
    "function dzOct(n){n=Number(n)||0;var u=['o','Ko','Mo','Go','To'],i=0;"
    "while(n>=1024&&i<u.length-1){n/=1024;i++}"
    "return (i?n.toFixed(1):String(n))+' '+u[i]}"

    "function dzTon(v){return v===!0?'green':v===!1?'red':'neutral'}"

    "function DzDiag(){"
    "const[d,setD]=x.useState(null),[busy,setBusy]=x.useState(!1),"
    "[tests,setTests]=x.useState({});"
    "const charger=()=>{setBusy(!0);fetch('/api/reglages/diagnostic')"
    ".then(R=>R.ok?R.json():null).then(j=>{setBusy(!1);if(j)setD(j)})"
    ".catch(()=>setBusy(!1))};"
    "x.useEffect(()=>{charger()},[]);"
    "const tester=k=>{setTests(t=>({...t,[k]:{ok:null,message:'test en cours...'}}));"
    "fetch('/api/reglages/diagnostic/cle',{method:'POST',"
    "headers:{'Content-Type':'application/json'},body:JSON.stringify({nom:k})})"
    ".then(R=>R.json()).then(j=>setTests(t=>({...t,[k]:j})))"
    ".catch(e=>setTests(t=>({...t,[k]:{ok:!1,message:String(e)}})))};"
    "if(!d)return r.jsx('div',{style:{padding:24,color:'var(--ink-muted)'},"
    "children:busy?'Diagnostic en cours...':'Diagnostic indisponible'});"
    "const cats=(d.disque&&d.disque.categories||[]).filter(c=>c.octets>0)"
    ".sort((a,b)=>b.octets-a.octets);"
    "const max=cats.length?cats[0].octets:1;"
    "return r.jsxs(r.Fragment,{children:["
    "r.jsxs('div',{style:{display:'flex',alignItems:'center',gap:12,marginBottom:16},"
    "children:["
    "r.jsx('div',{className:'display',style:{fontSize:22,color:'var(--ink-strong)'},"
    "children:'Diagnostic'}),"
    "r.jsx(te,{tone:'cyan',children:'v'+d.version}),"
    "r.jsx('div',{style:{flex:1}}),"
    "r.jsx(K,{variant:'primary',size:'sm',icon:'check',onClick:charger,disabled:busy,"
    "children:busy?'...':'Rafraichir'})]}),"

    "r.jsxs(jt,{style:{padding:16,marginBottom:14},children:["
    "r.jsx('div',{className:'upper',style:{marginBottom:10},children:'Cles'}),"
    "d.cles.map(c=>{const t=tests[c.cle];return r.jsxs('div',{style:{display:'grid',"
    "gridTemplateColumns:'210px 90px 1fr auto',gap:10,alignItems:'center',"
    "padding:'6px 0',borderTop:'1px solid var(--stroke)'},children:["
    "r.jsx('div',{className:'mono',style:{fontSize:11},children:c.cle}),"
    "r.jsx(te,{tone:c.definie?'green':'neutral',dot:!0,"
    "children:c.definie?'definie':'absente'}),"
    "r.jsx('div',{style:{fontSize:11,color:t?(t.ok===!1?'var(--red)':'var(--ink-soft)')"
    ":'var(--ink-muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'},"
    "title:t?String(t.message||''):c.apercu,"
    "children:t?String(t.message||''):(c.apercu||'')}),"
    "c.testable&&c.definie?r.jsx(K,{variant:'ghost',size:'sm',"
    "onClick:()=>tester(c.cle),children:'Tester'}):r.jsx('div',{})]},c.cle)})]}),"

    "r.jsxs(jt,{style:{padding:16,marginBottom:14},children:["
    "r.jsxs('div',{className:'upper',style:{marginBottom:10},children:["
    "'Disque - ',dzOct(d.disque.total_octets),' dans ',d.disque.racine,"
    "' (',dzOct(d.disque.libre_octets),' libres)']}),"
    "cats.map(c=>r.jsxs('div',{style:{display:'grid',"
    "gridTemplateColumns:'200px 1fr 90px 70px',gap:10,alignItems:'center',"
    "padding:'4px 0'},title:c.chemin,children:["
    "r.jsx('div',{style:{fontSize:11.5},children:c.nom}),"
    "r.jsx('div',{style:{height:6,background:'var(--bg-panel-2)',borderRadius:3},"
    "children:r.jsx('div',{style:{height:6,borderRadius:3,background:'var(--brand)',"
    "width:Math.max(2,Math.round(100*c.octets/max))+'%'}})}),"
    "r.jsx('div',{className:'mono',style:{fontSize:11,textAlign:'right'},"
    "children:dzOct(c.octets)}),"
    "r.jsx('div',{className:'mono',style:{fontSize:10.5,textAlign:'right',"
    "color:'var(--ink-muted)'},children:c.fichiers+' f.'})]},c.nom))]}),"

    "r.jsxs(jt,{style:{padding:16},children:["
    "r.jsx('div',{className:'upper',style:{marginBottom:10},"
    "children:'Journal - dernieres alertes'}),"
    "d.journal.length?d.journal.slice(-25).reverse().map((l,i)=>r.jsxs('div',"
    "{style:{display:'grid',gridTemplateColumns:'150px 80px 1fr',gap:10,"
    "fontSize:11,padding:'3px 0'},children:["
    "r.jsx('div',{className:'mono',style:{color:'var(--ink-muted)'},children:l.quand}),"
    "r.jsx(te,{tone:l.niveau==='WARNING'?'amber':'red',children:l.niveau}),"
    "r.jsx('div',{title:l.ou+' - '+l.message,style:{overflow:'hidden',"
    "textOverflow:'ellipsis',whiteSpace:'nowrap'},children:l.message})]},i))"
    ":r.jsx('div',{style:{fontSize:12,color:'var(--ink-muted)'},"
    "children:'Rien a signaler.'})]})]})}"

    "var " + MARQUEUR + "=1;"
)


def patcher(s):
    s = apply(s, "}function DzPricing(){", "}" + S1 + "function DzPricing(){", "S1-bloc")
    s = apply(s, '[{k:"keys",l:"API keys"},',
              '[{k:"diag",l:"Diagnostic"},{k:"keys",l:"API keys"},', "S2a-barre")
    s = apply(s, 'const ym=["keys",', 'const ym=["diag","keys",', "S2b-liste-blanche")
    s = apply(s, 's==="pricing"&&r.jsx(DzPricing,{})]})',
              's==="pricing"&&r.jsx(DzPricing,{}),s==="diag"&&r.jsx(DzDiag,{})]})',
              "S3-corps")
    return s


def main():
    verif = "--check" in sys.argv
    if not verif and "--force-unchained" not in sys.argv:
        guard_downstream(BAK)
    if BAK.exists() and not verif:
        shutil.copy2(BAK, BUNDLE)
    raw = BUNDLE.read_bytes()
    crlf = raw.count(b"\r\n")
    lf_seul = raw.count(b"\n") - crlf
    cr_seul = raw.count(b"\r") - crlf
    if lf_seul or cr_seul:
        raise SystemExit(f"[reglages] fins de ligne non homogenes AVANT patch "
                         f"(CRLF={crlf} LF-isole={lf_seul} CR-isole={cr_seul}). Aborting.")
    s = raw.decode("utf-8")
    if MARQUEUR in s:
        raise SystemExit("[reglages] marqueur deja present sur un bundle non restaure. Aborting.")
    s = patcher(s)
    if verif:
        print("check OK - toutes les ancres sont uniques, rien ecrit.")
        return
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    BUNDLE.write_text(s, encoding="utf-8", newline="")
    fin = BUNDLE.read_bytes()
    if fin.count(b"\n") != fin.count(b"\r\n"):
        raise SystemExit("[reglages] le patch a traduit des fins de ligne. Aborting.")
    print("bundle ecrit :", len(s), "o")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4 : lancer le banc, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 12 lignes `ok   …` puis `0 échec(s)`, code de sortie 0.

- [ ] **Step 5 : appliquer pour de vrai + inventaire**

Run (depuis la racine du dépôt) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
```
Expected : `backup -> index-BEOJX8L5.js.bak_reglages`, `bundle ecrit : …` ; le `--diff` sort **0** et ne signale que des ajouts de fonctions (`dzOct`, `dzTon`, `DzDiag`) — toute autre différence est une régression : restaurer le `.bak_reglages` et recommencer.

- [ ] **Step 6 : voir l'écran**

Copier le bundle patché vers l'installation, puis DEMANDER À L'UTILISATEUR de relancer l'app (c'est lui qui relance) :
```
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
git hash-object frontend\dist\assets\index-BEOJX8L5.js
git hash-object "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Expected : les deux `git hash-object` donnent le MÊME sha (jamais comparer un sha256 d'octets : `core.autocrlf` ferait divergér tout l'arbre). Puis, dans l'app relancée : Settings → **Diagnostic** en tête de barre, la liste des clés, les barres de poids disque, les dernières alertes du journal.

- [ ] **Step 7 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : ecran Diagnostic dans le bundle, patcheur en queue de chaine' -m 'Tag neuf reglages, backup .js.bak_reglages, quatre ancres comptees a 1 (bloc de composants, barre, liste blanche ym, branche du corps). La liste blanche est la piece qui manque toujours : sans elle ?section=diag retombe sur accounts. Banc-miroir sur une copie du bundle : ancres consommees, fins de ligne intactes, idempotence, --check muet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 4 : Plafonds — le registre `depenses` et le module `plafonds.py`

**Files:**
- Modify: `backend/app/services/storage.py` (nouveau modèle `Depense`, après `AtelierSetting` l. 328)
- Create: `backend/app/services/plafonds.py`
- Test: `backend/tests/test_plafonds.py`

**Décision, avec sa raison.** `verifier()` **vérifie ET enregistre** l'estimation en UN appel. Un tir qui échoue ensuite chez le fournisseur laisse donc une ligne un peu trop chère : c'est le sens SÛR pour un plafond (on sur-compte, jamais l'inverse), et D2 (T18) corrige avec la colonne « réel » là où le fournisseur la donne. Deux appels par route (vérifier puis noter) doubleraient 21 points de couture pour un gain que la colonne « réel » apporte déjà.

**Décision, avec sa raison (bis).** `depenses` est un registre NEUF, il ne rétro-remplit rien. `/cost/usage` (estimé depuis les `JobRecord` finis) reste tel quel pour la pastille du bandeau. Le tableau de T18 lit `depenses` et affiche « depuis le \<date de la première ligne\> » plutôt que de faire croire à un historique qu'il n'a pas.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Plafonds de dépense (plan Settings T4) — registre, garde, alerte.

Banc-miroir : les totaux sont relus dans la BASE (SELECT sur `depenses`),
pas dans un compteur en mémoire. Zéro réseau, base SQLite jetable.
Run: python tests/test_plafonds.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi import HTTPException                                  # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.services import plafonds as P                              # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

async def _lignes():
    async with async_session_factory() as s:
        return (await s.execute(select(Depense))).scalars().all()

def test_tout():
    async def sc():
        await init_db()
        check(P.charger() == {"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80},
              "plafonds par défaut : aucun plafond, alerte à 80 %")
        # 1. aucun plafond posé : rien ne bloque, tout est enregistré
        r = await P.verifier({"kind": "image", "n": 10, "model": "nano-banana-pro"}, "quick")
        check(abs(r["devis"]["total_usd"] - 1.5) < 1e-6,
              f"devis = 10 x 0,15 $ (lu {r['devis']['total_usd']})")
        lignes = await _lignes()
        check(len(lignes) == 1, f"une ligne écrite (lu {len(lignes)})")
        check(lignes[0].moteur == "fal" and lignes[0].categorie == "quick"
              and lignes[0].op == "image" and lignes[0].reel_usd is None,
              "moteur/catégorie/op écrits, réel encore vide")
        check(lignes[0].mois == P.mois_courant(), "rangée dans le mois courant")

        # 2. un plafond fal à 2 $ : le second tir dépasse et REFUSE en le disant
        P.enregistrer({"global_usd": 0.0, "par_moteur": {"fal": 2.0}, "alerte_pct": 80})
        try:
            await P.verifier({"kind": "image", "n": 10, "model": "nano-banana-pro"}, "quick")
            check(False, "402 attendu")
        except HTTPException as e:
            check(e.status_code == 402, f"402 (lu {e.status_code})")
            d = e.detail["dz_plafond"]
            check(d["motif"] == "moteur" and d["moteur"] == "fal", "motif et moteur nommés")
            check(abs(d["deja_usd"] - 1.5) < 1e-6 and abs(d["devis_usd"] - 1.5) < 1e-6
                  and d["plafond_usd"] == 2.0, "déjà / devis / plafond chiffrés")
            check("fal" in d["message"] and "2" in d["message"] and "quick" in d["message"],
                  "le message dit le moteur, le plafond et l'écran")
        check(len(await _lignes()) == 1, "un refus n'enregistre RIEN")

        # 3. confirmé : ça passe, et c'est enregistré
        jeton = P.CONFIRME.set(True)
        try:
            await P.verifier({"kind": "image", "n": 10, "model": "nano-banana-pro"}, "quick")
        finally:
            P.CONFIRME.reset(jeton)
        check(len(await _lignes()) == 2, "confirmé : la seconde ligne est écrite")

        # 4. plafond GLOBAL, tous moteurs confondus
        P.enregistrer({"global_usd": 3.5, "par_moteur": {}, "alerte_pct": 80})
        try:
            await P.verifier({"kind": "elevenlabs", "chars": 100000}, "son")
            check(False, "402 global attendu")
        except HTTPException as e:
            check(e.detail["dz_plafond"]["motif"] == "global", "motif global")

        # 5. état : estimé, réel, alerte à 80 %
        P.enregistrer({"global_usd": 3.5, "par_moteur": {"fal": 4.0}, "alerte_pct": 80})
        et = await P.etat()
        check(abs(et["global"]["estime_usd"] - 3.0) < 1e-6,
              f"total estimé du mois = 3,00 $ (lu {et['global']['estime_usd']})")
        check(et["global"]["reel_usd"] == 0.0, "aucun réel connu pour l'instant")
        check(abs(et["global"]["pct"] - 85.7) < 0.2, "3,00 / 3,50 = 85,7 % du plafond global")
        check("global" in et["alerte"], "alerte levée au-delà de 80 %")
        check("fal" not in et["alerte"], "fal à 75 % du sien : pas d'alerte")
        check(et["par_moteur"]["fal"]["estime_usd"] == 3.0, "détail par moteur")
        check(et["depuis"].startswith("20"), "l'état dit depuis quand il compte")

        # 6. rattachement puis réel : le réel écrase l'estimé dans le compte
        check(await P.noter_reel("", 0.10, None) == 0, "référence vide = aucun effet")
        check(await P.noter_reel("inconnue", 0.10, None) == 0,
              "référence inconnue = 0 ligne touchée, jamais une ligne inventée")
        r6 = await P.verifier({"kind": "image", "n": 1}, "cartes")
        check(len(r6["lignes"]) == 1 and isinstance(r6["lignes"][0], int),
              "verifier rend les ids des lignes qu'il vient d'écrire")
        check(await P.rattacher(r6["lignes"], "meshy:abc") == 1, "rattachement a posteriori")
        await P.noter_reel("meshy:abc", 0.10, 5.0)
        et2 = await P.etat()
        check(abs(et2["global"]["reel_usd"] - 0.10) < 1e-6, "réel remonté")
        check(abs(et2["global"]["estime_usd"] - 3.003) < 1e-6,
              f"estimé inchangé par le réel (lu {et2['global']['estime_usd']})")
        check(abs(et2["global"]["effectif_usd"] - 3.10) < 1e-6,
              f"effectif = réel là où il existe (0,10), estimé ailleurs (1,5+1,5) "
              f"→ 3,10 (lu {et2['global']['effectif_usd']})")
    asyncio.run(sc())

test_tout()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_plafonds.py`
Expected : `ModuleNotFoundError: No module named 'app.services.plafonds'`

- [ ] **Step 3 : le modèle `Depense`**

À coller dans `backend/app/services/storage.py` juste après la classe `AtelierSetting` (l. 328), avant `_engine = create_async_engine(...)`. `Base.metadata.create_all` (dans `init_db`) crée la table : aucune migration à écrire.

```python
class Depense(Base):
    """Une dépense prévue par la garde des plafonds (plan Settings, P2).

    `estime_usd` vient de `pricing.estimate` AVANT le tir ; `reel_usd` /
    `reel_unites` sont remplis APRÈS coup quand le fournisseur donne un
    chiffre (crédits Meshy consommés, delta de quota HeyGen) — sinon ils
    restent vides et le tableau de D2 dit « estimé » sur cette ligne.
    """
    __tablename__ = "depenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quand: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    mois: Mapped[str] = mapped_column(String(7), index=True)        # "2026-09", heure locale
    moteur: Mapped[str] = mapped_column(String(24), index=True)     # fal|heygen|elevenlabs|meshy|…
    categorie: Mapped[str] = mapped_column(String(24), index=True)  # écran du rail
    op: Mapped[str] = mapped_column(String(32), default="")         # `kind` de pricing.estimate
    estime_usd: Mapped[float] = mapped_column(Float, default=0.0)
    reel_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reel_unites: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
```

- [ ] **Step 4 : écrire `plafonds.py`**

```python
"""Plafonds de dépense (plan Settings, P2).

MESURE D'ABORD (grep du 03/09/2026) : les 21 routes payantes du dépôt n'ont
AUCUN point d'entrée commun — `/generate` (routes.py:2806), `/generate/batch`
(2846), `/generate/heygen` (3025), `/generate/heygen-image` (3047),
`/generate/heygen-cinematic` (3070), `/generate/composition` (3092),
`/images/generate` (4424), `/audio/voiceover` (2405), `/audio/sfx` (2209),
`/audio/music` (2269), `/episodes/render` (2680), `/assets/3d` (352),
`/assets/3d/{job}/refine` (612), `/assets/3d/{job}/texturer` (718),
`/assets/sprite` (1374), `/materials/generate` (7302), `/meshy/{path}` en
POST (1240), `/marketing/plan` (4273), `/news/script` (1949), plus
`services/cards/face.py:2503` et `services/cards/forge3d.py:3004`. Chacune
vérifie sa clé elle-même, et `pricing.estimate` n'y sert qu'à AFFICHER un
devis (routes.py:538, 540, 779, 4163, 4171-4190 ; face.py:2011 ;
forge3d.py:420, 2906). La garde est donc UNE fonction appelée en tête de
chacune : un seul propriétaire de la règle, 21 lignes de couture.

La confirmation voyage par une ContextVar posée par le middleware de
`main.py` AVANT `call_next` : `BaseHTTPMiddleware` copie le contexte à la
création de la tâche fille, donc le sens DESCENDANT marche (T5 le mesure).
Le sens montant, lui, ne marcherait pas — c'est pourquoi l'alerte à 80 %
est TIRÉE par l'écran (`/plafonds/etat`, une somme SQL) et jamais poussée.
"""
import json
import time
from contextvars import ContextVar
from datetime import datetime

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select

from app.config import DATA_ROOT

_FICHIER = DATA_ROOT / "plafonds.json"
DEFAUTS = {"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80}

# Les écrans du rail qui peuvent dépenser — le vocabulaire des catégories.
CATEGORIES = ("quick", "studio", "chapitres", "son", "montage", "news",
              "scheduler", "bibliotheque", "sprites", "tuiles", "matieres",
              "cartes", "moteurs3d", "marketing")

CONFIRME: ContextVar[bool] = ContextVar("dz_plafond_confirme", default=False)


def charger() -> dict:
    d = dict(DEFAUTS)
    try:
        if _FICHIER.is_file():
            brut = json.loads(_FICHIER.read_text(encoding="utf-8"))
            if isinstance(brut, dict):
                d["global_usd"] = float(brut.get("global_usd") or 0.0)
                pm = brut.get("par_moteur") or {}
                d["par_moteur"] = {str(k): float(v) for k, v in pm.items()
                                   if isinstance(v, (int, float))}
                d["alerte_pct"] = int(brut.get("alerte_pct") or 80)
    except (OSError, ValueError, TypeError):
        pass
    return d


def enregistrer(d: dict) -> dict:
    propre = {"global_usd": float((d or {}).get("global_usd") or 0.0),
              "par_moteur": {str(k): float(v) for k, v in ((d or {}).get("par_moteur") or {}).items()
                             if isinstance(v, (int, float))},
              "alerte_pct": max(1, min(100, int((d or {}).get("alerte_pct") or 80)))}
    _FICHIER.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FICHIER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(propre, indent=2), encoding="utf-8")
    tmp.replace(_FICHIER)
    return propre


def mois_courant() -> str:
    """Heure LOCALE : « mon mois » est celui du calendrier de l'utilisateur,
    pas celui d'UTC — un tir du 31 à 23 h ne compte pas pour le mois suivant."""
    return time.strftime("%Y-%m")


async def _cumul(mois: str) -> dict:
    """Somme du mois, relue en base. Rend, par moteur :
    estimé, réel (quand connu) et EFFECTIF = réel là où il existe, estimé ailleurs."""
    from app.services.storage import Depense, async_session_factory
    par: dict[str, dict] = {}
    depuis = ""
    async with async_session_factory() as s:
        lignes = (await s.execute(
            select(Depense).where(Depense.mois == mois))).scalars().all()
        prem = (await s.execute(
            select(Depense).order_by(Depense.quand))).scalars().first()
        if prem is not None:
            depuis = prem.quand.strftime("%Y-%m-%d")
    for l in lignes:
        d = par.setdefault(l.moteur, {"estime_usd": 0.0, "reel_usd": 0.0,
                                      "effectif_usd": 0.0, "lignes": 0})
        d["estime_usd"] = round(d["estime_usd"] + (l.estime_usd or 0.0), 6)
        if l.reel_usd is not None:
            d["reel_usd"] = round(d["reel_usd"] + l.reel_usd, 6)
            d["effectif_usd"] = round(d["effectif_usd"] + l.reel_usd, 6)
        else:
            d["effectif_usd"] = round(d["effectif_usd"] + (l.estime_usd or 0.0), 6)
        d["lignes"] += 1
    return {"par_moteur": par, "depuis": depuis, "mois": mois}


async def etat(mois: str | None = None) -> dict:
    """L'état du mois pour l'écran : totaux, pourcentages, alertes à 80 %."""
    mois = mois or mois_courant()
    p = charger()
    c = await _cumul(mois)
    par = c["par_moteur"]
    tot = {k: round(sum(v[k] for v in par.values()), 6)
           for k in ("estime_usd", "reel_usd", "effectif_usd")}
    seuil = p["alerte_pct"]
    alerte = []
    gp = p["global_usd"]
    tot["pct"] = round(100.0 * tot["effectif_usd"] / gp, 1) if gp > 0 else 0.0
    tot["plafond_usd"] = gp
    if gp > 0 and tot["pct"] >= seuil:
        alerte.append("global")
    for m, v in par.items():
        pm = float(p["par_moteur"].get(m) or 0.0)
        v["plafond_usd"] = pm
        v["pct"] = round(100.0 * v["effectif_usd"] / pm, 1) if pm > 0 else 0.0
        if pm > 0 and v["pct"] >= seuil:
            alerte.append(m)
    return {"mois": mois, "global": tot, "par_moteur": par, "plafonds": p,
            "alerte": alerte, "depuis": c["depuis"]}


def _refus(motif, moteur, deja, devis, plafond, categorie) -> HTTPException:
    ou = f" (écran « {categorie} »)" if categorie else ""
    qui = "toutes dépenses confondues" if motif == "global" else f"le moteur « {moteur} »"
    msg = (f"Plafond mensuel atteint : {qui} a déjà coûté {deja:.2f} $ ce mois-ci ; "
           f"ce tir{ou} ajouterait {devis:.2f} $ et passerait au-dessus de "
           f"{plafond:.2f} $. Confirmez pour tirer quand même, ou relevez le "
           f"plafond dans Réglages → Pricing & budget.")
    return HTTPException(402, {"dz_plafond": {
        "motif": motif, "moteur": moteur, "categorie": categorie,
        "deja_usd": round(deja, 4), "devis_usd": round(devis, 4),
        "plafond_usd": round(plafond, 4), "message": msg}})


async def verifier(op: dict, categorie: str = "", ref: str | None = None,
                   confirme: bool | None = None) -> dict:
    """LA garde. À appeler en TÊTE de chaque route payante.

    Rend {devis, etat}. Lève 402 avec un refus chiffré quand le devis passe
    au-dessus d'un plafond et que l'utilisateur n'a pas confirmé.
    Enregistre l'estimation dès qu'elle passe (voir le module).
    """
    from app.services import pricing as _pricing
    from app.services.storage import Depense, async_session_factory

    devis = _pricing.estimate(op or {})
    p = charger()
    mois = mois_courant()
    c = await _cumul(mois)
    par = c["par_moteur"]
    ok = CONFIRME.get() if confirme is None else bool(confirme)

    if not ok:
        deja_g = sum(v["effectif_usd"] for v in par.values())
        gp = p["global_usd"]
        if gp > 0 and deja_g + devis["total_usd"] > gp:
            raise _refus("global", "", deja_g, devis["total_usd"], gp, categorie)
        for ligne in devis["breakdown"]:
            m = ligne["provider"]
            pm = float(p["par_moteur"].get(m) or 0.0)
            if pm <= 0:
                continue
            deja = par.get(m, {}).get("effectif_usd", 0.0)
            somme = sum(x["usd"] for x in devis["breakdown"] if x["provider"] == m)
            if deja + somme > pm:
                raise _refus("moteur", m, deja, somme, pm, categorie)

    cat = categorie if categorie in CATEGORIES else (categorie or "")
    kind = str((op or {}).get("kind") or "")[:32]
    neuves = []
    async with async_session_factory() as s:
        for ligne in devis["breakdown"]:
            if ligne["usd"] <= 0 and ligne["provider"] == "local":
                continue          # le local est gratuit : il n'encombre pas le registre
            d = Depense(quand=datetime.utcnow(), mois=mois,
                        moteur=ligne["provider"][:24], categorie=cat[:24],
                        op=kind, estime_usd=float(ligne["usd"]), ref=ref)
            s.add(d)
            neuves.append(d)
        await s.commit()
        ids = [d.id for d in neuves]
    return {"devis": devis, "lignes": ids, "etat": {"mois": mois}}


async def rattacher(ids: list[int], ref: str) -> int:
    """Colle une référence aux lignes qu'un `verifier()` vient d'écrire.

    Pourquoi : l'id d'une tâche Meshy ou d'un job HeyGen n'existe QU'APRÈS
    la réservation. Sans ce rattachement, `noter_reel` n'aurait rien à
    retrouver et le coût réel n'arriverait jamais — ou pire, il faudrait le
    deviner (« la dernière ligne meshy du mois »), ce qui est une heuristique
    et non une mesure. Deux lignes dans la route, un rapprochement exact.
    """
    from app.services.storage import Depense, async_session_factory
    if not ids or not ref:
        return 0
    n = 0
    async with async_session_factory() as s:
        for i in ids:
            d = await s.get(Depense, i)
            if d is not None:
                d.ref = ref[:64]
                n += 1
        await s.commit()
    return n


async def noter_reel(ref: str, usd: float | None, unites: float | None) -> int:
    """Le fournisseur a facturé : on écrase l'estimé de CETTE ligne.
    Rend le nombre de lignes touchées (0 = référence inconnue, on le dit
    dans le journal plutôt que d'inventer une ligne)."""
    from app.services.storage import Depense, async_session_factory
    if not ref:
        return 0
    n = 0
    async with async_session_factory() as s:
        lignes = (await s.execute(
            select(Depense).where(Depense.ref == ref))).scalars().all()
        for l in lignes:
            if usd is not None:
                l.reel_usd = float(usd)
            if unites is not None:
                l.reel_unites = float(unites)
            n += 1
        await s.commit()
    if not n:
        logger.info(f"plafonds.noter_reel: référence inconnue {ref!r} — ignorée")
    return n
```

- [ ] **Step 5 : lancer, constater le vert**

Run : `python tests/test_plafonds.py`
Expected : 26 lignes `ok   …` puis `0 échec(s)`, code de sortie 0.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/plafonds.py backend/app/services/storage.py backend/tests/test_plafonds.py
git commit -m 'reglages : registre des depenses et garde des plafonds' -m 'Table depenses (estime a la reservation, reel quand le fournisseur le donne) et plafonds.verifier() : une seule fonction, parce que le grep du 03/09 montre que les 21 routes payantes ne partagent aucun point dentree. Un refus est chiffre — deja, devis, plafond, ecran — et nenregistre rien.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 5 : Plafonds — la garde branchée sur les 21 routes payantes

**Files:**
- Modify: `backend/app/main.py` (middleware de confirmation, à côté de `_csrf_origin_guard` l. 210)
- Modify: `backend/app/api/routes.py` (19 lignes de couture)
- Modify: `backend/app/services/cards/face.py:2503`, `backend/app/services/cards/forge3d.py:3004`
- Modify: `backend/app/api/settings_routes.py` (routes `/plafonds`, `/plafonds/etat`)
- Test: `backend/tests/test_plafonds_garde.py`

- [ ] **Step 1 : écrire le banc (rouge)**

Deux temps : un **recensement mécanique** (AST) qui refuse qu'une route payante oublie la garde, et un **essai réel** par `TestClient` qui prouve le 402 puis le rejeu avec l'en-tête.

```python
"""La garde des plafonds sur les routes payantes (plan Settings T5).

1) Recensement AST : chaque route payante NOMMÉE contient un appel à
   plafonds.verifier — un ajout futur qui oublierait la garde fait rougir ici.
2) Essai réel : /images/generate refuse en 402 sous plafond, puis passe avec
   l'en-tête de confirmation (preuve que la ContextVar descend bien à travers
   BaseHTTPMiddleware).
Run: python tests/test_plafonds_garde.py   (depuis backend/)"""
import ast, asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
R = pathlib.Path(__file__).resolve().parents[1]

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

PAYANTES = {
    "app/api/routes.py": [
        "/generate", "/generate/batch", "/generate/heygen", "/generate/heygen-image",
        "/generate/heygen-cinematic", "/generate/composition", "/images/generate",
        "/audio/voiceover", "/audio/sfx", "/audio/music", "/episodes/render",
        "/assets/3d", "/assets/3d/{job}/refine", "/assets/3d/{job}/texturer",
        "/assets/sprite", "/materials/generate", "/meshy/{meshy_path:path}",
        "/marketing/plan", "/news/script",
    ],
    "app/services/cards/face.py": ["/serie/generer"],
    "app/services/cards/forge3d.py": ["/mesh3d/{nid}"],
}

def _chemins_gardes(fichier):
    """{chemin de route -> True si le corps appelle verifier}."""
    arbre = ast.parse((R / fichier).read_text(encoding="utf-8"))
    out = {}
    for n in ast.walk(arbre):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in n.decorator_list:
            if not isinstance(deco, ast.Call) or not deco.args:
                continue
            a0 = deco.args[0]
            if not (isinstance(a0, ast.Constant) and isinstance(a0.value, str)):
                continue
            garde = any(isinstance(c, ast.Attribute) and c.attr == "verifier"
                        for c in ast.walk(n))
            out[a0.value] = out.get(a0.value, False) or garde
    return out

def test_recensement():
    for fichier, chemins in PAYANTES.items():
        vus = _chemins_gardes(fichier)
        for c in chemins:
            check(vus.get(c) is True, f"{fichier} {c} : garde présente")

def test_402_puis_confirmation():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import plafonds as P
    from app.services.storage import init_db
    asyncio.run(init_db())
    P.enregistrer({"global_usd": 0.001, "par_moteur": {}, "alerte_pct": 80})
    c = TestClient(app)
    r = c.post("/api/images/generate", json={"prompt": "un poulpe", "n": 1})
    check(r.status_code == 402, f"402 sous plafond (lu {r.status_code})")
    d = r.json()["detail"]["dz_plafond"]
    check(d["motif"] == "global" and "Plafond mensuel atteint" in d["message"],
          "le refus est parlant et chiffré")
    r2 = c.post("/api/images/generate", json={"prompt": "un poulpe", "n": 1},
                headers={"X-DZ-Plafond": "confirme"})
    check(r2.status_code != 402,
          f"confirmé : la garde laisse passer (lu {r2.status_code}, "
          f"l'échec suivant vient de la clé fal factice — c'est attendu)")
    P.enregistrer({"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80})

test_recensement(); test_402_puis_confirmation()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_plafonds_garde.py`
Expected : 21 lignes `FAIL … garde présente` puis `FAIL 402 sous plafond (lu 500)` — la garde n'existe nulle part.

- [ ] **Step 3 : le middleware de confirmation**

Dans `backend/app/main.py`, juste APRÈS la fonction `_csrf_origin_guard` (elle finit l. 221) :

```python
@app.middleware("http")
async def _dz_plafond_confirme(request, call_next):
    """Descend la confirmation de dépassement jusqu'à la garde.

    `BaseHTTPMiddleware` lance `call_next` dans une tâche fille dont le
    contexte est une COPIE de celui-ci : une ContextVar posée ICI, avant
    l'appel, est bien vue par la route (le banc T5 le mesure). L'inverse ne
    serait pas vrai — c'est pourquoi l'alerte à 80 % est tirée par l'écran
    (`GET /api/reglages/plafonds/etat`) et jamais poussée par une réponse.
    """
    from app.services import plafonds as _P
    jeton = _P.CONFIRME.set(
        (request.headers.get("x-dz-plafond") or "").strip().lower() == "confirme")
    try:
        return await call_next(request)
    finally:
        _P.CONFIRME.reset(jeton)
```

- [ ] **Step 4 : les 21 lignes de couture**

Le patron est toujours le même : **première instruction du corps**, après le docstring, avant toute autre vérification. La catégorie est celle de l'écran du rail qui appelle.

```python
from app.services import plafonds as _PLAF
await _PLAF.verifier({"kind": "...", ...}, "categorie")
```

Les 21, une par une (l'`op` reprend exactement celui que la route donnait déjà à `pricing.estimate` pour afficher son devis — même vocabulaire, donc même chiffre) :

| Fichier:ligne | Route | Appel à coller en tête |
|---|---|---|
| `routes.py:2807` | `/generate` | `await _PLAF.verifier({"kind": "seedance", "duration_s": request.duration or 10, "model": request.video_model or "", "resolution": request.resolution or "1080p"}, "quick")` |
| `routes.py:2854` | `/generate/batch` | `await _PLAF.verifier({"kind": "seedance", "n": request.count, "duration_s": request.duration or 10, "model": request.video_model or "", "resolution": request.resolution or "1080p"}, "quick")` |
| `routes.py:3027` | `/generate/heygen` | `_g = await _PLAF.verifier({"kind": "heygen", "chars": len(request.script or "")}, "quick")` puis, dès que `job_id` existe : `await _PLAF.rattacher(_g["lignes"], f"hg:{job_id}")` |
| `routes.py:3049` | `/generate/heygen-image` | idem, `_g = await _PLAF.verifier({"kind": "heygen", "chars": len(request.script or "")}, "quick")` + `await _PLAF.rattacher(_g["lignes"], f"hg:{job_id}")` |
| `routes.py:3072` | `/generate/heygen-cinematic` | idem, `_g = await _PLAF.verifier({"kind": "heygen", "chars": len(request.script or "")}, "quick")` + `await _PLAF.rattacher(_g["lignes"], f"hg:{job_id}")` |
| `routes.py:3094` | `/generate/composition` | `await _PLAF.verifier({"kind": "composition", "parts": [{"kind": "heygen", "chars": len(request.script or "")}, {"kind": "seedance", "duration_s": request.duration or 10}]}, "studio")` |
| `routes.py:4426` | `/images/generate` | `await _PLAF.verifier({"kind": "image", "n": int(body.get("n") or 1), "model": (body.get("model") or "")}, str(body.get("source") or "quick"))` |
| `routes.py:2407` | `/audio/voiceover` | après `payload = await request.json()` : `await _PLAF.verifier({"kind": "elevenlabs", "chars": len(str(payload.get("script") or "")), "model": payload.get("model") or ""}, "son")` |
| `routes.py:2211` | `/audio/sfx` | après lecture du corps : `await _PLAF.verifier({"kind": "elevenlabs", "chars": len(str(payload.get("prompt") or "")) * int(payload.get("variations") or 1)}, "son")` |
| `routes.py:2271` | `/audio/music` | après lecture du corps : `await _PLAF.verifier({"kind": "seedance", "duration_s": float(payload.get("duration_s") or 30)}, "son")` |
| `routes.py:2687` | `/episodes/render` | après `payload = await request.json()` : `await _PLAF.verifier({"kind": "episode", "images": len(payload.get("scenes") or []), "chars": sum(len(str(s.get("text") or "")) for s in (payload.get("scenes") or []))}, "chapitres")` |
| `routes.py:354` | `/assets/3d` | `await _PLAF.verifier({"kind": "asset3d", "engine": body.get("engine") or "tripo", "textures": body.get("textures", True), "quality": body.get("quality") or "", "formats": body.get("formats") or [], "multiview": body.get("multiview"), "views": body.get("views", 3), "geometry_detaillee": body.get("geometry_detaillee"), "quad": body.get("quad")}, "moteurs3d")` |
| `routes.py:614` | `/assets/3d/{job}/refine` | `await _PLAF.verifier({"kind": "asset3d", "engine": (body or {}).get("engine") or "tripo", "quality": (body or {}).get("quality") or "hd"}, "moteurs3d")` |
| `routes.py:720` | `/assets/3d/{job}/texturer` | `_g = await _PLAF.verifier({"kind": "asset3d_texture", "texture_resolution": (body or {}).get("resolution") or "2k", "pbr": (body or {}).get("pbr", True)}, "moteurs3d")` puis, dès que l'id de tâche Meshy est connu : `await _PLAF.rattacher(_g["lignes"], f"meshy:{tid}")` |
| `routes.py:1376` | `/assets/sprite` | `await _PLAF.verifier({"kind": "sprite2d", "frames": int(body.get("max_frames") or 16), "remove_bg": body.get("remove_bg") or "none"}, "sprites")` |
| `routes.py:7304` | `/materials/generate` | `await _PLAF.verifier({"kind": "image", "n": 1, "model": (body or {}).get("model") or ""}, "matieres")` |
| `routes.py:1242` | `/meshy/{meshy_path:path}` | juste après `parsed = MS.parse_proxy_path(...)` et le refus 403 : `_g = await _PLAF.verifier({"kind": "asset3d_texture", "texture_resolution": "2k"}, "moteurs3d") if (request.method == "POST" and parsed["task_id"] is None) else None` — seule la CRÉATION de tâche coûte, les GET de statut sont gratuits ; puis, quand la réponse de Meshy a rendu l'id : `if _g: await _PLAF.rattacher(_g["lignes"], f"meshy:{id_rendu}")` |
| `routes.py:4283` | `/marketing/plan` | `await _PLAF.verifier({"kind": "llm", "provider": "anthropic", "in_tok": 4000, "out_tok": 2000}, "marketing")` |
| `routes.py:1951` | `/news/script` | `await _PLAF.verifier({"kind": "llm", "provider": "anthropic", "in_tok": 3000 * max(1, len(request.items)), "out_tok": 1200}, "news")` |
| `cards/face.py:2505` | `/serie/generer` | `await _PLAF.verifier({"kind": "image", "n": nb_cartes, "model": modele or ""}, "cartes")` — `nb_cartes` et `modele` sont les variables déjà lues par la route pour son devis (`face.py:2011`) |
| `cards/forge3d.py:3006` | `/mesh3d/{nid}` | `await _PLAF.verifier({"kind": "asset3d", "engine": moteur or "tripo"}, "cartes")` — `moteur` est la variable du devis existant (`forge3d.py:2906`) |

> Piège : dans les routes qui lisent leur corps avec `await request.json()`, la garde va **après** cette lecture (sinon `op` serait vide) mais **avant** toute écriture ou tout appel réseau.

- [ ] **Step 5 : les deux routes de réglage**

À ajouter à `backend/app/api/settings_routes.py` :

```python
@router.get("/plafonds")
async def lire_plafonds(request: Request):
    _local(request)
    from app.services import plafonds as P
    return P.charger()


@router.post("/plafonds")
async def ecrire_plafonds(body: dict, request: Request):
    _local(request)
    from app.services import plafonds as P
    return P.enregistrer(body or {})


@router.get("/plafonds/etat")
async def etat_plafonds(request: Request, mois: str = ""):
    """Somme du mois : estimé, réel, effectif, pourcentages, alertes.
    TIRÉ par l'écran — le canal montant d'un middleware ne serait pas fiable."""
    _local(request)
    from app.services import plafonds as P
    return await P.etat(mois or None)
```

- [ ] **Step 6 : lancer, constater le vert**

Run : `python tests/test_plafonds_garde.py`
Expected : 21 lignes `ok   … garde présente`, puis `ok   402 sous plafond`, `ok   le refus est parlant et chiffré`, `ok   confirmé : la garde laisse passer (lu 500, …)` → `0 échec(s)`.

- [ ] **Step 7 : relancer les bancs voisins (aucune régression sur les routes touchées)**

Run, un processus par fichier :
```
python tests/test_plafonds.py
python tests/test_settings_routes.py
python -m pytest tests/test_cards_forge3d.py -q
python -m pytest tests/test_asset3d_phase_d.py -q
```
Expected : `0 échec(s)` pour les deux premiers, `passed` pour les deux autres.

- [ ] **Step 8 : commit**

```bash
git add backend/app/main.py backend/app/api/routes.py backend/app/api/settings_routes.py backend/app/services/cards/face.py backend/app/services/cards/forge3d.py backend/tests/test_plafonds_garde.py
git commit -m 'reglages : la garde des plafonds en tete des 21 routes payantes' -m 'Un middleware descend la confirmation par ContextVar (BaseHTTPMiddleware copie le contexte a la creation de la tache fille : le sens descendant marche, le banc le mesure ; le sens montant non, donc lalerte est tiree par lecran). Un recensement AST refuse quune route payante future oublie la garde.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 6 : Plafonds — le coût RÉEL de Meshy et de HeyGen

**Files:**
- Modify: `backend/app/services/meshy_service.py:446` (dans `record_state`)
- Modify: `backend/app/services/plafonds.py` (ajout de `suivi_heygen`)
- Modify: `backend/app/api/routes.py` (les trois routes HeyGen encadrent leur `_run`)
- Test: `backend/tests/test_plafonds_reel.py`

**Ce que les fournisseurs donnent, mesuré** : Meshy renvoie `consumed_credits` par tâche (`meshy_service.py:446`, `MeshyTaskRecord.consumed_credits`) — c'est un chiffre EXACT. HeyGen n'expose aucun coût par vidéo : la seule vérité est le solde du compte (`HeyGenClient.remaining_quota()`, `heygen_service.py:175`). Le delta avant/après un rendu n'est attribuable **qu'à un seul rendu en vol** — sinon on laisse « réel » vide et on le dit, plutôt que d'inventer.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Coût réel : crédits Meshy consommés, delta de quota HeyGen
(plan Settings T6). Banc-miroir : la colonne `reel_usd` est relue en base.
Run: python tests/test_plafonds_reel.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import select                                        # noqa: E402
from app.services import meshy_service as MS, plafonds as P          # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

async def _un(ref):
    async with async_session_factory() as s:
        return (await s.execute(select(Depense).where(Depense.ref == ref))).scalars().first()

def test_meshy_reel():
    async def sc():
        await init_db()
        await P.verifier({"kind": "asset3d_texture", "texture_resolution": "2k"},
                         "moteurs3d", ref="meshy:t1")
        await MS.record_state({"id": "t1", "status": "SUCCEEDED", "progress": 100,
                               "consumed_credits": 10})
        l = await _un("meshy:t1")
        check(l is not None and l.reel_unites == 10.0, "crédits consommés reportés")
        p = __import__("app.services.pricing", fromlist=["x"]).load()
        check(abs(l.reel_usd - 10 * p["meshy_credit_usd"]) < 1e-9,
              "réel $ = crédits x meshy_credit_usd (grille éditable)")
        await MS.record_state({"id": "t1", "status": "SUCCEEDED", "consumed_credits": 10})
        l2 = await _un("meshy:t1")
        check(l2.reel_usd == l.reel_usd, "idempotent : un second état ne double rien")
    asyncio.run(sc())

def test_heygen_delta():
    async def sc():
        quotas = [1000, 940]
        async def _quota():
            return quotas.pop(0)
        await P.verifier({"kind": "heygen", "chars": 500}, "quick", ref="hg:job1")
        async with P.suivi_heygen("hg:job1", _quota):
            pass
        l = await _un("hg:job1")
        check(l.reel_unites == 60.0, f"60 crédits consommés (lu {l.reel_unites})")
        check(l.reel_usd is not None and l.reel_usd > 0, "converti en $ par la grille")

        # deux rendus en vol : non attribuable, on laisse vide et on le dit
        quotas2 = [1000, 900]
        async def _q2():
            return quotas2.pop(0)
        await P.verifier({"kind": "heygen", "chars": 500}, "quick", ref="hg:job2")
        async with P.suivi_heygen("hg:job2", _q2):
            P._HEYGEN_EN_VOL += 1          # un autre rendu démarre pendant celui-ci
        P._HEYGEN_EN_VOL -= 1
        l2 = await _un("hg:job2")
        check(l2.reel_usd is None, "deux rendus concurrents : réel laissé vide")
    asyncio.run(sc())

test_meshy_reel(); test_heygen_delta()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_plafonds_reel.py`
Expected : `AttributeError: module 'app.services.plafonds' has no attribute 'suivi_heygen'`

- [ ] **Step 3 : le crochet Meshy**

Dans `backend/app/services/meshy_service.py`, `record_state`, remplacer les deux lignes l. 446-447 :

```python
        if task.get("consumed_credits") is not None:
            row.consumed_credits = int(task["consumed_credits"])
```

par :

```python
        if task.get("consumed_credits") is not None:
            row.consumed_credits = int(task["consumed_credits"])
            # Coût RÉEL (plan Settings, D2) : Meshy facture en crédits et les
            # dit par tâche — c'est la seule vérité comptable de ce moteur.
            _credits_reels = row.consumed_credits
        else:
            _credits_reels = None
```

puis, APRÈS le `await s.commit()` qui termine le bloc `async with` (hors de la session, pour ne pas imbriquer deux sessions) :

```python
    if _credits_reels:
        from app.services import plafonds as _PLAF, pricing as _pricing
        _p = _pricing.load()
        await _PLAF.noter_reel(f"meshy:{tid}",
                               _credits_reels * float(_p["meshy_credit_usd"]),
                               float(_credits_reels))
```

Le rapprochement est **exact, jamais deviné** : T5 a déjà posé `await _PLAF.rattacher(_g["lignes"], f"meshy:{tid}")` sur les deux routes qui créent une tâche Meshy (le proxy et `/assets/3d/{job}/texturer`), dès que l'id existe. `record_state` n'a donc qu'à écrire sur cette référence. Une tâche Meshy créée par un chemin qui n'a pas rattaché garde son estimé et le tableau de T18 l'affiche « estimé, non rapproché » — on ne colle jamais un coût réel à « la dernière ligne meshy du mois », qui serait une heuristique et non une mesure.

- [ ] **Step 4 : `suivi_heygen` dans `plafonds.py`**

À ajouter à la fin de `backend/app/services/plafonds.py` :

```python
_HEYGEN_EN_VOL = 0


@asynccontextmanager
async def suivi_heygen(ref: str, lire_quota=None):
    """Encadre UN rendu HeyGen pour en tirer le coût réel.

    HeyGen ne facture pas par vidéo : la seule vérité est le solde du compte
    (`/v2/user/remaining_quota`, `heygen_service.py:175`). Le delta
    avant/après n'est attribuable qu'à un seul rendu — d'où le compteur de
    vols : à deux rendus concurrents on laisse « réel » vide et le tableau
    dit « non attribuable », plutôt que d'inventer un chiffre.
    """
    global _HEYGEN_EN_VOL

    async def _defaut():
        from app.services.heygen_service import HeyGenClient
        q = await HeyGenClient().remaining_quota()
        v = q.get("remaining_quota") if isinstance(q, dict) else None
        return float(v) if v is not None else None

    lire = lire_quota or _defaut
    _HEYGEN_EN_VOL += 1
    depart = _HEYGEN_EN_VOL
    try:
        avant = await lire()
    except Exception:  # noqa: BLE001 — un solde muet ne casse pas un rendu
        avant = None
    try:
        yield
    finally:
        seul = (_HEYGEN_EN_VOL == depart)
        _HEYGEN_EN_VOL -= 1
        try:
            apres = await lire() if (avant is not None and seul) else None
        except Exception:  # noqa: BLE001
            apres = None
        if avant is not None and apres is not None and apres <= avant:
            from app.services import pricing as _pricing
            credits = float(avant - apres)
            await noter_reel(ref, credits * float(_pricing.load()["heygen_credit_usd"]),
                             credits)
        else:
            logger.info(f"plafonds.suivi_heygen({ref}) : coût réel non attribuable "
                        f"(rendus concurrents ou quota illisible) — estimé conservé")
```

Ajouter en tête du module : `from contextlib import asynccontextmanager`.

- [ ] **Step 5 : encadrer les trois rendus HeyGen**

Dans `routes.py`, pour `/generate/heygen` (l. 3025), `/generate/heygen-image` (3047) et `/generate/heygen-cinematic` (3070) : la garde de T5 passe `ref=f"hg:{job_id}"`, et le corps de la coroutine `_run()` est enveloppé :

```python
    async def _run():
        async with _PLAF.suivi_heygen(f"hg:{job_id}"):
            try:
                ...   # le corps existant, inchangé
```

- [ ] **Step 6 : lancer, constater le vert**

Run : `python tests/test_plafonds_reel.py`
Expected : 6 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/meshy_service.py backend/app/services/plafonds.py backend/app/api/routes.py backend/tests/test_plafonds_reel.py
git commit -m 'reglages : le cout reel de Meshy et de HeyGen remonte dans le registre' -m 'Meshy dit consumed_credits par tache : exact. HeyGen ne dit rien par video, seulement le solde du compte : le delta avant/apres nest attribuable qua un rendu en vol, sinon la colonne reste vide et le journal le dit. Inventer un chiffre serait pire que ne rien dire.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 7 : Plafonds — l'écran, la barre de confirmation et l'alerte à 80 % (section S4)

**Files:**
- Modify: `scripts/patch_bundle_reglages.py` (section S4)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur)
- Test: `backend/tests/test_patch_reglages.py` (assertions ajoutées)

**Coût de patch** : S4 ajoute au bloc S1 le composant `DzPlafonds` **et** une IIFE qui enveloppe `window.fetch`. Aucune ancre nouvelle : le composant se greffe sur la branche `pricing` déjà consommée par S3, l'IIFE vit dans le bloc.

**Limite dite** : le rejeu après confirmation n'est possible que quand `fetch` a été appelé avec une **URL en chaîne** (`fetch(url, init)`) — le corps d'un objet `Request` déjà construit n'est pas rejouable. Le bundle appelle toujours `fetch` avec une chaîne (vérifié : `D.postJson`, `Ge`, `setKeys`, `DzPricing` — tous en chaîne) ; si un jour ce n'était plus vrai, le 402 remonterait tel quel à l'appelant plutôt que de mentir.

- [ ] **Step 1 : ajouter les assertions au banc (rouge)**

Insérer dans `backend/tests/test_patch_reglages.py`, juste avant la ligne `b = cible.read_bytes()` :

```python
    check("function DzPlafonds(" in s, "DzPlafonds injecté")
    check(s.count("__dzPlafondFetch") == 1, "l'enveloppe de fetch est posée une fois")
    check("X-DZ-Plafond" in s, "l'en-tête de confirmation est bien celui du backend")
    check(s.count("r.jsx(DzPlafonds,{})") == 1, "DzPlafonds monté dans la branche pricing")
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : quatre `FAIL` sur les nouvelles lignes, `4 échec(s)`.

- [ ] **Step 3 : la section S4 du patcheur**

Dans `scripts/patch_bundle_reglages.py`, ajouter la constante `S4` après `S1`, puis l'insérer dans `patcher()`.

```python
# ── S4 : plafonds — l'écran, la barre de confirmation, l'alerte 80 % ───────

S4 = (
    "function DzPlafonds(){"
    "const[p,setP]=x.useState(null),[e,setE]=x.useState(null),"
    "[msg,setMsg]=x.useState('');const refs=x.useRef({});"
    "const charger=()=>{fetch('/api/reglages/plafonds').then(R=>R.json())"
    ".then(setP).catch(()=>{});fetch('/api/reglages/plafonds/etat')"
    ".then(R=>R.json()).then(setE).catch(()=>{})};"
    "x.useEffect(()=>{charger()},[]);"
    "if(!p||!e)return r.jsx('div',{style:{padding:16,color:'var(--ink-muted)'},"
    "children:'Plafonds...'});"
    "const moteurs=['fal','heygen','elevenlabs','meshy','openai','anthropic','gemini'];"
    "const sauver=()=>{const pm={};moteurs.forEach(m=>{const el=refs.current[m];"
    "const v=el?parseFloat(el.value):NaN;if(!isNaN(v)&&v>0)pm[m]=v});"
    "const g=parseFloat((refs.current.__g||{}).value);"
    "const a=parseFloat((refs.current.__a||{}).value);"
    "fetch('/api/reglages/plafonds',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({global_usd:isNaN(g)?0:g,par_moteur:pm,"
    "alerte_pct:isNaN(a)?80:a})}).then(R=>R.json()).then(d=>{setP(d);"
    "setMsg('Plafonds enregistres.');setTimeout(()=>setMsg(''),4000);charger()})"
    ".catch(()=>setMsg('Echec de lenregistrement.'))};"
    "const ligne=(k,l,u,val,def)=>r.jsxs('div',{style:{display:'grid',"
    "gridTemplateColumns:'220px 130px 1fr',gap:12,alignItems:'center',"
    "padding:'6px 0',borderTop:'1px solid var(--stroke)'},children:["
    "r.jsx('div',{style:{fontSize:12.5},children:l}),"
    "r.jsx('input',{type:'number',step:'1',defaultValue:val,"
    "ref:el=>{refs.current[k]=el},style:{background:'var(--bg-base)',"
    "border:'1px solid var(--stroke)',borderRadius:'var(--r-sm)',"
    "padding:'5px 8px',color:'var(--ink-strong)',"
    "fontFamily:'var(--f-mono)',fontSize:12}}),"
    "r.jsx('div',{style:{fontSize:11,color:'var(--ink-muted)'},children:u})]},k);"
    "return r.jsxs(jt,{style:{padding:16,marginTop:18},children:["
    "r.jsx('div',{className:'display',style:{fontSize:18,"
    "color:'var(--ink-strong)',marginBottom:4},children:'Plafonds de depense'}),"
    "r.jsxs('div',{style:{fontSize:12,color:'var(--ink-soft)',marginBottom:14},"
    "children:['Mensuels, en dollars. 0 = pas de plafond. Le refus vient du "
    "BACKEND : aucun tir ne passe derriere lui, meme depuis un script. "
    "Compte tenu depuis le ',e.depuis||'premier tir',' - ',"
    "e.global.effectif_usd.toFixed(2),' $ ce mois-ci (',"
    "e.global.estime_usd.toFixed(2),' $ estimes, ',"
    "e.global.reel_usd.toFixed(2),' $ factures).']}),"
    "ligne('__g','Plafond global','$ / mois - toutes depenses',p.global_usd),"
    "moteurs.map(m=>ligne(m,'Plafond '+m,"
    "(e.par_moteur[m]?e.par_moteur[m].effectif_usd.toFixed(2):'0.00')"
    "+' $ deja ce mois-ci',p.par_moteur[m]||0)),"
    "ligne('__a','Alerte a','% du plafond',p.alerte_pct),"
    "r.jsxs('div',{style:{marginTop:14,display:'flex',gap:10,alignItems:'center'},"
    "children:[r.jsx(K,{variant:'primary',size:'md',icon:'check',glow:!0,"
    "onClick:sauver,children:'Enregistrer'}),"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)'},children:msg}),"
    "e.alerte.length?r.jsx(te,{tone:'amber',dot:!0,"
    "children:'alerte : '+e.alerte.join(', ')}):null]})]})}"

    # l enveloppe de fetch : un 402 de plafond devient une barre de
    # confirmation, et le tir est REJOUE avec l en-tete. Une seule pose.
    "(function(){if(window.__dzPlafondFetch)return;window.__dzPlafondFetch=1;"
    "var of=window.fetch;"
    "function barre(d){return new Promise(function(res){"
    "var w=document.createElement('div');"
    "w.style.cssText='position:fixed;right:18px;bottom:18px;z-index:99999;"
    "max-width:420px;background:var(--bg-panel);border:1px solid var(--stroke);"
    "border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.45);padding:14px 16px;"
    "font-size:12.5px;color:var(--ink);font-family:inherit';"
    "var t=document.createElement('div');t.textContent=d.message||'Plafond atteint.';"
    "t.style.cssText='margin-bottom:10px;line-height:1.45';"
    "var br=document.createElement('div');"
    "br.style.cssText='display:flex;gap:8px;justify-content:flex-end';"
    "var no=document.createElement('button');no.textContent='Annuler';"
    "var ou=document.createElement('button');ou.textContent='Tirer quand meme';"
    "[no,ou].forEach(function(b){b.style.cssText='height:28px;padding:0 12px;"
    "border-radius:8px;border:1px solid var(--stroke);cursor:pointer;"
    "font-size:12px;background:var(--bg-panel-2);color:var(--ink)'});"
    "ou.style.background='var(--brand)';ou.style.color='#04121a';"
    "no.onclick=function(){w.remove();res(!1)};"
    "ou.onclick=function(){w.remove();res(!0)};"
    "br.appendChild(no);br.appendChild(ou);w.appendChild(t);w.appendChild(br);"
    "document.body.appendChild(w)})}"
    "window.fetch=function(u,o){var a=arguments;"
    "return of.apply(this,a).then(function(R){"
    "if(R.status!==402||typeof u!=='string')return R;"
    "return R.clone().json().then(function(j){"
    "var d=j&&j.detail&&j.detail.dz_plafond;if(!d)return R;"
    "return barre(d).then(function(ok){if(!ok)return R;"
    "var o2=Object.assign({},o||{});"
    "o2.headers=Object.assign({},(o&&o.headers)||{},{'X-DZ-Plafond':'confirme'});"
    "return of.call(window,u,o2)})}).catch(function(){return R})})}})();"
)
```

> Un commentaire Python (`#`) entre deux chaînes juxtaposées est parfaitement légal et ne casse pas la concaténation — c'est la seule forme de commentaire admise ici, puisque le résultat doit être du JS sans le moindre saut de ligne.

Dans `patcher()`, remplacer la première ligne par :

```python
    s = apply(s, "}function DzPricing(){", "}" + S1 + S4 + "function DzPricing(){", "S1-bloc")
```

et la dernière par :

```python
    s = apply(s, 's==="pricing"&&r.jsx(DzPricing,{})]})',
              's==="pricing"&&r.jsxs(r.Fragment,{children:[r.jsx(DzPricing,{}),'
              'r.jsx(DzPlafonds,{})]}),s==="diag"&&r.jsx(DzDiag,{})]})',
              "S3-corps")
```

- [ ] **Step 4 : lancer, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 16 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 5 : appliquer, comparer, voir**

Run (racine du dépôt) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Expected : `--diff` sort 0, seules `DzPlafonds` et `barre` s'ajoutent aux noms de fonctions. Puis, l'app relancée **par l'utilisateur** : Réglages → *Pricing & budget* montre la carte « Plafonds de depense » sous la grille de prix ; mettre le plafond global à `0.01`, aller dans Quick, lancer une image → la barre de confirmation apparaît en bas à droite avec le chiffre, « Tirer quand meme » relance le même appel et il passe.

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : ecran des plafonds et barre de confirmation sur le 402' -m 'Une enveloppe de window.fetch, posee une seule fois, transforme le 402 du backend en barre de confirmation et rejoue le tir avec len-tete. Limite dite : le rejeu ne vaut que pour fetch(url, init) - un objet Request deja construit remonte le 402 tel quel plutot que de mentir.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 8 : Test de clé à l'enregistrement, application à chaud, guides par fournisseur

**Files:**
- Create: `backend/app/services/guides_fournisseurs.py`
- Modify: `backend/app/api/routes.py:3502` (`_ALLOWED_ENV_KEYS` — ajout de `FIGMA_TOKEN`), `routes.py:3568-3614` (`set_key`)
- Modify: `backend/app/api/settings_routes.py` (route `/guides`)
- Test: `backend/tests/test_guides_et_cles.py`

**Bug mesuré, réparé ici** : `FIGMA_TOKEN` est lu par l'import Figma (`routes.py:8807`, `figma_import.py:6`) et le message d'erreur dit à l'utilisateur de le poser « dans le .env » — mais la clé n'est **pas** dans `_ALLOWED_ENV_KEYS` (l. 3502-3517), donc l'écran Settings refuse de l'écrire. Un seul ajout ferme le trou.

**Application à chaud, avec sa mesure** : `restart_required: True` est vrai depuis v1.8 et personne ne l'a remesuré. Le grep du 03/09 dit qu'aucune clé n'est figée à l'import : les 40 lectures passent par `settings.X` dans un corps de fonction, et la seule capture d'instance (`heygen_service.py:60`) est refaite à chaque `HeyGenClient()`. **Une seule exception** : `fal_service.py:34-35` recopie `settings.FAL_KEY` dans `os.environ["FAL_KEY"]` à l'import. On écrit donc les DEUX, et `restart_required` devient faux — sauf pour un champ non-`str` de `Settings` (`ARTICLE_READER_FALLBACK`), où l'on continue de dire la vérité.

- [ ] **Step 0 : ouvrir les liens une fois et les dater**

Aucun lien de console n'est copié « de mémoire » dans le code sans avoir été ouvert. Ouvrir chacun **dans le navigateur**, vérifier qu'il mène bien à la page de création de clé (une page de connexion qui renvoie ensuite au bon endroit compte comme vérifiée), puis reporter la date dans le champ `verifie_le` de l'entrée. Le 03/09/2026, seuls deux ont pu être contrôlés depuis cette session :

| Clé | Console | Statut au 03/09/2026 |
|---|---|---|
| `FAL_KEY` | `https://fal.ai/dashboard/keys` | **vérifié** — la page de connexion renvoie vers `/dashboard/keys` |
| — | `https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest` | **vérifié** (T10) |
| `OPENAI_API_KEY` | `https://platform.openai.com/api-keys` | **403 depuis l'outil** — à ouvrir au navigateur |
| `ANTHROPIC_API_KEY` | `https://console.anthropic.com/settings/keys` | à ouvrir |
| `GEMINI_API_KEY` | `https://aistudio.google.com/apikey` | à ouvrir |
| `ELEVENLABS_API_KEY` | `https://elevenlabs.io/app/settings/api-keys` | à ouvrir |
| `HEYGEN_API_KEY` | `https://app.heygen.com/settings?nav=API` | à ouvrir |
| `MESHY_API_KEY` | `https://www.meshy.ai/api` | à ouvrir (déjà cité par `Fu` dans le bundle) |
| `FIGMA_TOKEN` | `https://www.figma.com/developers/api#access-tokens` | à ouvrir (le chemin `Settings → Security → Personal access tokens` est déjà écrit dans `config.py:88`) |
| `TELEGRAM_BOT_TOKEN` | `https://t.me/BotFather` | à ouvrir |
| `X_API_KEY` … | `https://developer.x.com/en/portal/dashboard` | à ouvrir |

Un lien qui a bougé se corrige DANS le module avant d'écrire la suite : un guide qui envoie sur un 404 est pire que pas de guide.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Guides fournisseurs, application à chaud, test à l'enregistrement
(plan Settings T8).

Banc-miroir : après un POST, le banc RELIT le fichier `.env` sur le disque et
l'objet `settings` en mémoire — jamais la réponse seule. Réseau : zéro.
Run: python tests/test_guides_et_cles.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
(_tmp / ".env").write_text("FAL_KEY=ancienne\n", encoding="utf-8")

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                           # noqa: E402
from app.config import settings                                    # noqa: E402
from app.services import diagnostic as D, guides_fournisseurs as G  # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

async def _faux_get(url, headers=None, timeout=15.0):
    if "queue.fal.run" in url:
        return 404, {"detail": "Request not found"}
    if "api.figma.com" in url:
        return 200, {"handle": "olivier"}
    return 401, {"error": {"message": "invalid key"}}
D._get = _faux_get

c = TestClient(app)

def test_guides_complets():
    g = G.tous()
    for cle in sorted(D.TESTABLES):
        if cle.startswith("X_") and cle != "X_API_KEY":
            continue                     # les quatre X partagent une entrée
        e = g.get(cle)
        check(bool(e), f"{cle} : guide présent")
        if not e:
            continue
        check(e["console"].startswith("https://"), f"{cle} : lien console en https")
        check(len(e["fr"]) > 80 and len(e["en"]) > 80, f"{cle} : texte FR et EN écrits")
        check(e["verifie_le"].startswith("2026-"), f"{cle} : date de vérification portée")
    r = c.get("/api/reglages/guides")
    check(r.status_code == 200 and "FAL_KEY" in r.json()["guides"], "route /guides sert la table")

def test_figma_enfin_ecrivable():
    r = c.post("/api/settings/keys", json={"name": "FIGMA_TOKEN", "value": "figd_xyz"})
    check(r.status_code == 200, f"FIGMA_TOKEN accepté (lu {r.status_code})")
    env = (_tmp / ".env").read_text(encoding="utf-8")
    check("FIGMA_TOKEN=figd_xyz" in env, "écrit dans le .env du dossier de données")
    check(settings.FIGMA_TOKEN == "figd_xyz", "appliqué à chaud dans settings")

def test_application_a_chaud_et_test():
    r = c.post("/api/settings/keys",
               json={"entries": [{"name": "FAL_KEY", "value": "cle-neuve"}], "tester": True})
    j = r.json()
    check(j["restart_required"] is False, "plus de redémarrage exigé pour une clé texte")
    check(settings.FAL_KEY == "cle-neuve", "settings.FAL_KEY à jour")
    check(os.environ["FAL_KEY"] == "cle-neuve",
          "os.environ à jour AUSSI (fal_service.py:34-35 recopie la clé à l'import)")
    check(j["tests"]["FAL_KEY"]["ok"] is True, "la clé est testée dans la foulée")
    check("cle-neuve" not in json.dumps(j), "la réponse ne renvoie jamais la valeur")
    r2 = c.post("/api/settings/keys",
                json={"entries": [{"name": "ARTICLE_READER_FALLBACK", "value": "false"}]})
    check(r2.json()["restart_required"] is True,
          "un champ non-texte de Settings dit encore la vérité : redémarrage")

test_guides_complets(); test_figma_enfin_ecrivable(); test_application_a_chaud_et_test()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_guides_et_cles.py`
Expected : `ModuleNotFoundError: No module named 'app.services.guides_fournisseurs'`

- [ ] **Step 3 : écrire `guides_fournisseurs.py`**

```python
"""Guide par fournisseur (plan Settings, P3).

Une entrée par clé testable : où créer la clé, comment on est facturé, à quoi
elle sert DANS CETTE APPLI. Deux langues, parce que l'app est bilingue depuis
la localisation de juin. `verifie_le` est la date à laquelle le lien a été
OUVERT, pas celle où il a été écrit : un guide qui envoie sur un 404 est pire
que pas de guide (voir Step 0 du plan, T8).
"""

GUIDES = {
    "FAL_KEY": {
        "nom": "fal.ai",
        "console": "https://fal.ai/dashboard/keys",
        "tarifs": "https://fal.ai/pricing",
        "verifie_le": "2026-09-03",
        "fr": "Crée un compte sur fal.ai, ouvre Dashboard → Keys, « Add key », "
              "et copie la valeur tout de suite (elle ne se réaffiche jamais). "
              "Facturation à l'usage, sans abonnement : tu paies l'image ou la "
              "seconde de vidéo. C'est la clé indispensable — sans elle, ni "
              "image, ni clip, ni musique, ni retrait de fond.",
        "en": "Create a fal.ai account, open Dashboard → Keys, click « Add key » "
              "and copy the value right away (it is never shown again). "
              "Pay-as-you-go, no subscription: you pay per image or per second "
              "of video. This is the one required key — without it there are no "
              "images, no clips, no music and no background removal.",
    },
    "HEYGEN_API_KEY": {
        "nom": "HeyGen",
        "console": "https://app.heygen.com/settings?nav=API",
        "tarifs": "https://www.heygen.com/pricing",
        "verifie_le": "",
        "fr": "Compte HeyGen, Settings → API, « Create token ». Facturation en "
              "CRÉDITS d'un abonnement mensuel : l'app lit le solde restant et "
              "l'affiche dans le Diagnostic. Sert aux avatars parlants (Quick, "
              "Studio, Composition).",
        "en": "HeyGen account, Settings → API, « Create token ». Billed in "
              "CREDITS from a monthly plan: the app reads the remaining balance "
              "and shows it in Diagnostic. Powers the talking avatars (Quick, "
              "Studio, Composition).",
    },
    "ELEVENLABS_API_KEY": {
        "nom": "ElevenLabs",
        "console": "https://elevenlabs.io/app/settings/api-keys",
        "tarifs": "https://elevenlabs.io/pricing",
        "verifie_le": "",
        "fr": "Compte ElevenLabs, Settings → API Keys. Facturation en "
              "CARACTÈRES d'un quota mensuel : le Diagnostic affiche le "
              "restant. Sert à la voix off, aux bruitages et à la "
              "transcription des sous-titres. Le serveur local Voicebox fait "
              "la voix gratuitement quand il tourne — la clé reste optionnelle.",
        "en": "ElevenLabs account, Settings → API Keys. Billed in CHARACTERS "
              "from a monthly quota: Diagnostic shows what is left. Powers "
              "voiceover, sound effects and subtitle transcription. The local "
              "Voicebox server does voices for free when it runs — this key "
              "stays optional.",
    },
    "MESHY_API_KEY": {
        "nom": "Meshy",
        "console": "https://www.meshy.ai/api",
        "tarifs": "https://www.meshy.ai/pricing",
        "verifie_le": "",
        "fr": "Compte Meshy avec un plan API, page API. Facturation en CRÉDITS "
              "et Meshy dit exactement combien chaque tâche a consommé : c'est "
              "le seul moteur dont la colonne « réel » du tableau de dépenses "
              "est exacte. Sert au texturage 3D et au 3D Studio. "
              "MESHY_MOCK=1 fait tourner toute la chaîne sans clé ni crédit.",
        "en": "Meshy account with an API plan, API page. Billed in CREDITS and "
              "Meshy reports exactly what each task consumed: it is the only "
              "engine whose « actual » column in the spend table is exact. "
              "Powers 3D texturing and 3D Studio. MESHY_MOCK=1 runs the whole "
              "chain with no key and no credits.",
    },
    "ANTHROPIC_API_KEY": {
        "nom": "Anthropic",
        "console": "https://console.anthropic.com/settings/keys",
        "tarifs": "https://www.anthropic.com/pricing",
        "verifie_le": "",
        "fr": "Console Anthropic, Settings → API keys. Facturation aux jetons "
              "(entrée/sortie). Sert au résumé des articles News et au "
              "planificateur marketing. Le modèle est réglable juste en dessous "
              "(ANTHROPIC_MODEL).",
        "en": "Anthropic console, Settings → API keys. Billed per token "
              "(input/output). Powers the News article summariser and the "
              "marketing planner. The model is configurable just below "
              "(ANTHROPIC_MODEL).",
    },
    "OPENAI_API_KEY": {
        "nom": "OpenAI",
        "console": "https://platform.openai.com/api-keys",
        "tarifs": "https://openai.com/api/pricing/",
        "verifie_le": "",
        "fr": "Plateforme OpenAI, API keys. Facturation aux jetons pour le "
              "texte, à l'image pour GPT Image. Alternative à Anthropic pour "
              "les résumés et les plans ; sert aussi à la transcription "
              "(whisper) des sous-titres.",
        "en": "OpenAI platform, API keys. Billed per token for text and per "
              "image for GPT Image. An alternative to Anthropic for summaries "
              "and plans; also powers subtitle transcription (whisper).",
    },
    "GEMINI_API_KEY": {
        "nom": "Google Gemini",
        "console": "https://aistudio.google.com/apikey",
        "tarifs": "https://ai.google.dev/pricing",
        "verifie_le": "",
        "fr": "Google AI Studio, « Get API key ». Facturation aux jetons ; un "
              "palier gratuit existe. Sert aux résumés, aux plans, et aux "
              "modèles vidéo Veo servis en direct par Google (les mêmes "
              "modèles passés par fal utilisent FAL_KEY, pas celle-ci).",
        "en": "Google AI Studio, « Get API key ». Billed per token; a free tier "
              "exists. Powers summaries, plans, and the Veo video models served "
              "directly by Google (the same models served through fal use "
              "FAL_KEY, not this one).",
    },
    "FIGMA_TOKEN": {
        "nom": "Figma",
        "console": "https://www.figma.com/developers/api#access-tokens",
        "tarifs": "",
        "verifie_le": "",
        "fr": "figma.com → ton avatar → Settings → Security → Personal access "
              "tokens. Gratuit. Sert à importer un cadre Figma dans la "
              "Bibliothèque et dans Card Forge. Sans ce jeton, l'import répond "
              "409 en le disant.",
        "en": "figma.com → your avatar → Settings → Security → Personal access "
              "tokens. Free. Used to import a Figma frame into the Library and "
              "into Card Forge. Without it the import answers 409 and says so.",
    },
    "TELEGRAM_BOT_TOKEN": {
        "nom": "Telegram",
        "console": "https://t.me/BotFather",
        "tarifs": "",
        "verifie_le": "",
        "fr": "Écris à @BotFather sur Telegram, /newbot, il rend un jeton "
              "« 12345:AA… ». Gratuit, sans validation. C'est le canal de "
              "publication de référence du Scheduler. Pense à remplir aussi "
              "TELEGRAM_CHAT_ID (l'id du salon où publier).",
        "en": "Message @BotFather on Telegram, /newbot, it returns a token "
              "« 12345:AA… ». Free, no review process. This is the Scheduler's "
              "reference publishing channel. Fill TELEGRAM_CHAT_ID too (the id "
              "of the chat to post into).",
    },
    "X_API_KEY": {
        "nom": "X (Twitter)",
        "console": "https://developer.x.com/en/portal/dashboard",
        "tarifs": "https://developer.x.com/en/portal/products",
        "verifie_le": "",
        "fr": "Portail développeur X, crée une App, active « Read and write », "
              "puis relève les QUATRE valeurs : API key, API secret, Access "
              "token, Access token secret. Le palier gratuit autorise les "
              "publications avec un quota mensuel. Les quatre se testent "
              "ensemble, jamais une par une.",
        "en": "X developer portal, create an App, enable « Read and write », "
              "then collect ALL FOUR values: API key, API secret, Access token, "
              "Access token secret. The free tier allows posting within a "
              "monthly quota. All four are tested together, never one by one.",
    },
    "OLLAMA_URL": {
        "nom": "Ollama (local)",
        "console": "https://ollama.com/download",
        "tarifs": "",
        "verifie_le": "",
        "fr": "Pas une clé : l'adresse d'un serveur Ollama qui tourne sur ta "
              "machine (par défaut http://127.0.0.1:11434). Gratuit, et rien ne "
              "sort du PC. Renseigne aussi OLLAMA_MODEL (qwen2.5:14b-instruct "
              "ou mieux ; 8B est le plancher).",
        "en": "Not a key: the address of an Ollama server running on your "
              "machine (http://127.0.0.1:11434 by default). Free, and nothing "
              "leaves the PC. Set OLLAMA_MODEL too (qwen2.5:14b-instruct or "
              "better; 8B is the floor).",
    },
}
# Les quatre clés X partagent le guide de X_API_KEY.
for _k in ("X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    GUIDES[_k] = GUIDES["X_API_KEY"]


def guide(nom: str) -> dict | None:
    return GUIDES.get(nom)


def tous() -> dict:
    return dict(GUIDES)
```

- [ ] **Step 4 : ouvrir `FIGMA_TOKEN` à l'écriture**

Dans `backend/app/api/routes.py`, `_ALLOWED_ENV_KEYS` (l. 3502), ajouter la ligne après `"OLLAMA_URL", "OLLAMA_MODEL",` :

```python
    # 03/09/2026 : lu par l'import Figma (routes.py:8807, figma_import.py) et
    # cité par son message d'erreur, mais absent de cette liste depuis v1.8 —
    # l'écran Settings refusait donc d'écrire la clé qu'il demandait.
    "FIGMA_TOKEN",
```

- [ ] **Step 5 : application à chaud + test à l'enregistrement**

Dans `set_key` (`routes.py:3568`), remplacer la fin de la fonction (depuis `p.write_text(...)`) par :

```python
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"Wrote {len(changes)} key(s) to {p}")

    # Application À CHAUD (plan Settings, P3). Mesuré le 03/09/2026 : aucune
    # clé n'est figée à l'import — les 40 lectures passent par `settings.X`
    # dans un corps de fonction et `HeyGenClient` relit la sienne à chaque
    # instance. La seule copie d'environnement est fal_service.py:34-35, qui
    # recopie FAL_KEY dans os.environ pour le client fal : on écrit donc les
    # DEUX. Seul un champ non-`str` de Settings (ARTICLE_READER_FALLBACK)
    # exige encore un redémarrage, et on continue de le dire.
    a_froid = []
    for k, v in changes.items():
        os.environ[k] = v
        courant = getattr(settings, k, "")
        if isinstance(courant, str):
            try:
                setattr(settings, k, v)
            except Exception:  # noqa: BLE001
                a_froid.append(k)
        else:
            a_froid.append(k)

    tests: dict = {}
    if (body or {}).get("tester"):
        from app.services import diagnostic as _D
        for k, v in changes.items():
            if v and _D.testable(k):
                tests[k] = await _D.tester_cle(k, v)

    return {
        "ok": True,
        "written": list(changes.keys()),
        "restart_required": bool(a_froid),
        "restart_for": a_froid,
        "tests": tests,
        "message": ("Enregistré et appliqué tout de suite."
                    if not a_froid else
                    "Enregistré. Redémarrage nécessaire pour : "
                    + ", ".join(a_froid) + "."),
    }
```

`os` est déjà importé en tête de `routes.py`.

- [ ] **Step 6 : la route des guides**

À ajouter à `backend/app/api/settings_routes.py` :

```python
@router.get("/guides")
async def lire_guides(request: Request):
    """Où créer chaque clé, comment on est facturé, à quoi elle sert ici."""
    _local(request)
    from app.services import guides_fournisseurs as G
    return {"guides": G.tous()}
```

- [ ] **Step 7 : lancer, constater le vert**

Run : `python tests/test_guides_et_cles.py`
Expected : 40 lignes `ok   …` puis `0 échec(s)`. (10 clés × 3 assertions + la route + 3 + 6 ; le compte exact dépend de `TESTABLES`, seul `0 échec(s)` fait foi.)

- [ ] **Step 8 : essai manuel des tests de clés en direct (le banc les remplace, la vraie vie non)**

Le banc remplace `diagnostic._get` : il prouve le CÂBLAGE, pas les codes HTTP réels des fournisseurs. Une fois, à la main, avec les vraies clés, sur l'app relancée par l'utilisateur : Réglages → Diagnostic → « Tester » sur chaque ligne, et noter dans ce tableau ce que chaque fournisseur a répondu.

| Clé | Attendu | Observé | Date |
|---|---|---|---|
| `FAL_KEY` | vert, message « 404 sur une requête fictive, comme attendu » | | |
| `FAL_KEY` faussée | rouge — **le 401 de fal sur clé invalide n'est PAS documenté** (référence marquée « partiel ») : c'est CE test qui tranche | | |
| `HEYGEN_API_KEY` | vert + crédits restants | | |
| `ELEVENLABS_API_KEY` | vert + caractères restants | | |
| `MESHY_API_KEY` | vert + solde de crédits | | |
| `ANTHROPIC_API_KEY` | vert (`GET /v1/models`) | | |
| `OPENAI_API_KEY` | vert (`GET /v1/models`) — **URL de mémoire**, à confirmer ici | | |
| `GEMINI_API_KEY` | vert (`x-goog-api-key`) | | |
| `FIGMA_TOKEN` | vert + le handle du compte — **URL de mémoire**, à confirmer ici | | |
| `TELEGRAM_BOT_TOKEN` | vert + le nom du bot | | |
| `OLLAMA_URL` | vert + la liste des modèles locaux, ou rouge « injoignable » si Ollama ne tourne pas | | |
| Les quatre `X_*` | vert + le compte X — **chemin tweepy de mémoire**, à confirmer ici | | |

Une ligne qui ne se comporte pas comme annoncé se corrige dans `diagnostic.tester_cle` AVANT de passer à T9.

- [ ] **Step 9 : commit**

```bash
git add backend/app/services/guides_fournisseurs.py backend/app/api/routes.py backend/app/api/settings_routes.py backend/tests/test_guides_et_cles.py
git commit -m 'reglages : guides par fournisseur, FIGMA_TOKEN ecrivable, cles appliquees a chaud' -m 'FIGMA_TOKEN etait lu par limport Figma et cite par son message derreur, mais absent de lallowlist depuis v1.8 : lecran refusait decrire la cle quil reclamait. Le redemarrage exige depuis v1.8 na jamais ete remesure : le grep du 03/09 montre que rien nest fige a limport sauf la recopie de FAL_KEY dans os.environ par fal_service, donc on ecrit les deux et restart_required tombe a faux — sauf pour un champ non-texte, ou lon continue de le dire.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 9 : L'écran des clés — bouton Tester, verdict et guide (section S5)

**Files:**
- Modify: `scripts/patch_bundle_reglages.py` (section S5)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur)
- Test: `backend/tests/test_patch_reglages.py` (assertions ajoutées)

**Coût de patch** : S5 ajoute le composant `DzTestCle` au bloc S1 et consomme **quatre ancres neuves**, chacune comptée 1 le 03/09 (vérifié) :

| Ancre | Compte | Rôle |
|---|---|---|
| `,health:"has_meshy"}];function bm(){` | 1 | fin du tableau `Fu` — on y ajoute `FIGMA_TOKEN` et `TELEGRAM_BOT_TOKEN` |
| `gridTemplateColumns:"220px 1fr auto auto",gap:14` | 1 | la grille d'une ligne de clé passe à cinq colonnes |
| `children:h&&h.set?"set":"missing"}),` | 1 | juste après la pastille : on insère `DzTestCle` |
| `f(\`${k} saved — restart the backend to apply.\`)` | 1 | le message d'une clé enregistrée (le libellé mentait depuis T8) |
| `key(s) saved — restart the backend to apply.` | 1 | le message du bouton « tout enregistrer » |

> Le libellé `saved — restart the backend to apply.` apparaît **deux** fois dans le bundle : c'est pourquoi on ancre sur les deux formes complètes, distinctes, plutôt que sur le fragment commun.

- [ ] **Step 1 : ajouter les assertions au banc (rouge)**

Insérer dans `backend/tests/test_patch_reglages.py`, avant `b = cible.read_bytes()` :

```python
    check("function DzTestCle(" in s, "DzTestCle injecté")
    check(s.count('{k:"FIGMA_TOKEN"') == 1, "FIGMA_TOKEN ajouté au tableau des clés")
    check(s.count('gridTemplateColumns:"220px 1fr auto auto auto"') == 1,
          "la ligne de clé passe à cinq colonnes")
    check("restart the backend to apply" not in s,
          "les deux messages de redémarrage ont disparu (T8 applique à chaud)")
    check("pydantic-settings re-reads the file" not in s,
          "le texte d'aide ne promet plus un redémarrage")
    check(s.count("/api/reglages/guides") == 1, "le guide est chargé une fois")
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : six `FAIL` sur les nouvelles lignes, `6 échec(s)`.

- [ ] **Step 3 : la section S5 du patcheur**

Ajouter la constante `S5` dans `scripts/patch_bundle_reglages.py` :

```python
# ── S5 : tester une clé depuis sa ligne, et son guide ──────────────────────

S5 = (
    "var dzGuides=null,dzGuidesAtt=null;"
    "function dzChargerGuides(){if(dzGuidesAtt)return dzGuidesAtt;"
    "dzGuidesAtt=fetch('/api/reglages/guides').then(R=>R.json())"
    ".then(j=>{dzGuides=j.guides||{};return dzGuides}).catch(()=>({}));"
    "return dzGuidesAtt}"

    "function DzTestCle({ck:ck,def:def_}){"
    "const[e,setE]=x.useState(null),[g,setG]=x.useState(dzGuides);"
    "x.useEffect(()=>{dzChargerGuides().then(setG)},[]);"
    "const gu=(g||{})[ck];"
    "const tester=()=>{setE({ok:null,message:'test...'});"
    "fetch('/api/reglages/diagnostic/cle',{method:'POST',"
    "headers:{'Content-Type':'application/json'},body:JSON.stringify({nom:ck})})"
    ".then(R=>R.json()).then(setE)"
    ".catch(er=>setE({ok:!1,message:String(er)}))};"
    "return r.jsxs('div',{style:{display:'flex',flexDirection:'column',gap:4,"
    "alignItems:'flex-end',minWidth:150},children:["
    "r.jsxs('div',{style:{display:'flex',gap:6,alignItems:'center'},children:["
    "gu?r.jsx('a',{href:gu.console,target:'_blank',rel:'noreferrer',"
    "title:gu.fr,style:{fontSize:11,color:'var(--cyan)',textDecoration:'none'},"
    "children:'Guide'}):null,"
    "def_?r.jsx(K,{variant:'ghost',size:'sm',onClick:tester,children:'Tester'}):null]}),"
    "e?r.jsx('div',{title:String(e.message||''),style:{fontSize:10.5,maxWidth:150,"
    "textAlign:'right',overflow:'hidden',textOverflow:'ellipsis',"
    "whiteSpace:'nowrap',color:e.ok===!0?'var(--green)':e.ok===!1?'var(--red)'"
    ":'var(--ink-muted)'},children:(e.ok===!0?'OK - ':e.ok===!1?'Refus - ':'')"
    "+String(e.message||'')}):null]})}"
)
```

Puis, dans `patcher()`, après les quatre remplacements existants :

```python
    s = apply(s, ',health:"has_meshy"}];function bm(){',
              ',health:"has_meshy"},'
              '{k:"FIGMA_TOKEN",label:"Figma (import)",'
              'why:"importer un cadre Figma dans la Bibliotheque et Card Forge",'
              'health:"figma_enabled"},'
              '{k:"TELEGRAM_BOT_TOKEN",label:"Telegram (publication)",'
              'why:"canal de publication du Scheduler - @BotFather",'
              'health:"telegram_enabled"}];function bm(){', "S5a-table-cles")
    s = apply(s, 'gridTemplateColumns:"220px 1fr auto auto",gap:14',
              'gridTemplateColumns:"220px 1fr auto auto auto",gap:14', "S5b-grille")
    s = apply(s, 'children:h&&h.set?"set":"missing"}),',
              'children:h&&h.set?"set":"missing"}),'
              'r.jsx(DzTestCle,{ck:k.k,def:!!(h&&h.set)}),', "S5c-bouton")
    s = apply(s, "f(`${k} saved — restart the backend to apply.`)",
              "f(`${k} enregistree et appliquee.`)", "S5d-message-1")
    s = apply(s, "key(s) saved — restart the backend to apply.",
              "cle(s) enregistree(s) et appliquee(s).", "S5e-message-2")
    s = apply(s,
              'r.jsx("strong",{children:"Restart the backend"}),'
              '" after saving so pydantic-settings re-reads the file."',
              'r.jsx("strong",{children:"Aucun redemarrage"}),'
              '" n\'est necessaire : la cle est appliquee tout de suite, et le '
              'bouton Tester dit si le fournisseur l\'accepte."', "S5f-aide")
```

et brancher `S5` dans le bloc injecté :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + "function DzPricing(){", "S1-bloc")
```

> `figma_enabled` n'existe pas encore dans `/health` : la pastille verte/rouge de cette ligne se fie alors à `set`/`missing` du `.env`, ce qui est le comportement voulu (la santé sert d'indice, la clé fait foi). Ajouter `"figma_enabled": bool(settings.FIGMA_TOKEN)` à `/health` (`routes.py:3466`) dans le même commit pour que la pastille dise vrai.

- [ ] **Step 4 : lancer, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 22 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 5 : appliquer, comparer, voir**

Run (racine) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Expected : `--diff` sort 0 ; seules `DzTestCle` et `dzChargerGuides` s'ajoutent. Puis, l'app relancée par l'utilisateur : Réglages → API keys montre dix lignes (dont Figma et Telegram), chacune avec un lien **Guide** et, si la clé est posée, un bouton **Tester** dont le verdict s'affiche sous le bouton ; enregistrer une clé dit maintenant « enregistree et appliquee » et le fournisseur répond sans redémarrage.

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py backend/app/api/routes.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : tester une cle depuis sa ligne, avec son guide' -m 'Cinq ancres neuves, toutes comptees a 1. Le libelle saved - restart the backend to apply apparaissait deux fois : on ancre sur les deux formes completes plutot que sur le fragment commun. Figma et Telegram entrent enfin dans le tableau des cles, et /health apprend figma_enabled pour que la pastille dise vrai.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 10 : Vérification de mise à jour — `releases/latest`, cache, téléchargement

**Files:**
- Create: `backend/app/services/mise_a_jour.py`
- Modify: `backend/app/api/settings_routes.py` (quatre routes)
- Modify: `backend/app/main.py` (une tâche de fond dans `lifespan`)
- Test: `backend/tests/test_mise_a_jour.py`

**Le dépôt est une CONSTANTE, et voici pourquoi.** Le tronc bâti par `scripts/build-installer.ps1` exclut `.git` (`robocopy … /XD … .git`) : l'application installée chez l'acheteur ne peut donc PAS lire `git config`. Le nom du dépôt s'obtient une fois, à l'écriture du module, par :

```bash
git config --get remote.origin.url
```

Attendu : `https://github.com/hugboss1/DeepotusVideo.git` → la constante vaut `"hugboss1/DeepotusVideo"`. Si la commande rend autre chose, c'est CETTE valeur qui va dans le module.

**Référence vérifiée le 03/09/2026** (appel réel) : `GET https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest` répond sans jeton — `tag_name: "v2.6.0"`, `name: "Deepotus Video Gen v2.6.0 — Bibliothèque unifiée"`, `published_at: "2026-08-28T14:55:00Z"`, `html_url`, `draft: false`, `prerelease: false`, et un asset `DeepotusVideoGen-Setup-2.6.0.exe` de **129 635 836 o**, `content_type: application/x-msdownload`, `browser_download_url` sur `github.com/hugboss1/DeepotusVideo/releases/download/v2.6.0/…`.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Vérification de mise à jour (plan Settings T10) — cache, cadence,
comparaison de versions, téléchargement gardé.

Banc-miroir : le cache est relu SUR LE DISQUE (maj.json) et le fichier
téléchargé est relu octet à octet. Réseau : zéro (le hook `_json` et le hook
`_flux` du module sont remplacés).
Run: python tests/test_mise_a_jour.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import mise_a_jour as M                          # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

REPONSE = {
    "tag_name": "v2.7.1", "name": "Deepotus Video Gen v2.7.1",
    "body": "- coffre a mot de passe maitre\n- plafonds de depense",
    "html_url": "https://github.com/hugboss1/DeepotusVideo/releases/tag/v2.7.1",
    "published_at": "2026-10-01T09:00:00Z", "draft": False, "prerelease": False,
    "assets": [
        {"name": "notes.txt", "size": 12, "content_type": "text/plain",
         "browser_download_url": "https://github.com/x/notes.txt"},
        {"name": "DeepotusVideoGen-Setup-2.7.1.exe", "size": 131000000,
         "content_type": "application/x-msdownload",
         "browser_download_url": "https://github.com/hugboss1/DeepotusVideo/"
                                 "releases/download/v2.7.1/DeepotusVideoGen-Setup-2.7.1.exe"},
    ],
}
APPELS = {"n": 0}
async def _faux_json(url, timeout=10.0):
    APPELS["n"] += 1
    check(url == "https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest",
          "URL exacte de l'API GitHub")
    return 200, REPONSE
M._json = _faux_json

def test_versions():
    check(M._tuple("v2.6.0") == (2, 6, 0), "le v initial est ignoré")
    check(M._tuple("2.7.1") > M._tuple("v2.6.0"), "2.7.1 > 2.6.0")
    check(M._tuple("v2.10.0") > M._tuple("v2.9.9"), "10 > 9, pas une comparaison de texte")
    check(M._tuple("2.6.0-rc1") == (2, 6, 0), "un suffixe ne casse pas la lecture")
    check(M._tuple("nimporte") == (0, 0, 0), "une balise illisible ne lève pas")

def test_verifier_et_cache():
    async def sc():
        r = await M.verifier()
        check(r["disponible"] is True, "2.7.1 > 2.6.0 : mise à jour disponible")
        check(r["tag"] == "v2.7.1" and r["installee"] == "2.6.0", "les deux versions sont dites")
        check(r["asset"]["nom"].endswith(".exe") and r["asset"]["octets"] == 131000000,
              "l'asset .exe est choisi, pas le premier venu")
        check("coffre" in r["notes"], "les notes de version sont là")
        cache = json.loads((_tmp / "maj.json").read_text(encoding="utf-8"))
        check(cache["tag"] == "v2.7.1", "cache écrit sur le disque")
        n = APPELS["n"]
        await M.verifier()
        check(APPELS["n"] == n, "moins de 24 h : aucun second appel réseau")
        await M.verifier(force=True)
        check(APPELS["n"] == n + 1, "force=True : on redemande")
    asyncio.run(sc())

def test_jamais_bloquant():
    async def sc():
        async def _casse(url, timeout=10.0):
            raise OSError("le reseau est coupe")
        M._json = _casse
        r = await M.verifier(force=True)
        check(r["tag"] == "v2.7.1", "réseau coupé : le cache disque répond quand même")
        check(r["erreur"].startswith("le reseau"), "et l'échec est dit, pas caché")
        (_tmp / "maj.json").unlink()
        r2 = await M.verifier(force=True)
        check(r2["disponible"] is False and r2["erreur"],
              "sans cache ni réseau : pas de mise à jour annoncée, l'erreur est dite")
        M._json = _faux_json
    asyncio.run(sc())

def test_telechargement_garde():
    async def sc():
        async def _faux_flux(url, cible, taille, etat):
            cible.write_bytes(b"MZ" + b"\0" * 30)
            etat.update(octets=32, total=32)
        M._flux = _faux_flux
        r = await M.telecharger("https://exemple.invalide/vilain.exe", "v.exe", 10)
        check(r["ok"] is False and "github.com" in r["erreur"],
              "une URL hors github.com est refusée en le disant")
        await M.verifier(force=True)
        r2 = await M.telecharger(REPONSE["assets"][1]["browser_download_url"],
                                 "DeepotusVideoGen-Setup-2.7.1.exe", 131000000)
        check(r2["ok"] is True, "URL GitHub : téléchargement lancé")
        f = pathlib.Path(r2["chemin"])
        check(f.is_file() and f.read_bytes()[:2] == b"MZ", "le fichier est sur le disque")
        check(f.parent.name == "telechargements" and f.parent.parent == _tmp,
              "rangé dans DATA_ROOT/telechargements, jamais lancé")
        check(M.etat_telechargement()["fini"] is True, "l'état de progression est lisible")
    asyncio.run(sc())

def test_preversion_ignoree():
    async def sc():
        avant = dict(REPONSE)
        REPONSE["prerelease"] = True
        (_tmp / "maj.json").unlink(missing_ok=True)
        r = await M.verifier(force=True)
        check(r["disponible"] is False and r["tag"] == "",
              "une preversion n'est pas une mise a jour proposee")
        REPONSE.clear(); REPONSE.update(avant)
    asyncio.run(sc())

test_versions(); test_verifier_et_cache(); test_jamais_bloquant()
test_telechargement_garde(); test_preversion_ignoree()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_mise_a_jour.py`
Expected : `ModuleNotFoundError: No module named 'app.services.mise_a_jour'`

- [ ] **Step 3 : écrire `mise_a_jour.py`**

```python
"""Vérification de mise à jour (plan Settings, P4).

Le dépôt est une CONSTANTE : le tronc bâti par `scripts/build-installer.ps1`
exclut `.git`, donc l'application installée ne peut pas lire `git config`.
La valeur vient de `git config --get remote.origin.url` lancé UNE FOIS, au
dépôt, le 03/09/2026.

Contrat vérifié le 03/09/2026 par un appel réel à
`GET https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest` :
`tag_name`, `name`, `body`, `html_url`, `published_at`, `draft`, `prerelease`
et `assets[].{name,size,content_type,browser_download_url}`. Le dépôt est
public : aucun jeton.

Trois règles, toutes tenues par le banc :
  * une fois par jour au plus (cache disque `maj.json`) ;
  * JAMAIS bloquant : réseau muet = on rend le cache, et l'on DIT l'échec ;
  * on télécharge, on ne lance rien — c'est l'utilisateur qui lance
    l'installeur, comme le README le décrit déjà.
"""
import json
import re
import time
from pathlib import Path

import httpx
from loguru import logger

from app.config import APP_VERSION, DATA_ROOT, SSL_VERIFY

DEPOT = "hugboss1/DeepotusVideo"
URL = f"https://api.github.com/repos/{DEPOT}/releases/latest"
CACHE = DATA_ROOT / "maj.json"
DOSSIER = DATA_ROOT / "telechargements"
CADENCE_S = 24 * 3600
HOTES_PERMIS = ("github.com", "objects.githubusercontent.com")

_ETAT = {"nom": "", "octets": 0, "total": 0, "fini": False, "erreur": "", "chemin": ""}


def _tuple(tag: str) -> tuple:
    """(2, 6, 0) depuis « v2.6.0 », « 2.6.0-rc1 »… ; (0, 0, 0) si illisible.
    On compare des NOMBRES : « v2.10.0 » est plus récent que « v2.9.9 », ce
    qu'une comparaison de texte dirait à l'envers."""
    bouts = re.findall(r"\d+", str(tag or ""))[:3]
    while len(bouts) < 3:
        bouts.append("0")
    try:
        return tuple(int(b) for b in bouts)
    except ValueError:
        return (0, 0, 0)


async def _json(url: str, timeout: float = 10.0):
    """Le seul point de sortie réseau de la vérification. Remplacé au banc."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout,
                                 follow_redirects=True) as c:
        r = await c.get(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"DeepotusVideoGen/{APP_VERSION}"})
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


def _lire_cache() -> dict:
    try:
        if CACHE.is_file():
            d = json.loads(CACHE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
    except (OSError, ValueError):
        pass
    return {}


def _asset(rel: dict) -> dict:
    """L'installeur, pas le premier asset venu : on cherche un .exe."""
    for a in rel.get("assets") or []:
        if str(a.get("name") or "").lower().endswith(".exe"):
            return {"nom": a.get("name"), "octets": int(a.get("size") or 0),
                    "url": a.get("browser_download_url")}
    return {}


async def verifier(force: bool = False) -> dict:
    cache = _lire_cache()
    frais = (not force and cache
             and (time.time() - float(cache.get("verifie_a") or 0)) < CADENCE_S)
    if frais:
        return cache
    erreur = ""
    try:
        code, rel = await _json(URL)
        if code == 200 and isinstance(rel, dict) and rel.get("tag_name"):
            if rel.get("draft") or rel.get("prerelease"):
                rel = {}                      # une préversion n'est pas une mise à jour
        else:
            erreur = f"GitHub a repondu {code}"
            rel = {}
    except Exception as e:  # noqa: BLE001 — jamais bloquant, c'est la règle
        erreur = str(e)[:200]
        rel = {}
    if not rel:
        logger.info(f"mise_a_jour: verification impossible ({erreur or 'reponse vide'})")
        if cache:
            cache = dict(cache); cache["erreur"] = erreur
            return cache
        return {"disponible": False, "installee": APP_VERSION, "tag": "",
                "nom": "", "notes": "", "url": "", "publie_le": "",
                "asset": {}, "verifie_a": time.time(), "erreur": erreur}
    tag = str(rel.get("tag_name") or "")
    out = {"disponible": _tuple(tag) > _tuple(APP_VERSION),
           "installee": APP_VERSION, "tag": tag,
           "nom": str(rel.get("name") or tag),
           "notes": str(rel.get("body") or "")[:4000],
           "url": str(rel.get("html_url") or ""),
           "publie_le": str(rel.get("published_at") or ""),
           "asset": _asset(rel), "verifie_a": time.time(), "erreur": ""}
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(CACHE)
    except OSError as e:
        logger.warning(f"mise_a_jour: cache non ecrit ({e})")
    return out


async def _flux(url: str, cible: Path, taille: int, etat: dict) -> None:
    """Le seul point de sortie réseau du téléchargement. Remplacé au banc."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=None,
                                 follow_redirects=True) as c:
        async with c.stream("GET", url) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or taille or 0)
            etat["total"] = total
            with cible.open("wb") as f:
                async for bloc in r.aiter_bytes(1 << 16):
                    f.write(bloc)
                    etat["octets"] += len(bloc)


def etat_telechargement() -> dict:
    return dict(_ETAT)


async def telecharger(url: str, nom: str, octets: int) -> dict:
    """Range l'installeur dans DATA_ROOT/telechargements et s'arrête là.

    On NE LANCE JAMAIS le fichier : le README dit déjà que l'utilisateur
    lance l'installeur, et un exécutable démarré par le backend serait une
    surface qu'aucun bouton ne justifie.
    """
    from urllib.parse import urlparse
    hote = (urlparse(url).hostname or "").lower()
    if not (hote in HOTES_PERMIS or hote.endswith(".github.com")):
        return {"ok": False, "erreur": f"telechargement refuse : {hote or '?'} "
                                       f"n'est pas github.com"}
    nom = re.sub(r"[^A-Za-z0-9._-]", "_", str(nom or "installeur.exe"))[:120]
    DOSSIER.mkdir(parents=True, exist_ok=True)
    cible = DOSSIER / nom
    partiel = DOSSIER / (nom + ".partiel")
    _ETAT.update(nom=nom, octets=0, total=int(octets or 0), fini=False,
                 erreur="", chemin="")
    try:
        await _flux(url, partiel, int(octets or 0), _ETAT)
        partiel.replace(cible)
    except Exception as e:  # noqa: BLE001
        _ETAT.update(fini=True, erreur=str(e)[:200])
        try:
            partiel.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": False, "erreur": _ETAT["erreur"]}
    _ETAT.update(fini=True, chemin=str(cible))
    logger.info(f"mise_a_jour: installeur telecharge -> {cible} "
                f"({cible.stat().st_size} o) — a lancer par l'utilisateur")
    return {"ok": True, "chemin": str(cible), "octets": cible.stat().st_size}
```

- [ ] **Step 4 : les quatre routes**

À ajouter à `backend/app/api/settings_routes.py` :

```python
@router.get("/maj")
async def lire_maj(request: Request):
    """L'état connu, sans jamais appeler GitHub : c'est le cache qui parle."""
    _local(request)
    from app.services import mise_a_jour as M
    return await M.verifier()


@router.post("/maj/verifier")
async def forcer_maj(request: Request):
    _local(request)
    from app.services import mise_a_jour as M
    return await M.verifier(force=True)


@router.post("/maj/telecharger")
async def telecharger_maj(request: Request):
    """Télécharge l'installeur de la dernière version dans
    DATA_ROOT/telechargements. Ne le lance pas : c'est l'utilisateur."""
    _local(request)
    from app.services import mise_a_jour as M
    etat = await M.verifier()
    a = etat.get("asset") or {}
    if not a.get("url"):
        raise HTTPException(404, "aucun installeur dans la derniere Release")
    return await M.telecharger(a["url"], a["nom"], a.get("octets") or 0)


@router.get("/maj/telechargement")
async def suivre_telechargement(request: Request):
    _local(request)
    from app.services import mise_a_jour as M
    return M.etat_telechargement()
```

- [ ] **Step 5 : la vérification quotidienne au démarrage**

Dans `backend/app/main.py`, `lifespan`, juste après `sched_task = asyncio.create_task(schedule_loop())` :

```python
    async def _maj_au_demarrage():
        """Une fois par lancement, 20 s après le boot (le temps que l'écran
        soit là), et au plus une fois par jour grâce au cache disque. Jamais
        bloquant : `mise_a_jour.verifier` avale ses propres échecs."""
        try:
            await asyncio.sleep(20)
            from app.services import mise_a_jour as _M
            r = await _M.verifier()
            if r.get("disponible"):
                logger.info(f"Mise a jour disponible : {r['tag']} "
                            f"(installee {r['installee']})")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning(f"verification de mise a jour ignoree: {e}")
    maj_task = asyncio.create_task(_maj_au_demarrage())
```

et dans le `finally`, à côté de `sched_task.cancel()` : `maj_task.cancel()`.

- [ ] **Step 6 : lancer, constater le vert**

Run : `python tests/test_mise_a_jour.py`
Expected : 25 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 7 : essai réel, une fois (le banc n'appelle jamais GitHub)**

Run (depuis `backend/`, avec le réseau) :
```
python -c "import asyncio,sys; sys.path.insert(0,'.'); from app.services import mise_a_jour as M; print(asyncio.run(M.verifier(force=True)))"
```
Expected au 03/09/2026 : `disponible: False`, `tag: 'v2.6.0'`, `installee: '2.6.0'`, `asset: {'nom': 'DeepotusVideoGen-Setup-2.6.0.exe', 'octets': 129635836, …}`. Un `erreur` non vide ici veut dire que l'API a changé ou que le réseau filtre : le corriger AVANT T11, sinon le bandeau s'appuierait sur du vide.

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/mise_a_jour.py backend/app/api/settings_routes.py backend/app/main.py backend/tests/test_mise_a_jour.py
git commit -m 'reglages : verification de mise a jour par releases-latest, cache et telechargement garde' -m 'Le depot est une constante parce que le tronc bati exclut .git : lapp installee ne peut pas lire git config. Une fois par jour, jamais bloquant (reseau muet = le cache repond et lechec est dit), comparaison de versions par nombres (v2.10.0 > v2.9.9), telechargement refuse hors github.com, et rien nest jamais lance : cest lutilisateur qui lance linstalleur.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 11 : Le bandeau de mise à jour et le bloc version (section S6)

**Files:**
- Modify: `scripts/patch_bundle_reglages.py` (section S6)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur)
- Test: `backend/tests/test_patch_reglages.py` (assertions ajoutées)

**Coût de patch** : S6 n'ouvre **aucune ancre React neuve**. Le bandeau est une IIFE en DOM pur (comme la barre de confirmation de S4) et le bloc « version » est ajouté à `DzDiag`, qui appartient déjà au bloc S1. Coût : une constante de plus dans le patcheur.

- [ ] **Step 1 : ajouter les assertions au banc (rouge)**

Insérer dans `backend/tests/test_patch_reglages.py`, avant `b = cible.read_bytes()` :

```python
    check(s.count("__dzMajBandeau") == 1, "le bandeau est posé une seule fois")
    check(s.count("/api/reglages/maj") >= 1, "le bandeau interroge la route du cache")
    check("dz_maj_vu_" in s, "le rejet du bandeau est mémorisé par balise de version")
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : trois `FAIL`, `3 échec(s)`.

- [ ] **Step 3 : la section S6 du patcheur**

```python
# ── S6 : bandeau de mise a jour (DOM pur, aucune ancre React) ──────────────

S6 = (
    "(function(){if(window.__dzMajBandeau)return;window.__dzMajBandeau=1;"
    "function pose(m){"
    "if(localStorage.getItem('dz_maj_vu_'+m.tag))return;"
    "var w=document.createElement('div');"
    "w.style.cssText='position:fixed;left:0;right:0;top:0;z-index:99998;"
    "display:flex;gap:14px;align-items:center;padding:9px 16px;"
    "background:var(--bg-panel-2);border-bottom:1px solid var(--stroke);"
    "font-size:12.5px;color:var(--ink);font-family:inherit';"
    "var t=document.createElement('div');t.style.cssText='flex:1;line-height:1.4';"
    "t.textContent='Version '+m.tag+' disponible (vous avez la '+m.installee"
    "+'). '+(m.asset&&m.asset.nom?('Installeur : '+m.asset.nom+' - '"
    "+Math.round((m.asset.octets||0)/1048576)+' Mo.'):'');"
    "var notes=document.createElement('a');notes.textContent='Notes de version';"
    "notes.href=m.url||'#';notes.target='_blank';notes.rel='noreferrer';"
    "notes.style.cssText='color:var(--cyan);text-decoration:none';"
    "var dl=document.createElement('button');dl.textContent='Telecharger';"
    "var no=document.createElement('button');no.textContent='Plus tard';"
    "[dl,no].forEach(function(b){b.style.cssText='height:26px;padding:0 12px;"
    "border-radius:8px;border:1px solid var(--stroke);cursor:pointer;"
    "font-size:12px;background:var(--bg-panel);color:var(--ink)'});"
    "dl.style.background='var(--brand)';dl.style.color='#04121a';"
    "no.onclick=function(){localStorage.setItem('dz_maj_vu_'+m.tag,'1');w.remove()};"
    "dl.onclick=function(){dl.disabled=!0;dl.textContent='Telechargement...';"
    "fetch('/api/reglages/maj/telecharger',{method:'POST'})"
    ".then(R=>R.json()).then(function(j){"
    "t.textContent=j.ok?('Installeur enregistre : '+j.chemin"
    "+' - fermez l app et lancez-le.'):('Echec : '+(j.erreur||'inconnu'));"
    "dl.remove()}).catch(function(e){t.textContent='Echec : '+e;dl.disabled=!1});"
    "var tic=setInterval(function(){"
    "fetch('/api/reglages/maj/telechargement').then(R=>R.json()).then(function(p){"
    "if(p.fini){clearInterval(tic);return}"
    "if(p.total)dl.textContent='Telechargement '"
    "+Math.round(100*p.octets/p.total)+'%'})"
    ".catch(function(){clearInterval(tic)})},1200)};"
    "w.appendChild(t);w.appendChild(notes);w.appendChild(dl);w.appendChild(no);"
    "document.body.appendChild(w)}"
    "setTimeout(function(){fetch('/api/reglages/maj').then(R=>R.json())"
    ".then(function(m){if(m&&m.disponible&&m.tag)pose(m)})"
    ".catch(function(){})},2500)})();"
)
```

Le bloc « version » dans `DzDiag` : dans la constante `S1`, remplacer

```python
    "r.jsx(te,{tone:'cyan',children:'v'+d.version}),"
```

par

```python
    "r.jsx(te,{tone:'cyan',children:'v'+d.version}),"
    "r.jsx(DzMaj,{}),"
```

et ajouter à `S6` le petit composant qui va avec :

```python
S6 = S6 + (
    "function DzMaj(){const[m,setM]=x.useState(null),[b,setB]=x.useState(!1);"
    "x.useEffect(()=>{fetch('/api/reglages/maj').then(R=>R.json()).then(setM)"
    ".catch(()=>{})},[]);if(!m)return null;"
    "const revoir=()=>{setB(!0);fetch('/api/reglages/maj/verifier',{method:'POST'})"
    ".then(R=>R.json()).then(j=>{setM(j);setB(!1)}).catch(()=>setB(!1))};"
    "return r.jsxs('div',{style:{display:'flex',gap:8,alignItems:'center'},children:["
    "m.disponible?r.jsx(te,{tone:'amber',dot:!0,children:m.tag+' disponible'})"
    ":r.jsx(te,{tone:'green',dot:!0,children:m.erreur?'verification impossible':'a jour'}),"
    "r.jsx(K,{variant:'ghost',size:'sm',onClick:revoir,disabled:b,"
    "children:b?'...':'Verifier'}),"
    "m.url?r.jsx('a',{href:m.url,target:'_blank',rel:'noreferrer',"
    "style:{fontSize:11,color:'var(--cyan)',textDecoration:'none'},"
    "children:'Notes'}):null]})}"
)
```

Enfin, brancher `S6` dans le bloc injecté :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + S6 + "function DzPricing(){", "S1-bloc")
```

> Ordre : `S6` contient `DzMaj`, utilisé par `DzDiag` (dans `S1`). C'est une **déclaration de fonction**, donc hissée dans la portée du module : l'ordre d'écriture n'a pas d'importance, seul le fait d'être dans la même portée compte (le banc du Step 4 le prouve en montant l'écran, pas en lisant le code).

- [ ] **Step 4 : lancer, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 25 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 5 : appliquer, comparer, voir**

Run (racine) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Expected : `--diff` sort 0, ajouts `DzMaj` et `pose`. Puis, l'app relancée par l'utilisateur : Réglages → Diagnostic affiche `v2.6.0` + la pastille verte « a jour » + un bouton « Verifier ». Pour VOIR le bandeau sans attendre une release, éditer `%LOCALAPPDATA%\DeepotusVideoGenData\maj.json` et y mettre `"tag": "v9.9.9"`, `"disponible": true`, puis recharger la page : le bandeau doit apparaître en haut, « Plus tard » doit le faire disparaître définitivement pour cette balise, et « Telecharger » doit afficher un pourcentage puis le chemin du fichier. **Remettre `maj.json` en état** ensuite (ou le supprimer : il se reconstruit).

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : bandeau de mise a jour et bloc version dans le diagnostic' -m 'Le bandeau est du DOM pur : aucune ancre React neuve, donc aucun cout de patch au-dela dune constante. Le rejet est memorise par balise de version — refuser 2.7.1 ne masque pas 2.8.0. Le telechargement affiche son pourcentage et rend un chemin ; lapplication ne lance jamais linstalleur.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 12 : Export manuel des données — copie, manifeste, vérification d'intégrité

**Files:**
- Create: `backend/app/services/export_donnees.py`
- Modify: `backend/app/api/settings_routes.py` (quatre routes)
- Test: `backend/tests/test_export_donnees.py`

**Ce que la mesure impose.** `DATA_ROOT` pèse **14 855 500 770 o** répartis sur **9 911 fichiers** (mesuré le 03/09), dont **6 515 793 339 o** dans le seul `rebut_decks_2026-08-26` : presque la moitié du volume est un rebut daté. L'export propose donc des **lots cochables**, avec `rebuts` décoché par défaut — sans quoi chaque export doublerait sa durée pour recopier une corbeille. Le hachage n'est pas le goulot (`sha256` mesuré à **1 737 Mio/s** sur cette machine : ~5 s de CPU pour 8,3 Gio) ; le disque de destination l'est, d'où la progression par fichier.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Export manuel des données (plan Settings T12) — copie, manifeste, intégrité.

Banc-miroir : il relit les FICHIERS écrits dans le dossier de destination et
le manifeste sur le disque ; il ne se fie jamais à la valeur de retour seule.
Run: python tests/test_export_donnees.py   (depuis backend/)"""
import asyncio, hashlib, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import export_donnees as E                       # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

# un DATA_ROOT jouet, avec un rebut volumineux et un fichier volatil
(_tmp / "assets" / "images").mkdir(parents=True)
(_tmp / "assets" / "images" / "a.png").write_bytes(b"A" * 4096)
(_tmp / "assets" / "images" / "b.png").write_bytes(b"B" * 100)
(_tmp / "logs").mkdir(); (_tmp / "logs" / "j.log").write_bytes(b"L" * 10)
(_tmp / "rebut_decks_2026-08-26").mkdir()
(_tmp / "rebut_decks_2026-08-26" / "gros.bin").write_bytes(b"R" * 50000)
(_tmp / "deepotus.db").write_bytes(b"SQLite format 3\x00")
(_tmp / "deepotus.db-wal").write_bytes(b"WAL")
(_tmp / ".env").write_text("FAL_KEY=secret-a-ne-pas-copier\n", encoding="utf-8")

DEST = pathlib.Path(tempfile.mkdtemp())

def test_export():
    async def sc():
        r = await E.exporter(DEST, {"base": True, "assets": True, "logs": True,
                                    "rebuts": False, "cles": False})
        check(r["ok"] is True, f"export réussi ({r.get('erreur','')})")
        d = pathlib.Path(r["dossier"])
        check(d.parent == DEST and d.name.startswith("DeepotusVideoGen-export-"),
              "un sous-dossier daté dans la destination choisie")
        check((d / "assets" / "images" / "a.png").read_bytes() == b"A" * 4096,
              "le contenu est identique octet pour octet")
        check(not (d / "rebut_decks_2026-08-26").exists(),
              "rebuts décochés : 50 000 o non recopiés")
        check(not (d / ".env").exists(),
              "le .env n'est JAMAIS dans un export non chiffré (les clés, c'est le coffre)")
        check((d / "deepotus.db").is_file(), "la base est copiée")
        m = json.loads((d / "manifeste.json").read_text(encoding="utf-8"))
        check(m["total_octets"] == 4096 + 100 + 10 + 16 + 3,
              f"le manifeste totalise ce qui a été copié (lu {m['total_octets']})")
        check(len(m["fichiers"]) == 5, f"5 fichiers listés (lu {len(m['fichiers'])})")
        att = hashlib.sha256(b"A" * 4096).hexdigest()
        lig = [f for f in m["fichiers"] if f["rel"].endswith("a.png")][0]
        check(lig["sha256"] == att, "sha256 par fichier, calculé sur ce qui a été écrit")
        check(m["app_version"] == "2.6.0" and m["racine"] == str(_tmp),
              "le manifeste dit la version et la racine d'origine")
        check(E.etat()["fini"] is True and E.etat()["faits"] == 5,
              "la progression est lisible et complète")

        bilan = await E.verifier_dossier(d)
        check(bilan["ok"] is True and bilan["verifies"] == 5, "intégrité : 5/5")
        (d / "assets" / "images" / "b.png").write_bytes(b"C" * 100)
        bilan2 = await E.verifier_dossier(d)
        check(bilan2["ok"] is False and len(bilan2["divergents"]) == 1
              and bilan2["divergents"][0].endswith("b.png"),
              "un octet changé est vu et NOMMÉ")
        (d / "assets" / "images" / "a.png").unlink()
        bilan3 = await E.verifier_dossier(d)
        check(len(bilan3["manquants"]) == 1, "un fichier disparu est vu et nommé")
    asyncio.run(sc())

def test_gardes():
    async def sc():
        r = await E.exporter(_tmp / "assets" / "dedans", {"assets": True})
        check(r["ok"] is False and "dans le dossier de donnees" in r["erreur"],
              "une destination SOUS DATA_ROOT est refusée (copie sans fin)")
        r2 = await E.exporter(pathlib.Path("relatif"), {"assets": True})
        check(r2["ok"] is False and "absolu" in r2["erreur"],
              "un chemin relatif est refusé en le disant")
        r3 = await E.exporter(DEST, {})
        check(r3["ok"] is False and "rien" in r3["erreur"].lower(),
              "aucun lot coché : refus parlant, pas un dossier vide")
    asyncio.run(sc())

test_export(); test_gardes()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_export_donnees.py`
Expected : `ModuleNotFoundError: No module named 'app.services.export_donnees'`

- [ ] **Step 3 : écrire `export_donnees.py`**

```python
"""Export manuel des données (plan Settings, P5).

Réponse 6 du balayage : export MANUEL vers un dossier choisi, jamais une
sauvegarde programmée (E2). Ce que la mesure du 03/09/2026 impose :
`DATA_ROOT` = 14 855 500 770 o sur 9 911 fichiers, dont 6 515 793 339 o dans
le seul `rebut_decks_2026-08-26`. D'où des LOTS cochables, `rebuts` décoché
par défaut. `sha256` tourne à 1 737 Mio/s ici : le disque de destination est
le goulot, pas le hachage — la progression compte donc des FICHIERS.

Le `.env` n'entre JAMAIS dans cet export : un dossier en clair sur une clé
USB n'est pas l'endroit d'une clé d'API. Les clés voyagent par l'archive
chiffrée du coffre (D1, T16), qui a un mot de passe.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

from loguru import logger

from app.config import APP_VERSION, DATA_ROOT

BLOC = 1 << 20

# nom du lot -> chemins relatifs sous DATA_ROOT
LOTS = {
    "base": ["deepotus.db", "deepotus.db-wal", "deepotus.db-shm", "pricing.json",
             "plafonds.json"],
    "assets": ["assets", "cardforge_models", "cardforge_series"],
    "logs": ["logs"],
    "rebuts": ["__rebuts__"],          # développé plus bas : tous les rebut_*
}

_ETAT = {"total": 0, "faits": 0, "octets": 0, "octets_total": 0,
         "fichier": "", "fini": True, "erreur": "", "dossier": ""}


def etat() -> dict:
    return dict(_ETAT)


def _sha_et_copie(src: Path, dst: Path) -> tuple[str, int]:
    """Copie ET hache en UNE lecture : le sha256 porte donc sur ce qui a
    réellement été écrit, pas sur ce qu'on croyait lire."""
    h = hashlib.sha256()
    n = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as fi, dst.open("wb") as fo:
        while True:
            b = fi.read(BLOC)
            if not b:
                break
            h.update(b)
            fo.write(b)
            n += len(b)
    shutil.copystat(src, dst, follow_symlinks=False)
    return h.hexdigest(), n


def _sources(quoi: dict) -> list[Path]:
    out: list[Path] = []
    for lot, rels in LOTS.items():
        if not quoi.get(lot):
            continue
        for rel in rels:
            if rel == "__rebuts__":
                out += sorted(p for p in DATA_ROOT.glob("rebut_*") if p.exists())
            else:
                p = DATA_ROOT / rel
                if p.exists():
                    out.append(p)
    return out


def _fichiers(racines: list[Path]) -> list[Path]:
    out: list[Path] = []
    for r in racines:
        if r.is_file():
            out.append(r)
        elif r.is_dir():
            out += [p for p in r.rglob("*") if p.is_file()]
    # le .env n'est jamais exporté en clair : les clés passent par le coffre
    return [p for p in out if p.name != ".env"]


async def exporter(destination: Path, quoi: dict) -> dict:
    destination = Path(destination)
    if not destination.is_absolute():
        return {"ok": False, "erreur": "le dossier de destination doit etre un "
                                       "chemin absolu"}
    try:
        if destination.resolve() == DATA_ROOT.resolve() \
                or DATA_ROOT.resolve() in destination.resolve().parents:
            return {"ok": False, "erreur": "destination refusee : elle est dans "
                                           "le dossier de donnees (copie sans fin)"}
    except OSError as e:
        return {"ok": False, "erreur": f"destination illisible : {e}"}

    racines = _sources(quoi or {})
    if not racines:
        return {"ok": False, "erreur": "rien a exporter : aucun lot coche"}
    fichiers = _fichiers(racines)
    octets_total = sum(p.stat().st_size for p in fichiers if p.exists())

    try:
        libre = shutil.disk_usage(destination.parent if not destination.exists()
                                  else destination).free
    except OSError:
        libre = None
    if libre is not None and libre < octets_total * 1.05:
        return {"ok": False,
                "erreur": f"place insuffisante : {octets_total} o a copier, "
                          f"{libre} o libres a destination"}

    dossier = destination / ("DeepotusVideoGen-export-"
                             + time.strftime("%Y-%m-%d-%H%M%S"))
    dossier.mkdir(parents=True, exist_ok=True)
    _ETAT.update(total=len(fichiers), faits=0, octets=0, octets_total=octets_total,
                 fichier="", fini=False, erreur="", dossier=str(dossier))

    manifeste = {"cree_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "app_version": APP_VERSION, "racine": str(DATA_ROOT),
                 "lots": {k: bool(quoi.get(k)) for k in LOTS},
                 "fichiers": [], "total_octets": 0}
    try:
        for p in fichiers:
            rel = p.relative_to(DATA_ROOT).as_posix()
            _ETAT["fichier"] = rel
            sha, n = _sha_et_copie(p, dossier / rel)
            manifeste["fichiers"].append({"rel": rel, "octets": n, "sha256": sha})
            manifeste["total_octets"] += n
            _ETAT["faits"] += 1
            _ETAT["octets"] += n
        (dossier / "manifeste.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        _ETAT.update(fini=True, erreur=str(e)[:200])
        logger.warning(f"export interrompu : {e}")
        return {"ok": False, "erreur": _ETAT["erreur"], "dossier": str(dossier)}
    _ETAT["fini"] = True
    logger.info(f"export termine : {len(fichiers)} fichiers, "
                f"{manifeste['total_octets']} o -> {dossier}")
    return {"ok": True, "dossier": str(dossier), "fichiers": len(fichiers),
            "octets": manifeste["total_octets"]}


async def verifier_dossier(dossier: Path) -> dict:
    """Relit le manifeste et re-hache CHAQUE fichier du dossier exporté.

    C'est la seule preuve qui vaille : un export dont on n'a pas relu les
    octets n'est pas une sauvegarde, c'est un espoir.
    """
    dossier = Path(dossier)
    m_path = dossier / "manifeste.json"
    if not m_path.is_file():
        return {"ok": False, "erreur": "manifeste.json introuvable"}
    m = json.loads(m_path.read_text(encoding="utf-8"))
    manquants, divergents, verifies = [], [], 0
    for f in m.get("fichiers", []):
        p = dossier / f["rel"]
        if not p.is_file():
            manquants.append(f["rel"])
            continue
        h = hashlib.sha256()
        with p.open("rb") as fi:
            while True:
                b = fi.read(BLOC)
                if not b:
                    break
                h.update(b)
        if h.hexdigest() != f["sha256"]:
            divergents.append(f["rel"])
        else:
            verifies += 1
    return {"ok": not manquants and not divergents, "verifies": verifies,
            "manquants": manquants, "divergents": divergents,
            "attendus": len(m.get("fichiers", []))}
```

- [ ] **Step 4 : les trois routes**

À ajouter à `backend/app/api/settings_routes.py`. Il n'y a **pas** de route « poids par lot » : le poids par catégorie est déjà servi par `/diagnostic` (T2), et un second producteur du même chiffre finirait par mentir sur l'un des deux écrans.

```python
@router.post("/export")
async def lancer_export(body: dict, request: Request, background_tasks: BackgroundTasks):
    """Lance l'export en tâche de fond ; suivre par GET /export/etat."""
    _local(request)
    from pathlib import Path as _P
    from app.services import export_donnees as E
    dest = str((body or {}).get("destination") or "").strip()
    if not dest:
        raise HTTPException(400, "destination manquante")
    quoi = {k: bool((body or {}).get(k)) for k in E.LOTS}
    if E.etat()["fini"] is False:
        raise HTTPException(409, "un export est deja en cours")
    background_tasks.add_task(E.exporter, _P(dest), quoi)
    return {"ok": True, "demarre": True}


@router.get("/export/etat")
async def etat_export(request: Request):
    _local(request)
    from app.services import export_donnees as E
    return E.etat()


@router.post("/export/verifier")
async def verifier_export(body: dict, request: Request):
    _local(request)
    from pathlib import Path as _P
    from app.services import export_donnees as E
    d = str((body or {}).get("dossier") or "").strip()
    if not d:
        raise HTTPException(400, "dossier manquant")
    return await E.verifier_dossier(_P(d))
```

Ajouter `BackgroundTasks` à l'import FastAPI en tête de `settings_routes.py` :
`from fastapi import APIRouter, BackgroundTasks, HTTPException, Request`.

> `lancer_export` rend la main tout de suite : une copie de 8,3 Gio ne tient pas dans une requête HTTP. Le refus 409 empêche deux exports simultanés d'écrire dans le même `_ETAT`.

- [ ] **Step 5 : lancer, constater le vert**

Run : `python tests/test_export_donnees.py`
Expected : 17 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/export_donnees.py backend/app/api/settings_routes.py backend/tests/test_export_donnees.py
git commit -m 'reglages : export manuel avec manifeste et verification dintegrite' -m 'Lots cochables parce que la mesure du 03/09 dit que 6,5 Gio sur 13,8 sont un rebut date : recopier une corbeille a chaque export serait absurde. Le sha256 est calcule PENDANT la copie, donc il porte sur ce qui a ete ecrit ; verifier_dossier re-hache tout, parce quun export dont on na pas relu les octets nest pas une sauvegarde mais un espoir. Le .env nentre jamais dans un export en clair : les cles passent par le coffre.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 13 : L'écran d'export (section S7)

**Files:**
- Modify: `scripts/patch_bundle_reglages.py` (section S7)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur)
- Test: `backend/tests/test_patch_reglages.py` (assertions ajoutées)

**Coût de patch** : S7 ajoute `DzExport` au bloc S1 et **réutilise les trois ancres déjà consommées** par S2a / S2b / S3 — le patcheur les remplace en un seul passage, donc il suffit d'allonger les chaînes de remplacement. Zéro ancre neuve.

- [ ] **Step 1 : ajouter les assertions au banc (rouge)**

```python
    check("function DzExport(" in s, "DzExport injecté")
    check(s.count('{k:"export",l:"Sauvegarde"}') == 1, "une entrée de barre « Sauvegarde »")
    check(s.count('s==="export"&&r.jsx(DzExport,{})') == 1, "une branche de corps")
    check('"export"' in s.split('const ym=[')[1][:120], "section ajoutée à la liste blanche")
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : quatre `FAIL`, `4 échec(s)`.

- [ ] **Step 3 : la section S7**

```python
# ── S7 : ecran d'export manuel ─────────────────────────────────────────────

S7 = (
    "function DzExport(){"
    "const[dest,setDest]=x.useState('');"
    "const[q,setQ]=x.useState({base:!0,assets:!0,logs:!0,rebuts:!1});"
    "const[p,setP]=x.useState(null),[msg,setMsg]=x.useState('');"
    "const[bil,setBil]=x.useState(null);"
    "const tic=x.useRef(null);"
    "const suivre=()=>{if(tic.current)clearInterval(tic.current);"
    "tic.current=setInterval(()=>{fetch('/api/reglages/export/etat')"
    ".then(R=>R.json()).then(e=>{setP(e);if(e.fini){clearInterval(tic.current);"
    "tic.current=null;setMsg(e.erreur?('Echec : '+e.erreur)"
    ":('Termine : '+e.faits+' fichiers dans '+e.dossier))}})"
    ".catch(()=>{clearInterval(tic.current);tic.current=null})},700)};"
    "x.useEffect(()=>()=>{if(tic.current)clearInterval(tic.current)},[]);"
    "const lancer=()=>{setMsg('');setBil(null);"
    "fetch('/api/reglages/export',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify(Object.assign({destination:dest},q))})"
    ".then(R=>R.json().then(j=>({s:R.status,j:j})))"
    ".then(o=>{if(o.s!==200){setMsg('Refus : '+(o.j.detail||o.s));return}suivre()})"
    ".catch(e=>setMsg('Echec : '+e))};"
    "const controler=()=>{fetch('/api/reglages/export/verifier',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({dossier:(p&&p.dossier)||''})})"
    ".then(R=>R.json()).then(setBil).catch(e=>setMsg('Echec : '+e))};"
    "const case_=(k,l)=>r.jsxs('label',{style:{display:'flex',gap:7,"
    "alignItems:'center',fontSize:12.5,cursor:'pointer'},children:["
    "r.jsx('input',{type:'checkbox',checked:!!q[k],"
    "onChange:ev=>setQ(Object.assign({},q,{[k]:ev.target.checked}))}),l]},k);"
    "return r.jsxs(r.Fragment,{children:["
    "r.jsx('div',{className:'display',style:{fontSize:22,"
    "color:'var(--ink-strong)',marginBottom:4},children:'Sauvegarde'}),"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)',marginBottom:18},"
    "children:'Copie a la demande de vos donnees vers un dossier de votre choix, "
    "avec un manifeste et une empreinte sha256 par fichier. Vos CLES ne sont pas "
    "dans cet export : elles passent par larchive chiffree du coffre.'}),"
    "r.jsxs(jt,{style:{padding:16},children:["
    "r.jsxs('div',{style:{display:'grid',gridTemplateColumns:'150px 1fr',"
    "gap:12,alignItems:'center',marginBottom:14},children:["
    "r.jsx('div',{style:{fontSize:12.5},children:'Dossier de destination'}),"
    "r.jsx('input',{type:'text',value:dest,onChange:e=>setDest(e.target.value),"
    "placeholder:'D:\\\\sauvegardes\\\\deepotus',"
    "style:{background:'var(--bg-base)',border:'1px solid var(--stroke)',"
    "borderRadius:'var(--r-sm)',padding:'6px 10px',color:'var(--ink-strong)',"
    "fontFamily:'var(--f-mono)',fontSize:12}})]}),"
    "r.jsxs('div',{style:{display:'flex',gap:18,flexWrap:'wrap',marginBottom:14},"
    "children:[case_('base','Base de donnees et reglages'),"
    "case_('assets','Images, rendus, audio, 3D'),case_('logs','Journal'),"
    "case_('rebuts','Rebuts (corbeilles datees - volumineux)')]}),"
    "r.jsxs('div',{style:{display:'flex',gap:10,alignItems:'center'},children:["
    "r.jsx(K,{variant:'primary',size:'md',icon:'check',glow:!0,onClick:lancer,"
    "disabled:!dest||!!(p&&!p.fini),children:'Exporter'}),"
    "p&&p.fini&&p.dossier?r.jsx(K,{variant:'ghost',size:'md',onClick:controler,"
    "children:'Verifier lintegrite'}):null,"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)'},children:msg})]}),"
    "p&&!p.fini?r.jsxs('div',{style:{marginTop:14},children:["
    "r.jsx('div',{style:{height:6,background:'var(--bg-panel-2)',borderRadius:3},"
    "children:r.jsx('div',{style:{height:6,borderRadius:3,"
    "background:'var(--brand)',width:(p.total?Math.round(100*p.faits/p.total):0)"
    "+'%'}})}),"
    "r.jsxs('div',{className:'mono',style:{fontSize:11,marginTop:6,"
    "color:'var(--ink-muted)'},children:[p.faits,' / ',p.total,' fichiers - ',"
    "dzOct(p.octets),' / ',dzOct(p.octets_total),' - ',p.fichier]})]}):null,"
    "bil?r.jsx('div',{style:{marginTop:14,fontSize:12,"
    "color:bil.ok?'var(--green)':'var(--red)'},"
    "children:bil.ok?('Integrite verifiee : '+bil.verifies+' fichiers relus, "
    "empreintes identiques.'):('Divergences : '+(bil.divergents||[]).join(', ')"
    "+' ; manquants : '+(bil.manquants||[]).join(', '))}):null]})]})}"
)
```

Puis, dans `patcher()`, allonger les trois remplacements déjà écrits :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + S6 + S7 + "function DzPricing(){", "S1-bloc")
    s = apply(s, '[{k:"keys",l:"API keys"},',
              '[{k:"diag",l:"Diagnostic"},{k:"keys",l:"API keys"},'
              '{k:"export",l:"Sauvegarde"},', "S2a-barre")
    s = apply(s, 'const ym=["keys",', 'const ym=["diag","export","keys",',
              "S2b-liste-blanche")
    s = apply(s, 's==="pricing"&&r.jsx(DzPricing,{})]})',
              's==="pricing"&&r.jsxs(r.Fragment,{children:[r.jsx(DzPricing,{}),'
              'r.jsx(DzPlafonds,{})]}),s==="diag"&&r.jsx(DzDiag,{}),'
              's==="export"&&r.jsx(DzExport,{})]})', "S3-corps")
```

- [ ] **Step 4 : lancer, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 29 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 5 : appliquer, comparer, essayer pour de vrai**

Run (racine) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Puis, l'app relancée par l'utilisateur : Réglages → **Sauvegarde**, destination `%USERPROFILE%\Desktop\dz-test`, décocher « Images… » pour un premier essai court, **Exporter** → la barre avance, le message final donne le dossier ; **Verifier lintegrite** doit dire « empreintes identiques ». Refaire une fois avec « Images… » coché pour mesurer la durée réelle sur les 8,3 Gio hors rebuts, et **noter cette durée ici** :

| Lots | Fichiers | Octets | Durée observée | Date |
|---|---|---|---|---|
| base + journal | | | | |
| base + journal + assets | | ~8,3 Gio | | |

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : ecran de sauvegarde, progression et verification dintegrite' -m 'Zero ancre neuve : les trois ancres de S2 et S3 sont deja consommees, il suffit dallonger les remplacements. La case rebuts est decochee par defaut parce que la mesure dit quelle pese 6,5 Gio sur 13,8.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

### Task 14 : Trancher le coffre — mesure, table de décision, roue embarquée

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `scripts/build-installer.ps1` (garde après l'étape 3, l. ~155)
- Test: `backend/tests/test_coffre_socle.py`

#### La décision, avec ses trois mesures (03/09/2026)

La contrainte de départ, rappelée par le balayage : le Python embarqué est **stdlib pure** (numpy absent, mesuré le 27/08) et **la stdlib n'a pas d'AES**. Trois voies, toutes trois mesurées sous le VRAI runtime (`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`, 3.13.15), pas sous le python de développement :

| Voie | Poids ajouté | Mot de passe maître | Archive lisible par le téléphone (R12 P2) | Chiffrement revu par des tiers | Ce qui a été mesuré |
|---|---|---|---|---|---|
| **(a) DPAPI par `ctypes`** | **0 o** — `_ctypes.pyd` et `libffi-8.dll` sont déjà dans le runtime embarqué | **non** : la protection est liée au compte Windows, il n'y a aucun secret à saisir | **non**, par construction : un blob DPAPI est illisible sur un autre PC, a fortiori sur un iPhone | oui (Microsoft) | `CryptProtectData` sur 19 o rend **246 o** ; `CryptUnprotectData` rend l'original ; une entropie différente échoue |
| **(b) roue `cryptography` embarquée au build** | **+4 076 686 o** de roues (`cryptography-50.0.1-cp311-abi3-win_amd64` 3 842 826 + `cffi-2.1.1-cp313` 185 688 + `pycparser-3.0` 48 172), **+11 389 540 o** une fois installées, sur un installeur de **129 635 836 o** — ≈ **+3 %** après compression LZMA, à confirmer au premier build | **oui** (PBKDF2 → AES-256-GCM) | **oui** : AES-256-GCM se lit avec CommonCrypto (iOS) et `javax.crypto` (Android) sans rien réimplémenter | oui, largement | `AESGCM` **importé et aller-retour effectué, AAD comprise**, sous le runtime embarqué ; `PYTHONPATH` est ignoré par le `._pth` de l'embeddable, c'est `sys.path.insert` qui marche |
| **(c) flux stdlib : PBKDF2 + HMAC-SHA256 en compteur** | **0 o** | oui | oui, mais dans un format **maison** que l'app du téléphone devrait réimplémenter à l'identique | **non** : un mode de chiffrement écrit à la main, jamais revu | seule la KDF est mesurée (`pbkdf2_hmac` 600 000 = 0,42 s ; `scrypt` n=2¹⁵ = 0,14 s) — le mode resterait à écrire ET à prouver |

**Verdict : (b)**, et (a) en **protection au repos de la clé dérivée** (« retenir sur ce PC » : la clé de 32 o est scellée par DPAPI, donc le coffre s'ouvre seul sur cette session Windows et nulle part ailleurs). **(c) est écarté** : réimplémenter un mode de chiffrement pour économiser 4 Mo sur un installeur de 130 Mo est un mauvais échange, et la réponse R12-5 exige que le TÉLÉPHONE lise l'archive — un format maison lui ferait porter la même dette.

**KDF retenue : PBKDF2-HMAC-SHA256, 600 000 itérations** (0,42 s mesurées), et non `scrypt` pourtant trois fois plus rapide ici : PBKDF2-HMAC-SHA256 est dans CommonCrypto et `javax.crypto` en standard, `scrypt` non. 0,28 s de gagnées ne valent pas une dépendance de plus à porter sur deux plateformes mobiles.

- [ ] **Step 1 : refaire les trois mesures (elles datent, elles peuvent avoir bougé)**

Run (depuis la racine, avec le réseau) :
```
python -m pip download --only-binary=:all: --python-version 3.13 --platform win_amd64 --dest .cache\roues "cryptography>=46"
dir .cache\roues
```
Expected (03/09/2026) : trois roues — `cryptography-50.0.1-cp311-abi3-win_amd64.whl` (3 842 826 o), `cffi-2.1.1-cp313-cp313-win_amd64.whl` (185 688 o), `pycparser-3.0-py3-none-any.whl` (48 172 o). Une version plus récente est acceptable ; une roue **non-abi3** ou absente pour cp313 ne l'est pas — dans ce cas, revenir au tableau ci-dessus et retrancher.

- [ ] **Step 2 : prouver que ça tourne SOUS LE RUNTIME EMBARQUÉ, pas sous le python de dev**

Run :
```
python -m pip install --quiet --no-warn-script-location --target .cache\sp .cache\roues\*.whl
"%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe" -c "import sys, os; sys.path.insert(0, os.path.abspath('.cache/sp')); import cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; k=AESGCM.generate_key(bit_length=256); a=AESGCM(k); n=os.urandom(12); print(cryptography.__version__, a.decrypt(n, a.encrypt(n, b'bonjour', b'ad'), b'ad'))"
```
Expected : `50.0.1 b'bonjour'`. **Piège mesuré** : `PYTHONPATH=.cache\sp` ne marche pas — le `._pth` de l'embeddable ignore la variable ; seul `sys.path.insert` fait entrer le dossier.

- [ ] **Step 3 : prouver DPAPI sous le même runtime**

Run :
```
"%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe" -c "import ctypes, ctypes.wintypes as w; c=ctypes.WinDLL('crypt32', use_last_error=True); print('crypt32 charge', bool(c.CryptProtectData))"
```
Expected : `crypt32 charge True`.

- [ ] **Step 4 : ajouter la dépendance**

Dans `backend/requirements.txt`, après le bloc `# OS trust store for TLS …` :

```
# Coffre a mot de passe maitre + archive chiffree (plan Settings, D1).
# Roue abi3 : la meme vaut pour tout CPython >= 3.11, donc elle survivra a une
# montee de version du runtime embarque. Mesure du 03/09/2026 : +4 076 686 o de
# roues, +11 389 540 o installees, sur un installeur de 129 635 836 o.
# La stdlib embarquee n'a PAS d'AES : sans cette roue, pas de mot de passe
# maitre et pas d'archive lisible par le telephone (R12 P2).
cryptography>=46.0.0
```

- [ ] **Step 5 : la garde du build**

Dans `scripts/build-installer.ps1`, juste après `Write-Host "  $pkgCount packages staged (bytecode purged)"` (fin de l'étape 3) :

```powershell
# Garde du coffre (plan Settings, D1) : la roue cryptography doit non seulement
# etre posee, mais IMPORTABLE PAR LE PYTHON EMBARQUE (abi3), pas seulement par
# le python de build. Sans cette garde, un buyer decouvrirait le probleme au
# premier deverrouillage, cle en main et coffre ferme.
# Mesure du 03/09/2026 : PYTHONPATH est ignore par le ._pth de l'embeddable,
# donc le chemin se force par sys.path.insert dans le -c.
$pyEmb = Join-Path $runtime "python.exe"
$probe = "import sys, os; sys.path.insert(0, r'$sitePkgs'); " +
         "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; " +
         "import cryptography; k = AESGCM.generate_key(bit_length=256); " +
         "a = AESGCM(k); n = os.urandom(12); " +
         "assert a.decrypt(n, a.encrypt(n, b'x', b'y'), b'y') == b'x'; " +
         "print(cryptography.__version__)"
$cryptoVer = (& $pyEmb -c $probe)
if ($LASTEXITCODE -ne 0) {
    throw "cryptography inutilisable sous le runtime embarque -- le coffre ne s'ouvrirait pas chez l'acheteur"
}
Write-Host "  cryptography $cryptoVer utilisable par le runtime embarque" -ForegroundColor Green
```

- [ ] **Step 6 : le banc du socle**

`backend/tests/test_coffre_socle.py` :

```python
"""Socle du coffre (plan Settings T14) — la primitive AES doit exister ICI.

Ce banc ne teste pas notre code : il teste la DÉPENDANCE, et il le dit
franchement quand elle manque. C'est le filet qui empêche T15 d'être écrit
au-dessus de rien.
Run: python tests/test_coffre_socle.py   (depuis backend/)"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

try:
    import cryptography
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    presente = True
except ImportError as e:
    presente = False
    print("FAIL cryptography absente :", e)
    print("     -> pip install -r requirements.txt (la roue est dans "
          "requirements.txt depuis le plan Settings T14)")
    ECHECS += 1

if presente:
    check(tuple(int(x) for x in cryptography.__version__.split(".")[:1]) >= (46,),
          f"version >= 46 (lue {cryptography.__version__})")
    k = AESGCM.generate_key(bit_length=256)
    check(len(k) == 32, "clé de 256 bits")
    a = AESGCM(k); n = os.urandom(12)
    ct = a.encrypt(n, b"bonjour", b"entete")
    check(a.decrypt(n, ct, b"entete") == b"bonjour", "aller-retour AES-256-GCM")
    check(len(ct) == len(b"bonjour") + 16, "le tag GCM fait 16 o et voyage collé")
    try:
        a.decrypt(n, ct, b"autre-entete")
        check(False, "une AAD différente doit lever")
    except Exception:
        check(True, "une AAD différente lève : l'en-tête est authentifié")
    try:
        a.decrypt(n, ct[:-1] + bytes([ct[-1] ^ 1]), b"entete")
        check(False, "un octet retourné doit lever")
    except Exception:
        check(True, "un octet retourné lève : le chiffré est authentifié")
    import ctypes
    c = ctypes.WinDLL("crypt32", use_last_error=True)
    check(bool(c.CryptProtectData), "crypt32.CryptProtectData joignable par ctypes")

print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 7 : installer, lancer, constater le vert**

Run (depuis `backend/`) :
```
python -m pip install -r requirements.txt
python tests/test_coffre_socle.py
```
Expected : 7 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 8 : commit**

```bash
git add backend/requirements.txt scripts/build-installer.ps1 backend/tests/test_coffre_socle.py
git commit -m 'coffre : trancher pour la roue cryptography embarquee, avec la mesure' -m 'Trois voies mesurees sous le VRAI runtime embarque : DPAPI (0 o mais ni mot de passe ni archive portable), roue cryptography (+4 076 686 o de roues, +11 389 540 o installees sur un installeur de 129 635 836 o, AES-256-GCM lisible par CommonCrypto et javax.crypto), chiffrement stdlib maison (0 o mais un mode a ecrire et a prouver). La roue gagne : R12 exige que le telephone lise larchive. PBKDF2-HMAC-SHA256 600 000 plutot que scrypt, plus rapide mais absent des API mobiles standard. Une garde de build refuse un installeur ou la roue ne simporterait pas sous le python embarque.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 15 : Le coffre — DPAPI, dérivation, chiffrement, format d'archive figé

**Files:**
- Create: `backend/app/services/dpapi.py`
- Create: `backend/app/services/coffre.py`
- Test: `backend/tests/test_coffre.py`

#### Le format `DZKV1`, figé ici et lu par le plan mobile (R12 P2)

```
octets  0..5     "DZKV1\n"                 magie + version de format
octets  6..21    sel                       16 o aleatoires
octets 22..25    iterations PBKDF2         uint32 gros-boutiste
octets 26..37    nonce AES-GCM             12 o aleatoires
octets 38..      AES-256-GCM(clair) || tag  le tag de 16 o est colle a la fin

AAD  = les 38 premiers octets (magie + sel + iterations + nonce)
cle  = PBKDF2-HMAC-SHA256(mot_de_passe en UTF-8, sel, iterations, dklen=32)
clair = un objet JSON encode en UTF-8
```

Ce format est **le contrat avec l'application mobile** : l'AAD couvre l'en-tête, donc changer le nombre d'itérations dans le fichier fait échouer le déchiffrement au lieu de dériver silencieusement une mauvaise clé. Le plan mobile n'écrit pas ce format, il le LIT.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Le coffre (plan Settings T15) — DPAPI, derivation, chiffrement, format.

Banc-miroir : le coffre est relu DEPUIS LE FICHIER a chaque assertion, et le
format est verifie octet par octet, pas par la valeur de retour du chiffreur.
Run: python tests/test_coffre.py   (depuis backend/)"""
import json, os, pathlib, struct, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import coffre as C, dpapi as D                    # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

def test_dpapi():
    b = D.sceller(b"un-secret-de-32-octets-exactement", b"deepotus")
    check(b != b"un-secret-de-32-octets-exactement", "le blob n'est pas le clair")
    check(len(b) > 100, f"DPAPI ajoute son enveloppe (lu {len(b)} o)")
    check(D.desceller(b, b"deepotus") == b"un-secret-de-32-octets-exactement",
          "aller-retour DPAPI")
    check(D.desceller(b, b"autre") is None,
          "une entropie differente rend None, jamais une exception nue")
    check(D.desceller(b"nimporte quoi", b"deepotus") is None,
          "un blob invalide rend None")

def test_format():
    blob = C.chiffrer({"cles": {"FAL_KEY": "abc"}}, "mon mot de passe", iterations=1000)
    check(blob[:6] == b"DZKV1\n", "magie DZKV1")
    check(len(blob) == 38 + 16 + len(json.dumps(
        {"cles": {"FAL_KEY": "abc"}}, ensure_ascii=False, separators=(",", ":"))
        .encode("utf-8")), "en-tete de 38 o + tag de 16 o + le JSON compact")
    check(struct.unpack(">I", blob[22:26])[0] == 1000, "les iterations sont dans l'en-tete")
    check(C.dechiffrer(blob, "mon mot de passe")["cles"]["FAL_KEY"] == "abc",
          "aller-retour")
    try:
        C.dechiffrer(blob, "mauvais")
        check(False, "un mauvais mot de passe doit lever")
    except C.MotDePasseInvalide as e:
        check("mot de passe" in str(e).lower(), "et le dire en francais")
    casse = blob[:22] + struct.pack(">I", 999) + blob[26:]
    try:
        C.dechiffrer(casse, "mon mot de passe")
        check(False, "un en-tete trafique doit lever")
    except C.MotDePasseInvalide:
        check(True, "l'AAD couvre l'en-tete : changer les iterations echoue")
    check(C.chiffrer({"a": 1}, "x", iterations=1000)[6:22]
          != C.chiffrer({"a": 1}, "x", iterations=1000)[6:22],
          "un sel neuf a chaque chiffrement")

def test_coffre_pose_et_ouvre():
    check(C.est_pose() is False, "aucun coffre au depart")
    C.poser("mot-de-passe-maitre", {"FAL_KEY": "fal-123", "MESHY_API_KEY": "me-456"})
    check(C.est_pose() is True, "le coffre existe sur le disque")
    brut = (_tmp / "coffre.dzk").read_bytes()
    check(b"fal-123" not in brut and b"FAL_KEY" not in brut,
          "rien n'est lisible dans le fichier : ni la valeur, ni le nom de la cle")
    check(C.ouvert() is False, "poser ne laisse pas le coffre ouvert")
    try:
        C.ouvrir("pas-le-bon")
        check(False, "mauvais mot de passe : doit lever")
    except C.MotDePasseInvalide:
        check(True, "mauvais mot de passe refuse")
    cles = C.ouvrir("mot-de-passe-maitre")
    check(cles["FAL_KEY"] == "fal-123", "le coffre rend les cles")
    check(C.ouvert() is True and C.cles_posees() == {"FAL_KEY", "MESHY_API_KEY"},
          "le coffre est ouvert et sait ce qu'il contient")
    C.ecrire_cle("HEYGEN_API_KEY", "hg-789")
    C.fermer()
    check(C.ouvert() is False and C.lire_cle("FAL_KEY") is None,
          "ferme : plus rien en memoire")
    check(C.ouvrir("mot-de-passe-maitre")["HEYGEN_API_KEY"] == "hg-789",
          "l'ecriture a bien ete rechiffree sur le disque")

def test_changer_mot_de_passe():
    C.changer_mot_de_passe("mot-de-passe-maitre", "un-autre-secret")
    try:
        C.ouvrir("mot-de-passe-maitre")
        check(False, "l'ancien mot de passe ne doit plus ouvrir")
    except C.MotDePasseInvalide:
        check(True, "l'ancien mot de passe est mort")
    check(C.ouvrir("un-autre-secret")["FAL_KEY"] == "fal-123",
          "le nouveau ouvre, le contenu est intact")

def test_retenir_sur_ce_pc():
    C.ouvrir("un-autre-secret")
    C.retenir()
    check((_tmp / "coffre.pc").is_file(), "la cle derivee est scellee par DPAPI")
    scelle = (_tmp / "coffre.pc").read_bytes()
    check(b"un-autre-secret" not in scelle, "le mot de passe lui-meme n'est jamais ecrit")
    C.fermer()
    check(C.ouvrir_par_dpapi() is True, "le coffre s'ouvre seul sur ce PC")
    check(C.lire_cle("FAL_KEY") == "fal-123", "et les cles sont la")
    C.oublier()
    C.fermer()
    check(C.ouvrir_par_dpapi() is False and not (_tmp / "coffre.pc").exists(),
          "oublier() coupe l'ouverture automatique")

test_dpapi(); test_format(); test_coffre_pose_et_ouvre()
test_changer_mot_de_passe(); test_retenir_sur_ce_pc()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_coffre.py`
Expected : `ModuleNotFoundError: No module named 'app.services.coffre'`

- [ ] **Step 3 : écrire `dpapi.py`**

```python
"""DPAPI par ctypes (plan Settings, D1 — voie (a), gardée en protection au repos).

Ce que ça fait : sceller un secret POUR CETTE SESSION WINDOWS. Ce que ça ne
fait pas : donner un mot de passe maître (il n'y a rien à saisir) ni produire
quoi que ce soit de lisible ailleurs — un blob DPAPI est illisible sur un
autre PC, a fortiori sur un téléphone. C'est exactement pour cela qu'il sert
ici de SERRURE LOCALE sur la clé dérivée (« retenir sur ce PC ») et jamais de
coffre à lui tout seul.

Mesuré le 03/09/2026 sous le runtime embarqué : `CryptProtectData` sur 19 o
rend 246 o, l'aller-retour marche, une entropie différente échoue. Piège :
avec `ctypes.windll`, `get_last_error()` rend 0 même en cas d'échec — d'où
`WinDLL(..., use_last_error=True)`, seul moyen d'avoir un vrai code d'erreur.
"""
import ctypes
import ctypes.wintypes as wt

from loguru import logger

CRYPTPROTECT_UI_FORBIDDEN = 0x01


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _entree(b: bytes) -> tuple:
    buf = ctypes.create_string_buffer(b, len(b))
    return _BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _sortie(blob: _BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        _kernel32.LocalFree(blob.pbData)


def _appel(fn, data: bytes, entropie: bytes) -> bytes | None:
    dedans, _g1 = _entree(data)
    ent, _g2 = _entree(entropie or b"")
    dehors = _BLOB()
    ok = fn(ctypes.byref(dedans), None,
            ctypes.byref(ent) if entropie else None,
            None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dehors))
    if not ok:
        logger.info(f"dpapi: appel refuse (GetLastError={ctypes.get_last_error()})")
        return None
    return _sortie(dehors)


def sceller(donnees: bytes, entropie: bytes = b"") -> bytes:
    b = _appel(_crypt32.CryptProtectData, donnees, entropie)
    if b is None:
        raise OSError("DPAPI: CryptProtectData a echoue")
    return b


def desceller(blob: bytes, entropie: bytes = b"") -> bytes | None:
    """None plutôt qu'une exception : un blob illisible (autre compte, autre
    machine, fichier corrompu) est un cas NORMAL — l'app redemande le mot de
    passe, elle ne plante pas."""
    try:
        return _appel(_crypt32.CryptUnprotectData, blob, entropie)
    except Exception as e:  # noqa: BLE001
        logger.info(f"dpapi: descellement impossible ({e})")
        return None
```

- [ ] **Step 4 : écrire `coffre.py`**

```python
"""Coffre à mot de passe maître + format d'archive portable
(plan Settings, D1 — voie (b), tranchée en T14).

Format `DZKV1`, figé et LU PAR LE PLAN MOBILE (R12 P2) :

    octets  0..5   b"DZKV1\\n"              magie + version de format
    octets  6..21  sel                      16 o aleatoires
    octets 22..25  iterations PBKDF2        uint32 gros-boutiste
    octets 26..37  nonce AES-GCM            12 o aleatoires
    octets 38..    AES-256-GCM(clair)||tag  tag de 16 o colle a la fin
    AAD  = les 38 premiers octets
    cle  = PBKDF2-HMAC-SHA256(mdp UTF-8, sel, iterations, dklen=32)
    clair = un objet JSON encode en UTF-8, separateurs compacts

L'AAD couvre l'en-tête : trafiquer le nombre d'itérations fait ÉCHOUER le
déchiffrement au lieu de dériver silencieusement une autre clé.

600 000 itérations = 0,42 s mesurées sur cette machine (03/09/2026). PBKDF2
plutôt que `scrypt` (0,14 s) parce que le téléphone doit le relire avec
CommonCrypto / javax.crypto, où PBKDF2-HMAC-SHA256 est standard.
"""
import hashlib
import json
import os
import struct

from loguru import logger

from app.config import APP_VERSION, DATA_ROOT

MAGIE = b"DZKV1\n"
SEL_N = 16
NONCE_N = 12
ENTETE_N = len(MAGIE) + SEL_N + 4 + NONCE_N          # 38
ITERATIONS = 600_000
FICHIER = DATA_ROOT / "coffre.dzk"
SCEAU_PC = DATA_ROOT / "coffre.pc"
ENTROPIE_DPAPI = b"DeepotusVideoGen/coffre/v1"

# Le coffre OUVERT ne vit qu'en mémoire de processus : rien de déchiffré ne
# retouche le disque, jamais.
_ouvert: dict | None = None
_mdp_courant: str | None = None


class MotDePasseInvalide(Exception):
    """Mot de passe faux, fichier trafiqué, ou format inconnu — dans les trois
    cas la réponse à l'utilisateur est la même, et on ne dit pas laquelle."""


def _aesgcm():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM


def deriver(mot_de_passe: str, sel: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", (mot_de_passe or "").encode("utf-8"),
                               sel, iterations, dklen=32)


def chiffrer(objet: dict, mot_de_passe: str, iterations: int = ITERATIONS) -> bytes:
    sel = os.urandom(SEL_N)
    nonce = os.urandom(NONCE_N)
    entete = MAGIE + sel + struct.pack(">I", iterations) + nonce
    cle = deriver(mot_de_passe, sel, iterations)
    clair = json.dumps(objet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return entete + _aesgcm()(cle).encrypt(nonce, clair, entete)


def _cle_de(blob: bytes, mot_de_passe: str) -> tuple:
    if len(blob) < ENTETE_N + 16 or blob[:len(MAGIE)] != MAGIE:
        raise MotDePasseInvalide("fichier illisible : ce n'est pas une archive DZKV1")
    sel = blob[6:22]
    iterations = struct.unpack(">I", blob[22:26])[0]
    if not (1 <= iterations <= 10_000_000):
        raise MotDePasseInvalide("fichier illisible : nombre d'iterations aberrant")
    nonce = blob[26:38]
    return deriver(mot_de_passe, sel, iterations), nonce, blob[:ENTETE_N]


def dechiffrer(blob: bytes, mot_de_passe: str) -> dict:
    cle, nonce, entete = _cle_de(blob, mot_de_passe)
    try:
        clair = _aesgcm()(cle).decrypt(nonce, blob[ENTETE_N:], entete)
    except Exception:  # noqa: BLE001 — InvalidTag et compagnie
        raise MotDePasseInvalide("mot de passe incorrect, ou archive alteree")
    try:
        return json.loads(clair.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MotDePasseInvalide("archive dechiffree mais illisible")


# ── le coffre local ────────────────────────────────────────────────────────

def est_pose() -> bool:
    return FICHIER.is_file()


def ouvert() -> bool:
    return _ouvert is not None


def _reecrire(contenu: dict, mot_de_passe: str) -> None:
    """Réécrit le coffre en repassant par `chiffrer()`, donc avec un sel ET un
    nonce NEUFS. Réutiliser un nonce avec la même clé casserait GCM, et c'est
    le genre d'erreur qui ne se voit pas à l'œil : d'où l'unique chemin
    d'écriture, et l'écriture atomique par fichier temporaire."""
    tmp = FICHIER.with_suffix(".dzk.tmp")
    tmp.write_bytes(chiffrer(contenu, mot_de_passe))
    tmp.replace(FICHIER)


def poser(mot_de_passe: str, cles: dict) -> None:
    """Crée (ou remplace) le coffre. Ne l'ouvre pas : poser et ouvrir sont
    deux gestes différents, et les confondre ferait qu'un coffre fraîchement
    posé serait déjà déverrouillé sans que personne ne l'ait demandé."""
    contenu = {"format": 1, "cles": dict(cles or {})}
    _reecrire(contenu, mot_de_passe)
    logger.info(f"coffre pose : {len(contenu['cles'])} cle(s), {FICHIER}")


def ouvrir(mot_de_passe: str) -> dict:
    global _ouvert, _mdp_courant
    if not est_pose():
        raise MotDePasseInvalide("aucun coffre sur cette machine")
    contenu = dechiffrer(FICHIER.read_bytes(), mot_de_passe)
    _ouvert = contenu
    _mdp_courant = mot_de_passe
    appliquer_a_chaud(contenu.get("cles") or {})
    return dict(contenu.get("cles") or {})


def fermer() -> None:
    global _ouvert, _mdp_courant
    _ouvert = None
    _mdp_courant = None


def cles_posees() -> set:
    return set((_ouvert or {}).get("cles", {}).keys())


def lire_cle(nom: str) -> str | None:
    return ((_ouvert or {}).get("cles") or {}).get(nom)


def ecrire_cle(nom: str, valeur: str) -> None:
    """Écrit une clé dans le coffre OUVERT et rechiffre le fichier."""
    if _ouvert is None or _mdp_courant is None:
        raise MotDePasseInvalide("le coffre est ferme")
    if valeur:
        _ouvert.setdefault("cles", {})[nom] = valeur
    else:
        _ouvert.get("cles", {}).pop(nom, None)
    _reecrire(_ouvert, _mdp_courant)
    appliquer_a_chaud({nom: valeur})


def changer_mot_de_passe(ancien: str, nouveau: str) -> None:
    contenu = dechiffrer(FICHIER.read_bytes(), ancien)
    _reecrire(contenu, nouveau)
    oublier()          # le sceau DPAPI portait l'ancienne clé : il ne vaut plus
    logger.info("coffre : mot de passe change, sceau DPAPI efface")


def appliquer_a_chaud(cles: dict) -> None:
    """Pose les clés dans le processus. Mesuré le 03/09 (T8) : rien n'est figé
    à l'import, sauf la recopie de FAL_KEY dans os.environ par
    fal_service.py:34-35 — on écrit donc les deux."""
    from app.config import settings
    for k, v in (cles or {}).items():
        os.environ[k] = v or ""
        if isinstance(getattr(settings, k, ""), str):
            try:
                setattr(settings, k, v or "")
            except Exception:  # noqa: BLE001
                pass


# ── « retenir sur ce PC » : DPAPI scelle le MOT DE PASSE, pas les cles ─────

def retenir() -> None:
    if _mdp_courant is None:
        raise MotDePasseInvalide("le coffre est ferme")
    from app.services import dpapi
    tmp = SCEAU_PC.with_suffix(".pc.tmp")
    tmp.write_bytes(dpapi.sceller(_mdp_courant.encode("utf-8"), ENTROPIE_DPAPI))
    tmp.replace(SCEAU_PC)
    logger.info("coffre : ouverture automatique armee pour cette session Windows")


def oublier() -> None:
    try:
        SCEAU_PC.unlink(missing_ok=True)
    except OSError:
        pass


def ouvrir_par_dpapi() -> bool:
    """Ouverture au lancement, sans rien demander, SUR CETTE SESSION WINDOWS.
    Rend False (jamais d'exception) si le sceau manque, vient d'un autre
    compte, ou ne déchiffre plus le coffre."""
    if not (SCEAU_PC.is_file() and est_pose()):
        return False
    from app.services import dpapi
    brut = dpapi.desceller(SCEAU_PC.read_bytes(), ENTROPIE_DPAPI)
    if not brut:
        return False
    try:
        ouvrir(brut.decode("utf-8"))
        return True
    except (MotDePasseInvalide, UnicodeDecodeError):
        logger.info("coffre : sceau DPAPI perime (mot de passe change ?) — ignore")
        oublier()
        return False
```

- [ ] **Step 5 : lancer, constater le vert**

Run : `python tests/test_coffre.py`
Expected : 24 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 6 : mesurer le coût du déverrouillage sur CETTE machine**

Run (depuis `backend/`) :
```
python -c "import sys,time; sys.path.insert(0,'.'); import os, tempfile; os.environ['DEEPOTUS_DATA_DIR']=tempfile.mkdtemp(); from app.services import coffre as C; C.poser('x'*20, {'FAL_KEY':'a'}); t=time.perf_counter(); C.ouvrir('x'*20); print('ouverture : %.2f s' % (time.perf_counter()-t))"
```
Expected : ~0,42 s (les 600 000 itérations mesurées). Au-dessus d'**1,5 s**, baisser `ITERATIONS` et **le dire dans le module** : un déverrouillage qu'on subit à chaque lancement finit par être désarmé par l'utilisateur, ce qui est pire qu'un compte d'itérations plus bas.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/dpapi.py backend/app/services/coffre.py backend/tests/test_coffre.py
git commit -m 'coffre : DPAPI, derivation, AES-256-GCM et le format DZKV1 fige' -m 'Le format est le contrat avec le plan mobile : magie, sel, iterations, nonce, puis AES-256-GCM avec len-tete complet en AAD — trafiquer les iterations fait echouer le dechiffrement au lieu de deriver une autre cle en silence. Un sel ET un nonce neufs a chaque ecriture. DPAPI ne scelle QUE le mot de passe, pour louverture automatique sur cette session Windows ; changer le mot de passe efface le sceau. desceller() rend None plutot que de lever : un blob illisible est un cas normal.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 16 : Le coffre branché — `.env` vidé, ouverture au lancement, archive portable

**Files:**
- Modify: `backend/app/services/coffre.py` (`SECRETES`, `absorber_env`, `archiver`, `restaurer`)
- Modify: `backend/app/api/routes.py` (`list_keys` l. 3555, `set_key` l. 3568)
- Modify: `backend/app/api/settings_routes.py` (routes `/coffre/*`)
- Modify: `backend/app/main.py` (`lifespan` : ouverture automatique)
- Test: `backend/tests/test_coffre_integration.py`

**Ce que ça change pour l'utilisateur, dit franchement** : une fois le coffre posé, les clés **quittent le `.env` en clair**. Le fichier garde les réglages (modèles, identifiants de voix, `TELEGRAM_CHAT_ID`…) ; les secrets vivent dans `coffre.dzk`. Tant que le coffre est fermé, l'écran des clés dit « verrouillé » au lieu de mentir sur ce qu'il ne peut pas lire.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Le coffre branché (plan Settings T16) — .env vide, ecran, archive.

Banc-miroir : apres chaque geste, le banc RELIT le .env sur le disque, le
fichier coffre.dzk en octets, et les reponses JSON des routes.
Run: python tests/test_coffre_integration.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
(_tmp / ".env").write_text(
    "FAL_KEY=fal-secret-123\nGEMINI_MODEL=gemini-flash-latest\n"
    "TELEGRAM_BOT_TOKEN=111:AAA\nTELEGRAM_CHAT_ID=-100999\n", encoding="utf-8")

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                          # noqa: E402
from app.config import settings                                   # noqa: E402
from app.services import coffre as C                              # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

c = TestClient(app)
MDP = "un-mot-de-passe-maitre-long"

def test_poser_absorbe_le_env():
    r = c.post("/api/reglages/coffre/poser", json={"mot_de_passe": MDP})
    check(r.status_code == 200, f"200 (lu {r.status_code})")
    check(set(r.json()["absorbees"]) == {"FAL_KEY", "TELEGRAM_BOT_TOKEN"},
          "seules les clés SECRÈTES sont absorbées")
    env = (_tmp / ".env").read_text(encoding="utf-8")
    check("fal-secret-123" not in env and "111:AAA" not in env,
          "les secrets ont quitté le .env en clair")
    check("GEMINI_MODEL=gemini-flash-latest" in env and "TELEGRAM_CHAT_ID=-100999" in env,
          "les réglages non secrets restent dans le .env")
    brut = (_tmp / "coffre.dzk").read_bytes()
    check(b"fal-secret-123" not in brut, "et rien n'est lisible dans le coffre")

def test_ecran_des_cles_dit_la_verite():
    C.fermer()
    j = c.get("/api/settings/keys").json()["keys"]
    fal = [k for k in j if k["key"] == "FAL_KEY"][0]
    check(fal["source"] == "coffre-verrouille" and fal["set"] is None,
          "coffre fermé : l'écran dit « verrouillé », il n'invente pas un état")
    check(fal["preview"] == "", "et il ne montre aucun aperçu")
    r = c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": "faux"})
    check(r.status_code == 401, f"mauvais mot de passe : 401 (lu {r.status_code})")
    r = c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": MDP})
    check(r.status_code == 200 and r.json()["cles"] == 2, "ouvert, 2 clés")
    check(settings.FAL_KEY == "fal-secret-123" and os.environ["FAL_KEY"] == "fal-secret-123",
          "appliqué à chaud dans settings ET dans os.environ")
    j2 = c.get("/api/settings/keys").json()["keys"]
    fal2 = [k for k in j2 if k["key"] == "FAL_KEY"][0]
    check(fal2["source"] == "coffre" and fal2["set"] is True and fal2["preview"],
          "coffre ouvert : la clé est définie, avec son aperçu masqué")
    gm = [k for k in j2 if k["key"] == "GEMINI_MODEL"][0]
    check(gm["source"] == "env", "un réglage non secret vient toujours du .env")
    d = c.get("/api/reglages/diagnostic").json()["cles"]
    df = [k for k in d if k["cle"] == "FAL_KEY"][0]
    check(df["definie"] is True and df["source"] == "coffre",
          "le Diagnostic voit la cle du coffre ouvert, il ne la dit pas absente")
    C.fermer()
    df2 = [k for k in c.get("/api/reglages/diagnostic").json()["cles"]
           if k["cle"] == "FAL_KEY"][0]
    check(df2["definie"] is None and df2["source"] == "coffre-verrouille",
          "coffre ferme : le Diagnostic dit verrouille, pas absente")
    c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": MDP})

def test_ecrire_va_au_coffre():
    r = c.post("/api/settings/keys", json={"name": "MESHY_API_KEY", "value": "msh-42"})
    check(r.status_code == 200 and r.json()["ou"] == "coffre",
          "coffre ouvert : la clé secrète va au coffre, pas au .env")
    check("msh-42" not in (_tmp / ".env").read_text(encoding="utf-8"),
          "et le .env reste propre")
    check(C.lire_cle("MESHY_API_KEY") == "msh-42", "le coffre la rend")
    r2 = c.post("/api/settings/keys", json={"name": "GEMINI_MODEL", "value": "gemini-3"})
    check(r2.json()["ou"] == "env", "un réglage non secret continue d'aller au .env")

def test_archive_portable():
    r = c.post("/api/reglages/coffre/archive", json={"mot_de_passe": "phrase-du-telephone"})
    check(r.status_code == 200, f"200 (lu {r.status_code})")
    check(r.headers["content-type"] == "application/octet-stream", "octets bruts")
    check("DeepotusVideoGen-" in r.headers.get("content-disposition", ""),
          "un nom de fichier est proposé")
    blob = r.content
    check(blob[:6] == b"DZKV1\n", "l'archive est au format figé DZKV1")
    check(b"fal-secret-123" not in blob, "rien en clair dans l'archive")
    a = C.dechiffrer(blob, "phrase-du-telephone")
    check(a["genre"] == "archive" and a["format"] == 1, "en-tête de l'archive")
    check(a["cles"]["FAL_KEY"] == "fal-secret-123"
          and a["cles"]["MESHY_API_KEY"] == "msh-42"
          and a["cles"]["GEMINI_MODEL"] == "gemini-flash-latest",
          "coffre ET .env : l'archive porte TOUT ce qu'il faut au second poste")
    check("plafonds" in a and "pricing" in a, "plafonds et grille de prix voyagent aussi")
    check(a["app_version"] == "2.6.0" and a["machine"], "provenance datée et nommée")

    r2 = c.post("/api/reglages/coffre/archive/importer",
                files={"fichier": ("a.dzk", blob, "application/octet-stream")},
                data={"mot_de_passe": "pas-la-bonne"})
    check(r2.status_code == 401, "import : mauvais mot de passe refusé")
    r3 = c.post("/api/reglages/coffre/archive/importer",
                files={"fichier": ("a.dzk", blob, "application/octet-stream")},
                data={"mot_de_passe": "phrase-du-telephone"})
    check(r3.status_code == 200 and r3.json()["cles"] >= 3, "import accepté")

def test_retenir_et_boot():
    c.post("/api/reglages/coffre/retenir")
    check((_tmp / "coffre.pc").is_file(), "sceau DPAPI écrit")
    C.fermer()
    check(C.ouvrir_par_dpapi() is True, "au lancement, le coffre s'ouvre seul")
    e = c.get("/api/reglages/coffre/etat").json()
    check(e["pose"] and e["ouvert"] and e["retenu"], "l'état dit les trois faits")
    c.post("/api/reglages/coffre/oublier")
    check(not (_tmp / "coffre.pc").exists(), "oublier efface le sceau")

test_poser_absorbe_le_env(); test_ecran_des_cles_dit_la_verite()
test_ecrire_va_au_coffre(); test_archive_portable(); test_retenir_et_boot()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_coffre_integration.py`
Expected : `404` sur `/api/reglages/coffre/poser` → `FAIL 200 (lu 404)` en cascade.

- [ ] **Step 3 : `SECRETES`, `absorber_env`, `archiver`, `restaurer`**

À ajouter à `backend/app/services/coffre.py` :

```python
# Ce qui est un SECRET, et ce qui n'est qu'un réglage. La distinction fait
# tout : un modèle par défaut ou un identifiant de salon Telegram n'a rien à
# faire derrière un mot de passe, alors qu'un jeton en clair sur disque est
# exactement ce que le coffre existe pour supprimer.
SECRETES = {
    "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
    "IG_ACCESS_TOKEN",
}


def absorber_env(mot_de_passe: str) -> list:
    """Déplace les secrets du `.env` vers le coffre et les EFFACE du `.env`.

    Déplace, pas copie : laisser une copie en clair viderait le coffre de son
    sens. Les lignes non secrètes et les commentaires sont conservés tels
    quels (le `.env` reste lisible et éditable à la main).
    """
    from app.api.routes import _env_path, _read_env_file
    env = _read_env_file()
    pris = {k: v for k, v in env.items() if k in SECRETES and v}
    contenu = dict((_ouvert or {}).get("cles") or {})
    contenu.update(pris)
    _reecrire({"format": 1, "cles": contenu}, mot_de_passe)
    p = _env_path()
    if p.exists() and pris:
        gardees = []
        for ligne in p.read_text(encoding="utf-8").splitlines():
            s = ligne.strip()
            if s and not s.startswith("#") and "=" in s \
                    and s.split("=", 1)[0].strip() in pris:
                continue
            gardees.append(ligne)
        tmp = p.with_suffix(".env.tmp")
        tmp.write_text("\n".join(gardees) + "\n", encoding="utf-8")
        tmp.replace(p)
    logger.info(f"coffre : {len(pris)} secret(s) absorbe(s) depuis le .env")
    return sorted(pris)


def archiver(mot_de_passe: str) -> bytes:
    """L'archive portable — LUE PAR LE TÉLÉPHONE (R12 P2), jamais par lui écrite.

    Elle porte TOUT ce qu'un second poste doit savoir : les clés (coffre ET
    `.env`, parce qu'un modèle par défaut sert autant qu'un jeton), les
    plafonds et la grille de prix (sans quoi le mobile compterait ses tirs
    avec d'autres tarifs que le PC). Son mot de passe est DEMANDÉ à part :
    ce n'est pas forcément celui du coffre, et il ne doit pas l'être quand on
    envoie l'archive sur un téléphone.
    """
    import socket
    import time as _t
    from app.api.routes import _read_env_file
    from app.services import plafonds as _plaf, pricing as _pricing
    cles = dict(_read_env_file())
    cles.update((_ouvert or {}).get("cles") or {})
    objet = {"format": 1, "genre": "archive",
             "cree_le": _t.strftime("%Y-%m-%dT%H:%M:%S"),
             "app_version": APP_VERSION,
             "machine": socket.gethostname(), "cles": cles,
             "plafonds": _plaf.charger(), "pricing": _pricing.load()}
    return chiffrer(objet, mot_de_passe)


def restaurer(blob: bytes, mot_de_passe: str) -> dict:
    """Relit une archive et repose son contenu SUR CETTE MACHINE.

    Les secrets vont au coffre s'il est ouvert, au `.env` sinon — et l'on DIT
    lequel des deux, parce qu'écrire une clé en clair sans le dire serait
    exactement le contraire de ce qu'on construit ici.
    """
    from app.api.routes import _env_path, _read_env_file
    from app.services import plafonds as _plaf, pricing as _pricing
    a = dechiffrer(blob, mot_de_passe)
    if a.get("genre") != "archive":
        raise MotDePasseInvalide("ce fichier est un coffre, pas une archive")
    cles = dict(a.get("cles") or {})
    au_coffre, au_env = [], []
    if _ouvert is not None and _mdp_courant is not None:
        for k, v in cles.items():
            if k in SECRETES and v:
                _ouvert.setdefault("cles", {})[k] = v
                au_coffre.append(k)
        _reecrire(_ouvert, _mdp_courant)
    reste = {k: v for k, v in cles.items() if k not in au_coffre}
    if reste:
        p = _env_path()
        actuel = _read_env_file()
        actuel.update(reste)
        au_env = sorted(reste)
        tmp = p.with_suffix(".env.tmp")
        tmp.write_text("".join(f"{k}={v}\n" for k, v in sorted(actuel.items())),
                       encoding="utf-8")
        tmp.replace(p)
    if isinstance(a.get("plafonds"), dict):
        _plaf.enregistrer(a["plafonds"])
    if isinstance(a.get("pricing"), dict):
        _pricing.save(a["pricing"])
    appliquer_a_chaud(cles)
    logger.info(f"archive restauree : {len(au_coffre)} au coffre, {len(au_env)} au .env")
    return {"cles": len(cles), "au_coffre": sorted(au_coffre), "au_env": au_env,
            "venue_de": a.get("machine", ""), "creee_le": a.get("cree_le", "")}
```

- [ ] **Step 4 : `list_keys` et `set_key` deviennent conscients du coffre**

Dans `backend/app/api/routes.py`, remplacer le corps de `list_keys` (l. 3555) par :

```python
@router.get("/settings/keys")
async def list_keys(request: Request):
    """Chaque clé autorisée avec son état, son aperçu masqué et sa SOURCE.

    Trois sources possibles, et l'écran doit pouvoir les distinguer :
      env               — dans le .env en clair (réglages, et clés tant que
                          le coffre n'est pas posé) ;
      coffre            — dans le coffre, qui est ouvert : on sait ;
      coffre-verrouille — le coffre est posé mais fermé : on NE SAIT PAS si
                          la clé est dedans, et `set` vaut None plutôt que de
                          faire semblant.
    Les valeurs brutes ne sortent jamais.
    """
    _require_localhost(request)
    from app.services import coffre as _C
    env = _read_env_file()
    ouvert = _C.ouvert()
    verrouille = _C.est_pose() and not ouvert
    out = []
    for k in sorted(_ALLOWED_ENV_KEYS):
        v = env.get(k, "")
        source = "env"
        if not v and ouvert:
            cv = _C.lire_cle(k)
            if cv:
                v, source = cv, "coffre"
        if not v and verrouille and k in _C.SECRETES:
            out.append({"key": k, "set": None, "preview": "",
                        "source": "coffre-verrouille"})
            continue
        out.append({"key": k, "set": bool(v), "preview": _mask(v), "source": source})
    return {"keys": out, "env_path": str(_env_path()),
            "coffre": {"pose": _C.est_pose(), "ouvert": ouvert}}
```

Et, dans `backend/app/api/settings_routes.py`, `diagnostic_complet` a le même angle mort : il ne lit que le `.env`. Remplacer sa construction de `cles` par :

```python
    from app.services import coffre as C
    env = _read_env_file()
    cles = []
    for k in sorted(_ALLOWED_ENV_KEYS):
        v = env.get(k, "")
        if not v and C.ouvert():
            v = C.lire_cle(k) or ""
        if not v and C.est_pose() and not C.ouvert() and k in C.SECRETES:
            cles.append({"cle": k, "definie": None, "apercu": "",
                         "source": "coffre-verrouille", "testable": D.testable(k)})
            continue
        cles.append({"cle": k, "definie": bool(v), "apercu": _mask(v),
                     "source": "coffre" if (v and not env.get(k)) else "env",
                     "testable": D.testable(k)})
```

Sans ce complément, le Diagnostic afficherait toutes les clés « absente » dès que le coffre les a absorbées — exactement le symptôme que le coffre existe pour ne pas produire.
Puis, dans `set_key`, **avant** la réécriture du `.env` (juste après la boucle de validation des noms) :

```python
    # Coffre ouvert : les SECRETS y vont, et pas dans le .env en clair.
    from app.services import coffre as _C
    if _C.ouvert():
        secrets = {n: v for n, v in
                   {(e.get("name") or "").strip(): (e.get("value") or "").strip()
                    for e in entries}.items() if n in _C.SECRETES}
        if secrets:
            for n, v in secrets.items():
                _C.ecrire_cle(n, v)
            entries = [e for e in entries
                       if (e.get("name") or "").strip() not in secrets]
            if not entries:
                return {"ok": True, "written": sorted(secrets), "ou": "coffre",
                        "restart_required": False, "restart_for": [], "tests": {},
                        "message": "Enregistre dans le coffre et applique."}
```

et, dans le `return` final de `set_key` (écrit en T8), ajouter `"ou": "env",`.

- [ ] **Step 5 : les routes du coffre**

À ajouter à `backend/app/api/settings_routes.py` :

```python
@router.get("/coffre/etat")
async def coffre_etat(request: Request):
    _local(request)
    from app.services import coffre as C
    return {"pose": C.est_pose(), "ouvert": C.ouvert(),
            "retenu": C.SCEAU_PC.is_file(),
            "cles": sorted(C.cles_posees()) if C.ouvert() else []}


@router.post("/coffre/poser")
async def coffre_poser(body: dict, request: Request):
    """Pose le coffre ET absorbe les secrets du .env dans la foulée."""
    _local(request)
    from app.services import coffre as C
    mdp = str((body or {}).get("mot_de_passe") or "")
    if len(mdp) < 8:
        raise HTTPException(400, "mot de passe trop court (8 caracteres au moins)")
    if C.est_pose():
        raise HTTPException(409, "un coffre existe deja : ouvrez-le, ou changez "
                                 "son mot de passe — poser ecraserait son contenu")
    C.poser(mdp, {})
    absorbees = C.absorber_env(mdp)
    C.ouvrir(mdp)
    return {"ok": True, "absorbees": absorbees}


@router.post("/coffre/ouvrir")
async def coffre_ouvrir(body: dict, request: Request):
    _local(request)
    from app.services import coffre as C
    try:
        cles = C.ouvrir(str((body or {}).get("mot_de_passe") or ""))
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
    return {"ok": True, "cles": len(cles)}


@router.post("/coffre/fermer")
async def coffre_fermer(request: Request):
    _local(request)
    from app.services import coffre as C
    C.fermer()
    return {"ok": True}


@router.post("/coffre/mot-de-passe")
async def coffre_mot_de_passe(body: dict, request: Request):
    _local(request)
    from app.services import coffre as C
    nouveau = str((body or {}).get("nouveau") or "")
    if len(nouveau) < 8:
        raise HTTPException(400, "mot de passe trop court (8 caracteres au moins)")
    try:
        C.changer_mot_de_passe(str((body or {}).get("ancien") or ""), nouveau)
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
    return {"ok": True, "message": "Mot de passe change ; l'ouverture "
                                   "automatique a ete desarmee."}


@router.post("/coffre/retenir")
async def coffre_retenir(request: Request):
    _local(request)
    from app.services import coffre as C
    try:
        C.retenir()
    except C.MotDePasseInvalide as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@router.post("/coffre/oublier")
async def coffre_oublier(request: Request):
    _local(request)
    from app.services import coffre as C
    C.oublier()
    return {"ok": True}


@router.post("/coffre/archive")
async def coffre_archive(body: dict, request: Request):
    """Produit l'archive chiffrée portable (format DZKV1) et la rend telle
    quelle. C'est le fichier que le téléphone lira (R12 P2)."""
    from fastapi.responses import Response
    import time as _t
    _local(request)
    from app.services import coffre as C
    mdp = str((body or {}).get("mot_de_passe") or "")
    if len(mdp) < 8:
        raise HTTPException(400, "mot de passe trop court (8 caracteres au moins)")
    blob = C.archiver(mdp)
    nom = f"DeepotusVideoGen-{_t.strftime('%Y-%m-%d')}.dzk"
    return Response(content=blob, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"',
                             "Cache-Control": "no-store"})


@router.post("/coffre/archive/importer")
async def coffre_archive_importer(request: Request,
                                  fichier: UploadFile = File(...),
                                  mot_de_passe: str = Form("")):
    _local(request)
    from app.services import coffre as C
    blob = await fichier.read()
    try:
        return C.restaurer(blob, mot_de_passe)
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
```

Compléter l'import FastAPI en tête de `settings_routes.py` :
`from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile`.

- [ ] **Step 6 : ouvrir le coffre au lancement**

Dans `backend/app/main.py`, `lifespan`, juste après `await init_db()` :

```python
    # Coffre (plan Settings, D1) : si l'utilisateur a coche « retenir sur ce
    # PC », DPAPI descelle le mot de passe et les cles reviennent en memoire
    # sans qu'on demande rien. Sinon on le DIT dans le journal plutot que de
    # laisser croire a des cles perdues (le symptome exact qu'on veut eviter).
    try:
        from app.services import coffre as _coffre
        if _coffre.ouvrir_par_dpapi():
            logger.info(f"  Coffre:     ouvert automatiquement "
                        f"({len(_coffre.cles_posees())} cle(s))")
        elif _coffre.est_pose():
            logger.info("  Coffre:     pose mais VERROUILLE — "
                        "Reglages > Coffre pour l'ouvrir")
    except Exception as e:  # noqa: BLE001 — un coffre muet ne bloque pas le boot
        logger.warning(f"coffre au demarrage ignore: {e}")
```

- [ ] **Step 7 : lancer, constater le vert**

Run : `python tests/test_coffre_integration.py`
Expected : 29 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 8 : relancer les bancs que le changement traverse**

Run, un processus par fichier :
```
python tests/test_coffre.py
python tests/test_settings_routes.py
python tests/test_guides_et_cles.py
python tests/test_plafonds_garde.py
```
Expected : `0 échec(s)` sur les quatre. `test_guides_et_cles.py` en particulier : sans coffre posé, `set_key` doit se comporter EXACTEMENT comme avant (`ou: "env"`).

- [ ] **Step 9 : commit**

```bash
git add backend/app/services/coffre.py backend/app/api/routes.py backend/app/api/settings_routes.py backend/app/main.py backend/tests/test_coffre_integration.py
git commit -m 'coffre : le .env vide de ses secrets, ouverture au lancement, archive portable' -m 'absorber_env DEPLACE les secrets, il ne les copie pas : laisser une copie en clair viderait le coffre de son sens. Coffre ferme, lecran des cles repond coffre-verrouille avec set=None au lieu dinventer un etat quil ne peut pas lire. Larchive porte les cles du coffre ET du .env, plus les plafonds et la grille de prix, parce quun second poste qui compte avec dautres tarifs ne compte rien.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 17 : L'écran du coffre (section S8)

**Files:**
- Modify: `scripts/patch_bundle_reglages.py` (section S8 ; la ligne S5c de T9 est REMPLACÉE)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcheur)
- Test: `backend/tests/test_patch_reglages.py` (assertions ajoutées)

**Coût de patch** : `DzCoffre` s'ajoute au bloc S1, l'entrée « Coffre » et sa branche réutilisent les ancres S2a / S2b / S3 déjà consommées. **Une ancre change de forme** : celle de la pastille d'état d'une clé, élargie pour couvrir le ton en même temps que le libellé — parce que `list_keys` rend désormais `set: null` (coffre verrouillé), et qu'une pastille rouge « missing » sur une clé qui existe serait un mensonge.

| Ancre | Compte | Rôle |
|---|---|---|
| `r.jsx(te,{tone:h&&h.set?"green":"red",dot:!0,children:h&&h.set?"set":"missing"}),` | 1 | **remplace** l'ancre étroite de S5c : ton + libellé, trois états au lieu de deux |

- [ ] **Step 1 : ajouter les assertions au banc (rouge)**

```python
    check("function DzCoffre(" in s, "DzCoffre injecté")
    check(s.count('{k:"coffre",l:"Coffre"}') == 1, "une entrée de barre « Coffre »")
    check(s.count('h.set===null?"amber"') == 1, "la pastille connaît le troisième état")
    check(s.count('h.set===null?"coffre"') == 1, "et son libellé le dit")
    check(s.count("/api/reglages/coffre/archive") >= 1, "l'archive est joignable depuis l'écran")
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : cinq `FAIL`, `5 échec(s)`.

- [ ] **Step 3 : la section S8**

```python
# ── S8 : ecran du coffre a mot de passe maitre ─────────────────────────────

S8 = (
    "function DzCoffre(){"
    "const[e,setE]=x.useState(null),[m1,setM1]=x.useState(''),"
    "[m2,setM2]=x.useState(''),[msg,setMsg]=x.useState(''),"
    "[arc,setArc]=x.useState('');"
    "const lire=()=>fetch('/api/reglages/coffre/etat').then(R=>R.json())"
    ".then(setE).catch(()=>{});"
    "x.useEffect(()=>{lire()},[]);"
    "const poste=(u,b)=>fetch(u,{method:'POST',"
    "headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})})"
    ".then(R=>R.json().then(j=>({s:R.status,j:j})));"
    "const poser=()=>{if(m1.length<8){setMsg('Mot de passe trop court "
    "(8 caracteres au moins).');return}"
    "if(m1!==m2){setMsg('Les deux saisies different.');return}"
    "poste('/api/reglages/coffre/poser',{mot_de_passe:m1}).then(o=>{"
    "setMsg(o.s===200?('Coffre pose. Cles deplacees hors du .env : '"
    "+(o.j.absorbees||[]).join(', ')):('Refus : '+(o.j.detail||o.s)));"
    "setM1('');setM2('');lire()})};"
    "const ouvrir=()=>poste('/api/reglages/coffre/ouvrir',{mot_de_passe:m1})"
    ".then(o=>{setMsg(o.s===200?('Coffre ouvert : '+o.j.cles+' cle(s).')"
    ":'Mot de passe incorrect.');setM1('');lire()});"
    "const fermer=()=>poste('/api/reglages/coffre/fermer').then(()=>{"
    "setMsg('Coffre ferme. Les cles ne sont plus en memoire.');lire()});"
    "const retenir=()=>poste('/api/reglages/coffre/retenir').then(()=>{"
    "setMsg('Ouverture automatique armee pour cette session Windows.');lire()});"
    "const oublier=()=>poste('/api/reglages/coffre/oublier').then(()=>{"
    "setMsg('Ouverture automatique desarmee.');lire()});"
    "const archiver=()=>{if(arc.length<8){setMsg('Mot de passe de larchive "
    "trop court.');return}"
    "fetch('/api/reglages/coffre/archive',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({mot_de_passe:arc})}).then(R=>{"
    "if(!R.ok)return R.json().then(j=>{setMsg('Refus : '+(j.detail||R.status))});"
    "return R.blob().then(bl=>{var u=URL.createObjectURL(bl);"
    "var a=document.createElement('a');a.href=u;"
    "a.download='DeepotusVideoGen-archive.dzk';document.body.appendChild(a);"
    "a.click();a.remove();URL.revokeObjectURL(u);"
    "setMsg('Archive telechargee. Gardez le mot de passe : sans lui elle est "
    "definitivement illisible.')})}).catch(er=>setMsg('Echec : '+er))};"
    "const importer=ev=>{var f=ev.target.files&&ev.target.files[0];if(!f)return;"
    "var fd=new FormData();fd.append('fichier',f);"
    "fd.append('mot_de_passe',arc);"
    "fetch('/api/reglages/coffre/archive/importer',{method:'POST',body:fd})"
    ".then(R=>R.json().then(j=>({s:R.status,j:j}))).then(o=>{"
    "setMsg(o.s===200?('Archive lue : '+o.j.cles+' cle(s), venue de '"
    "+(o.j.venue_de||'?')+' le '+(o.j.creee_le||'?')+'.')"
    ":('Refus : '+(o.j.detail||o.s)));lire()})"
    ".catch(er=>setMsg('Echec : '+er));ev.target.value=''};"
    "const champ=(v,set,ph)=>r.jsx('input',{type:'password',value:v,"
    "onChange:ev=>set(ev.target.value),placeholder:ph,"
    "style:{background:'var(--bg-base)',border:'1px solid var(--stroke)',"
    "borderRadius:'var(--r-sm)',padding:'6px 10px',color:'var(--ink-strong)',"
    "fontFamily:'var(--f-mono)',fontSize:12,width:280}});"
    "if(!e)return r.jsx('div',{style:{padding:24,color:'var(--ink-muted)'},"
    "children:'Coffre...'});"
    "return r.jsxs(r.Fragment,{children:["
    "r.jsx('div',{className:'display',style:{fontSize:22,"
    "color:'var(--ink-strong)',marginBottom:4},children:'Coffre'}),"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)',marginBottom:18},"
    "children:'Vos cles chiffrees par un mot de passe maitre (AES-256-GCM, "
    "PBKDF2-HMAC-SHA256). Une fois le coffre pose, elles quittent le fichier "
    ".env en clair. Le mot de passe nest stocke nulle part : si vous le "
    "perdez, il faut regenerer les cles chez chaque fournisseur.'}),"
    "r.jsxs(jt,{style:{padding:16,marginBottom:14},children:["
    "r.jsxs('div',{style:{display:'flex',gap:10,alignItems:'center',"
    "marginBottom:12},children:["
    "r.jsx(te,{tone:e.pose?'green':'neutral',dot:!0,"
    "children:e.pose?'coffre pose':'aucun coffre'}),"
    "r.jsx(te,{tone:e.ouvert?'green':'amber',dot:!0,"
    "children:e.ouvert?('ouvert - '+e.cles.length+' cle(s)'):'verrouille'}),"
    "r.jsx(te,{tone:e.retenu?'cyan':'neutral',dot:!0,"
    "children:e.retenu?'retenu sur ce PC':'demande a chaque lancement'})]}),"
    "e.pose?r.jsxs('div',{style:{display:'flex',gap:10,alignItems:'center',"
    "flexWrap:'wrap'},children:["
    "e.ouvert?null:champ(m1,setM1,'mot de passe maitre'),"
    "e.ouvert?r.jsx(K,{variant:'ghost',size:'md',onClick:fermer,"
    "children:'Fermer'}):r.jsx(K,{variant:'primary',size:'md',icon:'check',"
    "onClick:ouvrir,children:'Ouvrir'}),"
    "e.ouvert&&!e.retenu?r.jsx(K,{variant:'ghost',size:'md',onClick:retenir,"
    "children:'Retenir sur ce PC'}):null,"
    "e.retenu?r.jsx(K,{variant:'ghost',size:'md',onClick:oublier,"
    "children:'Ne plus retenir'}):null]})"
    ":r.jsxs('div',{style:{display:'flex',gap:10,alignItems:'center',"
    "flexWrap:'wrap'},children:[champ(m1,setM1,'mot de passe maitre'),"
    "champ(m2,setM2,'le meme, pour verifier'),"
    "r.jsx(K,{variant:'primary',size:'md',icon:'check',glow:!0,onClick:poser,"
    "children:'Poser le coffre'})]}),"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)',marginTop:12},"
    "children:msg})]}),"
    "r.jsxs(jt,{style:{padding:16},children:["
    "r.jsx('div',{className:'upper',style:{marginBottom:8},"
    "children:'Archive chiffree'}),"
    "r.jsx('div',{style:{fontSize:12,color:'var(--ink-soft)',marginBottom:12},"
    "children:'Un fichier .dzk qui porte vos cles, vos plafonds et votre "
    "grille de prix, pour un second poste ou le telephone. Son mot de passe "
    "est demande a part - ce nest pas celui du coffre, et il vaut mieux quil "
    "ne le soit pas.'}),"
    "r.jsxs('div',{style:{display:'flex',gap:10,alignItems:'center',"
    "flexWrap:'wrap'},children:[champ(arc,setArc,'mot de passe de larchive'),"
    "r.jsx(K,{variant:'primary',size:'md',onClick:archiver,"
    "children:'Exporter larchive'}),"
    "r.jsxs('label',{style:{fontSize:12,color:'var(--cyan)',cursor:'pointer'},"
    "children:['Importer une archive...',"
    "r.jsx('input',{type:'file',accept:'.dzk',onChange:importer,"
    "style:{display:'none'}})]})]})]})]})}"
)
```

Puis, dans `patcher()` :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + S6 + S7 + S8 + "function DzPricing(){", "S1-bloc")
    s = apply(s, '[{k:"keys",l:"API keys"},',
              '[{k:"diag",l:"Diagnostic"},{k:"keys",l:"API keys"},'
              '{k:"coffre",l:"Coffre"},{k:"export",l:"Sauvegarde"},', "S2a-barre")
    s = apply(s, 'const ym=["keys",',
              'const ym=["diag","coffre","export","keys",', "S2b-liste-blanche")
    s = apply(s, 's==="pricing"&&r.jsx(DzPricing,{})]})',
              's==="pricing"&&r.jsxs(r.Fragment,{children:[r.jsx(DzPricing,{}),'
              'r.jsx(DzPlafonds,{})]}),s==="diag"&&r.jsx(DzDiag,{}),'
              's==="export"&&r.jsx(DzExport,{}),'
              's==="coffre"&&r.jsx(DzCoffre,{})]})', "S3-corps")
```

et **remplacer** la ligne S5c écrite en T9 par celle-ci, ancrée plus large (la pastille porte maintenant trois états, `set` pouvant valoir `null` quand le coffre est verrouillé) :

```python
    s = apply(s,
              'r.jsx(te,{tone:h&&h.set?"green":"red",dot:!0,'
              'children:h&&h.set?"set":"missing"}),',
              'r.jsx(te,{tone:h&&h.set===null?"amber":h&&h.set?"green":"red",dot:!0,'
              'children:h&&h.set===null?"coffre":h&&h.set?"set":"missing"}),'
              'r.jsx(DzTestCle,{ck:k.k,def:!!(h&&h.set)}),', "S5c-bouton")
```

- [ ] **Step 4 : lancer, constater le vert**

Run (depuis `backend/`) : `python tests/test_patch_reglages.py`
Expected : 34 lignes `ok   …` puis `0 échec(s)`.

- [ ] **Step 5 : appliquer, puis faire le tour complet à la main**

Run (racine) :
```
python scripts/qa/inventory_bundle.py > avant.json
python scripts/patch_bundle_reglages.py
python scripts/qa/inventory_bundle.py --diff avant.json
copy /Y frontend\dist\assets\index-BEOJX8L5.js "%LOCALAPPDATA%\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
```
Puis, dans l'app relancée par l'utilisateur — **avant de commencer, exporter les données (T13) et copier `%LOCALAPPDATA%\DeepotusVideoGenData\.env` ailleurs** : cette manœuvre déplace de vraies clés.

1. Réglages → **Coffre** → poser un mot de passe → le message doit lister les clés déplacées ; ouvrir le `.env` : les secrets ont disparu, les réglages sont là.
2. Réglages → **API keys** : chaque clé secrète est verte « set ». Fermer le coffre, recharger : elles passent en ambre « coffre ».
3. Rouvrir le coffre, lancer une génération d'image : elle marche **sans redémarrage**.
4. « Retenir sur ce PC », fermer l'app, la relancer : le journal (`%LOCALAPPDATA%\DeepotusVideoGenData\logs\`) doit dire `Coffre: ouvert automatiquement (N cle(s))`.
5. « Exporter larchive » avec un autre mot de passe → un `.dzk` arrive dans les téléchargements. Le rouvrir par « Importer une archive… » avec un mot de passe FAUX → refus ; avec le bon → « Archive lue : N cle(s), venue de <machine> le <date> ».
6. Changer le mot de passe du coffre, relancer l'app : le journal doit dire `pose mais VERROUILLE` (le sceau DPAPI a bien été effacé).

- [ ] **Step 6 : commit**

```bash
git add scripts/patch_bundle_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'coffre : lecran, larchive chiffree et la pastille a trois etats' -m 'Lancre de la pastille dune cle est elargie pour couvrir le ton avec le libelle : list_keys rend desormais set=null quand le coffre est verrouille, et une pastille rouge missing sur une cle qui existe serait un mensonge. Larchive se telecharge par un blob local, son mot de passe est demande a part de celui du coffre.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 18 : Dépenses par catégorie — réel contre estimé (D2, section S9)

**Files:**
- Modify: `backend/app/services/plafonds.py` (`tableau`)
- Modify: `backend/app/api/settings_routes.py` (route `/depenses`)
- Modify: `scripts/patch_bundle_reglages.py` (section S9)
- Test: `backend/tests/test_depenses_tableau.py`, `backend/tests/test_patch_reglages.py`

**Ce qui rend ce tableau différent, et pourquoi il tient.** Le registre porte DEUX chiffres par ligne : `estime_usd`, posé par la garde AVANT le tir depuis la grille de prix ; `reel_usd`, écrit APRÈS coup par le fournisseur quand il le dit. Trois états, jamais mélangés :

| État | Quand | Ce que la ligne affiche |
|---|---|---|
| **réel** | Meshy a rendu `consumed_credits` ; ou un rendu HeyGen était seul en vol et le delta de quota est attribuable | le chiffre du fournisseur, et l'écart avec l'estimé |
| **estimé** | fal, ElevenLabs, les LLM — aucun de ces fournisseurs ne renvoie un coût par appel | la grille de prix × les paramètres, dit comme tel |
| **estimé, non rapproché** | un tir Meshy ou HeyGen dont la référence n'a pas pu être rattachée | l'estimé, **et le fait qu'on n'a pas su rapprocher** |

Le troisième état est le plus important : c'est celui qu'un tableau de bord ordinaire cacherait en le comptant comme « estimé ».

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Tableau des depenses, reel contre estime (plan Settings T18).

Banc-miroir : les lignes sont ecrites par la vraie garde puis relues par la
vraie route ; le banc ne fabrique aucune ligne a la main.
Run: python tests/test_depenses_tableau.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                           # noqa: E402
from app.services import plafonds as P                             # noqa: E402
from app.services.storage import init_db                           # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

def test_tableau():
    async def sc():
        await init_db()
        await P.verifier({"kind": "image", "n": 4, "model": "flux"}, "quick")
        await P.verifier({"kind": "elevenlabs", "chars": 1000}, "son")
        g = await P.verifier({"kind": "asset3d_texture",
                              "texture_resolution": "2k"}, "moteurs3d")
        await P.rattacher(g["lignes"], "meshy:t9")
        await P.noter_reel("meshy:t9", 0.44, 22.0)
        await P.verifier({"kind": "asset3d_texture",
                          "texture_resolution": "2k"}, "cartes")  # jamais rattache
        t = await P.tableau()
        par = {(l["moteur"], l["categorie"]): l for l in t["lignes"]}
        fal = par[("fal", "quick")]
        check(fal["etat"] == "estime", "fal ne facture jamais a l'appel : estimé")
        check(abs(fal["estime_usd"] - 0.012) < 1e-9, "4 x 0,003 $")
        check(fal["reel_usd"] is None and fal["ecart_usd"] is None,
              "pas de réel : pas d'écart inventé")
        me = par[("meshy", "moteurs3d")]
        check(me["etat"] == "reel", "meshy rapproché : réel")
        check(abs(me["reel_usd"] - 0.44) < 1e-9, "le chiffre du fournisseur")
        check(abs(me["ecart_usd"] - (0.44 - me["estime_usd"])) < 1e-9,
              "l'écart est réel moins estimé, dans ce sens")
        check(me["reel_unites"] == 22.0, "les crédits consommés sont dits")
        mc = par[("meshy", "cartes")]
        check(mc["etat"] == "estime-non-rapproche",
              "un tir meshy sans référence est DIT non rapproché, pas noyé dans « estimé »")
        el = par[("elevenlabs", "son")]
        check(el["etat"] == "estime", "elevenlabs : estimé")
        check(abs(t["total"]["estime_usd"] - sum(l["estime_usd"] for l in t["lignes"]))
              < 1e-9, "le total est la somme des lignes, pas un second calcul")
        check(t["total"]["reel_usd"] == 0.44 and t["total"]["couverture_pct"] > 0,
              "la couverture dit quelle part du mois est vraiment facturée")
        check(t["depuis"], "le tableau dit depuis quand il compte")

        c = TestClient(app)
        j = c.get("/api/reglages/depenses").json()
        check(len(j["lignes"]) == len(t["lignes"]), "la route sert le même tableau")
        check(j["mois"] == P.mois_courant(), "et dit de quel mois il parle")
    asyncio.run(sc())

test_tableau()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_depenses_tableau.py`
Expected : `AttributeError: module 'app.services.plafonds' has no attribute 'tableau'`

- [ ] **Step 3 : `tableau()` dans `plafonds.py`**

```python
# Les moteurs qui savent dire ce qu'ils ont VRAIMENT facturé. Pour les autres,
# « estimé » n'est pas un défaut de rigueur : c'est tout ce qui existe.
RAPPROCHABLES = {"meshy", "heygen"}


async def tableau(mois: str | None = None) -> dict:
    """Une ligne par (moteur, catégorie), avec l'état de son chiffre.

    Trois états, jamais mélangés — c'est tout l'intérêt :
      reel                    le fournisseur a facturé, on affiche SON chiffre ;
      estime                  ce moteur ne facture pas à l'appel (fal,
                              ElevenLabs, les LLM) : l'estimé est la seule
                              vérité disponible, et on le dit ;
      estime-non-rapproche    un moteur rapprochable dont CETTE ligne n'a pas
                              pu être rattachée. Le taire la ferait passer
                              pour un « estimé » ordinaire.
    """
    from app.services.storage import Depense, async_session_factory
    mois = mois or mois_courant()
    groupes: dict = {}
    depuis = ""
    async with async_session_factory() as s:
        lignes = (await s.execute(
            select(Depense).where(Depense.mois == mois))).scalars().all()
        prem = (await s.execute(
            select(Depense).order_by(Depense.quand))).scalars().first()
        if prem is not None:
            depuis = prem.quand.strftime("%Y-%m-%d")
    for l in lignes:
        g = groupes.setdefault((l.moteur, l.categorie), {
            "moteur": l.moteur, "categorie": l.categorie, "tirs": 0,
            "estime_usd": 0.0, "reel_usd": None, "reel_unites": None,
            "rapproches": 0})
        g["tirs"] += 1
        g["estime_usd"] = round(g["estime_usd"] + (l.estime_usd or 0.0), 6)
        if l.reel_usd is not None:
            g["reel_usd"] = round((g["reel_usd"] or 0.0) + l.reel_usd, 6)
            g["rapproches"] += 1
        if l.reel_unites is not None:
            g["reel_unites"] = round((g["reel_unites"] or 0.0) + l.reel_unites, 4)
    out = []
    for g in groupes.values():
        if g["reel_usd"] is not None:
            g["etat"] = "reel"
            g["ecart_usd"] = round(g["reel_usd"] - g["estime_usd"], 6)
        elif g["moteur"] in RAPPROCHABLES:
            g["etat"] = "estime-non-rapproche"
            g["ecart_usd"] = None
        else:
            g["etat"] = "estime"
            g["ecart_usd"] = None
        g["effectif_usd"] = (g["reel_usd"] if g["reel_usd"] is not None
                             else g["estime_usd"])
        out.append(g)
    out.sort(key=lambda g: -g["effectif_usd"])
    te = round(sum(g["estime_usd"] for g in out), 6)
    tr = round(sum(g["reel_usd"] or 0.0 for g in out), 6)
    tf = round(sum(g["effectif_usd"] for g in out), 6)
    return {"mois": mois, "depuis": depuis, "lignes": out,
            "total": {"estime_usd": te, "reel_usd": tr, "effectif_usd": tf,
                      "couverture_pct": round(100.0 * tr / tf, 1) if tf else 0.0}}
```

- [ ] **Step 4 : la route**

```python
@router.get("/depenses")
async def depenses(request: Request, mois: str = ""):
    """Le tableau réel-contre-estimé du mois. Le registre commence le jour de
    l'installation de la garde : `depuis` le dit, plutôt que de laisser croire
    à un historique qui n'existe pas."""
    _local(request)
    from app.services import plafonds as P
    return await P.tableau(mois or None)
```

- [ ] **Step 5 : la section S9 du patcheur**

```python
# ── S9 : tableau des depenses, reel contre estime ─────────────────────────

S9 = (
    "function DzDepenses(){"
    "const[t,setT]=x.useState(null);"
    "x.useEffect(()=>{fetch('/api/reglages/depenses').then(R=>R.json())"
    ".then(setT).catch(()=>{})},[]);"
    "if(!t)return null;"
    "const usd=v=>(v==null?'-':('$'+Number(v).toFixed(3)));"
    "const ton=e=>e==='reel'?'green':e==='estime-non-rapproche'?'amber':'neutral';"
    "const lib=e=>e==='reel'?'reel':e==='estime-non-rapproche'"
    "?'estime, non rapproche':'estime';"
    "return r.jsxs(jt,{style:{padding:16,marginTop:18},children:["
    "r.jsx('div',{className:'display',style:{fontSize:18,"
    "color:'var(--ink-strong)',marginBottom:4},"
    "children:'Depenses du mois - reel contre estime'}),"
    "r.jsxs('div',{style:{fontSize:12,color:'var(--ink-soft)',marginBottom:14},"
    "children:['Compte tenu depuis le ',t.depuis||'premier tir','. ',"
    "usd(t.total.effectif_usd),' au total, dont ',usd(t.total.reel_usd),"
    "' reellement factures par les fournisseurs (',"
    "t.total.couverture_pct,' %). Le reste est estime par votre grille de "
    "prix : fal, ElevenLabs et les LLM ne facturent pas a lappel.']}),"
    "r.jsxs('div',{style:{display:'grid',"
    "gridTemplateColumns:'120px 130px 60px 90px 90px 90px 160px',gap:8,"
    "fontSize:10.5,color:'var(--ink-muted)',paddingBottom:6,"
    "borderBottom:'1px solid var(--stroke)'},className:'upper',children:["
    "'moteur','ecran','tirs','estime','reel','ecart','etat']}),"
    "t.lignes.map((l,i)=>r.jsxs('div',{style:{display:'grid',"
    "gridTemplateColumns:'120px 130px 60px 90px 90px 90px 160px',gap:8,"
    "fontSize:11.5,alignItems:'center',padding:'6px 0',"
    "borderBottom:'1px solid var(--stroke)'},children:["
    "r.jsx('div',{children:l.moteur}),"
    "r.jsx('div',{style:{color:'var(--ink-soft)'},children:l.categorie||'-'}),"
    "r.jsx('div',{className:'mono',children:l.tirs}),"
    "r.jsx('div',{className:'mono',children:usd(l.estime_usd)}),"
    "r.jsx('div',{className:'mono',children:usd(l.reel_usd)}),"
    "r.jsx('div',{className:'mono',style:{color:l.ecart_usd==null"
    "?'var(--ink-muted)':(l.ecart_usd>0?'var(--red)':'var(--green)')},"
    "children:l.ecart_usd==null?'-':((l.ecart_usd>0?'+':'')+usd(l.ecart_usd))}),"
    "r.jsx(te,{tone:ton(l.etat),dot:!0,children:lib(l.etat)"
    "+(l.reel_unites!=null?(' - '+l.reel_unites+' cr.'):'')})]},i))]})}"
)
```

Brancher `S9` dans le bloc et monter `DzDepenses` dans la branche `pricing` :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + S6 + S7 + S8 + S9 + "function DzPricing(){",
              "S1-bloc")
    s = apply(s, 's==="pricing"&&r.jsx(DzPricing,{})]})',
              's==="pricing"&&r.jsxs(r.Fragment,{children:[r.jsx(DzPricing,{}),'
              'r.jsx(DzPlafonds,{}),r.jsx(DzDepenses,{})]}),'
              's==="diag"&&r.jsxs(r.Fragment,{children:[r.jsx(DzDiag,{}),'
              'r.jsx(DzDepenses,{})]}),'
              's==="export"&&r.jsx(DzExport,{}),'
              's==="coffre"&&r.jsx(DzCoffre,{})]})', "S3-corps")
```

et, dans `backend/tests/test_patch_reglages.py` :

```python
    check("function DzDepenses(" in s, "DzDepenses injecté")
    check(s.count("estime, non rapproche") == 1, "le troisième état est écrit en toutes lettres")
    check(s.count("r.jsx(DzDepenses,{})") == 2,
          "le tableau est monté DEUX fois : dans Pricing & budget et dans le "
          "Diagnostic — la réponse 3 de R11 range les dépenses du mois parmi "
          "les quatre choses que le diagnostic doit montrer")
```

- [ ] **Step 6 : lancer, constater le vert**

Run, un processus par fichier (depuis `backend/`) :
```
python tests/test_depenses_tableau.py
python tests/test_patch_reglages.py
```
Expected : `0 échec(s)` sur les deux (14 puis 36 lignes `ok`).

- [ ] **Step 7 : appliquer et voir**

Run (racine) : `python scripts/patch_bundle_reglages.py` puis la copie vers `%LOCALAPPDATA%`, l'app relancée par l'utilisateur. Réglages → *Pricing & budget* : sous les plafonds, le tableau. Après une génération Meshy, sa ligne doit passer de « estime, non rapproche » à « reel » avec l'écart.

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/plafonds.py backend/app/api/settings_routes.py scripts/patch_bundle_reglages.py backend/tests/test_depenses_tableau.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'depenses : le tableau reel contre estime, avec son troisieme etat' -m 'Trois etats et non deux : reel, estime (fal, ElevenLabs, LLM ne facturent pas a lappel — lestime est tout ce qui existe), et estime-non-rapproche pour un tir Meshy ou HeyGen quon na pas su rattacher. Ce troisieme etat est celui quun tableau de bord ordinaire cacherait en le comptant comme un estime ordinaire.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 19 : Recherche dans les réglages (D3, section S10)

**Files:**
- Modify: `backend/app/api/settings_routes.py` (route `/index`)
- Modify: `scripts/patch_bundle_reglages.py` (section S10)
- Test: `backend/tests/test_index_reglages.py`, `backend/tests/test_patch_reglages.py`

**Coût de patch** : une ancre neuve, comptée 1 le 03/09 — `className:"upper",style:{padding:"0 10px 10px"},children:"Settings"}),`, le titre de la barre latérale. Le champ y est inséré, DANS la portée de `xm` : c'est le seul endroit du bundle où le setter de section (`a`) est accessible, ce qui permet à un résultat de recherche d'OUVRIR sa section au lieu de simplement la nommer.

- [ ] **Step 1 : écrire le banc (rouge)**

```python
"""Index de recherche des reglages (plan Settings T19).

Banc-miroir : il relit la reponse de la route et verifie que CHAQUE section
de la barre laterale y est representee — un index qui oublie une section
enverrait la recherche dans le vide.
Run: python tests/test_index_reglages.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                          # noqa: E402

ECHECS = 0
def check(cond, msg):
    global ECHECS
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: ECHECS += 1

SECTIONS = {"diag", "keys", "coffre", "export", "accounts", "personas",
            "branding", "pack", "defaults", "paths", "news", "appearance",
            "pricing"}

c = TestClient(app)

def test_index():
    j = c.get("/api/reglages/index").json()
    e = j["entrees"]
    check(len(e) > 40, f"l'index est fourni (lu {len(e)} entrées)")
    vues = {x["section"] for x in e}
    check(SECTIONS <= vues, f"toutes les sections sont couvertes ; manquent {SECTIONS - vues}")
    check(all(x["libelle"] and x["section"] and isinstance(x["mots"], str) for x in e),
          "chaque entrée a un libellé, une section et ses mots-clés")
    fal = [x for x in e if x.get("cle") == "FAL_KEY"]
    check(len(fal) == 1 and fal[0]["section"] == "keys", "FAL_KEY pointe sur les clés")
    check("seedance" in fal[0]["mots"].lower() or "image" in fal[0]["mots"].lower(),
          "et ses mots-clés viennent du guide fournisseur, pas d'une liste doublée")
    plaf = [x for x in e if x["section"] == "pricing" and "plafond" in x["mots"].lower()]
    check(len(plaf) >= 1, "les plafonds sont trouvables par le mot « plafond »")
    cof = [x for x in e if x["section"] == "coffre"]
    check(any("mot de passe" in x["mots"].lower() for x in cof),
          "le coffre est trouvable par « mot de passe »")
    check(all("valeur" not in x and "preview" not in x for x in e),
          "aucune valeur ni apercu de cle dans l'index : que des noms et des mots")

test_index()
print(f"{ECHECS} échec(s)"); sys.exit(1 if ECHECS else 0)
```

- [ ] **Step 2 : lancer, constater le rouge**

Run : `python tests/test_index_reglages.py`
Expected : `KeyError: 'entrees'` (la route rend un 404 JSON).

- [ ] **Step 3 : la route `/index`**

```python
# Ce que la recherche des réglages sait trouver. Les entrées « clés » sont
# DÉRIVÉES des guides fournisseurs (T8) : un seul propriétaire du texte, donc
# pas de liste parallèle qui se désynchronise au premier ajout de fournisseur.
_INDEX_FIXE = [
    ("diag", "Diagnostic", "diagnostic sante disque poids journal erreurs "
                           "version crédits soldes test des cles"),
    ("keys", "Cles API", "cle api jeton token fournisseur guide tester"),
    ("coffre", "Coffre", "coffre mot de passe maitre chiffrement archive "
                         "securite verrouiller deverrouiller dpapi"),
    ("coffre", "Archive chiffree", "archive export cles second poste telephone "
                                   "mobile dzk mot de passe"),
    ("export", "Sauvegarde", "sauvegarde export copie donnees manifeste "
                             "integrite sha256 dossier disque"),
    ("pricing", "Grille de prix", "prix tarif cout dollar grille estimation"),
    ("pricing", "Plafonds de depense", "plafond budget limite mensuel alerte "
                                       "depassement confirmation depense"),
    ("pricing", "Depenses du mois", "depenses reel estime facture moteur "
                                    "categorie tableau"),
    ("accounts", "Comptes connectes", "x twitter telegram youtube instagram "
                                      "publication compte"),
    ("personas", "Personas", "persona ton voix audience personnage"),
    ("branding", "Kit de marque", "marque logo couleur branding identite"),
    ("pack", "Pack de sous-titres", "sous-titres captions police style pack"),
    ("defaults", "Defauts par fournisseur", "defaut resumeur planificateur "
                                            "provider anthropic openai gemini ollama"),
    ("paths", "Dossiers", "chemin dossier images sorties data root disque"),
    ("news", "News", "news rss flux article lecteur proxy"),
    ("appearance", "Apparence", "theme apparence couleur sombre clair"),
]


@router.get("/index")
async def index_reglages(request: Request):
    """Tout ce qu'un champ de recherche peut trouver dans les réglages, avec
    la section à ouvrir. Aucune VALEUR de clé n'y figure — seulement des noms
    et des mots."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS
    from app.services import guides_fournisseurs as G
    entrees = [{"section": s, "libelle": l, "cle": "", "mots": m}
               for s, l, m in _INDEX_FIXE]
    guides = G.tous()
    for k in sorted(_ALLOWED_ENV_KEYS):
        g = guides.get(k) or {}
        mots = " ".join(filter(None, [k.replace("_", " ").lower(),
                                      g.get("nom", ""), g.get("fr", "")[:220]]))
        entrees.append({"section": "keys", "libelle": g.get("nom") or k,
                        "cle": k, "mots": mots})
    return {"entrees": entrees}
```

- [ ] **Step 4 : la section S10 du patcheur**

```python
# ── S10 : recherche dans les reglages ─────────────────────────────────────

S10 = (
    "function DzSettingsSearch({aller:aller}){"
    "const[q,setQ]=x.useState(''),[ix,setIx]=x.useState(null);"
    "x.useEffect(()=>{fetch('/api/reglages/index').then(R=>R.json())"
    ".then(j=>setIx(j.entrees||[])).catch(()=>setIx([]))},[]);"
    "const t=q.trim().toLowerCase();"
    "const res=!t||!ix?[]:ix.filter(e=>"
    "(e.libelle+' '+e.cle+' '+e.mots).toLowerCase().indexOf(t)>=0).slice(0,8);"
    "return r.jsxs('div',{style:{padding:'0 6px 10px'},children:["
    "r.jsx('input',{type:'text',value:q,onChange:ev=>setQ(ev.target.value),"
    "placeholder:'Rechercher un reglage...',"
    "style:{width:'100%',boxSizing:'border-box',background:'var(--bg-base)',"
    "border:'1px solid var(--stroke)',borderRadius:'var(--r-sm)',"
    "padding:'6px 9px',color:'var(--ink-strong)',fontSize:12}}),"
    "res.length?r.jsx('div',{style:{marginTop:6,border:'1px solid var(--stroke)',"
    "borderRadius:'var(--r-sm)',background:'var(--bg-panel-2)',overflow:'hidden'},"
    "children:res.map((e,i)=>r.jsxs('div',{onClick:()=>{aller(e.section);setQ('')},"
    "style:{padding:'6px 9px',cursor:'pointer',fontSize:11.5,"
    "borderTop:i?'1px solid var(--stroke)':'none'},children:["
    "r.jsx('div',{style:{color:'var(--ink-strong)'},children:e.libelle}),"
    "r.jsx('div',{style:{fontSize:10,color:'var(--ink-muted)'},"
    "children:e.cle||e.section})]},e.section+'/'+(e.cle||e.libelle)))})"
    ":(t?r.jsx('div',{style:{marginTop:6,fontSize:11,color:'var(--ink-muted)'},"
    "children:'Aucun reglage ne correspond.'}):null)]})}"
)
```

Brancher `S10` dans le bloc, et consommer l'ancre du titre :

```python
    s = apply(s, "}function DzPricing(){",
              "}" + S1 + S4 + S5 + S6 + S7 + S8 + S9 + S10 + "function DzPricing(){",
              "S1-bloc")
    s = apply(s,
              'className:"upper",style:{padding:"0 10px 10px"},children:"Settings"}),',
              'className:"upper",style:{padding:"0 10px 10px"},children:"Settings"}),'
              'r.jsx(DzSettingsSearch,{aller:a}),', "S10-recherche")
```

> `a` est le setter de section de `xm` (`const[s,a]=x.useState(...)`). L'ancre est DANS le JSX de `xm`, donc `a` y est en portée — c'est précisément pourquoi le champ est inséré là et pas ailleurs : un résultat de recherche doit OUVRIR sa section, pas seulement la nommer.

et dans `backend/tests/test_patch_reglages.py` :

```python
    check("function DzSettingsSearch(" in s, "DzSettingsSearch injecté")
    check(s.count("r.jsx(DzSettingsSearch,{aller:a})") == 1,
          "monté dans la barre, avec le setter de section")
```

- [ ] **Step 5 : lancer, constater le vert**

Run, un processus par fichier (depuis `backend/`) :
```
python tests/test_index_reglages.py
python tests/test_patch_reglages.py
```
Expected : `0 échec(s)` sur les deux (8 puis 38 lignes `ok`).

- [ ] **Step 6 : appliquer et essayer**

Run (racine) : `python scripts/patch_bundle_reglages.py`, la copie vers `%LOCALAPPDATA%`, l'app relancée par l'utilisateur. Dans Réglages, taper `plafond` → un résultat « Plafonds de depense » qui ouvre *Pricing & budget* ; taper `meshy` → la ligne de la clé Meshy qui ouvre *API keys* ; taper `zzz` → « Aucun reglage ne correspond. »

- [ ] **Step 7 : commit**

```bash
git add backend/app/api/settings_routes.py scripts/patch_bundle_reglages.py backend/tests/test_index_reglages.py backend/tests/test_patch_reglages.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'reglages : un champ de recherche qui ouvre la bonne section' -m 'Le champ sinsere dans la portee de xm, seul endroit du bundle ou le setter de section est accessible : un resultat OUVRE sa section au lieu de la nommer. Les entrees des cles sont derivees des guides fournisseurs, donc un fournisseur ajoute demain est trouvable sans toucher a lindex.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

Rien n'est construit ici. Chaque ligne dit ce qui a été écarté et **par quelle réponse**, pour qu'une session future ne le repropose pas comme une idée neuve.

- **E1 — Profils de configuration** (plusieurs jeux de clés/réglages commutables) : écarté par la **réponse 1** de R11 (« Profils : non »). Un seul utilisateur, un seul jeu ; l'archive chiffrée de D1 couvre le seul besoin réel, celui du second poste.
- **E2 — Sauvegarde programmée** (copie automatique à heure fixe) : écarté par la **réponse 6** (« export manuel à la demande vers un dossier choisi »). Le mécanisme de T12 saurait s'appeler depuis une boucle, mais programmer une copie de 8,3 Gio sans qu'on la demande ferait de l'application un logiciel de sauvegarde, ce qu'elle n'est pas.
- **E3 — Coffres multiples façon Obsidian** (plusieurs `DATA_ROOT` commutables) : écarté par la constante d'architecture du dépôt — un seul `DATA_ROOT` (`config.py:24-36`), sur lequel s'appuient l'index de la Bibliothèque, la base, les rebuts et tout le reste. `DEEPOTUS_DATA_DIR` reste la porte de sortie pour qui veut vraiment déplacer ses données.

---

## Campagne de mutations

**Files:**
- Create: `backend/tests/mutations_settings.py`

Patron : `backend/tests/mutations_plaque_slicer.py`. Différence unique et nécessaire : les bancs de ce plan sont des **scripts autonomes** (`python tests/test_x.py`), pas des tests pytest — le lecteur de rouges lit donc les lignes `FAIL …` et le compte final `N échec(s)`, et traite l'absence de ce compte comme un **troisième état** (collecte cassée), exactement comme le patron traite un code de sortie ≥ 2.

### Task 20 : Écrire et passer la campagne de mutations

- [ ] **Step 1 : écrire `backend/tests/mutations_settings.py`**

```python
"""Banc de mutations des Reglages : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`, donc ni pytest ni
run-tests.ps1 ne le ramassent. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_settings.py           # toutes
    python tests/mutations_settings.py 3 17      # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres
(assertion sha256), donc il ne tourne pas pendant qu'un autre banc lit ces
fichiers.

Difference avec mutations_plaque_slicer.py : les bancs vises sont des
SCRIPTS AUTONOMES (`python tests/test_x.py`), pas des tests pytest. On lit
donc les lignes `FAIL ...` et le compte final `N echec(s)`. L'absence de ce
compte = la collecte a casse (import impossible, erreur de syntaxe) : c'est
un TROISIEME etat, jamais une mutation verte — lue comme « aucun FAIL », une
collecte cassee passerait pour un trou de couverture alors que rien n'a ete
mesure.

Trois verdicts :
  ROUGE            la mutation fait rougir les assertions attendues ;
  VERTE            rien n'a rougi -> une assertion MANQUE, c'est un travail ;
  VERTE(attendue)  la mutation est semantiquement neutre pour ce banc, et la
                   raison est ecrite a cote (attendus=None).
"""
import hashlib
import os
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

# (fichier, ancien, nouveau, banc, attendus | None)
M = [
    # ── diagnostic.py ───────────────────────────────────────────────────────
    ("backend/app/services/diagnostic.py",
     'if _cache["val"] and _cache["racine"] == racine and time.time() - _cache["t"] < cache_s:',
     'if _cache["val"] and _cache["racine"] == racine:',
     "tests/test_diagnostic.py", ["cache 0 = relu"]),
    ("backend/app/services/diagnostic.py",
     'rebuts = sorted(x for x in racine.glob("rebut_*") if x.is_dir())',
     'rebuts = []',
     "tests/test_diagnostic.py", ["rebut_* compté à part"]),
    ("backend/app/services/diagnostic.py",
     r'_LIGNE = re.compile(r"^(\S+ \S+) \| (WARNING|ERROR|CRITICAL)\s*\| (\S+) - (.*)$")',
     r'_LIGNE = re.compile(r"^(\S+ \S+) \| (\w+)\s*\| (\S+) - (.*)$")',
     "tests/test_diagnostic.py", ["INFO filtré"]),
    ("backend/app/services/diagnostic.py",
     '                                           {"Authorization": f"Key {v}"}, ok_sur=(404,),',
     '                                           {"Authorization": f"Key {v}"}, ok_sur=(200,),',
     "tests/test_diagnostic.py", ["fal : 404 sur id fictif"]),
    ("backend/app/services/diagnostic.py",
     '    if code in (401, 403):\n        return code, corps, _res(False, f"refusée ({code}) : {_msg(corps)}")',
     '    if code in (401, 403):\n        return code, corps, _res(None, f"indetermine ({code})")',
     "tests/test_diagnostic.py", ["anthropic : 401"]),
    ("backend/app/services/diagnostic.py",
     '        if nom.startswith("X_"):\n            return _res(None, "les quatre clés X se testent ensemble',
     '        if False:\n            return _res(None, "les quatre clés X se testent ensemble',
     "tests/test_diagnostic.py", ["X : test de groupe"]),

    # ── plafonds.py ─────────────────────────────────────────────────────────
    ("backend/app/services/plafonds.py",
     "    ok = CONFIRME.get() if confirme is None else bool(confirme)",
     "    ok = True",
     "tests/test_plafonds.py", ["402 attendu"]),
    ("backend/app/services/plafonds.py",
     "        if gp > 0 and deja_g + devis[\"total_usd\"] > gp:",
     "        if False:",
     "tests/test_plafonds.py", ["402 global attendu"]),
    ("backend/app/services/plafonds.py",
     "            if deja + somme > pm:",
     "            if False:",
     "tests/test_plafonds.py", ["402 attendu"]),
    ("backend/app/services/plafonds.py",
     '    return time.strftime("%Y-%m")',
     '    return "1970-01"',
     "tests/test_plafonds.py", ["rangée dans le mois courant"]),
    ("backend/app/services/plafonds.py",
     '    qui = "toutes dépenses confondues" if motif == "global" else f"le moteur « {moteur} »"',
     '    qui = "une depense"',
     "tests/test_plafonds.py", ["le message dit le moteur"]),
    ("backend/app/services/plafonds.py",
     "    if not n:\n        logger.info(f\"plafonds.noter_reel: référence inconnue {ref!r} — ignorée\")\n    return n",
     "    return 1",
     "tests/test_plafonds.py", ["référence inconnue"]),
    ("backend/app/services/plafonds.py",
     "            if d is not None:\n                d.ref = ref[:64]\n                n += 1",
     "            if d is not None:\n                n += 1",
     "tests/test_plafonds.py", ["rattachement a posteriori", "réel remonté"]),
    ("backend/app/services/plafonds.py",
     '            d["effectif_usd"] = round(d["effectif_usd"] + l.reel_usd, 6)',
     '            d["effectif_usd"] = round(d["effectif_usd"] + (l.estime_usd or 0.0), 6)',
     "tests/test_plafonds.py", ["effectif = réel là où il existe"]),
    ("backend/app/services/plafonds.py",
     "    if gp > 0 and tot[\"pct\"] >= seuil:\n        alerte.append(\"global\")",
     "    if gp > 0 and tot[\"pct\"] >= 100000:\n        alerte.append(\"global\")",
     "tests/test_plafonds.py", ["alerte levée au-delà de 80 %"]),

    # ── la garde sur les routes ─────────────────────────────────────────────
    ("backend/app/api/routes.py",
     '    await _PLAF.verifier({"kind": "image", "n": int(body.get("n") or 1), "model": (body.get("model") or "")}, str(body.get("source") or "quick"))\n',
     '',
     "tests/test_plafonds_garde.py", ["/images/generate : garde présente", "402 sous plafond"]),
    ("backend/app/main.py",
     '        (request.headers.get("x-dz-plafond") or "").strip().lower() == "confirme")',
     '        True)',
     "tests/test_plafonds_garde.py", ["402 sous plafond"]),

    # ── mise_a_jour.py ──────────────────────────────────────────────────────
    ("backend/app/services/mise_a_jour.py",
     "        return tuple(int(b) for b in bouts)",
     "        return tuple(bouts)",
     "tests/test_mise_a_jour.py", ["10 > 9, pas une comparaison de texte"]),
    ("backend/app/services/mise_a_jour.py",
     '    frais = (not force and cache\n             and (time.time() - float(cache.get("verifie_a") or 0)) < CADENCE_S)',
     '    frais = False',
     "tests/test_mise_a_jour.py", ["moins de 24 h"]),
    ("backend/app/services/mise_a_jour.py",
     '        if str(a.get("name") or "").lower().endswith(".exe"):',
     '        if True:',
     "tests/test_mise_a_jour.py", ["l'asset .exe est choisi"]),
    ("backend/app/services/mise_a_jour.py",
     '            if rel.get("draft") or rel.get("prerelease"):\n                rel = {}                      # une préversion n\'est pas une mise à jour',
     '            pass',
     "tests/test_mise_a_jour.py", ["une preversion n'est pas une mise a jour"]),
    ("backend/app/services/mise_a_jour.py",
     '    if not (hote in HOTES_PERMIS or hote.endswith(".github.com")):',
     '    if False:',
     "tests/test_mise_a_jour.py", ["hors github.com est refusée"]),

    # ── export_donnees.py ───────────────────────────────────────────────────
    ("backend/app/services/export_donnees.py",
     '    return [p for p in out if p.name != ".env"]',
     '    return out',
     "tests/test_export_donnees.py", ["JAMAIS dans un export"]),
    ("backend/app/services/export_donnees.py",
     '        if destination.resolve() == DATA_ROOT.resolve() \\\n                or DATA_ROOT.resolve() in destination.resolve().parents:',
     '        if False:',
     "tests/test_export_donnees.py", ["SOUS DATA_ROOT est refusée"]),
    ("backend/app/services/export_donnees.py",
     '        if h.hexdigest() != f["sha256"]:',
     '        if p.stat().st_size != f["octets"]:',
     "tests/test_export_donnees.py", ["octet changé est vu et NOMMÉ"]),
    ("backend/app/services/export_donnees.py",
     '    racines = _sources(quoi or {})\n    if not racines:',
     '    racines = _sources(quoi or {}) or [DATA_ROOT]\n    if not racines:',
     "tests/test_export_donnees.py", ["aucun lot coché"]),
    # VERTE ATTENDUE, et la raison : le banc copie des fichiers qui ne changent
    # pas pendant la copie, donc hacher la source ou la destination donne le
    # meme sha256. La difference ne se voit que sur un fichier ecrit pendant
    # l'export — un cas qu'aucun banc deterministe ne sait fabriquer.
    ("backend/app/services/export_donnees.py",
     '            h.update(b)\n            fo.write(b)',
     '            fo.write(b)\n            h.update(b)',
     "tests/test_export_donnees.py", None),

    # ── coffre.py ───────────────────────────────────────────────────────────
    ("backend/app/services/coffre.py",
     "    return entete + _aesgcm()(cle).encrypt(nonce, clair, entete)",
     "    return entete + _aesgcm()(cle).encrypt(nonce, clair, None)",
     "tests/test_coffre.py", ["l'AAD couvre l'en-tete"]),
    ("backend/app/services/coffre.py",
     "def chiffrer(objet: dict, mot_de_passe: str, iterations: int = ITERATIONS) -> bytes:\n    sel = os.urandom(SEL_N)",
     "def chiffrer(objet: dict, mot_de_passe: str, iterations: int = ITERATIONS) -> bytes:\n    sel = b'0' * SEL_N",
     "tests/test_coffre.py", ["un sel neuf"]),
    ("backend/app/services/coffre.py",
     '    entete = MAGIE + sel + struct.pack(">I", iterations) + nonce\n    cle = deriver(mot_de_passe, sel, iterations)',
     '    entete = MAGIE + sel + struct.pack(">I", 0) + nonce\n    cle = deriver(mot_de_passe, sel, iterations)',
     "tests/test_coffre.py", ["les iterations sont dans l'en-tete"]),
    ("backend/app/services/coffre.py",
     '    except Exception:  # noqa: BLE001 — InvalidTag et compagnie\n        raise MotDePasseInvalide("mot de passe incorrect, ou archive alteree")',
     '    except Exception:  # noqa: BLE001\n        return {}',
     "tests/test_coffre.py", ["mauvais mot de passe doit lever"]),
    ("backend/app/services/dpapi.py",
     "    except Exception as e:  # noqa: BLE001\n        logger.info(f\"dpapi: descellement impossible ({e})\")\n        return None",
     "    except Exception as e:  # noqa: BLE001\n        raise",
     "tests/test_coffre.py", ["blob invalide rend None"]),

    # ── coffre branche ──────────────────────────────────────────────────────
    ("backend/app/services/coffre.py",
     '    pris = {k: v for k, v in env.items() if k in SECRETES and v}',
     '    pris = {k: v for k, v in env.items() if v}',
     "tests/test_coffre_integration.py", ["seules les clés SECRÈTES"]),
    ("backend/app/services/coffre.py",
     '        tmp = p.with_suffix(".env.tmp")\n        tmp.write_text("\\n".join(gardees) + "\\n", encoding="utf-8")\n        tmp.replace(p)',
     '        pass',
     "tests/test_coffre_integration.py", ["quitté le .env en clair"]),
    ("backend/app/api/routes.py",
     '            out.append({"key": k, "set": None, "preview": "",\n                        "source": "coffre-verrouille"})',
     '            out.append({"key": k, "set": False, "preview": "",\n                        "source": "coffre-verrouille"})',
     "tests/test_coffre_integration.py", ["l'écran dit « verrouillé »"]),
    ("backend/app/api/routes.py",
     '        secrets = {n: v for n, v in\n                   {(e.get("name") or "").strip(): (e.get("value") or "").strip()\n                    for e in entries}.items() if n in _C.SECRETES}',
     '        secrets = {}',
     "tests/test_coffre_integration.py", ["la clé secrète va au coffre"]),
    ("backend/app/services/coffre.py",
     '    cles = dict(_read_env_file())\n    cles.update((_ouvert or {}).get("cles") or {})',
     '    cles = dict((_ouvert or {}).get("cles") or {})',
     "tests/test_coffre_integration.py", ["l'archive porte TOUT"]),

    # ── guides et cles ──────────────────────────────────────────────────────
    ("backend/app/api/routes.py",
     '    "FIGMA_TOKEN",\n',
     '',
     "tests/test_guides_et_cles.py", ["FIGMA_TOKEN accepté"]),
    ("backend/app/api/routes.py",
     "    for k, v in changes.items():\n        os.environ[k] = v\n        courant = getattr(settings, k, \"\")",
     "    for k, v in changes.items():\n        courant = getattr(settings, k, \"\")",
     "tests/test_guides_et_cles.py", ["os.environ à jour AUSSI"]),
    ("backend/app/api/routes.py",
     '        "restart_required": bool(a_froid),',
     '        "restart_required": True,',
     "tests/test_guides_et_cles.py", ["plus de redémarrage exigé"]),
    ("backend/app/api/routes.py",
     "        if isinstance(courant, str):\n            try:\n                setattr(settings, k, v)\n            except Exception:  # noqa: BLE001\n                a_froid.append(k)\n        else:\n            a_froid.append(k)",
     "        try:\n            setattr(settings, k, v)\n        except Exception:  # noqa: BLE001\n            a_froid.append(k)",
     "tests/test_guides_et_cles.py", ["champ non-texte de Settings"]),

    # ── tableau reel contre estime ──────────────────────────────────────────
    ("backend/app/services/plafonds.py",
     'RAPPROCHABLES = {"meshy", "heygen"}',
     'RAPPROCHABLES = set()',
     "tests/test_depenses_tableau.py", ["DIT non rapproché"]),
    ("backend/app/services/plafonds.py",
     '            g["ecart_usd"] = round(g["reel_usd"] - g["estime_usd"], 6)',
     '            g["ecart_usd"] = round(g["estime_usd"] - g["reel_usd"], 6)',
     "tests/test_depenses_tableau.py", ["réel moins estimé, dans ce sens"]),

    # ── index de recherche ──────────────────────────────────────────────────
    ("backend/app/api/settings_routes.py",
     '    entrees = [{"section": s, "libelle": l, "cle": "", "mots": m}\n               for s, l, m in _INDEX_FIXE]',
     '    entrees = []',
     "tests/test_index_reglages.py", ["toutes les sections sont couvertes"]),
    ("backend/app/api/settings_routes.py",
     '        mots = " ".join(filter(None, [k.replace("_", " ").lower(),\n                                      g.get("nom", ""), g.get("fr", "")[:220]]))',
     '        mots = k.lower()',
     "tests/test_index_reglages.py", ["ses mots-clés viennent du guide"]),
]


def rouges(banc):
    """Les messages FAIL du banc autonome, et le troisieme etat.

    Un script autonome de ce plan finit TOUJOURS par « N echec(s) ». Si cette
    ligne manque, le script est mort avant (import impossible, erreur de
    syntaxe introduite par la mutation) : rien n'a ete mesure, et le dire est
    la seule reponse honnete.
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PY, banc], capture_output=True, cwd=R / "backend",
                       timeout=900, env=env)
    txt = (r.stdout + b"\n" + r.stderr).decode("utf-8", "replace")
    if not re.search(r"^\d+ .*chec\(s\)", txt, re.M):
        return set(), txt, True
    return set(re.findall(r"^FAIL (.+)$", txt, re.M)), txt, False


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # l'arbre est en CRLF (autocrlf) : on apparie en LF, on reecrit avec la
        # fin de ligne du fichier, et l'on remet A L'OCTET PRES depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:70])
        txt = txt.replace(old, new)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        elif attendus is None:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        else:
            manquants = [a for a in attendus
                         if not any(a in msg for msg in rg)]
            verdict = ("ROUGE" if not manquants
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        apercu = old.strip().split("\n")[0][:52]
        print(f"[{i:2d}] {verdict:16s} {rel.split('/')[-1]:22s} {banc.split('/')[-1]:28s}"
              f" {apercu!r}  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
        bilan.append((i, rel, banc, verdict))
    verts = [b for b in bilan if b[3] == "VERTE"]
    erreurs = [b for b in bilan if b[3].startswith("ERREUR")]
    print(f"\n{len(bilan)} mutation(s) : "
          f"{sum(1 for b in bilan if b[3] == 'ROUGE')} rouges, "
          f"{sum(1 for b in bilan if b[3] == 'VERTE(attendue)')} vertes attendues, "
          f"{len(verts)} VERTES (assertions manquantes), "
          f"{len(erreurs)} erreurs de collecte.")
    for b in verts + erreurs:
        print("   a traiter :", b)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne EN ENTIER, une fois**

Aucun autre banc ne doit lire ces fichiers pendant ce temps (le script les mute).

Run (depuis `backend/`) : `python tests/mutations_settings.py`
Expected : ~10 minutes ; **45 mutations**, chacune sur une ligne avec son verdict et l'assertion `sha …=…` qui prouve la remise à l'octet près, puis le bilan. Attendu : **44 ROUGE, 1 VERTE(attendue)**, `0 VERTES`, `0 erreurs de collecte`.

- [ ] **Step 3 : traiter ce que la campagne révèle**

C'est ici que la campagne sert à quelque chose ; elle n'est pas un rituel.

- **VERTE** = une assertion manque. Ajouter l'assertion **dans le banc concerné** (pas dans la campagne), relancer cette mutation seule (`python tests/mutations_settings.py <n>`), et ne passer à la suite qu'une fois qu'elle est ROUGE.
- **ERREUR(collecte)** = la mutation casse l'import du banc au lieu de casser une assertion. La reformuler pour qu'elle reste du Python valide — une mutation qui empêche le banc de tourner ne mesure rien.
- **ROUGE(autres)** = ça rougit, mais pas là où on l'attendait. Lire la sortie : soit l'assertion attendue est mal nommée dans la campagne, soit la ligne mutée porte plus de sens qu'on ne croyait — dans les deux cas, corriger la campagne pour dire la vérité.
- **assertion `sha` en échec** = un fichier n'a pas été remis à l'identique. **Arrêter tout**, restaurer le fichier depuis git, et comprendre avant de relancer.

- [ ] **Step 4 : le tour complet des bancs, un processus par fichier**

Run (depuis `backend/`) :
```
python tests/test_diagnostic.py
python tests/test_settings_routes.py
python tests/test_patch_reglages.py
python tests/test_plafonds.py
python tests/test_plafonds_garde.py
python tests/test_plafonds_reel.py
python tests/test_guides_et_cles.py
python tests/test_mise_a_jour.py
python tests/test_export_donnees.py
python tests/test_coffre_socle.py
python tests/test_coffre.py
python tests/test_coffre_integration.py
python tests/test_depenses_tableau.py
python tests/test_index_reglages.py
```
Expected : `0 échec(s)` et code de sortie 0 pour les quatorze. Un seul processus par fichier : ces bancs posent `DEEPOTUS_DATA_DIR` et `DATABASE_URL` avant d'importer `app`, donc deux d'entre eux dans le même interpréteur se marcheraient dessus (c'est la raison de la règle, pas une superstition).

- [ ] **Step 5 : commit**

```bash
git add backend/tests/mutations_settings.py
git commit -m 'reglages : campagne de mutations, 45 lignes portantes cassees une a une' -m 'Meme patron que mutations_plaque_slicer, avec une difference necessaire : les bancs vises sont des scripts autonomes, donc le lecteur de rouges lit les lignes FAIL et le compte final. Labsence de ce compte est un TROISIEME etat (collecte cassee) et jamais une mutation verte — lue comme aucun FAIL, une collecte cassee passerait pour un trou de couverture alors que rien na ete mesure. Une seule verte attendue, avec sa raison ecrite a cote : hacher avant ou apres lecriture donne le meme sha sur un fichier qui ne bouge pas pendant la copie.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Ce que ce plan NE fait pas, et le dit

Nommer les dettes vaut mieux que les laisser se découvrir en exécution.

1. **Le registre `depenses` démarre vide.** Il ne rétro-remplit pas les `JobRecord` d'avant l'installation de la garde. `/cost/usage` (estimé depuis les jobs finis) reste en place pour la pastille du bandeau ; le tableau de D2 affiche « compte tenu depuis le \<date\> ». Deux registres coexistent, et chacun dit lequel il est.
2. **Le coût réel HeyGen est un delta de quota**, attribuable seulement quand un seul rendu est en vol. Le reste du temps la ligne reste « estimé » et le journal le dit. HeyGen n'expose rien de mieux (mesuré : `remaining_quota` est le solde du compte, pas un coût par vidéo).
3. **Trois liens de console et trois chemins d'API restent « de mémoire »** au 03/09 (OpenAI `/v1/models` et sa page de clés — 403 depuis l'outil ; Figma `/v1/me` ; le chemin tweepy de `Client.get_me()`). T8 Step 0 et Step 8 les font ouvrir et essayer à la main, avec un tableau à remplir. Tant qu'il n'est pas rempli, ces trois lignes ne sont pas des mesures.
4. **Le 401 de fal sur clé invalide n'est pas documenté.** `tester_cle` traite 401/403 comme un refus et tout autre code comme « indéterminé » : c'est l'essai manuel de T8 qui tranchera si fal répond bien 401.
5. **Le rejeu après confirmation de plafond ne vaut que pour `fetch(url, init)`.** Un objet `Request` déjà construit n'est pas rejouable : le 402 remonte alors tel quel à l'appelant. Vérifié le 03/09 : le bundle appelle toujours `fetch` avec une chaîne.
6. **La croissance de l'installeur (+3 %) est calculée**, pas mesurée sur un vrai build : +4 076 686 o de roues et +11 389 540 o installés sont mesurés, la compression LZMA d'Inno ne l'est pas. À confirmer au premier `build-installer.ps1`.
7. **`repatch_all.py --from reglages`** n'a pas de maillon aval au 03/09 (`reglages` est la queue de chaîne). La garde de chaîne du patcheur existe pour le jour où ce ne sera plus vrai ; elle n'est pas exercée par les bancs aujourd'hui.
8. **L'archive `DZKV1` est produite ici, jamais lue par un téléphone dans ce plan.** Le format est figé et testé de bout en bout côté PC (chiffrer → relire) ; la lecture mobile appartient au plan mobile (R12 P2), qui n'écrira pas le format mais s'y conformera.
