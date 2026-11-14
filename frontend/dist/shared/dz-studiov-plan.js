// dz-studiov-plan.js — SVA (15/11/2026, studio virtuel 3D), la VUE EN PLAN de l'atelier du décor : la pièce vue d'en
// haut, comme un plan d'architecte — murs, meubles (leur emprise réelle, mesurée par le moteur), objets muraux,
// lumières, caméras et leur champ, présentateur, écrans. On y CHOISIT d'un clic et on y PLACE à la souris : glisser
// déplace, la poignée ronde tourne un meuble, la poignée carrée oriente une caméra ou une lumière.
// Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md (§ 8).
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared. Banc : backend/tests/test_studiov_ecran.py.
// La géométrie (échelle, emprises, cône d'une caméra, collage au mur, ce qu'on touche) est dans dz-studiov-logique.js,
// jouée sous node ; ce module ne fait que dessiner et écouter la souris.
//
//   const p = creerPlan({doc, T, decor, empreintes, palette, selection, choisir, modifier, livre});
//   p.canvas ; p.peindre() ; p.detruire()
// `decor()` rend la recette en cours ; `modifier(recette, leger)` la remplace (leger = geste en cours) ; `choisir(cible)`
// dit ce qui est choisi ; `livre()` = vrai pour un décor livré (on regarde, on ne déplace rien).
import { MURAUX, cadrePlan, echellePlan, coinsObjet, tourner, coneCamera, collerAuMur, toucherPlan, aimanter, couleur, borne } from "./dz-studiov-logique.js";

const PAS = 0.05, PAS_ANGLE = 15, PRISE = 11;                // aimant (m), aimant (degrés), rayon d'une poignée (px)
const C = { fond: "#0f1318", sol: "#1a212a", grille: "#232d38", metre: "#2c3947", mur: "#d5dbe2", ouvert: "#4a5562", objet: "rgba(154,164,174,.16)",
  bord: "#9aa4ae", mural: "rgba(0,229,255,.2)", choisi: "#f0b429", texte: "#c9d1d9", camera: "#00e5ff", ecran: "#e6e9ee", presentateur: "#8a94a0" };

export function creerPlan(o) {
  const doc = o.doc || document, T = o.T || ((k) => k);
  const canvas = doc.createElement("canvas");
  canvas.setAttribute("data-dz-studiov-plan", ""); canvas.setAttribute("tabindex", "0"); canvas.setAttribute("role", "application");
  canvas.setAttribute("aria-label", T("studiov.plan.titre"));
  canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;outline:none;touch-action:none;cursor:default";
  const x = canvas.getContext("2d");
  let E = null, prise = null, cadreFige = null, taille = [0, 0];
  const copie = (v) => JSON.parse(JSON.stringify(v));

  // l'élément de la recette que désigne une cible, et sa place sur le plan
  const element = (d, c) => (!c ? null : c.genre === "objet" ? d.objets[c.index] : c.genre === "lumiere" ? d.lumieres[c.index] : c.genre === "camera" ? d.cameras[c.index]
    : c.genre === "ecran" ? d.ecrans[c.index] : c.genre === "enseigne" ? d.enseigne : c.genre === "presentateur" ? d.presentateur : null);
  const meme = (a, b) => !!a && !!b && a.genre === b.genre && (a.index || 0) === (b.index || 0) && a.pan === b.pan;
  // les poignées de ce qui est choisi : « tourner » (meuble) ou « viser » (caméra, lumière), en mètres
  function poignee(d, c, emps) {
    const el = element(d, c); if (!el) return null;
    if (c.genre === "objet") { const e = (emps && emps[c.index]) || { z1: 0.2, x0: -0.2, x1: 0.2 }, [rx, rz] = tourner((e.x0 + e.x1) / 2, Math.max(e.z1, 0.07) + 0.3, el.ry); return { mode: "tourner", x: el.x + rx, z: el.z + rz }; }
    if (c.genre === "camera" || (c.genre === "lumiere" && el.type !== "neon")) return { mode: "viser", x: el.vers[0], z: el.vers[2] };
    if (c.genre === "lumiere" || c.genre === "ecran" || c.genre === "enseigne") { const [rx, rz] = tourner(0, 0.45, el.ry); return { mode: "tourner", x: el.x + rx, z: el.z + rz }; }
    return null;
  }

  function peindre() {
    const d = o.decor(); if (!d) return;
    const r = canvas.getBoundingClientRect(), L = Math.max(60, r.width), H = Math.max(60, r.height), dpr = Math.min(2, (doc.defaultView || window).devicePixelRatio || 1);
    if (canvas.width !== Math.round(L * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(L * dpr); canvas.height = Math.round(H * dpr); }
    taille = [L, H];
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    E = echellePlan(cadreFige || cadrePlan(d), L, H - 22);
    const P = d.piece, pal = o.palette(), sel = o.selection(), emps = o.empreintes() || [], V = E.vers, k = E.k;
    const trace = (pts, ferme) => { x.beginPath(); pts.forEach(([a, b], i) => { const [px, py] = V(a, b); if (i) x.lineTo(px, py); else x.moveTo(px, py); }); if (ferme) x.closePath(); };
    const etiquette = (txt, a, b, c) => { const [px, py] = V(a, b); x.font = "10px system-ui, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillStyle = c || C.texte; x.fillText(txt, px, py); };
    x.fillStyle = C.fond; x.fillRect(0, 0, L, H);
    // le sol de la pièce et sa grille (un trait tous les 50 cm, plus marqué au mètre)
    const x0 = -P.l / 2, x1 = P.l / 2, z0 = -P.p / 2, z1 = P.p / 2;
    trace([[x0, z0], [x1, z0], [x1, z1], [x0, z1]], true); x.fillStyle = C.sol; x.fill();
    x.lineWidth = 1;
    for (let g = Math.ceil(x0 * 2) / 2; g <= x1 + 1e-6; g += 0.5) { x.strokeStyle = Math.abs(g % 1) < 1e-6 ? C.metre : C.grille; trace([[g, z0], [g, z1]]); x.stroke(); }
    for (let g = Math.ceil(z0 * 2) / 2; g <= z1 + 1e-6; g += 0.5) { x.strokeStyle = Math.abs(g % 1) < 1e-6 ? C.metre : C.grille; trace([[x0, g], [x1, g]]); x.stroke(); }
    // les murs : le fond toujours, les côtés sauf pièce ouverte ; le devant reste ouvert (la caméra y est)
    const mur = (pan, pts) => { x.strokeStyle = sel && sel.genre === "surface" && sel.pan === pan ? C.choisi : C.mur; x.lineWidth = 5; x.lineCap = "square"; trace(pts); x.stroke(); };
    mur("fond", [[x0, z0], [x1, z0]]);
    if (!P.ouvert) { mur("gauche", [[x0, z0], [x0, z1]]); mur("droite", [[x1, z0], [x1, z1]]); }
    x.setLineDash([5, 5]); x.strokeStyle = C.ouvert; x.lineWidth = 1; trace([[x0, z1], [x1, z1]]); x.stroke(); x.setLineDash([]);
    etiquette(`${P.l.toFixed(1).replace(".", ",")} m × ${P.p.toFixed(1).replace(".", ",")} m`, 0, z1 + 14 / k, C.ouvert);
    // les écrans du décor et l'enseigne : des traits épais contre leur mur
    const barre = (el, l, coul, cible) => { const [ax, az] = tourner(-l / 2, 0, el.ry), [bx2, bz] = tourner(l / 2, 0, el.ry); x.strokeStyle = meme(sel, cible) ? C.choisi : coul; x.lineWidth = 4; trace([[el.x + ax, el.z + az], [el.x + bx2, el.z + bz]]); x.stroke(); };
    d.ecrans.forEach((e, i) => barre(e, e.l, C.ecran, { genre: "ecran", index: i }));
    if (d.enseigne.actif) barre(d.enseigne, d.enseigne.l, couleur(d.enseigne.couleur, pal), { genre: "enseigne", index: 0 });
    // les objets : au sol d'abord, puis ce qui s'accroche (mur, plafond)
    const dessiner = (ob, i) => {
      const coins = coinsObjet(ob, emps[i]), mural = MURAUX.indexOf(ob.type) >= 0, haut = ob.type === "suspension" || ob.type === "projecteur", choisi = meme(sel, { genre: "objet", index: i });
      trace(coins, true);
      x.fillStyle = choisi ? "rgba(240,180,41,.3)" : mural ? C.mural : ob.couleur ? couleur(ob.couleur, pal) + "44" : C.objet; x.fill();
      if (haut) x.setLineDash([3, 3]);
      x.strokeStyle = choisi ? C.choisi : mural ? C.camera : C.bord; x.lineWidth = choisi ? 2 : 1; x.stroke(); x.setLineDash([]);
      // un trait à l'avant de l'objet : on voit dans quel sens il regarde
      if (!mural) { x.beginPath(); const [a1, b1] = V(coins[3][0], coins[3][1]), [a2, b2] = V(coins[2][0], coins[2][1]); x.moveTo(a1, b1); x.lineTo(a2, b2); x.lineWidth = choisi ? 3 : 2; x.stroke(); }
      const large = Math.hypot(coins[1][0] - coins[0][0], coins[1][1] - coins[0][1]) * k;
      if (choisi || large > 58) etiquette(T("studiov.objet." + ob.type), (coins[0][0] + coins[2][0]) / 2, (coins[0][1] + coins[2][1]) / 2);
    };
    d.objets.forEach((ob, i) => { if (MURAUX.indexOf(ob.type) < 0) dessiner(ob, i); });
    d.objets.forEach((ob, i) => { if (MURAUX.indexOf(ob.type) >= 0) dessiner(ob, i); });
    // le présentateur
    { const R = d.presentateur, [px, py] = V(R.x, R.z), ch = meme(sel, { genre: "presentateur", index: 0 });
      x.beginPath(); x.arc(px, py, Math.max(9, 0.22 * k), 0, Math.PI * 2); x.fillStyle = ch ? "rgba(240,180,41,.35)" : "rgba(138,148,160,.35)"; x.fill(); x.strokeStyle = ch ? C.choisi : C.presentateur; x.lineWidth = ch ? 2 : 1.5; x.stroke();
      x.beginPath(); x.moveTo(px, py); x.lineTo(px, py + Math.max(9, 0.22 * k) + 7); x.stroke(); etiquette(T("studiov.plan.presentateur"), R.x, R.z - 0.22 - 9 / k); }
    // les lumières : un rond à leur couleur, un trait vers ce qu'elles éclairent ; un néon : son tube
    d.lumieres.forEach((l, i) => {
      if (l.type === "ambiance") return;
      const hex = couleur(l.couleur, pal, "#ffffff"), ch = meme(sel, { genre: "lumiere", index: i }), [px, py] = V(l.x, l.z);
      if (l.type === "neon") { const [ax, az] = tourner(0, -l.l / 2, l.ry), [bx2, bz] = tourner(0, l.l / 2, l.ry); x.strokeStyle = hex; x.lineWidth = ch ? 5 : 3; x.lineCap = "round"; trace([[l.x + ax, l.z + az], [l.x + bx2, l.z + bz]]); x.stroke(); x.lineCap = "butt"; if (!ch) return; }
      else { x.strokeStyle = hex; x.globalAlpha = 0.45; x.lineWidth = 1; x.setLineDash([4, 4]); trace([[l.x, l.z], [l.vers[0], l.vers[2]]]); x.stroke(); x.setLineDash([]); x.globalAlpha = 1; }
      x.beginPath(); x.arc(px, py, ch ? 9 : 7, 0, Math.PI * 2); x.fillStyle = hex; x.fill(); x.strokeStyle = ch ? C.choisi : "#0b0d10"; x.lineWidth = ch ? 2.5 : 1.5; x.stroke();
    });
    // les caméras : leur champ (image 16:9) et leur numéro
    d.cameras.forEach((cm, i) => {
      const cone = coneCamera(cm), ch = meme(sel, { genre: "camera", index: i }), [px, py] = V(cm.x, cm.z);
      trace(cone, true); x.fillStyle = ch ? "rgba(240,180,41,.12)" : "rgba(0,229,255,.07)"; x.fill(); x.strokeStyle = ch ? C.choisi : C.camera; x.globalAlpha = ch ? 1 : 0.5; x.lineWidth = 1; x.stroke(); x.globalAlpha = 1;
      x.fillStyle = ch ? C.choisi : C.camera; x.fillRect(px - 9, py - 7, 18, 14); x.fillStyle = "#0b0d10"; x.font = "700 10px system-ui, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText(String(i + 1), px, py + 0.5);
    });
    // les poignées de ce qui est choisi
    const pg = o.livre() ? null : poignee(d, sel, emps), el = element(d, sel);
    if (pg && el) {
      const [hx, hy] = V(pg.x, pg.z), [cx2, cy2] = V(el.x, el.z);
      x.strokeStyle = C.choisi; x.lineWidth = 1; x.setLineDash([2, 3]); x.beginPath(); x.moveTo(cx2, cy2); x.lineTo(hx, hy); x.stroke(); x.setLineDash([]);
      x.fillStyle = C.choisi; x.beginPath(); if (pg.mode === "tourner") x.arc(hx, hy, 6, 0, Math.PI * 2); else x.rect(hx - 6, hy - 6, 12, 12); x.fill(); x.strokeStyle = "#0b0d10"; x.lineWidth = 1.5; x.stroke();
    }
    x.font = "10.5px system-ui, sans-serif"; x.textAlign = "left"; x.textBaseline = "middle"; x.fillStyle = C.ouvert;
    x.fillText(o.livre() ? T("studiov.plan.aide.livre") : T("studiov.plan.aide"), 8, H - 11);
  }

  // ── la souris ──
  const lieu = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  function appliquer(mx, mz, libre) {
    const d = copie(o.decor()), c = prise.cible, el = element(d, c), P = d.piece; if (!el) return;
    const pas = libre ? 0 : PAS;
    if (prise.mode === "deplacer") {
      const large = c.genre === "camera" || c.genre === "lumiere";
      el.x = borne(aimanter(mx - prise.dx, pas), large ? -P.l / 2 - 3 : -P.l / 2, large ? P.l / 2 + 3 : P.l / 2);
      el.z = borne(aimanter(mz - prise.dz, pas), large ? -P.p / 2 - 1 : -P.p / 2, large ? P.p / 2 + 6 : P.p / 2 + 2);
      if (c.genre === "objet" && MURAUX.indexOf(el.type) >= 0 && el.type !== "panneau_acoustique") Object.assign(el, collerAuMur(el, P));
    } else if (prise.mode === "tourner") {
      const a = (Math.atan2(mx - el.x, mz - el.z) * 180) / Math.PI;
      el.ry = Math.round(aimanter(a, libre ? 1 : PAS_ANGLE));
      if (el.ry > 180) el.ry -= 360;
    } else { el.vers[0] = borne(aimanter(mx, pas), -12, 12); el.vers[2] = borne(aimanter(mz, pas), -12, 12); }
    prise.bouge = true;
    o.modifier(d, true);
    peindre();
  }
  function bas(e) {
    const d = o.decor(); if (!d || !E || e.button !== 0) return;
    canvas.focus();
    const [px, py] = lieu(e), [mx, mz] = E.depuis(px, py), emps = o.empreintes() || [], sel = o.selection();
    const pg = o.livre() ? null : poignee(d, sel, emps);
    if (pg) { const [hx, hy] = E.vers(pg.x, pg.z); if (Math.hypot(hx - px, hy - py) <= PRISE) prise = { mode: pg.mode, cible: sel }; }
    if (!prise) {
      const c = toucherPlan(d, emps, mx, mz, PRISE / E.k);
      o.choisir(c);
      const el = element(d, c);
      if (c && el && !o.livre()) prise = { mode: "deplacer", cible: c, dx: mx - el.x, dz: mz - el.z };
    }
    if (prise) { cadreFige = cadrePlan(d); try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* pointeur déjà relâché */ } }
    peindre();
  }
  function bouge(e) {
    if (!E) return;
    const [px, py] = lieu(e), [mx, mz] = E.depuis(px, py);
    if (prise) { appliquer(mx, mz, e.altKey); return; }
    const d = o.decor(); if (!d) return;
    canvas.style.cursor = toucherPlan(d, o.empreintes() || [], mx, mz, PRISE / E.k) ? (o.livre() ? "pointer" : "move") : "default";
  }
  function haut(e) {
    if (!prise) return;
    const bouge2 = prise.bouge; prise = null; cadreFige = null;
    try { canvas.releasePointerCapture(e.pointerId); } catch (err) { /* déjà relâché */ }
    if (bouge2) o.modifier(o.decor(), false);              // le geste est fini : le panneau se remet à jour
    peindre();
  }
  function molette(e) {
    const d = o.decor(), sel = o.selection();
    if (!d || o.livre() || !sel || sel.genre !== "objet" || !d.objets[sel.index]) return;
    e.preventDefault();
    const nd = copie(d), ob = nd.objets[sel.index];
    ob.ry = ((Math.round(ob.ry / PAS_ANGLE) * PAS_ANGLE + (e.deltaY > 0 ? PAS_ANGLE : -PAS_ANGLE) + 540) % 360) - 180;
    o.modifier(nd, false);
  }
  function touche(e) {
    const d = o.decor(), sel = o.selection();
    if (!d || o.livre() || !sel) return;
    const nd = copie(d), el = element(nd, sel); if (!el) return;
    const pas = e.shiftKey ? 0.25 : PAS, fleches = { ArrowLeft: [-pas, 0], ArrowRight: [pas, 0], ArrowUp: [0, -pas], ArrowDown: [0, pas] };
    if (fleches[e.key]) { el.x = Math.round((el.x + fleches[e.key][0]) * 100) / 100; el.z = Math.round((el.z + fleches[e.key][1]) * 100) / 100; }
    else if ((e.key === "Delete" || e.key === "Backspace") && sel.genre === "objet") { nd.objets.splice(sel.index, 1); o.choisir(null); }
    else if ((e.key === "r" || e.key === "R") && "ry" in el) el.ry = ((el.ry + 90 + 540) % 360) - 180;
    else return;
    e.preventDefault(); e.stopPropagation();
    o.modifier(nd, false);
  }
  canvas.addEventListener("pointerdown", bas); canvas.addEventListener("pointermove", bouge);
  canvas.addEventListener("pointerup", haut); canvas.addEventListener("pointercancel", haut);
  canvas.addEventListener("wheel", molette, { passive: false }); canvas.addEventListener("keydown", touche);

  return { canvas, peindre, taille: () => taille,
    detruire() { canvas.removeEventListener("pointerdown", bas); canvas.removeEventListener("pointermove", bouge); canvas.removeEventListener("pointerup", haut);
      canvas.removeEventListener("pointercancel", haut); canvas.removeEventListener("wheel", molette); canvas.removeEventListener("keydown", touche); canvas.remove(); } };
}
