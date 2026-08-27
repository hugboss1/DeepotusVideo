// qa/run.mjs — lance tous les *.test.mjs du dossier. Un échec = exit 1.
// Chaque test est auto-exécutant (il sort en 1 lui-même sur échec).
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ici = dirname(fileURLToPath(import.meta.url));
for (const f of readdirSync(ici).filter((n) => n.endsWith(".test.mjs")).sort()) {
  await import(pathToFileURL(join(ici, f)));
}
console.log("QA vectorlab : tous les bancs sont passes.");
