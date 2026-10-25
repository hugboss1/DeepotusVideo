# -*- coding: utf-8 -*-
"""t307 (Boîte à outils, 25/10/2026) — les CANAUX d'un projet de la Bibliothèque : des identifiants de comptes
(services/comptes.py) de SON espace de marque ; les nouveaux posts les prendront par défaut (tâches suivantes).
Ce que ce banc garde (sections 1 et 2) :
  - migration : la colonne `canaux` est ajoutée à une table library_projects d'avant (auto-migration) ;
  - poser / lire : un compte de l'espace du projet, l'historique pour Deepotus ; un compte d'un autre espace refusé
    (PermissionError), inconnu (KeyError), mauvaise forme (ValueError), projet inconnu (KeyError) ; liste vide = aucun ;
    un compte supprimé depuis disparaît à la lecture, sans erreur ;
  - défaut : les canaux du projet ACTIF de l'espace demandé (jamais de l'espace courant) ; Deepotus ne reçoit
    jamais le défaut d'un autre espace.
Aucun réseau, rien de payé, data-dir isolé.
Run (depuis backend/) : & $PY tests/test_projets_canaux.py"""
import asyncio, os, pathlib, sqlite3, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpcan_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
BASE_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{BASE_DB.as_posix()}"
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
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

# une base d'AVANT la colonne `canaux` (et avant `espace_id`) : l'auto-migration doit les ajouter
_con = sqlite3.connect(BASE_DB)
_con.execute("CREATE TABLE library_projects (id VARCHAR(36) PRIMARY KEY, nom VARCHAR(120) NOT NULL, couleur VARCHAR(7), "
             "note TEXT, epingle INTEGER, created_at DATETIME)")
_con.commit(); _con.close()

from app.config import settings                                     # noqa: E402
from app.services import comptes, espaces, storage                  # noqa: E402
from app.services import library_projects as LP                     # noqa: E402

_loop = asyncio.new_event_loop()
def run(coro):
    return _loop.run_until_complete(coro)
def _leve_async(exc, fn, *a):
    try:
        run(fn(*a))
    except exc:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False

run(storage.init_db())
print("[M] migration")
cols = {r[1] for r in sqlite3.connect(BASE_DB).execute("PRAGMA table_info(library_projects)")}
check("M1 la colonne canaux est ajoutée à une table d'avant", "canaux" in cols, str(sorted(cols)))
check("M2 espace_id l'est aussi (témoin de la même passe)", "espace_id" in cols)

espaces.lire()
B = espaces.creer({"nom": "Client B"})["id"]
cx_deepotus = comptes.creer({"espace_id": "deepotus", "plateforme": "x", "libelle": "Deepotus X"})["id"]
cx_B = comptes.creer({"espace_id": B, "plateforme": "x", "libelle": "B X"})["id"]
settings.X_API_KEY = "plat-k"          # un compte historique « historique-x » existe alors pour Deepotus

print("[1] poser et lire")
p = run(LP.creer("Lancement")); check("1a vue neuve : aucun canal", p["canaux"] == [])
v = run(LP.poser_canaux(p["id"], [cx_deepotus]))
check("1b canal posé", v["canaux"] == [cx_deepotus], str(v))
check("1c historique admis pour Deepotus", run(LP.poser_canaux(p["id"], ["historique-x"]))["canaux"] == ["historique-x"])
check("1d compte d'un autre espace refusé", _leve_async(PermissionError, LP.poser_canaux, p["id"], [cx_B]))
check("1e compte inconnu refusé", _leve_async(KeyError, LP.poser_canaux, p["id"], ["c_inconnu"]))
check("1f forme refusée", _leve_async(ValueError, LP.poser_canaux, p["id"], "cx"))
check("1g projet inconnu", _leve_async(KeyError, LP.poser_canaux, "proj_00000000", []))
check("1h liste vide = aucun canal", run(LP.poser_canaux(p["id"], []))["canaux"] == [])
check("1j les refus n'ont rien écrit", run(LP.lister(espace="deepotus"))[0]["canaux"] == [])
run(LP.poser_canaux(p["id"], [cx_deepotus, cx_deepotus]))
check("1k doublon écarté", run(LP.lister(espace="deepotus"))[0]["canaux"] == [cx_deepotus])
comptes.supprimer(cx_deepotus)
check("1i compte supprimé ignoré", run(LP.lister(espace="deepotus"))[0]["canaux"] == [])
check("1l contenu() porte la clé", run(LP.contenu(p["id"]))["canaux"] == [])

print("[2] canaux par défaut")
check("2a aucun projet actif", run(LP.canaux_par_defaut("deepotus")) == [])
with espaces.sous_espace(B):
    pb = run(LP.creer("Projet de B"))
    run(LP.poser_actif(pb["id"]))
check("2x le projet de B est bien de l'espace B", pb["espace_id"] == B, str(pb))
try:
    run(LP.poser_canaux(pb["id"], [cx_B]))
    check("2y un projet de B accepte un compte de B", True)
except Exception as e:  # noqa: BLE001
    check("2y un projet de B accepte un compte de B", False, repr(e))
check("2b défaut de B = canaux du projet actif de B", run(LP.canaux_par_defaut(B)) == [cx_B])
check("2c Deepotus ne reçoit jamais le défaut de B", run(LP.canaux_par_defaut("deepotus")) == [])
run(LP.poser_actif(p["id"]))        # l'espace courant (Deepotus) a maintenant un projet actif
check("2d le défaut de Deepotus lit son propre projet actif", run(LP.canaux_par_defaut("deepotus")) == [])
run(LP.poser_canaux(p["id"], ["historique-x"]))
check("2e ... et ses canaux", run(LP.canaux_par_defaut("deepotus")) == ["historique-x"])
check("2f B reste indépendant", run(LP.canaux_par_defaut(B)) == [cx_B])

print("[3] route PUT /api/library/projets/{pid}/canaux")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
sys.path.insert(0, str(_ICI))
import _jeton_appareil as JA                                        # noqa: E402
cx = comptes.creer({"espace_id": "deepotus", "plateforme": "x", "libelle": "Deepotus X2"})["id"]
pid = p["id"]
with TestClient(app, client=("127.0.0.1", 50000)) as client:
    def put(i, ids):
        return client.put(f"/api/library/projets/{i}/canaux", json={"canaux": ids})
    r = put(pid, [cx])
    check("3a PUT 200 et vue relue", r.status_code == 200 and r.json()["canaux"] == [cx], r.text[:200])
    check("3b autre espace 409", put(pid, [cx_B]).status_code == 409)
    check("3c compte inconnu 404", put(pid, ["c_inconnu"]).status_code == 404)
    check("3d projet inconnu 404", put("proj_00000000", []).status_code == 404)
    check("3e forme 400", client.put(f"/api/library/projets/{pid}/canaux", json={"canaux": "x"}).status_code == 400)
    check("3f GET /library/projets porte canaux", "canaux" in client.get("/api/library/projets").json()["projets"][0])
    check("3h les refus n'ont rien écrit", client.get(f"/api/library/projets/{pid}").json()["canaux"] == [cx])
    check("3i corps non objet 400", client.put(f"/api/library/projets/{pid}/canaux", json=[cx]).status_code == 400)
    check("3k [1] -> 400", client.put(f"/api/library/projets/{pid}/canaux", json={"canaux": [1]}).status_code == 400)
    check("3l clé absente -> 400", client.put(f"/api/library/projets/{pid}/canaux", json={}).status_code == 400)
    check("3m [''] -> 400", client.put(f"/api/library/projets/{pid}/canaux", json={"canaux": [""]}).status_code == 400)
    check("3n rien écrit par ces refus", client.get(f"/api/library/projets/{pid}").json()["canaux"] == [cx])
    H = JA.entetes(app)
    lan = TestClient(app, client=("192.168.1.20", 50000))
    r = lan.put(f"/api/library/projets/{pid}/canaux", json={"canaux": []}, headers=H)
    check("3g appareil appairé : 403", r.status_code == 403, str(r.status_code))
    check("3j ... et rien n'a changé", client.get(f"/api/library/projets/{pid}").json()["canaux"] == [cx])

    print("[4] POST /api/schedule : les canaux du projet actif quand aucune cible n'est donnée")
    def post(corps):
        return client.post("/api/schedule", json=dict({"run_at": "2026-12-01T10:00:00"}, **corps))
    def comptes_de(r):
        return r.json().get("comptes") if r.status_code == 200 else f"HTTP {r.status_code}"
    r = post({"caption": "a"})
    check("4a post sans cible -> comptes du projet actif", comptes_de(r) == [cx] and r.json()["channels"] == ["x"], r.text[:200])
    check("4b channels donnés -> rien d'hérité", comptes_de(post({"caption": "b", "channels": ["telegram"]})) == [])
    check("4c comptes donnés -> gardés", comptes_de(post({"caption": "c", "comptes": ["historique-x"]})) == ["historique-x"])
    check("4d post de l'espace B -> défaut de B, jamais celui de Deepotus",
          comptes_de(post({"caption": "d", "espace_id": B})) == [cx_B])

print("[4bis] agent : creer_brouillons")
from app.services import agent_outils as AO, agent_store as AST       # noqa: E402
from app.services.storage import ScheduledPost, async_session_factory   # noqa: E402
from sqlalchemy import select                                           # noqa: E402
async def _brouillons(eid, posts):
    conv = await AST.creer("campagnes", eid, "Campagne t307")
    await AST.regler_porte(conv["id"], "porte1_validee")
    r = await AO.executer("creer_brouillons", {"posts": posts}, AO.Ctx(cid=conv["id"], espace_id=eid, etat_porte="porte1_validee"))
    async with async_session_factory() as s:
        lignes = (await s.execute(select(ScheduledPost).where(ScheduledPost.plan_id == conv["id"]).order_by(ScheduledPost.title))).scalars().all()
    return r, [(l.title, l.channels, l.comptes) for l in lignes]
Q = {"quand": "2026-12-01T10:00:00"}
r, l = run(_brouillons("deepotus", [dict(Q, titre="p1", caption="un"), dict(Q, titre="p2", caption="deux", canaux=["telegram"])]))
check("4e brouillon sans canaux -> comptes du projet", r["ok"] and l[0][2] == f'["{cx}"]' and l[0][1] == "x", str((r, l)))
check("4f brouillon avec canaux -> gardés", l[1][1] == "telegram" and l[1][2] is None, str(l))
check("4g le résumé le dit", "canaux du projet" in r["resume"], str(r)[:200])
r, l = run(_brouillons(B, [dict(Q, titre="p1", caption="un")]))
check("4h brouillon de l'espace B -> défaut de B", l[0][2] == f'["{cx_B}"]', str(l))

_loop.close()
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
