# -*- coding: utf-8 -*-
"""Son & VFX › Post-traitement : illustrations animées codées des presets (t278, 22/10/2026).

Même chaîne que les gestes VFX IA (t275) : une page HTML / Canvas par preset de `effects_engine.POST_PILE`
(scripts/sonvfx_illus_post/<id>.html), écrite selon une fiche de style MAISON et passée au contrôle statique
`motion_code`, rendue AU DÉVELOPPEMENT (décision Q3) par `scripts/sonvfx_illustrations.py --jeu post` dans le
chrome-headless-shell embarqué : 480×270, 30 i/s, 4 s en boucle → frontend/dist/sonvfx/illus-post/<id>.webm (≤ 250 Ko)
et une affiche <id>.webp. Le script partagé dz-post-illus.js pose l'affiche en vignette sur chaque bouton du
catalogue (button[data-sv-post="ajout-<id>"]) et chaque maillon de la pile (div[data-sv-post="maillon"][data-preset]),
lit l'animation au survol ou au focus, et reste fixe en `prefers-reduced-motion`. Sections :
  [P] pages : une par preset (rouge si un preset arrive sans la sienne), contrôle motion_code, fiche maison, boucle ;
  [R] rendus : manifeste à jour (empreinte de chaque page), WebM VP9 480×270 de 4 s ≤ 250 Ko, affiche WebP 480×270 ;
  [C] chaîne : le jeu « post » à côté du jeu « vfx » de t275, `--check` couvre les deux ;
  [G] garde G3 : aucun contenu de prompt-motion.com dans les fichiers neufs ;
  [E] écran : script partagé (copie à l'octet, balise dans la SPA), catalogue ET pile, survol, focus, mouvement réduit,
      maillon dont le preset change, aucun arrondi, aucun texte visible, sous node avec un faux DOM.
Run (depuis backend/) : & $PY tests/test_sonvfx_illus_post.py"""
import hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile, unicodedata
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


from app.services import effects_engine as EE  # noqa: E402
from app.services import motion_code as MC  # noqa: E402

try:
    import sonvfx_illustrations as SI  # noqa: E402
except Exception as e:  # noqa: BLE001
    SI = None
    print(f"  (sonvfx_illustrations introuvable : {type(e).__name__}: {e})")

PAGES = RACINE / "scripts" / "sonvfx_illus_post"
SORTIE = RACINE / "frontend" / "dist" / "sonvfx" / "illus-post"
STYLES = RACINE / "backend" / "app" / "motion" / "styles"
JS_SRC = RACINE / "frontend" / "shared" / "dz-post-illus.js"
JS_DIST = RACINE / "frontend" / "dist" / "shared" / "dz-post-illus.js"
INDEX = RACINE / "frontend" / "dist" / "index.html"
IDS = list(EE.POST_PILE)


def _lire(p):
    return p.read_bytes().decode("utf-8") if p.is_file() else ""


def _meta(t, nom):
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(nom), t)
    return m.group(1) if m else None


# ── [P] pages ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[P] une page par preset de post-traitement")
check("P0 le script de la chaîne s'importe", SI is not None)
check("P1 15 presets au catalogue (livrés par t276)", len(IDS) == 15, IDS)
pages = {i: _lire(PAGES / f"{i}.html") for i in IDS}
check(f"P2 une page par preset de POST_PILE ({len(IDS)})", all(pages.values()), [i for i, t in pages.items() if not t])
orphelines = sorted(p.stem for p in PAGES.glob("*.html") if p.stem not in EE.POST_PILE) if PAGES.is_dir() else ["?"]
check("P3 aucune page orpheline (hors catalogue)", not orphelines, orphelines)
refus = {i: MC.controler(t) for i, t in pages.items() if t and MC.controler(t)}
check("P4 chaque page passe le contrôle statique motion_code", all(pages.values()) and not refus, refus)
_themes = {p.stem for p in STYLES.glob("*.json")}
_sk = {i: _meta(t, "dz-skill") for i, t in pages.items()}
check("P5 chaque page déclare sa fiche de style MAISON (style-<thème> existant)",
      all(s and s.startswith("style-") and s[6:] in _themes for s in _sk.values()), _sk)
check("P6 chaque page nomme son preset (dz-geste = id)", all(_meta(t, "dz-geste") == i for i, t in pages.items()),
      {i: _meta(t, "dz-geste") for i, t in pages.items()})
_aff = {i: _meta(t, "dz-affiche") for i, t in pages.items()}
check("P7 instant de l'affiche déclaré, dans [0, 4[ s",
      all(a is not None and re.fullmatch(r"\d+(\.\d+)?", a) and 0 <= float(a) < 4 for a in _aff.values()), _aff)
check("P8 animation pilotée par l'horloge virtuelle (window.dzFrame) et bouclée sur 4 s",
      all("window.dzFrame" in t and re.search(r"%\s*4\b", t) for t in pages.values()),
      [i for i, t in pages.items() if "window.dzFrame" not in t or not re.search(r"%\s*4\b", t)])
check("P9 pages de 480×270 (dz-format)", all(_meta(t, "dz-format") == "480x270" for t in pages.values()))
check("P10 aucune page ne charge de police ou d'image extérieure (data: seulement)",
      all("url(" not in t.replace("url(#", "") or "url(data:" in t for t in pages.values()))
check("P11 chaque page montre l'avant ET l'après (volet de comparaison, comme l'écran)",
      all("avant" in t.lower() and "apres" in t.lower().replace("après", "apres") for t in pages.values()),
      [i for i, t in pages.items() if "avant" not in t.lower()])
if SI:
    check("P12 verifier(jeu='post') vert sur le dépôt", lambda: SI.verifier(jeu="post") == [],
          SI.verifier(jeu="post") if SI and hasattr(SI, "JEUX") else "")
    _r2 = dict(EE.POST_PILE)
    _r2["preset-neuf"] = EE.POST_PILE["bloom"]
    check("P13 mutation : un preset ajouté sans sa page → rouge, et nommé",
          lambda: any("preset-neuf" in m for m in SI.verifier(registre=_r2, jeu="post")))
    if PAGES.is_dir():
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(PAGES, pathlib.Path(td) / "p")
            (pathlib.Path(td) / "p" / "bloom.html").unlink()
            (pathlib.Path(td) / "p" / "vhs.html").write_text(
                _lire(PAGES / "vhs.html").replace("</body>", "<script>fetch('x')</script></body>"), encoding="utf-8")
            _m = SI.verifier(pages=pathlib.Path(td) / "p", jeu="post")
            check("P14 mutation : page retirée → rouge", any("bloom" in m for m in _m), _m)
            check("P15 mutation : page refusée par motion_code → rouge", any("vhs" in m for m in _m), _m)

# ── [R] rendus ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] rendus statiques")
MAN = SORTIE / "index.json"
man = json.loads(_lire(MAN)) if MAN.is_file() else {}
check("R1 manifeste : 480×270, 30 i/s, 4 s, moteur embarqué nommé",
      (man.get("W"), man.get("H"), man.get("fps"), man.get("duree_s")) == (480, 270, 30, 4)
      and man.get("navigateur") == MC.NAVIGATEUR_VERSION,
      {k: man.get(k) for k in ("W", "H", "fps", "duree_s", "navigateur")})
G = man.get("presets") or {}
check("R2 manifeste : un rendu par preset, dans l'ordre du catalogue", list(G) == IDS, list(G))
if SI:
    check("R3 rendus à jour (empreinte de chaque page = celle du rendu)", lambda: SI.verifier_rendus(jeu="post") == [],
          SI.verifier_rendus(jeu="post") if hasattr(SI, "JEUX") else "")
    if SORTIE.is_dir():
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(SORTIE, pathlib.Path(td) / "s")
            m2 = json.loads(_lire(pathlib.Path(td) / "s" / "index.json"))
            m2["presets"]["glitch_rgb"]["source"] = "0" * 40
            (pathlib.Path(td) / "s" / "index.json").write_text(json.dumps(m2), encoding="utf-8")
            (pathlib.Path(td) / "s" / "duotone.webp").unlink()
            _m = SI.verifier_rendus(sortie=pathlib.Path(td) / "s", jeu="post")
            check("R4 mutation : page modifiée sans nouveau rendu → rouge", any("glitch_rgb" in m for m in _m), _m)
            check("R5 mutation : affiche manquante → rouge", any("duotone" in m for m in _m), _m)

FFPROBE = shutil.which("ffprobe")
check("R6 ffprobe disponible (lecture des rendus)", FFPROBE)


def _sonde(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=codec_name,width,height,nb_read_packets:format=duration,format_name", "-of", "json",
                        str(p)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return (s.get("codec_name"), s.get("width"), s.get("height"), int(s.get("nb_read_packets") or 0),
            round(float((d.get("format") or {}).get("duration") or 0), 2))


from PIL import Image  # noqa: E402
tailles, sondes, affiches = {}, {}, {}
for i in IDS:
    w, a = SORTIE / f"{i}.webm", SORTIE / f"{i}.webp"
    tailles[i] = w.stat().st_size if w.is_file() else None
    sondes[i] = _sonde(w) if w.is_file() and FFPROBE else None
    try:
        with Image.open(a) as im:
            affiches[i] = (im.format, im.size, a.stat().st_size)
    except Exception:  # noqa: BLE001
        affiches[i] = None
check("R7 un WebM par preset, ≤ 250 Ko", all(t and t <= 250_000 for t in tailles.values()), tailles)
check("R8 WebM : VP9, 480×270, 120 images, 4 s", all(s and s[0] == "vp9" and s[1:4] == (480, 270, 120)
                                                     and abs(s[4] - 4.0) <= 0.05 for s in sondes.values()), sondes)
check("R9 une affiche WebP 480×270 par preset (≤ 40 Ko)",
      all(a and a[0] == "WEBP" and a[1] == (480, 270) and a[2] <= 40_000 for a in affiches.values()), affiches)
check("R10 tailles déclarées au manifeste = fichiers",
      all(tailles[i] and (G.get(i) or {}).get("octets") == tailles[i] for i in IDS))
_tot = sum(t or 0 for t in tailles.values()) + sum((a or (0, 0, 0))[2] for a in affiches.values())
check("R11 poids total borné pour l'installeur (≤ 3 Mo)", 0 < _tot <= 3_000_000, _tot)
_hs = {i: hashlib.sha1((SORTIE / f"{i}.webp").read_bytes()).hexdigest() if (SORTIE / f"{i}.webp").is_file() else None
       for i in IDS}
check("R12 quinze affiches distinctes (pas une même image copiée)",
      None not in _hs.values() and len(set(_hs.values())) == len(IDS))
orph = sorted(p.name for p in SORTIE.iterdir() if p.name != "index.json" and p.stem not in EE.POST_PILE) \
    if SORTIE.is_dir() else ["?"]
check("R13 aucun fichier orphelin dans illus-post/", not orph, orph)

# ── [C] chaîne à deux jeux ────────────────────────────────────────────────────────────────────────────────────────
print("[C] la chaîne de t275 porte deux jeux")
if SI:
    check("C1 deux jeux déclarés : vfx (gestes, t275) et post (presets, t278)",
          lambda: set(SI.JEUX) == {"vfx", "post"} and SI.JEUX["post"]["cle"] == "presets"
          and SI.JEUX["vfx"]["cle"] == "gestes")
    check("C2 le jeu vfx de t275 reste vert (pages et rendus)",
          lambda: SI.verifier(jeu="vfx") == [] and SI.verifier_rendus(jeu="vfx") == [])
    check("C3 les défauts sans jeu restent ceux de t275 (VFX IA)", lambda: SI.verifier() == SI.verifier(jeu="vfx"))
_PY = sys.executable
_p = subprocess.run([_PY, str(RACINE / "scripts" / "sonvfx_illustrations.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=120,
                    env={**os.environ, "PYTHONUTF8": "1"})
check("C4 `sonvfx_illustrations.py --check` vert et couvre les deux jeux",
      _p.returncode == 0 and "12 gestes" in _p.stdout and "15 presets" in _p.stdout, (_p.stdout + _p.stderr)[-500:])

# ── [G] garde G3 ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[G] garde G3 : aucun contenu de prompt-motion.com dans les fichiers neufs")
EMP = json.loads(_lire(_ICI / "motion_garde_empreintes.json") or "{}").get("empreintes") or []
check("G1 empreintes lues", len(EMP) >= 400, len(EMP))


def _jetons(texte):
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.findall(r"[a-z0-9_]+", t)


def _h_phrase(j):
    return hashlib.sha256(("dzmotion|" + " ".join(j)).encode("utf-8")).hexdigest()[:20]


def _h_tete(j):
    return hashlib.sha256(("dzmotion1|" + j).encode("utf-8")).hexdigest()[:12]


TETES = {}
for n, t, h in EMP:
    TETES.setdefault(t, []).append((n, h))


def _touches(texte):
    jj = _jetons(texte)
    return [h for k, j in enumerate(jj) for n, h in TETES.get(_h_tete(j), ()) if _h_phrase(jj[k:k + n]) == h]


NEUFS = [*sorted(PAGES.glob("*.html")), RACINE / "scripts" / "sonvfx_illustrations.py", JS_SRC, MAN,
         pathlib.Path(__file__)]
trouves = {p.name: _touches(_lire(p)) for p in NEUFS if _touches(_lire(p))}
check(f"G2 {len(NEUFS)} fichiers neufs : aucun titre, pseudo ni extrait tiers", not trouves, trouves)
_tem = " ".join(reversed(["dz", "motion", "garde", "temoin"]))
check("G3 la garde attrape la phrase témoin au milieu d'un texte", bool(_touches(f"Début. {_tem.upper()} ! Fin.")))

# ── [E] écran ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[E] vignettes du catalogue et de la pile")
JS = _lire(JS_SRC)
check("E1 script partagé présent et copié à l'octet dans dist/shared", JS and JS_SRC.read_bytes() == (
    JS_DIST.read_bytes() if JS_DIST.is_file() else b""))
_ix = _lire(INDEX)
_b = '<script src="/shared/dz-post-illus.js"></script>'
check("E2 balise du script, une fois, dans la SPA, après dz-vfx-illus.js",
      _ix.count(_b) == 1 and _ix.find('<script src="/shared/dz-vfx-illus.js"></script>') < _ix.find(_b))
check("E3 lit le catalogue (ajout-<id>), la pile (maillon[data-preset]) et le manifeste /sonvfx/illus-post/",
      "ajout-" in JS and "maillon" in JS and "data-preset" in JS and "/sonvfx/illus-post/" in JS)
check("E4 survol ET focus (mouseenter/focusin), retour à l'affiche (mouseleave/focusout)",
      all(e in JS for e in ("mouseenter", "focusin", "mouseleave", "focusout")))
check("E5 prefers-reduced-motion respecté", "prefers-reduced-motion" in JS)
check("E6 aucun arrondi (angles vifs de Son & VFX)", "border-radius" not in JS and "borderRadius" not in JS)
check("E7 aucun texte visible en dur (décor aria-hidden, pas de dzT)", 'aria-hidden' in JS
      and not re.search(r"textContent\s*=|innerText\s*=", JS))
check("E8 aucune adresse extérieure", not re.search(r"https?:|//[a-z0-9-]+\.[a-z]", JS))
check("E9 la page de t276 et le maillon ne sont pas touchés (décor par script partagé seulement)",
      "dz-post-illus" not in _lire(RACINE / "frontend" / "patches" / "sonvfx-post.js")
      and "dz-post-illus" not in _lire(RACINE / "scripts" / "patch_bundle_dzsonvfx.py"))
NODE = shutil.which("node")
check("E10 node disponible", NODE)
_HARNAIS = r"""
const fs=require("fs"),vm=require("vm");
function El(tag){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.style={};this.ls={};this.parentNode=null;
  this.paused=true;this.currentTime=0;}
El.prototype.setAttribute=function(k,v){this.attrs[k]=String(v)};
El.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
El.prototype.hasAttribute=function(k){return k in this.attrs};
El.prototype.removeAttribute=function(k){delete this.attrs[k]};
El.prototype.appendChild=function(c){c.parentNode=this;this.children.push(c);return c};
El.prototype.insertBefore=function(c,r){c.parentNode=this;var i=this.children.indexOf(r);if(i<0)this.children.push(c);else this.children.splice(i,0,c);return c};
El.prototype.addEventListener=function(t,f){(this.ls[t]=this.ls[t]||[]).push(f)};
El.prototype.fire=function(t){(this.ls[t]||[]).forEach(f=>f({type:t,target:this}))};
function correspond(c,s){
  var m;
  if((m=/^\[data-sv-post\^="([^"]+)"\]$/.exec(s)))return (c.attrs["data-sv-post"]||"").indexOf(m[1])===0;
  if((m=/^\[data-sv-post="([^"]+)"\]\[data-preset\]$/.exec(s)))return c.attrs["data-sv-post"]===m[1]&&c.attrs["data-preset"]!=null;
  if((m=/^\[data-sv-post="([^"]+)"\]$/.exec(s)))return c.attrs["data-sv-post"]===m[1];
  if(s.charAt(0)===".")return (" "+(c.attrs["class"]||"")+" ").indexOf(" "+s.slice(1)+" ")>=0;
  return s===c.tagName.toLowerCase()}
El.prototype.querySelectorAll=function(s){var out=[],l=s.split(",").map(x=>x.trim());(function w(n){n.children.forEach(function(c){
  if(l.some(x=>correspond(c,x)))out.push(c);w(c)})})(this);return out};
El.prototype.querySelector=function(s){return this.querySelectorAll(s)[0]||null};
El.prototype.play=function(){this.paused=false;return Promise.resolve()};
El.prototype.pause=function(){this.paused=true};
Object.defineProperty(El.prototype,"className",{get(){return this.attrs["class"]||""},set(v){this.attrs["class"]=v}});
Object.defineProperty(El.prototype,"firstChild",{get(){return this.children[0]||null}});
const body=new El("body"),head=new El("head");
const doc={body,head,createElement:t=>new El(t),createTextNode:t=>({texte:t}),querySelectorAll:s=>body.querySelectorAll(s),
  getElementById:()=>null,readyState:"complete",addEventListener(){}};
let reduit=process.argv[3]==="reduit",obs=null,obsOpts=null;
const ctx={document:doc,window:{},console,setTimeout:(f)=>f(),clearTimeout(){},
  matchMedia:q=>({matches:reduit&&q.indexOf("reduce")>=0,addEventListener(){},addListener(){}}),
  MutationObserver:function(f){obs=f;this.observe=function(n,o){obsOpts=o}},
  fetch:u=>{ctx.url=u;return Promise.resolve({ok:true,json:()=>Promise.resolve(JSON.parse(fs.readFileSync(process.argv[4],"utf8")))})}};
ctx.window=ctx;
function ajout(id){const b=new El("button");b.setAttribute("class","dzsvo-ajout");b.setAttribute("data-sv-post","ajout-"+id);
  b.appendChild(new El("svg"));const s=new El("span");b.appendChild(s);body.appendChild(b);return b}
function maillon(id){const d=new El("div");d.setAttribute("class","dzsvo-maillon");d.setAttribute("data-sv-post","maillon");
  d.setAttribute("data-preset",id);const t=new El("div");t.setAttribute("class","dzsvo-mtete");
  const p=new El("span");p.setAttribute("class","dzsvo-poignee");t.appendChild(p);d.appendChild(t);body.appendChild(d);return d}
const a1=ajout("bloom"),a2=ajout("inconnu"),m1=maillon("vhs"),autre=new El("button");
autre.setAttribute("data-sv-post","vider");body.appendChild(autre);
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],"utf8"),ctx);
setImmediate(function(){
  const m2=maillon("duotone");if(obs)obs([]);
  setImmediate(function(){
  const f=a1.querySelector(".dzpi"),img=f&&f.querySelector("img"),vid=f&&f.querySelector("video");
  const t1=m1.querySelector(".dzsvo-mtete"),fm=m1.querySelector(".dzpi");
  const r={url:ctx.url,pose:!!f,premier:a1.children[0]===f,aria:f&&f.getAttribute("aria-hidden"),
    img:img&&img.getAttribute("src"),vidsrc0:vid&&vid.getAttribute("src"),inconnu:!a2.querySelector(".dzpi"),
    autre:!autre.querySelector(".dzpi"),pile:!!fm,pileTete:!!t1&&t1.children[0]===fm,
    pileImg:fm&&fm.querySelector("img").getAttribute("src"),tardif:!!m2.querySelector(".dzpi"),
    attrs:!!(obsOpts&&obsOpts.attributes&&(obsOpts.attributeFilter||[]).indexOf("data-preset")>=0)};
  a1.fire("mouseenter");r.vidsrc1=vid&&vid.getAttribute("src");r.joue=vid&&!vid.paused;r.etat1=f&&f.getAttribute("data-joue");
  if(vid)vid.currentTime=1.7;
  a1.fire("mouseleave");r.arret=vid&&vid.paused;r.temps=vid&&vid.currentTime;r.etat2=f&&f.getAttribute("data-joue");
  m1.fire("focusin");const vm1=fm&&fm.querySelector("video");r.focus=vm1&&!vm1.paused;r.focusSrc=vm1&&vm1.getAttribute("src");
  m1.fire("focusout");r.defocus=vm1&&vm1.paused;
  m1.setAttribute("data-preset","grain16");if(obs)obs([]);
  setImmediate(function(){
    const fm2=m1.querySelectorAll(".dzpi");r.change=fm2.length===1&&fm2[0].querySelector("img").getAttribute("src");
    m1.fire("mouseenter");const vm2=fm2[0]&&fm2[0].querySelector("video");r.changeVid=vm2&&vm2.getAttribute("src");
    r.ecouteurs=(m1.ls.mouseenter||[]).length;
    a1.fire("mouseenter");a1.fire("mouseenter");if(obs)obs([]);
    setImmediate(function(){r.unique=a1.querySelectorAll(".dzpi").length;console.log(JSON.stringify(r))})})})});
"""
if NODE and JS and MAN.is_file():
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.cjs"
        h.write_text(_HARNAIS, encoding="utf-8")
        res = {}
        for mode in ("normal", "reduit"):
            p = subprocess.run([NODE, str(h), str(JS_SRC), mode, str(MAN)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60)
            try:
                res[mode] = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception:  # noqa: BLE001
                res[mode] = {"erreur": (p.stdout + p.stderr)[-600:]}
    n, rd = res["normal"], res["reduit"]
    check("E11 manifeste lu à /sonvfx/illus-post/index.json", n.get("url") == "/sonvfx/illus-post/index.json", n)
    check("E12 catalogue : vignette en tête du bouton, décor aria-hidden", n.get("pose") and n.get("premier")
          and n.get("aria") == "true", n)
    check("E13 affiche = /sonvfx/illus-post/<id>.webp ; la vidéo n'est chargée qu'au premier survol",
          n.get("img") == "/sonvfx/illus-post/bloom.webp" and not n.get("vidsrc0")
          and n.get("vidsrc1") == "/sonvfx/illus-post/bloom.webm", n)
    check("E14 survol : lecture ; sortie : pause et retour au début (affiche)", n.get("joue") and n.get("etat1") == "1"
          and n.get("arret") and n.get("temps") == 0 and n.get("etat2") is None, n)
    check("E15 pile : vignette en tête de l'en-tête du maillon, affiche de son preset", n.get("pile")
          and n.get("pileTete") and n.get("pileImg") == "/sonvfx/illus-post/vhs.webp", n)
    check("E16 pile : focus clavier → lecture de l'animation du preset ; perte du focus → pause",
          n.get("focus") and n.get("focusSrc") == "/sonvfx/illus-post/vhs.webm" and n.get("defocus"), n)
    check("E17 seuls les presets du manifeste et les éléments visés sont décorés", n.get("inconnu") and n.get("autre"), n)
    check("E18 maillon rendu après coup (MutationObserver) décoré aussi ; une seule vignette par élément",
          n.get("tardif") and n.get("unique") == 1, n)
    check("E19 maillon dont le preset change : vignette suivie (attributs observés), une seule, un seul écouteur",
          n.get("attrs") and n.get("change") == "/sonvfx/illus-post/grain16.webp"
          and n.get("changeVid") == "/sonvfx/illus-post/grain16.webm" and n.get("ecouteurs") == 1, n)
    check("E20 mouvement réduit : vignettes posées, aucune lecture au survol ni au focus",
          rd.get("pose") and rd.get("pile") and not rd.get("joue") and not rd.get("vidsrc1") and not rd.get("focus"), rd)

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_illus_post():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
