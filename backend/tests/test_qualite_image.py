"""t478 (F6.1, lot « Fiches modèle ») — palier de qualité de GPT Image et d'Ideogram 4.5.

Le palier était figé à `high`. Il se choisit désormais par modèle (corps `qualite`, ou réglage d'Atelier
`image_qualite:<id>` posé par la pastille), il part chez le fournisseur, le devis et la garde de dépense le
chiffrent, la recette le garde. Sans choix, rien ne change (payload et ligne de devis identiques à avant).

Run: <python embarqué> backend/tests/test_qualite_image.py
"""
import asyncio
import base64
import io
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["FAL_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-oa"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")

FAL_CALLS, OPENAI_CALLS = [], []


async def _fake_subscribe(model, arguments=None, **kw):
    FAL_CALLS.append({"model": model, "arguments": dict(arguments or {})})
    return {"images": [{"url": "http://fal.test/img.png"}]}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from PIL import Image as _PILImage                        # noqa: E402
import httpx as _httpx                                    # noqa: E402
from httpx import AsyncClient, ASGITransport              # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (8, 8), (10, 20, 30)).save(_buf, "PNG")
_PNG = _buf.getvalue()


class _FakeResp:
    status_code = 200
    content = _PNG
    text = ""

    def json(self):
        return {"data": [{"b64_json": base64.b64encode(_PNG).decode()}]}

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None, data=None, **kw):
        OPENAI_CALLS.append({"url": url, "json": json if json is not None else data})
        return _FakeResp()

    async def get(self, url, **kw):
        return _FakeResp()

_httpx.AsyncClient = _FakeAsyncClient

from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.api import routes as R                           # noqa: E402
from app.services import pricing as P, image_providers as IP, catalogue_ia as CI  # noqa: E402

PLAFONDS = []
_plafond0 = R._plafond


async def _espion_plafond(op, *a, **kw):
    PLAFONDS.append(dict(op))
    return await _plafond0(op, *a, **kw)

R._plafond = _espion_plafond

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


# Tables fal relevées le 09/11/2026 (low, medium, high[, xhigh, max]) par taille servie : le facteur × le prix
# `high` de la même taille doit couvrir chaque palier (la garde ne passe jamais sous la facture).
TABLE_GPT2 = [(0.005, 0.037, 0.145), (0.006, 0.053, 0.211), (0.005, 0.042, 0.165), (0.005, 0.040, 0.158)]
TABLE_GPT25 = [(0.00402, 0.00903, 0.03612, 0.06420, 0.14445), (0.00588, 0.01317, 0.05268, 0.09366, 0.21072),
               (0.00474, 0.01029, 0.04116, 0.07377, 0.16464), (0.00441, 0.00951, 0.03945, 0.07014, 0.15780)]
IDEOGRAM = {"low": 0.03, "medium": 0.06, "high": 0.22}


def bloc_registre():
    print("\n[1] registre des paliers (pricing)")
    check("1.1 FLUX, Nano Banana, Qwen : pas de palier (None)",
          all(P.qualite_image(m, "low") is None for m in ("flux", "nano-banana-2.1", "qwen-image-3", "seedream-5-pro")))
    check("1.2 sans choix : high", P.qualite_image("gpt-image-2-fal") == "high" and P.qualite_image("ideogram-4.5", "") == "high")
    check("1.3 palier permis servi tel quel (casse ignorée)", P.qualite_image("ideogram-4.5", " LOW ") == "low")
    check("1.4 palier inconnu -> high, jamais d'erreur", P.qualite_image("gpt-image-2-fal", "ultra") == "high")
    check("1.5 xhigh et max chez fal pour 2.5", P.qualite_image("gpt-image-2.5-flare-fal", "max") == "max"
          and P.qualite_image("gpt-image-2.5-sunburst-fal", "xhigh") == "xhigh")
    check("1.6 xhigh refusé sur la voie OpenAI directe (non relevé) -> high",
          P.qualite_image("gpt-image-2.5-flare", "xhigh") == "high")
    check("1.7 gpt-image-2 n'a pas xhigh", P.qualite_image("gpt-image-2", "xhigh") == "high")
    check("1.8 le facteur de high vaut 1 partout", all(t["high"] == 1.0 for t in P.IMAGE_QUALITES.values()))
    check("1.9 chaque id à paliers existe au registre des prix", all(m in P._IMAGE_MODELS for m in P.IMAGE_QUALITES))
    f2, f25 = P.IMAGE_QUALITES["gpt-image-2-fal"], P.IMAGE_QUALITES["gpt-image-2.5-flare-fal"]
    couv2 = all(f2[q] * row[2] >= row[i] - 1e-9 for row in TABLE_GPT2 for i, q in enumerate(("low", "medium", "high")))
    couv25 = all(f25[q] * row[2] >= row[i] - 1e-9 for row in TABLE_GPT25
                 for i, q in enumerate(("low", "medium", "high", "xhigh", "max")))
    check("1.10 GPT Image 2 : facteur × high couvre chaque taille relevée", couv2)
    check("1.11 GPT Image 2.5 : facteur × high couvre chaque taille relevée", couv25)
    base = P.DEFAULTS["ideogram45_usd"]
    check("1.12 Ideogram : facteur × 0,22 $ couvre le prix publié de chaque palier",
          all(P.IMAGE_QUALITES["ideogram-4.5"][q] * base >= v - 1e-9 for q, v in IDEOGRAM.items()), base)
    check("1.13 les paliers sont croissants en prix",
          all(list(t.values()) == sorted(t.values()) for t in P.IMAGE_QUALITES.values()))


def bloc_devis():
    print("\n[2] devis")
    sans = P.estimate({"kind": "image", "n": 2, "model": "ideogram-4.5"})
    haut = P.estimate({"kind": "image", "n": 2, "model": "ideogram-4.5", "qualite": "high"})
    bas = P.estimate({"kind": "image", "n": 2, "model": "ideogram-4.5", "qualite": "low"})
    check("2.1 sans palier = high, ligne identique", sans == haut, (sans, haut))
    check("2.2 libellé inchangé sans palier ni high", "·" not in str(sans["breakdown"][0].get("label", sans["breakdown"][0])))
    check("2.3 low : prix × facteur", abs(bas["total_usd"] - 2 * 0.22 * 0.137) < 1e-3 and bas["total_usd"] < sans["total_usd"] / 3, bas["total_usd"])
    check("2.4 low nommé dans la ligne", "low" in str(bas["breakdown"][0]))
    m = P.estimate({"kind": "image", "n": 1, "model": "gpt-image-2.5-sunburst-fal", "qualite": "max"})
    check("2.5 max = 4 × high", abs(m["total_usd"] - 4 * P.DEFAULTS["gpt_image_25_sunburst_fal_usd"]) < 1e-6)
    fl = P.estimate({"kind": "image", "n": 1, "model": "flux", "qualite": "low"})
    check("2.6 un palier sur FLUX ne change rien", fl == P.estimate({"kind": "image", "n": 1, "model": "flux"}))


def bloc_builders():
    print("\n[3] requêtes (pures)")
    _, a = IP.build_fal_gpt_request("p", "square_hd", 1, None, model="gpt-image-2")
    check("3.1 GPT via fal : high par défaut (inchangé)", a["quality"] == "high")
    _, a = IP.build_fal_gpt_request("p", "square_hd", 1, "http://x", model="gpt-image-2.5-flare", qualite="low")
    check("3.2 GPT 2.5 via fal : le palier part (edit compris)", a["quality"] == "low" and a["image_urls"])
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", [], 1, qualite="medium")
    check("3.3 Ideogram : quality=medium", a["quality"] == "medium")
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", [], 1)
    check("3.4 Ideogram sans palier : high (inchangé)", a["quality"] == "high")
    _, a = IP.build_fal_image_request("qwen-image-3", "p", "square_hd", [], 1, qualite="low")
    check("3.5 Qwen : aucun champ quality ajouté", "quality" not in a)
    _, a = IP.build_openai_request("gpt-image-2", "p", "portrait_4_3", 1, False)
    check("3.6 gpt-image-2 direct sans choix : aucun quality (défaut OpenAI, inchangé)", "quality" not in a)
    _, a = IP.build_openai_request("gpt-image-2", "p", "portrait_4_3", 1, False, qualite="low")
    check("3.7 gpt-image-2 direct avec choix : quality=low", a.get("quality") == "low")
    _, a = IP.build_openai_request("gpt-image-2.5-flare", "p", "portrait_4_3", 1, False, qualite="medium")
    check("3.8 GPT 2.5 direct : quality=medium", a["quality"] == "medium")
    _, a = IP.build_openai_request("gpt-image-2.5-flare", "p", "portrait_4_3", 1, False)
    check("3.9 GPT 2.5 direct sans choix : high (inchangé)", a["quality"] == "high")


def bloc_catalogue():
    print("\n[4] catalogue")
    par = {e["id"]: e for e in CI.lister("image")}
    q = par["ideogram-4.5"].get("qualites") or {}
    check("4.1 Ideogram : trois paliers chiffrés", list(q) == ["low", "medium", "high"] and abs(q["high"] - 0.22) < 1e-9, q)
    check("4.2 GPT 2.5 fal : cinq paliers", len(par["gpt-image-2.5-flare-fal"].get("qualites") or {}) == 5)
    check("4.3 défaut annoncé : high", par["gpt-image-2-fal"].get("qualite_defaut") == "high")
    check("4.4 FLUX : aucun palier", "qualites" not in par["flux"])


async def bloc_route():
    print("\n[5] route /images/generate (fal et OpenAI simulés)")
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        FAL_CALLS.clear(); PLAFONDS.clear()
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5"})
        check("5.1 sans choix : quality=high envoyé", r.status_code == 200 and FAL_CALLS[-1]["arguments"]["quality"] == "high",
              r.text[:200])
        check("5.2 la garde reçoit qualite=None (high)", PLAFONDS[-1].get("qualite") is None, PLAFONDS[-1:])
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5", "qualite": "low"})
        check("5.3 corps qualite=low : envoyé low", FAL_CALLS[-1]["arguments"]["quality"] == "low")
        check("5.4 la garde chiffre low", PLAFONDS[-1].get("qualite") == "low")
        check("5.5 la réponse dit le palier servi", r.json().get("qualite") == "low", r.json())
        r = await c.put("/api/atelier/settings", json={"image_qualite:gpt-image-2.5-flare-fal": "xhigh"})
        check("5.6 réglage enregistré", r.status_code == 200)
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "gpt-image-2.5-flare-fal"})
        check("5.7 réglage suivi sans corps : xhigh envoyé", FAL_CALLS[-1]["arguments"]["quality"] == "xhigh",
              FAL_CALLS[-1:])
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "gpt-image-2.5-flare-fal",
                                                      "qualite": "low"})
        check("5.8 le corps prime sur le réglage", FAL_CALLS[-1]["arguments"]["quality"] == "low")
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "gpt-image-2-fal", "qualite": "max"})
        check("5.9 palier non permis -> high envoyé", FAL_CALLS[-1]["arguments"]["quality"] == "high")
        OPENAI_CALLS.clear()
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "gpt-image-2"})
        check("5.10 gpt-image-2 direct sans choix : pas de quality", r.status_code == 200
              and "quality" not in (OPENAI_CALLS[-1]["json"] or {}), OPENAI_CALLS[-1:])
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "gpt-image-2", "qualite": "medium"})
        check("5.11 gpt-image-2 direct avec choix : quality=medium", (OPENAI_CALLS[-1]["json"] or {}).get("quality") == "medium")
        n = len(FAL_CALLS)
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "qwen-image-3", "qualite": "low"})
        check("5.12 Qwen : aucun quality malgré le corps", len(FAL_CALLS) == n + 1 and "quality" not in FAL_CALLS[-1]["arguments"])
        r = await c.get("/api/image-models")
        check("5.13 /image-models rend le palier enregistré", r.json().get("qualites", {}).get("gpt-image-2.5-flare-fal") == "xhigh",
              r.json().get("qualites"))
        await c.put("/api/atelier/settings", json={"image_qualite:ideogram-4.5": "n'importe"})
        r = await c.get("/api/image-models")
        check("5.14 un réglage illisible n'est pas rendu", "ideogram-4.5" not in r.json().get("qualites", {}))
    # la façade appelée sans la route (Atelier DA, Cardforge, lots d'art)
    OPENAI_CALLS.clear()
    await IP.generate("gpt-image-2", "o", "portrait_4_3", 1)
    check("5.17 façade gpt-image-2 sans choix : pas de quality (défaut OpenAI, inchangé)",
          "quality" not in (OPENAI_CALLS[-1]["json"] or {}), OPENAI_CALLS[-1:])
    await IP.generate("gpt-image-2", "o", "portrait_4_3", 1, qualite="low")
    check("5.18 façade gpt-image-2 avec choix : quality=low", (OPENAI_CALLS[-1]["json"] or {}).get("quality") == "low")
    await IP.generate("gpt-image-2.5-sunburst", "o", "portrait_4_3", 1)
    check("5.19 façade GPT 2.5 direct sans choix : high", (OPENAI_CALLS[-1]["json"] or {}).get("quality") == "high")
    check("5.15 la recette garde le palier servi",
          R._recette_generation({"prompt": "o"}, {"images": ["a"], "qualite": "low"}).get("qualite") == "low")
    check("5.16 recette sans palier : pas de clé", "qualite" not in R._recette_generation({"prompt": "o"}, {"images": ["a"]}))


def bloc_ecran():
    print("\n[6] pastille (statique)")
    src = (ROOT / "frontend/shared/dz-champ-ia.js").read_bytes()
    dist = (ROOT / "frontend/dist/shared/dz-champ-ia.js").read_bytes()
    t = src.decode("utf-8")
    check("6.1 dist == shared (octet pour octet)", src == dist)
    check("6.2 rangée de paliers seulement pour la liste image", 'm.liste === "image" ? modeleDe("image", cour)' in t)
    check("6.3 le choix s'enregistre par modèle (image_qualite:<id>, PUT /api/atelier/settings)",
          '"image_qualite:" + cour' in t and 'method: "PUT"' in t and '"/api/atelier/settings"' in t)
    check("6.4 chaque palier a un titre avec son prix", 'prixUsd(mq.qualites[q], "image")' in t)
    check("6.5 bouton aria-pressed", "aria-pressed" in t)
    check("6.6 angles de la charte", re.search(r"\.dzia-qbtn\{[^}]*border-radius:var\(--r\)", t) is not None)
    dico = (ROOT / "frontend/shared/i18n/commun.json").read_text(encoding="utf-8")
    check("6.7 clés i18n des paliers (FR et EN)", all(f'"ia.qualite.{q}"' in dico for q in
                                                        ("titre", "low", "medium", "high", "xhigh", "max")))
    try:
        r = subprocess.run(["node", "--check", str(ROOT / "frontend/shared/dz-champ-ia.js")], capture_output=True, timeout=60)
        check("6.8 node --check", r.returncode == 0, r.stderr[:200])
    except FileNotFoundError:
        check("6.8 node --check (node absent)", True)


async def bloc_reecriture():
    """t479 (F6.2) : réécriture du prompt d'Ideogram (`enable_prompt_expansion`, texte → image seulement)."""
    print("\n[7] réécriture du prompt (Ideogram « magic prompt »)")
    check("7.1 Ideogram a l'interrupteur ; Qwen et GPT non",
          IP.accepte_reecriture("ideogram-4.5") and not IP.accepte_reecriture("qwen-image-3")
          and not IP.accepte_reecriture("gpt-image-2-fal"))
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", [], 1)
    check("7.2 sans choix : aucun champ (défaut fal, inchangé)", "enable_prompt_expansion" not in a)
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", [], 1, reecriture=False)
    check("7.3 coupée : enable_prompt_expansion=false", a.get("enable_prompt_expansion") is False)
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", [], 1, reecriture=True)
    check("7.4 active : enable_prompt_expansion=true", a.get("enable_prompt_expansion") is True)
    _, a = IP.build_fal_image_request("ideogram-4.5", "p", "square_hd", ["http://x"], 1, reecriture=False)
    check("7.5 retouche : le champ n'est jamais envoyé (absent du schéma edit)", "enable_prompt_expansion" not in a)
    _, a = IP.build_fal_image_request("qwen-image-3", "p", "square_hd", [], 1, reecriture=False)
    check("7.6 Qwen : rien d'ajouté", "enable_prompt_expansion" not in a)
    par = {e["id"]: e for e in CI.lister("image")}
    check("7.7 catalogue : reecriture sur Ideogram seulement",
          par["ideogram-4.5"].get("reecriture") is True and "reecriture" not in par["qwen-image-3"])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5"})
        check("7.8 route sans choix : aucun champ", "enable_prompt_expansion" not in FAL_CALLS[-1]["arguments"]
              and "reecriture" not in r.json(), FAL_CALLS[-1:])
        r = await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5", "reecriture": False})
        check("7.9 corps reecriture=false : envoyé false, rendu", FAL_CALLS[-1]["arguments"].get("enable_prompt_expansion") is False
              and r.json().get("reecriture") is False)
        await c.put("/api/atelier/settings", json={"image_reecriture:ideogram-4.5": "0"})
        await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5"})
        check("7.10 réglage « 0 » suivi sans corps", FAL_CALLS[-1]["arguments"].get("enable_prompt_expansion") is False)
        await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5", "reecriture": True})
        check("7.11 le corps prime sur le réglage", FAL_CALLS[-1]["arguments"].get("enable_prompt_expansion") is True)
        await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5", "reecriture": "non"})
        check("7.12 corps non booléen ignoré -> réglage", FAL_CALLS[-1]["arguments"].get("enable_prompt_expansion") is False)
        r = await c.get("/api/image-models")
        check("7.13 /image-models rend la réécriture enregistrée", r.json().get("reecritures") == {"ideogram-4.5": False},
              r.json().get("reecritures"))
        await c.put("/api/atelier/settings", json={"image_reecriture:ideogram-4.5": "peut-être"})
        await c.post("/api/images/generate", json={"prompt": "o", "model": "ideogram-4.5"})
        check("7.14 réglage illisible : défaut fal (aucun champ)", "enable_prompt_expansion" not in FAL_CALLS[-1]["arguments"])
        r = await c.get("/api/image-models")
        check("7.15 réglage illisible non rendu", r.json().get("reecritures") == {})
        n = len(FAL_CALLS)
        await c.post("/api/images/generate", json={"prompt": "o", "model": "qwen-image-3", "reecriture": False})
        check("7.16 Qwen avec corps : rien envoyé", len(FAL_CALLS) == n + 1 and "enable_prompt_expansion" not in FAL_CALLS[-1]["arguments"])
    check("7.17 recette : la réécriture choisie est gardée",
          R._recette_generation({"prompt": "o"}, {"images": ["a"], "reecriture": False}).get("reecriture") is False)
    t = (ROOT / "frontend/shared/dz-champ-ia.js").read_text(encoding="utf-8")
    check("7.18 pastille : interrupteur enregistré par modèle (« 0 » / « 1 »)",
          '"image_reecriture:" + cour' in t and 'nv ? "1" : "0"' in t and "mq && mq.reecriture" in t)
    check("7.19 pastille : absent du réglage = actif", "(d.reecritures || {})[e.id] !== false" in t)
    dico = (ROOT / "frontend/shared/i18n/commun.json").read_text(encoding="utf-8")
    check("7.20 clés i18n de la réécriture", all(f'"ia.reecriture.{k}"' in dico for k in ("titre", "oui", "non", "aide")))


async def bloc_references():
    """t480 (F6.3) : GPT Image via fal prend plusieurs références (16 au plus), facturées en entrée."""
    print("\n[8] plusieurs références pour GPT Image via fal")
    ep, a = IP.build_fal_gpt_request("p", "square_hd", 1, ["u1", "u2", "u3"], model="gpt-image-2.5-sunburst")
    check("8.1 liste de références : toutes envoyées, dans l'ordre, sur /edit",
          ep.endswith("/edit") and a["image_urls"] == ["u1", "u2", "u3"], (ep, a.get("image_urls")))
    _, a = IP.build_fal_gpt_request("p", "square_hd", 1, "u1", model="gpt-image-2")
    check("8.2 une URL seule (forme d'avant) : inchangé", a["image_urls"] == ["u1"])
    _, a = IP.build_fal_gpt_request("p", "square_hd", 1, [f"u{i}" for i in range(20)], model="gpt-image-2")
    check("8.3 tronqué à 16 (schéma fal)", len(a["image_urls"]) == 16 == IP.REF_MAX_GPT_FAL)
    ep, a = IP.build_fal_gpt_request("p", "square_hd", 1, [], model="gpt-image-2")
    check("8.4 liste vide : texte → image", "image_urls" not in a and not ep.endswith("/edit"))
    check("8.5 multi_references : GPT fal oui, GPT direct non, Nano et Seedream oui, Recraft non",
          IP.multi_references("gpt-image-2-fal") and IP.multi_references("gpt-image-2.5-flare-fal")
          and not IP.multi_references("gpt-image-2") and not IP.multi_references("gpt-image-2.5-flare")
          and IP.multi_references("nano-banana") and IP.multi_references("seedream-5-pro")
          and not IP.multi_references("recraft-4.1-vecteur") and not IP.multi_references("flux"))
    # façade : trois chemins -> trois téléversements, trois URLs
    from app.services import fal_service as FS
    vus = []

    async def _up(ch):
        vus.append(pathlib.Path(ch).name)
        return "http://fal.test/" + pathlib.Path(ch).name
    _up0 = FS.FalSeedanceClient.upload_image
    FS.FalSeedanceClient.upload_image = staticmethod(_up)
    try:
        chemins = []
        for i in range(3):
            p = pathlib.Path(_tmp, f"ref{i}.png"); p.write_bytes(_PNG); chemins.append(p)
        FAL_CALLS.clear()
        await IP.generate("gpt-image-2.5-flare-fal", "p", "square_hd", 1, image_paths=chemins, qualite="low")
        a = FAL_CALLS[-1]["arguments"]
        check("8.6 façade : les trois références téléversées et envoyées", vus == ["ref0.png", "ref1.png", "ref2.png"]
              and a.get("image_urls") == [f"http://fal.test/ref{i}.png" for i in range(3)], (vus, a.get("image_urls")))
        check("8.7 façade : le palier suit toujours", a.get("quality") == "low")
        vus.clear()
        await IP.generate("gpt-image-2-fal", "p", "square_hd", 1, image_path=chemins[0])
        check("8.8 façade : une image seule (forme d'avant)", vus == ["ref0.png"]
              and FAL_CALLS[-1]["arguments"].get("image_urls") == ["http://fal.test/ref0.png"])
    finally:
        FS.FalSeedanceClient.upload_image = _up0
    d0 = P.estimate({"kind": "image", "n": 1, "model": "gpt-image-2.5-flare-fal"})
    d3 = P.estimate({"kind": "image", "n": 2, "model": "gpt-image-2.5-flare-fal", "refs": 3})
    check("8.9 devis sans références : inchangé (une ligne)", len(d0["breakdown"]) == 1)
    check("8.10 devis : 0,012 $ par référence et par image", abs(d3["total_usd"] - (2 * 0.053 + 2 * 3 * 0.012)) < 1e-3
          and len(d3["breakdown"]) == 2, d3)
    dn = P.estimate({"kind": "image", "n": 1, "model": "nano-banana", "refs": 5})
    check("8.11 Nano Banana : les références ne changent pas le prix", len(dn["breakdown"]) == 1)
    check("8.12 chaque id GPT via fal est facturé à la référence, au plus haut relevé (0,012 $)",
          set(P.IMAGE_REF_USD) == set(IP._FAL_GPT) and all(v >= 0.012 for v in P.IMAGE_REF_USD.values()))
    t = (ROOT / "backend/app/api/routes.py").read_text(encoding="utf-8")
    check("8.13 retouche : l'identité de l'espace accepte GPT via fal (multi_references)",
          "if not IP.multi_references(model):" in t)
    check("8.14 retouche : la garde chiffre les références", '"refs": 1 + len(refs_idv)}' in t)


if __name__ == "__main__":
    bloc_registre()
    bloc_devis()
    bloc_builders()
    bloc_catalogue()
    asyncio.run(bloc_route())
    bloc_ecran()
    asyncio.run(bloc_reecriture())
    asyncio.run(bloc_references())
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
