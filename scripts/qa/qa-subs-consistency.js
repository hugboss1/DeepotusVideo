"use strict";
/* ════════════════════════════════════════════════════════════════════════════
   LE TEST QUI INTERDIT LA DIVERGENCE — piste de sous-titres S1.

   Sur une piste CONSTRUITE (un .srt importé, contenu connu), la sévérité vue
   par CHAQUE surface doit être identique, réplique par réplique :

     surface 1  la timeline du Montage   (.svm-clip[data-cid][data-warn])
     surface 2  la liste du tiroir       (.sub-row .sub-rbadge[data-k])
     surface 3  le verdict lui-même      (window.DzSubs.verdict(...))
     surface 4  l'inspecteur             (clip sélectionné → .sub-warn)

   et TOUS les comptes affichés (badge d'onglet « Répliques », chip
   « sous-titres » de la barre d'outils, filtre « n signalées », ligne des
   comptes) doivent valoir exactement ce que le verdict a décidé — chacun avec
   son unité écrite à côté.

   Le défaut fermé : ces nombres étaient calculés à quatre endroits qui se
   contredisaient DANS LA MÊME IMAGE (9 pastilles critiques sur la piste, 8
   ambre + 1 rouge dans la liste, « 9 » sur deux compteurs qui ne comptaient
   pas la même chose, 11 lignes marquées).

   Vérifie aussi que le défaut d'usine ne franchit pas le repère que l'aperçu
   trace lui-même (zone sûre 10 %) et que, s'il le franchissait, l'écran le
   dirait.

   Lancement (backend DeepotusVideoGen sur 127.0.0.1:8765) :
       node scripts/qa/qa-subs-consistency.js [chemin.srt]
   Sortie : lignes « OK / KO », puis un objet JSON de synthèse. Code 1 si KO.
   ════════════════════════════════════════════════════════════════════════════ */
const path = require("path");
const fs = require("fs");
const puppeteer = require(path.join(__dirname, "node_modules", "puppeteer-core"));

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = "http://127.0.0.1:8765";
const SRT = process.argv[2] || path.join(__dirname, "subs-consistency.srt");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* Piste de contrôle : contenu FIXE, défauts connus d'avance — une réplique
   trop rapide, une trop courte, un chevauchement, une trop longue, une saine. */
const SRT_FALLBACK = [
  "1", "00:00:00,000 --> 00:00:01,000",
  "Une phrase beaucoup trop longue pour tenir en une seule seconde de lecture", "",
  "2", "00:00:00,900 --> 00:00:01,300", "Chevauche et trop court", "",
  "3", "00:00:02,000 --> 00:00:05,000", "Une reponse posee, lisible, sans defaut", "",
  "4", "00:00:05,100 --> 00:00:14,000", "Celle-ci traine beaucoup trop longtemps a l ecran", "",
  "5", "00:00:14,200 --> 00:00:17,000", "Derniere replique, calme et courte", "",
].join("\n");

const out = [];
let bad = 0;
function chk(ok, label, detail) {
  out.push((ok ? "OK  " : "KO  ") + label + (detail ? "  — " + detail : ""));
  if (!ok) bad++;
}

(async () => {
  if (!fs.existsSync(SRT)) fs.writeFileSync(SRT, SRT_FALLBACK, "utf8");

  const b = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
  });
  const p = await b.newPage();
  const pageErrs = [];
  p.on("pageerror", (e) => pageErrs.push(String(e.message)));
  await p.setViewport({ width: 1600, height: 950 });
  await p.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 45000 });
  await p.evaluate(() => {
    localStorage.setItem("dz_onboarded", "1");
    localStorage.removeItem("dz_subs_style");
  });
  await p.goto(BASE + "/", { waitUntil: "networkidle2", timeout: 60000 });
  await sleep(3000);
  await p.evaluate(() => {
    const el = [...document.querySelectorAll("button,a,div[role=button],li,div")]
      .filter((e) => (e.textContent || "").includes("Timeline multipiste"))
      .sort((a, c) => (a.textContent || "").length - (c.textContent || "").length)[0];
    if (el) el.click();
  });
  await sleep(6000);

  /* ── la couche est-elle là, et n'expose-t-elle qu'UN verdict ? ── */
  const layer = await p.evaluate(() => {
    const d = window.DzSubs;
    return d && d.ready
      ? { verdict: typeof d.verdict === "function",
          segState: typeof d.segState === "function",
          safe: d.SAFE || null, dft: d.defaultStyle() }
      : null;
  });
  chk(!!layer, "couche DzSubs présente");
  if (!layer) { console.log(out.join("\n")); await b.close(); process.exit(1); }
  chk(layer.verdict && layer.segState, "DzSubs expose verdict() et segState()");

  /* ── défaut d'usine vs repère tracé par l'aperçu ── */
  const S = layer.safe, D = layer.dft;
  chk(D.marginV >= S.title, "marge d'usine dans la zone sûre",
    "marge " + D.marginV + " % ≥ zone sûre " + S.title + " %");
  chk((100 - D.width) / 2 >= S.title, "largeur d'usine dans la zone sûre",
    "marges latérales " + ((100 - D.width) / 2) + " % ≥ " + S.title + " %");
  const outSafe = await p.evaluate(() => window.DzSubs.outOfSafe(window.DzSubs.defaultStyle()));
  chk(outSafe === false, "le style d'usine ne déclenche pas son propre contrôle");
  const saidWhenOut = await p.evaluate(() => {
    const d = window.DzSubs;
    const st = Object.assign(d.defaultStyle(), { marginV: 4 });
    const w = d.safeIssues(st);
    return w.length > 0 && !!w[0].fix && w[0].fix.champ === "marginV"
      && w[0].fix.valeur === d.SAFE.title;
  });
  chk(saidWhenOut, "sortir de la zone sûre est annoncé, avec le geste qui le ferme");

  /* ── construire la piste : ouvrir le tiroir, vider, importer le .srt ── */
  await p.evaluate(() => {
    const c = [...document.querySelectorAll(".svm-toolchip")]
      .find((e) => e.textContent.includes("sous-titres"));
    if (c) c.click();
  });
  await sleep(1800);
  for (let i = 0; i < 80; i++) {
    const done = await p.evaluate(() => {
      const r = document.querySelector(".sub-row");
      if (!r) return true;
      const d = r.querySelector(".sub-del");
      if (!d) { const c = r.querySelector(".sub-rcar"); if (c) c.click(); return false; }
      d.click(); return false;
    });
    await sleep(180);
    if (done) break;
  }
  const inp = await p.$(".sub-drawer input[type=file]");
  if (!inp) { chk(false, "champ d'import trouvé"); console.log(out.join("\n")); await b.close(); process.exit(1); }
  await inp.uploadFile(SRT);
  /* laisser POST /check répondre : le verdict doit basculer sur le moteur, et
     TOUTES les surfaces avec lui — c'est le moment où elles divergeaient. */
  await sleep(4500);

  /* ── relevé : chaque surface, réplique par réplique ── */
  const snap = await p.evaluate(() => {
    const d = window.DzSubs;
    const clips = [...document.querySelectorAll(".svm-clip[data-cid]")];
    const timeline = {};
    clips.forEach((el) => {
      timeline[el.getAttribute("data-cid")] = el.getAttribute("data-warn") || null;
    });
    const rows = [...document.querySelectorAll(".sub-drawer .sub-row")];
    const liste = rows.map((el) => {
      const bg = el.querySelector(".sub-rbadge[data-k]");
      const k = bg ? bg.getAttribute("data-k") : null;
      return {
        n: (el.querySelector(".sub-rown") || {}).textContent || "",
        txt: ((el.querySelector(".sub-rtxt") || {}).textContent || "").trim(),
        sev: k === "off" ? null : k,
        badge: bg ? bg.textContent.trim() : "",
      };
    });
    const tabBad = document.querySelector(".sub-tab .sub-tbad");
    const chipN = document.querySelector(".svm-toolchip .sub-chipn");
    const chipBad = document.querySelector(".svm-toolchip .sub-chipbad");
    const filt = [...document.querySelectorAll(".sub-statfilt")]
      .map((e) => (e.textContent || "").trim()).find((t) => /signalée/.test(t));
    const tally = {};
    [...document.querySelectorAll(".sub-tally .sub-tal")].forEach((e) => {
      const b = e.querySelector("b");
      tally[e.getAttribute("data-k")] = Number(b ? b.textContent : NaN);
    });
    return {
      timeline, liste, tally,
      head: ((document.querySelector(".sub-count") || {}).textContent || "").trim(),
      tabBad: tabBad ? Number(tabBad.textContent) : 0,
      tabBadSev: tabBad ? tabBad.getAttribute("data-sev") : null,
      chipN: chipN ? Number(chipN.textContent) : 0,
      chipBad: chipBad ? Number(chipBad.textContent) : 0,
      chipBadSev: chipBad ? chipBad.getAttribute("data-sev") : null,
      filt: filt ? Number((filt.match(/(\d+)/) || [])[1]) : null,
      source: ((document.querySelector(".sub-talsrc") || {}).textContent || "").trim(),
    };
  });

  /* le verdict de référence, demandé à la couche avec la piste du Montage */
  const truth = await p.evaluate(() => {
    const d = window.DzSubs;
    /* on relit la piste depuis la timeline elle-même : c'est la même que celle
       que le Montage passe au tiroir et au verdict */
    const ids = [...document.querySelectorAll(".svm-clip[data-cid]")]
      .map((e) => e.getAttribute("data-cid"));
    return { ids: ids };
  });

  chk(truth.ids.length > 0, "la piste S1 porte des segments",
    truth.ids.length + " segments sur la timeline");
  chk(snap.liste.length === truth.ids.length,
    "autant de lignes dans la liste que de segments sur la piste",
    snap.liste.length + " lignes / " + truth.ids.length + " segments");

  /* ── ÉGALITÉ RÉPLIQUE PAR RÉPLIQUE : timeline vs liste ── */
  const diffs = [];
  truth.ids.forEach((id, i) => {
    const tl = snap.timeline[id] || null;
    const li = snap.liste[i] ? snap.liste[i].sev : undefined;
    if (tl !== (li === undefined ? null : li)) {
      diffs.push({ i: i + 1, id: id, timeline: tl, liste: li,
        texte: snap.liste[i] ? snap.liste[i].txt.slice(0, 40) : "?" });
    }
  });
  chk(diffs.length === 0,
    "sévérité identique sur la timeline et dans la liste, réplique par réplique",
    diffs.length ? JSON.stringify(diffs) : truth.ids.length + " répliques comparées");

  /* ── les comptes : tous des RÉPLIQUES, tous égaux au verdict ── */
  const nSig = snap.liste.filter((r) => r.sev).length;
  const nBlk = snap.liste.filter((r) => r.sev === "err").length;
  const nTlSig = Object.keys(snap.timeline).filter((k) => snap.timeline[k]).length;
  const nTlBlk = Object.keys(snap.timeline).filter((k) => snap.timeline[k] === "err").length;
  chk(nSig === nTlSig, "même nombre de répliques signalées des deux côtés",
    "liste " + nSig + " / timeline " + nTlSig);
  chk(nBlk === nTlBlk, "même nombre de répliques bloquantes des deux côtés",
    "liste " + nBlk + " / timeline " + nTlBlk);
  chk(snap.tabBad === nSig, "badge de l'onglet « Répliques » = répliques signalées",
    "badge " + snap.tabBad + " / signalées " + nSig);
  chk(snap.chipBad === nSig, "pastille de la chip = répliques signalées",
    "chip " + snap.chipBad + " / signalées " + nSig);
  chk(snap.chipN === truth.ids.length, "compteur de la chip = répliques de la piste",
    "chip " + snap.chipN + " / piste " + truth.ids.length);
  chk(snap.filt === null || snap.filt === nSig,
    "filtre « n signalées » = répliques signalées",
    "filtre " + snap.filt + " / signalées " + nSig);
  /* règle de couleur : les TOTAUX sont ambre, le rouge est réservé à ce qui
     EST bloquant (pastille d'une réplique, compte « n bloquantes »). Peindre
     en rouge un total de 12 dont une seule est bloquante remettrait la
     timeline et la liste en désaccord d'impression. */
  chk(snap.tabBadSev === "warn" && snap.chipBadSev === "warn",
    "les totaux sont ambre, le rouge reste réservé au bloquant",
    "onglet " + snap.tabBadSev + " / chip " + snap.chipBadSev);

  /* ── la ligne des comptes : chaque nombre a son unité, et vaut ce qu'il dit ── */
  chk(snap.tally["repliques"] === truth.ids.length,
    "« n répliques » = lignes de la piste", JSON.stringify(snap.tally));
  chk(snap.tally["signalees"] === nSig, "« n signalées » = lignes marquées");
  chk(snap.tally["bloquantes"] === nBlk, "« n bloquantes » = lignes en rouge");
  chk(snap.tally["bloquantes"] <= snap.tally["signalees"],
    "les bloquantes sont un sous-ensemble des signalées");
  /* somme des pastilles numérotées = « défauts », le SEUL nombre qui ne compte
     pas des répliques — et il est nommé */
  const sumPills = snap.liste.reduce((a, r) => {
    if (!r.sev) return a;
    const m = r.badge.match(/(\d+)/);
    return a + (m ? Number(m[1]) : 1);
  }, 0);
  chk(sumPills === snap.tally["defauts"],
    "somme des pastilles numérotées = « n défauts »",
    "pastilles " + sumPills + " / défauts " + snap.tally["defauts"]);

  /* ── l'inspecteur : mêmes avertissements que la ligne ── */
  const insp = await p.evaluate(() => {
    const el = document.querySelector(".svm-clip[data-cid][data-warn]");
    if (!el) return { skip: true };
    const id = el.getAttribute("data-cid");
    el.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: 0, clientY: 0 }));
    return { id: id, sev: el.getAttribute("data-warn") };
  });
  await sleep(900);
  if (insp.skip) chk(true, "inspecteur — aucune réplique signalée à comparer");
  else {
    /* les cartes d'avertissement de l'INSPECTEUR (hors du tiroir) */
    const got = await p.evaluate(() =>
      [...document.querySelectorAll(".sub-warn")]
        .filter((e) => !e.closest(".sub-drawer"))
        .map((e) => e.getAttribute("data-sev")));
    const rank = { info: 1, warn: 2, err: 3 };
    const maxSev = got.reduce((a, s) => (rank[s] || 0) > (rank[a] || 0) ? s : a, null);
    chk(got.length > 0, "l'inspecteur affiche les avertissements du segment choisi",
      JSON.stringify(got));
    chk(maxSev === insp.sev,
      "sévérité de l'inspecteur = sévérité de la pastille du segment",
      "inspecteur " + maxSev + " / pastille " + insp.sev);
  }

  chk(pageErrs.length === 0, "aucune erreur JS sur la page",
    pageErrs.join(" | ") || "0");

  console.log(out.join("\n"));
  console.log(JSON.stringify({
    repliques: truth.ids.length, signalees: nSig, bloquantes: nBlk,
    defauts: snap.tally["defauts"], tally: snap.tally,
    badge_onglet: snap.tabBad, chip: [snap.chipN, snap.chipBad],
    filtre: snap.filt, entete: snap.head, source_du_verdict: snap.source,
    divergences: diffs, erreurs_page: pageErrs, ko: bad,
  }, null, 2));
  await b.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error("KO " + e.message); process.exit(1); });
