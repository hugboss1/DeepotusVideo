// skeleton.test.mjs — t111 (plan-sprites T12) : le panneau Squelette. Module PUR : os posés au glisser (angle visuel,
// y de la case vers le bas), pièces tracées au glisser, noms uniques et valides, renommage et suppression en cascade,
// corps envoyé à POST /assets/sprite/{job}/skeleton. Les bornes et la règle de nom sont LUES dans sprite_skeleton.py.
import { readFileSync } from "node:fs";
import * as K from "../skeleton.js";
const echecs = []; const ok = (n, c, d = "") => { if (!c) echecs.push(n + (d ? " — " + String(d).slice(0, 240) : "")); };
const J = JSON.stringify;

const py = readFileSync(new URL("../../../backend/app/services/sprite_skeleton.py", import.meta.url), "utf-8");
ok("MAX_OS = celui du backend", K.MAX_OS === Number(py.match(/MAX_OS = (\d+)/)[1]));
ok("MAX_PIECES = celui du backend", K.MAX_PIECES === Number(py.match(/MAX_PIECES = (\d+)/)[1]));
ok("règle de nom = celle du backend", K.NOM.source === py.match(/_NOM = re\.compile\(r"([^"]+)"\)/)[1], K.NOM.source);

const m = { grid: { cell_w: 128, cell_h: 96 }, frames: [{ index: 0 }, { index: 1 }, { index: 2 }] };
const s = K.charger(m);
ok("charger : case, frame 0, aucun os, outil os", s.cw === 128 && s.ch === 96 && s.frame === 0 && !s.bones.length && s.outil === "os" && s.sel === "");

// un os au glisser : de la base vers le bout ; angle VISUEL (y de la case vers le bas), longueur = distance
const o1 = K.ajouterOs(s, { x: 64, y: 80 }, { x: 64, y: 40 });
ok("os vers le HAUT : 90°, longueur 40, parent root, nom auto", o1 && o1.rotation === 90 && o1.length === 40 && o1.parent === "root" && o1.name === "os1", J(o1));
ok("le nouvel os est sélectionné (le suivant s'y accroche)", s.sel === "os1");
const o2 = K.ajouterOs(s, { x: 64, y: 40 }, { x: 94, y: 40 });
ok("os vers la DROITE : 0°, enfant de l'os sélectionné", o2.rotation === 0 && o2.length === 30 && o2.parent === "os1" && o2.name === "os2");
const o3 = K.ajouterOs(s, { x: 10, y: 10 }, { x: 10.5, y: 10.4 });
ok("un clic (moins de 2 px) pose un os court vers le haut", o3.length === 0 && o3.rotation === 90 && o3.parent === "os2");
ok("os vers la GAUCHE : 180°", K.ajouterOs(s, { x: 50, y: 50 }, { x: 20, y: 50 }).rotation === 180);
ok("os vers le BAS : -90°", K.ajouterOs(s, { x: 50, y: 50 }, { x: 50, y: 70 }).rotation === -90);
ok("positions bornées à la case", (() => { const b = K.ajouterOs(s, { x: -5, y: 300 }, { x: 0, y: 0 }); return b.x === 0 && b.y === 96; })());

// une pièce au glisser : accrochée à l'os sélectionné, entiers, rognée
s.sel = "os1";
const p1 = K.ajouterPiece(s, { x: 70.6, y: 50 }, { x: 40.2, y: 90 });
ok("pièce : boîte entière, dans n'importe quel sens, sur l'os sélectionné", J(p1) === J({ name: "piece1", bone: "os1", x: 40, y: 50, w: 31, h: 40 }), J(p1));
ok("pièce qui sort : rognée à la case", (() => { const p = K.ajouterPiece(s, { x: 120, y: 90 }, { x: 140, y: 120 }); return p && p.x + p.w <= 128 && p.y + p.h <= 96; })());
ok("pièce trop petite (< 2 px) : rien", K.ajouterPiece(s, { x: 5, y: 5 }, { x: 6, y: 6 }) === null);
const vide = K.charger(m);
ok("pièce sans os : refusée en le disant", (() => { try { K.ajouterPiece(vide, { x: 0, y: 0 }, { x: 10, y: 10 }); return false; } catch (e) { return /os/.test(e.message); } })());

// noms : valides, uniques ; renommer suit dans les enfants et les pièces
ok("renommer un os : enfants et pièces suivent", K.renommerOs(s, "os1", "torse") && s.bones.find((b) => b.name === "os2").parent === "torse" && s.pieces[0].bone === "torse" && s.sel === "torse");
ok("renommer vers un nom pris : refusé", !K.renommerOs(s, "os2", "torse"));
ok("renommer vers « root » ou un nom sale : refusé", !K.renommerOs(s, "os2", "root") && !K.renommerOs(s, "os2", "../x") && !K.renommerOs(s, "os2", ""));
ok("renommer une pièce : unique et valide", K.renommerPiece(s, "piece1", "corps") && !K.renommerPiece(s, "corps", "piece2") && !K.renommerPiece(s, "corps", "a b"));
ok("nom libre après renommage", K.nomLibre("os", s.bones.map((b) => b.name)) === "os1");

// supprimer un os emporte ses descendants et leurs pièces (sinon le corps serait refusé : parent inconnu)
// chaque os posé devient la sélection : les six forment UNE chaîne torse -> os2 -> … -> os6
ok("la pose enchaîne : chaque os a pour parent le précédent", s.bones.slice(1).every((b, i) => b.parent === s.bones[i].name));
const branche = K.charger(m);
K.ajouterOs(branche, { x: 64, y: 90 }, { x: 64, y: 50 });                  // os1 (racine de la branche)
K.ajouterOs(branche, { x: 64, y: 50 }, { x: 64, y: 30 });                  // os2 < os1
branche.sel = "os1"; K.ajouterOs(branche, { x: 64, y: 50 }, { x: 90, y: 50 });   // os3 < os1 (un bras)
branche.sel = ""; K.ajouterOs(branche, { x: 10, y: 90 }, { x: 10, y: 60 }); // os4 < root (hors branche)
branche.sel = "os2"; K.ajouterPiece(branche, { x: 50, y: 10 }, { x: 78, y: 40 });   // piece1 sur os2
branche.sel = "os4"; K.ajouterPiece(branche, { x: 0, y: 60 }, { x: 20, y: 90 });    // piece2 sur os4
branche.sel = "os2";
const r = K.supprimerOs(branche, "os1");
ok("supprimer : la branche entière et ses pièces, compte rendu", r.os === 3 && r.pieces === 1 && J(branche.bones.map((b) => b.name)) === J(["os4"]) && J(branche.pieces.map((p) => p.name)) === J(["piece2"]) && branche.sel === "", J(r));
ok("supprimer une pièce", K.supprimerPiece(branche, "piece2") && branche.pieces.length === 0 && !K.supprimerPiece(branche, "absente"));
const r6 = K.supprimerOs(s, "torse");
ok("supprimer la base de la chaîne emporte les six os et les deux pièces", r6.os === 6 && r6.pieces === 2 && !s.bones.length && !s.pieces.length, J(r6));

// les bornes du backend
const plein = K.charger(m);
for (let i = 0; i < K.MAX_OS; i++) K.ajouterOs(plein, { x: 1, y: 1 }, { x: 1, y: 1 });
ok("MAX_OS atteint : l'os suivant est refusé", (() => { try { K.ajouterOs(plein, { x: 1, y: 1 }, { x: 1, y: 1 }); return false; } catch (e) { return /24/.test(e.message); } })());

// le corps : ce que la route attend, os PARENT AVANT ENFANT (l'ordre de pose le garantit)
const c = K.charger(m); c.frame = 2;
K.ajouterOs(c, { x: 64, y: 90 }, { x: 64, y: 50 }); K.ajouterOs(c, { x: 64, y: 50 }, { x: 64, y: 30 });
K.ajouterPiece(c, { x: 40, y: 20 }, { x: 88, y: 60 });
const corps = K.corps(c);
ok("corps : frame, os, pièces", corps.frame === 2 && corps.bones.length === 2 && corps.pieces.length === 1 && corps.pieces[0].bone === "os2");
ok("corps : champs de la route seulement", J(Object.keys(corps.bones[1]).sort()) === J(["length", "name", "parent", "rotation", "x", "y"]) && J(Object.keys(corps.pieces[0]).sort()) === J(["bone", "h", "name", "w", "x", "y"]));
ok("corps : parent avant enfant", corps.bones.findIndex((b) => b.name === corps.bones[1].parent) < 1);
ok("pret : faux sans os ou sans pièce", !K.pret(K.charger(m)) && K.pret(c));
ok("allerA borne la frame", K.allerA(c, 9) === 2 && K.allerA(c, -3) === 0);

if (echecs.length) { console.log("ÉCHECS :\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("PASS skeleton.test.mjs");
