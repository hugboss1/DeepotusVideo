// mod-doc.js — LE modèle-document du Vectorlab : validation + compilation
// JSON -> SVG. PUR (aucune lecture du DOM, aucun état) : la même fonction
// sert l'écran, l'export et le banc qa/ node. Le JSON est la vérité ; le
// SVG n'en est qu'une projection.

const escAttr = (v) => String(v)
  .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

export function parserDoc(doc) {
  if (!doc || typeof doc !== "object") throw new Error("document: objet requis");
  if (!doc.v) throw new Error("document: champ v requis");
  if (!doc.taille || !(doc.taille.w > 0) || !(doc.taille.h > 0)) {
    throw new Error("document: taille {w,h} positive requise");
  }
  if (!Array.isArray(doc.calques)) throw new Error("document: calques[] requis");
  for (const c of doc.calques) {
    if (!c.id) throw new Error("calque sans id");
    if (!Array.isArray(c.objets)) throw new Error(`calque ${c.id}: objets[] requis`);
  }
  return doc;
}

function styleAttrs(s = {}, ctx = {}) {
  let fond = s.fond === undefined ? "none" : s.fond;
  if (typeof fond === "string" && fond.startsWith("grad:")) {
    const gid = fond.slice(5);
    fond = (ctx.degrades && ctx.degrades[gid]) ? `url(#${gid})` : "none";
  }
  let out = ` fill="${escAttr(fond)}"`;
  if (s.contour && s.contour !== "none") {
    out += ` stroke="${escAttr(s.contour)}"`
        + ` stroke-width="${Number(s.epaisseur || 1)}"`
        + ` stroke-linejoin="${escAttr(s.joint || "round")}"`
        + ` stroke-linecap="round"`;
    if (s.pointilles) out += ` stroke-dasharray="${escAttr(s.pointilles)}"`;
  }
  if (s.opacite !== undefined && Number(s.opacite) !== 1) {
    out += ` opacity="${Number(s.opacite)}"`;
  }
  return out;
}

function compilerObjet(o, ctx = {}) {
  const t = ` data-objet="${escAttr(o.id)}"`;
  const tr = o.transform ? ` transform="${escAttr(o.transform)}"` : "";
  const st = styleAttrs(o.style, ctx);
  switch (o.type) {
    case "rect":
      return `<rect${t} x="${+o.x}" y="${+o.y}" width="${+o.w}"`
           + ` height="${+o.h}"${o.rx ? ` rx="${+o.rx}"` : ""}${st}${tr}/>`;
    case "ellipse":
      return `<ellipse${t} cx="${+o.cx}" cy="${+o.cy}" rx="${+o.rx}"`
           + ` ry="${+o.ry}"${st}${tr}/>`;
    case "path":
      return `<path${t} d="${escAttr(o.d)}"${st}${tr}/>`;
    case "groupe":
      return `<g${t}${st}${tr}>`
           + (o.enfants || []).map((e) => compilerObjet(e, ctx)).join("")
           + `</g>`;
    default:
      // un type inconnu ne casse pas le document : il se voit au commentaire
      return `<!-- objet ${escAttr(o.id)}: type inconnu ${escAttr(o.type)} -->`;
  }
}

/* ── chemins (T1.1) : le d de path, parsé, structuré, canonisé ──
   Segments {c:"M"|"L"|"C"|"Q"|"Z", p:[nombres]} en ABSOLU seulement (v1) ;
   lecture tolérante (virgules, implicites SVG), écriture canonique stable
   à l'octet — les opérations de nœuds et les booléens s'appuient dessus. */
const ARITE = { M: 2, L: 2, C: 6, Q: 4, Z: 0 };

// arrondi 2 décimales SANS le piège flottant (1.005 → 1.01, 3.10 → 3.1)
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);

export function chemin_parser(d) {
  const src = String(d ?? "").replace(/,/g, " ").trim();
  const jetons = src.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?/g) || [];
  const segs = [];
  let i = 0, cmd = null;
  while (i < jetons.length) {
    const t = jetons[i];
    if (/^[A-Za-z]$/.test(t)) {
      if (!(t in ARITE)) {
        if (t.toUpperCase() in ARITE) {
          throw new Error(`chemin: commande relative '${t}' non supportée `
                          + "(v1: M/L/C/Q/Z absolus)");
        }
        throw new Error(`chemin: commande inconnue '${t}'`);
      }
      cmd = t;
      i++;
      if (cmd === "Z") { segs.push({ c: "Z", p: [] }); cmd = null; }
      continue;
    }
    if (cmd === null) throw new Error("chemin: nombre sans commande");
    const p = [];
    for (let k = 0; k < ARITE[cmd]; k++, i++) {
      if (i >= jetons.length || /^[A-Za-z]$/.test(jetons[i])) {
        throw new Error(`chemin: arité de ${cmd} incomplète`);
      }
      p.push(Number(jetons[i]));
    }
    segs.push({ c: cmd, p });
    if (cmd === "M") cmd = "L";     // implicite SVG : paires après M = L
  }
  return segs;
}

export function chemin_serialiser(segs) {
  return segs.map((s) => s.c === "Z" ? "Z"
                       : s.c + " " + s.p.map(nbc).join(" ")).join(" ");
}


/* ── opérations d'objets (T1.2) : les COMMANDES pures sur le modèle ──
   L'UI ne fait que traduire des gestes vers ces fonctions ; l'historique
   d'annulation capture le JSON avant chacune. Déplacement et
   redimensionnement réécrivent la GÉOMÉTRIE (les booléens de phase 3
   veulent des coordonnées vraies) ; seule la rotation compose `transform`. */

function _calque(doc, calqueId) {
  const c = doc.calques.find((x) => x.id === calqueId);
  if (!c) throw new Error(`calque inconnu: ${calqueId}`);
  return c;
}

function* _objetsCibles(doc, ids, { ignorerVerrouilles = true } = {}) {
  const voulu = new Set(ids);
  for (const c of doc.calques) {
    if (ignorerVerrouilles && c.verrou) continue;
    for (let i = c.objets.length - 1; i >= 0; i--) {
      if (voulu.has(c.objets[i].id)) yield { calque: c, objet: c.objets[i], i };
    }
  }
}

function _idsPris(doc) {
  const pris = new Set();
  for (const cl of doc.calques) {
    (function visiter(objs) {
      for (const o of objs) {
        pris.add(o.id);
        if (o.type === "groupe") visiter(o.enfants || []);
      }
    })(cl.objets);
  }
  return pris;
}

function _idLibre(doc) {
  const pris = _idsPris(doc);
  let n = 1;
  while (pris.has("o" + n)) n++;
  return "o" + n;
}

export function op_ajouter(doc, calqueId, objet) {
  const c = _calque(doc, calqueId);
  if (c.verrou) throw new Error(`calque verrouillé: ${calqueId}`);
  const pris = _idsPris(doc);
  const id = (objet.id && !pris.has(objet.id)) ? objet.id : _idLibre(doc);
  c.objets.push({ ...objet, id });
  return id;
}

export function op_supprimer(doc, ids) {
  let n = 0;
  for (const { calque, i } of _objetsCibles(doc, ids)) {
    calque.objets.splice(i, 1);
    n++;
  }
  return n;
}

function _decalerObjet(o, dx, dy) {
  switch (o.type) {
    case "rect": o.x += dx; o.y += dy; break;
    case "ellipse": o.cx += dx; o.cy += dy; break;
    case "texte": o.x += dx; o.y += dy; break;
    case "path": {
      const segs = chemin_parser(o.d);
      for (const s of segs) {
        for (let k = 0; k < s.p.length; k += 2) { s.p[k] += dx; s.p[k + 1] += dy; }
      }
      o.d = chemin_serialiser(segs);
      break;
    }
    case "groupe": (o.enfants || []).forEach((e) => _decalerObjet(e, dx, dy)); break;
  }
}

export function op_deplacer(doc, ids, dx, dy) {
  for (const { objet } of _objetsCibles(doc, ids)) _decalerObjet(objet, dx, dy);
}

function _mapperObjet(o, av, ap) {
  const sx = ap.w / av.w, sy = ap.h / av.h;
  const fx = (X) => (X - av.x) * sx + ap.x;
  const fy = (Y) => (Y - av.y) * sy + ap.y;
  switch (o.type) {
    case "rect":
      o.x = fx(o.x); o.y = fy(o.y);
      o.w = o.w * sx; o.h = o.h * sy; break;
    case "ellipse":
      o.cx = fx(o.cx); o.cy = fy(o.cy);
      o.rx = Math.abs(o.rx * sx); o.ry = Math.abs(o.ry * sy); break;
    case "texte": o.x = fx(o.x); o.y = fy(o.y); break;
    case "path": {
      const segs = chemin_parser(o.d);
      for (const s of segs) {
        for (let k = 0; k < s.p.length; k += 2) {
          s.p[k] = fx(s.p[k]); s.p[k + 1] = fy(s.p[k + 1]);
        }
      }
      o.d = chemin_serialiser(segs);
      break;
    }
    case "groupe": (o.enfants || []).forEach((e) => _mapperObjet(e, av, ap)); break;
  }
}

export function op_redimensionner(doc, ids, bboxAvant, bboxApres) {
  if (!(bboxAvant.w > 0) || !(bboxAvant.h > 0)) return;
  for (const { objet } of _objetsCibles(doc, ids)) {
    _mapperObjet(objet, bboxAvant, bboxApres);
  }
}

export function op_tourner(doc, ids, cx, cy, deg) {
  const t = `rotate(${nbc(deg)} ${nbc(cx)} ${nbc(cy)})`;
  for (const { objet } of _objetsCibles(doc, ids)) {
    objet.transform = objet.transform ? `${t} ${objet.transform}` : t;
  }
}


/* ── nœuds Bézier (T1.3) ──
   Une ANCRE = le point on-curve d'un segment M/L/C/Q (ses deux derniers
   nombres). Poignée ENTRANTE = contrôles du segment porteur (C p[2..3],
   Q p[0..1]) ; poignée SORTANTE = premier contrôle du segment C suivant.
   Le Q partage sa poignée : v1 la rattache à l'ancre de FIN du segment. */

function _trouverPath(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "path") throw new Error(`objet ${id}: pas un chemin`);
      return o;
    }
  }
  throw new Error(`chemin introuvable (ou calque verrouillé): ${id}`);
}

function _porteurs(segs) {
  const out = [];
  segs.forEach((s, k) => { if (s.c !== "Z") out.push(k); });
  return out;
}

const _fin = (s) => ({ x: s.p[s.p.length - 2], y: s.p[s.p.length - 1] });

export function chemin_ancres(segs) {
  const noeuds = _porteurs(segs);
  return noeuds.map((k, i) => {
    const s = segs[k];
    const f = _fin(s);
    const entrante = s.c === "C" ? { x: s.p[2], y: s.p[3] }
                   : s.c === "Q" ? { x: s.p[0], y: s.p[1] } : null;
    const kn = noeuds[i + 1];
    const sn = kn === undefined ? null : segs[kn];
    const sortante = sn && sn.c === "C" ? { x: sn.p[0], y: sn.p[1] } : null;
    return { i, x: f.x, y: f.y, entrante, sortante };
  });
}

function _segsDe(o) { return chemin_parser(o.d); }
function _poser(o, segs) { o.d = chemin_serialiser(segs); }

export function op_noeud_deplacer(doc, id, iAncre, dx, dy) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  const s = segs[k];
  s.p[s.p.length - 2] += dx;
  s.p[s.p.length - 1] += dy;
  if (s.c === "C") { s.p[2] += dx; s.p[3] += dy; }
  if (s.c === "Q") { s.p[0] += dx; s.p[1] += dy; }
  const kn = noeuds[iAncre + 1];
  if (kn !== undefined && segs[kn].c === "C") {
    segs[kn].p[0] += dx; segs[kn].p[1] += dy;
  }
  _poser(o, segs);
}

export function op_noeud_convertir(doc, id, iAncre) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  const ferme = segs.some((s) => s.c === "Z");
  const s = segs[k];
  const f = _fin(s);
  const a = chemin_ancres(segs)[iAncre];
  // COURBE si la poignée ENTRANTE est vive ; une ancre mixte (entrée en
  // ligne, sortie courbe) est un ANGLE — l'ancre M, sans entrante possible,
  // se juge sur sa sortante.
  const vive = (pt) => pt && (pt.x !== f.x || pt.y !== f.y);
  const estCourbe = vive(a.entrante) || (s.c === "M" && vive(a.sortante));
  const kn = noeuds[iAncre + 1];
  if (estCourbe) {
    // courbe → angle : les poignées attachées se dégénèrent sur l'ancre
    if (s.c === "C") { s.p[2] = f.x; s.p[3] = f.y; }
    if (s.c === "Q") { s.p[0] = f.x; s.p[1] = f.y; }
    if (kn !== undefined && segs[kn].c === "C") {
      segs[kn].p[0] = f.x; segs[kn].p[1] = f.y;
    }
  } else {
    // angle → courbe : poignées symétriques ± (suivant − précédent) / 4
    const ancres = chemin_ancres(segs);
    const n = ancres.length;
    const prev = iAncre > 0 ? ancres[iAncre - 1]
               : (ferme && n > 1 ? ancres[n - 1] : a);
    const next = iAncre < n - 1 ? ancres[iAncre + 1]
               : (ferme && n > 1 ? ancres[0] : a);
    const vx = (next.x - prev.x) / 4, vy = (next.y - prev.y) / 4;
    const ent = { x: f.x - vx, y: f.y - vy };
    const sor = { x: f.x + vx, y: f.y + vy };
    if (s.c === "L") {
      segs[k] = { c: "C", p: [prev.x, prev.y, ent.x, ent.y, f.x, f.y] };
    } else if (s.c === "C") { s.p[2] = ent.x; s.p[3] = ent.y; }
    else if (s.c === "Q") { s.p[0] = ent.x; s.p[1] = ent.y; }
    if (kn !== undefined) {
      const sn = segs[kn];
      const nf = _fin(sn);
      if (sn.c === "L") {
        segs[kn] = { c: "C", p: [sor.x, sor.y, nf.x, nf.y, nf.x, nf.y] };
      } else if (sn.c === "C" || sn.c === "Q") {
        sn.p[0] = sor.x; sn.p[1] = sor.y;
      }
    }
  }
  _poser(o, segs);
}

export function op_noeud_supprimer(doc, id, iAncre) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  segs.splice(k, 1);
  if (iAncre === 0) {
    if (segs.length && segs[0].c !== "Z") {
      segs[0] = { c: "M", p: [_fin(segs[0]).x, _fin(segs[0]).y] };
    }
  } else if (k < segs.length && (segs[k].c === "C" || segs[k].c === "Q")) {
    segs[k] = { c: "L", p: [_fin(segs[k]).x, _fin(segs[k]).y] };
  }
  _poser(o, segs);
}

export function op_chemin_fermer(doc, id) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  if (!segs.length || segs[segs.length - 1].c !== "Z") {
    segs.push({ c: "Z", p: [] });
  }
  _poser(o, segs);
}


/* ── calques (T1.4) : l'ordre du tableau EST l'ordre de peinture
   (le dernier est au-dessus). Un document garde toujours au moins un
   calque — la suppression du dernier est refusée. */

export function op_calque_ajouter(doc, nom) {
  const pris = new Set(doc.calques.map((c) => c.id));
  let n = 1;
  while (pris.has("c" + n)) n++;
  const id = "c" + n;
  doc.calques.push({ id, nom: nom || id, visible: true, verrou: false,
                     objets: [] });
  return id;
}

export function op_calque_renommer(doc, id, nom) {
  _calque(doc, id).nom = String(nom || "");
}

export function op_calque_reordonner(doc, id, nouvelIndex) {
  const c = _calque(doc, id);
  const i = doc.calques.indexOf(c);
  doc.calques.splice(i, 1);
  const j = Math.max(0, Math.min(doc.calques.length, nouvelIndex));
  doc.calques.splice(j, 0, c);
}

export function op_calque_visible(doc, id, visible) {
  _calque(doc, id).visible = !!visible;
}

export function op_calque_verrou(doc, id, verrou) {
  _calque(doc, id).verrou = !!verrou;
}

export function op_calque_supprimer(doc, id) {
  const c = _calque(doc, id);
  if (doc.calques.length <= 1) {
    throw new Error("un document garde au moins un calque");
  }
  doc.calques.splice(doc.calques.indexOf(c), 1);
}


/* ── apparence (T2.1) : style fusionné par patch, opacité de calque ── */

export function op_style(doc, ids, patch) {
  for (const { objet } of _objetsCibles(doc, ids)) {
    const s = { ...(objet.style || {}) };
    for (const [k, v] of Object.entries(patch || {})) {
      if (v === null) delete s[k];
      else s[k] = v;
    }
    objet.style = s;
  }
}

export function op_calque_opacite(doc, id, opacite) {
  _calque(doc, id).opacite = Math.max(0, Math.min(1, Number(opacite)));
}


/* ── groupes, ordre z, sommet (T2.3) ── */

export function sommetDe(doc, id) {
  const dedans = (g) => (g.enfants || []).some(
    (e) => e.id === id || (e.type === "groupe" && dedans(e)));
  for (const c of doc.calques) {
    for (const o of c.objets) {
      if (o.id === id) return id;
      if (o.type === "groupe" && dedans(o)) return o.id;
    }
  }
  return null;
}

export function op_grouper(doc, ids) {
  const voulu = new Set(ids);
  const cibles = [];                   // en ordre de peinture (bas → haut)
  for (const c of doc.calques) {
    if (c.verrou) continue;
    for (const o of c.objets) {
      if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
    }
  }
  if (cibles.length < 2) {
    throw new Error("grouper: au moins deux objets déverrouillés");
  }
  const hote = cibles[cibles.length - 1].calque;
  for (const { calque, objet } of cibles) {
    calque.objets.splice(calque.objets.indexOf(objet), 1);
  }
  const id = _idLibre(doc);
  hote.objets.push({ id, type: "groupe", style: {},
                     enfants: cibles.map((t) => t.objet) });
  return id;
}

export function op_degrouper(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === id);
    if (i >= 0) {
      const g = c.objets[i];
      if (g.type !== "groupe") throw new Error(`${id}: pas un groupe`);
      const enfants = g.enfants || [];
      if (g.transform) {              // le transform du groupe suit les enfants
        for (const e of enfants) {
          e.transform = e.transform ? `${g.transform} ${e.transform}`
                                    : g.transform;
        }
      }
      c.objets.splice(i, 1, ...enfants);
      return enfants.map((e) => e.id);
    }
  }
  throw new Error(`groupe introuvable (ou calque verrouillé): ${id}`);
}

export function op_ordre(doc, ids, mode) {
  if (!["devant", "derriere", "avant", "arriere"].includes(mode)) {
    throw new Error(`ordre: mode inconnu ${mode}`);
  }
  const voulu = new Set(ids);
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const dedans = c.objets.filter((o) => voulu.has(o.id));
    if (!dedans.length) continue;
    if (mode === "devant") {
      c.objets = c.objets.filter((o) => !voulu.has(o.id)).concat(dedans);
    } else if (mode === "derriere") {
      c.objets = dedans.concat(c.objets.filter((o) => !voulu.has(o.id)));
    } else if (mode === "avant") {
      for (let i = c.objets.length - 2; i >= 0; i--) {
        if (voulu.has(c.objets[i].id) && !voulu.has(c.objets[i + 1].id)) {
          [c.objets[i], c.objets[i + 1]] = [c.objets[i + 1], c.objets[i]];
        }
      }
    } else {
      for (let i = 1; i < c.objets.length; i++) {
        if (voulu.has(c.objets[i].id) && !voulu.has(c.objets[i - 1].id)) {
          [c.objets[i], c.objets[i - 1]] = [c.objets[i - 1], c.objets[i]];
        }
      }
    }
  }
}


/* ── dégradés (T2.2) : en coordonnées DOCUMENT (userSpaceOnUse) ──
   doc.degrades = {id: {type: lineaire|radial, stops:[{t, couleur,
   opacite?}], x1..y2 | cx,cy,r}}. Un fond y réfère par "grad:<id>" ; la
   compilation émet <defs> (stops triés par t) et retombe sur "none" si le
   dégradé manque — un document ne casse jamais. */

const _TYPES_DEGRADE = new Set(["lineaire", "radial"]);

function _degrades(doc) {
  if (!doc.degrades) doc.degrades = {};
  return doc.degrades;
}
function _degrade(doc, id) {
  const g = _degrades(doc)[id];
  if (!g) throw new Error(`degrade inconnu: ${id}`);
  return g;
}

export function op_degrade_creer(doc, spec) {
  if (!spec || !_TYPES_DEGRADE.has(spec.type)) {
    throw new Error("degrade: type invalide (lineaire|radial)");
  }
  const stops = (Array.isArray(spec.stops) && spec.stops.length >= 2)
    ? spec.stops
    : [{ t: 0, couleur: "#000000" }, { t: 1, couleur: "#FFFFFF" }];
  const degs = _degrades(doc);
  let n = 1;
  while (("g" + n) in degs) n++;
  const id = "g" + n;
  const g = { type: spec.type, stops: stops.map((s) => ({ ...s })) };
  if (spec.type === "lineaire") {
    g.x1 = +(spec.x1 ?? 0); g.y1 = +(spec.y1 ?? 0);
    g.x2 = +(spec.x2 ?? 1); g.y2 = +(spec.y2 ?? 0);
  } else {
    g.cx = +(spec.cx ?? 0); g.cy = +(spec.cy ?? 0); g.r = +(spec.r ?? 1);
  }
  degs[id] = g;
  return id;
}

export function op_degrade_modifier(doc, id, patch) {
  const g = _degrade(doc, id);
  for (const k of ["x1", "y1", "x2", "y2", "cx", "cy", "r"]) {
    if (patch && k in patch) g[k] = +patch[k];
  }
}

export function op_degrade_stop_ajouter(doc, id, stop) {
  const g = _degrade(doc, id);
  g.stops.push({ ...stop });
  return g.stops.length - 1;
}

export function op_degrade_stop_modifier(doc, id, i, patch) {
  const g = _degrade(doc, id);
  if (i < 0 || i >= g.stops.length) throw new Error(`stop ${i} hors bornes`);
  for (const k of ["t", "couleur", "opacite"]) {
    if (patch && k in patch) g.stops[i][k] = patch[k];
  }
}

export function op_degrade_stop_supprimer(doc, id, i) {
  const g = _degrade(doc, id);
  if (g.stops.length <= 2) throw new Error("un degrade garde au moins deux stops");
  if (i < 0 || i >= g.stops.length) throw new Error(`stop ${i} hors bornes`);
  g.stops.splice(i, 1);
}

export function op_degrade_supprimer(doc, id) {
  _degrade(doc, id);
  delete doc.degrades[id];
}


/* ── historique (T1.5) : annulation par INSTANTANÉS du JSON ──
   `capturer(doc)` AVANT chaque commande ; `annuler(courant)` rend l'état
   capturé et empile le courant côté refaire ; `refaire(courant)` fait
   l'inverse. Tout entre et sort en CLONE — aucune référence partagée. */
export class Historique {
  constructor(cap = 100) {
    this.cap = cap;
    this._avant = [];
    this._apres = [];
  }
  _clone(doc) { return JSON.parse(JSON.stringify(doc)); }
  capturer(doc) {
    this._avant.push(this._clone(doc));
    if (this._avant.length > this.cap) this._avant.shift();
    this._apres.length = 0;         // une nouvelle commande invalide refaire
  }
  peutAnnuler() { return this._avant.length > 0; }
  peutRefaire() { return this._apres.length > 0; }
  annuler(courant) {
    if (!this.peutAnnuler()) throw new Error("rien à annuler");
    this._apres.push(this._clone(courant));
    return this._avant.pop();
  }
  refaire(courant) {
    if (!this.peutRefaire()) throw new Error("rien à refaire");
    this._avant.push(this._clone(courant));
    return this._apres.pop();
  }
}


/* ── aimantation et guides (T1.6) : les guides d'abord (l'intention posée
   par l'utilisateur prime sur la grille), rien hors tolérance. Les guides
   vivent dans doc.guides {v:[x…], h:[y…]} — mutés par commandes, donc
   capturés par l'historique comme le reste du document. */

export function aimanter(v, { pas = 0, guides = [] } = {}, tol = 0) {
  let meilleur = null, ecart = Infinity;
  for (const g of guides) {
    const e = Math.abs(v - g);
    if (e <= tol && e < ecart) { meilleur = g; ecart = e; }
  }
  if (meilleur !== null) return meilleur;
  if (pas > 0) {
    const g = Math.round(v / pas) * pas;
    if (Math.abs(v - g) <= tol) return g;
  }
  return v;
}

function _axeGuides(doc, axe) {
  if (axe !== "v" && axe !== "h") throw new Error(`axe de guide inconnu: ${axe}`);
  if (!doc.guides) doc.guides = { v: [], h: [] };
  if (!Array.isArray(doc.guides[axe])) doc.guides[axe] = [];
  return doc.guides[axe];
}

export function op_guide_ajouter(doc, axe, pos) {
  const g = _axeGuides(doc, axe);
  g.push(Number(pos));
  return g.length - 1;
}

export function op_guide_deplacer(doc, axe, i, pos) {
  const g = _axeGuides(doc, axe);
  if (i < 0 || i >= g.length) throw new Error(`guide ${axe}[${i}] hors bornes`);
  g[i] = Number(pos);
}

export function op_guide_supprimer(doc, axe, i) {
  const g = _axeGuides(doc, axe);
  if (i < 0 || i >= g.length) throw new Error(`guide ${axe}[${i}] hors bornes`);
  g.splice(i, 1);
}


function _defs(doc) {
  const refs = [];
  const vus = new Set();
  const visiter = (objs) => {
    for (const o of objs) {
      const f = o.style && o.style.fond;
      if (typeof f === "string" && f.startsWith("grad:")) {
        const gid = f.slice(5);
        if (!vus.has(gid)) { vus.add(gid); refs.push(gid); }
      }
      if (o.type === "groupe") visiter(o.enfants || []);
    }
  };
  for (const c of doc.calques) visiter(c.objets);
  const degs = doc.degrades || {};
  const morceaux = [];
  for (const id of refs) {
    const g = degs[id];
    if (!g) continue;                 // référence orpheline: le repli "none"
    const stops = [...g.stops].sort((a, b) => a.t - b.t).map((s) =>
      `<stop offset="${+s.t}" stop-color="${escAttr(s.couleur)}"`
      + ((s.opacite !== undefined && +s.opacite !== 1)
         ? ` stop-opacity="${+s.opacite}"` : "") + `/>`).join("");
    morceaux.push(g.type === "lineaire"
      ? `<linearGradient id="${escAttr(id)}" gradientUnits="userSpaceOnUse"`
        + ` x1="${+g.x1}" y1="${+g.y1}" x2="${+g.x2}" y2="${+g.y2}">`
        + stops + `</linearGradient>`
      : `<radialGradient id="${escAttr(id)}" gradientUnits="userSpaceOnUse"`
        + ` cx="${+g.cx}" cy="${+g.cy}" r="${+g.r}">`
        + stops + `</radialGradient>`);
  }
  return morceaux.length ? `<defs>${morceaux.join("")}</defs>` : "";
}

export function compilerSVG(doc) {
  parserDoc(doc);
  const ctx = { degrades: doc.degrades || {} };
  const w = +doc.taille.w, h = +doc.taille.h;
  const fond = doc.fond
    ? `<rect x="0" y="0" width="${w}" height="${h}"`
      + ` fill="${escAttr(doc.fond)}" data-fond="1"/>`
    : "";
  const calques = doc.calques.map((c) => {
    const cache = c.visible === false ? ` style="display:none"` : "";
    const op = (c.opacite !== undefined && Number(c.opacite) !== 1)
      ? ` opacity="${Number(c.opacite)}"` : "";
    return `<g data-calque="${escAttr(c.id)}"`
         + ` data-nom="${escAttr(c.nom || "")}"${op}${cache}>`
         + c.objets.map((o) => compilerObjet(o, ctx)).join("") + `</g>`;
  }).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg"`
       + ` viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`
       + _defs(doc) + fond + calques + `</svg>`;
}
