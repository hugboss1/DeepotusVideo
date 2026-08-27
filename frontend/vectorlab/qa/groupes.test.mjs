// groupes.test.mjs — groupes, ordre z, remontée au sommet (T2.3).
// Grouper conserve l'ordre de peinture et loge le groupe dans le calque de
// l'objet le plus haut ; dégrouper POUSSE le transform du groupe dans les
// enfants ; l'ordre z se règle par calque ; sommetDe fait remonter un
// enfant à son objet de premier niveau (la sélection au clic en dépend).
import { op_grouper, op_degrouper, op_ordre, op_tourner, sommetDe }
  from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const r = (id) => ({ id, type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} });

const banc = () => ({
  v: 1, nom: "G", taille: { w: 10, h: 10 },
  calques: [
    { id: "c1", nom: "bas", visible: true, verrou: false,
      objets: [r("r1"), r("e1")] },
    { id: "c2", nom: "haut", visible: true, verrou: false,
      objets: [r("r2")] },
    { id: "c3", nom: "verr", visible: true, verrou: true,
      objets: [r("r3")] },
  ],
});

// grouper : hôte = calque du plus haut, enfants en ordre de peinture
{
  const d = banc();
  const gid = op_grouper(d, ["r2", "r1"]);
  ok("groupe créé avec id libre", gid === "o1", gid);
  ok("hôte = calque de l'objet le plus haut (c2)",
     d.calques[1].objets.length === 1 && d.calques[1].objets[0].id === gid);
  ok("enfants en ordre de peinture (r1 puis r2)",
     d.calques[1].objets[0].enfants.map((e) => e.id).join(",") === "r1,r2");
  ok("c1 ne garde que e1",
     d.calques[0].objets.map((o) => o.id).join(",") === "e1");
  // sommetDe : l'enfant remonte au groupe, le libre reste lui-même
  ok("sommetDe enfant → groupe", sommetDe(d, "r1") === gid);
  ok("sommetDe libre → lui-même", sommetDe(d, "e1") === "e1");
  ok("sommetDe inconnu → null", sommetDe(d, "zz") === null);
}

// refus : moins de deux déverrouillés
{
  const d = banc();
  let refus = 0;
  try { op_grouper(d, ["r1"]); } catch { refus++; }
  try { op_grouper(d, ["r1", "r3"]); } catch { refus++; }   // r3 verrouillé
  ok("grouper exige deux objets déverrouillés", refus === 2, String(refus));
}

// dégrouper : à l'index du groupe, transform poussé aux enfants
{
  const d = banc();
  const gid = op_grouper(d, ["r1", "e1"]);
  op_tourner(d, [gid], 5, 5, 90);
  const ids = op_degrouper(d, gid);
  ok("dégroupé à l'index, ordre conservé",
     d.calques[0].objets.map((o) => o.id).join(",") === "r1,e1"
     && ids.join(",") === "r1,e1",
     d.calques[0].objets.map((o) => o.id).join(","));
  ok("transform du groupe poussé aux enfants",
     d.calques[0].objets.every((o) => o.transform === "rotate(90 5 5)"),
     JSON.stringify(d.calques[0].objets.map((o) => o.transform)));
}

// ordre z, par calque
{
  const d = { v: 1, nom: "Z", taille: { w: 1, h: 1 }, calques: [
    { id: "c1", nom: "z", visible: true, verrou: false,
      objets: [r("a"), r("b"), r("c"), r("d")] }] };
  const ids = () => d.calques[0].objets.map((o) => o.id).join(",");
  op_ordre(d, ["b"], "devant");
  ok("devant", ids() === "a,c,d,b", ids());
  op_ordre(d, ["d"], "derriere");
  ok("derrière", ids() === "d,a,c,b", ids());
  op_ordre(d, ["a"], "avant");
  ok("un cran vers l'avant", ids() === "d,c,a,b", ids());
  op_ordre(d, ["a"], "arriere");
  ok("un cran vers l'arrière", ids() === "d,a,c,b", ids());
  op_ordre(d, ["d", "c"], "devant");
  ok("multi conserve l'ordre relatif", ids() === "a,b,d,c", ids());
  let refus = false;
  try { op_ordre(d, ["a"], "milieu"); } catch { refus = true; }
  ok("mode inconnu refusé", refus);
}

if (echecs.length) {
  console.error("ECHECS groupes :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA groupes : PASS (15 controles)");
