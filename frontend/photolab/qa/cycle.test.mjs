// qa/cycle.test.mjs — le cycle inspect -> rendu (D1) : UN seul cycle en vol, les demandes suivantes fusionnées en UN
// cycle de plus ; ordre des rendus (un rendu ancien ne recouvre jamais un plus récent) ; débounce des vignettes.
import { fileUnique, rendusOrdonnes, revisionNeuve, documentNeuf, maxSideRequete, fileFifo, creerAccumulateur,
  viderEtatDocument, doitRecadrer } from "../js/mod-cycle.js";
const json = (x) => JSON.stringify(x);

let ok = 0, ko = 0;
function check(label, cond, detail = "") { if (cond) ok++; else { ko++; console.error("ECHEC :", label, detail); } }
const differe = () => { let ok_, ko_; const p = new Promise((a, b) => { ok_ = a; ko_ = b; }); return { p, ok: ok_, ko: ko_ }; };
const tick = () => new Promise((r) => setTimeout(r, 0));

// 1. un seul en vol, fusion
{
  let lances = 0, enVol = 0, maxEnVol = 0;
  const attentes = [];
  const demander = fileUnique(() => {
    lances++; enVol++; maxEnVol = Math.max(maxEnVol, enVol);
    const d = differe(); attentes.push(d);
    return d.p.finally(() => { enVol--; });
  });
  const a = demander();
  const b = demander(), c = demander(), d = demander();
  check("1.1 une seule tâche lancée tant que la première vole", lances === 1, lances);
  check("1.2 les demandes suivantes partagent UNE promesse", b === c && c === d && a !== b);
  attentes[0].ok("premier");
  check("1.3 la première se résout avec sa valeur", (await a) === "premier");
  await tick();
  check("1.4 puis UNE seule tâche fusionnée", lances === 2, lances);
  const e = demander();
  check("1.5 une demande pendant la fusionnée attend un troisième cycle", e !== b);
  attentes[1].ok("second");
  check("1.6 la fusionnée se résout", (await b) === "second");
  await tick();
  attentes[2].ok("troisieme");
  check("1.7 troisième cycle", (await e) === "troisieme" && lances === 3, lances);
  check("1.8 jamais deux en vol", maxEnVol === 1, maxEnVol);
  await tick();
  const f = demander();
  check("1.9 file vide : une demande relance immédiatement", lances === 4);
  attentes[3].ok("q"); await f;
}

// 2. un échec ne bloque pas la file
{
  let n = 0;
  const demander = fileUnique(async () => { n++; if (n === 1) throw new Error("boum"); return n; });
  let leve = false;
  try { await demander(); } catch (e) { leve = e.message === "boum"; }
  check("2.1 l'erreur remonte à l'appelant", leve);
  check("2.2 la file repart après un échec", (await demander()) === 2);
}

// 3. un échec du cycle en vol ne fait pas échouer la demande fusionnée
{
  const d1 = differe();
  let n = 0;
  const demander = fileUnique(() => { n++; return n === 1 ? d1.p : Promise.resolve("ok"); });
  const a = demander(); const b = demander();
  d1.ko(new Error("x"));
  try { await a; } catch (e) { /* attendu */ }
  check("3.1 la fusionnée tourne quand même", (await b) === "ok" && n === 2);
}

// 4. rendus ordonnés : un numéro de demande ; seul un rendu plus récent que le dernier posé passe
{
  const o = rendusOrdonnes();
  const n1 = o.numero(), n2 = o.numero();
  check("4.1 le plus récent passe", o.poser(n2));
  check("4.2 un plus ancien arrivé après est jeté", !o.poser(n1));
  check("4.3 le suivant passe", o.poser(o.numero()));
}

// 5. vignettes : seulement quand la révision (ou le document) a changé
check("5.1 première révision", revisionNeuve(null, { revision: 3, name: "a", width: 1, height: 1 }));
check("5.2 même révision : rien", !revisionNeuve({ revision: 3, name: "a", width: 1, height: 1 }, { revision: 3, name: "a", width: 1, height: 1 }));
check("5.3 révision changée", revisionNeuve({ revision: 3 }, { revision: 4 }));
check("5.4 aucun document : rien", !revisionNeuve({ revision: 3 }, null));

// 6. document neuf (recadrer la vue) : aucun avant, ou dimensions changées
check("6.1 aucun avant", documentNeuf(null, { width: 10, height: 10 }));
check("6.2 dimensions changées (recadrage)", documentNeuf({ width: 10, height: 10 }, { width: 8, height: 10 }));
check("6.3 mêmes dimensions", !documentNeuf({ width: 10, height: 10, revision: 1 }, { width: 10, height: 10, revision: 2 }));

// 7. taille demandée à /rendu : le moteur refuse tout côté > 2048 (y compris 0 = taille réelle sur un document plus
//    grand, relevé le 08/10 sur photocraft-cli 0.3.0) et la route refuse < 64 -> 0 devient le grand côté, borné.
check("7.1 0 sur un document de 1920 -> 1920", maxSideRequete(0, { width: 1920, height: 1080 }) === 1920);
check("7.2 0 sur un document de 3000 -> 2048", maxSideRequete(0, { width: 3000, height: 1000 }) === 2048);
check("7.3 valeur ordinaire inchangée", maxSideRequete(960, { width: 1920, height: 1080 }) === 960);
check("7.4 plancher 64 de la route", maxSideRequete(10, { width: 20, height: 20 }) === 64);
check("7.5 plafond 2048", maxSideRequete(5000, { width: 6000, height: 4000 }) === 2048);

// 8. file FIFO des commandes : ordre d'arrivée, une à la fois, un échec ne bloque pas la suite
{
  const ajouter = fileFifo();
  const journal = [];
  let enVol = 0, maxEnVol = 0;
  const tache = (nom, ms, echoue = false) => () => new Promise((ok, ko) => {
    enVol++; maxEnVol = Math.max(maxEnVol, enVol); journal.push("debut " + nom);
    setTimeout(() => { enVol--; journal.push("fin " + nom); echoue ? ko(new Error(nom)) : ok(nom); }, ms);
  });
  const a = ajouter(tache("a", 15)), b = ajouter(tache("b", 1, true)), c = ajouter(tache("c", 1));
  check("8.1 résultat de chaque tâche", (await a) === "a");
  let leve = false; try { await b; } catch (e) { leve = e.message === "b"; }
  check("8.2 l'échec remonte à son appelant", leve);
  check("8.3 la suivante tourne quand même", (await c) === "c");
  check("8.4 ordre d'arrivée, jamais deux en vol", journal.join() === "debut a,fin a,debut b,fin b,debut c,fin c" && maxEnVol === 1, journal.join());
}

// 9. accumulateur : pendant qu'un envoi vole, les demandes suivantes se cumulent en UN envoi
{
  const envois = [];
  let liberer = null;
  const acc = creerAccumulateur((x) => { envois.push(x); return new Promise((r) => { liberer = r; }); }, (a, b) => ({ dx: a.dx + b.dx, dy: a.dy + b.dy }));
  acc({ dx: 1, dy: 0 }); acc({ dx: 1, dy: 0 }); acc({ dx: 0, dy: 10 }); acc({ dx: -1, dy: 0 });
  check("9.1 le premier part seul", envois.length === 1 && json(envois[0]) === json({ dx: 1, dy: 0 }));
  liberer(); await tick();
  check("9.2 les trois suivants partent cumulés", envois.length === 2 && json(envois[1]) === json({ dx: 0, dy: 10 }), envois);
  liberer(); await tick();
  check("9.3 plus rien en attente", envois.length === 2);
  const hist = [];
  let lib2 = null;
  const accH = creerAccumulateur((n) => { hist.push(n); return new Promise((r) => { lib2 = r; }); }, (a, b) => a + b);
  accH(-1); accH(-1); accH(-1); accH(1);
  lib2(); await tick();
  check("9.4 historique : annuler, annuler, annuler, rétablir -> -1 puis -1 net", json(hist) === json([-1, -1]), hist);
  lib2(); await tick();
}

// 10. un document fermé ou perdu ne laisse rien derrière lui (verrous tenus par l'écran, vignettes)
{
  const etat = { doc: { revision: 3 }, vignettes: { 2: "x" }, verrous: { 2: { pixels: true } }, outil: "move", couleurs: { fg: "#000000" } };
  viderEtatDocument(etat);
  check("10.1 doc, vignettes, verrous vidés", etat.doc === null && !Object.keys(etat.vignettes).length && !Object.keys(etat.verrous).length);
  check("10.2 l'outil et les couleurs restent", etat.outil === "move" && etat.couleurs.fg === "#000000");
}

// 11. recadrer la vue : seulement pour le cycle lancé APRÈS l'ouverture (jeton), jamais par un cycle plus ancien
check("11.1 cycle parti avant l'ouverture : non", !doitRecadrer(0, 0));
check("11.2 cycle parti après : oui, une fois", doitRecadrer(1, 0) && !doitRecadrer(1, 1));

console.log(`cycle : ${ok} ok, ${ko} echec(s)`);
if (ko) process.exit(1);
