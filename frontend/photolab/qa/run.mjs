// qa/run.mjs — lance tous les *.test.mjs du dossier. Un échec = exit 1.
// Chaque test est auto-exécutant (il sort en 1 lui-même sur échec).
// t253 : AVANT de lancer, chaque import relatif des bancs (qa/*.mjs, qa/outils/*.mjs) doit exister — dans l'arbre
// installé, un fichier d'aide jamais copié (qa/outils/suite-icones.mjs, relevé en t252) faisait planter un banc sur
// ERR_MODULE_NOT_FOUND sans dire qu'il s'agissait d'une installation incomplète.
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ici = dirname(fileURLToPath(import.meta.url));

export function importsManquants(dossier) {
  const manquants = [];
  const fichiers = [...readdirSync(dossier).filter((n) => n.endsWith(".mjs")).map((n) => join(dossier, n)),
    ...(existsSync(join(dossier, "outils")) ? readdirSync(join(dossier, "outils")).filter((n) => n.endsWith(".mjs")).map((n) => join(dossier, "outils", n)) : [])];
  for (const f of fichiers) {
    const src = readFileSync(f, "utf8");
    for (const m of src.matchAll(/(?:import|from)\s*\(?\s*["'](\.{1,2}\/[^"'?]+)(?:\?[^"']*)?["']/g)) {
      const cible = resolve(dirname(f), m[1]);
      if (!existsSync(cible)) manquants.push(relative(dossier, f) + " -> " + m[1]);
    }
  }
  return manquants;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const manquants = importsManquants(ici);
  if (manquants.length) {
    console.error("QA photolab : fichier(s) importé(s) ABSENT(S) — installation incomplète ?\n  " + manquants.join("\n  "));
    process.exit(1);
  }
  for (const f of readdirSync(ici).filter((n) => n.endsWith(".test.mjs")).sort()) {
    await import(pathToFileURL(join(ici, f)));
  }
  console.log("QA photolab : tous les bancs sont passes.");
}
