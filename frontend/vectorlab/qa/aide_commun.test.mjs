// aide_commun.test.mjs — t126 : le banc commun des dossiers aide/ doit lui-même refuser ce qu'il faut. Les
// animations sont CONSTRUITES ici (en-têtes RIFF/WebP et PNG, seuls lus par animation_lire) : un WebP à une
// image, une toile de mauvaise taille, une APNG à trois images ; puis des dossiers fautifs (fiche orpheline,
// index non trié, animation sans fiche, id en double, fiche invalide).
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { animation_lire, verifier_aide } from "./aide_commun.mjs";

const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 220) : "")); };

const chunk = (id, corps) => { const n = Buffer.alloc(8); n.write(id, 0, "latin1"); n.writeUInt32LE(corps.length, 4); return Buffer.concat([n, corps, corps.length & 1 ? Buffer.alloc(1) : Buffer.alloc(0)]); };
function webp(w, h, images) {
  const vp8x = Buffer.alloc(10); vp8x[0] = 0x12; vp8x.writeUIntLE(w - 1, 4, 3); vp8x.writeUIntLE(h - 1, 7, 3);
  const corps = Buffer.concat([chunk("VP8X", vp8x), chunk("ANIM", Buffer.alloc(6)), ...Array.from({ length: images }, () => chunk("ANMF", Buffer.alloc(17)))]);
  const tete = Buffer.alloc(12); tete.write("RIFF", 0, "latin1"); tete.writeUInt32LE(corps.length + 4, 4); tete.write("WEBP", 8, "latin1");
  return Buffer.concat([tete, corps]);
}
const pchunk = (id, corps) => { const n = Buffer.alloc(8); n.writeUInt32BE(corps.length, 0); n.write(id, 4, "latin1"); return Buffer.concat([n, corps, Buffer.alloc(4)]); };
function apng(w, h, images) {
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), pchunk("IHDR", ihdr), pchunk("acTL", Buffer.alloc(8)),
    ...Array.from({ length: images }, () => pchunk("fcTL", Buffer.alloc(26))), pchunk("IEND", Buffer.alloc(0))]);
}

{
  const a = animation_lire(webp(320, 200, 3)), b = animation_lire(webp(320, 200, 1)), c = animation_lire(webp(640, 400, 3));
  ok("WebP : toile et nombre d'images lus dans VP8X / ANMF", a.w === 320 && a.h === 200 && a.images === 3 && b.images === 1 && c.w === 640 && c.h === 400, JSON.stringify([a, b, c]));
  const p = animation_lire(apng(320, 200, 3));
  ok("APNG : IHDR et fcTL", p.w === 320 && p.h === 200 && p.images === 3, JSON.stringify(p));
  ok("autre format : null", animation_lire(Buffer.from("GIF89a................................")) === null);
}

function dossier(fiches, fichiers) {
  const d = mkdtempSync(join(tmpdir(), "aide_t126_"));
  writeFileSync(join(d, "index.json"), JSON.stringify(fiches));
  for (const [n, b] of Object.entries(fichiers)) writeFileSync(join(d, n), b);
  return d;
}
const F = (id, fichier = `lab.${id}.webp`) => ({ id, titre: "T", phrase: "Une phrase courte.", fichier, version: 1 });
const src = ['<button id="alpha">', '$("#beta")'];
const essais = [
  ["un dossier juste passe", [F("alpha"), F("beta")], { "lab.alpha.webp": webp(320, 200, 3), "lab.beta.webp": apng(320, 200, 3) }, (e) => e.length === 0],
  ["une seule image refusée", [F("alpha")], { "lab.alpha.webp": webp(320, 200, 1) }, (e) => e.some((x) => /trois temps/.test(x))],
  ["mauvaise taille refusée", [F("alpha")], { "lab.alpha.webp": webp(640, 400, 3) }, (e) => e.some((x) => /640×400/.test(x))],
  ["bonne largeur, mauvaise hauteur refusée", [F("alpha")], { "lab.alpha.webp": webp(320, 100, 3) }, (e) => e.some((x) => /320×100/.test(x))],
  ["fichier absent", [F("alpha")], {}, (e) => e.some((x) => /absent/.test(x))],
  ["fiche orpheline (id hors page)", [F("gamma")], { "lab.gamma.webp": webp(320, 200, 3) }, (e) => e.some((x) => /orpheline/.test(x))],
  ["animation sans fiche", [F("alpha")], { "lab.alpha.webp": webp(320, 200, 3), "lab.perdue.webp": webp(320, 200, 3) }, (e) => e.some((x) => /sans fiche/.test(x))],
  ["index non trié", [F("beta"), F("alpha")], { "lab.alpha.webp": webp(320, 200, 3), "lab.beta.webp": webp(320, 200, 3) }, (e) => e.some((x) => /triées/.test(x))],
  ["id en double", [F("alpha"), F("alpha", "lab.alpha2.webp")], { "lab.alpha.webp": webp(320, 200, 3), "lab.alpha2.webp": webp(320, 200, 3) }, (e) => e.some((x) => /double/.test(x))],
  ["fiche invalide (phrase vide)", [{ ...F("alpha"), phrase: "" }], { "lab.alpha.webp": webp(320, 200, 3) }, (e) => e.some((x) => /phrase/.test(x))],
];
for (const [nom, fiches, fichiers, attendu] of essais) {
  const d = dossier(fiches, fichiers);
  const e = verifier_aide(d, src);
  ok(nom, attendu(e), JSON.stringify(e));
  rmSync(d, { recursive: true, force: true });
}
// un id seulement PRÉFIXE d'un autre id de la page ne compte pas (« alp » n'est pas « alpha »)
{
  const d = dossier([F("alp")], { "lab.alp.webp": webp(320, 200, 3) });
  ok("un préfixe d'id n'est pas l'id", verifier_aide(d, src).some((x) => /orpheline/.test(x)));
  rmSync(d, { recursive: true, force: true });
}
if (echecs.length) { console.error("ECHECS aide_commun :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA aide_commun : PASS (14 controles)");
