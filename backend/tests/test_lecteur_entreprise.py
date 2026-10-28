# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5c : le LECTEUR RENFORCÉ des pages d'entreprise. robots.txt lu et
respecté (refus dit, gardé 24 h) ; une requête par seconde au plus par domaine ; à partir d'une URL autorisée, 5 pages au
plus du MÊME domaine (la page, puis contact, mentions légales, à propos) ; l'e-mail retenu peut venir de l'une d'elles ;
jamais un autre domaine. Faux téléchargement et fausse horloge, aucun réseau.
Run (depuis backend/) : & $PY tests/test_lecteur_entreprise.py"""
import asyncio, os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlec_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
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


from app.services import agent_format as fmt, agent_outils as ao, agent_store as st, espaces as E, prospects as P   # noqa: E402
from app.services.storage import init_db                                                                          # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 28)
SITE = {"https://studio-lune.fr/robots.txt": "User-agent: *\nDisallow: /prive/\n",
        "https://studio-lune.fr/": "Studio Lune, studio vidéo à Lyon.",
        "https://studio-lune.fr/contact": "Contact : bonjour@studio-lune.fr",
        "https://studio-lune.fr/mentions-legales": "Éditeur : Studio Lune SAS, contact@studio-lune.fr",
        "https://studio-lune.fr/a-propos": "Nous sommes 12.",
        "https://ferme.fr/robots.txt": "User-agent: *\nDisallow: /\n",
        "https://ferme.fr/": "page"}
LUES, ATTENTES = [], []
T = [100.0]


async def faux_telecharger(url):
    LUES.append(url)
    if url not in SITE:
        raise ao._Refus("URL : réponse 404")
    return SITE[url]


async def faux_dormir(s):
    ATTENTES.append(s)
    T[0] += s


ao._telecharger = faux_telecharger
ao._url_sure = lambda u: None
ao._HORLOGE = lambda: T[0]
ao._DORMIR = faux_dormir


async def main():
    await init_db()
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    ctx = ao.Ctx(cid=cid, espace_id=A)
    await st.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte":
                           "https://studio-lune.fr/ et https://ferme.fr/ et https://studio-lune.fr/prive/x"}])])

    print("[1] pages du même domaine")
    r = await ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lune.fr/"}, ctx)
    pages = [u for u in LUES if not u.endswith("robots.txt")]
    check("1a la page, puis contact, mentions légales, à propos (5 au plus, même domaine)", r["ok"]
          and pages[0] == "https://studio-lune.fr/" and "https://studio-lune.fr/contact" in pages
          and "https://studio-lune.fr/mentions-legales" in pages and len(pages) <= 5
          and all(u.startswith("https://studio-lune.fr/") for u in LUES), LUES)
    check("1b le texte des pages revient en PREUVE, pages nommées", "bonjour@studio-lune.fr" in r["donnees"]["texte"]
          and "contact@studio-lune.fr" in r["donnees"]["texte"] and r["donnees"]["pages"][0] == "https://studio-lune.fr/", r["donnees"].get("pages"))
    check("1c une requête par seconde : attentes entre deux lectures", ATTENTES and all(0 < a <= 1.0 for a in ATTENTES)
          and len(ATTENTES) >= len(pages) - 1, ATTENTES)
    n_robots = sum(u.endswith("robots.txt") for u in LUES)
    r = await ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lune.fr/",
                                                 "fiche": {"entreprise": "Studio Lune", "email": "contact@studio-lune.fr"}}, ctx)
    check("1d l'e-mail des mentions légales suffit", r["ok"] and r["donnees"]["crees"] == 1, r["resume"])
    check("1e robots.txt gardé (une seule lecture)", sum(u.endswith("robots.txt") for u in LUES) == n_robots == 1, LUES)

    print("[2] robots.txt")
    LUES.clear()
    r = await ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://ferme.fr/"}, ctx)
    check("2a site fermé aux robots : refus dit, page jamais lue", not r["ok"] and "robots" in r["resume"]
          and "https://ferme.fr/" not in LUES, (r["resume"], LUES))
    r = await ao.executer("prospects_chercher", {"source": "entreprise", "url": "https://studio-lune.fr/prive/x"}, ctx)
    check("2b chemin interdit : refus dit", not r["ok"] and "robots" in r["resume"], r["resume"])


asyncio.run(main())
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
