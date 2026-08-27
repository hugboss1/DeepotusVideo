// booleens.test.mjs — l'aplatissement (T3.2) : objets → anneaux de points,
// tolérance 0,25 px, transform APPLIQUÉ, sous-chemins multiples ; aire_de
// pour les contrôles à ±0,5 % du contrat.
import { aplatir_objet, aire_de } from "../js/mod-bool.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};
const pres = (nom, obtenu, attendu, pct = 0.5) => {
  const marge = Math.abs(attendu) * pct / 100;
  ok(nom, Math.abs(obtenu - attendu) <= marge,
     `${obtenu} attendu ${attendu} ±${marge.toFixed(1)}`);
};

// rect : anneau exact, fermé (premier == dernier)
{
  const a = aplatir_objet({ id: "r", type: "rect", x: 10, y: 20, w: 100,
                            h: 50, style: {} });
  ok("rect: un anneau fermé de 5 points",
     a.length === 1 && a[0].length === 5
     && a[0][0][0] === a[0][4][0] && a[0][0][1] === a[0][4][1],
     JSON.stringify(a));
  pres("rect: aire exacte", aire_de(a), 5000, 0.0001);
}

// ellipse : approximation adaptative dans la tolérance d'aire
{
  const a = aplatir_objet({ id: "e", type: "ellipse", cx: 0, cy: 0,
                            rx: 60, ry: 40, style: {} });
  pres("ellipse: aire πab ±0,5 %", aire_de(a), Math.PI * 60 * 40);
}

// path : cercle en 4 cubiques (k = 0.5523) — la subdivision tient l'aire
{
  const k = 27.6142;
  const d = `M 50 0 C 50 ${k} ${k} 50 0 50 C ${-k} 50 -50 ${k} -50 0`
          + ` C -50 ${-k} ${-k} -50 0 -50 C ${k} -50 50 ${-k} 50 0 Z`;
  const a = aplatir_objet({ id: "p", type: "path", d, style: {} });
  pres("cercle en cubiques: aire πr² ±0,5 %", aire_de(a), Math.PI * 2500);
}

// sous-chemins multiples → plusieurs anneaux
{
  const a = aplatir_objet({ id: "p", type: "path",
    d: "M 0 0 L 10 0 L 10 10 Z M 20 0 L 30 0 L 30 10 Z", style: {} });
  ok("deux sous-chemins → deux anneaux", a.length === 2,
     String(a.length));
}

// transform appliqué : la rotation conserve l'aire, la bbox tourne
{
  const a = aplatir_objet({ id: "r", type: "rect", x: 0, y: 0, w: 100,
                            h: 50, style: {}, transform: "rotate(90 0 0)" });
  pres("rotation: aire conservée", aire_de(a), 5000, 0.0001);
  const xs = a[0].map((p) => p[0]);
  ok("rotation: la bbox a tourné (x dans [-50, 0])",
     Math.min(...xs) >= -50.01 && Math.max(...xs) <= 0.01,
     `${Math.min(...xs)}..${Math.max(...xs)}`);
}

// rotations composées (héritées d'un dégroupage) : matrice bien pliée
{
  const a = aplatir_objet({ id: "r", type: "rect", x: 0, y: 0, w: 10,
    h: 10, style: {}, transform: "rotate(45 0 0) rotate(45 0 0)" });
  const xs = a[0].map((p) => p[0]);
  ok("deux rotate 45 = rotate 90", Math.max(...xs) <= 0.01
     && Math.min(...xs) >= -10.01, `${Math.min(...xs)}..${Math.max(...xs)}`);
}

// groupe : enfants aplatis, transforms composés parent×enfant
{
  const a = aplatir_objet({ id: "g", type: "groupe", style: {},
    transform: "rotate(90 0 0)", enfants: [
      { id: "r", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] });
  pres("groupe: aire de l'enfant", aire_de(a), 100, 0.0001);
  ok("groupe: transform du parent appliqué",
     Math.max(...a[0].map((p) => p[0])) <= 0.01);
}

// texte : refus net (vectorisation hors périmètre)
{
  let refus = false;
  try {
    aplatir_objet({ id: "t", type: "texte", x: 0, y: 0, contenu: "x",
                    style: {} });
  } catch { refus = true; }
  ok("texte refusé", refus);
}

if (echecs.length) {
  console.error("ECHECS booleens :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA booleens : PASS (11 controles)");
