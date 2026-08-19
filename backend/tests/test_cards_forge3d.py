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
import hashlib                                                    # noqa: E402
import io                                                         # noqa: E402
import json                                                       # noqa: E402
import zipfile                                                    # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

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
    # I1 : la normalisation doit garder [] tel quel : [] = aucun painter,
    # null = tous — un .length ici casserait le cumulatif C0
    assert "Array.isArray(o.only_z) ? o.only_z : null" in corps, \
        "la normalisation doit garder [] tel quel : [] = aucun painter, null = tous — un .length ici casserait le cumulatif C0"


def test_un_rendu_partiel_ne_pollue_ni_evenement_ni_bandeau():
    """M1 : un rendu PARTIEL (only_z et/ou paper:false, donc P9) n'ecrase pas
    LAST_ERRORS et n'emet pas core:render — quatre modules y accrochent leur
    peremption (checkStale), un export par couches ne doit pas les alerter."""
    src = CORE.read_text(encoding="utf-8")
    corps = src.split("async function renderRaw(")[1].split("\n  }")[0]
    assert "const partial" in corps
    assert "if (!partial)" in corps
    garde = corps.split("if (!partial) {")[1].split("\n    }")[0]
    assert "LAST_ERRORS" in garde and 'emitCore("core:render"' in garde, \
        "la garde doit ENGLOBER le bandeau ET l'evenement - un demi-revert la viderait"
    assert "cv.cfErrors = errors" in corps


def test_cf_layers_verifie_couche_par_couche_et_avoue_le_mode():
    """Chaque couche est prouvée : isolée si elle EMPILE (pixel strict), sinon
    empreinte (delta de cumulatifs, exact par construction). Le mode est un
    constat mesuré, jamais une intention."""
    src = CORE.read_text(encoding="utf-8")
    assert "function layers(" in src or "async function layers(" in src
    corps = src.split("function layers(")[1].split("\n  }")[0]
    for attendu in ("only_z", '"isolee"', '"empreinte"', "stack_ok",
                    "getImageData"):
        assert attendu in corps, f"il manque {attendu}"
    # la comparaison est STRICTE : aucun seuil, aucune tolerance
    assert "tolerance" not in corps and "seuil" not in corps
    # les rendus passent par la MEME file serialisee que tout le monde
    assert "RENDER_CHAIN" in corps
    # l'API est publique et les blobs de couche sont mintes (provenance)
    assert re.search(r"layers:\s*layers", src), "CF.layers non exposee"


def _couches_synthetiques(w=815, h=1110):
    """6 couches + composite qui empilent exactement, en PIL pur."""
    fond = Image.new("RGBA", (w, h), (250, 246, 238, 255))
    couches = {"fond-matiere": fond}
    for nom, boite, teinte in (
            ("illustration", (80, 120, w - 80, 620), (196, 148, 74, 255)),
            ("voile-matiere", (0, 0, w, h), (0, 0, 0, 0)),        # couche VIDE
            ("cadre", (30, 30, w - 30, h - 30), (60, 80, 140, 255)),
            ("typographie", (120, 700, w - 120, 780), (240, 236, 228, 255)),
            ("ornements", (40, 40, 140, 140), (220, 190, 90, 255))):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if teinte[3]:
            ImageDraw.Draw(im).rectangle(boite, fill=teinte)
        couches[nom] = im
    composite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for nom in ("fond-matiere", "illustration", "voile-matiere", "cadre",
                "typographie", "ornements"):
        composite = Image.alpha_composite(composite, couches[nom])
    return couches, composite


def _png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_l_export_de_couches_zippe_manifeste_et_contre_preuve():
    did = _deck("Couches")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front",
            "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]

    # le manifeste : schema, roles ordonnes, SHA-256 et boites RECALCULES ici
    assert b["schema"] == "card-3d/layers-manifest@1"
    assert [l["role"] for l in b["layers"]] == [
        "fond-matiere", "illustration", "voile-matiere", "cadre",
        "typographie", "ornements"]
    # contre-preuve backend : empilement PIL == composite, ecart mesure nul
    assert b["proof"]["backend"]["diff_px"] == 0
    assert b["proof"]["client"]["stack_ok"] is True
    # la couche vide est LIVREE et mesuree, pas devinee
    voile = [l for l in b["layers"] if l["role"] == "voile-matiere"][0]
    assert voile["coverage_pct"] == 0.0 and voile["bbox_px"] is None

    # le ZIP existe, ses entrees portent les 7 PNG + manifeste, les SHA collent
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    noms = sorted(z.namelist())
    assert "layers.json" in noms and "composite_front.png" in noms
    man = json.loads(z.read("layers.json").decode("utf-8"))
    for l in man["layers"]:
        h = hashlib.sha256(z.read(l["file"])).hexdigest()
        assert h == l["sha256"], l["file"]
    # chaque PNG livre porte son pHYs (300 DPI reels, patron P1/P8)
    px = z.read("illustration_front.png")
    assert b"pHYs" in px


def test_une_trame_fausse_fait_409_jamais_500():
    did = _deck("Trame fausse")
    im = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    files = [("layers", ("fond-matiere.png", _png(im), "image/png")),
             ("composite", ("composite.png", _png(im), "image/png"))]
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 409, r.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
