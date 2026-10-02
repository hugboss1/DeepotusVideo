# -*- coding: utf-8 -*-
"""Plan chapitres T8 (tache #62 du suivi, 02/10/2026) — l'image de PRODUCTION d'un plan, generee avec les VUES de ses
entites en reference (Nano Banana), au lieu d'une seule.
  - build_banana_request prend une LISTE (ordre garde, tronquee a REF_MAX = 9 : fal ne documente aucun maximum, 9 est
    notre prudence) ; `generate` garde son parametre `background` (le plan le supprimait : 4 appelants casses) ;
  - les vues de PLUSIEURS entites sont ENTRELACEES (visage de face de chacune d'abord) : avec 9 places et deux
    personnages de 7 vues, le second n'est pas reduit a 2 vues ;
  - DECISION DE L'UTILISATEUR (02/10) : un BOUTON dans le storyboard, cout affiche et confirme ; la route est gardee
    par les PLAFONDS (402, confirmation) et recensee parmi les routes payantes ; la depense est ecrite ;
  - une nouvelle decoupe GARDE l'image payee d'un plan dont le texte n'a pas change.
Aucun appel paye : fal simule (televersements traces), data-dir isole, cles videes.
Temoin positif : la base (2ff66896) n'envoie qu'UNE reference et n'a pas la route.
Run (depuis backend/) : & $PY tests/test_chapitres_image.py"""
import io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzimage_"))
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
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "2ff66896"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/image_providers.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'envoie qu'UNE reference a Nano Banana et n'a pas la route d'image de production",
      b'"image_urls": [image_url]' in r0.stdout and b'"/shots/{shot_id}/image"' not in r1.stdout)

APPELS, TELEVERSES = [], []
from PIL import Image                                               # noqa: E402
_buf = io.BytesIO(); Image.new("RGB", (30, 40), (30, 60, 90)).save(_buf, "PNG"); PNG = _buf.getvalue()


async def _fake_subscribe(model, arguments=None, **kw):
    APPELS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": (arguments or {}).get("seed", 424242)}


async def _fake_upload(path):
    TELEVERSES.append(pathlib.Path(path).name)
    return f"http://fal.test/up/{pathlib.Path(path).name}"
_stub = types.ModuleType("fal_client"); _stub.subscribe_async = _fake_subscribe; _stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub
import httpx as _httpx                                              # noqa: E402
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG, request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)
_httpx.AsyncClient.get = _fake_get

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import image_providers as IP                      # noqa: E402
import app.api.routes as RT                                         # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def un(sql, *a):
    """Une ligne de la base, ou None (colonne absente sur la base temoin : le banc ECHOUE, il ne plante pas)."""
    try:
        return sqlite3.connect(str(_DB)).execute(sql, a).fetchone()
    except sqlite3.OperationalError:
        return None


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


print("[B] le constructeur")
m, a = IP.build_banana_request("p", "square_hd", 1, [], pro=True)
check("B1 aucune reference : generation simple (pas d'edit)", m == "fal-ai/nano-banana-pro" and "image_urls" not in a)
m, a = IP.build_banana_request("p", "square_hd", 1, [f"u{i}" for i in range(12)])
check("B2 une LISTE : edit, ordre garde, tronquee a REF_MAX = 9", m == "fal-ai/nano-banana/edit" and getattr(IP, "REF_MAX", None) == 9
      and a.get("image_urls") == [f"u{i}" for i in range(9)], str(a.get("image_urls")))
m, a = IP.build_banana_request("p", "square_hd", 1, "u1", ratio="9:16")
check("B3 une seule chaine (les appelants d'avant) : toujours acceptee, cadre force", a.get("image_urls") == ["u1"] and a.get("aspect_ratio") == "9:16")
import inspect                                                       # noqa: E402
sig = inspect.signature(IP.generate).parameters
check("B4 `generate` GARDE `background` (le plan le supprimait) et prend `image_paths`", "background" in sig and "image_paths" in sig, str(list(sig)))
entre = getattr(RT, "_refs_entrelacees", None)
if entre:
    o = entre([{"face_front": "a1", "face_left": "a2", "front": "a3", "left": "a4", "back": "a5", "face_right": "a6", "right": "a7"},
               {"face_front": "b1", "face_left": "b2", "front": "b3", "left": "b4", "back": "b5", "face_right": "b6", "right": "b7"}], 9)
    check("B5 deux personnages, 9 places : ENTRELACES, visage de face de chacun d'abord, puis le corps de face",
          o[:4] == ["a1", "b1", "a3", "b3"] and len(o) == 9 and sum(x.startswith("b") for x in o) >= 4, str(o))
    check("B6 une vue ne part jamais deux fois", entre([{"face_front": "x"}, {"face_front": "x", "front": "y"}], 9) == ["x", "y"])
else:
    check("B5 entrelacement", False, "_refs_entrelacees absent"); check("B6 sans doublon", False)

with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    def personnage(nom):
        e = js(c.post("/api/bible/entities", json={"kind": "character", "name": nom, "description": "cape bleue"}))
        c.post(f"/api/bible/entities/{e.get('id')}/generate", json={"seed": 1})
        return e
    vane, ysolde = personnage("Vane"), personnage("Ysolde")
    c.put("/api/atelier/settings", json={"image_provider": "nano-banana-pro"})
    ch = js(c.post("/api/chapters", json={"title": "C", "script_text": "Vane entre.\n\nYsolde et Vane se taisent.\n\nLa pluie."}))
    shots = js(c.post(f"/api/chapters/{ch.get('id')}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    s0, s1, s2 = shots[0], shots[1], shots[2]

    print("\n[R] la route")
    APPELS.clear(); TELEVERSES.clear()
    r = c.post(f"/api/shots/{s0['id']}/image", json={})
    j = js(r)
    check("R1 un plan avec Vane : 200, UN appel a nano-banana-pro/edit, SEPT vues en reference", r.status_code == 200 and len(APPELS) == 1
          and APPELS[0]["model"] == "fal-ai/nano-banana-pro/edit" and len(APPELS[0]["arguments"].get("image_urls", [])) == 7, f"{r.status_code} {r.text[:200]}")
    check("R2 la reponse et la base portent l'image et le NOMBRE de references", j.get("image", "").endswith(".png") and j.get("image_refs") == 7
          and un("SELECT image, image_refs FROM shots WHERE id=?", s0["id"]) == (j.get("image"), 7))
    dep = sqlite3.connect(str(_DB)).execute("SELECT moteur, categorie, estime_usd FROM depenses").fetchall()
    check("R3 la DEPENSE est ecrite (garde des plafonds) : fal, categorie chapitres, 0,15 $", ("fal", "chapitres", 0.15) in [(d[0], d[1], round(d[2], 3)) for d in dep], str(dep))
    prov = sqlite3.connect(str(_DB)).execute("SELECT source FROM library_assets WHERE filename=?", (j.get("image"),)).fetchone()
    check("R4 l'image entre dans la Bibliotheque (source atelier)", prov == ("atelier",), str(prov))
    APPELS.clear(); TELEVERSES.clear()
    r = c.post(f"/api/shots/{s1['id']}/image", json={})
    urls = APPELS[0]["arguments"].get("image_urls", []) if APPELS else []
    check("R5 deux personnages : 9 references, les DEUX visages de face d'abord", r.status_code == 200 and len(urls) == 9
          and all(u.endswith("_face_front.png") or "gen_" in u for u in urls[:2]) and TELEVERSES[:2] != [] and len(set(TELEVERSES)) == 9, str(TELEVERSES))
    e1, e2 = s1["entities"][:2] if len(s1.get("entities", [])) >= 2 else (None, None)      # l'ordre DU PLAN (Ysolde est nommee la premiere)
    v1 = js(c.get(f"/api/bible/entities/{e1}/vues")).get("par_cle", {})
    v2 = js(c.get(f"/api/bible/entities/{e2}/vues")).get("par_cle", {})
    check("R6 ... exactement, dans l'ordre du plan : visage de face de chacun, puis corps de face de chacun",
          e1 is not None and TELEVERSES[:4] == [v1.get("face_front"), v2.get("face_front"), v1.get("front"), v2.get("front")],
          f"{TELEVERSES[:4]} {[v1.get('face_front'), v2.get('face_front')]}")
    APPELS.clear()
    check("R7 un plan SANS entite : 400 (aucune vue), aucun appel", c.post(f"/api/shots/{s2['id']}/image", json={}).status_code == 400 and APPELS == [])
    check("R8 un fournisseur qui ne prend pas plusieurs references : 400, aucun appel",
          c.post(f"/api/shots/{s0['id']}/image", json={"provider": "flux"}).status_code == 400 and APPELS == [])
    check("R9 plan inconnu : 404", c.post("/api/shots/inconnu/image", json={}).status_code == 404)

    print("\n[P] plafonds")
    from app.services import plafonds as PL
    PL.enregistrer({"global_usd": 0.2, "par_moteur": {}, "alerte_pct": 80})
    APPELS.clear()
    r = c.post(f"/api/shots/{s0['id']}/image", json={})
    check("P1 au-dela du plafond mensuel : 402 dz_plafond, AUCUN appel fal", r.status_code == 402 and "dz_plafond" in r.text and APPELS == [],
          f"{r.status_code} {r.text[:160]}")
    r = c.post(f"/api/shots/{s0['id']}/image", json={}, headers={"X-DZ-Plafond": "confirme"})
    check("P2 confirme : il part", r.status_code == 200 and len(APPELS) == 1, f"{r.status_code}")
    src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("P3 recensee parmi les routes PAYANTES (le banc des plafonds la garde)", '("routes", "POST", "/shots/{shot_id}/image")' in src)
    PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})

    print("\n[D] redecoupe")
    img0 = (un("SELECT image FROM shots WHERE id=?", s0["id"]) or [None])[0]
    c.put(f"/api/chapters/{ch.get('id')}", json={"script_text": "Vane entre.\n\nUn texte neuf.\n\nLa pluie."})
    nouveaux = js(c.post(f"/api/chapters/{ch.get('id')}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    check("D1 une nouvelle decoupe GARDE l'image payee du plan dont le texte n'a pas change", bool(nouveaux) and img0 is not None and nouveaux[0].get("image") == img0
          and nouveaux[0].get("image_refs") == 7, str(nouveaux[:1])[:300])
    check("D2 ... et pas sur les autres", len(nouveaux) == 3 and nouveaux[1].get("image") is None)

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
_js = (_ICI.parent.parent / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
check("U1 le bouton existe, avec un title", 'class="btn ghost act-prod" title=' in _js)
check("U2 le cout est DIT et CONFIRME avant le tir (dialogue maison)", "async function imageProduction(" in _js
      and "window.__dzDialogue.confirmer(" in _js.split("async function imageProduction(")[1].split("\n}\n")[0]
      and "/cost/pricing" in _js.split("async function imageProduction(")[1].split("\n}\n")[0] if "async function imageProduction(" in _js else False)
_fn = _js.split("async function imageProduction(")[1].split("\n}\n")[0] if "async function imageProduction(" in _js else ""
_garde = _fn.find("if (!await window.__dzDialogue.confirmer(")
_retour = _fn.find(")) return;", _garde) if _garde >= 0 else -1
_post = _fn.find('api.send("POST"')
check("U2b la confirmation GARDE le tir : if (!await confirmer(...)) return; AVANT le POST",
      0 <= _garde < _retour < _post, f"garde={_garde} retour={_retour} post={_post}")
check("U3 il appelle la route, et l'image s'affiche sur la carte", "/image`, {})" in _js and "shot-prod" in _js)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
