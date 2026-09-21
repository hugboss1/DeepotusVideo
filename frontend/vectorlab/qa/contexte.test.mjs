// contexte.test.mjs — mod-contexte : la barre contextuelle d'Affinity —
// libellé de la sélection, champs inline par outil, application pure
// des changements, paramètres de l'appli (dz_vl_params). Feuille.
import { libelle_selection, champs_de, appliquer_champ, PARAMS_DEFAUT, params_lire, params_poser } from "../js/mod-contexte.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 250) : "")); };
{
  ok("libellé : aucune / 1 objet · type / n objets / état vide", libelle_selection([]) === "Aucune sélection" && libelle_selection([{ type: "rect" }]) === "1 objet · rect" && libelle_selection([{ type: "rect" }, { type: "path" }]) === "2 objets" && libelle_selection(null) === "Aucune sélection");
  ok("select sans sélection : bascule Sélection auto puis boutons Configuration et Paramètres", champs_de("select", { selection: [] }).map((c) => c.id).join() === "selectionAuto,configDoc,parametres", JSON.stringify(champs_de("select", { selection: [] })));
  ok("select avec sélection : opacité de l'objet de tête (en %)", champs_de("select", { selection: ["a"], objets: [{ type: "rect", style: { opacite: 0.5 } }], bbox: { x: 0, y: 0, w: 1, h: 1 } }).some((c) => c.id === "opacite" && c.valeur === 50 && c.type === "number"));
  ok("select avec sélection sans opacité : 100", champs_de("select", { selection: ["a"], objets: [{ type: "rect", style: {} }], bbox: { x: 0, y: 0, w: 1, h: 1 } }).find((c) => c.id === "opacite").valeur === 100);
  const f = champs_de("forme", { formeCourante: "etoile", formes: [{ id: "etoile", nom: "Étoile" }, { id: "polygone", nom: "Polygone" }] });
  ok("forme : un select des formes avec la courante ; gomme / coin : un nombre", f[0].type === "select" && f[0].valeur === "etoile" && f[0].options.length === 2 && f[0].options[0].libelle === "Étoile" && champs_de("gomme", { gommeLargeur: 12 })[0].valeur === 12 && champs_de("gomme", { gommeLargeur: 12 })[0].type === "number" && champs_de("coin", { coinRayon: 10 })[0].id === "coinRayon", JSON.stringify(f));
  ok("pinceau vectoriel et crayon : profil + largeur", champs_de("pinceauv", { pinceauv: { profil: "plat", largeur: 8 }, profils: [{ id: "plat", libelle: "Plat" }, { id: "fuseau", libelle: "Fuseau" }] }).map((c) => c.id).join() === "pvProfil,pvLargeur" && champs_de("crayon", { pinceauv: { profil: "plat", largeur: 8 }, profils: [] }).map((c) => c.id).join() === "pvProfil,pvLargeur");
  ok("raster : rayon + dureté (+ forme, secondaire, pipette au pinceau depuis les lots 2-3), cloner, tolérance + global (seau), tolérance (baguette), rien (lasso)", champs_de("px-pinceau", { px: { rayon: 4, durete: 1 } }).map((c) => c.id).join() === "pxRayon,pxDurete,pxForme,pxSecondaire,pxPipetteMode" && champs_de("px-cloner", { px: { rayon: 4, durete: 1 } }).length === 2 && champs_de("px-seau", { px: { tolerance: 16, global: false } }).map((c) => c.id).join() === "pxTolerance,pxGlobal,pxPipetteMode" && champs_de("px-baguette", { px: { tolerance: 16 } }).map((c) => c.id).join() === "pxTolerance" && champs_de("px-lasso", { px: {} }).length === 0);
  ok("tuiles : le terrain courant parmi les terrains ; texte : la police courante", champs_de("tuiles", { terrainCourant: "mer", terrains: { mer: { nom: "Mer" }, plaine: { nom: "Plaine" } } })[0].options.length === 2 && champs_de("tuiles", { terrainCourant: "mer", terrains: { mer: { nom: "Mer" } } })[0].valeur === "mer" && champs_de("texte", { typo: { courante: "lib:a", polices: [{ id: "lib:a", famille: "A" }], styleDefaut: { police: "A" } } })[0].valeur === "lib:a" && champs_de("texte", { typo: { polices: [] } }).length === 8);
  ok("texte (R11) : un texte sélectionné en outil Sélection montre ses champs de style ; un champ tx* → patch styleTexte", champs_de("select", { selection: ["t"], objets: [{ type: "texte", style: { corps: 30 } }], bbox: { x: 0, y: 0, w: 1, h: 1 }, typo: { polices: [] } }).some((c) => c.id === "txCorps" && c.valeur === 30) && appliquer_champ({}, "txCorps", 40).styleTexte.corps === 40 && appliquer_champ({}, "selectionAuto", false).selectionAuto === false);
  ok("tranche : le mode d'export", champs_de("tranche", { exportPlus: { mode: "document" } })[0].id === "trMode" && champs_de("tranche", { exportPlus: { mode: "document" } })[0].options.length >= 3);
  ok("plume (R8) : select du mode + huit boutons d'action plume:<action> ; plumeMode appliqué sous plume, valeur inconnue → plume", (() => { const c = champs_de("plume", { plume: { mode: "polygone" } }); return c[0].id === "plumeMode" && c[0].valeur === "polygone" && c[0].options.length === 4 && c.length === 10 && c[1].id === "plume:vif" && c[3].id === "plume:intelligent" && c[9].id === "plume:inverser" && appliquer_champ({}, "plumeMode", "ligne").plume.mode === "ligne" && appliquer_champ({}, "plumeMode", "zz").plume.mode === "plume"; })());
  ok("noeuds (R9) : les huit actions plume:* puis six alignements noeuds:al-*", (() => { const c = champs_de("noeuds", {}); return c.length === 16 && c[0].id === "plume:vif" && c[9].id === "noeuds:al-gauche" && c[14].id === "noeuds:al-bas" && c[15].id === "aimantNoeuds" && c[15].type === "bascule" && c[15].valeur === true && appliquer_champ({}, "aimantNoeuds", false).aimantNoeuds === false; })());
  ok("select avec sélection (R10) : X · Y · L · H de la boîte puis opacité ; appliquer → patch bbox", (() => { const c = champs_de("select", { selection: ["a"], objets: [{ type: "rect", style: {} }], bbox: { x: 10, y: 20, w: 30, h: 40 } }); return c.map((x) => x.id).join() === "selectionAuto,selX,selY,selW,selH,opacite" && c[1].valeur === 10 && c[4].valeur === 40 && appliquer_champ({}, "selW", 99).bbox.w === 99 && appliquer_champ({}, "selW", 0).bbox.w === 1; })());
  ok("état vide : outil inconnu → [], état absent → [], listes absentes → select sans option mais pas d'exception", champs_de("zz", {}).length === 0 && champs_de("gomme", null).length === 0 && champs_de("forme", {})[0].options.length === 0 && champs_de("tuiles", {})[0].options.length === 0);
  ok("appliquer : gommeLargeur borné ≥ 1, pxDurete borné 0..1, pvProfil posé sous pinceauv sans perdre la largeur, formeCourante posée", appliquer_champ({}, "gommeLargeur", 0).gommeLargeur === 1 && appliquer_champ({}, "pxDurete", 250).px.durete === 1 && appliquer_champ({ pinceauv: { largeur: 8 } }, "pvProfil", "plat").pinceauv.profil === "plat" && appliquer_champ({ pinceauv: { largeur: 8 } }, "pvProfil", "plat").pinceauv.largeur === 8 && appliquer_champ({}, "formeCourante", "etoile").formeCourante === "etoile");
  ok("appliquer : champ inconnu → objet vide ; opacite → patch de style 0..1 ; pxGlobal → booléen ; terrain, police, mode", Object.keys(appliquer_champ({}, "zz", 1)).length === 0 && appliquer_champ({}, "opacite", 50).style.opacite === 0.5 && appliquer_champ({}, "opacite", 500).style.opacite === 1 && appliquer_champ({}, "pxGlobal", "true").px.global === true && appliquer_champ({}, "terrainCourant", "mer").terrainCourant === "mer" && appliquer_champ({}, "typoCourante", "lib:a").typo.courante === "lib:a" && appliquer_champ({}, "trMode", "objets").exportPlus.mode === "objets");
  ok("params : défauts (bulles, grille 8, aimant), lecture tolérante, pose immuable, clé inconnue refusée", PARAMS_DEFAUT.bulles === true && PARAMS_DEFAUT.grillePas === 8 && PARAMS_DEFAUT.aimant === true && params_lire("{oops").grillePas === 8 && params_lire(null).bulles === true && params_lire('{"bulles":false,"zz":1,"grillePas":"x"}').bulles === false && params_lire('{"grillePas":"x"}').grillePas === 8 && params_poser(PARAMS_DEFAUT, "grillePas", 16).grillePas === 16 && PARAMS_DEFAUT.grillePas === 8 && params_poser(PARAMS_DEFAUT, "zz", 1) === PARAMS_DEFAUT);
}
{
  const px = { rayon: 4, durete: 1, forme: "carre", parfait: false, secondaire: null };
  const c1 = champs_de("px-pinceau", { px }).map((c) => c.id);
  ok("lot 2 — pinceau : champ Forme (rond / carré) et Secondaire", c1.includes("pxForme") && c1.includes("pxSecondaire"), c1.join());
  const c2 = champs_de("px-crayon", { px });
  ok("lot 2 — crayon : bascule Pixel-parfait (valeur lue dans etat.px.parfait) + Secondaire", c2.some((c) => c.id === "pxParfait" && c.type === "bascule" && c.valeur === false) && c2.some((c) => c.id === "pxSecondaire" && c.type === "couleur"));
  ok("lot 2 — gomme : Forme mais pas Secondaire", champs_de("px-gomme", { px }).some((c) => c.id === "pxForme") && !champs_de("px-gomme", { px }).some((c) => c.id === "pxSecondaire"));
  ok("lot 2 — appliquer : pxForme borné à rond / carré, pxParfait booléen, pxSecondaire hex ou null (vide = transparent)", appliquer_champ({ px }, "pxForme", "carre").px.forme === "carre" && appliquer_champ({ px }, "pxForme", "zz").px.forme === "rond" && appliquer_champ({ px }, "pxParfait", "true").px.parfait === true && appliquer_champ({ px }, "pxSecondaire", "#ff00aa").px.secondaire === "#FF00AA" && appliquer_champ({ px }, "pxSecondaire", "").px.secondaire === null);
}
{
  const px = { rayon: 4, durete: 1, pipetteMode: "exact" };
  const c = champs_de("px-crayon", { px }).find((x) => x.id === "pxPipetteMode");
  ok("lot 3 — crayon : select Pipette (exacte / moyenne / dominante) avec la valeur de etat.px", c && c.type === "select" && c.valeur === "exact" && c.options.length === 3);
  ok("lot 3 — pinceau et seau : Pipette aussi ; gomme non", champs_de("px-pinceau", { px }).some((x) => x.id === "pxPipetteMode") && champs_de("px-seau", { px }).some((x) => x.id === "pxPipetteMode") && !champs_de("px-gomme", { px }).some((x) => x.id === "pxPipetteMode"));
  ok("lot 3 — appliquer : pxPipetteMode borné, inconnu → moyenne", appliquer_champ({ px }, "pxPipetteMode", "dominante").px.pipetteMode === "dominante" && appliquer_champ({ px }, "pxPipetteMode", "zz").px.pipetteMode === "moyenne");
}
{
  // 21/09 : la barre en ICÔNES — chaque bouton d'action porte une icône connue et garde son libellé (la bulle)
  const { ICONES } = await import("../js/mod-icones.js");
  const { boutons_groupes } = await import("../js/mod-contexte.js");
  const n = champs_de("noeuds", {}).filter((c) => c.type === "bouton");
  ok("icônes (21/09) : les 15 boutons de l'outil Nœuds portent une icône d'ICONES et un libellé", n.length === 15 && n.every((c) => c.icone && ICONES[c.icone] && c.libelle), n.map((c) => c.id + ":" + c.icone).join());
  const pl = champs_de("plume", {}).filter((c) => c.type === "bouton");
  ok("icônes (21/09) : les boutons de la Plume aussi", pl.length === 9 && pl.every((c) => c.icone && ICONES[c.icone]));
  const s0 = champs_de("select", { selection: [] }).filter((c) => c.type === "bouton");
  ok("icônes (21/09) : Configuration du document et Paramètres de l'appli en icônes", s0.length === 2 && s0.every((c) => c.icone && ICONES[c.icone]));
  const g = boutons_groupes(champs_de("noeuds", {}));
  ok("boutons_groupes : les actions plume:* puis les alignements noeuds:al-* forment deux groupes ; état vide → []", g.length === 2 && g[0].length === 9 && g[1].length === 6 && boutons_groupes([]).length === 0, JSON.stringify(g.map((x) => x.length)));
}
if (echecs.length) { console.error("ECHECS contexte :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA contexte : PASS (24 controles)");
