// mod-deplacer.js — l'outil Déplacement (C3) : glisser = aperçu par translation CSS du canevas pendant le geste,
// UNE commande au relâchement (contenu de la sélection par edit.transform, sinon le calque par layer.translate) ;
// Maj = axe dominant ; Échap abandonne ; flèches 1 px, Maj+flèches 10 px (cumulées pendant qu'un envoi vole) ;
// « Sélection auto. » ou Ctrl+clic = layer.pickAt. t253 : Alt-glisser une sélection en déplace une COPIE (select.float
// copy puis select.drop : un seul état « Déplacement ») ; le glisser suit la vue tournée.
// Fonctions PURES exportées (qa/gestes.test.mjs, qa/selection-m4.test.mjs).
import { creerAccumulateur } from "./mod-cycle.js";
import { tournerVecteur } from "./mod-vue.js";

// Déplacement entier -> commande ; null si rien ne bouge. Sans calque actif connu, `layer` est omis (le moteur prend
// le calque actif).
export function deplacementCommande(aSelection, dx, dy, calque) {
  const x = Math.round(dx), y = Math.round(dy);
  if (!x && !y) return null;
  if (aSelection) return { command: "edit.transform", params: { matrix: [1, 0, 0, 1, x, y] } };
  const params = calque != null ? { layer: calque, dx: x, dy: y } : { dx: x, dy: y };
  return { command: "layer.translate", params };
}

// Maj : on ne garde que l'axe dominant.
export function contrainteAxe(dx, dy) {
  return Math.abs(dx) >= Math.abs(dy) ? { dx, dy: 0 } : { dx: 0, dy };
}

const FLECHES = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
export function pasFleche(touche, maj) {
  const f = FLECHES[touche];
  if (!f) return null;
  const k = maj ? 10 : 1;
  return { dx: f[0] * k, dy: f[1] * k };
}

// Delta du glisser en pixels document, mesuré en coordonnées CLIENT depuis l'appui. Surtout pas depuis le rectangle
// de #toile : l'aperçu le translate, la mesure suivrait l'aperçu et le geste dériverait.
// t152 : vue en miroir -> le glisser horizontal à l'écran est l'inverse du déplacement dans le document.
// t253 : vue tournée de `angle` degrés -> le glisser écran est ramené dans le repère du document.
export function deltaGlisser(appui, ev, z, miroir = false, angle = 0) {
  const t = tournerVecteur(ev.clientX - appui.clientX, ev.clientY - appui.clientY, -angle);
  const dx = t.dx / z;
  return { dx: miroir ? -dx : dx, dy: t.dy / z };
}

export function cumulerPas(a, b) { return { dx: a.dx + b.dx, dy: a.dy + b.dy }; }

// t253 : la ou les commandes d'un déplacement. Alt + sélection : flotter une copie décalée puis la déposer (le moteur
// n'en fait qu'un état) ; sinon la commande d'avant. Rien ne bouge : aucune.
export function commandesDeplacement(aSelection, alt, dx, dy, calque) {
  const x = Math.round(dx), y = Math.round(dy);
  if (!x && !y) return [];
  if (alt && aSelection) return [{ command: "select.float", params: { dx: x, dy: y, copy: true } }, { command: "select.drop", params: {} }];
  return [deplacementCommande(aSelection, x, y, calque)];
}

/* ───────────── côté DOM ───────────── */

export function initDeplacer(PL) {
  const toile = PL.$("#toile");
  let g = null;
  const doc = () => PL.etat.doc;
  // t152 : en miroir, un déplacement document vers la droite se voit vers la gauche.
  const apercu = (dx, dy) => { const sx = PL.vue.v.miroir ? -dx : dx; toile.style.transform = dx || dy ? `translate(${sx * PL.vue.v.z}px, ${dy * PL.vue.v.z}px)` : ""; };

  // -> true si une commande est partie et a réussi (le rendu qui suit effacera l'aperçu, PL.surRendu).
  async function deplacer(dx, dy, alt = false) {
    const d = doc(); if (!d) return false;
    const cs = commandesDeplacement(d.hasSelection, alt, dx, dy, d.activeLayer);
    if (!cs.length) return false;
    for (let i = 0; i < cs.length; i++) {
      // le flottant n'est pas un état à lui seul : pas de cycle entre flotter et déposer
      const r = await PL.executer(cs[i].command, cs[i].params, i < cs.length - 1 ? { cycle: false } : undefined);
      if (!r.ok) return false;
    }
    return true;
  }
  // Flèches : une poussée part tout de suite ; celles qui arrivent pendant qu'elle vole sont cumulées en une seule.
  const pousser = creerAccumulateur((p) => deplacer(p.dx, p.dy), cumulerPas);

  PL.gestes.move = {
    appui(p, ev) {
      const geste = { appui: { clientX: ev.clientX, clientY: ev.clientY }, z: PL.vue.v.z, dx: 0, dy: 0, choix: null, annule: false, alt: ev.altKey };
      g = geste;
      const o = PL.etat.options;
      const x = Math.floor(p.x), y = Math.floor(p.y);
      const d = doc();
      if ((o.autoSelect || ev.ctrlKey || ev.metaKey) && d && x >= 0 && y >= 0 && x < d.width && y < d.height) {
        // Le calque sous le pointeur devient l'actif AVANT le déplacement : le relâchement attend ce choix. Rien sous le
        // pointeur (ou refus du moteur, déjà signalé) : le geste est abandonné, l'ancien calque actif ne bouge PAS.
        geste.choix = PL.executer("layer.pickAt", { x, y, target: o.autoCible === "group" ? "group" : "layer", select: true }, { cycle: false })
          .then((r) => {
            if (!(r.ok && r.r && r.r.layer != null)) { geste.annule = true; if (g === geste) apercu(0, 0); return; }
            if (PL.etat.doc) PL.etat.doc = { ...PL.etat.doc, activeLayer: r.r.layer };
            PL.cycle();
          });
      }
    },
    bouger(p, ev) {
      if (!g || g.annule) return;
      let { dx, dy } = deltaGlisser(g.appui, ev, g.z, !!PL.vue.v.miroir, PL.vue.v.r || 0);
      if (ev.shiftKey) ({ dx, dy } = contrainteAxe(dx, dy));
      // t152 : Affichage › Aimanter (Ctrl tenu pendant le glisser l'interrompt, comme dans la référence)
      if (PL.affichage && !ev.ctrlKey) ({ dx, dy } = PL.affichage.aimanterDeplacement(dx, dy));
      g.dx = dx; g.dy = dy;
      apercu(Math.round(dx), Math.round(dy));
    },
    async relacher() {
      if (!g) return;
      const geste = g; g = null;
      if (geste.choix) await geste.choix;
      // Pas de remise à zéro ici : le rendu qui suit la commande efface l'aperçu (sinon l'image sauterait en arrière
      // le temps du rendu). Seulement si rien n'est parti, ou si la commande a échoué.
      const parti = !geste.annule && await deplacer(geste.dx, geste.dy, geste.alt);
      if (!parti) apercu(0, 0);
    },
    annuler() { g = null; apercu(0, 0); },
    touche(ev) {
      if (ev.key === "Escape" && g) { g.annule = true; g.dx = 0; g.dy = 0; apercu(0, 0); return true; }
      const f = pasFleche(ev.key, ev.shiftKey);
      if (!f) return false;
      pousser(f);
      return true;
    },
    quitter() { g = null; apercu(0, 0); },
  };
  // Un nouveau rendu posé efface l'aperçu CSS (fin normale d'un déplacement, ou sécurité si le relâchement s'est perdu).
  PL.surRendu.push(() => { if (!g) apercu(0, 0); });
}
