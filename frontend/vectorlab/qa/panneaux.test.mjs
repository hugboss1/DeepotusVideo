// panneaux.test.mjs — la refonte Vitrail du handoff (06/09/2026) : les
// quatre générateurs PURS (arc, rosette, grille, plomb libre), le hasard
// déterministe, le panneau-groupe porteur de ses réglages, l'insertion et
// la regénération (op_panneau_regen) — y compris APRÈS un déplacement, où
// la bbox est relue des enfants et non de la méta.
import { hash01, teinteDe, GAMMES, MOTIFS, construire_panneau,
         bbox_enfants, op_panneau_inserer, op_panneau_regen }
  from "../js/mod-vitrail.js";
import { op_deplacer } from "../js/mod-doc.js";

const echecs = [];
let total = 0;
const ok = (nom, cond, detail = "") => {
  total += 1;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

const O = (extra = {}) => ({ colonnes: 4, rangees: 6, plomb: 6,
  arrondi: false, gamme: "chartres", teintes: GAMMES.chartres.teintes,
  couleurPlomb: "#1F1512", graine: 41, ...extra });
const B = { x: 100, y: 80, w: 300, h: 500 };
const docNeuf = () => ({ v: "1", taille: { w: 640, h: 960 },
  calques: [{ id: "c1", nom: "fond", objets: [] }] });

// ── le hasard : pur, borné, discriminant ──
ok("hash01 est pur", hash01(5) === hash01(5) && hash01(5) !== hash01(6));
ok("hash01 rend dans [0,1)",
   [0, 1, 41, 9973].every((n) => hash01(n) >= 0 && hash01(n) < 1));
ok("teinteDe pioche DANS la gamme",
   Array.from({ length: 40 }, (_, i) =>
     teinteDe(GAMMES.foret.teintes, i, 7)).every(
     (c) => GAMMES.foret.teintes.includes(c)));

// ── les comptes de pièces, par motif (formules du générateur) ──
{
  const arc = MOTIFS.arc.gen(B, O());          // quartiers = colonnes+1
  ok("arc: 2×5 lancettes + 4×6 verres + cadre = 35",
     arc.length === 35, String(arc.length));
  const ros = MOTIFS.rosette.gen(B, O({ rangees: 2 }));  // n = colonnes×2
  ok("rosette: 2 couronnes ×16 + 8 pétales + moyeu + cadre = 42",
     ros.length === 42, String(ros.length));
  const gri = MOTIFS.grille.gen(B, O());
  ok("grille: fond + 7×5 losanges + cadre = 37",
     gri.length === 37, String(gri.length));
  const plb = MOTIFS.plomb.gen(B, O());        // (colonnes+1)×rangees
  ok("plomb libre: 5×6 pièces + cadre = 31",
     plb.length === 31, String(plb.length));
}

// ── déterminisme par graine, style des pièces, cadre ──
for (const [nom, m] of Object.entries(MOTIFS)) {
  const a = m.gen(B, O()), b = m.gen(B, O()), c = m.gen(B, O({ graine: 42 }));
  ok(`${nom}: même graine → même panneau, à l'octet`,
     JSON.stringify(a) === JSON.stringify(b));
  ok(`${nom}: une autre graine change au moins un verre`,
     JSON.stringify(a) !== JSON.stringify(c));
  const pieces = a.filter((o) => o.style.fond !== "none"
                                 && o.style.contour);
  ok(`${nom}: chaque pièce porte plomb 6 et joint miter`,
     pieces.length > 0 && pieces.every((o) => o.style.epaisseur === 6
       && o.style.joint === "miter" && o.style.contour === "#1F1512"));
  const rondes = m.gen(B, O({ arrondi: true }))
    .filter((o) => o.style.joint);
  ok(`${nom}: joints arrondis → linejoin round partout`,
     rondes.length > 0 && rondes.every((o) => o.style.joint === "round"));
  const cadre = a[a.length - 1];
  ok(`${nom}: le dernier objet est le cadre fond none, plomb ×1.8`,
     cadre.style.fond === "none" && cadre.style.epaisseur === 10.8,
     JSON.stringify(cadre.style));
  const bb = bbox_enfants(a);
  ok(`${nom}: la géométrie tient dans la bbox demandée`,
     bb.x >= B.x - 0.5 && bb.y >= B.y - 0.5
     && bb.x + bb.w <= B.x + B.w + 0.5 && bb.y + bb.h <= B.y + B.h + 0.5,
     JSON.stringify(bb));
  if (nom === "rosette") {
    // la rosette est un CERCLE inscrit (loi du handoff : R = min(w,h)/2,
    // centré) — elle remplit le petit côté, pas une bbox oblongue
    const d = Math.min(B.w, B.h);
    ok("rosette: cercle inscrit centré (diamètre = petit côté)",
       Math.abs(bb.w - d) <= 1 && Math.abs(bb.h - d) <= 1
       && Math.abs((bb.x + bb.w / 2) - (B.x + B.w / 2)) <= 1
       && Math.abs((bb.y + bb.h / 2) - (B.y + B.h / 2)) <= 1,
       JSON.stringify(bb));
  } else {
    ok(`${nom}: et la remplit (largeur et hauteur à ±1)`,
       Math.abs(bb.w - B.w) <= 1 && Math.abs(bb.h - B.h) <= 1,
       JSON.stringify(bb));
  }
}

// ── teintes : les verres piochent DANS la gamme demandée ──
{
  const fonds = MOTIFS.grille.gen(B, O({ gamme: "aube",
    teintes: GAMMES.aube.teintes }))
    .slice(1, -1).map((o) => o.style.fond);
  ok("grille: tous les verres viennent de la gamme aube",
     fonds.every((c) => GAMMES.aube.teintes.includes(c)));
}

// ── le panneau-groupe : méta complète, insertion, ids adressables ──
{
  const g = construire_panneau("arc", B, O());
  ok("construire_panneau rend un groupe à méta vitrail complète",
     g.type === "groupe" && g.vitrail && g.vitrail.motif === "arc"
     && g.vitrail.graine === 41 && g.vitrail.teintes.length === 6
     && g.vitrail.bbox.w === B.w);
  ok("le groupe porte le NOM du motif (calques, §8.5 du handoff)",
     g.name === "Baie à arc", String(g.name));
  let lever = "";
  try { construire_panneau("inconnu", B, O()); }
  catch (e) { lever = e.message; }
  ok("motif inconnu → refus parlant", lever.includes("motif inconnu"),
     lever);
  const doc = docNeuf();
  const id = op_panneau_inserer(doc, "c1", "rosette", B, O({ rangees: 2 }));
  const grp = doc.calques[0].objets[0];
  ok("op_panneau_inserer pose UN groupe, id rendu",
     doc.calques[0].objets.length === 1 && grp.id === id);
  ok("les enfants sont adressables (ids préfixés par le groupe)",
     grp.enfants.length === 42
     && grp.enfants.every((e, k) => e.id === `${id}p${k}`));
}

// ── regénération : id et place conservés, patch appliqué ──
{
  const doc = docNeuf();
  const id = op_panneau_inserer(doc, "c1", "grille", B, O());
  const avant = JSON.stringify(doc.calques[0].objets[0].enfants);
  op_panneau_regen(doc, id, { gamme: "or", teintes: GAMMES.or.teintes });
  const g = doc.calques[0].objets[0];
  ok("regen garde l'id et le compte, change les verres",
     g.id === id && g.enfants.length === 37
     && JSON.stringify(g.enfants) !== avant
     && g.vitrail.gamme === "or");
  ok("les verres regénérés viennent de la gamme or",
     g.enfants.slice(1, -1).every(
       (e) => GAMMES.or.teintes.includes(e.style.fond)));
  op_panneau_regen(doc, id, { colonnes: 2, rangees: 3 });
  ok("regen colonnes/rangées recompte les pièces (fond + 4×3 + cadre)",
     doc.calques[0].objets[0].enfants.length === 14,
     String(doc.calques[0].objets[0].enfants.length));
}

// ── regénération APRÈS déplacement : la bbox suit les enfants ──
{
  const doc = docNeuf();
  const id = op_panneau_inserer(doc, "c1", "plomb", B, O());
  op_deplacer(doc, [id], 50, 30);
  op_panneau_regen(doc, id, { graine: 43 });
  const bb = bbox_enfants(doc.calques[0].objets[0].enfants);
  ok("après op_deplacer(+50,+30), regen regénère À LA NOUVELLE PLACE",
     Math.abs(bb.x - (B.x + 50)) <= 1 && Math.abs(bb.y - (B.y + 30)) <= 1,
     JSON.stringify(bb));
}

// ── refus parlants (état vide compris) ──
{
  const doc = docNeuf();
  doc.calques[0].objets.push({ id: "o1", type: "rect", x: 0, y: 0,
                               w: 10, h: 10, style: {} });
  let lever = "";
  try { op_panneau_regen(doc, "o1", {}); } catch (e) { lever = e.message; }
  ok("regen d'un objet qui n'est pas un panneau → refus parlant",
     lever.includes("pas un panneau"), lever);
  let lever2 = "";
  try { bbox_enfants([]); } catch (e) { lever2 = e.message; }
  ok("bbox d'un panneau vide → refus parlant (pas NaN silencieux)",
     lever2.includes("sans géométrie"), lever2);
}

if (echecs.length) {
  console.error("ECHECS panneaux :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA panneaux : PASS (" + total + " controles)");
