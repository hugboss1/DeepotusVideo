// mod-recherche.js — t156 (parité L6) : Édition › Rechercher… (palette de l'amont palette.rs) : une recherche dans les
// entrées de menu ACTIVES (libellé affiché, libellé anglais, chemin) et les outils ; ↑ ↓ choisir, Entrée exécuter, Échap
// fermer. Une entrée passe par le même chemin qu'un clic dans le menu (PL.menus.activer) ; un outil est choisi.
// Fonctions PURES exportées (qa/texte.test.mjs, section recherche).

const sansAccent = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// Entrées de commande actives de l'arbre des menus, avec leur chemin affiché.
export function entreesCherchables(menus) {
  const out = [];
  const voir = (es, chemin) => {
    for (const e of es || []) {
      if (e.type === "sous-menu") voir(e.entrees, [...chemin, e.nom_affiche || e.nom]);
      else if (e.type === "commande" && e.etat === "actif" && e.id !== "edit.search") out.push({ sorte: "menu", entree: e, libelle: String(e.libelle || "").replace(/…$/, ""), chemin: chemin.join(" › ") });
    }
  };
  for (const m of menus || []) voir(m.entrees, [m.nom_affiche || m.nom]);
  return out;
}
// Score de correspondance (0 = aucune) : début de mot > contenu > sous-suite ; les outils ont +2 (amont).
export function score(q, texte) {
  const a = sansAccent(q).trim(), b = sansAccent(texte);
  if (!a) return 0;
  if (b.startsWith(a)) return 100 - Math.min(50, b.length - a.length);
  const i = b.indexOf(a);
  if (i >= 0) return (/\s|›/.test(b[i - 1] || " ") ? 60 : 40) - Math.min(20, i);
  let j = 0;
  for (const c of b) if (c === a[j]) j++;
  return j === a.length ? 10 : 0;
}
// Le chemin (« Calque › … ») ne compte que s'il CONTIENT la recherche : une sous-suite sur le chemin ramenait du bruit.
export function chercher(q, elements, max = 12) {
  const a = sansAccent(q).trim();
  const parChemin = (e) => (a && sansAccent(e.chemin + " " + e.libelle).includes(a) ? 30 : 0);
  return elements.map((e) => { const s = Math.max(score(q, e.libelle), parChemin(e)); return { e, s: s > 0 && e.sorte === "outil" ? s + 2 : s }; })
    .filter((x) => x.s > 0).sort((x, y) => y.s - x.s).slice(0, max).map((x) => x.e);
}

export function initRecherche(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let boite = null;
  function fermer() { if (boite) { boite.remove(); boite = null; } }
  function ouvrir() {
    if (boite) { fermer(); return; }
    const outils = (PL.outilsCherchables ? PL.outilsCherchables() : []).map((o) => ({ sorte: "outil", id: o.id, libelle: o.nom, chemin: T("photolab.recherche.outils") }));
    const elements = [...entreesCherchables(PL.menus && PL.menus.arbre), ...outils];
    boite = document.createElement("div"); boite.className = "rc-palette"; boite.setAttribute("role", "dialog"); boite.setAttribute("aria-label", T("photolab.recherche.titre"));
    const champ = Object.assign(document.createElement("input"), { type: "search", className: "rc-champ", placeholder: T("photolab.recherche.indice") });
    const liste = document.createElement("div"); liste.className = "rc-liste"; liste.setAttribute("role", "listbox");
    boite.append(champ, liste);
    document.body.appendChild(boite);
    let res = [], k = 0;
    const executer = (e) => {
      fermer();
      if (!e) return;
      if (e.sorte === "outil") { if (PL.choisirOutil) PL.choisirOutil(e.id); return; }
      if (PL.menus && PL.menus.activer) PL.menus.activer(e.entree);
    };
    const dessiner = () => {
      liste.textContent = "";
      res.forEach((e, i) => {
        const l = document.createElement("div"); l.className = "rc-ligne" + (i === k ? " actif" : ""); l.setAttribute("role", "option");
        const a = document.createElement("span"); a.className = "rc-lib"; a.textContent = e.libelle;
        const c = document.createElement("span"); c.className = "rc-chemin"; c.textContent = e.chemin;
        l.append(a, c);
        l.addEventListener("pointerdown", (ev) => { ev.preventDefault(); executer(e); });
        liste.appendChild(l);
      });
      if (champ.value.trim() && !res.length) { const v = document.createElement("div"); v.className = "rc-vide"; v.textContent = T("photolab.recherche.aucun"); liste.appendChild(v); }
    };
    champ.addEventListener("input", () => { res = chercher(champ.value, elements); k = 0; dessiner(); });
    champ.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); }
      else if (ev.key === "ArrowDown") { ev.preventDefault(); k = Math.min(res.length - 1, k + 1); dessiner(); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); k = Math.max(0, k - 1); dessiner(); }
      else if (ev.key === "Enter") { ev.preventDefault(); executer(res[k]); }
    });
    champ.addEventListener("blur", () => setTimeout(fermer, 150));
    setTimeout(() => champ.focus(), 0);
  }
  PL.actions = PL.actions || {};
  PL.actions["edit.search"] = ouvrir;
  PL.recherche = { ouvrir, fermer, ouverte: () => !!boite };
}
