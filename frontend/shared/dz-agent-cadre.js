// dz-agent-cadre.js — assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md) : le RÉPONDEUR des
// labs affichés dans un cadre intégré de la SPA (Vectorlab, Photolab, Spritelab, Tilelab). La SPA demande
// {dzAgent:"trouve", id, selecteur, libelle, texte, lang} ; le lab répond {dzAgent:"rect", id, rect|null} avec le
// rectangle de l'élément dans SON viewport. Même origine seulement, dans les deux sens. SOURCE : frontend/shared ;
// copie identique : frontend/dist/shared (banc backend/tests/test_agent_ecran.py).
// C4 : sur {dzAgent:"releve", id}, il rend {dzAgent:"visibles", id, items} — le relevé de SON écran (texte +
// infobulle des éléments visibles, borné), derrière la même garde d'origine et de source.
import { choisir, candidats, releverVisibles } from "./dz-agent-logique.js";

if (!window.__dzAgentCadre && window.parent !== window) {
  window.__dzAgentCadre = true;
  window.addEventListener("message", (ev) => {
    if (ev.origin !== location.origin || !ev.source || ev.source !== window.parent) return;
    const d = ev.data;
    if (d && d.dzAgent === "releve") {
      ev.source.postMessage({ dzAgent: "visibles", id: d.id, items: releverVisibles(document) }, location.origin);
      return;
    }
    if (!d || d.dzAgent !== "trouve" || typeof d.selecteur !== "string") return;
    let rect = null;
    try {
      // comme le tiroir : libelle (facultatif) = sous-élément dont le texte sert à la comparaison
      const c = candidats(document, d.selecteur, typeof d.libelle === "string" ? d.libelle : "");
      const i = choisir(c, { texte: d.texte }, d.lang === "en" ? "en" : "fr");
      if (i >= 0) {
        c[i].noeud.scrollIntoView({ block: "center" });
        const r = c[i].noeud.getBoundingClientRect();
        rect = { x: r.x, y: r.y, w: r.width, h: r.height };
      }
    } catch (e) { rect = null; }
    ev.source.postMessage({ dzAgent: "rect", id: d.id, rect }, location.origin);
  });
}
