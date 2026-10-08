// qa/dialogue.test.mjs — dialogue générique de réglage avec aperçu moteur (t138 B2) : fonctions PURES de
// mod-dialogue-reglage.js. Familles qui ont un aperçu (copie de la liste du pont), « la plus récente gagne » (une seule
// requête d'aperçu en vol), placement de la boîte, valeurs bornées par le moteur reportées dans le formulaire.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { estFamilleApercu, FILTRES_HORS_APERCU, REGLAGES_HORS_APERCU, derniereGagne, positionInitiale, bornerPosition,
  valeursAppliquees, valeursInitiales, uniteAffichee, libelleOption, titreDialogue, DELAI_APERCU, curseurPuissance, versCurseur,
  depuisCurseur, CRANS_CURSEUR, identiteDocument } from "../js/mod-dialogue-reglage.js";

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const json = (x) => JSON.stringify(x);
const differe = () => { let a, b; const p = new Promise((x, y) => { a = x; b = y; }); return { p, ok: a, ko: b }; };
const tick = () => new Promise((r) => setTimeout(r, 0));
const racine = join(dirname(fileURLToPath(import.meta.url)), "..");

// 1. familles avec aperçu : filter.* et image.adjustments.*, moins les exclusions du pont
check("1.1 Flou gaussien", estFamilleApercu("filter.blur.gaussianBlur") === true);
check("1.2 Luminosité/Contraste destructif", estFamilleApercu("image.adjustments.brightnessContrast") === true);
check("1.3 Fluidité (D9) exclue", estFamilleApercu("filter.liquify") === false);
check("1.4 Galerie de filtres exclue", estFamilleApercu("filter.filterGallery") === false);
check("1.5 Dernier filtre exclu", estFamilleApercu("filter.lastFilter") === false);
check("1.6 liste des LUT exclue", estFamilleApercu("image.adjustments.colorLookup.list") === false);
check("1.7 autres familles : pas d'aperçu générique",
  !estFamilleApercu("edit.fill") && !estFamilleApercu("layer.layerStyle.dropShadow") && !estFamilleApercu("filter")
  && !estFamilleApercu("image.adjustmentsX") && !estFamilleApercu(null) && !estFamilleApercu(42));
{
  // Copie du pont : une dérive entre photolab_moteur.py et l'écran rougit (l'écran proposerait un aperçu refusé en 400).
  const py = readFileSync(join(racine, "../../backend/app/services/photolab_moteur.py"), "utf8");
  const lire = (nom) => {
    const m = py.match(new RegExp(nom + "\\s*=\\s*frozenset\\(\\{([\\s\\S]*?)\\}\\)"));
    return m ? [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]).sort() : null;
  };
  check("1.8 FILTRES_HORS_APERCU == pont", json([...FILTRES_HORS_APERCU].sort()) === json(lire("FILTRES_HORS_APERCU")), lire("FILTRES_HORS_APERCU"));
  check("1.9 REGLAGES_HORS_APERCU == pont", json([...REGLAGES_HORS_APERCU].sort()) === json(lire("REGLAGES_HORS_APERCU")), lire("REGLAGES_HORS_APERCU"));
}
check("1.10 délai d'aperçu 250 ms", DELAI_APERCU === 250);

// 2. derniereGagne : une seule requête en vol, la plus récente gagne
{
  const appels = [], attentes = [];
  let enVol = 0, maxEnVol = 0;
  const demander = derniereGagne((x) => {
    appels.push(x); enVol++; maxEnVol = Math.max(maxEnVol, enVol);
    const d = differe(); attentes.push(d);
    return d.p.finally(() => { enVol--; });
  });
  const r1 = demander("a");
  check("2.1 la première demande part tout de suite", json(appels) === json(["a"]));
  check("2.2 enVol() vrai pendant le vol", demander.enVol() === true);
  const r2 = demander("b"), r3 = demander("c");
  check("2.3 rien d'autre ne part tant que la première vole", appels.length === 1);
  check("2.4 la demande remplacée est périmée sans être lancée", json(await r2) === json({ perime: true }));
  attentes[0].ok("A");
  check("2.5 la première, dépassée, revient périmée", json(await r1) === json({ perime: true }));
  await tick();
  check("2.6 seule la plus récente part ensuite", json(appels) === json(["a", "c"]), appels);
  attentes[1].ok("C");
  check("2.7 la plus récente rend sa valeur", json(await r3) === json({ perime: false, valeur: "C" }));
  check("2.8 jamais deux en vol", maxEnVol === 1, maxEnVol);
  await tick();
  check("2.9 file vide", demander.enVol() === false);

  // annuler : le résultat en vol est jeté, la demande en attente aussi
  const r4 = demander("d");
  const r5 = demander("e");
  demander.annuler();
  check("2.10 annuler : l'attente est périmée", json(await r5) === json({ perime: true }));
  attentes[2].ok("D");
  check("2.11 annuler : le vol en cours revient périmé", json(await r4) === json({ perime: true }));
  await tick();
  check("2.12 annuler : l'attente n'est jamais lancée", json(appels) === json(["a", "c", "d"]), appels);

  // une erreur revient à l'appelant (affichée dans le dialogue), sans bloquer la suivante
  const r6 = demander("f");
  attentes[3].ko(new Error("422"));
  const v6 = await r6;
  check("2.13 erreur rendue, non périmée", v6.perime === false && v6.erreur instanceof Error && v6.erreur.message === "422");
  await tick();
  const r7 = demander("g");
  attentes[4].ok("G");
  check("2.14 après une erreur, la suivante passe", json(await r7) === json({ perime: false, valeur: "G" }));

  // une tâche qui lève de façon synchrone est rendue comme une erreur
  const lance = derniereGagne(() => { throw new Error("sync"); });
  const v8 = await lance(1);
  check("2.15 exception synchrone -> erreur", v8.perime === false && v8.erreur && v8.erreur.message === "sync");
  // enVol() suffit aux dialogues (indicateur « occupé ») ; attendre() ne servait qu'aux bancs : retiré.
  check("2.16 enVol() faux quand rien ne vole ; plus d'attendre()", demander.enVol() === false && !("attendre" in demander));
  const r9 = demander("h");
  check("2.17 enVol() vrai tant qu'une requête vole", demander.enVol() === true);
  attentes[5].ok("H");
  await r9; await tick();
  check("2.18 enVol() faux après le vol", demander.enVol() === false);
}

// 3. position initiale : en haut à droite de #scene, marge 12 ; jamais à gauche de la scène
{
  const scene = { left: 100, top: 60, width: 800, height: 600 };
  check("3.1 haut droite", json(positionInitiale(scene, { w: 320, h: 200 })) === json({ x: 568, y: 72 }));
  check("3.2 scène étroite : collée au bord gauche de la scène", json(positionInitiale({ left: 100, top: 60, width: 200, height: 600 }, { w: 320, h: 200 })) === json({ x: 112, y: 72 }));
  check("3.3 marge donnée", json(positionInitiale(scene, { w: 320, h: 200 }, 0)) === json({ x: 580, y: 60 }));
  check("3.4 scène absente : coin de la fenêtre", json(positionInitiale(null, { w: 320, h: 200 })) === json({ x: 12, y: 12 }));
}

// 4. déplacement : la boîte reste dans la fenêtre
{
  const f = { w: 1000, h: 700 }, b = { w: 320, h: 200 };
  check("4.1 dedans : inchangé", json(bornerPosition(300, 200, b, f)) === json({ x: 300, y: 200 }));
  check("4.2 trop à gauche / en haut", json(bornerPosition(-50, -10, b, f)) === json({ x: 0, y: 0 }));
  check("4.3 trop à droite / en bas", json(bornerPosition(900, 650, b, f)) === json({ x: 680, y: 500 }));
  check("4.4 boîte plus grande que la fenêtre : coin haut gauche", json(bornerPosition(50, 50, { w: 1200, h: 900 }, f)) === json({ x: 0, y: 0 }));
}

// 5. valeurs bornées par le moteur (resultats[0].filter) reportées dans le formulaire
{
  const champs = [
    { cle: "radius", type: "number", min: 0.1, max: 1000, defaut: 1, optionnel: false },
    { cle: "layer", type: "layerId", optionnel: true },
    { cle: "distribution", type: "enum", valeurs: ["uniform", "gaussian"], optionnel: false },
  ];
  const envoyes = { radius: 12.4, distribution: "uniform" };
  check("5.1 valeur bornée par le moteur -> reportée", json(valeursAppliquees(champs, envoyes, { ...envoyes }, { radius: 12 })) === json({ radius: 12 }));
  check("5.2 valeur identique -> rien", json(valeursAppliquees(champs, envoyes, { ...envoyes }, { radius: 12.4, distribution: "uniform" })) === json({}));
  check("5.3 l'utilisateur a changé la valeur depuis l'envoi -> on ne l'écrase pas",
    json(valeursAppliquees(champs, envoyes, { radius: 30, distribution: "uniform" }, { radius: 12 })) === json({}));
  check("5.4 clé cachée ou inconnue ignorée", json(valeursAppliquees(champs, envoyes, { ...envoyes }, { layer: 3, zorg: 1 })) === json({}));
  check("5.5 pas de filtre -> rien", json(valeursAppliquees(champs, envoyes, envoyes, null)) === json({}) && json(valeursAppliquees(champs, envoyes, envoyes, "x")) === json({}));
  check("5.6 valeur du moteur coercée (texte -> nombre)", json(valeursAppliquees(champs, envoyes, { ...envoyes }, { radius: "7" })) === json({ radius: 7 }));
}

// 6. valeurs initiales : deux passes (les bornes de la colorisation dépendent de la case)
{
  const champs = [
    { cle: "hue", type: "number", min: -180, max: 180, defaut: -20, optionnel: false },
    { cle: "saturation", type: "number", min: -100, max: 100, defaut: 25, optionnel: false },
    { cle: "colorize", type: "bool", defaut: true, optionnel: false },
    { cle: "layer", type: "layerId", optionnel: true },
    { cle: "points", type: "json", optionnel: false },
  ];
  const v = valeursInitiales(champs);
  check("6.1 colorisation : teinte ramenée dans 0..360", v.hue === 0, v);
  check("6.2 saturation dans 0..100", v.saturation === 25, v);
  check("6.3 case au défaut", v.colorize === true);
  check("6.4 seulement les champs visibles", json(Object.keys(v).sort()) === json(["colorize", "hue", "saturation"]), Object.keys(v));
  const sans = valeursInitiales(champs.map((c) => (c.cle === "colorize" ? { ...c, defaut: false } : c)));
  check("6.5 sans colorisation : défaut tel quel", sans.hue === -20);
  check("6.6 champs absents", json(valeursInitiales(null)) === json({}));
}

// 7. unités, libellés d'options, titre
check("7.1 unités", uniteAffichee("deg") === "°" && uniteAffichee("px") === "px" && uniteAffichee("%") === "%"
  && uniteAffichee("ev") === "EV" && uniteAffichee(undefined) === "" && uniteAffichee("mm") === "mm");
{
  const dico = JSON.parse(readFileSync(join(racine, "../shared/i18n/photolab.json"), "utf8"));
  const t = (k) => (dico[k] ? dico[k].fr : k);
  check("7.2 mode de fusion : clé photolab.fusion.* (pas photolab.valeur.*)", libelleOption({ cle: "blend", type: "str" }, "colorBurn", t) === "Densité couleur +");
  check("7.3 valeur d'énumération sans entrée : humanisée", libelleOption({ cle: "distribution", type: "enum" }, "sansEntree", t) === "Sans entree");
  check("7.4 valeur numérique telle quelle", libelleOption({ cle: "n", type: "enum" }, 4, t) === "4");
  check("7.5 mode inconnu : humanisé", libelleOption({ cle: "blend", type: "str" }, "zorg", t) === "Zorg");
}
check("7.6 titre sans points de suspension", titreDialogue("Flou gaussien…") === "Flou gaussien" && titreDialogue("Add Noise...") === "Add Noise"
  && titreDialogue("Inverser") === "Inverser" && titreDialogue(null) === "");

// 9. curseur non linéaire (puissance 3 sur 1000 crans) pour les grandes étendues ; linéaire sinon
{
  const rayon = { cle: "radius", type: "number", min: 0.1, max: 1000, defaut: 1, optionnel: false };
  const distance = { cle: "distance", type: "number", min: 1, max: 2000, entier: true, defaut: 10, optionnel: false };
  const opacite = { cle: "opacity", type: "number", min: 0, max: 100, defaut: 75, optionnel: false };
  const echelle = { cle: "scale", type: "number", min: 10, max: 150, defaut: 100, optionnel: false };
  check("9.1 rayon 0.1..1000 : puissance", curseurPuissance(rayon) === true && curseurPuissance(distance) === true);
  check("9.2 0..100 et 10..150 : linéaire", curseurPuissance(opacite) === false && curseurPuissance(echelle) === false);
  check("9.3 non borné ou autre contrôle : linéaire", curseurPuissance({ cle: "angle", type: "number", unite: "deg" }) === false
    && curseurPuissance({ cle: "n", type: "int", min: 1, max: 1000 }) === false && curseurPuissance(null) === false);
  check("9.4 bornes : min -> 0, max -> 1000", versCurseur(rayon, 0.1) === 0 && versCurseur(rayon, 1000) === CRANS_CURSEUR);
  check("9.5 bornes : 0 -> min, 1000 -> max", depuisCurseur(rayon, 0) === 0.1 && depuisCurseur(rayon, CRANS_CURSEUR) === 1000
    && depuisCurseur(distance, 0) === 1 && depuisCurseur(distance, CRANS_CURSEUR) === 2000);
  check("9.6 hors course : bornée", depuisCurseur(rayon, -50) === 0.1 && depuisCurseur(rayon, 5000) === 1000 && versCurseur(rayon, 99999) === CRANS_CURSEUR);
  check("9.7 les petites valeurs occupent l'essentiel de la course", versCurseur(rayon, 10) > 200 && versCurseur(rayon, 125) >= 490, [versCurseur(rayon, 10), versCurseur(rayon, 125)]);
  let mono = true, prec = -Infinity, allerRetour = true;
  for (let p = 0; p <= CRANS_CURSEUR; p++) {
    const v = depuisCurseur(rayon, p);
    if (v < prec) mono = false;
    prec = v;
    if (Math.abs(versCurseur(rayon, v) - p) > 1 && v > 1) allerRetour = false;   // sous 1 px, le pas de 0,1 regroupe des crans
  }
  check("9.8 monotone sur toute la course", mono);
  check("9.9 aller-retour position -> valeur -> position à un cran près", allerRetour);
  check("9.10 valeur arrondie au pas (0,1 ; entier pour la distance)", depuisCurseur(rayon, 500) === 125.1 && Number.isInteger(depuisCurseur(distance, 333))
    && [1, 37, 412, 999].every((p) => Math.abs(depuisCurseur(rayon, p) * 10 - Math.round(depuisCurseur(rayon, p) * 10)) < 1e-9));
  check("9.11 aller-retour valeur -> position -> valeur proche", [1, 5, 12.5, 250, 800].every((v) => Math.abs(depuisCurseur(rayon, versCurseur(rayon, v)) - v) / v < 0.02));
  check("9.12 linéaire : la position EST la valeur", versCurseur(opacite, 40) === 40 && depuisCurseur(opacite, "40") === 40 && depuisCurseur(opacite, 500) === 100);
  check("9.13 valeur illisible -> position 0", versCurseur(rayon, "zorg") === 0);
}

// 10. identité du document visé (un autre document actif ferme le dialogue)
check("10.1 identité : nom, index, génération", identiteDocument({ name: "a", index: 1 }, 3) === "a|1|3"
  && identiteDocument({ name: "a" }, 3) !== identiteDocument({ name: "b" }, 3)
  && identiteDocument({ name: "a" }, 3) !== identiteDocument({ name: "a" }, 4) && identiteDocument(null, 3) === null);

// 8. DOM relu statiquement : bornes et pas des curseurs posés par le module, boîte non modale, touches stoppées
{
  const src = readFileSync(join(racine, "js/mod-dialogue-reglage.js"), "utf8");
  check("8.1 pas de voile (non modal)", !/pl-voile/.test(src) && !/aria-modal", "true/.test(src));
  check("8.2 curseur : min, max et step posés", /\.min = /.test(src) && /\.max = /.test(src) && /\.step = /.test(src));
  check("8.3 touches stoppées dans la boîte", /stopPropagation\(\)/.test(src));
  check("8.4 l'aperçu passe par poserApercu", /PL\.vue\.poserApercu\(/.test(src));
  check("8.5 OK par la file FIFO (PL.executer), tout de suite (pas après attendre())", /PL\.executer\(/.test(src) && !/attendre\(\)\.then\(\(\) => PL\.executer/.test(src));
  check("8.5b OK en échec avec aperçu posé : rendu réel relu", /PL\.executer\(id, p\)\.then\(\(r\) => \{ if \(!\(r && r\.ok\) && apercuAEffacer\) PL\.cycle\(\)/.test(src));
  check("8.5c maxSide voulu gardé à la demande", /PL\.vue\.poserApercu\(image, voulu\)/.test(src));
  check("8.5d erreur annoncée (role=alert), boîte nommée par son titre", /setAttribute\("role", "alert"\)/.test(src) && /setAttribute\("aria-labelledby"/.test(src));
  const vue = readFileSync(join(racine, "js/mod-vue.js"), "utf8");
  check("8.6 mod-vue : poserApercu ne touche pas PL.etat.doc", /vue\.poserApercu = function/.test(vue)
    && !/poserApercu[\s\S]{0,400}PL\.etat\.doc\s*=/.test(vue));
  const core = readFileSync(join(racine, "js/core.js"), "utf8");
  check("8.7 core.js initialise le dialogue", /initDialogueReglage\(PL\)/.test(core));
}

console.log(`dialogue : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
