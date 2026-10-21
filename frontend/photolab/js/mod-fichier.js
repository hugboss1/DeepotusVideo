import { brut } from "./mod-cycle.js";
import { recevoir } from "../../shared/dz-envoi.js";

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
// t257 (M8) : + TIFF à calques (même format « tif » au pont, "calques": true), OpenRaster, PDF d'une page (aplati par le
// moteur). `id` distingue les deux TIFF ; `cle` = un libellé à traduire.
export const FORMATS_EXPORT = [
  { id: "png", format: "png", libelle: "PNG" },
  { id: "jpg", format: "jpg", libelle: "JPG", qualite: true },
  { id: "webp", format: "webp", libelle: "WEBP", qualite: true },
  { id: "tif", format: "tif", libelle: "TIFF" },
  { id: "tif-calques", format: "tif", libelle: "TIFF", cle: "photolab.export.tiff_calques", calques: true },
  { id: "psd", format: "psd", libelle: "PSD" },
  { id: "ora", format: "ora", libelle: "ORA" },
  { id: "pdf", format: "pdf", libelle: "PDF", cle: "photolab.export.pdf_page" },
  { id: "pcraft", format: "pcraft", libelle: "PCRAFT" },
];

export const formatExport = (id) => FORMATS_EXPORT.find((x) => x.id === id) || null;
export const libelleFormat = (f, T) => (f.cle ? T(f.cle) : f.libelle);

export function corpsExport(id, nom, quality = 90) {
  const f = formatExport(id);
  if (!f) throw erreurSaisie("photolab.export.erreur.format");
  const corps = { format: f.format, nom: String(nom || "") };
  if (f.calques) corps.calques = true;
  if (f.qualite) corps.quality = Math.max(1, Math.min(100, Math.round(Number(quality) || 90)));
  return corps;
}

// #415 : Fichier › Enregistrer sous… — un NOUVEAU fichier de la Bibliothèque sous le nom saisi (route /bibliotheque :
// PNG ou JPG) ; « Exporter sous… » reste le téléchargement.
export const FORMATS_BIBLIO = FORMATS_EXPORT.filter((f) => f.id === "png" || f.id === "jpg");
export function corpsBibliotheque(id, nom, quality = 90) {
  const f = FORMATS_BIBLIO.find((x) => x.id === id);
  if (!f) throw erreurSaisie("photolab.export.erreur.format");
  const n = String(nom == null ? "" : nom).trim();
  if (!n) throw erreurSaisie("photolab.enregistrer_sous.erreur.nom");
  const corps = { format: f.format, nom: n };
  if (f.qualite) corps.quality = Math.max(1, Math.min(100, Math.round(Number(quality) || 90)));
  return corps;
}

// t257 : ce que le moteur dit avoir perdu (`warnings` de doc.save, en anglais) -> clés de message, sans doublon.
const AVERTISSEMENTS = [[/flattened/i, "photolab.export.avert.aplati"], [/lossy/i, "photolab.export.avert.pertes"],
  [/resolution|dpi/i, "photolab.export.avert.dpi"]];
export function clesAvertissements(liste) {
  const cles = (Array.isArray(liste) ? liste : []).map((a) => (AVERTISSEMENTS.find(([m]) => m.test(String(a))) || [null, "photolab.export.avert.autre"])[1]);
  return [...new Set(cles)];
}

// t257 : préréglages de « Exporter… », gardés par le pont (/export/prereglages : file.export.presets.* est désactivé
// par le moteur en automation). Mêmes règles que photolab_routes.verifier_prereglages.
export const PREREGLAGES_MAX = 50;
export function prereglageDe(nom, id, quality) {
  const n = String(nom || "").trim();
  if (!n || n.length > 64) throw erreurSaisie("photolab.export.prereglage.erreur.nom");
  const corps = corpsExport(id, "", quality);
  const p = { nom: n, format: corps.format };
  if ("quality" in corps) p.quality = corps.quality;
  if (corps.calques) p.calques = true;
  return p;
}
export const idDePrereglage = (p) => {
  const id = p && p.format === "tif" && p.calques ? "tif-calques" : p && p.format;
  return formatExport(id) ? id : null;
};
export function rangerPrereglage(liste, p) {
  const l = (liste || []).filter((x) => x.nom.toLowerCase() !== p.nom.toLowerCase());
  if (l.length >= PREREGLAGES_MAX) throw erreurSaisie("photolab.export.prereglage.erreur.max");
  const k = (liste || []).findIndex((x) => x.nom.toLowerCase() === p.nom.toLowerCase());
  if (k < 0) return [...l, p];
  const r = (liste || []).slice(); r[k] = p; return r;
}
export const retirerPrereglage = (liste, nom) => (liste || []).filter((x) => x.nom !== nom);

// t257 : ouvrir un fichier de l'ordinateur. Ce que la Bibliothèque reçoit (/images/upload, décodé par Pillow) y va
// d'abord ; les formats que seul le moteur lit passent par /importer. Copie de PM.FORMATS_OUVERTURE (banc). HEIC/HEIF :
// non activé (question Q3, brevets HEVC).
export const FORMATS_BIBLIOTHEQUE = ["png", "jpg", "jpeg", "webp", "gif", "bmp", "avif"];
export const FORMATS_OUVERTURE = ["ora", "kra", "pdn", "af", "afphoto", "afdesign", "afpub", "exr", "dpx", "dds",
  "dng", "cr2", "cr3", "crw", "nef", "nrw", "arw", "srf", "sr2", "raf", "rw2", "orf", "pef", "srw", "3fr",
  "iiq", "erf", "mrw", "x3f",
  "psd", "psb", "pcraft", "tif", "tiff", "tga", "png", "jpg", "jpeg", "webp", "gif", "bmp"];
export const IMPORT_MAX = 1024 * 1024 * 1024;
export function routeFichier(nom, taille = 0) {
  const m = /\.([A-Za-z0-9]{1,10})$/.exec(String(nom || ""));
  const ext = m ? m[1].toLowerCase() : "";
  if (ext === "heic" || ext === "heif") return { refus: "photolab.import.heic" };
  if (Number(taille) > IMPORT_MAX) return { refus: "photolab.import.trop_lourd" };
  if (FORMATS_BIBLIOTHEQUE.includes(ext)) return "bibliotheque";
  if (FORMATS_OUVERTURE.includes(ext)) return "importer";
  return { refus: "photolab.import.format" };
}
export const ACCEPTES = [...new Set([...FORMATS_BIBLIOTHEQUE, ...FORMATS_OUVERTURE])].map((e) => "." + e).join(",");

// Faut-il demander avant de fermer ? Oui si la révision a bougé depuis le dernier enregistrement (ou, jamais
// enregistré, depuis l'ouverture) ; sans repère du tout, on demande.
export function aSauvegarder(doc, revEnregistree, revOuverture = null) {
  if (!doc) return false;
  const ref = revEnregistree != null ? revEnregistree : revOuverture;
  return ref == null || doc.revision !== ref;
}

// Nom à montrer et à enregistrer : /ouvrir copie l'image sous « <empreinte sha1 8>-<nom> » dans le dossier du moteur,
// qui nomme le document d'après cette copie ; on retire l'empreinte et l'extension (« e99baeb8-herbe.png » -> « herbe »).
// t139 : une image enregistrée par le Photolab porte « photolab_<AAAAMMJJ-HHMMSS>_ » devant son nom, et son fichier de
// travail « -png » / « -jpg » derrière : on les retire aussi, sinon chaque nouvel enregistrement empilerait le préfixe.
export function nomDocument(nom) {
  let s = String(nom == null ? "" : nom).replace(/^[0-9a-f]{8}-/, "");
  s = /\.[A-Za-z0-9]{2,6}$/.test(s) ? s.replace(/\.[A-Za-z0-9]{2,6}$/, "") : s;
  const m = /^photolab_\d{8}-\d{6}_(.+)$/.exec(s);
  return m ? m[1].replace(/-(png|jpg)$/, "") : s;
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
    if (PL.majOnglets) PL.majOnglets();   // l'onglet a été dessiné pendant le cycle, avant ce repère : sans lui, « • » d'emblée
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
  // t139 : une image enregistrée par le Photolab se rouvre avec ses calques (fichier de travail) ; la lignée
  // « retouche » vers l'image d'origine est tenue par le pont (chemin moteur du document), pas par l'écran.
  async function ouvrirImage(nom) {
    let r;
    try { r = await PL.post("/ouvrir", { filename: nom }); } catch (e) { return; }      // signalé par mod-api
    await apresOuverture();
    PL.signaler(T(r && r.travail ? "photolab.envoi.calques" : "photolab.fichier.ouvert", { nom }));
  }
  PL.ouvrirImage = ouvrirImage;

  // t158 : choisir une image de la Bibliothèque (Ouvrir, Placer incorporé) -> rappel(nom | null).
  function choisirImage(titre, rappel) {
    // Le sélecteur de la Bibliothèque du parent (même origine) d'abord ; un parent d'une autre origine lève à la lecture.
    let picker = null;
    try {
      const parent = window.parent !== window ? window.parent : null;
      picker = parent && typeof parent.__dzLibPicker === "function" ? parent.__dzLibPicker : null;
    } catch (e) { picker = null; }
    if (picker) { picker({ titre }, (nom) => rappel(nom || null)); return; }
    grilleDeRepli(titre).then(rappel);
  }
  PL.choisirImage = choisirImage;

  function ouvrir() {
    choisirImage(T("photolab.fichier.choisir"), (nom) => { if (nom) ouvrirImage(nom); });
  }

  // Repli hors de l'application (page ouverte seule) : grille de GET /api/images avec recherche.
  async function grilleDeRepli(titre) {
    let choisi = null;
    await ouvrirDialogue(PL, {
      titre, classe: "large",
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
    return choisi;
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
    if (f) ouvrirFichier(f);
  });

  // t257 : un fichier de l'ordinateur (dépôt ou Fichier › Ouvrir depuis l'ordinateur…) — dans la Bibliothèque puis
  // ouvert s'il est une image qu'elle reçoit, sinon ouvert par /importer (ORA, Krita, Affinity, Paint.NET, EXR, DPX, DDS,
  // raws, PSD, TIFF…) : le document s'enregistre ensuite dans la Bibliothèque avec ses calques, comme les autres.
  async function ouvrirFichier(f) {
    const route = routeFichier(f.name, f.size);
    if (route.refus) { PL.signaler(T(route.refus, { nom: f.name }), true); return; }
    if (route === "bibliotheque") {
      const fd = new FormData(); fd.append("file", f);
      let rep;
      try { rep = await fetch("/api/images/upload", { method: "POST", body: fd }); } catch (e) { PL.signaler(T("photolab.moteur.injoignable"), true); return; }
      if (!rep.ok) { PL.signaler(T("photolab.fichier.depot_refuse", { nom: f.name }), true); return; }
      const d = await rep.json();
      if (d && d.filename) ouvrirImage(d.filename);
      return;
    }
    try { await PL.post("/importer?nom=" + encodeURIComponent(f.name), f); } catch (e) { return; }      // signalé par mod-api
    await apresOuverture();
    PL.signaler(T("photolab.import.ouvert", { nom: f.name }));
  }
  PL.ouvrirFichier = ouvrirFichier;

  function importer() {
    const i = document.createElement("input");
    i.type = "file"; i.accept = ACCEPTES; i.hidden = true;
    i.addEventListener("change", () => { const f = i.files && i.files[0]; i.remove(); if (f) ouvrirFichier(f); });
    document.body.appendChild(i);
    i.click();
  }

  /* ── Enregistrer dans la Bibliothèque (PNG + fichier de travail .pcraft, toujours un NOUVEAU fichier) ── */
  async function enregistrer() {
    const doc = PL.etat.doc;
    if (!doc) return null;
    let r;
    // Le nom affiché (sans l'empreinte de la copie) : sinon la Bibliothèque recevrait « photolab_…_e99baeb8-herbe-png ».
    const corps = { format: "png" };
    if (nomDocument(doc.name)) corps.nom = nomDocument(doc.name);
    try { r = await PL.post("/bibliotheque", corps); } catch (e) { return null; }
    PL.etat.revEnregistree = doc.revision;
    if (PL.majOnglets) PL.majOnglets();
    PL.signaler(T(r.travail ? "photolab.fichier.enregistre" : "photolab.envoi.sans_calques", { nom: r.filename }));
    return r;
  }

  /* ── #415 : Enregistrer sous… : nom, format (PNG / JPG), qualité -> /bibliotheque, un nouveau fichier ── */
  async function enregistrerSous() {
    const doc = PL.etat.doc;
    if (!doc) return;
    let r = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.enregistrer_sous.titre"),
      boutons: [
        { role: "annuler", libelle: T("commun.action.annuler") },
        { role: "ok", libelle: T("commun.action.enregistrer"), principal: true },
      ],
      construire({ corps }) {
        const format = document.createElement("select");
        for (const f of FORMATS_BIBLIO) { const o = document.createElement("option"); o.value = f.id; o.textContent = libelleFormat(f, T); format.appendChild(o); }
        const qualite = entree("range", "90", { min: "1", max: "100", step: "1" });
        const vq = document.createElement("span"); vq.className = "pl-unite"; vq.textContent = "90";
        qualite.addEventListener("input", () => { vq.textContent = qualite.value; });
        const lQualite = champ(T("photolab.export.qualite"), qualite); lQualite.appendChild(vq);
        const majQualite = () => { lQualite.hidden = !(FORMATS_BIBLIO.find((f) => f.id === format.value) || {}).qualite; };
        format.addEventListener("change", majQualite); majQualite();
        const nom = brut(entree("text", nomDocument(doc.name), { maxlength: "80" }));
        const aide = document.createElement("p"); aide.className = "pl-note"; aide.textContent = T("photolab.enregistrer_sous.aide");
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");
        corps.append(champ(T("photolab.nouveau.nom"), nom), champ(T("photolab.export.format"), format), lQualite, aide, erreur);
        return async () => {
          try { r = await PL.post("/bibliotheque", corpsBibliotheque(format.value, nom.value, qualite.value)); }
          catch (e) { erreur.textContent = e.cle ? T(e.cle) : e.message; return false; }
          return true;
        };
      },
    });
    if (!r) return;
    PL.etat.revEnregistree = doc.revision;
    if (PL.majOnglets) PL.majOnglets();
    PL.signaler(T(r.travail ? "photolab.fichier.enregistre" : "photolab.envoi.sans_calques", { nom: r.filename }));
  }

  /* ── Envoyer vers… : enregistrer (nouveau fichier) puis le menu « Envoyer vers » de l'application, mêmes cibles que
     la Bibliothèque (Studio, Quick, Montage, Vectorlab, Sprite Lab, Tile Lab, Cardforge…) ── */
  async function envoyer() {
    const r = await enregistrer();
    if (!r) return;
    let vers = null;
    try {
      const haut = window.top !== window ? window.top : null;
      vers = haut && typeof haut.__dzEnvoyerVers === "function" ? haut.__dzEnvoyerVers : null;
    } catch (e) { vers = null; }                 // application d'une autre origine : pas de menu partagé
    if (vers) vers(r.filename, "photolab");
    else PL.signaler(T("photolab.envoi.hors_app", { nom: r.filename }));
  }

  /* ── t140 (D10) : repli « app native » — le document part dans photocraft.exe avec ses calques, et en revient ── */
  async function natifOuvrir() {
    if (!PL.etat.doc) return;
    let r;
    try { r = await PL.post("/natif/ouvrir", {}); } catch (e) { return; }          // signalé par mod-api
    PL.signaler(T("photolab.natif.ouvert", { nom: String(r.fichier || "").split("/").pop() }));
  }
  async function natifReprendre() {
    let r;
    try { r = await PL.post("/natif/reprendre", {}); } catch (e) { return; }
    await apresOuverture();
    PL.signaler(T("photolab.natif.repris", { nom: String(r.fichier || "").split("/").pop() }));
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
        for (const f of FORMATS_EXPORT) { const o = document.createElement("option"); o.value = f.id; o.textContent = libelleFormat(f, T); format.appendChild(o); }
        const qualite = entree("range", "90", { min: "1", max: "100", step: "1" });
        const vq = document.createElement("span"); vq.className = "pl-unite"; vq.textContent = "90";
        qualite.addEventListener("input", () => { vq.textContent = qualite.value; });
        const lQualite = champ(T("photolab.export.qualite"), qualite); lQualite.appendChild(vq);
        const majQualite = () => { lQualite.hidden = !formatExport(format.value).qualite; };
        format.addEventListener("change", majQualite); majQualite();
        const nom = entree("text", nomDocument(doc.name), { maxlength: "80" });
        const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.setAttribute("role", "alert");

        // t257 : préréglages (choisir = format et qualité posés ; Enregistrer = sous le nom saisi ; Supprimer)
        let prereglages = [];
        const choix = document.createElement("select"); choix.className = "pl-prereglage";
        const nomP = brut(entree("text", "", { maxlength: "64", placeholder: T("photolab.export.prereglage.nom") }));
        const bGarder = document.createElement("button"); bGarder.type = "button"; bGarder.className = "pl-bouton pl-prereglage-garder";
        bGarder.textContent = T("photolab.export.prereglage.enregistrer");
        const bOter = document.createElement("button"); bOter.type = "button"; bOter.className = "pl-bouton pl-prereglage-oter";
        bOter.textContent = T("commun.action.supprimer");
        const ligneP = document.createElement("div"); ligneP.className = "pl-prereglages"; ligneP.append(choix, nomP, bGarder, bOter);
        const dessinerChoix = (garde = "") => {
          choix.textContent = "";
          const vide = document.createElement("option"); vide.value = ""; vide.textContent = T("photolab.export.prereglage.aucun"); choix.appendChild(vide);
          for (const p of prereglages) { const o = brut(document.createElement("option")); o.value = p.nom; o.textContent = p.nom; choix.appendChild(o); }
          choix.value = garde; bOter.disabled = !garde;
        };
        const ecrire = async (liste, garde) => {
          try { prereglages = (await PL.api("PUT", "/export/prereglages", { prereglages: liste })).prereglages; }
          catch (e) { erreur.textContent = e.message; return; }
          dessinerChoix(garde);
        };
        choix.addEventListener("change", () => {
          const p = prereglages.find((x) => x.nom === choix.value);
          bOter.disabled = !p;
          if (!p) return;
          const id = idDePrereglage(p);
          if (id) { format.value = id; majQualite(); }
          if (p.quality) { qualite.value = String(p.quality); vq.textContent = qualite.value; }
          nomP.value = p.nom;
        });
        bGarder.addEventListener("click", () => {
          let p;
          try { p = prereglageDe(nomP.value, format.value, qualite.value); ecrire(rangerPrereglage(prereglages, p), p.nom); erreur.textContent = ""; }
          catch (e) { erreur.textContent = T(e.cle || "photolab.moteur.erreur"); }
        });
        bOter.addEventListener("click", () => { if (choix.value) ecrire(retirerPrereglage(prereglages, choix.value), ""); });
        dessinerChoix();
        PL.get("/export/prereglages", true).then((r) => { prereglages = (r && r.prereglages) || []; dessinerChoix(); }).catch(() => {});

        corps.append(champ(T("photolab.export.prereglage"), ligneP), champ(T("photolab.export.format"), format), lQualite,
          champ(T("photolab.nouveau.nom"), nom), erreur);
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
    // t257 : ce que le format a perdu (PDF aplati, calques fusionnés, compression avec pertes) dans le même message
    const avert = clesAvertissements(resultat.avertissements).map((c) => T(c));
    PL.signaler([T("photolab.export.fait", { nom: resultat.fichier }), ...avert].join(" "));
  }

  // t158 : les onglets (un par document de la session) et « Fermer » (confirmation si modifié, puis fermeture RÉELLE du
  // document du moteur) sont dans mod-documents (PL.majOnglets, PL.actions["file.close"]).

  PL.actions["file.new"] = nouveau;
  PL.actions["file.open"] = ouvrir;
  PL.actions["file.save"] = enregistrer;
  PL.actions["file.saveAs"] = enregistrerSous;
  PL.actions["file.export.exportAs"] = exporter;
  PL.actions["pl.importer"] = importer;
  PL.actions["pl.envoyer"] = envoyer;
  PL.actions["pl.natif.ouvrir"] = natifOuvrir;
  PL.actions["pl.natif.reprendre"] = natifReprendre;
  PL.$("#btnNouveau").addEventListener("click", nouveau);
  PL.$("#btnOuvrir").addEventListener("click", ouvrir);

  // t139 : une image envoyée par un autre écran (« Envoyer vers › Photolab ») ou `?img=` : ouverte à l'arrivée.
  const recu = recevoir("photolab");
  if (recu) ouvrirImage(recu.image);
}
