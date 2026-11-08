// tracesui.test.mjs — lot D1 « Tracés » T9 (t430) : le câblage des commandes de tracé. Un VL factice (etat,
// executer qui ENREGISTRE l'appel, demander remplacé) : chaque action a le bon grisage (peut) et appelle la bonne
// opération avec les bons arguments ; annuler un dialogue n'appelle rien ; Ctrl+4 répète le dernier Pathfinder,
// booléens d'origine compris. Les menus (bloc Tracé et Pathfinder du menu Vecteur) nomment ces actions.
import { traces_actions, initTracesUI, PATHFINDER } from "../js/mod-tracesui.js";
import { op_contour_vectoriser, op_simplifier, op_points_ajouter, op_noeuds_moyenne, op_nettoyer, op_diviser_dessous,
         op_lignes_colonnes, op_pathfinder } from "../js/mod-traces.js";
import { MENUS_BARRE } from "../js/mod-menus.js";
import { T } from "../js/mod-i18n.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
function faux({ selection = [], outil = "deplacer", ancreSel = null, ancresSel = [], path = null, objets = [] } = {}) {
  const appels = [], toasts = [], selections = [];
  const VL = {
    etat: { doc: { calques: [{ id: "c", objets }] }, selection, outil, ancreSel, ancresSel },
    executer: (fn, ...args) => { appels.push({ fn, args }); return fn === op_nettoyer ? { isoles: 2, invisibles: 1, textesVides: 0 } : ["n1", "n2"]; },
    setSelection: (ids) => selections.push(ids),
    toast: (m, err) => toasts.push([m, !!err]),
    objetDe: (id) => { const o = objets.find((x) => x.id === id); return o ? { objet: o } : null; },
    pathSelectionne: () => path,
    actions: { noeuds: { supprimerLisse: () => appels.push({ fn: "supprimerLisse", args: [] }) },
               selection: { booleen: (op) => appels.push({ fn: "booleen", args: [op] }) } },
  };
  return { VL, appels, toasts, selections };
}
const rect = (id) => ({ id, type: "rect", x: 0, y: 0, w: 10, h: 10, style: { fond: "#eee" } });

/* ── grisage ── */
{
  const vide = traces_actions(faux().VL);
  ok("rien de sélectionné : contour, simplifier, ajouter, diviser, lignes, Pathfinder et répéter grisés",
     ["contour", "simplifier", "ajouter", "diviser", "lignes", "repeter", ...PATHFINDER.map(([k]) => "pf-" + k)].every((a) => !vide.action(a).peut()));
  ok("nettoyer : actif dès qu'un document est ouvert", vide.action("nettoyer").peut());
  ok("action inconnue : grisée", !vide.action("inconnue").peut());
  const un = traces_actions(faux({ selection: ["a"], objets: [rect("a")] }).VL);
  ok("un objet : contour, simplifier, ajouter, diviser, lignes actifs ; Pathfinder grisé",
     ["contour", "simplifier", "ajouter", "diviser", "lignes"].every((a) => un.action(a).peut()) && !un.action("pf-exclusion").peut());
  const deux = traces_actions(faux({ selection: ["a", "b"], objets: [rect("a"), rect("b")] }).VL);
  ok("deux objets mais aucun Pathfinder encore : répéter grisé", !deux.action("repeter").peut());
  ok("deux objets : Pathfinder actifs ; diviser et lignes (un seul objet) grisés", PATHFINDER.every(([k]) => deux.action("pf-" + k).peut())
     && !deux.action("diviser").peut() && !deux.action("lignes").peut());
  ok("supprimer des points : grisé hors de l'outil Nœud", !traces_actions(faux({ path: { id: "p" }, ancreSel: 1 }).VL).action("supprimer").peut());
  ok("supprimer des points : actif à l'outil Nœud avec un nœud choisi", traces_actions(faux({ outil: "noeuds", path: { id: "p" }, ancreSel: 1 }).VL).action("supprimer").peut());
  ok("moyenne : il faut un chemin et deux nœuds", !traces_actions(faux({ path: { id: "p" }, ancresSel: [1] }).VL).action("moyenne").peut()
     && traces_actions(faux({ path: { id: "p" }, ancresSel: [1, 2] }).VL).action("moyenne").peut());
}
/* ── appels ── */
const attendre = () => new Promise((r) => setTimeout(r, 0));
{
  const f = faux({ selection: ["a", "b"], objets: [rect("a"), rect("b")] });
  const A = traces_actions(f.VL);
  A.action("contour").faire();
  ok("contour : op_contour_vectoriser(sélection), puis le résultat est sélectionné", f.appels[0].fn === op_contour_vectoriser
     && JSON.stringify(f.appels[0].args) === '[["a","b"]]' && JSON.stringify(f.selections[0]) === '["n1","n2"]');
  A.action("ajouter").faire();
  ok("ajouter : op_points_ajouter(sélection)", f.appels[1].fn === op_points_ajouter);
  let spec = null;
  A.demander = async (s) => { spec = s; return { precision: 30, droites: true }; };
  await A.action("simplifier").faire();
  ok("simplifier : dialogue (précision, lignes droites), puis op_simplifier avec ces réglages", f.appels[2].fn === op_simplifier
     && JSON.stringify(f.appels[2].args) === '[["a","b"],{"precision":30,"droites":true}]' && spec.champs.map((c) => c.id).join() === "precision,droites", JSON.stringify(f.appels[2].args));
  ok("simplifier : l'aperçu compte les points avant → après", /8/.test(spec.apercu({ precision: 50, droites: false })), spec.apercu({ precision: 50 }));
  A.demander = async () => null;
  await A.action("simplifier").faire();
  ok("simplifier annulé : aucune opération", f.appels.length === 3);
  A.action("pf-decoupage").faire();
  ok("Pathfinder : op_pathfinder(sélection, mode)", f.appels[3].fn === op_pathfinder && JSON.stringify(f.appels[3].args) === '[["a","b"],"decoupage"]');
  ok("répéter : actif après un Pathfinder", A.action("repeter").peut());
  A.action("repeter").faire();
  ok("répéter : refait le même Pathfinder", f.appels[4].fn === op_pathfinder && f.appels[4].args[1] === "decoupage");
}
{
  const f = faux({ selection: ["a"], objets: [rect("a")] });
  const A = traces_actions(f.VL);
  A.action("diviser").faire();
  ok("diviser : op_diviser_dessous(l'objet)", f.appels[0].fn === op_diviser_dessous && f.appels[0].args[0] === "a");
  A.demander = async () => ({ lignes: 3, colonnes: 2, gouttiereLignes: 4, gouttiereColonnes: 5, reperes: true });
  await A.action("lignes").faire();
  ok("lignes : op_lignes_colonnes(l'objet, réglages)", f.appels[1].fn === op_lignes_colonnes && f.appels[1].args[0] === "a"
     && JSON.stringify(f.appels[1].args[1]) === '{"lignes":3,"colonnes":2,"gouttiereLignes":4,"gouttiereColonnes":5,"reperes":true}');
  A.demander = async () => ({ isoles: true, invisibles: false, textesVides: true });
  await A.action("nettoyer").faire();
  ok("nettoyer : op_nettoyer(cases), puis le bilan traduit", f.appels[2].fn === op_nettoyer && JSON.stringify(f.appels[2].args[0]) === '{"isoles":true,"invisibles":false,"textesVides":true}'
     && f.toasts[0][0] === T("vectorlab.traces.nettoyer_bilan_plusieurs", { n: 3 }) && !f.toasts[0][1], JSON.stringify(f.toasts));
}
{
  const f = faux({ outil: "noeuds", path: { id: "p" }, ancresSel: [0, 2] });
  const A = traces_actions(f.VL);
  A.demander = async (s) => (s.champs[0].options.length === 3 ? { axe: "horizontale" } : null);
  await A.action("moyenne").faire();
  ok("moyenne : op_noeuds_moyenne(chemin, nœuds, axe choisi)", f.appels[0].fn === op_noeuds_moyenne && JSON.stringify(f.appels[0].args) === '["p",[0,2],"horizontale"]');
  A.action("supprimer").faire();
  ok("supprimer des points : la suppression lisse de l'outil Nœud", f.appels[1].fn === "supprimerLisse");
}
{
  // initTracesUI : VL.traces et VL.actions.traces posés ; un booléen d'origine devient « le dernier », Ctrl+4 le refait
  const f = faux({ selection: ["a", "b"], objets: [rect("a"), rect("b")] });
  const A = initTracesUI(f.VL);
  ok("initTracesUI pose VL.traces et VL.actions.traces", f.VL.traces === A && f.VL.actions.traces === A);
  f.VL.actions.selection.booleen("union");
  ok("un booléen d'origine passe toujours", f.appels[0].fn === "booleen" && f.appels[0].args[0] === "union");
  A.action("repeter").faire();
  ok("répéter après une union : refait l'union", f.appels[1].fn === "booleen" && f.appels[1].args[0] === "union");
  initTracesUI(f.VL);
  f.VL.actions.selection.booleen("intersection");
  ok("deux initialisations n'emballent pas deux fois", f.appels.length === 3);
  ok("après une seconde initialisation, le booléen est noté dans le VL.traces COURANT", f.VL.traces !== A && f.VL.traces.dernier() && f.VL.traces.dernier().bool === "intersection", JSON.stringify(f.VL.traces.dernier()));
  const fly = A.flyoutBool((id, libelle, actif, fn, icone) => ({ id, libelle, desactive: !actif, fn }), { n: 1 });
  ok("menu détaché Sélection : 6 Pathfinder, grisés à un objet", fly.length === 6 && fly.every((x) => x.desactive && x.id.startsWith("pf-")));
}
/* ── menus ── */
{
  const vec = MENUS_BARRE.find((m) => m.entrees.some((x) => x.action === "bool:union"));
  const actions = vec ? vec.entrees.filter((x) => x !== "-").map((x) => x.action) : [];
  const voulues = ["contour", "simplifier", "ajouter", "supprimer", "moyenne", "nettoyer", "diviser", "lignes", ...PATHFINDER.map(([k]) => "pf-" + k), "repeter"].map((a) => "traces:" + a);
  ok("menu Vecteur : les 15 commandes de tracé y sont", voulues.every((a) => actions.includes(a)), voulues.filter((a) => !actions.includes(a)).join());
  const rep = vec && vec.entrees.find((x) => x.action === "traces:repeter");
  ok("Répéter le dernier Pathfinder : Ctrl+4", rep && rep.raccourci === "ctrl+4");
  ok("libellés traduits (pas de clé brute)", vec && vec.entrees.filter((x) => x !== "-" && String(x.action).startsWith("traces:")).every((x) => !/^vectorlab\./.test(x.libelle)));
}

if (echecs.length) {
  console.error(`tracesui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("tracesui : ok");
