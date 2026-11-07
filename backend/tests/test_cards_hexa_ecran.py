# -*- coding: utf-8 -*-
"""Card Forge — t421 (cartes hexagonales, 07/11/2026, tâche 3) à l'écran : l'aperçu hexagonal, le verso d'une carte
sans cadre, le Cadre qui dort sur un hexagone et les pièces hors périmètre.

Le VRAI core.js et le VRAI mod-frame.js sont chargés sous node, dans un contexte `vm` muni d'un faux DOM et d'une
toile qui JOURNALISE chaque appel de dessin (son empreinte) et tient la couche alpha des remplissages qui comptent
ici (fond de papier, découpe `destination-in`). Les fonctions privées (reperes, vignette) sont extraites du fichier
livré, telles quelles. Les sources d'AVANT la tâche (HEAD au moment du banc : commit 3e52a992 ou plus récent qui ne
porte pas t421_apercu) servent de témoin : un rectangle doit rendre la MÊME empreinte qu'avant.

Ce banc lit la source TRADUITE (sans `_cartes_avant_l7`) : `dzT` est une paille qui rend la clé.
Run (depuis backend/) : <embedded python> tests/test_cards_hexa_ecran.py
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
JS = RACINE / "frontend" / "cardforge" / "js"
TEMOIN = "3e52a992"          # la tâche 2 : formats et géométrie, sans aperçu hexagonal


def _source(p: pathlib.Path) -> str:
    return p.read_bytes().decode("utf-8")


def _temoin(nom: str) -> str:
    return subprocess.run(["git", "show", f"{TEMOIN}:frontend/cardforge/js/{nom}"], cwd=str(RACINE),
                          capture_output=True, check=True).stdout.decode("utf-8")


HARNAIS = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";
const [coreP, frameP, quoiP] = process.argv.slice(2);
const QUOI = JSON.parse(readFileSync(quoiP, "utf8"));

/* ── la toile qui journalise ───────────────────────────────────────────── */
let LOG = [];
const r3 = (v) => (typeof v === "number" ? Math.round(v * 1000) / 1000 : v);
const arg = (v) => (typeof v === "number" ? r3(v) : typeof v === "string" ? v
  : Array.isArray(v) ? "[" + v.map(arg).join(",") + "]" : v && v.__toile ? "toile" : v && v.__img ? "img" : typeof v);
function Ctx2D(cv) {
  const t = {
    canvas: cv, __path: [], __cur: null, __m: [1, 0, 0, 1, 0, 0], __pile: [],
    globalCompositeOperation: "source-over",
    _p(x, y) { const m = this.__m; return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]; },
    save() { this.__pile.push({ m: this.__m.slice(), op: this.globalCompositeOperation }); },
    restore() { const s = this.__pile.pop(); if (s) { this.__m = s.m; this.globalCompositeOperation = s.op; } },
    setTransform(a, b, c, d, e, f) { this.__m = [a, b, c, d, e, f]; },
    resetTransform() { this.__m = [1, 0, 0, 1, 0, 0]; },
    translate(x, y) { const m = this.__m; m[4] += m[0] * x + m[2] * y; m[5] += m[1] * x + m[3] * y; },
    scale(x, y) { const m = this.__m; m[0] *= x; m[1] *= x; m[2] *= y; m[3] *= y; },
    beginPath() { this.__path = []; this.__cur = null; },
    moveTo(x, y) { this.__cur = [this._p(x, y)]; this.__path.push(this.__cur); },
    lineTo(x, y) { if (!this.__cur) this.moveTo(x, y); else this.__cur.push(this._p(x, y)); },
    arcTo(x1, y1) { this.lineTo(x1, y1); },
    closePath() { },
    rect(x, y, w, h) { this.moveTo(x, y); this.lineTo(x + w, y); this.lineTo(x + w, y + h); this.lineTo(x, y + h); this.__cur = null; },
    _dedans(px, py) {
      let w = 0;
      for (const sp of this.__path) for (let i = 0; i < sp.length; i++) {
        const a = sp[i], b = sp[(i + 1) % sp.length];
        if ((a[1] <= py) !== (b[1] <= py)) {
          const x = a[0] + (py - a[1]) * (b[0] - a[0]) / (b[1] - a[1]);
          if (x > px) w += b[1] > a[1] ? 1 : -1;
        }
      }
      return w !== 0;
    },
    _raster(fn) {
      const W = cv.width, H = cv.height;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) fn(x, y, y * W + x);
    },
    fill() {
      /* seule la DECOUPE touche l'alpha ici : le papier est deja opaque partout */
      if (this.globalCompositeOperation === "destination-in")
        this._raster((x, y, k) => { if (!this._dedans(x + 0.5, y + 0.5)) cv.__a[k] = 0; });
    },
    fillRect(x, y, w, h) {
      const p = this._p(x, y), q = this._p(x + w, y + h);
      const x0 = Math.max(0, Math.round(Math.min(p[0], q[0]))), x1 = Math.min(cv.width, Math.round(Math.max(p[0], q[0])));
      const y0 = Math.max(0, Math.round(Math.min(p[1], q[1]))), y1 = Math.min(cv.height, Math.round(Math.max(p[1], q[1])));
      if (this.globalCompositeOperation === "source-over")
        for (let yy = y0; yy < y1; yy++) for (let xx = x0; xx < x1; xx++) cv.__a[yy * cv.width + xx] = 255;
    },
    clearRect() { },
    measureText() { return { width: 0, actualBoundingBoxAscent: 0, actualBoundingBoxDescent: 0 }; },
    getImageData(x, y, w, h) { return { data: new Uint8ClampedArray(Math.max(1, w * h * 4)), width: w, height: h }; },
    createImageData(w, h) { return { data: new Uint8ClampedArray(Math.max(1, w * h * 4)), width: w, height: h }; },
    getLineDash() { return []; },
    isPointInPath() { return false; },
  };
  const stub = () => new Proxy(function () { }, { get: (o, k) => (k === "addColorStop" ? () => { } : stub()), apply: () => stub() });
  return new Proxy(t, {
    get(o, k) {
      if (typeof k !== "string" || k.startsWith("_") || k === "canvas") return o[k];
      const v = o[k];
      if (typeof v === "function") return (...a) => { LOG.push(k + "(" + a.map(arg).join(",") + ")"); return v.apply(o, a); };
      if (v === undefined && !(k in o)) return (...a) => { LOG.push(k + "(" + a.map(arg).join(",") + ")"); return /^create/.test(k) ? stub() : undefined; };
      return v;
    },
    set(o, k, v) { if (typeof k === "string" && !k.startsWith("_")) LOG.push(k + "=" + arg(v)); o[k] = v; return true; },
  });
}
class Toile {
  constructor() { this.__toile = true; this._w = 300; this._h = 150; this.__a = null; this.style = {}; this.__ctx = null; }
  get width() { return this._w; } set width(v) { this._w = v | 0; this.__a = null; }
  get height() { return this._h; } set height(v) { this._h = v | 0; this.__a = null; }
  getContext() {
    if (!this.__a) this.__a = new Uint8Array(Math.max(1, this._w * this._h));
    if (!this.__ctx) this.__ctx = Ctx2D(this);
    return this.__ctx;
  }
  toBlob(cb) { cb(null); }
}
class Img {
  constructor() { this.__img = true; }
  set src(u) { this._src = u; setTimeout(() => { this.width = this.naturalWidth = 400; this.height = this.naturalHeight = 600; if (this.onload) this.onload(); }, 1); }
  get src() { return this._src; }
}

/* ── le faux DOM ───────────────────────────────────────────────────────── */
function el(cls, mod) {
  const classes = new Set(cls ? [cls] : []);
  const e = {
    dataset: { mod: mod }, title: "", hidden: false, textContent: "", children: [], className: cls || "",
    classList: { toggle: (c, on) => { if (on === undefined ? !classes.has(c) : on) classes.add(c); else classes.delete(c); },
      contains: (c) => classes.has(c), add: (c) => classes.add(c), remove: (c) => classes.delete(c) },
    setAttribute(k, v) { this["@" + k] = v; }, getAttribute(k) { return this["@" + k] || null; },
    style: { setProperty() { } }, addEventListener() { },
    querySelector(s) { return this.children.find((c) => c.className === s.slice(1)) || null; },
    insertBefore(n) { this.children.push(n); }, appendChild(n) { this.children.push(n); },
  };
  if (cls === "cf-panel") e.children.push(el("panel-head"));
  return e;
}
const RAIL = ["face", "frame", "type", "data", "solid", "texture", "print", "gltf", "forge3d", "capture", "edition"]
  .map((id) => el("rail-item", id));
const PANNEAUX = RAIL.map((b) => el("cf-panel", b.dataset.mod));
const SCRIPT = (nom) => ({ src: "http://h/cardforge/js/" + nom, getAttribute: () => null });
const document = {
  readyState: "loading", addEventListener() { }, baseURI: "http://h/cardforge/", currentScript: SCRIPT("core.js"),
  createElement(t) { if (t === "canvas") return new Toile(); const e = el(""); e.className = ""; return e; },
  querySelector() { return null; },
  querySelectorAll(s) { return s === ".rail-item" ? RAIL : s === ".cf-panel" ? PANNEAUX : []; },
};
const ctx = vm.createContext({ console: { log() { }, warn() { }, error() { }, info() { } }, setTimeout, clearTimeout, URL, Image: Img,
  document, dzT: (k, v) => k + (v ? JSON.stringify(v) : "") });
ctx.window = ctx;
vm.runInContext(readFileSync(coreP, "utf8"), ctx, { filename: "core.js" });
const CF = ctx.CF;
/* les objets du banc naissent DANS le contexte : sanitize() exige le prototype d'Object du moteur */
const dedans = (o) => vm.runInContext("(" + JSON.stringify(o) + ")", ctx);
/* les jetons des pieces que le banc tient : un faux module dont le fichier
   est le bon (l'identite se lit sur document.currentScript, comme au navigateur) */
function pose(id, ordre, state) {
  document.currentScript = SCRIPT("mod-" + id + ".js");
  const m = dedans({ id: id, title: id, order: ordre, state: state || {} });
  m.init = vm.runInContext("(function () { })", ctx);
  const t = CF.register(m);
  document.currentScript = null;
  return t;
}
let FRAME = null;
const P_DATA = pose("data", 4, { columns: ["nom", "art", "dos"], rows: [["Une", "recto.png", "verso.png"]] });
const P_TYPE = pose("type", 3, { slots: [{ id: "titre", box: [4, 4, 40, 8] }], seeded: true });
const P_PRINT = pose("print", 7, {});
if (frameP !== "-") {
  document.currentScript = SCRIPT("mod-frame.js");
  const fenetre = { CF: Object.assign({}, CF, { register: (m) => { const t = CF.register(m); FRAME = t; return t; } }) };
  vm.runInContext("(function (window) {" + readFileSync(frameP, "utf8") + "\n})", ctx, { filename: "mod-frame.js" })(fenetre);
  document.currentScript = null;
}
const dort = (ms) => new Promise((r) => setTimeout(r, ms));
async function rendu(face) {
  LOG = [];
  const cv = await CF.renderCard(0, { face: face });
  const a = cv.__a, W = cv.width, H = cv.height;
  const px = (x, y) => a[Math.min(H - 1, Math.max(0, Math.round(y))) * W + Math.min(W - 1, Math.max(0, Math.round(x)))];
  const log = LOG.slice();
  return { w: W, h: H, log: log, clip: log.filter((s) => s === "clip()" || s.startsWith("clip(")).length,
    draw: log.filter((s) => s.startsWith("drawImage(")),
    coin: [px(0, 0), px(W - 1, 0), px(0, H - 1), px(W - 1, H - 1)], centre: px(W / 2, H / 2),
    opaques: a.reduce((n, v) => n + (v ? 1 : 0), 0), erreurs: (cv.cfErrors || []).map((e) => e.message) };
}

const R = {};
(async function () {
  try {
    for (const q of QUOI) {
      if (q.fmt) P_PRINT.setFormat(dedans({ fmt: q.fmt, dpi: q.dpi || 150 }));
      if (q.cartes) P_DATA.setCards(dedans(q.cartes));
      if (q.cadre && FRAME) FRAME.patch(dedans(q.cadre));
      if (q.attente) await dort(q.attente);
      if (q.rendu) R[q.nom] = await rendu(q.rendu);
      if (q.doc) R[q.nom] = JSON.parse(JSON.stringify({ frame: CF.doc().frame, type: CF.doc().type, data: CF.doc().data }));
      if (q.rail) R[q.nom] = { rail: RAIL.map((b) => [b.dataset.mod, b.classList.contains("hors-hex"), b.title]),
        panneaux: PANNEAUX.map((p) => { const n = p.children.find((c) => c.className === "cf-hors-hex"); return [p.dataset.mod, n ? (n.hidden ? "" : n.textContent) : null]; }),
        hors: RAIL.map((b) => b.dataset.mod).filter((id) => typeof CF.horsHex === "function" && CF.horsHex(id)) };
      if (q.geom) R[q.nom] = CF.geom();
    }
  } catch (e) { R.erreur = String(e && e.stack || e); }
  process.stdout.write(JSON.stringify(R));
  process.exit(0);
})();
"""


def _node(tmp: pathlib.Path, core: str, frame: str | None, quoi: list) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc de l'aperçu ne peut pas tourner")
    (tmp / "harnais.mjs").write_text(HARNAIS, encoding="utf-8")
    (tmp / "core.js").write_text(core, encoding="utf-8")
    fp = "-"
    if frame is not None:
        (tmp / "mod-frame.js").write_text(frame, encoding="utf-8")
        fp = str(tmp / "mod-frame.js")
    (tmp / "quoi.json").write_text(json.dumps(quoi), encoding="utf-8")
    r = subprocess.run([node, str(tmp / "harnais.mjs"), str(tmp / "core.js"), fp, str(tmp / "quoi.json")],
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]
    out = json.loads(r.stdout)
    assert "erreur" not in out, out.get("erreur")
    return out


@pytest.fixture(scope="module")
def neuf():
    return _source(JS / "core.js"), _source(JS / "mod-frame.js")


@pytest.fixture(scope="module")
def avant():
    return _temoin("core.js"), _temoin("mod-frame.js")


SANS_CADRE = {"family": "none"}
CARTE_VERSO = [{"art": "recto.png", "back": "verso.png", "fields": {"nom": "Une"}}]
CARTE_NUE = [{"art": "recto.png", "fields": {"nom": "Une"}}]


# ═══ 1. l'aperçu d'un hexagone est DÉCOUPÉ au fond perdu ═══════════════════

def test_l_angle_d_un_hexagone_est_transparent_et_son_centre_opaque(tmp_path, neuf):
    R = _node(tmp_path, *neuf, [
        {"fmt": "hex_p50", "cartes": CARTE_NUE, "cadre": SANS_CADRE, "rendu": "front", "nom": "p"},
        {"fmt": "hex_f75", "rendu": "front", "nom": "f"},
        {"geom": True, "nom": "g"},
    ])
    for k in ("p", "f"):
        assert R[k]["coin"] == [0, 0, 0, 0], (k, R[k]["coin"])
        assert R[k]["centre"] == 255, k
        assert "globalCompositeOperation=destination-in" in R[k]["log"], k
        # un hexagone occupe 3/4 de son rectangle : le fond perdu tronqué un peu plus
        part = R[k]["opaques"] / (R[k]["w"] * R[k]["h"])
        assert 0.74 < part < 0.86, (k, part)
    assert R["g"]["forme"] == "hex" and R["g"]["corner_mm"] == 0


def test_un_rectangle_rend_la_meme_empreinte_qu_avant(tmp_path, neuf, avant):
    quoi = [
        {"fmt": "poker_us", "cartes": CARTE_NUE, "attente": 300, "rendu": "front", "nom": "recto"},
        {"rendu": "back", "nom": "verso"},
        {"cadre": SANS_CADRE, "attente": 300, "rendu": "front", "nom": "nu_recto"},
        {"cartes": CARTE_VERSO, "cadre": {"family": "deco"}, "attente": 300, "rendu": "back", "nom": "verso_motif"},
    ]
    (tmp_path / "n").mkdir()
    (tmp_path / "a").mkdir()
    N = _node(tmp_path / "n", *neuf, quoi)
    A = _node(tmp_path / "a", *avant, quoi)
    for k in ("recto", "verso", "nu_recto", "verso_motif"):
        assert N[k]["erreurs"] == [] and A[k]["erreurs"] == [], (k, N[k]["erreurs"], A[k]["erreurs"])
        assert N[k]["clip"] == A[k]["clip"], (k, N[k]["clip"], A[k]["clip"])
        assert N[k]["log"] == A[k]["log"], k
        assert "globalCompositeOperation=destination-in" not in N[k]["log"]
    assert N["recto"]["clip"] > 0 and len(N["recto"]["log"]) > 200          # le cadre a bien peint


# ═══ 2. le verso d'une carte sans cadre ════════════════════════════════════

def test_sans_cadre_le_verso_est_l_image_de_la_carte(tmp_path, neuf):
    R = _node(tmp_path, *neuf, [
        {"fmt": "poker_us", "cartes": CARTE_VERSO, "cadre": SANS_CADRE, "rendu": "back", "nom": "avec"},
        {"cartes": CARTE_NUE, "rendu": "back", "nom": "sans"},
        {"fmt": "hex_p635", "cartes": CARTE_VERSO, "rendu": "back", "nom": "hex"},
    ])
    w, h = R["avec"]["w"], R["avec"]["h"]
    # l'image (400 x 600) couvre la TOILE : 413 x 563 à 150 DPI -> échelle 1,0325
    assert len(R["avec"]["draw"]) == 1, R["avec"]["draw"]
    d = R["avec"]["draw"][0][len("drawImage("):-1].split(",")
    assert d[0] == "img" and float(d[3]) >= w - 0.01 and float(d[4]) >= h - 0.01, d
    # sans image de dos : rien n'est peint, la face reste blanche (le papier seul)
    assert R["sans"]["draw"] == [] and R["sans"]["opaques"] == R["sans"]["w"] * R["sans"]["h"]
    assert not [s for s in R["sans"]["log"] if s.startswith(("fill(", "stroke("))], R["sans"]["log"]
    # un hexagone : le verso image, puis la découpe
    assert len(R["hex"]["draw"]) == 1 and R["hex"]["coin"] == [0, 0, 0, 0] and R["hex"]["centre"] == 255


def test_un_motif_du_catalogue_n_est_pas_une_image_sans_cadre(tmp_path, neuf):
    R = _node(tmp_path, *neuf, [
        {"fmt": "poker_us", "cartes": [{"back": "lattice"}], "cadre": SANS_CADRE, "rendu": "back", "nom": "m"},
    ])
    assert R["m"]["draw"] == []


# ═══ 3. le Cadre dort sur un hexagone, et revient tel quel ═════════════════

def test_le_cadre_ne_peint_rien_sur_un_hexagone(tmp_path, neuf):
    R = _node(tmp_path, *neuf, [
        {"fmt": "hex_p50", "cartes": CARTE_NUE, "attente": 300, "rendu": "front", "nom": "cadre"},
        {"rendu": "back", "nom": "cadre_dos"},
        {"cadre": SANS_CADRE, "attente": 300, "rendu": "front", "nom": "nu"},
        {"rendu": "back", "nom": "nu_dos"},
    ])
    assert R["cadre"]["log"] == R["nu"]["log"]
    assert R["cadre_dos"]["log"] == R["nu_dos"]["log"]
    assert R["cadre"]["clip"] == 0


def test_hexagone_puis_retour_rectangle_rend_le_document_de_depart(tmp_path, neuf):
    R = _node(tmp_path, *neuf, [
        {"fmt": "poker_us", "cartes": CARTE_VERSO, "cadre": {"family": "deco", "back": "lattice"},
         "attente": 300, "rendu": "front", "nom": "r0"},
        {"rendu": "back", "attente": 300, "doc": True, "nom": "depart"},
        {"fmt": "hex_p50", "rendu": "front", "nom": "h1"},
        {"rendu": "back", "attente": 400, "doc": True, "nom": "pendant"},
        {"fmt": "poker_us", "rendu": "front", "nom": "r1"},
        {"rendu": "back", "attente": 400, "doc": True, "nom": "retour"},
    ])
    assert R["depart"]["frame"].get("art_window"), R["depart"]["frame"]       # le cadre avait publié sa fenêtre
    assert R["pendant"] == R["depart"]
    assert R["retour"] == R["depart"]
    assert R["r1"]["log"] == R["r0"]["log"]                                 # le cadre revient au pixel près


# ═══ 4. reperes et vignette : des polygones ════════════════════════════════

def _fonction(src: str, nom: str) -> str:
    k = src.index("function " + nom + "(")
    i, n = src.index("{", k), 0
    for j in range(i, len(src)):
        if src[j] == "{":
            n += 1
        elif src[j] == "}":
            n -= 1
            if n == 0:
                return src[k:j + 1]
    raise AssertionError(nom)


def _bloc(src: str, debut: str, fin: str) -> str:
    k = src.index(debut)
    return src[k:src.index(fin, k) + len(fin)]


BANC_REPERES = r"""
import { readFileSync } from "node:fs";
const CODE = readFileSync(process.argv[2], "utf8");
const CAS = JSON.parse(readFileSync(process.argv[3], "utf8"));
let LOG = [];
const r3 = (v) => (typeof v === "number" ? Math.round(v * 1000) / 1000 : v);
const ctx = new Proxy({}, { get: (o, k) => (k in o ? o[k] : (...a) => { LOG.push(k + "(" + a.map(r3).join(",") + ")"); }),
  set: (o, k, v) => { LOG.push(k + "=" + (Array.isArray(v) ? "[" + v.join(",") + "]" : r3(v))); return true; } });
const cv = { width: 0, height: 0, style: {}, getContext: () => ctx };
const mod = new Function("dzT", "devicePixelRatio", CODE + "\nreturn { guidesPainter: guidesPainter, galThumb: typeof galThumb === 'function' ? galThumb : null, hexContours: typeof hexContours === 'function' ? hexContours : null };")((k) => k, 1);
const out = {};
for (const c of CAS.reperes) { LOG = []; mod.guidesPainter(ctx, Object.assign({ mm2px: (v) => v / 25.4 * c.dpi }, c)); out[c.fmt] = LOG.slice();
  if (mod.hexContours && c.forme === "hex") out[c.fmt + "_contours"] = mod.hexContours(c); }
for (const m of CAS.vignettes) { LOG = []; mod.galThumb(cv, m); out["v_" + m.format] = LOG.slice(); }
process.stdout.write(JSON.stringify(out));
"""


def _reperes(tmp: pathlib.Path, core: str, geoms: list, vignettes: list) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    morceaux = [_bloc(core, "const FORMATS = [", "];"), "const FMT_BY_ID = {}; FORMATS.forEach((f) => { FMT_BY_ID[f.id] = f; });",
                'const DEFAULT_FMT = "poker_eu";', "const GAL_THUMB_W = 132;",
                _bloc(core, "const GAL_HEX = ", ";"), _fonction(core, "isPlain"), _fonction(core, "galColor"),
                _fonction(core, "galRect"), _fonction(core, "galThumb"), _fonction(core, "guidesPainter")]
    if "CF-HEX-BEGIN" in core:
        morceaux.insert(0, _bloc(core, "/* ═══ CF-HEX-BEGIN ═══ */", "/* ═══ CF-HEX-END ═══ */"))
    if "L'APERCU HEXAGONAL" in core:
        morceaux.insert(1, _bloc(core, "/* ═══ t421 : L'APERCU HEXAGONAL", "/* ═══ fin t421 ═══ */"))
    (tmp / "code.js").write_text("\n".join(morceaux), encoding="utf-8")
    (tmp / "banc.mjs").write_text(BANC_REPERES, encoding="utf-8")
    (tmp / "cas.json").write_text(json.dumps({"reperes": geoms, "vignettes": vignettes}), encoding="utf-8")
    r = subprocess.run([node, str(tmp / "banc.mjs"), str(tmp / "code.js"), str(tmp / "cas.json")],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _geoms(tmp, core):
    R = _node(tmp, core, None, [{"fmt": "hex_p50", "dpi": 300, "geom": True, "nom": "hex"},
                                {"fmt": "poker_us", "dpi": 300, "geom": True, "nom": "rect"}])
    return R["hex"], R["rect"]


def test_les_reperes_d_un_hexagone_sont_trois_polygones(tmp_path, neuf, avant):
    (tmp_path / "g").mkdir()
    gh, gr = _geoms(tmp_path / "g", neuf[0])
    (tmp_path / "n").mkdir(); (tmp_path / "a").mkdir()
    N = _reperes(tmp_path / "n", neuf[0], [gh, gr], [{"format": "hex_f50"}, {"format": "poker_us"}])
    A = _reperes(tmp_path / "a", avant[0], [gr], [{"format": "poker_us"}])
    hexa = N["hex_p50"]
    assert not [s for s in hexa if s.startswith("strokeRect(")], hexa
    assert hexa.count("stroke()") == 3
    assert [s for s in hexa if s.startswith("strokeStyle=")] == ["strokeStyle=#00b7ff", "strokeStyle=#ff2d92", "strokeStyle=#33d18b"]
    # la coupe passe par les six sommets de hexContours, en px
    k = 300 / 25.4
    coupe = N["hex_p50_contours"]["coupe"]
    pts = [tuple(float(v) for v in s[s.index("(") + 1:-1].split(","))
           for s in hexa if s.startswith(("moveTo(", "lineTo("))]
    for x, y in coupe:
        assert any(abs(px - x * k) < 0.002 and abs(py - y * k) < 0.002 for px, py in pts), (x, y)
    # un rectangle : les mêmes repères qu'avant, la même vignette qu'avant
    assert N["poker_us"] == A["poker_us"]
    assert N["v_poker_us"] == A["v_poker_us"]
    v = N["v_hex_f50"]
    assert "globalCompositeOperation=destination-in" in v and not [s for s in v if s.startswith("strokeRect(")]


# ═══ 5. les pièces hors périmètre le disent ════════════════════════════════

def test_les_pieces_hors_perimetre_le_disent_au_rail_et_au_panneau(tmp_path, neuf):
    R = _node(tmp_path, neuf[0], None, [
        {"fmt": "hex_p50", "rail": True, "nom": "hex"},
        {"fmt": "poker_us", "rail": True, "nom": "rect"},
    ])
    hors = ["frame", "solid", "texture", "gltf", "forge3d", "capture", "edition"]
    assert sorted(R["hex"]["hors"]) == sorted(hors)
    for mod, marque, titre in R["hex"]["rail"]:
        assert marque == (mod in hors), mod
        assert ("cartes.hexa.non_gere" in titre) == (mod in hors), (mod, titre)
    assert dict(R["hex"]["panneaux"]) == {m: ("cartes.hexa.non_gere" if m in hors else None)
                                          for m, _ in R["hex"]["panneaux"]}
    assert not [m for m, marque, t in R["rect"]["rail"] if marque or "non_gere" in t]
    assert all(not txt for _, txt in R["rect"]["panneaux"])


def test_la_phrase_est_traduite():
    d = json.loads((RACINE / "frontend" / "shared" / "i18n" / "cartes.json").read_text(encoding="utf-8"))
    fr, en = d["cartes.hexa.non_gere"]["fr"], d["cartes.hexa.non_gere"]["en"]
    assert "hexagonales" in fr and "hexagonal" in en


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
