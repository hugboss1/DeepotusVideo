// ids_uniques.test.mjs — tout identifiant NEUF est unique dans tout le document : calques, groupes, enfants et
// objets des symboles. Défaut du 12/10 : grouper o1 et o2 donnait {id:"o1", type:"groupe", enfants:[o1, o2]}
// (op_grouper retirait ses enfants PUIS demandait idLibre) — la sélection, l'édition, « Retirer le fond » et la
// suppression pouvaient viser le groupe au lieu de l'image. Chaque op qui crée des objets est rejouée ici ; un
// document d'avant le correctif est réparé (groupe au même id qu'un descendant) ou signalé (autre doublon).
import { op_grouper, op_ecreter, op_symbole_creer, op_symbole_detacher, op_symbole_ouvrir, op_instance_poser,
         op_dupliquer, op_ajouter, op_texte_vectoriser, parserDoc, ids_doublons, op_ids_reparer }
  from "../js/mod-doc.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : ""));
};
const img = (id, x = 0) => ({ id, type: "image", href: "/images/a.png", nat: { w: 10, h: 10 }, x, y: 0, w: 10, h: 10, style: {} });
const rect = (id, x = 0) => ({ id, type: "rect", x, y: 0, w: 4, h: 4, style: { fond: "#123456" } });
const doc = (objets, plus = {}) => ({ v: 1, nom: "I", taille: { w: 100, h: 100 },
  calques: [{ id: "c1", nom: "Calque", visible: true, verrou: false, objets }], ...plus });
// TOUS les ids : calques (groupes et enfants compris) puis intérieur des symboles
function tous(d) {
  const out = [];
  const v = (objs) => { for (const o of objs || []) { out.push(o.id); if (o.type === "groupe") v(o.enfants); } };
  for (const c of d.calques) v(c.objets);
  for (const s of Object.values(d.symboles || {})) v(s.objets);
  return out;
}
const distincts = (d) => { const t = tous(d); return t.length === new Set(t).size; };

// 1. grouper deux images (le cas du 8799)
{
  const d = doc([img("o1"), img("o2", 20)]);
  const gid = op_grouper(d, ["o1", "o2"]);
  const g = d.calques[0].objets[0];
  ok("grouper : le groupe n'a PAS l'id d'un enfant", gid !== "o1" && gid !== "o2", JSON.stringify(g));
  ok("grouper : enfants o1, o2 intacts", g.enfants.map((e) => e.id).join(",") === "o1,o2", JSON.stringify(g));
  ok("grouper : ids tous distincts", distincts(d), tous(d));
  ok("grouper : ids_doublons vide", ids_doublons(d).length === 0, ids_doublons(d));
  // regrouper le groupe avec une 3e image : toujours distincts
  op_ajouter(d, "c1", img(undefined, 40));
  const tiers = d.calques[0].objets[1].id;
  const g2 = op_grouper(d, [gid, tiers]);
  ok("grouper un groupe : id neuf, distinct", ![gid, tiers, "o1", "o2"].includes(g2) && distincts(d), tous(d));
}

// 2. écrêter (« coller dans ») : même faute, même correctif ; le clip reste sur le conteneur
{
  const d = doc([rect("o1"), img("o2")]);
  const gid = op_ecreter(d, "o1", ["o2"]);
  const g = d.calques[0].objets[0];
  ok("écrêter : groupe à id neuf", gid !== "o1" && gid !== "o2" && distincts(d), JSON.stringify(g));
  ok("écrêter : clip = le conteneur o1", g.clip === "o1" && g.enfants[0].id === "o1", JSON.stringify(g));
}

// 3. symbole fait d'un GROUPE, deux instances détachées : les descendants reçoivent aussi des ids neufs
{
  const d = doc([rect("o1"), rect("o2", 10)]);
  const gid = op_grouper(d, ["o1", "o2"]);
  const sid = op_symbole_creer(d, [gid], "S");
  // un objet posé APRÈS : l'intérieur du symbole compte, il ne reprend pas o1/o2
  const neuf = op_ajouter(d, "c1", rect(undefined, 50));
  ok("symbole : un id neuf ne recroise pas l'intérieur du symbole", !["o1", "o2", gid].includes(neuf) && distincts(d), tous(d));
  const i1 = op_instance_poser(d, "c1", sid, 0, 0);
  const i2 = op_instance_poser(d, "c1", sid, 30, 30);
  op_symbole_detacher(d, i1);
  op_symbole_detacher(d, i2);
  ok("détacher deux fois un symbole groupé : ids tous distincts", distincts(d), tous(d));
}

// 4. ouvrir un symbole groupé pour l'éditer : les copies du calque d'édition aussi
{
  const d = doc([rect("o1"), rect("o2", 10)]);
  const gid = op_grouper(d, ["o1", "o2"]);
  const sid = op_symbole_creer(d, [gid], "S");
  op_instance_poser(d, "c1", sid, 0, 0);
  const inst = d.calques[0].objets.find((o) => o.type === "instance" && o.x === 0 && o.y === 0 && o.symbole === sid);
  op_symbole_ouvrir(d, inst.id);
  ok("ouvrir un symbole groupé : ids tous distincts", distincts(d), tous(d));
}

// 5. dupliquer un groupe ÉCRÊTÉ : la copie garde un clip valide (il visait l'ancien id du conteneur)
{
  const d = doc([rect("o1"), img("o2")]);
  const gid = op_ecreter(d, "o1", ["o2"]);
  const [cid] = op_dupliquer(d, [gid]);
  const c = d.calques[0].objets.find((o) => o.id === cid);
  let lu = true;
  try { parserDoc(d); } catch { lu = false; }
  ok("dupliquer un écrêté : clip sur le conteneur de la COPIE", c && c.enfants[0].id === c.clip && c.clip !== "o1", JSON.stringify(c));
  ok("dupliquer un écrêté : le document reste valide", lu);
  ok("dupliquer un écrêté : ids tous distincts", distincts(d), tous(d));
}

// 6. op_ajouter d'un groupe : un id d'enfant libre est gardé (panneau vitrail « o5p0 »), un id pris remplacé
{
  const d = doc([rect("o1"), rect("o2")]);
  const id = op_ajouter(d, "c1", { type: "groupe", style: {}, enfants: [rect("o1"), rect("o9p0"), rect(undefined)] });
  const g = d.calques[0].objets.find((o) => o.id === id);
  ok("ajouter un groupe : enfant à id libre gardé", g.enfants[1].id === "o9p0", JSON.stringify(g));
  ok("ajouter un groupe : enfant à id pris / absent renuméroté", g.enfants[0].id !== "o1" && !!g.enfants[2].id, JSON.stringify(g));
  ok("ajouter un groupe : ids tous distincts", distincts(d), tous(d));
  const ec = op_ajouter(d, "c1", { type: "groupe", clip: "o2", style: {}, enfants: [rect("o2"), rect("o3")] });
  const ge = d.calques[0].objets.find((o) => o.id === ec);
  ok("ajouter un écrêté au conteneur pris : le clip suit", ge.clip === ge.enfants[0].id && ge.clip !== "o2", JSON.stringify(ge));
}

// 7. texte vectorisé en glyphes : le groupe garde l'id du texte, les glyphes ont des ids neufs
{
  const d = doc([{ id: "o1", type: "texte", x: 0, y: 10, contenu: "AB", style: { fond: "#000" } }, rect("o2")]);
  const ids = op_texte_vectoriser(d, "o1", [{ car: "A", d: "M0 0 L1 1" }, { car: "B", d: "M2 0 L3 1" }]);
  ok("texte vectorisé : glyphes à ids neufs, distincts", !ids.includes("o1") && !ids.includes("o2") && distincts(d), tous(d));
}

// 8. un document d'AVANT le correctif : le groupe au même id que son enfant est réparé, rien d'autre
{
  const d = doc([{ id: "o1", type: "groupe", style: {}, enfants: [img("o1"), img("o2", 20)] },
                 { id: "o3", type: "groupe", clip: "o3", style: {}, enfants: [rect("o3"), img("o4")] }]);
  ok("ancien document : doublons signalés", ids_doublons(d).join(",") === "o1,o3", ids_doublons(d));
  const rep = op_ids_reparer(d);
  const [g1, g3] = d.calques[0].objets;
  ok("réparer : deux groupes renumérotés", rep.length === 2 && rep[0][0] === "o1" && rep[1][0] === "o3", JSON.stringify(rep));
  ok("réparer : les ENFANTS gardent leur id", g1.enfants[0].id === "o1" && g3.enfants[0].id === "o3", JSON.stringify(d.calques[0].objets));
  ok("réparer : le clip vise toujours le conteneur", g3.clip === "o3", JSON.stringify(g3));
  ok("réparer : plus aucun doublon, document valide", ids_doublons(d).length === 0 && distincts(d) && !!parserDoc(d), tous(d));
  ok("réparer une 2e fois : rien", op_ids_reparer(d).length === 0);
}
{
  // deux objets DISTINCTS au même id : non renumérotés (on ne sait pas lequel est visé), seulement signalés
  const d = doc([rect("o1"), rect("o1", 10)]);
  ok("autre doublon : non réparé", op_ids_reparer(d).length === 0 && d.calques[0].objets.every((o) => o.id === "o1"));
  ok("autre doublon : signalé", ids_doublons(d).join(",") === "o1", ids_doublons(d));
}

if (echecs.length) {
  console.error("ECHECS ids_uniques :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA ids_uniques : PASS (${n} controles)`);
