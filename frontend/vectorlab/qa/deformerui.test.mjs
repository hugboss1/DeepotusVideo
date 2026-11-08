// deformerui.test.mjs — lot D3 « Déformer » T6 (t465) : le câblage des déformations vivantes. Un VL factice qui
// EXÉCUTE vraiment (clone, op, dérivés) et note chaque appel ; `demander` remplacé. Les actions « repeter:def-<x> »
// passent par mod-repeterui.js ; dialogues pré-remplis à aperçu ; Options, Modifier le contenu, Annuler, Décomposer ;
// section Apparence ; le menu Vecteur nomme le bloc Déformer.
import { deformer_actions, initDeformerUI, champs_deformation, params_formulaire, resume_deformation, EFFETS_MENU } from "../js/mod-deformerui.js";
import { repeter_actions } from "../js/mod-repeterui.js";
import { op_deformer, op_deformation_regler, op_deformation_editer, op_deformation_annuler } from "../js/mod-deformer.js";
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { MENUS_BARRE } from "../js/mod-menus.js";
import { T } from "../js/mod-i18n.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const cloner = (o) => JSON.parse(JSON.stringify(o));
const rect = (id, x = 100, y = 100, w = 200, h = 100) => ({ id, type: "rect", x, y, w, h, style: { fond: "#3a6fd0" } });
function faux(objets, selection = []) {
  const appels = [], toasts = [], selections = [];
  let rendus = 0;
  const etat = { doc: { v: 1, taille: { w: 400, h: 400 }, calques: [{ id: "c", objets }] }, selection };
  const trouver = (id) => { let r = null; (function v(l) { for (const o of l) { if (o.id === id) r = o; if (o.type === "groupe") v(o.enfants || []); } })(etat.doc.calques[0].objets); return r; };
  const VL = {
    etat,
    executer: (fn, ...args) => {
      appels.push({ fn, args: cloner(args) });
      try { const essai = cloner(etat.doc); const r = fn(essai, ...args); derives_rafraichir(essai); etat.doc = essai; return r; }
      catch (e) { toasts.push([e.message, true]); return undefined; }
    },
    setSelection: (ids) => { selections.push(ids); etat.selection = ids.slice(); },
    toast: (m, err) => toasts.push([m, !!err]),
    objetDe: (id) => { const o = trouver(id); return o ? { objet: o } : null; },
    rendre: () => { rendus++; },
  };
  return { VL, etat, appels, toasts, selections, rendus: () => rendus };
}
const avecDeformation = (effet = "enveloppe", params = { style: "arc", courbure: 40 }) => {
  const f = faux([rect("a")]);
  const gid = f.VL.executer(op_deformer, ["a"], effet, params);
  f.appels.length = 0; f.etat.selection = [gid];
  initDeformerUI(f.VL);
  return { ...f, gid };
};

/* ── grisage et délégation par mod-repeterui ── */
{
  const f = faux([rect("a")], []);
  initDeformerUI(f.VL);
  const R = repeter_actions(f.VL);
  ok("rien de sélectionné : les sept effets grisés", EFFETS_MENU.every((e) => !R.action("def-" + e).peut()));
  f.etat.selection = ["a"];
  ok("un objet : les sept effets actifs (par repeter:def-<x>)", EFFETS_MENU.every((e) => R.action("def-" + e).peut()));
  ok("un objet ordinaire : modifier le contenu, annuler, options grisés", !R.action("def-editer").peut() && !R.action("def-annuler").peut() && !R.action("def-options").peut() && !R.action("options").peut());
  ok("sans module D3 chargé : def-<x> grisé", !repeter_actions(faux([rect("a")], ["a"]).VL).action("def-enveloppe").peut());
  const g = avecDeformation();
  const Rg = repeter_actions(g.VL);
  ok("une déformation : modifier le contenu, annuler, options, décomposer actifs", Rg.action("def-editer").peut() && Rg.action("def-annuler").peut() && Rg.action("options").peut() && Rg.action("decomposer").peut());
  g.etat.doc.calques[0].objets.push(rect("x", 0, 0, 5, 5));
  g.etat.selection = [g.gid, "x"];
  ok("une déformation ET un autre objet : modifier le contenu et annuler grisés", !Rg.action("def-editer").peut() && !Rg.action("def-annuler").peut());
  g.etat.selection = [g.gid];
  ok("action inconnue : grisée", !Rg.action("def-spirale").peut() && !deformer_actions(g.VL).action("spirale").peut());
}
/* ── créer : dialogue pré-rempli, aperçu, application ── */
{
  const f = faux([rect("a")], ["a"]);
  const A = initDeformerUI(f.VL);
  const avant = f.etat.doc;
  let spec = null, pendant = null;
  A.demander = async (s) => { spec = s; s.surChange({ style: "drapeau", courbure: 60, orientation: "horizontale", distH: 0, distV: 0 }); pendant = cloner(f.etat.doc); return { style: "drapeau", courbure: 60, orientation: "horizontale", distH: 0, distV: 0 }; };
  await A.action("enveloppe").faire();
  ok("enveloppe : dialogue titré, champs style / courbure / orientation / distorsions", spec.titre === T("vectorlab.deformer.d_enveloppe") && spec.champs.map((c) => c.id).join() === "style,courbure,orientation,distH,distV");
  ok("enveloppe : les 15 styles proposés, traduits", spec.champs[0].options.length === 15 && spec.champs[0].options.every(([, l]) => !/^vectorlab\./.test(l)));
  ok("aperçu : le document montré porte la déformation", pendant.calques[0].objets[0].deformation && pendant.calques[0].objets[0].deformation.params.style === "drapeau");
  ok("appliquer : UNE exécution d'op_deformer, le groupe sélectionné", f.appels.length === 1 && f.appels[0].fn === op_deformer && f.appels[0].args[1] === "enveloppe"
     && JSON.stringify(f.selections[0]) === JSON.stringify([f.etat.doc.calques[0].objets[0].id]) && f.etat.doc !== avant);
  A.demander = async () => null;
  const avant2 = f.etat.doc;
  f.etat.selection = ["a"];
  await A.action("torsion").faire();
  ok("annuler le dialogue : aucune exécution, document d'avant", f.appels.length === 1 && f.etat.doc === avant2);
}
{
  // distorsion : huit champs regroupés en quatre coins
  ok("distorsion : 8 champs pré-remplis à zéro", champs_deformation("distorsion").length === 8 && champs_deformation("distorsion").every((c) => c.valeur === 0));
  ok("distorsion : les huit nombres deviennent quatre coins", JSON.stringify(params_formulaire("distorsion", { c0x: 1, c0y: 2, c1x: 3, c1y: 4, c2x: 5, c2y: 6, c3x: 7, c3y: 8 })) === '{"coins":[[1,2],[3,4],[5,6],[7,8]]}');
  ok("autres effets : valeurs passées telles quelles", JSON.stringify(params_formulaire("torsion", { angle: 30 })) === '{"angle":30}');
  ok("pointes : début, fin, échelle ; 6 styles", champs_deformation("pointes").map((c) => c.id).join() === "debut,fin,echelle" && champs_deformation("pointes")[0].options.length === 6);
  ok("rugosité, zigzag, contraction : leurs champs", champs_deformation("rugosite").map((c) => c.id).join() === "taille,details,lisse,graine"
     && champs_deformation("zigzag").map((c) => c.id).join() === "taille,cretes,lisse" && champs_deformation("gonfler").map((c) => c.id).join() === "pourcent");
  ok("pré-remplis par une recette", champs_deformation("torsion", { angle: 77 })[0].valeur === 77 && champs_deformation("enveloppe", { style: "vague", courbure: -20 })[1].valeur === -20);
  const f = faux([rect("a")], ["a"]);
  const A = initDeformerUI(f.VL);
  A.demander = async () => ({ c0x: -20, c0y: -10, c1x: 0, c1y: 0, c2x: 0, c2y: 0, c3x: 0, c3y: 0 });
  await A.action("distorsion").faire();
  ok("distorsion appliquée avec des coins", f.appels[0].fn === op_deformer && JSON.stringify(f.appels[0].args[2]) === '{"coins":[[-20,-10],[0,0],[0,0],[0,0]]}', JSON.stringify(f.appels[0].args));
}
/* ── options, modifier le contenu, annuler, décomposer ── */
{
  const g = avecDeformation();
  const A = g.VL.deformerUI;
  let spec = null;
  A.demander = async (s) => { spec = s; return { style: "arc", courbure: 70, orientation: "horizontale", distH: 0, distV: 0 }; };
  await repeter_actions(g.VL).action("options").faire();
  ok("« Options… » sur une déformation : ses options pré-remplies, op_deformation_regler", spec.champs[1].valeur === 40 && g.appels[0].fn === op_deformation_regler && g.etat.doc.calques[0].objets[0].deformation.params.courbure === 70);
  A.demander = async () => null;
  await repeter_actions(g.VL).action("options").faire();
  ok("options annulées : rien n'est exécuté", g.appels.length === 1);
  A.action("editer").faire();
  ok("modifier le contenu : op_deformation_editer", g.appels[1].fn === op_deformation_editer && g.etat.doc.calques[0].objets[0].deformation.edition === true);
  repeter_actions(g.VL).action("decomposer").faire();
  ok("décomposer : op_derive_detacher, plus de recette", g.appels[2].fn === op_derive_detacher && !g.etat.doc.calques[0].objets[0].deformation);
  const h = avecDeformation();
  h.VL.deformerUI.action("annuler").faire();
  ok("annuler : op_deformation_annuler, la source sélectionnée", h.appels[0].fn === op_deformation_annuler && JSON.stringify(h.selections[0]) === '["a"]');
}
/* ── Apparence ── */
{
  const g = avecDeformation();
  const o = g.etat.doc.calques[0].objets[0];
  const html = repeter_actions(g.VL).sectionApparence(o);
  ok("Apparence : la section vivante de la déformation, par mod-repeterui", html.includes(T("vectorlab.deformer.a_titre")) && html.includes('id="a2VivantOptions"') && html.includes('id="a2DefEditer"') && html.includes('id="a2Detacher"'), html);
  ok("résumé enveloppe : style traduit et courbure", resume_deformation(o) === T("vectorlab.deformer.r_enveloppe", { style: T("vectorlab.deformer.s_arc"), courbure: 40 }));
  ok("résumés torsion et contraction", resume_deformation({ deformation: { effet: "torsion", params: { angle: 30 } } }) === T("vectorlab.deformer.r_torsion", { angle: 30 })
     && resume_deformation({ deformation: { effet: "gonfler", params: { pourcent: -20 } } }) === T("vectorlab.deformer.r_gonfler", { pourcent: -20 }));
  ok("résumé des autres effets : le titre de l'effet", resume_deformation({ deformation: { effet: "zigzag", params: {} } }) === T("vectorlab.deformer.d_zigzag"));
  ok("Apparence en édition : le bouton dit « Terminer »", g.VL.deformerUI.sectionApparence({ ...o, deformation: { ...o.deformation, edition: true } }).includes(T("vectorlab.deformer.a_editer_fin")));
  ok("Apparence d'un objet ordinaire : rien", g.VL.deformerUI.sectionApparence({ id: "x", type: "rect" }) === "" && resume_deformation(null) === "");
}
/* ── menu ── */
{
  const vec = MENUS_BARRE.find((m) => m.entrees.some((x) => x.action === "bool:union"));
  const actions = vec.entrees.filter((x) => x !== "-").map((x) => x.action);
  const voulues = [...EFFETS_MENU, "editer", "annuler"].map((a) => "repeter:def-" + a);
  ok("menu Vecteur : les 9 entrées du bloc Déformer", voulues.every((a) => actions.includes(a)), voulues.filter((a) => !actions.includes(a)).join());
  ok("libellés traduits", vec.entrees.filter((x) => x !== "-" && String(x.action).startsWith("repeter:def-")).every((x) => !/^vectorlab\./.test(x.libelle)));
}

if (echecs.length) {
  console.error(`deformerui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("deformerui : ok");
