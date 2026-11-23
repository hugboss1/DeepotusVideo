/* Détecteur de débordement (écran calé sur la fenêtre, 23/11/2026).
   Partagé par le banc backend/tests/test_ecran_cale.py et les relevés à la main
   (coller le fichier dans la console : il rend un objet).

   Rend la liste des éléments INTERACTIFS visibles qu'on ne peut ni lire ni
   atteindre : leur boîte sort de la fenêtre ou d'un ancêtre qui les coupe
   (overflow hidden/clip), sans ancêtre défilable pour les ramener à l'écran.
   Une iframe doit tenir ENTIÈRE dans sa zone visible : son contenu croit
   disposer de toute sa hauteur (les barres du bas d'un lab y sont posées).
   Un tiroir fermé (ancêtre position:fixed entièrement hors fenêtre) est ignoré, comme
   un nœud posé sur un canevas qu'on fait glisser et zoomer (transform translate + scale). */
(function () {
  const W = innerWidth, H = innerHeight, TOL = 2;
  const SEL = 'button,a[href],input:not([type=hidden]),select,textarea,iframe,'
    + '[role=button],[role=tab],[role=menuitem],[tabindex]:not([tabindex="-1"])';
  const cs = (el) => getComputedStyle(el);
  const coupe = (v) => v === 'hidden' || v === 'clip';
  const roule = (v) => v === 'auto' || v === 'scroll' || v === 'overlay';
  const root = document.scrollingElement || document.documentElement;
  const sb = cs(document.body), sh = cs(document.documentElement);
  const docRoule = {
    y: root.scrollHeight > H + 1 && !coupe(sb.overflowY) && !coupe(sh.overflowY),
    x: root.scrollWidth > W + 1 && !coupe(sb.overflowX) && !coupe(sh.overflowX),
  };
  // part visible exigée : 80 % d'un petit élément, 60 px d'un grand, tout d'une iframe
  const assez = (vu, taille, iframe) => iframe ? vu >= taille - TOL
    : vu >= Math.min(taille * 0.8, Math.max(60, taille * 0.25)) - TOL;
  const vu = (a0, a1, c0, c1) => Math.max(0, Math.min(a1, c1) - Math.max(a0, c0));

  function horsCanevas(el) {           // tiroir / panneau fixe rangé hors de la fenêtre
    for (let p = el; p && p !== document.documentElement; p = p.parentElement) {
      if (cs(p).position === 'fixed') {
        const r = p.getBoundingClientRect();
        return r.right <= 0 || r.left >= W || r.bottom <= 0 || r.top >= H;
      }
    }
    return false;
  }

  function surCanevas(el) {            // canevas qu'on fait glisser et zoomer (graphe du Studio) : hors champ = voulu
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const st = p.getAttribute('style') || '';
      if (/transform:[^;]*scale\(/.test(st) && /translate/.test(st)) return true;
    }
    return false;
  }

  function verdict(el) {
    const ifr = el.tagName === 'IFRAME';
    let r = el.getBoundingClientRect();
    let cause = null;
    for (let p = el.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const s = cs(p), pr = p.getBoundingClientRect();
      const ry = roule(s.overflowY) && p.scrollHeight > p.clientHeight + 1;
      const rx = roule(s.overflowX) && p.scrollWidth > p.clientWidth + 1;
      const cy = coupe(s.overflowY) || roule(s.overflowY), cx = coupe(s.overflowX) || roule(s.overflowX);
      const okY = assez(vu(r.top, r.bottom, pr.top, pr.bottom), r.height, ifr);
      const okX = assez(vu(r.left, r.right, pr.left, pr.right), r.width, ifr);
      if (cy && !okY && !ry) { cause = 'coupé en hauteur par ' + nom(p); break; }
      if (cx && !okX && !rx) { cause = 'coupé en largeur par ' + nom(p); break; }
      if ((ry && !okY) || (rx && !okX)) {
        // on peut le faire venir en défilant p : reste à atteindre p lui-même (son coin haut-gauche)
        r = { top: pr.top, left: pr.left, bottom: Math.min(pr.bottom, pr.top + 40), right: Math.min(pr.right, pr.left + 40),
              height: Math.min(pr.height, 40), width: Math.min(pr.width, 40) };
      }
      if (s.position === 'fixed') break;
    }
    if (!cause) {
      const okY = assez(vu(r.top, r.bottom, 0, H), r.height, ifr) || docRoule.y;
      const okX = assez(vu(r.left, r.right, 0, W), r.width, ifr) || docRoule.x;
      if (!okY) cause = 'hors de la fenêtre en hauteur';
      else if (!okX) cause = 'hors de la fenêtre en largeur';
    }
    return cause;
  }

  function nom(el) {
    const t = (el.getAttribute('aria-label') || el.title || (el.tagName === 'IFRAME' ? el.getAttribute('src') : el.innerText)
      || el.value || el.placeholder || '').trim().replace(/\s+/g, ' ');
    let id = el.tagName.toLowerCase();
    if (el.id) id += '#' + el.id;
    else if (el.classList.length) id += '.' + [...el.classList].slice(0, 2).join('.');
    return id + (t ? ' « ' + t.slice(0, 40) + ' »' : '');
  }

  const out = [];
  for (const el of document.querySelectorAll(SEL)) {
    const s = cs(el);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;
    if (el.closest('[hidden],[aria-hidden=true],[inert],dialog:not([open])')) continue;
    const ferme = el.closest('details:not([open])');           // groupe replié : son contenu n'est pas affiché
    if (ferme && !el.closest('summary')) continue;
    let op = el, transp = false;
    for (; op && op !== document.documentElement; op = op.parentElement) if (+cs(op).opacity === 0) { transp = true; break; }
    if (transp || horsCanevas(el) || surCanevas(el)) continue;
    const cause = verdict(el);
    if (cause) out.push({ el: nom(el), cause, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) });
  }
  return { W, H, page: { sw: root.scrollWidth, sh: root.scrollHeight, defile: docRoule }, hors: out };
})();
