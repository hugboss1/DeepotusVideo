// mod-iacalque.js — t190 (G8, plan « Génération IA enrichie ») : l'IMAGE IA PAR CALQUE du Vectorlab.
//
// Le geste voulu : fond ; calque 1 : générer une image, retirer son fond ; calque 2 : texte et formes ;
// calque 3 : générer une autre image… Le panneau flottant « Image IA sur le calque » (même allure que le
// dialogue IA de mod-ia, posé sur #stage À GAUCHE — le dialogue IA est à droite —, déplaçable par sa tête)
// choisit le CALQUE cible (les calques non verrouillés, présélection = celui d'où l'on vient ; un calque masqué
// le dit), le MODÈLE (DzModelesIA, une option sans clé reste choisissable : le 503 n'arrive qu'au lancement), le
// FORMAT d'après la page, et le DÉTOURAGE (registre G4, sujet à garder si le modèle l'exige) ; le prix TOTAL est
// chiffré par le serveur (/api/cost/estimate, campagne image + détourage), jamais inventé. Sans liste des modèles
// (catalogue illisible), « Générer » reste gris et « Réessayer » relit la liste : le serveur ne tire jamais le
// modèle par défaut sans prix affiché. Jamais gris pour une clé manquante.
//
// Les modèles vectoriels (sortie « svg », Recraft) n'y sont PAS : l'image posée ici est un raster, et
// /images/generate refuse un modèle vectoriel sans `sortie: "svg"` (le dialogue IA du canevas, mod-ia, pose
// les tracés). « Retirer le fond » du panneau Image (ligneDetour, prix serveur affiché à côté) remplace l'image
// par une NOUVELLE image du magasin du document en UNE commande (op_image_remplacer de mod-doc via VL.executer) :
// Ctrl+Z rend l'image d'avant, dont le PNG reste au magasin.
//
// La case « Guider par les calques du dessous » (suite du 12/10) : le rendu PNG des calques visibles SOUS le calque
// cible part en Bibliothèque puis à /images/process op « edit » ; le sélecteur ne propose alors que les modèles qui
// acceptent une image d'entrée (catalogue `edit`). Voir docGuide plus bas.
//
// Les gestes du panneau : garderClics (mod-flottant, en bulle) et VL.dansPanneau (les outils en CAPTURE sortent).
// La logique PURE est en tête (banc qa/iacalque.test.mjs) ; initIaCalque ne touche le DOM qu'à l'appel. t197 : ce qui
// est commun avec le panneau du Photolab (formats, devis, prix, refus, un seul vol, gestes gardés) vient de
// /shared/dz-iacalque-commun.js — ici, l'adaptation au document du Vectorlab et aux clés vectorlab.iacalque.*.
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
import { esc, garderClics } from "./mod-flottant.js";
import { op_image_remplacer, image_profonde } from "./mod-doc.js";
import * as C from "../../shared/dz-iacalque-commun.js";

// les rôles du module commun -> les clés du Vectorlab, écrites EN ENTIER (le banc test_i18n_l6 relève les clés par
// leur texte : un préfixe concaténé lui échapperait)
const CLES = {
  prix_inconnu: "vectorlab.iacalque.prix_inconnu", prix_a_mesurer: "vectorlab.iacalque.prix_a_mesurer",
  prix_gratuit: "vectorlab.iacalque.prix_gratuit", prix: "vectorlab.iacalque.prix",
  prix_partiel_image: "vectorlab.iacalque.prix_partiel_image", prix_partiel: "vectorlab.iacalque.prix_partiel",
  cle_absente: "vectorlab.iacalque.cle_absente", detour_modele: "vectorlab.iacalque.detour_modele",
  detour_cle: "vectorlab.iacalque.detour_cle", detour_cle_image: "vectorlab.iacalque.detour_cle_image",
  sujet_requis: "vectorlab.iacalque.sujet_requis",
};
const tr = (role, vars) => T(CLES[role], vars);

/* ── pur ── */
export { TAILLES, RAPPORTS, unSeulVol } from "../../shared/dz-iacalque-commun.js";

// le format au rapport le plus PROCHE de la page (doc.taille {w, h})
export const taillePour = (t) => C.formatPour(t && t.w, t && t.h);

// le corps de POST /api/images/generate ({prompt, n, model, size, source})
export function requete(o) {
  const prompt = String((o && o.prompt) || "").trim();
  if (!prompt) throw new Error(T("vectorlab.iacalque.prompt_vide"));
  const q = { prompt, n: 1 };
  if (o.modele) q.model = String(o.modele);
  q.size = C.TAILLES.includes(o.taille) ? o.taille : "square_hd";
  q.source = "vectorlab";
  return q;
}

// le corps de POST /api/images/process (registre G4) : {op, filename, modele, sujet?, source}
export function requeteDetour(o) {
  if (!o || !o.modele) throw new Error(T("vectorlab.iacalque.detour_modele"));
  const q = { op: "remove-bg", filename: String(o.nom || ""), modele: String(o.modele) };
  const sujet = String(o.sujet || "").trim();
  if (sujet) q.sujet = sujet;
  q.source = "vectorlab";
  return q;
}

// le PLAN d'un tir : générer, détourer (sur demande), poser sur LE calque demandé
export function etapes(o) {
  const out = [{ op: "generer" }];
  if (o && o.detourer) out.push({ op: "detourer", modele: o.modeleDetour, sujet: o.sujet || "" });
  out.push({ op: "poser", calqueId: o && o.calqueId });
  return out;
}

// la cible AVANT toute dépense : un calque inconnu ou verrouillé est refusé, rien ne part
export function verifierCible(doc, calqueId) {
  const c = doc && Array.isArray(doc.calques) ? doc.calques.find((x) => x.id === calqueId) : null;
  if (!c) throw new Error(T("vectorlab.iacalque.calque_absent", { id: String(calqueId) }));
  if (c.verrou) throw new Error(T("vectorlab.iacalque.calque_verrouille", { nom: c.nom || c.id }));
  return c;
}

// les calques qu'on peut viser (le dessus en tête, comme le panneau Calques) ; un calque masqué le dit — l'image
// y serait posée invisible
export function calquesCibles(doc) {
  return [...((doc && doc.calques) || [])].reverse().filter((c) => !c.verrou)
    .map((c) => ({ id: c.id, nom: c.nom || c.id, masque: c.visible === false }));
}

// les <option> de la liste des calques (la cible présélectionnée)
export function optionsCalques(doc, cible) {
  return calquesCibles(doc).map((c) => `<option value="${esc(c.id)}"${c.id === cible ? " selected" : ""}>`
    + `${esc(c.nom)}${c.masque ? esc(T("vectorlab.iacalque.masque")) : ""}</option>`).join("");
}

// la cible après un changement du document : la même si elle est encore libre, sinon le calque demandé, sinon
// le premier libre, sinon aucune
export function cibleValide(doc, voulu, repli) {
  const ids = calquesCibles(doc).map((c) => c.id);
  if (ids.includes(voulu)) return voulu;
  if (ids.includes(repli)) return repli;
  return ids[0] || "";
}

// le devis serveur (POST /api/cost/estimate) : une campagne image + détourage
// sans modèle choisi, aucun devis plutôt qu'un prix faux (null → « Prix estimé : … ») — et « Générer » est gris
export const devisCorps = (o) => C.devisCorps({ modele: o && o.modele, detourer: !!(o && o.detourer), modeleDetour: o && o.modeleDetour });

// le devis du seul détourage (le bouton « Retirer le fond » du panneau Image)
export const devisDetour = (modele) => C.devisCorps({ image: false, detourer: true, modeleDetour: modele });

// le libellé du prix : jamais « gratuit » pour un 0 $ payant (« à mesurer ») ; une ligne locale à 0 $ l'est ; la part
// à mesurer est nommée (image ou détourage)
export const libellePrix = (devis) => C.libellePrix(devis, tr);

// le message d'une réponse en échec : 503 = clé absente (lisible), le 402 d'un plafond refusé rend une chaîne
export const messageErreur = (status, d, statut) => C.messageErreur(status, d, statut, tr);

// fetch rejette par un TypeError (« Failed to fetch », « NetworkError… ») quand le serveur ne répond pas : un
// message lisible, dans la langue de l'interface
export async function chercher(url, init, f = (typeof window !== "undefined" && window.fetch) || globalThis.fetch) {
  try { return await f(url, init); } catch (e) { throw new Error(T("vectorlab.iacalque.reseau")); }
}

// l'état de « Générer » : gris pendant le vol, sans calque libre, et tant que la liste des modèles n'est pas lue
// (chargement), illisible (raison « catalogue » : message + Réessayer) ou lue mais VIDE (raison « vide » : aucun
// modèle d'image à proposer) — sinon le serveur tirerait le modèle par défaut sans prix affiché. JAMAIS gris pour une clé manquante : l'option sans clé reste choisissable, le 503
// n'arrive qu'au lancement (décision de l'utilisateur 11/10).
//   catalogue : "chargement" | "ok" | "echec" ; modele : la valeur de la liste ("" = aucune) ; guide : la case
//   « Guider par les calques du dessous » (liste lue, NON vide, sans aucun modèle qui sache partir d'une image : raison
//   « guide » ; une liste vide reste « vide » — décocher n'y changerait rien) ; nbModeles : la taille de la liste lue
export function etatGenerer({ enVol, cible, catalogue, modele, guide = false, nbModeles = 1 }) {
  if (enVol) return { gris: true, raison: "" };
  if (!cible) return { gris: true, raison: "calque" };
  if (catalogue === "echec") return { gris: true, raison: "catalogue" };
  if (catalogue === "ok" && !modele && guide && nbModeles > 0) return { gris: true, raison: "guide" };
  if (catalogue === "ok" && !modele) return { gris: true, raison: "vide" };
  if (catalogue !== "ok") return { gris: true, raison: "" };
  return { gris: false, raison: "" };
}

// le détourage demandé est complet AVANT la génération payée : un modèle, sa clé (l'option sans clé reste
// CHOISISSABLE, seul le lancement est refusé) et le sujet si le modèle l'exige. `info` = l'entrée du catalogue
// detourage_image ({dispo, cle, prompt}) — LA source du « sujet requis » et de la clé ; null si inconnue.
// `sansCase` : le panneau Image n'a pas de case « Retirer le fond » à décocher — le message ne la propose pas.
export const verifierDetour = (o, info, opts) => C.verifierDetour(o, info, tr, opts);

// le tir : cible vérifiée, génération, détourage éventuel, pose sur LE calque demandé — d = {doc(), post(url,
// corps), poser(nom, calqueId) → id (faux = pose refusée : VL.executer avale l'erreur), infoDetour(id)?,
// modelesImage()? → la liste du catalogue, guide(docGuide, calqueId, cadre)? → nom du guide déposé en Bibliothèque}
// (fetch et pose réels dans la page, faux au banc). Tout refus GRATUIT part avant le premier POST — avec la case
// « guide » : modèle qui sait partir d'une image, quelque chose de visible sous le calque cible. Un détourage
// qui échoue APRÈS la génération payée (plafond refusé, fournisseur en 502…) n'efface pas l'image payée : elle est
// posée telle quelle et `detourEchec` le dit. Une pose impossible le dit aussi, avec le nom gardé en Bibliothèque.
// Un tir guidé qui échoue après le dépôt du guide (503, 402, 502…) dit le guide gardé en Bibliothèque (jamais
// supprimé d'office) ; l'image guidée est posée par image_poser_page (le cadre du format ramené sur la page).
export async function executerPlan(o, d) {
  verifierCible(d.doc(), o.calqueId);
  const { size } = requete(o);
  // le guide est FIGÉ avant le premier await : le document tel qu'au clic (o.docGuide, pris par le panneau)
  let docG = null, cadre = null;
  if (o.guide) {
    docG = o.docGuide || docGuide(d.doc(), o.calqueId);
    cadre = cadreGuide(docG.taille, size);
    verifierGuide(o, d.modelesImage ? await d.modelesImage() : null);
  }
  verifierDetour(o, o.detourer && d.infoDetour ? await d.infoDetour(o.modeleDetour) : null);
  let nom = null, detourEchec = "", guide = "";
  for (const e of etapes(o)) {
    if (e.op === "generer") {
      let r;
      if (docG) {
        // le guide d'abord (dépôt gratuit en Bibliothèque), puis l'édition payante qui part de lui
        guide = await d.guide(docG, o.calqueId, cadre);
        try {
          r = await d.post("/api/images/process", requeteGuide({ ...o, filename: guide }));
        } catch (x) {
          throw new Error(T("vectorlab.iacalque.guide_garde", { raison: String(x && x.message || x), guide }));
        }
        nom = (r && r.images || [])[0];
        if (!nom) throw new Error(T("vectorlab.iacalque.guide_garde", { raison: T("vectorlab.image.generation_vide"), guide }));
        continue;
      }
      r = await d.post("/api/images/generate", requete(o));
      nom = (r && r.images || [])[0];
      if (!nom) throw new Error(T("vectorlab.image.generation_vide"));
    } else if (e.op === "detourer") {
      try {
        const r = await d.post("/api/images/process", requeteDetour({ nom, modele: e.modele, sujet: e.sujet }));
        const n2 = (r && r.images || [])[0];
        if (!n2) throw new Error(T("vectorlab.iacalque.detour_vide"));
        nom = n2;
      } catch (x) { detourEchec = String(x && x.message || x); }
    } else if (e.op === "poser") {
      let id;
      try {
        verifierCible(d.doc(), e.calqueId);        // verrouillé ou supprimé PENDANT le vol
        id = await d.poser(nom, e.calqueId, cadre ? (nat, taille) => image_poser_page(nat, taille, cadre) : undefined);
      } catch (x) {
        throw new Error(T("vectorlab.iacalque.pose_echouee", { raison: String(x && x.message || x), nom }));
      }
      if (!id) throw new Error(T("vectorlab.iacalque.pose_echouee", { raison: T("vectorlab.iacalque.pose_refusee"), nom }));
      const out = detourEchec ? { nom, id, detourEchec } : { nom, id };
      if (guide) out.guide = guide;
      return out;
    }
  }
}

// « Retirer le fond » d'une image du document — d = {doc() → le document, versBiblio(o) → nom en Bibliothèque,
// post(url, corps), deposer(nom) → {href, nat} (nouvelle image du magasin du document), executer(fn, …args)}.
// Tout refus GRATUIT part avant le premier POST : modèle, et l'image RETROUVABLE par op_image_remplacer (la même
// recherche, qui descend dans les groupes) — jamais un détourage payé que la commande ne pourrait pas poser.
export async function retirerFondFlux(o, choix, d) {
  if (!o || o.type !== "image") throw new Error(T("vectorlab.iacalque.image_introuvable", { id: String(o && o.id) }));
  const corps = requeteDetour({ nom: "", modele: choix && choix.modele, sujet: choix && choix.sujet });
  image_profonde(d.doc(), o.id);
  corps.filename = await d.versBiblio(o);
  const r = await d.post("/api/images/process", corps);
  const nom = (r && r.images || [])[0];
  if (!nom) throw new Error(T("vectorlab.iacalque.detour_vide"));
  const { href, nat } = await d.deposer(nom);
  // jamais par-dessus l'image d'avant : Annuler doit la retrouver
  if (href === o.href) throw new Error(T("vectorlab.iacalque.meme_image"));
  if (!d.executer(op_image_remplacer, o.id, href, nat)) {
    throw new Error(T("vectorlab.iacalque.detour_remplacement", { nom }));
  }
  return href;
}

// le nom du dépôt en Bibliothèque de l'image à détourer (`vector_` : provenance vectorlab, réécrit en place)
export function nomDepot(docId, href) {
  const a = (s) => String(s || "").replace(/\.png$/i, "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `vector_${a(docId)}_detour_${a(href)}.png`;
}

// le nom rendu par /api/images/upload, ou une erreur lisible (jamais un « filename » undefined envoyé au détourage
// ni à l'édition guidée) — `cle` : le message du dépôt concerné (image à détourer par défaut, ou guide)
export function nomDuDepot(d, cle = "vectorlab.iacalque.biblio_sans_nom") {
  if (!d || !d.filename) throw new Error(T(cle));
  return String(d.filename);
}

/* ── le GUIDE (suite de t190, 12/10) : l'image de ce qui est visible SOUS le calque cible ──
   Case « Guider par les calques du dessous » : le rendu PNG des calques INFÉRIEURS visibles (au format de la page,
   fond de page compris) est déposé en Bibliothèque puis envoyé à POST /api/images/process op « edit » (l'image
   d'entrée du modèle) au lieu de /images/generate. La provenance relie l'image produite à son guide (l'enveloppe de
   /images/process note parent = filename, relation = « edit »). Sa SOURCE reste « retouche », celle de toutes les
   ops de /images/process : la Bibliothèque classe par fonction (une édition est une retouche) et le parent, lui, est
   un `vector_` noté « vectorlab » — noter ici la source du corps changerait le classement des huit ops pour un seul
   appelant ; le serveur n'est donc pas touché. Seuls les modèles dont l'entrée du catalogue porte
   `edit: true` savent partir d'une image. Le prix : la garde de l'op edit chiffre {kind: "image", model, n} — le
   MÊME devis que la génération (devisCorps), donc le même chiffre avant et après le clic. */

// les modèles qui acceptent une image d'entrée (champ `edit` de /api/ia/catalogue?nature=image)
export function guidables(mods) {
  return (mods || []).filter((m) => m && m.edit === true);
}

// un objet DESSINABLE : tout objet hors groupe ; un groupe l'est s'il contient (à toute profondeur) un dessinable
function dessinable(o) {
  if (!o) return false;
  if (o.type === "groupe") return (o.enfants || []).some(dessinable);
  return true;
}

// un calque se voit : ni masqué, ni à opacité nulle, et il porte au moins un objet dessinable
function calqueVu(c) {
  return !!c && c.visible !== false && !(c.opacite !== undefined && !(+c.opacite > 0))
    && Array.isArray(c.objets) && c.objets.some(dessinable);
}

// le document du guide : une COPIE qui ne garde que les calques visibles SOUS le calque cible (le calque cible et
// ceux du dessus exclus) ; le document de l'écran et son historique ne sont jamais touchés. Rien de visible sous
// le calque → refus gratuit, avant tout envoi (un fond de page seul n'est pas un guide).
export function docGuide(doc, calqueId) {
  const cs = (doc && doc.calques) || [];
  const i = cs.findIndex((c) => c.id === calqueId);
  if (i < 0) throw new Error(T("vectorlab.iacalque.calque_absent", { id: String(calqueId) }));
  const dessous = cs.slice(0, i).filter(calqueVu);
  if (!dessous.length) throw new Error(T("vectorlab.iacalque.guide_rien", { nom: cs[i].nom || cs[i].id }));
  const copie = JSON.parse(JSON.stringify(doc));
  const garder = new Set(dessous.map((c) => c.id));
  copie.calques = copie.calques.filter((c) => garder.has(c.id));
  return copie;
}

// le guide demandé est complet AVANT tout envoi : un modèle choisi, et qui sait partir d'une image (`mods` = la
// liste du catalogue ; null = inconnue, le serveur tranchera)
export function verifierGuide(o, mods) {
  if (!o || !o.guide) return;
  if (!o.modele) throw new Error(T("vectorlab.iacalque.guide_choisir"));
  if (mods && !guidables(mods).some((m) => m.id === o.modele)) {
    throw new Error(T("vectorlab.iacalque.guide_modele", { modele: String(o.modele) }));
  }
}

// le corps de POST /api/images/process op « edit » (routes.py : filename, prompt, model, n, size, source)
export function requeteGuide(o) {
  const q = requete(o);
  if (!q.model) throw new Error(T("vectorlab.iacalque.guide_choisir"));
  if (!o.filename) throw new Error(T("vectorlab.iacalque.guide_sans_nom"));
  return { op: "edit", filename: String(o.filename), prompt: q.prompt, model: q.model, n: 1, size: q.size, source: q.source };
}

// le nom du guide en Bibliothèque : UNIQUE (un `vector_` est réécrit en place par /images/upload — la lignée d'une
// image guidée doit garder SON guide)
export function nomGuide(docId, calqueId, t) {
  const a = (s) => String(s || "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `vector_${a(docId)}_guide_${a(calqueId)}_${(+t || 0).toString(36)}.png`;
}

// le CADRE du guide : un canevas au rapport du format DEMANDÉ (taillePour : le preset le plus proche de la page),
// 1536 px au plus grand côté, la page centrée dedans en « contain » ({W, H} le canevas, k l'échelle page → canevas,
// {ox, oy} le coin de la page). Le résultat du modèle couvre ce canevas : image_poser_page le ramène sur la page.
// Une page si allongée que le dessous y tiendrait sur moins de GUIDE_PLANCHER px (bannière 10000×100) : refus nommé,
// jamais un guide de quelques pixels envoyé au modèle.
export const GUIDE_COTE = 1536, GUIDE_PLANCHER = 64;
export function cadreGuide(taille, size) {
  const pw = +(taille && taille.w), ph = +(taille && taille.h);
  if (!(pw > 0 && ph > 0)) throw new Error(T("vectorlab.image.taille_inconnue"));
  const r = C.RAPPORTS[size] || 1;
  const W = r >= 1 ? GUIDE_COTE : Math.round(GUIDE_COTE * r);
  const H = r >= 1 ? Math.round(GUIDE_COTE / r) : GUIDE_COTE;
  const k = Math.min(W / pw, H / ph);
  const petit = Math.min(pw * k, ph * k);
  if (petit < GUIDE_PLANCHER) throw new Error(T("vectorlab.iacalque.guide_page_etiree", { w: pw, h: ph, px: Math.round(petit) }));
  return { W, H, k, ox: (W - pw * k) / 2, oy: (H - ph * k) / 2 };
}

// la pose d'une image GUIDÉE : son cadre entier (le canevas du guide, quelle que soit sa taille native) ramené sur
// la page — la page est couverte EXACTEMENT, les marges du format débordent hors page. Pas de plafond « jamais
// agrandie » ici (image_poser_spec, la pose ordinaire, rendait 1376×768 au milieu d'une page 1920×1080).
export function image_poser_page(nat, taille, cadre) {
  if (!(nat && nat.w > 0 && nat.h > 0)) throw new Error(T("vectorlab.image.taille_inconnue"));
  const { W, H, k, ox, oy } = cadre;
  return { x: Math.round(-ox / k), y: Math.round(-oy / k), w: Math.max(1, Math.round(W / k)), h: Math.max(1, Math.round(H / k)) };
}

// SVG → Image → canvas → PNG : le canevas du cadre, rempli du fond de page (blanc sans fond : les modèles
// d'édition lisent mal la transparence), la page dessinée à sa place. Copie VOLONTAIRE de la rasterisation de
// mod-export plutôt qu'un rasteriserSVG partagé : celle-ci vit dans la fermeture d'initExport, ses messages sont des
// éditions L de la saisie L6 (export.py) sur les mêmes lignes qu'une édition S devrait remplacer, la mise en page
// diffère (canevas du format, page décalée) et mod-iacalque importerait mod-export, qui importe mod-image, qui
// importe mod-iacalque (cycle).
export function rasteriserGuide(svg, taille, cadre, fond) {
  return new Promise((res, rej) => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const img = new Image();
    img.onload = () => {
      const cv = document.createElement("canvas");
      cv.width = cadre.W; cv.height = cadre.H;
      const cx = cv.getContext("2d");
      cx.fillStyle = "#ffffff";
      if (fond) cx.fillStyle = fond;                // une couleur illisible est ignorée : le blanc reste
      cx.fillRect(0, 0, cadre.W, cadre.H);
      cx.drawImage(img, cadre.ox, cadre.oy, taille.w * cadre.k, taille.h * cadre.k);
      URL.revokeObjectURL(url);
      cv.toBlob((png) => png ? res(png) : rej(new Error(T("vectorlab.export.rasterisation_vide"))), "image/png");
    };
    img.onerror = () => { URL.revokeObjectURL(url); rej(new Error(T("vectorlab.export.svg_navigateur"))); };
    img.src = url;
  });
}

/* ── DOM ── */
// déplaçable par sa tête, comme le dialogue IA du canevas (borné à la scène)
export function brancherPoignee(el, stage, win) {
  el.addEventListener("pointerdown", (ev) => {
    if (!ev.target.closest("[data-poigne]") || ev.target.closest("button")) return;
    const r = el.getBoundingClientRect();
    const ox = ev.clientX - r.left, oy = ev.clientY - r.top;
    const sr = stage.getBoundingClientRect();
    const bouge = (e2) => {
      el.style.left = Math.max(0, Math.min(sr.width - 60, e2.clientX - sr.left - ox)) + "px";
      el.style.top = Math.max(0, Math.min(sr.height - 30, e2.clientY - sr.top - oy)) + "px";
      el.style.right = "auto";
    };
    const fin = () => { win.removeEventListener("pointermove", bouge); win.removeEventListener("pointerup", fin); };
    win.addEventListener("pointermove", bouge);
    win.addEventListener("pointerup", fin);
    ev.preventDefault();
  });
}

export function initIaCalque(VL) {
  const { $, etat } = VL;
  const lire = (k) => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };
  const ecrire = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } };
  const MI = () => (typeof window !== "undefined" && window.DzModelesIA) || null;

  async function poster(url, corps) {
    const r = await chercher(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps), cache: "no-store" });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(messageErreur(r.status, d, r.statusText));
    return d;
  }

  // les catalogues (gratuits), lus une fois par page ; un échec se relira (Réessayer)
  const catalogues = {};
  function catalogue(nature) {
    if (!catalogues[nature]) {
      const M = MI();
      catalogues[nature] = M ? M.charger(nature).then((l) => M.filtrer(l)) : Promise.reject(new Error("DzModelesIA"));
      catalogues[nature].catch(() => { delete catalogues[nature]; });
    }
    return catalogues[nature];
  }
  // l'entrée du catalogue d'un modèle de détourage (dispo, clé, sujet exigé) — catalogue() est la SEULE source
  const infoDe = (mods, id) => (mods || []).find((m) => m.id === id) || null;
  const sujetRequis = (mods, id) => !!(infoDe(mods, id) || {}).prompt;

  /* ── le tir ── */
  const deps = {
    doc: () => etat.doc,
    post: poster,
    // le calque actif ne change qu'une fois la pose RÉUSSIE
    poser: async (nom, calqueId, placer) => {
      const id = await VL.poserDepuisLibrary(nom, calqueId, placer);
      if (id) etat.calqueActif = calqueId;
      return id;
    },
    infoDetour: async (id) => infoDe(await catalogue("detourage_image").catch(() => []), id),
    modelesImage: () => catalogue("image").catch(() => null),
    // le guide : les calques du dessous compilés par l'export du Vectorlab (VL.svgCourant, images inlinées), rendus
    // en PNG ici et déposés en Bibliothèque sous un nom unique — le document et l'historique ne bougent pas
    guide: async (docG, calqueId, cadre) => {
      const svg = await VL.svgCourant(false, null, docG);
      const png = await rasteriserGuide(svg, docG.taille, cadre, docG.fond || "");
      return deposerFichier(png, nomGuide(etat.docId, calqueId, Date.now()), "vectorlab.iacalque.guide_sans_nom");
    },
  };
  const lancer = C.unSeulVol(async (o) => {
    VL.toast(T("vectorlab.image.generation"));
    return executerPlan({ ...o, taille: o.taille || taillePour(etat.doc && etat.doc.taille) }, deps);
  }, () => majBouton());

  /* ── le panneau ── */
  let cible = "", modsDetour = [], modsImage = [], retour = null, etatCatalogue = "chargement", messageEcrit = "";
  const dire = (t) => { const e = $("#iacEtat"); if (e) e.textContent = t; };   // relu à chaque fois
  const guideCoche = () => !!($("#iacGuide") || {}).checked;
  // le modèle préféré de chaque mode : un tir guidé n'écrase pas celui du mode non guidé ; au décochage, le modèle
  // d'avant la bascule revient
  const CLE_MODELE = "dz_vl_iac_modele", CLE_MODELE_GUIDE = "dz_vl_iac_modele_guide";
  let avantGuide = "";
  function hote() {
    let el = $("#iaCalqueDlg");
    if (el) return el;
    const stage = $("#stage");
    if (!stage) return null;
    el = document.createElement("div");
    el.id = "iaCalqueDlg";
    el.className = "ia-dlg iac-dlg";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-labelledby", "iacTitre");
    el.hidden = true;
    stage.appendChild(el);
    brancher(el);
    return el;
  }
  const ouvert = () => { const el = $("#iaCalqueDlg"); return !!(el && !el.hidden); };
  const nomCalque = (id) => { const c = etat.doc && etat.doc.calques.find((x) => x.id === id); return c ? (c.nom || c.id) : String(id); };
  const choix = () => ({
    calqueId: cible,
    prompt: ($("#iacPrompt") || {}).value || "",
    modele: ($("#iacModele") || {}).value || "",
    guide: guideCoche(),
    detourer: !!($("#iacDetourer") || {}).checked,
    modeleDetour: ($("#iacDetour") || {}).value || "",
    sujet: ($("#iacSujet") || {}).value || "",
  });

  function squelette(el) {
    el.innerHTML = `
      <div class="ia-tete" data-poigne="1">
        <span class="ia-titre" id="iacTitre">${T("vectorlab.iacalque.titre")}</span>
        <span class="ia-sp"></span>
        <button class="ia-x" data-act="fermer" title="${T("vectorlab.ia.fermer")}" aria-label="${T("vectorlab.ia.fermer")}">${dzi("dz-action-fermer", 16)}</button>
      </div>
      <div class="ia-bas">
        <label class="ia-moteur">${T("vectorlab.iacalque.calque")}
          <select id="iacCalque" title="${T("vectorlab.iacalque.calque_aide")}">${optionsCalques(etat.doc, cible)}</select></label>
        <textarea id="iacPrompt" data-dz-ia="image" rows="3" placeholder="${T("vectorlab.iacalque.placeholder")}"></textarea>
        <label class="ia-moteur iac-case" title="${T("vectorlab.iacalque.guide_aide")}"><input type="checkbox" id="iacGuide"${lire("dz_vl_iac_guide") === "1" ? " checked" : ""}/>${T("vectorlab.iacalque.guide")}</label>
        <label class="ia-moteur">${T("vectorlab.ia.modele")}
          <select id="iacModele" title="${T("vectorlab.iacalque.modele_aide")}"><option value="">…</option></select></label>
        <label class="ia-moteur iac-case"><input type="checkbox" id="iacDetourer"/>${T("vectorlab.iacalque.retirer_fond")}</label>
        <label class="ia-moteur" id="iacDetourLigne" hidden>${T("vectorlab.iacalque.detourage")}
          <select id="iacDetour" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select></label>
        <input type="text" id="iacSujet" class="iac-sujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>
        <div class="iac-prix" id="iacPrix">${T("vectorlab.iacalque.prix_inconnu")}</div>
        <button id="iacGo" class="primaire">${dzi("dz-media-generer-image", 16)}<span id="iacGoTexte"></span></button>
        <div class="iac-etat-ligne"><span class="iac-etat" id="iacEtat" role="status"></span>
          <span class="iac-sep" id="iacSep" hidden>—</span><button id="iacReessayer" class="iac-reessayer" hidden>${T("vectorlab.iacalque.reessayer")}</button></div>
      </div>`;
    chargerModeles();
    catalogue("detourage_image").then((l) => {
      modsDetour = l;
      const sel = $("#iacDetour"), M = MI();
      if (sel && sel.isConnected && M) { M.remplir(sel, l, { valeur: lire("dz_vl_iac_detour") }); majSujet(); majDevis(); }
    }).catch(() => { /* le détourage reste sans liste : la case seule (le tir le refusera, sans dépense) */ });
  }
  // la liste des modèles d'image (cache par page) ; un échec → « Générer » gris + Réessayer
  function chargerModeles() {
    etatCatalogue = "chargement";
    majBouton();
    catalogue("image").then((l) => {
      modsImage = l;
      remplirModeles(guideCoche() ? (lire(CLE_MODELE_GUIDE) || lire(CLE_MODELE)) : lire(CLE_MODELE));
      etatCatalogue = "ok";
      majBouton(); majDevis();
    }).catch(() => { etatCatalogue = "echec"; majBouton(); });
  }
  // le sélecteur de modèles : tous, ou — case « guide » cochée — les seuls qui savent partir d'une image (une option
  // sans clé reste choisissable). Le modèle en place (ou mémorisé) qui ne sait pas guider cède la place au premier
  // qui sait, et on le dit.
  function remplirModeles(voulu) {
    const sel = $("#iacModele"), M = MI();
    if (!sel || !sel.isConnected || !M) return;
    const guide = guideCoche();
    M.remplir(sel, guide ? guidables(modsImage) : modsImage, { valeur: voulu });
    const nom = (id) => { const m = modsImage.find((x) => x.id === id); return m ? (m.label || m.id) : String(id); };
    if (guide && voulu && sel.value && sel.value !== voulu && modsImage.some((m) => m.id === voulu)) {
      dire(T("vectorlab.iacalque.guide_modele_remplace", { avant: nom(voulu), apres: nom(sel.value) }));
    }
  }
  // la liste des calques seule (réouverture, calque ajouté / renommé / verrouillé / masqué) : le prompt, les
  // listes de modèles et le message restent
  // les <option> ne sont réécrites que si elles ont CHANGÉ : un rendu du document ne referme pas une liste ouverte
  let sigCalques = "";
  function majCalques() {
    const sel = $("#iacCalque");
    cible = cibleValide(etat.doc, cible, "");
    if (sel) {
      const sig = optionsCalques(etat.doc, cible);
      if (sig !== sigCalques) { sel.innerHTML = sig; sigCalques = sig; }
      if (sel.value !== cible) sel.value = cible;
    }
    majBouton();
  }
  function majBouton() {
    const go = $("#iacGo"), tx = $("#iacGoTexte");
    if (!go || !tx) return;
    const { gris, raison } = etatGenerer({ enVol: lancer.enVol, cible, catalogue: etatCatalogue, modele: ($("#iacModele") || {}).value || "", guide: guideCoche(), nbModeles: modsImage.length });
    tx.textContent = lancer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.generer_sur", { nom: nomCalque(cible) });
    go.disabled = gris;
    const e = $("#iacEtat"), re = $("#iacReessayer"), sep = $("#iacSep");
    if (re) re.hidden = raison !== "catalogue";
    if (sep) sep.hidden = raison !== "catalogue";
    const m = raison === "calque" ? T("vectorlab.iacalque.aucun_calque_libre")
      : raison === "catalogue" ? T("vectorlab.iacalque.catalogue_absent")
        : raison === "vide" ? T("vectorlab.iacalque.modeles_vides")
          : raison === "guide" ? T("vectorlab.iacalque.guide_aucun_modele") : "";
    if (e) {
      // la raison est écrite ; une raison levée efface SON message (jamais l'issue d'un tir)
      if (m) e.textContent = m;
      else if (messageEcrit && e.textContent === messageEcrit) e.textContent = "";
    }
    messageEcrit = m;
  }
  function majSujet() {
    const c = choix();
    const l = $("#iacDetourLigne"), s = $("#iacSujet");
    if (l) l.hidden = !c.detourer;
    if (s) s.hidden = !(c.detourer && sujetRequis(modsDetour, c.modeleDetour));
  }
  let devisN = 0;
  async function majDevis() {
    const el = $("#iacPrix");
    if (!el) return;
    const n = ++devisN;
    el.textContent = T("vectorlab.iacalque.prix_inconnu");
    try {
      const corps = devisCorps(choix());
      if (!corps) return;                            // aucun modèle : « Prix estimé : … », jamais un prix faux
      const d = await poster("/api/cost/estimate", corps);
      if (n === devisN) el.textContent = libellePrix(d);
    } catch (e) {
      if (n === devisN) el.textContent = T("vectorlab.iacalque.prix_inconnu");
    }
  }

  async function tirer() {
    if (lancer.enVol) return;                       // anti-double tir : le second clic ne relance rien
    if (etatGenerer({ enVol: false, cible, catalogue: etatCatalogue, modele: ($("#iacModele") || {}).value || "", guide: guideCoche(), nbModeles: modsImage.length }).gris) return;
    const c = choix();
    try {
      verifierCible(etat.doc, c.calqueId);          // AVANT toute dépense
      requete(c);
      if (c.guide) {                                 // aucun POST, pas même le dépôt ; le guide est FIGÉ au clic
        verifierGuide(c, modsImage);
        c.docGuide = docGuide(etat.doc, c.calqueId);
        cadreGuide(c.docGuide.taille, taillePour(etat.doc.taille));
      }
      verifierDetour(c, infoDe(modsDetour, c.modeleDetour));
    } catch (e) { dire(e.message); VL.toast(e.message, true); return; }
    if (c.modele) ecrire(c.guide ? CLE_MODELE_GUIDE : CLE_MODELE, c.modele);
    if (c.modeleDetour) ecrire("dz_vl_iac_detour", c.modeleDetour);
    const p = lancer(c);
    majBouton();
    dire(T("vectorlab.iacalque.en_cours"));
    try {
      const r = await p;
      if (r && r.detourEchec) {
        const t = T("vectorlab.iacalque.detour_echoue_pose", { raison: r.detourEchec, calque: nomCalque(c.calqueId) });
        dire(t); VL.toast(t, true);
      } else if (r && r.guide) dire(T("vectorlab.iacalque.posee_guide", { nom: r.nom, calque: nomCalque(c.calqueId), guide: r.guide }));
      else if (r) dire(T("vectorlab.iacalque.posee", { nom: r.nom, calque: nomCalque(c.calqueId) }));
    } catch (e) {
      dire(e.message);
      VL.toast(e.message, true);
    }
    majBouton();
  }

  function brancher(el) {
    el.addEventListener("click", (ev) => {
      const b = ev.target.closest("button");
      if (!b) return;
      if (b.dataset.act === "fermer") fermer();
      else if (b.id === "iacGo") tirer();
      else if (b.id === "iacReessayer") chargerModeles();
    });
    el.addEventListener("change", (ev) => {
      const id = ev.target.id;
      if (id === "iacCalque") { cible = ev.target.value; majBouton(); }
      if (id === "iacModele") majBouton();
      if (id === "iacGuide") {
        const sel = $("#iacModele");
        ecrire("dz_vl_iac_guide", ev.target.checked ? "1" : "0");
        if (ev.target.checked) { avantGuide = (sel && sel.value) || ""; remplirModeles(lire(CLE_MODELE_GUIDE) || avantGuide); }
        else remplirModeles(avantGuide || lire(CLE_MODELE));
        majBouton();
      }
      if (id === "iacDetourer" || id === "iacDetour") majSujet();
      if (id === "iacModele" || id === "iacGuide" || id === "iacDetourer" || id === "iacDetour") majDevis();
    });
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); }
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey) && ev.target.id === "iacPrompt") { ev.preventDefault(); tirer(); }
    });
    brancherPoignee(el, $("#stage"), window);
    garderClics(el);
  }

  function ouvrir(calqueId) {
    if (!etat.doc) { VL.toast(T("vectorlab.image.aucun_doc"), true); return; }
    const el = hote();
    if (!el) return;
    const dejaOuvert = !el.hidden, construit = !!$("#iacPrompt");
    // le focus reviendra à l'élément d'ouverture (bouton du calque, menu…) à la fermeture
    if (!dejaOuvert) retour = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
    // l'outil actif reste : les outils en CAPTURE sortent devant un panneau flottant (VL.dansPanneau)
    cible = cibleValide(etat.doc, calqueId, "");
    if (calqueId && cible !== calqueId) {
      const c = etat.doc.calques.find((x) => x.id === calqueId);
      VL.toast(c ? T("vectorlab.iacalque.calque_verrouille", { nom: c.nom || c.id })
        : cible ? T("vectorlab.iacalque.calque_disparu", { nom: nomCalque(cible) })
          : T("vectorlab.iacalque.aucun_calque_libre"), true);
    }
    el.hidden = false;
    // le squelette n'est construit qu'UNE fois : rouvert (ou déjà ouvert), la liste des calques seule — le prompt
    // tapé et les listes de modèles restent ; une liste de modèles illisible est relue
    if (!construit) squelette(el);
    else { majCalques(); if (etatCatalogue === "echec") chargerModeles(); }
    // t193 : le « ? » de la fiche didactique de « Générer » — l'encart n'observe que les panneaux de droite, pas #stage
    if (VL.didact && typeof VL.didact.poserQ === "function") VL.didact.poserQ();
    const p = $("#iacPrompt");
    if (p) p.focus();
  }
  function fermer() {
    const el = $("#iaCalqueDlg");
    if (!el || el.hidden) return;
    el.hidden = true;
    if (retour && retour.isConnected && typeof retour.focus === "function") retour.focus();
    retour = null;
  }
  // la liste suit le document (calque ajouté, renommé, verrouillé, masqué, supprimé)
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { if (suivantRendu) suivantRendu(); if (ouvert()) majCalques(); };

  // un PNG déposé en Bibliothèque par la route d'import (gratuite) : le nom rendu, ou une erreur lisible
  async function deposerFichier(blob, nom, cle) {
    const fd = new FormData();
    fd.append("file", new File([blob], nom, { type: "image/png" }));
    const u = await chercher("/api/images/upload", { method: "POST", body: fd, cache: "no-store" });
    const d = await u.json().catch(() => ({}));
    if (!u.ok) throw new Error(messageErreur(u.status, d, u.statusText));
    return nomDuDepot(d, cle);
  }

  /* ── « Retirer le fond » du panneau Image ── */
  async function versBiblio(o) {
    const r = await chercher(VL.imageUrl(o.href, o.rev, o.px), { cache: "no-store" });
    if (!r.ok) throw new Error(T("vectorlab.iacalque.image_illisible", { href: o.href }));
    return deposerFichier(await r.blob(), nomDepot(etat.docId, o.href));
  }
  async function deposer(nom) {
    const r = await chercher("/api/images/" + encodeURIComponent(nom), { cache: "no-store" });
    if (!r.ok) throw new Error(T("vectorlab.image.biblio_introuvable", { nom, status: r.status }));
    return VL.deposerBlob(await r.blob());
  }
  // le bouton du panneau Image : son état suit le vol, et il est REDESSINÉ à la fin (le panneau a pu être rendu
  // pendant le vol — executer → surRendu — avec « en cours… »). Seule pose de son icône et de son libellé :
  // ligneDetour lui passe le bouton qu'elle vient de créer
  function majBoutonDetour(b = $("#imDetourer")) {
    if (!b) return;
    b.disabled = detourer.enVol;
    b.innerHTML = dzi("dz-action-detourer", 16) + (detourer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.retirer_fond"));
  }
  // la barre d'options mesure la boîte de l'objet À L'ÉCRAN : rendue avant que la nouvelle image ne soit chargée,
  // elle se trompait (X −146 au lieu de 0, preuve 8799) — on la remesure au chargement de chaque image sélectionnée
  function remesurer() {
    for (const id of etat.selection || []) {
      const g = document.querySelector(`#canvasHost [data-objet="${String(id).replace(/"/g, "")}"]`);
      const im = g && (g.tagName && g.tagName.toLowerCase() === "image" ? g : g.querySelector("image"));
      if (im) im.addEventListener("load", () => { if (VL.surSelection) VL.surSelection(); }, { once: true });
    }
  }
  const detourer = C.unSeulVol(async (o, c) => {
    const href = await retirerFondFlux(o, c, { doc: () => etat.doc, versBiblio, post: poster, deposer, executer: VL.executer });
    remesurer();
    return href;
  }, () => majBoutonDetour());
  // Annuler / Refaire du détourage : la même remesure
  const suivantHisto = VL.surHistorique;
  VL.surHistorique = () => { if (suivantHisto) suivantHisto(); remesurer(); };

  // le sujet tapé, par image : la ligne est reconstruite à chaque rendu du panneau Image
  const sujets = new Map();
  // le prix du détourage par modèle (devis serveur) : la PROMESSE est gardée (un devis en vol n'est pas redemandé, le
  // même chiffre avant et après le rendu, sans clignoter) ; un échec n'est pas gardé, mais n'est relu qu'après 30 s
  // (pas une requête à chaque rendu). On n'écrit que dans une ligne encore affichée, pour le modèle encore choisi.
  const prixDetour = new Map(), echecPrix = new Map();
  function prixDe(modele) {
    if (prixDetour.has(modele)) return prixDetour.get(modele);
    if (Date.now() - (echecPrix.get(modele) || -Infinity) < 30000) return Promise.reject(new Error("devis"));
    const p = poster("/api/cost/estimate", devisDetour(modele)).then(libellePrix);
    prixDetour.set(modele, p);
    p.catch(() => { prixDetour.delete(modele); echecPrix.set(modele, Date.now()); });
    return p;
  }
  async function majPrixDetour(span, sel) {
    const modele = sel.value;
    if (!modele) { span.textContent = ""; return; }
    span.textContent = T("vectorlab.iacalque.prix_inconnu");
    let t;
    try { t = await prixDe(modele); } catch (e) { t = T("vectorlab.iacalque.prix_inconnu"); }
    if (span.isConnected && sel.value === modele) span.textContent = t;
  }

  function ligneDetour(ligne, o) {
    ligne.innerHTML = `<span>${T("vectorlab.iacalque.fond")}</span>
      <select id="imDetourModele" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select>
      <button id="imDetourer" title="${T("vectorlab.iacalque.retirer_fond_titre")}"></button>
      <span class="iac-prix" id="imDetourPrix"></span>
      <input type="text" id="imDetourSujet" class="iac-sujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>`;
    const sel = ligne.querySelector("#imDetourModele"), sujet = ligne.querySelector("#imDetourSujet");
    const prix = ligne.querySelector("#imDetourPrix");
    sujet.value = sujets.get(o.id) || "";
    let mods = [];
    const maj = () => { sujet.hidden = !sujetRequis(mods, sel.value); majPrixDetour(prix, sel); };
    majBoutonDetour(ligne.querySelector("#imDetourer"));
    const M = MI();
    if (M) {
      catalogue("detourage_image").then((l) => {
        mods = l;
        if (sel.isConnected) { M.remplir(sel, l, { valeur: lire("dz_vl_iac_detour") }); maj(); }
      }).catch(() => { /* sans catalogue : le bouton refusera (aucun modèle) */ });
    }
    sel.addEventListener("change", () => { ecrire("dz_vl_iac_detour", sel.value); maj(); });
    sujet.addEventListener("input", () => sujets.set(o.id, sujet.value));
    ligne.querySelector("#imDetourer").addEventListener("click", async () => {
      if (detourer.enVol) return;
      // mêmes refus gratuits que le tir : modèle, clé, sujet — avant tout envoi (pas de case ici : sansCase)
      try { verifierDetour({ detourer: true, modeleDetour: sel.value, sujet: sujet.value }, infoDe(mods, sel.value), { sansCase: true }); }
      catch (e) { VL.toast(e.message, true); return; }
      VL.toast(T("vectorlab.iacalque.detour_en_cours"));
      try {
        const p = detourer(o, { modele: sel.value, sujet: sujet.value });
        majBoutonDetour();
        const r = await p;
        if (r) VL.toast(T("vectorlab.iacalque.detour_fait"));
      } catch (e) { VL.toast(e.message, true); }
    });
  }

  VL.iaCalque = { ouvrir, fermer, ligneDetour };
}
