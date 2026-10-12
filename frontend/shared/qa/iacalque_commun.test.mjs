// t197 — /shared/dz-iacalque-commun.js : la logique pure commune aux panneaux « Image IA sur le calque » du Vectorlab
// (t190) et du Photolab (t191), qui avaient divergé en deux copies. Le module seul, puis le BALAYAGE des deux labs :
// aucune copie ne revient (un lab qui redéfinit une fonction commune rougit), la copie servie sous dist est identique.
// Lancer : node frontend/shared/qa/iacalque_commun.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";
import * as C from "../dz-iacalque-commun.js";

const echecs = [];
let n = 0;
const ok = (nom, cond, detail = "") => {
  n++;
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : ""));
};
const lit = (p) => readFileSync(new URL(p, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const tr = (r, v) => "<" + r + (v ? JSON.stringify(v) : "") + ">";

// 1. formats
ok("[format] 1080×1920 → portrait_16_9", C.formatPour(1080, 1920) === "portrait_16_9");
ok("[format] 2:3 → portrait_4_3, 3:2 → landscape_4_3", C.formatPour(200, 300) === "portrait_4_3" && C.formatPour(300, 200) === "landscape_4_3");
ok("[format] carré, illisible → square_hd", C.formatPour(500, 500) === "square_hd" && C.formatPour(0, 10) === "square_hd" && C.formatPour(undefined, 3) === "square_hd");
ok("[format] TAILLES et RAPPORTS se répondent", C.TAILLES.length === 5 && C.TAILLES.every((t) => C.RAPPORTS[t] > 0));

// 2. devis
const D = (o) => JSON.stringify(C.devisCorps(o));
ok("[devis] image + détourage", D({ modele: "m", detourer: true, modeleDetour: "d" })
  === '{"kind":"campaign","ops":[{"kind":"image","model":"m","n":1},{"kind":"detourage","modele":"d","images":1}]}');
ok("[devis] détourage coché sans modèle : l'image seule", D({ modele: "m", detourer: true }) === '{"kind":"campaign","ops":[{"kind":"image","model":"m","n":1}]}');
ok("[devis] image sans modèle : aucun devis", C.devisCorps({ modele: "", detourer: true, modeleDetour: "d" }) === null && C.devisCorps() === null);
ok("[devis] détourage seul", D({ image: false, detourer: true, modeleDetour: "d" }) === '{"kind":"campaign","ops":[{"kind":"detourage","modele":"d","images":1}]}');
ok("[devis] détourage seul sans modèle : aucun devis", C.devisCorps({ image: false, detourer: true }) === null);

// 3. dollars = DzModelesIA.prixUsd (le repli du banc nu suit la MÊME règle)
{
  const ctx = { window: {} };
  vm.createContext(ctx);
  vm.runInContext(lit("../dz-modeles-ia.js"), ctx);
  const prixUsd = ctx.window.DzModelesIA.prixUsd;
  const vals = [0.001, 0.0015, 0.004, 0.02, 0.04, 0.066, 0.1, 0.145, 0.22, 1, 1.5, 2.3456, 12.0004, 0.0004999];
  const nus = vals.map((v) => C.dollars(v));
  ok("[dollars] repli = prixUsd (14 valeurs)", vals.every((v, k) => nus[k] === prixUsd(v)), JSON.stringify(nus));
  globalThis.DzModelesIA = { prixUsd: () => "$PRIX" };
  ok("[dollars] la page : DzModelesIA.prixUsd sert", C.dollars(0.5) === "$PRIX");
  delete globalThis.DzModelesIA;
}

// 4. libellé du prix
const L = (provider, usd, unit) => ({ provider, usd, unit });
ok("[prix] devis absent", C.libellePrix(null, tr) === "<prix_inconnu>");
ok("[prix] 0 $ payant : à mesurer, jamais gratuit", C.libellePrix({ total_usd: 0, breakdown: [L("fal", 0, "image")] }, tr) === "<prix_a_mesurer>");
ok("[prix] devis sans ligne : à mesurer", C.libellePrix({ total_usd: 0, breakdown: [] }, tr) === "<prix_a_mesurer>");
ok("[prix] local à 0 $ : gratuit", C.libellePrix({ total_usd: 0, breakdown: [L("local", 0, "img")] }, tr) === "<prix_gratuit>");
ok("[prix] total", C.libellePrix({ total_usd: 0.066, breakdown: [L("fal", 0.048, "image"), L("fal", 0.018, "img")] }, tr) === '<prix{"prix":"$0.066"}>');
ok("[prix] part à mesurer NOMMÉE : l'image", C.libellePrix({ total_usd: 0.018, breakdown: [L("openai", 0, "image"), L("fal", 0.018, "img")] }, tr)
  === '<prix{"prix":"$0.018"}><prix_partiel_image>');
ok("[prix] part à mesurer NOMMÉE : le détourage", C.libellePrix({ total_usd: 0.048, breakdown: [L("fal", 0.048, "image"), L("fal", 0, "img")] }, tr)
  === '<prix{"prix":"$0.048"}><prix_partiel>');

// 5. refus
ok("[erreur] 503 = clé absente", C.messageErreur(503, { detail: "FAL_KEY" }, "", tr) === '<cle_absente{"detail":"FAL_KEY"}>');
ok("[erreur] 402 du plafond", C.messageErreur(402, { detail: { dz_plafond: { message: "mois plein" } } }, "", tr) === "mois plein");
ok("[erreur] détail chaîne, repli, code", C.messageErreur(409, { detail: "x" }, "", tr) === "x"
  && C.messageErreur(500, {}, "Internal", tr) === "Internal" && C.messageErreur(500, null, "", tr) === "500");
const leve = (f) => { try { f(); return ""; } catch (e) { return e.message; } };
ok("[détourage] rien demandé : rien", leve(() => C.verifierDetour({ detourer: false }, null, tr)) === "");
ok("[détourage] sans modèle", leve(() => C.verifierDetour({ detourer: true }, null, tr)) === "<detour_modele>");
ok("[détourage] clé absente (case / bouton seul)", leve(() => C.verifierDetour({ detourer: true, modeleDetour: "d" }, { dispo: false, cle: "K" }, tr)) === '<detour_cle{"cle":"K"}>'
  && leve(() => C.verifierDetour({ detourer: true, modeleDetour: "d" }, { dispo: false, cle: "K" }, tr, { sansCase: true })) === '<detour_cle_image{"cle":"K"}>');
ok("[détourage] sujet exigé", leve(() => C.verifierDetour({ detourer: true, modeleDetour: "d", sujet: " " }, { prompt: true }, tr)) === "<sujet_requis>"
  && leve(() => C.verifierDetour({ detourer: true, modeleDetour: "d", sujet: "chat" }, { prompt: true }, tr)) === "");

// 6. un seul vol
{
  let fin, apres = 0;
  const g = C.unSeulVol(() => new Promise((r) => { fin = r; }), () => { apres++; });
  const p1 = g(1), p2 = g(2);
  ok("[vol] le second appel ne relance rien", g.enVol === true && (await p2) === null);
  fin("fait");
  ok("[vol] l'issue du premier, puis apres()", (await p1) === "fait" && g.enVol === false && apres === 1);
}

// 7. gestes : ce qui COMMENCE est gardé, jamais un relâchement
ok("[gestes] clic, molette, touche enfoncée gardés", ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel", "keydown"].every((t) => C.GESTES_GARDES.includes(t)));
ok("[gestes] keyup et pointerup JAMAIS gardés (Espace relâché sur le panneau rend la main)",
  !C.GESTES_GARDES.includes("keyup") && !C.GESTES_GARDES.includes("pointerup"));
{
  const ec = {};
  const el = { addEventListener: (t, f, o) => { ec[t] = { f, o }; } };
  C.garderGestes(el);
  let arrete = 0;
  ec.keydown.f({ stopPropagation: () => { arrete++; } });
  ok("[gestes] garderGestes arrête keydown, molette passive, rien sur keyup", arrete === 1 && ec.wheel.o && ec.wheel.o.passive === true && !ec.keyup);
}

// 8. BALAYAGE : les deux labs prennent le module commun, aucune copie ne revient
const LABS = { vectorlab: "../../vectorlab/js/mod-iacalque.js", photolab: "../../photolab/js/mod-iacalque.js" };
const COMMUNES = ["formatPour", "dollars", "unSeulVol", "garderGestes"];
for (const [lab, p] of Object.entries(LABS)) {
  const s = lit(p);
  ok(`[balayage] ${lab} importe ../../shared/dz-iacalque-commun.js`, s.includes('from "../../shared/dz-iacalque-commun.js"'));
  for (const f of COMMUNES) ok(`[balayage] ${lab} ne redéfinit pas ${f}`, !new RegExp(`function\\s+${f}\\s*\\(`).test(s));
  ok(`[balayage] ${lab} : aucune liste de formats ni de gestes recopiée`, !/\[\s*"portrait_16_9"/.test(s) && !/\[\s*"pointerdown"/.test(s));
  ok(`[balayage] ${lab} : libellePrix / messageErreur / verifierDetour / devisCorps délèguent`,
    ["libellePrix", "messageErreur", "verifierDetour", "devisCorps"].every((f) => !new RegExp(`function\\s+${f}\\s*\\(`).test(s)
      && new RegExp(`C\\.${f}\\(`).test(s)));
}
{
  const fl = lit("../../vectorlab/js/mod-flottant.js");
  ok("[balayage] mod-flottant : la garde du Vectorlab est garderGestes", /garderGestes\(el\)/.test(fl) && !/\[\s*"pointerdown"/.test(fl));
}
ok("[servi] frontend/dist/shared/dz-iacalque-commun.js identique", lit("../dz-iacalque-commun.js") === lit("../../dist/shared/dz-iacalque-commun.js"));
ok("[pur] aucun window ni document à l'import", !/^\s*(window|document)\./m.test(lit("../dz-iacalque-commun.js")));

// 9. les deux labs, adaptés : même format, même règle de prix
{
  const V = await import(LABS.vectorlab), P = await import(LABS.photolab);
  ok("[labs] même format pour la même page", V.taillePour({ w: 1080, h: 1920 }) === "portrait_16_9" && P.taillePour({ width: 1080, height: 1920 }) === "portrait_16_9");
  ok("[labs] même devis", JSON.stringify(V.devisCorps({ modele: "m", detourer: true, modeleDetour: "d" }))
    === JSON.stringify(P.devisCorps({ mode: "ia", modele: "m", detourer: true, modeleDetour: "d" }))
    && JSON.stringify(V.devisDetour("d")) === JSON.stringify(P.devisCorps({ mode: "detour", modeleDetour: "d" })));
  ok("[labs] Photolab : la part à mesurer est nommée comme au Vectorlab",
    P.libellePrix({ total_usd: 0.018, breakdown: [L("openai", 0, "image"), L("fal", 0.018, "img")] }).endsWith("photolab.iacalque.prix_partiel_image")
    && P.libellePrix({ total_usd: 0, breakdown: [] }) === "photolab.iacalque.prix_a_mesurer"
    && P.libellePrix({ total_usd: 0, breakdown: [L("local", 0, "img")] }) === "photolab.iacalque.gratuit");
  ok("[labs] les deux gardent la même liste de gestes", P.GESTES_GARDES === C.GESTES_GARDES);
  const dico = JSON.parse(lit("../i18n/photolab.json"));
  ok("[labs] photolab.json porte prix_partiel_image et prix_partiel (détourage)", !!dico["photolab.iacalque.prix_partiel_image"]
    && /détourage/.test(dico["photolab.iacalque.prix_partiel"].fr));
}

if (echecs.length) {
  console.error("ECHECS iacalque_commun :\n- " + echecs.join("\n- "));
  process.exit(1);
}
console.log(`QA iacalque_commun : PASS (${n} controles)`);
