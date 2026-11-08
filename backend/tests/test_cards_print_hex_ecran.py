# -*- coding: utf-8 -*-
"""Card Forge — t421 (cartes hexagonales, 08/11/2026, tâche 8) : l'ÉCRAN D'IMPRESSION HEXAGONAL.

Le VRAI `mod-print.js` (source traduite, livrée) est chargé ENTIER sous node, dans un contexte `vm` muni d'un CF de
paille (format, cartes, événements, jeton M dont l'API JOURNALISE chaque appel) et d'un faux DOM qui sait répondre aux
sélecteurs `[data-x="v"]` du panneau. `dzT` rend le FRANÇAIS du dictionnaire `cartes.json` (une clé absente rend
`??clé`). Le panneau est initialisé, puis piloté par ses propres écouteurs (clic, changement, `core:geom`).

Ce qui est jugé :
- un deck HEXAGONAL rend le bloc `data-role="hex"` (et le gabarit de dessin de la tâche 6, visible), n'appelle ni
  `layoutOf` ni les routes `layout` / `preflight` ; il demande `hex/plan` avec la gouttière par défaut
  `2 × fond perdu`, dessine la page depuis le plan du serveur, affiche TEL QUEL le message d'un refus ; « PDF
  d'impression » rend les cartes par `CF.cardBlob` et les envoie à `hex/pdf` (versos en recto verso) ; « Fichier de
  coupe (ZIP) » appelle `hex/coupe` ; les réglages (feuille, marge, gouttière, recto verso, trait) se patchent sous
  la seule clé `hexa` ;
- un deck RECTANGULAIRE rend EXACTEMENT le panneau d'avant la tâche 6 (témoin 5425375b) : même HTML, mêmes appels
  réseau, aucun `print/hex` ; un aller-retour rectangle -> hexagone -> rectangle rend le même panneau ;
- la table des formats nomme chaque hexagone par son libellé traduit (`CF.libelleFormat`), sans toucher aux lignes
  rectangulaires ;
- chaque clé `cartes.print.hex_*` du module existe en FR et en EN.
Run (depuis backend/) : & $PY tests/test_cards_print_hex_ecran.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.services.cards import contract as CT, print_hex as PHX  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
JSF = RACINE / "frontend" / "cardforge" / "js" / "mod-print.js"
DICO = RACINE / "frontend" / "shared" / "i18n" / "cartes.json"
TEMOIN = "5425375b"          # la tâche 5 : le panneau d'impression d'avant tout ajout hexagonal

HARNAIS = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";
const [srcP, confP] = process.argv.slice(2);
const SRC0 = readFileSync(srcP, "utf8");
const CONF = JSON.parse(readFileSync(confP, "utf8"));
const OUT = {};
const APPELS = [], TRACE = [], TOASTS = [], DL = [], PATCHS = [], BLOBS = [], DESSIN = [];
/* l'espion de layoutOf : posé dans la source, au début de la fonction */
const SRC = SRC0.replace("function layoutOf(st, g, n) {", "function layoutOf(st, g, n) { __TRACE.push('layoutOf');");

/* ── le faux DOM ─────────────────────────────────────────────────────────── */
const camel = (s) => s.replace(/-([a-z])/g, (m, c) => c.toUpperCase());
function mkCtx() {
  const t = {};
  return new Proxy(t, {
    get(o, k) {
      if (k in o) return o[k];
      if (k === "measureText") return () => ({ width: 10 });
      if (k === "getImageData") return () => ({ data: new Uint8ClampedArray(4) });
      return (...a) => { DESSIN.push([String(k)].concat(a.map((v) => typeof v === "number" ? Math.round(v * 1000) / 1000 : typeof v))); };
    },
    set(o, k, v) { o[k] = v; if (k === "fillStyle" || k === "strokeStyle") DESSIN.push(["set", k, String(v)]); return true; },
  });
}
function mkEl(attr, val, hidden) {
  const ds = {};
  if (attr && attr.indexOf("data-") === 0) ds[camel(attr.slice(5))] = val;
  const cls = new Set();
  const e = {
    dataset: ds, innerHTML: "", textContent: "", hidden: !!hidden, value: "", checked: false, disabled: false,
    style: {}, width: 264, height: 330, _attrs: {},
    setAttribute(k, v) { this._attrs[k] = String(v); }, getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    removeAttribute(k) { delete this._attrs[k]; },
    classList: { toggle(c, v) { if (v === undefined) v = !cls.has(c); if (v) cls.add(c); else cls.delete(c); return v; },
      add(c) { cls.add(c); }, remove(c) { cls.delete(c); }, contains(c) { return cls.has(c); } },
    querySelectorAll() { return []; }, querySelector() { return null; }, addEventListener() { }, appendChild() { },
    closest() { return null; }, getContext() { return CTX; }, focus() { }, setPointerCapture() { },
    getBoundingClientRect() { return { width: 264, height: 330, left: 0, top: 0 }; },
  };
  return e;
}
const CTX = mkCtx();
let HTML = "", CACHE = {};
function cacheEl(attr, val) {
  const k = attr + "=" + val;
  if (!CACHE[k]) {
    const i = HTML.indexOf(attr + '="' + val + '"');
    const a = HTML.lastIndexOf("<", i), z = HTML.indexOf(">", i);
    CACHE[k] = mkEl(attr, val, /\shidden(\s|>|=)/.test(HTML.slice(a, z + 1)));
  }
  return CACHE[k];
}
function trouve(sel) {
  sel = sel.trim();
  const m = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(sel);
  if (!m) return [];
  if (m[2] != null) return HTML.indexOf(m[1] + '="' + m[2] + '"') >= 0 ? [cacheEl(m[1], m[2])] : [];
  const out = [], re = new RegExp("\\s" + m[1] + '="([^"]*)"', "g");
  let r;
  while ((r = re.exec(HTML))) out.push(cacheEl(m[1], r[1]));
  return out;
}
const ECOUTE = {};
/* vague finale (C5) : le sous-titre statique de l'onglet (index.html, .panel-head .hint), que le panneau peut changer */
const HINT = { dataset: {}, textContent: "" };
const PANNEAU = { querySelector: (s) => (s === ".panel-head .hint" ? HINT : null) };
const HOST = {
  get innerHTML() { return HTML; }, set innerHTML(v) { HTML = String(v); CACHE = {}; },
  querySelector(sel) { return sel.split(",").map(trouve).reduce((a, b) => a.concat(b), [])[0] || null; },
  querySelectorAll(sel) { return sel.split(",").map(trouve).reduce((a, b) => a.concat(b), []); },
  addEventListener(n, f) { (ECOUTE[n] = ECOUTE[n] || []).push(f); }, appendChild() { },
  closest(s) { return s === ".cf-panel" ? PANNEAU : null; },
};
const document = { createElement: () => mkEl(), body: { appendChild() { } }, addEventListener() { },
  getElementById() { return null; } };

/* ── dzT : le français du dictionnaire ──────────────────────────────────── */
const DIC = CONF.dico;
HINT.textContent = DIC["cartes.page.print_hint"].fr;
function dzT(k, v) {
  const e = DIC[k];
  if (!e) return "??" + k;
  return String(e.fr).replace(/\{(\w+)\}/g, (m, n) => (v && n in v ? String(v[n]) : m));
}

/* ── le CF de paille ─────────────────────────────────────────────────────── */
let GEOM = CONF.geom;
const DOC = { name: "Mon jeu", format: CONF.format, print: {} };
const EV = {};
const etat = (o) => JSON.parse(JSON.stringify(o));
let PLAN_ERR = null, BLOB_ERR = null;
function api(m, sub, b) {
  const corps = b == null ? null : (typeof FormData !== "undefined" && b instanceof FormData)
    ? { spec: JSON.parse(b.get("spec")), fronts: b.getAll("fronts").length, backs: b.getAll("backs").length } : etat(b);
  APPELS.push({ m: m, sub: sub, b: corps });
}
const M = {
  api: {
    get: async (sub) => { api("GET", sub); if (sub === "icc") { const e = new Error("absent"); e.missing = true; throw e; } return {}; },
    post: async (sub, b) => {
      api("POST", sub, b);
      if (sub === "hex/plan") { if (PLAN_ERR) throw new Error(PLAN_ERR); return etat(CONF.plan); }
      if (sub === "preflight") return { rows: [], errors: 0, warnings: 0 };
      return {};
    },
    blob: async (m, sub, b) => {
      api(m, sub, b);
      if (BLOB_ERR && BLOB_ERR.sub === sub) throw new Error(BLOB_ERR.status + " " + BLOB_ERR.texte);
      const o = { size: 1234, sub: sub }; BLOBS.push(o); return o;
    },
    raw: async (m, sub, b) => {
      api("RAW " + m, sub, b);
      if (BLOB_ERR && BLOB_ERR.sub === sub)
        return { ok: false, status: BLOB_ERR.status, json: async () => ({ detail: BLOB_ERR.detail }) };
      return { ok: true, status: 200, json: async () => ({}) };
    },
    del: async (sub) => { api("DELETE", sub); return {}; },
  },
  patch(o) { PATCHS.push(etat(o)); Object.keys(o).forEach((k) => { DOC.print[k] = etat(o[k]); }); emit("core:doc", { id: "print" }); },
  setFormat(o) { },
  emit() { },
};
function emit(n, p) { (EV[n] || []).forEach((f) => f(p)); }
let REG = null;
const CF = {
  FORMATS: CONF.formats, DPIS: [150, 300, 600],
  geom: () => GEOM, geomOf: (id) => CONF.geoms[id], nativeBleed: (id) => CONF.geoms[id].bleed_mm,
  doc: () => DOC, cards: () => CONF.cartes.map((i) => ({ i: i, fields: {} })), get: (p, d) => d, current: () => 0,
  on: (n, f) => { (EV[n] = EV[n] || []).push(f); }, toast: (t, e) => { TOASTS.push([String(t), !!e]); }, busy() { },
  cardBlob: async (k, o) => { TRACE.push("cardBlob:" + k + ":" + o.face); return new Blob(["x"], { type: "image/png" }); },
  download: (b, n) => { DL.push(n); },
  libelleFormat: (id) => "LIB[" + id + "]",
  gabaritUrl: (fmt, ext, o) => "/api/cards/gabarit/" + fmt + "." + ext + "?bleed_mm=" + o.bleed_mm,
  register: (mod) => { REG = mod; return M; },
};
const ctx = vm.createContext({ window: { CF: CF }, CF: CF, dzT: dzT, document: document, console: console,
  getComputedStyle: () => ({ color: "rgb(0, 0, 0)" }), setTimeout: setTimeout, clearTimeout: clearTimeout,
  performance: performance, devicePixelRatio: 1, FormData: FormData, Blob: Blob, __TRACE: TRACE });
vm.runInContext(SRC, ctx, { filename: "mod-print.js" });
const dort = (ms) => new Promise((r) => setTimeout(r, ms));
function clic(act, extra) {
  const cible = { dataset: Object.assign({ act: act }, extra || {}) };
  const ev = { target: { closest: (s) => (s === "[data-act]" ? cible : null) } };
  (ECOUTE.click || []).forEach((f) => f(ev));
}
function clicSeg(seg, v) {
  const b = { dataset: { v: v }, closest: (s) => (s === "[data-hxseg]" ? { dataset: { hxseg: seg } } : null) };
  const ev = { target: { closest: (s) => (s === "[data-hxseg] .seg-b" ? b : null) } };
  (ECOUTE.click || []).forEach((f) => f(ev));
}
function change(hx, v, checked) {
  const t = { dataset: { hx: hx }, value: String(v), checked: !!checked, id: "" };
  (ECOUTE.change || []).forEach((f) => f({ target: t }));
}
function photo(k) { OUT[k] = { html: HTML, appels: etat(APPELS), trace: TRACE.slice(), hint: HINT.textContent }; }
function role(r) { const e = HOST.querySelector('[data-role="' + r + '"]'); return e ? { html: e.innerHTML, hidden: e.hidden, href: e.getAttribute("href") } : null; }

(async function () {
  await REG.init(HOST);
  await dort(900);
  photo("init");
  OUT.fmts = role("fmts");
  OUT.gabhex = role("gabhex"); OUT.gabpng = role("gabhex-png");
  OUT.hexread = role("hex-read"); OUT.hexerr = role("hex-err");
  OUT.dessin = DESSIN.slice();
  for (const pas of CONF.scenario || []) {
    APPELS.length = 0; TRACE.length = 0; TOASTS.length = 0; DL.length = 0; PATCHS.length = 0; DESSIN.length = 0;
    if (pas.erreur !== undefined) PLAN_ERR = pas.erreur;
    if (pas.blobErr !== undefined) BLOB_ERR = pas.blobErr;
    if (pas.geom) { GEOM = pas.geom; DOC.format = pas.format; emit("core:geom", {}); }
    if (pas.clic) clic(pas.clic);
    if (pas.seg) clicSeg(pas.seg[0], pas.seg[1]);
    if (pas.change) change(pas.change[0], pas.change[1], pas.change[2]);
    await dort(pas.attente || 700);
    OUT[pas.nom] = { html: HTML, appels: etat(APPELS), trace: TRACE.slice(), toasts: TOASTS.slice(), dl: DL.slice(),
      patchs: etat(PATCHS), print: etat(DOC.print), hexerr: role("hex-err"), hexread: role("hex-read"), dessin: DESSIN.slice(),
      hint: HINT.textContent };
  }
  process.stdout.write(JSON.stringify(OUT));
  process.exit(0);
})().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(2); });
"""


def _dico() -> dict:
    return json.loads(DICO.read_bytes().decode("utf-8"))


def _formats() -> list:
    out = []
    for fid, f in CT.FORMATS.items():
        d = {"id": fid, "label": f["label"], "unit": f["unit"], "trim_mm": list(f["trim_mm"])}
        if f.get("forme"):
            d["forme"], d["orientation"] = f["forme"], f["orientation"]
        out.append(d)
    return out


def _geoms() -> dict:
    return {fid: CT.geom(fid, 300).to_dict() for fid in CT.FORMATS}


def _fmt(fid: str) -> dict:
    g = CT.geom(fid, 300)
    return {"fmt": fid, "dpi": 300, "bleed_mm": g.bleed_mm, "safe_mm": g.safe_mm, "corner_mm": g.corner_mm}


GHEX = CT.geom("hex_p50", 300)
PLAN = PHX.plan_hex_dict(PHX.plan_hex(GHEX, "a4", 12, 6, 3))


def _source(rev: str | None) -> str:
    if rev is None:
        return JSF.read_bytes().decode("utf-8")
    return subprocess.run(["git", "show", f"{rev}:frontend/cardforge/js/mod-print.js"], cwd=str(RACINE),
                          capture_output=True, check=True).stdout.decode("utf-8")


def _node(tmp_path, src: str, fmt: str, scenario=None) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le banc d'écran ne peut pas tourner")
    (tmp_path / "h.mjs").write_text(HARNAIS, encoding="utf-8")
    (tmp_path / "src.js").write_text(src, encoding="utf-8")
    conf = {"dico": _dico(), "formats": _formats(), "geoms": _geoms(), "geom": CT.geom(fmt, 300).to_dict(),
            "format": _fmt(fmt), "cartes": [0, 1, 2], "plan": PLAN, "scenario": scenario or []}
    (tmp_path / "conf.json").write_text(json.dumps(conf), encoding="utf-8")
    r = subprocess.run([node, str(tmp_path / "h.mjs"), str(tmp_path / "src.js"), str(tmp_path / "conf.json")],
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _subs(appels) -> list:
    return [a["sub"] for a in appels]


# ── l'hexagone ─────────────────────────────────────────────────────────────────────────────────────────────────────

def test_hexagone_panneau_propre_sans_layout_ni_preflight(tmp_path):
    R = _node(tmp_path, _source(None), "hex_p50")
    init = R["init"]
    html = init["html"]
    assert 'data-role="hex"' in html
    # ni layoutOf, ni la vérification de plan rectangulaire, ni le contrôle avant vol
    assert "layoutOf" not in init["trace"]
    subs = _subs(init["appels"])
    assert "layout" not in subs and "preflight" not in subs, subs
    # aucun bloc rectangulaire : ni planche, ni contrôle avant vol, ni gabarits d'imprimeur
    for r in ('data-role="plan"', 'data-role="pf"', 'data-role="gabs"', 'data-act="pdf"', 'data-act="png"'):
        assert r not in html, r
    assert "??" not in html, re.findall(r"\?\?[\w.]+", html)
    # le gabarit de dessin de la tâche 6 fait partie du panneau, visible, adresses posées
    assert R["gabhex"] and R["gabhex"]["hidden"] is False
    assert R["gabpng"]["href"] == "/api/cards/gabarit/hex_p50.png?bleed_mm=3"
    # les deux téléchargements, nommés comme la brève
    assert "PDF d'impression" in html and "Fichier de coupe (ZIP)" in html
    assert 'data-act="hexpdf"' in html and 'data-act="hexcoupe"' in html
    # réglages : feuilles A4 / Letter / A3 (pas « 1 carte »), marge, gouttière, recto verso, trait
    for v in ('data-v="a4"', 'data-v="letter"', 'data-v="a3"'):
        assert v in html
    assert 'data-v="card"' not in html
    for k in ("marge_mm", "gouttiere_mm", "duplex", "trait"):
        assert f'data-hx="{k}"' in html, k
    # le rappel : couper recto dessus
    assert "recto dessus" in html


def test_hexagone_plan_demande_avec_la_gouttiere_de_deux_fonds_perdus(tmp_path):
    R = _node(tmp_path, _source(None), "hex_p50")
    plans = [a for a in R["init"]["appels"] if a["sub"] == "hex/plan"]
    assert plans, _subs(R["init"]["appels"])
    assert plans[-1]["m"] == "POST"
    assert plans[-1]["b"] == {"sheet": "a4", "marge_mm": 12, "gouttiere_mm": 6, "n_cards": 3,
                              "trait": False, "duplex": False}
    # la lecture du plan servi : cartes par page et pages
    lu = R["hexread"]["html"]
    assert ">13<" in lu and ">1<" in lu, lu
    # la page est DESSINÉE depuis le plan : 13 cases (6 sommets chacune), 3 repères
    d = R["dessin"]
    assert sum(1 for x in d if x[0] == "closePath") >= PLAN["par_page"], d[:40]
    assert sum(1 for x in d if x[0] == "arc") == 3
    # le premier sommet de la première case : (24 + 25) mm sur la feuille, à l'échelle de l'aperçu
    sc = min(264 / 210.0, 330 / 297.0)
    mv = [x for x in d if x[0] == "moveTo"]
    assert any(abs(x[1] - round(49 * sc, 3)) < 0.01 and abs(x[2] - round(22.6377 * sc, 3)) < 0.01 for x in mv), mv[:5]


def test_hexagone_refus_du_serveur_affiche_tel_quel(tmp_path):
    msg = "La gouttière (4 mm) est plus petite que 2 × le fond perdu (6 mm) : les fonds perdus se chevaucheraient."
    R = _node(tmp_path, _source(None), "hex_p50", [
        {"nom": "refus", "erreur": msg, "change": ["gouttiere_mm", "4"]},
        {"nom": "pdf", "clic": "hexpdf"},
    ])
    r = R["refus"]
    assert r["patchs"] == [{"hexa": {"gouttiere_mm": 4}}]
    assert [a["b"]["gouttiere_mm"] for a in r["appels"] if a["sub"] == "hex/plan"][-1] == 4
    assert "La gouttière (4 mm) est plus petite que 2 × le fond perdu (6 mm)" in r["hexerr"]["html"]
    # un export sur un plan refusé ne part pas : la phrase du serveur, aucune carte rendue
    p = R["pdf"]
    assert "hex/pdf" not in _subs(p["appels"]) and not any(t.startswith("cardBlob") for t in p["trace"])
    assert any(msg[:30] in t[0] and t[1] for t in p["toasts"]), p["toasts"]


def test_hexagone_pdf_et_coupe(tmp_path):
    R = _node(tmp_path, _source(None), "hex_p50", [
        {"nom": "pdf", "clic": "hexpdf"},
        {"nom": "dup", "change": ["duplex", "", True]},
        {"nom": "pdf2", "clic": "hexpdf"},
        {"nom": "coupe", "clic": "hexcoupe"},
        {"nom": "a3", "seg": ["sheet", "a3"]},
        {"nom": "trait", "change": ["trait", "", True]},
        {"nom": "marge", "change": ["marge_mm", "15"]},
    ])
    p = R["pdf"]
    assert [t for t in p["trace"] if t.startswith("cardBlob")] == ["cardBlob:0:front", "cardBlob:1:front",
                                                                    "cardBlob:2:front"]
    env = [a for a in p["appels"] if a["sub"] == "hex/pdf"]
    assert len(env) == 1 and env[0]["m"] == "POST"
    assert env[0]["b"]["spec"] == {"sheet": "a4", "marge_mm": 12, "gouttiere_mm": 6, "n_cards": 3,
                                   "trait": False, "duplex": False}
    assert env[0]["b"]["fronts"] == 3 and env[0]["b"]["backs"] == 0
    assert len(p["dl"]) == 1 and p["dl"][0].endswith(".pdf")
    assert R["dup"]["print"]["hexa"]["duplex"] is True
    p2 = R["pdf2"]
    assert sorted(t for t in p2["trace"] if t.startswith("cardBlob")) == sorted(
        [f"cardBlob:{k}:{f}" for k in range(3) for f in ("front", "back")])
    env2 = [a for a in p2["appels"] if a["sub"] == "hex/pdf"][0]
    assert env2["b"]["spec"]["duplex"] is True and env2["b"]["backs"] == 3
    c = R["coupe"]
    cz = [a for a in c["appels"] if a["sub"] == "hex/coupe"]
    assert len(cz) == 1 and cz[0]["m"] == "POST" and cz[0]["b"]["duplex"] is True and cz[0]["b"]["n_cards"] == 3
    assert not any(t.startswith("cardBlob") for t in c["trace"])
    assert len(c["dl"]) == 1 and c["dl"][0].endswith(".zip")
    assert R["a3"]["print"]["hexa"]["sheet"] == "a3"
    assert [a["b"]["sheet"] for a in R["a3"]["appels"] if a["sub"] == "hex/plan"][-1] == "a3"
    assert R["trait"]["print"]["hexa"]["trait"] is True
    dern = [a["b"] for a in R["marge"]["appels"] if a["sub"] == "hex/plan"][-1]
    assert dern == {"sheet": "a3", "marge_mm": 15, "gouttiere_mm": 6, "n_cards": 3, "trait": True, "duplex": True}
    # toujours rien de rectangulaire
    for k in ("pdf", "dup", "pdf2", "coupe", "a3", "trait", "marge"):
        s = _subs(R[k]["appels"])
        assert "layout" not in s and "preflight" not in s and "pdf" not in s and "sheet" not in s, (k, s)
        assert "layoutOf" not in R[k]["trace"], k


def test_hexagone_refus_des_exports_avec_la_phrase_du_serveur(tmp_path):
    """Fix 1 : M.api.blob ne garde que « 400 Bad Request » ; la phrase du serveur est relue par M.api.raw et
    montrée ÉCHAPPÉE, encadrée par l'action, dans le panneau et le toast."""
    d400 = "recto: la carte mesure 600x700, la géométrie impose 661x753 <b>"
    d409 = "Recto-verso demandé sans aucun verso reçu"
    R = _node(tmp_path, _source(None), "hex_p50", [
        {"nom": "pdf", "blobErr": {"sub": "hex/pdf", "status": 400, "texte": "Bad Request", "detail": d400},
         "clic": "hexpdf"},
        {"nom": "coupe", "blobErr": {"sub": "hex/coupe", "status": 409, "texte": "Conflict", "detail": d409},
         "clic": "hexcoupe"},
    ])
    p, c = R["pdf"], R["coupe"]
    assert "RAW POST" in [a["m"] for a in p["appels"] if a["sub"] == "hex/pdf"]
    assert ("PDF d'impression refusé : recto: la carte mesure 600x700, la géométrie impose 661x753 &lt;b&gt;"
            in p["hexerr"]["html"]), p["hexerr"]
    assert "<b>" not in p["hexerr"]["html"]
    assert any(t[1] and t[0] == "PDF d'impression refusé : " + d400 for t in p["toasts"]), p["toasts"]
    assert not p["dl"] and "Bad Request" not in p["hexerr"]["html"]
    assert "Fichier de coupe refusé : " + d409 in c["hexerr"]["html"], c["hexerr"]
    assert any(t[1] and t[0] == "Fichier de coupe refusé : " + d409 for t in c["toasts"]), c["toasts"]
    assert not c["dl"] and "Conflict" not in c["hexerr"]["html"]


# ── le rectangle : le panneau d'avant ──────────────────────────────────────────────────────────────────────────────

def _lignes_rect(html: str) -> list:
    return [b for b in re.findall(r'<button class="cf-print-row.*?</button>', html) if 'data-fmt="hex_' not in b]


def test_rectangle_identique_au_temoin(tmp_path):
    a = _node(tmp_path, _source(TEMOIN), "poker_eu")
    b = _node(tmp_path, _source(None), "poker_eu")
    assert b["init"]["html"] == a["init"]["html"]
    assert b["init"]["appels"] == a["init"]["appels"]
    assert "layoutOf" in b["init"]["trace"]
    assert not any(x["sub"].startswith("hex/") for x in b["init"]["appels"])
    assert 'data-role="hex"' not in b["init"]["html"]
    assert _lignes_rect(b["fmts"]["html"]) == _lignes_rect(a["fmts"]["html"]) and len(_lignes_rect(a["fmts"]["html"])) == 12


def test_table_des_formats_nomme_chaque_hexagone(tmp_path):
    R = _node(tmp_path, _source(None), "poker_eu")
    html = R["fmts"]["html"]
    for fid in CT.FORMATS:
        if CT.is_hex(fid):
            ligne = re.search(r'<button class="cf-print-row[^>]*data-fmt="' + fid + r'".*?</button>', html).group(0)
            assert '<span class="cf-print-nm">LIB[' + fid + "]</span>" in ligne, ligne[:200]


def test_aller_retour_rectangle_hexagone_rectangle(tmp_path):
    a = _node(tmp_path, _source(TEMOIN), "poker_eu")
    R = _node(tmp_path, _source(None), "poker_eu", [
        {"nom": "hex", "geom": GHEX.to_dict(), "format": _fmt("hex_p50"), "attente": 900},
        {"nom": "rect", "geom": CT.geom("poker_eu", 300).to_dict(), "format": _fmt("poker_eu"), "attente": 900},
    ])
    h = R["hex"]
    assert 'data-role="hex"' in h["html"] and 'data-role="plan"' not in h["html"]
    assert "hex/plan" in _subs(h["appels"])
    assert "layout" not in _subs(h["appels"]) and "preflight" not in _subs(h["appels"]) and "layoutOf" not in h["trace"]
    r = R["rect"]
    assert r["html"] == a["init"]["html"]
    assert not any(x["sub"].startswith("hex/") for x in r["appels"])
    assert "layoutOf" in r["trace"] and "layout" in _subs(r["appels"]) and "preflight" in _subs(r["appels"])


def test_le_sous_titre_de_l_onglet_suit_la_forme(tmp_path):
    """Vague finale (C5) : un hexagone n'a ni TrimBox / BleedBox ni contrôle avant vol ; son sous-titre le dit.
    Un rectangle garde le texte d'index.html, retour d'un hexagone compris."""
    d = _dico()
    rect, hexa = d["cartes.page.print_hint"]["fr"], d["cartes.print.hex_hint"]["fr"]
    assert "TrimBox" not in hexa and "avant vol" not in hexa and "nid d'abeilles" in hexa
    assert "TrimBox" not in d["cartes.print.hex_hint"]["en"] and d["cartes.print.hex_hint"]["en"] != hexa
    R = _node(tmp_path, _source(None), "hex_p50")
    assert R["init"]["hint"] == hexa
    R = _node(tmp_path, _source(None), "poker_eu", [
        {"nom": "hex", "geom": GHEX.to_dict(), "format": _fmt("hex_p50"), "attente": 900},
        {"nom": "rect", "geom": CT.geom("poker_eu", 300).to_dict(), "format": _fmt("poker_eu"), "attente": 900},
    ])
    assert R["init"]["hint"] == rect
    assert R["hex"]["hint"] == hexa
    assert R["rect"]["hint"] == rect


def test_cles_hex_fr_et_en():
    src = _source(None)
    d = _dico()
    cles = sorted(set(re.findall(r'dzT\("(cartes\.print\.hex_[a-z0-9_]+)"', src)))
    assert len(cles) >= 8, cles
    for k in cles:
        assert k in d and d[k].get("fr") and d[k].get("en"), k
    assert d["cartes.print.hex_btn_pdf"]["fr"] == "PDF d'impression"
    assert d["cartes.print.hex_btn_coupe"]["fr"] == "Fichier de coupe (ZIP)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
