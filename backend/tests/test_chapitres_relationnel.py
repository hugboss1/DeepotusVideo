# -*- coding: utf-8 -*-
"""Plan chapitres T1 + T2 (tache #60 du suivi, 02/10/2026) — P1, la bible relationnelle :
  - le decoupage PAR PARAGRAPHE (le seul sans cle LLM) lie les entites presentes a chaque plan — nom ET alias, sans
    casse ni accents, par MA.compute_spans (le moteur du surlignage). Avant : `entities: []`, toujours ;
  - GET /api/bible/entities/{id}/apparitions : ou l'entite apparait, chapitre par chapitre (mentions, plans, scenes),
    dans l'ordre de lecture, lu en base, sans LLM ;
  - PUT /api/shots/{id} n'accepte que des ids d'entites EXISTANTES, sans doublon (ecart au plan du 03/09 : il
    stockait n'importe quoi) ;
  - /atelier : cases a cocher par plan, bouton « Apparitions » sur la fiche (cablage lu dans la source ; le
    comportement est prouve dans le navigateur, sur 8799).
Banc-miroir : vraies requetes, lignes relues en base. Temoin positif : la base (0812e27e) laisse `entities` vide.
Run (depuis backend/) : & $PY tests/test_chapitres_relationnel.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrelation_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "0812e27e"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base laisse les entites du decoupage par paragraphe VIDES et n'a pas la route apparitions",
      r0.returncode == 0 and b'"entities": [],\n' in r0.stdout.replace(b"\r\n", b"\n") and b"/apparitions" not in r0.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def js(r):
    try:
        return r.json()
    except Exception:
        return {}


SCRIPT = ("Elias Vane s'éveille avant l'alarme.\n\n"
          "VANE serre la cle de nacre. Le Prophete l'observe, et Vane se tait.\n\n"
          "Dehors, Londres disparait sous la pluie.")

with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    elias = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Elias Vane"}))
    c.put(f"/api/bible/entities/{elias.get('id')}", json={"aliases": ["Vane"]})
    cle = js(c.post("/api/bible/entities", json={"kind": "object", "name": "Clé de Nacre"}))
    londres = js(c.post("/api/bible/entities", json={"kind": "place", "name": "Londres"}))
    ch = js(c.post("/api/chapters", json={"title": "Ch1", "script_text": SCRIPT,
                                          "spans": [{"start": 0, "end": 10, "text": "Elias Vane", "entity_id": elias.get("id")}]}))
    ch2 = js(c.post("/api/chapters", json={"title": "Ch2", "script_text": "Rien ici."}))

    print("\n[D] decoupage par paragraphe")
    r = c.post(f"/api/chapters/{ch.get('id')}/storyboard/decoupe", json={"method": "paragraph"})
    shots = js(r).get("shots", []) if r.status_code == 200 else []
    check("D1 trois plans", r.status_code == 200 and len(shots) == 3, f"{r.status_code} {r.text[:200]}")
    E, K, L = elias.get("id"), cle.get("id"), londres.get("id")
    check("D2 plan 1 : le NOM lie l'entite", len(shots) == 3 and shots[0]["entities"] == [E], str(shots[:1]))
    check("D3 plan 2 : l'ALIAS (en capitales, deux fois) et l'objet SANS ACCENTS sont lies, chacun UNE fois",
          len(shots) == 3 and set(shots[1]["entities"]) == {E, K} and len(shots[1]["entities"]) == 2,
          str(shots[1:2]))
    check("D4 plan 3 : le lieu", len(shots) == 3 and shots[2]["entities"] == [L], str(shots[2:3]))
    en_base = {row[0]: json.loads(row[1]) for row in sqlite3.connect(str(_DB)).execute("SELECT idx, entities FROM shots")}
    check("D5 ecrit EN BASE (shots.entities)", en_base.get(0) == [E] and set(en_base.get(1, [])) == {E, K}, str(en_base))
    r = c.post(f"/api/chapters/{ch2.get('id')}/storyboard/decoupe", json={"method": "paragraph"})
    check("D6 un chapitre sans entite : des plans sans entite (pas d'erreur)", r.status_code == 200 and js(r)["shots"][0]["entities"] == [])

    print("\n[A] apparitions")
    r = c.get(f"/api/bible/entities/{E}/apparitions")
    a = js(r)
    check("A1 totaux : 1 chapitre, 1 mention (span), 2 plans, 0 scene", r.status_code == 200
          and a.get("totals") == {"chapters": 1, "mentions": 1, "shots": 2, "scenes": 0}, str(a.get("totals")))
    c0 = (a.get("chapters") or [{}])[0]
    check("A2 le chapitre, ses plans dans l'ordre, leur action", c0.get("title") == "Ch1" and [s["idx"] for s in c0.get("shots", [])] == [0, 1]
          and c0["shots"][0]["action"].startswith("Elias"), str(c0)[:300])
    check("A3 la fiche dit son nom et son genre", a.get("name") == "Elias Vane" and a.get("kind") == "character")
    check("A4 entite inconnue : 404", c.get("/api/bible/entities/inconnu/apparitions").status_code == 404)
    a_l = js(c.get(f"/api/bible/entities/{L}/apparitions"))
    check("A5 Londres : un plan, aucune mention (aucun span), le chapitre sans entite n'y figure pas",
          a_l.get("totals") == {"chapters": 1, "mentions": 0, "shots": 1, "scenes": 0}, str(a_l.get("totals")))

    print("\n[E] edition a la main")
    r = c.put(f"/api/shots/{shots[2]['id']}", json={"entities": [E, L, E, "inconnu", 12]})
    check("E1 PUT : ids EXISTANTS seulement, sans doublon, ordre garde", r.status_code == 200 and js(r).get("entities") == [E, L], r.text[:200])
    a = js(c.get(f"/api/bible/entities/{E}/apparitions"))
    check("E2 la fiche le voit : 3 plans", a.get("totals", {}).get("shots") == 3)
    check("E3 entities qui n'est pas une liste : 400", c.put(f"/api/shots/{shots[2]['id']}", json={"entities": "Elias"}).status_code == 400)
    check("E4 liste vide : le plan n'a plus d'entite", js(c.put(f"/api/shots/{shots[2]['id']}", json={"entities": []})).get("entities") == [])

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
_js = (_ICI.parent.parent / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
_css = (_ICI.parent.parent / "frontend" / "atelier" / "atelier.css").read_text(encoding="utf-8")
check("U1 la fiche appelle la route apparitions, une fois", _js.count("/apparitions`") == 1 and "function showApparitions(" in _js)
check("U2 le plan a son selecteur d'entites, qui ecrit par PUT /shots", "function entPicker(" in _js and "shot-ents-edit" in _js
      and '{ entities: ids }' in _js)
check("U3 le bouton « Apparitions » de la fiche a un title (E-12)", 'class="btn ghost act-apps" title=' in _js)
check("U4 les attributs echappent les guillemets (une action contenant \" ne casse pas le title)", "function escA(" in _js
      and 'title="${escA(s.action)}"' in _js)
check("U6 le bouton « Apparitions » est BRANCHE", '.act-apps").addEventListener("click", () => showApparitions(id, card))' in _js)
check("U5 le style existe", ".entity-apps" in _css and ".shot-ents-edit" in _css)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
