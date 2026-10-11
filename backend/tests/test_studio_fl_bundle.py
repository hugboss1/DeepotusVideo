"""t185 / G3 (plan « Génération IA enrichie ») — le port `end` du nœud Seedance est compilé, dans le Studio et dans
Quick › Composition, et le sélecteur du nœud le sait.

  [0] bundle : le compilateur du Studio (Mh) lit l'entrée `end` pour le tir seul (POST /generate), l'Enchaînement
      (créneaux du gabarit) et la moitié animation de la composition UGC — le code RÉEL extrait du bundle, joué sous
      node sur un graphe : image_filename_end = le fichier branché sur `end`, absent du JSON sans `end` ;
  [1] bundle : dzCompose (Composition spatiale) envoie image_filename_end dans le créneau du Seedance (joué sous node,
      faux fetch et faux D.renderLayoutTemplate) ;
  [2] bundle : le sélecteur DzVideoModelSel (code réel sous node) — avec `fin`, les modèles `fl` (nature video_fl)
      d'abord ; un modèle sans image de fin -> bandeau studio.video.fl_absent + action « Veo 3.1 Fast » ; le modèle
      ne change JAMAIS au rendu, seulement au clic ; sans `fin`, rendu d'avant ; le panneau du nœud passe `fin` ;
      Quick › Composition envoie image_filename_end (dzEndOK) ; les paires du maillon encartsia (la SOURCE) sont dans
      le bundle ; clés fr/en au catalogue studio.json ; compteurs figés (useState 731, DzTracks 181), CRLF ;
  [3] backend : /generate/composition, seedance.image_filename_end + veo-3.1-fast-fal -> build_fal_args reçoit
      end_image_url et la soumission part vers l'endpoint FL (first/last_frame_url) — espion sur la couture
      `_soumettre`, aucun réseau ; un créneau Seedance de /layout-templates/{id}/render (dzCompose) idem ;
  [4] backend : même payload en kling-v3-turbo-pro -> 400 « n'accepte pas d'image de fin » AVANT _plafond, zéro
      dépense ; image de fin absente du disque -> 404 avant _plafond.

AUCUN appel réel : `_plafond` est un espion, `_soumettre` lève après capture, `fal_client.*` et tout
`httpx.AsyncClient.post` hors du client de test sont COMPTÉS et refusés.
Run : & $PY tests/test_studio_fl_bundle.py   (depuis backend/)
"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="studiofl_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-key"
os.environ["HEYGEN_API_KEY"] = "test-heygen"
for _k in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY",
           "MESHY_API_KEY"):
    os.environ.pop(_k, None)
Path(TMP, "images").mkdir(parents=True, exist_ok=True)
Path(TMP, "outputs").mkdir(parents=True, exist_ok=True)
ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(RACINE / "scripts"))
BUNDLE = RACINE / "frontend/dist/assets/index-BEOJX8L5.js"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


BUNB = BUNDLE.read_bytes()
BUN = BUNB.decode("utf-8")


def entre(s, a, b, inclure_b=False):
    i = s.find(a)
    j = s.find(b, i + len(a)) if i >= 0 else -1
    return s[i:j + (len(b) if inclure_b else 0)] if 0 <= i < j else ""


def node_json(script):
    """Joue le script sous node (par fichier) ; rend (dernier objet JSON de la sortie, raison)."""
    if not NODE:
        return {}, "node absent du PATH"
    p = os.path.join(TMP, "harnais.js")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script)
    r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-600:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        return json.loads(lignes[-1]), ""
    except Exception as e:  # noqa: BLE001
        return {}, repr(e) + (r.stdout or "")[-300:]


# le code réel, extrait du bundle
WT = entre(BUN, "function Wt(e,t,n){", "function WtAll(")                 # Wt + dzFinImg (posée avant WtAll)
IMGN = entre(BUN, "function dzIsImgNode(", "function dzInImg(")
MH = entre(BUN, "function Mh(e){", "const Zi=")
DZC = entre(BUN, "async function dzCompose(", "function DzOpenGraph(")
SEL = entre(BUN, "function DzVideoModelSel(", "var dzVoMult=")
check("TÉMOIN : Wt, dzIsImgNode, Mh, dzCompose et DzVideoModelSel extraits du bundle",
      all(len(x) > 50 for x in (WT, IMGN, MH, DZC, SEL)), [len(x) for x in (WT, IMGN, MH, DZC, SEL)])

PRELUDE = r"""
var dzT=function(k,v){return v?k+JSON.stringify(v):k};
var dzAvCompile=function(){return null};
var pd=function(){return[1080,1920]};
var dzGraphVoiceover=function(){return null};
var dzRunMaxTake=function(){return void 0};
var dzPinReemploi=function(){return!1};
var dzSSML=function(s){return s};
var dzReach=function(){return!1};
var dzSpatialSlots=function(tpl){return{ports:[{id:"s_main",slot:"main"}],seq:!1}};
var CAPT=[];
var D={postJson:function(u,b){CAPT.push({u:u,b:b});return{ok:!0}},
  renderLayoutTemplate:function(id,slots,v,def,o,g){CAPT.push({tpl:id,slots:slots});return{ok:!0}},
  listHeygenAvatars:function(){return{avatars:[]}},listHeygenVoices:function(){return{voices:[]}}};
var TPL={regions:[{type:"video_slot",slot_name:"main",x:0,y:0,width:1080,height:1920}],canvas:{width:1080,height:1920}};
var fetch=function(){return Promise.resolve({ok:!0,json:function(){return Promise.resolve(TPL)}})};
"""


def graphe(avec_fin, extra_nodes=(), extra_edges=()):
    nodes = [{"id": "R", "type": "Render", "props": {"format": "9:16", "name": "rendu"}},
             {"id": "S", "type": "Seedance", "props": {"model": "veo-3.1-fast-fal", "durationS": 8}},
             {"id": "A", "type": "Image", "props": {"filename": "depart.png"}},
             {"id": "B", "type": "Image", "props": {"filename": "fin.png"}}] + list(extra_nodes)
    edges = [{"from": "A", "to": "S", "toPort": "image"}] + list(extra_edges)
    if avec_fin:
        edges.append({"from": "B", "to": "S", "toPort": "end"})
    return {"nodes": nodes, "edges": edges}


# ── [0] Mh : tir seul, Enchaînement, composition UGC ────────────────────────
print("\n[0] le compilateur du Studio (Mh) lit l'entrée `end`")
CONCAT = ([{"id": "C", "type": "Concatenate", "props": {}},
           {"id": "S2", "type": "Seedance", "props": {"model": "seedance-2.5"}}],
          [{"from": "S", "to": "C", "toPort": "a"}, {"from": "S2", "to": "C", "toPort": "b"},
           {"from": "A", "to": "S2", "toPort": "image"}])
UGC = ([{"id": "U", "type": "Upload", "props": {"jobId": "job-ugc", "durationS": 8}}], [])
H0 = PRELUDE + WT + IMGN + MH + r"""
var G=JSON.parse(require("fs").readFileSync(process.argv[2],"utf8")),out={};
async function un(nom,g){CAPT=[];var c=Mh(g);if(!c.ok){out[nom]={err:c.error};return}await c.run();out[nom]=CAPT[0]}
(async function(){
  await un("solo_fin",G.solo_fin);await un("solo_sans",G.solo_sans);
  await un("concat_fin",G.concat_fin);await un("ugc_fin",G.ugc_fin);
  console.log(JSON.stringify(out));
})();
"""
GRAPHES = {"solo_fin": graphe(True), "solo_sans": graphe(False), "concat_fin": graphe(True, *CONCAT),
           "ugc_fin": graphe(True, *UGC)}
p = os.path.join(TMP, "graphes.json")
d0, why = {}, "node absent"
if NODE and MH:
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(GRAPHES))
    pathlib.Path(TMP, "h0.js").write_text(H0, encoding="utf-8")
    r = subprocess.run([NODE, str(Path(TMP, "h0.js")), p], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    try:
        d0, why = json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception as e:  # noqa: BLE001
        why = f"{e!r} {r.stderr[-500:]}"
solo = (d0.get("solo_fin") or {})
check("0a tir seul : POST /generate porte image_filename_end = le fichier branché sur `end`",
      solo.get("u") == "/generate" and (solo.get("b") or {}).get("image_filename_end") == "fin.png"
      and (solo.get("b") or {}).get("image_filename") == "depart.png", (d0, why))
sans = ((d0.get("solo_sans") or {}).get("b") or {})
check("0b sans `end` branché : la clé est ABSENTE du JSON (payload d'avant)",
      bool(sans) and "image_filename_end" not in json.loads(json.dumps(sans)) and sans.get("image_filename") == "depart.png",
      sans)
cc = ((d0.get("concat_fin") or {}).get("slots") or {})
check("0c Enchaînement : le créneau du Seedance avec `end` porte la fin, l'autre non",
      (cc.get("clip0") or {}).get("seedance", {}).get("image_filename_end") == "fin.png"
      and "image_filename_end" not in (cc.get("clip1") or {}).get("seedance", {"image_filename_end": 1}), cc)
ug = ((d0.get("ugc_fin") or {}).get("slots") or {})
check("0d composition UGC : la moitié animation porte la fin",
      (ug.get("anim") or {}).get("seedance", {}).get("image_filename_end") == "fin.png", ug)

# ── [1] dzCompose ───────────────────────────────────────────────────────────
print("\n[1] dzCompose (Composition spatiale) envoie image_filename_end")
H1 = PRELUDE + WT + IMGN + DZC + r"""
var G=JSON.parse(require("fs").readFileSync(process.argv[2],"utf8")),out={};
async function un(nom,g){CAPT=[];var t=g.nodes.find(function(n){return n.type==="Render"}),
  l=g.nodes.find(function(n){return n.type==="SpatialCompose"});var res=await dzCompose(g,t,l,"9:16","titre");
  out[nom]=CAPT[0]||{res:res}}
(async function(){await un("fin",G.fin);await un("sans",G.sans);console.log(JSON.stringify(out))})();
"""
SC = ([{"id": "L", "type": "SpatialCompose", "props": {"templateId": "tpl_x"}}],
      [{"from": "S", "to": "L", "toPort": "s_main"}])
d1, why1 = {}, "node absent"
if NODE and DZC:
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"fin": graphe(True, *SC), "sans": graphe(False, *SC)}))
    pathlib.Path(TMP, "h1.js").write_text(H1, encoding="utf-8")
    r = subprocess.run([NODE, str(Path(TMP, "h1.js")), p], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    try:
        d1, why1 = json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception as e:  # noqa: BLE001
        why1 = f"{e!r} {r.stderr[-500:]}"
s1 = (((d1.get("fin") or {}).get("slots") or {}).get("main") or {})
check("1a le créneau du Seedance porte image_filename_end = fin.png (et son modèle Veo 3.1 Fast)",
      s1.get("source_kind") == "seedance" and s1.get("seedance", {}).get("image_filename_end") == "fin.png"
      and s1.get("seedance", {}).get("video_model") == "veo-3.1-fast-fal", (d1, why1))
s1b = (((d1.get("sans") or {}).get("slots") or {}).get("main") or {})
check("1b sans `end` : pas d'image de fin dans le créneau",
      s1b.get("source_kind") == "seedance" and "image_filename_end" not in s1b.get("seedance", {}), s1b)
check("1c la source : dzCompose lit `end` par dzFinImg (forme de l'entrée `image`)",
      "image_filename:img.props.filename,image_filename_end:dzFinImg(e,g.id)," in DZC
      and 'function dzFinImg(e,id){var f=Wt(e,id,"end");' in WT, DZC[:80])

# ── [2] le sélecteur, le panneau, Quick, la source ──────────────────────────
print("\n[2] le sélecteur DzVideoModelSel : video_fl d'abord, bandeau, jamais de bascule silencieuse")
MODELS = [{"id": "seedance-2.5", "label": "Seedance 2.5", "available": True, "fl": False, "end_image": False},
          {"id": "kling-v3-turbo-pro", "label": "Kling v3 Turbo", "available": True, "fl": False, "end_image": False},
          {"id": "veo-3.1-fast-fal", "label": "Veo 3.1 Fast (fal)", "available": True, "fl": True, "end_image": True},
          {"id": "veo-3.1-fal", "label": "Veo 3.1 (fal)", "available": False, "fl": True, "end_image": True}]
H2 = r"""
var MM=null;
var dzT=function(k,v){return v?k+JSON.stringify(v):k};
var dzPrixUsd=function(){return""};
const x={useState:function(){return[MM,function(){}]},useEffect:function(){}};
const r={jsx:function(t,p){return{t:t,p:p}},jsxs:function(t,p){return{t:t,p:p}}};
const re="SELECT";
""" + SEL + r"""
var M=JSON.parse(process.argv[2]),CH=[];
function oc(v){CH.push(v)}
function trouve(n,f){if(!n||typeof n!=="object")return null;if(f(n))return n;var c=n.p&&n.p.children;
  if(Array.isArray(c)){for(var i=0;i<c.length;i++){var t=trouve(c[i],f);if(t)return t}return null}return trouve(c,f)}
function sel(o){return trouve(o,function(n){return n.t==="SELECT"})}
function texte(o){var s=[];(function w(n){if(n==null)return;if(typeof n==="string"){s.push(n);return}
  if(Array.isArray(n)){n.forEach(w);return}if(n.p)w(n.p.children)})(o);return s.join("|")}
MM={models:M,default:"seedance-2.5"};
var sans=DzVideoModelSel({value:"kling-v3-turbo-pro",onChange:oc});
var kl=DzVideoModelSel({value:"kling-v3-turbo-pro",onChange:oc,fin:"fin.png"});
var dflt=DzVideoModelSel({value:"",onChange:oc,fin:"fin.png"});
var veo=DzVideoModelSel({value:"veo-3.1-fast-fal",onChange:oc,fin:"fin.png"});
var rendu=CH.slice();
var bt=trouve(kl,function(n){return n.t==="button"});
if(bt)bt.p.onClick();
console.log(JSON.stringify({
  sans_ordre:sel(sans).p.options.map(function(o){return o.value}),sans_t:sans.p["data-dzvmfin"]||null,sans_txt:texte(sans),
  kl_ordre:sel(kl).p.options.map(function(o){return o.value}),kl_fin:kl.p["data-dzvmfin"],kl_txt:texte(kl),
  kl_val:sel(kl).p.value,dflt_fin:dflt.p["data-dzvmfin"],veo_fin:veo.p["data-dzvmfin"],veo_txt:texte(veo),
  veo_bt:!!trouve(veo,function(n){return n.t==="button"}),bt:bt?bt.p.children:null,rendu:rendu,clic:CH.slice(rendu.length)}));
"""
d2, why2 = {}, "node absent"
if NODE and SEL:
    pathlib.Path(TMP, "h2.js").write_text(H2, encoding="utf-8")
    r = subprocess.run([NODE, str(Path(TMP, "h2.js")), json.dumps(MODELS)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    try:
        d2, why2 = json.loads(r.stdout.strip().splitlines()[-1]), ""
    except Exception as e:  # noqa: BLE001
        why2 = f"{e!r} {r.stderr[-500:]}"
check("2a sans `fin` : ordre du serveur, aucun bandeau (rendu d'avant pour Quick, Épisodes, Réglages)",
      d2.get("sans_ordre") == ["", "seedance-2.5", "kling-v3-turbo-pro", "veo-3.1-fast-fal", "veo-3.1-fal"]
      and d2.get("sans_t") is None and "studio.video" not in d2.get("sans_txt", "x"), (d2, why2))
check("2b avec `fin` : les modèles video_fl (fl) EN TÊTE, puis les autres",
      d2.get("kl_ordre") == ["", "veo-3.1-fast-fal", "veo-3.1-fal", "seedance-2.5", "kling-v3-turbo-pro"], d2.get("kl_ordre"))
check("2c modèle courant sans image de fin : bandeau studio.video.fl_absent + action studio.video.fl",
      d2.get("kl_fin") == "non" and "studio.video.fl_absent" in d2.get("kl_txt", "") and d2.get("bt") == "studio.video.fl",
      d2.get("kl_txt"))
check("2d JAMAIS de bascule silencieuse : le rendu n'appelle pas onChange, la valeur reste Kling",
      d2.get("rendu") == [] and d2.get("kl_val") == "kling-v3-turbo-pro", d2.get("rendu"))
check("2e le clic sur l'action choisit veo-3.1-fast-fal (une fois)", d2.get("clic") == ["veo-3.1-fast-fal"], d2.get("clic"))
check("2f le défaut du serveur (seedance-2.5, sans fin) est signalé aussi",
      d2.get("dflt_fin") == "non", d2.get("dflt_fin"))
check("2g Veo 3.1 Fast choisi : pas de bandeau, l'image de fin du créneau rappelée",
      d2.get("veo_fin") == "oui" and not d2.get("veo_bt") and "studio.compose.fin : fin.png" in d2.get("veo_txt", ""),
      d2.get("veo_txt"))
check("2h le panneau du nœud Seedance passe `fin` (dzFinImg du graphe) au sélecteur",
      BUN.count('r.jsx(DzVideoModelSel,{value:n.model,onChange:i=>o("model",i),fin:g?dzFinImg(g,e.id):void 0})') == 1)
QCOMP = entre(BUN, 'else if(o==="comp"){', 'D.postJson("/generate/composition"', inclure_b=False)
QPAY = entre(BUN, 'D.postJson("/generate/composition",{', 'layout:We,')
check("2i Quick › Composition : le côté Seedance envoie l'image de fin du Quick (dzEndOK), comme l'onglet Seedance",
      bool(QCOMP) and "image_filename:w,image_filename_end:(dzEndOK()?g:\"\")||null," in QPAY, QPAY[:200])
import patch_bundle_encartsia as ENC                                         # noqa: E402
G3 = ENC.PAIRES[-9:]
check("2j les neuf paires G3 du maillon encartsia (la SOURCE) sont dans le bundle, une fois, ancres consommées",
      len(ENC.PAIRES) == 17 and all(BUN.count(b) == 1 and BUN.count(a) == (1 if a in b else 0) for a, b in G3)
      and G3[0][1].startswith("function dzFinImg("), [(BUN.count(b), BUN.count(a)) for a, b in G3])
DICO = json.loads((RACINE / "frontend/shared/i18n/studio.json").read_text("utf-8"))
CLES = ("studio.video.fl", "studio.video.fl_absent", "studio.compose.fin")
check("2k clés fr/en au catalogue studio.json et appelées par le bundle",
      all(DICO.get(c, {}).get("fr") and DICO.get(c, {}).get("en") and f'dzT("{c}")' in BUN for c in CLES),
      {c: DICO.get(c) for c in CLES})
check("2l compteurs figés : x.useState( 731, DzTracks 181 ; bundle tout en CRLF",
      BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181
      and BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\n") == BUNB.count(b"\r\n"),
      (BUN.count("x.useState("), BUN.count("DzTracks")))
check("2m le registre déclare toujours le port `end` du Seedance",
      '{id:"image",type:"image"},{id:"end",type:"image"},{id:"prompt",type:"text"}' in BUN)

# ── [3]-[4] backend ─────────────────────────────────────────────────────────
import fal_client                                                # noqa: E402
import httpx                                                     # noqa: E402
from fastapi import HTTPException                                # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402
from PIL import Image                                            # noqa: E402

from app.config import settings                                  # noqa: E402
from app.main import app                                         # noqa: E402
from app.services.storage import init_db                         # noqa: E402
from app.api import routes as R                                  # noqa: E402
from app.services import fal_service as F                        # noqa: E402

RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async", "upload_file_async", "upload_async", "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))
_vrai_post = httpx.AsyncClient.post


async def _post_garde(self, url, *a, **k):
    if str(getattr(self, "base_url", "")).startswith("http://t"):
        return await _vrai_post(self, url, *a, **k)
    RESEAU["n"] += 1
    RESEAU["noms"].append(f"httpx.post {url}")
    raise RuntimeError(f"GARDE RESEAU : httpx.post {url}")

httpx.AsyncClient.post = _post_garde

PLAF, ARGS, SOUMIS = [], [], []
MODE = {"plafond": "passe"}


async def _plafond_espion(ops, categorie="", *a, **k):
    PLAF.append((categorie, ops))
    if MODE["plafond"] != "passe":
        raise HTTPException(402, "ESPION _plafond : arrêt du banc")

R._plafond = _plafond_espion
_vrai_bfa = F.build_fal_args


def _bfa_espion(model_id, **kw):
    ARGS.append({"model_id": model_id, **kw})
    return _vrai_bfa(model_id, **kw)

F.build_fal_args = _bfa_espion


async def _soumettre_espion(endpoint, arguments):
    SOUMIS.append((endpoint, dict(arguments)))
    raise RuntimeError("ESPION _soumettre : aucune soumission dans un banc")

F.FalSeedanceClient._soumettre = staticmethod(_soumettre_espion)


async def _upload_espion(image_path):
    return "https://fal.test/" + Path(image_path).name

R.pipeline.fal.upload_image = _upload_espion


async def _heygen_bouchon(*a, **k):
    raise RuntimeError("BOUCHON run_heygen : le côté HeyGen n'est pas le sujet")

R.pipeline.run_heygen = _heygen_bouchon
SRC, FIN = "depart.png", "fin.png"
Image.new("RGB", (64, 64), (10, 20, 30)).save(settings.images_path / SRC)
Image.new("RGB", (64, 64), (90, 20, 30)).save(settings.images_path / FIN)
asyncio.run(init_db())


async def _req(path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.post("/api" + path, json=body)


def call(path, body):
    rr = asyncio.run(_req(path, body))
    try:
        return rr.status_code, rr.json()
    except Exception:  # noqa: BLE001
        return rr.status_code, {"_texte": rr.text}


def n_depenses():
    con = sqlite3.connect(TMP + "/t.db")
    try:
        return con.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
    finally:
        con.close()


def composition(model, fin=FIN):
    sd = {"image_filename": SRC, "custom_prompt": "un chat", "video_model": model, "duration_s": 8,
          "aspect_ratio": "9:16", "voiceover_enabled": False}
    if fin:
        sd["image_filename_end"] = fin
    return {"seedance": sd, "heygen": {"avatar_id": "av", "voice_id": "vo", "script": "Bonjour."},
            "layout": "sequential"}


print("\n[3] backend : la fin traverse /generate/composition et le créneau d'un gabarit jusqu'à build_fal_args")
EP_FL = F.VIDEO_MODELS["veo-3.1-fast-fal"]["endpoint_fl"]
PLAF.clear(); ARGS.clear(); SOUMIS.clear()
r0 = RESEAU["n"]
st, js = call("/generate/composition", composition("veo-3.1-fast-fal"))
check("3a /generate/composition Veo 3.1 Fast fal + fin : acceptée (200), le plafond consulté une fois",
      st == 200 and len(PLAF) == 1, f"{st} {js} {PLAF}")
a3 = ARGS[-1] if ARGS else {}
check("3b build_fal_args reçoit end_image_url (l'image de fin téléversée) pour veo-3.1-fast-fal",
      a3.get("model_id") == "veo-3.1-fast-fal" and a3.get("end_image_url") == "https://fal.test/" + FIN
      and a3.get("image_url") == "https://fal.test/" + SRC, ARGS)
e3, g3 = SOUMIS[-1] if SOUMIS else ("", {})
check("3c la soumission (couture _soumettre) part vers l'endpoint FL avec first/last_frame_url",
      e3 == EP_FL and g3.get("first_frame_url") == "https://fal.test/" + SRC
      and g3.get("last_frame_url") == "https://fal.test/" + FIN and "image_url" not in g3, SOUMIS)
check("3d aucun appel réseau", RESEAU["n"] == r0, RESEAU)
PLAF.clear(); ARGS.clear(); SOUMIS.clear()
sd = composition("veo-3.1-fast-fal")["seedance"]
# le gabarit EN LIGNE d'un seul créneau vidéo, comme celui qu'envoie dzCompose quand il modifie le gabarit
TPL = {"id": "tpl_g3", "name": "G3", "render_mode": "sequential",
       "canvas": {"width": 1080, "height": 1920, "fps": 30, "background_color": "#02060d"},
       "regions": [{"id": "r0", "type": "video_slot", "x": 0, "y": 0, "width": 1080, "height": 1920,
                    "slot_name": "main", "length_s": 0, "length_mode": "source"}]}
st, js = call("/layout-templates/tpl_g3/render",
              {"template_id": "tpl_g3", "template": TPL,
               "slot_values": {"main": {"source_kind": "seedance", "seedance": sd}}})
e3b, g3b = SOUMIS[-1] if SOUMIS else ("", {})
check("3e un créneau Seedance de gabarit (dzCompose) avec fin : build_fal_args reçoit end_image_url, endpoint FL",
      st == 200 and any(a.get("end_image_url") == "https://fal.test/" + FIN for a in ARGS)
      and e3b == EP_FL and g3b.get("last_frame_url") == "https://fal.test/" + FIN, f"{st} {js} {ARGS} {SOUMIS}")
check("3f aucun appel réseau (gabarit)", RESEAU["n"] == r0, RESEAU)

print("\n[4] backend : refus AVANT _plafond, zéro dépense")
MODE["plafond"] = "arrete"
PLAF.clear(); SOUMIS.clear()
d0 = n_depenses()
st, js = call("/generate/composition", composition("kling-v3-turbo-pro"))
check("4a kling-v3-turbo-pro + fin -> 400 « n'accepte pas d'image de fin »",
      st == 400 and "n'accepte pas d'image de fin" in str(js), f"{st} {js}")
check("4b ... _plafond jamais appelé, zéro dépense, aucune soumission, aucun réseau",
      PLAF == [] and n_depenses() == d0 and SOUMIS == [] and RESEAU["n"] == r0, f"{PLAF} {d0} {SOUMIS} {RESEAU}")
st, js = call("/generate/composition", composition("veo-3.1-fast-fal", fin="absente.png"))
check("4c image de fin absente du disque -> 404 avant _plafond",
      st == 404 and "absente.png" in str(js) and PLAF == [], f"{st} {js} {PLAF}")
st, js = call("/generate/composition", composition("kling-v3-turbo-pro", fin=None))
check("TÉMOIN : kling-v3-turbo-pro SANS fin atteint _plafond (402 de l'espion)", st == 402 and len(PLAF) == 1,
      f"{st} {js} {PLAF}")

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
