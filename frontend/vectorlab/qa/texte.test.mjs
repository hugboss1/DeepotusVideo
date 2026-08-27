// texte.test.mjs — texte SVG (T3.5) : fonte/corps/graisse/interlettrage
// portés par style (op_style marche gratuitement), contenu échappé, posé
// (déplacement) et transformable (rotation, corps à l'échelle au resize).
import { compilerSVG, op_deplacer, op_redimensionner, op_tourner }
  from "../js/mod-doc.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 180) : ""));
};

const banc = () => ({
  v: 1, nom: "T", taille: { w: 400, h: 200 },
  calques: [{ id: "c1", nom: "t", visible: true, verrou: false, objets: [
    { id: "t1", type: "texte", x: 10, y: 40, contenu: "Verre & <plomb>",
      style: { fond: "#1F1512", police: "Georgia", corps: 24,
               graisse: "bold", interlettrage: 2 } },
  ] }],
});

// compilation : mini-snapshot littéral, contenu échappé
{
  const svg = compilerSVG(banc());
  const attendu = `<text data-objet="t1" x="10" y="40"`
    + ` font-family="Georgia" font-size="24" font-weight="bold"`
    + ` letter-spacing="2" fill="#1F1512">Verre &amp; &lt;plomb&gt;</text>`;
  ok("snapshot du <text>", svg.includes(attendu), svg);
}
// défauts : sans fonte déclarée, corps 16, pas d'attributs superflus
{
  const d = banc();
  d.calques[0].objets[0].style = { fond: "#000000" };
  const svg = compilerSVG(d);
  ok("défauts sobres",
     svg.includes(`<text data-objet="t1" x="10" y="40" font-size="16"`
       + ` fill="#000000">`)
     && !svg.includes("font-weight") && !svg.includes("letter-spacing"),
     svg);
}
// posé : le déplacement bouge x/y
{
  const d = banc();
  op_deplacer(d, ["t1"], 5, -10);
  const t = d.calques[0].objets[0];
  ok("déplacé", t.x === 15 && t.y === 30, `${t.x},${t.y}`);
}
// transformable : rotation composée, corps à l'échelle au redimensionnement
{
  const d = banc();
  op_tourner(d, ["t1"], 10, 40, 30);
  ok("rotation posée", d.calques[0].objets[0].transform === "rotate(30 10 40)");
  op_redimensionner(d, ["t1"], { x: 0, y: 0, w: 100, h: 100 },
                                { x: 0, y: 0, w: 100, h: 200 });
  const t = d.calques[0].objets[0];
  ok("corps à l'échelle (×2 en hauteur)", t.style.corps === 48,
     String(t.style.corps));
  ok("y mappé", t.y === 80, String(t.y));
}

if (echecs.length) {
  console.error("ECHECS texte :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA texte : PASS (6 controles)");
