// dz-agent-pointeur.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md) :
// le pointeur à la Clicky du tiroir (/shared/dz-agent.js). Un curseur part de depart(), décrit un arc (courbe), puis
// un halo et une bulle se posent sur la cible. Calques éphémères, au-dessus de tout, transparents aux clics. Un seul
// pointage à la fois : chaque nouveau pointage (ou un clic que ignorer() ne retient pas) annule le précédent —
// animation, minuterie, écouteurs. SOURCE : frontend/shared ; copie identique : frontend/dist/shared (banc
// backend/tests/test_agent_ecran.py).
import { courbe } from "./dz-agent-logique.js";

const CSS = `
.dzAgentCurseur{position:fixed;left:0;top:0;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;z-index:2147483002;
 pointer-events:none;background:var(--cyan,#f0b429);box-shadow:0 0 16px 4px var(--cyan-glow,rgba(240,180,41,.33))}
.dzAgentHalo{position:fixed;z-index:2147483002;pointer-events:none;border:2px solid var(--cyan,#f0b429);border-radius:10px;
 box-shadow:0 0 0 4px var(--cyan-glow,rgba(240,180,41,.33)),0 0 24px var(--cyan-glow,rgba(240,180,41,.33));transition:opacity .4s}
.dzAgentBulle{position:fixed;z-index:2147483002;pointer-events:none;background:var(--bg-panel,#151519);color:var(--ink-strong,#eaf2ff);
 border:1px solid var(--cyan,#f0b429);border-radius:8px;padding:4px 8px;font-family:inherit;font-size:12px;font-weight:600;line-height:1.3;white-space:nowrap;transition:opacity .4s}
@media (prefers-reduced-motion: reduce){.dzAgentHalo,.dzAgentBulle{transition:none}}`;

// depart() : le point d'où part le curseur ; ignorer(el) : vrai si un pointerdown sur el ne doit PAS l'effacer
export function creerPointeur({ depart, ignorer }) {
  const style = document.createElement("style");
  style.textContent = CSS;
  const div = (classe, texte) => { const n = document.createElement("div"); n.className = classe; if (texte) n.textContent = texte; return n; };
  const reduit = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  let calques = [], anim = 0, minuterie = 0, suivre = null, interieur = null;

  function effacerPointeur() {
    if (anim) cancelAnimationFrame(anim);
    if (minuterie) clearTimeout(minuterie);
    anim = 0; minuterie = 0;
    if (suivre) { window.removeEventListener("scroll", suivre, true); window.removeEventListener("resize", suivre); suivre = null; }
    if (interieur) {                                  // écouteurs posés DANS le lab et pas encore servis
      const w = interieur; interieur = null;
      try { w.removeEventListener("pointerdown", effacerPointeur, true); w.removeEventListener("scroll", effacerPointeur, true); } catch (e) { /* lab parti */ }
    }
    calques.forEach((c) => c.remove());
    calques = [];
  }

  // cible : un nœud DOM, ou {rect: () => ({x, y, w, h}) | null} pour un élément d'un lab en cadre intégré ;
  // fenetre (facultatif) : la fenêtre du lab, dont le premier clic ou défilement intérieur efface le pointeur.
  // Une cible disparue (rect null, nœud détaché) efface le pointeur au lieu de le poser au mauvais endroit.
  function montrer(cible, libelle, fenetre) {
    effacerPointeur();
    if (!style.isConnected) document.head.appendChild(style);
    const mesurer = cible.rect ? () => {
      const q = cible.rect();
      return q ? { x: q.x, y: q.y, width: q.w, height: q.h, bottom: q.y + q.h } : null;
    } : () => (cible.isConnected ? cible.getBoundingClientRect() : null);
    const dep = depart();
    const curseur = div("dzAgentCurseur");
    const halo = div("dzAgentHalo");
    const bulle = div("dzAgentBulle", libelle);
    halo.style.opacity = "0"; bulle.style.opacity = "0";
    curseur.style.transform = `translate(${dep.x}px,${dep.y}px)`;
    document.body.append(curseur, halo, bulle);
    calques = [curseur, halo, bulle];
    let arrivee = dep, pose = false;
    // recalcule la place de la cible : au départ, puis à chaque défilement / redimensionnement (même pendant l'arc)
    const placer = () => {
      const r = mesurer();
      if (!r) { effacerPointeur(); return false; }
      arrivee = { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      Object.assign(halo.style, { left: r.x - 6 + "px", top: r.y - 6 + "px", width: r.width + 12 + "px", height: r.height + 12 + "px" });
      const hb = bulle.offsetHeight || 24, lb = bulle.offsetWidth || 0;
      const haut = r.y - hb - 10 >= 8 ? r.y - hb - 10 : r.bottom + 10;          // au-dessus, sinon en dessous
      bulle.style.left = Math.max(8, Math.min(r.x, window.innerWidth - lb - 8)) + "px";
      bulle.style.top = Math.max(8, Math.min(haut, window.innerHeight - hb - 8)) + "px";
      if (pose) curseur.style.transform = `translate(${arrivee.x}px,${arrivee.y}px)`;
      return true;
    };
    if (!placer()) return;
    suivre = () => placer();
    if (fenetre) {
      try {
        for (const e of ["pointerdown", "scroll"]) fenetre.addEventListener(e, effacerPointeur, { capture: true, once: true });
        interieur = fenetre;
      } catch (e) { /* fenêtre inaccessible : la minuterie et Échap suffisent */ }
    }
    window.addEventListener("scroll", suivre, { capture: true, passive: true });
    window.addEventListener("resize", suivre);
    const finir = () => {
      anim = 0; pose = true;
      curseur.style.transform = `translate(${arrivee.x}px,${arrivee.y}px)`;
      halo.style.opacity = "1"; bulle.style.opacity = "1";
      minuterie = setTimeout(effacerPointeur, 3200);
    };
    if (reduit()) return finir();
    const debut = performance.now(), duree = 700;
    const pas = (t) => {
      const k = Math.max(0, Math.min(1, (t - debut) / duree));
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;         // ease-in-out
      const p = courbe(dep, arrivee, e);
      curseur.style.transform = `translate(${p.x}px,${p.y}px)`;
      if (k < 1) anim = requestAnimationFrame(pas); else finir();
    };
    anim = requestAnimationFrame(pas);
  }
  document.addEventListener("pointerdown", (ev) => { if (calques.length && !ignorer(ev.target)) effacerPointeur(); }, true);

  return { montrer, effacer: effacerPointeur, actif: () => calques.length > 0 };
}
