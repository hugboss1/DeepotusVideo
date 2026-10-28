// dz-skins-calques.js — t316 (28/10/2026, lot D2 « skins de capture »), les CALQUES d'un skin posés sur la scène
// commune de la capture (dz-capture-scene.js, contrat t315). Plan docs/superpowers/plans/2026-10-28-t316-skins.md.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared (banc backend/tests/test_skins_ecran.py, faux
// canvas sous node).
//
//   const h = habiller(scene, skin, {contexte, T, images: {logo, fond}, camera, halo});
//   h.maj(skin)               un autre skin (éditeur : chaque réglage, chaque glisser) ; h.skin()
//   h.alerte({type: "abonne" | "message", nom, texte})          une alerte du live (t318)
//   h.ecran("pause" | "fin" | null)                            l'écran « on revient tout de suite » / « fin du direct »
//   h.outro() -> Promise      joue l'outro (résolue à sa fin ; tout de suite si l'outro est éteinte)
//   h.rejouer()               relance l'intro ; h.retirer()   rend la scène telle qu'elle était
// Calques : skin-fond 40, skin-cadre 150, clics 500 (remplacé : style du curseur, seulement s'il existait), encart 600
// (remplacé : forme, bord, ombre, seulement s'il existait), skin-logo 710, skin-bandeau 720, skin-signature 730,
// skin-alertes 760, skin-carte 790. Tous sous 900 : le CAVIARDAGE reste au-dessus de tout. Le skin ne redessine jamais la
// source « ecran » : il pose `etat.cadre`, que la scène applique à l'écran, aux clics et au caviardage.
import { Z, FONDU, borne, palette, couleur, rgba, polices, police, textes, remplir, disposer, carte, bandeau, alertes,
  ajuster } from "./dz-skins-logique.js";
import { calqueClics, calqueEncart, DUREE_HALO } from "./dz-capture-scene.js";

const IDS = ["skin-fond", "skin-cadre", "skin-logo", "skin-bandeau", "skin-signature", "skin-alertes", "skin-carte"];

function mesureur(ctx) {
  return (t) => {
    try { const m = ctx.measureText(t); if (m && Number.isFinite(m.width)) return m.width; } catch (e) { /* faux canvas */ }
    return String(t).length * 8;
  };
}
// une image prête à dessiner (HTMLImageElement chargée, canvas…) : sinon rien
const prete = (im) => !!im && (im.complete !== false) && ((im.naturalWidth || im.width || 0) > 0);
function contenir(ctx, im, x, y, l, h) {
  const w = im.naturalWidth || im.width, hh = im.naturalHeight || im.height, k = Math.min(l / w, h / hh);
  ctx.drawImage(im, x + (l - w * k) / 2, y + (h - hh * k) / 2, w * k, hh * k);
}
function couvrir(ctx, im, x, y, l, h) {
  const w = im.naturalWidth || im.width, hh = im.naturalHeight || im.height, k = Math.max(l / w, h / hh);
  ctx.drawImage(im, x + (l - w * k) / 2, y + (h - hh * k) / 2, w * k, hh * k);
}
function forme(ctx, f, x, y, l, h) {
  ctx.beginPath();
  if (f === "cercle") { const r = Math.min(l, h) / 2; ctx.arc(x + l / 2, y + h / 2, r, 0, Math.PI * 2); }
  else if (f === "carre" && typeof ctx.roundRect === "function") ctx.roundRect(x, y, l, h, Math.min(l, h) * 0.12);
  else ctx.rect(x, y, l, h);
}

export function habiller(scene, skin0, env) {
  const E = env || {}, T = typeof E.T === "function" ? E.T : (k) => k;
  let skin = skin0 || {}, pal, pol, txt;
  // apercu (éditeur) : l'intro est déjà passée au départ et le bandeau reste visible (pour le régler et le glisser)
  const st = { debut: null, outro: null, ecran: null, alertes: [], t: 0, decalage: E.apercu ? 1e7 : 0 };
  const avant = { cadre: scene.etat.cadre, styleZoom: scene.etat.styleZoom, forme: scene.etat.forme, encart: scene.etat.encart };
  const avaitClics = scene.calques().some((c) => c.id === "clics");
  const avaitEncart = scene.calques().some((c) => c.id === "encart");
  const images = E.images || {};

  function appliquer() {
    pal = palette(skin, E.contexte);
    pol = polices(skin, E.contexte);
    txt = textes(skin, E.contexte, T);
    scene.etat.cadre = { marge: Number(skin.cadre && skin.cadre.marge) || 0 };
    scene.etat.styleZoom = { k: Number(skin.zoom && skin.zoom.niveau) || 1.5, duree: Number(skin.zoom && skin.zoom.duree_ms) || 1800 };
    if (avaitEncart && skin.encart) {
      scene.etat.forme = skin.encart.forme || scene.etat.forme;
      const e = skin.encart;
      // la place vient du skin ; l'encart DOM la réécrit ensuite (glisser) en gardant bord/ombre/couleur
      scene.etat.encart = Object.assign({}, scene.etat.encart || {}, { x: e.x, y: e.y, l: e.l, h: e.h },
        { bord: e.bord, ombre: !!e.ombre, couleur: couleur(e.couleur, pal) });
    }
  }
  appliquer();
  const temps = (s) => { if (st.debut == null) st.debut = s.t - st.decalage; st.t = s.t - st.debut; return st.t; };
  const retirerCrochet = scene.surImage((s) => { temps(s); });

  // fond (sous l'écran) : visible seulement autour d'un écran réduit
  scene.ajouterCalque({ id: "skin-fond", z: Z.fond, dessiner(ctx, s) {
    const c = s.cadre;
    if (!c || c.x <= 0) return;
    const f = (skin.cadre && skin.cadre.fond) || {};
    if (f.type === "image" && prete(images.fond)) { couvrir(ctx, images.fond, 0, 0, s.largeur, s.hauteur); return; }
    if (f.type === "uni") { ctx.fillStyle = couleur(f.c1, pal); ctx.fillRect(0, 0, s.largeur, s.hauteur); return; }
    const g = ctx.createLinearGradient(0, 0, s.largeur, s.hauteur);
    if (g && typeof g.addColorStop === "function") { g.addColorStop(0, couleur(f.c1 || "fond", pal)); g.addColorStop(1, couleur(f.c2 || "principale", pal)); }
    ctx.fillStyle = g || couleur(f.c1, pal);
    ctx.fillRect(0, 0, s.largeur, s.hauteur);
  } });
  // bord de l'écran (au-dessus de l'écran, sous les clics)
  scene.ajouterCalque({ id: "skin-cadre", z: Z.cadre, dessiner(ctx, s) {
    const b = Number(skin.cadre && skin.cadre.bord) || 0;
    if (!(b > 0)) return;
    const c = s.cadre, e = Math.max(1, b * s.largeur);
    ctx.lineWidth = e;
    ctx.strokeStyle = couleur(skin.cadre.couleur, pal);
    if (c.x > 0) ctx.strokeRect(c.x - e / 2, c.y - e / 2, c.l + e, c.h + e);
    else ctx.strokeRect(e / 2, e / 2, s.largeur - e, s.hauteur - e);
  } });
  // le curseur (halo des clics) : remplace le calque « clics » de l'enregistreur, s'il l'avait posé
  if (avaitClics) {
    scene.ajouterCalque({ id: "clics", z: 500, dessiner(ctx, s) {
      const cu = skin.curseur || {};
      if (cu.style === "aucun") { s.etat.clics = s.etat.clics.filter((c) => s.t - c.debut <= DUREE_HALO); return; }
      if (cu.style !== "point") {
        const n = couleur(cu.couleur, pal), k = Number(cu.taille) || 1;
        const r = parseInt(n.slice(1, 3), 16), g = parseInt(n.slice(3, 5), 16), b = parseInt(n.slice(5, 7), 16);
        // la taille du halo suit la largeur de scène qu'on lui donne (même état : les clics expirés partent)
        calqueClics(`rgba(${r},${g},${b},`).dessiner(ctx, k === 1 ? s : Object.assign({}, s, { largeur: s.largeur * k }));
        return;
      }
      s.etat.clics = s.etat.clics.filter((c) => s.t - c.debut <= DUREE_HALO);
      ctx.setTransform(s.vue.k, 0, 0, s.vue.k, s.vue.ox, s.vue.oy);
      const r0 = Math.max(6, s.largeur / 160) * (Number(cu.taille) || 1);
      for (const c of s.etat.clics) {
        const p = borne((s.t - c.debut) / DUREE_HALO, 0, 1);
        ctx.beginPath();
        ctx.arc(c.x, c.y, r0 * (1 - 0.5 * p), 0, Math.PI * 2);
        ctx.fillStyle = rgba(couleur(cu.couleur, pal), 0.85 * (1 - p));
        ctx.fill();
      }
    } });
  }
  // l'encart caméra : forme, bord (épaisseur, couleur), ombre ; remplace celui de l'enregistreur, s'il l'avait posé
  if (avaitEncart) {
    scene.ajouterCalque({ id: "encart", z: 600, dessiner(ctx, s) {
      const v = s.sources.camera, e = s.etat.encart;
      if (!v || !e || !(v.readyState >= 2)) return;
      const x = e.x * s.largeur, y = e.y * s.hauteur, l = e.l * s.largeur, h = e.h * s.hauteur;
      if (e.ombre) {
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = Math.max(8, s.largeur / 70); ctx.shadowOffsetY = Math.max(3, s.largeur / 300);
        forme(ctx, s.etat.forme, x, y, l, h); ctx.fillStyle = "#000"; ctx.fill();
        ctx.restore();
      }
      forme(ctx, s.etat.forme, x, y, l, h);
      ctx.save();
      ctx.clip();
      const vw = v.videoWidth || v.width || l, vh = v.videoHeight || v.height || h, k = Math.max(l / vw, h / vh);
      ctx.drawImage(v, x + (l - vw * k) / 2, y + (h - vh * k) / 2, vw * k, vh * k);
      ctx.restore();
      const b = Number(e.bord);
      if (b > 0) { ctx.lineWidth = Math.max(1, b * s.largeur); ctx.strokeStyle = e.couleur || pal.principale; ctx.stroke(); }
    } });
  }
  // le logo de l'espace (ou l'image du skin)
  scene.ajouterCalque({ id: "skin-logo", z: Z.logo, dessiner(ctx, s) {
    if (!skin.logo || !skin.logo.actif || !prete(images.logo) || carte(skin, st.t, st)) return;
    const r = disposer(skin, s.largeur, s.hauteur).logo;
    ctx.globalAlpha = borne(Number(skin.logo.opacite) || 1, 0.2, 1);
    contenir(ctx, images.logo, r.x, r.y, r.l, r.h);
  } });
  // le bandeau titre (lower third)
  scene.ajouterCalque({ id: "skin-bandeau", z: Z.bandeau, dessiner(ctx, s) {
    const a = E.apercu && skin.bandeau && skin.bandeau.actif ? 1 : bandeau(skin, st.t);
    if (!(a > 0) || carte(skin, st.t, st)) return;
    const r = disposer(skin, s.largeur, s.hauteur).bandeau, b = skin.bandeau, mes = mesureur(ctx);
    const glisse = (1 - a) * -r.l * 0.15;
    ctx.globalAlpha = a;
    ctx.translate(glisse, 0);
    const pad = r.h * 0.16, ht = r.h * 0.38, hs = r.h * 0.24;
    if (b.style === "bloc") {
      ctx.fillStyle = rgba(pal.fond, 0.9); ctx.fillRect(r.x, r.y, r.l, r.h);
      ctx.fillStyle = pal.accent; ctx.fillRect(r.x, r.y, r.h * 0.08, r.h);
    } else if (b.style === "bande") {
      ctx.fillStyle = pal.principale; ctx.fillRect(r.x, r.y, r.l, r.h * 0.6);
      ctx.fillStyle = rgba(pal.fond, 0.92); ctx.fillRect(r.x, r.y + r.h * 0.6, r.l * 0.85, r.h * 0.4);
    } else {
      ctx.fillStyle = pal.accent; ctx.fillRect(r.x, r.y + r.h - Math.max(2, r.h * 0.05), r.l, Math.max(2, r.h * 0.05));
    }
    ctx.textBaseline = "middle"; ctx.textAlign = "left";
    const x0 = r.x + pad + (b.style === "bloc" ? r.h * 0.08 : 0), lmax = r.l - 2 * pad;
    ctx.fillStyle = pal.texte;
    ctx.font = police(pol.titre, ht, true);
    ctx.fillText(ajuster(txt.bandeau.titre, lmax, mes), x0, r.y + (b.style === "bande" ? r.h * 0.3 : r.h * 0.36));
    if (txt.bandeau.sous_titre) {
      ctx.font = police(pol.texte, hs, false);
      ctx.fillStyle = b.style === "bande" ? pal.texte : rgba(pal.texte, 0.8);
      ctx.fillText(ajuster(txt.bandeau.sous_titre, lmax, mes), x0, r.y + (b.style === "bande" ? r.h * 0.8 : r.h * 0.72));
    }
  } });
  // « Fait avec DeepotusVideo » (promotion organique, désactivable)
  scene.ajouterCalque({ id: "skin-signature", z: Z.signature, dessiner(ctx, s) {
    const g = skin.signature;
    if (!g || !g.actif || carte(skin, st.t, st)) return;
    const r = disposer(skin, s.largeur, s.hauteur).signature;
    ctx.globalAlpha = borne(Number(g.opacite) || 0.75, 0.3, 1);
    ctx.fillStyle = "rgba(0,0,0,.45)"; ctx.fillRect(r.x, r.y, r.l, r.h);
    ctx.fillStyle = "#ffffff"; ctx.font = police(pol.texte, r.h * 0.5, false);
    ctx.textBaseline = "middle"; ctx.textAlign = "center";
    ctx.fillText(ajuster(txt.signature, r.l * 0.94, mesureur(ctx)), r.x + r.l / 2, r.y + r.h / 2);
  } });
  // les alertes du live (nouvel abonné, message)
  scene.ajouterCalque({ id: "skin-alertes", z: Z.alertes, dessiner(ctx, s) {
    if (!skin.alertes || !skin.alertes.actif) return;
    const vivantes = alertes(st.alertes, st.t, skin.alertes.duree_s);
    st.alertes = st.alertes.filter((a) => st.t - a.debut <= (Number(skin.alertes.duree_s) || 5) * 1000);
    const r0 = disposer(skin, s.largeur, s.hauteur).alertes, mes = mesureur(ctx);
    for (const a of vivantes) {
      const y = r0.y + a.rang * r0.h * 1.12 - (1 - a.alpha) * r0.h * 0.4;
      ctx.globalAlpha = a.alpha;
      ctx.fillStyle = rgba(pal.fond, 0.94); ctx.fillRect(r0.x, y, r0.l, r0.h);
      ctx.lineWidth = Math.max(2, r0.h * 0.05); ctx.strokeStyle = pal.accent; ctx.strokeRect(r0.x, y, r0.l, r0.h);
      ctx.fillStyle = pal.principale; ctx.fillRect(r0.x, y, r0.h * 0.12, r0.h);
      const texte = a.type === "message" ? remplir(txt.message, a) : remplir(txt.abonne, a);
      ctx.fillStyle = pal.texte; ctx.font = police(pol.titre, r0.h * 0.36, true);
      ctx.textBaseline = "middle"; ctx.textAlign = "left";
      ctx.fillText(ajuster(texte, r0.l - r0.h * 0.5, mes), r0.x + r0.h * 0.3, y + r0.h / 2);
    }
  } });
  // les cartes plein cadre : intro, outro, « on revient tout de suite », « fin du direct »
  scene.ajouterCalque({ id: "skin-carte", z: Z.carte, dessiner(ctx, s) {
    const c = carte(skin, st.t, st);
    if (!c) return;
    const W = s.largeur, H = s.hauteur, t = txt[c.nom] || {}, mes = mesureur(ctx);
    ctx.globalAlpha = c.alpha;
    const g = ctx.createLinearGradient(0, 0, W, H);
    if (g && typeof g.addColorStop === "function") { g.addColorStop(0, pal.fond); g.addColorStop(1, rgba(pal.principale, 1)); }
    ctx.fillStyle = g || pal.fond;
    ctx.fillRect(0, 0, W, H);
    if (skin.logo && skin.logo.actif && prete(images.logo)) contenir(ctx, images.logo, W * 0.42, H * 0.14, W * 0.16, H * 0.24);
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillStyle = pal.texte; ctx.font = police(pol.titre, H * 0.085, true);
    ctx.fillText(ajuster(t.titre || "", W * 0.86, mes), W / 2, H * 0.52);
    if (t.sous_titre) {
      ctx.font = police(pol.texte, H * 0.04, false); ctx.fillStyle = rgba(pal.texte, 0.85);
      ctx.fillText(ajuster(t.sous_titre, W * 0.8, mes), W / 2, H * 0.63);
    }
    ctx.fillStyle = pal.accent; ctx.fillRect(W * 0.44, H * 0.7, W * 0.12, Math.max(2, H * 0.006));
  } });

  return {
    skin: () => skin,
    etat: st,
    maj(nouveau) { skin = nouveau || {}; appliquer(); },
    alerte(a) {
      if (!a || (a.type !== "abonne" && a.type !== "message")) return false;
      st.alertes.push({ type: a.type, nom: String(a.nom || "").slice(0, 40), texte: String(a.texte || "").slice(0, 80), debut: st.t });
      return true;
    },
    ecran(nom) { st.ecran = nom === "pause" || nom === "fin" ? nom : null; return st.ecran; },
    outro() {
      if (!skin.outro || !skin.outro.actif) return Promise.resolve(false);
      st.outro = st.t;
      const ms = (Number(skin.outro.duree_s) || 3) * 1000 + FONDU;
      return new Promise((ok) => setTimeout(() => ok(true), ms));
    },
    rejouer() { st.debut = null; st.decalage = 0; st.outro = null; st.ecran = null; st.alertes = []; },
    retirer() {
      retirerCrochet();
      IDS.forEach((id) => scene.retirerCalque(id));
      if (avaitClics) scene.ajouterCalque(calqueClics());
      if (avaitEncart) scene.ajouterCalque(calqueEncart());
      Object.assign(scene.etat, { cadre: avant.cadre || null, styleZoom: avant.styleZoom || null, forme: avant.forme });
    },
  };
}
