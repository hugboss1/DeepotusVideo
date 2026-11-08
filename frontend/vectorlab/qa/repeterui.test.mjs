// repeterui.test.mjs — lot D2 « Répéter et fusionner » T6 (t455) : le câblage des répétitions et fusions vivantes.
// Un VL factice qui EXÉCUTE vraiment (clone, op, dérivés) et note chaque appel ; `demander` remplacé. Chaque action
// a le bon grisage et appelle la bonne opération ; l'aperçu en direct montre l'essai sans toucher à l'historique et
// rend toujours le document d'avant ; l'onglet Apparence résume la recette ; le menu Vecteur nomme ces actions.
import { repeter_actions, initRepeterUI, resume_vivant, champs_repetition } from "../js/mod-repeterui.js";
import { op_repeter, op_repetition_regler, op_fusionner, op_fusion_regler, op_fusion_annuler, op_fusion_trajectoire,
         op_fusion_inverser_trajectoire, op_fusion_inverser_ordre } from "../js/mod-repeter.js";
import { derives_rafraichir, op_derive_detacher } from "../js/mod-vivants.js";
import { MENUS_BARRE } from "../js/mod-menus.js";
import { T } from "../js/mod-i18n.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const rect = (id, x, y, w = 20, h = 20, fond = "#ff0000") => ({ id, type: "rect", x, y, w, h, style: { fond } });
const cloner = (o) => JSON.parse(JSON.stringify(o));
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
const repetition = () => { const f = faux([rect("a", 90, 40)]); const gid = f.VL.executer(op_repeter, ["a"], "radiale", { nombre: 4, rayon: 50 }); f.appels.length = 0; f.etat.selection = [gid]; return { ...f, gid }; };
const fusion = (extra = []) => { const f = faux([rect("a", 0, 0), rect("b", 300, 0, 20, 20, "#0000ff"), ...extra]); const gid = f.VL.executer(op_fusionner, ["a", "b"], { etapes: 3 }); f.appels.length = 0; f.etat.selection = [gid]; return { ...f, gid }; };
const ACTIONS = ["radiale", "grille", "miroir", "options", "decomposer", "fusionner", "fusionOptions", "fusionAnnuler", "trajectoire", "inverserTrajectoire", "inverserOrdre"];
const actives = (A) => ACTIONS.filter((a) => A.action(a).peut()).join();

/* ── grisage ── */
{
  ok("rien de sélectionné : tout est grisé", actives(repeter_actions(faux([rect("a", 0, 0)]).VL)) === "");
  ok("un objet : les trois répétitions", actives(repeter_actions(faux([rect("a", 0, 0)], ["a"]).VL)) === "radiale,grille,miroir");
  ok("trois objets : pas de fusion", actives(repeter_actions(faux([rect("a", 0, 0), rect("b", 50, 0), rect("c", 90, 0)], ["a", "b", "c"]).VL)) === "radiale,grille,miroir");
  const r2 = repetition();
  r2.etat.doc.calques[0].objets.push(rect("x", 300, 300));
  r2.etat.selection = [r2.gid, "x"];
  ok("une répétition ET un autre objet : ni options ni décomposer", actives(repeter_actions(r2.VL)) === "radiale,grille,miroir,fusionner", actives(repeter_actions(r2.VL)));
  ok("deux objets : répéter et fusionner", actives(repeter_actions(faux([rect("a", 0, 0), rect("b", 50, 0)], ["a", "b"]).VL)) === "radiale,grille,miroir,fusionner");
  ok("une répétition : la répéter encore, ses options, la décomposer", actives(repeter_actions(repetition().VL)) === "radiale,grille,miroir,options,decomposer", actives(repeter_actions(repetition().VL)));
  ok("une fusion : options, décomposer, et tout le menu Fusion sauf créer et trajectoire", actives(repeter_actions(fusion().VL)) === "radiale,grille,miroir,options,decomposer,fusionOptions,fusionAnnuler,inverserTrajectoire,inverserOrdre", actives(repeter_actions(fusion().VL)));
  const f = fusion([{ id: "t", type: "path", d: "M0 100 L300 100", style: {} }]);
  f.etat.selection = [f.gid, "t"];
  ok("une fusion et un chemin : remplacer la trajectoire", repeter_actions(f.VL).action("trajectoire").peut());
  const g = fusion([rect("c", 0, 200), rect("d", 300, 200)]);
  const g2 = g.VL.executer(op_fusionner, ["c", "d"], {});
  g.etat.selection = [g.gid, g2];
  ok("deux fusions : pas de trajectoire", !repeter_actions(g.VL).action("trajectoire").peut());
  g.etat.selection = ["c"];
  ok("action inconnue : grisée", !repeter_actions(g.VL).action("inconnue").peut());
}
/* ── répéter : dialogue pré-rempli, aperçu en direct, application ── */
{
  const f = faux([rect("a", 90, 40)], ["a"]);
  const A = repeter_actions(f.VL);
  const avant = f.etat.doc;
  let spec = null, pendant = null, pendantRefus = null;
  A.demander = async (s) => {
    spec = s;
    s.surChange({ nombre: 6, rayon: 30, orienter: false });
    pendant = cloner(f.etat.doc);
    s.surChange({ nombre: 1, rayon: 30, orienter: false });       // refusé par l'opération : le document d'avant
    pendantRefus = f.etat.doc;
    return { nombre: 6, rayon: 30, orienter: false };
  };
  await A.action("radiale").faire();
  ok("radiale : dialogue titré, champs nombre / rayon / orienter", spec.titre === T("vectorlab.repeter.d_radiale") && spec.champs.map((c) => c.id).join() === "nombre,rayon,orienter");
  ok("radiale : pré-rempli des défauts (8, demi-diagonale arrondie, orienter)", spec.champs[0].valeur === 8 && spec.champs[1].valeur === 14.14 && spec.champs[2].valeur === true, JSON.stringify(spec.champs.map((c) => c.valeur)));
  ok("aperçu : le document montré est l'essai (6 instances)", pendant && pendant.calques[0].objets[0].repetition && pendant.calques[0].objets[0].enfants.length === 6, JSON.stringify(pendant && pendant.calques[0].objets.map((o) => o.id)));
  ok("aperçu refusé : le document d'avant est montré", pendantRefus === avant);
  ok("aperçu : rendu à chaque changement et à la fermeture", f.rendus() >= 3, f.rendus());
  ok("appliquer : UNE exécution d'op_repeter avec les valeurs", f.appels.length === 1 && f.appels[0].fn === op_repeter && JSON.stringify(f.appels[0].args) === '[["a"],"radiale",{"nombre":6,"rayon":30,"orienter":false}]', JSON.stringify(f.appels.map((x) => x.args)));
  ok("appliquer : le groupe vivant est sélectionné", f.selections.length === 1 && f.etat.doc.calques[0].objets[0].id === f.selections[0][0]);
}
{
  const f = faux([rect("a", 90, 40)], ["a"]);
  const A = repeter_actions(f.VL);
  const avant = f.etat.doc;
  A.demander = async (s) => { s.surChange({ lignes: 2, colonnes: 2, ecartX: 0, ecartY: 0, decalage: "hexagones", miroirLignes: false, miroirColonnes: false }); return null; };
  await A.action("grille").faire();
  ok("annuler le dialogue : aucune exécution, document d'avant rendu", f.appels.length === 0 && f.etat.doc === avant);
  let champs = null;
  A.demander = async (s) => { champs = s.champs; throw new Error("fenêtre fermée"); };
  let lance = false;
  try { await A.action("miroir").faire(); } catch (e) { lance = true; }
  ok("dialogue qui échoue : le document d'avant est quand même rendu", lance && f.etat.doc === avant && champs.map((c) => c.id).join() === "angle,ecart");
  const t = faux([{ id: "t", type: "texte", x: 0, y: 0, texte: "x", style: {} }], ["t"]);
  const At = repeter_actions(t.VL);
  At.demander = async () => { throw new Error("ne doit pas s'ouvrir"); };
  await At.action("radiale").faire();
  ok("un texte : pas de dialogue, un message", t.toasts.length === 1 && t.toasts[0][0] === T("vectorlab.repeter.source_type") && t.toasts[0][1]);
}
{
  const r = repetition();
  const A = repeter_actions(r.VL);
  let spec = null;
  A.demander = async (s) => { spec = s; return { nombre: 12, rayon: 50, orienter: true }; };
  await A.action("options").faire();
  ok("options de répétition : pré-remplies de la recette", spec.champs[0].valeur === 4 && spec.champs[1].valeur === 50);
  ok("options de répétition : op_repetition_regler", r.appels.length === 1 && r.appels[0].fn === op_repetition_regler && r.appels[0].args[0] === r.gid && r.etat.doc.calques[0].objets[0].enfants.length === 12);
  A.demander = async () => null;
  await A.action("options").faire();
  ok("options de répétition annulées : rien n'est exécuté", r.appels.length === 1);
  A.action("decomposer").faire();
  ok("décomposer : op_derive_detacher", r.appels[1].fn === op_derive_detacher && !r.etat.doc.calques[0].objets[0].repetition);
}
/* ── fusion ── */
{
  const f = fusion();
  let spec = null;
  const A = repeter_actions(f.VL);
  A.demander = async (s) => { spec = s; return null; };
  await A.action("fusionOptions").faire();
  ok("options de fusion : pré-remplies de la recette (3 étapes), annulées sans exécution", spec.champs.find((c) => c.id === "etapes").valeur === 3 && f.appels.length === 0);
}
{
  const f = faux([rect("a", 0, 0), rect("b", 300, 0)], ["a", "b"]);
  const A = repeter_actions(f.VL);
  A.action("fusionner").faire();
  const gid = f.etat.doc.calques[0].objets[0].id;
  ok("fusionner : op_fusionner, le groupe sélectionné", f.appels[0].fn === op_fusionner && JSON.stringify(f.selections[0]) === JSON.stringify([gid]));
  let spec = null;
  A.demander = async (s) => { spec = s; return { mode: "etapes", etapes: 2, pas: 20, orienter: false }; };
  await A.action("fusionOptions").faire();
  ok("options de fusion : champs mode / étapes / pas / orienter, op_fusion_regler", spec.champs.map((c) => c.id).join() === "mode,etapes,pas,orienter" && spec.champs[0].valeur === "etapes" && spec.champs[1].valeur === 5
     && f.appels[1].fn === op_fusion_regler && f.etat.doc.calques[0].objets[0].enfants.length === 4);
  await A.action("options").faire();
  ok("« Options… » sur une fusion : les options de fusion", f.appels[2].fn === op_fusion_regler);
  A.action("inverserOrdre").faire();
  ok("inverser l'ordre : op_fusion_inverser_ordre", f.appels[3].fn === op_fusion_inverser_ordre && f.etat.doc.calques[0].objets[0].enfants[0].id === "b");
  A.action("inverserTrajectoire").faire();
  ok("inverser la trajectoire : op_fusion_inverser_trajectoire", f.appels[4].fn === op_fusion_inverser_trajectoire);
  A.action("fusionAnnuler").faire();
  ok("annuler la fusion : op_fusion_annuler, A et B sélectionnés", f.appels[5].fn === op_fusion_annuler && f.selections[f.selections.length - 1].slice().sort().join() === "a,b");
}
{
  const f = fusion([{ id: "t", type: "path", d: "M0 100 L300 100", style: { contour: "#000" } }]);
  f.etat.selection = ["t", f.gid];
  repeter_actions(f.VL).action("trajectoire").faire();
  ok("trajectoire : op_fusion_trajectoire(fusion, chemin), la fusion sélectionnée", f.appels[0].fn === op_fusion_trajectoire && JSON.stringify(f.appels[0].args) === JSON.stringify([f.gid, "t"])
     && JSON.stringify(f.selections[0]) === JSON.stringify([f.gid]) && f.etat.doc.calques[0].objets[0].fusion_vive.trajectoire === "t");
}
/* ── onglet Apparence ── */
{
  const r = repetition();
  const A = repeter_actions(r.VL);
  const g = r.etat.doc.calques[0].objets[0];
  const h = A.sectionApparence(g);
  ok("Apparence d'une répétition : titre, résumé, Options…, Décomposer (a2Detacher)", h.includes(T("vectorlab.repeter.a_titre")) && h.includes(resume_vivant(g)) && h.includes('id="a2VivantOptions"') && h.includes('id="a2Detacher"'), h);
  ok("Apparence d'un objet ordinaire : rien", A.sectionApparence({ id: "x", type: "rect" }) === "" && A.sectionApparence(null) === "");
  ok("résumé radial", resume_vivant(g) === T("vectorlab.repeter.resume_radiale", { nombre: 4, rayon: 50 }));
  ok("résumé grille", resume_vivant({ repetition: { mode: "grille", params: { lignes: 2, colonnes: 5 } } }) === T("vectorlab.repeter.resume_grille", { lignes: 2, colonnes: 5 }));
  ok("résumé miroir", resume_vivant({ repetition: { mode: "miroir", params: { angle: 90, ecart: 0 } } }) === T("vectorlab.repeter.resume_miroir", { angle: 90 }));
  const fu = fusion();
  const fg = fu.etat.doc.calques[0].objets[0];
  ok("résumé fusion : le nombre d'intermédiaires", resume_vivant(fg) === T("vectorlab.fusion.resume", { n: 3 }) && repeter_actions(fu.VL).sectionApparence(fg).includes(T("vectorlab.fusion.a_titre")));
  ok("résumé fusion sur trajectoire", resume_vivant({ ...fg, fusion_vive: { ...fg.fusion_vive, trajectoire: "t" } }) === T("vectorlab.fusion.resume_trajectoire", { n: 3 }));
  ok("champs de grille : le décalage propose les hexagones", champs_repetition("grille", { lignes: 3, colonnes: 3, ecartX: 0, ecartY: 0, decalage: "aucun", miroirLignes: false, miroirColonnes: false })
     .find((c) => c.id === "decalage").options.map(([v]) => v).join() === "aucun,brique_lignes,brique_colonnes,hexagones");
}
/* ── init et menus ── */
{
  const f = faux([rect("a", 0, 0)]);
  const A = initRepeterUI(f.VL);
  ok("initRepeterUI pose VL.repeterUI et VL.actions.repeter", f.VL.repeterUI === A && f.VL.actions.repeter === A);
  const vec = MENUS_BARRE.find((m) => m.entrees.some((x) => x.action === "bool:union"));
  const actions = vec ? vec.entrees.filter((x) => x !== "-").map((x) => x.action) : [];
  const voulues = ["radiale", "grille", "miroir", "options", "decomposer", "fusionner", "fusionOptions", "fusionAnnuler", "trajectoire", "inverserTrajectoire", "inverserOrdre"].map((a) => "repeter:" + a);
  ok("menu Vecteur : les 11 commandes Répétition et Fusion y sont", voulues.every((a) => actions.includes(a)), voulues.filter((a) => !actions.includes(a)).join());
  ok("Fusion › Créer : Ctrl+Alt+B", vec && (vec.entrees.find((x) => x.action === "repeter:fusionner") || {}).raccourci === "ctrl+alt+b");
  const tous = MENUS_BARRE.flatMap((m) => m.entrees.filter((x) => x !== "-"));
  ok("Ctrl+Alt+B n'est pris par aucune autre entrée", tous.filter((x) => x.raccourci === "ctrl+alt+b").length === 1);
  ok("libellés traduits (pas de clé brute)", vec && vec.entrees.filter((x) => x !== "-" && String(x.action).startsWith("repeter:")).every((x) => !/^vectorlab\./.test(x.libelle)));
}

if (echecs.length) {
  console.error(`repeterui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("repeterui : ok");
