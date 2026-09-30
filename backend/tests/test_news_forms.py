# -*- coding: utf-8 -*-
"""Les formes de reel News et leur cout AVANT tir (plan 2026-09-03 T11, tache #35 du suivi, 30/09/2026).

Aucun fournisseur appele : le catalogue, l'estimation (pricing.estimate, deja eprouve), la disponibilite par la CLE du
fournisseur et les refus motives. Temoin : les routes /news/forms n'existent pas a la base (dd60e50).
Run (depuis backend/) : & $PY tests/test_news_forms.py"""
import os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewsf_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
from app.services import news_forms as F, pricing                   # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


TROIS = [{"title": f"Sujet numero {n}", "source_name": "CoinDesk", "link": "https://c/1", "id": f"a{n}"} for n in range(3)]
r0 = subprocess.run(["git", "show", "dd60e50:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : aucune route /news/forms a la base", r0.returncode == 0 and b"/news/forms" not in r0.stdout)

print("\n[A] catalogue")
ids = [f["id"] for f in F.catalogue()]
check("A1 cinq formes : les cartes gratuites d'abord, puis les quatre de R8",
      ids == ["cartes", "illustration_ia", "plans_seedance", "avatar", "voix_sous_titres"], str(ids))
check("A2 chaque forme a label, description, producteur, et dit si elle est payante",
      all(f["label"] and f["description"] and (f["producteur"].startswith("/") or ":" in f["producteur"])
          and isinstance(f["payant"], bool) for f in F.catalogue()))
check("A3 seules les cartes sont gratuites", [f["id"] for f in F.catalogue() if not f["payant"]] == ["cartes"])
c = F.catalogue(); c[0]["id"] = "vandale"
check("A4 le catalogue rendu est une copie", F.catalogue()[0]["id"] == "cartes")

print("\n[B] devis")
d = F.estimer("cartes", TROIS)
check("B1 cartes : 0 $, aucun poste, rendu local dit", d["total_usd"] == 0 and d["breakdown"] == [] and d["detail"]["cartes"] == 3
      and "gratuit" in d["detail"]["rendu"], str(d))
d = F.estimer("illustration_ia", TROIS, {"model": "flux"})
check("B2 illustration IA : une image par titre (x3) au prix du registre", d["total_usd"] > 0 and any("x3" in l["label"] for l in d["breakdown"])
      and d["forme"] == "illustration_ia" and abs(d["total_usd"] - pricing.estimate({"kind": "image", "n": 3, "model": "flux"})["total_usd"]) < 1e-9, str(d))
check("B3 deux titres coutent moins que trois", F.estimer("illustration_ia", TROIS[:2])["total_usd"] < F.estimer("illustration_ia", TROIS)["total_usd"])
d = F.estimer("plans_seedance", TROIS, {"model": "seedance-2-fast", "duration_s": 5})
check("B4 plans Seedance : la duree par sujet (15 s) et le prix de 3 plans", d["detail"]["secondes"] == 15
      and abs(d["total_usd"] - 3 * F.estimer("plans_seedance", TROIS[:1], {"duration_s": 5})["total_usd"]) < 1e-6, str(d["total_usd"]))
check("B5 une duree illisible retombe sur 5 s", F.estimer("plans_seedance", TROIS, {"duration_s": "abc"})["detail"]["secondes"] == 15)
check("B5b une duree NaN ou negative retombe aussi sur 5 s (pas de devis negatif ni NaN)",
      all(F.estimer("plans_seedance", TROIS, {"duration_s": v})["detail"]["secondes"] == 15 for v in ("nan", -3, 1e12)))
check("B6 avatar : les caracteres du script", F.estimer("avatar", TROIS, {"chars": 600})["total_usd"] > 0
      and F.estimer("avatar", TROIS, {"chars": 600})["detail"]["caracteres"] == 600)
d = F.estimer("voix_sous_titres", TROIS, {"chars": 600})
check("B7 voix off : ElevenLabs, aucune transcription payante", "elevenlabs" in [l["provider"] for l in d["breakdown"]]
      and not any(l["label"].lower().startswith("transcri") for l in d["breakdown"]))
for forme, items, mot in (("hologramme", TROIS, "hologramme"), ("illustration_ia", [], "aucun article")):
    try:
        F.estimer(forme, items, {}); m = ""
    except ValueError as e:
        m = str(e)
    check(f"B8 refus motive : {mot}", mot in m.lower() and (forme != "hologramme" or "cartes" in m), m)

print("\n[C] disponibilite par la cle")
sauve = (settings.FAL_KEY, settings.HEYGEN_API_KEY, settings.ELEVENLABS_API_KEY)
settings.FAL_KEY, settings.HEYGEN_API_KEY, settings.ELEVENLABS_API_KEY = "", "", ""
check("C1 sans cle : seules les cartes sont disponibles", [i for i in F.IDS if F.disponible(i)] == ["cartes"])
settings.FAL_KEY, settings.HEYGEN_API_KEY, settings.ELEVENLABS_API_KEY = "k", "k", "k"
check("C2 avec les cles : toutes disponibles", all(F.disponible(i) for i in F.IDS))
settings.FAL_KEY, settings.HEYGEN_API_KEY, settings.ELEVENLABS_API_KEY = sauve
check("C3 une forme inconnue n'est pas disponible", F.disponible("hologramme") is False)

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
