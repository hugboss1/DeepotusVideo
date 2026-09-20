# Vectorlab classe Affinity — LOT C : grilles, plateau et planches — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot C ; décisions D2 champs optionnels, D3 tuiles objets de premier
> rang, D9 modules purs bancables). Branche : `chantier/vectorlab-affinity`,
> après le lot A (`7c99667`). Ce plan est COMMIS avant le code.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT C LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ.**
>
> **Livré** (7 commits `7a3ccee`→`f818bf7`, poussés) : `mod-grille.js` feuille
> (carrée subdivisée, iso, tri, hex pointe/plat, origine, échelle, tracé
> borné Liang–Barsky, garde 20 000 cellules, aimantation au réseau, hex
> axial avec arrondi cubique, cellules disque/rectangle) ; `mod-aimant.js`
> feuille (bords↔bords, centres↔centres, écarts réguliers, fusion) ; modèle :
> `grille`, `terrains` (5 défauts fusionnés), objet `tuile` ancré (déplacer
> ré-arrondit à la cellule, redimensionner/miroir sans effet), `op_tuiles_peindre`,
> `op_plateau_generer` (grille hex centrée si absente, calque plateau +
> numéros), `planches` + `compilerSVG(doc, {cadre})` ; UI : grille du document
> tracée et aimantante (les guides priment), aimantation aux objets avec
> lignes d'aide (rose bord, or écart), bouton ⌖, outil pinceau de tuiles (K)
> avec aperçu, panneaux Grille / Terrains / Plateau / Planches / Assets,
> export PNG par planche (`vector_<id>_p1_2x.png`).
>
> **TDD tenu** : RED constaté ×5 (modules et exports manquants) ; le banc
> `aimant_objets` a démasqué une sémantique « tout contre tout » (un bord
> s'aimantait au centre d'un voisin) corrigée en paires de même nature.
> Bancs : node **514 contrôles** (+97 : grille 33, aimant_objets 13,
> tuiles 30, planches 15, plateau_ui 6), pytest `test_vector_docs` **27
> passed** (+2). Le snapshot du compilateur est inchangé.
>
> **Prouvé en réel** (backend du worktree 8799, données isolées, viewport
> émulé 1400×900) : hex 40 → 296 hexagones tracés (`#dzGrille` 812 px de
> haut), bouton « ⊞ hex 40 pointe » ; iso → 79 lignes ; carrée ÷4 → 208
> lignes, « ⊞ 40 ÷4 » ; `aimantePt(41.2, 38.7)` → (40, 40). Générer rayon 3
> terrain forêt numéroté → 37 tuiles `data-terrain="foret"` (66 px de haut)
> + 37 textes, grille centrée en (600, 450), outil `tuiles` actif, calque
> « plateau » actif. Pinceau (terrain mer) par `pointerdown/move/up` sur
> (0,0), (1,0), (5,0 vide) → aperçu 2 puis toast « 2 tuile(s) peinte(s), 1
> posée(s) », 38 tuiles, les trois en `mer`. Aimantation : r2 glissé à 223
> se colle à **220** (bord droit de r1) avec deux lignes `aimant-bord`
> `#d05aa0` ; r3 glissé à 443 se pose à **440** (écart 80 reproduit, ligne
> `aimant-ecart`) — mesuré calques de tuiles cachés, sinon un bord de tuile
> plus proche gagne (443,44 : le plus proche gagne, comportement voulu) ;
> aimant coupé → 0 ligne, bouton rallumé. Planches : « ＋ sélection » → p1
> (100,700,400×80), « ＋ page » → p2 (540,0,1200×900), deux `rect.planche`
> d'overlay mesurables (332×66, 995×746), libellés, zoom planche 0,829 →
> 2,565, PNG 2× de p1 → `vector_9165b7ff4044_p1_2x.png` 200 image/png
> **800×160 = 2× la planche**. Assets : volet → 2 cartes (`offsetHeight` 96),
> clic → image posée (toast). Sauver → relu : grille hex, 2 planches, 38
> tuiles, v2. Négatifs : pinceau sur grille iso → toast « poser d'abord une
> grille hexagonale », 38 tuiles inchangées ; `op_grille({pas:0})` → toast
> « grille: pas > 0 requis », pas gardé à 40. Piège de mesure : un toast
> antérieur a un minuteur de 2,6 s qui réécrit le message — attendre 3 s
> avant de lire un négatif.
>
> **Déployé** : 8 fichiers installés = base lot A (`7c99667`) → sauvegarde
> `_backup_predeploy_2026-09-17b-vectorlab-lotC` → copie depuis `git archive
> f818bf7` → **62 fichiers = cible** ; l'app installée sert déjà
> `mod-grille.js` en 200 (statiques relus du disque). **Aucun fichier
> Python touché : aucune relance nécessaire.**
>
> **Reste** : `motif` de terrain stocké mais non rendu (lot F) ; miroir /
> redimensionnement d'une tuile sans effet (ancrée) ; le générateur garde
> une grille hex existante ; capture d'écran du volet impossible pendant la
> preuve (rendu du volet caché en délai), les mesures DOM font foi.

**Goal :** des grilles de document (carrée subdivisée, isométrique,
triangulaire, hexagonale pointe/plat, taille, origine, échelle) tracées et
aimantantes ; l'aimantation aux objets (bords, centres, écarts) ; un
générateur de quadrillage hexagonal qui pose des objets `tuile` peints par
un pinceau de tuiles selon une fiche de terrains ; des planches multiples
dans un même document, exportables une par une ; un panneau Assets branché
sur la Bibliothèque.

**Architecture :** deux modules purs nouveaux — `mod-grille.js` (géométrie
des quatre grilles, mathématiques hexagonales axiales, tracé des lignes,
aimantation à la grille) et `mod-aimant.js` (aimantation aux objets :
bords, centres, écarts) — sans aucun import, bancables node RED d'abord.
`mod-doc.js` gagne trois champs optionnels rétro-compatibles (`grille`,
`terrains`, `planches`) et l'objet `tuile {q, r, terrain, hauteur_mm?}`
dont la forme hexagonale est DÉRIVÉE de la grille à la compilation (D3) ;
`compilerSVG` gagne `opts.cadre` (viewBox d'une planche). Trois modules UI
(`mod-plateau.js` : panneaux Grille / Terrains / Plateau, outil pinceau de
tuiles ; `mod-planches.js` : panneau Planches, cadres d'overlay, export par
planche ; le panneau Assets dans `mod-image.js`) traduisent les gestes en
UNE commande via `VL.executer`. Aucune route backend nouvelle : le magasin
accepte déjà tout champ optionnel ; miroirs pytest pour l'aller-retour des
champs et la surface.

**Tech Stack :** vanilla ESM, SVG-DOM, node 24 (`qa/run.mjs`), pytest
(`backend/tests/test_vector_docs.py`).

---

## Contrats du modèle (D2, tout optionnel — un doc v1 s'ouvre inchangé)

```json
"grille": { "type": "hex", "pas": 32, "sous": 1, "orientation": "pointe",
            "origine": [0, 0], "echelle": [1, 1] }
```
- `type` : `carree | iso | tri | hex` ; `pas` > 0 en px document : côté de
  la maille (carrée, iso, tri) ou **rayon circonscrit** de l'hexagone ;
  `sous` ≥ 1 : subdivisions (carrée seulement) ; `orientation` : `pointe`
  (sommet en haut) ou `plat` (côté en haut), hex seulement ; `origine` :
  décalage du réseau ; `echelle` : facteur par axe (x, y).
- Sans `doc.grille`, l'ancienne grille carrée d'affichage (`etat.grille.pas`,
  localStorage) reste la référence : rien ne change pour un vieux document.

```json
"terrains": { "plaine": { "nom": "Plaine", "couleur": "#7FB069", "hauteur_mm": 2, "motif": "" } }
```
- clé = identifiant `[a-z0-9_-]+` ; fiche fusionnée avec `TERRAINS_DEFAUT`
  (mer 0 mm, plaine 2, foret 3, colline 5, montagne 8) ; `hauteur_mm` ≥ 0.

```json
{ "id": "o7", "type": "tuile", "q": 2, "r": -1, "terrain": "foret", "hauteur_mm": 4 }
```
- coordonnées axiales ; `terrain` = clé de la fiche (inconnue → gris et
  dit) ; `hauteur_mm` surcharge celle du terrain (lot D l'extrude) ; la
  forme = hexagone de la grille (`hex` du document, sinon hex 32 pointe).
  Compilé : `<path data-objet data-q data-r data-terrain d="…" fill=…/>`.

```json
"planches": [ { "id": "p1", "nom": "Plateau", "x": 0, "y": 0, "w": 2000, "h": 1400 } ]
```
- des cadres nommés dans la page ; tracés à l'overlay (jamais compilés) ;
  aimantants ; exportables : `compilerSVG(doc, { cadre })` rend le SVG dont
  le viewBox EST la planche.

Hexagones (mathématiques axiales, `s` = pas) :
- pointe : centre `x = s·√3·(q + r/2)`, `y = s·1,5·r` ; sommets aux angles
  30° + 60°·k ;
- plat : centre `x = s·1,5·q`, `y = s·√3·(r + q/2)` ; sommets aux angles 60°·k ;
- point → axial : inverse puis arrondi cubique (`x+y+z=0`, on corrige la
  coordonnée dont l'erreur d'arrondi est la plus grande) ; l'origine et
  l'échelle s'appliquent avant.

---

## Cartographie des fichiers

| Fichier | Rôle |
|---|---|
| `frontend/vectorlab/js/mod-grille.js` (créer) | pur : normalisation, lignes des 4 grilles, hex axial, aimantation grille |
| `frontend/vectorlab/js/mod-aimant.js` (créer) | pur : aimantation aux objets (bords, centres, écarts) |
| `frontend/vectorlab/js/mod-doc.js` (modifier) | `grille/terrains/planches`, objet `tuile`, ops, `opts.cadre` |
| `frontend/vectorlab/js/mod-plateau.js` (créer) | UI : panneaux Grille / Terrains / Plateau, outil `tuiles` |
| `frontend/vectorlab/js/mod-planches.js` (créer) | UI : panneau Planches, cadres d'overlay, export par planche |
| `frontend/vectorlab/js/mod-image.js` (modifier) | panneau Assets (Bibliothèque) |
| `frontend/vectorlab/js/core.js` (modifier) | grille tracée depuis `doc.grille`, aimantation (grille + objets + planches), `bboxDocDe`, outil `tuiles`, inits |
| `frontend/vectorlab/js/mod-tools.js` (modifier) | aimantation aux objets pendant le déplacement + lignes d'aide ; geste du pinceau de tuiles |
| `frontend/vectorlab/js/mod-export.js` (modifier) | `exporterPNG(k, {cadre, suffixe})`, `rasteriser` avec cadre |
| `frontend/vectorlab/index.html`, `vectorlab.css` (modifier) | bouton outil `tuiles`, panneaux, details Assets |
| `frontend/vectorlab/qa/grille.test.mjs`, `aimant.test.mjs` (existe → `aimant_objets.test.mjs`), `tuiles.test.mjs`, `planches.test.mjs`, `plateau_ui.test.mjs` (créer) | bancs node |
| `backend/tests/test_vector_docs.py` (modifier) | aller-retour des champs + miroir de surface |

---

## Task 1 : `mod-grille.js` — géométrie pure des grilles et des hexagones

**Files :** Create `frontend/vectorlab/js/mod-grille.js` ; Test `frontend/vectorlab/qa/grille.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// grille.test.mjs — mod-grille (lot C) : normalisation, hex axial (centre,
// sommets, point→axial), lignes des quatre grilles bornées à la page,
// aimantation à la grille, garde de densité. Aucun DOM, aucun import de
// mod-doc (le module est feuille).
import { GRILLE_TYPES, grille_normaliser, hex_centre, hex_sommets, hex_d,
         hex_depuis_point, grille_d, grille_aimanter, grille_cellules }
  from "../js/mod-grille.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (a, b, e = 1e-6) => Math.abs(a - b) <= e;
const S3 = Math.sqrt(3);

/* ── normalisation ── */
{
  ok("types", JSON.stringify(GRILLE_TYPES) === JSON.stringify(["carree", "iso", "tri", "hex"]));
  const g = grille_normaliser({ type: "hex", pas: 32 });
  ok("défauts : sous 1, pointe, origine 0, échelle 1", g.sous === 1 && g.orientation === "pointe"
     && g.origine[0] === 0 && g.echelle[1] === 1, JSON.stringify(g));
  let refus = 0;
  for (const m of [null, { type: "octo", pas: 8 }, { type: "hex", pas: 0 }, { type: "carree", pas: 8, sous: 0 },
                   { type: "hex", pas: 8, orientation: "biais" }, { type: "hex", pas: 8, origine: [1] },
                   { type: "hex", pas: 8, echelle: [0, 1] }]) {
    try { grille_normaliser(m); } catch { refus++; }
  }
  ok("7 grilles malformées refusées", refus === 7, String(refus));
}
/* ── hexagones pointe ── */
{
  const g = grille_normaliser({ type: "hex", pas: 10 });
  const c00 = hex_centre(0, 0, g), c10 = hex_centre(1, 0, g), c01 = hex_centre(0, 1, g);
  ok("pointe : centre (0,0) à l'origine", pres(c00[0], 0) && pres(c00[1], 0));
  ok("pointe : (1,0) à √3·s en x", pres(c10[0], 10 * S3) && pres(c10[1], 0), c10.join(","));
  ok("pointe : (0,1) à (√3/2·s, 1,5·s)", pres(c01[0], 5 * S3) && pres(c01[1], 15), c01.join(","));
  const s = hex_sommets(0, 0, 10, "pointe");
  ok("6 sommets, le premier en haut (angle -90°)", s.length === 6 && pres(s[0][0], 0) && pres(s[0][1], -10), JSON.stringify(s[0]));
  ok("hex_d fermé, canonique 2 déc.", /^M -?\d/.test(hex_d(0, 0, 10, "pointe")) && hex_d(0, 0, 10, "pointe").endsWith("Z")
     && hex_d(0, 0, 10, "pointe").split(" L ").length === 6, hex_d(0, 0, 10, "pointe"));
  // point → axial : le centre de chaque cellule revient sur elle-même
  for (const [q, r] of [[0, 0], [3, -2], [-4, 5], [7, 7]]) {
    const [x, y] = hex_centre(q, r, g);
    const a = hex_depuis_point(x + 2, y - 3, g);           // près du centre
    ok(`point→axial (${q},${r})`, a.q === q && a.r === r, JSON.stringify(a));
  }
  // origine et échelle s'appliquent
  const g2 = grille_normaliser({ type: "hex", pas: 10, origine: [100, 50], echelle: [2, 1] });
  const c = hex_centre(1, 0, g2);
  ok("origine + échelle : (1,0) → (100 + 2·√3·10, 50)", pres(c[0], 100 + 20 * S3) && pres(c[1], 50), c.join(","));
  ok("inverse avec origine/échelle", (() => { const a = hex_depuis_point(c[0], c[1], g2); return a.q === 1 && a.r === 0; })());
}
/* ── hexagones plat ── */
{
  const g = grille_normaliser({ type: "hex", pas: 10, orientation: "plat" });
  const c10 = hex_centre(1, 0, g), c01 = hex_centre(0, 1, g);
  ok("plat : (1,0) à (1,5·s, √3/2·s)", pres(c10[0], 15) && pres(c10[1], 5 * S3), c10.join(","));
  ok("plat : (0,1) à (0, √3·s)", pres(c01[0], 0) && pres(c01[1], 10 * S3));
  const s = hex_sommets(0, 0, 10, "plat");
  ok("plat : premier sommet à droite (angle 0°)", pres(s[0][0], 10) && pres(s[0][1], 0));
  ok("plat : inverse", (() => { const a = hex_depuis_point(c10[0] + 1, c10[1] + 1, g); return a.q === 1 && a.r === 0; })());
}
/* ── cellules d'un plateau ── */
{
  ok("rayon 0 → 1 cellule ; rayon 1 → 7 ; rayon 2 → 19",
     grille_cellules({ mode: "rayon", rayon: 0 }).length === 1
     && grille_cellules({ mode: "rayon", rayon: 1 }).length === 7
     && grille_cellules({ mode: "rayon", rayon: 2 }).length === 19);
  const rect = grille_cellules({ mode: "rect", colonnes: 4, lignes: 3 });
  ok("rect 4×3 → 12 cellules, coordonnées entières distinctes", rect.length === 12
     && new Set(rect.map((c) => c.q + "," + c.r)).size === 12);
  let refus = 0;
  for (const m of [{ mode: "rayon", rayon: -1 }, { mode: "rect", colonnes: 0, lignes: 2 }, { mode: "x" }, { mode: "rayon", rayon: 80 }]) {
    try { grille_cellules(m); } catch { refus++; }
  }
  ok("4 spécifications refusées (dont rayon > 60)", refus === 4, String(refus));
}
/* ── lignes bornées à la page ── */
{
  const T = { w: 100, h: 50 };
  const dC = grille_d(grille_normaliser({ type: "carree", pas: 25 }), T);
  ok("carrée 25 : 3 verticales + 1 horizontale intérieures", (dC.match(/M/g) || []).length === 4, dC);
  const dS = grille_d(grille_normaliser({ type: "carree", pas: 25, sous: 5 }), T);
  ok("subdivisions ÷5 : 19 verticales + 9 horizontales", (dS.match(/M/g) || []).length === 28, (dS.match(/M/g) || []).length);
  const dI = grille_d(grille_normaliser({ type: "iso", pas: 20 }), T);
  ok("iso : des lignes, toutes dans la page", (dI.match(/M/g) || []).length > 6
     && dI.split(/[ML]/).filter(Boolean).every((p) => { const [x, y] = p.trim().split(/\s+/).map(Number); return x >= -1e-6 && x <= 100 + 1e-6 && y >= -1e-6 && y <= 50 + 1e-6; }), dI.slice(0, 120));
  const dT = grille_d(grille_normaliser({ type: "tri", pas: 20 }), T);
  ok("tri : trois directions (des horizontales + des obliques)", /M 0 \d+(\.\d+)? L 100 \d+(\.\d+)?/.test(dT) && (dT.match(/M/g) || []).length > 6, dT.slice(0, 120));
  const dH = grille_d(grille_normaliser({ type: "hex", pas: 10 }), T);
  ok("hex : des hexagones fermés couvrant la page", (dH.match(/Z/g) || []).length >= 30 && (dH.match(/Z/g) || []).length <= 80, (dH.match(/Z/g) || []).length);
  ok("trop dense → chaîne vide (garde de densité)", grille_d(grille_normaliser({ type: "hex", pas: 1 }), { w: 3000, h: 3000 }) === "");
}
/* ── aimantation à la grille ── */
{
  const c = grille_normaliser({ type: "carree", pas: 20, sous: 2 });
  ok("carrée ÷2 : 27,4 → 30 ; 12 → 10", grille_aimanter(c, 27.4, 12).join(",") === "30,10");
  const o = grille_normaliser({ type: "carree", pas: 20, origine: [5, 5] });
  ok("origine décalée : 27 → 25", grille_aimanter(o, 27, 27).join(",") === "25,25");
  const h = grille_normaliser({ type: "hex", pas: 10 });
  const [cx, cy] = hex_centre(2, 1, h);
  const a = grille_aimanter(h, cx + 1, cy + 1);
  ok("hex : près d'un centre → le centre", pres(a[0], cx, 1e-6) && pres(a[1], cy, 1e-6), a.join(","));
  const som = hex_sommets(cx, cy, 10, "pointe")[0];
  const b = grille_aimanter(h, som[0] + 0.5, som[1] - 0.5);
  ok("hex : près d'un sommet → le sommet", pres(b[0], som[0]) && pres(b[1], som[1]), b.join(","));
  const t = grille_normaliser({ type: "tri", pas: 20 });
  const p = grille_aimanter(t, 10.3, 17.1);
  ok("tri : sommet du réseau (10, 10√3)", pres(p[0], 10) && pres(p[1], 10 * S3), p.join(","));
  const i = grille_normaliser({ type: "iso", pas: 20 });
  const pi = grille_aimanter(i, 17.5, 9.8);
  ok("iso : sommet du réseau (√3·10, 10)", pres(pi[0], 10 * S3) && pres(pi[1], 10), pi.join(","));
}

if (echecs.length) {
  console.error("ECHECS grille :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA grille : PASS (33 controles)");
```

- [ ] **Step 2 : RED** — `cd frontend/vectorlab && node qa/grille.test.mjs` → `Cannot find module '.../js/mod-grille.js'`.

- [ ] **Step 3 : écrire `mod-grille.js`**

```js
// mod-grille.js — la GÉOMÉTRIE des grilles du Vectorlab (lot C) : quatre
// réseaux (carrée subdivisée, isométrique, triangulaire, hexagonale pointe
// ou plat), origine et échelle par axe, tracé borné à la page, aimantation
// au réseau, mathématiques hexagonales axiales (D3). Module FEUILLE : aucun
// import, aucun DOM — le banc node l'exerce tel quel.
export const GRILLE_TYPES = ["carree", "iso", "tri", "hex"];
const S3 = Math.sqrt(3);
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);
const GRILLE_MAX_CELLULES = 20000;

export function grille_normaliser(g) {
  if (!g || typeof g !== "object") throw new Error("grille: objet requis");
  if (!GRILLE_TYPES.includes(g.type)) throw new Error(`grille: type ${g.type} inconnu (${GRILLE_TYPES.join("|")})`);
  if (!(+g.pas > 0)) throw new Error("grille: pas > 0 requis");
  const sous = g.sous === undefined ? 1 : +g.sous;
  if (!(Number.isInteger(sous) && sous >= 1)) throw new Error("grille: sous = entier ≥ 1");
  const orientation = g.orientation === undefined ? "pointe" : g.orientation;
  if (!["pointe", "plat"].includes(orientation)) throw new Error("grille: orientation pointe|plat");
  const origine = g.origine === undefined ? [0, 0] : g.origine;
  if (!Array.isArray(origine) || origine.length !== 2 || !origine.every(Number.isFinite)) {
    throw new Error("grille: origine [x, y]");
  }
  const echelle = g.echelle === undefined ? [1, 1] : g.echelle;
  if (!Array.isArray(echelle) || echelle.length !== 2 || !echelle.every((v) => v > 0)) {
    throw new Error("grille: echelle [sx > 0, sy > 0]");
  }
  return { type: g.type, pas: +g.pas, sous, orientation, origine: [+origine[0], +origine[1]],
           echelle: [+echelle[0], +echelle[1]] };
}

/* ── hexagones (axial q, r) ── */
export function hex_centre(q, r, g) {
  const s = g.pas;
  const [x, y] = g.orientation === "plat"
    ? [s * 1.5 * q, s * S3 * (r + q / 2)]
    : [s * S3 * (q + r / 2), s * 1.5 * r];
  return [g.origine[0] + x * g.echelle[0], g.origine[1] + y * g.echelle[1]];
}
export function hex_sommets(cx, cy, s, orientation, echelle = [1, 1]) {
  const dep = orientation === "plat" ? 0 : -90;
  const out = [];
  for (let k = 0; k < 6; k++) {
    const a = (dep + 60 * k) * Math.PI / 180;
    out.push([cx + s * Math.cos(a) * echelle[0], cy + s * Math.sin(a) * echelle[1]]);
  }
  return out;
}
export function hex_d(cx, cy, s, orientation, echelle = [1, 1]) {
  const p = hex_sommets(cx, cy, s, orientation, echelle);
  return "M " + p.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L ") + " Z";
}
function _arrondiCube(qf, rf) {
  const sf = -qf - rf;
  let q = Math.round(qf), r = Math.round(rf), s = Math.round(sf);
  const dq = Math.abs(q - qf), dr = Math.abs(r - rf), ds = Math.abs(s - sf);
  if (dq > dr && dq > ds) q = -r - s; else if (dr > ds) r = -q - s;
  return { q, r };
}
export function hex_depuis_point(x, y, g) {
  const s = g.pas;
  const lx = (x - g.origine[0]) / g.echelle[0], ly = (y - g.origine[1]) / g.echelle[1];
  const [qf, rf] = g.orientation === "plat"
    ? [lx * 2 / 3 / s, (-lx / 3 + S3 / 3 * ly) / s]
    : [(S3 / 3 * lx - ly / 3) / s, ly * 2 / 3 / s];
  return _arrondiCube(qf, rf);
}

/* ── les cellules d'un plateau : disque de rayon n ou rectangle ── */
export function grille_cellules(spec) {
  if (!spec || typeof spec !== "object") throw new Error("plateau: spécification requise");
  const out = [];
  if (spec.mode === "rayon") {
    const n = +spec.rayon;
    if (!(Number.isInteger(n) && n >= 0 && n <= 60)) throw new Error("plateau: rayon entier 0..60");
    for (let q = -n; q <= n; q++) {
      for (let r = Math.max(-n, -q - n); r <= Math.min(n, -q + n); r++) out.push({ q, r });
    }
    return out;
  }
  if (spec.mode === "rect") {
    const c = +spec.colonnes, l = +spec.lignes;
    if (!(Number.isInteger(c) && c >= 1 && c <= 120 && Number.isInteger(l) && l >= 1 && l <= 120)) {
      throw new Error("plateau: colonnes et lignes entières 1..120");
    }
    // décalage « odd-r » → axial : q = col − floor(row / 2)
    for (let row = 0; row < l; row++) for (let col = 0; col < c; col++) out.push({ q: col - Math.floor(row / 2), r: row });
    return out;
  }
  throw new Error(`plateau: mode ${spec.mode} inconnu (rayon|rect)`);
}

/* ── lignes bornées à la page ── */
function _clip(x0, y0, dx, dy, W, H) {
  // segment de la droite (x0,y0)+t·(dx,dy) dans [0,W]×[0,H] (Liang–Barsky)
  let t0 = -Infinity, t1 = Infinity;
  for (const [p, q] of [[-dx, x0], [dx, W - x0], [-dy, y0], [dy, H - y0]]) {
    if (p === 0) { if (q < 0) return null; continue; }
    const t = q / p;
    if (p < 0) t0 = Math.max(t0, t); else t1 = Math.min(t1, t);
  }
  if (t0 >= t1) return null;
  return [x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy];
}
function _famille(angleDeg, espacement, origine, W, H) {
  // toutes les droites de direction `angle`, espacées de `espacement`
  // perpendiculairement, passant par le réseau d'origine `origine`
  const a = angleDeg * Math.PI / 180;
  const dx = Math.cos(a), dy = Math.sin(a);
  const nx = -dy, ny = dx;                       // normale unitaire
  const d0 = origine[0] * nx + origine[1] * ny;  // offset de la droite d'origine
  const coins = [[0, 0], [W, 0], [0, H], [W, H]].map(([x, y]) => x * nx + y * ny);
  const kMin = Math.ceil((Math.min(...coins) - d0) / espacement);
  const kMax = Math.floor((Math.max(...coins) - d0) / espacement);
  let d = "";
  for (let k = kMin; k <= kMax; k++) {
    const off = d0 + k * espacement;
    const seg = _clip(off * nx, off * ny, dx, dy, W, H);
    if (seg) d += `M ${nbc(seg[0])} ${nbc(seg[1])} L ${nbc(seg[2])} ${nbc(seg[3])} `;
  }
  return d;
}
export function grille_d(g, taille) {
  const W = +taille.w, H = +taille.h;
  const [sx, sy] = g.echelle;
  if (g.type === "carree") {
    const px = g.pas * sx / g.sous, py = g.pas * sy / g.sous;
    if ((W / px) * (H / py) > GRILLE_MAX_CELLULES) return "";
    let d = "";
    const x0 = ((g.origine[0] % px) + px) % px, y0 = ((g.origine[1] % py) + py) % py;
    for (let x = x0; x < W; x += px) if (x > 0) d += `M ${nbc(x)} 0 L ${nbc(x)} ${nbc(H)} `;
    for (let y = y0; y < H; y += py) if (y > 0) d += `M 0 ${nbc(y)} L ${nbc(W)} ${nbc(y)} `;
    return d.trim();
  }
  if (g.type === "iso") {
    // réseau losange : droites à ±30°, espacement perpendiculaire = pas/2·√3… 
    // le réseau a pour base a=(√3/2·s, s/2), b=(√3/2·s, −s/2) → hauteur s
    const s = g.pas * sy, e = s * Math.cos(30 * Math.PI / 180);
    if ((W / (g.pas * sx)) * (H / s) * 2 > GRILLE_MAX_CELLULES) return "";
    return (_famille(30, e, g.origine, W, H) + _famille(-30, e, g.origine, W, H)).trim();
  }
  if (g.type === "tri") {
    const s = g.pas * sx, e = s * S3 / 2;         // hauteur du triangle équilatéral
    if ((W / s) * (H / e) * 2 > GRILLE_MAX_CELLULES) return "";
    return (_famille(0, e, g.origine, W, H) + _famille(60, e, g.origine, W, H)
            + _famille(120, e, g.origine, W, H)).trim();
  }
  // hex : un hexagone fermé par cellule visible
  const s = g.pas;
  const a0 = hex_depuis_point(0, 0, g), a1 = hex_depuis_point(W, 0, g),
        a2 = hex_depuis_point(0, H, g), a3 = hex_depuis_point(W, H, g);
  const qs = [a0.q, a1.q, a2.q, a3.q], rs = [a0.r, a1.r, a2.r, a3.r];
  const qMin = Math.min(...qs) - 2, qMax = Math.max(...qs) + 2;
  const rMin = Math.min(...rs) - 2, rMax = Math.max(...rs) + 2;
  if ((qMax - qMin + 1) * (rMax - rMin + 1) > GRILLE_MAX_CELLULES) return "";
  let d = "";
  for (let q = qMin; q <= qMax; q++) {
    for (let r = rMin; r <= rMax; r++) {
      const [cx, cy] = hex_centre(q, r, g);
      if (cx < -s * sx || cx > W + s * sx || cy < -s * sy || cy > H + s * sy) continue;
      d += hex_d(cx, cy, s, g.orientation, g.echelle) + " ";
    }
  }
  return d.trim();
}

/* ── aimantation au réseau : le sommet le plus proche ── */
function _reseau(x, y, a, b, origine) {
  // coordonnées fractionnaires dans la base (a, b), arrondies
  const det = a[0] * b[1] - a[1] * b[0];
  const lx = x - origine[0], ly = y - origine[1];
  const u = Math.round((lx * b[1] - ly * b[0]) / det), v = Math.round((a[0] * ly - a[1] * lx) / det);
  return [origine[0] + u * a[0] + v * b[0], origine[1] + u * a[1] + v * b[1]];
}
export function grille_aimanter(g, x, y) {
  const [sx, sy] = g.echelle;
  if (g.type === "carree") {
    const p = g.pas / g.sous;
    return _reseau(x, y, [p * sx, 0], [0, p * sy], g.origine);
  }
  if (g.type === "iso") {
    const s = g.pas;
    return _reseau(x, y, [S3 / 2 * s * sx, s / 2 * sy], [S3 / 2 * s * sx, -s / 2 * sy], g.origine);
  }
  if (g.type === "tri") {
    const s = g.pas;
    return _reseau(x, y, [s * sx, 0], [s / 2 * sx, S3 / 2 * s * sy], g.origine);
  }
  const { q, r } = hex_depuis_point(x, y, g);
  const [cx, cy] = hex_centre(q, r, g);
  let meilleur = [cx, cy], dist = Math.hypot(x - cx, y - cy);
  for (const [px, py] of hex_sommets(cx, cy, g.pas, g.orientation, g.echelle)) {
    const dd = Math.hypot(x - px, y - py);
    if (dd < dist) { dist = dd; meilleur = [px, py]; }
  }
  return meilleur;
}
```

- [ ] **Step 4 : GREEN** — `node qa/grille.test.mjs` → `PASS (33 controles)`. Si un
  compte de lignes iso/tri diffère d'une unité (bords exclus/inclus), ajuster
  le BANC après avoir vérifié à la main que toutes les extrémités sont sur les
  bords de la page — la règle (« aucune ligne hors page ») prime sur le compte.

- [ ] **Step 5 : commit**

```bash
git add frontend/vectorlab/js/mod-grille.js frontend/vectorlab/qa/grille.test.mjs
git commit --only frontend/vectorlab/js/mod-grille.js frontend/vectorlab/qa/grille.test.mjs -m "vectorlab : mod-grille — quatre reseaux (carree subdivisee, iso, tri, hex pointe/plat), origine, echelle, trace borne, aimantation, hex axial (lot C, T1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 2 : `mod-aimant.js` — aimantation aux objets (bords, centres, écarts)

**Files :** Create `frontend/vectorlab/js/mod-aimant.js` ; Test `frontend/vectorlab/qa/aimant_objets.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// aimant_objets.test.mjs — l'aimantation aux OBJETS (lot C) : une boîte en
// mouvement s'aligne sur les bords et les centres des voisins, et sur les
// écarts réguliers ; l'état vide (aucun voisin) ne bouge rien.
import { aimant_objets, aimant_ecarts, aimant_fusion } from "../js/mod-aimant.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const B = (x, y, w, h) => ({ x, y, w, h });

{
  const r = aimant_objets(B(10.4, 20, 30, 30), [], 5);
  ok("état vide : dx=dy=0, aucune ligne", r.dx === 0 && r.dy === 0 && r.lignes.length === 0);
}
{
  const cands = [B(100, 100, 50, 50)];
  // bord gauche sur bord gauche
  let r = aimant_objets(B(103, 300, 20, 20), cands, 5);
  ok("gauche→gauche : dx=-3, ligne v à 100", r.dx === -3 && r.lignes.some((l) => l.axe === "v" && l.pos === 100), JSON.stringify(r));
  // bord droit sur bord droit (150)
  r = aimant_objets(B(126, 300, 20, 20), cands, 5);
  ok("droite→droite : 146→150, dx=4", r.dx === 4, JSON.stringify(r));
  // centre sur centre (125)
  r = aimant_objets(B(113, 300, 20, 20), cands, 5);
  ok("centre→centre : 123→125, dx=2", r.dx === 2, JSON.stringify(r));
  // gauche sur droite du voisin (accolement)
  r = aimant_objets(B(152, 300, 20, 20), cands, 5);
  ok("gauche→droite du voisin : dx=-2", r.dx === -2, JSON.stringify(r));
  // vertical : haut sur haut
  r = aimant_objets(B(300, 97, 20, 20), cands, 5);
  ok("haut→haut : dy=3, ligne h à 100", r.dy === 3 && r.lignes.some((l) => l.axe === "h" && l.pos === 100), JSON.stringify(r));
  // hors tolérance : rien
  r = aimant_objets(B(300, 300, 20, 20), cands, 5);
  ok("hors tolérance : rien", r.dx === 0 && r.dy === 0 && r.lignes.length === 0);
  // le plus proche gagne
  r = aimant_objets(B(104, 300, 20, 20), [B(100, 0, 10, 10), B(106, 0, 10, 10)], 5);
  ok("le candidat le plus proche gagne (106)", r.dx === 2, JSON.stringify(r));
}
/* ── écarts : A[0..50] gap 20 B[70..120] → C se pose à 140 ── */
{
  const cands = [B(0, 0, 50, 50), B(70, 0, 50, 50)];
  let r = aimant_ecarts(B(137, 0, 30, 30), cands, 5);
  ok("écart régulier après B : x→140, dx=3, ligne écart", r.dx === 3 && r.lignes.some((l) => l.type === "ecart"), JSON.stringify(r));
  r = aimant_ecarts(B(-52, 0, 30, 30), cands, 5);
  ok("écart régulier avant A : droite à -20 → x=-50, dx=2", r.dx === 2, JSON.stringify(r));
  r = aimant_ecarts(B(400, 0, 30, 30), cands, 5);
  ok("écart : hors tolérance → rien", r.dx === 0 && r.lignes.length === 0);
  ok("écart : moins de deux voisins → rien", aimant_ecarts(B(137, 0, 30, 30), [cands[0]], 5).dx === 0);
}
{
  const f = aimant_fusion([{ dx: 0, dy: 3, lignes: [{ axe: "h", pos: 1 }] }, { dx: 2, dy: 0, lignes: [{ axe: "v", pos: 2 }] }]);
  ok("fusion : le premier résultat non nul par axe, lignes concaténées", f.dx === 2 && f.dy === 3 && f.lignes.length === 2, JSON.stringify(f));
}

if (echecs.length) {
  console.error("ECHECS aimant_objets :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA aimant_objets : PASS (13 controles)");
```

- [ ] **Step 2 : RED** — module introuvable.

- [ ] **Step 3 : `mod-aimant.js`**

```js
// mod-aimant.js — l'aimantation aux OBJETS (lot C, § 2.5 d'Affinity) : une
// boîte en mouvement s'aligne sur les bords et les centres de ses voisins
// (bords contre bords, centre sur centre, bord contre bord opposé =
// accolement) et sur les écarts réguliers entre voisins. Module FEUILLE,
// pur : les boîtes sont FOURNIES par l'appelant (l'écran mesure).
function _axe(vals, cibles, tol) {
  let meilleur = null, ecart = tol + 1e-9;
  for (const v of vals) for (const c of cibles) {
    const e = Math.abs(c - v);
    if (e < ecart) { ecart = e; meilleur = { d: c - v, pos: c }; }
  }
  return meilleur;
}
export function aimant_objets(b, candidats, tol) {
  const out = { dx: 0, dy: 0, lignes: [] };
  if (!candidats || !candidats.length) return out;
  const cx = [], cy = [];
  for (const c of candidats) { cx.push(c.x, c.x + c.w / 2, c.x + c.w); cy.push(c.y, c.y + c.h / 2, c.y + c.h); }
  const mx = _axe([b.x, b.x + b.w / 2, b.x + b.w], cx, tol);
  const my = _axe([b.y, b.y + b.h / 2, b.y + b.h], cy, tol);
  if (mx) { out.dx = mx.d; out.lignes.push({ axe: "v", pos: mx.pos, type: "bord" }); }
  if (my) { out.dy = my.d; out.lignes.push({ axe: "h", pos: my.pos, type: "bord" }); }
  return out;
}
function _ecartsAxe(b0, b1, cands, k0, k1) {
  // positions candidates du bord [k0] de la boîte pour reproduire l'écart
  // entre deux voisins ADJACENTS le long de l'axe (k0 = "x"|"y", k1 = "w"|"h")
  const tri = cands.slice().sort((a, c) => a[k0] - c[k0]);
  const cibles = [];
  for (let i = 0; i + 1 < tri.length; i++) {
    const A = tri[i], Bv = tri[i + 1];
    const g = Bv[k0] - (A[k0] + A[k1]);
    if (g < 0) continue;
    cibles.push({ debut: Bv[k0] + Bv[k1] + g, fin: A[k0] - g });     // après B, avant A
  }
  return cibles;
}
export function aimant_ecarts(b, candidats, tol) {
  const out = { dx: 0, dy: 0, lignes: [] };
  if (!candidats || candidats.length < 2) return out;
  for (const [k0, k1, dk, axe] of [["x", "w", "dx", "v"], ["y", "h", "dy", "h"]]) {
    let meilleur = null, ecart = tol + 1e-9;
    for (const c of _ecartsAxe(b, null, candidats, k0, k1)) {
      for (const [v, cible] of [[b[k0], c.debut], [b[k0] + b[k1], c.fin]]) {
        const e = Math.abs(cible - v);
        if (e < ecart) { ecart = e; meilleur = { d: cible - v, pos: cible }; }
      }
    }
    if (meilleur) { out[dk] = meilleur.d; out.lignes.push({ axe, pos: meilleur.pos, type: "ecart" }); }
  }
  return out;
}
export function aimant_fusion(resultats) {
  const out = { dx: 0, dy: 0, lignes: [] };
  for (const r of resultats) {
    if (!out.dx && r.dx) out.dx = r.dx;
    if (!out.dy && r.dy) out.dy = r.dy;
    out.lignes.push(...(r.lignes || []));
  }
  return out;
}
```

- [ ] **Step 4 : GREEN** puis **commit**

```bash
git add frontend/vectorlab/js/mod-aimant.js frontend/vectorlab/qa/aimant_objets.test.mjs
git commit --only frontend/vectorlab/js/mod-aimant.js frontend/vectorlab/qa/aimant_objets.test.mjs -m "vectorlab : mod-aimant — aimantation aux objets, bords, centres et ecarts reguliers (lot C, T2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 3 : modèle — `grille`, `terrains`, `tuile`, `planches`, `opts.cadre`

**Files :** Modify `frontend/vectorlab/js/mod-doc.js` ; Test `frontend/vectorlab/qa/tuiles.test.mjs`, `frontend/vectorlab/qa/planches.test.mjs`

- [ ] **Step 1 : banc RED tuiles**

```js
// tuiles.test.mjs — lot C : doc.grille (commande op_grille), la fiche de
// terrains (défauts + surcharges), l'objet `tuile` compilé en hexagone de
// la grille, le pinceau (op_tuiles_peindre : peint l'existant, pose le
// manquant) et le générateur de plateau. États vides construits.
import { parserDoc, compilerSVG, op_grille, terrains_de, op_terrain_definir,
         op_terrain_supprimer, op_tuiles_peindre, op_plateau_generer, tuile_a,
         op_deplacer, op_redimensionner, TERRAINS_DEFAUT } from "../js/mod-doc.js";
import { hex_centre } from "../js/mod-grille.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "P", taille: { w: 800, h: 600 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] });

/* ── grille ── */
{
  const d = base();
  op_grille(d, { type: "hex", pas: 24 });
  ok("op_grille pose une grille normalisée", d.grille.type === "hex" && d.grille.sous === 1 && d.grille.orientation === "pointe", JSON.stringify(d.grille));
  op_grille(d, { orientation: "plat", origine: [10, 5] });
  ok("op_grille : patch partiel fusionné", d.grille.type === "hex" && d.grille.orientation === "plat" && d.grille.origine[0] === 10);
  op_grille(d, null);
  ok("op_grille(null) retire la grille", d.grille === undefined);
  let refus = 0;
  for (const p of [{ type: "octo" }, { pas: -1 }, { type: "hex", pas: 8, sous: 0 }]) {
    const e = base(); try { op_grille(e, p); } catch { refus++; }
  }
  ok("op_grille refuse 3 patchs", refus === 3, String(refus));
  const m = base(); m.grille = { type: "hex", pas: 0 };
  let refusDoc = false; try { parserDoc(m); } catch { refusDoc = true; }
  ok("parserDoc refuse une grille malformée", refusDoc);
}
/* ── terrains ── */
{
  const d = base();
  const t = terrains_de(d);
  ok("état vide : les défauts (mer, plaine, foret, colline, montagne)", Object.keys(t).length === 5 && t.mer.hauteur_mm === 0 && t.montagne.hauteur_mm === 8, JSON.stringify(Object.keys(t)));
  ok("TERRAINS_DEFAUT n'est pas muté par terrains_de", terrains_de(d) !== TERRAINS_DEFAUT);
  op_terrain_definir(d, "lave", { nom: "Lave", couleur: "#D33", hauteur_mm: 1 });
  ok("définir ajoute au document, fusionné", terrains_de(d).lave.couleur === "#D33" && d.terrains.lave && Object.keys(terrains_de(d)).length === 6);
  op_terrain_definir(d, "mer", { couleur: "#123456" });
  ok("surcharger un défaut garde son nom et sa hauteur", terrains_de(d).mer.couleur === "#123456" && terrains_de(d).mer.hauteur_mm === 0 && terrains_de(d).mer.nom === "Mer");
  op_terrain_supprimer(d, "lave");
  ok("supprimer retire la surcharge", terrains_de(d).lave === undefined);
  let refus = 0;
  for (const [k, f] of [["Lave!", {}], ["x", { hauteur_mm: -1 }], ["x", { couleur: "rouge" }], ["x", null]]) {
    try { op_terrain_definir(base(), k, f); } catch { refus++; }
  }
  ok("définir refuse clé/hauteur/couleur/fiche invalides", refus === 4, String(refus));
}
/* ── tuile : compilation ── */
{
  const d = base();
  op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 1, r: 1, terrain: "foret" });
  const svg = compilerSVG(d);
  const [cx, cy] = hex_centre(1, 1, d.grille);
  ok("tuile : path data-q/data-r/data-terrain", svg.includes('data-objet="t1"') && svg.includes('data-q="1" data-r="1" data-terrain="foret"'), svg);
  ok("tuile : fond = couleur du terrain, contour fin", svg.includes(`fill="${TERRAINS_DEFAUT.foret.couleur}"`) && svg.includes('stroke-width="1"'));
  ok("tuile : d = hexagone centré sur la cellule", svg.includes(`M ${Math.round(cx * 100) / 100} ${Math.round((cy - 20) * 100) / 100}`), svg);
  d.calques[0].objets[0].terrain = "inconnu";
  ok("terrain inconnu : gris et dit", compilerSVG(d).includes('fill="#888888"') && compilerSVG(d).includes('data-terrain-inconnu="1"'));
  const sans = base(); sans.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  ok("sans grille hex : hexagone par défaut (32, pointe) — le doc ne casse pas", compilerSVG(sans).includes('data-objet="t1"'));
  let refus = 0;
  for (const o of [{ id: "t", type: "tuile", q: 0.5, r: 0, terrain: "mer" }, { id: "t", type: "tuile", q: 0, r: 0 }, { id: "t", type: "tuile", q: 0, r: 0, terrain: "mer", hauteur_mm: -2 }]) {
    const e = base(); e.calques[0].objets.push(o); try { parserDoc(e); } catch { refus++; }
  }
  ok("parserDoc refuse 3 tuiles malformées", refus === 3, String(refus));
}
/* ── tuile_a, déplacer (aimanté à la cellule), redimensionner (no-op) ── */
{
  const d = base(); op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  ok("tuile_a trouve (0,0), pas (1,0)", tuile_a(d, 0, 0) && tuile_a(d, 0, 0).id === "t1" && tuile_a(d, 1, 0) === null);
  const [cx1] = hex_centre(1, 0, d.grille), [cx0] = hex_centre(0, 0, d.grille);
  op_deplacer(d, ["t1"], cx1 - cx0 + 1, 0);
  ok("déplacer une tuile la ré-ancre à la cellule voisine", d.calques[0].objets[0].q === 1 && d.calques[0].objets[0].r === 0, JSON.stringify(d.calques[0].objets[0]));
  op_redimensionner(d, ["t1"], { x: 0, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 100, h: 100 });
  ok("redimensionner une tuile est sans effet (ancrée)", d.calques[0].objets[0].q === 1);
}
/* ── pinceau ── */
{
  const d = base(); op_grille(d, { type: "hex", pas: 20 });
  d.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  const r = op_tuiles_peindre(d, "c1", [{ q: 0, r: 0 }, { q: 1, r: 0 }, { q: 1, r: 0 }], "foret");
  ok("peindre : 1 repeinte, 1 posée (doublon ignoré)", r.peintes.length === 1 && r.posees.length === 1 && d.calques[0].objets.length === 2, JSON.stringify(r));
  ok("la posée porte le terrain et la cellule", tuile_a(d, 1, 0).terrain === "foret" && tuile_a(d, 0, 0).terrain === "foret");
  let refus = 0;
  try { op_tuiles_peindre(d, "c1", [], "foret"); } catch { refus++; }
  try { op_tuiles_peindre(d, "c1", [{ q: 0, r: 0 }], "inconnu"); } catch { refus++; }
  ok("peindre refuse : aucune cellule ; terrain inconnu", refus === 2, String(refus));
  const v = base(); op_grille(v, { type: "hex", pas: 20 }); v.calques[0].verrou = true;
  v.calques[0].objets.push({ id: "t1", type: "tuile", q: 0, r: 0, terrain: "mer" });
  op_calque_ajouterPour(v);
  function op_calque_ajouterPour(doc) { doc.calques.push({ id: "c2", nom: "libre", visible: true, verrou: false, objets: [] }); }
  const rv = op_tuiles_peindre(v, "c2", [{ q: 0, r: 0 }], "foret");
  ok("une tuile d'un calque verrouillé n'est ni peinte ni doublée", rv.peintes.length === 0 && rv.posees.length === 0 && v.calques[0].objets[0].terrain === "mer");
}
/* ── générateur ── */
{
  const d = base();
  const r = op_plateau_generer(d, { mode: "rayon", rayon: 2, pas: 30, orientation: "plat", terrain: "plaine", numeroter: true });
  ok("générer pose la grille hex du document", d.grille && d.grille.type === "hex" && d.grille.pas === 30 && d.grille.orientation === "plat");
  ok("un calque « plateau » de 19 tuiles + un calque « numéros » de 19 textes", r.tuiles.length === 19
     && d.calques.find((c) => c.id === r.calqueId).objets.length === 19
     && d.calques.find((c) => c.id === r.calqueNumeros).objets.filter((o) => o.type === "texte").length === 19, JSON.stringify(r));
  ok("les numéros lisent « q,r »", d.calques.find((c) => c.id === r.calqueNumeros).objets.some((o) => o.contenu === "0,0"));
  ok("le plateau est centré : l'origine de la grille est au centre de la page", d.grille.origine[0] === 400 && d.grille.origine[1] === 300, JSON.stringify(d.grille.origine));
  const r2 = op_plateau_generer(d, { mode: "rect", colonnes: 3, lignes: 2, terrain: "mer" });
  ok("un second plateau : la grille existante est GARDÉE, calque neuf", d.grille.pas === 30 && r2.tuiles.length === 6 && !r2.calqueNumeros);
  ok("le document compilé passe parserDoc", (() => { try { compilerSVG(parserDoc(d)); return true; } catch { return false; } })());
  let refus = 0;
  try { op_plateau_generer(base(), { mode: "rayon", rayon: 2, terrain: "inconnu" }); } catch { refus++; }
  try { op_plateau_generer(base(), { mode: "rect", colonnes: 0, lignes: 1 }); } catch { refus++; }
  ok("générer refuse terrain inconnu et rect vide", refus === 2, String(refus));
}

if (echecs.length) {
  console.error("ECHECS tuiles :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA tuiles : PASS (30 controles)");
```

- [ ] **Step 2 : banc RED planches**

```js
// planches.test.mjs — lot C : doc.planches (cadres nommés), commandes,
// guides d'aimantation, compilerSVG(doc, {cadre}) dont le viewBox EST la
// planche. État vide construit.
import { parserDoc, compilerSVG, op_planche_ajouter, op_planche_modifier,
         op_planche_supprimer, planches_guides, planche_de } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "P", taille: { w: 800, h: 600 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 100, y: 100, w: 50, h: 50, style: { fond: "#0047AB" } }] }] });

{
  const d = base();
  ok("état vide : aucun guide", planches_guides(d).v.length === 0 && planches_guides(d).h.length === 0);
  ok("état vide : planche_de rend null", planche_de(d, "p1") === null);
  const id = op_planche_ajouter(d, { nom: "Plateau", x: 0, y: 0, w: 400, h: 300 });
  ok("ajouter → p1, planche stockée", id === "p1" && d.planches.length === 1 && d.planches[0].nom === "Plateau");
  const id2 = op_planche_ajouter(d, { x: 400, y: 0, w: 400, h: 600 });
  ok("second id p2, nom par défaut", id2 === "p2" && d.planches[1].nom === "Planche 2");
  op_planche_modifier(d, "p1", { nom: "Carte", w: 200 });
  ok("modifier fusionne", d.planches[0].nom === "Carte" && d.planches[0].w === 200 && d.planches[0].h === 300);
  const g = planches_guides(d);
  ok("guides : bords des planches, triés, uniques", JSON.stringify(g.v) === JSON.stringify([0, 200, 400, 800]) && JSON.stringify(g.h) === JSON.stringify([0, 300, 600]), JSON.stringify(g));
  ok("parserDoc accepte", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  ok("les planches ne sont JAMAIS compilées", !compilerSVG(d).includes("planche"));
  // compilation cadrée sur une planche
  const svg = compilerSVG(d, { cadre: planche_de(d, "p2") });
  ok("cadre : viewBox = la planche, width/height = sa taille", svg.includes('viewBox="400 0 400 600"') && svg.includes('width="400" height="600"'), svg.slice(0, 160));
  ok("cadre : le contenu entier reste (le viewBox rogne)", svg.includes('data-objet="r1"'));
  op_planche_supprimer(d, "p1");
  ok("supprimer", d.planches.length === 1 && d.planches[0].id === "p2");
  op_planche_supprimer(d, "p2");
  ok("plus de planche → doc.planches disparaît", d.planches === undefined);
  let refus = 0;
  for (const s of [{ x: 0, y: 0, w: 0, h: 10 }, { x: 0, y: 0, w: 10 }, "x"]) { try { op_planche_ajouter(base(), s); } catch { refus++; } }
  try { op_planche_modifier(base(), "p9", {}); } catch { refus++; }
  ok("refus : 3 specs + planche inconnue", refus === 4, String(refus));
  const m = base(); m.planches = [{ id: "p1", x: 0, y: 0, w: -5, h: 5 }];
  let refusDoc = false; try { parserDoc(m); } catch { refusDoc = true; }
  ok("parserDoc refuse une planche malformée", refusDoc);
}

if (echecs.length) {
  console.error("ECHECS planches :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA planches : PASS (15 controles)");
```

- [ ] **Step 3 : RED** — les deux bancs : exports manquants.

- [ ] **Step 4 : implémenter dans `mod-doc.js`**

En tête, après `escAttr` :

```js
import { grille_normaliser, hex_centre, hex_d, hex_depuis_point, grille_cellules }
  from "./mod-grille.js";
```

Dans `parserDoc`, après `reperes` :

```js
  if (doc.grille !== undefined) grille_normaliser(doc.grille);
  if (doc.terrains !== undefined) {
    if (!doc.terrains || typeof doc.terrains !== "object" || Array.isArray(doc.terrains)) {
      throw new Error("document: terrains = {cle: fiche}");
    }
    for (const [k, f] of Object.entries(doc.terrains)) _validerTerrain(k, f);
  }
  if (doc.planches !== undefined) {
    if (!Array.isArray(doc.planches)) throw new Error("document: planches = liste");
    for (const p of doc.planches) { if (!p.id) throw new Error("planche sans id"); _validerCadre(p, `planche ${p.id}`); }
  }
```

Dans `_validerObjets`, un cas :

```js
    if (o.type === "tuile") {
      if (!Number.isInteger(o.q) || !Number.isInteger(o.r)) throw new Error(`tuile ${o.id}: q et r entiers requis`);
      if (typeof o.terrain !== "string" || !o.terrain) throw new Error(`tuile ${o.id}: terrain requis`);
      if (o.hauteur_mm !== undefined && !(o.hauteur_mm >= 0)) throw new Error(`tuile ${o.id}: hauteur_mm ≥ 0`);
    }
```

Bloc terrains / cadre (au-dessus de `parserDoc`) :

```js
/* ── lot C (D3) : la fiche de terrains — défauts fusionnés avec doc.terrains ── */
export const TERRAINS_DEFAUT = Object.freeze({
  mer:      Object.freeze({ nom: "Mer",      couleur: "#2B5F9E", hauteur_mm: 0, motif: "" }),
  plaine:   Object.freeze({ nom: "Plaine",   couleur: "#7FB069", hauteur_mm: 2, motif: "" }),
  foret:    Object.freeze({ nom: "Forêt",    couleur: "#3F7D3A", hauteur_mm: 3, motif: "" }),
  colline:  Object.freeze({ nom: "Colline",  couleur: "#B08D57", hauteur_mm: 5, motif: "" }),
  montagne: Object.freeze({ nom: "Montagne", couleur: "#8A8A8A", hauteur_mm: 8, motif: "" }),
});
const _CLE_TERRAIN = /^[a-z0-9_-]+$/;
function _validerTerrain(k, f) {
  if (!_CLE_TERRAIN.test(k)) throw new Error(`terrain: clé « ${k} » ([a-z0-9_-])`);
  if (!f || typeof f !== "object") throw new Error(`terrain ${k}: fiche requise`);
  if (f.couleur !== undefined && !/^#[0-9A-Fa-f]{3,8}$/.test(f.couleur)) throw new Error(`terrain ${k}: couleur hex`);
  if (f.hauteur_mm !== undefined && !(+f.hauteur_mm >= 0)) throw new Error(`terrain ${k}: hauteur_mm ≥ 0`);
}
export function terrains_de(doc) {
  const out = {};
  for (const [k, f] of Object.entries(TERRAINS_DEFAUT)) out[k] = { ...f };
  for (const [k, f] of Object.entries(doc.terrains || {})) out[k] = { ...(out[k] || { nom: k, couleur: "#888888", hauteur_mm: 0, motif: "" }), ...f };
  return out;
}
export function op_terrain_definir(doc, cle, fiche) {
  _validerTerrain(cle, fiche);
  if (!doc.terrains) doc.terrains = {};
  doc.terrains[cle] = { ...(doc.terrains[cle] || {}), ...fiche };
}
export function op_terrain_supprimer(doc, cle) {
  if (!doc.terrains || !doc.terrains[cle]) throw new Error(`terrain ${cle}: pas de surcharge à retirer`);
  delete doc.terrains[cle];
  if (!Object.keys(doc.terrains).length) delete doc.terrains;
}
function _validerCadre(c, ou) {
  if (!c || typeof c !== "object" || !(c.w > 0) || !(c.h > 0) || !Number.isFinite(+c.x) || !Number.isFinite(+c.y)) {
    throw new Error(`${ou}: cadre {x, y, w > 0, h > 0}`);
  }
}
const _GRILLE_TUILE_DEFAUT = { type: "hex", pas: 32, sous: 1, orientation: "pointe", origine: [0, 0], echelle: [1, 1] };
function _grilleHex(doc) {
  return (doc.grille && doc.grille.type === "hex") ? doc.grille : _GRILLE_TUILE_DEFAUT;
}
```

Dans `compilerObjet`, un cas `tuile` (le `ctx` porte `grille` et `terrains`) :

```js
    case "tuile": {
      const g = ctx.grille || _GRILLE_TUILE_DEFAUT;
      const [cx, cy] = hex_centre(o.q, o.r, g);
      const fiche = (ctx.terrains || {})[o.terrain];
      const fond = fiche ? fiche.couleur : "#888888";
      const inconnu = fiche ? "" : ` data-terrain-inconnu="1"`;
      const s = { fond, contour: "#1F1512", epaisseur: 1, ...(o.style || {}) };
      return `<path${t} data-q="${+o.q}" data-r="${+o.r}" data-terrain="${escAttr(o.terrain)}"${inconnu}`
        + ` d="${hex_d(cx, cy, g.pas, g.orientation, g.echelle)}"${styleAttrs(s, ctx)}${tr}/>`;
    }
```

et dans `compilerSVG` : `const ctx = { degrades: …, image: opts.image, grille: _grilleHex(doc), terrains: terrains_de(doc) };`
puis le cadre :

```js
  const cadre = opts.cadre ? (_validerCadre(opts.cadre, "cadre"), opts.cadre) : { x: 0, y: 0, w, h };
  …
  return `<svg xmlns="http://www.w3.org/2000/svg"`
       + ` viewBox="${+cadre.x} ${+cadre.y} ${+cadre.w} ${+cadre.h}" width="${+cadre.w}" height="${+cadre.h}">`
```

(le `fond` reste le rect 0,0,w,h de la page — le viewBox rogne.)

Géométrie des tuiles : dans `_decalerObjet` :

```js
    case "tuile": {
      // ancrée à la grille : le centre décalé est ré-arrondi à la cellule
      const g = _grilleHex(o.__doc || {});
      void g; break;   // (voir ci-dessous : la grille est passée par _decalerTuile)
    }
```

**Non** — `_decalerObjet` n'a pas le document. Faire passer la grille : dans
`op_deplacer`, AVANT la boucle : `const gh = _grilleHex(doc);` et pour chaque
objet : `if (o.type === "tuile") _decalerTuile(o, dx, dy, gh); else _decalerObjet(o, dx, dy);`
avec :

```js
function _decalerTuile(o, dx, dy, g) {
  const [cx, cy] = hex_centre(o.q, o.r, g);
  const a = hex_depuis_point(cx + dx, cy + dy, g);
  o.q = a.q; o.r = a.r;
}
```

Même chose dans `op_dupliquer` (`_decalerObjet(clone, dx, dy)` → si tuile,
`_decalerTuile(clone, dx, dy, _grilleHex(doc))`). `_mapperObjet` et `op_miroir` :
`case "tuile": break;` (ancrée — écart dit).

Commandes :

```js
/* ── grille du document (lot C) : une commande, un patch fusionné ── */
export function op_grille(doc, patch) {
  if (patch === null || patch === undefined) { delete doc.grille; return; }
  if (typeof patch !== "object") throw new Error("grille: patch objet requis");
  doc.grille = grille_normaliser({ ...(doc.grille || {}), ...patch });
}

/* ── tuiles (D3) ── */
export function tuile_a(doc, q, r) {
  for (const c of doc.calques) for (const o of c.objets) {
    if (o.type === "tuile" && o.q === q && o.r === r) return o;
  }
  return null;
}
export function op_tuiles_peindre(doc, calqueId, cellules, terrain) {
  if (!Array.isArray(cellules) || !cellules.length) throw new Error("pinceau: aucune cellule");
  if (!terrains_de(doc)[terrain]) throw new Error(`pinceau: terrain inconnu ${terrain}`);
  const c = _calque(doc, calqueId);
  if (c.verrou) throw new Error(`calque verrouillé: ${calqueId}`);
  const peintes = [], posees = [], vues = new Set();
  for (const cel of cellules) {
    const k = cel.q + "," + cel.r;
    if (vues.has(k)) continue;
    vues.add(k);
    let existante = null, verrouillee = false;
    for (const cl of doc.calques) for (const o of cl.objets) {
      if (o.type === "tuile" && o.q === cel.q && o.r === cel.r) { existante = o; verrouillee = !!cl.verrou; }
    }
    if (existante) {
      if (verrouillee) continue;
      existante.terrain = terrain; peintes.push(existante.id);
    } else {
      posees.push(op_ajouter(doc, calqueId, { type: "tuile", q: cel.q, r: cel.r, terrain }));
    }
  }
  return { peintes, posees };
}
export function op_plateau_generer(doc, spec) {
  const terrain = spec.terrain || "plaine";
  if (!terrains_de(doc)[terrain]) throw new Error(`plateau: terrain inconnu ${terrain}`);
  const cellules = grille_cellules(spec);          // refuse les specs invalides
  if (!doc.grille || doc.grille.type !== "hex") {
    doc.grille = grille_normaliser({ type: "hex", pas: +spec.pas || 32, orientation: spec.orientation || "pointe",
      origine: [doc.taille.w / 2, doc.taille.h / 2] });
  }
  const calqueId = op_calque_ajouter(doc, spec.nom || "plateau");
  const tuiles = cellules.map((cel) => op_ajouter(doc, calqueId, { type: "tuile", q: cel.q, r: cel.r, terrain }));
  const out = { calqueId, tuiles };
  if (spec.numeroter) {
    out.calqueNumeros = op_calque_ajouter(doc, "numéros");
    const g = doc.grille;
    for (const cel of cellules) {
      const [cx, cy] = hex_centre(cel.q, cel.r, g);
      op_ajouter(doc, out.calqueNumeros, { type: "texte", x: cx - g.pas * 0.45, y: cy + g.pas * 0.15,
        contenu: `${cel.q},${cel.r}`, style: { fond: "#1F1512", police: "Segoe UI", corps: Math.max(6, g.pas * 0.36) } });
    }
  }
  return out;
}

/* ── planches (lot C) : des cadres nommés, jamais compilés, aimantants ── */
export function planche_de(doc, id) {
  return (doc.planches || []).find((p) => p.id === id) || null;
}
export function op_planche_ajouter(doc, spec) {
  _validerCadre(spec, "planche");
  if (!doc.planches) doc.planches = [];
  const pris = new Set(doc.planches.map((p) => p.id));
  let n = 1; while (pris.has("p" + n)) n++;
  const id = "p" + n;
  doc.planches.push({ id, nom: String(spec.nom || `Planche ${n}`), x: +spec.x, y: +spec.y, w: +spec.w, h: +spec.h });
  return id;
}
export function op_planche_modifier(doc, id, patch) {
  const p = planche_de(doc, id);
  if (!p) throw new Error(`planche inconnue: ${id}`);
  const neuf = { ...p, ...(patch || {}) };
  _validerCadre(neuf, `planche ${id}`);
  Object.assign(p, { nom: String(neuf.nom), x: +neuf.x, y: +neuf.y, w: +neuf.w, h: +neuf.h });
}
export function op_planche_supprimer(doc, id) {
  const p = planche_de(doc, id);
  if (!p) throw new Error(`planche inconnue: ${id}`);
  doc.planches.splice(doc.planches.indexOf(p), 1);
  if (!doc.planches.length) delete doc.planches;
}
export function planches_guides(doc) {
  const v = [], h = [];
  for (const p of doc.planches || []) { v.push(p.x, p.x + p.w); h.push(p.y, p.y + p.h); }
  return { v: [...new Set(v)].sort((a, b) => a - b), h: [...new Set(h)].sort((a, b) => a - b) };
}
```

- [ ] **Step 5 : GREEN** des deux bancs + `node qa/run.mjs` (le snapshot ne
  change pas : pas de cadre, pas de tuile).

- [ ] **Step 6 : commit**

```bash
git add frontend/vectorlab/qa/tuiles.test.mjs frontend/vectorlab/qa/planches.test.mjs
git commit --only frontend/vectorlab/js/mod-doc.js frontend/vectorlab/qa/tuiles.test.mjs frontend/vectorlab/qa/planches.test.mjs -m "vectorlab : modele du lot C — grille du document, fiche de terrains, objet tuile ancre a la grille, pinceau et generateur de plateau, planches et compilation cadree (lot C, T3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 4 : cœur et outils — grille tracée, aimantation composée, pinceau de tuiles

**Files :** Modify `core.js`, `mod-tools.js`, `mod-export.js`, `index.html`, `vectorlab.css`

- [ ] **Step 1 : `core.js`**

Imports : `grille_d, grille_aimanter, hex_depuis_point` de `./mod-grille.js` ;
`planches_guides` de `./mod-doc.js` ; `aimant_objets, aimant_ecarts, aimant_fusion`
de `./mod-aimant.js` ; `initPlateau` de `./mod-plateau.js` ; `initPlanches`
de `./mod-planches.js`.

État : `etat.aimantObjets = true`, `etat.terrainCourant = "plaine"`.

`grilleDoc()` : `return etat.doc && etat.doc.grille ? etat.doc.grille : null;`

`aimantePt(x, y)` : si `grilleDoc()` et `etat.grille.active`, la position
aimantée au réseau remplace l'aimantation au `pas` :

```js
function aimantePt(x, y) {
  const g = etat.doc.guides || { v: [], h: [] };
  const rg = reperes_guides(etat.doc), pg = planches_guides(etat.doc);
  const guidesV = (g.v || []).concat(rg.v, pg.v), guidesH = (g.h || []).concat(rg.h, pg.h);
  const gd = grilleDoc();
  if (gd && etat.grille.active) {
    const [gx, gy] = grille_aimanter(gd, x, y);
    const tol = tolDoc();
    const ax = aimanter(x, { guides: guidesV }, tol), ay = aimanter(y, { guides: guidesH }, tol);
    return [ax !== x ? ax : (Math.abs(gx - x) <= tol ? gx : x),
            ay !== y ? ay : (Math.abs(gy - y) <= tol ? gy : y)];
  }
  const pas = etat.grille.active ? etat.grille.pas : 0;
  return [aimanter(x, { pas, guides: guidesV }, tolDoc()), aimanter(y, { pas, guides: guidesH }, tolDoc())];
}
```

`dessinerGrille()` : si `grilleDoc()`, le `d` vient de `grille_d(gd, etat.doc.taille)`
(vide = non tracée) ; la garde `grilleLisible()` lit `gd ? gd.pas : etat.grille.pas`.
`majBoutonGrille()` : libellé `⊞ hex 32` / `⊞ iso 20` / etc. quand `gd`.

`bboxDocDe(id)` déplacé ici depuis mod-style (mod-style l'appelle via `VL.bboxDocDe`) :

```js
function bboxDocDe(id) {
  const el = document.querySelector(`#canvasHost [data-objet="${id}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect(), r0 = stageRect();
  return { x: (r.left - r0.left - etat.tx) / etat.zoom, y: (r.top - r0.top - etat.ty) / etat.zoom,
           w: r.width / etat.zoom, h: r.height / etat.zoom };
}
// les voisins d'une sélection en mouvement : objets visibles non sélectionnés + planches
function candidatsAimant() {
  const sel = new Set(etat.selection);
  const out = [];
  for (const c of etat.doc.calques) {
    if (!c.visible) continue;
    for (const o of c.objets) { if (!sel.has(o.id)) { const b = bboxDocDe(o.id); if (b) out.push(b); } }
  }
  for (const p of etat.doc.planches || []) out.push({ x: p.x, y: p.y, w: p.w, h: p.h });
  out.push({ x: 0, y: 0, w: etat.doc.taille.w, h: etat.doc.taille.h });   // la page
  return out;
}
function aimanteBoite(b) {
  if (!etat.aimantObjets) return { dx: 0, dy: 0, lignes: [] };
  const cands = candidatsAimant();
  const tol = tolDoc();
  return aimant_fusion([aimant_objets(b, cands, tol), aimant_ecarts(b, cands, tol)]);
}
```

Overlay : cadres des planches (avant les repères) :

```js
  for (const p of etat.doc.planches || []) {
    const [ex, ey] = ecranPt(p.x, p.y);
    o.appendChild(ov("rect", { x: ex, y: ey, width: p.w * etat.zoom, height: p.h * etat.zoom, fill: "none",
      stroke: "#e0b34a", "stroke-width": 1, class: "planche", "data-planche": p.id, "pointer-events": "none" }));
    const lbl = ov("text", { x: ex + 4, y: ey - 5, fill: "#e0b34a", "font-size": 11, class: "planche-nom", "data-planche": p.id });
    lbl.textContent = p.nom; o.appendChild(lbl);
  }
```

Raccourci `k` → outil `tuiles` (dans la table `outils`) ; bouton `#btnAimant`
bascule `etat.aimantObjets` (classe `actif`). Exposer dans `VL` : `grilleDoc,
bboxDocDe, candidatsAimant, aimanteBoite`. Inits : `initPlateau(VL); initPlanches(VL);`
après `initTrace(VL)`.

- [ ] **Step 2 : `mod-tools.js` — déplacement aimanté aux objets + pinceau**

Dans le geste `move` (pointermove), APRÈS le calcul de `[cx, cy]` :

```js
      const boite = { x: cx, y: cy, w: geste.b0.w, h: geste.b0.h };
      const am = VL.aimanteBoite(boite);
      geste.dxA = cx + am.dx - geste.b0.x;
      geste.dyA = cy + am.dy - geste.b0.y;
      const gl = tmpDoc();
      for (const l of am.lignes) {
        forme(l.axe === "v" ? "line" : "line", l.axe === "v"
          ? { x1: l.pos, y1: -1e4, x2: l.pos, y2: 1e4, stroke: l.type === "ecart" ? "#e0b34a" : "#d05aa0", "stroke-width": 1 / etat.zoom, "stroke-dasharray": `${4 / etat.zoom} ${3 / etat.zoom}` }
          : { x1: -1e4, y1: l.pos, x2: 1e4, y2: l.pos, stroke: l.type === "ecart" ? "#e0b34a" : "#d05aa0", "stroke-width": 1 / etat.zoom, "stroke-dasharray": `${4 / etat.zoom} ${3 / etat.zoom}` }, gl);
      }
      etiquette(gl, dx, dy, VL.cote("delta", { dx: geste.dxA, dy: geste.dyA }));
```

(remplace les deux lignes `geste.dxA = …`/`geste.dyA = …` et l'`etiquette(tmpDoc(), …)`
existante ; la mise à jour des `transform` reste.)

Pinceau de tuiles (pointerdown, avant `texte`) :

```js
    if (etat.outil === "tuiles") {
      const g = VL.grilleDoc();
      if (!g || g.type !== "hex") { VL.toast("pinceau : poser d'abord une grille hexagonale (panneau Plateau)", true); return; }
      const cel = hex_depuis_point(dx, dy, g);
      geste = { type: "tuiles", cellules: [cel], vues: new Set([cel.q + "," + cel.r]) };
      apercuTuile(cel);
      ev.preventDefault();
      return;
    }
```

pointermove : `else if (geste.type === "tuiles") { const cel = hex_depuis_point(dx, dy, VL.grilleDoc()); const k = cel.q + "," + cel.r; if (!geste.vues.has(k)) { geste.vues.add(k); geste.cellules.push(cel); apercuTuile(cel); } }`

pointerup : `else if (g.type === "tuiles") { const r = VL.executer(op_tuiles_peindre, etat.calqueActif, g.cellules, etat.terrainCourant); if (r) VL.toast(`${r.peintes.length} tuile(s) peinte(s), ${r.posees.length} posée(s)`); }`

```js
  function apercuTuile(cel) {
    const g = VL.grilleDoc(); const host = $("#ovTmp");
    if (!g || !host) return;
    let grp = host.querySelector("g[data-tuiles]");
    if (!grp) { grp = tmpDoc(); grp.setAttribute("data-tuiles", "1"); }
    const [cx, cy] = hex_centre(cel.q, cel.r, g);
    forme("path", { d: hex_d(cx, cy, g.pas, g.orientation, g.echelle), fill: "rgba(224,179,74,.35)", stroke: "#e0b34a", "stroke-width": 1.5 / etat.zoom }, grp);
  }
```

Imports : `op_tuiles_peindre` de mod-doc ; `hex_depuis_point, hex_centre, hex_d`
de mod-grille. HINTS : `tuiles: "cliquer ou glisser sur les cellules : peint le terrain courant, pose la tuile manquante (K)"`.

- [ ] **Step 3 : `mod-export.js` — export par planche**

`rasteriser(k, transparent, cadre)` : `const svg = await svgCourant(transparent, cadre);`
avec `svgCourant(transparent, cadre)` → `compilerSVG(doc, { image: …, cadre })` ;
la taille du canvas = `(cadre || etat.doc.taille)` × k. `exporterPNG(k, opts = {})` :
`const png = await rasteriser(k, transparent, opts.cadre); const nom = \`vector_${etat.docId}${opts.suffixe || ""}_${k}x${transparent ? "_t" : ""}.png\`;`.

- [ ] **Step 4 : `index.html`**

Rail : après le bouton `texte` :
```html
      <button data-outil="tuiles" title="Pinceau de tuiles — peint le terrain courant, pose la tuile manquante (K)"><svg viewBox="0 0 24 24" fill="currentColor"><use href="#t-hex"></use></svg></button>
```
et le symbole : `<symbol id="t-hex" viewBox="0 0 24 24"><path d="M12 2.5 20.2 7.2v9.6L12 21.5 3.8 16.8V7.2z" fill="none" stroke="currentColor" stroke-width="1.7"></path></symbol>`.
Barre : après `#selGrille` : `<button id="btnAimant" class="actif" title="Aimantation aux objets : bords, centres, écarts réguliers">⌖</button>`.
Panneau : après `#panneauReperes` :
```html
      <div class="panneau-tete">Grille</div>
      <div id="panneauGrille"></div>
      <details id="plateauDetails"><summary class="panneau-tete">Plateau &amp; terrains</summary>
        <div id="panneauTerrains"></div><div id="panneauPlateau"></div></details>
      <details id="planchesDetails"><summary class="panneau-tete">Planches</summary><div id="panneauPlanches"></div></details>
      <details id="assetsDetails"><summary class="panneau-tete">Bibliothèque (Assets)</summary>
        <input id="assetsRecherche" type="search" placeholder="rechercher…"/><div id="assetsGrille" class="assets-grille"></div></details>
```

CSS : `.assets-grille { display:grid; grid-template-columns: repeat(2, 1fr); gap:6px; max-height: 260px; overflow:auto; }
.assets-grille .lib-carte { height: 96px; } .assets-grille .lib-carte img { height: 64px; }
.terrain { display:flex; align-items:center; gap:6px; padding:2px 4px; cursor:pointer; } .terrain.actif { background:#20293a; }
.terrain i { width:14px; height:14px; border-radius:3px; display:inline-block; border:1px solid #3a4150; }
.planche-ligne { display:flex; align-items:center; gap:4px; } .planche-ligne .nom { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }`

- [ ] **Step 5 : `node --check` de chaque module, `node qa/run.mjs` ; commit**

```bash
git commit --only frontend/vectorlab/js/core.js frontend/vectorlab/js/mod-tools.js frontend/vectorlab/js/mod-export.js frontend/vectorlab/js/mod-style.js frontend/vectorlab/index.html frontend/vectorlab/vectorlab.css -m "vectorlab : grille du document tracee et aimantante, aimantation aux objets avec lignes d'aide, pinceau de tuiles, export par planche (lot C, T4)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

(Ce commit n'est valide qu'avec la Task 5 : les modules importés doivent
exister — faire T4 et T5 puis committer ensemble si nécessaire.)

---

## Task 5 : UI — `mod-plateau.js`, `mod-planches.js`, panneau Assets

**Files :** Create `frontend/vectorlab/js/mod-plateau.js`, `frontend/vectorlab/js/mod-planches.js` ; Modify `mod-image.js` ; Test `frontend/vectorlab/qa/plateau_ui.test.mjs`

- [ ] **Step 1 : banc RED de la logique pure (libellés et lignes HTML)**

```js
// plateau_ui.test.mjs — la logique PURE des panneaux du lot C : lignes des
// terrains (échappement, actif, hauteur), libellé de grille, lignes des planches.
import { terrainLigne, grilleLibelle } from "../js/mod-plateau.js";
import { plancheLigne } from "../js/mod-planches.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
{
  const h = terrainLigne("foret", { nom: "For<êt>", couleur: "#3F7D3A", hauteur_mm: 3 }, true);
  ok("terrainLigne : échappe, pastille couleur, hauteur mm, actif", h.includes("For&lt;êt&gt;") && h.includes("background:#3F7D3A") && h.includes("3 mm") && h.includes('class="terrain actif"') && h.includes('data-terrain="foret"'), h);
  ok("terrainLigne inactif", !terrainLigne("mer", { nom: "Mer", couleur: "#2B5F9E", hauteur_mm: 0 }, false).includes("actif"));
}
{
  ok("grilleLibelle sans grille", grilleLibelle(null, 8) === "⊞ 8");
  ok("grilleLibelle hex", grilleLibelle({ type: "hex", pas: 32, orientation: "plat" }, 8) === "⊞ hex 32 plat");
  ok("grilleLibelle carrée subdivisée", grilleLibelle({ type: "carree", pas: 20, sous: 4 }, 8) === "⊞ 20 ÷4");
}
{
  const h = plancheLigne({ id: "p1", nom: "Carte <1>", x: 0, y: 0, w: 750, h: 1050 }, { affichage: "mm", dpi: 300 });
  ok("plancheLigne : nom échappé, taille en unité d'affichage, 4 actions", h.includes("Carte &lt;1&gt;") && h.includes("63.5 × 88.9 mm") && ["zoom", "png", "renommer", "supprimer"].every((a) => h.includes(`data-pl-${a}="p1"`)), h);
}
if (echecs.length) {
  console.error("ECHECS plateau_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA plateau_ui : PASS (6 controles)");
```

- [ ] **Step 2 : `mod-plateau.js`**

```js
// mod-plateau.js — lot C côté UI : le panneau Grille (type, pas,
// subdivisions, orientation, origine, échelle — une commande op_grille par
// changement), le panneau Terrains (fiche, terrain courant du pinceau,
// définir/retoucher/retirer) et le panneau Plateau (générateur : rayon ou
// rectangle, taille, orientation, terrain, numérotation). Logique PURE en
// tête (banc node).
import { op_grille, terrains_de, op_terrain_definir, op_terrain_supprimer,
         op_plateau_generer } from "./mod-doc.js";
import { GRILLE_TYPES } from "./mod-grille.js";

const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function terrainLigne(cle, f, actif) {
  return `<div class="terrain${actif ? " actif" : ""}" data-terrain="${esc(cle)}" title="Clic : terrain courant du pinceau · double-clic : retoucher">`
    + `<i style="background:${esc(f.couleur)}"></i><span class="nom">${esc(f.nom)}</span><small>${+f.hauteur_mm} mm</small></div>`;
}
export function grilleLibelle(g, pasAffichage) {
  if (!g) return "⊞ " + pasAffichage;
  if (g.type === "hex") return `⊞ hex ${g.pas} ${g.orientation}`;
  if (g.type === "carree") return `⊞ ${g.pas}` + (g.sous > 1 ? ` ÷${g.sous}` : "");
  return `⊞ ${g.type} ${g.pas}`;
}

/* ── DOM ── */
export function initPlateau(VL) {
  const { $, etat } = VL;
  const hG = $("#panneauGrille"), hT = $("#panneauTerrains"), hP = $("#panneauPlateau");

  function rendreGrille() {
    if (!etat.doc) { hG.innerHTML = ""; return; }
    const g = etat.doc.grille;
    hG.innerHTML = `
      <div class="ap-ligne"><span>Type</span>
        <select id="grType" title="Grille du document (sauvée avec lui) — « aucune » garde la grille carrée d'affichage">
          <option value=""${g ? "" : " selected"}>aucune (affichage)</option>
          ${GRILLE_TYPES.map((t) => `<option value="${t}"${g && g.type === t ? " selected" : ""}>${t}</option>`).join("")}
        </select></div>
      ${g ? `
      <div class="ap-ligne"><span>Pas</span>
        <input type="number" id="grPas" min="1" step="1" value="${g.pas}" title="Côté de maille, ou rayon de l'hexagone (px document)"/>
        ${g.type === "carree" ? `<input type="number" id="grSous" min="1" max="10" step="1" value="${g.sous}" title="Subdivisions"/>` : ""}
        ${g.type === "hex" ? `<select id="grOrient" title="Orientation"><option value="pointe"${g.orientation === "pointe" ? " selected" : ""}>pointe</option><option value="plat"${g.orientation === "plat" ? " selected" : ""}>plat</option></select>` : ""}
      </div>
      <div class="ap-ligne"><span>Origine</span>
        <input type="number" id="grOx" step="1" value="${g.origine[0]}" title="Origine X (px)"/>
        <input type="number" id="grOy" step="1" value="${g.origine[1]}" title="Origine Y (px)"/></div>
      <div class="ap-ligne"><span>Échelle</span>
        <input type="number" id="grSx" step="0.05" min="0.05" value="${g.echelle[0]}" title="Échelle X"/>
        <input type="number" id="grSy" step="0.05" min="0.05" value="${g.echelle[1]}" title="Échelle Y"/></div>` : ""}`;
    $("#grType").addEventListener("change", (e) => {
      const t = e.target.value;
      VL.executer(op_grille, t ? { type: t, pas: (g && g.pas) || 32 } : null);
    });
    if (!g) return;
    const patch = () => ({
      pas: Math.max(1, +$("#grPas").value || g.pas),
      sous: $("#grSous") ? Math.max(1, Math.round(+$("#grSous").value || 1)) : g.sous,
      orientation: $("#grOrient") ? $("#grOrient").value : g.orientation,
      origine: [+$("#grOx").value || 0, +$("#grOy").value || 0],
      echelle: [Math.max(0.05, +$("#grSx").value || 1), Math.max(0.05, +$("#grSy").value || 1)],
    });
    for (const id of ["grPas", "grSous", "grOrient", "grOx", "grOy", "grSx", "grSy"]) {
      const el = $("#" + id);
      if (el) el.addEventListener("change", () => VL.executer(op_grille, patch()));
    }
  }

  function rendreTerrains() {
    if (!etat.doc) { hT.innerHTML = ""; return; }
    const t = terrains_de(etat.doc);
    if (!t[etat.terrainCourant]) etat.terrainCourant = Object.keys(t)[0];
    hT.innerHTML = Object.entries(t).map(([k, f]) => terrainLigne(k, f, k === etat.terrainCourant)).join("")
      + `<div class="ap-ligne"><button id="terPlus" title="Nouveau terrain (clé, nom, couleur, hauteur mm)">＋ terrain</button>
         <button id="terMoins" title="Retirer la surcharge du terrain courant (un défaut revient à sa fiche)">− surcharge</button></div>`;
    hT.querySelectorAll(".terrain").forEach((el) => {
      el.addEventListener("click", () => { etat.terrainCourant = el.dataset.terrain; rendreTerrains(); });
      el.addEventListener("dblclick", () => retoucher(el.dataset.terrain));
    });
    $("#terPlus").addEventListener("click", () => {
      const cle = prompt("Clé du terrain ([a-z0-9_-]) :", "sable");
      if (!cle) return;
      retoucher(cle.trim().toLowerCase(), true);
    });
    $("#terMoins").addEventListener("click", () => VL.executer(op_terrain_supprimer, etat.terrainCourant));
  }
  function retoucher(cle, neuf) {
    const f = terrains_de(etat.doc)[cle] || { nom: cle, couleur: "#C2B280", hauteur_mm: 1 };
    const nom = prompt("Nom :", f.nom); if (nom === null) return;
    const couleur = prompt("Couleur hex :", f.couleur); if (couleur === null) return;
    const h = prompt("Hauteur d'extrusion (mm) :", String(f.hauteur_mm)); if (h === null) return;
    const ok = VL.executer(op_terrain_definir, cle, { nom, couleur: couleur.trim(), hauteur_mm: Math.max(0, +h || 0) });
    if (ok !== undefined || neuf) { etat.terrainCourant = cle; rendreTerrains(); }
  }

  function rendrePlateau() {
    if (!etat.doc) { hP.innerHTML = ""; return; }
    const g = etat.doc.grille;
    hP.innerHTML = `
      <div class="ap-ligne"><span>Forme</span>
        <select id="plMode"><option value="rayon">disque (rayon)</option><option value="rect">rectangle</option></select>
        <input type="number" id="plN1" min="0" max="60" value="3" title="Rayon en tuiles / colonnes"/>
        <input type="number" id="plN2" min="1" max="120" value="4" title="Lignes (rectangle)" style="display:none"/></div>
      <div class="ap-ligne"><span>Hexagone</span>
        <input type="number" id="plPas" min="4" value="${g && g.type === "hex" ? g.pas : 40}" title="Rayon de l'hexagone (px) — ignoré si la grille hex existe"/>
        <select id="plOrient"><option value="pointe">pointe</option><option value="plat">plat</option></select></div>
      <div class="ap-ligne"><label><input type="checkbox" id="plNum"/> numéroter q,r</label>
        <button id="plGenerer" class="primaire" title="Pose la grille hexagonale (si absente, centrée) et un calque de tuiles du terrain courant — une commande, annulable">Générer le plateau</button></div>`;
    $("#plMode").addEventListener("change", (e) => { $("#plN2").style.display = e.target.value === "rect" ? "" : "none"; });
    $("#plGenerer").addEventListener("click", () => {
      const mode = $("#plMode").value;
      const spec = { mode, pas: +$("#plPas").value, orientation: $("#plOrient").value,
                     terrain: etat.terrainCourant, numeroter: $("#plNum").checked };
      if (mode === "rayon") spec.rayon = Math.round(+$("#plN1").value);
      else { spec.colonnes = Math.round(+$("#plN1").value); spec.lignes = Math.round(+$("#plN2").value); }
      const r = VL.executer(op_plateau_generer, spec);
      if (r) { etat.calqueActif = r.calqueId; VL.setSelection([]); VL.setOutil("tuiles"); VL.toast(`${r.tuiles.length} tuile(s) posées — pinceau actif`); }
    });
  }

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendreGrille(); rendreTerrains(); rendrePlateau(); };
  VL.grilleLibelle = grilleLibelle;
}
```

- [ ] **Step 3 : `mod-planches.js`**

```js
// mod-planches.js — lot C : le panneau Planches (liste, ajouter depuis la
// sélection ou depuis la page, zoom sur une planche, renommer, retirer,
// PNG 2× de la planche). Les cadres se tracent dans l'overlay du cœur.
import { op_planche_ajouter, op_planche_modifier, op_planche_supprimer, planche_de } from "./mod-doc.js";
import { versUnite, suffixe } from "./mod-unites.js";

const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ── pur ── */
export function plancheLigne(p, unites) {
  const u = (v) => Math.round(versUnite(v, unites) * 10) / 10;
  return `<div class="planche-ligne" data-planche="${esc(p.id)}">`
    + `<span class="nom" title="${esc(p.nom)}">${esc(p.nom)}</span><small>${u(p.w)} × ${u(p.h)} ${esc(suffixe(unites.affichage))}</small>`
    + `<button data-pl-zoom="${esc(p.id)}" title="Cadrer la vue sur la planche">⌕</button>`
    + `<button data-pl-png="${esc(p.id)}" title="PNG 2× de la planche → Library">2×</button>`
    + `<button data-pl-renommer="${esc(p.id)}" title="Renommer">✎</button>`
    + `<button data-pl-supprimer="${esc(p.id)}" title="Retirer la planche (les objets restent)">✕</button></div>`;
}

/* ── DOM ── */
export function initPlanches(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauPlanches");
  function rendre() {
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const ps = etat.doc.planches || [];
    hote.innerHTML = (ps.length ? ps.map((p) => plancheLigne(p, VL.unites())).join("")
      : `<p class="vl-amorce">Aucune planche — la page entière est la seule surface.</p>`)
      + `<div class="ap-ligne"><button id="plaSel" ${etat.selection.length ? "" : "disabled"} title="Une planche au cadre de la sélection">＋ sélection</button>
         <button id="plaPage" title="Une planche de la taille de la page, à droite de la dernière">＋ page</button></div>`;
    $("#plaSel").addEventListener("click", () => {
      const b = VL.bboxSelectionDoc(); if (!b) return;
      const id = VL.executer(op_planche_ajouter, { nom: "", x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.w), h: Math.round(b.h) });
      if (id) VL.toast(`planche ${id} créée`);
    });
    $("#plaPage").addEventListener("click", () => {
      const der = ps[ps.length - 1];
      const x = der ? der.x + der.w + 40 : 0;
      VL.executer(op_planche_ajouter, { nom: "", x, y: 0, w: etat.doc.taille.w, h: etat.doc.taille.h });
    });
    hote.querySelectorAll("[data-pl-zoom]").forEach((b) => b.addEventListener("click", () => zoomSur(b.dataset.plZoom)));
    hote.querySelectorAll("[data-pl-png]").forEach((b) => b.addEventListener("click", () => {
      const p = planche_de(etat.doc, b.dataset.plPng);
      VL.exporterPNG(2, { cadre: p, suffixe: "_" + p.id }).then((f) => VL.toast(`${f} déposé (planche ${p.nom})`))
        .catch((e) => VL.toast(e.message, true));
    }));
    hote.querySelectorAll("[data-pl-renommer]").forEach((b) => b.addEventListener("click", () => {
      const p = planche_de(etat.doc, b.dataset.plRenommer);
      const nom = prompt("Nom de la planche :", p.nom);
      if (nom !== null) VL.executer(op_planche_modifier, p.id, { nom });
    }));
    hote.querySelectorAll("[data-pl-supprimer]").forEach((b) => b.addEventListener("click", () => VL.executer(op_planche_supprimer, b.dataset.plSupprimer)));
  }
  function zoomSur(id) {
    const p = planche_de(etat.doc, id); if (!p) return;
    const r = $("#stage").getBoundingClientRect();
    etat.zoom = Math.max(0.05, Math.min(16, Math.min((r.width - 80) / p.w, (r.height - 80) / p.h)));
    etat.tx = (r.width - p.w * etat.zoom) / 2 - p.x * etat.zoom;
    etat.ty = (r.height - p.h * etat.zoom) / 2 - p.y * etat.zoom;
    VL.appliquerVue();
  }
  const suivant = VL.surRendu; VL.surRendu = () => { suivant(); rendre(); };
  const suivantSel = VL.surSelection; VL.surSelection = () => { suivantSel(); rendre(); };
  VL.zoomPlanche = zoomSur;
}
```

- [ ] **Step 4 : panneau Assets dans `mod-image.js`** (dans `initImage`, après la
  grille de repli) :

```js
  /* ── panneau Assets : la Bibliothèque en permanence dans le panneau, un
     clic pose l'image (lot C) — chargée à l'ouverture du volet ── */
  const det = $("#assetsDetails");
  let assets = null;
  async function chargerAssets() {
    $("#assetsGrille").innerHTML = `<p class="lib-vide">chargement…</p>`;
    const d = await VL.api.get("/images");
    assets = (d.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
    $("#assetsGrille").innerHTML = libListeHTML(assets, $("#assetsRecherche").value);
  }
  det.addEventListener("toggle", () => { if (det.open && !assets) chargerAssets().catch((e) => VL.toast(e.message, true)); });
  $("#assetsRecherche").addEventListener("input", () => { $("#assetsGrille").innerHTML = libListeHTML(assets || [], $("#assetsRecherche").value); });
  $("#assetsGrille").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-lib-nom]"); if (!b) return;
    poserDepuisLibrary(b.dataset.libNom).catch((e) => VL.toast(e.message, true));
  });
  VL.poserDepuisLibrary = poserDepuisLibrary;
```

- [ ] **Step 5 : GREEN** — `node qa/plateau_ui.test.mjs`, `node qa/run.mjs`, `node --check js/*.js`.

- [ ] **Step 6 : commit (T4 + T5 ensemble si T4 n'a pas pu l'être seul)**

```bash
git add frontend/vectorlab/js/mod-plateau.js frontend/vectorlab/js/mod-planches.js frontend/vectorlab/qa/plateau_ui.test.mjs
git commit --only frontend/vectorlab/js/mod-plateau.js frontend/vectorlab/js/mod-planches.js frontend/vectorlab/qa/plateau_ui.test.mjs frontend/vectorlab/js/mod-image.js frontend/vectorlab/js/core.js frontend/vectorlab/js/mod-tools.js frontend/vectorlab/js/mod-export.js frontend/vectorlab/js/mod-style.js frontend/vectorlab/index.html frontend/vectorlab/vectorlab.css -m "vectorlab : panneaux Grille, Terrains, Plateau, Planches et Assets — generateur hex, pinceau de tuiles, export par planche (lot C, T5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 6 : miroirs pytest

**Files :** Modify `backend/tests/test_vector_docs.py`

- [ ] **Step 1 : tests**

```python
# ── S. lot C : grille, terrains, tuiles, planches — aller-retour et surface ──

def test_les_champs_du_lot_c_font_l_aller_retour():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            doc = _doc("Plateau")
            doc["grille"] = {"type": "hex", "pas": 40, "sous": 1, "orientation": "plat",
                             "origine": [320, 480], "echelle": [1, 1]}
            doc["terrains"] = {"lave": {"nom": "Lave", "couleur": "#D33", "hauteur_mm": 1, "motif": ""}}
            doc["planches"] = [{"id": "p1", "nom": "Plateau", "x": 0, "y": 0, "w": 640, "h": 480}]
            doc["calques"][0]["objets"].append({"id": "t1", "type": "tuile", "q": 0, "r": 0, "terrain": "lave"})
            r = await c.post("/api/vector/docs", json={"name": "Plateau", "role": "libre", "doc": doc})
            did = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{did}")
            d = r.json()["doc"]
            assert d["grille"]["orientation"] == "plat" and d["grille"]["origine"] == [320, 480]
            assert d["terrains"]["lave"]["hauteur_mm"] == 1
            assert d["planches"][0]["w"] == 640
            assert d["calques"][0]["objets"][0]["type"] == "tuile"
            # un document SANS ces champs reste intact (rétro-compatibilité)
            r = await c.post("/api/vector/docs", json={"name": "V1", "role": "libre", "doc": _doc()})
            r = await c.get(f"/api/vector/docs/{r.json()['id']}")
            assert "grille" not in r.json()["doc"] and "planches" not in r.json()["doc"]

    asyncio.run(scenario())


def test_le_miroir_lot_c_grilles_plateau_planches():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    html = (vl / "index.html").read_text("utf-8")
    core = (vl / "js" / "core.js").read_text("utf-8")
    for m in ("mod-grille.js", "mod-aimant.js", "mod-plateau.js", "mod-planches.js"):
        assert (vl / "js" / m).is_file(), m
    # les modules géométriques sont des FEUILLES : aucun import (bancables partout)
    for m in ("mod-grille.js", "mod-aimant.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m
    assert "initPlateau(VL)" in core and "initPlanches(VL)" in core
    assert "grille_d(" in core and "aimant_fusion(" in core and "planches_guides(" in core
    for tok in ("panneauGrille", "panneauTerrains", "panneauPlateau", "panneauPlanches",
                "assetsDetails", "assetsGrille", "btnAimant"):
        assert f'id="{tok}"' in html, tok
    assert 'data-outil="tuiles"' in html
    qa = vl / "qa"
    for b in ("grille", "aimant_objets", "tuiles", "planches", "plateau_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    assert "TERRAINS_DEFAUT" in doc and "op_plateau_generer" in doc and "op_tuiles_peindre" in doc
    assert 'case "tuile"' in doc and "opts.cadre" in doc
```

- [ ] **Step 2 : `pytest tests/test_vector_docs.py -q` → 27 passed ; commit**

```bash
git commit --only backend/tests/test_vector_docs.py -m "vectorlab : miroirs pytest du lot C — aller-retour grille/terrains/tuiles/planches, surface (lot C, T6)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 7 : preuve en réel (backend du worktree, 8799, données isolées, viewport émulé)

- [ ] Créer un doc 1200×900 ; panneau Grille → type `hex`, pas 40 : `#canvasHost #dzGrille path` a un `d` contenant ≥ 100 `Z`, `getBoundingClientRect().height > 0` ; type `iso` : lignes ; `carree` ÷4 : compte de `M`.
- [ ] Générer le plateau (rayon 3, terrain plaine, numéroter) : 37 `path[data-terrain]` + 37 textes ; l'origine de la grille au centre (600, 450) ; le calque actif = plateau, outil `tuiles` actif.
- [ ] Pinceau : `pointerdown/move/up` sur trois cellules dont une vide → toast « 2 peinte(s), 1 posée(s) », les `data-terrain` passent au terrain courant (choisir « foret » par clic sur la ligne).
- [ ] Aimantation aux objets : deux rects ; déplacer le second près du bord droit du premier → `dxA` colle (bbox.x = right voisin) et une `line` d'aide `#d05aa0` dans `#ovTmp` pendant le geste ; trois rects → écart régulier (ligne `#e0b34a`).
- [ ] Planches : « ＋ sélection », « ＋ page » → deux `rect.planche` d'overlay mesurables, libellés ; « 2× » sur p1 → `vector_<id>_p1_2x.png` 200 image/png de taille 2×(w,h) de la planche ; zoom planche → `etat.zoom` change.
- [ ] Assets : ouvrir le volet → grille chargée (`.lib-carte` ≥ 1, `offsetHeight` 96), clic → image posée.
- [ ] Sauver → relire : `grille`, `terrains` (si surcharge), `planches`, tuiles présents.
- [ ] Négatifs : pinceau sans grille hex → toast ; générer avec terrain inconnu impossible depuis l'UI (liste) → vérifié au banc ; `op_grille` pas 0 → toast.

## Task 8 : déploiement et relevé

- [ ] Table `git hash-object` (installé = `7c99667` pour les fichiers du lot A modifiés ici : `core.js`, `mod-tools.js`, `mod-export.js`, `mod-style.js`, `mod-image.js`, `mod-doc.js`, `index.html`, `vectorlab.css` ; `test_vector_docs.py` non déployé) ; sauvegarde `_backup_predeploy_2026-09-17b-vectorlab-lotC` ; copie depuis `git archive` ; vérification = cible ; aucun fichier Python touché → **aucune relance nécessaire** (statiques relus du disque) ; le dire.
- [ ] Relevé de livraison en tête de ce plan, commit, push. Mémoire.

## Auto-revue

- **Couverture §4 lot C** : grilles carrée subdivisée / iso / tri / hex pointe-plat, taille, origine, échelle ✔ (T1, T3, T4, T5) ; aimantation aux objets bords/centres/écarts ✔ (T2, T4) ; générateur hex rayon/rectangle, numérotation axiale ✔ (T1 `grille_cellules`, T3 `op_plateau_generer`) ; objets `tuile` + fiche de terrains (nom, couleur, hauteur mm, motif — `motif` porté par la fiche, rendu au lot F) ✔ ; pinceau de tuiles ✔ (T4) ; planches multiples ✔ (T3, T5, export par planche) ; panneau Assets branché sur la Bibliothèque ✔ (T5).
- **Écarts déclarés** : `motif` de terrain stocké mais non rendu (lot F : motifs) ; miroir/redimensionnement d'une tuile sans effet (ancrée) ; le générateur ne déplace pas une grille hex existante (il la garde) ; l'export par planche passe par le PNG de la Library (les tranches nommées et multi-formats sont le lot G).
- **Cohérence des noms** : `grille_normaliser / hex_centre / hex_sommets / hex_d / hex_depuis_point / grille_d / grille_aimanter / grille_cellules` (mod-grille) ; `aimant_objets / aimant_ecarts / aimant_fusion` (mod-aimant) ; `op_grille / TERRAINS_DEFAUT / terrains_de / op_terrain_definir / op_terrain_supprimer / tuile_a / op_tuiles_peindre / op_plateau_generer / planche_de / op_planche_ajouter / op_planche_modifier / op_planche_supprimer / planches_guides` (mod-doc) ; `terrainLigne / grilleLibelle / initPlateau` ; `plancheLigne / initPlanches` ; `VL.grilleDoc / bboxDocDe / candidatsAimant / aimanteBoite / zoomPlanche / poserDepuisLibrary` ; `exporterPNG(k, {cadre, suffixe})`.
