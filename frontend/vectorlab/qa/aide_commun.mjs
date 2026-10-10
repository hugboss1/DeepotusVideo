// aide_commun.mjs — t126 : le contrôle d'un dossier aide/ (Vectorlab, Spritelab, Tilelab), partagé par les
// bancs aide.test.mjs des trois labs. Une fiche que valider_fiche refuse n'apparaît JAMAIS (mod-didact
// l'ignore en silence) : ce banc dit pourquoi. Il lit aussi l'animation elle-même — un WebP animé de
// 320 × 200 à TROIS images (chunk VP8X pour la toile, un ANMF par image), ou une APNG (IHDR + un fcTL par
// image) — et vérifie que l'id de la fiche existe dans les sources de la page (une option renommée laisserait
// une fiche orpheline, muette).
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { valider_fiche } from "../js/mod-didact.js";

const u24 = (b, o) => b[o] | (b[o + 1] << 8) | (b[o + 2] << 16);
const u32be = (b, o) => ((b[o] << 24) >>> 0) + (b[o + 1] << 16) + (b[o + 2] << 8) + b[o + 3];

// { w, h, images } d'un WebP animé ou d'une APNG ; null si le format n'est pas reconnu
export function animation_lire(b) {
  if (b.length > 12 && b.toString("latin1", 0, 4) === "RIFF" && b.toString("latin1", 8, 12) === "WEBP") {
    let o = 12, w = 0, h = 0, images = 0;
    while (o + 8 <= b.length) {
      const id = b.toString("latin1", o, o + 4), n = b.readUInt32LE(o + 4);
      if (id === "VP8X") { w = u24(b, o + 12) + 1; h = u24(b, o + 15) + 1; }
      if (id === "ANMF") images++;
      o += 8 + n + (n & 1);
    }
    return { w, h, images };
  }
  if (b.length > 24 && b[0] === 0x89 && b.toString("latin1", 1, 4) === "PNG") {
    let o = 8, w = 0, h = 0, images = 0;
    while (o + 8 <= b.length) {
      const n = u32be(b, o), id = b.toString("latin1", o + 4, o + 8);
      if (id === "IHDR") { w = u32be(b, o + 8); h = u32be(b, o + 12); }
      if (id === "fcTL") images++;
      o += 12 + n;
    }
    return { w, h, images };
  }
  return null;
}

// echecs[] du dossier aide/ d'un lab ; sources = textes (HTML, JS) où chaque id doit apparaître
export function verifier_aide(dossier, sources) {
  const e = [];
  const fIndex = join(dossier, "index.json");
  if (!existsSync(fIndex)) return [`${fIndex} absent`];
  let index;
  try { index = JSON.parse(readFileSync(fIndex, "utf-8")); } catch (err) { return [`index.json illisible : ${err.message}`]; }
  if (!Array.isArray(index) || !index.length) return ["index.json : liste de fiches attendue"];
  const ids = new Set(), fichiers = new Set();
  for (const f of index) {
    const v = valider_fiche(f);
    if (v.length) { e.push(`${f && f.id} : ${v.join(", ")}`); continue; }
    if (ids.has(f.id)) e.push(`${f.id} : id en double`);
    ids.add(f.id); fichiers.add(f.fichier);
    // t146 : la version anglaise (titre_en, phrase_en, fichier_en — capture refaite sur l'interface anglaise) passe le
    // même contrôle ; une fiche qui en porte une partie seulement est refusée
    const en = ["titre_en", "phrase_en", "fichier_en"].filter((k) => f[k]);
    if (en.length && en.length !== 3) e.push(`${f.id} : version anglaise incomplète (${en.join(", ")})`);
    if (en.length === 3 && valider_fiche({ ...f, titre: f.titre_en, phrase: f.phrase_en, fichier: f.fichier_en }).length)
      e.push(`${f.id} : version anglaise invalide`);
    const anims = en.length === 3 ? [f.fichier, f.fichier_en] : [f.fichier];
    let absent = false;
    for (const fic of anims) {
      fichiers.add(fic);
      const p = join(dossier, fic);
      if (!existsSync(p)) { e.push(`${f.id} : ${fic} absent`); absent = true; continue; }
      const a = animation_lire(readFileSync(p));
      if (!a) e.push(`${f.id} : ${fic} n'est ni un WebP ni une APNG`);
      else if (a.w !== 320 || a.h !== 200 || a.images !== 3) e.push(`${f.id} : ${a.w}×${a.h}, ${a.images} image(s) — 320×200 à trois temps attendu`);
    }
    if (absent) continue;
    const re = new RegExp(`(id="${f.id}"|["'\`#]${f.id}["'\`])`);
    if (!sources.some((s) => re.test(s))) e.push(`${f.id} : aucun élément de ce nom dans la page (fiche orpheline)`);
  }
  for (const n of readdirSync(dossier)) if (/\.(webp|png)$/i.test(n) && !fichiers.has(n)) e.push(`${n} : animation sans fiche`);
  const tri = index.map((f) => f.id);
  if (tri.join() !== [...tri].sort((a, b) => a.localeCompare(b)).join()) e.push("index.json : fiches non triées par id");
  return e;
}
