# Vectorlab relooking Affinity — R2 colonne d'outils — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `…-relooking-design.md` (R-D6 familles, R-D1 icônes fines, R-D9).

> **RELEVÉ DE LIVRAISON (18/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ (statiques seuls : aucune relance).**
>
> **Livré** (commits `ccd4d1c`, `3ba2203`, poussés) : `mod-icones.js`
> (32 icônes trait 1,5 / currentColor / viewBox 24, repli pointillé, RED
> constaté, 6 contrôles) ; `mod-familles.js` (17 familles — 13 Vecteur, 6
> Pixel, Déplacer et Tranche partagées —, `famille_de / famille_par_id /
> membre_courant / choisir_membre / flyout_famille / touche_de`, 10
> contrôles) ; `mod-flyout.js` gagne `ouvrirMenu(bouton, menu)` et
> `armer` exposés, le triangle / l'appui long passent d'abord par
> `VL.familleOuvrir` (une famille d'un membre rend false → menu de
> réglages), le clic droit garde le menu de réglages ; `mod-barreoutils.js`
> réordonne les boutons EXISTANTS de `#outils` (ids, `data-outil`,
> écouteurs intacts), replie les membres non courants (`outil-repli`),
> pose les icônes et le raccourci dans la bulle, mémorise `dz_vl_familles`,
> chaîne `surOutil` (un raccourci bascule la famille) et enveloppe
> `VL.flyout.ouvrir` (montre le membre avant d'ouvrir) ; `index.html` sans
> `<use>` dans les boutons ; CSS R2 (colonne 44, boutons 30 × 30, pas 36,
> actif = carré #3c3c3c, triangle d'angle).
>
> **TDD** : node tous bancs verts (icones 6, familles 10 — premier RED
> réel : l'ordre des familles Pixel plaçait Tranche avant la Sélection, et
> `famille_de("formes")` cherchait un OUTIL nommé formes → `famille_par_id`
> ajouté).
>
> **Prouvé en réel** (8799, 1400 × 900) : `#outils` 44 px ; 13 boutons
> visibles en Vecteur (select, noeuds, plume, rect, constructeur, texte,
> image, apparence, symbole, mesure, tuiles, ia, tranche), 6 en Pixel
> (select, px-selrect, px-pinceau, px-seau, px-crayon, tranche) ; tous 30 ×
> 30 avec une icône de 18 ; `setOutil("crayon")` → plume repliée, crayon
> visible et actif ; touche « e » → ellipse visible, rect replié ;
> `VL.familleOuvrir(ellipse)` → flyout à 43 px du bord avec 4 entrées
> « Outil Rectangle R · Outil Ellipse E · Outil Ligne L · Outil Forme
> paramétrique F » ; clic « Outil Ligne » → outil ligne, bouton visible,
> mémoire `{"plume":"crayon","formes":"ligne"}` ; clic droit sur gomme →
> « Gomme vectorielle » (réglages) ; `VL.flyout.ouvrir("forme")` → forme
> montrée puis menu « Forme paramétrique » ; audit : 0 bouton tronqué,
> scrollWidth 44 / clientWidth 43 (bordure).
>
> **Déployé** : installé = base R1 `fbada07` (124, 0 divergent) →
> sauvegarde `_backup_predeploy_2026-09-18-relooking-r2` → `git archive
> HEAD` → 129/129 = cible. Aucun Python touché.
>
> **Reste** : le bouton d'une famille repliée n'est pas atteignable au
> clic droit (cas synthétique seulement) ; les bulles des outils gardent
> le `title` natif stylé par mod-infobulle (bulle riche titre + gestes :
> R6) ; le sprite `<symbol>` de tête d'`index.html` est désormais inutilisé.

**Goal :** la colonne d'outils ressemble à celle d'Affinity — boutons
carrés 30 px au pas de 36, icônes fines monochromes (traits 1,5 px), un
bouton par FAMILLE montrant le membre courant, petit triangle d'angle,
flyout VERTICAL « Outil X · R » par appui long / clic sur le triangle,
clic droit = menu de réglages existant ; un raccourci clavier bascule la
famille sur le membre choisi.

**Architecture :** deux feuilles bancables (`mod-icones.js` : sprite
d'icônes trait, une par outil ; `mod-familles.js` : familles par persona,
membre courant, entrées de flyout) ; un module UI `mod-barreoutils.js`
qui RÉORDONNE les boutons existants de `#outils` (ils gardent leurs ids,
`data-outil` et écouteurs), ne montre que le membre courant de chaque
famille, pose les icônes et branche l'appui long / le triangle sur un
flyout de famille rendu par `mod-flyout` (`VL.flyout.ouvrirMenu`) ; le clic
droit garde le menu de réglages.

**Tech :** vanilla ESM, CSS, `node qa/run.mjs`.

---

### Task 1 : `mod-icones.js`

**Files :** Create `frontend/vectorlab/js/mod-icones.js`, Test `frontend/vectorlab/qa/icones.test.mjs`.

- [ ] **Step 1 : banc RED**

```js
// icones.test.mjs — mod-icones : le sprite d'icônes fines (trait 1,5,
// viewBox 24, monochrome currentColor) — une icône par outil des deux
// personas, un repli générique pour l'inconnu. Feuille.
import { ICONES, icone_svg, outils_sans_icone } from "../js/mod-icones.js";
import { FAMILLES } from "../js/mod-familles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const tous = FAMILLES.flatMap((f) => f.membres.map((m) => m.outil));
  ok("une icône par outil de toutes les familles", outils_sans_icone(tous).length === 0, outils_sans_icone(tous).join(","));
  const s = icone_svg("rect");
  ok("svg : viewBox 24, trait currentColor 1.5, sans remplissage, classe ic", s.startsWith('<svg class="ic" viewBox="0 0 24 24"') && s.includes('stroke="currentColor"') && s.includes('stroke-width="1.5"') && s.includes('fill="none"'), s);
  ok("taille : width/height posés", icone_svg("rect", 18).includes('width="18" height="18"'));
  ok("inconnu : le repli (un carré pointillé) et pas une exception", icone_svg("zz").includes("stroke-dasharray") && outils_sans_icone(["zz", "rect"]).join() === "zz");
  ok("état vide : liste vide → aucun manquant", outils_sans_icone([]).length === 0 && outils_sans_icone(undefined).length === 0);
  ok("chaque icône est un fragment SVG non vide sans script", Object.values(ICONES).every((v) => typeof v === "string" && v.length > 10 && !/script|on\w+=/i.test(v)));
}
if (echecs.length) { console.error("ECHECS icones :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA icones : PASS (6 controles)");
```

- [ ] **Step 2 : RED** — `node qa/icones.test.mjs` → module introuvable.
- [ ] **Step 3 : le module** — `ICONES` = objet outil → fragment (`<path d=…/>`, `<circle/>`, `<rect/>`…) SANS attributs de style (le `<svg>` porte `fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"`) ; entrées : select, plume, crayon, pinceauv, rect, ellipse, ligne, forme, noeuds, coin, mesure, pipette, texte, couteau, gomme, constructeur, tuiles, ia, image, apparence, symbole, tranche, px-pinceau, px-gomme, px-seau, px-crayon, px-ligne, px-rectpx, px-selrect, px-lasso, px-baguette, px-cloner. `icone_svg(id, taille = 18)` ; `outils_sans_icone(liste)`.
- [ ] **Step 4 : vert**, **Step 5 : commit** `--only` module + test.

### Task 2 : `mod-familles.js`

**Files :** Create `frontend/vectorlab/js/mod-familles.js`, Test `frontend/vectorlab/qa/familles.test.mjs`.

- [ ] **Step 1 : banc RED**

```js
// familles.test.mjs — mod-familles : les familles d'outils d'Affinity —
// par persona, membre courant, flyout vertical « Outil X · R », bascule
// par raccourci. Feuille.
import { FAMILLES, famille_de, familles_de, membre_courant, choisir_membre, flyout_famille, touche_de } from "../js/mod-familles.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  ok("Vecteur : 13 familles dans l'ordre, Pixel : 6", familles_de("vecteur").length === 13 && familles_de("pixel").length === 6 && familles_de("vecteur")[0].id === "deplacer" && familles_de("pixel")[1].id === "pxselection", familles_de("vecteur").map((f) => f.id).join(","));
  ok("Déplacer et Tranche sont dans les deux personas", familles_de("pixel").some((f) => f.id === "deplacer") && familles_de("pixel").some((f) => f.id === "tranche"));
  ok("famille_de : plume → plume (3 membres), px-lasso → pxselection, inconnu → null", famille_de("crayon").id === "plume" && famille_de("plume").membres.length === 3 && famille_de("px-lasso").id === "pxselection" && famille_de("zz") === null);
  ok("membres uniques dans toutes les familles", (() => { const t = FAMILLES.flatMap((f) => f.membres.map((m) => m.outil)); return new Set(t).size === t.length; })());
  const e0 = {};
  ok("membre courant : le premier par défaut", membre_courant(e0, "plume") === "plume" && membre_courant(e0, "formes") === "rect");
  const e1 = choisir_membre(e0, "crayon");
  ok("choisir : la famille du membre le retient, l'état d'origine intact", membre_courant(e1, "plume") === "crayon" && membre_courant(e0, "plume") === "plume");
  ok("choisir un outil inconnu : état inchangé", choisir_membre(e1, "zz") === e1);
  const fl = flyout_famille(famille_de("formes"), "ellipse");
  ok("flyout : « Outil X », raccourci en détail, le courant marqué, id = outil", fl.length === 4 && fl[0].libelle === "Outil Rectangle" && fl[0].detail === "R" && fl[1].actif === true && fl[1].id === "ellipse" && fl.filter((x) => x.actif).length === 1, JSON.stringify(fl));
  ok("état vide : famille null → []", flyout_famille(null, "x").length === 0);
  ok("touche_de : R pour rect, vide pour ia", touche_de("rect") === "R" && touche_de("ia") === "" && touche_de("zz") === "");
}
if (echecs.length) { console.error("ECHECS familles :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA familles : PASS (10 controles)");
```

- [ ] **Step 2 : RED**.
- [ ] **Step 3 : le module**

```js
// mod-familles.js — les familles d'outils d'Affinity (R-D6) : un bouton
// par famille montrant le membre courant, flyout vertical des membres.
// Feuille pure. `personas` : les personas où la famille est visible.
const m = (outil, nom, touche = "") => ({ outil, nom, touche });
export const FAMILLES = [
  { id: "deplacer", nom: "Déplacer", personas: ["vecteur", "pixel"], membres: [m("select", "Déplacer", "V")] },
  { id: "noeuds", nom: "Nœuds", personas: ["vecteur"], membres: [m("noeuds", "Nœud", "N"), m("coin", "Coin", "C")] },
  { id: "plume", nom: "Plume", personas: ["vecteur"], membres: [m("plume", "Plume", "P"), m("crayon", "Crayon", "B"), m("pinceauv", "Pinceau vectoriel", "J")] },
  { id: "formes", nom: "Formes", personas: ["vecteur"], membres: [m("rect", "Rectangle", "R"), m("ellipse", "Ellipse", "E"), m("ligne", "Ligne", "L"), m("forme", "Forme paramétrique", "F")] },
  { id: "constructeur", nom: "Constructeur", personas: ["vecteur"], membres: [m("constructeur", "Constructeur de formes", "S"), m("couteau", "Couteau", "X"), m("gomme", "Gomme vectorielle", "W")] },
  { id: "texte", nom: "Texte", personas: ["vecteur"], membres: [m("texte", "Texte", "T")] },
  { id: "image", nom: "Image", personas: ["vecteur"], membres: [m("image", "Image (menu)")] },
  { id: "apparence", nom: "Apparence", personas: ["vecteur"], membres: [m("apparence", "Apparence (menu)")] },
  { id: "symbole", nom: "Symboles", personas: ["vecteur"], membres: [m("symbole", "Symboles (menu)")] },
  { id: "mesure", nom: "Mesure", personas: ["vecteur"], membres: [m("mesure", "Mesure", "M"), m("pipette", "Pipette", "I")] },
  { id: "tuiles", nom: "Tuiles", personas: ["vecteur"], membres: [m("tuiles", "Pinceau de tuiles", "K")] },
  { id: "ia", nom: "IA", personas: ["vecteur"], membres: [m("ia", "Illustration IA")] },
  { id: "tranche", nom: "Tranche", personas: ["vecteur", "pixel"], membres: [m("tranche", "Tranche d'export")] },
  { id: "pxselection", nom: "Sélection de pixels", personas: ["pixel"], membres: [m("px-selrect", "Sélection rectangle", "M"), m("px-lasso", "Lasso", "L"), m("px-baguette", "Baguette magique", "W")] },
  { id: "pxpinceau", nom: "Pinceau", personas: ["pixel"], membres: [m("px-pinceau", "Pinceau", "B"), m("px-gomme", "Gomme", "E"), m("px-cloner", "Tampon de clonage", "C")] },
  { id: "pxseau", nom: "Seau", personas: ["pixel"], membres: [m("px-seau", "Pot de peinture", "G")] },
  { id: "pxart", nom: "Pixel-art", personas: ["pixel"], membres: [m("px-crayon", "Crayon pixel", "K"), m("px-ligne", "Ligne pixel", "I"), m("px-rectpx", "Rectangle pixel", "R")] },
];
export const familles_de = (persona) => FAMILLES.filter((f) => f.personas.includes(persona));
export const famille_de = (outil) => FAMILLES.find((f) => f.membres.some((x) => x.outil === outil)) || null;
export function membre_courant(etat, familleId) {
  const f = FAMILLES.find((x) => x.id === familleId);
  if (!f) return null;
  const v = etat && etat[familleId];
  return f.membres.some((x) => x.outil === v) ? v : f.membres[0].outil;
}
export function choisir_membre(etat, outil) {
  const f = famille_de(outil);
  if (!f) return etat;
  return { ...(etat || {}), [f.id]: outil };
}
export function flyout_famille(famille, courant) {
  if (!famille) return [];
  return famille.membres.map((x) => ({ id: x.outil, libelle: `Outil ${x.nom}`, detail: x.touche, actif: x.outil === courant }));
}
export function touche_de(outil) {
  for (const f of FAMILLES) { const x = f.membres.find((y) => y.outil === outil); if (x) return x.touche; }
  return "";
}
```

- [ ] **Step 4 : vert** ; **Step 5 : commit**.

### Task 3 : `mod-flyout.js` — `VL.flyout.ouvrirMenu(bouton, menu)` et l'appui long délégué

**Files :** Modify `frontend/vectorlab/js/mod-flyout.js` (`ouvrir`, `armer`, `VL.flyout`).

- [ ] **Step 1** : extraire de `ouvrir(bouton, nom)` un `ouvrirMenu(bouton, menu, cle)` (rendu + position + choix) ; `ouvrir` devient `ouvrirMenu(bouton, MENUS[nom](ctx), bouton)`. Dans `armer(b)` : le triangle / l'appui long appellent `VL.familleOuvrir ? VL.familleOuvrir(b) || ouvrir(b, b.dataset.menu) : ouvrir(b, b.dataset.menu)` (la famille d'abord ; une famille d'un seul membre rend `false` et le menu de réglages s'ouvre) ; le clic droit reste `ouvrir(b, b.dataset.menu)`. `armer` s'applique désormais à TOUS les boutons `#outils button[data-outil]` (ceux sans menu ont `data-menu` vide : le clic droit ne fait rien, l'appui long ouvre la famille). Exposer `VL.flyout.ouvrirMenu` et `VL.flyout.armer`.

### Task 4 : `mod-barreoutils.js` — réordonner, replier, iconifier

**Files :** Create `frontend/vectorlab/js/mod-barreoutils.js` ; Modify `frontend/vectorlab/js/core.js` (import + `initBarreOutils(VL)` juste après `initFlyout`), `frontend/vectorlab/index.html` (retirer les `<svg><use>` des boutons : le module pose les icônes), `frontend/vectorlab/vectorlab.css`.

```js
// mod-barreoutils.js — la colonne d'outils d'Affinity : les boutons
// existants de #outils sont réordonnés par famille, seul le membre
// courant est visible, l'icône fine remplace le glyphe, le triangle
// d'angle / l'appui long ouvrent le flyout vertical de la famille.
import { FAMILLES, famille_de, membre_courant, choisir_membre, flyout_famille, touche_de } from "./mod-familles.js";
import { icone_svg } from "./mod-icones.js";
export function initBarreOutils(VL) {
  const { $, etat } = VL;
  const nav = $("#outils");
  const bouton = (outil) => nav.querySelector(`button[data-outil="${outil}"]`);
  let familles = {};
  try { familles = JSON.parse(localStorage.getItem("dz_vl_familles") || "{}") || {}; } catch (e) { familles = {}; }
  // 1. réordonner : famille par famille, membre par membre ; les boutons inconnus des familles restent à la fin
  for (const f of FAMILLES) for (const x of f.membres) { const b = bouton(x.outil); if (b) { nav.appendChild(b); b.dataset.famille = f.id; if (f.membres.length > 1) b.classList.add("a-famille"); } }
  // 2. icônes + titres avec raccourci
  for (const b of nav.querySelectorAll("button[data-outil]")) {
    b.innerHTML = icone_svg(b.dataset.outil, 18);
    const t = touche_de(b.dataset.outil);
    if (t && !/\(\w\)$/.test(b.title)) b.title = `${b.title} (${t})`;
  }
  // 3. replier : seul le membre courant de chaque famille est visible
  function appliquer() {
    for (const f of FAMILLES) { const c = membre_courant(familles, f.id); for (const x of f.membres) { const b = bouton(x.outil); if (b) b.classList.toggle("outil-repli", x.outil !== c); } }
  }
  function montrer(outil) {
    if (!famille_de(outil)) return;
    familles = choisir_membre(familles, outil);
    try { localStorage.setItem("dz_vl_familles", JSON.stringify(familles)); } catch (e) { /* stockage indisponible */ }
    appliquer();
  }
  // 4. le flyout de famille (appui long / triangle) — rendu par mod-flyout
  VL.familleOuvrir = (b) => {
    const f = famille_de(b.dataset.outil);
    if (!f || f.membres.length < 2) return false;
    VL.flyout.ouvrirMenu(b, { titre: f.nom, entrees: flyout_famille(f, membre_courant(familles, f.id)), choisir: (e) => { montrer(e.id); VL.setOutil(e.id); } }, "famille:" + f.id);
    return true;
  };
  for (const b of nav.querySelectorAll("button[data-outil]")) VL.flyout.armer(b);
  // 5. un raccourci ou un module qui choisit un membre replié : la famille bascule
  const sOutil = VL.surOutil;
  VL.surOutil = () => { sOutil(); montrer(etat.outil); };
  // VL.flyout.ouvrir(nom) doit trouver un bouton VISIBLE : montrer d'abord
  const oOuvrir = VL.flyout.ouvrir;
  VL.flyout.ouvrir = (nom) => { montrer(nom); return oOuvrir(nom); };
  appliquer();
  VL.familles = { etat: () => familles, montrer, bouton };   // la preuve
}
```

CSS (fin de `vectorlab.css`) :
```css
/* ══ R2 colonne d'outils Affinity ══ */
.outils { width: 44px; flex: 0 0 44px; gap: 6px; padding: 8px 7px; background: var(--aff-fond); border-right: 1px solid var(--aff-bord); overflow-y: auto; scrollbar-width: none; }
.outils button { width: 30px; height: 30px; border-radius: 4px; border: 0; background: transparent; color: #c8c8c8; padding: 0; font-size: 0; }
.outils button:hover { background: #3a3a3a; color: #fff; }
.outils button.actif { background: #3c3c3c; color: #fff; box-shadow: none; }
.outils button .ic { width: 18px; height: 18px; display: block; margin: auto; }
.outils button.outil-repli { display: none !important; }
.outils button.a-famille::after, .outils button.a-menu::after { content: ""; position: absolute; right: 2px; bottom: 2px; border: 3px solid transparent; border-right-color: #8a8a8a; border-bottom-color: #8a8a8a; }
.outils button.a-famille, .outils button.a-menu { position: relative; }
.fo-item .fo-lib { flex: 1; } .fo-item small { min-width: 14px; text-align: right; }
```
Les règles de persona existantes (`body.persona-pixel #outils button…`) restent : elles cachent par persona, `outil-repli` cache par famille.

- [ ] **Étapes** : écrire le module, brancher dans `core.js` (après `initFlyout`), retirer les `<svg><use>` d'`index.html` (le sprite `<symbol>` de tête peut rester, les `use` disparaissent), `node --check`, banc complet vert, commit.

### Task 5 : preuve, déploiement, relevé

- [ ] 8799, 1400 × 900, document : `.outils` largeur 44 ; boutons visibles en Vecteur = 13 (un par famille), en Pixel = 6 ; chaque bouton visible 30 × 30 avec un `.ic` de 18 ; `VL.setOutil("crayon")` → le bouton `plume` se replie, `crayon` visible et `.actif` ; touche « e » (KeyboardEvent sur document) → `ellipse` visible, `rect` replié ; `VL.familleOuvrir(bouton("ellipse"))` → `#flyout` visible avec 4 `.fo-item` dont « Outil Rectangle » et le détail « R », cliquer « Outil Ligne » → outil `ligne`, bouton visible ; rechargement → la famille Formes montre encore `ligne` (localStorage) ; clic droit sur `gomme` → menu de réglages (« Gomme vectorielle ») ; `VL.flyout.ouvrir("forme")` → bouton forme visible et menu Forme paramétrique ouvert ; audit : aucun bouton tronqué (offsetWidth 30), colonne sans débordement horizontal.
- [ ] taskkill 8799 ; déploiement hash-object ; relevé ; mémoire ; push.
