// degrades.test.mjs — dégradés (T2.2) : modèle en coordonnées DOCUMENT
// (userSpaceOnUse — les poignées sur canevas en dépendent), stops triés à
// la compilation, référence par style.fond = "grad:<id>", repli "none" si
// le dégradé manque (jamais de document cassé).
import { op_degrade_creer, op_degrade_modifier, op_degrade_stop_ajouter,
         op_degrade_stop_modifier, op_degrade_stop_supprimer,
         op_degrade_supprimer, op_style, compilerSVG } from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 180) : ""));
};

const banc = () => ({
  v: 1, nom: "Deg", taille: { w: 100, h: 100 },
  calques: [{ id: "c1", nom: "a", visible: true, verrou: false, objets: [
    { id: "r1", type: "rect", x: 10, y: 10, w: 80, h: 40, style: {} },
  ] }],
});

// création + application + compilation defs
{
  const d = banc();
  const id = op_degrade_creer(d, { type: "lineaire", x1: 10, y1: 10,
    x2: 90, y2: 10, stops: [{ t: 0, couleur: "#0047AB" },
                            { t: 1, couleur: "#DAA520" }] });
  ok("id de dégradé", id === "g1", id);
  op_style(d, ["r1"], { fond: "grad:" + id });
  const svg = compilerSVG(d);
  ok("defs émis", svg.includes("<defs>") && svg.includes("</defs>"));
  ok("linearGradient userSpaceOnUse",
     svg.includes(`<linearGradient id="g1" gradientUnits="userSpaceOnUse"`
       + ` x1="10" y1="10" x2="90" y2="10">`), svg);
  ok("stops émis",
     svg.includes(`<stop offset="0" stop-color="#0047AB"/>`)
     && svg.includes(`<stop offset="1" stop-color="#DAA520"/>`), svg);
  ok("le fond réfère url(#g1)", svg.includes(`fill="url(#g1)"`), svg);
}

// radial + stops triés par t + stop-opacity
{
  const d = banc();
  const id = op_degrade_creer(d, { type: "radial", cx: 50, cy: 30, r: 40,
    stops: [{ t: 1, couleur: "#000000" },
            { t: 0, couleur: "#FFFFFF", opacite: 0.5 }] });
  op_style(d, ["r1"], { fond: "grad:" + id });
  const svg = compilerSVG(d);
  ok("radialGradient", svg.includes(`<radialGradient id="g1"`
     + ` gradientUnits="userSpaceOnUse" cx="50" cy="30" r="40">`), svg);
  const i0 = svg.indexOf('offset="0"'), i1 = svg.indexOf('offset="1"');
  ok("stops triés par t", i0 >= 0 && i1 > i0);
  ok("stop-opacity émis",
     svg.includes(`<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.5"/>`),
     svg);
}

// modification des poignées + stops
{
  const d = banc();
  const id = op_degrade_creer(d, { type: "lineaire", x1: 0, y1: 0, x2: 1,
    y2: 0, stops: [{ t: 0, couleur: "#000000" }, { t: 1, couleur: "#FFFFFF" }] });
  op_degrade_modifier(d, id, { x2: 100, y2: 50 });
  ok("poignées modifiées", d.degrades[id].x2 === 100 && d.degrades[id].y2 === 50);
  const i = op_degrade_stop_ajouter(d, id, { t: 0.5, couleur: "#FF0000" });
  ok("stop ajouté", d.degrades[id].stops[i].couleur === "#FF0000");
  op_degrade_stop_modifier(d, id, i, { t: 0.6 });
  ok("stop modifié", d.degrades[id].stops[i].t === 0.6);
  op_degrade_stop_supprimer(d, id, i);
  ok("stop supprimé", d.degrades[id].stops.length === 2);
  let refus = false;
  try { op_degrade_stop_supprimer(d, id, 0); } catch { refus = true; }
  ok("jamais moins de deux stops", refus);
}

// repli : dégradé manquant → fill none ; suppression du dégradé
{
  const d = banc();
  op_style(d, ["r1"], { fond: "grad:fantome" });
  ok("repli none", compilerSVG(d).includes(`fill="none"`), compilerSVG(d));
  const id = op_degrade_creer(d, { type: "lineaire", x1: 0, y1: 0, x2: 1,
    y2: 1, stops: [{ t: 0, couleur: "#000000" }, { t: 1, couleur: "#FFFFFF" }] });
  op_degrade_supprimer(d, id);
  ok("dégradé supprimé", !(id in d.degrades));
  let refus = 0;
  try { op_degrade_creer(d, { type: "conique", stops: [] }); } catch { refus++; }
  try { op_degrade_modifier(d, "gX", {}); } catch { refus++; }
  ok("type inconnu + id inconnu refusés", refus === 2, String(refus));
}

if (echecs.length) {
  console.error("ECHECS degrades :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA degrades : PASS (13 controles)");
