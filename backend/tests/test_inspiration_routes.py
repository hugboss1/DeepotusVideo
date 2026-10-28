# -*- coding: utf-8 -*-
"""t313 (28/10/2026) (C3 Inspiration, tâche 3) — banc des routes /api/inspiration (TestClient ; faux Claude par la couture
HTTP de moteurs_texte ; OCR remplacé ; aucun réseau).
Sections :
  1. garde locale : 403 hors machine locale sur chaque route (avant toute lecture) ;
  2. capter : multipart image + source -> 200 (pour qui : espace, projet, canaux) ; texte seul ; rien -> 400 vide ;
     langue inconnue -> 400 ; format inconnu -> 415 ; image trop lourde -> 413 ; liste de l'espace de la requête ;
  3. devis d'analyse (gratuit), analyse : 409 cout (usd), 200, gardée (deja_payee), 409 en_cours, 503 sans clé,
     502 réseau, 504 délai, 404 inconnue ;
  4. carte de devis, rédaction ; 409 angle ;
  5. brouillon : 409 copie avec la garde ; 409 visuel_capte ; 200 brouillon du projet actif ;
  6. L10 : messages traduits avec Accept-Language: en (404, 400 vide, 409 copie) ;
  7. journaux sans texte capté.
Run (depuis backend/) : & $PY tests/test_inspiration_routes.py"""
import io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinsr_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
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
_JOURNAL = []
logger.add(lambda m: _JOURNAL.append(str(m)), level="DEBUG")
from PIL import Image, ImageDraw                                    # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import scan_lecture as SL                         # noqa: E402
from app.services import espaces, comptes, library_projects as LP   # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

CAPTE = ("Le matin la ville respire lentement les cafés ouvrent les vélos glissent sur les pavés mouillés et chacun "
         "cherche sa place dans la lumière grise qui annonce une journée ordinaire.")
DOUZE = "les cafés ouvrent les vélos glissent sur les pavés mouillés et chacun cherche"
SL._lire_ocr = lambda plan, langue, echeance=None: {"texte": CAPTE, "incertains": [], "stats": {}, "langue": "fr"}

APPELS = []
MODE = {"panne": None}
ANALYSE = json.dumps({"matiere": {"ton": "calme"}, "angles": [
    {"titre": "Notre atelier à l'aube", "accroche": "Avant 7 h", "idee": "préparer", "visuel": "Atelier, tons chauds"},
    {"titre": "Reprise", "accroche": DOUZE, "idee": "", "visuel": ""}]}, ensure_ascii=False)
REDAC = json.dumps({"titre": "L'aube", "accroche": "Tout se prépare.", "legende": "Nous allumons les fours.",
                    "hashtags": ["atelier"]}, ensure_ascii=False)


class _Rep:
    status_code = 200
    text = ""
    def __init__(self, t): self._t = t
    def json(self): return {"content": [{"type": "text", "text": self._t}], "usage": {"input_tokens": 1, "output_tokens": 1}}


def faux_post(url, headers=None, json=None, timeout=None, verify=None):
    import httpx
    APPELS.append(json)
    if MODE["panne"] == "delai":
        raise httpx.ReadTimeout("délai")
    if MODE["panne"] == "reseau":
        raise httpx.ConnectError("réseau")
    return _Rep(ANALYSE if "TROIS angles" in str(json.get("system")) else REDAC)


MT.httpx.post = faux_post


def png(couleur=(20, 60, 160), fmt="PNG", q=None):
    im = Image.new("RGB", (300, 200), couleur)
    ImageDraw.Draw(im).ellipse((40, 30, 200, 180), fill=(250, 250, 250))
    b = io.BytesIO()
    im.save(b, fmt, **({"quality": q} if q else {}))
    return b.getvalue()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import storage                                    # noqa: E402

with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
    EA = espaces.creer({"nom": "Atelier Soleil"})["id"]
    ca = comptes.creer({"espace_id": EA, "plateforme": "telegram", "libelle": "TG Soleil"})["id"]
    H = {"X-Dz-Espace": EA}
    r = client.post("/api/library/projets", json={"nom": "Projet Soleil"}, headers=H)
    pid = (r.json() or {}).get("id") if r.status_code == 200 else None
    if pid:
        client.put("/api/library/projets/actif", json={"id": pid}, headers=H)
        client.put(f"/api/library/projets/{pid}/canaux", json={"canaux": [ca]}, headers=H)

    print("[1] garde locale")
    for m, u in (("get", "/api/inspiration"), ("post", "/api/inspiration/capter"), ("get", "/api/inspiration/" + "a" * 32),
                 ("get", "/api/inspiration/" + "a" * 32 + "/devis-analyse"), ("post", "/api/inspiration/" + "a" * 32 + "/analyse"),
                 ("post", "/api/inspiration/" + "a" * 32 + "/devis"), ("post", "/api/inspiration/" + "a" * 32 + "/redaction"),
                 ("post", "/api/inspiration/" + "a" * 32 + "/brouillon")):
        r = getattr(dehors, m)(u)
        check(f"1 {m.upper()} {u[17:40]} hors machine -> 401 ou 403 (jamais traitée)", r.status_code in (401, 403), r.status_code)

    print("[2] capter")
    r = client.post("/api/inspiration/capter", headers=H, data={"source_libelle": "Post vu sur X", "source_lien": "https://x.example/1",
                                                                "langue": "fr"},
                    files={"image": ("cap.png", png(), "image/png")})
    check("2a 200, texte lu, source", r.status_code == 200 and r.json()["texte_capte"] == CAPTE
          and r.json()["source"]["libelle"] == "Post vu sur X", r.text[:300])
    j = r.json()
    IID = j.get("id")
    check("2b pour qui : espace de la requête, projet actif et ses canaux",
          j.get("espace", {}).get("id") == EA and (not pid or (j["projet"]["nom"] == "Projet Soleil"
                                                              and [c["id"] for c in j["projet"]["canaux"]] == [ca])), j.get("projet"))
    check("2c aucune empreinte exposée", "sha256" not in r.text and "ahash" not in r.text)
    r = client.post("/api/inspiration/capter", headers=H, data={"texte": "Un texte collé"})
    check("2d texte seul -> 200", r.status_code == 200 and r.json()["texte_capte"] == "Un texte collé", r.text[:200])
    r = client.post("/api/inspiration/capter", headers=H, data={"texte": "  "})
    check("2e rien -> 400 code vide", r.status_code == 400 and r.json()["detail"]["code"] == "vide", r.text[:200])
    r = client.post("/api/inspiration/capter", headers=H, data={"texte": "x", "langue": "de"})
    check("2f langue inconnue -> 400", r.status_code == 400, r.status_code)
    r = client.post("/api/inspiration/capter", headers=H, files={"image": ("a.txt", b"bonjour", "text/plain")})
    check("2g format inconnu -> 415", r.status_code == 415, r.status_code)
    r = client.post("/api/inspiration/capter", headers=H, files={"image": ("a.png", b"\x89PNG" + b"0" * (20 * 1024 * 1024 + 10), "image/png")})
    check("2h image trop lourde -> 413", r.status_code == 413, r.status_code)
    r = client.get("/api/inspiration", headers=H)
    check("2i liste de l'espace de la requête", r.status_code == 200 and IID in [x["id"] for x in r.json()["inspirations"]]
          and r.json()["espace"]["nom"] == "Atelier Soleil", r.text[:300])
    r = client.get("/api/inspiration")
    check("2j sans en-tête : l'espace actif (Deepotus) ne voit pas celles de A", IID not in [x["id"] for x in r.json()["inspirations"]])

    print("[3] analyse")
    r = client.get(f"/api/inspiration/{IID}/devis-analyse?image=1")
    d = r.json()
    check("3a devis gratuit", r.status_code == 200 and d["disponible"] and d["usd"] > 0 and APPELS == [], r.text[:200])
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": d["usd"] / 10, "avec_image": True})
    check("3b accord trop bas -> 409 cout + usd, aucun appel", r.status_code == 409 and r.json()["detail"]["code"] == "cout"
          and abs(r.json()["detail"]["usd"] - d["usd"]) < 1e-4 and APPELS == [], r.text[:200])
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": "abc"})
    check("3c accord illisible -> 400", r.status_code == 400, r.status_code)
    MODE["panne"] = "delai"
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": d["usd"], "avec_image": True})
    check("3d délai -> 504 (peut-être facturée)", r.status_code == 504 and "facturée" in r.json()["detail"], r.text[:200])
    MODE["panne"] = "reseau"
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": d["usd"], "avec_image": True})
    check("3e réseau -> 502", r.status_code == 502, r.status_code)
    MODE["panne"] = None
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": d["usd"], "avec_image": True})
    check("3f 200 : angles, l'angle copié en alerte", r.status_code == 200 and len(r.json()["angles"]) == 2
          and r.json()["angles"][1]["alertes"] == ["copie"], r.text[:300])
    n = len(APPELS)
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": 0})
    check("3g gardée : deja_payee, aucun appel", r.status_code == 200 and r.json().get("deja_payee") and len(APPELS) == n)
    from app.services import inspiration as I
    I._EN_COURS.add(IID)
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": 9, "nouvelle": True})
    I._EN_COURS.discard(IID)
    check("3h en cours -> 409 en_cours", r.status_code == 409 and r.json()["detail"]["code"] == "en_cours", r.text[:200])
    settings.ANTHROPIC_API_KEY = ""
    r = client.post(f"/api/inspiration/{IID}/analyse", json={"max_usd": 9, "nouvelle": True})
    settings.ANTHROPIC_API_KEY = "cle-de-banc"
    check("3i sans clé -> 503", r.status_code == 503, r.text[:200])
    r = client.get("/api/inspiration/" + "f" * 32)
    check("3j inconnue -> 404", r.status_code == 404, r.status_code)
    r = client.post("/api/inspiration/../x/analyse", json={})
    check("3k id hostile -> 404 ou 405 (jamais 200)", r.status_code in (404, 405), r.status_code)

    print("[4] carte et rédaction")
    r = client.post(f"/api/inspiration/{IID}/devis", json={"angle": 0, "image": True})
    a = r.json().get("arguments", {})
    check("4a carte : texte + image", r.status_code == 200 and a["texte"]["usd"] > 0 and a["image"]["route"] == "/api/images/generate",
          r.text[:300])
    r = client.post(f"/api/inspiration/{IID}/devis", json={"angle": 1})
    check("4b angle en alerte -> 409 angle", r.status_code == 409 and r.json()["detail"]["code"] == "angle", r.text[:200])
    r = client.post(f"/api/inspiration/{IID}/redaction", json={"angle": 0, "max_usd": a["texte"]["usd"]})
    check("4c rédaction 200 avec garde", r.status_code == 200 and r.json()["garde"]["ok"] is True, r.text[:300])

    print("[5] brouillon")
    r = client.post(f"/api/inspiration/{IID}/brouillon", json={"titre": "T", "legende": "Ce matin " + DOUZE})
    check("5a copie -> 409 code copie avec la garde", r.status_code == 409 and r.json()["detail"]["code"] == "copie"
          and r.json()["detail"]["garde"]["suite"] >= 12, r.text[:300])
    (_tmp / "images" / "gen_x.jpg").write_bytes(png(fmt="JPEG", q=50))
    r = client.post(f"/api/inspiration/{IID}/brouillon", json={"titre": "T", "legende": "Neuf.", "visuel": "gen_x.jpg"})
    check("5b capture comme visuel -> 409 visuel_capte", r.status_code == 409 and r.json()["detail"]["code"] == "visuel_capte",
          r.text[:200])
    r = client.post(f"/api/inspiration/{IID}/brouillon", json={"titre": "L'aube", "legende": "Nous allumons les fours."})
    p = r.json().get("post", {})
    check("5c 200 : brouillon dans l'espace, canaux du projet", r.status_code == 200 and p.get("espace_id") == EA
          and p.get("status") == "draft" and (not pid or p.get("comptes") == [ca]), r.text[:300])
    check("5d (le projet du banc a bien été posé par les routes du projet)", bool(pid), pid)

    print("[6] L10")
    E = {"Accept-Language": "en"}
    r = client.get("/api/inspiration/" + "f" * 32, headers=E)
    check("6a 404 traduit", r.status_code == 404 and r.json()["detail"] == "Unknown inspiration.", r.text[:200])
    r = client.post("/api/inspiration/capter", headers={**E, **H}, data={"texte": ""})
    check("6b 400 vide traduit", r.json()["detail"]["message"].startswith("Nothing to read"), r.text[:200])
    r = client.post(f"/api/inspiration/{IID}/brouillon", headers=E, json={"titre": "T", "legende": DOUZE})
    check("6c 409 copie traduit", r.json()["detail"]["message"].startswith("Too close to the capture"), r.text[:200])

    print("[7] journaux")
    jr = "\n".join(_JOURNAL)
    check("7a jamais le texte capté ni rédigé", "vélos" not in jr and "fours" not in jr)

print(f"\n{ok} PASS, {fail} FAIL")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
