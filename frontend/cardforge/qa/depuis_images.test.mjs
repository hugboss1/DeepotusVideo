// t421 (cartes hexagonales, 07/11/2026, tâche 5) — la LOGIQUE du dialogue « Nouveau jeu depuis des images »
// (js/depuis-images-logique.js), jouée sous node : tri naturel, appariement recto / verso, nom de carte, fond perdu
// inclus ou non, format proposé et écarts de rapport. Les formats et la toile viennent du VRAI core.js, chargé dans un
// `vm` (aucune recopie de la table) ; le lot réel de l'utilisateur sert de cas : 89 images 1060 × 1484 et 4 images
// 977 × 1610, noms accentués.
// Lancer : node frontend/cardforge/qa/depuis_images.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const JS = new URL("../js/", import.meta.url);
let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : ""));
};
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/* le fichier livré, tel quel, dans un contexte qui imite le navigateur (window) */
function charger(nom, ctx) {
  vm.runInContext(readFileSync(new URL(nom, JS), "utf8"), ctx, { filename: nom });
  return ctx;
}
const ctxL = vm.createContext({ console });
ctxL.window = ctxL;
let L = null;
try { L = charger("depuis-images-logique.js", ctxL).CFImages; } catch (e) { echecs.push("chargement : " + e.message); }
ok("0.1 la logique se publie sous window.CFImages", !!L);
const ctxC = vm.createContext({ console, setTimeout, clearTimeout, URL });
ctxC.globalThis = ctxC;
charger("core.js", ctxC);
const CF = ctxC.CF;
ok("0.2 core.js publie CF", !!CF);

if (L && CF) {
  /* ── tri naturel ── */
  ok("1.1 tri naturel, casse ignorée", eq(L.triNaturel(["c10", "c2", "C1"]), ["C1", "c2", "c10"]),
     JSON.stringify(L.triNaturel(["c10", "c2", "C1"])));
  ok("1.2 tri naturel avec accents (é range avec e)",
     eq(L.triNaturel(["eb.png", "éa.png", "ec.png", "carte_10.png", "carte_9.png"]),
        ["carte_9.png", "carte_10.png", "éa.png", "eb.png", "ec.png"]));
  ok("1.3 le tri ne modifie pas la liste reçue", (() => { const a = ["b", "a"]; L.triNaturel(a); return eq(a, ["b", "a"]); })());

  /* ── appariement ── */
  const P = L.apparier(["a_recto.png", "a_verso.png", "b.png", "b_verso.png", "c_front.png", "c_back.png",
                        "d_verso.png", "e_recto-1.png", "e_verso.png"]);
  ok("2.1 trois cartes appariées, dans l'ordre naturel",
     eq(P.cartes.filter((c) => c.verso).map((c) => [c.recto, c.verso]),
        [["a_recto.png", "a_verso.png"], ["b.png", "b_verso.png"], ["c_front.png", "c_back.png"]]), JSON.stringify(P));
  ok("2.2 e_recto-1.png est une carte sans verso", eq(P.sansVerso, ["e_recto-1.png"])
     && P.cartes.some((c) => c.recto === "e_recto-1.png" && c.verso === null), JSON.stringify(P));
  ok("2.3 d_verso.png et e_verso.png sont orphelins", eq(P.orphelins, ["d_verso.png", "e_verso.png"]), JSON.stringify(P.orphelins));
  ok("2.4 quatre cartes en tout (un verso n'est jamais une carte)", P.cartes.length === 4, P.cartes.length);
  const P2 = L.apparier(["dos_VERSO.PNG", "dos.png", "le_pape_du_sanctuaire_brisé_recto.png", "le_pape_du_sanctuaire_brisé_verso.png"]);
  ok("2.5 suffixes sans casse, noms accentués appariés",
     eq(P2.cartes, [{ recto: "dos.png", verso: "dos_VERSO.PNG" },
                    { recto: "le_pape_du_sanctuaire_brisé_recto.png", verso: "le_pape_du_sanctuaire_brisé_verso.png" }]),
     JSON.stringify(P2));

  /* ── nom de carte ── */
  ok("3.1 nomCarte : sans extension, _ devient une espace", L.nomCarte("la_magnat_de_la_tech.png") === "la magnat de la tech",
     L.nomCarte("la_magnat_de_la_tech.png"));
  ok("3.2 nomCarte garde les accents", L.nomCarte("le_pape_du_sanctuaire_brisé.png") === "le pape du sanctuaire brisé");
  /* vague finale (I2, ruling) : une retouche du Photolab perd son préfixe photolab_AAAAMMJJ-HHMMSS_, comme _titre */
  ok("3.3 nomCarte retire le préfixe d'une retouche du Photolab",
     L.nomCarte("photolab_20261108-012041_adrian_veilleur_des_ames_fracturees.png") === "adrian veilleur des ames fracturees",
     L.nomCarte("photolab_20261108-012041_adrian_veilleur_des_ames_fracturees.png"));
  ok("3.4 nomCarte : préfixe seul gardé, préfixe mal formé gardé",
     L.nomCarte("photolab_20261108-012041_.png") === "photolab 20261108-012041"
     && L.nomCarte("photolab_2026-x_a.png") === "photolab 2026-x a", L.nomCarte("photolab_20261108-012041_.png"));
  ok("3.5 nomCarte garde un nom courant d'import", L.nomCarte("carte (1).png") === "carte (1)" && L.nomCarte("d'été.png") === "d'été");

  /* ── format proposé et écarts, sur le lot réel ── */
  const FMTS = CF.FORMATS.map((f) => ({ id: f.id, trim_mm: f.trim_mm, bleed_mm: CF.nativeBleed(f.id) }));
  const dims = [];
  for (let i = 1; i <= 89; i++) dims.push({ nom: "carte_" + i + ".png", w: 1060, h: 1484 });
  ["la_magnat_de_la_tech.png", "le_pape_du_sanctuaire_brisé.png", "z_long_1.png", "z_long_2.png"]
    .forEach((nom) => dims.push({ nom: nom, w: 977, h: 1610 }));
  ok("4.1 formatPropose : poker_us pour le lot réel", L.formatPropose(dims, FMTS) === "poker_us", L.formatPropose(dims, FMTS));
  const pk = FMTS.find((f) => f.id === "poker_us");
  const E = L.ecarts(dims, pk, false);
  ok("4.2 ecarts nomme les 4 cartes 977 × 1610", eq(L.triNaturel(E),
     ["la_magnat_de_la_tech.png", "le_pape_du_sanctuaire_brisé.png", "z_long_1.png", "z_long_2.png"]), JSON.stringify(E));
  ok("4.3 à la taille du gabarit, ecarts (fond perdu inclus) ne nomme que ces 4-là aussi",
     L.ecarts([{ nom: "g.png", w: 825, h: 1125 }], pk, true).length === 0
     && L.ecarts([{ nom: "g.png", w: 825, h: 1125 }], pk, false).length === 1);
  ok("4.4 formatPropose : à égalité, l'ordre des formats décide",
     L.formatPropose([{ nom: "x", w: 100, h: 100 }], [{ id: "a", trim_mm: [70, 70] }, { id: "b", trim_mm: [50, 50] }]) === "a");
  ok("4.5 formatPropose : un hexagone pointe en haut pour une image de son rapport",
     L.formatPropose([{ nom: "h", w: 866, h: 1000 }], FMTS) === "hex_p50", L.formatPropose([{ nom: "h", w: 866, h: 1000 }], FMTS));
  ok("4.6 formatPropose : sans dimensions connues, rien n'est proposé", L.formatPropose([{ nom: "x", w: null, h: null }], FMTS) === null);
  ok("4.7 ecarts ignore une image sans dimensions", L.ecarts([{ nom: "x", w: null, h: null }], pk, false).length === 0);

  /* ── fond perdu inclus : le rapport de la TOILE (geomOf : coupe + 2 × fond perdu) ── */
  const cas = [["poker_us", 300], ["poker_eu", 300], ["tarot_eu", 600], ["hex_p50", 300], ["hex_f90", 300], ["hex_p90", 600]];
  cas.forEach(([id, dpi]) => {
    const b = CF.nativeBleed(id), g = CF.geomOf(id, dpi, b, 3, 0);
    const f = FMTS.find((x) => x.id === id);
    ok(`5.1 ${id} à ${dpi} dpi : vrai à la taille du gabarit (${g.canvas_px.join("×")})`,
       L.inclutFondPerdu(g.canvas_px[0], g.canvas_px[1], f, b) === true);
    ok(`5.2 ${id} à ${dpi} dpi : faux à la taille de coupe (${g.trim_px.join("×")})`,
       L.inclutFondPerdu(g.trim_px[0], g.trim_px[1], f, b) === false);
  });
  ok("5.3 le lot réel (cartes finies, 1060 × 1484) n'inclut pas le fond perdu", L.inclutFondPerdu(1060, 1484, pk, 3.175) === false);
  ok("5.4 fond perdu nul : jamais « inclus »", L.inclutFondPerdu(750, 1050, pk, 0) === false);
}

/* ══ 6. LE DIALOGUE, joué sous node : faux DOM, faux CF (formats du VRAI core.js), dzT qui rend la clé ══ */
const INNER = [];
class Noeud {
  constructor(tag, texte) {
    this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.ec = {}; this.parentNode = null;
    this._t = texte == null ? "" : String(texte); this.className = ""; this.hidden = false; this.disabled = false;
    this.value = ""; this.checked = false; this.files = [];
    const moi = this;
    this.classList = {
      contains: (c) => moi.className.split(/\s+/).indexOf(c) >= 0,
      toggle: (c, on) => {
        const l = moi.className.split(/\s+/).filter(Boolean).filter((x) => x !== c);
        if (on) l.push(c);
        moi.className = l.join(" ");
      },
    };
  }
  get firstChild() { return this.children[0] || null; }
  get textContent() { return this.tagName === "#TEXT" ? this._t : this._t + this.children.map((c) => c.textContent).join(""); }
  set textContent(v) { this.children = []; this._t = String(v); }
  set innerHTML(_v) { INNER.push(this.tagName); }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  removeChild(c) { this.children.splice(this.children.indexOf(c), 1); c.parentNode = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  removeEventListener(t, f) { this.ec[t] = (this.ec[t] || []).filter((x) => x !== f); }
  fire(t, ev) { (this.ec[t] || []).forEach((f) => f(ev || { preventDefault() {} })); }
  click() { this.fire("click"); }
  focus() {}
}
const tous = (r, out = []) => { out.push(r); r.children.forEach((c) => tous(c, out)); return out; };
const trouve = (r, f) => tous(r).filter(f);
const parClasse = (r, c) => trouve(r, (x) => x.classList.contains(c));
const dort = () => new Promise((res) => setTimeout(res, 0));

const BIB = [];
for (let i = 1; i <= 6; i++) BIB.push({ filename: "carte_" + i + ".png", width: 1060, height: 1484 });
BIB.push({ filename: "le_pape_du_sanctuaire_brisé.png", width: 977, height: 1610 });
BIB.push({ filename: "la_magnat_de_la_tech.png", width: 977, height: 1610 });
BIB.push({ filename: "carte_1_verso.png", width: 1060, height: 1484 });
BIB.push({ filename: "seul_verso.png", width: 1060, height: 1484 });
const APPELS = [];
const fauxCF = CF && {
  FORMATS: CF.FORMATS, nativeBleed: CF.nativeBleed,
  doc: () => ({ format: { fmt: "poker_eu" } }),
  libelleFormat: (id) => "⟦fmt:" + id + "⟧",
  gabaritUrl: (fmt, ext, opt) => "/api/cards/gabarit/" + fmt + "." + ext + (opt && opt.bleed_mm != null ? "?bleed_mm=" + opt.bleed_mm : ""),
  busy: (on, t) => APPELS.push(["busy", on, t]),
  bibliotheque: {
    images: async () => BIB.slice(),
    projets: async () => [{ id: "p1", nom: "Mon lot", n: 2 }],
    projet: async (id) => ({ id: id, nom: "Mon lot", refs: ["carte_2.png", "carte_3.png"] }),
    importer: async (f) => {
      const nom = f.name.replace(".png", "-1.png");      /* l'homonyme : le nom RENDU fait foi */
      BIB.push({ filename: nom, width: 1060, height: 1484 });
      return { filename: nom };
    },
    url: (nom) => "/api/images/" + encodeURIComponent(nom),
  },
  deckDepuisImages: async (corps) => { APPELS.push(["deck", corps]); return { id: "deck_00000001" }; },
};
if (fauxCF) {
  const body = new Noeud("body");
  const docEc = {};
  const ctxD = vm.createContext({
    console, setTimeout,
    dzT: (k, v) => "⟦" + k + (v ? JSON.stringify(v) : "") + "⟧",
    document: {
      body: body,
      createElement: (t) => new Noeud(t), createElementNS: (_ns, t) => new Noeud(t), createTextNode: (t) => new Noeud("#text", t),
      addEventListener: (t, f) => { docEc[t] = f; }, removeEventListener: (t) => { delete docEc[t]; },
    },
  });
  ctxD.window = ctxD;
  ctxD.CF = fauxCF;
  charger("depuis-images-logique.js", ctxD);
  charger("depuis-images.js", ctxD);
  const D = ctxD.CFDepuisImages;
  ok("6.0 le dialogue se publie sous window.CFDepuisImages", !!(D && D.ouvrir));
  D.ouvrir();
  await dort();
  const root = body.children[0];
  ok("6.1 la boîte est posée, en dialogue modal, à l'étape 1", root && root.className === "cf-di"
     && trouve(root, (x) => x.attrs.role === "dialog" && x.attrs["aria-modal"] === "true").length === 1
     && parClasse(root, "cur")[0].textContent.indexOf("cartes.depuis.e1") >= 0);
  const opts = trouve(root, (x) => x.tagName === "OPTION");
  ok("6.2 le format propose les 20 formats, hexagones d'abord", opts.length === 20 && opts[0].value === "hex_p50"
     && trouve(root, (x) => x.tagName === "OPTGROUP").length === 2, opts.length);
  const suiv = () => parClasse(root, "cf-di-pied")[0].children[3];
  suiv().click();
  await dort();
  let tuiles = parClasse(root, "cf-di-tuile");
  ok("6.3 étape 2 : une tuile par image, en tri naturel, vignettes paresseuses",
     tuiles.length === BIB.length && tuiles[0].title === "carte_1.png" && tuiles[1].title === "carte_1_verso.png"
     && tuiles.every((t) => t.children[0].tagName === "IMG" && t.children[0].loading === "lazy"), tuiles.map((t) => t.title));
  suiv().click();
  ok("6.4 sans image choisie, on ne quitte pas l'étape 2", parClasse(root, "cf-di-msg")[0].textContent.indexOf("aucune_image") >= 0);
  const recherche = parClasse(root, "cf-di-recherche")[0];
  recherche.value = "brise"; recherche.fire("input");
  ok("6.5 la recherche ignore les accents", tuiles.filter((t) => !t.hidden).map((t) => t.title).join() === "le_pape_du_sanctuaire_brisé.png");
  recherche.value = ""; recherche.fire("input");
  const pj = parClasse(root, "cf-di-projet")[0];
  ok("6.6 le filtre de projet liste les projets", pj.children.length === 2 && pj.children[1].value === "p1");
  pj.value = "p1"; pj.fire("change"); await dort();
  ok("6.7 le filtre de projet ne montre que ses images", tuiles.filter((t) => !t.hidden).map((t) => t.title).join() === "carte_2.png,carte_3.png");
  pj.value = ""; pj.fire("change");
  const outils = parClasse(root, "cf-di-outils")[0].children.filter((x) => x.tagName === "BUTTON");
  recherche.value = "magnat"; recherche.fire("input");
  outils[0].click();
  ok("6.8 « Tout sélectionner » ne coche que les images visibles",
     tuiles.filter((t) => t.classList.contains("on")).map((t) => t.title).join() === "la_magnat_de_la_tech.png");
  outils[1].click();
  ok("6.8b « Tout désélectionner » vide la sélection", tuiles.every((t) => !t.classList.contains("on")));
  recherche.value = ""; recherche.fire("input");
  outils[0].click();
  ok("6.8c sans filtre, tout est coché", tuiles.every((t) => t.classList.contains("on") && t.attrs["aria-pressed"] === "true"));
  const fic = parClasse(root, "cf-di-fichiers")[0];
  ok("6.9 l'import accepte plusieurs fichiers", fic.multiple === true && fic.type === "file");
  fic.files = [{ name: "neuve.png" }]; fic.fire("change"); await dort(); await dort();
  tuiles = parClasse(root, "cf-di-tuile");
  ok("6.10 l'image importée apparaît, cochée, sous le nom rendu", tuiles.length === BIB.length
     && tuiles.some((t) => t.title === "neuve-1.png" && t.classList.contains("on")), tuiles.map((t) => t.title));
  /* on décoche l'importée pour garder le lot de départ */
  tuiles.find((t) => t.title === "neuve-1.png").click();
  suiv().click(); await dort();
  ok("6.11 étape 3 : trois modes de verso", trouve(root, (x) => x.tagName === "INPUT" && x.type === "radio").length === 3);
  const radio = trouve(root, (x) => x.tagName === "INPUT" && x.type === "radio" && x.value === "apparie")[0];
  radio.checked = true; radio.fire("change");
  ok("6.12 apparié : le bilan et les listes (sans verso, orphelins)",
     parClasse(root, "cf-di-corps")[0].textContent.indexOf('cartes.depuis.apparie_bilan{"n":8,"p":1}') >= 0
     && parClasse(root, "cf-di-liste").length === 2, parClasse(root, "cf-di-corps")[0].textContent.slice(0, 400));
  suiv().click(); await dort();
  const corpsTxt = parClasse(root, "cf-di-corps")[0].textContent;
  ok("6.13 étape 4 : format proposé poker_us, fond perdu décoché d'office, avertissement de liseré",
     corpsTxt.indexOf("fmt:poker_us") >= 0 && corpsTxt.indexOf("cartes.depuis.format_propose") >= 0
     && trouve(root, (x) => x.type === "checkbox")[0].checked === false && parClasse(root, "cf-di-avert").length === 1, corpsTxt.slice(0, 300));
  ok("6.14 étape 4 : écarts (2), rectos sans verso (7), orphelins (1)",
     corpsTxt.indexOf('cartes.depuis.ecarts{"n":2}') >= 0 && corpsTxt.indexOf('cartes.depuis.sans_verso{"n":7}') >= 0
     && corpsTxt.indexOf('cartes.depuis.orphelins{"n":1}') >= 0, corpsTxt.slice(0, 600));
  const cb = trouve(root, (x) => x.type === "checkbox")[0];
  cb.checked = true; cb.fire("change");
  ok("6.15 cocher le fond perdu retire l'avertissement de liseré", parClasse(root, "cf-di-avert").length === 0);
  const cb2 = trouve(root, (x) => x.type === "checkbox")[0];
  cb2.checked = false; cb2.fire("change");
  /* t421 (tâche 6) : le gabarit de dessin, pour un hexagone seulement */
  ok("6.15b un rectangle n'a pas de gabarit à télécharger", parClasse(root, "cf-di-gabarit").length === 0);
  const versFormat = async (id) => {
    parClasse(root, "cf-di-etape")[0].click(); await dort();
    const sel = trouve(root, (x) => x.tagName === "SELECT")[0];
    sel.value = id; sel.fire("change"); await dort();
    parClasse(root, "cf-di-etape")[3].click(); await dort();
  };
  await versFormat("hex_p75");
  const liensG = trouve(parClasse(root, "cf-di-gabarit")[0] || root, (x) => x.tagName === "A");
  ok("6.15c un hexagone : deux liens, PNG et SVG, vers la route du gabarit (fond perdu natif si le fichier en a un)",
     liensG.length === 2 && liensG[0].attrs.href === "/api/cards/gabarit/hex_p75.png?bleed_mm=0"
     && liensG[1].attrs.href === "/api/cards/gabarit/hex_p75.svg?bleed_mm=0"
     && "download" in liensG[0].attrs, JSON.stringify(liensG.map((l) => l.attrs)));
  const cbG = trouve(root, (x) => x.type === "checkbox")[0];
  cbG.checked = true; cbG.fire("change");
  ok("6.15d fichier avec fond perdu : le gabarit garde le fond perdu natif (aucun paramètre)",
     trouve(parClasse(root, "cf-di-gabarit")[0], (x) => x.tagName === "A")[0].attrs.href === "/api/cards/gabarit/hex_p75.png");
  await versFormat("poker_us");
  /* le texte affiché : rien que des clés dzT, des noms de fichiers, des chiffres et de la ponctuation */
  const textes = tous(root).filter((x) => x._t).map((x) => x._t)
    .concat(tous(root).flatMap((x) => [x.title, x.placeholder, x.attrs["aria-label"]].filter(Boolean)));
  const noms = new Set(BIB.map((b) => b.filename));
  const durs = textes.filter((t) => !/⟦/.test(t) && !noms.has(t) && !/^[\d\s().,;:—×/+-]*$/.test(t)
    && !BIB.some((b) => t === L.nomCarte(b.filename)));
  ok("6.16 aucun texte affiché hors dzT (sauf noms de fichiers et de cartes)", !durs.length, JSON.stringify(durs));
  suiv().click(); await dort();
  const dk = APPELS.filter((a) => a[0] === "deck");
  const c0 = dk.length && dk[0][1];
  ok("6.17 Créer : CF.deckDepuisImages reçoit le corps de la route", dk.length === 1 && c0.format === "poker_us"
     && c0.fond_perdu === false && c0.name === "⟦cartes.depuis.nom_defaut⟧" && c0.images.length === 8
     && c0.images[0] === "carte_1.png" && c0.versos[0] === "carte_1_verso.png" && c0.versos.slice(1).every((v) => v === null)
     && !("verso_commun" in c0) && c0.images.indexOf("seul_verso.png") < 0, JSON.stringify(c0));
  ok("6.18 le voile de création est posé", APPELS.some((a) => a[0] === "busy" && a[1] === true));
  ok("6.19 aucun innerHTML", INNER.length === 0, INNER.join());
  D.fermer();
  ok("6.20 fermer retire la boîte et l'écoute d'Échap", body.children.length === 0 && !docEc.keydown);
}

console.log(`${n - echecs.length}/${n} vérifications`);
if (echecs.length) {
  echecs.forEach((e) => console.log("  KO  " + e));
  process.exit(1);
}
console.log("OK");
