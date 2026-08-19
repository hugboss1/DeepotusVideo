# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Squelette de la pièce (phase 1).

Ce fichier verrouille, pour l'instant, ce que le squelette DOIT tenir avant
que la moindre logique d'export par couches ne s'écrive (§4 de
docs/superpowers/plans/2026-08-19-cardforge-phase1-couches.md, Task 1) :

  1. La pièce respecte la règle 1 du lab (1 JS + 1 CSS + 1 py + 1 test) et
     passe le lint mécanique — c'est LUI le juge, pas ce fichier.
  2. `GET /api/cards/{did}/forge3d/info` publie les six rôles de couches et
     leurs z, ceux de la Z_TABLE gelée du CORE.
  3. Le bloc miroir JS <-> py (marqueurs CF-FORGE3D-LAYERS-*) est identique
     champ à champ et dans l'ordre des deux côtés : une table recopiée à la
     main qui dérive est un mensonge.

Run : <python embarqué> backend/tests/test_cards_forge3d.py
      .\\scripts\\run-tests.ps1 -Filter cards_forge3d
"""
import asyncio
import os
import pathlib
import re
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                     # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = ROOT / "frontend" / "cardforge" / "js" / "mod-forge3d.js"


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=180.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck(nom: str = "Forge") -> str:
    r = _api("POST", "/api/cards/decks", json={"name": nom})
    assert r.status_code == 200, r.text
    return r.json()["deck"]["id"]


def test_la_piece_est_complete_et_passe_le_lint():
    """Règle 1 : 1 JS + 1 CSS + 1 py + 1 test. Le lint est le juge, pas nous."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "qa" / "lint_cardforge.py"),
         "--module", "forge3d"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_info_publie_les_roles_de_couches():
    did = _deck("Forge")
    info = _api("GET", f"/api/cards/{did}/forge3d/info").json()
    assert info["schema"] == "card-3d/layers-manifest@1"
    roles = [r["role"] for r in info["layer_roles"]]
    assert roles == ["fond-matiere", "illustration", "voile-matiere",
                     "cadre", "typographie", "ornements"]
    # les z de chaque rôle sont ceux de la table gelée du CORE
    par_role = {r["role"]: r["z"] for r in info["layer_roles"]}
    assert par_role["fond-matiere"] == [10] and par_role["illustration"] == [20]
    assert par_role["voile-matiere"] == [30] and par_role["cadre"] == [40]
    assert par_role["typographie"] == [60] and par_role["ornements"] == [70]
    # /info est scopée au deck comme toute route du domaine (règle §2.5) :
    # un id syntaxiquement invalide lève 400, un id valide mais absent 404.
    assert _api("GET", "/api/cards/nimportequoi/forge3d/info").status_code == 400
    assert _api("GET", "/api/cards/deck_00000000/forge3d/info").status_code == 404


def test_la_table_des_couches_est_identique_des_deux_cotes():
    """Bloc miroir JS <-> py : une table recopiée qui dérive est un mensonge."""
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-LAYERS-BEGIN")[1].split("CF-FORGE3D-LAYERS-END")[0]
    js_rows = re.findall(
        r'\{ role: "([a-z-]+)", z: \[([0-9, ]+)\], module: "([a-z]+)" \}', bloc)
    js_table = [{"role": r, "z": [int(x) for x in z.split(",")], "module": m}
                for r, z, m in js_rows]
    assert js_table == F9.LAYER_ROLES, (js_table, F9.LAYER_ROLES)
    # ...et les z sont un sous-ensemble EXACT de la table gelée du CORE
    core = (ROOT / "frontend" / "cardforge" / "js" / "core.js").read_text(encoding="utf-8")
    assert "Z_TABLE" in core
    tous = sorted(z for row in F9.LAYER_ROLES for z in row["z"])
    assert tous == [10, 20, 30, 40, 60, 70], tous


def test_le_core_connait_la_piece_forge3d():
    """Le registre du CORE est gelé : une pièce absente de sa table lève au
    premier CF.register dans un vrai navigateur — le lint et les routes ne
    l'attrapent pas (constat de la tâche 1).

    `ORDER` (core.js ~78-79) et `assertId()` (core.js ~226-230) dérivent tous
    deux de la table `MODULES` littérale : il n'y a qu'UNE table à tenir à
    jour, pas trois. On la cible directement, pas un commentaire voisin."""
    core = (ROOT / "frontend" / "cardforge" / "js" / "core.js").read_text(encoding="utf-8")
    m = re.search(r"const MODULES = \[([^\]]*)\];", core)
    assert m, "core.js : table MODULES introuvable (structure inattendue)"
    ids = re.findall(r'"([a-z0-9]+)"', m.group(1))
    assert "forge3d" in ids, (
        "forge3d absent de la table MODULES gelée du CORE — "
        "CF.register(\"forge3d\", ...) lèvera dans un vrai navigateur")
    # le rail est dans l'ordre de MODULES (core.js:1349-1350) : forge3d doit
    # occuper le rang 9, en dernier de la liste gelée.
    assert ids[-1] == "forge3d" and len(ids) == 9, ids


CORE = ROOT / "frontend" / "cardforge" / "js" / "core.js"


def test_le_moteur_sait_rendre_un_sous_ensemble_sur_toile_nue():
    """`renderRaw({only_z, paper:false})` : le rendu par couches est un filtre
    du MOTEUR UNIQUE, pas un second moteur qui divergerait (règle WYSIWYG)."""
    src = CORE.read_text(encoding="utf-8")
    corps = src.split("async function renderRaw(")[1].split("\n  }")[0]
    assert "only_z" in corps, "le filtre de painters manque"
    assert "o.paper" in corps, "l'option de support papier manque"
    # le filtre s'applique DANS la boucle des painters, apres le garde z=90
    boucle = corps.split("for (let k = 0; k < PAINTERS.length; k++) {")[1]
    assert "only" in boucle.split("ctx.save()")[0]
    # le papier reste le defaut : paper !== false
    assert 'o.paper !== false' in corps


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
