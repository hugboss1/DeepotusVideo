# Finitions UI — chantier 3 : panneaux équilibrés et contrôles maison — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** les panneaux du persona Vecteur (Apparence, Apparence + : Remplissage, Couleurs globales) et du persona Pixel (Pixel-art, Couleurs, Modèle, Ligne de temps, Ajustements) n'ont plus de curseur ni de case à cocher natifs, leurs rangées ne débordent plus, leurs boutons de rangée sont d'égale largeur — mesuré par un audit DOM bancable.

**Architecture :** `mod-controles.js` = fonctions PURES bancables (valeur d'un curseur depuis une position, pas au clavier/molette, largeurs égales d'une rangée, `auditer(mesures)` qui juge des mesures DOM) + éléments personnalisés `<vl-curseur>`, `<vl-curseur-couleur>`, `<vl-bascule>` qui exposent `value` / `checked` et émettent `input` / `change` bubbling — les modules existants gardent leurs `on(id, "input"|"change")` et `val(id)`, seuls les gabarits HTML changent. `VL.ergonomie.mesurer()` relève le DOM des panneaux visés (in-page), `auditer` juge (pur). Un banc `qa/ergonomie.test.mjs` bance `auditer` et les purs ; la preuve exécute mesurer + auditer dans les trois personas.

**Tech :** custom elements v1 (le Vectorlab est en ES modules natifs), CSS aux jetons `--aff-*` / `--pan-*` (le banc `theme.test.mjs` refuse les hex hérités).

## Relevé de livraison (20/09/2026)

- **Livré** : `mod-controles.js` — purs `curseur_valeur / curseur_position / curseur_pas / rangee_largeurs / auditer` + éléments `<vl-curseur>` (piste 4 px, poignée 14 px, valeur éditable, flèches, Maj ×10, molette), `<vl-curseur-couleur>` (pastille → nuancier maison, double-clic = sélecteur système ; `mode="teinte"` = roue des teintes), `<vl-bascule>` (interrupteur 34 × 18, rôle switch, Espace/Entrée), `.vl-rangee`, `VL.ergonomie.mesurer/auditer` — `2b1c0fa` ; gabarits : Pixel (1 range + 9 cases + 2 couleurs + 6 `number` à pas fin → maison ; 6 rangées de boutons en `.vl-rangee`, Palette N sur sa rangée), Apparence + (`a2Decalage`, rangée Remplissage « Conique / Transparence / ✕ masque »), Apparence (`apOpacite` avec valeur intégrée), nuancier (`nuH` teinte) ; palette en grille 6 × 22 px / 6 px — `28837a3` ; champs des panneaux à **28 px** : le jeton `--pan-champ-h` était écrasé à 24 px par la densité R4 (`249afed`) et quatre règles portaient 24 px en dur → ramenées au jeton ; libellé « Désigner comme modèle » ; boutons de rangée rétractables (ellipse) — `7d3d6a1`.
- **TDD** : `qa/ergonomie.test.mjs` RED (module absent) → GREEN 8 contrôles (curseur, rangée, audit avec état vide et tolérance ± 1 px) ; `run.mjs` intégral vert, `theme.test` (hex hérités) vert — toutes les couleurs nouvelles en `var(--aff-*)` / `--pan-*`.
- **Prouvé** (8799, 1400 × 900, `onerror` capturé, zéro erreur) : persona Vecteur, rectangle sélectionné, onglets Couleur / Apparence + (toutes sections ouvertes) → `VL.ergonomie.auditer()` = **[]** sur 11 rangées ; rangée Remplissage 71 / 71 / 71 px ; curseur Opacité 103 × 28 px : glisser réel (`PointerEvent` 50 % → 25 %) → `style.opacite` 0,25 ; Maj + flèche → 35 ; molette → 36 → 0,36. Persona Pixel, image sélectionnée, toutes sections ouvertes → audit **[]** sur 34 rangées, 0 natif ; bascule `pxGrille` clic → `etat.px.grille` true → false ; `pxDurete` glissé 20 % → 80 % → `etat.px.durete` 0,8 ; palette en `22px × 6` ; rangées 110/110, 71/71/71 ; pastille `pxCouleur` clic → nuancier visible, teinte glissée à 33 % → `nuH.value` 118, poignée `hsl(118 100% 50%)`, `#nuHex` `#FF0000` → `#09FF00`. Sans sélection → [] ; onglet Exporter → [] (1 rangée). Avant correction, l'audit avait DÉMASQUÉ : 31 contrôles à 24 px (R4), un libellé qui débordait (230 > 225), une rangée « inégale » à cause d'un `<span>` de score (mesure restreinte aux `button`).
- **Déployé** : 8 fichiers vers `%LOCALAPPDATA%\DeepotusVideoGen` (installé = base `5b82c7a`), sauvegarde `_backup_predeploy_2026-09-20-panneaux`, installé = cible par `git hash-object`, `GET :8765/vectorlab/js/mod-controles.js` 200 ; statiques seuls, aucune relance.
- **Reste / écarts** : le code n'a que DEUX personas (`vecteur`, `pixel`, `mod-persona.js`) — le « troisième » du spec est l'onglet Exporter, audité aussi ; le nuancier flottant (210 px, champs RGB/CMJN à 18 px) est hors périmètre de l'audit (relevé : 11 violations si on l'y met) ; l'édition des pixels (`pxEditer`) n'a pas chargé de tampon dans le volet caché (`Image.decode` suspendu, piège connu) — l'audit porte sur le panneau rendu, tampon ou non ; `Image.decode` : à ouvrir par `onload` si une preuve future en a besoin.

---

## Relevé (code lu le 20/09/2026 à `5b82c7a`)

| Module | Natifs dans les panneaux visés | Écouteurs | Décision |
|---|---|---|---|
| `mod-pixelui.js` (Pixel : Modèle, Couleur, Dureté, Sélection, Ajustements, Pixel-art, Ligne de temps) | `range` ×1 (`pxDurete`, `on(…,"input")` + `val`), `checkbox` ×10 (`pxTuileArtOn`, `pxRamener`, `pxGlobal`, `pxGrille`, `pxIso`, `pxSymH/V`, `pxLoop`, `pxPelure` — lus par `ev.target.checked` ou `$("#pxSymH").checked`), `color` ×2 (`pxCouleur`, `pxSecondaire`, `on(…,"input")`, `ev.target.value`), `number` ×~22 via `num(id, v, attrs)` (Tuile W/H, tolérance, rayon, FPS, contour, accentuation, flou…) | `on(id, ev, fn)` local, `val(id)` = `+$("#id").value` | `pxDurete` → `<vl-curseur>` ; 10 cases → `<vl-bascule>` (propriété `checked`, `change`) ; `pxCouleur/pxSecondaire` → `<vl-curseur-couleur>` (double-clic = `<input type=color>` natif hors panneau, ouvert par le composant) ; `number` à pas fin → `<vl-curseur>` pour rayon (0,5–64), tolérance (0–255), FPS (1–60), contour (1–4), accentuation (0,1–2), flou (1–50) ; les autres `number` (tuile, niveaux, cellule) restent des champs |
| `mod-apparence2.js` (Apparence + : effets, contours, Remplissage, motifs, couleurs globales, texte +, pinceau) | `range` ×1 (`a2Decalage`), `number` ×10, rangée `a2Conique / a2Transp / a2MasqueX` (libellés « ◔ conique » / « ◧ transparence » / « ✕ » — capture 2 : largeurs inégales, ✕ décalé) | `on(id, ev, fn)` ; `input[data-fx]`/`[data-ct]` par `querySelectorAll` + `change` | `a2Decalage` → `<vl-curseur>` ; la rangée Remplissage → `.vl-rangee` (trois boutons égaux : « Conique », « Transparence », « ✕ masque ») |
| `mod-style.js` (Apparence : X·Y·L·H redistribués, Opacité) | `range` ×1 (`apOpacite`, `input` + `change`), `number` ×8 | `$("#apOpacite").addEventListener` | `apOpacite` → `<vl-curseur>` (0–100, valeur affichée par le composant : `<b id="apOpaciteVal">` conservé) |
| `mod-couleur.js` (le nuancier flottant `#nuancier`, ouvert depuis Couleurs / pastilles) | `range` `nuH` (teinte 0–359, `input`), `number` ×7 RGB/CMJN | `$("#nuH").addEventListener("input")` | `nuH` → `<vl-curseur-couleur mode="teinte">` (piste = dégradé des teintes, poignée = couleur courante) |
| CSS | `.ap-ligne` : libellé `--pan-libelle` 64 px, champs `--pan-champ-h` 28 px, `flex-wrap: wrap` sur le porte-champs ; `.px-pastille` 22 px, `.px-palette` gap 6 px | | `.vl-curseur` (piste 4 px, poignée 14 px, `flex: 1 1 60px`), `.vl-bascule` (34 × 18 px, `min-height` 28 px avec son libellé), `.vl-rangee` (`display:flex; gap: var(--pan-gap)`, enfants `flex: 1 1 0; min-width: 0`), `.px-palette` en `grid-template-columns: repeat(6, 22px)` gap 6 px |
| Hors périmètre (spec) | `mod-barrecontexte` (barre contextuelle, `checkbox` ×4), `mod-exportplus`, `mod-impression` (dialogue), `mod-trace`, `mod-vitrail`, `mod-plateau`, `mod-carte`, `mod-typo` | | inchangés — l'audit ne vise que `#panneauStyle`, `#panneauApparence2`, `#panneauPixel`, `#nuancier` |

Pièges connus : un `<details>` fermé a des rangées `display: none` (l'audit ne juge que les rangées VISIBLES : `offsetParent !== null` et `getClientRects().length`) ; les `<details>` sont DÉPLACÉS par `mod-pile` dans les groupes d'onglets (mesurer après `VL.ouvrirOnglet`) ; le volet caché ne tire pas rAF (les composants n'en dépendent pas : rendu synchrone).

---

### Task 1 : les purs de `mod-controles.js` + `auditer` (RED → GREEN)

**Files :** Create `frontend/vectorlab/js/mod-controles.js`, `frontend/vectorlab/qa/ergonomie.test.mjs`.

- [ ] **Step 1 : banc**

```js
// ergonomie.test.mjs — mod-controles : curseur (valeur ↔ position, pas),
// rangée à largeurs égales, et l'AUDIT d'ergonomie qui juge des mesures DOM
// (relevées in-page par VL.ergonomie.mesurer) : débordement, contrôles < 28 px,
// boutons inégaux, natifs interdits. Le DOM est mesuré dans la page ; ici on
// bance le jugement.
import { curseur_valeur, curseur_pas, curseur_position, rangee_largeurs, auditer } from "../js/mod-controles.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
{
  ok("valeur : milieu de piste = milieu d'échelle, bornée, arrondie au pas", curseur_valeur(50, 100, { min: 0, max: 100, step: 1 }) === 50 && curseur_valeur(-10, 100, { min: 0, max: 1, step: 0.05 }) === 0 && curseur_valeur(37, 100, { min: 0, max: 1, step: 0.05 }) === 0.35 && curseur_valeur(999, 100, { min: 1, max: 60, step: 1 }) === 60);
  ok("état vide : piste de largeur 0 → min", curseur_valeur(10, 0, { min: 2, max: 8, step: 1 }) === 2);
  ok("position : fraction de la valeur sur l'échelle, bornée", curseur_position(0.5, { min: 0, max: 1 }) === 0.5 && curseur_position(-5, { min: 0, max: 10 }) === 0 && curseur_position(3, { min: 3, max: 3 }) === 0);
  ok("pas : ±step, Maj ×10, borné, arrondi au pas", curseur_pas(0.5, +1, { min: 0, max: 1, step: 0.05 }) === 0.55 && curseur_pas(0.5, -1, { min: 0, max: 1, step: 0.05 }, true) === 0 && curseur_pas(99, +1, { min: 0, max: 100, step: 1 }, true) === 100 && curseur_pas(0.1 + 0.2, +1, { min: 0, max: 1, step: 0.1 }) === 0.4);
  ok("rangée : n largeurs égales à ±1 px qui remplissent la place", JSON.stringify(rangee_largeurs(3, 200, 8)) === JSON.stringify([62, 61, 61]) && rangee_largeurs(0, 200, 8).length === 0 && rangee_largeurs(1, 100, 8)[0] === 100);
  const mesures = [
    { id: "l1", panneau: "#panneauPixel", scrollWidth: 240, clientWidth: 240, controles: [{ tag: "vl-curseur", h: 28, w: 120 }], boutons: [] },
    { id: "l2", panneau: "#panneauPixel", scrollWidth: 262, clientWidth: 240, controles: [], boutons: [{ w: 90 }, { w: 40 }] },
    { id: "l3", panneau: "#panneauApparence2", scrollWidth: 240, clientWidth: 240, controles: [{ tag: "input", type: "range", h: 20, w: 100 }, { tag: "input", type: "checkbox", h: 13, w: 13 }], boutons: [{ w: 60 }, { w: 61 }, { w: 60 }] },
  ];
  const v = auditer(mesures);
  ok("audit : déborde (l2), boutons inégaux (l2), natif range + checkbox (l3), contrôle < 28 px (l3 ×2), l1 propre", v.length === 6 && v.filter((x) => x.ligne === "l1").length === 0 && v.some((x) => x.ligne === "l2" && x.type === "deborde") && v.some((x) => x.ligne === "l2" && x.type === "inegal") && v.filter((x) => x.ligne === "l3" && x.type === "natif").length === 2 && v.filter((x) => x.ligne === "l3" && x.type === "petit").length === 2, JSON.stringify(v));
  ok("audit : ±1 px de tolérance sur le débordement et les largeurs", auditer([{ id: "t", panneau: "p", scrollWidth: 241, clientWidth: 240, controles: [], boutons: [{ w: 50 }, { w: 51 }] }]).length === 0);
  ok("état vide : aucune mesure → aucune violation", auditer([]).length === 0 && auditer(null).length === 0);
}
if (echecs.length) { console.error("ECHECS ergonomie :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA ergonomie : PASS (8 controles)");
```

- [ ] **Step 2 : RED** — `node frontend/vectorlab/qa/ergonomie.test.mjs` → module absent.
- [ ] **Step 3 : les purs** (tête de `mod-controles.js`) :

```js
const _arrondi = (v, step) => { const d = Math.max(0, -Math.floor(Math.log10(step || 1))); return +(Math.round(v / step) * step).toFixed(d + 2); };
export function curseur_valeur(x, w, { min, max, step = 1 }) {
  if (!(w > 0)) return min;
  const f = Math.max(0, Math.min(1, x / w));
  return Math.max(min, Math.min(max, _arrondi(min + f * (max - min), step)));
}
export function curseur_position(v, { min, max }) { if (!(max > min)) return 0; return Math.max(0, Math.min(1, (v - min) / (max - min))); }
export function curseur_pas(v, sens, { min, max, step = 1 }, maj = false) {
  return Math.max(min, Math.min(max, _arrondi(v + sens * step * (maj ? 10 : 1), step)));
}
export function rangee_largeurs(n, total, gap) {
  if (!(n > 0)) return [];
  const libre = total - gap * (n - 1), base = Math.floor(libre / n); let reste = libre - base * n;
  return Array.from({ length: n }, () => base + (reste-- > 0 ? 1 : 0));
}
export function auditer(mesures) {
  const v = [];
  for (const m of mesures || []) {
    if (m.scrollWidth > m.clientWidth + 1) v.push({ ligne: m.id, panneau: m.panneau, type: "deborde", detail: `${m.scrollWidth} > ${m.clientWidth}` });
    for (const c of m.controles || []) {
      if (c.tag === "input" && (c.type === "range" || c.type === "checkbox")) v.push({ ligne: m.id, panneau: m.panneau, type: "natif", detail: c.type });
      if (c.h < 28) v.push({ ligne: m.id, panneau: m.panneau, type: "petit", detail: `${c.tag} ${c.h}px` });
    }
    const ws = (m.boutons || []).map((b) => b.w);
    if (ws.length > 1 && Math.max(...ws) - Math.min(...ws) > 1) v.push({ ligne: m.id, panneau: m.panneau, type: "inegal", detail: ws.join("/") });
  }
  return v;
}
```
  (le contrôle `0.1 + 0.2 → 0.4` impose l'arrondi par `toFixed`.)
- [ ] **Step 4 : GREEN** puis commit `--only` : `vectorlab : mod-controles — purs du curseur, rangée égale, audit d'ergonomie`.

### Task 2 : les éléments `<vl-curseur>`, `<vl-curseur-couleur>`, `<vl-bascule>`, `.vl-rangee`, `VL.ergonomie`

**Files :** Modify `mod-controles.js` (partie DOM), `vectorlab.css`, `core.js` (import + `initControles(VL)` avant les panneaux).

- [ ] **Step 1 : DOM** — dans `mod-controles.js` :

```js
export function initControles(VL) {
  if (typeof customElements === "undefined" || customElements.get("vl-curseur")) return;
  const num = (el, a, d) => { const v = parseFloat(el.getAttribute(a)); return Number.isFinite(v) ? v : d; };
  class VlCurseur extends HTMLElement {
    static get observedAttributes() { return ["value", "min", "max", "step", "disabled"]; }
    connectedCallback() {
      if (this._pret) { this._peindre(); return; }
      this._pret = true; this.tabIndex = this.hasAttribute("disabled") ? -1 : 0;
      this.setAttribute("role", "slider");
      this.innerHTML = `<span class="vl-curseur-piste"><span class="vl-curseur-plein"></span><span class="vl-curseur-poignee"></span></span><input class="vl-curseur-val" type="text" inputmode="decimal" aria-label="valeur">`;
      this._val = this.querySelector(".vl-curseur-val");
      const piste = this.querySelector(".vl-curseur-piste");
      const poser = (ev, fin) => { const r = piste.getBoundingClientRect(); const v = curseur_valeur(ev.clientX - r.left, r.width, this._echelle()); this._poser(v, fin); };
      piste.addEventListener("pointerdown", (ev) => { if (this.hasAttribute("disabled")) return; ev.preventDefault(); this.focus(); piste.setPointerCapture(ev.pointerId); this._glisse = true; poser(ev, false); });
      piste.addEventListener("pointermove", (ev) => { if (this._glisse) poser(ev, false); });
      piste.addEventListener("pointerup", (ev) => { if (!this._glisse) return; this._glisse = false; poser(ev, true); });
      this.addEventListener("keydown", (ev) => {
        const s = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[ev.key];
        if (s && ev.target !== this._val) { ev.preventDefault(); this._poser(curseur_pas(this.value, s, this._echelle(), ev.shiftKey), true); }
      });
      this.addEventListener("wheel", (ev) => { if (ev.target === this._val) return; ev.preventDefault(); this._poser(curseur_pas(this.value, ev.deltaY < 0 ? 1 : -1, this._echelle(), ev.shiftKey), true); }, { passive: false });
      this._val.addEventListener("change", () => { const v = parseFloat(String(this._val.value).replace(",", ".")); if (Number.isFinite(v)) this._poser(curseur_pas(v, 0, this._echelle()), true); else this._peindre(); });
      this._val.addEventListener("keydown", (ev) => ev.stopPropagation());
      this._peindre();
    }
    attributeChangedCallback() { if (this._pret && !this._glisse) this._peindre(); }
    _echelle() { return { min: num(this, "min", 0), max: num(this, "max", 100), step: num(this, "step", 1) }; }
    get value() { return num(this, "value", this._echelle().min); }
    set value(v) { this.setAttribute("value", String(v)); }
    _poser(v, fin) {
      const avant = this.value; this.setAttribute("value", String(v)); this._peindre();
      if (v !== avant || fin) this.dispatchEvent(new Event("input", { bubbles: true }));
      if (fin) this.dispatchEvent(new Event("change", { bubbles: true }));
    }
    _peindre() {
      if (!this._val) return;
      const e = this._echelle(), f = curseur_position(this.value, e);
      this.style.setProperty("--vl-f", String(f));
      this.setAttribute("aria-valuemin", e.min); this.setAttribute("aria-valuemax", e.max); this.setAttribute("aria-valuenow", this.value);
      if (document.activeElement !== this._val) this._val.value = String(this.value);
    }
  }
  class VlCurseurCouleur extends HTMLElement {
    // mode="teinte" : piste = roue des teintes, value = 0..359 ; sinon : piste = dégradé
    // noir → couleur → blanc, value = "#RRGGBB", double-clic = <input type=color> natif.
    connectedCallback() {
      if (this._pret) return; this._pret = true;
      const teinte = this.getAttribute("mode") === "teinte";
      this.innerHTML = teinte
        ? `<span class="vl-curseur-piste vl-teintes"><span class="vl-curseur-poignee"></span></span>`
        : `<span class="vl-couleur-pastille" title="Double-clic : sélecteur système"></span><input type="color" class="vl-couleur-natif" tabindex="-1" aria-hidden="true">`;
      if (teinte) {
        const piste = this.querySelector(".vl-curseur-piste");
        const poser = (ev, fin) => { const r = piste.getBoundingClientRect(); this._poser(curseur_valeur(ev.clientX - r.left, r.width, { min: 0, max: 359, step: 1 }), fin); };
        piste.addEventListener("pointerdown", (ev) => { ev.preventDefault(); piste.setPointerCapture(ev.pointerId); this._glisse = true; poser(ev, false); });
        piste.addEventListener("pointermove", (ev) => { if (this._glisse) poser(ev, false); });
        piste.addEventListener("pointerup", (ev) => { if (!this._glisse) return; this._glisse = false; poser(ev, true); });
      } else {
        const natif = this.querySelector(".vl-couleur-natif");
        natif.value = /^#[0-9a-f]{6}$/i.test(this.getAttribute("value") || "") ? this.getAttribute("value") : "#000000";
        this.querySelector(".vl-couleur-pastille").addEventListener("dblclick", () => natif.click());
        this.querySelector(".vl-couleur-pastille").addEventListener("click", (ev) => { if (VL.ouvrirNuancier) VL.ouvrirNuancier(this.value, (hex) => this._poser(hex, true), ev.currentTarget); });
        natif.addEventListener("input", () => this._poser(natif.value, false));
        natif.addEventListener("change", () => this._poser(natif.value, true));
      }
      this._peindre();
    }
    static get observedAttributes() { return ["value", "class"]; }
    attributeChangedCallback() { if (this._pret) this._peindre(); }
    get value() { const v = this.getAttribute("value"); return this.getAttribute("mode") === "teinte" ? (parseFloat(v) || 0) : (v || "#000000"); }
    set value(v) { this.setAttribute("value", String(v)); }
    _poser(v, fin) { this.setAttribute("value", String(v)); this._peindre(); this.dispatchEvent(new Event("input", { bubbles: true })); if (fin) this.dispatchEvent(new Event("change", { bubbles: true })); }
    _peindre() {
      if (this.getAttribute("mode") === "teinte") { this.style.setProperty("--vl-f", String(curseur_position(this.value, { min: 0, max: 359 }))); this.style.setProperty("--vl-couleur", `hsl(${this.value} 100% 50%)`); }
      else { this.style.setProperty("--vl-couleur", this.classList.contains("vide") ? "transparent" : this.value); const n = this.querySelector(".vl-couleur-natif"); if (n && /^#[0-9a-f]{6}$/i.test(this.value)) n.value = this.value; }
    }
  }
  class VlBascule extends HTMLElement {
    connectedCallback() {
      if (this._pret) return; this._pret = true;
      this.setAttribute("role", "switch"); this.tabIndex = 0;
      this.innerHTML = `<span class="vl-bascule-piste"><span class="vl-bascule-bouton"></span></span>`;
      this.addEventListener("click", () => { if (!this.hasAttribute("disabled")) this._basculer(); });
      this.addEventListener("keydown", (ev) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); this._basculer(); } });
      this._peindre();
    }
    static get observedAttributes() { return ["checked"]; }
    attributeChangedCallback() { if (this._pret) this._peindre(); }
    get checked() { return this.hasAttribute("checked"); }
    set checked(v) { if (v) this.setAttribute("checked", ""); else this.removeAttribute("checked"); }
    _basculer() { this.checked = !this.checked; this.dispatchEvent(new Event("input", { bubbles: true })); this.dispatchEvent(new Event("change", { bubbles: true })); }
    _peindre() { this.setAttribute("aria-checked", String(this.checked)); }
  }
  customElements.define("vl-curseur", VlCurseur);
  customElements.define("vl-curseur-couleur", VlCurseurCouleur);
  customElements.define("vl-bascule", VlBascule);

  // l'audit in-page : mesure les rangées VISIBLES des panneaux visés, auditer() juge
  const PANNEAUX = ["#panneauStyle", "#panneauApparence2", "#panneauPixel", "#nuancier"];
  function mesurer(racines = PANNEAUX) {
    const out = [];
    for (const sel of racines) {
      const p = document.querySelector(sel); if (!p) continue;
      const lignes = [...p.querySelectorAll(".ap-ligne, .vl-rangee, .nu-ligne")].filter((l) => l.getClientRects().length && l.offsetParent !== null);
      lignes.forEach((l, i) => {
        const el = [...l.querySelectorAll("input, select, button, vl-curseur, vl-bascule, vl-curseur-couleur")].filter((c) => c.getClientRects().length && !c.closest("vl-curseur, vl-curseur-couleur, vl-bascule") || c.matches("vl-curseur, vl-bascule, vl-curseur-couleur"));
        const controles = el.filter((c) => !c.classList.contains("px-pastille")).map((c) => ({ tag: c.tagName.toLowerCase(), type: c.getAttribute("type") || "", h: c.getBoundingClientRect().height, w: c.getBoundingClientRect().width }));
        const boutons = l.matches(".vl-rangee") ? [...l.children].map((b) => ({ w: b.getBoundingClientRect().width })) : [];
        out.push({ id: `${sel} #${i}${l.id ? " " + l.id : ""}`, panneau: sel, scrollWidth: l.scrollWidth, clientWidth: l.clientWidth, controles, boutons });
      });
    }
    return out;
  }
  VL.ergonomie = { mesurer, auditer: (racines) => auditer(mesurer(racines)), PANNEAUX };
}
```

- [ ] **Step 2 : CSS** (fin de `vectorlab.css`, jetons seulement — `#4a90e2` du focus existant est repris par `--pan-bord-focus`) :

```css
/* ── finitions UI (20/09) : contrôles maison — curseur, curseur de couleur, bascule, rangée égale ── */
vl-curseur { display: inline-flex; align-items: center; gap: 8px; flex: 1 1 60px; min-width: 0; height: var(--pan-champ-h); --vl-f: 0; outline: none; }
vl-curseur[disabled] { opacity: .5; pointer-events: none; }
.vl-curseur-piste { position: relative; flex: 1 1 auto; height: var(--pan-champ-h); cursor: pointer; touch-action: none; }
.vl-curseur-piste::before { content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 4px; margin-top: -2px; border-radius: 2px; background: var(--aff-bord); }
.vl-curseur-plein { position: absolute; left: 0; top: 50%; height: 4px; margin-top: -2px; border-radius: 2px; width: calc(var(--vl-f) * 100%); background: var(--aff-sel); }
.vl-curseur-poignee { position: absolute; top: 50%; left: calc(var(--vl-f) * 100%); width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%; background: var(--aff-texte); border: 2px solid var(--aff-fond); box-shadow: 0 0 0 1px var(--aff-bord); }
vl-curseur:focus-visible .vl-curseur-poignee { box-shadow: 0 0 0 2px var(--pan-bord-focus); }
#panneauCalques .ap-ligne vl-curseur .vl-curseur-val, vl-curseur .vl-curseur-val { flex: 0 0 44px; width: 44px; height: var(--pan-champ-h); text-align: center; font-variant-numeric: tabular-nums; background: var(--pan-fond); color: var(--pan-texte); border: 1px solid var(--pan-bord); border-radius: 6px; font-size: 12px; padding: 0 4px; }
vl-curseur-couleur { display: inline-flex; align-items: center; height: var(--pan-champ-h); --vl-couleur: transparent; --vl-f: 0; flex: 0 0 auto; }
vl-curseur-couleur[mode="teinte"] { flex: 1 1 60px; width: 100%; }
.vl-teintes { flex: 1 1 auto; height: var(--pan-champ-h); position: relative; cursor: pointer; touch-action: none; }
.vl-teintes::before { content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 10px; margin-top: -5px; border-radius: 5px; background: linear-gradient(to right, hsl(0 100% 50%), hsl(60 100% 50%), hsl(120 100% 50%), hsl(180 100% 50%), hsl(240 100% 50%), hsl(300 100% 50%), hsl(360 100% 50%)); }
.vl-teintes .vl-curseur-poignee { background: var(--vl-couleur); }
.vl-couleur-pastille { display: inline-block; width: var(--pan-champ-h); height: var(--pan-champ-h); border-radius: 6px; border: 1px solid var(--pan-bord); background: var(--vl-couleur); cursor: pointer; box-shadow: inset 0 0 0 1px rgba(255,255,255,.08); }
vl-curseur-couleur.vide .vl-couleur-pastille { background: repeating-conic-gradient(var(--aff-bord) 0 25%, var(--aff-champ) 0 50%) 0 0 / 8px 8px; }
.vl-couleur-natif { position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none; }
vl-bascule { display: inline-flex; align-items: center; height: var(--pan-champ-h); cursor: pointer; outline: none; flex: 0 0 auto; }
.vl-bascule-piste { position: relative; width: 34px; height: 18px; border-radius: 9px; background: var(--aff-bord); transition: background .12s; }
.vl-bascule-bouton { position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: var(--aff-texte); transition: left .12s; }
vl-bascule[checked] .vl-bascule-piste { background: var(--aff-sel); }
vl-bascule[checked] .vl-bascule-bouton { left: 18px; }
vl-bascule:focus-visible .vl-bascule-piste { box-shadow: 0 0 0 2px var(--pan-bord-focus); }
vl-bascule[disabled] { opacity: .5; pointer-events: none; }
#panneauCalques .ap-ligne > label:has(vl-bascule) { gap: 8px; }
.vl-rangee { display: flex; gap: var(--pan-gap); min-height: var(--pan-champ-h); }
#panneauCalques .vl-rangee > button { flex: 1 1 0; min-width: 0; max-width: none; height: var(--pan-champ-h); padding: 0 6px; border-radius: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#panneauCalques .px-palette { display: grid; grid-template-columns: repeat(6, 22px); gap: 6px; justify-content: start; }
```

- [ ] **Step 3 :** `core.js` : `import { initControles } from "./mod-controles.js";` + `initControles(VL);` juste après `initDialogue(VL)` (avant tout rendu de panneau).
- [ ] **Step 4 :** `node --check`, `run.mjs` vert (theme.test inclus), commit `--only` : `vectorlab : <vl-curseur>, <vl-curseur-couleur>, <vl-bascule>, .vl-rangee et VL.ergonomie (audit in-page)`.

### Task 3 : les gabarits — pixelui, apparence2, style, couleur

- [ ] **Step 1 : mod-pixelui** — remplacer dans `rendrePanneau` :
  - `<input type="range" id="pxDurete" min="0" max="1" step="0.05" value="${p.durete}" title="…"/>` → `<vl-curseur id="pxDurete" min="0" max="1" step="0.05" value="${p.durete}" title="…"></vl-curseur>` ;
  - chaque `<input type="checkbox" id="X"${cond ? " checked" : ""}/>` → `<vl-bascule id="X"${cond ? " checked" : ""}></vl-bascule>` (10 cas ; `pxTuileArtOn` sans condition) ;
  - `<input type="color" id="pxCouleur" value="${p.couleur}"/>` → `<vl-curseur-couleur id="pxCouleur" value="${p.couleur}"></vl-curseur-couleur>` ; `pxSecondaire` idem avec `${p.secondaire ? "" : ' class="vide"'}` ;
  - `num("pxRayon", …)` → `<vl-curseur id="pxRayon" min="0.5" max="64" step="0.5" value="${p.rayon}" title="…"></vl-curseur>` ; `pxTol` → `vl-curseur 0–255 step 1` ; `pxFps` → `1–60` ; `pxContourE` → `1–4` ; `pxAccF` → `0.1–2 step 0.1` ; `pxFlouR` → `1–50` ;
  - rangées de boutons → `.vl-rangee` : Sélection (`pxMasqueCalque` / `pxVersVecteur`), Palette (`pxPalExtraire` / `pxQuantifier` — le champ N reste dans une `.ap-ligne` au-dessus : « Palette · N »), Pixeliser (`pxPixeliser` / `pxPixeliserVec`), cadres (`pxCadreNouveau` / `pxCadreVide` / `pxCadreSuppr`), envois (`pxTilelab` / `pxSpritelab`) — `<div class="vl-rangee">` à la place de `<div class="ap-ligne">` quand la rangée ne porte QUE des boutons ; « Tuile W × H OK » : les deux champs gardent `num`, le bouton OK passe en fin ; le libellé de `pxPalExtraire` / `pxQuantifier` : « Extraire » / « Quantifier ».
  Les écouteurs restent (`val(id)` lit `.value` ; `ev.target.checked` lit `checked` ; `$("#pxSymH").checked` idem).
- [ ] **Step 2 : mod-apparence2** — `a2Decalage` → `<vl-curseur … ></vl-curseur>` ; la rangée Remplissage → `<div class="vl-rangee"><button id="a2Conique" …>Conique</button><button id="a2Transp" …>Transparence</button><button id="a2MasqueX" …>✕ masque</button></div>`.
- [ ] **Step 3 : mod-style** — `apOpacite` → `<vl-curseur id="apOpacite" min="0" max="100" step="1" value="…"></vl-curseur>` et retirer `<b id="apOpaciteVal">` (le composant affiche la valeur) ; l'écouteur `input` qui posait `apOpaciteVal` devient inutile : le supprimer (le `change` reste).
- [ ] **Step 4 : mod-couleur** — `nuH` → `<vl-curseur-couleur id="nuH" mode="teinte" value="0" title="Teinte"></vl-curseur-couleur>` ; `synchroniser()` posait `$("#nuH").value = h` : inchangé (setter) ; CSS `#nuH` (lignes 199-207, `-webkit-slider-thumb`) devient caduque : la retirer.
- [ ] **Step 5 :** `grep -n -E 'type="?(range|checkbox)' mod-pixelui.js mod-apparence2.js mod-style.js mod-couleur.js` → 0 ; `node --check` ×4 ; `run.mjs` vert (les bancs `pixel_ui`, `apparence2_ui`, `couleur` parsent-ils le HTML rendu ? les relire si rouges et adapter leurs attentes AVEC le nouveau gabarit) ; commit `--only` : `vectorlab : panneaux Pixel / Apparence + / Apparence / nuancier sur les contrôles maison`.

### Task 4 : preuve (8799, 1400 × 900, trois personas)

- [ ] **Step 1 :** document de preuve avec un rectangle et une image (POST `/api/vector/docs` + `/images`), ouvrir, `onerror` capturé.
- [ ] **Step 2 :** persona Vecteur, rectangle sélectionné, onglets Apparence / Apparence + ouverts (`VL.ouvrirOnglet`) : `VL.ergonomie.auditer()` → `[]` ; mesurer une rangée `.vl-rangee` (trois largeurs à ± 1 px) ; glisser RÉEL sur le curseur Opacité (`PointerEvent` pointerdown/move/up sur `.vl-curseur-piste` de `#apOpacite`) → `style.opacite` du rectangle change ; molette → ± 1 ; Maj + flèche → ± 10.
- [ ] **Step 3 :** persona Pixel, image sélectionnée, « Éditer les pixels » : `auditer()` → `[]` sur `#panneauPixel` (sections Ajustements / Pixel-art ouvertes) ; clic sur la bascule `pxGrille` → `etat.px.grille` bascule ; glisser sur `pxDurete` → `etat.px.durete` ; `pxCouleur` clic → nuancier, glisser sur la teinte `nuH` → `#nuHex` change ; `nuH.value` suit.
- [ ] **Step 4 :** persona Export (troisième persona) : `auditer()` → `[]` (les panneaux visés n'y sont pas visibles ; l'audit rend 0 mesure, on le note) ; `qa/ergonomie.test.mjs` vert ; capture de la rangée Remplissage et du panneau Pixel-art (avant / après par `screenshot`).
- [ ] **Step 5 :** `taskkill` 8799 ; relevé.

### Task 5 : déploiement (statiques), mémoire, push

- [ ] table `git hash-object` installé / base `5b82c7a` / cible ; sauvegarde `_backup_predeploy_2026-09-20-panneaux` ; copie ; re-table ; aucune relance (statiques) ; relevé en tête du plan ; mémoire ; push.
