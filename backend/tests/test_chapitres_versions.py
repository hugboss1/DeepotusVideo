# -*- coding: utf-8 -*-
"""Plan chapitres T3-T5 (tache #61 du suivi, 02/10/2026) — P2, les versions du texte : un instantane de l'ANCIEN texte
avant chaque ecrasement, historique elague a 10, comparaison ligne a ligne, restauration qui garde le courant.
Points d'ecrasement RECOMPTES dans le code du 02/10 (le plan du 03/09 en voyait quatre, dont un a tort) :
  - PUT /chapters/{id} (script_text) .................... chapitre, « manuelle »
  - PUT /scenes/{id} (fountain_text) .................... scene, « manuelle »
  - adaptation en scenario (supprime TOUTES les scenes) .. scenario du chapitre, « adaptation »
  - DELETE /chapters/{id}/scenes ......................... scenario du chapitre, « suppression »   (absent du plan)
  - re-import du manuscrit (reecrit script_text) ......... chapitre, « import »                   (absent du plan)
  - retour du telephone (#105, reecrit script_text) ...... chapitre, « telephone »                (absent du plan)
Ecarts au plan : la decoupe en plans ne versionne PAS le texte (elle ne le touche pas) ; l'adaptation gardait chaque
scene sous son id puis SUPPRIMAIT la scene (versions orphelines, invisibles) -> un instantane du SCENARIO entier,
lisible et copiable ; la restauration respecte le verrou du telephone (423) et recalcule le surlignage ; confirm()
natif -> dialogue maison.
Banc-miroir : vraies requetes, lignes relues en base. Temoin positif : la base (a93c82a3) n'a pas text_versions.
Run (depuis backend/) : & $PY tests/test_chapitres_versions.py"""
import asyncio, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzversions_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL"):
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


BASE = "a93c82a3"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/text_versions.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas text_versions", r0.returncode != 0)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def versions(c, cid):
    return js(c.get(f"/api/chapters/{cid}/versions")).get("versions", [])


def texte(cid):
    try:
        r = sqlite3.connect(str(_DB)).execute("SELECT script_text, spans FROM chapters WHERE id=?", (cid,)).fetchone()
        return r or (None, None)
    except sqlite3.OperationalError:
        return (None, None)


print("[P] comparaison (pure)")
try:
    from app.services import text_versions as TV
    d = TV.diff("un\ndeux\ntrois", "un\nDEUX\ntrois\nquatre")
    check("P1 ligne a ligne : = ~ = + ; compte ajout/suppression/identiques", [l["op"] for l in d["lignes"]] == ["=", "~", "=", "+"]
          and d["lignes"][1] == {"op": "~", "a": "deux", "b": "DEUX"} and (d["ajoutees"], d["supprimees"], d["identiques"]) == (2, 1, 2), str(d))
    check("P2 identiques : rien d'ajoute", TV.diff("x", "x")["ajoutees"] == 0 and TV.diff("x", "x")["identiques"] == 1)
except ImportError as e:
    check("P1 ligne a ligne", False, repr(e)); check("P2 identiques", False, repr(e))

with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    loc_e = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Oriane"}))
    ch = js(c.post("/api/chapters", json={"title": "V", "script_text": "premier jet\n\nsecond para"}))
    C = ch.get("id")

    print("\n[M] edition manuelle")
    check("M1 un chapitre neuf : aucune version", versions(c, C) == [] and c.get(f"/api/chapters/{C}/versions").status_code == 200)
    c.put(f"/api/chapters/{C}", json={"script_text": "deuxieme jet\n\nsecond para"})
    c.put(f"/api/chapters/{C}", json={"title": "V2"})
    c.put(f"/api/chapters/{C}", json={"script_text": "deuxieme jet\n\nsecond para"})            # identique : rien
    vs = versions(c, C)
    check("M2 un instantane de l'ANCIEN texte ; ni le titre seul ni un texte identique ne versionnent",
          len(vs) == 1 and vs[0]["passe"] == "manuelle" and vs[0]["apercu"].startswith("premier jet") and vs[0]["kind"] == "chapter", str(vs))
    check("M3 la liste ne porte pas le texte entier (apercu + taille)", vs and "text" not in vs[0] and vs[0].get("taille") == len("premier jet\n\nsecond para"))
    lu = js(c.get(f"/api/versions/{vs[0]['id']}")) if vs else {}
    check("M4 lire une version : son texte entier", lu.get("text") == "premier jet\n\nsecond para", str(lu)[:200])
    check("M5 version inconnue : 404", c.get("/api/versions/inconnu").status_code == 404)
    for i in range(12):
        c.put(f"/api/chapters/{C}", json={"script_text": f"jet {i}"})
    vs = versions(c, C)
    check("M6 elague aux 10 plus recentes, du plus recent au plus ancien", len(vs) == 10 and vs[0]["apercu"] == "jet 10"
          and [v["n"] for v in vs] == list(range(13, 3, -1)), str([(v["n"], v["apercu"]) for v in vs]))
    n_lignes = sqlite3.connect(str(_DB)).execute("SELECT COUNT(*) FROM text_versions WHERE target_id=?", (C,)).fetchone()[0] if vs else -1
    check("M7 et elague EN BASE (pas seulement a l'affichage)", n_lignes == 10, str(n_lignes))

    async def _deux_fois():
        from app.services import text_versions as TVs
        from app.services.storage import async_session_factory
        async with async_session_factory() as s:
            a = await TVs.snapshot(s, "chapter", "cible-test", "meme texte", "manuelle")
            b = await TVs.snapshot(s, "chapter", "cible-test", "meme texte", "adaptation")
            return a, b
    a, b = asyncio.run(_deux_fois())
    check("M8 le MEME texte deux fois de suite : un seul instantane (dix passes sans effet ne chassent pas l'historique)",
          a is not None and b is None, f"{a} {b}")

    print("\n[D] decoupe : ne versionne pas (elle ne touche pas le texte)")
    avant = len(versions(c, C))
    c.post(f"/api/chapters/{C}/storyboard/decoupe", json={"method": "paragraph"})
    check("D1 aucune version de plus", len(versions(c, C)) == avant)

    print("\n[R] comparer, restaurer")
    c.put(f"/api/chapters/{C}", json={"script_text": "Oriane arrive.\n\nfin"})
    vs = versions(c, C)
    vieux = next((v for v in vs if v["apercu"] == "jet 11"), {})
    dd = js(c.get(f"/api/versions/{vieux.get('id')}/diff"))
    check("R1 la version FACE au texte courant", dd.get("lignes", [{}])[0] == {"op": "~", "a": "jet 11", "b": "Oriane arrive."}
          and dd.get("version", {}).get("id") == vieux.get("id"), str(dd)[:300])
    r = c.post(f"/api/versions/{vieux.get('id')}/restore")
    check("R2 restaurer : 200, le chapitre a ce texte EN BASE", r.status_code == 200 and texte(C)[0] == "jet 11", f"{r.status_code} {texte(C)}")
    vs = versions(c, C)
    check("R3 le texte qu'on quitte est garde (« restauration »)", vs and vs[0]["passe"] == "restauration" and vs[0]["apercu"].startswith("Oriane arrive"), str(vs[:1]))
    if vs:
        c.post(f"/api/versions/{vs[0]['id']}/restore")
    spans = json.loads(texte(C)[1] or "[]")
    check("R4 retour sur « Oriane arrive » : le surlignage des entites est RECALCULE", texte(C)[0].startswith("Oriane arrive")
          and any(s.get("entity_id") == loc_e.get("id") for s in spans), str(spans)[:200])
    check("R5 restaurer une version inconnue : 404", c.post("/api/versions/inconnu/restore").status_code == 404)

    print("\n[S] scenes et scenario")
    def scene(idx, txt):
        cx = sqlite3.connect(str(_DB))
        cx.execute("INSERT INTO scenes (id, chapter_id, idx, slugline, int_ext, time_of_day, fountain_text, created_at, updated_at) "
                   "VALUES (?,?,?,?,?,?,?,datetime('now'),datetime('now'))", (f"s{idx}", C, idx, f"INT. LIEU {idx} - JOUR", "INT", "JOUR", txt))
        cx.commit(); cx.close()
    scene(0, "ORIANE\nBonjour."); scene(1, "ORIANE\nAu revoir.")
    c.put("/api/scenes/s0", json={"fountain_text": "ORIANE\nSalut."})
    sv = js(c.get("/api/scenes/s0/versions")).get("versions", [])
    check("S1 editer une scene garde son ancien texte (scene, « manuelle »)", len(sv) == 1 and sv[0]["kind"] == "scene"
          and sv[0]["apercu"].startswith("ORIANE Bonjour"), str(sv))
    r = c.post(f"/api/versions/{sv[0]['id']}/restore") if sv else None
    fx = sqlite3.connect(str(_DB)).execute("SELECT fountain_text FROM scenes WHERE id='s0'").fetchone()
    check("S2 une scene se restaure", r is not None and r.status_code == 200 and fx[0] == "ORIANE\nBonjour.", f"{fx}")
    r = c.delete(f"/api/chapters/{C}/scenes")
    vs = versions(c, C)
    sc = [v for v in vs if v["kind"] == "scenario"]
    check("S3 supprimer le scenario : le scenario ENTIER est garde (« suppression »), visible dans les versions du chapitre",
          r.status_code == 200 and len(sc) == 1 and sc[0]["passe"] == "suppression", str([(v["kind"], v["passe"]) for v in vs]))
    check("S3b le tiroir mele texte, scenario et scenes, du PLUS RECENT au plus ancien", bool(vs) and vs[0]["kind"] == "scenario"
          and [v["created_at"] for v in vs] == sorted([v["created_at"] for v in vs], reverse=True), str([(v["kind"], v["created_at"]) for v in vs][:4]))
    plein = js(c.get(f"/api/versions/{sc[0]['id']}")) if sc else {}
    check("S4 son texte : chaque scene, slugline puis texte, dans l'ordre", plein.get("text") == "INT. LIEU 0 - JOUR\n\nORIANE\nBonjour.\n\nINT. LIEU 1 - JOUR\n\nORIANE\nAu revoir.",
          repr(plein.get("text")))
    check("S5 un scenario ne se restaure pas en scenes : 409 qui dit de copier", sc and c.post(f"/api/versions/{sc[0]['id']}/restore").status_code == 409
          and sc[0].get("restaurable") is False)
    check("S6 supprimer un scenario deja vide : aucune version", c.delete(f"/api/chapters/{C}/scenes").status_code == 200
          and len([v for v in versions(c, C) if v["kind"] == "scenario"]) == 1)

    print("\n[A] adaptation (vrai job, LLM remplace)")
    scene(0, "AVANT ADAPTATION")
    adapt_src = (_ICI.parent / "app" / "api" / "routes.py").read_text(encoding="utf-8")
    check("A1 l'adaptation garde le scenario AVANT de supprimer les scenes (« adaptation »)",
          'await TV.snapshot_scenario(session, chapter_id, "adaptation")' in adapt_src
          and adapt_src.index('await TV.snapshot_scenario(session, chapter_id, "adaptation")') < adapt_src.index("            for s in await _list_scenes(session, chapter_id):\n                await session.delete(s)\n            n_scenes = 0"))

    print("\n[I] re-import du manuscrit, retour du telephone")
    import app.services.manuscript_agent as MA
    MA.segment_chapters = lambda t: [{"title": "V2", "text": "TEXTE REIMPORTE"}]
    MA.extract_chapter = lambda titre, txt, roster: [{"kind": "character", "name": "Oriane", "aliases": [], "quotes": [], "description": "x"}]
    MA.consolidate = lambda raw, comp: raw[:1]
    c.put(f"/api/chapters/{C}", json={"series": ""})
    cx = sqlite3.connect(str(_DB)); cx.execute("UPDATE chapters SET series=? WHERE id=?", ("Saga", C)); cx.commit(); cx.close()
    avant_import = texte(C)[0]
    RT._ms_register("job-v", {"job_id": "job-v", "phase": "segmentation", "chapter_i": 0, "chapter_n": 0, "message": "",
                              "done": False, "error": None, "stats": {}, "series": "Saga"})
    asyncio.run(RT._run_manuscript_job("job-v", "x" * 300, "", "Saga"))
    vs = versions(c, C)
    check("I1 le re-import garde le texte qu'il remplace (« import »)", texte(C)[0] == "TEXTE REIMPORTE" and bool(vs) and vs[0]["passe"] == "import"
          and js(c.get(f"/api/versions/{vs[0]['id']}")).get("text") == avant_import, f"{texte(C)[0]!r} {vs[:1]}")
    H = JA.entetes(app, "192.168.1.42")
    lan = TestClient(app, client=("192.168.1.42", 50000), raise_server_exceptions=False)
    p = js(lan.post("/api/sync/chapitre/prendre", headers=H, json={"chapitre": C}))
    r = lan.post("/api/sync/chapitre/rendre", headers=H, json={"chapitre": C, "base_sha256": p.get("sha256"), "texte": "Ecrit dans le train.", "garder": True})
    vs = versions(c, C)
    check("I2 le retour du telephone garde le texte qu'il remplace (« telephone »)", r.status_code == 200 and bool(vs) and vs[0]["passe"] == "telephone"
          and js(c.get(f"/api/versions/{vs[0]['id']}")).get("text") == "TEXTE REIMPORTE", f"{r.status_code} {vs[:1]}")
    r = c.post(f"/api/versions/{vs[0]['id'] if vs else 'x'}/restore")
    check("I3 restaurer un chapitre EMPORTE par le telephone : 423, rien d'ecrit", r.status_code == 423 and texte(C)[0] == "Ecrit dans le train.",
          f"{r.status_code} {texte(C)[0]!r}")

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
_racine = _ICI.parent.parent
_js = (_racine / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
_html = (_racine / "frontend" / "atelier" / "index.html").read_text(encoding="utf-8")
_css = (_racine / "frontend" / "atelier" / "atelier.css").read_text(encoding="utf-8")
_parts = _js.split("async function renderDiff(")
_diff = _parts[1].split("\n}\n")[0] if len(_parts) > 1 else ""      # absente : le banc ECHOUE, il ne plante pas
check("U1 le bouton et le tiroir existent, avec un title", 'id="verBtn"' in _html and 'id="verModal"' in _html and 'id="verClose" class="btn ghost" title=' in _html)
check("U2 la liste, le cote a cote, la restauration", "function openVersions(" in _js and "async function renderDiff(" in _js
      and "/versions`" in _js and "/restore`" in _js)
check("U3 la restauration passe par le dialogue maison (jamais confirm natif)", "window.__dzDialogue.confirmer(" in _diff
      and "confirm(\"" not in _js and " confirm(" not in _js)
check("U4 une sauvegarde en attente n'ecrase pas le texte restaure ; le chapitre est RECHARGE (surlignage)",
      "clearTimeout(saveTimer)" in _diff and "await openChapter(chapter.id)" in _diff)
check("U5 un scenario se copie, il ne se restaure pas", "restaurable" in _js and "verCopier" in _js)
check("U6 le style existe", ".ver-mod" in _css and ".ver-add" in _css and ".ver-del" in _css)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
