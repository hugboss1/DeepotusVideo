# Library — la Bibliothèque unifiée : parité puis différenciant (plan d'implémentation)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** faire de la Bibliothèque un vrai DAM local — tags, favori et étoiles persistés en base, projets qui traversent les catégories, lignée pour tout asset, fiche complète (recette, dérivés, usages en aval, coût cumulé), droits, nettoyage sûr, couleur dominante — puis lui donner ce qu'aucun DAM n'a : recherche par description et similarité, annotations horodatées, et le projet qui sait ce qui est publié, monté, imprimé.

**Architecture :** `library_assets` reste l'index de provenance PAR FICHIER (le `filename` canonique est l'identifiant de tout le dépôt, décision D5 du 28/08) et s'élargit **par colonnes ajoutées** — jamais de table de remplacement ; les entités neuves (projets, appartenances, notes) sont des tables neuves que `create_all` suffit à poser. Le calcul est en Python stdlib + Pillow, dans quatre modules à responsabilité unique (`library_projects.py`, `library_fiche.py`, `library_clean.py`, `library_color.py`) plus la façade `image_search.py`. L'écran vit dans le **bundle minifié** : sept patchers neufs chaînés en queue, chacun son `.bak_<tag>` et ses ancres uniques mesurées. **Aucun modèle d'apprentissage ne tourne dans le backend** : les embeddings viennent d'un service local optionnel (patron `voice_providers.py`/Voicebox) ou d'un endpoint distant, derrière une seule façade.

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow 12.2.0, **pas de numpy**), SQLAlchemy async + SQLite (WAL), FastAPI (`backend/app/api/routes.py`), bundle React minifié patché par `scripts/patch_bundle_<tag>.py`, bancs lancés **un processus par fichier** depuis `backend/`.

---

## Périmètre

Les bacs de `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md` § **R9. Library — réponses (03/09/2026)** sont le périmètre **exact**. Rien d'autre n'entre.

| Bac | Id | Tâche(s) | Résumé |
|---|---|---|---|
| Parité | P1 | T1, T2 | tags libres + favori + note 0–5, en base, éditables sur la vignette et la fiche, filtres partout |
| Parité | P2 | T3, T4 | projets (campagne, chapitre, deck) de **toutes** catégories ; un asset dans N projets ; catégorie devenue filtre |
| Parité | P3 | T5 | lignée pour **tout** asset : `parent_filename` + `relation` écrits par les producteurs ; le repli sous la mère est **T6 de l'Établi**, référencé |
| Parité | P4 | T6, T7 | fiche : recette rejouable, dérivés, usages en aval, coût cumulé de la lignée |
| Parité | P5 | T8 | licence + source + auteur, remplis à l'import, avertissement si la licence est inconnue |
| Parité | P6 | T9, T10 | tableau de nettoyage (poids, doublons exacts, orphelins, ratés) + corbeille + retour arrière |
| Parité | P7 | T11 | couleur dominante en PIL à l'indexation + filtre par teinte |
| Différenciant | D1 | T12, T13 | recherche par description et similarité, « comme celle-ci », doublons proches |
| Différenciant | D2 | T14 | notes et commentaires horodatés, statut à revoir / validé / rejeté |
| Différenciant | D3 | T15 | le projet dit ce qui est publié, monté, imprimé |
| Écarté | E1, E2 | — | reconnaissance de visages ; droits façon DAM d'entreprise — voir « Écarté » |

**Socle (T0)** : `library_assets` s'élargit et `library_index.carte()` cesse de rendre un tuple. Pas une fonctionnalité : le canal par lequel P1, P3, P5, P6 et P7 arrivent jusqu'à `GET /api/images` sans qu'aucun ne retouche la migration.

**Lien référencé, jamais replanifié :** `docs/superpowers/plans/2026-09-01-etabli-plaque-et-extraction.md` « **Task 6 — la Bibliothèque hiérarchique** », exécutée par `docs/superpowers/plans/2026-09-03-plan-etabli.md` **tâche 10** (tag `lignee`, `scripts/patch_bundle_lignee.py`, trois ancres mesurées le 03/09). C'est le **premier lot de P3** : le repli visuel sous la mère et la comparaison côte à côte y sont déjà planifiés. T5 ici **généralise le modèle de données** et ne réécrit pas l'écran.

## Ce que le terrain dit — mesuré le 03/09/2026

| Fait | Où | Conséquence |
|---|---|---|
| `library_assets` a 8 colonnes (`filename` PK, `source`, `kind`, `origin`, `job_id`, `deck_id`, `doc_id`, `created`) | `storage.py:228-250` | tout le reste s'ajoute par colonnes |
| Patron d'ajout : une liste `<TABLE>_COLUMNS` + une entrée dans la boucle `for table, columns in (…)` de `_auto_migrate` | `storage.py:377`, `storage.py:515-532` | `create_all` n'ALTER jamais une table existante : sans cette entrée, la base des 998 lignes n'a aucune colonne neuve |
| `carte()` rend `{filename: (source, origin)}`, **un tuple**, et n'a qu'**un** appelant | `library_index.py:192-204`, `routes.py:2044` | on passe au dict une fois plutôt que d'allonger un tuple à chaque colonne |
| 14 sites `LI.noter` dans `routes.py` + 1 dans `cards/face.py` ; `noter` avale toute exception | `grep -n "LI\." routes.py`, `library_index.py:95` | P3 et P5 passent par la **signature**, pas par 15 réécritures ; l'index ne casse jamais sa route |
| `reconcilier()` parcourt `images/` et `audio/` au boot | `library_index.py:149-189`, `main.py:137` | P6 (empreintes) et P7 (couleur) s'y branchent : un seul balayage |
| Le favori vit dans **localStorage** : `dz_fav_renders` (job ids), `dz_fav_images` (noms) | bundle, offsets 393484 et 393838 | P1 doit **reprendre** ces listes, sinon l'utilisateur perd ses favoris |
| L'onglet « Favoris » existe déjà et se calcule côté client | `Favoris:H.filter(z=>__dzFavHas(z.jobId))` ×1 | P1 remplace la **source de vérité**, pas l'onglet |
| Les onglets sont `Object.keys(vo).map(...)` | `Audio:[],Favoris:[],"Établi":[]};` ×1 | P2 et P6 obtiennent leur onglet pour ~30 octets |
| `.dzlp-case` porte `height:123px` **explicite** avec `overflow:hidden` ; `img{height:96px}` + nom ≈ 27 px | bundle, CSS du picker | une rangée d'étoiles de 18 px impose `height:141px` — sinon elle est découpée en silence : **mesurer `offsetHeight`**, pas l'existence du nœud |
| `const Lfs=(L)=>{` ×1 et `Lfs(` n'a **qu'un** site d'appel | bundle | le filtre méta entre dans `Lfs` : il s'applique aussi au repli de démo `vo[o]`, qui disparaît dès qu'un filtre est actif |
| `q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]))` ×1, `__dzSrcChips(o,T,dzSF,dzSFs)` ×1, `function __dzEtabli(cb){` ×1 | bundle | **réservées** par `patch_bundle_lignee.py` : aucun patcher d'ici ne les touche |
| `/images/process` reçoit `{op, filename, …}` et indexe `retouche` en **un seul site**, pour 8 opérations | `routes.py:4538-4565` | P3 obtient la mère et la relation d'un coup |
| `_ALLOWED_ENV_KEYS` est une liste blanche stricte ; `VOICEBOX_URL` n'y est **pas** | `routes.py:3501-3517`, `config.py:82` | D1 y ajoute ses clés, et répare l'oubli |
| `voice_providers.py` : URL par défaut, `_reach_cache` à TTL, `resolve_provider()`, `available()` | `voice_providers.py:33-105` | patron exact de la façade D1 |
| `atelier_settings` est une table clé/valeur | `storage.py:318-327` | le projet actif tient en une ligne |
| Sept colonnes portent un nom de fichier : `jobs.image_filename(_end)`, `scheduled_posts.source_image`, `bible_entities.ref_image/.face_image/.inspiration_images`, `shots.sketch_image` | `storage.py` | P4 : « où sert cet asset » sans inventer un journal d'usage |
| Les decks vivent dans `outputs/decks/`, **aucune table SQL** | `cards/contract.py:390-396` | P4 s'arrête à `library_assets.deck_id` (dette nommée) |
| `hashlib.file_digest` existe ; sha256 de 2 Mio = **1,17 ms** → 998 fichiers ≈ **1,2 s** | mesuré le 03/09 sur ce poste | P6 fait les doublons exacts au boot |
| PIL 12.2.0 : `thumbnail(128) + quantize(8, MEDIANCUT) + getcolors()` sur 1080×1920 = **16,8 ms** | mesuré le 03/09 | P7 : 998 images ≈ 17 s, une fois, en tâche de fond |
| Produit scalaire pur Python, 998 × 512 dims, tri compris = **24,5 ms** | mesuré le 03/09 | D1 : le backend ne garde que des vecteurs |
| Bundle = 1 377 573 caractères / 1 395 299 octets, CRLF homogène | `frontend/dist/assets/index-BEOJX8L5.js` | tout patcher vérifie les fins de ligne avant/après |
| Ce worktree n'a que **4** `.bak_*`, tous **ignorés par git** (`.gitignore:58`) | `ls frontend/dist/assets` | la chaîne n'est pas rejouable ici : chaque patcher crée son `.bak` depuis le bundle courant |
| Les en-têtes disent la chaîne : `print3d → libpicker → libprov → libsend → etabli` | `grep -i BASELINE scripts/patch_bundle_*.py` | queue mesurée : `etabli`, puis `lignee`, puis les sept tags d'ici |
| `guard_downstream` refuse un patcher ayant un `.bak` plus récent en aval ; `repatch_all.py` refuse une chaîne à maillon manquant | `patch_bundle_libprov.py:198-206`, `repatch_all.py:56-60` | chaque patcher se lance **seul**, dans l'ordre du plan |
| `run-tests.ps1` lance **un processus par fichier**, mode script si le fichier appelle ses tests au niveau module | `run-tests.ps1:48-78` | chaque banc porte un `__main__` autonome |

## Coût de patch

L'écran Library est **dans le bundle** ; ses greffes (`libpicker`, `libprov`, `libsend`, `etabli`) sont en queue. Sept tags neufs, chacun `EN QUEUE`, `.js.bak_<tag>`, rejouable par `python scripts/repatch_all.py --from <tag>`. **Baseline de chacun = le bundle post-patch du précédent**, dans cet ordre.

| Tâche | Bac | Backend | Bundle : tag neuf | Ancres | Coût |
|---|---|---|---|---|---|
| T0 | socle | `storage.py`, `library_index.py`, `schemas.py`, `routes.py` | aucun | — | 0 |
| T1 | P1 | `library_index.py`, `routes.py` | aucun | — | 0 |
| T2 | P1 | — | **`libmeta`** (baseline post-`lignee`) | 11 ×1 | 1 patcher |
| T3 | P2 | `storage.py`, `library_projects.py`, `routes.py` | aucun | — | 0 |
| T4 | P2 | — | **`libproj`** (post-`libmeta`) | 4 ×1 | 1 patcher |
| T5 | P3 | `library_index.py`, `routes.py` | **aucun** — le repli est `lignee`, plan Établi tâche 10 | — | 0 |
| T6 | P4 | `library_fiche.py`, `routes.py` | aucun | — | 0 |
| T7 | P4 | — | **`libfiche`** (post-`libproj`) — panneau **générique** : il peint `fiche.sections` telles qu'elles viennent | 2 ×1 | 1 patcher |
| T8 | P5 | `library_index.py`, `library_fiche.py`, `routes.py` | **aucun** — les droits sont une section de plus | — | 0 |
| T9 | P6 | `library_clean.py`, `routes.py` | aucun | — | 0 |
| T10 | P6 | — | **`libclean`** (post-`libfiche`) | 3 ×1 | 1 patcher |
| T11 | P7 | `library_color.py`, `library_index.py` | **aucun** — la rangée de chips de `libmeta` liste les valeurs présentes, teintes comprises | — | 0 |
| T12 | D1 | `image_search.py`, `config.py`, `routes.py` | aucun | — | 0 |
| T13 | D1 | `image_search.py`, `routes.py` | **`libsearch`** (post-`libclean`) | 3 ×1 | 1 patcher |
| T14 | D2 | `storage.py`, `routes.py`, `library_fiche.py` | **`libnotes`** (post-`libsearch`) | 2 ×1 | 1 patcher |
| T15 | D3 | `library_projects.py`, `routes.py` | **`libtable`** (post-`libnotes`) | 2 ×1 | 1 patcher |
| T16 | — | `tests/mutations_library.py` | aucun | — | 0 |

**Total : 7 patchers, 27 ancres ; P3, P5, P7 et la moitié de P4 coûtent zéro octet de bundle** parce qu'ils passent par des surfaces déjà génériques (la rangée de chips pilotée par les données, le panneau de fiche pilotée par `sections`).

**Deux règles non négociables, mesurées :**
1. `patch_bundle_lignee.py` réserve `q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]))`, `__dzSrcChips(o,T,dzSF,dzSFs)`, `function __dzEtabli(cb){`. Aucun patcher d'ici ne les prend. **Celui des deux qui passe en second re-mesure ses ancres** (étape 1 de T2 et T10).
2. Chaque patcher se lance **seul** ; jamais `repatch_all.py --from` un maillon amont.

## Références vérifiées

- **Eagle** (en.eagle.cool, 03/09/2026) : tags dont auto-tag à l'entrée d'un dossier ; recherche par **couleur exacte ou tons proches** ; dossiers intelligents ; **détection et fusion des doublons**. → P1, P6, P7.
- **Immich** (docs.immich.app, 03/09/2026) : recherche contextuelle **CLIP**, modèle choisi dans les réglages, **ré-indexation obligatoire au changement** ; doublons probables par distance d'embedding ; visages par DBSCAN. → D1, et sa règle : changer de modèle invalide l'index.
- **Frame.io** (help.frame.io, 03/09/2026) : commentaires **horodatés** (désactivables), annotations dessinées, **piles de versions** (empilées sans dossier, revue côte à côte), export des commentaires. → D2, et la forme de P3 (pile, pas dossier).
- **fal** (fal.ai, 03/09/2026) : **aucun endpoint d'embedding CLIP texte ↔ image** ; seul SAM 3 « image/embed », qui sert la segmentation. → D1 ne passe pas par fal ; c'est la mesure qui ouvre T12.
- **De mémoire, non vérifiés, donc jamais un argument ici** : Adobe Bridge / Lightroom, Bynder ; les embeddings multimodaux Gemini et OpenAI (**T12 les mesure avant d'en faire quoi que ce soit**) ; les formats d'export de commentaires.

## Règles du plan

1. **Le mesuré prime.** Chaque tâche commence par une mesure et son POURQUOI la cite.
2. **Bancs autonomes.** `python tests/test_<x>.py` depuis `backend/`, un processus par fichier, UTF-8 forcé dans `__main__`, **jamais** `pytest tests`. L'environnement se pose **avant** tout `import app`.
3. **Bancs-miroirs, trois temps.** On lit la **base** et le **JSON servi**, jamais le code qui prétend les produire ; on vérifie que la surface lue est la vraie ; on **compte les assertions**.
4. **Le DOM se mesure en hauteur.** Pour une case en `overflow:hidden`, l'assertion est `offsetHeight` : une case peut contribuer ~0 à la hauteur des rangées avec tous ses nœuds présents.
5. **Le navigateur voit et manipule, Python écrit.**
6. **Pas de numpy.** Boucles seulement sur des vignettes (≤ 128²) et des vecteurs (≤ 512), coût mesuré écrit dans le code.
7. **Commits** : sujet **sans accents**, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, **aucun guillemet double** dans un `-m` — d'où `git commit -F msg.txt` partout.

Patron de message (fichier `msg.txt` écrit avec `Write`) :

```
library : T0 - la table s elargit par colonnes ajoutees

Pourquoi : create_all n ALTER jamais une table existante (storage.py:515) ;
sans entree dans _auto_migrate, la base des 998 lignes n aurait aucune colonne
neuve. carte() cesse de rendre un tuple : un seul appelant, routes.py:2044.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Patron d'en-tête de banc, repris tel quel par chaque fichier de test d'ici (désigné plus bas par « l'en-tête patron ») :

```python
"""<Ce que le banc tient — une phrase.>

Run: python tests/test_<x>.py   (depuis backend/ ; un processus par fichier)
"""
import io, os, pathlib, sys, tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PIL import Image  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent


def _png(w=8, h=8, couleur=(10, 200, 30)) -> bytes:
    im = Image.new("RGB", (w, h), couleur)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _cl():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


# ... tests ...

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

Banc vert : `N passed in X.XXs`, code 0. Banc rouge : `FAILED tests/test_<x>.py::<nom> - AssertionError…`, code 1.

**Patron de patcher** — les sept patchers sont des **copies** de `scripts/patch_bundle_libprov.py` (347 lignes, mécanique éprouvée : `guard_downstream`, `ensure_tail_order`, `check_spec_parity`, `STABLE_PROBES`, `--check`, `--deltas`, restauration automatique si la vérification échoue). Recette, pour chacun : copier le fichier, puis remplacer **exactement** six blocs — `TAG`, `MARKER` + `MARKER_ATTENDU`, la docstring, `STABLE_PROBES`, `SPEC_CHAR_DELTA`/`SPEC_BYTE_DELTA`, la liste `PATCHES`. Rien d'autre. Les deltas se lisent par `--deltas` **avant** de figer `SPEC_*` (le patcher refuse de tourner tant que les deux ne concordent pas). `STABLE_PROBES` commun (comptes mesurés le 03/09), chaque patcher y ajoutant les marqueurs des patchers d'ici déjà passés :

```python
STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10), ("libprov", "__dzSrcChips", 2),
    ("libsend", "__dzSendTo", 2), ("etabli", "__dzEtabli", 2),
    ("print3d", "__dzPrint3d", 3), ("spritelab", "__dzToSpriteLab", 5),
    ("navrail", "dz_nav_collapsed", 2), ("dzdesign", "__dzCatBar", 2),
    ("cardforge-pane", 'src:"/cardforge/"', 1),
    ("vectorlab-pane", 'src:"/vectorlab/"', 1),
    ("etabli-litteral", '"Établi"', 2),
]
```

Validation de tout patcher, dans cet ordre : `--check`, application, `--deltas`, puis copie en `.mjs` et `node --check` — le bundle est un module ES, c'est la seule preuve qu'il parse encore.

---

# Lot 1 — parité

## Tâche 0 — socle : la table s'élargit, `carte()` rend un dict

**Files :** Modify `backend/app/services/storage.py:235-250` + `:441` + `:515-521` ; `backend/app/services/library_index.py:192-204` ; `backend/app/models/schemas.py:417-429` ; `backend/app/api/routes.py:2043-2051`. Test : `backend/tests/test_library_meta.py`.

- [ ] **Étape 1 : mesurer le patron de migration.**

Run (racine) : `python -c "import pathlib;s=pathlib.Path('backend/app/services/storage.py').read_text('utf-8');print(s.count('VECTOR_DOCS_COLUMNS'))"`
Attendu : `2` — déclarée une fois, référencée une fois dans la boucle. C'est le patron à copier.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_meta.py` (en-tête patron) puis :

```python
def test_les_colonnes_neuves_existent_et_migrent():
    """Une base d'AVANT (8 colonnes) reçoit les 12 neuves sans perdre ses lignes."""
    import asyncio, sqlite3

    async def init():
        from app.services.storage import init_db, _engine
        await init_db(); await _engine.dispose()

    asyncio.run(init())
    con = sqlite3.connect(pathlib.Path(_tmp, "t.db"))
    con.execute("DROP TABLE library_assets")
    con.execute("CREATE TABLE library_assets (filename VARCHAR(255) PRIMARY KEY,"
                " source VARCHAR(24), kind VARCHAR(12), origin VARCHAR(12),"
                " job_id VARCHAR(36), deck_id VARCHAR(36), doc_id VARCHAR(36),"
                " created DATETIME)")
    con.execute("INSERT INTO library_assets (filename, source, origin) "
                "VALUES ('vieux.png', 'generation', 'depot')")
    con.commit(); con.close()
    asyncio.run(init())
    con = sqlite3.connect(pathlib.Path(_tmp, "t.db"))
    cols = {r[1] for r in con.execute("PRAGMA table_info(library_assets)")}
    lignes = con.execute("SELECT filename, source FROM library_assets").fetchall()
    con.close()
    for c in ("tags", "fav", "note", "parent_filename", "relation", "licence",
              "auteur", "source_url", "sha256", "taille_o", "couleur", "teinte"):
        assert c in cols, c
    assert lignes == [("vieux.png", "generation")], lignes   # la donnée survit


def test_carte_rend_un_dict_et_images_sert_les_champs():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        (pathlib.Path(_tmp, "images") / "gen_aa11.png").write_bytes(_png())
        await LI.noter(["gen_aa11.png"], "generation")
        c = await LI.carte()
        assert isinstance(c["gen_aa11.png"], dict), type(c["gen_aa11.png"])
        assert c["gen_aa11.png"]["source"] == "generation"
        assert c["gen_aa11.png"]["origin"] == "depot"
        async with _cl() as cl:
            im = (await cl.get("/api/images")).json()["images"]
        it = [i for i in im if i["filename"] == "gen_aa11.png"][0]
        assert it["source"] == "generation" and it["tags"] == [], it  # liste, pas None
        assert it["fav"] is False and it["note"] == 0, it
        assert it["couleur"] is None and it["teinte"] is None, it

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run (depuis `backend/`) : `python tests/test_library_meta.py`
Attendu : `FAILED …::test_les_colonnes_neuves_existent_et_migrent - AssertionError: tags`, code 1.

- [ ] **Étape 4 : les colonnes.** Dans `storage.py`, `class LibraryAsset`, après `doc_id` :

```python
    # ── 03/09 : le DAM. Colonnes AJOUTÉES (jamais une table de
    # remplacement) — le filename canonique reste l'identifiant du dépôt.
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    fav: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_filename: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True)
    relation: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    licence: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    auteur: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True,
                                                  index=True)
    taille_o: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    couleur: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    teinte: Mapped[Optional[str]] = mapped_column(String(12), nullable=True,
                                                  index=True)
```

- [ ] **Étape 5 : la migration.** Après `VECTOR_DOCS_COLUMNS` :

```python
# Bibliothèque (03/09) — colonnes ajoutées à library_assets APRÈS sa livraison
# du 28/08. `create_all` n'ALTER jamais une table existante : sans cette liste,
# la base d'un utilisateur qui a déjà 998 lignes n'aurait aucune de ces
# colonnes et toute lecture partirait en OperationalError.
LIBRARY_ASSETS_COLUMNS = [
    ("tags", "TEXT"), ("fav", "INTEGER"), ("note", "INTEGER"),
    ("parent_filename", "VARCHAR(255)"), ("relation", "VARCHAR(24)"),
    ("licence", "VARCHAR(40)"), ("auteur", "VARCHAR(120)"),
    ("source_url", "TEXT"), ("sha256", "VARCHAR(64)"), ("taille_o", "INTEGER"),
    ("couleur", "VARCHAR(7)"), ("teinte", "VARCHAR(12)"),
]
```

et dans `_auto_migrate`, ajouter à la boucle la ligne `("library_assets", LIBRARY_ASSETS_COLUMNS)):` en dernière position du tuple.

- [ ] **Étape 6 : `carte()` rend un dict, les tags se lisent.** Dans `library_index.py` (`import json` en tête) :

```python
_CHAMPS = ("source", "origin", "kind", "tags", "fav", "note",
           "parent_filename", "relation", "licence", "auteur", "source_url",
           "sha256", "taille_o", "couleur", "teinte",
           "job_id", "deck_id", "doc_id")


def tags_lus(brut) -> list[str]:
    """`tags` est du JSON en base. Une valeur abîmée rend [] sans lever :
    l'index est un à-côté, il ne casse jamais la route qui le lit."""
    if not brut:
        return []
    try:
        v = json.loads(brut) if isinstance(brut, str) else brut
    except Exception:
        return []
    return [str(t) for t in v if str(t).strip()] if isinstance(v, list) else []


def tags_ecrits(tags) -> str:
    """Normalise : minuscules, espaces réduits, dédoublonné, ordre d'arrivée,
    32 caractères par tag, 24 tags. UNE seule plume d'écriture, donc une seule
    forme en base — c'est ce qui rend le filtre exact."""
    vus, out = set(), []
    for t in (tags or []):
        s = " ".join(str(t).split()).strip().lower()[:32]
        if s and s not in vus:
            vus.add(s); out.append(s)
    return json.dumps(out[:24], ensure_ascii=False)


async def carte() -> dict[str, dict]:
    """{filename: {champ: valeur}} en UNE requête — pour list_images. Rendait
    `(source, origin)` jusqu'au 03/09 ; un dict, parce que l'unique appelant
    (routes.py:2044) devrait sinon apprendre une position de tuple de plus à
    chaque colonne neuve."""
    try:
        from sqlalchemy import select
        from app.services.storage import LibraryAsset, async_session_factory
        cols = [getattr(LibraryAsset, c) for c in _CHAMPS]
        async with async_session_factory() as session:
            res = await session.execute(select(LibraryAsset.filename, *cols))
            return {r[0]: dict(zip(_CHAMPS, r[1:])) for r in res.fetchall()}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_index.carte ignorée: {e}")
        return {}
```

- [ ] **Étape 7 : le schéma et la route.** Dans `schemas.py`, `class ImageItem`, après `source_origin` :

```python
    # DAM (03/09) : additifs. Jamais None côté liste — le front ne fait pas
    # de garde sur un tableau, et une chip vide n'est pas une rangée.
    tags: list[str] = []
    fav: bool = False
    note: int = 0
    parent_filename: Optional[str] = None
    relation: Optional[str] = None
    licence: Optional[str] = None
    auteur: Optional[str] = None
    source_url: Optional[str] = None
    couleur: Optional[str] = None
    teinte: Optional[str] = None
```

Dans `routes.py`, remplacer la boucle de provenance de `list_images` :

```python
    prov = await LI.carte()
    for it in items:
        connu = prov.get(it.filename) or {}
        it.source = connu.get("source") or LI.heuristique(it.filename)
        it.source_origin = connu.get("origin") or "heuristique"
        it.tags = LI.tags_lus(connu.get("tags"))
        it.fav = bool(connu.get("fav"))
        it.note = int(connu.get("note") or 0)
        for c in ("parent_filename", "relation", "licence", "auteur",
                  "source_url", "couleur", "teinte"):
            setattr(it, c, connu.get(c))
```

- [ ] **Étape 8 : vert, et l'ancien banc tient.** Run (depuis `backend/`) : `python tests/test_library_meta.py` puis `python -m pytest tests/test_library_provenance.py -q`
Attendu : `2 passed`, puis `N passed` sans régression (`source` et `source_origin` n'ont pas bougé).

- [ ] **Étape 9 : commit.**

```bash
git add backend/app/services/storage.py backend/app/services/library_index.py backend/app/models/schemas.py backend/app/api/routes.py backend/tests/test_library_meta.py
git commit -F msg.txt
```

## Tâche 1 — P1 serveur : tags, favori, étoiles, reprise des favoris du navigateur

**Files :** Modify `backend/app/services/library_index.py` (après `renommer`), `backend/app/api/routes.py` (après `/images/{filename}/rename`, ~ligne 2150). Test : `backend/tests/test_library_meta.py` (section B).

- [ ] **Étape 1 : mesurer ce qu'on doit reprendre.**

Run : `python -c "import pathlib;s=pathlib.Path('frontend/dist/assets/index-BEOJX8L5.js').read_text('utf-8');print(s.count('dz_fav_renders'), s.count('dz_fav_images'))"`
Attendu : `2 2`. **Sans reprise, l'utilisateur perd ses favoris** le jour où la vérité passe en base — le POURQUOI de la route d'import.

- [ ] **Étape 2 : le banc rouge.** Ajouter à `test_library_meta.py` :

```python
def test_patch_asset_ecrit_tags_favori_note():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        await init_db()
        (pathlib.Path(_tmp, "images") / "gen_bb22.png").write_bytes(_png())
        async with _cl() as cl:
            r = await cl.patch("/api/library/asset/gen_bb22.png", json={
                "tags": ["  Vitrail ", "vitrail", "Deep Sea"], "fav": True,
                "note": 4})
            assert r.status_code == 200, r.text
            assert r.json()["tags"] == ["vitrail", "deep sea"], r.json()
            im = (await cl.get("/api/images")).json()["images"]
            it = [i for i in im if i["filename"] == "gen_bb22.png"][0]
            assert it["fav"] is True and it["note"] == 4, it  # ligne créée à la volée
            r2 = await cl.patch("/api/library/asset/gen_bb22.png", json={"note": 9})
            assert r2.status_code == 400 and "0" in r2.text, r2.text
            f = (await cl.get("/api/library/facettes")).json()
            assert {"valeur": "vitrail", "n": 1} in f["tags"], f
            assert f["favoris"] == 1 and f["notes"]["4"] == 1, f

    asyncio.run(scenario())


def test_reprise_des_favoris_du_navigateur():
    """Les listes localStorage entrent en base, une fois, sans doublon."""
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        await init_db()
        (pathlib.Path(_tmp, "images") / "gen_cc33.png").write_bytes(_png())
        async with _cl() as cl:
            r = await cl.post("/api/library/favoris/import",
                              json={"images": ["gen_cc33.png", "absent.png"]})
            assert r.json() == {"repris": 1, "ignores": ["absent.png"]}, r.json()
            r2 = await cl.post("/api/library/favoris/import",
                               json={"images": ["gen_cc33.png"]})
            assert r2.json()["repris"] == 0, r2.json()      # idempotent

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_meta.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : l'écriture.** Dans `library_index.py`, après `renommer` :

```python
_CHAMPS_EDITABLES = ("tags", "fav", "note", "licence", "auteur",
                     "source_url", "parent_filename", "relation")


async def editer(filename: str, champs: dict) -> dict:
    """Écrit les champs éditables, en CRÉANT la ligne si le fichier existe
    mais n'est pas indexé — `reconcilier()` ne tourne qu'au boot, et l'on ne
    fait pas attendre un redémarrage à quelqu'un qui étoile une image. Rend
    l'état RELU, jamais l'état demandé."""
    from app.services.storage import LibraryAsset, async_session_factory
    nom = Path(str(filename)).name
    async with async_session_factory() as session:
        row = await session.get(LibraryAsset, nom)
        if row is None:
            row = LibraryAsset(filename=nom, source=heuristique(nom),
                               origin="heuristique")
            session.add(row)
        if "tags" in champs:
            row.tags = tags_ecrits(champs["tags"])
        if "fav" in champs:
            row.fav = 1 if champs["fav"] else 0
        if "note" in champs:
            row.note = int(champs["note"])
        for c in ("licence", "auteur", "source_url", "parent_filename",
                  "relation"):
            if c in champs:
                v = champs[c]
                setattr(row, c, (str(v)[:255] if v not in (None, "") else None))
        await session.commit()
        await session.refresh(row)
        return {"filename": row.filename, "tags": tags_lus(row.tags),
                "fav": bool(row.fav), "note": int(row.note or 0),
                "licence": row.licence, "auteur": row.auteur,
                "source_url": row.source_url,
                "parent_filename": row.parent_filename, "relation": row.relation}


async def facettes() -> dict:
    """Ce qui existe VRAIMENT dans l'index — le front n'invente aucune valeur
    de filtre, et une facette vide n'est pas une rangée de chips."""
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    tags: dict[str, int] = {}
    teintes: dict[str, int] = {}
    notes: dict[str, int] = {}
    favoris = 0
    async with async_session_factory() as session:
        res = await session.execute(select(
            LibraryAsset.tags, LibraryAsset.teinte, LibraryAsset.note,
            LibraryAsset.fav))
        for brut, teinte, note, fav in res.fetchall():
            for t in tags_lus(brut):
                tags[t] = tags.get(t, 0) + 1
            if teinte:
                teintes[teinte] = teintes.get(teinte, 0) + 1
            if note:
                notes[str(int(note))] = notes.get(str(int(note)), 0) + 1
            if fav:
                favoris += 1

    def ordonne(d):
        return [{"valeur": k, "n": v} for k, v in
                sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))]

    return {"tags": ordonne(tags), "teintes": ordonne(teintes),
            "notes": notes, "favoris": favoris}
```

- [ ] **Étape 5 : les trois routes.** Dans `routes.py`, après `rename_image_file` :

```python
# ── Bibliothèque, le DAM (03/09) : tags, favori, note ──────────────────────

@router.patch("/library/asset/{filename}")
async def library_editer_asset(filename: str, body: dict):
    """Body : tout sous-ensemble de {tags:[str], fav:bool, note:0..5,
    licence, auteur, source_url}."""
    safe = Path(filename).name
    if not safe or safe in (".", "..") or safe != filename:
        raise HTTPException(400, "Invalid filename")
    champs = {k: v for k, v in (body or {}).items()
              if k in LI._CHAMPS_EDITABLES}
    if not champs:
        raise HTTPException(400, "Aucun champ éditable dans le corps "
                                 f"(attendus : {sorted(LI._CHAMPS_EDITABLES)})")
    if "note" in champs:
        try:
            n = int(champs["note"])
        except (TypeError, ValueError):
            raise HTTPException(400, "note doit être un entier de 0 à 5")
        if not 0 <= n <= 5:
            raise HTTPException(400, "note hors bornes : attendu 0 à 5")
        champs["note"] = n
    if "tags" in champs and not isinstance(champs["tags"], list):
        raise HTTPException(400, "tags doit être une liste de chaînes")
    return await LI.editer(safe, champs)


@router.get("/library/facettes")
async def library_facettes():
    """Les valeurs de filtre réellement présentes — la rangée de chips de
    l'écran se peint là-dessus."""
    return await LI.facettes()


@router.post("/library/favoris/import")
async def library_import_favoris(body: dict):
    """Reprise UNE FOIS des favoris du navigateur (`dz_fav_images`).
    Idempotente ; un nom absent du magasin est RENDU, jamais avalé."""
    noms = [Path(str(n)).name for n in (body or {}).get("images") or []]
    repris, ignores = 0, []
    for nom in noms:
        if not nom or not (settings.images_path / nom).is_file():
            ignores.append(nom)
            continue
        if not (await LI.editer(nom, {}))["fav"]:
            await LI.editer(nom, {"fav": True})
            repris += 1
    return {"repris": repris, "ignores": ignores}
```

- [ ] **Étape 6 : vert, commit.** Run : `python tests/test_library_meta.py` → `4 passed`.

```bash
git add backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_library_meta.py
git commit -F msg.txt   # sujet : library : P1 serveur - tags, favori, etoiles en base
```

## Tâche 2 — P1 écran : le patcher `libmeta`

**Files :** Create `scripts/patch_bundle_libmeta.py` (copie de `patch_bundle_libprov.py`) ; le bundle est modifié **par le patcher seul**. Test : `backend/tests/test_library_meta_bundle.py`.

- [ ] **Étape 1 : re-mesurer les onze ancres sur le bundle DU JOUR.**

Run (racine) :

```bash
python - <<'EOF'
import pathlib
s = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js").read_text("utf-8", newline="")
for a in ['function vm({variant:e,uploads:t=[],setUploads:n=()=>{}}){',
          '[dzSF,dzSFs]=x.useState(""),[dzEta,dzEtas]=x.useState([]),',
          'onClick:()=>{i(C);dzSFs("")},style:{height:26,padding:"0 10px",background:o===C?',
          'const Lfs=(L)=>{',
          ',o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",gap:10},children:[',
          'var tout=[],srcA="";function fermer(){',
          'function dzChips(){var bar=hote.querySelector(".dzlp-chips");if(!bar)return;',
          '\'"><img loading="lazy" src="/api/images/\'']:
    print(s.count(a), a[:56])
for a in ['q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]));', '__dzSrcChips(o,T,dzSF,dzSFs)']:
    print(s.count(a), "RESERVE lignee :", a)
EOF
```

Attendu (mesuré le 03/09) : `1` partout. Les deux dernières valent `1` **et restent intouchées** — elles appartiennent à `patch_bundle_lignee.py`. Si l'une ne vaut plus 1, `lignee` est déjà passé : lire son fichier et re-mesurer les ancres voisines **avant** d'écrire quoi que ce soit.

- [ ] **Étape 2 : le banc-miroir rouge.** Créer `backend/tests/test_library_meta_bundle.py` :

```python
"""Bibliothèque — P1 dans le bundle : étoile, tags, note, filtres.

Banc-miroir : il lit le BUNDLE LIVRÉ (jamais le patcher), et pin les comptes
d'amont — c'est ce qui attrape un effacement silencieux de la chaîne.

Run: python tests/test_library_meta_bundle.py
"""
import pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def test_le_miroir_bundle_p1():
    s = BUNDLE.read_text("utf-8")
    assert s.count("__dzMetaChips") == 2, s.count("__dzMetaChips")
    assert s.count("__dzMetaFiltre") == 2, s.count("__dzMetaFiltre")
    assert s.count("__dzLibPatch") == 2, s.count("__dzLibPatch")
    # 3 = la règle CSS, sa variante `.on`, et la classe posée sur la case
    assert s.count("dzlp-etoile") == 3, s.count("dzlp-etoile")
    for probe, want in (("__dzLibPicker", 10), ("__dzSrcChips", 2),
                        ("__dzSendTo", 2), ("__dzEtabli", 2), ('"Établi"', 2)):
        assert s.count(probe) == want, (probe, s.count(probe))


def test_la_case_du_selecteur_a_grandi_avec_sa_rangee():
    """LE PIÈGE MESURÉ : `.dzlp-case` est en `overflow:hidden`. Une rangée
    ajoutée sans relever `height` est invisible ET son nœud existe — le
    compte de nœuds ne dit rien, la hauteur si."""
    s = BUNDLE.read_text("utf-8")
    h = int(re.search(r"\.dzlp-case\{[^}]*height:(\d+)px\}", s).group(1))
    img = int(re.search(r"\.dzlp-case img\{[^}]*height:(\d+)px", s).group(1))
    et = int(re.search(r"\.dzlp-etoile\{[^}]*height:(\d+)px", s).group(1))
    assert h >= img + et + 27, (h, img, et)     # 27 = la ligne de nom


def test_le_patcher_libmeta_est_garde():
    p = (RACINE / "scripts" / "patch_bundle_libmeta.py").read_text("utf-8")
    assert "guard_downstream" in p and "STABLE_PROBES" in p
    assert "SPEC_CHAR_DELTA" in p and "node --check" in p
    for reserve in ("q=Lfs(dzSF?dzYf:", "__dzSrcChips(o,T,dzSF,dzSFs)",
                    "function __dzEtabli(cb){"):
        assert reserve not in p, reserve      # les ancres de `lignee`


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_meta_bundle.py` → `assert 0 == 2`, code 1.

- [ ] **Étape 4 : le patcher.** Copier `patch_bundle_libprov.py` → `patch_bundle_libmeta.py`. `TAG = "libmeta"`, `MARKER = "__dzMetaChips"`, `MARKER_ATTENDU = 2`. Docstring : « BASELINE : bundle POST-patch `lignee` (ou POST-`etabli` si `lignee` n'est pas passé — l'étape 1 le dit). Backup `.js.bak_libmeta`. Position : EN QUEUE. » Puis :

```python
HELPERS = (
    "function __dzLibPatch(nom,champs,ok){"
    'fetch("/api/library/asset/"+encodeURIComponent(nom),{method:"PATCH",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify(champs)})'
    ".then(function(r){return r.json()}).then(function(d){ok&&ok(d)})"
    ".catch(function(){})}"
    "function __dzMetaFiltre(L,f){"
    "if(!f||(!f.tag&&!f.note&&!f.teinte))return L||[];"
    "return (L||[]).filter(function(z){"
    "if(f.tag&&((z&&z.tags)||[]).indexOf(f.tag)<0)return false;"
    "if(f.note&&Number((z&&z.note)||0)<f.note)return false;"
    'if(f.teinte&&String((z&&z.teinte)||"")!==f.teinte)return false;'
    "return true})}"
    "function __dzMetaChips(o,T,f,setF){"
    "var lst=T[o]||[],tg={},te={},nb=0;"
    "lst.forEach(function(z){((z&&z.tags)||[]).forEach(function(t){"
    "tg[t]=(tg[t]||0)+1});if(z&&z.teinte)te[z.teinte]=(te[z.teinte]||0)+1;"
    "if(z&&Number(z.note||0)>0)nb++});"
    "var kt=Object.keys(tg).sort(),ke=Object.keys(te).sort();"
    "if(!kt.length&&!ke.length&&!nb&&!f.tag&&!f.note&&!f.teinte)return null;"
    "var mk=function(cle,val,lbl,on){"
    'return r.jsx("button",{onClick:function(){var g={tag:f.tag,note:f.note,'
    'teinte:f.teinte};g[cle]=on?(cle==="note"?0:""):val;setF(g)},'
    'style:{height:22,padding:"0 10px",fontSize:11,borderRadius:11,'
    'cursor:"pointer",border:"1px solid "+(on?"var(--amber,#f0b429)"'
    ':"var(--stroke)"),background:on?"var(--bg-panel-2)":"transparent",'
    'color:on?"var(--ink-strong)":"var(--ink-soft)"},children:lbl},'
    '"dzm_"+cle+"_"+val)};var ch=[];'
    'kt.forEach(function(t){ch.push(mk("tag",t,"#"+t+" ("+tg[t]+")",f.tag===t))});'
    'ke.forEach(function(t){ch.push(mk("teinte",t,t+" ("+te[t]+")",f.teinte===t))});'
    'if(nb)ch.push(mk("note",3,"★ 3+ ("+nb+")",f.note===3));'
    'return r.jsx("div",{"data-dz":"metachips",style:{display:"flex",gap:6,'
    'flexWrap:"wrap",alignItems:"center",marginBottom:10},children:ch})}'
)

_M1 = 'function vm({variant:e,uploads:t=[],setUploads:n=()=>{}}){'
_M2 = '[dzSF,dzSFs]=x.useState(""),[dzEta,dzEtas]=x.useState([]),'
_M3 = ('onClick:()=>{i(C);dzSFs("")},style:{height:26,padding:"0 10px",'
       'background:o===C?')
_M4 = 'const Lfs=(L)=>{'
_M5 = (',o==="Audio"&&r.jsxs("div",{style:{marginBottom:14,display:"grid",'
       'gap:10},children:[')
_M6 = ('r.jsxs("div",{style:{padding:"8px 10px"},children:[r.jsx("div",'
       '{style:{fontSize:11.5,color:"var(--ink-strong)",'
       'fontFamily:"var(--f-mono)",whiteSpace:"nowrap",overflow:"hidden",'
       'textOverflow:"ellipsis"},children:C.name})')
_M7 = 'var tout=[],srcA="";function fermer(){'
_M8 = ('var vus=tout.filter(function(im){return(!q'
       '||im.filename.toLowerCase().indexOf(q)>=0)'
       '&&(!srcA||String(im.source||"inconnu")===srcA)});')
_M9 = ('function dzChips(){var bar=hote.querySelector(".dzlp-chips");'
       'if(!bar)return;')
_M10 = ('.dzlp-case{border:1px solid var(--stroke,#20262d);border-radius:9px;'
        'overflow:hidden;background:var(--bg-base,#0a0c0f);cursor:pointer;'
        'padding:0;text-align:left;height:123px}')
_M11 = '\'"><img loading="lazy" src="/api/images/\''

PATCHES = [
    ("M1-helpers", _M1, HELPERS + _M1),
    ("M2-etat", _M2, _M2 + '[dzMF,dzMFs]=x.useState({tag:"",note:0,teinte:""}),'),
    ("M3-reset-onglet", _M3,
     'onClick:()=>{i(C);dzSFs("");dzMFs({tag:"",note:0,teinte:""})},'
     'style:{height:26,padding:"0 10px",background:o===C?'),
    # LE POINT : le filtre entre dans Lfs, donc il s'applique AUSSI au repli
    # de démo `vo[o]` — une liste de démo ne survit plus à un filtre actif.
    ("M4-filtre", _M4, _M4 + "L=__dzMetaFiltre(L,dzMF);"),
    ("M5-rangée", _M5, ",__dzMetaChips(o,T,dzMF,dzMFs)" + _M5),
    ("M6-carte", _M6, _M6 + ',r.jsxs("div",{style:{display:"flex",'
     'alignItems:"center",gap:6,marginTop:4},children:['
     'r.jsx("span",{onClick:function(ev){ev.stopPropagation();'
     'var v=Number(C.note||0)>=1?0:5;__dzLibPatch(C.name,{note:v,fav:!!v},'
     'function(){C.note=v;C.fav=!!v})},style:{cursor:"pointer",fontSize:12,'
     'color:Number(C.note||0)>0?"var(--amber)":"var(--ink-muted)"},'
     'children:Number(C.note||0)>0?"★":"☆"}),'
     'r.jsx("span",{style:{fontSize:9.5,color:"var(--ink-muted)",'
     'whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},'
     'children:((C.tags||[]).map(function(t){return"#"+t}).join(" "))})]})'),
    ("M7-picker-etat", _M7, 'var tout=[],srcA="",tagA="";function fermer(){'),
    ("M8-picker-filtre", _M8,
     "var vus=tout.filter(function(im){return(!q"
     "||im.filename.toLowerCase().indexOf(q)>=0)"
     '&&(!srcA||String(im.source||"inconnu")===srcA)'
     "&&(!tagA||(im.tags||[]).indexOf(tagA)>=0)});"),
    ("M9-picker-chips", _M9, _M9 + "var tg={};tout.forEach(function(im){"
     "(im.tags||[]).forEach(function(t){tg[t]=(tg[t]||0)+1})});"),
    ("M10-picker-css", _M10, _M10.replace("height:123px}", "height:141px}")
     + '+".dzlp-etoile{display:block;height:18px;line-height:18px;'
       'padding:0 7px;font-size:11px;color:var(--ink-muted,#5d6b7a)}"+'
       '".dzlp-etoile.on{color:var(--amber,#f0b429)}"+"'),
    ("M11-picker-case", _M11,
     '\'"><span class="dzlp-etoile\'+(im.note>0?" on":"")+\'">\''
     '+(im.note>0?"★":"☆")+\'</span><img loading="lazy" src="/api/images/\''),
]
```

**Note sur M10** : dans le bundle, `_M10` est suivi de `+".dzlp-case:hover{…}"` ; le remplacement referme donc la concaténation par `+"`. La parité des deltas et `node --check` prouvent que la chaîne parse.

- [ ] **Étape 5 : appliquer, mesurer, prouver que ça parse.**

```powershell
python scripts/patch_bundle_libmeta.py --check
python scripts/patch_bundle_libmeta.py --deltas
python scripts/patch_bundle_libmeta.py
Copy-Item frontend/dist/assets/index-BEOJX8L5.js "$env:TEMP/b.mjs" -Force
node --check "$env:TEMP/b.mjs"
```

Attendu : `[libmeta] applicable sur …` puis `11 ancres OK, marqueur absent, 11 sondes aux comptes` ; `[libmeta] delta +N car / +M o` (reporter N et M dans `SPEC_CHAR_DELTA`/`SPEC_BYTE_DELTA` **avant** l'application) ; `OK - bundle patché` avec la taille passant de `1395299` à `1395299 + M` octets ; **aucune sortie** de `node --check` (silence = le module parse).

- [ ] **Étape 6 : vert, et la hauteur mesurée dans le vrai DOM.**

Run : `python tests/test_library_meta_bundle.py` → `3 passed`.

Puis, **navigateur ouvert sur l'application** (le backend tourne déjà chez l'utilisateur), ouvrir un sélecteur de Bibliothèque et exécuter dans la console :

```js
[document.querySelectorAll('.dzlp-case').length,
 document.querySelector('.dzlp-case').offsetHeight,
 document.querySelector('.dzlp-etoile').offsetHeight]
```

Attendu : `[N, 141, 18]` avec `N > 0`. **`141` et `18`, pas `0` ni `2`** : une case à 2 px est le piège mesuré du 28/08 — les nœuds sont là, la rangée est effondrée.

- [ ] **Étape 7 : commit.**

```bash
git add scripts/patch_bundle_libmeta.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_meta_bundle.py
git commit -F msg.txt   # sujet : library : P1 ecran - etoile, tags et filtres, patcher libmeta
```

## Tâche 3 — P2 serveur : les projets

**Files :** Create `backend/app/services/library_projects.py` ; Modify `backend/app/services/storage.py` (après `LibraryAsset`), `backend/app/services/library_index.py` (`noter`), `backend/app/api/routes.py`. Test : `backend/tests/test_library_projets.py`.

- [ ] **Étape 1 : mesurer ce qui existe comme « ensemble ».**

Run : `python -c "import pathlib;s=pathlib.Path('backend/app/services/storage.py').read_text('utf-8');print([l.split('\"')[1] for l in s.splitlines() if '__tablename__' in l])"`
Attendu : les 12 tables. **Aucune n'est un ensemble d'assets** — `vector_doc_links` lie un chapitre à un document, pas un projet. Le POURQUOI des deux tables neuves.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_projets.py` (en-tête patron) :

```python
def test_un_projet_traverse_les_categories():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        await init_db()
        (pathlib.Path(_tmp, "images") / "gen_a.png").write_bytes(_png())
        async with _cl() as cl:
            p = (await cl.post("/api/library/projets",
                               json={"nom": "Campagne Abysses"})).json()
            assert p["id"].startswith("proj_"), p
            r = await cl.post(f"/api/library/projets/{p['id']}/items", json={
                "items": [{"ref": "gen_a.png", "kind": "image"},
                          {"ref": "job-1234", "kind": "render"}]})
            assert r.json()["ajoutes"] == 2, r.json()
            d = (await cl.get(f"/api/library/projets/{p['id']}")).json()
            assert {i["kind"] for i in d["items"]} == {"image", "render"}, d
            p2 = (await cl.post("/api/library/projets",
                                json={"nom": "Deck Oracle"})).json()
            await cl.post(f"/api/library/projets/{p2['id']}/items",
                          json={"items": [{"ref": "gen_a.png", "kind": "image"}]})
            ou = (await cl.get("/api/library/projets?ref=gen_a.png")).json()
            assert len(ou["projets"]) == 2, ou            # un asset dans N projets
            r2 = await cl.post(f"/api/library/projets/{p2['id']}/items",
                               json={"items": [{"ref": "gen_a.png", "kind": "image"}]})
            assert r2.json()["ajoutes"] == 0, r2.json()   # idempotent
            await cl.request("DELETE", f"/api/library/projets/{p2['id']}/items",
                             json={"refs": ["gen_a.png"]})
            assert (await cl.get(f"/api/library/projets/{p2['id']}")).json()["items"] == []

    asyncio.run(scenario())


def test_le_projet_actif_range_les_productions():
    """Sans ce hook, « ranger » resterait un geste manuel après coup."""
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_projects as LP
        await init_db()
        async with _cl() as cl:
            p = (await cl.post("/api/library/projets", json={"nom": "Nuit"})).json()
            await cl.put("/api/library/projets/actif", json={"id": p["id"]})
            assert (await cl.get("/api/library/projets/actif")).json()["id"] == p["id"]
            await LP.ranger_dans_actif(["gen_z.png"], "image")
            d = (await cl.get(f"/api/library/projets/{p['id']}")).json()
            assert [i["ref"] for i in d["items"]] == ["gen_z.png"], d
            await cl.put("/api/library/projets/actif", json={"id": ""})
            await LP.ranger_dans_actif(["gen_y.png"], "image")   # no-op silencieux
            assert len((await cl.get(
                f"/api/library/projets/{p['id']}")).json()["items"]) == 1

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_projets.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : les deux tables.** Dans `storage.py`, après `class LibraryAsset` :

```python
class LibraryProject(Base):
    """Bibliothèque (03/09) — un PROJET : campagne, chapitre, deck. Il contient
    des assets de TOUTES les catégories ; la catégorie devient un filtre à
    l'intérieur. Table neuve : create_all suffit."""
    __tablename__ = "library_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))
    couleur: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)


class LibraryProjectItem(Base):
    """L'appartenance d'un asset à un projet : n:n, PK composite — l'unicité
    de la paire est TENUE PAR LA BASE, pas par une garde applicative. `ref` =
    filename pour un fichier, job_id pour un rendu / 3D / sprite : exactement
    les clés que les onglets de l'écran manipulent déjà."""
    __tablename__ = "library_project_items"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                            index=True)
    ref: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(12), default="image")
    added_at: Mapped[datetime] = mapped_column(DateTime,
                                               default=datetime.utcnow)
```

- [ ] **Étape 5 : le service.** Créer `backend/app/services/library_projects.py` :

```python
# -*- coding: utf-8 -*-
"""Projets de la Bibliothèque (P2 du plan 2026-09-03-plan-library).

Un projet contient des assets de TOUTES les catégories ; la catégorie
redevient un filtre à l'intérieur. Un asset appartient à N projets. `ref` est
le filename pour un fichier, le job_id pour un rendu / 3D / sprite.

Le PROJET ACTIF est une ligne d'`atelier_settings` (clé
`library_projet_actif`) : le patron de `global_style`. Ranger dans l'actif est
OPTIONNEL et silencieux — comme l'index de provenance, ce hook ne fait jamais
échouer la route (ni la génération payée) qui l'appelle.
"""
from __future__ import annotations

from uuid import uuid4

from loguru import logger
from sqlalchemy import select

CLE_ACTIF = "library_projet_actif"


def _tables():
    from app.services.storage import (AtelierSetting, LibraryProject,
                                      LibraryProjectItem,
                                      async_session_factory)
    return (AtelierSetting, LibraryProject, LibraryProjectItem,
            async_session_factory)


async def creer(nom: str, couleur: str | None = None) -> dict:
    _A, P, _I, S = _tables()
    nom = " ".join(str(nom or "").split()).strip()[:120]
    if not nom:
        raise ValueError("Le nom du projet est vide.")
    pid = "proj_" + uuid4().hex[:8]
    async with S() as s:
        s.add(P(id=pid, nom=nom, couleur=couleur))
        await s.commit()
    return {"id": pid, "nom": nom, "couleur": couleur}


async def lister(ref: str | None = None) -> list[dict]:
    """Tous les projets, ou seulement ceux qui contiennent `ref` — c'est la
    question « où sert cet asset ? », posée par la fiche (P4)."""
    _A, P, I, S = _tables()
    async with S() as s:
        q = select(P)
        if ref:
            q = q.join(I, I.project_id == P.id).where(I.ref == ref)
        projets = list((await s.execute(q.order_by(P.created_at.desc()))).scalars())
        cnt: dict[str, int] = {}
        for (pid,) in (await s.execute(select(I.project_id))).fetchall():
            cnt[pid] = cnt.get(pid, 0) + 1
    return [{"id": p.id, "nom": p.nom, "couleur": p.couleur,
             "n": cnt.get(p.id, 0)} for p in projets]


async def contenu(pid: str) -> dict:
    _A, P, I, S = _tables()
    async with S() as s:
        p = await s.get(P, pid)
        if p is None:
            raise KeyError(pid)
        res = await s.execute(select(I.ref, I.kind).where(I.project_id == pid)
                              .order_by(I.added_at.desc()))
        items = [{"ref": r, "kind": k} for r, k in res.fetchall()]
    return {"id": p.id, "nom": p.nom, "couleur": p.couleur, "items": items}


async def ajouter(pid: str, items: list[dict]) -> int:
    """Rend le nombre RÉELLEMENT ajouté : re-poser un item existant vaut 0, et
    c'est ce que le banc mesure (l'idempotence est une promesse)."""
    _A, P, I, S = _tables()
    n = 0
    async with S() as s:
        if await s.get(P, pid) is None:
            raise KeyError(pid)
        for it in items or []:
            ref = str((it or {}).get("ref") or "").strip()[:255]
            if not ref or await s.get(I, (pid, ref)) is not None:
                continue
            s.add(I(project_id=pid, ref=ref,
                    kind=str((it or {}).get("kind") or "image")[:12]))
            n += 1
        await s.commit()
    return n


async def retirer(pid: str, refs: list[str]) -> int:
    _A, _P, I, S = _tables()
    n = 0
    async with S() as s:
        for ref in refs or []:
            row = await s.get(I, (pid, str(ref)))
            if row is not None:
                await s.delete(row); n += 1
        await s.commit()
    return n


async def actif() -> str:
    A, _P, _I, S = _tables()
    async with S() as s:
        row = await s.get(A, CLE_ACTIF)
        return (row.value or "") if row is not None else ""


async def poser_actif(pid: str) -> str:
    A, _P, _I, S = _tables()
    async with S() as s:
        row = await s.get(A, CLE_ACTIF)
        if row is None:
            row = A(key=CLE_ACTIF); s.add(row)
        row.value = str(pid or "")
        await s.commit()
    return str(pid or "")


async def ranger_dans_actif(refs, kind: str = "image") -> int:
    """Hook des producteurs. Aucun projet actif = no-op. Toute panne est
    avalée : ranger ne fait jamais échouer une génération payée."""
    try:
        pid = await actif()
        if not pid:
            return 0
        return await ajouter(pid, [{"ref": str(r), "kind": kind}
                                   for r in (refs or [])])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_projects.ranger_dans_actif ignoré: {e}")
        return 0
```

- [ ] **Étape 6 : les routes, et le rangement automatique.** Dans `routes.py`, six routes qui n'appellent que le service : `POST /library/projets` (`ValueError` → 400 avec le message tel quel), `GET /library/projets` (`ref` optionnel, rend `{"projets": [...]}`), `GET`/`PUT /library/projets/actif`, `GET /library/projets/{pid}` (`KeyError` → 404 `f"Projet inconnu : {pid}"`), `POST` et `DELETE /library/projets/{pid}/items`.

**Ordre FastAPI** : `/library/projets/actif` DOIT précéder `/library/projets/{pid}`, sinon `actif` est capturé comme `pid` — la règle déjà écrite pour `/audio/meta` avant `/audio/{filename}` (`routes.py`).

Et dans `LI.noter`, juste après le `commit` :

```python
        # P2 : ce qui est produit pendant qu'un projet est actif y entre. Un
        # seul site, parce que les 15 producteurs passent tous par ici.
        from app.services import library_projects as LP
        await LP.ranger_dans_actif([Path(str(n)).name for n in files], kind)
```

- [ ] **Étape 7 : vert, commit.** Run : `python tests/test_library_projets.py` puis `python tests/test_library_meta.py`
Attendu : `2 passed` puis `4 passed`.

```bash
git add backend/app/services/storage.py backend/app/services/library_projects.py backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_library_projets.py
git commit -F msg.txt   # sujet : library : P2 serveur - projets, appartenance n vers n, projet actif
```

## Tâche 4 — P2 écran : le patcher `libproj`

**Files :** Create `scripts/patch_bundle_libproj.py`. Test : `backend/tests/test_library_projets_bundle.py`.

- [ ] **Étape 1 : mesurer les quatre ancres sur le bundle POST-`libmeta`.** Le script de T2 étape 1, avec :

```
Audio:[],Favoris:[],"Établi":[]};function __dzFavGet(){
function __dzSendTo(m,onClose){try{var items=[];
r.jsx(le,{icon:"search",placeholder:"Search assets
const Lfs=(L)=>{L=__dzMetaFiltre(L,dzMF);
```

Attendu : `1` sur chaque. Les trois premières sont mesurées `×1` le 03/09 et `libmeta` n'y touche pas ; la quatrième est le texte que `libmeta` vient de laisser — si elle vaut `0`, `libmeta` n'est pas appliqué : arrêter et l'appliquer d'abord.

- [ ] **Étape 2 : le banc rouge.** `backend/tests/test_library_projets_bundle.py`, même en-tête que le banc-miroir de T2 :

```python
def test_le_miroir_bundle_projets():
    s = BUNDLE.read_text("utf-8")
    assert s.count("__dzProjets") == 3, s.count("__dzProjets")
    assert s.count("__dzProjFiltre") == 2, s.count("__dzProjFiltre")
    assert s.count("Projets:[]") == 1, s.count("Projets:[]")
    # 2 = le PUT du projet actif (J3) et le POST d'items (J4) ; la lecture
    # `/api/library/projets` n'a pas de barre finale et ne compte pas ici
    assert s.count("library/projets/") == 2, s.count("library/projets/")
    for probe, want in (("__dzMetaChips", 2), ("__dzSendTo", 2),
                        ('"Établi"', 2), ("__dzLibPicker", 10)):
        assert s.count(probe) == want, (probe, s.count(probe))
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_projets_bundle.py` → `assert 0 == 3`, code 1.

- [ ] **Étape 4 : le patcher.** Copie de `patch_bundle_libprov.py`. `TAG = "libproj"`, `MARKER = "__dzProjets"`, `MARKER_ATTENDU = 3`, `STABLE_PROBES` du patron **plus** `("libmeta", "__dzMetaChips", 2)`. Quatre greffes :

- `J1-onglet` : `Audio:[],Favoris:[],"Établi":[]};function __dzFavGet(){` → `Audio:[],Favoris:[],"Établi":[],Projets:[]};function __dzFavGet(){`. Le littéral `"Établi"` est **ré-écrit à l'identique** : le compte `("Établi", 2)` de `patch_bundle_etabli.py` tient, et le banc le pin.
- `J2-état + filtre` : `const Lfs=(L)=>{L=__dzMetaFiltre(L,dzMF);` → `const Lfs=(L)=>{L=__dzMetaFiltre(L,dzMF);L=__dzProjFiltre(L,dzProjA);` ; l'état `[dzProjA,dzProjAs]=x.useState("")` s'ajoute derrière `[dzMF,dzMFs]=x.useState({tag:"",note:0,teinte:""}),`. `__dzProjFiltre(L,pid)` rend `L` tel quel si `pid` est vide, sinon filtre sur l'appartenance chargée par `__dzProjets()`.
- `J3-sélecteur d'en-tête` : ancre `r.jsx(le,{icon:"search",placeholder:"Search assets` → insérer **avant** lui un `<select>` peint par `__dzProjets()` (`GET /api/library/projets`) et qui écrit par `PUT /api/library/projets/actif`.
- `J4-cible du menu` : `function __dzSendTo(m,onClose){try{var items=[];` → ajouter une entrée « 📁 Projet… » qui `POST /api/library/projets/{pid}/items` avec `{ref: nom, kind: m.kind}` ; le `pid` vient du projet actif, ou d'un `window.prompt` listant les projets quand aucun n'est actif.

- [ ] **Étape 5 : appliquer, prouver.** Run : `--check`, `--deltas`, application, puis `node --check` sur la copie `.mjs`.
Attendu : `4 ancres OK, marqueur absent, 12 sondes aux comptes` ; `OK - bundle patché` ; silence de `node`.

- [ ] **Étape 6 : vert, commit.** Run : `python tests/test_library_projets_bundle.py` puis `python tests/test_library_meta_bundle.py`
Attendu : `1 passed`, puis `3 passed` — les pins de `libmeta` tiennent.

```bash
git add scripts/patch_bundle_libproj.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_projets_bundle.py
git commit -F msg.txt   # sujet : library : P2 ecran - onglet Projets, projet actif, cible du menu
```

## Tâche 5 — P3 : la lignée pour tout asset (le serveur ; l'écran est T6 de l'Établi)

**Files :** Modify `backend/app/services/library_index.py` (signature de `noter`), `backend/app/api/routes.py:4544`, `:8946`, `:8976`, `:1228`, `:1529`, plus la route de lignée. Test : `backend/tests/test_library_lignee.py`.

**Ce que cette tâche ne fait PAS, et c'est le point.** Le repli sous la mère et la comparaison côte à côte sont la **tâche 10 de `2026-09-03-plan-etabli.md`** (tag `lignee`), premier lot de P3 défini par « Task 6 — la Bibliothèque hiérarchique » de `2026-09-01-etabli-plaque-et-extraction.md`. Ici on généralise le **modèle de données** pour que ce repli, le jour où il est là, ait de quoi replier autre chose que les productions de l'Établi. **Zéro octet de bundle.**

- [ ] **Étape 1 : mesurer les producteurs qui connaissent déjà leur mère.**

Run : `grep -n "LI.noter" backend/app/api/routes.py`
Attendu : 14 sites. **Quatre** ont la mère sous la main sans rien changer d'autre : `/images/process` (`body["filename"]`, et `body["op"]` donne la relation pour les 8 opérations du cœur), la finition (`fn`), `/assets/3d` et `/assets/sprite` (`image_filename`). Le POURQUOI de la portée : on n'en réécrit pas 14, on en instrumente 4 et l'on ouvre la porte pour les autres.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_lignee.py` (en-tête patron) :

```python
def test_la_retouche_ecrit_sa_mere_et_sa_relation():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        (pathlib.Path(_tmp, "images") / "gen_mere.png").write_bytes(_png(64, 64))
        await LI.noter(["gen_mere.png"], "generation")
        async with _cl() as cl:
            r = await cl.post("/api/images/process",
                              json={"op": "crop", "filename": "gen_mere.png",
                                    "ratio": "9:16"})
            fille = r.json()["images"][0]
            c = await LI.carte()
            assert c[fille]["parent_filename"] == "gen_mere.png", c[fille]
            assert c[fille]["relation"] == "crop", c[fille]
            lg = (await cl.get("/api/library/lignee/gen_mere.png")).json()
            assert lg["racine"] == "gen_mere.png", lg
            assert [e["filename"] for e in lg["enfants"]] == [fille], lg
            lg2 = (await cl.get(f"/api/library/lignee/{fille}")).json()
            assert lg2["racine"] == "gen_mere.png", lg2   # on remonte à la mère

    asyncio.run(scenario())


def test_une_boucle_de_lignee_ne_pend_pas():
    """Un cycle de `parent` est une donnée possible (deux éditions croisées) :
    la remontée est BORNÉE, elle ne boucle pas et le DIT."""
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        for n in ("a.png", "b.png"):
            (pathlib.Path(_tmp, "images") / n).write_bytes(_png())
        await LI.editer("a.png", {"parent_filename": "b.png", "relation": "edit"})
        await LI.editer("b.png", {"parent_filename": "a.png", "relation": "edit"})
        async with _cl() as cl:
            r = await cl.get("/api/library/lignee/a.png")
            assert r.status_code == 200 and r.json()["cycle"] is True, r.text

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_lignee.py` → `assert None == 'gen_mere.png'`, code 1.

- [ ] **Étape 4 : `noter` apprend la lignée.** Deux paramètres nommés — les 14 appelants d'aujourd'hui continuent de marcher **sans être touchés** :

```python
async def noter(files, source: str, kind: str = "image",
                job_id: str | None = None, deck_id: str | None = None,
                doc_id: str | None = None, parent: str | None = None,
                relation: str | None = None) -> None:
```

et, dans la boucle, avant le `commit` :

```python
                if parent is not None:
                    mere = Path(str(parent)).name
                    # Une image ne descend pas d'elle-même : une opération qui
                    # réécrit EN PLACE rendrait le même nom, et la remontée
                    # tournerait en rond dès la première lecture.
                    row.parent_filename = mere if mere and mere != nom else None
                if relation is not None:
                    row.relation = str(relation)[:24] or None
```

- [ ] **Étape 5 : les quatre producteurs disent leur mère.** `routes.py:4544` :

```python
            await LI.noter(out["images"], "retouche",
                           parent=Path(str(body.get("filename") or "")).name,
                           relation=str(body.get("op") or "")[:24])
```

Même forme ailleurs : finition → `parent=fn, relation="upscale"` (et `"upscale_ai"` pour la variante payante) ; `/assets/3d` → `parent=body["image_filename"], relation="mesh"` ; `/assets/sprite` → `parent=body["image_filename"], relation="sprite"`.

- [ ] **Étape 6 : la route de lignée.** Dans `routes.py` :

```python
@router.get("/library/lignee/{filename}")
async def library_lignee(filename: str):
    """L'arbre d'un asset : on REMONTE jusqu'à la racine, puis on descend.

    La remontée est bornée à 32 pas et rend `cycle: true` si elle s'arrête sur
    un nom déjà vu — un `parent_filename` en cycle est une donnée possible,
    pas un bug à supposer absent."""
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    safe = Path(filename).name
    async with async_session_factory() as s:
        res = await s.execute(select(
            LibraryAsset.filename, LibraryAsset.parent_filename,
            LibraryAsset.relation, LibraryAsset.source, LibraryAsset.job_id))
        lignes = {r[0]: {"filename": r[0], "parent": r[1], "relation": r[2],
                         "source": r[3], "job_id": r[4]} for r in res.fetchall()}
    racine, vus, cycle = safe, {safe}, False
    for _ in range(32):
        p = (lignes.get(racine) or {}).get("parent")
        if not p or p not in lignes:
            break
        if p in vus:
            cycle = True
            break
        vus.add(p)
        racine = p
    enfants, file_, vus2 = [], [racine], {racine}
    while file_:
        cour = file_.pop(0)
        for nom, l in lignes.items():
            if l["parent"] == cour and nom not in vus2:
                vus2.add(nom); enfants.append(l); file_.append(nom)
    return {"racine": racine, "cycle": cycle,
            "noeud": lignes.get(safe) or {"filename": safe}, "enfants": enfants}
```

- [ ] **Étape 7 : vert, commit.** Run : `python tests/test_library_lignee.py` puis `python -m pytest tests/test_library_provenance.py -q`
Attendu : `2 passed`, puis aucune régression (les 14 appels d'origine n'ont pas changé de forme).

```bash
git add backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_library_lignee.py
git commit -F msg.txt   # sujet : library : P3 serveur - lignee pour tout asset, remontee bornee
```
Corps : rappeler que le repli sous la mère est la tâche 10 du plan Établi (tag `lignee`), **pas** re-planifié ici.

## Tâche 6 — P4 serveur : la fiche complète

**Files :** Create `backend/app/services/library_fiche.py` ; Modify `backend/app/api/routes.py`. Test : `backend/tests/test_library_fiche.py`.

- [ ] **Étape 1 : mesurer les jointures d'usage disponibles.**

Run : `grep -n "image_filename\|source_image\|ref_image\|sketch_image\|face_image\|inspiration_images" backend/app/services/storage.py`
Attendu : sept colonnes, cinq tables. C'est exactement « où cet asset sert-il », **sans inventer un journal d'usage**.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_fiche.py` :

```python
def test_la_fiche_dit_recette_derives_usages_et_cout():
    import asyncio

    async def scenario():
        from app.services.storage import (JobRecord, ScheduledPost,
                                          async_session_factory, init_db)
        from app.services import library_index as LI
        await init_db()
        for n in ("gen_m.png", "gen_f.png"):
            (pathlib.Path(_tmp, "images") / n).write_bytes(_png())
        async with async_session_factory() as s:
            s.add(JobRecord(id="job-1", status="done", image_filename="gen_m.png",
                            final_prompt="poulpe de vitrail", seed=4242,
                            provider="seedance", duration_s=5,
                            video_model="seedance-2.5", title="Trone"))
            s.add(ScheduledPost(id="post-1", title="Drop", channels="x",
                                source_image="gen_m.png", status="draft"))
            await s.commit()
        await LI.noter(["gen_m.png"], "generation", job_id="job-1")
        await LI.noter(["gen_f.png"], "retouche", parent="gen_m.png",
                       relation="crop")
        async with _cl() as cl:
            f = (await cl.get("/api/library/fiche/gen_m.png")).json()
        rec = {l["cle"]: l["valeur"] for l in f["recette"]}
        assert rec["prompt"] == "poulpe de vitrail", rec
        assert rec["graine"] == "4242" and rec["modele"] == "seedance-2.5", rec
        assert [d["filename"] for d in f["derives"]] == ["gen_f.png"], f
        assert {"table": "scheduled_posts", "id": "post-1",
                "libelle": "Drop"} in f["usages"], f["usages"]
        assert f["cout"]["assiette"] == 2, f["cout"]      # la mère + la fille
        assert f["rejouer"]["route"] == "/api/generate", f["rejouer"]
        assert [s_["titre"] for s_ in f["sections"]][:2] == ["Recette", "Droits"]

    asyncio.run(scenario())


def test_une_fiche_sans_job_ne_ment_pas():
    """Un import n'a ni recette ni coût : la fiche le DIT, elle n'invente pas
    des champs vides qui ressembleraient à une recette perdue."""
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        (pathlib.Path(_tmp, "images") / "perso.webp").write_bytes(_png())
        await LI.noter(["perso.webp"], "import")
        async with _cl() as cl:
            f = (await cl.get("/api/library/fiche/perso.webp")).json()
        assert f["recette"] == [] and f["rejouer"] is None, f
        assert f["cout"]["usd"] is None and f["cout"]["assiette"] == 1, f["cout"]

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_fiche.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : le module.** Créer `backend/app/services/library_fiche.py`, quatre fonctions d'assemblage, **une requête par table** :

- `recette(job)` → `[{cle, valeur}]` bâti sur les colonnes **non nulles** de `JobRecord` (`final_prompt` → `prompt`, `negative_prompt`, `seed` → `graine`, `video_model` → `modele`, `provider`, `duration_s`, `aspect_ratio`, `style`). Ce qui est nul **n'apparaît pas** : sinon une fiche d'import ressemblerait à une recette abîmée.
- `usages(nom)` → les sept jointures de l'étape 1, chacune `{table, id, libelle}`. `inspiration_images` est du JSON : lu sous `try` (une valeur abîmée n'est pas un usage, ce n'est pas une erreur).
- `cout(noms)` → `pricing.estimate` sur chaque job de la lignée, somme, plus `assiette` = le nombre d'assets comptés. Un job sans tarif renseigné rend `usd: None` **et** `assiette` quand même : la fiche affiche « coût partiel », jamais un zéro qui mentirait.
- `fiche(nom)` → `{filename, meta, recette, derives, usages, cout, rejouer, sections}` ; `rejouer` vaut `None` sans job, sinon `{route: "/api/generate", corps: {...}}`. **`sections` est la forme générique** que `libfiche` (T7) peint : `[{titre, lignes:[{cle, valeur, ton}]}]` — c'est ce qui rend P5 et D2 gratuits côté bundle.

- [ ] **Étape 5 : la route.**

```python
@router.get("/library/fiche/{filename}")
async def library_fiche(filename: str):
    """Tout ce qu'on sait d'un asset en une requête : recette rejouable,
    dérivés (P3), usages en aval (5 tables), coût cumulé de la lignée."""
    from app.services import library_fiche as LF
    safe = Path(filename).name
    if not safe or safe in (".", "..") or safe != filename:
        raise HTTPException(400, "Invalid filename")
    return await LF.fiche(safe)
```

- [ ] **Étape 6 : vert, commit.** Run : `python tests/test_library_fiche.py` → `2 passed`.

```bash
git add backend/app/services/library_fiche.py backend/app/api/routes.py backend/tests/test_library_fiche.py
git commit -F msg.txt   # sujet : library : P4 serveur - fiche complete, recette usages et cout cumule
```

## Tâche 7 — P4 écran : le patcher `libfiche`, générique par construction

**Files :** Create `scripts/patch_bundle_libfiche.py`. Test : `backend/tests/test_library_fiche_bundle.py`.

- [ ] **Étape 1 : mesurer les deux ancres sur le bundle POST-`libproj`.** Le script de T2 étape 1, avec :

```
}})]})}),s&&r.jsx("div",{style:{position:"absolute",inset:0,pointerEvents:"none",
r.jsx(se,{name:"close",onClick:()=>y(null)})]}),m.kind==="sprite2d"?
```

Attendu : `1 1` (mesuré le 03/09 ; ni `libmeta` ni `libproj` n'y touchent).

- [ ] **Étape 2 : le banc rouge.** `backend/tests/test_library_fiche_bundle.py` :

```python
def test_le_miroir_bundle_fiche():
    s = BUNDLE.read_text("utf-8")
    assert s.count("__dzFiche") == 3, s.count("__dzFiche")
    assert s.count("library/fiche/") == 1, s.count("library/fiche/")
    # LE POINT : le panneau ne connaît AUCUN nom de champ. Il peint
    # `sections`, donc P5 (droits) et D2 (notes) n'ajouteront pas un octet de
    # bundle. Un libellé métier ici serait une régression de conception.
    corps = s.split("function __dzFiche")[1][:1800]
    for interdit in ("licence", "auteur", "graine", "usages"):
        assert interdit not in corps, interdit
    for probe, want in (("__dzMetaChips", 2), ("__dzProjets", 3)):
        assert s.count(probe) == want, (probe, s.count(probe))
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_fiche_bundle.py` → `assert 0 == 3`, code 1.

- [ ] **Étape 4 : le patcher.** `TAG = "libfiche"`, `MARKER = "__dzFiche"`, `MARKER_ATTENDU = 3`, `STABLE_PROBES` + `("libmeta", "__dzMetaChips", 2)` + `("libproj", "__dzProjets", 3)`. Deux greffes :

- `F1-helper` : avant `function vm(`, un `__dzFiche(m)` qui, à l'ouverture du modal, appelle `fetch("/api/library/fiche/"+encodeURIComponent(m.name))` et peint `d.sections` — **une boucle sur `sections`, une boucle sur `lignes`, zéro nom de champ en dur** ; le `ton` d'une ligne (`"alerte"`) colore en `var(--amber)`, ce qui est la façon dont P5 affichera « licence inconnue » sans patch.
- `F2-appel` : `}})]})}),s&&r.jsx("div",{style:{position:"absolute",inset:0,pointerEvents:"none",` → `}}),__dzFiche(m)]})}),s&&r.jsx("div",{style:{position:"absolute",inset:0,pointerEvents:"none",`.

- [ ] **Étape 5 : appliquer, prouver, vert.** Run : `--check`, `--deltas`, application, `node --check`, puis `python tests/test_library_fiche_bundle.py`.
Attendu : `2 ancres OK, marqueur absent, 13 sondes aux comptes` ; `OK - bundle patché` ; silence de `node` ; `1 passed`.

- [ ] **Étape 6 : commit.**

```bash
git add scripts/patch_bundle_libfiche.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_fiche_bundle.py
git commit -F msg.txt   # sujet : library : P4 ecran - panneau de fiche generique, patcher libfiche
```

## Tâche 8 — P5 : licence, source, auteur (coût de bundle : zéro)

**Files :** Modify `backend/app/services/library_index.py`, `backend/app/services/library_fiche.py`, `backend/app/api/routes.py` (`/images/upload`, `/images/import-figma`, `/images/fetch`). Test : `backend/tests/test_library_droits.py`.

- [ ] **Étape 1 : mesurer les portes d'entrée externes.**

Run : `grep -n "LI.noter" backend/app/api/routes.py | grep -i "import\|figma\|2067\|4859"`
Attendu : trois sites — `upload_image` (`"import"`), `import_figma` (`"figma"`), `/images/fetch` (`"import_url"`). Ce sont les **seuls** endroits où un asset entre sans qu'on l'ait produit : les seuls où une licence peut être connue ou inconnue.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_droits.py` :

```python
def test_les_droits_entrent_a_l_import_et_l_inconnu_se_dit():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        async with _cl() as cl:
            await cl.post("/api/images/upload",
                          files={"file": ("perso.png", _png(), "image/png")})
            c = await LI.carte()
            assert c["perso.png"]["licence"] == "inconnue", c["perso.png"]
            f = (await cl.get("/api/library/fiche/perso.png")).json()
            d = [s for s in f["sections"] if s["titre"] == "Droits"][0]
            l = [x for x in d["lignes"] if x["cle"] == "licence"][0]
            assert l["ton"] == "alerte", l          # l'inconnu est VISIBLE
            await cl.patch("/api/library/asset/perso.png",
                           json={"licence": "CC0", "auteur": "moi"})
            f2 = (await cl.get("/api/library/fiche/perso.png")).json()
            d2 = [s for s in f2["sections"] if s["titre"] == "Droits"][0]
            assert all(x["ton"] != "alerte" for x in d2["lignes"]), d2

    asyncio.run(scenario())


def test_le_catalogue_de_demarrage_est_cc0_sans_qu_on_le_demande():
    """`starter_catalog` est CC0 (Kenney, module ligne 2) : la licence se pose
    seule, sinon 606 assets porteraient une alerte mensongère."""
    from app.services import library_index as LI
    assert LI.LICENCE_PAR_SOURCE["catalogue"] == "CC0"
    assert LI.LICENCE_PAR_SOURCE["import"] == "inconnue"
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_droits.py` → `assert None == 'inconnue'`, code 1.

- [ ] **Étape 4 : la table des licences par défaut.** Dans `library_index.py` :

```python
# P5 — ce qu'on SAIT de la licence à l'entrée, par source. « inconnue » est
# une VALEUR, pas une absence : la fiche l'affiche en alerte, et c'est le seul
# moyen qu'un asset importé ne passe pas pour libre de droits.
LICENCE_PAR_SOURCE = {
    "import": "inconnue",
    "import_url": "inconnue",
    "figma": "propriétaire",     # le fichier Figma de l'utilisateur
    "catalogue": "CC0",          # starter_catalog : Kenney, CC0
}
```

et dans `noter`, après la lignée : `if row.licence is None: row.licence = LICENCE_PAR_SOURCE.get(source)`.

Les routes d'import passent ce qu'elles savent : `import_figma` → `source_url=body["url"]` ; `/images/fetch` → `source_url` de la requête.

- [ ] **Étape 5 : la section « Droits ».** Dans `library_fiche.py`, une section de plus dans `sections`, avec `ton: "alerte"` quand `licence in (None, "", "inconnue")`. **Aucune ligne de bundle** : `libfiche` peint `sections` sans savoir ce qu'elles contiennent (assertion du banc de T7).

- [ ] **Étape 6 : vert, commit.** Run : `python tests/test_library_droits.py` puis `python tests/test_library_fiche_bundle.py`
Attendu : `2 passed` puis `1 passed` — **le bundle n'a pas bougé d'un octet**, ce que le second banc prouve.

```bash
git add backend/app/services/library_index.py backend/app/services/library_fiche.py backend/app/api/routes.py backend/tests/test_library_droits.py
git commit -F msg.txt   # sujet : library : P5 - licence source et auteur, l inconnu se dit
```

## Tâche 9 — P6 serveur : le tableau de nettoyage, la corbeille, le retour arrière

**Files :** Create `backend/app/services/library_clean.py` ; Modify `backend/app/services/library_index.py` (`reconcilier`), `backend/app/api/routes.py`. Test : `backend/tests/test_library_nettoyage.py`.

- [ ] **Étape 1 : mesurer le coût de l'empreinte.**

Run : `python -c "import hashlib,os,time;b=os.urandom(2*1024*1024);t=time.perf_counter();[hashlib.sha256(b).hexdigest() for _ in range(20)];print(round((time.perf_counter()-t)/20*1000,2),'ms',hasattr(hashlib,'file_digest'))"`
Attendu : `~1.17 ms True`. Donc 998 fichiers ≈ **1,2 s** : l'empreinte se calcule dans `reconcilier()` au boot, sans réglage ni bouton.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_nettoyage.py` :

```python
def test_le_tableau_dit_poids_doublons_orphelins_et_la_corbeille_revient():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        img = pathlib.Path(_tmp, "images")
        meme = _png(16, 16, (7, 7, 7))
        (img / "un.png").write_bytes(meme)
        (img / "deux.png").write_bytes(meme)          # doublon EXACT
        (img / "trois.png").write_bytes(_png(16, 16, (9, 9, 9)))
        await LI.reconcilier()
        await LI.noter(["fantome.png"], "generation")  # index sans fichier
        async with _cl() as cl:
            t = (await cl.get("/api/library/nettoyage")).json()
            assert t["poids"]["image"]["n"] == 3, t["poids"]
            grp = [g for g in t["doublons"] if len(g["fichiers"]) == 2][0]
            assert sorted(grp["fichiers"]) == ["deux.png", "un.png"], grp
            assert "fantome.png" in t["orphelins"]["index_sans_fichier"], t
            r = await cl.post("/api/library/corbeille",
                              json={"fichiers": ["deux.png"]})
            assert r.json()["deplaces"] == ["deux.png"], r.json()
            assert not (img / "deux.png").is_file()
            assert "deux.png" not in (await LI.carte())
            u = await cl.post("/api/library/corbeille/restaurer",
                              json={"fichiers": ["deux.png"]})
            assert u.json()["restaures"] == ["deux.png"], u.json()
            assert (img / "deux.png").read_bytes() == meme
            assert "deux.png" in (await LI.carte())    # l'index revient aussi

    asyncio.run(scenario())


def test_la_corbeille_refuse_de_sortir_du_magasin():
    """Un nom se REFUSE, il ne s'aplatit pas (piège hérité de l'Établi :
    `Path('..').name` vaut '..')."""
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        await init_db()
        async with _cl() as cl:
            r = await cl.post("/api/library/corbeille",
                              json={"fichiers": ["../../.env"]})
            assert r.status_code == 400 and "nom" in r.text.lower(), r.text

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_nettoyage.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : `reconcilier` pose l'empreinte.** Dans la boucle de `reconcilier`, pour chaque fichier ajouté **et** chaque ligne dont `sha256` est nul :

```python
                    # P6 — l'empreinte exacte, calculée UNE fois par fichier
                    # (1,17 ms / 2 Mio mesuré le 03/09 : 998 fichiers = 1,2 s
                    # au boot, sous le temps de démarrage de l'app).
                    try:
                        with p.open("rb") as fh:
                            emp = hashlib.file_digest(fh, "sha256").hexdigest()
                        taille = p.stat().st_size
                    except Exception:
                        emp, taille = None, None
```

- [ ] **Étape 5 : le service.** Créer `backend/app/services/library_clean.py` :

- `tableau()` → `{poids: {kind: {n, octets}}, doublons: [{sha256, octets, fichiers:[…]}], orphelins: {index_sans_fichier: […], fichier_sans_index: […]}, rates: [job_id…]}`. Les doublons sont les groupes de `sha256` à ≥ 2 lignes (un `GROUP BY`), les ratés les `JobRecord.status == "failed"`.
- `corbeille(noms)` → appelle **d'abord** `_journal_ecrire(entrees)`, qui écrit `_corbeille/_journal.json` (`{nom: {source, kind, tags, note, licence, …, quand}}`) en `.part` → `os.replace` (patron `sfx_service.record_meta`), **puis** déplace vers `settings.images_path.parent / "_corbeille"`, **puis** retire la ligne d'index. Dans cet ordre : un journal écrit après le déplacement ne saurait plus quoi remettre en base si l'écriture s'interrompait.
- `restaurer(noms)` → remet le fichier et **rejoue** la ligne d'index depuis le journal.
- La garde de nom : `if n != Path(n).name: raise ValueError(f"Nom de fichier invalide : {n!r}")`.

- [ ] **Étape 6 : les trois routes** (`GET /library/nettoyage`, `POST /library/corbeille`, `POST /library/corbeille/restaurer`) ; `ValueError` → 400 avec le message tel quel.

- [ ] **Étape 7 : vert, commit.** Run : `python tests/test_library_nettoyage.py` → `2 passed`.

```bash
git add backend/app/services/library_clean.py backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_library_nettoyage.py
git commit -F msg.txt   # sujet : library : P6 serveur - tableau de nettoyage, corbeille et retour arriere
```

## Tâche 10 — P6 écran : le patcher `libclean`

**Files :** Create `scripts/patch_bundle_libclean.py`. Test : `backend/tests/test_library_nettoyage_bundle.py`.

- [ ] **Étape 1 : mesurer les trois ancres APRÈS `libproj` et `libmeta`.** Le script de T2 étape 1, avec :

```
Audio:[],Favoris:[],"Établi":[],Projets:[]};function __dzFavGet(){
,__dzMetaChips(o,T,dzMF,dzMFs),o==="Audio"&&
const Lfs=(L)=>{L=__dzMetaFiltre(L,dzMF);L=__dzProjFiltre(L,dzProjA);
```

Attendu : `1 1 1`. **Un `0` sur la première dit que `libproj` n'est pas passé, sur les deux autres que `libmeta` ne l'est pas** : arrêter, appliquer le maillon manquant, recommencer.

- [ ] **Étape 2 : le banc rouge.** `backend/tests/test_library_nettoyage_bundle.py` :

```python
def test_le_miroir_bundle_nettoyage():
    s = BUNDLE.read_text("utf-8")
    assert s.count("__dzClean") == 3, s.count("__dzClean")
    assert s.count("Nettoyage:[]") == 1, s.count("Nettoyage:[]")
    assert s.count("library/corbeille") == 2, s.count("library/corbeille")
    for probe, want in (("__dzFiche", 3), ("__dzProjets", 3),
                        ("__dzMetaChips", 2), ('"Établi"', 2),
                        ("__dzLibPicker", 10)):
        assert s.count(probe) == want, (probe, s.count(probe))
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_nettoyage_bundle.py` → `assert 0 == 3`, code 1.

- [ ] **Étape 4 : le patcher.** `TAG = "libclean"`, `MARKER = "__dzClean"`, `MARKER_ATTENDU = 3`, `STABLE_PROBES` + les trois marqueurs d'ici déjà passés. Trois greffes : la clé `Nettoyage:[]` ajoutée à `vo` (le littéral `"Établi"` ré-écrit à l'identique) ; un helper `__dzClean()` qui lit `GET /api/library/nettoyage` et rend un tableau (poids par catégorie, groupes de doublons, orphelins, ratés) avec une case à cocher par ligne et **un** bouton « Mettre à la corbeille » (plus « Restaurer » sur le contenu de la corbeille) ; le rendu conditionnel `o==="Nettoyage"&&__dzClean(...)` inséré à l'ancre `,__dzMetaChips(o,T,dzMF,dzMFs),o==="Audio"&&`.

- [ ] **Étape 5 : appliquer, prouver, vert.** Run : `--check`, `--deltas`, application, `node --check`, `python tests/test_library_nettoyage_bundle.py`.
Attendu : `3 ancres OK, 14 sondes aux comptes` ; `OK - bundle patché` ; silence ; `1 passed`.

- [ ] **Étape 6 : commit.**

```bash
git add scripts/patch_bundle_libclean.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_nettoyage_bundle.py
git commit -F msg.txt   # sujet : library : P6 ecran - onglet Nettoyage, patcher libclean
```

## Tâche 11 — P7 : la couleur dominante en PIL (coût de bundle : zéro)

**Files :** Create `backend/app/services/library_color.py` ; Modify `backend/app/services/library_index.py`. Test : `backend/tests/test_library_couleur.py`.

- [ ] **Étape 1 : mesurer le coût réel, sur ce poste.**

```bash
python -c "
from PIL import Image; import time
im = Image.new('RGB', (1080, 1920)); px = im.load()
for y in range(1920):
    for x in range(1080): px[x, y] = ((x*7)%256, (y*3)%256, 40 if x<540 else 200)
t=time.perf_counter(); v=im.convert('RGB'); v.thumbnail((128,128), Image.Resampling.BILINEAR)
q=v.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
print(round((time.perf_counter()-t)*1000,1),'ms', v.size, len(q.getcolors()))"
```

Attendu (mesuré le 03/09, Pillow 12.2.0) : `~16.8 ms (72, 128) 8`. **998 images ≈ 17 s**, une fois, au boot. Le POURQUOI du calcul à l'indexation plutôt qu'à la demande (17 ms par vignette affichée).

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_couleur.py` :

```python
def test_la_couleur_dominante_et_sa_teinte():
    from app.services.library_color import dominante, teinte_de

    p = pathlib.Path(_tmp, "images", "rouge.png")
    Image.new("RGB", (64, 64), (200, 20, 20)).save(p)
    assert dominante(p) == ("#c81414", "rouge"), dominante(p)

    # Une image quasi neutre n'est pas rangée dans une teinte : la saturation
    # décide, sinon tout gris atterrirait en « rouge » (h = 0).
    p2 = pathlib.Path(_tmp, "images", "gris.png")
    Image.new("RGB", (64, 64), (128, 129, 128)).save(p2)
    assert dominante(p2)[1] == "neutre", dominante(p2)

    # La table est TOTALE : les 12 secteurs, aucun trou.
    assert {teinte_de(h, 0.9, 0.5) for h in range(0, 360, 5)} == {
        "rouge", "orange", "ambre", "jaune", "lime", "vert", "menthe",
        "cyan", "azur", "bleu", "violet", "magenta"}


def test_l_indexation_pose_la_couleur_et_la_facette_la_rend():
    import asyncio

    async def scenario():
        from app.services.storage import init_db
        from app.services import library_index as LI
        await init_db()
        Image.new("RGB", (32, 32), (20, 40, 200)).save(
            pathlib.Path(_tmp, "images", "bleu.png"))
        await LI.reconcilier()
        assert (await LI.carte())["bleu.png"]["teinte"] == "bleu"
        async with _cl() as cl:
            f = (await cl.get("/api/library/facettes")).json()
            assert {"valeur": "bleu", "n": 1} in f["teintes"], f
            im = (await cl.get("/api/images")).json()["images"]
        it = [i for i in im if i["filename"] == "bleu.png"][0]
        assert it["couleur"].startswith("#"), it

    asyncio.run(scenario())
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_couleur.py` → `ModuleNotFoundError: No module named 'app.services.library_color'`, code 1.

- [ ] **Étape 4 : le module.** Créer `backend/app/services/library_color.py` :

```python
# -*- coding: utf-8 -*-
"""Couleur dominante d'un asset (P7), en PIL pur.

Pas de numpy : le python embarqué est stdlib + Pillow. La recette est
`thumbnail(128) → quantize(8, MEDIANCUT) → getcolors()` — mesurée le
03/09/2026 sur ce poste (Pillow 12.2.0) à **16,8 ms** pour une image
1080x1920, donc ~17 s pour les 998 assets du magasin, une seule fois, à
l'indexation. À la demande, ce serait 17 ms par vignette affichée.

La teinte est rangée en 12 secteurs de 30 degres, PLUS « neutre » : sans ce
cas, un gris (saturation ~0, teinte 0) atterrirait dans « rouge » et le filtre
par teinte mentirait sur la moitié des captures d'écran.
"""
from __future__ import annotations

import colorsys
from pathlib import Path

from loguru import logger
from PIL import Image

_SECTEURS = ["rouge", "orange", "ambre", "jaune", "lime", "vert",
             "menthe", "cyan", "azur", "bleu", "violet", "magenta"]
_SAT_MIN = 0.18                # sous ce seuil, la teinte n'a pas de sens
_LUM_BORNES = (0.06, 0.94)     # le noir et le blanc ne sont pas des teintes


def teinte_de(h_deg: float, s: float, l: float) -> str:
    """Secteur de 30 degrés, ou « neutre ». TOTALE par construction : tout
    couple (h, s, l) rend une valeur, jamais None."""
    if s < _SAT_MIN or not (_LUM_BORNES[0] < l < _LUM_BORNES[1]):
        return "neutre"
    return _SECTEURS[int((h_deg % 360) // 30)]


def dominante(chemin: Path) -> tuple[str | None, str | None]:
    """(#rrggbb, teinte) de la couleur la plus PRÉSENTE après réduction.

    `getcolors()` sur l'image quantifiée rend (compte, index de palette) : on
    prend le compte le plus grand, pas le premier. Une image illisible rend
    (None, None) — l'indexation est un à-côté, elle ne casse pas son appelant.
    """
    try:
        with Image.open(chemin) as im:
            v = im.convert("RGB")
            v.thumbnail((128, 128), Image.Resampling.BILINEAR)
            q = v.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
            cols = q.getcolors()
            if not cols:
                return None, None
            _n, idx = max(cols, key=lambda c: c[0])
            pal = q.getpalette() or []
            r, g, b = pal[idx * 3:idx * 3 + 3]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_color.dominante({chemin.name}) ignorée: {e}")
        return None, None
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return f"#{r:02x}{g:02x}{b:02x}", teinte_de(h * 360, s, l)
```

- [ ] **Étape 5 : le branchement.** Dans `reconcilier()`, pour tout fichier `kind == "image"` dont `couleur` est nul : `row.couleur, row.teinte = dominante(p)`. Dans `noter`, même chose pour les fichiers fraîchement écrits, **sous `asyncio.to_thread`** : 16,8 ms dans la boucle d'événements bloqueraient toutes les requêtes du serveur pendant ce temps (même règle que `_etabli_productions`, `routes.py:9290`).

**Aucun octet de bundle** : la rangée `__dzMetaChips` de `libmeta` liste déjà les teintes présentes dans les items, parce qu'elle se peint sur les données et non sur une liste écrite en dur.

- [ ] **Étape 6 : vert, commit.** Run : `python tests/test_library_couleur.py` puis `python tests/test_library_meta_bundle.py`
Attendu : `2 passed` puis `3 passed` — bundle inchangé.

```bash
git add backend/app/services/library_color.py backend/app/services/library_index.py backend/tests/test_library_couleur.py
git commit -F msg.txt   # sujet : library : P7 - couleur dominante en PIL, teinte en 12 secteurs
```

---

# Lot 2 — différenciant

## Tâche 12 — D1a : la porte des embeddings image — mesurer, trancher, l'écrire

**Files :** Create `backend/app/services/image_search.py` (la façade seule) ; Modify `backend/app/config.py`, `backend/app/api/routes.py:3501`. Test : `backend/tests/test_library_recherche_porte.py`.

**Cette tâche ne devine rien.** Elle mesure, remplit une table, tranche, et écrit la décision dans la docstring du module. R9 a déjà mesuré une case : **fal n'a aucun endpoint d'embedding CLIP texte ↔ image** (fal.ai, 03/09/2026). Les autres sont à mesurer ici.

- [ ] **Étape 1 : les trois mesures, dans cet ordre.**

1. **Le modèle dans le backend.** Run : `python -c "import numpy"` puis `python -c "import torch"`
   Attendu : `ModuleNotFoundError` sur les deux → case **IMPOSSIBLE**, mesurée, pas supposée.
2. **Un fournisseur distant d'embeddings multimodaux.** `WebFetch url=https://ai.google.dev/gemini-api/docs/embeddings prompt="Does this API embed IMAGES (not only text)? Which model id, which dimension?"` puis `WebFetch url=https://platform.openai.com/docs/guides/embeddings prompt="Does this API accept image input? Which model, which dimension?"` → écrire le verdict **et la date** dans la table. R9 les classe « de mémoire, à vérifier » : tant que cette étape n'a pas tourné, aucune ligne du plan ne s'appuie dessus.
3. **Le service local.** Run : `python -c "import pathlib;print(pathlib.Path('tools/clapbox').exists())"`
   `2026-09-03-plan-son-vfx.md` tâche 11 pose `tools/clapbox/` et le **contrat HTTP** `GET /health` → `{"ok","model","dim"}`, `POST /embed/text`, `POST /embed/audio`. La question tranchée ici : un processus pour CLAP et CLIP, ou deux ? La réponse est **mesurée par la nature des modèles**, pas choisie : l'encodeur texte de CLAP et celui de CLIP sont deux modèles distincts, aucun vecteur n'est comparable d'une famille à l'autre. Donc **même contrat, même patron, port distinct** (`17495`) ; `tools/clapbox/` peut héberger les deux jeux de poids si l'utilisateur ne veut qu'un processus — un choix de déploiement, pas d'API.

Table à écrire dans la docstring du module (les cellules « distant » se remplissent à l'étape 1.2) :

| Voie | Coût | Exige | Verdict |
|---|---|---|---|
| modèle DANS le backend | 0 $ | torch + numpy embarqués | **IMPOSSIBLE** (mesuré : ni l'un ni l'autre) |
| service local « Clipbox » (`127.0.0.1:17495`) | 0 $ | un processus Python à part, ses poids | **RETENUE** (défaut) |
| endpoint distant | à mesurer (1.2) | une URL + une clé | **POSSIBLE**, même façade |
| via fal | — | — | **EXCLUE** : aucun endpoint CLIP texte↔image (fal.ai, 03/09/2026) |

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_recherche_porte.py` :

```python
def test_la_porte_dit_pourquoi_elle_est_fermee():
    from app.config import settings
    from app.services import image_search as IS
    IS._reach_cache.update(t=0.0, ok=False)
    settings.CLIPBOX_URL = "http://127.0.0.1:1"      # rien n'écoute
    settings.CLIP_REMOTE_URL = ""
    st = IS.status()
    assert st["ready"] is False, st
    assert "Clipbox" in st["hint"] and "CLIP_REMOTE_URL" in st["hint"], st
    assert IS.resolve_embedder() == "", IS.resolve_embedder()


def test_la_porte_s_ouvre_par_le_distant_sans_service_local():
    from app.config import settings
    from app.services import image_search as IS
    IS._reach_cache.update(t=0.0, ok=False)
    settings.CLIP_REMOTE_URL = "https://clip.test/v1"
    assert IS.resolve_embedder() == "remote", IS.resolve_embedder()
    assert IS.status()["ready"] is True
    settings.CLIP_REMOTE_URL = ""


def test_les_cles_sont_reglables_depuis_l_interface():
    """Sans cette liste blanche, la clé se pose à la main dans le .env — et
    VOICEBOX_URL est resté dans ce trou (mesuré le 03/09, config.py:82)."""
    import re
    s = (RACINE / "backend" / "app" / "api" / "routes.py").read_text("utf-8")
    bloc = re.search(r"_ALLOWED_ENV_KEYS = \{(.+?)\}", s, re.S).group(1)
    for k in ("CLIPBOX_URL", "CLIP_REMOTE_URL", "CLIP_REMOTE_KEY",
              "VOICEBOX_URL"):
        assert f'"{k}"' in bloc, k
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_recherche_porte.py` → `ModuleNotFoundError: app.services.image_search`, code 1.

- [ ] **Étape 4 : la façade.** Créer `backend/app/services/image_search.py` : **copie littérale du patron** de `voice_providers.py` — `CLIPBOX_DEFAULT_URL = "http://127.0.0.1:17495"`, `clipbox_url()`, `remote_url()`, `_reach(url)` (couture que le banc remplace), `_reach_cache` à TTL 5 s, `clipbox_reachable()`, `resolve_embedder()` (le local d'abord : gratuit), `embedder_url()`, `status()`, `available()` — avec la table de l'étape 1 en docstring et le `hint` :

```python
"Recherche par description indisponible : lance le service local Clipbox "
f"({clipbox_url()}, contrat identique à tools/clapbox/) ou renseigne "
"CLIP_REMOTE_URL dans Réglages → Clés."
```

Dans `config.py`, après `VOICEBOX_URL` : `CLIPBOX_URL: str = ""`, `CLIP_REMOTE_URL: str = ""`, `CLIP_REMOTE_KEY: str = ""`. Dans `_ALLOWED_ENV_KEYS`, ajouter les trois **plus `VOICEBOX_URL`** (mesuré absent le 03/09 ; si le plan Son & VFX l'a déjà ajouté, l'assertion passe quand même).

- [ ] **Étape 5 : vert, commit.** Run : `python tests/test_library_recherche_porte.py` → `3 passed`.

```bash
git add backend/app/services/image_search.py backend/app/config.py backend/app/api/routes.py backend/tests/test_library_recherche_porte.py
git commit -F msg.txt   # sujet : library : D1a - la porte CLIP, mesuree et tranchee
```

## Tâche 13 — D1b : l'index, la recherche par description, « comme celle-ci »

**Files :** Modify `backend/app/services/image_search.py`, `backend/app/api/routes.py` ; Create `scripts/patch_bundle_libsearch.py`. Tests : `backend/tests/test_library_recherche.py`, `backend/tests/test_library_recherche_bundle.py`.

- [ ] **Étape 1 : mesurer le coût du cosinus, ici, sans numpy.**

```bash
python -c "
import random, time
from array import array
from operator import mul
random.seed(1); N, D = 998, 512
base=[array('f',[random.random() for _ in range(D)]) for _ in range(N)]
q=array('f',[random.random() for _ in range(D)])
t=time.perf_counter(); s=[(sum(map(mul,v,q)),i) for i,v in enumerate(base)]; s.sort(reverse=True)
print(round((time.perf_counter()-t)*1000,1),'ms')"
```

Attendu (mesuré le 03/09) : `~24.5 ms` pour 998 × 512, tri compris. **Le backend ne garde que des vecteurs** : c'est tenable, le modèle ne l'est pas.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_recherche.py` (en-tête patron) avec un **faux service** local (`http.server.ThreadingHTTPServer` dans un thread, répondant `/health`, `/embed/text`, `/embed/image` par des vecteurs déterministes ; `settings.CLIPBOX_URL` pointé sur son port). Six fonctions de test, une par promesse — **les noms comptent : la campagne de mutations (T16) les cible par `-k`** :

```python
def test_l_index_se_relit_a_l_identique():
    assert ix2.count() == ix.count() and ix2.model == ix.model, (ix2, ix)

def test_la_recherche_ordonne():
    assert [r["name"] for r in res][:2] == ["bleu.png", "azur.png"], res

def test_la_similarite_exclut_le_demandeur():
    assert all(x["name"] != "bleu.png" for x in sim) and len(sim) == 2, sim

def test_un_index_d_une_autre_dimension_est_ignore_pas_fatal():
    assert IS.Index.load().count() == 0 and "dim" in journal[-1], journal

def test_changer_de_modele_invalide_l_index():
    """Règle mesurée chez Immich (docs.immich.app, 03/09) : la ré-indexation
    est obligatoire au changement de modèle."""
    assert IS.reindex()["reindexes"] == 3, IS.reindex()

def test_porte_fermee_repli_propre_avec_la_raison():
    assert r.json()["hint"].startswith("Recherche"), r.json()
```

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_recherche.py` → `AttributeError: module 'app.services.image_search' has no attribute 'reindex'`, code 1.

- [ ] **Étape 4 : l'index et les trois opérations.** Dans `image_search.py` : `Index` (fichier `_clip_index.json` dans le dossier des images ; `model` et `dim` en tête ; vecteurs en base64 d'`array('f')`, `BYTEORDER = "little"`, **rejet avec avertissement** d'un index d'un autre boutisme ou d'une autre dimension, jamais une exception) ; `reindex(force=False)` (n'embarque que les fichiers absents ou dont le `sha256` — déjà calculé par P6 — a changé, et **tout** l'index si le modèle a changé) ; `search(texte, k)` ; `similar(filename, k)` (le demandeur exclu) ; `proches(seuil)` pour les doublons **proches** de P6.

- [ ] **Étape 5 : les quatre routes** — `GET /library/recherche/etat`, `POST /library/recherche/reindexer`, `GET /library/recherche?q=…`, `GET /library/recherche/similaires/{filename}` — chacune rendant le `hint` de la porte quand `resolve_embedder()` est vide, **jamais une 500**.

- [ ] **Étape 6 : le patcher `libsearch`.** `TAG = "libsearch"`, `MARKER = "__dzSearch"`, `MARKER_ATTENDU = 3`, `STABLE_PROBES` + les quatre marqueurs d'ici. Trois greffes : un commutateur « nom / description » à côté du champ de recherche de l'en-tête (ancre `r.jsx(le,{icon:"search",placeholder:"Search assets`, ×1 — `libproj` insère **avant** elle, donc elle est intacte : le re-mesurer) ; l'appel de `GET /library/recherche` en mode « description », avec le `hint` affiché **tel quel** si la porte est fermée ; une entrée « ≈ Comme celle-ci » dans le modal, sous le panneau de fiche.

- [ ] **Étape 7 : appliquer, prouver, vert, commit.** Run : `--check`, `--deltas`, application, `node --check`, puis les deux bancs.
Attendu : `OK - bundle patché` ; silence de `node` ; les deux bancs verts.

```bash
git add backend/app/services/image_search.py backend/app/api/routes.py scripts/patch_bundle_libsearch.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_recherche.py backend/tests/test_library_recherche_bundle.py
git commit -F msg.txt   # sujet : library : D1b - index CLIP, recherche par description et similarite
```

## Tâche 14 — D2 : les annotations horodatées

**Files :** Modify `backend/app/services/storage.py`, `backend/app/services/library_fiche.py`, `backend/app/api/routes.py` ; Create `scripts/patch_bundle_libnotes.py`. Tests : `backend/tests/test_library_notes.py`, `backend/tests/test_library_notes_bundle.py`.

Référence vérifiée (help.frame.io, 03/09/2026) : commentaires **horodatés** et **piles de versions**. La pile est déjà rendue par P3 ; ici on ajoute le commentaire au temps `t`.

- [ ] **Étape 1 : mesurer ce qui existe.** Run : `grep -rn "commentaire\|annotation" backend/app/services/storage.py`
Attendu : **rien**. Aucune table de commentaire dans le dépôt : la table est neuve, `create_all` suffit.

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_notes.py` (en-tête patron). Assertions : une note posée à `t_s=3.5` sur un rendu se relit avec **son instant dans le média** et **sa date d'écriture** ; le statut vaut `a_revoir` par défaut et n'accepte que `a_revoir|valide|rejete` (autre valeur → 400 **nommant les trois**) ; les notes d'un asset apparaissent dans une **section** de la fiche (donc zéro octet de bundle côté fiche) ; supprimer une note ne touche pas les autres ; une note sur une image a `t_s` à `None` et ce n'est pas une erreur.

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_notes.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : la table.** Dans `storage.py` :

```python
class LibraryNote(Base):
    """Annotation horodatée sur un asset (D2). `t_s` est l'instant DANS le
    média (None pour une image) ; `created_at` est l'instant où la note a été
    écrite. Les deux, parce que « revoir à 3,5 s » et « noté hier » ne
    répondent pas à la même question. Table neuve : create_all suffit."""
    __tablename__ = "library_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ref: Mapped[str] = mapped_column(String(255), index=True)
    t_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    texte: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(12), default="a_revoir",
                                        index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)
```

- [ ] **Étape 5 : trois routes** (`GET`/`POST /library/notes/{ref}`, `DELETE /library/notes/{ref}/{nid}`) et **une section de plus** dans `library_fiche.sections`.

- [ ] **Étape 6 : le patcher `libnotes`.** `MARKER = "__dzNotes"`, `MARKER_ATTENDU = 2`. Deux greffes : un champ de saisie sous le panneau de fiche, qui poste `{t_s: <currentTime de la balise video si présente, sinon null>, texte}` ; trois pastilles de statut. **Le mobile (R12) consomme les mêmes routes** — rien de plus à faire ici.

- [ ] **Étape 7 : appliquer, prouver, vert, commit.** Run : `--check`, `--deltas`, application, `node --check`, les deux bancs.

```bash
git add backend/app/services/storage.py backend/app/services/library_fiche.py backend/app/api/routes.py scripts/patch_bundle_libnotes.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_notes.py backend/tests/test_library_notes_bundle.py
git commit -F msg.txt   # sujet : library : D2 - notes et commentaires horodates, statut de revue
```

## Tâche 15 — D3 : la Bibliothèque comme table de montage des projets

**Files :** Modify `backend/app/services/library_projects.py`, `backend/app/api/routes.py` ; Create `scripts/patch_bundle_libtable.py`. Tests : `backend/tests/test_library_table.py`, `backend/tests/test_library_table_bundle.py`.

**Le POURQUOI, mesuré.** Les jointures de P4 disent « où sert cet asset ». D3 renverse la question : **le projet** dit ce qui, chez lui, est publié, monté, imprimé. Aucune donnée neuve — un regroupement, et c'est ce qu'aucune référence DAM vérifiée de R9 ne fait.

- [ ] **Étape 1 : mesurer les états atteignables.** Run : `grep -n "    status:" backend/app/services/storage.py`
Attendu : `jobs.status` et `scheduled_posts.status`. Trois états lisibles **sans écrire une colonne** : *monté* (un `job` `done` qui référence l'asset), *publié* (un `scheduled_post` `posted` qui le référence), *imprimé* (une production de l'Établi, `GET /api/etabli/productions`).

- [ ] **Étape 2 : le banc rouge.** Créer `backend/tests/test_library_table.py`. Assertions : `GET /api/library/projets/{pid}/etat` rend `{monte, publie, imprime, inutilise}` ; un asset dans **deux** états apparaît dans les deux ; **`inutilise` est le complément exact** — le banc l'assert comme une partition (`set(monte) | set(publie) | set(imprime) | set(inutilise) == set(refs)` et `inutilise` disjoint des trois), sinon un oubli de jointure passerait pour « rien à signaler ».

- [ ] **Étape 3 : rouge.** Run : `python tests/test_library_table.py` → `assert 404 == 200`, code 1.

- [ ] **Étape 4 : `etat_projet(pid)`** dans `library_projects.py` : trois requêtes, une partition, **aucune écriture**.

- [ ] **Étape 5 : la route** `GET /library/projets/{pid}/etat`, déclarée **après** `/library/projets/actif` — même piège d'ordre FastAPI qu'en T3.

- [ ] **Étape 6 : le patcher `libtable`.** `MARKER = "__dzTable"`, `MARKER_ATTENDU = 2`. Deux greffes dans l'onglet Projets posé par `libproj` : quatre colonnes (monté / publié / imprimé / inutilisé) et un compteur par colonne.

- [ ] **Étape 7 : appliquer, prouver, vert, commit.** Run : `--check`, `--deltas`, application, `node --check`, les deux bancs.

```bash
git add backend/app/services/library_projects.py backend/app/api/routes.py scripts/patch_bundle_libtable.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_library_table.py backend/tests/test_library_table_bundle.py
git commit -F msg.txt   # sujet : library : D3 - le projet dit ce qui est monte publie imprime
```

---

## Écarté

- **E1 — Reconnaissance de visages** : un seul utilisateur, des personnages générés ; la bible (R3) tient l'identité avec `ref_image`, `face_image` et `aliases` — la Bibliothèque n'a rien à reconnaître, et Immich la fait par un **second** modèle local (DBSCAN sur un modèle de reconnaissance, docs.immich.app, 03/09) pour une question déjà répondue ailleurs.
- **E2 — Droits façon DAM d'entreprise** (expiration de licence, workflow d'approbation multi-rôles) : utilisateur unique ; P5 (licence + source + auteur, avertissement si inconnue) et D2 (statut à revoir / validé / rejeté) couvrent le besoin réel sans inventer des rôles qui n'existent pas.

---

## Tâche 16 — la campagne de mutations

**Files :** Create `backend/tests/mutations_library.py` (patron : `backend/tests/mutations_plaque_slicer.py`).

**Ce que c'est.** Pas un test : `pytest` ne le collecte pas (le nom ne commence pas par `test_`) et `run-tests.ps1` ne le liste pas. Il se lance **à la main**, depuis `backend/`. Il mute les sources une à une, lance le banc ciblé, lit les tests rouges, et **remet le fichier à l'octet près** (assertion sur le sha256). Une mutation **VERTE est une assertion qui manque** — c'est l'argument de la revue.

- [ ] **Étape 1 : copier la mécanique.**

Run : `python -c "import pathlib;s=pathlib.Path('backend/tests/mutations_plaque_slicer.py').read_text('utf-8');print(len(s.splitlines()),'lignes',('rouges' in s),('sha256' in s))"`
Attendu : le compte de lignes, `True True`. Copier vers `backend/tests/mutations_library.py` et ne changer que la docstring, les constantes de bancs et la liste `M`. Seul changement de mécanique : `rouges` prend le banc en argument, la campagne couvrant neuf fichiers de test au lieu d'un.

```python
B_META, B_PROJ = "tests/test_library_meta.py", "tests/test_library_projets.py"
B_LIGN, B_FICHE = "tests/test_library_lignee.py", "tests/test_library_fiche.py"
B_DROITS, B_CLEAN = "tests/test_library_droits.py", "tests/test_library_nettoyage.py"
B_COUL, B_PORTE = "tests/test_library_couleur.py", "tests/test_library_recherche_porte.py"
B_RECH = "tests/test_library_recherche.py"


def rouges(banc, k):
    """Les tests rouges du banc ciblé — et si RIEN n'a tourné, on le dit.
    pytest sort 0 ou 1 quand il a tourné ; 2 à 5 quand la COLLECTE a cassé.
    Lue comme « aucun FAILED », une collecte cassée passerait pour une
    mutation VERTE alors que rien n'a été mesuré."""
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur
```

- [ ] **Étape 2 : écrire les mutations.** Chaque entrée : `(banc, fichier, ancien, nouveau, [tests attendus rouges])` — le dernier champ est passé à `-k`, donc un **fragment** du nom du test suffit. Les vingt-deux visent les décisions que ce plan a prises **exprès** :

```python
M = [
    # ── T0 : la migration, l'endroit où une base d'avant se perd ──────────
    (B_META, "backend/app/services/storage.py",
     '                               ("library_assets", LIBRARY_ASSETS_COLUMNS)):',
     "                               ):", ["les_colonnes_neuves"]),
    (B_META, "backend/app/services/storage.py",
     '    ("couleur", "VARCHAR(7)"), ("teinte", "VARCHAR(12)"),',
     '    ("couleur", "VARCHAR(7)"),', ["les_colonnes_neuves"]),
    # ── T0 : la garantie « jamais None » côté liste ───────────────────────
    (B_META, "backend/app/api/routes.py",
     '        it.tags = LI.tags_lus(connu.get("tags"))',
     '        it.tags = connu.get("tags")', ["carte_rend_un_dict"]),
    # ── T1 : la normalisation des tags (une seule plume d'écriture) ───────
    (B_META, "backend/app/services/library_index.py",
     '        s = " ".join(str(t).split()).strip().lower()[:32]',
     "        s = str(t)", ["patch_asset_ecrit_tags"]),
    (B_META, "backend/app/services/library_index.py",
     "        if s and s not in vus:", "        if s:",
     ["patch_asset_ecrit_tags"]),
    # ── T1 : les bornes de la note ────────────────────────────────────────
    (B_META, "backend/app/api/routes.py",
     "        if not 0 <= n <= 5:", "        if False:",
     ["patch_asset_ecrit_tags"]),
    # ── T1 : la ligne créée à la volée (le filet du boot ne suffit pas) ───
    (B_META, "backend/app/services/library_index.py",
     '            row = LibraryAsset(filename=nom, source=heuristique(nom),\n                               origin="heuristique")\n            session.add(row)',
     "            return {}", ["patch_asset_ecrit_tags"]),
    # ── T1 : l'idempotence de la reprise des favoris ──────────────────────
    (B_META, "backend/app/api/routes.py",
     '        if not (await LI.editer(nom, {}))["fav"]:', "        if True:",
     ["reprise_des_favoris"]),
    # ── T3 : l'unicité de la paire, tenue par la base ─────────────────────
    (B_PROJ, "backend/app/services/library_projects.py",
     "            if not ref or await s.get(I, (pid, ref)) is not None:",
     "            if not ref:", ["un_projet_traverse"]),
    # ── T3 : le no-op quand aucun projet n'est actif ──────────────────────
    (B_PROJ, "backend/app/services/library_projects.py",
     "        if not pid:\n            return 0", "        pass",
     ["le_projet_actif_range"]),
    # ── T5 : une image ne descend pas d'elle-même ─────────────────────────
    (B_LIGN, "backend/app/services/library_index.py",
     "                    row.parent_filename = mere if mere and mere != nom else None",
     "                    row.parent_filename = mere",
     ["la_retouche_ecrit_sa_mere"]),
    # ── T5 : la remontée bornée et le cycle dit ───────────────────────────
    (B_LIGN, "backend/app/api/routes.py",
     "        if p in vus:\n            cycle = True\n            break",
     "        pass", ["une_boucle_de_lignee"]),
    (B_LIGN, "backend/app/api/routes.py",
     "    for _ in range(32):", "    for _ in range(1):",
     ["la_retouche_ecrit_sa_mere"]),
    # ── T5 : la relation vient de l'op, pas d'une constante ───────────────
    (B_LIGN, "backend/app/api/routes.py",
     '                           relation=str(body.get("op") or "")[:24])',
     '                           relation="retouche")',
     ["la_retouche_ecrit_sa_mere"]),
    # ── T6 : la fiche ne fabrique pas de recette pour un import ───────────
    (B_FICHE, "backend/app/services/library_fiche.py",
     "    if job is None:\n        return []",
     "    if False:\n        return []", ["une_fiche_sans_job"]),
    # ── T8 : l'inconnu se dit ─────────────────────────────────────────────
    (B_DROITS, "backend/app/services/library_index.py",
     '    "import": "inconnue",', '    "import": "CC0",',
     ["les_droits_entrent"]),
    # ── T9 : la garde de nom REFUSE, elle n'aplatit pas ───────────────────
    (B_CLEAN, "backend/app/services/library_clean.py",
     '            raise ValueError(f"Nom de fichier invalide : {n!r}")',
     "            n = Path(n).name", ["la_corbeille_refuse"]),
    # ── T9 : le journal AVANT le déplacement ──────────────────────────────
    (B_CLEAN, "backend/app/services/library_clean.py",
     "    _journal_ecrire(entrees)\n", "", ["le_tableau_dit_poids"]),
    # ── T11 : le seuil de saturation (sans lui, tout gris est rouge) ──────
    (B_COUL, "backend/app/services/library_color.py",
     "    if s < _SAT_MIN or not (_LUM_BORNES[0] < l < _LUM_BORNES[1]):",
     "    if False:", ["la_couleur_dominante"]),
    # ── T11 : la dominante est la PLUS PRÉSENTE, pas la première ──────────
    (B_COUL, "backend/app/services/library_color.py",
     "            _n, idx = max(cols, key=lambda c: c[0])",
     "            _n, idx = cols[0]", ["la_couleur_dominante"]),
    # ── T12 : la porte fermée dit POURQUOI ────────────────────────────────
    (B_PORTE, "backend/app/services/image_search.py",
     '    if clipbox_reachable():\n        return "clipbox"',
     '    return "clipbox"', ["la_porte_dit_pourquoi"]),
    # ── T13 : la similarité exclut le demandeur ───────────────────────────
    (B_RECH, "backend/app/services/image_search.py",
     "        if nom == filename:\n            continue", "        pass",
     ["la_similarite_exclut"]),
]
```

- [ ] **Étape 3 : lancer la campagne.**

Run (depuis `backend/`) : `python tests/mutations_library.py`
Attendu : 22 lignes `[ n] ROUGE            <fichier> '<extrait>' -> ['<test>']  sha <a>=<a>`, puis un JSON de bilan. **Tout `sha <a>=<b>` avec `a != b` est un échec de remise : arrêter et restaurer par `git checkout --`.**

- [ ] **Étape 4 : traiter les vertes.**

Toute ligne `VERTE` nomme une assertion manquante. Pour chacune : écrire l'assertion dans le banc concerné, la voir rouge sous la mutation, verte sans elle, relancer **la seule** mutation par `python tests/mutations_library.py <n>`.
Attendu après traitement : `ROUGE` sur les 22, **0** `VERTE`, **0** `ERREUR(collecte)`.

- [ ] **Étape 5 : commit.**

```bash
git add backend/tests/mutations_library.py backend/tests/test_library_*.py
git commit -F msg.txt   # sujet : library : campagne de mutations - 22 mutants, aucune verte
```
Corps : dire combien d'assertions la campagne a fait naître, et lesquelles.

---

## Ce que ce plan laisse comme dettes, nommées

1. **L'ordre `lignee` / `libmeta`.** Les deux touchent le même écran. **Aucune ancre n'est partagée** — mesuré le 03/09 — mais celui qui passe en second **re-mesure ses ancres** (étape 1 de T2, T4, T7, T10, T13). Ce n'est pas une supposition : c'est une étape du plan.
2. **Dix producteurs sur quatorze n'écrivent pas leur mère.** T5 instrumente les quatre qui la connaissent. Les autres (`atelier`, `matieres`, `cardforge`, `news`, `vectorlab`…) passeront `parent=` quand leur chantier les rouvrira : la signature est prête, et l'index ne ment pas — il rend `parent_filename: null`.
3. **Les decks ne sont pas en base** (`outputs/decks/`, aucune table SQL, `cards/contract.py:390`). P4 lit `library_assets.deck_id`, ce qui dit « cet asset sert dans ce deck » mais **pas** « à quelle carte ». Le balayage des JSON de deck serait un chantier Cardforge.
4. **`tools/clipbox/` n'est pas dans ce dépôt**, comme `tools/clapbox/`. Le plan livre la façade, le contrat HTTP et le repli parlant ; pas le processus ni les poids.
5. **La reprise des favoris est déclenchée par l'écran.** `POST /library/favoris/import` est idempotente, mais c'est le montage de `libmeta` qui l'appelle une fois si `localStorage.dz_fav_images` n'est pas vide. Ouvrir l'app dans un autre navigateur ne reprend pas les favoris de celui-là : le prix de ne pas fouiller un stockage client depuis le serveur.
