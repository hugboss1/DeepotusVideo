// vitrail.test.mjs — le mode vitrail (T5.2/T5.3) : générateur de baie pur
// nourri par la FICHE ÉPINGLÉE (lue ici même — zéro constante recopiée),
// presets de motifs, et la COUVERTURE ANALYTIQUE des plombs (union
// martinez des contours gonflés) dans les bornes de la fiche.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { generer_baie, motif_iris, motif_rayons, motif_halo }
  from "../js/mod-vitrail.js";
import { fournirMartinez, contour_en_multi, aire_multi }
  from "../js/mod-bool.js";

const ici = dirname(fileURLToPath(import.meta.url));
fournirMartinez(createRequire(import.meta.url)("../vendor/martinez.umd.js"));
const fiche = JSON.parse(readFileSync(
  join(ici, "..", "..", "..", "backend", "app", "services",
       "style_vitrail.json"), "utf-8"));
const V = fiche.familles.vitrail;
const ancres = Object.values(V.palette.ancres);
const plomb = Object.values(V.palette.contour)[0];

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 160) : ""));
};

// ── baie ogivale par défaut : comptes, ancres, plomb, géométrie ──
{
  const b = generer_baie(V, { w: 640, h: 960 });
  ok("verre: 2×3 panneaux + tympan = 7", b.verre.length === 7,
     String(b.verre.length));
  ok("contours: cadre + bordure + 1 meneau + 2 traverses = 5",
     b.contours.length === 5, String(b.contours.length));
  ok("les verres cyclent sur les ancres de la fiche",
     b.verre.every((o) => ancres.includes(o.style.fond))
     && b.verre[0].style.fond === V.palette.ancres.cobalt,
     JSON.stringify(b.verre.map((o) => o.style.fond)));
  ok("les contours sont des tracés plomb fond none",
     b.contours.every((o) => o.style.fond === "none"
                          && o.style.contour === plomb));
  ok("épaisseurs cadre/bordure/réseau",
     b.contours[0].style.epaisseur === 18
     && b.contours[1].style.epaisseur === 8
     && b.contours[2].style.epaisseur === 10);
  // d = 0.08 × min(592, 912) = 47.36 ; naissance = 24 + 0.35×912 = 343.2
  const p0 = b.verre[0];
  ok("premier panneau à (71.36, 343.2)",
     Math.abs(p0.x - 71.36) < 0.01 && Math.abs(p0.y - 343.2) < 0.01,
     `${p0.x},${p0.y}`);
  ok("le cadre part de la naissance et passe par l'apex",
     b.contours[0].d.startsWith("M 24 343.2")
     && b.contours[0].d.includes("320 24"), b.contours[0].d.slice(0, 60));
  ok("le tympan est un chemin fermé",
     b.verre[6].type === "path" && b.verre[6].d.endsWith("Z"));
}

// ── bordure clampée aux bornes de la fiche ──
{
  const [lo, hi] = V.bornes.part_bordure_ornementale;
  const b = generer_baie(V, { w: 640, h: 960, bordure: 0.5 });
  ok("bordure clampée au plafond de la fiche",
     Math.abs(b.params.bordure - hi) < 1e-9, String(b.params.bordure));
  const b2 = generer_baie(V, { w: 640, h: 960, bordure: 0.001 });
  ok("bordure clampée au plancher",
     Math.abs(b2.params.bordure - lo) < 1e-9, String(b2.params.bordure));
}

// ── rectangle : pas de tympan, mêmes comptes de contours ──
{
  const b = generer_baie(V, { w: 640, h: 960, forme: "rectangle" });
  ok("rectangle: 6 verres, 5 contours",
     b.verre.length === 6 && b.contours.length === 5,
     `${b.verre.length}/${b.contours.length}`);
  ok("rectangle: cadre en rect", b.contours[0].type === "rect");
}

// ── motifs : groupes insérables, palette de la fiche ──
{
  const iris = motif_iris(V, 100, 100, 1);
  ok("iris: groupe de 4 chemins",
     iris.type === "groupe" && iris.enfants.length === 4
     && iris.enfants.every((e) => e.type === "path"));
  ok("iris: pétales violets, tige émeraude",
     iris.enfants.slice(0, 3).every(
       (e) => e.style.fond === V.palette.ancres.violet_profond)
     && iris.enfants[3].style.fond === V.palette.ancres.emeraude);
  const ray = motif_rayons(V, 0, 0, 80, 8);
  ok("rayons: 8 traits ambre",
     ray.enfants.length === 8 && ray.enfants.every(
       (e) => e.style.fond === "none"
           && e.style.contour === V.palette.ancres.ambre_dore));
  const halo = motif_halo(V, 0, 0, 60);
  ok("halo: 2 anneaux dorés",
     halo.enfants.length === 2
     && halo.enfants.every((e) => e.type === "ellipse"
        && e.style.fond === "none")
     && halo.enfants[1].rx === 75);
}

// ── T5.3 : couverture ANALYTIQUE des plombs dans les bornes de la fiche ──
{
  const mz = createRequire(import.meta.url)("../vendor/martinez.umd.js");
  const b = generer_baie(V, { w: 640, h: 960 });
  let mp = null;
  for (const o of b.contours) {
    const m = contour_en_multi(o, 0.25);
    mp = mp ? mz.union(mp, m) : m;
  }
  const part = aire_multi(mp) / (640 * 960);
  const [lo, hi] = V.bornes.part_contours_plomb;
  console.log(`  (couverture plombs par défaut : ${(part * 100).toFixed(2)} %`
              + ` — bornes fiche ${lo * 100}–${hi * 100} %)`);
  ok("couverture des plombs dans les bornes de la fiche",
     part >= lo && part <= hi, (part * 100).toFixed(2) + " %");
}

if (echecs.length) {
  console.error("ECHECS vitrail :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log("QA vitrail : PASS (14 controles)");
