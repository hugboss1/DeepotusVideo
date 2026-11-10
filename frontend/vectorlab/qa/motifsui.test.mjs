// motifsui.test.mjs — lot D5 « Couleur et motif » (t479) : l'éditeur de motif. Vecteur › Créer un motif… (depuis la
// sélection, aperçu en direct) et Vecteur › Motifs du document… (liste, appliquer, régler, remplacer, supprimer),
// js/mod-motifsui.js avec un VL factice ; les aides pures de js/mod-motifs.js.
import { createRequire } from "node:module";
import { motif_apercu, motifs_objets_liste } from "../js/mod-motifs.js";
import { motifs_actions, champs_motif, opts_formulaire, motif_vignette } from "../js/mod-motifsui.js";
import { couleurs_actions } from "../js/mod-recolorerui.js";
import { fournirMartinez } from "../js/mod-bool.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const pres = (a, b, e = 0.01) => Math.abs(a - b) <= e;
const doc = () => ({ v: 1, taille: { w: 300, h: 300 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
  { id: "a", type: "rect", x: 40, y: 50, w: 10, h: 10, style: { fond: "#ff0000" } },
  { id: "b", type: "ellipse", cx: 60, cy: 55, rx: 5, ry: 5, style: { fond: "#0000ff" } },
  { id: "cible", type: "rect", x: 100, y: 100, w: 80, h: 80, style: { fond: "#ffffff" } }] }] });

/* ── aides pures ── */
{
  const d = doc();
  const id = motif_apercu(d, ["a", "b"], { pavage: "grille", espacement: { h: 5, v: 0 } });
  const r = d.calques[0].objets.at(-1);
  ok("aperçu : le motif, et un rectangle qu'il remplit posé sur la sélection (3 × 3 cellules)", d.motifs[id] && r.style.fond === "motif:" + id
     && r.x === 40 && r.y === 50 && pres(r.w, 3 * 30) && pres(r.h, 3 * 10), JSON.stringify(r));
  d.motifs.m9 = { type: "points", pas: 8 };
  d.motifs.m10 = { ...d.motifs[id] };
  d.calques[0].objets[2].style.fond = "motif:m10";
  const l = motifs_objets_liste(d);
  ok("liste : les motifs d'objets seuls, dans l'ordre naturel des ids, avec leurs usages", l.map((x) => x.id).join(",") === `${id},m10` && l[1].usages === 1 && l[0].usages === 1 && l[0].pavage === "grille", JSON.stringify(l));
}

{
  // le premier calque est verrouillé : l'aperçu va sur le premier calque libre
  const d = doc();
  d.calques.unshift({ id: "c0", nom: "v", visible: true, verrou: true, objets: [] });
  motif_apercu(d, ["a"], {});
  ok("aperçu : sur le premier calque déverrouillé", d.calques[0].objets.length === 0 && d.calques[1].objets.at(-1).id === "_apercu_motif");
  // usages comptés dans les groupes ; ordre naturel m1, m2, m10
  const e = doc();
  motif_apercu(e, ["a"], {});
  e.motifs.m10 = { ...e.motifs.m1 }; e.motifs.m2 = { ...e.motifs.m1 };
  e.calques[0].objets.push({ id: "g", type: "groupe", style: {}, enfants: [{ id: "x", type: "rect", x: 0, y: 0, w: 1, h: 1, style: { fond: "motif:m2" } }] });
  const l = motifs_objets_liste(e);
  ok("liste : ordre naturel des ids, usages dans les groupes", l.map((x) => x.id).join(",") === "m1,m2,m10" && l[1].usages === 1, JSON.stringify(l));
}

/* ── formulaire ── */
{
  const c = champs_motif({ pavage: "hexagone", espacement: { h: 2, v: -1 }, fond: "#abcdef" });
  ok("champs : pavage, espacements, fond (case et couleur), pré-remplis", c.map((x) => x.id).join(",") === "pavage,eh,ev,fond_actif,fond"
     && c[0].valeur === "hexagone" && c[0].options.length === 4 && c[1].valeur === 2 && c[2].valeur === -1 && c[3].valeur === true && c[4].type === "couleur" && c[4].valeur === "#abcdef");
  ok("champs par défaut : grille, 0, sans fond (blanc proposé)", (() => { const d = champs_motif(); return d[0].valeur === "grille" && d[1].valeur === 0 && d[3].valeur === false && d[4].valeur === "#ffffff"; })());
  ok("fond « none » ou couleur globale : case décochée, blanc proposé", champs_motif({ fond: "none" })[3].valeur === false && champs_motif({ fond: "glob:Marque" })[4].valeur === "#ffffff");
  ok("valeurs → réglages", JSON.stringify(opts_formulaire({ pavage: "brique_lignes", eh: 3, ev: 4, fond_actif: true, fond: "#000000" })) === JSON.stringify({ pavage: "brique_lignes", espacement: { h: 3, v: 4 }, fond: "#000000" })
     && opts_formulaire({ pavage: "grille", eh: 0, ev: 0, fond_actif: false, fond: "#000000" }).fond === "none");
  ok("vignette : un petit SVG rempli du motif", (() => { const d = doc(); const i = motif_apercu(d, ["a"], {}); const v = motif_vignette(d, i); return /^<svg/.test(v) && /<pattern id="m1"/.test(v); })());
}

/* ── l'interface (VL factice) ── */
const vl = (d, sel) => {
  const VL = { etat: { doc: d, selection: sel }, toasts: [],
    executer(fn, ...a) { try { const x = JSON.parse(JSON.stringify(VL.etat.doc)); const r = fn(x, ...a); VL.etat.doc = x; return r; } catch (e) { VL.toast(e.message, true); return undefined; } },
    toast(m, e) { VL.toasts.push([m, !!e]); }, rendre() {}, setSelection(s) { VL.etat.selection = s; } };
  return VL;
};
{
  const VL = vl(doc(), ["a", "b"]);
  const A = motifs_actions(VL);
  let vu = null, spec = null;
  A.demander = async (s) => { spec = s; s.surChange({ pavage: "brique_lignes", eh: 0, ev: 0, fond_actif: false, fond: "#ffffff" }); vu = JSON.parse(JSON.stringify(VL.etat.doc)); return null; };
  ok("créer : possible avec une sélection", A.action("motif_creer").peut());
  await A.action("motif_creer").faire();
  ok("créer : aperçu en direct (motif + rectangle), Annuler ne laisse rien", vu.motifs && vu.motifs.m1 && vu.calques[0].objets.at(-1).style.fond === "motif:m1" && !VL.etat.doc.motifs && VL.etat.doc.calques[0].objets.length === 3);
  ok("créer : le dialogue a ses champs", spec.titre === T("vectorlab.motifs.d_creer") && spec.champs.length === 5);
  A.demander = async () => ({ pavage: "hexagone", eh: 1, ev: 2, fond_actif: true, fond: "#eeeeee" });
  await A.action("motif_creer").faire();
  const m = VL.etat.doc.motifs && VL.etat.doc.motifs.m1;
  ok("créer : le motif, sans rectangle d'aperçu ; dit dans un toast", m && m.pavage === "hexagone" && m.espacement.v === 2 && m.fond === "#eeeeee"
     && VL.etat.doc.calques[0].objets.length === 3 && VL.toasts.at(-1)[0] === T("vectorlab.motifs.cree", { id: "m1" }) && !VL.toasts.at(-1)[1], JSON.stringify(VL.toasts));
  // la liste : appliquer à la sélection
  VL.etat.selection = ["cible"];
  let liste = null;
  A.demanderListe = async (s) => { liste = s; return { action: "appliquer", id: "m1" }; };
  ok("motifs du document : possible avec un document", A.action("motifs").peut());
  await A.action("motifs").faire();
  ok("liste : ses motifs, avec vignette", liste.motifs.length === 1 && liste.motifs[0].id === "m1" && /^<svg/.test(liste.motifs[0].vignette));
  ok("appliquer : le fond de la sélection", VL.etat.doc.calques[0].objets[2].style.fond === "motif:m1");
  // régler, avec aperçu
  A.demanderListe = async () => ({ action: "regler", id: "m1" });
  A.demander = async (s) => { spec = s; s.surChange({ pavage: "grille", eh: 9, ev: 0, fond_actif: false, fond: "#ffffff" }); vu = VL.etat.doc.motifs.m1.espacement.h; return { pavage: "brique_colonnes", eh: 4, ev: 0, fond_actif: false, fond: "#ffffff" }; };
  await A.action("motifs").faire();
  ok("régler : pré-rempli, aperçu, puis appliqué", spec.champs[0].valeur === "hexagone" && vu === 9 && VL.etat.doc.motifs.m1.pavage === "brique_colonnes" && VL.etat.doc.motifs.m1.fond === "none", JSON.stringify(VL.etat.doc.motifs.m1.pavage));
  // remplacer par la sélection
  VL.etat.selection = ["a"];
  A.demanderListe = async () => ({ action: "remplacer", id: "m1" });
  await A.action("motifs").faire();
  ok("remplacer : le contenu devient la sélection", VL.etat.doc.motifs.m1.objets.length === 1 && VL.etat.doc.motifs.m1.objets[0].type === "rect");
  // appliquer sans sélection : dit
  VL.etat.selection = [];
  A.demanderListe = async () => ({ action: "appliquer", id: "m1" });
  await A.action("motifs").faire();
  ok("appliquer sans sélection : refus dit", VL.toasts.at(-1)[0] === T("vectorlab.motifs.selection_requise") && VL.toasts.at(-1)[1]);
  // supprimer : les fonds qui l'emploient passent à none
  A.demanderListe = async () => ({ action: "supprimer", id: "m1" });
  await A.action("motifs").faire();
  ok("supprimer : le motif, et les fonds qui l'emploient", !VL.etat.doc.motifs.m1 && VL.etat.doc.calques[0].objets[2].style.fond === "none");
  // plus aucun motif : dit, sans dialogue
  let ouvert = false;
  A.demanderListe = async () => { ouvert = true; return null; };
  await A.action("motifs").faire();
  ok("aucun motif : dit, sans dialogue", !ouvert && VL.toasts.at(-1)[0] === T("vectorlab.motifs.aucun"));
  ok("créer sans sélection : impossible", !A.action("motif_creer").peut());
  ok("Édition / Vecteur : « couleurs:motif_creer » arrive à l'éditeur de motif", (() => { const V = vl(doc(), ["a"]); V.motifsUI = motifs_actions(V); return couleurs_actions(V).action("motif_creer").peut() === true; })());
  ok("action inconnue : aucune (mod-recolorerui aiguille alors ailleurs)", A.action("zzz") === null);
}

if (echecs.length) {
  console.error(`motifsui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("motifsui : ok");
