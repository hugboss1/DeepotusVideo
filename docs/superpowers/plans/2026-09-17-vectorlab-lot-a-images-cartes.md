# Vectorlab classe Affinity — LOT A : images et cartes — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module
> pur). Steps use checkbox (`- [ ]`) syntax for tracking.

> Conception validée : `docs/superpowers/specs/2026-09-17-vectorlab-affinity-design.md`
> (§4 lot A, décisions D1, D2, D5, D6, D7, D9). Branche : `chantier/vectorlab-affinity`.
> Ce plan est COMMIS avant le code (patron des chantiers du 27/08).

> **RELEVÉ DE LIVRAISON (17/09/2026) : LOT A LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ.**
>
> **Livré** (10 commits sur `chantier/vectorlab-affinity`, T0→T8, tous
> poussés) : imagetracerjs 1.2.6 vendorisé (Unlicense, écart dit) ; objet
> `image` du modèle (href relatif, `nat`, `rognage`, `verrou` d'objet,
> résolveur d'href de `compilerSVG(doc, opts)`, `fill-rule`) ; `reperes`
> fond perdu / zone sûre (rects dérivés, guides aimantants, jamais compilés) ;
> magasin d'images `<did>.img<n>.png` + routes `POST/GET
> /vector/docs/{id}/images[/{name}]`, dupliquer copie les images ;
> `mod-image.js` (Bibliothèque via `__dzLibPicker` du parent ou grille de
> repli, fichier, presse-papiers ×2 voies, génération ; panneau Image :
> rognage, verrou, Vectoriser ; panneau Repères) ; export SVG/PNG avec
> images inlinées en `data:` (le JSON n'en porte jamais) ; `mod-trace.js`
> (couleurs, lissage, seuil, définition, aperçu par LE compilateur, pose en
> UNE commande dans un calque « vectorisé ») ; `mod-brouillon.js` (30 s,
> restauré si pertinent, effacé au Sauver) ; Cardforge : `CF.vector.update`
> + `CF.vector.image` au CORE, bouton « Éditer cette face dans le
> Vectorlab » (`docFaceVec`, calque image verrouillé, repères depuis la
> géométrie du jeu).
>
> **TDD tenu** : RED constaté avant chaque module (exports manquants ×5,
> `AttributeError lister_images`, `cf-face-vlab-edit` absent). Bancs :
> node **417 contrôles** (+89 : image 33, image_ui 16, reperes 13, trace 17,
> brouillon 10), pytest `test_vector_docs` **25 passed** (+3), `cards_face`
> 147, `cards_type` 348, `cards_core` vert. Deux pins corrigés EN LE DISANT :
> le cas `..%2F` du client tombe dans le catch-all SPA (piège n°7 — assertion
> « jamais une image ») ; un pin sur le MOT « base64 » rougissait sur un
> commentaire (→ le jeton `;base64,`).
>
> **Prouvé en réel** (backend du worktree sur 8799, données isolées,
> viewport émulé 1400×900 — un volet caché rend `#stage` 0×0 et
> `elementFromPoint` nul, mesuré) : pose d'un PNG canvas 400×400 →
> `href=/api/vector/docs/<id>/images/img1.png`, bbox 400 px, panneau Image
> `offsetHeight` 106 ; drag pointeur synthétique x 175→259 (dx 84 = 60 px
> écran / zoom 0,71, `translate` vu pendant le geste) ; poignée 4 : 400→297 ;
> rognage 80/80/240/240 → `viewBox="80 80 240 240"` ; verrou → `data-verrou`
> et drag sans effet (259→259), libéré → 259→315 ; repères 3 mm / 6 mm →
> `[35.43, 35.43]` / `[70.87, 70.87]`, deux `rect.repere` d'overlay (679 et
> 608 px de large), `aimantePt(35.9)` → 35.43 ; brouillon écrit, doc serveur
> relu, `surCharge` + confirm → 1 objet restauré, `sale=true`, toast ; Sauver
> → v2, clé effacée. **Le pont du spec** : Cardforge (poker_eu, 300 dpi,
> toile 815×1110) → « Éditer cette face » → doc `92dd13f76ab7` ancré
> `deck_id`, taille 815×1110, mm/300, `reperes {fondPerdu:[35.5,35.5],
> zoneSure:[71,70.5]}`, calque « face (verrouillée) » avec l'image
> `img1.png` (1 095 162 octets, décodée 815×1110) verrouillée, calque
> « retouches » actif ; Vectoriser 8 couleurs → **2 876 chemins**, aperçu
> `#trApercu` `offsetHeight` 540, Valider → calque « vectorisé » (2 876
> objets) ; retouche : un chemin déplacé au pointeur (`d` changé, historique
> annulable) ; Exporter PNG 2× → `vector_92dd13f76ab7_2x.png` 200 image/png
> **1630×2220 = exactement le 2×** ; Cardforge « Poser 2× » → `face.src =
> img:vector_92dd13f76ab7_2x.png`, **jauge 832 DPI « suffisante »** (source
> 1630×2220 posée en 587,8×800,6 px dans la fenêtre du cadre — au-dessus de
> 600 parce que la fenêtre d'illustration est plus petite que la toile ;
> la jauge lit bien la trame 2×). Négatifs : Vectoriser sur un doc vide →
> toast « aucune image dans le document — Image ▾ pour en poser une » ;
> grille de repli Bibliothèque hors iframe (1 carte, `offsetHeight` 140).
>
> **Déployé** : 10 fichiers installés = base `5d01db2` (table hash-object)
> → sauvegarde `_backup_predeploy_2026-09-17-vectorlab-lotA` → copie depuis
> `git archive 30a3fc6` → **57 fichiers = cible** (hash-object), pré-vol du
> python embarqué `import app.main` OK. Aucune migration de base. **Le
> backend installé n'écoutait pas (8765 muet, journal du 07/09) : c'est
> l'utilisateur qui relance.**
>
> **Reste** : l'écran « restaurer ? » n'a été exercé que par `surCharge`
> simulé (le confirm au rechargement bloque le navigateur de preuve) ; le
> miroir d'une image ne retourne que sa position ; la génération n'a pas
> été tirée (clé absente en données isolées — la route est l'existante).

**Goal :** poser des images dans un document du Vectorlab (Bibliothèque,
fichier, presse-papiers, génération), les rogner, les verrouiller, les
vectoriser par aplats de couleur avec aperçu ; des repères de fond perdu
et de zone sûre ; le pont Cartes dans l'autre sens (une face du Cardforge
s'ouvre dans le Vectorlab au format physique du jeu) ; un brouillon toutes
les 30 s restauré à l'ouverture.

**Architecture :** le modèle-document (`mod-doc.js`, pur) gagne l'objet
`image` (`href` vers un PNG stocké À CÔTÉ du JSON du document, jamais de
base64 dans le JSON — D1) et le champ optionnel `reperes` (D2) ; le
compilateur prend un résolveur d'`href` en option pour que l'écran, l'export
et le banc node partagent LA MÊME compilation. Le backend gagne un magasin
d'images par document (`<did>.img<n>.png`) et deux routes. Trois modules
UI nouveaux (`mod-image.js`, `mod-trace.js`, `mod-brouillon.js`) traduisent
les gestes en UNE commande via `VL.executer` ; leur logique pure est en
tête de fichier et bancable node (D9). La vectorisation est `imagetracerjs`
vendorisé (D6/D7 — licence Unlicense, domaine public : écart déclaré avec
le « MIT » du spec, encore plus permissif, zéro coût). Le Cardforge gagne
deux méthodes de transport dans son CORE (`CF.vector.update`,
`CF.vector.image` — la règle « aucun réseau nu dans une pièce » tient) et
un bouton dans la pièce Face.

**Tech Stack :** vanilla ESM, SVG-DOM, Canvas 2D (rasterisation client),
node 24 (banc `qa/run.mjs`), FastAPI + fichiers (vector_store), pytest
(`backend/tests/test_vector_docs.py`), imagetracerjs 1.2.6 vendorisé.

---

## Cartographie des fichiers

| Fichier | Rôle dans ce lot |
|---|---|
| `frontend/vectorlab/vendor/imagetracer_v1.2.6.js` (créer) + `LICENSE-imagetracerjs.txt` | vectoriseur vendorisé (T0) |
| `frontend/vectorlab/js/mod-doc.js` (modifier) | objet `image`, verrou d'objet, `fill-rule`, `reperes`, `compilerSVG(doc, opts)`, `op_vectoriser_poser` (T1, T2, T5) |
| `frontend/vectorlab/qa/image.test.mjs`, `reperes.test.mjs`, `trace.test.mjs`, `brouillon.test.mjs`, `image_ui.test.mjs` (créer) | bancs node RED d'abord |
| `backend/app/services/vector_store.py` (modifier) | `ecrire_image / lire_image / lister_images / copier_images` (T3) |
| `backend/app/api/routes.py` (modifier, bloc Vectorlab ~l. 6251-6560) | `POST/GET /vector/docs/{id}/images[/{name}]`, duplicate copie les images (T3) |
| `backend/tests/test_vector_docs.py` (modifier) | miroirs pytest (T3, T7, T8) |
| `frontend/vectorlab/js/mod-image.js` (créer) | pose (4 sources), panneau Image (rognage, verrou, vectoriser), panneau Repères, résolution d'`href`, inline pour l'export (T4) |
| `frontend/vectorlab/js/core.js` (modifier) | rendu avec résolveur d'images, overlay des repères, aimantation aux repères, hooks `surCharge`/`surSauve`, init des modules (T4, T6) |
| `frontend/vectorlab/js/mod-export.js` (modifier) | `svgCourant` async avec images inlinées en `data:` (T4) |
| `frontend/vectorlab/index.html`, `vectorlab.css` (modifier) | menu « Image ▾ », panneaux Image / Repères, dialogue Vectoriser, script vendor (T4, T5) |
| `frontend/vectorlab/js/mod-trace.js` (créer) | `options_trace`, `definition_trace`, `tracedata_vers_objets` (purs) + dialogue d'aperçu (T5) |
| `frontend/vectorlab/js/mod-brouillon.js` (créer) | `brouillon_*` purs + minuteur 30 s + restauration (T6) |
| `frontend/cardforge/js/core.js` (modifier) | `CF.vector.update`, `CF.vector.image` (T7) |
| `frontend/cardforge/js/mod-face.js` (modifier, §3-ter) | bouton « Éditer cette face dans le Vectorlab », `docFaceVec` (T7) |

Contrat de l'objet `image` (D2, champs optionnels, un doc v1 s'ouvre inchangé) :

```json
{ "id": "o1", "type": "image", "x": 0, "y": 0, "w": 815, "h": 1110,
  "href": "img1.png", "nat": { "w": 815, "h": 1110 },
  "rognage": { "x": 0, "y": 0, "w": 815, "h": 1110 },
  "verrou": true, "style": { "opacite": 0.8 } }
```

- `href` : nom relatif d'un PNG du magasin du document (`img<n>.png`), ou
  une URL absolue (`data:`, `blob:`, `http(s):`, `/…`) — le résolveur ne
  touche que les noms relatifs ;
- `nat` : taille native en px de l'image (mesurée au dépôt) ;
- `rognage` : fenêtre en px NATIFS de l'image (absent = image entière) ;
- `verrou` : l'objet est ignoré par toutes les commandes de sélection
  (`_objetsCibles`) — seule `op_image_verrou` le rend ;
- `style.opacite` : la seule clé de style qui compte pour une image.

Compilation (uniforme, avec ou sans rognage) :

```html
<g data-objet="o1" data-verrou="1" fill="none" opacity="0.8">
  <svg x="0" y="0" width="815" height="1110" viewBox="0 0 815 1110" preserveAspectRatio="none">
    <image x="0" y="0" width="815" height="1110" href="/api/vector/docs/<did>/images/img1.png" preserveAspectRatio="none"/>
  </svg>
</g>
```

Contrat de `reperes` : `{ "fondPerdu": [ox, oy], "zoneSure": [ox, oy] }` —
retraits en px document depuis le bord de la page, chaque clé optionnelle.
Rectangles dérivés : `fondPerdu` = `{x: ox, y: oy, w: W-2ox, h: H-2oy}` (la
ligne de COUPE — tout ce qui est hors d'elle est le fond perdu), `zoneSure`
idem. Dessinés dans l'overlay (jamais exportés), aimantants.

---

## Task 0 : vendoriser imagetracerjs

**Files :**
- Create : `frontend/vectorlab/vendor/imagetracer_v1.2.6.js`, `frontend/vectorlab/vendor/LICENSE-imagetracerjs.txt`
- Modify : `frontend/vectorlab/vendor/package.json`

- [ ] **Step 1 : télécharger le fichier et sa licence**

```bash
cd frontend/vectorlab/vendor
curl -sL -o imagetracer_v1.2.6.js https://cdn.jsdelivr.net/npm/imagetracerjs@1.2.6/imagetracer_v1.2.6.js
curl -sL -o LICENSE-imagetracerjs.txt https://cdn.jsdelivr.net/npm/imagetracerjs@1.2.6/LICENSE
wc -c imagetracer_v1.2.6.js LICENSE-imagetracerjs.txt
head -c 200 LICENSE-imagetracerjs.txt
```

Attendu : ~47 118 octets pour le js ; la licence commence par « This is free
and unencumbered software released into the public domain » (Unlicense). Si
le fichier LICENSE du paquet est absent (404), écrire dans
`LICENSE-imagetracerjs.txt` le bloc « The Unlicense / PUBLIC DOMAIN » qui
figure en tête du js lui-même (lignes 8-30), précédé de la ligne
`imagetracerjs 1.2.6 — https://github.com/jankovicsandras/imagetracerjs`.

- [ ] **Step 2 : vérifier le chargement node (CommonJS) et navigateur**

```bash
cd frontend/vectorlab && node -e "const T=require('./vendor/imagetracer_v1.2.6.js'); console.log(typeof T.imagedataToTracedata, T.versionnumber)"
```

Attendu : `function 1.2.6`. Le fichier finit par
`else if(typeof module !== 'undefined'){ module.exports = new ImageTracer(); }` ;
`vendor/package.json` est déjà `"type": "commonjs"` — mettre à jour sa
description :

```json
{
  "type": "commonjs",
  "description": "vendor UMD (martinez, imagetracerjs) : commonjs pour le require du banc node; le navigateur charge en script classique (window.martinez, window.ImageTracer)."
}
```

- [ ] **Step 3 : commit**

```bash
git add frontend/vectorlab/vendor
git commit --only frontend/vectorlab/vendor -m "vectorlab : imagetracerjs 1.2.6 vendorise (Unlicense) — la vectorisation sans GPU ni API (D6/D7)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 1 : modèle — l'objet `image`, le verrou d'objet, `fill-rule`, le résolveur d'href

**Files :**
- Modify : `frontend/vectorlab/js/mod-doc.js`
- Test : `frontend/vectorlab/qa/image.test.mjs`

- [ ] **Step 1 : écrire le banc RED**

```js
// image.test.mjs — l'objet `image` du lot A (D1/D2) : validation, compilation
// uniforme <g><svg viewBox><image/></svg></g>, résolveur d'href, rognage,
// verrou d'objet ignoré par les commandes, fill-rule. Aucun DOM.
import { parserDoc, compilerSVG, op_ajouter, op_deplacer, op_redimensionner,
         op_supprimer, op_miroir, op_style, op_dupliquer,
         op_image_rogner, op_image_verrou } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const clone = (d) => JSON.parse(JSON.stringify(d));
const base = () => ({
  v: 1, nom: "Images", taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }],
});
const img = (sur = {}) => ({ id: "i1", type: "image", x: 10, y: 20, w: 200, h: 100,
  href: "img1.png", nat: { w: 800, h: 400 }, style: {}, ...sur });

/* ── validation ── */
{
  let refus = 0;
  for (const mauvais of [
    img({ href: "" }), img({ href: 42 }), img({ nat: null }),
    img({ nat: { w: 0, h: 5 } }), img({ w: 0 }),
    img({ rognage: { x: -1, y: 0, w: 10, h: 10 } }),
    img({ rognage: { x: 0, y: 0, w: 900, h: 10 } }),   // déborde nat
    img({ rognage: { x: 0, y: 0, w: 0, h: 10 } }),
  ]) {
    const d = base(); d.calques[0].objets.push(mauvais);
    try { parserDoc(d); } catch { refus++; }
  }
  ok("parserDoc refuse 8 images malformées", refus === 8, String(refus));
  const d = base(); d.calques[0].objets.push(img());
  let accepte = true;
  try { parserDoc(d); } catch (e) { accepte = false; }
  ok("parserDoc accepte une image bien formée", accepte);
  // dans un groupe aussi
  const g = base();
  g.calques[0].objets.push({ id: "g1", type: "groupe", style: {},
    enfants: [img({ href: "" })] });
  let refusG = false;
  try { parserDoc(g); } catch { refusG = true; }
  ok("parserDoc descend dans les groupes", refusG);
}

/* ── compilation : uniforme, href verbatim sans résolveur ── */
{
  const d = base(); d.calques[0].objets.push(img({ style: { opacite: 0.5 } }));
  const svg = compilerSVG(d);
  ok("image : <g data-objet> hôte", svg.includes('<g data-objet="i1"'), svg);
  ok("image : svg imbriqué à la boîte de l'objet et viewBox natif entier",
     svg.includes('<svg x="10" y="20" width="200" height="100" viewBox="0 0 800 400" preserveAspectRatio="none">'), svg);
  ok("image : <image> à la taille native, href VERBATIM sans résolveur",
     svg.includes('<image x="0" y="0" width="800" height="400" href="img1.png" preserveAspectRatio="none"/>'), svg);
  ok("image : l'opacité du style porte sur le <g>", svg.includes('opacity="0.5"'));
  ok("image : pas de data-verrou sans verrou", !svg.includes("data-verrou"));
  // résolveur
  const svg2 = compilerSVG(d, { image: (h) => "/api/vector/docs/abc/images/" + h });
  ok("résolveur d'href appliqué", svg2.includes('href="/api/vector/docs/abc/images/img1.png"'), svg2);
  // href échappé
  const e = base(); e.calques[0].objets.push(img({ href: 'a"b<c.png' }));
  ok("href échappé", compilerSVG(e).includes('href="a&quot;b&lt;c.png"'));
}

/* ── rognage ── */
{
  const d = base(); d.calques[0].objets.push(img());
  op_image_rogner(d, "i1", { x: 100, y: 50, w: 400, h: 200 });
  ok("op_image_rogner pose la fenêtre", JSON.stringify(d.calques[0].objets[0].rognage)
     === JSON.stringify({ x: 100, y: 50, w: 400, h: 200 }));
  ok("compilation : viewBox = rognage",
     compilerSVG(d).includes('viewBox="100 50 400 200"'), compilerSVG(d));
  op_image_rogner(d, "i1", null);
  ok("op_image_rogner(null) retire la fenêtre", d.calques[0].objets[0].rognage === undefined);
  let refus = 0;
  for (const r of [{ x: -5, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 801, h: 10 },
                   { x: 0, y: 0, w: 0, h: 10 }, "x"]) {
    try { op_image_rogner(clone(d), "i1", r); } catch { refus++; }
  }
  ok("op_image_rogner refuse 4 fenêtres hors image", refus === 4, String(refus));
  const r = base(); r.calques[0].objets.push({ id: "r1", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} });
  let refusType = false;
  try { op_image_rogner(r, "r1", { x: 0, y: 0, w: 1, h: 1 }); } catch { refusType = true; }
  ok("op_image_rogner refuse un non-image", refusType);
}

/* ── verrou d'objet : l'état vide construit (rien verrouillé) puis le verrou ── */
{
  const d = base();
  d.calques[0].objets.push(img(), img({ id: "i2", x: 300 }));
  op_deplacer(d, ["i1", "i2"], 5, 5);
  ok("sans verrou, les deux images bougent (négation démasquée)",
     d.calques[0].objets[0].x === 15 && d.calques[0].objets[1].x === 305);
  op_image_verrou(d, "i1", true);
  ok("op_image_verrou pose verrou:true", d.calques[0].objets[0].verrou === true);
  ok("compilation : data-verrou", compilerSVG(d).includes('data-verrou="1"'));
  op_deplacer(d, ["i1", "i2"], 5, 5);
  ok("l'image verrouillée ne bouge pas, l'autre si",
     d.calques[0].objets[0].x === 15 && d.calques[0].objets[1].x === 310);
  op_redimensionner(d, ["i1"], { x: 15, y: 25, w: 200, h: 100 }, { x: 0, y: 0, w: 50, h: 50 });
  ok("verrouillée : pas de redimensionnement", d.calques[0].objets[0].w === 200);
  op_style(d, ["i1"], { opacite: 0.2 });
  ok("verrouillée : pas de style", d.calques[0].objets[0].style.opacite === undefined);
  const n = op_supprimer(d, ["i1"]);
  ok("verrouillée : pas de suppression", n === 0 && d.calques[0].objets.length === 2);
  op_image_verrou(d, "i1", false);
  ok("déverrouiller retire la clé", d.calques[0].objets[0].verrou === undefined);
  op_deplacer(d, ["i1"], 1, 0);
  ok("déverrouillée : elle bouge à nouveau", d.calques[0].objets[0].x === 16);
}

/* ── géométrie : miroir, redimensionnement, duplication ── */
{
  const d = base(); d.calques[0].objets.push(img());
  op_redimensionner(d, ["i1"], { x: 10, y: 20, w: 200, h: 100 }, { x: 0, y: 0, w: 100, h: 50 });
  const o = d.calques[0].objets[0];
  ok("redimensionner mappe x,y,w,h", o.x === 0 && o.y === 0 && o.w === 100 && o.h === 50, JSON.stringify(o));
  op_miroir(d, ["i1"], "h", { x: 0, y: 0, w: 400, h: 300 });
  ok("miroir h : position réfléchie (pixels non retournés — écart dit)", o.x === 300 && o.w === 100);
  const ids = op_dupliquer(d, ["i1"], 3, 3);
  const c = d.calques[0].objets.find((x) => x.id === ids[0]);
  ok("dupliquer : clone décalé, même href", c && c.href === "img1.png" && c.x === 303);
  const a = op_ajouter(base(), "c1", img({ id: undefined }));
  ok("op_ajouter accepte une image", a === "o1");
}

/* ── fill-rule (la vectorisation en a besoin pour les trous) ── */
{
  const d = base();
  d.calques[0].objets.push({ id: "p", type: "path", d: "M 0 0 L 10 0 L 10 10 Z",
    style: { fond: "#112233", regle: "evenodd" } });
  ok("style.regle → fill-rule", compilerSVG(d).includes('fill-rule="evenodd"'));
  d.calques[0].objets[0].style = { fond: "#112233" };
  ok("sans regle, pas de fill-rule", !compilerSVG(d).includes("fill-rule"));
}

if (echecs.length) {
  console.error("ECHECS image :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA image : PASS (33 controles)");
```

- [ ] **Step 2 : constater le RED**

```bash
cd frontend/vectorlab && node qa/image.test.mjs
```

Attendu : `SyntaxError: The requested module '../js/mod-doc.js' does not
provide an export named 'op_image_rogner'`.

- [ ] **Step 3 : implémenter dans `mod-doc.js`**

Dans `parserDoc`, après la boucle des calques (l. 16-19), ajouter la
validation récursive des images :

```js
  for (const c of doc.calques) _validerObjets(c.objets, c.id);
```

et, au-dessus de `parserDoc`, la fonction :

```js
/* ── lot A (D1/D2) : l'objet `image` — href RELATIF (nom du PNG stocké à
   côté du JSON du document, jamais de base64) ou URL absolue ; `nat` =
   taille native ; `rognage` = fenêtre en px NATIFS ; `verrou` = ignoré
   par toutes les commandes de sélection. */
function _validerRognage(r, nat, ou) {
  if (!r || typeof r !== "object") throw new Error(`${ou}: rognage {x,y,w,h}`);
  const { x, y, w, h } = r;
  if (!(x >= 0) || !(y >= 0) || !(w > 0) || !(h > 0)
      || x + w > nat.w + 1e-6 || y + h > nat.h + 1e-6) {
    throw new Error(`${ou}: rognage hors de l'image native`);
  }
}
function _validerObjets(objs, ou) {
  for (const o of objs) {
    if (o.type === "image") {
      if (typeof o.href !== "string" || !o.href) throw new Error(`image ${o.id}: href requis`);
      if (!o.nat || !(o.nat.w > 0) || !(o.nat.h > 0)) throw new Error(`image ${o.id}: nat {w,h} positif requis`);
      if (!(o.w > 0) || !(o.h > 0)) throw new Error(`image ${o.id}: taille positive requise`);
      if (o.rognage !== undefined) _validerRognage(o.rognage, o.nat, `image ${o.id}`);
    }
    if (o.type === "groupe") _validerObjets(o.enfants || [], ou);
  }
}
```

Dans `styleAttrs`, avant le `return out;` :

```js
  if (s.regle) out += ` fill-rule="${escAttr(s.regle)}"`;
```

Dans `compilerObjet`, un cas avant `default:` :

```js
    case "image": {
      const url = (ctx.image || ((h) => h))(o.href);
      const nat = o.nat;
      const r = o.rognage || { x: 0, y: 0, w: nat.w, h: nat.h };
      const verrou = o.verrou ? ` data-verrou="1"` : "";
      return `<g${t}${verrou}${st}${tr}>`
        + `<svg x="${+o.x}" y="${+o.y}" width="${+o.w}" height="${+o.h}"`
        + ` viewBox="${+r.x} ${+r.y} ${+r.w} ${+r.h}" preserveAspectRatio="none">`
        + `<image x="0" y="0" width="${+nat.w}" height="${+nat.h}"`
        + ` href="${escAttr(url)}" preserveAspectRatio="none"/>`
        + `</svg></g>`;
    }
```

Dans `_objetsCibles`, ignorer les objets verrouillés :

```js
      if (voulu.has(c.objets[i].id) && !c.objets[i].verrou) {
        yield { calque: c, objet: c.objets[i], i };
      }
```

Dans `_decalerObjet` et `_mapperObjet`, traiter `image` comme `rect` :
`case "rect": case "image":` (mêmes lignes). Dans `op_miroir` : `case "rect": case "image":`
(position seule — les pixels ne se retournent pas, comme le texte : écart dit
en commentaire).

Ajouter, après `op_rect_rayon` :

```js
/* ── image (lot A) : rognage et verrou d'objet. Ces deux commandes
   trouvent l'objet SANS passer par _objetsCibles — le verrou doit pouvoir
   se retirer. Rognage en px natifs, borné à l'image ; null = entière. */
function _trouverImage(doc, id) {
  for (const c of doc.calques) {
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "image") throw new Error(`objet ${id}: pas une image`);
      return o;
    }
  }
  throw new Error(`image introuvable: ${id}`);
}

export function op_image_rogner(doc, id, rognage) {
  const o = _trouverImage(doc, id);
  if (rognage === null || rognage === undefined) { delete o.rognage; return; }
  _validerRognage(rognage, o.nat, `image ${id}`);
  o.rognage = { x: +rognage.x, y: +rognage.y, w: +rognage.w, h: +rognage.h };
}

export function op_image_verrou(doc, id, verrou) {
  const o = _trouverImage(doc, id);
  if (verrou) o.verrou = true; else delete o.verrou;
}
```

Et `compilerSVG(doc)` devient `compilerSVG(doc, opts = {})` avec
`const ctx = { degrades: doc.degrades || {}, image: opts.image };`.

- [ ] **Step 4 : GREEN et non-régression**

```bash
cd frontend/vectorlab && node qa/image.test.mjs && node qa/run.mjs
```

Attendu : `QA image : PASS (33 controles)` puis `QA vectorlab : tous les
bancs sont passes.` (le snapshot ne change pas : aucune image, aucune
`regle` dans son document).

- [ ] **Step 5 : commit**

```bash
git add frontend/vectorlab/js/mod-doc.js frontend/vectorlab/qa/image.test.mjs
git commit --only frontend/vectorlab/js/mod-doc.js frontend/vectorlab/qa/image.test.mjs -m "vectorlab : l'objet image du modele — href relatif, nat, rognage, verrou d'objet, resolveur d'href, fill-rule (lot A, T1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 2 : modèle — les repères de fond perdu et de zone sûre

**Files :**
- Modify : `frontend/vectorlab/js/mod-doc.js`
- Test : `frontend/vectorlab/qa/reperes.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// reperes.test.mjs — doc.reperes {fondPerdu:[ox,oy], zoneSure:[ox,oy]} :
// validation, rectangles dérivés, guides d'aimantation, commande op_reperes.
// L'état VIDE est construit d'abord : sans repères, rects nuls et guides vides.
import { parserDoc, compilerSVG, op_reperes, reperes_rects, reperes_guides }
  from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const base = () => ({ v: 1, nom: "R", taille: { w: 400, h: 300 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] });

{
  const d = base();
  const r = reperes_rects(d);
  ok("état vide : deux rects nuls", r.fondPerdu === null && r.zoneSure === null, JSON.stringify(r));
  const g = reperes_guides(d);
  ok("état vide : guides vides", g.v.length === 0 && g.h.length === 0);
}
{
  const d = base();
  op_reperes(d, { fondPerdu: [12, 12], zoneSure: [30, 25] });
  ok("op_reperes pose les deux", JSON.stringify(d.reperes)
     === JSON.stringify({ fondPerdu: [12, 12], zoneSure: [30, 25] }), JSON.stringify(d.reperes));
  const r = reperes_rects(d);
  ok("rect fond perdu = ligne de coupe", JSON.stringify(r.fondPerdu)
     === JSON.stringify({ x: 12, y: 12, w: 376, h: 276 }), JSON.stringify(r));
  ok("rect zone sûre", JSON.stringify(r.zoneSure)
     === JSON.stringify({ x: 30, y: 25, w: 340, h: 250 }));
  const g = reperes_guides(d);
  ok("guides : 4 verticaux, 4 horizontaux, triés",
     JSON.stringify(g.v) === JSON.stringify([12, 30, 370, 388])
     && JSON.stringify(g.h) === JSON.stringify([12, 25, 275, 288]), JSON.stringify(g));
  ok("parserDoc accepte", (() => { try { parserDoc(d); return true; } catch { return false; } })());
  ok("les repères ne sont JAMAIS compilés", !compilerSVG(d).includes("repere")
     && !compilerSVG(d).includes('x="12" y="12" width="376"'));
  // un nombre = retrait uniforme
  op_reperes(d, { zoneSure: 40 });
  ok("un nombre pose [n,n]", JSON.stringify(d.reperes.zoneSure) === "[40,40]");
  // null retire la clé ; la dernière clé retirée retire doc.reperes
  op_reperes(d, { zoneSure: null });
  ok("null retire une clé", d.reperes.zoneSure === undefined && d.reperes.fondPerdu);
  op_reperes(d, { fondPerdu: null });
  ok("plus rien → doc.reperes disparaît", d.reperes === undefined);
}
{
  let refus = 0;
  for (const p of [{ fondPerdu: [-1, 0] }, { fondPerdu: [300, 0] },   // ≥ W/2
                   { zoneSure: "x" }, { inconnu: 3 }, { fondPerdu: [1] }]) {
    try { op_reperes(base(), p); } catch { refus++; }
  }
  ok("op_reperes refuse 5 patchs invalides", refus === 5, String(refus));
  let refusDoc = 0;
  for (const r of [{ fondPerdu: [200, 0] }, { zoneSure: 5 }, [1, 2], { bidon: [1, 1] }]) {
    const d = base(); d.reperes = r;
    try { parserDoc(d); } catch { refusDoc++; }
  }
  ok("parserDoc refuse 4 reperes malformés", refusDoc === 4, String(refusDoc));
}

if (echecs.length) {
  console.error("ECHECS reperes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA reperes : PASS (13 controles)");
```

- [ ] **Step 2 : RED**

```bash
cd frontend/vectorlab && node qa/reperes.test.mjs
```

Attendu : `does not provide an export named 'op_reperes'`.

- [ ] **Step 3 : implémenter**

Dans `parserDoc`, après la validation de `palette` :

```js
  if (doc.reperes !== undefined) _validerReperes(doc.reperes, doc.taille);
```

Après `op_guide_supprimer`, ajouter :

```js
/* ── repères de page (lot A) : fond perdu et zone sûre — retraits [ox, oy]
   en px document depuis les bords. Dessinés par l'overlay (jamais
   compilés), aimantants (reperes_guides). Un nombre = retrait uniforme. */
const _CLES_REPERES = ["fondPerdu", "zoneSure"];

function _validerReperes(r, taille) {
  if (!r || typeof r !== "object" || Array.isArray(r)) {
    throw new Error("document: reperes {fondPerdu?, zoneSure?}");
  }
  for (const k of Object.keys(r)) {
    if (!_CLES_REPERES.includes(k)) throw new Error(`reperes: clé inconnue ${k}`);
    const v = r[k];
    if (!Array.isArray(v) || v.length !== 2 || !(v[0] >= 0) || !(v[1] >= 0)
        || v[0] >= taille.w / 2 || v[1] >= taille.h / 2) {
      throw new Error(`reperes.${k}: [ox, oy] ≥ 0 et sous la demi-page`);
    }
  }
}

export function op_reperes(doc, patch) {
  if (!patch || typeof patch !== "object") throw new Error("reperes: patch requis");
  const r = { ...(doc.reperes || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (!_CLES_REPERES.includes(k)) throw new Error(`reperes: clé inconnue ${k}`);
    if (v === null || v === undefined) { delete r[k]; continue; }
    r[k] = typeof v === "number" ? [v, v] : v;
  }
  _validerReperes(r, doc.taille);
  if (Object.keys(r).length) doc.reperes = r; else delete doc.reperes;
}

export function reperes_rects(doc) {
  const out = { fondPerdu: null, zoneSure: null };
  const r = doc.reperes || {};
  const W = +doc.taille.w, H = +doc.taille.h;
  for (const k of _CLES_REPERES) {
    if (r[k]) out[k] = { x: r[k][0], y: r[k][1], w: W - 2 * r[k][0], h: H - 2 * r[k][1] };
  }
  return out;
}

export function reperes_guides(doc) {
  const v = [], h = [];
  const rects = reperes_rects(doc);
  for (const k of _CLES_REPERES) {
    const b = rects[k];
    if (b) { v.push(b.x, b.x + b.w); h.push(b.y, b.y + b.h); }
  }
  return { v: [...new Set(v)].sort((a, b) => a - b), h: [...new Set(h)].sort((a, b) => a - b) };
}
```

- [ ] **Step 4 : GREEN**

```bash
cd frontend/vectorlab && node qa/reperes.test.mjs && node qa/run.mjs
```

- [ ] **Step 5 : commit**

```bash
git commit --only frontend/vectorlab/js/mod-doc.js frontend/vectorlab/qa/reperes.test.mjs -m "vectorlab : reperes de fond perdu et de zone sure dans le modele — rects derives, guides aimantants, jamais compiles (lot A, T2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 3 : backend — le magasin d'images du document et ses routes

**Files :**
- Modify : `backend/app/services/vector_store.py`
- Modify : `backend/app/api/routes.py` (après `get_vector_vignette`, ~l. 6552 ; et `duplicate_vector_doc`)
- Test : `backend/tests/test_vector_docs.py`

- [ ] **Step 1 : tests RED (magasin puis routes) — ajouter avant la section « miroirs »**

```python
# ── N. lot A : le magasin d'IMAGES du document (D1 — jamais de base64) ──────

_PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d"
    "4944415478da63f8ffff3f0300050001ff2a5d2b0000000049454e44ae426082")


def test_le_magasin_d_images_du_document():
    from app.services import vector_store as VS
    did = VS.creer(_doc("Avec image"))
    # état vide construit : aucune image, la lecture rend None, la liste []
    assert VS.lister_images(did) == []
    assert VS.lire_image(did, "img1.png") is None
    n1 = VS.ecrire_image(did, _PNG_1PX)
    n2 = VS.ecrire_image(did, _PNG_1PX + b"x")
    assert (n1, n2) == ("img1.png", "img2.png")
    dossier = pathlib.Path(os.environ["VECTOR_FOLDER"])
    assert (dossier / f"{did}.img1.png").read_bytes() == _PNG_1PX
    assert VS.lire_image(did, "img2.png") == _PNG_1PX + b"x"
    assert VS.lister_images(did) == ["img1.png", "img2.png"]
    # noms hors patron : refusés sans toucher le disque
    for mauvais in ("../x.png", "img1.jpg", "autre.png", "img.png", ""):
        assert VS.lire_image(did, mauvais) is None
    # la copie (socle de « dupliquer ») emporte les images
    dst = VS.creer(_doc("copie"))
    VS.copier_images(did, dst)
    assert VS.lister_images(dst) == ["img1.png", "img2.png"]
    assert VS.lire_image(dst, "img1.png") == _PNG_1PX
    # un doc sans image : la copie est un no-op silencieux
    vide = VS.creer(_doc("vide"))
    VS.copier_images(vide, dst)
    assert VS.lister_images(dst) == ["img1.png", "img2.png"]
    # document inconnu : refus parlant
    import pytest
    with pytest.raises(FileNotFoundError):
        VS.ecrire_image("inexistant", _PNG_1PX)


def test_les_routes_images_du_document():
    import asyncio
    from httpx import AsyncClient, ASGITransport

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/vector/docs", json={"name": "Img", "role": "libre",
                                                       "doc": _doc()})
            did = r.json()["id"]
            # pas un PNG → 400 ; doc inconnu → 404
            r = await c.post(f"/api/vector/docs/{did}/images", content=b"GIF89a",
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 400 and "PNG" in r.json()["detail"]
            r = await c.post("/api/vector/docs/nope/images", content=_PNG_1PX,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 404
            # dépôt → nom stable, servi en image/png
            r = await c.post(f"/api/vector/docs/{did}/images", content=_PNG_1PX,
                             headers={"Content-Type": "image/png"})
            assert r.status_code == 200 and r.json() == {"name": "img1.png"}
            r = await c.get(f"/api/vector/docs/{did}/images/img1.png")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("image/png")
            assert r.content == _PNG_1PX
            # nom hors patron ou absent → 404 (jamais le catch-all SPA en 200)
            for mauvais in ("img9.png", "x.png", "..%2Fimg1.png"):
                r = await c.get(f"/api/vector/docs/{did}/images/{mauvais}")
                assert r.status_code == 404, mauvais
            # le document qui RÉFÉRENCE l'image se sauve et se relit tel quel
            doc = _doc()
            doc["calques"][0]["objets"].append(
                {"id": "o1", "type": "image", "x": 0, "y": 0, "w": 640, "h": 960,
                 "href": "img1.png", "nat": {"w": 1, "h": 1}, "verrou": True})
            doc["reperes"] = {"fondPerdu": [10, 10], "zoneSure": [30, 30]}
            r = await c.put(f"/api/vector/docs/{did}", json={"doc": doc})
            assert r.status_code == 200 and r.json()["version"] == 2
            r = await c.get(f"/api/vector/docs/{did}")
            assert r.json()["doc"]["calques"][0]["objets"][0]["href"] == "img1.png"
            assert r.json()["doc"]["reperes"]["zoneSure"] == [30, 30]
            # dupliquer emporte les images : la copie sert img1.png
            r = await c.post(f"/api/vector/docs/{did}/duplicate", json={})
            nid = r.json()["id"]
            r = await c.get(f"/api/vector/docs/{nid}/images/img1.png")
            assert r.status_code == 200 and r.content == _PNG_1PX
            # supprimer archive le JSON ; les images restent (dit dans le service)
            r = await c.delete(f"/api/vector/docs/{did}")
            assert r.status_code == 200
            from app.services import vector_store as VS
            assert VS.lire_image(did, "img1.png") == _PNG_1PX

    asyncio.run(scenario())
```

Vérifier d'abord comment les tests existants de routes obtiennent l'app
(l. 109-130 : `from app.main import app`, `init_db`) et copier exactement
leur amorce si elle diffère de ce qui précède.

- [ ] **Step 2 : RED**

```powershell
$py = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend; & $py -m pytest tests/test_vector_docs.py -q -k "images" 2>&1 | Select-Object -Last 15
```

Attendu : `AttributeError: module 'app.services.vector_store' has no attribute 'lister_images'`.

- [ ] **Step 3 : implémenter le magasin (`vector_store.py`, après `copier_vignette`)**

```python
# ── lot A (D1) : les IMAGES du document — `<did>.img<n>.png` à côté du JSON,
# jamais de base64 dans le document. Le nom rendu (`img<n>.png`) est ce que
# l'objet `image` du modèle porte en `href`. Le magasin stocke des octets ;
# le magic PNG se vérifie à la ROUTE. La suppression du document (archive)
# LAISSE les images : l'archive `.v<n>.json` les référence encore.
_NOM_IMAGE = re.compile(r"img([0-9]+)\.png")


def _numeros_images(did: str, d: Path) -> list[int]:
    out = []
    for p in d.glob(f"{did}.img*.png"):
        m = re.fullmatch(re.escape(did) + r"\.img([0-9]+)\.png", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def lister_images(did: str) -> list[str]:
    return [f"img{n}.png" for n in _numeros_images(did, _dossier())]


def ecrire_image(did: str, octets: bytes) -> str:
    d = _dossier()
    if not (d / f"{did}.json").is_file():
        raise FileNotFoundError(did)
    nums = _numeros_images(did, d)
    n = (nums[-1] + 1) if nums else 1
    nom = f"img{n}.png"
    tmp = d / f"{did}.{nom}.tmp"
    tmp.write_bytes(octets)
    os.replace(tmp, d / f"{did}.{nom}")
    return nom


def lire_image(did: str, nom: str):
    if not _NOM_IMAGE.fullmatch(nom or ""):
        return None
    p = _dossier() / f"{did}.{nom}"
    return p.read_bytes() if p.is_file() else None


def copier_images(src: str, dst: str) -> None:
    """Socle de « dupliquer » : la copie emporte les images sous les MÊMES
    noms (les href du JSON copié restent valides) — no-op sans image."""
    d = _dossier()
    for nom in lister_images(src):
        octets = (d / f"{src}.{nom}").read_bytes()
        tmp = d / f"{dst}.{nom}.tmp"
        tmp.write_bytes(octets)
        os.replace(tmp, d / f"{dst}.{nom}")
```

- [ ] **Step 4 : implémenter les routes (`routes.py`, après `get_vector_vignette`)**

```python
_VECTOR_IMAGE_MAX = 40 * 1024 * 1024


@router.post("/vector/docs/{doc_id}/images")
async def add_vector_image(doc_id: str, request: Request):
    """Lot A (D1) : corps binaire image/png — un calque image du document.
    Stocké `<id>.img<n>.png` à côté du JSON ; rend {name} que l'objet
    `image` porte en href. Jamais par /images/upload : la Library reste
    propre, et le fichier suit le document (duplication, transfert)."""
    from app.services import vector_store as VS
    from app.services.storage import VectorDoc, async_session_factory
    octets = await request.body()
    if not octets.startswith(_PNG_MAGIC):
        raise HTTPException(400, "image: un PNG est attendu")
    if len(octets) > _VECTOR_IMAGE_MAX:
        raise HTTPException(413, "image: 40 Mo au plus")
    async with async_session_factory() as session:
        if not await session.get(VectorDoc, doc_id):
            raise HTTPException(404, "Document introuvable")
    try:
        return {"name": VS.ecrire_image(doc_id, octets)}
    except FileNotFoundError:
        raise HTTPException(404, "Contenu du document introuvable")


@router.get("/vector/docs/{doc_id}/images/{name}")
async def get_vector_image(doc_id: str, name: str):
    from app.services import vector_store as VS
    octets = VS.lire_image(doc_id, name)
    if octets is None:
        raise HTTPException(404, "Image du document introuvable")
    return Response(content=octets, media_type="image/png")
```

Dans `duplicate_vector_doc`, juste après `VS.copier_vignette(doc_id, nid)` :

```python
        VS.copier_images(doc_id, nid)
```

- [ ] **Step 5 : GREEN, banc vector complet**

```powershell
Set-Location backend; & $py -m pytest tests/test_vector_docs.py -q 2>&1 | Select-Object -Last 5
```

Attendu : `24 passed` (22 + 2).

- [ ] **Step 6 : commit**

```bash
git commit --only backend/app/services/vector_store.py backend/app/api/routes.py backend/tests/test_vector_docs.py -m "vectorlab : magasin d'images du document (<did>.img<n>.png) et routes POST/GET /vector/docs/{id}/images — jamais de base64 (lot A, T3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 4 : UI — poser, rogner, verrouiller ; repères ; export avec images

**Files :**
- Create : `frontend/vectorlab/js/mod-image.js`
- Test : `frontend/vectorlab/qa/image_ui.test.mjs`
- Modify : `frontend/vectorlab/js/core.js`, `mod-export.js`, `index.html`, `vectorlab.css`

- [ ] **Step 1 : banc RED de la logique pure de `mod-image.js`**

```js
// image_ui.test.mjs — la logique PURE de mod-image (résolution d'href,
// pose ajustée à la page, normalisation du rognage, hrefs d'un document,
// liste de la Bibliothèque de repli). initImage n'est jamais importé.
import { href_est_absolu, image_url, image_poser_spec, rognage_normaliser,
         image_hrefs, libListeHTML } from "../js/mod-image.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

ok("absolu : data/blob/http/https//", ["data:x", "blob:x", "http://a", "https://a", "/api/x"]
   .every(href_est_absolu) && !href_est_absolu("img1.png") && !href_est_absolu(""));
ok("image_url résout un nom relatif dans le magasin du doc",
   image_url("ab c", "img1.png") === "/api/vector/docs/ab%20c/images/img1.png",
   image_url("ab c", "img1.png"));
ok("image_url laisse l'absolu", image_url("d", "/api/images/x.png") === "/api/images/x.png");

{
  const s = image_poser_spec({ w: 1600, h: 800 }, { w: 400, h: 300 });
  ok("pose : contenue dans la page, centrée, ratio gardé",
     s.w === 400 && s.h === 200 && s.x === 0 && s.y === 50, JSON.stringify(s));
  const p = image_poser_spec({ w: 100, h: 50 }, { w: 400, h: 300 });
  ok("pose : une petite image garde sa taille native, centrée",
     p.w === 100 && p.h === 50 && p.x === 150 && p.y === 125, JSON.stringify(p));
  let refus = 0;
  try { image_poser_spec({ w: 0, h: 5 }, { w: 4, h: 4 }); } catch { refus++; }
  ok("pose : taille native nulle refusée", refus === 1);
}
{
  const nat = { w: 800, h: 400 };
  ok("rognage entier → null", rognage_normaliser({ x: 0, y: 0, w: 800, h: 400 }, nat) === null);
  ok("rognage null → null", rognage_normaliser(null, nat) === null);
  const r = rognage_normaliser({ x: -10, y: 10, w: 900, h: 50.6 }, nat);
  ok("rognage borné à l'image, arrondi", JSON.stringify(r) === JSON.stringify({ x: 0, y: 10, w: 800, h: 51 }), JSON.stringify(r));
  const m = rognage_normaliser({ x: 799, y: 399, w: 0, h: 0 }, nat);
  ok("rognage : au moins 1 px", m.w === 1 && m.h === 1);
}
{
  const doc = { v: 1, taille: { w: 1, h: 1 }, calques: [
    { id: "c1", objets: [{ id: "a", type: "image", href: "img1.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 },
      { id: "g", type: "groupe", enfants: [{ id: "b", type: "image", href: "img2.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 },
        { id: "c", type: "image", href: "img1.png", nat: { w: 1, h: 1 }, x: 0, y: 0, w: 1, h: 1 }] }] },
    { id: "c2", objets: [{ id: "r", type: "rect", x: 0, y: 0, w: 1, h: 1 }] }] };
  ok("image_hrefs : uniques, dans l'ordre, groupes compris",
     JSON.stringify(image_hrefs(doc)) === JSON.stringify(["img1.png", "img2.png"]));
  ok("image_hrefs : état vide → []", image_hrefs({ calques: [{ id: "c", objets: [] }] }).length === 0);
}
{
  const h = libListeHTML([{ filename: "a<b>.png", width: 10, height: 20 }, { filename: "z.png" }], "");
  ok("libListeHTML échappe et porte le nom en data", h.includes("&lt;b&gt;") && h.includes('data-lib-nom="a&lt;b&gt;.png"'), h);
  ok("libListeHTML : vignette sur /api/images/<nom>", h.includes('src="/api/images/a%3Cb%3E.png"'), h);
  const v = libListeHTML([], "chat");
  ok("libListeHTML : état vide qui NOMME la recherche", v.includes("chat") && v.includes("Aucune image"), v);
  const f = libListeHTML([{ filename: "chat.png" }, { filename: "chien.png" }], "CHA");
  ok("libListeHTML filtre insensible à la casse", f.includes("chat.png") && !f.includes("chien.png"));
}

if (echecs.length) {
  console.error("ECHECS image_ui :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA image_ui : PASS (16 controles)");
```

- [ ] **Step 2 : RED** — `node qa/image_ui.test.mjs` → `Cannot find module '.../js/mod-image.js'`.

- [ ] **Step 3 : écrire `mod-image.js`**

```js
// mod-image.js — les IMAGES du Vectorlab (lot A, D1) : pose depuis la
// Bibliothèque (sélecteur __dzLibPicker du parent quand il existe, sinon
// une grille de repli sur /api/images), un fichier, le presse-papiers ou
// une génération ; rognage, verrou, opacité ; les repères de page. Le
// raster va au magasin du DOCUMENT (POST /vector/docs/<id>/images), jamais
// en base64 dans le JSON. La logique PURE est en tête (banc node) ;
// initImage ne touche le DOM qu'à l'appel.
import { op_ajouter, op_image_rogner, op_image_verrou, op_reperes,
         reperes_rects } from "./mod-doc.js";

/* ── pur ── */
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function href_est_absolu(h) {
  return /^(data:|blob:|https?:|\/)/.test(String(h || ""));
}

export function image_url(docId, href) {
  if (href_est_absolu(href)) return href;
  return `/api/vector/docs/${encodeURIComponent(docId)}/images/${encodeURIComponent(href)}`;
}

// la pose par défaut : contenue dans la page (jamais agrandie), centrée
export function image_poser_spec(nat, taille) {
  if (!(nat && nat.w > 0 && nat.h > 0)) throw new Error("image: taille native inconnue");
  const k = Math.min(1, taille.w / nat.w, taille.h / nat.h);
  const w = Math.max(1, Math.round(nat.w * k)), h = Math.max(1, Math.round(nat.h * k));
  return { x: Math.round((taille.w - w) / 2), y: Math.round((taille.h - h) / 2), w, h };
}

// borne une fenêtre à l'image ; null si elle couvre tout (= pas de rognage)
export function rognage_normaliser(r, nat) {
  if (!r) return null;
  const x = Math.min(nat.w - 1, Math.max(0, Math.round(+r.x || 0)));
  const y = Math.min(nat.h - 1, Math.max(0, Math.round(+r.y || 0)));
  const w = Math.max(1, Math.min(nat.w - x, Math.round(+r.w || 0)));
  const h = Math.max(1, Math.min(nat.h - y, Math.round(+r.h || 0)));
  if (x === 0 && y === 0 && w === nat.w && h === nat.h) return null;
  return { x, y, w, h };
}

export function image_hrefs(doc) {
  const out = [];
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.type === "image" && !out.includes(o.href)) out.push(o.href);
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  return out;
}

export function libListeHTML(images, q) {
  const f = String(q || "").toLowerCase();
  const vus = (images || []).filter((i) => !f || String(i.filename).toLowerCase().includes(f));
  if (!vus.length) {
    return `<p class="lib-vide">Aucune image${f ? ` pour « ${esc(q)} »` : " dans la Bibliothèque"}.</p>`;
  }
  return vus.map((i) => `<button class="lib-carte" data-lib-nom="${esc(i.filename)}"
    title="${esc(i.filename)}${i.width ? ` — ${i.width}×${i.height}` : ""}">
    <img src="/api/images/${encodeURIComponent(i.filename)}" alt="" loading="lazy"/>
    <span>${esc(i.filename)}</span></button>`).join("");
}

/* ── DOM ── */
export function initImage(VL) {
  const { $, etat } = VL;

  VL.imageUrl = (href) => image_url(etat.docId, href);

  async function deposer(png) {
    const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images`,
      { method: "POST", headers: { "Content-Type": "image/png" }, body: png });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d.name;
  }
  function decoder(blob) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(blob);
      const im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); res(im); };
      im.onerror = () => { URL.revokeObjectURL(url); rej(new Error("image illisible")); };
      im.src = url;
    });
  }
  // le magasin ne stocke que du PNG : tout autre format est ré-encodé ici
  async function versPNG(blob, im) {
    if (blob.type === "image/png") return blob;
    const cv = document.createElement("canvas");
    cv.width = im.naturalWidth; cv.height = im.naturalHeight;
    cv.getContext("2d").drawImage(im, 0, 0);
    return new Promise((res, rej) => cv.toBlob((b) => b ? res(b)
      : rej(new Error("ré-encodage PNG impossible")), "image/png"));
  }
  async function poserBlob(blob) {
    if (!etat.docId) throw new Error("aucun document ouvert");
    const im = await decoder(blob);
    const nat = { w: im.naturalWidth, h: im.naturalHeight };
    const png = await versPNG(blob, im);
    const href = await deposer(png);
    const spec = image_poser_spec(nat, etat.doc.taille);
    const id = VL.executer(op_ajouter, etat.calqueActif,
      { type: "image", ...spec, href, nat, style: {} });
    if (id) { VL.setOutil("select"); VL.setSelection([id]); }
    return id;
  }
  async function poserDepuisLibrary(nom) {
    const r = await fetch("/api/images/" + encodeURIComponent(nom));
    if (!r.ok) throw new Error(`Bibliothèque : ${nom} introuvable (${r.status})`);
    await poserBlob(await r.blob());
    VL.toast(`« ${nom} » posée`);
  }

  /* ── Bibliothèque : le sélecteur du parent, sinon la grille de repli ── */
  let libImages = null;
  async function ouvrirBiblio() {
    const parent = window.parent !== window ? window.parent : null;
    if (parent && typeof parent.__dzLibPicker === "function") {
      parent.__dzLibPicker({ titre: "Poser une image dans le Vectorlab" },
        (nom) => poserDepuisLibrary(nom).catch((e) => VL.toast(e.message, true)));
      return;
    }
    const dlg = $("#libDlg");
    dlg.classList.remove("hidden");
    $("#libRecherche").value = "";
    $("#libGrille").innerHTML = `<p class="lib-vide">chargement…</p>`;
    const d = await VL.api.get("/images");
    libImages = (d.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
    $("#libGrille").innerHTML = libListeHTML(libImages, "");
  }
  $("#libRecherche").addEventListener("input", () => {
    $("#libGrille").innerHTML = libListeHTML(libImages || [], $("#libRecherche").value);
  });
  $("#libGrille").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-lib-nom]");
    if (!b) return;
    $("#libDlg").classList.add("hidden");
    poserDepuisLibrary(b.dataset.libNom).catch((e) => VL.toast(e.message, true));
  });
  $("#libFermer").addEventListener("click", () => $("#libDlg").classList.add("hidden"));

  /* ── fichier ── */
  const inputFichier = $("#imgFichierInput");
  inputFichier.addEventListener("change", () => {
    const f = inputFichier.files && inputFichier.files[0];
    inputFichier.value = "";
    if (f) poserBlob(f).then(() => VL.toast(`« ${f.name} » posée`))
                       .catch((e) => VL.toast(e.message, true));
  });

  /* ── presse-papiers : Ctrl+V d'une image, et le bouton (clipboard.read) ── */
  document.addEventListener("paste", (ev) => {
    if (!etat.docId) return;
    if (/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName || "")) return;
    const items = [...((ev.clipboardData && ev.clipboardData.items) || [])];
    const it = items.find((i) => i.type.startsWith("image/"));
    if (!it) return;                       // pas une image : le coller interne garde la main
    ev.preventDefault();
    poserBlob(it.getAsFile()).then(() => VL.toast("image du presse-papiers posée"))
      .catch((e) => VL.toast(e.message, true));
  });
  async function collerImage() {
    if (!navigator.clipboard || !navigator.clipboard.read) {
      throw new Error("presse-papiers : utiliser Ctrl+V sur la scène");
    }
    for (const item of await navigator.clipboard.read()) {
      const t = item.types.find((x) => x.startsWith("image/"));
      if (t) { await poserBlob(await item.getType(t)); VL.toast("image du presse-papiers posée"); return; }
    }
    throw new Error("le presse-papiers ne contient pas d'image");
  }

  /* ── génération : la route existante, la clé dépensée est dite ── */
  async function generer() {
    const p = prompt("Décrire l'image à générer (dépense la clé du fournisseur des Réglages) :", "");
    if (!p) return;
    VL.toast("génération en cours…");
    const r = await fetch("/api/images/generate", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: p, n: 1, source: "vectorlab" }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    const nom = (d.images || [])[0];
    if (!nom) throw new Error("la génération n'a rendu aucune image");
    await poserDepuisLibrary(nom);
  }

  /* ── le menu ── */
  const menu = $("#imgMenu");
  $("#btnImage").addEventListener("click", () => menu.classList.toggle("hidden"));
  const garde = (fn) => () => {
    menu.classList.add("hidden");
    Promise.resolve().then(fn).catch((e) => VL.toast(e.message, true));
  };
  $("#imgBiblio").addEventListener("click", garde(ouvrirBiblio));
  $("#imgFichier").addEventListener("click", garde(() => inputFichier.click()));
  $("#imgColler").addEventListener("click", garde(collerImage));
  $("#imgGenerer").addEventListener("click", garde(generer));
  $("#imgVectoriser").addEventListener("click", garde(() => {
    if (VL.vectoriser) VL.vectoriser(imageCible());
  }));

  /* ── l'image cible d'une action : la sélection, sinon l'unique image ── */
  function imagesDuDoc() {
    const out = [];
    for (const c of etat.doc.calques) for (const o of c.objets) if (o.type === "image") out.push(o);
    return out;
  }
  function imageCible() {
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    if (t && t.objet.type === "image") return t.objet.id;
    const toutes = imagesDuDoc();
    if (toutes.length === 1) return toutes[0].id;
    if (!toutes.length) throw new Error("aucune image dans le document — Image ▾ pour en poser une");
    const rep = prompt("Quelle image ?\n" + toutes.map((o, i) =>
      `${i + 1}) ${o.id} — ${o.href} (${o.nat.w}×${o.nat.h})`).join("\n"), "1");
    if (rep === null) throw new Error("annulé");
    const o = toutes[(+rep || 0) - 1];
    if (!o) throw new Error("numéro inconnu");
    return o.id;
  }

  /* ── panneau Image (sélection unique d'une image) ── */
  const hote = $("#panneauImage"), tete = $("#teteImage");
  function rendrePanneauImage() {
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    const o = t && t.objet.type === "image" ? t.objet : null;
    tete.hidden = !o; hote.hidden = !o;
    if (!o) { hote.innerHTML = ""; return; }
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    hote.innerHTML = `
      <div class="ap-ligne"><span>Source</span><i class="img-src" title="${esc(o.href)}">${esc(o.href)} · ${o.nat.w}×${o.nat.h}</i></div>
      <div class="ap-ligne"><span>Rogner</span>
        <input type="number" id="imRx" min="0" value="${r.x}" title="X de la fenêtre (px de l'image)"/>
        <input type="number" id="imRy" min="0" value="${r.y}" title="Y de la fenêtre"/></div>
      <div class="ap-ligne"><span></span>
        <input type="number" id="imRw" min="1" value="${r.w}" title="Largeur de la fenêtre"/>
        <input type="number" id="imRh" min="1" value="${r.h}" title="Hauteur de la fenêtre"/>
        <button id="imRognerRaz" title="Image entière">↺</button></div>
      <div class="ap-ligne"><span>Verrou</span>
        <button id="imVerrou" class="${o.verrou ? "actif" : ""}" title="Verrouillé : aucune commande ne bouge, ne redimensionne ni ne supprime l'image">${o.verrou ? "🔒 verrouillée" : "🔓 libre"}</button>
        <button id="imVectoriser" title="Vectoriser cette image en aplats de couleur (aperçu avant validation)">Vectoriser…</button></div>`;
    const lireRognage = () => rognage_normaliser({ x: +$("#imRx").value, y: +$("#imRy").value,
      w: +$("#imRw").value, h: +$("#imRh").value }, o.nat);
    for (const id of ["imRx", "imRy", "imRw", "imRh"]) {
      $("#" + id).addEventListener("change", () => VL.executer(op_image_rogner, o.id, lireRognage()));
    }
    $("#imRognerRaz").addEventListener("click", () => VL.executer(op_image_rogner, o.id, null));
    $("#imVerrou").addEventListener("click", () => VL.executer(op_image_verrou, o.id, !o.verrou));
    $("#imVectoriser").addEventListener("click", () => { if (VL.vectoriser) VL.vectoriser(o.id); });
  }

  /* ── panneau Repères : deux retraits uniformes dans l'unité d'affichage ── */
  const hoteRep = $("#panneauReperes");
  function rendrePanneauReperes() {
    if (!etat.doc) { hoteRep.innerHTML = ""; return; }
    const r = etat.doc.reperes || {};
    const nv = (v) => v === undefined ? "" : Math.round(VL.versUnite(v[0]) * 100) / 100;
    const suf = VL.unites().affichage;
    hoteRep.innerHTML = `
      <div class="ap-ligne"><span>Coupe</span>
        <input type="number" id="repFond" step="any" min="0" value="${nv(r.fondPerdu)}" placeholder="—"
               title="Fond perdu : retrait de la ligne de coupe depuis le bord (${suf}) — vide = aucun"/>
        <i class="rep-pastille rep-fond"></i></div>
      <div class="ap-ligne"><span>Zone sûre</span>
        <input type="number" id="repSure" step="any" min="0" value="${nv(r.zoneSure)}" placeholder="—"
               title="Zone sûre : retrait depuis le bord (${suf}) — vide = aucune"/>
        <i class="rep-pastille rep-sure"></i></div>`;
    const lire = (id) => { const v = $("#" + id).value.trim(); return v === "" ? null : VL.depuisUnite(+v); };
    $("#repFond").addEventListener("change", () => VL.executer(op_reperes, { fondPerdu: lire("repFond") }));
    $("#repSure").addEventListener("change", () => VL.executer(op_reperes, { zoneSure: lire("repSure") }));
  }

  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendrePanneauImage(); rendrePanneauReperes(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneauImage(); };
  VL.poserBlob = poserBlob;                 // la preuve et la vectorisation
  VL.reperesRects = () => reperes_rects(etat.doc);
}
```

- [ ] **Step 4 : GREEN du banc pur** — `node qa/image_ui.test.mjs` → `PASS (16 controles)`.

- [ ] **Step 5 : `core.js` — rendu, overlay, aimantation, hooks**

Imports : ajouter `reperes_guides, reperes_rects` à l'import de `mod-doc.js`
et `import { initImage } from "./mod-image.js";`.

`rendre()` : `$("#canvasHost").innerHTML = etat.doc ? compilerSVG(etat.doc, { image: VL.imageUrl }) : "";`

`aimantePt` : fusionner les guides des repères :

```js
function aimantePt(x, y) {
  const g = etat.doc.guides || { v: [], h: [] };
  const rg = reperes_guides(etat.doc);
  const pas = etat.grille.active ? etat.grille.pas : 0;
  return [aimanter(x, { pas, guides: (g.v || []).concat(rg.v) }, tolDoc()),
          aimanter(y, { pas, guides: (g.h || []).concat(rg.h) }, tolDoc())];
}
```

`rendreOverlay()` : juste après les guides et AVANT le cadre de sélection :

```js
  // repères de page (lot A) : coupe en rouge, zone sûre en vert — overlay
  // seulement, jamais dans l'export
  const rr = reperes_rects(etat.doc);
  for (const [k, couleur] of [["fondPerdu", "#d0553a"], ["zoneSure", "#3aa66b"]]) {
    const b = rr[k];
    if (!b) continue;
    const [ex, ey] = ecranPt(b.x, b.y);
    o.appendChild(ov("rect", { x: ex, y: ey, width: b.w * etat.zoom, height: b.h * etat.zoom,
      fill: "none", stroke: couleur, "stroke-width": 1, "stroke-dasharray": "6 3",
      class: "repere", "data-repere": k, "pointer-events": "none" }));
  }
```

Hooks : dans `VL`, ajouter `surCharge: () => {}, surSauve: () => {}` ; dans
`charger()` appeler `VL.surCharge()` juste après `appliquerVue();` du
succès ; dans `sauver()` appeler `VL.surSauve()` après `majTete();`.
Inits : `initImage(VL);` après `initStyle(VL)` (le panneau Image se rend
après Apparence).

- [ ] **Step 6 : `mod-export.js` — les images inlinées en `data:`**

```js
import { image_hrefs } from "./mod-image.js";
// …
  async function svgCourant(transparent) {
    const doc = JSON.parse(JSON.stringify(etat.doc));
    if (transparent) delete doc.fond;
    // un SVG chargé comme <img> ne peut PAS charger d'images externes :
    // chaque PNG du document est inliné en data: — pour l'export seulement,
    // le JSON stocké ne porte jamais de base64 (D1)
    const carte = new Map();
    for (const href of image_hrefs(doc)) {
      const r = await fetch(VL.imageUrl(href));
      if (!r.ok) throw new Error(`image ${href} introuvable (${r.status})`);
      const b = await r.blob();
      carte.set(href, await new Promise((res, rej) => {
        const fr = new FileReader();
        fr.onload = () => res(fr.result); fr.onerror = () => rej(new Error("lecture image"));
        fr.readAsDataURL(b);
      }));
    }
    return compilerSVG(doc, { image: (h) => carte.get(h) || h });
  }
```

`exporterSVG` : `svg: await svgCourant(...)`. `rasteriser(k, transparent)`
devient `async` et commence par `const svg = await svgCourant(transparent);`
puis `new Blob([svg], …)` dans la promesse.

- [ ] **Step 7 : `index.html` et `vectorlab.css`**

Dans la barre, après le bloc `exp-conteneur` :

```html
    <span class="exp-conteneur">
      <button id="btnImage" title="Poser une image dans le document (Bibliothèque, fichier, presse-papiers, génération) et la vectoriser">Image ▾</button>
      <div id="imgMenu" class="exp-menu hidden">
        <button id="imgBiblio" title="Choisir une image de la Bibliothèque unifiée">📚 Bibliothèque…</button>
        <button id="imgFichier" title="Importer un fichier image (PNG, JPEG, WebP — stocké en PNG avec le document)">⬆ Fichier…</button>
        <button id="imgColler" title="Coller l'image du presse-papiers (ou Ctrl+V sur la scène)">📋 Presse-papiers</button>
        <button id="imgGenerer" title="Générer une image par le fournisseur des Réglages — dépense la clé">✦ Générer…</button>
        <button id="imgVectoriser" title="Vectoriser une image du document en aplats de couleur — aperçu avant validation">◇ Vectoriser…</button>
      </div>
      <input type="file" id="imgFichierInput" accept="image/png,image/jpeg,image/webp" hidden/>
    </span>
```

Dans `<aside id="panneauCalques">`, après `<div id="panneauStyle"></div>` :

```html
      <div class="panneau-tete" id="teteImage" hidden>Image</div>
      <div id="panneauImage" hidden></div>
      <div class="panneau-tete" title="Fond perdu et zone sûre — tracés à l'écran, aimantants, jamais exportés">Repères</div>
      <div id="panneauReperes"></div>
```

Avant `<script src="vendor/martinez.umd.js">`, les dialogues (le
`#traceDlg` est rempli à la Task 5) :

```html
  <div id="libDlg" class="vl-dlg hidden">
    <div class="vl-dlg-boite">
      <div class="vl-dlg-tete"><b>Bibliothèque</b>
        <input id="libRecherche" type="search" placeholder="rechercher…"/>
        <button id="libFermer" title="Fermer">✕</button></div>
      <div id="libGrille" class="lib-grille"></div>
    </div>
  </div>
  <div id="traceDlg" class="vl-dlg hidden"></div>
  <script src="vendor/imagetracer_v1.2.6.js"></script>
```

CSS (fin de `vectorlab.css`) :

```css
/* ── lot A : dialogues, grille bibliothèque de repli, panneaux image/repères ── */
.vl-dlg { position: fixed; inset: 0; z-index: 60; background: rgba(8,10,14,.6);
  display: flex; align-items: center; justify-content: center; }
.vl-dlg.hidden { display: none; }
.vl-dlg-boite { background: #1a1e26; color: #d6d9de; border: 1px solid #3a4150;
  border-radius: 8px; width: min(920px, 92vw); max-height: 88vh; display: flex;
  flex-direction: column; box-shadow: 0 18px 50px rgba(0,0,0,.5); }
.vl-dlg-tete { display: flex; gap: 10px; align-items: center; padding: 10px 12px;
  border-bottom: 1px solid #2c323d; }
.vl-dlg-tete input[type="search"] { flex: 1; background: #232833; color: #d6d9de;
  border: 1px solid #3a4150; border-radius: 4px; padding: 4px 8px; }
.lib-grille { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px; padding: 12px; overflow: auto; }
.lib-carte { background: #232833; border: 1px solid #3a4150; border-radius: 6px;
  padding: 4px; cursor: pointer; display: flex; flex-direction: column; gap: 4px;
  height: 140px; }                          /* hauteur EXPLICITE : une case en
                                               overflow:hidden ne contribue pas à la rangée */
.lib-carte img { width: 100%; height: 100px; object-fit: cover; border-radius: 4px; }
.lib-carte span { font-size: 11px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; color: #9aa3b2; }
.lib-carte:hover { border-color: #5b82b8; }
.lib-vide { color: #8b93a0; padding: 24px; text-align: center; grid-column: 1 / -1; }
.img-src { font-size: 11px; color: #9aa3b2; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; max-width: 150px; }
.rep-pastille { width: 14px; height: 10px; border: 1px dashed; display: inline-block; }
.rep-fond { border-color: #d0553a; } .rep-sure { border-color: #3aa66b; }
#panneauImage button.actif { background: #3d2f22; border-color: #e0b34a; }
```

- [ ] **Step 8 : banc complet + syntaxe**

```bash
cd frontend/vectorlab && node qa/run.mjs && for f in js/*.js; do node --check "$f" || echo "KO $f"; done
```

Attendu : tous verts (`node --check` accepte l'ESM avec l'extension .js car
`package.json` est `"type": "module"`).

- [ ] **Step 9 : commit**

```bash
git add frontend/vectorlab/js/mod-image.js frontend/vectorlab/qa/image_ui.test.mjs
git commit --only frontend/vectorlab/js/mod-image.js frontend/vectorlab/qa/image_ui.test.mjs frontend/vectorlab/js/core.js frontend/vectorlab/js/mod-export.js frontend/vectorlab/index.html frontend/vectorlab/vectorlab.css -m "vectorlab : poser une image (Bibliotheque, fichier, presse-papiers, generation), rogner, verrouiller ; reperes traces et aimantants ; export avec images inlinees (lot A, T4)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 5 : vectorisation avec aperçu (imagetracerjs)

**Files :**
- Create : `frontend/vectorlab/js/mod-trace.js`
- Modify : `frontend/vectorlab/js/mod-doc.js` (`op_vectoriser_poser`), `core.js` (init), `index.html` (déjà `#traceDlg`)
- Test : `frontend/vectorlab/qa/trace.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// trace.test.mjs — la vectorisation (D6) : options bornées, définition de
// tracé, conversion tracedata → objets path du modèle (trous en evenodd,
// couleurs hex, coordonnées ramenées au cadre de l'image), et la commande
// op_vectoriser_poser. Le vendor est exercé EN VRAI sur une ImageData
// synthétique (node : require CommonJS du même fichier que le navigateur).
import { createRequire } from "node:module";
import { TRACE_DEFAUTS, options_trace, definition_trace, tracedata_vers_objets }
  from "../js/mod-trace.js";
import { parserDoc, compilerSVG, op_vectoriser_poser, chemin_parser } from "../js/mod-doc.js";

const ImageTracer = createRequire(import.meta.url)("../vendor/imagetracer_v1.2.6.js");
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

/* ── options ── */
{
  const o = options_trace(TRACE_DEFAUTS);
  ok("défauts : 8 couleurs, lissage 1, seuil 8, pas de trait, coordonnées 2 déc.",
     o.numberofcolors === 8 && o.ltres === 1 && o.qtres === 1 && o.pathomit === 8
     && o.strokewidth === 0 && o.roundcoords === 2 && o.blurradius === 0, JSON.stringify(o));
  const b = options_trace({ couleurs: 999, lissage: 0, seuil: -4 });
  ok("options bornées : 64 couleurs max, lissage ≥ 0.1, seuil ≥ 0",
     b.numberofcolors === 64 && b.ltres === 0.1 && b.pathomit === 0, JSON.stringify(b));
  ok("options : 2 couleurs min", options_trace({ couleurs: 1 }).numberofcolors === 2);
}
/* ── définition : la fenêtre tracée tient dans `definition` px de côté ── */
{
  const d = definition_trace({ w: 1600, h: 800 }, 512);
  ok("définition : plus grand côté = 512, ratio gardé", d.w === 512 && d.h === 256, JSON.stringify(d));
  const p = definition_trace({ w: 100, h: 60 }, 512);
  ok("définition : une petite fenêtre n'est pas agrandie", p.w === 100 && p.h === 60);
}
/* ── tracedata → objets, sur une image synthétique : fond bleu, carré rouge
   avec un trou — le vendor en vrai ── */
function imageSynthetique() {
  const W = 40, H = 40, data = new Uint8ClampedArray(W * H * 4);
  const poser = (x, y, r, g, b) => { const i = (y * W + x) * 4; data[i] = r; data[i + 1] = g; data[i + 2] = b; data[i + 3] = 255; };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let c = [0, 71, 171];                                   // #0047AB
    if (x >= 8 && x < 32 && y >= 8 && y < 32) c = [155, 17, 30];   // #9B111E
    if (x >= 16 && x < 24 && y >= 16 && y < 24) c = [0, 71, 171];  // trou
    poser(x, y, ...c);
  }
  return { width: W, height: H, data };
}
{
  const td = ImageTracer.imagedataToTracedata(imageSynthetique(), options_trace({ couleurs: 2, seuil: 0 }));
  ok("vendor : tracedata 40×40 avec palette", td.width === 40 && td.height === 40 && td.palette.length === 2, JSON.stringify([td.width, td.palette]));
  const objets = tracedata_vers_objets(td, { x: 100, y: 200, w: 80, h: 80 });
  ok("au moins deux chemins (fond et carré)", objets.length >= 2, objets.length);
  ok("tous des path evenodd à fond hex", objets.every((o) => o.type === "path"
     && o.style.regle === "evenodd" && /^#[0-9A-F]{6}$/.test(o.style.fond)
     && o.style.contour === undefined), JSON.stringify(objets[0]));
  const couleurs = new Set(objets.map((o) => o.style.fond));
  ok("les deux couleurs du synthétique ressortent", couleurs.has("#0047AB") && couleurs.has("#9B111E"), [...couleurs].join(","));
  // coordonnées : dans le cadre [100..180]×[200..280] (tolérance 1 px de lissage)
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const o of objets) for (const s of chemin_parser(o.d)) {
    for (let k = 0; k < s.p.length; k += 2) {
      minX = Math.min(minX, s.p[k]); maxX = Math.max(maxX, s.p[k]);
      minY = Math.min(minY, s.p[k + 1]); maxY = Math.max(maxY, s.p[k + 1]);
    }
  }
  ok("coordonnées ramenées au cadre", minX >= 99 && maxX <= 181 && minY >= 199 && maxY <= 281,
     [minX, maxX, minY, maxY].join(" "));
  // le carré rouge porte son trou : un sous-chemin de plus (deux M)
  const rouge = objets.find((o) => o.style.fond === "#9B111E");
  ok("le trou est un sous-chemin du carré (2 × M)", rouge && (rouge.d.match(/M /g) || []).length === 2, rouge && rouge.d);
  // parse canonique : tout d est relisible par chemin_parser
  ok("tous les d sont canoniques", objets.every((o) => { try { chemin_parser(o.d); return true; } catch { return false; } }));
  // état vide : image transparente → aucun objet
  const vide = { width: 4, height: 4, data: new Uint8ClampedArray(64) };
  const tdVide = ImageTracer.imagedataToTracedata(vide, options_trace({ couleurs: 2 }));
  ok("image transparente → aucun objet (alpha < 32 ignoré)",
     tracedata_vers_objets(tdVide, { x: 0, y: 0, w: 4, h: 4 }).length === 0);
  /* ── la commande ── */
  const doc = { v: 1, nom: "T", taille: { w: 400, h: 400 },
    calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [] }] };
  const r = op_vectoriser_poser(doc, objets, "vectorisé");
  ok("op_vectoriser_poser : calque neuf au-dessus, ids rendus", r.calqueId === "c2"
     && doc.calques[1].nom === "vectorisé" && r.ids.length === objets.length
     && doc.calques[1].objets.length === objets.length, JSON.stringify(r));
  ok("le document compilé passe parserDoc et porte fill-rule",
     (() => { try { return compilerSVG(parserDoc(doc)).includes('fill-rule="evenodd"'); } catch { return false; } })());
  let refus = 0;
  try { op_vectoriser_poser(doc, [], "x"); } catch { refus++; }
  ok("op_vectoriser_poser refuse une liste vide", refus === 1);
}

if (echecs.length) {
  console.error("ECHECS trace :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA trace : PASS (17 controles)");
```

- [ ] **Step 2 : RED** — `node qa/trace.test.mjs` → `Cannot find module '.../js/mod-trace.js'`.

- [ ] **Step 3 : `mod-doc.js` — la commande**

Après `op_image_verrou` :

```js
/* ── vectorisation (lot A, D6) : les chemins tracés se posent d'un coup
   dans un calque NEUF au-dessus — une commande, une entrée d'historique. */
export function op_vectoriser_poser(doc, objets, nom) {
  if (!Array.isArray(objets) || !objets.length) throw new Error("rien à vectoriser (image vide ou seuil trop haut)");
  const calqueId = op_calque_ajouter(doc, nom || "vectorisé");
  const ids = objets.map((o) => op_ajouter(doc, calqueId, { ...o, id: undefined }));
  return { calqueId, ids };
}
```

- [ ] **Step 4 : `mod-trace.js`**

```js
// mod-trace.js — la vectorisation d'une image (lot A, D6) par imagetracerjs
// vendorisé (Unlicense) : aplats de couleur → chemins du modèle. PUR en
// tête : options bornées, définition de tracé, conversion tracedata →
// objets `path` (trous en sous-chemins, fill-rule evenodd). Le dialogue
// (initTrace) rasterise la fenêtre rognée de l'image dans un canvas,
// trace, montre un aperçu compilé par LE compilateur, puis pose en UNE
// commande (op_vectoriser_poser).
import { compilerSVG, op_vectoriser_poser, chemin_parser, chemin_serialiser }
  from "./mod-doc.js";

/* ── pur ── */
export const TRACE_DEFAUTS = { couleurs: 8, lissage: 1, seuil: 8, definition: 512 };
const borne = (v, lo, hi, def) => { const n = +v; return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : def; };

export function options_trace(p = {}) {
  const lissage = borne(p.lissage, 0.1, 10, TRACE_DEFAUTS.lissage);
  return {
    numberofcolors: Math.round(borne(p.couleurs, 2, 64, TRACE_DEFAUTS.couleurs)),
    ltres: lissage, qtres: lissage,
    pathomit: Math.round(borne(p.seuil, 0, 500, TRACE_DEFAUTS.seuil)),
    colorsampling: 2, mincolorratio: 0, colorquantcycles: 3,
    blurradius: 0, blurdelta: 20, layering: 0, rightangleenhance: true,
    strokewidth: 0, linefilter: false, roundcoords: 2, viewbox: false, desc: false,
  };
}

export function definition_trace(fenetre, definition) {
  const d = borne(definition, 64, 2048, TRACE_DEFAUTS.definition);
  const k = Math.min(1, d / Math.max(fenetre.w, fenetre.h));
  return { w: Math.max(1, Math.round(fenetre.w * k)), h: Math.max(1, Math.round(fenetre.h * k)), echelle: k };
}

const hex2 = (n) => Math.round(n).toString(16).padStart(2, "0").toUpperCase();
function _d(segments, fx, fy) {
  if (!segments.length) return "";
  let d = `M ${fx(segments[0].x1)} ${fy(segments[0].y1)}`;
  for (const s of segments) {
    d += s.type === "Q" ? ` Q ${fx(s.x2)} ${fy(s.y2)} ${fx(s.x3)} ${fy(s.y3)}`
                        : ` L ${fx(s.x2)} ${fy(s.y2)}`;
  }
  return d + " Z";
}

export function tracedata_vers_objets(td, cadre) {
  const fx = (x) => cadre.x + x * cadre.w / td.width;
  const fy = (y) => cadre.y + y * cadre.h / td.height;
  const out = [];
  td.layers.forEach((chemins, l) => {
    const c = td.palette[l];
    if (!c || c.a < 32) return;                       // transparent : rien
    const fond = "#" + hex2(c.r) + hex2(c.g) + hex2(c.b);
    for (const p of chemins) {
      if (p.isholepath) continue;                     // les trous suivent leur parent
      let d = _d(p.segments, fx, fy);
      for (const k of p.holechildren || []) d += " " + _d(chemins[k].segments, fx, fy);
      if (!d) continue;
      out.push({ type: "path", d: chemin_serialiser(chemin_parser(d)),
                 style: { fond, regle: "evenodd" } });
    }
  });
  return out;
}

/* ── DOM ── */
export function initTrace(VL) {
  const { $, etat } = VL;
  const dlg = $("#traceDlg");
  let courant = null;                  // { id, objets, params }

  function charger(url) {
    return new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im);
      im.onerror = () => rej(new Error("image source illisible"));
      im.src = url;
    });
  }
  async function tracer(o, params) {
    if (!window.ImageTracer) throw new Error("imagetracerjs indisponible (vendor non chargé)");
    const im = await charger(VL.imageUrl(o.href));
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    const def = definition_trace(r, params.definition);
    const cv = document.createElement("canvas");
    cv.width = def.w; cv.height = def.h;
    const ctx = cv.getContext("2d");
    ctx.drawImage(im, r.x, r.y, r.w, r.h, 0, 0, def.w, def.h);
    const td = window.ImageTracer.imagedataToTracedata(
      ctx.getImageData(0, 0, def.w, def.h), options_trace(params));
    return tracedata_vers_objets(td, { x: o.x, y: o.y, w: o.w, h: o.h });
  }
  function lireParams() {
    return { couleurs: +$("#trCouleurs").value, lissage: +$("#trLissage").value,
             seuil: +$("#trSeuil").value, definition: +$("#trDef").value };
  }
  async function apercu() {
    const t = VL.objetDe(courant.id);
    if (!t) throw new Error("image disparue");
    $("#trEtat").textContent = "tracé en cours…";
    $("#trValider").disabled = true;
    const objets = await tracer(t.objet, lireParams());
    courant.objets = objets;
    const couleurs = new Set(objets.map((o) => o.style.fond)).size;
    const b = t.objet;
    const mini = { v: 1, taille: { w: b.w, h: b.h }, fond: "#FFFFFF",
      calques: [{ id: "c", objets: objets.map((o, i) => ({ ...o, id: "t" + i })) }] };
    // le même compilateur que l'écran ; les d sont décalés au cadre → viewBox
    $("#trApercu").innerHTML = compilerSVG(mini)
      .replace(`viewBox="0 0 ${+b.w} ${+b.h}"`, `viewBox="${+b.x} ${+b.y} ${+b.w} ${+b.h}"`)
      .replace(`width="${+b.w}" height="${+b.h}"`, `width="100%" height="100%"`);
    $("#trEtat").textContent = `${objets.length} chemin(s) · ${couleurs} couleur(s)`;
    $("#trValider").disabled = !objets.length;
  }
  function fermer() { dlg.classList.add("hidden"); dlg.innerHTML = ""; courant = null; }

  VL.vectoriser = (id) => {
    const t = VL.objetDe(id);
    if (!t || t.objet.type !== "image") { VL.toast("pas une image", true); return; }
    courant = { id, objets: [], params: { ...TRACE_DEFAUTS } };
    const p = courant.params;
    dlg.innerHTML = `<div class="vl-dlg-boite tr-boite">
      <div class="vl-dlg-tete"><b>Vectoriser « ${t.objet.href} »</b><span class="spacer"></span>
        <button id="trFermer" title="Annuler">✕</button></div>
      <div class="tr-corps">
        <div class="tr-regles">
          <label>Couleurs <input type="range" id="trCouleurs" min="2" max="32" step="1" value="${p.couleurs}"/><output id="trCouleursV">${p.couleurs}</output></label>
          <label>Lissage <input type="range" id="trLissage" min="0.5" max="4" step="0.5" value="${p.lissage}"/><output id="trLissageV">${p.lissage}</output></label>
          <label>Seuil (px) <input type="range" id="trSeuil" min="0" max="64" step="1" value="${p.seuil}"/><output id="trSeuilV">${p.seuil}</output></label>
          <label>Définition <select id="trDef">${[256, 512, 1024].map((d) => `<option value="${d}"${d === p.definition ? " selected" : ""}>${d} px</option>`).join("")}</select></label>
          <button id="trApercuBtn" class="primaire">Aperçu</button>
          <p id="trEtat" class="tr-etat">réglez, puis Aperçu</p>
        </div>
        <div id="trApercu" class="tr-apercu"></div>
      </div>
      <div class="tr-pied"><button id="trAnnuler">Annuler</button>
        <button id="trValider" class="primaire" disabled title="Pose les chemins dans un calque neuf « vectorisé » (une commande, annulable)">Valider</button></div>
    </div>`;
    dlg.classList.remove("hidden");
    for (const [id, out] of [["trCouleurs", "trCouleursV"], ["trLissage", "trLissageV"], ["trSeuil", "trSeuilV"]]) {
      $("#" + id).addEventListener("input", (e) => { $("#" + out).textContent = e.target.value; });
    }
    const garde = (fn) => () => Promise.resolve().then(fn).catch((e) => { $("#trEtat").textContent = e.message; VL.toast(e.message, true); });
    $("#trApercuBtn").addEventListener("click", garde(apercu));
    $("#trFermer").addEventListener("click", fermer);
    $("#trAnnuler").addEventListener("click", fermer);
    $("#trValider").addEventListener("click", () => {
      const r = VL.executer(op_vectoriser_poser, courant.objets, "vectorisé");
      if (r) { etat.calqueActif = r.calqueId; VL.setSelection(r.ids); VL.toast(`${r.ids.length} chemin(s) posés dans « vectorisé »`); }
      fermer();
    });
    garde(apercu)();                    // un premier aperçu aux défauts
  };
}
```

CSS à ajouter :

```css
.tr-boite { width: min(1000px, 94vw); }
.tr-corps { display: flex; gap: 14px; padding: 12px; min-height: 360px; }
.tr-regles { width: 220px; display: flex; flex-direction: column; gap: 10px; }
.tr-regles label { display: flex; flex-direction: column; font-size: 12px; color: #9aa3b2; gap: 3px; }
.tr-regles output { color: #d6d9de; font-size: 12px; }
.tr-etat { font-size: 12px; color: #9aa3b2; margin: 0; }
.tr-apercu { flex: 1; background: #fff; border-radius: 6px; min-height: 340px;
  display: flex; align-items: center; justify-content: center; overflow: hidden; }
.tr-apercu svg { max-width: 100%; max-height: 60vh; }
.tr-pied { display: flex; justify-content: flex-end; gap: 8px; padding: 10px 12px;
  border-top: 1px solid #2c323d; }
```

`core.js` : `import { initTrace } from "./mod-trace.js";` et `initTrace(VL);`
après `initImage(VL)`.

- [ ] **Step 5 : GREEN** — `node qa/trace.test.mjs && node qa/run.mjs`.

- [ ] **Step 6 : commit**

```bash
git add frontend/vectorlab/js/mod-trace.js frontend/vectorlab/qa/trace.test.mjs
git commit --only frontend/vectorlab/js/mod-trace.js frontend/vectorlab/qa/trace.test.mjs frontend/vectorlab/js/mod-doc.js frontend/vectorlab/js/core.js frontend/vectorlab/vectorlab.css -m "vectorlab : vectorisation par imagetracerjs — couleurs, lissage, seuil, definition, apercu par LE compilateur, pose en une commande (lot A, T5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 6 : brouillon automatique (30 s, restauré à l'ouverture)

**Files :**
- Create : `frontend/vectorlab/js/mod-brouillon.js`
- Modify : `frontend/vectorlab/js/core.js`
- Test : `frontend/vectorlab/qa/brouillon.test.mjs`

- [ ] **Step 1 : banc RED**

```js
// brouillon.test.mjs — le brouillon (lot A) : clé par document, contenu
// cloné, pertinence (même document, même version serveur, contenu DIFFÉRENT
// du serveur), libellé horaire. L'état vide (aucun brouillon) est construit.
import { BROUILLON_PERIODE_MS, brouillon_cle, brouillon_faire,
         brouillon_pertinent, brouillon_libelle } from "../js/mod-brouillon.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const doc = { v: 1, taille: { w: 1, h: 1 }, calques: [{ id: "c", objets: [] }] };

ok("période : 30 s", BROUILLON_PERIODE_MS === 30000);
ok("clé par document", brouillon_cle("ab12") === "dz_vl_brouillon_ab12");
{
  const b = brouillon_faire("ab12", 3, doc, 1700000000000);
  ok("brouillon : docId, version, t, doc cloné", b.docId === "ab12" && b.version === 3
     && b.t === 1700000000000 && b.doc !== doc && JSON.stringify(b.doc) === JSON.stringify(doc));
  const meta = { id: "ab12", version: 3 };
  ok("état vide : null n'est pas pertinent", brouillon_pertinent(null, meta, doc) === false);
  ok("identique au serveur : pas pertinent", brouillon_pertinent(b, meta, doc) === false);
  const modif = JSON.parse(JSON.stringify(doc)); modif.calques[0].objets.push({ id: "o1", type: "rect", x: 0, y: 0, w: 1, h: 1 });
  const b2 = brouillon_faire("ab12", 3, modif, 1);
  ok("différent du serveur, même version : PERTINENT", brouillon_pertinent(b2, meta, doc) === true);
  ok("autre version serveur (sauvé ailleurs depuis) : pas pertinent",
     brouillon_pertinent(b2, { id: "ab12", version: 4 }, doc) === false);
  ok("autre document : pas pertinent", brouillon_pertinent(b2, { id: "zz", version: 3 }, doc) === false);
  ok("brouillon corrompu (sans doc) : pas pertinent", brouillon_pertinent({ docId: "ab12", version: 3 }, meta, doc) === false);
  ok("libellé : heure lisible", /brouillon du \d{2}:\d{2}/.test(brouillon_libelle(b)), brouillon_libelle(b));
}

if (echecs.length) {
  console.error("ECHECS brouillon :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA brouillon : PASS (10 controles)");
```

- [ ] **Step 2 : RED** — `Cannot find module '.../js/mod-brouillon.js'`.

- [ ] **Step 3 : `mod-brouillon.js`**

```js
// mod-brouillon.js — la sauvegarde AUTOMATIQUE (lot A) : toutes les 30 s,
// si le document est sale, un brouillon part dans localStorage (clé par
// document) ; à l'ouverture, un brouillon PERTINENT (même document, même
// version serveur, contenu différent) est proposé ; un Sauver réussi
// l'efface. Le raster n'est jamais dedans (les href sont des noms). Les
// timers d'un onglet caché sont throttlés : la période est un minimum.
import { parserDoc } from "./mod-doc.js";

/* ── pur ── */
export const BROUILLON_PERIODE_MS = 30000;
export function brouillon_cle(docId) { return "dz_vl_brouillon_" + docId; }
export function brouillon_faire(docId, version, doc, t = Date.now()) {
  return { docId, version, t, doc: JSON.parse(JSON.stringify(doc)) };
}
export function brouillon_pertinent(b, meta, docServeur) {
  if (!b || !b.doc || !meta) return false;
  if (b.docId !== meta.id || b.version !== meta.version) return false;
  return JSON.stringify(b.doc) !== JSON.stringify(docServeur);
}
export function brouillon_libelle(b) {
  const d = new Date(b.t);
  const p = (n) => String(n).padStart(2, "0");
  return `brouillon du ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* ── DOM ── */
export function initBrouillon(VL) {
  const { $, etat } = VL;
  const lire = (k) => { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch { return null; } };
  const effacer = (k) => { try { localStorage.removeItem(k); } catch (e) { /* stockage indisponible */ } };

  function ecrire() {
    if (!etat.docId || !etat.doc || !etat.sale) return;
    const b = brouillon_faire(etat.docId, etat.meta.version, etat.doc);
    try { localStorage.setItem(brouillon_cle(etat.docId), JSON.stringify(b)); }
    catch (e) { return; }
    $("#temoin").title = "État d'enregistrement · " + brouillon_libelle(b) + " (non sauvé au serveur)";
  }
  setInterval(ecrire, BROUILLON_PERIODE_MS);

  const suivantCharge = VL.surCharge;
  VL.surCharge = () => {
    suivantCharge();
    const k = brouillon_cle(etat.docId);
    const b = lire(k);
    if (!brouillon_pertinent(b, { id: etat.docId, version: etat.meta.version }, etat.doc)) {
      if (b) effacer(k);                 // périmé : on ne le reproposera pas
      return;
    }
    if (confirm(`Un ${brouillon_libelle(b)} de ce document n'a pas été sauvé. Le restaurer ?\n(Annuler = repartir de la version ${etat.meta.version} du serveur ; le brouillon est alors oublié.)`)) {
      try { etat.doc = parserDoc(b.doc); } catch (e) { VL.toast("brouillon illisible : " + e.message, true); effacer(k); return; }
      etat.sale = true;
      etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id;
      VL.rendre();
      VL.toast("brouillon restauré — Sauver pour l'écrire au serveur");
    } else effacer(k);
  };
  const suivantSauve = VL.surSauve;
  VL.surSauve = () => { suivantSauve(); effacer(brouillon_cle(etat.docId)); $("#temoin").title = "État d'enregistrement"; };
  VL.brouillonEcrire = ecrire;           // la preuve force un tic sans attendre 30 s
}
```

`core.js` : `import { initBrouillon } from "./mod-brouillon.js";` puis
`initBrouillon(VL);` AVANT `charger();` (le hook `surCharge` doit être posé
avant le chargement).

- [ ] **Step 4 : GREEN** — `node qa/brouillon.test.mjs && node qa/run.mjs`.

- [ ] **Step 5 : commit**

```bash
git add frontend/vectorlab/js/mod-brouillon.js frontend/vectorlab/qa/brouillon.test.mjs
git commit --only frontend/vectorlab/js/mod-brouillon.js frontend/vectorlab/qa/brouillon.test.mjs frontend/vectorlab/js/core.js -m "vectorlab : brouillon automatique toutes les 30 s, restaure a l'ouverture s'il est pertinent, efface au Sauver (lot A, T6)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 7 : pont Cartes retour — « Éditer cette face dans le Vectorlab »

**Files :**
- Modify : `frontend/cardforge/js/core.js` (bloc `vector`, ~l. 1515-1548)
- Modify : `frontend/cardforge/js/mod-face.js` (§3-ter ~l. 1877-2025 ; rangée `#cf-face-vlab-new` ~l. 3476 ; câblage des boutons)
- Test : `backend/tests/test_vector_docs.py::test_le_miroir_pont_cartes_mod_face` (étendre)

- [ ] **Step 1 : étendre le miroir pytest (RED)**

Ajouter à la fin de `test_le_miroir_pont_cartes_mod_face` :

```python
    # lot A (D5) : le pont RETOUR — la face rendue par LE moteur (CF.cardBlob)
    # part au magasin d'images du document par le CORE (CF.vector.image), le
    # document se réécrit par le CORE (CF.vector.update) au format physique
    # du jeu (canvas_px, dpi, repères = bleed_off_px / safe_off_px), la face
    # est un calque image VERROUILLÉ, l'éditeur s'ouvre dessus.
    assert 'id="cf-face-vlab-edit"' in face
    assert "CF.vector.image(" in face and "CF.vector.update(" in face
    assert "CF.cardBlob(" in face and "docFaceVec(" in face
    for cle in ("bleed_off_px", "safe_off_px", "canvas_px", '"fondPerdu"', '"zoneSure"',
                'type: "image"', "verrou: true"):
        assert cle in face, cle
    assert '"/images"' in core and 'update: vectorUpdate' in core and 'image: vectorImage' in core
    assert '"image/png"' in core
```

Lancer : `& $py -m pytest tests/test_vector_docs.py -q -k miroir_pont` → FAIL
sur `cf-face-vlab-edit`.

- [ ] **Step 2 : `core.js` du Cardforge — deux méthodes de transport**

Après `vectorDel` :

```js
  async function vectorUpdate(id, doc) {
    const s = String(id == null ? "" : id);
    if (!s) throw new Error("cardforge: CF.vector.update exige un identifiant de document");
    if (!isPlain(doc)) throw new Error("cardforge: CF.vector.update exige un document (objet)");
    return jsonFetch("PUT", "/vector/docs/" + encodeURIComponent(s), { doc: doc });
  }
  /* la face rendue par LE moteur (cardBlob) part au magasin d'images DU
     DOCUMENT vectoriel — jamais par /images/upload : la Library reste
     propre, et le PNG suit le document (duplication, transfert) */
  async function vectorImage(id, blob) {
    const s = String(id == null ? "" : id);
    if (!s) throw new Error("cardforge: CF.vector.image exige un identifiant de document");
    if (typeof Blob === "undefined" || !(blob instanceof Blob) || blob.type !== "image/png")
      throw new Error("cardforge: CF.vector.image attend un Blob image/png (sorti de CF.cardBlob)");
    return jsonFetch("POST", "/vector/docs/" + encodeURIComponent(s) + "/images", blob,
      { "Content-Type": "image/png" });
  }
  const vector = Object.freeze({ docs: vectorDocs, create: vectorCreate, del: vectorDel,
                                 update: vectorUpdate, image: vectorImage });
```

- [ ] **Step 3 : `mod-face.js` — le document au format du jeu et le bouton**

Après `vecTailleDefaut()` (§3-ter) :

```js
  /* Le document « face à éditer » (lot A, D5) : la toile ENTIÈRE du jeu
     (fond perdu compris) au dpi du jeu, les repères posés depuis LA
     géométrie (bleed_off_px = ligne de coupe, safe_off_px = zone sûre),
     la face rendue posée en calque image VERROUILLÉ sous un calque de
     retouches vide et actif. `href` est le nom rendu par CF.vector.image. */
  function docFaceVec(g, nom, href) {
    const W = g.canvas_px[0], H = g.canvas_px[1];
    return { v: 1, nom: nom, taille: { w: W, h: H },
      unites: { affichage: "mm", dpi: g.dpi },
      reperes: { "fondPerdu": [g.bleed_off_px[0], g.bleed_off_px[1]],
                 "zoneSure": [g.safe_off_px[0], g.safe_off_px[1]] },
      calques: [
        { id: "c1", nom: "face (verrouillée)", visible: true, verrou: true, objets: [
          { id: "o1", type: "image", x: 0, y: 0, w: W, h: H, href: href,
            nat: { w: W, h: H }, verrou: true, style: {} } ] },
        { id: "c2", nom: "retouches", visible: true, verrou: false, objets: [] } ] };
  }

  async function editerFaceVec() {
    const did = vecDeckId();
    if (!did) { CF.toast("aucun jeu ouvert", true); return; }
    const g = CF.geom();
    const nom = "Face " + (CF.current() + 1) + " — " + String(CF.doc().name || "carte").slice(0, 60);
    CF.busy(true, "rendu de la face à " + g.canvas_px[0] + " x " + g.canvas_px[1] + " px…");
    try {
      const png = await CF.cardBlob(CF.current(), {});          /* LE moteur unique */
      const d = await CF.vector.create({ name: nom, role: "libre", deck_id: did,
        doc: docFaceVec(g, nom, "img1.png") });
      const im = await CF.vector.image(d.id, png);
      await CF.vector.update(d.id, docFaceVec(g, nom, im.name));
      window.open("/vectorlab/?doc=" + encodeURIComponent(d.id), "_blank");
      VECS = { deck: null, docs: [] };
      chargerVecs();
    } catch (e) {
      CF.toast("éditer la face : " + String((e && e.message) || e), true);
    } finally { CF.busy(false); }
  }
```

Dans la rangée du volet `vec` (~l. 3477), après le bouton `+ Nouveau` :

```js
      + '<button class="btn sm" type="button" id="cf-face-vlab-edit" title="Rend la face courante (le moteur, fond perdu compris), crée un document Vectorlab au format physique du jeu avec les repères de coupe et de zone sûre, la face en calque image verrouillé, et l\'ouvre — « Poser 2× » ramène le résultat">Éditer cette face dans le Vectorlab</button>'
```

Câblage : trouver où `#cf-face-vlab-new` est branché (`grep -n "cf-face-vlab-new" mod-face.js`)
et ajouter à côté, sur le même patron :

```js
    on(q("#cf-face-vlab-edit"), "click", () => { editerFaceVec(); });
```

(adapter au helper d'écoute réellement utilisé à cet endroit — `on(...)`,
`addEventListener`, ou délégation — en copiant la ligne du bouton voisin).

- [ ] **Step 4 : GREEN + non-régression des pins Cardforge**

```powershell
Set-Location backend
& $py -m pytest tests/test_vector_docs.py -q 2>&1 | Select-Object -Last 3
& $py -m pytest tests/test_cards_face.py tests/test_cards_type.py tests/test_cards_core.py -q -x 2>&1 | Select-Object -Last 6
```

Attendu : vector 24 passed ; les trois bancs cards verts (le pin « aucun
`fetch(` dans une pièce » tient : mod-face ne fait que `CF.*`). Si un pin
compte les boutons du volet ou les `id="` de mod-face, lire son message et
le mettre à jour EN LE DISANT (le bouton est voulu).

- [ ] **Step 5 : commit**

```bash
git commit --only frontend/cardforge/js/core.js frontend/cardforge/js/mod-face.js backend/tests/test_vector_docs.py -m "cardforge : « Editer cette face dans le Vectorlab » — la face rendue part au magasin du document par le CORE (CF.vector.image/update), format physique du jeu, reperes, calque verrouille (lot A, T7, D5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 8 : miroir pytest de la surface du lot A + banc complet

**Files :**
- Modify : `backend/tests/test_vector_docs.py`

- [ ] **Step 1 : le miroir (RED s'il manque quelque chose)**

```python
def test_le_miroir_lot_a_images_et_cartes():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    html = (vl / "index.html").read_text("utf-8")
    core = (vl / "js" / "core.js").read_text("utf-8")
    # le vendor et sa licence — zéro dépendance payante (D7)
    assert (vl / "vendor" / "imagetracer_v1.2.6.js").is_file()
    lic = (vl / "vendor" / "LICENSE-imagetracerjs.txt").read_text("utf-8")
    assert "public domain" in lic.lower()
    assert 'src="vendor/imagetracer_v1.2.6.js"' in html
    # les trois modules, initialisés par le cœur ; le brouillon AVANT charger()
    for m in ("mod-image.js", "mod-trace.js", "mod-brouillon.js"):
        assert (vl / "js" / m).is_file(), m
        assert m in core, m
    assert core.index("initBrouillon(VL)") < core.index("charger();")
    # le rendu passe le résolveur d'href ; l'overlay trace les repères
    assert "compilerSVG(etat.doc, { image: VL.imageUrl })" in core
    assert "reperes_rects" in core and 'data-repere' in core
    # les surfaces : menu Image (4 sources + vectoriser), panneaux, dialogues
    for tok in ("imgBiblio", "imgFichier", "imgColler", "imgGenerer", "imgVectoriser",
                "panneauImage", "panneauReperes", "libDlg", "traceDlg"):
        assert f'id="{tok}"' in html, tok
    # le banc node porte les cinq bancs du lot
    qa = vl / "qa"
    for b in ("image", "image_ui", "reperes", "trace", "brouillon"):
        assert (qa / f"{b}.test.mjs").is_file(), b
    # le JSON d'un document ne porte JAMAIS de base64 (D1) : l'export inline,
    # pas le modèle
    exp = (vl / "js" / "mod-export.js").read_text("utf-8")
    assert "readAsDataURL" in exp and "image_hrefs" in exp
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    assert "base64" not in doc and "data:image" not in doc
```

- [ ] **Step 2 : exécuter le banc node entier et le banc pytest**

```bash
cd frontend/vectorlab && node qa/run.mjs 2>&1 | tail -30
```

```powershell
Set-Location backend; & $py -m pytest tests/test_vector_docs.py -q 2>&1 | Select-Object -Last 3
```

Relever le total de contrôles node (somme des « PASS (n controles) ») :
275 + 33 + 16 + 13 + 17 + 10 = **364 attendus**.

- [ ] **Step 3 : commit**

```bash
git commit --only backend/tests/test_vector_docs.py -m "vectorlab : miroir pytest de la surface du lot A (vendor, modules, menu Image, panneaux, bancs) (lot A, T8)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Task 9 : preuve en réel

Serveur du worktree sur un port libre avec des données ISOLÉES (rien ne
touche la base de l'utilisateur), backend embarqué de l'app installée :

```powershell
$py = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
$env:DEEPOTUS_DATA_DIR = "<scratchpad>\data_lotA"; New-Item -ItemType Directory -Force $env:DEEPOTUS_DATA_DIR | Out-Null
$env:PORT = "8799"
Set-Location backend; & $py -m uvicorn app.main:app --host 127.0.0.1 --port 8799
```

(en arrière-plan ; `curl -s http://127.0.0.1:8799/api/health`.)

- [ ] **Step 1 : Vectorlab seul** — ouvrir `http://127.0.0.1:8799/vectorlab/`,
  créer un doc « carte » (750×1050, mm/300) ; dans la page : 
  `await VL.poserBlob(await (await fetch("/api/images/<une image réelle de la Library du data dir isolé — sinon un PNG fabriqué au canvas>")).blob())` ;
  lire le DOM : `document.querySelector('#canvasHost [data-objet] image').getAttribute("href")`
  commence par `/api/vector/docs/<id>/images/img1.png` ; **mesurer**
  `document.querySelector('#canvasHost [data-objet]').getBoundingClientRect().height > 0`.
- [ ] **Step 2 : gestes synthétiques** — `pointerdown/pointermove/pointerup`
  sur `#stage` au centre de l'image (outil select) : l'image se déplace
  (x du modèle change) ; poignée 4 : redimensionne ; panneau Image :
  `#imRw` → rognage, viewBox change ; `#imVerrou` → `data-verrou="1"`, un
  nouveau drag ne bouge plus l'objet ; déverrouiller.
- [ ] **Step 3 : repères** — `#repFond` = 3 (mm) → un `rect.repere[data-repere=fondPerdu]`
  dans `#overlay` dont `getBoundingClientRect().width > 0` ; aimantation :
  `VL.aimantePt(35.5, 0)` près de 35.43 px (3 mm à 300 dpi) rend 35.43.
- [ ] **Step 4 : brouillon** — modifier, `VL.brouillonEcrire()`,
  `localStorage.getItem("dz_vl_brouillon_<id>")` non nul ; recharger la
  page : le `confirm` apparaît (le stubber `window.confirm = () => true`
  AVANT `charger` par un rechargement scripté n'est pas possible :
  recharger, accepter dans la boîte du navigateur, puis vérifier
  `VL.etat.sale === true` et l'objet présent) ; Sauver → clé effacée.
- [ ] **Step 5 : le pont complet (LA preuve du spec)** — ouvrir
  `http://127.0.0.1:8799/cardforge/`, créer un jeu de test, onglet
  Vectorlab de la pièce Face, cliquer `#cf-face-vlab-edit` (intercepter
  `window.open`) ; ouvrir le doc : `VL.etat.doc.taille` = `canvas_px` du
  jeu, `unites.dpi` = 300, `reperes` posés, calque c1 verrouillé avec
  l'image `data-verrou`, overlay avec deux `rect.repere` ; `Image ▾ →
  Vectoriser…` : 8 couleurs, Aperçu → `#trApercu svg path` ≥ 1 et
  `#trApercu` `offsetHeight > 0`, Valider → calque « vectorisé » ;
  retoucher (déplacer un chemin) ; Exporter → PNG 2× (200, image/png,
  le fichier `vector_<id>_2x.png` de la Library du data dir) ; retour
  Cardforge : Rafraîchir, « Poser 2× » → `face.src = img:vector_<id>_2x.png`
  et **la jauge lit 600 DPI** (source = 2× canvas_px), c'est-à-dire « la
  jauge DPI reste au 2× ».
- [ ] **Step 6 : négatifs** — Vectoriser sur un doc sans image → toast
  « aucune image dans le document » ; POST d'un JPEG brut sur
  `/images` → 400 ; `Poser 2×` avant export → refus existant.
- [ ] **Step 7 : nettoyer** — arrêter le serveur 8799 ; le data dir isolé
  est jetable (le laisser dans le scratchpad).

Consigner chaque mesure (valeurs lues) dans le relevé de livraison.

---

## Task 10 : déploiement vers `%LOCALAPPDATA%\DeepotusVideoGen`

- [ ] **Step 1 : instantané du commit livré et table de hashes**

```bash
sha=$(git rev-parse HEAD); mkdir -p "$SCRATCH/snap_$sha"
git archive $sha frontend/vectorlab frontend/cardforge/js/core.js frontend/cardforge/js/mod-face.js backend/app/services/vector_store.py backend/app/api/routes.py | tar -x -C "$SCRATCH/snap_$sha"
INST="$LOCALAPPDATA/DeepotusVideoGen"
for f in frontend/cardforge/js/core.js frontend/cardforge/js/mod-face.js backend/app/services/vector_store.py backend/app/api/routes.py frontend/vectorlab/index.html frontend/vectorlab/vectorlab.css frontend/vectorlab/js/core.js frontend/vectorlab/js/mod-doc.js frontend/vectorlab/js/mod-export.js; do
  printf "%-50s installe=%s base=%s cible=%s\n" "$f" "$(git hash-object "$INST/$f" | cut -c1-8)" "$(git rev-parse 5d01db2:$f | cut -c1-8)" "$(git rev-parse $sha:$f | cut -c1-8)"
done
```

Règle : chaque fichier installé doit valoir **base** (`5d01db2`, main
v2.8.0). Sinon STOP et demander (travail tiers non publié).

- [ ] **Step 2 : sauvegarde puis copie depuis l'instantané**

```bash
B="$INST/_backup_predeploy_2026-09-17-vectorlab-lotA"; mkdir -p "$B"
for f in <la même liste>; do mkdir -p "$B/$(dirname $f)"; cp "$INST/$f" "$B/$f"; done
cp -r "$SCRATCH/snap_$sha/frontend/vectorlab/." "$INST/frontend/vectorlab/"
cp "$SCRATCH/snap_$sha/frontend/cardforge/js/core.js" "$INST/frontend/cardforge/js/core.js"
cp "$SCRATCH/snap_$sha/frontend/cardforge/js/mod-face.js" "$INST/frontend/cardforge/js/mod-face.js"
cp "$SCRATCH/snap_$sha/backend/app/services/vector_store.py" "$INST/backend/app/services/vector_store.py"
cp "$SCRATCH/snap_$sha/backend/app/api/routes.py" "$INST/backend/app/api/routes.py"
```

Puis re-dresser la table : chaque installé = **cible**. Les fichiers
NOUVEAUX (mod-image, mod-trace, mod-brouillon, vendor imagetracer +
licence, 5 bancs) : `git hash-object` installé = `git rev-parse $sha:<f>`.

- [ ] **Step 3 : pré-vol du python embarqué**

```powershell
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -c "import sys; sys.path.insert(0, r'$env:LOCALAPPDATA\DeepotusVideoGen\backend'); import app.main; from app.services import vector_store as VS; print('ok', VS.lister_images.__name__)"
```

Aucune migration de base dans ce lot (aucune colonne nouvelle) : rien à
rejouer. Les statiques sont servis immédiatement ; le Python exige la
relance : **c'est l'utilisateur qui relance** (le dire dans le compte
rendu, ne pas lancer `stop.ps1` sans vérifier que le journal
`DeepotusVideoGenData\logs` est muet).

- [ ] **Step 4 : pousser et écrire le relevé de livraison en tête du plan**

```bash
git push origin chantier/vectorlab-affinity
```

Puis remplacer le bloc « RELEVÉ DE LIVRAISON » en tête de ce fichier par le
relevé (livré / prouvé avec valeurs lues / déployé avec hashes / reste),
commit `--only` du plan, push.

---

## Auto-revue (faite à la rédaction)

- **Couverture du §4 lot A** : objet image ✔ (T1) ; 4 sources de pose ✔
  (T4 : Bibliothèque via `__dzLibPicker` du parent ou repli, fichier,
  presse-papiers ×2 voies, génération) ; opacité ✔ (style générique) ;
  rognage ✔ (T1/T4) ; verrou ✔ (T1/T4) ; guides de marge/fond perdu ✔ (T2/T4
  — « marge » = zone sûre) ; pont Cartes retour D5 ✔ (T7 : format physique,
  dpi, calque image verrouillé, repères, Poser 2× existant) ; vectorisation
  D6 avec aperçu, couleurs/lissage/seuil ✔ (T5) ; brouillon 30 s restauré ✔
  (T6) ; preuve du spec ✔ (T9 étape 5).
- **Écarts déclarés** : imagetracerjs est sous Unlicense et non MIT (plus
  permissif, D7 tenu) ; le miroir d'une image ne retourne que sa position
  (comme le texte) ; « depuis une génération » passe par la route
  `/images/generate` existante (dépense la clé, dit dans le libellé) ; le
  sélecteur `__dzLibPicker` n'existe que dans le bundle de la SPA : hors
  iframe (onglet ouvert par le Cardforge) c'est la grille de repli sur
  `/api/images`.
- **Cohérence des noms** : `op_image_rogner / op_image_verrou / op_reperes /
  reperes_rects / reperes_guides / op_vectoriser_poser` (mod-doc) ;
  `href_est_absolu / image_url / image_poser_spec / rognage_normaliser /
  image_hrefs / libListeHTML / initImage` (mod-image) ; `TRACE_DEFAUTS /
  options_trace / definition_trace / tracedata_vers_objets / initTrace`
  (mod-trace) ; `BROUILLON_PERIODE_MS / brouillon_cle / brouillon_faire /
  brouillon_pertinent / brouillon_libelle / initBrouillon` (mod-brouillon) ;
  `VL.imageUrl / VL.poserBlob / VL.vectoriser / VL.brouillonEcrire /
  VL.surCharge / VL.surSauve` (cœur) ; `CF.vector.update / CF.vector.image`,
  `docFaceVec / editerFaceVec` (Cardforge) — identiques dans tous les
  tasks.
