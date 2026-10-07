# -*- coding: utf-8 -*-
"""Plan-studio T8 (tache #70 du suivi, 02/10/2026) — le tiroir de resultat du Studio se PARCOURT image par image.
DECISIONS DE L'UTILISATEUR (02/10) : la cadence est LUE dans le fichier rendu (GET /jobs/{id}/media, ffprobe ; illisible
-> 30 i/s et la raison DITE) ; « , » « . » tant que le tiroir est ouvert (sauf en saisie) + ← → sur la reglette ;
lecture automatique a l'ouverture, PAUSE au premier pas. Code dans le maillon montage.
Ce que le plan faisait faux, et que ce banc garde : la cadence prise au noeud Render (le compilateur l'ignore, 30 en
dur ; un clip Seedance/HeyGen garde la sienne) ; sa garde clavier coupait « , » « . » des que SA reglette avait le
focus ; « autoPlay » ne disparait pas du bundle (deux autres lecteurs le gardent) ; viser le BORD d'une image montre
souvent la precedente (on vise son milieu).
Data-dir isole, cles de banc, aucun appel paye ; un vrai clip 24 i/s fabrique par ffmpeg.
Temoin positif : la base (fa6c11ba) n'a ni la route ni le lecteur.
Run (depuis backend/) : & $PY tests/test_studio_scrub.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzscrub_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "fa6c11ba"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni la route de cadence ni le lecteur", r0.returncode == 0 and r1.returncode == 0
      and b'"/jobs/{job_id}/media"' not in r0.stdout and b"DzScrub" not in r1.stdout and b"function Jh(" in r1.stdout)

print("[S] la cadence lue dans le fichier")
try:
    from app.services import media_info as MI                       # noqa: E402
except ImportError as e:
    MI = None
    check("S0 le module existe", False, str(e))


def sonde(stream, fmt=None):
    return json.dumps({"streams": [stream], "format": fmt or {}})


if MI:
    a = MI.lire_sonde(sonde({"avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001", "nb_frames": "150", "duration": "5.005"}))
    check("S1 30000/1001 -> 29.97 i/s, nb_frames du flux, source fichier", a == {"fps": 29.97, "frames": 150, "duration_s": 5.005,
          "source": "fichier", "raison": None}, str(a))
    b = MI.lire_sonde(sonde({"avg_frame_rate": "24/1", "r_frame_rate": "60/1", "duration": "2.0"}))
    check("S2 avg d'abord (r_frame_rate = pas de base, 60/1 ou 90000/1 sur un flux variable) ; sans nb_frames : duree x ips",
          b["fps"] == 24.0 and b["frames"] == 48, str(b))
    c = MI.lire_sonde(sonde({"avg_frame_rate": "0/0", "r_frame_rate": "25/1"}, {"duration": "4"}))
    check("S3 avg absent (0/0) -> r_frame_rate ; duree du conteneur a defaut du flux", c["fps"] == 25.0 and c["frames"] == 100
          and c["duration_s"] == 4.0, str(c))
    d = [MI.lire_sonde(t) for t in ("pas du json", sonde({"avg_frame_rate": "0/0", "r_frame_rate": "0/0"}), sonde({"avg_frame_rate": "500/1"}),
                                     json.dumps({"streams": []}))]
    check("S4 illisible, cadence absente, hors bornes, aucun flux : 30 i/s et une RAISON (source defaut)",
          all(x["fps"] == 30.0 and x["source"] == "defaut" and isinstance(x["raison"], str) and len(x["raison"]) > 8 and x["frames"] is None
              for x in d), str(d))
    e = MI.lire_sonde(sonde({"avg_frame_rate": "24/1"}))
    check("S5 cadence sans duree ni nb_frames : frames inconnu (None), pas zero", e["fps"] == 24.0 and e["frames"] is None, str(e))

CLIP = _tmp / "outputs" / "clip24.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=s=64x112:r=24:d=2", "-pix_fmt", "yuv420p", str(CLIP)],
               capture_output=True, check=True)
if MI:
    g = MI.cadence(CLIP)
    check("S6 un VRAI clip 24 i/s de 2 s : 24 i/s, 48 images, lues dans le fichier", g["fps"] == 24.0 and g["frames"] == 48
          and g["source"] == "fichier" and abs((g["duration_s"] or 0) - 2.0) < 0.05, str(g))
    h = MI.cadence(_tmp / "absent.mp4")
    check("S7 fichier introuvable : defaut, raison dite", h["source"] == "defaut" and "introuvable" in h["raison"], str(h))
    (_tmp / "pas_video.mp4").write_bytes(b"ceci n'est pas une video")
    i = MI.cadence(_tmp / "pas_video.mp4")
    check("S8 fichier qui n'est pas une video : defaut, la raison dit le REFUS de ffprobe (pas d'exception)", i["source"] == "defaut" and i["fps"] == 30.0
          and "refusé" in (i["raison"] or ""), str(i))

print("\n[R] la route")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def job(jid, chemin):
    cx = sqlite3.connect(str(_DB))
    cols = cx.execute("PRAGMA table_info(jobs)").fetchall()
    val = {c[1]: (0 if "INT" in (c[2] or "").upper() else "2026-10-02 12:00:00.000000" if "DATE" in (c[2] or "").upper() else "")
           for c in cols if c[3] and c[4] is None}
    val.update({"id": jid, "status": "done", "final_video_path": chemin})
    cx.execute(f"INSERT INTO jobs ({','.join(val)}) VALUES ({','.join('?' * len(val))})", list(val.values()))
    cx.commit(); cx.close()


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    j1, j2, j3 = (str(uuid.uuid4()) for _ in range(3))
    job(j1, str(CLIP)); job(j2, str(_tmp / "disparu.mp4")); job(j3, None)
    r = c.get(f"/api/jobs/{j1}/media")
    d = r.json() if r.status_code == 200 else {}
    check("R1 200 : la cadence du rendu, lue dans son fichier", r.status_code == 200 and d.get("fps") == 24.0 and d.get("frames") == 48
          and d.get("source") == "fichier", f"{r.status_code} {r.text[:200]}")
    rs = [c.get(f"/api/jobs/{x}/media").status_code for x in (j2, j3, str(uuid.uuid4()))]
    check("R2 fichier disparu, rendu sans video, job inconnu : 404 (comme /video)", rs == [404, 404, 404], str(rs))
src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("R3 la route n'est pas payante (absente du recensement)", "/media" not in src)

print("\n[B] le lecteur, dans le bundle livre")
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
VIEUX = ('r.jsx("video",{src:D.jobVideoUrl(n.id),controls:!0,autoPlay:!0,'
         'style:{width:"100%",borderRadius:8,background:"#000",border:"1px solid var(--stroke-strong)"}})')
jh = BUN.find("function Jh({onClose:e,graph:t,lastJob:n}){")
k = BUN.find("r.jsx(DzScrub,{jobId:n.id})")
check("B1 le lecteur d'origine du tiroir est REMPLACE (pas double), dans Jh ; les deux autres lecteurs autoPlay restent",
      BUN.count("r.jsx(DzScrub,{jobId:n.id})") == 1 and VIEUX not in BUN and 0 <= jh < k < jh + 4500
      and BUN.count("autoPlay:!0") == 3 and BUN.count("function DzScrub(") == 1)


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k:i + 1]
        i += 1
    return ""


COUCHE = "\n".join(fonction(n) for n in ("dzScrubIndex", "dzScrubTemps", "dzScrubSaisie", "DzScrub"))
HARNAIS = r"""
var H=[],hi=0,EFF=[],NET=[],MEDIA=null,KEYS=[],RETIRES=0;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},
  useEffect:function(f){var i=hi++;if(!(i in H)){H[i]=1;EFF.push(f)}}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};var K="K";var D={jobVideoUrl:function(id){return "/api/jobs/"+id+"/video"}};
var window={addEventListener:function(t,f){if(t==="keydown")KEYS.push(f)},removeEventListener:function(t,f){KEYS=KEYS.filter(function(g){return g!==f});RETIRES++}};
globalThis.fetch=async function(u){NET.push(u);if(MEDIA==="panne")throw new Error("hors ligne");
  return {ok:MEDIA.ok!==false,status:MEDIA.status||200,json:async function(){return MEDIA}}};
function trouver(n,f){if(!n||typeof n!=="object")return null;if(f(n))return n;var c=n.p&&n.p.children;
  if(Array.isArray(c)){for(var i=0;i<c.length;i++){var z=trouver(c[i],f);if(z)return z}}else if(c&&typeof c==="object")return trouver(c,f);return null}
var NETTOIE=[];
function rendre(){hi=0;var T=DzScrub({jobId:"j 1"});EFF.splice(0).forEach(function(f){var z=f();if(typeof z==="function")NETTOIE.push(z)});return T}
function video(dur,rvfc){return {currentTime:0,duration:dur,paused:false,nrv:0,pause:function(){this.paused=true},
  requestVideoFrameCallback:rvfc?function(cb){var v=this;v.nrv++;cb(0,{mediaTime:v.currentTime+0.0001})}:undefined}}
async function attendre(){for(var i=0;i<10;i++)await new Promise(function(r){setImmediate(r)})}
function texte(T){return trouver(T,function(n){return n.t==="span"&&n.p.className==="mono"}).p.children}
function aide(T){var d=T.p.children[2];return d.p.children}
function cle(k,cible,mod){var ev={key:k,target:cible||{tagName:"BODY"},defaultPrevented:false,preventDefault:function(){this.defaultPrevented=true}};
  if(mod)ev[mod]=true;KEYS.forEach(function(f){f(ev)});return ev.defaultPrevented}
"""


def node(corps):
    f = _tmp / f"s{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


R = node("""
R.idx=[dzScrubIndex(0.083333,24,72),dzScrubIndex(0.708333,24,72),dzScrubIndex(0,24,48),dzScrubIndex(0.0416,24,48),dzScrubIndex(1/24,24,48),dzScrubIndex(99,24,48),dzScrubIndex(-1,24,48),dzScrubIndex(0.5,30,0)];
R.tps=[dzScrubTemps(0,24),dzScrubTemps(10,25),dzScrubTemps(-3,24)];
R.saisie=[dzScrubSaisie({tagName:"INPUT",type:"text"}),dzScrubSaisie({tagName:"INPUT"}),dzScrubSaisie({tagName:"INPUT",type:"range"}),
  dzScrubSaisie({tagName:"TEXTAREA"}),dzScrubSaisie({tagName:"SELECT"}),dzScrubSaisie({tagName:"DIV",isContentEditable:true}),dzScrubSaisie({tagName:"BUTTON"}),dzScrubSaisie(null)];
MEDIA={fps:24,frames:48,duration_s:2,source:"fichier"};
var T=rendre();var V=video(2,true);trouver(T,function(n){return n.t==="video"}).p.ref.current=V;
R.net=NET.slice();R.vid=trouver(T,function(n){return n.t==="video"}).p;R.vid={src:R.vid.src,auto:R.vid.autoPlay,ctl:R.vid.controls};
R.avant=aide(T);await attendre();T=rendre();R.c0=texte(T);R.aide=aide(T);
R.pt=cle(".");T=rendre();R.c1=texte(T);R.t1=V.currentTime;R.pause1=V.paused;R.nrv=V.nrv;
cle(",");cle(",");cle(",");T=rendre();R.c2=texte(T);R.t2=V.currentTime;
var rg=trouver(T,function(n){return n.t==="input"});R.rg={max:rg.p.max,step:rg.p.step,title:rg.p.title};V.paused=false;rg.p.onChange({target:{value:"47"}});T=rendre();
R.c3=texte(T);R.t3=V.currentTime;R.pause3=V.paused;cle(".");T=rendre();R.c4=texte(T);
R.saisieTexte=cle(".",{tagName:"INPUT",type:"text"});R.surReglette=cle(",",{tagName:"INPUT",type:"range"});T=rendre();R.c5=texte(T);
R.ctrl=cle(".",null,"ctrlKey");
var bs=[];(function f(n){if(!n||typeof n!=="object")return;if(n.t==="K")bs.push({title:n.p.title,ch:n.p.children});var c=n.p&&n.p.children;if(Array.isArray(c))c.forEach(f);else f(c)})(T);R.btn=bs;
var prec=bs[0];T.p.children[1].p.children[0].p.onClick();T=rendre();R.c6=texte(T);
R.nett=NETTOIE.length;NETTOIE.forEach(function(f){f()});R.keys=KEYS.length;R.retires=RETIRES;
""")
check("B2 sous node : le lecteur s'execute (aucune exception)", R is not None)
if R:
    check("B3 image = plancher(t x ips + 1/1000), bornee [0, n-1] — le DEBUT d'image que rend rVFC, arrondi a la microseconde (2/24 -> 0.083333), reste l'image 2 ; une image est visee en son MILIEU ((k + ½) / ips)",
          R["idx"] == [2, 17, 0, 0, 1, 47, 0, 15] and [round(t, 6) for t in R["tps"]] == [round(0.5 / 24, 6), 0.42, round(0.5 / 24, 6)], f"{R['idx']} {R['tps']}")
    check("B4 « saisie » = champ texte, zone de texte, liste, contentEditable — PAS la reglette (sinon elle couperait ses propres touches)",
          R["saisie"] == [True, True, False, True, True, True, False, False], str(R["saisie"]))
    check("B5 la cadence est DEMANDEE au serveur pour CE rendu (id encode) ; le lecteur garde autoPlay et controls sur la video du job",
          R["net"] == ["/api/jobs/j%201/media"] and R["vid"] == {"src": "/api/jobs/j 1/video", "auto": True, "ctl": True}, f"{R['net']} {R['vid']}")
    check("B6 avant la reponse : « cadence… » ; apres : « f 1 / 48 » et « 24 i/s (lue dans le fichier) »",
          "cadence…" in R["avant"] and R["c0"] == "f 1 / 48" and "24 i/s (lue dans le fichier)" in R["aide"], f"{R['avant']} {R['c0']} {R['aide']}")
    check("B7 « . » : une image en avant, PAUSE, temps au milieu de l'image 2 ; l'evenement est consomme ; la precision (rVFC) est demandee",
          R["nrv"] == 1 and R["pt"] is True and R["c1"] == "f 2 / 48" and R["pause1"] is True and abs(R["t1"] - 1.5 / 24) < 1e-6, f"{R['c1']} {R['t1']} {R['pause1']}")
    check("B8 « , » trois fois depuis l'image 2 : bute sur l'image 1 (jamais negative)", R["c2"] == "f 1 / 48" and abs(R["t2"] - 0.5 / 24) < 1e-6, f"{R['c2']} {R['t2']}")
    check("B9 la reglette compte en IMAGES (0..47, pas 1) avec un title ; la poser met en PAUSE sur l'image visee",
          R["rg"]["max"] == 47 and R["rg"]["step"] == 1 and "← →" in (R["rg"]["title"] or "") and R["c3"] == "f 48 / 48" and R["pause3"] is True
          and R["t3"] < 2.0, str(R["rg"]) + f" {R['c3']} {R['t3']}")
    check("B10 « . » sur la DERNIERE image : reste sur la derniere, le temps reste sous la duree", R["c4"] == "f 48 / 48", R["c4"])
    check("B11 en saisie, « . » est laisse au champ ; sur la reglette focalisee, « , » recule quand meme ; Ctrl+. n'est pas pris",
          R["saisieTexte"] is False and R["surReglette"] is True and R["c5"] == "f 47 / 48" and R["ctrl"] is False, f"{R['saisieTexte']} {R['surReglette']} {R['c5']} {R['ctrl']}")
    check("B12 ‹ et › : boutons du Studio AVEC title (la touche dite) ; ‹ recule d'une image",
          len(R["btn"]) == 2 and R["btn"][0]["ch"] == "‹" and "« , »" in (R["btn"][0]["title"] or "") and R["btn"][1]["ch"] == "›"
          and "« . »" in (R["btn"][1]["title"] or "") and R["c6"] == "f 46 / 48", f"{R['btn']} {R['c6']}")
    check("B13 a la fermeture du tiroir, l'ecoute du clavier est RETIREE", R["nett"] >= 2 and R["keys"] == 0 and R["retires"] == 1, f"{R['nett']} {R['keys']} {R['retires']}")

R2 = node("""
MEDIA={ok:false,status:404,detail:"x"};var T=rendre();var V=video(2,false);trouver(T,function(n){return n.t==="video"}).p.ref.current=V;
await attendre();trouver(T,function(n){return n.t==="video"}).p.onLoadedMetadata({target:{duration:2,currentTime:0}});T=rendre();R.a=aide(T);R.c=texte(T);
cle(".");T=rendre();R.c1=texte(T);R.t1=V.currentTime;
H=[];hi=0;NET=[];MEDIA="panne";T=rendre();await attendre();T=rendre();R.p=aide(T);
""")
check("B14 cadence non lue (404, serveur injoignable) : 30 i/s et la RAISON dites ; images comptees sur la duree (2 s -> 60)",
      R2 is not None and "30 i/s (cadence non lue : HTTP 404)" in R2["a"] and R2["c"] == "f 1 / 60" and R2["c1"] == "f 2 / 60"
      and abs(R2["t1"] - 1.5 / 30) < 1e-6 and "30 i/s (cadence non lue : hors ligne)" in R2["p"], str(R2))
R3 = node("""
MEDIA={fps:24,frames:48,source:"fichier"};var T=rendre();var V=video(NaN,false);trouver(T,function(n){return n.t==="video"}).p.ref.current=V;
await attendre();T=rendre();for(var i=0;i<60;i++){cle(".");T=rendre()}R.t=V.currentTime;R.c=texte(T);
""")
check("B16 durees pas encore connues (metadonnees en route) : 60 « . » butent sur l'image 48, sans viser au-dela de la fin",
      R3 is not None and abs(R3["t"] - 47.5 / 24) < 1e-6 and R3["c"] == "f 48 / 48", str(R3))
check("B15 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "confirm(" not in COUCHE and "alert(" not in COUCHE and BUN.count("DzTracks") == 181 and BUN.count("__dzCoutBlanc") == 7
      and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
