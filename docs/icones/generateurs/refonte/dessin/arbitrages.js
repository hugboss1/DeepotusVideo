// Deux icônes ajoutées après la relecture des lots (10/10/2026), même charte que la suite :
//  - dz-edit-sans-contour : retire le contour (cadre carré pâle barré) — distinct de dz-edit-sans-couleur (carré plein pâle barré = sans fond)
//  - dz-edit-position     : option « Position » d'une composition de calques (croix de flèches dans des coins de visée)
//                           — distinct de l'outil Déplacement (croix + pointeur) et du verrou de position (croix + cadenas)
const fs = require("fs"), path = require("path");
const G = require("../geo.js"), M = require("../motifs.js");
const OUT = path.join(__dirname, "..", "svg");

// sans contour : anneau carré (bord 2,6) pâle, barre diagonale pleine découpée dedans avec la réserve
const anneau = G.rect(3.2, 3.2, 17.6, 17.6, 2) + G.rect(5.8, 5.8, 12.4, 12.4, 0.8);
const barre = G.pill(4.2, 19.8, 19.8, 4.2, 2.8);
fs.writeFileSync(path.join(OUT, "dz-edit-sans-contour.svg"),
  M.icone([{ d: barre }, { d: anneau, op: .38 }]));

// position : croix de flèches pleine au centre, coins de visée pâles
const croix = G.arrow(12, 12, 12, 4.6, 2.6, 6.4, 3.6) + G.arrow(12, 12, 12, 19.4, 2.6, 6.4, 3.6)
  + G.arrow(12, 12, 4.6, 12, 2.6, 6.4, 3.6) + G.arrow(12, 12, 19.4, 12, 2.6, 6.4, 3.6);
const coin = (x, y, sx, sy) => G.poly([[x, y], [x + 5 * sx, y], [x + 5 * sx, y + 2 * sy], [x + 2 * sx, y + 2 * sy], [x + 2 * sx, y + 5 * sy], [x, y + 5 * sy]]);
const coins = coin(2, 2, 1, 1) + coin(22, 2, -1, 1) + coin(2, 22, 1, -1) + coin(22, 22, -1, -1);
fs.writeFileSync(path.join(OUT, "dz-edit-position.svg"),
  M.icone([{ d: M.union ? M.union(croix) : croix }, { d: coins, op: .38 }]));
console.log("ok");
