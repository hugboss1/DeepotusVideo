import { brut } from "./mod-cycle.js";

// mod-fichier.js — Nouveau, Ouvrir (Bibliothèque), Enregistrer, Exporter, Fermer (C1, décision D5). Les fichiers ne
// passent JAMAIS par une commande moteur (le pont refuse file.*) : uniquement par les routes /nouveau, /ouvrir,
// /bibliotheque et /enregistrer. Données et règles PURES exportées (qa/fichier.test.mjs).

// Préréglages du dialogue Nouveau : un sous-ensemble des 33 de photocraft (inventaire B §5), renommés (D8).
export const CATEGORIES = ["photo", "film", "mobile", "imprimer", "web"];
export const PRESETS = [
  { id: "defaut", cle: "photolab.preset.defaut", categorie: "photo", w: 2100, h: 1500, ppi: 300 },
  { id: "hdtv", cle: "photolab.preset.hdtv", categorie: "film", w: 1920, h: 1080, ppi: 72 },
  { id: "uhd4k", cle: "photolab.preset.uhd4k", categorie: "film", w: 3840, h: 2160, ppi: 72 },
  { id: "carre", cle: "photolab.preset.carre", categorie: "mobile", w: 1080, h: 1080, ppi: 72 },
  { id: "story", cle: "photolab.preset.story", categorie: "mobile", w: 1080, h: 1920, ppi: 72 },
  { id: "a4", cle: "photolab.preset.a4", categorie: "imprimer", w: 2480, h: 3508, ppi: 300 },
  { id: "web", cle: "photolab.preset.web", categorie: "web", w: 1366, h: 768, ppi: 72 },
];
export const COTE_MAX = 30000;              // borne de la route /nouveau
const FONDS = ["white", "black", "transparent"];

function erreurSaisie(cle) { const e = new Error(cle); e.cle = cle; return e; }

// Entier strict : « 12.5 », « abc », « » sont refusés (jamais d'arrondi muet d'une cote saisie).
function entierStrict(v) {
  const s = String(v == null ? "" : v).trim();
  return /^\d+$/.test(s) ? Number(s) : NaN;
}

// Formulaire du dialogue -> paramètres de /nouveau. Lève une erreur dont `.cle` est la clé du message au dictionnaire.
export function parametresNouveau(form, nomDefaut = "") {
  const w = entierStrict(form.largeur), h = entierStrict(form.hauteur);
  if (!(w >= 1 && w <= COTE_MAX)) throw erreurSaisie("photolab.nouveau.erreur.largeur");
  if (!(h >= 1 && h <= COTE_MAX)) throw erreurSaisie("photolab.nouveau.erreur.hauteur");
  const rs = String(form.resolution == null ? "" : form.resolution).trim().replace(",", ".");
  const r = /^\d+(\.\d+)?$/.test(rs) ? Number(rs) : NaN;
  if (!(r > 0 && r <= 10000)) throw erreurSaisie("photolab.nouveau.erreur.resolution");
  let fond = String(form.fond || "white").trim().toLowerCase();
  if (!FONDS.includes(fond) && !/^#[0-9a-f]{6}$/.test(fond)) throw erreurSaisie("photolab.nouveau.erreur.fond");
  const nom = String(form.nom || "").trim().slice(0, 120) || nomDefaut;
  return { width: w, height: h, resolution: r, mode: "rgb", depth: 8, background: fond, name: nom };
}

export function orientation(w, h) { return w > h ? "paysage" : w < h ? "portrait" : "carre"; }

// Formats de « Exporter… » : tous acceptés par /enregistrer (FORMATS de photolab_routes.py, vérifié par le banc).
export const FORMATS_EXPORT = [
  { format: "png", libelle: "PNG" },
  { format: "jpg", libelle: "JPG", qualite: true },
  { format: "webp", libelle: "WEBP", qualite: true },
  { format: "tif", libelle: "TIFF" },
  { format: "psd", libelle: "PSD" },
  { format: "pcraft", libelle: "PCRAFT" },
];

export function corpsExport(format, nom, quality = 90) {
  const f = FORMATS_EXPORT.find((x) => x.format === format);
  if (!f) throw erreurSaisie("photolab.export.erreur.format");
  const corps = { format, nom: String(nom || "") };
  if (f.qualite) corps.quality = Math.max(1, Math.min(100, Math.round(Number(quality) || 90)));
  return corps;
}

// Faut-il demander avant de fermer ? Oui si la révision a bougé depuis le dernier enregistrement (ou, jamais
// enregistré, depuis l'ouverture) ; sans repère du tout, on demande.
export function aSauvegarder(doc, revEnregistree, revOuverture = null) {
  if (!doc) return false;
  const ref = revEnregistree != null ? revEnregistree : revOuverture;
  return ref == null || doc.revision !== ref;
}

// Nom à montrer et à enregistrer : /ouvrir copie l'image sous « <empreinte sha1 8>-<nom> » dans le dossier du moteur,
// qui nomme le document d'après cette copie ; on retire l'empreinte et l'extension (« e99baeb8-herbe.png » -> « herbe »).
export function nomDocument(nom) {
  const s = String(nom == null ? "" : nom).replace(/^[0-9a-f]{8}-/, "");
  return /\.[A-Za-z0-9]{2,6}$/.test(s) ? s.replace(/\.[A-Za-z0-9]{2,6}$/, "") : s;
}

/* ───────────── côté DOM ───────────── */

// Dialogue maison (jamais window.prompt) : voile + boîte, Échap = annuler, Entrée = bouton principal. Les touches ne
// sortent pas du dialogue (sinon une lettre tapée sur un bouton changerait d'outil). -> Promise<rôle du bouton>.
export function ouvrirDialogue(PL, { titre, classe = "", construire, boutons }) {
  return new Promise((resoudre) => {
    const voile = document.createElement("div");
    voile.className = "pl-voile";
    const boite = document.createElement("div");
    boite.className = "pl-dlg " + classe;
    boite.setAttribute("role", "dialog"); boite.setAttribute("aria-modal", "true");
    const tete = document.createElement("header"); tete.className = "pl-dlg-tete"; tete.textContent = titre;
    const corps = document.createElement("div"); corps.className = "pl-dlg-corps";
    const pied = document.createElement("footer"); pied.className = "pl-dlg-pied";
    boite.append(tete, corps, pied);
    voile.appendChild(boite);
    let fini = false;
    const fermer = (role) => { if (fini) return; fini = true; voile.remove(); resoudre(role); };
    const api = { corps, fermer, boite };
    const avant = construire ? construire(api) : null;     // peut rendre une fonction de validation (false = rester ouvert)
    for (const b of boutons) {
      const el = document.createElement("button");
      el.type = "button"; el.className = "pl-bouton" + (b.principal ? " principal" : "");
      el.textContent = b.libelle;
      el.addEventListener("click", async () => {
        if (b.role !== "annuler" && avant && (await avant(b.role)) === false) return;
        fermer(b.role);
      });
      b.el = el;
      pied.appendChild(el);
    }
    voile.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Escape") { ev.preventDefault(); fermer("annuler"); }
      else if (ev.key === "Enter" && !(ev.target && ev.target.tagName === "BUTTON")) {
        const p = boutons.find((b) => b.principal);
        if (p) { ev.preventDefault(); p.el.click(); }
      }
    });
    voile.addEventListener("pointerdown", (ev) => { if (ev.target === voile) fermer("annuler"); });
    document.body.appendChild(voile);
    const premier = boite.querySelector("input, select, button.principal, button");
    if (premier) premier.focus();
  });
}

export function initFichier(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.etat.revEnregistree = null;   // révision au dernier enregistrement
  PL.etat.revOuverture = null;     // révision à l'ouverture (repère tant que rien n'est enregistré)
  PL.actions = PL.actions || {};

  const champ = (libelle, el, unite = "") => {
    const l = document.createElement("label"); l.className = "pl-champ";
    const s = document.createElement("span"); s.textContent = libelle;
    l.append(s, el);
    if (unite) { const u = document.createElement("span"); u.className = "pl-unite"; u.textContent = unite; l.appendChild(u); }
    return l;
  };
  const entree = (type, valeur, attrs = {}) => {
    const i = document.createElement("input"); i.type = type; i.value = valeur;
    for (const [k, v] of Object.entries(attrs)) i.setAttribute(k, v);
    return i;
  };

  async function apresOuverture() {
    PL.etat.revEnregistree = null;
    const doc = await PL.documentOuvert();
    PL.etat.revOuverture = doc ? doc.revision : null;
    majOnglet(PL.etat.doc);          // l'onglet a été dessiné pendant le cycle, avant ce repère : sans lui, « • » d'emblée
    return doc;
  }

  /* ── Nouveau ── */
  async function nouveau() {
    let categorie = "photo";
    let preset = PRESETS[0];
    await ouvrirDialogue(PL, {
      titre: T("photolab.nouveau.titre"), classe: "large",
      boutons: [
        { role: "annuler", libelle: T("commun.action.fermer") },
        { role: "creer", libelle: T("photolab.nouveau.creer"), principal: true },
      ],
      construire({ corps }) {
        corps.classList.add("nv-corps");
        const gauche = document.createElement("div"); gauche.className = "nv-gauche";
        const cats = document.createElement("div"); cats.className = "nv-cats"; cats.setAttribute("role", "tablist");
        const cartes = document.createElement("div"); cartes.className = "nv-cartes";
        gauche.append(cats, cartes);
        const droite = document.createElement("div"); droite.className = "nv-details";
        const titreD = document.createElement("h3"); titreD.textContent = T("photolab.nouveau.details");
        const nom = entree("text", T("photolab.nouveau.sans_titre"), { maxlength: "120" });
        const largeur = entree("number", preset.w, { min: "1", max: String(COTE_MAX), step: "1" });
        const hauteur = entree("number", preset.h, { min: "1", max: String(COTE_MAX), step: "1" });
        const resolution = entree("number", preset.ppi, { min: "1", max: "10000", step: "1" });
        const orient = document.createElement("span"); orient.className = "pl-segments";
        const bPortrait = document.createElement("button"); bPortrait.type = "button"; bPortrait.textContent = T("photolab.nouveau.portrait");
        const bPaysage = document.createElement("button"); bPaysage.type = "button"; bPaysage.textContent = T("photolab.nouveau.paysage");
        orient.append(bPortrait, bPaysage);
        const fond = document.createElement("select");
        for (const [v, cle] of [["white", "photolab.nouveau.fond.blanc"], ["black", "photolab.nouveau.fond.noir"],
          ["transparent", "photolab.nouveau.fond.transparent"], ["couleur", "photolab.nouveau.fond.couleur"]]) {
          const o = document.createElement("option"); o.value = v; o.textContent = T(cle); fond.appendChild(o);
        }
        const couleur = entree("color", "#ffffff"); couleur.hidden = true;
        fond.addEventListener("change", () => { couleur.hidden = fond.value !== "couleur"; });
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        const lFond = champ(T("photolab.nouveau.fond"), fond); lFond.appendChild(couleur);
        droite.append(titreD, champ(T("photolab.nouveau.nom"), nom), champ(T("photolab.nouveau.largeur"), largeur, "px"),
          champ(T("photolab.nouveau.hauteur"), hauteur, "px"), champ(T("photolab.nouveau.orientation"), orient),
          champ(T("photolab.nouveau.resolution"), resolution, "ppi"), lFond, erreur);
        corps.append(gauche, droite);

        const majOrientation = () => {
          const o = orientation(Number(largeur.value), Number(hauteur.value));
          bPortrait.classList.toggle("actif", o === "portrait");
          bPaysage.classList.toggle("actif", o === "paysage");
        };
        const tourner = (voulue) => {
          if (orientation(Number(largeur.value), Number(hauteur.value)) === voulue) return;
          const w = largeur.value; largeur.value = hauteur.value; hauteur.value = w; majOrientation();
        };
        bPortrait.addEventListener("click", () => tourner("portrait"));
        bPaysage.addEventListener("click", () => tourner("paysage"));
        largeur.addEventListener("input", majOrientation); hauteur.addEventListener("input", majOrientation);

        function dessinerCartes() {
          cats.textContent = ""; cartes.textContent = "";
          for (const c of CATEGORIES) {
            const b = document.createElement("button"); b.type = "button"; b.setAttribute("role", "tab");
            b.className = "nv-cat" + (c === categorie ? " actif" : "");
            b.textContent = T("photolab.nouveau.categorie." + c);
            b.addEventListener("click", () => { categorie = c; dessinerCartes(); });
            cats.appendChild(b);
          }
          for (const p of PRESETS.filter((x) => x.categorie === categorie)) {
            const b = document.createElement("button"); b.type = "button";
            b.className = "nv-carte" + (p === preset ? " actif" : "");
            const n = document.createElement("span"); n.className = "nv-carte-nom"; n.textContent = T(p.cle);
            const d = document.createElement("span"); d.className = "nv-carte-dim"; d.textContent = p.w + " × " + p.h + " px · " + p.ppi + " ppi";
            b.append(n, d);
            b.addEventListener("click", () => {
              preset = p; largeur.value = p.w; hauteur.value = p.h; resolution.value = p.ppi;
              majOrientation();
              // Classes seulement : reconstruire les cartes ici détruirait celle qui reçoit le double-clic (créer).
              PL.$$(".nv-carte", cartes).forEach((x) => x.classList.toggle("actif", x === b));
            });
            b.addEventListener("dblclick", () => { const c = corps.closest(".pl-dlg").querySelector(".pl-bouton.principal"); if (c) c.click(); });
            cartes.appendChild(b);
          }
        }
        dessinerCartes(); majOrientation();

        return async () => {
          let params;
          try {
            params = parametresNouveau({ nom: nom.value, largeur: largeur.value, hauteur: hauteur.value, resolution: resolution.value,
              fond: fond.value === "couleur" ? couleur.value : fond.value }, T("photolab.nouveau.sans_titre"));
          } catch (e) { erreur.textContent = T(e.cle || "photolab.moteur.erreur"); return false; }
          erreur.textContent = "";
          try { await PL.post("/nouveau", params); } catch (e) { erreur.textContent = e.message; return false; }
          apresOuverture();
          return true;
        };
      },
    });
  }

  /* ── Ouvrir : Bibliothèque ── */
  async function ouvrirImage(nom) {
    try { await PL.post("/ouvrir", { filename: nom }); } catch (e) { return; }      // signalé par mod-api
    await apresOuverture();
    PL.signaler(T("photolab.fichier.ouvert", { nom }));
  }
  PL.ouvrirImage = ouvrirImage;

  function ouvrir() {
    // Le sélecteur de la Bibliothèque du parent (même origine) d'abord ; un parent d'une autre origine lève à la lecture.
    let picker = null;
    try {
      const parent = window.parent !== window ? window.parent : null;
      picker = parent && typeof parent.__dzLibPicker === "function" ? parent.__dzLibPicker : null;
    } catch (e) { picker = null; }
    if (picker) { picker({ titre: T("photolab.fichier.choisir") }, (nom) => { if (nom) ouvrirImage(nom); }); return; }
    grilleDeRepli();
  }

  // Repli hors de l'application (page ouverte seule) : grille de GET /api/images avec recherche.
  async function grilleDeRepli() {
    let choisi = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.fichier.choisir"), classe: "large",
      boutons: [{ role: "annuler", libelle: T("commun.action.fermer") }],
      construire({ corps, fermer }) {
        const recherche = entree("search", "", { placeholder: T("commun.action.rechercher") });
        recherche.className = "lib-recherche";
        const grille = document.createElement("div"); grille.className = "lib-grille";
        grille.textContent = T("commun.etat.chargement");
        corps.append(recherche, grille);
        let images = [];
        const dessiner = () => {
          const f = recherche.value.trim().toLowerCase();
          const vues = images.filter((i) => !f || String(i.filename).toLowerCase().includes(f));
          grille.textContent = "";
          if (!vues.length) { grille.textContent = T("commun.etat.aucun_resultat"); return; }
          for (const i of vues) {
            const b = brut(document.createElement("button")); b.type = "button"; b.className = "lib-carte"; b.title = i.filename;   // nom de fichier : jamais traduit
            const im = document.createElement("img"); im.loading = "lazy"; im.alt = ""; im.src = "/api/images/" + encodeURIComponent(i.filename);
            const n = document.createElement("span"); n.textContent = i.filename;
            b.append(im, n);
            b.addEventListener("click", () => { choisi = i.filename; fermer("ok"); });
            grille.appendChild(b);
          }
        };
        recherche.addEventListener("input", dessiner);
        fetch("/api/images").then((r) => r.json()).then((d) => {
          images = (d.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
          dessiner();
        }).catch(() => { grille.textContent = T("photolab.fichier.biblio_injoignable"); });
      },
    });
    if (choisi) ouvrirImage(choisi);
  }

  /* ── Dépôt d'un fichier sur la page : téléversé dans la Bibliothèque puis ouvert ── */
  const scene = PL.$("#scene");
  const aDesFichiers = (ev) => ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes("Files");
  scene.addEventListener("dragover", (ev) => { if (aDesFichiers(ev)) { ev.preventDefault(); scene.classList.add("depot-survol"); } });
  scene.addEventListener("dragleave", () => scene.classList.remove("depot-survol"));
  scene.addEventListener("drop", async (ev) => {
    scene.classList.remove("depot-survol");
    if (!aDesFichiers(ev)) return;
    ev.preventDefault();
    const f = ev.dataTransfer.files && ev.dataTransfer.files[0];
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    let rep;
    try { rep = await fetch("/api/images/upload", { method: "POST", body: fd }); } catch (e) { PL.signaler(T("photolab.moteur.injoignable"), true); return; }
    if (!rep.ok) { PL.signaler(T("photolab.fichier.depot_refuse", { nom: f.name }), true); return; }
    const d = await rep.json();
    if (d && d.filename) ouvrirImage(d.filename);
  });

  /* ── Enregistrer dans la Bibliothèque (PNG) ── */
  async function enregistrer() {
    const doc = PL.etat.doc;
    if (!doc) return;
    let r;
    // Le nom affiché (sans l'empreinte de la copie) : sinon la Bibliothèque recevrait « photolab_…_e99baeb8-herbe-png ».
    const corps = { format: "png" };
    if (nomDocument(doc.name)) corps.nom = nomDocument(doc.name);
    try { r = await PL.post("/bibliotheque", corps); } catch (e) { return; }
    PL.etat.revEnregistree = doc.revision;
    majOnglet(PL.etat.doc);
    PL.signaler(T("photolab.fichier.enregistre", { nom: r.filename }));
  }

  /* ── Exporter… : format, qualité, nom -> /enregistrer puis téléchargement ── */
  async function exporter() {
    const doc = PL.etat.doc;
    if (!doc) return;
    let resultat = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.export.titre"),
      boutons: [
        { role: "annuler", libelle: T("commun.action.annuler") },
        { role: "ok", libelle: T("commun.action.exporter"), principal: true },
      ],
      construire({ corps }) {
        const format = document.createElement("select");
        for (const f of FORMATS_EXPORT) { const o = document.createElement("option"); o.value = f.format; o.textContent = f.libelle; format.appendChild(o); }
        const qualite = entree("range", "90", { min: "1", max: "100", step: "1" });
        const vq = document.createElement("span"); vq.className = "pl-unite"; vq.textContent = "90";
        qualite.addEventListener("input", () => { vq.textContent = qualite.value; });
        const lQualite = champ(T("photolab.export.qualite"), qualite); lQualite.appendChild(vq);
        const majQualite = () => { lQualite.hidden = !FORMATS_EXPORT.find((f) => f.format === format.value).qualite; };
        format.addEventListener("change", majQualite); majQualite();
        const nom = entree("text", nomDocument(doc.name), { maxlength: "80" });
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        corps.append(champ(T("photolab.export.format"), format), lQualite, champ(T("photolab.nouveau.nom"), nom), erreur);
        return async () => {
          try { resultat = await PL.post("/enregistrer", corpsExport(format.value, nom.value, qualite.value)); }
          catch (e) { erreur.textContent = e.cle ? T(e.cle) : e.message; return false; }
          return true;
        };
      },
    });
    if (!resultat) return;
    const a = document.createElement("a");
    a.href = resultat.url; a.download = resultat.fichier;
    document.body.appendChild(a); a.click(); a.remove();
    PL.signaler(T("photolab.export.fait", { nom: resultat.fichier }));
  }

  /* ── Fermer : confirmation si modifié depuis le dernier enregistrement ── */
  async function fermer() {
    const doc = PL.etat.doc;
    if (!doc) return;
    if (aSauvegarder(doc, PL.etat.revEnregistree, PL.etat.revOuverture)) {
      const d = window.__dzDialogue;
      // Sans le dialogue partagé (page ouverte hors de l'application), le dialogue maison du fichier : jamais de
      // fermeture muette d'un document modifié.
      const oui = d ? await d.confirmer(T("photolab.fichier.fermer_question"), { titre: T("photolab.fichier.fermer_titre"), ok: T("photolab.fichier.fermer_sans") })
        : (await ouvrirDialogue(PL, {
          titre: T("photolab.fichier.fermer_titre"),
          construire({ corps }) { const p = document.createElement("p"); p.textContent = T("photolab.fichier.fermer_question"); corps.appendChild(p); },
          boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "fermer", libelle: T("photolab.fichier.fermer_sans"), principal: true }],
        })) === "fermer";
      if (!oui) return;
    }
    PL.fermerVue();
  }

  /* ── onglet du document ── */
  function majOnglet(doc) {
    const zone = PL.$("#onglets");
    zone.textContent = "";
    if (!doc) return;
    const o = document.createElement("div"); o.className = "onglet-doc actif"; o.setAttribute("role", "tab"); o.setAttribute("aria-selected", "true");
    const n = brut(document.createElement("span"));        // nom du document : jamais traduit
    n.textContent = (nomDocument(doc.name) || T("photolab.nouveau.sans_titre")) + (aSauvegarder(doc, PL.etat.revEnregistree, PL.etat.revOuverture) ? " •" : "");
    const x = document.createElement("button"); x.type = "button"; x.className = "onglet-fermer"; x.textContent = "×";
    x.title = T("commun.action.fermer"); x.setAttribute("aria-label", x.title);
    x.addEventListener("click", fermer);
    o.append(n, x);
    zone.appendChild(o);
  }
  PL.surDoc.push(majOnglet);

  PL.actions["file.new"] = nouveau;
  PL.actions["file.open"] = ouvrir;
  PL.actions["file.close"] = fermer;
  PL.actions["file.save"] = enregistrer;
  PL.actions["file.saveAs"] = exporter;
  PL.actions["file.export.exportAs"] = exporter;
  PL.$("#btnNouveau").addEventListener("click", nouveau);
  PL.$("#btnOuvrir").addEventListener("click", ouvrir);
}
