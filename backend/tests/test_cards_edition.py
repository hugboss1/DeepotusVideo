# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition » (tâche #84, plan-cartes T5-T7, 04/10/2026) : ce qui se livre AUTOUR de la carte.

Table virtuelle (Tabletop Simulator, Tabletopia) ; plus tard livret, mockup, fiche produit (T18-T19). La pièce ne
dessine RIEN : aucun z ne lui est alloué.
DÉCISION DE L'UTILISATEUR (04/10) : une ONZIÈME pièce au rail (et non deux boutons dans la pièce 07).
Les QUATRE listes qui doivent s'accorder (MODULE_IDS, core.js, le lint, l'assemblage) + index.html (data-host) :
un id présent d'un côté et absent de l'autre voit son sous-arbre JETÉ à chaque autosave — c'est arrivé à forge3d.
Témoin positif : la base (9765ed6d) n'a que dix pièces.

Run : cd backend ; & $PY tests/test_cards_edition.py
"""
import asyncio
import os
import pathlib
import re
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfedi_")
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
from app.services.cards import contract as CT                    # noqa: E402

RACINE = _ICI.parent.parent
FRONT = RACINE / "frontend" / "cardforge"
BASE = "9765ed6d"


def _lire(p):
    return p.read_bytes().decode("utf-8").replace("\r\n", "\n")


def test_temoin_la_base_n_a_que_dix_pieces():
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/contract.py"], capture_output=True, cwd=str(RACINE))
    assert r.returncode == 0 and b'"forge3d", "capture")' in r.stdout and b"edition" not in r.stdout


def test_la_piece_est_la_onzieme_dans_toutes_les_listes():
    assert CT.MODULE_IDS[-1] == "edition" and len(CT.MODULE_IDS) == 11, CT.MODULE_IDS
    js = _lire(FRONT / "js" / "core.js")
    mods = re.findall(r'"(\w+)"', js.split("const MODULES =")[1].split("]")[0])
    assert tuple(mods) == CT.MODULE_IDS, mods
    lint = _lire(RACINE / "scripts" / "qa" / "lint_cardforge.py")
    assert '"edition": set()' in lint, "Z_TABLE : la pièce ne dessine pas"
    assert tuple(re.findall(r'"(\w+)"', lint.split("\nMODULES = [")[1].split("]")[0])) == CT.MODULE_IDS
    init = _lire(RACINE / "backend" / "app" / "services" / "cards" / "__init__.py")
    k_ed, k_filet = init.find('prefix="/{did}/edition"'), init.find('@router.api_route("/{rest:path}"')
    assert 0 < init.find('prefix="/{did}/capture"') < k_ed < k_filet, "monté après capture, AVANT le filet"


def test_les_quatre_fichiers_de_la_piece_sont_la():
    for p in (FRONT / "js" / "mod-edition.js", FRONT / "css" / "mod-edition.css",
              RACINE / "backend/app/services/cards/edition.py", RACINE / "backend/tests/test_cards_edition.py"):
        assert p.is_file(), p


def test_la_coquille_est_montee_dans_la_page_avec_son_hote():
    html = _lire(FRONT / "index.html")
    assert 'href="css/mod-edition.css"' in html
    assert 'id="cf-panel-edition" data-mod="edition"' in html
    assert '<div class="cf-host cf-edition" data-host="edition"></div>' in html     # sinon init() n'a pas d'hôte
    assert '<b class="ph-n">11</b><h2>Édition</h2>' in html
    assert html.index("js/mod-edition.js") > html.index("js/mod-capture.js") > 0
    assert html.index('data-host="edition"') > html.index('data-host="capture"')


def test_le_module_ecran_s_enregistre_onzieme_sans_painter():
    js = _lire(FRONT / "js" / "mod-edition.js")
    assert '"use strict"' in js[:3000], "règle 11"
    assert "painters: []" in js and 'id: "edition"' in js and "order: 11" in js
    core = _lire(FRONT / "js" / "core.js")
    assert "edition: SVG_O" in core, "le rail a son pictogramme"


def test_la_piece_repond_ses_cibles():
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Édition"})
            did = r.json()["deck"]["id"]
            return (await c.get(f"/api/cards/{did}/edition/cibles"),
                    await c.get("/api/cards/deck_00000000/edition/cibles"),
                    await c.get("/api/cards/pas-un-did/edition/cibles"))
    r, r404, r400 = asyncio.run(go())
    assert r.status_code == 200, r.text
    assert [t["id"] for t in r.json()["cibles"]] == ["tts", "tabletopia"]
    assert all(t["note"] and t["verifie"] for t in r.json()["cibles"])
    assert (r404.status_code, r400.status_code) == (404, 400)


def test_le_sous_arbre_edition_survit_a_un_enregistrement():
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Survie"})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}", json={"edition": {"cible": "tabletopia"}})
            return (await c.get(f"/api/cards/{did}")).json()
    doc = asyncio.run(go())
    assert doc["deck"]["edition"]["cible"] == "tabletopia", doc["deck"].get("edition")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
