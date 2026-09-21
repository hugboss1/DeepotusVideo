// pipette.test.mjs — mod-pipette : le Sélecteur de couleur de classe Affinity
// (pur) — l'échantillon moyen dans un rayon (pixels opaques seulement, borné
// à l'image), l'hex, les champs de la barre contextuelle, et la DÉCISION
// du prélèvement (style de l'objet sous Ctrl, fond / contour de la sélection
// quand « Appliquer », couleur courante sinon ; Alt inverse « Appliquer »).
import { echantillon_rayon, hex_de_rgb, champs_pipette, pipette_decision, RAYONS_PIPETTE } from "../js/mod-pipette.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 250) : "")); };
{
  // image 4 × 4 : colonne 0 rouge opaque, colonne 1 bleue opaque, colonne 2 transparente, colonne 3 verte
  const w = 4, h = 4, data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const k = (y * w + x) * 4; if (x === 0) data.set([255, 0, 0, 255], k); if (x === 1) data.set([0, 0, 255, 255], k); if (x === 3) data.set([0, 255, 0, 255], k); }
  const img = { w, h, data };
  const p = echantillon_rayon(img, 0, 0, 0);
  ok("rayon 0 : le pixel exact", p && p.r === 255 && p.g === 0 && p.b === 0 && p.n === 1, JSON.stringify(p));
  const m = echantillon_rayon(img, 0, 1, 1);
  ok("rayon 1 : moyenne des opaques du carré 3 × 3 borné (6 pixels : 3 rouges + 3 bleus)", m && m.n === 6 && m.r === 128 && m.b === 128 && m.g === 0, JSON.stringify(m));
  ok("les transparents sont ignorés ; un carré tout transparent → a = 0 et n = 0", echantillon_rayon(img, 2, 1, 0).n === 0 && echantillon_rayon(img, 2, 1, 0).a === 0);
  ok("état vide : hors image / image nulle → null", echantillon_rayon(img, -1, 0, 0) === null && echantillon_rayon(img, 4, 0, 0) === null && echantillon_rayon(null, 0, 0, 0) === null);
  ok("hex_de_rgb : majuscules, borné", hex_de_rgb(255, 0, 128) === "#FF0080" && hex_de_rgb(300, -1, 15.6) === "#FF0010");
  const c = champs_pipette({ pipette: { appliquer: true, loupe: false, source: "calque", rayon: 2 } });
  ok("champs : Appliquer (bascule), Loupe (bascule), Source (select global/calque), Rayon (select des rayons)", c.map((x) => x.id + ":" + x.type).join() === "pipAppliquer:bascule,pipLoupe:bascule,pipSource:select,pipRayon:select" && c[0].valeur === true && c[1].valeur === false && c[2].valeur === "calque" && c[3].valeur === "2", c.map((x) => x.id + ":" + x.type + "=" + x.valeur).join());
  ok("champs : état vide → défauts (appliquer, loupe, global, point)", champs_pipette({}).map((x) => String(x.valeur)).join() === "true,true,global,0");
  ok("RAYONS_PIPETTE : 0 → Point (1×1), 1 → 3 × 3, 2 → 5 × 5, 4 → 9 × 9", RAYONS_PIPETTE.map((r) => r.id + "=" + r.libelle).join() === "0=Point (1×1),1=3 × 3,2=5 × 5,4=9 × 9");
  const d = (o) => pipette_decision({ appliquer: true, alt: false, ctrl: false, droit: false, selection: ["a"], cible: "b", ...o });
  ok("décision : Ctrl → le style de l'objet visé", d({ ctrl: true }).action === "style" && d({ ctrl: true }).cible === "b");
  ok("décision : Ctrl sans objet visé → rien", d({ ctrl: true, cible: null }).action === "rien");
  ok("décision : appliquer + sélection → fond ; clic droit → contour", d({}).action === "fond" && d({ droit: true }).action === "contour");
  ok("décision : Alt inverse Appliquer ; sans sélection → couleur courante", d({ alt: true }).action === "courant" && d({ selection: [] }).action === "courant" && d({ appliquer: false }).action === "courant" && d({ appliquer: false, alt: true }).action === "fond");
}
if (echecs.length) { console.error("ECHECS pipette :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA pipette : PASS (12 controles)");
