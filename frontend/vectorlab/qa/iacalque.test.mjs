// iacalque.test.mjs — t190 (G8) : l'image IA PAR CALQUE et « Retirer le fond » réversible. Logique PURE de
// mod-iacalque (format d'après la page, corps des routes réelles, plan du tir, cible refusée avant toute
// dépense, anti-double tir, libellé du prix serveur), le tir de bout en bout sur de FAUSSES routes, et
// l'annulation du détourage par le vrai Historique de mod-doc. Suite du 12/10 : le GUIDE (calques du dessous
// rendus, déposés, envoyés à /images/process op edit) — volet [guide], pur puis sur le vrai initIaCalque. t190-bis : le VRAI initIaCalque tourne sur un
// mini-DOM par id (le panneau, la liste des modèles illisible → « Générer » gris + Réessayer, la réouverture qui
// garde le prompt, la liste des calques qui suit le document, le focus rendu, la ligne « Retirer le fond »).
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { taillePour, requete, requeteDetour, etapes, verifierCible, calquesCibles, devisCorps, libellePrix,
         messageErreur, unSeulVol, executerPlan, retirerFondFlux, nomDepot, TAILLES, brancherPoignee, verifierDetour,
         etatGenerer, devisDetour, optionsCalques, cibleValide, chercher, nomDuDepot, initIaCalque,
         guidables, docGuide, verifierGuide, requeteGuide, nomGuide, cadreGuide, image_poser_page, GUIDE_PLANCHER }
  from "../js/mod-iacalque.js";
import { garderClics, GESTES_GARDES } from "../js/mod-flottant.js";
import { image_hrefs, image_rev_max } from "../js/mod-image.js";
import { docVierge } from "../js/mod-biblio.js";
import { Historique, op_calque_ajouter, op_calque_verrou, op_ajouter, op_image_remplacer } from "../js/mod-doc.js";

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
ok("[taille] 640×960 (2:3) → portrait_4_3 (rapport le plus proche en écart logarithmique)",
   taillePour({ w: 640, h: 960 }) === "portrait_4_3", taillePour({ w: 640, h: 960 }));
ok("[taille] 960×640 (3:2) → landscape_4_3", taillePour({ w: 960, h: 640 }) === "landscape_4_3");
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

/* ── [pose] la pose refusée n'est JAMAIS annoncée : VL.executer avale l'échec (toast + undefined) ── */
{
  const b = banc();
  b.d.poser = async (nom, calqueId) => { b.poses.push({ nom, calqueId }); return undefined; };   // comme le vrai executer
  let m = "", r = null;
  try { r = await executerPlan({ calqueId: b.c2, prompt: "x", modele: "flux-3" }, b.d); } catch (e) { m = e.message; }
  ok("[pose] executer qui avale : erreur qui dit l'image gardée en Bibliothèque (nom), rien d'annoncé",
     r === null && /Bibliothèque/.test(m) && m.includes("gen_a.png"), m);
}
{
  const b = banc();
  const post0 = b.d.post;
  b.d.post = async (url, corps) => { const r = await post0(url, corps); op_calque_verrou(b.doc, b.c3, true); return r; };
  let m = "";
  try { await executerPlan({ calqueId: b.c3, prompt: "x", modele: "flux-3" }, b.d); } catch (e) { m = e.message; }
  ok("[pose] calque verrouillé PENDANT le vol : la génération a eu lieu, le message le dit (verrou + nom gardé)",
     b.appels.length === 1 && b.poses.length === 0 && /verrouill/.test(m) && /Bibliothèque/.test(m) && m.includes("gen_a.png"), m);
}
{
  const b = banc();
  b.d.post = async (url, corps) => {
    b.appels.push({ url, corps });
    if (url === "/api/images/generate") return { images: ["gen_a.png"] };
    throw new Error("fal.ai : 502");
  };
  const r = await executerPlan({ calqueId: b.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "bria-rmbg" }, b.d);
  ok("[pose] détourage en échec APRÈS la génération payée : l'image générée est posée telle quelle, l'échec est dit",
     egal(b.poses, [{ nom: "gen_a.png", calqueId: b.c2 }]) && /502/.test(r.detourEchec || ""), JSON.stringify(r));
}

/* ── [detour-avant] le détourage incomplet est refusé AVANT la génération payée ── */
{
  const b = banc();
  let m = "";
  try { await executerPlan({ calqueId: b.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "" }, b.d); }
  catch (e) { m = e.message; }
  ok("[detour-avant] détourage coché sans modèle : refusé, AUCUN POST", !!m && b.appels.length === 0, m + " / " + b.appels.length);
  const CAT = [{ id: "sam3-sujet", prompt: true, dispo: true, cle: "FAL_KEY" }, { id: "bria-rmbg", prompt: false, dispo: false, cle: "FAL_KEY" },
               { id: "local-rembg", prompt: false, dispo: true, cle: null }];
  const info = async (id) => CAT.find((x) => x.id === id) || null;
  const b2 = banc();
  b2.d.infoDetour = info;
  let m2 = "";
  try { await executerPlan({ calqueId: b2.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "sam3-sujet", sujet: "  " }, b2.d); }
  catch (e) { m2 = e.message; }
  ok("[detour-avant] tir direct, modèle à sujet sans sujet : refusé, AUCUN POST", /sujet/.test(m2) && b2.appels.length === 0, m2 + " / " + b2.appels.length);
  const b4 = banc();
  b4.d.infoDetour = info;
  let m4 = "";
  try { await executerPlan({ calqueId: b4.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "bria-rmbg" }, b4.d); }
  catch (e) { m4 = e.message; }
  ok("[detour-avant] modèle de détourage SANS clé (dispo:false) : refusé avant tout POST, la clé est nommée",
     m4.includes("FAL_KEY") && /Retirer le fond/.test(m4) && b4.appels.length === 0, m4 + " / " + b4.appels.length);
  const b5 = banc();
  b5.d.infoDetour = info;
  await executerPlan({ calqueId: b5.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "local-rembg" }, b5.d);
  ok("[detour-avant] modèle local disponible : le tir part", b5.appels.length === 2);
  const b3 = banc();
  b3.d.infoDetour = info;
  await executerPlan({ calqueId: b3.c2, prompt: "x", modele: "flux-3", detourer: true, modeleDetour: "sam3-sujet", sujet: "le renard" }, b3.d);
  ok("[detour-avant] sujet dit : le tir part et le sujet suit", b3.appels.length === 2 && b3.appels[1].corps.sujet === "le renard");
  let m3 = "";
  try { verifierDetour({ detourer: true, modeleDetour: "bria-objet", sujet: "" }, { prompt: true, dispo: true }); } catch (e) { m3 = e.message; }
  ok("[detour-avant] verifierDetour : sujet exigé", /sujet/.test(m3));
  let m5 = "", m6 = "";
  try { verifierDetour({ detourer: true, modeleDetour: "bria-rmbg" }, { dispo: false, cle: "FAL_KEY" }); } catch (e) { m5 = e.message; }
  try { verifierDetour({ detourer: true, modeleDetour: "bria-rmbg" }, { dispo: false, cle: "FAL_KEY" }, { sansCase: true }); } catch (e) { m6 = e.message; }
  ok("[detour-avant] panneau IA : la clé manquante propose de décocher la case", /FAL_KEY/.test(m5) && /décochez/.test(m5), m5);
  ok("[detour-avant] panneau Image (pas de case) : la variante SANS « décochez »", /FAL_KEY/.test(m6) && !/décochez/.test(m6), m6);
  let rien = true;
  try { verifierDetour({ detourer: false, modeleDetour: "" }, { prompt: true, dispo: false }); } catch (e) { rien = false; }
  ok("[detour-avant] sans détourage : rien à vérifier", rien);
  ok("[prix] sans modèle choisi : aucun devis (pas de prix faux)", devisCorps({ modele: "", detourer: true, modeleDetour: "bria-rmbg" }) === null);
}

/* ── [guide] pur : les calques du DESSOUS visibles, le corps de l'op edit, le cadre et la pose, les refus gratuits ── */
const docQuatre = (fond = "#ffffff") => ({ id: "d1", taille: { w: 800, h: 600 }, ...(fond ? { fond } : {}), calques: [
  { id: "c1", nom: "Fond", visible: true, objets: [{ id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] },
  { id: "c2", nom: "Masqué", visible: false, objets: [{ id: "r2", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] },
  { id: "c3", nom: "Cible", visible: true, objets: [{ id: "r3", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] },
  { id: "c4", nom: "Dessus", visible: true, objets: [{ id: "r4", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] }] });
{
  const M = [{ id: "a", edit: true }, { id: "b", edit: false }, { id: "c" }, { id: "d", edit: true, dispo: false }];
  ok("[guide] guidables : les seuls modèles edit:true (un sans clé compris)", egal(guidables(M).map((m) => m.id), ["a", "d"]));
  const doc = docQuatre(), avantJson = JSON.stringify(doc);
  const g = docGuide(doc, "c3");
  ok("[guide] docGuide : seuls les calques visibles SOUS la cible (ni la cible, ni le masqué, ni le dessus)",
     egal(g.calques.map((c) => c.id), ["c1"]), g.calques.map((c) => c.id).join(","));
  ok("[guide] docGuide : le fond et le format de la page suivent", g.fond === "#ffffff" && egal(g.taille, { w: 800, h: 600 }));
  ok("[guide] docGuide : le document de l'écran n'est pas touché (copie)", JSON.stringify(doc) === avantJson && g !== doc && g.calques[0] !== doc.calques[0]);
  ok("[guide] docGuide sous le dessus : le dessous visible ET la cible d'avant, jamais le masqué",
     egal(docGuide(doc, "c4").calques.map((c) => c.id), ["c1", "c3"]));
  let m1 = "";
  try { docGuide(doc, "c1"); } catch (e) { m1 = e.message; }
  ok("[guide] calque du bas : rien dessous, refus lisible", /rien n'est visible sous « Fond »/.test(m1), m1);
  const refus = (f) => { try { f(); return ""; } catch (e) { return e.message; } };
  const d2 = docQuatre(); d2.calques[0].visible = false;
  ok("[guide] le seul dessous est masqué : refus (le fond de page seul n'est pas un guide)", /rien n'est visible/.test(refus(() => docGuide(d2, "c3"))));
  const d3 = docQuatre(); d3.calques[0].opacite = 0;
  ok("[guide] dessous à opacité nulle : refus", /rien n'est visible/.test(refus(() => docGuide(d3, "c3"))));
  const d4 = docQuatre(); d4.calques[0].objets = [];
  ok("[guide] dessous vide : refus", /rien n'est visible/.test(refus(() => docGuide(d4, "c3"))));
  const d5 = docQuatre(); d5.calques[0].objets = [{ id: "g1", type: "groupe", style: {}, enfants: [{ id: "g2", type: "groupe", style: {}, enfants: [] }] }];
  ok("[guide] dessous qui ne porte que des groupes VIDES : rien de dessinable, refus", /rien n'est visible/.test(refus(() => docGuide(d5, "c3"))));
  d5.calques[0].objets[0].enfants[0].enfants.push({ id: "r9", type: "rect", x: 0, y: 0, w: 5, h: 5, style: {} });
  ok("[guide] un groupe qui contient (en profondeur) un dessinable : le calque compte", egal(docGuide(d5, "c3").calques.map((c) => c.id), ["c1"]));
  ok("[guide] verifierGuide : un modèle qui ne sait pas partir d'une image est refusé, nommé",
     /« b » ne sait pas/.test(refus(() => verifierGuide({ guide: true, modele: "b" }, M))));
  ok("[guide] verifierGuide : sans modèle, refus", /choisissez un modèle/.test(refus(() => verifierGuide({ guide: true, modele: "" }, M))));
  ok("[guide] verifierGuide : case décochée, rien à vérifier", !refus(() => verifierGuide({ guide: false, modele: "b" }, M)));
  ok("[guide] verifierGuide : un modèle edit SANS clé passe (le 503 viendra du serveur)", !refus(() => verifierGuide({ guide: true, modele: "d" }, M)));
  const q = requeteGuide({ prompt: " un renard ", modele: "flux-3", taille: "landscape_4_3", filename: "vector_d1_guide_c3_x.png" });
  ok("[guide] requeteGuide : le corps de /images/process op edit",
     egal(q, { op: "edit", filename: "vector_d1_guide_c3_x.png", prompt: "un renard", model: "flux-3", n: 1, size: "landscape_4_3", source: "vectorlab" }), JSON.stringify(q));
  const m8 = refus(() => requeteGuide({ prompt: "x", modele: "flux-3" }));
  ok("[guide] requeteGuide sans guide déposé : refus lisible", /guide/.test(m8) && !/^vectorlab\./.test(m8), m8);
  const n1 = nomGuide("doc 1", "c3", 1000), n2 = nomGuide("doc 1", "c3", 2000);
  ok("[guide] nomGuide : préfixe vector_ (provenance vectorlab) et UNIQUE (un vector_ est réécrit en place)",
     /^vector_doc-1_guide_c3_[0-9a-z]+\.png$/.test(n1) && n1 !== n2, n1 + " " + n2);
  // I1 : le guide au rapport du FORMAT demandé, la page centrée ; la pose ramène ce cadre sur la page
  const c169 = cadreGuide({ w: 1920, h: 1080 }, "landscape_16_9");
  ok("[cadre] page 1920×1080, landscape_16_9 : canevas 1536×864, la page le remplit", egal(c169, { W: 1536, H: 864, k: 0.8, ox: 0, oy: 0 }), JSON.stringify(c169));
  const p169 = image_poser_page({ w: 1376, h: 768 }, { w: 1920, h: 1080 }, c169);
  ok("[pose] page 1920×1080, résultat 1376×768 : la page est couverte (w === 1920, x === 0), jamais 1376 au milieu",
     p169.w === 1920 && p169.x === 0 && p169.h === 1080 && p169.y === 0, JSON.stringify(p169));
  const c23 = cadreGuide({ w: 640, h: 960 }, "portrait_4_3");
  ok("[cadre] page 2:3 en portrait_4_3 : canevas 1152×1536, page centrée (bandes de 64 px)", c23.W === 1152 && c23.H === 1536 && c23.ox === 64 && c23.oy === 0, JSON.stringify(c23));
  const p23 = image_poser_page({ w: 768, h: 1024 }, { w: 640, h: 960 }, c23);
  ok("[pose] page 2:3 + résultat 3:4 : la page couverte EXACTEMENT, les bandes débordent hors page",
     p23.y === 0 && p23.h === 960 && p23.x === -40 && p23.w === 720 && p23.x + p23.w - 640 === 40, JSON.stringify(p23));
  const c43 = cadreGuide({ w: 800, h: 600 }, "landscape_4_3");
  ok("[pose] la pose ne dépend pas de la taille native rendue (le cadre entier = le résultat entier)",
     egal(image_poser_page({ w: 1024, h: 768 }, { w: 800, h: 600 }, c43), image_poser_page({ w: 1184, h: 896 }, { w: 800, h: 600 }, c43)));
  const mb = refus(() => cadreGuide({ w: 10000, h: 100 }, "landscape_16_9"));
  ok("[cadre] bannière 10000×100 : refus NOMMÉ (le dessous y tiendrait sur ~15 px), jamais un guide de quelques pixels",
     /10000×100 est trop allongée/.test(mb) && new RegExp(`${Math.round(100 * 0.1536)} px`).test(mb), mb);
  ok("[cadre] le plancher est 64 px", GUIDE_PLANCHER === 64 && !refus(() => cadreGuide({ w: 1536, h: 64 }, "landscape_16_9")));
  ok("[guide] devis du tir guidé : kind « image » + le modèle (celui de la garde de l'op edit : banc test_vectorlab_guide_devis), détourage en plus",
     egal(devisCorps({ modele: "flux-3", guide: true, detourer: true, modeleDetour: "bria-rmbg" }),
          { kind: "campaign", ops: [{ kind: "image", model: "flux-3", n: 1 }, { kind: "detourage", modele: "bria-rmbg", images: 1 }] }));
  const eg = etatGenerer({ enVol: false, cible: "c3", catalogue: "ok", modele: "", guide: true, nbModeles: 3 });
  ok("[guide] etatGenerer : case cochée, liste non vide sans modèle qui guide → gris, raison « guide »", eg.gris && eg.raison === "guide", JSON.stringify(eg));
  const ev = etatGenerer({ enVol: false, cible: "c3", catalogue: "ok", modele: "", guide: true, nbModeles: 0 });
  ok("[guide] etatGenerer : liste entièrement VIDE, case cochée → raison « vide » (décocher n'y changerait rien)", ev.gris && ev.raison === "vide", JSON.stringify(ev));
  // l'export inline aussi les images des SYMBOLES (mod-image, saisie L6)
  const ds = { calques: [{ id: "c1", objets: [{ id: "i1", type: "image", href: "a.png", rev: 1 }] }],
               symboles: { s1: { nom: "S", objets: [{ id: "g", type: "groupe", enfants: [{ id: "i2", type: "image", href: "b.png", rev: 4 }] }] } } };
  ok("[symboles] image_hrefs visite les objets des symboles (groupes compris)", egal(image_hrefs(ds), ["a.png", "b.png"]), JSON.stringify(image_hrefs(ds)));
  ok("[symboles] image_rev_max aussi (la révision d'une image de symbole n'est pas perdue)", image_rev_max(ds, "b.png") === 4);
}
{
  // le tir guidé de bout en bout sur de fausses routes : guide déposé, PUIS l'op edit, jamais /images/generate
  let doc = docQuatre();
  const appels = [], poses = [], guides = [];
  const MODS = [{ id: "flux-3", edit: true }, { id: "texte-seul", edit: false }];
  const d = {
    doc: () => doc,
    modelesImage: async () => MODS,
    guide: async (docG, calqueId, cadre) => { guides.push({ ids: docG.calques.map((c) => c.id), calqueId, cadre }); appels.push({ url: "depot" }); return "vector_d1_guide_c3_k.png"; },
    post: async (url, corps) => { appels.push({ url, corps }); return url === "/api/images/process" && corps.op === "edit" ? { images: ["gen_g.png"] } : { images: ["gen_det.png"] }; },
    poser: async (nom, calqueId, placer) => { poses.push({ nom, calqueId, spec: placer ? placer({ w: 1184, h: 896 }, doc.taille) : null }); return "o5"; },
  };
  const r = await executerPlan({ calqueId: "c3", prompt: "un renard", modele: "flux-3", taille: "landscape_4_3", guide: true,
                                 detourer: true, modeleDetour: "bria-rmbg" }, d);
  ok("[guide] tir : dépôt du guide, op edit, puis détourage — jamais /images/generate",
     egal(appels.map((a) => a.url), ["depot", "/api/images/process", "/api/images/process"]) && appels[1].corps.op === "edit" && appels[2].corps.op === "remove-bg",
     JSON.stringify(appels.map((a) => a.url + (a.corps ? ":" + a.corps.op : ""))));
  ok("[guide] tir : le guide rendu = les seuls calques du dessous visibles, au cadre du format demandé",
     egal(guides.map((x) => [x.ids, x.calqueId]), [[["c1"], "c3"]]) && egal(guides[0].cadre, cadreGuide({ w: 800, h: 600 }, "landscape_4_3")), JSON.stringify(guides));
  ok("[guide] tir : l'op edit part du guide déposé, avec le modèle et le prompt",
     appels[1].corps.filename === "vector_d1_guide_c3_k.png" && appels[1].corps.model === "flux-3" && appels[1].corps.prompt === "un renard", JSON.stringify(appels[1].corps));
  ok("[guide] tir : le détourage porte sur l'image GUIDÉE, posée sur la cible, couvrant la page (image_poser_page)",
     appels[2].corps.filename === "gen_g.png" && egal(poses, [{ nom: "gen_det.png", calqueId: "c3", spec: { x: 0, y: 0, w: 800, h: 600 } }]), JSON.stringify(poses));
  ok("[guide] tir : le résultat nomme son guide", r.guide === "vector_d1_guide_c3_k.png" && r.id === "o5", JSON.stringify(r));
  appels.length = 0; guides.length = 0; poses.length = 0;
  let mr = "";
  try { await executerPlan({ calqueId: "c1", prompt: "x", modele: "flux-3", guide: true }, d); } catch (e) { mr = e.message; }
  ok("[guide] rien sous le calque : refus, AUCUN envoi (ni dépôt ni POST)", /rien n'est visible/.test(mr) && !appels.length && !guides.length, mr + " / " + appels.length);
  let mm = "";
  try { await executerPlan({ calqueId: "c3", prompt: "x", modele: "texte-seul", guide: true }, d); } catch (e) { mm = e.message; }
  ok("[guide] modèle qui ne guide pas : refus, AUCUN envoi", /ne sait pas partir/.test(mm) && !appels.length, mm + " / " + appels.length);
  const d0 = { ...d, modelesImage: async () => [{ id: "texte-seul", edit: false }] };
  let m0 = "";
  try { await executerPlan({ calqueId: "c3", prompt: "x", modele: "texte-seul", guide: true }, d0); } catch (e) { m0 = e.message; }
  ok("[guide] aucun modèle qui guide : refus, AUCUN envoi", !!m0 && !appels.length, m0);
  const ban = { ...docQuatre(), taille: { w: 10000, h: 100 } };
  let mb = "";
  try { await executerPlan({ calqueId: "c3", prompt: "x", modele: "flux-3", guide: true, taille: "landscape_16_9" }, { ...d, doc: () => ban }); } catch (e) { mb = e.message; }
  ok("[guide] bannière : refus nommé, AUCUN envoi", /trop allongée/.test(mb) && !appels.length, mb);
  // le document FIGÉ au clic : ce qui change pendant la lecture du catalogue n'entre pas dans le guide
  const d8 = { ...d, modelesImage: async () => { doc = docQuatre(); doc.calques[0].visible = false; doc.calques[2].visible = false; return MODS; } };
  doc = docQuatre();
  await executerPlan({ calqueId: "c4", prompt: "x", modele: "flux-3", guide: true, taille: "landscape_4_3" }, d8);
  ok("[guide] guide figé avant le premier await : les calques masqués PENDANT le vol y restent", egal(guides.map((x) => x.ids), [["c1", "c3"]]), JSON.stringify(guides.map((x) => x.ids)));
  doc = docQuatre(); appels.length = 0; guides.length = 0;
  // un échec du tir APRÈS le dépôt du guide : le guide gardé est nommé (pas de suppression d'office)
  for (const [statut, err] of [["503", "Clé absente — FAL_KEY non configurée"], ["402", "plafond atteint"], ["502", "fal.ai : 502"]]) {
    const dx = { ...d, post: async (url, corps) => { appels.push({ url, corps }); throw new Error(err); } };
    let me = "";
    try { await executerPlan({ calqueId: "c3", prompt: "x", modele: "flux-3", guide: true, taille: "landscape_4_3" }, dx); } catch (e) { me = e.message; }
    ok(`[guide] échec ${statut} après le dépôt : le message garde la raison ET nomme le guide gardé en Bibliothèque`,
       me.includes(err) && /guide gardé en Bibliothèque : vector_d1_guide_c3_k\.png/.test(me), me);
  }
  const dv = { ...d, post: async () => ({ images: [] }) };
  let mv = "";
  try { await executerPlan({ calqueId: "c3", prompt: "x", modele: "flux-3", guide: true, taille: "landscape_4_3" }, dv); } catch (e) { mv = e.message; }
  ok("[guide] édition sans image rendue : le guide gardé est nommé aussi", /aucune image/.test(mv) && /guide gardé/.test(mv), mv);
  appels.length = 0; guides.length = 0;
  await executerPlan({ calqueId: "c3", prompt: "x", modele: "texte-seul", guide: false }, d);
  ok("[guide] case décochée : le chemin d'avant (/images/generate seul, aucun guide, pose ordinaire)",
     egal(appels.map((a) => a.url), ["/api/images/generate"]) && !guides.length && poses.at(-1).spec === null, JSON.stringify(appels.map((a) => a.url)));
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
  const vu = [];
  const g = unSeulVol(async () => { throw new Error("x"); }, () => vu.push(g.enVol));
  try { await g(); } catch (e) { /* attendu */ }
  ok("[vol] libéré après un échec", g.enVol === false);
  ok("[vol] rappel APRÈS le vol (le bouton « en cours… » est redessiné, libre)", egal(vu, [false]), JSON.stringify(vu));
  const vu2 = [];
  const h = unSeulVol(async () => "ok", () => vu2.push(h.enVol));
  await h();
  ok("[vol] rappel aussi après un succès", egal(vu2, [false]));
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
  // t190-bis : la mention partielle NOMME la ligne à mesurer d'après le devis (unité « image » = l'image)
  const LU = (prov, usd, unit) => ({ provider: prov, usd, unit });
  const pi = libellePrix({ breakdown: [LU("openai", 0, "image"), LU("fal", 0.018, "img")], total_usd: 0.018 });
  ok("[prix] image à mesurer, détourage chiffré : « + image à mesurer »", /image à mesurer/.test(pi) && !/détourage à mesurer/.test(pi), pi);
  const pd = libellePrix({ breakdown: [LU("fal", 0.048, "image"), LU("fal", 0, "img")], total_usd: 0.048 });
  ok("[prix] détourage à mesurer, image chiffrée : « + détourage à mesurer »", /détourage à mesurer/.test(pd) && !/image à mesurer/.test(pd), pd);
  ok("[prix] détourage LOCAL seul (0 $) : gratuit, jamais « à mesurer »",
     /gratuit/.test(libellePrix({ breakdown: [LU("local", 0, "img")], total_usd: 0 })));
  ok("[prix] le devis du seul détourage (panneau Image)",
     egal(devisDetour("bria-rmbg"), { kind: "campaign", ops: [{ kind: "detourage", modele: "bria-rmbg", images: 1 }] }) && devisDetour("") === null);
}

/* ── [generer] « Générer » gris sans liste des modèles, JAMAIS pour une clé manquante ── */
{
  const base = { enVol: false, cible: "c1", catalogue: "ok", modele: "flux-3" };
  ok("[generer] liste lue, modèle choisi : actif", etatGenerer(base).gris === false);
  const e = etatGenerer({ ...base, catalogue: "echec", modele: "" });
  ok("[generer] liste illisible : gris, raison « catalogue » (message + Réessayer)", e.gris && e.raison === "catalogue", JSON.stringify(e));
  ok("[generer] liste lue mais VIDE (aucun modèle) : gris, raison « vide » (pas « Réessayer »)",
     etatGenerer({ ...base, modele: "" }).gris && etatGenerer({ ...base, modele: "" }).raison === "vide");
  ok("[generer] liste en lecture : gris, sans message", etatGenerer({ ...base, catalogue: "chargement", modele: "" }).gris
     && etatGenerer({ ...base, catalogue: "chargement", modele: "" }).raison === "");
  ok("[generer] aucun calque libre : gris, raison « calque »", etatGenerer({ ...base, cible: "" }).raison === "calque");
  ok("[generer] en vol : gris", etatGenerer({ ...base, enVol: true }).gris);
  ok("[generer] la clé n'entre pas en compte (l'état ne la reçoit même pas)", etatGenerer({ ...base, dispo: false, cle: "FAL_KEY" }).gris === false);
}

/* ── [calques] la liste des calques : masqués dits, cible gardée tant qu'elle est libre ── */
{
  const doc = { calques: [{ id: "c1", nom: "Fond" }, { id: "c2", nom: "Logo", visible: false }, { id: "c3", nom: "Verrou", verrou: true }] };
  const html = optionsCalques(doc, "c2");
  ok("[calques] un calque masqué le dit dans son option", /<option value="c2" selected>Logo \(masqué\)<\/option>/.test(html), html);
  ok("[calques] un calque verrouillé n'est pas proposé", !/c3/.test(html));
  ok("[calques] le dessus en tête", html.indexOf("c2") < html.indexOf("c1"));
  ok("[calques] cible gardée si libre, sinon la demandée, sinon la première libre",
     cibleValide(doc, "c1", "c2") === "c1" && cibleValide(doc, "c3", "c1") === "c1" && cibleValide(doc, "zz", "") === "c2"
     && cibleValide({ calques: [{ id: "x", verrou: true }] }, "x", "") === "");
}

/* ── [reseau] « Failed to fetch » traduit ; dépôt sans nom refusé lisiblement ── */
{
  let m = "";
  try { await chercher("/api/x", {}, async () => { throw new TypeError("Failed to fetch"); }); } catch (e) { m = e.message; }
  ok("[reseau] erreur réseau : message lisible, plus « Failed to fetch »", /injoignable/.test(m) && !/Failed/.test(m), m);
  const r = await chercher("/api/x", {}, async (u) => ({ ok: true, u }));
  ok("[reseau] réponse rendue telle quelle", r.ok && r.u === "/api/x");
  let m2 = "";
  try { nomDuDepot({}); } catch (e) { m2 = e.message; }
  ok("[reseau] dépôt en Bibliothèque sans nom : erreur lisible (jamais filename undefined)", /Bibliothèque/.test(m2), m2);
  ok("[reseau] dépôt avec nom : le nom", nomDuDepot({ filename: "vector_a.png" }) === "vector_a.png");
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
    doc: () => doc,
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
  const ex2 = (fn, ...a) => { const essai = JSON.parse(JSON.stringify(doc)); const out = fn(essai, ...a); h2.capturer(doc); doc = essai; return out; };
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
    await retirerFondFlux(doc.calques[0].objets[0], { modele: "bria-rmbg" }, { doc: () => doc,
      versBiblio: async () => "a.png", post: async () => ({ images: ["b.png"] }),
      deposer: async () => ({ href: "img1.png", nat: { w: 800, h: 400 } }), executer: () => { execs++; } });
  } catch (e) { m = e.message; }
  ok("[annuler] même href refusé (l'image d'avant serait perdue)", !!m && execs === 0, m);
  // l'executer réel AVALE l'échec de la commande (toast + undefined) : jamais « fond retiré »
  let m4 = "";
  try {
    await retirerFondFlux(doc.calques[0].objets[0], { modele: "bria-rmbg" }, { doc: () => doc,
      versBiblio: async () => "a.png", post: async () => ({ images: ["gen_det.png"] }),
      deposer: async () => ({ href: "img9.png", nat: { w: 800, h: 400 } }), executer: () => undefined });
  } catch (e) { m4 = e.message; }
  ok("[annuler] remplacement avalé par executer : erreur qui dit l'image détourée gardée (nom)",
     /Bibliothèque/.test(m4) && m4.includes("gen_det.png"), m4);
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
{
  // t190-bis : une image ENFANT d'un groupe (Ctrl+clic la sélectionne, le panneau Image lui offre « Retirer le
  // fond ») — la commande la retrouve, le remplacement et l'annulation marchent
  const docGroupe = () => {
    const dg = docVierge("t", 400, 300);
    dg.calques[0].objets.push({ id: "g1", type: "groupe", style: {}, enfants: [
      { id: "i5", type: "image", x: 0, y: 0, w: 100, h: 100, href: "img5.png", nat: { w: 100, h: 100 }, rev: 2, style: {} },
      { id: "r1", type: "rect", x: 0, y: 0, w: 10, h: 10, style: {} }] });
    return dg;
  };
  let doc = docGroupe();
  const h = new Historique();
  const executer = (fn, ...a) => { const essai = JSON.parse(JSON.stringify(doc)); const out = fn(essai, ...a); h.capturer(doc); doc = essai; return out; };
  const img = () => doc.calques[0].objets.find((x) => x.id === "g1").enfants[0];
  let href = "", mg = "";
  try {
  href = await retirerFondFlux(img(), { modele: "bria-rmbg" }, { doc: () => doc, versBiblio: async () => "a.png",
    post: async () => ({ images: ["det5.png"] }), deposer: async () => ({ href: "img6.png", nat: { w: 100, h: 100 } }), executer });
  } catch (e) { mg = e.message; }
  ok("[groupe] image dans un groupe : le fond retiré la remplace (" + mg + ")", href === "img6.png" && img().href === "img6.png" && !("rev" in img()), JSON.stringify(img()));
  if (h.peutAnnuler()) doc = h.annuler(doc);
  ok("[groupe] Annuler rend l'image d'avant dans le groupe", img().href === "img5.png" && img().rev === 2, JSON.stringify(img()));
  let m = "";
  try { op_image_remplacer(docGroupe(), "r1", "x.png", { w: 1, h: 1 }); } catch (e) { m = e.message; }
  ok("[groupe] un enfant de groupe qui n'est pas une image : même refus « pas une image »", !!m && !/introuvable/.test(m), m);
  // aucun POST si la commande ne pourrait pas aboutir (image disparue du document) : rien de payé pour rien
  const posts = [];
  let m2 = "";
  try {
    await retirerFondFlux({ id: "fantome", type: "image", href: "z.png" }, { modele: "bria-rmbg" }, { doc: () => docGroupe(),
      versBiblio: async () => { posts.push("upload"); return "a.png"; }, post: async (u) => { posts.push(u); return { images: ["x.png"] }; },
      deposer: async () => ({ href: "q.png", nat: { w: 1, h: 1 } }), executer: () => true });
  } catch (e) { m2 = e.message; }
  ok("[groupe] image introuvable par la commande : refus AVANT tout POST (ni upload, ni /images/process)", !!m2 && !posts.length, m2 + " " + posts.join(","));
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
  const m1 = monter();
  const e1 = m1.caseDetour.dispatch("pointerdown", { clientX: 750, clientY: 200 });
  ok("[clics] un pointerdown sur la case n'atteint aucun écouteur de #stage", !m1.vus.length, m1.vus.join(","));
  const m2 = monter();
  const e2 = m2.go.dispatch("pointerdown", { clientX: 760, clientY: 300 });
  ok("[clics] un pointerdown sur le bouton n'atteint aucun écouteur de #stage", !m2.vus.length, m2.vus.join(","));
  ok("[clics] ni preventDefault : la case garde son geste natif", !e1.empeche && !e2.empeche);
  for (const t of ["mousedown", "dblclick", "wheel", "contextmenu"]) {
    const mt = monter();
    mt.caseDetour.dispatch(t);
    ok(`[clics] ${t} reste au panneau`, !mt.vus.length, mt.vus.join(","));
  }
  {
    // le CLAVIER : le keydown global de core.js (document) ne doit pas voir Échap / une lettre tapés sur une liste
    const mk = monter();
    const doc = new Noeud(null), vusK = [];
    mk.stage.parent = doc;
    doc.addEventListener("keydown", (ev) => vusK.push(ev.key));
    const k1 = mk.caseDetour.dispatch("keydown", { key: "Escape" });
    mk.go.dispatch("keydown", { key: "v" });
    ok("[clavier] Échap et une lettre sur un contrôle du panneau n'atteignent pas le raccourci global", !vusK.length, vusK.join(","));
    ok("[clavier] sans preventDefault (la liste garde ses flèches et sa frappe)", !k1.empeche);
  }
  const m = monter();
  const hors = m.stage.dispatch("pointerdown");
  ok("[clics] un pointerdown sur la scène hors panneau atteint toujours l'outil", m.vus.includes("pointerdown:autre") && !hors.arrete);
  const g = m.tete.dispatch("pointerdown", { clientX: 710, clientY: 30 });
  m.win.dispatch("pointermove", { clientX: 410, clientY: 130 });
  ok("[clics] la poignée glisse toujours (preventDefault du glisser, panneau déplacé)",
     g.empeche && m.el.style.left === "400px" && m.el.style.top === "120px" && m.el.style.right === "auto", JSON.stringify(m.el.style));
  m.win.dispatch("pointerup");
  m.win.dispatch("pointermove", { clientX: 10, clientY: 10 });
  ok("[clics] relâché : le panneau ne suit plus", m.el.style.left === "400px");
  ok("[clics] les gestes gardés", ["pointerdown", "mousedown", "dblclick", "wheel", "keydown"].every((t) => GESTES_GARDES.includes(t)));
}

/* ── [page] le câblage hors du module (index.html, mod-image, mod-layers : lus, non importables ici) ── */
{
  const html = lit("../index.html");
  ok("[page] index.html charge /shared/dz-modeles-ia.js, dz-plafonds et dz-champ-ia",
     ["/shared/dz-modeles-ia.js", "/shared/dz-plafonds.js", "/shared/dz-champ-ia.js"].every((s) => html.includes(`src="${s}"`)));
  const img = lit("../js/mod-image.js"), lay = lit("../js/mod-layers.js"), mod = lit("../js/mod-iacalque.js");
  ok("[page] mod-image branche le panneau (import + initIaCalque) et Retirer le fond",
     /import \{ initIaCalque, chercher \} from "\.\/mod-iacalque\.js";/.test(img) && /initIaCalque\(VL\)/.test(img) && /ligneDetour/.test(img));
  ok("[page] generer() ouvre le panneau sur le calque actif — plus de voie generer(opts) (aucun appelant)",
     /async function generer\(\) \{\s*VL\.iaCalque\.ouvrir\(etat\.calqueActif\);\s*\}/.test(img) && !/iaCalque\.lancer/.test(img));
  ok("[page] poserDepuisLibrary : une pose avalée par executer lève une erreur, jamais « posée »",
     /if \(!id\) throw new Error\(T\("vectorlab\.image\.pose_impossible"/.test(img));
  ok("[page] Calques : bouton data-act=\"ia\" (glyphe dz-media-generer-image) qui ouvre le panneau sur le calque actif",
     /data-act="ia"[^\n]*dz-media-generer-image/.test(lay) && /act === "ia" && c\) VL\.iaCalque\.ouvrir\(c\.id\);/.test(lay));
  ok("[page] aucun prompt/alert/confirm natif dans le module",
     !/(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(/.test(mod.replace(/\/\/[^\n]*/g, "")));
}

/* ── [panneau] le VRAI initIaCalque sur un mini-DOM par id : chaque gabarit innerHTML crée les éléments qu'il
   nomme (id, attributs, <option> d'un <select>), $ les retrouve par id ; un rendu neuf déconnecte les anciens ── */
{
  const reg = new Map();
  let actif = null;
  class El {
    constructor(tag, attrs = {}) {
      this.tagName = String(tag).toUpperCase(); this.attrs = { ...attrs }; this.id = attrs.id || "";
      this.dataset = {}; for (const [k, v] of Object.entries(attrs)) if (k.startsWith("data-")) this.dataset[k.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase())] = v;
      this.hidden = "hidden" in attrs; this.disabled = "disabled" in attrs; this.checked = false;
      this.value = attrs.value || ""; this.textContent = ""; this.ec = []; this.style = {}; this.isConnected = true;
      this.parent = null; this.enfants = []; this._html = "";
    }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
    addEventListener(t, fn) { this.ec.push({ t, fn }); }
    removeEventListener(t, fn) { this.ec = this.ec.filter((e) => !(e.t === t && e.fn === fn)); }
    appendChild(e) { e.parent = this; if (e.id) reg.set(e.id, e); return e; }
    focus() { actif = this; }
    getBoundingClientRect() { return { left: 0, top: 0, width: 300, height: 400 }; }
    closest(sel) {
      for (let x = this; x; x = x.parent) {
        if (sel === "button" && x.tagName === "BUTTON") return x;
        if (sel === "[data-poigne]" && "poigne" in x.dataset) return x;
      }
      return null;
    }
    querySelector(sel) { const e = reg.get(sel.replace(/^#/, "")); return e && e.isConnected ? e : null; }
    get innerHTML() { return this._html; }
    set innerHTML(h) {
      this.ecritures = (this.ecritures || 0) + 1;
      this._html = h;
      for (const e of this.enfants) e.isConnected = false;
      this.enfants = [];
      if (this.tagName === "SELECT") { this.options(h); return; }
      // chaque balise à id devient un élément enregistré ; ses parents d'id les plus proches sont suivis
      const pile = [this];
      for (const m of h.matchAll(/<(\/?)([a-z]+)([^>]*?)(\/?)>/gi)) {
        const [, ferme, tag, reste, auto] = m;
        if (ferme) { if (pile.length > 1 && pile[pile.length - 1].tagName === tag.toUpperCase()) pile.pop(); continue; }
        const attrs = {};
        for (const a of reste.matchAll(/([\w-]+)(?:="([^"]*)")?/g)) attrs[a[1]] = a[2] === undefined ? "" : a[2];
        const e = new El(tag, attrs);
        e.parent = pile[pile.length - 1];
        this.enfants.push(e);
        if (e.id) reg.set(e.id, e);
        if (!auto && !/^(input|br|img)$/i.test(tag)) pile.push(e);
      }
      for (const e of this.enfants) if (e.tagName === "SELECT") {
        const i = h.indexOf(`id="${e.id}"`), j = h.indexOf("</select>", i);
        e.options(h.slice(h.indexOf(">", i) + 1, j));
      }
    }
    options(h) {
      this._html = h;
      const opts = [...h.matchAll(/<option value="([^"]*)"( selected)?>([^<]*)<\/option>/g)];
      this.valeurs = opts.map((o) => o[1]);
      this.value = (opts.find((o) => o[2]) || opts[0] || [, ""])[1];
    }
    // un geste qui remonte du nœud au panneau (les écouteurs du panneau sont posés sur lui)
    tirer(t, extra = {}) {
      const ev = { type: t, target: this, key: "", ctrlKey: false, metaKey: false, ...extra, defaultPrevented: false,
        stopPropagation() {}, preventDefault() { this.defaultPrevented = true; } };
      for (let x = this; x; x = x.parent) for (const e of x.ec.filter((y) => y.t === t)) e.fn(ev);
      return ev;
    }
  }
  const attendre = async (k = 6) => { for (let i = 0; i < k; i++) await new Promise((r) => setTimeout(r, 0)); };

  // le faux DzModelesIA : une promesse par nature, réglable ; remplir choisit le modèle mémorisé, sinon le premier
  const modeles = { image: null, detourage_image: null };
  const DzModelesIA = {
    charger: (nature) => modeles[nature] ? Promise.resolve(modeles[nature]) : Promise.reject(new Error("catalogue")),
    filtrer: (l) => l,
    remplir: (sel, l, o) => { sel.valeurs = l.map((m) => m.id); sel.value = (l.find((m) => m.id === (o && o.valeur)) || l[0] || { id: "" }).id; return sel.value; },
    prixUsd: (v) => (+v > 0 ? "$" + (Math.round(v * 1000) / 1000).toFixed(3).replace(/0$/, "") : ""),
  };
  const appels = [];
  const fetchFaux = async (url, init) => {
    const corps = init && init.body && typeof init.body === "string" ? JSON.parse(init.body) : null;
    appels.push({ url, corps });
    if (url === "/api/cost/estimate") {
      const lignes = corps.ops.map((o) => o.kind === "image" ? { provider: "fal", usd: 0.048, unit: "image" } : { provider: "fal", usd: 0.018, unit: "img" });
      return { ok: true, status: 200, json: async () => ({ breakdown: lignes, total_usd: lignes.reduce((t, l) => t + l.usd, 0) }) };
    }
    return { ok: false, status: 500, statusText: "x", json: async () => ({}) };
  };
  const avant = { document: globalThis.document, window: globalThis.window, localStorage: globalThis.localStorage };
  const stage = new El("main", { id: "stage" }); reg.set("stage", stage);
  const corps = new El("body");
  globalThis.document = { createElement: (t) => new El(t), get activeElement() { return actif || corps; }, body: corps, querySelector: () => null };
  globalThis.window = { fetch: fetchFaux, DzModelesIA, addEventListener() {}, removeEventListener() {} };
  globalThis.localStorage = { getItem: () => null, setItem: () => {} };
  const toasts = [];
  const doc = { taille: { w: 800, h: 600 }, calques: [{ id: "c1", nom: "Fond", objets: [] }, { id: "c2", nom: "Logo", objets: [] }] };
  const VL = { etat: { doc, calqueActif: "c1", selection: [] }, $: (s) => { const e = reg.get(s.replace(/^#/, "")); return e && e.isConnected ? e : null; },
    toast: (m, err) => toasts.push((err ? "!" : "") + m), surRendu: () => {}, surHistorique: () => {}, executer: () => true };
  try {
    initIaCalque(VL);
    ok("[panneau] VL.iaCalque n'expose que ce qu'on appelle (ouvrir, fermer, ligneDetour)",
       egal(Object.keys(VL.iaCalque).sort(), ["fermer", "ligneDetour", "ouvrir"]), Object.keys(VL.iaCalque).join(","));

    // ouverture depuis un bouton : le focus y reviendra
    const boutonCalque = new El("button"); boutonCalque.focus();
    VL.iaCalque.ouvrir("c2");
    await attendre();
    const dlg = reg.get("iaCalqueDlg");
    ok("[panneau] un dialogue nommé, posé dans #stage, marqué panneau flottant",
       dlg && dlg.parent === stage && dlg.attrs.role === "dialog" && dlg.attrs["aria-labelledby"] === "iacTitre" && reg.get("iacTitre")
       && dlg.dataset.vlFlottant === "1" && /\bia-dlg\b/.test(dlg.className) && /\biac-dlg\b/.test(dlg.className), dlg && dlg.className);
    ok("[panneau] le prompt est marqué data-dz-ia (dz-champ-ia) et reçoit le focus",
       reg.get("iacPrompt").dataset.dzIa === "image" && actif === reg.get("iacPrompt"));
    ok("[panneau] présélection : le calque d'où l'on vient", reg.get("iacCalque").value === "c2");

    // [mineur 1] la liste des modèles illisible : « Générer » gris, la raison et Réessayer
    const go = reg.get("iacGo");
    ok("[catalogue] liste illisible : « Générer » GRIS (le serveur ne tirera pas le défaut sans prix)", go.disabled === true);
    ok("[catalogue] la raison est écrite et « Réessayer » paraît",
       /liste des modèles indisponible/.test(reg.get("iacEtat").textContent) && reg.get("iacReessayer").hidden === false, reg.get("iacEtat").textContent);
    ok("[catalogue] aucun devis demandé sans modèle (pas de prix faux)", !appels.some((a) => a.url === "/api/cost/estimate"));
    // la liste revient — avec un modèle SANS clé : choisissable, et « Générer » s'allume quand même
    modeles.image = [{ id: "flux-3", dispo: false, cle: "FAL_KEY", usd: 0.048, unite: "image", edit: true },
                     { id: "texte-seul", label: "Texte seul", dispo: true, usd: 0.003, unite: "image", edit: false },
                     { id: "gpt-image-2", label: "GPT Image 2", dispo: false, cle: "OPENAI_API_KEY", usd: 0.12, unite: "image", edit: true }];
    reg.get("iacReessayer").tirer("click");
    await attendre();
    ok("[catalogue] Réessayer relit la liste : modèle choisi, « Générer » ACTIF même sans clé", reg.get("iacModele").value === "flux-3" && go.disabled === false);
    ok("[catalogue] la raison s'efface, Réessayer se cache",
       reg.get("iacEtat").textContent === "" && reg.get("iacReessayer").hidden === true, reg.get("iacEtat").textContent);
    ok("[catalogue] le devis serveur est demandé et affiché", appels.some((a) => a.url === "/api/cost/estimate") && /\$0\.048/.test(reg.get("iacPrix").textContent), reg.get("iacPrix").textContent);

    // [mineur 6] rouvrir le panneau déjà ouvert : le prompt reste, seule la liste des calques change
    const prompt = reg.get("iacPrompt");
    prompt.value = "un renard en vitrail";
    VL.iaCalque.ouvrir("c1");
    await attendre();
    ok("[rouvrir] le prompt tapé reste (même champ, même texte)", reg.get("iacPrompt") === prompt && prompt.value === "un renard en vitrail" && prompt.isConnected);
    ok("[rouvrir] la cible suit le nouveau calque demandé", reg.get("iacCalque").value === "c1" && /Fond/.test(reg.get("iacGoTexte").textContent));
    ok("[rouvrir] la liste des modèles n'est pas relue (choix gardé)", reg.get("iacModele").value === "flux-3");
    // la liste suit le document : calque ajouté, renommé, masqué
    doc.calques.push({ id: "c3", nom: "Texte", objets: [] });
    doc.calques[1].nom = "Logo final";
    doc.calques[0].visible = false;
    VL.surRendu();
    const lc = reg.get("iacCalque");
    ok("[rouvrir] calque ajouté et renommé : la liste suit (surRendu)", lc.valeurs.includes("c3") && /Logo final/.test(lc.innerHTML), lc.innerHTML);
    ok("[rouvrir] un calque masqué le dit (« (masqué) »)", /Fond \(masqué\)/.test(lc.innerHTML), lc.innerHTML);
    ok("[rouvrir] le prompt a survécu au rendu", reg.get("iacPrompt").value === "un renard en vitrail");
    const n0 = lc.ecritures;
    VL.surRendu(); VL.surRendu();
    ok("[rouvrir] un rendu sans changement de calques ne réécrit pas la liste (une liste ouverte reste ouverte)", lc.ecritures === n0, `${n0} → ${lc.ecritures}`);
    toasts.length = 0;
    VL.iaCalque.ouvrir("zz");
    ok("[rouvrir] calque demandé disparu : « n'existe plus », pas « verrouillé »",
       toasts.some((t) => /n'existe plus/.test(t)) && !toasts.some((t) => /verrouillé/.test(t)), toasts.join(" | "));
    doc.calques[1].verrou = true; toasts.length = 0;
    VL.iaCalque.ouvrir("c2");
    ok("[rouvrir] calque demandé verrouillé : « verrouillé »", toasts.some((t) => /verrouillé/.test(t)), toasts.join(" | "));
    doc.calques[1].verrou = false; VL.surRendu();
    // tous verrouillés : la raison ; un calque déverrouillé : la raison s'efface, la cible revient
    for (const c of doc.calques) c.verrou = true;
    VL.surRendu();
    ok("[verrou] tous verrouillés : « Générer » gris, la raison est écrite",
       go.disabled && /tous les calques sont verrouillés/.test(reg.get("iacEtat").textContent), reg.get("iacEtat").textContent);
    doc.calques[2].verrou = false;
    VL.surRendu();
    ok("[verrou] un calque redevient libre : message effacé, cible valide, « Générer » actif",
       reg.get("iacEtat").textContent === "" && reg.get("iacCalque").value === "c3" && !go.disabled, reg.get("iacEtat").textContent);

    // fermer : le focus revient au bouton d'ouverture ; Échap ferme aussi
    const croix = [...dlg.enfants].find((e) => e.dataset.act === "fermer");
    croix.tirer("click");
    ok("[panneau] la croix ferme et rend le focus au bouton d'ouverture", dlg.hidden === true && actif === boutonCalque);
    VL.iaCalque.ouvrir("c3");
    await attendre();
    ok("[panneau] rouvert après fermeture : le prompt tapé reste (squelette construit une seule fois)",
       reg.get("iacPrompt") === prompt && prompt.value === "un renard en vitrail" && !dlg.hidden, reg.get("iacPrompt").value);
    reg.get("iacModele").tirer("keydown", { key: "Escape" });
    ok("[panneau] Échap sur une liste ferme le panneau", dlg.hidden === true);

    // [mineurs 3, 4, 5] la ligne « Retirer le fond » du panneau Image
    modeles.detourage_image = [{ id: "bria-rmbg", dispo: false, cle: "FAL_KEY", usd: 0.018 }, { id: "sam3", dispo: true, prompt: true, usd: 0.02 }];
    const o = { id: "i1", type: "image", href: "img1.png" };
    const ligne1 = new El("div");
    VL.iaCalque.ligneDetour(ligne1, o);
    await attendre();
    const prix1 = ligne1.querySelector("#imDetourPrix");
    ok("[detour] le prix serveur du détourage est affiché à côté du bouton", /\$0\.018/.test(prix1.textContent), prix1.textContent);
    const nDevis = appels.filter((a) => a.url === "/api/cost/estimate").length;
    reg.get("imDetourSujet").value = "le chat";
    reg.get("imDetourSujet").tirer("input");
    toasts.length = 0;
    reg.get("imDetourer").tirer("click");
    await attendre();
    ok("[detour] clé manquante dans le panneau Image : refus SANS « décochez » (pas de case ici)",
       toasts.some((t) => /FAL_KEY/.test(t)) && !toasts.some((t) => /décochez/.test(t)), toasts.join(" | "));
    // le panneau Image est rendu de nouveau (executer → surRendu) : le sujet et le prix restent
    const ligne2 = new El("div");
    VL.iaCalque.ligneDetour(ligne2, o);
    ok("[detour] nouveau rendu : le sujet tapé pour CETTE image revient", ligne2.querySelector("#imDetourSujet").value === "le chat");
    await attendre();
    ok("[detour] nouveau rendu : le même prix, sans nouveau devis", /\$0\.018/.test(ligne2.querySelector("#imDetourPrix").textContent)
       && appels.filter((a) => a.url === "/api/cost/estimate").length === nDevis, ligne2.querySelector("#imDetourPrix").textContent);
    const ligne3 = new El("div");
    VL.iaCalque.ligneDetour(ligne3, { id: "i2", type: "image", href: "img2.png" });
    ok("[detour] une autre image : son propre sujet (vide)", ligne3.querySelector("#imDetourSujet").value === "");
    /* ── [guide] le VRAI panneau : la case, le sélecteur restreint aux modèles edit, le rendu des SEULS calques du
       dessous visibles (VL.svgCourant espionné), le dépôt PUIS l'op edit, la pose qui couvre la page, les refus sans
       envoi, la préférence de modèle par mode, la case décochée ── */
    {
      const stock = new Map();
      globalThis.localStorage = { getItem: (k) => (stock.has(k) ? stock.get(k) : null), setItem: (k, v) => stock.set(k, String(v)) };
      VL.etat.doc = docQuatre("#102030"); VL.etat.docId = "d1";     // c1 Fond, c2 Masqué, c3 Cible, c4 Dessus
      const rendus = [], poses2 = [], envois = [], dessins = [];
      VL.svgCourant = async (transparent, cadre, docBase) => {
        rendus.push({ transparent, ids: docBase.calques.map((c) => c.id), fond: docBase.fond }); return "<svg/>";
      };
      VL.poserDepuisLibrary = async (nom, calqueId, placer) => {
        poses2.push({ nom, calqueId, spec: placer ? placer({ w: 1184, h: 896 }, VL.etat.doc.taille) : null }); return "o8";
      };
      // le rendu PNG du navigateur (Image → canvas → toBlob), simulé
      globalThis.Image = class { set src(u) { this._src = u; setTimeout(() => this.onload && this.onload(), 0); } get src() { return this._src; } };
      const creer0 = globalThis.document.createElement;
      globalThis.document.createElement = (t) => {
        if (t !== "canvas") return creer0(t);
        const cv = { width: 0, height: 0, toBlob: (cb) => cb(new Blob(["png"], { type: "image/png" })) };
        const cx = { fillStyle: "#000000",
          fillRect: (x, y, w, h) => dessins.push(`aplat ${cx.fillStyle} ${w}x${h}`),
          drawImage: (i, x, y, w, h) => dessins.push(`page ${x},${y} ${w}x${h} sur ${cv.width}x${cv.height}`) };
        cv.getContext = () => cx;
        return cv;
      };
      window.fetch = async (url, init) => {
        const corps = init && typeof init.body === "string" ? JSON.parse(init.body) : null;
        const fichier = init && init.body && typeof init.body.get === "function" ? init.body.get("file") : null;
        envois.push({ url, corps, fichier: fichier ? fichier.name : null });
        if (url === "/api/cost/estimate") return fetchFaux(url, init);
        if (url === "/api/images/upload") return { ok: true, status: 200, json: async () => ({ filename: fichier.name }) };
        if (url === "/api/images/process") return { ok: true, status: 200, json: async () => ({ images: ["gen_guide.png"], op: corps.op }) };
        if (url === "/api/images/generate") return { ok: true, status: 200, json: async () => ({ images: ["gen_txt.png"] }) };
        return { ok: false, status: 500, statusText: "x", json: async () => ({}) };
      };
      const tirs = () => envois.filter((e) => e.url !== "/api/cost/estimate").map((e) => e.url);
      VL.iaCalque.ouvrir("c3");
      await attendre();
      const caseG = reg.get("iacGuide"), selM = reg.get("iacModele"), goG = reg.get("iacGo");
      ok("[guide] la case « Guider par les calques du dessous » est au panneau, décochée par défaut",
         caseG && caseG.attrs.type === "checkbox" && caseG.checked === false && /Guider par les calques du dessous/.test(dlg.innerHTML), caseG && caseG.attrs.type);
      ok("[guide] case décochée : tous les modèles raster", egal(selM.valeurs, ["flux-3", "texte-seul", "gpt-image-2"]), JSON.stringify(selM.valeurs));
      selM.value = "texte-seul"; selM.tirer("change");
      caseG.checked = true; caseG.tirer("change");
      await attendre();
      ok("[guide] case cochée : le sélecteur ne propose que les modèles edit — un modèle SANS clé reste proposé",
         egal(selM.valeurs, ["flux-3", "gpt-image-2"]), JSON.stringify(selM.valeurs));
      ok("[guide] le modèle en place ne sait pas guider : le premier qui sait est pris, et c'est dit",
         selM.value === "flux-3" && /« Texte seul » ne sait pas partir d'une image : « flux-3 »/.test(reg.get("iacEtat").textContent), reg.get("iacEtat").textContent);
      ok("[guide] le choix de la case est mémorisé", stock.get("dz_vl_iac_guide") === "1");
      {
        const ctx = { window: {} };
        vm.runInNewContext(lit("../../shared/dz-modeles-ia.js"), ctx);
        const opts = ctx.window.DzModelesIA.grouper(guidables(modeles.image)).flatMap((g) => g.options);
        ok("[guide] les options restreintes (vrai DzModelesIA) : jamais désactivées, la clé manquante dite",
           opts.length === 2 && opts.every((o) => o.desactive === false && o.sansCle && /clé/.test(o.texte)), JSON.stringify(opts));
      }
      const devisG = envois.filter((e) => e.url === "/api/cost/estimate").pop();
      ok("[guide] le devis du tir guidé : kind « image » du modèle qui guide (celui de la garde de l'op edit)",
         devisG && egal(devisG.corps, { kind: "campaign", ops: [{ kind: "image", model: "flux-3", n: 1 }] }) && /\$0\.048/.test(reg.get("iacPrix").textContent),
         JSON.stringify(devisG && devisG.corps) + " " + reg.get("iacPrix").textContent);
      ok("[guide] « Générer » actif (modèle sans clé : le 503 viendra au lancement)", goG.disabled === false);
      reg.get("iacPrompt").value = "un renard en vitrail";
      goG.tirer("click");
      await attendre(14);
      ok("[guide] le tir : dépôt du guide en Bibliothèque PUIS POST /api/images/process — jamais /images/generate",
         egal(tirs(), ["/api/images/upload", "/api/images/process"]), JSON.stringify(tirs()));
      const depot = envois.find((e) => e.url === "/api/images/upload"), edit = envois.find((e) => e.url === "/api/images/process");
      ok("[guide] le guide porte un nom vector_ unique (provenance vectorlab)", /^vector_d1_guide_c3_[0-9a-z]+\.png$/.test(depot.fichier || ""), depot.fichier);
      ok("[guide] l'op edit : {op:\"edit\", filename: le guide déposé, model, prompt, n:1, size du format}",
         edit && edit.corps.op === "edit" && edit.corps.filename === depot.fichier && edit.corps.model === "flux-3" && edit.corps.size === "landscape_4_3"
         && edit.corps.prompt === "un renard en vitrail" && edit.corps.n === 1 && edit.corps.source === "vectorlab", JSON.stringify(edit && edit.corps));
      ok("[guide] le rendu : les SEULS calques du dessous visibles (ni la cible, ni le masqué, ni le dessus), fond gardé, opaque",
         egal(rendus, [{ transparent: false, ids: ["c1"], fond: "#102030" }]), JSON.stringify(rendus));
      ok("[guide] au rapport du format (landscape_4_3 : 1536×1152), canevas rempli du FOND DE PAGE, page à sa place",
         egal(dessins, ["aplat #102030 1536x1152", "page 0,0 1536x1152 sur 1536x1152"]), JSON.stringify(dessins));
      ok("[guide] l'image guidée est posée sur la cible et COUVRE la page (image_poser_page), et c'est dit",
         egal(poses2, [{ nom: "gen_guide.png", calqueId: "c3", spec: { x: 0, y: 0, w: 800, h: 600 } }])
         && /guidée par « vector_d1_guide_c3_/.test(reg.get("iacEtat").textContent), JSON.stringify(poses2) + " " + reg.get("iacEtat").textContent);
      ok("[guide] le document n'a pas bougé (le rendu travaille sur une copie)", VL.etat.doc.calques.length === 4 && VL.etat.doc.calques[2].objets.length === 1);
      ok("[modele] le tir guidé mémorise SON modèle sans écraser celui du mode non guidé",
         stock.get("dz_vl_iac_modele_guide") === "flux-3" && stock.get("dz_vl_iac_modele") !== "flux-3", JSON.stringify([...stock]));
      // une page SANS fond : le guide est posé sur un aplat blanc
      delete VL.etat.doc.fond; dessins.length = 0; envois.length = 0;
      goG.tirer("click");
      await attendre(14);
      ok("[guide] page sans fond : aplat BLANC sous le guide", dessins[0] === "aplat #ffffff 1536x1152" && egal(tirs(), ["/api/images/upload", "/api/images/process"]), JSON.stringify(dessins));
      // rien sous le calque : refus gratuit, aucun envoi (ni dépôt, ni POST)
      envois.length = 0; rendus.length = 0; toasts.length = 0;
      VL.iaCalque.ouvrir("c1");
      await attendre();
      goG.tirer("click");
      await attendre(8);
      ok("[guide] rien sous le calque : aucun envoi, ni rendu ; le refus est dit",
         !tirs().length && !rendus.length && /rien n'est visible sous « Fond »/.test(reg.get("iacEtat").textContent) && toasts.some((t) => /rien n'est visible/.test(t)),
         JSON.stringify(tirs()) + " " + reg.get("iacEtat").textContent);
      // case décochée : le modèle d'avant la bascule revient, le chemin d'avant est inchangé (/images/generate)
      reg.get("iacCalque").value = "c3"; reg.get("iacCalque").tirer("change");
      caseG.checked = false; caseG.tirer("change");
      await attendre();
      envois.length = 0; rendus.length = 0; poses2.length = 0;
      ok("[modele] décochée : mémorisée, tous les modèles reviennent, et le modèle d'AVANT la bascule (texte-seul)",
         stock.get("dz_vl_iac_guide") === "0" && selM.valeurs.length === 3 && selM.value === "texte-seul", selM.value);
      goG.tirer("click");
      await attendre(10);
      ok("[guide] case décochée : POST /api/images/generate seul, ni dépôt ni rendu, pose ordinaire",
         egal(tirs(), ["/api/images/generate"]) && !rendus.length && envois.find((e) => e.url === "/api/images/generate").corps.model === "texte-seul"
         && poses2.length === 1 && poses2[0].spec === null, JSON.stringify(tirs()) + JSON.stringify(poses2));
      ok("[modele] le tir non guidé écrit SA préférence, celle du mode guidé reste",
         stock.get("dz_vl_iac_modele") === "texte-seul" && stock.get("dz_vl_iac_modele_guide") === "flux-3");
      // re-cocher : la préférence du mode guidé revient
      caseG.checked = true; caseG.tirer("change");
      ok("[modele] re-cochée : le modèle guidé mémorisé revient (flux-3)", selM.value === "flux-3", selM.value);
      caseG.checked = false; caseG.tirer("change");

      // une page NEUVE (panneau neuf, catalogue RELU) dont aucun modèle ne sait guider ; puis un catalogue vide
      const neuf = async (liste) => {
        const ancien = reg.get("iaCalqueDlg");           // le panneau de la page précédente disparaît avec elle
        for (const e of (ancien && ancien.enfants) || []) e.isConnected = false;
        if (ancien) ancien.isConnected = false;
        reg.delete("iaCalqueDlg");
        modeles.image = liste;
        const VL2 = { ...VL, etat: { doc: docQuatre("#102030"), docId: "d2", calqueActif: "c3", selection: [] }, surRendu: () => {}, surHistorique: () => {} };
        initIaCalque(VL2);
        VL2.iaCalque.ouvrir("c3");
        await attendre();
        reg.get("iacGuide").checked = true; reg.get("iacGuide").tirer("change");
        await attendre();
        envois.length = 0;
        reg.get("iacPrompt").value = "x";
        reg.get("iacGo").tirer("click");
        reg.get("iacPrompt").tirer("keydown", { key: "Enter", ctrlKey: true });
        await attendre(8);
        return { go: reg.get("iacGo"), sel: reg.get("iacModele"), etat: reg.get("iacEtat").textContent };
      };
      const sansGuide = await neuf([{ id: "texte-seul", label: "Texte seul", dispo: true, usd: 0.003, unite: "image", edit: false }]);
      ok("[guide] catalogue relu sans aucun modèle qui guide : « Générer » gris, la raison « guide », AUCUN envoi",
         sansGuide.sel.value === "" && sansGuide.go.disabled === true && /aucun modèle de la liste ne sait partir d'une image/.test(sansGuide.etat) && !tirs().length,
         `${sansGuide.sel.value} ${sansGuide.go.disabled} ${sansGuide.etat} ${JSON.stringify(tirs())}`);
      const vide = await neuf([]);
      ok("[guide] catalogue relu VIDE, case cochée : raison « vide » (pas « décochez »), AUCUN envoi",
         vide.go.disabled === true && /aucun modèle d'image disponible/.test(vide.etat) && !/décochez/.test(vide.etat) && !tirs().length, vide.etat);
      delete globalThis.Image;
    }
  } finally {
    Object.assign(globalThis, avant);
  }
}

if (echecs.length) {
  console.error("ECHECS iacalque :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA iacalque : PASS (${n} controles)`);
