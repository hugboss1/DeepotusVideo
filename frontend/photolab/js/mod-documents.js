// mod-documents.js — t158 (parité L8) : les documents de la session et les entrées « Fichier sûr ».
// Onglets de TOUS les documents ouverts dans le moteur (clic = document.activate, × = fermer vraiment) ; Tout fermer,
// Fermer les autres ; Enregistrer une copie (/copie) ; Revenir (/revenir) ; Exportation rapide PNG ; Placer incorporé
// (/placer, depuis la Bibliothèque) ; Informations sur le fichier ; Calque › Exportation rapide / Exporter sous
// (/calque/exporter) ; listes de choix du dialogue générique (autre document, tracé). Le moteur désactive ses commandes
// à chemin : tout fichier passe par une route du pont. Règles PURES exportées (qa/documents.test.mjs).

import { brut } from "./mod-cycle.js";
import { ouvrirDialogue, nomDocument, aSauvegarder, FORMATS_EXPORT } from "./mod-fichier.js";

export const DOSSIERS_REVENIR = ["entrees/", "exports/", "biblio/", "natif/"];   // copie de DOSSIERS_REVENIR du pont
export const FORMATS_CALQUE = ["png", "jpg", "webp"];                          // FORMATS_CALQUE du pont
export const FORMATS_BIBLIO = ["png", "jpg"];
export const ECHELLE_MIN = 1, ECHELLE_MAX = 1000;
export const MAX_TEXTE_INFO = 2000, MAX_MOTS_CLES = 64, MAX_MOT_CLE = 64;      // bornes de _v_infos (pont)
export const STATUTS_COPYRIGHT = ["unknown", "copyrighted", "publicDomain"];
const QUALITE = (f) => f === "jpg" || f === "webp";

function erreurSaisie(cle) { const e = new Error(cle); e.cle = cle; return e; }

// Onglets : un par document de session.list, dans l'ordre du moteur. Le document actif dit « modifié » par l'écran
// (révision depuis le dernier enregistrement), les autres par le moteur (`dirty`).
export function ongletsDe(session, modifieActif) {
  const docs = (session && Array.isArray(session.documents)) ? session.documents : [];
  return docs.map((d) => {
    const actif = d.index === session.active;
    return { index: d.index, nom: nomDocument(d.name) || d.name || "", actif, modifie: actif ? !!modifieActif : !!d.dirty };
  });
}

// Documents modifiés que fermer perdrait : tous (garder = null) ou tous sauf `garder`.
export function aConfirmer(onglets, garder = null) {
  return onglets.filter((o) => o.modifie && o.index !== garder).map((o) => o.nom);
}

// Revenir n'a de sens qu'avec un fichier du moteur sous l'un des dossiers relus par le pont.
export function peutRevenir(chemin) {
  return typeof chemin === "string" && DOSSIERS_REVENIR.some((d) => chemin.startsWith(d)) && !chemin.includes("..");
}

// Liste de choix « document » : les autres documents ouverts (et le document actif si `avecActif`, en premier). Deux
// documents du même nom (la même image ouverte deux fois) sont départagés par leur rang : « herbe (1) », « herbe (2) ».
export function choixDocuments(session, avecActif, T = (k) => k) {
  const docs = (session && Array.isArray(session.documents)) ? session.documents : [];
  const nom = (d) => nomDocument(d.name) || d.name || "";
  const compte = {};
  for (const d of docs) compte[nom(d)] = (compte[nom(d)] || 0) + 1;
  const libelle = (d) => (compte[nom(d)] > 1 ? `${nom(d)} (${d.index + 1})` : nom(d));
  const autres = docs.filter((d) => d.index !== session.active).map((d) => ({ valeur: d.index, libelle: libelle(d) }));
  if (!avecActif) return autres;
  const a = docs.find((d) => d.index === session.active);
  return a ? [{ valeur: a.index, libelle: T("photolab.choix.ce_document", { nom: libelle(a) }) }, ...autres] : autres;
}

// Liste de choix « tracé » (Flamme) : aucun (toute la toile), le tracé de travail, les tracés enregistrés.
export function choixTraces(liste, T = (k) => k) {
  const out = [{ valeur: "", libelle: T("photolab.choix.aucun_trace") }];
  if (liste && liste.workPath) out.push({ valeur: "work", libelle: T("photolab.traces.travail") });
  for (const p of (liste && Array.isArray(liste.paths)) ? liste.paths : []) if (p && p.name) out.push({ valeur: p.name, libelle: p.name });
  return out;
}
// Défaut : le tracé de travail, sinon le premier enregistré, sinon aucun.
export function traceParDefaut(choix) {
  return (choix.find((c) => c.valeur === "work") || choix.find((c) => c.valeur !== "") || { valeur: "" }).valeur;
}

function qualite(v) { return Math.max(1, Math.min(100, Math.round(Number(v) || 90))); }

// Formulaire « Enregistrer une copie » -> corps de /copie.
// t159 : Préférences › Exportation — l'exportation rapide suit le format, la qualité JPG et le lieu choisis
// (« ask » : le dialogue Enregistrer une copie ; « library » : la Bibliothèque, PNG ou JPG seulement).
export function exportRapidePrefs(prefs) {
  const e = (prefs && prefs.export) || { quickExportFormat: "png", jpegQuality: 85, quickExportLocation: "download" };
  if (e.quickExportLocation === "ask") return { dialogue: true };
  const corps = { format: e.quickExportFormat };
  if (e.quickExportFormat === "jpg") corps.quality = e.jpegQuality;
  const biblio = e.quickExportLocation === "library" && FORMATS_BIBLIO.includes(e.quickExportFormat);
  return { route: biblio ? "/copie" : "/enregistrer", corps: biblio ? { ...corps, destination: "bibliotheque" } : corps };
}
// t159 : Gestion des fichiers › extension en minuscules (décochée : « image.PNG » au téléchargement).
export const nomTelecharge = (fichier, minuscules = true) => (minuscules ? fichier : String(fichier).replace(/\.([A-Za-z0-9]+)$/, (m, x) => "." + x.toUpperCase()));

export function corpsCopie(form) {
  const f = FORMATS_EXPORT.find((x) => x.format === form.format);
  if (!f) throw erreurSaisie("photolab.export.erreur.format");
  const destination = form.destination === "bibliotheque" ? "bibliotheque" : "telecharger";
  if (destination === "bibliotheque" && !FORMATS_BIBLIO.includes(f.format)) throw erreurSaisie("photolab.copie.erreur.biblio");
  const corps = { format: f.format, nom: String(form.nom || "").trim().slice(0, 80), destination };
  if (f.qualite) corps.quality = qualite(form.quality);
  return corps;
}

// Formulaire « Exporter sous » (calque) -> corps de /calque/exporter. Échelle entière stricte (« 12,5 » refusé).
export function corpsCalque(form) {
  if (!FORMATS_CALQUE.includes(form.format)) throw erreurSaisie("photolab.export.erreur.format");
  const s = String(form.echelle == null ? "100" : form.echelle).trim();
  const e = /^\d+$/.test(s) ? Number(s) : NaN;
  if (!(e >= ECHELLE_MIN && e <= ECHELLE_MAX)) throw erreurSaisie("photolab.calque_export.erreur.echelle");
  const destination = form.destination === "bibliotheque" ? "bibliotheque" : "telecharger";
  if (destination === "bibliotheque" && !FORMATS_BIBLIO.includes(form.format)) throw erreurSaisie("photolab.copie.erreur.biblio");
  const corps = { format: form.format, echelle: e, nom: String(form.nom || "").trim().slice(0, 80), destination };
  if (QUALITE(form.format)) corps.quality = qualite(form.quality);
  if (Number.isInteger(form.layer) && form.layer >= 0) corps.layer = form.layer;
  return corps;
}

// « a, b ; c » -> ["a", "b", "c"] (vides retirés, doublons gardés une fois).
export function motsCles(texte) {
  const vus = [];
  for (const m of String(texte || "").split(/[;,]/).map((x) => x.trim()).filter(Boolean)) if (!vus.includes(m)) vus.push(m);
  return vus;
}
export function urlValide(u) {
  return u === "" || /^https?:\/\/[^\s"'<>\\]{1,500}$/.test(String(u));
}

// Informations : seules les clés CHANGÉES partent au moteur (une étape « File Info » seulement s'il y en a). Lève une
// erreur de saisie (clé du dictionnaire) si une borne du pont serait dépassée.
export function infosModifiees(avant, form) {
  const a = avant || {};
  const sortie = {};
  for (const k of ["title", "author", "authorTitle", "description", "copyright"]) {
    const v = String(form[k] == null ? "" : form[k]);
    if (v.length > MAX_TEXTE_INFO) throw erreurSaisie("photolab.infos.erreur.long");
    if (v !== String(a[k] == null ? "" : a[k])) sortie[k] = v;
  }
  const mots = motsCles(form.keywords);
  if (mots.length > MAX_MOTS_CLES || mots.some((m) => m.length > MAX_MOT_CLE)) throw erreurSaisie("photolab.infos.erreur.mots");
  if (JSON.stringify(mots) !== JSON.stringify(Array.isArray(a.keywords) ? a.keywords : [])) sortie.keywords = mots;
  if (STATUTS_COPYRIGHT.includes(form.copyrightStatus) && form.copyrightStatus !== (a.copyrightStatus || "unknown")) sortie.copyrightStatus = form.copyrightStatus;
  const u = String(form.copyrightUrl == null ? "" : form.copyrightUrl).trim();
  if (!urlValide(u)) throw erreurSaisie("photolab.infos.erreur.url");
  if (u !== String(a.copyrightUrl || "")) sortie.copyrightUrl = u;
  return sortie;
}

// États des entrées selon la session : Fermer les autres sans autre document, Revenir sans fichier -> inactives.
export function decorerDocuments(menus, o) {
  const voir = (l) => l.map((e) => {
    if (e.type === "sous-menu") return { ...e, entrees: voir(e.entrees) };
    if (e.type !== "commande") return e;
    if (e.id === "file.closeOthers" && !(o.nbDocs > 1)) return { ...e, etat: "inactif" };
    if (e.id === "file.revert" && !peutRevenir(o.chemin)) return { ...e, etat: "inactif" };
    return e;
  });
  return menus.map((m) => ({ ...m, entrees: voir(m.entrees) }));
}

/* ───────────── côté DOM ───────────── */

export function initDocuments(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.etat.session = null;
  let jeton = 0;

  const modifieActif = () => aSauvegarder(PL.etat.doc, PL.etat.revEnregistree, PL.etat.revOuverture);
  const actifDeSession = () => {
    const s = PL.etat.session;
    return s && Array.isArray(s.documents) ? s.documents.find((d) => d.index === s.active) || null : null;
  };

  async function relireSession() {
    const n = ++jeton;
    let s = null;
    try { s = await PL.get("/session", true); } catch (e) { s = null; }
    if (n !== jeton) return;
    PL.etat.session = s;
    dessiner();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  }
  PL.relireSession = relireSession;

  /* ── onglets ── */
  function dessiner() {
    const zone = PL.$("#onglets");
    if (!zone) return;
    zone.textContent = "";
    if (!PL.etat.doc) return;
    const s = PL.etat.session;
    const liste = s ? ongletsDe(s, modifieActif()) : [{ index: -1, nom: nomDocument(PL.etat.doc.name), actif: true, modifie: modifieActif() }];
    for (const o of liste) {
      const el = document.createElement("div"); el.className = "onglet-doc" + (o.actif ? " actif" : "");
      el.setAttribute("role", "tab"); el.setAttribute("aria-selected", o.actif ? "true" : "false");
      el.dataset.index = String(o.index);
      const n = brut(document.createElement("span"));        // nom du document : jamais traduit
      n.textContent = o.nom || T("photolab.nouveau.sans_titre");
      // G4 : document modifié = icône dz-etat-modifie après le nom (le nom reste une donnée brute)
      const mod = document.createElement("span"); mod.className = "onglet-modifie"; mod.hidden = !o.modifie;
      if (o.modifie) mod.innerHTML = PL.icone("dz-etat-modifie", 10);
      const x = document.createElement("button"); x.type = "button"; x.className = "onglet-fermer"; x.innerHTML = PL.icone("dz-action-fermer", 12);
      x.title = T("commun.action.fermer"); x.setAttribute("aria-label", x.title);
      x.addEventListener("click", (ev) => { ev.stopPropagation(); fermerDocument(o.index); });
      if (!o.actif) el.addEventListener("click", () => activer(o.index));
      el.append(n, mod, x);
      zone.appendChild(el);
    }
  }
  PL.majOnglets = dessiner;
  PL.surDoc.push((doc) => { if (doc) relireSession(); else { PL.etat.session = null; dessiner(); } });

  // Repères d'enregistrement du document qui devient actif : propre selon le moteur -> sa révision ; sinon aucun
  // repère (fermer demandera), comme un document jamais enregistré.
  async function reperes() {
    await relireSession();
    const d = actifDeSession();
    PL.etat.revEnregistree = null;
    PL.etat.revOuverture = d && !d.dirty ? d.revision : null;
  }

  async function activer(index) {
    if (!PL.etat.doc) return;
    const r = await PL.executer("document.activate", { document: index }, { cycle: false });
    if (!r.ok) return;
    await reperes();
    await PL.documentOuvert();
  }

  async function confirmer(question, titre, ok) {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, { titre, ok });
    return (await ouvrirDialogue(PL, {
      titre,
      construire({ corps }) { const p = document.createElement("p"); p.textContent = question; corps.appendChild(p); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: ok, principal: true }],
    })) === "ok";
  }

  // Après une fermeture : un document reste -> il devient l'écran (repères relus) ; sinon l'accueil.
  async function apresFermeture() {
    let s = null;
    try { s = await PL.get("/session", true); } catch (e) { s = null; }
    const docs = s && Array.isArray(s.documents) ? s.documents : [];
    if (!docs.length) { PL.etat.session = s; PL.fermerVue(); return; }
    if (!docs.some((d) => d.index === s.active)) {
      try { await PL.file(() => PL.post("/executer", { command: "document.activate", params: { document: docs[0].index } })); } catch (e) { /* signalé */ }
    }
    await reperes();
    await PL.documentOuvert();
  }

  async function fermerDocument(index) {
    if (!PL.etat.doc) return;
    const s = PL.etat.session;
    const actif = !s || index === s.active || index < 0;
    const o = s ? ongletsDe(s, modifieActif()).find((x) => x.index === index) : null;
    if ((actif ? modifieActif() : o && o.modifie)
      && !(await confirmer(T("photolab.fichier.fermer_question"), T("photolab.fichier.fermer_titre"), T("photolab.fichier.fermer_sans")))) return;
    const params = actif && s ? { document: s.active } : actif ? {} : { document: index };
    const r = await PL.executer("file.close", params, { cycle: false });
    if (r.ok) await apresFermeture();
  }
  PL.fermerDocument = () => fermerDocument(PL.etat.session ? PL.etat.session.active : -1);

  async function toutFermer() {
    if (!PL.etat.doc) return;
    await relireSession();
    const noms = aConfirmer(ongletsDe(PL.etat.session || {}, modifieActif()));
    if (noms.length && !(await confirmer(T("photolab.documents.fermer_modifies", { noms: noms.join(", ") }),
      T("photolab.documents.tout_fermer"), T("photolab.fichier.fermer_sans")))) return;
    const r = await PL.executer("file.closeAll", {}, { cycle: false });
    if (r.ok) { PL.etat.session = null; PL.fermerVue(); }
  }

  async function fermerAutres() {
    if (!PL.etat.doc) return;
    await relireSession();
    const s = PL.etat.session || {};
    const noms = aConfirmer(ongletsDe(s, modifieActif()), s.active);
    if (noms.length && !(await confirmer(T("photolab.documents.fermer_modifies", { noms: noms.join(", ") }),
      T("photolab.documents.fermer_autres"), T("photolab.fichier.fermer_sans")))) return;
    const r = await PL.executer("file.closeOthers", {}, { cycle: false });
    if (r.ok) { await relireSession(); await PL.documentOuvert(); }
  }

  async function revenir() {
    if (!PL.etat.doc) return;
    if (!(await confirmer(T("photolab.revenir.question"), T("photolab.revenir.titre"), T("photolab.revenir.ok")))) return;
    try { await PL.file(() => PL.post("/revenir", {})); } catch (e) { return; }          // signalé par mod-api
    await reperes();
    await PL.documentOuvert();
    PL.signaler(T("photolab.revenir.fait"));
  }

  function telecharger(url, nom) {
    const a = document.createElement("a"); a.href = url; a.download = nom;
    document.body.appendChild(a); a.click(); a.remove();
  }
  function livrer(r, cleBiblio = "photolab.copie.biblio") {
    if (!r) return;
    const nom = r.fichier ? nomTelecharge(r.fichier, !PL.prefs || PL.prefs.v("fileHandling", "lowercaseExtension")) : r.fichier;
    if (r.url) { telecharger(r.url, nom); PL.signaler(T("photolab.export.fait", { nom })); }
    else if (r.filename) PL.signaler(T(cleBiblio, { nom: r.filename }));
  }

  const champ = (libelle, el) => {
    const l = document.createElement("label"); l.className = "pl-champ";
    const s = document.createElement("span"); s.textContent = libelle;
    l.append(s, el);
    return l;
  };
  const liste = (options, valeur) => {
    const sel = document.createElement("select");
    for (const [v, lib] of options) { const o = document.createElement("option"); o.value = v; o.textContent = lib; sel.appendChild(o); }
    sel.value = valeur;
    return sel;
  };
  const saisie = (valeur, attrs = {}) => {
    const i = document.createElement("input"); i.type = attrs.type || "text"; i.value = valeur;
    for (const [k, v] of Object.entries(attrs)) if (k !== "type") i.setAttribute(k, v);
    return i;
  };

  // Dialogue d'export commun (copie du document, calque) : format, qualité, échelle ?, nom, destination.
  async function dialogueExport({ titre, formats, avecEchelle, nom, envoyer, cleBiblio }) {
    let resultat = null;
    await ouvrirDialogue(PL, {
      titre,
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.exporter"), principal: true }],
      construire({ corps }) {
        const format = liste(formats.map((f) => [f, f.toUpperCase()]), formats[0]);
        const qualite = saisie("90", { type: "range", min: "1", max: "100", step: "1" });
        const vq = document.createElement("span"); vq.className = "pl-unite"; vq.textContent = "90";
        qualite.addEventListener("input", () => { vq.textContent = qualite.value; });
        const lQualite = champ(T("photolab.export.qualite"), qualite); lQualite.appendChild(vq);
        const echelle = saisie("100", { type: "number", min: String(ECHELLE_MIN), max: String(ECHELLE_MAX), step: "1" });
        const lEchelle = champ(T("photolab.calque_export.echelle"), echelle);
        const u = document.createElement("span"); u.className = "pl-unite"; u.textContent = "%"; lEchelle.appendChild(u);
        const nomEl = brut(saisie(nom, { maxlength: "80" }));
        const dest = liste([["telecharger", T("commun.action.telecharger")], ["bibliotheque", T("photolab.copie.bibliotheque")]], "telecharger");
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        const maj = () => {
          lQualite.hidden = !QUALITE(format.value);
          const biblioOk = FORMATS_BIBLIO.includes(format.value);
          dest.options[1].disabled = !biblioOk;
          if (!biblioOk) dest.value = "telecharger";
        };
        format.addEventListener("change", maj); maj();
        corps.append(champ(T("photolab.export.format"), format), lQualite);
        if (avecEchelle) corps.appendChild(lEchelle);
        corps.append(champ(T("photolab.nouveau.nom"), nomEl), champ(T("photolab.copie.destination"), dest), erreur);
        return async () => {
          try { resultat = await envoyer({ format: format.value, quality: qualite.value, echelle: echelle.value, nom: nomEl.value, destination: dest.value }); }
          catch (e) { erreur.textContent = e.cle ? T(e.cle) : e.message; return false; }
          return true;
        };
      },
    });
    livrer(resultat, cleBiblio);
  }

  function copie() {
    if (!PL.etat.doc) return;
    return dialogueExport({
      titre: T("photolab.copie.titre"), formats: FORMATS_EXPORT.map((f) => f.format), avecEchelle: false,
      nom: T("photolab.copie.nom", { nom: nomDocument(PL.etat.doc.name) || T("photolab.nouveau.sans_titre") }),
      envoyer: (f) => PL.file(() => PL.post("/copie", corpsCopie(f))),
    });
  }

  async function exportRapide() {
    if (!PL.etat.doc) return;
    const q = exportRapidePrefs(PL.prefs ? PL.prefs.p : null);
    if (q.dialogue) return copie();
    let r;
    try { r = await PL.file(() => PL.post(q.route, { ...q.corps, nom: nomDocument(PL.etat.doc.name) })); } catch (e) { return; }
    livrer(r);
  }

  const calqueActif = () => {
    const doc = PL.etat.doc;
    const plat = (l) => (l || []).flatMap((x) => [x, ...plat(x.children)]);
    return doc ? plat(doc.layers).find((c) => c.id === doc.activeLayer) || null : null;
  };

  async function calqueRapide() {
    const c = calqueActif();
    if (!c) return;
    let r;
    try { r = await PL.file(() => PL.post("/calque/exporter", corpsCalque({ format: "png", echelle: 100, nom: c.name, layer: c.id }))); } catch (e) { return; }
    livrer(r);
  }

  function calqueExporter() {
    const c = calqueActif();
    if (!c) return;
    return dialogueExport({
      titre: T("photolab.calque_export.titre"), formats: FORMATS_CALQUE, avecEchelle: true, nom: c.name || "", cleBiblio: "photolab.calque_export.biblio",
      envoyer: (f) => PL.file(() => PL.post("/calque/exporter", corpsCalque({ ...f, layer: c.id }))),
    });
  }

  function placer() {
    if (!PL.etat.doc || !PL.choisirImage) return;
    PL.choisirImage(T("photolab.placer.choisir"), async (nom) => {
      if (!nom) return;
      // t159 : Préférences › Paramètres (objet dynamique, redimensionner pendant le placement)
      const p = PL.prefs ? PL.prefs.p.general : { alwaysCreateSmartObjectsWhenPlacing: true, resizeImageDuringPlace: true };
      const corps = { filename: nom, objetDynamique: p.alwaysCreateSmartObjectsWhenPlacing, reduire: p.resizeImageDuringPlace };
      try { await PL.file(() => PL.post("/placer", corps)); } catch (e) { return; }
      await PL.cycle();
      PL.signaler(T("photolab.placer.fait", { nom }));
      // comme la référence : l'objet placé arrive sous les poignées de la transformation manuelle
      if (PL.actions["edit.freeTransform"]) PL.actions["edit.freeTransform"]();
    });
  }

  async function infos() {
    if (!PL.etat.doc) return;
    let avant;
    try { avant = await PL.file(() => PL.post("/executer", { command: "file.fileInfo", params: {} })); } catch (e) { return; }   // lecture : aucune étape
    let changees = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.infos.titre"), classe: "large",
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }],
      construire({ corps }) {
        const els = {};
        for (const k of ["title", "author", "authorTitle"]) els[k] = brut(saisie(avant[k] || "", { maxlength: String(MAX_TEXTE_INFO) }));
        els.description = brut(document.createElement("textarea")); els.description.rows = 3; els.description.value = avant.description || "";
        els.keywords = brut(saisie((avant.keywords || []).join("; ")));
        els.copyrightStatus = liste(STATUTS_COPYRIGHT.map((s) => [s, T("photolab.infos.statut." + s.toLowerCase())]), avant.copyrightStatus || "unknown");
        els.copyright = brut(saisie(avant.copyright || "", { maxlength: String(MAX_TEXTE_INFO) }));
        els.copyrightUrl = brut(saisie(avant.copyrightUrl || "", { type: "url", maxlength: "508", placeholder: "https://" }));
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        for (const k of ["title", "author", "authorTitle", "description", "keywords", "copyrightStatus", "copyright", "copyrightUrl"]) {
          corps.appendChild(champ(T("photolab.infos." + k.toLowerCase()), els[k]));
        }
        corps.appendChild(erreur);
        return () => {
          try { changees = infosModifiees(avant, Object.fromEntries(Object.entries(els).map(([k, el]) => [k, el.value]))); }
          catch (e) { erreur.textContent = T(e.cle); return false; }
          return true;
        };
      },
    });
    if (changees && Object.keys(changees).length) {
      const r = await PL.executer("file.fileInfo", changees);
      if (r.ok) PL.signaler(T("photolab.infos.fait"));
    }
  }

  /* ── listes de choix du dialogue générique ── */
  async function sessionFraiche() {
    try { return await PL.get("/session", true); } catch (e) { return null; }
  }
  PL.choixDialogue = PL.choixDialogue || {};
  PL.choixDialogue["image.adjustments.matchColor"] = async () => {
    const s = await sessionFraiche();
    const valeurs = choixDocuments(s, false, T);
    if (!valeurs.length) { PL.signaler(T("photolab.choix.aucun_document"), true); return null; }
    return [{ cle: "source", libelle: T("photolab.choix.source"), valeurs }];
  };
  PL.choixDialogue["filter.distort.displace"] = async () => {
    const s = await sessionFraiche();
    const valeurs = choixDocuments(s, true, T);
    if (!valeurs.length) return null;
    return [{ cle: "mapDocument", libelle: T("photolab.choix.carte"), valeurs, defaut: valeurs.length > 1 ? valeurs[1].valeur : valeurs[0].valeur }];
  };
  PL.choixDialogue["filter.render.flame"] = async () => {
    let l = null;
    try { l = await PL.post("/executer", { command: "path.list", params: {} }); } catch (e) { return null; }
    const valeurs = choixTraces(l, T);
    return [{ cle: "path", libelle: T("photolab.choix.trace"), valeurs, defaut: traceParDefaut(valeurs) }];
  };

  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => {
    const s = PL.etat.session;
    const d = actifDeSession();
    return decorerDocuments(menus, { nbDocs: s && Array.isArray(s.documents) ? s.documents.length : (PL.etat.doc ? 1 : 0), chemin: d ? d.path : null });
  });

  Object.assign(PL.actions, {
    "file.closeAll": toutFermer, "file.closeOthers": fermerAutres, "file.saveACopy": copie, "file.revert": revenir,
    "file.export.quickExportAsPng": exportRapide, "file.placeEmbedded": placer, "file.fileInfo": infos,
    "layer.quickExportAsPng": calqueRapide, "layer.exportAs": calqueExporter,
  });
  // « Fermer » (menu et ×) ferme désormais VRAIMENT le document du moteur (t158) : sinon les onglets le remontreraient.
  PL.actions["file.close"] = () => PL.fermerDocument();
}
