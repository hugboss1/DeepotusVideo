# -*- coding: utf-8 -*-
"""Card Forge — tâche #86 PR B (plan-cartes T13, 04/10/2026) : TRADUCTION par LLM, validée carte par carte.

DÉCISIONS DE L'UTILISATEUR (04/10) :
  * moteur = le fournisseur des Réglages (le répartiteur de l'appli : Anthropic, OpenAI, Gemini — payant, coût
    annoncé avant, garde de dépense « cartes ») + Ollama LOCAL et gratuit quand il est configuré ;
  * validation carte par carte SEULEMENT : le serveur PROPOSE, il n'écrit rien ; aucun « tout accepter ».
Écarts au plan corrigés : `json` n'était pas importé dans data.py ; le plan sautait Anthropic, ignorait Ollama et
n'avait AUCUNE garde de dépense ; la route rejoint le recensement des routes payantes.
AUCUN APPEL RÉEL : le répartiteur, Ollama et la garde sont simulés.
Témoin positif : la base (0cd41ee6) n'a pas de traduction.
Run : cd backend ; & $PY tests/test_cards_traduction.py
"""
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cftrad_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN", "OLLAMA_MODEL"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "test-key"
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import pytest                                                    # noqa: E402
from fastapi import HTTPException                                # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

RACINE = _ICI.parent.parent
BASE = "0cd41ee6"

COLS = ["id", "titre_fr", "titre_en", "regles_fr", "regles_en", "qty", "note"]
ROWS = [["c1", "Veilleur", "Watcher", "Vol.", "", "2", "x"],
        ["c2", "Golem", "", "Bloque deux créatures.", "", "1", "y"],
        ["c3", "", "", "", "", "1", "z"],
        ["c4", "Écartée", "", "Rien.", "", "1", "w"]]
MAP = {"titre_fr": "title", "regles_fr": "rules", "qty": "qty"}
CORPS = {"columns": COLS, "rows": ROWS, "map": MAP, "off": [3], "source": "fr", "cible": "en", "moteur": "auto"}

APPELS, GARDES = [], []


def _faux_dispatch(prompt, system, max_tokens):
    APPELS.append(("auto", prompt, system, max_tokens))
    textes = json.loads(prompt[prompt.index("["):])
    return json.dumps([("EN:" + t) for t in textes], ensure_ascii=False), "anthropic"


def _faux_tirer(moteur, modele, prompt, systeme, max_tokens=4000, **k):
    APPELS.append(("ollama:" + modele, prompt, systeme, max_tokens))
    textes = json.loads(prompt[prompt.index("["):])
    return "```json\n" + json.dumps([("OL:" + t) for t in textes], ensure_ascii=False) + "\n```"


async def _faux_verifier(op, categorie="", ref=None, confirme=None):
    GARDES.append((op, categorie))
    if GARDES_REFUS:
        raise HTTPException(402, detail={"dz_plafond": True, "message": "Plafond mensuel atteint"})
    return {}

GARDES_REFUS = []


def _armer(cles=("ANTHROPIC_API_KEY",), ollama=""):
    from app.config import settings
    from app.services import summarizer as SZ, vector_illustration as VI, plafonds as PL
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        setattr(settings, k, "cle-test" if k in cles else "")
    settings.OLLAMA_MODEL = ollama
    SZ._chat_dispatch = _faux_dispatch
    VI.tirer = _faux_tirer
    PL.verifier = _faux_verifier
    APPELS.clear(); GARDES.clear(); GARDES_REFUS.clear()


def _post(chemin, corps):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Trad"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/{chemin}", json=corps)
    return asyncio.run(go())


def test_temoin_la_base_n_a_pas_de_traduction():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert d and b"/traduire" not in d


def test_le_devis_compte_les_cellules_sans_rien_appeler():
    _armer()
    r = _post("traduire/devis", CORPS)
    assert r.status_code == 200, r.text
    j = r.json()
    # titre de c2, regles de c1 et c2 ; c3 n'a pas de source ; c4 est écartée ; « note » n'est pas mappée
    assert j["n"] == 3 and j["lots"] == 1 and j["restants"] == 0, j
    assert j["fournisseur"] == "anthropic" and j["usd"] > 0 and j["payant"] is True
    assert j["dispo"] == {"auto": True, "ollama": False}
    assert APPELS == [] and GARDES == []


def test_la_traduction_propose_et_n_ecrit_rien():
    _armer()
    r = _post("traduire", CORPS)
    assert r.status_code == 200, r.text
    j = r.json()
    props = [(p["ligne"], p["colonne"], p["source"], p["proposition"]) for p in j["propositions"]]
    assert props == [(1, "regles_en", "Vol.", "EN:Vol."), (2, "titre_en", "Golem", "EN:Golem"),
                     (2, "regles_en", "Bloque deux créatures.", "EN:Bloque deux créatures.")], props
    assert j["fournisseur"] == "anthropic" and j["colonnes_a_creer"] == []
    # LA GARDE DE DÉPENSE AVANT L'APPEL, en LLM, catégorie « cartes »
    assert len(GARDES) == 1 and GARDES[0][0]["kind"] == "llm" and GARDES[0][1] == "cartes"
    assert len(APPELS) == 1 and "français" in APPELS[0][2] and "anglais" in APPELS[0][2]


def test_une_colonne_cible_existante_est_reprise_meme_autrement_ecrite():
    _armer()
    cols = ["titre_fr", "Titre-EN"]
    r = _post("traduire", dict(CORPS, columns=cols, rows=[["Golem", ""]], map={"titre_fr": "title"}, off=[]))
    j = r.json()
    assert j["colonnes_a_creer"] == [] and j["propositions"][0]["colonne"] == "Titre-EN", j
    # une entrée de mappage PÉRIMÉE (colonne absente de la table) n'ouvre pas sa base à la traduction
    r = _post("traduire", dict(CORPS, columns=["Titre-FR", "Titre-EN"], rows=[["Golem", ""]], map={"titre_fr": "title"}, off=[]))
    assert r.status_code == 200 and r.json()["propositions"] == [], r.text


def test_une_colonne_cible_absente_est_annoncee_a_creer():
    _armer()
    r = _post("traduire", dict(CORPS, cible="de"))
    j = r.json()
    assert sorted(j["colonnes_a_creer"]) == ["regles_de", "titre_de"], j["colonnes_a_creer"]
    assert {p["colonne"] for p in j["propositions"]} == {"titre_de", "regles_de"}


def test_sans_cle_503_sans_rien_lancer_et_ollama_est_local_gratuit():
    _armer(cles=())
    r = _post("traduire", CORPS)
    assert r.status_code == 503 and "Réglages" in r.text and APPELS == [] and GARDES == [], r.text
    r = _post("traduire", dict(CORPS, moteur="ollama"))                      # Ollama demandé mais pas configuré
    assert r.status_code == 503 and "OLLAMA_MODEL" in r.text and APPELS == [], r.text
    _armer(cles=(), ollama="llama3.1")
    d = _post("traduire/devis", dict(CORPS, moteur="ollama")).json()
    assert d["dispo"] == {"auto": False, "ollama": True} and d["usd"] == 0 and d["payant"] is False and d["fournisseur"] == "ollama"
    r = _post("traduire", dict(CORPS, moteur="ollama"))
    assert r.status_code == 200, r.text
    assert r.json()["propositions"][0]["proposition"] == "OL:Vol."          # bloc ```json``` toléré
    assert APPELS[0][0] == "ollama:llama3.1" and GARDES[0][0]["provider"] == "ollama"


def test_un_plafond_atteint_arrete_avant_l_appel():
    _armer()
    GARDES_REFUS.append(True)
    r = _post("traduire", CORPS)
    assert r.status_code == 402 and APPELS == [], r.text


def test_une_reponse_illisible_est_dite_502():
    _armer()
    from app.services import summarizer as SZ
    SZ._chat_dispatch = lambda p, s, m: ("je ne suis pas du JSON", "anthropic")
    r = _post("traduire", CORPS)
    assert r.status_code == 502 and "JSON" in r.text, r.text
    SZ._chat_dispatch = lambda p, s, m: ('["un seul"]', "anthropic")
    r = _post("traduire", CORPS)
    assert r.status_code == 502 and "3" in r.text and "1" in r.text, r.text
    SZ._chat_dispatch = lambda p, s, m: (None, "")
    r = _post("traduire", CORPS)
    assert r.status_code == 502 and "n'a rien rendu" in r.text, r.text


def test_les_lots_et_le_plafond_de_200():
    _armer()
    rows = [[f"c{i}", f"Nom {i}", "", "", "", "1", ""] for i in range(250)]
    r = _post("traduire", dict(CORPS, rows=rows, off=[]))
    j = r.json()
    assert len(j["propositions"]) == 200 and j["restants"] == 50 and len(APPELS) == 5, (len(j["propositions"]), j["restants"], len(APPELS))
    assert len(GARDES) == 1 and GARDES[0][0]["in_tok"] > 0


def test_corps_mal_forme_et_langues_invalides():
    _armer()
    assert _post("traduire", dict(CORPS, cible="fr")).status_code == 400            # même langue
    assert _post("traduire", dict(CORPS, cible="klingon")).status_code == 400
    assert _post("traduire", dict(CORPS, source="de")).status_code == 400            # aucune colonne source
    assert _post("traduire", dict(CORPS, moteur="xyz")).status_code == 400
    r = _post("traduire", dict(CORPS, rows=[r[:] for r in ROWS[2:3]], off=[]))
    assert r.status_code == 200 and r.json()["propositions"] == []


def test_la_route_est_recensee_payante_et_gardee():
    sys.path.insert(0, str(_ICI))
    import _recensement_payant as RP
    rec = RP.recenser()
    cle = ("data", "POST", "/traduire")
    assert cle in rec and rec[cle]["garde"] is True, rec.get(cle)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
