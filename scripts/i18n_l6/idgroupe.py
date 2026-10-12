"""id-groupe (12/10, postérieur à L6) — tout identifiant NEUF du Vectorlab est unique dans tout le document.

Défaut vu sur le backend de preuve : grouper o1 et o2 donnait {id:"o1", type:"groupe", enfants:[o1, o2]}. op_grouper
retirait ses enfants du calque PUIS demandait idLibre, qui ne les voyait plus ; op_ecreter faisait de même. La
sélection, l'édition, « Retirer le fond » (image_profonde) ou la suppression pouvaient viser le groupe au lieu de
l'image. Corrigé dans js/mod-doc.js :
- op_grouper / op_ecreter prennent l'id du groupe AVANT le retrait ;
- _idsPris compte aussi l'intérieur des symboles (un id neuf ne recroise jamais un objet de symbole) ;
- _idsNeufs : une source d'ids qui relève les pris UNE fois et y ajoute chaque id rendu ; _reidentifier donne un id
  neuf à un objet et à TOUS ses descendants, le clip d'un groupe écrêté suivant son conteneur ;
- détacher / ouvrir un symbole renumérotent les descendants des groupes (ils gardaient les ids du symbole, en double
  dès la 2e instance détachée) ; op_dupliquer d'un groupe écrêté garde un clip valide (il visait l'ancien conteneur,
  la copie était refusée par parserDoc) ; op_ajouter d'un groupe garde l'id libre d'un enfant, renumérote les autres.
Documents existants : jamais renumérotés en bloc. À l'ouverture (core.charger, et un brouillon restauré), le SEUL
motif sûr est réparé : un groupe qui porte l'id d'un de ses descendants reçoit un id neuf (op_ids_reparer ; ses
enfants, le clip, gardent les leurs) ; tout autre doublon est signalé (ids_doublons), pas touché — on ne sait pas
lequel des deux objets était visé. Édition consignée en S sur la source de BASE (test_i18n_l6 [2])."""
from outils import L, S, X, H  # noqa: F401


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


DOC = "js/mod-doc.js"

AIDES = """const _idLibre = idLibre;
// id-groupe : une SOURCE d'ids neufs pour une op qui en crée plusieurs, ou qui retire des objets avant de poser
// le sien — les ids pris sont relevés UNE fois, AVANT toute modification, et chaque id rendu y entre
function _idsNeufs(doc, pris = _idsPris(doc)) {
  let n = 1;
  return () => { while (pris.has("o" + n)) n++; pris.add("o" + n); return "o" + n; };
}
// un id neuf pour l'objet et TOUS ses descendants ; le clip d'un groupe écrêté suit son conteneur
function _reidentifier(o, neuf) {
  o.id = neuf();
  if (o.type !== "groupe" || !Array.isArray(o.enfants)) return;
  const avant = o.enfants.map((e) => e.id);
  for (const e of o.enfants) _reidentifier(e, neuf);
  if (o.clip !== undefined) { const k = avant.indexOf(o.clip); if (k >= 0) o.clip = o.enfants[k].id; }
}
// les ids portés par plus d'un objet des calques (groupes et enfants compris), triés
export function ids_doublons(doc) {
  const vus = new Set(), doubles = new Set();
  _visiterObjets(doc, (o) => { if (vus.has(o.id)) doubles.add(o.id); else vus.add(o.id); });
  return [...doubles].sort();
}
// réparation SÛRE d'un document d'avant id-groupe : un groupe qui porte l'id d'un de ses descendants (la trace
// d'op_grouper / op_ecreter) reçoit un id neuf ; ses enfants et son clip gardent les leurs. Les autres doublons
// ne sont pas renumérotés (on ne sait pas lequel était visé) : ids_doublons les signale. -> [[ancien, neuf]]
export function op_ids_reparer(doc) {
  const neuf = _idsNeufs(doc), faits = [];
  const dessous = (g, out) => { for (const e of g.enfants || []) { out.add(e.id); if (e.type === "groupe") dessous(e, out); } return out; };
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.type !== "groupe") continue;
      visiter(o.enfants);
      if (dessous(o, new Set()).has(o.id)) { const id = neuf(); faits.push([o.id, id]); o.id = id; }
    }
  };
  for (const c of [...doc.calques, ...Object.values(doc.symboles || {})]) visiter(c.objets);
  return faits;
}"""

AJOUTER_AVANT = """  const pris = _idsPris(doc);
  const id = (objet.id && !pris.has(objet.id)) ? objet.id : _idLibre(doc);
  c.objets.push({ ...objet, id });
  return id;"""
AJOUTER_APRES = """  // id-groupe : un id fourni est gardé s'il est libre — les enfants d'un groupe aussi ; sinon (ou sans id), un
  // neuf, et le clip d'un groupe écrêté suit son conteneur
  const pris = _idsPris(doc), neuf = _idsNeufs(doc, pris);
  const poser = (o) => {
    const id = (o.id && !pris.has(o.id)) ? (pris.add(o.id), o.id) : neuf();
    if (o.type !== "groupe" || !Array.isArray(o.enfants)) return { ...o, id };
    const g = { ...o, id, enfants: o.enfants.map(poser) };
    if (o.clip !== undefined) { const k = o.enfants.findIndex((e) => e.id === o.clip); if (k >= 0) g.clip = g.enfants[k].id; }
    return g;
  };
  const o = poser(objet);
  c.objets.push(o);
  return o.id;"""

GROUPER_AVANT = """  for (const { calque, objet } of cibles) {
    calque.objets.splice(calque.objets.indexOf(objet), 1);
  }
  const id = _idLibre(doc);"""
GROUPER_APRES = """  // id-groupe : l'id du groupe se prend AVANT de retirer ses enfants — après, idLibre ne les voit plus et
  // rendait l'id du premier (le groupe et son enfant portaient le même id)
  const id = _idLibre(doc);
  for (const { calque, objet } of cibles) {
    calque.objets.splice(calque.objets.indexOf(objet), 1);
  }"""

ECRETER_AVANT = """  for (const { calque, objet } of contenus) calque.objets.splice(calque.objets.indexOf(objet), 1);
  const iC = hote.objets.indexOf(conteneur);
  hote.objets.splice(iC, 1);
  const id = _idLibre(doc);"""
ECRETER_APRES = """  const id = _idLibre(doc);            // id-groupe : AVANT le retrait (sinon l'id du conteneur ou d'un contenu)
  for (const { calque, objet } of contenus) calque.objets.splice(calque.objets.indexOf(objet), 1);
  const iC = hote.objets.indexOf(conteneur);
  hote.objets.splice(iC, 1);"""

DETACHER_AVANT = """    // copies à ids NEUFS (insérées une à une : _idLibre voit chaque id posé),
    // mappées de la bbox du symbole vers celle de l'instance
    const copies = _clone(sym.objets);
    copies.forEach((o, k) => { o.id = _idLibre(doc); _mapperObjet(o, av, ap, doc); c.objets.splice(i + k, 0, o); });"""
DETACHER_APRES = """    // copies à ids NEUFS, descendants des groupes compris (id-groupe : ils gardaient les ids du symbole, en
    // double dès la 2e instance détachée), mappées de la bbox du symbole vers celle de l'instance
    const copies = _clone(sym.objets), neuf = _idsNeufs(doc);
    copies.forEach((o, k) => { _reidentifier(o, neuf); _mapperObjet(o, av, ap, doc); c.objets.splice(i + k, 0, o); });"""

OUVRIR_AVANT = """    // copies à ids NEUFS, posées une à une (_idLibre voit chaque id posé)
    for (const o of _clone(sym.objets)) { o.id = _idLibre(doc); _mapperObjet(o, sym.bbox, cadre, doc); cal.objets.push(o); }"""
OUVRIR_APRES = """    // copies à ids NEUFS, descendants des groupes compris (id-groupe)
    const neuf = _idsNeufs(doc);
    for (const o of _clone(sym.objets)) { _reidentifier(o, neuf); _mapperObjet(o, sym.bbox, cadre, doc); cal.objets.push(o); }"""

REID_AVANT = """  const reid = (o) => {
    o.id = idNeuf();
    if (o.type === "groupe") (o.enfants || []).forEach(reid);
  };"""
REID_APRES = """  // id-groupe : descendants compris, et le clip d'un groupe écrêté suit le conteneur de la COPIE
  const reid = (o) => _reidentifier(o, idNeuf);"""

CORE = "js/core.js"
VERIFIER = """// id-groupe : un document d'avant le correctif peut porter un groupe au MÊME id qu'un de ses descendants
// (op_grouper, op_ecreter) — il reçoit un id neuf ; tout autre doublon est seulement signalé
function verifierIds() {
  const rep = op_ids_reparer(etat.doc), dbl = ids_doublons(etat.doc);
  if (rep.length) etat.sale = true;
  if (dbl.length) toast(T("vectorlab.core.ids_doublons", { ids: dbl.join(", ") }), true);
  else if (rep.length) toast(T(rep.length > 1 ? "vectorlab.core.ids_repares_plusieurs" : "vectorlab.core.ids_repares_un", { n: rep.length }));
}

function toast(msg, erreur) {"""

DICO_CORE = {
    "vectorlab.core.ids_doublons": (
        "Identifiants en double dans ce document : {ids} — la sélection et l'édition peuvent viser le mauvais objet",
        "Duplicate ids in this document: {ids} — selecting and editing may target the wrong object"),
    "vectorlab.core.ids_repares_un": (
        "Un groupe portait l'id d'un de ses objets : il a reçu un id neuf (Sauver pour l'écrire)",
        "A group shared an id with one of its objects: it got a new id (Save to keep it)"),
    "vectorlab.core.ids_repares_plusieurs": (
        "{n} groupes portaient l'id d'un de leurs objets : ils ont reçu un id neuf (Sauver pour l'écrire)",
        "{n} groups shared an id with one of their objects: they got new ids (Save to keep it)"),
}

ENTREES = [
    # ── js/mod-doc.js ──
    S(DOC, 516, "  for (const cl of doc.calques) {",
      c("  // id-groupe : l'intérieur des symboles compte aussi — un id neuf ne recroise jamais un objet de symbole\n"
        "  for (const cl of [...doc.calques, ...Object.values(doc.symboles || {})]) {"), {}),
    S(DOC, 533, "const _idLibre = idLibre;", c(AIDES), {}),
    S(DOC, 538, c(AJOUTER_AVANT), c(AJOUTER_APRES), {}),
    S(DOC, 933, c(GROUPER_AVANT), c(GROUPER_APRES), {}),
    S(DOC, 1118, c(ECRETER_AVANT), c(ECRETER_APRES), {}),
    S(DOC, 1237, c(DETACHER_AVANT), c(DETACHER_APRES), {}),
    S(DOC, 1265, c(OUVRIR_AVANT), c(OUVRIR_APRES), {}),
    S(DOC, 1430, c(REID_AVANT), c(REID_APRES), {}),

    # ── js/core.js : réparer / signaler à l'ouverture, exposé pour le brouillon ──
    S(CORE, 7, "         sommetDe, op_dupliquer, reperes_guides, reperes_rects, planches_guides }",
      "         sommetDe, op_dupliquer, reperes_guides, reperes_rects, planches_guides, op_ids_reparer, ids_doublons }", {}),
    S(CORE, 580, "    majTete();", c("    majTete();\n    verifierIds();                     // id-groupe : réparer / signaler les ids en double"), {}),
    S(CORE, 617, "function toast(msg, erreur) {", c(VERIFIER), DICO_CORE),
    S(CORE, 774, "  executer, annuler, refaire, sauver, charger,",
      "  executer, annuler, refaire, sauver, charger, verifierIds,", {}),

    # ── js/mod-brouillon.js : un brouillon restauré passe la même vérification ──
    S("js/mod-brouillon.js", 59, "    } else effacer(k);",
      c("      VL.verifierIds();                  // id-groupe : un brouillon d'avant le correctif aussi\n"
        "    } else effacer(k);"), {}),
]
