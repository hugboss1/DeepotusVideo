// mod-clavier.js — t159 (parité L9) : Édition › Raccourcis clavier et Édition › Menus. Un jeu PERSONNEL de raccourcis
// (commandes des menus : Ctrl / Alt / touches de fonction ; outils : une lettre) et des menus personnalisés (éléments
// masqués, couleurs), gardés dans les préférences de l'écran (PL.prefs, dossier de données Deepotus). Le moteur n'est
// jamais appelé : edit.keyboardShortcuts / edit.menus écriraient ses préférences. Les menus sont décorés après tous
// les autres modules (raccourcis affichés = raccourcis actifs, mod-raccourcis les indexe tels quels) ; un élément
// masqué garde son raccourci, comme chez photocraft. Fonctions PURES exportées (qa/clavier.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";
import { normaliser, aIntercepter, RACCOURCIS_ECRAN } from "./mod-raccourcis.js";
import { EMPLACEMENTS, cleNom } from "./mod-outils.js";

export const COULEURS_MENU = ["red", "orange", "yellow", "green", "blue", "violet", "gray"];
export const NON_MASQUABLES = ["edit.menus", "edit.keyboardShortcuts", "edit.preferences.general"];
// Lettres que l'écran garde : X échange, D remet les couleurs par défaut (mod-outils).
export const LETTRES_RESERVEES = ["x", "d"];
export const ID_TOUT_MONTRER = "pl.menus.tout";

// Touches nommées (le dictionnaire les dit : photolab.touche.<nom>) ; les flèches sont des signes.
export const TOUCHES_NOMMEES = ["delete", "backspace", "tab", "enter", "escape", "space", "home", "end", "pageup", "pagedown"];
const FLECHES = { arrowup: "↑", arrowdown: "↓", arrowleft: "←", arrowright: "→" };

// "ctrl+alt+shift+f5" -> "Ctrl+Alt+Maj+F5" (fr) / "Ctrl+Alt+Shift+F5" (en). `T` traduit les touches nommées.
export function comboAffiche(combo, lang = "fr", T = (c) => c) {
  if (!combo) return "";
  return combo.split("+").map((p) => (p === "ctrl" ? "Ctrl" : p === "alt" ? "Alt" : p === "shift" ? (lang === "fr" ? "Maj" : "Shift")
    : FLECHES[p] || (TOUCHES_NOMMEES.includes(p) ? T("photolab.touche." + p) : p.toUpperCase()))).join("+");
}

const copie = (o) => JSON.parse(JSON.stringify(o));
const pourChaque = (menus, f) => {
  const voir = (entrees) => { for (const e of entrees || []) { if (e.type === "sous-menu") voir(e.entrees); else if (e.type === "commande") f(e); } };
  for (const m of menus || []) voir(m.entrees);
};

// Raccourcis personnels appliqués : l'entrée surchargée affiche le sien ("" = retiré) ; une entrée dont le raccourci
// d'origine a été donné à une autre le perd. `raccourciDefaut` garde l'origine (éditeur, « Par défaut »).
export function appliquerRaccourcis(menus, commandes, lang = "fr", T) {
  const sortie = copie(menus);
  const pris = new Set(Object.values(commandes || {}).filter(Boolean));
  pourChaque(sortie, (e) => {
    e.raccourciDefaut = e.raccourci || "";
    if (Object.prototype.hasOwnProperty.call(commandes || {}, e.id)) e.raccourci = comboAffiche(commandes[e.id], lang, T);
    else if (e.raccourci && pris.has(normaliser(e.raccourci))) e.raccourci = "";
  });
  return sortie;
}

// Menus personnalisés : `masque` (rendu sauté, raccourci gardé) et `couleur` ; un menu qui cache quelque chose gagne
// « Afficher tous les éléments de menu ».
export function appliquerMenus(menus, { masques = [], couleurs = {} } = {}, { montrerCouleurs = true, montrerTout = false } = {}, T = (c) => c) {
  const sortie = copie(menus);
  const caches = new Set(montrerTout ? [] : masques.filter((id) => !NON_MASQUABLES.includes(id)));
  for (const m of sortie) {
    let n = 0;
    const voir = (entrees) => { for (const e of entrees || []) {
      if (e.type === "sous-menu") voir(e.entrees);
      else if (e.type === "commande") {
        if (caches.has(e.id)) { e.masque = true; n++; }
        if (montrerCouleurs && COULEURS_MENU.includes(couleurs[e.id])) e.couleur = couleurs[e.id];
      }
    } };
    voir(m.entrees);
    if (n) m.entrees = [...m.entrees, { type: "separateur" },
      { type: "commande", id: ID_TOUT_MONTRER, libelle: T("photolab.menus.tout"), raccourci: "", etat: "actif", champs: [] }];
  }
  return sortie;
}

// Commandes des menus, à plat, une fois chacune : {id, chemin (noms des menus), libelle, defaut, actuel} (combos normalisés).
export function listeCommandes(menus) {
  const L = [], vus = new Set();
  const voir = (entrees, chemin) => { for (const e of entrees || []) {
    if (e.type === "sous-menu") voir(e.entrees, [...chemin, e.nom_affiche]);
    else if (e.type === "commande" && e.id && e.id !== ID_TOUT_MONTRER && !vus.has(e.id)) {
      vus.add(e.id);
      L.push({ id: e.id, chemin, libelle: e.libelle, defaut: normaliser(e.raccourciDefaut ?? e.raccourci), actuel: normaliser(e.raccourci) });
    }
  } };
  for (const m of menus || []) voir(m.entrees, [m.nom_affiche]);
  return L;
}

// Combinaison effective de chaque commande avec les surcharges `commandes`.
export function effectif(liste, commandes) {
  const pris = new Set(Object.values(commandes).filter(Boolean));
  const m = new Map();
  for (const c of liste) {
    if (Object.prototype.hasOwnProperty.call(commandes, c.id)) m.set(c.id, commandes[c.id]);
    else m.set(c.id, c.defaut && !pris.has(c.defaut) ? c.defaut : "");
  }
  return m;
}

// Une combinaison peut-elle aller à une commande ? -> null | {raison: "forme"|"reserve"|"conflit", id?}
export function conflit(liste, commandes, id, combo) {
  if (!combo) return null;
  if (!aIntercepter(combo) || !/^(ctrl\+|alt\+|(shift\+)?f([1-9]|1[0-2])$)/.test(combo)) return { raison: "forme" };
  if (RACCOURCIS_ECRAN[combo] && RACCOURCIS_ECRAN[combo] !== id) return { raison: "reserve", id: RACCOURCIS_ECRAN[combo] };
  for (const [autre, c] of effectif(liste, commandes)) if (autre !== id && c === combo) return { raison: "conflit", id: autre };
  return null;
}

// Donne `combo` à `id` (et le retire à la commande qui l'avait). Revenir au défaut efface la surcharge.
export function assigner(liste, commandes, id, combo) {
  const c = { ...commandes };
  const k = conflit(liste, c, id, combo);
  if (k && k.raison !== "conflit") return c;
  if (k) c[k.id] = "";
  const d = (liste.find((x) => x.id === id) || {}).defaut || "";
  if (combo === d) delete c[id]; else c[id] = combo;
  return c;
}

// Outils : lettre effective (surcharge, sinon celle de la barre ; "" = aucune).
export const OUTILS = EMPLACEMENTS.flat();
export function lettreOutil(id, outils) {
  const o = OUTILS.find((x) => x.id === id);
  if (outils && Object.prototype.hasOwnProperty.call(outils, id)) return outils[id];
  return o ? o.lettre.toLowerCase() : "";
}
export const lettreAdmise = (l) => l === "" || (/^[a-z]$/.test(l) && !LETTRES_RESERVEES.includes(l));

// Résumé téléchargeable (Résumer…) : un HTML autonome, échappé.
const echapper = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
export function resume(liste, commandes, outils, lang, T) {
  const eff = effectif(liste, commandes);
  const lignes = liste.filter((c) => eff.get(c.id)).map((c) => `<tr><td>${echapper(c.chemin.join(" › "))} › ${echapper(c.libelle)}</td><td>${echapper(comboAffiche(eff.get(c.id), lang, T))}</td></tr>`);
  const lo = OUTILS.filter((o) => lettreOutil(o.id, outils)).map((o) => `<tr><td>${echapper(T(cleNom(o.id)))}</td><td>${echapper(lettreOutil(o.id, outils).toUpperCase())}</td></tr>`);
  return `<!doctype html><html lang="${lang}"><head><meta charset="utf-8"><title>${echapper(T("photolab.clavier.titre"))}</title>`
    + `<style>body{font:14px system-ui;margin:24px}td{padding:2px 12px 2px 0;border-bottom:1px solid #ddd}h2{margin-top:24px}</style></head><body>`
    + `<h1>${echapper(T("photolab.clavier.titre"))}</h1><h2>${echapper(T("photolab.clavier.menus"))}</h2><table>${lignes.join("")}</table>`
    + `<h2>${echapper(T("photolab.clavier.outils"))}</h2><table>${lo.join("")}</table></body></html>`;
}

/* ───────────── côté DOM ───────────── */

export function initClavier(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  let montrerTout = false;
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };

  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => {
    const e = PL.prefs ? PL.prefs.etat : null;
    if (!e) return menus;
    const m = appliquerRaccourcis(menus, e.raccourcis.commandes, lang(), T);
    return appliquerMenus(m, e.menus, { montrerCouleurs: e.prefs.interface.showMenuColors, montrerTout }, T);
  });
  PL.actions = PL.actions || {};
  PL.actions[ID_TOUT_MONTRER] = () => { montrerTout = true; if (PL.menus) PL.menus.redessiner(); };
  // lettres d'outils personnalisées : lues par mod-outils au moment de la frappe
  PL.lettresOutils = () => (PL.prefs ? PL.prefs.etat.raccourcis.outils : {});

  function telecharger(nom, texte, type) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([texte], { type }));
    a.download = nom;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  /* Raccourcis clavier */
  async function raccourcis() {
    const liste = listeCommandes(PL.menus ? PL.menus.arbre : []);
    let cmd = { ...PL.prefs.etat.raccourcis.commandes }, outils = { ...PL.prefs.etat.raccourcis.outils };
    let onglet = "menus";
    await ouvrirDialogue(PL, {
      titre: T("photolab.clavier.titre"), classe: "large pl-clavier",
      boutons: [
        { role: "resumer", libelle: T("photolab.clavier.resumer") },
        { role: "defaut", libelle: T("photolab.clavier.tout_defaut") },
        { role: "annuler", libelle: T("commun.action.annuler") },
        { role: "ok", libelle: T("commun.action.valider"), principal: true },
      ],
      construire({ corps }) {
        const tete = el("div", "cl-tete");
        const choix = el("select"); choix.setAttribute("aria-label", T("photolab.clavier.pour"));
        for (const [v, k] of [["menus", "photolab.clavier.menus"], ["outils", "photolab.clavier.outils"]]) { const o = el("option", null, T(k)); o.value = v; choix.appendChild(o); }
        const filtre = el("input"); filtre.type = "search"; filtre.placeholder = T("commun.action.rechercher");
        const message = el("p", "cl-message"); message.setAttribute("role", "status");
        tete.append(choix, filtre);
        const table = el("div", "cl-liste");
        corps.append(tete, table, message);
        choix.addEventListener("change", () => { onglet = choix.value; dessiner(); });
        filtre.addEventListener("input", () => dessiner());

        function saisie(valeur, surTouche) {
          const i = el("input", "cl-saisie"); i.type = "text"; i.readOnly = true; i.value = valeur;
          i.addEventListener("keydown", (ev) => {
            if (ev.key === "Tab") return;
            ev.preventDefault(); ev.stopPropagation();
            if (ev.key === "Backspace" || ev.key === "Delete") { surTouche(""); return; }
            surTouche(ev);
          });
          return i;
        }
        function dessiner() {
          const q = filtre.value.trim().toLowerCase();
          table.replaceChildren();
          message.textContent = "";
          if (onglet === "menus") {
            const eff = effectif(liste, cmd);
            for (const c of liste) {
              const nom = `${c.chemin.join(" › ")} › ${c.libelle}`;
              if (q && !nom.toLowerCase().includes(q)) continue;
              const ligne = el("div", "cl-ligne"); ligne.dataset.id = c.id;
              const reserve = Object.values(RACCOURCIS_ECRAN).includes(c.id);
              const i = saisie(comboAffiche(eff.get(c.id), lang(), T), (ev) => {
                const combo = typeof ev === "string" ? ev : normaliserEv(ev);
                if (combo === null) return;
                const k = conflit(liste, cmd, c.id, combo);
                if (k && k.raison === "forme") { message.textContent = T("photolab.clavier.forme"); return; }
                if (k && k.raison === "reserve") { message.textContent = T("photolab.clavier.reserve"); return; }
                if (k) {
                  const autre = liste.find((x) => x.id === k.id);
                  message.textContent = T("photolab.clavier.conflit", { combo: comboAffiche(combo, lang(), T), commande: autre ? autre.libelle : k.id });
                }
                cmd = assigner(liste, cmd, c.id, combo);
                const garde = message.textContent;
                dessiner(); message.textContent = garde;
              });
              i.disabled = reserve;
              const def = el("button", "pl-bouton cl-defaut", T("photolab.clavier.defaut")); def.type = "button";
              def.disabled = reserve || !Object.prototype.hasOwnProperty.call(cmd, c.id);
              def.addEventListener("click", () => { const n = { ...cmd }; delete n[c.id]; cmd = n; dessiner(); });
              ligne.append(el("span", "cl-nom", nom), i, def);
              table.appendChild(ligne);
            }
          } else {
            for (const o of OUTILS.filter((x) => x.p2)) {
              const nom = T(cleNom(o.id));
              if (q && !nom.toLowerCase().includes(q)) continue;
              const ligne = el("div", "cl-ligne"); ligne.dataset.id = o.id;
              const i = saisie(lettreOutil(o.id, outils).toUpperCase(), (ev) => {
                const l = typeof ev === "string" ? ev : (ev.key && ev.key.length === 1 && !ev.ctrlKey && !ev.altKey && !ev.metaKey ? ev.key.toLowerCase() : null);
                if (l === null) return;
                if (!lettreAdmise(l)) { message.textContent = T("photolab.clavier.lettre"); return; }
                outils = { ...outils };
                if (l === o.lettre.toLowerCase()) delete outils[o.id]; else outils[o.id] = l;
                dessiner();
              });
              const def = el("button", "pl-bouton cl-defaut", T("photolab.clavier.defaut")); def.type = "button";
              def.disabled = !Object.prototype.hasOwnProperty.call(outils, o.id);
              def.addEventListener("click", () => { outils = { ...outils }; delete outils[o.id]; dessiner(); });
              ligne.append(el("span", "cl-nom", nom), i, def);
              table.appendChild(ligne);
            }
          }
        }
        dessiner();
        return async (role) => {
          if (role === "resumer") {
            telecharger(T("photolab.clavier.fichier_resume") + ".html", resume(liste, cmd, outils, lang(), T), "text/html");
            return false;
          }
          if (role === "defaut") { cmd = {}; outils = {}; dessiner(); return false; }
          try { await PL.prefs.modifier("raccourcis", { commandes: cmd, outils }); } catch (e) { return false; }
          PL.signaler(T("photolab.clavier.enregistres"));
          return true;
        };
      },
    });
  }
  // Événement clavier -> combinaison normalisée ; null pour une touche de modification seule.
  function normaliserEv(ev) {
    let k = (ev.key || "").toLowerCase();
    if (/^(control|shift|alt|meta|altgraph|os)$/.test(k)) return null;
    if (k === " ") k = "space";
    else if (k === "esc") k = "escape";
    else if (k.length !== 1 && !/^f\d{1,2}$/.test(k) && !TOUCHES_NOMMEES.includes(k) && !FLECHES[k]) {
      const m = /^(?:Key([A-Z])|Digit(\d))$/.exec(ev.code || "");
      if (!m) return null;
      k = (m[1] || m[2]).toLowerCase();
    }
    return [ev.ctrlKey || ev.metaKey ? "ctrl" : "", ev.altKey ? "alt" : "", ev.shiftKey ? "shift" : "", k].filter(Boolean).join("+");
  }

  /* Menus */
  async function menus() {
    const arbre = PL.menus ? PL.menus.arbre : [];
    let masques = new Set(PL.prefs.etat.menus.masques), couleurs = { ...PL.prefs.etat.menus.couleurs };
    await ouvrirDialogue(PL, {
      titre: T("photolab.menus.titre"), classe: "large pl-menus-perso",
      boutons: [
        { role: "defaut", libelle: T("photolab.clavier.tout_defaut") },
        { role: "annuler", libelle: T("commun.action.annuler") },
        { role: "ok", libelle: T("commun.action.valider"), principal: true },
      ],
      construire({ corps }) {
        const filtre = el("input"); filtre.type = "search"; filtre.placeholder = T("commun.action.rechercher");
        const table = el("div", "cl-liste");
        corps.append(filtre, table);
        filtre.addEventListener("input", () => dessiner());
        function dessiner() {
          const q = filtre.value.trim().toLowerCase();
          table.replaceChildren();
          for (const c of listeCommandes(arbre)) {
            const nom = `${c.chemin.join(" › ")} › ${c.libelle}`;
            if (q && !nom.toLowerCase().includes(q)) continue;
            const ligne = el("div", "cl-ligne"); ligne.dataset.id = c.id;
            const vis = el("input"); vis.type = "checkbox"; vis.checked = !masques.has(c.id); vis.title = T("photolab.menus.visible");
            vis.disabled = NON_MASQUABLES.includes(c.id);
            vis.addEventListener("change", () => { if (vis.checked) masques.delete(c.id); else masques.add(c.id); });
            const coul = el("select");
            for (const v of ["", ...COULEURS_MENU]) { const o = el("option", null, T("photolab.menus.couleur." + (v || "aucune"))); o.value = v; coul.appendChild(o); }
            coul.value = couleurs[c.id] || "";
            coul.addEventListener("change", () => { couleurs = { ...couleurs }; if (coul.value) couleurs[c.id] = coul.value; else delete couleurs[c.id]; ligne.dataset.couleur = coul.value; });
            ligne.dataset.couleur = coul.value;
            ligne.append(vis, el("span", "cl-nom", nom), coul);
            table.appendChild(ligne);
          }
        }
        dessiner();
        return async (role) => {
          if (role === "defaut") { masques = new Set(); couleurs = {}; dessiner(); return false; }
          try { await PL.prefs.modifier("menus", { masques: [...masques], couleurs }); } catch (e) { return false; }
          montrerTout = false;
          return true;
        };
      },
    });
  }

  PL.actions["edit.keyboardShortcuts"] = raccourcis;
  PL.actions["edit.menus"] = menus;
  PL.clavier = { raccourcis, menus };
}
