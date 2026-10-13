// t200 (Espaces de marque E0) : tire la liste Quick ACTUELLE (prompts.jsx + VIBES de screens.jsx) en JSON,
// pour que l'espace « deepotus » migre a l'identique. Usage : node scripts/espaces/extraire_contenus_deepotus.mjs [--check]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RACINE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const lire = (p) => fs.readFileSync(path.join(RACINE, p), 'utf8');

function litteral(src, debut, fin) {
  const i = src.indexOf(debut);
  if (i < 0) throw new Error(`borne absente : ${debut}`);
  const j = src.indexOf(fin, i);
  if (j < 0) throw new Error(`fin absente apres : ${debut}`);
  const corps = src.slice(i + debut.length, j + fin.length - 1);
  return Function(`"use strict"; return (${corps});`)();
}

export function extraire() {
  const pr = lire('frontend/src/studio/prompts.jsx');
  const sc = lire('frontend/src/studio/screens.jsx');
  return {
    version: 1,
    prompt_templates: litteral(pr, 'const PROMPT_TEMPLATES = ', '\n];'),
    prompt_cats: litteral(pr, 'const PROMPT_CATS = ', '\n];'),
    ingredients: litteral(pr, 'const ING = ', '\n};'),
    vibes: litteral(sc, 'const VIBES = ', '\n  ];'),
  };
}

const CIBLE = path.join(RACINE, 'backend', 'app', 'espaces', 'deepotus_contenus.json');
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const texte = JSON.stringify(extraire(), null, 2) + '\n';
  if (process.argv.includes('--check')) {
    const ok = fs.existsSync(CIBLE) && fs.readFileSync(CIBLE, 'utf8') === texte;
    console.log(ok ? 'a jour' : 'PERIME : relancer sans --check');
    process.exit(ok ? 0 : 1);
  }
  fs.writeFileSync(CIBLE, texte, 'utf8');
  console.log(`ecrit ${path.relative(RACINE, CIBLE)}`);
}
