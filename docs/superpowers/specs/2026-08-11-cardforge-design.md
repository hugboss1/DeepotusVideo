# Card Forge — spec d'execution du gauntlet (8 pieces)

**Date** 2026-08-11 · **Depot** `C:\Users\olivi\DeepotusVideo` · branche `claude/audit-cleanup-2026-08`, HEAD `3e29d97` (v2.2.0)
**Objet** editeur de cartes a jouer complet dans l'ecran Game Assets : faces importees ou generees par IA, bordures/cadres,
epaisseur 3D, textures 2D et PBR, caracteristiques pilotees par CSV, export en rendu 3D facon NFT ET en planche prete a imprimer.

**Les 4 barres reelles, jugees en duel aveugle**

| # | barre | URL | ce qu'elle tient |
|---|---|---|---|
| A | Clash of Decks — card generator | https://cardgenerator.clashofdecks.com/ | composition + impression, 300 illustrations, sans compte |
| B | nanDECK 1.29 | https://nandeck.com | CSV -> deck, 300 DPI, imposition, traits vectoriels |
| C | Meshy workspace | https://www.meshy.ai/fr/workspace | panneau 3D + visionneuse + 8 formats d'export |
| D | Sorceress Material Forge | https://sorceress.games/material-forge | textures PBR |

---

## 0. Ce qui est verifie (mesure ce jour, ne pas re-deriver)

| fait | valeur mesuree |
|---|---|
| Bundle | `frontend/dist/assets/index-BEOJX8L5.js` — 1 366 986 octets, 11 885 lignes |
| **Fins de ligne du bundle** | **CRLF** (11 884 `\r\n`, 0 `\n` isole). La reco disait « LF pur » : c'est faux, l'artefact de `read_text(newline=None)`. Avec `newline=''` : 1 349 438 caracteres. |
| Ancres du hub | K1..K5 = 1 occurrence chacune (verifie par `str.count`) |
| `src:"/cardforge/"`, `"cards"`, `DzCardForge` | 0 occurrence — aucun risque de collision |
| Python de PROD | `C:\Users\olivi\AppData\Local\DeepotusVideoGen\runtime\python\python.exe` — 3.13.14 |
| Paquets de PROD | **PIL 12.3.0 OK · pypdf 6.15.0 OK · reportlab ABSENT · numpy ABSENT** |
| PIL -> PDF | `Image.init()` **obligatoire** avant `save(...)` en PDF, sinon `KeyError: 'JPEG'`. Verifie. |
| PDF PIL a 300 DPI | page 2480x3508 px -> `/MediaBox [0 0 595.2 841.92]` (A4 a 0,03 mm pres) |
| pypdf TrimBox/BleedBox | `page.trimbox = RectangleObject([...])` -> relu correctement apres `PdfWriter.write`. **Verifie.** C'est ce que le PDF de nanDECK n'a PAS. |
| Visionneuse 3D | `<model-viewer>` deja vendore : `/assets/model-viewer.min.js` (servi par le mount racine du SPA) |
| Polices servies | 23 fichiers sur `/fonts/` — 22 `.ttf` + **`PolandKaito.otf`** (ne pas deviner l'extension) |
| PBR existant | `pbr_service.MAP_KINDS` = `basecolor, normal, roughness, metallic, ao, height, emissive, orm` (8) |
| GLB existant | `gltf_builder.build_glb(maps, props, mesh, name, stage_png, uv_repeat)`, `TEXTURE_SLOTS` = basecolor/normal/orm/emissive/roughness/metallic/ao |
| Generation IA | `POST /api/images/generate` `{prompt, n<=4, size, model, seed}` -> `{images:[fname], model}`, ecrit dans `settings.images_path` |
| Tests | UN PROCESSUS PAR FICHIER : `.\scripts\run-tests.ps1 -Filter cards` |

---

## 1. La moitie mesurable, traduite en seuils

### 1.1 Regle de geometrie (unique, gravee dans `core.py` / `core.js`)

```
R(x)          = floor(x + 0.5)                         arrondi demi-haut
px(mm, dpi)   = R(mm / 25.4 * dpi)
canvas_px     = px(trim_mm + 2*bleed_mm, dpi)          <- la TOILE fait autorite
trim_px       = px(trim_mm, dpi)
bleed_off_px  = (canvas_px - trim_px) / 2              <- peut valoir x.5, assume
safe_px       = px(trim_mm - 2*safe_mm, dpi)           <- la ZONE SURE, de meme
safe_off_px   = bleed_off_px + (trim_px - safe_px) / 2
```

Pourquoi la toile fait autorite : deriver `canvas = trim + 2*round(bleed)` donne 814 px la ou le metier attend 815, et
**rate les chiffres de nanDECK d'un pixel** sur les formats imperiaux. Avec la regle ci-dessus, `poker_us` sort a
825x1125 EXACTEMENT comme nanDECK, et le trait de coupe tombe a 37,5 px — un demi-pixel assume, rendu en sous-pixel.

**UNE SEULE CONVERSION PAR LONGUEUR — la zone sure n'y echappe pas.** (Corrige le 11/08 : la premiere redaction gravait
`safe_px = trim_px - 2*px(safe_mm)`, c'est-a-dire exactement la double conversion que la regle pretend supprimer, et
elle se trompait DANS LES DEUX SENS : 1 px de trop peu sur les 7 formats imperiaux — `micro` sortait 299x449 pour une
zone sure de 1 x 1,5 pouce EXACT, donc 300x450 — et jusqu'a +1,18 px sur les 5 metriques, donc du texte hors zone sure
qui PASSAIT le controle avant vol de P7. Elle produisait aussi trois collisions internes dans une seule reponse de
`/formats` : 57,15 mm valait 675 px comme rogne de `bridge_us` et 674 px comme zone sure de `poker_us`.) La zone sure
mesure `trim_mm - 2*safe_mm` : on convertit CETTE longueur, d'un bloc. Et `safe_off_px` est le CENTRAGE de la zone sure
dans la rogne — demi-difference, comme `bleed_off_px` — pas une seconde somme de marges : sur `poker_us`, fond perdu et
zone sure valent tous deux 3,175 mm et donnent tous deux 37,5 px d'inset.

**Fond perdu natif par format** : metrique -> 3 mm ; imperial -> 0.125 in (3,175 mm). **Zone de securite par defaut = fond perdu**
(convention Artscow / Printer's Studio). Les deux restent reglables (0 a 10 mm).

### 1.2 Table des formats — seuils DURS a 300 DPI

| id | rogne | trim px | **toile px (avec fond perdu)** | fond perdu px | zone sure px | offset sur px (x, y) |
|---|---|---|---|---|---|---|
| `poker_us` | 2.5 x 3.5 in | 750x1050 | **825x1125** | 37,5 | 675x975 | 75 / 75 |
| `poker_eu` | 63 x 88 mm | 744x1039 | **815x1110** | 35,5 | 673x969 | 71 / 70,5 |
| `bridge_us` | 2.25 x 3.5 in | 675x1050 | **750x1125** | 37,5 | 600x975 | 75 / 75 |
| `bridge_eu` | 59 x 91 mm | 697x1075 | **768x1146** | 35,5 | 626x1004 | 71 / 71 |
| `tarot_us` | 2.75 x 4.75 in | 825x1425 | **900x1500** | 37,5 | 750x1350 | 75 / 75 |
| `tarot_eu` | 70 x 120 mm | 827x1417 | **898x1488** | 35,5 | 756x1346 | 71 / 71 |
| `mini` | 44 x 68 mm | 520x803 | **591x874** | 35,5 | 449x732 | 71 / 71 |
| `square_eu` | 70 x 70 mm | 827x827 | **898x898** | 35,5 | 756x756 | 71 / 71 |
| `domino` | 1.75 x 3.5 in | 525x1050 | **600x1125** | 37,5 | 450x975 | 75 / 75 |
| `business` | 2 x 3.5 in | 600x1050 | **675x1125** | 37,5 | 525x975 | 75 / 75 |
| `jumbo` | 3.5 x 5.5 in | 1050x1650 | **1125x1725** | 37,5 | 975x1575 | 75 / 75 |
| `micro` | 1.25 x 1.75 in | 375x525 | **450x600** | 37,5 | 300x450 | 75 / 75 |

Les zones sures des 7 formats imperiaux tombent sur des pouces EXACTS (`micro` = 1 x 1,5 in = 300x450 px, `poker_us` =
2,25 x 3,25 in = 675x975) : c'est le controle le plus simple de la colonne. Sur les metriques, `x` et `y` peuvent
differer d'un demi-pixel (`poker_eu` : 71 / 70,5) — c'est le centrage exact de la zone sure dans la rogne, pas une
faute d'arrondi. **Ces chiffres ne sont PAS la reference du test** : `backend/tests/test_cards_core.py` les confronte a
une reference en arithmetique exacte (`fractions.Fraction`) sur 12 formats x 6 definitions x 5 fonds perdus x 4 zones
sures, et au bloc de formule EXTRAIT de `core.js`. Une table recopiee ne prouve rien contre la regle qui l'a produite.

Les 7 formats imperiaux reproduisent **au pixel** les tailles avec fond perdu de nanDECK (825x1125, 750x1125, 900x1500,
600x1125, 675x1125, 1125x1725, 450x600). Ce n'est pas une coincidence, c'est le critere de non-regression.

**Les deux « bridge » ne sont pas la meme carte, et c'est voulu.** `bridge_us` 57,15 x 88,9 mm est une carte poker US
retrecie : meme hauteur que `poker_us`, seulement plus etroite. `bridge_eu` 59 x 91 mm est un standard europeen a part
entiere — plus etroit ET plus haut que `poker_eu` 63 x 88. Les deux existent chez de vrais imprimeurs ; la table les
sert tels quels et chaque libelle porte ses dimensions, precisement pour que le choix se fasse sur les chiffres. P7
(selecteur de format nomme) affiche mm + pouces + px en permanence : c'est la que la difference se lit.

### 1.3 Planches

| page | 150 DPI | 300 DPI | 600 DPI |
|---|---|---|---|
| A4 210x297 | 1240x1754 | **2480x3508** | 4961x7016 |
| Letter 215.9x279.4 | 1275x1650 | **2550x3300** | 5100x6600 |
| A3 297x420 | 1754x2480 | **3508x4961** | 7016x9921 |

PDF a 300 DPI : `/MediaBox [0 0 595.2 841.92]` pour A4 ; **`/TrimBox` et `/BleedBox` presents sur chaque page** (pypdf).

### 1.4 Jeu COMPLET de maps PBR — liste nommee, non negociable

`basecolor` · `normal` · `roughness` · `metallic` · `ao` · `height` · `emissive` · `orm`

Huit. Meshy en livre **cinq** (base_color, metallic, roughness, normal, emission) et **n'a ni AO ni height**.
Repartition a l'export :

* **ZIP** : les 8 PNG, plus `card.mtl`-like manifeste JSON. `height` et `normal` en 16 bits (`material_store.png_bytes(..., bits=16)`).
* **GLB / glTF** : 4 emplacements reellement lus — `basecolor`, `normal`, `orm` (= AO/rough/metal packes), `emissive`.
  `height` n'a pas d'equivalent en glTF cœur : il part dans le ZIP et dans `extras`. `roughness`/`metallic`/`ao` separes
  sont volontairement omis du GLB (`build_glb` les ecarte des qu'une ORM existe : les encoder gonfle le fichier sans etre lu).
* **`.gltf`** en plus du `.glb` (via `material_store.glb_to_gltf`) — Meshy n'exporte **pas** de `.gltf`.

---

## 2. Architecture

### 2.1 Arborescence — QUI possede QUOI

```
frontend/cardforge/
  index.html               [CORE]  coquille : topbar, rail, 8 <section> vides, 8 <script>, 9 <link>
  cardforge.css            [CORE]  @import tokens + coquille + primitives partagees
  js/core.js               [CORE]  LE CONTRAT. Zero code metier.
  js/mod-face.js           [P1]    css/mod-face.css      [P1]
  js/mod-frame.js          [P2]    css/mod-frame.css     [P2]
  js/mod-type.js           [P3]    css/mod-type.css      [P3]
  js/mod-data.js           [P4]    css/mod-data.css      [P4]
  js/mod-solid.js          [P5]    css/mod-solid.css     [P5]
  js/mod-texture.js        [P6]    css/mod-texture.css   [P6]
  js/mod-print.js          [P7]    css/mod-print.css     [P7]
  js/mod-gltf.js           [P8]    css/mod-gltf.css      [P8]
  assets/frames/           [P2]    catalogue de cadres livre
  assets/papers/           [P6]    catalogue de textures livre

backend/app/services/cards/
  __init__.py              [CORE]
  contract.py              [CORE]  dataclass CardGeom + signatures gelees + validation
  core.py                  [CORE]  deck store (disque), assemblage du routeur, /geom, /formats
  face.py [P1]  frame.py [P2]  type.py [P3]  data.py [P4]
  solid.py [P5]  texture.py [P6]  print.py [P7]  gltf.py [P8]

backend/tests/test_cards_core.py [CORE] · test_cards_face.py [P1] · ... · test_cards_gltf.py [P8]
scripts/patch_bundle_cardforge.py   [CORE]
scripts/qa/inventory_bundle.py      [CORE]
scripts/qa/lint_cardforge.py        [CORE]  fait respecter R4/R5/R8 mecaniquement
```

**Les 8 builders ne touchent JAMAIS** : `index.html`, `cardforge.css`, `js/core.js`, `cards/__init__.py`,
`cards/contract.py`, `cards/core.py`, `backend/app/main.py`, le patcher, les scripts QA, `routes.py`.
Toute la coquille est ecrite **une fois, avant** que les 8 partent, et gelee.

### 2.2 LE CONTRAT `core.js` — le point le plus important de cette spec

`core.js` expose un unique global `window.CF`, gele (`Object.freeze`) **et sous un nom lui-meme gele**
(`defineProperty`, writable:false, configurable:false — sans quoi le premier module charge sert un faux contrat aux
sept autres). Il ne contient aucun code metier : il ne sait pas ce qu'est un cadre, une police ou un CSV. Il ne sait que
**partitionner**.

> **REVISION 2 (11/08) — L'IDENTITE NE SE LIT PLUS DANS LA PILE D'APPEL.** La premiere redaction identifiait l'appelant
> par le nom de fichier lu dans `new Error().stack`. Trois attaques mesurees l'ont demolie : `eval` + `//# sourceURL`
> suffisait a ecrire chez autrui ; le controle portait sur le nom de BASE, donc un `lib/mod-face.js` pose n'importe ou
> avait les pleins droits sur `doc.face` ; et `[{dpi:600}].forEach(CF.setFormat)` blanchissait la pile, ce que
> `setFormat` prenait pour « c'est le CORE » (la regle etait INVERSEE entre les API). L'identite est maintenant prouvee
> UNE FOIS, a l'enregistrement, par `document.currentScript` — l'element `<script>` que le navigateur execute
> reellement, qu'aucun eval ne contrefait — puis **portee par le JETON** que `CF.register` rend a ce script-la.
> `CF.patch`, `CF.setFormat`, `CF.setCards`, `CF.emit`, `CF.api`, `CF.slot`, `CF.aside`, `CF.invalidate` **n'existent
> plus sur le global** : ils levent en nommant leur remplacant.

```js
/* ═══ 1. REGISTRE — et la remise du JETON ════════════════════════════════ */
const M = CF.register({
  id:      "face",              // DOIT valoir l'un des 8 ids geles
  title:   "Face",              // titre du panneau
  order:   1,                   // rang dans le rail (= numero de piece)
  painters: [                   // 0..n couches; z pris dans la TABLE Z gelee
    { z: 20, fn(ctx, geom, doc, card, side) { /* dessine — AUCUNE echelle */ } }
  ],
  state:   { art_fit: "cover" },// LE SCHEMA : seules ces cles seront patchables
  async init(host) { /* host = HTMLDivElement du panneau, deja vide */ }
});
// -> throw si id inconnu, si deja enregistre, si un z n'est pas alloue a cet id,
//    ET si le <script> appelant n'est pas exactement js/mod-<id>.js.
// M est le JETON. Il porte l'identite : on le garde dans la fermeture du module,
// on ne l'accroche JAMAIS a window (une capacite se donne).

/* ═══ 2. ETAT PARTAGE — lecture universelle, ecriture EXCLUSIVE ══════════ */
CF.doc()                 // document complet, deep-frozen (mutation = TypeError
                         //   — a condition d'etre en "use strict" : regle 11)
CF.get("solid.thickness_mm", 0.32)   // acces sur par chemin, defaut si absent
                         //   (hasOwnProperty : ne traverse PAS Object.prototype)
M.patch({ art_fit: "cover" })
//  ecrit UNIQUEMENT sous doc[M.id] ; une cle hors du `state` declare ->
//  throw "cardforge: <id> ne possede pas <cle>". Fusion superficielle sur le
//  1er niveau du sous-arbre, valeur CLONEE, puis emet "core:doc".
//  L'onglet n'enregistre que les sous-arbres QU'IL A MODIFIES : un onglet qui
//  n'a pas touche doc.face ne peut pas l'effacer (c'etait le cas avant).
M.setFormat({ fmt, dpi, bleed_mm, safe_mm, corner_mm })   // JETON DE P7 SEUL

/* ═══ 3. GEOMETRIE — verite unique ══════════════════════════════════════ */
CF.geom()   // objet gele, memoise, recalcule a chaque setFormat :
// { fmt:"poker_eu", label:"Poker 63 x 88 mm", unit:"mm", dpi:300,
//   trim_mm:[63,88], bleed_mm:3, safe_mm:3, corner_mm:3,
//   trim_px:[744,1039], canvas_px:[815,1110], bleed_off_px:[35.5,35.5],
//   safe_px:[674,969], safe_off_px:[70.5,70.5], corner_px:35.4,
//   mm2px(v), px2mm(v) }
// Aucun module ne recalcule un pixel a partir des mm. Jamais.

/* ═══ 4. CARTES ═════════════════════════════════════════════════════════ */
CF.cards()          // [{ i, id, fields:{slotId:string}, art:string|null, back:string|null }]
M.setCards(rows)    // JETON DE P4 SEUL (la methode n'existe pas sur les autres)
CF.card(i)          // raccourci

/* ═══ 5. RENDU — UN SEUL moteur, UNE SEULE echelle ══════════════════════ */
await CF.renderCard(i, { face = "front" })
//  -> HTMLCanvasElement de geom.canvas_px. TOUJOURS. C'est LE FICHIER LIVRE.
//  Compose les painters par z croissant. Un painter ne recoit AUCUNE echelle :
//  il ne peut donc pas savoir s'il dessine pour l'ecran ou pour l'imprimeur, et
//  « ne pas faire le grain quand c'est petit » n'est plus exprimable.
//  L'apercu est ce MEME bitmap, reduit par drawImage.
//  Il n'y a PAS de parametre `guides` : la couche z=90 n'est joignable que par
//  l'apercu du CORE, donc aucun fichier telecharge ne peut la contenir.
//  Les rendus sont SERIALISES (CF.side() est partage ; deux rendus concurrents
//  se le volaient au premier await et le verso sortait au recto).
//  Un painter a 4 s pour rendre la main ; au-dela il est signale et ecarte,
//  et les sept autres pieces continuent de s'afficher.
M.invalidate()      // demande un re-rendu ; coalesce sur requestAnimationFrame

/* ═══ 6. EVENEMENTS ═════════════════════════════════════════════════════ */
CF.on("core:doc", fn) / CF.off(h)
M.emit("art-ready", payload)   // diffuse "face:art-ready" — le prefixe est
//  celui du jeton, il n'y a plus d'id a usurper. Evenements core : core:doc,
//  core:geom, core:cards, core:render, core:deck, core:invalidate, core:images.

/* ═══ 7. UI ═════════════════════════════════════════════════════════════ */
M.slot()       // le <div> du panneau du module (deja fourni a init)
M.aside()      // panneau lateral droit optionnel, a la demande
CF.toast(msg, isErr) · CF.busy(bool, label) · CF.show(id)

/* ═══ 8. RESEAU — chacun chez soi ═══════════════════════════════════════ */
M.api.get/post/patch/del(sous_chemin, body)
//  -> /api/cards/<did>/<M.id>/<sous_chemin>. Le miroir exact de la regle 8
//  backend. Un chemin absolu ("/health", "/images/generate") ou un ".." leve.
//  ApiMissing si 404 ou HTML (piege 7).
M.api.blob(method, sous_chemin, body)  // binaire, et TELECHARGEABLE (provenance)
M.api.url(sous_chemin)                 // pour un <img src>
CF.images.generate({ prompt, n<=4, size, model, seed })   // LE SEUL dehors,
//  tenu par le CORE : c'est la seule depense de credits, elle se compte a un
//  seul endroit (regle 17). CF.images.models() · CF.images.url(fname).

/* ═══ 9. FICHIERS ═══════════════════════════════════════════════════════ */
CF.download(blob, "nom.png")
//  n'accepte qu'un blob de PROVENANCE connue : sorti de CF.cardBlob (le
//  moteur) ou de M.api.blob (le backend du module). Une toile fabriquee a cote
//  ne se telecharge pas — sinon « le fichier livre vient du moteur unique »
//  n'est tenu par rien.
CF.imageURL(fname)     // resout un nom de fichier image du backend en URL

/* ═══ 10. PERSISTANCE ═══════════════════════════════════════════════════ */
// CORE seul. Autosave debounce 900 ms sur "core:doc", PATCH /api/cards/<did>,
// et SEULEMENT les sous-arbres modifies par cet onglet. Aucun module n'ecrit
// le document sur disque. Un chargement de page n'est pas une creation : le
// dernier jeu (dz_cf_deck_id) est REOUVERT, on ne cree que s'il n'existe plus.
```

**TABLE Z GELEE** — un module ne peut enregistrer un painter qu'a ses propres z :

| z | proprietaire | couche |
|---|---|---|
| 10 | `texture` | fond de papier / matiere sous l'illustration |
| 20 | `face` | illustration (importee ou IA), recadrage, transformation |
| 30 | `texture` | grain / foil / holo par-dessus l'illustration, sous le cadre |
| 40 | `frame` | cadre, bordure, filets, coins |
| 60 | `type` | **tout** le texte |
| 70 | `frame` | ornements de dessus (gemme de rarete, sceau) |
| 90 | **core** | reperes fond perdu / coupe / zone sure — **jamais exporte** |

`data`, `solid`, `print`, `gltf` n'ont **aucun** painter : ils ne dessinent pas la carte.

**LES 12 REGLES** (verifiees par `scripts/qa/lint_cardforge.py`, sortie non nulle = build rejete)

1. Un module = 1 JS + 1 CSS + 1 py + 1 test. Rien d'autre.
2. `M.patch(...)` n'ecrit que sous `doc[M.id]`. Le document est deep-frozen ailleurs.
3. La **lecture** est universelle : `CF.get("type.slots")` depuis n'importe ou.
4. Tout selecteur de `css/mod-<id>.css` contient `.cf-<id>`. Aucune regle sur `body`, `:root`, `*`, un element nu.
5. Tout `id=` DOM cree par un module commence par `cf-<id>-`.
6. `M.emit(nom, ...)` porte le prefixe du jeton — il n'y a plus d'id a usurper.
7. Painters seulement aux z alloues.
8. Backend : `backend/app/services/cards/<id>.py` declare `router = APIRouter()`, chemins **relatifs**.
   Aucun module n'importe le `router` d'un autre. `M.api` est confine au meme sous-prefixe.
9. Les signatures inter-modules sont gelees dans `contract.py` (voir 2.4). On remplit le corps, jamais la signature.
10. Zero dependance externe, zero CDN, zero build. `<model-viewer>` vient de `/assets/model-viewer.min.js`.
11. **Tout `js/mod-<id>.js` commence par `"use strict"`.** Ce n'est pas du style : `CF.doc()` rend un clone
    deep-frozen, mais en mode bâclé une mutation ne leve PAS — c'est un no-op MUET, le module croit avoir ecrit et
    relit l'ancienne valeur. La garantie « mutation = TypeError » est entierement portee par cette directive, dans des
    `<script>` classiques ou le mode bâclé est le DEFAUT. Aucun test dynamique ne peut la remplacer (sur V8 moderne,
    `Object.getOwnPropertyNames` d'une fonction rend la meme chose stricte ou non — mesure). Le lint la refuse au
    build, et `auditStrict()` relit la source SERVIE au demarrage : un module non conforme ne demarre pas et ses
    couches sont retirees du rendu.
12. **Aucun mutateur global dans un module.** `CF.patch`, `CF.setFormat`, `CF.setCards`, `CF.emit`, `CF.api`,
    `CF.slot`, `CF.aside`, `CF.invalidate` n'existent plus : l'ecriture passe par le jeton de `CF.register`.

**LA PREUVE DU CONTRAT** — `frontend/cardforge/qa/test_core_contract.mjs` (aucune dependance npm) :
`--geom` charge le VRAI `core.js` dans un `vm` Node et le compare a une reference en arithmetique exacte (BigInt
rationnel) sur 1440 geometries ; `--contract` ouvre `qa/contract.html` dans un Chrome sans tete — le vrai `core.js` +
huit modules d'essai dont deux hostiles (un squatteur de registre, un `lib/mod-face.js`) — et refuse de sortir 0 si une
seule attaque passe. 46 controles. C'est ce fichier que l'en-tete de `core.js` annonçait sans qu'il existe.

### 2.3 Le document du deck (schema partitionne)

```jsonc
{ "v": 1, "id": "deck_a1b2c3d4", "name": "Mon jeu",            // CORE
  "format": { "fmt":"poker_eu", "dpi":300, "bleed_mm":3.0,      // CORE (widget topbar)
              "safe_mm":3.0, "corner_mm":3.0 },
  "face":    { /* P1 */ },  "frame":   { /* P2 */ },
  "type":    { /* P3 */ },  "data":    { /* P4 */ },
  "solid":   { /* P5 */ },  "texture": { /* P6 */ },
  "print":   { /* P7 */ },  "gltf":    { /* P8 */ } }
```

Contrats de donnees **entre** pieces (le seul couplage tolere, en lecture) :

* `doc.type.slots[] = {id, label, box:[x,y,w,h] en mm depuis le coin ROGNE, ...}` — ecrit par **P3**, lu par **P4**
  (pour construire le menu de mappage) et par **P7** (controle avant vol : texte hors zone sure).
* `card.fields[slotId]` — ecrit par **P4** via `CF.setCards`, lu par **P3** (rendu du texte).
* `card.art` — precedence explicite : `card.art ?? card.fields["art"] ?? doc.face.default_art`.
* `doc.solid.{thickness_mm, corner_mm, edge}` — ecrit par **P5**, lu par **P8**.
* `doc.texture.pbr` (reglages de derivation) — ecrit par **P6**, lu par **P8**.

### 2.4 Signatures gelees, backend (`cards/contract.py`, ecrit par CORE)

```python
@dataclass(frozen=True)
class CardGeom:
    fmt: str; dpi: int
    trim_mm: tuple[float, float]; bleed_mm: float; safe_mm: float; corner_mm: float
    trim_px: tuple[int, int]; canvas_px: tuple[int, int]
    bleed_off_px: tuple[float, float]; safe_px: tuple[int, int]; safe_off_px: tuple[float, float]

def geom(fmt: str, dpi: int = 300, bleed_mm: float | None = None,
         safe_mm: float | None = None, corner_mm: float = 3.0) -> CardGeom: ...   # CORE
def deck_dir(did: str, create: bool = False) -> Path: ...                          # CORE

# P5 ecrit le corps, P8 l'importe en lecture seule. Signature intouchable :
def card_mesh(geom: CardGeom, solid: dict) -> dict:
    """-> {name, positions, normals, uvs, indices, tangents} — meme forme que
    gltf_builder.build_mesh. 3 ilots UV disjoints : recto, verso, tranche.
    INVARIANT : determinant UV negatif sur TOUT triangle (cf. test_uv_orientation)."""
```

### 2.5 Backend — le domaine « cartes » hors `routes.py`

`backend/app/main.py`, **4 lignes** inserees immediatement apres `# __DZ_MONTAGE_ROUTER_END__` (ligne 221) :

```python
# __DZ_CARDS_ROUTER_BEGIN__
from app.services.cards import router as cards_router
app.include_router(cards_router, prefix="/api/cards")
# __DZ_CARDS_ROUTER_END__
```

`cards/__init__.py` assemble : `router.include_router(face.router, prefix="/{did}/face")` ... pour les 8.
Plus le bloc `_cardforge` copie mot pour mot du bloc Material Forge (`main.py:319-342`) : sous-classe `StaticFiles`
qui force `Cache-Control: no-cache, must-revalidate`, `app.mount("/cardforge", ..., html=True)`, et la route
`@app.get("/cardforge")` qui redirige en **307** vers `/cardforge/`.

> **Limite dure** : tout doit etre insere **avant** `app.mount("/", _SPAStaticFiles...)` (`main.py:453`). Apres cette
> ligne, Starlette n'atteint plus rien — l'API repondrait du HTML.
> **`main.py` est en LF.** `material_store.py` et `routes.py` sont en CRLF.

Stockage : `settings.outputs_path / "decks" / deck_xxxxxxxx/` (voisins existants : materials/, sprites/, assets3d/...).
`DID_RE = ^deck_[0-9a-f]{8}$`, double garde-fou (motif **puis** confinement `str(p).startswith(str(root.resolve()))`),
`meta.json` ecrit atomiquement (tmp + `.replace()`). **Aucune table SQL** — ni les matieres ni les sprites n'en ont.

Style impose (calque de la section `/materials` de `routes.py`) : import paresseux du service dans chaque route,
`await asyncio.to_thread(...)` pour tout PIL/disque, reponses nommees `{"deck": {...}}` / `{"ok": True}` / `{"job_id": ...}`,
erreurs `HTTPException(code, "phrase en francais")` — 400 en enumerant la liste blanche, 404 introuvable, 409 etat
impossible, 503 module absent, 500 seulement apres `logger.exception`. **Un corps mal forme ne doit JAMAIS faire 500.**

### 2.6 Patcher du bundle — `scripts/patch_bundle_cardforge.py`, TAG `cardforge`, EN QUEUE

Calque de `patch_bundle_materialforge.py` (backup `.bak_cardforge`, restore + reapplication, `--check`, `--root`,
`--force-unchained` accepte/ignore) **plus** `guard_downstream()` copie de `patch_bundle_geminimodel.py:32-42`.

| ancre | remplacement | delta |
|---|---|---|
| K1 `return t==="sprites"\|\|t==="tiles"\|\|t==="studio3d"\|\|t==="materials"?t:"3d"}` | + `\|\|t==="cards"` | +13 |
| K2 `if(d.subtab===...\|\|d.subtab==="materials")setTab(d.subtab)` | + `\|\|d.subtab==="cards"` | +20 |
| K3 `tb("materials","✨ Matières")]},"tabs")` | + `,tb("cards","\U0001f0cf Cartes")` | +23 car / +26 o |
| K4 `}},"pmf"):r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",` | branche `tab==="cards"` -> iframe `/cardforge/`, cle React `"pcf"`, **avant** le fallback | +187 |
| K5 `desc:"3D studio, sprites, tuiles & matières"` | `desc:"3D studio, sprites, tuiles, matières & cartes"` | +8 |

**Delta total attendu : +251 caracteres / +254 octets** -> 1 337 805 car. (lecture universelle) / **1 367 240 octets**.

Style de l'iframe impose par la chaine : `{flex:1,width:"100%",minHeight:"calc(100vh - 110px)",border:"0",marginTop:10,background:"var(--bg-base)"}`.

Verification **par inventaire de fonctions**, pas a l'oeil (`scripts/qa/inventory_bundle.py`) :

* `function\s+([A-Za-z_$][\w$]*)\s*\(` : **1228 noms distincts / 1395 declarations / sha1 `458e3d054a1a346d0edb1b0155f158f4581c89db`** — IDENTIQUE avant/apres (le patch n'ajoute aucune fonction).
  (Corrige le 11/08 : la premiere redaction gravait `bcf7ab29…`, un sha1 qui n'existe nulle part. Les deux COMPTES
  etaient justes, le condensat non — et c'est le chiffre qu'un builder aurait compare pour « verifier la
  non-regression », concluant a une regression inexistante et restaurant un `.bak` « par precaution », ce qui en aurait
  cree une vraie. La recette qui fait foi est celle de `scripts/qa/inventory_bundle.py` :
  `sha1('\n'.join(sorted(set(noms))).utf-8)`, verifiee identique sur le blob HEAD et sur le bundle patche.)
* taille : +251 car. / +254 o exactement, recalcules depuis `PATCHES`, pas codes en dur.
* onglets du hub : `['3d','studio3d','sprites','tiles','materials']` -> **+ `'cards'` en DERNIER**.
* iframes : `['/spritelab/','/tilelab/','/materialforge/','/studio3d/']` -> `[...,'/cardforge/','/studio3d/']` — `/studio3d/` reste **dernier** (c'est le fallback du ternaire).
* les 5 ancres passent de 1 a 0 ; `src:"/cardforge/"` de 0 a 1 ; le switch d'ecran (ligne 11884) et les cles `p3d/p2d/ptl/pmf/ps3` restent a 1.

Ordre : `--check` -> inventaire AVANT -> patch -> inventaire APRES -> `python scripts/repatch_all.py --list`
(`cardforge` doit sortir **en DERNIER**) -> mount backend -> relance du :8765.

---

## 3. Pieges connus (chacun a deja coute une regression dans ce depot)

1. **`repatch_all.py --from ...` est interdit sur cette chaine.** `.bak_subs` et `.bak_vfxrack` ont le meme mtime a la
   microseconde ET le meme sha1 ; `--list` sort deja `subs` AVANT `vfxrack`, l'inverse de l'ordre reel. Le patcher
   cardforge se lance **seul**.
2. ~~**Relancer `patch_bundle_materialforge.py` seul efface cardforge sans un mot** (aucune garde de chaine amont).~~
   **CORRIGE le 11/08** : les trois maillons qui RESTAURENT leur `.bak` avant de reappliquer — `materialforge`,
   `vfxrack`, `subs` — ont recu la meme `guard_downstream()` que cardforge. Mesure avant : une relance de
   materialforge seul faisait disparaitre `src:"/cardforge/"` et `tb("cards"` du bundle et lui otait 29 545
   caracteres, sans un mot, en laissant tous les marqueurs BEGIN/END en place. Apres : les trois refusent avec
   « backup aval detecte » et le sha1 du bundle ne bouge pas. `--force-unchained` desarme la garde (c'est ce que passe
   `repatch_all.py` quand il rejoue la chaine entiere dans l'ordre). Les cinq autres maillons
   (`audiobanks`, `sonvfx`, `keepstate`, `keepview`, `sfxstudio`) ne restaurent RIEN : ils n'ont pas ce defaut.
3. **`shutil.copy2` conserve le mtime de la SOURCE** : verifier apres le 1er run que `cardforge` sort en dernier.
4. **Emojis** : ecrire `\U0001f0cf` en echappement (console Windows cp1252) et ne jamais `print` une ancre.
5. **CRLF** : `read_text`/`write_text` sans `newline=` round-trippe le CRLF sur Windows — et le casserait sur Linux.
   Le patcher tourne sur Windows, point.
6. **`grep -c` compte des LIGNES** : tout le hub tient sur la ligne 147. La mesure qui fait foi est `str.count()`.
7. **Sans le mount `/cardforge` cote backend, l'iframe affiche la SPA entiere en cascade** — symptome trompeur d'« onglet casse ».
8. **Le mount se cree au boot** : ajouter le bloc a `main.py` exige de tuer/relancer le python du :8765.
9. **`gltf_builder` ignore SILENCIEUSEMENT un nom de maillage inconnu et rend une sphere.** On enregistre `"card"` par
   `GB._BUILDERS.setdefault("card", ...)` **au chargement du module** (jamais dans le corps d'une route), et on verifie
   par `mesh_stats("card")["triangles"] != mesh_stats("sphere")["triangles"]`.
10. **Ne PAS incrementer `MESH_VERSION`** : la constante entre dans la cle du cache d'apercu ET dans `thumb_is_current`
    — la bumper perimerait toutes les vignettes du Material Forge.
11. **`build_glb` force `metallicFactor`/`roughnessFactor` a 1.0 des qu'une ORM existe** : cuire les niveaux avec
    `pbr_service.bake_levels` AVANT encodage, sinon le reglage est perdu.
12. **Pas d'`uv_repeat` ni de `tiling`/`rotation` != (1.0, 0.0)** pour une carte a atlas : les ilots recto/verso/tranche
    deborderaient les uns sur les autres.
13. **`preview_cache_get/put` rejettent silencieusement toute cle hors `[0-9a-f]{1,40}`** : re-empreinter en sha1 hex.
14. **`Image.init()` avant tout `save(...pdf)`** — sinon `KeyError: 'JPEG'`. Verifie ce jour.
15. **reportlab est ABSENT, numpy est ABSENT** : PIL + pypdf, rien d'autre, aucune installation reseau supposee.
16. **Dette a NE PAS copier** : `spritelab.css` redeclare les tokens en dur et ne suivra jamais le theme clair.
    Modele a copier = `materialforge.css:8` (`@import url("/shared/deepotus.tokens.css")`).
    Ajouter `select{color-scheme:dark}` + `select option{background:var(--bg-panel-2)}` (popups natifs).
17. **`.btn.primary` ambre = SEULE action qui depense des credits.** L'export local est en `.btn.strong` neutre.
18. Tests : `.\scripts\run-tests.ps1 -Filter cards`. Un `pytest tests` global n'est jamais vert **par construction**.

---

## 4. Les 8 pieces

Chaque piece est jugee **a l'aveugle, deux captures cote a cote sans etiquette**. Le critere de victoire ne parle donc
que de ce qui **se voit** ou se **mesure sur un fichier telecharge**.

### Piece 01 — Generation de face (import + IA)
**Barre** Clash of Decks — galerie de 300 illustrations, import avec refus sous 650x1024, placement au clic maintenu.
**Fichiers** `frontend/cardforge/js/mod-face.js`, `css/mod-face.css`, `backend/app/services/cards/face.py`,
`backend/tests/test_cards_face.py`.
**Livrables** import glisser-depose et coller ; **generation IA via `POST /api/images/generate`** (FLUX / gpt-image /
nano-banana, choix expose, cout affiche) avec amorces d'invite adaptees a une face de carte ; catalogue de depart local
>= 60 faces ; placement au **glisser sur la carte + molette** + rotation + valeurs numeriques editables + recentrage ;
ajustement `cover`/`contain`/libre ; **jauge de DPI effectif** de l'image posee, verte >= 300, rouge en dessous, avec le
chiffre ; import par lot vers la pile de faces ; verrou de proportions.
**Mesurable**
- refus/alerte **non bloquante** si l'image donne < 300 DPI a la taille posee, avec le DPI reel affiche (Clash of Decks : refus brut a 650x1024 par `alert()` natif).
- catalogue de depart >= 60 faces servies en local, 0 octet reseau.
- placement : molette = zoom, glisser = pan, `Alt+glisser` = rotation ; 3 champs numeriques (x, y, echelle en %) editables au clavier.
- une face IA generee en <= 1 appel, resultat pose sur la carte sans copier-coller de nom de fichier.
**Victoire (critique impitoyable)** Sur les deux captures, la mienne montre le DPI effectif de l'illustration en clair
a cote de la carte ; l'autre n'affiche aucun chiffre. Et sur le fichier telecharge, l'illustration de la barre est
visiblement re-echantillonnee (bords mous a 238 DPI) tandis que la mienne est nette a 300.

### Piece 02 — Bordures et cadres
**Barre** Clash of Decks — **3** cadres PNG 638x1004 qui sont le meme cadre avec un mot different, plafonnes a 255 DPI.
**Fichiers** `js/mod-frame.js`, `css/mod-frame.css`, `assets/frames/`, `cards/frame.py`, `test_cards_frame.py`.
**Livrables** cadres **vectoriels** (dessines au canvas depuis une description, donc sans plafond de resolution) :
>= 4 familles graphiques x >= 5 variantes de rarete ; epaisseur, rayon de coin, couleur de filet, double filet, marge
interieure, ornements de coin ; fenetre d'illustration reglable (position + taille + coins) ; **dos de carte** (commun
ou par carte) ; degrade et liseré metallique parametrables.
**Mesurable**
- >= 20 combinaisons cadre x rarete visuellement distinctes, listees dans l'UI.
- **zero PNG de cadre en resolution fixe** : le cadre se redessine a `geom.canvas_px` quel que soit le DPI — a 600 DPI il n'est pas flou.
- epaisseur de filet reglable de 0 a 8 mm, rayon de coin 0 a 8 mm, tous deux affiches **en mm et en px**.
- un dos de carte existe et s'exporte (la barre n'en a aucun).
**Victoire** Deux captures d'un cadre agrandi 4x : le sien est un PNG 638 px de large, donc pixelise et borde d'un halo
de compression ; le mien est net a n'importe quel zoom. Et si le critique compte les cadres proposes, il voit 3 d'un
cote, plus de 20 de l'autre.

### Piece 03 — Typographie
**Barre** Clash of Decks — **2** polices imposees, tailles/couleurs/positions codees en dur, titre **tronque
silencieusement a 25 caracteres** et force en majuscules. nanDECK : `FONT`/`TEXT` en script, rendu riche via IE11.
**Fichiers** `js/mod-type.js`, `css/mod-type.css`, `cards/type.py`, `test_cards_type.py`.
**Livrables** **23 polices deja servies sur `/fonts/`** (22 `.ttf` + `PolandKaito.otf` — lire l'extension, ne pas la
deviner) ; systeme de **slots de texte** (`doc.type.slots[]`, boite en mm depuis le coin rogne) avec titre, cout,
attaque, vie, **encadre de regles**, texte d'ambiance, numero, artiste — ajout/suppression/deplacement/redimensionnement
a la souris ; par slot : taille, couleur, interlettrage, interligne, alignement, contour, ombre portee, capitales,
rotation, **texte sur arc** ; **ajustement automatique** (retrecir-pour-tenir + retour a la ligne) ; jamais de troncature
muette : depassement = liseré d'alerte + compteur.
**Mesurable**
- **23** familles selectionnables, apercu du glyphe dans le menu.
- **0 troncature silencieuse** : un titre de 44 caracteres passe sur 2 lignes ou retrecit ; il n'est jamais coupe sans avertissement (la barre coupe a 25).
- >= 10 reglages par slot (police, corps, couleur, interlettrage, interligne, alignement H, alignement V, contour, ombre, casse, rotation).
- l'encadre de regles accepte >= 400 caracteres et reste dans la zone sure, mesure en px.
**Victoire** Cote a cote : sur sa capture le titre long est ampute en plein mot (« ABCDEFGHIJKLMNOPQRSTUVWXY ») sans
aucun signe ; sur la mienne il tient en entier. Et son texte n'existe qu'en 2 polices, la mienne en 23 visibles au menu.

### Piece 04 — Import CSV et mapping des champs
**Barre** nanDECK — `LINK` (entete auto), `LINKMULTI = qty` (3 lignes -> 6 cartes), `LINKFILTER`, `LINKSORT`,
`LINKSEP`, `LINKCSV` (UTF-8 **non par defaut**), editeur « Linked data ». Tout s'ecrit **en texte**.
**Fichiers** `js/mod-data.js`, `css/mod-data.css`, `cards/data.py`, `test_cards_data.py`.
**Livrables** import `.csv`/`.tsv` par glisser-depose ; **detection automatique** du separateur (`,` `;` tabulation) et de
l'encodage (UTF-8/UTF-8-BOM/cp1252) ; detection d'entete ; **mappage colonne -> slot par glisser-deposer** (la barre
l'ecrit en script) ; colonne de **quantite** (duplication), **filtre**, **tri** ; jetons de copie `n/N` ; table editable
(ajout/suppression de lignes et colonnes, tri par entete, activation/desactivation ligne a ligne, double-clic = apercu
de cette carte) ; colonne image resolue vers la bibliotheque ; **export CSV** du deck (aller-retour).
**Mesurable**
- CSV de 3 lignes avec `qty` 3/2/1 -> deck de **6** cartes (parite exacte avec le test nanDECK).
- filtre `atk > 1` sur 4 lignes -> 3 lignes retenues ; combine avec `qty` -> **10** cartes.
- **UTF-8 par defaut**, les accents francais passent sans directive (chez nanDECK le defaut est ANSI : piege classique).
- separateur detecte automatiquement sur les 3 cas `,` `;` tabulation, sans question posee.
- mappage : 0 ligne de code a ecrire ; le menu de chaque colonne liste les slots reels de `doc.type.slots`.
- import de 200 lignes en < 2 s, compteur de cartes affiche en permanence.
**Victoire** Deux captures de l'ecran d'import : la sienne est un editeur de texte avec `LINKMULTI = qty` tape a la main
et une aide de 202 pages a cote ; la mienne est une table avec des menus par colonne. Et sur le CSV d'accents francais,
sa capture montre « MÃ©lÃ©e », la mienne « Melee ».

### Piece 05 — Apercu 3D et epaisseur
**Barre** Meshy workspace — visionneuse `<model-viewer>`-like : 4 reglages d'affichage, 5 HDRI, filaire on/off,
isolation de 4 canaux, HUD faces/sommets. **Aucune notion de carte, aucune epaisseur.**
**Fichiers** `js/mod-solid.js`, `css/mod-solid.css`, `cards/solid.py` (**detient `card_mesh()`**), `test_cards_solid.py`.
**Livrables** maillage **boite arrondie** parametree, **3 ilots UV disjoints** (recto / verso / tranche) dans un atlas
0..1 ; epaisseur, rayon de coin, segments d'arrondi, biseau ; viewport `<model-viewer>` avec orbite/zoom/pan, tourne-disque,
>= 4 environnements, filaire, isolation des canaux, HUD (faces, sommets, **epaisseur en mm**, **dimensions reelles en mm**
— Meshy n'affiche aucune dimension) ; **rendu tourne-disque facon NFT** (N images -> mp4/webm par ffmpeg deja present) ;
tranche coloree ou texturee ; enregistrement `GB._BUILDERS.setdefault("card", ...)` **au chargement du module**.
**Mesurable**
- `mesh_stats("card")["triangles"]` != celui de `sphere` (preuve que le maillage est bien pris, cf. piege 9).
- **determinant UV negatif sur TOUT triangle** (invariant `test_uv_orientation.py`) : le texte de la carte n'est jamais en miroir.
- 3 ilots UV **disjoints** : aucun triangle recto ne recouvre un triangle verso ou tranche dans l'atlas (test de chevauchement).
- epaisseur reglable 0,20 a 1,20 mm, defaut **0,32 mm** (carte a jouer reelle) ; le HUD affiche mm ET pouces.
- HUD affiche **largeur x hauteur x epaisseur en mm** (Meshy : aucune dimension, aucune unite).
- tourne-disque : >= 90 images, boucle sans saut, >= 24 i/s, fichier < 8 Mo pour 3 s en 1080x1080.
**Victoire** Deux captures de la visionneuse : la sienne montre un objet flottant et un HUD « Faces / Sommets » ; la
mienne montre une carte de 63 x 88 x 0,32 mm dont on VOIT la tranche et le verso pendant la rotation, avec les
dimensions physiques ecrites. Un critique qui ne sait rien du sujet voit une carte d'un cote, une forme de l'autre.

### Piece 06 — Textures (2D et PBR)
**Barre** Sorceress Material Forge.
**Fichiers** `js/mod-texture.js`, `css/mod-texture.css`, `assets/papers/`, `cards/texture.py`, `test_cards_texture.py`.
**Livrables** couche 2D sous l'illustration (z=10) et par-dessus (z=30) : grain de papier, lin, toile, effet foil,
holographique, usure des bords, vernis selectif, **le tout module en opacite et en mode de fusion** ; catalogue local
>= 24 matieres ; derivation des **8 maps PBR** de la face via `pbr_service.derive_maps` (reutilisation, pas de reecriture)
avec les curseurs de derivation exposes ; cuisson des niveaux par `pbr_service.bake_levels` ; **vignettes des 8 maps**
avec, sous chacune, le rapport `map_report` (moyenne, informative oui/non) ; resolution de sortie 1k/2k/4k.
**Mesurable**
- **8** maps produites et affichees : basecolor, normal, roughness, metallic, ao, height, emissive, orm (Meshy : 5, ni AO ni height).
- >= 24 matieres 2D livrees en local, 0 octet reseau.
- chaque map porte une mesure lue sur les **octets encodes** (`effective_levels`), pas une promesse de curseur.
- 4k = 4096x4096 disponible ; `height` et `normal` encodables en **16 bits**.
- l'ORM respecte la convention R=AO, V=rugosite, B=metal, verifiee par un test qui relit les canaux.
**Victoire** Cote a cote des planches de maps : la mienne en montre 8 avec une valeur mesuree sous chacune ; la sienne en
montre moins, et sans chiffre. Sur une capture de la carte en 3D, le grain du papier accroche la lumiere de facon
differente selon l'angle chez moi (normal + roughness reels) et reste plat chez l'autre.

### Piece 07 — Export impression
**Barre** nanDECK — 300 DPI par defaut, poker = **750x1050 px** exactement, planche A4 = **2480x3508 px**, `/MediaBox
595 x 841.89`, traits de coupe **vectoriels** (`m`/`l`/`S`, `1.0 0.0 0.0 RG`), gouttiere exacte a 11,338 pt, duplex
miroir correct. **Mais** : ni TrimBox ni BleedBox, fond perdu manuel, mot « safe » absent des 202 pages, aucun controle
avant vol.
**Fichiers** `js/mod-print.js`, `css/mod-print.css`, `cards/print.py`, `test_cards_print.py`.
**Livrables** selecteur de format nomme (les 12 de la table, mm **et** pouces **et** px affiches en permanence) ;
DPI 150/300/600 ; fond perdu et zone sure reglables et **dessines en surimpression pendant qu'on compose** (couche core
z=90), masquables d'**un clic** — jamais a commenter dans du code ; export **carte seule** (PNG 8/16 bits avec alpha,
JPEG q95) ; **planche imposee** A4/Letter/A3, portrait/paysage, marges, gouttiere, centrage, lignes x colonnes calculees
seules, pagination ; traits de coupe / croix / lignes, epaisseur et couleur reglables ; **gouttiere avec fond perdu et
double trait de coupe** (nanDECK ne l'a pas) ; **recto/verso** avec miroir horizontal correct pour retournement bord long ;
**PDF multipage 300 DPI avec `/TrimBox` et `/BleedBox` par page** ; **controle avant vol** : liste des cartes dont un
texte sort de la zone sure ou dont une image tombe sous 300 DPI, avec le chiffre.
**Mesurable**
- `poker_us` -> carte exportee **825x1125 px** ; `poker_eu` -> **815x1110 px** ; planche A4 -> **2480x3508 px** ; A4 a 600 DPI -> **4961x7016**. Tolerance : **0 pixel**.
- PNG exporte : chunk `pHYs` present et egal a 11811 px/m (= 300 DPI) — nanDECK ecrit 299,9994.
- PDF : `/MediaBox [0 0 595.2 841.92]`, **et `/TrimBox` + `/BleedBox` presents sur CHAQUE page** (le PDF nanDECK n'a que MediaBox).
- traits de coupe **vectoriels** dans le PDF, pas des pixels.
- A4, marges 10 mm, gouttiere 4 mm, poker : **2 colonnes x 3 lignes = 6 cartes**, gouttiere mesuree = 11,34 pt (parite nanDECK).
- duplex : la carte 1 du recto fait face a la carte en position miroir du verso (F1 <-> B7 sur une grille 2x3).
- controle avant vol : au moins 2 regles (texte hors zone sure, image < 300 DPI), avec le nom de la carte et le chiffre.
- rendu d'un deck de 60 cartes + PDF A4 en **< 30 s**.
**Victoire** Le critique ouvre les deux PDF dans un lecteur qui affiche les boites : le mien annonce TrimBox et BleedBox,
le sien seulement MediaBox — un imprimeur voit la difference en 2 s. Et sur les deux captures de l'editeur, la mienne
montre les trois cadres (fond perdu / coupe / zone sure) dessines par-dessus la carte pendant l'edition ; l'autre montre
un editeur de script, ou rien du tout.

### Piece 08 — Export 3D
**Barre** Meshy — 8 formats (fbx, obj, glb, usdz, stl, blend, 3mf, dxf), **pas de `.gltf`**, 5 maps PBR sans AO ni
height, echelle a une seule dimension (hauteur en cm), **plan gratuit plafonne a 10 modeles/mois**, badge PRO sur le
bouton, retention 3 jours.
**Fichiers** `js/mod-gltf.js`, `css/mod-gltf.css`, `cards/gltf.py`, `test_cards_gltf.py`.
**Livrables** export **`.glb` ET `.gltf`** (via `material_store.glb_to_gltf`) ; ZIP avec les **8** PNG + `manifest.json`
+ le maillage ; construction par `gltf_builder.build_glb(maps, props, mesh="card")` — **aucune ligne de `gltf_builder.py`
modifiee**, enregistrement par `setdefault` ; atlas unique portant les 3 ilots (donc **un seul materiau suffit**, pas de
patch de `build_glb`) ; bordereau d'export chiffre avant telechargement (poids par fichier) ; resolutions 1k/2k/4k ;
export du deck entier en un ZIP ; `extras` documentant la convention facteur=1.0 + les dimensions physiques en mm.
**Mesurable**
- **`.glb` + `.gltf`** tous deux telechargeables (Meshy : `.glb` seul).
- ZIP contenant **8** PNG nommes exactement `basecolor/normal/roughness/metallic/ao/height/emissive/orm` (Meshy : 5, sans AO ni height).
- GLB : 4 textures reellement referencees (basecolor, normal, orm, emissive), `metallicFactor == 1.0` et `roughnessFactor == 1.0` (niveaux cuits), `KHR_materials_*` emis quand pertinent.
- `mesh_stats("card")` retourne un compte de triangles **stable et documente**, different de `sphere`.
- le GLB s'ouvre dans `<model-viewer>` **et** rapporte les bonnes dimensions physiques : 63 x 88 x 0,32 mm inscrites dans `extras`.
- **0 credit, 0 compte, 0 plafond mensuel, 0 retention** : le fichier est ecrit en local.
- poids d'un GLB carte en 2k < 6 Mo.
**Victoire** Deux ecrans d'export cote a cote : le sien liste 8 formats mais le bouton porte un badge PRO et la note
« 10 modeles / mois » ; le mien telecharge tout de suite. Et en depliant les deux ZIP, le critique compte 8 fichiers de
maps d'un cote, 5 de l'autre — avec `ao.png` et `height.png` presents seulement chez moi.

---

## 5. Risques

1. **`core.js` mal gele = tout le parallelisme s'ecroule.** Si `CF.patch` n'interdit pas reellement les cles etrangeres,
   deux builders ecriront le meme sous-arbre et le dernier merge gagnera en silence. `core.js` et `lint_cardforge.py`
   doivent etre ecrits, testes et geles **avant** que le premier builder demarre.
2. **Deux renderers = le bug WYSIWYG deja vu ici** (`test_export_wysiwyg.py`). Un seul moteur : le navigateur rend la
   carte a `geom.canvas_px`, le backend ne fait que l'**imposition**. Si un builder redessine cote serveur, l'ecran et le
   fichier divergeront.
3. **P5 detient `card_mesh()` dont P8 depend.** La signature est gelee dans `contract.py`, mais si P5 livre en retard,
   P8 doit pouvoir travailler sur un bouchon. Prevoir un `card_mesh` de reference (boite non arrondie) dans
   `contract.py` des le depart.
4. **Le nombre de pixels a 600 DPI** : A4 = 34,8 Mpx dans un canvas navigateur. Passe sur desktop, pas garanti ailleurs.
   L'imposition reste **backend/PIL** ; le navigateur ne rend que des cartes.
5. **Le trait de coupe a 37,5 px** (demi-pixel) sur les formats imperiaux. Rendu en sous-pixel, c'est juste ; arrondi
   par mégarde, la carte perd 1 px et la parite avec nanDECK tombe.
6. **Le backend :8765 doit etre relance** pour que `/cardforge` et `/api/cards` existent. Interdit de le tuer a l'aveugle
   — a coordonner avec l'utilisateur.
7. **`repatch_all.py` sur cette chaine detruit vfxrack/subs** (mtimes ex aequo). Le patcher cardforge se lance seul.
8. **`Image.init()` oublie** = plantage du PDF a la premiere planche, uniquement en prod. A mettre dans `cards/print.py`
   au niveau module.
9. **Le catalogue de depart (>= 60 faces, >= 24 matieres, >= 20 cadres)** est du contenu, pas du code : sans lui, l'ecran
   vide perd le duel contre les 300 illustrations de Clash of Decks avant meme la premiere fonctionnalite.
10. **Theme clair** : rien ne le propage a l'iframe aujourd'hui. Soit on l'assume sombre (comme les 4 autres labs), soit
    c'est un travail NEUF a affecter a CORE — pas a une piece.
