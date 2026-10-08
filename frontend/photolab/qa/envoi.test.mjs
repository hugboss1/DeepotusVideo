// qa/envoi.test.mjs — t139 (P4) : le contrat d'envoi entre écrans (shared/dz-envoi.js), l'entrée « Envoyer vers… » du
// menu Fichier, le nom affiché d'un document rouvert depuis la Bibliothèque.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { lireEnvoi, porteurDe, sansImg, nomValide, DUREE_MS } from "../../shared/dz-envoi.js";
import { construireMenus, REFUSES, TRAITES_PAR_ECRAN, NECESSITE_DOC, actionEntree } from "../js/mod-menus.js";
import { nomDocument } from "../js/mod-fichier.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));

// 1. lireEnvoi : l'URL d'abord, puis l'envoi de la fenêtre de l'application, consommé une fois
const T0 = 1_800_000_000_000;
const envoi = (cible, image, t = T0) => ({ __dzEnvoiImg: { cible, image, t } });
check("1.1 ?img= ouvre l'image (via url)", JSON.stringify(lireEnvoi("?img=herbe.png", null, "photolab", T0)) === '{"image":"herbe.png","via":"url"}');
check("1.2 ?img= passe avant un envoi, et ne le consomme pas", (() => {
  const p = envoi("photolab", "autre.png"); const r = lireEnvoi("?img=herbe.png", p, "photolab", T0);
  return r.image === "herbe.png" && p.__dzEnvoiImg && p.__dzEnvoiImg.image === "autre.png";
})());
let p = envoi("photolab", "rouge.png", T0 - 5000);
const r1 = lireEnvoi("", p, "photolab", T0);
check("1.3 envoi frais pour cet écran : ouvert (via envoi) puis CONSOMMÉ", r1 && r1.image === "rouge.png" && r1.via === "envoi" && !("__dzEnvoiImg" in p), r1);
check("1.4 une seconde lecture ne rouvre rien", lireEnvoi("", p, "photolab", T0) === null);
p = envoi("vectorlab", "rouge.png");
check("1.5 envoi pour un AUTRE écran : ignoré et laissé intact", lireEnvoi("", p, "photolab", T0) === null && p.__dzEnvoiImg.cible === "vectorlab");
p = envoi("photolab", "rouge.png", T0 - DUREE_MS - 1);
check("1.6 envoi périmé (> 120 s) : rien, mais consommé", lireEnvoi("", p, "photolab", T0) === null && !("__dzEnvoiImg" in p));
p = envoi("photolab", "rouge.png", T0 + 60000);
check("1.7 horodatage dans le futur : refusé", lireEnvoi("", p, "photolab", T0) === null);
check("1.8 envoi à la limite (120 s pile) : accepté", lireEnvoi("", envoi("photolab", "a.png", T0 - DUREE_MS), "photolab", T0) !== null);
for (const mauvais of ["../t.db", "a/b.png", "a\\b.png", "", ".cache", 12, null])
  check("1.9 nom refusé " + JSON.stringify(mauvais), lireEnvoi("", envoi("photolab", mauvais), "photolab", T0) === null
    && (typeof mauvais !== "string" || lireEnvoi("?img=" + encodeURIComponent(mauvais), null, "photolab", T0) === null));
check("1.10 sans porteur ni URL : null", lireEnvoi("", null, "photolab", T0) === null && lireEnvoi(undefined, undefined, "photolab", T0) === null);
check("1.11 nomValide accepte les noms de la Bibliothèque", nomValide("photolab_20261008-154030_herbe.png") && nomValide("Mon image 2.jpg"));

// 2. porteurDe : la fenêtre de l'application, null si elle est d'une autre origine
check("2.1 top accessible -> top", (() => { const top = {}; return porteurDe({ top }) === top; })());
check("2.2 top d'une autre origine (lecture qui lève) -> null", porteurDe({ top: new Proxy({}, { get() { throw new Error("SecurityError"); } }) }) === null);
check("2.3 pas de fenêtre -> null", porteurDe(null) === null);

// 3. sansImg : l'URL nettoyée (recharger ne rouvre pas)
check("3.1 img retiré, le reste gardé", sansImg("http://h/photolab/?img=a.png&x=1#z") === "/photolab/?x=1#z", sansImg("http://h/photolab/?img=a.png&x=1#z"));
check("3.2 seul paramètre : plus de ?", sansImg("http://h/photolab/?img=a.png") === "/photolab/");

// 4. menu Fichier : « Envoyer vers… » après « Revenir à la version enregistrée », traité par l'écran, document requis
const catalogue = JSON.parse(readFileSync(join(racine, "donnees/menus.json"), "utf8"));
const t = (c) => (dico[c] ? dico[c].fr : c);
const tEn = (c) => (dico[c] ? dico[c].en : c);
const fichier = construireMenus(catalogue, [], REFUSES, "fr", t)[0].entrees;
const fichierEn = construireMenus(catalogue, [], REFUSES, "en", tEn)[0].entrees;
const i = fichier.findIndex((e) => e.id === "pl.envoyer"), iRev = fichier.findIndex((e) => e.id === "file.revert");
check("4.1 l'entrée existe juste après « Revenir »", i > 0 && i === iRev + 1, [iRev, i]);
check("4.2 libellés fr / en", fichier[i] && fichier[i].libelle === "Envoyer vers…" && fichierEn[i] && fichierEn[i].libelle === "Send to…",
  fichier[i] && [fichier[i].libelle, fichierEn[i].libelle]);
check("4.3 traitée par l'écran, document requis", TRAITES_PAR_ECRAN.has("pl.envoyer") && NECESSITE_DOC.has("pl.envoyer")
  && fichier[i].etat === "actif" && actionEntree(fichier[i]) === "ecran");
check("4.4 une seule fois dans le menu", fichier.filter((e) => e.id === "pl.envoyer").length === 1);
// t140 : les deux entrées du repli natif (pl.natif.*) s'intercalent, le groupe se clôt toujours par le séparateur
const fin = fichier.findIndex((e, k) => k > i && !String(e.id || "").startsWith("pl."));
check("4.5 le groupe (Envoyer vers…, repli natif) est suivi du séparateur qui précède Exporter", fin > i && fichier[fin].type === "separateur",
  fichier.slice(i, fin + 1).map((e) => e.id || e.type));

// 5. nom affiché : empreinte, extension, préfixe d'enregistrement et suffixe du fichier de travail retirés
check("5.1 image enregistrée par le Photolab", nomDocument("e99baeb8-photolab_20261008-154030_herbe.png") === "herbe");
check("5.2 fichier de travail rouvert", nomDocument("e99baeb8-photolab_20261008-154030_herbe-png.pcraft") === "herbe");
check("5.3 suffixe -jpg aussi", nomDocument("photolab_20261008-154030_ciel-jpg") === "ciel");
check("5.4 un nom ordinaire qui finit par -png reste intact", nomDocument("logo-png.png") === "logo-png");
check("5.5 sans préfixe : inchangé (6.x de fichier.test)", nomDocument("e99baeb8-herbe.png") === "herbe");

// 6. textes au dictionnaire
for (const cle of ["photolab.menu.envoyer", "photolab.envoi.hors_app", "photolab.envoi.calques", "photolab.envoi.recu"])
  check("6.1 " + cle + " fr et en", dico[cle] && dico[cle].fr && dico[cle].en, cle);

console.log(`envoi : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
