// mod-recolorerui.js — lot D5 « Couleur et motif », T2 (t476) : Édition › Couleurs dans l'interface. Les entrées du
// menu Édition sont des actions « couleurs:<x> », résolues par mod-charpente (préfixe greffé par t476.py) ; les
// transformations viennent de mod-recolorer.js et s'appliquent à la SÉLECTION en une seule étape d'annulation. Saturer et
// Régler l'équilibre ouvrent un dialogue pré-rempli avec aperçu en direct (dialogue_apercu de D2).
import { T } from "./mod-i18n.js";
import { formulaire_dom } from "./mod-tracesui.js";
import { dialogue_apercu } from "./mod-repeterui.js";
import { op_couleurs_transformer, op_couleurs_fusion, inverser, niveaux_de_gris, saturer, equilibre } from "./mod-recolorer.js";

export function champs_equilibre(p = {}) {
  const nb = (id, lib, valeur) => ({ id, type: "nombre", libelle: T(lib), valeur, min: -100, max: 100, pas: 1 });
  return [
    { id: "mode", type: "choix", valeur: p.mode || "rvb", options: [["rvb", T("vectorlab.couleurs.o_rvb")], ["cmjn", T("vectorlab.couleurs.o_cmjn")]] },
    nb("a", "vectorlab.couleurs.c_a", p.a ?? 0), nb("b", "vectorlab.couleurs.c_b", p.b ?? 0),
    nb("c", "vectorlab.couleurs.c_c", p.c ?? 0), nb("d", "vectorlab.couleurs.c_d", p.d ?? 0)];
}

export function couleurs_actions(VL) {
  const etat = VL.etat;
  const sel = () => (etat.doc ? (etat.selection || []).slice() : []);
  const A = { demander: (spec) => formulaire_dom(spec) };
  A.dialogue = (spec, appliquer) => dialogue_apercu(VL, (s) => A.demander(s), spec, appliquer);
  const direct = (f) => ({ peut: () => sel().length >= 1, faire: async () => { VL.executer(op_couleurs_transformer, sel(), f); } });
  const fusion = (sens) => ({ peut: () => sel().length >= 1, faire: async () => { VL.executer(op_couleurs_fusion, sel(), sens); } });
  const ACTIONS = {
    inverser: direct(inverser),
    gris: direct(niveaux_de_gris),
    saturer: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await A.dialogue({ titre: T("vectorlab.couleurs.d_saturer"), champs: [{ id: "pct", type: "nombre", libelle: T("vectorlab.couleurs.c_pct"), valeur: 20, min: -100, max: 100, pas: 1 }] },
        (d, x) => op_couleurs_transformer(d, ids, (h) => saturer(h, x.pct)));
      if (v) VL.executer(op_couleurs_transformer, ids, (h) => saturer(h, v.pct));
    } },
    equilibre: { peut: () => sel().length >= 1, faire: async () => {
      const ids = sel();
      const v = await A.dialogue({ titre: T("vectorlab.couleurs.d_equilibre"), champs: champs_equilibre() }, (d, x) => op_couleurs_transformer(d, ids, (h) => equilibre(h, x)));
      if (v) VL.executer(op_couleurs_transformer, ids, (h) => equilibre(h, v));
    } },
    fusion_h: fusion("horizontal"),
    fusion_v: fusion("vertical"),
    fusion_z: fusion("avant_arriere"),
  };
  A.action = (nom) => ACTIONS[nom] || { peut: () => false, faire: () => {} };
  return A;
}

export function initRecolorerUI(VL) {
  const A = couleurs_actions(VL);
  VL.couleursUI = A;
  return A;
}
