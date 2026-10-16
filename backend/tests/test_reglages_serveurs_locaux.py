# -*- coding: utf-8 -*-
"""t223 (Menus : Réglages, 16/10/2026) — LLM local : plusieurs serveurs. Banc SERVEUR (l'écran a son banc à part :
test_reglages_serveurs_locaux_ecran.py).

Remontée de l'utilisateur (15/10) : « LLM local : pouvoir ajouter d'autres lignes de serveur (URL), pas un seul
Ollama ». Zéro réseau, aucune clé réelle : le transport httpx de `serveurs_locaux` est un FAUX SERVEUR OLLAMA
(127.0.0.1:11434, GET /api/tags, POST /api/chat) ET un FAUX SERVEUR COMPATIBLE OPENAI (192.168.1.20:1234,
GET /v1/models, POST /v1/chat/completions ; 10.0.0.7:8000 exige une clé), en mémoire ; la résolution DNS est remplacée.
Ce que ce banc garde :
  [U] l'URL : http(s) ; ni identifiants, ni requête, ni fragment ; boucle locale et réseau privé PERMIS, adresse
      publique, lien local (169.254.x, fe80::), non spécifiée et multicast REFUSÉS ; un nom qui résout vers une
      adresse publique est refusé à l'appel ; « /v1 » ajouté à un serveur OpenAI sans chemin ;
  [S] la garde de fournisseurs_llm reste REFUSANTE pour fl:<id> (privé et http refusés) : l'assouplissement est ici ;
  [M] migration : OLLAMA_URL / OLLAMA_MODEL = la première ligne, lue telle quelle, .env inchangé à l'octet ; le moteur
      `ollama` garde son id ; la première ligne ne se supprime ni ne se modifie ici ;
  [C] créer / modifier / supprimer : fichier sans secret ; clé (OpenAI seulement) au .env sous DZL_<ID>_API_KEY, jamais
      renvoyée ; coffre fermé → 409 ; modèle qui ressemble à une clé → 400 ; 20 serveurs au plus ; id « ollama » réservé ;
  [L] « Lire les modèles » : Ollama /api/tags, OpenAI /models (Bearer seulement s'il y a une clé), texte seulement ;
      refus dit « HTTP 401 » sans recopier ; aucune redirection suivie ;
  [T] « Tester » : ok / refus, aucun POST (rien généré), la première ligne aussi ;
  [R] le registre : tous() = intégrés, fl:<id>, local:<id> ; configure = un modèle ; etat() ;
  [V] Vectorlab : local:<id> listé et tiré (POST /api/chat ou /chat/completions au modèle choisi) ;
  [P] prix : un serveur local est GRATUIT (0, pas a_mesurer), le plafond ne le bloque pas ;
  [D] Fournisseurs par défaut : rôles résumé / planificateur, dispatch, modèle par défaut (fichier), /modeles, /tester ;
  [K] /api/ia/catalogue?nature=texte : … puis local:<id>, voie local, usd 0, note vide ;
  [F] Card Forge : local:<id> accepté, gratuit ; [G] Diagnostic : une ligne par serveur ;
  [X] écriture et lecture refusées depuis un autre appareil ; paquet d'espace sans rien d'ici ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_traductions.json).
Run (depuis backend/) : & $PY tests/test_reglages_serveurs_locaux.py"""
import asyncio, json, os, pathlib, socket, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "OLLAMA_URL", "SUMMARIZER_PROVIDER",
           "PLANNER_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
ENV0 = "# fichier de l'utilisateur\nOLLAMA_URL=http://127.0.0.1:11434\nOLLAMA_MODEL=qwen2.5:14b-instruct\n"
(_tmp / ".env").write_text(ENV0, encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import serveurs_locaux as SL                      # noqa: E402
from app.services import fournisseurs_llm as FL                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import vector_illustration as VI                  # noqa: E402
from app.services import pricing as PR, plafonds as PLAF            # noqa: E402
import app.api.settings_routes as SR                                # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "",
               "OLLAMA_URL": "http://127.0.0.1:11434", "OLLAMA_MODEL": "qwen2.5:14b-instruct",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


# ── les faux serveurs (en mémoire) ────────────────────────────────────────────────────────────────────────────────
CLE = "sk-faussecle-banc-t223-0000000000"
REQ = []
REPONSE = {"texte": "Réponse du faux serveur."}


def _faux(req: httpx.Request) -> httpx.Response:
    REQ.append(req)
    hote, port, chemin = req.url.host, req.url.port, req.url.path
    hote = {"nas.local": "192.168.1.20", "monpc": "10.0.0.7"}.get(hote, hote)     # le nom tel que le faux DNS le résout
    if (hote, port) == ("127.0.0.1", 11434):                        # Ollama natif
        if req.method == "GET" and chemin == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:14b-instruct"}, {"name": "llama3.2:3b"},
                                                        {"name": "nomic-embed-text:latest"}]})
        if req.method == "POST" and chemin == "/api/chat":
            corps = json.loads(req.content)
            return httpx.Response(200, json={"message": {"role": "assistant",
                                                         "content": REPONSE["texte"] + " [" + corps["model"] + "]"},
                                             "done": True})
        return httpx.Response(404, json={})
    if (hote, port) in (("192.168.1.20", 1234), ("10.0.0.7", 8000)):  # compatible OpenAI (le second exige la clé)
        if port == 8000 and req.headers.get("authorization") != f"Bearer {CLE}":
            return httpx.Response(401, json={"error": f"bad key {req.headers.get('authorization')}"})
        if req.method == "GET" and chemin == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": [{"id": "qwen2.5-7b-instruct"},
                                                                        {"id": "text-embedding-nomic"},
                                                                        {"id": "llama-3.2-3b"}]})
        if req.method == "POST" and chemin == "/v1/chat/completions":
            corps = json.loads(req.content)
            return httpx.Response(200, json={"choices": [{"message": {"role": "assistant",
                                                                      "content": REPONSE["texte"] + " [" + corps["model"] + "]"}}]})
        return httpx.Response(404, json={})
    if (hote, port) == ("127.0.0.1", 9999):                          # redirige vers une adresse publique
        return httpx.Response(302, headers={"location": "http://93.184.216.34/api/tags"})
    return httpx.Response(599, json={"inattendu": str(req.url)})


SL._TRANSPORT = httpx.MockTransport(_faux)


def _faux_dns(hote, port, *a, **k):
    table = {"nas.local": "192.168.1.20", "monpc": "10.0.0.7", "public.exemple.test": "93.184.216.34",
             "mixte.exemple.test": None}
    if hote in table:
        if table[hote] is None:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", port)),
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (table[hote], port))]
    if hote == "absent.local":
        raise socket.gaierror("introuvable")
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (hote.strip("[]"), port))]


SL._resoudre = _faux_dns

c = TestClient(app)
c.__enter__()


def env():
    return (_tmp / ".env").read_text(encoding="utf-8")


def fichier():
    f = _tmp / "serveurs_locaux.json"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


# ── [U] l'URL ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[U] URL")
check("U1 Ollama : « / » final retiré, chemin gardé vide", SL.verifier_url(" http://127.0.0.1:11434/ ", "ollama") == "http://127.0.0.1:11434")
check("U1b OpenAI sans chemin : « /v1 » ajouté ; avec chemin : gardé",
      SL.verifier_url("http://192.168.1.20:1234", "openai") == "http://192.168.1.20:1234/v1"
      and SL.verifier_url("http://localhost:8080/v1/", "openai") == "http://localhost:8080/v1")
permis = [("http://localhost:11434", "ollama"), ("http://127.0.0.1:1234/v1", "openai"), ("http://10.0.0.5:8000/v1", "openai"),
          ("http://172.16.4.2:11434", "ollama"), ("https://[::1]:8443/v1", "openai"), ("http://[fd00::5]:1234/v1", "openai"),
          ("http://nas.local:11434", "ollama"), ("http://monpc:8000/v1", "openai")]
mauvais = [u for u, t in permis if not SL.verifier_url(u, t)]
check(f"U2 {len(permis)} URL locales ou privées permises (boucle, 10/8, 172.16/12, ::1, fd00::, .local, nom court)", not mauvais, mauvais)
refus = ["ftp://127.0.0.1", "http://user:pw@127.0.0.1:11434", "http://127.0.0.1:11434?x=1", "http://127.0.0.1:11434#a",
         "http://8.8.8.8:11434", "http://93.184.216.34", "http://169.254.169.254/latest", "http://[fe80::1]:11434",
         "http://0.0.0.0:11434", "http://224.0.0.1", "http://[2001:4860::8888]", "", "http://"]
passent = []
for u in refus:
    try:
        SL.verifier_url(u, "ollama")
        passent.append(u)
    except ValueError:
        pass
check(f"U3 {len(refus)} URL refusées (schéma, identifiants, requête, publique, lien local, non spécifiée, multicast)",
      not passent, passent)
try:
    SL.verifier_url("http://127.0.0.1:11434", "grpc")
    check("U4 type inconnu refusé", False)
except ValueError:
    check("U4 type inconnu refusé", True)
for hote in ("public.exemple.test", "mixte.exemple.test", "absent.local"):
    try:
        SL._hote_local(f"http://{hote}:11434")
        check(f"U5 {hote} : refusé à l'appel (résout hors du réseau local, ou introuvable)", False)
    except ValueError:
        check(f"U5 {hote} : refusé à l'appel (résout hors du réseau local, ou introuvable)", True)
SL._hote_local("http://nas.local:11434")
check("U6 nas.local (192.168.1.20) passe à l'appel", True)

# ── [S] la garde de t222 reste refusante ──────────────────────────────────────────────────────────────────────────
print("[S] garde fl:")
refuse_fl = []
for u in ("https://127.0.0.1/v1", "https://192.168.1.20/v1", "http://api.exemple.test/v1", "https://nas.local/v1",
          "https://monpc/v1"):
    try:
        FL.verifier_base(u)
        refuse_fl.append(u)
    except ValueError:
        pass
check("S1 fournisseurs_llm refuse toujours local, privé, http, .local et nom court", not refuse_fl, refuse_fl)
check("S2 _adresse_privee de fournisseurs_llm reste refusante (10.0.0.7, ::1 = privées → refus)",
      FL._adresse_privee("10.0.0.7") and FL._adresse_privee("::1") and not FL._adresse_privee("93.184.216.34"))
_src_sl = (RACINE / "backend" / "app" / "services" / "serveurs_locaux.py").read_text(encoding="utf-8")
check("S3 serveurs_locaux ne touche pas la garde de fournisseurs_llm (aucune affectation FL.*)",
      "fournisseurs_llm" not in _src_sl.replace("`fournisseurs_llm` (`_adresse_privee`, refusante)", ""))

# ── [X] autre appareil ────────────────────────────────────────────────────────────────────────────────────────────
print("[X] autre appareil")
cd = TestClient(app, client=("192.168.1.50", 5000))
r = cd.post("/api/reglages/serveurs-locaux", json={"url": "http://192.168.1.20:1234", "type": "openai", "cle": CLE})
check("X1 créer depuis un autre appareil → refusé, rien d'écrit", r.status_code in (401, 403) and not fichier()
      and CLE not in env(), r.status_code)
check("X1b lire depuis un autre appareil → refusé", cd.get("/api/reglages/serveurs-locaux").status_code in (401, 403))
import ast as _ast                                                  # noqa: E402
_sr = _ast.parse((RACINE / "backend" / "app" / "api" / "settings_routes.py").read_text(encoding="utf-8"))
_sl = [f for f in _sr.body if isinstance(f, _ast.AsyncFunctionDef) and any(
    isinstance(d, _ast.Call) and d.args and isinstance(d.args[0], _ast.Constant)
    and "serveurs-locaux" in str(d.args[0].value) for d in f.decorator_list)]
_sans = [f.name for f in _sl if not any(isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "_local"
                                        for st in f.body[:3] for n in _ast.walk(st))]
check(f"X1c les {len(_sl)} routes serveurs-locaux appellent _local d'entrée", len(_sl) == 6 and not _sans, _sans)

# ── [M] migration : la première ligne ─────────────────────────────────────────────────────────────────────────────
print("[M] migration")
env_avant = (_tmp / ".env").read_bytes()
r = c.get("/api/reglages/serveurs-locaux")
l0 = (r.json().get("serveurs") or [{}])[0]
check("M1 première ligne = OLLAMA_URL / OLLAMA_MODEL lus TELS QUELS, moteur ollama, intégrée",
      r.status_code == 200 and l0.get("id") == "ollama" and l0.get("moteur") == "ollama" and l0.get("type") == "ollama"
      and l0.get("url") == settings.OLLAMA_URL == "http://127.0.0.1:11434" and l0.get("defaut") == "qwen2.5:14b-instruct"
      and l0.get("integre") is True and len(r.json()["serveurs"]) == 1, r.text[:300])
check("M2 GET n'écrit rien : .env identique à l'octet, aucun fichier serveurs_locaux.json",
      (_tmp / ".env").read_bytes() == env_avant and not fichier())
check("M3 4 préréglages (Ollama, LM Studio, llama.cpp, vLLM)", [p["nom"] for p in r.json()["prereglages"]]
      == ["Ollama", "LM Studio", "llama.cpp", "vLLM"])
check("M4 supprimer la première ligne → 400 ; modifier → 400 ; .env intact",
      c.delete("/api/reglages/serveurs-locaux/ollama").status_code == 400
      and c.post("/api/reglages/serveurs-locaux/ollama", json={"url": "http://10.0.0.1"}).status_code == 400
      and (_tmp / ".env").read_bytes() == env_avant)
CAC.appliquer({"OLLAMA_MODEL": "AIzaUneCleColleeIci0000000000000000"})
l0f = SL.lister()[0]
check("M5 un OLLAMA_MODEL fautif (clé collée) n'est jamais montré : défaut vide, fautif", l0f["defaut"] == ""
      and l0f["fautif"] is True and "AIza" not in json.dumps(l0f))
CAC.appliquer({"OLLAMA_MODEL": "qwen2.5:14b-instruct"})

# ── [C] créer ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[C] créer / modifier / supprimer")
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://93.184.216.34:11434", "type": "ollama"})
check("C1 adresse publique → 400, rien d'écrit", r.status_code == 400 and not fichier(), r.text[:160])
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://127.0.0.1:11434", "type": "ollama", "cle": CLE})
check("C2 une clé pour un serveur Ollama → 400, rien d'écrit", r.status_code == 400 and not fichier() and CLE not in env())
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://127.0.0.1:11434", "type": "ollama",
                                                   "modeles": "llama3.2:3b, sk-uneclecolleeaulieudunmodele"})
check("C3 un modèle qui ressemble à une clé → 400", r.status_code == 400 and not fichier())
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://127.0.0.1:11434", "type": "ollama", "nom": "Ollama",
                                                   "defaut": "llama3.2:3b"})
v = r.json().get("serveur") or {}
check("C4 nom « Ollama » : id ollama2 (« ollama » est la première ligne), moteur local:ollama2, sans clé",
      r.status_code == 200 and v.get("id") == "ollama2" and v.get("moteur") == "local:ollama2" and v.get("type") == "ollama"
      and v.get("defaut") == "llama3.2:3b" and v.get("cle") == "" and v.get("cle_posee") is False, r.text[:300])
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://nas.local:1234", "type": "openai", "nom": "LM Studio",
                                                   "modeles": ["qwen2.5-7b-instruct", "llama-3.2-3b"]})
v = r.json().get("serveur") or {}
check("C5 LM Studio : url normalisée (/v1), moteur local:lmstudio, défaut = premier modèle",
      v.get("id") == "lmstudio" and v.get("url") == "http://nas.local:1234/v1" and v.get("defaut") == "qwen2.5-7b-instruct"
      and v.get("cle") == "DZL_LMSTUDIO_API_KEY" and v.get("cle_posee") is False, r.text[:300])
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://monpc:8000", "type": "openai", "nom": "vLLM",
                                                   "cle": CLE, "defaut": "qwen2.5-7b-instruct"})
v = r.json().get("serveur") or {}
check("C6 vLLM avec clé : la réponse ne contient PAS la clé, cle_posee, clé au .env sous DZL_VLLM_API_KEY",
      r.status_code == 200 and CLE not in r.text and v.get("cle_posee") is True and f"DZL_VLLM_API_KEY={CLE}" in env()
      and os.environ.get("DZL_VLLM_API_KEY") == CLE, r.text[:300])
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://[::1]:8080", "type": "openai"})
v = r.json().get("serveur") or {}
check("C7 sans nom : nom par défaut lisible (type + hôte), id tiré du nom", r.status_code == 200
      and v.get("nom") == "OpenAI ::1:8080" and v.get("id") == "openai18080" and v.get("url") == "http://[::1]:8080/v1", r.text[:300])
doc = json.loads(fichier())
check("C8 serveurs_locaux.json n'a AUCUN secret, ni la première ligne",
      CLE not in fichier() and "ollama" not in doc["serveurs"]
      and set(doc["serveurs"]["vllm"]) == {"nom", "type", "url", "modeles", "defaut", "cree"}, fichier()[:300])
r = c.get("/api/reglages/serveurs-locaux")
check("C9 GET : première ligne puis les 4 ajoutés, sans la clé", [s["id"] for s in r.json()["serveurs"]]
      == ["ollama", "ollama2", "lmstudio", "vllm", "openai18080"] and CLE not in r.text)
r = c.post("/api/reglages/serveurs-locaux/lmstudio", json={"defaut": "mon-modele", "nom": "LM Studio (NAS)"})
v = r.json().get("serveur") or {}
check("C10 modifier : défaut saisi librement en tête, nom changé, type gardé", r.status_code == 200
      and v["defaut"] == "mon-modele" and v["modeles"][0] == "mon-modele" and v["nom"] == "LM Studio (NAS)"
      and v["type"] == "openai", r.text[:200])
r = c.post("/api/reglages/serveurs-locaux/lmstudio", json={"url": "http://8.8.8.8:1234"})
check("C11 modifier vers une adresse publique → 400", r.status_code == 400 and "8.8.8.8" not in fichier())
check("C12 serveur inconnu → 404", c.post("/api/reglages/serveurs-locaux/inconnu", json={"nom": "x"}).status_code == 404)
from app.services import coffre as CF                                # noqa: E402
_vp = CF.verrouille
CF.verrouille = lambda: True
avant = fichier()
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://10.0.0.7:8000", "type": "openai", "cle": CLE})
check("C13 coffre fermé : créer AVEC clé → 409, rien d'écrit", r.status_code == 409 and fichier() == avant, r.status_code)
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://10.0.0.8:11434", "type": "ollama", "nom": "Sans clé"})
check("C14 coffre fermé : un serveur SANS clé s'ajoute quand même", r.status_code == 200, r.status_code)
c.delete("/api/reglages/serveurs-locaux/" + ((r.json().get("serveur") or {}).get("id") or "x"))
CF.verrouille = _vp

# ── [L] lire les modèles ──────────────────────────────────────────────────────────────────────────────────────────
print("[L] lire les modèles")
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"id": "ollama"})
check("L1 première ligne : GET OLLAMA_URL/api/tags, texte seulement (embeddings écartés), trié",
      r.status_code == 200 and r.json()["modeles"] == ["llama3.2:3b", "qwen2.5:14b-instruct"]
      and len(REQ) == 1 and str(REQ[0].url) == "http://127.0.0.1:11434/api/tags", r.text[:200])
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"id": "lmstudio"})
check("L2 compatible OpenAI : GET {url}/models SANS en-tête Authorization (pas de clé)",
      r.status_code == 200 and r.json()["modeles"] == ["llama-3.2-3b", "qwen2.5-7b-instruct"]
      and str(REQ[0].url) == "http://nas.local:1234/v1/models" and "authorization" not in REQ[0].headers, r.text[:200])
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"id": "vllm"})
check("L3 avec clé : Bearer envoyé, liste lue", r.status_code == 200 and r.json()["modeles"]
      and REQ[0].headers.get("authorization") == f"Bearer {CLE}", r.text[:200])
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"url": "http://10.0.0.7:8000", "type": "openai",
                                                                "cle": "sk-mauvaise"})
check("L4 clé refusée : 400 « HTTP 401 », sans recopier la réponse du serveur",
      r.status_code == 400 and "401" in r.text and "sk-mauvaise" not in r.text and "bad key" not in r.text, r.text[:200])
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"url": "http://192.168.1.20:1234", "type": "openai"})
check("L5 avant création (url + type) : la liste se lit, rien n'est écrit", r.status_code == 200
      and r.json()["modeles"] == ["llama-3.2-3b", "qwen2.5-7b-instruct"] and "192.168.1.20:1234\"" not in fichier())
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"url": "http://127.0.0.1:9999", "type": "ollama"})
check("L6 une redirection n'est PAS suivie (refus, une seule requête, rien vers l'adresse publique)",
      r.status_code == 400 and "302" in r.text and len(REQ) == 1 and all("93.184" not in str(q.url) for q in REQ), r.text[:200])
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/lire-modeles", json={"url": "http://public.exemple.test:11434", "type": "ollama"})
check("L7 nom qui résout vers une adresse publique : 400, aucune requête partie", r.status_code == 400 and not REQ, r.text[:200])

# ── [T] tester ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[T] tester")
REQ.clear()
r = c.post("/api/reglages/serveurs-locaux/ollama/tester")
check("T1 première ligne : ok, 2 modèles, défaut publié, aucun POST", r.status_code == 200 and r.json()["etat"] == "ok"
      and r.json()["n"] == 2 and r.json()["defaut_publie"] is True and all(q.method == "GET" for q in REQ), r.text[:200])
r = c.post("/api/reglages/serveurs-locaux/lmstudio/tester")
check("T2 LM Studio : ok, défaut « mon-modele » NON publié", r.json()["etat"] == "ok" and r.json()["defaut_publie"] is False, r.text)
SL.modifier("vllm", {"cle": "sk-autre-cle-fausse-00000"})
r = c.post("/api/reglages/serveurs-locaux/vllm/tester")
check("T3 clé refusée : etat refus, cause HTTP 401 sans la clé", r.json()["etat"] == "refus" and "401" in r.json()["cause"]
      and "sk-autre" not in r.text, r.text)
SL.modifier("vllm", {"cle": CLE})
check("T4 serveur inconnu → 404", c.post("/api/reglages/serveurs-locaux/inconnu/tester").status_code == 404)

# ── [R] le registre ───────────────────────────────────────────────────────────────────────────────────────────────
print("[R] registre")
check("R1 MOTEURS (intégrés) inchangés", MT.MOTEURS == ("anthropic", "openai", "gemini", "ollama"))
check("R2 tous() = intégrés puis local:<id> (aucun fl: ici)", MT.tous() == ["anthropic", "openai", "gemini", "ollama",
      "local:ollama2", "local:lmstudio", "local:vllm", "local:openai18080"], MT.tous())
check("R3 configure : un modèle suffit (openai18080 sans modèle : non)", MT.configure("local:ollama2")
      and MT.configure("local:lmstudio") and not MT.configure("local:openai18080"))
et = {e["moteur"]: e for e in MT.etat()}
check("R4 etat() : ligne local, nom, modèle", et.get("local:lmstudio", {}).get("local") is True
      and et["local:lmstudio"]["nom"] == "LM Studio (NAS)" and et["local:lmstudio"]["modele"] == "mon-modele", et.get("local:lmstudio"))
check("R5 connu / est_local", MT.connu("local:vllm") and not MT.connu("local:inconnu") and MT.est_local("local:x")
      and not MT.est_local("ollama") and not MT.est_libre("local:vllm"))
c.post("/api/reglages/serveurs-locaux/lmstudio", json={"defaut": "qwen2.5-7b-instruct"})

# ── [V] Vectorlab ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] Vectorlab")
CAC.appliquer({"OLLAMA_MODEL": ""})       # le moteur intégré `ollama` lirait le vrai réseau : retiré le temps du Vectorlab
VI._CATALOGUE.clear()
r = c.get("/api/vector/illustration/moteurs")
mo = {m["moteur"]: m for m in r.json().get("moteurs", [])}
check("V1 /vector/illustration/moteurs : local:lmstudio et sa liste (défaut en tête), pas openai18080 (sans modèle)",
      "local:lmstudio" in mo and mo["local:lmstudio"]["modeles"][0] == "qwen2.5-7b-instruct"
      and "local:ollama2" in mo and "local:openai18080" not in mo, r.text[:300])
REQ.clear()
REPONSE["texte"] = '<svg viewBox="0 0 10 10"><rect x="1" y="1" width="4" height="4" fill="#f00"/></svg>'
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "local:ollama2", "model": "qwen2.5:14b-instruct"})
post = [q for q in REQ if q.method == "POST"]
check("V2 Ollama : POST {url}/api/chat au modèle choisi, stream false", r.status_code == 200 and len(post) == 1
      and str(post[0].url) == "http://127.0.0.1:11434/api/chat" and json.loads(post[0].content)["model"] == "qwen2.5:14b-instruct"
      and json.loads(post[0].content)["stream"] is False and r.json()["provider"] == "local:ollama2", r.text[:300])
REQ.clear()
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "local:vllm", "model": "llama-3.2-3b"})
post = [q for q in REQ if q.method == "POST"]
check("V3 compatible OpenAI : POST {url}/chat/completions, Bearer de sa clé", r.status_code == 200 and len(post) == 1
      and str(post[0].url) == "http://monpc:8000/v1/chat/completions" and json.loads(post[0].content)["model"] == "llama-3.2-3b"
      and post[0].headers.get("authorization") == f"Bearer {CLE}", r.text[:300])
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "local:openai18080"})
check("V4 serveur sans modèle : 400 indisponible", r.status_code == 400)
CAC.appliquer({"OLLAMA_MODEL": "qwen2.5:14b-instruct"})

# ── [P] prix ──────────────────────────────────────────────────────────────────────────────────────────────────────
print("[P] prix")
dv = PR.estimate(PLAF.op_llm(1_000_000, 1_000_000, "local:lmstudio"))
lig = dv["breakdown"][0]
check("P1 un serveur local est GRATUIT : total 0, ligne local:lmstudio, pas a_mesurer",
      dv["total_usd"] == 0 and lig["provider"] == "local:lmstudio" and "a_mesurer" not in lig, dv)
check("P2 un fournisseur libre reste « à mesurer » (jamais gratuit)", PR.estimate(PLAF.op_llm(10, 10, "fl:x"))["breakdown"][0].get("a_mesurer") is True)
PLAF.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
REQ.clear()
REPONSE["texte"] = '<svg viewBox="0 0 10 10"><rect x="1" y="1" width="4" height="4" fill="#f00"/></svg>'
CAC.appliquer({"OLLAMA_MODEL": ""})
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "local:lmstudio"})
check("P3 le plafond ne bloque pas un serveur local (gratuit) : 200", r.status_code == 200, r.text[:200])
CAC.appliquer({"OLLAMA_MODEL": "qwen2.5:14b-instruct"})
PLAF.enregistrer({"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80})

# ── [D] Fournisseurs par défaut ───────────────────────────────────────────────────────────────────────────────────
print("[D] Fournisseurs par défaut")
d = c.get("/api/settings/provider-defaults").json()
check("D1 les rôles proposent local:lmstudio (prêt), pas openai18080", "local:lmstudio" in d["roles"]["summarizer"]["available"]
      and "local:lmstudio" in d["roles"]["planner"]["available"] and "local:openai18080" not in d["roles"]["planner"]["available"], d["roles"])
check("D1b moteurs : la ligne local:lmstudio", any(m["moteur"] == "local:lmstudio" for m in d["moteurs"]))
r = c.post("/api/settings/provider-defaults", json={"summarizer": "local:lmstudio", "planner": "local:ollama2"})
check("D2 rôles → local:<id> écrits au .env", r.status_code == 200 and "SUMMARIZER_PROVIDER=local:lmstudio" in env()
      and settings.PLANNER_PROVIDER == "local:ollama2", r.text[:200])
check("D3 local:inconnu → 400", c.post("/api/settings/provider-defaults", json={"summarizer": "local:inconnu"}).status_code == 400)
from app.services import summarizer as SZ, marketing as MK         # noqa: E402
REQ.clear()
REPONSE["texte"] = "Texte du faux serveur."
out, p = SZ._chat_dispatch("bonjour", "sys", 50)
check("D4 _chat_dispatch tire le serveur local actif", p == "local:lmstudio" and out and "qwen2.5-7b-instruct" in out
      and str([q for q in REQ if q.method == "POST"][0].url) == "http://nas.local:1234/v1/chat/completions", (out, p))
txt = SZ.summarize("x" * 200, title="T", language="FR")
check("D5 summarize passe par le serveur local", txt and "Texte du faux serveur" in txt, txt)
check("D6 op_llm suit le rôle (local:lmstudio) : devis 0", PLAF.op_llm(10, 10)["provider"] == "local:lmstudio"
      and PR.estimate(PLAF.op_llm(5000, 5000))["total_usd"] == 0)
check("D7 planificateur : local:ollama2 disponible et dans l'ordre", MK._plan_available("local:ollama2")
      and "local:ollama2" in MK._moteurs_plan() and not MK._plan_available("local:openai18080"))
REPONSE["texte"] = json.dumps({"posts": [{"day_offset": 0, "time": "10:00", "title": "A", "caption": "Bonjour",
                                          "channels": ["x"]}]})
plan = asyncio.run(MK.generate_plan("une semaine", days=1, posts_per_day=1))
check("D8 generate_plan par local:ollama2 (POST /api/chat)", plan.get("engine") == "local:ollama2", plan.get("engine"))
r = c.post("/api/settings/provider-defaults", json={"modeles": {"local:lmstudio": "llama-3.2-3b"}})
check("D9 modèle par défaut d'un serveur local : écrit au fichier (pas au .env)", r.status_code == 200
      and SL.obtenir("lmstudio")["defaut"] == "llama-3.2-3b" and "llama-3.2-3b" not in env(), r.text[:200])
r = c.post("/api/settings/provider-defaults", json={"modeles": {"local:lmstudio": "sk-uneclecollee"}})
check("D10 modèle qui ressemble à une clé → 400", r.status_code == 400 and SL.obtenir("lmstudio")["defaut"] == "llama-3.2-3b")
r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "local:lmstudio"})
check("D11 /modeles?moteur=local:lmstudio : sa liste, défaut en tête", r.status_code == 200
      and r.json()["modeles"][0] == "llama-3.2-3b" and r.json()["configure"] is True, r.text[:200])
r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "local:lmstudio", "modele": "qwen2.5-7b-instruct"})
check("D12 /tester local:lmstudio : connu (liste publiée relue)", r.status_code == 200 and r.json()["etat"] == "connu", r.text[:200])
c.post("/api/settings/provider-defaults", json={"summarizer": "", "planner": ""})

# ── [K] catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] catalogue")
r = c.get("/api/ia/catalogue", params={"nature": "texte"})
ids = [m["id"] for m in r.json().get("modeles", [])]
lo = {m["id"]: m for m in r.json().get("modeles", [])}
check("K1 nature texte : intégrés puis local:<id>", r.status_code == 200 and ids[:4] == ["anthropic", "openai", "gemini", "ollama"]
      and ids[4:] == ["local:ollama2", "local:lmstudio", "local:vllm", "local:openai18080"], ids)
m = lo.get("local:lmstudio") or {}
check("K2 local : voie local, usd 0, note vide (gratuit), dispo, modèles", m.get("voie") == "local" and m.get("usd") == 0
      and m.get("note") == "" and m.get("dispo") is True and "llama-3.2-3b" in m.get("modeles", []), m)
check("K3 vLLM : cle = DZL_VLLM_API_KEY (son nom, jamais sa valeur) ; Ollama ajouté : cle vide",
      lo["local:vllm"]["cle"] == "DZL_VLLM_API_KEY" and not lo["local:ollama2"]["cle"] and CLE not in r.text)
check("K4 openai18080 (sans modèle) listé, dispo False", lo["local:openai18080"]["dispo"] is False)

# ── [F] Card Forge ────────────────────────────────────────────────────────────────────────────────────────────────
print("[F] Card Forge")
from app.services.cards import data as CD                          # noqa: E402
mo = CD._trad_moteur("local:lmstudio")
check("F1 _trad_moteur(local:lmstudio) : gratuit, prêt", mo["payant"] is False and mo["pret"]
      and mo["fournisseur"] == "local:lmstudio" and mo["dispo"].get("local:lmstudio") is True, mo)
try:
    CD._trad_moteur("local:inconnu")
    check("F2 local:inconnu refusé", False)
except ValueError:
    check("F2 local:inconnu refusé", True)
check("F3 devis Card Forge d'un serveur local : 0", PR.estimate(CD._trad_op([{"source": "bonjour"}], "local:lmstudio"))["total_usd"] == 0)

# ── [G] Diagnostic ────────────────────────────────────────────────────────────────────────────────────────────────
print("[G] Diagnostic")


async def _soldes():
    return {}
SR._soldes = _soldes
r = c.get("/api/reglages/diagnostic")
lg = {l["cle"]: l for l in r.json()["cles"]}
g = lg.get("local:lmstudio", {})
check("G1 une ligne local:lmstudio : prête, rubrique keys, nom, aperçu = URL · modèle, pas testable ici",
      g.get("definie") is True and g.get("rubrique") == "keys" and g.get("serveur") == "LM Studio (NAS)"
      and g.get("apercu") == "http://nas.local:1234/v1 · llama-3.2-3b" and g.get("testable") is False, g)
check("G2 openai18080 : non prête", lg.get("local:openai18080", {}).get("definie") is False)
check("G3 le Diagnostic ne contient pas la clé", CLE not in r.text and CLE[-6:] not in r.text)

# ── [X] paquet d'espace ───────────────────────────────────────────────────────────────────────────────────────────
print("[X] paquet d'espace")
src = (RACINE / "backend" / "app" / "services" / "espaces_paquet.py").read_text(encoding="utf-8")
check("X2 le paquet d'espace ignore serveurs_locaux.json et DZL_", "serveurs_locaux" not in src and "DZL_" not in src)

# ── [C] supprimer ─────────────────────────────────────────────────────────────────────────────────────────────────
r = c.delete("/api/reglages/serveurs-locaux/vllm")
check("C15 supprimer : retiré, clé effacée du .env et du processus", r.status_code == 200 and "\"vllm\"" not in fichier()
      and "DZL_VLLM_API_KEY" not in env() and not os.environ.get("DZL_VLLM_API_KEY")
      and "local:vllm" not in MT.tous(), (r.status_code, env()))
check("C16 supprimer un inconnu → 404", c.delete("/api/reglages/serveurs-locaux/vllm").status_code == 404)
check("C17 la première ligne et le .env d'origine sont intacts", "OLLAMA_URL=http://127.0.0.1:11434" in env()
      and "OLLAMA_MODEL=qwen2.5:14b-instruct" in env() and SL.lister()[0]["url"] == "http://127.0.0.1:11434")
for i in range(17):
    c.post("/api/reglages/serveurs-locaux", json={"url": f"http://10.0.1.{i + 1}:11434", "type": "ollama", "nom": f"S{i}x"})
r = c.post("/api/reglages/serveurs-locaux", json={"url": "http://10.0.2.1:11434", "type": "ollama", "nom": "Trop"})
check("C18 20 serveurs au plus → 400", r.status_code == 400 and len(SL.ids()) == 20, len(SL.ids()))

# ── [E] messages d'erreur traduits ────────────────────────────────────────────────────────────────────────────────
print("[E] traductions L10")
tr = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
import ast                                                          # noqa: E402
msgs = set()
for n in ast.walk(ast.parse(_src_sl)):
    if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and getattr(n.exc.func, "id", "") in ("ValueError", "RuntimeError") \
            and n.exc.args and isinstance(n.exc.args[0], ast.Constant) and isinstance(n.exc.args[0].value, str):
        msgs.add(n.exc.args[0].value)
manque = sorted(m for m in msgs if m not in tr)
check(f"E1 les {len(msgs)} messages fixes du service sont traduits", msgs and not manque, manque)
for m in ("Serveur local inconnu : {v}",):
    check(f"E2 « {m} » traduit", m in tr)

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
