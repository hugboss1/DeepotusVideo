# -*- coding: utf-8 -*-
"""t325 tâche 1 (26/10/2026) — les écrans de création de brouillon n'envoient plus le canal X par défaut : le serveur
reprend alors les comptes du projet actif (héritage t307, `POST /api/schedule`). Plan
docs/superpowers/plans/2026-10-26-t325-canaux-preremplis.md, spec 2026-10-25-boite-a-outils-design.md §5.4.
Le maillon de QUEUE scripts/patch_bundle_dzcanauxpre.py (après dzassistant, t308) retire deux défauts, tous deux HORS de
tout bloc de couche __DZ_*_BEGIN__ :
  P1 `__dzSendSched` (Bibliothèque › Envoyer vers › Planificateur, sortie de libsend) : `post.channels||["x"]` ;
  P2 Planificateur › Nouveau post (composant d'origine, fonction A) : `channels:["x"]` dans createScheduledPost.
Son inverse `avant_dzcanauxpre` (backend/tests/_i18n_l1_aide.py) est appelé EN TÊTE de `avant_dzassistant`.
[1] le maillon   marqueur x1, aucun .bak, --check « déjà appliqué », ancres uniques vues d'avant, plus aucun défaut ["x"],
                 hors couche, octets/CRLF, comptes figés ;
[2] sous node    la fonction LIVRÉE __dzSendSched (faux D) : sans canaux, pas de clé channels ; status draft, mode assisted,
                 run_at ISO ; des canaux explicites passent tels quels, un tableau vide part sans clé (1.4) ;
[3] Nouveau post la fonction LIVRÉE A (faux D, ra, ri) : l'objet envoyé n'a ni channels ni champ dupliqué (1.3 : SONDE NODE
                 sur la fonction extraite, plus contrôle textuel exact de la sortie P2) ;
[4] inverse      avant_dzcanauxpre rend la base à l'octet (empreinte), la chaîne reste cohérente (1.5) ;
[5] la route     POST /api/schedule sur données temporaires, avec le corps que P2 envoie maintenant (1.6) : deux comptes du
                 projet actif de B ; aucun projet actif -> ["x"] ; un compte supprimé -> l'autre ; X-Dz-Espace jamais le
                 projet de Deepotus.
Aucun réseau, data-dir isolé.
Run (depuis backend/) : & $PY tests/test_canaux_preremplis.py"""
import asyncio, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcanpre_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
          "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()
import _i18n_l1_aide as AIDE                                        # noqa: E402

NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
MARKER = "/*dzcanauxpre*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
# empreinte du bundle d'AVANT le maillon (HEAD 98bdc347 = t308 ec211e85 pour le bundle), mesurée avant la pose
BASE_SHA256 = "e4c748ee8be9172cc29356a6e0a4f564e36e9c3d25148d3c8852929467dbdf81"

print("\n[1] le maillon")
try:
    import patch_bundle_dzcanauxpre as PM                   # noqa: E402
except Exception as e:                                      # noqa: BLE001
    PM = None
    check("1.0 le maillon patch_bundle_dzcanauxpre existe", False, repr(e))
check("1.1a le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.1b P1 et P2 appliquées : plus aucun défaut [\"x\"] posé par l'écran (channels:[\"x\"], channels||[\"x\"])",
      'channels:["x"]' not in B and 'channels||["x"]' not in B and "||[\"x\"]" not in B,
      f'{B.count(chr(99) + "hannels:" + chr(91) + chr(34) + "x" + chr(34) + chr(93))}')
check("1.1c aucun .bak_dzcanauxpre laissé", not list(ASSETS.glob("*.bak_dzcanauxpre")))
check("1.1d le marqueur est collé à la fin de la sortie P1, sans fin de ligne",
      lambda: PM.PAIRES[0][1].endswith(MARKER) and "\n" not in PM.PAIRES[0][1] and PM.MARKER == MARKER)
if PM:
    src = (REPO / "scripts" / "patch_bundle_dzcanauxpre.py").read_text("utf-8")
    check("1.1e lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzcanauxpre.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.1f --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    try:
        avant = PM.defaire(B) if MARKER in B else ""
    except AssertionError:                                  # maillon partiel : le banc continue et rougit sur le reste
        avant = ""
    check("1.1g chaque ancre une fois dans le bundle d'avant, chaque remplacement une fois dans le livré",
          lambda: all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("1.1h les paires n'ont aucune fin de ligne, n'ajoutent aucun x.useState(",
          all("\n" not in a + z and "x.useState(" not in z for a, z in PM.PAIRES))
    check("1.1i la sonde de précédence compte le marqueur de dzassistant",
          lambda: ("dzassistant", "/*__dzassistant*/", 1) in PM.SONDE_AMONT)

    def hors_couche(jeton, s=B):
        i = s.index(jeton)
        for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s):
            if m.start() <= i <= s.index("/*__DZ_%s_END__*/" % m.group(1)):
                return False
        return True
    check("1.1j les deux cibles sont HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: hors_couche(PM.PAIRES[0][1]) and hors_couche(PM.PAIRES[1][1]))
    check("1.1k aller-retour exact à l'octet : appliquer(defaire(B)) == B, defaire(B) sans marqueur",
          lambda: PM.appliquer(PM.defaire(B)) == B and MARKER not in PM.defaire(B))
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*__dzassistant*/": 1,
                 "function __dzSendSched(": 1}.items():
    check(f"1.2 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("1.2x CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("1.2n node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


def tranche(debut, fin):
    i = B.index(debut)
    return B[i:B.index(fin, i)]


# ── [2] __dzSendSched LIVRÉE sous node ─────────────────────────────────────────────────────────────
print("\n[2] __dzSendSched, la fonction livrée, sous node")
SEND = tranche("function __dzSendSched(", "function __dzExtendClip(")
HARNAIS_SEND = r"""
var captured=[];
var D={createScheduledPost:function(p){captured.push(p);return Promise.resolve(null)}};
var window={alert:function(){},dispatchEvent:function(){}};
function CustomEvent(){}function __dzSendNav(){}function __dzToast(){}function dzT(k){return k}
__FONCTION__
var CAS={sans:{title:"Post — a",source_image:"a.png"},telegram:{title:"t",channels:["telegram"]},
         deux:{title:"d",channels:["x","telegram"]},vide:{title:"v",channels:[]}};
(async function(){
  var R={};
  for(var k in CAS){captured.length=0;__dzSendSched(CAS[k]);await new Promise(function(r){setTimeout(r,5)});
    var o=captured[0];R[k]={cles:Object.keys(o).sort(),channels:o.channels,aCles:Object.prototype.hasOwnProperty.call(o,"channels"),
      status:o.status,mode:o.mode,run_at:o.run_at,titre:o.title};}
  process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R2 = {}
if NODE:
    R2 = node(HARNAIS_SEND.replace("__FONCTION__", SEND))
check("1.2.0 la sonde s'exécute sous node", bool(R2) and "erreur" not in R2, str(R2.get("erreur", ""))[:600])
S = R2.get("sans", {})
check("1.2a sans post.channels : l'objet envoyé n'a PAS de clé channels", S.get("aCles") is False, str(S))
check("1.2b status = draft, mode = assisted", S.get("status") == "draft" and S.get("mode") == "assisted", str(S))
check("1.2c run_at est une date ISO (dans environ 2 h)",
      bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", S.get("run_at", ""))), str(S.get("run_at")))
check("1.2d les autres champs passent (titre, source_image) sans doublon",
      S.get("cles") == ["mode", "run_at", "source_image", "status", "title"], str(S.get("cles")))
check("1.4a canaux explicites [\"telegram\"] : envoyés tels quels", R2.get("telegram", {}).get("channels") == ["telegram"],
      str(R2.get("telegram")))
check("1.4b canaux explicites [\"x\",\"telegram\"] : envoyés tels quels", R2.get("deux", {}).get("channels") == ["x", "telegram"],
      str(R2.get("deux")))
check("1.4c channels:[] : un objet SANS channels (le serveur hérite)", R2.get("vide", {}).get("aCles") is False,
      str(R2.get("vide")))

# ── [3] Nouveau post (fonction A du Planificateur) ──────────────────────────────────────────────────
print("\n[3] Planificateur › Nouveau post, la fonction livrée, sous node")
A_FN = tranche("async function A(M){const U=ra(ri(P,M??0)", "async function V(){")
HARNAIS_A = r"""
var captured=[],selectionnes=[];
var D={createScheduledPost:function(p){captured.push(p);return Promise.resolve({id:"p1"})}};
var ra=function(){return{toISOString:function(){return"2026-12-01T12:00:00.000Z"}}};var ri=function(){return 0};var P=0;
var o=function(){return Promise.resolve()};var u=function(id){selectionnes.push(id)};
__FONCTION__
(async function(){
  await A(2);
  var p=captured[0];
  process.stdout.write(JSON.stringify({objet:p,cles:Object.keys(p).sort(),aCles:Object.prototype.hasOwnProperty.call(p,"channels"),
    selectionnes:selectionnes,appels:captured.length}));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R3 = {}
if NODE:
    R3 = node(HARNAIS_A.replace("__FONCTION__", A_FN))
check("1.3.0 la sonde s'exécute sous node (un seul appel à createScheduledPost)",
      bool(R3) and "erreur" not in R3 and R3.get("appels") == 1, str(R3.get("erreur", R3))[:600])
check("1.3a l'objet envoyé n'a PAS de clé channels", R3.get("aCles") is False, str(R3.get("objet")))
check("1.3b ni champ perdu ni champ dupliqué : exactement caption, mode, run_at, status, title",
      R3.get("cles") == ["caption", "mode", "run_at", "status", "title"], str(R3.get("cles")))
check("1.3c valeurs : titre d'origine, légende vide, brouillon assisté, date ISO",
      R3.get("objet") == {"title": "Untitled post", "caption": "", "run_at": "2026-12-01T12:00:00.000Z",
                          "status": "draft", "mode": "assisted"}, str(R3.get("objet")))
check("1.3d l'éditeur s'ouvre toujours sur le post créé (u(id))", R3.get("selectionnes") == ["p1"], str(R3.get("selectionnes")))
check("1.3e contrôle textuel exact de la sortie : « channels » n'apparaît plus dans la fonction, et l'objet est exact",
      "channels" not in A_FN and 'D.createScheduledPost({title:"Untitled post",caption:"",run_at:U.toISOString(),'
      'status:"draft",mode:"assisted"})' in A_FN)

# ── [4] l'inverse ──────────────────────────────────────────────────────────────────────────────────────
print("\n[4] l'inverse avant_dzcanauxpre")
if PM and MARKER in B:
    check("1.5a avant_dzcanauxpre existe et rend defaire(B)", lambda: AIDE.avant_dzcanauxpre(B) == PM.defaire(B))
    check("1.5b la base est rendue À L'OCTET (empreinte du bundle d'avant le maillon)",
          lambda: hashlib.sha256(AIDE.avant_dzcanauxpre(B).encode("utf-8")).hexdigest() == BASE_SHA256)
    check("1.5c sans marqueur : rendu tel quel", lambda: AIDE.avant_dzcanauxpre(PM.defaire(B)) == PM.defaire(B))
    check("1.5d avant_dzassistant défait dzcanauxpre d'abord, puis dzassistant (chaîne cohérente)",
          lambda: MARKER not in AIDE.avant_dzassistant(B) and "/*__dzassistant*/" not in AIDE.avant_dzassistant(B)
          and AIDE.avant_dzassistant(B) == AIDE.avant_dzassistant(AIDE.avant_dzcanauxpre(B)))
    check("1.5e avant_dzagentplan défait aussi dzcanauxpre",
          lambda: MARKER not in AIDE.avant_dzagentplan(B) and "/*__dzagentplan*/" not in AIDE.avant_dzagentplan(B))
    check("1.5f l'inverse garde le défaut X dans la base (le maillon l'a bien retiré)",
          lambda: 'channels:["x"]' in AIDE.avant_dzcanauxpre(B) and 'channels||["x"]' in AIDE.avant_dzcanauxpre(B))
    check("1.5g CRLF préservé (en octets)",
          lambda: AIDE.avant_dzcanauxpre(B).encode("utf-8").count(b"\n") == AIDE.avant_dzcanauxpre(B).encode("utf-8").count(b"\r\n"))
else:
    check("1.5 l'inverse a un maillon posé à défaire", False, "maillon absent")

# ── [5] la route, avec le corps que P2 envoie maintenant ─────────────────────────────────────────────
print("\n[5] POST /api/schedule avec le corps de Nouveau post (sans channels)")
CORPS = R3.get("objet") or {"title": "Untitled post", "caption": "", "run_at": "2026-12-01T12:00:00.000Z",
                            "status": "draft", "mode": "assisted"}
from app.services import comptes, espaces, storage                  # noqa: E402
from app.services import library_projects as LP                     # noqa: E402
_loop = asyncio.new_event_loop()


def run(coro):
    return _loop.run_until_complete(coro)


run(storage.init_db())
espaces.lire()
EB = espaces.creer({"nom": "Client B"})["id"]
EC = espaces.creer({"nom": "Client C sans projet"})["id"]
c_deep = comptes.creer({"espace_id": "deepotus", "plateforme": "x", "libelle": "Deepotus X"})["id"]
cb_tg = comptes.creer({"espace_id": EB, "plateforme": "telegram", "libelle": "B Telegram"})["id"]
cb_x = comptes.creer({"espace_id": EB, "plateforme": "x", "libelle": "B X"})["id"]
pd = run(LP.creer("Projet Deepotus"))
run(LP.poser_canaux(pd["id"], [c_deep]))
run(LP.poser_actif(pd["id"]))
with espaces.sous_espace(EB):
    pb = run(LP.creer("Projet de B"))
    run(LP.poser_actif(pb["id"]))
run(LP.poser_canaux(pb["id"], [cb_tg, cb_x]))
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    def post(espace=None, corps=None):
        return client.post("/api/schedule", json=dict(corps or CORPS), headers={"X-Dz-Espace": espace} if espace else {})
    r = post(EB)
    check("1.6a le projet actif de B a deux comptes : le post a ces deux comptes, channels = leurs plateformes",
          r.status_code == 200 and r.json().get("comptes") == [cb_tg, cb_x] and r.json().get("channels") == ["telegram", "x"],
          r.text[:300])
    check("1.6b ... et c'est bien un post de l'espace B", r.json().get("espace_id") == EB, r.text[:200])
    r = post(EC)
    check("1.6c aucun projet actif (espace C) : channels = [\"x\"], aucun compte, sans erreur",
          r.status_code == 200 and r.json().get("channels") == ["x"] and not r.json().get("comptes"), r.text[:300])
    r = post()
    check("1.6d sans en-tête : le projet de Deepotus (jamais celui de B)",
          r.status_code == 200 and r.json().get("comptes") == [c_deep], r.text[:300])
    check("1.6e X-Dz-Espace: B ne prend jamais le projet de Deepotus", c_deep not in (post(EB).json().get("comptes") or []))
    comptes.supprimer(cb_x)
    r = post(EB)
    check("1.6f un compte du projet supprimé : le post est créé sur l'autre, sans erreur",
          r.status_code == 200 and r.json().get("comptes") == [cb_tg] and r.json().get("channels") == ["telegram"], r.text[:300])
    comptes.supprimer(cb_tg)
    r = post(EB)
    check("1.6g tous les comptes supprimés : le post est créé sur X (repli), sans erreur",
          r.status_code == 200 and r.json().get("channels") == ["x"] and not r.json().get("comptes"), r.text[:300])
    # ce que l'ANCIEN écran envoyait (channels:["x"]) court-circuitait l'héritage : le banc 1.6 en dépend
    r = post(EB, dict(CORPS, channels=["x"]))
    check("1.6h (témoin) un corps AVEC channels:[\"x\"] n'hérite de rien : c'est ce que P2 retire",
          r.status_code == 200 and not r.json().get("comptes"), r.text[:300])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
