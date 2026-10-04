# -*- coding: utf-8 -*-
"""Card Forge — tâche #86 PR A (plan-cartes T12, 04/10/2026) : LOCALISATION, une colonne par langue.

Le rendu par langue est gratuit : un mappage différent, le même /build, les mêmes cartes (mêmes identifiants).
LE DÉFAUT DU PLAN, CORRIGÉ : il réécrivait un mappage « en bases » alors que la table garde un mappage RÉEL
(« nom_fr » -> titre) ; « nom_fr » n'étant pas une base, il passait pour NEUTRE et du français s'imprimait sur les
cartes anglaises — exactement ce que le plan disait interdire. Ici la langue active réécrit le mappage réel : une
colonne d'une langue est remplacée par sa sœur dans la langue choisie, ou RETIRÉE si elle n'existe pas — jamais
repliée sur une autre langue. La réécriture vit DANS /build : toutes les pièces (impression, édition) suivent.
Témoin positif : la base (f40144b6) n'a aucune langue.
Run : cd backend ; & $PY tests/test_cards_langues.py
"""
import asyncio
import os
import pathlib
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cflang_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN", "OLLAMA_URL"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "test-key"
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

RACINE = _ICI.parent.parent
BASE = "f40144b6"

COLS = ["id", "nom_fr", "nom_en", "texte_fr", "texte_en", "atk", "qty", "flavor_de"]
ROWS = [["c1", "Colosse", "Colossus", "Mêlée de lances", "Spear melee", "7", "2", "Speerkampf"],
        ["c2", "Oracle", "Oracle", "Voit la brume", "", "2", "1", ""],
        ["c3", "Écartée", "Discarded", "x", "x", "1", "9", ""]]
MAP = {"nom_fr": "titre", "texte_fr": "corps", "atk": "atk", "#n": "num"}


def _D():
    from app.services.cards import data as D
    return D


def test_temoin_la_base_n_a_aucune_langue():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert d and b"map_pour_langue" not in d and b"/langues" not in d


def test_les_langues_se_devinent_par_le_suffixe_des_colonnes():
    r = _D().langues_table(COLS)
    assert [(l["code"], l["label"]) for l in r["langues"]] == [("fr", "français"), ("en", "anglais"), ("de", "allemand")]
    assert r["langues"][0]["colonnes"] == {"nom": "nom_fr", "texte": "texte_fr"}
    assert r["neutres"] == ["id", "atk", "qty"]                  # sans suffixe : servent dans toutes les langues
    t = _D().langues_table(["Nom-EN", "nom.pt", "nom_xx", "titre_en_us", "en"])
    assert {l["code"] for l in t["langues"]} == {"en", "pt", "en-us"} and t["neutres"] == ["nom_xx", "en"], t


def test_le_mappage_reel_est_reecrit_dans_la_langue_et_jamais_replie():
    D = _D()
    assert D.map_pour_langue(COLS, MAP, "en") == {"nom_en": "titre", "texte_en": "corps", "atk": "atk", "#n": "num"}
    # allemand : seule « flavor » existe ; « nom » et « texte » n'y ont pas de colonne -> RETIRÉS, pas du français
    assert D.map_pour_langue(COLS, MAP, "de") == {"atk": "atk", "#n": "num"}
    assert D.map_pour_langue(COLS, MAP, "") == MAP                  # aucune langue : le mappage tel quel
    assert D.map_pour_langue(COLS, {"nom_en": "titre"}, "fr") == {"nom_fr": "titre"}   # dans l'autre sens aussi


def _post(chemin, corps):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Langues"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/{chemin}", json=corps)
    return asyncio.run(go())


def test_build_rend_le_meme_jeu_dans_chaque_langue():
    slots = [{"id": "titre"}, {"id": "corps"}, {"id": "atk"}, {"id": "num"}]
    corps = {"columns": COLS, "rows": ROWS, "map": MAP, "qty_col": "qty", "off": [2], "slots": slots}
    fr = _post("build", dict(corps, lang="fr")).json()["cards"]
    en = _post("build", dict(corps, lang="en")).json()["cards"]
    tel = _post("build", corps).json()["cards"]
    assert [c["id"] for c in fr] == [c["id"] for c in en] == [c["id"] for c in tel] and len(fr) == 3
    assert fr[0]["fields"]["titre"] == "Colosse" and en[0]["fields"]["titre"] == "Colossus"
    assert en[0]["fields"]["corps"] == "Spear melee" and en[0]["fields"]["atk"] == "7"
    assert tel[0]["fields"]["titre"] == "Colosse"
    de = _post("build", dict(corps, lang="de")).json()["cards"]
    assert de[0]["fields"].get("titre", "").replace("​", "") == "", de[0]["fields"]     # jamais « Colosse »
    r = _post("build", dict(corps, lang="klingon"))
    assert r.status_code == 400 and "klingon" in r.text, r.text


def test_les_cellules_manquantes_sont_dites_par_langue_en_cartes():
    r = _D().langues_report(COLS, ROWS, MAP, qty_col="qty", off=[2])
    par = {l["code"]: l for l in r["langues"]}
    assert par["fr"]["manquants"] == 0 and par["fr"]["cartes_incompletes"] == 0
    en = par["en"]
    assert (en["manquants"], en["cartes_incompletes"], en["lignes_incompletes"]) == (1, 1, 1), en   # texte_en de c2 (×1)
    assert en["details"][0] == {"ligne": 2, "cartes": 1, "colonnes": ["texte_en"]}
    de = par["de"]
    assert de["absentes"] == ["nom", "texte"] and de["cartes_incompletes"] == 3, de                 # tout le jeu
    assert en["map"] == {"nom_en": "titre", "texte_en": "corps", "atk": "atk", "#n": "num"}
    rows = [r[:] for r in ROWS]
    rows[1][6] = "3"                                   # la ligne incomplète vaut TROIS cartes
    en3 = [l for l in _D().langues_report(COLS, rows, MAP, qty_col="qty", off=[2])["langues"] if l["code"] == "en"][0]
    assert (en3["manquants"], en3["cartes_incompletes"], en3["lignes_incompletes"]) == (3, 3, 1), en3


def test_la_route_langues_repond_et_refuse_un_corps_mal_forme():
    ok = _post("langues", {"columns": COLS, "rows": ROWS, "map": MAP, "qty_col": "qty"})
    assert ok.status_code == 200 and [l["code"] for l in ok.json()["langues"]] == ["fr", "en", "de"], ok.text
    assert _post("langues", {"columns": COLS, "rows": ROWS, "map": "oui"}).status_code == 400
    sans = _post("langues", {"columns": ["nom", "atk"], "rows": [["a", "1"]], "map": {}})
    assert sans.json()["langues"] == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
