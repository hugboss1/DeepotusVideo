# -*- coding: utf-8 -*-
"""Son & VFX › Particules, canevas moderne avec aperçu en direct (t274, 21/10/2026) — `DzSvParticules`, posée par le
maillon de queue `dzsonvfx` depuis sa source frontend/patches/sonvfx-particules.js. Le hub la rend sur le sous-onglet
« vfx » et masque la vue d'origine. Son moteur est le PORT JS de particle_service (Q4 du plan : aperçu FIDÈLE).
Sections :
  [M] moteur serveur : réglages t274 neutres (un preset rend à l'octet ce qu'il rendait avant t274), gardes d'entrée,
      forme « disque », clés de cadence, vent, turbulence, frame seule = frame de la planche ;
  [R] routes : presets avec l'émetteur complet et les bornes, texture en RGBA brut, image PNG / RGBA d'une frame ;
  [F] FIDÉLITÉ sous node, le moteur DU LIVRÉ contre Python/PIL : générateur (random.Random), positions, tailles,
      couleurs, opacités, rotations à 5 instants pour les 12 presets et les réglages t274, puis les PIXELS (octet par
      octet) à 3 instants ;
  [S] source et livré : source APLATIE à l'octet, règles d'écriture, routes, hooks par alias, aucun texte en dur,
      aucun arrondi ;
  [H] le hub : « vfx » rend la page, la vue d'origine reste montée mais masquée ;
  [P] sous node, la VRAIE fonction du livré, un mini-moteur de hooks et un faux serveur : presets, inspecteur
      repliable, forme, naissance, frise et clés de cadence, tête de lecture, graine, fond et source, vérification
      contre le serveur, export WebM (job) et PNG, séquences prêtes, erreurs, état gardé ;
  [K] textes FR / EN de la page.
Run (depuis backend/) : & $PY tests/test_sonvfx_particules.py"""
import hashlib, io, json, pathlib, random, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE / "backend"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:700]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRC_P = RACINE / "frontend" / "patches" / "sonvfx-particules.js"
SRC = SRC_P.read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsvvoix*/"), BUNDLE.find("/*__dzsvparticules*/")
PAGE = BUNDLE[_i + len("/*__dzsvvoix*/"):_j] if 0 <= _i < _j else ""
_h0, _h1 = BUNDLE.find("var __dzSvHue="), BUNDLE.find("/*__dzsonvfx*/")
HUB = BUNDLE[_h0:_h1] if 0 <= _h0 < _h1 else ""
TEXDIR = RACINE / "backend" / "app" / "assets" / "starter" / "particles"

from PIL import Image  # noqa: E402
from app.services import particle_service as PS  # noqa: E402


def _sha(im):
    b = io.BytesIO()
    im.save(b, format="PNG")
    return hashlib.sha1(b.getvalue()).hexdigest()[:12]


# ── [M] moteur serveur ─────────────────────────────────────────────────────────────────────────────────────────────
print("[M] moteur serveur")
_D = PS._DEFAULT_EMITTER
check("M1 réglages t274 neutres par défaut (centre, rectangle, sans vent, sans turbulence, cadence pleine)",
      (_D["pos_x"], _D["pos_y"], _D["shape"], _D["wind"], _D["turbulence"], _D["rate_keys"]) == (0.5, 0.5, "rect", 0.0, 0.0, None))
# empreintes PNG prises AVANT t274 (main c272e7a6) : la refonte etat_frame / composer_frame ne change pas un octet
_AVANT = {("explosion", 1234, 3): "c9bac3932266", ("smoke", 1234, 10): "949d2b0dda36", ("shockwave", 7, 5): "5734b0d470bb"}


def _frame_png(preset, seed, f, **em):
    o = PS.normalize_opts({"preset": preset, "seed": seed, "emitter": em})
    with tempfile.TemporaryDirectory() as d:
        fr = PS.render_frames(TEXDIR / (o["texture"] + ".png"), o, pathlib.Path(d))
        return hashlib.sha1(fr[f].read_bytes()).hexdigest()[:12]


check("M2 un preset rend à l'octet ce qu'il rendait avant t274 (3 empreintes figées)",
      all(_frame_png(p, s, f) == h for (p, s, f), h in _AVANT.items()),
      {k: _frame_png(*k) for k in _AVANT})
for _bad, _motif in (({"shape": "etoile"}, "shape"), ({"rate_keys": [[0, 2]]}, "rate_keys"), ({"rate_keys": "x"}, "rate_keys"),
                     ({"rate_keys": [[0, 1]] * 9}, "rate_keys"), ({"turbulence": 401}, "turbulence"), ({"pos_x": 1.5}, "pos_x"),
                     ({"wind": 3000}, "wind")):
    def _refus(b=_bad, m=_motif):
        try:
            PS.normalize_opts({"preset": "magic", "emitter": b})
        except ValueError as e:
            return m in str(e)
        return False
    check(f"M3 refus : {_bad}", _refus)
_o = PS.normalize_opts({"preset": "magic", "seed": 3, "emitter": {"rate_keys": [[1, 0.5], [0, 0.2]]}})
check("M4 clés de cadence triées par t", _o["emitter"]["rate_keys"] == [[0.0, 0.2], [1.0, 0.5]])


def _parts(**em):
    o = PS.normalize_opts({"preset": "ashes", "seed": 11, "emitter": em})
    return o["emitter"], PS._spawn(o["emitter"], random.Random(o["seed"]))


_er, _pr = _parts()
_ed, _pd = _parts(shape="disque")
check("M5 disque : mêmes tirages que le rectangle (vitesses, vies identiques), naissances dans l'ellipse",
      [(p["vx"], p["life"], p["rot0"]) for p in _pr] == [(p["vx"], p["life"], p["rot0"]) for p in _pd]
      and all((p["ox"] / (.5 * _ed["spawn_x"])) ** 2 + (p["oy"] / (.5 * _ed["spawn_y"])) ** 2 <= 1 + 1e-9 for p in _pd)
      and any(p["ox"] != q["ox"] for p, q in zip(_pr, _pd)))
_em0, _p0 = _parts(rate_keys=[[0, 0], [1, 0]])
_em1, _p1 = _parts(rate_keys=[[0, 1]])
_emm, _pm = _parts(rate_keys=[[0, 0], [1, 1]])
_n = lambda em, ps: sum(len(PS.etat_frame(em, ps, f)) for f in range(em["frames"]))  # noqa: E731
check("M6 cadence : 0 = aucune particule, 1 = toutes, rampe = entre les deux",
      _n(_em0, _p0) == 0 and _n(_em1, _p1) == _n(_er, _pr) and 0 < _n(_emm, _pm) < _n(_er, _pr), (_n(_em0, _p0), _n(_emm, _pm), _n(_er, _pr)))
_ev, _pv = _parts(wind=400)
check("M7 vent : même population, x poussé vers la droite, y inchangé",
      all(b["x"] > a["x"] and abs(b["y"] - a["y"]) < 1e-9 for a, b in zip(PS.etat_frame(_er, _pr, 20), PS.etat_frame(_ev, _pv, 20))
          if a["i"] == b["i"]))
_et, _pt = _parts(turbulence=60)
check("M8 turbulence : déterministe et bornée (|écart| ≤ 2 × amplitude)",
      PS.etat_frame(_et, _pt, 9) == PS.etat_frame(_et, _pt, 9)
      and all(abs(b["x"] - a["x"]) <= 120 + 1e-6 and abs(b["y"] - a["y"]) <= 120 + 1e-6
              for a, b in zip(PS.etat_frame(_er, _pr, 9), PS.etat_frame(_et, _pt, 9)))
      and any(abs(b["x"] - a["x"]) > 1 for a, b in zip(PS.etat_frame(_er, _pr, 9), PS.etat_frame(_et, _pt, 9))))
_oi = PS.normalize_opts({"preset": "goldburst", "seed": 21, "emitter": {"pos_x": 0.3, "wind": -200}})
with tempfile.TemporaryDirectory() as _d:
    _fr = PS.render_frames(TEXDIR / "star_04.png", _oi, pathlib.Path(_d))
    _b7 = Image.open(_fr[7]).convert("RGBA").tobytes()
check("M9 la frame seule (export PNG) est la frame de la planche, à l'octet",
      PS.rendre_image(TEXDIR / "star_04.png", _oi, 7).tobytes() == _b7)


def _hors():
    try:
        PS.rendre_image(TEXDIR / "star_04.png", _oi, 18)
    except ValueError as e:
        return "frame" in str(e)
    return False


check("M10 frame hors de l'animation refusée", _hors)


def _attendre(coro):
    import asyncio
    return asyncio.run(coro)


def _export_exact():
    """L'export (job sprite2d) pose les frames SIMULÉES à l'octet : cellule native, pas de double alpha."""
    from app.config import settings
    ancien = settings.OUTPUTS_FOLDER
    with tempfile.TemporaryDirectory() as d:
        settings.OUTPUTS_FOLDER = d
        try:
            corps = {"preset": "muzzle", "seed": 5, "emitter": {"turbulence": 12}, "webm": False}
            r = _attendre(PS.generate_particles(corps, "t274test"))
            o = PS.normalize_opts(corps)
            em = o["emitter"]
            parts = PS._spawn(em, random.Random(5))
            sp = PS._sprites(PS._texture(TEXDIR / "muzzle_02.png"), em)
            fr = sorted((pathlib.Path(d) / "sprites" / "t274test" / "frames").glob("*.png"))
            return r["frames"] == em["frames"] == len(fr) and all(
                Image.open(f).convert("RGBA").tobytes() == PS.composer_frame(em, parts, k, sp).tobytes()
                for k, f in enumerate(fr))
        finally:
            settings.OUTPUTS_FOLDER = ancien


check("M11 l'export (planche + frames du job) est l'image simulée, à l'octet", _export_exact)

# ── [R] routes ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] routes")
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
C = TestClient(app)
_rp = C.get("/api/particles/presets").json()
check("R1 presets : émetteur complet (réglages t274 compris) et bornes du serveur",
      all(set(PS._DEFAULT_EMITTER) <= set(p.get("emitter", {})) for p in _rp["presets"])
      and _rp["bornes"].get("turbulence") == [0.0, 400.0] and len(_rp["presets"]) == len(PS.PRESETS))
_rt = C.get("/api/particles/texture/fire_02")
_tex = Image.open(TEXDIR / "fire_02.png").convert("RGBA")
check("R2 texture en RGBA brut, décodée par PIL (mêmes octets que le rendu)",
      _rt.status_code == 200 and _rt.content == _tex.tobytes()
      and (_rt.headers.get("x-dz-largeur"), _rt.headers.get("x-dz-hauteur")) == (str(_tex.width), str(_tex.height)))
check("R3 texture inconnue : 404", C.get("/api/particles/texture/nexistepas").status_code == 404)
_corps = {"preset": "goldburst", "seed": 21, "emitter": {"pos_x": 0.3, "wind": -200}, "frame": 7}
_ri = C.post("/api/particles/image", json=_corps)
check("R4 image PNG d'une frame = la frame de la planche, nom de fichier avec graine et rang",
      _ri.status_code == 200 and _ri.headers["content-type"] == "image/png"
      and Image.open(io.BytesIO(_ri.content)).convert("RGBA").tobytes() == _b7
      and 'particules_21_007.png' in _ri.headers.get("content-disposition", ""))
_rr = C.post("/api/particles/image", json=dict(_corps, format="rgba"))
check("R5 format « rgba » : les octets bruts de la frame", _rr.status_code == 200 and _rr.content == _b7
      and _rr.headers.get("x-dz-graine") == "21")
check("R6 frame invalide : 400", C.post("/api/particles/image", json=dict(_corps, frame="x")).status_code == 400
      and C.post("/api/particles/image", json=dict(_corps, frame=99)).status_code == 400)
check("R7 réglage invalide : 400", C.post("/api/particles/image", json=dict(_corps, emitter={"shape": "x"})).status_code == 400)

# ── [F] fidélité : le moteur du livré contre Python/PIL ───────────────────────────────────────────────────────────
print("[F] fidélité JS (livré) = serveur")
NODE_F = r"""
const fs=require("fs");const D=process.argv[2];
const M=require(D+"/moteur.cjs");
const T=JSON.parse(fs.readFileSync(D+"/taches.json","utf8"));const R={mt:{}};
for(const g of [0,1,7,1234,1073741823]){const q=M.dzSvxMT(g);R.mt[g]={a:Array.from({length:12},()=>q.alea()),s:Array.from({length:12},()=>q.signe())}}
for(const t of T){const tex={w:t.tw,h:t.th,d:new Uint8Array(fs.readFileSync(D+"/"+t.tex))};
 const m=M.dzSvxMoteur(t.em,t.graine,tex);R[t.id]={etats:t.instants.map(f=>M.dzSvxEtat(m.em,m.parts,f))};
 for(const f of t.pixels)fs.writeFileSync(D+"/js_"+t.id+"_"+f,Buffer.from(M.dzSvxFrame(m,f)));}
fs.writeFileSync(D+"/r.json",JSON.stringify(R));"""
_CAS = [{"preset": p["id"], "seed": 1234} for p in PS.PRESETS] + [
    {"preset": "magic", "seed": 99, "emitter": {"wind": 300, "turbulence": 40, "shape": "disque", "pos_x": 0.3}},
    {"preset": "embers", "seed": 5, "emitter": {"rate_keys": [[0, 0], [0.5, 1], [1, 0.2]], "shape": "disque", "pos_y": 0.7}},
    {"preset": "sparks", "seed": 3, "emitter": {"size": 256, "blend": "normal", "orient": "velocity", "angle": 90,
                                                 "spread": 0, "rot_speed": 0}}]
FR = {}
with tempfile.TemporaryDirectory() as _d:
    D = pathlib.Path(_d)
    _fn = sorted(set(re.findall(r"function (dzSvx[A-Za-z0-9]+)\(", PAGE)))
    (D / "moteur.cjs").write_text(PAGE + "\nmodule.exports={" + ",".join(_fn) + "};", encoding="utf-8")
    _taches = []
    for n, c in enumerate(_CAS):
        o = PS.normalize_opts(c)
        em = dict(o["emitter"], color0=list(o["emitter"]["color0"]), color1=list(o["emitter"]["color1"]))
        tx = PS._texture(TEXDIR / (o["texture"] + ".png"))
        (D / f"t{n}").write_bytes(tx.tobytes())
        F = em["frames"]
        _taches.append({"id": f"c{n}", "em": em, "graine": o["seed"], "tex": f"t{n}", "tw": tx.width, "th": tx.height,
                        "instants": sorted({0, F // 4, F // 2, (3 * F) // 4, F - 1}), "pixels": sorted({1, F // 2, F - 2}),
                        "_o": o, "_tx": tx})
    (D / "taches.json").write_text(json.dumps([{k: v for k, v in t.items() if not k.startswith("_")} for t in _taches]),
                                   encoding="utf-8")
    (D / "h.js").write_text(NODE_F, encoding="utf-8")
    _p = subprocess.run(["node", str(D / "h.js"), str(D)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("F0 le moteur du livré tourne sous node", _p.returncode == 0, _p.stderr[-600:])
    RJ = json.loads((D / "r.json").read_text(encoding="utf-8")) if _p.returncode == 0 else {}
    for t in _taches:
        o, em = t["_o"], t["_o"]["emitter"]
        parts = PS._spawn(em, random.Random(o["seed"]))
        sp = PS._sprites(t["_tx"], em)
        FR[t["id"]] = {"etats": [PS.etat_frame(em, parts, f) for f in t["instants"]],
                       "pix": {f: (PS.composer_frame(em, parts, f, sp).tobytes(),
                                   (D / f"js_{t['id']}_{f}").read_bytes() if (D / f"js_{t['id']}_{f}").exists() else b"")
                               for f in t["pixels"]}}
_mt = RJ.get("mt", {})


def _suite(g):
    """12 random() puis 12 choice((-1, 1)) sur UN générateur, comme le harnais JS."""
    q = random.Random(g)
    return [q.random() for _ in range(12)], [q.choice((-1, 1)) for _ in range(12)]


check("F1 générateur : random.Random(graine) de Python reproduit (random() et choice((-1, 1))), 5 graines",
      _mt and all((_mt[str(g)]["a"], _mt[str(g)]["s"]) == _suite(g) for g in (0, 1, 7, 1234, 1073741823)))


def _etats_egaux(t):
    js, py = RJ.get(t["id"], {}).get("etats"), FR[t["id"]]["etats"]
    if js is None or len(js) != len(py):
        return False, "absent"
    ecart = 0.0
    for lj, lp in zip(js, py):
        if [d["i"] for d in lj] != [d["i"] for d in lp]:
            return False, "population"
        for a, b in zip(lj, lp):
            if a["px"] != b["px"] or a["cle"] != list(b["cle"]) or a["col"] != list(b["col"]):
                return False, (a, b)
            ecart = max(ecart, abs(a["x"] - b["x"]), abs(a["y"] - b["y"]), abs(a["rot"] - b["rot"]), abs(a["a"] - b["a"]))
    return ecart < 1e-9, ecart


for t, c in zip(_taches, _CAS):
    _r = _etats_egaux(t)
    lib = c["preset"] + (" + " + ",".join(c["emitter"]) if c.get("emitter") else "")
    check(f"F2 {lib} : positions, tailles, couleurs, opacités, rotations à 5 instants", _r[0], _r[1])
for t, c in zip(_taches, _CAS):
    _px = FR[t["id"]]["pix"]
    _diff = {f: (sum(1 for u, v in zip(a, b) if u != v) if a != b else 0, len(a), len(b)) for f, (a, b) in _px.items()}
    lib = c["preset"] + (" + " + ",".join(c["emitter"]) if c.get("emitter") else "")
    check(f"F3 {lib} : pixels identiques à l'octet à 3 instants", all(a == b and a for a, b in _px.values()), _diff)

# ── [S] source et livré ────────────────────────────────────────────────────────────────────────────────────────────
print("[S] source et livré")
import patch_bundle_dzsonvfx as PZ  # noqa: E402
check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PZ.aplatir(SRC), (len(PAGE), len(PZ.aplatir(SRC))))
check("S2 la page est posée une fois, après la Voix et avant `const Te=`",
      BUNDLE.count("function DzSvParticules(") == 1 and 0 < _i < _j < BUNDLE.find('const Te="/api";'))
_lignes, _dans = [], False
for _l in (l.strip() for l in SRC.splitlines()):
    if _dans or _l.startswith("/*"):
        _dans = not _l.endswith("*/")
        continue
    _lignes.append(_l)
check("S3 règles d'écriture : ni « // », ni ligne qui commence par ( ou [",
      not any(l.startswith(("//", "(", "[")) for l in _lignes))
check("S4 aucun texte en dur : libellés par dzT, aucun aria-label/placeholder/title littéral",
      not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE) and not re.search(r'"aria-label":"|placeholder:"|title:"', PAGE))
check("S5 clés dzT littérales seulement (aucune clé construite)", not re.search(r'dzT\("[a-z0-9_.]+"\s*\+', PAGE))
_ROUTES = ('"/api/particles/presets"', '"/api/starter/catalog"', '"/api/starter/catalog?kind=particle"',
           '"/api/particles/texture/"', '"/api/particles/image"', '"/api/assets/particles"', '"/api/assets/starter-anim"')
check("S6 routes : presets, catalogue, texture brute, image, export WebM, séquences", all(u in PAGE for u in _ROUTES),
      [u for u in _ROUTES if u not in PAGE])
_rt_src = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
check("S7 chaque route existe côté serveur",
      all(s in _rt_src for s in ('@router.get("/particles/presets")', '@router.get("/particles/texture/{tid}")',
                                 '@router.post("/particles/image")', '@router.post("/assets/particles")',
                                 '@router.post("/assets/starter-anim")', '@router.get("/starter/catalog")')))
check("S8 hooks par alias dans la fonction (x.useState( absent de la page)",
      "function DzSvParticules(p){ var US=x.useState,UE=x.useEffect,UR=x.useRef;" in PAGE and "x.useState(" not in PAGE)
check("S9 aucun arrondi : ni la page ni sa feuille ne posent de border-radius (règle unique du hub)",
      "border-radius" not in PAGE and "borderRadius" not in PAGE and "border-radius" not in PZ.CSS_PARTICULES)
check("S10 le moteur est un port, pas une approximation : générateur de Python, Lanczos, rotation et compositions de Pillow",
      all(s in PAGE for s in ("function dzSvxMT(", "19650218", "1664525", "1566083941", "function dzSvxRedim(",
                              "function dzSvxTourne(", "function dzSvxPoser(", "function dzSvxEtat(")))
check("S11 aucune variable globale de navigateur pour garder l'état hors de window.__dzSvPart",
      "localStorage" not in PAGE and "window.__dzSvPart=" in PAGE)

# ── [H] le hub ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] le hub")
check("H1 « vfx » rend DzSvParticules (go transmis), la vue d'origine masquée par le même style que la Voix",
      'parti=sub==="vfx"' in HUB and re.search(r'style:pistes\|\|atelier\|\|voix\|\|parti(\|\|\w+)*\?\{display:"none"\}:void 0', HUB)  # t276 : + post
      and 'parti?r.jsx(DzSvParticules,{go:p.go},"particules"):null' in HUB)
check("H2 la feuille de la page est injectée avec celle du hub", ".dzsvx{" in HUB and ".dzsvx-cles{" in HUB)
check("H3 la vue d'origine (SvmParticles) n'est pas réécrite : la couche L4 est intacte",
      BUNDLE.count("function SvmParticles(") == 1)

# ── [P] sous node ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[P] la page sous node")
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("/*__dzsvvoix*/"),j=S.indexOf("/*__dzsvparticules*/");if(i<0||j<i)throw new Error("page introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[];
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q])){EFF.push([k,f]);}H[k]=d||[]},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const NETTOYER={};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
function dzSvpJson(res){return res.json().catch(()=>({})).then(d=>{if(!res.ok){const m=d&&d.detail;throw new Error((typeof m==="string"&&m)||("code "+res.status))}return d})}
let SONDES=[];function svmPollJob(id,onStep){SONDES.push(id);onStep&&onStep("Simulation");return Promise.resolve({job_id:id+"-0000-1111",status:"done",title:"t"})}
const window={};let PEINT=[];
class ImageData{constructor(d,w,h){this.data=d;this.width=w;this.height=h}}
function toile(){return {width:0,height:0,getContext(){const c=this;return {putImageData(im){PEINT.push([c.nom,im.width,im.data.length])}}}}}
let CLIC=[];const document={body:{appendChild(){}},createElement(){return {click(){CLIC.push(this.download)},remove(){}}}};
const URL={createObjectURL:b=>"blob:"+(b&&b.name||"x"),revokeObjectURL(){}};
let APPELS=[],REP={},CATALOGUE=null,ECART=0;
const TEX={w:6,h:6,d:new Uint8Array(144).map((v,q)=>(q*37)%256)};
function json(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d),headers:{get:()=>null}})}
let MOT=null;
function fetch(u,o){o=o||{};const corps=o.body?JSON.parse(o.body):null;APPELS.push([u,o.method||"GET",corps]);
 if(REP[u])return json(REP[u].d,REP[u].st);
 if(u==="/api/particles/presets")return json(CATALOGUE);
 if(u==="/api/starter/catalog")return json({particle_families:[{id:"fire",name:"Feu"},{id:"star",name:"Étoiles"}]});
 if(u==="/api/starter/catalog?kind=particle")return json({items:[{id:"t_fire",family:"fire",name:"Feu 1",thumb:"particles/thumb/a.png"},{id:"t_star",family:"star",name:"Étoile 1",thumb:"particles/thumb/b.png"}]});
 if(u.indexOf("/api/particles/texture/")===0)return Promise.resolve({ok:true,status:200,headers:{get:h=>h==="X-Dz-Largeur"||h==="X-Dz-Hauteur"?"6":null},arrayBuffer:()=>Promise.resolve(TEX.d.slice().buffer)});
 if(u==="/api/particles/image"){const e=Object.assign({},corps.emitter);e.color0=dzSvxRvb(e.color0);e.color1=dzSvxRvb(e.color1);
  const m=dzSvxMoteur(dzSvxPourMoteur(e),corps.seed,{w:6,h:6,d:TEX.d.slice()});const b=dzSvxFrame(m,corps.frame);if(ECART)b[5]^=1;
  return Promise.resolve({ok:true,status:200,headers:{get:()=>null},arrayBuffer:()=>Promise.resolve(b.buffer),blob:()=>Promise.resolve({name:"png"})})}
 if(u==="/api/assets/particles"||u==="/api/assets/starter-anim")return json({job_id:"job"+APPELS.length,status:"queued"});
 return json({},404)}
eval(CODE);
let ALLER=[];
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
let A=null;const REFS={toile:toile(),video:{paused:true,duration:4,currentTime:0,play(){this.paused=false},pause(){this.paused=true}},fichier:{click(){CLIC.push("fichier")}}};
REFS.toile.nom="vue";
function rendre(){HI=0;EFF=[];A=DzSvParticules({go:v=>ALLER.push(v)});
 tout(A,n=>n.p&&n.p.ref,[]).forEach(n=>{if(typeof n.p.ref==="function"){const c=toile();c.nom=n.p.className;n.p.ref(c)}else n.p.ref.current=n.t==="canvas"?REFS.toile:n.t==="video"?REFS.video:REFS.fichier});
 const e=EFF;EFF=[];e.forEach(([k,f])=>{if(NETTOYER[k])NETTOYER[k]();const c=f();NETTOYER[k]=typeof c==="function"?c:null});return A}
async function calme(ms){const fin=Date.now()+(ms||0);for(let k=0;k<12||Date.now()<fin;k++){await new Promise(r0=>setTimeout(r0,ms?10:0));rendre()}}
function un(f){return tout(A,f,[])[0]}
function part(a){return un(n=>n.p&&n.p["data-sv-part"]===a)}
function cls(c){return n=>n.p&&typeof n.p.className==="string"&&n.p.className.split(" ").indexOf(c)>=0}
function em(){return H[3]}
function etat(){return {zones:tout(A,n=>n.p&&/^dzsvx-(bandeau|vue|frise|inspecteur)$/.test(n.p.className),[]).map(n=>n.p.className),
 presets:tout(A,cls("dzsvx-preset"),[]).map(n=>[n.p["data-preset"]||n.p["data-anim"],n.p["aria-pressed"]]),
 sections:tout(A,cls("dzsvx-section"),[]).map(n=>[n.p["data-section"],tout(n,cls("dzsvx-stete"),[])[0].p["aria-expanded"]]),
 regles:tout(A,n=>n.p&&n.p["data-regle"],[]).map(n=>n.p["data-regle"]),
 segs:Object.fromEntries(tout(A,cls("dzsvx-segs"),[]).map(n=>[n.p["data-seg"],(tout(n,m=>m.p&&m.p["aria-pressed"]==="true",[])[0]||{p:{}}).p["data-val"]])),
 textures:tout(A,cls("dzsvx-texture"),[]).map(n=>[n.p["data-texture"],n.p["aria-pressed"]]),
 cles:tout(A,cls("dzsvx-cle"),[]).length,temps:texte(part("temps")),calcul:texte(part("calcul")),
 note:texte(part("note")),erreur:texte(part("erreur")),sortie:part("sortie")?tout(part("sortie"),n=>n.t==="a"||n.t==="img",[]).map(n=>n.p.href||n.p.src):null,
 aides:tout(A,cls("dzsvx-aide"),[]).map(texte),source:(un(cls("dzsvx-source"))||{t:null,p:{}}),fond:(un(cls("dzsvx-vue"))||{p:{}}).p["data-fond"],
 em:em(),graine:H[5],f:H[6],lecture:H[7],texture:H[4],preset:H[2],attente:texte(un(cls("dzsvx-attente"))),appels:APPELS.slice()}}
function segClic(nom,val){const s=un(n=>cls("dzsvx-segs")(n)&&n.p["data-seg"]===nom);tout(s,n=>n.p&&n.p["data-val"]===String(val),[])[0].p.onClick();rendre()}
function curseur(k,v){un(n=>n.p&&n.p["data-regle"]===k).p.children[1].p.onChange({target:{value:String(v)}});rendre()}
const BOITE={getBoundingClientRect:()=>({left:0,top:0,width:200,height:40}),setPointerCapture(){}};
function svgEv(x,y,cible){return {currentTarget:BOITE,clientX:x,clientY:y,pointerId:1,target:{getAttribute:a=>a==="data-cle"&&cible!=null?String(cible):null}}}
function preset(id,f,frames,extra){return {id,name:"N"+id,type:"sprite",desc:"d",texture:"t_"+f,thumb:null,frames,fps:12,blend:"add",
 emitter:Object.assign({count:5,frames,fps:12,size:128,birth:"burst",birth_spread:0.2,angle:0,spread:120,speed:80,speed_var:0.3,gravity:40,drag:1.4,life:0.5,life_var:0.2,
 scale0:0.2,scale1:0.4,rot_speed:30,color0:"FFD9A0",color1:"8A2B10",alpha0:1,alpha1:0,blend:"add",orient:"random",spawn_x:0,spawn_y:0,pos_x:0.5,pos_y:0.5,shape:"rect",wind:0,turbulence:0,rate_keys:null},extra||{})}}
(async()=>{const R={};
 CATALOGUE={available:true,presets:[preset("p1","fire",6),preset("p2","star",8,{birth:"stream",blend:"normal"})],
  anims:[{id:"a1",name:"Explosion CC0",frames:10,thumb:"/starter/anims/a1/000.png"}],
  bornes:{count:[1,200],frames:[2,64],fps:[4,60],birth_spread:[0,1],angle:[-360,360],spread:[0,360],speed:[0,2000],speed_var:[0,1],gravity:[-2000,2000],drag:[0.5,6],life:[0.05,6],
   life_var:[0,1],scale0:[0.01,2],scale1:[0.01,2],rot_speed:[-720,720],alpha0:[0,1],alpha1:[0,1],spawn_x:[0,2],spawn_y:[0,2],pos_x:[0,1],pos_y:[0,1],wind:[-2000,2000],turbulence:[0,400]}};
 rendre();R.charge0=etat();await calme();R.charge=etat();
 await calme(900);R.moteur=etat();R.peint=PEINT.filter(p=>p[0]==="vue").length;R.peint_mini=PEINT.filter(p=>p[0]==="dzsvx-vignette").length;
 un(n=>n.p&&n.p["data-preset"]==="p2").p.onClick();await calme(300);R.p2=etat();
 R.tex_p2=APPELS.some(a=>a[0]==="/api/particles/texture/t_star");
 curseur("count",9);R.count=etat().em.count;curseur("speed",120.5);R.speed=etat().em.speed;
 segClic("forme","disque");R.disque=[em().shape,em().spawn_x,em().spawn_y,etat().regles];
 segClic("forme","ligne");R.ligne=[em().shape,em().spawn_x,em().spawn_y,etat().regles.indexOf("spawn_y")];
 segClic("forme","point");R.point=[em().shape,em().spawn_x,em().spawn_y,etat().regles.indexOf("spawn_x")];
 segClic("naissance","burst");R.burst=etat().regles.indexOf("birth_spread")>=0;
 segClic("naissance","stream");R.stream=[etat().regles.indexOf("birth_spread"),etat().aides];
 part("section-apparence").p.onClick();rendre();R.apparence=etat();
 un(n=>n.t==="select"&&n.p["data-sv-part"]==="famille").p.onChange({target:{value:"fire"}});rendre();R.famille=etat().textures;
 un(n=>n.p&&n.p["data-texture"]==="t_fire").p.onClick();rendre();R.texture=etat().texture;
 un(n=>n.p&&n.p["data-regle"]==="color0").p.children[1].p.onChange({target:{value:"#12ab9f"}});rendre();R.couleur=em().color0;
 segClic("blend","add");R.blend=em().blend;
 part("section-duree").p.onClick();rendre();segClic("size",256);R.size=em().size;
 part("section-emetteur").p.onClick();rendre();R.replie=etat().sections;
 const svg=()=>part("cles");
 svg().p.onPointerDown(svgEv(50,10));rendre();R.cle1=[em().rate_keys,etat().cles];
 svg().p.onPointerMove(svgEv(100,30));rendre();R.cle_glisse=em().rate_keys;svg().p.onPointerUp();rendre();
 svg().p.onPointerDown(svgEv(20,20));rendre();svg().p.onPointerUp();rendre();R.cle2=em().rate_keys;
 tout(A,cls("dzsvx-cle"),[])[1].p.onDoubleClick();rendre();R.cle_retiree=em().rate_keys;
 for(let k=0;k<9;k++){svg().p.onPointerDown(svgEv(10+k*20,5));rendre();svg().p.onPointerUp();rendre()}
 R.cles_max=[em().rate_keys.length,etat().note];
 part("cles-effacer").p.onClick();rendre();R.effacees=em().rate_keys;
 await calme(300);
 part("regle").p.onPointerDown(svgEv(100,5));rendre();R.scrub=[H[6],H[7]];
 part("lecture").p.onClick();rendre();R.relance=H[7];part("lecture").p.onClick();rendre();
 un(n=>n.t==="input"&&n.p["data-sv-part"]==="graine").p.onChange({target:{value:"4242"}});rendre();R.graine=H[5];
 part("graine-neuve").p.onClick();rendre();R.graine_neuve=H[5];
 un(n=>n.t==="input"&&n.p["data-sv-part"]==="graine").p.onChange({target:{value:"77"}});rendre();
 await calme(300);
 APPELS=[];part("verifier").p.onClick();await calme();R.verif=[etat().note,APPELS.filter(a=>a[0]==="/api/particles/image").map(a=>[a[2].format,a[2].seed,a[2].frame])];
 ECART=1;part("verifier").p.onClick();await calme();R.verif_ecart=etat().note;ECART=0;
 APPELS=[];part("webm").p.onClick();await calme();R.webm=[APPELS.filter(a=>a[0]==="/api/assets/particles").map(a=>a[2]),SONDES.slice(),etat().sortie];
 part("biblio").p.onClick();R.biblio=ALLER.slice();
 APPELS=[];CLIC=[];part("png").p.onClick();await calme();R.png=[APPELS.filter(a=>a[0]==="/api/particles/image").map(a=>a[2]),CLIC.slice(),etat().note];
 REP["/api/assets/particles"]={d:{detail:"texture requise (ou preset)"},st:400};part("webm").p.onClick();await calme();R.webm_err=etat().erreur;delete REP["/api/assets/particles"];
 segClic("fond","noir");R.noir=etat().fond;
 part("source").p.onClick();un(n=>n.t==="input"&&n.p.type==="file").p.onChange({target:{files:[{name:"plan.mp4",type:"video/mp4"}]}});rendre();
 R.source=[etat().fond,etat().source.t,etat().source.p.src,tout(A,n=>cls("dzsvx-segs")(n)&&n.p["data-seg"]==="fond",[]).flatMap(s=>tout(s,cls("dzsvx-seg"),[]).map(b=>b.p["data-val"]))];
 part("onglet-sequences").p.onClick();rendre();R.sequences=etat().presets;
 APPELS=[];un(n=>n.p&&n.p["data-anim"]==="a1").p.onClick();await calme();R.anim=APPELS.filter(a=>a[0]==="/api/assets/starter-anim").map(a=>a[2]);
 R.memo=Object.assign({},window.__dzSvPart);
 H=[];HI=0;rendre();await calme();R.remonte=[H[3]&&H[3].size,H[4],H[5],H[2]];
 H=[];CATALOGUE={available:false,presets:[],anims:[],bornes:{}};window.__dzSvPart=undefined;rendre();await calme();R.absent=etat().attente;
 fs.writeFileSync(process.argv[3],JSON.stringify(R));process.exit(0)})().catch(e=>{console.error(e&&e.stack||e);process.exit(1)});
"""
with tempfile.TemporaryDirectory() as _d:
    _h = pathlib.Path(_d) / "h.js"
    _h.write_text(HARNAIS, encoding="utf-8")
    _o = pathlib.Path(_d) / "o.json"
    _p = subprocess.run(["node", str(_h), str(BUN_P), str(_o)], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=240)
    check("P0 le harnais tourne", _p.returncode == 0, _p.stderr[-900:])
    R = json.loads(_o.read_text(encoding="utf-8")) if _o.exists() else {}
c = R.get("charge", {})
check("P1 chargement : bandeau, viewport, frise, inspecteur ; premier preset choisi",
      c.get("zones") == ["dzsvx-bandeau", "dzsvx-vue", "dzsvx-frise", "dzsvx-inspecteur"]
      and c.get("presets") == [["p1", "true"], ["p2", "false"]] and c.get("texture") == "t_fire", c.get("zones"))
check("P2 attente avant le catalogue", R.get("charge0", {}).get("attente") == "⟦sonvfx.particules.chargement⟧")
check("P3 inspecteur en sections repliables : émetteur et mouvement ouverts, apparence et durée fermées",
      c.get("sections") == [["emetteur", "true"], ["mouvement", "true"], ["apparence", "false"], ["duree", "false"]])
m = R.get("moteur", {})
check("P4 le moteur calcule toutes les frames et peint le viewport ; les vignettes sont rendues par le moteur",
      m.get("calcul") == "⟦sonvfx.particules.calcul_fait⟧" and R.get("peint", 0) > 0 and R.get("peint_mini", 0) > 0,
      (m.get("calcul"), R.get("peint"), R.get("peint_mini")))
check("P5 la frise donne image, durée et cadence", m.get("temps", "").startswith("⟦sonvfx.particules.temps⟧")
      and '"n":6' in m.get("temps", "") and '"fps":12' in m.get("temps", ""), m.get("temps"))
p2 = R.get("p2", {})
check("P6 choisir un preset charge son émetteur et sa texture", p2.get("preset") == "p2" and p2.get("texture") == "t_star"
      and p2.get("em", {}).get("birth") == "stream" and R.get("tex_p2"))
check("P7 curseurs : entier arrondi pour le nombre, réel pour la vitesse", R.get("count") == 9 and R.get("speed") == 120.5)
check("P8 forme disque : zone non nulle, largeur et hauteur réglables", R.get("disque", [None])[:3] == ["disque", 0.6, 0.6]
      and "spawn_x" in R["disque"][3] and "spawn_y" in R["disque"][3])
check("P9 forme ligne : hauteur nulle, pas de curseur de hauteur", R.get("ligne") == ["rect", 0.6, 0, -1])
check("P10 forme point : zone nulle, pas de curseur de zone", R.get("point") == ["rect", 0, 0, -1])
check("P11 naissance : rafale = étalement réglable, flux continu = aide de la boucle parfaite",
      R.get("burst") is True and R.get("stream", [0])[0] == -1 and "⟦sonvfx.particules.flux_aide⟧" in R["stream"][1])
a = R.get("apparence", {})
check("P12 apparence : textures du catalogue, filtre par famille, choix, couleur en RRGGBB, fusion",
      len(a.get("textures", [])) == 2 and R.get("famille") == [["t_fire", "false"]] and R.get("texture") == "t_fire"
      and R.get("couleur") == "12AB9F" and R.get("blend") == "add", (a.get("textures"), R.get("famille")))
check("P13 durée : canevas 256 px", R.get("size") == 256)
check("P14 une section se replie", R.get("replie", [[None]])[0] == ["emetteur", "false"])
check("P15 frise : un clic pose une clé (t, v), glisser la déplace", R.get("cle1") == [[[0.25, 0.798]], 1]
      and R.get("cle_glisse") == [[0.5, 0.202]], (R.get("cle1"), R.get("cle_glisse")))
check("P16 clés triées par t, double-clic retire", R.get("cle2") == [[0.1, 0.5], [0.5, 0.202]]
      and R.get("cle_retiree") == [[0.1, 0.5]], (R.get("cle2"), R.get("cle_retiree")))
check("P17 8 clés au plus (la note le dit), « Effacer les clés » revient à la cadence pleine",
      R.get("cles_max", [0])[0] == 8 and "⟦sonvfx.particules.cles_max⟧" in R["cles_max"][1] and R.get("effacees") is None,
      R.get("cles_max"))
check("P18 la règle de temps place la tête et arrête la lecture", R.get("scrub") == [4, False] and R.get("relance") is True,
      R.get("scrub"))
check("P19 graine : saisie bornée, « Nouvelle graine » en tire une autre",
      R.get("graine") == 4242 and isinstance(R.get("graine_neuve"), int) and R.get("graine_neuve") != 4242)
check("P20 « Comparer au serveur » : octets bruts de la même frame, même graine, verdict identique",
      R.get("verif", [""])[0].startswith("⟦sonvfx.particules.verif_ok⟧") and R["verif"][1] == [["rgba", 77, 4]], R.get("verif"))
check("P21 écart signalé à l'octet près", R.get("verif_ecart", "").startswith("⟦sonvfx.particules.verif_ecart⟧")
      and '"n":1' in R.get("verif_ecart", ""), R.get("verif_ecart"))
w = R.get("webm", [[{}]])
_c0 = (w[0] or [{}])[0]
check("P22 export WebM : job serveur avec l'émetteur complet (couleurs RRGGBB), la graine et la texture de l'aperçu",
      _c0.get("webm") is True and _c0.get("seed") == 77 and _c0.get("texture") == "t_fire" and _c0.get("preset") == "p2"
      and _c0.get("emitter", {}).get("color0") == "12AB9F" and _c0.get("emitter", {}).get("size") == 256
      and "title" in _c0, _c0)
check("P23 le job est suivi puis le sprite proposé (aperçu, ZIP, Bibliothèque)",
      w[1] and w[2] == ["/api/assets/sprite/job1-000/preview", "/api/assets/sprite/job1-000/zip"]
      and R.get("biblio") == ["library"], w[1:])
pn = R.get("png", [[{}], [], ""])
check("P24 export PNG : la frame affichée, rendue par le serveur, téléchargée",
      (pn[0] or [{}])[0].get("frame") == 4 and "format" not in pn[0][0] and pn[1] == ["particules_77_004.png"]
      and pn[2].startswith("⟦sonvfx.particules.png_fait⟧"), pn)
check("P25 erreur du serveur affichée", R.get("webm_err", "").startswith("⟦sonvfx.particules.echec⟧")
      and "texture requise" in R.get("webm_err", ""), R.get("webm_err"))
check("P26 fond noir, puis vidéo source : le fond passe à « source » et la vidéo est sous le canevas",
      R.get("noir") == "noir" and R.get("source", [None])[:3] == ["source", "video", "blob:plan.mp4"]
      and R["source"][3] == ["damier", "noir", "source"], R.get("source"))
check("P27 séquences prêtes : liste du catalogue, un clic lance l'assemblage (local, gratuit)",
      R.get("sequences") == [["a1", None]] and R.get("anim") == [{"anim": "a1", "cell": 512}], (R.get("sequences"), R.get("anim")))
mm = R.get("memo", {})
check("P28 état gardé d'une visite à l'autre (émetteur, texture, graine, preset)",
      mm.get("graine") == 77 and mm.get("texture") == "t_fire" and R.get("remonte") == [256, "t_fire", 77, "p2"], R.get("remonte"))
check("P29 catalogue absent : la page le dit", R.get("absent") == "⟦sonvfx.particules.catalogue_absent⟧", R.get("absent"))

# ── [K] textes ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
CLES = sorted(set(re.findall(r'dzT\("(sonvfx\.particules\.[a-z0-9_]+)"', PAGE)))
check("K1 chaque clé de la page : FR et EN, mêmes variables, trois segments",
      CLES and all((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en") and len(k.split(".")) == 3
                   and set(re.findall(r"\{(\w+)\}", DICO[k]["fr"])) == set(re.findall(r"\{(\w+)\}", DICO[k]["en"]))
                   for k in CLES), [k for k in CLES if k not in DICO])
check("K2 aucune clé sonvfx.particules.* orpheline dans le dictionnaire",
      sorted(k for k in DICO if k.startswith("sonvfx.particules.")) == CLES,
      sorted(set(k for k in DICO if k.startswith("sonvfx.particules.")) ^ set(CLES)))
_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K3 dictionnaire assemblé (source = copie de dist)", all(k.encode() in _dico for k in CLES)
      and _dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_particules():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
