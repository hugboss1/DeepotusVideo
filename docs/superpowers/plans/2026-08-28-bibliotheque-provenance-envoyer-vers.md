# Bibliothèque robuste — provenance & classement + « Envoyer vers… »

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, session du 28/08, spawn task_fa6029e8). Steps use
> checkbox (`- [ ]`) syntax.

> Ordre utilisateur (verbatim) : « je veux pouvoir identifier dans les
> sections de la librairie ce qui est généré depuis chaque fonction :
> cardforge, images générations, rendus depuis les différentes sources de
> l'application par catégorie, réfléchis à comment marquer chaque
> génération issue de chaque fonction de l'application et recrée un
> système d'identifiant et de classement de la bibliothèque » ; et :
> « lorsque j'ouvre depuis la bibliothèque une image source, ou un rendu,
> je peux l'envoyer vers le générateur de sprite, je dois pouvoir
> sélectionner toutes les autres cibles de l'application : chapitre,
> montage, template, etc. ».

> **RELEVÉ (28/08) : CHANTIER LIVRÉ, DÉPLOYÉ, PROUVÉ EN RÉEL, NETTOYÉ.**
> T1-T2 : `library_assets` + `library_index.py` (noter/renommer/retirer/
> reconcilier/carte, hooks résilients), TOUS les producteurs notent au
> dépôt, réconciliation au boot ; banc `test_library_provenance.py`
> 8 tests RED d'abord, 12 fichiers voisins verts. T3 `libprov` (13
> ancres, deltas +2830/+2835) ; T4 `libsend` (4 ancres, +7457/+7568,
> pin print3d 2→3 commenté) ; `test_library_sendto.py` 3 tests ;
> node --check OK ×2. **Déployé** (7 fichiers sha-vérifiés, stop/
> relance, santé 2.5.0) — le boot a rétro-indexé les **998 assets réels**
> (934 generation, 56 inconnu, 4 vectorlab, 2 news, 1 atelier,
> 1 assets3d — tous `heuristique`, dits). **Preuves navigateur** :
> chips Images (« Tout (998) · ≈ Générateur (934) · … », 22 px, clic
> Vectorlab → 4/4 cases vector_*), chips Renders par provider
> (75 = 1+3+4+1+24+33+9, clic Heygen → 3 vidéos), chips du picker
> (998→4, chip active) ; menu « Envoyer vers… » 8 cibles image /
> 3 rendu / print3d (3D) / sheet (Sprites) : → Studio (nœud Image,
> Filename = le fichier), → Quick (« Start image | vector_… » affiché),
> → Template (Spatial compose au canevas, image câblée), → Bible
> (entité de test, PUT réel, inspirations = [fichier], toast),
> → Montage (clip posé sur la vraie timeline puis retiré par le bouton
> Annuler de l'éditeur), → Cardforge (toast « img:… copié » + iframe
> /cardforge/), → Scheduler ×2 (brouillons source_image ET job_id créés
> puis SUPPRIMÉS), copie de sheet arrivée **sourcée sprites/depot par le
> hook vivant** puis supprimée. Nettoyage vérifié aux endpoints (998
> images, 0 post/entité/sheet de banc, timeline restaurée). Limites
> dites : vignettes news écrites en thread = indexées au boot suivant
> (préfixe exact) ; l'entrée Sprite Lab du menu appelle le
> `__dzToSpriteLab` déjà prouvé de son chantier ; l'entrée Impression 3D
> ouvre le `window.prompt` mm existant (non cliqué au banc navigateur).

**Goal :** chaque asset de la Bibliothèque porte la FONCTION qui l'a
produit (table d'index alimentée au dépôt + rétro-remplissage honnête),
filtrable par chips dans l'écran Library ET le sélecteur `__dzLibPicker` ;
et un menu « Envoyer vers… » sur chaque image/rendu couvrant les cibles
réelles de l'app en réutilisant leurs mécanismes existants.

**Architecture :** une table SQLite neuve `library_assets` (patron
VectorDoc : create_all seul) + un service pur `library_index.py` (hooks
minuscules aux points d'écriture async, `noter_bg` = create_task) ; le
GET /api/images s'enrichit (additif) ; deux patchers bundle NEUFS en
queue de chaîne APRÈS libpicker (`libprov` puis `libsend`), greffes
additives à ancres uniques ; les renders gardent `jobs.provider` comme
provenance (déjà en base, déjà dans les items UI).

**Coût API : 0 $** (aucun tir fal/OpenAI/Meshy — tout est local).

---

## Inventaire MESURÉ (28/08) — qui dépose quoi dans la Bibliothèque

### Images (fichiers de `settings.images_path`)

| Producteur (fonction) | Point d'écriture | Nom produit | Le nom suffit-il ? |
|---|---|---|---|
| Générateur d'images (`POST /images/generate` — FLUX `_flux_generate`, OpenAI routes:3776, nano-banana `image_providers.generate`) | routes.py:3776/3805/3796 + image_providers.py:59 | `gen_<hex8>.png` | **NON** — préfixe partagé par 5 fonctions |
| Retouche (`POST /images/process` : crop/upscale/remove-bg/pixel/seamless/tile-preview/edit/variations) | routes.py:3841/3911/3892/3933/4006/4015 | `gen_<hex8>.png` | NON (même préfixe) |
| Material Forge (image de base d'une matière générée) | routes.py:6455-6463 | `gen_<hex8>.png` | NON |
| Planches Atelier (bible `POST /bible/entities/{id}/generate` : panneaux `gen_*` + `board_service` boards) | routes.py:4455-4660, board_service.py:188/224/265 | `gen_*` + `board_<hex8>.png` | partiel (`board_` oui, panneaux non) |
| Croquis storyboard (`POST /shots/{id}/sketch`) | routes.py:5181 | `gen_<hex8>.png` | NON |
| Cardforge (rescaper mise-au-ton → copie du gagnant vers la Library) | cards/face.py:2695-2697 | `gen_<hex8>.png` | NON |
| Import fichier (`POST /images/upload` — garde le nom du client) | routes.py:1356 | nom arbitraire | NON (sauf préfixes ci-dessous) |
| Vectorlab (exports PNG du client via `/images/upload`) | vectorlab → upload | `vector_<doc>_<k>x[_t].png` | OUI |
| Figma (`POST /images/import-figma`) | figma_import.py:71 | `figma_<clé>_<node>.png` | OUI |
| News (`POST /images/import-url` + vignettes scrapées) | routes.py:3706, news_service.py:326 | `news_<hex8|hash10>.*` | OUI |
| Import URL (`POST /images/fetch` — titre de news, slot Studio) | routes.py:4120 | `gen_<hex8>.<ext>` | NON |
| Sprite Lab (sheet → Library `POST /assets/sprite/{job}/save`) | routes.py:835 | `gen_sprite_<short>[_n].png` | OUI |
| Game Assets 3D (vue → Library `POST /assets/3d/{job}/shot/{i}/save`) | routes.py:535 | `shot_<short>_<i>[_n].png` | OUI |

Verdict mesuré : `gen_` recouvre à lui seul génération, retouche,
matières, planches, croquis, cardforge et fetch — **les noms seuls ne
peuvent pas classer la bibliothèque**. Un renommage utilisateur
(`/images/{f}/rename`, file-only) efface en prime tout préfixe.

### Renders (table `jobs`)

`jobs.provider` EXISTE déjà et est déjà renvoyé par `GET /jobs` :
seedance, heygen, composition, template, news, episode, animation,
asset3d, sprite2d, ugc, card3d, montage (pipeline.py:240/465/937/1013/
1222/787, routes.py:316/390/725/2055, forge3d.py:4060,
montage_service.py:1356). L'item Renders du bundle porte déjà
`provider:(C.provider||"").replace(/^./,maj)`. **Décision : AUCUNE
duplication en table — la provenance des rendus EST `jobs.provider`.**

### Audio

Magasin `images_path.parent / "audio"` (routes.py:1449), upload
`POST /audio/upload`, plus les pistes voix des jobs. Indexé a minima
(kind=`audio`, hook upload → `import`, reconcile → `inconnu`) ; PAS de
chips audio dans ce chantier (dit, YAGNI).

## Décisions (tranchées avant le code)

**D1 — Le marquage : table d'index `library_assets` (SQLite).**
```python
class LibraryAsset(Base):
    __tablename__ = "library_assets"
    filename: str = mapped_column(String(255), primary_key=True)
    source:   str = mapped_column(String(24), index=True)   # slug fonction
    kind:     str = mapped_column(String(12), default="image")  # image|audio
    origin:   str = mapped_column(String(12), default="depot")  # depot|heuristique
    job_id:   str|None = mapped_column(String(36), nullable=True)
    deck_id:  str|None = mapped_column(String(36), nullable=True)
    doc_id:   str|None = mapped_column(String(36), nullable=True)
    created:  datetime = mapped_column(DateTime, default=utcnow)
```
Table NEUVE → `create_all` suffit (patron VectorDocLink) ; zéro ALTER.
Elle vit dans deepotus.db → migre avec le kit export.

**Alternatives PESÉES et rejetées :** (a) sidecar JSON par fichier —
pollue le dossier (×996), aucune requête d'ensemble, se désynchronise au
moindre déplacement manuel ; (b) convention de nommage seule — MESURÉ
au-dessus : `gen_` est ambigu entre 7 fonctions et le rename efface tout ;
(c) métadonnées PNG (tEXt) — réécrit les octets (les recettes bible/seed
s'ancrent sur les fichiers), muet pour jpg/webp, illisible sans outil.
La table est le seul marquage qui classe l'EXISTANT sans toucher aux
octets et qui survit au renommage (la ligne migre avec).

**D2 — Vocabulaire des sources (slug stable → libellé UI) :**
`generation` (Générateur d'images), `retouche` (Retouche), `matieres`
(Material Forge), `atelier` (Atelier — planches & croquis), `cardforge`
(Cardforge), `vectorlab` (Vectorlab), `figma` (Figma), `news` (News),
`sprites` (Sprite Lab), `assets3d` (Game Assets 3D), `import` (Import
fichier), `import_url` (Import URL), repli `inconnu`. La carte
slug→libellé vit UNE fois dans `library_index.SOURCES` et est servie par
`GET /api/images` (chaque item porte `source`) — le front n'invente rien.

**D3 — Alimentation AU DÉPÔT : hooks minuscules, tous en contexte async.**
Service `backend/app/services/library_index.py` :
- `async noter(files, source, kind="image", job_id=None, deck_id=None,
  doc_id=None)` — upsert (merge) par filename ;
- `noter_bg(...)` — `asyncio.get_running_loop().create_task(...)` pour
  les sites sync-dans-la-boucle (no-op silencieux hors boucle) ;
- `heuristique(filename)` — préfixe → source : `gen_sprite_`→sprites,
  `vector_`→vectorlab, `figma_`→figma, `news_`→news, `board_`→atelier,
  `shot_`→assets3d, `gen_`→generation, sinon→inconnu ;
- `async reconcilier()` — scanne images/ (+ audio/) et insère les
  fichiers absents de la table avec `origin="heuristique"` (honnête) ;
  idempotent, appelé au lifespan APRÈS init_db (self-healing : rattrape
  aussi les écritures hors-boucle, ex. vignettes news en thread) ;
- `async carte()` — `{filename: (source, origin)}` en une requête.

Sites (mesurés) : /images/generate ×3 → `generation` (hint `source`
optionnel du body accepté si slug connu — appelants futurs) ; /images/
process ×6 → `retouche` ; matières routes:6463 → `matieres` ; planche
bible (panneaux+board+miroir) → `atelier` ; sketch:5183 → `atelier` ;
face.py:2697 → `cardforge` (deck_id connu sur place) ; /images/upload →
`vectorlab` si `vector_*` sinon `import` ; /images/fetch → `import_url` ;
/images/import-url → `news` ; import-figma → `figma` ; sprite save →
`sprites` (job court) ; shot save → `assets3d` (job court) ;
/audio/upload → `import` kind=audio. `DELETE /images/{f}` retire la
ligne ; `POST /images/{f}/rename` migre la ligne (delete+insert, même
source/origin). news_service (thread, hors boucle) = reconcile+préfixe.

**D4 — Rétro-remplissage des ~996 existants :** `reconcilier()` au boot
= le backfill une-fois ET le filet permanent. Chaque ligne rétro-remplie
dit `origin="heuristique"` ; l'UI l'affiche (`≈` devant le libellé).
`GET /api/images` : fichier non indexé → heuristique À LA VOLÉE (origin
`heuristique`, non persisté) — l'API est toujours complète, la table
n'est qu'un raffinement exact.

**D5 — Le « système d'identifiant » (point d du spawn) : le filename
canonique RESTE l'identifiant.** Mesuré : c'est déjà l'ancre de TOUT le
dépôt — `jobs.image_filename`, `ScheduledPost.source_image`,
`BibleEntity.ref_image/face_image/inspiration_images`, `img:<fichier>`
du Cardforge (artSource), overlays Montage `{image:name}`, props
`filename` du nœud Image Studio, exports print3d. Un id opaque séparé
exigerait une indirection à chaque lecture ou une réécriture générale
des réfs, pour un gain nul tant que le fichier est la vérité. La table
ajoute la provenance SUR cette ancre ; le rename migre la ligne d'index
mais reste file-only pour les réfs (limite EXISTANTE de l'app,
inchangée et dite).

**D6 — Exposition : additif partout.** `ImageItem.source: str|None` +
`ImageItem.source_origin: str|None` (schemas.py) remplis par
`list_images` via `carte()` + heuristique. Pas d'endpoint de casse par
catégorie (les chips comptent côté client — YAGNI dit). Rien ne casse
pour un fichier non indexé (repli `inconnu`).

**D7 — Chips de filtre (patcher NEUF `patch_bundle_libprov.py`,
maillon APRÈS libpicker).** Écran Library (`vm`, mesuré) : état
`[SF,SFs]` injecté dans la chaîne const du composant (ancre
`{const[o,i]=x.useState("Images"),` count==1) ; reset au changement
d'onglet (ancre `onClick:()=>i(C)` count==1) ; filtre au calcul de la
liste (ancre `Y=T[o]||[],q=Lfs(Y.length>0?Y:vo[o]);` count==1 →
Images par `(z.source||"inconnu")`, Renders par `z.provider`, filtre
actif → jamais le repli démo) ; rangée de chips (Tout + valeurs
distinctes + compte, `≈` si origin heuristique) rendue au-dessus de la
grille pour Images ET Renders. L'item image gagne
`source:S.source||"inconnu",srcOrigin:S.source_origin||""` (ancre = le
map mesuré `const W=((ne==null?void 0:ne.images)||[]).map(S=>({name:S.filename,kind:"image",...`).
Sélecteur `__dzLibPicker` : chips par source dans l'overlay — patchs à
ancres UNIQUES sur le corps du picker (`var tout=[];function fermer()`,
`hote.querySelector("b").textContent`, bloc CSS `.dzlp-vide`), SANS
ajouter ni retirer d'occurrence du token `__dzLibPicker` (le pin ×10 de
test_library_picker.py TIENT tel quel).

**D8 — « Envoyer vers… » (patcher NEUF `patch_bundle_libsend.py`,
maillon APRÈS libprov).** Un bouton unique dans le modal d'asset
(ancre post-libsprites `children:"Rouvrir dans Studio"}),` count==1)
ouvrant un menu overlay `__dzSendTo(m, onClose)` (helper module inséré
avant `function __dzToSpriteLab(src){`). Cibles par kind, chacune sur un
MÉCANISME EXISTANT mesuré :

| Cible | kind | Mécanisme réel (mesuré dans le bundle/l'API) |
|---|---|---|
| Studio (nœud Image) | image | `window.__dzRenderGraph={name,nodes:[{id:"im1",type:"Image",x:300,y:240,props:{filename}}],edges:[]}` + `deepotus:navigate{view:"studio"}` — le `Lh` init consomme déjà `__dzRenderGraph` (aucune greffe Studio) |
| Quick (image de départ) | image | `window.__dzQuickStart=name` + navigate quick ; UNE greffe consomme le global au mount (ancre `f(je),!w&&je.length&&v(je[0])` count==1) |
| Template (Studio) | image | même `__dzRenderGraph` : nodes Image + SpatialCompose (port `bg` type image mesuré), edge `{id:"e1",from:"im1",fromPort:"out",to:"sc1",toPort:"bg"}` — le template se choisit dans le nœud |
| Chapitre/Atelier (bible) | image | sous-menu entités : `GET /api/bible/entities` → `PUT /api/bible/entities/{id}` `{inspiration_images: existantes+[name]}` (patron « → Bible » du Vectorlab, endpoint existant) |
| Montage (overlay V2) | image | `window.__dzMontageAdd={image:name}` + navigate montage ; UNE greffe useEffect dans DzMontage (ancre `function defaultLen(kind,srcDur){` count==1, `addAsset` hoisté, délai 450 ms post-restauration) |
| Montage (clip) | render | `window.__dzMontageAdd={job_id,title,dur}` — même greffe, `addAsset({job_id},title,"video",dur)` (forme mesurée du clic « Rendus vidéo ») |
| Cardforge | image | presse-papier `img:<name>` (artSource le résout — mesuré) + navigate `{view:"assets3d",subtab:"cards"}` + toast expliquant où coller ; AUCUNE modification du module cards (bancs cards_face pinés) |
| Sprite Lab | image, render | `__dzToSpriteLab({kind,…})` EXISTANT (libsprites) |
| Scheduler (brouillon) | image, render | `D.createScheduledPost({title,source_image|job_id,channels:["x"],run_at:+2h,status:"draft",mode:"assisted"})` + navigate scheduler + `deepotus:select-post{id}` (patron Épisodes mesuré) |
| Impression 3D | asset3d | `__dzPrint3d(m.short)` EXISTANT (prompt mm + from-assets3d + open slicer) — l'appel passe le compte du token à 3 → pin test_print3d.py:309 mis à jour 2→3 (commenté) |
| Copier la sheet en image | sprite2d | `POST /assets/sprite/{short}/save` puis toast (la copie arrive sourcée `sprites`) |

Hors périmètre DIT : audio (pas de cible pertinente), News/Épisodes
comme cibles (aucun point de consommation d'une image existante),
modification du module /cardforge/ (presse-papier à la place), chips
audio, OAuth Figma. Aucune navigation vers `vectorlab` par événement
(absent de la liste Yu mesurée) — pas une cible de toute façon.

**Méthode patchers :** squelette libpicker complet (backup dédié
`.bak_libprov`/`.bak_libsend`, `guard_downstream` + `ensure_tail_order`,
SPEC_DELTA char/octets recalculés-épinglés, sondes amont AUX COMPTES —
`__dzLibPicker`×10, `__dzPrint3d`×2 (libprov) puis ×3 (post-libsend),
`__dzCatBar`×2, `dz_nav_collapsed`×2, cardforge/vectorlab panes ×1 —,
vérification post-écriture sinon restauration, `node --check` en .mjs,
`--check` à blanc d'abord). Chaîne finale :
`… → print3d → libpicker → libprov → libsend`. JAMAIS repatch_all.

## Structure de fichiers

```
backend/app/services/library_index.py   NEUF — SOURCES, heuristique, noter,
                                        noter_bg, reconcilier, carte
backend/app/services/storage.py         + class LibraryAsset (create_all)
backend/app/models/schemas.py           ImageItem.source, .source_origin
backend/app/api/routes.py               hooks D3 + list_images enrichi +
                                        delete/rename qui entretiennent l'index
backend/app/services/cards/face.py      hook rescaper → cardforge
backend/app/main.py                     lifespan : await reconcilier()
backend/tests/test_library_provenance.py NEUF — RED d'abord (chantier A)
backend/tests/test_library_sendto.py    NEUF — miroirs bundle (chantier B)
backend/tests/test_print3d.py           pin __dzPrint3d 2→3 (commenté)
scripts/patch_bundle_libprov.py         NEUF — chips (vm + picker)
scripts/patch_bundle_libsend.py         NEUF — Envoyer vers…
frontend/dist/assets/index-BEOJX8L5.js  patché (résultat committé)
```

## Tasks

- [x] **T1 backend RED→GREEN (chantier A)** :
  `test_library_provenance.py` (UN processus, patron test_library_picker)
  — (a) heuristique pure (7 préfixes + inconnu) ; (b) upload → source
  `import` / `vector_*` → `vectorlab` dans GET /api/images ; (c)
  /images/process crop (PIL local) → `retouche` ; (d) rename migre la
  ligne, delete la retire ; (e) reconcilier() : fichiers pré-posés
  `gen_x.png`/`figma_a_1-2.png` → lignes `heuristique`, ligne `depot`
  existante INTACTE ; (f) fichier jamais indexé → source heuristique à
  la volée dans l'API. RED d'abord → service+table+schemas+hooks routes →
  GREEN → `scripts\run-tests.ps1 -Filter test_library_provenance` +
  voisins (test_library_picker, test_image_rename, test_images_process,
  test_hygiene_imports) → commit.
- [x] **T2 hooks restants + lifespan** : generate ×3 (+hint), process ×6,
  matières, planche/sketch atelier, face.py cardforge, sprite/shot
  saves, audio upload, import-url ; `main.py` reconcilier ; re-run banc +
  test_cards_face si touché → commit.
- [x] **T3 patcher libprov** : items vm sourcés + état/reset/filtre/chips
  vm + chips picker ; `--check` d'abord ; miroirs dans
  test_library_provenance (marqueur `dzlp-chips`, patcher gardé,
  `__dzLibPicker`×10 INCHANGÉ) ; node --check ; commit.
- [x] **T4 patcher libsend** : helper `__dzSendTo` + bouton modal +
  greffes Quick/Montage + pin print3d 2→3 ; `test_library_sendto.py`
  miroirs (helper présent, greffes présentes, comptes) ; node --check ;
  commit.
- [x] **T5 déploiement & preuves réelles** : copie sha-vérifiée bundle +
  backend → %LOCALAPPDATA%\DeepotusVideoGen, stop.ps1 + relance uvicorn
  caché, santé 2.5.0 ; preuves navigateur en PETITS PAS : chips visibles
  et filtrantes (compter les cases AFFICHÉES, offsetHeight>0), sources
  vraies sur les 996 (heuristique dite), picker chips ; Envoyer vers…
  ouvert depuis une image : → Studio (nœud Image porte le filename), →
  Quick (champ affiché), → Scheduler (brouillon créé puis SUPPRIMÉ), →
  Bible (entité de test créée/PUT/retirée), → Montage (clip ajouté sur
  V2) ; depuis un rendu : → Montage/Scheduler ; nettoyage vérifié aux
  endpoints ; relevé ici ; push `HEAD:claude/audit-cleanup-2026-08` ;
  mémoires (projet « bibliotheque-provenance » + Export) ; rapport.
