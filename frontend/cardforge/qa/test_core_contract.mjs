#!/usr/bin/env node
/* ═══════════════════════════════════════════════════════════════════════════
   qa/test_core_contract.mjs — LA PREUVE DU CONTRAT, sans main humaine.

   L'en-tete de core.js annonçait ce fichier depuis le premier jour ; il
   n'existait pas. Le contrat n'avait donc AUCUN test : c'est ce qui a laissé
   passer l'usurpation d'identite, le squat du registre, l'export qui diverge
   de l'apercu et la course sur CF.side(). Il existe maintenant, et il fait
   deux choses.

   1. GEOMETRIE, sans navigateur (`--geom`) — charge le VRAI js/core.js dans un
      `vm` Node (aucune recopie de la formule) et compare ses sorties a une
      reference ecrite en arithmetique EXACTE (BigInt rationnel, zero
      flottant), sur 12 formats x 6 definitions x 5 fonds perdus x 4 zones
      sures = 1440 geometries, 5 champs de pixels chacune.

   2. CLOISONNEMENT, dans un Chrome sans tete (`--contract`) — ouvre
      qa/contract.html, qui charge le vrai core.js et de FAUX modules dont
      deux hostiles, et relit ce que chacun a obtenu. Toute ligne « OUVERT »
      fait sortir en erreur.

   Usage :
     node frontend/cardforge/qa/test_core_contract.mjs            (les deux)
     node frontend/cardforge/qa/test_core_contract.mjs --geom
     node frontend/cardforge/qa/test_core_contract.mjs --contract [--url …]
   Code de sortie : 0 = contrat tenu, 1 = au moins une violation.
   ═══════════════════════════════════════════════════════════════════════════ */
import { readFileSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import vm from 'node:vm';

const HERE = dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const CORE = join(HERE, '..', 'js', 'core.js');
const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
const want = (k) => argv.indexOf(k) >= 0;
const URL_ = arg('--url', 'http://127.0.0.1:8765/cardforge/qa/contract.html');
const doGeom = want('--geom') || !want('--contract');
const doContract = want('--contract') || !want('--geom');

/* « Enregistrer comme modele » ECRIT un fichier chez l'utilisateur : le banc
   doit savoir le reprendre, sinon chaque passage laisse un modele de plus dans
   sa galerie. Il le fait par la ROUTE (DELETE /api/cards/models/{id}, ronde T3
   du 22/08) et non en allant chercher le dossier sur le disque : le banc n'a
   alors aucun chemin de donnees a recopier, donc rien qui puisse deriver le
   jour ou le backend range ses modeles ailleurs. Si la route n'existe pas sur
   le backend interroge, le pin n'est pas JOUE — on ne salit pas ce qu'on ne
   sait pas nettoyer. */
/* miroir de core.js:DID_RE / contract.py:is_valid_did */
const DID_RE_QA = /^deck_[0-9a-f]{8}$/;

let failures = 0;
const ok = (m) => console.log('  ok   ' + m);
const ko = (m) => { failures++; console.log('  KO   ' + m); };

/* ── 1. GEOMETRIE ───────────────────────────────────────────────────────── */
/* reference EXACTE : rationnels sur BigInt, aucun flottant nulle part. */
function frac(dec) {                       /* "63.5" -> [num, den] */
  const s = String(dec);
  const neg = s.startsWith('-');
  const [i, f = ''] = (neg ? s.slice(1) : s).split('.');
  const num = BigInt((i || '0') + f) * (neg ? -1n : 1n);
  return [num, 10n ** BigInt(f.length)];
}
function mul([a, b], [c, d]) { return [a * c, b * d]; }
function add([a, b], [c, d]) { return [a * d + c * b, b * d]; }
function floorHalf([a, b]) {               /* floor(a/b + 1/2), b > 0 */
  const n = 2n * a + b, d = 2n * b;
  let q = n / d;
  if (n % d !== 0n && n < 0n) q -= 1n;
  return q;
}
function refGeom(trim_mm, dpi, bleed_mm, safe_mm) {
  const px = (mmStr) => Number(floorHalf(mul(frac(mmStr), [BigInt(dpi) * 10n, 254n])));
  const sum = (a, k, b) => {               /* a + k*b, en decimal exact */
    const r = add(frac(a), mul([BigInt(k), 1n], frac(b)));
    return [r[0], r[1]];
  };
  const dec = ([n, d]) => {                /* rationnel -> chaine decimale exacte */
    const neg = n < 0n; if (neg) n = -n;
    const ent = n / d; let rest = n % d, out = ent.toString(), frac2 = '';
    for (let i = 0; i < 12 && rest !== 0n; i++) { rest *= 10n; frac2 += (rest / d).toString(); rest %= d; }
    return (neg ? '-' : '') + out + (frac2 ? '.' + frac2 : '');
  };
  const w = trim_mm[0], h = trim_mm[1];
  const trim = [px(w), px(h)];
  const canvas = [px(dec(sum(w, 2, bleed_mm))), px(dec(sum(h, 2, bleed_mm)))];
  const safe = [px(dec(sum(w, -2, safe_mm))), px(dec(sum(h, -2, safe_mm)))];
  const boff = [(canvas[0] - trim[0]) / 2, (canvas[1] - trim[1]) / 2];
  const soff = [boff[0] + (trim[0] - safe[0]) / 2, boff[1] + (trim[1] - safe[1]) / 2];
  return { trim_px: trim, canvas_px: canvas, bleed_off_px: boff, safe_px: safe, safe_off_px: soff };
}

/* charge le VRAI fichier, tel quel, dans un contexte sans DOM. Aucune recopie
   de la formule : c'est le fichier de production qui repond. */
let LAST_CTX = null;
function loadCF() {
  const src = readFileSync(CORE, 'utf8');
  const ctx = vm.createContext({ console, setTimeout, clearTimeout, URL });
  ctx.globalThis = ctx;
  vm.runInContext(src, ctx, { filename: CORE });
  if (!ctx.CF) throw new Error("core.js n'a pas publie CF dans un contexte sans DOM");
  LAST_CTX = ctx;
  return ctx.CF;
}

function testGeom() {
  console.log('[1] geometrie — le VRAI core.js dans un vm, contre une reference exacte');
  const CF = loadCF();
  const DPIS = [72, 96, 150, 300, 600, 1200];
  const BLEEDS = ['0', '3', '3.175', '5.5', '10'];
  const SAFES = ['0', '1.5', '3.175', '10'];
  let n = 0, bad = 0, firstBad = null;
  for (const f of CF.FORMATS) {
    const trim = [String(f.trim_mm[0]), String(f.trim_mm[1])];
    for (const dpi of DPIS) for (const b of BLEEDS) for (const s of SAFES) {
      const g = CF.geomOf(f.id, dpi, Number(b), Number(s), 3);
      const r = refGeom(trim, dpi, b, s);
      n++;
      for (const k of ['trim_px', 'canvas_px', 'bleed_off_px', 'safe_px', 'safe_off_px']) {
        if (JSON.stringify(g[k]) !== JSON.stringify(r[k])) {
          bad++;
          if (!firstBad) firstBad = `${f.id} dpi=${dpi} bleed=${b} safe=${s} ${k}: core=${JSON.stringify(g[k])} exact=${JSON.stringify(r[k])}`;
        }
      }
    }
  }
  if (bad) ko(`${bad} divergence(s) sur ${n} geometries — ex. ${firstBad}`);
  else ok(`${n} geometries x 5 champs : 0 divergence avec l'arithmetique exacte`);

  /* les chiffres nommes par la spec, au pixel */
  const cas = [
    ['poker_us', 300, 'canvas_px', [825, 1125]], ['poker_eu', 300, 'canvas_px', [815, 1110]],
    ['bridge_us', 300, 'canvas_px', [750, 1125]], ['tarot_us', 300, 'canvas_px', [900, 1500]],
    ['domino', 300, 'canvas_px', [600, 1125]], ['business', 300, 'canvas_px', [675, 1125]],
    ['jumbo', 300, 'canvas_px', [1125, 1725]], ['micro', 300, 'canvas_px', [450, 600]],
    ['poker_us', 300, 'trim_px', [750, 1050]], ['micro', 300, 'safe_px', [300, 450]],
    ['poker_us', 300, 'safe_off_px', [75, 75]], ['poker_us', 300, 'bleed_off_px', [37.5, 37.5]],
  ];
  let p = 0;
  for (const [fmt, dpi, champ, att] of cas) {
    const F = CF.FORMATS.find((x) => x.id === fmt);
    const nat = F.unit === 'in' ? 3.175 : 3;
    const g = CF.geomOf(fmt, dpi, nat, nat, 3);
    if (JSON.stringify(g[champ]) !== JSON.stringify(att)) ko(`${fmt}@${dpi} ${champ} = ${JSON.stringify(g[champ])}, attendu ${JSON.stringify(att)}`);
    else p++;
  }
  if (p === cas.length) ok(`${p}/${cas.length} seuils nommes par la spec (parite nanDECK + zone sure)`);

  /* les bornes : geomOf n'est pas une porte de service */
  try { CF.geomOf('poker_eu', 100000, -50, 0, 0); ko('geomOf accepte dpi=100000 / bleed=-50'); }
  catch (e) { ok('geomOf refuse hors bornes : ' + e.message.slice(0, 60)); }

  /* le global est gele, et le NOM avec */
  loadCF();
  const d = Object.getOwnPropertyDescriptor(LAST_CTX, 'CF');
  if (d && (d.writable === false && d.configurable === false)) ok('window.CF : writable=false configurable=false');
  else ko('window.CF est encore remplacable : ' + JSON.stringify(d && { w: d.writable, c: d.configurable }));
}
/* ── 2. CLOISONNEMENT (Chrome sans tete) ────────────────────────────────── */
const CHROME = [process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'].filter(Boolean).find((p) => existsSync(p));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const BATTERIE = `(async () => {
  const out = window.__CFQA.slice();
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const g = CF.geom();

  /* le painter recoit-il une echelle ? */
  const cv = await CF.renderCard(0, { scale: 0.35, guides: true });
  const a = window.__QA_PAINTER_ARGS || {};
  say("renderCard ignore un scale du dehors",
      (cv.width === g.canvas_px[0] && cv.height === g.canvas_px[1]) ? "TENU" : "OUVERT",
      "toile " + g.canvas_px.join("x") + " -> rendu " + cv.width + "x" + cv.height);
  say("le painter ne recoit AUCUNE echelle", (a.n === 5 && a.types.indexOf("Number") < 0) ? "TENU" : "OUVERT",
      "arguments=" + a.n + " [" + (a.types || []).join(", ") + "]");
  say("le painter recoit une matrice identite", JSON.stringify(a.transform) === JSON.stringify([1,0,0,1,0,0]) ? "TENU" : "OUVERT",
      JSON.stringify(a.transform));

  /* les reperes dans un fichier livre */
  const px = (c) => { const d = c.getContext("2d").getImageData(0,0,c.width,c.height).data; let r=0,b=0,v=0;
    for (let i=0;i<d.length;i+=4){ if(d[i]===0xff&&d[i+1]===0x2d&&d[i+2]===0x92)r++; if(d[i]===0x00&&d[i+1]===0xb7&&d[i+2]===0xff)b++; if(d[i]===0x33&&d[i+1]===0xd1&&d[i+2]===0x8b)v++; }
    return {rose:r,cyan:b,vert:v}; };
  const n1 = px(cv);
  say("reperes z=90 dans une toile rendue par CF.renderCard", (n1.rose+n1.cyan+n1.vert)===0 ? "TENU" : "OUVERT", JSON.stringify(n1));
  /* et ils sont bien LA dans l'apercu du CORE : on ne peut pas y compter des
     couleurs exactes (l'apercu est un bitmap REDUIT, donc interpole), alors on
     compare l'apercu au meme rendu SANS reperes, reduit pareil. Il doit
     differer — c'est la preuve que la couche z=90 existe a l'ecran et nulle
     part ailleurs. */
  const apercu = document.getElementById("stageCanvas");
  const tmp = document.createElement("canvas");
  tmp.width = apercu.width; tmp.height = apercu.height;
  const t2 = tmp.getContext("2d");
  t2.imageSmoothingEnabled = true;
  t2.drawImage(await CF.renderCard(0, {}), 0, 0, tmp.width, tmp.height);
  const A = apercu.getContext("2d").getImageData(0,0,apercu.width,apercu.height).data;
  const B = t2.getImageData(0,0,tmp.width,tmp.height).data;
  let diff = 0;
  for (let i = 0; i < A.length; i += 4) if (Math.abs(A[i]-B[i]) + Math.abs(A[i+1]-B[i+1]) + Math.abs(A[i+2]-B[i+2]) > 24) diff++;
  say("reperes bien PRESENTS dans l'apercu du CORE (et absents du fichier)",
      diff > 200 ? "TENU" : "OUVERT", diff + " pixels different de la meme carte sans reperes (" + apercu.width + "x" + apercu.height + ")");

  /* provenance du telechargement */
  try { CF.download(new Blob([new Uint8Array([1,2,3])]), "x.png"); say("CF.download d'un blob etranger","OUVERT","accepte"); }
  catch (e) { say("CF.download d'un blob etranger","TENU", e.message); }
  try { const b = await CF.cardBlob(0, {}); CF.download(b, "carte_qa.png"); say("CF.download du blob du moteur","TENU", b.size + " o"); }
  catch (e) { say("CF.download du blob du moteur","OUVERT", e.message); }

  /* course sur CF.side() : deux rendus concurrents, painter lent */
  window.__QA_SIDE_TRACE = [];
  const p1 = CF.renderCard(0, { face: "back" });
  const p2 = CF.renderCard(0, { face: "front" });
  await Promise.all([p1, p2]);
  const trace = window.__QA_SIDE_TRACE.slice();
  const melange = trace.filter((t) => { const m = t.match(/apres-await:(\\w+)\\/(\\w+)/); return m && m[1] !== m[2]; });
  say("CF.side() pendant deux rendus concurrents", melange.length === 0 ? "TENU" : "OUVERT", trace.join(" | "));

  /* painter qui redimensionne la toile */
  window.__QA_RESIZE = true;
  const cv2 = await CF.renderCard(0, {});
  window.__QA_RESIZE = false;
  const errs = CF.renderErrors();
  say("painter qui redimensionne la toile : rendu conserve + erreur nommee",
      (cv2.width === g.canvas_px[0] && errs.some((e) => e.id === "texture")) ? "TENU" : "OUVERT",
      cv2.width + "x" + cv2.height + " erreurs=" + JSON.stringify(errs));

  /* painter dont la promesse ne se resout jamais */
  window.__QA_HANG = true;
  const t0 = Date.now();
  let fini = "BLOQUE";
  try { const cv3 = await Promise.race([CF.renderCard(0, {}), new Promise((r) => setTimeout(() => r(null), 9000))]);
        fini = cv3 ? "rendu en " + (Date.now()-t0) + " ms" : "TOUJOURS BLOQUE apres 9 s"; }
  catch (e) { fini = "erreur " + e.message; }
  window.__QA_HANG = false;
  const errs2 = CF.renderErrors();
  say("painter qui ne rend jamais la main : delai de garde",
      (fini.indexOf("rendu en") === 0 && errs2.some((e) => e.id === "texture")) ? "TENU" : "OUVERT",
      fini + " erreurs=" + JSON.stringify(errs2.map((e) => e.id + " z" + e.z)));

  /* l'apercu repart apres l'incident : pas de gel definitif */
  await CF.renderCard(0, {});
  say("le moteur repart apres l'incident", "TENU", "rendu suivant obtenu");

  /* ── P9 : couches prouvees sur les painters du banc. Les groupes = la table
     LAYER_ROLES de la piece forge3d : ils doivent COUVRIR tous les z qui
     peignent (10, 20, 30, 40, 60), sinon l'empilement ne peut pas reproduire
     le composite PLEIN. z=70 n'a pas de painter au banc : couche vide,
     transparente, isolee — valide. */
  try {
    const L = await CF.layers(0, { face: "front", groups: [
      { role: "fond-matiere", z: [10] }, { role: "illustration", z: [20] },
      { role: "voile-matiere", z: [30] }, { role: "cadre", z: [40] },
      { role: "typographie", z: [60] }, { role: "ornements", z: [70] }] });
    say("layers : empilement reproduit le rendu", L.stack_ok === true ? "TENU" : "OUVERT",
        (L.stack_ok === true ? "stack_ok" : "ECHEC stack_ok=false")
        + (L.errors.length ? " erreurs=" + JSON.stringify(L.errors) : ""));
    say("layers : modes avoues", "NOTE", L.layers.map((l) => l.role + "=" + l.mode).join(" "));
    try { const lb = await CF.layerBlob(L.layers[0].canvas); CF.download(lb, "couche_qa.png");
          say("layers : blob de couche MINTE accepte par CF.download", "TENU", lb.size + " o"); }
    catch (e) { say("layers : blob de couche MINTE accepte par CF.download", "OUVERT", e.message); }
  } catch (e) { say("layers", "OUVERT", e.message); }

  /* ── coquille : rail et colonne carte escamotables (patron shell.jsx) ────
     Le banc masque les visuels (display:none) : on n'affirme AUCUNE geometrie
     — seulement les CLASSES portees par la grille .cf et le STOCKAGE. Ce
     qui est prouve : les deux chevrons existent apres le boot ; un clic pose
     la classe ET ecrit la cle ; un second clic retire l'une ET efface
     l'autre. Une bascule qui oublie d'ecrire laisse l'ecran juste et fait
     mentir le rechargement — c'est exactement ce que la classe seule ne dit
     pas. */
  const cfg = document.querySelector(".cf");
  const rfb = document.getElementById("railFoldBtn");
  const sfb = document.getElementById("stageFoldBtn");
  const lsq = (k) => { try { return localStorage.getItem(k); } catch (e) { return "?refus"; } };
  const cls = () => "classes=[" + (cfg ? cfg.className : "?") + "]";
  say("escamotage : les deux chevrons existent apres le boot",
      (rfb && sfb && cfg) ? "TENU" : "OUVERT",
      "rail=" + !!rfb + " carte=" + !!sfb + " grille .cf=" + !!cfg);
  if (rfb && sfb && cfg) {
    rfb.click();
    say("escamotage rail : clic -> classe rail-replie ET dz_cf_rail=1",
        (cfg.classList.contains("rail-replie") && lsq("dz_cf_rail") === "1") ? "TENU" : "OUVERT",
        cls() + " dz_cf_rail=" + JSON.stringify(lsq("dz_cf_rail")));
    rfb.click();
    say("escamotage rail : second clic -> classe retiree ET cle effacee",
        (!cfg.classList.contains("rail-replie") && lsq("dz_cf_rail") === null) ? "TENU" : "OUVERT",
        cls() + " dz_cf_rail=" + JSON.stringify(lsq("dz_cf_rail")));
    sfb.click();
    say("escamotage carte : clic -> classe stage-replie ET dz_cf_stage=1",
        (cfg.classList.contains("stage-replie") && lsq("dz_cf_stage") === "1") ? "TENU" : "OUVERT",
        cls() + " dz_cf_stage=" + JSON.stringify(lsq("dz_cf_stage")));
    sfb.click();
    say("escamotage carte : second clic -> classe retiree ET cle effacee",
        (!cfg.classList.contains("stage-replie") && lsq("dz_cf_stage") === null) ? "TENU" : "OUVERT",
        cls() + " dz_cf_stage=" + JSON.stringify(lsq("dz_cf_stage")));
    /* replie, une rangee du rail n'a plus que son numero : sans title=, neuf
       pastilles muettes. */
    const muettes = Array.prototype.filter.call(document.querySelectorAll(".rail-item"), (b) => !b.title).length;
    say("escamotage rail : chaque rangee nomme sa piece en title=",
        muettes === 0 ? "TENU" : "OUVERT", muettes + " rangee(s) sans title sur " + document.querySelectorAll(".rail-item").length);
    say("escamotage : le chevron du rail n'est PAS une piece du rail",
        (rfb.classList.contains("rail-item") === false && !rfb.dataset.mod) ? "TENU" : "OUVERT",
        "classes=[" + rfb.className + "] data-mod=" + JSON.stringify(rfb.dataset.mod || null));
  }

  /* ── GALERIE DE DEMARRAGE (T4, spec §6.4) ───────────────────────────────
     Meme discipline que l'escamotage : le banc masque les visuels et n'a pas
     la feuille du lab, donc AUCUNE geometrie n'est affirmee. On lit la
     CLASSE, le data-, le DOM reellement construit et le stockage. Les
     modeles, eux, viennent du VRAI backend (:8765) : c'est le seul moyen de
     prouver que l'ecran consomme GET /api/cards/models et non une table
     recopiee dans le navigateur. */
  const gb = document.getElementById("galleryBtn");
  say("galerie : le bouton « Modeles » existe apres le boot", gb ? "TENU" : "OUVERT",
      gb ? ("#" + gb.id + " [" + gb.className + "]") : "absent");
  if (gb) {
    gb.click();
    const gr = document.getElementById("galRoot");
    say("galerie : le clic ouvre l'ecran (hidden retiree ET data-open=1)",
        (gr && !gr.classList.contains("hidden") && gr.dataset.open === "1") ? "TENU" : "OUVERT",
        gr ? ("classes=[" + gr.className + "] data-open=" + gr.dataset.open + " why=" + gr.dataset.why) : "pas de #galRoot");
    let cartes = [];
    for (let i = 0; i < 60 && cartes.length === 0; i++) {
      await new Promise((r) => setTimeout(r, 200));
      cartes = Array.prototype.slice.call(document.querySelectorAll("#galModels .cf-gal-card"));
    }
    const ids = cartes.map((c) => c.dataset.model);
    say("galerie : au moins les 7 modeles d'usine sont listes",
        cartes.length >= 7 ? "TENU" : "OUVERT", cartes.length + " carte(s) : " + ids.join(", "));
    const sept = ["superstar", "duel", "creature", "arcane", "monstre", "legende", "gravee"];
    const manquants = sept.filter((s) => ids.indexOf(s) < 0);
    say("galerie : les sept archetypes nommes par la spec y sont",
        manquants.length === 0 ? "TENU" : "OUVERT",
        manquants.length ? ("manquants : " + manquants.join(", ")) : "les 7");
    /* la vignette : une toile PEINTE, pas un rectangle. Un plan de zones
       porte au moins le papier, la plaque, l'encre et le trait de coupe. */
    const cv = document.querySelector('#galModels .cf-gal-card[data-model="superstar"] .cf-gal-thumb');
    const teintes = new Set();
    if (cv) {
      const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data;
      for (let i = 0; i < d.length; i += 4) teintes.add(d[i] + "," + d[i + 1] + "," + d[i + 2]);
    }
    say("galerie : la vignette est le PLAN DES ZONES, reellement peint",
        (cv && teintes.size >= 6) ? "TENU" : "OUVERT",
        cv ? (cv.width + "x" + cv.height + " -> " + teintes.size + " teintes") : "pas de vignette");
    document.getElementById("galImport").click();
    const tst = document.getElementById("toast");
    say("galerie : « Importer une carte » refuse en NOMMANT la phase",
        (tst && !tst.classList.contains("hidden")
         && tst.textContent.indexOf("phase 4 — l'import arrive") >= 0) ? "TENU" : "OUVERT",
        tst ? tst.textContent.slice(0, 90) : "pas de toast");
    say("galerie : le refus d'import ne referme pas l'ecran",
        (gr && gr.dataset.open === "1") ? "TENU" : "OUVERT", gr ? gr.dataset.open : "?");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    say("galerie : Echap ferme (hidden posee ET data-open=0)",
        (gr && gr.classList.contains("hidden") && gr.dataset.open === "0") ? "TENU" : "OUVERT",
        gr ? ("classes=[" + gr.className + "] data-open=" + gr.dataset.open) : "?");
  }

  /* le module en mode bâclé n'a pas demarre et ses couches ont quitte la pile */
  const hote = document.querySelector('.cf-host[data-host="solid"]');
  say("module sans \\"use strict\\" : init NON appelee",
      (hote && hote.textContent.indexOf("use strict") >= 0) ? "TENU" : "OUVERT",
      (hote ? hote.textContent.slice(0, 90) : "pas d'hote"));
  say("module sans \\"use strict\\" : bandeau visible",
      document.getElementById("apiBar").classList.contains("hidden") === false ? "TENU" : "OUVERT",
      document.getElementById("apiBarMsg").textContent.slice(0, 90));

  return { deck: CF.get("id", null), out };
})()`;

/* ── batterie « repli au BOOT » ─────────────────────────────────────────────
   Jouee sur une page RECHARGEE, les deux cles dz_cf_* deja ecrites. C'est le
   seul pin qui distingue « la classe est posee au demarrage » de « la classe
   est posee plus tard » : une application tardive passerait toute la batterie
   principale et ferait quand meme clignoter la coquille a chaque ouverture
   (colonnes ouvertes, puis refermees sous les yeux de l'utilisateur). */
const BATTERIE_REPLI = `(async () => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const cf = document.querySelector(".cf");
  const rfb = document.getElementById("railFoldBtn");
  const sfb = document.getElementById("stageFoldBtn");
  const lsq = (k) => { try { return localStorage.getItem(k); } catch (e) { return "?refus"; } };
  say("escamotage : dz_cf_rail/dz_cf_stage relus AU BOOT (les deux colonnes repliees d'entree)",
      (cf && cf.classList.contains("rail-replie") && cf.classList.contains("stage-replie")) ? "TENU" : "OUVERT",
      "classes=[" + (cf ? cf.className : "pas de .cf") + "] rail=" + JSON.stringify(lsq("dz_cf_rail"))
      + " carte=" + JSON.stringify(lsq("dz_cf_stage")));
  if (cf && rfb && sfb) {
    rfb.click(); sfb.click();
    say("escamotage : rouvrir depuis l'etat replie efface les deux cles",
        (!cf.classList.contains("rail-replie") && !cf.classList.contains("stage-replie")
         && lsq("dz_cf_rail") === null && lsq("dz_cf_stage") === null) ? "TENU" : "OUVERT",
        "classes=[" + cf.className + "] rail=" + JSON.stringify(lsq("dz_cf_rail"))
        + " carte=" + JSON.stringify(lsq("dz_cf_stage")));
  } else {
    say("escamotage : chevrons presents apres rechargement", "OUVERT",
        "rail=" + !!rfb + " carte=" + !!sfb + " grille=" + !!cf);
  }
  /* LE PENDANT NEGATIF DU PREMIER LANCEMENT. Cette page-ci a REPRIS un jeu
     (dz_cf_deck_id) : la galerie de demarrage n'a rien a faire par-dessus.
     Sans ce pin, un « openGallery() » pose sans condition dans boot() passerait
     toute la batterie et sauterait au visage de l'utilisateur a chaque
     ouverture de l'onglet Cartes. */
  const gr = document.getElementById("galRoot");
  say("galerie : un jeu REPRIS au boot n'ouvre pas la galerie de demarrage",
      (!gr || gr.classList.contains("hidden")) ? "TENU" : "OUVERT",
      gr ? ("classes=[" + gr.className + "] why=" + gr.dataset.why) : "pas de #galRoot (jamais construit)");
  return { out };
})()`;

/* ── batterie « instancier un modele » ──────────────────────────────────────
   Elle CLIQUE et la page part : le POST cree le jeu, `galGo` pose ?deck= et
   recharge. Les verdicts se lisent donc dans la passe suivante, et le jeu cree
   est un jeu de banc de plus a supprimer. */
const BATTERIE_SEMER = `(async () => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const avant = CF.get("id", null);
  const gb = document.getElementById("galleryBtn");
  if (!gb) { say("galerie : bouton present avant instanciation", "OUVERT", "absent"); return { out, avant }; }
  gb.click();
  let b = null;
  for (let i = 0; i < 60 && !b; i++) {
    await new Promise((r) => setTimeout(r, 200));
    b = document.querySelector('#galModels .cf-gal-card[data-model="superstar"] .cf-gal-new');
  }
  say("galerie : « Nouveau jeu depuis ce modele » est offert sur superstar",
      b ? "TENU" : "OUVERT", b ? b.textContent : "absent");
  if (b) b.click();
  return { out, avant, clique: !!b };
})()`;

const BATTERIE_SEME = `(() => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const did = CF.get("id", null);
  const slots = CF.get("type.slots", []);
  const ls = (() => { try { return localStorage.getItem("dz_cf_deck_id"); } catch (e) { return "?refus"; } })();
  say("galerie : instancier un modele OUVRE le jeu cree (?deck= + dz_cf_deck_id + document)",
      (did && location.search.indexOf(did) >= 0 && ls === did) ? "TENU" : "OUVERT",
      "deck=" + did + " search=" + location.search + " dz_cf_deck_id=" + ls);
  say("galerie : le jeu ouvert porte deja les slots du modele (la graine a pris)",
      (Array.isArray(slots) && slots.length >= 10) ? "TENU" : "OUVERT",
      (Array.isArray(slots) ? slots.length : "?") + " slot(s) dans doc.type");
  const gr = document.getElementById("galRoot");
  say("galerie : le jeu instancie s'ouvre SANS la galerie par-dessus",
      (!gr || gr.classList.contains("hidden")) ? "TENU" : "OUVERT",
      gr ? ("classes=[" + gr.className + "]") : "pas de #galRoot (jamais construit)");
  return { out, did };
})()`;

/* ── batterie « enregistrer comme modele » ──────────────────────────────────
   Jouee sur le jeu instancie a la passe precedente. Elle ne navigue pas : le
   modele doit apparaitre DANS l'ecran ouvert (un modele qui n'arrive qu'a la
   prochaine ouverture laisse croire que l'enregistrement a echoue). */
const BATTERIE_MODELE = `(async () => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const gb = document.getElementById("galleryBtn");
  if (!gb) { say("galerie : bouton present avant « enregistrer comme modele »", "OUVERT", "absent"); return { out }; }
  gb.click();
  for (let i = 0; i < 60 && document.querySelectorAll("#galModels .cf-gal-card").length === 0; i++) {
    await new Promise((r) => setTimeout(r, 200));
  }
  const avant = document.querySelectorAll("#galModels .cf-gal-card").length;
  const so = document.getElementById("galSaveOpen");
  say("galerie : « Enregistrer comme modele » est actif quand un jeu est ouvert",
      (so && so.disabled === false) ? "TENU" : "OUVERT",
      so ? ("disabled=" + so.disabled + " title=" + so.title) : "absent");
  if (!so) return { out };
  so.click();
  const form = document.getElementById("galSaveForm");
  const nm = document.getElementById("galSaveName");
  say("galerie : le nom se demande DANS l'ecran (aucun window.prompt)",
      (form && !form.classList.contains("hidden") && nm) ? "TENU" : "OUVERT",
      form ? ("classes=[" + form.className + "] champ=" + !!nm) : "pas de formulaire");
  if (!nm) return { out };
  nm.value = "Banc QA modele";
  document.getElementById("galSaveGo").click();
  let cartes = [];
  for (let i = 0; i < 80; i++) {
    await new Promise((r) => setTimeout(r, 200));
    cartes = Array.prototype.slice.call(document.querySelectorAll("#galModels .cf-gal-card"));
    if (cartes.length > avant) break;
  }
  const perso = cartes.filter((c) => {
    const t = c.querySelector(".cf-gal-tag");
    return t && t.textContent === "perso";
  });
  say("galerie : le modele enregistre est RE-LISTE tout de suite",
      (cartes.length === avant + 1 && perso.length === 1) ? "TENU" : "OUVERT",
      avant + " -> " + cartes.length + " carte(s), perso = " + perso.map((c) => c.dataset.model).join(","));
  const tst = document.getElementById("toast");
  say("galerie : l'enregistrement du modele le DIT",
      (tst && tst.textContent.indexOf("enregistré") >= 0) ? "TENU" : "OUVERT",
      tst ? tst.textContent.slice(0, 90) : "pas de toast");
  say("galerie : le formulaire se referme une fois le modele ecrit",
      (form && form.classList.contains("hidden")) ? "TENU" : "OUVERT",
      form ? ("classes=[" + form.className + "]") : "?");
  return { out, slug: perso.length ? perso[0].dataset.model : null };
})()`;

/* ── batterie « dupliquer » ────────────────────────────────────────────────
   Elle navigue elle aussi : la copie s'OUVRE. Verdicts a la passe suivante. */
const BATTERIE_DUP = `(async () => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const gb = document.getElementById("galleryBtn");
  if (!gb) { say("galerie : bouton present avant duplication", "OUVERT", "absent"); return { out }; }
  gb.click();
  await new Promise((r) => setTimeout(r, 300));
  const d = document.getElementById("galDup");
  say("galerie : « Dupliquer ce jeu » est actif quand un jeu est ouvert",
      (d && d.disabled === false) ? "TENU" : "OUVERT", d ? ("disabled=" + d.disabled) : "absent");
  const avant = CF.get("id", null);
  if (d) d.click();
  return { out, avant };
})()`;

const BATTERIE_DUPE = `(() => {
  const out = [];
  const say = (k, v, d) => out.push({ k, verdict: v, detail: String(d) });
  const did = CF.get("id", null), nom = String(CF.get("name", ""));
  say("galerie : dupliquer OUVRE la copie (?deck= pose, nom « copie de … »)",
      (did && location.search.indexOf(did) >= 0 && nom.indexOf("copie de ") === 0) ? "TENU" : "OUVERT",
      "deck=" + did + " nom=" + nom + " search=" + location.search);
  return { out, did };
})()`;

/* ── BOUCHON DE RESEAU DU BANC ──────────────────────────────────────────────
   Il ne touche PAS core.js : pose par Page.addScriptToEvaluateOnNewDocument,
   il repond a la place du backend sur DEUX routes seulement — le document
   d'un jeu (`GET /api/cards/<did>`) et la liste des jeux
   (`GET /api/cards/decks`) — et il ecrit ou efface le dernier jeu retenu.
   C'est le seul moyen d'eprouver « backend vide » et « dernier jeu supprime »
   contre un :8765 qui, lui, a des milliers de jeux bien vivants.

   `mort` distingue les DEUX 404 que le lab doit cesser de confondre, sur le
   jeu `mortId` :
     · "json" = le VRAI 404 du backend cartes ({"detail":"Deck introuvable"},
       content-type application/json) — un jeu qui n'existe plus ;
     · "html" = le catch-all SPA (200 + du HTML) — le domaine /api/cards
       n'est pas monte, et LA le lab doit passer hors ligne.
   `dernier` ecrit dz_cf_deck_id (absent = on l'efface) — le jeu mort peut
   donc etre designe par le STOCKAGE ou, sans lui, par le `?deck=` de l'URL.
   `decks` choisit ce que rend la liste : "vide", "soi" (le seul jeu present
   est celui que le boot vient de creer) ou "etranger" (un jeu d'avant). */
function stubReseau(o) {
  return `(() => {
  const O = ${JSON.stringify(o)};
  try {
    if (O.dernier) localStorage.setItem("dz_cf_deck_id", O.dernier);
    else localStorage.removeItem("dz_cf_deck_id");
    localStorage.removeItem("dz_cf_rail");
    localStorage.removeItem("dz_cf_stage");
  } catch (e) { }
  const rep = (corps, ct, code) => new Response(corps, { status: code, headers: { "content-type": ct } });
  const vrai = window.fetch;
  window.fetch = function (u, i) {
    const url = String((u && u.url) || u || "");
    const m = String((i && i.method) || (u && u.method) || "GET").toUpperCase();
    if (O.mort && O.mortId && m === "GET" && url.indexOf("/api/cards/" + O.mortId) >= 0) {
      window.__QA_MORT = (window.__QA_MORT || 0) + 1;
      if (O.mort === "html") return Promise.resolve(rep("<!doctype html><title>SPA</title><div id=root></div>", "text/html; charset=utf-8", 200));
      return Promise.resolve(rep('{"detail":"Deck introuvable"}', "application/json", 404));
    }
    if (O.decks && m === "GET" && url.indexOf("/api/cards/decks") >= 0) {
      window.__QA_DECKS = (window.__QA_DECKS || 0) + 1;
      let liste = [];
      if (O.decks === "soi") {
        liste = [{ id: (window.CF && CF.get("id", null)) || "deck_00000000",
                   name: "le jeu qui vient de naitre",
                   created: "2026-08-22T00:00:00Z", updated: "2026-08-22T00:00:00Z" }];
      } else if (O.decks === "etranger") {
        liste = [{ id: "deck_ffffffff", name: "un jeu d'avant",
                   created: "2026-08-01T00:00:00Z", updated: "2026-08-01T00:00:00Z" }];
      }
      return Promise.resolve(rep(JSON.stringify({ decks: liste }), "application/json", 200));
    }
    return vrai.apply(this, arguments);
  };
})()`;
}

/* Releve d'un DEMARRAGE, sans verdict : le harnais compare ce relevé a ce que
   chaque bouchon doit produire. Un seul releve pour six scenarios — les
   verdicts vivent en un seul endroit, la ou l'on sait ce qu'on a bouchonne. */
const RELEVE_BOOT = `(async () => {
  const fini = () => (window.__QA_DECKS || 0) > 0 || (window.__QA_MORT || 0) > 0;
  for (let i = 0; i < 45; i++) {
    const g = document.getElementById("galRoot");
    if (g && g.dataset.open === "1") break;
    if (fini() && i > 6) break;
    await new Promise((r) => setTimeout(r, 200));
  }
  await new Promise((r) => setTimeout(r, 500));
  const gr = document.getElementById("galRoot");
  const bar = document.getElementById("apiBar");
  const chip = document.getElementById("apiChip");
  const gd = document.getElementById("galDecks");
  const msg = document.getElementById("apiBarMsg");
  return {
    deck: CF.get("id", null),
    ouverte: !!(gr && !gr.classList.contains("hidden") && gr.dataset.open === "1"),
    why: gr ? String(gr.dataset.why || "") : null,
    bandeau: !!(bar && !bar.classList.contains("hidden")),
    bandeauTexte: msg ? String(msg.textContent).slice(0, 80) : "",
    chip: chip ? (chip.className + " / " + String(chip.textContent).slice(0, 60)) : "?",
    retenu: (() => { try { return localStorage.getItem("dz_cf_deck_id"); } catch (e) { return "?refus"; } })(),
    search: location.search,
    sondages: window.__QA_DECKS || 0,
    morts: window.__QA_MORT || 0,
    jeux: gd ? String(gd.textContent).slice(0, 60) : null,
  };
})()`;

async function testContract() {
  console.log('[2] cloisonnement — qa/contract.html dans un Chrome sans tete');
  if (!CHROME) { ko('Chrome introuvable (CHROME_PATH)'); return; }
  const port = await new Promise((res, rej) => { const s = createServer(); s.on('error', rej); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); });
  const profile = join(tmpdir(), 'dzcfqa', 'p' + port);
  try { rmSync(profile, { recursive: true, force: true }); } catch { }
  mkdirSync(profile, { recursive: true });
  const proc = spawn(CHROME, ['--headless=new', '--disable-gpu', '--remote-debugging-port=' + port,
    '--remote-allow-origins=*', '--user-data-dir=' + profile, '--window-size=1200,900', '--no-first-run',
    '--no-default-browser-check', '--disable-background-networking', '--disable-sync', 'about:blank'],
    { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true });
  const cleanup = () => {
    try { spawnSync('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' }); } catch { }
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 3 }); } catch { }
  };
  process.on('exit', cleanup);
  try {
    const fetchJson = async (u, tries = 80) => {
      for (let i = 0; i < tries; i++) { try { const r = await fetch(u); if (r.ok) return await r.json(); } catch { } await sleep(250); }
      throw new Error('injoignable ' + u);
    };
    await fetchJson('http://127.0.0.1:' + port + '/json/version');
    let target = null;
    for (let i = 0; i < 60 && !target; i++) {
      const list = await fetchJson('http://127.0.0.1:' + port + '/json/list', 1).catch(() => []);
      target = (list || []).find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (!target) await sleep(200);
    }
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener('open', res, { once: true }); ws.addEventListener('error', rej, { once: true }); });
    let id = 0; const pend = new Map();
    ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    await send('Page.enable'); await send('Runtime.enable');
    await send('Page.navigate', { url: URL_ });
    await sleep(3000);
    const r = await send('Runtime.evaluate', { expression: BATTERIE, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) { ko('la batterie a leve : ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text).slice(0, 400)); return; }
    const { deck, out } = r.result.value;
    /* Tous les jeux que le banc fait naitre, quel que soit le chemin : celui
       du boot, celui de l'instanciation d'un modele, celui du « premier
       lancement ». Ils sont supprimes a la fin, sans exception. */
    const bancs = new Set();
    if (deck) bancs.add(deck);
    const imprime = (rows) => {
      for (const row of rows) {
        const line = `${row.k} — ${row.detail.slice(0, 110)}`;
        if (row.verdict === 'TENU') ok(line);
        else if (row.verdict === 'NOTE') console.log('  note ' + line);
        else ko(line);
      }
    };
    imprime(out);

    /* ── passe « instancier » : la galerie cree un jeu depuis « superstar » et
       la page bascule dessus. Le clic part ici, les verdicts se lisent apres
       le rechargement. */
    const rs = await send('Runtime.evaluate', { expression: BATTERIE_SEMER, awaitPromise: true, returnByValue: true });
    if (rs.exceptionDetails) ko('la batterie « instancier » a leve : ' + JSON.stringify(rs.exceptionDetails.exception && rs.exceptionDetails.exception.description || rs.exceptionDetails.text).slice(0, 400));
    else {
      imprime(rs.result.value.out);
      await sleep(5000);
      const rs2 = await send('Runtime.evaluate', { expression: BATTERIE_SEME, returnByValue: true });
      if (rs2.exceptionDetails) ko('la relecture « instancier » a leve : ' + JSON.stringify(rs2.exceptionDetails.exception && rs2.exceptionDetails.exception.description || rs2.exceptionDetails.text).slice(0, 400));
      else {
        imprime(rs2.result.value.out);
        const neuf = rs2.result.value.did;
        if (neuf && neuf !== deck) bancs.add(neuf);
        /* CONTRE-EXPERTISE COTE SERVEUR : le banc a un SCHEMA de type reduit
           (`state: {slots: []}` de qa/mod-type.js), donc `preset` est ecarte
           a l'hydratation et le navigateur ne peut pas le prouver. Le
           document sur le disque, lui, le porte. */
        if (neuf) {
          try {
            const d = await (await fetch(new URL('/api/cards/' + neuf, URL_).href)).json();
            const t = (d && d.deck && d.deck.type) || {};
            const n = Array.isArray(t.slots) ? t.slots.length : -1;
            if (t.preset === 'superstar' && n === 12 && t.seeded === true)
              ok(`galerie : le jeu cree porte le modele SUR LE DISQUE — preset=${t.preset} slots=${n} seeded=${t.seeded}`);
            else ko(`galerie : le jeu cree ne porte pas le modele — preset=${t.preset} slots=${n} seeded=${t.seeded}`);
          } catch (e) { ko('galerie : relecture serveur du jeu instancie impossible — ' + e.message); }
        }
      }
    }

    /* ── passe « enregistrer comme modele » : seulement si le backend sait
       reprendre ce qu'elle ecrit. On le lui demande AVANT de salir : un
       DELETE sur un modele qui n'existe pas doit repondre 404 (la route est
       la), et non 405 / du HTML (elle n'y est pas). */
    let peutNettoyer = false;
    try {
      const sonde = await fetch(new URL('/api/cards/models/banc-qa-inexistant', URL_).href, { method: 'DELETE' });
      peutNettoyer = sonde.status === 404
        && (sonde.headers.get('content-type') || '').toLowerCase().indexOf('json') >= 0;
    } catch { }
    if (peutNettoyer) {
      const rm = await send('Runtime.evaluate', { expression: BATTERIE_MODELE, awaitPromise: true, returnByValue: true });
      if (rm.exceptionDetails) ko('la batterie « enregistrer comme modele » a leve : ' + JSON.stringify(rm.exceptionDetails.exception && rm.exceptionDetails.exception.description || rm.exceptionDetails.text).slice(0, 400));
      else {
        imprime(rm.result.value.out);
        const slug = rm.result.value.slug;
        if (slug) {
          let r = null;
          try { r = await fetch(new URL('/api/cards/models/' + slug, URL_).href, { method: 'DELETE' }); } catch (e) { }
          if (r && r.ok) console.log('  --   modele de banc ' + slug + ' supprime (DELETE /models/' + slug + ')');
          else ko('modele de banc ' + slug + ' non supprime — ' + (r ? r.status + ' ' + r.statusText : 'requete impossible'));
        }
      }
    } else {
      console.log('  note galerie : « enregistrer comme modele » non joue — DELETE /api/cards/models/{id} absent de ce backend');
    }

    /* ── passe « dupliquer » : la copie s'ouvre, donc la page part. */
    const rd = await send('Runtime.evaluate', { expression: BATTERIE_DUP, awaitPromise: true, returnByValue: true });
    if (rd.exceptionDetails) ko('la batterie « dupliquer » a leve : ' + JSON.stringify(rd.exceptionDetails.exception && rd.exceptionDetails.exception.description || rd.exceptionDetails.text).slice(0, 400));
    else {
      imprime(rd.result.value.out);
      await sleep(5000);
      const rd2 = await send('Runtime.evaluate', { expression: BATTERIE_DUPE, returnByValue: true });
      if (rd2.exceptionDetails) ko('la relecture « dupliquer » a leve : ' + JSON.stringify(rd2.exceptionDetails.exception && rd2.exceptionDetails.exception.description || rd2.exceptionDetails.text).slice(0, 400));
      else {
        imprime(rd2.result.value.out);
        const copie = rd2.result.value.did;
        if (copie && copie !== rd.result.value.avant) { bancs.add(copie); ok('galerie : la copie porte un identifiant NEUF — ' + rd.result.value.avant + ' -> ' + copie); }
        else ko('galerie : la copie n\'a pas d\'identifiant neuf — ' + rd.result.value.avant + ' -> ' + copie);
      }
    }

    /* ── seconde passe : le repli est-il applique AU BOOT ? On ecrit les deux
       cles, on RECHARGE la meme page (le jeu est rouvert par dz_cf_deck_id,
       aucun deck de plus sur le disque) et on relit les classes. */
    await send('Runtime.evaluate', {
      expression: "(() => { try { localStorage.setItem('dz_cf_rail','1'); localStorage.setItem('dz_cf_stage','1'); } catch (e) { } return 1; })()",
      returnByValue: true,
    });
    await send('Page.navigate', { url: URL_ });
    await sleep(3000);
    const r2 = await send('Runtime.evaluate', { expression: BATTERIE_REPLI, awaitPromise: true, returnByValue: true });
    if (r2.exceptionDetails) ko('la batterie « repli au boot » a leve : ' + JSON.stringify(r2.exceptionDetails.exception && r2.exceptionDetails.exception.description || r2.exceptionDetails.text).slice(0, 400));
    else imprime(r2.result.value.out);

    /* ── SIX DEMARRAGES BOUCHONNES ──────────────────────────────────────────
       Un bouchon se pose AVANT le document, la page est rechargee, on releve
       l'etat, on retire le bouchon. Ce que ces six scenarios separent :
         · ce qui OUVRE la galerie de demarrage (rien a reprendre) ;
         · ce qui ne l'ouvre PAS (il y a un jeu d'avant) ;
         · les deux 404 que le lab confondait — un jeu SUPPRIME (JSON) n'est
           pas un domaine ABSENT (HTML), et seul le second est « hors ligne ».
       Sans le scenario "soi", l'exclusion « aucun jeu AUTRE que celui qu'on
       vient de creer » restait vacueusement verte : une liste vide passe la
       condition quelle que soit l'exclusion.

       LE BANDEAU N'EST PAS UN SIGNAL SUR CE BANC : `auditStrict` l'allume a
       CHAQUE demarrage pour qa/mod-solid.js (mode bâclé, c'est son role) et
       ecrase le message « hors ligne » pose juste avant. Ce qui distingue
       vraiment les deux etats, c'est la PUCE de la barre (`chip("ok"|"ko")`,
       le texte que l'utilisateur lit) et l'existence REELLE du jeu sur le
       backend — verifiee ici depuis Node, hors du navigateur. */
    const boot = async (titre, o, url) => {
      const s = await send('Page.addScriptToEvaluateOnNewDocument', { source: stubReseau(o) });
      await send('Page.navigate', { url: url || URL_ });
      await sleep(3000);
      const rr = await send('Runtime.evaluate', { expression: RELEVE_BOOT, awaitPromise: true, returnByValue: true });
      try { await send('Page.removeScriptToEvaluateOnNewDocument', { identifier: s.identifier }); } catch { }
      if (rr.exceptionDetails) {
        ko('releve « ' + titre + ' » : la batterie a leve — ' + JSON.stringify(rr.exceptionDetails.exception && rr.exceptionDetails.exception.description || rr.exceptionDetails.text).slice(0, 300));
        return null;
      }
      const v = rr.result.value;
      /* le jeu existe-t-il VRAIMENT ? Hors ligne, `boot` se donne un
         identifiant au hasard (`randDid`) qui ressemble a tout sauf a un jeu
         du disque : seule cette lecture le distingue. */
      v.surDisque = false;
      if (v.deck && DID_RE_QA.test(v.deck)) {
        try { v.surDisque = (await fetch(new URL('/api/cards/' + v.deck, URL_).href)).ok; } catch { }
        if (v.surDisque) bancs.add(v.deck);
      }
      return v;
    };
    const dit = (v) => 'galerie=' + (v.ouverte ? 'OUVERTE(' + v.why + ')' : 'fermee')
      + ' chip=[' + v.chip + '] deck=' + v.deck + ' surDisque=' + v.surDisque
      + ' retenu=' + v.retenu + ' sondages=' + v.sondages + ' morts=' + v.morts;

    const vVide = await boot('backend vide', { decks: 'vide' });
    if (vVide) {
      if (vVide.ouverte && vVide.why === 'premier lancement' && vVide.sondages > 0)
        ok('galerie : backend SANS jeu -> elle s\'ouvre toute seule et dit pourquoi — ' + dit(vVide));
      else ko('galerie : backend SANS jeu -> elle devait s\'ouvrir — ' + dit(vVide));
      if (vVide.jeux && vVide.jeux.indexOf('aucun jeu') >= 0)
        ok('galerie : un backend vide le DIT, la liste ne reste pas blanche — ' + vVide.jeux);
      else ko('galerie : un backend vide devait le dire — ' + vVide.jeux);
    }

    /* NON VACUEUX : la liste contient EXACTEMENT le jeu que le boot vient de
       creer. C'est encore un premier lancement — l'exclusion doit le voir. */
    const vSoi = await boot('le seul jeu est celui qu\'on vient de creer', { decks: 'soi' });
    if (vSoi) {
      if (vSoi.ouverte && vSoi.sondages > 0)
        ok('galerie : le SEUL jeu liste est celui que le boot vient de creer -> elle s\'ouvre quand meme — ' + dit(vSoi));
      else ko('galerie : le SEUL jeu liste est celui que le boot vient de creer -> elle devait s\'ouvrir quand meme — ' + dit(vSoi));
    }

    /* et le pendant : un jeu ETRANGER dans la liste = il y a du travail. */
    const vEtr = await boot('un jeu d\'avant', { decks: 'etranger' });
    if (vEtr) {
      if (!vEtr.ouverte && vEtr.sondages > 0)
        ok('galerie : un jeu ETRANGER dans la liste -> elle ne s\'ouvre pas — ' + dit(vEtr));
      else ko('galerie : un jeu ETRANGER dans la liste -> elle devait rester fermee — ' + dit(vEtr));
    }

    /* ── LE 404 NOMME : un dernier jeu SUPPRIME n'est pas un backend absent.
       Le lab doit creer un jeu neuf, RESTER en ligne, ne pas mentir dans le
       bandeau, reecrire dz_cf_deck_id, et le sondage de premier lancement
       doit JOUER. */
    const vMort = await boot('dernier jeu supprime (404 JSON)',
      { dernier: 'deck_deadbeef', mortId: 'deck_deadbeef', mort: 'json', decks: 'vide' });
    if (vMort) {
      const neuf = !!(vMort.surDisque && vMort.deck !== 'deck_deadbeef');
      if (neuf && vMort.chip.indexOf('ok') >= 0 && vMort.morts > 0)
        ok('deck : un 404 NOMME (jeu supprime) cree un jeu neuf sans passer hors ligne — ' + dit(vMort));
      else ko('deck : un 404 NOMME a ete pris pour un domaine absent — ' + dit(vMort));
      if (vMort.retenu === vMort.deck)
        ok('deck : dz_cf_deck_id est REECRIT sur le jeu neuf (le mort ne survit pas au rechargement) — retenu=' + vMort.retenu);
      else ko('deck : dz_cf_deck_id garde un jeu mort — retenu=' + vMort.retenu + ' deck=' + vMort.deck);
      if (vMort.ouverte && vMort.why === 'premier lancement' && vMort.sondages > 0)
        ok('deck : apres un jeu mort, le sondage de premier lancement JOUE — ' + dit(vMort));
      else ko('deck : apres un jeu mort, le sondage n\'a jamais ete atteint — ' + dit(vMort));
    }

    /* ── LE MEME JEU MORT, MAIS DANS L'URL. `?deck=` PRIME sur dz_cf_deck_id :
       reecrire la cle de stockage ne suffit pas. Une URL restee sur un jeu
       supprime referait un jeu de plus a CHAQUE rechargement — la fuite que
       l'en-tete d'openDeck decrit. L'URL doit donc designer le jeu
       reellement ouvert quand la page a fini de demarrer. */
    const urlMorte = (() => { const u = new URL(URL_); u.searchParams.set('deck', 'deck_deadbeef'); return u.href; })();
    const vUrl = await boot('?deck= vers un jeu supprime',
      { mortId: 'deck_deadbeef', mort: 'json', decks: 'vide' }, urlMorte);
    if (vUrl) {
      if (vUrl.surDisque && vUrl.chip.indexOf('ok') >= 0 && vUrl.morts > 0)
        ok('deck : un ?deck= vers un jeu supprime cree un jeu neuf sans passer hors ligne — ' + dit(vUrl));
      else ko('deck : un ?deck= mort a ete pris pour un domaine absent — ' + dit(vUrl));
      if (vUrl.search.indexOf(vUrl.deck) >= 0 && vUrl.search.indexOf('deck_deadbeef') < 0)
        ok('deck : l\'URL ne designe plus le jeu mort (aucun jeu de plus au prochain rechargement) — search=' + vUrl.search);
      else ko('deck : l\'URL garde le jeu mort, chaque rechargement en creera un de plus — search=' + vUrl.search);
    }

    /* ── ET LE VRAI DOMAINE ABSENT (catch-all SPA : 200 + du HTML) : celui-la
       DOIT passer hors ligne, avec son bandeau. Sans ce pin, « ne plus
       confondre » se reglerait en ne detectant plus rien. */
    const vHtml = await boot('domaine /api/cards absent (200 + HTML)',
      { dernier: 'deck_deadbeef', mortId: 'deck_deadbeef', mort: 'html' });
    if (vHtml) {
      if (vHtml.chip.indexOf('ko') >= 0 && vHtml.chip.indexOf('hors ligne') >= 0
          && !vHtml.surDisque && !vHtml.ouverte && vHtml.morts > 0)
        ok('deck : le catch-all SPA (HTML) reste « hors ligne » et ne cree AUCUN jeu — ' + dit(vHtml));
      else ko('deck : un domaine absent doit passer hors ligne — ' + dit(vHtml));
    }

    /* le banc a ouvert des jeux : on ne laisse rien derriere */
    for (const d of bancs) {
      try { await fetch(new URL('/api/cards/' + d, URL_).href, { method: 'DELETE' }); console.log('  --   jeu de banc ' + d + ' supprime'); }
      catch { console.log('  --   jeu de banc ' + d + ' : suppression impossible'); }
    }
  } finally { cleanup(); }
}

/* ── pilote ─────────────────────────────────────────────────────────────── */
console.log('== test_core_contract — ' + CORE);
if (doGeom) testGeom();
if (doContract) await testContract();
console.log(failures ? `\nKO — ${failures} violation(s) du contrat.` : '\nOK — contrat tenu.');
process.exit(failures ? 1 : 0);
