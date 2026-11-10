// pinceauxui.test.mjs — lot D5 « Couleur et motif » (t481) : les pinceaux dans l'interface (js/mod-pinceauxui.js, VL
// factice) — Vecteur › Nouveau pinceau…, Appliquer un pinceau… (aperçu en direct), Options du pinceau…, Retirer le
// pinceau, Supprimer un pinceau… ; la section « Pinceau vivant » de l'onglet Apparence, branchée par mod-repeterui.js.
import { createRequire } from "node:module";
import { pinceaux_actions, champs_pinceau, resume_pinceau } from "../js/mod-pinceauxui.js";
import { op_pinceau_creer, op_pinceau_appliquer } from "../js/mod-pinceaux.js";
import { repeter_actions } from "../js/mod-repeterui.js";
import { couleurs_actions } from "../js/mod-recolorerui.js";
import { fournirMartinez } from "../js/mod-bool.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const doc = () => ({ v: 1, taille: { w: 300, h: 300 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
  { id: "haut", type: "rect", x: 200, y: 200, w: 20, h: 1, style: { fond: "#ff0000" } },
  { id: "bas", type: "rect", x: 200, y: 203, w: 20, h: 1, style: { fond: "#0000ff" } },
  { id: "trace", type: "path", d: "M0 50 L100 50", style: { fond: "none", contour: "#000000" } },
  { id: "trace2", type: "path", d: "M0 80 L100 80", style: { fond: "none", contour: "#000000" } }] }] });
const obj = (d, id) => d.calques[0].objets.find((o) => o.id === id);
const vl = (d, sel) => {
  const VL = { etat: { doc: d, selection: sel }, toasts: [],
    executer(fn, ...a) { try { const x = JSON.parse(JSON.stringify(VL.etat.doc)); const r = fn(x, ...a); VL.etat.doc = x; return r; } catch (e) { VL.toast(e.message, true); return undefined; } },
    toast(m, e) { VL.toasts.push([m, !!e]); }, rendre() {}, setSelection(s) { VL.etat.selection = s; },
    objetDe(id) { const t = (function v(objs) { for (const o of objs) { if (o.id === id) return o; if (o.type === "groupe") { const r = v(o.enfants || []); if (r) return r; } } return null; })(VL.etat.doc.calques[0].objets); return t ? { objet: t } : null; } };
  return VL;
};

/* ── champs et résumé ── */
{
  ok("champs artistique", champs_pinceau("artistique").map((c) => c.id).join(",") === "echelle,retourner,proportionnel");
  ok("champs motif", champs_pinceau("motif", { ajustement: "couper" }).map((c) => c.id).join(",") === "echelle,espacement,ajustement" && champs_pinceau("motif", { ajustement: "couper" })[2].valeur === "couper");
  ok("champs dispersion, pré-remplis", (() => { const c = champs_pinceau("dispersion", { taille: 150, rotation: "fixe" }); return c.map((x) => x.id).join(",") === "espacement,taille,taille_alea,rotation,rotation_alea,ecart,ecart_alea,graine"
     && c[1].valeur === 150 && c[3].valeur === "fixe" && c[0].valeur === 100; })());
  const d = doc(); const pid = op_pinceau_creer(d, ["haut", "bas"], { nom: "Plume", genre: "artistique" });
  const [gid] = op_pinceau_appliquer(d, ["trace"], pid, {});
  ok("résumé : nom et genre", resume_pinceau(d, obj(d, gid)) === T("vectorlab.pinceaux.a_resume", { nom: "Plume", genre: T("vectorlab.pinceaux.g_artistique") }));
  delete d.pinceaux[pid];
  ok("résumé : définition disparue", resume_pinceau(d, obj(d, gid)) === T("vectorlab.pinceaux.a_disparu", { id: pid }));
}

/* ── les actions ── */
{
  const VL = vl(doc(), ["haut", "bas"]);
  const A = pinceaux_actions(VL);
  let spec = null;
  A.demander = async (s) => { spec = s; return { nom: "Plume", genre: "artistique" }; };
  ok("nouveau : possible avec une sélection", A.action("pinceau_nouveau").peut());
  await A.action("pinceau_nouveau").faire();
  ok("nouveau : nom et genre demandés, pinceau créé, dit", spec.champs.map((c) => c.id).join(",") === "nom,genre" && VL.etat.doc.pinceaux.pc1.nom === "Plume"
     && VL.toasts.at(-1)[0] === T("vectorlab.pinceaux.cree", { nom: "Plume" }));
  // appliquer : choix du pinceau, puis réglages avec aperçu
  VL.etat.selection = ["trace"];
  const vus = [];
  A.demander = async (s) => {
    vus.push(s);
    if (s.champs[0].id === "pinceau") return { pinceau: "pc1" };
    s.surChange({ echelle: 2, retourner: false, proportionnel: false });
    vus.push(JSON.parse(JSON.stringify(VL.etat.doc)));
    return { echelle: 3, retourner: false, proportionnel: false };
  };
  await A.action("pinceau_appliquer").faire();
  const g = VL.etat.doc.calques[0].objets.find((o) => o.pinceau);
  ok("appliquer : choix parmi les pinceaux du document", vus[0].champs[0].options.length === 1 && vus[0].champs[0].options[0][0] === "pc1");
  ok("appliquer : aperçu en direct (sur une copie), puis appliqué avec les réglages", vus[2].calques[0].objets.some((o) => o.pinceau && o.pinceau.params.echelle === 2)
     && g && g.pinceau.params.echelle === 3 && VL.etat.selection[0] === g.id, JSON.stringify(g && g.pinceau));
  // options
  VL.etat.selection = [g.id];
  ok("options : possible sur un tracé peint", A.action("pinceau_options").peut());
  A.demander = async (s) => { spec = s; s.surChange({ echelle: 5, retourner: true, proportionnel: false }); vus.push(VL.etat.doc.calques[0].objets.find((o) => o.pinceau).pinceau.params.echelle); return null; };
  await A.action("pinceau_options").faire();
  ok("options : pré-rempli, aperçu, Annuler rend l'avant", spec.champs[0].valeur === 3 && vus.at(-1) === 5 && VL.etat.doc.calques[0].objets.find((o) => o.pinceau).pinceau.params.echelle === 3);
  A.demander = async () => ({ echelle: 1, retourner: true, proportionnel: false });
  await A.action("pinceau_options").faire();
  ok("options : appliqué", VL.etat.doc.calques[0].objets.find((o) => o.pinceau).pinceau.params.retourner === true);
  // la section Apparence, branchée par mod-repeterui
  VL.pinceauxUI = A;
  const R = repeter_actions(VL);
  const html = R.sectionApparence(VL.etat.doc.calques[0].objets.find((o) => o.pinceau));
  ok("Apparence : la section du pinceau (résumé, Options…, Retirer, Décomposer)", /a2VivantOptions/.test(html) && /a2PinRetirer/.test(html) && /a2Detacher/.test(html) && html.includes("Plume"), html);
  ok("Apparence : Options… et Décomposer passent au pinceau", R.action("options").peut() && R.action("decomposer").peut());
  ok("Apparence : Options… ouvre bien les réglages du pinceau", await (async () => { let vu = false; const avant = A.demander; A.demander = async () => { vu = true; return null; }; await R.action("options").faire(); A.demander = avant; return vu; })());
  const garde = VL.etat.selection;
  VL.etat.selection = [garde[0], "trace2"];
  ok("deux objets sélectionnés : pas d'options de pinceau", !A.action("pinceau_options").peut());
  VL.etat.selection = ["trace2"];
  ok("un tracé non peint : ni options ni retirer", !A.action("pinceau_options").peut() && !A.action("pinceau_retirer").peut());
  VL.etat.selection = garde;
  // le menu (préfixe « couleurs: ») arrive aux pinceaux
  ok("menu : « couleurs:pinceau_options » arrive aux pinceaux", (() => { const C = couleurs_actions(VL); return C.action("pinceau_options").peut(); })());
  // retirer
  await A.action("pinceau_retirer").faire();
  ok("retirer : le tracé revient, sélectionné", obj(VL.etat.doc, "trace") && VL.etat.selection[0] === "trace" && !VL.etat.doc.calques[0].objets.some((o) => o.pinceau));
  // supprimer un pinceau : choix, puis ses tracés reviennent simples
  VL.etat.selection = ["trace2"];
  A.demander = async (s) => (s.champs[0].id === "pinceau" ? { pinceau: "pc1" } : { echelle: 1, retourner: false, proportionnel: false });
  await A.action("pinceau_appliquer").faire();
  A.demander = async (s) => { spec = s; return { pinceau: "pc1" }; };
  ok("supprimer : possible s'il y a des pinceaux", A.action("pinceau_supprimer").peut());
  await A.action("pinceau_supprimer").faire();
  ok("supprimer : le pinceau, et ses tracés redeviennent simples", spec.titre === T("vectorlab.pinceaux.d_supprimer") && !VL.etat.doc.pinceaux.pc1 && obj(VL.etat.doc, "trace2"));
  // plus de pinceau : appliquer le dit, sans dialogue
  let ouvert = false;
  A.demander = async () => { ouvert = true; return null; };
  VL.etat.selection = ["trace"];
  await A.action("pinceau_appliquer").faire();
  ok("aucun pinceau : dit, sans dialogue", !ouvert && VL.toasts.at(-1)[0] === T("vectorlab.pinceaux.aucun") && VL.toasts.at(-1)[1]);
  ok("supprimer impossible sans pinceau", !A.action("pinceau_supprimer").peut());
  VL.etat.selection = [];
  ok("sans sélection : nouveau, appliquer, options, retirer impossibles", ["pinceau_nouveau", "pinceau_appliquer", "pinceau_options", "pinceau_retirer"].every((k) => !A.action(k).peut()));
  ok("action inconnue : aucune (aiguillage)", A.action("zzz") === null);
}

if (echecs.length) {
  console.error(`pinceauxui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("pinceauxui : ok");
