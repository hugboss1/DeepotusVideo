// dz-skins-logique.js — t316 (28/10/2026, lot D2 « skins de capture »), la LOGIQUE PURE des skins : couleurs et polices
// résolues (kit et identité de l'espace par défaut), textes par défaut, mise en page des éléments (dessin ET
// glisser-déposer de l'éditeur), phases de l'intro, de l'outro et du bandeau. Plan
// docs/superpowers/plans/2026-10-28-t316-skins.md, spec 2026-10-25-boite-a-outils-design.md §8.5.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared (banc backend/tests/test_skins_ecran.py, qui
// joue ce module sous node). Aucun accès au DOM : tout arrive en paramètre.
//
// Un skin est le document normalisé par le serveur (backend/app/services/skins.py) ; le `contexte` vient de
// GET /api/skins/{id} : {espace: {id, nom}, kit: {brand_color, accent_color, tagline_1, tagline_2}, polices: {titre,
// texte}, logo_espace}. Places normalisées 0..1 (x, y, l, et h pour l'encart).

export const Z = { fond: 40, cadre: 150, logo: 710, bandeau: 720, signature: 730, alertes: 760, carte: 790 };
export const FONDU = 400;                       // ms : entrée et sortie des cartes, du bandeau et des alertes
export const borne = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const HEX = /^#[0-9a-fA-F]{6}$/;
const FAMILLE = /^[A-Za-z0-9][A-Za-z0-9 \-]{0,39}$/;
export const POLICES = ["system-ui", "Inter", "IBM Plex Mono", "Georgia", "Times New Roman", "Arial Black", "Impact",
  "Trebuchet MS", "Verdana", "Courier New"];

// ── couleurs : principale/accent null = le kit de l'espace ; une référence = un rôle ou un #rrggbb ──
export function palette(skin, contexte) {
  const c = (skin && skin.couleurs) || {}, kit = (contexte && contexte.kit) || {};
  const sur = (v, d) => (typeof v === "string" && HEX.test(v) ? v : d);
  return {
    principale: sur(c.principale, sur(kit.brand_color, "#f0b429")),
    accent: sur(c.accent, sur(kit.accent_color, "#00e5ff")),
    texte: sur(c.texte, "#ffffff"),
    fond: sur(c.fond, "#0b0f14"),
  };
}
export function couleur(ref, pal) {
  if (typeof ref === "string" && HEX.test(ref)) return ref;
  return (pal && pal[ref]) || (pal && pal.principale) || "#f0b429";
}
// une couleur #rrggbb avec une opacité -> rgba()
export function rgba(hex, a) {
  const h = HEX.test(hex) ? hex : "#000000";
  const n = parseInt(h.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${borne(a, 0, 1).toFixed(3)})`;
}

// ── polices : null = l'identité de l'espace (titres, textes), sinon system-ui ; un nom douteux n'entre jamais ──
export function polices(skin, contexte) {
  const p = (skin && skin.polices) || {}, id = (contexte && contexte.polices) || {};
  const sure = (v) => (typeof v === "string" && FAMILLE.test(v) ? v : null);
  return { titre: sure(p.titre) || sure(id.titre) || "system-ui", texte: sure(p.texte) || sure(id.texte) || "system-ui" };
}
export function police(famille, taille, gras) {
  const f = typeof famille === "string" && FAMILLE.test(famille) ? famille : "system-ui";
  const nom = f === "system-ui" ? "system-ui" : `"${f}", system-ui`;
  return `${gras ? "700 " : ""}${Math.max(6, Math.round(taille))}px ${nom}, sans-serif`;
}

// ── textes : un champ vide prend le texte par défaut (nom de l'espace, slogans du kit, phrases traduites) ──
// T(cle) = dzT ; les clés skins.defaut.* sont dans frontend/shared/i18n/skins.json
export function textes(skin, contexte, T) {
  const s = skin || {}, cx = contexte || {}, kit = cx.kit || {}, nom = (cx.espace && cx.espace.nom) || "";
  const slogan = [kit.tagline_1, kit.tagline_2].filter((x) => typeof x === "string" && x.trim()).join(" ");
  const v = (sec, k, d) => { const x = s[sec] && s[sec][k]; return typeof x === "string" && x.trim() ? x.trim() : d; };
  return {
    intro: { titre: v("intro", "titre", nom), sous_titre: v("intro", "sous_titre", slogan) },
    outro: { titre: v("outro", "titre", T("skins.defaut.outro")), sous_titre: v("outro", "sous_titre", nom) },
    bandeau: { titre: v("bandeau", "titre", nom), sous_titre: v("bandeau", "sous_titre", slogan) },
    pause: { titre: v("pause", "titre", T("skins.defaut.pause")), sous_titre: v("pause", "sous_titre", nom) },
    fin: { titre: v("fin", "titre", T("skins.defaut.fin")), sous_titre: v("fin", "sous_titre", nom) },
    abonne: v("alertes", "abonne", T("skins.defaut.abonne")),
    message: v("alertes", "message", T("skins.defaut.message")),
    signature: T("skins.signature.texte"),
  };
}
// « {nom} vient de s'abonner » : seules les variables nom et texte, bornées
export function remplir(gabarit, vars) {
  return String(gabarit || "").replace(/\{(nom|texte)\}/g, (_, k) => String((vars && vars[k]) || "").slice(0, 80));
}

// ── mise en page : px de scène pour chaque élément déplaçable (et la signature, posée dans un coin) ──
export const HAUTEURS = { bandeau: 0.11, alertes: 0.09, signature: 0.034 };
export function disposer(skin, largeur, hauteur) {
  const s = skin || {}, W = largeur, H = hauteur, out = {};
  const place = (sec, h) => {
    const p = s[sec] || {};
    const l = borne(Number(p.l) || 0.2, 0.02, 1) * W, hh = h(l);
    return { x: borne((Number(p.x) || 0) * W, 0, W - l), y: borne((Number(p.y) || 0) * H, 0, Math.max(0, H - hh)), l, h: hh };
  };
  out.logo = place("logo", (l) => l);
  out.bandeau = place("bandeau", () => HAUTEURS.bandeau * H);
  out.alertes = place("alertes", () => HAUTEURS.alertes * H);
  const e = s.encart || {};
  const el = borne(Number(e.l) || 0.2, 0.08, 0.6), eh = borne(Number(e.h) || 0.3, 0.08, 0.6);
  out.encart = { x: borne(Number(e.x) || 0, 0, 1 - el) * W, y: borne(Number(e.y) || 0, 0, 1 - eh) * H, l: el * W, h: eh * H };
  const sg = (s.signature || {}).coin || "bas-droite", sl = 0.19 * W, sh = HAUTEURS.signature * H, m = 0.012 * W;
  out.signature = { x: sg.endsWith("gauche") ? m : W - sl - m, y: sg.startsWith("haut") ? m : H - sh - m, l: sl, h: sh };
  return out;
}
// l'élément sous le point (px de scène), le plus haut d'abord ; seuls les éléments ACTIFS se saisissent
export const DEPLACABLES = ["alertes", "bandeau", "logo", "signature", "encart"];
export function toucher(skin, rects, x, y, avecEncart) {
  for (const n of DEPLACABLES) {
    if (n === "encart" ? !avecEncart : !(skin && skin[n] && skin[n].actif)) continue;
    const r = rects[n];
    if (r && x >= r.x && x <= r.x + r.l && y >= r.y && y <= r.y + r.h) return n;
  }
  return null;
}
// déplacer un élément de (dx, dy) normalisés : une COPIE du skin, place tenue dans le cadre ; la signature se pose dans
// le coin le plus proche du point d'arrivée (cx, cy normalisés)
export function deplacer(skin, nom, dx, dy, largeur, hauteur, cx, cy) {
  const s = JSON.parse(JSON.stringify(skin || {}));
  if (nom === "signature") {
    s.signature = Object.assign({}, s.signature, { coin: (cy < 0.5 ? "haut-" : "bas-") + (cx < 0.5 ? "gauche" : "droite") });
    return s;
  }
  const p = s[nom];
  if (!p) return s;
  const r = disposer(skin, largeur, hauteur)[nom];
  const hN = r.h / hauteur, lN = r.l / largeur;
  p.x = Math.round(borne((Number(p.x) || 0) + dx, 0, 1 - lN) * 1e4) / 1e4;
  p.y = Math.round(borne((Number(p.y) || 0) + dy, 0, 1 - hN) * 1e4) / 1e4;
  return s;
}

// ── le temps : t = ms depuis le début de la scène habillée ──
// la carte à montrer : pause/fin (écran demandé) > outro (lancé) > intro (au début) ; alpha avec fondu
export function carte(skin, t, etat) {
  const s = skin || {}, e = etat || {};
  if (e.ecran === "pause" || e.ecran === "fin") return { nom: e.ecran, alpha: 1 };
  if (e.outro != null && s.outro && s.outro.actif) {
    const d = t - e.outro;
    return d >= 0 ? { nom: "outro", alpha: borne(d / FONDU, 0, 1) } : null;
  }
  if (s.intro && s.intro.actif) {
    const fin = (Number(s.intro.duree_s) || 3) * 1000;
    if (t >= 0 && t < fin) return { nom: "intro", alpha: borne((fin - t) / FONDU, 0, 1) };
  }
  return null;
}
// le bandeau : visible de debut_s à debut_s + duree_s (0 = jusqu'au bout), compté APRÈS l'intro ; alpha avec fondus
export function bandeau(skin, t) {
  const s = skin || {}, b = s.bandeau || {};
  if (!b.actif) return 0;
  const intro = s.intro && s.intro.actif ? (Number(s.intro.duree_s) || 3) * 1000 : 0;
  const debut = intro + (Number(b.debut_s) || 0) * 1000, duree = (Number(b.duree_s) || 0) * 1000;
  if (t < debut) return 0;
  const entree = borne((t - debut) / FONDU, 0, 1);
  if (!duree) return entree;
  if (t > debut + duree) return 0;
  return Math.min(entree, borne((debut + duree - t) / FONDU, 0, 1));
}
// les alertes vivantes : [{type, nom, texte, debut}] -> [{…, alpha, rang}] ; une alerte expirée disparaît
export function alertes(liste, t, dureeS) {
  const d = (Number(dureeS) || 5) * 1000;
  return (liste || []).filter((a) => t - a.debut >= 0 && t - a.debut <= d).slice(-3)
    .map((a, i) => Object.assign({}, a, { rang: i, alpha: Math.min(borne((t - a.debut) / FONDU, 0, 1), borne((a.debut + d - t) / FONDU, 0, 1)) }));
}
// le texte ramené à une largeur : coupé avec « … » (mesure = fonction texte -> px)
export function ajuster(texte, largeur, mesure) {
  let t = String(texte || "");
  if (!(largeur > 0) || mesure(t) <= largeur) return t;
  while (t.length > 1 && mesure(t + "…") > largeur) t = t.slice(0, -1);
  return t + "…";
}
