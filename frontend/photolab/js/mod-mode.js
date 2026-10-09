// mod-mode.js — t158 (parité L8) : Image › Mode. Le pont rouvre les 12 conversions une à une (PERMIS_REFUSES), profil
// limité aux profils INTÉGRÉS. Conversions directes (profil de travail, comme la référence) ; confirmation quand la
// conversion aplatit un document à plusieurs calques ; coches du mode et de la profondeur ; Bitmap et Couleurs indexées
// = formulaire du registre ; Bichromie (type + encres) et Table des couleurs = éditeurs. Le grisé vient du moteur
// (engine.commands.enabled : Bitmap et Bichromie exigent Niveaux de gris, la Table exige Couleurs indexées).
// Règles PURES exportées (qa/mode.test.mjs).

import { compterCalques } from "./mod-cycle.js";
import { ouvrirDialogue } from "./mod-fichier.js";

const P = "image.mode.";
// mode de doc.inspect -> entrée cochée
export const MODES = { Rgb: P + "rgb", Grayscale: P + "grayscale", Cmyk: P + "cmyk", Lab: P + "lab", Indexed: P + "indexedColor",
  Bitmap: P + "bitmap", Duotone: P + "duotone", Multichannel: P + "multichannel" };
export const PROFONDEURS = { 8: P + "bits8", 16: P + "bits16", 32: P + "bits32" };
// Conversions sans dialogue (profil de travail du moteur) ; le registre décrit leurs options, la référence les range
// dans « Convertir en profil ».
export const DIRECTES = new Set([P + "rgb", P + "grayscale", P + "cmyk", P + "lab", P + "multichannel", P + "bits8", P + "bits16", P + "bits32"]);
// Le registre le dit (« flattens ») et le moteur le fait.
export const APLATISSENT = new Set([P + "bitmap", P + "indexedColor", P + "multichannel"]);
export const ENCRES_PAR_TYPE = { monotone: 1, duotone: 2, tritone: 3, quadtone: 4 };     // ENCRES_PAR_TYPE du pont
export const TABLES = ["custom", "blackBody", "grayscale", "spectrum", "systemMac", "systemWindows", "web"];
// Encres de départ (noms traduits par l'écran ; l'utilisateur les renomme).
export const ENCRES_DEFAUT = [
  { cle: "photolab.bichromie.encre.noir", color: "#000000" },
  { cle: "photolab.bichromie.encre.brun", color: "#8b5a2b" },
  { cle: "photolab.bichromie.encre.or", color: "#d4a017" },
  { cle: "photolab.bichromie.encre.bleu", color: "#1f4e79" },
];
const HEX = /^#[0-9a-f]{6}$/i;
const MAX_NOM_ENCRE = 64;

function erreurSaisie(cle) { const e = new Error(cle); e.cle = cle; return e; }

// Coches : le mode du document et sa profondeur (la Table des couleurs n'en a pas).
export function cochesMode(doc) {
  const s = new Set();
  if (!doc) return s;
  if (MODES[doc.mode]) s.add(MODES[doc.mode]);
  if (PROFONDEURS[doc.depth]) s.add(PROFONDEURS[doc.depth]);
  return s;
}

export function decorerMode(menus, doc) {
  if (!doc) return menus;
  const coches = cochesMode(doc);
  const voir = (l) => l.map((e) => {
    if (e.type === "sous-menu") return { ...e, entrees: voir(e.entrees) };
    if (e.type === "commande" && e.id !== P + "colorTable" && (Object.values(MODES).includes(e.id) || Object.values(PROFONDEURS).includes(e.id))) {
      return { ...e, coche: coches.has(e.id) };
    }
    return e;
  });
  return menus.map((m) => ({ ...m, entrees: voir(m.entrees) }));
}

// Faut-il prévenir que la conversion aplatit ? (un seul calque : rien à perdre)
export function doitConfirmerAplatir(id, doc) {
  return APLATISSENT.has(id) && !!doc && compterCalques(doc.layers) > 1;
}

// Formulaire de la Bichromie -> paramètres du moteur : EXACTEMENT autant d'encres que le type (le moteur complète ou
// tronque en silence), nom 1..64, couleur #rrggbb ; courbes linéaires (non envoyées).
export function paramsBichromie(type, encres) {
  const n = ENCRES_PAR_TYPE[type];
  if (!n) throw erreurSaisie("photolab.bichromie.erreur.type");
  const l = (Array.isArray(encres) ? encres : []).slice(0, n);
  if (l.length !== n) throw erreurSaisie("photolab.bichromie.erreur.encres");
  return {
    type,
    inks: l.map((e) => {
      const name = String(e.name || "").trim();
      if (!name || name.length > MAX_NOM_ENCRE) throw erreurSaisie("photolab.bichromie.erreur.nom");
      if (!HEX.test(String(e.color || ""))) throw erreurSaisie("photolab.bichromie.erreur.couleur");
      return { name, color: String(e.color).toLowerCase() };
    }),
  };
}

// Table des couleurs : un préréglage remplace la table ; sinon seules les cases CHANGÉES partent (entries), plus la
// transparence si elle a changé. Rien de changé -> null (aucune étape).
export function paramsTable(avant, apres, prereglage = "custom") {
  if (prereglage !== "custom") {
    if (!TABLES.includes(prereglage)) throw erreurSaisie("photolab.table.erreur.prereglage");
    return { table: prereglage };
  }
  const a = (avant && avant.colors) || [], b = (apres && apres.colors) || [];
  const entries = {};
  b.forEach((c, i) => { if (i < 256 && HEX.test(c) && String(c).toLowerCase() !== String(a[i] || "").toLowerCase()) entries[String(i)] = c.toLowerCase(); });
  const out = {};
  if (Object.keys(entries).length) out.entries = entries;
  const ta = avant && avant.transparent != null ? avant.transparent : null;
  const tb = apres && apres.transparent != null ? apres.transparent : null;
  if (ta !== tb) out.transparent = tb;
  return Object.keys(out).length ? out : null;
}

/* ───────────── côté DOM ───────────── */

export function initMode(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);

  async function confirmer(question, titre, ok) {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, { titre, ok });
    return (await ouvrirDialogue(PL, {
      titre,
      construire({ corps }) { const p = document.createElement("p"); p.textContent = question; corps.appendChild(p); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: ok, principal: true }],
    })) === "ok";
  }

  PL.ouvrirMode = async function ouvrirMode(entree) {
    const id = entree && entree.id;
    if (!id || !PL.etat.doc) return;
    if (doitConfirmerAplatir(id, PL.etat.doc)
      && !(await confirmer(T("photolab.mode.aplatir_question"), T("photolab.mode.aplatir_titre"), T("photolab.mode.aplatir_ok")))) return;
    if (DIRECTES.has(id)) { await PL.executer(id, {}); return; }
    if (id === P + "duotone") return bichromie();
    if (id === P + "colorTable") return tableCouleurs();
    return PL.ouvrirReglage(entree);                     // Bitmap, Couleurs indexées : formulaire du registre
  };

  async function bichromie() {
    let params = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.bichromie.titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const type = document.createElement("select");
        for (const t of Object.keys(ENCRES_PAR_TYPE)) { const o = document.createElement("option"); o.value = t; o.textContent = T("photolab.bichromie.type." + t); type.appendChild(o); }
        type.value = "duotone";
        const lType = document.createElement("label"); lType.className = "pl-champ";
        const sType = document.createElement("span"); sType.textContent = T("photolab.bichromie.type"); lType.append(sType, type);
        const zone = document.createElement("div"); zone.className = "pl-encres";
        const encres = ENCRES_DEFAUT.map((e) => ({ name: T(e.cle), color: e.color }));
        const lignes = [];
        encres.forEach((e, i) => {
          const l = document.createElement("div"); l.className = "pl-encre"; l.dataset.encre = String(i);
          const n = document.createElement("span"); n.className = "pl-encre-num"; n.textContent = T("photolab.bichromie.encre", { n: i + 1 });
          const c = document.createElement("input"); c.type = "color"; c.value = e.color; c.setAttribute("aria-label", T("photolab.bichromie.couleur"));
          const nom = document.createElement("input"); nom.type = "text"; nom.value = e.name; nom.maxLength = MAX_NOM_ENCRE;
          nom.setAttribute("data-dz-brut", "1"); nom.setAttribute("aria-label", T("photolab.bichromie.nom"));
          c.addEventListener("input", () => { encres[i].color = c.value; });
          nom.addEventListener("input", () => { encres[i].name = nom.value; });
          l.append(n, c, nom); zone.appendChild(l); lignes.push(l);
        });
        const note = document.createElement("p"); note.className = "pl-note"; note.textContent = T("photolab.bichromie.note");
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        const maj = () => lignes.forEach((l, i) => { l.hidden = i >= ENCRES_PAR_TYPE[type.value]; });
        type.addEventListener("change", maj); maj();
        corps.append(lType, zone, note, erreur);
        return () => {
          try { params = paramsBichromie(type.value, encres); } catch (e) { erreur.textContent = T(e.cle); return false; }
          return true;
        };
      },
    });
    if (params) await PL.executer(P + "duotone", params);
  }

  async function tableCouleurs() {
    let avant;
    try { avant = await PL.file(() => PL.post("/executer", { command: P + "colorTable", params: {} })); } catch (e) { return; }   // lecture : aucune étape
    if (!avant || !Array.isArray(avant.colors)) return;
    const apres = { colors: avant.colors.slice(), transparent: avant.transparent == null ? null : avant.transparent };
    let prereglage = "custom";
    let params;
    const role = await ouvrirDialogue(PL, {
      titre: T("photolab.table.titre"), classe: "large",
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const sel = document.createElement("select");
        for (const t of TABLES) { const o = document.createElement("option"); o.value = t; o.textContent = T("photolab.table.prereglage." + t.toLowerCase()); sel.appendChild(o); }
        const lSel = document.createElement("label"); lSel.className = "pl-champ";
        const sSel = document.createElement("span"); sSel.textContent = T("photolab.table.table"); lSel.append(sSel, sel);
        const grille = document.createElement("div"); grille.className = "pl-table-grille"; grille.setAttribute("role", "grid");
        const choix = document.createElement("input"); choix.type = "color"; choix.hidden = true;
        const transp = document.createElement("label"); transp.className = "pl-champ pl-case";
        const kTransp = document.createElement("input"); kTransp.type = "checkbox";
        const sTransp = document.createElement("span"); sTransp.textContent = T("photolab.table.pipette_transparence");
        transp.append(kTransp, sTransp);
        const sansT = document.createElement("button"); sansT.type = "button"; sansT.className = "pl-bouton"; sansT.textContent = T("photolab.table.sans_transparence");
        const info = document.createElement("p"); info.className = "pl-note";
        let cible = -1;
        const dessiner = () => {
          grille.textContent = "";
          apres.colors.forEach((c, i) => {
            const b = document.createElement("button"); b.type = "button"; b.className = "pl-table-case" + (apres.transparent === i ? " transparente" : "");
            b.style.background = c; b.title = (i) + " · " + c; b.dataset.index = String(i);
            b.disabled = prereglage !== "custom";
            b.addEventListener("click", () => {
              if (kTransp.checked) { apres.transparent = i; kTransp.checked = false; dessiner(); return; }
              cible = i; choix.value = c; choix.click();
            });
            grille.appendChild(b);
          });
          info.textContent = T("photolab.table.compte", { n: apres.colors.length });
        };
        choix.addEventListener("input", () => { if (cible >= 0) { apres.colors[cible] = choix.value; dessiner(); } });
        sansT.addEventListener("click", () => { apres.transparent = null; dessiner(); });
        sel.addEventListener("change", () => { prereglage = sel.value; dessiner(); });
        dessiner();
        corps.append(lSel, grille, choix, transp, sansT, info);
        return () => { params = paramsTable(avant, apres, prereglage); return true; };
      },
    });
    if (role === "ok" && params) await PL.executer(P + "colorTable", params);
  }

  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => decorerMode(menus, PL.etat.doc));
}
