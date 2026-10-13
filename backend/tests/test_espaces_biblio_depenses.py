# -*- coding: utf-8 -*-
"""t209 (Espaces de marque E9, 14/10/2026) — la Bibliothèque et les dépenses PAR ESPACE (spec D8).
Ce que ce banc garde :
  - migration : `espace_id` ajouté à jobs, library_assets, library_projects et depenses ; une base d'AVANT (lignes
    sans espace) garde ses lignes, et elles sont à Deepotus ;
  - Bibliothèque : GET /images et GET /jobs filtrés par `espace` (« * » ou absent = tout, comme avant) ; un fichier
    jamais indexé est à Deepotus ; un fichier noté ou un job créé prend l'espace de la requête ;
  - projets : rattachés à l'espace de leur création ; la liste suit l'espace courant (« * » = tous) ; le projet ACTIF
    est propre à chaque espace (Deepotus garde sa clé d'avant) et le rangement automatique va dans celui de l'espace ;
  - dépenses : chaque ligne porte son espace ; tableau et état par espace ; relevé CSV d'un espace et d'un mois
    (en-têtes et nombres dans la langue de la requête, total, nom de fichier) ; 404 espace inconnu, 400 mois illisible ;
  - plafond OPTIONNEL par espace (Réglages › Espaces) : 402 motif « espace » au-delà, confirmable, sans effet sur les
    autres espaces ; une valeur illisible vaut « aucun ».
Data-dir isolé, aucune clé, rien de payé. Témoin : la base (f2abddd8) n'a pas depenses.espace_id.
Run (depuis backend/) : & $PY tests/test_espaces_biblio_depenses.py"""
import asyncio, csv, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzebd_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY"):
    os.environ[k] = ""
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


r0 = subprocess.run(["git", "show", "f2abddd8:backend/app/services/storage.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas depenses.espace_id", r0.returncode == 0 and b"DEPENSES_COLUMNS" not in r0.stdout)

# une base d'AVANT t209 : depenses et library_projects existent déjà, sans espace, avec une ligne chacune
MOIS = __import__("time").strftime("%Y-%m")
db = sqlite3.connect(_tmp / "t.db")
db.executescript(f"""
CREATE TABLE depenses (id INTEGER PRIMARY KEY AUTOINCREMENT, quand DATETIME, mois VARCHAR(7), moteur VARCHAR(24),
  categorie VARCHAR(24), op VARCHAR(32), estime_usd FLOAT, reel_usd FLOAT, reel_unites FLOAT, ref VARCHAR(64));
INSERT INTO depenses (quand, mois, moteur, categorie, op, estime_usd) VALUES ('{MOIS}-01 10:00:00', '{MOIS}', 'fal', 'quick', 'image', 0.5);
CREATE TABLE library_projects (id VARCHAR(36) PRIMARY KEY, nom VARCHAR(120), couleur VARCHAR(7), note TEXT,
  epingle INTEGER, created_at DATETIME);
INSERT INTO library_projects (id, nom, created_at) VALUES ('proj_ancien', 'Ancien projet', '2026-10-01 10:00:00');
""")
db.commit(); db.close()

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
c.__enter__()                                                       # lifespan : init_db (create_all + auto-migration)
from app.services import espaces as ES, library_index as LI, library_projects as LP, plafonds as P   # noqa: E402
from app.services.storage import JobRecord, async_session_factory  # noqa: E402

print("[M] migration")
con = sqlite3.connect(_tmp / "t.db")
for t in ("jobs", "library_assets", "library_projects", "depenses"):
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
    check(f"M1 {t}.espace_id présente", "espace_id" in cols, str(sorted(cols))[:160])
check("M2 les lignes d'avant sont gardées, sans espace",
      con.execute("SELECT count(*), max(espace_id) FROM depenses").fetchone() == (1, None)
      and con.execute("SELECT nom, espace_id FROM library_projects").fetchone() == ("Ancien projet", None))
con.close()

ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]


def png(nom):
    from PIL import Image
    Image.new("RGB", (4, 4), (10, 20, 30)).save(_tmp / "images" / nom)


async def preparer():
    png("legacy_sans_index.png")
    png("deep_quick.png")
    png("rip_quick.png")
    au = _tmp / "audio"
    au.mkdir(exist_ok=True)
    for n in ("legacy.mp3", "rip.mp3"):
        (au / n).write_bytes(b"ID3")
    await LI.noter(["deep_quick.png"], "quick")
    with ES.sous_espace(rip):
        await LI.noter(["rip_quick.png"], "quick")
        await LI.noter(["rip.mp3"], "son", kind="audio")
    async with async_session_factory() as s:
        s.add(JobRecord(id="job_legacy", status="done", title="legacy", image_filename="x.png"))
        s.add(JobRecord(id="job_deep", status="done", title="deep", image_filename="x.png"))
        await s.commit()
    with ES.sous_espace(rip):
        async with async_session_factory() as s:
            s.add(JobRecord(id="job_rip", status="done", title="rip", image_filename="x.png"))
            await s.commit()
asyncio.run(preparer())
con = sqlite3.connect(_tmp / "t.db")
con.execute("UPDATE jobs SET espace_id=NULL WHERE id='job_legacy'")      # un job d'avant les espaces
con.commit()
jes = dict(con.execute("SELECT id, espace_id FROM jobs").fetchall())
con.close()
check("B0 un job créé prend l'espace de la requête", jes == {"job_legacy": None, "job_deep": "deepotus", "job_rip": rip}, str(jes))

print("[B] la Bibliothèque par espace")
def noms(r):
    return sorted(i["filename"] for i in r.json()["images"])
tous = ["deep_quick.png", "legacy_sans_index.png", "rip_quick.png"]
check("B1 /images sans filtre : tout, comme avant", noms(c.get("/api/images")) == tous, str(noms(c.get("/api/images"))))
check("B2 /images?espace=* : tout", noms(c.get("/api/images?espace=*")) == tous)
check("B3 /images?espace=deepotus : le sien + le jamais indexé",
      noms(c.get("/api/images?espace=deepotus")) == ["deep_quick.png", "legacy_sans_index.png"], str(noms(c.get("/api/images?espace=deepotus"))))
check("B4 /images?espace=<Rippled> : le sien seulement", noms(c.get(f"/api/images?espace={rip}")) == ["rip_quick.png"])
def jobs(q):
    return sorted(j["job_id"] for j in c.get("/api/jobs?limit=50" + q).json())
check("B5 /jobs sans filtre : tous", jobs("") == ["job_deep", "job_legacy", "job_rip"], str(jobs("")))
check("B6 /jobs?espace=deepotus : le sien + celui d'avant", jobs("&espace=deepotus") == ["job_deep", "job_legacy"], str(jobs("&espace=deepotus")))
check("B7 /jobs?espace=<Rippled>", jobs(f"&espace={rip}") == ["job_rip"], str(jobs(f"&espace={rip}")))
check("B8 /jobs?espace=* : tous", jobs("&espace=*") == ["job_deep", "job_legacy", "job_rip"])
def sons(q):
    return sorted(a["name"] for a in c.get("/api/audio" + q).json()["audio"])
check("B9 /audio : tout sans filtre, le jamais indexé à Deepotus, le son de Rippled à Rippled",
      sons("") == ["legacy.mp3", "rip.mp3"] and sons("?espace=deepotus") == ["legacy.mp3"] and sons(f"?espace={rip}") == ["rip.mp3"],
      str((sons(""), sons("?espace=deepotus"), sons(f"?espace={rip}"))))

print("[P] projets")
pd = c.post("/api/library/projets", json={"nom": "Campagne Deepotus"}).json()
ES.activer(rip)
pr = c.post("/api/library/projets", json={"nom": "Lancement Rippled"}).json()
def pids(q=""):
    return sorted(p["id"] for p in c.get("/api/library/projets" + q).json()["projets"])
lr = c.get("/api/library/projets").json()
check("P1 la liste suit l'espace courant (Rippled)", pids() == [pr["projet"]["id"]] if "projet" in pr else pids() == [pr["id"]], str(lr)[:200])
PR_ID = pr.get("projet", pr).get("id")
PD_ID = pd.get("projet", pd).get("id")
check("P2 « * » = tous, l'ancien compris", pids("?espace=*") == sorted([PR_ID, PD_ID, "proj_ancien"]), str(pids("?espace=*")))
c.put("/api/library/projets/actif", json={"id": PR_ID})
check("P3 projet actif de Rippled", c.get("/api/library/projets/actif").json().get("id") == PR_ID)
async def ranger_rip():
    with ES.sous_espace(rip):
        return await LP.ranger_dans_actif(["rip_quick.png"])
check("P4 le rangement d'un tir de Rippled va dans le projet actif de Rippled", asyncio.run(ranger_rip()) == 1
      and [i["ref"] for i in c.get(f"/api/library/projets/{PR_ID}").json()["items"]] == ["rip_quick.png"])
ES.activer("deepotus")
check("P5 Deepotus : la liste a son projet ET l'ancien", pids() == sorted([PD_ID, "proj_ancien"]), str(pids()))
check("P6 Deepotus n'a pas hérité du projet actif de Rippled", c.get("/api/library/projets/actif").json().get("id") == "")
c.put("/api/library/projets/actif", json={"id": "proj_ancien"})
con = sqlite3.connect(_tmp / "t.db")
cle = con.execute("SELECT key FROM atelier_settings WHERE value='proj_ancien'").fetchall()
con.close()
check("P7 l'actif de Deepotus garde la clé d'avant (library_projet_actif)", cle == [("library_projet_actif",)], str(cle))
ES.activer(rip)
check("P8 Rippled retrouve son actif", c.get("/api/library/projets/actif").json().get("id") == PR_ID)
ES.activer("deepotus")

print("[D] dépenses par espace")
async def tirer():
    await P.verifier({"kind": "image", "n": 2, "model": "flux"}, "quick")
    with ES.sous_espace(rip):
        await P.verifier({"kind": "image", "n": 4, "model": "flux"}, "quick")
asyncio.run(tirer())
con = sqlite3.connect(_tmp / "t.db")
es = sorted((r[0] or "") for r in con.execute("SELECT espace_id FROM depenses"))
con.close()
check("D1 chaque ligne porte l'espace du tir (l'ancienne reste vide)", es == ["", "deepotus", rip], str(es))
tr = asyncio.run(P.tableau(espace=rip))
td = asyncio.run(P.tableau(espace="deepotus"))
tt = asyncio.run(P.tableau())
check("D2 tableau par espace ; Deepotus compte l'ancienne ligne ; sans espace = tout",
      tr["total"]["estime_usd"] > 0 and abs(td["total"]["estime_usd"] - 0.5 - tr["total"]["estime_usd"] / 2) < 1e-6
      and abs(tt["total"]["estime_usd"] - td["total"]["estime_usd"] - tr["total"]["estime_usd"]) < 1e-6,
      str((tr["total"], td["total"], tt["total"])))
r = c.get(f"/api/reglages/depenses?espace={rip}").json()
check("D3 GET /reglages/depenses?espace=", abs(r["total"]["estime_usd"] - tr["total"]["estime_usd"]) < 1e-9, str(r)[:200])
pe = c.get("/api/reglages/depenses/espaces").json()
check("D4 dépenses du mois par espace (tous les espaces, plafond dit)",
      set(pe["par_espace"]) >= {"deepotus", rip} and abs(pe["par_espace"][rip]["effectif_usd"] - tr["total"]["effectif_usd"]) < 1e-9
      and pe["par_espace"][rip]["plafond_usd"] == 0 and pe["mois"] == MOIS, str(pe)[:300])

print("[R] relevé exportable")
rv = c.get(f"/api/reglages/depenses/releve?espace={rip}&mois={MOIS}")
lignes = list(csv.reader(io.StringIO(rv.content.decode("utf-8-sig")), delimiter=";"))
check("R1 CSV en pièce jointe, nommé d'après l'espace et le mois", rv.status_code == 200
      and rv.headers["content-type"].startswith("text/csv") and f"releve_rippled_{MOIS}.csv" in rv.headers.get("content-disposition", ""),
      str((rv.status_code, rv.headers.get("content-type"), rv.headers.get("content-disposition"))))
check("R2 en-têtes français, une ligne de tir, une ligne de total (virgule décimale)",
      lignes and lignes[0][:3] == ["Date", "Moteur", "Écran"] and len(lignes) == 3 and lignes[1][1] == "fal"
      and lignes[2][0] == "Total" and "," in lignes[2][6], str(lignes))
rv_en = c.get(f"/api/reglages/depenses/releve?espace={rip}&mois={MOIS}", headers={"Accept-Language": "en"})
le = list(csv.reader(io.StringIO(rv_en.content.decode("utf-8-sig")), delimiter=","))
check("R3 en anglais : virgule séparatrice, point décimal", le and le[0][:3] == ["Date", "Engine", "Screen"]
      and le[2][0] == "Total" and "." in le[2][6], str(le))
rd = list(csv.reader(io.StringIO(c.get(f"/api/reglages/depenses/releve?espace=deepotus&mois={MOIS}").content.decode("utf-8-sig")), delimiter=";"))
check("R4 relevé Deepotus : son tir ET la ligne d'avant", len(rd) == 4, str(rd))
check("R5 espace inconnu 404, mois illisible 400",
      c.get("/api/reglages/depenses/releve?espace=nope").status_code == 404
      and c.get(f"/api/reglages/depenses/releve?espace={rip}&mois=2026-1").status_code == 400)

print("[L] plafond par espace")
rr = c.post(f"/api/espaces/{rip}", json={"plafond_usd": 0.01})
check("L1 plafond enregistré et rendu par la vue", rr.status_code == 200 and rr.json()["espace"]["plafond_usd"] == 0.01, rr.text[:200])
async def tir(eid, confirme=None):
    with ES.sous_espace(eid):
        try:
            await P.verifier({"kind": "image", "n": 1, "model": "flux"}, "quick", confirme=confirme)
            return "ok"
        except Exception as e:  # noqa: BLE001
            return getattr(e, "detail", repr(e))
d = asyncio.run(tir(rip))
check("L2 au-delà : 402 motif espace, nom de l'espace dans le message",
      isinstance(d, dict) and d["dz_plafond"]["motif"] == "espace" and "Rippled" in d["dz_plafond"]["message"], str(d))
check("L3 confirmé : passe", asyncio.run(tir(rip, confirme=True)) == "ok")
check("L4 un autre espace n'est pas concerné", asyncio.run(tir("deepotus")) == "ok")
for mauvais in ("-3", '"abc"', "1e999", "true"):
    c.post(f"/api/espaces/{rip}", content=('{"plafond_usd": ' + mauvais + '}').encode(), headers={"Content-Type": "application/json"})
    vue = [e for e in ES.lister() if e["id"] == rip][0]
    check(f"L5 {mauvais!r} vaut aucun plafond", vue["plafond_usd"] == 0 and asyncio.run(tir(rip)) == "ok", str(vue))
c.post(f"/api/espaces/{rip}", json={"plafond_usd": 25})
pe = c.get("/api/reglages/depenses/espaces").json()["par_espace"]
check("L6 /depenses/espaces dit le plafond et le pourcentage", pe[rip]["plafond_usd"] == 25
      and abs(pe[rip]["pct"] - round(100 * pe[rip]["effectif_usd"] / 25, 1)) < 1e-9 and pe["deepotus"]["plafond_usd"] == 0, str(pe))

from app.services import pricing as PRI                             # noqa: E402
c1 = PRI.estimate({"kind": "image", "n": 1, "model": "flux"})["total_usd"]
pe = c.get("/api/reglages/depenses/espaces").json()["par_espace"]
juste = round(pe[rip]["effectif_usd"] + c1 + 0.001, 4)
c.post(f"/api/espaces/{rip}", json={"plafond_usd": juste})
check("L7 le plafond de Rippled ne compte QUE les dépenses de Rippled (Deepotus a dépensé bien plus)",
      pe["deepotus"]["effectif_usd"] > juste - pe[rip]["effectif_usd"] and asyncio.run(tir(rip)) == "ok"
      and isinstance(asyncio.run(tir(rip)), dict), str((pe, juste, c1)))
c.post(f"/api/espaces/{rip}", json={"plafond_usd": 0})

print("[E] écran (maillon dzespace)")
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8")
SITES = {
    "B1 listImages accepte un filtre": 'listImages:(dzQ)=>Ge("/images"+(dzQ||""),{images:[]})',
    "B2 listJobs accepte un filtre": 'listJobs:(e=50,dzQ)=>Ge(`/jobs?limit=${e}`+(dzQ||""),[])',
    "B3 listAudio accepte un filtre": 'listAudio:(dzQ)=>Ge("/audio"+(dzQ||""),{audio:[]})',
    "B4 la Bibliothèque passe l'espace aux trois": '[D.listImages(dzBibQ("?")),D.listJobs(80,dzBibQ("&")),D.listAudio(dzBibQ("?"))]',
    "B5 elle se recharge sur dz-bib-esp": 'window.addEventListener("dz-bib-esp",dzBq);return()=>{C=!1,clearInterval(ee),window.removeEventListener("dz-bib-esp",dzBq)}',
    "B6 le sélecteur dans l'en-tête": 'onChange:v=>LsortS(v),style:{width:130}}),r.jsx(DzBibEspace,{}),',
    "E1 la ligne de chaque espace montre sa dépense": 'r.jsx(DzDepEspace,{espace:e.id},"dep:"+e.id)]},e.id)',
}
for nom, motif in SITES.items():
    check(nom, BUNDLE.count(motif) == 1)
check("E2 aucun useState ajouté, les autres appels de l'API inchangés",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("D.listImages()") == 4 and BUNDLE.count("D.listJobs(") == 6)
sys.path.insert(0, str(RACINE / "scripts"))
import patch_bundle_dzespace as DZE                                   # noqa: E402
try:
    avant = DZE.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)
check("E3 l'inverse du maillon rend la Bibliothèque d'avant, aller-retour exact",
      "dzBibQ" not in avant and "[D.listImages(),D.listJobs(80),D.listAudio()]" in avant and DZE.appliquer(avant) == BUNDLE, avant[:120])
i = BUNDLE.index("var dzBibTous=!1;")
fn = BUNDLE[i:BUNDLE.index("function DzBibEspace(", i)]
js = ("var window={addEventListener:function(){},dispatchEvent:function(){}};" + fn +
      ";var R=[];R.push(dzBibQ('?'));var dzEspCache={actif:'deepotus'};R.push(dzBibQ('?'));"
      "dzEspCache={actif:'esp 1'};R.push(dzBibQ('&'));dzBibTous=!0;R.push(dzBibQ('?'));console.log(JSON.stringify(R))")
rn = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
check("E4 dzBibQ : rien tant que les espaces ne sont pas lus, l'espace actif encodé, rien pour « tous »",
      rn.stdout.strip() == json.dumps(["", "?espace=deepotus", "&espace=esp%201", ""], separators=(",", ":")), rn.stdout + rn.stderr)

print(f"\n{ok} PASS / {fail} FAIL")
c.__exit__(None, None, None)
sys.exit(1 if fail else 0)
