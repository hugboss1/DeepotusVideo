// hitbox.test.mjs — T112 : hitboxes par frame. Le module est PUR : le même bornage que le backend (sprite_hitbox.py,
// lu en texte pour les constantes), dessin au glisser, sélection, inspecteur, copier/coller entre frames.
import { readFileSync } from "node:fs";
import * as H from "../hitbox.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 240) : "")); };
const J = JSON.stringify;

// les constantes ne dérivent pas du backend
const py = readFileSync(new URL("../../../backend/app/services/sprite_hitbox.py", import.meta.url), "utf-8");
ok("TYPES = ceux du backend", J(H.TYPES) === J(py.match(/TYPES = \(([^)]*)\)/)[1].match(/"(\w+)"/g).map((s) => s.slice(1, -1))), H.TYPES);
ok("MAX_PAR_FRAME = celui du backend", H.MAX_PAR_FRAME === Number(py.match(/MAX_PAR_FRAME = (\d+)/)[1]));

// glisser : deux points dans n'importe quel ordre, entiers, bornés ; un clic sans mouvement ne crée rien
ok("glisser de bas-droite vers haut-gauche", J(H.rectDepuisGlisser({ x: 40.6, y: 30 }, { x: 10.2, y: 5 }, 64, 64, "hurt")) === J({ x: 10, y: 5, w: 31, h: 25, type: "hurt" }));
ok("glisser qui sort de la case : rogné", J(H.rectDepuisGlisser({ x: 50, y: 50 }, { x: 90, y: -8 }, 64, 64)) === J({ x: 50, y: 0, w: 14, h: 50, type: "hit" }));
ok("un clic (moins de 2 px) ne crée rien", H.rectDepuisGlisser({ x: 5, y: 5 }, { x: 6, y: 6 }, 64, 64) === null);

// l'état : une liste par frame, chargée depuis le manifeste (copie, pas référence)
const m = { grid: { cell_w: 64, cell_h: 64 }, frames: [{ index: 0, hitboxes: [{ x: 1, y: 1, w: 4, h: 4, type: "hit" }] }, { index: 1 }, { index: 2 }] };
const s = H.charger(m);
ok("charger : une liste par frame, frames sans clé = vide", s.rects.length === 3 && s.rects[0].length === 1 && s.rects[1].length === 0);
s.rects[0][0].x = 9;
ok("charger copie : le manifeste n'est pas modifié", m.frames[0].hitboxes[0].x === 1);
ok("charge : frame 0 courante, rien de sélectionné, rien à enregistrer", s.frame === 0 && s.sel === -1 && s.sale === false);

H.ajouter(s, { x: 10, y: 10, w: 20, h: 20, type: "hurt" });
ok("ajouter : sélectionne le nouveau, marque à enregistrer", s.rects[0].length === 2 && s.sel === 1 && s.sale === true);
ok("selectionnerSous : le DERNIER dessiné gagne (dessus)", H.selectionnerSous(s, 12, 12) === 1 && s.sel === 1);
ok("selectionnerSous dans le vide : rien", H.selectionnerSous(s, 60, 60) === -1 && s.sel === -1);
s.sel = 1;
H.modifier(s, { x: 60, w: 30 });
ok("modifier (inspecteur) : rogné à la case", J(s.rects[0][1]) === J({ x: 60, y: 10, w: 4, h: 20, type: "hurt" }), J(s.rects[0][1]));
H.modifier(s, { type: "bouclier" });
ok("modifier un type inconnu : ignoré", s.rects[0][1].type === "hurt");

// copier / coller entre frames
H.copier(s);
ok("copier : TOUTE la frame courante (2 rectangles)", s.presse.length === 2);
H.allerA(s, 2);
ok("allerA : change de frame, désélectionne", s.frame === 2 && s.sel === -1);
H.coller(s);
ok("coller : les rectangles arrivent sur la frame 2, copies indépendantes", s.rects[2].length === 2 && s.rects[2][0] !== s.rects[0][0]);
H.coller(s);
ok("coller deux fois : s'ajoute", s.rects[2].length === 4);
for (let i = 0; i < 10; i++) H.coller(s);
ok("coller s'arrête au plafond par frame", s.rects[2].length === H.MAX_PAR_FRAME, s.rects[2].length);
H.allerA(s, 1); H.copier(s); H.allerA(s, 0); const avant = s.rects[0].length; H.coller(s);
ok("copier une frame VIDE puis coller : ne change rien", s.rects[0].length === avant);

H.allerA(s, 0); s.sel = 0;
H.supprimer(s);
ok("supprimer : le sélectionné disparaît, plus de sélection", s.rects[0].length === avant - 1 && s.sel === -1);
ok("supprimer sans sélection : ne fait rien", (() => { const n = s.rects[0].length; H.supprimer(s); return s.rects[0].length === n; })());
ok("allerA hors bornes : borné", (H.allerA(s, 99), s.frame === 2) && (H.allerA(s, -3), s.frame === 0));

// ce qui part au serveur : la forme exacte de POST …/hitboxes
const corps = H.corps(s);
ok("corps : {hitboxes: une liste par frame}", Array.isArray(corps.hitboxes) && corps.hitboxes.length === 3 && corps.hitboxes[1].length === 0);
ok("corps : seulement x, y, w, h, type", corps.hitboxes[0].every((r) => J(Object.keys(r).sort()) === J(["h", "type", "w", "x", "y"])));

if (echecs.length) { console.error("ECHECS hitbox :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA hitbox : PASS");
