// pinceaux.test.mjs — lot D5 « Couleur et motif » (t480) : les pinceaux artistique, dispersion et motif, VIVANTS
// (js/mod-pinceaux.js). Un tracé peint est un groupe { pinceau } dont la source est cachée et le dessin généré ; il suit
// la source, la définition du pinceau et ses réglages (empreinte), et se décompose comme les objets vivants de D2/D3.
import { createRequire } from "node:module";
import { op_pinceau_creer, op_pinceau_appliquer, op_pinceau_regler, op_pinceau_retirer, op_pinceau_supprimer, pinceaux_rafraichir, GENRES, params_pinceau } from "../js/mod-pinceaux.js";
import { deformations_rafraichir } from "../js/mod-deformer.js";
import { op_derive_detacher } from "../js/mod-vivants.js";
import { polylignes_objet, fournirMartinez } from "../js/mod-bool.js";
import { compilerSVG } from "../js/mod-doc.js";
import { T } from "../js/mod-i18n.js";

fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const pres = (a, b, e = 0.05) => Math.abs(a - b) <= e;
const boite = (o) => {
  const P = polylignes_objet(o).flatMap((l) => l.points);
  return { x0: Math.min(...P.map((p) => p[0])), y0: Math.min(...P.map((p) => p[1])), x1: Math.max(...P.map((p) => p[0])), y1: Math.max(...P.map((p) => p[1])) };
};
// pinceau : deux bandes (rouge en haut, bleue en bas) de 20 × 4 ; carré 10 × 10 ; tracé horizontal de 100 px
const doc = () => ({ v: 1, taille: { w: 300, h: 300 }, calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets: [
  { id: "haut", type: "rect", x: 200, y: 200, w: 20, h: 1, style: { fond: "#ff0000" } },
  { id: "bas", type: "rect", x: 200, y: 203, w: 20, h: 1, style: { fond: "#0000ff" } },
  { id: "carre", type: "rect", x: 250, y: 250, w: 10, h: 10, style: { fond: "#00ff00" } },
  { id: "trace", type: "path", d: "M0 50 L100 50", style: { fond: "none", contour: "#000000" } },
  { id: "vert", type: "path", d: "M50 0 L50 100", style: { fond: "none", contour: "#000000" } },
  { id: "mot", type: "texte", x: 0, y: 0, contenu: "A", style: { fond: "#000000" } }] }] });
const obj = (d, id) => d.calques[0].objets.find((o) => o.id === id);
const genere = (g) => g.enfants.filter((e) => e.genere);

/* ── réglages ── */
ok("réglages : une clé d'un autre genre est ignorée", !("espacement" in params_pinceau("artistique", { espacement: 5 })));
ok("réglages : choix inconnu → refus traduit", (() => { try { params_pinceau("motif", { ajustement: "zz" }); return false; } catch (e) { return e.message === T("vectorlab.pinceaux.choix", { v: "zz" }); } })());
ok("réglages : l'espacement du motif peut être négatif, pas celui de la dispersion", params_pinceau("motif", { espacement: -50 }).espacement === -50
   && refus(() => params_pinceau("dispersion", { espacement: -50 })) === T("vectorlab.pinceaux.borne", { min: 1, max: 1000 }));
ok("réglages : la graine est entière", params_pinceau("dispersion", { graine: 3.6 }).graine === 4);

ok("trois genres", JSON.stringify(GENRES) === JSON.stringify(["artistique", "dispersion", "motif"]));

/* ── créer un pinceau ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["haut", "bas"], { nom: "Ruban", genre: "artistique" });
  const p = d.pinceaux[pid];
  ok("créé : id pc<n>, nom, genre, objets ramenés à l'origine, taille", pid === "pc1" && p.nom === "Ruban" && p.genre === "artistique" && pres(p.largeur, 20) && pres(p.hauteur, 4)
     && p.objets[0].transform === "translate(-200 -200)" && d.calques[0].objets.length === 6, JSON.stringify(p));
  ok("genre inconnu → refus traduit", refus(() => op_pinceau_creer(d, ["haut"], { genre: "soies" })) === T("vectorlab.pinceaux.genre", { genre: "soies" }));
  ok("sans sélection → refus traduit", refus(() => op_pinceau_creer(d, [], { genre: "artistique" })) === T("vectorlab.pinceaux.aucune_selection"));
  ok("nom par défaut", d.pinceaux[op_pinceau_creer(d, ["carre"], { genre: "motif" })].nom === T("vectorlab.pinceaux.nom_defaut", { n: 2 }));
}

/* ── artistique ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["haut", "bas"], { genre: "artistique" });
  const [gid] = op_pinceau_appliquer(d, ["trace"], pid, {});
  const g = obj(d, gid);
  ok("appliqué : un groupe vivant à la place du tracé, source cachée, dessin généré", g && g.pinceau.id === pid && g.enfants[0].id === "trace" && g.enfants[0].cache === true
     && genere(g).length === 2 && genere(g)[0].id === `${gid}_p1` && !obj(d, "trace"), JSON.stringify(g && g.enfants.map((e) => e.id)));
  const [r, b] = genere(g).map(boite);
  ok("étiré le long du tracé : x de 0 à 100, la bande rouge au-dessus (y 48–49), la bleue en dessous (51–52)", pres(r.x0, 0) && pres(r.x1, 100) && pres(r.y0, 48) && pres(r.y1, 49) && pres(b.y0, 51) && pres(b.y1, 52), JSON.stringify([r, b]));
  ok("un rectangle du pinceau reste fermé", genere(g).every((e) => /Z$/.test(e.d)));
  ok("styles du pinceau gardés", genere(g)[0].style.fond === "#ff0000" && genere(g)[1].style.fond === "#0000ff");
  op_pinceau_regler(d, gid, { echelle: 2 });
  ok("échelle 2 : deux fois plus épais", pres(boite(genere(obj(d, gid))[0]).y0, 46) && pres(boite(genere(obj(d, gid))[1]).y1, 54));
  op_pinceau_regler(d, gid, { echelle: 1, retourner: true });
  ok("retourner : la bande rouge passe dessous", pres(boite(genere(obj(d, gid))[0]).y0, 51));
  op_pinceau_regler(d, gid, { retourner: false, proportionnel: true });
  ok("proportionnel : l'épaisseur suit l'étirement (×5)", pres(boite(genere(obj(d, gid))[0]).y0, 40) && pres(boite(genere(obj(d, gid))[0]).y1, 45), JSON.stringify(boite(genere(obj(d, gid))[0])));
  ok("réglage hors bornes → refus traduit, rien de changé", refus(() => op_pinceau_regler(d, gid, { echelle: 0 })) === T("vectorlab.pinceaux.borne", { min: 0.05, max: 20 }) && obj(d, gid).pinceau.params.proportionnel === true);
  // un tracé vertical : le dessin se pose sur la normale (la bande rouge à droite, x 51–52)
  const dv = doc(); const pv = op_pinceau_creer(dv, ["haut", "bas"], { genre: "artistique" });
  const [gv] = op_pinceau_appliquer(dv, ["vert"], pv, {});
  const bv = boite(genere(obj(dv, gv))[0]);
  ok("tracé vertical : décalage sur la normale", pres(bv.x0, 51) && pres(bv.x1, 52) && pres(bv.y0, 0) && pres(bv.y1, 100), JSON.stringify(bv));
  // un tracé fermé : le dessin fait tout le tour (le côté gauche compris)
  const df = doc(); const pf = op_pinceau_creer(df, ["haut", "bas"], { genre: "artistique" });
  df.calques[0].objets.push({ id: "boucle", type: "rect", x: 0, y: 0, w: 100, h: 50, style: { fond: "none" } });
  const [gf] = op_pinceau_appliquer(df, ["boucle"], pf, {});
  const pts = genere(obj(df, gf)).flatMap((e) => polylignes_objet(e).flatMap((l) => l.points));
  ok("tracé fermé : le côté de retour est peint aussi", pts.some(([x, y]) => x < 3 && y > 20 && y < 30), pts.length);
  // un sous-tracé de longueur nulle ne pose rien
  const dz = doc(); const pz = op_pinceau_creer(dz, ["haut", "bas"], { genre: "artistique" });
  obj(dz, "trace").d = "M10 10 L10 10 M0 50 L100 50";
  ok("sous-tracé de longueur nulle : ignoré", genere(obj(dz, op_pinceau_appliquer(dz, ["trace"], pz, {})[0])).length === 2);
  // un pinceau fait d'un GROUPE : la transformation du groupe s'applique à ses feuilles
  const dg = doc();
  dg.calques[0].objets.push({ id: "grp", type: "groupe", style: {}, enfants: [obj(dg, "haut"), obj(dg, "bas")] });
  dg.calques[0].objets = dg.calques[0].objets.filter((o) => o.id !== "haut" && o.id !== "bas");
  const pg = op_pinceau_creer(dg, ["grp"], { genre: "artistique" });
  const bg = boite(genere(obj(dg, op_pinceau_appliquer(dg, ["trace"], pg, {})[0]))[0]);
  ok("pinceau fait d'un groupe : même dessin", pres(bg.y0, 48) && pres(bg.y1, 49) && pres(bg.x1, 100), JSON.stringify(bg));
  // un pinceau sans dessin (un texte seul) ne se pose pas en artistique
  const dt = doc(); const pt = op_pinceau_creer(dt, ["mot"], { genre: "artistique" });
  ok("pinceau sans dessin → refus traduit", refus(() => op_pinceau_appliquer(dt, ["trace"], pt, {})) === T("vectorlab.pinceaux.sans_geometrie"));
  // un tracé courbe : chaque point du dessin reste à distance ≤ 2 de la courbe
  const c = doc(); const pc = op_pinceau_creer(c, ["haut", "bas"], { genre: "artistique" });
  obj(c, "trace").d = "M0 50 C30 0 70 100 100 50";
  const [gc] = op_pinceau_appliquer(c, ["trace"], pc, {});
  const src = polylignes_objet({ type: "path", d: "M0 50 C30 0 70 100 100 50" })[0].points;
  const loin = genere(obj(c, gc)).flatMap((e) => polylignes_objet(e).flatMap((l) => l.points)).map(([x, y]) => Math.min(...src.slice(1).map((q, i) => { const [ax, ay] = src[i], [bx, by] = q, L2 = (bx - ax) ** 2 + (by - ay) ** 2 || 1; const t = Math.max(0, Math.min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / L2)); return Math.hypot(ax + t * (bx - ax) - x, ay + t * (by - ay) - y); }))).reduce((m, v) => Math.max(m, v), 0);
  ok("tracé courbe : le dessin suit la courbe (écart ≤ 2,2)", loin <= 2.2, loin);
}

/* ── motif ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["carre"], { genre: "motif" });
  const [gid] = op_pinceau_appliquer(d, ["trace"], pid, {});
  ok("motif, étirer : 10 tuiles de 10 sur 100", genere(obj(d, gid)).length === 10 && pres(boite(genere(obj(d, gid))[9]).x1, 100));
  obj(d, gid).enfants[0].d = "M0 50 L95 50";
  pinceaux_rafraichir(d);
  ok("étirer sur 95 : 10 tuiles de 9,5, la dernière finit à 95", genere(obj(d, gid)).length === 10 && pres(boite(genere(obj(d, gid))[9]).x1, 95) && pres(boite(genere(obj(d, gid))[0]).x1, 9.5));
  op_pinceau_regler(d, gid, { ajustement: "couper" });
  ok("couper sur 95 : 9 tuiles entières, la dernière finit à 90", genere(obj(d, gid)).length === 9 && pres(boite(genere(obj(d, gid))[8]).x1, 90));
  op_pinceau_regler(d, gid, { ajustement: "etirer", espacement: 100 });
  obj(d, gid).enfants[0].d = "M0 50 L100 50";
  pinceaux_rafraichir(d);
  const t = genere(obj(d, gid)).map(boite);
  ok("espacement 100 % : 5 tuiles, un vide d'une tuile entre deux", t.length === 5 && pres(t[1].x0, 20) && pres(t[1].x1, 30), JSON.stringify(t.map((x) => [x.x0, x.x1])));
}

/* ── dispersion ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["carre"], { genre: "dispersion" });
  const [gid] = op_pinceau_appliquer(d, ["trace"], pid, { espacement: 100, rotation: "fixe" });
  const c = genere(obj(d, gid));
  ok("dispersion : une copie tous les 10 px, de 0 à 100 (11), groupes générés", c.length === 11 && c.every((e) => e.type === "groupe") && c[0].transform === "translate(0 50) rotate(0) scale(1) translate(-5 -5)"
     && c[0].enfants[0].id === `${gid}_p1_1`, JSON.stringify(c[0]));
  const [gv] = op_pinceau_appliquer(d, ["vert"], pid, { espacement: 100, rotation: "trace" });
  const d2 = doc(); const p2 = op_pinceau_creer(d2, ["carre"], { genre: "dispersion" });
  ok("rotation fixe sur un tracé vertical : 0°", genere(obj(d2, op_pinceau_appliquer(d2, ["vert"], p2, { rotation: "fixe" })[0]))[0].transform.includes("rotate(0)"));
  ok("écart latéral (100 % de la largeur) : sur la normale", genere(obj(d2, op_pinceau_appliquer(d2, ["trace"], p2, { rotation: "fixe", ecart: 100 })[0]))[0].transform.startsWith("translate(0 60)"));
  ok("rotation qui suit le tracé : 90° sur un tracé vertical", genere(obj(d, gv))[0].transform.includes("rotate(90)"), genere(obj(d, gv))[0].transform);
  op_pinceau_regler(d, gid, { taille_alea: 50, rotation_alea: 45, ecart_alea: 100, graine: 3 });
  const a1 = JSON.stringify(genere(obj(d, gid)).map((e) => e.transform));
  op_pinceau_regler(d, gid, { graine: 3 });
  ok("aléa à graine : le même tirage", JSON.stringify(genere(obj(d, gid)).map((e) => e.transform)) === a1);
  op_pinceau_regler(d, gid, { graine: 4 });
  ok("autre graine : un autre tirage", JSON.stringify(genere(obj(d, gid)).map((e) => e.transform)) !== a1);
  const tailles = genere(obj(d, gid)).map((e) => +/scale\(([\d.]+)\)/.exec(e.transform)[1]);
  ok("taille ± 50 % : entre 0,5 et 1,5", tailles.every((s) => s >= 0.5 && s <= 1.5) && new Set(tailles).size > 1, tailles.join(","));
  ok("trop de copies → refus traduit", refus(() => op_pinceau_regler(d, gid, { espacement: 1, taille: 1 })) === T("vectorlab.pinceaux.trop", { n: 2000 }));
}

/* ── vivant : source, définition, empreinte ; retirer, supprimer, décomposer ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["haut", "bas"], { genre: "artistique" });
  const [gid] = op_pinceau_appliquer(d, ["trace"], pid, {});
  ok("rien n'a changé : pas de recalcul", pinceaux_rafraichir(d) === 0);
  obj(d, gid).enfants[0].d = "M0 50 L200 50";
  ok("la source change : recalcul (appelé aussi par deformations_rafraichir)", deformations_rafraichir(d) === 1 && pres(boite(genere(obj(d, gid))[0]).x1, 200));
  d.pinceaux[pid].objets[0].style.fond = "#123456";
  pinceaux_rafraichir(d);
  ok("la définition change : le dessin suit", genere(obj(d, gid))[0].style.fond === "#123456");
  ok("le SVG ne montre pas la source cachée", !/data-objet="trace"/.test(compilerSVG(d)) && /data-objet="o\d+_p1"/.test(compilerSVG(d)), compilerSVG(d).slice(0, 300));
  // décomposer : le dessin reste en objets ordinaires
  const x = JSON.parse(JSON.stringify(d));
  op_derive_detacher(x, gid);
  const gx = obj(x, gid);
  ok("décomposer : le dessin gardé, la source et la recette partent", !gx.pinceau && gx.enfants.length === 2 && gx.enfants.every((e) => !e.genere && !e.cache && !/_p\d/.test(e.id)), JSON.stringify(gx.enfants.map((e) => e.id)));
  // retirer : le tracé revient seul, visible
  const y = JSON.parse(JSON.stringify(d));
  ok("retirer : la source revient à la place du groupe", op_pinceau_retirer(y, gid) === "trace" && obj(y, "trace") && !obj(y, "trace").cache && !obj(y, gid));
  // supprimer la définition : tous ses tracés reviennent simples
  const [g2] = op_pinceau_appliquer(d, ["vert"], pid, {});
  op_pinceau_supprimer(d, pid);
  ok("supprimer le pinceau : ses tracés reviennent simples", !d.pinceaux[pid] && obj(d, "trace") && obj(d, "vert") && !obj(d, gid) && !obj(d, g2));
}

/* ── refus ── */
{
  const d = doc();
  const pid = op_pinceau_creer(d, ["carre"], { genre: "motif" });
  ok("pinceau inconnu → refus traduit", refus(() => op_pinceau_appliquer(d, ["trace"], "pc9", {})) === T("vectorlab.pinceaux.inconnu", { id: "pc9" }));
  ok("un texte n'est pas un tracé → refus traduit", refus(() => op_pinceau_appliquer(d, ["mot"], pid, {})) === T("vectorlab.pinceaux.pas_trace", { type: "texte" }));
  ok("rien de sélectionné → refus traduit", refus(() => op_pinceau_appliquer(d, [], pid, {})) === T("vectorlab.pinceaux.aucune_selection"));
  d.calques.push({ id: "c2", nom: "v", visible: true, verrou: true, objets: [{ id: "tv", type: "path", d: "M0 0 L9 9", style: {} }] });
  ok("calque verrouillé → refus traduit", refus(() => op_pinceau_appliquer(d, ["tv"], pid, {})) === T("vectorlab.repeter.verrou"));
  d.calques[1].verrou = false;
  const [gl] = op_pinceau_appliquer(d, ["tv"], pid, {});
  d.calques[1].verrou = true;
  ok("retirer sur un calque verrouillé → refus traduit", refus(() => op_pinceau_retirer(d, gl)) === T("vectorlab.repeter.verrou"));
  ok("régler un objet sans pinceau → refus traduit", refus(() => op_pinceau_regler(d, "trace", {})) === T("vectorlab.pinceaux.pas_pinceau", { id: "trace" }));
}

if (echecs.length) {
  console.error(`pinceaux : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("pinceaux : ok");
