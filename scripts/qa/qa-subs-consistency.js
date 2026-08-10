"use strict";
/* ════════════════════════════════════════════════════════════════════════════
   LE TEST QUI INTERDIT LA DIVERGENCE — piste de sous-titres S1.

   Sur une piste CONSTRUITE (un .srt importé, contenu connu), la sévérité vue
   par CHAQUE surface doit être identique, réplique par réplique :

     surface 1  la timeline du Montage   (.svm-clip[data-cid][data-warn])
     surface 2  la liste du tiroir       (.sub-row .sub-rbadge[data-k])
     surface 3  le verdict lui-même      (window.DzSubs.verdict(...))
     surface 4  l'inspecteur             (clip sélectionné → .sub-warn)

   et TOUS les comptes affichés (chip « sous-titres » de la barre d'outils,
   ligne des comptes) doivent valoir exactement ce que le verdict a décidé —
   chacun avec son unité écrite à côté.

   Le défaut fermé : ces nombres étaient calculés à quatre endroits qui se
   contredisaient DANS LA MÊME IMAGE (9 pastilles critiques sur la piste, 8
   ambre + 1 rouge dans la liste, « 9 » sur deux compteurs qui ne comptaient
   pas la même chose, 11 lignes marquées).

   ── TOUR 4 : trois gardes de plus ──────────────────────────────────────────
   A. UN NOMBRE COLLÉ À UN MOT COMPTE CE QUE CE MOT NOMME, ou il porte son
      propre libellé — et il doit pouvoir se vérifier À L'ÉCRAN. L'onglet
      affichait « Répliques 12 » sur une piste de 13 répliques, et « Style et
      placement 2 » sans que rien d'affiché ne produise ce 2. On interdit donc
      tout chiffre dans les onglets, l'en-tête et les filtres : la ligne des
      comptes est le seul domicile d'un nombre agrégé, et chacun de ses nombres
      doit être reproductible en comptant des éléments du DOM.
   B. AUCUNE REDITE : « 12 signalées » était écrit trois fois dans une bande de
      60 px. Un couple « nombre + mot » n'apparaît qu'une fois dans la bande.
   C. LA COUVERTURE est un fait affiché : la part du montage réellement
      sous-titrée, les plans qui ne le sont pas (dans le panneau ET sur la
      timeline), et le geste qui les traite.

   Vérifie aussi que le défaut d'usine ne franchit pas le repère que l'aperçu
   trace lui-même (zone sûre 10 %) et que, s'il le franchissait, l'écran le
   dirait ; et qu'un réglage que la gravure ignore (le contour sous un fond,
   mesuré) n'affiche AUCUNE valeur vivante.

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
  /* ÉTAT NEUTRE : les acquittements « sans parole » vivent sur les clips, donc
     ils se sauvegardent avec le montage. Une passe précédente ne doit pas
     teinter les chiffres de celle-ci. */
  for (let i = 0; i < 4; i++) {
    const reste = await p.evaluate(() => {
      const r = [...document.querySelectorAll(".sub-covign button")]
        .find((e) => /révoquer/i.test(e.textContent || ""));
      if (!r) return false;
      r.click(); return true;
    });
    await sleep(1200);
    if (!reste) break;
  }
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
  /* TOUR 7 : la couverture RÉSUME son diagnostic par défaut et replie ses
     lignes de plan (elles mangeaient les 276 px du corps et la liste des
     répliques n'apparaissait plus du tout). Les gardes C et E ci-dessous
     portent sur ces lignes-là : on déplie l'atelier pour les mesurer. L'état
     PAR DÉFAUT, lui, est mesuré par la garde G, après un aller-retour
     d'onglet qui remet le pli à zéro. */
  await p.evaluate(() => {
    const m = document.querySelector(".sub-drawer .sub-covmore");
    if (m && !document.querySelector(".sub-drawer .sub-plan")) m.click();
  });
  await sleep(1200);

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
    const tallyTxt = {};
    [...document.querySelectorAll(".sub-tally .sub-tal")].forEach((e) => {
      const b = e.querySelector("b");
      const k = e.getAttribute("data-k");
      tally[k] = Number(String(b ? b.textContent : "").replace(/[^\d.-]/g, ""));
      tallyTxt[k] = (e.textContent || "").trim();
    });
    /* ── la BANDE : en-tête + comptes + onglets + barre de recherche. C'est
       là que trois « 12 signalées » cohabitaient. ── */
    const band = [".sub-head", ".sub-tally", ".sub-tabs", ".sub-searchrow"]
      .map((s) => document.querySelector(".sub-drawer " + s))
      .filter(Boolean);
    /* tout couple « nombre + mot » de la bande, normalisé */
    const couples = [];
    band.forEach((el) => {
      const t = (el.innerText || "").replace(/\s+/g, " ");
      (t.match(/(\d+(?:[.,]\d+)?)\s*%?\s*([A-Za-zÀ-ÿ]+)/g) || [])
        .forEach((m) => couples.push(m.trim().toLowerCase()));
    });
    return {
      timeline, liste, tally, tallyTxt, couples,
      head: ((document.querySelector(".sub-count") || {}).textContent || "").trim(),
      /* les onglets ne portent plus de nombre : un point de sévérité, rien de
         plus. Tout chiffre qui reviendrait ici serait un badge qui se trompe
         sur ce que son mot nomme. */
      tabTxt: [...document.querySelectorAll(".sub-drawer .sub-tab")]
        .map((e) => (e.textContent || "").trim()),
      tabDots: document.querySelectorAll(".sub-drawer .sub-tab .sub-tdot").length,
      tabBad: tabBad ? Number(tabBad.textContent) : 0,
      headTxt: ((document.querySelector(".sub-drawer .sub-head") || {}).innerText || "").trim(),
      filtTxt: [...document.querySelectorAll(".sub-drawer .sub-statfilt")]
        .map((e) => (e.textContent || "").trim()).join(" | "),
      chipN: chipN ? Number(chipN.textContent) : 0,
      chipBad: chipBad ? Number(chipBad.textContent) : 0,
      chipBadSev: chipBad ? chipBad.getAttribute("data-sev") : null,
      chipCov: ((document.querySelector(".svm-toolchip .sub-chipcov") || {}).textContent || "").trim(),
      filt: filt ? Number((filt.match(/(\d+)/) || [])[1]) : null,
      source: ((document.querySelector(".sub-talsrc") || {}).textContent || "").trim(),
      /* ── couverture ── */
      covNote: ((document.querySelector(".sub-cov .sub-secnote") || {}).textContent || "").trim(),
      covPlans: [...document.querySelectorAll(".sub-plan")].map((e) => ({
        etat: e.getAttribute("data-etat"),
        gestes: [...e.querySelectorAll("button")].map((x) => x.textContent.trim()),
      })),
      tlNoSub: [...document.querySelectorAll(".svm-clip[data-nosub]")]
        .map((e) => e.getAttribute("data-nosub") || "sans"),
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
  chk(snap.chipBad === nSig, "pastille de la chip = répliques signalées",
    "chip " + snap.chipBad + " / signalées " + nSig);
  chk(snap.chipN === truth.ids.length, "compteur de la chip = répliques de la piste",
    "chip " + snap.chipN + " / piste " + truth.ids.length);
  /* règle de couleur : les TOTAUX sont ambre, le rouge est réservé à ce qui
     EST bloquant (pastille d'une réplique, compte « n bloquantes »). Peindre
     en rouge un total de 12 dont une seule est bloquante remettrait la
     timeline et la liste en désaccord d'impression. */
  chk(snap.chipBadSev === "warn",
    "le total de la chip est ambre, le rouge reste réservé au bloquant",
    "chip " + snap.chipBadSev);

  /* ════════ GARDE A — un badge ne peut pas se tromper sur ce qu'il nomme ════
     L'onglet affichait « Répliques 12 » sur 13 répliques, et « Style et
     placement 2 » sans que rien à l'écran ne produise ce 2. Plus aucun chiffre
     hors de la ligne des comptes : un point de sévérité ne prétend rien
     compter, et il ne peut donc pas mentir. */
  const digits = (s) => (String(s).match(/\d/g) || []).length;
  chk(snap.tabTxt.every((t) => digits(t) === 0),
    "aucun onglet ne porte de nombre", JSON.stringify(snap.tabTxt));
  chk(snap.tabDots > 0, "les onglets signalent par un point de sévérité",
    snap.tabDots + " point(s)");
  chk(snap.tabBad === 0, "l'ancien badge numéroté d'onglet a disparu");
  chk(digits(snap.headTxt) === 0, "l'en-tête ne porte pas de nombre",
    JSON.stringify(snap.headTxt));
  chk(digits(snap.filtTxt) === 0,
    "le filtre est un bouton d'action, pas un second compteur",
    JSON.stringify(snap.filtTxt));

  /* ════════ GARDE B — aucune redite dans la bande ═══════════════════════════
     « 12 signalées » était écrit trois fois en 60 px. */
  const vus = {}, redites = [];
  snap.couples.forEach((c) => { if (vus[c]) redites.push(c); vus[c] = 1; });
  chk(redites.length === 0,
    "aucun couple « nombre + mot » répété dans l'en-tête du tiroir",
    redites.length ? JSON.stringify(redites) : JSON.stringify(snap.couples));

  /* chaque nombre de la ligne des comptes porte son mot */
  const sansMot = Object.keys(snap.tallyTxt)
    .filter((k) => !/[A-Za-zÀ-ÿ]{3}/.test(snap.tallyTxt[k]));
  chk(sansMot.length === 0, "chaque nombre de la ligne des comptes porte son unité",
    JSON.stringify(snap.tallyTxt));

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

  /* ════════ GARDE C — LA COUVERTURE est affichée, et désigne les plans ══════
     On auditait un clip et on facturait le verdict au montage entier. */
  const covOk = await p.evaluate(() => {
    const d = window.DzSubs;
    /* un montage de 60 s, deux plans, des répliques sur le premier seulement */
    const clips = [
      { id: "v1a", tr: "v1", start: 0, end: 20, name: "plan A" },
      { id: "v1b", tr: "v1", start: 20, end: 60, name: "plan B" },
    ];
    const segs = [d.make(0, 5, "un"), d.make(6, 12, "deux")];
    const c = d.coverage(segs, clips, 60);
    const marque = d.coverage(segs, clips.map((x) =>
      x.id === "v1b" ? Object.assign({}, x, { noSub: true }) : x), 60);
    return {
      pct: Math.round(c.pct), sans: c.sans.length,
      pctApres: Math.round(marque.pct), sansApres: marque.sans.length,
      /* une réplique masquée ou vide ne couvre rien */
      vide: Math.round(d.coverage([d.make(0, 20, "")], clips, 60).pct),
    };
  });
  chk(covOk.pct === 18 && covOk.sans === 1,
    "la couverture mesure la part du montage réellement sous-titrée",
    "11 s sur 60 s = " + covOk.pct + " %, " + covOk.sans + " plan sans réplique");
  chk(covOk.pctApres === 55 && covOk.sansApres === 0,
    "marquer un plan « sans parole » déplace la barre au lieu de cacher le trou",
    covOk.pct + " % -> " + covOk.pctApres + " %");
  chk(covOk.vide === 0, "une réplique vide ne couvre rien", covOk.vide + " %");
  chk(/couvert/.test(snap.tallyTxt["couverture"] || ""),
    "la couverture est écrite dans la ligne des comptes",
    snap.tallyTxt["couverture"] || "absente");
  if (snap.covPlans.length) {
    chk(snap.covPlans.every((x) => x.gestes.length >= 2),
      "chaque plan non couvert porte les gestes qui le traitent",
      JSON.stringify(snap.covPlans[0].gestes));
    chk(snap.tlNoSub.length >= snap.covPlans.filter((x) => x.etat === "sans").length,
      "les plans sans sous-titre sont aussi marqués sur la timeline",
      "timeline " + snap.tlNoSub.length + " / panneau " +
      snap.covPlans.filter((x) => x.etat === "sans").length);
  } else {
    chk(true, "couverture — ce montage n'a aucun plan à signaler");
  }

  /* ════════ GARDE D — un réglage que la gravure ignore n'affiche pas de
     valeur vivante ═══════════════════════════════════════════════════════════
     Mesuré à la gravure : sous un fond, le contour ne sort pas (0, 3 ou 8 px
     donnent la même image au pixel près). Le curseur affichait « 3 px ». */
  const mort = await p.evaluate(() => {
    const d = window.DzSubs;
    const st = Object.assign(d.defaultStyle(), { bgOn: true, outOn: true, outW: 3 });
    const eff = d.effective(st);
    const nu = d.effective(Object.assign({}, st, { bgOn: false }));
    const n = d.neutralized(st);
    return {
      effOut: eff.outW, effOutOn: eff.outOn, nuOut: nu.outW,
      /* l'ombre, elle, SURVIT au fond (mesuré : 4 516 px sous une boîte) */
      effSh: d.effective(Object.assign({}, st, { shOn: true })).shOn,
      champs: n.map((x) => x.champ),
      dit: n.length > 0 && !!n[0].why && !!n[0].fix,
      /* tout correctif de style annonce ce qu'il éteint / crée / laisse */
      plans: d.styleRules(Object.assign(d.defaultStyle(), { karMode: "box", bgOn: false }))
        .reduce((a, w) => a.concat((w.fixes || []).map((f) => d.stylePlan(
          Object.assign(d.defaultStyle(), { karMode: "box", bgOn: false }), f))), [])
        .map((pl) => (pl.ok ? pl.effect : pl.blocked)),
    };
  });
  chk(mort.effOut === 0 && mort.effOutOn === false && mort.nuOut === 3,
    "sous un fond le contour est éteint dans le style EFFECTIF, pas ailleurs",
    "avec fond " + mort.effOut + " px / sans fond " + mort.nuOut + " px");
  chk(mort.effSh === true, "l'ombre, elle, survit au fond (mesuré à la gravure)");
  chk(mort.champs.indexOf("outW") >= 0 && mort.dit,
    "le réglage éteint est nommé, expliqué, et porte le geste qui le rallume",
    JSON.stringify(mort.champs));
  chk(mort.plans.length >= 2 && mort.plans.every((t) =>
    /Après|Cela crée|cessera d'agir|réduirait/.test(t)),
    "chaque correctif de style annonce ce qu'il éteint, crée ou laisse",
    JSON.stringify(mort.plans));

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

  /* ════════ GARDE E — TOUR 5 : LA RÈGLE DES GESTES ═════════════════════════
     E1. Deux familles, distinguables PAR LA FORME (pas par le libellé seul) :
         un correctif écrit dans le fichier livré, un acquittement ne fait que
         taire l'alerte. Mesuré sur le style CALCULÉ des deux boutons.
     E2. Aucun bouton de remède sans son APRÈS.
     E3. Un bouton qui dépense annonce langue, moteur, prix et durée — les
         quatre boutons par plan compris.
     E4. Une ligne repliée porte début, DURÉE et la MESURE de sa pastille.
     E5. L'acquittement laisse une trace chiffrée et révocable dans le verdict.
     ═══════════════════════════════════════════════════════════════════════ */
  /* le contrôle doit être IDEMPOTENT : un acquittement laissé par une passe
     précédente vit sur le clip (donc sauvegardé). On repart de zéro. */
  await p.evaluate(() => {
    const r = [...document.querySelectorAll(".sub-covign button")]
      .find((e) => /révoquer/i.test(e.textContent || ""));
    if (r) r.click();
  });
  await sleep(1500);

  const fam = await p.evaluate(() => {
    const lu = (sel) => {
      const e = document.querySelector(sel);
      if (!e) return null;
      const s = getComputedStyle(e);
      return { txt: (e.innerText || "").replace(/\s+/g, " ").trim().slice(0, 70),
        radius: s.borderTopLeftRadius, style: s.borderTopStyle,
        bg: s.backgroundColor, title: (e.getAttribute("title") || "").length };
    };
    return { fix: lu('.sub-drawer .sub-act[data-fam="fix"]'),
      /* l'acquittement d'un PLAN (« révoquer » est aussi de la famille ack,
         mais c'est le geste inverse : il ne s'annonce pas de la même façon) */
      ack: lu('.sub-drawer .sub-plan .sub-act[data-fam="ack"]')
        || lu('.sub-drawer .sub-act[data-fam="ack"]'),
      nFix: document.querySelectorAll('.sub-drawer .sub-act[data-fam="fix"]').length,
      nAck: document.querySelectorAll('.sub-drawer .sub-act[data-fam="ack"]').length,
      muets: [...document.querySelectorAll(".sub-drawer .sub-act")]
        .filter((e) => (e.getAttribute("title") || "").trim().length < 25)
        .map((e) => (e.innerText || "").replace(/\s+/g, " ").trim()),
      couts: [...document.querySelectorAll(".sub-drawer .sub-act")]
        .filter((e) => /Transcrire|Caler la narration/i.test(e.innerText || ""))
        .map((e) => ((e.querySelector(".sub-actcost") || {}).textContent || "")),
    };
  });
  chk(fam.nFix > 0 && fam.nAck > 0, "les deux familles de gestes sont à l'écran",
    fam.nFix + " correctifs, " + fam.nAck + " acquittements");
  if (fam.fix && fam.ack) {
    const formes = [fam.fix.style !== fam.ack.style,
      fam.fix.radius !== fam.ack.radius, fam.fix.bg !== fam.ack.bg]
      .filter(Boolean).length;
    chk(formes >= 3, "les deux familles se distinguent PAR LA FORME",
      "bord " + fam.fix.style + "/" + fam.ack.style + ", rayon " +
      fam.fix.radius + "/" + fam.ack.radius);
    chk(/Acquitter|révoquer/.test(fam.ack.txt),
      "l'acquittement dit qu'il en est un", fam.ack.txt);
  }
  chk(fam.muets.length === 0, "aucun bouton de remède sans son APRÈS",
    fam.muets.length ? JSON.stringify(fam.muets) : "tous annoncés");
  chk(fam.couts.length > 0 && fam.couts.every((c) =>
    /gratuit|\$/.test(c) &&
    /français|anglais|espagnol|allemand|italien|portugais/.test(c)),
    "chaque bouton qui dépense annonce langue, moteur, prix et durée",
    JSON.stringify(fam.couts));

  const lignes = await p.evaluate(() => [...document.querySelectorAll(".sub-row")]
    .map((r) => ({ tc: ((r.querySelector(".sub-rtc") || {}).textContent || "").trim(),
      dur: ((r.querySelector(".sub-rdur") || {}).textContent || "").trim(),
      mes: ((r.querySelector(".sub-rmes") || {}).textContent || "").trim(),
      bad: !!r.querySelector(".sub-rbadge[data-k]") })));
  chk(lignes.length > 0 && lignes.every((l) => /\d\d:\d\d/.test(l.tc) && /s$/.test(l.dur)),
    "chaque ligne repliée porte son début ET sa durée",
    JSON.stringify(lignes.slice(0, 3)));
  const marquees = lignes.filter((l) => l.bad);
  chk(marquees.length > 0 && marquees.every((l) => l.mes.length > 0),
    "toute ligne à pastille porte LA MESURE qui l'a motivée",
    JSON.stringify(marquees.map((l) => l.mes).slice(0, 6)));

  const acq = await p.evaluate(() => {
    const a = [...document.querySelectorAll('.sub-plan .sub-act[data-fam="ack"]')][0];
    if (!a) return { skip: true };
    const annonce = ((a.querySelector(".sub-actcost") || {}).textContent || "").trim();
    a.click();
    return { skip: false, annonce: annonce };
  });
  await sleep(1800);
  if (acq.skip) chk(true, "acquittement — aucun plan muet à acquitter ici");
  else {
    const trace = await p.evaluate(() => ({
      chip: !!document.querySelector('.sub-tal[data-k="acquittes"]'),
      txt: ((document.querySelector('.sub-tal[data-k="acquittes"]') || {}).innerText || "")
        .replace(/\s+/g, " ").trim(),
      ligne: ((document.querySelector(".sub-covign") || {}).innerText || "")
        .replace(/\s+/g, " ").trim(),
      revoc: !![...document.querySelectorAll(".sub-covign button")]
        .find((e) => /révoquer/i.test(e.textContent || "")),
      pct: Math.round(window.DzSubs ? 0 : 0),
    }));
    chk(trace.chip && /acquitt/i.test(trace.txt),
      "l'acquittement laisse une trace CHIFFRÉE dans la ligne des comptes",
      trace.txt || "absente");
    chk(/acquitt/i.test(trace.ligne) && trace.revoc,
      "la trace nomme les plans et se révoque", trace.ligne.slice(0, 120));
    chk(/%/.test(acq.annonce),
      "l'acquittement annonçait AVANT le clic le chiffre qu'il déplace",
      acq.annonce);
    /* on remet le montage dans l'état où on l'a trouvé — et on laisse
       l'autosave écrire, sinon la passe suivante hériterait de l'aveu */
    await p.evaluate(() => {
      const r = [...document.querySelectorAll(".sub-covign button")]
        .find((e) => /révoquer/i.test(e.textContent || ""));
      if (r) r.click();
    });
    await sleep(3000);
  }

  /* deux remèdes visibles ne poussent pas en sens inverse sans nommer leur but */
  const arb = await p.evaluate(() => {
    const d = window.DzSubs;
    const st = Object.assign(d.defaultStyle(),
      { bgOn: true, bgOpacity: 64, karOn: true, outOn: true, outW: 3 });
    return d.goalConflicts(st).map((c) => ({
      trait: c.trait, a: c.a.label, aBut: c.a.but, b: c.b.label, bBut: c.b.but }));
  });
  chk(arb.length > 0 && arb.every((c) => c.aBut && c.bBut),
    "deux gestes opposés sont détectés et chacun nomme son objectif",
    JSON.stringify(arb));

  /* ── TOUR 6 — une réplique VIDE ne couvre rien ────────────────────────────
     Le geste « Écrire ici » pose une réplique sans texte sur la ligne même
     dont l'avertissement dit « ils sortiront muets », et rien ne disait si
     une réplique vide comptait comme couverte. La règle est tranchée : elle
     ne couvre rien. On la mesure sur le VRAI calcul, pas sur le libellé —
     même plan, même durée, un texte puis pas de texte. */
  const vide = await p.evaluate(() => {
    const d = window.DzSubs;
    const plans = [{ id: "p1", tr: "v1", start: 0, end: 10, name: "plan" }];
    const seg = (t) => [{ id: "s", tr: "s1", start: 0, end: 10, text: t }];
    const cov = (t) => d.coverage(seg(t), plans, 10);
    return {
      plein: cov("du texte").pct, vide: cov("").pct,
      espaces: cov("   \n  ").pct, masquee: d.coverage(
        [{ id: "s", tr: "s1", start: 0, end: 10, text: "du texte",
          hidden: true }], plans, 10).pct,
    };
  });
  chk(vide.plein === 100 && vide.vide === 0 && vide.espaces === 0 &&
      vide.masquee === 0,
    "le verdict ne compte JAMAIS une réplique vide comme couverture",
    JSON.stringify(vide));

  /* ── TOUR 6 — tout pourcentage se refait à la main ────────────────────────
     « 21 % » à côté de « 14,1 s sur 68,8 s » était juste et invérifiable :
     14,1/68,8 rend 20 %. Le calcul se fait désormais sur les secondes
     ARRONDIES — celles que l'écran montre — donc le refaire redonne le
     chiffre affiché, au point près. */
  const refait = await p.evaluate(() => {
    const d = window.DzSubs;
    /* couvert 14,14 s sur un plan de 21,63 s + un plan de 47,17 s : les
       valeurs exactes donneraient un arrondi different de celui des valeurs
       affichees si le calcul ne partait pas des secondes arrondies */
    const plans = [
      { id: "p1", tr: "v1", start: 0, end: 21.63, name: "a" },
      { id: "p2", tr: "v1", start: 21.63, end: 68.8, name: "b" }];
    const c = d.coverage(
      [{ id: "s", tr: "s1", start: 0, end: 14.14, text: "x" }], plans, 68.8);
    const r1 = (v) => Math.round(v * 10) / 10;
    return { pct: c.pct, couvert: c.couvert, attendu: c.attendu,
      aLaMain: Math.round(r1(c.couvert) / r1(c.attendu) * 100) };
  });
  chk(refait.pct === refait.aLaMain,
    "le pourcentage affiché est celui qu'on retrouve avec les nombres affichés",
    JSON.stringify(refait));

  /* ── TOUR 6 — la langue est lue sur le contenu, jamais affirmée contre lui */
  const lg = await p.evaluate(() => {
    const d = window.DzSubs;
    const seg = (t) => [{ id: "s", tr: "s1", start: 0, end: 4, text: t }];
    const en = "One of the best decisions I made all year was to invest in " +
      "tools that improve my productivity and this is when I found the " +
      "platform which has helped my team and I make videos faster";
    const fr = "Une des meilleures décisions que j'ai prises cette année a " +
      "été d'investir dans des outils qui améliorent ma productivité et " +
      "c'est là que j'ai trouvé la plateforme qui a aidé mon équipe";
    return { en: d.detectLang(seg(en), []), fr: d.detectLang(seg(fr), []),
      court: d.detectLang(seg("ok"), []), rien: d.detectLang([], []) };
  });
  chk(lg.en.code === "en" && lg.en.sur && lg.fr.code === "fr" && lg.fr.sur,
    "la langue se lit sur le texte présent (anglais et français tranchés)",
    JSON.stringify([lg.en.code, lg.en.hits, lg.fr.code, lg.fr.hits]));
  chk(!lg.court.sur && !!lg.court.raison && !lg.rien.total,
    "une détection incertaine le DIT au lieu de choisir en silence",
    JSON.stringify([lg.court.raison, lg.rien.raison]));
  /* et l'écran ne peut pas annoncer une langue que son propre contenu dément */
  const lgDom = await p.evaluate(() => {
    const n = document.querySelector(".sub-lgnote");
    const sel = document.querySelector(".sub-trlang select");
    const cost = document.querySelector(".sub-trrow .sub-actcost");
    return n ? { etat: n.getAttribute("data-etat"),
      txt: (n.innerText || "").replace(/\s+/g, " ").slice(0, 150),
      sel: sel ? sel.value : "", cost: (cost && cost.textContent) || "" } : null;
  });
  chk(!!lgDom && !!lgDom.etat && /mots reconnus|à analyser|indécise/i
      .test(lgDom.txt),
    "l'écran dit sur quoi repose la langue qu'il annonce",
    JSON.stringify(lgDom));

  /* ══════════════════════════════════════════════════════════════════════════
     TOUR 7 — trois gardes de plus, toutes mesurées EN PIXELS sur l'écran réel.

     F. UN TEXTE D'ARBITRAGE NE CITE JAMAIS UN LIBELLÉ ABSENT DE L'ÉCRAN.
        Le bloc disait « choisissez entre "Couper le fond" et "Fond opaque" »
        pendant que les deux boutons affichés étaient « Fond opaque » et
        « Couper le karaoké » : « Couper le fond » existait, 300 px plus bas,
        hors du cadre visible. La règle est donc la même que la source de
        vérité unique — ne jamais recopier ce qu'on peut lire.
     G. UN ÉCRAN D'ÉDITION MONTRE CE QU'ON ÉDITE. Le diagnostic se résume, le
        contenu reste : au moins trois lignes de réplique ENTIÈREMENT visibles
        dans le corps du tiroir, sans défiler, dans l'état par défaut.
     H. LES COMPTES AVEC LEURS RÈGLES. Le seuil qui déclenche une pastille est
        lisible à l'écran, il vaut EXACTEMENT ce que le verdict applique, et le
        changer change les pastilles.
     ══════════════════════════════════════════════════════════════════════════ */

  /* ── GARDE F ─────────────────────────────────────────────────────────────
     On force un style qui met deux gestes en opposition (fond translucide +
     karaoké + contour), on ouvre l'onglet Style, et on lit le bloc. */
  await p.evaluate(() => {
    const t = [...document.querySelectorAll(".sub-drawer .sub-tab")]
      .find((e) => /Style/i.test(e.textContent));
    if (t) t.click();
  });
  await sleep(1200);
  /* le style D'USINE oppose déjà deux gestes (fond translucide sous karaoké,
     donc contour éteint) : on repart de lui, par le bouton du panneau, plutôt
     que d'écrire dans un état privé que l'UI ne connaîtrait pas. */
  await p.evaluate(() => {
    const r = [...document.querySelectorAll(".sub-drawer button")]
      .find((e) => /Réinitialiser le style/i.test(e.textContent));
    if (r) r.click();
  });
  await sleep(1400);
  await p.evaluate(() => {
    const b = document.querySelector(".sub-drawer .sub-body");
    if (b) b.scrollTop = 0;
  });
  await sleep(500);
  const arbDom = await p.evaluate(() => {
    const box = document.querySelector(".sub-drawer .sub-arb");
    if (!box) return { absent: true };
    const body = document.querySelector(".sub-drawer .sub-body");
    const br = body.getBoundingClientRect();
    const visible = (e) => {
      const r = e.getBoundingClientRect();
      return r.top >= br.top - 1 && r.bottom <= br.bottom + 1 &&
        r.width > 0 && r.height > 0;
    };
    /* tout libellé de geste RENDU dans le tiroir, avec sa visibilité */
    const boutons = [...document.querySelectorAll(".sub-drawer .sub-act")]
      .map((e) => ({
        lab: ((e.querySelector(".sub-actlab") || {}).textContent || "").trim(),
        vu: visible(e), dansArb: !!e.closest(".sub-arb"),
      }));
    /* toute citation « … » dans le texte de l'arbitrage */
    const txt = (box.innerText || "").replace(/\s+/g, " ");
    const cites = (txt.match(/«\s*([^»]+?)\s*»/g) || [])
      .map((s) => s.replace(/[«»]/g, "").trim());
    return {
      absent: false, txt: txt.slice(0, 240), cites,
      /* les gestes que l'arbitrage rend LUI-MÊME */
      dedans: boutons.filter((b) => b.dansArb),
      /* ceux qu'il rend et qui sont hors du cadre visible : zéro exigé */
      dedansCaches: boutons.filter((b) => b.dansArb && !b.vu).map((b) => b.lab),
      /* aucun doublon : un geste arbitré ne vit pas AUSSI ailleurs */
      doublons: boutons.filter((b) => b.dansArb).map((b) => b.lab)
        .filter((l) => boutons.filter((b) => b.lab === l).length > 1),
      renvois: document.querySelectorAll(".sub-drawer .sub-arbptr").length,
    };
  });
  if (arbDom.absent) {
    chk(true, "arbitrage — ce style n'oppose aucun geste (rien à arbitrer)");
  } else {
    const labs = arbDom.dedans.map((b) => b.lab);
    chk(arbDom.dedans.length >= 2,
      "l'arbitrage PORTE les gestes qu'il oppose, il ne les cite pas",
      JSON.stringify(labs));
    chk(arbDom.dedansCaches.length === 0,
      "aucun geste de l'arbitrage n'est hors du cadre visible",
      JSON.stringify(arbDom.dedansCaches));
    /* LE test demandé : toute citation entre guillemets dans le bloc doit
       correspondre à un bouton VISIBLE. Par construction il n'y en a plus
       aucune — le bloc ne recopie plus un seul libellé. */
    const fantomes = arbDom.cites.filter((c) =>
      !arbDom.dedans.some((b) => b.lab === c && b.vu));
    chk(fantomes.length === 0,
      "aucun libellé cité par l'arbitrage n'est absent de l'écran",
      fantomes.length ? JSON.stringify(fantomes)
        : "0 citation — " + JSON.stringify(labs));
    chk(arbDom.doublons.length === 0,
      "un geste arbitré n'est pas dupliqué ailleurs dans l'onglet",
      JSON.stringify(arbDom.doublons));
    chk(arbDom.renvois > 0,
      "sa place d'origine porte un renvoi (qui ne le NOMME pas)",
      arbDom.renvois + " renvoi(s)");
  }

  /* ── GARDE G — le panneau montre ce qu'il sert à éditer ────────────────── */
  await p.evaluate(() => {
    const t = [...document.querySelectorAll(".sub-drawer .sub-tab")]
      .find((e) => /Répliques/i.test(e.textContent));
    if (t) t.click();
  });
  await sleep(1200);
  /* ÉTAT PAR DÉFAUT : toutes les lignes repliées. Une garde précédente a
     sélectionné un segment sur la timeline (l'inspecteur), et la ligne
     sélectionnée s'ouvre seule — ce n'est pas l'état d'un panneau qu'on vient
     d'ouvrir, et une ligne dépliée fait 415 px à elle seule. */
  await p.evaluate(() => {
    const b = [...document.querySelectorAll(".sub-drawer .sub-statfilt")]
      .find((e) => /replier/i.test(e.textContent || ""));
    if (b) b.click();
  });
  await sleep(800);
  await p.evaluate(() => {
    const b = document.querySelector(".sub-drawer .sub-body");
    if (b) b.scrollTop = 0;
  });
  await sleep(600);
  const place = await p.evaluate(() => {
    const body = document.querySelector(".sub-drawer .sub-body");
    const br = body.getBoundingClientRect();
    const rows = [...document.querySelectorAll(".sub-drawer .sub-row")];
    const entieres = rows.filter((e) => {
      const r = e.getBoundingClientRect();
      return r.top >= br.top - 1 && r.bottom <= br.bottom + 1;
    });
    const cov = document.querySelector(".sub-drawer .sub-cov");
    const R = (s) => {
      const e = document.querySelector(".sub-drawer " + s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return Math.round(r.top) + "→" + Math.round(r.bottom);
    };
    return {
      rows: rows.length, entieres: entieres.length,
      corps: Math.round(br.height),
      geo: { corps: Math.round(br.top) + "→" + Math.round(br.bottom),
        cov: R(".sub-cov"), outils: R(".sub-toolrow"), rech: R(".sub-searchrow"),
        seuils: R(".sub-nrm"), liste: R(".sub-rows"),
        r1: rows[0] ? Math.round(rows[0].getBoundingClientRect().top) + "→" +
          Math.round(rows[0].getBoundingClientRect().bottom) : null,
        scroll: body.scrollTop },
      cov: cov ? Math.round(cov.getBoundingClientRect().height) : 0,
      covOuvert: cov ? cov.hasAttribute("data-open") : false,
      /* le CONSTAT reste, lui, sans rien déplier */
      say: ((document.querySelector(".sub-drawer .sub-covsay") || {}).innerText
        || "").replace(/\s+/g, " ").trim(),
    };
  });
  chk(place.rows === 0 || place.entieres >= 3,
    "au moins 3 lignes de réplique entières sans défiler, état par défaut",
    place.entieres + " entières sur " + place.rows + " — corps " +
    place.corps + " px, couverture " + place.cov + " px " +
    JSON.stringify(place.geo));
  chk(!place.covOuvert,
    "le diagnostic de couverture est RÉSUMÉ par défaut, pas déplié");
  chk(place.cov === 0 || place.cov <= place.corps / 2,
    "le diagnostic ne prend pas plus de la moitié du corps du tiroir",
    place.cov + " px sur " + place.corps + " px");

  /* ── GARDE H — la règle est écrite, elle vaut ce qu'elle dit, et elle agit ── */
  const nrm = await p.evaluate(() => {
    const el = document.querySelector(".sub-drawer .sub-nrm");
    if (!el) return null;
    const body = document.querySelector(".sub-drawer .sub-body");
    const br = body.getBoundingClientRect(), r = el.getBoundingClientRect();
    return {
      cps: Number(el.getAttribute("data-cps")),
      min: Number(el.getAttribute("data-min")),
      max: Number(el.getAttribute("data-max")),
      gap: Number(el.getAttribute("data-gap")),
      txt: (el.innerText || "").replace(/\s+/g, " ").trim(),
      vu: r.top >= br.top - 1 && r.bottom <= br.bottom + 1,
      couche: window.DzSubs.normes(),
    };
  });
  chk(!!nrm, "les seuils sont AFFICHÉS dans l'onglet des répliques",
    nrm ? nrm.txt : "bloc absent");
  if (nrm) {
    chk(nrm.vu, "la règle est visible sans défiler, au-dessus des pastilles");
    chk(nrm.cps === nrm.couche.cps && nrm.min === nrm.couche.minS &&
        nrm.max === nrm.couche.maxS && nrm.gap === nrm.couche.gapMs,
      "le seuil affiché est EXACTEMENT celui que le verdict applique",
      JSON.stringify([nrm.cps, nrm.min, nrm.max, nrm.gap]) + " vs " +
      JSON.stringify(nrm.couche));
    /* chaque nombre écrit se retrouve dans le texte lisible du bloc */
    const dit = [String(nrm.cps), String(nrm.gap)]
      .filter((n) => nrm.txt.replace(",", ".").indexOf(n) < 0);
    chk(dit.length === 0, "chaque seuil est écrit en clair, pas seulement en attribut",
      dit.length ? JSON.stringify(dit) : nrm.txt);
    /* ET IL AGIT : on descend le seuil, le nombre de lignes marquées monte */
    const avant = await p.evaluate(() =>
      document.querySelectorAll(".sub-drawer .sub-row .sub-rbadge[data-k]").length);
    await p.evaluate(() => window.DzSubs.setNormes({ cps: 8 }));
    await sleep(2600);
    const apres = await p.evaluate(() => ({
      marquees: document.querySelectorAll(
        ".sub-drawer .sub-row .sub-rbadge[data-k]").length,
      txt: ((document.querySelector(".sub-drawer .sub-nrm") || {}).innerText || "")
        .replace(/\s+/g, " ").trim(),
      source: ((document.querySelector(".sub-talsrc") || {}).textContent || "").trim(),
    }));
    chk(apres.marquees >= avant && /8/.test(apres.txt),
      "changer le seuil change les pastilles ET ce qui est écrit",
      "à " + nrm.cps + " c/s : " + avant + " marquées ; à 8 c/s : " +
      apres.marquees + " (" + apres.source + ")");
    await p.evaluate(() => window.DzSubs.setNormes(
      { cps: 20, minS: 1, maxS: 7, gapMs: 80, fps: 25 }));
    await sleep(2200);
  }

  /* ── GARDE I — L'ACQUITTEMENT RETIRE DU CALCUL, PAS DU CONSTAT ───────────
     « Acquitter — sans parole » rendait l'alarme verte alors que le plan sort
     toujours muet. Après acquittement, l'écran doit CONTINUER de dire, sans
     rien déplier, que ces plans sortiront muets. */
  const ack = await p.evaluate(() => {
    const more = document.querySelector(".sub-drawer .sub-covmore");
    if (more && !document.querySelector(".sub-drawer .sub-plan")) more.click();
    return !!document.querySelector(".sub-drawer .sub-covmore");
  });
  await sleep(900);
  const ackClic = await p.evaluate(() => {
    const a = document.querySelector('.sub-drawer .sub-plan .sub-act[data-fam="ack"]');
    if (!a) return false;
    a.click();
    return true;
  });
  await sleep(2000);
  if (!ackClic) {
    chk(true, "acquittement — aucun plan muet à acquitter sur ce montage", String(ack));
  } else {
    const constat = await p.evaluate(() => {
      const body = document.querySelector(".sub-drawer .sub-body");
      const br = body.getBoundingClientRect();
      const vu = (s) => {
        const e = document.querySelector(".sub-drawer " + s);
        if (!e) return null;
        const r = e.getBoundingClientRect();
        return { txt: (e.innerText || "").replace(/\s+/g, " ").trim(),
          vu: r.top >= br.top - 1 && r.bottom <= br.bottom + 1 };
      };
      const cov = document.querySelector(".sub-drawer .sub-cov");
      return {
        say: vu(".sub-covsay"), ign: vu(".sub-covign"),
        ack: cov ? cov.hasAttribute("data-ack") : false,
        tal: ((document.querySelector('.sub-tal[data-k="acquittes"]') || {})
          .innerText || "").replace(/\s+/g, " ").trim(),
        tlOff: [...document.querySelectorAll('.svm-clip[data-nosub="off"]')].length,
      };
    });
    const dit = [constat.say, constat.ign].filter(Boolean)
      .filter((o) => o.vu && /muet/i.test(o.txt));
    chk(dit.length > 0,
      "après acquittement, l'écran dit TOUJOURS que ces plans sortiront muets",
      JSON.stringify([constat.say, constat.ign]));
    chk(constat.ack,
      "le bloc de couverture ne redevient pas neutre après un acquittement");
    chk(/acquitt/i.test(constat.tal),
      "la trace chiffrée reste dans la ligne des comptes", constat.tal);
    chk(constat.tlOff > 0,
      "le plan acquitté reste marqué sur la timeline", constat.tlOff + " clip(s)");
    await p.evaluate(() => {
      const r = [...document.querySelectorAll(".sub-covign button")]
        .find((e) => /révoquer/i.test(e.textContent || ""));
      if (r) r.click();
    });
    await sleep(3000);
  }

  chk(pageErrs.length === 0, "aucune erreur JS sur la page",
    pageErrs.join(" | ") || "0");

  console.log(out.join("\n"));
  console.log(JSON.stringify({
    repliques: truth.ids.length, signalees: nSig, bloquantes: nBlk,
    defauts: snap.tally["defauts"], tally: snap.tallyTxt,
    onglets: snap.tabTxt, points: snap.tabDots,
    chip: [snap.chipN, snap.chipBad, snap.chipCov],
    filtre: snap.filtTxt, entete: snap.headTxt, source_du_verdict: snap.source,
    couples_de_la_bande: snap.couples,
    couverture: { note: snap.covNote, plans: snap.covPlans.map((x) => x.etat),
      timeline: snap.tlNoSub },
    divergences: diffs, erreurs_page: pageErrs, ko: bad,
  }, null, 2));
  await b.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error("KO " + e.message); process.exit(1); });
