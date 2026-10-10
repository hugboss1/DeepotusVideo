# -*- coding: utf-8 -*-
"""Plan chapitres T6 (tache #62 du suivi, 02/10/2026) — la DERIVE d'identite, en PIL pur, et son angle mort ;
DECISION DE L'UTILISATEUR (02/10) : branchee EN LECTURE — affichee a cote de l'image de production d'un plan, gratuite,
elle ne decide rien.
  - deux axes independants : ΔE76 entre palettes (la colorimetrie de cards/style_walkuski, pas une copie) et
    1 − Jaccard d'une occupation 16×16 relative au fond du bord ;
  - le fond est la moyenne EXACTE du bord (le plan l'arrondissait au pas de 16, vers le bas : un voile a peine visible
    sur fond sombre devenait du « sujet ») ;
  - l'angle mort — le visage — est ASSERTE, et rendu par la route.
Aucun appel paye : fal simule, data-dir isole, cles videes.
Temoin positif : la base (36859113) n'a ni le service ni la route.
Run (depuis backend/) : & $PY tests/test_chapitres_derive.py"""
import io, json, os, pathlib, shutil, sqlite3, subprocess, sys, tempfile, types
import sys as _s8, pathlib as _p8; _s8.path.insert(0, str(_p8.Path(__file__).resolve().parent)); import _labs_avant_l8  # noqa: E402,F401  (t148 : Atelier, Material Forge, Établi d'avant la traduction L8)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzderive_"))
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


BASE = "36859113"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/identity_drift.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le service de derive ni la route", r0.returncode != 0 and r1.returncode == 0
      and b'"/shots/{shot_id}/derive"' not in r1.stdout)

from PIL import Image, ImageDraw                                    # noqa: E402
try:
    from app.services import identity_drift as ID                   # noqa: E402
except ImportError as e:
    ID = None
    check("T2 le service existe", False, str(e))

FOND = (242, 239, 233)          # board_service._BG, le fond des planches


def figure(*, cape=(30, 60, 140), peau=(226, 190, 160), larg=90, yeux=(20, 20, 20), fond=FOND):
    """Un personnage schematique : cape (le costume), tete (la peau), deux yeux (les traits). Un parametre = un axe."""
    im = Image.new("RGB", (320, 480), fond)
    d = ImageDraw.Draw(im)
    d.rectangle([160 - larg, 220, 160 + larg, 440], fill=cape)
    d.ellipse([120, 90, 200, 200], fill=peau)
    d.ellipse([138, 130, 150, 142], fill=yeux)
    d.ellipse([170, 130, 182, 142], fill=yeux)
    return im


if ID:
    print("[M] la mesure")
    a = figure()
    d = ID.derive(a, a)
    check("M1 deux images identiques : 0 et 0, stable", d["ecart_couleur"] == 0.0 and d["ecart_silhouette"] == 0.0 and d["verdict"] == "stable", str(d))
    d = ID.derive(a, figure(cape=(150, 40, 40)))
    check("M2 le costume change de teinte : la COULEUR bouge (> 15), pas la silhouette (< 0,02), derive",
          d["ecart_couleur"] > 15 and d["ecart_silhouette"] < 0.02 and d["verdict"] == "derive", str(d))
    d = ID.derive(a, figure(larg=140))
    check("M3 la carrure grossit : la SILHOUETTE bouge (> 0,15), pas la couleur (< 4), derive",
          d["ecart_silhouette"] > 0.15 and d["ecart_couleur"] < 4.0 and d["verdict"] == "derive", str(d))
    d = ID.derive(a, figure(yeux=(210, 40, 40)))
    check("M4 L'ANGLE MORT : d'autres yeux, meme costume et carrure -> ~0, stable ; et la limite est DITE",
          d["ecart_couleur"] < 2.0 and d["ecart_silhouette"] < 0.02 and d["verdict"] == "stable"
          and "visage" in ID.CE_QUE_CA_NE_MESURE_PAS.lower() and d.get("angle_mort") == ID.CE_QUE_CA_NE_MESURE_PAS, str(d))
    p = ID.palette(a)
    check("M5 la palette : 2 a 8 couleurs, ordonnee par poids, somme 1, le fond domine",
          2 <= len(p) <= 8 and p == sorted(p, reverse=True) and abs(sum(w for w, _ in p) - 1.0) < 1e-6 and p[0][0] > 0.4, str(p[:3]))
    occ = ID.occupation(a)
    check("M6 l'occupation : 256 cases, la figure en occupe une part plausible (20-50 %)", len(occ) == 256 and 50 < sum(occ) < 130, str(sum(occ)))
    check("M7 deux images sans sujet : silhouette 0 (on ne crie pas au loup)",
          ID.ecart_silhouette([False] * 256, [False] * 256) == 0.0 and ID.ecart_couleur([], [(1.0, (0, 0, 0))]) == 100.0)
    pv, pf = ID.palette(Image.new("RGB", (320, 480), FOND)), ID.palette(a)
    check("M8 l'appariement va dans les DEUX sens : symetrique, et une image VIDE ne passe pas pour proche de la figure",
          ID.ecart_couleur(pv, pf) == ID.ecart_couleur(pf, pv) > 8, f"{ID.ecart_couleur(pv, pf)} {ID.ecart_couleur(pf, pv)}")
    pts = Image.new("RGB", (64, 64), FOND)
    for y in range(1, 64, 4):
        for x in range(1, 64, 4):
            pts.putpixel((x, y), (20, 20, 20))
    check("M9 une case n'est du sujet qu'a la MAJORITE : un pixel sur seize ne suffit pas", sum(ID.occupation(pts)) == 0, str(sum(ID.occupation(pts))))

    print("\n[F] le fond EXACT (le plan l'arrondissait au pas de 16)")
    voile = Image.new("RGB", (320, 480), (31, 31, 31))
    ImageDraw.Draw(voile).rectangle([60, 60, 260, 420], fill=(44, 44, 44))
    check("F1 le fond sombre est retrouve EXACTEMENT ((31,31,31), pas (16,16,16))", ID._fond(voile) == (31, 31, 31), str(ID._fond(voile)))
    check("F2 un voile a 6 ΔE du fond n'est PAS du sujet (contre l'arrondi : 13 ΔE, il le devenait)",
          sum(ID.occupation(voile)) == 0, str(sum(ID.occupation(voile))))
    from app.services.cards import style_walkuski as SW
    check("F3 la colorimetrie est celle de style_walkuski (une seule copie de sRGB -> L*a*b*)", ID.lab is SW.rgb_vers_lab)

# ── la route, en lecture ──────────────────────────────────────────────────────────────────────────────────────────
APPELS = []
_buf = io.BytesIO(); Image.new("RGB", (30, 40), (30, 60, 90)).save(_buf, "PNG"); PNG = _buf.getvalue()


async def _fake_subscribe(model, arguments=None, **kw):
    APPELS.append(model)
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": (arguments or {}).get("seed", 424242)}


async def _fake_upload(path):
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


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def depenses():
    try:
        return sqlite3.connect(str(_DB)).execute("SELECT count(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return -1


IMG = _tmp / "images"
print("\n[R] la route GET /shots/{id}/derive")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    e = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Vane", "description": "cape bleue"}))
    c.post(f"/api/bible/entities/{e.get('id')}/generate", json={"seed": 1})
    c.put("/api/atelier/settings", json={"image_provider": "nano-banana-pro"})
    ch = js(c.post("/api/chapters", json={"title": "C", "script_text": "Vane entre.\n\nLa pluie."}))
    shots = js(c.post(f"/api/chapters/{ch.get('id')}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [{}, {}])
    s0, s1 = shots[0], shots[1]
    check("R1 un plan SANS image de production : 400", c.get(f"/api/shots/{s0.get('id')}/derive").status_code == 400)
    check("R2 plan inconnu : 404", c.get("/api/shots/inconnu/derive").status_code == 404)
    prod = js(c.post(f"/api/shots/{s0.get('id')}/image", json={})).get("image")
    vues = js(c.get(f"/api/bible/entities/{e.get('id')}/vues")).get("par_cle", {})
    front = vues.get("front")
    figure().save(IMG / front) if front else None
    shutil.copy(IMG / front, IMG / prod) if front and prod else None
    n_appels, n_dep = len(APPELS), depenses()
    r = c.get(f"/api/shots/{s0.get('id')}/derive")
    j = js(r)
    l0 = (j.get("entites") or [{}])[0]
    check("R3 l'image de production identique a la vue de face : 200, comparee a « front », 0 / 0, stable",
          r.status_code == 200 and l0.get("vue") == "front" and l0.get("fichier") == front and l0.get("ecart_couleur") == 0.0
          and l0.get("ecart_silhouette") == 0.0 and l0.get("verdict") == "stable", f"{r.status_code} {r.text[:240]}")
    check("R4 la reponse DIT l'angle mort et les seuils", "visage" in str(j.get("angle_mort", "")) and j.get("seuils") == {"couleur": 8.0, "silhouette": 0.12})
    figure(cape=(150, 40, 40), larg=140).save(IMG / prod)
    l0 = (js(c.get(f"/api/shots/{s0.get('id')}/derive")).get("entites") or [{}])[0]
    check("R5 une cape rouge et plus large : derive, sur les DEUX axes",
          l0.get("verdict") == "derive" and l0.get("ecart_couleur", 0) > 8 and l0.get("ecart_silhouette", 0) > 0.12, str(l0))
    check("R6 EN LECTURE : aucun appel fal, aucune depense, la base du plan intacte",
          len(APPELS) == n_appels and depenses() == n_dep >= 0
          and js(c.get(f"/api/chapters/{ch.get('id')}/shots")).get("shots", [{}])[0].get("image") == prod, f"{len(APPELS)}/{n_appels} {depenses()}/{n_dep}")
    y = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Ysolde", "description": "robe"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET ref_image='absente.png', prompt_recipe=NULL WHERE id=?", (y.get("id"),)).connection.commit()
    sqlite3.connect(str(_DB)).execute("UPDATE shots SET entities=? WHERE id=?", (json.dumps([e.get("id"), y.get("id")]), s0.get("id"))).connection.commit()
    r = c.get(f"/api/shots/{s0.get('id')}/derive")
    ls = js(r).get("entites") or [{}, {}]
    check("R8 une entite dont la planche a DISPARU du disque : 200, « aucune vue », l'autre entite toujours mesuree",
          r.status_code == 200 and len(ls) == 2 and ls[1].get("vue") is None and ls[0].get("verdict") == "derive", f"{r.status_code} {r.text[:240]}")
    sqlite3.connect(str(_DB)).execute("UPDATE shots SET entities=? WHERE id=?", (json.dumps([e.get("id")]), s0.get("id"))).connection.commit()
    (IMG / front).unlink()
    l0 = (js(c.get(f"/api/shots/{s0.get('id')}/derive")).get("entites") or [{}])[0]
    check("R7 la vue de face disparue : une AUTRE vue la remplace (ordre de _ORDRE_VUES), jamais un plantage",
          l0.get("vue") not in (None, "front") and l0.get("verdict") in ("stable", "derive"), str(l0))

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
_js = (_ICI.parent.parent / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
_fn = _js.split("async function deriveProduction(")[1].split("\n}\n")[0] if "async function deriveProduction(" in _js else ""
check("U1 le bouton 📏 existe, avec un title, et il est cable", 'class="btn ghost act-derive" title=' in _js
      and '.act-derive")?.addEventListener("click", () => deriveProduction(id, card))' in _js)
check("U2 il LIT la route (GET, rien d'autre)", "api.get(`/shots/${encodeURIComponent(id)}/derive`)" in _fn and "api.send(" not in _fn)
check("U3 l'angle mort est AFFICHE avec le chiffre", "d.angle_mort" in _fn and "Angle mort" in _fn)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
