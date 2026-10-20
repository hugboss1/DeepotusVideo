// mod-perspective.js — t253 (photocraft 0.10) : l'outil Recadrage de perspective. Glisser = un cadre de quatre coins,
// ou quatre clics ; chaque coin se tire par sa poignée (8 px écran) ; Entrée ou double-clic = image.perspectiveCrop
// {corners (haut-gauche, haut-droit, bas-droit, bas-gauche), interpolation}, le moteur redresse le quadrilatère en
// rectangle (côtés moyens) ; Échap abandonne. Un quadrilatère non convexe est refusé par l'écran avant le moteur.
// Fonctions PURES exportées (qa/selection-m4.test.mjs).
import { rectDepuisGlisser } from "./mod-selection.js";
import { versEcran } from "./mod-vue.js";

// Quatre points dans l'ordre du moteur, quel que soit l'ordre des clics : tri par angle autour du centre (y vers le bas :
// sens horaire), puis rotation pour commencer au coin le plus haut-gauche (plus petit x + y).
export function ordonnerCoins(pts) {
  if (!Array.isArray(pts) || pts.length !== 4) return pts;
  const cx = pts.reduce((s, p) => s + p[0], 0) / 4, cy = pts.reduce((s, p) => s + p[1], 0) / 4;
  const tri = [...pts].sort((a, b) => Math.atan2(a[1] - cy, a[0] - cx) - Math.atan2(b[1] - cy, b[0] - cx));
  let k = 0;
  tri.forEach((p, i) => { if (p[0] + p[1] < tri[k][0] + tri[k][1]) k = i; });
  return [...tri.slice(k), ...tri.slice(0, k)];
}

// Convexe et non dégénéré : les quatre produits vectoriels de côtés consécutifs ont le même signe, aucun nul.
export function convexe(c) {
  if (!Array.isArray(c) || c.length !== 4) return false;
  let signe = 0;
  for (let i = 0; i < 4; i++) {
    const a = c[i], b = c[(i + 1) % 4], d = c[(i + 2) % 4];
    const x = (b[0] - a[0]) * (d[1] - b[1]) - (b[1] - a[1]) * (d[0] - b[0]);
    if (!x) return false;
    if (signe && Math.sign(x) !== signe) return false;
    signe = Math.sign(x);
  }
  return true;
}

const centieme = (v) => Math.round(v * 100) / 100;
export function commandePerspective(coins) {
  if (!Array.isArray(coins) || coins.length !== 4) return null;
  const c = ordonnerCoins(coins).map((p) => [centieme(p[0]), centieme(p[1])]);
  if (!convexe(c)) return null;
  return { command: "image.perspectiveCrop", params: { corners: c, interpolation: "bicubic" } };
}

export const coinsDepuisRect = (r) => [[r.x, r.y], [r.x + r.width, r.y], [r.x + r.width, r.y + r.height], [r.x, r.y + r.height]];

// Indice du coin sous le point ÉCRAN (sx, sy), ou -1.
export function coinSous(coins, sx, sy, v, tol = 8) {
  for (let i = 0; i < (coins || []).length; i++) {
    const s = versEcran(v, coins[i][0], coins[i][1]);
    if (Math.abs(sx - s.x) <= tol && Math.abs(sy - s.y) <= tol) return i;
  }
  return -1;
}

/* ───────────── côté DOM ───────────── */

export function initPerspective(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const toile = PL.$("#toile");
  let coins = [];            // 0 à 4 points document
  let g = null;              // {type: "coin", i} | {type: "cadre", x0, y0, bouge}
  const redessiner = () => PL.dessinerFourmis && PL.dessinerFourmis();
  const abandonner = () => { coins = []; g = null; redessiner(); };

  function valider() {
    if (coins.length < 4) { PL.signaler(T("photolab.perspective.aide")); return; }
    const c = commandePerspective(coins);
    if (!c) { PL.signaler(T("photolab.perspective.non_convexe")); return; }
    coins = []; redessiner();
    PL.executer(c.command, c.params);
  }

  PL.gestes.perspectiveCrop = {
    appui(p) {
      const i = coinSous(coins, p.sx, p.sy, PL.vue.v);
      if (i >= 0) { g = { type: "coin", i }; return; }
      if (!coins.length) { g = { type: "cadre", x0: p.x, y0: p.y, bouge: false }; return; }
      if (coins.length < 4) { coins.push([p.x, p.y]); redessiner(); }
    },
    bouger(p) {
      if (!g) return;
      if (g.type === "coin") coins[g.i] = [p.x, p.y];
      else {
        const r = rectDepuisGlisser(g.x0, g.y0, p.x, p.y);
        g.bouge = r.width >= 2 && r.height >= 2;
        coins = g.bouge ? coinsDepuisRect(r) : [];
      }
      redessiner();
    },
    relacher(p) {
      if (g && g.type === "cadre" && !g.bouge) coins = [[p.x, p.y]];     // un clic : premier des quatre coins
      g = null; redessiner();
    },
    survol(p) { toile.style.cursor = coinSous(coins, p.sx, p.sy, PL.vue.v) >= 0 ? "move" : "crosshair"; },
    double() { if (coins.length > 4) coins.length = 4; valider(); },
    touche(ev) {
      if (ev.key === "Enter") { valider(); return true; }
      if (ev.key === "Escape" && coins.length) { abandonner(); return true; }
      if (ev.key === "Backspace" && coins.length) { coins.pop(); redessiner(); return true; }
      return false;
    },
    annuler() { g = null; },
    quitter() { coins = []; g = null; },
  };

  // Le quadrilatère (fourmis), sa grille 3 × 3 (guide pour aligner les bords) et ses poignées ; rouge s'il n'est pas convexe.
  PL.dessinsSup = PL.dessinsSup || [];
  PL.dessinsSup.push((svg, el, ecran) => {
    if (PL.etat.outil !== "perspectiveCrop" || !coins.length) return;
    const s = coins.map((c) => ecran(c[0], c[1]));
    const d = s.map((q, i) => (i ? "L" : "M") + q.x + " " + q.y).join(" ") + (s.length === 4 ? "Z" : "");
    const mauvais = coins.length === 4 && !convexe(ordonnerCoins(coins));
    for (const classe of ["fourmis-sombre", "fourmis-clair"]) svg.appendChild(el("path", { d, fill: "none" }, classe + (mauvais ? " perspective-mauvais" : "")));
    if (coins.length === 4 && !mauvais) {
      const o = ordonnerCoins(s.map((q) => [q.x, q.y]));
      const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
      for (const t of [1 / 3, 2 / 3]) {
        const [h, b] = [lerp(o[0], o[1], t), lerp(o[3], o[2], t)], [gch, dr] = [lerp(o[0], o[3], t), lerp(o[1], o[2], t)];
        svg.appendChild(el("path", { d: `M${h[0]} ${h[1]}L${b[0]} ${b[1]}M${gch[0]} ${gch[1]}L${dr[0]} ${dr[1]}`, fill: "none" }, "grille-perspective"));
      }
    }
    for (const q of s) svg.appendChild(el("rect", { x: q.x - 4, y: q.y - 4, width: 8, height: 8 }, "poignee"));
  });
}
