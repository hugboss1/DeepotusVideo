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
import math                                                       # noqa: E402
import struct                                                     # noqa: E402
import zipfile                                                    # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = ROOT / "frontend" / "cardforge" / "js" / "mod-forge3d.js"
CSS = ROOT / "frontend" / "cardforge" / "css" / "mod-forge3d.css"


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=180.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck(nom: str = "Forge", fmt: str | None = None) -> str:
    corps: dict = {"name": nom}
    if fmt:
        corps["format"] = {"fmt": fmt}
    r = _api("POST", "/api/cards/decks", json=corps)
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
    # le vocabulaire du graphe (P2a) et ses bornes : publiés ici pour que
    # l'écran ne recopie JAMAIS une borne en dur.
    from app.services.cards import forge3d as F9
    assert info["node_kinds"] == F9.NODE_KINDS
    lim = info["graph_limits"]
    assert lim["plane_depth_mm"] == list(F9.PLANE_DEPTH_MM)
    assert lim["relief_depth_mm_max"] == F9.RELIEF_DEPTH_MM_MAX
    assert lim["relief_base_mm"] == list(F9.RELIEF_BASE_MM)
    assert lim["relief_grid"] == list(F9.RELIEF_GRID)
    assert lim["relief_grid_default"] == F9.RELIEF_GRID_DEFAULT
    # I3 — LE VOCABULAIRE D'EXPORT EST SERVI, PAS RECOPIÉ (2c Task 4). C'est
    # le contrat sur lequel la Task 5 bâtit son sélecteur de format : sans ce
    # pin, publier la liste puis la laisser tomber ferait recopier quatre
    # littéraux à l'écran — la faute des tables miroir, à la porte du client.
    assert lim["export_formats"] == list(F9.EXPORT_FORMATS)
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


def _couches_papier_none(w=815, h=1110):
    """C2 : meme jeu que `_couches_synthetiques`, mais la couche
    fond-matiere est ENTIEREMENT TRANSPARENTE — le papier de la piece
    Matieres mis a « none ». Le composite REEL (cote navigateur) ne redevient
    blanc que parce que le MOTEUR peint PAPER (core.js) avant les couches ;
    aucune couche ne porte ce blanc. Discrimine la base d'empilement de la
    contre-preuve : une base transparente cote backend divergerait en masse
    la ou aucune couche ne couvre, une base blanche (paper) ne diverge pas."""
    couches, _ = _couches_synthetiques(w, h)
    couches = dict(couches)
    couches["fond-matiere"] = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    composite = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    for nom in ("fond-matiere", "illustration", "voile-matiere", "cadre",
                "typographie", "ornements"):
        composite = Image.alpha_composite(composite, couches[nom])
    return couches, composite


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
    # C1 : identite de carte — par defaut card="0", donc c01
    assert b["card"] == {"index": 0, "label": "c01"}
    # C2 : la base papier REELLEMENT peinte par le moteur voyage dans le
    # manifeste (defaut du formulaire : blanc, PAPER de core.js)
    assert b["paper"] == "#ffffff"
    # contre-preuve backend : empilement PIL == composite, ecart mesure nul
    assert b["proof"]["backend"]["diff_px"] == 0
    assert b["proof"]["client"]["stack_ok"] is True
    # la couche vide est LIVREE et mesuree, pas devinee
    voile = [l for l in b["layers"] if l["role"] == "voile-matiere"][0]
    assert voile["coverage_pct"] == 0.0 and voile["bbox_px"] is None
    assert voile["bbox_mm"] is None    # boite vide : None des deux cotes

    # reliquat de revue phase 1 : le manifeste porte le format du deck et la
    # densite pHYs REELLEMENT ecrite (memes octets que ceux relus plus bas),
    # et chaque couche non vide porte sa boite convertie en mm a cote de sa
    # boite en pixels — deck par defaut : poker_eu, 300 DPI.
    assert b["format"] == "poker_eu"
    assert b["phys_ppm"] == 11811
    # I2 (revue) : la trame physique totale, miroir de canvas_px — poker_eu
    # a 300 DPI : 63 x 88 mm de trim + 3 mm de fond perdu des DEUX cotes.
    assert b["canvas_mm"] == [69.0, 94.0]
    cadre = [l for l in b["layers"] if l["role"] == "cadre"][0]
    assert cadre["bbox_px"] is not None and cadre["bbox_mm"] is not None
    # bbox_mm = bbox_px * dimensions physiques TOTALES / canvas_px — poker_eu
    # a 300 DPI : canvas = 815 x 1110 px pour 69 x 94 mm (trim + fond perdu
    # des deux cotes), donc c'est bien la trame w x h qui divise, pas trim_mm
    # seul (qui sous-evaluerait toute couche qui deborde dans le fond perdu).
    # ORIGINE (I2, revue) : coin de TOILE (fond perdu compris), comme
    # bbox_px — PAS le coin de COUPE de P2/P3 (frame.py:164) ; soustraire
    # bleed_mm pour la convention slots.
    bx = cadre["bbox_px"]
    attendu_mm = [round(bx[0] * 69.0 / 815, 2), round(bx[1] * 94.0 / 1110, 2),
                  round(bx[2] * 69.0 / 815, 2), round(bx[3] * 94.0 / 1110, 2)]
    assert cadre["bbox_mm"] == attendu_mm

    # le ZIP existe, ses entrees portent les 7 PNG + manifeste, les SHA collent
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    # patron P8 : Content-Disposition + Cache-Control sur le livrable
    assert rz.headers.get("content-disposition", "").startswith("attachment")
    assert rz.headers.get("cache-control") == "no-store"
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    noms = sorted(z.namelist())
    assert "layers.json" in noms and "composite_c01_front.png" in noms
    man = json.loads(z.read("layers.json").decode("utf-8"))
    for l in man["layers"]:
        h = hashlib.sha256(z.read(l["file"])).hexdigest()
        assert h == l["sha256"], l["file"]
    # chaque PNG livre porte son pHYs, et la VALEUR relue dans les octets
    # est celle de P1 - pas seulement sa presence (patron P1/P8, la deck
    # par defaut est a 300 DPI). Parite : copie locale == 11811 == pHYs reel.
    from app.services.cards import forge3d as F9
    assert F9._dpi_to_ppm(300) == 11811
    px = z.read("illustration_c01_front.png")
    i = px.find(b"pHYs")
    assert i >= 0, "pHYs absent"
    ppm_x, ppm_y, unite = struct.unpack(">IIB", px[i + 4:i + 13])
    assert (ppm_x, ppm_y, unite) == (F9._dpi_to_ppm(300), F9._dpi_to_ppm(300), 1) \
        == (11811, 11811, 1)


def test_deux_cartes_ne_s_ecrasent_pas():
    """C1 : aujourd'hui, exporter la carte B ecrase les fichiers de la carte
    A (sorties nommees par deck+side seulement). Deux exports successifs,
    carte 0 puis carte 1 : les fichiers de c01 doivent EXISTER ENCORE apres
    l'export de c02, et chaque manifeste doit porter son propre index."""
    did = _deck("Deux cartes")
    couches, composite = _couches_synthetiques()

    def _envoie(idx):
        files = [("layers", (f"{nom}.png", _png(im), "image/png"))
                 for nom, im in couches.items()]
        files.append(("composite", ("composite.png", _png(composite), "image/png")))
        data = {"side": "front", "card": str(idx),
                "modes": json.dumps({n: "isolee" for n in couches}),
                "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
        r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
        assert r.status_code == 200, r.text
        return r.json()["layers"]

    man0 = _envoie(0)
    assert man0["card"] == {"index": 0, "label": "c01"}
    zip0 = man0["zip"]["name"]
    assert zip0 == "couches_c01_front.zip"

    man1 = _envoie(1)
    assert man1["card"] == {"index": 1, "label": "c02"}
    zip1 = man1["zip"]["name"]
    assert zip1 == "couches_c02_front.zip"
    assert zip1 != zip0

    # les fichiers de c01 existent ENCORE apres l'export de c02 — plus
    # d'ecrasement croise entre cartes du meme deck.
    rz0 = _api("GET", f"/api/cards/{did}/forge3d/file/{zip0}")
    assert rz0.status_code == 200
    z0 = zipfile.ZipFile(io.BytesIO(rz0.content))
    assert "composite_c01_front.png" in z0.namelist()
    rz1 = _api("GET", f"/api/cards/{did}/forge3d/file/{zip1}")
    assert rz1.status_code == 200
    z1 = zipfile.ZipFile(io.BytesIO(rz1.content))
    assert "composite_c02_front.png" in z1.namelist()


def test_card_non_numerique_ou_negatif_retombe_sur_zero_jamais_500():
    """C1 : garde numerique LOCALE sur `card` — un formulaire qui envoie
    « abc » (ou un index negatif) ne doit jamais faire 500, seulement
    retomber sur la carte 0 (meme patron que `_num` pour diff_px)."""
    did = _deck("Carte non numerique")
    couches, composite = _couches_synthetiques()

    def _envoie(card_raw):
        files = [("layers", (f"{nom}.png", _png(im), "image/png"))
                 for nom, im in couches.items()]
        files.append(("composite", ("composite.png", _png(composite), "image/png")))
        data = {"side": "front", "card": card_raw,
                "modes": json.dumps({n: "isolee" for n in couches}),
                "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
        return _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)

    r1 = _envoie("abc")
    assert r1.status_code == 200, r1.text
    assert r1.json()["layers"]["card"] == {"index": 0, "label": "c01"}
    r2 = _envoie("-5")
    assert r2.status_code == 200, r2.text
    assert r2.json()["layers"]["card"] == {"index": 0, "label": "c01"}


def test_papier_none_la_contre_preuve_empile_sur_la_base_papier():
    """C2 : la preuve client empile sur PAPER (#ffffff, le fond que peint le
    moteur) ; sans ce correctif, la contre-preuve backend empilait sur
    TRANSPARENT — le ZIP seul ne reproduisait pas le composite des que le
    papier de la piece Matieres passe a « none ». Fond-matiere ENTIEREMENT
    transparent, composite construit sur base blanche (comme le moteur) :
    la contre-preuve doit rendre diff_px == 0."""
    did = _deck("Papier none")
    couches, composite = _couches_papier_none()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "paper": "#ffffff",
            "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]
    assert b["proof"]["backend"]["diff_px"] == 0, (
        "la contre-preuve doit empiler sur la base papier, pas sur transparent")
    assert b["paper"] == "#ffffff"


def test_papier_invalide_retombe_sur_blanc_jamais_500():
    """C2 : validation hex STRICTE (`^#[0-9a-fA-F]{6}$`) — toute entree qui
    n'est pas exactement de cette forme retombe sur #ffffff, jamais une
    exception (meme discipline que la garde de `card`, I3, `_num`)."""
    did = _deck("Papier invalide")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "paper": "rouge",
            "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    assert r.json()["layers"]["paper"] == "#ffffff"


def test_chaque_png_porte_srgb_gama_et_chrm():
    """C3 : `_stamp_phys` n'ecrivait que pHYs - « la moitie d'un fichier de
    prepresse » (spec §4.3). Les couches sont des rendus d'ecran (sRGB) :
    intention perceptuelle, gamma 1/2,2 x 100000, primaires + point blanc
    sRGB — les memes octets EXACTS que P1 (face.py:SRGB_INTENT_PERCEPTUAL /
    SRGB_GAMA / SRGB_CHRM), relus dans le fichier livre, pas seulement leur
    presence. Ordre des chunks : IHDR . sRGB . gAMA . cHRM . pHYs (patron P1,
    face.py:png_finalize)."""
    did = _deck("Espace de couleur")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    px = z.read("illustration_c01_front.png")

    i_srgb = px.find(b"sRGB")
    assert i_srgb >= 0, "sRGB absent"
    (intent,) = struct.unpack(">B", px[i_srgb + 4:i_srgb + 5])
    assert intent == 0, "intention de rendu : 0 = perceptuel (P1)"

    i_gama = px.find(b"gAMA")
    assert i_gama >= 0, "gAMA absent"
    (gama,) = struct.unpack(">I", px[i_gama + 4:i_gama + 8])
    assert gama == 45455, "1/2,2 x 100000, valeur libpng (P1)"

    i_chrm = px.find(b"cHRM")
    assert i_chrm >= 0, "cHRM absent"
    chrm = struct.unpack(">8I", px[i_chrm + 4:i_chrm + 36])
    assert chrm == (31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000), (
        "primaires + point blanc sRGB, memes octets que P1")

    # l'ordre des chunks est celui de la spec / P1 : IHDR . sRGB . gAMA .
    # cHRM . pHYs — tous APRES IHDR, avant le premier IDAT.
    i_phys = px.find(b"pHYs")
    assert i_phys >= 0, "pHYs absent"
    assert i_srgb < i_gama < i_chrm < i_phys


def test_une_trame_fausse_fait_409_jamais_500():
    did = _deck("Trame fausse")
    im = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    files = [("layers", ("fond-matiere.png", _png(im), "image/png")),
             ("composite", ("composite.png", _png(im), "image/png"))]
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 409, r.text


def test_un_png_illisible_fait_400_jamais_500():
    """Spec 2.5 : un corps mal forme fait 400, JAMAIS 500. Un octet qui
    n'EST pas un PNG (ni une trame de la bonne taille, ni autre chose de
    decodable) doit lever avant meme d'atteindre le controle de taille."""
    did = _deck("PNG illisible")
    bon = _png(Image.new("RGBA", (815, 1110), (10, 20, 30, 255)))
    # la couche est du bruit, jamais un PNG
    r1 = _api("POST", f"/api/cards/{did}/forge3d/layers",
              files=[("layers", ("fond-matiere.png", b"pas un png", "image/png")),
                     ("composite", ("composite.png", bon, "image/png"))],
              data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r1.status_code == 400, r1.text
    # le composite est du bruit, la couche est valide
    r2 = _api("POST", f"/api/cards/{did}/forge3d/layers",
              files=[("layers", ("fond-matiere.png", bon, "image/png")),
                     ("composite", ("composite.png", b"pas un png", "image/png"))],
              data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r2.status_code == 400, r2.text


def test_modes_ou_preuve_malformes_sont_repares_jamais_500():
    """C1 : `modes`/`client_proof` en JSON VALIDE mais pas un objet (liste,
    nombre, chaine) faisait lever AttributeError/TypeError plus loin dans la
    route - 500 non attrape, reproduit en revue (scratchpad/repro_500.py).
    Repare en {} / valeur numerique par defaut, jamais une erreur serveur."""
    did = _deck("Formes malformees")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "modes": "[]",
            "client_proof": json.dumps({"diff_px": "abc"})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]
    # diff_px non numerique -> garde numerique -> 0, pas une exception
    assert b["proof"]["client"]["diff_px"] == 0
    # modes="[]" n'est pas un objet -> repare en {} -> mode par defaut partout
    assert all(l["mode"] == "isolee" for l in b["layers"])


def test_un_png_a_queue_parasite_est_estampille_correctement():
    """C2 : un PNG valide + des octets APRES IEND (navigateurs et outils en
    ecrivent) est accepte par PIL mais faisait planter `struct.unpack` dans
    `_stamp_phys` - 500 non attrape, reproduit en revue. La boucle bornee
    doit s'arreter proprement et estampiller quand meme le bon pHYs."""
    did = _deck("Queue parasite")
    couches, composite = _couches_synthetiques()
    files = []
    for nom, im in couches.items():
        raw = _png(im)
        if nom == "fond-matiere":
            raw = raw + b"xy"          # queue parasite apres IEND
        files.append(("layers", (f"{nom}.png", raw, "image/png")))
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    px = z.read("fond-matiere_c01_front.png")
    i = px.find(b"pHYs")
    assert i >= 0, "pHYs absent"
    ppm_x, ppm_y, unite = struct.unpack(">IIB", px[i + 4:i + 13])
    assert (ppm_x, ppm_y, unite) == (11811, 11811, 1)


def test_get_file_avec_did_invalide_fait_400_jamais_500():
    """C3 : `deck_dir` leve un ValueError sur un `did` syntaxiquement
    invalide - 500 non attrape, reproduit en revue. Meme garde que /info."""
    r = _api("GET", "/api/cards/nimportequoi/forge3d/file/x.zip")
    assert r.status_code == 400, r.text
    # syntaxiquement valide mais aucun deck derriere -> 404, pas 500 non plus
    r2 = _api("GET", "/api/cards/deck_00000000/forge3d/file/x.zip")
    assert r2.status_code == 404, r2.text


def test_plus_de_douze_fichiers_fait_400():
    """I2 : plafond de compte AVANT tout decodage - 13 couches, meme toutes
    valides, sont refusees d'emblee."""
    did = _deck("Trop de couches")
    raw = _png(Image.new("RGBA", (815, 1110), (1, 2, 3, 255)))
    files = [("layers", (f"c{i}.png", raw, "image/png")) for i in range(13)]
    files.append(("composite", ("composite.png", raw, "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 400, r.text


def test_un_fichier_trop_lourd_fait_413(monkeypatch):
    """I2 : borne de poids par fichier. La constante de production (64 Mo)
    n'est pas testable a taille reelle ; on l'abaisse pour ce test (idiome
    pytest monkeypatch), la constante nominale reste en vigueur ailleurs."""
    from app.services.cards import forge3d as F9
    monkeypatch.setattr(F9, "MAX_LAYER_BYTES", 200)
    did = _deck("Trop lourd")
    raw = _png(Image.new("RGBA", (815, 1110), (10, 20, 30, 255)))
    assert len(raw) > 200, "le PNG de test doit depasser la borne abaissee"
    files = [("layers", ("fond-matiere.png", raw, "image/png")),
             ("composite", ("composite.png", raw, "image/png"))]
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 413, r.text


def test_mode_hors_vocabulaire_ferme_fait_400():
    """I3 : le seul producteur de `modes` est core.js, dont le vocabulaire
    est {isolee, empreinte}. Un autre mot est un bug a reveler, pas a
    archiver dans le manifeste."""
    did = _deck("Mode invalide")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front", "modes": json.dumps({"fond-matiere": "xyz"}),
            "client_proof": "{}"}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 400, r.text


def test_role_inconnu_ou_duplique_fait_400_nomme():
    """M4 : un role hors table ou envoye deux fois est un bug a reveler
    (coherent avec I3) - jamais silencieusement ignore ou ecrase."""
    did = _deck("Role invalide")
    raw = _png(Image.new("RGBA", (815, 1110), (1, 2, 3, 255)))
    r1 = _api("POST", f"/api/cards/{did}/forge3d/layers",
              files=[("layers", ("pas-un-role.png", raw, "image/png")),
                     ("composite", ("composite.png", raw, "image/png"))],
              data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r1.status_code == 400, r1.text
    r2 = _api("POST", f"/api/cards/{did}/forge3d/layers",
              files=[("layers", ("fond-matiere.png", raw, "image/png")),
                     ("layers", ("fond-matiere.png", raw, "image/png")),
                     ("composite", ("composite.png", raw, "image/png"))],
              data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r2.status_code == 400, r2.text


def test_jpeg_ne_traverse_pas_la_contre_preuve():
    """M3 : `_ouvre` exige `im.format == "PNG"` - un JPEG ne doit pas
    atteindre la contre-preuve d'empilement."""
    did = _deck("JPEG refuse")
    buf = io.BytesIO()
    Image.new("RGB", (815, 1110), (10, 20, 30)).save(buf, "JPEG")
    jpg = buf.getvalue()
    png = _png(Image.new("RGBA", (815, 1110), (1, 2, 3, 255)))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers",
             files=[("layers", ("fond-matiere.png", jpg, "image/png")),
                    ("composite", ("composite.png", png, "image/png"))],
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 400, r.text


def test_l_ecran_prouve_avant_de_televerser_et_montre_le_bordereau():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    corps = rendu.split("async function exportLayers(")[1].split("\n  }")[0]
    # les DEUX faces partent, avec la preuve client par face
    assert 'CF.layers' in corps and '"front"' in corps and '"back"' in corps
    assert "stack_ok" in corps
    # l'echec de preuve NOMME la couche et n'envoie RIEN
    assert "return" in corps.split("stack_ok")[1].split("FormData")[0]
    # provenance : les blobs passent par CF.layerBlob (mintes)
    assert "CF.layerBlob" in corps
    # l'identite de carte et la base papier partent bel et bien avec chaque
    # envoi — des defauts backend (card="0", paper="#ffffff") rendraient
    # leur suppression invisible aux tests d'integration (200 quand meme) :
    # ce test cible litteralement l'appel, pas seulement son effet observe.
    assert 'fd.append("card"' in corps
    assert 'fd.append("paper"' in corps
    # le bordereau est peint depuis la REPONSE (mesure), pas depuis l'intention
    assert "cf-forge3d-slip" in rendu
    assert "weight" in rendu or "Kio" in rendu


def test_le_vocabulaire_gagne_export_des_deux_cotes():
    """Le miroir CF-FORGE3D-NODES s'étend une dernière fois (2c Task 4) : le
    kind `export` — un VRAI nœud du graphe, pas un bouton d'écran. Les kinds
    2b (mesh3d, material, transform) restent épinglés ici : l'assert d'ordre
    de la 2b est REMPLACÉ par celui-ci, jamais doublé (deux listes d'ordre
    dériveraient, et l'une des deux seule dirait vrai)."""
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-NODES-BEGIN")[1].split("CF-FORGE3D-NODES-END")[0]
    js_rows = re.findall(r'\{ kind: "([a-z0-9]+)", params: \[([^\]]*)\] \}', bloc)
    js_table = [{"kind": k, "params": [p.strip().strip('"') for p in ps.split(",") if p.strip()]}
                for k, ps in js_rows]
    assert js_table == F9.NODE_KINDS, (js_table, F9.NODE_KINDS)
    assert [r["kind"] for r in F9.NODE_KINDS] == [
        "layer", "plane", "relief", "mesh3d", "material", "transform",
        "assemble", "artifact", "export"]
    # le format d'un export est un vocabulaire FERMÉ (comme LAYER_MODES) :
    # publié par /info avec le reste, jamais recopié à l'écran.
    assert F9.EXPORT_FORMATS == ("glb", "stl", "metadata", "preview")


def test_clean_graph_borne_le_noeud_export():
    """Le nœud `export` traverse le nettoyage comme les autres : son format
    est ramené dans le vocabulaire, et le RÉSOLVEUR l'ignore SANS l'avouer —
    ce sont des points de téléchargement, pas des éléments ; le bordereau
    `artifact@1` reste ENTIER (il ne nomme que ce qui a été PERDU)."""
    from app.services.cards import forge3d as F9
    g = {"nodes": [{"id": "e1", "kind": "export", "format": "stl"},
                   {"id": "e2", "kind": "export", "format": "warp"},
                   {"id": "e3", "kind": "export", "format": ["glb"]}],
         "edges": []}
    out = F9.clean_graph(g)
    n = {x["id"]: x for x in out["nodes"]}
    assert n["e1"]["format"] == "stl"
    assert n["e2"]["format"] == "glb"      # défaut sur format inconnu
    # même garde que partout ailleurs dans cette fonction : un type non
    # hachable (une liste) répare, il ne lève pas — jamais 500 (doctrine 2.5).
    assert n["e3"]["format"] == "glb"
    # ── LE BORDEREAU RESTE ENTIER ────────────────────────────────────────
    g2 = {"nodes": [
        {"id": "s", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "t", "kind": "plane", "depth_mm": 0.2},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte"},
        {"id": "ex", "kind": "export", "format": "stl"},
        {"id": "ex2", "kind": "export", "format": "metadata"}],
        "edges": [{"from": "s", "to": "t"}, {"from": "t", "to": "asm"},
                  {"from": "asm", "to": "art"}, {"from": "art", "to": "ex"},
                  {"from": "art", "to": "ex2"}]}
    cands, ignores = F9._resolve_graph_elements(F9.clean_graph(g2))
    assert [c["proc"]["id"] for c in cands] == ["t"]
    # AUCUNE entrée `ignored` : ni pour les deux nœuds export, ni pour leurs
    # arêtes depuis l'artefact. Un export n'éteint rien.
    assert ignores == [], ignores


def test_clean_graph_borne_les_nouveaux_noeuds():
    from app.services.cards import forge3d as F9
    g = {"nodes": [
        {"id": "s", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m", "kind": "mesh3d", "engine": "meshy-7",
         "texture_prompt": "  or ancien, gravure  ", "ultra": 1},
        {"id": "m2", "kind": "mesh3d", "engine": "warp-drive", "ultra": True},
        {"id": "mat", "kind": "material", "mat": "zzz-pas-un-mid",
         "finish": "argent", "aniso": "oui", "tile_mm": 9999},
        {"id": "tr", "kind": "transform", "x_mm": -500, "rot_deg": 720,
         "scale": 99, "z_mm": "abc"},
        {"id": "a", "kind": "assemble"}], "edges": []}
    out = F9.clean_graph(g)
    n = {x["id"]: x for x in out["nodes"]}
    assert n["m"]["engine"] == "meshy-7" and n["m"]["ultra"] is True
    assert n["m"]["texture_prompt"] == "or ancien, gravure"
    # moteur inconnu -> défaut meshy-7 ; ET l'ultra ne survit pas à la
    # réparation (amendement contrôleur) : un drapeau PAYANT ne peut pas
    # naître du repli sur le défaut, l'utilisateur n'a pas nommé ce moteur.
    assert n["m2"]["engine"] == "meshy-7"
    assert n["m2"]["ultra"] is False
    assert F9.clean_graph({"nodes": [{"id": "x", "kind": "mesh3d",
        "engine": "tripo", "ultra": True}], "edges": []})["nodes"][0]["ultra"] is False
    # matière : mid invalide -> None, mais la FINITION la garde en vie
    assert n["mat"]["mat"] is None and n["mat"]["finish"] == "argent"
    assert n["mat"]["aniso"] is True
    assert n["mat"]["tile_mm"] == F9.MATERIAL_TILE_MM[1]
    # matière sans matière NI finition -> jetée
    vide = F9.clean_graph({"nodes": [{"kind": "material", "mat": "!!",
                                      "finish": "aucune"}], "edges": []})
    assert vide["nodes"] == []
    # transform : bornes
    assert n["tr"]["x_mm"] == F9.TRANSFORM_XY_MM[0]
    assert n["tr"]["rot_deg"] == F9.TRANSFORM_ROT_DEG[1]
    assert n["tr"]["scale"] == F9.TRANSFORM_SCALE[1]
    assert n["tr"]["z_mm"] == 0.0


def test_clean_graph_ne_laisse_plus_d_aretes_pendantes():
    """Important 3 (revue, amendement du contrôleur) : une arête ne doit
    survivre que si SES DEUX BOUTS ont survécu au nettoyage — filtrer sur
    `ids` (tout id VU, y compris un nœud jeté par une branche kind-spécifique)
    laissait des arêtes PENDANTES vers un nœud absent du graphe nettoyé."""
    from app.services.cards import forge3d as F9
    g = {"nodes": [
        {"id": "src", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "matvide", "kind": "material", "mat": "!!", "finish": "aucune"},
        {"id": "asm", "kind": "assemble"}],
        "edges": [{"from": "src", "to": "matvide"},
                 {"from": "matvide", "to": "asm"}]}
    out = F9.clean_graph(g)
    ids = {n["id"] for n in out["nodes"]}
    assert "matvide" not in ids                  # la matière vide est jetée
    assert "src" in ids and "asm" in ids          # les deux voisins survivent
    # aucune arête ne nomme plus le nœud jeté, des deux côtés
    for e in out["edges"]:
        assert e["from"] != "matvide" and e["to"] != "matvide"
    assert out["edges"] == []                     # les DEUX arêtes de matvide tombent


def test_info_publie_moteurs_prix_matieres_et_bornes(monkeypatch):
    """7 moteurs, prix fal en $ depuis pricing, crédits Meshy depuis la grille
    partagée (+ conversion $ directionnelle meshy_credit_usd), matières de la
    boutique, bornes matière/transform — l'écran ne recopie RIEN."""
    from app.config import settings
    from app.services import pricing, meshy_service as MS, material_store
    from app.services import asset3d_service as A3D
    from app.services.cards import forge3d as F9
    did = _deck("Info 2b")
    mat = material_store.create_material(name="essai-info")
    try:
        info = _api("GET", f"/api/cards/{did}/forge3d/info").json()
        eng = {e["id"]: e for e in info["mesh3d"]["engines"]}
        assert list(eng) == ["tripo", "hunyuan", "trellis", "rodin", "triposr",
                             "meshy-6", "meshy-7"]
        # roster lock (M4) : les moteurs fal du miroir 2b sont un
        # SOUS-ENSEMBLE du registre asset3d_service — jamais un moteur que
        # le job (Task 4) ne saurait pas router.
        assert {e["id"] for e in F9.MESH3D_ENGINES if e["provider"] == "fal"} \
            <= set(A3D.ENGINES)
        p = pricing.load()
        attendu = pricing.estimate({"kind": "asset3d", "engine": "tripo"}, p)["total_usd"]
        assert eng["tripo"]["provider"] == "fal" and eng["tripo"]["price_usd"] == attendu
        assert eng["meshy-7"]["provider"] == "meshy"
        assert eng["meshy-7"]["credits"] == MS.credits_image_to_3d("meshy-7", "standard", True, "2k") == 30
        assert eng["meshy-7"]["ultra_extra_credits"] == 5
        assert eng["meshy-6"]["ultra_extra_credits"] == 0
        assert eng["meshy-7"]["price_usd"] == round(30 * float(p["meshy_credit_usd"]), 4)
        assert info["mesh3d"]["default_engine"] == "meshy-7"
        assert info["mesh3d"]["degraded"] is None
        assert info["materials_degraded"] is None
        # has_meshy / has_fal : CONDUITS par leurs deux états (résidu de
        # re-revue Task 3). L'ancien miroir `== (settings.has_meshy or
        # bool(settings.MESHY_MOCK))` recopiait l'expression de
        # l'implémentation : VACUEUX dès que les deux côtés valaient False —
        # un `has_meshy: False` en dur l'aurait passé. Ici on force chaque
        # état et on lit le contrat, jamais la formule.
        monkeypatch.setattr(settings, "MESHY_API_KEY", "")
        monkeypatch.setattr(settings, "MESHY_MOCK", False)
        i0 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i0["has_meshy"] is False and i0["meshy_mock"] is False
        monkeypatch.setattr(settings, "MESHY_MOCK", True)     # simulateur seul
        i1 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i1["has_meshy"] is True and i1["meshy_mock"] is True
        monkeypatch.setattr(settings, "MESHY_MOCK", False)
        monkeypatch.setattr(settings, "MESHY_API_KEY", "cle-de-test")  # clé seule
        i2 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i2["has_meshy"] is True and i2["meshy_mock"] is False
        monkeypatch.setattr(settings, "FAL_KEY", "")
        assert _api("GET", f"/api/cards/{did}/forge3d/info"
                    ).json()["mesh3d"]["has_fal"] is False
        monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
        assert _api("GET", f"/api/cards/{did}/forge3d/info"
                    ).json()["mesh3d"]["has_fal"] is True
        monkeypatch.undo()      # les réglages redeviennent ceux du runtime
        # la boutique n'est plus vide (M3) : la matière créée voyage telle
        # quelle, et CHAQUE entrée n'expose que id/name — jamais les maps.
        assert isinstance(info["materials"], list)
        assert all(set(m.keys()) == {"id", "name"} for m in info["materials"])
        assert {"id": mat["id"], "name": "essai-info"} in info["materials"]
        # bornes matière/transform, épinglées littéralement (M6)
        assert info["material_limits"]["tile_mm"] == [10.0, 200.0]
        assert info["material_limits"]["finishes"] == ["aucune", "argent", "dorure"]
        assert info["transform_limits"]["xy_mm"] == [-100.0, 100.0]
        assert info["transform_limits"]["z_mm"] == [0.0, 10.0]
        assert info["transform_limits"]["rot_deg"] == [-180.0, 180.0]
        assert info["transform_limits"]["scale"] == [0.1, 4.0]
    finally:
        material_store.delete_material(mat["id"])


def test_info_degrade_au_lieu_de_500_si_prix_ou_matieres_explosent(monkeypatch):
    """Important 2 (revue, amendement du contrôleur) : une panne de la grille
    de prix OU de la boutique de matières ne doit JAMAIS faire tomber /info
    en 500 — chacune dégrade isolément, et le nom de la panne est publié
    (mesh3d.degraded), jamais avalé en silence."""
    from app.services import material_store, pricing
    did = _deck("Info degrade")

    def _casse_disque(*a, **k):
        raise OSError("disque HS")
    monkeypatch.setattr(material_store, "list_materials", _casse_disque)
    r1 = _api("GET", f"/api/cards/{did}/forge3d/info")
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["materials"] == []
    # la panne de la boutique est NOMMÉE, jamais avalée (résidu de re-revue
    # Task 3) : `materials: []` seul ne distingue pas une panne d'une boutique
    # réellement vide — l'écran ne pouvait pas savoir quoi dire.
    assert "disque HS" in b1["materials_degraded"]
    # le reste du payload reste INTACT : la panne de la boutique ne touche
    # pas la table des moteurs (les deux dégradent ISOLÉMENT)
    assert len(b1["mesh3d"]["engines"]) == 7
    assert b1["mesh3d"]["degraded"] is None
    monkeypatch.undo()

    # ISOLEMENT RÉEL dans l'autre sens : une matière TÉMOIN existe pendant la
    # panne de prix. L'ancien `assert b2["materials"] == []` n'épinglait que la
    # vacuité du magasin — il passait au vert sans rien prouver, et virait au
    # rouge dès qu'un test voisin y laissait une matière.
    temoin = material_store.create_material(name="temoin")
    try:
        def _casse_prix(op, p=None):
            raise KeyError("meshy_credit_usd")
        monkeypatch.setattr(pricing, "estimate", _casse_prix)
        r2 = _api("GET", f"/api/cards/{did}/forge3d/info")
        assert r2.status_code == 200, r2.text
        b2 = r2.json()
        assert b2["mesh3d"]["engines"] == []
        assert "meshy_credit_usd" in b2["mesh3d"]["degraded"]
        # la boutique, elle, n'est pas touchée par la panne de prix : elle rend
        # sa matière ET n'avoue aucune panne.
        assert {"id": temoin["id"], "name": "temoin"} in b2["materials"]
        assert b2["materials_degraded"] is None
    finally:
        material_store.delete_material(temoin["id"])


def test_clean_graph_repare_et_ne_leve_jamais():
    """Un graphe mal formé ne fait jamais 500 : nettoyeur clé par clé, patron
    clean_options de P8. Les bornes sont celles du bloc miroir."""
    from app.services.cards import forge3d as F9
    # graphe sain : conservé tel quel (aux arrondis près)
    g = {"nodes": [
        {"id": "n1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "n2", "kind": "relief", "depth_mm": 1.2, "base_mm": 0.3},
        {"id": "n3", "kind": "assemble"}],
        "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]}
    out = F9.clean_graph(g)
    assert [n["kind"] for n in out["nodes"]] == ["layer", "relief", "assemble"]
    assert out["nodes"][1]["depth_mm"] == 1.2
    # poubelle : kinds inconnus jetés, bornes appliquées, ids resynthétisés,
    # edges orphelines jetées, JAMAIS d'exception
    sale = {"nodes": [{"kind": "teleport"}, {"kind": "relief", "depth_mm": 99},
                      {"id": "x", "kind": "layer", "role": "inexistant"}],
            "edges": [{"from": "fantome", "to": "x"}], "extra": object}
    out2 = F9.clean_graph(sale)   # ne lève pas
    kinds = [n["kind"] for n in out2["nodes"]]
    assert "teleport" not in kinds
    relief = [n for n in out2["nodes"] if n["kind"] == "relief"][0]
    assert relief["depth_mm"] <= F9.RELIEF_DEPTH_MM_MAX
    assert out2["edges"] == []
    assert F9.clean_graph(None) == {"nodes": [], "edges": []}
    assert F9.clean_graph("n'importe quoi") == {"nodes": [], "edges": []}
    # constaté en auto-revue, absent du graphe « poubelle » ci-dessus (qui
    # n'utilise que des chaînes) : `x in un_set` HACHE x avant de comparer —
    # un `kind`/`role`/`id` de bord NON HACHABLE (liste, dict) au lieu d'une
    # chaîne levait TypeError avant garde, un vrai chemin puisque ces valeurs
    # viennent telles quelles du JSON client. Repris ici jusqu'aux arêtes.
    hostile = {
        "nodes": [{"kind": ["layer"]}, {"kind": {"x": 1}},
                 {"kind": "layer", "role": ["cadre"]},
                 {"kind": "layer", "role": {"a": 1}},
                 {"id": ["a"], "kind": "assemble"},
                 {"id": {"a": 1}, "kind": "assemble"},
                 {"id": 1, "kind": "assemble"}],
        "edges": [{"from": ["x"], "to": "y"}, {"from": 1, "to": 1}],
    }
    out3 = F9.clean_graph(hostile)     # ne lève pas non plus
    assert isinstance(out3, dict) and "nodes" in out3 and "edges" in out3
    assert out3["edges"] == []         # aucune arête à bouts non-chaîne ne survit
    # I1/M1 (revue) : l'id BRUT {"a": 1} (déjà dans `hostile` ci-dessus,
    # kind="assemble", 2e survivant sur les 3) est DÉSINFECTÉ comme
    # artifact.name — aucune accolade, guillemet ni espace ne doit survivre
    # dans l'id qui sort.
    assemble_ids = [n["id"] for n in out3["nodes"] if n["kind"] == "assemble"]
    assert len(assemble_ids) == 3
    id_moche = assemble_ids[1]         # né de {"id": {"a": 1}, ...}
    assert not any(c in id_moche for c in "{}'\" "), f"id non desinfecte : {id_moche!r}"

    # I1 (revue) : deux nœuds d'id BRUT "n2x" — la resynthese anti-collision
    # doit suffixer en BOUCLE jusqu'a unicite (mesure en revue : un simple
    # "n{i+1}x" retombait sur EXACTEMENT "n2x" pour LES DEUX, et l'arête
    # visant l'un des deux devenait ambiguë entre les deux). Le scheme est
    # DETERMINISTE (aucun hasard nulle part dans clean_graph) : le meme
    # doublon rend TOUJOURS les memes ids resynthetises.
    doublon = {"nodes": [{"id": "n2x", "kind": "assemble"},
                        {"id": "n2x", "kind": "assemble"}],
              "edges": []}
    out4 = F9.clean_graph(doublon)
    assert len(out4["nodes"]) == 2, "les deux noeuds doivent etre conserves"
    ids4 = [n["id"] for n in out4["nodes"]]
    assert len(ids4) == len(set(ids4)), f"ids en collision : {ids4}"
    assert ids4 == ["n2x", "n2x_2"], ids4
    assert [n["id"] for n in F9.clean_graph(doublon)["nodes"]] == ids4, \
        "resynthese non deterministe"

    # P1 (revue, 2c) : le suffixe de collision reste DANS le budget de 24
    # caracteres — atteignable des que deux ids bruts partagent un prefixe
    # de 24 caracteres identiques. L'ancien "+x" poussait alors le second a
    # 25 caracteres, que `_NID_RE` (borne {1,24}, gardee par les routes
    # mesh3d/node-preview) rejette ensuite : le noeud resynthetise ne
    # pouvait plus jamais lancer/poller/previsualiser son mesh3d.
    plein = "a" * 24
    trois_pleins = {"nodes": [{"id": plein, "kind": "assemble"},
                              {"id": plein, "kind": "assemble"},
                              {"id": plein, "kind": "assemble"}],
                    "edges": []}
    out5 = F9.clean_graph(trois_pleins)
    ids5 = [n["id"] for n in out5["nodes"]]
    assert len(ids5) == 3 and len(set(ids5)) == 3, f"ids en collision : {ids5}"
    assert all(len(x) <= 24 for x in ids5), f"id hors budget de 24 : {ids5}"
    assert all(F9._NID_RE.match(x) for x in ids5), \
        f"id repare invalide pour _NID_RE (routes/dossiers) : {ids5}"


def test_le_relief_est_un_solide_ferme_et_le_quad_un_plan_exact():
    """La dalle en relief est FERMÉE PAR CONSTRUCTION — on le PROUVE sur les
    arêtes (chacune partagée par exactement 2 triangles) et sur le volume
    signé positif, les mesures du domaine (doctrine P8), en copie locale."""
    from PIL import Image, ImageDraw
    from app.services.cards import forge3d as F9
    # une silhouette réaliste : un anneau (trou au centre)
    im = Image.new("L", (64, 64), 0)
    d = ImageDraw.Draw(im)
    d.ellipse([4, 4, 60, 60], fill=255)
    d.ellipse([20, 20, 44, 44], fill=0)
    m = F9.relief_mesh(im, w_mm=63.0, h_mm=88.0, depth_mm=1.0, base_mm=0.3,
                       grid=48)
    rep = F9.mesh_measures(m)
    assert rep["closed"] is True, rep
    assert rep["volume_mm3"] > 0.0
    # le relief DÉCLARE sa fermeture (drapeau topologique, économise la
    # remesure côté route — ~7 s au grid max) : la déclaration DOIT coïncider
    # avec la mesure, sinon le raccourci de build3d mentirait au client.
    assert m["closed"] is True
    assert m["closed"] == rep["closed"]
    # le relief est borné : base <= z <= base+depth, xy dans la carte
    xs = m["positions"][0::3]; ys = m["positions"][1::3]; zs = m["positions"][2::3]
    assert min(zs) == 0.0 and max(zs) <= 0.3 + 1.0 + 1e-6
    assert max(xs) <= 63.0 + 1e-6 and max(ys) <= 88.0 + 1e-6
    # UV : couvertes 0..1 pour plaquer la texture de couche
    assert 0.0 <= min(m["uvs"]) and max(m["uvs"]) <= 1.0

    q = F9.quad_mesh(w_mm=63.0, h_mm=88.0)
    assert len(q["positions"]) == 4 * 3 and len(q["indices"]) == 6
    assert q["closed"] is False       # un plan n'est pas un solide
    assert F9.mesh_measures(q)["closed"] is False
    assert q["closed"] == F9.mesh_measures(q)["closed"]


def _read_glb(data: bytes):
    import struct as _s
    assert data[:4] == b"glTF"
    doc_len = _s.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + doc_len].decode("utf-8").rstrip("\x00 "))
    off = 20 + doc_len
    binv = b""
    if off < len(data):
        blen = _s.unpack("<I", data[off:off + 4])[0]
        binv = data[off + 8:off + 8 + blen]
    return doc, binv


def test_le_glb_assemble_est_propre_des_l_ecriture():
    """Bornes EXACTES, zéro identité, CLAMP, échelle physique — pas une
    rustine post-hoc : le writer écrit juste du premier coup, et ce test
    relit les octets pour le prouver (doctrine P8, re-mesurée ici)."""
    from PIL import Image
    from app.services.cards import forge3d as F9
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (200, 30, 30, 255)).save(png, "PNG")
    elements = [
        {"name": "cadre", "mesh": F9.quad_mesh(63.0, 88.0), "png": png.getvalue(),
         "alpha": True, "z_mm": 0.0},
        {"name": "relief", "mesh": F9.relief_mesh(Image.new("L", (16, 16), 255),
                                                  63.0, 88.0, 1.0, 0.3, 8),
         "png": png.getvalue(), "alpha": False, "z_mm": 0.4},
    ]
    glb = F9.write_scene_glb(elements, name="carte3d",
                             extras={"deck": "test", "unit": "metre"})
    doc, binv = _read_glb(glb)
    # 1. identité : AUCUN champ interdit, nulle part
    plat = json.dumps(doc)
    for mot in ("generator", "copyright", "author", "producer"):
        assert f'"{mot}"' not in plat, mot
    # 2. bornes exactes : re-mesure des float32 du buffer, écart zéro exigé
    import struct as _s
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126 or "min" not in acc:
            continue
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[acc["type"]]
        lo = [float("inf")] * n; hi = [float("-inf")] * n
        for e in range(acc["count"]):
            vals = _s.unpack_from("<" + "f" * n, binv, off + e * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c]); hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi, "bornes inexactes"
    # 3. CLAMP partout, échelle physique sur la racine, enfants nommés
    for s in doc.get("samplers", []):
        assert s["wrapS"] == 33071 and s["wrapT"] == 33071
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert racine["scale"] == [0.001, 0.001, 0.001]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    assert noms == ["cadre", "relief"]
    # 4. l'écart z du second élément est porté par SON nœud (translation mm)
    assert doc["nodes"][racine["children"][1]]["translation"][2] == 0.4
    # 5. matériaux : BLEND pour le plan, OPAQUE non double face pour le relief
    m_plan = doc["materials"][doc["meshes"][0]["primitives"][0]["material"]]
    m_rel = doc["materials"][doc["meshes"][1]["primitives"][0]["material"]]
    assert m_plan["alphaMode"] == "BLEND" and m_plan["doubleSided"] is True
    assert m_rel.get("alphaMode", "OPAQUE") == "OPAQUE" and not m_rel.get("doubleSided")
    # 6. taille de scene : le GLB a UN seul element pris isolement doit aussi
    #    passer (racine + 1 enfant, pas de translation quand z_mm == 0.0)
    seul = F9.write_scene_glb(
        [{"name": "solo", "mesh": F9.quad_mesh(63.0, 88.0), "png": png.getvalue(),
         "alpha": False, "z_mm": 0.0}], name="carte3d", extras={})
    doc1, bin1 = _read_glb(seul)
    racine1 = doc1["nodes"][doc1["scenes"][0]["nodes"][0]]
    assert len(racine1["children"]) == 1
    assert doc1["nodes"][racine1["children"][0]]["name"] == "solo"
    # 7. la taille declaree du buffer couvre EXACTEMENT les donnees du chunk
    #    BIN — sur les deux tailles (1 et 2 elements)
    assert doc1["buffers"][0]["byteLength"] == len(bin1)
    assert doc["buffers"][0]["byteLength"] == len(binv)
    # 8. zéro identité VRAIE pour TOUT appelant : le writer filtre lui-même
    #    "generator" même quand l'APPELANT en glisse un dans extras — et la
    #    racine porte l'extras FILTRÉ (pas l'original), aux deux étages
    #    (asset.extras ET racine.extras — les DCC divergent sur lequel ils
    #    gardent).
    sale = F9.write_scene_glb(
        [{"name": "x", "mesh": F9.quad_mesh(63.0, 88.0), "png": png.getvalue(),
         "alpha": False, "z_mm": 0.0}], name="carte3d",
        extras={"deck": "test", "generator": "espion"})
    doc_sale, _ = _read_glb(sale)
    assert '"generator"' not in json.dumps(doc_sale)
    racine_sale = doc_sale["nodes"][doc_sale["scenes"][0]["nodes"][0]]
    assert racine_sale["extras"] == {"deck": "test"}
    assert doc_sale["asset"]["extras"] == {"deck": "test"}


def test_le_glb_assemble_est_relisible_par_un_lecteur_tiers():
    """Preuve supplémentaire, INDÉPENDANTE du re-empaquetage du test
    précédent : si `pygltflib` est présent dans le runtime embarqué, on lui
    fait recharger le GLB (un vrai lecteur tiers, pas notre propre parseur).
    Absent (cas attendu ici, mesuré), on valide honnêtement ce qu'on PEUT
    vérifier sans lui : la cohérence RÉFÉRENTIELLE du document — chaque
    index cité (bufferView, byteOffset+byteLength, material, image) reste
    DANS les bornes des tableaux qu'il vise. Ce n'est pas une conformité
    glTF complète, seulement des invariants de cohérence croisée.

    SCÈNE MIXTE (revue Task 5) : parmi les six quads, l'un porte une finition
    et un autre une matière. C'est la SEULE configuration où les index
    d'images, de textures et d'accesseurs peuvent dériver les uns des autres —
    un élément habillé en insère deux à trois AU MILIEU de la boucle. Les
    quatre autres doivent rester, au champ près, des éléments de la 2a."""
    from PIL import Image
    from app.services.cards import forge3d as F9
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(png, "PNG")
    fin = F9.holo_finish("argent", aniso=True, out_px=64)
    mm = F9.material_pngs({"normal": Image.new("RGB", (8, 8), (128, 128, 255)),
                           "roughness": Image.new("L", (8, 8), 90),
                           "ao": Image.new("L", (8, 8), 210)})
    elements = [{"name": f"e{i}", "mesh": F9.quad_mesh(63.0, 88.0),
                "png": png.getvalue(), "alpha": bool(i % 2), "z_mm": float(i)}
               for i in range(6)]
    elements[2]["finish"] = fin
    elements[4]["mat_maps"] = mm
    glb = F9.write_scene_glb(elements, name="six", extras={})
    doc, binv = _read_glb(glb)

    # 1. les éléments NUS restent des éléments de la 2a — aucune contagion
    for i in (0, 1, 3, 5):
        m = doc["materials"][doc["meshes"][i]["primitives"][0]["material"]]
        assert "extensions" not in m, i
        assert "normalTexture" not in m and "occlusionTexture" not in m, i
        assert m["pbrMetallicRoughness"]["roughnessFactor"] == 0.9, i
        assert "TANGENT" not in doc["meshes"][i]["primitives"][0]["attributes"]
    # 2. le document ne déclare QUE ce qui a réellement servi
    assert set(doc["extensionsUsed"]) == {"KHR_materials_iridescence",
                                          "KHR_materials_clearcoat",
                                          "KHR_materials_anisotropy"}
    assert "extensionsRequired" not in doc
    # 3. chaque élément pointe SA propre image de couche, dans l'ordre : les
    #    six PNG sont octet pour octet identiques et NE SONT PAS mutualisés
    #    (l'identité des couches est un contrat de la 2a).
    for i in range(6):
        m = doc["materials"][doc["meshes"][i]["primitives"][0]["material"]]
        src = doc["textures"][
            m["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]
        assert doc["images"][src]["name"] == f"e{i}", i
    # 4. les textures de matière d'e4 portent SES noms, pas ceux d'un voisin
    m4 = doc["materials"][doc["meshes"][4]["primitives"][0]["material"]]
    assert "metallicRoughnessTexture" in m4["pbrMetallicRoughness"]
    for cle, suffixe in (("normalTexture", "-normal"),
                         ("occlusionTexture", "-ao")):
        src = doc["textures"][m4[cle]["index"]]["source"]
        assert doc["images"][src]["name"] == "e4" + suffixe
    # 5. bornes EXACTES sur TOUS les accesseurs flottants, TANGENT compris —
    #    la table de types du test 2a n'a pas d'entrée VEC4 : ce contrôle-ci
    #    est le seul qui couvre l'accesseur ajouté par une finition.
    import struct as _s2
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126:
            continue
        n = {"VEC4": 4, "VEC3": 3, "VEC2": 2, "SCALAR": 1}[acc["type"]]
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        lo = [float("inf")] * n; hi = [float("-inf")] * n
        for e in range(acc["count"]):
            vals = _s2.unpack_from("<" + "f" * n, binv, off + e * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c]); hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi, acc["type"]
    try:
        import pygltflib
    except ImportError:
        pygltflib = None
    if pygltflib is not None:
        rechargeur = pygltflib.GLTF2.load_from_bytes(glb)
        assert len(rechargeur.meshes) == len(elements)
        return
    # pas de lecteur tiers dans ce runtime : mini-validateur de cohérence
    # référentielle, honnête sur ce qu'il vérifie.
    for acc in doc["accessors"]:
        assert 0 <= acc["bufferView"] < len(doc["bufferViews"])
    for bv in doc["bufferViews"]:
        assert bv.get("byteOffset", 0) + bv["byteLength"] <= len(binv)
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            assert 0 <= prim["material"] < len(doc["materials"])
    for tex in doc["textures"]:
        assert 0 <= tex["source"] < len(doc["images"])


def test_le_graphe_gratuit_produit_un_glb_et_son_metadata():
    """Bout en bout backend : couches livrées (réutilise l'export de la
    phase 1) -> graphe par défaut -> GLB assemblé + metadata.json ERC-721 +
    bordereau ; STL refusé avec MOTIF (des plans ne sont pas un solide)."""
    did = _deck("Graphe gratuit")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "card": "0", "paper": "#ffffff",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text

    graphe = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "fond-matiere", "side": "front"},
        {"id": "t1", "kind": "plane", "depth_mm": 0.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "essai3d"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe, "card": 0})
    assert r2.status_code == 200, r2.text
    b = r2.json()["artifact"]

    # le GLB : relu, 2 éléments nommés par leurs rôles, échelle physique
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, _ = _read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert [doc["nodes"][k]["name"] for k in racine["children"]] == \
        ["fond-matiere", "cadre"]
    # metadata.json : ERC-721 compatible, attributs mesurés
    meta = json.loads(_api("GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    assert meta["name"] and meta["image"] and meta["animation_url"]
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["deck"] and types["elements_3d"] == 2 and types["engines"] == "local"
    # STL : REFUSÉ avec motif (le plan n'est pas fermé) — jamais un fichier faux
    assert b["stl"]["written"] is False
    assert "ferme" in b["stl"]["why"] or "fermé" in b["stl"]["why"]

    # le graphe 100 % relief, lui, obtient son STL
    graphe2 = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "relief3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r3 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe2, "card": 0})
    b3 = r3.json()["artifact"]
    assert b3["stl"]["written"] is True
    stl = _api("GET", f"/api/cards/{did}/forge3d/file/{b3['stl']['name']}").content
    assert len(stl) == 84 + 50 * struct.unpack("<I", stl[80:84])[0]


def test_un_graphe_sans_couches_livrees_fait_409_motive():
    did = _deck("Sans couches")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": {"nodes": [], "edges": []}, "card": 0})
    assert r.status_code == 409
    assert "couches" in r.json()["detail"]


def test_le_plafond_de_12_elements_fait_400_avant_tout_travail():
    """OBLIGATION de revue (tâche 4) : le plafond (6 rôles x 2 côtés) est
    vérifié AVANT tout travail lourd — même un did SANS aucune couche
    livrée doit obtenir 400, jamais un 409/500 provoqué par le décodage
    d'image (aucun fichier n'est même touché avant ce garde-fou)."""
    from app.services.cards import forge3d as F9
    did = _deck("Trop d'elements")
    roles = [r["role"] for r in F9.LAYER_ROLES]
    nodes, edges = [], []
    for i in range(13):
        role = roles[i % len(roles)]
        s, t = f"s{i}", f"t{i}"
        nodes.append({"id": s, "kind": "layer", "role": role, "side": "front"})
        nodes.append({"id": t, "kind": "plane", "depth_mm": 0.0})
        edges.append({"from": s, "to": t})
        edges.append({"from": t, "to": "asm"})
    nodes.append({"id": "asm", "kind": "assemble"})
    nodes.append({"id": "art", "kind": "artifact", "name": "trop"})
    edges.append({"from": "asm", "to": "art"})
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": {"nodes": nodes, "edges": edges}, "card": 0})
    assert r.status_code == 400, r.text
    assert "13" in r.json()["detail"]


def test_une_couche_manquante_fait_409_distinct_du_graphe_vide():
    """OBLIGATION de revue (tâche 4) : le 409 « couche introuvable sur
    disque » (graphe bien câblé, mais le fichier livré manque) doit se
    DISTINGUER du 409 « graphe vide » (aucune chaîne résolue, couvert par
    le test soeur ci-dessus) — deux motifs NOMMÉS, jamais le même message
    générique recyclé pour deux causes différentes."""
    did = _deck("Couche manquante")
    graphe = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t1", "kind": "plane", "depth_mm": 0.0},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "jamaislivre"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": graphe, "card": 0})
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    # le motif NOMME LE FICHIER attendu — la preuve qu'il ne s'agit pas du
    # message générique "graphe vide" (qui, lui, ne cite aucun fichier).
    assert "cadre_c01_front.png" in detail

    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": {"nodes": [], "edges": []}, "card": 0})
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"] != detail


def test_preview_refuse_un_corps_trop_lourd_et_un_faux_png():
    """Route sœur `POST /preview/{art}` : corps brut borné à 8 Mo (413),
    signature PNG vérifiée (400) — mêmes gardes que `gltf.py:post_atlas`.
    Le succès écrit `{art}_preview.png` tel quel, sans rien redessiner côté
    serveur, et le rend aussitôt livrable par `/file` (patron P8)."""
    did = _deck("Apercu")
    gros = b"\x89PNG\r\n\x1a\n" + b"0" * (8 * 1024 * 1024 + 1)
    r1 = _api("POST", f"/api/cards/{did}/forge3d/preview/essai3d", content=gros)
    assert r1.status_code == 413, r1.text
    r2 = _api("POST", f"/api/cards/{did}/forge3d/preview/essai3d",
              content=b"pas un png")
    assert r2.status_code == 400, r2.text
    png = _png(Image.new("RGBA", (4, 4), (10, 20, 30, 255)))
    r3 = _api("POST", f"/api/cards/{did}/forge3d/preview/essai3d", content=png)
    assert r3.status_code == 200, r3.text
    assert r3.json()["preview"]["name"] == "essai3d_preview.png"
    r4 = _api("GET", f"/api/cards/{did}/forge3d/file/essai3d_preview.png")
    assert r4.status_code == 200 and r4.content == png


def test_les_elements_ignores_du_graphe_sont_avoues_au_bordereau():
    """REQUIS (revue) : `ignored` au bordereau — le contrat `artifact@1` se
    fige a CETTE tache, « l'ecran ne peut pas produire ces topologies »
    expire des la tache 5/2b. Deux motifs distincts, chacun avoue son nœud :
    une source SURNUMERAIRE (deux couches vers le meme traitement — la
    premiere arete gagne, la seconde est jetee AVEC un motif, jamais tue) et
    un traitement ORPHELIN (aucune couche source) a cote d'une chaine
    valide. Les deux cohabitent avec un artefact construit normalement
    (200) : ignorer n'est pas echouer."""
    did = _deck("Ignores")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "card": "0",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text

    graphe = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "s1b", "kind": "layer", "role": "fond-matiere", "side": "front"},
        {"id": "t1", "kind": "plane", "depth_mm": 0.0},
        # t2 : orphelin, aucune arete entrante — a cote d'une chaine valide
        {"id": "t2", "kind": "plane", "depth_mm": 0.0},
        # s4/t4 : source VALIDE mais t4 ne rejoint AUCUN assemble — motif
        # distinct du "sans source" ci-dessus (revue : decouvert non teste)
        {"id": "s4", "kind": "layer", "role": "typographie", "side": "front"},
        {"id": "t4", "kind": "relief", "depth_mm": 0.5, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "ignores3d"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "s1b", "to": "t1"},
                  {"from": "t1", "to": "asm"}, {"from": "asm", "to": "art"},
                  {"from": "s4", "to": "t4"}]}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe, "card": 0})
    assert r2.status_code == 200, r2.text
    b = r2.json()["artifact"]

    # l'element retenu porte le role du GAGNANT (premiere arete : s1, cadre)
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, _ = _read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert [doc["nodes"][k]["name"] for k in racine["children"]] == ["cadre"]

    # le PERDANT (s1b), l'ORPHELIN (t2) et le NON-RELIE-A-UN-ASSEMBLE (t4)
    # sont tous avoues, chacun avec un motif nomme, non vide
    ignores_par_noeud = {i["node"]: i["why"] for i in b["ignored"]}
    assert set(ignores_par_noeud) == {"s1b", "t2", "t4"}
    assert isinstance(ignores_par_noeud["s1b"], str) and ignores_par_noeud["s1b"]
    assert isinstance(ignores_par_noeud["t2"], str) and ignores_par_noeud["t2"]
    # t4 a une source valide (s4) MAIS ne rejoint aucun assemble : motif
    # distinct de celui de t2 (t2 n'a AUCUNE source), jusqu'ici jamais
    # verifie par une assertion — decouvert en revue.
    assert "non relie a un assemble" in ignores_par_noeud["t4"]

    # un graphe SANS rien a ignorer rend une liste VIDE, jamais absente
    graphe_propre = {"nodes": [
        {"id": "s3", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t3", "kind": "plane", "depth_mm": 0.0},
        {"id": "asm3", "kind": "assemble"},
        {"id": "art3", "kind": "artifact", "name": "propre3d"}],
        "edges": [{"from": "s3", "to": "t3"}, {"from": "t3", "to": "asm3"},
                  {"from": "asm3", "to": "art3"}]}
    r3 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe_propre, "card": 0})
    assert r3.status_code == 200, r3.text
    assert r3.json()["artifact"]["ignored"] == []


def test_la_fenetre_uv_reconcilie_coupe_et_toile_le_fond_perdu_ne_fuit_pas():
    """Défaut de couture (revue finale 2a) : les PNG de couche couvrent la
    TOILE (fond perdu compris, canvas_px), le maillage (quad_mesh/relief_mesh)
    couvre la COUPE (trim_mm) — sans fenêtre UV inset, le fond perdu
    s'affichait sur l'artefact avec ~2,5 % de distorsion anisotrope
    (63/69 != 88/94), et l'alpha du fond perdu pesait sur la silhouette du
    relief. Ce test le prouve sur les DEUX faces du bug, avec une silhouette
    SENTINELLE : alpha=255 UNIQUEMENT dans le fond perdu, alpha=0 dans la
    coupe.
      1. chaque accessor TEXCOORD_0 du GLB reste DANS la fenêtre [u0..u1] x
         [v0..v1] calculée depuis la géométrie RÉELLE du deck (jamais une
         constante) ;
      2. le relief reste PLAT (volume == trim_w * trim_h * base_mm, à
         tolérance de flottant près) — la preuve que l'alpha du fond perdu
         n'influence plus la géométrie, lue dans les OCTETS du GLB livré."""
    from app.services.cards.contract import geom
    from app.services.cards import forge3d as F9
    g = geom("poker_eu", 300)                 # le format par défaut du deck
    w_px, h_px = g.canvas_px                   # (815, 1110) — toile
    bx, by = round(g.bleed_off_px[0]), round(g.bleed_off_px[1])   # (36, 36)
    u0, v0 = bx / w_px, by / h_px
    u1, v1 = 1.0 - u0, 1.0 - v0

    # "fond-matiere" : un plan quelconque, présent pour vérifier que TOUS les
    # accessors TEXCOORD_0 (pas seulement celui du relief) sont insetés.
    fond = Image.new("RGBA", (w_px, h_px), (250, 246, 238, 255))
    # "cadre" : silhouette SENTINELLE — alpha=255 UNIQUEMENT dans le fond
    # perdu (l'anneau extérieur), alpha=0 dans la zone de coupe (le
    # rectangle intérieur, EXACTEMENT la boîte que la route est censée
    # cropper). Si la géométrie du relief lit encore le fond perdu, la
    # dalle ne sera plus plate.
    cadre = Image.new("RGBA", (w_px, h_px), (200, 30, 30, 255))
    ImageDraw.Draw(cadre).rectangle([bx, by, w_px - bx - 1, h_px - by - 1],
                                    fill=(0, 0, 0, 0))
    couches = {"fond-matiere": fond, "cadre": cadre}
    composite = Image.alpha_composite(fond.copy(), cadre)

    did = _deck("Fenetre UV")
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "card": "0", "paper": "#ffffff",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text

    graphe = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "fond-matiere", "side": "front"},
        {"id": "t1", "kind": "plane", "depth_mm": 0.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "fenetreuv"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe, "card": 0})
    assert r2.status_code == 200, r2.text
    b = r2.json()["artifact"]

    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, binv = _read_glb(glb)

    # 1. TOUS les accessors TEXCOORD_0 restent DANS la fenêtre — aucune fuite
    #    du fond perdu vers la texture visible.
    texcoord_accs = sorted({prim["attributes"]["TEXCOORD_0"]
                            for mesh in doc["meshes"]
                            for prim in mesh["primitives"]})
    assert texcoord_accs, "aucun accessor TEXCOORD_0 trouve"
    for ai in texcoord_accs:
        acc = doc["accessors"][ai]
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        for e in range(acc["count"]):
            u, v = struct.unpack_from("<2f", binv, off + e * 8)
            assert u0 - 1e-6 <= u <= u1 + 1e-6, (ai, e, u, u0, u1)
            assert v0 - 1e-6 <= v <= v1 + 1e-6, (ai, e, v, v0, v1)

    # 2. le relief (2e élément : "cadre") reste PLAT — l'alpha du fond perdu,
    #    seul porteur de sentinelle, n'influence plus la géométrie livrée.
    #    Relu depuis les OCTETS du GLB (pas un rejeu local) : positions et
    #    indices du 2e mesh, mesuré par mesh_measures (même instrument que
    #    la tâche 2).
    def _read_accessor(idx):
        acc = doc["accessors"][idx]
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[acc["type"]]
        count = acc["count"] * n
        code = "f" if acc["componentType"] == 5126 else "I"
        return list(struct.unpack_from("<" + code * count, binv, off))

    prim = doc["meshes"][1]["primitives"][0]
    positions = _read_accessor(prim["attributes"]["POSITION"])
    indices = _read_accessor(prim["indices"])
    rep = F9.mesh_measures({"positions": positions, "indices": indices})
    assert rep["closed"] is True, rep
    w_mm, h_mm = g.trim_mm
    base_mm = 0.3
    vol_attendu = w_mm * h_mm * base_mm
    assert abs(rep["volume_mm3"] - vol_attendu) < 0.5, \
        (rep["volume_mm3"], vol_attendu)


def test_l_ecran_du_graphe_est_une_liste_honnete_et_un_apercu_reel():
    """Test de SOURCE (Tache 5) : l'ecran ne peut pas exister sans ces
    quatre engagements — un rang par noeud de traitement construit depuis
    `defaultGraph`, un POST `build3d` qui part avec le graphe de l'etat et
    peint le bordereau depuis la reponse (`artifact`), un apercu REEL
    (model-viewer, jamais un rendu invente), une capture qui part au
    serveur (`toBlob` + `preview/`) et un motif STL affiche TEL QUEL."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # un rang par couche : traitement + profondeur, bornés par /info (jamais
    # de bornes recopiées en dur dans le HTML)
    assert 'id="cf-forge3d-graph"' in rendu
    assert "defaultGraph(" in rendu
    # le POST part avec le graphe de l'état, la réponse peint le bordereau
    corps = rendu.split("async function build3d(")[1].split("\n  }")[0]
    assert 'M.api.post("build3d"' in corps
    assert "artifact" in corps
    # l'aperçu est le VRAI fichier livré, chargé dans model-viewer par blob
    assert "model-viewer" in rendu
    # la capture d'aperçu part au serveur (rien n'est rendu côté serveur)
    assert "toBlob" in rendu and "preview/" in rendu
    # STL refusé : le motif du backend est AFFICHÉ, jamais réécrit
    assert "stl.why" in rendu or 'stl["why"]' in rendu or "stl && !" in rendu
    # « annulable » : le plan l'exige, patron du lab (mod-gltf.js et quatre
    # autres modules) — pile d'annulation + bouton, pas juste un mot dans un
    # commentaire.
    assert "HIST" in rendu
    assert 'id="cf-forge3d-undo"' in rendu
    # le re-seed reste OFFERT une fois le graphe DÉJÀ construit (pas
    # seulement dans la branche « graph est null ») : on le vérifie en
    # coupant le corps de paintGraph après la RÉSOLUTION DES CHAÎNES, qui ne
    # peut s'exécuter QUE dans la branche « le graphe existe ».
    # AMENDÉ À LA SOURCE (revue 2c, M8) — le marqueur était le littéral
    # `graphRows(graph)`. La résolution passe désormais par un mémo
    # (`rowsDe`, mémorisé sur l'IDENTITÉ du graphe : le CORE reconstruit le
    # sous-arbre à chaque écriture, donc un contenu qui change change
    # d'identité). L'INVARIANT vérifié ici n'a pas bougé d'un pouce ; seul le
    # nom de l'appel a changé, et un pin qui tombe sur un renommage légitime
    # mesure le vocabulaire, pas la propriété.
    corps_graph = rendu.split("function paintGraph(")[1].split("\n  }")[0]
    apres_rows = corps_graph.split("rowsDe(graph)")[1]
    assert "cf-forge3d-reseed" in apres_rows
    # I1 — NE PLUS TUER LE FOCUS (revue qualité) : editGraph distingue
    # explicitement les deux chemins — l'état est TOUJOURS commis
    # (setGraph), un repaint de la liste ne suit QUE si `kind` a changé la
    # structure du rang (base/grille apparues/disparues) ; les autres champs
    # (depth_mm/base_mm/grid/side) ne repeignent jamais, sans quoi chaque pas
    # de spinner détruirait l'input focalisé (le piège syncInputs/renderPanel
    # de mod-face).
    corps_edit = rendu.split("function editGraph(")[1].split("\n  }")[0]
    apres_commit = corps_edit.split("setGraph(next, field)")[1]
    assert 'field === "kind"' in apres_commit
    # AMENDÉ À LA SOURCE (revue 2c) — ce pin exigeait le littéral
    # `paintGraph()` À CET ENDROIT. La 2c ajoute une SECONDE projection du
    # graphe (le canvas) et un dispatcher `paintVue` ; la lettre du pin
    # obligeait alors `editGraph` à RECOPIER la dispatche au lieu de
    # l'appeler — une duplication qui n'existait que pour satisfaire un test,
    # c'est-à-dire exactement le contournement que ces pins existent pour
    # empêcher. On amende à la source plutôt que de contourner : ce que le
    # pin VEUT dire, c'est « un changement de `kind` repeint la vue entière,
    # et la liste garde son peintre ». La première moitié se vérifie ici, la
    # seconde là où la logique vit — dans le corps de `paintVue`.
    assert "paintVue()" in apres_commit
    corps_vue = rendu.split("function paintVue(")[1].split("\n  }")[0]
    assert "paintGraph()" in corps_vue, corps_vue
    assert "paintCanvas()" in corps_vue, corps_vue


def test_l_ecran_2b_affiche_les_prix_avant_et_les_etats_de_job():
    """Test de SOURCE (Task 7) : l'écran 2b ne peut pas exister sans ces
    engagements — le prix AVANT (servi par /info, jamais recopié), le
    lancement et le poll d'un job payant, la clé manquante DITE avant le 503
    du backend, les chaînes matière/transform bornées par /info, le manifeste
    qui suit LA CARTE (legs 5), l'échec montré LITTÉRAL, une dégradation
    affichée telle quelle plutôt qu'un select vide muet, et le `run_id`
    comparé entre deux polls (une relance d'un autre onglet est DITE)."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # le sélecteur de traitement offre mesh3d, les moteurs viennent de /info
    # (jamais une liste recopiée), le prix est affiché sur le nœud ET sommé
    assert "mesh3d" in rendu
    assert 'INFO.mesh3d' in rendu and "engines" in rendu
    assert 'id="cf-forge3d-cost"' in rendu
    # Lancer -> POST mesh3d/{nid}, puis poll GET jusqu'au terminal
    corps = rendu.split("async function launchMesh3d(")[1].split("\n  }")[0]
    assert 'M.api.post("mesh3d/"' in corps
    assert "pollMesh3d" in rendu
    # crédit/clé : l'écran DIT quand la clé manque (has_meshy) et n'invente rien
    assert "has_meshy" in rendu
    # texture_prompt et ultra existent (meshy), bornés par prompt_max de /info
    assert "texture_prompt" in rendu and "ultra" in rendu and "prompt_max" in rendu
    # matière + finition + aniso + tile, transform x/y/z/rot/scale : édités par
    # M.patch via le graphe (annulable), bornes lues de /info
    for champ in ("material_limits", "transform_limits", "finish", "aniso",
                  "tile_mm", "rot_deg"):
        assert champ in rendu, champ
    # legs 5 : le manifeste est rechargé quand la CARTE change, pas au boot seul
    assert "LAST_MANIFEST" in rendu and "cardChanged" in rendu
    # ... et ce rechargement est POUSSÉ, pas seulement tiré : le rail émet
    # `core:render` (jamais `core:deck`), l'évènement auquel mod-gltf/type/
    # print/data accrochent déjà leur péremption de carte. Sans cet abonnement
    # le contrôle de fraîcheur n'était appelé que depuis paintGraph, que rien
    # ne déclenchait quand l'utilisateur changeait de carte.
    assert 'CF.on("core:render"' in rendu
    handler = rendu.split('CF.on("core:render"')[1][:160]
    assert "cardChanged" in handler, handler
    # le seed CONSOMME le manifeste : il attend la vérification de fraîcheur
    # AVANT de le lire, sinon « construire le graphe par défaut » juste après
    # un changement de carte sème depuis les couches de la carte PRÉCÉDENTE.
    seed = rendu.split("async function seedDefault(")[1].split("\n  }")[0]
    assert "cardChanged" in seed and "defaultGraph(" in seed, seed
    assert seed.index("cardChanged") < seed.index("defaultGraph("), seed

    # L'INVARIANT D'APPARIEMENT, ÉPINGLÉ SUR LA SOURCE ENTIÈRE (et pas sur les
    # seuls chemins auxquels on a pensé) : `LAST_MANIFEST` et `MANIFEST_CARD`
    # forment une PAIRE — le manifeste et la carte POUR LAQUELLE il vaut. Poser
    # l'un sans l'autre fige un appariement faux que le comparateur de
    # `cardChanged` valide ensuite pour toujours ; c'est exactement ce qui est
    # arrivé au chemin de l'export (il posait `LAST_MANIFEST = rep.layers` seul,
    # à 123 lignes du plus proche `MANIFEST_CARD =`). Toute écriture de l'un
    # doit donc voisiner une écriture de l'autre. Mesuré : le plus grand écart
    # LÉGITIME est de 7 lignes.
    src_lignes = src.splitlines()
    pose_man = [i for i, l in enumerate(src_lignes)
                if re.search(r"LAST_MANIFEST\s*=[^=]", l)]
    pose_carte = [i for i, l in enumerate(src_lignes)
                  if re.search(r"MANIFEST_CARD\s*=[^=]", l)]
    assert pose_man and pose_carte
    # SYMETRIQUE (N6) : la paire se casse aussi bien en posant l'etiquette
    # seule (l'ecran se croit a jour sur un manifeste qui ne l'est pas) qu'en
    # posant le manifeste seul. Les deux sens sont donc verifies.
    for gauche, droite, quoi in ((pose_man, pose_carte, "LAST_MANIFEST"),
                                 (pose_carte, pose_man, "MANIFEST_CARD")):
        autre = "MANIFEST_CARD" if quoi == "LAST_MANIFEST" else "LAST_MANIFEST"
        for i in gauche:
            ecart = min(abs(i - j) for j in droite)
            assert ecart <= 10, (
                f"ligne {i + 1} pose {quoi} sans poser {autre} a cote (plus "
                f"proche : {ecart} lignes) — l'appariement manifeste/carte se "
                f"casse la : {src_lignes[i].strip()}")

    # le poll s'arrête aux DEUX états terminaux du contrat — et la DISJONCTION
    # est le fond de l'affaire : avec un « et » à la place du « ou », aucun job
    # ne satisfait plus la condition et la boucle tourne pour toujours, à un
    # GET toutes les 1,2 s, sans qu'aucun état affiché ne bouge. Épingler les
    # deux mots ne suffisait donc pas : on épingle l'opérateur.
    poll = rendu.split("function pollMesh3d(")[1].split("\n  }")[0]
    assert '"served"' in poll and '"failed"' in poll, poll
    assert re.search(r'status\s*===\s*"served"\s*\|\|', poll), poll

    # I1 — LA COUTURE writer<->ecran. Cote writer, `translate` REMPLACE le
    # `z_mm` de l'element (_node_trs) : il ne s'y AJOUTE pas. Semer un nœud
    # placement a z=0 sur un PLAN n'est donc pas « neutre » — ca l'aplatit sur
    # la couche du dessous (le cadre du graphe par defaut vit a 1,05 mm), et il
    # suffit d'ouvrir le tiroir Placement et de pousser x pour perdre la
    # parallaxe. Le neutre d'un plan, c'est SON z d'empilement.
    trs_corps = rendu.split("function editTrs(")[1].split("\n  }")[0]
    assert re.search(r"z_mm:\s*zEmpilement\(", trs_corps), trs_corps
    assert not re.search(r"z_mm:\s*0\b", trs_corps), trs_corps
    # ... et cette regle est CELLE que l'ecran affiche : une seule fonction,
    # lue par le semis ET par le rendu, sinon les deux derivent.
    zemp = rendu.split("function zEmpilement(")[1].split("\n  }")[0]
    assert "depth_mm" in zemp and '"plane"' in zemp, zemp
    assert "zEmpilement(" in rendu.split("function trsHtml(")[1].split("\n  }")[0]

    # LES CHAINES ECRITES PAR LE BACKEND (error, step, closed_note) sont
    # rendues ECHAPPEES : ce sont les seules valeurs de chipHtml qui ne
    # viennent ni d'un Number() ni d'un litteral d'ici, et un `<` dans un
    # message d'erreur de moteur casse la mise en page — au mieux.
    chip = rendu.split("function chipHtml(")[1].split("\n  }")[0]
    for champ in ("job.error", "job.step", "job.closed_note"):
        assert champ in chip, f"{champ} a disparu de chipHtml — pin obsolete"
        for m in re.finditer(re.escape(champ), chip):
            avant = chip[:m.start()]
            assert re.search(r"esc\(\s*(?:[\w.]+\s*\|\|\s*)?$", avant), (
                f"{champ} interpole sans esc() dans chipHtml : "
                f"...{chip[max(0, m.start() - 60):m.end() + 20]}")
    # l'échec d'un job est montré LITTÉRAL (error du job.json)
    assert "job.error" in rendu or 'job["error"]' in rendu
    # les legs d'affichage : degraded affiché tel quel, jamais un select vide muet
    assert "degraded" in rendu
    # run_id comparé entre deux polls (une relance d'un autre onglet est DITE)
    assert "run_id" in rendu


def test_la_geometrie_vit_dans_forge3d_scene_et_le_stl_garde_son_contrat_d_octets():
    """Legs 6 : la couture intra-pièce. Le module scène n'importe pas FastAPI ;
    forge3d réexporte (compat) ; le writer STL garde son CONTRAT D'OCTETS —
    structure, normale unitaire, ordre des sommets, z_mm appliqué, en-tête
    sans horodatage — pas seulement sa taille (mutants tués en revue)."""
    # stratégie deux-passes mesurée en revue : pic 267 Mo → 57 Mo sur 575k
    # triangles — propriété d'implémentation, pas d'assert ici (un budget
    # mémoire flakerait).
    import importlib
    from app.services.cards import forge3d as F9
    scene = importlib.import_module("app.services.cards.forge3d_scene")
    src = (ROOT / "backend" / "app" / "services" / "cards" /
           "forge3d_scene.py").read_text(encoding="utf-8")
    assert "fastapi" not in src.lower() and "APIRouter" not in src
    for nom in ("quad_mesh", "relief_mesh", "mesh_measures",
                "write_scene_glb", "_write_stl_binary"):
        assert getattr(F9, nom) is getattr(scene, nom), nom

    # ── LE SECOND SIDECAR (couture de delestage 2c-T6) ────────────────────
    # Il n'est PAS pur au sens de celui-ci (il porte des refus NOMMES, donc
    # leur code de statut) — l'ecart est assume et ecrit dans son en-tete.
    # Ce qui est mesure ici est ce qui fait de lui une VRAIE couture : il
    # n'importe RIEN de forge3d.py. Un sidecar qui importe son parent n'est
    # pas une couture, c'est la meme piece en deux fichiers.
    apercu = importlib.import_module("app.services.cards.forge3d_apercu")
    src_ap = (ROOT / "backend" / "app" / "services" / "cards" /
              "forge3d_apercu.py").read_text(encoding="utf-8")
    sans_com = re.sub(r"#[^\n]*", "", re.sub(r'""".*?"""', "", src_ap,
                                             flags=re.S))
    assert "forge3d" not in sans_com.replace("forge3d_scene", ""), \
        "le sidecar importe (ou nomme) forge3d : la couture est fausse"
    # ... et les DEUX noms que les tests lisent A TRAVERS forge3d sont bien
    # les MEMES objets. Les six autres reexports ont ete ELAGUES (personne ne
    # les lisait) : ces deux-la sont exerces, donc epingles.
    for nom in ("_resolve_graph_elements", "_PREVIEW_ASM_ID"):
        assert getattr(F9, nom) is getattr(apercu, nom), nom

    m = scene.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0, 0.3, 8)
    m["closed"] = True
    stl = scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": 0.0}], "x")
    n = struct.unpack("<I", stl[80:84])[0]
    assert n == len(m["indices"]) // 3
    assert len(stl) == 84 + 50 * n
    # déterminisme : deux appels, mêmes octets
    assert stl == scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": 0.0}], "x")

    # Le CONTRAT d'octets de la facette, pas seulement sa taille : normale
    # UNITAIRE, sommets dans l'ORDRE du triangle, z_mm APPLIQUÉ (le format STL
    # n'a pas de nœud pour le porter) et en-tête SANS horodatage. Sans ça, une
    # réécriture du writer passe la suite en inversant le winding, en perdant
    # l'empilement ou en datant le fichier (mutants mesurés en revue).
    assert stl[:80].rstrip(b"\x00") == f"x - millimetres - {n} triangles".encode()
    dz = 4.25
    stl_z = scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": dz}], "x")
    f0 = struct.unpack_from("<12fH", stl_z, 84)
    pos, idx = m["positions"], m["indices"]
    for s, iv in enumerate((idx[0] * 3, idx[1] * 3, idx[2] * 3)):
        for k in range(3):
            attendu = pos[iv + k] + (dz if k == 2 else 0.0)
            assert f0[3 + s * 3 + k] == pytest.approx(attendu, abs=1e-4), (s, k)
    assert sum(v * v for v in f0[:3]) == pytest.approx(1.0, abs=1e-5)
    assert f0[12] == 0


# ── LE JOB mesh3d (Task 4) — moteurs fal monkeypatchés, Meshy en simulateur ──
# AUCUN de ces tests ne dépense un crédit : les coutures fal (_upload /
# _run_engine / _download) sont remplacées, et Meshy tourne sur MESHY_MOCK.

def _graphe_mesh3d(engine="meshy-7", ultra=False):
    return {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": engine,
         "texture_prompt": "pierre gravee", "ultra": ultra},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}


def _exporter_couches(did, side: str = "front"):
    """Les couches de la phase 1, MÊME forme d'envoi que les tests voisins.

    `side` (2d) : le MÊME lot de PNG des deux côtés — c'est voulu. Le verso de
    la 2d ne se prouve pas sur des pixels différents mais sur une PLACE
    différente ; deux exports identiques rendent les deux boîtes de couche
    (`bbox_mm`) rigoureusement égales, donc le placement verso comparable au
    placement recto CHIFFRE POUR CHIFFRE.

    La TRAME vient de la GÉOMÉTRIE DU DECK (`geom_of`), pas d'un 815x1110 en
    dur : `post_layers` refuse (409) toute couche dont la taille ne tombe pas
    sur `canvas_px`, donc un deck jumbo ou tarot exigeait jusqu'ici de recopier
    ses pixels à la main dans le test."""
    from app.services.cards.core import read_deck, geom_of
    w_px, h_px = geom_of(read_deck(did)).canvas_px
    couches, composite = _couches_synthetiques(w_px, h_px)
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": side, "card": "0", "paper": "#ffffff",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text


def _dossier_noeud(did, nid):
    """Le dossier DURABLE d'un nœud, par le chemin du domaine lui-même
    (contract.deck_dir) — jamais une recomposition locale qui dériverait."""
    from app.services.cards.contract import deck_dir
    return deck_dir(did) / "forge3d" / "nodes" / nid


def _glb_ferme():
    """Un GLB FERMÉ écrit par NOTRE writer — le « modèle téléchargé » des
    tests de moteur : on connaît sa fermeture par construction, donc ce que la
    mesure doit en dire."""
    from app.services.cards import forge3d_scene as SC
    relief = SC.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0,
                            0.3, 8)
    png = io.BytesIO()
    Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(png, "PNG")
    return SC.write_scene_glb(
        [{"name": "x", "mesh": relief, "png": png.getvalue(), "alpha": False,
          "z_mm": 0.0}], name="x", extras={"unit": "metre"})


def _attendre_job(did, nid, timeout=30.0):
    import time as _t
    fin = _t.monotonic() + timeout
    while _t.monotonic() < fin:
        r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/{nid}")
        if r.status_code == 200 and r.json().get("status") in ("served", "failed"):
            return r.json()
        _t.sleep(0.05)
    raise AssertionError("job mesh3d jamais terminal")


def test_le_job_meshy_traverse_le_mock_et_mesure_closed_une_fois():
    """Flux Meshy COMPLET sur le simulateur (zéro crédit) : création, poll,
    rapatriement des binaires DANS le nœud, crédits consommés (ultra compté),
    closed mesuré à l'import et caché — le triangle du mock est OUVERT."""
    from app.config import settings as cfg
    from app.services import meshy_service as MS, pricing
    from app.services.storage import init_db
    # le journal partagé (I2) vit en base : les tests n'exécutent pas le
    # `lifespan` de l'application, donc les tables n'existent pas encore ici.
    asyncio.run(init_db())
    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    try:
        did = _deck("Job meshy")
        _exporter_couches(did)
        g = _graphe_mesh3d("meshy-7", ultra=True)
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        lance = r.json()
        assert lance["job"]["status"] in ("queued", "running")
        # le prix est ANNONCÉ avant, depuis la grille partagée et pricing.json
        # (jamais un littéral recopié) : 30 cr + 5 d'ultra sur meshy-7.
        cr = MS.credits_image_to_3d("meshy-7", "standard", True, "2k", ultra=True)
        assert cr == 35
        usd = round(cr * float(pricing.load()["meshy_credit_usd"]), 4)
        assert lance["job"]["price"] == {"credits": cr, "usd": usd}
        # la provenance voyage avec le job : LA couche source, son empreinte
        assert lance["job"]["source"]["file"] == "illustration_c01_front.png"

        job = _attendre_job(did, "m1")
        assert job["status"] == "served", job
        assert job["engine"] == "meshy-7" and job["consumed_credits"] == 35
        assert job["closed"] is False            # le tiny_glb du mock est un triangle
        base = _dossier_noeud(did, "m1")
        assert (base / "model.glb").is_file()
        assert (base / "preview.png").is_file()
        assert (base / "job.json").is_file()
        # les octets rapatriés sont bien ceux du simulateur, pas un fichier vide
        assert (base / "model.glb").read_bytes() == MS.tiny_glb()
        assert job["files"]["glb"] == "model.glb"
        assert job["files"]["textures"] == ["textures/0_base_color.png"]
        assert (base / "textures" / "0_base_color.png").is_file()
        assert job["task_id"], job          # l'id du fournisseur est tracé
        # l'empreinte annoncée est celle de la couche RÉELLEMENT lue — et la
        # vignette RÉELLEMENT envoyée a la sienne (M1 : deux questions
        # distinctes, « de quelle couche » et « qu'a vu le moteur »).
        from app.services.cards.contract import deck_dir
        src = deck_dir(did) / "forge3d" / "illustration_c01_front.png"
        assert job["source"]["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
        assert job["source"]["bytes"] == src.stat().st_size
        envoi = (base / "upload_src.png").read_bytes()
        assert job["source"]["upload_sha256"] == hashlib.sha256(envoi).hexdigest()
        assert job["source"]["upload_bytes"] == len(envoi)

        # I2 : la tâche PAYÉE est entrée au journal PARTAGÉ — sans quoi
        # `repatriate` refuse son id et `expiring_soon` ne prévient personne
        # avant que les URL Meshy n'expirent.
        rows = {r["id"]: r for r in asyncio.run(MS.list_tasks())}
        assert job["task_id"] in rows, sorted(rows)
        # la CRÉATION (seule à écrire le payload) et l'ÉTAT TERMINAL (seul à
        # écrire les crédits débités) sont journalisés tous les deux — l'un
        # sans l'autre laisserait le journal muet sur la moitié de l'histoire.
        assert rows[job["task_id"]]["payload"]["ai_model"] == "meshy-7"
        assert rows[job["task_id"]]["payload"]["ultra_mode"] is True
        assert rows[job["task_id"]]["status"] == "SUCCEEDED"
        assert rows[job["task_id"]]["consumed_credits"] == 35

        # relancer = dossier RÉINITIALISÉ (legs 4) : un vestige de la passe
        # précédente ne doit pas survivre au nouveau job.
        (base / "vestige.txt").write_text("passe precedente", encoding="utf-8")
        r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r2.status_code == 200, r2.text
        job2 = _attendre_job(did, "m1")
        assert job2["status"] == "served", job2
        assert not (base / "vestige.txt").exists(), "le dossier n'a pas ete reinitialise"
        # ...et la relance a bien une IDENTITÉ neuve (clôture C2)
        assert job2["run_id"] and job2["run_id"] != job["run_id"]
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None


def test_le_job_fal_passe_par_les_coutures_et_le_glb_ferme_est_su():
    """Moteur fal monkeypatché de bout en bout : upload -> run -> download.
    Le « GLB téléchargé » est un relief FERMÉ écrit par notre writer ->
    closed True mesuré une fois, prix $ = pricing."""
    from pathlib import Path
    from app.services import asset3d_service as A3D
    from app.services import pricing
    glb_connu = _glb_ferme()

    async def faux_upload(path):
        assert Path(path).is_file()
        return "https://fal.test/src.png"

    async def faux_run(engine, args):
        assert engine == "tripo" and args["image_url"] == "https://fal.test/src.png"
        return {"mesh_url": "https://fal.test/model.glb",
                "format_urls": {}, "texture_urls": [], "preview_url": None}

    def faux_download(url, dest, timeout=120):
        dest.write_bytes(glb_connu)
        return True

    vrai = (A3D._upload, A3D._run_engine, A3D._download)
    A3D._upload, A3D._run_engine, A3D._download = faux_upload, faux_run, faux_download
    try:
        did = _deck("Job fal")
        _exporter_couches(did)
        g = _graphe_mesh3d("tripo")
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        attendu = pricing.estimate({"kind": "asset3d", "engine": "tripo"})["total_usd"]
        assert r.json()["job"]["price"] == {"usd": attendu}
        job = _attendre_job(did, "m1")
        assert job["status"] == "served" and job["closed"] is True
        # le GLB livré est EXACTEMENT celui que la couture a téléchargé
        assert (_dossier_noeud(did, "m1") / "model.glb").read_bytes() == glb_connu
        # I3 : l'URL de l'artefact PAYÉ est PERSISTÉE, pas jetée après usage —
        # c'est le seul lien vers ce qu'on vient d'acheter si le disque casse.
        assert job["mesh_url"] == "https://fal.test/model.glb", job
        disque = json.loads(
            (_dossier_noeud(did, "m1") / "job.json").read_text(encoding="utf-8"))
        assert disque["mesh_url"] == "https://fal.test/model.glb"
    finally:
        A3D._upload, A3D._run_engine, A3D._download = vrai


def test_un_runner_rassis_se_tait_devant_une_relance(monkeypatch):
    """C2 — LA COURSE PAYANTE. Un runner dont l'envoi de la réponse a traîné
    au-delà de la péremption du marqueur peut démarrer APRÈS qu'une relance a
    réinitialisé le dossier et lancé un second job. Sans clôture d'identité, il
    ressuscitait le dossier effacé, DÉPENSAIT une seconde fois et écrivait son
    bordereau par-dessus celui du job vivant.

    Boîte blanche (la course est invisible d'un harnais sérialisé) : on écrit
    un `job.json` portant le run_id du SUCCESSEUR, puis on invoque le runner du
    prédécesseur avec SON run_id — les coutures de dépense sont piégées."""
    import time
    from app.services import asset3d_service as A3D
    from app.services.cards import forge3d as F9
    depenses = []

    async def jamais(*a, **k):
        depenses.append(a)
        raise AssertionError("un runner rassis ne doit RIEN depenser")

    monkeypatch.setattr(A3D, "_upload", jamais)
    monkeypatch.setattr(A3D, "_run_engine", jamais)
    did = _deck("Runner rassis")
    _exporter_couches(did)
    base = _dossier_noeud(did, "m1")
    base.mkdir(parents=True, exist_ok=True)
    (base / "job.json").write_text(json.dumps(
        {"schema": "card-3d/mesh3d-job@1", "node": "m1", "engine": "tripo",
         "run_id": "b" * 32, "status": "queued", "progress": 0,
         "step": "En file", "files": {}}), encoding="utf-8")
    fige = (base / "job.json").read_bytes()
    node = {"id": "m1", "kind": "mesh3d", "engine": "tripo",
            "texture_prompt": "", "ultra": False}
    source = {"role": "illustration", "side": "front",
              "file": "illustration_c01_front.png", "sha256": None}
    # le marqueur du SUCCESSEUR est en place : le rassis ne doit pas y toucher
    marqueur = time.monotonic()
    F9._MESH3D_RUNNING[(did, "m1")] = marqueur

    asyncio.run(F9._run_mesh3d(did, "m1", node, "fal", source, "a" * 32))

    assert depenses == [], "le runner rassis a depense"
    assert (base / "job.json").read_bytes() == fige, "job.json du successeur ecrase"
    assert not (base / "upload_src.png").exists(), "le dossier a ete ressuscite"
    assert F9._MESH3D_RUNNING.get((did, "m1")) is marqueur, \
        "le rassis a retire le marqueur de son successeur (job vivant declare orphelin)"
    F9._MESH3D_RUNNING.pop((did, "m1"), None)

    # ── la clôture vaut aussi EN COURS DE ROUTE ────────────────────────────
    # Le prédécesseur passe l'entrée (son run_id est bon), puis la relance
    # survient PENDANT l'appel au moteur. Il ne doit ni écrire son bordereau
    # par-dessus celui du successeur, ni déposer son modèle dans son dossier.
    monkeypatch.undo()
    glb = _glb_ferme()

    async def faux_upload(path):
        return "https://fal.test/src.png"

    successeur = {"schema": "card-3d/mesh3d-job@1", "node": "m1",
                  "engine": "tripo", "run_id": "c" * 32, "status": "queued",
                  "progress": 0, "step": "En file", "files": {}}

    async def run_puis_relance(engine, args):
        (base / "job.json").write_text(json.dumps(successeur), encoding="utf-8")
        return {"mesh_url": "https://fal.test/model.glb", "format_urls": {},
                "texture_urls": [], "preview_url": None}

    monkeypatch.setattr(A3D, "_upload", faux_upload)
    monkeypatch.setattr(A3D, "_run_engine", run_puis_relance)
    monkeypatch.setattr(A3D, "_download",
                        lambda url, dest, timeout=120: dest.write_bytes(glb))
    asyncio.run(F9._run_mesh3d(did, "m1", node, "fal", source, "b" * 32))
    milieu = json.loads((base / "job.json").read_text(encoding="utf-8"))
    assert milieu["run_id"] == "c" * 32, milieu
    assert milieu["status"] == "queued", "le predecesseur a ecrit chez le successeur"
    assert not (base / "model.glb").exists(), \
        "le predecesseur a depose son modele dans le dossier du successeur"

    # le runner LÉGITIME, lui, travaille : même dossier, même nœud, run_id qui
    # correspond — la clôture n'est pas un refus systématique.
    async def faux_run(engine, args):
        return {"mesh_url": "https://fal.test/model.glb", "format_urls": {},
                "texture_urls": [], "preview_url": None}

    monkeypatch.setattr(A3D, "_run_engine", faux_run)
    asyncio.run(F9._run_mesh3d(did, "m1", node, "fal", source, "c" * 32))
    apres = json.loads((base / "job.json").read_text(encoding="utf-8"))
    assert apres["status"] == "served" and apres["closed"] is True, apres
    assert F9._MESH3D_RUNNING.get((did, "m1")) is None


def test_un_moteur_qui_echoue_laisse_un_job_failed_au_message_litteral(monkeypatch):
    """Le chemin d'ÉCHEC, mesuré des deux côtés. fal : une réponse sans mesh
    (le cas réel du 20/07/2026, `pbr_model` non parsé) ne finit pas « servi »
    sur un dossier vide. Meshy : le message du fournisseur arrive TEL QUEL
    dans `error`, jamais réécrit ni avalé — c'est ce texte que l'écran montre
    quand des crédits manquent."""
    from app.config import settings as cfg
    from app.services import asset3d_service as A3D
    from app.services import meshy_service as MS

    async def faux_upload(path):
        return "https://fal.test/src.png"

    async def faux_run(engine, args):
        return {"mesh_url": None, "format_urls": {}, "texture_urls": [],
                "preview_url": None}

    monkeypatch.setattr(A3D, "_upload", faux_upload)
    monkeypatch.setattr(A3D, "_run_engine", faux_run)
    did = _deck("Moteur en echec")
    _exporter_couches(did)
    r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
             json={"graph": _graphe_mesh3d("tripo"), "card": 0})
    assert r.status_code == 200, r.text
    job = _attendre_job(did, "m1")
    assert job["status"] == "failed", job
    assert "aucun mesh" in job["error"] and "tripo" in job["error"]
    assert job["files"] == {}                  # rien n'est annonce livre
    assert not (_dossier_noeud(did, "m1") / "model.glb").exists()

    async def faux_create(base, payload):
        return "mock-9999"

    async def faux_get(base, tid):
        return {"id": tid, "status": "FAILED", "progress": 0,
                "task_error": {"message": "credits epuises"}}

    monkeypatch.setattr(cfg, "MESHY_MOCK", True)
    monkeypatch.setattr(MS, "create_task", faux_create)
    monkeypatch.setattr(MS, "get_task", faux_get)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
              json={"graph": _graphe_mesh3d("meshy-7"), "card": 0})
    assert r2.status_code == 200, r2.text
    job2 = _attendre_job(did, "m1")
    assert job2["status"] == "failed", job2
    assert job2["error"] == "meshy: credits epuises", job2["error"]


def test_le_verrou_du_noeud_est_pose_avant_le_premier_await_et_relache(monkeypatch):
    """C1 — LE VERROU EST ATOMIQUE. Entre le contrôle « un job court-il ? » et
    la pose du marqueur il ne doit y avoir AUCUN `await` : sinon deux POST
    rapprochés passent tous les deux, effacent tous les deux le dossier et
    lancent DEUX jobs PAYANTS, après quoi le second marqueur écrase le premier
    et le survivant se fait déclarer orphelin.

    La course elle-même est invisible d'un harnais sérialisé ; on mesure donc
    ses DEUX conditions : la toute première opération qui suit la pose (le
    devis) voit le verrou DÉJÀ posé, et un refus survenu après la pose le
    RELÂCHE — sans quoi le nœud resterait bloqué en 409 jusqu'au redémarrage."""
    from app.config import settings as cfg
    from app.services import meshy_service as MS
    from app.services.cards import forge3d as F9
    vu = {}
    vrai_prix = F9._mesh3d_price

    def prix_qui_casse(engine, provider, ultra):
        vu["verrou"] = F9._mesh3d_vivant(did, "m1")
        raise RuntimeError("bareme HS")

    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    did = _deck("Verrou atomique")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    try:
        monkeypatch.setattr(F9, "_mesh3d_price", prix_qui_casse)
        with pytest.raises(RuntimeError):
            _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert vu.get("verrou") is True, \
            "le verrou n'etait pas pose avant le premier await du lancement"
        assert F9._mesh3d_vivant(did, "m1") is False, \
            "un refus a laisse le noeud verrouille pour toujours"
        # ...et le nœud repart normalement, sans 409 fantôme
        monkeypatch.setattr(F9, "_mesh3d_price", vrai_prix)
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        assert _attendre_job(did, "m1")["status"] == "served"
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None
        F9._MESH3D_RUNNING.pop((did, "m1"), None)


def test_un_blip_reseau_ne_tue_pas_un_job_paye(monkeypatch):
    """I1 — un poll qui casse deux fois ne doit pas jeter vingt minutes de
    calcul DÉJÀ PAYÉ : les reprises sont bornées et vivent dans le budget. Au
    delà, l'échec porte le message LITTÉRAL du dernier essai."""
    from app.config import settings as cfg
    from app.services import meshy_service as MS
    from app.services.cards import forge3d as F9
    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    vrai_get = MS.get_task
    compte = {"n": 0}

    async def get_capricieux(base, tid):
        compte["n"] += 1
        if compte["n"] <= 2:
            raise RuntimeError(f"meshy: ReadTimeout (essai {compte['n']})")
        return await vrai_get(base, tid)

    try:
        monkeypatch.setattr(MS, "get_task", get_capricieux)
        did = _deck("Blip reseau")
        _exporter_couches(did)
        g = _graphe_mesh3d("meshy-7")
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        job = _attendre_job(did, "m1")
        assert job["status"] == "served", job
        assert compte["n"] > 2, "les deux pannes n'ont pas ete traversees"

        # ...et une panne QUI DURE finit en echec NOMME. La constante est
        # abaissee pour ne pas payer cinq attentes exponentielles dans la
        # suite ; sa valeur nominale est epinglee juste en dessous.
        assert F9.MESH3D_POLL_RETRIES == 5
        monkeypatch.setattr(F9, "MESH3D_POLL_RETRIES", 2)

        async def get_mort(base, tid):
            raise RuntimeError("meshy: ReadTimeout definitif")

        monkeypatch.setattr(MS, "get_task", get_mort)
        r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r2.status_code == 200, r2.text
        job2 = _attendre_job(did, "m1")
        assert job2["status"] == "failed", job2
        assert job2["error"] == "meshy: ReadTimeout definitif", job2["error"]

        # ...et le compteur de reprises se REMET À ZÉRO à chaque succès : trois
        # blips ESPACÉS par des polls réussis, sur un budget de deux reprises,
        # doivent passer. Sans remise à zéro ils s'additionnent et le job payé
        # meurt sur des pannes qui n'ont jamais coexisté.
        etat = {"n": 0}

        async def get_alternant(base, tid):
            etat["n"] += 1
            if etat["n"] <= 5 and etat["n"] % 2 == 1:      # blips 1, 3, 5
                raise RuntimeError(f"meshy: blip {etat['n']}")
            if etat["n"] < 6:
                return {"id": tid, "status": "IN_PROGRESS", "progress": 40}
            return await vrai_get(base, tid)

        monkeypatch.setattr(MS, "get_task", get_alternant)
        r3 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r3.status_code == 200, r3.text
        job3 = _attendre_job(did, "m1")
        assert job3["status"] == "served", job3
        assert etat["n"] >= 6, etat
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None


def test_le_rapatriement_des_textures_est_borne(monkeypatch):
    """M3 — le fournisseur annonce autant de textures qu'il veut, notre disque
    non : la borne est un PLAFOND MESURÉ, pas une intention. Cinq entrées
    annoncées, plafond abaissé à deux, deux fichiers écrits."""
    from app.config import settings as cfg
    from app.services import meshy_service as MS
    from app.services.cards import forge3d as F9
    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    vrai_get = MS.get_task

    async def get_riche(base, tid):
        t = await vrai_get(base, tid)
        if t.get("status") == "SUCCEEDED":
            pre = f"{MS.MOCK_FILE_PREFIX}{tid}/"
            t["texture_urls"] = [{"base_color": f"{pre}texture_{i}.png"}
                                 for i in range(5)]
        return t

    try:
        monkeypatch.setattr(MS, "get_task", get_riche)
        monkeypatch.setattr(F9, "MESH3D_TEXTURES_MAX", 2)
        did = _deck("Textures bornees")
        _exporter_couches(did)
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": _graphe_mesh3d("meshy-7"), "card": 0})
        assert r.status_code == 200, r.text
        job = _attendre_job(did, "m1")
        assert job["status"] == "served", job
        assert job["files"]["textures"] == ["textures/0_base_color.png",
                                            "textures/1_base_color.png"]
        ecrits = sorted(p.name for p in
                        (_dossier_noeud(did, "m1") / "textures").iterdir())
        assert ecrits == ["0_base_color.png", "1_base_color.png"], ecrits
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None


def test_les_bornes_de_taille_du_glb_livre_sont_nommees(monkeypatch):
    """I4 — les deux branches de la borne, chacune avec son LITTÉRAL, prouvées
    en abaissant la constante (la vraie, 64 Mo, n'est pas testable à taille
    réelle). Elles ne finissent PAS pareil, et c'est voulu : côté fal le
    fichier est déjà sur le disque et PAYÉ, refuser ne le récupérerait pas —
    la mesure dégrade et l'artefact reste ; côté Meshy, `_mesh3d_rapatrie`
    décide encore s'il écrit, et c'est là que la borne garde son mordant."""
    from app.config import settings as cfg
    from app.services import asset3d_service as A3D
    from app.services import meshy_service as MS
    from app.services.cards import forge3d as F9
    glb = _glb_ferme()
    assert len(glb) > 10

    async def faux_upload(path):
        return "https://fal.test/src.png"

    async def faux_run(engine, args):
        return {"mesh_url": "https://fal.test/model.glb", "format_urls": {},
                "texture_urls": [], "preview_url": None}

    monkeypatch.setattr(A3D, "_upload", faux_upload)
    monkeypatch.setattr(A3D, "_run_engine", faux_run)
    monkeypatch.setattr(A3D, "_download",
                        lambda url, dest, timeout=120: dest.write_bytes(glb))
    monkeypatch.setattr(F9, "MAX_EXT_GLB_BYTES", 10)
    did = _deck("Bornes de taille")
    _exporter_couches(did)
    r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
             json={"graph": _graphe_mesh3d("tripo"), "card": 0})
    assert r.status_code == 200, r.text
    job = _attendre_job(did, "m1")
    assert job["status"] == "served", job          # l'artefact PAYÉ est gardé
    assert job["closed"] is None
    assert job["closed_note"] == (
        f"fermeture non mesurée : GLB trop lourd ({len(glb)} o, plafond 10 o)")
    assert (_dossier_noeud(did, "m1") / "model.glb").read_bytes() == glb

    # côté Meshy : le fichier n'est pas encore écrit, la borne REFUSE et le
    # job échoue avec son motif nommé.
    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    try:
        r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": _graphe_mesh3d("meshy-7"), "card": 0})
        assert r2.status_code == 200, r2.text
        job2 = _attendre_job(did, "m1")
        assert job2["status"] == "failed", job2
        assert job2["error"] == (
            f"meshy: model.glb trop lourd ({len(MS.tiny_glb())} o, "
            f"maximum 10 o)"), job2["error"]
        assert not (_dossier_noeud(did, "m1") / "model.glb").exists()
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None


def test_les_refus_du_job_mesh3d_sont_nommes(monkeypatch):
    """Chaque refus a SON motif : couches absentes (409), nœud hors graphe
    (400), couche trop lourde (413), clé de moteur manquante (503), job
    inexistant (404)."""
    from app.config import settings as cfg
    from app.services.cards import forge3d as F9
    did = _deck("Refus mesh3d")
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1", json={"graph": g, "card": 0})
    assert r.status_code == 409 and "couches" in r.json()["detail"]
    _exporter_couches(did)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/zzz", json={"graph": g, "card": 0})
    assert r2.status_code == 400
    # M1 : la borne de POIDS de la couche source est vérifiée sur un `stat`,
    # AVANT tout travail — la constante de production (64 Mo) n'est pas
    # testable à taille réelle, on l'abaisse (idiome du fichier).
    monkeypatch.setattr(F9, "MAX_LAYER_BYTES", 10)
    rl = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
              json={"graph": g, "card": 0})
    assert rl.status_code == 413, rl.text
    assert "trop lourde" in rl.json()["detail"]
    monkeypatch.undo()
    avant = (cfg.MESHY_API_KEY, cfg.MESHY_MOCK)
    cfg.MESHY_API_KEY, cfg.MESHY_MOCK = "", False
    try:
        r3 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r3.status_code == 503 and "MESHY_API_KEY" in r3.json()["detail"]
    finally:
        cfg.MESHY_API_KEY, cfg.MESHY_MOCK = avant
    r4 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r4.status_code == 404
    # aucun refus n'a laissé de dossier derrière lui
    assert not _dossier_noeud(did, "m1").exists()

    # TRAVERSÉE (constatée en auto-revue) : un nid qui n'est QUE des points
    # n'est pas un NOM de dossier, c'est un SAUT — `nodes/..` désigne
    # `forge3d/`, que la réinitialisation du nœud efface au rmtree. Un seul
    # lancement sur un nœud nommé `..` détruisait toutes les couches du deck.
    from app.services.cards.contract import deck_dir
    for mechant in ("..", ".", "...", "a" * 25):
        assert not F9._NID_RE.match(mechant), mechant
    # le CONFINEMENT, par-dessus le motif (doctrine deck_dir : ceinture et
    # bretelles) : les deux noms qui sont vraiment des sauts de chemin.
    for saut in ("..", "."):
        with pytest.raises(Exception):
            F9._node_dir(did, saut, create=True)
    for mechant in ("..", ".", "...", "a" * 25):
        g2 = json.loads(json.dumps(g))
        g2["nodes"][1]["id"] = mechant
        g2["edges"] = [{"from": "s1", "to": mechant}]
        chemin = mechant.replace(".", "%2e")
        rr = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/{chemin}",
                  json={"graph": g2, "card": 0})
        assert rr.status_code in (400, 404), (mechant, rr.status_code, rr.text)
    # ...et les couches exportées du deck sont TOUJOURS là
    assert (deck_dir(did) / "forge3d" / "illustration_c01_front.png").is_file()


def test_un_job_running_orphelin_apres_redemarrage_est_avoue(monkeypatch):
    """Le registre mémoire ne survit pas au processus : un `running` sur
    disque sans tâche vivante est un ORPHELIN — avoué, jamais laissé tourner
    en rond dans l'écran."""
    import time as _t
    from app.services.cards import forge3d as F9
    did = _deck("Orphelin")
    base = _dossier_noeud(did, "m1")
    base.mkdir(parents=True, exist_ok=True)
    (base / "job.json").write_text(json.dumps(
        {"schema": "card-3d/mesh3d-job@1", "node": "m1", "engine": "tripo",
         "run_id": "d" * 32, "status": "running", "progress": 50}),
        encoding="utf-8")

    # L'AUTRE moitié du garde-fou, celle qui ne doit PAS se déclencher : tant
    # que le marqueur de lancement est frais (la tâche de fond n'a pas encore
    # démarré — le serveur ne la lance qu'après l'envoi de la réponse), le job
    # est VIVANT et le poll doit le voir « running », pas « failed ».
    F9._MESH3D_RUNNING[(did, "m1")] = _t.monotonic()
    try:
        r0 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
        assert r0.status_code == 200 and r0.json()["status"] == "running", r0.text
        # ...et ce marqueur PÉRIME : sans péremption, un lancement dont la
        # tâche n'est jamais partie bloquerait le nœud jusqu'au redémarrage.
        F9._MESH3D_RUNNING[(did, "m1")] = _t.monotonic() - F9.MESH3D_LAUNCH_GRACE_S - 1
        assert F9._mesh3d_vivant(did, "m1") is False
    finally:
        F9._MESH3D_RUNNING.pop((did, "m1"), None)

    r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "interrompu" in r.json()["error"]
    # le motif dit CE QU'ON A CONSTATÉ (aucune tâche vivante), pas une cause
    # devinée : un redémarrage n'est qu'UNE des façons de perdre la tâche.
    assert r.json()["error"] == ("interrompu (aucune tache vivante) - "
                                 "relancer le noeud")
    # l'aveu est PERSISTÉ, pas seulement servi : un second appel le relit tel
    # quel (sinon l'écran verrait « running » à chaque rechargement).
    disque = json.loads((base / "job.json").read_text(encoding="utf-8"))
    assert disque["status"] == "failed" and "interrompu" in disque["error"]

    # ...et il est DÉFINITIF : le run_id est invalidé, donc un runner en retard
    # (envoi de réponse resté coincé au-delà de la péremption du marqueur) qui
    # démarrerait enfin ne peut PLUS contredire ce que l'écran vient de
    # montrer — sa clôture échoue et il abandonne SANS DÉPENSER.
    assert r.json()["run_id"] is None
    assert disque["run_id"] is None
    from app.services import asset3d_service as A3D

    async def jamais(*a, **k):
        raise AssertionError("un runner en retard ne doit RIEN depenser")

    monkeypatch.setattr(A3D, "_upload", jamais)
    monkeypatch.setattr(A3D, "_run_engine", jamais)
    fige = (base / "job.json").read_bytes()
    asyncio.run(F9._run_mesh3d(
        did, "m1", {"id": "m1", "kind": "mesh3d", "engine": "tripo",
                    "texture_prompt": "", "ultra": False}, "fal",
        {"role": "illustration", "side": "front",
         "file": "illustration_c01_front.png", "sha256": None}, "d" * 32))
    assert (base / "job.json").read_bytes() == fige, "l'aveu a ete contredit"


def test_le_marqueur_de_lancement_protege_le_job_qui_demarre(monkeypatch):
    """Le registre est posé PAR LA ROUTE, jamais seulement par la tâche : le
    serveur ne lance la tâche de fond qu'APRÈS l'envoi de la réponse, et sans
    ce marqueur un poll immédiat déclarerait ORPHELIN un job qui vient de
    partir. On neutralise la tâche de fond pour tenir cette fenêtre ouverte —
    ce qui donne du même coup le verrou de concurrence à mesurer."""
    from app.config import settings as cfg
    from app.services.cards import forge3d as F9

    async def _ne_fait_rien(*a, **k):
        return None

    monkeypatch.setattr(F9, "_run_mesh3d", _ne_fait_rien)
    monkeypatch.setattr(cfg, "MESHY_MOCK", True)
    did = _deck("Marqueur")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    try:
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        assert F9._mesh3d_vivant(did, "m1") is True, \
            "la route doit poser le marqueur AVANT de rendre sa reponse"
        # le poll voit « queued », JAMAIS l'aveu d'orphelin
        r2 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
        assert r2.status_code == 200 and r2.json()["status"] == "queued", r2.text
        # ...et un second lancement sur le MÊME nœud est refusé, nommé — deux
        # jobs concurrents écriraient le même dossier, le dernier gagnerait
        # en silence.
        r3 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r3.status_code == 409 and "job" in r3.json()["detail"], r3.text
    finally:
        F9._MESH3D_RUNNING.pop((did, "m1"), None)


def test_la_mesure_de_fermeture_refuse_motive_au_dela_de_la_borne(monkeypatch):
    """`closed` n'est mesuré qu'EN DEÇÀ d'une borne mémoire : au-delà, la
    mesure est REFUSÉE et NOMMÉE (closed None + note), jamais tentée en
    silence — `mesh_measures` alloue ~3 entrées de dictionnaire par triangle.
    Des octets qui ne sont pas un GLB dégradent de la même façon : le binaire
    est PAYÉ, il ne se perd pas pour un chiffre manquant."""
    from app.services.cards import forge3d as F9
    from app.services.cards import forge3d_scene as SC
    relief = SC.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0, 0.3, 8)
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(png, "PNG")
    glb = SC.write_scene_glb([{"name": "r", "mesh": relief, "png": png.getvalue(),
                               "alpha": False, "z_mm": 0.0}], name="r", extras={})
    closed, note, tris = F9._mesh3d_closed(glb)
    assert closed is True and note is None
    assert tris == len(relief["indices"]) // 3
    monkeypatch.setattr(F9, "MESH3D_CLOSED_TRI_MAX", 1)
    closed2, note2, tris2 = F9._mesh3d_closed(glb)
    assert closed2 is None and tris2 == tris
    # le motif est épinglé au LITTÉRAL : c'est ce texte que l'écran montre,
    # une reformulation silencieuse le rendrait incompréhensible.
    assert note2 == (f"fermeture non mesurée : maillage trop lourd "
                     f"({tris} triangles, plafond 1)"), note2
    monkeypatch.undo()
    closed3, note3, _ = F9._mesh3d_closed(b"pas un glb")
    assert closed3 is None and "mesur" in (note3 or "")


def test_le_lecteur_glb_extrait_un_maillage_et_nomme_ses_refus():
    """`read_glb` / `glb_scene_mesh` : l'extraction qui permet de mesurer
    `closed` sur un GLB de MOTEUR (octets tiers). Un GLB fermé écrit par notre
    writer se remesure fermé et au bon compte de triangles ; le triangle nu du
    simulateur Meshy (primitive NON INDEXÉE, licite au glTF 2.0) se mesure
    OUVERT ; des octets qui ne sont pas un GLB lèvent une ValueError NOMMÉE
    (que la route change en refus motivé, jamais en 500)."""
    from app.services import meshy_service as MS
    from app.services.cards import forge3d_scene as SC
    relief = SC.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0, 0.3, 8)
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(png, "PNG")
    glb = SC.write_scene_glb([{"name": "r", "mesh": relief, "png": png.getvalue(),
                               "alpha": False, "z_mm": 0.0}], name="r", extras={})
    m = SC.glb_scene_mesh(glb)
    rep = SC.mesh_measures(m)
    assert rep["closed"] is True, rep
    assert rep["triangles"] == len(relief["indices"]) // 3
    assert m["positions"] == pytest.approx(relief["positions"], abs=1e-3)

    # le GLB du simulateur : un triangle, donc OUVERT — et sa primitive n'a
    # AUCUN `indices` (tirage non indexé) : la refuser ferait échouer une
    # mesure parfaitement calculable.
    mm = SC.glb_scene_mesh(MS.tiny_glb())
    assert SC.mesh_measures(mm)["triangles"] == 1
    assert SC.mesh_measures(mm)["closed"] is False

    # read_glb : refus NOMMÉS, jamais une exception anonyme
    for octets in (b"junk", b"", b"glTF" + b"\x00" * 8):
        with pytest.raises(ValueError):
            SC.read_glb(octets)
    doc_len = struct.unpack("<I", glb[12:16])[0]
    with pytest.raises(ValueError):                 # chunk JSON tronqué
        SC.read_glb(glb[:20 + doc_len - 4])
    # un GLB SANS aucune primitive triangle (et sans chunk BIN) : refus nommé,
    # jamais un maillage vide rendu comme s'il était mesurable.
    js = json.dumps({"asset": {"version": "2.0"}, "meshes": []}).encode()
    js += b" " * (-len(js) % 4)
    creux = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js))
             + struct.pack("<II", len(js), 0x4E4F534A) + js)
    assert SC.read_glb(creux)[1] == b""              # pas de chunk BIN : b""
    with pytest.raises(ValueError):
        SC.glb_scene_mesh(creux)
    # un indice qui dépasse le compte de sommets : refusé ICI, sinon
    # `mesh_measures` lèverait un IndexError nu — donc un 500 chez l'appelant.
    faux = SC.write_scene_glb(
        [{"name": "f", "png": png.getvalue(), "alpha": False, "z_mm": 0.0,
          "mesh": {"positions": [0.0] * 9, "normals": [0.0, 0.0, 1.0] * 3,
                   "uvs": [0.0] * 6, "indices": [0, 1, 9]}}],
        name="f", extras={})
    with pytest.raises(ValueError):
        SC.glb_scene_mesh(faux)


def test_la_matiere_habille_l_element_et_les_maps_sont_cuites():
    """normal/MR/ao câblées ; le pack MR suit la convention glTF (G=rugosité,
    B=métal — doctrine pbr_service) ; relu dans les OCTETS du GLB."""
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (200, 30, 30, 255)).save(png, "PNG")
    maps = {
        "normal": Image.new("RGB", (16, 16), (128, 128, 255)),
        "roughness": Image.new("L", (16, 16), 64),
        "metallic": Image.new("L", (16, 16), 255),
        "ao": Image.new("L", (16, 16), 200),
    }
    el = {"name": "cadre", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": True, "z_mm": 0.0,
          "mat_maps": SC.material_pngs(maps)}
    glb = SC.write_scene_glb([el], name="x", extras={"unit": "metre"})
    doc, binv = _read_glb(glb)
    m = doc["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in pbr and "normalTexture" in m
    assert "occlusionTexture" in m
    # quand une map MR existe, les FACTEURS repassent à 1.0 (les niveaux sont
    # dans la map — convention pbr_service)
    assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0
    # relire le PNG MR du buffer : G=64 (rugosité), B=255 (métal)
    img_idx = doc["textures"][pbr["metallicRoughnessTexture"]["index"]]["source"]
    bv = doc["bufferViews"][doc["images"][img_idx]["bufferView"]]
    mr_png = binv[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
    px = Image.open(io.BytesIO(mr_png)).convert("RGB").getpixel((4, 4))
    assert px[1] == 64 and px[2] == 255
    # et le sampler reste CLAMP (le tuilage est CUIT, pas répété)
    for s in doc["samplers"]:
        assert s["wrapS"] == 33071 and s["wrapT"] == 33071

    # UNE FINITION SAUTE LE PACK MR (décision de revue Task 5). glTF MULTIPLIE
    # facteur x texture : garder les deux donnerait rugosité = 0,12 x G/255 —
    # une dorure posée sur une matière mate virerait au miroir noir, l'inverse
    # de ce que les deux réglages disent séparément. Sémantique : la feuille
    # holo REMPLACE la micro-surface, le RELIEF et l'OCCLUSION parlent encore.
    el2 = dict(el, name="sceau",
               finish=SC.holo_finish("dorure", aniso=False, out_px=64))
    doc2, _ = _read_glb(SC.write_scene_glb([el2], name="x", extras={}))
    m2 = doc2["materials"][0]
    pbr2 = m2["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" not in pbr2          # sauté, pas empilé
    assert pbr2["roughnessFactor"] == 0.12 and pbr2["metallicFactor"] == 1.0
    assert pbr2["baseColorFactor"] == [1.0, 0.84, 0.55, 1.0]
    assert "normalTexture" in m2 and "occlusionTexture" in m2   # relief + AO
    # la map MR n'est même plus EMBARQUÉE : rien ne la référencerait
    assert not any(im["name"].endswith("-mr") for im in doc2["images"])


def test_tile_maps_tuile_au_pas_physique_et_reste_deterministe(monkeypatch):
    """Une matière de la boutique, tuilée à tile_mm sur le ratio carte :
    mêmes octets à chaque appel ; le motif se répète au pas attendu.
    (tile_maps vit dans forge3d.py — décision de pureté du module scène.)

    COTES À DIVISION EXACTE (correctif de revue Task 5) : 64x128 mm, pas de
    32 mm, 256 px -> toile 128x256, tuile de 64 px. La première version
    comparait x et x + W//2 sur 183 px de large pour une tuile de 92 — DEUX
    TEXELS QUI NE SE CORRESPONDENT PAS, d'un texel près ; l'assertion ne
    tenait que parce que la map demandée (`roughness`) était UNIFORME. Ici on
    compare des TUILES ENTIÈRES, sur la map qui porte vraiment un motif."""
    from app.services import material_store as MSTORE
    from app.services.cards import forge3d as F9
    mat = MSTORE.create_material(name="essai-2b")
    try:
        tuile = Image.new("RGB", (64, 64), (10, 10, 10))
        tuile.paste(Image.new("RGB", (8, 8), (250, 250, 250)), (0, 0))
        MSTORE.save_maps(mat["id"], {"basecolor": tuile,
                                     "roughness": Image.new("L", (64, 64), 100)})
        a = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=32.0,
                         w_mm=64.0, h_mm=128.0, out_px=256)
        b = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=32.0,
                         w_mm=64.0, h_mm=128.0, out_px=256)
        assert a["basecolor"].tobytes() == b["basecolor"].tobytes()
        im = a["basecolor"]
        assert im.size == (128, 256)          # ratio carte, division exacte
        # 64 mm / 32 mm = 2 tuiles de 64 px : les tuiles voisines sont
        # identiques OCTET POUR OCTET, à l'horizontale comme à la verticale.
        coin = im.crop((0, 0, 64, 64)).tobytes()
        assert im.crop((64, 0, 128, 64)).tobytes() == coin
        assert im.crop((0, 64, 64, 128)).tobytes() == coin
        # ...et le motif est bien LÀ : sans ça les égalités ci-dessus seraient
        # vraies d'une toile unie (le piège exact de la version précédente).
        assert im.getpixel((2, 2))[0] > im.getpixel((40, 40))[0] + 100
        import pytest as _pt
        # matière introuvable -> ValueError nommée
        with _pt.raises(ValueError):
            F9.tile_maps("mat_inexistant00", ("basecolor",), 63.0, 63.0, 88.0)
        # cote nulle, négative, ou PAS NUMÉRIQUE : refus NOMMÉ — jamais un
        # ZeroDivisionError ni un TypeError nus (ce serait un 500).
        for cotes in ((0.0, 63.0, 88.0), (31.5, -1.0, 88.0),
                      (31.5, 63.0, 0.0), ("31,5", 63.0, 88.0)):
            with _pt.raises(ValueError):
                F9.tile_maps(mat["id"], ("basecolor",), *cotes)
        # out_px borné au MÊME plafond que les finitions (bornes symétriques)
        gros = F9.tile_maps(mat["id"], ("basecolor",), 32.0, 64.0, 64.0,
                            out_px=99999)["basecolor"]
        assert gros.size == (F9.HOLO_PX[1], F9.HOLO_PX[1]) == (2048, 2048)
        # LA BORNE DE L'ALLOCATION DÉRIVÉE (résidu de re-revue Task 5) : à
        # tile_mm=200 sur une carte mini de 31,75 mm, `W x tile_mm / w_mm`
        # visait 12 900 px de côté — une tuile de ~500 Mo en RGB, depuis des
        # entrées PARFAITEMENT LÉGALES (les deux sont dans les bornes
        # publiées). Le pixel rendu, lui, ne change pas d'un poil : une tuile
        # plus grande que la toile est collée UNE fois puis rognée. La seule
        # trace observable est donc la taille DEMANDÉE au rééchantillonnage —
        # espionnée ici, faute de quoi la borne ne serait qu'un commentaire.
        demandes = []
        vrai_resize = Image.Image.resize

        def resize_espion(self, size, *a, **kw):
            demandes.append(tuple(size))
            return vrai_resize(self, size, *a, **kw)

        monkeypatch.setattr(Image.Image, "resize", resize_espion)
        petit = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=200.0,
                             w_mm=31.75, h_mm=44.45, out_px=256)["basecolor"]
        monkeypatch.undo()
        assert petit.size == (183, 256)      # ratio de la carte mini
        assert demandes, "aucun reechantillonnage observe"
        assert max(max(s) for s in demandes) <= max(petit.size), demandes
    finally:
        MSTORE.delete_material(mat["id"])


def test_les_finitions_holo_suivent_la_recette_et_restent_optionnelles():
    """§6.2bis-c : extensions dans extensionsUsed UNIQUEMENT, facteurs exacts,
    épaisseur en secteurs radiaux relue dans le canal G, TANGENT présent quand
    l'anisotropie est demandée, clearcoat posé. Déterminisme prouvé."""
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (220, 220, 220, 255)).save(png, "PNG")
    f1 = SC.holo_finish("argent", aniso=True, out_px=256)
    f2 = SC.holo_finish("argent", aniso=True, out_px=256)
    assert f1["iridescence"]["png"] == f2["iridescence"]["png"]   # mêmes octets
    el = {"name": "sceau", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": False, "z_mm": 0.0, "finish": f1}
    glb = SC.write_scene_glb([el], name="x", extras={"unit": "metre"})
    doc, binv = _read_glb(glb)
    assert "extensionsRequired" not in doc
    assert set(doc["extensionsUsed"]) == {"KHR_materials_iridescence",
                                          "KHR_materials_clearcoat",
                                          "KHR_materials_anisotropy"}
    m = doc["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert pbr["baseColorFactor"] == [0.95, 0.95, 0.97, 1.0]
    assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 0.12
    iri = m["extensions"]["KHR_materials_iridescence"]
    assert iri["iridescenceFactor"] == 1.0 and iri["iridescenceIor"] == 1.8
    assert iri["iridescenceThicknessMinimum"] == 200.0
    assert iri["iridescenceThicknessMaximum"] == 900.0
    cc = m["extensions"]["KHR_materials_clearcoat"]
    assert cc["clearcoatFactor"] == 1.0 and cc["clearcoatRoughnessFactor"] == 0.06
    ani = m["extensions"]["KHR_materials_anisotropy"]
    assert ani["anisotropyStrength"] == 0.85 and "anisotropyTexture" in ani
    # TANGENT écrit (VEC4, un par sommet)
    prim = doc["meshes"][0]["primitives"][0]
    assert "TANGENT" in prim["attributes"]
    acc = doc["accessors"][prim["attributes"]["TANGENT"]]
    assert acc["type"] == "VEC4" and acc["count"] == 4
    # LE SIGNE DE w : -1, PAS +1 — relu dans les OCTETS, pas déduit du code.
    # Nos UV sont inversées en v (`quad_mesh`), donc dP/dv = -y quand
    # cross(N, T) = cross(+z, +x) = +y : la règle glTF (w = signe de
    # dot(cross(N,T), B)) donne -1, ce que `gltf_builder.py:485` calcule déjà
    # pour les maillages du dépôt. Avec +1 le champ anisotrope devient RADIAL
    # sur les diagonales et le vert d'une normal map s'inverse.
    bvt = doc["bufferViews"][acc["bufferView"]]
    offt = bvt.get("byteOffset", 0) + acc.get("byteOffset", 0)
    for k in range(acc["count"]):
        tx, ty, tz, tw = struct.unpack_from("<4f", binv, offt + k * 16)
        assert (tx, ty, tz) == (1.0, 0.0, 0.0), (k, tx, ty, tz)
        assert tw == -1.0, (k, tw)
    assert acc["min"][3] == -1.0 and acc["max"][3] == -1.0
    # l'épaisseur varie AUTOUR du centre : 4 angles -> >= 3 valeurs G distinctes
    img_idx = doc["textures"][iri["iridescenceThicknessTexture"]["index"]]["source"]
    bv = doc["bufferViews"][doc["images"][img_idx]["bufferView"]]
    tex = Image.open(io.BytesIO(binv[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]))
    cx = cy = tex.size[0] // 2
    r = tex.size[0] // 3
    gs = {tex.getpixel((cx + r, cy))[1], tex.getpixel((cx - r, cy))[1],
          tex.getpixel((cx, cy + r))[1], tex.getpixel((cx + int(r * 0.7), cy + int(r * 0.7)))[1]}
    assert len(gs) >= 3, gs
    # LE PEIGNE EST TANGENT AU PÉRIMÈTRE, pas radial : le produit scalaire
    # (R-127,5 ; G-127,5).(dx ; dy) est nul aux arrondis près (borne exacte :
    # 0,5 par canal). Un champ RADIAL — une texture d'anisotropie qui porterait
    # la DIRECTION du rayon au lieu de sa perpendiculaire — y donnerait
    # ~127,5 x r, deux ordres de grandeur plus haut.
    #
    # RECTIFICATIF (re-revue Task 5) : cet assert et le `tw == -1` ci-dessus
    # sont COMPLÉMENTAIRES, pas redondants — ne jamais supprimer le second en
    # le croyant couvert par celui-ci. Ils mesurent deux objets différents :
    # `tw` épingle la MAIN du repère tangent (l'attribut du maillage), celui-ci
    # épingle le CHAMP dans l'espace des pixels (les octets de la texture). Une
    # tangente de mauvaise main laisse cette texture PARFAITEMENT
    # perpendiculaire — elle ne la touche pas — et ne se voit que sur `tw` ;
    # inversement une texture radiale passerait le `tw`. Il faut les deux.
    i_ani = doc["textures"][ani["anisotropyTexture"]["index"]]["source"]
    bva = doc["bufferViews"][doc["images"][i_ani]["bufferView"]]
    tex_a = Image.open(io.BytesIO(
        binv[bva["byteOffset"]:bva["byteOffset"] + bva["byteLength"]]))
    ca = tex_a.size[0] // 2
    for dx, dy in ((60, 0), (0, 60), (42, 42), (-42, 42), (-55, -20),
                   (30, -70), (-70, 30)):
        rr, gg, bb = tex_a.getpixel((ca + dx, ca + dy))[:3]
        scal = (rr - 127.5) * dx + (gg - 127.5) * dy
        assert abs(scal) <= 0.5 * (abs(dx) + abs(dy)) + 1.0, (dx, dy, scal)
        # et le canal B reste à 255 : l'extension MULTIPLIE la force par lui,
        # à 0 la finition serait invisible partout (amendement Task 5).
        assert bb == 255, (dx, dy, bb)
    # la dorure a SA recette
    fd = SC.holo_finish("dorure", aniso=False, out_px=128)
    assert fd["pbr"]["baseColorFactor"] == [1.0, 0.84, 0.55, 1.0]
    assert fd["iridescence"]["ior"] == 1.6
    assert fd["iridescence"]["thickness"] == [200.0, 600.0]
    assert fd.get("anisotropy") is None
    # SANS finition ni matière : AUCUNE extension n'apparaît (dégradation
    # propre : un GLB 2a reste un GLB 2a)
    el2 = {"name": "nu", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
           "alpha": True, "z_mm": 0.0}
    doc2, _ = _read_glb(SC.write_scene_glb([el2], name="x", extras={}))
    assert "extensionsUsed" not in doc2 and "extensions" not in doc2["materials"][0]
    # LES DEUX GARDES, PROUVÉES et pas seulement écrites (revue Task 5) : une
    # finition inconnue est REFUSÉE (la remplacer en douce par l'argent
    # livrerait une carte fausse sans que personne le sache), et out_px est
    # ramené au plafond §6.2bis au lieu de cuire 4096² pour rien.
    with pytest.raises(ValueError):
        SC.holo_finish("cuivre", aniso=False, out_px=128)
    borne = SC.holo_finish("argent", aniso=False, out_px=99999)
    assert Image.open(io.BytesIO(borne["iridescence"]["png"])).size == \
        (SC.HOLO_PX[1], SC.HOLO_PX[1]) == (2048, 2048)
    assert Image.open(io.BytesIO(
        SC.holo_finish("argent", aniso=False, out_px=1)["iridescence"]["png"]
    )).size == (SC.HOLO_PX[0], SC.HOLO_PX[0])


def test_l_anisotropie_exige_un_maillage_aux_uv_alignees():
    """Garde Task 6 : la tangente CONSTANTE du writer n'est vraie que sur les
    maillages du lab (plans et reliefs, u sur +x). Sur un maillage de moteur
    (mesh3d, UV dépaquetées par un atlas) elle peignerait n'importe comment —
    refus NOMMÉ plutôt qu'un reflet faux livré sans un mot."""
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (7, 7, 7, 255)).save(png, "PNG")
    # les maillages du lab PORTENT le drapeau, les deux
    assert SC.quad_mesh(63.0, 88.0)["uv_axis_aligned"] is True
    assert SC.relief_mesh(Image.new("L", (8, 8), 255), 63.0, 88.0,
                          1.0, 0.3, 4)["uv_axis_aligned"] is True
    etranger = {"positions": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0],
                "normals": [0.0, 0.0, 1.0] * 3, "uvs": [0.0] * 6,
                "indices": [0, 1, 2]}
    base = {"name": "moteur", "mesh": etranger, "png": png.getvalue(),
            "alpha": False, "z_mm": 0.0}
    with pytest.raises(ValueError) as e:
        SC.write_scene_glb([dict(base, finish=SC.holo_finish(
            "argent", aniso=True, out_px=64))], name="x", extras={})
    assert "uv" in str(e.value).lower()
    # SANS anisotropie, le même maillage étranger passe : ni l'iridescence ni
    # le clearcoat n'ont besoin d'une tangente.
    doc, _ = _read_glb(SC.write_scene_glb(
        [dict(base, finish=SC.holo_finish("argent", aniso=False, out_px=64))],
        name="x", extras={}))
    assert set(doc["extensionsUsed"]) == {"KHR_materials_iridescence",
                                          "KHR_materials_clearcoat"}
    assert "TANGENT" not in doc["meshes"][0]["primitives"][0]["attributes"]
    # un paquet de finition MAL FORMÉ dégrade en « pas de finition » : jamais
    # un .get sur un booléen, jamais un 500 sur une donnée d'entrée. ET IL NE
    # DOIT RIEN EMPORTER AVEC LUI (résidu de re-revue Task 5) : le saut de la
    # map MR est conditionné à une RECETTE présente (`pbr` en dict), pas à la
    # simple vérité du dictionnaire — sans quoi une seule donnée douteuse
    # dégradait DEUX fois, la finition perdue ET la matière valide jetée.
    maps_temoin = SC.material_pngs({"roughness": Image.new("L", (8, 8), 90),
                                    "metallic": Image.new("L", (8, 8), 200)})
    doc2, binv2 = _read_glb(SC.write_scene_glb(
        [dict(base, mat_maps=maps_temoin,
              finish={"anisotropy": True, "clearcoat": "oui",
                      "iridescence": None, "pbr": 3})],
        name="x", extras={}))
    assert "extensions" not in doc2["materials"][0]
    assert "extensionsUsed" not in doc2
    # la map MR a SURVÉCU au paquet poubelle — et ce sont bien SES octets
    pbr2 = doc2["materials"][0]["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in pbr2
    assert pbr2["metallicFactor"] == 1.0 and pbr2["roughnessFactor"] == 1.0
    i2 = doc2["textures"][pbr2["metallicRoughnessTexture"]["index"]]["source"]
    bv2 = doc2["bufferViews"][doc2["images"][i2]["bufferView"]]
    px2 = Image.open(io.BytesIO(
        binv2[bv2["byteOffset"]:bv2["byteOffset"] + bv2["byteLength"]])
    ).convert("RGB").getpixel((2, 2))
    assert px2[1] == 90 and px2[2] == 200


def test_les_textures_de_finition_sont_mutualisees_pas_celles_des_couches():
    """Deux éléments finis à la MÊME recette portent les mêmes octets
    d'iridescence : les embarquer deux fois double le GLB pour rien. Le
    partage s'arrête aux textures de matière et de finition — le PNG de
    COUCHE garde son image propre, même identique à celle du voisin
    (l'identité des couches est un contrat de la 2a)."""
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    fin = SC.holo_finish("argent", aniso=True, out_px=64)
    els = [{"name": f"s{i}", "mesh": SC.quad_mesh(63.0, 88.0),
            "png": png.getvalue(), "alpha": False, "z_mm": float(i),
            "finish": fin} for i in range(3)]
    doc, _ = _read_glb(SC.write_scene_glb(els, name="x", extras={}))
    noms = [im["name"] for im in doc["images"]]
    # 3 couches distinctes + 1 iridescence + 1 anisotropie, PAS 3 + 3 + 3
    assert noms == ["s0", "s0-iridescence", "s0-anisotropie", "s1", "s2"], noms
    # ...et les trois matériaux visent bien LA texture partagée
    cibles = {doc["materials"][i]["extensions"]
              ["KHR_materials_iridescence"]["iridescenceThicknessTexture"]["index"]
              for i in range(3)}
    assert len(cibles) == 1, cibles
    # chaque élément garde SA propre couche
    bases = {doc["materials"][i]["pbrMetallicRoughness"]
             ["baseColorTexture"]["index"] for i in range(3)}
    assert len(bases) == 3, bases


def test_le_transform_porte_le_trs_du_noeud():
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(png, "PNG")
    el = {"name": "e", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": True, "z_mm": 0.0,
          "trs": {"translate": [5.0, -3.0, 2.0], "rotate_deg": 90.0, "scale": 2.0}}
    doc, _ = _read_glb(SC.write_scene_glb([el], name="x", extras={}))
    node = doc["nodes"][0]
    assert node["translation"] == [5.0, -3.0, 2.0]
    assert node["scale"] == [2.0, 2.0, 2.0]
    q = node["rotation"]                      # quaternion z pour 90°
    assert abs(q[2] - 0.7071067811865476) < 1e-12 and abs(q[3] - 0.7071067811865476) < 1e-12
    assert q[0] == 0.0 and q[1] == 0.0


# ── LA FUSION DES GLB EXTERNES (Task 6) — chaînes, STL mixte, moteurs ───────
# AUCUN de ces tests ne dépense un crédit ni ne touche le réseau : le « GLB du
# moteur » est écrit par NOTRE writer (bornes connues par construction) ou
# fabriqué à la main, et le job `served` est POSÉ sur disque exactement comme
# `_run_mesh3d` l'aurait écrit.

def _dossier_forge3d(did):
    """`.../forge3d` du deck, par le chemin du domaine (contract.deck_dir) —
    jamais une recomposition locale qui dériverait."""
    from app.services.cards.contract import deck_dir
    return deck_dir(did) / "forge3d"


def _job_servi(did, nid, glb: bytes, closed, engine="meshy-7", credits=None,
               note=None, octets=None, source=None):
    """Pose un nœud mesh3d SERVI sur disque, avec la forme EXACTE de job.json
    qu'écrit `_run_mesh3d` (Task 4) — `bytes` compris : c'est LUI que le gate
    de taille de la fusion relit, sans ouvrir le fichier. `octets` permet de
    mentir sur cette taille (le gate doit croire le job, pas le disque)."""
    base = _dossier_noeud(did, nid)
    (base / "textures").mkdir(parents=True, exist_ok=True)
    (base / "model.glb").write_bytes(glb)
    job = {"schema": "card-3d/mesh3d-job@1", "node": nid, "engine": engine,
           "provider": "meshy" if str(engine).startswith("meshy") else "fal",
           "run_id": "essai-" + nid, "status": "served", "progress": 100,
           "step": "Livré", "error": None, "closed": closed,
           "closed_note": note, "triangles": 0,
           "bytes": len(glb) if octets is None else int(octets),
           "files": {"glb": "model.glb"}}
    if credits is not None:
        job["consumed_credits"] = credits
    if source is not None:
        # `source` dit de QUELLE couche ce GLB est né (la route l'écrit au
        # lancement) — le laisser absent garde le comportement historique des
        # tests qui ne s'y intéressent pas.
        job["source"] = source
    (base / "job.json").write_text(json.dumps(job, ensure_ascii=False),
                                   encoding="utf-8")
    return job


def _glb_bricole(**surcharges):
    """Un GLB minimal VALIDE (un triangle indexé, un matériau), surchargé clé
    par clé — le laboratoire des cas que NOS writers ne produisent jamais
    (ressources externes, exigences exotiques, hiérarchies absurdes)."""
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                       "indices": 1, "material": 0}]}],
           "materials": [{"name": "moteur"}],
           "accessors": [
               {"componentType": 5126, "count": 3, "type": "VEC3",
                "bufferView": 0, "min": [0, 0, 0], "max": [1, 1, 0]},
               {"componentType": 5125, "count": 3, "type": "SCALAR",
                "bufferView": 1}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                           {"buffer": 0, "byteOffset": 36, "byteLength": 12}],
           "buffers": [{"byteLength": 48}]}
    doc.update(surcharges)
    binv = (struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0.5, 1, 0)
            + struct.pack("<3I", 0, 1, 2))
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    return (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binv))
            + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binv), 0x004E4942) + binv)


def _stl_bbox(stl: bytes):
    """(min, max) par axe des sommets d'un STL binaire — LA PLACE RÉELLE de ce
    qui sera imprimé, la seule qui puisse contredire celle du GLB."""
    n = struct.unpack("<I", stl[80:84])[0]
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for k in range(84, 84 + 50 * n, 50):
        for s in range(3):
            v = struct.unpack_from("<3f", stl, k + 12 + s * 12)
            for c in range(3):
                lo[c] = min(lo[c], v[c])
                hi[c] = max(hi[c], v[c])
    return lo, hi


def _glb_externe_63x88():
    """L'« externe » des tests : un relief FERMÉ écrit par notre writer, aux
    cotes CONNUES 63x88x(0,3..1,3) — le fit attendu se calcule donc de tête."""
    from app.services.cards import forge3d_scene as SC
    relief = SC.relief_mesh(Image.new("L", (8, 8), 255), 63.0, 88.0, 1.0,
                            0.3, 4)
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    return SC.write_scene_glb([{"name": "brut", "mesh": relief,
                                "png": png.getvalue(), "alpha": False,
                                "z_mm": 0.0}], name="brut", extras={})


def test_l_assemblage_fusionne_le_glb_externe_a_sa_place_de_couche():
    """Chaîne layer->mesh3d->transform->assemble : l'élément externe est
    réindexé sous un parent au TRS calculé (ajusté à la BOÎTE MM de sa couche,
    centré, à z du transform), l'identité du doc externe est jetée, les
    accesseurs restent exacts, le STL mixte sort quand tout est fermé."""
    did = _deck("Fusion")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="meshy-7",
               credits=30)

    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": "meshy-7",
         "texture_prompt": "", "ultra": False},
        {"id": "tr", "kind": "transform", "x_mm": 0, "y_mm": 0, "z_mm": 2.0,
         "rot_deg": 0, "scale": 1.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "fusion3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "tr"},
                  {"from": "tr", "to": "asm"}, {"from": "s2", "to": "t2"},
                  {"from": "t2", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, binv = _read_glb(glb)
    # l'identité du document externe est JETÉE : le nôtre n'en émet aucune, le
    # sien n'en apporte pas.
    plat = json.dumps(doc)
    for mot in ("generator", "copyright", "author", "producer"):
        assert f'"{mot}"' not in plat, mot
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    # DEUX enfants de racine, et deux SEULEMENT : les nœuds INTERNES du GLB
    # externe restent sous SON parent — les hisser au rang de racine ferait
    # exploser la carte en pièces détachées, chacune à l'origine.
    assert sorted(noms) == ["cadre", "illustration"], noms
    parent_ext = doc["nodes"][racine["children"][noms.index("illustration")]]
    assert [doc["nodes"][k]["name"] for k in parent_ext["children"]] == ["brut"]
    # LE FIT, RECALCULÉ DEPUIS LE MANIFESTE : la boîte de la couche
    # illustration est mesurée à l'export (champ `bbox_mm`, repère TOILE —
    # origine au coin de toile, y vers le BAS, fond perdu compris) ; l'externe
    # (63x88) y est mis à l'échelle, centré, et posé à z du transform.
    man = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/layers_c01_front.json").content)
    boite = next(l for l in man["layers"]
                 if l["role"] == "illustration")["bbox_mm"]
    bw = boite[2] - boite[0]
    bh = boite[3] - boite[1]
    # NOTE D'ÉCHELLE, et ce n'est PAS un détail : ce faux-moteur est écrit par
    # NOTRE writer, dont la racine porte le mm->m (0,001). Sa scène mesure donc
    # 0,063 x 0,088, pas 63 x 88 — et c'est la taille RENDUE que le fit doit
    # mesurer. Un fit calculé sur les positions BRUTES rendrait ici une pièce
    # mille fois trop petite dans un GLB structurellement irréprochable.
    mw, mh = 63.0 * 0.001, 88.0 * 0.001
    s = min(bw / mw, bh / mh)
    assert abs(parent_ext["scale"][0] - s) < 1e-9
    assert parent_ext["scale"] == [parent_ext["scale"][0]] * 3   # UNIFORME
    # TOUT le z vient du transform (le fit ne le compte pas deux fois) : la
    # base de l'externe est à z=0, donc translation z == 2.0 EXACTEMENT.
    assert abs(parent_ext["translation"][2] - 2.0) < 1e-9
    # ...et le centrage est celui de la boîte RAMENÉE au repère COUPE du
    # maillage (origine coin de coupe, y vers le HAUT) : sans ce changement de
    # repère, l'élément serait décalé du fond perdu sur les deux axes.
    saignee = man["bleed_mm"]
    cx = (boite[0] + boite[2]) / 2.0 - saignee - s * mw / 2.0
    cy = (man["canvas_mm"][1] - (boite[1] + boite[3]) / 2.0) - saignee - s * mh / 2.0
    assert abs(parent_ext["translation"][0] - cx) < 1e-6
    assert abs(parent_ext["translation"][1] - cy) < 1e-6
    # BORNES DES ACCESSEURS DU DOC FUSIONNÉ : toujours EXACTES (re-mesurées
    # ici, pas relues du document) — la recopie vue par vue décale les
    # offsets, elle ne doit toucher NI les octets NI les bornes.
    vus = 0
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126 or "min" not in acc:
            continue
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
        lo = [float("inf")] * n
        hi = [float("-inf")] * n
        for e2 in range(acc["count"]):
            vals = struct.unpack_from("<" + "f" * n, binv, off + e2 * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c])
                hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi, acc
        vus += 1
    assert vus >= 6, vus            # 3 par élément au minimum, deux éléments
    # RÉINDEXATION PROUVÉE : le matériau du maillage externe vise SON image
    # (celle embarquée avec lui), pas celle du voisin local — un indice oublié
    # au décalage donnerait un GLB parfaitement valide montrant la mauvaise
    # texture, ce qu'aucun contrôle de structure ne verrait.
    # (le faux-moteur est un GLB de NOTRE writer : sous son parent de fusion
    # vient SA racine mm->m, et sous elle seulement le nœud porteur du mesh —
    # la hiérarchie interne est GARDÉE telle quelle, pas aplatie)
    n_brut = doc["nodes"][doc["nodes"][parent_ext["children"][0]]["children"][0]]
    prim = doc["meshes"][n_brut["mesh"]]["primitives"][0]
    tex_ext = doc["materials"][prim["material"]]["pbrMetallicRoughness"][
        "baseColorTexture"]["index"]
    assert doc["images"][doc["textures"][tex_ext]["source"]]["name"] == "brut"
    # ...et son SAMPLER est le SIEN, ajouté, jamais notre CLAMP recyclé
    tex_loc = doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    assert doc["textures"][tex_loc]["sampler"] == 0
    assert doc["textures"][tex_ext]["sampler"] != 0
    assert len(doc["samplers"]) >= 2
    # metadata : les moteurs RÉELLEMENT utilisés, mesurés
    meta = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["engines"] == "local+meshy-7"
    assert types["elements_3d"] == 2
    # le bordereau dit QUI est local et QUI vient d'un moteur, et ce qu'il a coûté
    detail = {e["name"]: e for e in b["elements_detail"]}
    assert detail["cadre"]["kind"] == "local"
    assert detail["illustration"]["kind"] == "externe"
    assert detail["illustration"]["engine"] == "meshy-7"
    assert detail["illustration"]["credits"] == 30
    assert b["elements"] == 2
    # STL : les DEUX éléments sont fermés -> écrit, longueur exacte
    assert b["stl"]["written"] is True, b["stl"]
    stl = _api("GET", f"/api/cards/{did}/forge3d/file/{b['stl']['name']}").content
    n_tri = struct.unpack("<I", stl[80:84])[0]
    assert len(stl) == 84 + 50 * n_tri
    # LE MAILLAGE EXTERNE EST DANS LE STL, ET À SA PLACE. Le compte : celui
    # des deux éléments réunis — mesuré en rebâtissant le MÊME graphe amputé
    # de sa chaîne moteur (aucun chiffre recopié à la main).
    from app.services.cards import forge3d_scene as SC
    ext_tris = len(SC.glb_scene_mesh(_glb_externe_63x88())["indices"]) // 3
    g_local = {"nodes": [n for n in g["nodes"] if n["id"] not in ("s1", "m1", "tr")],
               "edges": [e for e in g["edges"]
                         if e["from"] not in ("s1", "m1", "tr")]}
    g_local["nodes"] = [dict(n, name="fusion3d_local") if n["kind"] == "artifact"
                        else n for n in g_local["nodes"]]
    r_l = _api("POST", f"/api/cards/{did}/forge3d/build3d",
               json={"graph": g_local, "card": 0})
    assert r_l.status_code == 200, r_l.text
    stl_l = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                 + r_l.json()["artifact"]["stl"]["name"]).content
    assert n_tri == struct.unpack("<I", stl_l[80:84])[0] + ext_tris
    # ...et à SA place : l'externe est posé à z=2.0 + son épaisseur mise à
    # l'échelle, bien au-dessus du relief local (qui plafonne à 1,3 mm).
    zmax = max(max(struct.unpack_from("<f", stl, k + 20)[0],
                   struct.unpack_from("<f", stl, k + 32)[0],
                   struct.unpack_from("<f", stl, k + 44)[0])
               for k in range(84, 84 + 50 * n_tri, 50))
    assert abs(zmax - (2.0 + s * 1.3 * 0.001)) < 1e-3, zmax
    # ── LE MANIFESTE FAIT FOI pour le changement de repère (M6) : la toile et
    # le fond perdu viennent de LUI, pas d'une re-dérivation depuis la
    # géométrie courante. Preuve : on rallonge la toile DÉCLARÉE de 10 mm et
    # le placement suit, exactement de 10 mm en y (une re-dérivation ne
    # bougerait pas d'un cheveu).
    p_man = _dossier_forge3d(did) / "layers_c01_front.json"
    doctore = json.loads(p_man.read_text(encoding="utf-8"))
    doctore["canvas_mm"] = [doctore["canvas_mm"][0],
                            doctore["canvas_mm"][1] + 10.0]
    p_man.write_text(json.dumps(doctore), encoding="utf-8")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 200, r2.text
    doc2, _ = _read_glb(_api(
        "GET", "/api/cards/" + did + "/forge3d/file/"
        + r2.json()["artifact"]["glb"]["name"]).content)
    rac2 = doc2["nodes"][doc2["scenes"][0]["nodes"][0]]
    noms2 = [doc2["nodes"][k]["name"] for k in rac2["children"]]
    p2 = doc2["nodes"][rac2["children"][noms2.index("illustration")]]
    assert abs(p2["translation"][1] - (cy + 10.0)) < 1e-6
    assert abs(p2["translation"][0] - cx) < 1e-6      # x : inchangé


def test_un_noeud_mesh3d_sans_glb_servi_refuse_l_assemblage():
    did = _deck("Trou")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 409, r.text
    assert "m1" in r.json()["detail"] and "servi" in r.json()["detail"]


def test_le_stl_mixte_refuse_un_externe_ouvert_ou_non_mesure():
    """Le gate STL relit le `closed` CACHÉ au job (jamais une re-mesure) :
    `False` refuse pour non-fermeture, `None` refuse pour non-MESURE, avec la
    note du job — deux motifs distincts, jamais le même message recyclé."""
    from app.services.cards import forge3d_scene as SC
    did = _deck("Ouvert")
    _exporter_couches(did)
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    q = SC.quad_mesh(63.0, 88.0)
    ext = SC.write_scene_glb([{"name": "plan", "mesh": q,
                               "png": png.getvalue(), "alpha": True,
                               "z_mm": 0.0}], name="p", extras={})
    _job_servi(did, "m1", ext, closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    assert b["stl"]["written"] is False and "ferm" in b["stl"]["why"]
    assert "m1" in b["stl"]["why"] or "illustration" in b["stl"]["why"]
    # un graphe SANS aucun élément local : les moteurs seuls font le metadata
    meta = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["engines"] == "meshy-7" and types["elements_3d"] == 1
    # closed=None (non mesuré) refuse aussi, motif DIFFÉRENT — et la note du
    # job voyage jusqu'au bordereau (le « pourquoi » du pourquoi).
    _job_servi(did, "m1", ext, closed=None,
               note="fermeture non mesurée : maillage trop lourd (2 triangles)")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 200, r2.text
    pourquoi = r2.json()["artifact"]["stl"]
    assert pourquoi["written"] is False
    assert "mesur" in pourquoi["why"] and "trop lourd" in pourquoi["why"]
    assert pourquoi["why"] != b["stl"]["why"]


def test_le_rebuild_efface_l_apercu_perime():
    """Legs 4 : rebâtir `carte3d` supprime carte3d_preview.png — le metadata
    ne montre plus jamais l'aperçu d'un GLB qui n'existe plus."""
    did = _deck("Perime")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    fdir = _dossier_forge3d(did)
    (fdir / "carte3d_preview.png").write_bytes(_png(Image.new("RGBA", (4, 4))))
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    assert not (fdir / "carte3d_preview.png").exists()
    # le bordereau reste HONNÊTE : l'aperçu est attendu, pas écrit
    assert r.json()["artifact"]["preview"] == {
        "expected": "carte3d_preview.png", "written": False}


def test_le_glb_externe_a_images_uri_est_refuse_motive():
    """Rien ne se télécharge à l'assemblage : un GLB dont les images vivent
    au bout d'une URL est REFUSÉ NOMMÉMENT, pas silencieusement dépouillé de
    ses textures."""
    did = _deck("Uri")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_bricole(
        images=[{"uri": "https://ailleurs.example/tex.png"}]), closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 409, r.text
    assert "uri" in r.json()["detail"].lower()


def test_la_fusion_gate_sur_la_taille_du_job_sans_ouvrir_le_fichier(monkeypatch):
    """LEGS TASK 4 : `served` n'implique plus « utilisable ». Un GLB au-delà
    de MAX_EXT_GLB_BYTES arrive SERVI (closed None + note) ; la fusion doit le
    refuser sur la taille RELUE AU JOB, sans jamais ouvrir le fichier — ici
    prouvé par un model.glb réduit à du charabia : s'il était lu, le refus
    serait un 409 de lecture, pas le 400 de la borne."""
    from app.services.cards import forge3d as F9
    did = _deck("Trop lourd")
    _exporter_couches(did)
    _job_servi(did, "m1", b"ceci n'est pas un GLB", closed=None,
               note="fermeture non mesurée : GLB trop lourd",
               octets=99_000_000)
    monkeypatch.setattr(F9, "MAX_EXT_GLB_BYTES", 1024)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert "99000000" in detail and "1024" in detail and "m1" in detail
    # sous la borne, le MÊME charabia part en 409 de LECTURE — la preuve que
    # le 400 ci-dessus n'a pas ouvert le fichier.
    monkeypatch.setattr(F9, "MAX_EXT_GLB_BYTES", 64 * 1024 * 1024)
    _job_servi(did, "m1", b"ceci n'est pas un GLB", closed=None)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 409, r2.text
    assert "glTF" in r2.json()["detail"] or "GLB" in r2.json()["detail"]


def test_la_chaine_matiere_et_transform_habille_l_element_local():
    """layer -> relief -> material(matière + finition + aniso) -> transform ->
    assemble : les maps TUILÉES et la recette holo arrivent sur le matériau
    glTF de CET élément, et le TRS du transform sur son nœud."""
    from app.services import material_store as MSTORE
    did = _deck("Chaine locale")
    _exporter_couches(did)
    mat = MSTORE.create_material(name="chaine-2b")
    try:
        MSTORE.save_maps(mat["id"], {
            "basecolor": Image.new("RGB", (32, 32), (120, 90, 60)),
            "normal": Image.new("RGB", (32, 32), (128, 128, 255)),
            "roughness": Image.new("L", (32, 32), 70),
            "metallic": Image.new("L", (32, 32), 210),
            "ao": Image.new("L", (32, 32), 180)})
        g = {"nodes": [
            {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
            {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
             "grid": 48},
            {"id": "mt", "kind": "material", "mat": mat["id"],
             "tile_mm": 31.5, "finish": "argent", "aniso": True},
            {"id": "tr", "kind": "transform", "x_mm": 4.0, "y_mm": -2.0,
             "z_mm": 1.5, "rot_deg": 0.0, "scale": 2.0},
            {"id": "asm", "kind": "assemble"},
            {"id": "art", "kind": "artifact", "name": "habille"}],
            "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "mt"},
                      {"from": "mt", "to": "tr"}, {"from": "tr", "to": "asm"},
                      {"from": "asm", "to": "art"}]}
        r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        b = r.json()["artifact"]
        assert b["ignored"] == [], b["ignored"]
        doc, _ = _read_glb(_api(
            "GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content)
        m = doc["materials"][0]
        assert "normalTexture" in m and "occlusionTexture" in m
        # la finition SAUTE la map MR (doctrine Task 5) et pose SA recette
        assert "metallicRoughnessTexture" not in m["pbrMetallicRoughness"]
        assert m["pbrMetallicRoughness"]["baseColorFactor"] == \
            [0.95, 0.95, 0.97, 1.0]
        assert set(doc["extensionsUsed"]) == {"KHR_materials_iridescence",
                                              "KHR_materials_clearcoat",
                                              "KHR_materials_anisotropy"}
        assert "extensionsRequired" not in doc
        # le TRS du transform, sur le nœud de l'élément
        assert doc["nodes"][0]["translation"] == [4.0, -2.0, 1.5]
        assert doc["nodes"][0]["scale"] == [2.0, 2.0, 2.0]
        # les maps sont TUILÉES au ratio carte, pas collées telles quelles
        i_nrm = doc["textures"][m["normalTexture"]["index"]]["source"]
        assert doc["images"][i_nrm]["name"] == "cadre-normal"
        # ── ET LE STL DIT LA MÊME CHOSE QUE LE GLB ─────────────────────────
        # Le format STL n'a pas de nœud : ce que le GLB porte sur le nœud doit
        # être CUIT dans les sommets. Sans cela, la pièce s'imprimait à
        # l'origine, à l'échelle 1, pendant que l'aperçu la montrait déplacée
        # et doublée — deux fichiers, deux vérités, et c'est le fichier
        # PAYANT (l'impression) qui avait tort.
        assert b["stl"]["written"] is True, b["stl"]
        stl = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                   + b["stl"]["name"]).content
        lo, hi = _stl_bbox(stl)
        # relief 63 x 88, z de 0 a 0,3+1,0 -> x2 puis + (4 ; -2 ; 1,5)
        for axe, attendu in enumerate(([4.0, 130.0], [-2.0, 174.0],
                                       [1.5, 4.1])):
            assert abs(lo[axe] - attendu[0]) < 1e-3, (axe, lo[axe])
            assert abs(hi[axe] - attendu[1]) < 1e-3, (axe, hi[axe])
    finally:
        MSTORE.delete_material(mat["id"])


def test_les_chaines_impossibles_sont_avouees_sans_faire_tomber_l_artefact():
    """Deux aveux, deux motifs : une matière chaînée sur un mesh3d (le GLB du
    moteur porte DÉJÀ ses matériaux) et une matière introuvable sur disque
    (l'élément passe SANS maps, jamais un 500 ni un silence)."""
    did = _deck("Chaines ignorees")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="tripo")
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": "tripo",
         "texture_prompt": "", "ultra": False},
        {"id": "mt", "kind": "material", "mat": "mat_deadbeef",
         "tile_mm": 63.0, "finish": "aucune", "aniso": False},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "mt2", "kind": "material", "mat": "mat_deadbeef",
         "tile_mm": 63.0, "finish": "aucune", "aniso": False},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "ignores2b"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "mt"},
                  {"from": "mt", "to": "asm"}, {"from": "s2", "to": "t2"},
                  {"from": "t2", "to": "mt2"}, {"from": "mt2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    motifs = {i["node"]: i["why"] for i in b["ignored"]}
    assert set(motifs) == {"mt", "mt2"}, motifs
    assert "moteur" in motifs["mt"]                    # matière sur un mesh3d
    assert "introuvable" in motifs["mt2"]              # matière absente du disque
    # l'artefact EXISTE quand même, et l'élément local passe SANS maps
    doc, _ = _read_glb(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content)
    local = next(m for m in doc["materials"] if m["name"] == "cadre")
    assert "normalTexture" not in local and "occlusionTexture" not in local
    assert "extensionsUsed" not in doc
    types = {a["trait_type"]: a["value"] for a in json.loads(_api(
        "GET",
        f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content
    )["attributes"]}
    assert types["engines"] == "local+tripo" and types["elements_3d"] == 2


def test_le_glb_externe_aux_exigences_inconnues_ou_trop_profond_est_refuse():
    """Deux refus NOMMÉS là où le silence livrerait un artefact FAUX :
    une extension EXIGÉE que la fusion ne sait pas transporter (son bloc vit
    dans des champs que la recopie ne connaît pas — le fichier annoncerait une
    exigence dont la description a disparu), et une hiérarchie de scène plus
    profonde que la descente ne va (tronquer y perdrait de la géométrie SANS
    le dire : boîte trop petite, STL amputé, `closed` toujours vrai)."""
    did = _deck("Exigences")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    _job_servi(did, "m1", _glb_bricole(
        extensionsUsed=["EXT_meshopt_compression"],
        extensionsRequired=["EXT_meshopt_compression"]), closed=False)
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 409, r.text
    assert "EXT_meshopt_compression" in r.json()["detail"]

    prof = 40
    noeuds = [{"children": [i + 1]} for i in range(prof)]
    noeuds.append({"mesh": 0})
    _job_servi(did, "m1", _glb_bricole(nodes=noeuds), closed=False)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 409, r2.text
    assert "profonde" in r2.json()["detail"]


def test_un_glb_servi_pour_une_autre_couche_est_refuse_nomme():
    """I2 — un GLB de moteur est lié à SA carte : il est né d'UNE couche
    précise, que le job nomme (`source.file`). L'assembler dans la
    construction d'une AUTRE carte (ou d'un autre côté) livrerait l'illustration
    de la carte 7 présentée comme celle de la carte 1 — le bon fichier, au
    mauvais endroit, qu'aucune mesure ne rattrape après coup. Refus NOMMÉ, avec
    LES DEUX noms, pour que le motif soit actionnable."""
    did = _deck("Appariement")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="meshy-7",
               credits=30,
               source={"role": "illustration", "side": "front",
                       "file": "illustration_c07_front.png",
                       "bytes": 10, "sha256": None})
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": _graphe_mesh3d("meshy-7"), "card": 0})
    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert "illustration_c07_front.png" in d, d      # ce qui a ete servi
    assert "illustration_c01_front.png" in d, d      # ce qui est attendu
    assert "m1" in d, d

    # ... et le MEME job, servi pour la bonne couche, passe : le gate discrimine
    # bien la carte, il ne casse pas la fusion.
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="meshy-7",
               credits=30,
               source={"role": "illustration", "side": "front",
                       "file": "illustration_c01_front.png",
                       "bytes": 10, "sha256": None})
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": _graphe_mesh3d("meshy-7"), "card": 0})
    assert r2.status_code == 200, r2.text


def test_l_eligibilite_a_l_ultra_a_une_seule_source():
    """M8 — `clean_graph` ne recopie plus « meshy-7 » : il interroge la grille
    partagee qui FACTURE le surcout (et que /info publie en
    `ultra_extra_credits`). Deux verites divergentes sur un axe payant, c'est
    un devis qui annonce ce que le nettoyage efface."""
    from app.services.cards import forge3d as F9
    from app.services import meshy_service as MS

    def ultra_de(engine):
        g = F9.clean_graph({"nodes": [{"id": "m1", "kind": "mesh3d",
                                       "engine": engine, "ultra": True}],
                            "edges": []})
        return g["nodes"][0]["ultra"], g["nodes"][0]["engine"]

    for e in F9.MESH3D_ENGINES:
        ultra, moteur = ultra_de(e["id"])
        assert moteur == e["id"]
        # LA grille est l'arbitre, des deux cotes de l'assertion
        assert ultra is (MS._ultra_extra(e["id"], True) > 0), e["id"]
    # un moteur INCONNU est repare vers le defaut, et l'ultra ne survit pas a
    # une reparation, meme si le defaut, lui, l'accepterait
    ultra, moteur = ultra_de("warp-drive")
    assert moteur == F9.MESH3D_DEFAULT_ENGINE
    assert ultra is False, "l'ultra ne se reconduit pas vers un moteur non nomme"


def test_un_accesseur_de_positions_non_float32_est_refuse_nomme():
    """Résidu de re-revue (Task 6) : le lecteur de flottants ne décode QUE du
    float32. Un accesseur quantifié (KHR_mesh_quantization, componentType
    5123) relu comme des flottants rendrait des positions ABSURDES SANS lever
    — un GLB valide qui mesure et imprime la mauvaise chose. Le refus est
    NOMMÉ, et il rend explicite le couplage avec `_EXIG_CONNUES` (qui exclut
    l'extension pour exactement cette raison)."""
    from app.services.cards import forge3d_scene as SC
    # même GLB minimal, mais l'accesseur POSITION se DÉCLARE en entiers courts
    quantifie = _glb_bricole(accessors=[
        {"componentType": 5123, "count": 3, "type": "VEC3", "bufferView": 0,
         "normalized": True, "min": [0, 0, 0], "max": [1, 1, 0]},
        {"componentType": 5125, "count": 3, "type": "SCALAR", "bufferView": 1}])
    with pytest.raises(ValueError) as ex:
        SC.glb_scene_mesh(quantifie)
    assert "non float32" in str(ex.value), str(ex.value)
    assert "5123" in str(ex.value), str(ex.value)
    # et l'allowlist des exigences ne la laisse pas entrer par la porte d'à côté
    assert "KHR_mesh_quantization" not in SC._EXIG_CONNUES


def test_les_maillons_surnumeraires_d_une_chaine_sont_avoues():
    """M3 : deux matières partent du MÊME relief — la première arête gagne (la
    règle de l'entrée depuis la 2a), et la seconde est une PERTE, avouée avec
    les mots de l'entrée. L'écran ne produit pas cette topologie ; l'API brute,
    elle, est ouverte à qui la poste."""
    did = _deck("Eventail")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "mA", "kind": "material", "mat": None, "tile_mm": 63.0,
         "finish": "argent", "aniso": False},
        {"id": "mB", "kind": "material", "mat": None, "tile_mm": 63.0,
         "finish": "dorure", "aniso": False},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "eventail"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "mA"},
                  {"from": "t2", "to": "mB"}, {"from": "mA", "to": "asm"},
                  {"from": "mB", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    motifs = {i["node"]: i["why"] for i in b["ignored"]}
    assert set(motifs) == {"mB"}, motifs
    assert "surnumeraire" in motifs["mB"] and "mA" in motifs["mB"]
    # c'est bien mA (ARGENT) qui a servi, pas mB (dorure) : l'aveu ne dit pas
    # l'inverse de ce qui a été fait.
    doc, _ = _read_glb(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content)
    assert doc["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"] == \
        [0.95, 0.95, 0.97, 1.0]


def test_le_rebuild_efface_le_stl_perime():
    """Jumeau de l'aperçu périmé : un STL qu'une NOUVELLE passe refuse ne doit
    pas rester servi par /file en contredisant le bordereau qui vient de dire
    « non »."""
    did = _deck("Stl perime")
    _exporter_couches(did)
    base = [{"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
            {"id": "asm", "kind": "assemble"},
            {"id": "art", "kind": "artifact", "name": "solide"}]
    aretes = [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
              {"from": "asm", "to": "art"}]
    g1 = {"nodes": base + [{"id": "t2", "kind": "relief", "depth_mm": 1.0,
                            "base_mm": 0.3, "grid": 48}], "edges": aretes}
    r1 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g1, "card": 0})
    assert r1.status_code == 200 and r1.json()["artifact"]["stl"]["written"]
    assert _api("GET", f"/api/cards/{did}/forge3d/file/solide.stl"
                ).status_code == 200
    # même NOM d'artefact, mais un plan : plus de solide, donc plus de STL
    g2 = {"nodes": base + [{"id": "t2", "kind": "plane", "depth_mm": 0.0}],
          "edges": aretes}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g2, "card": 0})
    assert r2.status_code == 200, r2.text
    assert r2.json()["artifact"]["stl"]["written"] is False
    assert _api("GET", f"/api/cards/{did}/forge3d/file/solide.stl"
                ).status_code == 404


def test_les_exigences_de_l_externe_survivent_et_ses_variants_sont_reindexes():
    """Le pendant POSITIF du refus : une extension exigée que la fusion SAIT
    transporter reste EXIGÉE dans le document fusionné (il l'exige vraiment),
    tandis que les NÔTRES — enjolivures — n'y entrent jamais. Et les indices
    de matériau cachés dans les extensions d'une primitive
    (KHR_materials_variants) sont décalés comme les autres, sans quoi la
    variante du moteur pointerait le matériau de NOTRE couche."""
    did = _deck("Exigences gardees")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_bricole(
        extensionsUsed=["KHR_materials_unlit", "KHR_materials_variants"],
        extensionsRequired=["KHR_materials_unlit"],
        extensions={"KHR_materials_variants": {"variants": [{"name": "or"}]}},
        materials=[{"name": "moteur",
                    "extensions": {"KHR_materials_unlit": {}}}],
        # `sampler: true` n'est PAS l'indice 1 — ce n'est pas un indice du
        # tout (M7 : en Python, `True in {0:..., 1:...}` est VRAI).
        images=[{"bufferView": 0, "mimeType": "image/png"}],
        samplers=[{"wrapS": 33071, "wrapT": 33071}, {"wrapS": 10497}],
        textures=[{"source": 0, "sampler": True}],
        meshes=[{"primitives": [{
            "attributes": {"POSITION": 0}, "indices": 1, "material": 0,
            "extensions": {"KHR_materials_variants": {
                "mappings": [{"material": 0, "variants": [0]}]}}}]}]),
        closed=False, engine="tripo")
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": "tripo",
         "texture_prompt": "", "ultra": False},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "mt", "kind": "material", "mat": None, "tile_mm": 63.0,
         "finish": "argent", "aniso": False},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "exig3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "asm"},
                  {"from": "s2", "to": "t2"}, {"from": "t2", "to": "mt"},
                  {"from": "mt", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    doc, _ = _read_glb(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content)
    # SON exigence est portée par le document fusionné ; LES NÔTRES, non
    assert doc["extensionsRequired"] == ["KHR_materials_unlit"]
    assert "KHR_materials_iridescence" in doc["extensionsUsed"]
    assert "KHR_materials_unlit" in doc["extensionsUsed"]
    # le matériau du moteur est le SECOND (notre couche occupe le premier) et
    # le mapping de variante a suivi le décalage
    prim = doc["meshes"][1]["primitives"][0]
    assert prim["material"] == 1
    assert doc["materials"][1]["name"] == "moteur"
    mapp = prim["extensions"]["KHR_materials_variants"]["mappings"][0]
    assert mapp["material"] == 1, mapp
    # M7 : le `sampler` BOOLÉEN n'a pas volé le second sampler du moteur — la
    # texture a reçu un sampler par DÉFAUT ajouté (`{}` = REPEAT au glTF).
    assert doc["samplers"][doc["textures"][-1]["sampler"]] == {}
    # ...et ce que la fusion NE reprend PAS est avoué : la DÉCLARATION de
    # niveau document (la liste des variantes) n'est pas fusionnable.
    motifs = [i["why"] for i in b["ignored"] if i["node"] == "m1"]
    assert any("document" in w and "KHR_materials_variants" in w
               for w in motifs), b["ignored"]


def test_un_job_verrouille_par_l_ecriture_n_est_pas_declare_absent(monkeypatch):
    """CONSTATÉ EN NAVIGATEUR (2 lancements sur 2, trace serveur à l'appui) :
    sous Windows, `os.replace` fait échouer en `PermissionError` l'ouverture du
    `job.json` DESTINATION pendant l'écriture concurrente du runner. Rendu
    comme « fichier absent », ce refus devenait un 404 « aucun job sur ce
    noeud » PENDANT qu'un job PAYANT tournait : l'écran — qui a raison de tenir
    un job nul pour terminal — affichait « jamais lancé », arrêtait son poll,
    et le nœud finissait sa course en dépensant sans laisser de trace, le pied
    de coût le recomptant comme restant à lancer.

    Un verrou passager doit donc être RETENTÉ, et lui seul : l'absence vraie
    répond du premier coup, une corruption vaut toujours ABSENT."""
    import time
    from app.services.cards import forge3d as F9
    did = _deck("Verrou passager")
    base = _dossier_noeud(did, "m1")
    base.mkdir(parents=True, exist_ok=True)
    job = {"schema": "card-3d/mesh3d-job@1", "node": "m1", "engine": "tripo",
           "run_id": "e" * 32, "status": "served", "progress": 100}
    (base / "job.json").write_text(json.dumps(job), encoding="utf-8")

    vrai_read_text = pathlib.Path.read_text
    refus = {"n": 0}

    def read_text_verrouille(self, *a, **k):
        # UNIQUEMENT le job.json de ce nœud, et seulement les deux premières
        # fois : la troisième doit réussir, sinon le test ne prouve pas la
        # reprise mais l'abandon.
        if self.name == "job.json" and refus["n"] < 2:
            refus["n"] += 1
            raise PermissionError(13, "Permission denied")
        return vrai_read_text(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "read_text", read_text_verrouille)
    r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert refus["n"] == 2, "le verrou simule n'a pas ete rencontre"
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "served"
    assert r.json()["run_id"] == "e" * 32

    # ...et le verrou QUI NE LÂCHE PAS ne devient pas un 500 : il retombe sur
    # l'absence, après avoir vraiment épuisé les essais.
    refus["n"] = 0
    monkeypatch.setattr(pathlib.Path, "read_text",
                        lambda self, *a, **k: (_ for _ in ()).throw(
                            PermissionError(13, "Permission denied"))
                        if self.name == "job.json"
                        else vrai_read_text(self, *a, **k))
    r2 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r2.status_code == 404, r2.text
    assert "aucun job" in r2.json()["detail"]

    # LE CHEMIN COURANT NE PAIE RIEN : un nœud jamais lancé répond sans
    # attendre — `is_file()` est faux, aucune reprise n'est tentée.
    monkeypatch.setattr(pathlib.Path, "read_text", vrai_read_text)
    assert F9._JOB_IO_ESSAIS >= 2 and F9._JOB_IO_PAUSE_S > 0
    debut = time.monotonic()
    r3 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/jamais")
    ecoule = time.monotonic() - debut
    assert r3.status_code == 404
    assert ecoule < F9._JOB_IO_ESSAIS * F9._JOB_IO_PAUSE_S, ecoule

    # ── L'AUTRE MOITIÉ DE LA COURSE, mesurée elle aussi en navigateur : quand
    # c'est le POLL qui tient le fichier, c'est `os.replace` qui échoue
    # (WinError 5). L'exception remontait jusqu'à `_run_mesh3d`, qui déclarait
    # FAILED un job PAYÉ — un simple poll suffisait à le tuer.
    vrai_replace = os.replace
    refus_w = {"n": 0}

    def replace_verrouille(src, dst, *a, **k):
        if str(dst).endswith("job.json") and refus_w["n"] < 2:
            refus_w["n"] += 1
            raise PermissionError(5, "Acces refuse")
        return vrai_replace(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", replace_verrouille)
    job2 = dict(job, status="running", progress=42)
    assert F9._job_write(did, "m1", job2) is job2
    assert refus_w["n"] == 2, "le verrou d'ecriture simule n'a pas ete rencontre"
    disque = json.loads((base / "job.json").read_text(encoding="utf-8"))
    assert disque["progress"] == 42 and disque["status"] == "running"

    # ...et un verrou qui NE LÂCHE JAMAIS reste une panne : elle repart telle
    # quelle (l'aveu doit dire la vérité), elle n'est pas avalée en silence.
    monkeypatch.setattr(os, "replace", lambda src, dst, *a, **k: (
        (_ for _ in ()).throw(PermissionError(5, "Acces refuse"))
        if str(dst).endswith("job.json") else vrai_replace(src, dst, *a, **k)))
    with pytest.raises(PermissionError):
        F9._job_write(did, "m1", dict(job, progress=99))


# ── L'APERCU D'UN SEUL NOEUD + LA VIGNETTE DE MATIERE (Task 1, 2c) ──────────
# AUCUN de ces tests ne depense un credit : le job mesh3d SERVI est pose sur
# disque a la main (meme patron que la fusion des GLB externes ci-dessus), le
# GLB "moteur" est ecrit par NOTRE writer.

def _reset_node(did, nid):
    """Repart de zero sur un noeud, comme une relance (post_mesh3d) : rmtree
    du dossier durable du noeud."""
    import shutil
    d = _dossier_noeud(did, nid)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)


def test_node_preview_construit_le_glb_du_seul_element(monkeypatch):
    """POST /forge3d/node-preview {graph, card, nid} -> le GLB d'UN element,
    grille de relief BORNEE (apercu rapide), reponse ephemere, jamais-500."""
    from app.services.cards import forge3d as F9
    from app.services.cards import forge3d_scene as SC
    did = _deck("Preview noeud")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 256},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "x"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
             json={"graph": g, "card": 0, "nid": "t1"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("model/gltf-binary")
    doc, binv = _read_glb(r.content)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert [doc["nodes"][k]["name"] for k in racine["children"]] == ["cadre"]
    # I1/M5 (revue) : le schema est CELUI de l'apercu (jamais artifact@1),
    # `preview` est le discriminant explicite, et rien n'a ete ecarte ici ->
    # `ignored` est VIDE (present, pas absent).
    extras = doc["asset"]["extras"]
    assert extras["schema"] == F9.PREVIEW_SCHEMA == "card-3d/apercu@1"
    assert extras["preview"] is True
    assert extras["ignored"] == []
    # la grille demandee (256) est PLAFONNEE pour l'apercu : le compte de
    # triangles est celui de RELIEF_GRID_PREVIEW, pas du grid max
    m = SC.glb_scene_mesh(r.content)
    gy = max(2, round(F9.RELIEF_GRID_PREVIEW * (88.0 / 63.0)))
    attendu = (4 * F9.RELIEF_GRID_PREVIEW * gy + 4 * F9.RELIEF_GRID_PREVIEW
               + 4 * gy)
    assert len(m["indices"]) // 3 == attendu

    # un noeud mesh3d SERVI -> les octets du GLB du job, tels quels
    relief = SC.relief_mesh(Image.new("L", (8, 8), 255), 63.0, 88.0, 1.0,
                            0.3, 4)
    relief["closed"] = True
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    glb_job = SC.write_scene_glb([{"name": "brut", "mesh": relief,
                                   "png": png.getvalue(), "alpha": False,
                                   "z_mm": 0.0}], name="b", extras={})
    _job_servi(did, "m1", glb_job, closed=True)
    g2 = _graphe_mesh3d("meshy-7")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r2.status_code == 200 and r2.content == glb_job

    # refus nommes : mesh3d non servi -> 409 « servi » ; nid inconnu -> 400 ;
    # kind non previsualisable (assemble) -> 400 nomme
    _reset_node(did, "m1")
    r3 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r3.status_code == 409 and "servi" in r3.json()["detail"]
    r4 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g, "card": 0, "nid": "zzz"})
    assert r4.status_code == 400
    r5 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g, "card": 0, "nid": "asm"})
    assert r5.status_code == 400
    assert "prévisualisable" in r5.json()["detail"]

    # CF2 (revue) : borne PROPRE a l'inspecteur (pas MAX_EXT_GLB_BYTES),
    # mesuree sur job/stat (jamais une lecture), refus au motif LITTERAL.
    _job_servi(did, "m1", glb_job, closed=True)
    monkeypatch.setattr(F9, "MAX_APERCU_GLB_BYTES", 10)
    r6 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r6.status_code == 409, r6.text
    assert ("trop lourd pour l'inspecteur" in r6.json()["detail"]
            and "10 o" in r6.json()["detail"]), r6.json()["detail"]
    monkeypatch.undo()
    # sous la vraie borne, le MEME job repasse -- FileResponse sert les
    # octets du DISQUE, byte-identiques a ce que le job a ecrit.
    r7 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r7.status_code == 200 and r7.content == glb_job


def test_l_id_synthetique_de_l_apercu_est_hors_alphabet():
    """M1/CF1 (revue) : la garantie anti-collision de l'assemble synthetique
    est STRUCTURELLE (un caractere que `clean_graph` ne peut jamais emettre),
    pas arithmetique (une longueur) — l'argument « > 24 caracteres » etait
    FAUX au moment ou il a ete ecrit (P1 : le suffixe anti-collision pouvait
    depasser 24)."""
    from app.services.cards import forge3d as F9
    assert re.search(r"[^A-Za-z0-9._-]", F9._PREVIEW_ASM_ID)
    assert not F9._NID_RE.match(F9._PREVIEW_ASM_ID)


def test_node_preview_chaine_matiere_transform_et_ignores():
    """I1/I3 (revue) : layer -> relief -> material(temoin + finition argent)
    -> transform -> assemble : l'apercu d'UN noeud montre l'option DEJA
    choisie sur SA chaine (memes maps tuilees et TRS que build3d), et un
    aveu ecarte (matiere supprimee de la boutique ENTRE le graphe et
    l'apercu) reste VISIBLE dans extras["ignored"] — jamais tu."""
    from app.services import material_store as MSTORE
    did = _deck("Preview chaine")
    _exporter_couches(did)
    mat = MSTORE.create_material(name="apercu-2c")
    try:
        MSTORE.save_maps(mat["id"], {
            "basecolor": Image.new("RGB", (32, 32), (120, 90, 60)),
            "normal": Image.new("RGB", (32, 32), (128, 128, 255)),
            "roughness": Image.new("L", (32, 32), 70),
            "metallic": Image.new("L", (32, 32), 210),
            "ao": Image.new("L", (32, 32), 180)})
        g = {"nodes": [
            {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
            {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
             "grid": 48},
            {"id": "mat", "kind": "material", "mat": mat["id"],
             "tile_mm": 31.5, "finish": "argent", "aniso": True},
            {"id": "trs", "kind": "transform", "x_mm": 4.0, "y_mm": 0.0,
             "z_mm": 2.0, "rot_deg": 0.0, "scale": 2.0},
            {"id": "asm", "kind": "assemble"}],
            "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "mat"},
                      {"from": "mat", "to": "trs"},
                      {"from": "trs", "to": "asm"}]}
        r = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
                 json={"graph": g, "card": 0, "nid": "t1"})
        assert r.status_code == 200, r.text
        doc, _binv = _read_glb(r.content)
        extras = doc["asset"]["extras"]
        assert extras["schema"] == "card-3d/apercu@1"
        assert extras["preview"] is True
        assert extras["ignored"] == []
        m = doc["materials"][0]
        assert "normalTexture" in m and "occlusionTexture" in m
        assert set(doc.get("extensionsUsed", [])) == {
            "KHR_materials_iridescence", "KHR_materials_clearcoat",
            "KHR_materials_anisotropy"}
        # le TRS du transform, sur le noeud de l'element (meme composition
        # que build3d : translate + scale UNIFORME du transform utilisateur)
        assert doc["nodes"][0]["translation"] == [4.0, 0.0, 2.0]
        assert doc["nodes"][0]["scale"] == [2.0, 2.0, 2.0]

        # ET SANS materiere/transform (chaine nue) : le noeud ne porte NI
        # translation NI l'echelle x2 — la preuve que le TRS ci-dessus vient
        # bien de CETTE chaine, pas d'un defaut du writer.
        g_nu = {"nodes": [
            {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
            {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
             "grid": 48},
            {"id": "asm", "kind": "assemble"}],
            "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"}]}
        r_nu = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
                    json={"graph": g_nu, "card": 0, "nid": "t1"})
        assert r_nu.status_code == 200, r_nu.text
        doc_nu, _ = _read_glb(r_nu.content)
        assert "translation" not in doc_nu["nodes"][0]
        assert doc_nu["nodes"][0].get("scale") != [2.0, 2.0, 2.0]

        # la matiere disparait de la boutique ENTRE deux apercus du MEME
        # graphe : 200 toujours, element NU, mais le motif ECARTE reste
        # VISIBLE (I1) — jamais un silence.
        MSTORE.delete_material(mat["id"])
        r2 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
                  json={"graph": g, "card": 0, "nid": "t1"})
        assert r2.status_code == 200, r2.text
        doc2, _ = _read_glb(r2.content)
        m2 = doc2["materials"][0]
        assert "normalTexture" not in m2 and "occlusionTexture" not in m2
        ignored2 = doc2["asset"]["extras"]["ignored"]
        motifs2 = {i["node"]: i["why"] for i in ignored2}
        assert "mat" in motifs2 and "introuvable" in motifs2["mat"], ignored2
    finally:
        if MSTORE.read_material(mat["id"]) is not None:
            MSTORE.delete_material(mat["id"])


def test_la_phrase_de_source_surnumeraire_est_LA_MEME_des_deux_cotes():
    """N1 (couture de delestage, tache 6) : la phrase d'aveu de la « premiere
    arete gagnante » etait ECRITE DEUX FOIS — une dans le resolveur de
    build3d, une dans le sous-graphe de l'apercu — et le decoupage de
    litteral suffisait a faire rater la copie au grep (l'une disait
    « deja » + « retenu », l'autre « deja retenu »). Elles viennent desormais
    de `_source_gagnante`, et RIEN ne le prouve mieux que de les comparer
    OCTET POUR OCTET sur la meme topologie.

    Mutant qui a rendu ce test necessaire : changer le mot de cette phrase-la
    ne faisait rougir AUCUN test (celle du maillon, elle, etait deja pinnee).
    """
    did = _deck("Aveu partage")
    _exporter_couches(did)
    # DEUX couches entrent dans le MEME traitement : s1 gagne, s3 est perdue.
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "s3", "kind": "layer", "role": "typographie", "side": "front"},
        {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "aveu"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "s3", "to": "t1"},
                  {"from": "t1", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    cote_build = {i["node"]: i["why"] for i in r.json()["artifact"]["ignored"]}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g, "card": 0, "nid": "t1"})
    assert r2.status_code == 200, r2.text
    doc, _ = _read_glb(r2.content)
    cote_apercu = {i["node"]: i["why"]
                   for i in doc["asset"]["extras"]["ignored"]}
    assert "s3" in cote_build, cote_build
    assert "s3" in cote_apercu, cote_apercu
    # LA MEME PHRASE, mot pour mot : c'est CA, la propriete de la couture.
    assert cote_build["s3"] == cote_apercu["s3"], (cote_build, cote_apercu)
    # ... et elle dit les DEUX noms plus la regle, sinon l'aveu n'est pas
    # actionnable (« lequel a gagne, et pourquoi ? »).
    assert "surnumeraire" in cote_build["s3"], cote_build["s3"]
    assert "s1" in cote_build["s3"] and "t1" in cote_build["s3"], \
        cote_build["s3"]
    assert "premiere arete gagnante" in cote_build["s3"], cote_build["s3"]


def test_node_preview_n_ecrit_jamais_sur_disque():
    """M7 (revue) : « reponse EPHEMERE » (spec §5.6 point 4) devient un test
    — snapshot du dossier forge3d du deck avant/apres un apercu plane/relief,
    memes fichiers, memes mtimes."""
    did = _deck("Preview sans ecriture")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"}]}
    base = _dossier_forge3d(did)

    def snapshot():
        return sorted((str(p.relative_to(base)), p.stat().st_mtime_ns)
                     for p in base.rglob("*") if p.is_file())

    avant = snapshot()
    r = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
             json={"graph": g, "card": 0, "nid": "t1"})
    assert r.status_code == 200, r.text
    apres = snapshot()
    assert avant == apres, (avant, apres)


def test_material_thumb_est_servi_par_provenance():
    from app.services import material_store as MSTORE
    mat = MSTORE.create_material(name="vignette-2c")
    try:
        MSTORE.write_thumb(mat["id"], _png(Image.new("RGBA", (64, 64),
                                                     (10, 200, 10, 255))))
        did = _deck("Thumb")
        r = _api("GET", f"/api/cards/{did}/forge3d/material-thumb/{mat['id']}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/")
        # mid invalide -> 400 ; matiere sans vignette -> 404 nomme
        r2 = _api("GET", f"/api/cards/{did}/forge3d/material-thumb/..%2Fx")
        assert r2.status_code in (400, 404)
        m2 = MSTORE.create_material(name="sans-vignette")
        try:
            r3 = _api("GET",
                      f"/api/cards/{did}/forge3d/material-thumb/{m2['id']}")
            assert r3.status_code == 404
        finally:
            MSTORE.delete_material(m2["id"])
        # REPRISE T6 (re-revue de la ronde T5) : le `no-store` des REFUS etait
        # ENVOYE mais jamais LU ici — le test ne le mesurait que sur
        # `node-file`, alors que le defaut vise est le MEME et qu'il est pire
        # sur cette route-ci : « matiere sans vignette » devient « vignette
        # servie » des qu'on la capture dans la boutique, et un 404 mis en
        # cache par heuristique laisserait le nœud `material` sur son aplat de
        # couleur alors que la vignette EXISTE. CHAQUE sortie de refus est
        # mesuree : chacune a son propre `raise`, donc chacune peut perdre ses
        # en-tetes toute seule.
        #
        # AMENDE A LA SOURCE : la reprise nommait « r2/r3/r4 », et r2 N'EST PAS
        # un refus de cette route — `..%2Fx` porte un separateur, donc AUCUNE
        # route ne matche et c'est le 404 du ROUTEUR qui repond, sans un seul
        # de nos en-tetes (mesure ci-dessous, pour que le prochain lecteur ne
        # reouvre pas la question). Le refus que r2 CROYAIT viser — « mid hors
        # motif » — a donc son cas propre, avec un mid qui atteint vraiment la
        # route.
        assert r2.headers.get("cache-control") is None, dict(r2.headers)
        rmid = _api("GET", f"/api/cards/{did}/forge3d/material-thumb/pas-un-mid")
        assert rmid.status_code == 400, rmid.text
        assert "matière" in rmid.json()["detail"], rmid.text
        assert rmid.headers.get("cache-control") == "no-store", \
            dict(rmid.headers)
        assert r3.headers.get("cache-control") == "no-store", dict(r3.headers)
        # I4 (revue) : une vignette PERIMEE (MESH_VERSION a change depuis
        # sa capture — thumb_is_current lit "thumb.mv") est tenue pour
        # ABSENTE, meme doctrine que la boutique pour sa propre carte : le
        # client retombe sur un aplat de couleur, comme la galerie deja.
        d = MSTORE.material_dir(mat["id"])
        (d / "thumb.mv").write_text("-1", encoding="utf-8")
        assert MSTORE.thumb_is_current(d) is False
        r4 = _api("GET",
                  f"/api/cards/{did}/forge3d/material-thumb/{mat['id']}")
        assert r4.status_code == 404
        assert r4.headers.get("cache-control") == "no-store", dict(r4.headers)
    finally:
        MSTORE.delete_material(mat["id"])


def test_node_file_sert_l_apercu_d_un_noeud_par_liste_blanche():
    """L'APERCU d'un noeud, servi par provenance (Task 5, 2c) — le manque
    REMONTE au controleur en Task 3 : `nodes/{nid}/preview.png` n'etait
    atteignable par AUCUNE route (`GET /file/{name}` interdit le separateur),
    et la vignette d'un noeud moteur prenait la branche « a defaut ».

    Ce qui est mesure ici : la LISTE BLANCHE (le dossier d'un noeud porte
    aussi `job.json` et des textures PAYEES — seul l'apercu est un affichage
    public), le confinement (un nid en forme de saut ne sort pas du dossier
    des noeuds) et les refus NOMMES."""
    did = _deck("Apercu de noeud")
    _job_servi(did, "m1", _glb_ferme(), closed=True)
    d = _dossier_noeud(did, "m1")
    (d / "preview.png").write_bytes(
        _png(Image.new("RGBA", (8, 8), (7, 9, 11, 255))))
    r = _api("GET", f"/api/cards/{did}/forge3d/node-file/m1/preview.png")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    # un apercu CHANGE sous le meme nom (une relance le reecrit) : le cache
    # n'a pas le droit de le figer.
    assert r.headers.get("cache-control") == "no-store"
    assert r.content == (d / "preview.png").read_bytes()

    # absent -> 404 NOMME (une reponse, pas une panne : le moteur n'en a pas
    # rapatrie, ou le noeud n'a jamais tourne)
    r2 = _api("GET", f"/api/cards/{did}/forge3d/node-file/m2/preview.png")
    assert r2.status_code == 404, r2.text
    assert "m2" in r2.json()["detail"]
    # N1 (ronde de correction 2c-T5) : le REFUS ne se met pas en cache non
    # plus. « pas encore d'apercu » devient « apercu servi » des que le job
    # rapatrie le fichier ; un 404 heuristiquement mis en cache par le
    # navigateur ferait afficher le pictogramme par defaut sur un noeud qui a
    # DEJA sa vignette.
    assert r2.headers.get("cache-control") == "no-store", dict(r2.headers)

    # HORS LISTE BLANCHE -> 400 NOMME. `job.json` est le cas qui compte : il
    # est LISIBLE (JSON), il porte l'etat interne du noeud, et un motif de nom
    # a la `get_file` l'aurait servi sans un mot.
    r3 = _api("GET", f"/api/cards/{did}/forge3d/node-file/m1/job.json")
    assert r3.status_code == 400, r3.text
    assert "job.json" in r3.json()["detail"]
    assert (d / "job.json").is_file(), "le fichier existe : c'est bien la " \
        "liste blanche qui refuse, pas l'absence"

    # un nid en FORME DE SAUT -> 400 (le motif `_NID_RE` refuse le
    # separateur ET les noms qui ne sont que des points ; `_node_dir` est la
    # ceinture par-dessus les bretelles)
    for saut in ("..%5Cx", "%2E%2E", "a%2Fb"):
        r4 = _api("GET",
                  f"/api/cards/{did}/forge3d/node-file/{saut}/preview.png")
        assert r4.status_code in (400, 404), (saut, r4.status_code, r4.text)
        assert r4.status_code != 200, saut
    # ... et le refus du nid est bien un 400 quand la route est ATTEINTE
    # (un seul segment, hors charset)
    r5 = _api("GET", f"/api/cards/{did}/forge3d/node-file/..%5Cx/preview.png")
    assert r5.status_code == 400, r5.text

    # deck invalide / inconnu : les memes gardes que toute la piece
    r6 = _api("GET", "/api/cards/pas-un-deck/forge3d/node-file/m1/preview.png")
    assert r6.status_code == 400, r6.text
    r7 = _api("GET",
              "/api/cards/deck_00000000/forge3d/node-file/m1/preview.png")
    assert r7.status_code == 404, r7.text

    # M2 (ronde de correction 2c-T5) : LES OCTETS SONT LUS EN RAM (ecart
    # assume, voir la docstring de la route), et le chemin qui ECRIT ce
    # fichier — le telechargement de l'apercu chez le fournisseur — ne le
    # borne pas. Sans plafond ICI, une reponse de moteur inattendue devient
    # une lecture illimitee en memoire, une requete par onglet ouvert. Au-dela
    # de `_NODE_FILE_MAX` : 413 NOMME, jamais un 500, jamais un serveur qui
    # gonfle.
    from app.services.cards import forge3d as _F9
    apercu = d / "preview.png"
    garde = apercu.read_bytes()
    apercu.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * _F9._NODE_FILE_MAX)
    r8 = _api("GET", f"/api/cards/{did}/forge3d/node-file/m1/preview.png")
    assert r8.status_code == 413, (r8.status_code, r8.text)
    assert "lourd" in r8.json()["detail"], r8.text
    assert r8.headers.get("cache-control") == "no-store", dict(r8.headers)
    # ... et le plafond reste GENEREUX : une vraie vignette de moteur passe
    # toujours (une borne qui refuserait le cas nominal serait une panne
    # deguisee en garde).
    assert len(garde) < _F9._NODE_FILE_MAX, (len(garde), _F9._NODE_FILE_MAX)
    apercu.write_bytes(garde)
    r9 = _api("GET", f"/api/cards/{did}/forge3d/node-file/m1/preview.png")
    assert r9.status_code == 200, r9.text


# ── LA REGLE DE COTE (2d, tache 1) : LE VERSO EST LA CARTE RETOURNEE ────────
# P8 FAIT FOI, et ces tests le MESURENT au lieu de le croire : recto plat +z
# sens direct, verso plat -z sens INVERSE (solid.py:532-545), `uv_back` miroir
# en U parce que « vu de -Z la droite de l'ecran est -x » (solid.py:513-522).
# P9 obtient la MEME physique sans toucher un maillage : l'element est construit
# en ESPACE RECTO (memes quad/relief, memes UV, meme TANGENT local) puis LA
# CARTE EST RETOURNEE — rotation PROPRE de 180 degres autour de la verticale
# qui passe par le MILIEU de la carte, (x, y, z) -> (w_mm - x, y, -z).
#
# Ces mesures se font sur les OCTETS LIVRES (les accesseurs du GLB, les
# matrices de noeuds composees par le module scene lui-meme), jamais sur les
# intentions du writer — et le controle de lisibilite est LITTERALEMENT
# l'instrument de P8 (`solid.face_orientation`), applique aux quads de P9.
# Importer P8 depuis un TEST n'enfreint pas la regle 8 (zero import
# piece->piece dans le CODE) : c'est meme tout l'interet, la convention est
# celle de P8, elle doit etre jugee par le juge de P8.

def _exporte_les_deux_cotes(did):
    _exporter_couches(did, side="front")
    _exporter_couches(did, side="back")


def _elements_monde(glb: bytes) -> list:
    """Les enfants de la racine, en coordonnees MONDE, DANS L'ORDRE.

    Une LISTE et pas un dictionnaire par nom : deux couches homonymes des deux
    cotes d'une carte portent le MEME nom d'element (le writer le dit deja de
    ses propres aveux) — les indexer par nom en perdrait une en silence.

    Chaque entree : {name, positions, normals, uvs, indices}, positions passees
    par la matrice COMPOSEE racine x element (donc l'echelle physique mm->m
    comprise), normales par la seule PARTIE LINEAIRE puis renormalisees."""
    from app.services.cards import forge3d_scene as SC
    doc, binv = SC.read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    m_rac = SC._node_matrix(racine)
    out = []
    for k in racine["children"]:
        nd = doc["nodes"][k]
        if not isinstance(nd.get("mesh"), int):
            continue
        m = SC._mat4_mul(m_rac, SC._node_matrix(nd))
        prim = doc["meshes"][nd["mesh"]]["primitives"][0]
        a = prim["attributes"]
        brut = SC._accessor_floats(doc, binv, a["NORMAL"])
        nrm = []
        for i in range(0, len(brut) - 2, 3):
            v = [m[0] * brut[i] + m[4] * brut[i + 1] + m[8] * brut[i + 2],
                 m[1] * brut[i] + m[5] * brut[i + 1] + m[9] * brut[i + 2],
                 m[2] * brut[i] + m[6] * brut[i + 1] + m[10] * brut[i + 2]]
            ln = math.sqrt(sum(c * c for c in v)) or 1.0
            nrm += [c / ln for c in v]
        out.append({
            "name": nd.get("name"),
            "positions": SC._applique_mat4(
                SC._accessor_floats(doc, binv, a["POSITION"]), m),
            "normals": nrm,
            "uvs": SC._accessor_floats(doc, binv, a["TEXCOORD_0"]),
            "indices": SC._accessor_indices(doc, binv, prim["indices"])})
    return out


def _fusionne_monde(els: list) -> dict:
    """Les elements monde CONCATENES en UN maillage — la forme exacte que
    `solid.face_orientation` (P8) sait juger."""
    pos, nrm, uv, idx = [], [], [], []
    for el in els:
        base = len(pos) // 3
        pos += el["positions"]
        nrm += el["normals"]
        uv += el["uvs"]
        idx += [base + i for i in el["indices"]]
    return {"positions": pos, "normals": nrm, "uvs": uv, "indices": idx}


def _bbox(el: dict) -> list:
    p = el["positions"]
    return [[min(p[c::3]), max(p[c::3])] for c in range(3)]


def _centre(el: dict) -> list:
    return [(lo + hi) / 2.0 for lo, hi in _bbox(el)]


def _sens_image_droite(el: dict) -> list:
    """La direction MONDE de « la droite de l'image » (u croissant) : du sommet
    de u minimal a celui de u maximal, pris sur la MEME ligne v (le bas de
    l'image). C'est l'esprit de `face_orientation` reduit a un vecteur —
    l'imprimeur qui pose le doigt sur le bord droit du dessin et regarde ou il
    atterrit."""
    uv, p = el["uvs"], el["positions"]
    n = len(uv) // 2
    vmax = max(uv[1::2])
    ligne = [i for i in range(n) if abs(uv[2 * i + 1] - vmax) < 1e-9]
    a = min(ligne, key=lambda i: uv[2 * i])
    b = max(ligne, key=lambda i: uv[2 * i])
    d = [p[3 * b + c] - p[3 * a + c] for c in range(3)]
    ln = math.sqrt(sum(c * c for c in d)) or 1.0
    return [c / ln for c in d]


def _angle_vu_de_sa_face(el: dict, verso: bool) -> float:
    """L'angle (degres) de « la droite de l'image » DANS LE REPERE DE CELUI QUI
    REGARDE CETTE FACE : droite = +x monde au recto, -x monde au verso (on est
    passe derriere) ; haut = +y monde des deux cotes. C'est la definition meme
    du WYSIWYG : a rot_deg egal, cet angle doit etre LE MEME des deux cotes."""
    d = _sens_image_droite(el)
    return math.degrees(math.atan2(d[1], -d[0] if verso else d[0]))


def _graphe_recto_verso(role_f="cadre", role_b="illustration", depth=0.35):
    return {"nodes": [
        {"id": "sf", "kind": "layer", "role": role_f, "side": "front"},
        {"id": "pf", "kind": "plane", "depth_mm": depth},
        {"id": "sb", "kind": "layer", "role": role_b, "side": "back"},
        {"id": "pb", "kind": "plane", "depth_mm": depth},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "rectoverso"}],
        "edges": [{"from": "sf", "to": "pf"}, {"from": "pf", "to": "asm"},
                  {"from": "sb", "to": "pb"}, {"from": "pb", "to": "asm"},
                  {"from": "asm", "to": "art"}]}


def _build(did, graphe):
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": graphe, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    glb = _api("GET",
               f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    return b, glb


@pytest.mark.parametrize("fmt", ["poker_eu", "jumbo"])
def test_le_verso_du_graphe_est_la_carte_retournee(fmt):
    """2d/T1 — LES DEUX PILES NE SE CROISENT PAS, LES NORMALES S'OPPOSENT, ET
    LE VERSO SE LIT A L'ENDROIT QUAND ON LE REGARDE.

    Un graphe 2 couches (une recto, une verso, meme profondeur de plan 0,35) :
      1. tous les z monde du quad verso < 0, tous ceux du recto > 0 (signes
         STRICTS — pas de chevauchement au plan median) ;
      2. normales monde exactement opposees (+z / -z) ;
      3. « la droite de l'image » atterrit en -x monde au verso, +x au recto —
         le retournement GAUCHE-DROITE d'une vraie carte. C'EST CE POINT-CI,
         avec le 5, QUI PORTE LA DISTINCTION gauche-droite / tete-beche ;
      4. le verdict de P8 lui-meme (`face_orientation`) sur le maillage monde
         concatene : chaque face est CLASSEE du bon cote par sa normale, et
         son sens de parcours UV s'accorde a son sens de parcours a l'ecran
         (zero miroir des deux cotes). PORTEE EXACTE, mesuree en revue
         adverse : ce verdict ne separe PAS un demi-tour gauche-droite d'un
         demi-tour tete-beche — TOUTE rotation de 180 degres dans le plan
         preserve le produit det_img x det_scr, donc un imposteur R_x(pi)
         coherent passerait ici. Il prouve la coherence normale/UV/ecran, pas
         l'axe du retournement ;
      5. l'EMPREINTE est conservee : les deux faces se superposent en x/y au
         lieu de se poser cote a cote (la rotation passe par le MILIEU de la
         carte, pas par son coin).

    DEUX FORMATS, et ce n'est pas de la garniture (N4, revue adverse) : les
    cotes imperiales (jumbo 88,9 mm) ne sont pas representables en float32 —
    l'aller-retour d'accesseur laisse ~1,5e-9 m de residu de quantification,
    juste au-dela de la tolerance 1e-9 qu'un test poker_eu (63,0 mm, exact au
    bit) n'aurait jamais fait sonner. La tolerance est donc EXERCEE, pas
    supposee."""
    from app.services.cards import forge3d_scene as SC
    from app.services.cards.core import read_deck, geom_of
    from app.services.cards.solid import face_orientation
    did = _deck(f"Verso {fmt}", fmt=fmt)
    w_mm = geom_of(read_deck(did)).trim_mm[0]
    _exporte_les_deux_cotes(did)
    b, glb = _build(did, _graphe_recto_verso())

    # 1. les deux piles, SIGNEES — mesure globale d'abord (glb_scene_mesh,
    #    world=True : la scene telle qu'elle sera VUE), puis element par
    #    element pour dire LEQUEL est en dessous.
    monde = SC.glb_scene_mesh(glb, world=True)
    zs = monde["positions"][2::3]
    assert len(zs) == 8, len(zs)                     # deux quads
    assert len([z for z in zs if z > 0]) == 4, zs
    assert len([z for z in zs if z < 0]) == 4, zs
    els = _elements_monde(glb)
    assert [e["name"] for e in els] == ["cadre", "illustration_verso"], els
    recto, verso = els[0], els[1]
    assert all(z > 0 for z in recto["positions"][2::3]), _bbox(recto)
    assert all(z < 0 for z in verso["positions"][2::3]), _bbox(verso)
    assert _bbox(recto)[2] == pytest.approx([0.00035, 0.00035], abs=1e-12)
    assert _bbox(verso)[2] == pytest.approx([-0.00035, -0.00035], abs=1e-12)

    # 2. normales monde opposees, exactement
    for i in range(0, len(recto["normals"]), 3):
        assert recto["normals"][i:i + 3] == pytest.approx([0.0, 0.0, 1.0],
                                                          abs=1e-6)
    for i in range(0, len(verso["normals"]), 3):
        assert verso["normals"][i:i + 3] == pytest.approx([0.0, 0.0, -1.0],
                                                          abs=1e-6)

    # 3. LISIBILITE : la droite de l'image, mesuree
    assert _sens_image_droite(recto) == pytest.approx([1.0, 0.0, 0.0], abs=1e-6)
    assert _sens_image_droite(verso) == pytest.approx([-1.0, 0.0, 0.0], abs=1e-6)

    # 4. LE JUGE DE P8, sur la geometrie de P9 (portee : voir la docstring)
    fo = face_orientation(_fusionne_monde(els))
    assert fo["recto"]["triangles"] == 2 and fo["recto"]["miroir"] == 0, fo
    assert fo["verso"]["triangles"] == 2 and fo["verso"]["miroir"] == 0, fo
    assert fo["ok"] is True, fo

    # 5. EMPREINTE CONSERVEE : la carte se retourne autour de son MILIEU, elle
    #    ne bascule pas autour de son coin — sinon les deux faces se posent
    #    cote a cote et la « carte » mesure deux fois sa largeur.
    #    TOLERANCE 1e-8 m (10 nm) et non 1e-9 : voir la docstring — jumbo
    #    laisse 1,5e-9 m de residu float32, et une borne qui casse sur un
    #    format legitime est une panne deguisee en garde.
    assert _bbox(verso)[0] == pytest.approx(_bbox(recto)[0], abs=1e-8)
    assert _bbox(verso)[1] == pytest.approx(_bbox(recto)[1], abs=1e-8)
    assert _bbox(recto)[0] == pytest.approx([0.0, w_mm * 0.001], abs=1e-8)

    # ... et rien n'a ete perdu en chemin : deux elements, aucun aveu.
    assert b["elements"] == 2 and b["ignored"] == [], b
    # M3 (revue adverse) : deux couches HOMONYMES des deux cotes ne doivent pas
    # sortir deux noeuds « cadre » que Blender renommerait cadre/cadre.001, et
    # le bordereau doit DIRE le cote. Le suffixe ne touche QUE le verso : un
    # GLB recto seul garde ses octets (pin de non-regression plus bas).
    detail = {e["name"]: e for e in b["elements_detail"]}
    assert set(detail) == {"cadre", "illustration_verso"}, detail
    assert "side" not in detail["cadre"], detail["cadre"]
    assert detail["illustration_verso"]["side"] == "back", detail


def test_deux_couches_du_meme_role_des_deux_cotes_ne_sont_pas_homonymes():
    """M3 (revue adverse) — LE MEME ROLE DES DEUX COTES SORTAIT DEUX FOIS LE
    MEME NOM. Un GLB recto+verso portait ['cadre', 'cadre'] : Blender importe
    cadre / cadre.001, et le bordereau ne disait nulle part LEQUEL etait le
    verso. Le nom d'un element de verso porte donc le suffixe `_verso` —
    noeud, maillage ET materiau, puisque le writer les nomme tous les trois du
    meme mot — et `elements_detail` gagne une cle `side`.

    LE SUFFIXE NE TOUCHE QUE LE VERSO, et c'est la moitie qui compte : un
    artefact recto seul (l'immense majorite, et tout ce qui a ete construit
    avant la 2d) garde ses octets a l'identique. Verifie ici structurellement
    (aucune occurrence du mot, aucune cle `side`) et, au moment du correctif,
    par comparaison de sha256 avant/apres sur une construction recto complete
    (plan + relief + transform)."""
    did = _deck("Homonymes")
    _exporte_les_deux_cotes(did)
    b, glb = _build(did, _graphe_recto_verso(role_f="cadre", role_b="cadre"))
    doc, _ = _read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    assert noms == ["cadre", "cadre_verso"], noms
    assert len(set(noms)) == len(noms), noms
    # le MATERIAU et le MAILLAGE portent le meme mot que le noeud : un
    # importateur qui deduplique par nom de materiau fusionnerait les deux
    # faces d'une carte en une seule.
    assert sorted(m["name"] for m in doc["materials"]) == ["cadre",
                                                           "cadre_verso"]
    assert sorted(m["name"] for m in doc["meshes"]) == ["cadre", "cadre_verso"]
    detail = {e["name"]: e for e in b["elements_detail"]}
    assert detail["cadre_verso"]["side"] == "back", detail
    assert "side" not in detail["cadre"], detail

    # ... et un artefact RECTO SEUL n'apprend rien de tout ca : ni le mot, ni
    # la cle. C'est la garantie de non-regression a l'octet, dite en structure.
    g_recto = {"nodes": [n for n in _graphe_recto_verso()["nodes"]
                         if n["id"] not in ("sb", "pb")],
               "edges": [e for e in _graphe_recto_verso()["edges"]
                         if e["from"] not in ("sb", "pb")]}
    g_recto["nodes"] = [dict(n, name="rectoseul") if n["kind"] == "artifact"
                        else n for n in g_recto["nodes"]]
    b_r, glb_r = _build(did, g_recto)
    doc_r, _ = _read_glb(glb_r)
    assert "verso" not in json.dumps(doc_r), "le recto seul a appris le verso"
    assert all("side" not in e for e in b_r["elements_detail"]), b_r


def test_le_transform_verso_pousse_dans_le_plan_de_la_face_regardee():
    """2d/T1 — x_mm/z_mm SIGNES par le cote, rot_deg WYSIWYG des deux cotes.

    Quatre chaines dans UN graphe : recto et verso avec le MEME transform
    (x=+5, z=1), puis recto et verso avec le MEME rot_deg (+90).

      · x_mm=+5 pousse vers +x monde au recto, vers -x monde au verso (la
        DROITE DE CELUI QUI REGARDE cette face) ; z_mm=1 empile vers +z au
        recto, vers -z au verso. Les valeurs postees restent >= 0 : le SIGNE
        appartient a la regle de cote, aucune borne ne bouge.
      · rot_deg tourne du MEME angle vu de sa propre face — c'est la DEFINITION
        du WYSIWYG, et c'est ce qui epingle l'ORDRE de composition
        R_y(pi) o R_z(rot_deg) : l'ordre inverse ferait voir -rot_deg au verso.
        LE CHOIX DE L'ANGLE (corrige en revue adverse, M2 — la justification
        precedente etait FAUSSE) : la separation des deux ordres vaut
        2 |sin(rot_deg)| en repere verso, donc les angles DEGENERES sont 0 et
        180 (sin = 0, les deux ordres coincident) et 90 est au contraire celui
        qui SEPARE LE PLUS. 30 est retenu parce qu'il est loin des deux
        degenerescences (separation 1,0) tout en restant un angle oblique, ou
        x ET y sont non nuls : la mesure ne peut donc pas passer par
        accident sur une composante qui s'annule.
      · le quaternion du noeud verso est relu tel quel dans les octets :
        (sin(d/2), cos(d/2), 0, 0) — un demi-tour autour d'un axe du plan XY."""
    did = _deck("Transform verso")
    _exporte_les_deux_cotes(did)
    tr = {"kind": "transform", "x_mm": 5.0, "y_mm": 0.0, "z_mm": 1.0,
          "rot_deg": 0.0, "scale": 1.0}
    rot = {"kind": "transform", "x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0,
           "rot_deg": 30.0, "scale": 1.0}
    g = {"nodes": [
        {"id": "sf", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "pf", "kind": "plane", "depth_mm": 0.0},
        {"id": "trf", **tr},
        {"id": "sb", "kind": "layer", "role": "cadre", "side": "back"},
        {"id": "pb", "kind": "plane", "depth_mm": 0.0},
        {"id": "trb", **tr},
        {"id": "sf2", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "pf2", "kind": "plane", "depth_mm": 0.0},
        {"id": "rof", **rot},
        {"id": "sb2", "kind": "layer", "role": "illustration", "side": "back"},
        {"id": "pb2", "kind": "plane", "depth_mm": 0.0},
        {"id": "rob", **rot},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "trsverso"}],
        "edges": [{"from": "sf", "to": "pf"}, {"from": "pf", "to": "trf"},
                  {"from": "trf", "to": "asm"},
                  {"from": "sb", "to": "pb"}, {"from": "pb", "to": "trb"},
                  {"from": "trb", "to": "asm"},
                  {"from": "sf2", "to": "pf2"}, {"from": "pf2", "to": "rof"},
                  {"from": "rof", "to": "asm"},
                  {"from": "sb2", "to": "pb2"}, {"from": "pb2", "to": "rob"},
                  {"from": "rob", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    b, glb = _build(did, g)
    assert b["elements"] == 4 and b["ignored"] == [], b
    els = _elements_monde(glb)
    assert len(els) == 4, [e["name"] for e in els]
    c_rec, c_ver = _centre(els[0]), _centre(els[1])
    # x : +5 mm au recto, -5 mm au verso, a partir du MEME milieu de carte
    assert c_rec[0] == pytest.approx((63.0 / 2.0 + 5.0) * 0.001, abs=1e-9)
    assert c_ver[0] == pytest.approx((63.0 / 2.0 - 5.0) * 0.001, abs=1e-9)
    # y : jamais retourne (P8 : « en bas = -y des deux cotes »)
    assert c_ver[1] == pytest.approx(c_rec[1], abs=1e-9)
    # z : +1 mm au recto, -1 mm au verso
    assert c_rec[2] == pytest.approx(0.001, abs=1e-12)
    assert c_ver[2] == pytest.approx(-0.001, abs=1e-12)

    # rot_deg : le MEME angle vu de sa propre face — WYSIWYG prouve, pas cru
    assert _angle_vu_de_sa_face(els[2], verso=False) == pytest.approx(30.0,
                                                                      abs=1e-4)
    assert _angle_vu_de_sa_face(els[3], verso=True) == pytest.approx(30.0,
                                                                     abs=1e-4)
    # ... et le vecteur BRUT, en clair, pour que la separation des deux ordres
    #     de composition se lise sans trigonometrie : x oppose, y IDENTIQUE.
    d_rec = _sens_image_droite(els[2])
    d_ver = _sens_image_droite(els[3])
    assert d_ver[0] == pytest.approx(-d_rec[0], abs=1e-9), (d_rec, d_ver)
    assert d_ver[1] == pytest.approx(d_rec[1], abs=1e-9), (d_rec, d_ver)
    assert d_rec[1] > 0.4, d_rec          # oblique : le y ne s'annule PAS
    # ... et la meme chose a 0 degre, sur les deux premieres chaines
    assert _angle_vu_de_sa_face(els[0], verso=False) == pytest.approx(0.0,
                                                                      abs=1e-4)
    assert _angle_vu_de_sa_face(els[1], verso=True) == pytest.approx(0.0,
                                                                     abs=1e-4)
    # le quaternion, dans les octets : demi-tour autour d'un axe du plan XY
    doc, _ = _read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    d2 = math.radians(30.0) / 2.0
    q_ver = doc["nodes"][racine["children"][3]]["rotation"]
    assert q_ver == pytest.approx([math.sin(d2), math.cos(d2), 0.0, 0.0],
                                 abs=1e-12), q_ver
    # le recto, lui, garde EXACTEMENT le quaternion z de la 2a
    q_rec = doc["nodes"][racine["children"][2]]["rotation"]
    assert q_rec == pytest.approx([0.0, 0.0, math.sin(d2), math.cos(d2)],
                                 abs=1e-12), q_rec
    # ... et un element verso SANS rotation utilisateur porte quand meme la
    # sienne (le demi-tour n'est pas une valeur par defaut sous-entendue)
    assert doc["nodes"][racine["children"][1]]["rotation"] == pytest.approx(
        [0.0, 1.0, 0.0, 0.0], abs=1e-12)
    assert "rotation" not in doc["nodes"][racine["children"][0]]


def test_le_stl_verso_garde_le_prouve_ou_refuse_et_descend_sous_le_plan():
    """2d/T1 — LE STL NE CHANGE PAS DE SEMANTIQUE AU VERSO, et il montre LA
    MEME CHOSE QUE LE GLB (le format n'a pas de noeud : le retournement doit
    etre CUIT dans les sommets, comme le fit d'un externe).

      · un plan verso seul : STL REFUSE, au motif MOT POUR MOT de son jumeau
        recto (un plan n'est pas un solide, des deux cotes) ;
      · un relief verso seul : STL ECRIT, meme empreinte x/y que son jumeau
        recto, mais extrude vers -z ;
      · S1 (revue adverse) — ET D'ABORD : LE STL EST COMPARE AU GLB DE LA MEME
        CONSTRUCTION, sur un relief verso qui traverse un `transform` A ANGLE
        OBLIQUE. Le jumeau recto a rot=0 ne suffisait PAS : a cet angle-la les
        deux ordres de composition coincident, et un mutant qui retourne AVANT
        de tourner (au lieu d'apres) sortait 102/102 VERT en imprimant une
        piece a 53 mm de l'apercu, bordereau `written: true`. Les deux sorties
        d'une meme construction doivent montrer LA MEME CHOSE.

    PORTEE DE CHAQUE MESURE, mesuree par mutation et non supposee : l'accord
    STL<->GLB est le SEUL juge de l'INVERSION (aucune autre assertion ne la
    voit) ; il voit aussi l'OUBLI ; il ne peut PAS, par construction, voir une
    faute de PIVOT — celle-la deplace les DEUX sorties du meme montant, donc
    elles restent d'accord entre elles. C'est le jumeau recto (empreinte x/y
    identique) qui la tient, et c'est pour cela que les deux mesures
    coexistent ici au lieu que la seconde remplace la premiere."""
    did = _deck("STL verso")
    _exporte_les_deux_cotes(did)

    def graphe(kind, side, nom, rot=None):
        proc = ({"id": "t", "kind": "plane", "depth_mm": 0.35}
                if kind == "plane" else
                {"id": "t", "kind": "relief", "depth_mm": 1.0,
                 "base_mm": 0.3, "grid": 48})
        g = {"nodes": [
            {"id": "s", "kind": "layer", "role": "cadre", "side": side},
            proc,
            {"id": "asm", "kind": "assemble"},
            {"id": "art", "kind": "artifact", "name": nom}],
            "edges": [{"from": "s", "to": "t"}, {"from": "t", "to": "asm"},
                      {"from": "asm", "to": "art"}]}
        if rot is None:
            return g
        g["nodes"].insert(2, {"id": "tr", "kind": "transform", "x_mm": 4.0,
                              "y_mm": -2.0, "z_mm": 1.5, "rot_deg": rot,
                              "scale": 1.0})
        g["edges"] = [{"from": "s", "to": "t"}, {"from": "t", "to": "tr"},
                      {"from": "tr", "to": "asm"}, {"from": "asm", "to": "art"}]
        return g

    # ── S1 D'ABORD : LES DEUX SORTIES D'UNE MEME CONSTRUCTION, A ANGLE
    #    OBLIQUE. 37 degres : ni 0 ni 90 ni 180 — aucun ordre de composition
    #    n'y coincide avec un autre. La comparaison ne se fait PAS avec un
    #    jumeau recto (deux constructions differentes peuvent etre fausses de
    #    la meme facon) mais avec le GLB DE CETTE construction-ci : le STL est
    #    en MILLIMETRES, le GLB en metres (racine mm->m), l'ecart tolere est
    #    5 microns.
    from app.services.cards import forge3d_scene as SC
    b_ro, glb_ro = _build(did, graphe("relief", "back", "reliefverso37", 37.0))
    assert b_ro["stl"]["written"] is True, b_ro["stl"]
    stl_o = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                 + b_ro["stl"]["name"]).content
    lo_o, hi_o = _stl_bbox(stl_o)
    mo = SC.glb_scene_mesh(glb_ro, world=True)["positions"]
    for c in range(3):
        assert lo_o[c] == pytest.approx(min(mo[c::3]) * 1000.0, abs=5e-3), c
        assert hi_o[c] == pytest.approx(max(mo[c::3]) * 1000.0, abs=5e-3), c
    # ... et l'oblique a VRAIMENT tourne quelque chose (sinon la comparaison
    # ci-dessus retomberait sur le cas rot=0 plus bas, sans le dire) : une
    # carte de 63 mm tournee de 37 degres couvre plus de 100 mm en x.
    assert hi_o[0] - lo_o[0] > 100.0, (lo_o, hi_o)
    assert hi_o[2] == pytest.approx(-1.5, abs=1e-3), hi_o   # z_mm=1.5 -> -1,5

    b_pf, _ = _build(did, graphe("plane", "front", "planrecto"))
    b_pb, _ = _build(did, graphe("plane", "back", "planverso"))
    assert b_pf["stl"]["written"] is False and b_pb["stl"]["written"] is False
    assert b_pb["stl"]["why"] == b_pf["stl"]["why"], (b_pb["stl"], b_pf["stl"])

    b_rf, _ = _build(did, graphe("relief", "front", "reliefrecto"))
    b_rb, _ = _build(did, graphe("relief", "back", "reliefverso"))
    assert b_rf["stl"]["written"] is True and b_rb["stl"]["written"] is True
    stl_f = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                 + b_rf["stl"]["name"]).content
    stl_b = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                 + b_rb["stl"]["name"]).content
    lo_f, hi_f = _stl_bbox(stl_f)
    lo_b, hi_b = _stl_bbox(stl_b)
    # meme nombre de facettes : le maillage n'a PAS change, sa place si
    assert (struct.unpack("<I", stl_f[80:84])[0]
            == struct.unpack("<I", stl_b[80:84])[0])
    # empreinte x/y IDENTIQUE (retournement autour du milieu), z OPPOSE
    for c in (0, 1):
        assert lo_b[c] == pytest.approx(lo_f[c], abs=1e-3), c
        assert hi_b[c] == pytest.approx(hi_f[c], abs=1e-3), c
    assert lo_f[2] == pytest.approx(0.0, abs=1e-6) and hi_f[2] > 1.0
    assert hi_b[2] == pytest.approx(0.0, abs=1e-6)
    assert lo_b[2] == pytest.approx(-hi_f[2], abs=1e-4), (lo_b, hi_f)


def test_node_preview_d_un_element_verso_le_montre_deja_retourne():
    """2d/T1 — L'INSPECTEUR MONTRE CE QUE LE BUILD CONSTRUIRA. `element_local`
    est la MEME fonction des deux cotes : un aperçu de noeud verso doit sortir
    200 et vivre SOUS le plan median (z <= 0 monde), plan comme relief."""
    from app.services.cards import forge3d_scene as SC
    did = _deck("Apercu verso")
    _exporte_les_deux_cotes(did)

    def apercu(proc):
        g = {"nodes": [
            {"id": "s", "kind": "layer", "role": "cadre", "side": "back"},
            proc,
            {"id": "asm", "kind": "assemble"},
            {"id": "art", "kind": "artifact", "name": "x"}],
            "edges": [{"from": "s", "to": "t"}, {"from": "t", "to": "asm"},
                      {"from": "asm", "to": "art"}]}
        r = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
                 json={"graph": g, "card": 0, "nid": "t"})
        assert r.status_code == 200, r.text
        return SC.glb_scene_mesh(r.content, world=True)["positions"][2::3]

    z_plan = apercu({"id": "t", "kind": "plane", "depth_mm": 0.35})
    assert z_plan and all(z < 0 for z in z_plan), z_plan
    z_rel = apercu({"id": "t", "kind": "relief", "depth_mm": 1.0,
                    "base_mm": 0.3, "grid": 48})
    assert all(z <= 1e-12 for z in z_rel), max(z_rel)
    assert min(z_rel) < 0, min(z_rel)


def test_le_maillage_de_moteur_d_une_couche_verso_est_retourne_comme_elle():
    """2d/T1 — UN mesh3d VERSO SUIT SA COUCHE. Le fit ne change pas (la boite
    de couche est deja lue dans le manifeste du bon cote) : c'est le MEME
    retournement qui s'applique par-dessus. Prouve en construisant DEUX FOIS
    le meme graphe, cote pour cote, et en comparant les deux TRS de parent —
    aucun chiffre recopie a la main."""
    did = _deck("Moteur verso")
    _exporte_les_deux_cotes(did)
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="meshy-7")

    def graphe(side, nom):
        return {"nodes": [
            {"id": "s1", "kind": "layer", "role": "illustration", "side": side},
            {"id": "m1", "kind": "mesh3d", "engine": "meshy-7",
             "texture_prompt": "", "ultra": False},
            {"id": "tr", "kind": "transform", "x_mm": 3.0, "y_mm": 0.0,
             "z_mm": 2.0, "rot_deg": 0.0, "scale": 1.0},
            {"id": "asm", "kind": "assemble"},
            {"id": "art", "kind": "artifact", "name": nom}],
            "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "tr"},
                      {"from": "tr", "to": "asm"}, {"from": "asm", "to": "art"}]}

    def parent(nom, side):
        _b, glb = _build(did, graphe(side, nom))
        doc, _ = _read_glb(glb)
        racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
        return doc["nodes"][racine["children"][0]]

    p_f = parent("moteurrecto", "front")
    p_b = parent("moteurverso", "back")
    assert p_b["scale"] == p_f["scale"]                    # le fit est le MEME
    assert p_b["translation"][0] == pytest.approx(63.0 - p_f["translation"][0],
                                                  abs=1e-9)
    assert p_b["translation"][1] == pytest.approx(p_f["translation"][1],
                                                  abs=1e-9)
    assert p_b["translation"][2] == pytest.approx(-p_f["translation"][2],
                                                  abs=1e-9)
    assert "rotation" not in p_f
    assert p_b["rotation"] == pytest.approx([0.0, 1.0, 0.0, 0.0], abs=1e-12)


def test_publier_dans_la_bibliotheque_est_idempotent():
    """POST /forge3d/library/{art} (Task 6, 2c) : un JobRecord provider=card3d
    + une COPIE dans outputs/assets3d/{short}/ pour que les routes EXISTANTES
    de la Bibliotheque 3D servent le modele sans une ligne de plus. Re-publier
    MET A JOUR, ne duplique pas — l'id est DERIVE (uuid5 deck/artefact), donc
    l'idempotence est une propriete de construction, pas une verification."""
    from app.config import settings as cfg
    from app.services.storage import init_db
    # le JobRecord vit en base, et les tests n'executent pas le `lifespan` de
    # l'application : les tables n'existent pas encore ici (meme preambule que
    # le test du job meshy, plus haut).
    asyncio.run(init_db())
    did = _deck("Bibliotheque")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    # SANS BUILD -> 409 NOMME, et il tombe AVANT toute ecriture : rien n'est
    # publie tant que rien n'est construit.
    r0 = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d")
    assert r0.status_code == 409, r0.text
    assert "construis" in r0.json()["detail"], r0.text

    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    r = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d")
    assert r.status_code == 200, r.text
    pub = r.json()
    assert pub["provider"] == "card3d" and pub["short"], pub
    assert pub["short"] == pub["job_id"][:8], pub

    # LE GLB EST SERVI PAR LA ROUTE EXISTANTE — c'est TOUT le pari de la
    # tache : aucune route neuve cote Bibliotheque, seulement la disposition
    # de fichiers que `/api/assets/3d/{short}/{fmt}` lit deja (model.{fmt}).
    r2 = _api("GET", f"/api/assets/3d/{pub['short']}/glb")
    assert r2.status_code == 200, r2.text
    assert r2.content[:4] == b"glTF", r2.content[:16]
    depot = (_dossier_forge3d(did) / "carte3d.glb").read_bytes()
    assert r2.content == depot, "la copie doit etre l'artefact, a l'octet"
    # ... et le manifeste de la Bibliotheque voit le format, sans vignette
    # encore (« figer l'apercu » n'a pas tourne) : l'ABSENCE est toleree.
    man = _api("GET", f"/api/assets/3d/{pub['short']}/manifest")
    assert man.status_code == 200 and man.json()["formats"] == ["glb"], man.text
    assert man.json()["has_preview"] is False, man.text
    # le metadata voyage AUSSI (bonus honnete : la provenance reste lisible a
    # cote du modele, meme si aucune route ne la sert aujourd'hui)
    d3d = cfg.outputs_path / "assets3d" / pub["short"]
    assert (d3d / "metadata.json").is_file(), sorted(p.name for p in d3d.iterdir())

    # LE JobRecord, LU PAR LA ROUTE DE LA FILE (la forme reelle de /api/jobs :
    # `job_id`, pas `id`)
    jobs = _api("GET", "/api/jobs").json()
    moi = [j for j in jobs if j.get("job_id") == pub["job_id"]]
    assert len(moi) == 1, [j.get("job_id") for j in jobs]
    assert moi[0]["provider"] == "card3d", moi[0]
    assert moi[0]["status"] == "done", moi[0]
    # le TITRE nomme le deck ET l'artefact : dans une bibliotheque melangee,
    # « asset3d_1a2b3c4d » ne dit rien de ce qu'on regarde.
    assert "Bibliotheque" in moi[0]["title"] and "carte3d" in moi[0]["title"], \
        moi[0]["title"]
    # ECART ASSUME AU PLAN, MESURE ICI : `final_video_path` reste VIDE. Trois
    # ecrans de l'app listent les rendus par
    # `status==="done" && final_video_path && provider!=="asset3d"` (la
    # Bibliotheque onglet rendus, le selecteur « Existing render » du Studio,
    # le Scheduler) : y poser le chemin du GLB aurait fait apparaitre la carte
    # comme une VIDEO dans les trois, avec un lecteur qui ne peut pas l'ouvrir.
    # Un GLB n'est pas un rendu video, et la colonne ne ment pas.
    assert not moi[0]["final_video_path"], moi[0]
    # M6 (ronde de correction T6) : `image_filename` est NON NUL en base, et
    # ce n'est PAS « preview.png » — ce nom-la PASSE le controle d'extension du
    # tiroir de file d'attente du bundle, qui le resoudrait en
    # `/api/images/preview.png`, c'est-a-dire une image de la bibliotheque
    # d'images SANS AUCUN RAPPORT si elle existe. Un nom derive sans extension
    # ne peut pas etre pris pour un fichier d'images : il ne designe rien, ce
    # qui est la verite (la vignette de l'onglet 3D vient du SHORT).
    assert moi[0]["image_filename"] == f"card3d_{pub['short']}", moi[0]
    assert not str(moi[0]["image_filename"]).lower().endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".gif")), moi[0]

    # IDEMPOTENT : meme artefact -> meme id, aucun doublon, et la copie est
    # RAFRAICHIE (l'artefact a pu etre reconstruit entre-temps). Le corps JSON
    # est celui que l'ECRAN envoie REELLEMENT (`M.api.post` poste toujours un
    # objet, meme vide) : la route n'en lit rien, et ne doit pas s'en etouffer.
    r3 = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d", json={})
    assert r3.status_code == 200, r3.text
    assert r3.json()["job_id"] == pub["job_id"], (r3.json(), pub)
    jobs2 = _api("GET", "/api/jobs").json()
    assert len([j for j in jobs2 if j.get("job_id") == pub["job_id"]]) == 1

    # L'APERCU FIGE VOYAGE quand il existe — et la vignette de la Bibliotheque
    # (`/preview`) le sert alors, toujours sans route neuve.
    p_ap = _api("POST", f"/api/cards/{did}/forge3d/preview/carte3d",
                content=_png(Image.new("RGBA", (16, 16), (3, 4, 5, 255))))
    assert p_ap.status_code == 200, p_ap.text
    assert _api("POST", f"/api/cards/{did}/forge3d/library/carte3d"
                ).status_code == 200
    rv = _api("GET", f"/api/assets/3d/{pub['short']}/preview")
    assert rv.status_code == 200, rv.text
    assert rv.content == (_dossier_forge3d(did)
                          / "carte3d_preview.png").read_bytes()
    assert _api("GET", f"/api/assets/3d/{pub['short']}/manifest"
                ).json()["has_preview"] is True
    # TROUVAILLE T7 (navigateur reel) : la tuile 3D de la Bibliotheque pose
    # `/preview` en src PRIMAIRE et retombe UNE FOIS sur `/shot/0` par
    # `onError` (bundle : `dataset.f` garde le repli unique). Le second nom
    # n'existait nulle part dans nos dossiers — le repli tombait donc dans le
    # vide, et avec lui « Copier le shot dans la bibliotheque d'images »
    # (routes.py, /shot/{i}/save) et la liste `shots` du manifeste. L'apercu
    # fige voyage desormais SOUS LES DEUX NOMS : les memes octets, aux deux
    # endroits ou l'ecran sait les chercher.
    rs = _api("GET", f"/api/assets/3d/{pub['short']}/shot/0")
    assert rs.status_code == 200, rs.text
    assert rs.content == rv.content, "le repli doit servir LES MEMES octets"
    assert _api("GET", f"/api/assets/3d/{pub['short']}/manifest"
                ).json()["shots"] == [0]
    # M6 — ET SURTOUT ICI : la colonne ne devient PAS « preview.png » sous
    # pretexte qu'une vignette a voyage. (Mesure trouvee par mutation : la
    # premiere version de ce pin vivait AVANT que l'apercu existe, la ou les
    # deux ecritures rendent le meme nom — il ne mesurait donc rien.)
    apres = [j for j in _api("GET", "/api/jobs").json()
             if j.get("job_id") == pub["job_id"]]
    assert apres[0]["image_filename"] == f"card3d_{pub['short']}", apres[0]

    # UN AUTRE ARTEFACT DU MEME DECK EST UN AUTRE OBJET : l'id derive du
    # COUPLE (deck, artefact), pas du deck seul — sans quoi publier la carte 2
    # ecraserait la carte 1 dans la Bibliotheque.
    g2 = json.loads(json.dumps(g))
    g2["nodes"][3]["name"] = "carte3d-bis"
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g2, "card": 0}).status_code == 200
    autre = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d-bis")
    assert autre.status_code == 200, autre.text
    assert autre.json()["job_id"] != pub["job_id"], autre.json()

    # REFUS NOMMES — jamais un 500, jamais un chemin construit sur l'entree
    # brute (`..` est un nom d'artefact possible pour qui poste a la main).
    r4 = _api("POST", f"/api/cards/{did}/forge3d/library/jamais-construit")
    assert r4.status_code == 409, r4.text
    assert "construis" in r4.json()["detail"], r4.text
    r5 = _api("POST", f"/api/cards/{did}/forge3d/library/..")
    assert r5.status_code in (400, 404), r5.text
    assert r5.status_code != 200
    r6 = _api("POST", f"/api/cards/{did}/forge3d/library/pas%20un%20nom")
    assert r6.status_code == 400, r6.text
    r7 = _api("POST", "/api/cards/pas-un-deck/forge3d/library/carte3d")
    assert r7.status_code == 400, r7.text
    r8 = _api("POST", "/api/cards/deck_00000000/forge3d/library/carte3d")
    assert r8.status_code == 404, r8.text

    # LE NAMESPACE EST UN LITTERAL GELE — pin explicite (un mutant l'a montre
    # SURVIVANT). En changer la valeur ne casse rien de visible... et
    # ORPHELINE toutes les publications passees : les anciens dossiers
    # `{short}` restent sur le disque, plus aucun JobRecord ne les designe, et
    # re-publier fabrique un DOUBLON sous un nouveau short. Un id derive n'est
    # une promesse d'idempotence que si sa graine ne bouge jamais.
    from app.services.cards import forge3d as _F9b
    assert str(_F9b.NAMESPACE_CARD3D) == "ac928da5-740b-48d6-8913-93a83055aeeb"
    # ... et le short est bien LE prefixe de l'id, celui que l'ecran calcule
    # (`job_id.slice(0,8)`) et que `_delete_provider_output_dir` recalcule
    # (`job.id[:8]`) : une seule regle, verifiee ici sur un cas reel.
    assert pub["short"] == pub["job_id"][:8]


def test_republier_publie_L_ENSEMBLE_et_ne_tombe_jamais_en_500():
    """Ronde de correction T6 — trois défauts SONDÉS par la revue adverse :

      · S2 : re-publier ne faisait qu'ÉCRASER ce qui existe. Un artefact
        reconstruit SANS re-figer l'aperçu laissait la vignette de la
        publication PRÉCÉDENTE servie sous le même `short` (le rebuild efface
        pourtant le PNG périmé du deck), et un `model.opt.glb` d'« Optimiser »
        aurait continué de servir le maillage optimisé de l'ANCIEN modèle.
      · M5 : un metadata bien formé JSON mais de la mauvaise FORME
        (`[1,2,3]`, `{"attributes": 5}`) traversait le `except` et faisait un
        500 sur un fichier qu'on ne fait que RECOPIER.
      · M8 : `short` fait 32 bits et `asset3d` coupe un uuid4 au même endroit
        — publier par-dessus le dossier d'un maillage PAYÉ l'écraserait
        définitivement, et de façon REPRODUCTIBLE (notre id est déterministe).
    """
    from app.config import settings as cfg
    from app.services.storage import init_db
    asyncio.run(init_db())
    did = _deck("Republication")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "reptile"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    assert _api("POST", f"/api/cards/{did}/forge3d/preview/reptile",
                content=_png(Image.new("RGBA", (16, 16), (1, 2, 3, 255)))
                ).status_code == 200
    pub = _api("POST", f"/api/cards/{did}/forge3d/library/reptile").json()
    short = pub["short"]
    d3d = cfg.outputs_path / "assets3d" / short
    assert _api("GET", f"/api/assets/3d/{short}/preview").status_code == 200
    # ... sous les DEUX noms (trouvaille T7) : `/preview` est le src primaire
    # de la tuile, `/shot/0` son repli `onError`.
    assert _api("GET", f"/api/assets/3d/{short}/shot/0").status_code == 200
    assert "shot_0.png" in pub["files"], pub["files"]

    # ── S2 : la RECONSTRUCTION efface l'apercu perime du deck (`_efface`),
    # et re-publier doit RETIRER celui de la Bibliotheque. Sinon la vignette
    # illustre un modele qui n'existe plus.
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    assert not (_dossier_forge3d(did) / "reptile_preview.png").is_file()
    # ... on pose AUSSI les deux fichiers d'« Optimiser » (routes.py, chantier
    # 10a) : ils decrivent le maillage qu'on vient de remplacer.
    (d3d / "model.opt.glb").write_bytes(b"glTF-vieux-maillage-optimise")
    (d3d / "optimize.json").write_text('{"before":{"tris":1}}',
                                       encoding="utf-8")
    assert _api("POST", f"/api/cards/{did}/forge3d/library/reptile"
                ).status_code == 200
    assert _api("GET", f"/api/assets/3d/{short}/preview").status_code == 404, \
        "l'apercu de la publication PRECEDENTE reste servi"
    # ... et son JUMEAU part avec lui : une vignette retiree d'un cote et
    # gardee de l'autre, c'est la meme image periemee servie par le repli.
    assert _api("GET", f"/api/assets/3d/{short}/shot/0").status_code == 404, \
        "le repli `onError` sert encore l'apercu de la publication PRECEDENTE"
    assert not (d3d / "model.opt.glb").is_file(), \
        "le GLB optimise de l'ANCIEN maillage reste telechargeable"
    assert not (d3d / "optimize.json").is_file()
    # ... et le manifeste, qui est LE lecteur de ce dossier, le dit
    man = _api("GET", f"/api/assets/3d/{short}/manifest").json()
    assert man["has_preview"] is False, man
    assert man["formats"] == ["glb"], man
    assert man["shots"] == [], man
    # ... aucun temporaire de copie ne traine, et rien ne s'y annonce comme un
    # format (le `.tmp` porte un point de tete EXPRES).
    assert sorted(p.name for p in d3d.iterdir()) == ["metadata.json",
                                                     "model.glb"], \
        sorted(p.name for p in d3d.iterdir())

    # ── M5 : un metadata de la MAUVAISE FORME ne fait pas tomber la
    # publication. Le MODELE est bon — c'est lui qu'on publie.
    meta = _dossier_forge3d(did) / "reptile.metadata.json"
    for faux in ("[1, 2, 3]", '{"attributes": 5}', '{"attributes": [7]}',
                 '"une chaine"', "null"):
        meta.write_text(faux, encoding="utf-8")
        r = _api("POST", f"/api/cards/{did}/forge3d/library/reptile")
        assert r.status_code == 200, (faux, r.status_code, r.text)
        assert (d3d / "metadata.json").read_text(encoding="utf-8") == faux

    # ── M8 : le dossier `{short}` appartient DEJA a un autre objet 3D. On
    # fabrique la collision a la main (un JobRecord asset3d dont l'id partage
    # les 8 premiers hex) : publier doit REFUSER, nommement, AVANT d'ecrire.
    from app.services.storage import JobRecord, async_session_factory
    from app.models.schemas import JobStatus
    pub2 = _api("POST", f"/api/cards/{did}/forge3d/library/reptile").json()
    victime = pub2["short"] + "-dead-beef-cafe-000000000001"

    async def _pose():
        async with async_session_factory() as s:
            s.add(JobRecord(id=victime, provider="asset3d",
                            status=JobStatus.DONE.value, progress=100,
                            image_filename=f"asset3d_{pub2['short']}",
                            title="un maillage PAYE"))
            await s.commit()
    asyncio.run(_pose())
    avant = sorted(p.name for p in d3d.iterdir())
    r = _api("POST", f"/api/cards/{did}/forge3d/library/reptile")
    assert r.status_code == 409, r.text
    assert "appartient" in r.json()["detail"], r.text
    assert victime in r.json()["detail"], r.text
    # ... et RIEN n'a bouge sur le disque : le refus tombe avant l'ecriture.
    assert sorted(p.name for p in d3d.iterdir()) == avant

    async def _retire():
        async with async_session_factory() as s:
            v = await s.get(JobRecord, victime)
            if v is not None:
                await s.delete(v)
                await s.commit()
    asyncio.run(_retire())
    assert _api("POST", f"/api/cards/{did}/forge3d/library/reptile"
                ).status_code == 200

    # ── M9a : SUPPRIMER une carte publiee depuis la Bibliotheque emporte SES
    # FICHIERS. `_delete_provider_output_dir` ne connaissait que sprite2d et
    # asset3d : la ligne partait, le dossier restait — invisible, et
    # re-publie sous le meme short deterministe.
    assert d3d.is_dir()
    assert _api("DELETE", f"/api/jobs/{pub2['job_id']}").status_code == 200
    assert not d3d.exists(), sorted(p.name for p in d3d.iterdir())


def test_la_copie_publiee_est_promue_pas_ecrasee(monkeypatch):
    """M3 (ronde de correction T6) : une copie vers un chemin PUBLIQUEMENT
    SERVI passe par un temporaire puis `os.replace`.

    `copyfile` tronque puis reecrit EN PLACE : un `FileResponse` deja en train
    de streamer `model.glb` lirait la fin du nouveau fichier apres le debut de
    l'ancien — un GLB EPISSE, valide a l'octet pres. La course elle-meme n'est
    pas reproductible dans un test en process ; CE QUI L'EST, c'est la
    mecanique qui l'evite : le nom du temporaire (hors de toute liste publique)
    et la REPRISE du `os.replace` que Windows fait echouer quand la cible est
    ouverte — la meme course, les memes bornes, que `_job_write`."""
    from app.config import settings as cfg
    from app.services.cards import forge3d as F9
    from app.services.storage import init_db
    asyncio.run(init_db())
    did = _deck("Promotion")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "promu"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200

    vrai_replace = os.replace
    vus = {"tmp": [], "echecs": 0}

    def replace_espion(src, dst, *a, **kw):
        s_nom = pathlib.Path(src).name
        if s_nom.endswith(".tmp") and "assets3d" in str(dst):
            vus["tmp"].append(s_nom)
            # DEUX echecs PASSAGERS (la course Windows), puis ca passe : la
            # publication doit SURVIVRE, exactement comme `_job_write` survit
            # a un poll concurrent.
            if vus["echecs"] < 2:
                vus["echecs"] += 1
                raise PermissionError(5, "occupe par un lecteur")
        return vrai_replace(src, dst, *a, **kw)

    monkeypatch.setattr(F9.os, "replace", replace_espion)
    r = _api("POST", f"/api/cards/{did}/forge3d/library/promu")
    assert r.status_code == 200, r.text
    assert vus["echecs"] == 2, vus
    # LE TEMPORAIRE NE COMMENCE PAS PAR `model.` : la route `manifest` declare
    # un FORMAT pour tout fichier qui commence par la (routes.py). Un
    # `model.glb.tmp`, meme une milliseconde, se serait annonce comme un
    # format « glb.tmp » telechargeable.
    assert vus["tmp"], vus
    for nom in vus["tmp"]:
        assert not nom.startswith("model."), nom
        assert nom.startswith("."), nom
    # ... et LE GLB EN PARTICULIER. Mesure trouvee par mutation : un test qui
    # se contente de « au moins un temporaire » reste VERT quand SEUL le
    # `model.glb` retombe sur un `copyfile` en place — or c'est justement le
    # fichier de 32 Mio qu'un lecteur est en train de streamer.
    assert ".model.glb.tmp" in vus["tmp"], vus["tmp"]
    d3d = cfg.outputs_path / "assets3d" / r.json()["short"]
    assert (d3d / "model.glb").read_bytes() == (
        _dossier_forge3d(did) / "promu.glb").read_bytes()
    assert [p.name for p in d3d.iterdir() if p.name.endswith(".tmp")] == []

    # ... et une cible DEFINITIVEMENT verrouillee reste une PANNE avouee — pas
    # un succes silencieux — ET ne laisse aucun temporaire derriere elle.
    def replace_mort(src, dst, *a, **kw):
        if "assets3d" in str(dst):
            raise PermissionError(5, "verrouille pour de bon")
        return vrai_replace(src, dst, *a, **kw)

    monkeypatch.setattr(F9.os, "replace", replace_mort)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/library/promu")
    assert r2.status_code == 500, r2.text
    assert [p.name for p in d3d.iterdir() if p.name.endswith(".tmp")] == [], \
        sorted(p.name for p in d3d.iterdir())


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = ROOT / "scripts" / "patch_bundle_card3d_library.py"

# LES DEUX PAIRES (ancre -> remplacement) DU PATCH card3d, ECRITES ICI ET PAS
# IMPORTEES DU PATCHER : ce test doit pouvoir dire « le bundle livre porte
# CECI » meme si le patcher se trompe. Les importer ferait comparer le patcher
# a lui-meme. Elles servent aussi a DERIVER l'etat pre-patch (S1) : le `.bak`
# du depot est gitignore, donc absent de tout clone frais.
_PAIRES_CARD3D = [
    ('return z.provider==="asset3d"});setJobs(L)',
     'return z.provider==="asset3d"||z.provider==="card3d"});setJobs(L)'),
    ('T3=u.filter(C=>C.provider==="asset3d"&&C.status==="done")',
     'T3=u.filter(C=>(C.provider==="asset3d"||C.provider==="card3d")'
     '&&C.status==="done")'),
]


def test_le_bundle_reconnait_le_provider_card3d_et_le_patcher_est_idempotent(
        tmp_path):
    """Le patch bundle MINIMAL de la tache 6 (2c) : DEUX filtres de provider
    elargis, et rien d'autre.

    Deux choses sont mesurees, et elles ne se remplacent pas : (1) le bundle
    DU DEPOT porte bien le patch — c'est LUI qui part a l'app, un patcher
    correct qui n'a jamais tourne ne sert a rien ; (2) le patcher lui-meme est
    idempotent sur une COPIE — le rejouer ne double pas le patch et ne change
    pas un octet."""
    src = BUNDLE.read_text(encoding="utf-8", newline="")
    # (1) LE BUNDLE LIVRE. Les deux filtres, elargis, et les parentheses de
    # L2 : `&&` lie plus fort que `||`, sans elles un job card3d NON termine
    # passerait le filtre de la Bibliotheque.
    assert src.count(_PAIRES_CARD3D[0][1]) == 1, \
        "filtre du hub Game Assets non elargi"
    assert src.count(_PAIRES_CARD3D[1][1]) == 1, \
        "filtre de la Bibliotheque 3D non elargi (ou parentheses perdues)"
    # ... et le `kind` n'a PAS bouge : « asset3d » est la categorie de l'OBJET
    # (un modele 3D), le provider dit d'ou viennent les octets. Le viewer, le
    # telechargement et « Optimiser » s'accrochent tous au kind.
    assert src.count('kind:"asset3d"') == 1
    # ... et les TROIS filtres de rendus VIDEO restent INTACTS : une carte 3D
    # n'y entre pas parce que son JobRecord laisse `final_video_path` vide
    # (decision backend), pas parce qu'on aurait ajoute une exclusion de plus.
    for var in ("C", "l", "q"):
        assert src.count(f'{var}.provider!=="asset3d"'
                         f'&&{var}.provider!=="sprite2d"') == 1, var

    # (2) LE PATCHER, SUR UNE COPIE — jamais sur le bundle du depot.
    faux = tmp_path / "frontend" / "dist" / "assets"
    faux.mkdir(parents=True)
    cible = faux / BUNDLE.name
    # LE TAG EST LE NOM DU FICHIER (`repatch_all` deduit `patch_bundle_<tag>.py`
    # du `.bak_<tag>`) : un tag qui derive du nom sort « SANS SCRIPT » de la
    # chaine, c'est-a-dire une chaine non rejouable. Le pin le tient.
    assert PATCHER.name == "patch_bundle_card3d_library.py"
    # ── L'ETAT PRE-PATCH EST DERIVE, PAS LU (S1, revue adverse de la T6) ────
    # La premiere version lisait `.bak_card3d_library` a cote du bundle. Or
    # `.gitignore` exclut `frontend/dist/assets/*.js.bak_*` : ce fichier
    # n'existe QUE sur la machine qui a lance le patcher — sur tout clone
    # frais, ce test etait le seul rouge de la suite. Un test qui depend d'un
    # fichier non versionne ne mesure pas le depot, il mesure un poste.
    # L'inverse des DEUX paires rend le meme octet (verifie ci-dessous par le
    # compte de caracteres ET par l'absence des remplacements) : le pre-patch
    # se DEDUIT du bundle livre, qui, lui, est versionne.
    pre = src
    for anchor, repl in _PAIRES_CARD3D:
        assert pre.count(repl) == 1, repl
        pre = pre.replace(repl, anchor)
    assert len(pre) == len(src) - 48, (len(pre), len(src))
    for _a, repl in _PAIRES_CARD3D:
        assert repl not in pre
    cible.write_text(pre, encoding="utf-8", newline="")
    avant = cible.read_bytes()
    assert avant.count(b"\r\n") == BUNDLE.read_bytes().count(b"\r\n")

    def run():
        return subprocess.run(
            [sys.executable, str(PATCHER), "--root", str(tmp_path)],
            capture_output=True, text=True)

    r1 = run()
    assert r1.returncode == 0, r1.stdout + r1.stderr
    apres = cible.read_bytes()
    # DEUX remplacements, mesures : +48 octets exactement, deux marqueurs
    assert len(apres) == len(avant) + 48, (len(avant), len(apres))
    txt = cible.read_text(encoding="utf-8", newline="")
    assert txt.count('||z.provider==="card3d"') == 1
    assert txt.count('||C.provider==="card3d"') == 1
    # les fins de ligne du bundle sont un piege connu de la chaine : le
    # patcher ne doit en traduire AUCUNE.
    assert apres.count(b"\r\n") == avant.count(b"\r\n")
    assert apres.count(b"\n") - apres.count(b"\r\n") == 0

    # IDEMPOTENT : rejouer ne double pas le patch et ne change pas un octet.
    r2 = run()
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert cible.read_bytes() == apres, "second passage : le bundle a bouge"
    txt2 = cible.read_text(encoding="utf-8", newline="")
    assert txt2.count('||z.provider==="card3d"') == 1, "double patch"
    assert txt2.count('||C.provider==="card3d"') == 1, "double patch"

    # ... et le maillon est REJOUABLE : `repatch_all` deduit le script du TAG
    # du backup, donc le .bak POSE PAR CETTE EXECUTION doit porter le nom du
    # fichier. Sinon la chaine sort « SANS SCRIPT » et s'arrete la. (Mesure
    # sur la COPIE — le .bak du depot, lui, est gitignore : rien ici ne le
    # regarde.)
    pose = sorted(p.name for p in faux.glob(BUNDLE.name + ".bak_*"))
    assert pose == [BUNDLE.name + ".bak_card3d_library"], pose
    # ... et un bundle DEJA patche sans son .bak est un etat AMBIGU : refus
    # nomme, aucun backup empoisonne cree (le piege que la chaine a deja paye).
    (faux / (BUNDLE.name + ".bak_card3d_library")).unlink()
    r3 = run()
    assert r3.returncode != 0, r3.stdout
    assert "sanity" in (r3.stdout + r3.stderr), r3.stdout + r3.stderr

    # (3) M7 — UNE ANCRE PERIMEE NE LAISSE AUCUN BACKUP DERRIERE ELLE.
    # Le controle des ancres vivait APRES la copie du .bak : un bundle ou
    # l'ancre a bouge produisait un backup PUIS un abandon. Ce backup-la est un
    # piege differe — l'operateur repare l'ancre a la main, relance, et la
    # branche « restore <- .bak » DETRUIT la reparation sans un mot.
    autre = tmp_path / "perime" / "frontend" / "dist" / "assets"
    autre.mkdir(parents=True)
    (autre / BUNDLE.name).write_text(
        pre.replace(_PAIRES_CARD3D[0][0], 'return z.provider==="asset3D"});'
                    'setJobs(L)'),
        encoding="utf-8", newline="")
    r4 = subprocess.run(
        [sys.executable, str(PATCHER), "--root", str(tmp_path / "perime")],
        capture_output=True, text=True)
    assert r4.returncode != 0, r4.stdout
    assert "anchor count=0" in (r4.stdout + r4.stderr), r4.stdout + r4.stderr
    assert list(autre.glob(BUNDLE.name + ".bak_*")) == [], \
        "un abandon ne doit JAMAIS laisser un backup derriere lui"


def test_le_bouton_publier_est_garde_et_vit_dans_les_deux_vues():
    """Test de SOURCE (2c Task 6) : « Publier dans la Bibliotheque ».

    Ce qui est epingle ici : le geste est GARDE (un seul a la fois, garde de
    GENERATION apres l'await), il vit dans LES DEUX vues (le nœud artefact ET
    le bordereau de la liste — la vue liste est le repli sans pointeur, elle ne
    perd aucune action), il ne touche PAS au graphe (publier n'est pas une
    edition : aucune entree d'annulation), et l'etat « publie » meurt avec le
    bordereau qu'il decrit."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    pl = rendu.split("async function publishLibrary(")[1].split("\n  }")[0]
    assert '"library/"' in pl, pl
    assert "artifactName(" in pl, pl
    # UN SEUL GESTE A LA FOIS (patron `build3d.busy` / `freezePreview.busy`) :
    # deux POST concurrents publieraient deux fois les memes octets. Le garde
    # est le PREMIER geste de la fonction — plus bas, il aurait deja laisse
    # passer la peinture d'occupation, voire la requete.
    assert pl.split("{", 1)[1].lstrip().startswith(
        "if (publishLibrary.busy) return;"), pl[:200]
    # M4 (ronde de correction T6) : ... ET PENDANT UNE CONSTRUCTION. Ce qui
    # part a la Bibliotheque, c'est `{art}.glb` SUR LE DISQUE DU DECK : tant
    # que `build3d` l'ecrit, ce fichier n'est pas l'artefact qu'on croit
    # publier (c'est celui d'avant, ou une moitie des deux). Le garde vit dans
    # la FONCTION, pas seulement sur le bouton — un bouton desactive n'arrete
    # ni le clavier, ni un double-clic dans la fenetre de repeinture.
    assert "build3d.busy" in pl.split("if (!ARTIFACT)")[0], pl[:600]
    ph = rendu.split("function publieHtml(")[1].split("\n  }")[0]
    assert "build3d.busy" in ph, ph
    # LA GARDE DE GENERATION APRES CHAQUE await (doctrine du fichier) : une
    # publication lancee sur la carte d'avant n'ecrit pas « publie » dans
    # l'ecran de la suivante. Invariant, pas compte fige...
    assert pl.count("gen !== GEN") >= pl.count("await "), pl
    # ... ET LA ZONE EXACTE (lecon T5 : l'invariant ci-dessus a une unite de
    # jeu, le `catch` portant lui aussi un garde). Entre le RETOUR RESEAU et
    # l'ecriture de l'etat « publie », le garde doit etre la : c'est le seul
    # endroit ou son absence ecrirait le bordereau d'une autre carte.
    retour = pl.split("await M.api.post(", 1)[1].split(
        "ARTIFACT = Object.assign", 1)[0]
    assert "gen !== GEN" in retour, retour
    # PUBLIER N'EST PAS UNE EDITION DU GRAPHE : aucune entree d'annulation,
    # aucun patch. « ↶ annuler » ne doit pas avaler un geste de publication.
    assert "setGraph(" not in pl and "M.patch" not in pl, pl
    # LE TITRE PUBLIE remonte dans le toast : c'est le seul lien entre l'ecran
    # et ce que l'utilisateur trouvera dans la Bibliotheque.
    assert "rep.title" in pl, pl
    # ... et le motif d'un refus part TEL QUEL (jamais-500 cote ecran)
    assert "e.message" in pl, pl

    # DANS LES DEUX VUES, par la MEME fonction d'etat (doctrine `ignoresHtml` :
    # deux rendus du meme fait auraient derive).
    art = rendu.split("function artifactNodeHtml(")[1].split("\n  }")[0]
    assert "publieHtml(" in art, art
    pa = rendu.split("function paintArtifact(")[1].split("\n  }")[0]
    assert "publieHtml(" in pa, pa
    # ... et les DEUX delegations connaissent l'acte (le canvas et la section
    # n'ont pas le meme handler de clic).
    og = rendu.split("function onGraphClick(")[1].split("\n  }")[0]
    osc = rendu.split("function onSlipClick(")[1].split("\n  }")[0]
    assert '"publish-lib"' in og, og
    assert '"publish-lib"' in osc, osc

    # L'ETAT « PUBLIE » MEURT AVEC SON BORDEREAU. Deux portes, mesurees :
    # `cardChanged` lache `ARTIFACT` (deja epingle plus haut), et `build3d` le
    # REMPLACE par la reponse du serveur — la copie qui dort dans la
    # Bibliotheque porte alors les octets d'AVANT, et « publie » deviendrait un
    # mensonge sur le fichier qu'on ira y chercher.
    b3 = rendu.split("async function build3d(")[1].split("\n  }")[0]
    assert "ARTIFACT = rep.artifact;" in b3, b3
    assert "published" not in b3, b3


def test_le_canvas_est_la_projection_du_meme_graphe():
    """Test de SOURCE (phase 2c, Task 2) : le canvas nodal est une VUE du
    MEME graphe, jamais un second modele. Ce qui est epingle ici :

      · la surface `#cf-forge3d-canvas` et la bascule liste/canvas existent,
        et la vue LISTE survit (tous les pins 2a/2b restent valables) ;
      · les positions vivent dans `doc.forge3d.layout` — de la PRESENTATION,
        donc patchees SANS entree d'annulation (l'annulation appartient au
        CONTENU du graphe : setGraph/HIST) ;
      · la barre de fluidite §9.6 sur CHAQUE glisser du canvas : <= 1 patch
        par frame (paire rAF), geste EXACT au relache, `isPrimary` en garde,
        `touch-action: none` sur la surface ;
      · l'auto-arrangement est DETERMINISTE (colonnes par kind, zero alea) ;
      · les aretes sont UNE couche SVG (un chemin par arete du graphe)."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # la surface, la bascule liste/canvas, le layout dans le doc
    assert 'id="cf-forge3d-canvas"' in rendu
    assert "layout" in rendu and 'get("layout"' in rendu
    # les positions sont de la PRESENTATION : patchees SANS entree d'annulation
    corps = rendu.split("function flushLayout(")[1].split("\n  }")[0]
    assert "M.patch" in corps and "HIST" not in corps, corps
    # `__proto__` NE PART JAMAIS AU PATCH — et c'est la seconde moitie d'une
    # paire. Cote LECTURE, les registres de positions sont sans prototype
    # (`sansProto`), ce qui fait de « __proto__ » une vraie cle propre au lieu
    # d'un acces qui reparente. Mais le CORE, lui, REBATIT le sous-arbre dans
    # un `{}` ordinaire (core.js:211) : `o["__proto__"] = [x, y]` y traverse
    # l'accesseur d'Object.prototype et reparente `o` sur le tableau. La garde
    # de classe de `sanitize` (core.js:209) leve alors a chaque `doc()`
    # suivant — l'onglet est mort jusqu'au rechargement. Le durcissement de la
    # lecture SANS ce filtre est donc une regression, pas une protection.
    assert '__proto__' in corps, corps
    assert re.search(r'if\s*\(\s*k\s*===\s*"__proto__"\s*\)\s*return', corps), corps
    # drag de noeud coalesce au rAF (spec 9.6-1) + geste exact au relache :
    # la frame en vol est ANNULEE puis le flush est fait a la main, sinon la
    # derniere position attend une frame qui peut ne jamais venir.
    assert "scheduleFrame" in rendu and "cancelFrame" in rendu
    fin = rendu.split("function onCanvasUp(")[1].split("\n  }")[0]
    assert "cancelFrame" in fin and "flushLayout()" in fin, fin
    # ... et le geste ne demarre que sur le pointeur PRIMAIRE (9.6-3)
    debut = rendu.split("function onCanvasDown(")[1].split("\n  }")[0]
    assert "isPrimary" in debut, debut
    # UN GESTE, UN POINTEUR — et c'est une propriete DISTINCTE de la
    # precedente : `isPrimary` empeche un second doigt d'OUVRIR un geste, il
    # n'empeche pas ses `pointermove` d'arriver. Sans filtre par
    # `pointerId`, un debut de pincement teleportait le nœud a l'ecart du
    # SECOND doigt (mesure contre l'origine du premier) et le COMMETTAIT au
    # relache. Le jeton se COMPARE, il ne se contente pas d'exister (meme
    # doctrine que le registre POLLS de la 2b).
    assert "pid: e.pointerId" in rendu
    for nom in ("onCanvasMove", "onCanvasUp"):
        bloc = rendu.split("function " + nom + "(")[1].split("\n  }")[0]
        assert "e.pointerId !== DRAG.pid" in bloc, (nom, bloc)
    # ... sur une surface qui ne defile pas sous le doigt (9.6-3)
    feuille = CSS.read_text(encoding="utf-8")
    assert "touch-action: none" in feuille
    # ── LE GESTE NE PEUT PAS RASER LE LAYOUT (C1 de la revue) ─────────────
    # Le degat : le pointeur est CAPTURE par la surface, donc un glisser
    # survit a la bascule de vue. `videCanvas` vidait LAYOUT_VU sans annuler
    # le geste ; les `pointermove` suivants y re-posaient LA SEULE entree du
    # nœud traine, et le relache patchait cette carte-la. `patchAs` fusionne
    # au PREMIER NIVEAU (la valeur remplace, elle ne se melange pas) : toutes
    # les autres positions detruites — et sans recours, puisque le layout est
    # precisement ce qui n'entre PAS dans la pile d'annulation.
    # L'ORDRE est le correctif : flusher CE layout, PUIS couper le geste,
    # PUIS vider. On epingle l'ordre, pas seulement la presence.
    vc = rendu.split("function videCanvas(")[1].split("\n  }")[0]
    for jalon in ("flushLayout()", "DRAG = null", "LAYOUT_VU = sansProto()"):
        assert jalon in vc, (jalon, vc)
    assert vc.index("flushLayout()") < vc.index("DRAG = null") \
        < vc.index("LAYOUT_VU = sansProto()"), vc
    # la meme coupure sur l'autre chemin qui vide sous le geste : annuler le
    # tout premier semis EN PLEIN GLISSER fait disparaitre le graphe.
    pc = rendu.split("function paintCanvas(")[1].split("\n  }")[0]
    sans_graphe = pc.split("if (!graph) {")[1]
    assert "DRAG = null" in sans_graphe, sans_graphe
    # ... et le chemin du CHANGEMENT DE DECK, lui, n'ecrit RIEN : les
    # positions en attente appartiennent au deck qu'on quitte, les patcher
    # les poserait sur le suivant.
    ol = rendu.split("function oublieLeCanvas(")[1].split("\n  }")[0]
    assert "flushLayout" not in ol, ol
    assert "DRAG = null" in ol and "LAYOUT_SALE = false" in ol, ol
    # UNE SEULE PORTE POUSSE LA PILE D'ANNULATION, et c'est `setGraph` : si un
    # jour un helper poussait HIST ailleurs, « le layout ne s'annule pas »
    # redeviendrait une affirmation de commentaire au lieu d'une propriete du
    # code (le mutant : deplacer HIST.push dans une fonction intermediaire).
    assert rendu.count("HIST.push") == 1, rendu.count("HIST.push")
    sg = rendu.split("function setGraph(")[1].split("\n  }")[0]
    assert "HIST.push" in sg, sg
    # l'auto-arrangement est DETERMINISTE (colonnes par kind, pas de hasard)
    assert "function seedLayout(" in rendu and "Math.random" not in rendu
    # les aretes sont UNE couche SVG sous les noeuds
    assert "cf-forge3d-edges" in rendu and "path" in rendu
    # la vue liste SURVIT (bascule) — les pins 2a/2b restent valables
    assert "graphRows(graph)" in rendu
    assert "cf-forge3d-vue" in rendu
    # la bascule est de la PRESENTATION : elle vit dans localStorage, pas dans
    # le document (un graphe ne se transporte pas avec une preference d'ecran)
    assert "localStorage" in rendu and "dz_cf_forge3d_vue" in rendu
    # le SCHEMA du module gagne `layout` (les cles declarees a
    # l'enregistrement sont les SEULES patchables ensuite) — et la bascule,
    # elle, n'y entre pas : un graphe ne se transporte pas avec une
    # preference d'ecran.
    reg = rendu.split("CF.register(")[1].split("\n  });")[0]
    assert "layout" in reg, reg
    assert "dz_cf_forge3d_vue" not in reg, reg
    # le dispatcher : la vue ACTIVE se repeint, et la LISTE garde son peintre
    # (paintGraph reste le peintre de la liste — les pins 2a/2b le lisent)
    vue = rendu.split("function paintVue(")[1].split("\n  }")[0]
    assert "paintCanvas()" in vue and "paintGraph()" in vue, vue
    # ... et plus aucun appelant ne peint la LISTE en aveugle : les points
    # d'entree du module passent par le dispatcher.
    for appelant in ("function wire(", "function undoGraph("):
        bloc = rendu.split(appelant)[1].split("\n  }")[0]
        assert "paintVue()" in bloc, (appelant, bloc)


def test_chaque_noeud_porte_ses_menus_et_sa_vignette_reactive():
    """Test de SOURCE (phase 2c, Task 3) : un nœud du canvas porte SES menus
    et une vignette qui REAGIT. Ce qui est epingle ici :

      · REUTILISATION STRICTE — le corps d'un nœud compose les batisseurs de
        champs DEJA ecrits pour la liste (aucun balisage de champ n'existe en
        double : c'est le compte litteral des `data-field` qui le prouve, pas
        une promesse de commentaire) ;
      · les handlers d'edition remontent DEPUIS LE CANVAS (meme delegation
        `change` que la liste) ;
      · la vignette est un canvas 2D DETERMINISTE, peinte localement (blobs
        de provenance en cache, garde de generation apres chaque await) ;
      · le repaint PAR NŒUD existe et preserve focus + tiroirs — sans lui,
        chaque frappe passerait par la reconstruction complete de
        `paintCanvas` et volerait le curseur (piege syncInputs de mod-face) ;
      · la zone chip est INDEPENDANTE DE L'HOTE : le poll d'un job repeint
        dans LES DEUX vues."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # ── REUTILISATION STRICTE ────────────────────────────────────────────
    # le corps d'un nœud appelle les blocs EXISTANTS...
    corps = rendu.split("function nodeBodyHtml(")[1].split("\n  }")[0]
    for bloc in ("mesh3dHtml", "matHtml", "trsHtml",
                 "procSelHtml", "geoHtml", "sideSelHtml", "thumbHtml"):
        assert bloc in corps, (bloc, corps)
    # ... et le RANG de la liste appelle EXACTEMENT les memes.
    ligne = rendu.split("function rowHtml(")[1].split("\n  }")[0]
    for bloc in ("mesh3dHtml", "matHtml", "trsHtml",
                 "procSelHtml", "geoHtml", "sideSelHtml"):
        assert bloc in ligne, (bloc, ligne)
    # I4 — LA PROMESSE DE L'EN-TETE, EPINGLEE AU CARACTERE PRES. « les memes
    # batisseurs » ne veut rien dire si l'appel du canvas oublie l'HOTE :
    # sans `"node"`, matiere et placement rendraient un <details> dans un
    # corps de nœud, c'est-a-dire un nœud entier qui ne montre rien — et
    # aucun autre pin ne le voyait (le nom de la fonction, lui, est bien la).
    for appel in ('matHtml(r, r.proc.kind === "mesh3d", "node")',
                  'trsHtml(r, "node")'):
        assert appel in corps, (appel, corps)
    # LA PREUVE DE NON-DUPLICATION : chaque champ n'a qu'UN point d'ecriture
    # dans tout le module. Un balisage recopie pour le canvas ferait passer
    # ces comptes a 2 — et deux copies derivent (la lecon des tables
    # miroir : une seule source, ou une seule des deux dit vrai).
    for champ in ('data-field="engine"', 'data-field="mat"',
                  'data-field="finish"', 'data-field="side"',
                  'data-field="kind"', 'data-field="texture_prompt"',
                  'data-field="aniso"'):
        assert rendu.count(champ) == 1, (champ, rendu.count(champ))
    # les handlers remontent DEPUIS LE CANVAS : meme delegation que la liste
    wc = rendu.split("function wireCanvas(")[1].split("\n  }")[0]
    assert "onGraphChange" in wc, wc
    # ── LA VIGNETTE ──────────────────────────────────────────────────────
    assert "function paintNodeThumb(" in rendu
    assert "cf-forge3d-thumb" in rendu and "Math.random" not in rendu
    # mesh3d : la chip d'etat + un PICTOGRAMME moteur. Le `preview.png` du
    # job vit sous `nodes/{nid}/` et AUCUNE route ne le sert (le regex de
    # GET /file/{name} interdit le separateur) : c'est la branche « a defaut »
    # du plan qui s'applique, et elle est nommee.
    assert "chipHtml" in rendu and "preview" in rendu
    assert "PICTO" in rendu
    # matiere : la vignette de la boutique par la route de provenance
    assert "material-thumb/" in rendu
    # AUCUN reseau hors provenance : les images passent par M.api.blob
    ci = rendu.split("async function chargeImage(")[1].split("\n  }")[0]
    assert "M.api.blob" in ci, ci
    # ... et la GARDE DE GENERATION apres CHAQUE await (2b Task 7) : une
    # image du deck precedent ne se peint pas dans l'ecran du suivant. Le pin
    # est un INVARIANT, pas un compte fige : autant de gardes que d'awaits —
    # sinon un await ajoute demain repasserait sous le radar.
    assert ci.count("gen !== GEN") >= ci.count("await "), ci
    # ── LE REPAINT PAR NŒUD (le pendant de paintRow) ─────────────────────
    pn = rendu.split("function paintNode(")[1].split("\n  }")[0]
    # le focus est RENDU, pas seulement mentionne : c'est l'appel qui compte.
    # (Pas de sauvegarde de tiroirs a epingler : un corps de nœud n'en a
    # aucun — `blocHtml` reserve <details> a l'hote « row ». La recopier
    # aurait fait tourner une boucle sur zero element, du code qui a l'air de
    # proteger et ne protege rien.)
    assert "rendLeFocus(" in pn, pn
    rf = rendu.split("function rendLeFocus(")[1].split("\n  }")[0]
    assert ".focus()" in rf and "findByAttr(" in rf, rf
    # il ne reconstruit PAS le monde (ce serait exactement le vol de curseur
    # que cette fonction existe pour empecher)
    assert "paintCanvas()" not in pn, pn
    # ... et il est BRANCHE la ou `paintRow` l'est pour la liste
    eg = rendu.split("function editGraph(")[1].split("\n  }")[0]
    assert "paintChamps(" in eg, eg
    pch = rendu.split("function paintChamps(")[1].split("\n  }")[0]
    assert "paintNode(" in pch and "paintRow(" in pch, pch
    # une profondeur editee REPEINT LA VIGNETTE du nœud touche (sinon le
    # relief se dessinerait a l'ancienne profondeur jusqu'au prochain
    # repaint global) — la branche « ni structure ni naissance ». Et la
    # CHAINE avec lui : la face d'une couche change la PNG que son
    # traitement et son placement dessinent tous les deux.
    # LE PIN VISE LA BRANCHE, PAS LE FICHIER : `repeintChaine` apparait
    # desormais dans DEUX branches (I1 l'a ajoute a la structurelle) et dans
    # `onGraphInput`, donc un simple « le nom est quelque part » ne prouve
    # plus rien — c'est exactement le mutant qui a survecu a la revue.
    apres_commit_t3 = eg.split("setGraph(next, field)")[1]
    assert apres_commit_t3.count("} else {") == 1, apres_commit_t3
    sinon = apres_commit_t3.split("} else {")[1]
    assert "repeintChaine(" in sinon, sinon
    rc = rendu.split("function repeintChaine(")[1].split("\n  }")[0]
    assert "paintNodeThumb(" in rc, rc
    # ... et le poll d'un job repeint la chip ET la vignette (elles portent
    # le MEME etat lu : deux centimetres d'ecart, un seul job)
    pcp = rendu.split("function paintChip(")[1].split("\n  }")[0]
    assert "paintNodeThumb(" in pcp, pcp
    # I4 — LA PEINTURE COMPLETE PEINT AUSSI LES VIGNETTES. Sans cette ligne,
    # un graphe s'ouvrait avec onze canvas VIDES jusqu'a la premiere edition
    # (les images arrivent par `demandeRepeintVignettes`, mais un cache deja
    # chaud — bascule de vue, retour d'onglet — ne declenche rien du tout).
    pcv = rendu.split("function paintCanvas(")[1].split("\n  }")[0]
    assert "paintNodeThumb(" in pcv, pcv
    # I1 — `side` change l'EN-TETE d'un nœud couche (noeudTitre lit `side`),
    # pas seulement la valeur du champ : il appartient donc aux champs
    # structurels, et la branche structurelle repeint AUSSI la chaine.
    assert '"side"' in rendu.split("const STRUCT_FIELDS")[1].split(";")[0], rendu
    struct = eg.split("STRUCT_FIELDS.indexOf(field) >= 0")[1].split("} else")[0]
    assert "repeintChaine(" in struct, struct
    # M10 — la vignette suit la FRAPPE (input), le document le COMMIT
    # (change) : l'evenement `input` ne doit rien ecrire.
    ogi = rendu.split("function onGraphInput(")[1].split("\n  }")[0]
    assert "repeintChaine(" in ogi, ogi
    assert "editGraph(" not in ogi and "M.patch" not in ogi, ogi
    # M5 — le registre des chargements en vol porte la GENERATION (doctrine
    # du jeton POLLS) : un chargement rassis ne retire que SA propre entree.
    ci2 = rendu.split("async function chargeImage(")[1].split("\n  }")[0]
    assert "IMGS_VOL[cle] = gen" in ci2, ci2
    assert "IMGS_VOL[cle] === gen" in ci2, ci2
    # ── L'EPOQUE DU CACHE (suivi T3, referme en tete de T4) ──────────────
    # La GENERATION ne couvre PAS le vidage de cache d'un export : `GEN` ne
    # bouge qu'au changement de deck/carte, alors que `oublieLesImages()` est
    # aussi appele quand une FACE vient d'etre livree (I3a). Un chargeur parti
    # AVANT l'export revenait donc apres le vidage et re-posait dans le cache
    # les octets PRE-export — precisement ceux que le vidage venait de jeter,
    # et sans le moindre signe jusqu'au changement de deck. L'epoque est le
    # jeton qui manquait ; comme pour GEN, le pin est un INVARIANT (autant de
    # gardes que d'awaits), pas un compte fige.
    assert ci2.count("ep !== IMGS_EPOQUE") >= ci2.count("await "), ci2
    oi = rendu.split("function oublieLesImages(")[1].split("\n  }")[0]
    assert "IMGS_EPOQUE += 1" in oi, oi
    # ... et le RETAILLAGE (I2) est au site d'appel, pas seulement declare :
    # une fonction de reduction que personne n'appelle laisse les bitmaps
    # pleine definition en memoire (~49 Mo par couche) tout en ayant l'air
    # d'un cache econome.
    assert "retaille(" in ci2, ci2
    # ── LES TROIS SITES D'APPEL (suivi T3) ──────────────────────────────
    # Une invalidation declaree et jamais appelee est pire qu'absente : elle
    # se lit comme une garantie. On epingle donc l'APPEL, dans le corps ou il
    # doit vivre — une face livree invalide SA face, DANS le tour ou elle est
    # livree (l'export peut s'arreter au milieu : le verso qui leve laissait
    # sinon le recto reecrit sous le meme nom avec le cache d'avant).
    env = rendu.split("async function exportLayers(")[1].split("\n  }")[0]
    boucle = env.split("for (let p = 0; p < preuves.length; p++) {")[1]
    assert "oublieLesImages()" in boucle, boucle
    # ... et la fenetre de fraicheur des vignettes de matiere s'ouvre UNE FOIS
    # PAR PEINTURE, avant de peindre (I3b) — jamais pendant.
    assert "reSondeLesMatieres(" in pcv, pcv
    # ── LA CHIP, DANS LES DEUX VUES ──────────────────────────────────────
    fb = rendu.split("function findByAttr(")[1].split("\n  }")[0]
    assert "#cf-forge3d-graph" not in fb, fb
    assert "hoteVue()" in fb, fb
    # ── LA FEUILLE ───────────────────────────────────────────────────────
    # les SELECTEURS, pas la sous-chaine : `.cf-forge3d-thumb` se retrouve
    # dans la regle de perspective meme si la zone elle-meme a disparu.
    feuille = CSS.read_text(encoding="utf-8")
    for sel in (".cf-forge3d .cf-forge3d-thumb {",
                ".cf-forge3d .cf-forge3d-thumb.cf-forge3d-plan {",
                ".cf-forge3d .cf-forge3d-corps {",
                ".cf-forge3d .cf-forge3d-blk-n {"):
        assert sel in feuille, sel


def test_les_connexions_valident_la_grammaire_a_l_arete():
    """Test de SOURCE (phase 2c, Task 4) : les connexions se font A LA SOURIS
    et sont validees A L'ARETE. Ce qui est epingle ici :

      · UNE table de grammaire, NOMMEE et unique (`GRAMMAIRE`) — les ports,
        la validation et le texte du refus en DERIVENT tous les trois ;
      · un refus est un toast NOMME qui n'ecrit RIEN (jamais creer-puis-
        avouer : le backend, lui, accepte et avoue au bordereau) ;
      · creer/supprimer une arete passe par `setGraph` (donc UNE entree
        d'annulation), et un doublon n'en pousse AUCUNE ;
      · le glisser de port suit la barre de fluidite 9.6 : `isPrimary` en
        garde, un pointeur par geste, feedback coalesce au rAF ;
      · la DETTE de la Task 2 est payee : une arete a une zone de saisie
        EXPLICITE (chemin transparent epais, seul a recevoir le pointeur — le
        trait visible, lui, reste sourd) et les ports tombent EXACTEMENT sur
        les coordonnees d'ancrage des aretes (NOEUD_W, PORT_Y)."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # ── LA GRAMMAIRE, UNIQUE ET NOMMEE ───────────────────────────────────
    assert "GRAMMAIRE" in rendu and "function lienValide(" in rendu
    corps = rendu.split("function lienValide(")[1].split("\n  }")[0]
    for regle in ("layer", "assemble", "artifact", "export"):
        assert regle in corps or regle in rendu, regle
    # la table est LA source : la validation la LIT au lieu de recopier ses
    # regles (le mutant : une cascade de `if` a cote de la table).
    assert "GRAMMAIRE" in corps, corps
    gram = rendu.split("const GRAMMAIRE")[1].split("\n  };")[0]
    for etage in ("layer:", "plane:", "relief:", "mesh3d:", "material:",
                  "transform:", "assemble:", "artifact:", "export:"):
        assert etage in gram, (etage, gram)
    # ... et les PORTS en derivent aussi : un kind a une sortie s'il mene
    # quelque part, une entree si quelque chose y mene. Une seconde table
    # « qui a quel port » aurait derive de la premiere au premier etage
    # ajoute — et l'ecran aurait alors montre une poignee qui ne branche rien.
    for fn in ("function aEntree(", "function aSortie("):
        bloc = rendu.split(fn)[1].split("\n  }")[0]
        assert "GRAMMAIRE" in bloc, (fn, bloc)
    # ── ECRIRE ET DEFAIRE PASSENT PAR LA MEME PORTE ──────────────────────
    assert "function creeLien(" in rendu and "setGraph" in rendu
    assert "function suppLien(" in rendu
    for nom in ("creeLien", "suppLien"):
        bloc = rendu.split("function " + nom + "(")[1].split("\n  }")[0]
        assert "setGraph(" in bloc, (nom, bloc)
    # UNE SEULE PORTE POUSSE LA PILE (le pin de la Task 2 reste vrai apres
    # deux ecrivains de plus) — verifie la aussi, parce que c'est ICI qu'on
    # aurait ete tente d'empiler « a la main ».
    assert rendu.count("HIST.push") == 1, rendu.count("HIST.push")
    # LE REFUS N'ECRIT RIEN. La decision est prise AVANT le clone : la
    # fonction pure rend un motif, et l'appelante ne patche que quand elle
    # recoit un graphe. Le mutant vise : creer puis avouer.
    pur = rendu.split("function grapheAvecLien(")[1].split("\n  }")[0]
    assert "refus" in pur, pur
    assert "setGraph" not in pur and "M.patch" not in pur, pur
    assert "M.toast" not in pur, pur
    # ... et le texte du refus DERIVE de la table (jamais une phrase gelee) :
    # le jour ou la grammaire gagne un etage, le refus le dit tout seul.
    assert "function chaineAttendue(" in rendu
    ca = rendu.split("function chaineAttendue(")[1].split("\n  }")[0]
    assert "GRAMMAIRE" in ca, ca
    # le motif est compose PAR LA FONCTION PURE (c'est ce qui le rend
    # mesurable au harnais) ; l'appelante ne fait que le DIRE.
    assert "chaineAttendue()" in pur, pur
    cl = rendu.split("function creeLien(")[1].split("\n  }")[0]
    assert "M.toast" in cl, cl
    # ... et un DOUBLON ne dit rien du tout : ni toast, ni ecriture. Le pin
    # vise la branche : `refus` seul declenche le toast.
    assert "r.refus" in cl, cl
    # ── LE GLISSER DE PORT (barre 9.6) ───────────────────────────────────
    assert "cf-forge3d-port" in rendu
    debut = rendu.split("function onCanvasDown(")[1].split("\n  }")[0]
    assert "cf-forge3d-port" in debut, debut
    assert "isPrimary" in debut, debut
    # LES PORTS SURVIVENT AU REPAINT D'UN SEUL NŒUD. `paintNode` reecrit
    # l'INTERIEUR du nœud a chaque champ edite ; les ports en sont des
    # enfants directs (leur ancre est le BORD du nœud, pas l'interieur de
    # l'en-tete) — les oublier la aurait fait disparaitre les poignees de
    # connexion au premier caractere tape, et seulement sur le nœud edite.
    for hote in ("function canvasNodeHtml(", "function paintNode("):
        bloc = rendu.split(hote)[1].split("\n  }")[0]
        assert "portsHtml(" in bloc, (hote, bloc)
    # LE BOUTON DE COUPE N'EST PAS LE FOND. Il vit DANS le monde (pour suivre
    # le cadrage), donc aucune surcouche ne le protege — et le glisser du
    # fond DESIGNE l'arete a null, ce qui RETIRE ce bouton du DOM au
    # `pointerdown`, avant que son propre `click` n'arrive : il aurait
    # disparu sous le doigt sans jamais couper.
    assert "cf-forge3d-supp" in debut, debut
    # le fantome est un feedback LOCAL, coalesce au rAF : un `d` par frame,
    # jamais un par evenement de pointeur (spec 9.6-1/2).
    mv = rendu.split("function onCanvasMove(")[1].split("\n  }")[0]
    assert "DRAG.lien" in mv, mv
    assert "scheduleFrame" in mv or "lienRaf" in mv, mv
    # ... et le geste est PROPRE a sa fin : le relache decide, l'annulation
    # (Echap, pointercancel, fond) efface le fantome sans rien ecrire.
    up = rendu.split("function onCanvasUp(")[1].split("\n  }")[0]
    assert "fermeFantome" in up, up
    assert "e.pointerId !== DRAG.pid" in up, up
    # `pointercancel` N'EST PAS UN LACHER : ce handler sert les deux
    # evenements (wireCanvas les abonne ensemble), et sans le test du TYPE une
    # reprise du pointeur par l'OS poserait une connexion a l'aveugle, sous un
    # curseur que l'utilisateur ne dirigeait plus.
    assert 'e.type === "pointerup"' in up, up
    assert "Escape" in rendu
    # ── LA DETTE DE LA TASK 2, PAYEE ─────────────────────────────────────
    feuille = CSS.read_text(encoding="utf-8")
    # 1. la zone de saisie d'une arete est EXPLICITE et epaisse ; le trait
    #    visible, lui, ne prend aucun evenement (sinon 1,5 px de cible, sous
    #    la barre des 12 px de la spec 9.6-3).
    assert "cf-forge3d-edge-hit" in rendu
    hit = re.search(r"\.cf-forge3d \.cf-forge3d-edge-hit \{([^}]*)\}", feuille)
    assert hit, feuille
    assert "pointer-events: stroke" in hit.group(1), hit.group(1)
    larg = re.search(r"stroke-width:\s*(\d+(?:\.\d+)?)", hit.group(1))
    assert larg and float(larg.group(1)) >= 12, hit.group(1)
    vis = re.search(r"\.cf-forge3d \.cf-forge3d-edge \{([^}]*)\}", feuille)
    assert vis and "pointer-events: none" in vis.group(1), feuille
    # 2. LES PORTS TOMBENT SUR L'ANCRE — et le mirroir est verifie AU
    #    CHIFFRE : la feuille et le JS doivent dire la meme chose, sinon le
    #    trait et sa poignee se decollent (le defaut nomme dans la dette).
    noeud_w = int(re.search(r"const NOEUD_W = (\d+);", rendu).group(1))
    port_y = int(re.search(r"const PORT_Y = (\d+);", rendu).group(1))
    # LES CHIFFRES DU JS SONT DANS LA FEUILLE, ET LA BORDURE EST REPRISE. Le
    # repere d'un enfant absolu est la boite de PADDING de son ancetre
    # positionne, pas sa boite de BORDURE : sans le `- var(--cf-bord)` les
    # trois coordonnees tombent a UN PIXEL de l'ancre — le decollement que la
    # dette de la Task 2 nommait, invisible a la lecture et visible a l'œil.
    port = re.search(r"\.cf-forge3d \.cf-forge3d-port \{([^}]*)\}", feuille)
    assert port, feuille
    assert f"top: calc({port_y}px - var(--cf-bord))" in port.group(1), \
        (port_y, port.group(1))
    sortie = re.search(r"\.cf-forge3d \.cf-forge3d-port-out \{([^}]*)\}", feuille)
    entree = re.search(r"\.cf-forge3d \.cf-forge3d-port-in \{([^}]*)\}", feuille)
    assert sortie and f"left: calc({noeud_w}px - var(--cf-bord))" in sortie.group(1), feuille
    assert entree and "left: calc(0px - var(--cf-bord))" in entree.group(1), feuille
    # ... et `--cf-bord` est bien CE QUE LA BORDURE VAUT (pas un chiffre pose
    # a cote d'elle) : le nœud la declare et s'en sert.
    nd = re.search(r"\.cf-forge3d \.cf-forge3d-noeud \{([^}]*)\}", feuille)
    assert nd and "--cf-bord:" in nd.group(1), feuille
    assert nd and "border: var(--cf-bord) solid" in nd.group(1), nd.group(1)
    # ... et le CENTRE tombe sur l'ancre, pas le coin : la pastille est
    # decalee d'une demi-taille (sans quoi l'arete partirait du bord de la
    # poignee et non de son milieu).
    taille = re.search(r"width:\s*(\d+)px", port.group(1))
    assert taille and int(taille.group(1)) >= 12, port.group(1)
    assert f"margin: -{int(taille.group(1)) // 2}px" in port.group(1), port.group(1)
    # 3. le bouton « supprimer » d'une arete existe et passe par suppLien
    assert "cf-forge3d-supp" in rendu and "lien-supp" in rendu
    ogc = rendu.split("function onGraphClick(")[1].split("\n  }")[0]
    assert "suppLien(" in ogc, ogc
    assert "cf-forge3d-edge-hit" in ogc, ogc


def test_l_inspecteur_est_unique_et_l_artefact_rend_dans_son_noeud():
    """Test de SOURCE (phase 2c, Task 5) : l'inspecteur partage, le nœud
    artefact, les nœuds d'export et la palette. Ce qui est epingle ici :

      · DEUX contextes WebGL, PAS TROIS — l'inspecteur (le nœud selectionne)
        et le viewer du RESULTAT (monte DANS le nœud artefact, deplace depuis
        la section « Apercu » quand le canvas est a l'ecran) ;
      · l'inspecteur POSTe `node-preview` par `M.api.raw` (le detail litteral
        d'un refus est perdu par `M.api.blob`), sous garde de GENERATION,
        DEBOUNCE — un balayage de selection ne doit pas mettre N constructions
        en file — et les aveux du GLB (`extras.ignored`) sont RENDUS ;
      · le nœud artefact porte son nom, « Construire », « figer l'apercu » et
        le RESUME du bordereau ; les nœuds d'export lisent
        `graph_limits.export_formats` et disent l'etat de CHAQUE format au
        motif LITTERAL (jamais un nœud muet) ;
      · la palette fait NAITRE — une entree d'annulation par naissance — et
        REFUSE un maillon flottant : matiere et placement exigent un
        traitement SELECTIONNE et naissent CONNECTES (report T4) ;
      · le plafond `max_elements` est NOMME avant que le backend ne refuse ;
      · designer une arete LACHE la selection de nœud, et l'inspecteur le dit
        (report T4 : l'asymetrie arete/SEL, tranchee)."""
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # ── L'INSPECTEUR : UN SEUL, ET IL LIT LE BACKEND ─────────────────────
    assert 'id="cf-forge3d-inspecteur"' in rendu
    corps = rendu.split("async function inspecte(")[1].split("\n  }")[0]
    assert "node-preview" in corps, corps
    assert "M.api.raw" in corps, corps
    # la garde de GENERATION apres CHAQUE await (doctrine du fichier) : un
    # apercu du deck (ou de la carte) precedent ne se monte pas dans l'ecran
    # du suivant. Invariant, pas compte fige.
    assert corps.count("gen !== GEN") >= corps.count("await "), corps
    # ... et la garde du RETOUR RESEAU porte bien la GENERATION, pas seulement
    # le jeton d'inspection. Les deux ne couvrent PAS la meme chose : le jeton
    # avance quand le SUJET change (une autre selection), `GEN` quand la CARTE
    # ou le DECK change — et une carte qui change pendant la construction
    # ferait peindre l'apercu des couches d'HIER. Le pin d'invariant
    # ci-dessus a une unite de jeu (le `catch` porte une garde lui aussi) :
    # celui-ci vise la zone exacte.
    reseau = corps.split("} catch (e) {", 1)[1].split("if (!r.ok)", 1)[0]
    assert reseau.count("gen !== GEN") >= 2, reseau
    # ... et un changement de CARTE lâche l'apercu, comme il lache les jobs :
    # un GLB d'apercu est construit depuis LES COUCHES d'une carte precise.
    cc = rendu.split("function cardChanged(")[1].split("\n  }")[0]
    assert "videInspecteur(" in cc, cc
    # RONDE DE CORRECTION 2c-T5 (M6) : ... et le BORDEREAU part avec. Les nœuds
    # d'export ne lisent RIEN d'autre que `ARTIFACT` : le garder faisait
    # afficher, sur la carte 2, les poids, les credits et les boutons de
    # telechargement de la carte 1. Meme mensonge que les chips de jobs, au
    # meme endroit. `videApercu` est la porte complete du viewer du RESULTAT
    # (objectURL REVOQUEE, viewer detache, « figer » re-verrouille).
    assert "ARTIFACT = null" in cc, cc
    assert "videApercu(" in cc, cc
    # REPRISE T6 (re-revue de la ronde T5) : ... et LA PROMESSE EST PRISE AVANT
    # LA PEINTURE. `repeintLeBordereau` peint, et TOUTE peinture rappelle
    # `cardChanged` : c'est le verrou `.busy` pose par `refreshManifest` qui
    # ferme la recursion. Les deux appels etaient epingles par leur PRESENCE,
    # jamais par leur ORDRE — un reordonnancement accidentel aurait ravive la
    # boucle sans qu'un seul test rougisse. On mesure donc l'ORDRE (patron du
    # pin M1 de la feuille : c'est lui, et lui seul, qui tranche).
    assert "refreshManifest(" in cc and "repeintLeBordereau(" in cc, cc
    assert cc.index("refreshManifest(") < cc.index("repeintLeBordereau("), cc
    # ... et un JETON d'inspection en plus : deux clics rapides lancent deux
    # requetes, la PREMIERE peut revenir en dernier. Sans jeton, l'inspecteur
    # afficherait le nœud qu'on ne regarde plus.
    assert "INSP_JETON" in corps, corps
    # l'objectURL PRECEDENTE est revoquee (patron mountPreview) — une URL par
    # selection retenue a vie serait une fuite lente
    assert "revokeObjectURL" in corps, corps
    # LE DEBOUNCE : la note de concurrence du relecteur T1. Il vit dans le
    # DECLENCHEUR, pas dans la requete.
    maj = rendu.split("function majInspecteur(")[1].split("\n  }")[0]
    assert "INSP_MS" in maj and "setTimeout" in maj, maj
    ms = re.search(r"const INSP_MS = (\d+);", rendu)
    assert ms and 120 <= int(ms.group(1)) <= 600, ms
    # les AVEUX du GLB sont lus CLIENT (chunk JSON) et rendus
    assert "function glbExtras(" in rendu
    ge = rendu.split("function glbExtras(")[1].split("\n  }")[0]
    assert "getUint32" in ge and "asset" in ge, ge
    assert "ignored" in rendu.split("function inspAvoues(")[1].split("\n  }")[0]
    # ── DEUX CONTEXTES WebGL, PAS TROIS ──────────────────────────────────
    assert rendu.count('createElement("model-viewer")') == 2, \
        rendu.count('createElement("model-viewer")')
    # ── LE NŒUD ARTEFACT ─────────────────────────────────────────────────
    assert "function artifactNodeHtml(" in rendu
    art = rendu.split("function artifactNodeHtml(")[1].split("\n  }")[0]
    assert "build3d" in art, art
    assert "freeze" in art, art
    assert 'data-field="name"' in art, art
    # le RESUME du bordereau vit dans le nœud (poids, moteurs, credits,
    # ignores) et il REUTILISE le rendu du bordereau de la section — deux
    # ecritures des memes aveux auraient derive.
    assert "bordereauHtml(" in art, art
    bd = rendu.split("function bordereauHtml(")[1].split("\n  }")[0]
    assert "weight(" in bd and "ignoresHtml(" in bd, bd
    pa = rendu.split("function paintArtifact(")[1].split("\n  }")[0]
    assert "ignoresHtml(" in pa, pa
    # le viewer du RESULTAT est monte DANS le nœud : `mountPreview` prend son
    # hote en parametre (le retarget du plan), il n'est plus cloue a la section
    mp = rendu.split("async function mountPreview(")[1].split("\n  }")[0]
    assert "hoteApercu(" in mp or "hote" in mp, mp
    ha = rendu.split("function hoteApercu(")[1].split("\n  }")[0]
    assert "cf-forge3d-art-view" in ha, ha
    # RONDE DE CORRECTION 2c-T5 (M5) : « figer » suit la SCENE, pas l'URL. Le
    # drapeau est BAISSE au montage — et avant `src`, sinon un `load` immediat
    # releverait celui qu'on s'apprete a baisser — et RELEVE par le seul
    # evenement qui prouve que la scene est decodee.
    assert "FIGE_PRET = false" in mp, mp
    assert mp.index("FIGE_PRET = false") < mp.index('setAttribute("src"'), mp
    pv = rendu.split("function poseViewer(")[1].split("\n  }")[0]
    assert "FIGE_PRET = true" in pv and '"load"' in pv, pv
    art_f = rendu.split("function artifactNodeHtml(")[1].split("\n  }")[0]
    assert "FIGE_PRET" in art_f and "PREVIEW_URL" in art_f, art_f
    # ── LES NŒUDS D'EXPORT ───────────────────────────────────────────────
    assert "function exportNodeHtml(" in rendu
    exp = rendu.split("function exportNodeHtml(")[1].split("\n  }")[0]
    assert "grabZip(" in rendu or "M.api.blob" in rendu
    # les formats viennent du CONTRAT, jamais recopies ici
    ef = rendu.split("function exportFormats(")[1].split("\n  }")[0]
    assert "export_formats" in ef, ef
    assert "exportFormats(" in exp, exp
    # l'etat de CHAQUE format, au motif LITTERAL — et jamais une erreur quand
    # rien n'est construit : c'est un ETAT.
    et = rendu.split("function exportEtatHtml(")[1].split("\n  }")[0]
    assert "stl" in et and "why" in et, et
    assert "construis" in et, et
    # le corps d'un nœud NE REEMET PAS ses ports (ils vivent dehors) : sinon
    # `paintNode` en poserait deux jeux au premier champ edite.
    nb = rendu.split("function nodeBodyHtml(")[1].split("\n  }")[0]
    assert "portsHtml(" not in nb, nb
    assert "artifactNodeHtml(" in nb and "exportNodeHtml(" in nb, nb
    # ── LA PALETTE ───────────────────────────────────────────────────────
    assert 'id="cf-forge3d-palette"' in rendu
    pal = rendu.split("function paletteHtml(")[1].split("\n  }")[0]
    # le plafond est NOMME avant le refus du backend, et le chiffre vient du
    # contrat (jamais recopie)
    assert "max_elements" in pal, pal
    # une naissance = UNE entree d'annulation (setGraph), jamais deux patches
    for fn in ("function naitCouche(", "function naitProc(",
               "function naitMaillon(", "function naitExport("):
        bloc = rendu.split(fn)[1].split("\n  }")[0]
        assert bloc.count("setGraph(") == 1, (fn, bloc)
        assert "M.patch" not in bloc, (fn, bloc)
    # REPORT T4, TRANCHE : la palette REFUSE un maillon flottant — matiere et
    # placement exigent un traitement SELECTIONNE, et l'arete est posee DANS
    # la meme naissance (ne pas laisser un nœud mort que le bordereau
    # denoncerait). Le refus emprunte les MOTS du bordereau (`surnumeraire`).
    nm = rendu.split("function naitMaillon(")[1].split("\n  }")[0]
    assert "SEL" in nm, nm
    assert "surnumeraire(" in nm, nm
    # ... et le cablage passe par l'ecrivain de chaine EXISTANT (editMat/
    # editTrs -> rewireRow), pas par une seconde recette d'aretes
    assert "editMat(" in nm and "editTrs(" in nm, nm
    # « + export » exige l'artefact et le cable a lui
    ne = rendu.split("function naitExport(")[1].split("\n  }")[0]
    assert "artifact" in ne, ne
    # RONDE DE CORRECTION 2c-T5 (N3) : un format REFUSE n'ECRIT PAS. `setGraph`
    # est inconditionnel plus bas, donc la branche doit SORTIR — sans quoi un
    # menu qui propose une valeur que le contrat ne sert plus pousse une entree
    # d'annulation pour un graphe INCHANGE (« ↶ annuler format » avalerait un
    # geste fantome et le vrai geste resterait sous la pile).
    eg = rendu.split("function editGraph(")[1].split("\n  }")[0]
    br = eg.split('field === "format"')[1].split("} else if (")[0]
    assert "return;" in br, br
    # ── L'ARETE ET LA SELECTION (report T4, tranche) ─────────────────────
    sa = rendu.split("function selectionneArete(")[1].split("\n  }")[0]
    assert "SEL = null" in sa, sa
    assert "majInspecteur(" in sa, sa
    assert "arête" in rendu
    # RONDE DE CORRECTION 2c-T5 (residu S3) : la REPRISE apres un echec passe
    # le garde de balayage, et RIEN d'autre. La condition porte les DEUX
    # moities : un nœud DESIGNE (`!!SEL` — sans quoi chaque pointerdown du
    # fond, qui appelle `selectionne(null)`, rouvrirait le passage et
    # repeindrait la palette a chaque debut de deplacement) ET une cle RENDUE
    # (`!INSP_SUJET` — ce que seul `echecInsp` fait).
    sn = rendu.split("function selectionne(")[1].split("\n  }")[0]
    assert "const reprise = !!SEL && !INSP_SUJET;" in sn, sn
    assert "!reprise" in sn, sn
    # ── RONDE DE CORRECTION 2c-T5 (S2) : LA MOLETTE DU VIEWER EMBARQUE ───
    # Le `model-viewer` vendorise `preventDefault` sa molette mais ne l'ARRETE
    # PAS de remonter : sur le canvas il vit DANS le nœud artefact, donc
    # `onCanvasWheel` (abonne a la surface) zoomait la scene entiere pendant
    # que l'utilisateur croyait dolly-er son modele. Le garde est le PREMIER
    # geste du handler, avant meme `preventDefault` — sinon la molette est
    # confisquee au viewer sans que rien ne bouge chez lui.
    ow = rendu.split("function onCanvasWheel(")[1].split("\n  }")[0]
    assert "cf-forge3d-art-view" in ow, ow
    assert ow.index("cf-forge3d-art-view") < ow.index("preventDefault"), ow
    # ── LES GARDES 2b RESTENT ────────────────────────────────────────────
    pcv = rendu.split("function paintCanvas(")[1].split("\n  }")[0]
    assert "paintCost(" in pcv, pcv
    assert "sondeMoteurs(" in pcv, pcv
    # ── CHAIN_MAX : la clause du report T4 ───────────────────────────────
    # Le commentaire est lu dans le SOURCE (pas dans `rendu`, qui est
    # justement le fichier sans ses commentaires) : la borne est une garde
    # d'API BRUTE, pas une regle que cet ecran pourrait rencontrer.
    cm = src.split("const CHAIN_MAX")[0].rsplit("/*", 1)[-1]
    assert "api brute" in cm.lower(), cm
    # ── LA FEUILLE ───────────────────────────────────────────────────────
    feuille = CSS.read_text(encoding="utf-8")
    for sel in (".cf-forge3d .cf-forge3d-scene {",
                ".cf-forge3d .cf-forge3d-palette {",
                ".cf-forge3d .cf-forge3d-art-view {",
                ".cf-forge3d .cf-forge3d-insp-view {"):
        assert sel in feuille, sel
    # LE SELECTEUR NE SUFFIT PAS ICI, et c'est un mutant qui l'a montré :
    # `.cf-forge3d-inspecteur` apparaît AUSSI dans la requête de média (la
    # colonne passe sous le canvas en étroit), donc un pin par sous-chaîne
    # survit à la disparition de la règle PRINCIPALE. On mesure ce que la
    # règle DIT — la largeur de la colonne.
    corps_insp = re.findall(
        r"\.cf-forge3d \.cf-forge3d-inspecteur \{([^}]*)\}", feuille)
    assert any("flex: 0 0" in c for c in corps_insp), feuille
    # RONDE DE CORRECTION 2c-T5 (M1) : ... et la REQUETE DE MEDIA doit venir
    # APRES cette regle de base. `flex-basis: 100%` y est une LONGHAND ; la
    # forme courte `flex: 0 0 232px` posee PLUS BAS, a specificite egale, la
    # remet a 232 px — le repli sous 720 px etait donc MORT dans la feuille
    # livree (la colonne ecrasait le canvas au lieu de passer dessous). On
    # mesure l'ORDRE, pas la presence : c'est lui, et lui seul, qui tranche.
    m_base = re.search(
        r"\.cf-forge3d \.cf-forge3d-inspecteur \{[^}]*flex: 0 0[^}]*\}",
        feuille)
    m_media = re.search(r"@media \(max-width: 720px\) \{", feuille)
    assert m_base and m_media, feuille
    assert m_media.start() > m_base.end(), (m_media.start(), m_base.end())
    bloc_media = feuille[m_media.start():].split("\n}", 1)[0]
    assert "cf-forge3d-inspecteur" in bloc_media, bloc_media
    # ... et l'ellipse de l'en-tete d'inspecteur n'est pas INERTE : sans
    # `white-space: nowrap` le texte se replie et `text-overflow` ne coupe
    # jamais rien (le patron est `.cf-forge3d-titre`, deux blocs plus haut).
    tete = re.search(
        r"\.cf-forge3d \.cf-forge3d-insp-tete \.mono \{([^}]*)\}", feuille)
    assert tete and "text-overflow: ellipsis" in tete.group(1), feuille
    assert "white-space: nowrap" in tete.group(1), tete.group(1)
    # ... et un viewer sans hauteur declaree se replie a zero : l'hote du
    # resultat DOIT en porter une.
    av = re.search(r"\.cf-forge3d \.cf-forge3d-art-view \{([^}]*)\}", feuille)
    assert av and "height:" in av.group(1), feuille


# ── LE HARNAIS DE CHAINES (2c Task 4) ────────────────────────────────────
# Les pins de source disent QUE le code appelle ; ils ne disent pas CE QU'IL
# REND. Le harnais fait tourner les fonctions PURES du module — les vraies,
# extraites du fichier livre, jamais une reecriture — dans node, et mesure la
# propriete qui compte : un graphe cable A LA SOURIS se lit EXACTEMENT comme
# un graphe cable par la vue liste (`rowModel`/`graphRows`/`rewireRow`).

def _js_fn(src: str, nom: str) -> str:
    """Le SOURCE d'une fonction de `mod-forge3d.js`, accolades equilibrees.

    Le mot `async` qui la precede EST pris : sans lui, le corps extrait
    porterait des `await` hors fonction asynchrone — une erreur de syntaxe que
    node leverait au chargement du banc, pas un cas rouge lisible."""
    i = src.index("function " + nom + "(")
    if src[max(0, i - 6):i] == "async ":
        i -= 6
    j = src.index("{", i)
    n = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            n += 1
        elif src[k] == "}":
            n -= 1
            if n == 0:
                return src[i:k + 1]
    raise AssertionError("accolades non equilibrees pour " + nom)


def _js_decl(src: str, nom: str, mot: str = "const") -> str:
    """La DECLARATION d'une constante (ou d'un `let`) du module, jusqu'au
    point-virgule de premier niveau."""
    i = src.index(mot + " " + nom + " = ")
    prof = 0
    for k in range(i, len(src)):
        c = src[k]
        if c in "{[(":
            prof += 1
        elif c in "}])":
            prof -= 1
        elif c == ";" and prof == 0:
            return src[i:k + 1]
    raise AssertionError("declaration non terminee pour " + nom)


_BANC_CHAINES = r"""
/* le pilote du harnais : il ne DEFINIT rien du module, il l'INTERROGE. */
const out = [];
const dit = (nom, ok, detail) => out.push(
  { nom: nom, ok: !!ok, detail: detail === undefined ? null : detail });
const J = (x) => JSON.stringify(x);
const clone = (g) => JSON.parse(JSON.stringify(g));
const aretes = (g) => (g.edges || []).map((e) => e.from + ">" + e.to).sort();

/* LE GRAPHE NU : les nœuds existent, AUCUNE arete. C'est l'etat que la
   palette (Task 5) laissera derriere elle ; tout le cablage qui suit se fait
   « a la souris » — c'est-a-dire par la fonction pure que le glisser appelle. */
const NU = { nodes: [
  { id: "s1", kind: "layer", role: "illustration", side: "front" },
  { id: "s2", kind: "layer", role: "cadre", side: "front" },
  { id: "t1", kind: "plane", depth_mm: 0.35 },
  { id: "t2", kind: "relief", depth_mm: 0.6, base_mm: 0.3, grid: 160 },
  { id: "m1", kind: "material", mat: "aaa", finish: "aucune" },
  { id: "m2", kind: "material", mat: "bbb", finish: "aucune" },
  { id: "r1", kind: "transform", x_mm: 0, y_mm: 0, z_mm: 0.35, rot_deg: 0, scale: 1 },
  { id: "r2", kind: "transform", x_mm: 0, y_mm: 0, z_mm: 0.7, rot_deg: 0, scale: 1 },
  { id: "asm", kind: "assemble" },
  { id: "art", kind: "artifact", name: "carte3d" },
  { id: "ex", kind: "export", format: "glb" },
], edges: [] };

function cable(g, paires) {
  let cur = g;
  for (let i = 0; i < paires.length; i++) {
    const r = grapheAvecLien(cur, paires[i][0], paires[i][1]);
    if (!r || !r.graph) return { erreur: paires[i].join(">") + " : " + J(r) };
    cur = r.graph;
  }
  return { graph: cur };
}

/* 1. LA CHAINE CABLEE A LA SOURIS SE LIT AVEC LE MEME `rowModel`. */
const avant = J(NU);
const c1 = cable(NU, [["s1", "t1"], ["t1", "m1"], ["m1", "r1"],
                      ["r1", "asm"], ["asm", "art"], ["art", "ex"]]);
dit("la chaine complete se cable", !c1.erreur, c1.erreur || null);
const G = c1.graph;
const row = G ? rowModel(G, "t1") : null;
dit("rowModel retrouve la chaine cablee a la souris",
    !!row && row.layer && row.layer.id === "s1" && row.proc.id === "t1"
    && !!row.mat && row.mat.id === "m1" && !!row.trs && row.trs.id === "r1",
    J(row && { l: row.layer && row.layer.id, m: row.mat && row.mat.id,
               t: row.trs && row.trs.id }));
dit("un seul rang, comme la vue liste",
    !!G && graphRows(G).length === 1, G ? graphRows(G).length : null);
/* la fonction est PURE : le graphe d'entree n'a pas bouge d'un octet */
dit("grapheAvecLien n'ecrit pas dans son entree", J(NU) === avant);

/* 2. ALLER-RETOUR : l'ECRIVAIN DE LA VUE LISTE relit ce que le canvas a
      cable et n'y change RIEN. Les deux vues ecrivent le MEME graphe — si
      elles divergeaient, editer un champ apres avoir cable a la souris
      reecrirait la chaine autrement (et les aretes du canvas sauteraient). */
const gr = clone(G);
rewireRow(gr, "t1", "m1", "r1");
dit("rewireRow relit la chaine du canvas sans la reecrire",
    J(aretes(gr)) === J(aretes(G)), J(aretes(gr)) + " vs " + J(aretes(G)));
const grr = clone(G);
rewireRow(grr, "t1", "m1", "r1");
dit("… et il est idempotent", J(aretes(grr)) === J(aretes(gr)));

/* 3. LA GRAMMAIRE REFUSE A L'ARETE, ET LE MOTIF EST NOMME. */
const refus = [["s1", "asm"], ["m1", "art"], ["ex", "art"], ["t1", "s1"],
               ["art", "asm"]];
refus.forEach((p) => {
  const r = grapheAvecLien(G, p[0], p[1]);
  dit("refus " + p.join(">"),
      !!r && !r.graph && typeof r.refus === "string"
      && r.refus.indexOf("chaîne attendue") >= 0, J(r));
});
dit("un lien valide reste valide", !!(grapheAvecLien(NU, "s2", "t1") || {}).graph);

/* 4. LE DOUBLON N'EST NI UNE ERREUR NI UNE ECRITURE : rien a annuler, rien
      a dire. */
const dbl = grapheAvecLien(G, "s1", "t1");
dit("un doublon ne rend pas de graphe", !!dbl && !dbl.graph && dbl.deja === true, J(dbl));

/* 5. LA REGLE DE CHAINE UNIQUE EST TENUE AVANT L'ECRITURE (le backend, lui,
      accepte et AVOUE au bordereau : « maillon surnumeraire »). */
const sur = grapheAvecLien(G, "t1", "m2");
dit("une seconde matiere sur la meme chaine est refusee AVANT d'etre ecrite",
    !!sur && !sur.graph && typeof sur.refus === "string"
    && sur.refus.indexOf("surnum") >= 0, J(sur));
const src2 = grapheAvecLien(G, "s2", "t1");
dit("une seconde source sur le meme traitement est refusee",
    !!src2 && !src2.graph && typeof src2.refus === "string"
    && src2.refus.indexOf("surnum") >= 0, J(src2));

/* 5bis. UN MAILLON N'APPARTIENT QU'A UNE CHAINE (C1). Le surnombre que le
      controle ne voyait pas : la question posee etait « MA chaine en a-t-elle
      deja un ? », jamais « ce maillon-ci appartient-il deja a quelqu'un ? ».
      Un maillon PARTAGE passait donc, et le degat arrivait plus tard et
      ailleurs : `rewireRow` reecrit la rangee editee EN PREMIER et purge
      l'arete que l'autre empruntait — la seconde chaine cesse d'etre
      construite (« traitement non relie a un assemble » au bordereau) tout
      en s'affichant encore comme une rangee. LE BANC est la couche qui
      attrape ca : un pin de source y survit (le nom d'une fonction ne dit
      pas ce qu'elle refuse). */
const deux = cable(NU, [["s1", "t1"], ["t1", "m1"], ["m1", "asm"],
                        ["s2", "t2"], ["t2", "r1"], ["r1", "asm"]]);
dit("deux chaines se cablent", !deux.erreur, deux.erreur || null);
const D = deux.graph;
const vole = D ? grapheAvecLien(D, "m1", "r1") : null;
dit("un maillon DEJA pris par une autre chaine est refuse",
    !!vole && !vole.graph && typeof vole.refus === "string"
    && vole.refus.indexOf("autre chaîne") >= 0, J(vole));
/* ... et le refus ne mord PAS le cas inoffensif : un maillon LIBRE se
   branche, meme quand une autre chaine porte deja un maillon du meme genre. */
const libre = D ? grapheAvecLien(D, "m1", "r2") : null;
dit("un maillon LIBRE reste branchable", !!libre && !!libre.graph, J(libre));

/* 5ter. LE CONTROLE NE S'AVEUGLE PLUS SANS COUCHE (I2). Couper
      `layer -> traitement` est un geste de PREMIERE CLASSE depuis la Task 4 ;
      la chaine disparait alors de `graphRows` (qui n'a de rang qu'AVEC une
      couche) et le controle de surnombre recevait `null` — donc acceptait
      tout, c'est-a-dire creer-puis-avouer. Le seul chemin ou la source n'est
      PAS un traitement est `matiere -> placement` (la grammaire ne mene a
      `material` que depuis un traitement) : c'est donc lui qu'on mesure. */
const orph = cable(NU, [["t1", "m1"], ["m1", "r1"], ["r1", "asm"]]);
dit("une chaine SANS couche se cable", !orph.erreur, orph.erreur || null);
const O = orph.graph;
dit("... et n'a effectivement aucun rang (c'est ce qui aveuglait le controle)",
    !!O && graphRows(O).length === 0, O ? graphRows(O).length : null);
const sur2 = O ? grapheAvecLien(O, "m1", "r2") : null;
dit("un second placement sur une chaine sans couche est refuse AVANT l'ecriture",
    !!sur2 && !sur2.graph && typeof sur2.refus === "string"
    && sur2.refus.indexOf("surnum") >= 0, J(sur2));
/* le meme controle depuis le traitement lui-meme (chemin deja sain) */
const sur3 = O ? grapheAvecLien(O, "t1", "m2") : null;
dit("... et une seconde matiere aussi, sans couche non plus",
    !!sur3 && !sur3.graph && typeof sur3.refus === "string"
    && sur3.refus.indexOf("surnum") >= 0, J(sur3));

/* 6. COUPER UNE ARETE : la chaine tombe, et AUCUNE arete pendante ne reste. */
const coupe = grapheSansLien(G, "s1", "t1");
const GC = coupe && coupe.graph;
dit("couper la source vide le rang",
    !!GC && !rowModel(GC, "t1").layer && graphRows(GC).length === 0,
    GC ? J(graphRows(GC).length) : null);
const vivants = {};
((GC && GC.nodes) || []).forEach((n) => { vivants[n.id] = 1; });
dit("aucune arete pendante apres la coupe",
    !!GC && (GC.edges || []).every((e) => vivants[e.from] && vivants[e.to]),
    GC ? J(GC.edges) : null);
dit("couper une arete qui n'existe pas n'ecrit rien",
    grapheSansLien(G, "s2", "asm") === null);

/* 7. LES PORTS DERIVENT DE LA TABLE (et pas d'une seconde liste). */
dit("une couche n'a pas d'entree", !aEntree("layer") && aSortie("layer"));
dit("un export n'a pas de sortie", aEntree("export") && !aSortie("export"));
["plane", "relief", "mesh3d", "material", "transform", "assemble", "artifact"]
  .forEach((k) => dit("le kind " + k + " a ses deux ports",
                      aEntree(k) && aSortie(k)));
dit("la chaine attendue se lit", chaineAttendue().indexOf("→") > 0,
    chaineAttendue());

process.stdout.write(JSON.stringify(out));
"""


def _banc_chaines(tmp_path) -> list:
    """Fait tourner les VRAIES fonctions de chaine de `mod-forge3d.js`."""
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le harnais de chaines ne peut pas tourner")
    src = re.sub(r"/\*.*?\*/", " ", JS.read_text(encoding="utf-8"), flags=re.S)
    morceaux = [_js_decl(src, "PROC_KINDS"), _js_decl(src, "CHAIN_MAX"),
                _js_decl(src, "KIND_LABELS"), _js_decl(src, "GRAMMAIRE"),
                _js_decl(src, "ROWS_MEMO", "let")]
    for nom in ("connu", "sansProto", "kindLabel", "rowModel", "graphRows",
                "rowsDe", "rowDuNoeud", "lienValide", "aEntree", "aSortie",
                "chaineAttendue", "chaineDe", "surnumeraire", "grapheAvecLien",
                "grapheSansLien", "maillonsAval", "rewireRow"):
        morceaux.append(_js_fn(src, nom))
    js = tmp_path / "banc_chaines.js"
    js.write_text("\n".join(morceaux) + "\n" + _BANC_CHAINES, encoding="utf-8")
    r = subprocess.run([node, str(js)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


_BANC_PALETTE = r"""
/* ── LE PILOTE (2c Task 5) ────────────────────────────────────────────────
   Il n'ecrit AUCUNE logique du module : il pose les STUBS de ce que le module
   lit du CORE (le document, le jeton `M`, les peintres) et interroge les
   VRAIES fonctions, extraites du fichier livre. */
const out = [];
const dit = (nom, ok, detail) => out.push(
  { nom: nom, ok: !!ok, detail: detail === undefined ? null : detail });
const J = (x) => JSON.stringify(x);

/* 1. LA PALETTE NE FAIT PAS NAITRE DE MAILLON FLOTTANT (report T4, tranche) */
const INFO0 = { graph_limits: { max_elements: 12,
                         export_formats: ["glb", "stl", "metadata", "preview"] },
         materials: [{ id: "aaa", name: "gres" }],
         material_limits: { tile_mm: [10, 200], finishes: ["aucune", "argent"] },
         transform_limits: { xy_mm: [-100, 100], z_mm: [0, 10],
                             rot_deg: [-180, 180], scale: [0.1, 4] },
         mesh3d: { engines: [], default_engine: "meshy-7", has_meshy: false } };
INFO = INFO0;
LAST_MANIFEST = { side: "front",
                  layers: [{ role: "cadre" }, { role: "illustration" },
                           { role: "typographie" }] };
const NU = { nodes: [
  { id: "s1", kind: "layer", role: "cadre", side: "front" },
  { id: "t1", kind: "plane", depth_mm: 0.35 },
  { id: "asm", kind: "assemble" },
  { id: "art", kind: "artifact", name: "carte3d" },
], edges: [{ from: "s1", to: "t1" }, { from: "t1", to: "asm" },
           { from: "asm", to: "art" }] };
DOC_GRAPH = NU;
const raz = () => { TOASTS.length = 0; PATCHES.length = 0; HIST.length = 0; };

SEL = null;
raz();
naitMaillon("material");
dit("sans traitement designe, « + matiere » n'ECRIT rien",
    PATCHES.length === 0 && TOASTS.length === 1, J(TOASTS));
dit("... et le refus dit QUOI FAIRE, il ne se contente pas de refuser",
    /d[eé]signe d'abord/i.test(TOASTS[0] || ""), TOASTS[0]);
SEL = "asm";
raz();
naitMaillon("transform");
dit("un nœud designe qui n'est pas un TRAITEMENT ne suffit pas",
    PATCHES.length === 0 && TOASTS.length === 1, J(TOASTS));

/* 2. AVEC un traitement designe, le maillon nait CONNECTE (jamais mort) */
SEL = "t1";
raz();
naitMaillon("material");
dit("une naissance = UNE entree d'annulation, un seul patch",
    HIST.length === 1 && PATCHES.length === 1, J(HIST.map((h) => h.label)));
const G = DOC_GRAPH;
const r1 = rowModel(G, "t1");
dit("la matiere nait DANS la chaine, et porte une vraie matiere (sinon "
    + "clean_graph la jetterait)",
    !!r1 && !!r1.mat && r1.mat.mat === "aaa", J(r1 && r1.mat));
dit("... et la chaine rejoint TOUJOURS l'assemblage",
    !!r1 && (G.edges || []).some((e) => e.from === r1.mat.id && e.to === "asm"),
    J(G.edges));

/* 3. UN SECOND MAILLON EST REFUSE AVANT L'ECRITURE, dans les mots du
      bordereau (`surnumeraire`, la MEME phrase que le glisser de fil) */
raz();
naitMaillon("material");
dit("une seconde matiere est refusee AVANT d'etre ecrite",
    PATCHES.length === 0 && /surnum/.test(TOASTS[0] || ""), J(TOASTS));

/* 4. LE PLACEMENT NAIT AU BOUT DE LA CHAINE, pas en eventail depuis le
      traitement — c'est exactement le residu que la palette ne doit pas
      rendre trivial */
raz();
naitMaillon("transform");
const G2 = DOC_GRAPH;
const r2 = rowModel(G2, "t1");
dit("le placement nait dans la chaine", !!r2 && !!r2.trs, J(r2 && r2.trs));
dit("... APRES la matiere, jamais en eventail depuis le traitement",
    !!r2 && (G2.edges || []).some((e) => e.from === r2.mat.id && e.to === r2.trs.id)
    && !(G2.edges || []).some((e) => e.from === "t1" && e.to === r2.trs.id),
    J(G2.edges));
dit("... et son z est celui de l'EMPILEMENT du plan, pas un zero",
    !!r2 && r2.trs.z_mm === 0.35, J(r2 && r2.trs));

/* 5. LE PLAFOND EST DIT AVANT QUE LE BACKEND NE REFUSE */
INFO.graph_limits.max_elements = 3;
DOC_GRAPH = { nodes: [
  { id: "s1", kind: "layer", role: "cadre", side: "front" },
  { id: "t1", kind: "plane" },
  { id: "s2", kind: "layer", role: "illustration", side: "front" },
  { id: "t2", kind: "plane" },
  { id: "s3", kind: "layer", role: "typographie", side: "front" },
  { id: "t3", kind: "plane" },
  { id: "asm", kind: "assemble" },
  { id: "art", kind: "artifact", name: "x" }],
  edges: [{ from: "s1", to: "t1" }, { from: "s2", to: "t2" },
          { from: "s3", to: "t3" }, { from: "t1", to: "asm" },
          { from: "t2", to: "asm" }, { from: "t3", to: "asm" },
          { from: "asm", to: "art" }] };
dit("trois rangs", graphRows(DOC_GRAPH).length === 3,
    graphRows(DOC_GRAPH).length);
raz();
naitProc();
dit("au plafond, « + traitement » refuse AVANT le 400 du backend",
    PATCHES.length === 0 && /maximum construisible est 3/.test(TOASTS[0] || ""),
    J(TOASTS));
dit("... et la palette le NOMME sans attendre le refus",
    paletteHtml().indexOf("3 / 3 &eacute;l") >= 0
    || paletteHtml().indexOf("3 / 3 él") >= 0, paletteHtml());
INFO.graph_limits.max_elements = 12;

/* 6. « + COUCHE » NE PROPOSE QUE CE QUI EST LIVRE ET PAS ENCORE SOURCE */
DOC_GRAPH = NU;
dit("les couches restantes sont celles du manifeste, moins les sources",
    J(couchesRestantes(DOC_GRAPH)) === J(["illustration", "typographie"]),
    J(couchesRestantes(DOC_GRAPH)));
PAL.role = "typographie";
raz();
naitCouche();
const G3 = DOC_GRAPH;
const neuve = (G3.nodes || []).filter(
  (n) => n.kind === "layer" && n.role === "typographie")[0];
dit("« + couche » pose LA couche choisie, une seule ecriture",
    HIST.length === 1 && !!neuve, J((G3.nodes || []).map((n) => n.id)));
dit("... et elle nait LIBRE (une couche se relie au geste suivant)",
    !!neuve && !(G3.edges || []).some(
      (e) => e.from === neuve.id || e.to === neuve.id), J(G3.edges));

/* 7. « + EXPORT » EXIGE L'ARTEFACT, ET SE CABLE A LUI */
DOC_GRAPH = { nodes: [{ id: "asm", kind: "assemble" }], edges: [] };
raz();
naitExport();
dit("sans nœud artefact, « + export » n'ecrit rien",
    PATCHES.length === 0 && /artefact/.test(TOASTS[0] || ""), J(TOASTS));
DOC_GRAPH = NU;
PAL.format = "stl";
raz();
naitExport();
const G4 = DOC_GRAPH;
const ex = (G4.nodes || []).filter((n) => n.kind === "export")[0];
dit("« + export » nait CONNECTE a l'artefact, au format choisi",
    !!ex && ex.format === "stl"
    && (G4.edges || []).some((e) => e.from === "art" && e.to === ex.id),
    J(ex) + " " + J(G4.edges));

/* 8. L'ETAT D'UN EXPORT — AU MOTIF LITTERAL, JAMAIS MUET */
ARTIFACT = null;
dit("sans build, un export dit « construis d'abord » (un ETAT, pas une erreur)",
    exportEtatHtml("glb").indexOf("construis d'abord") >= 0,
    exportEtatHtml("glb"));
ARTIFACT = { elements: 2, glb: { name: "x.glb", bytes: 2048 },
             metadata: { name: "x.json", bytes: 300 },
             stl: { written: false,
                    why: "solide non ferme : 4 aretes de bord" },
             preview: { expected: "x_preview.png", written: false },
             elements_detail: [
               { name: "a", kind: "relief", node: "t1" },
               { name: "b", kind: "mesh3d", node: "m1", engine: "meshy-7",
                 credits: 30 }],
             ignored: [{ node: "m9", why: "maillon surnumeraire" }] };
dit("glb : le poids ET le bouton de telechargement",
    exportEtatHtml("glb").indexOf("2.0 Kio") >= 0
    && exportEtatHtml("glb").indexOf('data-act="grab-file"') >= 0,
    exportEtatHtml("glb"));
dit("stl refuse : le MOTIF du backend, mot pour mot",
    exportEtatHtml("stl").indexOf("solide non ferme : 4 aretes de bord") >= 0,
    exportEtatHtml("stl"));
dit("... et AUCUN bouton de telechargement pour un fichier qui n'existe pas",
    exportEtatHtml("stl").indexOf("grab-file") < 0, exportEtatHtml("stl"));
dit("preview : attendu tant qu'il n'est pas fige, et NOMME",
    /attendu/.test(exportEtatHtml("preview"))
    && exportEtatHtml("preview").indexOf("x_preview.png") >= 0,
    exportEtatHtml("preview"));
ARTIFACT.preview = { expected: "x_preview.png", written: true, bytes: 4096 };
dit("... et telechargeable une fois ecrit",
    exportEtatHtml("preview").indexOf('data-act="grab-file"') >= 0,
    exportEtatHtml("preview"));

/* 9. LE RESUME DU BORDEREAU, DANS LE NŒUD ARTEFACT */
const bd = bordereauHtml(ARTIFACT);
dit("le resume dit poids, moteur et credits CONSOMMES",
    bd.indexOf("2.0 Kio") >= 0 && bd.indexOf("meshy-7") >= 0
    && bd.indexOf("30 cr") >= 0, bd);
dit("... et les aveux du backend, mot pour mot",
    bd.indexOf("maillon surnumeraire") >= 0, bd);
dit("sans bordereau, il le DIT au lieu de se taire",
    bordereauHtml(null).indexOf("rien de construit") >= 0,
    bordereauHtml(null));

/* 9bis. « PUBLIER DANS LA BIBLIOTHEQUE » (2c Task 6) — l'ETAT, pas l'action */
dit("sans bordereau, AUCUN bouton de publication : publier n'est pas "
    + "construire", publieHtml(null) === "", publieHtml(null));
const pb0 = publieHtml(ARTIFACT);
dit("avec un bordereau, le bouton est la et l'etat dit « pas encore publie »",
    pb0.indexOf('data-act="publish-lib"') >= 0
    && /pas encore publi/.test(pb0) && pb0.indexOf("disabled") < 0, pb0);
publishLibrary.busy = true;
dit("... et pendant le geste il est VERROUILLE (patron build3d.busy)",
    publieHtml(ARTIFACT).indexOf("disabled") >= 0, publieHtml(ARTIFACT));
publishLibrary.busy = false;
/* M4 (ronde de correction T6) : et pendant une CONSTRUCTION aussi — ce qui
   part a la Bibliotheque est le fichier que `build3d` est en train d'ecrire. */
build3d.busy = true;
dit("... et pendant une CONSTRUCTION il est verrouille lui aussi",
    publieHtml(ARTIFACT).indexOf("disabled") >= 0, publieHtml(ARTIFACT));
build3d.busy = false;
dit("... et il se DEVERROUILLE quand les deux gestes sont finis",
    publieHtml(ARTIFACT).indexOf("disabled") < 0, publieHtml(ARTIFACT));
ARTIFACT.published = { job_id: "aaaabbbb-cccc-dddd-eeee-ffff00001111",
                       short: "aaaabbbb",
                       title: "Carte 3D · Mon deck · carte3d" };
const pb1 = publieHtml(ARTIFACT);
dit("une fois publie, le bordereau porte le TITRE publie et le dossier servi",
    pb1.indexOf("Carte 3D") >= 0 && pb1.indexOf("carte3d") >= 0
    && pb1.indexOf("aaaabbbb") >= 0, pb1);
dit("... et le bouton propose de REPUBLIER (le serveur est idempotent)",
    /republier/.test(pb1) && pb1.indexOf('data-act="publish-lib"') >= 0, pb1);
dit("... et le titre publie est ECHAPPE, jamais concatene brut",
    publieHtml({ elements: 1, glb: { name: "x", bytes: 1 },
                 published: { title: '<img src=x onerror=1>', short: "s" } })
      .indexOf("<img") < 0,
    publieHtml({ elements: 1, glb: { name: "x", bytes: 1 },
                 published: { title: '<img src=x onerror=1>', short: "s" } }));
delete ARTIFACT.published;

/* 10. LE CORPS D'UN NŒUD ARTEFACT / EXPORT */
DOC_GRAPH = G4;
const corpsArt = nodeBodyHtml("art");
dit("le nœud artefact porte son nom, Construire, figer et l'hote du viewer",
    corpsArt.indexOf('data-field="name"') >= 0
    && corpsArt.indexOf('data-act="build3d"') >= 0
    && corpsArt.indexOf('data-act="freeze"') >= 0
    && corpsArt.indexOf("cf-forge3d-art-view") >= 0, corpsArt);
dit("... et l'edition s'ecrit A SON NOM (data-proc = lui-meme)",
    corpsArt.indexOf('data-proc="art"') >= 0, corpsArt);
dit("... sans vignette : le viewer EST son image",
    corpsArt.indexOf("cf-forge3d-thumb") < 0, corpsArt);
const corpsEx = nodeBodyHtml(ex.id);
dit("le nœud d'export porte son format et l'etat de ce format",
    corpsEx.indexOf('data-field="format"') >= 0
    && corpsEx.indexOf("solide non ferme") >= 0, corpsEx);
dit("... et AUCUN port (ils vivent hors du corps)",
    corpsEx.indexOf("cf-forge3d-port") < 0, corpsEx);

/* 11. LES FORMATS VIENNENT DU CONTRAT, ET SON ABSENCE SE DIT */
dit("les formats sont ceux du contrat",
    J(exportFormats()) === J(["glb", "stl", "metadata", "preview"]),
    J(exportFormats()));
INFO = { graph_limits: {}, materials: [] };
dit("contrat absent : aucun format invente", exportFormats().length === 0);
dit("... et le nœud le DIT au lieu d'un menu vide",
    exportNodeHtml({ id: "e1", kind: "export", format: "glb" })
      .indexOf("formats inconnus") >= 0,
    exportNodeHtml({ id: "e1", kind: "export", format: "glb" }));

/* 12. LES AVEUX D'UN VRAI GLB, LUS COTE CLIENT */
const bin = Buffer.from(GLB_B64, "base64");
const ab = bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.byteLength);
const ex2 = glbExtras(ab);
dit("les aveux se lisent dans le chunk JSON d'un VRAI GLB (octets du backend)",
    !!ex2 && Array.isArray(ex2.ignored) && ex2.ignored.length === 1
    && ex2.ignored[0].node === "m9", J(ex2));
dit("le schema de l'apercu est celui de l'APERCU, pas d'un artefact",
    !!ex2 && ex2.schema === "card-3d/apercu@1", J(ex2 && ex2.schema));
dit("un octet inattendu ne leve pas : il rend null",
    glbExtras(new ArrayBuffer(8)) === null && glbExtras(null) === null);

/* 13. UN SEUL SUJET A LA FOIS (report T4, tranche) — mesure, pas promesse :
      le NOM d'une fonction ne dit pas ce qu'elle lache. */
DOC_GRAPH = NU;
VUE = "canvas";
ARETE = null; SEL = null; INSP_SUJET = "";
NOMS.length = 0; ETATS.length = 0; INSPECTES.length = 0;
selectionne("t1");
dit("designer un nœud fait de LUI le sujet de l'inspecteur",
    SEL === "t1" && INSP_SUJET === "n:t1", SEL + " / " + INSP_SUJET);
dit("... et l'apercu est DIFFERE (debounce), jamais lance sur le champ",
    INSPECTES.length === 0, J(INSPECTES));
NOMS.length = 0; ETATS.length = 0; INSPECTES.length = 0;
selectionneArete("s1", "t1");
dit("designer une arete LACHE la selection de nœud", SEL === null, String(SEL));
dit("... et l'inspecteur le DIT au lieu de se vider",
    (NOMS[NOMS.length - 1] || "").indexOf("s1") >= 0
    && (NOMS[NOMS.length - 1] || "").indexOf("t1") >= 0, J(NOMS));
dit("... et ne construit RIEN (une arete n'est pas un element)",
    INSPECTES.length === 0, J(INSPECTES));
NOMS.length = 0;
/* « asm » et pas « t2 » : ce cas designait un nœud QUI N'EXISTE PAS dans NU,
   et la relache S1 (ronde de correction) le refuse desormais — a raison. Ce
   qu'il mesure (reprendre un nœud lache l'arete, quel que soit l'ordre des
   appels) demande juste un nœud REEL, et un AUTRE que celui d'avant. */
selectionne("asm");
dit("... et reprendre un nœud lache l'arete, sans dependre de l'ordre "
    + "des appels", ARETE === null && SEL === "asm" && INSP_SUJET === "n:asm",
    J(ARETE) + " / " + SEL + " / " + INSP_SUJET);
/* ... et un nœud ABSENT du graphe n'est pas un sujet : la relache tombe des
   la designation (le meme garde, atteint par l'autre porte). */
selectionne("t2");
dit("designer un nœud absent du graphe ne pose AUCUN sujet",
    SEL === null && INSP_SUJET === "", String(SEL) + " / " + J(INSP_SUJET));
videInspecteur();   /* rend la minuterie : node n'a pas a attendre le debounce */

/* ═══════════════════════════════════════════════════════════════════════════
   RONDE DE CORRECTION 2c-T5 — ce que la revue adverse a trouve, mesure ICI.
   ═══════════════════════════════════════════════════════════════════════════ */

/* 14. S1 — UN SUJET QUI QUITTE LE GRAPHE EST LACHE. « ↶ annuler », ou un
      maillon vide par `editMat`, fait disparaitre le nœud DESIGNE. Sans
      relache, la cle de sujet fait sortir `majInspecteur` PAR LE HAUT et le
      panneau garde le nom ET le 3D d'un mort, pour toujours. `majSelArete`
      lache DEJA l'arete disparue : c'etait l'asymetrie. */
INFO = INFO0;       /* la section 11 avait mis le contrat a zero */
DOC_GRAPH = NU;
VUE = "canvas";
ARETE = null; SEL = null; INSP_SUJET = "";
NOMS.length = 0;
selectionne("t1");
dit("le nœud designe est bien le sujet",
    SEL === "t1" && INSP_SUJET === "n:t1", SEL + " / " + INSP_SUJET);
NOMS.length = 0;
DOC_GRAPH = { nodes: (NU.nodes || []).filter((n) => n.id !== "t1"), edges: [] };
majInspecteur();
dit("un nœud disparu du graphe LACHE la selection (comme l'arete disparue)",
    SEL === null, String(SEL));
dit("... et le panneau se VIDE au lieu de garder un mort a l'affiche",
    INSP_SUJET === "" && NOMS[NOMS.length - 1] === "", J(NOMS));

/* 15. M4 — UN MAILLON NE NAIT PAS SUR UN TRAITEMENT SANS SOURCE. Il naitrait
      CABLE (`editMat` le relie), mais son corps dirait « matiere hors chaine
      — aucun traitement ne la porte », ce qui est FAUX : le traitement la
      porte, c'est la COUCHE qui manque. Un ecran qui se trompe de coupable
      est pire qu'un ecran qui refuse. */
DOC_GRAPH = { nodes: [
  { id: "t9", kind: "plane", depth_mm: 0.2 },
  { id: "asm", kind: "assemble" },
  { id: "art", kind: "artifact", name: "x" }],
  edges: [{ from: "t9", to: "asm" }, { from: "asm", to: "art" }] };
SEL = "t9";
raz();
naitMaillon("material");
dit("un traitement SANS couche source ne fait naitre aucun maillon",
    PATCHES.length === 0 && TOASTS.length === 1, J(TOASTS));
dit("... et le refus nomme le VRAI manque : relier une couche d'abord",
    /couche/i.test(TOASTS[0] || "") && /relie/i.test(TOASTS[0] || ""),
    TOASTS[0]);
raz();
naitMaillon("transform");
dit("... et c'est vrai du placement aussi",
    PATCHES.length === 0 && TOASTS.length === 1, J(TOASTS));

/* 16. N8 — DEUX EXPORTS DU MEME FORMAT NE TELECHARGENT PAS DEUX FOIS PLUS. */
DOC_GRAPH = NU;
PAL.format = "stl";
raz();
naitExport();
dit("le premier export d'un format nait",
    PATCHES.length === 1
    && (DOC_GRAPH.nodes || []).filter((n) => n.kind === "export").length === 1,
    J((DOC_GRAPH.nodes || []).map((n) => n.id)));
raz();
naitExport();
dit("le SECOND du meme format est refuse, nomme",
    PATCHES.length === 0 && /existe d[eé]j/.test(TOASTS[0] || ""), J(TOASTS));
PAL.format = "glb";
raz();
naitExport();
dit("... mais un AUTRE format nait sans discuter",
    PATCHES.length === 1
    && (DOC_GRAPH.nodes || []).filter((n) => n.kind === "export").length === 2,
    J((DOC_GRAPH.nodes || []).map((n) => n.id)));

/* 16bis. N5 — LE GARDE `|| []` A L'ECRITURE. Un graphe charge a la main peut
      n'avoir aucune clef `nodes` (ou aucune clef `edges`) : TOUTE la lecture
      du module le tolere deja (`grapheAvecLien`, `aretes`, `rowsDe`…), seule
      la naissance levait — et une exception ici emporte la peinture entiere,
      pas seulement le bouton clique. */
DOC_GRAPH = {};
PAL.role = "";
raz();
naitCouche();
dit("un graphe SANS clef `nodes` ne fait pas lever « + couche »",
    PATCHES.length === 1 && (DOC_GRAPH.nodes || []).length === 1,
    J(DOC_GRAPH));
DOC_GRAPH = {};
raz();
naitProc();
dit("... ni « + traitement »",
    PATCHES.length === 1 && (DOC_GRAPH.nodes || []).length === 1,
    J(DOC_GRAPH));
DOC_GRAPH = { nodes: [{ id: "art", kind: "artifact", name: "x" }] };
PAL.format = "glb";
raz();
naitExport();
dit("... et un graphe SANS clef `edges` ne fait pas lever « + export » (il "
    + "nait CABLE : l'arete doit bien s'ecrire quelque part)",
    PATCHES.length === 1 && (DOC_GRAPH.edges || []).length === 1,
    J(DOC_GRAPH));

/* 17. M5 — « FIGER L'APERCU » NE S'ARME PAS AVANT QUE LA SCENE SOIT CHARGEE.
      `mountPreview` VERROUILLE le bouton jusqu'a l'evenement `load` du viewer
      (`majFige`), mais le corps du nœud artefact, lui, se reconstruit a chaque
      champ commis et le RE-ARMAIT sur la seule presence de `PREVIEW_URL` :
      dans cette fenetre, « figer » capturait un cadre VIDE — et cette capture
      devient l'image de la carte. L'etat n'est donc pas « une URL existe »
      mais « la scene est la ». */
PREVIEW_URL = null; FIGE_PRET = false;
const artHtml = () => artifactNodeHtml({ id: "art", kind: "artifact",
                                         name: "carte3d" });
dit("sans apercu monte, « figer » est verrouille",
    /data-act="freeze"[^>]*disabled/.test(artHtml()), artHtml());
PREVIEW_URL = "blob:x";
dit("... et il RESTE verrouille tant que la scene n'a pas dit « load » (une "
    + "capture de cadre vide deviendrait l'image de la carte)",
    /data-act="freeze"[^>]*disabled/.test(artHtml()), artHtml());
FIGE_PRET = true;
dit("... et il ne s'arme qu'ensuite",
    !/data-act="freeze"[^>]*disabled/.test(artHtml()), artHtml());
PREVIEW_URL = null;
dit("... et un apercu LACHE (changement de carte) le re-verrouille",
    /data-act="freeze"[^>]*disabled/.test(artHtml()), artHtml());
FIGE_PRET = false;

/* 18. S3 — LES SORTIES D'ECHEC DE `inspecte` NE LAISSENT RIEN DE L'ANCIEN.
      Un transport coupe, un refus du serveur ou un corps vide laissaient le
      modele PRECEDENT sous le NOM du nouveau nœud — et la cle de sujet,
      restee posee, rendait l'echec COLLANT : ni la re-selection ni une
      peinture ne re-essayaient. C'est la VRAIE fonction qui tourne ici ; seul
      le transport est pilote. */
const MVF = { pris: [], parentNode: null,
              removeAttribute: (n) => { MVF.pris.push("-" + n); },
              setAttribute: (n, v) => { MVF.pris.push(n + "=" + v); } };
const armeVue = () => {
  INSP_VIEW_EL = { innerHTML: "<model-viewer></model-viewer>" };
  INSP_MV = MVF;
  MVF.pris.length = 0;
  REVOQUEES.length = 0;
  ETATS.length = 0;
  INSP_SUJET = "n:t1";
};

async function banc18() {
  DOC_GRAPH = NU;
  /* (a) LE TRANSPORT COUPE — la seule panne qui a droit au rouge */
  armeVue(); INSP_URL = "blob:vieux";
  RAW = () => { throw new Error("transport coupé"); };
  await inspecte("t1");
  dit("transport coupe : la boite du viewer est VIDEE (le modele d'avant ne "
      + "reste pas a l'ecran sous le nom du nouveau nœud)",
      INSP_VIEW_EL.innerHTML === "", J(INSP_VIEW_EL.innerHTML));
  dit("... l'objectURL d'avant est REVOQUEE, pas seulement oubliee",
      INSP_URL === null && REVOQUEES.indexOf("blob:vieux") >= 0, J(REVOQUEES));
  dit("... et la cle de sujet est RENDUE (sinon l'echec est collant : aucune "
      + "peinture ne re-essaierait)", INSP_SUJET === "", J(INSP_SUJET));
  dit("... le motif est dit tel quel, et en rouge",
      /transport/.test(ETATS[ETATS.length - 1] || ""), J(ETATS));

  /* (b) LE REFUS NOMME DU SERVEUR — un ETAT, pas une panne */
  armeVue(); INSP_URL = null;
  RAW = () => ({ ok: false, status: 409, statusText: "Conflict",
                 json: async () => ({ detail: "lance-le d'abord" }) });
  await inspecte("t1");
  dit("refus du serveur : le motif LITTERAL, jamais un resume",
      (ETATS[ETATS.length - 1] || "").indexOf("lance-le d'abord") >= 0,
      J(ETATS));
  dit("... la boite est vidée", INSP_VIEW_EL.innerHTML === "",
      J(INSP_VIEW_EL.innerHTML));
  dit("... et la cle de sujet est rendue LA AUSSI (« lance-le d'abord » se "
      + "re-tente : c'est meme le seul refus qui INVITE a re-essayer)",
      INSP_SUJET === "", J(INSP_SUJET));

  /* (c) UN CORPS VIDE — le serveur a repondu 200 et n'a rien livre */
  armeVue(); INSP_URL = "blob:vieux2";
  RAW = () => ({ ok: true, blob: async () => { throw new Error("vide"); } });
  await inspecte("t1");
  dit("corps illisible : boite vidée, URL revoquee, sujet rendu",
      INSP_VIEW_EL.innerHTML === "" && INSP_URL === null
      && INSP_SUJET === "" && REVOQUEES.indexOf("blob:vieux2") >= 0,
      J(INSP_VIEW_EL.innerHTML) + " " + J(INSP_SUJET) + " " + J(REVOQUEES));
  dit("... et il a droit au rouge (ca, c'est casse)",
      /illisible/.test(ETATS[ETATS.length - 1] || ""), J(ETATS));

  /* (d) LE SUCCES NE VIDE RIEN, ET GARDE SA CLE — l'ancre de mutation : un
        `videApercuInsp` (ou un `INSP_SUJET = ""`) pose trop haut effacerait
        l'apercu au moment precis ou il arrive, et rendrait le declencheur
        non idempotent. */
  armeVue(); INSP_URL = null;
  RAW = () => ({ ok: true, blob: async () => ({
    arrayBuffer: async () => new ArrayBuffer(8) }) });
  await inspecte("t1");
  dit("succes : la cle de sujet RESTE posee (l'idempotence du declencheur "
      + "n'est rendue qu'aux ECHECS)", INSP_SUJET === "n:t1", J(INSP_SUJET));
  dit("... et la boite n'est pas vidée : elle porte ce que l'apercu a rendu",
      INSP_VIEW_EL.innerHTML !== "", J(INSP_VIEW_EL.innerHTML));

  /* (e) LE RE-CLIC — le residu nomme a la livraison, tranche. `selectionne`
        sort PAR LE HAUT sur un nœud deja designe (un balayage ne doit pas
        relancer N constructions), donc rendre la cle ne suffisait pas : le
        geste evident apres un echec — re-cliquer le nœud — ne repartait pas.
        La clause etroite n'ouvre le passage que dans l'etat exact « un nœud
        est designe ET sa cle a ete rendue », c'est-a-dire apres un echec.
        LE FOND RESTE GARDE : `onCanvasDown` appelle `selectionne(null)` a
        CHAQUE pointerdown du fond (chaque debut de pan), et sans selection il
        n'y a rien a re-tenter. */
  DOC_GRAPH = NU;
  VUE = "canvas";
  armeVue(); INSP_URL = null;
  ARETE = null; SEL = null; INSP_SUJET = ""; INSPECTES.length = 0;
  selectionne("t1");
  dit("le premier clic pose le sujet et DIFFERE la construction",
      SEL === "t1" && INSP_SUJET === "n:t1" && INSPECTES.length === 0,
      SEL + " / " + INSP_SUJET);
  RAW = () => ({ ok: true, blob: async () => ({
    arrayBuffer: async () => new ArrayBuffer(8) }) });
  await inspecte("t1");
  INSPECTES.length = 0;
  SELECTEURS.length = 0;
  selectionne("t1");
  dit("apres un SUCCES, re-cliquer le meme nœud SORT PAR LE HAUT (ni palette "
      + "repeinte, ni construction relancee)",
      INSPECTES.length === 0 && INSP_SUJET === "n:t1"
      && SELECTEURS.indexOf("#cf-forge3d-palette") < 0,
      J(INSPECTES) + " / " + J(INSP_SUJET) + " / " + J(SELECTEURS));
  RAW = () => { throw new Error("transport coupé"); };
  await inspecte("t1");
  dit("un echec rend la cle", INSP_SUJET === "" && SEL === "t1",
      J(INSP_SUJET) + " / " + String(SEL));
  INSPECTES.length = 0;
  SELECTEURS.length = 0;
  selectionne("t1");
  dit("... et re-cliquer le MEME nœud RE-TENTE : le geste evident, enfin "
      + "branche", INSP_SUJET === "n:t1", J(INSP_SUJET));
  dit("... il est bien PASSE par le corps de `selectionne` (palette repeinte)",
      SELECTEURS.indexOf("#cf-forge3d-palette") >= 0, J(SELECTEURS));
  dit("... en DIFFERANT comme le premier clic (rien n'est poste tout de "
      + "suite)", INSPECTES.length === 0, J(INSPECTES));
  /* LE FOND, LUI, NE PASSE PAS. `onCanvasDown` appelle `selectionne(null)` a
     CHAQUE pointerdown du fond — c'est-a-dire au debut de chaque pan. Une
     clause qui ne regarderait que la cle (vide au repos, puisque rien n'est
     designe) rouvrirait le passage a tous ces gestes-la, et chaque debut de
     pan repeindrait la palette entiere pour rien. */
  videInspecteur();
  SEL = null; INSP_SUJET = "";
  SELECTEURS.length = 0;
  selectionne(null);
  dit("cliquer le FOND au repos SORT PAR LE HAUT (chaque debut de pan passe "
      + "ici : sans selection, il n'y a rien a re-tenter)",
      SELECTEURS.indexOf("#cf-forge3d-palette") < 0 && SEL === null,
      J(SELECTEURS));
  videInspecteur();
}

/* 19. S2 — LA MOLETTE DU VIEWER EMBARQUE NE ZOOME PAS LA SCENE. Le
      `model-viewer` vendorise `preventDefault` sa propre molette (c'est son
      dolly) mais ne l'ARRETE PAS de remonter : sur le canvas il vit DANS le
      nœud artefact, donc la surface la recevait AUSSI et zoomait la scene
      entiere pendant que l'utilisateur croyait s'approcher de son modele.
      Mesure sur la vraie fonction, evenement fabrique — un pin de source
      dirait que la chaine est la, pas que la camera reste immobile. */
const SURF = { getBoundingClientRect: () => ({ left: 0, top: 0 }),
               clientLeft: 0, clientTop: 0 };
const molette = (dans) => {
  let empeche = 0;
  onCanvasWheel({
    currentTarget: SURF, clientX: 100, clientY: 100, deltaY: -120,
    preventDefault: () => { empeche += 1; },
    target: { closest: (s) => ((dans && s === ".cf-forge3d-art-view")
                               ? {} : null) },
  });
  return empeche;
};
camPending = null; camRaf = 0; FRAMES.length = 0;
const emp1 = molette(true);
dit("molette SUR le viewer du nœud artefact : la camera ne bouge pas",
    camPending === null && FRAMES.length === 0, J(camPending));
dit("... et le defilement n'est meme pas confisque — le viewer, LUI, en fait "
    + "quelque chose", emp1 === 0, emp1);
const emp2 = molette(false);
dit("molette sur le FOND : la camera zoome (le garde ne mange pas le geste "
    + "normal)", !!camPending && camPending.z > 1, J(camPending));
dit("... et la surface confisque bien le defilement de la page", emp2 === 1,
    emp2);
camPending = null; camRaf = 0; FRAMES.length = 0;

banc18().then(
  () => {
    videInspecteur();   /* aucune minuterie ne survit au banc */
    process.stdout.write(JSON.stringify(out));
  },
  (e) => {
    dit("le banc asynchrone a leve", false, String((e && e.stack) || e));
    process.stdout.write(JSON.stringify(out));
  });
"""


_BANC_PALETTE_PRELUDE = r"""
/* LES STUBS — et RIEN QUE les stubs : ce que le module lit du CORE (le
   document, le jeton `M`, les peintres du DOM). Toute la logique mesuree
   ci-dessous est extraite du fichier LIVRE. */
let DOC_GRAPH = null;
let INFO = null, ARTIFACT = null, LAST_MANIFEST = null, SEL = null;
let VUE = "canvas", PREVIEW_URL = null;
const HIST = [];
const TOASTS = [];
const PATCHES = [];
/* LE TRANSPORT, PILOTE (ronde de correction 2c-T5, S3). `inspecte` n'est plus
   un stub : c'est la VRAIE fonction, extraite du fichier livre, et ce banc
   decide de ce que le reseau lui rend (ou lui LEVE). `INSPECTES` enregistre
   les nœuds REELLEMENT postes — une mesure du debounce plus honnete qu'un
   stub : zero requete veut dire zero apercu construit, cote serveur compris. */
let RAW = null;
const INSPECTES = [];
const M = {
  toast: (t) => { TOASTS.push(String(t)); },
  patch: (p) => {
    PATCHES.push(p);
    if (Object.prototype.hasOwnProperty.call(p, "graph")) DOC_GRAPH = p.graph;
  },
  api: {
    raw: async (methode, route, corps) => {
      INSPECTES.push(corps && corps.nid);
      if (typeof RAW !== "function") throw new Error("aucun transport arme");
      return RAW(methode, route, corps);
    },
  },
};
const CF = { current: () => 0 };
/* L'OBJECTURL, PILOTEE. node n'offre pas d'`URL.createObjectURL` sur lequel on
   voudrait compter, et ce qui se mesure ici est justement qu'une URL posee
   soit REVOQUEE (pas seulement oubliee) : on la tient donc nous-memes. */
const REVOQUEES = [];
const URL = { createObjectURL: () => "blob:neuf",
              revokeObjectURL: (u) => { REVOQUEES.push(String(u)); } };
/* le SEUL nœud de DOM du banc : la boite du viewer de l'inspecteur. Tout le
   reste rend `null` — les peintres s'arretent d'eux-memes. */
let INSP_VIEW_EL = null;
/* ... et LES SELECTEURS DEMANDES, enregistres. C'est la seule facon de voir
   qu'un garde a bien SORTI PAR LE HAUT : `marqueSel` et `paintPalette` ne
   laissent aucune trace dans un banc sans DOM (leurs `$` rendent null), donc
   sans ce journal un « il n'a rien fait » passerait au vert meme si le code
   avait tout refait. */
const SELECTEURS = [];
function get(k) { return (k === "graph") ? DOC_GRAPH : null; }
function $(sel) {
  SELECTEURS.push(String(sel));
  return (sel === "#cf-forge3d-insp-view") ? INSP_VIEW_EL : null;
}
function paintVue() {}
function paintUndo() {}
function paintNodeThumb() {}
function paintCost() {}
function build3d() {}
build3d.busy = false;
/* le GESTE de publication est un stub (il parle au reseau) ; ce qui se mesure
   ici est ce que le BORDEREAU en DIT — `publieHtml` lit son `.busy`, comme le
   bouton « Construire » lit celui de `build3d`. */
function publishLibrary() {}
publishLibrary.busy = false;
/* la paire rAF, PILOTEE : rien ne s'execute tant que le banc ne le demande
   pas — une frame reelle n'a rien a faire dans une mesure, et ce qui compte
   est justement de savoir si une frame a ete DEMANDEE. */
const FRAMES = [];
function scheduleFrame(fn) { FRAMES.push(fn); return FRAMES.length; }
function flushCam() {}
/* ce que l'inspecteur DIT, enregistre au lieu d'etre peint — c'est la seule
   facon de mesurer un panneau sans DOM. */
const NOMS = [];
const ETATS = [];
function inspNom(t) { NOMS.push(String(t == null ? "" : t)); }
function inspEtat(t) { ETATS.push(String(t == null ? "" : t)); }
function inspAvoues() {}
"""


def _banc_palette(tmp_path, glb_b64: str) -> list:
    """Fait tourner les VRAIES fonctions de palette / d'export / de bordereau
    de `mod-forge3d.js` — jamais une reecriture."""
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : le harnais de palette ne peut pas tourner")
    src = re.sub(r"/\*.*?\*/", " ", JS.read_text(encoding="utf-8"), flags=re.S)
    morceaux = [_BANC_PALETTE_PRELUDE,
                'const GLB_B64 = "' + glb_b64 + '";']
    for nom in ("PROC_KINDS", "PROC_LABELS", "CHAIN_MAX", "TILE_DEFAUT",
                "ART_NAME_MAX", "KIND_LABELS", "KIND_HINTS", "GRAMMAIRE",
                # `THUMB_W` et `THUMB_H` sont declarees ENSEMBLE : une seule
                # extraction les porte toutes les deux.
                "THUMB_W", "PAL", "JOBS", "RUNS", "ERRS",
                # la camera et ses bornes (ronde 2c-T5, S2) : `CAM_X0`
                # declare aussi `CAM_Y0`, `ZOOM_MIN` aussi `ZOOM_MAX`.
                "CAM_X0", "ZOOM_MIN", "CAM"):
        morceaux.append(_js_decl(src, nom))
    morceaux.append(_js_decl(src, "INSP_MS"))
    for nom in ("ROWS_MEMO", "ARETE", "INSP_SUJET", "INSP_JETON", "INSP_URL",
                # `GEN` : la garde de generation de `inspecte` ; `FIGE_PRET` :
                # l'etat REEL du viewer du resultat (ronde 2c-T5).
                "inspTimer", "INSP_MV", "GEN", "FIGE_PRET",
                # `camPending` declare aussi `camRaf`.
                "camPending"):
        morceaux.append(_js_decl(src, nom, "let"))
    for nom in ("esc", "weight", "connu", "sansProto", "kindLabel",
                "noeudTitre", "rowModel", "graphRows", "rowsDe", "rowDuNoeud",
                "lienValide", "aEntree", "aSortie", "chaineAttendue",
                "chaineDe", "surnumeraire", "maillonsAval", "rewireRow",
                "freeId", "zEmpilement", "editMat", "editTrs", "setGraph",
                "numHtml", "procSelHtml", "geoHtml", "sideSelHtml", "blocHtml",
                "finishLabel", "matHtml", "trsHtml", "thumbHtml",
                "mesh3dInfo", "engineOf", "engineFor", "ultraCredits",
                "engPrice", "usdTxt", "priceTxt", "sourceTxt", "chipHtml",
                "runHtml", "mesh3dHtml", "kindHintHtml", "nodeBodyHtml",
                "artifactNodeHtml", "bordereauHtml", "ignoresHtml",
                # 2c Task 6 : ce que le bordereau DIT de la publication.
                "publieHtml",
                "fichierHtml", "exportFormats", "exportNodeHtml",
                "exportEtatHtml", "couchesRestantes", "plafondAtteint",
                "premiereMatiere", "naitCouche", "naitProc", "naitMaillon",
                "naitExport", "paletteHtml", "paintPalette", "glbExtras",
                "mondeEl", "marqueSel", "majSelArete", "selectionne",
                "selectionneArete", "videInspecteur", "majInspecteur",
                # ronde de correction 2c-T5 (S3) : les sorties d'ECHEC de
                # l'inspecteur se mesurent sur la vraie fonction, transport
                # pilote — un stub ne dit pas ce qu'elle rend.
                "videApercuInsp", "echecInsp", "inspecte", "onCanvasWheel"):
        morceaux.append(_js_fn(src, nom))
    js = tmp_path / "banc_palette.js"
    js.write_text("\n".join(morceaux) + "\n" + _BANC_PALETTE, encoding="utf-8")
    r = subprocess.run([node, str(js)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def test_le_harnais_de_palette_refuse_le_maillon_flottant_et_dit_les_exports(
        tmp_path):
    """Les pins de source disent QUE le code appelle ; ils ne disent pas ce
    qu'il REFUSE (la lecon de la Task 4). Ce banc fait tourner les VRAIES
    fonctions de la Task 5 dans node et mesure les proprietes qui comptent :
    une naissance = UNE entree d'annulation, un maillon ne nait JAMAIS
    flottant (ni en eventail depuis son traitement), le plafond est dit AVANT
    le refus du backend, un nœud d'export n'est JAMAIS muet, et les aveux d'un
    VRAI GLB d'apercu (octets construits ici, par le backend) se relisent
    cote client."""
    from app.services.cards import forge3d as F9
    from app.services.cards import forge3d_scene as SC
    import base64
    relief = SC.relief_mesh(Image.new("L", (8, 8), 255), 63.0, 88.0, 1.0,
                            0.3, 4)
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    glb = SC.write_scene_glb(
        [{"name": "x", "mesh": relief, "png": png.getvalue(), "alpha": False,
          "z_mm": 0.0}], name="apercu",
        extras={"schema": F9.PREVIEW_SCHEMA, "preview": True,
                "ignored": [{"node": "m9", "why": "maillon surnumeraire"}]})
    cas = _banc_palette(tmp_path, base64.b64encode(glb).decode("ascii"))
    rates = [c for c in cas if not c["ok"]]
    assert not rates, "\n".join(f"{c['nom']} : {c['detail']}" for c in rates)
    # un PLANCHER, pas un compte fige (meme raison que le banc de chaines) :
    # un banc ampute — une section commentee, une exception avalee — passerait
    # sinon en vert sans rien mesurer. (43 cas a la livraison T5, 83 apres la
    # ronde de correction, 89 avec la publication de la T6 — le plancher garde
    # la meme marge qu'avant.)
    assert len(cas) >= 72, len(cas)


def test_le_harnais_de_chaines_tient_l_aller_retour_canvas_liste(tmp_path):
    """Les deux vues ecrivent LE MEME graphe (plan 2c, Task 4) : un lien cree
    a la souris produit une chaine que `rowModel` lit a l'identique, et que
    l'ecrivain de la vue liste (`rewireRow`) relit sans la reecrire. Mesure
    sur le code LIVRE, extrait du fichier — pas sur une reecriture."""
    cas = _banc_chaines(tmp_path)
    rates = [c for c in cas if not c["ok"]]
    assert not rates, "\n".join(f"{c['nom']} : {c['detail']}" for c in rates)
    # un PLANCHER, pas un compte : un banc qui perdrait la moitie de ses cas
    # (une exception avalee, une section commentee) passerait sinon en vert
    # sans rien mesurer. Le chiffre exact, lui, n'a pas a etre gele — en
    # figer un condamnerait chaque cas ajoute a toucher deux endroits.
    assert len(cas) >= 28, len(cas)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
