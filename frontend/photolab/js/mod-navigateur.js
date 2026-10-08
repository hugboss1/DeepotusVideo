// mod-navigateur.js — le panneau Navigateur (C2) : le dernier rendu réduit et le rectangle de la vue ; clic ou
// glisser = recentrer la vue sur ce point (le zoom ne change pas). Fonctions PURES exportées (qa/panneaux.test.mjs).

// Vignette du document {w,h} centrée dans la boîte {w,h} : {echelle, x, y, w, h}.
export function cadreNavigateur(doc, boite) {
  if (!doc || !(doc.w > 0) || !(doc.h > 0) || !(boite.w > 0) || !(boite.h > 0)) return { echelle: 0, x: 0, y: 0, w: 0, h: 0 };
  const echelle = Math.min(boite.w / doc.w, boite.h / doc.h);
  const w = doc.w * echelle, h = doc.h * echelle;
  return { echelle, x: (boite.w - w) / 2, y: (boite.h - h) / 2, w, h };
}

// Partie du document visible dans la vue {w,h} (vue v = {z, ox, oy}) -> rectangle dans le repère du navigateur.
export function rectVue(v, vue, cadre) {
  const x0 = -v.ox / v.z, y0 = -v.oy / v.z;
  return { x: cadre.x + x0 * cadre.echelle, y: cadre.y + y0 * cadre.echelle, w: (vue.w / v.z) * cadre.echelle, h: (vue.h / v.z) * cadre.echelle };
}

// Point (px, py) du navigateur -> nouvelle vue, même zoom, qui met ce point du document au centre de la vue.
export function centrerVue(px, py, cadre, v, vue) {
  const dx = (px - cadre.x) / cadre.echelle, dy = (py - cadre.y) / cadre.echelle;
  return { z: v.z, ox: vue.w / 2 - dx * v.z, oy: vue.h / 2 - dy * v.z };
}

export function initNavigateur(PL) {
  const corps = PL.$("#corpsNavigateur");
  corps.textContent = "";
  const c = document.createElement("canvas"); c.className = "na-toile";
  c.setAttribute("aria-label", window.dzT ? window.dzT("photolab.panneau.navigateur") : "photolab.panneau.navigateur");
  corps.appendChild(c);
  const ctx = c.getContext("2d");
  let cadre = null;

  const jeton = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function dessiner() {
    if (corps.hidden) return;                          // onglet masqué : rien à mesurer
    const k = window.devicePixelRatio || 1;
    const w = Math.max(1, corps.clientWidth - 16), h = Math.max(1, Math.min(220, corps.clientHeight - 16));
    if (c.width !== Math.round(w * k) || c.height !== Math.round(h * k)) { c.width = Math.round(w * k); c.height = Math.round(h * k); c.style.width = w + "px"; c.style.height = h + "px"; }
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const doc = PL.etat.doc;
    if (!doc) { cadre = null; return; }
    cadre = cadreNavigateur({ w: doc.width, h: doc.height }, { w, h });
    const im = PL.vue.rendu && PL.vue.rendu.image;
    ctx.fillStyle = jeton("--bg-panel-2");
    ctx.fillRect(cadre.x, cadre.y, cadre.w, cadre.h);
    if (im) { ctx.imageSmoothingEnabled = true; ctx.drawImage(im, cadre.x, cadre.y, cadre.w, cadre.h); }
    const toile = PL.$("#toile");
    const r = rectVue(PL.vue.v, { w: toile.clientWidth, h: toile.clientHeight }, cadre);
    ctx.strokeStyle = jeton("--accent");
    ctx.lineWidth = 1.5;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
  }

  function aller(ev) {
    if (!cadre || !PL.etat.doc) return;
    const b = c.getBoundingClientRect();
    const toile = PL.$("#toile");
    PL.vue.allerA(centrerVue(ev.clientX - b.left, ev.clientY - b.top, cadre, PL.vue.v, { w: toile.clientWidth, h: toile.clientHeight }));
  }
  let tient = false;
  c.addEventListener("pointerdown", (ev) => { if (ev.button !== 0) return; tient = true; c.setPointerCapture(ev.pointerId); aller(ev); });
  c.addEventListener("pointermove", (ev) => { if (tient) aller(ev); });
  const lacher = () => { tient = false; };
  c.addEventListener("pointerup", lacher); c.addEventListener("pointercancel", lacher); c.addEventListener("lostpointercapture", lacher);

  PL.surVue.push(dessiner);
  PL.surRendu.push(dessiner);
  PL.surDoc.push(dessiner);
  PL.dessinerNavigateur = dessiner;
  new ResizeObserver(dessiner).observe(corps);
}
