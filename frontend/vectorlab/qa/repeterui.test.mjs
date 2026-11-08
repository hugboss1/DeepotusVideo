// repeterui.test.mjs — lot D2 « Répéter et fusionner » T6 (t455) : le câblage des répétitions et fusions vivantes.
// Un VL factice qui EXÉCUTE vraiment (clone, op, dérivés) et note chaque appel ; `demander` remplacé. Chaque action
// a le bon grisage et appelle la bonne opération ; l'aperçu en direct montre l'essai sans toucher à l'historique et
// rend toujours le document d'avant ; l'onglet Apparence résume la recette ; le menu Vecteur nomme ces actions.
// T7 (t456) : poignées sur la toile — rosace (rayon, nombre), miroir (écart, angle de l'axe) ; un glisser = un aperçu en
// direct puis UNE exécution d'op_repetition_regler.
import { repeter_actions, initRepeterUI, resume_vivant, champs_repetition, poignees_vivant, params_par_poignee } from "../js/mod-repeterui.js";
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
/* ── T7 (t456) poignées sur la toile : rosace (rayon, nombre) et miroir (écart, angle de l'axe) ── */
{
  const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
  // rosace : source 20 × 20 de centre (100, 50), rayon 50 → centre de la rosace (100, 100)
  const r = repetition();
  const g = r.etat.doc.calques[0].objets[0];
  const P = poignees_vivant(g);
  const rayon = P.find((p) => p.role === "rayon"), nombre = P.find((p) => p.role === "nombre");
  ok("rosace : deux poignées, rayon et nombre", P.length === 2 && rayon && nombre, JSON.stringify(P));
  ok("rosace : la poignée de rayon est en bas du cercle (100, 150)", pres(rayon.x, 100) && pres(rayon.y, 150), JSON.stringify(rayon));
  ok("rosace : la poignée de nombre est sur la première copie (150, 100 pour 4 instances)", pres(nombre.x, 150) && pres(nombre.y, 100), JSON.stringify(nombre));
  ok("rayon : tirer la poignée à y = 210 → rayon 80", JSON.stringify(params_par_poignee(g, "rayon", 100, 210)) === '{"rayon":80}');
  ok("rayon : au-dessus de la source → 0,5 au moins", params_par_poignee(g, "rayon", 100, 0).rayon === 0.5);
  ok("nombre : la poignée à 60° du haut → 6 instances", params_par_poignee(g, "nombre", 100 + 50 * Math.sin(Math.PI / 3), 100 - 50 * Math.cos(Math.PI / 3)).nombre === 6);
  ok("nombre : à 180° → 2", params_par_poignee(g, "nombre", 100, 150).nombre === 2);
  ok("nombre : presque sur la source (1°) → plafonné à 100", params_par_poignee(g, "nombre", 100 + 50 * Math.sin(Math.PI / 180), 100 - 50 * Math.cos(Math.PI / 180)).nombre === 100);
  ok("nombre : à 270° (à gauche) → 2 au moins", params_par_poignee(g, "nombre", 50, 100).nombre === 2);
  ok("rôle inconnu : rien", params_par_poignee(g, "x", 0, 0) === null);
  const r3 = faux([rect("a", 90, 40)]);
  r3.VL.executer(op_repeter, ["a"], "radiale", { nombre: 3, rayon: 50 });
  const n3 = poignees_vivant(r3.etat.doc.calques[0].objets[0]).find((p) => p.role === "nombre");
  ok("rosace de 3 : la poignée de nombre à 120° (143,3 ; 125)", pres(n3.x, 100 + 50 * Math.sin(2 * Math.PI / 3)) && pres(n3.y, 125), JSON.stringify(n3));
  // miroir vertical collé : axe x = 110, normale vers la droite
  const m = faux([{ id: "a", type: "path", d: "M90 40 L110 40 L90 60 Z", style: { fond: "#c33" } }]);
  m.VL.executer(op_repeter, ["a"], "miroir", {});
  const mg = m.etat.doc.calques[0].objets[0];
  const Q = poignees_vivant(mg);
  const ecart = Q.find((p) => p.role === "ecart"), angle = Q.find((p) => p.role === "angle");
  ok("miroir : deux poignées sur l'axe, écart et angle", Q.length === 2 && ecart && angle && pres(ecart.x, 110) && pres(angle.x, 110) && angle.y > ecart.y, JSON.stringify(Q));
  ok("écart : tirer l'axe à x = 125 → écart 15", JSON.stringify(params_par_poignee(mg, "ecart", 125, 0)) === '{"ecart":15}');
  ok("écart : à x = 100 (dans la source) → -10", params_par_poignee(mg, "ecart", 100, 77).ecart === -10);
  ok("une poignée de rosace sur un miroir : rien", params_par_poignee(mg, "rayon", 0, 0) === null && params_par_poignee(g, "ecart", 0, 0) === null);
  const m10 = faux([{ id: "a", type: "path", d: "M90 40 L110 40 L90 60 Z", style: { fond: "#c33" } }]);
  m10.VL.executer(op_repeter, ["a"], "miroir", { ecart: 10 });
  ok("miroir à écart 10 : la poignée d'écart est sur l'axe x = 120", pres(poignees_vivant(m10.etat.doc.calques[0].objets[0])[0].x, 120), JSON.stringify(poignees_vivant(m10.etat.doc.calques[0].objets[0])));
  ok("angle : la poignée à droite de l'axe → 0°", params_par_poignee(mg, "angle", ecart.x + 30, ecart.y).angle === 0);
  ok("angle : en bas à droite → 45°", params_par_poignee(mg, "angle", ecart.x + 30, ecart.y + 30).angle === 45);
  ok("angle : en haut → 270°", params_par_poignee(mg, "angle", ecart.x, ecart.y - 30).angle === 270);
  ok("une grille ou une fusion : pas de poignée", poignees_vivant({ repetition: { mode: "grille", params: {} }, enfants: [] }).length === 0 && poignees_vivant(fusion().etat.doc.calques[0].objets[0]).length === 0 && poignees_vivant(null).length === 0);
}
{
  // le geste : début, déplacements en aperçu (sans historique), fin = UNE exécution d'op_repetition_regler
  const r = repetition();
  const A = repeter_actions(r.VL);
  const avant = r.etat.doc;
  ok("poignée : pas de geste sans répétition sélectionnée", (() => { const f = faux([rect("a", 0, 0)], ["a"]); return repeter_actions(f.VL).poignee.debut("rayon") === false; })());
  ok("poignée : une poignée de miroir sur une rosace ne démarre pas", A.poignee.debut("ecart") === false);
  ok("poignée : début du geste", A.poignee.debut("rayon") === true);
  A.poignee.bouger(100, 210);
  const pendant = r.etat.doc.calques[0].objets[0];
  ok("poignée : aperçu en direct (rayon 80), sans exécution", pendant.repetition.params.rayon === 80 && r.appels.length === 0 && r.etat.doc !== avant);
  A.poignee.bouger(100, 250);
  const exec = r.VL.executer;
  let docVu = null;
  r.VL.executer = (fn, ...args) => { docVu = r.etat.doc; return exec(fn, ...args); };
  A.poignee.fin();
  r.VL.executer = exec;
  ok("poignée : l'exécution part du document d'AVANT (Ctrl+Z ramène au départ, pas à l'aperçu)", docVu === avant);
  ok("poignée : à la fin, UNE exécution avec le dernier réglage", r.appels.length === 1 && r.appels[0].fn === op_repetition_regler && JSON.stringify(r.appels[0].args) === JSON.stringify([r.gid, { rayon: 100 }]), JSON.stringify(r.appels.map((x) => x.args)));
  ok("poignée : le document final porte le rayon 100", r.etat.doc.calques[0].objets[0].repetition.params.rayon === 100);
  const docFin = r.etat.doc;
  A.poignee.fin();
  ok("poignée : une fin de trop ne fait rien", r.appels.length === 1 && r.etat.doc === docFin);
  // un clic sans déplacement : rien n'est exécuté, le document d'avant est rendu
  const doc2 = r.etat.doc;
  A.poignee.debut("nombre");
  A.poignee.fin();
  ok("poignée : un clic sans glisser n'exécute rien", r.appels.length === 1 && r.etat.doc === doc2);
  // un geste interrompu par une valeur impossible garde le document d'avant à l'écran
  A.poignee.debut("rayon");
  A.poignee.bouger(100, 210);
  A.poignee.bouger(NaN, NaN);
  ok("poignée : valeur impossible après un aperçu → document d'avant montré", r.etat.doc === doc2);
  A.poignee.fin();
  ok("poignée : et rien d'exécuté (le dernier réglage valable est oublié)", r.appels.length === 1);
  ok("poignée : bouger sans début ne fait rien", (() => { A.poignee.bouger(100, 300); return r.etat.doc === doc2; })());
}

{
  // le dessin des poignées dans l'overlay : repère + disques tirables aux libellés traduits, seulement à l'outil Sélection
  const r = repetition();
  r.etat.outil = "select";
  const A = repeter_actions(r.VL);
  const els = [];
  const o = { appendChild: (e) => els.push(e) };
  const ov = (nom, attrs) => ({ nom, attrs });
  A.dessinerPoignees(o, ov, (x, y) => [x * 2, y * 2], 2);
  const disques = els.filter((e) => e.attrs.class === "poignee-vivant");
  ok("dessin : un cercle-repère (rayon × zoom) et deux poignées", els[0].nom === "circle" && els[0].attrs.r === 100 && disques.length === 2, JSON.stringify(els.map((e) => e.attrs)));
  ok("dessin : rôles et libellés traduits", disques.map((e) => e.attrs["data-vivant"]).join() === "rayon,nombre"
     && disques[0].attrs["aria-label"] === T("vectorlab.repeter.poignee_rayon") && !/^vectorlab\./.test(disques[1].attrs["aria-label"]));
  ok("dessin : positions converties à l'écran", disques[0].attrs.cx === 200 && disques[0].attrs.cy === 300, JSON.stringify(disques[0].attrs));
  r.etat.outil = "plume";
  const avant = els.length;
  A.dessinerPoignees(o, ov, (x, y) => [x, y], 1);
  ok("dessin : rien hors de l'outil Sélection", els.length === avant);
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
