# -*- coding: utf-8 -*-
"""Plan chapitres T17 (tache #66 du suivi, PR A, 02/10/2026) — REECRIRE ou ENGENDRER un passage dans le ton de la bible.
DECISION DE L'UTILISATEUR (02/10) : le cout est DIT et CONFIRME a chaque proposition (devis gratuit), la proposition
passe la garde des plafonds, appliquer est gratuit + sauvegarde ; 409 si le passage a change ; 423 des le devis.
Ce que le plan faisait faux, et que ce banc garde : ni verrou ni plafond ni cout ; « scene/dialogue » qui remplacait
la selection (l'action relue dans un selecteur remis a zero) ; des decalages perimes ecrits sans controle ; la bible
entiere sans borne ni delimiteurs ; « traduire » cable sur le francais ; les surlignages oublies.
LLM SIMULE (aucun appel paye), data-dir isole, cles videes.
Temoin positif : la base (a9805dcc) n'a ni le module ni la route.
Run (depuis backend/) : & $PY tests/test_chapitres_reecriture.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzreec_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY",
          "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "a9805dcc"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/reecriture.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le module ni la route de reecriture", r0.returncode != 0 and r1.returncode == 0
      and b'"/chapters/{chapter_id}/reecrire"' not in r1.stdout)


def leve(f):
    try:
        f()
    except ValueError as e:
        return str(e)
    return None


try:
    from app.services import reecriture as RE                       # noqa: E402
except ImportError as e:
    RE = None
    check("T2 le module existe", False, str(e))

if RE:
    print("[P] le module (pur)")
    check("P1 cinq passes closes, chacune avec son mode et sa consigne", set(RE.ACTIONS) == {"reformuler", "resserrer", "traduire", "scene", "dialogue"}
          and all(len(v["consigne"]) > 20 for v in RE.ACTIONS.values()) and RE.ACTIONS["scene"]["mode"] == RE.ACTIONS["dialogue"]["mode"] == "insere"
          and RE.ACTIONS["resserrer"]["mode"] == "remplace")
    ents = [{"name": "Vane Ardel", "kind": "character", "aliases": ["Vane"], "description": "homme fatigue", "voice_name": "Grave"},
            {"name": "Ysolde", "kind": "character", "aliases": [], "description": "absente"},
            {"name": "Phare de Brume", "kind": "place", "aliases": ["le Phare"], "description": "tour"}]
    u = RE.entites_utiles(ents, "Vane monte vers le phare.")
    check("P2 seules les entites PRESENTES (nom ou alias, sans casse) ; borne", [e["name"] for e in u] == ["Vane Ardel", "Phare de Brume"]
          and len(RE.entites_utiles([{"name": f"N{i}", "kind": "object", "aliases": []} for i in range(40)], " ".join(f"N{i}" for i in range(40)))) == RE.MAX_ENTITES)
    b = RE.bloc_bible(u, "vitrail")
    check("P3 la bible ENTRE DELIMITEURS, declaree comme donnee ; la voix castee et le style y sont",
          "<<<BIBLE" in b and "BIBLE>>>" in b and "DONNÉE" in b and "[voix : Grave]" in b and "vitrail" in b and "Ysolde" not in b, b)
    s, p, m = RE.construire("traduire", "Vane entre.", "", ents, "", "en")
    check("P4 traduire vers la langue CIBLE (anglais) ; une langue inconnue est refusee", "LANGUE DE SORTIE : anglais." in p and m == "remplace"
          and "langue inconnue" in (leve(lambda: RE.construire("traduire", "x", "", [], "", "kl")) or ""))
    e1, s1 = RE.jetons(s, p, "x" * 400, "remplace")
    e2, s2 = RE.jetons(s, p, "x" * 400, "insere")
    check("P5 l'estimation : l'entree suit le prompt ; une reecriture rend ~son passage, une insertion 1 200",
          e1 == (len(s) + len(p)) // 4 + 1 and s1 == 190 and s2 == 1200, f"{e1} {s1} {s2}")
    check("P6 nettoyer : « Voici : », guillemets, delimiteurs recopies", RE.nettoyer("Voici : « Le texte. »") == "Le texte."
          and RE.nettoyer("<<<PASSAGE\nLe texte.\nPASSAGE>>>") == "Le texte.")

# ── la route ──────────────────────────────────────────────────────────────────────────────────────────────────────
sys.modules["fal_client"] = types.ModuleType("fal_client")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import summarizer as SUMZ                         # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
VUS = []
SORTIE = {"t": "Vane franchit le seuil."}


def _stub(prompt, system, max_tokens):
    VUS.append({"prompt": prompt, "system": system})
    return SORTIE["t"], "anthropic"
SUMZ._chat_dispatch = _stub
FOURNISSEUR = {"v": "anthropic"}
SUMZ.active_provider = lambda: FOURNISSEUR["v"]


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def texte(c, cid):
    return js(c.get(f"/api/chapters/{cid}")).get("script_text")


def depenses():
    try:
        return sqlite3.connect(str(_DB)).execute("SELECT count(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return -1


print("\n[R] la route")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    vane = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Vane Ardel", "description": "homme fatigue"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET aliases=? WHERE id=?", (json.dumps(["Vane"]), vane.get("id"))).connection.commit()
    c.post("/api/bible/entities", json={"kind": "character", "name": "Ysolde", "description": "absente du passage"})
    c.put("/api/atelier/settings", json={"global_style": "vitrail"})
    T0 = "Vane entre. Il tient la Cle. La pluie tombe."
    ch = js(c.post("/api/chapters", json={"title": "R", "script_text": T0}))
    cid = ch.get("id")
    url = f"/api/chapters/{cid}/reecrire"
    check("R1 chapitre inconnu : 404", c.post("/api/chapters/inconnu/reecrire", json={"start": 0, "end": 3, "action": "reformuler"}).status_code == 404)
    r = c.post(url, json={"start": 0, "end": 3, "action": "inventer"})
    check("R2 action inconnue : 400 qui la nomme", r.status_code == 400 and "inventer" in r.text)
    check("R3 langue inconnue : 400", c.post(url, json={"start": 0, "end": 3, "action": "traduire", "language": "kl"}).status_code == 400)
    check("R4 selection vide : 400", c.post(url, json={"start": 5, "end": 5, "action": "reformuler"}).status_code == 400)
    from app.services import pricing as PR, plafonds as PL
    n_dep = depenses()
    r = c.post(url, json={"start": 0, "end": 11, "action": "resserrer", "devis": True})
    d = js(r)
    op = PL.op_llm(d.get("jetons", {}).get("entree", 0), d.get("jetons", {}).get("sortie", 0), "anthropic")
    check("R5 le DEVIS : chiffre au tarif du PC (> 0), fournisseur dit, AUCUN appel, aucune depense, rien d'ecrit",
          r.status_code == 200 and d.get("devis") is True and d.get("fournisseur") == "anthropic" and d.get("usd", 0) > 0
          and d.get("usd") == PR.estimate(op)["total_usd"] and VUS == [] and depenses() == n_dep and texte(c, cid) == T0, str(d))
    FOURNISSEUR["v"] = ""
    r = c.post(url, json={"start": 0, "end": 11, "action": "resserrer"})
    check("R6 aucun LLM (Ollama seul ne suffit pas : _chat_dispatch ne l'appelle pas) : 503, aucun appel", r.status_code == 503 and VUS == [], r.text[:100])
    FOURNISSEUR["v"] = "anthropic"
    r = c.post(url, json={"start": 0, "end": 11, "action": "resserrer"})
    d = js(r)
    vs = js(c.get(f"/api/chapters/{cid}/versions")).get("versions", [])
    dep = sqlite3.connect(str(_DB)).execute("SELECT moteur, categorie FROM depenses").fetchall()
    check("R7 la PROPOSITION : un appel ; la bible du passage (Vane, pas Ysolde), le style, les delimiteurs, la consigne ; RIEN d'ecrit",
          r.status_code == 200 and len(VUS) == 1 and d.get("proposition") == "Vane franchit le seuil." and d.get("attendu") == "Vane entre."
          and "Vane Ardel" in VUS[0]["prompt"] and "Ysolde" not in VUS[0]["prompt"] and "vitrail" in VUS[0]["prompt"]
          and "<<<PASSAGE\nVane entre.\nPASSAGE>>>" in VUS[0]["prompt"] and "resserr" in VUS[0]["system"].lower()
          and texte(c, cid) == T0 and vs == [], f"{r.status_code} {d}")
    check("R8 la depense est ecrite (garde des plafonds, categorie chapitres)", any(x[1] == "chapitres" for x in dep), str(dep))
    r = c.post(url, json={"start": 0, "end": 11, "action": "resserrer", "appliquer": True, "texte": d.get("proposition"), "attendu": "Vane entre."})
    vs = js(c.get(f"/api/chapters/{cid}/versions")).get("versions", [])
    spans = json.loads(js(c.get(f"/api/chapters/{cid}")).get("spans") or "[]") if isinstance(js(c.get(f"/api/chapters/{cid}")).get("spans"), str) \
        else js(c.get(f"/api/chapters/{cid}")).get("spans") or []
    check("R9 APPLIQUER (remplace) : le passage exact, UNE version « reecriture » avec l'ancien texte, gratuit (aucun appel)",
          r.status_code == 200 and texte(c, cid) == "Vane franchit le seuil. Il tient la Cle. La pluie tombe." and len(vs) == 1
          and vs[0].get("passe") == "reecriture" and len(VUS) == 1, f"{r.status_code} {texte(c, cid)!r} {vs}")
    check("R10 le surlignage suit le texte applique (recalcule par le serveur)", any(s.get("entity_id") == vane.get("id") and s.get("start") == 0 for s in spans), str(spans)[:200])
    T1 = texte(c, cid)
    SORTIE["t"] = "— Tu as froid ?\n— Non."
    d = js(c.post(url, json={"start": 24, "end": 40, "action": "dialogue"}))
    r = c.post(url, json={"start": 24, "end": 40, "action": "dialogue", "appliquer": True, "texte": d.get("proposition"), "attendu": d.get("attendu")})
    check("R11 APPLIQUER (insere) : le dialogue arrive APRES la selection, qui reste", r.status_code == 200
          and texte(c, cid) == T1[:40] + "\n\n— Tu as froid ?\n— Non." + T1[40:], repr(texte(c, cid)))
    T2 = texte(c, cid)
    r = c.post(url, json={"start": 0, "end": 4, "action": "reformuler", "appliquer": True, "texte": "X", "attendu": "Autre"})
    check("R12 le passage a CHANGE depuis la proposition : 409, rien n'est ecrit", r.status_code == 409 and texte(c, cid) == T2)
    r = c.post(url, json={"start": 0, "end": 4, "action": "reformuler", "appliquer": True, "texte": "X"})
    check("R13 appliquer SANS « attendu » : 400", r.status_code == 400 and texte(c, cid) == T2)
    with sqlite3.connect(str(_DB)) as db:
        db.execute("INSERT INTO chapter_locks (chapter_id, device_id, device_nom, base_sha256, pris_le) VALUES (?,?,?,?,?)",
                   (cid, "dev1", "Pixel", "", datetime.utcnow().isoformat(sep=" ")))
    n = len(VUS)
    codes = [c.post(url, json={"start": 0, "end": 4, "action": "reformuler", **x}).status_code
             for x in ({"devis": True}, {}, {"appliquer": True, "texte": "X", "attendu": T2[:4]})]
    check("R14 chapitre EMPORTE : 423 des le devis, a la proposition et a l'application ; aucun appel", codes == [423, 423, 423]
          and len(VUS) == n and texte(c, cid) == T2, str(codes))
    with sqlite3.connect(str(_DB)) as db:
        db.execute("DELETE FROM chapter_locks")
    PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post(url, json={"start": 0, "end": 4, "action": "reformuler"})
    check("R15 au-dela du plafond : 402 dz_plafond, AUCUN appel", r.status_code == 402 and "dz_plafond" in r.text and len(VUS) == n, f"{r.status_code}")
    r = c.post(url, json={"start": 0, "end": 4, "action": "reformuler"}, headers={"X-DZ-Plafond": "confirme"})
    check("R16 confirme : il part", r.status_code == 200 and len(VUS) == n + 1)
    PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
    src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("R17 recensee parmi les routes PAYANTES", '("routes", "POST", "/chapters/{chapter_id}/reecrire")' in src)

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
import re as _re                                                     # noqa: E402
_at = _ICI.parent.parent / "frontend" / "atelier"
_js = (_at / "atelier.js").read_text(encoding="utf-8")
_html = (_at / "index.html").read_text(encoding="utf-8")
_fn = _js.split("async function reecrire(")[1].split("\n}\n")[0] if "async function reecrire(" in _js else ""
_ap = _js.split("async function reecrireAppliquer(")[1].split("\n}\n")[0] if "async function reecrireAppliquer(" in _js else ""
_mod = _re.split(r"\n<div id=", _html.split('<div id="reeModal"')[1])[0] if '<div id="reeModal"' in _html else ""   # la modale SEULE
check("U1 le selecteur (avec title, cinq passes) et les trois boutons de la proposition, chacun avec un title",
      _re.search(r'<select id="reeAction" title="[^"]+">', _html) is not None and len(_re.findall(r'<option value="(?:reformuler|resserrer|traduire|scene|dialogue)">', _html)) == 5
      and len(_re.findall(r"<button [^>]*title=", _mod)) == 3 and _mod.count("<button") == 3)
_dv = _fn.find("devis: true")
_cf = _fn.find("if (!await window.__dzDialogue.confirmer(")
_rt = _fn.find("return;", _cf) if _cf >= 0 else -1
_pr = _fn.find("const d = await api.send(\"POST\"")
check("U2 l'ordre : DEVIS -> dialogue qui DIT le cout (et s'arrete sur Annuler) -> proposition", 0 <= _dv < _cf < _rt < _pr and "usd" in _fn,
      f"{_dv} {_cf} {_rt} {_pr}")
check("U3 appliquer renvoie l'ACTION gardee et le passage ATTENDU (pas le selecteur remis a zero)",
      "action: reeEnCours.action" in _ap and "attendu: reeEnCours.attendu" in _ap and '$("#reeAction").value' not in _ap)
check("U4 traduire demande la langue CIBLE (dialogue maison) ; le texte en attente est sauve avant le devis ; aucun dialogue natif",
      "window.__dzDialogue.saisir(" in _fn and "await sauverMaintenant();" in _fn and _fn.find("await sauverMaintenant();") < _dv
      and not _re.search(r"(?<![.\w])(confirm|prompt|alert)\(", _fn + _ap))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
