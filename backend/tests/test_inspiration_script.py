# -*- coding: utf-8 -*-
"""t514 (RV4, 26/11/2026) — banc de la fiche d'offre et du script sur recette (porte 1).

Sections :
  1. fiche d'offre : GET vide (incomplète) ; PUT bornée, appels hors liste écartés, chiffre sans source -> 400 ;
     PUT complète ; un autre espace ne la voit pas ; hors machine -> 403 ;
  2. script : sans recette -> 409 sans_recette ; sans offre -> 409 sans_offre ; devis gratuit ; accord bas -> 409 cout ;
     écriture (faux Claude) : briques, faits, contrôles, statut a_valider ; recette et offre ENCADRÉES, source jamais
     envoyée ; appel « commentaire » retiré tant que G11 n'existe pas (R6) ;
  3. porte 1 : un chiffre non sourcé bloque la validation (409 bloquant) ; réécriture à la main (PUT) -> contrôles
     rejoués, validation 200, statut valide ;
  4. normaliser_recette relève les mots par brique (RV2 -> RV4).
Run (depuis backend/) : & $PY tests/test_inspiration_script.py"""
import json, os, pathlib, shutil, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinss_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import inspiration as I                           # noqa: E402
from app.services import inspiration_recette as IR                  # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
SOURCE = "Tu paies chaque mois pour un outil que tu ouvres deux fois par semaine et personne ne te le dit jamais"
REPONSE = {"briques": [{"role": "accroche", "texte": "Tu paies encore chaque mois ?", "ecran": "chaque mois ?"},
                       {"role": "offre", "texte": "Deepotus se paie une fois : 45 €, contre 99 $ par mois.", "ecran": "45 €"},
                       {"role": "appel", "texte": "Le lien est dans la bio.", "ecran": "lien bio"}],
           "faits": ["45 €"]}
APPELS = []


class _Rep:
    status_code = 200
    text = ""

    def __init__(self, t): self._t = t

    def json(self): return {"content": [{"type": "text", "text": self._t}], "usage": {"input_tokens": 1, "output_tokens": 1}}


def faux_post(url, headers=None, json=None, timeout=None, verify=None):
    APPELS.append(json)
    import json as _j
    return _Rep(_j.dumps(REPONSE, ensure_ascii=False))


MT.httpx.post = faux_post


def reference(eid: str, avec_recette: bool = True) -> str:
    iid = uuid.uuid4().hex
    rec = {"id": iid, "espace_id": eid, "cree": I._maintenant(), "langue": "fr", "matiere": "video",
           "source": {"libelle": "Reel", "lien": "https://x.example/r"}, "texte_capte": SOURCE, "palette": [],
           "video": {"fiche": {"format": {"duree_s": 6.0}}, "planches": []}, "analyse": None, "brouillons": []}
    if avec_recette:
        rec["recette"] = {"rythme": {"mots_par_minute": 170}, "soustitres": {"lignes": 2},
                          "structure": [{"role": "accroche", "debut": 0, "fin": 2, "regle": "une question", "mots": 5},
                                        {"role": "offre", "debut": 2, "fin": 4, "regle": "le prix comparé", "mots": 11},
                                        {"role": "appel", "debut": 4, "fin": 6, "regle": "le lien", "mots": 6}]}
    I._ecrire(rec)
    return iid


def run():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import espaces
    with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        EA = espaces.creer({"nom": "Studio Offre"})["id"]
        EB = espaces.creer({"nom": "Autre Offre"})["id"]
        H, HB = {"X-Dz-Espace": EA}, {"X-Dz-Espace": EB}
        print("[1] fiche d'offre")
        r = client.get("/api/inspiration/offre", headers=H)
        check("1a vide au départ, incomplète", r.status_code == 200 and r.json()["complete"] is False and r.json()["offre"]["appels"] == ["lien"])
        r = dehors.put("/api/inspiration/offre", json={"produit": "x"})
        check("1b hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        r = client.put("/api/inspiration/offre", headers=H, json={"produit": "VideoGen", "chiffres": [{"valeur": "45 €"}]})
        check("1c chiffre sans source -> 400", r.status_code == 400 and "source" in r.text, r.text[:200])
        offre = {"produit": "Deepotus VideoGen " + "x" * 300, "pour_qui": "créateurs", "promesse": "payé une fois, à vie",
                 "preuves": ["mises à jour comprises", ""], "frein_leve": "remboursé 14 jours", "appels": ["lien", "commentaire", "pirater"],
                 "chiffres": [{"valeur": "45 €", "libelle": "prix de lancement", "source": "page d'achat"}]}
        r = client.put("/api/inspiration/offre", headers=H, json=offre)
        o = r.json().get("offre", {})
        check("1d PUT : complète, bornée, appel inconnu écarté, preuve vide retirée", r.status_code == 200 and r.json()["complete"]
              and len(o["produit"]) == 200 and o["appels"] == ["lien", "commentaire"] and o["preuves"] == ["mises à jour comprises"], o)
        check("1e un autre espace ne la voit pas", client.get("/api/inspiration/offre", headers=HB).json()["complete"] is False)
        print("[2] script")
        sans = reference(EA, avec_recette=False)
        r = client.get(f"/api/inspiration/{sans}/devis-script", headers=H)
        check("2a sans recette -> 409 sans_recette", r.status_code == 409 and r.json()["detail"]["code"] == "sans_recette", r.text[:200])
        iB = reference(EB)
        r = client.get(f"/api/inspiration/{iB}/devis-script", headers=HB)
        check("2b sans offre -> 409 sans_offre, message traduit", r.status_code == 409 and r.json()["detail"]["code"] == "sans_offre", r.text[:200])
        r = client.get(f"/api/inspiration/{iB}/devis-script", headers={**HB, "Accept-Language": "en"})
        check("2c message en anglais", "offer sheet" in r.text, r.text[:200])
        IID = reference(EA)
        r = client.get(f"/api/inspiration/{IID}/devis-script", headers=H)
        d = r.json()
        check("2d devis gratuit, disponible, aucun appel", r.status_code == 200 and d["disponible"] and d["usd"] > 0 and not APPELS, d)
        r = client.post(f"/api/inspiration/{IID}/script", headers=H, json={"max_usd": 0.00001})
        check("2e accord trop bas -> 409 cout", r.status_code == 409 and r.json()["detail"]["code"] == "cout" and not APPELS, r.text[:200])
        r = dehors.post(f"/api/inspiration/{IID}/script", json={"max_usd": 1})
        check("2f hors machine -> 401 ou 403", r.status_code in (401, 403))
        r = client.post(f"/api/inspiration/{IID}/script", headers=H, json={"max_usd": d["usd"]})
        s = r.json()
        check("2g 200 : trois briques, faits, statut a_valider", r.status_code == 200 and len(s["briques"]) == 3
              and s["faits"] == ["45 €"] and s["statut"] == "a_valider", r.text[:300])
        envoye = json.dumps(APPELS[-1], ensure_ascii=False)
        check("2h offre et recette ENCADRÉES", "<<<PREUVE offre" in envoye and "<<<PREUVE recette" in envoye)
        check("2i la source n'est jamais envoyée", "personne ne te le dit" not in envoye)
        check("2j R6 : « commentaire » retiré des appels permis tant que G11 manque", s["appels_permis"] == ["lien"]
              and '"commentaire"' not in envoye.split("appels_autorises")[1][:60], s["appels_permis"])
        c = s["controle"]["controles"]
        check("2k contrôles : 99 $ non sourcé -> vérité KO et bloquant", not c["verite"]["ok"] and s["controle"]["bloquant"], c["verite"])
        check("2l contrôles : appel, accroche, distance ok", c["appel"]["ok"] and c["accroche"]["ok"] and c["distance"]["ok"], c)
        print("[3] porte 1")
        r = client.post(f"/api/inspiration/{IID}/script/valider", headers=H)
        check("3a validation refusée tant qu'un contrôle bloquant échoue (409 bloquant)", r.status_code == 409
              and r.json()["detail"]["code"] == "bloquant", r.text[:200])
        neuves = [dict(b) for b in s["briques"]]
        neuves[1] = {"role": "offre", "texte": "Deepotus se paie une seule fois, 45 €, et reste à toi.", "ecran": "45 €"}
        r = client.put(f"/api/inspiration/{IID}/script", headers=H, json={"briques": neuves})
        check("3b réécriture à la main : contrôles rejoués, plus bloquant", r.status_code == 200 and not r.json()["controle"]["bloquant"]
              and r.json()["statut"] == "a_valider", r.text[:300])
        r = client.post(f"/api/inspiration/{IID}/script/valider", headers=H)
        check("3c PORTE 1 : validé par le geste de l'utilisateur", r.status_code == 200 and r.json()["statut"] == "valide" and r.json()["valide_le"])
        r = client.put(f"/api/inspiration/{IID}/script", headers=H, json={"briques": neuves})
        check("3d toute modification repasse « à valider »", r.json()["statut"] == "a_valider" and "valide_le" not in r.json())
        r = client.post(f"/api/inspiration/{sans}/script/valider", headers=H)
        check("3e sans script -> 400 sans_script", r.status_code == 400, r.status_code)
    print("[4] mots par brique")
    rec = {"video": {"fiche": {"format": {"duree_s": 6.0}}}, "source": {}}
    mots = [{"start": t} for t in (0.1, 0.5, 1.9, 2.0, 3.5, 5.9)]
    r = IR.normaliser_recette({"structure": [{"role": "accroche", "debut": 0, "fin": 2}, {"role": "appel", "debut": 2, "fin": 6}]}, rec, mots)
    check("4a mots relevés par brique (3 puis 3)", [b["mots"] for b in r["structure"]] == [3, 3], r["structure"])


def test_inspiration_script():
    run()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        run()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
