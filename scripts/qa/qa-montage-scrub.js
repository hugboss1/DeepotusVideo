"use strict";
/* ════════════════════════════════════════════════════════════════════════════
   LA MESURE « AVANT » DU BALAYAGE — timeline du Montage (P7, tâche 8).

   Ce script ne corrige rien : il MESURE. Il glisse la tête de lecture sur la
   règle, 60 fois, et chronomètre deux choses que l'œil confond :

     1. LA MAIN — l'intervalle entre deux `requestAnimationFrame` pendant que
        le pointeur bouge. C'est ce qui décide si le glissement « colle » au
        doigt. Un intervalle de 16,7 ms = 60 images/s ; au-delà de 33 ms on
        voit la timeline sauter.
     2. L'IMAGE — le délai entre le `pointerdown` sur la règle et le PREMIER
        `seeked` (à défaut `timeupdate`) du `<video>` visible. C'est ce qui
        décide si l'aperçu suit, ou s'il arrive une demi-seconde après.

   CIBLES (celles du plan, pas des mesures) :
        p95 des intervalles rAF < 33 ms     p95 du premier seek < 150 ms

   ── LANCEMENT (c'est L'UTILISATEUR qui lance, pas l'agent) ────────────────
   Prérequis, dans cet ordre :
     1. le backend DeepotusVideoGen démarré et joignable sur 127.0.0.1:8765
        (le lanceur habituel — ce script ne démarre RIEN) ;
     2. les dépendances de scripts/qa installées UNE FOIS :

            cd scripts\qa
            npm ci            (ou : npm install)

        `node_modules/` n'est pas versionné : sans cette étape le script
        s'arrête sur un message d'une ligne, pas sur une pile d'appels.
     3. Chrome à l'emplacement ci-dessous (`CHROME`).

   Puis, depuis la racine du dépôt :

            node scripts/qa/qa-montage-scrub.js [nombre de positions]

   Sortie : une ligne par verdict, puis
     scrub p50/p95 ms, seek p50/p95 ms, images/s
   et un objet JSON de synthèse. Code de sortie 1 si une cible est manquée,
   2 si le script n'a pas pu démarrer (dépendance, Chrome ou backend absent) —
   les deux se distinguent, un environnement incomplet n'est pas un échec de
   performance.

   ── CE QUE CETTE MESURE N'AFFIRME PAS ─────────────────────────────────────
   * Elle dépend de la MACHINE et de la timeline OUVERTE (nombre de clips,
     durée, zoom). Deux exécutions ne sont comparables qu'à timeline égale :
     citer un chiffre d'ici sans dire quel projet était ouvert ne veut rien
     dire. La synthèse JSON porte donc `clips`, `duree_s` et `zoom_pct`.
   * `headless: "new"` n'est pas la fenêtre de l'utilisateur : le compositeur
     n'y fait pas le même travail. Les chiffres servent à comparer AVANT et
     APRÈS sur la même machine et le même mode, pas à décrire l'expérience
     réelle en valeur absolue.
   * Le délai de seek est mesuré depuis le `pointerdown` REÇU PAR LA PAGE
     (horodatage du navigateur, pas du pilote) : l'aller-retour CDP en est
     donc exclu. C'est le protocole, et il est là pour être relu.
   * Aucun rendu, aucun crédit, aucune écriture : le script LIT l'écran et
     bouge la souris. Il ne clique ni « Rendre » ni « Enregistrer ».
   ════════════════════════════════════════════════════════════════════════════ */
const path = require("path");
const fs = require("fs");

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = "http://127.0.0.1:8765";
const N_POS = Math.max(2, Math.min(400, Number(process.argv[2]) || 60));
const FENETRE_MS = 300;   // durée d'échantillonnage rAF par position
const CIBLE_RAF_MS = 33;
const CIBLE_SEEK_MS = 150;

function stop(msg) {
  console.error("PREREQUIS MANQUANT — " + msg);
  process.exit(2);
}

/* La dépendance n'est PAS versionnée : on le dit en UNE ligne, avec la
   commande exacte, plutôt que de laisser tomber une pile MODULE_NOT_FOUND
   sur quelqu'un qui lance le script pour la première fois. */
let puppeteer;
try {
  puppeteer = require(path.join(__dirname, "node_modules", "puppeteer-core"));
} catch (e) {
  stop("puppeteer-core est absent de scripts/qa/node_modules.\n" +
       "  Installe-le une fois :   cd scripts\\qa   puis   npm ci\n" +
       "  (npm install fonctionne aussi ; package-lock.json est versionné.)\n" +
       "  Détail : " + String(e.message || e).split("\n")[0]);
}
if (!fs.existsSync(CHROME)) {
  stop("Chrome est introuvable à " + CHROME + ".\n" +
       "  Corrige la constante CHROME en tête de ce fichier.");
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = [];
let bad = 0;
function chk(ok, label, detail) {
  out.push((ok ? "OK  " : "KO  ") + label + (detail ? "  — " + detail : ""));
  if (!ok) bad++;
}
function pct(xs, p) {
  if (!xs.length) return null;
  const s = xs.slice().sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.max(0, Math.ceil(p * s.length) - 1));
  return Math.round(s[i] * 10) / 10;
}

/* ── L'INSTRUMENTATION, posée DANS la page ────────────────────────────────
   `arm()` remet à zéro, arme un `pointerdown` en capture sur la règle (c'est
   LUI qui fixe t0 : l'horodatage du navigateur, pas celui du pilote), écoute
   `seeked` et `timeupdate` sur les <video> VISIBLES, et lance une boucle rAF
   de FENETRE_MS. `read()` rend la promesse qui se résout à la fin de cette
   fenêtre. Aucune de ces écritures ne touche l'état de l'application. */
const INSTRUMENT = (fenetreMs) => {
  const vis = () => [...document.querySelectorAll("video")].filter((v) => {
    const r = v.getBoundingClientRect();
    return r.width > 4 && r.height > 4 && v.offsetParent !== null;
  });
  const S = {
    t0: null, seek: null, frames: [], fin: null, off: [],
    nVideos: vis().length,
  };
  window.__dzScrub = {
    videos: () => vis().length,
    arm() {
      S.off.forEach((f) => { try { f(); } catch (_e) {} });
      S.off = []; S.t0 = null; S.seek = null; S.frames = [];
      const ruler = document.querySelector(".svm-ruler");
      const onDown = (e) => { if (S.t0 === null) S.t0 = e.timeStamp || performance.now(); };
      if (ruler) {
        ruler.addEventListener("pointerdown", onDown, true);
        S.off.push(() => ruler.removeEventListener("pointerdown", onDown, true));
      }
      const onSeek = () => {
        if (S.seek === null && S.t0 !== null) S.seek = performance.now() - S.t0;
      };
      vis().forEach((v) => {
        v.addEventListener("seeked", onSeek);
        v.addEventListener("timeupdate", onSeek);
        S.off.push(() => {
          v.removeEventListener("seeked", onSeek);
          v.removeEventListener("timeupdate", onSeek);
        });
      });
      S.nVideos = vis().length;
      const debut = performance.now();
      S.fin = new Promise((res) => {
        const tick = (t) => {
          S.frames.push(t);
          if (t - debut < fenetreMs) requestAnimationFrame(tick);
          else res();
        };
        requestAnimationFrame(tick);
      });
      return true;
    },
    async read() {
      await S.fin;
      S.off.forEach((f) => { try { f(); } catch (_e) {} });
      S.off = [];
      const d = [];
      for (let i = 1; i < S.frames.length; i++) d.push(S.frames[i] - S.frames[i - 1]);
      return { rafs: d, seek: S.seek, videos: S.nVideos, vu: S.t0 !== null };
    },
  };
  return true;
};

(async () => {
  const b = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
  }).catch((e) => { stop("Chrome n'a pas démarré : " + e.message); });
  const p = await b.newPage();
  const pageErrs = [];
  p.on("pageerror", (e) => pageErrs.push(String(e.message)));
  await p.setViewport({ width: 1600, height: 950 });

  try {
    await p.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 45000 });
  } catch (e) {
    await b.close();
    stop("le backend ne répond pas sur " + BASE + " — démarre-le d'abord.\n" +
         "  Détail : " + e.message);
  }
  await p.evaluate(() => { try { localStorage.setItem("dz_onboarded", "1"); } catch (_e) {} });
  await p.goto(BASE + "/", { waitUntil: "networkidle2", timeout: 60000 });
  await sleep(3000);

  /* l'écran Montage — même geste que qa-subs-consistency.js */
  await p.evaluate(() => {
    const el = [...document.querySelectorAll("button,a,div[role=button],li,div")]
      .filter((e) => (e.textContent || "").includes("Timeline multipiste"))
      .sort((a, c) => (a.textContent || "").length - (c.textContent || "").length)[0];
    if (el) el.click();
  });
  try {
    await p.waitForSelector(".svm-lanes", { timeout: 20000 });
    await p.waitForSelector(".svm-ruler", { timeout: 20000 });
  } catch (e) {
    console.log(out.join("\n"));
    await b.close();
    stop("la timeline (.svm-lanes / .svm-ruler) n'est pas apparue en 20 s — " +
         "l'écran Montage n'a pas été atteint.\n  Détail : " + e.message);
  }
  await sleep(2000);

  /* de quoi rendre le chiffre relisible : SANS ce contexte, un p95 ne dit
     rien — deux timelines différentes ne se comparent pas. */
  const ctx = await p.evaluate(() => {
    const lanes = document.querySelector(".svm-lanes");
    const clips = document.querySelectorAll(".svm-clip").length;
    const t = [...document.querySelectorAll(".svm-tbar, .svm-toolbar, .svm-lanes")]
      .map((e) => (e.innerText || "")).join(" ");
    const m = /(\d+)\s*%/.exec(t || "");
    return {
      clips,
      zoom_pct: m ? Number(m[1]) : (lanes ? parseInt(lanes.style.width, 10) || null : null),
      largeur_regle: (document.querySelector(".svm-ruler") || {}).clientWidth || 0,
      videos: document.querySelectorAll("video").length,
    };
  });
  chk(ctx.clips > 0, "la timeline porte des clips", ctx.clips + " clip(s)");

  await p.evaluate(INSTRUMENT, FENETRE_MS);
  const nVid = await p.evaluate(() => window.__dzScrub.videos());
  chk(true, "vidéos visibles au moment de la mesure", String(nVid));

  const box = await p.evaluate(() => {
    const r = document.querySelector(".svm-ruler").getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  });
  /* la gouttière d'en-tête fait 88 px (cf. `rulerHover` du bundle) : on ne
     mesure que la zone qui déplace réellement la tête de lecture. */
  const x0 = box.x + 88 + 4;
  const x1 = box.x + box.w - 4;
  const y = box.y + box.h / 2;
  chk(x1 > x0, "la règle a une zone utile", `${Math.round(x1 - x0)} px`);

  const rafs = [];
  const seeks = [];
  let vus = 0;
  let dureeTotale = 0;
  let frames = 0;
  for (let i = 0; i < N_POS; i++) {
    const x = x0 + ((x1 - x0) * i) / Math.max(1, N_POS - 1);
    await p.evaluate(() => window.__dzScrub.arm());
    await p.mouse.move(x, y);
    await p.mouse.down();
    /* trois pas de déplacement sous le bouton : c'est un GLISSEMENT, pas un
       clic — c'est là que le rendu de la timeline travaille. */
    await p.mouse.move(x + 6, y);
    await p.mouse.move(x + 12, y);
    await p.mouse.move(x + 6, y);
    await p.mouse.up();
    const r = await p.evaluate(() => window.__dzScrub.read());
    if (r.vu) vus++;
    if (Array.isArray(r.rafs) && r.rafs.length) {
      for (const d of r.rafs) rafs.push(d);
      frames += r.rafs.length + 1;
      dureeTotale += r.rafs.reduce((a, c) => a + c, 0);
    }
    if (typeof r.seek === "number" && r.seek >= 0) seeks.push(r.seek);
  }

  chk(vus === N_POS, "chaque position a bien été reçue par la règle",
    `${vus}/${N_POS} pointerdown vus`);
  chk(rafs.length > 0, "des images ont été échantillonnées",
    `${rafs.length} intervalles`);

  const rp50 = pct(rafs, 0.5), rp95 = pct(rafs, 0.95);
  const sp50 = pct(seeks, 0.5), sp95 = pct(seeks, 0.95);
  const ips = dureeTotale > 0 ? Math.round((frames / dureeTotale) * 1000 * 10) / 10 : null;

  chk(rp95 !== null && rp95 < CIBLE_RAF_MS,
    `p95 des intervalles rAF sous ${CIBLE_RAF_MS} ms`, `${rp95} ms`);
  chk(seeks.length > 0,
    "au moins un seek observé (sinon la cible de seek ne veut rien dire)",
    `${seeks.length}/${N_POS} positions`);
  chk(seeks.length > 0 && sp95 !== null && sp95 < CIBLE_SEEK_MS,
    `p95 du premier seek sous ${CIBLE_SEEK_MS} ms`, `${sp95} ms`);
  chk(pageErrs.length === 0, "aucune erreur JS sur la page",
    pageErrs.join(" | ") || "0");

  console.log(out.join("\n"));
  console.log(`scrub p50 ${rp50} ms / p95 ${rp95} ms, ` +
              `seek p50 ${sp50} ms / p95 ${sp95} ms, ` +
              `${ips} images/s`);
  console.log(JSON.stringify({
    positions: N_POS, fenetre_ms: FENETRE_MS,
    scrub_p50_ms: rp50, scrub_p95_ms: rp95,
    seek_p50_ms: sp50, seek_p95_ms: sp95, seeks_observes: seeks.length,
    images_par_s: ips, intervalles: rafs.length,
    cibles: { scrub_p95_ms: CIBLE_RAF_MS, seek_p95_ms: CIBLE_SEEK_MS },
    contexte: { clips: ctx.clips, zoom_pct: ctx.zoom_pct,
      largeur_regle_px: ctx.largeur_regle, videos: ctx.videos,
      videos_visibles: nVid },
    erreurs_page: pageErrs, ko: bad,
  }, null, 2));
  await b.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error("KO " + (e && e.stack || e)); process.exit(1); });
