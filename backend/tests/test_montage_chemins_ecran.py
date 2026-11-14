# -*- coding: utf-8 -*-
"""t409 (05/11/2026) — l'écran du Montage lit ce que le rendu lit : `src.file_path` et les sources que le navigateur ne décode pas.

CONSTAT (teaser de 118 s poussé le 05/11) : 50 clips vidéo et 193 sons donnés par chemin absolu passaient par
`POST /api/montage/render`, mais le moniteur affichait « TROU » : `svmActiveV1`, `svmSrcUrl`, `svmSrcKey` et le pool du
lecteur vivant ne connaissaient que job_id / audio / image. Second écart : une source ProRes laissait le moniteur
muet (élément <video> en erreur, ou métadonnées sans image), alors que `POST /api/montage/proxy` sait fabriquer un
aperçu lisible et que l'écran ne l'appelait jamais.
CORRECTION : `GET /api/montage/source?src=` (mêmes gardes que `_media_source`, plus : média seulement, jamais un
appel d'un autre site) ; l'écran passe par elle pour tout `file_path` ; une source illisible se dit dans le moniteur,
son aperçu 480p se fabrique, un à la fois, puis remplace la source dans l'élément.

Run : & $PY tests/test_montage_chemins_ecran.py   (depuis backend/)
"""
import json, os, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt409_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REPO = os.path.abspath(os.path.join(BACKEND, ".."))
sys.path.insert(0, BACKEND)


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand
    print(f"  ECHEC {name} introuvable")
    sys.exit(1)


FF, FP = _exe("ffmpeg"), _exe("ffprobe")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240, entree=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
                          input=entree)

def fixture(cmd):
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture : {r.stderr[-400:]}")
        sys.exit(1)

def codec(path):
    return sh([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0",
               path]).stdout.strip()

MP4 = os.path.join(TMP, "plan.mp4")
fixture([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x2040a0:s=160x288:r=30:d=2", "-pix_fmt", "yuv420p", MP4])
MOV = os.path.join(TMP, "plan_h264.mov")
fixture([FF, "-y", "-v", "error", "-i", MP4, "-c", "copy", MOV])
PRORES = os.path.join(TMP, "plan_prores.mov")
fixture([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x30c030:s=160x288:r=30:d=2", "-c:v", "prores_ks",
         "-profile:v", "1", PRORES])
WAV = os.path.join(TMP, "son.wav")
fixture([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", WAV])
PNG = os.path.join(TMP, "carton.png")
fixture([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=32x32:d=1", "-frames:v", "1", PNG])
SECRET = os.path.join(TMP, "cles.env")
open(SECRET, "w", encoding="utf-8").write("FAL_KEY=secret-a-ne-jamais-servir\n")
BASE = os.path.join(TMP, "deepotus.db")
open(BASE, "wb").write(b"SQLite format 3\0" + b"x" * 64)
os.makedirs(os.path.join(TMP, "dossier.mp4"), exist_ok=True)

print("\n[1] ROUTE — GET /api/montage/source")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
def q(src): return "/api/montage/source?src=" + json.dumps(src)
def fp(p): return q({"file_path": p})
with TestClient(app) as c:
    r = c.get(fp(MP4))
    check("mp4_200", r.status_code == 200 and r.headers.get("content-type", "").startswith("video/mp4")
          and len(r.content) == os.path.getsize(MP4), f"{r.status_code} {r.headers.get('content-type')}")
    r = c.get(fp(MP4), headers={"Range": "bytes=10-19"})
    check("mp4_plage_206", r.status_code == 206 and len(r.content) == 10, f"{r.status_code} {len(r.content)}")
    r = c.get(fp(MOV))
    check("mov_annonce_video_mp4", r.status_code == 200 and r.headers.get("content-type", "").startswith("video/mp4"),
          f"{r.status_code} {r.headers.get('content-type')}")
    r = c.get(fp(WAV))
    check("wav_200_audio", r.status_code == 200 and r.headers.get("content-type", "").startswith("audio/"),
          f"{r.status_code} {r.headers.get('content-type')}")
    r = c.get(fp(PNG))
    check("png_200_image", r.status_code == 200 and r.headers.get("content-type", "").startswith("image/png"),
          f"{r.status_code} {r.headers.get('content-type')}")
    for nom, chemin in (("env", SECRET), ("base", BASE)):
        r = c.get(fp(chemin))
        check(f"{nom}_refuse_415", r.status_code == 415 and b"secret" not in r.content, str(r.status_code))
    check("absent_404", c.get(fp(os.path.join(TMP, "absent.mp4"))).status_code == 404)
    check("dossier_404", c.get(fp(os.path.join(TMP, "dossier.mp4"))).status_code == 404)
    os.chdir(TMP)
    check("relatif_404", c.get(fp("plan.mp4")).status_code == 404)
    os.chdir(BACKEND)
    check("src_illisible_404", c.get("/api/montage/source?src=pasdujson").status_code == 404)
    r = c.get(fp(MP4), headers={"Sec-Fetch-Site": "cross-site"})
    check("autre_site_403", r.status_code == 403, str(r.status_code))
    r = c.get(fp(MP4), headers={"Sec-Fetch-Site": "same-origin"})
    check("meme_origine_200", r.status_code == 200, str(r.status_code))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _jeton_appareil as _JA                           # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("hors_boucle_locale_403", c2.get(fp(MP4)).status_code == 403)

print("\n[2] APERÇU — POST /api/montage/proxy d'une source ProRes donnée par chemin")
with TestClient(app) as c:
    check("prores_avant_404", c.get("/api/montage/proxy?src=" + json.dumps({"file_path": PRORES})).status_code == 404)
    r = c.post("/api/montage/proxy", json={"src": {"file_path": PRORES}})
    d = r.json()
    check("prores_post_ok", r.status_code == 200 and (d.get("job_id") or d.get("ready")), r.text[:200])
    r = c.get("/api/montage/proxy?src=" + json.dumps({"file_path": PRORES}))
    check("prores_apercu_200", r.status_code == 200 and r.headers.get("content-type", "").startswith("video/mp4"),
          str(r.status_code))
    apercu = os.path.join(TMP, "apercu.mp4")
    open(apercu, "wb").write(r.content)
    check("prores_apercu_h264", codec(PRORES) == "prores" and codec(apercu) == "h264", codec(apercu))

print("\n[3] ÉCRAN — les aides pures et la fabrication de l'aperçu, exécutées sous node")
SRCJS = open(os.path.join(REPO, "frontend", "patches", "son-vfx-montage.js"), encoding="utf-8", newline="").read().replace("\r\n", "\n")
BLOC = SRCJS[SRCJS.index("/* ═══════════ t409"):] if "/* ═══════════ t409" in SRCJS else ""
check("bloc_t409_en_fin_de_couche", bool(BLOC))
def fonction(nom):
    m = re.search(r"function " + nom + r"\(.*?\n(?=function |var |/\*)", SRCJS, re.S)
    return m.group(0) if m else ""
AIDES = "\n".join(fonction(n) for n in ("svmActiveV1", "svmFirstA2Id", "svmSrcKey", "svmSrcUrl", "svU", "svmCalqueUrl"))
HARNAIS = r"""
var attente=[];globalThis.setTimeout=function(f){attente.push(f);return attente.length};
var elt=function(o){o=o||{};var e={ec:{},charges:0,videoWidth:o.w||0,_src:o.src===void 0?"/brut":o.src,
  addEventListener:function(n,f){(e.ec[n]=e.ec[n]||[]).push(f)},removeEventListener:function(n,f){e.ec[n]=(e.ec[n]||[]).filter(function(g){return g!==f})},
  feu:function(n){(e.ec[n]||[]).slice().forEach(function(f){f()})},getAttribute:function(){return e._src},load:function(){e.charges++}};
  Object.defineProperty(e,"src",{get:function(){return e._src},set:function(v){e._src=v}});return e};
var appels=[],reponses=[];
globalThis.fetch=function(u,o){appels.push({u:u,o:o});var d=reponses.shift()||{ok:!0,d:{ok:!0,ready:!0}};
  return Promise.resolve({ok:d.ok,status:d.ok?200:415,json:function(){return Promise.resolve(d.d)}})};
var dzT=function(k,v){return k+(v?" "+JSON.stringify(v):"")},
    r={jsx:function(t,p){return {t:t,p:p}}},x={useState:function(v){return [v,function(){}]},useEffect:function(){}};
AIDES_ICI
BLOC_ICI
var attendre=async function(){for(var i=0;i<40;i++){await Promise.resolve();await new Promise(function(f){setImmediate(f)});
  while(attente.length)attente.shift()()}};
(async function(){var o={};
  var P={file_path:"C:/a b/plan.mp4"},G={file_path:"C:/a/carton.png"};
  o.cle=svmSrcKey(P);o.cle_job=svmSrcKey({job_id:"j"});o.cle_vide=svmSrcKey({});
  o.url=svmSrcUrl(P);o.url_job=svmSrcUrl({job_id:"j"});o.url_audio=svmSrcUrl({audio:"a.mp3"});
  o.v1=(svmActiveV1([{id:1,tr:"v1",src:P,start:0,end:2}],1)||{}).id;
  o.v1_nu=svmActiveV1([{id:1,tr:"v1",src:{},start:0,end:2}],1);
  o.a2=svmFirstA2Id([{id:7,tr:"a2",src:{file_path:"C:/m.wav"}}]);
  o.svW_mp4=svW(P);o.svW_png=svW(G);o.svW_job=svW({job_id:"j"});o.svW_vide=svW({});
  o.svU_b=svU(P,"b");o.svU_o=svU(P,"o");o.svU_job_b=svU({job_id:"j"},"b");o.svU_job_o=svU({job_id:"j"},"o");

  var e1=elt(),s1={file_path:"C:/p1.mov"},sync=0;
  var it=svG(e1,s1,"b",function(){sync++});
  o.it_video=it.video;
  reponses.push({ok:!0,d:{ok:!0,ready:!1,job_id:"J1"}},{ok:!0,d:{status:"running"}},{ok:!0,d:{status:"done"}});
  var vus=[];SVM_PX_EC.add(function(){vus.push((SVM_PX.get(svmSrcKey(s1))||{}).st)});
  o.vierge=appels.length;e1.feu("error");await attendre();
  o.post=appels[0]&&appels[0].u;o.corps=appels[0]&&JSON.parse(appels[0].o.body);o.methode=appels[0]&&appels[0].o.method;
  o.suivi=appels[1]&&appels[1].u;o.vus=vus;o.etat=SVM_PX.get(svmSrcKey(s1)).st;
  o.src_apres=e1.src;o.charges=e1.charges;e1.feu("loadeddata");e1.feu("loadeddata");o.sync=sync;
  o.message_ok=svL({c:{src:s1}});

  appels.length=0;var e2=elt({w:0}),s2={file_path:"C:/p2.mov"};svG(e2,s2,"b",function(){});
  reponses.push({ok:!1,d:{detail:"ffmpeg en panne"}});e2.feu("loadedmetadata");await attendre();
  o.m0_post=appels.length;o.m0_etat=SVM_PX.get(svmSrcKey(s2)).st;o.m0_msg=SVM_PX.get(svmSrcKey(s2)).msg;
  o.message_err=svL({c:{src:s2}});
  appels.length=0;var e9=elt(),s9={file_path:"C:/p9.mov"};svG(e9,s9,"b",function(){});
  reponses.push({ok:!1,d:{detail:"x".repeat(400)}});e9.feu("error");await attendre();
  o.message_long=svL({c:{src:s9}});

  appels.length=0;var e3=elt({w:1920}),s3={file_path:"C:/p3.mp4"};svG(e3,s3,"b",function(){});e3.feu("loadedmetadata");await attendre();
  o.lisible_post=appels.length;
  var e4=elt(),s4={file_path:"C:/p4.mov"};svG(e4,s4,"o",function(){});e4.feu("error");await attendre();
  o.calque_post=appels.length;
  var e5=elt({src:null}),s5={file_path:"C:/p5.mov"};svG(e5,s5,"b",function(){});e5.feu("error");await attendre();
  o.evince_post=appels.length;

  /* un seul aperçu à la fois : le second part quand le premier a fini */
  var e6=elt(),e7=elt(),s6={file_path:"C:/p6.mov"},s7={file_path:"C:/p7.mov"};svG(e6,s6,"b",function(){});svG(e7,s7,"b",function(){});
  appels.length=0;reponses.push({ok:!0,d:{ready:!1,job_id:"J6"}},{ok:!0,d:{status:"running"}},{ok:!0,d:{status:"done"}},{ok:!0,d:{ready:!0}});
  e6.feu("error");e7.feu("error");await Promise.resolve();await Promise.resolve();
  o.en_vol=appels.filter(function(a){return a.u==="/api/montage/proxy"}).length;
  o.message_attente=svL({c:{src:s7}});await attendre();
  o.apres_vol=appels.filter(function(a){return a.u==="/api/montage/proxy"}).length;
  var e8=elt();var it8=svG(e8,s7,"b",function(){});o.deja_apercu=e8.src;
  o.message_trou=svL({c:null});o.message_lisible=svL({c:{src:s3}});
  console.log(JSON.stringify(o))})().catch(function(e){console.log(JSON.stringify({plante:String(e&&e.stack||e)}))});
"""
script = HARNAIS.replace("AIDES_ICI", AIDES).replace("BLOC_ICI", BLOC)
sortie = sh(["node", "-"], entree=script)
try:
    o = json.loads(sortie.stdout.strip().splitlines()[-1])
except Exception:
    o = {}
    print("  node :", sortie.stdout[-300:], sortie.stderr[-600:])
if o.get("plante"): print("  node :", o["plante"][:600])
check("cle_chemin", o.get("cle") == "f:C:/a b/plan.mp4", str(o.get("cle")))
check("cle_job_intacte", o.get("cle_job") == "j:j" and o.get("cle_vide") == "")
check("url_chemin_route_source", o.get("url") == "/api/montage/source?src=%7B%22file_path%22%3A%22C%3A%2Fa%20b%2Fplan.mp4%22%7D", str(o.get("url")))
check("url_job_intacte", o.get("url_job") == "/api/jobs/j/video" and o.get("url_audio") == "/api/audio/a.mp3")
check("moniteur_prend_le_chemin", o.get("v1") == 1 and o.get("v1_nu") is None, f"{o.get('v1')} {o.get('v1_nu')}")
check("musique_a2_par_chemin", o.get("a2") == 7, str(o.get("a2")))
check("video_ou_image_par_extension", o.get("svW_mp4") is True and o.get("svW_png") is False
      and o.get("svW_job") is True and o.get("svW_vide") is False)
check("svU_chemin_fond", o.get("svU_b") == o.get("url"), str(o.get("svU_b")))
check("svU_chemin_calque", str(o.get("svU_o")).startswith("/api/montage/calque?src=%7B%22file_path"), str(o.get("svU_o")))
check("svU_job_intact", o.get("svU_job_b") == "/api/jobs/j/video" and "job_id" in str(o.get("svU_job_o")))
check("element_video", o.get("it_video") is True)
check("rien_avant_erreur", o.get("vierge") == 0)
check("erreur_lance_post_proxy", o.get("post") == "/api/montage/proxy" and o.get("methode") == "POST"
      and o.get("corps") == {"src": {"file_path": "C:/p1.mov"}}, f"{o.get('post')} {o.get('corps')}")
check("job_suivi", o.get("suivi") == "/api/jobs/J1", str(o.get("suivi")))
check("etat_annonce_puis_ok", (o.get("vus") or [None])[0] == "pend" and o.get("etat") == "ok", f"{o.get('vus')}")
check("element_rebranche", str(o.get("src_apres")).startswith("/api/montage/proxy?src=") and o.get("charges") == 1, str(o.get("src_apres")))
check("lecteur_resynchronise_une_fois", o.get("sync") == 1, str(o.get("sync")))
def texte(m):
    return (m or {}).get("p", {}).get("children") or ""
check("etiquette_apercu_480p", "montage.lecteur.codec_ok" in texte(o.get("message_ok")), str(o.get("message_ok")))
check("metadonnees_sans_image_lancent", o.get("m0_post") == 1, str(o.get("m0_post")))
check("refus_serveur_retenu", o.get("m0_etat") == "err" and o.get("m0_msg") == "ffmpeg en panne", f"{o.get('m0_msg')}")
check("message_erreur_nomme_la_raison", "montage.lecteur.codec_err" in texte(o.get("message_err"))
      and "ffmpeg en panne" in texte(o.get("message_err")), str(o.get("message_err")))
check("raison_longue_bornee", 0 < texte(o.get("message_long")).count("x") <= 140, str(len(texte(o.get("message_long")))))
check("source_lisible_rien", o.get("lisible_post") == 0, str(o.get("lisible_post")))
check("calque_rien_son_apercu_existe", o.get("calque_post") == 0, str(o.get("calque_post")))
check("element_evince_rien", o.get("evince_post") == 0, str(o.get("evince_post")))
check("un_seul_apercu_en_vol", o.get("en_vol") == 1 and o.get("apres_vol") == 2, f"{o.get('en_vol')} {o.get('apres_vol')}")
check("message_attente", "montage.lecteur.codec_pend" in texte(o.get("message_attente")), str(o.get("message_attente")))
check("source_connue_va_droit_a_l_apercu", str(o.get("deja_apercu")).startswith("/api/montage/proxy?src="), str(o.get("deja_apercu")))
check("pas_de_message_sans_clip", o.get("message_trou") is None, str(o.get("message_trou")))
check("source_saine_aucun_message", o.get("message_lisible") is None, str(o.get("message_lisible")))

print("\n[4] LECTEUR VIVANT — chaque garde du moniteur et des pistes passe par les aides")
for nom, bout in (("pool_cle", 'function livePoolKey(src,role){return role+svmSrcKey(src)'),
                  ("pool_video", 'if(svW(src)'),
                  ("pool_image", 'el.src=svmSrcUrl(src);'),
                  ("pool_hook", 'it=svG(el,src,role,liveSync);pool.set(key,it);'),
                  ("prechauffe", 'if(c.tr!=="v1"||!c.src||!svW(c.src)'),
                  ("message_moniteur", 'liveOn?r.jsx(svL,{c:liveClip}):null,'),
                  ("onde", 'if(trackKind(tr.id)==="audio"&&svA(c.src)'),
                  ("onde_aud", 'var aud=trackKind(tr.id)==="audio"&&c.src&&svA(c.src)'),
                  ("bande", 'else if(svV(tr.id,c)&&svW(c.src)')):
    check(f"site_{nom}", bout in SRCJS)
check("sites_overlay", SRCJS.count("svI(k.src)") == 1 and SRCJS.count("svI(c.src)") >= 2, str(SRCJS.count("svI(c.src)")))
check("plus_de_garde_job_image", "(c.src.job_id||c.src.image)" not in SRCJS and "(k.src.job_id||k.src.image)" not in SRCJS)
MONTAGEJS = open(os.path.join(REPO, "frontend", "patches", "montage.js"), encoding="utf-8").read()
check("scopes_suivent_le_lecteur", "(k.src.job_id||k.src.image)" not in MONTAGEJS)

print("\n[5] TRADUCTION — clés FR et EN, messages d'erreur, couche servie")
D = json.load(open(os.path.join(REPO, "frontend", "shared", "i18n", "montage_svm.json"), encoding="utf-8"))
for cle in ("montage.lecteur.codec_pend", "montage.lecteur.codec_ok", "montage.lecteur.codec_err"):
    e = D.get(cle) or {}
    check(f"cle_{cle}", bool(e.get("fr")) and bool(e.get("en")) and e["fr"] != e["en"], str(e))
env = dict(os.environ, PYTHONUTF8="1")
r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=env)
check("erreurs_traduites", r.returncode == 0, (r.stdout + r.stderr)[-300:])
r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "i18n_l4_generer.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=env)
check("saisie_l4_a_jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])
BUNDLE = open(os.path.join(REPO, "frontend", "dist", "assets", "index-BEOJX8L5.js"), "rb").read()
check("bundle_porte_le_bloc", "/* ═══════════ t409".encode("utf-8") in BUNDLE and b"it=svG(el,src,role,liveSync);" in BUNDLE)
r = sh([sys.executable, os.path.join(REPO, "scripts", "refresh_layer.py"), "--layer", "sonvfx", "--check"])
check("bundle_couche_sonvfx_a_jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
