// mod-noeudapercu.js — R12 : pendant un geste de l'outil Nœud, le chemin ET
// l'overlay (ancres, poignées, boîte) suivent le curseur à chaque
// pointermove, au rythme d'UN cadre d'animation ; le relâchement VIDE le
// cadre en attente puis pose exactement ce qui est affiché. Pur en tête
// (planificateur bancable), DOM en bas. Aucun clone de document : les
// gestes travaillent sur les segs parsés une fois au pointerdown.

// au plus UNE demande en vol ; la dernière demande gagne ; vider() exécute
// la demande en attente tout de suite (le pointerup pose ce qui est affiché)
export function planificateur({ raf, caf }) {
  let fn = null, id = null;
  const tirer = () => { id = null; const f = fn; fn = null; if (f) f(); };
  return {
    demander(f) { fn = f; if (id === null) id = raf(tirer); },
    vider() {
      const f = fn; fn = null;
      if (id !== null) { caf(id); id = null; }
      if (!f) return false;
      f();
      return true;
    },
    enAttente: () => fn !== null,
  };
}

export function initNoeudApercu(VL) {
  const { etat } = VL;
  const P = planificateur({ raf: (f) => requestAnimationFrame(f), caf: (i) => cancelAnimationFrame(i) });
  let courant = null;    // { id, el, d }
  const pathEl = (id) => {
    const el = document.querySelector(`#canvasHost [data-objet="${id}"]`);
    if (!el) return null;
    return el.tagName === "path" ? el : el.querySelector("path");
  };
  VL.apercuNoeuds = {
    debut(id, segs) { courant = { id, el: pathEl(id), d: null }; etat.noeudsApercu = segs || null; },
    poser(segs, d) {
      if (!courant) return;
      courant.d = d;
      P.demander(() => {
        if (courant && courant.el) courant.el.setAttribute("d", d);
        etat.noeudsApercu = segs;
        VL.rendreOverlay();
      });
    },
    fin() {
      P.vider();
      const c = courant; courant = null; etat.noeudsApercu = null;
      return c ? { d: c.d } : null;
    },
    enCours: () => !!courant,
  };
}
