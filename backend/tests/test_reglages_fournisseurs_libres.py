# -*- coding: utf-8 -*-
"""t222 (Menus : Réglages, 16/10/2026) — les fournisseurs libres compatibles OpenAI. Banc SERVEUR (l'écran a son banc
à part : test_reglages_fournisseurs_libres_ecran.py).

Remontée de l'utilisateur (15/10) : « Clés d'API : pouvoir ajouter un fournisseur libre (DeepSeek, OpenRouter,
Mistral, Groq…) ; ses modèles doivent ensuite apparaître dans les listes de modèles IA de l'application ».

Zéro réseau, aucune clé réelle, aucun appel payant : le transport httpx de `fournisseurs_llm` est un FAUX SERVEUR
compatible OpenAI (GET /models, POST /chat/completions, en mémoire) et la résolution DNS est remplacée.
Ce que ce banc garde :
  [U] l'URL de base : https seulement ; ni identifiants, ni requête, ni fragment ; localhost, IP privées / boucle /
      lien local, noms .local refusés ; un nom public qui RÉSOUT vers le réseau privé est refusé à l'appel ;
  [C] créer / modifier / supprimer : le fichier DATA_ROOT/fournisseurs_llm.json n'a AUCUN secret ; la clé va au
      .env (ou au coffre) sous DZF_<ID>_API_KEY ; aucune réponse ne contient la clé ; coffre fermé → 409 sans écrire ;
      supprimer efface la clé ; un modèle qui ressemble à une clé → 400 ; 20 fournisseurs au plus ;
  [L] « Lire la liste » = GET {base}/models avec la clé (en-tête Bearer), texte seulement, triée ; refus 401 dit sans
      recopier la réponse ; avant création (base + cle) comme après (id) ;
  [T] « Tester » : ok / refus / sans_cle, sans POST (rien dépensé) ;
  [R] le registre : `tous()` = intégrés puis fl:<id>, ids intégrés inchangés ; `etat()` ; configure = clé + modèle ;
  [V] Vectorlab : /vector/illustration/moteurs liste fl:<id> et ses modèles ; POST /vector/illustration tire
      POST {base}/chat/completions au modèle choisi, sous le plafond (estimation par jetons) ;
  [P] prix : jamais « gratuit » — estimation par jetons au tarif Anthropic, ligne `a_mesurer` ; le plafond refuse 402 ;
  [D] Fournisseurs par défaut : rôles résumé / planificateur acceptent fl:<id> (et le dispatch le tire), le modèle par
      défaut s'y règle (fichier, pas .env), /modeles et /tester l'acceptent ;
  [K] /api/ia/catalogue?nature=texte : les intégrés puis fl:<id>, note a_mesurer, cle = DZF_<ID>_API_KEY ;
  [F] Card Forge : la traduction accepte fl:<id> (devis payant, tir par le fournisseur) ;
  [G] Diagnostic : une ligne par fournisseur (clé posée ou non), rubrique keys, jamais d'aperçu ;
  [X] écriture refusée depuis un autre appareil (403) ; le paquet d'espace (t210) n'emporte rien d'ici ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_traductions.json).
Run (depuis backend/) : & $PY tests/test_reglages_fournisseurs_libres.py"""
import asyncio, json, os, pathlib, socket, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import fournisseurs_llm as FL                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import vector_illustration as VI                  # noqa: E402
from app.services import pricing as PR, plafonds as PLAF            # noqa: E402
import app.api.settings_routes as SR                                # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "", "OLLAMA_MODEL": "",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


# ── le faux serveur compatible OpenAI (en mémoire) ────────────────────────────────────────────────────────────────
CLE = "sk-faussecle-banc-t222-0000000000"
REQ = []
REPONSE = {"texte": "Résumé du faux fournisseur."}


def _faux(req: httpx.Request) -> httpx.Response:
    REQ.append(req)
    if req.headers.get("authorization") != f"Bearer {CLE}":
        return httpx.Response(401, json={"error": {"message": f"Incorrect API key provided: {req.headers.get('authorization')}"}})
    if req.method == "GET" and req.url.path.endswith("/models"):
        return httpx.Response(200, json={"object": "list", "data": [
            {"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}, {"id": "text-embedding-x"}, {"id": "deepseek-chat"}]})
    if req.method == "POST" and req.url.path.endswith("/chat/completions"):
        corps = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant",
                                                                  "content": REPONSE["texte"] + " [" + corps["model"] + "]"}}]})
    return httpx.Response(404, json={})


FL._TRANSPORT = httpx.MockTransport(_faux)
PUBLIC = "93.184.216.34"


def _faux_dns(hote, port, *a, **k):
    if hote == "piege.exemple.test":
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", port))]
    if hote == "absent.exemple.test":
        raise socket.gaierror("introuvable")
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, port))]


FL._resoudre = _faux_dns

c = TestClient(app)
c.__enter__()


def env():
    return (_tmp / ".env").read_text(encoding="utf-8")


def fichier():
    f = _tmp / "fournisseurs_llm.json"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


# ── [U] l'URL de base ─────────────────────────────────────────────────────────────────────────────────────────────
print("[U] URL de base")
check("U1 https normalisée, « / » final retiré", FL.verifier_base(" https://api.deepseek.com/v1/ ") == "https://api.deepseek.com/v1")
check("U1b port gardé", FL.verifier_base("https://api.exemple.test:8443/v1") == "https://api.exemple.test:8443/v1")
refus = ["http://api.deepseek.com/v1", "ftp://x.com", "https://user:pw@api.x.ai/v1", "https://api.x.ai/v1?key=1",
         "https://api.x.ai/v1#a", "https://localhost/v1", "https://127.0.0.1/v1", "https://10.0.0.4/v1",
         "https://192.168.1.2/v1", "https://169.254.169.254/latest", "https://[::1]/v1", "https://[fe80::1]/v1",
         "https://box.local/v1", "https://intranet/v1", "https://a.localhost/v1", "", "https://"]
mauvais = []
for u in refus:
    try:
        FL.verifier_base(u)
        mauvais.append(u)
    except ValueError:
        pass
check(f"U2 {len(refus)} URL refusées (http, identifiants, requête, local, privé, lien local, .local, sans point)",
      not mauvais, mauvais)
check("U3 les 6 préréglages passent la garde et sont https",
      len(FL.PREREGLAGES) == 6 and all(FL.verifier_base(p["base"]) == p["base"] for p in FL.PREREGLAGES)
      and {p["nom"] for p in FL.PREREGLAGES} == {"DeepSeek", "OpenRouter", "Mistral", "Groq", "Together", "xAI"})
try:
    FL._hote_public("https://piege.exemple.test/v1")
    check("U4 un nom public qui résout vers le réseau privé est refusé à l'appel", False)
except ValueError:
    check("U4 un nom public qui résout vers le réseau privé est refusé à l'appel", True)

# ── [X] autre appareil ────────────────────────────────────────────────────────────────────────────────────────────
print("[X] autre appareil")
cd = TestClient(app, client=("192.168.1.50", 5000))
r = cd.post("/api/reglages/fournisseurs-libres", json={"nom": "DeepSeek", "base": "https://api.deepseek.com/v1", "cle": CLE})
check("X1 créer depuis un autre appareil → 403, rien d'écrit", r.status_code in (401, 403) and not fichier() and CLE not in env(), r.status_code)
check("X1b lire depuis un autre appareil → 403", cd.get("/api/reglages/fournisseurs-libres").status_code in (401, 403))
import ast as _ast                                                  # noqa: E402
_sr = _ast.parse((RACINE / "backend" / "app" / "api" / "settings_routes.py").read_text(encoding="utf-8"))
_fl = [f for f in _sr.body if isinstance(f, _ast.AsyncFunctionDef) and any(
    isinstance(d, _ast.Call) and d.args and isinstance(d.args[0], _ast.Constant)
    and "fournisseurs-libres" in str(d.args[0].value) for d in f.decorator_list)]
_sans = [f.name for f in _fl if not any(isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "_local"
                                        for st in f.body[:3] for n in _ast.walk(st))]
check(f"X1c les {len(_fl)} routes fournisseurs-libres appellent _local (garde de la boucle locale) d'entrée",
      len(_fl) == 6 and not _sans, _sans)

# ── [C] créer ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[C] créer / modifier / supprimer")
r = c.get("/api/reglages/fournisseurs-libres")
check("C0 liste vide + 6 préréglages", r.status_code == 200 and r.json()["fournisseurs"] == [] and len(r.json()["prereglages"]) == 6, r.text[:200])
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "Test", "base": "http://api.exemple.test/v1", "cle": CLE})
check("C1 http → 400, rien d'écrit (ni fichier, ni clé)", r.status_code == 400 and not fichier() and CLE not in env(), r.status_code)
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "Test", "base": "https://api.exemple.test/v1", "cle": CLE,
                                                       "modeles": "deepseek-chat, AIzaUneCleColleeIci000000000000000"})
check("C2 un modèle qui ressemble à une clé → 400, rien d'écrit", r.status_code == 400 and not fichier() and CLE not in env(), r.text[:160])
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "", "base": "https://api.exemple.test/v1"})
check("C3 sans nom → 400", r.status_code == 400)

r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "DeepSeek", "base": "https://api.deepseek.com/v1/", "cle": CLE,
                                                       "modeles": "deepseek-chat\ndeepseek-reasoner, deepseek-chat",
                                                       "defaut": "deepseek-chat"})
v = r.json().get("fournisseur") or {}
check("C4 créé : id deepseek, moteur fl:deepseek, base normalisée, modèles dédoublonnés",
      r.status_code == 200 and v.get("id") == "deepseek" and v.get("moteur") == "fl:deepseek"
      and v.get("base") == "https://api.deepseek.com/v1" and v.get("modeles") == ["deepseek-chat", "deepseek-reasoner"]
      and v.get("defaut") == "deepseek-chat", r.text[:300])
check("C5 la réponse ne contient PAS la clé ; elle dit cle_posee et le NOM de la clé",
      CLE not in r.text and v.get("cle_posee") is True and v.get("cle") == "DZF_DEEPSEEK_API_KEY")
check("C6 la clé est au .env sous DZF_DEEPSEEK_API_KEY (pas de coffre) et appliquée",
      f"DZF_DEEPSEEK_API_KEY={CLE}" in env() and os.environ.get("DZF_DEEPSEEK_API_KEY") == CLE)
doc = json.loads(fichier())
check("C7 fournisseurs_llm.json n'a AUCUN secret (ni clé, ni nom de champ de clé en valeur)",
      CLE not in fichier() and set(doc["fournisseurs"]["deepseek"]) == {"nom", "base", "modeles", "defaut", "cree"}, fichier()[:300])
r2 = c.get("/api/reglages/fournisseurs-libres")
check("C8 GET : la liste ne contient pas la clé", r2.status_code == 200 and CLE not in r2.text and len(r2.json()["fournisseurs"]) == 1)
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "Deep Seek!", "base": "https://api.deepseek.com/v1"})
check("C9 même nom → id distinct (deepseek2), sans clé : cle_posee False", r.json()["fournisseur"]["id"] == "deepseek2"
      and r.json()["fournisseur"]["cle_posee"] is False, r.text[:200])

r = c.post("/api/reglages/fournisseurs-libres/deepseek2", json={"defaut": "mon-modele-libre", "nom": "Deep 2"})
v2 = r.json().get("fournisseur") or {}
check("C10 modifier : défaut saisi librement entre en tête des modèles", r.status_code == 200 and v2["defaut"] == "mon-modele-libre"
      and v2["modeles"][0] == "mon-modele-libre" and v2["nom"] == "Deep 2", r.text[:200])
r = c.post("/api/reglages/fournisseurs-libres/deepseek2", json={"defaut": "sk-clecolleeaulieudunmodele"})
check("C11 modifier : un défaut qui ressemble à une clé → 400", r.status_code == 400)
r = c.post("/api/reglages/fournisseurs-libres/inconnu", json={"nom": "x"})
check("C12 fournisseur inconnu → 404", r.status_code == 404)

# coffre posé mais fermé : refus 409 avant toute écriture
from app.services import coffre as CF                                # noqa: E402
_vp, _vo = CF.verrouille, CF.ouvert
CF.verrouille = lambda: True
avant = fichier()
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "Groq", "base": "https://api.groq.com/openai/v1", "cle": CLE})
check("C13 coffre fermé : créer AVEC clé → 409, rien d'écrit", r.status_code == 409 and fichier() == avant, r.status_code)
r = c.post("/api/reglages/fournisseurs-libres/deepseek2", json={"cle": CLE})
check("C14 coffre fermé : poser une clé → 409", r.status_code == 409 and fichier() == avant)
CF.verrouille = _vp

# ── [L] lire la liste ─────────────────────────────────────────────────────────────────────────────────────────────
print("[L] lire la liste")
REQ.clear()
r = c.post("/api/reglages/fournisseurs-libres/lire-modeles", json={"id": "deepseek"})
check("L1 GET {base}/models avec Bearer : texte seulement, dédoublonné, trié",
      r.status_code == 200 and r.json()["modeles"] == ["deepseek-chat", "deepseek-reasoner"], r.text[:200])
check("L2 une seule requête, GET https://api.deepseek.com/v1/models", len(REQ) == 1 and REQ[0].method == "GET"
      and str(REQ[0].url) == "https://api.deepseek.com/v1/models")
r = c.post("/api/reglages/fournisseurs-libres/lire-modeles", json={"base": "https://api.mistral.ai/v1", "cle": CLE})
check("L3 avant création (base + clé) : la liste se lit, la clé n'est ni gardée ni renvoyée",
      r.status_code == 200 and r.json()["modeles"] and CLE not in r.text and "mistral" not in fichier())
r = c.post("/api/reglages/fournisseurs-libres/lire-modeles", json={"base": "https://api.mistral.ai/v1", "cle": "sk-mauvaise"})
check("L4 clé refusée : 400 « 401 », sans recopier la réponse du fournisseur (qui cite la clé)",
      r.status_code == 400 and "401" in r.text and "sk-mauvaise" not in r.text and "Incorrect" not in r.text, r.text[:200])
r = c.post("/api/reglages/fournisseurs-libres/lire-modeles", json={"base": "https://piege.exemple.test/v1", "cle": CLE})
check("L5 nom qui résout vers le réseau privé : 400, aucune requête partie", r.status_code == 400 and
      not any("piege" in str(q.url) for q in REQ), r.text[:200])
r = c.post("/api/reglages/fournisseurs-libres/lire-modeles", json={"base": "https://api.mistral.ai/v1", "cle": ""})
check("L6 sans clé : 400", r.status_code == 400)

# ── [T] tester ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[T] tester")
REQ.clear()
r = c.post("/api/reglages/fournisseurs-libres/deepseek/tester")
check("T1 ok : n modèles, défaut publié, AUCUN POST (rien dépensé)", r.status_code == 200 and r.json()["etat"] == "ok"
      and r.json()["n"] == 2 and r.json()["defaut_publie"] is True and all(q.method == "GET" for q in REQ), r.text[:200])
r = c.post("/api/reglages/fournisseurs-libres/deepseek2/tester")
check("T2 sans clé : etat sans_cle, aucune requête", r.json()["etat"] == "sans_cle" and len(REQ) == 1, r.text[:200])

# ── [R] le registre ───────────────────────────────────────────────────────────────────────────────────────────────
print("[R] registre")
check("R1 MOTEURS (intégrés) inchangés", MT.MOTEURS == ("anthropic", "openai", "gemini", "ollama"))
check("R2 tous() = intégrés puis fl:<id>", MT.tous() == ["anthropic", "openai", "gemini", "ollama", "fl:deepseek", "fl:deepseek2"], MT.tous())
check("R3 configure : clé + modèle (deepseek oui, deepseek2 sans clé non)", MT.configure("fl:deepseek") and not MT.configure("fl:deepseek2"))
et = {e["moteur"]: e for e in MT.etat()}
check("R4 etat() : une ligne par fournisseur, libre, nom, modèle", et.get("fl:deepseek", {}).get("libre") is True
      and et["fl:deepseek"]["nom"] == "DeepSeek" and et["fl:deepseek"]["modele"] == "deepseek-chat", et.get("fl:deepseek"))
check("R5 connu : fl:inconnu non, fl:deepseek oui", MT.connu("fl:deepseek") and not MT.connu("fl:inconnu") and not MT.connu("x"))

# ── [V] Vectorlab ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] Vectorlab")
VI._CATALOGUE.clear()
r = c.get("/api/vector/illustration/moteurs")
mo = {m["moteur"]: m for m in r.json().get("moteurs", [])}
check("V1 /vector/illustration/moteurs : fl:deepseek et ses modèles (pas deepseek2 sans clé)",
      "fl:deepseek" in mo and mo["fl:deepseek"]["modeles"] == ["deepseek-chat", "deepseek-reasoner"]
      and mo["fl:deepseek"]["defaut"] == "deepseek-chat" and "fl:deepseek2" not in mo, r.text[:300])
REQ.clear()
REPONSE["texte"] = '<svg viewBox="0 0 10 10"><rect x="1" y="1" width="4" height="4" fill="#f00"/></svg>'
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "fl:deepseek", "model": "deepseek-reasoner"})
post = [q for q in REQ if q.method == "POST"]
check("V2 tir : POST {base}/chat/completions au modèle choisi, une forme rendue", r.status_code == 200 and len(post) == 1
      and str(post[0].url) == "https://api.deepseek.com/v1/chat/completions"
      and json.loads(post[0].content)["model"] == "deepseek-reasoner" and r.json()["provider"] == "fl:deepseek", r.text[:300])
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "fl:deepseek2"})
check("V3 fournisseur sans clé : 400 indisponible", r.status_code == 400)

# ── [P] prix et plafond ───────────────────────────────────────────────────────────────────────────────────────────
print("[P] prix")
dv = PR.estimate(PLAF.op_llm(1_000_000, 1_000_000, "fl:deepseek"))
grille = PR.load()["llm_usd_per_mtok"]["anthropic"]
lig = dv["breakdown"][0]
check("P1 jamais gratuit : estimation au tarif Anthropic de la grille, ligne a_mesurer, moteur fl:deepseek",
      abs(dv["total_usd"] - (grille["in"] + grille["out"])) < 1e-6 and lig.get("a_mesurer") is True
      and lig["provider"] == "fl:deepseek", dv)
check("P2 les intégrés gardent leur ligne (pas d'a_mesurer)", "a_mesurer" not in PR.estimate(PLAF.op_llm(10, 10, "openai"))["breakdown"][0])
PLAF.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
REQ.clear()
r = c.post("/api/vector/illustration", json={"prompt": "un carré", "provider": "fl:deepseek"})
check("P3 le plafond s'applique : 402 et AUCUN POST parti", r.status_code == 402 and not [q for q in REQ if q.method == "POST"], r.status_code)
PLAF.enregistrer({"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80})

# ── [D] Fournisseurs par défaut ───────────────────────────────────────────────────────────────────────────────────
print("[D] Fournisseurs par défaut")
r = c.get("/api/settings/provider-defaults")
d = r.json()
check("D1 les rôles proposent fl:deepseek (configuré), pas deepseek2", "fl:deepseek" in d["roles"]["summarizer"]["available"]
      and "fl:deepseek" in d["roles"]["planner"]["available"] and "fl:deepseek2" not in d["roles"]["planner"]["available"], d["roles"])
check("D1b moteurs : la ligne fl:deepseek", any(m["moteur"] == "fl:deepseek" for m in d["moteurs"]))
r = c.post("/api/settings/provider-defaults", json={"summarizer": "fl:deepseek", "planner": "fl:deepseek"})
check("D2 rôles → fl:deepseek écrits au .env", r.status_code == 200 and "SUMMARIZER_PROVIDER=fl:deepseek" in env()
      and settings.PLANNER_PROVIDER == "fl:deepseek", r.text[:200])
r = c.post("/api/settings/provider-defaults", json={"summarizer": "fl:inconnu"})
check("D3 fl:inconnu → 400", r.status_code == 400)
from app.services import summarizer as SZ, marketing as MK         # noqa: E402
REQ.clear()
REPONSE["texte"] = "Texte du faux fournisseur."
out, p = SZ._chat_dispatch("bonjour", "sys", 50)
check("D4 _chat_dispatch tire le fournisseur libre actif", p == "fl:deepseek" and out and "deepseek-chat" in out, (out, p))
txt = SZ.summarize("x" * 200, title="T", language="FR")
check("D5 summarize passe par le fournisseur libre", txt and "Texte du faux fournisseur" in txt, txt)
check("D6 op_llm suit le rôle (fl:deepseek)", PLAF.op_llm(10, 10)["provider"] == "fl:deepseek")
check("D7 planificateur : fl:deepseek disponible et dans l'ordre", MK._plan_available("fl:deepseek")
      and "fl:deepseek" in MK._moteurs_plan() and not MK._plan_available("fl:deepseek2"))
REPONSE["texte"] = json.dumps({"posts": [{"day_offset": 0, "time": "10:00", "title": "A", "caption": "Bonjour",
                                          "channels": ["x"]}]})
plan = asyncio.run(MK.generate_plan("une semaine", days=1, posts_per_day=1))
check("D8 generate_plan par fl:deepseek", plan.get("engine") == "fl:deepseek", plan.get("engine"))
r = c.post("/api/settings/provider-defaults", json={"modeles": {"fl:deepseek": "deepseek-reasoner"}})
check("D9 modèle par défaut d'un libre : écrit au fichier (pas au .env)", r.status_code == 200
      and FL.obtenir("deepseek")["defaut"] == "deepseek-reasoner" and "deepseek-reasoner" not in env(), r.text[:200])
r = c.post("/api/settings/provider-defaults", json={"modeles": {"fl:deepseek": "sk-uneclecollee"}})
check("D10 modèle libre qui ressemble à une clé → 400", r.status_code == 400 and FL.obtenir("deepseek")["defaut"] == "deepseek-reasoner")
r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "fl:deepseek"})
check("D11 /modeles?moteur=fl:deepseek : sa liste, défaut en tête", r.status_code == 200
      and r.json()["modeles"][0] == "deepseek-reasoner" and r.json()["configure"] is True, r.text[:200])
r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "fl:deepseek", "modele": "deepseek-chat"})
check("D12 /tester fl:deepseek : connu (liste publiée relue)", r.status_code == 200 and r.json()["etat"] == "connu", r.text[:200])
c.post("/api/settings/provider-defaults", json={"summarizer": "", "planner": ""})

# ── [K] catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] catalogue")
r = c.get("/api/ia/catalogue", params={"nature": "texte"})
ids = [m["id"] for m in r.json().get("modeles", [])]
fl = {m["id"]: m for m in r.json().get("modeles", [])}.get("fl:deepseek") or {}
check("K1 nature texte : intégrés puis fl:<id>", r.status_code == 200 and ids[:4] == ["anthropic", "openai", "gemini", "ollama"]
      and ids[4:] == ["fl:deepseek", "fl:deepseek2"], ids)
check("K2 libre : note a_mesurer (jamais gratuit), voie libre, clé DZF_, dispo, modèles", fl.get("note") == "a_mesurer"
      and fl.get("voie") == "libre" and fl.get("cle") == "DZF_DEEPSEEK_API_KEY" and fl.get("dispo") is True
      and "deepseek-chat" in fl.get("modeles", []), fl)
check("K3 deepseek2 (sans clé) reste listé, dispo False", {m["id"]: m for m in r.json()["modeles"]}["fl:deepseek2"]["dispo"] is False)
check("K4 le catalogue ne contient pas la clé", CLE not in r.text)

# ── [F] Card Forge ────────────────────────────────────────────────────────────────────────────────────────────────
print("[F] Card Forge")
from app.services.cards import data as CD                          # noqa: E402
mo = CD._trad_moteur("fl:deepseek")
check("F1 _trad_moteur(fl:deepseek) : payant, prêt, fournisseur fl:deepseek", mo["payant"] and mo["pret"]
      and mo["fournisseur"] == "fl:deepseek" and mo["dispo"].get("fl:deepseek") is True, mo)
try:
    CD._trad_moteur("fl:inconnu")
    check("F2 fl:inconnu refusé", False)
except ValueError:
    check("F2 fl:inconnu refusé", True)
c.post("/api/settings/provider-defaults", json={"summarizer": "fl:deepseek"})
ma = CD._trad_moteur("auto")
check("F2b « Fournisseur des Réglages » (auto) suit le rôle Résumé : fl:deepseek, payant", ma["fournisseur"] == "fl:deepseek"
      and ma["payant"] and ma["pret"], ma)
c.post("/api/settings/provider-defaults", json={"summarizer": ""})
dv = PR.estimate(CD._trad_op([{"source": "bonjour"}], "fl:deepseek"))
check("F3 devis Card Forge non nul (estimation)", dv["total_usd"] > 0, dv)

# ── [G] Diagnostic ────────────────────────────────────────────────────────────────────────────────────────────────
print("[G] Diagnostic")


async def _soldes():
    return {}
SR._soldes = _soldes
r = c.get("/api/reglages/diagnostic")
lg = {l["cle"]: l for l in r.json()["cles"]}
check("G1 une ligne DZF_DEEPSEEK_API_KEY : posée, rubrique keys, nom du fournisseur, SANS aperçu",
      lg.get("DZF_DEEPSEEK_API_KEY", {}).get("definie") is True and lg["DZF_DEEPSEEK_API_KEY"]["rubrique"] == "keys"
      and lg["DZF_DEEPSEEK_API_KEY"]["apercu"] == "" and lg["DZF_DEEPSEEK_API_KEY"]["fournisseur"] == "DeepSeek"
      and lg["DZF_DEEPSEEK_API_KEY"]["testable"] is False, lg.get("DZF_DEEPSEEK_API_KEY"))
check("G2 deepseek2 : ligne non posée", lg.get("DZF_DEEPSEEK2_API_KEY", {}).get("definie") is False)
check("G3 le Diagnostic ne contient pas la clé (ni ses 4 derniers caractères)", CLE not in r.text and CLE[-4:] not in r.text)

# ── [X] paquet d'espace ───────────────────────────────────────────────────────────────────────────────────────────
print("[X] paquet d'espace")
from app.services import espaces_paquet as EP                      # noqa: E402
src = (RACINE / "backend" / "app" / "services" / "espaces_paquet.py").read_text(encoding="utf-8")
check("X2 le paquet d'espace ignore fournisseurs_llm.json et DZF_ (ni nommé ni lu)", "fournisseurs_llm" not in src and "DZF_" not in src)
try:
    blob = EP.exporter("deepotus")
    contenu = blob if isinstance(blob, (bytes, bytearray)) else blob[0]
    import io, zipfile                                                # noqa: E402
    z = zipfile.ZipFile(io.BytesIO(contenu))
    tout = b"".join(z.read(n) for n in z.namelist())
    check("X3 l'export zip de l'espace ne porte ni la clé, ni le fournisseur", CLE.encode() not in tout
          and b"fournisseurs_llm" not in tout and b"api.deepseek.com" not in tout)
except Exception as e:  # noqa: BLE001
    check("X3 l'export zip de l'espace ne porte ni la clé, ni le fournisseur", False, repr(e)[:200])

# ── [C] supprimer ─────────────────────────────────────────────────────────────────────────────────────────────────
r = c.delete("/api/reglages/fournisseurs-libres/deepseek")
check("C15 supprimer : retiré, clé effacée du .env et du processus", r.status_code == 200 and "deepseek\"" not in fichier()
      and "DZF_DEEPSEEK_API_KEY" not in env() and not os.environ.get("DZF_DEEPSEEK_API_KEY")
      and MT.tous() == ["anthropic", "openai", "gemini", "ollama", "fl:deepseek2"], (r.status_code, env()))
check("C16 supprimer un inconnu → 404", c.delete("/api/reglages/fournisseurs-libres/deepseek").status_code == 404)
for i in range(19):
    c.post("/api/reglages/fournisseurs-libres", json={"nom": f"F{i}x", "base": "https://api.exemple.test/v1"})
r = c.post("/api/reglages/fournisseurs-libres", json={"nom": "Trop", "base": "https://api.exemple.test/v1"})
check("C17 20 fournisseurs au plus → 400", r.status_code == 400 and len(FL.ids()) == 20, len(FL.ids()))

# ── [E] messages d'erreur traduits ────────────────────────────────────────────────────────────────────────────────
print("[E] traductions L10")
tr = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
import ast                                                          # noqa: E402
srcf = (RACINE / "backend" / "app" / "services" / "fournisseurs_llm.py").read_text(encoding="utf-8")
msgs = set()
for n in ast.walk(ast.parse(srcf)):
    if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and getattr(n.exc.func, "id", "") in ("ValueError", "RuntimeError") \
            and n.exc.args and isinstance(n.exc.args[0], ast.Constant) and isinstance(n.exc.args[0].value, str):
        msgs.add(n.exc.args[0].value)
manque = sorted(m for m in msgs if m not in tr)
check(f"E1 les {len(msgs)} messages fixes du service sont traduits", msgs and not manque, manque)
for m in ("Fournisseur libre inconnu : {v}", "Coffre verrouillé : {e}"):
    check(f"E2 « {m} » traduit", m in tr)

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
