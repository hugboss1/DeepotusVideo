# -*- coding: utf-8 -*-
"""t207 (Espaces de marque E7, 13/10/2026) — les CONTENUS DE DÉPART d'un espace (contenus.json, spec D5).
Ce que ce banc garde :
  - la validation : la graine Deepotus passe TELLE QUELLE ; identifiant, doublon, catégorie inconnue, preset inconnu,
    plafonds, champ inconnu -> 400 et RIEN d'écrit ; écritures réservées à la machine locale ;
  - la proposition SANS IA : tirée du persona (personnage, produits, directions d'ambiance choisies) et de son identité
    (palette, descripteurs) — rien de Deepotus ; une catégorie seule ; une catégorie inconnue -> 400 ; rien d'écrit ;
  - la doctrine : un modèle qui nomme un artiste ou un interdit du persona est ÉCARTÉ (et dit) ;
  - par LLM : aucun LLM -> 503 AVANT la garde (aucune dépense) ; faux LLM -> ses modèles, un modèle invalide écarté, la
    proposition sans IA en repli de chaque partie, UNE ligne de dépense par appel ; illisible -> sans IA, et c'est dit ;
  - appliquer : ajouter les cochés (un id pris reçoit un suffixe), remplacer UNE catégorie, tout remplacer (catégories,
    ingrédients, vibes) ; une proposition invalide -> 400, rien d'écrit ; Deepotus jamais touché ;
  - l'onboarding validé sème les contenus d'un espace SANS modèle (jamais un espace qui en a, jamais Deepotus).
Data-dir isolé, rien de payé.
Témoin : la base (aa61fa8f) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_espaces_contenus.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzct_"))
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


r0 = subprocess.run(["git", "show", "aa61fa8f:backend/app/services/contenus_espace.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas le module", r0.returncode != 0)

from app.config import settings                                     # noqa: E402
from app.services import espaces as ES, contenus_espace as CE, identite as IDV, onboarding_persona as OB   # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import Depense, async_session_factory     # noqa: E402
from sqlalchemy import select                                       # noqa: E402
c = TestClient(app)
c.__enter__()
dist = TestClient(app, client=("192.168.1.20", 50000))
ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]
B = f"/api/espaces/{rip}/contenus"
GRAINE = (RACINE / "backend/app/espaces/deepotus_contenus.json").read_bytes()
DEEP = ES.chemin("deepotus", "contenus.json")


async def _dep():
    async with async_session_factory() as s:
        return list((await s.execute(select(Depense))).scalars().all())
def depenses():
    return asyncio.run(_dep())


print("[V] la validation")
seed = json.loads(GRAINE.decode("utf-8"))
check("V1 la graine Deepotus passe la validation TELLE QUELLE", CE.valider(seed) == seed)
avant = ES.chemin(rip, "contenus.json").read_bytes()
cat = [{"id": "produit", "label": "Produit"}]
tpl = {"id": "a", "cat": "produit", "title": "A", "emoji": "", "short": "", "body": "x"}
for i, (corps, attendu) in enumerate([
        ({"prompt_cats": cat, "prompt_templates": [dict(tpl, id="Pas Bon")]}, "identifiant"),
        ({"prompt_cats": cat, "prompt_templates": [tpl, tpl]}, "double"),
        ({"prompt_cats": cat, "prompt_templates": [dict(tpl, cat="autre")]}, "catégorie inconnue"),
        ({"prompt_cats": cat, "vibes": [{"id": "v", "preset": "vhs", "tags": ""}]}, "preset"),
        ({"prompt_cats": cat * 13}, "12"),
        ({"prompt_cats": cat, "prompt_templates": [dict(tpl, body="")]}, "body"),
        ({"prompt_cats": cat, "ingredients": {"subject": ["x"] * 21}}, "20"),
        ({"prompt_cats": cat, "autre": 1}, "champ inconnu")], 1):
    r = c.put(B, json=corps)
    check(f"V{i + 1}b {attendu} -> 400, rien d'écrit", r.status_code == 400 and attendu.lower() in r.text.lower()
          and ES.chemin(rip, "contenus.json").read_bytes() == avant, r.text[:160])
r = c.put(B, json={"prompt_cats": cat, "prompt_templates": [tpl], "vibes": [{"id": "v", "preset": "hybrid", "tags": "t"}]})
check("V10 des contenus valides s'écrivent", r.status_code == 200 and r.json()["prompt_templates"][0]["id"] == "a")
check("V11 depuis le réseau local sans jeton -> refusé", dist.put(B, json={}).status_code in (401, 403)
      and dist.post(f"{B}/generer", json={}).status_code in (401, 403) and dist.post(f"{B}/appliquer", json={}).status_code in (401, 403))
c.put(B, json=ES.CONTENUS_VIDES)

print("\n[M] la proposition sans IA")
ES.ecrire_persona(rip, dict(ES.persona(rip), display_name="Rippled",
                            identite={"nom": "Rippled", "produits": ["ceramic mug", "glazed vase"]},
                            visuel={"personnage": {"type": "mascotte", "description": "a calm otter potter", "nom": "Otto"},
                                    "directions_choisies": ["organique", "graphique"],
                                    "interdits": {"sujets": ["casino"], "couleurs": [], "concurrents": ["potteryco"]}},
                            ecran={"id": rip, "tone": ["warm", "patient"], "banned": ["moon"]},
                            default_hashtags_pool=["#Rippled", "#Ceramics"]))
IDV.ecrire(rip, {"palette": [{"hex": "#c2410c", "role": "primaire"}], "style_ecrit": "warm terracotta tones, matte glaze"})
g = c.post(f"{B}/generer", json={})
p = g.json()
cats = [x["id"] for x in p.get("prompt_cats", [])]
corps = json.dumps(p, ensure_ascii=False).lower()
check("M1 catégories : les directions choisies d'abord, puis produit/personnage/ambiance/social",
      g.status_code == 200 and cats[:2] == ["organique", "graphique"] and "produit" in cats, str(cats))
check("M2 modèles nourris du persona (personnage, produits) et de l'identité (palette, style)",
      any("a calm otter potter" in t["body"] for t in p["prompt_templates"]) and any("ceramic mug" in t["body"] for t in p["prompt_templates"])
      and any("#C2410C" in t["body"] for t in p["prompt_templates"]) and any("warm terracotta tones" in t["body"] for t in p["prompt_templates"])
      and p["hashtags"] == ["#Rippled", "#Ceramics"])
check("M3 rien de Deepotus", not any(w in corps for w in ("deepotus", "tentacle", "abyss", "bioluminescent", "throne")))
check("M4 ingrédients et vibes valides (presets connus)", set(p["ingredients"]) >= {"subject", "mood", "light"}
      and {v["preset"] for v in p["vibes"]} <= set(CE.PRESETS) and "a calm otter potter" in p["ingredients"]["subject"])
check("M5 rien n'est écrit par une proposition", ES.contenus(rip)["prompt_templates"] == [])
g2 = c.post(f"{B}/generer", json={"categorie": "produit"}).json()
check("M6 une catégorie seule", {t["cat"] for t in g2["prompt_templates"]} == {"produit"} and [x["id"] for x in g2["prompt_cats"]] == ["produit"])
check("M7 catégorie inconnue -> 400", c.post(f"{B}/generer", json={"categorie": "zzz"}).status_code == 400)

print("\n[F] la doctrine")
fp = CE._filtrer(rip, {"prompt_cats": cat, "prompt_templates": [
    dict(tpl, id="ok1", body="a calm otter at a wheel"), dict(tpl, id="art", body="mug, in the style of Van Gogh"),
    dict(tpl, id="cas", body="otter in a CASINO"), dict(tpl, id="conc", body="like PotteryCo ads")]})
check("F1 artiste et interdits (sujet, concurrent) écartés et dits", [t["id"] for t in fp["prompt_templates"]] == ["ok1"]
      and len(fp.get("_ecartes", [])) == 3, json.dumps(fp)[:300])

print("\n[L] par LLM (payant, sur demande)")
d0 = c.get(f"{B}/devis").json()
check("L0 devis : voie fermée sans LLM, devis rendu (sans clé : chiffré « local », gratuit)", d0["llm"] is False
      and d0["devis"]["breakdown"] and d0["devis"]["total_usd"] >= 0, str(d0))
l1 = c.post(f"{B}/generer", json={"llm": True})
check("L1 aucun LLM -> 503, AUCUNE dépense", l1.status_code == 503 and depenses() == [], l1.text[:160])
from app.services import summarizer as SMZ                          # noqa: E402
_oa, _od = SMZ._available_providers, SMZ._chat_dispatch
SMZ._available_providers = lambda: ["anthropic"]
settings.ANTHROPIC_API_KEY = "cle-de-banc"
REP = {"prompt_cats": [{"id": "atelier", "label": "Atelier"}, {"id": "vitrine", "label": "Vitrine"}],
       "prompt_templates": [
           {"id": "Wheel Spin", "cat": "atelier", "title": "Wheel spin", "emoji": "🏺", "short": "Otter throws a pot",
            "body": "A calm otter shapes wet clay on a spinning wheel, macro lens, warm side light, terracotta palette."},
           {"id": "bad", "cat": "inexistante", "title": "x", "body": "y"},
           {"id": "copy", "cat": "vitrine", "title": "Copy", "body": "vase on a plinth in the style of Picasso"},
           {"id": "shelf", "cat": "vitrine", "title": "Shelf", "emoji": "🪴", "short": "Products on oak",
            "body": "Glazed vases on an oak shelf, soft morning window light, slow dolly, matte textures."}],
       "vibes": [{"id": "clay", "preset": "vhs", "tags": "x"}],
       "hashtags": ["#Clay"]}
appels = []
def faux(prompt, system, mt):
    appels.append(prompt)
    return "```json\n" + json.dumps(REP) + "\n```", "anthropic"
SMZ._chat_dispatch = faux
try:
    l2 = c.post(f"{B}/generer", json={"llm": True}).json()
    REP2 = {"prompt_templates": [{"id": "z", "cat": "produit", "title": "Only", "body": "A glazed vase turning slowly."}]}
    SMZ._chat_dispatch = lambda p_, s_, m_: (json.dumps(REP2), "anthropic")
    l3 = c.post(f"{B}/generer", json={"llm": True, "categorie": "produit"}).json()
    SMZ._chat_dispatch = lambda p_, s_, m_: ("je ne sais pas", "anthropic")
    l4 = c.post(f"{B}/generer", json={"llm": True}).json()
finally:
    SMZ._available_providers, SMZ._chat_dispatch = _oa, _od
    settings.ANTHROPIC_API_KEY = ""
ids2 = [t["id"] for t in l2.get("prompt_templates", [])]
check("L2 faux LLM : ses modèles valides (id remis en slug), catégorie inconnue et artiste ÉCARTÉS",
      ids2 == ["wheel-spin", "shelf"] and [x["id"] for x in l2["prompt_cats"]] == ["atelier", "vitrine"]
      and l2["source"] == "llm:anthropic" and l2["hashtags"] == ["#Clay"], json.dumps(l2)[:400])
check("L3 ... une partie invalide (vibe au preset inconnu) garde la proposition sans IA, et c'est dit",
      {v["id"] for v in l2["vibes"]} >= {"cinematic", "ugc_raw"} and "vibes" in l2.get("note", ""), l2.get("note"))
check("L4 le LLM reçoit le persona (personnage, interdits) et l'identité visuelle", appels and "a calm otter potter" in appels[0]
      and "casino" in appels[0] and "warm terracotta tones" in appels[0])
check("L5 une catégorie : seulement elle", [t["cat"] for t in l3["prompt_templates"]] == ["produit"]
      and [x["id"] for x in l3["prompt_cats"]] == ["produit"], json.dumps(l3)[:300])
check("L6 illisible : la proposition sans IA, et c'est dit", "rien rendu de lisible" in l4.get("note", "")
      and l4["prompt_templates"] and "source" not in l4)
check("L7 trois appels par LLM = trois lignes de dépense (catégorie quick)", len(depenses()) == 3
      and all(x.categorie == "quick" for x in depenses()), str([(x.categorie, x.ref) for x in depenses()]))

print("\n[A] appliquer")
a1 = c.post(f"{B}/appliquer", json={"proposition": p, "mode": "ajouter", "tout": True})
ct = ES.contenus(rip)
check("A1 tout appliquer : modèles, catégories, ingrédients, vibes, hashtags de la proposition",
      a1.status_code == 200 and len(ct["prompt_templates"]) == len(p["prompt_templates"]) and ct["ingredients"] == p["ingredients"]
      and ct["vibes"] == p["vibes"] and ct["hashtags"] == p["hashtags"], a1.text[:200])
un = p["prompt_templates"][0]["id"]
c.post(f"{B}/appliquer", json={"proposition": p, "mode": "ajouter", "ids": [un]})
ids = [t["id"] for t in ES.contenus(rip)["prompt_templates"]]
check("A2 ajouter un modèle coché déjà présent : il reçoit un suffixe", ids.count(un) == 1 and f"{un[:36]}-2" in ids
      and len(ids) == len(p["prompt_templates"]) + 1, str(ids))
n_prod = sum(1 for t in ES.contenus(rip)["prompt_templates"] if t["cat"] == "produit")
n_hors = sum(1 for t in ES.contenus(rip)["prompt_templates"] if t["cat"] != "produit")
c.post(f"{B}/appliquer", json={"proposition": l3, "mode": "remplacer", "categorie": "produit"})
ct = ES.contenus(rip)
check("A3 remplacer UNE catégorie (qui avait des modèles) : les siens remplacés, les autres gardés",
      n_prod >= 2 and [t["id"] for t in ct["prompt_templates"] if t["cat"] == "produit"] == ["z"]
      and sum(1 for t in ct["prompt_templates"] if t["cat"] != "produit") == n_hors, json.dumps(ct)[:300])
c.post(f"{B}/appliquer", json={"proposition": l2, "mode": "ajouter", "ids": ["wheel-spin"]})
check("A3b ajouter apporte la catégorie neuve du modèle", "atelier" in [x["id"] for x in ES.contenus(rip)["prompt_cats"]])
c.post(f"{B}/appliquer", json={"proposition": l2, "mode": "remplacer", "tout": True})
ct = ES.contenus(rip)
check("A4 tout remplacer : seulement les modèles de la proposition, catégories vides retirées",
      [t["id"] for t in ct["prompt_templates"]] == ["wheel-spin", "shelf"] and [x["id"] for x in ct["prompt_cats"]] == ["atelier", "vitrine"],
      json.dumps(ct)[:300])
av = ES.chemin(rip, "contenus.json").read_bytes()
a5 = c.post(f"{B}/appliquer", json={"proposition": {"prompt_templates": [tpl]}, "mode": "ajouter"})
a6 = c.post(f"{B}/appliquer", json={"proposition": l2, "mode": "fusionner"})
check("A5 proposition invalide ou mode inconnu -> 400, rien d'écrit", a5.status_code == 400 and a6.status_code == 400
      and ES.chemin(rip, "contenus.json").read_bytes() == av)
check("A6 Deepotus jamais touché : son contenus.json est la graine, servie telle quelle",
      DEEP.read_bytes() == GRAINE and c.get("/api/espaces/deepotus/contenus").json() == seed)

print("\n[O] l'onboarding sème les contenus d'un espace vide")
neuf = ES.creer({"nom": "Client"})["id"]
OB.enregistrer_etape(neuf, "produit", {"nom": "Client Co", "produits": ["solar lamp"]})
OB.proposer(neuf, OB.synthese_manuelle(neuf))
OB.valider(neuf)
cn = ES.contenus(neuf)
check("O1 valider l'onboarding d'un espace sans modèle écrit ses contenus de départ",
      cn["prompt_templates"] and any("solar lamp" in t["body"] for t in cn["prompt_templates"]), json.dumps(cn)[:200])
av = ES.chemin(rip, "contenus.json").read_bytes()
OB.proposer(rip, OB.synthese_manuelle(rip))
OB.valider(rip)
check("O2 ... jamais un espace qui a déjà des modèles", ES.chemin(rip, "contenus.json").read_bytes() == av)
check("O3 ... jamais Deepotus", CE.semer_si_vide("deepotus") is False and DEEP.read_bytes() == GRAINE)

print("\n[E] l'écran (maillon dzespace, C1-C6)")
sys.path.insert(0, str(RACINE / "scripts"))
import patch_bundle_dzespace as M                                   # noqa: E402
BUNDLE = (RACINE / M.BUNDLE).read_bytes().decode("utf-8")
_ct = [pr for pr in M.PAIRES if "dzCt" in pr[1] or "DzContenusBtn" in pr[1]]
check("E1 les 7 paires de t207 (aides, C1-C3, C5 vibes et prompt par défaut, C6) posées une fois chacune dans le bundle livré",
      len(_ct) == 7 and all(BUNDLE.count(b) == 1 for _a, b in _ct), str([BUNDLE.count(b) for _a, b in _ct]))
check("E2 la liste Deepotus livrée reste dans le bundle (repli), aucun useState ajouté (731)",
      'const fd=[{id:"deep-throne"' in BUNDLE and BUNDLE.count("x.useState(") == 731 and "x.useState(" not in M.AIDES_CT)
JS = ("var x={useReducer:function(){return[0,function(){}]},useEffect:function(){}},r={};var window={addEventListener:function(){}};"
      + M.AIDES_CT + ";var D=[1],O={a:[1]},out=[];out.push(dzCt('prompt_templates',D)===D);"
      "dzEspCt={id:'deepotus',data:{prompt_templates:[2],ingredients:{}}};out.push(dzCt('prompt_templates',D)[0]===2);"
      "out.push(dzCt('ingredients',O)===O);"
      "dzEspCt={id:'esp_x',data:{prompt_templates:[],ingredients:{},vibes:[]}};"
      "out.push(Array.isArray(dzCt('prompt_templates',D))&&dzCt('prompt_templates',D).length===0);"
      "out.push(JSON.stringify(dzCt('ingredients',O))==='{}');out.push(dzCt('vibes',D)===D);"
      "dzEspCt={id:'esp_x',data:{prompt_templates:[3]}};out.push(dzCt('prompt_templates',D)[0]===3);"
      "console.log(JSON.stringify(out))")
rn = subprocess.run(["node", "-e", JS], capture_output=True, text=True, encoding="utf-8")
check("E3 dzCt : rien de chargé -> livré ; Deepotus -> ses contenus, vide -> livré ; autre espace -> les siens, VIDES "
      "compris (jamais Deepotus), sauf les vibes", rn.stdout.strip() == "[true,true,true,true,true,true,true]", rn.stdout + rn.stderr[-300:])

c.__exit__(None, None, None)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
