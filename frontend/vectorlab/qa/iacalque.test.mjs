// iacalque.test.mjs — t190 (G8) : l'image IA PAR CALQUE et « Retirer le fond » réversible. Logique PURE de
// mod-iacalque (format d'après la page, corps des routes réelles, plan du tir, cible refusée avant toute
// dépense, anti-double tir, libellé du prix serveur), le tir de bout en bout sur de FAUSSES routes, et
// l'annulation du détourage par le vrai Historique de mod-doc. initIaCalque n'est jamais appelé.
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { taillePour, requete, requeteDetour, etapes, verifierCible, calquesCibles, devisCorps, libellePrix,
         messageErreur, unSeulVol, executerPlan, op_image_remplacer, retirerFondFlux, nomDepot, TAILLES,
         garderClics, brancherPoignee, GESTES_GARDES }
  from "../js/mod-iacalque.js";
import { docVierge } from "../js/mod-biblio.js";
import { Historique, op_calque_ajouter, op_calque_verrou, op_ajouter } from "../js/mod-doc.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const lit = (p) => readFileSync(new URL(p, import.meta.url), "utf8");

/* ── [taille] le format le plus proche de la page ── */
ok("[taille] 1080×1920 → portrait_16_9", taillePour({ w: 1080, h: 1920 }) === "portrait_16_9");
ok("[taille] 1920×1080 → landscape_16_9", taillePour({ w: 1920, h: 1080 }) === "landscape_16_9");
ok("[taille] 1000×1000 → square_hd", taillePour({ w: 1000, h: 1000 }) === "square_hd");
ok("[taille] 3:4 → portrait_4_3 ; 4:3 → landscape_4_3",
   taillePour({ w: 1500, h: 2000 }) === "portrait_4_3" && taillePour({ w: 2000, h: 1500 }) === "landscape_4_3");
ok("[taille] taille illisible → square_hd", taillePour(null) === "square_hd" && taillePour({ w: 0, h: 5 }) === "square_hd");
ok("[taille] chaque format rendu est accepté par /images/generate",
   [[1, 3], [3, 4], [1, 1], [4, 3], [3, 1]].every(([w, h]) => TAILLES.includes(taillePour({ w, h }))));

/* ── [requete] la forme RÉELLE de /api/images/generate (routes.py : prompt, n, model, size, source) ── */
{
  const q = requete({ prompt: " un renard ", modele: "flux-3", taille: "square_hd" });
  ok("[requete] corps exact", egal(q, { prompt: "un renard", n: 1, model: "flux-3", size: "square_hd", source: "vectorlab" }), JSON.stringify(q));
  const s = requete({ prompt: "x", taille: "inconnue" });
  ok("[requete] sans modèle : pas de model (défaut des Réglages) ; format inconnu → square_hd",
     !("model" in s) && s.size === "square_hd", JSON.stringify(s));
  let refus = false;
  try { requete({ prompt: "   " }); } catch (e) { refus = true; }
  ok("[requete] prompt vide refusé", refus);
  const d = requeteDetour({ nom: "gen_1.png", modele: "birefnet-v2" });
  ok("[detour] corps du registre G4 (sans sujet)",
     egal(d, { op: "remove-bg", filename: "gen_1.png", modele: "birefnet-v2", source: "vectorlab" }), JSON.stringify(d));
  ok("[detour] sujet transmis s'il est dit", requeteDetour({ nom: "a", modele: "sam3-sujet", sujet: " le renard " }).sujet === "le renard");
}

/* ── [etapes] le plan ── */
{
  const plan = etapes({ calqueId: "c3", detourer: true, modeleDetour: "birefnet-v2" });
  ok("[etapes] générer, détourer, poser", egal(plan.map((e) => e.op), ["generer", "detourer", "poser"]));
  ok("[etapes] la pose vise le calque DEMANDÉ", plan[2].calqueId === "c3", JSON.stringify(plan));
  ok("[etapes] détourage avec son modèle", plan[1].modele === "birefnet-v2");
  ok("[etapes] sans détourage : générer, poser", egal(etapes({ calqueId: "c1" }).map((e) => e.op), ["generer", "poser"]));
}

/* ── [verrouillé] la cible refusée AVANT toute dépense ── */
{
  const doc = docVierge("t", 100, 100); doc.calques[0].verrou = true;
  let m = "";
  try { verifierCible(doc, doc.calques[0].id); } catch (e) { m = e.message; }
  ok("[verrouillé] calque verrouillé refusé", /verrouill/.test(m), m);
  let m2 = "";
  try { verifierCible(doc, "zz"); } catch (e) { m2 = e.message; }
  ok("[verrouillé] calque inconnu refusé", !!m2 && !/^vectorlab\./.test(m2), m2);
  doc.calques[0].verrou = false;
  ok("[verrouillé] calque libre accepté", verifierCible(doc, "c1").id === "c1");
  const d2 = docVierge("t", 100, 100);
  const c2 = op_calque_ajouter(d2, "calque 2"); const c3 = op_calque_ajouter(d2, "calque 3");
  op_calque_verrou(d2, c2, true);
  ok("[cibles] calques non verrouillés, le dessus en tête", egal(calquesCibles(d2).map((c) => c.id), [c3, "c1"]));
}

/* ── [tir] de bout en bout sur de fausses routes ── */
const banc = () => {
  const doc = docVierge("t", 1080, 1920);
  const c2 = op_calque_ajouter(doc, "calque 2"), c3 = op_calque_ajouter(doc, "calque 3");
  const appels = [], poses = [];
  const d = {
    calqueActif: "c1",
    doc: () => doc,
    post: async (url, corps) => {
      appels.push({ url, corps });
      if (url === "/api/images/generate") return { images: ["gen_a.png"], model: corps.model };
      if (url === "/api/images/process") return { images: ["gen_b.png"], op: "remove-bg", modele: corps.modele };
      throw new Error("route inattendue " + url);
    },
    poser: async (nom, calqueId) => { poses.push({ nom, calqueId }); return "o9"; },
  };
  return { doc, c2, c3, appels, poses, d };
};
{
  const b = banc();
  const r = await executerPlan({ calqueId: b.c3, prompt: "un renard", modele: "flux-3", taille: "portrait_16_9",
                                 detourer: true, modeleDetour: "birefnet-v2" }, b.d);
  ok("[etapes] tir : generate puis process", egal(b.appels.map((a) => a.url), ["/api/images/generate", "/api/images/process"]));
  ok("[etapes] le détourage porte sur l'image GÉNÉRÉE", b.appels[1].corps.filename === "gen_a.png", JSON.stringify(b.appels[1]));
  ok("[etapes] l'image DÉTOURÉE est posée sur le calque demandé (pas l'actif)",
     egal(b.poses, [{ nom: "gen_b.png", calqueId: b.c3 }]), JSON.stringify(b.poses));
  ok("[etapes] le tir rend le nom et l'objet posé", r.nom === "gen_b.png" && r.id === "o9");
}
{
  const b = banc();
  op_calque_verrou(b.doc, b.c3, true);
  let m = "";
  try { await executerPlan({ calqueId: b.c3, prompt: "x", modele: "flux-3" }, b.d); } catch (e) { m = e.message; }
  ok("[verrouillé] tir vers un calque verrouillé : refusé, AUCUN appel payant", /verrouill/.test(m) && b.appels.length === 0,
     m + " / " + b.appels.length);
  let m2 = "";
  try { await executerPlan({ calqueId: b.c2, prompt: "  " }, b.d); } catch (e) { m2 = e.message; }
  ok("[requete] prompt vide : aucun appel", !!m2 && b.appels.length === 0);
}
{
  const b = banc();
  b.d.post = async () => ({ images: [] });
  let m = "";
  try { await executerPlan({ calqueId: b.c2, prompt: "x" }, b.d); } catch (e) { m = e.message; }
  ok("[tir] génération vide : erreur lisible, rien n'est posé", /aucune image/.test(m) && b.poses.length === 0, m);
}

/* ── [vol] un second clic pendant le vol ne relance rien ── */
{
  let tirs = 0, lacher;
  const f = unSeulVol(() => { tirs++; return new Promise((res) => { lacher = res; }); });
  const p1 = f(), p2 = f();
  ok("[vol] en vol après le premier appel", f.enVol === true);
  lacher("fait");
  const [r1, r2] = await Promise.all([p1, p2]);
  ok("[vol] un seul tir pour deux clics", tirs === 1 && r1 === "fait" && r2 === null, `${tirs} ${r1} ${r2}`);
  ok("[vol] libéré après le vol", f.enVol === false);
  const g = unSeulVol(async () => { throw new Error("x"); });
  try { await g(); } catch (e) { /* attendu */ }
  ok("[vol] libéré après un échec", g.enVol === false);
}

/* ── [prix] chiffré par le serveur, jamais inventé ── */
{
  ok("[prix] devis : campagne image + détourage",
     egal(devisCorps({ modele: "flux-3", detourer: true, modeleDetour: "bria-rmbg" }),
          { kind: "campaign", ops: [{ kind: "image", model: "flux-3", n: 1 }, { kind: "detourage", modele: "bria-rmbg", images: 1 }] }));
  ok("[prix] sans détourage : l'image seule", devisCorps({ modele: "flux-3", detourer: false, modeleDetour: "x" }).ops.length === 1);
  const L = (prov, usd) => ({ provider: prov, usd });
  ok("[prix] total du serveur", libellePrix({ breakdown: [L("fal", 0.048), L("fal", 0.018)], total_usd: 0.066 }).includes("$0.066"));
  ok("[prix] 0 $ → prix à mesurer (jamais gratuit)", /mesurer/.test(libellePrix({ breakdown: [L("fal", 0)], total_usd: 0 })));
  ok("[prix] ligne payante à 0 $ : total partiel dit",
     /mesurer/.test(libellePrix({ breakdown: [L("fal", 0.048), L("fal", 0)], total_usd: 0.048 })));
  ok("[prix] ligne locale à 0 $ : pas « à mesurer »",
     !/mesurer/.test(libellePrix({ breakdown: [L("fal", 0.048), L("local", 0)], total_usd: 0.048 })));
  ok("[prix] devis absent : texte d'attente, pas de chiffre", !/\$/.test(libellePrix(null)));
}

/* ── [erreurs] 503 lisible, plafond refusé lisible ── */
{
  const m = messageErreur(503, { detail: "FAL_KEY non configurée (Réglages) pour flux-3." });
  ok("[erreurs] 503 : la clé manquante est dite", m.includes("FAL_KEY") && m !== "FAL_KEY non configurée (Réglages) pour flux-3.", m);
  ok("[erreurs] 402 refusé (detail chaîne) rendu tel quel", messageErreur(402, { detail: "plafond atteint" }) === "plafond atteint");
  ok("[erreurs] detail objet du plafond : son message", messageErreur(402, { detail: { dz_plafond: { message: "mois plein" } } }) === "mois plein");
}

/* ── [annuler] « Retirer le fond » : UNE commande réversible, l'image d'avant revient ── */
const docImage = () => {
  const doc = docVierge("t", 400, 300);
  op_ajouter(doc, "c1", { id: "i1", type: "image", x: 0, y: 0, w: 200, h: 100, href: "img1.png",
                           nat: { w: 800, h: 400 }, rev: 3, px: "0123456789abcdef", rognage: { x: 0, y: 0, w: 400, h: 400 }, style: {} });
  return doc;
};
{
  let doc = docImage();
  const h = new Historique();
  const executer = (fn, ...a) => { const essai = JSON.parse(JSON.stringify(doc)); const out = fn(essai, ...a); h.capturer(doc); doc = essai; return out; };
  const appels = [];
  const d = {
    versBiblio: async (o) => { appels.push(["biblio", o.href]); return nomDepot("doc 1", o.href); },
    post: async (url, corps) => { appels.push([url, corps]); return { images: ["gen_det.png"], op: "remove-bg", modele: corps.modele }; },
    deposer: async (nom) => { appels.push(["deposer", nom]); return { href: "img2.png", nat: { w: 800, h: 400 } }; },
    executer,
  };
  const o = doc.calques[0].objets[0];
  const href = await retirerFondFlux(o, { modele: "bria-rmbg" }, d);
  const apres = doc.calques[0].objets[0];
  ok("[annuler] le détourage passe par la Bibliothèque puis /images/process",
     appels[0][0] === "biblio" && appels[1][0] === "/api/images/process" && appels[1][1].filename === "vector_doc-1_detour_img1.png"
     && appels[1][1].modele === "bria-rmbg" && appels[1][1].op === "remove-bg", JSON.stringify(appels));
  ok("[annuler] l'objet désigne la NOUVELLE image (révision et empreinte de l'ancienne retirées)",
     href === "img2.png" && apres.href === "img2.png" && !("rev" in apres) && !("px" in apres) && apres.rognage, JSON.stringify(apres));
  ok("[annuler] le détourage est entré dans l'historique", h.peutAnnuler());
  doc = docImage(); const h2 = new Historique();
  const ex2 = (fn, ...a) => { const essai = JSON.parse(JSON.stringify(doc)); fn(essai, ...a); h2.capturer(doc); doc = essai; };
  await retirerFondFlux(doc.calques[0].objets[0], { modele: "bria-rmbg" }, { ...d, executer: ex2 });
  ok("[annuler] après le détourage : img2.png", doc.calques[0].objets[0].href === "img2.png");
  ok("[annuler] le détourage est UNE étape de l'historique", h2.peutAnnuler());
  if (h2.peutAnnuler()) doc = h2.annuler(doc);
  const rendu = doc.calques[0].objets[0];
  ok("[annuler] Annuler restaure l'image d'avant (href, révision, empreinte)",
     rendu.href === "img1.png" && rendu.rev === 3 && rendu.px === "0123456789abcdef", JSON.stringify(rendu));
  ok("[annuler] plus rien à annuler : c'était UNE étape", !h2.peutAnnuler());
  if (h2.peutRefaire()) doc = h2.refaire(doc);
  ok("[annuler] Refaire remet l'image détourée", doc.calques[0].objets[0].href === "img2.png");
}
{
  // jamais par-dessus : un dépôt qui rendrait le même href est refusé, rien n'est exécuté
  const doc = docImage();
  let execs = 0;
  let m = "";
  try {
    await retirerFondFlux(doc.calques[0].objets[0], { modele: "bria-rmbg" }, {
      versBiblio: async () => "a.png", post: async () => ({ images: ["b.png"] }),
      deposer: async () => ({ href: "img1.png", nat: { w: 800, h: 400 } }), executer: () => { execs++; } });
  } catch (e) { m = e.message; }
  ok("[annuler] même href refusé (l'image d'avant serait perdue)", !!m && execs === 0, m);
  let m2 = "";
  try { await retirerFondFlux(doc.calques[0].objets[0], { modele: "" }, { versBiblio: async () => { throw new Error("ne doit pas partir"); } }); }
  catch (e) { m2 = e.message; }
  ok("[annuler] sans modèle : refusé avant tout envoi", !!m2 && !/ne doit pas partir/.test(m2), m2);
  const d2 = docImage();
  op_image_remplacer(d2, "i1", "img3.png", { w: 50, h: 50 });
  ok("[annuler] nouvelle taille native : le rognage qui ne tient plus tombe", !d2.calques[0].objets[0].rognage);
  let refus = 0;
  try { op_image_remplacer(d2, "zz", "a.png", { w: 1, h: 1 }); } catch { refus++; }
  try { op_image_remplacer(d2, "i1", "", { w: 1, h: 1 }); } catch { refus++; }
  ok("[annuler] image inconnue ou href vide refusés", refus === 2);
}

/* ── [cle] une option SANS clé reste CHOISISSABLE (jamais disabled) ── */
{
  const src = lit("../../shared/dz-modeles-ia.js");
  const ctx = { window: {} };
  vm.runInNewContext(src, ctx);
  const G = ctx.window.DzModelesIA.grouper([
    { id: "flux-3", voie: "fal", cle: "FAL_KEY", dispo: false, usd: 0.048, unite: "image" },
    { id: "gpt-image-2", voie: "openai", cle: "OPENAI_API_KEY", dispo: false, usd: 0.12 }]);
  const opts = G.flatMap((g) => g.options);
  ok("[cle] DzModelesIA : option sans clé jamais désactivée, la clé est dite",
     opts.length === 2 && opts.every((o) => o.desactive === false && o.sansCle && /clé/.test(o.texte)), JSON.stringify(opts));
  const mod = lit("../js/mod-iacalque.js");
  const fautives = mod.split("\n").filter((l) => /disabled/.test(l) && /option|dispo|sansCle|sans-cle|\bcle\b/i.test(l));
  ok("[cle] mod-iacalque ne désactive aucune option de modèle", !fautives.length, fautives.join(" | "));
  const ia = lit("../../shared/dz-modeles-ia.js");
  ok("[cle] dz-modeles-ia : op.disabled = o.desactive (toujours faux)", /op\.disabled = o\.desactive;/.test(ia) && /desactive: false/.test(ia));
}

/* ── [clics] le panneau vit dans #stage : ses gestes n'atteignent pas les outils de la scène ──
   un mini-DOM à propagation réelle (capture de la racine vers la cible, puis bulle), comme le navigateur */
{
  class Noeud {
    constructor(parent, attrs = {}) { this.parent = parent; this.attrs = attrs; this.ec = []; this.style = {}; }
    addEventListener(type, fn, o) { this.ec.push({ type, fn, capture: o === true || !!(o && o.capture) }); }
    removeEventListener(type, fn) { this.ec = this.ec.filter((e) => !(e.type === type && e.fn === fn)); }
    closest(sel) {
      for (let n = this; n; n = n.parent) {
        if (sel === "[data-poigne]" && n.attrs.poigne) return n;
        if (sel === "button" && n.attrs.tag === "button") return n;
      }
      return null;
    }
    getBoundingClientRect() { return this.attrs.rect || { left: 0, top: 0, width: 0, height: 0 }; }
    dispatch(type, extra = {}) {
      const ev = { type, target: this, arrete: false, empeche: false, ...extra,
        stopPropagation() { this.arrete = true; }, preventDefault() { this.empeche = true; } };
      const chemin = [];
      for (let n = this; n; n = n.parent) chemin.unshift(n);
      for (const n of chemin.slice(0, -1)) { for (const e of n.ec.filter((x) => x.type === type && x.capture)) e.fn(ev); if (ev.arrete) return ev; }
      for (const n of [...chemin].reverse()) {
        for (const e of n.ec.filter((x) => x.type === type && (n === this || !x.capture))) e.fn(ev);
        if (ev.arrete) return ev;
      }
      return ev;
    }
  }
  const monter = () => {
    const stage = new Noeud(null, { rect: { left: 0, top: 0, width: 1000, height: 800 } });
    const el = new Noeud(stage, { rect: { left: 700, top: 20, width: 280, height: 400 } });
    const tete = new Noeud(el, { poigne: true });
    const caseDetour = new Noeud(el, { tag: "input" }), go = new Noeud(el, { tag: "button" });
    const win = new Noeud(null);
    const vus = [];
    // l'outil Sélection de mod-tools : en BULLE sur #stage, setPointerCapture + geste
    stage.addEventListener("pointerdown", (ev) => vus.push(ev.type + ":" + (ev.target === caseDetour ? "case" : ev.target === go ? "go" : "autre")));
    for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) stage.addEventListener(t, (ev) => vus.push(t));
    garderClics(el);
    brancherPoignee(el, stage, win);
    return { stage, el, tete, caseDetour, go, win, vus };
  };
  const m = monter();
  const e1 = m.caseDetour.dispatch("pointerdown", { clientX: 750, clientY: 200 });
  const e2 = m.go.dispatch("pointerdown", { clientX: 760, clientY: 300 });
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) m.caseDetour.dispatch(t);
  ok("[clics] un pointerdown sur la case ou le bouton n'atteint aucun écouteur de #stage", !m.vus.length, m.vus.join(","));
  ok("[clics] ni preventDefault : la case garde son geste natif", !e1.empeche && !e2.empeche);
  ok("[clics] la molette, le double-clic, le menu contextuel restent au panneau", !m.vus.length);
  const hors = m.stage.dispatch("pointerdown");
  ok("[clics] un pointerdown sur la scène hors panneau atteint toujours l'outil", m.vus.includes("pointerdown:autre") && !hors.arrete);
  const g = m.tete.dispatch("pointerdown", { clientX: 710, clientY: 30 });
  m.win.dispatch("pointermove", { clientX: 410, clientY: 130 });
  ok("[clics] la poignée glisse toujours (preventDefault du glisser, panneau déplacé)",
     g.empeche && m.el.style.left === "400px" && m.el.style.top === "120px" && m.el.style.right === "auto", JSON.stringify(m.el.style));
  m.win.dispatch("pointerup");
  m.win.dispatch("pointermove", { clientX: 10, clientY: 10 });
  ok("[clics] relâché : le panneau ne suit plus", m.el.style.left === "400px");
  ok("[clics] les gestes gardés", ["pointerdown", "mousedown", "dblclick", "wheel"].every((t) => GESTES_GARDES.includes(t)));
}

/* ── [page] le câblage : scripts chargés, bouton du calque, entrées de menu, aucun dialogue natif ── */
{
  const html = lit("../index.html");
  ok("[page] index.html charge /shared/dz-modeles-ia.js, dz-plafonds et dz-champ-ia",
     ["/shared/dz-modeles-ia.js", "/shared/dz-plafonds.js", "/shared/dz-champ-ia.js"].every((s) => html.includes(`src="${s}"`)));
  const img = lit("../js/mod-image.js"), lay = lit("../js/mod-layers.js"), mod = lit("../js/mod-iacalque.js");
  ok("[page] mod-image branche le panneau (import + initIaCalque) et Retirer le fond",
     /import \{ initIaCalque \} from "\.\/mod-iacalque\.js";/.test(img) && /initIaCalque\(VL\)/.test(img) && /ligneDetour/.test(img));
  ok("[page] generer() sans options ouvre le panneau sur le calque actif",
     /VL\.iaCalque\.ouvrir\(etat\.calqueActif\)/.test(img));
  ok("[page] Calques : bouton data-act=\"ia\" (glyphe dz-media-generer-image) qui ouvre le panneau sur le calque actif",
     /data-act="ia"[^\n]*dz-media-generer-image/.test(lay) && /act === "ia"[^\n]*VL\.iaCalque\.ouvrir\(c\.id\)/.test(lay));
  ok("[page] prompt marqué data-dz-ia (dz-champ-ia), aucun prompt/alert/confirm natif",
     /id="iacPrompt" data-dz-ia="image"/.test(mod) && !/(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(/.test(mod.replace(/\/\/[^\n]*/g, "")));
}

if (echecs.length) {
  console.error("ECHECS iacalque :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA iacalque : PASS (${n} controles)`);
