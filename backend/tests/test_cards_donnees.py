# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR B (plan-cartes T9, 04/10/2026) : les STATISTIQUES du jeu, colonne par colonne.

C'est le JEU qu'on décrit, pas le fichier : 3 Colosses à 7 d'attaque pèsent 3 (quantités appliquées), une ligne
écartée ne compte pas. Écarts au plan, mesurés :
  * pas de dépliage carte par carte (999 copies x 20 000 lignes = 20 millions d'éléments en mémoire) : la médiane
    et les classes se calculent sur des couples (valeur, poids) ;
  * une colonne d'ENTIERS à peu de valeurs (coût, attaque — la courbe d'un jeu) a UNE barre PAR VALEUR, pas 8
    classes aux bornes fractionnaires ;
  * DÉCISION DE L'UTILISATEUR (04/10) : un panneau à l'écran (pièce 04), pas seulement la route.
Témoin positif : la base (2014083f) n'a pas de /data/stats.
Run : cd backend ; & $PY tests/test_cards_donnees.py
"""
import asyncio
import os
import pathlib
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfstat_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "test-key"
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

RACINE = _ICI.parent.parent
BASE = "2014083f"

COLS = ["nom", "atk", "pv", "rarete", "qty", "art"]
ROWS = [["Colosse", "7", "5", "rare", "3", "a.png"],
        ["Oracle", "2", "3", "commune", "2", "b.png"],
        ["Rebut", "9", "1", "épique", "5", "c.png"],
        ["Écho", "1", "9", "commune", "4", "d.png"],
        ["Vase", "", "4", "commune", "1", "e.png"],
        ["Écartée", "100", "100", "mythique", "50", "f.png"]]


def test_temoin_la_base_n_a_pas_de_statistiques():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert d and b'@router.post("/stats")' not in d


def _st():
    from app.services.cards import data_stats as ST
    return ST


def _col(r, nom):
    return [c for c in r["colonnes"] if c["nom"] == nom][0]


def test_une_colonne_numerique_rend_min_max_moyenne_mediane_quantites_appliquees():
    r = _st().stats_table(COLS, ROWS, qty_col="qty", off=[5], skip=["art"])
    atk = _col(r, "atk")
    assert atk["genre"] == "numerique"
    assert atk["n"] == 14 and atk["vides"] == 1              # 3+2+5+4 ; la ligne vide pèse 1 ; l'écartée ne compte pas
    assert (atk["min"], atk["max"]) == (1.0, 9.0)
    assert round(atk["moyenne"], 6) == round((7 * 3 + 2 * 2 + 9 * 5 + 1 * 4) / 14, 6)
    assert atk["mediane"] == 7.0                             # 1×4, 2×2 | 7×3, 9×5 : la 7e et la 8e carte valent 7
    assert sum(b["n"] for b in atk["classes"]) == 14


def test_des_entiers_a_peu_de_valeurs_ont_une_barre_par_valeur():
    atk = _col(_st().stats_table(COLS, ROWS, qty_col="qty", off=[5]), "atk")
    assert atk["discret"] is True
    assert [(b["de"], b["n"]) for b in atk["classes"]] == [(1, 4), (2, 2), (3, 0), (4, 0), (5, 0), (6, 0), (7, 3), (8, 0), (9, 5)]


def test_mediane_paire_vides_ponderes_et_bornes_de_classe():
    ST = _st()
    m = _col(ST.stats_table(["x", "q"], [["1", "2"], ["3", "2"], ["", "4"]], qty_col="q"), "x")
    assert m["mediane"] == 2.0, m["mediane"]                 # 1,1,3,3 : la moyenne des deux du milieu
    assert m["vides"] == 4, m["vides"]                       # la ligne vide PÈSE 4 cartes, pas 1 ligne
    r = _col(ST.stats_table(["x"], [["0"], ["1"], ["10.5"]]), "x")
    # 1 / (10,5 / 8) = 0,76 : la première classe, pas la deuxième (un arrondi la déplacerait)
    assert [c["n"] for c in r["classes"]] == [2, 0, 0, 0, 0, 0, 0, 1], r["classes"]


def test_des_reels_ont_huit_classes_et_le_maximum_tombe_dans_la_derniere():
    x = _col(_st().stats_table(["x"], [["0"], ["10.5"], ["3,25"]]), "x")
    assert x["discret"] is False and len(x["classes"]) == 8
    assert sum(b["n"] for b in x["classes"]) == 3 and x["classes"][-1]["n"] == 1 and x["classes"][0]["n"] == 1


def test_une_colonne_categorielle_rend_ses_valeurs_triees_par_cartes():
    rar = _col(_st().stats_table(COLS, ROWS, qty_col="qty", off=[5]), "rarete")
    assert rar["genre"] == "categoriel" and rar["distinctes"] == 3
    assert [(v["valeur"], v["n"]) for v in rar["valeurs"]] == [("commune", 7), ("épique", 5), ("rare", 3)]


def test_la_quantite_et_les_colonnes_ecartees_ne_sont_pas_decrites():
    r = _st().stats_table(COLS, ROWS, qty_col="qty", off=[5], skip=["art"])
    assert [c["nom"] for c in r["colonnes"]] == ["nom", "atk", "pv", "rarete"]
    assert r["total_cartes"] == 15 and r["lignes"] == 5 and r["qty_col"] == "qty"


def test_une_colonne_a_moitie_numerique_est_categorielle_et_le_dit():
    x = _col(_st().stats_table(["x"], [["1"], ["2"], ["trois"], ["4"]]), "x")
    assert x["genre"] == "categoriel" and "75" in x["note"], x["note"]
    y = _col(_st().stats_table(["y"], [["1"]] * 19 + [["dix"]]), "y")      # 95 % : numérique, et l'exclusion est dite
    assert y["genre"] == "numerique" and "1 valeur(s) sur 20" in y["note"], y["note"]


def test_un_gros_jeu_ne_deplie_rien():
    import time
    rows = [[str(i % 13), "999"] for i in range(20000)]
    t0 = time.perf_counter()
    r = _st().stats_table(["cout", "qty"], rows, qty_col="qty")
    assert time.perf_counter() - t0 < 2.0
    c = _col(r, "cout")
    assert r["total_cartes"] == 20000 * 999 and c["n"] == 20000 * 999 and c["mediane"] == 6.0
    assert len(c["classes"]) == 13


def test_beaucoup_de_valeurs_sont_tronquees_et_c_est_dit():
    c = _col(_st().stats_table(["nom"], [[f"carte {i}"] for i in range(55)]), "nom")
    assert len(c["valeurs"]) == 40 and c["tronque"] == 15


def test_la_route_sert_les_stats_et_refuse_un_corps_mal_forme_sans_500():
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Stats"})
            did = r.json()["deck"]["id"]
            ok = await c.post(f"/api/cards/{did}/data/stats", json={"columns": COLS, "rows": ROWS, "qty_col": "qty",
                                                                    "off": [5], "skip": ["art"]})
            ko = await c.post(f"/api/cards/{did}/data/stats", json=[1, 2, 3])
            ko2 = await c.post(f"/api/cards/{did}/data/stats", json={"columns": "x"})
            return ok, ko, ko2
    ok, ko, ko2 = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    assert ok.json()["total_cartes"] == 15 and [c["nom"] for c in ok.json()["colonnes"]] == ["nom", "atk", "pv", "rarete"]
    assert (ko.status_code, ko2.status_code) == (400, 400)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
