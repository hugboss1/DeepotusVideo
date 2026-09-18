# Vectorlab relooking Affinity — R6 raffinements — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `…-relooking-design.md` (R-D2 Histogramme ajouté, R-D9 audit final) ; « Reste » des relevés R1→R5.

**Goal :** les derniers écarts relevés pendant l'exploration d'Affinity
sont comblés — panneau **Histogramme** du persona Pixel (canaux RVB + L
sur fond noir, moyenne / écart-type / médiane / pixels), bulles d'outil
riches (titre, puis gestes aux verbes en gras comme « **Glisser** les
poignées… »), nom du document au-dessus de la page comme le nom de
planche d'Affinity, nuancier en place compacté, audit final de
lisibilité des deux personas.

**Architecture :** `mod-histogramme.js` feuille (`histogramme(tampon)` →
quatre tableaux de 256 + statistiques, `histogramme_chemins(h, w, hauteur)`
→ chemins SVG normalisés) ; `mod-statut` gagne `verbes_gras(texte)`
(extrait de `phrase_statut`) que `mod-infobulle` applique aux lignes de
suite ; `mod-onglets` : onglet `histogramme` en tête du groupe 1 de Pixel
(2 / 4 / 4) ; `mod-pile` rend l'Histogramme depuis `etat.px.tampon` (les
pixels chargés par « Éditer les pixels ») ; `core.js` : le nom du document
au-dessus de la page dans l'overlay quand il n'y a pas de planche ; CSS.

**Tech :** vanilla ESM, CSS ; node `qa/run.mjs`.

---

### Task 1 : `mod-histogramme.js` (RED → vert)

```js
// histogramme.test.mjs
import { histogramme, histogramme_chemins } from "../js/mod-histogramme.js";
// tampon 2 × 2 : noir opaque, blanc opaque, rouge opaque, transparent (ignoré)
const t = { w: 2, h: 2, data: new Uint8ClampedArray([0,0,0,255, 255,255,255,255, 255,0,0,255, 9,9,9,0]) };
const h = histogramme(t);
ok("quatre canaux de 256 ; 3 pixels comptés (le transparent est ignoré)", h.r.length === 256 && h.l.length === 256 && h.pixels === 3 && h.r[0] === 1 && h.r[255] === 2 && h.g[255] === 1 && h.b[0] === 2);
ok("luminance : noir 0, blanc 255, rouge ≈ 54 (Rec. 601)", h.l[0] === 1 && h.l[255] === 1 && h.l[54] === 1);
ok("statistiques : moyenne 103, écart-type ≈ 108,7, médiane 54", h.moyenne === 103 && Math.abs(h.ecartType - 108.66) < 0.05 && h.mediane === 54, JSON.stringify([h.moyenne, h.ecartType, h.mediane]));
ok("état vide : tampon nul ou sans pixel opaque → 0 partout, chemins vides", histogramme(null).pixels === 0 && histogramme({ w: 1, h: 1, data: new Uint8ClampedArray([1,2,3,0]) }).pixels === 0 && histogramme_chemins(histogramme(null), 200, 80).l === "");
const c = histogramme_chemins(h, 256, 100);
ok("chemins : un par canal, normalisés au maximum, de bas en bas (fermés), largeur = w", c.r.startsWith("M0 100") && c.r.endsWith("L256 100Z") && /L0 (0|0\.0+) /.test(c.r) === false && c.r.includes("L0.5 50") === false && c.l.length > 20);
```
Module : `histogramme(tampon)` compte les pixels d'alpha > 0 ; `l = Math.round(0.299 r + 0.587 g + 0.114 b)` ; moyenne / écart-type (population) / médiane sur `l` ; `histogramme_chemins(h, w, hauteur)` : pour chaque canal, `M0 h` puis 256 points `L x y` avec `x = i * w / 255`, `y = h − v / max * h` (max = max des quatre canaux, 1 si 0), puis `L w h Z` ; canal sans pixel → chaîne vide.

### Task 2 : bulles riches

- `mod-statut` : `export function verbes_gras(texte)` (le `replace` de `phrase_statut`, lignes de suite comprises) ; `phrase_statut` l'appelle ; banc statut +1 contrôle (« **Glisser** les poignées, **Maj** contraint »).
- `mod-infobulle` : les lignes `ib-suite` passent par `statut_html(verbes_gras(l))` (import de mod-statut) ; banc infobulle +1 contrôle sur `texte_bulle` inchangé (les gras sont posés côté HTML).

### Task 3 : Histogramme dans la pile, nom de page, nuancier compact

- `mod-onglets` : `histogramme: o("Histogramme", "histogrammeDetails")`, `GROUPES.pixel[0] = ["histogramme", "couleur"]` (défaut Pixel groupe 1 : couleur) ; banc onglets : « Pixel : 2 / 4 / 4 ».
- `index.html` : `<details id="histogrammeDetails"><summary class="panneau-tete">Histogramme</summary><div id="panneauHistogramme"></div></details>` ; `mod-panneaux` : l'id.
- `mod-pile` : `rendreHistogramme()` sur `surRendu` et quand l'onglet s'active : si `etat.px && etat.px.tampon` → `<svg viewBox="0 0 256 100">` fond noir, quatre `<path>` (r rouge, g vert, b bleu, l gris à 60 %, `mix-blend-mode: screen`), puis `Moyenne · Écart-type · Médiane · Pixels` ; sinon la note « Éditer les pixels d'une image (persona Pixel) pour lire son histogramme ».
- `core.js` `rendreOverlay` : sans planche, un `<text class="page-nom">` avec `etat.meta.name` à 4 px au-dessus du coin haut-gauche de la page (même style que `planche-nom`, couleur `--aff-muet`).
- CSS : `#panneauCouleurInline > #nuancier #nuSV { height: 96px }`, `.hist-svg { width: 100%; height: 100px; background: #000; border-radius: 3px }`, `.hist-stats { font-size: 11px; color: var(--aff-muet); display: grid; grid-template-columns: 1fr 1fr; gap: 2px 8px }`.

### Task 4 : preuve, audit final, déploiement, relevé

8799, 1400 × 900 : persona Pixel → onglets 2 / 4 / 4, Histogramme sans image → la note ; poser une image (PNG réel généré par python) + « Éditer les pixels » → svg avec 4 paths et pixels > 0 ; bulle de l'outil Plume (`VL.infobulle.montrer`) → `.ib-suite` contient `<b>` ; nom du document au-dessus de la page (`text.page-nom` dans `#overlay`) ; audit des deux personas : toutes les `.ap-ligne` visibles `scrollWidth ≤ clientWidth + 1`, champs ≥ 22 px, aucun onglet tronqué, les six bandes ; taskkill ; déploiement ; relevé ; mémoire ; push.
