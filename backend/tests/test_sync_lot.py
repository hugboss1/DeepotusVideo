# -*- coding: utf-8 -*-
"""Plan mobile T8 (tache #57 du suivi, 01/10/2026) — « le Scheduler dans la poche » : le lot part, l'etat revient.
DECISIONS DE L'UTILISATEUR (01/10) : (1) DELEGATION EXPLICITE — un post emporte par un telephone lui est CONFIE ; le
Scheduler du PC ne le publie plus (tick ET « publier maintenant ») tant qu'il ne lui revient pas (echec rapporte,
rendu, reprise a la main, ou appareil revoque) : aucun doublon possible ; (2) UNE SEULE ecriture ouverte au reseau
local en plus de l'appairage : POST /api/sync/lot/etat (jeton exige), qui porte TOUS les statuts du telephone
(emporte, posted, failed, rendu). Le lot ne porte AUCUN jeton (les cles voyagent par l'archive chiffree).
Banc-miroir : LIGNES relues dans la base, vraies requetes portant une IP du reseau local, tick REEL du Scheduler.
Aucun reseau (posts en mode assiste : le tick ne publie rien). Data-dir isole.
Temoin positif : la base (3bfa611e) n'a ni sync_lot ni la colonne delegue_a.
Run (depuis backend/) : & $PY tests/test_sync_lot.py"""
import asyncio, hashlib, json, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsynclot_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "3bfa611e:backend/app/services/storage.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "cat-file", "-e", "3bfa611e:backend/app/services/sync_lot.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni sync_lot ni delegue_a", r0.returncode == 0 and b"delegue_a" not in r0.stdout and r1.returncode != 0)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    """La VRAIE boucle du Scheduler partirait avec le TestClient et ferait son propre tick avant nos delegations :
    seuls les ticks appeles par le banc (S1) comptent."""
    return None
_MAIN.schedule_loop = _boucle_coupee

VIDEO = _tmp / "outputs" / "clip.mp4"
VIDEO.write_bytes(bytes(range(256)) * 16)                           # 4096 o
LAN = ("192.168.1.42", 50000)


def ligne(pid):
    cx = sqlite3.connect(str(_DB))
    try:
        return cx.execute("SELECT status, delegue_a, published_by, error, posted_at FROM scheduled_posts WHERE id=?", (pid,)).fetchone()
    finally:
        cx.close()


def semer():
    cx = sqlite3.connect(str(_DB))
    try:
        cx.execute("DELETE FROM scheduled_posts"); cx.execute("DELETE FROM jobs")
        vals = {"id": "job-1", "status": "completed", "image_filename": "a.png", "final_video_path": str(VIDEO),
                "created_at": datetime.utcnow()}
        for _cid, nom, typ, notnull, defaut, _pk in cx.execute("PRAGMA table_info(jobs)"):
            if notnull and defaut is None and nom not in vals:      # colonnes NOT NULL sans defaut SQL : une valeur neutre
                vals[nom] = 0 if any(t in (typ or "").upper() for t in ("INT", "FLOAT", "REAL", "NUM", "BOOL")) else ""
        cx.execute(f"INSERT INTO jobs ({', '.join(vals)}) VALUES ({', '.join('?' * len(vals))})", list(vals.values()))
        def p(pid, run_at, status, mode="assisted", job=None, canaux="x,telegram", lg="Une legende"):
            cx.execute("INSERT INTO scheduled_posts (id, title, caption, channels, run_at, status, mode, job_id, created_at) "
                       "VALUES (?,?,?,?,?,?,?,?,?)", (pid, pid, lg, canaux, run_at, status, mode, job, datetime.utcnow()))
        now = datetime.utcnow()
        p("p-demain", now + timedelta(days=1), "scheduled", job="job-1")
        p("p-loin", now + timedelta(days=30), "scheduled")
        p("p-fait", now - timedelta(days=1), "posted")
        p("p-du", now - timedelta(minutes=5), "scheduled")            # DU : le tick le traiterait
        p("p-du-libre", now - timedelta(minutes=5), "scheduled")
        p("p-auto-du", now - timedelta(minutes=5), "scheduled", mode="auto")
        cx.commit()
    finally:
        cx.close()


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as loc:
    cols = {r[1] for r in sqlite3.connect(str(_DB)).execute("PRAGMA table_info(scheduled_posts)")}
    check("B1 colonnes delegue_a et delegue_le (migration)", {"delegue_a", "delegue_le"} <= cols, str(sorted(cols))[:200])
    semer()
    H = JA.entetes(app, LAN[0])
    autre = JA.entetes(app, "192.168.1.43")
    lan = TestClient(app, client=LAN, raise_server_exceptions=False)
    lan2 = TestClient(app, client=("192.168.1.43", 50000), raise_server_exceptions=False)
    appareils = loc.get("/api/devices").json()["appareils"]
    moi = [a for a in appareils if not a["revoque"]][0]

    print("\n[L] le lot")
    check("L1 sans jeton : 401", lan.get("/api/sync/lot").status_code == 401)
    r = lan.get("/api/sync/lot?jours=7", headers=H)
    lot = r.json() if r.status_code == 200 else {}
    ids = [p["id"] for p in lot.get("posts", [])]
    check("L2 la fenetre : les posts actionnables des 7 jours (pas le lointain, pas le publie)",
          r.status_code == 200 and set(ids) == {"p-demain", "p-du", "p-du-libre", "p-auto-du"}, f"{r.status_code} {ids}")
    brut = json.dumps(lot).lower()
    check("L3 le lot ne porte AUCUN jeton ni cle", not any(m in brut for m in ("x_api_key", "x_access", "telegram_bot", "api_key", "secret", "token", "jeton")))
    pd = next((p for p in lot.get("posts", []) if p["id"] == "p-demain"), {})
    check("L4 un post porte son media (nom, taille, sha256, url), ses canaux, sa legende, son heure en UTC Z",
          pd.get("media") == {"nom": "clip.mp4", "taille": 4096, "sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
                              "url": "/api/sync/media/job-1"}
          and pd.get("canaux") == ["x", "telegram"] and pd.get("legende") == "Une legende" and str(pd.get("run_at")).endswith("Z")
          and pd.get("confie") is False, str(pd)[:300])
    m = lan.get("/api/sync/media/job-1", headers=H)
    mr = lan.get("/api/sync/media/job-1", headers={**H, "Range": "bytes=100-199"})
    check("L5 le media : octets exacts, et REPRISE par Range (206, 100 octets)", m.status_code == 200 and m.content == VIDEO.read_bytes()
          and mr.status_code == 206 and mr.content == VIDEO.read_bytes()[100:200], f"{m.status_code} {mr.status_code}")
    check("L6 media inconnu : 404 ; sans jeton : 401", lan.get("/api/sync/media/nope", headers=H).status_code == 404
          and lan.get("/api/sync/media/job-1").status_code == 401)
    check("L7 la route media est reservee a un APPAREIL, meme depuis le PC (sans jeton : 401)",
          loc.get("/api/sync/media/job-1").status_code == 401 and loc.get("/api/sync/lot").status_code == 401)

    print("\n[E] emporter (delegation explicite)")
    e = lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-du", "statut": "emporte"}, {"id": "p-demain", "statut": "emporte"},
                                                                      {"id": "p-fait", "statut": "emporte"}, {"id": "nope", "statut": "emporte"}]})
    ej = e.json() if e.status_code == 200 else {}
    check("E1 l'ecriture d'etat passe depuis le reseau local AVEC jeton (seule ecriture ouverte avec l'appairage)",
          e.status_code == 200 and sorted(ej.get("appliques", [])) == ["p-demain", "p-du"], f"{e.status_code} {e.text[:200]}")
    check("E2 les LIGNES portent l'appareil", ligne("p-du")[1] == moi["id"] and ligne("p-demain")[1] == moi["id"], str(ligne("p-du")))
    check("E3 emporter un post deja publie ou inconnu : conflit DIT, rien de change",
          {c["id"] for c in ej.get("conflits", [])} == {"p-fait", "nope"} and ligne("p-fait")[0] == "posted" and ligne("p-fait")[1] is None)
    e2 = lan2.post("/api/sync/lot/etat", headers=autre, json={"rapports": [{"id": "p-du", "statut": "emporte"}, {"id": "p-du", "statut": "posted"}]})
    check("E4 un AUTRE appareil ne peut ni emporter ni publier un post confie au premier", e2.status_code == 200
          and e2.json().get("appliques") == [] and ligne("p-du")[1] == moi["id"] and ligne("p-du")[0] == "scheduled", e2.text[:200])
    l2 = lan2.get("/api/sync/lot?jours=7", headers=autre).json()
    check("E5 le lot de l'autre appareil ne montre PAS les posts confies au premier", {p["id"] for p in l2.get("posts", [])} == {"p-du-libre", "p-auto-du"},
          str([p["id"] for p in l2.get("posts", [])]))
    check("E6 sans jeton, l'ecriture d'etat est refusee (401)", lan.post("/api/sync/lot/etat", json={"rapports": []}).status_code == 401)

    print("\n[S] le Scheduler du PC ne publie PAS un post confie")
    from app.services import marketing
    lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-auto-du", "statut": "emporte"}]})
    asyncio.run(marketing.tick([datetime.utcnow().strftime("%Y-%m-%d")]))
    check("S1 tick REEL : le post DU confie reste au telephone (scheduled), le post DU libre passe a ready (assiste)",
          ligne("p-du")[0] == "scheduled" and ligne("p-du-libre")[0] == "ready", f"{ligne('p-du')} {ligne('p-du-libre')}")
    fp = asyncio.run(marketing.fire_post("p-auto-du"))
    check("S2 « publier maintenant » sur un post confie : refuse AVANT tout appel reseau, le dit, statut intact",
          fp.get("ok") is False and "confi" in str(fp.get("error")) and ligne("p-auto-du")[0] == "scheduled", str(fp))

    print("\n[R] le retour")
    lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-du", "statut": "posted", "detail": "x: ok", "publie_a": "2026-10-04T09:00:00Z"}]})
    st, dl, pb, err, pa = ligne("p-du")
    check("R1 publie par le telephone : posted, published_by = l'appareil, heure gardee, delegation levee",
          st == "posted" and pb == moi["nom"][:40] and str(pa).startswith("2026-10-04 09:00") and dl is None, str(ligne("p-du")))
    lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-demain", "statut": "failed", "detail": "x: 403 duplicate content"}]})
    st, dl, pb, err, _ = ligne("p-demain")
    check("R2 echec rapporte : le post REVIENT au PC (ready, delegation levee), raison et appareil gardes",
          st == "ready" and dl is None and "duplicate content" in (err or "") and moi["nom"] in (err or ""), str(ligne("p-demain")))
    cpost = lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-fait", "statut": "failed", "detail": "timeout"}]}).json()
    check("R3 le PC a le dernier mot : un post publie par le PC n'est pas ecrase, le conflit est RENDU",
          ligne("p-fait")[0] == "posted" and any(c["id"] == "p-fait" and "PC" in c["raison"] for c in cpost.get("conflits", [])), str(cpost))
    check("R4 statut inconnu : ignore et dit", any(c.get("id") == "p-du-libre" and "inconnu" in c.get("raison", "") for c in lan.post("/api/sync/lot/etat", headers=H,
          json={"rapports": [{"id": "p-du-libre", "statut": "efface"}]}).json().get("conflits", [])))

    print("\n[P] reprendre depuis le PC, revoquer")
    rp = loc.post("/api/schedule/p-auto-du/reprendre")
    check("P1 reprendre (PC) : la delegation est levee, le post revient au Scheduler du PC", rp.status_code == 200 and ligne("p-auto-du")[1] is None)
    check("P2 reprendre depuis le reseau local : refuse (ecriture locale)", lan.post("/api/schedule/p-auto-du/reprendre", headers=H).status_code == 403)
    lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-du-libre", "statut": "emporte"}]})
    rv = lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-du-libre", "statut": "rendu"}]}).json()
    check("P3 le telephone REND un post : delegation levee", ligne("p-du-libre")[1] is None and rv.get("appliques") == ["p-du-libre"], str(rv))
    lan.post("/api/sync/lot/etat", headers=H, json={"rapports": [{"id": "p-du-libre", "statut": "emporte"}]})
    loc.post(f"/api/devices/{moi['id']}/revoke")
    check("P4 appareil REVOQUE (perdu) : ses posts reviennent au PC tout de suite", ligne("p-du-libre")[1] is None, str(ligne("p-du-libre")))
    li = loc.get("/api/schedule").json()
    items = li if isinstance(li, list) else (li.get("posts") or li.get("items") or [])
    check("P5 la liste du Scheduler expose delegue_a (l'ecran pourra le montrer)", items and all("delegue_a" in p for p in items), str(items[:1])[:200])

print("\n[U] l'ecran du Scheduler (bundle ecrit)")
import shutil as _sh                                                # noqa: E402
_B = (_ICI.parents[1] / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8")
check("U1 le post du Scheduler porte la delegation (wh : delegueA)", _B.count("brief:e.brief||null,delegueA:e.delegue_a||null}}") == 1)
# t142 (09/10) : la traduction L2 passe le libelle, le title et les toasts par dzT("cle") ; la borne de fin suit la cle,
# le francais de chaque cle reste verifie, et le clic s'execute avec le prelude dzT (en francais)
import _i18n_l1_aide as AIDE                                        # noqa: E402
i_b = _B.find("e.delegueA&&r.jsx(K,{")
bouton = _B[i_b:_B.find('children:dzT("scheduler.post.confie")})', i_b)]
check("U2 l'inspecteur : bouton SEULEMENT pour un post confie, avec un title qui dit que le PC ne le publiera pas",
      i_b > 0 and _B.find('children:dzT("scheduler.post.confie")})', i_b) > i_b
      and AIDE.fr("scheduler.post.confie") == "Confié au téléphone · Reprendre sur le PC"
      and 'title:dzT("scheduler.post.confie_aide")' in bouton
      and "le PC ne le publiera pas" in AIDE.fr("scheduler.post.confie_aide") and "/reprendre" in bouton)
_node = _sh.which("node")
if _node and i_b > 0:
    clic = bouton[bouton.find("onClick:") + len("onClick:"):bouton.rfind(",")]
    js = ("(function(){\n" + AIDE.PRELUDE_DZT + "\n})();\n"   # t142 : dzT publie sur globalThis, son window a lui
          "var appels=[],toasts=[],evts=[];globalThis.__dzToast=function(m){toasts.push(m)};"
          "globalThis.window={dispatchEvent:function(e){evts.push(e.type)}};globalThis.CustomEvent=function(t){this.type=t};"
          "globalThis.fetch=function(u,o){appels.push([u,o&&o.method]);return Promise.resolve({ok:true,status:200})};"
          "var e={id:'p 1',delegueA:'d1'};var f=" + clic + ";f();"
          "setTimeout(function(){console.log(JSON.stringify({appels:appels,toasts:toasts,evts:evts}))},30);")
    fj = _tmp / "u.mjs"; fj.write_text(js, encoding="utf-8")
    pn = subprocess.run([_node, str(fj)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        oj = json.loads(pn.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        oj = {}
        print(pn.stdout[-400:], pn.stderr[-800:])
    check("U3 cliquer : POST /api/schedule/<id encode>/reprendre, toast, la liste se recharge",
          oj.get("appels") == [["/api/schedule/p%201/reprendre", "POST"]] and "repris" in str(oj.get("toasts"))
          and oj.get("evts") == ["deepotus:schedule-reload"], str(oj))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
