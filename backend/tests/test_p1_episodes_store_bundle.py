# -*- coding: utf-8 -*-
"""P1 t132 (lot B de #6, 28/09/2026) — LA PAGE EPISODES ENREGISTRE, ROUVRE,
NARRE UNE FOIS.

Temoin (.bak_montage) : DzEpisodes n'avait ni barre ni etat d'episode ;
assembleEpisode n'envoyait aucun episode_id. Groupe P1 du maillon montage :
P1es1 (dzEpDoc / dzEpSnap / DzEpBar), P1es2 (etat dzE), P1es3 (barre sous
l'en-tete), et le repli t132 dans P1ep4 (l'assemblage enregistre d'abord).
DzEpBar n'a AUCUN hook : il est EXECUTE sous node avec des composants-temoins,
un faux fetch qui journalise et un faux dialogue ; les setters de la page sont
des espions. Faute n6 : details par _d().
Run : & $PY tests/test_p1_episodes_store_bundle.py   (depuis backend/)
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:500]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
s = BUNDLE.read_bytes().decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
NODE = shutil.which("node")

print("\n[0] temoins et presence")
check("0.1 .bak present, node present ; temoin : aucune barre ni episode_id dans le .bak",
      bool(bak) and bool(NODE) and "DzEpBar" not in bak and "episode_id:" not in bak.split("function DzEpisodes(")[1][:40000], "")
check("0.2 bundle : DzEpBar pose sous l'en-tete x1, etat dzE x1, assemblage qui enregistre puis envoie episode_id",
      s.count("r.jsx(DzEpBar,{st:{title:title") == 1 and s.count(",_dzE=x.useState({id:\"\",sig:\"\",msg:\"\",list:null,open:!1})") == 1
      and s.count("var dzEid=window.__dzEpSave?await window.__dzEpSave():\"\";") == 1
      and s.count("max_usd:dzMx,episode_id:dzEid||void 0})") == 1, "")

i0 = s.find("function dzEpDoc(")
i1 = s.find('(function(){try{if(document.getElementById("__dzNavMotion"))return;', i0)
SRC = s[i0:i1] if 0 <= i0 < i1 else ""
check("0.3 source de la barre extraite", bool(SRC) and "function DzEpBar(" in SRC, "")

HARNAIS = r"""
var journal=[],reponses={},confirmer=true,dz=null;
var r={Fragment:"F",jsx:function(t,p){return{t:t,p:p||{}}},jsxs:function(t,p){return{t:t,p:p||{}}}};
var D={imageUrl:function(f){return "/api/images/"+f}};
global.window={__dzDialogue:{confirmer:function(m,o){journal.push(["confirm",(o&&o.titre)||""]);return Promise.resolve(confirmer)}}};
global.fetch=function(u,o){var m=(o&&o.method)||"GET";journal.push([m,u,o&&o.body?JSON.parse(o.body):null]);
  var rep=reponses[m+" "+u]||{ok:true,j:{}};return Promise.resolve({ok:rep.ok!==false,status:rep.status||200,json:function(){return Promise.resolve(rep.j)}})};
var appels=[];function espion(n){return function(v){appels.push([n,v])}}
var SET={};["setTitle","setScript","setLang","setVid","setScenes","setSceneMethod","setSceneStyle","setRes","setEpJob","setEpStatus"].forEach(function(n){SET[n]=espion(n)});
function setDz(v){dz=typeof v==="function"?v(dz):v}
function arbre(st){return DzEpBar({st:st,set:SET,dz:dz,setDz:setDz})}
function boutons(n,acc){acc=acc||{};if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(c){boutons(c,acc)});return acc}
  if(n.p){if(n.p["data-dzep"])acc[n.p["data-dzep"]]=n;boutons(n.p.children,acc)}return acc}
function texte(n){if(n==null||n===false)return"";if(typeof n==="string"||typeof n==="number")return String(n);if(Array.isArray(n))return n.map(texte).join("");return n.p?texte(n.p.children):""}
function attendre(){return new Promise(function(res){setTimeout(res,20)})}
"""
ST = {"title": "Chapitre 1", "script": "Texte du chapitre.", "lang": "fr", "vid": "v1",
      "scenes": [{"text": "a", "image_filename": "i.png", "image_url": "/api/images/i.png", "motion": "seedance", "video_model": "seedance-v1-pro"}],
      "sceneMethod": "paragraph", "sceneStyle": "", "res": {"filename": "n.mp3", "url": "/api/audio/n.mp3", "kb": 12}}
DOC = {"id": "ep_0123456789ab", "title": "Rouvert", "script": "Autre texte.", "language": "en", "voice_id": "v2",
       "scenes": [{"text": "b", "image_filename": "j.png", "motion": "kenburns"}], "scene_method": "ai", "scene_style": "vitrail",
       "narration": None, "last_job_id": "job-42"}
SCEN = HARNAIS + SRC + r"""
(async function(){var out={},st=%s,DOC=%s;
dz={id:"",sig:"",msg:"",list:null,open:!1};
out.doc=dzEpDoc(st);
var b=boutons(arbre(st));out.dirty0=texte(b.enregistrer);out.msg0=texte(b.msg);
reponses["POST /api/episodes"]={j:{id:"ep_aaaaaaaaaaaa"}};
b.enregistrer.p.onClick();await attendre();
out.post=journal.filter(function(x){return x[0]==="POST"})[0]||null;out.dz1={id:dz.id,propre:dz.sig===dzEpSnap(st)};
b=boutons(arbre(st));out.dirty1=texte(b.enregistrer);
journal=[];var id=await window.__dzEpSave();out.put=journal[0];out.saveId=id;
var st2=JSON.parse(JSON.stringify(st));st2.title="Modifie";b=boutons(arbre(st2));out.dirty2=texte(b.enregistrer);
journal=[];confirmer=false;reponses["GET /api/episodes/ep_0123456789ab"]={j:DOC};
reponses["GET /api/episodes"]={j:{episodes:[{id:"ep_0123456789ab",title:"Rouvert",scene_count:1,updated_at:"2026-09-28T10:00:00"}]}};
b.ouvrir.p.onClick();await attendre();var t=arbre(st2),items=[];(function f(n){if(!n||typeof n!=="object")return;if(Array.isArray(n)){n.forEach(f);return}if(n.p){if(n.p["data-dzepitem"])items.push(n);f(n.p.children)}})(t);
out.items=items.map(function(n){return n.p["data-dzepitem"]});appels=[];
items[0].p.onClick();await attendre();out.refus={confirm:journal.filter(function(x){return x[0]==="confirm"}).length,appels:appels.length};
confirmer=true;journal=[];items[0].p.onClick();await attendre();
var A={};appels.forEach(function(x){A[x[0]]=x[1]});out.charge=A;out.dz2={id:dz.id,msg:dz.msg};
var st3={title:"Rouvert",script:"Autre texte.",lang:"en",vid:"v2",scenes:A.setScenes,sceneMethod:"ai",sceneStyle:"vitrail",res:null};
out.propreApresOuverture=dz.sig===dzEpSnap(st3);
journal=[];appels=[];reponses["PUT /api/episodes/ep_0123456789ab"]={j:{id:"ep_0123456789ab"}};
reponses["POST /api/episodes/ep_0123456789ab/narrate"]={j:{scenes:[{scene:1,cached:true},{scene:2,cached:false}],paid_chars:17}};
b=boutons(arbre(st3));b.narrer.p.onClick();await attendre();await attendre();
out.narre=journal.filter(function(x){return x[0]!=="confirm"}).map(function(x){return x[0]+" "+x[1]});out.msgNarre=dz.msg;
process.stdout.write(JSON.stringify(out));})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
""" % (json.dumps(ST), json.dumps(DOC))
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(SCEN)
rr = subprocess.run([NODE, f.name], capture_output=True, text=True, encoding="utf-8") if NODE else None
os.unlink(f.name)
try:
    O = json.loads(rr.stdout) if rr and rr.stdout else {}
except Exception:
    O = {"erreur": (rr.stdout if rr else "")[:300]}

print("\n[1] DzEpBar execute")
check("1.1 s'execute", bool(O) and "erreur" not in O, _d(O.get("erreur"), rr.stderr[-300:] if rr else ""))
dd = O.get("doc") or {}
check("1.2 le document envoye : champs de la page, image_url RETIREE (derivee), scenes intactes sinon",
      dd.get("title") == "Chapitre 1" and dd.get("language") == "fr" and dd.get("voice_id") == "v1"
      and dd.get("scenes") == [{"text": "a", "image_filename": "i.png", "motion": "seedance", "video_model": "seedance-v1-pro"}]
      and dd.get("narration") == {"filename": "n.mp3", "url": "/api/audio/n.mp3", "kb": 12}, _d(dd))
check("1.3 non enregistre : « ● Enregistrer » et « Non enregistré »", O.get("dirty0") == "● Enregistrer" and O.get("msg0") == "Non enregistré",
      _d(O.get("dirty0"), O.get("msg0")))
check("1.4 Enregistrer : POST /api/episodes avec le document ; id recu, etat propre", (O.get("post") or [None, None])[1] == "/api/episodes"
      and (O.get("post") or [0, 0, {}])[2] == dd and O.get("dz1") == {"id": "ep_aaaaaaaaaaaa", "propre": True}
      and O.get("dirty1") == "Enregistrer", _d(O.get("post"), O.get("dz1"), O.get("dirty1")))
check("1.5 window.__dzEpSave (assemblage) : PUT sur l'id connu, rend l'id", (O.get("put") or [0, 0])[0:2] == ["PUT", "/api/episodes/ep_aaaaaaaaaaaa"]
      and O.get("saveId") == "ep_aaaaaaaaaaaa", _d(O.get("put"), O.get("saveId")))
check("1.6 une modification rallume « ● Enregistrer »", O.get("dirty2") == "● Enregistrer", _d(O.get("dirty2")))
check("1.7 Ouvrir liste les episodes du serveur", O.get("items") == ["ep_0123456789ab"], _d(O.get("items")))
check("1.8 episode modifie + confirmation REFUSEE : rien n'est charge", O.get("refus") == {"confirm": 1, "appels": 0}, _d(O.get("refus")))
ch = O.get("charge") or {}
check("1.9 confirmation acceptee : TOUS les champs charges, image_url recalculee, job rattache repris",
      ch.get("setTitle") == "Rouvert" and ch.get("setScript") == "Autre texte." and ch.get("setLang") == "en" and ch.get("setVid") == "v2"
      and ch.get("setScenes") == [{"text": "b", "image_filename": "j.png", "motion": "kenburns", "image_url": "/api/images/j.png"}]
      and ch.get("setSceneMethod") == "ai" and ch.get("setSceneStyle") == "vitrail" and ch.get("setRes") is None
      and ch.get("setEpJob") == "job-42" and "setEpStatus" in ch and (O.get("dz2") or {}).get("id") == "ep_0123456789ab", _d(ch, O.get("dz2")))
check("1.10 juste apres l'ouverture, l'episode n'apparait PAS modifie", O.get("propreApresOuverture") is True, _d(O.get("propreApresOuverture")))
check("1.11 Narrer : enregistre (PUT), narre (POST /narrate), relit l'episode (GET) ; le message dit reutilisees et payes",
      O.get("narre") == ["PUT /api/episodes/ep_0123456789ab", "POST /api/episodes/ep_0123456789ab/narrate", "GET /api/episodes/ep_0123456789ab"]
      and "1 réutilisée(s)" in (O.get("msgNarre") or "") and "17 car. payés" in (O.get("msgNarre") or ""),
      _d(O.get("narre"), O.get("msgNarre")))

print("\n[2] groupe P1 et syntaxe")
_P1 = [t for t, _a, _r in getattr(P, "P1", [])]
# P1 #9 (28/09/2026) : le groupe P1 se prolonge (P1gc1..P1gc9) -- P1es1..P1es3 restent juste AVANT eux
_ES = [t.split("-")[0] for t in _P1]
check("2.1 P1es1..P1es3 dans le groupe P1 en queue de PATCHES, suivis des seules P1gc (tache #9)",
      "P1es1" in _ES and _ES[_ES.index("P1es1"):_ES.index("P1es1") + 3] == ["P1es1", "P1es2", "P1es3"]
      and all(t.startswith(("P1gc", "P2dg", "P2pl")) for t in _ES[_ES.index("P1es1") + 3:])   # + P2dg (tache #15)
      and [t for t, _a, _r in P.PATCHES[-len(_P1):]] == _P1, _d(_P1[-12:]))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("2.2 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
