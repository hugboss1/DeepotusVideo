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
import struct                                                     # noqa: E402
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
    # le bordereau est peint depuis la REPONSE (mesure), pas depuis l'intention
    assert "cf-forge3d-slip" in rendu
    assert "weight" in rendu or "Kio" in rendu


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
