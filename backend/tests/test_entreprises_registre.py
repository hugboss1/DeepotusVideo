# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5a : le REGISTRE DES ENTREPRISES (API Recherche d'entreprises de
l'État, gratuite, sans clé). Sociétés actives seulement ; jamais un entrepreneur individuel (personne physique), jamais une
diffusion partielle ; jamais les dirigeants ; 429 → un nouvel essai puis refus dit ; cache 24 h ; outil `entreprises_registre`
de l'agent (lecture, gratuit) qui rend des CIBLES, pas des fiches. Faux transport, aucun réseau.
Run (depuis backend/) : & $PY tests/test_entreprises_registre.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzreg_"))
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


from app.services import agent_boites as B, agent_outils as ao, agent_store as st, espaces as E   # noqa: E402
from app.services import entreprises_registre as RG, prospects as P                            # noqa: E402
from app.services.storage import init_db                                                       # noqa: E402

SOC = {"siren": "428841472", "nom_complet": "E MAGINEURS", "activite_principale": "59.11A", "etat_administratif": "A",
       "nature_juridique": "5710", "statut_diffusion": "O", "tranche_effectif_salarie": "12", "date_creation": "2000-01-01",
       "siege": {"code_postal": "69009", "libelle_commune": "LYON", "adresse": "31 RUE GORGE DE LOUP 69009 LYON"},
       "dirigeants": [{"nom": "DUPONT", "prenoms": "Jean", "type_dirigeant": "personne physique"}]}
EI = dict(SOC, siren="111111111", nom_complet="JEAN DUPONT", nature_juridique="1000")
PARTIEL = dict(SOC, siren="222222222", nom_complet="CACHEE", statut_diffusion="P")
FERMEE = dict(SOC, siren="333333333", nom_complet="FERMEE", etat_administratif="C")
APPELS, REPONSES = [], []


async def faux_get(url, params):
    APPELS.append((url, dict(params)))
    statut, corps = REPONSES.pop(0) if REPONSES else (200, {"results": [SOC, EI, PARTIEL, FERMEE], "total_results": 4})
    return statut, corps


RG._GET = faux_get
RG._DORMIR = lambda s: asyncio.sleep(0)


async def main():
    await init_db()
    print("[1] chercher")
    r = await RG.chercher(naf="59.11A", departement="69")
    check("1a une seule cible : société active, diffusible", [x["siren"] for x in r] == ["428841472"], r)
    x = r[0] if r else {}
    check("1b forme : nom, naf, commune, code postal, effectif, création", x == {"siren": "428841472", "nom": "E MAGINEURS",
          "naf": "59.11A", "commune": "LYON", "code_postal": "69009", "tranche_effectif": "12", "creee_le": "2000-01-01"}, x)
    check("1c jamais les dirigeants ni l'adresse d'une personne", "dirigeants" not in str(r) and "DUPONT" not in str(r))
    u, p = APPELS[-1]
    check("1d paramètres : activité, département, actives seulement", u.endswith("/search") and p.get("activite_principale") == "59.11A"
          and p.get("departement") == "69" and p.get("etat_administratif") == "A", p)
    n = len(APPELS)
    await RG.chercher(naf="59.11A", departement="69")
    check("1e cache 24 h : pas de second appel", len(APPELS) == n)
    REPONSES.extend([(429, {}), (200, {"results": [SOC]})])
    r = await RG.chercher(naf="73.11Z", code_postal="75011")
    check("1f 429 : un nouvel essai réussi", len(r) == 1 and len(APPELS) == n + 2, len(APPELS) - n)
    REPONSES.extend([(429, {}), (429, {})])
    try:
        await RG.chercher(naf="58.21Z"); code = None
    except RG.RegistreIndisponible as e:
        code = str(e)
    check("1g 429 deux fois : refus dit", code and "réessayez" in code, code)
    for bad in ({"naf": "abc"}, {"code_postal": "7501"}, {"departement": "999"}, {}):
        try:
            await RG.chercher(**bad); leve = False
        except ValueError:
            leve = True
        check(f"1h critère fautif ou absent refusé {bad}", leve)

    print("[2] outil de l'agent")
    check("2a dans la boîte « prospects », lecture", "entreprises_registre" in B.BOITES["prospects"]["outils"]
          and ao.OUTILS["entreprises_registre"]["nature"] == "lecture" and B.verifier() == [])
    A = E.creer({"nom": "Prospection"})["id"]
    cid = (await st.creer("campagnes", A, "x"))["id"]
    r = await ao.executer("entreprises_registre", {"naf": "59.11A", "departement": "69"}, ao.Ctx(cid=cid, espace_id=A))
    check("2b rend des cibles, n'écrit aucune fiche", r["ok"] and r["donnees"]["cibles"][0]["nom"] == "E MAGINEURS"
          and P.lister(A) == [] and "site" in r["resume"], r)
    r = await ao.executer("entreprises_registre", {"naf": "zz"}, ao.Ctx(cid=cid, espace_id=A))
    check("2c critère fautif : refus dit", not r["ok"], r["resume"])


asyncio.run(main())
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
