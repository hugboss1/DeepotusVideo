// mod-pipette.js — l'outil Pipette (C3) : clic = document.pixel (composite, RGBA flottant) puis tools.setColors
// {foreground} ; Alt+clic = {background}. Les pastilles et le panneau Couleur relisent la session du moteur.
// Fonctions PURES exportées (qa/gestes.test.mjs).
import { rgbaVersHex } from "./mod-outils.js";

// Point document -> pixel entier dans le document, ou null.
export function pixelDans(doc, x, y) {
  if (!doc || !(x >= 0) || !(y >= 0)) return null;
  const px = Math.floor(x), py = Math.floor(y);
  return px < doc.width && py < doc.height ? { x: px, y: py } : null;
}

// Réponse de document.pixel ([r, g, b, a] flottants, relevé sur le vrai moteur) -> commande ; null si illisible.
export function commandeCouleur(rgba, alt) {
  if (!Array.isArray(rgba) || rgba.length < 3) return null;
  return { command: "tools.setColors", params: { [alt ? "background" : "foreground"]: rgbaVersHex(rgba) } };
}

export function initPipette(PL) {
  PL.gestes.eyedropper = {
    async appui(p, ev) {
      const px = pixelDans(PL.etat.doc, p.x, p.y);
      if (!px) return;
      const r = await PL.executer("document.pixel", px, { cycle: false });
      if (!r.ok) return;
      const c = commandeCouleur(r.r, ev.altKey);
      if (!c) return;
      try { await PL.post("/executer", { command: c.command, params: c.params }); } catch (e) { return; }      // signalé par mod-api
      if (PL.relireCouleurs) PL.relireCouleurs();
    },
    bouger() {}, relacher() {},
  };
}
