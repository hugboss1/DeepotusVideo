// mod-champs.js — champs du registre du moteur -> modèle de formulaire (t138 B1). Tout est PUR (qa/champs.test.mjs).
// Un champ arrive de GET /api/photolab/commandes tel que photolab_registre.structurer l'a lu :
// {cle, type, optionnel, defaut?, min?, max?, entier?, unite?, valeurs?, ouverte?, formes?, note?}.
// Les valeurs envoyées doivent passer la liste blanche du pont (photolab_registre.verifier) : bornes, types, couleur
// #rrggbb, chaînes de 256 caractères au plus. La coercition ci-dessous vise exactement ces règles, pour qu'un formulaire
// rempli n'importe comment produise quand même une commande admise.

// Les 27 modes de fusion du panneau Calques (import sans DOM : mod-calques n'exécute rien au chargement). passThrough
// (MODE_TRANSFERT) est exclu : réservé aux groupes, et un dialogue de style ou de remplissage ne vise jamais un groupe.
import { MODES_FUSION, idFusion } from "./mod-calques.js";

export const VALEURS_FUSION = MODES_FUSION.map((m) => m.id);
// Clé dont le pont exige un mode de fusion connu, QUEL QUE SOIT le type écrit au registre (str des styles, énumération
// ouverte « Multiply|… » de layer.setProps) : `blend: ""` ou `"zorg"` serait refusé.
const estFusion = (c) => c && String(c.cle).toLowerCase() === "blend";

// Colorisation de Teinte/Saturation : le registre ne donne que les bornes hors colorisation (hue -180..180, saturation
// -100..100) ; en colorisation le moteur prend teinte 0..360 et saturation 0..100. Copie de BORNES_COLORIZE du pont.
export const BORNES_COLORIZE = { hue: [0, 360], saturation: [0, 100] };

// Clés que l'écran ne montre jamais : elles désignent la cible ou une variante d'appel, pas un réglage.
export const CLES_CACHEES = new Set(["layer", "add", "enabled", "list", "wait"]);
// Copie de CLES_CHEMIN du pont (comparées en minuscules) : une clé « fichier » est refusée par le pont quel que soit son
// type ; la montrer en champ texte promettrait un réglage voué au refus. Un banc relit le source Python.
export const CLES_FICHIER = new Set(["path", "file", "mappath", "dir", "directory", "folder", "input", "output", "droplet", "script", "data"]);
// D9 : interfaces lourdes écartées au départ (grisées « bientôt »). Les deux Déformation de la marionnette (Édition et
// Objets dynamiques) y sont : leurs épingles se posent à la souris sur l'image, pas dans un formulaire.
export const D9 = new Set(["filter.cameraRaw", "filter.liquify", "filter.vanishingPoint", "filter.adaptiveWideAngle", "layer.smartObjects.puppetWarp",
  "edit.puppetWarp"]);
// Commandes sans éditeur, nommées UNE À UNE parce que le registre ne permet pas de les reconnaître :
// - filter.other.custom (Personnalisé) : `kernel` (int[25]) est requis mais opaque, le formulaire générique ne montrerait
//   que scale et offset et le moteur appliquerait un noyau que l'utilisateur n'a jamais vu.
// t157 : filter.convertForSmartFilters en est sorti — le panneau Calques montre désormais les filtres dynamiques.
export const SANS_EDITEUR = new Set(["filter.other.custom"]);
// Champs sans éditeur générique : l'écran ne les montre pas et le pont les borne en taille.
export const OPAQUES = new Set(["json", "struct", "intArray", "union", "?"]);
// Références (calque, document, état d'historique) : un entier qui DÉSIGNE quelque chose ; un champ nombre libre n'a
// pas de sens (l'index d'un autre document ouvert, l'id d'un calque) — l'écran ne les montre pas non plus.
export const REFERENCES = new Set(["layerId", "index", "docIndex"]);

const MAX_CHAINE_STR = 256;          // MAX_CHAINE_STR du pont
const MAX_CHAINE_OUVERTE = 64;       // MAX_CHAINE_OPAQUE du pont (énumérations ouvertes)

const liste = (champs) => (Array.isArray(champs) ? champs : []);
// Une clé « fichier » n'est refusée par le pont que pour un texte ou un opaque : `output` de edit.contentAwareFill est une
// énumération (current|new|duplicate) admise, elle reste visible.
const fichier = (c) => CLES_FICHIER.has(String(c.cle).toLowerCase()) && (c.type === "str" || OPAQUES.has(c.type));
const cache = (c) => CLES_CACHEES.has(c.cle) || fichier(c);
// Clés qui désignent un fichier À ÉCRIRE ou À LIRE comme tout l'objet de la commande (layer.exportAs {path},
// filter.render.flame {path}, file.automate.batch {input, output}) : requises, elles grisent l'entrée même s'il reste
// des champs visibles. `file` et `data` (colorLookup) n'y sont pas : alternatives à `lut`, optionnelles de fait.
const CLES_FICHIER_REQUIS = new Set(["path", "mappath", "dir", "directory", "folder", "input", "output", "droplet", "script"]);
const borne = (c) => typeof c.min === "number" && typeof c.max === "number";
// Un défaut « en prose » ({texte: "foreground"}) décrit un comportement du moteur : jamais une valeur.
const aDefaut = (c) => c.defaut !== undefined && c.defaut !== null && typeof c.defaut !== "object";

// Un champ montré à l'écran : ni clé cachée ou fichier, ni opaque, ni référence.
export function champsVisibles(champs) {
  return liste(champs).filter((c) => c && !cache(c) && !OPAQUES.has(c.type) && !REFERENCES.has(c.type));
}

// « bientôt » : D9 ; SANS_EDITEUR ; ou une commande qui exige un AUTRE document (docIndex requis : Déplacement, Correspondance de la
// couleur — le formulaire générique n'a pas de choix de document) ; ou une commande dont l'écran ne peut rien montrer
// alors qu'elle attend une donnée opaque sans défaut (Galerie de filtres). Le registre 0.3.0 n'écrit « ? » que rarement :
// un opaque non marqué n'est donc pas forcément requis (Effets d'éclairage marche sans `lights`) — tant qu'il reste des
// champs visibles, le dialogue s'ouvre et l'opaque garde le défaut du moteur.
export function sansEcran(id, champs) {
  if (D9.has(id) || SANS_EDITEUR.has(id)) return true;
  const requis = (c) => !c.optionnel && !aDefaut(c);
  if (liste(champs).some((c) => c && fichier(c) && requis(c) && CLES_FICHIER_REQUIS.has(String(c.cle).toLowerCase()))) return true;
  // Une commande qui n'est QU'un fichier (layer.smartObjects.replaceContents {layer?, path}) : l'écran n'en envoie
  // jamais, le pont les refuse. Pas quand d'autres champs restent visibles : colorLookup écrit `file:text` sans « ? »
  // alors que `lut` (liste intégrée) suffit — le registre ne dit pas « requis » de façon fiable.
  if (!champsVisibles(champs).length && liste(champs).some((c) => c && fichier(c) && requis(c))) return true;
  const l = liste(champs).filter((c) => c && !cache(c));
  if (l.some((c) => c.type === "docIndex" && requis(c))) return true;
  return champsVisibles(l).length === 0 && l.some((c) => OPAQUES.has(c.type) && requis(c));
}

// Contrôle de chaque champ : curseur+nombre (borné), nombre (unité, entier, référence), liste, case, couleur, texte ;
// « aucun » pour un opaque (pas d'éditeur générique).
export function controleDe(c) {
  if (!c) return "aucun";
  if (OPAQUES.has(c.type)) return "aucun";
  if (estFusion(c)) return "liste";                               // VALEURS_FUSION, quel que soit le type écrit
  if (c.type === "number" && borne(c)) return "curseur";
  if (c.type === "number" || c.type === "int" || REFERENCES.has(c.type)) return "nombre";
  if (c.type === "enum") return "liste";
  if (c.type === "bool") return "case";
  if (c.type === "color") return "couleur";
  return "texte";
}

// Entier effectif. `entier` du registre n'est qu'une indication tirée de l'écriture des bornes (0..2 sans point) ; un
// défaut décimal la dément (lightZ 0..2=0.6) — arrondir y casserait la valeur par défaut elle-même.
export function estEntier(c) {
  if (!c) return false;
  if (c.type === "int" || REFERENCES.has(c.type)) return true;
  if (c.type !== "number" || c.entier !== true) return false;
  return !(typeof c.defaut === "number" && !Number.isInteger(c.defaut));
}

// Bornes d'un champ numérique compte tenu des AUTRES valeurs du formulaire -> {min?, max?} (vide = sans bornes).
// - Teinte/Saturation : `colorize` vrai dans les valeurs -> hue 0..360, saturation 0..100 (BORNES_COLORIZE du pont ;
//   seuls les deux hueSaturation du registre ont une clé `colorize`). Le formulaire (B2) les relit à chaque bascule.
// - `seed` : le registre écrit `u32`/`u64` (non signé) mais le champ structuré ne garde que `int` ; on le borne à ≥ 0 par
//   son NOM (les 17 `seed` du registre sont tous u32/u64). Les autres u32 (id de style, index de filtre dynamique)
//   sont hors périmètre.
export function bornesEffectives(c, valeurs) {
  if (!c) return {};
  const v = valeurs && typeof valeurs === "object" ? valeurs : {};
  const bc = BORNES_COLORIZE[c.cle];
  if (bc && "colorize" in v && (v.colorize === true || v.colorize === "true")) return { min: bc[0], max: bc[1] };
  if (borne(c)) return { min: c.min, max: c.max };
  if (c.cle === "seed" && (c.type === "int" || c.type === "number")) return { min: 0 };
  return {};
}

// Les valeurs d'une liste : les 27 modes pour un champ `blend` (28 avec passThrough en tête quand le champ le permet :
// `transfert`, options de fusion d'un groupe, t138 B6), sinon les valeurs du registre.
export function valeursDe(c) {
  if (estFusion(c)) return c.transfert === true ? ["passThrough", ...VALEURS_FUSION] : VALEURS_FUSION.slice();
  return c && Array.isArray(c.valeurs) ? c.valeurs.slice() : [];
}

// Un mode de fusion lisible ("Multiply", "linear dodge (add)", "colorBurn") -> son id ; passThrough refusé (groupes).
function fusionDe(v) {
  const id = typeof v === "string" ? idFusion(v) : null;
  return id && id !== "passThrough" ? id : null;
}

// Borne n selon {min?, max?}.
function dans(n, b) {
  if (typeof b.min === "number") n = Math.max(b.min, n);
  if (typeof b.max === "number") n = Math.min(b.max, n);
  return n;
}

// Valeur neutre quand ni valeur connue ni défaut utilisable : 0 ramené dans les bornes, faux, 1re valeur, noir, vide.
function neutre(c, valeurs) {
  if (estFusion(c)) return "normal";
  switch (c.type) {
    case "number": case "int": return dans(0, bornesEffectives(c, valeurs));
    case "layerId": case "index": case "docIndex": return 0;
    case "bool": return false;
    case "enum": return Array.isArray(c.valeurs) && c.valeurs.length ? c.valeurs[0] : "";
    case "color": return "#000000";
    case "str": return "";
    default: return undefined;                                  // opaque : le moteur garde son défaut
  }
}

// Repli d'une saisie illisible : le défaut du registre s'il est du bon type (coercé), sinon le neutre. Jamais de
// récursion : le défaut n'est retenu que s'il passe tel quel le test de son type.
function repli(c, valeurs) {
  if (estFusion(c)) return fusionDe(c.defaut) || "normal";       // défaut du registre s'il est un mode, sinon normal
  if (aDefaut(c)) {
    const d = c.defaut;
    if ((c.type === "number" || c.type === "int") && typeof d === "number" && Number.isFinite(d)) return coercer(c, d, valeurs);
    if (c.type === "bool" && typeof d === "boolean") return d;
    if (c.type === "enum" && Array.isArray(c.valeurs) && c.valeurs.includes(d)) return d;
    if (c.type === "enum" && c.ouverte && typeof d === "string" && d && d.length <= MAX_CHAINE_OUVERTE) return d;
    if (c.type === "color" && typeof d === "string" && hex(d)) return hex(d);
    if (c.type === "str" && typeof d === "string") return d.slice(0, MAX_CHAINE_STR);
  }
  return neutre(c, valeurs);
}

// Valeur initiale : la valeur connue (coercée), sinon le défaut du registre, sinon un neutre. `valeurs` = les autres
// valeurs du formulaire (bornes de la colorisation).
export function valeurInitiale(c, connue, valeurs) {
  if (!c) return undefined;
  if (connue !== undefined && connue !== null) return coercer(c, connue, valeurs);
  return repli(c, valeurs);
}

// Nombre lu d'une saisie : nombre fini, ou texte (virgule décimale française admise) ; booléen et le reste -> NaN.
function lireNombre(v) {
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.trim() !== "") return Number(v.trim().replace(",", "."));
  return NaN;
}

// "#ABC", "abcdef", "#AbCdEf", [r,g,b(,a)] en 0..255 -> "#rrggbb" ; null si illisible. L'alpha est abandonné : le pont
// n'admet que #rrggbb pour la plupart des couleurs, et un sélecteur de couleur n'en a pas.
function hex(v) {
  if (typeof v === "string") {
    const s = v.trim().replace(/^#/, "");
    if (/^[0-9a-f]{6}$/i.test(s)) return "#" + s.toLowerCase();
    if (/^[0-9a-f]{3}$/i.test(s)) return "#" + s.split("").map((x) => x + x).join("").toLowerCase();
    return null;
  }
  if (Array.isArray(v) && (v.length === 3 || v.length === 4) && v.every((x) => typeof x === "number" && Number.isFinite(x) && x >= 0 && x <= 255))
    return "#" + v.slice(0, 3).map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
  return null;
}

// Coercition à l'envoi : nombre fini borné (arrondi si entier), bool strict, enum dans la liste, couleur #rrggbb,
// texte borné, mode de fusion parmi les 27. Une saisie illisible retombe sur le défaut du registre, sinon le neutre.
// `valeurs` = tout le formulaire (bornes effectives : colorisation).
export function coercer(c, brut, valeurs) {
  if (!c) return brut;
  if (estFusion(c)) return fusionDe(brut) || repli(c, valeurs);
  switch (c.type) {
    case "number": case "int": {
      let n = lireNombre(brut);
      if (!Number.isFinite(n)) return repli(c, valeurs);
      if (estEntier(c)) n = Math.round(n);
      n = dans(n, bornesEffectives(c, valeurs));
      return n === 0 ? 0 : n;                                        // jamais -0
    }
    case "layerId": case "index": case "docIndex": {
      const n = lireNombre(brut);
      return Number.isFinite(n) ? Math.max(0, Math.round(n)) : repli(c);
    }
    case "bool":
      if (brut === true || brut === "true") return true;
      if (brut === false || brut === "false") return false;
      return repli(c);
    case "enum": {
      const vals = Array.isArray(c.valeurs) ? c.valeurs : [];
      if (vals.includes(brut)) return brut;
      // un <select> rend toujours du texte : "4" pour la valeur 4
      const parTexte = vals.find((v) => typeof v === "number" && String(v) === String(brut));
      if (parTexte !== undefined) return parTexte;
      if (c.ouverte && typeof brut === "string" && brut !== "" && brut.length <= MAX_CHAINE_OUVERTE) return brut;
      return repli(c);
    }
    case "color": return hex(brut) || repli(c);
    case "str":
      if (typeof brut === "string") return brut.slice(0, MAX_CHAINE_STR);
      if (typeof brut === "number" && Number.isFinite(brut)) return String(brut);
      return repli(c);
    default: return brut;                                           // opaque : jamais envoyé par parametres
  }
}

// Paramètres à envoyer : les champs VISIBLES présents dans `valeurs`, coercés. Une clé absente est omise (le moteur
// garde son défaut, plus juste que notre neutre) ; un texte vide aussi (`blend: ""` serait refusé par le pont). Les
// clés cachées, fichiers, références et opaques ne partent jamais d'ici.
export function parametres(champs, valeurs) {
  const v = valeurs && typeof valeurs === "object" ? valeurs : {};
  const sortie = {};
  for (const c of champsVisibles(champs)) {
    if (!Object.prototype.hasOwnProperty.call(v, c.cle) || v[c.cle] === undefined) continue;
    const x = coercer(c, v[c.cle], v);
    if (x === undefined || (c.type === "str" && x === "")) continue;
    sortie[c.cle] = x;
  }
  return sortie;
}

// Traduction si le dictionnaire a la clé (dzT rend la clé elle-même quand elle manque), sinon null.
function traduit(cle, t) {
  if (typeof t !== "function") return null;
  const r = t(cle);
  return typeof r === "string" && r !== "" && r !== cle ? r : null;
}

// Libellé d'un paramètre : dico photolab.param.<cle en minuscules> (B3), sinon la clé camelCase en mots (« blurAngle »
// -> « Blur angle »). Toutes les clés du dictionnaire sont en minuscules (convention de l'app, test_i18n_l0) : « blurAngle »
// se cherche sous photolab.param.blurangle ; le banc libellés vérifie qu'aucune clé du moteur ne s'écrase ainsi.
export function libelleParam(cle, t) {
  return traduit("photolab.param." + String(cle).toLowerCase(), t) || humaniser(cle);
}
// Libellé d'une valeur d'énumération : dico photolab.valeur.<v>, sinon la valeur en mots ; un nombre reste tel quel.
export function libelleValeur(v, t) {
  if (typeof v === "number") return String(v);
  return traduit("photolab.valeur." + String(v).toLowerCase(), t) || humaniser(v);   // minuscules : voir libelleParam
}

// « blurAngle » -> « Blur angle », « cooling80 » -> « Cooling80 », « warmingLBA » -> « Warming LBA »,
// « lightX » -> « Light X ». Les sigles (2 capitales ou plus) restent en capitales, une lettre seule aussi (axe X).
export function humaniser(cle) {
  const s = String(cle == null ? "" : cle).replace(/[_-]+/g, " ");
  const mots = s.match(/[A-Z]{2,}(?=[A-Z][a-z]|[^A-Za-z]|$)|[A-Z]?[a-z]+[0-9]*|[A-Z][0-9]*|[0-9]+[a-z]*/g) || [];
  const txt = mots.map((m) => (/^[A-Z]{2,}[0-9]*$/.test(m) ? m : m.length === 1 ? m.toUpperCase() : m.toLowerCase())).join(" ");
  return txt.charAt(0).toUpperCase() + txt.slice(1);
}

// Décimales écrites d'un nombre (0.25 -> 2), plafonnées à 4.
function decimales(x) {
  if (typeof x !== "number" || !Number.isFinite(x) || Number.isInteger(x)) return 0;
  const m = String(x).match(/\.(\d+)/);
  return Math.min(4, m ? m[1].length : 0);
}

// Pas du curseur : 1 pour un entier ; 0,01 pour un écart ≤ 2 (fractions 0..1) ; sinon la précision écrite des bornes
// ou du défaut (gamma 0.01..9.99 -> 0,01 ; rayon 0.1..1000 -> 0,1) ; EV -> 0,01 ; écart ≤ 20 -> 0,1 ; sinon 1.
// `valeurs` : bornes effectives (colorisation), comme coercer.
export function pasDe(c, valeurs) {
  if (!c || estEntier(c)) return 1;
  const b = bornesEffectives(c, valeurs);
  const borneB = typeof b.min === "number" && typeof b.max === "number";
  const d = Math.max(decimales(b.min), decimales(b.max), decimales(c.defaut));
  if (borneB && b.max - b.min <= 2) return Math.min(0.01, 10 ** -d);
  if (d > 0) return Number((10 ** -d).toFixed(d));
  if (c.unite === "ev") return 0.01;
  if (borneB && b.max - b.min <= 20) return 0.1;
  return 1;
}
