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
    say("layers : modes avoues", "TENU", L.layers.map((l) => l.role + "=" + l.mode).join(" "));
    try { const lb = await CF.layerBlob(L.layers[0].canvas); CF.download(lb, "couche_qa.png");
          say("layers : blob de couche MINTE accepte par CF.download", "TENU", lb.size + " o"); }
    catch (e) { say("layers : blob de couche MINTE accepte par CF.download", "OUVERT", e.message); }
  } catch (e) { say("layers", "OUVERT", e.message); }

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
    for (const row of out) {
      const line = `${row.k} — ${row.detail.slice(0, 110)}`;
      if (row.verdict === 'TENU') ok(line);
      else if (row.verdict === 'NOTE') console.log('  note ' + line);
      else ko(line);
    }
    /* le banc a ouvert un jeu : on ne laisse rien derriere */
    if (deck) {
      try { await fetch(new URL('/api/cards/' + deck, URL_).href, { method: 'DELETE' }); console.log('  --   jeu de banc ' + deck + ' supprime'); }
      catch { console.log('  --   jeu de banc ' + deck + ' : suppression impossible'); }
    }
  } finally { cleanup(); }
}

/* ── pilote ─────────────────────────────────────────────────────────────── */
console.log('== test_core_contract — ' + CORE);
if (doGeom) testGeom();
if (doContract) await testContract();
console.log(failures ? `\nKO — ${failures} violation(s) du contrat.` : '\nOK — contrat tenu.');
process.exit(failures ? 1 : 0);
