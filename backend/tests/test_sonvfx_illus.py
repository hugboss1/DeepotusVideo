# -*- coding: utf-8 -*-
"""Son & VFX › VFX IA : illustrations animées en motion design codé (t275, 22/10/2026).

Une page HTML / SVG / Canvas par geste de `vfx_ia.REGISTRE` (scripts/sonvfx_illus/<id>.html), écrite selon une fiche
de style MAISON (backend/app/motion/styles) et passée au contrôle statique `motion_code`, est rendue AU
DÉVELOPPEMENT (décision Q3 : statiques, aucun coût à l'exécution) par `scripts/sonvfx_illustrations.py` dans le
chrome-headless-shell embarqué : 480×270, 30 i/s, 4 s en boucle → frontend/dist/sonvfx/illus/<id>.webm (≤ 250 Ko) et
une affiche <id>.webp. Le script partagé dz-vfx-illus.js pose l'affiche sur chaque carte du rail, lit l'animation au
survol ou au focus, et reste fixe en `prefers-reduced-motion`. Sections :
  [P] pages : une par geste (rouge si un geste arrive sans la sienne), contrôle motion_code, fiche maison, boucle ;
  [R] rendus : manifeste à jour (empreinte de chaque page), WebM VP9 480×270 de 4 s ≤ 250 Ko, affiche WebP 480×270 ;
  [G] garde G3 : aucun contenu de prompt-motion.com dans les fichiers neufs ;
  [E] écran : script partagé (copie à l'octet, balise dans la SPA), survol, focus, mouvement réduit, aucun arrondi,
      aucun texte visible, sous node avec un faux DOM.
Run (depuis backend/) : & $PY tests/test_sonvfx_illus.py"""
import hashlib, json, pathlib, re, shutil, subprocess, sys, tempfile, unicodedata
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


from app.services import vfx_ia as VI  # noqa: E402
from app.services import motion_code as MC  # noqa: E402

try:
    import sonvfx_illustrations as SI  # noqa: E402
except Exception as e:  # noqa: BLE001
    SI = None
    print(f"  (sonvfx_illustrations introuvable : {type(e).__name__}: {e})")

PAGES = RACINE / "scripts" / "sonvfx_illus"
SORTIE = RACINE / "frontend" / "dist" / "sonvfx" / "illus"
STYLES = RACINE / "backend" / "app" / "motion" / "styles"
JS_SRC = RACINE / "frontend" / "shared" / "dz-vfx-illus.js"
JS_DIST = RACINE / "frontend" / "dist" / "shared" / "dz-vfx-illus.js"
INDEX = RACINE / "frontend" / "dist" / "index.html"
IDS = list(VI.REGISTRE)


def _lire(p):
    return p.read_bytes().decode("utf-8") if p.is_file() else ""


# ── [P] pages ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[P] une page par geste")
check("P0 le script de la chaîne s'importe", SI is not None)
pages = {i: _lire(PAGES / f"{i}.html") for i in IDS}
check(f"P1 une page par geste du registre ({len(IDS)})", all(pages.values()),
      [i for i, t in pages.items() if not t])
orphelines = sorted(p.stem for p in PAGES.glob("*.html") if p.stem not in VI.REGISTRE) if PAGES.is_dir() else ["?"]
check("P2 aucune page orpheline (hors registre)", not orphelines, orphelines)
refus = {i: MC.controler(t) for i, t in pages.items() if t and MC.controler(t)}
check("P3 chaque page passe le contrôle statique motion_code", all(pages.values()) and not refus, refus)
_themes = {p.stem for p in STYLES.glob("*.json")}


def _meta(t, nom):
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(nom), t)
    return m.group(1) if m else None


_sk = {i: _meta(t, "dz-skill") for i, t in pages.items()}
check("P4 chaque page déclare sa fiche de style MAISON (style-<thème> existant)",
      all(s and s.startswith("style-") and s[6:] in _themes for s in _sk.values()), _sk)
check("P5 chaque page nomme son geste (dz-geste = id)", all(_meta(t, "dz-geste") == i for i, t in pages.items()),
      {i: _meta(t, "dz-geste") for i, t in pages.items()})
_aff = {i: _meta(t, "dz-affiche") for i, t in pages.items()}
check("P6 instant de l'affiche déclaré, dans [0, 4[ s",
      all(a is not None and re.fullmatch(r"\d+(\.\d+)?", a) and 0 <= float(a) < 4 for a in _aff.values()), _aff)
check("P7 animation pilotée par l'horloge virtuelle (window.dzFrame) et bouclée sur 4 s",
      all("window.dzFrame" in t and re.search(r"%\s*4\b", t) for t in pages.values()),
      [i for i, t in pages.items() if "window.dzFrame" not in t or not re.search(r"%\s*4\b", t)])
check("P8 pages de 480×270 (dz-format)", all(_meta(t, "dz-format") == "480x270" for t in pages.values()))
check("P9 aucune page ne charge de police ou d'image extérieure (data: seulement)",
      all("url(" not in t.replace("url(#", "") or "url(data:" in t for t in pages.values()))
if SI:
    check("P10 verifier() vert sur le dépôt", lambda: SI.verifier() == [], SI.verifier() if SI else "")
    _r2 = dict(VI.REGISTRE)
    _r2["geste-neuf"] = VI.REGISTRE["eau"]
    check("P11 mutation : un geste ajouté sans sa page → rouge, et nommé",
          lambda: any("geste-neuf" in m for m in SI.verifier(registre=_r2)), SI.verifier(registre=_r2))
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(PAGES, pathlib.Path(td) / "p")
        (pathlib.Path(td) / "p" / "eau.html").unlink()
        (pathlib.Path(td) / "p" / "coloriser.html").write_text(
            _lire(PAGES / "coloriser.html").replace("</body>", "<script>fetch('x')</script></body>"), encoding="utf-8")
        _m = SI.verifier(pages=pathlib.Path(td) / "p")
        check("P12 mutation : page retirée → rouge", any("eau" in m for m in _m), _m)
        check("P13 mutation : page refusée par motion_code → rouge", any("coloriser" in m for m in _m), _m)

# ── [R] rendus ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] rendus statiques")
MAN = SORTIE / "index.json"
man = json.loads(_lire(MAN)) if MAN.is_file() else {}
check("R1 manifeste : 480×270, 30 i/s, 4 s, moteur embarqué nommé",
      (man.get("W"), man.get("H"), man.get("fps"), man.get("duree_s")) == (480, 270, 30, 4)
      and man.get("navigateur") == MC.NAVIGATEUR_VERSION, {k: man.get(k) for k in ("W", "H", "fps", "duree_s",
                                                                                   "navigateur")})
G = man.get("gestes") or {}
check("R2 manifeste : un rendu par geste, dans l'ordre du registre", list(G) == IDS, list(G))
if SI:
    check("R3 rendus à jour (empreinte de chaque page = celle du rendu)", lambda: SI.verifier_rendus() == [],
          SI.verifier_rendus())
    with tempfile.TemporaryDirectory() as td:
        shutil.copytree(SORTIE, pathlib.Path(td) / "s")
        m2 = json.loads(_lire(pathlib.Path(td) / "s" / "index.json"))
        m2["gestes"]["jour-nuit"]["source"] = "0" * 40
        (pathlib.Path(td) / "s" / "index.json").write_text(json.dumps(m2), encoding="utf-8")
        (pathlib.Path(td) / "s" / "agrandir.webp").unlink()
        _m = SI.verifier_rendus(sortie=pathlib.Path(td) / "s")
        check("R4 mutation : page modifiée sans nouveau rendu → rouge", any("jour-nuit" in m for m in _m), _m)
        check("R5 mutation : affiche manquante → rouge", any("agrandir" in m for m in _m), _m)

FFPROBE = shutil.which("ffprobe")
check("R6 ffprobe disponible (lecture des rendus)", FFPROBE)


def _sonde(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=codec_name,width,height,nb_read_packets:format=duration,format_name", "-of", "json",
                        str(p)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return (s.get("codec_name"), s.get("width"), s.get("height"), int(s.get("nb_read_packets") or 0),
            round(float((d.get("format") or {}).get("duration") or 0), 2), (d.get("format") or {}).get("format_name"))


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
check("R7 un WebM par geste, ≤ 250 Ko", all(t and t <= 250_000 for t in tailles.values()), tailles)
check("R8 WebM : VP9, 480×270, 120 images, 4 s", all(s and s[0] == "vp9" and s[1:4] == (480, 270, 120)
                                                     and abs(s[4] - 4.0) <= 0.05 for s in sondes.values()), sondes)
check("R9 une affiche WebP 480×270 par geste (≤ 40 Ko)",
      all(a and a[0] == "WEBP" and a[1] == (480, 270) and a[2] <= 40_000 for a in affiches.values()), affiches)
check("R10 tailles déclarées au manifeste = fichiers", all(tailles[i] and (G.get(i) or {}).get("octets") == tailles[i]
                                                           for i in IDS))
_tot = sum(t or 0 for t in tailles.values()) + sum((a or (0, 0, 0))[2] for a in affiches.values())
check("R11 poids total borné pour l'installeur (≤ 2,5 Mo)", 0 < _tot <= 2_500_000, _tot)
_hs = {}
for i in IDS:
    a = SORTIE / f"{i}.webp"
    _hs[i] = hashlib.sha1(a.read_bytes()).hexdigest() if a.is_file() else None
check("R12 douze affiches distinctes (pas une même image copiée)", None not in _hs.values()
      and len(set(_hs.values())) == len(IDS))
orph = sorted(p.name for p in SORTIE.iterdir() if p.name != "index.json" and p.stem not in VI.REGISTRE) \
    if SORTIE.is_dir() else ["?"]
check("R13 aucun fichier orphelin dans illus/", not orph, orph)

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
print("[E] cartes du rail VFX IA")
JS = _lire(JS_SRC)
check("E1 script partagé présent et copié à l'octet dans dist/shared", JS and JS_SRC.read_bytes() == (
    JS_DIST.read_bytes() if JS_DIST.is_file() else b""))
_ix = _lire(INDEX)
check("E2 balise du script, une fois, dans la SPA", _ix.count('<script src="/shared/dz-vfx-illus.js"></script>') == 1)
check("E3 lit les cartes [data-dzvfxia] et le manifeste /sonvfx/illus/",
      "data-dzvfxia" in JS and "/sonvfx/illus/" in JS)
check("E4 survol ET focus (mouseenter/focusin), retour à l'affiche (mouseleave/focusout)",
      all(e in JS for e in ("mouseenter", "focusin", "mouseleave", "focusout")))
check("E5 prefers-reduced-motion respecté", "prefers-reduced-motion" in JS)
check("E6 aucun arrondi (angles vifs de Son & VFX)", "border-radius" not in JS and "borderRadius" not in JS)
check("E7 aucun texte visible en dur (décor aria-hidden, pas de dzT)", 'aria-hidden' in JS
      and not re.search(r"textContent\s*=|innerText\s*=", JS))
check("E8 aucune adresse extérieure", not re.search(r"https?:|//[a-z0-9-]+\.[a-z]", JS))
NODE = shutil.which("node")
check("E9 node disponible", NODE)
_HARNAIS = r"""
const fs=require("fs"),vm=require("vm");
function El(tag){this.tagName=tag.toUpperCase();this.children=[];this.attrs={};this.style={};this.ls={};this.parentNode=null;
  this.dataset={};this.paused=true;this.currentTime=0;this.src="";}
El.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);if(k.indexOf("data-")===0)this.dataset[k.slice(5)]=String(v)};
El.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
El.prototype.hasAttribute=function(k){return k in this.attrs};
El.prototype.removeAttribute=function(k){delete this.attrs[k]};
El.prototype.appendChild=function(c){c.parentNode=this;this.children.push(c);return c};
El.prototype.insertBefore=function(c,r){c.parentNode=this;var i=this.children.indexOf(r);if(i<0)this.children.push(c);else this.children.splice(i,0,c);return c};
El.prototype.addEventListener=function(t,f){(this.ls[t]=this.ls[t]||[]).push(f)};
El.prototype.fire=function(t){(this.ls[t]||[]).forEach(f=>f({type:t,target:this}))};
El.prototype.querySelector=function(s){return this.querySelectorAll(s)[0]||null};
El.prototype.querySelectorAll=function(s){var out=[];(function w(n){n.children.forEach(function(c){
  if(s==="[data-dzvfxia]"&&c.attrs["data-dzvfxia"]!=null)out.push(c);
  else if(s.charAt(0)==="."&&(" "+(c.attrs["class"]||"")+" ").indexOf(" "+s.slice(1)+" ")>=0)out.push(c);
  else if(s===c.tagName.toLowerCase())out.push(c);w(c)})})(this);return out};
El.prototype.play=function(){this.paused=false;return Promise.resolve()};
El.prototype.pause=function(){this.paused=true};
El.prototype.load=function(){};
Object.defineProperty(El.prototype,"className",{get(){return this.attrs["class"]||""},set(v){this.attrs["class"]=v}});
Object.defineProperty(El.prototype,"firstChild",{get(){return this.children[0]||null}});
const body=new El("body"),head=new El("head");
const doc={body,head,createElement:t=>new El(t),createTextNode:t=>({texte:t}),querySelectorAll:s=>body.querySelectorAll(s),
  getElementById:()=>null,readyState:"complete",addEventListener(){}};
let reduit=process.argv[3]==="reduit",obs=null;
const ctx={document:doc,window:{},console,setTimeout:(f)=>f(),clearTimeout(){},
  matchMedia:q=>({matches:reduit&&q.indexOf("reduce")>=0,addEventListener(){},addListener(){}}),
  MutationObserver:function(f){obs=f;this.observe=function(){}},
  fetch:u=>Promise.resolve({ok:true,json:()=>Promise.resolve(JSON.parse(fs.readFileSync(process.argv[4],"utf8")))})};
ctx.window=ctx;ctx.window.matchMedia=ctx.matchMedia;
function carte(id){const b=new El("button");b.setAttribute("class","svm-model");b.setAttribute("data-dzvfxia",id);
  const r=new El("div");r.setAttribute("class","svm-genrow");b.appendChild(r);body.appendChild(b);return b}
const c1=carte("eau"),c2=carte("rail"),c3=carte("inconnu");
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],"utf8"),ctx);
setImmediate(function(){
  const c4=carte("coloriser");if(obs)obs([]);
  setImmediate(function(){
  const f=c1.querySelector(".dzvi"),img=f&&f.querySelector("img"),vid=f&&f.querySelector("video");
  const r={pose:!!f,premier:c1.children[0]===f,aria:f&&f.getAttribute("aria-hidden"),
    img:img&&img.getAttribute("src"),vidsrc0:vid&&vid.getAttribute("src"),
    rail:!c2.querySelector(".dzvi"),inconnu:!c3.querySelector(".dzvi"),tardif:!!c4.querySelector(".dzvi")};
  c1.fire("mouseenter");r.vidsrc1=vid&&vid.getAttribute("src");r.joue=vid&&!vid.paused;r.etat1=f&&f.getAttribute("data-joue");if(vid)vid.currentTime=1.7;
  c1.fire("mouseleave");r.arret=vid&&vid.paused;r.temps=vid&&vid.currentTime;r.etat2=f&&f.getAttribute("data-joue");
  c4.fire("focusin");const v4=c4.querySelector("video");r.focus=v4&&!v4.paused;c4.fire("focusout");r.defocus=v4&&v4.paused;
  c1.fire("mouseenter");c1.fire("mouseenter");r.unique=c1.querySelectorAll(".dzvi").length;
  console.log(JSON.stringify(r))})});
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
    check("E10 affiche posée en tête de la carte, décor aria-hidden", n.get("pose") and n.get("premier")
          and n.get("aria") == "true", n)
    check("E11 affiche = /sonvfx/illus/<id>.webp ; la vidéo n'est chargée qu'au premier survol",
          n.get("img") == "/sonvfx/illus/eau.webp" and not n.get("vidsrc0") and n.get("vidsrc1") == "/sonvfx/illus/eau.webm", n)
    check("E12 survol : lecture ; sortie : pause et retour au début (affiche)", n.get("joue") and n.get("etat1") == "1"
          and n.get("arret") and n.get("temps") == 0 and n.get("etat2") is None, n)
    check("E13 focus clavier : lecture ; perte du focus : pause", n.get("focus") and n.get("defocus"), n)
    check("E14 seuls les gestes du manifeste sont décorés (ni « rail », ni un id inconnu)",
          n.get("rail") and n.get("inconnu"), n)
    check("E15 carte rendue après coup (MutationObserver) décorée aussi, une seule fois",
          n.get("tardif") and n.get("unique") == 1, n)
    check("E16 mouvement réduit : affiche posée, aucune lecture au survol ni au focus",
          rd.get("pose") and not rd.get("joue") and not rd.get("vidsrc1") and not rd.get("focus"), rd)

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_illus():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
