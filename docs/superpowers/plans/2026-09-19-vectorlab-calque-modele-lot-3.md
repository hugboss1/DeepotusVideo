# Vectorlab — LOT 3 « Calque modèle et pixel-art guidé » — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Spec validé le 19/09/2026 :
> `docs/superpowers/specs/2026-09-19-vectorlab-calque-modele-pixel-design.md`
> (réponses C / D / C / D, approche « le document connaît son modèle »).
> Contrats : `doc.pixelart` + `op_pixelart` (mod-doc), tampons `{w, h,
> data}`, `mod-pixelart` / `mod-solide` feuilles pures, `etat.px`, cache des
> tampons de `mod-pixelui`, pièces `{nom, tris, couleur, hauteur_mm}` de la
> chaîne R12 (`glb_de_pieces`, 3MF par objet). Branche
> `chantier/vectorlab-affinity`, après le lot 2 (`a4e33f3`). Ce plan est
> COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (19/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — statiques seuls, aucune relance.**
>
> **Livré** (plan `09ac83d`, code `c636dd2` → `9792ac1`, 8 commits) :
> mod-doc `pixelart.modele {id, cellule}` + `calque` ; mod-pixelart
> `cellule_et_cible`, `echantillon_cellule` (exact / moyenne / dominante — la
> dominante rend la moyenne de la classe gagnante à 64 niveaux),
> `remplir_depuis_modele`, `couleurs_utilisees` ; mod-solide
> `rects_de_pixels` (runs fusionnés verticalement), `pixels_vers_pieces`
> (une pièce colorée et une hauteur par couleur, socle optionnel, y
> retourné), `hauteurs_par_luminosite` ; mod-contexte champ Pipette ;
> mod-impression `reglages_lire` mode `pixelart` (cellule mm, hmin / hmax),
> `hauteurs_lire` ; UI : section « Modèle » (désigner — atténue à 0,6 PUIS
> verrouille, une image verrouillée n'est plus une cible de commande,
> mesuré —, cellule ↔ cible liées, boutons 4·8·16·32·64, tuile d'art, Créer
> le calque pixel, Remplir depuis le modèle, Retirer), grille du modèle en
> aperçu dans l'overlay (plafond 65 536 cellules), pipette Alt+clic qui lit
> la CELLULE DU MODÈLE quand le calque pixel est édité (droit → swatch),
> section Couleurs (swatches : clic / droit / Alt-retire / + courante /
> Palette depuis le modèle ; couleurs utilisées → swatches), `VL.pixelTampon`,
> `VL.actions.pixel.designerModele / creerCalquePixel / remplirDepuisModele /
> paletteDepuisModele` ; dialogue Impression 3D : mode « Pixel-art » proposé
> d'office quand un calque pixel existe, cellule mm, hauteurs min / max,
> table par couleur préremplie par luminosité et modifiable, socle, lot = un
> STL par couleur.
>
> **TDD tenu** : RED ×5 constatés ; bancs pixel_doc 20 → **23**, pixelart 43
> → **54**, solide 52 → **62**, contexte 21 → **24**, impression_ui 11 →
> **14** ; `run.mjs` par code de sortie (0).
>
> **Prouvé en réel** (8799, données isolées, 1400 × 900, modèle 64 × 64 à
> quatre aplats rouge / vert / bleu / jaune) : Désigner → `modele {mod, 16}`,
> verrou, opacité 0,6 (après correctif, rechargement) ; grille du modèle :
> cadre + **10 lignes** (5 + 5) à cellule 16, cible 4 ; Créer → calque
> « pixel », image **4 × 4 sur le rectangle exact du modèle** (40, 40, 256,
> 256), éditée, grille d'aperçu retirée ; pipette moyenne (0,0) → `#FF0000`,
> (3,0) → `#00C800`, exacte (0,3) → `#0000FF`, dominante (3,3) → `#FFDC00`,
> Alt+droit → swatch `#FF0000` ; Remplir → 4 × 4 avec les quatre aplats aux
> bonnes cases ; couleurs utilisées = les 4 ; Palette depuis le modèle (4) →
> 4 swatches ; « → swatches » et « + courante » sans doublon (4) ;
> **Impression 3D** : mode `pixelart` proposé d'office, table préremplie
> (jaune 5 > vert 3,58 > rouge 1,74 > bleu 1), Aperçu → **4 pièces `px_*`
> colorées d'aire 16 mm² chacune** (4 px × 2 mm²… soit 2 × 2 px × 4 mm²),
> GLB à 4 matériaux `loaded`, ligne bleue éditée à 7 → hauteur 7, socle 1 →
> 5 pièces, Lot → `preuve-lot3-lot-20260919` : 5 STL, `plateau.3mf` à 5
> objets colorés (`#FF0000FF … #D1C7B3FF`), `impression.json.couleurs`. 0
> erreur console.
>
> **Déployé** : 12 fichiers installés = base `a4e33f3` → sauvegarde
> `_backup_predeploy_2026-09-19-pixel-lot3` → `git archive HEAD` → 12/12 =
> cible ; l'installé (8765) sert `pixels_vers_pieces`. Aucun Python : pas de
> relance.
>
> **Reste (assumé)** : les rectangles adjacents d'une même couleur gardent
> des faces internes (un slicer les avale) ; un seul modèle par document ;
> la grille d'aperçu suit le rectangle du modèle sans sa rotation ; les
> palettes nommées partagées restent au lot 4.

**Goal :** désigner une image comme modèle, régler cellule et taille cible
avec la grille en aperçu, créer le calque pixel dessus, piocher les couleurs
DANS le modèle (exacte / moyenne / dominante), pré-remplir, composer ses
swatches et voir les couleurs utilisées, exporter vers Spritelab / Tilelab
(existant) et imprimer en 3D une pièce par couleur avec une hauteur par
couleur.

**Architecture :** purs — `mod-pixelart` (`cellule_et_cible`,
`echantillon_cellule`, `remplir_depuis_modele`, `couleurs_utilisees`),
`mod-solide` (`rects_de_pixels`, `pixels_vers_pieces`,
`hauteurs_par_luminosite`), `mod-doc` (`pixelart.modele`, `pixelart.calque`),
`mod-contexte` (`pxPipetteMode`), `mod-impression` (`reglages_lire.cellule_mm`,
`hauteurs_lire`) ; UI — `mod-pixelui` (section Modèle, overlay de grille,
pipette modèle, remplissage, section Couleurs), `mod-impression` (mode
« Pixel-art », table des hauteurs). Aucun Python.

---

## Décisions d'implémentation

- **Modèle** : `doc.pixelart.modele = { id, cellule }`, `doc.pixelart.calque
  = id`. Le panneau propose « Désigner comme modèle » quand une image est
  sélectionnée ; désigner pose aussi `verrou` et une opacité 0,6 si l'objet
  n'en a pas (commande unique).
- **Grille en aperçu** : dessinée dans `surOverlay` tant que
  `modele && !calque` (ou calque absent), lignes tous les `cellule` px
  natifs du modèle projetées par son rectangle ; plafond 65 536 cellules.
- **Créer le calque pixel** : `cellule_et_cible` → tampon transparent →
  `deposerNouvelleImage` → commande : calque « pixel » créé au-dessus du
  calque du modèle s'il n'existe pas, objet posé sur `{x, y, w, h}` du
  modèle, `op_pixelart({ calque: id })` ; puis `editer(id)`.
- **Pipette modèle** : dans le `pointerdown` Alt+clic existant, si
  `doc.pixelart.modele` et `courant().id === doc.pixelart.calque`, la
  cellule du modèle sous le pixel d'art = `{ x: px·cellule, y: py·cellule,
  w: cellule, h: cellule }` ; `echantillon_cellule(tamponModele, rect,
  etat.px.pipetteMode)` ; le tampon du modèle vient du cache (`tamponsDe`).
- **Remplir depuis le modèle** : remplace le tampon entier du calque pixel
  (dit), `commettre` ; palette = swatches si la case « ramener aux
  swatches » est cochée.
- **Couleurs utilisées** : recalculées par `couleurs_utilisees(t, 64)` à
  chaque `rendrePanneau` quand le tampon existe (coût O(pixels), 64 × 64 →
  négligeable ; au-delà de 1 M pixels on affiche « trop grand »).
- **Impression Pixel-art** : mode `pixelart` du dialogue, visible si
  `doc.pixelart.calque` (ou une image sélectionnée) ; cellule en mm
  (`impCellule`, défaut 2), socle (`impSocle`), hauteurs min / max
  (`impHmin` 1, `impHmax` 5) et une table `#impHauteurs` (une ligne par
  couleur : pastille, hex, `<input>` mm) préremplie par
  `hauteurs_par_luminosite` ; `pixels_vers_pieces(img, cellule_mm,
  hauteurs, { socle_mm })` → pièces `{nom: "px_rrggbb", couleur, hauteur_mm,
  tris}` (+ « socle ») ; y retourné (SVG y-bas → plateau y-haut) comme les
  tuiles.
- **Fusion des pixels en rectangles** : `rects_de_pixels(img, couleur)` :
  runs horizontaux par ligne, puis fusion verticale des runs de mêmes bornes
  x sur des lignes consécutives → rectangles ; chaque rectangle devient un
  anneau, l'union des rectangles d'une couleur = un multipolygone SANS
  martinez (les rectangles ne se chevauchent pas, `extruder` accepte
  plusieurs polygones ; les faces internes entre rectangles adjacents sont
  redondantes mais fermées — dit au relevé, un slicer les avale ; l'aire
  mesurée reste exacte).

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `mod-doc.js` + `qa/pixel_doc.test.mjs` | `modele`, `calque` (T1) |
| `mod-pixelart.js` + `qa/pixelart.test.mjs` | `cellule_et_cible`, `echantillon_cellule`, `remplir_depuis_modele`, `couleurs_utilisees` (T2) |
| `mod-solide.js` + `qa/solide.test.mjs` | `rects_de_pixels`, `pixels_vers_pieces`, `hauteurs_par_luminosite` (T3) |
| `mod-contexte.js` + `qa/contexte.test.mjs` ; `mod-impression.js` + `qa/impression_ui.test.mjs` | `pxPipetteMode` ; `cellule_mm`, `hauteurs_lire` (T4) |
| `mod-pixelui.js`, `vectorlab.css` | modèle, grille, calque pixel, pipette, remplissage, couleurs (T5) |
| `mod-impression.js`, `vectorlab.css` | mode Pixel-art, table des hauteurs (T6) |

---

### Task 1 : `pixelart.modele` et `pixelart.calque` (pur)

- [ ] **RED** (`pixel_doc.test.mjs`) :

```js
{
  const d = base();
  op_pixelart(d, { modele: { id: "i1", cellule: 16 }, calque: "i1" });
  ok("modele {id, cellule} et calque acceptés", d.pixelart.modele.id === "i1" && d.pixelart.modele.cellule === 16 && d.pixelart.calque === "i1");
  let refus = 0;
  for (const m of [{ modele: { id: "i1" } }, { modele: { id: "", cellule: 4 } }, { modele: { id: "i1", cellule: 0 } }, { calque: 7 }]) { try { op_pixelart(base(), m); } catch { refus++; } }
  ok("modele sans cellule, id vide, cellule 0, calque non-chaîne → refusés", refus === 4);
  parserDoc(JSON.parse(JSON.stringify(d)));
  op_pixelart(d, { modele: null, calque: null });
  ok("retirés par null", d.pixelart === undefined || (d.pixelart.modele === undefined && d.pixelart.calque === undefined));
}
```

- [ ] **Implémenter** (mod-doc) : `_CLES_PIXELART` += `"modele", "calque"` ; validation : `modele` = objet `{id: chaîne non vide, cellule: entier ≥ 1}`, `calque` = chaîne non vide ; `op_pixelart` : `if (k === "modele") p.modele = { id: String(v.id || ""), cellule: Math.round(+v.cellule) }; else if (k === "calque") p.calque = v;` (avant la branche symetrie).
- [ ] Vert (`pixel_doc` 23), commit `… -m "vectorlab lot 3 : doc.pixelart.modele et calque (pur)"`.

### Task 2 : cellule / cible, échantillon, remplissage, couleurs utilisées (pur)

- [ ] **RED** (`pixelart.test.mjs`) :

```js
{
  const { cellule_et_cible, echantillon_cellule, remplir_depuis_modele, couleurs_utilisees } = await import("../js/mod-pixelart.js");
  ok("cellule 16 sur 64 × 48 → cible 4 × 3", JSON.stringify(cellule_et_cible({ w: 64, h: 48 }, { cellule: 16 })) === JSON.stringify({ cellule: 16, cible_w: 4, cible_h: 3 }));
  ok("cible 32 sur 100 × 60 → cellule 3, cible réelle 34 × 20", JSON.stringify(cellule_et_cible({ w: 100, h: 60 }, { cible: 32 })) === JSON.stringify({ cellule: 3, cible_w: 34, cible_h: 20 }));
  ok("cellule > image → 1 × 1 ; cellule < 1 → 1", cellule_et_cible({ w: 10, h: 10 }, { cellule: 50 }).cible_w === 1 && cellule_et_cible({ w: 10, h: 10 }, { cellule: 0 }).cellule === 1);
  // un modèle 8 × 8 : cellule (0,0) 4 × 4 = 12 rouges + 4 bleus, cellule (4,0) transparente
  const m = tampon(8, 8); for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) { const k = (y * 8 + x) * 4; const bleu = (x === 3 && y < 4); m.data[k] = bleu ? 0 : 255; m.data[k + 2] = bleu ? 255 : 0; m.data[k + 3] = 255; }
  const r = { x: 0, y: 0, w: 4, h: 4 };
  ok("exact = le pixel du centre (2,2) → rouge", echantillon_cellule(m, r, "exact") === "#FF0000");
  ok("moyenne = (12·255 + 0)/16 rouge, (4·255)/16 bleu → #BF0040", echantillon_cellule(m, r, "moyenne") === "#BF0040", echantillon_cellule(m, r, "moyenne"));
  ok("dominante → rouge", echantillon_cellule(m, r, "dominante") === "#FF0000");
  ok("cellule transparente → null ; mode inconnu → refus", echantillon_cellule(m, { x: 4, y: 0, w: 4, h: 4 }, "moyenne") === null && (() => { try { echantillon_cellule(m, r, "zz"); return false; } catch { return true; } })());
  const f = remplir_depuis_modele(m, 2, 2, 4, "dominante");
  ok("remplir 8 × 8 par cellule 4 → 2 × 2 : (0,0) rouge, (1,0) transparent", f.w === 2 && f.h === 2 && f.data[0] === 255 && f.data[3] === 255 && f.data[7] === 0);
  const fp = remplir_depuis_modele(m, 2, 2, 4, "moyenne", ["#000000", "#FF0000"]);
  ok("avec palette : la moyenne #BF0040 est ramenée à #FF0000", fp.data[0] === 255 && fp.data[1] === 0 && fp.data[2] === 0);
  const u = couleurs_utilisees(m);
  ok("couleurs utilisées triées par fréquence : rouge (12) puis bleu (4)", u.length === 2 && u[0] === "#FF0000" && u[1] === "#0000FF", u.join());
  ok("couleurs utilisées : plafond respecté", couleurs_utilisees(m, 1).length === 1);
}
```

- [ ] **Implémenter** (mod-pixelart) :

```js
/* ── lot 3 : le calque modèle — cellule ↔ cible, pipette sur le modèle, remplissage, couleurs utilisées ── */
export function cellule_et_cible(nat, { cellule, cible } = {}) {
  const w = Math.max(1, nat.w | 0), h = Math.max(1, nat.h | 0);
  let c = cellule !== undefined ? Math.max(1, Math.round(+cellule) || 1) : Math.max(1, Math.round(w / Math.max(1, Math.round(+cible) || 1)));
  return { cellule: c, cible_w: Math.max(1, Math.ceil(w / c)), cible_h: Math.max(1, Math.ceil(h / c)) };
}
export const MODES_PIPETTE = ["exact", "moyenne", "dominante"];
const _hex = (r, g, b) => "#" + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0").toUpperCase()).join("");
export function echantillon_cellule(img, rect, mode = "moyenne") {
  if (!MODES_PIPETTE.includes(mode)) throw new Error("pipette : mode exact, moyenne ou dominante");
  const x0 = Math.max(0, rect.x | 0), y0 = Math.max(0, rect.y | 0), x1 = Math.min(img.w, x0 + Math.max(1, rect.w | 0)), y1 = Math.min(img.h, y0 + Math.max(1, rect.h | 0));
  if (x0 >= x1 || y0 >= y1) return null;
  if (mode === "exact") { const cx = Math.min(x1 - 1, x0 + ((x1 - x0) >> 1)), cy = Math.min(y1 - 1, y0 + ((y1 - y0) >> 1)), k = (cy * img.w + cx) * 4; return img.data[k + 3] ? _hex(img.data[k], img.data[k + 1], img.data[k + 2]) : null; }
  let sr = 0, sg = 0, sb = 0, n = 0; const votes = new Map();
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
    const k = (y * img.w + x) * 4; if (!img.data[k + 3]) continue;
    n++; sr += img.data[k]; sg += img.data[k + 1]; sb += img.data[k + 2];
    const q = ((img.data[k] >> 2) << 12) | ((img.data[k + 1] >> 2) << 6) | (img.data[k + 2] >> 2);
    votes.set(q, (votes.get(q) || 0) + 1);
  }
  if (!n) return null;
  if (mode === "moyenne") return _hex(sr / n, sg / n, sb / n);
  let best = -1, bn = 0; for (const [q, c] of votes) if (c > bn) { bn = c; best = q; }
  // la dominante rend la MOYENNE des pixels de la classe gagnante (pas le centre de classe)
  let r = 0, g = 0, b = 0, m = 0;
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const k = (y * img.w + x) * 4; if (!img.data[k + 3]) continue; const q = ((img.data[k] >> 2) << 12) | ((img.data[k + 1] >> 2) << 6) | (img.data[k + 2] >> 2); if (q === best) { r += img.data[k]; g += img.data[k + 1]; b += img.data[k + 2]; m++; } }
  return _hex(r / m, g / m, b / m);
}
export function remplir_depuis_modele(modele, cible_w, cible_h, cellule, mode = "moyenne", palette = null) {
  const out = _tampon(cible_w, cible_h);
  for (let y = 0; y < cible_h; y++) for (let x = 0; x < cible_w; x++) {
    const hex = echantillon_cellule(modele, { x: x * cellule, y: y * cellule, w: cellule, h: cellule }, mode);
    if (!hex) continue;
    const [r, g, b] = _rgb(hex), k = (y * cible_w + x) * 4;
    out.data[k] = r; out.data[k + 1] = g; out.data[k + 2] = b; out.data[k + 3] = 255;
  }
  return palette && palette.length ? quantifier(out, palette) : out;
}
export function couleurs_utilisees(img, max = 64) {
  const votes = new Map();
  for (let k = 0; k < img.w * img.h; k++) { if (!img.data[k * 4 + 3]) continue; const h = _hex(img.data[k * 4], img.data[k * 4 + 1], img.data[k * 4 + 2]); votes.set(h, (votes.get(h) || 0) + 1); }
  return [...votes.entries()].sort((a, b) => b[1] - a[1]).slice(0, Math.max(1, max | 0)).map(([h]) => h);
}
```

- [ ] Vert (`pixelart` 54), commit `… -m "vectorlab lot 3 : cellule / cible, echantillon de cellule (exact, moyenne, dominante), remplir depuis le modele, couleurs utilisees (purs)"`.

### Task 3 : rectangles de pixels, pièces par couleur, hauteurs par luminosité (pur)

- [ ] **RED** (`solide.test.mjs`) :

```js
{
  const { rects_de_pixels, pixels_vers_pieces, hauteurs_par_luminosite } = await import("../js/mod-solide.js");
  const img = { w: 4, h: 3, data: new Uint8ClampedArray(4 * 3 * 4) };
  const pose = (x, y, rgb) => { const k = (y * 4 + x) * 4; img.data[k] = rgb[0]; img.data[k + 1] = rgb[1]; img.data[k + 2] = rgb[2]; img.data[k + 3] = 255; };
  // rouge : un bloc 2 × 2 en (0,0) + un pixel isolé (3,2) ; bleu : la colonne x=2 sur 3 lignes
  pose(0, 0, [255, 0, 0]); pose(1, 0, [255, 0, 0]); pose(0, 1, [255, 0, 0]); pose(1, 1, [255, 0, 0]); pose(3, 2, [255, 0, 0]);
  pose(2, 0, [0, 0, 255]); pose(2, 1, [0, 0, 255]); pose(2, 2, [0, 0, 255]);
  const rr = rects_de_pixels(img, "#FF0000");
  ok("rouge : 2 rectangles (le bloc 2 × 2 fusionné, le pixel isolé)", rr.length === 2 && rr.some((r) => r.w === 2 && r.h === 2) && rr.some((r) => r.w === 1 && r.h === 1), JSON.stringify(rr));
  ok("bleu : 1 rectangle 1 × 3 (runs fusionnés verticalement)", JSON.stringify(rects_de_pixels(img, "#0000FF")) === JSON.stringify([{ x: 2, y: 0, w: 1, h: 3 }]));
  const P = pixels_vers_pieces(img, 2, { "#FF0000": 4, "#0000FF": 1.5 }, { socle_mm: 0 });
  const aire = (tris) => tris.filter((t) => t[0][2] === t[1][2] && t[1][2] === t[2][2] && t[0][2] > 0).reduce((s, [a, b, c]) => s + Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2, 0);
  ok("deux pièces nommées par hex, colorées, à leur hauteur", P.length === 2 && P[0].nom === "px_ff0000" && P[0].couleur === "#FF0000" && P[0].hauteur_mm === 4 && P[1].hauteur_mm === 1.5);
  ok("aire du capot rouge = 5 pixels × 4 mm² = 20 ; bleu = 3 × 4 = 12", pres(aire(P[0].tris), 20, 1e-6) && pres(aire(P[1].tris), 12, 1e-6), `${aire(P[0].tris)} / ${aire(P[1].tris)}`);
  ok("volume rouge = 20 × 4 = 80", pres(volume_de(P[0].tris), 80, 1e-6), volume_de(P[0].tris));
  ok("y retourné : le pixel (3,2) rouge a son y en mm ≤ 0 (plateau y-haut)", P[0].tris.flat().some((p) => p[1] < 0));
  const S = pixels_vers_pieces(img, 2, { "#FF0000": 4, "#0000FF": 1.5 }, { socle_mm: 1 });
  ok("socle : une pièce de plus, 8 × 6 mm, sous les pièces (z de 0 à 1) et les pièces posées sur lui", S.length === 3 && S[2].nom === "socle" && pres(volume_de(S[2].tris), 48, 1e-6) && Math.min(...S[0].tris.flat().map((p) => p[2])) === 1);
  ok("couleur sans hauteur → hauteur par défaut 2", pixels_vers_pieces(img, 2, {}, {})[0].hauteur_mm === 2);
  const H = hauteurs_par_luminosite(["#000000", "#FFFFFF", "#808080"], 1, 5);
  ok("hauteurs par luminosité : noir 1, blanc 5, gris ≈ 3", H["#000000"] === 1 && H["#FFFFFF"] === 5 && pres(H["#808080"], 3, 0.1), JSON.stringify(H));
  ok("une seule couleur → max", hauteurs_par_luminosite(["#123456"], 1, 5)["#123456"] === 5);
}
```

- [ ] **Implémenter** (mod-solide) :

```js
/* ── lot 3 : pixel-art → pièces (une par couleur, une hauteur par couleur) ── */
const _hexDe = (d, k) => "#" + [d[k], d[k + 1], d[k + 2]].map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");
// runs horizontaux d'une couleur, fusionnés verticalement quand les bornes x coïncident
export function rects_de_pixels(img, couleur) {
  const cible = String(couleur).toUpperCase(), ouverts = [], out = [];
  for (let y = 0; y < img.h; y++) {
    const runs = [];
    for (let x = 0; x < img.w; x++) {
      const k = (y * img.w + x) * 4;
      if (img.data[k + 3] && _hexDe(img.data, k) === cible) { const d = runs[runs.length - 1]; if (d && d.x + d.w === x) d.w++; else runs.push({ x, w: 1 }); }
    }
    const suivants = [];
    for (const r of runs) {
      const o = ouverts.find((q) => q.x === r.x && q.w === r.w && q.y + q.h === y);
      if (o) { o.h++; suivants.push(o); } else suivants.push({ x: r.x, y, w: r.w, h: 1 });
    }
    for (const o of ouverts) if (!suivants.includes(o)) out.push(o);
    ouverts.length = 0; ouverts.push(...suivants);
  }
  out.push(...ouverts);
  return out;
}
export function hauteurs_par_luminosite(couleurs, min_mm = 1, max_mm = 5) {
  const lum = (h) => { const r = parseInt(h.slice(1, 3), 16), g = parseInt(h.slice(3, 5), 16), b = parseInt(h.slice(5, 7), 16); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ls = couleurs.map(lum), lo = Math.min(...ls), hi = Math.max(...ls), out = {};
  couleurs.forEach((c, i) => { out[c] = hi === lo ? +max_mm : Math.round((+min_mm + (ls[i] - lo) / (hi - lo) * (+max_mm - +min_mm)) * 100) / 100; });
  return out;
}
export function pixels_vers_pieces(img, cellule_mm, hauteurs = {}, { socle_mm = 0, hauteur_defaut = 2 } = {}) {
  const c = +cellule_mm; if (!(c > 0)) throw new Error("pixel-art : cellule en mm > 0");
  const couleurs = [...new Set((() => { const s = []; for (let k = 0; k < img.w * img.h; k++) if (img.data[k * 4 + 3]) s.push(_hexDe(img.data, k * 4)); return s; })())];
  const z0 = socle_mm > 0 ? +socle_mm : 0, out = [];
  for (const hex of couleurs) {
    const h = hauteurs[hex] !== undefined ? +hauteurs[hex] : hauteur_defaut;
    if (!(h > 0)) continue;
    const multi = rects_de_pixels(img, hex).map((r) => [[[r.x * c, -r.y * c], [(r.x + r.w) * c, -r.y * c], [(r.x + r.w) * c, -(r.y + r.h) * c], [r.x * c, -(r.y + r.h) * c], [r.x * c, -r.y * c]]]);
    out.push({ nom: "px_" + hex.slice(1).toLowerCase(), couleur: hex, hauteur_mm: h, tris: extruder(multi, h, z0) });
  }
  if (z0 > 0) out.push({ nom: "socle", couleur: COULEUR_DEFAUT, hauteur_mm: z0, tris: extruder([[[[0, 0], [img.w * c, 0], [img.w * c, -img.h * c], [0, -img.h * c], [0, 0]]]], z0, 0) });
  return out;
}
```

- [ ] Vert (`solide` 62), commit `… -m "vectorlab lot 3 : rectangles de pixels, pieces par couleur, hauteurs par luminosite (purs)"`.

### Task 4 : champ de contexte et réglages d'impression (purs)

- [ ] **RED** (`contexte.test.mjs`) : `champs_de("px-crayon", { px: { pipetteMode: "exact" } })` contient `{ id: "pxPipetteMode", type: "select", valeur: "exact" }` avec 3 options ; idem pinceau et seau ; `appliquer_champ({}, "pxPipetteMode", "dominante").px.pipetteMode === "dominante"`, valeur inconnue → `moyenne`. (`impression_ui.test.mjs`) : `reglages_lire({ mode: "pixelart", cellule: "2,5", hmin: "1", hmax: "6" })` → `mode pixelart, cellule_mm 2.5, hmin 1, hmax 6` ; bornes : cellule < 0,2 → 0,2, hmax < hmin → hmax = hmin + 0,2 ; `hauteurs_lire([{ couleur: "#FF0000", mm: "3" }, { couleur: "#00FF00", mm: "abc" }], 2)` → `{ "#FF0000": 3, "#00FF00": 2 }`.
- [ ] **Implémenter** : mod-contexte `select("pxPipetteMode", "Pipette", px.pipetteMode || "moyenne", [{id:"exact",libelle:"Exacte"},{id:"moyenne",libelle:"Moyenne"},{id:"dominante",libelle:"Dominante"}])` ajouté aux cas `px-pinceau`, `px-crayon`, `px-seau` ; `appliquer_champ` : `case "pxPipetteMode": return { px: { ...(e.px||{}), pipetteMode: ["exact","moyenne","dominante"].includes(String(valeur)) ? String(valeur) : "moyenne" } }`. mod-impression : `reglages_lire` accepte `"pixelart"` dans la liste des modes, lit `cellule_mm = Math.max(0.2, num(f.cellule, 2))`, `hmin = Math.max(0.2, num(f.hmin, 1))`, `hmax = Math.max(hmin + 0.2, num(f.hmax, 5))` ; export `hauteurs_lire(lignes, defaut)` → `{ [couleur]: num(mm, defaut) }`.
- [ ] Vert, commit `… -m "vectorlab lot 3 : champ Pipette (exacte / moyenne / dominante) et reglages du mode Pixel-art (purs)"`.

### Task 5 : UI du persona Pixel (modèle, grille, calque pixel, pipette, remplissage, couleurs)

- [ ] `etat.px.pipetteMode = "moyenne"`. Panneau Pixel : nouvelle section **« Modèle »** en tête : si `pa.modele` → « modèle : <href> · cellule N » + boutons « Retirer » ; sinon « Désigner l'image sélectionnée comme modèle » (activé si `sel`). Puis, avec un modèle : cellule (`pxCellule`, liste 4·8·16·32·64 + saisie) et cible (`pxCible`) liés par `cellule_et_cible` (le changement de l'un réécrit l'autre et `op_pixelart({ modele: { id, cellule } })`), case « tuile = cellule d'art » (pose `tuile` = `{w: cible tuile, h}` : la taille d'une tuile d'art, champ `pxTuileArt` défaut 16), bouton **« Créer le calque pixel <cible_w>×<cible_h> »** (désactivé si `pa.calque` existe encore), bouton **« Remplir depuis le modèle »** (+ case « ramener aux swatches ») visible si le calque pixel est édité.
- [ ] Overlay : après la grille existante, si `pa.modele && (!pa.calque || !VL.objetDe(pa.calque))` : lire l'objet modèle, tracer `M x v h` tous les `cellule` px natifs projetés sur son rectangle (plafond 65 536 cellules → cadre seul), classe `px-grille-modele` (`pointer-events: none`, trait `#ffd166` à 0,6).
- [ ] `pointerdown` Alt+clic : si `pa.modele && o.id === pa.calque` → `const M = await tamponModele()` (cache par `tamponsDe([objetModele])`) ; `rect = { x: Math.floor(px) * cellule, y: Math.floor(py) * cellule, w: cellule, h: cellule }` ; `hex = echantillon_cellule(M, rect, etat.px.pipetteMode)` ; `null` → toast « cellule transparente » ; gauche → `etat.px.couleur`, droit → `op_pixelart({ palette: [...(pa.palette||[]), hex] })` sans doublon + toast. (Le geste est asynchrone : `garde`.)
- [ ] Section **« Couleurs »** : swatches (`pa.palette`, pastilles ; clic = courante ; clic droit = secondaire ; Alt+clic = retirer ; bouton « + courante » ; « Palette depuis le modèle » = `palette_extraire(M, N)` → `op_pixelart({ palette })` ; « Extraire » existant conservé), **couleurs utilisées** (`couleurs_utilisees(t, 64)` si `t.w * t.h ≤ 1_000_000`, pastilles cliquables, bouton « → swatches »).
- [ ] `node --check`, `run.mjs` (exit 0), commit `… -m "vectorlab lot 3 : modele designe, grille en apercu, calque pixel sur le modele, pipette depuis le modele, remplissage, swatches et couleurs utilisees"`.

### Task 6 : mode « Pixel-art » de l'impression 3D

- [ ] `mod-impression` : option `<option value="pixelart">Pixel-art (une pièce et une hauteur par couleur)</option>` activée si `doc.pixelart.calque` ou une image sélectionnée ; champs `imp-pixelart` : cellule mm (`impCellule` 2), socle (`impSocle` partagé), hauteur min / max (`impHmin` 1, `impHmax` 5), bouton « Hauteurs par luminosité » et table `#impHauteurs` (pastille, hex, input mm) construite à l'ouverture depuis `couleurs_utilisees(tampon)` ; `construire` : `mode === "pixelart"` → tampon de l'image (`VL.pixelTampon(id)` exposé par mod-pixelui : lit le cache ou charge) → `pixels_vers_pieces(t, r.cellule_mm, hauteurs_lire(lignes, r.hmin), { socle_mm: r.socle })` ; le reste de la chaîne (aperçu GLB coloré, Un STL, Lot) est inchangé ; `impLot` activé en pixelart (un STL par couleur).
- [ ] Commit `… -m "vectorlab lot 3 : impression 3D mode Pixel-art (une piece coloree et une hauteur par couleur, table editable)"`.

### Task 7 : preuve en réel (8799, 1400 × 900)

- [ ] Document + image modèle 64 × 64 à quatre aplats 32 × 32 (rouge, vert, bleu, jaune) déposée par `POST …/images` ; persona Pixel ; désigner le modèle → `doc.pixelart.modele`, verrou posé ; cellule 16 → cible 4 × 4 ; overlay : `.px-grille-modele` avec 5 + 5 lignes ; créer le calque pixel → objet 4 × 4 sur le rectangle du modèle, `pa.calque`, édité ; Alt+clic cellule (0,0) → `#FF0000` ; mode `exact` / `dominante` → même aplat ; Alt+clic droit → swatches contient `#FF0000` ; Remplir → tampon 4 × 4 = 4 couleurs (chaque quart) ; couleurs utilisées = 4 ; Palette depuis le modèle (4) → 4 swatches ; Impression 3D mode Pixel-art, cellule 2 → 4 pièces `px_*` colorées, aire du capot = 4 × 4 px × 4 mm² = 64 chacune, hauteurs par luminosité distinctes (jaune > vert > rouge > bleu), GLB à 4 matériaux, Un STL → dossier avec `couleur` du vote, lot → 4 STL + 3MF à 4 objets colorés (relu sur disque).
- [ ] 0 erreur ; `taskkill` 8799 ; `preset: desktop`.

### Task 8 : déploiement, relevé, mémoire, push

- [ ] Installé = base `a4e33f3` par hash ; sauvegarde `_backup_predeploy_2026-09-19-pixel-lot3` ; `git archive HEAD` ; hash = cible ; aucun Python.
- [ ] Relevé en tête ; mémoire (`spritelab-feuille.md` + MEMORY.md) ; push.
