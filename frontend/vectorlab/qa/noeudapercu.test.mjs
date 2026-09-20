// noeudapercu.test.mjs — R12 : l'aperçu des nœuds suit le curseur — un
// planificateur à UN cadre en vol (rAF simulé), vidé au relâchement, et le
// déplacement d'ancres sur des segs SANS clone de document.
import { planificateur } from "../js/mod-noeudapercu.js";
import { noeuds_deplacer_segs, op_noeuds_deplacer } from "../js/mod-noeuds.js";
import { chemin_parser, chemin_serialiser, chemin_ancres } from "../js/mod-doc.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : "")); };
{
  const cadres = [];
  let annules = 0;
  const raf = (fn) => { cadres.push(fn); return cadres.length; };
  const caf = () => { annules++; };
  const P = planificateur({ raf, caf });
  const vus = [];
  P.demander(() => vus.push(1));
  P.demander(() => vus.push(2));
  P.demander(() => vus.push(3));
  ok("trois demandes → UN cadre en vol", cadres.length === 1 && P.enAttente() === true && vus.length === 0);
  cadres[0]();
  ok("le cadre exécute la DERNIÈRE demande seulement", vus.join() === "3" && P.enAttente() === false);
  P.demander(() => vus.push(4));
  const r = P.vider();
  ok("vider() exécute tout de suite la demande en attente et annule le cadre", vus.join() === "3,4" && r === true && annules === 1 && P.enAttente() === false);
  ok("vider() sans demande → false, rien d'exécuté", P.vider() === false && vus.length === 2);
  cadres[1] && cadres[1]();
  ok("un cadre annulé qui tirerait quand même n'exécute rien", vus.length === 2);
}
{
  const segs = chemin_parser("M 0 0 L 100 0 C 120 0 140 20 140 40 L 0 40 Z");
  const s2 = noeuds_deplacer_segs(segs, [1], 5, 7);
  ok("noeuds_deplacer_segs ne mute pas l'entrée", chemin_serialiser(segs) === "M 0 0 L 100 0 C 120 0 140 20 140 40 L 0 40 Z");
  const a = chemin_ancres(s2);
  ok("l'ancre 1 et sa sortante suivent", a[1].x === 105 && a[1].y === 7 && a[1].sortante.x === 125 && a[1].sortante.y === 7, JSON.stringify(a[1]));
  const doc = { calques: [{ id: "c", objets: [{ id: "p", type: "path", d: chemin_serialiser(segs) }] }] };
  op_noeuds_deplacer(doc, "p", [1], 5, 7);
  ok("op_noeuds_deplacer = la même géométrie (même fonction dessous)", doc.calques[0].objets[0].d === chemin_serialiser(s2));
  let refus = 0; try { noeuds_deplacer_segs(segs, [9], 1, 1); } catch { refus++; }
  ok("indice hors chemin refusé", refus === 1);
}
if (echecs.length) { console.error("ECHECS noeudapercu :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA noeudapercu : PASS (10 controles)");
