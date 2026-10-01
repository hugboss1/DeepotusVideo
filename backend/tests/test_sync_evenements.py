# -*- coding: utf-8 -*-
"""Plan mobile T17 (tache #58 du suivi, 01-02/10/2026) — les evenements du PC que le telephone change en notifications.
Le PC ne notifie rien : il fournit la matiere ; chaque evenement porte une CLE stable (le telephone dedoublonne).
Corrections du plan (03/09), mesurees dans le code :
  - un rendu fini a le statut « done » (JobStatus.DONE), pas « completed » : le plan ne l'aurait JAMAIS vu ;
  - un post n'a pas de statut « failed » : un echec est « ready » AVEC une erreur ; « ready » SANS erreur est un post
    assiste qui attend un geste ; « posted » porte posted_at (pas run_at : une publication tardive serait perdue) ;
  - D6 (delegation explicite) : un post confie a CE telephone a deja son rappel local, un post confie a un AUTRE ne le
    regarde pas — aucun des deux ne sort ;
  - les plafonds EXISTENT (#16) : plafonds.etat() et sa liste `alerte` nourrissent plafond_approche / plafond_depasse ;
  - sync_terminee / sync_conflit sont LOCALES au telephone (il recoit les conflits en reponse a /sync/lot/etat) : le
    PC ne les nomme pas.
Banc-miroir : vraies requetes depuis une IP du reseau local avec un vrai jeton, lignes semees en base.
Temoin positif : la base (9bda3a9a) n'a pas sync_evenements.
Run (depuis backend/) : & $PY tests/test_sync_evenements.py"""
import asyncio, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsyncev_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "9bda3a9a"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_evenements.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas sync_evenements", r0.returncode != 0)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
LAN = ("192.168.1.42", 50000)
NOW = datetime.utcnow()


def js(r) -> dict:
    try:
        v = r.json()
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def semer(moi: str):
    cx = sqlite3.connect(str(_DB))
    try:
        cx.execute("DELETE FROM scheduled_posts"); cx.execute("DELETE FROM jobs")
        def job(jid, status, quand, titre, err=None):
            vals = {"id": jid, "status": status, "image_filename": "a.png", "title": titre, "error": err,
                    "created_at": NOW - timedelta(days=3), "completed_at": quand}
            for _c, nom, typ, notnull, defaut, _pk in cx.execute("PRAGMA table_info(jobs)"):
                if notnull and defaut is None and nom not in vals:
                    vals[nom] = 0 if any(t in (typ or "").upper() for t in ("INT", "FLOAT", "REAL", "NUM", "BOOL")) else ""
            cx.execute(f"INSERT INTO jobs ({', '.join(vals)}) VALUES ({', '.join('?' * len(vals))})", list(vals.values()))
        job("j-ok", "done", NOW - timedelta(minutes=10), "Le poulpe")
        job("j-ko", "failed", NOW - timedelta(minutes=5), "Le rate", "fal: 402 insufficient credits")
        job("j-cours", "generating_video", None, "En cours")
        job("j-vieux", "done", NOW - timedelta(days=2), "Le vieux")
        def post(pid, status, run_at, err=None, delegue=None, posted_at=None):
            cx.execute("INSERT INTO scheduled_posts (id, title, caption, channels, run_at, status, mode, error, delegue_a, "
                       "posted_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (pid, "T " + pid, "", "x", run_at, status, "assisted", err, delegue, posted_at, NOW - timedelta(days=3)))
        post("p-geste", "ready", NOW - timedelta(minutes=30))                                   # attend un geste sur le PC
        post("p-echec", "ready", NOW - timedelta(minutes=20), err="x: 403 duplicate content")   # echec de publication
        post("p-a-moi", "ready", NOW - timedelta(minutes=20), delegue=moi)                      # confie a CE telephone
        post("p-autre", "ready", NOW - timedelta(minutes=20), delegue="autre-appareil")         # confie a un autre
        post("p-publie", "posted", NOW - timedelta(days=3), posted_at=NOW - timedelta(minutes=2))  # publie EN RETARD
        post("p-futur", "scheduled", NOW + timedelta(days=1))
        post("p-publie2", "posted", NOW - timedelta(hours=2), posted_at=NOW - timedelta(minutes=40))   # 2e : cles distinctes
        cx.commit()
    finally:
        cx.close()


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as loc:
    H = JA.entetes(app, LAN[0])
    lan = TestClient(app, client=LAN, raise_server_exceptions=False)
    moi = [a for a in loc.get("/api/devices").json()["appareils"] if not a["revoque"]][0]["id"]
    semer(moi)
    from app.services import plafonds as PL
    PL.enregistrer({"global_usd": 0, "par_moteur": {"fal": 10.0, "heygen": 10.0}, "alerte_pct": 80})
    async def _depenses():
        from app.services.storage import Depense, async_session_factory
        async with async_session_factory() as s:
            s.add(Depense(mois=PL.mois_courant(), moteur="fal", categorie="images", estime_usd=8.5))
            s.add(Depense(mois=PL.mois_courant(), moteur="heygen", categorie="avatar", estime_usd=12.0))
            await s.commit()
    asyncio.run(_depenses())

    print("\n[A] acces")
    check("A1 sans jeton depuis le Wi-Fi : 401", lan.get("/api/sync/evenements").status_code == 401)
    check("A2 sans jeton meme en local : 401 (les evenements sont ceux d'un appareil)", loc.get("/api/sync/evenements").status_code == 401)
    r = lan.get("/api/sync/evenements", headers=H)
    e = js(r)
    ev = e.get("evenements", [])
    par = {(x.get("type"), x.get("ref")) for x in ev}
    print("\n[R] rendus")
    check("R1 un rendu « done » donne rendu_termine (le plan filtrait « completed » : muet)", ("rendu_termine", "j-ok") in par, str(par))
    ko = [x for x in ev if x.get("ref") == "j-ko"]
    check("R2 un rendu echoue donne rendu_echoue AVEC sa raison", ko and ko[0]["type"] == "rendu_echoue"
          and "insufficient credits" in ko[0].get("detail", ""), str(ko))
    check("R3 un rendu en cours ne donne rien", not any(x.get("ref") == "j-cours" for x in ev))
    print("\n[P] posts")
    check("P1 un post assiste qui attend un geste : post_a_publier", ("post_a_publier", "p-geste") in par, str(par))
    ec = [x for x in ev if x.get("ref") == "p-echec"]
    check("P2 un echec de publication (ready + erreur) : post_echoue avec sa raison", ec and ec[0]["type"] == "post_echoue"
          and "duplicate" in ec[0].get("detail", ""), str(ec))
    check("P3 D6 : ni le post confie a CE telephone (son rappel local suffit) ni celui d'un AUTRE",
          not any(x.get("ref") in ("p-a-moi", "p-autre") for x in ev), str(par))
    pub = [x for x in ev if x.get("ref") == "p-publie"]
    check("P4 publie : post_publie, date = posted_at (pas run_at)", pub and pub[0]["type"] == "post_publie"
          and pub[0].get("quand", "").startswith((NOW - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M")), str(pub))
    check("P5 un post a venir ne donne rien", not any(x.get("ref") == "p-futur" for x in ev))
    print("\n[L] plafonds (#16)")
    pf = {x.get("ref"): x for x in ev if str(x.get("type", "")).startswith("plafond_")}
    check("L1 fal a 85 % d'un plafond de 10 $ (seuil 80 %) : plafond_approche, chiffres dits",
          pf.get("fal", {}).get("type") == "plafond_approche" and "85" in pf.get("fal", {}).get("detail", "")
          and "10" in pf.get("fal", {}).get("detail", ""), str(pf))
    check("L2 heygen a 120 % : plafond_depasse", pf.get("heygen", {}).get("type") == "plafond_depasse", str(pf))
    print("\n[K] cles et familles")
    cles = [x.get("cle") for x in ev]
    check("K1 chaque evenement a une CLE stable, toutes distinctes", len(cles) >= 7 and all(cles) and len(set(cles)) == len(cles), str(cles))
    r2 = js(lan.get("/api/sync/evenements", headers=H))
    check("K2 relu : les MEMES cles (le telephone dedoublonne)", sorted(x.get("cle") for x in r2.get("evenements", [])) == sorted(cles) and len(cles) >= 7)
    check("K3 les familles du PC (sync_* sont locales au telephone)", set(e.get("familles", [])) == {
          "rendu_termine", "rendu_echoue", "post_a_publier", "post_publie", "post_echoue", "plafond_approche", "plafond_depasse"},
          str(e.get("familles")))
    print("\n[D] depuis")
    depuis = (NOW - timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
    rd = js(lan.get(f"/api/sync/evenements?depuis={depuis}", headers=H)).get("evenements", [])
    refs = {x.get("ref") for x in rd}
    check("D1 `depuis` : un rendu ancien (2 jours) n'est plus rendu, les recents oui", "j-vieux" not in refs and {"j-ok", "j-ko", "p-publie"} <= refs, str(refs))
    check("D2 `depuis` : les ETATS en cours (attend un geste, echec, plafond) restent — leur cle evite le doublon",
          {"p-geste", "p-echec", "fal", "heygen"} <= refs, str(refs))
    futur = (NOW + timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
    rf = js(lan.get(f"/api/sync/evenements?depuis={futur}", headers=H)).get("evenements", [])
    check("D3 `depuis` dans le futur : plus aucun rendu ni publication", not any(x.get("type") in ("rendu_termine", "rendu_echoue", "post_publie")
          for x in rf), str(rf)[:200])
    rx = lan.get("/api/sync/evenements?depuis=nimporte", headers=H)
    check("D4 `depuis` illisible : tout, pas une 500", rx.status_code == 200 and len(ev) >= 7 and len(js(rx).get("evenements", [])) == len(ev), str(rx.status_code))
    check("D5 le rendu ancien est la sans `depuis`", ("rendu_termine", "j-vieux") in par)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
