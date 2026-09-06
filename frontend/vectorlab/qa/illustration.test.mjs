// illustration.test.mjs — une illustration IA se manipule comme TOUTE autre
// forme (remontée du 07/09/2026 : « je dois pouvoir la sélectionner et la
// déplacer ou redimensionner comme toute autre forme rectangle ou ellipse
// créée par l'outil », et « éditable vectoriellement, les lignes, les
// formes »).
//
// La correction : le groupe posé ne porte AUCUN `transform` — les formes
// arrivent au repère du viewBox et c'est la commande de redimensionnement,
// celle des poignées, qui réécrit leurs COORDONNÉES. Ce banc épingle la
// conséquence : déplacer de 100 px déplace de 100 px, l'échelle se compose,
// et les tracés restent au vocabulaire que l'outil Nœuds sait lire.
import { op_ajouter, op_deplacer, op_redimensionner, op_degrouper,
         chemin_parser, chemin_ancres, compilerSVG } from "../js/mod-doc.js";

const echecs = [];
let total = 0;
const ok = (nom, cond, detail = "") => {
  total += 1;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};

const docNeuf = () => ({ v: "1", taille: { w: 604, h: 831 },
  calques: [{ id: "c1", nom: "fond", objets: [] }] });

// ce que la route rend désormais : des FORMES typées, chemins absolus
const REPONSE = {
  ok: true, viewbox: [0, 0, 100, 100], provider: "anthropic",
  modele: "claude-opus-5",
  formes: [
    { type: "path", d: "M 10 10 L 90 10 L 90 90 L 10 90 Z",
      style: { fond: "#1e56c8" } },
    { type: "ellipse", cx: 50, cy: 50, rx: 20, ry: 20,
      style: { fond: "#c0202f" } },
    { type: "rect", x: 20, y: 70, w: 60, h: 10, style: { fond: "#d8b12a" } },
  ],
};

// la pose du client, reproduite ici SANS le DOM : groupe nu + la commande
// de redimensionnement (c'est exactement ce que `VL.iaPoser` exécute)
function poser(doc, rep, nom = "illustration") {
  const vb = rep.viewbox;
  const cote = Math.min(doc.taille.w, doc.taille.h) * 0.6;
  const gid = op_ajouter(doc, "c1", { type: "groupe", style: {}, name: nom,
    enfants: JSON.parse(JSON.stringify(rep.formes)) });
  const av = { x: vb[0], y: vb[1], w: vb[2], h: vb[3] };
  const k = cote / Math.max(av.w, av.h);
  op_redimensionner(doc, [gid], av, {
    x: (doc.taille.w - av.w * k) / 2, y: (doc.taille.h - av.h * k) / 2,
    w: av.w * k, h: av.h * k });
  return gid;
}

const groupeDe = (doc, gid) => doc.calques[0].objets.find((o) => o.id === gid);

// ── le groupe posé ne porte AUCUNE transformation ──
{
  const doc = docNeuf();
  const gid = poser(doc, REPONSE);
  const g = groupeDe(doc, gid);
  ok("le groupe posé n'a pas de transform (c'était la cause du défaut)",
     !g.transform, g.transform);
  ok("aucun enfant ne porte de transform non plus",
     g.enfants.every((e) => !e.transform));
  ok("les trois formes sont là, typées",
     g.enfants.map((e) => e.type).join(",") === "path,ellipse,rect",
     g.enfants.map((e) => e.type).join(","));
  // 604×831 → côté = 0,6 × 604 = 362,4 ; k = 3,624
  ok("l'illustration est centrée sur un carré de 60 % du petit côté",
     Math.abs(g.enfants[1].cx - 302) < 0.5
     && Math.abs(g.enfants[1].rx - 72.5) < 0.5,
     JSON.stringify({ cx: g.enfants[1].cx, rx: g.enfants[1].rx }));
}

// ── DÉPLACER : 100 px du document valent 100 px, pas 100 × k ──
{
  const doc = docNeuf();
  const gid = poser(doc, REPONSE);
  const av = groupeDe(doc, gid).enfants[1].cx;
  op_deplacer(doc, [gid], 100, 50);
  const g = groupeDe(doc, gid);
  ok("déplacer de +100 déplace de 100 (et pas de 100 × échelle)",
     Math.abs(g.enfants[1].cx - (av + 100)) < 0.01,
     JSON.stringify({ avant: av, apres: g.enfants[1].cx }));
  ok("le rectangle enfant suit du même pas",
     Math.abs(g.enfants[2].y - (doc.taille.h - 362.4) / 2 - 70 * 3.624 - 50)
       < 0.5, String(g.enfants[2].y));
  const pts = chemin_parser(g.enfants[0].d);
  ok("et le chemin aussi, coordonnée par coordonnée",
     Math.abs(pts[0].p[0] - ((604 - 362.4) / 2 + 10 * 3.624 + 100)) < 0.5,
     JSON.stringify(pts[0]));
}

// ── REDIMENSIONNER : comme une forme, par la même commande ──
{
  const doc = docNeuf();
  const gid = poser(doc, REPONSE);
  const g0 = groupeDe(doc, gid);
  const b = { x: (604 - 362.4) / 2, y: (831 - 362.4) / 2, w: 362.4, h: 362.4 };
  op_redimensionner(doc, [gid], b, { x: b.x, y: b.y, w: b.w / 2, h: b.h });
  const g = groupeDe(doc, gid);
  ok("redimensionner de moitié en x divise les abscisses, pas les ordonnées",
     Math.abs(g.enfants[1].rx - 36.24) < 0.5
     && Math.abs(g.enfants[1].ry - 72.5) < 0.5,
     JSON.stringify({ rx: g.enfants[1].rx, ry: g.enfants[1].ry }));
  ok("le groupe reste sans transform après redimensionnement", !g.transform);
}

// ── ÉDITABLE : l'outil Nœuds mord sur les chemins posés ──
{
  const doc = docNeuf();
  const gid = poser(doc, REPONSE);
  const g = groupeDe(doc, gid);
  const segs = chemin_parser(g.enfants[0].d);
  ok("le chemin se relit par chemin_parser (M/L/C/Q/Z absolus)",
     segs.length === 5 && segs[0].c === "M" && segs[4].c === "Z",
     JSON.stringify(segs.map((s) => s.c)));
  const ancres = chemin_ancres(segs);
  ok("il porte quatre ancres éditables au nœud", ancres.length === 4,
     String(ancres.length));
  // un `d` que la normalisation N'AURAIT PAS produit tue l'édition : c'est
  // l'invariant que le service backend garantit — épinglé ici côté client
  let leve = "";
  try { chemin_parser("m10 10 h20 v20 z"); }
  catch (e) { leve = e.message; }
  ok("un chemin RELATIF, lui, ne serait pas éditable (d'où la "
     + "normalisation serveur)", !!leve, leve || "chemin_parser l'a accepté !");
}

// ── DÉGROUPER : chaque forme devient indépendante ──
{
  const doc = docNeuf();
  const gid = poser(doc, REPONSE);
  const ids = op_degrouper(doc, gid);
  ok("dégrouper rend trois objets indépendants",
     ids.length === 3 && doc.calques[0].objets.length === 3,
     String(doc.calques[0].objets.length));
  const av = doc.calques[0].objets[1].cx;
  op_deplacer(doc, [ids[1]], 30, 0);
  ok("et chacun se déplace seul",
     doc.calques[0].objets[1].cx === av + 30
     && doc.calques[0].objets[0].d.startsWith("M "),
     JSON.stringify({ av, ap: doc.calques[0].objets[1].cx }));
}

// ── le document compile : rien de ce qui est posé ne casse l'export ──
{
  const doc = docNeuf();
  poser(doc, REPONSE);
  const svg = compilerSVG(doc);
  ok("le SVG exporté porte les trois formes et aucun transform de groupe",
     svg.includes("<path") && svg.includes("<ellipse") && svg.includes("<rect")
     && !/<g[^>]*transform/.test(svg), svg.slice(0, 200));
}

// ── états vides : la pose ne ment pas ──
{
  const doc = docNeuf();
  const gid = poser(doc, { viewbox: [0, 0, 100, 100], formes: [] });
  ok("une réponse sans forme pose un groupe VIDE, sans lever",
     !!gid && groupeDe(doc, gid).enfants.length === 0);
}

if (echecs.length) {
  console.error("ECHECS illustration :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA illustration : PASS (" + total + " controles)");
