// envoi_noms.test.mjs — t421 (cartes hexagonales, tâche 1) : le contrat « Envoyer vers » accepte les noms accentués
// (53 des 93 cartes réelles) et DIT son refus au lieu d'ouvrir une page vide en silence.
// Lancer : node frontend/shared/qa/envoi_noms.test.mjs
import { nomValide, lireEnvoi, recevoir } from "../dz-envoi.js";

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const T0 = 1_800_000_000_000;
const NFC = "adrian_veilleur_des_âmes_fracturées.png";
const NFD = NFC.normalize("NFD");
const envoi = (cible, image, t = T0) => ({ __dzEnvoiImg: { cible, image, t } });

ok("1.1 les deux formes sont distinctes", NFC !== NFD);
ok("1.2 nomValide accepte la forme NFC", nomValide(NFC));
ok("1.3 nomValide accepte la forme NFD", nomValide(NFD));
ok("1.4 nomValide accepte espace, tiret, chiffre", nomValide("Âme d été 2-3.jpg"));
/* t421 (vague finale) : la règle est celle de backend/app/services/noms.py — seul le dangereux est refusé. Les noms
   COURANTS d'un import (gardés tels quels par /images/upload) passent ; String.raw pour un VRAI antislash. */
const COURANTS = ["carte (1).png", "d'été.png", "âmes fracturées.png", "âmes fracturées.png".normalize("NFD"),
  "a+b.png", "carte #3.png", "-a.png", ".cache", "x".repeat(176) + ".png", "🂡 as.png"];
for (const bon of COURANTS) ok("1.5a nomValide accepte " + JSON.stringify(bon.slice(0, 30)), nomValide(bon));
for (const mauvais of ["a/b.png", String.raw`a\b.png`, "..", ".", "x\n.png", "a\u007fb.png", "a\u0085b.png", "a:b.png",
  "a<b.png", "a>b.png", 'a"b.png', "a|b.png", "a?b.png", "a*b.png", "fin.", "fin ", "", "x".repeat(177) + ".png",
  "🂡".repeat(181), 12, null])
  ok("1.5 nomValide refuse " + JSON.stringify(typeof mauvais === "string" ? mauvais.slice(0, 30) : mauvais), !nomValide(mauvais));
ok("1.6 lireEnvoi ouvre « carte (1).png » (via envoi)",
  JSON.stringify(lireEnvoi("", envoi("photolab", "carte (1).png"), "photolab", T0)) === JSON.stringify({ image: "carte (1).png", via: "envoi" }));
ok("1.7 lireEnvoi ouvre ?img=d'été.png (via url)",
  JSON.stringify(lireEnvoi("?img=" + encodeURIComponent("d'été.png"), null, "photolab", T0)) === JSON.stringify({ image: "d'été.png", via: "url" }));

const p1 = envoi("photolab", NFC);
ok("2.1 envoi accentué : ouvert (via envoi)", JSON.stringify(lireEnvoi("", p1, "photolab", T0)) === JSON.stringify({ image: NFC, via: "envoi" }));
ok("2.2 ?img= accentué : ouvert (via url)", JSON.stringify(lireEnvoi("?img=" + encodeURIComponent(NFD), null, "photolab", T0)) === JSON.stringify({ image: NFD, via: "url" }));

const p2 = envoi("photolab", "a/b.png");
ok("3.1 envoi {cible:photolab, image:'a/b.png'} -> {refus:'a/b.png'}", JSON.stringify(lireEnvoi("", p2, "photolab", T0)) === '{"refus":"a/b.png"}');
ok("3.2 l'envoi refusé est consommé", !("__dzEnvoiImg" in p2));
const p3 = envoi("vectorlab", "a/b.png");
ok("3.3 envoi refusé pour un AUTRE écran : null et laissé intact", lireEnvoi("", p3, "photolab", T0) === null && p3.__dzEnvoiImg.cible === "vectorlab");
ok("3.4 envoi périmé au nom invalide : null (rien à dire d'un envoi caduc)", lireEnvoi("", envoi("photolab", "a/b.png", T0 - 999999), "photolab", T0) === null);
ok("3.5 nom non texte : null", lireEnvoi("", envoi("photolab", 12), "photolab", T0) === null && lireEnvoi("", envoi("photolab", ""), "photolab", T0) === null);
ok("3.6 ?img= invalide : {refus}", JSON.stringify(lireEnvoi("?img=" + encodeURIComponent("../t.db"), null, "photolab", T0)) === '{"refus":"../t.db"}');
ok("3.7 ?img= vide : null", lireEnvoi("?img=", null, "photolab", T0) === null);
ok("3.8 rien du tout : null", lireEnvoi("", null, "photolab", T0) === null);

// recevoir (navigateur simulé) : le refus traverse, l'URL n'est pas nettoyée pour un refus
const fen = { location: { search: "?img=" + encodeURIComponent("a/b.png"), href: "http://x/photolab/?img=a%2Fb.png" }, history: { state: null, replaceState() { fen.nettoye = true; } }, top: {} };
fen.top = fen;
ok("4.1 recevoir rend {refus} pour un ?img= invalide", JSON.stringify(recevoir("photolab", fen)) === '{"refus":"a/b.png"}');

if (echecs.length) { console.error("envoi_noms : " + echecs.length + " échec(s) sur " + n + "\n  " + echecs.join("\n  ")); process.exit(1); }
console.log("envoi_noms : " + n + " vérifications ok");
