# -*- coding: utf-8 -*-
"""t205 (Espaces de marque E5, 13/10/2026) — l'ONBOARDING d'un persona.
Ce que ce banc garde :
  - le brouillon par espace : chaque étape validée champ par champ (champ inconnu, type, curseur hors 0-100, URL non
    http(s), nom de fichier avec chemin -> 400, RIEN d'écrit) ;
  - les 4 directions d'ambiance : déterministes, nourries des réponses (personnage, couleurs interdites) ; une vignette
    reste tant que le prompt de sa direction ne change pas ;
  - lire l'URL du produit : jamais une adresse privée ou locale, ni par redirection ; une page publique donne nom et
    pitch (faux transport httpx, aucun réseau) ;
  - vignettes : clé fal absente -> 503 AVANT la garde (aucune dépense écrite) ; avec la clé (faux FLUX) -> une ligne de
    dépense, une image par direction rangée dans le brouillon ;
  - synthèse SANS IA : le persona v2 complet tiré des réponses, rien de Deepotus ; synthèse par LLM : aucun LLM -> 503
    sans dépense ; faux LLM -> ses champs, COMPLÉTÉS par la manuelle, les mots interdits de l'utilisateur TOUJOURS
    bannis ; LLM illisible -> la manuelle, dit ;
  - rien n'est écrit dans le persona avant VALIDER ; valider garde les modèles et voix existants, pose `ecran` (id de
    l'espace) ; écritures réservées à la machine locale. Data-dir isolé, rien de payé.
Témoin : la base (cf948298) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_espaces_onboarding.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzonb_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY"):
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


r0 = subprocess.run(["git", "show", "cf948298:backend/app/services/onboarding_persona.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas le module", r0.returncode != 0)

import httpx                                                        # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import espaces as ES, onboarding_persona as OB   # noqa: E402
from app.api import routes as RT                                    # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
c.__enter__()
ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]
B = f"/api/espaces/{rip}/onboarding"
PERSONA_AVANT = ES.chemin(rip, "persona.json").read_bytes()

print("[E] le brouillon")
g = c.get(B).json()
check("E1 brouillon vide, 4 directions, devis gratuits rendus, voies payantes dites (aucune clé ici)",
      g["etapes"] == {} and len(g["directions"]) == 4 and g["devis"]["vignettes"]["total_usd"] > 0
      and g["voies"] == {"vignettes": False, "llm": False}, str(g)[:300])
REP = {
    "produit": {"nom": "Rippled", "url": "https://rippled.example/", "pitch": "Payments on the XRP Ledger, fast.", "produits": ["Wallet", "Bridge"]},
    "audience": {"qui": "devs et traders", "ou": ["x", "telegram"], "aime": ["vitesse"], "rejette": ["hype"]},
    "personnage": {"type": "mascotte", "description": "a sleek silver dolphin made of light", "nom": "Ripple Dolphin"},
    "ton": {"serieux_meme": 30, "oracle_copain": 70, "sobre_exuberant": 20, "garder": ["ledger"], "rejeter": ["moon"],
            "langues": ["en", "fr"], "catchphrase": "Settle in seconds.", "handle": "@rippled"},
    "interdits": {"sujets": ["gambling"], "mots": ["guaranteed returns"], "couleurs": ["neon pink"], "concurrents": ["X Corp"],
                  "legal": "pas de promesse de gain"},
}
for k, v in REP.items():
    r = c.put(f"{B}/{k}", json=v)
    check(f"E2 étape {k} enregistrée", r.status_code == 200 and r.json()["etapes"][k] == v, r.text[:200])
brut = (_tmp / "espaces" / rip / "onboarding.json").read_bytes()
for etape, corps, quoi in (("produit", {"inconnu": "x"}, "champ inconnu"), ("ton", {"serieux_meme": 150}, "curseur > 100"),
                           ("ton", {"serieux_meme": True}, "booléen pour un curseur"), ("produit", {"url": "file:///c:/x"}, "URL non http"),
                           ("audience", {"aime": "vitesse"}, "liste attendue"), ("references", {"images": ["../secret.png"]}, "chemin"),
                           ("personnage", {"type": "dragon"}, "choix inconnu"), ("nimporte", {}, "étape inconnue")):
    r = c.put(f"{B}/{etape}", json=corps)
    check(f"E3 refus ({quoi}) -> 400", r.status_code == 400, r.text[:120])
check("E4 aucun refus n'a écrit", (_tmp / "espaces" / rip / "onboarding.json").read_bytes() == brut)
check("E5 espace inconnu -> 404", c.get("/api/espaces/esp_nope/onboarding").status_code == 404)

print("\n[D] les directions d'ambiance")
dirs = c.get(B).json()["directions"]
check("D1 quatre partis pris, même sujet (le personnage), couleurs interdites évitées",
      [x["id"] for x in dirs] == ["cinema", "lumineux", "graphique", "organique"]
      and all("silver dolphin" in x["prompt"] and "neon pink" in x["prompt"] for x in dirs), dirs[0]["prompt"])
check("D2 déterministes", OB.directions(OB.brouillon(rip)) == OB.directions(OB.brouillon(rip)))

print("\n[V] les vignettes (payantes)")
from app.services.storage import Depense, async_session_factory     # noqa: E402
from sqlalchemy import select                                       # noqa: E402
async def depenses():
    async with async_session_factory() as s:
        return list((await s.execute(select(Depense))).scalars().all())
v0 = c.post(f"{B}/vignettes", json={})
check("V1 clé fal absente -> 503, AUCUNE dépense écrite", v0.status_code == 503 and asyncio.run(depenses()) == [], v0.text[:200])
settings.FAL_KEY = "cle-de-banc"
tirs = []
async def faux_flux(prompt, size, n, **kw):
    tirs.append(prompt)
    nom = f"gen_banc_{len(tirs)}.png"
    (_tmp / "images" / nom).write_bytes(b"png")
    return {"images": [nom], "seed": 1}
_of = RT._flux_generate
RT._flux_generate = faux_flux
try:
    v1 = c.post(f"{B}/vignettes", json={"ids": ["cinema", "graphique"]})
finally:
    RT._flux_generate = _of
dd = {x["id"]: x for x in (v1.json().get("directions") or [])}
dep = asyncio.run(depenses())
check("V2 deux directions demandées : deux tirs, leurs images rangées, les autres vides",
      v1.status_code == 200 and len(tirs) == 2 and dd["cinema"]["image"] == "gen_banc_1.png" and dd["graphique"]["image"] == "gen_banc_2.png"
      and dd["lumineux"]["image"] is None, v1.text[:300])
check("V3 la garde a écrit UNE ligne de dépense (catégorie reglages, ref onboarding)",
      len(dep) == 1 and dep[0].categorie == "reglages" and (dep[0].ref or "").startswith("onboarding:"), str([(d.categorie, d.ref) for d in dep]))
c.put(f"{B}/audience", json=dict(REP["audience"], qui="devs"))
check("V4 une réponse qui ne change pas le prompt garde les vignettes", {x["id"]: x["image"] for x in c.get(B).json()["directions"]}["cinema"] == "gen_banc_1.png")
c.put(f"{B}/personnage", json=dict(REP["personnage"], description="a golden wave"))
check("V5 un prompt changé efface la vignette périmée", {x["id"]: x["image"] for x in c.get(B).json()["directions"]}["cinema"] is None)
c.put(f"{B}/personnage", json=REP["personnage"])
c.put(f"{B}/ambiance", json={"choisies": ["cinema", "organique"], "rejetees": ["graphique"]})
c.put(f"{B}/references", json={"images": ["logo.png"]})

print("\n[U] lire l'URL du produit")
PAGE = '<html><head><title>Rippled | Fast payments</title><meta name="description" content="Settle on the XRP Ledger in 3 seconds."></head><body><p>Hello</p></body></html>'
HOTES = []
def transport(req):
    HOTES.append(req.url.host)
    if req.url.host == "rippled.example":
        return httpx.Response(200, text=PAGE)
    if req.url.host == "redirige.example":
        return httpx.Response(302, headers={"location": "http://127.0.0.1:8765/api/settings/keys"})
    return httpx.Response(404)
cl = httpx.Client(transport=httpx.MockTransport(transport))
lu = OB.lire_url("https://rippled.example/", client=cl)
check("U1 une page publique donne nom et pitch", lu["nom"] == "Rippled" and lu["pitch"].startswith("Settle on the XRP Ledger"), str(lu))
for u in ("http://127.0.0.1:8765/api/settings/keys", "http://localhost/", "http://10.0.0.2/", "http://[::1]/", "http://deepotus.localhost/"):
    try:
        OB.lire_url(u, client=cl); check(f"U2 refusé : {u}", False)
    except ValueError:
        check(f"U2 refusé : {u}", True)
HOTES.clear()
try:
    OB.lire_url("https://redirige.example/", client=cl); check("U3 une redirection vers la boucle locale est refusée", False)
except ValueError as e:
    check("U3 une redirection vers la boucle locale est refusée AVANT d'être suivie (jamais contactée)",
          "privée" in str(e) and HOTES == ["redirige.example"], f"{e} / {HOTES}")
check("U4 la route refuse une adresse privée (400)", c.post(f"{B}/lire-url", json={"url": "http://192.168.1.1/"}).status_code == 400)

print("\n[S] la synthèse")
check("S0 le persona n'a pas bougé avant VALIDER", ES.chemin(rip, "persona.json").read_bytes() == PERSONA_AVANT)
sm = c.post(f"{B}/synthese", json={}).json()
check("S1 sans IA : nom, mission, mots-clés des directions choisies, interdits dans le négatif",
      sm["display_name"] == "Rippled" and sm["identite"]["mission"].startswith("Payments") and "cinematic" in sm["vibe_keywords"]
      and "neon pink" in sm["default_negative_prompt"] and "bold flat colors" in sm["default_negative_prompt"], json.dumps(sm)[:400])
e = sm["ecran"]
check("S2 persona d'écran à l'id de l'espace, ton tiré des curseurs, interdits bannis",
      e["id"] == rip and e["name"] == "Ripple Dolphin" and e["handle"] == "@rippled" and e["catchphrase"] == "Settle in seconds."
      and "guaranteed returns" in e["banned"] and "moon" in e["banned"] and e["languages"] == ["EN", "FR"] and e["emojiPolicy"] == "none", str(e))
check("S3 rien de Deepotus dans la proposition", "deepotus" not in json.dumps(sm).lower())
check("S4 la proposition est gardée dans le brouillon, le persona toujours intact",
      OB.brouillon(rip)["proposition"]["source"] == "manuelle" and ES.chemin(rip, "persona.json").read_bytes() == PERSONA_AVANT)
n_dep = len(asyncio.run(depenses()))
s1 = c.post(f"{B}/synthese", json={"llm": True})
check("S5 par LLM sans aucun LLM -> 503, aucune dépense", s1.status_code == 503 and len(asyncio.run(depenses())) == n_dep)
from app.services import summarizer as SMZ                          # noqa: E402
_oa, _od = SMZ._available_providers, SMZ._chat_dispatch
SMZ._available_providers = lambda: ["anthropic"]
settings.ANTHROPIC_API_KEY = "cle-de-banc"          # pour que la garde chiffre l'appel chez Anthropic (sinon « local », gratuit)
SMZ._chat_dispatch = lambda prompt, system, mt: ('```json\n{"display_name": "Rippled Network", "mission": "Move value at internet speed.",'
                                                 ' "vibe_keywords": ["liquid silver", "speed lines"], "ecran": {"role": "Le guide calme du ledger",'
                                                 ' "banned": ["wagmi"], "tone": ["calm", "precise"]}}\n```', "anthropic")
try:
    s2 = c.post(f"{B}/synthese", json={"llm": True}).json()
    SMZ._chat_dispatch = lambda prompt, system, mt: ("désolé je ne sais pas", "anthropic")
    s3 = c.post(f"{B}/synthese", json={"llm": True}).json()
finally:
    SMZ._available_providers, SMZ._chat_dispatch = _oa, _od
    settings.ANTHROPIC_API_KEY = ""
check("S6 faux LLM : ses champs pris, le reste COMPLÉTÉ par la manuelle, chaque appel dépensé",
      s2["display_name"] == "Rippled Network" and s2["identite"]["mission"] == "Move value at internet speed."
      and s2["vibe_keywords"] == ["liquid silver", "speed lines"] and s2["ecran"]["role"] == "Le guide calme du ledger"
      and s2["ecran"]["handle"] == "@rippled" and s2["source"] == "llm:anthropic"
      and len(asyncio.run(depenses())) == n_dep + 2,   # deux appels (S6 et S8, illisible), deux lignes de dépense
      json.dumps(s2)[:300])
check("S7 les mots interdits de l'utilisateur restent bannis même si le LLM les oublie",
      {"guaranteed returns", "moon", "wagmi"} <= set(s2["ecran"]["banned"]), str(s2["ecran"]["banned"]))
check("S8 LLM illisible : la manuelle, et c'est dit", s3["source"] == "manuelle" and "rien rendu de lisible" in s3.get("note", ""), str(s3)[:200])

print("\n[W] valider")
ES.ecrire_persona(rip, dict(ES.persona(rip), templates=[dict(json.loads((RACINE / "backend/app/personas/deepotus.json").read_text(encoding="utf-8"))["templates"][0], id="rip_tpl")],
                            voice_ids={"en": {"voice_id": "v1"}}))
w0 = c.post("/api/espaces/deepotus/onboarding/valider", json={})
check("W1 valider sans proposition -> 400", w0.status_code == 400)
corrigee = dict(s2, display_name="Rippled (corrigé)")
w = c.post(f"{B}/valider", json={"proposition": corrigee})
p = ES.persona(rip)
check("W2 valider écrit la proposition CORRIGÉE dans le persona", w.status_code == 200 and p["display_name"] == "Rippled (corrigé)"
      and p["visuel"]["references"] == ["logo.png"] and p["ecran"]["id"] == rip and p["onboarding"]["source"] == "llm:anthropic", w.text[:300])
check("W3 ... en gardant les modèles et les voix existants", [t["id"] for t in p["templates"]] == ["rip_tpl"] and p["voice_ids"] == {"en": {"voice_id": "v1"}})
check("W4 Deepotus intact", ES.persona("deepotus")["display_name"].startswith("Deepotus"))
dist = TestClient(app, client=("192.168.1.20", 50000))
check("W5 écrire depuis le réseau local sans jeton -> refusé", dist.put(f"{B}/produit", json={"nom": "x"}).status_code in (401, 403)
      and dist.post(f"{B}/valider", json={}).status_code in (401, 403))
check("W6 effacer le brouillon", c.delete(B).status_code == 200 and c.get(B).json()["etapes"] == {})

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
