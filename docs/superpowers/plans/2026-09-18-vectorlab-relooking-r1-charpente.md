# Vectorlab relooking Affinity — R1 charpente — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `docs/superpowers/specs/2026-09-18-vectorlab-affinity-relooking-design.md` (R-D1 à R-D4, R-D9).

**Goal :** le Vectorlab s'ouvre dans la charpente d'Affinity — barre de
menus fonctionnelle, pastilles Vecteur / Pixel, barre contextuelle
(squelette), onglet de document, barre d'état avec phrase d'aide — sans
changer une seule capacité ; le persona Export devient l'onglet Exporter.

**Architecture :** deux modules feuilles bancables (`mod-menus.js` : arbre
des menus et disponibilité ; `mod-statut.js` : phrase d'aide, onglet de
document, pagination) ; `index.html` réorganisé en six bandes en gardant
tous les ids ; `mod-persona.js` réduit à deux personas ; une couche CSS
« charpente » en fin de `vectorlab.css`.

**Tech :** vanilla ESM, CSS, banc `node qa/run.mjs`, pytest `test_vector_docs.py` (aucun champ nouveau dans ce lot : le miroir n'est pas touché).

---

### Task 1 : `mod-statut.js` (phrase d'aide, onglet de document, pagination)

**Files :** Create `frontend/vectorlab/js/mod-statut.js`, Test `frontend/vectorlab/qa/statut.test.mjs`.

- [ ] **Step 1 : le banc RED**

```js
// statut.test.mjs — mod-statut : la barre d'état d'Affinity — phrase d'aide
// aux verbes en gras selon l'outil et la sélection, onglet de document
// « nom @ 73%* », pagination « 1 sur N ». Feuille.
import { phrase_statut, statut_html, onglet_document, pagination } from "../js/mod-statut.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  const p0 = phrase_statut("select", 0, {});
  ok("sélection sans objet : cadre / cliquer / clic droit", p0.startsWith("**Glisser** pour utiliser un cadre de sélection") && p0.includes("**Cliquer** sur un objet"), p0);
  const p1 = phrase_statut("select", 2, {});
  ok("sélection avec 2 objets : « 2 objets sélectionnés » puis déplacer", p1.startsWith("2 objets sélectionnés.") && p1.includes("**Glisser** pour déplacer"), p1);
  ok("un seul objet : singulier", phrase_statut("select", 1, {}).startsWith("1 objet sélectionné."));
  ok("autre outil : la phrase de l'outil (les HINTS existants), verbes gras posés sur les infinitifs connus", phrase_statut("rect", 0, { rect: "glisser pour tracer · Maj contraint au carré" }) === "**Glisser** pour tracer · **Maj** contraint au carré");
  ok("état vide : outil inconnu sans hint → chaîne vide", phrase_statut("zz", 0, {}) === "");
  ok("html : échappe puis pose les <b>", statut_html("**Glisser** <x> & y") === "<b>Glisser</b> &lt;x&gt; &amp; y");
  ok("onglet : nom @ zoom, astérisque si sale", onglet_document({ name: "carte" }, 0.734, true) === "carte @ 73%*" && onglet_document({ name: "carte" }, 1, false) === "carte @ 100%");
  ok("onglet sans meta : « … »", onglet_document(null, 1, false) === "…");
  ok("pagination : planches ou page unique", pagination([], null) === "1 sur 1" && pagination([{ id: "a" }, { id: "b" }], "b") === "2 sur 2" && pagination([{ id: "a" }], "zz") === "1 sur 1");
}
if (echecs.length) { console.error("ECHECS statut :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA statut : PASS (9 controles)");
```

- [ ] **Step 2 : RED** — `cd frontend/vectorlab && node qa/statut.test.mjs` → `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3 : le module**

```js
// mod-statut.js — la barre d'état d'Affinity : phrase d'aide (verbes en
// gras, selon l'outil et la sélection), onglet de document, pagination.
// Feuille pure (bancable node) ; l'UI ne fait que poser le HTML.
const VERBES = ["glisser", "cliquer", "double-cliquer", "clic droit", "maj", "alt", "ctrl", "entrée", "échap", "suppr"];
export function phrase_statut(outil, nSel, hints) {
  if (outil === "select") {
    if (!nSel) return "**Glisser** pour utiliser un cadre de sélection. **Cliquer** sur un objet pour le sélectionner. **Clic droit** pendant la sélection pour activer/désactiver le mode Intersection.";
    return `${nSel} objet${nSel > 1 ? "s" : ""} sélectionné${nSel > 1 ? "s" : ""}. **Glisser** pour déplacer la sélection. **Cliquer** sur un autre objet pour le sélectionner. **Cliquer** sur une zone vide pour annuler la sélection. **Suppr** pour retirer.`;
  }
  const h = (hints || {})[outil];
  if (!h) return "";
  // les verbes connus en tête de segment (début, après « · » ou « , ») passent en gras avec majuscule
  return h.replace(/(^|·\s*|,\s*)([a-zéè-]+(?: droit)?)/gi, (m, sep, mot) => VERBES.includes(mot.toLowerCase()) ? `${sep}**${mot[0].toUpperCase()}${mot.slice(1)}**` : m);
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
export const statut_html = (s) => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
export function onglet_document(meta, zoom, sale) {
  if (!meta) return "…";
  return `${meta.name} @ ${Math.round((+zoom || 1) * 100)}%${sale ? "*" : ""}`;
}
export function pagination(planches, courante) {
  const n = Math.max(1, (planches || []).length);
  const i = (planches || []).findIndex((p) => p.id === courante);
  return `${i >= 0 ? i + 1 : 1} sur ${n}`;
}
```

- [ ] **Step 4 : vert** — `node qa/statut.test.mjs` → `QA statut : PASS (9 controles)`.
- [ ] **Step 5 : commit** `git commit --only frontend/vectorlab/js/mod-statut.js frontend/vectorlab/qa/statut.test.mjs -m "vectorlab : mod-statut — phrase d'aide aux verbes gras, onglet de document, pagination (RED constate puis 9 controles)"`

### Task 2 : `mod-menus.js` (arbre des dix menus, disponibilité, raccourcis)

**Files :** Create `frontend/vectorlab/js/mod-menus.js`, Test `frontend/vectorlab/qa/menus.test.mjs`.

- [ ] **Step 1 : le banc RED**

```js
// menus.test.mjs — mod-menus : la barre de menus d'Affinity — dix menus,
// entrées {id, libelle, raccourci, action} ou séparateurs, disponibilité
// calculée par un prédicat, libellé du raccourci. Feuille.
import { MENUS_BARRE, menus_construire, raccourci_de, menu_trouver } from "../js/mod-menus.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 200) : "")); };
{
  ok("dix menus dans l'ordre d'Affinity", JSON.stringify(MENUS_BARRE.map((m) => m.titre)) === '["Fichier","Edition","Document","Texte","Vecteur","Pixel","Calque","Affichage","Fenêtre","Aide"]', MENUS_BARRE.map((m) => m.titre).join(","));
  const toutes = MENUS_BARRE.flatMap((m) => m.entrees.filter((e) => e !== "-"));
  ok("chaque entrée a id, libellé et action ; ids uniques", toutes.every((e) => e.id && e.libelle && e.action) && new Set(toutes.map((e) => e.id)).size === toutes.length);
  ok("Edition porte Annuler Ctrl+Z, Rétablir, Dupliquer Ctrl+D, Tout sélectionner Ctrl+A", (() => { const m = menu_trouver(MENUS_BARRE, "Edition"); const ids = m.entrees.filter((e) => e !== "-").map((e) => e.id); return ids.includes("annuler") && ids.includes("refaire") && ids.includes("dupliquer") && ids.includes("toutSelectionner") && raccourci_de(m.entrees.find((e) => e.id === "annuler")) === "Ctrl+Z"; })());
  const c = menus_construire(MENUS_BARRE, (action) => action === "sauver" || action === "annuler");
  ok("construire : desactive = le prédicat dit non, séparateurs conservés", (() => { const f = c.find((m) => m.titre === "Fichier"); const s = f.entrees.find((e) => e !== "-" && e.id === "sauver"); const o = f.entrees.find((e) => e !== "-" && e.id === "ouvrir"); return s.desactive === false && o.desactive === true && f.entrees.includes("-"); })());
  ok("construire : les données d'origine restent intactes", MENUS_BARRE[0].entrees.every((e) => e === "-" || e.desactive === undefined));
  ok("état vide : prédicat absent → tout disponible", menus_construire(MENUS_BARRE).every((m) => m.entrees.every((e) => e === "-" || e.desactive === false)));
  ok("raccourci : Ctrl+Maj+Z, sans raccourci → chaîne vide", raccourci_de({ raccourci: "ctrl+shift+z" }) === "Ctrl+Maj+Z" && raccourci_de({}) === "");
  ok("trouver : menu inconnu → null", menu_trouver(MENUS_BARRE, "zz") === null);
  ok("Calque : Nouveau calque, Grouper, Verrouiller ; Vecteur : Convertir en courbes, Traçage d'image, Géométrie ; Pixel : Inverser, Nouveau calque", (() => { const ids = (t) => menu_trouver(MENUS_BARRE, t).entrees.filter((e) => e !== "-").map((e) => e.id); return ids("Calque").includes("calqueNouveau") && ids("Calque").includes("grouper") && ids("Calque").includes("verrouiller") && ids("Vecteur").includes("vectoriserTexte") && ids("Vecteur").includes("tracerImage") && ids("Vecteur").includes("boolUnion") && ids("Pixel").includes("pxInverser") && ids("Pixel").includes("pxCalque"); })());
}
if (echecs.length) { console.error("ECHECS menus :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA menus : PASS (9 controles)");
```

- [ ] **Step 2 : RED** — `node qa/menus.test.mjs` → `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3 : le module** (les actions sont des NOMS ; l'UI les résout dans une table vers `VL.*` / `VL.actions.*` / des boutons par id)

```js
// mod-menus.js — la barre de menus d'Affinity pour le Vectorlab : dix
// menus, entrées {id, libelle, raccourci?, action, ouvre?} ou "-"
// (séparateur). `action` est un NOM que l'UI résout ; `ouvre` désigne un
// onglet de la pile à montrer. Feuille pure ; l'inventaire du 18/09
// donne l'ordre et les libellés, seules les entrées réalisables sont là.
const e = (id, libelle, action, raccourci, extra) => ({ id, libelle, action, raccourci: raccourci || "", ...(extra || {}) });
export const MENUS_BARRE = [
  { titre: "Fichier", entrees: [
    e("accueil", "Accueil (Bibliothèque)", "biblio", "ctrl+alt+h"), "-",
    e("nouveau", "Nouveau…", "nouveau", "ctrl+n"), e("ouvrir", "Ouvrir…", "biblio", "ctrl+o"), "-",
    e("sauver", "Enregistrer", "sauver", "ctrl+s"), e("brouillon", "Restaurer le brouillon", "brouillon"), "-",
    e("inserer", "Insérer une image…", "imageFichier", "ctrl+shift+m"), e("insererBiblio", "Insérer depuis la Bibliothèque…", "imageBiblio"), e("coller", "Nouveau depuis Presse-papiers", "imageColler"), e("generer", "Nouveau traitement d'image (IA)…", "imageGenerer"), e("gpx", "Importer un GPX…", "gpx", "", { ouvre: "carte" }), "-",
    e("exporter", "Exporter…", "exporter", "ctrl+alt+shift+s", { ouvre: "exporter" }), e("exporterSvg", "Exporter SVG", "expSvg"), e("exporterPng", "Exporter PNG 2×", "expPng2"), e("print3d", "Impression 3D…", "expPrint3d"), e("bible", "Vers la Bible…", "expBible"), "-",
    e("metadonnees", "Configuration du document…", "configDoc"),
  ] },
  { titre: "Edition", entrees: [
    e("annuler", "Annuler", "annuler", "ctrl+z"), e("refaire", "Rétablir", "refaire", "ctrl+shift+z"), "-",
    e("toutSelectionner", "Tout sélectionner", "toutSelectionner", "ctrl+a"), e("deselectionner", "Désélectionner", "deselectionner", "escape"), e("selAttribut", "Sélectionner par attribut…", "selAttribut"), "-",
    e("copier", "Copier", "copier", "ctrl+c"), e("collerObj", "Coller", "coller", "ctrl+v"), e("dupliquer", "Dupliquer", "dupliquer", "ctrl+d"), e("puissance", "Dupliquer en puissance…", "puissance"), e("supprimer", "Supprimer", "supprimer", "delete"), "-",
    e("style", "Créer un style", "creerStyle"), e("instantane", "Ajouter un instantané", "instantane"), "-",
    e("parametres", "Paramètres…", "parametres", "ctrl+,"),
  ] },
  { titre: "Document", entrees: [
    e("configDoc", "Configuration…", "configDoc"), e("unites", "Unité d'affichage suivante", "unite"), "-",
    e("planches", "Planches…", "ouvrir", "", { ouvre: "planches" }), e("reperes", "Marges et fond perdu…", "ouvrir", "", { ouvre: "reperes" }), e("grilleDoc", "Grille du document…", "ouvrir", "", { ouvre: "grille" }), e("plateau", "Plateau et terrains…", "ouvrir", "", { ouvre: "plateau" }), e("carte", "Carte réelle…", "ouvrir", "", { ouvre: "carte" }), "-",
    e("instantaneDoc", "Ajouter un instantané", "instantane"), e("historique", "Historique…", "ouvrir", "", { ouvre: "historique" }),
  ] },
  { titre: "Texte", entrees: [
    e("poserTexte", "Outil Texte", "outil:texte", "t"), e("polices", "Typographies…", "flyout:texte"), e("editer", "Éditer le texte sélectionné", "editerTexte"), "-",
    e("vectoriserTexteMenu", "Convertir en courbes", "vectoriserTexte", "ctrl+enter"), e("vectoriserGlyphes", "Convertir en courbes par glyphe", "vectoriserGlyphes"), e("logo3d", "Logo 3D…", "expPrint3d"), "-",
    e("panneauTexte", "Panneau Texte…", "ouvrir", "", { ouvre: "texte" }),
  ] },
  { titre: "Vecteur", entrees: [
    e("vectoriserTexte", "Convertir en courbes", "vectoriserTexte", "ctrl+enter"), e("symbole", "Créer un symbole", "symboleCreer"), "-",
    e("boolUnion", "Géométrie : Union", "bool:union"), e("boolSoustraction", "Géométrie : Soustraction", "bool:soustraction"), e("boolIntersection", "Géométrie : Intersection", "bool:intersection"), e("boolDivision", "Géométrie : Division", "bool:division"), "-",
    e("grouper", "Grouper", "grouper", "ctrl+g"), e("degrouper", "Dégrouper", "degrouper", "ctrl+shift+g"), "-",
    e("joindre", "Relier les courbes", "noeuds:joindre"), e("inverser", "Inverser le sens", "noeuds:inverser"), e("diviser", "Diviser au nœud", "noeuds:diviser"), e("coins", "Arrondir les coins", "noeuds:coins"), "-",
    e("tracerImage", "Traçage d'image…", "imageVectoriser"), e("formes", "Formes paramétriques…", "flyout:forme"),
  ] },
  { titre: "Pixel", entrees: [
    e("pxCalque", "Nouveau calque pixel (poser une image)", "imageBiblio", "ctrl+shift+n"), e("pxEditer", "Éditer les pixels", "pxEditer"), "-",
    e("pxTout", "Tout sélectionner", "pixel:tout"), e("pxAucune", "Désélectionner", "pixel:aucune"), e("pxInverser", "Inverser la sélection", "pixel:inverser", "ctrl+i"), e("pxCroitre", "Croître", "pixel:croitre"), e("pxContracter", "Contracter", "pixel:contracter"), e("pxCouleur", "Sélectionner par couleur", "pixel:couleur"), "-",
    e("pxPanneau", "Réglages et filtres…", "ouvrir", "", { ouvre: "pixel" }), e("pxArt", "Pixel-art vers Tilelab…", "ouvrir", "", { ouvre: "pixel" }),
  ] },
  { titre: "Calque", entrees: [
    e("calqueNouveau", "Nouveau calque", "calqueNouveau"), e("calqueRenommer", "Renommer le calque", "calqueRenommer"), e("calqueSupprimer", "Supprimer le calque", "calqueSupprimer"), "-",
    e("grouperC", "Grouper", "grouper", "ctrl+g"), e("degrouperC", "Dégrouper", "degrouper", "ctrl+shift+g"), "-",
    e("verrouiller", "Verrouiller / déverrouiller le calque", "calqueVerrou"), e("masquer", "Masquer / afficher le calque", "calqueOeil"), "-",
    e("devant", "Tout devant", "ordre:devant"), e("avant", "Un cran devant", "ordre:avant"), e("arriere", "Un cran derrière", "ordre:arriere"), e("derriere", "Tout derrière", "ordre:derriere"), "-",
    e("effets", "Effets de calque…", "ouvrir", "", { ouvre: "apparence" }), e("panneauCalques", "Panneau Calques…", "ouvrir", "", { ouvre: "calques" }),
  ] },
  { titre: "Affichage", entrees: [
    e("zoomAjuster", "Zoom : ajuster", "zoomAjuster", "ctrl+0"), e("zoomCent", "Zoom : 100 %", "zoomCent", "ctrl+1"), "-",
    e("grille", "Grille", "grille", "g"), e("aimant", "Magnétisme aux objets", "aimant"), e("unite", "Unité des règles", "unite"), "-",
    e("persVecteur", "Persona Vecteur", "persona:vecteur"), e("persPixel", "Persona Pixel", "persona:pixel"),
  ] },
  { titre: "Fenêtre", entrees: [
    e("wCouleur", "Couleur", "ouvrir", "", { ouvre: "couleur" }), e("wApparence", "Apparence", "ouvrir", "", { ouvre: "apparence" }), e("wTexte", "Texte", "ouvrir", "", { ouvre: "texte" }), "-",
    e("wCalques", "Calques", "ouvrir", "", { ouvre: "calques" }), e("wTrace", "Tracé", "ouvrir", "", { ouvre: "trace" }), e("wImage", "Image", "ouvrir", "", { ouvre: "image" }), e("wStock", "Stock (Bibliothèque)", "ouvrir", "", { ouvre: "stock" }), "-",
    e("wTransformer", "Transformer", "ouvrir", "", { ouvre: "transformer" }), e("wNavigateur", "Navigateur", "ouvrir", "", { ouvre: "navigateur" }), e("wHistorique", "Historique", "ouvrir", "", { ouvre: "historique" }), e("wExporter", "Exporter", "ouvrir", "", { ouvre: "exporter" }),
  ] },
  { titre: "Aide", entrees: [
    e("raccourcis", "Raccourcis clavier…", "raccourcis", "f1"), e("guide", "Guide du Vectorlab…", "guide"), "-", e("apropos", "À propos…", "apropos"),
  ] },
];
const LIB = { ctrl: "Ctrl", shift: "Maj", alt: "Alt", enter: "Entrée", escape: "Échap", delete: "Suppr", ",": "," };
export function raccourci_de(entree) {
  const r = entree && entree.raccourci;
  if (!r) return "";
  return r.split("+").map((k) => LIB[k] || (k.length === 1 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1))).join("+");
}
export function menus_construire(menus, peut) {
  return (menus || []).map((m) => ({ titre: m.titre, entrees: m.entrees.map((x) => x === "-" ? "-" : { ...x, desactive: peut ? !peut(x.action, x) : false }) }));
}
export const menu_trouver = (menus, titre) => (menus || []).find((m) => m.titre === titre) || null;
```

- [ ] **Step 4 : vert** — `node qa/menus.test.mjs` → `QA menus : PASS (9 controles)`.
- [ ] **Step 5 : commit** `git commit --only frontend/vectorlab/js/mod-menus.js frontend/vectorlab/qa/menus.test.mjs -m "vectorlab : mod-menus — l'arbre des dix menus d'Affinity, disponibilite, raccourcis (RED puis 9 controles)"`

### Task 3 : deux personas, l'outil tranche partagé

**Files :** Modify `frontend/vectorlab/js/mod-persona.js` (PERSONAS, `persona_de_outil`), `frontend/vectorlab/qa/pixel_ui.test.mjs` (pin des personas), `frontend/vectorlab/js/mod-exportplus.js:60` (classe `outil-export` retirée).

- [ ] **Step 1 : RED** — dans `pixel_ui.test.mjs` remplacer le pin par `ok("deux personas : vecteur, pixel (l'export est un onglet)", JSON.stringify(PERSONAS.map((p) => p.id)) === '["vecteur","pixel"]')` et ajouter `ok("tranche : outil de tous les personas", persona_de_outil("tranche") === "tous")`. `node qa/pixel_ui.test.mjs` → ECHECS (deux lignes).
- [ ] **Step 2 : le code** — `PERSONAS` = vecteur + pixel ; `persona_de_outil` : `if (outil === "select" || outil === "tranche") return "tous";`. Dans mod-exportplus, `b.className = ""` (le bouton n'est plus réservé à un persona). Le panneau Export rendu par `rendreExport()` reste (il vit dans `#panneauExport`).
- [ ] **Step 3 : vert** — `node qa/pixel_ui.test.mjs` → PASS.
- [ ] **Step 4 : commit** `--only` des trois fichiers, message `vectorlab : deux personas (Vecteur, Pixel) — l'export devient un onglet, l'outil tranche est partage`.

### Task 4 : `index.html` — les six bandes (ids conservés)

**Files :** Modify `frontend/vectorlab/index.html` (le `<header class="bar">` et `<main>` / `#hintOutil`).

- [ ] **Step 1 : réécrire l'en-tête** — remplacer `<header class="bar">…</header>` par :

```html
  <nav id="menubar" class="mb" aria-label="Menus"></nav>
  <header class="bar pb">
    <div class="brand" title="Vectorlab">a</div>
    <nav id="personas" class="personas" title="Persona : une surface, deux métiers"></nav>
    <button id="btnBiblio" class="pb-icone" title="Bibliothèque des documents (Accueil)">⌂</button>
    <div class="spacer"></div>
    <span id="pbCotes" class="pb-cotes" title="Cotes de la sélection">Pas de données</span>
    <span id="pbDoc" class="pb-doc" title="Taille, unité et dpi du document"></span>
    <span id="temoin" title="État d'enregistrement">✓</span>
    <button id="btnAnnuler" class="pb-icone" title="Annuler (Ctrl+Z)">↶</button>
    <button id="btnRefaire" class="pb-icone" title="Refaire (Ctrl+Y)">↷</button>
    <span class="exp-conteneur">
      <button id="btnExporter" class="pb-export" title="Exporter le document"><i></i>Exporter SVG ▾</button>
      <div id="expMenu" class="exp-menu hidden">…(inchangé)…</div>
    </span>
    <span class="exp-conteneur"><input type="file" id="imgFichierInput" accept="image/png,image/jpeg,image/webp" hidden/></span>
    <button id="btnSauver" class="primaire" title="Sauver (Ctrl+S)">Sauver</button>
    <button id="btnAide" class="pb-icone" title="Raccourcis clavier (F1)">?</button>
  </header>
  <div id="contexte" class="cb">
    <span id="cbSelection">Aucune sélection</span>
    <span class="cb-sep"></span>
    <span id="cbOutil"></span>
    <span class="cb-sep"></span>
    <button id="btnGrille" title="Grille d'aimantation et repère visuel (G)">⊞ 8</button>
    <select id="selGrille" title="Pas de la grille — en pixels du document"></select>
    <button id="btnAimant" class="actif" title="Aimantation aux objets">⌖</button>
    <button id="btnUnite" title="Unité d'affichage des règles et des cotes">px</button>
    <span class="spacer"></span>
    <span id="zoomLabel" title="Molette : zoom · glisser (main ou fond) : déplacer">100 %</span>
  </div>
  <div class="dt"><span id="docTitle" class="dt-onglet">…</span></div>
```
puis, sous `.rangee`, la barre d'état :
```html
  <footer class="sb">
    <span id="sbPages" class="sb-pages">|◀ ◀ 1 sur 1 ▶ ▶|</span>
    <span id="hintOutil" class="sb-phrase"></span>
    <span class="spacer"></span>
    <span id="docMeta" class="sb-msg"></span>
  </footer>
```
Retirer `<div id="hintOutil" class="hint"></div>` de `#stage`. Le `<b id="docTitle">` du `.doc` disparaît (l'id vit dans `.dt`).

- [ ] **Step 2 : vérifier** que chaque id référencé par un module existe encore : `grep -o 'id="[^"]*"' index.html | sort` ⊇ {btnBiblio, personas, temoin, zoomLabel, btnUnite, btnGrille, selGrille, btnAimant, btnAnnuler, btnRefaire, btnExporter, expMenu, expSvg, expPng1, expPng2, expPng4, expTransparent, expBible, expPrint3d, imgFichierInput, btnSauver, docTitle, docMeta, hintOutil, outils, stage, canvasHost, overlay}.
- [ ] **Step 3 : commit** `--only frontend/vectorlab/index.html`.

### Task 5 : `mod-charpente.js` — la barre de menus, l'onglet, la barre d'état, le résolveur d'actions

**Files :** Create `frontend/vectorlab/js/mod-charpente.js` ; Modify `frontend/vectorlab/js/core.js` (import + `initCharpente(VL)` après `initPanneaux`), `frontend/vectorlab/js/mod-tools.js:748` et les trois autres `majHint` (ils écrivent `textContent` : le module réécrit `innerHTML` depuis `phrase_statut` — voir Step 2).

- [ ] **Step 1 : le module UI**

```js
// mod-charpente.js — la charpente d'Affinity : barre de menus (mod-menus),
// onglet de document, barre d'état (mod-statut), cotes de la sélection,
// bouton « Exporter SVG », aide Raccourcis. Traduit, délègue, ne calcule pas.
import { MENUS_BARRE, menus_construire, raccourci_de } from "./mod-menus.js";
import { phrase_statut, statut_html, onglet_document, pagination } from "./mod-statut.js";
import { op_calque_ajouter, op_calque_supprimer, op_calque_renommer, op_calque_verrou, op_calque_visible, op_supprimer } from "./mod-doc.js";
export function initCharpente(VL) {
  const { $, etat } = VL;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const clic = (sel) => { const b = $(sel); if (!b || b.disabled) return false; b.click(); return true; };
  const A = () => VL.actions || {};
  const sel = () => etat.selection.length;
  // ── la table des actions : nom → { peut(), faire() } ──
  const T = {
    biblio: { peut: () => true, faire: () => VL.ouvrirBiblio() },
    nouveau: { peut: () => true, faire: () => { VL.ouvrirBiblio(); setTimeout(() => $("#bibNouvNom")?.focus(), 50); } },
    sauver: { peut: () => !!etat.doc, faire: () => VL.sauver() },
    brouillon: { peut: () => !!(etat.doc && VL.restaurerBrouillon), faire: () => VL.restaurerBrouillon() },
    imageFichier: { peut: () => !!etat.doc, faire: () => A().image.fichier() }, imageBiblio: { peut: () => !!etat.doc, faire: () => A().image.biblio() },
    imageColler: { peut: () => !!etat.doc, faire: () => A().image.coller() }, imageGenerer: { peut: () => !!etat.doc, faire: () => A().image.generer() },
    imageVectoriser: { peut: () => !!(etat.doc && A().image && A().image.vectoriser), faire: () => A().image.vectoriser() },
    gpx: { peut: () => !!etat.doc, faire: () => clic("#carteGpx") || VL.ouvrirOnglet("carte") },
    exporter: { peut: () => !!etat.doc, faire: () => VL.ouvrirOnglet("exporter") },
    expSvg: { peut: () => !!etat.doc, faire: () => clic("#expSvg") }, expPng2: { peut: () => !!etat.doc, faire: () => clic("#expPng2") },
    expPrint3d: { peut: () => !!etat.doc, faire: () => clic("#expPrint3d") }, expBible: { peut: () => !!etat.doc, faire: () => clic("#expBible") },
    configDoc: { peut: () => !!etat.doc, faire: () => VL.configurerDocument ? VL.configurerDocument() : VL.toast("configuration : lot R5") },
    parametres: { peut: () => true, faire: () => VL.parametresAppli ? VL.parametresAppli() : VL.toast("paramètres : lot R5") },
    annuler: { peut: () => etat.histo.peutAnnuler(), faire: () => VL.annuler() }, refaire: { peut: () => etat.histo.peutRefaire(), faire: () => VL.refaire() },
    toutSelectionner: { peut: () => !!etat.doc, faire: () => VL.setSelection(etat.doc.calques.filter((c) => c.visible && !c.verrou).flatMap((c) => c.objets.map((o) => o.id))) },
    deselectionner: { peut: () => sel() > 0, faire: () => VL.setSelection([]) },
    selAttribut: { peut: () => sel() === 1, faire: () => VL.ouvrirOnglet("transformer") },
    copier: { peut: () => sel() > 0, faire: () => VL.copierSelection() }, coller: { peut: () => !!etat.pressePapiers, faire: () => VL.collerSelection() },
    dupliquer: { peut: () => sel() > 0, faire: () => VL.dupliquerSelection() }, puissance: { peut: () => sel() > 0, faire: () => VL.ouvrirOnglet("transformer") },
    supprimer: { peut: () => sel() > 0, faire: () => { VL.executer(op_supprimer, etat.selection.slice()); VL.setSelection([]); } },
    creerStyle: { peut: () => sel() === 1, faire: () => clic("#a2StyleCreer") || VL.ouvrirOnglet("apparence") },
    instantane: { peut: () => !!etat.doc, faire: () => clic("#instCreer") || VL.ouvrirOnglet("historique") },
    unite: { peut: () => !!etat.doc, faire: () => clic("#btnUnite") },
    ouvrir: { peut: () => true, faire: (x) => VL.ouvrirOnglet(x.ouvre) },
    "outil:texte": { peut: () => !!etat.doc, faire: () => VL.setOutil("texte") },
    "flyout:texte": { peut: () => !!etat.doc, faire: () => VL.flyout.ouvrir("texte") }, "flyout:forme": { peut: () => !!etat.doc, faire: () => VL.flyout.ouvrir("forme") },
    editerTexte: { peut: () => sel() === 1 && VL.objetDe(etat.selection[0])?.objet.type === "texte", faire: () => VL.editerTexte && VL.editerTexte(etat.selection[0]) },
    vectoriserTexte: { peut: () => sel() >= 1 && !!VL.textesEnChemins, faire: () => VL.textesEnChemins(etat.selection.slice()) },
    vectoriserGlyphes: { peut: () => sel() === 1 && !!VL.vectoriserTexte, faire: () => VL.vectoriserTexte(etat.selection[0], undefined, true) },
    symboleCreer: { peut: () => sel() > 0, faire: () => VL.flyout.ouvrir("symbole") },
    grouper: { peut: () => sel() >= 2, faire: () => A().selection.grouper() }, degrouper: { peut: () => !!(A().selection && A().selection.peut && A().selection.peut().groupe), faire: () => A().selection.degrouper() },
    pxEditer: { peut: () => !!etat.doc, faire: () => { VL.setPersona("pixel"); setTimeout(() => clic("#pxEditer"), 60); } },
    calqueNouveau: { peut: () => !!etat.doc, faire: () => clic("#btnCalquePlus") },
    calqueRenommer: { peut: () => !!etat.doc, faire: () => { const c = etat.doc.calques.find((x) => x.id === etat.calqueActif); const nom = prompt("Nom du calque :", c ? c.nom : ""); if (nom !== null) VL.executer(op_calque_renommer, etat.calqueActif, nom); } },
    calqueSupprimer: { peut: () => !!(etat.doc && etat.doc.calques.length > 1), faire: () => { if (confirm("Supprimer le calque actif et ses objets ?")) { VL.executer(op_calque_supprimer, etat.calqueActif); etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id; VL.rendre(); } } },
    calqueVerrou: { peut: () => !!etat.doc, faire: () => { const c = etat.doc.calques.find((x) => x.id === etat.calqueActif); VL.executer(op_calque_verrou, c.id, !c.verrou); } },
    calqueOeil: { peut: () => !!etat.doc, faire: () => { const c = etat.doc.calques.find((x) => x.id === etat.calqueActif); VL.executer(op_calque_visible, c.id, !c.visible); } },
    zoomAjuster: { peut: () => !!etat.doc, faire: () => VL.zoomAjuster() }, zoomCent: { peut: () => !!etat.doc, faire: () => VL.zoomCent() },
    grille: { peut: () => true, faire: () => clic("#btnGrille") }, aimant: { peut: () => true, faire: () => clic("#btnAimant") },
    raccourcis: { peut: () => true, faire: () => ouvrirRaccourcis() }, guide: { peut: () => true, faire: () => window.open("/guide/", "_blank") }, apropos: { peut: () => true, faire: () => VL.toast("Vectorlab — Deepotus Video Gen, éditeur vectoriel et raster, thème Affinity") },
  };
  // préfixes : bool:x, noeuds:x, pixel:x, ordre:x, persona:x
  function resoudre(action) {
    if (T[action]) return T[action];
    const [pre, arg] = action.split(":");
    if (pre === "bool") return { peut: () => sel() >= 2, faire: () => A().selection.booleen(arg) };
    if (pre === "ordre") return { peut: () => sel() >= 1, faire: () => A().selection.ordre(arg) };
    if (pre === "noeuds") return { peut: () => !!(A().noeuds && A().noeuds.peut && (arg === "joindre" ? A().noeuds.peut().deux : arg === "diviser" ? A().noeuds.peut().ancre : A().noeuds.peut().sel || A().noeuds.peut().chemin)), faire: () => A().noeuds[arg]() };
    if (pre === "pixel") return { peut: () => !!(A().pixel && etat.px && etat.px.id), faire: () => A().pixel[arg]() };
    if (pre === "persona") return { peut: () => true, faire: () => VL.setPersona(arg) };
    return { peut: () => false, faire: () => {} };
  }
  // ── la barre de menus ──
  const mb = $("#menubar");
  let ouvert = null;
  function fermer() { if (ouvert) { ouvert.remove(); ouvert = null; } mb.querySelectorAll(".mb-titre.actif").forEach((b) => b.classList.remove("actif")); }
  function ouvrirMenu(titreEl, m) {
    fermer();
    titreEl.classList.add("actif");
    const menu = menus_construire([m], (a, x) => resoudre(a).peut(x))[0];
    const d = document.createElement("div");
    d.className = "mb-menu";
    d.innerHTML = menu.entrees.map((x, i) => x === "-" ? `<hr/>` : `<button class="mb-item" data-i="${i}" ${x.desactive ? "disabled" : ""}><span>${esc(x.libelle)}</span><small>${esc(raccourci_de(x))}</small></button>`).join("");
    d.querySelectorAll(".mb-item").forEach((b) => b.addEventListener("click", () => { const x = menu.entrees[+b.dataset.i]; fermer(); resoudre(x.action).faire(x); }));
    const r = titreEl.getBoundingClientRect();
    d.style.left = r.left + "px"; d.style.top = r.bottom + "px";
    document.body.appendChild(d); ouvert = d;
  }
  mb.innerHTML = `<span class="mb-logo">a</span>` + MENUS_BARRE.map((m, i) => `<button class="mb-titre" data-i="${i}">${esc(m.titre)}</button>`).join("");
  mb.querySelectorAll(".mb-titre").forEach((b) => {
    b.addEventListener("click", (ev) => { ev.stopPropagation(); if (b.classList.contains("actif")) fermer(); else ouvrirMenu(b, MENUS_BARRE[+b.dataset.i]); });
    b.addEventListener("pointerenter", () => { if (ouvert && !b.classList.contains("actif")) ouvrirMenu(b, MENUS_BARRE[+b.dataset.i]); });
  });
  document.addEventListener("pointerdown", (ev) => { if (ouvert && !ouvert.contains(ev.target) && !mb.contains(ev.target)) fermer(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && ouvert) { fermer(); ev.stopImmediatePropagation(); } }, true);
  // ── onglets de la pile (R3 les branche ; ici le crochet existe déjà) ──
  VL.ouvrirOnglet = VL.ouvrirOnglet || ((nom) => { const d = $("#" + nom + "Details"); if (d) { d.open = true; d.scrollIntoView({ block: "start" }); } });
  // ── l'aide Raccourcis : un dialogue construit depuis les menus ──
  function ouvrirRaccourcis() {
    let dlg = $("#raccDlg");
    if (!dlg) { dlg = document.createElement("div"); dlg.id = "raccDlg"; dlg.className = "vl-dlg"; document.body.appendChild(dlg); }
    const lignes = MENUS_BARRE.flatMap((m) => m.entrees.filter((x) => x !== "-" && x.raccourci).map((x) => `<tr><td>${esc(m.titre)}</td><td>${esc(x.libelle)}</td><td><kbd>${esc(raccourci_de(x))}</kbd></td></tr>`)).join("");
    dlg.innerHTML = `<div class="vl-dlg-boite racc-boite"><div class="vl-dlg-tete"><b>Raccourcis clavier</b><span class="spacer"></span><button id="raccFermer" title="Fermer">✕</button></div><div class="racc-corps"><table>${lignes}</table></div></div>`;
    dlg.classList.remove("hidden");
    $("#raccFermer").addEventListener("click", () => dlg.classList.add("hidden"));
  }
  $("#btnAide")?.addEventListener("click", ouvrirRaccourcis);
  document.addEventListener("keydown", (ev) => { if (ev.key === "F1") { ouvrirRaccourcis(); ev.preventDefault(); } });
  // ── onglet de document, cotes, barre d'état ──
  function majOnglet() {
    $("#docTitle").textContent = onglet_document(etat.meta, etat.zoom, etat.sale);
    const d = etat.doc; const u = VL.unites();
    $("#pbDoc").textContent = d ? `${d.taille.w} × ${d.taille.h}px, ${(d.taille.w * d.taille.h / 1e6).toFixed(2)}MP, ${u.affichage} · ${u.dpi} dpi` : "";
    const b = etat.doc && etat.selection.length ? VL.bboxSelectionDoc() : null;
    $("#pbCotes").textContent = b ? `${VL.cote("L", b.w)} × ${VL.cote("H", b.h)}` : "Pas de données";
    $("#sbPages").textContent = `|◀ ◀ ${pagination(etat.doc ? etat.doc.planches : [], etat.plancheCourante)} ▶ ▶|`;
  }
  VL.majStatut = () => { const h = $("#hintOutil"); if (!h) return; const hints = Object.assign({}, VL.hints || {}); h.innerHTML = statut_html(phrase_statut(etat.outil, etat.selection.length, hints)); };
  const sRendu = VL.surRendu, sSel = VL.surSelection, sOutil = VL.surOutil;
  VL.surRendu = () => { sRendu(); majOnglet(); };
  VL.surSelection = () => { sSel(); majOnglet(); VL.majStatut(); };
  VL.surOutil = () => { sOutil(); VL.majStatut(); };
  const sVue = VL.appliquerVue;   // le zoom change l'onglet
  VL.appliquerVue = () => { sVue(); majOnglet(); };
  majOnglet(); VL.majStatut();
}
```

- [ ] **Step 2 : les HINTS deviennent une source** — dans `mod-tools.js`, après `const HINTS = {…}`, poser `VL.hints = Object.assign(VL.hints || {}, HINTS);` et remplacer `majHint` par `function majHint() { if (VL.majStatut) VL.majStatut(); else { const el = $("#hintOutil"); if (el) el.textContent = HINTS[etat.outil] || ""; } }`. Même geste dans `mod-outils2.js:347`, `mod-pixelui.js:615`, `mod-apparence2.js:272`, `mod-exportplus.js:253` : `VL.hints = Object.assign(VL.hints || {}, HINTS2)` (resp. `HINTS_PIXEL`, `HINTS3`, `HINTS4`) et le crochet `surOutil` appelle `VL.majStatut && VL.majStatut()` au lieu d'écrire `textContent`.
- [ ] **Step 3 : core.js** — `import { initCharpente } from "./mod-charpente.js";` et `initCharpente(VL);` juste avant `window.VL = VL;`. Le `zoomLabel` reste mis à jour par `appliquerVue` (core) : `VL.appliquerVue` est réassigné par le module mais le cœur appelle sa fonction locale — l'onglet suit donc le zoom par la molette **via `surRendu`** seulement : ajouter dans core `appliquerVue()` une ligne `VL.surVue && VL.surVue();` en fin de fonction, et dans mod-charpente utiliser `VL.surVue = majOnglet` (retirer la réassignation de `appliquerVue`).
- [ ] **Step 4 : CSS de la charpente** (fin de `vectorlab.css`) :

```css
/* ══ Relooking Affinity — R1 charpente ══ */
:root { --aff-fond: #2b2b2b; --aff-barre: #232323; --aff-canevas: #262626; --aff-bord: #3a3a3a; --aff-texte: #d0d0d0; --aff-muet: #9a9a9a; --aff-sel: #2b6fd6; --aff-cyan: #22c3d8; --aff-violet: #cf6fe3; --aff-menu: #1e1e1e; }
.mb { display: flex; align-items: center; height: 32px; padding: 0 8px; gap: 2px; background: var(--aff-barre); border-bottom: 1px solid var(--aff-bord); font-size: 12px; }
.mb-logo { width: 20px; height: 20px; margin-right: 10px; border-radius: 4px; background: #3fbf5a; color: #0b1a0e; font-weight: 800; text-align: center; line-height: 20px; }
.mb-titre { background: none; border: 0; color: var(--aff-texte); padding: 0 9px; height: 26px; border-radius: 4px; font-size: 12px; }
.mb-titre:hover, .mb-titre.actif { background: #3c3c3c; }
.mb-menu { position: fixed; z-index: 120; min-width: 230px; padding: 4px; background: var(--aff-menu); border: 1px solid var(--aff-bord); border-radius: 4px; box-shadow: 0 10px 28px rgba(0,0,0,.55); display: flex; flex-direction: column; }
.mb-menu hr { border: 0; border-top: 1px solid var(--aff-bord); margin: 4px 6px; }
.mb-item { display: flex; justify-content: space-between; gap: 24px; background: none; border: 0; color: var(--aff-texte); height: 24px; padding: 0 10px; border-radius: 3px; text-align: left; font-size: 12px; }
.mb-item:hover:not(:disabled) { background: var(--aff-sel); color: #fff; }
.mb-item:disabled { color: #6a6a6a; opacity: 1; }
.mb-item small { color: var(--aff-muet); font-size: 11px; } .mb-item:hover:not(:disabled) small { color: #e8eefc; }
.pb { height: 42px; padding: 0 10px; gap: 8px; background: var(--aff-fond); border-bottom: 1px solid var(--aff-bord); }
.pb .brand { width: 26px; height: 26px; border-radius: 6px; background: #3a3a3a; color: #d9d9d9; text-align: center; line-height: 26px; font-size: 18px; font-weight: 800; letter-spacing: 0; }
.personas { display: flex; gap: 2px; padding: 3px; margin-left: 6px; background: #1f1f1f; border-radius: 18px; }
.personas button { height: 26px; padding: 0 14px; border: 0; border-radius: 13px; background: transparent; color: var(--aff-muet); font-size: 12px; letter-spacing: 0; }
.personas button:hover { background: #333; color: var(--aff-texte); }
.personas button.actif { color: #101010; font-weight: 600; }
.personas button[data-persona="vecteur"].actif { background: var(--aff-cyan); }
.personas button[data-persona="pixel"].actif { background: var(--aff-violet); }
.pb-icone { width: 28px; height: 28px; padding: 0; border: 0; border-radius: 4px; background: transparent; font-size: 15px; }
.pb-icone:hover { background: #3c3c3c; }
.pb-cotes, .pb-doc { color: var(--aff-muet); font-size: 11px; font-variant-numeric: tabular-nums; }
.pb-export { height: 28px; border: 0; border-radius: 4px; background: #3b3b3b; padding: 0 10px 0 8px; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; }
.pb-export i { width: 3px; height: 14px; background: #f0803c; border-radius: 1px; }
.cb { display: flex; align-items: center; height: 32px; padding: 0 10px; gap: 8px; background: var(--aff-fond); border-bottom: 1px solid var(--aff-bord); font-size: 12px; color: var(--aff-texte); }
.cb-sep { width: 1px; height: 18px; background: var(--aff-bord); }
.cb button, .cb select { height: 24px; border: 0; border-radius: 4px; background: #3b3b3b; color: #e0e0e0; font-size: 12px; padding: 0 8px; }
.cb button.actif { background: #4a4a4a; box-shadow: inset 0 0 0 1px #5a5a5a; }
.dt { height: 26px; display: flex; align-items: flex-end; background: var(--aff-barre); border-bottom: 1px solid var(--aff-bord); padding: 0 6px; }
.dt-onglet { height: 24px; line-height: 24px; padding: 0 12px; background: var(--aff-fond); color: var(--aff-texte); font-size: 11.5px; border-radius: 4px 4px 0 0; border: 1px solid var(--aff-bord); border-bottom: 0; }
.sb { display: flex; align-items: center; height: 22px; padding: 0 8px; gap: 12px; background: var(--aff-barre); border-top: 1px solid var(--aff-bord); font-size: 11px; color: var(--aff-muet); white-space: nowrap; overflow: hidden; }
.sb-pages { font-variant-numeric: tabular-nums; letter-spacing: .04em; }
.sb-phrase { overflow: hidden; text-overflow: ellipsis; } .sb-phrase b { color: var(--aff-texte); font-weight: 600; }
.sb-msg { color: var(--aff-texte); } .sb-msg.erreur { color: #e08a8a; }
.mode-biblio .cb, .mode-biblio .dt, .mode-biblio .sb, .mode-biblio .pb-cotes, .mode-biblio .pb-doc, .mode-biblio .pb-export { display: none; }
.racc-boite { width: min(620px, 92vw); } .racc-corps { overflow: auto; padding: 8px 14px; max-height: 70vh; font-size: 12px; }
.racc-corps table { border-collapse: collapse; width: 100%; } .racc-corps td { padding: 3px 8px; border-bottom: 1px solid #2c323d; } .racc-corps kbd { background: #1b2028; border: 1px solid var(--aff-bord); border-radius: 3px; padding: 1px 6px; font: 11px Consolas, monospace; }
```
et retirer les règles mortes `.hint { … }` / `.hint:empty` (l'id vit dans `.sb`). Les règles `.mode-biblio … #zoomLabel` restent vraies.

- [ ] **Step 5 : banc complet** — `node qa/run.mjs` → tous PASS (les nouveaux bancs listés).
- [ ] **Step 6 : commit** `--only` de `mod-charpente.js`, `core.js`, `vectorlab.css`, `mod-tools.js`, `mod-outils2.js`, `mod-pixelui.js`, `mod-apparence2.js`, `mod-exportplus.js`, `index.html` (si pas déjà) — message `vectorlab : charpente Affinity — barre de menus qui execute, pastilles Vecteur / Pixel, barre contextuelle (squelette), onglet de document, barre d'etat`.

### Task 6 : preuve en réel, déploiement, relevé

- [ ] **Step 1 : backend du worktree** — `DEEPOTUS_DATA_DIR=<scratchpad>/data PORT=8799 python -m uvicorn app.main:app --host 127.0.0.1 --port 8799` en arrière-plan ; navigateur intégré sur `http://127.0.0.1:8799/vectorlab/`, `resize_window` 1400 × 900 ; créer un document.
- [ ] **Step 2 : mesures DOM** — `offsetHeight` de `.mb` (32), `.pb` (42), `.cb` (32), `.dt` (26), `.sb` (22) ; `#stage` ≥ 600 ; cliquer « Edition » → `.mb-menu` visible avec ≥ 12 `.mb-item`, « Dupliquer » disabled sans sélection ; poser un rectangle, `VL.setSelection([id])`, menu Edition → « Dupliquer » → 2 objets ; « Annuler » → 1 ; Échap ferme le menu ; `#docTitle` = `nom @ 100%*` après la commande ; la phrase `#hintOutil` contient `<b>Glisser</b>` avec l'outil select et change en passant à `rect` ; `#pbCotes` ≠ « Pas de données » avec la sélection ; persona Pixel → pastille violette (`getComputedStyle` background) ; `#personas` a 2 boutons ; l'onglet Export n'existe plus comme persona mais `#panneauExport` existe.
- [ ] **Step 3 : audit de lisibilité** — aucune bande avec `scrollWidth > clientWidth + 1` à 1400 px ; tous les `.cb button` ≥ 24 px de haut.
- [ ] **Step 4 : taskkill du PID 8799.**
- [ ] **Step 5 : déploiement** — comparer `%LOCALAPPDATA%\DeepotusVideoGen\frontend\vectorlab` à la base (`git hash-object`), sauvegarde `_backup_predeploy_2026-09-18-relooking-r1`, copier, vérifier = cible ; statiques seuls : aucune relance.
- [ ] **Step 6 : relevé de livraison** en tête de ce plan, mémoire, push.
