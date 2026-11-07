// mod-objets.js — t411 (Photolab N1, photocraft 0.21) : Calque › Objets dynamiques › Remplacer le contenu… et Exporter le
// contenu… Les commandes moteur de ces noms refusent tout chemin : l'écran passe par /objets/remplacer (image de la
// Bibliothèque) et /objets/exporter (PNG déposé dans la Bibliothèque).
import { IDS_OBJETS } from "./mod-menus.js";
import { trouverCalque } from "./mod-calques.js";

export const estObjetDynamique = (calque) => !!calque && calque.kind === "Smart Object";

// Ces deux entrées n'ont de sens que sur un objet dynamique : grisées ailleurs, comme chez la référence.
export function decorerObjets(menus, calque) {
  const inactif = !estObjetDynamique(calque);
  const voir = (l) => l.map((e) => {
    if (e.type === "sous-menu") return { ...e, entrees: voir(e.entrees) };
    return e.type === "commande" && inactif && IDS_OBJETS.includes(e.id) ? { ...e, etat: "inactif" } : e;
  });
  return menus.map((m) => ({ ...m, entrees: voir(m.entrees) }));
}

export function initObjets(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => decorerObjets(menus, PL.etat.doc ? trouverCalque(PL.etat.doc.layers, PL.etat.doc.activeLayer) : null));

  PL.actions["layer.smartObjects.replaceContents"] = () => {
    if (!PL.etat.doc || !PL.choisirImage) return;
    PL.choisirImage(T("photolab.objets.remplacer_choisir"), async (nom) => {
      if (!nom) return;
      try { await PL.file(() => PL.post("/objets/remplacer", { filename: nom })); } catch (e) { return; }
      await PL.cycle();
      PL.signaler(T("photolab.objets.remplace", { nom }));
    });
  };

  PL.actions["layer.smartObjects.exportContents"] = async () => {
    if (!PL.etat.doc) return;
    let r = null;
    try { r = await PL.file(() => PL.post("/objets/exporter", {})); } catch (e) { return; }
    PL.signaler(T("photolab.objets.exporte", { nom: (r.filenames || [])[0] || "" }));
  };
}
