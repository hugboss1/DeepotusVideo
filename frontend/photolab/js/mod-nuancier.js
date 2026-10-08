// mod-nuancier.js — t153 (parité L3) : le panneau Nuancier, onglet du groupe Couleur.
// Le moteur n'a aucune commande de nuancier : les groupes de nuances sont une donnée Deepotus (/api/photolab/nuancier,
// photolab_nuancier.py dont le défaut est la copie exacte de etatDefaut() — banc test_photolab_panneaux3 [3]). Choisir
// une nuance passe par tools.setColors (clic = premier plan, Alt+clic = arrière-plan, comme la référence) ; clic droit =
// marquer la nuance (Supprimer). Fonctions PURES exportées (qa/panneaux3.test.mjs).
import { demanderNom } from "./mod-nommer.js";

// Les 40 nuances de l'amont (4 rangées de 10), en quatre groupes fournis.
export const DEFAUT_GROUPES = [
  ["gris", ["#000000", "#1a1a1a", "#333333", "#4d4d4d", "#666666", "#808080", "#999999", "#b3b3b3", "#cccccc", "#ffffff"]],
  ["pastels", ["#ec8080", "#f4b084", "#fae080", "#d6f080", "#96e896", "#80e8c8", "#80dcf0", "#80b0f4", "#a890f4", "#e890e8"]],
  ["vives", ["#e62828", "#f5781e", "#fad21e", "#a0dc28", "#28c850", "#1ec8aa", "#1eaae6", "#2864e6", "#7846dc", "#d232b4"]],
  ["foncees", ["#781414", "#823c0a", "#826e0a", "#507814", "#146428", "#0a645a", "#0a5078", "#143278", "#3c1e6e", "#6e145a"]],
];
export const MAX_RECENTES = 12;
export const MAX_NOM = 64;
// Nom affiché d'un groupe fourni (nom vide dans le fichier : traduit ici).
export const NOMS_GROUPES = { gris: "photolab.nuancier.groupe_gris", pastels: "photolab.nuancier.groupe_pastels",
  vives: "photolab.nuancier.groupe_vives", foncees: "photolab.nuancier.groupe_foncees" };

const copie = (o) => JSON.parse(JSON.stringify(o));
const nomPropre = (brut) => {
  const n = String(brut == null ? "" : brut).trim();
  return n && n.length <= MAX_NOM && ![...n].some((c) => c.charCodeAt(0) < 32) ? n : null;
};
export const etatDefaut = () => ({ version: 1, recentes: [],
  groupes: DEFAUT_GROUPES.map(([id, c]) => ({ id, nom: "", couleurs: c.map((hex) => ({ hex, nom: "" })) })) });

export const nomGroupe = (g, t) => (g.nom ? g.nom : NOMS_GROUPES[g.id] ? t(NOMS_GROUPES[g.id]) : g.id);

// La couleur choisie passe en tête des récentes (sans doublon, 12 au plus).
export function ajouterRecente(etat, hex) {
  return { ...etat, recentes: [hex, ...etat.recentes.filter((h) => h !== hex)].slice(0, MAX_RECENTES) };
}
function idLibre(e) {
  let n = 1;
  while (e.groupes.some((x) => x.id === "g-" + n)) n++;
  return "g-" + n;
}
// Nouvelle nuance en fin du groupe `id` (à défaut le premier ; sans groupe du tout, un groupe est créé).
export function ajouterNuance(etat, id, hex, nom = "") {
  const e = copie(etat);
  const g = e.groupes.find((x) => x.id === id) || e.groupes[0];
  if (g) g.couleurs.push({ hex, nom });
  else e.groupes.push({ id: idLibre(e), nom: hex, couleurs: [{ hex, nom }] });
  return e;
}
// Nouveau groupe -> {etat, id} ou {erreur} ; un groupe créé porte toujours un nom.
export function nouveauGroupe(etat, nomBrut) {
  const nom = nomPropre(nomBrut);
  if (!nom) return { erreur: true };
  const e = copie(etat);
  const id = idLibre(e);
  e.groupes.push({ id, nom, couleurs: [] });
  return { etat: e, id };
}
export function renommerGroupe(etat, id, nomBrut) {
  const nom = nomPropre(nomBrut);
  if (!nom) return etat;
  const e = copie(etat);
  const g = e.groupes.find((x) => x.id === id);
  if (g) g.nom = nom;
  return e;
}
// sel = {groupe, index} (une nuance) ou {groupe} (le groupe entier).
export function supprimer(etat, sel) {
  if (!sel) return etat;
  const e = copie(etat);
  if (sel.index == null) e.groupes = e.groupes.filter((x) => x.id !== sel.groupe);
  else {
    const g = e.groupes.find((x) => x.id === sel.groupe);
    if (g && sel.index >= 0 && sel.index < g.couleurs.length) g.couleurs.splice(sel.index, 1);
  }
  return e;
}
// Recherche : nom de la nuance ou code hexadécimal ; les groupes vides après filtre disparaissent. Chaque nuance garde
// son index d'origine `i` (supprimer après un filtre vise la bonne).
export function filtrer(etat, texte) {
  const q = String(texte || "").trim().toLowerCase();
  const avecIndex = etat.groupes.map((g) => ({ ...g, couleurs: g.couleurs.map((c, i) => ({ ...c, i })) }));
  if (!q) return avecIndex;
  return avecIndex.map((g) => ({ ...g, couleurs: g.couleurs.filter((c) => c.hex.includes(q) || (c.nom && c.nom.toLowerCase().includes(q))) }))
    .filter((g) => g.couleurs.length);
}
// Clic sur une nuance : premier plan, ou arrière-plan avec Alt (référence).
export const cibleClic = (ev) => (ev && ev.altKey ? "background" : "foreground");

export function initNuancier(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const corps = PL.$("#corpsNuancier");
  if (!corps) return;
  let etat = etatDefaut();
  let sel = null;                      // {groupe, index?} : ce que Supprimer retire
  let fg = "#000000";
  const replies = new Set();
  let minut = null;

  const recherche = document.createElement("input");
  recherche.type = "search"; recherche.className = "pr-recherche"; recherche.placeholder = T("photolab.nuancier.rechercher");
  recherche.setAttribute("aria-label", T("photolab.nuancier.rechercher"));
  const recentes = document.createElement("div"); recentes.className = "nu-recentes";
  const liste = document.createElement("div"); liste.className = "pr-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  bouton("folder-plus", "photolab.nuancier.nouveau_groupe", async () => {
    const r = nouveauGroupe(etat, await demanderNom(PL, T("photolab.nuancier.nouveau_groupe")));
    if (!r.erreur) { etat = r.etat; sel = { groupe: r.id }; changer(); }
  });
  bouton("plus", "photolab.nuancier.nouvelle_nuance", () => {
    const g = sel ? sel.groupe : (etat.groupes.find((x) => x.id.startsWith("g-")) || etat.groupes[0] || {}).id;
    etat = ajouterNuance(etat, g, fg);
    changer();
  });
  const bSuppr = bouton("trash-2", "photolab.nuancier.supprimer", () => { etat = supprimer(etat, sel); sel = null; changer(); });
  corps.append(recherche, recentes, liste, pied);
  if (PL.hydraterIcones) PL.hydraterIcones(pied);
  recherche.addEventListener("input", dessiner);

  async function choisir(hex, ev) {
    try { await PL.post("/executer", { command: "tools.setColors", params: { [cibleClic(ev)]: hex } }); } catch (e) { return; }
    etat = ajouterRecente(etat, hex);
    changer();
    if (PL.relireCouleurs) PL.relireCouleurs();
  }
  function pastille(hex, nom, choisie) {
    const b = document.createElement("button"); b.type = "button"; b.className = "nu-pastille" + (choisie ? " choisie" : "");
    b.style.background = hex; b.title = nom ? nom + " (" + hex + ")" : hex; b.setAttribute("aria-label", b.title);
    if (nom) b.setAttribute("data-dz-brut", "");
    b.addEventListener("click", (ev) => choisir(hex, ev));
    return b;
  }
  function dessiner() {
    recentes.textContent = "";
    for (const h of etat.recentes) recentes.appendChild(pastille(h, "", false));
    recentes.hidden = !etat.recentes.length;
    liste.textContent = "";
    for (const g of filtrer(etat, recherche.value)) {
      const tete = document.createElement("div");
      tete.className = "pr-groupe" + (sel && sel.groupe === g.id && sel.index == null ? " choisi" : "");
      const fl = document.createElement("button"); fl.type = "button"; fl.className = "pr-fleche"; fl.textContent = replies.has(g.id) ? "▸" : "▾";
      fl.setAttribute("aria-label", T(replies.has(g.id) ? "photolab.presets.deplier" : "photolab.presets.replier"));
      fl.addEventListener("click", () => { if (replies.has(g.id)) replies.delete(g.id); else replies.add(g.id); dessiner(); });
      const nom = document.createElement("span"); nom.className = "pr-nom"; nom.textContent = nomGroupe(g, T);
      if (g.nom) nom.setAttribute("data-dz-brut", "");
      nom.addEventListener("click", () => { sel = { groupe: g.id }; dessiner(); });
      nom.addEventListener("dblclick", async () => {
        const n = await demanderNom(PL, T("commun.action.renommer"), nomGroupe(g, T));
        if (n) { etat = renommerGroupe(etat, g.id, n); changer(); }
      });
      tete.append(fl, nom);
      liste.appendChild(tete);
      if (replies.has(g.id)) continue;
      const grille = document.createElement("div"); grille.className = "nu-grille";
      for (const c of g.couleurs) {
        const b = pastille(c.hex, c.nom, !!sel && sel.groupe === g.id && sel.index === c.i);
        b.addEventListener("contextmenu", (ev) => { ev.preventDefault(); sel = { groupe: g.id, index: c.i }; dessiner(); });
        grille.appendChild(b);
      }
      liste.appendChild(grille);
    }
    bSuppr.disabled = !sel;
  }
  function changer() {
    dessiner();
    clearTimeout(minut);
    minut = setTimeout(async () => {
      try { etat = await PL.api("PUT", "/nuancier", etat); } catch (e) { /* signalé par mod-api */ }
    }, 300);
  }
  PL.surCouleurs = PL.surCouleurs || [];
  PL.surCouleurs.push((c) => { if (c && c.fg) fg = c.fg; });
  PL.nuancier = { etat: () => etat, sel: () => sel };
  PL.get("/nuancier", true).then((e) => { if (e && Array.isArray(e.groupes)) etat = e; dessiner(); }).catch(() => dessiner());
}
