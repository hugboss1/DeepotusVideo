// mod-exports.js — t257 (M8, photocraft 0.10) : exports en lot vers la Bibliothèque et Image › Variables.
// Fichier › Exporter › Calques en fichiers… (/calques/fichiers : doc.exportLayers) et Jeux de données en fichiers…
// (/jeux/fichiers : doc.exportDataSets) — les fichiers arrivent dans la Bibliothèque, jamais dans un dossier choisi ;
// Fichier › Importer › Jeux de données variables… (/jeux/importer : un CSV lu par l'écran, envoyé en texte) ;
// Image › Variables › Définir… / Jeux de données… et Image › Appliquer un jeu de données… (commandes moteur vérifiées
// clé par clé par le pont : visibilité et remplacement de texte ; le remplacement de PIXELS prend un chemin de fichier,
// il n'est pas proposé). Règles PURES exportées (qa/exports-m8.test.mjs).

import { brut } from "./mod-cycle.js";
import { ouvrirDialogue, nomDocument } from "./mod-fichier.js";

export const FORMATS_LOT = ["png", "jpg"];                   // ce que la Bibliothèque reçoit (_format_lot du pont)
export const TYPES_VARIABLE = ["visibility", "textReplacement"];   // TYPES_VARIABLE du registre (pont)
export const MAX_NOM_VARIABLE = 64, MAX_NOM_JEU = 255, MAX_TEXTE_JEU = 4000, MAX_VARIABLES = 200, MAX_JEUX = 500;
export const CSV_MAX = 1024 * 1024;
export const SEPARATEURS = { virgule: ",", point_virgule: ";", tabulation: "\t" };

function erreurSaisie(cle, vars) { const e = new Error(cle); e.cle = cle; e.vars = vars; return e; }
const qualite = (q) => Math.max(1, Math.min(100, Math.round(Number(q) || 90)));
const uneLigne = (s, n) => typeof s === "string" && s.trim().length > 0 && s.length <= n && !/[\x00-\x1f]/.test(s);

// Calques en fichiers : formulaire -> corps de /calques/fichiers.
export function corpsCalquesFichiers(form) {
  if (!FORMATS_LOT.includes(form.format)) throw erreurSaisie("photolab.export.erreur.format");
  const corps = { format: form.format, visibles: form.visibles !== false, nom: String(form.nom || "").trim().slice(0, 80) };
  if (form.format === "jpg") corps.quality = qualite(form.quality);
  return corps;
}

// Jeux de données en fichiers : `choisis` = les noms cochés ; tous cochés -> aucune liste (le moteur les prend tous).
export function corpsJeuxFichiers(form, tous, choisis) {
  if (!FORMATS_LOT.includes(form.format)) throw erreurSaisie("photolab.export.erreur.format");
  if (!choisis.length) throw erreurSaisie("photolab.jeux.erreur.aucun");
  const corps = { format: form.format, nom: String(form.nom || "").trim().slice(0, 80) };
  if (form.format === "jpg") corps.quality = qualite(form.quality);
  if (choisis.length < tous.length) corps.jeux = choisis.slice();
  return corps;
}

// Les calques qu'une variable peut viser (à plat, dans l'ordre du panneau) ; `texte` : un calque de texte.
export function calquesVariables(layers) {
  const plat = (l) => (l || []).flatMap((x) => [x, ...plat(x.children)]);
  return plat(layers).filter((c) => Number.isInteger(c.id)).map((c) => ({ id: c.id, nom: c.name || "", texte: c.kind === "Type" }));
}

// Lignes du dialogue Définir -> `defs` d'image.variables.define. Un nom par variable, unique ; le remplacement de
// texte seulement sur un calque de texte (le moteur l'accepterait ailleurs, sans effet).
export function defsDe(lignes, calques) {
  if (lignes.length > MAX_VARIABLES) throw erreurSaisie("photolab.variables.erreur.trop");
  const vus = new Set();
  return lignes.map((l) => {
    const nom = String(l.nom || "").trim();
    if (!uneLigne(nom, MAX_NOM_VARIABLE)) throw erreurSaisie("photolab.variables.erreur.nom");
    if (vus.has(nom)) throw erreurSaisie("photolab.variables.erreur.double", { nom });
    vus.add(nom);
    const c = calques.find((x) => x.id === Number(l.calque));
    if (!c) throw erreurSaisie("photolab.variables.erreur.calque");
    if (!TYPES_VARIABLE.includes(l.type)) throw erreurSaisie("photolab.variables.erreur.type");
    if (l.type === "textReplacement" && !c.texte) throw erreurSaisie("photolab.variables.erreur.texte", { nom });
    return { name: nom, layer: c.id, type: l.type };
  });
}

// Sorte de valeur d'un jeu selon le type de la variable.
export const sorteDe = (type) => (type === "textReplacement" ? "text" : type === "visibility" ? "visibility" : null);

// Lignes du dialogue Jeux de données -> `dataSets` d'image.variables.dataSets (variables de `defs` seulement ; une
// valeur absente = la variable n'est pas touchée par ce jeu).
export function jeuxDe(lignes, defs) {
  if (lignes.length > MAX_JEUX) throw erreurSaisie("photolab.jeux.erreur.trop");
  const vus = new Set();
  return lignes.map((l) => {
    const nom = String(l.nom || "").trim();
    if (!uneLigne(nom, MAX_NOM_JEU)) throw erreurSaisie("photolab.jeux.erreur.nom");
    if (vus.has(nom)) throw erreurSaisie("photolab.jeux.erreur.double", { nom });
    vus.add(nom);
    const values = [];
    for (const d of defs) {
      const sorte = sorteDe(d.type);
      if (!sorte || !(d.name in (l.valeurs || {}))) continue;
      let v = l.valeurs[d.name];
      if (sorte === "visibility") v = !!v;
      else {
        v = String(v == null ? "" : v);
        if (v.length > MAX_TEXTE_JEU) throw erreurSaisie("photolab.jeux.erreur.texte", { nom });
      }
      values.push({ variable: d.name, kind: sorte, value: v });
    }
    return { name: nom, values };
  });
}

// Jeux lus du moteur (variables.list) -> lignes du dialogue.
export function lignesDeJeux(dataSets) {
  return (dataSets || []).map((j) => ({ nom: j.name || "", valeurs: Object.fromEntries((j.values || []).map((v) => [v.variable, v.value])) }));
}

// Séparateur d'un CSV deviné sur sa première ligne : tabulation, puis point-virgule, sinon virgule.
export function separateurDe(texte) {
  const premiere = String(texte || "").split(/\r?\n/, 1)[0];
  if (premiere.includes("\t")) return "\t";
  return (premiere.match(/;/g) || []).length > (premiere.match(/,/g) || []).length ? ";" : ",";
}

/* ───────────── côté DOM ───────────── */

export function initExports(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.actions = PL.actions || {};

  const champ = (libelle, el) => {
    const l = document.createElement("label"); l.className = "pl-champ";
    const s = document.createElement("span"); s.textContent = libelle;
    l.append(s, el);
    return l;
  };
  const liste = (options, valeur) => {
    const sel = document.createElement("select");
    for (const [v, lib, isBrut] of options) {
      const o = document.createElement("option"); o.value = v; o.textContent = lib; if (isBrut) brut(o); sel.appendChild(o);
    }
    if (valeur !== undefined) sel.value = valeur;
    return sel;
  };
  const saisie = (valeur, attrs = {}) => {
    const i = document.createElement("input"); i.type = attrs.type || "text"; i.value = valeur;
    for (const [k, v] of Object.entries(attrs)) if (k !== "type") i.setAttribute(k, v);
    return i;
  };
  const caseACocher = (coche) => { const i = document.createElement("input"); i.type = "checkbox"; i.checked = !!coche; return i; };
  const bouton = (cle, classe = "") => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pl-bouton " + classe; b.textContent = T(cle); return b;
  };
  const zoneErreur = () => { const p = document.createElement("p"); p.className = "pl-erreur"; p.setAttribute("role", "alert"); return p; };
  const messageDe = (e) => (e && e.cle ? T(e.cle, e.vars) : (e && e.message) || "");

  async function lireVariables() {
    try { return await PL.post("/executer", { command: "variables.list", params: {} }); }      // lecture : aucun état
    catch (e) { return null; }
  }

  // Format, qualité (jpg), nom : le haut commun des deux exports en lot.
  function hautLot(corps, nomDefaut) {
    const format = liste(FORMATS_LOT.map((f) => [f, f.toUpperCase()]), "png");
    const q = saisie("90", { type: "range", min: "1", max: "100", step: "1" });
    const vq = document.createElement("span"); vq.className = "pl-unite"; vq.textContent = "90";
    q.addEventListener("input", () => { vq.textContent = q.value; });
    const lq = champ(T("photolab.export.qualite"), q); lq.appendChild(vq);
    const maj = () => { lq.hidden = format.value !== "jpg"; };
    format.addEventListener("change", maj); maj();
    const nom = brut(saisie(nomDefaut, { maxlength: "80" }));
    corps.append(champ(T("photolab.export.format"), format), lq, champ(T("photolab.nouveau.nom"), nom));
    return () => ({ format: format.value, quality: q.value, nom: nom.value });
  }

  function deposes(r) {
    const n = (r && r.filenames ? r.filenames.length : 0);
    PL.signaler(T("photolab.lot.depose", { n }));
  }

  /* ── Fichier › Exporter › Calques en fichiers… ── */
  async function calquesFichiers() {
    const doc = PL.etat.doc;
    if (!doc) return;
    let r = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.calques_fichiers.titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.exporter"), principal: true }],
      construire({ corps }) {
        const intro = document.createElement("p"); intro.className = "pl-note"; intro.textContent = T("photolab.lot.vers_biblio");
        corps.appendChild(intro);
        const lire = hautLot(corps, nomDocument(doc.name));
        const visibles = caseACocher(true);
        corps.appendChild(champ(T("photolab.calques_fichiers.visibles"), visibles));
        const erreur = zoneErreur(); corps.appendChild(erreur);
        return async () => {
          try { r = await PL.file(() => PL.post("/calques/fichiers", corpsCalquesFichiers({ ...lire(), visibles: visibles.checked }))); }
          catch (e) { erreur.textContent = messageDe(e); return false; }
          return true;
        };
      },
    });
    if (r) deposes(r);
  }

  /* ── Fichier › Exporter › Jeux de données en fichiers… ── */
  async function jeuxFichiers() {
    const doc = PL.etat.doc;
    if (!doc) return;
    const v = await lireVariables();
    const tous = ((v && v.dataSets) || []).map((j) => j.name);
    if (!tous.length) { PL.signaler(T("photolab.jeux.aucun"), true); return; }
    let r = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.jeux_fichiers.titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.exporter"), principal: true }],
      construire({ corps }) {
        const intro = document.createElement("p"); intro.className = "pl-note"; intro.textContent = T("photolab.lot.vers_biblio");
        corps.appendChild(intro);
        const lire = hautLot(corps, nomDocument(doc.name));
        const boite = document.createElement("div"); boite.className = "pl-jeux-choix";
        const cases = tous.map((nom) => {
          const c = caseACocher(true);
          const l = document.createElement("label"); l.className = "pl-case";
          const s = brut(document.createElement("span")); s.textContent = nom;
          l.append(c, s); boite.appendChild(l);
          return [nom, c];
        });
        corps.appendChild(champ(T("photolab.jeux_fichiers.jeux"), boite));
        const erreur = zoneErreur(); corps.appendChild(erreur);
        return async () => {
          try {
            const choisis = cases.filter(([, c]) => c.checked).map(([n]) => n);
            r = await PL.file(() => PL.post("/jeux/fichiers", corpsJeuxFichiers(lire(), tous, choisis)));
          } catch (e) { erreur.textContent = messageDe(e); return false; }
          return true;
        };
      },
    });
    if (r) deposes(r);
  }

  /* ── Fichier › Importer › Jeux de données variables… : un CSV de l'ordinateur, lu ici, envoyé en texte ── */
  function importerJeux() {
    if (!PL.etat.doc) return;
    const i = document.createElement("input");
    i.type = "file"; i.accept = ".csv,.txt,.tsv"; i.hidden = true;
    i.addEventListener("change", async () => {
      const f = i.files && i.files[0]; i.remove();
      if (!f) return;
      if (f.size > CSV_MAX) { PL.signaler(T("photolab.jeux.csv_lourd"), true); return; }
      const texte = await f.text();
      let r;
      try { r = await PL.file(() => PL.post("/jeux/importer", { csv: texte, separateur: separateurDe(texte) })); } catch (e) { return; }
      PL.signaler(T("photolab.jeux.importes", { n: r.imported || 0 }));
    });
    document.body.appendChild(i);
    i.click();
  }

  /* ── Image › Variables › Définir… ── */
  async function definir() {
    const doc = PL.etat.doc;
    if (!doc) return;
    const v = await lireVariables();
    if (!v) return;
    const calques = calquesVariables(doc.layers);
    let defs = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.variables.titre"), classe: "large",
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const note = document.createElement("p"); note.className = "pl-note"; note.textContent = T("photolab.variables.note");
        const table = document.createElement("div"); table.className = "pl-variables";
        const lignes = [];
        const ajouter = (d = {}) => {
          const ligne = document.createElement("div"); ligne.className = "pl-variable";
          const cal = liste(calques.map((c) => [String(c.id), c.nom, true]), String(d.layer != null ? d.layer : (calques[0] || {}).id));
          const type = liste(TYPES_VARIABLE.map((t) => [t, T("photolab.variables.type." + t.toLowerCase())]), d.type || "visibility");
          const nom = brut(saisie(d.name || "", { maxlength: String(MAX_NOM_VARIABLE), placeholder: T("photolab.variables.nom") }));
          const oter = bouton("commun.action.supprimer", "pl-variable-oter");
          const l = { ligne, lire: () => ({ calque: cal.value, type: type.value, nom: nom.value }) };
          oter.addEventListener("click", () => { ligne.remove(); lignes.splice(lignes.indexOf(l), 1); });
          ligne.append(cal, type, nom, oter);
          table.appendChild(ligne); lignes.push(l);
        };
        for (const d of v.defs || []) if (TYPES_VARIABLE.includes(d.type)) ajouter(d);
        const plus = bouton("photolab.variables.ajouter", "pl-variable-ajouter");
        plus.addEventListener("click", () => ajouter());
        const erreur = zoneErreur();
        corps.append(note, table, plus, erreur);
        return () => {
          try { defs = defsDe(lignes.map((l) => l.lire()), calques); } catch (e) { erreur.textContent = messageDe(e); return false; }
          return true;
        };
      },
    });
    if (defs) {
      const r = await PL.executer("image.variables.define", { defs });
      if (r.ok) PL.signaler(T("photolab.variables.fait", { n: defs.length }));
    }
  }

  /* ── Image › Variables › Jeux de données… ── */
  async function jeux() {
    if (!PL.etat.doc) return;
    const v = await lireVariables();
    if (!v) return;
    const defs = (v.defs || []).filter((d) => sorteDe(d.type));
    if (!defs.length) { PL.signaler(T("photolab.variables.aucune"), true); return; }
    let dataSets = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.jeux.titre"), classe: "large",
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const table = document.createElement("div"); table.className = "pl-jeux";
        const tete = document.createElement("div"); tete.className = "pl-jeu pl-jeu-tete";
        const tNom = document.createElement("span"); tNom.textContent = T("photolab.jeux.nom"); tete.appendChild(tNom);
        for (const d of defs) { const s = brut(document.createElement("span")); s.textContent = d.name; tete.appendChild(s); }
        tete.appendChild(document.createElement("span"));
        table.appendChild(tete);
        const lignes = [];
        const ajouter = (l = { nom: "", valeurs: {} }) => {
          const ligne = document.createElement("div"); ligne.className = "pl-jeu";
          const nom = brut(saisie(l.nom, { maxlength: String(MAX_NOM_JEU) }));
          ligne.appendChild(nom);
          const els = defs.map((d) => {
            const el = sorteDe(d.type) === "visibility" ? caseACocher(d.name in l.valeurs ? l.valeurs[d.name] : true)
              : brut(saisie(d.name in l.valeurs ? String(l.valeurs[d.name]) : "", { maxlength: String(MAX_TEXTE_JEU) }));
            ligne.appendChild(el);
            return [d.name, el];
          });
          const oter = bouton("commun.action.supprimer", "pl-jeu-oter");
          const x = { lire: () => ({ nom: nom.value, valeurs: Object.fromEntries(els.map(([n, el]) => [n, el.type === "checkbox" ? el.checked : el.value])) }) };
          oter.addEventListener("click", () => { ligne.remove(); lignes.splice(lignes.indexOf(x), 1); });
          ligne.appendChild(oter);
          table.appendChild(ligne); lignes.push(x);
        };
        for (const l of lignesDeJeux(v.dataSets)) ajouter(l);
        if (!lignes.length) ajouter({ nom: T("photolab.jeux.premier"), valeurs: {} });
        const plus = bouton("photolab.jeux.ajouter", "pl-jeu-ajouter");
        plus.addEventListener("click", () => ajouter({ nom: "", valeurs: {} }));
        const erreur = zoneErreur();
        corps.append(table, plus, erreur);
        return () => {
          try { dataSets = jeuxDe(lignes.map((l) => l.lire()), defs); } catch (e) { erreur.textContent = messageDe(e); return false; }
          return true;
        };
      },
    });
    if (dataSets) {
      const r = await PL.executer("image.variables.dataSets", { dataSets, append: false });
      if (r.ok) PL.signaler(T("photolab.jeux.fait", { n: dataSets.length }));
    }
  }

  /* ── Image › Appliquer un jeu de données… (un état d'historique) ── */
  async function appliquer() {
    if (!PL.etat.doc) return;
    const v = await lireVariables();
    const tous = ((v && v.dataSets) || []).map((j) => j.name);
    if (!tous.length) { PL.signaler(T("photolab.jeux.aucun"), true); return; }
    let nom = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.jeux.appliquer"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.appliquer"), principal: true }],
      construire({ corps }) {
        const sel = liste(tous.map((n) => [n, n, true]), v.active != null && tous[v.active] ? tous[v.active] : tous[0]);
        corps.appendChild(champ(T("photolab.jeux.nom"), sel));
        return () => { nom = sel.value; return true; };
      },
    });
    if (nom) await PL.executer("image.applyDataSet", { name: nom });
  }

  Object.assign(PL.actions, {
    "file.export.layersToFiles": calquesFichiers, "file.export.dataSetsAsFiles": jeuxFichiers,
    "file.import.variableDataSets": importerJeux, "image.variables.define": definir, "image.variables.dataSets": jeux,
    "image.applyDataSet": appliquer,
  });
}
