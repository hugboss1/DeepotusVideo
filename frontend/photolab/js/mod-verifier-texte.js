// mod-verifier-texte.js — #415 (relevé du 20/10/2026) : Texte › Résoudre les polices manquantes… et Édition › Vérifier
// l'orthographe…, deux entrées qui s'exécutaient sans montrer ce que le moteur rendait (la liste était jetée). Le moteur
// fait tout : type.resolveMissingFonts {} liste les familles absentes, {map} les remplace ; edit.checkSpelling liste les
// fautes ({misspellings: [{layer, start, end, word, suggestions}]}) puis change, change partout ou ajoute au dictionnaire.
// L'écran ne fait que les dialogues. Fonctions PURES exportées (qa/defauts-menus.test.mjs).
import { brut } from "./mod-cycle.js";
import { ouvrirDialogue } from "./mod-fichier.js";

export const IDS_VERIF_TEXTE = ["type.resolveMissingFonts", "edit.checkSpelling"];

// Choix du dialogue (famille manquante -> famille installée, "" = laissée) -> paramètres, ou null si rien n'est remplacé.
export function remplacementsPolices(manquantes, choix) {
  const map = {};
  for (const f of Array.isArray(manquantes) ? manquantes : []) {
    const v = choix && typeof choix[f] === "string" ? choix[f] : "";
    if (v) map[f] = v;
  }
  return Object.keys(map).length ? { map } : null;
}

// Une occurrence de faute (Ignorer ne saute qu'elle ; Tout ignorer passe par `ignore` du moteur).
export const cleFaute = (f) => [f.layer, f.start, f.word].join("|");
export function fauteSuivante(liste, sautees) {
  for (const f of Array.isArray(liste) ? liste : []) if (f && !sautees.has(cleFaute(f))) return f;
  return null;
}
// Paramètres de edit.checkSpelling pour un geste sur cette faute ; null si le remplacement est vide.
export function paramsCorrection(f, action, remplacement = "") {
  if (action === "addToDictionary") return { action, word: f.word };
  const r = String(remplacement || "").trim();
  if (!r) return null;
  if (action === "changeAll") return { action, word: f.word, replace: r };
  return { action: "change", layer: f.layer, start: f.start, end: f.end, word: f.word, replace: r };
}

/* ───────────── côté DOM ───────────── */

export function initVerifierTexte(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lire = async (command, params) => {
    const r = await PL.executer(command, params, { cycle: false });
    return r && r.ok ? r.r : null;
  };

  async function polices() {
    const r = await lire("type.resolveMissingFonts", {});
    const manquantes = r && Array.isArray(r.missing) ? r.missing : null;
    if (!manquantes) return;
    if (!manquantes.length) { PL.signaler(T("photolab.polices.aucune")); return; }
    let installees = [];
    try { const f = await PL.post("/executer", { command: "type.fonts", params: {} }); installees = (f && f.families) || []; } catch (e) { return; }
    let params = null;
    await ouvrirDialogue(PL, {
      titre: T("photolab.polices.titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.polices.remplacer"), principal: true }],
      construire({ corps }) {
        const intro = document.createElement("p"); intro.className = "pl-note"; intro.textContent = T("photolab.polices.intro");
        corps.appendChild(intro);
        const selects = {};
        for (const m of manquantes) {
          const l = document.createElement("label"); l.className = "pl-champ";
          const nom = brut(document.createElement("span")); nom.textContent = m;
          const s = document.createElement("select");
          const garder = document.createElement("option"); garder.value = ""; garder.textContent = T("photolab.polices.garder"); s.appendChild(garder);
          for (const f of installees) { const o = brut(document.createElement("option")); o.value = f; o.textContent = f; s.appendChild(o); }
          selects[m] = s;
          l.append(nom, s); corps.appendChild(l);
        }
        return () => { params = remplacementsPolices(manquantes, Object.fromEntries(Object.entries(selects).map(([k, s]) => [k, s.value]))); return true; };
      },
    });
    if (params) await PL.executer("type.resolveMissingFonts", params);
  }

  async function orthographe() {
    const ignores = [];                         // Tout ignorer : la liste `ignore` de chaque relecture
    const sautees = new Set();                  // Ignorer : cette occurrence seulement
    const relire = async () => { const r = await lire("edit.checkSpelling", { action: "list", ...(ignores.length ? { ignore: ignores } : {}) }); return r ? r.misspellings : null; };
    let liste = await relire();
    if (!liste) return;
    if (!fauteSuivante(liste, sautees)) { PL.signaler(T("photolab.orthographe.aucune")); return; }
    let change = false;
    await ouvrirDialogue(PL, {
      titre: T("photolab.orthographe.titre"),
      boutons: [{ role: "annuler", libelle: T("commun.action.fermer") }],
      construire({ corps, fermer }) {
        const mot = brut(document.createElement("input")); mot.type = "text"; mot.readOnly = true;
        const rempl = brut(document.createElement("input")); rempl.type = "text"; rempl.maxLength = 256;
        const sugg = document.createElement("select"); sugg.size = 5; sugg.className = "pl-orthographe-suggestions";
        const ligne = (cle, el) => { const l = document.createElement("label"); l.className = "pl-champ"; const s = document.createElement("span"); s.textContent = T(cle); l.append(s, el); return l; };
        const actions = document.createElement("div"); actions.className = "pl-orthographe-actions";
        const bouton = (cle, f) => { const b = document.createElement("button"); b.type = "button"; b.className = "pl-bouton"; b.textContent = T(cle); b.addEventListener("click", f); actions.appendChild(b); return b; };
        let f = null;
        const montrer = () => {
          f = fauteSuivante(liste, sautees);
          if (!f) { PL.signaler(T("photolab.orthographe.fini")); fermer("ok"); return; }
          mot.value = f.word; sugg.textContent = "";
          for (const s of f.suggestions || []) { const o = brut(document.createElement("option")); o.value = s; o.textContent = s; sugg.appendChild(o); }
          rempl.value = (f.suggestions || [])[0] || f.word;
          if (sugg.options.length) sugg.selectedIndex = 0;
        };
        sugg.addEventListener("change", () => { rempl.value = sugg.value; });
        const corriger = async (action) => {
          const p = paramsCorrection(f, action, rempl.value);
          if (!p) return;
          if (!(await lire("edit.checkSpelling", p))) return;
          if (action !== "addToDictionary") change = true;
          liste = (await relire()) || []; montrer();
        };
        bouton("photolab.orthographe.ignorer", () => { sautees.add(cleFaute(f)); montrer(); });
        bouton("photolab.orthographe.tout_ignorer", async () => { ignores.push(f.word); liste = (await relire()) || []; montrer(); });
        bouton("photolab.orthographe.changer", () => corriger("change"));
        bouton("photolab.orthographe.tout_changer", () => corriger("changeAll"));
        bouton("photolab.orthographe.ajouter", () => corriger("addToDictionary"));
        corps.append(ligne("photolab.orthographe.absent", mot), ligne("photolab.orthographe.remplacer_par", rempl),
          ligne("photolab.orthographe.suggestions", sugg), actions);
        montrer();
        return null;
      },
    });
    if (change) PL.cycle();                      // les calques de texte ont changé : un seul cycle à la fermeture
  }

  PL.actions = PL.actions || {};
  PL.actions["type.resolveMissingFonts"] = polices;
  PL.actions["edit.checkSpelling"] = orthographe;
}
