// mod-proprietes.js — le panneau Propriétés (C2) : sans calque actif, le document (taille, résolution, mode,
// profondeur) ; avec un calque, son nom, son type, ses bornes et son opacité. Lecture seule en P2 (la modification passe
// par les panneaux Calques et les menus). Fonction PURE exportée (qa/panneaux.test.mjs).
import { trouverCalque } from "./mod-calques.js";
import { brut } from "./mod-cycle.js";

// doc.inspect -> {titre, lignes:[{libelle, valeur}]}. `t` = traducteur (dzT) injecté pour rester bancable sous node.
export function proprietesDe(doc, t = (c) => c, lang = "fr") {
  if (!doc) return { titre: "", lignes: [] };
  const c = doc.activeLayer != null ? trouverCalque(doc.layers, doc.activeLayer) : null;
  if (!c) {
    return {
      titre: t("photolab.proprietes.document"),
      lignes: [
        { libelle: t("photolab.proprietes.dimensions"), valeur: doc.width + " × " + doc.height + " px" },
        { libelle: t("photolab.nouveau.resolution"), valeur: (doc.resolution != null ? Math.round(doc.resolution * 100) / 100 : "—") + " ppi" },
        { libelle: t("photolab.option.mode"), valeur: String(doc.mode || "").toUpperCase() },
        { libelle: t("photolab.proprietes.profondeur"), valeur: (doc.depth || 8) + " bits" },
      ],
    };
  }
  const b = Array.isArray(c.bounds) ? c.bounds : null;
  const genre = String(c.kind || "").toLowerCase();
  const opac = Math.round((c.opacity ?? 1) * 100);
  return {
    titre: t("photolab.proprietes.calque"),
    lignes: [
      { libelle: t("photolab.nouveau.nom"), valeur: c.name || "", brut: true },      // nom saisi par l'utilisateur
      { libelle: t("photolab.proprietes.type"), valeur: genre ? t("photolab.type_calque." + genre) : "—" },
      { libelle: t("photolab.proprietes.bornes"), valeur: b ? b[0] + ", " + b[1] + " · " + b[2] + " × " + b[3] + " px" : "—" },
      { libelle: t("photolab.calques.opacite"), valeur: lang === "fr" ? opac + " %" : opac + "%" },
    ],
  };
}

export function initProprietes(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  const corps = PL.$("#corpsProprietes");
  function dessiner(doc) {
    corps.textContent = "";
    if (!doc) {
      const p = document.createElement("p"); p.className = "pr-vide"; p.textContent = T("photolab.proprietes.aucun"); corps.appendChild(p);
      return;
    }
    // Un type de calque inconnu du dictionnaire (le moteur en ajoutera) s'affiche tel que le moteur le nomme.
    const tr = (cle, vars) => { const s = T(cle, vars); return s === cle && cle.startsWith("photolab.type_calque.") ? cle.slice(21) : s; };
    const p = proprietesDe(doc, tr, lang());
    const h = document.createElement("h4"); h.className = "pr-titre"; h.textContent = p.titre;
    const dl = document.createElement("dl"); dl.className = "pr-liste";
    for (const l of p.lignes) {
      const dt = document.createElement("dt"); dt.textContent = l.libelle;
      const dd = document.createElement("dd"); dd.textContent = l.valeur;
      if (l.brut) brut(dd);                              // donnée de l'utilisateur : la surcouche n'y touche pas
      dl.append(dt, dd);
    }
    corps.append(h, dl);
  }
  PL.surDoc.push(dessiner);
  dessiner(null);
}
