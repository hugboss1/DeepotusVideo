# Plateau hexagonal — Lot 1 : découpe du plateau — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Depuis le Photolab ou le Vectorlab, découper l'image ouverte en grille hexagonale ajustée (colonnes × rangées) et créer en un clic un jeu neuf « plateau » dans le Card Forge, sans toucher l'image d'origine.

**Architecture:** La géométrie de la grille et la découpe vivent côté serveur (`services/cards/plateau.py`, Pillow), derrière une route `POST /api/cards/decks/plateau` qui écrit les tuiles dans la Bibliothèque (lignée `plateau`) puis sème un jeu comme `depuis-images`, avec un champ racine `categorie: "plateau"`. Un dialogue partagé (`frontend/shared/dz-decoupe-hex*.js`) montre la grille sur l'image et calcule le cadrage ; le Photolab et le Vectorlab ne font que lui fournir dimensions, aperçu et nom d'image de la Bibliothèque.

**Tech Stack:** FastAPI, Pillow, pytest (python embarqué, lanceur `__main__`), JS vanilla en modules ES, bancs node (`*.test.mjs`).

**Spec:** `docs/superpowers/specs/2026-11-08-plateau-masques-hexagonaux-design.md` (validée le 08/11 ; sections « Lot 1 » et « Précisions après relecture » points 3, 4, 5).

## Global Constraints

- TDD ; chaque tâche finit par ses bancs verts et un commit. Mutations sur les règles neuves (au moins : partition des pixels, bornes, nettoyage en cas d'échec, conservation de `categorie`).
- Preuve sur le backend de preuve **8799** uniquement, jamais 8765 ; aucune dépense IA dans ce lot.
- Toute chaîne d'écran dans un dictionnaire `frontend/shared/i18n/*.json`, en FR **et** EN ; tout `HTTPException` neuf a son entrée dans `scripts/i18n_l10_traductions.json` puis `backend/app/i18n/erreurs.json` régénéré.
- `frontend/cardforge/js/{core,mod-face,mod-frame,mod-print}.js` sont **générés** depuis `scripts/i18n_l7/*.py` (`scripts/i18n_l7_generer.py`, `--check`) : modifier la saisie, jamais le JS.
- Charte `dz-charte.css` : angles vifs, aucun `border-radius`.
- Noms d'images : `app.services.noms.nom_image_valide`.
- Préfixe de fichier des tuiles : `tuile_` (le préfixe `plateau_` appartient au Plateau 3D du Studio).
- L'image source n'est **jamais** ouverte en écriture.
- Ne pas committer `.claude/launch.json` ni `.superpowers/`.

## Review Focus

1. **Image source très petite ou très allongée** (ex. 300 × 2000 px pour 6 × 4 tuiles 90 mm) : la découpe doit réussir avec le zoom couvrant, et le dialogue doit afficher la résolution effective sous 300 ppp avec son avertissement — jamais une tuile vide ou transparente dans la zone de coupe. Test : Tâche 2 (`test_image_minuscule_couvre_toutes_les_tuiles`).
2. **Image avec transparence ou en mode P / LA / CMYK** : les tuiles doivent sortir en RGBA sans fond noir inattendu. Test : Tâche 2 (`test_modes_d_image`).
3. **Même image découpée deux fois** : deux jeux, deux jeux de tuiles, aucun fichier écrasé. Test : Tâche 3 (`test_deux_decoupes_n_ecrasent_rien`).
4. **Échec en pleine écriture** (disque plein à la 7e tuile) : ni tuile ni jeu ne restent. Test : Tâche 3 (`test_echec_a_mi_chemin_ne_laisse_rien`).
5. **Un jeu plateau rouvert et autosauvé par l'écran** garde `categorie` (l'écran ne l'envoie pas). Test : Tâche 4 (`test_categorie_survit_a_l_autosave`).

---

### Task 1: Géométrie de la grille (Python + miroir JS)

**Files:**
- Create: `backend/app/services/cards/plateau.py`
- Create: `frontend/shared/dz-decoupe-hex-logique.js`
- Test: `backend/tests/test_cards_plateau_grille.py`
- Test: `frontend/shared/qa/decoupe_hex_logique.test.mjs` (créer le dossier `qa` s'il n'existe pas)

**Interfaces:**
- Produces (Python, `plateau.py`):
  - `COTE_MAX = 30` ; `TUILES_MAX = 500` (= `depuis_images.IMAGES_MAX`).
  - `@dataclass(frozen=True) class Grille: fmt: str; colonnes: int; rangees: int; bleed_mm: float; centres_mm: tuple[tuple[int, int, float, float], ...]` (rang, colonne, x, y — **1-based**, ordre de lecture rangée par rangée) `; largeur_mm: float; hauteur_mm: float` (étendue des contours de coupe + 2 × fond perdu).
  - `grille(fmt: str, colonnes: int, rangees: int, bleed_mm: float | None = None) -> Grille` — `bleed_mm=None` = fond perdu natif du format. Lève `ValueError` (format non hexagonal, bornes).
  - `cadrage_couvrant(src_w: int, src_h: int, ext_w: float, ext_h: float, zoom: float = 1.0, x: float = 0.5, y: float = 0.5) -> tuple[float, float, float, float]` — rectangle (gauche, haut, largeur, hauteur) en pixels source, du rapport `ext_w/ext_h`. `zoom=1` = le plus grand rectangle de ce rapport contenu dans l'image ; `zoom>1` le divise ; `x`, `y` ∈ [0, 1] = position dans la course libre. `zoom<1` est ramené à 1 ; `x`, `y` bornés.
  - `ppp_effectif(rect_w_px: float, largeur_mm: float) -> float`.
- Produces (JS, ES module, `dz-decoupe-hex-logique.js`): `FORMATS_HEX` (`{hex_p50:{p:50,o:"pointe"},…, hex_f90:{p:90,o:"plat"}}`), `COTE_MAX`, `TUILES_MAX`, `grille(fmt, colonnes, rangees, bleedMm)` → `{centres:[{r,c,x,y}], largeurMm, hauteurMm}`, `cadrageCouvrant(srcW, srcH, extW, extH, zoom, x, y)` → `{x, y, w, h}`, `pppEffectif(rectW, largeurMm)`. Mêmes formules que Python.

Géométrie (mesure `p` de côté plat à côté plat, `h = 2p/√3`) :
- **pointe en haut** : pas horizontal `p`, pas vertical `0,75·h`, rangées paires (2e, 4e…) décalées de `+p/2` ; centre de (r, c) = `(b + p/2 + (c−1)·p + δ, b + h/2 + (r−1)·0,75·h)` avec `δ = p/2` si `r` est pair, `b` = fond perdu ; étendue = `colonnes·p + (p/2 si rangees > 1)` + 2b par `h + (rangees−1)·0,75·h` + 2b.
- **côté plat en haut** : transposée (colonnes paires décalées de `+p/2` vers le bas, pas horizontal `0,75·h`).

- [ ] **Step 1: Write the failing tests** (`test_cards_plateau_grille.py`)

```python
def test_pointe_6x4_90mm_etendue_et_centres():
    g = P.grille("hex_p90", 6, 4)
    h = 90 * 2 / math.sqrt(3)
    assert g.bleed_mm == 3.0 and len(g.centres_mm) == 24
    assert g.largeur_mm == pytest.approx(6 * 90 + 45 + 6)
    assert g.hauteur_mm == pytest.approx(h + 3 * 0.75 * h + 6)
    assert g.centres_mm[0] == pytest.approx((1, 1, 3 + 45, 3 + h / 2))
    assert g.centres_mm[6][:2] == (2, 1) and g.centres_mm[6][2] == pytest.approx(3 + 45 + 45)

def test_voisins_a_distance_p():          # jointifs : 6 voisins à p exactement, aucun plus près
    for fmt in ("hex_p50", "hex_f635"):
        g = P.grille(fmt, 4, 3)
        p = min(CT.geom(fmt, 300).trim_mm)
        ...  # min des distances entre centres == p à 1e-9 près ; le centre (2, 2) a exactement 6 voisins à p

def test_plat_est_la_transposee():
    a, b = P.grille("hex_p75", 3, 5), P.grille("hex_f75", 5, 3)
    assert a.largeur_mm == pytest.approx(b.hauteur_mm) and a.hauteur_mm == pytest.approx(b.largeur_mm)

def test_une_seule_rangee_sans_demi_decalage():
    assert P.grille("hex_p50", 3, 1).largeur_mm == pytest.approx(3 * 50 + 6)

@pytest.mark.parametrize("args", [("poker", 2, 2), ("hex_p50", 0, 2), ("hex_p50", 31, 1), ("hex_p50", 30, 17)])
def test_bornes(args):
    with pytest.raises(ValueError): P.grille(*args)

def test_cadrage_couvrant():
    assert P.cadrage_couvrant(2000, 1000, 2, 1) == pytest.approx((0, 0, 2000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1) == pytest.approx((500, 0, 1000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, x=0) == pytest.approx((0, 0, 1000, 1000))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, zoom=2, x=1, y=1) == pytest.approx((1500, 500, 500, 500))
    assert P.cadrage_couvrant(2000, 1000, 1, 1, zoom=0.2) == P.cadrage_couvrant(2000, 1000, 1, 1)

def test_ppp_effectif():
    assert P.ppp_effectif(3000, 254) == pytest.approx(300)
```

(`test_voisins_a_distance_p` : écrire le corps complet — `p` = `min(trim_mm)` du format ; distances entre tous les couples de centres ; `min == p` et chaque centre intérieur a exactement 6 voisins à `p`.)

Banc node `decoupe_hex_logique.test.mjs` : mêmes cas que ci-dessus avec les mêmes valeurs attendues, plus `FORMATS_HEX` identique à une table JSON écrite par le banc Python (le banc Python lit `dz-decoupe-hex-logique.js`, en extrait `FORMATS_HEX` par expression régulière et le compare à `contract.FORMATS` : `p = min(trim_mm)`, orientation).

- [ ] **Step 2: Run tests to verify they fail**

Run (depuis `backend/`) : `& $PY tests/test_cards_plateau_grille.py` puis `node ../frontend/shared/qa/decoupe_hex_logique.test.mjs`
Expected: FAIL (module absent).

- [ ] **Step 3: Implement `plateau.py` (géométrie) and `dz-decoupe-hex-logique.js`**

Lire `p` et l'orientation depuis `contract.FORMATS` / `geom()` ; aucun nombre de format recopié en Python. Lanceur `__main__` obligatoire dans le banc.

- [ ] **Step 4: Run tests to verify they pass** — mêmes commandes ; Expected: PASS.

- [ ] **Step 5: Commit** — `git commit -m "plateau : géométrie de la grille hexagonale, Python et miroir JS (lot 1)"`

---

### Task 2: Découpe des tuiles (Pillow)

**Files:**
- Modify: `backend/app/services/cards/plateau.py`
- Test: `backend/tests/test_cards_plateau_decoupe.py`

**Interfaces:**
- Consumes: `grille`, `cadrage_couvrant` (Task 1) ; `contract.geom(fmt, dpi, bleed_mm)` (`canvas_px`, `bleed_off_px`, `trim_px`).
- Produces: `decouper(src: PIL.Image.Image, g: Grille, cadrage: dict, dpi: int = 300) -> list[tuple[int, int, PIL.Image.Image]]` — (rang, colonne, tuile RGBA de taille `geom(fmt, dpi, bleed).canvas_px`), ordre de lecture. `cadrage = {"zoom", "x", "y"}`, défauts 1 / 0,5 / 0,5. Fonction pure : n'écrit rien.

Algorithme :
1. Convertir `src` en RGBA (mode P, LA, L, CMYK, RGB acceptés).
2. Rectangle `cadrage_couvrant(src.w, src.h, g.largeur_mm, g.hauteur_mm, …)` → rééchantillonné **une fois** (`LANCZOS`) à `(round(largeur_mm/25.4·dpi), round(hauteur_mm/25.4·dpi))` = l'image de travail `W`.
3. Pour chaque tuile : origine entière `(round(cx_px − canvas_w/2), round(cy_px − canvas_h/2))` ; recadrer `W` à la toile.
4. Masque alpha de la tuile : un pixel (centre de pixel, en coordonnées de `W`) est **dans la coupe** de la tuile `t` si `t` est le centre le plus proche parmi tous les centres de la grille (égalité : plus petit `(rang, colonne)`) ; il est **dans le fond perdu** s'il est hors de la coupe mais à l'intérieur du contour de fond perdu de `t` (`hexa.contour_toile_mm` décalé à la position de la tuile). Coupe ∪ fond perdu → alpha 255, le reste → 0.

- [ ] **Step 1: Write the failing tests**

```python
def _mire(w, h):   # chaque pixel a une couleur unique : (x % 256, y % 256, (x // 256) * 16 + y // 256)
    ...

def test_nombre_taille_et_ordre():
    t = P.decouper(_mire(1200, 900), P.grille("hex_p50", 3, 2), {})
    g = CT.geom("hex_p50", 300, 3.0)
    assert [(r, c) for r, c, _ in t] == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]
    assert all(im.size == g.canvas_px and im.mode == "RGBA" for _, _, im in t)

def test_partition_exacte_des_pixels():
    # recomposer : chaque pixel de W situé dans la COUPE d'une tuile est couvert par exactement une tuile (coupe),
    # et sa couleur est celle de W. Aucun pixel de coupe perdu, aucun dupliqué.
    ...

def test_fond_perdu_vient_des_pixels_voisins():
    # un pixel du fond perdu d'une tuile intérieure a la couleur de W au même endroit (pas un prolongement)
    ...

def test_hors_contour_transparent():
    # coins de la toile (hors contour de fond perdu) : alpha 0
    ...

def test_image_minuscule_couvre_toutes_les_tuiles():
    t = P.decouper(_mire(30, 200), P.grille("hex_p90", 6, 4), {})
    assert all(im.getpixel(_centre(im))[3] == 255 for _, _, im in t)

@pytest.mark.parametrize("mode", ["P", "LA", "L", "CMYK", "RGB", "RGBA"])
def test_modes_d_image(mode):
    ...  # la tuile (1,1) a alpha 255 au centre et une couleur non noire pour une mire non noire

def test_source_intacte():
    src = _mire(800, 600); avant = src.tobytes()
    P.decouper(src, P.grille("hex_f50", 2, 2), {"zoom": 1.7, "x": 0.1, "y": 0.9})
    assert src.tobytes() == avant
```

(Écrire les corps marqués `...` ; `_centre(im)` = milieu de la toile.)

- [ ] **Step 2: Run** `& $PY tests/test_cards_plateau_decoupe.py` — Expected: FAIL.
- [ ] **Step 3: Implement `decouper`** (numpy autorisé s'il est déjà une dépendance du backend ; sinon Pillow pur).
- [ ] **Step 4: Run** — Expected: PASS. Mutation : remplacer la règle « centre le plus proche » par « dans le contour de coupe » avec `<=` des deux côtés → `test_partition_exacte_des_pixels` doit rougir.
- [ ] **Step 5: Commit** — `"plateau : découpe des tuiles, partition exacte au centre le plus proche (lot 1)"`

---

### Task 3: Route `POST /api/cards/decks/plateau`

**Files:**
- Modify: `backend/app/services/cards/plateau.py` (router)
- Modify: `backend/app/services/cards/__init__.py` (inclure `plateau.router` AVANT `core`, comme `depuis_images`)
- Modify: `backend/app/services/library_index.py` (`_PREFIXES` : `("tuile_", "cardforge")`, avant `("tile_", "tuiles")` n'est pas nécessaire — préfixes distincts — mais placé avant `gen_`)
- Modify: `scripts/i18n_l10_traductions.json`, `backend/app/i18n/erreurs.json` (régénéré)
- Test: `backend/tests/test_cards_plateau_route.py`

**Interfaces:**
- Consumes: Tasks 1-2 ; `depuis_images._nom_valide`, `_verifie_presente`, `_CADRE_NU` ; `core.create_deck`, `core.patch_deck`, `core.delete_deck`, `core.clean_name` ; `library_index.noter`.
- Produces: `POST /api/cards/decks/plateau` — corps `{image: str, format: str|{fmt,…}, colonnes: int, rangees: int, cadrage?: {zoom, x, y}, name?: str, verso_commun?: str, dpi?: int}` → `{deck, tuiles: [noms], ppp: float}`. Tuiles nommées `tuile_<base>_<did8>_r{RR}c{CC}.png` (`<base>` = nom source sans extension ni préfixe `photolab_AAAAMMJJ-HHMMSS_`, passé par la même garde de nom ; `<did8>` = 8 derniers caractères de l'id du jeu ; `RR`, `CC` sur 2 chiffres). Jeu : `name` par défaut « Plateau — <base> » ; `format.fmt` hexagonal seulement (400 sinon) ; même ensemencement que `depuis_images._ensemencer` sauf `data = {columns: ["nom","art","dos","rang","colonne"], rows: [["plateau-01", tuile, dos, "1", "1"], …], map: {art: "art", dos: "back"}}` (numéro sur 2 chiffres, 3 au-delà de 99) et `categorie: "plateau"` (Task 4).

Ordre : valider tout (corps, image présente, verso présent, bornes de la grille, format hexagonal, `dpi` dans les bornes de `contract`) → ouvrir l'image source **en lecture** → `create_deck` → écrire les tuiles → `noter(tuiles, "cardforge", deck_id=did, parent=image, relation="plateau")` → `patch_deck`. Toute exception après `create_deck` : supprimer les tuiles écrites et le jeu, puis 500 (`OSError`) ou relancer. Découpe et écriture dans `asyncio.to_thread`.

- [ ] **Step 1: Write the failing tests** (même amorce d'environnement que `test_cards_depuis_images.py` : `_tmp`, `IMAGES_FOLDER`, `_api`, `_empreintes`)

```python
def test_cree_un_jeu_plateau_de_24_tuiles():
    r = _post(image="fond.png", format="hex_p90", colonnes=6, rangees=4)
    assert r.status_code == 200, r.text
    d = r.json(); deck = d["deck"]
    assert deck["categorie"] == "plateau" and deck["name"] == "Plateau — fond"
    assert deck["format"]["fmt"] == "hex_p90" and deck["frame"]["family"] == "none"
    assert deck["data"]["columns"] == ["nom", "art", "dos", "rang", "colonne"]
    assert deck["data"]["rows"][0][0] == "plateau-01" and deck["data"]["rows"][23][3:] == ["4", "6"]
    assert len(d["tuiles"]) == 24 and all((IMAGES / t).is_file() for t in d["tuiles"])
    assert re.fullmatch(r"tuile_fond_[0-9a-z]{8}_r01c01\.png", d["tuiles"][0])

def test_image_source_intacte():          # empreinte sha1 de fond.png identique avant/après

def test_lignee_plateau():                # lignée Bibliothèque : parent == "fond.png", relation == "plateau", source cardforge

def test_deux_decoupes_n_ecrasent_rien(): # deux POST identiques : 48 tuiles distinctes, 2 jeux, empreintes des 24 premières inchangées

def test_echec_a_mi_chemin_ne_laisse_rien(monkeypatch):
    # monkeypatch de l'écriture d'une tuile : OSError(28) à la 7e -> 500, aucun tuile_* dans IMAGES, nombre de jeux inchangé

@pytest.mark.parametrize("corps,code", [
    ({"format": "poker"}, 400), ({"colonnes": 0}, 400), ({"colonnes": 30, "rangees": 17}, 400),
    ({"image": "absente.png"}, 404), ({"image": "../x.png"}, 400), ({"verso_commun": "absent.png"}, 404),
    ({"cadrage": "x"}, 400)])
def test_refus_sans_rien_creer(corps, code):   # aucun jeu, aucune tuile

def test_messages_refus_traduits():
    # chaque `detail` neuf de plateau.py a une entrée dans backend/app/i18n/erreurs.json (fr et en)

def test_impression_hex_du_jeu_plateau():
    # GET /api/cards/{did}/print/hex/plan sur le jeu créé -> 200 (le chemin t421 accepte le jeu)
```

(Écrire les corps des tests décrits en commentaire.)

- [ ] **Step 2: Run** `& $PY tests/test_cards_plateau_route.py` — Expected: FAIL.
- [ ] **Step 3: Implement** la route, l'inclusion dans `__init__`, le préfixe `tuile_`, puis les entrées L10 (`scripts/i18n_l10_traductions.json`, régénération selon la procédure d'`AGENTS.md`).
- [ ] **Step 4: Run** le banc + `test_cards_depuis_images.py` + le banc L10 existant — Expected: PASS. Mutation : retirer la suppression des tuiles dans le `except` → `test_echec_a_mi_chemin_ne_laisse_rien` rougit.
- [ ] **Step 5: Commit** — `"plateau : route POST /api/cards/decks/plateau, tuiles en Bibliothèque avec lignée (lot 1)"`

---

### Task 4: Champ `categorie` du jeu, index et galerie

**Files:**
- Modify: `backend/app/services/cards/core.py` (`default_doc`, `normalize_deck`, `DECK_SUMMARY_KEYS`, `INDEX_VERSION`, entrées d'index)
- Modify: la saisie L7 qui produit la galerie de `frontend/cardforge/js/core.js` (`scripts/i18n_l7/coque.py` ou celle qui contient `galImages` — vérifier par `grep`), puis `python scripts/i18n_l7_generer.py`
- Modify: `frontend/shared/i18n/cartes.json` (clés `cartes.plateau.*`)
- Modify: la feuille de la galerie du Card Forge (badge, filtre ; angles vifs)
- Test: `backend/tests/test_cards_categorie.py`, et un cas ajouté au banc d'écran de la galerie existant

**Interfaces:**
- Produces: `CATEGORIES = ("plateau",)` dans `core.py`. Document : clé racine `categorie` **présente seulement** si sa valeur est dans `CATEGORIES` ; `normalize_deck` la garde, la jette sinon. `patch_deck` ne la reprend **pas** du corps client (seul le serveur la pose : `plateau.py` l'écrit directement dans le document via une fonction `core.poser_categorie(did, cat) -> dict | None`). `DECK_SUMMARY_KEYS = ("id", "name", "created", "updated", "categorie")` ; `INDEX_VERSION = 2` (l'ancien index est ignoré et reconstruit).
- Galerie : badge « Plateau » / « Board » sur la vignette d'un jeu `categorie == "plateau"` ; filtre « Tous / Plateaux » au-dessus de la grille.

- [ ] **Step 1: Write the failing tests**

```python
def test_categorie_gardee_et_filtree():
    assert core.normalize_deck({"id": "deck_abcdef12", "categorie": "plateau"})["categorie"] == "plateau"
    assert "categorie" not in core.normalize_deck({"id": "deck_abcdef12", "categorie": "pirate"})
    assert "categorie" not in core.default_doc("deck_abcdef12")

def test_categorie_survit_a_l_autosave():
    did = <jeu créé par POST /decks/plateau>
    core.patch_deck(did, {"name": "Mon plateau", "type": {"slots": []}})
    assert core.read_deck(did)["categorie"] == "plateau"

def test_client_ne_pose_pas_la_categorie():
    did = core.create_deck("x")["id"]
    core.patch_deck(did, {"categorie": "plateau"})
    assert "categorie" not in core.read_deck(did)

def test_resume_et_index():
    # GET /api/cards/decks : le résumé du jeu plateau porte "categorie": "plateau", un autre jeu "" ;
    # un index v1 présent sur disque est ignoré (reconstruit en v2) sans perdre de jeu
```

Banc d'écran : la source traduite de `core.js` contient le badge et le filtre, leurs clés existent en FR et EN dans `cartes.json`, `i18n_l7_generer.py --check` est vert, aucun rayon littéral.

- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** ; brancher `plateau.py` (Task 3) sur `core.poser_categorie`.
- [ ] **Step 4: Run** ces bancs + `test_cards_core.py` + `test_cards_plateau_route.py` — Expected: PASS. Mutation : laisser `patch_deck` reprendre `categorie` du corps → `test_client_ne_pose_pas_la_categorie` rougit.
- [ ] **Step 5: Commit** — `"cartes : catégorie « plateau » du jeu, index v2, badge et filtre de la galerie (lot 1)"`

---

### Task 5: Dialogue partagé « Découper en hexagones »

**Files:**
- Create: `frontend/shared/dz-decoupe-hex.js` (ES module)
- Create: `frontend/shared/dz-decoupe-hex.css` (sélecteurs sous `.dz-dh`, angles vifs)
- Create: `frontend/shared/i18n/decoupehex.json` (clés `decoupehex.*`, FR + EN) et son inscription dans l'assemblage des dictionnaires (suivre ce que fait un dictionnaire partagé existant, p. ex. `dialogue.json`, dans `dz-i18n-dico.js` / le script d'assemblage)
- Test: `frontend/shared/qa/decoupe_hex_dialogue.test.mjs`, `backend/tests/test_decoupe_hex_ecran.py`

**Interfaces:**
- Consumes: `dz-decoupe-hex-logique.js` (Task 1) ; route de la Task 3.
- Produces: `export async function ouvrirDecoupeHex({ largeur, hauteur, apercu, nomImage, fournirImage, T, fetch = window.fetch }) -> {deck, tuiles} | null`
  - `largeur`, `hauteur` : pixels de l'image du lab ; `apercu` : `HTMLCanvasElement` ou `ImageBitmap` dessinable ; `nomImage` : nom proposé pour le jeu ; `fournirImage: async ({ largeurMm, hauteurMm }) => string` : rend le nom de l'image dans la Bibliothèque, en recevant l'étendue de la grille choisie (appelé **au clic sur « Créer »**, jamais avant) ; `T(cle, vars)` : traduction.
  - Réglages : format (8 formats, libellé « 90 mm, pointe en haut »), colonnes et rangées (1..`COTE_MAX`, total ≤ `TUILES_MAX`), glisser pour déplacer l'image, molette ou curseur pour zoomer (jamais sous 1), ppp effectif affiché, avertissement sous 300 ppp, nom du jeu (« Plateau — <nomImage> »), verso commun facultatif (sélecteur d'image de la Bibliothèque existant ou champ nom), bouton « Créer le jeu plateau ».
  - Au succès : `window.open("/cardforge/?deck=" + encodeURIComponent(deck.id))` (vérifier le chemin réel du Card Forge dans l'application et l'utiliser) et retour `{deck, tuiles}`. Erreur serveur : phrase traduite dans le dialogue (le `detail` déjà traduit par L10), dialogue resté ouvert.
- Rendu de l'aperçu : image dessinée selon `cadrageCouvrant`, contours de coupe en trait plein, fond perdu non dessiné, compteur « 24 tuiles ».

- [ ] **Step 1: Write the failing tests**
  - Banc node (DOM simulé comme `frontend/cardforge/qa/depuis_images.test.mjs`) : le corps POSTé pour 6 × 4, `hex_p90`, zoom 1,4, x 0,2 est exactement `{image, format:"hex_p90", colonnes:6, rangees:4, cadrage:{zoom:1.4,x:0.2,y:0.5}, name:"Plateau — fond"}` ; `fournirImage` n'est appelé qu'une fois, au clic ; `colonnes=31` désactive « Créer » avec la phrase de borne ; un 400 serveur laisse le dialogue ouvert avec sa phrase ; ppp affiché = `pppEffectif` du cadrage courant ; l'avertissement apparaît à 299 et pas à 300.
  - Banc Python d'écran : toutes les clés `decoupehex.*` en FR et EN, mêmes variables, aucune orpheline ; aucune chaîne en dur dans `dz-decoupe-hex.js` ; aucun `border-radius` ni rayon littéral dans la feuille.
- [ ] **Step 2: Run** `node frontend/shared/qa/decoupe_hex_dialogue.test.mjs` et `& $PY tests/test_decoupe_hex_ecran.py` — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** — `"plateau : dialogue partagé « Découper en hexagones » (lot 1)"`

---

### Task 6: Branchement Photolab

**Files:**
- Create: `frontend/photolab/js/mod-plateau.js`
- Modify: `frontend/photolab/js/mod-menus.js` (nouvelle liste `INSERTIONS_PLATEAU = [{ chemin: ["Image"], apres: null, id: "pl.plateau.decouper", cle: "photolab.menu.decouper_hex" }]` ajoutée à la boucle de `construireMenus` ; `"pl.plateau.decouper"` dans `NECESSITE_DOC`)
- Modify: `frontend/photolab/js/core.js` ou le point d'initialisation des modules (appeler `initPlateau(PL)`)
- Modify: `frontend/photolab/index.html` (feuille `../shared/dz-decoupe-hex.css`)
- Modify: `frontend/shared/i18n/photolab.json` (`photolab.menu.decouper_hex`)
- Test: banc node de menus existant du Photolab (ajouter le cas), `backend/tests/test_photolab_plateau_ecran.py`

**Interfaces:**
- Consumes: `ouvrirDecoupeHex` (Task 5) ; `enregistrer()` de `mod-fichier.js` (l'exposer comme `PL.enregistrerBibliotheque` s'il n'est pas déjà accessible) ; `aSauvegarder(doc, revEnregistree, revOuverture)`.
- Produces: `PL.actions["pl.plateau.decouper"]` : ouvre le dialogue avec `largeur/hauteur` du document, `apercu` = le rendu courant du document (le canevas d'affichage ou la vignette que l'écran sait déjà produire), `nomImage` = `nomDocument(doc.name)`, `fournirImage` = **si le document n'a aucune modification depuis son ouverture et que son nom d'origine dans la Bibliothèque est connu de l'écran**, ce nom ; **sinon** `(await enregistrer()).filename` (un nouveau fichier, lignée `retouche`). Si l'écran ne connaît pas le nom d'origine, toujours enregistrer (consigner ce choix dans le rapport).

- [ ] **Step 1: Write the failing tests** — l'entrée apparaît dans Image (FR « Découper en hexagones… », EN « Cut into hexagons… »), grisée sans document, active avec ; l'action appelle `ouvrirDecoupeHex` avec les dimensions du document ; `fournirImage` appelle `enregistrer` quand le document est modifié et ne l'appelle pas sinon (si le nom d'origine est connu).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** + bancs de menus du Photolab existants — Expected: PASS.
- [ ] **Step 5: Commit** — `"photolab : Image › Découper en hexagones… vers un jeu plateau (lot 1)"`

---

### Task 7: Branchement Vectorlab

**Files:**
- Modify: `frontend/vectorlab/index.html` (bouton `#expPlateau` dans le panneau Export, à côté de `#expPng4`) et `frontend/vectorlab/js/mod-export.js` (câblage)
- Modify: `frontend/shared/i18n/vectorlab.json` (`vectorlab.export.plateau`, infobulle)
- Test: `frontend/vectorlab/qa/plateau.test.mjs`, ajout au banc d'écran du Vectorlab

**Interfaces:**
- Consumes: `ouvrirDecoupeHex` ; `exporterPNG(k, {suffixe})` (renvoie le nom déposé `vector_<docId>_plateau_<k>x.png`).
- Produces: clic sur `#expPlateau` → dialogue avec `largeur/hauteur = etat.doc.taille`, `apercu` = `rasteriser(1, false)` dessiné dans un canevas, `nomImage` = nom du document, `fournirImage` = `exporterPNG(k, {suffixe: "_plateau"})` avec `k = min(8192 / max(w, h), cible / w)` où `cible = ceil(largeurMm / 25.4 × 300)` (largeur en pixels donnant 300 ppp sur la grille choisie ; `largeurMm` reçu par `fournirImage`, cf. Task 5), export **opaque** (la case transparente n'est pas lue). La lignée vers le document passe par le nom `vector_<docId>_…` (pas de nouvelle route).

- [ ] **Step 1: Write the failing tests** — `k` pour un document 1000 × 700 et une grille 6 × 4 `hex_p90` (cible 300 ppp) ; borne 8192 respectée ; nom déposé conforme ; bouton présent, libellé FR/EN.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** + bancs existants du Vectorlab (export) — Expected: PASS.
- [ ] **Step 5: Commit** — `"vectorlab : Export › Découper en hexagones vers un jeu plateau (lot 1)"`

---

### Task 8: Assistant, documentation, preuve FR/EN

**Files:**
- Modify: `AGENTS.md` (route, module, dialogue partagé), `docs/agent/AGENT.md` (une ligne Card Forge / plateau ; respecter le plafond de taille testé par `test_agent_connaissance.py`)
- Modify: catalogue de l'assistant (skill `connaissance-agent` : fiches de l'entrée de menu Photolab, du bouton Vectorlab, du badge et du filtre de la galerie)
- Create: `docs/superpowers/preuves/2026-11-08-plateau-lot1/` (captures FR et EN)

- [ ] **Step 1:** Lancer la skill `connaissance-agent` pour les éléments visibles neufs ; bancs du catalogue verts.
- [ ] **Step 2:** Preuve sur **8799** (données jetables, aucune clé) : une image de test 3000 × 2000 importée dans la Bibliothèque ; depuis le Photolab, 6 × 4 `hex_p90` → jeu « Plateau — … » de 24 cartes ouvert dans le Card Forge, badge visible, filtre « Plateaux » ; depuis le Vectorlab, un document simple → 3 × 2 `hex_f50` ; empreinte de l'image source identique avant/après ; planche d'impression nid d'abeilles du jeu plateau affichée. Captures en FR puis en EN.
- [ ] **Step 3:** Suite complète des bancs touchés (cartes, photolab, vectorlab, i18n, L10, L7 `--check`, catalogue assistant) — Expected: tout vert.
- [ ] **Step 4: Commit** — `"plateau : fiches de l'assistant, AGENTS.md, preuve FR/EN (lot 1)"`

---

## Après ce lot

PR vers `main` ; fusion et installation **uniquement sur accord de l'utilisateur dans la session** (procédure d'installation habituelle, l'utilisateur relance). Les plans des lots 2 (masques) et 3 (IA) s'écrivent ensuite, à partir de la même spec.
