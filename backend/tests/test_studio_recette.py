# -*- coding: utf-8 -*-
"""Plan-studio T9-T10 (tache #71 du suivi, PR A, 03/10/2026) — la RECETTE du Studio : un graphe fige, relancable avec
d'autres images et d'autres textes, PAR la route de rendu existante.
DECISIONS DE L'UTILISATEUR (03/10) : memes gardes que le rendu (epingles verifiees, garde de cout, plafond mensuel,
route recensee) + devis CONFIRME avant chaque lancement (`max_usd` obligatoire) ; capture APRES la preparation des
epingles (un noeud inchange est reemploye gratuitement) ; nom « Recette » ; trous = images + textes ; « Rouvrir dans
Studio » montre les valeurs TIREES.
Ce que le plan faisait faux, et que ce banc garde : son /run sautait TOUTES les gardes ; il passait un `node_slots`
inexistant ; sa capture precedait les epingles (tout repaye) et perdait la voix ; ses trous venaient du client.
Generations SIMULEES (aucun appel paye), composition simulee, data-dir isole, cles de banc.
Temoin positif : la base (3b6a504d) n'a ni le module ni les routes.
Run (depuis backend/) : & $PY tests/test_studio_recette.py"""
import asyncio, json, os, pathlib, shutil, sqlite3, subprocess, sys, tempfile, time, types, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrec_"))
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


BASE = "3b6a504d"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/studio_recette.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni le module ni les routes de recette", r0.returncode != 0 and r1.returncode == 0
      and b"/recette/lancer" not in r1.stdout and b"/recette/devis" not in r1.stdout)

sys.modules["fal_client"] = types.ModuleType("fal_client")
from PIL import Image                                               # noqa: E402
for nom, coul in (("depart.png", (200, 40, 40)), ("autre.png", (40, 200, 40)), ("logo.png", (40, 40, 200))):
    Image.new("RGB", (90, 160), coul).save(_tmp / "images" / nom)

try:
    from app.services import studio_recette as SR                   # noqa: E402
except ImportError as e:
    SR = None
    check("T2 le module existe", False, str(e))

TPL = "tpl_classic_vstack_50_50"
SEED = {"image_filename": "depart.png", "custom_prompt": "Vane entre", "duration_s": 5}
HEY = {"avatar_id": "av1", "voice_id": "vx1", "script": "Bonjour."}
GRAPHE = {"id": "g_ancien", "name": "Matin",
          "nodes": [{"id": "n1", "type": "Image", "props": {"filename": "depart.png"}},
                    {"id": "n2", "type": "Seedance", "props": {}},
                    {"id": "n4", "type": "Prompt", "props": {"value": "Vane entre", "negative": ""}},
                    {"id": "n6", "type": "Text", "props": {"value": "Bonjour."}},
                    {"id": "n3", "type": "HeyGenAvatar", "props": {}}],
          "edges": [{"from": "n1", "to": "n2", "toPort": "image", "fromPort": "out"}]}


def capture(pins=None, **extra):
    pins = pins or {}
    sv = {"animation": {"source_kind": "seedance", "seedance": dict(SEED), "node_id": "n2", "pin": pins.get("animation")},
          "avatar": {"source_kind": "heygen", "heygen": dict(HEY), "node_id": "n3", "pin": pins.get("avatar")}}
    sv.update(extra)
    return {"template_id": TPL, "slot_values": sv, "voice_mode": None, "template": None, "title": "Matin", "voiceover": None,
            "max_usd": 999, "preview": True, "source_graph": {"x": 1}}


print("[N] la recette normalisee, ses trous")
if SR:
    cap = capture(logo={"source_kind": "upload", "upload_filename": "logo.png"},
                  clip={"source_kind": "upload", "upload_filename": "clip.mp4"},
                  titre={"source_kind": "text", "text": "Le titre"},
                  bis={"source_kind": "upload", "upload_filename": "depart.png"})
    rec = SR.normaliser(cap, GRAPHE)
    T = {t["valeur"]: t for t in rec["trous"]}
    check("N1 trous = images + textes de la compilation (image de depart, prompt, script, image posee, texte) ; une VIDEO "
          "posee en slot n'en est pas un", sorted(T) == sorted(["depart.png", "Vane entre", "Bonjour.", "logo.png", "Le titre"])
          and [t["nature"] for t in rec["trous"]].count("image") == 2, str(sorted(T)))
    check("N2 une meme image dans deux slots = UN trou, ses deux chemins", sorted(map(tuple, T["depart.png"]["chemins"]))
          == [("animation", "seedance", "image_filename"), ("bis", "upload_filename")], str(T.get("depart.png")))
    check("N3 le libelle nomme le noeud du graphe qui porte la valeur (registre en miroir) et ce que c'est",
          T["depart.png"]["libelle"] == "Image n1 — image de départ" and T["Bonjour."]["libelle"] == "Text n6 — script de l'avatar"
          and T["Le titre"]["libelle"] == "texte", f"{T['depart.png']['libelle']} | {T['Bonjour.']['libelle']} | {T['Le titre']['libelle']}")
    rq = rec["requete"]
    check("N4 la compilation FIGEE garde slots, epingles et node_id ; perd source_graph, preview et max_usd (fixes au lancement) ; "
          "le graphe garde sans son id", rq["template_id"] == TPL and rq["slot_values"]["animation"]["node_id"] == "n2"
          and "source_graph" not in rq and "preview" not in rq and "max_usd" not in rq and "id" not in rec["graphe"]
          and rec["graphe"]["name"] == "Matin", str(rq)[:300])
    rp = SR.normaliser(capture(pins={"animation": {"job_id": "j1", "empreinte": "e1"}}), GRAPHE)["requete"]
    check("N5 une epingle capturee reste dans la recette (reemploi gratuit si sa requete ne bouge pas)",
          rp["slot_values"]["animation"]["pin"] == {"job_id": "j1", "empreinte": "e1"})
    mauvais = [None, {"slot_values": {"a": {"source_kind": "text", "text": "x"}}}, {"template_id": TPL, "slot_values": {}},
               {"template_id": TPL, "slot_values": {"a": {"source_kind": "sora"}}}]
    rs = []
    for m in mauvais:
        try:
            SR.normaliser(m, GRAPHE); rs.append(None)
        except ValueError as e:
            rs.append(str(e))
    check("N6 une capture qui ne tient pas : refus avec une PHRASE (sans template, sans slot, slot invalide)",
          all(isinstance(x, str) and len(x) > 20 for x in rs), str(rs))

print("\n[A] poser les valeurs")
if SR:
    rec = SR.normaliser(capture(bis={"source_kind": "upload", "upload_filename": "depart.png"}), GRAPHE)
    tid = {t["valeur"]: t["id"] for t in rec["trous"]}
    req, g, ret = SR.appliquer(rec, {tid["depart.png"]: "autre.png", tid["Bonjour."]: "Salut."})
    nd = {n["id"]: n for n in g["nodes"]}
    check("A1 la nouvelle image est posee a TOUS ses chemins ; le script aussi ; les trous non remplis gardent leur valeur",
          req["slot_values"]["animation"]["seedance"]["image_filename"] == "autre.png" and req["slot_values"]["bis"]["upload_filename"] == "autre.png"
          and req["slot_values"]["avatar"]["heygen"]["script"] == "Salut." and req["slot_values"]["animation"]["seedance"]["custom_prompt"] == "Vane entre")
    check("A2 le graphe porte les valeurs TIREES (Image n1, Text n6) ; la recette elle-meme n'est pas touchee",
          nd["n1"]["props"]["filename"] == "autre.png" and nd["n6"]["props"]["value"] == "Salut." and nd["n4"]["props"]["value"] == "Vane entre"
          and rec["requete"]["slot_values"]["animation"]["seedance"]["image_filename"] == "depart.png" and rec["graphe"]["nodes"][0]["props"]["filename"] == "depart.png")
    erreurs = []
    for v in ({"t99": "x"}, {tid["depart.png"]: "../images/autre.png"}, {tid["depart.png"]: "film.mp4"}, {tid["Bonjour."]: "   "},
              {tid["Bonjour."]: "x" * 4901}, {tid["Bonjour."]: 3}, ["x"]):
        try:
            SR.appliquer(rec, v); erreurs.append(None)
        except ValueError as e:
            erreurs.append(str(e))
    check("A3 refus qui NOMMENT : trou inconnu, chemin, pas une image, texte vide, trop long, pas une chaine, pas un objet",
          all(isinstance(x, str) for x in erreurs) and "t99" in erreurs[0] and "Image n1" in erreurs[1] and "4900" in erreurs[4], str(erreurs))

print("\n[R] les routes (generations simulees)")
from fastapi.testclient import TestClient                           # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402
from app.services.storage import JobRecord                          # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
CLIP = _tmp / "clip.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x112:d=1", "-pix_fmt", "yuv420p", str(CLIP)], capture_output=True, check=True)
APPELS, VUS, PLAFONDS = [], [], []


async def _faux_sous_rendu(kind, req):
    from app.services.storage import async_session_factory
    from app.models.schemas import JobStatus
    APPELS.append(kind)
    VUS.append((kind, req.image_filename if kind == "seedance" else req.script))
    jid = str(uuid.uuid4())
    out = _tmp / "outputs" / f"{kind}_{jid[:8]}.mp4"
    shutil.copy(CLIP, out)
    async with async_session_factory() as s:
        s.add(JobRecord(id=jid, status=JobStatus.DONE.value, progress=100, title=kind, image_filename=f"{kind}_{jid[:8]}",
                        provider=kind, final_video_path=str(out), video_path=str(out), completed_at=datetime.utcnow()))
        await s.commit()
    return jid


async def _faux_run(self, req, *a, **k):
    return await _faux_sous_rendu("seedance", req)


async def _faux_heygen(self, req, *a, **k):
    return await _faux_sous_rendu("heygen", req)


def _fausse_compo(template_id, resolved, out_path, template=None):
    shutil.copy(CLIP, out_path)
    return out_path


_plafond_vrai = RT._plafond


async def _plafond_note(op, categorie, ref=None):
    PLAFONDS.append(categorie)
    return await _plafond_vrai(op, categorie, ref)
RT._plafond = _plafond_note
RT._op_voix_off = lambda req: [{"kind": "elevenlabs", "chars": 400}]
RT.pipeline.__class__.run = _faux_run
RT.pipeline.__class__.run_heygen = _faux_heygen
RT.pipeline.template_engine.render = _fausse_compo


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def attendre(c, jid):
    for _ in range(150):
        st = js(c.get(f"/api/jobs/{jid}")).get("status")
        if st in ("done", "failed"):
            return st
        time.sleep(0.1)
    return "timeout"


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    r = c.post("/api/studio-graphs", json={"name": "Matin", "graph": GRAPHE, "recette": capture()})
    d = js(r); gid = d.get("id")
    f = _tmp / "studio_graphs" / f"{gid}.json"
    stock = json.loads(f.read_text(encoding="utf-8")) if gid and f.is_file() else {}
    check("R1 enregistrer avec la capture : la recette est normalisee au magasin, la reponse dit ses trous",
          r.status_code == 200 and d.get("trous") == 3 and stock.get("recette", {}).get("v") == 1, f"{r.status_code} {r.text[:200]}")
    r2 = c.post("/api/studio-graphs", json={"id": gid, "name": "Matin", "graph": GRAPHE})
    stock2 = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    liste = js(c.get("/api/studio-graphs")).get("graphs", [])
    check("R2 « Save » sans recette ne l'EFFACE pas ; la liste dit le nombre de trous (None pour un graphe simple)",
          r2.status_code == 200 and stock2.get("recette") == stock.get("recette") and js(r2).get("trous") == 3
          and [x.get("recette") for x in liste if x["id"] == gid] == [3], str(liste)[:200])
    simple = js(c.post("/api/studio-graphs", json={"name": "Simple", "graph": GRAPHE})).get("id")
    rb = c.post("/api/studio-graphs", json={"name": "X", "graph": GRAPHE, "recette": {"slot_values": {}}})
    check("R3 une capture invalide : 400 avec la phrase ; un graphe simple n'est pas une recette (404 qui le DIT)",
          rb.status_code == 400 and "template" in js(rb).get("detail", "") and c.get(f"/api/studio-graphs/{simple}/recette").status_code == 404
          and "Recette" in js(c.get(f"/api/studio-graphs/{simple}/recette")).get("detail", "")
          and c.get("/api/studio-graphs/inconnu/recette").status_code == 404, rb.text[:200])
    tr = js(c.get(f"/api/studio-graphs/{gid}/recette")).get("trous", [])
    tid = {t["valeur"]: t["id"] for t in tr}
    check("R4 GET : les trous (id, nature, libelle, valeur d'origine), sans les chemins internes",
          sorted(tid) == ["Bonjour.", "Vane entre", "depart.png"] and all(set(t) == {"id", "nature", "libelle", "valeur"} for t in tr), str(tr))
    APPELS.clear(); PLAFONDS.clear()
    dv = js(c.post(f"/api/studio-graphs/{gid}/recette/devis", json={"valeurs": {tid["depart.png"]: "autre.png"}}))
    _vo = RT._op_voix_off; RT._op_voix_off = lambda req: []
    dv0 = js(c.post(f"/api/studio-graphs/{gid}/recette/devis", json={"valeurs": {tid["depart.png"]: "autre.png"}}))
    RT._op_voix_off = _vo
    check("R5 DEVIS : les memes ops que la garde du rendu (Seedance + avatar + voix off, la voix COMPTEE dans le montant), un montant ; rien de genere, aucun plafond touche",
          dv.get("usd", 0) > dv0.get("usd", 0) > 0 and dv.get("generations") == 2 and dv.get("voix") == 1 and dv.get("reemplois") == 0 and dv.get("usd", 0) > 0
          and APPELS == [] and PLAFONDS == [], str(dv))
    rs = [c.post(f"/api/studio-graphs/{gid}/recette/lancer", json=b) for b in
          ({"valeurs": {}}, {"valeurs": {}, "max_usd": "10"}, {"valeurs": {}, "max_usd": True}, {"valeurs": {}, "max_usd": -1})]
    check("R6 lancer SANS devis confirme (max_usd absent, texte, booleen, negatif) : 400, rien ne part",
          [x.status_code for x in rs] == [400] * 4 and "devis" in js(rs[0]).get("detail", "") and APPELS == [], str([x.status_code for x in rs]))
    r7 = c.post(f"/api/studio-graphs/{gid}/recette/lancer", json={"valeurs": {}, "max_usd": 0.0001})
    check("R7 devis confirme plus BAS que le cout : la garde de cout du rendu refuse (402) avant toute generation",
          r7.status_code == 402 and APPELS == [], f"{r7.status_code} {r7.text[:150]}")
    r8 = c.post(f"/api/studio-graphs/{gid}/recette/lancer", json={"valeurs": {tid["depart.png"]: "absente.png"}, "max_usd": 50})
    r8b = c.post(f"/api/studio-graphs/{gid}/recette/devis", json={"valeurs": {"t9": "x"}})
    check("R8 image absente de la Bibliotheque, trou inconnu : 400 qui les nomment", r8.status_code == 400 and "absente.png" in js(r8).get("detail", "")
          and r8b.status_code == 400 and "t9" in js(r8b).get("detail", "") and APPELS == [], f"{r8.text[:150]} {r8b.text[:150]}")
    VUS.clear(); PLAFONDS.clear()
    r9 = c.post(f"/api/studio-graphs/{gid}/recette/lancer",
                json={"valeurs": {tid["depart.png"]: "autre.png", tid["Bonjour."]: "Salut."}, "max_usd": dv.get("usd")})
    j9 = js(r9).get("job_id")
    st9 = attendre(c, j9) if j9 else None
    sg = _tmp / "outputs" / "_graphs" / f"{j9}.json"
    g9 = json.loads(sg.read_text(encoding="utf-8")) if sg.is_file() else {}
    n9 = {n["id"]: n for n in g9.get("nodes", [])}
    jr = js(c.get(f"/api/jobs/{j9}"))
    check("R9 lancer au devis confirme : la route de RENDU tourne (plafond mensuel « studio » passe), avec les valeurs tirees",
          r9.status_code == 200 and st9 == "done" and sorted(VUS) == [("heygen", "Salut."), ("seedance", "autre.png")]
          and PLAFONDS == ["studio"], f"{r9.status_code} {r9.text[:200]} {st9} {VUS} {PLAFONDS}")
    check("R10 « Rouvrir dans Studio » : le graphe garde avec le rendu porte les valeurs TIREES ; titre « Matin — recette »",
          n9.get("n1", {}).get("props", {}).get("filename") == "autre.png" and n9.get("n6", {}).get("props", {}).get("value") == "Salut."
          and jr.get("title") == "Matin — recette", f"{str(n9)[:200]} {jr.get('title')}")
    parts = js(c.get(f"/api/jobs/{j9}/parts")).get("parts", [])
    pins = {p["slot"]: {"job_id": p["job_id"], "empreinte": p["empreinte"]} for p in parts}
    g2 = json.loads(json.dumps(GRAPHE)); g2["nodes"][0]["props"]["filename"] = "autre.png"; g2["nodes"][3]["props"]["value"] = "Salut."
    cap2 = capture(pins=pins); cap2["slot_values"]["animation"]["seedance"]["image_filename"] = "autre.png"
    cap2["slot_values"]["avatar"]["heygen"]["script"] = "Salut."
    gid2 = js(c.post("/api/studio-graphs", json={"name": "Epinglee", "graph": g2, "recette": cap2})).get("id")
    t2 = {t["valeur"]: t["id"] for t in js(c.get(f"/api/studio-graphs/{gid2}/recette")).get("trous", [])}
    dv2 = js(c.post(f"/api/studio-graphs/{gid2}/recette/devis", json={"valeurs": {t2.get("Salut.", "?"): "Autre script."}}))
    APPELS.clear()
    r11 = c.post(f"/api/studio-graphs/{gid2}/recette/lancer", json={"valeurs": {t2.get("Salut.", "?"): "Autre script."}, "max_usd": dv2.get("usd")})
    st11 = attendre(c, js(r11).get("job_id")) if js(r11).get("job_id") else None
    check("R11 EPINGLES gardees : seul le trou change (script) -> le Seedance epingle est REEMPLOYE (devis : 1 reemploi), seul l'avatar repart",
          len(pins) == 2 and dv2.get("reemplois") == 1 and dv2.get("generations") == 1 and st11 == "done" and APPELS == ["heygen"],
          f"{pins} {dv2} {st11} {APPELS}")
src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("R12 la route de lancement est RECENSEE payante ; le devis non", '"/studio-graphs/{graph_id}/recette/lancer"' in src and "/recette/devis" not in src)
try:
    asyncio.run(RT.lancer_studio_recette("x", {"max_usd": 1}, types.SimpleNamespace(client=types.SimpleNamespace(host="10.0.0.7")), None))
    _st = 200
except HTTPException as e:
    _st = e.status_code
check("R13 la route de lancement refuse elle-meme un client distant (403)", _st == 403, str(_st))

print("\n[B] la capture et le bouton, dans le bundle livre")
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
PREP = "if(!_pv&&g&&t){var dzPP=await dzPinPreparer(e,t,n,o,g);if(dzPP)return{ok:!1,error:dzPP}}"
CAPT = ("if(window.__dzCapture){window.__dzCapture=!1;return{ok:!0,captured:{template_id:e,slot_values:t||{},voice_mode:n||null,"
        "template:o||null,title:i||null,voiceover:dzGraphVoiceover(g)||null}}}const s=await fetch(`${Te}/layout-templates/")
check("B1 la capture s'arrete APRES la preparation des epingles et AVANT l'envoi, voix comprise", BUN.count(PREP + CAPT) == 1)
check("B2 « Recette » dans la barre du Studio, juste avant « Importer »",
      BUN.count("r.jsx(DzRecetteBtn,{graph:o,setGraph:i,dire:p}),r.jsx(DzImportGraph,{graph:o,") == 1 and BUN.count("r.jsx(DzRecetteBtn,") == 1)


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
            if vu and prof == 0: return BUN[k - 6 if BUN[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


COUCHE = "\n".join(fonction(n) for n in ("dzPinRendu", "dzRecRefus", "dzRecVerrou", "dzRecCapturer", "DzRecetteBtn"))
HARNAIS = r"""
var H=[],hi=0,J=[],MHV=0,MH=null,REP=null,SAISIE="Ma recette",ETAT=null;
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el};var K="K";
var CORPS=[];function f0(u,o){J.push(["net",String(o&&o.method||"GET"),String(u&&u.url||u)]);if(o&&o.body)CORPS.push(JSON.parse(o.body));
  return Promise.resolve({ok:REP?REP.ok:true,status:REP?REP.status:200,json:async function(){return REP?REP.d:{}}})}
var window={fetch:f0,__dzCapture:false,dispatchEvent:function(e){J.push(["evt",e.type])},
  __dzDialogue:{saisir:async function(m,o){J.push(["saisir",m,o.titre,o.valeur,o.ok]);return SAISIE},
    informer:async function(m,o){J.push(["informer",m,o&&o.titre])}}};
var fetch=function(){return window.fetch.apply(null,arguments)};
function Event(t){this.type=t}
function Mh(g){MHV++;return MH(g)}
var COMPO={nodes:[{id:"a",type:"Seedance"},{id:"b",type:"HeyGenAvatar"}]};
function capteur(){return {ok:true,run:async function(){
  if(window.__dzCapture){window.__dzCapture=false;return {ok:true,captured:{template_id:"tpl",slot_values:{a:{source_kind:"text",text:"x"}}}}}
  return {ok:true,job_id:"PAYE"}}}}
"""


def node(corps):
    f = _tmp / f"r{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


R = node("""
R.refus=[dzRecRefus({nodes:[]}),dzRecRefus({nodes:[{type:"Seedance"},{type:"Image"}]}),dzRecRefus({nodes:[{type:"HeyGenAvatar"}]}),
  dzRecRefus({nodes:[{type:"Animation"},{type:"SpatialCompose"}]}),dzRecRefus(COMPO),dzRecRefus({nodes:[{type:"Concatenate"}]}),
  dzRecRefus({nodes:[{type:"Upload",props:{jobId:"j"}},{type:"Animation"}]})];
var V=dzRecVerrou(f0);J=[];await V("/api/layout-templates/x");await V("/api/studio/pins/verifier",{method:"POST"});await V({url:"/api/studio/pins/verifier"},{method:"POST"});
var bloque=null;try{await V("/api/generate",{method:"POST"})}catch(e){bloque=String(e.message)}
var bloque2=null;try{await V({url:"/api/layout-templates/t/render"},{method:"post"})}catch(e){bloque2=String(e.message)}
R.verrou={net:J.slice(),bloque:bloque,bloque2:bloque2};
MHV=0;var e1=null;try{await dzRecCapturer({nodes:[{type:"Seedance"},{type:"Image"}]})}catch(e){e1=String(e.message)}R.solo={mh:MHV,err:e1};
MH=capteur;R.cap=await dzRecCapturer(COMPO);R.apres={cap:window.__dzCapture,f:window.fetch===f0};
MH=function(){return {ok:true,run:async function(){return await window.fetch("/api/generate",{method:"POST"})}}};J=[];var e2=null;
try{await dzRecCapturer(COMPO)}catch(e){e2=String(e.message)}R.fuite={err:e2,net:J.slice(),f:window.fetch===f0,cap:window.__dzCapture};
MH=function(){return {ok:false,error:"Add a Render node"}};var e3=null;try{await dzRecCapturer(COMPO)}catch(e){e3=String(e.message)}R.compil=e3;
MH=function(){return {ok:true,run:async function(){return {ok:true,job_id:"x"}}}};var e4=null;try{await dzRecCapturer(COMPO)}catch(e){e4=String(e.message)}R.pasCapt=e4;
""")
check("B3 sous node : la capture s'execute (aucune exception non rattrapee)", R is not None)
if R:
    check("B4 refus AVANT compilation : vide, Seedance seul, avatar seul, Animation (sauf derriere un UGC) ; un graphe compose passe",
          all(isinstance(x, str) and len(x) > 10 for x in R["refus"][:4]) and R["refus"][4:] == ["", "", ""] and "Animation" in R["refus"][3], str(R["refus"]))
    check("B5 le VERROU : GET et la verification gratuite des epingles passent ; tout autre envoi est REFUSE sans partir (meme en Request)",
          R["verrou"]["net"] == [["net", "GET", "/api/layout-templates/x"], ["net", "POST", "/api/studio/pins/verifier"], ["net", "POST", "/api/studio/pins/verifier"]]
          and "bloquée" in (R["verrou"]["bloque"] or "") and "/api/generate" in R["verrou"]["bloque"] and "bloquée" in (R["verrou"]["bloque2"] or ""), str(R["verrou"]))
    check("B6 un graphe refuse n'est meme pas COMPILE", R["solo"]["mh"] == 0 and "fournisseur" in (R["solo"]["err"] or ""), str(R["solo"]))
    check("B7 graphe compose : la requete CAPTUREE est rendue ; drapeau baisse et fetch RENDU apres", R["cap"] == {"template_id": "tpl",
          "slot_values": {"a": {"source_kind": "text", "text": "x"}}} and R["apres"] == {"cap": False, "f": True}, str(R["cap"]) + str(R["apres"]))
    check("B8 une branche qui tenterait d'ENVOYER pendant la capture : bloquee (rien ne part), erreur dite, fetch et drapeau rendus",
          "bloquée" in (R["fuite"]["err"] or "") and R["fuite"]["net"] == [] and R["fuite"]["f"] is True and R["fuite"]["cap"] is False, str(R["fuite"]))
    check("B9 compilation impossible : SA phrase ; rien de capture : dit", R["compil"] == "Add a Render node" and "figée" in (R["pasCapt"] or ""), f"{R['compil']} {R['pasCapt']}")

R2 = node("""
MH=capteur;var SET=[],DIRE=[];
async function clic(){hi=0;var b=DzRecetteBtn({graph:{id:"g1",name:"Matin",nodes:COMPO.nodes},setGraph:function(f){SET.push(f({id:"g1",name:"Matin"}))},dire:function(m){DIRE.push(m)}});
  R.titre=b.p.title;R.ch=b.p.children;R.icon=b.p.icon;await b.p.onClick();for(var i=0;i<5;i++)await new Promise(function(r){setImmediate(r)})}
J=[];SAISIE=null;await clic();R.annule=J.slice();
J=[];CORPS=[];SAISIE="Recette du matin";REP={ok:true,status:200,d:{id:"g1",name:"Recette du matin",trous:3}};await clic();R.ok=J.slice();R.set=SET.slice();R.dire=DIRE.slice();R.corps=CORPS.slice();
J=[];REP={ok:false,status:400,d:{detail:"La recette n'a pas de template."}};await clic();R.refus=J.slice();
J=[];MH=function(){return {ok:false,error:"Add a Render node"}};await clic();R.err=J.slice();
""")
check("B10 le bouton s'execute sous node", R2 is not None)
if R2:
    post = [x for x in R2["ok"] if x[0] == "net"]
    check("B11 « Recette » : bouton du Studio AVEC title qui dit que rien n'est genere ici", R2["ch"] == "Recette" and R2["icon"] == "check"
          and "rien n’est généré ici" in (R2["titre"] or ""), str(R2.get("titre")))
    check("B12 le nom est demande par le dialogue maison (valeur = nom du graphe) ; annuler n'enregistre RIEN",
          R2["annule"] == [["saisir", "Nom de la recette (le graphe est enregistré avec elle) :", "Figer en recette", "Matin", "Enregistrer"]], str(R2["annule"]))
    check("B13 nom donne : POST /api/studio-graphs avec le graphe ET la capture ; le graphe prend l'id rendu ; la liste est rafraichie ; le message dit les trous",
          post == [["net", "POST", "/api/studio-graphs"]] and ["evt", "dz-graphs-changed"] in R2["ok"]
          and len(R2["corps"]) == 1 and R2["corps"][0].get("id") == "g1" and R2["corps"][0].get("name") == "Recette du matin"
          and R2["corps"][0].get("recette", {}).get("template_id") == "tpl" and len(R2["corps"][0].get("graph", {}).get("nodes", [])) == 2
          and R2["set"][-1] == {"id": "g1", "name": "Recette du matin"} and "3 source(s) remplaçable(s)" in R2["dire"][-1], str(R2["ok"]) + str(R2["dire"]))
    check("B14 refus du serveur : SA phrase dans un dialogue « Recette refusée » ; compilation impossible : « Recette impossible »",
          R2["refus"][-1] == ["informer", "La recette n'a pas de template.", "Recette refusée"]
          and R2["err"] == [["informer", "Add a Render node", "Recette impossible"]], f"{R2['refus']} {R2['err']}")
check("B15 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "confirm(" not in COUCHE and BUN.count("DzTracks") == 181 and BUN.count("__dzCoutBlanc") == 7
      and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
