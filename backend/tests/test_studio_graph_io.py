# -*- coding: utf-8 -*-
"""Plan-studio T6 (tache #69 du suivi, 02/10/2026) — IMPORTER un graphe JSON dans le Studio : le registre des noeuds
MIROITE cote serveur, la validation qui refuse en NOMMANT le fautif, la route qui dit ce qui manque sur cette machine.
DECISIONS DE L'UTILISATEUR (02/10) : registre en miroir JSON + banc de derive ; graphe ouvert + dialogue qui liste les
sources manquantes et les aretes jetees ; rien n'est enregistre (« Save » le garde) ; bouton dans le maillon montage.
Ce que le plan faisait faux, et que ce banc garde : l'export du Studio ecrit le graphe NU mais le magasin l'enveloppe
({id, name, graph}) — les deux formes s'importent ; le graphe importe ne garde PAS l'id d'origine (sinon « Save »
ecraserait l'enregistrement d'une autre machine) ; un UGC (Upload) cite aussi un rendu.
Data-dir isole, cles de banc, aucun appel paye. Temoin positif : la base (bdb70ceb) n'a ni le module ni la route.
Run (depuis backend/) : & $PY tests/test_studio_graph_io.py"""
import copy, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzimp_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
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


BASE = "bdb70ceb"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/studio_graph.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni le module ni la route d'import", r0.returncode != 0 and r1.returncode == 0
      and b'"/studio-graphs/import"' not in r1.stdout)

BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
MIROIR = RACINE / "backend" / "app" / "assets" / "studio_nodes.json"

print("[A] le registre miroite")
doc = json.loads(MIROIR.read_bytes().decode("utf-8")) if MIROIR.is_file() else {"count": 0, "types": {}}
T = doc["types"]
check("A1 34 types, chacun present au registre du bundle avec sa categorie et son titre", doc["count"] == 34 == len(T)
      and all(f'{n}:{{cat:"{d["cat"]}",title:"{d["title"]}"' in BUN for n, d in T.items()), str(doc["count"]))
check("A2 les ports sont ceux du bundle (Seedance image/end/prompt -> out ; Render in/overlay/audio/fx ; Image sans entree)",
      T.get("Seedance", {}).get("in") == ["image", "end", "prompt"] and T.get("Render", {}).get("in") == ["in", "overlay", "audio", "fx"]
      and T.get("Image", {}).get("in") == [] and T.get("Image", {}).get("out") == ["out"] and T.get("Render", {}).get("out") == [])
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "qa" / "dump_studio_registry.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", cwd=str(RACINE))
check("A3 DERIVE : le miroir suit le bundle livre (dump --check)", r.returncode == 0 and "a jour (34 types)" in r.stdout, r.stdout + r.stderr)
import importlib.util, io, contextlib                               # noqa: E402
_sp = importlib.util.spec_from_file_location("dz_dump", RACINE / "scripts" / "qa" / "dump_studio_registry.py")
DUMP = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(DUMP)
_perime = _tmp / "miroir_perime.json"
_d = json.loads(MIROIR.read_bytes().decode("utf-8")) if MIROIR.is_file() else {"types": {}}
_d.get("types", {}).pop("Upscale", None)
_perime.write_bytes(DUMP.texte(_d).encode("utf-8"))
DUMP.CIBLE, _argv, _out = _perime, sys.argv, io.StringIO()
sys.argv = ["dump", "--check"]
with contextlib.redirect_stdout(_out):
    _rc = DUMP.main()
sys.argv = _argv
check("A4 un miroir PERIME (un type de moins) est denonce par --check, sans etre reecrit",
      _rc == 1 and "DERIVE" in _out.getvalue() and "Upscale" not in _perime.read_text(encoding="utf-8"), _out.getvalue())

print("\n[V] la validation")
try:
    from app.services import studio_graph as SG                     # noqa: E402
except ImportError as e:
    SG = None
    check("V0 le module existe", False, str(e))


def sain():
    return {"name": "essai", "id": "g_autre",
            "nodes": [{"id": "im", "type": "Image", "x": 0, "y": "12", "props": {"filename": "trone.png", "inconnu": 7}},
                      {"id": "sd", "type": "Seedance", "x": 300, "y": 0, "props": {"durationS": 10}},
                      {"id": "rn", "type": "Render", "x": 600, "y": 0}],
            "edges": [{"id": "e1", "from": "im", "fromPort": "out", "to": "sd", "toPort": "image"},
                      {"id": "e2", "from": "sd", "fromPort": "out", "to": "rn", "toPort": "in"}]}


def refus(g):
    try:
        SG.valider(g)
    except ValueError as e:
        return str(e)
    return None


if SG:
    g, av, mq = SG.valider(sain())
    check("V1 un graphe sain passe, normalise : props inconnues GARDEES, x/y numeriques, props absentes -> {}",
          [n["id"] for n in g["nodes"]] == ["im", "sd", "rn"] and g["nodes"][0]["props"] == {"filename": "trone.png", "inconnu": 7}
          and g["nodes"][0]["y"] == 0.0 and g["nodes"][2]["props"] == {} and len(g["edges"]) == 2 and av == [] and mq == [], str(g))
    check("V2 le graphe rendu n'a PAS d'id (il s'ouvre non enregistre) et garde son nom", "id" not in g and g["name"] == "essai")
    m = sain(); m["nodes"][1]["type"] = "SoraDeluxe"
    e = refus(m)
    check("V3 type inconnu : REFUS qui nomme le type, le noeud et le nombre de types connus", bool(e) and "SoraDeluxe" in e and "sd" in e and "34" in e, str(e))
    m = sain(); m["nodes"][2]["id"] = "im"
    e = refus(m)
    check("V4 identifiant en double : refus qui le nomme", bool(e) and "double" in e and "im" in e, str(e))
    m = sain(); m["nodes"].append({"id": "sd2", "type": "Seedance"})
    m["edges"] += [{"from": "sd", "fromPort": "out", "to": "sd2", "toPort": "end"}, {"from": "sd2", "fromPort": "out", "to": "sd", "toPort": "prompt"}]
    e = refus(m)
    check("V5 cycle : refus qui nomme les noeuds bloques (et pas les autres)", bool(e) and "cycle" in e and "sd, sd2" in e and "im" not in e.split("(")[1], str(e))
    m = sain(); m["nodes"].append({"id": "rn2", "type": "Render"})
    e = refus(m)
    check("V6 deux noeuds Render : refus qui les nomme", bool(e) and "Render" in e and "rn, rn2" in e, str(e))
    m = sain(); m["edges"][0]["toPort"] = "fantome"; m["edges"][1]["fromPort"] = "spectre"
    gg, av, _ = SG.valider(m)
    check("V7 arete sur un port inexistant (entree OU sortie) : JETEE et dite avec le port, le type et le noeud",
          gg["edges"] == [] and any("fantome" in a and "Seedance" in a and "(sd)" in a for a in av)
          and any("spectre" in a and "sortie" in a for a in av) and len(av) == 2, str(av))
    m = sain(); m["edges"].append({"from": "im", "fromPort": "out", "to": "nulle_part", "toPort": "in"}); m["edges"].append("x")
    gg, av, _ = SG.valider(m)
    check("V8 arete vers un noeud absent, arete qui n'est pas un objet : jetees et dites", len(gg["edges"]) == 2 and len(av) == 2
          and any("nulle_part" in a for a in av), str(av))
    m = sain(); m["edges"][1]["id"] = "e1"
    ids = [x["id"] for x in SG.valider(m)[0]["edges"]]
    m2 = sain(); del m2["edges"][0]["id"]
    ids2 = [x["id"] for x in SG.valider(m2)[0]["edges"]]
    check("V9 les identifiants d'aretes sortent uniques : doublon -> suffixe (le premier garde le sien), absent -> derive",
          ids[0] == "e1" and len(set(ids)) == 2 and ids2 == ["e_im_sd_image", "e2"], f"{ids} {ids2}")
    m = sain()
    m["nodes"] += [{"id": "er", "type": "ExistingRender", "props": {"jobId": "job_disparu"}},
                   {"id": "ug", "type": "Upload", "props": {"jobId": "job_ugc", "filename": "x.mp4"}},
                   {"id": "vo", "type": "Voiceover", "props": {"filename": "voix.mp3"}},
                   {"id": "ig", "type": "ImageGen", "props": {"filename": "gen.png"}}]
    _, _, mq = SG.valider(m, images=set(), jobs=set())
    par = {x["node_id"]: x for x in mq}
    check("V10 sources ABSENTES : image d'un noeud Image, rendu d'un ExistingRender ET d'un UGC — avec noeud, champ, valeur",
          sorted(par) == ["er", "im", "ug"] and par["im"]["champ"] == "filename" and par["im"]["valeur"] == "trone.png"
          and par["er"]["valeur"] == "job_disparu" and par["ug"]["champ"] == "jobId" and par["ug"]["magasin"] == "jobs", str(mq))
    _, _, mq2 = SG.valider(m, images={"trone.png"}, jobs={"job_disparu", "job_ugc"})
    _, _, mq3 = SG.valider(m)
    check("V11 une source PRESENTE ne remonte pas ; None = pas de verification", mq2 == [] and mq3 == [], f"{mq2} {mq3}")
    mauvais = [None, [], "x", {"nodes": []}, {"nodes": "x", "edges": []}, {"nodes": [{"type": "Image"}]},
               {"nodes": [{"id": "a", "type": "Image"}], "edges": "x"}, {"nodes": ["a"]}, {"graph": {"nodes": []}}]
    rs = [refus(x) for x in mauvais]
    check("V12 ce qui n'est pas un graphe est refuse, avec une phrase (jamais une exception brute)", all(isinstance(x, str) and len(x) > 15 for x in rs), str(rs))
    gros = {"nodes": [{"id": f"n{i}", "type": "Text"} for i in range(201)]}
    check("V13 au-dela de 200 noeuds : refus dit", "200" in (refus(gros) or ""))
    rec = {"id": "g_123", "name": "Du magasin", "graph": {k: v for k, v in sain().items() if k != "id"}, "updated_at": "x"}
    gg, _, _ = SG.valider(rec)
    check("V14 un ENREGISTREMENT du magasin ({id, name, graph}) s'importe : son graphe, le nom de la LISTE (pas celui du graphe), sans id",
          len(gg["nodes"]) == 3 and gg["name"] == "Du magasin" and "id" not in gg, str(gg)[:200])
    m = sain(); del m["edges"]; m["name"] = "  "
    gg, _, _ = SG.valider(m)
    check("V15 sans aretes ni nom : accepte, nomme « Graphe importé »", gg["edges"] == [] and gg["name"] == "Graphe importé")

print("\n[R] la route")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def job(jid):
    cx = sqlite3.connect(str(_DB))
    cols = cx.execute("PRAGMA table_info(jobs)").fetchall()
    val = {c[1]: (0 if "INT" in (c[2] or "").upper() else "") for c in cols if c[3] and c[4] is None}
    val.update({"id": jid, "status": "done"})
    cx.execute(f"INSERT INTO jobs ({','.join(val)}) VALUES ({','.join('?' * len(val))})", list(val.values()))
    cx.commit(); cx.close()


GDIR = _tmp / "studio_graphs"
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    g = sain(); g["nodes"].append({"id": "er", "type": "ExistingRender", "props": {"jobId": "job_la"}})
    r = c.post("/api/studio-graphs/import", json={"graph": g})
    d = r.json() if r.status_code == 200 else {}
    check("R1 200 : le graphe normalise, et ce qui manque ICI (l'image et le rendu absents)", r.status_code == 200
          and len(d.get("graph", {}).get("nodes", [])) == 4 and sorted(x["node_id"] for x in d.get("missing", [])) == ["er", "im"]
          and d.get("warnings") == [] and "id" not in d.get("graph", {}), f"{r.status_code} {r.text[:300]}")
    (_tmp / "images" / "trone.png").write_bytes(b"x")
    job("job_la")
    r = c.post("/api/studio-graphs/import", json={"graph": g})
    check("R2 l'image presente et le rendu en base ne manquent plus", r.status_code == 200 and r.json()["missing"] == [], r.text[:300])
    g2 = copy.deepcopy(g); g2["nodes"][0]["props"]["filename"] = "../images/trone.png"
    r = c.post("/api/studio-graphs/import", json={"graph": g2})
    check("R3 un nom d'image avec chemin n'est jamais cherche hors du dossier : il MANQUE", r.status_code == 200
          and [x["node_id"] for x in r.json()["missing"]] == ["im"], r.text[:300])
    r = c.post("/api/studio-graphs/import", json={"graph": {"id": "g_9", "name": "Rec", "graph": g, "updated_at": "x"}})
    check("R4 un enregistrement du magasin s'importe aussi", r.status_code == 200 and r.json()["graph"]["name"] == "Rec", r.text[:200])
    m = sain(); m["nodes"][0]["type"] = "Inconnu"
    r = c.post("/api/studio-graphs/import", json={"graph": m})
    check("R5 type inconnu : 400 avec la phrase qui le nomme", r.status_code == 400 and "Inconnu" in r.json().get("detail", ""), r.text[:200])
    rs = [c.post("/api/studio-graphs/import", json=x).status_code for x in ({}, {"graph": None}, {"graph": [1]})]
    check("R6 corps sans graphe : 400 (pas de 500)", rs == [400, 400, 400], str(rs))
    check("R7 l'import N'ENREGISTRE rien (magasin des graphes vide)", not any(GDIR.glob("*.json")) if GDIR.is_dir() else True)
with TestClient(app, client=("10.0.0.7", 50000), raise_server_exceptions=False) as c2:
    r = c2.post("/api/studio-graphs/import", json={"graph": sain()})
    check("R8 reserve a la machine locale (401 de _require_localhost)", r.status_code == 401, str(r.status_code))
import asyncio, types                                               # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
import app.api.routes as RT                                         # noqa: E402
try:
    asyncio.run(RT.import_studio_graph({"graph": sain()}, types.SimpleNamespace(client=types.SimpleNamespace(host="10.0.0.7"))))
    _st = 200
except HTTPException as e:
    _st = e.status_code
check("R8b la ROUTE elle-meme refuse un client distant (403), meme si les middlewares changent", _st == 403, str(_st))
src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("R9 la route n'est pas payante (absente du recensement)", "/studio-graphs/import" not in src)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
