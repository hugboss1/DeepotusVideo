// mod-vivants.js — t123 : les objets DÉRIVÉS d'un autre restent vivants.
//
// Deux dérivés existent, chacun avec un LIEN vers sa source et l'EMPREINTE (JSON) de la source au moment où il
// l'a lue :
//   * le texte sur chemin (`textechemin.chemin`) — il recopie le tracé et le transform de son chemin ;
//   * le contour décalé (`derive = {source, decalage, empreinte}`, posé par op_contour) — il recalcule son
//     décalage par les booléens.
// `derives_rafraichir` passe après CHAQUE commande (core.executer), sur le même clone : la source et son dérivé
// changent dans la même étape d'historique, et un Ctrl+Z les défait ensemble. Seule une empreinte qui a changé
// coûte un recalcul. Une source disparue, ou un retrait qui viderait la forme, laisse le dérivé à son dernier
// état — jamais une exception au rendu.
import { T } from "./mod-i18n.js";
import { forme_d } from "./mod-formes.js";
import { contour_d } from "./mod-bool.js";

function _index(doc) {
  const idx = new Map();
  const v = (objs) => { for (const o of objs || []) { idx.set(o.id, o); if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
  return idx;
}
function _tous(doc, fn) {
  const v = (objs) => { for (const o of objs || []) { fn(o); if (o.type === "groupe") v(o.enfants); } };
  for (const c of doc.calques) v(c.objets);
}

export function derives_rafraichir(doc) {
  const idx = _index(doc);
  let n = 0;
  _tous(doc, (o) => {
    if (o.type === "textechemin" && o.chemin) {
      const s = idx.get(o.chemin);
      if (!s || (s.type !== "path" && s.type !== "forme")) return;
      const e = JSON.stringify(s);
      if (e === o.empreinte) return;
      o.d = s.type === "forme" ? forme_d(s) : s.d;
      if (s.transform) o.transform = s.transform; else delete o.transform;
      o.empreinte = e;
      n++;
    } else if (o.derive && o.derive.source) {
      const s = idx.get(o.derive.source);
      if (!s) return;
      const e = JSON.stringify(s);
      if (e === o.derive.empreinte) return;
      try {
        o.d = contour_d(s, o.derive.decalage);
      } catch (err) {
        return;                     // le retrait viderait la forme : le dernier tracé reste (et sera retenté)
      }
      o.derive.empreinte = e;
      n++;
    }
  });
  return n;
}

// le dérivé redevient un objet ordinaire : il ne suit plus sa source
export function op_derive_detacher(doc, id) {
  const o = _index(doc).get(id);
  if (!o) throw new Error(T("vectorlab.vivants.err_introuvable", { id }));
  if (o.derive) { delete o.derive; return; }
  if (o.type === "textechemin" && o.chemin) { delete o.chemin; delete o.empreinte; return; }
  throw new Error(T("vectorlab.vivants.err_detacher", { id }));
}
