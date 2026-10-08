// qa/zones.test.mjs — squelette du Photolab (B1) : ordre des scripts, zones, jetons, mots interdits.
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
let ok = 0, ko = 0;
function check(label, cond, detail = "") {
  if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); }
}
const lire = (f) => (existsSync(join(racine, f)) ? readFileSync(join(racine, f), "utf8") : "");
const html = lire("index.html");
const css = lire("photolab.css");

// 1. scripts : dico puis runtime AVANT tout autre script, puis plafonds, dialogue, core.js en fin de body
const iDico = html.indexOf('<script src="/shared/dz-i18n-dico.js"></script>');
const iRun = html.indexOf('<script src="/shared/dz-i18n.js"></script>');
const premier = html.search(/<script\b/);
check("1.1 dico en premier script", iDico >= 0 && iDico === premier, iDico);
check("1.2 runtime juste après le dico", iRun > iDico);
const iPlaf = html.indexOf('<script src="/shared/dz-plafonds.js"></script>');
const iDlg = html.indexOf('<script src="/shared/dialogue.js"></script>');
check("1.3 plafonds puis dialogue après le runtime", iRun < iPlaf && iPlaf < iDlg, [iRun, iPlaf, iDlg]);
const iCore = html.indexOf('<script type="module" src="js/core.js"></script>');
check("1.4 core.js en module", iCore > iDlg && iDlg > 0);
check("1.5 core.js dans le body, après les zones", iCore > html.indexOf("<body") && iCore > html.indexOf('id="statut"'));
check("1.6 lang fr et titre", /<html lang="fr">/.test(html) && /<title>Photolab<\/title>/.test(html));

// 2. zones
for (const id of ["menubar", "options", "onglets", "outils", "scene", "toile", "fourmis", "rail", "panneaux",
                  "grpCouleur", "grpProprietes", "grpCalques", "statut", "accueil"]) {
  check("2 zone #" + id, new RegExp('id="' + id + '"').test(html));
}
check("2.1 canvas#toile", /<canvas[^>]*id="toile"/.test(html));
check("2.2 #fourmis est un svg", /<svg[^>]*id="fourmis"/.test(html));
check("2.3 quatre groupes de panneaux (t155 : + Pinceaux)", (html.match(/<section\b/g) || []).length === 4);
check("2.4 rail à 6 boutons (t155 : + Pinceaux)", ((html.match(/id="rail"[\s\S]*?<\/nav>/) || [""])[0].match(/<button\b/g) || []).length === 6);
check("2.5 accueil : boutons Nouveau et Ouvrir", /id="btnNouveau"/.test(html) && /id="btnOuvrir"/.test(html));

// 3. cotes de photocraft (A1)
const cote = (sel, prop, v) => new RegExp(sel.replace(/[#.]/g, "\\$&") + "\\s*\\{[^}]*" + prop + "\\s*:\\s*" + v + "px").test(css);
check("3.1 menu 32", cote("#menubar", "height", 32));
check("3.2 options 36", cote("#options", "height", 36));
check("3.3 onglets 26", cote("#onglets", "height", 26));
check("3.4 outils 68", cote("#outils", "width", 68));
check("3.5 rail 34", cote("#rail", "width", 34));
check("3.6 panneaux 278", cote("#panneaux", "width", 278));
check("3.7 statut 24", cote("#statut", "height", 24));

// 3b. #outils : 68 px = 2 × 32 + gouttière 4 — aucune marge horizontale ni bordure qui rognerait la grille (sinon barre de défilement)
const bloc = (css.match(/#outils\s*\{[^}]*\}/) || [""])[0];
check("3.8 #outils : padding horizontal nul", /padding\s*:\s*\d+px\s+0(px)?\s*;/.test(bloc), bloc);
check("3.9 #outils : pas de border-left/right (trait par box-shadow)", !/border(-left|-right)?\s*:/.test(bloc.replace(/border-radius[^;]*;/g, "")), bloc);
check("3.10 #outils : pas de défilement horizontal", /overflow-x\s*:\s*hidden/.test(bloc), bloc);

// 4. CSS : jetons, aucune couleur en dur
check("4.1 @import des jetons", css.includes('@import url("/shared/deepotus.tokens.css");'));
check("4.2 --cat avec repli", /:root\s*\{\s*--cat\s*:\s*var\(--cat-photo/.test(css));
const sansCommentaires = css.replace(/\/\*[\s\S]*?\*\//g, "");
const enDur = sansCommentaires.match(/#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(/g) || [];
check("4.3 aucune couleur en dur hors var(--…)", enDur.length === 0, enDur.slice(0, 5));
const nomsColeur = sansCommentaires.match(/:\s*(white|black|red|green|blue|gray|grey|yellow|orange)\b/g) || [];
check("4.4 aucun nom de couleur CSS", nomsColeur.length === 0, nomsColeur);
check("4.5 polices par jetons", css.includes("var(--f-ui") && css.includes("var(--f-mono"));

// 5. mots interdits (D8)
for (const [nom, t] of [["index.html", html], ["photolab.css", css], ["core.js", lire("js/core.js")], ["mod-api.js", lire("js/mod-api.js")]]) {
  check("5 " + nom + " sans ArtCraft/Discord/Photoshop", !/artcraft|discord|photoshop/i.test(t));
}

// 6. fichiers d'icônes et attribution
for (const f of ["icones/LICENSE-lucide.txt", "ATTRIBUTION.md", "icones/move.svg", "icones/layers.svg", "js/core.js", "js/mod-api.js"]) {
  check("6 fichier " + f, existsSync(join(racine, f)));
}

console.log(`zones : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
